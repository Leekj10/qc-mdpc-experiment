#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tier-upgrade experiments: push the three tier-limiting gaps of the paper.

Gaps (from the 2026-10-07 self-assessment):
  G1 (red)    no theorem / no quantitative model / no extrapolation apparatus
  G2 (red)    zero gain at production parameters (BIKE L1: 0 failures in 9e6)
  G3 (yellow) the mechanism window sits in the waterfall (DFR 1e-3..1e-4)

This script hosts the phases that can be pre-registered tightly.  Each phase
writes its frozen protocol to results/tier_upgrade/protocol_*.json BEFORE the
first decode of that phase is run (the offset-rule convention: the protocol
file's mtime precedes the result file's).

Phase T90   t=90 at P1' on the SAME 92-key formal pool as the headline result,
            C0 vs FRO-2, chunked, with a pre-registered sample-size stopping
            rule.  Purpose: G3 -- extend the measured band one order of
            magnitude below the paper's t=92 point, on the same keys.
            (The earlier plan in exp_lowdfr_model.py phase A used a fresh
            150-key pool; same-pool is strictly better for a scaling claim,
            so the sampling budget goes here instead.)

Other phases in this file:
  BUDGET  max_iter in {4,6,8,12} at P1' main pool, C0 vs FRO-2 (G3) -- implemented,
          with its own embedded protocol (protocol_BUDGET.json), but NOT run in the
          2026-10-07 session.
  P1PP    (12323,71,t*) production-code-parameter point (G2) -- run; t* = 172 from a
          bracketed bisection (protocol_P1PP.json amendments 1-3).

Run:  python lw-vs/scripts/exp_tier_upgrade.py --phase T90
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

from qcmdpc.decoders import build_decoder, make_threshold          # noqa: E402
from qcmdpc.generators import (KeyPool, make_error_generator,      # noqa: E402
                               _child_seed)
from qcmdpc.stats import (wilson_upper, cluster_bootstrap_paired,  # noqa: E402
                          sign_test_paired)                        # noqa: E402

SEED = 20260901
MAX_ITER = 20
N_WORKERS = int(os.environ.get("TU_WORKERS", "11"))

# The headline P1' pool: KeyPool(SEED, P1prime, "G0", {random, 100 keys}),
# keys 8..99 (fresh_from = 8) -- identical to exp_round_controls.phase1 G0.
P1 = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
G0_SPEC = {"type": "random", "n_keys": 100}
FRESH_FROM = 8

# ---------------------------------------------------------------- phase T90
T90 = 90
T90_ARMS = {"C0": [0], "FRO-2": [2, 0]}
T90_CHUNK = 4000          # errors per key per chunk
T90_TARGET_C0_FAIL = 120  # stop when C0 failures reach this ...
T90_MAX_ERR = 100_000     # ... or errors/key reaches this, whichever first


_POOL_CACHE: dict = {}


def _pool():
    """KeyPool build is expensive (100 keys x (d x r) gather matrices); cache it
    per worker process -- jobs are one key each and would otherwise rebuild it."""
    if "pool" not in _POOL_CACHE:
        _POOL_CACHE["pool"] = KeyPool(SEED, P1, "G0", G0_SPEC)
    return _POOL_CACHE["pool"]


def _decoder(offsets, d, t, r):
    return build_decoder("X", {"algo": "bf_parallel",
                               "threshold": {"type": "offset",
                                             "base": {"type": "classic"},
                                             "offsets": offsets},
                               "max_iter": MAX_ITER}, d, t, r)


def _work_t90(job):
    """One key, one chunk of error ids [lo, hi), all arms on the same (H,e,s)."""
    ki, lo, hi, t = job
    pool = _pool()
    key = pool.keys[ki]
    param = {"id": "P1prime", "r": P1["r"], "d": P1["d"], "t": t, "n0": 2}
    gen = make_error_generator(SEED, "G0", key.key_id, param, G0_SPEC, key, None)
    decs = {n: _decoder(offs, P1["d"], t, P1["r"]) for n, offs in T90_ARMS.items()}
    fails = {n: 0 for n in T90_ARMS}
    for eid in range(lo, hi):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        for n, d in decs.items():
            if not d(key, s.copy()).success:
                fails[n] += 1
    return ki, fails


