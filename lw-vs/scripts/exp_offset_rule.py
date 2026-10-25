#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Prespecified first-round offset selection rule, validated at a held-out point.

Motivation
----------
The study's weakest point is that FRO-2 (a first-round +2 offset) could be read as
an empirical tune for one calibrated operating point. This script removes that
reading by (a) fixing a selection RULE a priori, (b) applying it once at a work
point P4 that has never been used anywhere in this project, and (c) validating the
rule's output on a fresh key sample at P4.

The rule is not a search over decoder performance. It is computed from first-round
UPC tail masses only, exactly the A_1/A_0 quantities of the paper's local model,
and it never runs a decoding experiment at P4 to choose its own answer.

FROZEN PROTOCOL (written to results/offset_rule/protocol.json before any run)
-----------------------------------------------------------------------------
Rule.  Let tau_1 be the CLASSIC first-round threshold and U the first-round UPC
vector. For c in {1,0} (error / non-error positions) let q_c(tau) be the tail mass
of class c at tau and A_c(delta) = q_c(tau_1+delta)/q_c(tau_1). The offset buys
avoided incorrect flips at the price of deferred correct flips, so we score the
exchange rate directly:
    rho(delta) = [ (n - t) * (q_0(tau_1) - q_0(tau_1+delta)) ]
               / [    t    * (q_1(tau_1) - q_1(tau_1+delta)) ]
        = incorrect flips avoided per correct flip deferred,
and choose
    delta* = argmax_{delta in {1,2,3,4}} rho(delta),  ties to the smaller delta.
No free numerical parameter. (A first formulation, argmax A_1/A_0 per unit delta,
was discarded before the real run because A_0 -> 0 makes it diverge and always
select the largest delta; rho does not degenerate, since avoided incorrect flips
saturate while deferred correct flips keep growing.)

Development sample.  12 fresh random keys x 200 errors at P4, seed context "dev".
Validation sample.   48 fresh random keys x 1000 errors at P4, seed context "val",
                     C0 / FRO-delta* / FRO-2(+2) on identical (H,e,s).
Inference.           key-cluster bootstrap (B=10000) + exact paired sign test.

P4 = (r, d, t) = (3607, 39, t*), with t* calibrated so the C0 carrier again sits
near 1e-3. The (r,d) pair is new: the project has used 4801/45, 3001/37, 4001/41,
12323/71. P4 is not used for any other purpose.

Run:  python lw-vs/scripts/exp_offset_rule.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
OUT = ROOT / "lw-vs" / "results" / "offset_rule"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder, make_threshold       # noqa: E402
from qcmdpc.generators import random_key, uniform_fixed_weight, _child_seed  # noqa: E402
from qcmdpc.stats import (wilson_upper, cluster_bootstrap_paired,            # noqa: E402
                          sign_test_paired)

MASTER_SEED = 20260901
R, D = 3607, 39
MAX_ITER = 20
T_SWEEP = [70, 72, 74, 76, 78, 80]
N_CALIB_KEYS, N_CALIB_ERR = 6, 300
DELTAS = (1, 2, 3, 4)
N_DEV_KEYS, N_DEV_ERR = 12, 200
N_VAL_KEYS, N_VAL_ERR = 48, 1000
N_WORKERS = min(12, os.cpu_count() or 1)


def arm(delta: int) -> dict:
    """bf_parallel with a first-round-only offset (offsets=[delta,0] == FRO-delta)."""
    return {"algo": "bf_parallel",
            "threshold": {"type": "offset", "base": {"type": "classic"},
                          "offsets": [delta, 0]},
            "max_iter": MAX_ITER}


def _key(ctx: str, ki: int):
    rng = np.random.default_rng(_child_seed(MASTER_SEED, f"P4|{ctx}|key", ki))
    return random_key(rng, R, D, f"P4-{ctx}-{ki:04d}")


def _errors(ctx: str, ki: int, n_err: int, t: int):
    out = []
    for ei in range(n_err):
        erng = np.random.default_rng(_child_seed(MASTER_SEED, f"P4|{ctx}|err|{ki}", ei))
        out.append(uniform_fixed_weight(erng, 2 * R, t))
    return out


# --------------------------------------------------------------------------
# workers (module level: required for Windows spawn)
# --------------------------------------------------------------------------
def _work_decode(job):
    """Run every requested arm on one key's error pool. Returns per-arm failures."""
    ctx, ki, n_err, t, deltas = job
    key = _key(ctx, ki)
    errs = _errors(ctx, ki, n_err, t)
    decs = {d: build_decoder(f"FRO-{d}", arm(d), D, t, R) for d in deltas}
    fails = {d: 0 for d in deltas}
    for e in errs:
        s0 = key.syndrome_from_global(e)
        for d in deltas:
            if not decs[d](key, s0).success:
                fails[d] += 1
    return ki, n_err, fails


