#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Counterfactual round-1 surrogate model (tier-upgrade gap G1).

Idea
----
The paper's mechanism result says the first-round flip set determines much of the
subsequent fate: FRO-2 suppresses incorrect first-round flips ~9.5x while correct
flips fall only ~2.7x, and yet the arm succeeds more often.  If a small set of
ROUND-1-ONLY statistics is approximately sufficient for the failure probability,
then the effect of ANY first-round offset delta can be predicted WITHOUT running
that arm's decoder:

    alpha = key.upc_fast(s0)                      (initial syndrome only)
    tau1  = clip(classic_th(0, |s0|) + delta, lo, hi)
    F     = { i : alpha_i >= tau1 }
    n_false = |F \\ supp(e)|,  n_true = |F INTER supp(e)|
    w1      = |s0 XOR (XOR of H-columns at F)|     (post-round-1 syndrome weight)

Verified bit-exact against the frozen carrier by check_surrogate_features.py
(525/525 exact, no threshold clipping at delta in -1..3).

Protocol
--------
Fit  : logistic P(fail | features) on C0 instances at P1', t=92, keys 8..53.
Test : keys 54..99 (key-disjoint).  Predicted DFR for arm delta is the mean of
       the fitted probabilities over the SAME instances with features recomputed
       under delta.  Measured DFR comes from actually running the arm.
       Predicted vs measured RR is the validation statistic; a key-clustered
       bootstrap over held-out keys gives its interval.

Out-of-sample axes:
  (i)   delta  : +1, +3, -1 predicted from a model fit on delta=0 only
  (ii)  t      : same fitted model applied at t=94 and t=96 (same pool/instances)
  (iii) code   : applied at (6007,56,100) and at the L1-scale calibrated point
                 (12323,71,t*)  -- a different key pool and code size
  (iv)  key    : fit and evaluation keys are disjoint everywhere

Candidate feature sets are pre-registered and selected on HELD-OUT C0 log-loss,
never on how well they reproduce the RR:
  M1  n_false
  M2  n_false + n_true
  M3  n_false + n_true + w1
The RR itself is only looked at after selection.

Phases
  S1  P1' t=92, 5 arms, per-instance outcomes + features      (~45 min)
  S4  fit + validate + report (no decoding)                   (seconds)
  S6  cross-config validation vs ARCHIVED measurements, using only the
      first-round features of those configurations (no decoding, ~5 min).
      This supersedes S2/S3: the archived risk ratios already exist, so only
      the features are needed.
  RHO exchange ratios at P2/P3/P1' (no decoding, ~1 min)
  S5  freeze prospective predictions for t=93 and P1PP (no decoding)
  S2B run t=93 and compare with the frozen prediction         (~17 min)
  S2  [superseded by S6] P1' t=94 and t=96 per-instance runs
  S3  [superseded by S6] (6007,56,100) per-instance rerun

Run:  python lw-vs/scripts/exp_surrogate_model.py --phase S1,S2,S3,S4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
OUT = ROOT / "lw-vs" / "results" / "tier_upgrade"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))


def _load_json(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

from qcmdpc.decoders import build_decoder, make_threshold    # noqa: E402
from qcmdpc.generators import (KeyPool, make_error_generator,  # noqa: E402
                               uniform_fixed_weight, random_key, _child_seed)  # noqa: E402
from qcmdpc.stats import cluster_bootstrap_paired, wilson_upper  # noqa: E402

SEED = 20260901
MAX_ITER = 20
N_WORKERS = int(os.environ.get("SM_WORKERS", "10"))

P1 = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
G0_SPEC = {"type": "random", "n_keys": 100}
FRESH_FROM = 8
E_PER_KEY = 3000
DELTAS = (0, 1, 2, 3, -1)          # arms: C0, +1, +2, +3, -1
ARM_NAME = {0: "C0", 1: "FROp1", 2: "FRO-2", 3: "FROp3", -1: "FRONEG"}

# reproducibility gate: the archived formal counts for C0 and FRO-2 on RAND
GATE = {"C0": 282, "FRO-2": 68}

# --- key split (pre-registered, by pool index; keys 8..53 fit, 54..99 test) ---
FIT_KEYS = list(range(FRESH_FROM, FRESH_FROM + 46))
TEST_KEYS = list(range(FRESH_FROM + 46, 100))

_POOL_CACHE: dict = {}


def _pool(pt, gid, spec, tag):
    key = (tag, pt["r"], pt["d"], spec["n_keys"])
    if key not in _POOL_CACHE:
        _POOL_CACHE[key] = KeyPool(SEED, pt, gid, spec)
    return _POOL_CACHE[key]


# ------------------------------------------------------------------ features
def first_round_features(key, e, s0, alpha, tau1_raw, deltas, lo, hi):
    """Per-delta first-round statistics; NO decoder is run here."""
    sup = e.astype(bool)
    out = {}
    for dl in deltas:
        tau = int(np.clip(tau1_raw + dl, lo, hi))
        F = np.nonzero(alpha >= tau)[0]
        n_true = int(sup[F].sum()) if F.size else 0
        n_false = int(F.size) - n_true
        s1 = s0.copy()
        for p in F:
            s1 = key.flip(s1, int(p))
        out[dl] = {"nflip": int(F.size), "n_true": n_true, "n_false": n_false,
                   "w1": int(s1.sum()), "tau": tau}
    return out


def _work_s(job):
    """One key: all arms + features on the same instances."""
    ki, t, n_err, deltas, tag = job
    pt = dict(P1); pt["t"] = t
    pool = _pool(pt, "G0", G0_SPEC, "G0main")
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "G0", key.key_id, pt, G0_SPEC, key, None)
    lo, hi = max(1, (P1["d"] + 1) // 2), P1["d"]
    classic = make_threshold({"type": "classic"}, P1["d"], t, 2 * P1["r"])
    decs = {dl: build_decoder(f"a{dl}", {"algo": "bf_parallel",
                                         "threshold": {"type": "offset",
                                                       "base": {"type": "classic"},
                                                       "offsets": [dl, 0]},
                                         "max_iter": MAX_ITER}, P1["d"], t, P1["r"])
            for dl in deltas}
    n = len(deltas)
    feat = {k: np.zeros((n_err, 5), dtype=np.int32) for k in ("nflip", "n_true", "n_false", "w1", "tau")}
    w0 = np.zeros(n_err, dtype=np.int32)          # |s0|
    fail = {dl: np.zeros(n_err, dtype=np.uint8) for dl in deltas}
    iters = {dl: np.zeros(n_err, dtype=np.int16) for dl in deltas}
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        w0[eid] = int(s0.sum())
        alpha = key.upc_fast(s0)
        tau1 = classic(0, int(s0.sum()))
        f = first_round_features(key, e, s0, alpha, tau1, deltas, lo, hi)
        for j, dl in enumerate(deltas):
            for k in ("nflip", "n_true", "n_false", "w1", "tau"):
                feat[k][eid, j] = f[dl][k]
            r = decs[dl](key, s0.copy())
            fail[dl][eid] = 0 if r.success else 1
            iters[dl][eid] = r.n_iters_run
    return ki, {k: v for k, v in feat.items()}, w0, fail, iters


def _run_s(keys, t, n_err, deltas, tag, workers):
    jobs = [(ki, t, n_err, deltas, tag) for ki in keys]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_work_s, jobs))