def _run_chunks(t, err_before, err_after, workers):
    """Run error ids [err_before, err_after) for every key in the pool."""
    pool = _pool()
    idxs = list(range(FRESH_FROM, len(pool.keys)))
    jobs = [(ki, err_before, err_after, t) for ki in idxs]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(_work_t90, jobs)), idxs


def _accumulate(state_path, res, idxs, err_lo, err_hi):
    """Merge one chunk into the checkpoint state."""
    if state_path.exists():
        st = json.load(open(state_path, encoding="utf-8"))
    else:
        st = {"t": T90, "arms": {n: [0] * len(idxs) for n in T90_ARMS},
              "errors_done": 0, "chunks": [], "pool": "G0 keys 8..99"}
    pos = {ki: j for j, ki in enumerate(idxs)}
    for ki, fails in res:
        for n in T90_ARMS:
            st["arms"][n][pos[ki]] += fails[n]
    st["errors_done"] += (err_hi - err_lo)
    st["chunks"].append({"lo": err_lo, "hi": err_hi})
    json.dump(st, open(state_path, "w", encoding="utf-8"), indent=1)
    return st


def _report(st):
    per0 = np.array(st["arms"]["C0"], dtype=np.int64)
    per2 = np.array(st["arms"]["FRO-2"], dtype=np.int64)
    e = st["errors_done"]
    n_keys = len(per0)
    trials = n_keys * e
    c0, f2 = int(per0.sum()), int(per2.sum())
    out = {"t": st["t"], "n_keys": n_keys, "errors_per_key": e, "trials": trials,
           "c0_failures": c0, "c0_dfr": c0 / trials if trials else None,
           "c0_upper95": wilson_upper(c0, trials),
           "fro2_failures": f2, "fro2_dfr": f2 / trials if trials else None}
    if c0 > 0 and f2 > 0:
        boot = cluster_bootstrap_paired(per0, per2, e, B=10000, seed=20260905)
        sg = sign_test_paired(per0, per2)
        out.update({"rr": boot["point"]["risk_ratio"],
                    "rr_ci95": boot["ci"]["risk_ratio"],
                    "rr_excludes_1": boot["rr_excludes_1"],
                    "sign_test": sg})
    elif c0 > 0 and f2 == 0:
        # Treatment arm has zero failures: the bootstrap CI would be truncated
        # (replicates with t_sums==0 dropped).  Report the rule-of-three bound
        # instead: p2 <= 3/trials (one-sided 95%), hence
        # RR = p0/p2 >= (c0/trials) / (3/trials) = c0/3.
        sg = sign_test_paired(per0, per2)
        out.update({"rr": None,
                    "fro2_upper95": 3.0 / trials,
                    "rr_lower_bound95": c0 / 3.0,
                    "rr_bound_note": "FRO-2 zero failures: RR >= C0_failures/3 "
                                     "(rule of three, one-sided 95%)",
                    "sign_test": sg})
    out["per_key_c0"] = per0.tolist()
    out["per_key_fro2"] = per2.tolist()
    return out