def _work_upc(job):
    """Accumulate first-round UPC tail counts for error / non-error positions."""
    ctx, ki, n_err, t, deltas = job
    key = _key(ctx, ki)
    errs = _errors(ctx, ki, n_err, t)
    thr = make_threshold({"type": "classic"}, D, t, 2 * R)
    n1 = n0 = 0
    q1 = {d: 0 for d in (0,) + deltas}
    q0 = {d: 0 for d in (0,) + deltas}
    for e in errs:
        s0 = key.syndrome_from_global(e)
        u = key.upc_fast(s0)                       # first-round UPC vector
        tau1 = thr(0, int(s0.sum()))
        sup = e.astype(bool)
        n1 += int(sup.sum())
        n0 += int(sup.size - sup.sum())
        for d in (0,) + deltas:
            q1[d] += int(np.count_nonzero(u[sup] >= tau1 + d))
            q0[d] += int(np.count_nonzero(u[~sup] >= tau1 + d))
    return ki, n1, n0, q1, q0


def _run_jobs(fn, jobs):
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        return list(ex.map(fn, jobs))


# --------------------------------------------------------------------------
def calibrate() -> tuple[int, list]:
    print(f"[1] calibrating t at (r,d)=({R},{D}) over t in {T_SWEEP}")
    sweep = []
    for t in T_SWEEP:
        jobs = [(f"calib{t}", ki, N_CALIB_ERR, t, (0,)) for ki in range(N_CALIB_KEYS)]
        res = _run_jobs(_work_decode, jobs)
        fails = sum(r[2][0] for r in res)
        n = sum(r[1] for r in res)
        row = {"t": t, "failures": fails, "trials": n,
               "dfr": fails / n, "upper95": wilson_upper(fails, n)}
        sweep.append(row)
        print(f"    t={t}: DFR={row['dfr']:.3e}  ({fails}/{n})", flush=True)
    band = [r for r in sweep if 1e-4 <= r["dfr"] <= 1e-2]
    if not band:
        raise SystemExit("[abort] no t landed C0 inside [1e-4, 1e-2]; widen T_SWEEP")
    best = min(band, key=lambda r: abs(np.log10(r["dfr"]) + 3))
    print(f"    -> t* = {best['t']}  (C0 DFR = {best['dfr']:.3e})")
    return best["t"], sweep


def estimate_rule(t: int) -> dict:
    print(f"[2] estimating the rule at P4=({R},{D},{t}) on "
          f"{N_DEV_KEYS} keys x {N_DEV_ERR} errors")
    jobs = [(f"dev{t}", ki, N_DEV_ERR, t, DELTAS) for ki in range(N_DEV_KEYS)]
    res = _run_jobs(_work_upc, jobs)
    n1 = sum(r[1] for r in res)
    n0 = sum(r[2] for r in res)
    q1 = {d: sum(r[3][d] for r in res) for d in (0,) + DELTAS}
    q0 = {d: sum(r[4][d] for r in res) for d in (0,) + DELTAS}

    n = 2 * R
    p1 = {d: q1[d] / n1 for d in (0,) + DELTAS}     # per-position tail probability
    p0 = {d: q0[d] / n0 for d in (0,) + DELTAS}
    table, scores = [], {}
    for d in DELTAS:
        a1 = p1[d] / p1[0] if p1[0] else float("nan")
        a0 = p0[d] / p0[0] if p0[0] else float("nan")
        inc_avoided = (n - t) * (p0[0] - p0[d])      # per decoding instance
        cor_deferred = t * (p1[0] - p1[d])
        rho = inc_avoided / cor_deferred if cor_deferred > 0 else float("inf")
        scores[d] = rho
        table.append({"delta": d, "A1": a1, "A0": a0,
                      "expected_incorrect_avoided": inc_avoided,
                      "expected_correct_deferred": cor_deferred, "rho": rho})
        print(f"    delta={d}: A1={a1:.4f}  A0={a0:.5f}  "
              f"inc_avoided={inc_avoided:6.2f}  cor_deferred={cor_deferred:6.2f}  "
              f"rho={rho:6.3f}")
    best = max(DELTAS, key=lambda d: (scores[d], -d))
    return {"n_error_positions": n1, "n_nonerror_positions": n0,
            "q1_pooled": q1, "q0_pooled": q0,
            "p1_tail_prob": p1, "p0_tail_prob": p0,
            "instances": n1 // t, "table": table, "delta_star": best,
            "rho": {str(d): scores[d] for d in DELTAS}}