def _save_s(tag, keys, t, res, deltas):
    out = {"keys": np.array(keys, dtype=np.int32), "t": np.array([t]),
           "deltas": np.array(deltas, dtype=np.int32), "e_per_key": np.array([E_PER_KEY])}
    for k in ("nflip", "n_true", "n_false", "w1", "tau"):
        out[k] = np.stack([r[1][k] for r in res])      # (n_keys, n_err, n_deltas)
    out["w0"] = np.stack([r[2] for r in res])
    for dl in deltas:
        out[f"fail_{dl}"] = np.stack([r[3][dl] for r in res])
        out[f"iters_{dl}"] = np.stack([r[4][dl] for r in res])
    p = OUT / f"surrogate_{tag}.npz"
    np.savez_compressed(p, **out)
    return p


def _summary(res, t, deltas):
    n_keys = len(res)
    out = {"t": t, "n_keys": n_keys, "errors_per_key": E_PER_KEY,
           "arms": {}}
    for dl in deltas:
        f = np.stack([r[3][dl] for r in res])
        per_key = f.sum(axis=1)
        k = int(per_key.sum()); n = n_keys * E_PER_KEY
        out["arms"][ARM_NAME[dl]] = {
            "failures": k, "trials": n, "dfr": k / n,
            "upper95": wilson_upper(k, n), "per_key": per_key.tolist()}
    return out


def phase_S1() -> None:
    p = OUT / "surrogate_S1.json"
    if not (OUT / "protocol_SURROGATE.json").exists():
        proto = {
            "phase": "SURROGATE",
            "frozen_before": "first S1 decode (see file mtime)",
            "purpose": "G1: a quantitative, out-of-sample-validated predictor of the "
                       "first-round offset effect, computed from round-1 statistics "
                       "only (no decoder run for the counterfactual arm).",
            "feature_recipe": {
                "alpha": "key.upc_fast(s0) on the INITIAL syndrome",
                "tau1": "classic(0,|s0|)",
                "F_delta": "{ i : alpha_i >= clip(tau1+delta, lo, hi) }",
                "n_false": "|F \\ supp(e)|", "n_true": "|F INTER supp(e)|",
                "w1": "|s0 XOR (XOR of H-columns at F)|  (post-round-1 syndrome weight)",
                "status": "verified bit-exact against the frozen carrier by "
                          "check_surrogate_features.py (525/525 exact)"},
            "data": {"pool": "main G0 keys 8..99 (headline pool)",
                     "instances": "error ids 0..2999 at t=92, five arms "
                                  "C0/+1/+2/+3/-1 on identical (H,e,s)"},
            "key_split": {"fit": "pool keys 8..53 (46 keys)",
                          "test": "pool keys 54..99 (46 keys)",
                          "rule": "no key contributes to both sides"},
            "model_candidates": {"M1": ["n_false"], "M2": ["n_false", "n_true"],
                                 "M3": ["n_false", "n_true", "w1"]},
            "selection_rule": "lowest held-out C0 log-loss on the test keys; "
                              "the risk ratio is NOT used for selection",
            "primary_validation": "for each delta, predicted RR (ratio of predicted "
                                  "DFRs over the SAME held-out instances) against "
                                  "measured RR with key-clustered CI95",
            "secondary_validation": [
                "cross-t: same fitted model applied at t=94 and t=96, same pool",
                "cross-code: applied at (6007,56,100)",
                "cross-code: applied at the L1-scale calibrated point "
                "(12323,71,t*) when available",
                "sensitivity: model refit on pooled C0+FRO-2 instances"],
            "falsification": "a predicted RR outside the measured CI95 on a "
                             "validation axis falsifies the sufficiency claim for "
                             "that axis; reported as measured either way",
            "privileged_information": "features require supp(e); this is a "
                                      "diagnostic/mechanistic model, explicitly not "
                                      "a deployable detector.",
            "written_by": "Claude (session 2026-10-07) before any S1 decode",
        }
        json.dump(proto, open(OUT / "protocol_SURROGATE.json", "w", encoding="utf-8"),
                  indent=1)
        print(f"[S1] protocol frozen -> {OUT/'protocol_SURROGATE.json'}")
    if p.exists() and (OUT / "surrogate_S1.npz").exists():
        print("[S1] cached"); return
    print(f"[S1] P1' t=92, arms {list(ARM_NAME.values())}, "
          f"keys {FIT_KEYS[0]}..{TEST_KEYS[-1]}, {E_PER_KEY} errors/key")
    t0 = time.time()
    keys = FIT_KEYS + TEST_KEYS
    res = _run_s(keys, 92, E_PER_KEY, DELTAS, "S1", N_WORKERS)
    s = _summary(res, 92, DELTAS)
    # reproducibility gate against the archived formal run
    c0 = s["arms"]["C0"]["failures"]; f2 = s["arms"]["FRO-2"]["failures"]
    s["gate"] = {"expected": GATE, "observed": {"C0": c0, "FRO-2": f2},
                 "pass": (c0 == GATE["C0"] and f2 == GATE["FRO-2"])}
    _save_s("S1", keys, 92, res, DELTAS)
    json.dump(s, open(p, "w", encoding="utf-8"), indent=1)
    print(f"    gate {'PASS' if s['gate']['pass'] else '*** FAIL ***'}: "
          f"C0 {c0}/{GATE['C0']}, FRO-2 {f2}/{GATE['FRO-2']}  ({time.time()-t0:.0f}s)")
    for nm in ("C0", "FRO-2", "FROp1", "FROp3", "FRONEG"):
        a = s["arms"][nm]
        print(f"      {nm:7s} {a['failures']:5d}/{a['trials']}  DFR={a['dfr']:.3e}")