def phase_T90(smoke: bool = False) -> None:
    prot_path = OUT / "protocol_T90.json"
    state_path = OUT / "state_T90.json"
    if not prot_path.exists():
        proto = {
            "phase": "T90",
            "purpose": "G3: extend the measured DFR band one order of magnitude "
                       "below the headline point, on the SAME 92-key formal pool.",
            "frozen_before": "first decode of this phase (see file mtime)",
            "hypothesis": "RR(FRO-2 vs C0) at t=90 is larger than the t=92 value "
                          "4.15 and its 95% key-clustered CI excludes 1.",
            "design": {
                "pool": "KeyPool(20260901, P1prime, 'G0', {random,100}) keys 8..99, "
                        "identical to exp_round_controls.phase1 G0 (the headline pool)",
                "error_generator": "make_error_generator(20260901,'G0',key_id,"
                                   "param{t=90},'G0'-spec,key,None), error ids "
                                   "0..E-1, same error ids for every arm",
                "arms": {"C0": [0], "FRO-2": [2, 0]},
                "decoder": "bf_parallel, classic threshold, max_iter=20 "
                           "(identical carrier to the headline result)",
                "chunking": f"{T90_CHUNK} errors/key per chunk; state checkpointed "
                            "after each chunk; arms added per chunk on identical "
                            "instances, so pairing is exact",
            },
            "stopping_rule": {
                "target": f"stop when C0 failures >= {T90_TARGET_C0_FAIL}",
                "cap": f"or errors/key = {T90_MAX_ERR}, whichever comes first",
                "note": "sample-size stopping rule, NOT significance-based: the "
                        "decision rule is fixed in advance and never looks at RR.",
                "after_cap": "if the cap is reached below target, report the "
                             "achieved CI as-is; do not extend the sample.",
            },
            "analysis": {
                "primary": "cluster_bootstrap_paired(per_key C0, per_key FRO-2, "
                           "errors_per_key, B=10000, seed=20260905)",
                "secondary": ["sign_test_paired", "wilson_upper(C0)"],
                "reported": ["C0 DFR + upper95", "FRO-2 DFR", "RR + CI95", "sign test"],
            },
            "falsification": "CI includes 1, or RR <= 4.15, falsifies the "
                             "'strengthens toward lower DFR' hypothesis; either way "
                             "the result is reported as measured.",
            "prior_expectation": "t=90 saw 1/30000 C0 failures on a different "
                                 "30-key pool; target 120 failures at 92 keys "
                                 "implies ~40k errors/key if DFR ~3.3e-5.",
            "written_by": "Claude (session 2026-10-07) before any t=90 decode",
        }
        json.dump(proto, open(prot_path, "w", encoding="utf-8"), indent=1)
        print(f"[T90] protocol frozen -> {prot_path}")

    if smoke:
        pool = _pool()
        ki = FRESH_FROM
        res, idxs = _run_chunks(T90, 0, 20, min(4, N_WORKERS))
        st = _accumulate(state_path.with_suffix(".smoke.json"), res, idxs, 0, 20)
        print("[T90 smoke]", _report(st))
        return

    e_done = 0
    while True:
        if state_path.exists():
            st = json.load(open(state_path, encoding="utf-8"))
            e_done = st["errors_done"]
            c0 = int(np.sum(st["arms"]["C0"]))
        else:
            c0 = 0
        if c0 >= T90_TARGET_C0_FAIL or e_done >= T90_MAX_ERR:
            break
        lo, hi = e_done, min(e_done + T90_CHUNK, T90_MAX_ERR)
        t0 = time.time()
        res, idxs = _run_chunks(T90, lo, hi, N_WORKERS)
        st = _accumulate(state_path, res, idxs, lo, hi)
        rep = _report(st)
        rr_txt = (f"{rep['rr']:.3f} [{rep['rr_ci95'][0]:.3f}, {rep['rr_ci95'][1]:.3f}]"
                  if "rr" in rep else "undefined")
        print(f"[T90] errors/key={rep['errors_per_key']:6d}  "
              f"C0 {rep['c0_failures']:4d}/{rep['trials']} DFR={rep['c0_dfr']:.3e}  "
              f"FRO-2 {rep['fro2_failures']:3d}  RR={rr_txt}  "
              f"({time.time()-t0:.0f}s/chunk)", flush=True)
    rep = _report(st)
    with open(OUT / "phase_T90.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print(f"[T90] done -> {OUT/'phase_T90.json'}")


# --------------------------------------------------------------------------
# phase BUDGET: iteration-budget truncation axis at P1' t=92, main pool.
# At t=92 the C0 DFR is 1.02e-3 with a 20-iteration budget; truncating the
# budget raises it into the 1e-2..1e-1 range, giving a second axis on which the
# decoder's failure pressure varies while the error model and the pool are
# fixed.  The archived tier-3 ablation (results/q2_iterablation) used a
# different, smaller pool; this rerun puts the axis on the headline pool with
# paired instances, and yields high-event per-key data for the per-key
# predictor test (surrogate model).
# --------------------------------------------------------------------------
BUDGETS = (4, 6, 8, 12)
BUDGET_E_PER_KEY = 3000


def _work_budget(job):
    ki, B = job
    pool = _pool()
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "G0", key.key_id, P1, G0_SPEC, key, None)
    decs = {"C0": build_decoder("C0", {"algo": "bf_parallel",
                                       "threshold": {"type": "classic"},
                                       "max_iter": B}, P1["d"], P1["t"], P1["r"]),
            "FRO-2": build_decoder("FRO-2", {"algo": "bf_parallel",
                                             "threshold": {"type": "offset",
                                                           "base": {"type": "classic"},
                                                           "offsets": [2, 0]},
                                             "max_iter": B}, P1["d"], P1["t"], P1["r"])}
    fails = {"C0": 0, "FRO-2": 0}
    it_acc = {"C0": 0, "FRO-2": 0}
    for eid in range(BUDGET_E_PER_KEY):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        for n, d in decs.items():
            r = d(key, s.copy())
            if not r.success:
                fails[n] += 1
            it_acc[n] += r.n_iters_run
    return ki, fails, it_acc


