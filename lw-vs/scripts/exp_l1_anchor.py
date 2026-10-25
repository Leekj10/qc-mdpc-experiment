#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""BIKE Level-1 anchor experiments (tier-upgrade gap G2).

At true BIKE Level-1 (r,d,t)=(12323,71,134) the study carrier records zero
failures in 9e6 archived runs; only a <3e-6 non-degradation bound exists, and
the archived offsets were {0,+2,+4} -- the NEGATIVE first-round direction was
never tested.  This script adds three measurable production-scale signals that
do not require the DFR itself to be measurable:

  L1a  first-round decision margin at t=134, computed WITHOUT decoding:
       per-delta flip counts split into true/false, the UPC-tail exchange
       ratios, and the fraction of true-error positions sitting exactly on the
       threshold boundary.  Question: does the knife-edge that defines the
       first-round window at P1' exist identically at production parameters?
  L1b  classic carrier at true t=134: C0 vs FRO-2 vs FRONEG on the same
       (H,e,s), measuring the CONVERGENCE-ITERATION distribution (mean, tail,
       two-round fraction).  Question: does a single -1 in round 1 break
       production-parameter decoding, and what does +2 cost there?
  L1c  spec-exact BIKE-Flip v5.2 ablation: the specification's first-round
       protection term T_1 = ft(S) + delta (p.14) removed (delta1=0) and
       doubled (delta1=2*delta), everything else spec-exact.  Question: is the
       production decoder's own first-round term load-bearing at L1?
  L1d  the surrogate model (exp_surrogate_model.py, S4) applied at t=134 to
       predict the risk ratio there -- a MODEL PREDICTION, labelled as such.
       Implemented in exp_surrogate_model.py after S4; this script only exports
       the feature statistics it needs (L1a output).

Key pool and error construction replicate the archived L1 experiments exactly
(SEED 20260901, param id "L1", group "RAND"); KeyPool generation is
prefix-stable per attempt index, so n_keys=32 contains the archived 16 keys.

Memory note: at r=12323 each key costs ~14 MB of gather matrices, so keep
worker counts low (L1_WORKERS<=6) and key counts <=32.

Run:  python lw-vs/scripts/exp_l1_anchor.py --phase L1a,L1b,L1c
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

from qcmdpc.decoders import build_decoder, make_threshold   # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402

SEED = 20260901
MAX_ITER = 20
L1_WORKERS = int(os.environ.get("L1_WORKERS", "6"))
L1 = {"id": "L1", "r": 12323, "d": 71, "t": 134, "n0": 2}
RAND_SPEC = {"type": "random", "n_keys": 32}
DELTAS = (0, 1, 2, 3, -1)

_POOL_CACHE: dict = {}


def _pool(n_keys):
    key = ("L1rand", n_keys)
    if key not in _POOL_CACHE:
        _POOL_CACHE[key] = KeyPool(SEED, L1, "RAND", {"type": "random", "n_keys": n_keys})
    return _POOL_CACHE[key]