def validate(t: int, delta_star: int) -> dict:
    arms = sorted({0, 2, delta_star})
    print(f"[3] validating at P4 on {N_VAL_KEYS} FRESH keys x {N_VAL_ERR} errors; "
          f"arms = {['C0' if a == 0 else f'FRO-{a}' for a in arms]}")
    jobs = [(f"val{t}", ki, N_VAL_ERR, t, tuple(arms)) for ki in range(N_VAL_KEYS)]
    t0 = time.time()
    res = _run_jobs(_work_decode, jobs)
    elapsed = time.time() - t0
    per_key = {a: np.zeros(N_VAL_KEYS, dtype=np.int64) for a in arms}
    for ki, n_err, fails in res:
        for a in arms:
            per_key[a][ki] = fails[a]
    out = {"n_keys": N_VAL_KEYS, "errors_per_key": N_VAL_ERR,
           "wall_seconds": round(elapsed, 1), "arms": {}}
    n = N_VAL_KEYS * N_VAL_ERR
    for a in arms:
        k = int(per_key[a].sum())
        d = {"label": "C0" if a == 0 else f"FRO-{a}", "failures": k, "trials": n,
             "dfr": k / n, "upper95": wilson_upper(k, n),
             "per_key_failures": per_key[a].tolist()}
        if a != 0:
            boot = cluster_bootstrap_paired(per_key[0], per_key[a], N_VAL_ERR,
                                            B=10000, seed=20260905)
            sg = sign_test_paired(per_key[0], per_key[a])
            d["rr_vs_C0"] = boot["point"]["risk_ratio"]
            d["rr_ci95"] = boot["ci"]["risk_ratio"]
            d["rr_excludes_1"] = boot["rr_excludes_1"]
            d["sign_test"] = sg
        out["arms"][d["label"]] = d
        print(f"    {d['label']:7s} {k}/{n}  DFR={d['dfr']:.3e}"
              + (f"  RR={d['rr_vs_C0']:.3f} [{d['rr_ci95'][0]:.3f}, {d['rr_ci95'][1]:.3f}]"
                 f"  excludes1={d['rr_excludes_1']}" if a != 0 else ""), flush=True)
    return out


def main() -> int:
    started = time.time()
    protocol = {
        "name": "prespecified_first_round_offset_rule",
        "frozen_before_run": True,
        "point": {"r": R, "d": D, "t": "calibrated", "id": "P4",
                  "note": "new (r,d); project has used 4801/45, 3001/37, 4001/41, 12323/71"},
        "rule": {
            "definition": "delta* = argmax_{delta in {1,2,3,4}} rho(delta), rho = incorrect flips avoided per correct flip deferred",
            "A_c": "A_c(delta) = q_c(tau1+delta)/q_c(tau1), q_c = tail mass of first-round UPC in class c",
            "free_parameters": "none",
            "rho": "rho(delta) = [(n-t)*(q0(tau1)-q0(tau1+delta))] / [t*(q1(tau1)-q1(tau1+delta))]",
            "tie_break": "smaller delta",
        },
        "development_sample": {"keys": N_DEV_KEYS, "errors_per_key": N_DEV_ERR,
                               "seed_context": "dev"},
        "validation_sample": {"keys": N_VAL_KEYS, "errors_per_key": N_VAL_ERR,
                              "seed_context": "val", "fresh_keys": True},
        "inference": {"cluster_bootstrap": {"B": 10000, "seed": 20260905,
                                            "unit": "key"},
                      "sign_test": "exact two-sided, paired per-key"},
        "master_seed": MASTER_SEED,
    }
    with open(OUT / "protocol.json", "w", encoding="utf-8") as f:
        json.dump(protocol, f, indent=1)
    print(f"protocol frozen -> {OUT / 'protocol.json'}\n")

    t_star, sweep = calibrate()
    protocol["point"]["t"] = t_star
    with open(OUT / "protocol.json", "w", encoding="utf-8") as f:
        json.dump(protocol, f, indent=1)

    rule = estimate_rule(t_star)
    print(f"    => delta* = {rule['delta_star']}\n")

    val = validate(t_star, rule["delta_star"])

    result = {"protocol": protocol, "calibration_sweep": sweep, "rule": rule,
              "validation": val, "wall_seconds_total": round(time.time() - started, 1)}
    with open(OUT / "report.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    print(f"\n[done] {OUT / 'report.json'}  ({result['wall_seconds_total']:.0f} s total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