def phase_BUDGET() -> None:
    prot = OUT / "protocol_BUDGET.json"
    if not prot.exists():
        json.dump({
            "phase": "BUDGET",
            "purpose": "G3/G1: a second axis where C0's measurable DFR varies at "
                       "fixed pool, fixed t, fixed error model; also high-event "
                       "per-key data for the per-key predictor.",
            "design": {"pool": "main G0 keys 8..99 (headline pool)",
                       "instances": "error ids 0..2999 at t=92 (same as headline)",
                       "arms": {"C0": [0], "FRO-2": [2, 0]},
                       "budgets": list(BUDGETS),
                       "note": "budget 20 already archived (headline result)"},
            "analysis": {"primary": "RR + key-clustered CI95 per budget",
                         "secondary": ["C0 DFR", "mean iters", "per-key vectors"]},
            "expectation": "the archived tier-3 ablation (different pool) saw RR "
                           "1.72/2.15/3.00 at budgets 7/10/20; if the benefit comes "
                           "from protecting round 1 so that later rounds act on a "
                           "cleaner state, RR should increase with the budget.",
            "written_by": "Claude (session 2026-10-07) before this phase was run",
        }, open(prot, "w", encoding="utf-8"), indent=1)
        print(f"[BUDGET] protocol frozen -> {prot}")
    for B in BUDGETS:
        p = OUT / f"budget_B{B}.json"
        if p.exists():
            print(f"[BUDGET] B={B} cached"); continue
        print(f"[BUDGET] B={B} at P1' main pool, {BUDGET_E_PER_KEY} errors/key")
        t0 = time.time()
        pool = _pool()
        idxs = list(range(FRESH_FROM, len(pool.keys)))
        with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
            res = list(ex.map(_work_budget, [(ki, B) for ki in idxs]))
        per0 = np.array([r[1]["C0"] for r in sorted(res)], dtype=np.int64)
        per2 = np.array([r[1]["FRO-2"] for r in sorted(res)], dtype=np.int64)
        n = len(idxs) * BUDGET_E_PER_KEY
        boot = cluster_bootstrap_paired(per0, per2, BUDGET_E_PER_KEY, B=10000,
                                        seed=20260905)
        it0 = sum(r[2]["C0"] for r in res) / n
        it2 = sum(r[2]["FRO-2"] for r in res) / n
        cell = {"budget": B, "trials": n, "c0_failures": int(per0.sum()),
                "c0_dfr": float(per0.sum() / n), "c0_upper95": wilson_upper(int(per0.sum()), n),
                "fro2_failures": int(per2.sum()), "fro2_dfr": float(per2.sum() / n),
                "rr": boot["point"]["risk_ratio"], "rr_ci95": boot["ci"]["risk_ratio"],
                "rr_excludes_1": boot["rr_excludes_1"],
                "sign_test": sign_test_paired(per0, per2),
                "mean_iters_c0": it0, "mean_iters_fro2": it2,
                "per_key_c0": per0.tolist(), "per_key_fro2": per2.tolist(),
                "wall_seconds": round(time.time() - t0, 1)}
        json.dump(cell, open(p, "w", encoding="utf-8"), indent=1)
        print(f"    B={B}: C0 {cell['c0_failures']}/{n} DFR={cell['c0_dfr']:.3e}  "
              f"FRO-2 {cell['fro2_failures']}  RR={cell['rr']:.3f} "
              f"[{cell['rr_ci95'][0]:.3f}, {cell['rr_ci95'][1]:.3f}]  "
              f"it {it0:.2f}->{it2:.2f}  ({cell['wall_seconds']}s)")