# ------------------------------------------------------------------- L1a
def _work_l1a(job):
    """First-round statistics only; no decoder is constructed."""
    ki, n_err = job
    pool = _pool(RAND_SPEC["n_keys"])
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "RAND", key.key_id, L1, RAND_SPEC, key, None)
    lo, hi = max(1, (L1["d"] + 1) // 2), L1["d"]
    classic = make_threshold({"type": "classic"}, L1["d"], L1["t"], 2 * L1["r"])
    n1 = n0 = 0
    # counts of flips per delta, split true/false, plus boundary occupancy
    cnt = {dl: {"true": 0, "false": 0, "tau_sum": 0} for dl in DELTAS}
    # marginal counts p1(k)/p0(k) for k = tau-2..tau+2 need tau per instance;
    # instead count "how many true-error positions have alpha in {tau1-1,tau1,tau1+1}"
    marg = {k: {"true": 0, "false": 0} for k in (-3, -2, -1, 0, 1, 2, 3)}
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        alpha = key.upc_fast(s0)
        sup = e.astype(bool)
        tau1 = classic(0, int(s0.sum()))
        n1 += int(sup.sum()); n0 += int(sup.size - sup.sum())
        for k in (-3, -2, -1, 0, 1, 2, 3):
            m = alpha >= (tau1 + k)
            marg[k]["true"] += int(m[sup].sum())
            marg[k]["false"] += int(m[~sup].sum())
        for dl in DELTAS:
            tau = int(np.clip(tau1 + dl, lo, hi))
            F = alpha >= tau
            t_in = int(F[sup].sum())
            cnt[dl]["true"] += t_in
            cnt[dl]["false"] += int(F.sum()) - t_in
            cnt[dl]["tau_sum"] += tau
    return ki, n1, n0, cnt, marg


def phase_L1a(n_keys=32, n_err=300) -> None:
    p = OUT / "l1a_firstround_margin.json"
    if p.exists():
        print("[L1a] cached"); return
    print(f"[L1a] first-round margin at true L1 t=134, {n_keys} keys x {n_err} errors (no decoding)")
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=L1_WORKERS) as ex:
        res = list(ex.map(_work_l1a, [(ki, n_err) for ki in range(n_keys)]))
    n1 = sum(r[1] for r in res); n0 = sum(r[2] for r in res)
    cnt = {dl: {k: sum(r[3][dl][k] for r in res) for k in ("true", "false", "tau_sum")}
           for dl in DELTAS}
    marg = {k: {t: sum(r[4][k][t] for r in res) for t in ("true", "false")}
            for k in (-3, -2, -1, 0, 1, 2, 3)}
    n_err_tot = n_keys * n_err
    p1 = {str(k): marg[k]["true"] / n1 for k in marg}
    p0 = {str(k): marg[k]["false"] / n0 for k in marg}
    # exchange ratios: every deferred true-error flip per avoided false flip
    model = {}
    for dl in DELTAS:
        if dl == 0:
            continue
        d_true = (marg[0]["true"] - marg[dl]["true"]) / n_err_tot
        d_false = (marg[0]["false"] - marg[dl]["false"]) / n_err_tot
        model[str(dl)] = {"deferred_true_per_instance": d_true,
                          "avoided_false_per_instance": d_false,
                          "rho": (d_false / d_true) if d_true > 0 else float("inf")}
    out = {"r": L1["r"], "d": L1["d"], "t": L1["t"], "n_keys": n_keys,
           "errors_per_key": n_err, "trials": n_err_tot,
           "true_flag_positions": n1, "false_positions": n0,
           "marginal_true_p": p1, "marginal_false_p": p0,
           "per_delta": {str(dl): cnt[dl] for dl in DELTAS},
           "model_rho": model,
           "note": "p1/p0 are tail probabilities P(UPC >= tau1+k) at true-error "
                   "and non-error positions; rho = avoided false flips per "
                   "deferred true flip, the same exchange ratio as P1'.",
           "wall_seconds": round(time.time() - t0, 1)}
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    for dl in (1, 2, 3, -1):
        m = model[str(dl)]
        print(f"    delta {dl:+d}: deferred_true/inst {m['deferred_true_per_instance']:.3f}  "
              f"avoided_false/inst {m['avoided_false_per_instance']:.3f}  rho={m['rho']:.3f}")
    print(f"    ({time.time()-t0:.0f}s)")


# ------------------------------------------------------------------- L1b
def _work_l1b(job):
    ki, n_err = job
    pool = _pool(RAND_SPEC["n_keys"])
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "RAND", key.key_id, L1, RAND_SPEC, key, None)
    decs = {dl: build_decoder(f"l1{dl}", {"algo": "bf_parallel",
                                          "threshold": {"type": "offset",
                                                        "base": {"type": "classic"},
                                                        "offsets": [dl, 0]},
                                          "max_iter": MAX_ITER}, L1["d"], L1["t"], L1["r"])
            for dl in (0, 2, -1)}
    fail = {dl: 0 for dl in decs}
    iters = {dl: np.zeros(n_err, dtype=np.int16) for dl in decs}
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        for dl, d in decs.items():
            r = d(key, s0.copy())
            fail[dl] += 0 if r.success else 1
            iters[dl][eid] = r.n_iters_run
    return ki, fail, iters