def phase_S2() -> None:
    for t in (94, 96):
        p = OUT / f"surrogate_S2_t{t}.json"
        if p.exists() and (OUT / f"surrogate_S2_t{t}.npz").exists():
            print(f"[S2 t={t}] cached"); continue
        print(f"[S2] P1' t={t}, C0/FRO-2, same pool/instances")
        t0 = time.time()
        res = _run_s(FIT_KEYS + TEST_KEYS, t, E_PER_KEY, (0, 2), f"S2_t{t}", N_WORKERS)
        s = _summary(res, t, (0, 2))
        _save_s(f"S2_t{t}", FIT_KEYS + TEST_KEYS, t, res, (0, 2))
        json.dump(s, open(p, "w", encoding="utf-8"), indent=1)
        print(f"    t={t}: C0 {s['arms']['C0']['failures']} "
              f"FRO-2 {s['arms']['FRO-2']['failures']}  ({time.time()-t0:.0f}s)")


def phase_S3() -> None:
    """(6007,56,100) with per-instance features -- exact key/error reconstruction
    of exp_round_controls.phase4 (rid='run', t=100)."""
    p = OUT / "surrogate_S3_bigr.json"
    if p.exists() and (OUT / "surrogate_S3_bigr.npz").exists():
        print("[S3] cached"); return
    r, d, t, n_keys, n_err = 6007, 56, 100, 40, 1000
    print(f"[S3] (r,d,t)=({r},{d},{t}), {n_keys} keys x {n_err} errors")
    t0 = time.time()

    def work(ki):
        rng = np.random.default_rng(_child_seed(SEED, f"big|run|{t}|key", ki))
        key = random_key(rng, r, d, f"run-{t}-{ki:03d}")
        n = 2 * r
        lo, hi = max(1, (d + 1) // 2), d
        classic = make_threshold({"type": "classic"}, d, t, n)
        decs = {dl: build_decoder(f"b{dl}", {"algo": "bf_parallel",
                                             "threshold": {"type": "offset",
                                                           "base": {"type": "classic"},
                                                           "offsets": [dl, 0]},
                                             "max_iter": MAX_ITER}, d, t, r)
                for dl in (0, 2)}
        feat = {k: np.zeros((n_err, 2), dtype=np.int32) for k in ("nflip", "n_true", "n_false", "w1", "tau")}
        w0 = np.zeros(n_err, dtype=np.int32)
        fail = {dl: np.zeros(n_err, dtype=np.uint8) for dl in (0, 2)}
        iters = {dl: np.zeros(n_err, dtype=np.int16) for dl in (0, 2)}
        for eid in range(n_err):
            erng = np.random.default_rng(_child_seed(SEED, f"big|run|{t}|err|{ki}", eid))
            e = uniform_fixed_weight(erng, n, t)
            s0 = key.syndrome_from_global(e)
            w0[eid] = int(s0.sum())
            alpha = key.upc_fast(s0)
            tau1 = classic(0, int(s0.sum()))
            f = first_round_features(key, e, s0, alpha, tau1, (0, 2), lo, hi)
            for j, dl in enumerate((0, 2)):
                for k in ("nflip", "n_true", "n_false", "w1", "tau"):
                    feat[k][eid, j] = f[dl][k]
                rr = decs[dl](key, s0.copy())
                fail[dl][eid] = 0 if rr.success else 1
                iters[dl][eid] = rr.n_iters_run
        return ki, feat, w0, fail, iters

    with ProcessPoolExecutor(max_workers=min(N_WORKERS, 8)) as ex:
        res = list(ex.map(work, range(n_keys)))
    out = {"keys": np.arange(n_keys, dtype=np.int32), "t": np.array([t]),
           "r": np.array([r]), "d": np.array([d]), "e_per_key": np.array([n_err]),
           "deltas": np.array([0, 2], dtype=np.int32)}
    for k in ("nflip", "n_true", "n_false", "w1", "tau"):
        out[k] = np.stack([x[1][k] for x in res])
    out["w0"] = np.stack([x[2] for x in res])
    for dl in (0, 2):
        out[f"fail_{dl}"] = np.stack([x[3][dl] for x in res])
        out[f"iters_{dl}"] = np.stack([x[4][dl] for x in res])
    np.savez_compressed(OUT / "surrogate_S3_bigr.npz", **out)
    c0 = sum(int(x[3][0].sum()) for x in res); f2 = sum(int(x[3][2].sum()) for x in res)
    json.dump({"t": t, "r": r, "d": d, "n_keys": n_keys, "errors_per_key": n_err,
               "c0_failures": c0, "fro2_failures": f2,
               "note": "archive phase4 had C0 8.125e-3 -> 2.407"},
              open(p, "w", encoding="utf-8"), indent=1)
    print(f"    C0 {c0}/{n_keys*n_err} FRO-2 {f2}  ({time.time()-t0:.0f}s)")


# ---------------------------------------------------------------- phase RHO
# Model-input statistics at the work points that already have measured FRO-1/2/3
# risk ratios (P2 and P3, tier-2 expanded-confirmation data).  No decoding.
RHO_POINTS = [
    {"id": "P2", "r": 3001, "d": 37, "t": 66},
    {"id": "P3", "r": 4001, "d": 41, "t": 82},
    {"id": "P1prime", "r": 4801, "d": 45, "t": 92},
]
RHO_KEYS, RHO_ERR = 12, 300


def _work_rho(job):
    pid_, r, d, t, ki = job
    param = {"id": pid_, "r": r, "d": d, "t": t, "n0": 2}
    spec = {"type": "random", "n_keys": RHO_KEYS}
    pool = KeyPool(SEED, param, f"rho{pid_}", spec)
    key = pool.keys[ki]
    gen = make_error_generator(SEED, f"rho{pid_}", key.key_id, param, spec, key, None)
    lo, hi = max(1, (d + 1) // 2), d
    classic = make_threshold({"type": "classic"}, d, t, 2 * r)
    deltas = (0, 1, 2, 3)
    cnt = {dl: {"true": 0, "false": 0} for dl in deltas}
    n1 = n0 = 0
    for eid in range(RHO_ERR):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        alpha = key.upc_fast(s0)
        sup = e.astype(bool)
        tau1 = classic(0, int(s0.sum()))
        n1 += int(sup.sum()); n0 += int(sup.size - sup.sum())
        for dl in deltas:
            tau = int(np.clip(tau1 + dl, lo, hi))
            F = alpha >= tau
            tin = int(F[sup].sum())
            cnt[dl]["true"] += tin
            cnt[dl]["false"] += int(F.sum()) - tin
    return ki, n1, n0, cnt


def phase_RHO() -> None:
    """rho(delta) at every work point with measured offset risk ratios."""
    p = OUT / "rho_workpoints.json"
    if p.exists():
        print("[RHO] cached"); return
    print(f"[RHO] exchange ratios at {len(RHO_POINTS)} work points "
          f"({RHO_KEYS} keys x {RHO_ERR} errors each, no decoding)")
    out = {"points": {}}
    for pt in RHO_POINTS:
        with ProcessPoolExecutor(max_workers=min(N_WORKERS, 6)) as ex:
            res = list(ex.map(_work_rho, [(pt["id"], pt["r"], pt["d"], pt["t"], ki)
                                          for ki in range(RHO_KEYS)]))
        spec = {"type": "random", "n_keys": RHO_KEYS}
        cnt = {dl: {"true": sum(x[3][dl]["true"] for x in res),
                    "false": sum(x[3][dl]["false"] for x in res)} for dl in (0, 1, 2, 3)}
        n_inst = RHO_KEYS * RHO_ERR
        cell = {"r": pt["r"], "d": pt["d"], "t": pt["t"], "n_keys": RHO_KEYS,
                "errors_per_key": RHO_ERR, "rho": {}}
        for dl in (1, 2, 3):
            def_true = (cnt[0]["true"] - cnt[dl]["true"]) / n_inst
            def_false = (cnt[0]["false"] - cnt[dl]["false"]) / n_inst
            cell["rho"][str(dl)] = {
                "deferred_true_per_instance": def_true,
                "avoided_false_per_instance": def_false,
                "rho": (def_false / def_true) if def_true > 0 else None}
        out["points"][pt["id"]] = cell
        print(f"  {pt['id']} (r={pt['r']},d={pt['d']},t={pt['t']}): " +
              "  ".join(f"rho(+{dl})={cell['rho'][str(dl)]['rho']:.3f}"
                        for dl in (1, 2, 3)))
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    print(f"[RHO] -> {p}")


# ------------------------------------------------------------------ phase S7
def phase_S7() -> None:
    """Arm-conditional model with leave-one-ARM-out validation.

    S4 showed why the C0-only design fails: the round-1 counts are a POST-TREATMENT
    variable, so P(fail | counts) estimated under C0 does not transfer to an arm
    whose counts arise from a different threshold (low n_true means "hard instance"
    under C0 but "deferred by the intervention" under FRO-2).  The causal-inference
    fix is to condition on the TREATMENT as well: fit P(fail | counts, delta)
    pooling several arms, then predict a held-out arm from ITS OWN counts, which
    are computable without decoding it.  Double hold-out: keys AND arm.
    No decoding: everything is read from the S1 npz."""
    p = OUT / "surrogate_S7_leaveoneout.json"
    if p.exists():
        print("[S7] cached"); return
    proto = OUT / "protocol_S7.json"
    if not proto.exists():
        json.dump({
            "phase": "S7",
            "written_before": "the S7 fit (no decoding involved)",
            "motivation": "S4's C0-only counterfactual model failed: its features are "
                          "post-treatment, so P(fail|counts) does not transfer across "
                          "arms. S7 conditions on the arm instead.",
            "design": {"data": "S1 npz: 92 keys x 3000 errors, arms {0,+1,+2,+3,-1}, "
                               "features (n_false, n_true, w1) per arm",
                       "fit": "keys 8..53 x the four NON-held-out arms",
                       "validate": "keys 54..99 x the held-out arm",
                       "prediction": "held-out arm's DFR = mean of predicted "
                                     "probabilities over held-out keys, using the "
                                     "held-out arm's own features (no decoding)",
                       "candidate_sets": {"P1": ["n_false", "n_true"],
                                          "P2": ["n_false", "n_true", "w1"],
                                          "P3": ["n_false", "n_true", "w1", "nflip"]},
                       "selection": "held-out-C0 log-loss is NOT applicable here "
                                    "(C0 is itself an arm); select by mean held-out "
                                    "log-loss across the four leave-one-out folds, "
                                    "then report the risk ratios for ALL arms as "
                                    "measured -- the selection never sees an arm's RR"},
            "grading": "same scale as the SURROGATE protocol amendment-1: SUCCESS if "
                       "the measured RR lies inside the measured CI95 AND the "
                       "prediction is within a factor of 1.5 in >=3/4 of the folds",
        }, open(proto, "w", encoding="utf-8"), indent=1)
        print(f"[S7] protocol frozen -> {proto}")
    d1 = np.load(OUT / "surrogate_S1.npz")
    keys = d1["keys"]; deltas = list(d1["deltas"])
    fit_mask = np.isin(keys, FIT_KEYS)
    test_mask = ~fit_mask
    n_err = d1["nflip"].shape[1]
    cands = {"P1": ["n_false", "n_true"], "P2": ["n_false", "n_true", "w1"],
             "P3": ["n_false", "n_true", "w1", "nflip"]}
    results = {}
    best = None
    for cname, cols in cands.items():
        fold_ll = []
        for j, dl in enumerate(deltas):
            tr = [(jj, ddx) for jj, ddx in enumerate(deltas) if jj != j]
            Xtr = np.stack([np.concatenate([d1[c][:, :, jj][fit_mask].ravel()
                                            for jj, _ in tr]) for c in cols], axis=1)
            ytr = np.concatenate([d1[f"fail_{ddx}"][fit_mask].ravel().astype(int)
                                  for _, ddx in tr])
            Xte = np.stack([d1[c][:, :, j][test_mask].ravel() for c in cols], axis=1)
            yte = d1[f"fail_{dl}"][test_mask].ravel().astype(int)
            clf, mu, sd, ll, auc, brier, _ = _fit_eval(Xtr, ytr, Xte, yte)
            fold_ll.append(ll)
        mll = float(np.mean(fold_ll))
        results[cname] = {"cols": cols, "mean_heldout_logloss": mll}
        print(f"  {cname} {cols}: mean held-out logloss across folds = {mll:.6f}")
        if best is None or mll < best[1]:
            best = (cname, mll, cols)
    cname, _, cols = best
    print(f"  -> selected {cname} {cols}")
    out = {"selected": cname, "features": cols, "folds": {}}
    for j, dl in enumerate(deltas):
        tr = [(jj, ddx) for jj, ddx in enumerate(deltas) if jj != j]
        Xtr = np.stack([np.concatenate([d1[c][:, :, jj][fit_mask].ravel()
                                        for jj, _ in tr]) for c in cols], axis=1)
        ytr = np.concatenate([d1[f"fail_{ddx}"][fit_mask].ravel().astype(int)
                              for _, ddx in tr])
        clf, mu, sd, ll, auc, brier, _ = _fit_eval(Xtr, ytr, Xtr, ytr)
        pred = {}
        for tag, jj in (("C0", deltas.index(0)), (ARM_NAME[dl], j)):
            X = np.stack([d1[c][:, :, jj][test_mask].ravel() for c in cols], axis=1)
            pred[tag] = float(clf.predict_proba((X - mu) / sd)[:, 1].sum())
        rr_pred = pred["C0"] / pred[ARM_NAME[dl]]
        per0 = d1["fail_0"][test_mask].sum(axis=1)
        pera = d1[f"fail_{dl}"][test_mask].sum(axis=1)
        boot = cluster_bootstrap_paired(per0, pera, n_err, B=10000, seed=20260905)
        out["folds"][ARM_NAME[dl]] = {
            "predicted_rr_vs_C0": rr_pred,
            "measured_rr": boot["point"]["risk_ratio"],
            "measured_rr_ci95": boot["ci"]["risk_ratio"],
            "inside_ci": (boot["ci"]["risk_ratio"][0] is not None and
                          boot["ci"]["risk_ratio"][0] <= rr_pred <= boot["ci"]["risk_ratio"][1]),
            "factor": rr_pred / boot["point"]["risk_ratio"] if boot["point"]["risk_ratio"] else None}
        f = out["folds"][ARM_NAME[dl]]
        mark = "INSIDE" if f["inside_ci"] else ("within 1.5x" if f["factor"] and
               0.667 <= f["factor"] <= 1.5 else "*** OFF ***")
        print(f"  hold out {ARM_NAME[dl]:7s}: predicted RR {rr_pred:6.3f}  measured "
              f"{f['measured_rr']:.3f} [{f['measured_rr_ci95'][0]:.3f}, "
              f"{f['measured_rr_ci95'][1]:.3f}]  {mark}")
    # grading
    inside = sum(1 for f in out["folds"].values() if f["inside_ci"])
    within = sum(1 for f in out["folds"].values()
                 if f["factor"] and 0.667 <= f["factor"] <= 1.5)
    out["grading"] = {"n_folds": len(out["folds"]), "inside_ci": inside,
                      "within_1.5x": within,
                      "verdict": ("SUCCESS" if inside > len(out["folds"]) / 2 and
                                  within >= 3 * len(out["folds"]) / 4 else
                                  "PARTIAL" if within >= len(out["folds"]) / 2 else "FAILURE")}
    print(f"  grading: {out['grading']['verdict']} "
          f"({inside}/{len(out['folds'])} inside CI, {within} within 1.5x)")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    print(f"[S7] -> {p}")


# ------------------------------------------------------------------ phase S6
# Cross-configuration validation WITHOUT decoding: for every archived
# measurement of the first-round effect at another configuration, the model
# needs only the FIRST-ROUND FEATURES of that configuration's instances --
# and those are computable from the same seed discipline with no decoder.
# The comparison target is the archived measured risk ratio and its CI.
S6_POINTS = [
    {"id": "tsweep_t94", "r": 4801, "d": 45, "t": 94, "n_keys": 30,
     "key_ctx": "tsweep|key|94", "err_ctx": "tsweep|err|94|{}",
     "measured_rr": 2.819, "measured_ci": [2.275, 3.603], "src": "round_controls/phase2"},
    {"id": "tsweep_t96", "r": 4801, "d": 45, "t": 96, "n_keys": 30,
     "key_ctx": "tsweep|key|96", "err_ctx": "tsweep|err|96|{}",
     "measured_rr": 1.871, "measured_ci": [1.721, 2.039], "src": "round_controls/phase2"},
    {"id": "bigr_6007_56_100", "r": 6007, "d": 56, "t": 100, "n_keys": 40,
     "key_ctx": "big|run|100|key", "err_ctx": "big|run|100|err|{}",
     "measured_rr": 2.407, "measured_ci": [2.092, 2.817], "src": "round_controls/phase4"},
]


def _work_s6(job):
    pid_, r, d, t, ki, n_err, key_ctx, err_ctx = job
    rng = np.random.default_rng(_child_seed(SEED, key_ctx, ki))
    key = random_key(rng, r, d, f"s6-{pid_}-{ki:03d}")
    lo, hi = max(1, (d + 1) // 2), d
    classic = make_threshold({"type": "classic"}, d, t, 2 * r)
    out = {k: np.zeros((n_err, 2), dtype=np.int32) for k in ("nflip", "n_true", "n_false", "w1")}
    for eid in range(n_err):
        erng = np.random.default_rng(_child_seed(SEED, err_ctx.format(ki), eid))
        e = uniform_fixed_weight(erng, 2 * r, t)
        s0 = key.syndrome_from_global(e)
        alpha = key.upc_fast(s0)
        tau1 = classic(0, int(s0.sum()))
        f = first_round_features(key, e, s0, alpha, tau1, (0, 2), lo, hi)
        for j, dl in enumerate((0, 2)):
            for k in ("nflip", "n_true", "n_false", "w1"):
                out[k][eid, j] = f[dl][k]
    return ki, out


def phase_S6() -> None:
    """Predict the risk ratio at each archived cross-configuration point from
    first-round features alone, and compare with the archived measurement."""
    p = OUT / "surrogate_S6_crossconfig.json"
    if p.exists():
        print("[S6] cached"); return
    sel = _load_json(OUT / "surrogate_S4_fit.json")
    if not sel:
        print("[S6] needs surrogate_S4_fit.json (run S4 first)"); return
    cols = {"M1": ["n_false"], "M2": ["n_false", "n_true"],
            "M3": ["n_false", "n_true", "w1"]}[sel["selected"]]
    d1 = np.load(OUT / "surrogate_S1.npz")
    keys1 = d1["keys"]; deltas1 = list(d1["deltas"])
    fit_mask = np.isin(keys1, FIT_KEYS)
    j0 = deltas1.index(0)
    Xtr = np.stack([d1[c][:, :, j0][fit_mask].ravel() for c in cols], axis=1)
    ytr = d1["fail_0"][fit_mask].ravel().astype(int)
    clf, mu, sd, ll, auc, brier, _ = _fit_eval(Xtr, ytr, Xtr, ytr)
    print(f"[S6] model {sel['selected']} {cols}; predicting cross-config points")
    res = {"model": sel["selected"], "features": cols,
           "note": "features computed WITHOUT decoding; the comparison target is the "
                   "archived measured risk ratio of the corresponding experiment",
           "predictions": {}}
    for pt in S6_POINTS:
        n_err = 1000
        with ProcessPoolExecutor(max_workers=min(N_WORKERS, 8)) as ex:
            out = list(ex.map(_work_s6, [(pt["id"], pt["r"], pt["d"], pt["t"], ki,
                                          n_err, pt["key_ctx"], pt["err_ctx"])
                                         for ki in range(pt["n_keys"])]))
        preds = {}
        for tag, jj in (("C0", 0), ("FRO-2", 1)):
            X = np.stack([np.stack([o[1][c][:, jj] for o in out]).ravel() for c in cols], axis=1)
            preds[tag] = float(clf.predict_proba((X - mu) / sd)[:, 1].sum())
        rr_pred = preds["C0"] / preds["FRO-2"]
        inside = pt["measured_ci"][0] <= rr_pred <= pt["measured_ci"][1]
        res["predictions"][pt["id"]] = {
            "config": {"r": pt["r"], "d": pt["d"], "t": pt["t"],
                       "n_keys": pt["n_keys"], "errors_per_key": n_err},
            "predicted_rr": rr_pred, "measured_rr": pt["measured_rr"],
            "measured_ci95": pt["measured_ci"], "prediction_inside_ci": bool(inside),
            "ratio_pred_over_measured": rr_pred / pt["measured_rr"],
            "source": pt["src"]}
        mark = "INSIDE" if inside else "*** OUTSIDE ***"
        print(f"  {pt['id']:18s} predicted {rr_pred:6.3f}  measured {pt['measured_rr']:6.3f} "
              f"[{pt['measured_ci'][0]:.2f},{pt['measured_ci'][1]:.2f}]  {mark}")
    json.dump(res, open(p, "w", encoding="utf-8"), indent=1)
    print(f"[S6] -> {p}")


# --------------------------------------------------- phases S5 / S2B: PROSPECTIVE
def phase_S5() -> None:
    """Freeze prospective predictions BEFORE the corresponding runs exist.

    t=93 on the main pool and the P1PP point (12323,71,t*) are configs the model
    can predict from first-round statistics alone.  Writing the numbers here,
    with a timestamp, makes the later comparison a genuine prediction test
    rather than a post-hoc fit."""
    import datetime
    out_p = OUT / "surrogate_S5_prospective_predictions.json"
    if out_p.exists():
        print("[S5] prediction file already frozen; not overwriting")
        return
    d1 = np.load(OUT / "surrogate_S1.npz")
    keys = d1["keys"]; deltas = list(d1["deltas"])
    fit_mask = np.isin(keys, FIT_KEYS)
    # use the S4-selected feature set so the prospective prediction is made by
    # the same model that S4 validates; fall back to M3 only if S4 has not run
    F = ["n_false", "n_true", "w1"]
    sel = _load_json(OUT / "surrogate_S4_fit.json")
    if sel and sel.get("selected"):
        F = {"M1": ["n_false"], "M2": ["n_false", "n_true"],
             "M3": ["n_false", "n_true", "w1"]}[sel["selected"]]
        print(f"  [S5] using S4-selected model {sel['selected']} {F}")
    j0 = deltas.index(0)

    def fit_predict(dsrc, cols, j0_, j2_, mask):
        Xtr = np.stack([dsrc[c][:, :, j0_][mask].ravel() for c in cols], axis=1)
        ytr = dsrc["fail_0"][mask].ravel().astype(int)
        clf, mu, sd, ll, auc, brier, _ = _fit_eval(Xtr, ytr, Xtr, ytr)
        preds = {}
        for tag, jj in (("C0", j0_), ("FRO-2", j2_)):
            X = np.stack([dsrc[c][:, :, jj].ravel() for c in cols], axis=1)
            preds[tag] = float(clf.predict_proba((X - mu) / sd)[:, 1].sum())
        return preds["C0"] / preds["FRO-2"], (ll, auc, brier)

    pred = {"written_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "model": {"features": F, "fit_on": "C0 at P1' t=92, keys 8..53 (fit split)",
                      "note": "single fit, no refit for the targets"},
            "note": "frozen BEFORE the t=93 and P1PP decodes exist; if those files "
                    "are absent at freeze time the test is prospective."}
    rr93, stats93 = fit_predict(d1, F, j0, deltas.index(2), fit_mask)
    pred["t93_main_pool"] = {"predicted_rr_vs_C0": rr93,
                             "fit_stats": {"logloss": stats93[0], "auc": stats93[1]}}
    print(f"  [S5] t=93 predicted RR = {rr93:.3f}")

    cal = OUT / "p1pp_calibration.json"
    pz = OUT / "p1pp_features.npz"
    exists = pz.exists()
    if cal.exists():
        chosen_t = json.load(open(cal, encoding="utf-8"))["chosen_t"]
        p = {"id": "L1", "r": 12323, "d": 71, "t": chosen_t, "n0": 2}
        pool = KeyPool(SEED, p, "RAND", {"type": "random", "n_keys": 32})
        feats = {k: [] for k in F}
        gen0 = None
        for key in pool.keys:
            gen0 = make_error_generator(SEED, "RAND", key.key_id, p,
                                        {"type": "random", "n_keys": 32}, key, None)
            lo, hi = max(1, (71 + 1) // 2), 71
            th = make_threshold({"type": "classic"}, 71, chosen_t, 2 * 12323)
            for eid in range(200):                     # same rule as P1PP's main run
                e = gen0(eid)
                s0 = key.syndrome_from_global(e)
                alpha = key.upc_fast(s0)
                tau1 = th(0, int(s0.sum()))            # per-instance (fixes a latent bug)
                f = first_round_features(key, e, s0, alpha, tau1, (0, 2), lo, hi)
                for k in F:
                    feats[k].append([f[0][k], f[2][k]])
        X = {}
        for k in F:
            X[k] = np.array(feats[k], dtype=np.int32)
        # fit on the P1' fit-keys C0 instances (same model), predict here
        Xtr = np.stack([d1[c][:, :, j0][fit_mask].ravel() for c in F], axis=1)
        ytr = d1["fail_0"][fit_mask].ravel().astype(int)
        clf, mu, sd, ll, auc, brier, _ = _fit_eval(Xtr, ytr, Xtr, ytr)
        pc0 = clf.predict_proba((np.stack([X[k][:, 0] for k in F], axis=1) - mu) / sd)[:, 1].sum()
        pf2 = clf.predict_proba((np.stack([X[k][:, 1] for k in F], axis=1) - mu) / sd)[:, 1].sum()
        pred["p1pp_feature_sample"] = {
            "t_star": chosen_t, "keys": 32, "errors_per_key": 200,
            "note": "PREDICTION-ONLY sample (no decoding): the frozen model is "
                    "applied to the first-round features at the P1PP point",
            "predicted_rr_vs_C0": float(pc0 / pf2)}
        print(f"  [S5] P1PP (12323,71,t={chosen_t}) predicted RR = {pc0/pf2:.3f}")
    pred["p1pp_main_already_existed_at_freeze"] = exists
    pred["t93_already_existed_at_freeze"] = (OUT / "surrogate_S2_t93.json").exists()
    json.dump(pred, open(out_p, "w", encoding="utf-8"), indent=1)
    print(f"  [S5] frozen -> {out_p}")


def phase_S2B() -> None:
    """Run t=93 on the main pool; compare with the frozen S5 prediction."""
    p93 = OUT / "surrogate_S2_t93.json"
    if not p93.exists():
        print("[S2B] running t=93 on the main pool (prospective test)")
        t0 = time.time()
        res = _run_s(FIT_KEYS + TEST_KEYS, 93, E_PER_KEY, (0, 2), "S2_t93", N_WORKERS)
        s = _summary(res, 93, (0, 2))
        _save_s("S2_t93", FIT_KEYS + TEST_KEYS, 93, res, (0, 2))
        json.dump(s, open(p93, "w", encoding="utf-8"), indent=1)
        print(f"    t=93: C0 {s['arms']['C0']['failures']} FRO-2 "
              f"{s['arms']['FRO-2']['failures']}  ({time.time()-t0:.0f}s)")
    pred_p = OUT / "surrogate_S5_prospective_predictions.json"
    if not pred_p.exists():
        print("[S2B] no frozen prediction; run S5 first (or the comparison is post hoc)")
        return
    pred = json.load(open(pred_p, encoding="utf-8"))
    s = json.load(open(p93, encoding="utf-8"))
    per0 = np.array(s["arms"]["C0"]["per_key"]); per2 = np.array(s["arms"]["FRO-2"]["per_key"])
    e = s["errors_per_key"]
    boot = cluster_bootstrap_paired(per0, per2, e, B=10000, seed=20260905)
    cmp_ = {"predicted_rr": pred["t93_main_pool"]["predicted_rr_vs_C0"],
            "measured_rr": boot["point"]["risk_ratio"],
            "measured_rr_ci95": boot["ci"]["risk_ratio"],
            "c0_failures": int(per0.sum()), "fro2_failures": int(per2.sum()),
            "trials": len(per0) * e,
            "frozen_before_measurement": not pred.get("t93_already_existed_at_freeze", True)}
    json.dump(cmp_, open(OUT / "surrogate_S2B_t93_comparison.json", "w", encoding="utf-8"),
              indent=1)
    print(f"  [S2B] t=93: predicted RR {cmp_['predicted_rr']:.3f} vs measured "
          f"{cmp_['measured_rr']:.3f} [{cmp_['measured_rr_ci95'][0]:.3f}, "
          f"{cmp_['measured_rr_ci95'][1]:.3f}]  (frozen first: "
          f"{cmp_['frozen_before_measurement']})")


# ------------------------------------------------------------------ phase S4
def _fit_eval(X, y, Xte, yte):
    from sklearn.linear_model import LogisticRegression
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    clf = LogisticRegression(max_iter=2000, C=1e6)     # near-unregularised
    clf.fit((X - mu) / sd, y)
    p_te = clf.predict_proba((Xte - mu) / sd)[:, 1]
    ll = -np.mean(yte * np.log(np.clip(p_te, 1e-12, 1)) +
                  (1 - yte) * np.log(np.clip(1 - p_te, 1e-12, 1)))
    from sklearn.metrics import roc_auc_score, brier_score_loss
    auc = roc_auc_score(yte, p_te) if yte.sum() > 0 else float("nan")
    brier = brier_score_loss(yte, p_te)
    return clf, mu, sd, ll, auc, brier, p_te


def phase_S4() -> None:
    """Fit + counterfactual validation. No decoding."""
    d1 = np.load(OUT / "surrogate_S1.npz")
    keys = d1["keys"]; deltas = list(d1["deltas"])
    n_keys, n_err, _ = d1["nflip"].shape
    fit_mask = np.isin(keys, FIT_KEYS)
    test_mask = ~fit_mask
    F = [k for k in ("nflip", "n_true", "n_false", "w1")]

    def featmat(name, j):
        return d1[name][:, :, j]

    rep = {"model_candidates": {}, "selection": "held-out C0 log-loss", "predictions": {}}
    # --- candidate selection on held-out C0 (delta index j0) ---
    j0 = deltas.index(0)
    cands = {"M1": ["n_false"], "M2": ["n_false", "n_true"],
             "M3": ["n_false", "n_true", "w1"]}
    y = d1["fail_0"].astype(int)
    best = None
    for nm, cols in cands.items():
        Xtr = np.stack([featmat(c, j0)[fit_mask].ravel() for c in cols], axis=1)
        ytr = y[fit_mask].ravel()
        Xte = np.stack([featmat(c, j0)[test_mask].ravel() for c in cols], axis=1)
        yte = y[test_mask].ravel()
        clf, mu, sd, ll, auc, brier, p_te = _fit_eval(Xtr, ytr, Xte, yte)
        rep["model_candidates"][nm] = {"cols": cols, "heldout_logloss": float(ll),
                                       "heldout_auc": float(auc), "heldout_brier": float(brier)}
        print(f"  {nm} {cols}: heldout logloss={ll:.6f} auc={auc:.4f} brier={brier:.6f}")
        if best is None or ll < best[1]:
            best = (nm, ll, cols, clf, mu, sd)      # KEEP the fit-set model
    nm, _, cols, clf, mu, sd = best
    rep["selected"] = nm
    print(f"  -> selected {nm} {cols}")

    # The model used for every prediction below is the one fitted on the FIT
    # keys only.  Refitting on all keys before predicting on the test keys
    # would leak their C0 outcomes into the baseline arm of the ratio.
    coef = {c: float(w) for c, w in zip(cols, clf.coef_[0])}
    rep["fitted_coefficients_standardised"] = {"intercept": float(clf.intercept_[0]),
                                               "fitted_on": "keys 8..53 only", **coef}

    def predict_arm(arm_idx, mask):
        X = np.stack([d1[c][:, :, arm_idx][mask].ravel() for c in cols], axis=1)
        p = clf.predict_proba((X - mu) / sd)[:, 1].reshape(mask.sum(), -1)
        return p.reshape(mask.sum(), n_err)          # (keys, errors)

    out = {}
    for j, dl in enumerate(deltas):
        nm_arm = ARM_NAME[dl]
        p_fit = predict_arm(j, fit_mask)
        p_test = predict_arm(j, test_mask)
        # predicted per-key failure counts on held-out keys
        pred_c0_test = predict_arm(j0, test_mask).sum(axis=1)
        pred_arm_test = p_test.sum(axis=1)
        meas_fit = int(d1[f"fail_{dl}"][fit_mask].sum())
        meas_test_per_key = d1[f"fail_{dl}"][test_mask].sum(axis=1)
        c0_test_per_key = d1["fail_0"][test_mask].sum(axis=1)
        rr_pred = float(pred_c0_test.sum() / max(pred_arm_test.sum(), 1e-12))
        # measured RR CI on the held-out keys (cluster bootstrap)
        boot = cluster_bootstrap_paired(c0_test_per_key, meas_test_per_key, n_err,
                                        B=10000, seed=20260905)
        out[nm_arm] = {
            "predicted_dfr": float(pred_arm_test.sum() / (test_mask.sum() * n_err)),
            "predicted_rr_vs_C0": rr_pred,
            "measured_failures_heldout": int(meas_test_per_key.sum()),
            "measured_dfr": float(meas_test_per_key.sum() / (test_mask.sum() * n_err)),
            "measured_rr": boot["point"]["risk_ratio"],
            "measured_rr_ci95": boot["ci"]["risk_ratio"],
            "measured_failures_full_pool": int(d1[f"fail_{dl}"].sum()),
            "iters_mean": float(d1[f"iters_{dl}"].mean()),
        }
        print(f"  {nm_arm:7s} predicted RR {rr_pred:6.3f}   measured RR "
              f"{out[nm_arm]['measured_rr']} [{out[nm_arm]['measured_rr_ci95'][0]}, "
              f"{out[nm_arm]['measured_rr_ci95'][1]}]")

    # --- cross-t validation ---
    for t in (94, 96):
        f2 = OUT / f"surrogate_S2_t{t}.npz"
        if not f2.exists():
            continue
        d2 = np.load(f2)
        k2 = d2["keys"]; dl2 = list(d2["deltas"])
        m2 = np.isin(k2, TEST_KEYS)
        j0b = dl2.index(0); j2b = dl2.index(2)
        preds = {}
        for tag, jj in (("C0", j0b), ("FRO-2", j2b)):
            X = np.stack([d2[c][:, :, jj][m2].ravel() for c in cols], axis=1)
            preds[tag] = clf.predict_proba((X - mu) / sd)[:, 1].sum()
        rr_pred = float(preds["C0"] / preds["FRO-2"])
        perf2 = d2["fail_2"][m2].sum(axis=1); per0 = d2["fail_0"][m2].sum(axis=1)
        boot = cluster_bootstrap_paired(per0, perf2, int(d2["e_per_key"][0]), B=10000,
                                        seed=20260905)
        out[f"t{t}"] = {"predicted_rr_vs_C0": rr_pred,
                        "measured_rr": boot["point"]["risk_ratio"],
                        "measured_rr_ci95": boot["ci"]["risk_ratio"],
                        "measured_failures_heldout": int(perf2.sum())}
        print(f"  t={t}  predicted RR {rr_pred:6.3f}   measured RR "
              f"{boot['point']['risk_ratio']} "
              f"[{boot['ci']['risk_ratio'][0]}, {boot['ci']['risk_ratio'][1]}]")

    # --- cross-code validation at (6007,56,100) ---
    f3 = OUT / "surrogate_S3_bigr.npz"
    if f3.exists():
        d3 = np.load(f3)
        preds = {}
        for tag, jj in (("C0", 0), ("FRO-2", 1)):
            X = np.stack([d3[c][:, :, jj].ravel() for c in cols], axis=1)
            preds[tag] = clf.predict_proba((X - mu) / sd)[:, 1].sum()
        rr_pred = float(preds["C0"] / preds["FRO-2"])
        per0 = d3["fail_0"].sum(axis=1); perf2 = d3["fail_2"].sum(axis=1)
        boot = cluster_bootstrap_paired(per0, perf2, int(d3["e_per_key"][0]), B=10000,
                                        seed=20260905)
        out["bigr_6007_56_100"] = {
            "predicted_rr_vs_C0": rr_pred,
            "measured_rr": boot["point"]["risk_ratio"],
            "measured_rr_ci95": boot["ci"]["risk_ratio"],
            "measured_c0_dfr": float(d3["fail_0"].mean()),
            "archive_rr": 2.407}
        print(f"  big-r (6007,56,100)  predicted RR {rr_pred:6.3f}   measured RR "
              f"{boot['point']['risk_ratio']} "
              f"[{boot['ci']['risk_ratio'][0]}, {boot['ci']['risk_ratio'][1]}]  "
              f"(archive 2.407)")

    rep["predictions"] = out
    json.dump(rep, open(OUT / "surrogate_S4_fit.json", "w", encoding="utf-8"), indent=1)
    print(f"[S4] -> {OUT/'surrogate_S4_fit.json'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="S1,S2,S3,S4")
    a = ap.parse_args()
    ph = [x.strip().upper() for x in a.phase.split(",") if x.strip()]
    t0 = time.time()
    if "S1" in ph: phase_S1()
    if "S2" in ph: phase_S2()
    if "S3" in ph: phase_S3()
    if "S4" in ph: phase_S4()
    if "S7" in ph: phase_S7()
    if "S6" in ph: phase_S6()
    if "RHO" in ph: phase_RHO()
    if "S5" in ph: phase_S5()
    if "S2B" in ph: phase_S2B()
    print(f"[done] {OUT}  ({time.time()-t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