# --------------------------------------------------------------------------
# phase P1PP: production code parameters, error weight raised into the
# measurable band.  (r,d) = (12323,71) is EXACTLY BIKE Level-1; only t is
# calibrated upward from the production value 134 so that C0's DFR becomes
# resolvable.  Keys are the archived L1 pool (KeyPool(20260901, "L1", "RAND"))
# -- key generation does not depend on t, so the first 16 keys coincide with
# the archived BIKE-Flip L1 comparison.  Per-instance first-round features are
# logged so the P1' surrogate can be applied here as a cross-code validation.
# --------------------------------------------------------------------------
L1S_KEYS = 32
L1S_T_CAND = (150, 160, 170, 180, 195, 210, 230)
L1S_E_CAL = 200
L1S_E_MAIN = 1500
L1S_ARMS = {"C0": 0, "FRO-2": 2, "FRONEG": -1}


def _l1s_param(t):
    return {"id": "L1", "r": 12323, "d": 71, "t": t, "n0": 2}


def _l1s_pool(t, n_keys):
    """Pool build at r=12323 costs ~14 MB/key; cache it per worker process."""
    key = ("l1s", t, n_keys)
    if key not in _POOL_CACHE:
        p = _l1s_param(t)
        _POOL_CACHE[key] = KeyPool(SEED, p, "RAND", {"type": "random", "n_keys": n_keys})
    return _POOL_CACHE[key]