def phase_L1b(n_keys=32, n_err=1000) -> None:
    p = OUT / "l1b_classic_carrier.json"
    if p.exists():
        print("[L1b] cached"); return
    print(f"[L1b] classic carrier at true L1 t=134: C0 / FRO-2 / FRONEG, "
          f"{n_keys} keys x {n_err} errors")
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=L1_WORKERS) as ex:
        res = list(ex.map(_work_l1b, [(ki, n_err) for ki in range(n_keys)]))
    out = {"r": L1["r"], "d": L1["d"], "t": L1["t"], "n_keys": n_keys,
           "errors_per_key": n_err, "trials": n_keys * n_err, "arms": {}}
    for dl, nm in ((0, "C0"), (2, "FRO-2"), (-1, "FRONEG")):
        f = sum(r[1][dl] for r in res)
        it = np.concatenate([r[2][dl] for r in res])
        out["arms"][nm] = {
            "failures": int(f), "dfr": f / (n_keys * n_err),
            "upper95": (3.0 / (n_keys * n_err)) if f == 0 else None,
            "mean_iters": float(it.mean()), "p99_iters": int(np.percentile(it, 99)),
            "two_round_fraction": float((it <= 2).mean()),
            "three_round_fraction": float((it <= 3).mean()),
            "per_key_failures": [int(r[1][dl]) for r in res],
            "per_key_mean_iters": [float(r[2][dl].mean()) for r in res]}
        a = out["arms"][nm]
        print(f"    {nm:7s} {a['failures']:4d}/{out['trials']}  mean_iters={a['mean_iters']:.3f}  "
              f"2-round={a['two_round_fraction']:.4f}  3-round={a['three_round_fraction']:.4f}")
    out["wall_seconds"] = round(time.time() - t0, 1)
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)   # save FIRST
    for nm in ("C0", "FRO-2", "FRONEG"):
        a = out["arms"][nm]
        print(f"    {nm:7s} {a['failures']:4d}/{out['trials']}  mean_iters={a['mean_iters']:.3f}  "
              f"2-round={a['two_round_fraction']:.4f}  3-round={a['three_round_fraction']:.4f}")


# ------------------------------------------------------------------- L1c
def _bike_flip_d1(key, s0, a, b, delta, nb_iter, d1):
    """Faithful copy of qcmdpc.bikeflip.bike_flip with the ROUND-1 term
    T_1 = ft(S0) + d1 decoupled from the delta used in later rounds.
    At d1 == delta it must reproduce the frozen decoder exactly (checked in
    phase_L1c before any ablation number is produced)."""
    import math
    from qcmdpc.decoders import TrajectoryResult
    d = key.d
    lo, hi = (d + 1) // 2, d
    s = np.asarray(s0).copy()
    S0 = int(s.sum())

    def ft(S):
        return a * S + b

    fS0 = ft(S0)
    Ti = [None] * (nb_iter + 1)
    for i in range(1, nb_iter + 1):
        if i == 1:
            Ti[i] = fS0 + d1
        elif i == 2:
            Ti[i] = (2 * fS0 + lo) / 3 + delta
        elif i == 3:
            Ti[i] = (fS0 + 2 * lo) / 3 + delta
        else:
            Ti[i] = lo + delta
    res = TrajectoryResult("BIKE-Flip-d1", False, None, 0)
    success_at = None
    for i in range(1, nb_iter + 1):
        S = int(s.sum())
        if S == 0:
            if success_at is None:
                success_at = i - 1
            res.syndrome_weights.append(0)
            res.flip_counts.append(0)
            res.n_iters_run = i
            continue
        T = int(np.clip(math.ceil(max(ft(S), Ti[i])), lo, hi))
        alpha = key.upc_fast(s)
        flips = np.nonzero(alpha >= T)[0]
        for p in flips:
            s = key.flip(s, int(p))
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(int(flips.size))
        res.n_iters_run = i
        if int(s.sum()) == 0 and success_at is None:
            success_at = i
    res.success = int(s.sum()) == 0
    res.iters_to_success = success_at
    return res


def _work_l1c(job):
    ki, n_err, d1, d_rest = job
    from qcmdpc.bikeflip import BIKEFLIP_OFFICIAL, bike_flip
    pool = _pool(RAND_SPEC["n_keys"])
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "RAND", key.key_id, L1, RAND_SPEC, key, None)
    off = BIKEFLIP_OFFICIAL[(12323, 71, 134)]
    nb, dl, a, b = off["nb_iter"], off["delta"], off["a"], off["b"]
    fail = 0
    iters = np.zeros(n_err, dtype=np.int16)
    agree = True
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        r = _bike_flip_d1(key, s0, a, b, d_rest, nb, d1)
        if d1 == dl and d_rest == dl:     # equivalence gate against the frozen decoder
            r0 = bike_flip(key, s0, a, b, dl, nb)
            if r0.success != r.success or r0.n_iters_run != r.n_iters_run:
                agree = False
        fail += 0 if r.success else 1
        # convergence = first iteration with zero syndrome; if the syndrome never
        # reaches zero, record nb_iter (the budget) as the censoring value
        iters[eid] = (r.iters_to_success if r.iters_to_success is not None else nb_iter)
    return ki, fail, iters, agree


def phase_L1c(n_keys=16, n_err=500) -> None:
    p = OUT / "l1c_bikeflip_firstround_ablation.json"
    if p.exists():
        print("[L1c] cached"); return
    from qcmdpc.bikeflip import BIKEFLIP_OFFICIAL
    off = BIKEFLIP_OFFICIAL[(12323, 71, 134)]
    dl = off["delta"]
    nb_iter = off["nb_iter"]
    print(f"[L1c] BIKE-Flip v5.2 first-round ablation at L1: "
          f"delta1 in {{0, {dl}, {2*dl}}}, {n_keys} keys x {n_err} errors")
    t0 = time.time()
    out = {"r": 12323, "d": 71, "t": 134, "n_keys": n_keys, "errors_per_key": n_err,
           "spec_delta": dl, "arms": {}}
    for d1, d_rest, nm in ((dl, dl, "spec"),
                           (0, dl, "no_first_round_delta"),
                           (2 * dl, dl, "double_first_round_delta"),
                           (dl, 0, "first_round_delta_only")):
        with ProcessPoolExecutor(max_workers=L1_WORKERS) as ex:
            res = list(ex.map(_work_l1c, [(ki, n_err, d1, d_rest) for ki in range(n_keys)]))
        f = sum(r[1] for r in res)
        it = np.concatenate([r[2] for r in res])
        out["arms"][nm] = {"d1": d1, "d_rest": d_rest, "failures": int(f),
                           "dfr": f / (n_keys * n_err),
                           "converged_fraction": float((it < nb_iter).mean()),
                           "mean_conv_iters": float(it[it < nb_iter].mean()) if (it < nb_iter).any() else None,
                           "two_round_fraction": float((it <= 2).mean()),
                           "three_round_fraction": float((it <= 3).mean()),
                           "per_key_conv_iters": [float(r[2].mean()) for r in res]}
        if nm == "spec":
            out["equivalence_gate_vs_frozen_bikeflip"] = bool(all(r[3] for r in res))
        a = out["arms"][nm]
        print(f"    {nm:24s} {a['failures']:3d}/{n_keys*n_err}  "
              f"conv={a['converged_fraction']:.4f}  2-round={a['two_round_fraction']:.4f}  "
              f"3-round={a['three_round_fraction']:.4f}  "
              f"mean_conv_iters={a['mean_conv_iters']}")
    print(f"    equivalence gate vs frozen bike_flip: "
          f"{'PASS' if out.get('equivalence_gate_vs_frozen_bikeflip') else '*** FAIL ***'}")
    out["wall_seconds"] = round(time.time() - t0, 1)
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="L1a,L1b,L1c")
    ap.add_argument("--keys", type=int, default=None)
    a = ap.parse_args()
    ph = [x.strip().upper() for x in a.phase.split(",") if x.strip()]
    t0 = time.time()
    if "L1A" in ph: phase_L1a(n_keys=a.keys or 32)
    if "L1B" in ph: phase_L1b(n_keys=a.keys or 32)
    if "L1C" in ph: phase_L1c(n_keys=min(a.keys or 16, 16))
    print(f"[done] {OUT}  ({time.time()-t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