def _work_l1s(job):
    ki, t, n_err, arms, collect_features = job
    p = _l1s_param(t)
    pool = _l1s_pool(t, L1S_KEYS)
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "RAND", key.key_id, p, {"type": "random",
                                                             "n_keys": L1S_KEYS}, key, None)
    lo, hi = max(1, (71 + 1) // 2), 71
    decs = {nm: build_decoder(nm, {"algo": "bf_parallel",
                                   "threshold": {"type": "offset",
                                                 "base": {"type": "classic"},
                                                 "offsets": [dl, 0]},
                                   "max_iter": MAX_ITER}, 71, t, 12323)
            for nm, dl in arms.items()}
    fails = {nm: 0 for nm in arms}
    it_acc = {nm: 0 for nm in arms}
    fail_vec = {nm: np.zeros(n_err, dtype=np.uint8) for nm in arms}
    feats = None
    if collect_features:
        from exp_surrogate_model import first_round_features
        classic = make_threshold({"type": "classic"}, 71, t, 2 * 12323)
        dls = tuple(arms.values())
        feats = {"deltas": dls,
                 "nflip": np.zeros((n_err, len(dls)), dtype=np.int32),
                 "n_true": np.zeros((n_err, len(dls)), dtype=np.int32),
                 "n_false": np.zeros((n_err, len(dls)), dtype=np.int32),
                 "w1": np.zeros((n_err, len(dls)), dtype=np.int32)}
    for eid in range(n_err):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        if collect_features:
            alpha = key.upc_fast(s)
            tau1 = classic(0, int(s.sum()))
            f = first_round_features(key, e, s, alpha, tau1, tuple(arms.values()), lo, hi)
            for j, dl in enumerate(arms.values()):
                for k in ("nflip", "n_true", "n_false", "w1"):
                    feats[k][eid, j] = f[dl][k]
        for nm, d in decs.items():
            r = d(key, s.copy())
            if not r.success:
                fails[nm] += 1
                fail_vec[nm][eid] = 1
            it_acc[nm] += r.n_iters_run
    return ki, fails, it_acc, feats, fail_vec


def phase_P1PP(cal_only: bool = False) -> None:
    prot = OUT / "protocol_P1PP.json"
    if not prot.exists():
        json.dump({
            "phase": "P1PP",
            "purpose": "G2: a measurable operating point at EXACTLY the BIKE "
                       "Level-1 code parameters (r,d)=(12323,71); only the error "
                       "weight t is raised from the production 134 into the "
                       "measurable band. Keys are the archived L1 pool.",
            "calibration_rule": f"C0 only, 6 keys x {L1S_E_CAL} errors at t in "
                                f"{list(L1S_T_CAND)}; choose the t whose C0 DFR lands "
                                "in [1e-4,1e-2], closest to 1e-3; if none qualifies, "
                                "report the closest and DO NOT extend the scan beyond "
                                "the candidate list without a new amendment.",
            "main_run": {"keys": L1S_KEYS, "errors_per_key": L1S_E_MAIN,
                         "arms": {"C0": [0], "FRO-2": [2,0], "FRONEG": [-1,0]},
                         "features": "per-instance first-round features logged for the "
                                     "P1' surrogate cross-code validation"},
            "analysis": "RR + key-clustered CI95 per arm vs C0; mean iters; "
                        "surrogate prediction in exp_surrogate_model phase S5.",
            "written_by": "Claude (session 2026-10-07) before this phase ran",
        }, open(prot, "w", encoding="utf-8"), indent=1)
        print(f"[P1PP] protocol frozen -> {prot}")

    cal_path = OUT / "p1pp_calibration.json"
    if cal_path.exists():
        cal = json.load(open(cal_path, encoding="utf-8"))
        chosen = cal["chosen_t"]
        print(f"[P1PP] calibration cached, chosen t={chosen}")
    else:
        cal = {"candidates": [], "rule": "DFR in [1e-4,1e-2] closest to 1e-3"}
        for t in L1S_T_CAND:
            t0 = time.time()
            with ProcessPoolExecutor(max_workers=min(N_WORKERS, 4)) as ex:
                res = list(ex.map(_work_l1s, [(ki, t, L1S_E_CAL, {"C0": 0}, False)
                                              for ki in range(6)]))
            n = 6 * L1S_E_CAL
            c0 = sum(r[1]["C0"] for r in res)
            row = {"t": t, "t_over_r": t / 12323, "trials": n, "c0_failures": c0,
                   "c0_dfr": c0 / n, "seconds": round(time.time() - t0, 1)}
            cal["candidates"].append(row)
            print(f"    calib t={t}: C0 {c0}/{n} DFR={c0/n:.3e} ({row['seconds']}s)", flush=True)
        ok = [r for r in cal["candidates"] if 1e-4 <= r["c0_dfr"] <= 1e-2]
        best = (min(ok, key=lambda r: abs(r["c0_dfr"] - 1e-3)) if ok
                else min(cal["candidates"], key=lambda r: abs(r["c0_dfr"] - 1e-3)))
        cal["chosen_t"] = best["t"]
        cal["in_band"] = bool(ok)
        json.dump(cal, open(cal_path, "w", encoding="utf-8"), indent=1)
        chosen = best["t"]
        print(f"    chosen t={chosen} (in band: {cal['in_band']})")

    if cal_only:
        print("[P1PP] calibration-only run finished")
        return
    p = OUT / "p1pp_main.json"
    if p.exists():
        print("[P1PP] main cached"); return
    print(f"[P1PP] main run: (12323,71,t={chosen}), {L1S_KEYS} keys x {L1S_E_MAIN} "
          f"errors, arms {list(L1S_ARMS)}")
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, 5)) as ex:
        res = list(ex.map(_work_l1s, [(ki, chosen, L1S_E_MAIN, L1S_ARMS, True)
                                      for ki in range(L1S_KEYS)]))
    res.sort(key=lambda r: r[0])
    n = L1S_KEYS * L1S_E_MAIN
    out = {"r": 12323, "d": 71, "t": chosen, "n_keys": L1S_KEYS,
           "errors_per_key": L1S_E_MAIN, "trials": n, "arms": {}}
    per0 = np.array([r[1]["C0"] for r in res], dtype=np.int64)
    for nm in L1S_ARMS:
        pera = np.array([r[1][nm] for r in res], dtype=np.int64)
        cell = {"failures": int(pera.sum()), "dfr": float(pera.sum() / n),
                "upper95": wilson_upper(int(pera.sum()), n),
                "mean_iters": sum(r[2][nm] for r in res) / n,
                "per_key_failures": pera.tolist()}
        if nm != "C0" and per0.sum() > 0 and pera.sum() > 0:
            boot = cluster_bootstrap_paired(per0, pera, L1S_E_MAIN, B=10000,
                                            seed=20260905)
            cell.update({"rr": boot["point"]["risk_ratio"],
                         "rr_ci95": boot["ci"]["risk_ratio"],
                         "rr_excludes_1": boot["rr_excludes_1"],
                         "sign_test": sign_test_paired(per0, pera)})
        out["arms"][nm] = cell
        a = cell
        rr_txt = (f"RR={a['rr']:.3f} [{a['rr_ci95'][0]:.3f}, {a['rr_ci95'][1]:.3f}]"
                  if "rr" in a else "RR undefined")
        print(f"    {nm:7s} {a['failures']:4d}/{n}  DFR={a['dfr']:.3e}  "
              f"iters={a['mean_iters']:.2f}  {rr_txt}")
    # persist per-instance features + failures for the surrogate cross-code check
    npz = {"deltas": np.array([L1S_ARMS[n] for n in L1S_ARMS], dtype=np.int32),
           "keys": np.array([r[0] for r in res], dtype=np.int32),
           "r": np.array([12323]), "d": np.array([71]), "t": np.array([chosen]),
           "e_per_key": np.array([L1S_E_MAIN])}
    for k in ("nflip", "n_true", "n_false", "w1"):
        npz[k] = np.stack([r[3][k] for r in res])
    for nm, dl in L1S_ARMS.items():
        npz[f"fail_{dl}"] = np.stack([r[4][nm] for r in res])
    np.savez_compressed(OUT / "p1pp_features.npz", **npz)
    out["wall_seconds"] = round(time.time() - t0, 1)
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    print(f"[P1PP] -> {p}  ({out['wall_seconds']}s)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="T90")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--cal-only", action="store_true")
    a = ap.parse_args()
    ph = [x.strip().upper() for x in a.phase.split(",") if x.strip()]
    t0 = time.time()
    if "T90" in ph:
        phase_T90(smoke=a.smoke)
    if "BUDGET" in ph:
        phase_BUDGET()
    if "P1PP" in ph:
        phase_P1PP(cal_only=a.cal_only)
    print(f"[done] {OUT}  ({time.time()-t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
