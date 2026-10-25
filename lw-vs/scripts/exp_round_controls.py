#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Round-control and parameter-sweep experiments for the first-round timing claim.

Why these arms
--------------
The paper argues that the ROUND in which a threshold offset is applied is the essential
variable, resting on three arms: first-round only ([2,0,...]) is beneficial, round-2 only
([0,2,0,...]) is mildly beneficial, and uniform ([2,2,2,...]) is catastrophic. Between the
last two there is a gap. Because `offsets` are clamped (`offs[min(it, len-1)]`), the
candidate set in search_m4.py contains no "round 2 onwards" arm, so the catastrophe of the
uniform offset cannot be attributed to the first round versus to sustained later-round
offsets. This script adds that arm, plus a first-round NEGATIVE offset to separate
"first-round conservatism" from "any first-round perturbation", plus a t-sensitivity curve
so the primary result is not read as an artifact of one knife-edge t.

Phase 1  P1' formal pool: C0, FRO-2, R2plus=[0,2], FRONEG=[-1,0]
         (C0 and FRO-2 re-run as a hard reproducibility gate against m5_formal)
Phase 2  t-sensitivity at P1': t in {88,90,92,94,96}, C0 vs FRO-2, 30 keys x 1000
Phase 3  parameter sweep: four new (r,d) points spanning t/r and d away from the
         narrow band (t/r ~ 0.02, d in [37,45]) that all existing points occupy

Run:  python lw-vs/scripts/exp_round_controls.py [--phase 1,2,3]
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
OUT = ROOT / "lw-vs" / "results" / "round_controls"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder                          # noqa: E402
from qcmdpc.generators import (KeyPool, make_error_generator,      # noqa: E402
                               random_key, uniform_fixed_weight, _child_seed)
from qcmdpc.stats import (wilson_upper, cluster_bootstrap_paired,  # noqa: E402
                          sign_test_paired)

SEED = 20260901
MAX_ITER = 20
N_WORKERS = int(os.environ.get("RC_WORKERS", "10"))

P1 = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
E_PER_KEY = 3000
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 100}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 100, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 100, "kappa": 12, "max_syn_weight": None,
                    "require_better_than_canonical": True}, "fresh_from": 8},
}
COND = {"G0": "RAND", "G2_d12": "TYPE-I", "G3": "NCW-shallow"}
EXPECTED = {"G0": (282, 68), "G2_d12": (372, 68), "G3": (141, 31)}

ARMS = {
    "C0":      [0],
    "FRO-2":   [2, 0],
    "R2plus":  [0, 2],      # NEW: round 2 onwards (sustained)
    "R2one":   [0, 2, 0],   # NEW: round 2 ONLY (one-shot) -- same pool as R2plus,
                            # so one-shot vs sustained is not confounded with the point
    "FRONEG":  [-1, 0],     # NEW: first-round negative offset
}
ARM_NOTE = {
    "C0": "baseline",
    "FRO-2": "first round only",
    "R2plus": "round 2 onwards, sustained (NEW)",
    "R2one": "round 2 only, one-shot (NEW)",
    "FRONEG": "first round -1 (NEW)",
}


def _dec(name):
    return build_decoder(name, {"algo": "bf_parallel",
                                "threshold": {"type": "offset",
                                              "base": {"type": "classic"},
                                              "offsets": ARMS[name]},
                                "max_iter": MAX_ITER},
                         P1["d"], P1["t"], P1["r"])


# --------------------------------------------------------------------------
def _work_p1(job):
    gid, ki = job
    pool = KeyPool(SEED, P1, gid, GROUPS[gid]["spec"])
    key = pool.keys[ki]
    gen = make_error_generator(SEED, gid, key.key_id, P1, GROUPS[gid]["spec"], key,
                               pool.ncws.get(key.key_id))
    decs = {n: _dec(n) for n in ARMS}
    fails = {n: 0 for n in ARMS}
    for eid in range(E_PER_KEY):
        e = gen(eid)
        s = key.syndrome_from_global(e)
        for n, d in decs.items():
            if not d(key, s.copy()).success:
                fails[n] += 1
    return gid, ki, fails


def phase1() -> bool:
    print("[phase 1] round controls at P1' formal pool "
          f"({E_PER_KEY} errors/key, arms: {list(ARMS)})")
    rep = {"phase": 1, "parameter": P1, "errors_per_key": E_PER_KEY,
           "arms": {n: {"offsets": ARMS[n], "note": ARM_NOTE[n]} for n in ARMS},
           "groups": {}}
    gate = True
    for gid in GROUPS:
        g = GROUPS[gid]
        pool = KeyPool(SEED, P1, gid, g["spec"])
        idxs = list(range(g["fresh_from"], len(pool.keys)))
        res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(
            _work_p1, [(gid, k) for k in idxs]))
        n_keys, n_dec = len(idxs), len(idxs) * E_PER_KEY
        per = {n: np.zeros(n_keys, dtype=np.int64) for n in ARMS}
        for _, ki, fails in res:
            j = idxs.index(ki)
            for n in ARMS:
                per[n][j] = fails[n]
        cell = {"condition": COND[gid], "n_keys": n_keys, "trials": n_dec, "arms": {}}
        for n in ARMS:
            k = int(per[n].sum())
            d = {"failures": k, "trials": n_dec, "dfr": k / n_dec,
                 "upper95": wilson_upper(k, n_dec),
                 "per_key_failures": per[n].tolist()}
            if n != "C0":
                boot = cluster_bootstrap_paired(per["C0"], per[n], E_PER_KEY,
                                                B=10000, seed=20260905)
                sg = sign_test_paired(per["C0"], per[n])
                d["rr_vs_C0"] = boot["point"]["risk_ratio"]
                d["rr_ci95"] = boot["ci"]["risk_ratio"]
                d["rr_excludes_1"] = boot["rr_excludes_1"]
                d["sign_test"] = sg
            cell["arms"][n] = d
        c0, f2 = int(per["C0"].sum()), int(per["FRO-2"].sum())
        ok = (c0, f2) == EXPECTED[gid]
        gate &= ok
        print(f"  [{COND[gid]:12s}] C0 {c0} (archive {EXPECTED[gid][0]}) "
              f"FRO-2 {f2} (archive {EXPECTED[gid][1]}) {'OK' if ok else '*** MISMATCH ***'}")
        for n in ("R2plus", "R2one", "FRONEG"):
            a = cell["arms"][n]
            print(f"     {n:7s} {a['failures']:5d}/{n_dec}  DFR={a['dfr']:.4e}  "
                  f"RR={a['rr_vs_C0']:.3f} [{a['rr_ci95'][0]:.3f}, {a['rr_ci95'][1]:.3f}] "
                  f"excl1={a['rr_excludes_1']}", flush=True)
        rep["groups"][gid] = cell
    rep["gate_passed"] = gate
    with open(OUT / "phase1_round_controls.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print(f"  gate: {'PASS' if gate else 'FAIL'}")
    return gate


# --------------------------------------------------------------------------
def _work_t(job):
    ti, ki, n_err = job
    t = ti
    rng = np.random.default_rng(_child_seed(SEED, f"tsweep|key|{t}", ki))
    key = random_key(rng, P1["r"], P1["d"], f"ts-{t}-{ki:03d}")
    decs = {"C0": build_decoder("C0", {"algo": "bf_parallel",
                                       "threshold": {"type": "classic"},
                                       "max_iter": MAX_ITER},
                                P1["d"], t, P1["r"]),
            "FRO-2": build_decoder("FRO-2", {"algo": "bf_parallel",
                                             "threshold": {"type": "offset",
                                                           "base": {"type": "classic"},
                                                           "offsets": [2, 0]},
                                             "max_iter": MAX_ITER},
                                   P1["d"], t, P1["r"])}
    fails = {"C0": 0, "FRO-2": 0}
    for eid in range(n_err):
        erng = np.random.default_rng(_child_seed(SEED, f"tsweep|err|{t}|{ki}", eid))
        e = uniform_fixed_weight(erng, 2 * P1["r"], t)
        s = key.syndrome_from_global(e)
        for n, d in decs.items():
            if not d(key, s.copy()).success:
                fails[n] += 1
    return t, ki, fails


def phase2(t_list=(88, 90, 92, 94, 96), n_keys=30, n_err=1000) -> None:
    print(f"\n[phase 2] t-sensitivity at P1' (r,d)=({P1['r']},{P1['d']}), "
          f"{n_keys} keys x {n_err} errors per t")
    rep = {"phase": 2, "r": P1["r"], "d": P1["d"], "n_keys": n_keys,
           "errors_per_key": n_err, "seed": SEED, "cells": {}}
    for t in t_list:
        res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(
            _work_t, [(t, ki, n_err) for ki in range(n_keys)]))
        n = n_keys * n_err
        c0 = sum(r[2]["C0"] for r in res)
        f2 = sum(r[2]["FRO-2"] for r in res)
        c0_per = np.array([r[2]["C0"] for r in sorted(res, key=lambda x: x[1])])
        f2_per = np.array([r[2]["FRO-2"] for r in sorted(res, key=lambda x: x[1])])
        boot = cluster_bootstrap_paired(c0_per, f2_per, n_err, B=10000, seed=20260905)
        rep["cells"][str(t)] = {
            "t": t, "t_over_r": t / P1["r"], "trials": n,
            "c0_failures": c0, "c0_dfr": c0 / n,
            "fro2_failures": f2, "fro2_dfr": f2 / n,
            "rr": boot["point"]["risk_ratio"], "rr_ci95": boot["ci"]["risk_ratio"],
            "rr_excludes_1": boot["rr_excludes_1"],
            "c0_upper95": wilson_upper(c0, n),
        }
        c = rep["cells"][str(t)]
        rr_txt = ("undefined (zero failures in one arm)"
                  if c["rr"] is None or c["rr_ci95"][0] is None
                  else f"{c['rr']:.3f} [{c['rr_ci95'][0]:.3f}, {c['rr_ci95'][1]:.3f}]")
        print(f"  t={t} (t/r={c['t_over_r']:.4f}): C0 {c0:4d}/{n} "
              f"DFR={c['c0_dfr']:.3e}  FRO-2 {f2:4d}/{n}  RR={rr_txt}", flush=True)
    with open(OUT / "phase2_t_sensitivity.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)


# --------------------------------------------------------------------------
# phase 3: parameter sweep away from the narrow band all existing points occupy
SWEEP = [
    {"id": "Q1", "r": 4801, "d": 45, "t_list": [80, 84, 88], "note": "low t/r"},
    {"id": "Q2", "r": 4801, "d": 45, "t_list": [98, 102, 106], "note": "high t/r"},
    {"id": "Q3", "r": 4801, "d": 59, "t_list": [86, 92, 98], "note": "large d"},
    {"id": "Q4", "r": 4801, "d": 31, "t_list": [74, 80, 86], "note": "small d"},
]


def _work_q(job):
    rid, r, d, t, ki, n_err = job
    rng = np.random.default_rng(_child_seed(SEED, f"sweep|{rid}|key", ki))
    key = random_key(rng, r, d, f"{rid}-{ki:03d}")
    decs = {"C0": build_decoder("C0", {"algo": "bf_parallel",
                                       "threshold": {"type": "classic"},
                                       "max_iter": MAX_ITER}, d, t, r),
            "FRO-2": build_decoder("FRO-2", {"algo": "bf_parallel",
                                             "threshold": {"type": "offset",
                                                           "base": {"type": "classic"},
                                                           "offsets": [2, 0]},
                                             "max_iter": MAX_ITER}, d, t, r)}
    fails = {"C0": 0, "FRO-2": 0}
    for eid in range(n_err):
        erng = np.random.default_rng(_child_seed(SEED, f"sweep|{rid}|err|{ki}", eid))
        e = uniform_fixed_weight(erng, 2 * r, t)
        s = key.syndrome_from_global(e)
        for n, dec in decs.items():
            if not dec(key, s.copy()).success:
                fails[n] += 1
    return rid, t, ki, fails


def phase3(n_keys=30, n_err=1000) -> None:
    print(f"\n[phase 3] parameter sweep, {n_keys} keys x {n_err} errors per cell")
    rep = {"phase": 3, "n_keys": n_keys, "errors_per_key": n_err, "seed": SEED,
           "note": "four new (r,d,t) points spanning t/r and d away from the existing "
                   "narrow band (t/r ~ 0.02, d in [37,45])",
           "points": {}}
    for spec in SWEEP:
        rid, r, d = spec["id"], spec["r"], spec["d"]
        rep["points"][rid] = {"r": r, "d": d, "note": spec["note"], "cells": {}}
        for t in spec["t_list"]:
            res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(
                _work_q, [(rid, r, d, t, ki, n_err) for ki in range(n_keys)]))
            n = n_keys * n_err
            c0_per = np.array([x[3]["C0"] for x in sorted(res, key=lambda y: y[2])])
            f2_per = np.array([x[3]["FRO-2"] for x in sorted(res, key=lambda y: y[2])])
            c0, f2 = int(c0_per.sum()), int(f2_per.sum())
            boot = cluster_bootstrap_paired(c0_per, f2_per, n_err, B=10000,
                                            seed=20260905)
            cell = {"t": t, "t_over_r": t / r, "trials": n,
                    "c0_failures": c0, "c0_dfr": c0 / n,
                    "fro2_failures": f2, "fro2_dfr": f2 / n,
                    "rr": boot["point"]["risk_ratio"],
                    "rr_ci95": boot["ci"]["risk_ratio"],
                    "rr_excludes_1": boot["rr_excludes_1"],
                    "c0_upper95": wilson_upper(c0, n),
                    "c0_zero_failures": c0 == 0}
            rep["points"][rid]["cells"][str(t)] = cell
            print(f"  {rid} (r={r},d={d}) t={t:3d} (t/r={t/r:.4f}): "
                  f"C0 {c0:4d}/{n} DFR={c0/n:.3e}  FRO-2 {f2:4d}/{n}  "
                  f"RR={'undefined (zero failures)' if cell['rr'] is None else f'{cell[chr(114)+chr(114)]:.3f}'}"
                  , flush=True)
    with open(OUT / "phase3_parameter_sweep.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)



# --------------------------------------------------------------------------
# phase 4: a larger-r point, calibrated first (the earlier sweep guessed t and
# missed the measurable band at three of four points)
# --------------------------------------------------------------------------
BIG = {"r": 6007, "d": 56}          # r/d = 107.3 and d/r = 0.0093, matching P1'
BIG_T_CAND = [88, 92, 96, 100]
BIG_KEYS, BIG_ERR = 40, 1000


def _work_big(job):
    rid, r, d, t, ki, n_err = job
    rng = np.random.default_rng(_child_seed(SEED, f"big|{rid}|{t}|key", ki))
    key = random_key(rng, r, d, f"{rid}-{t}-{ki:03d}")
    decs = {"C0": build_decoder("C0", {"algo": "bf_parallel",
                                       "threshold": {"type": "classic"},
                                       "max_iter": MAX_ITER}, d, t, r),
            "FRO-2": build_decoder("FRO-2", {"algo": "bf_parallel",
                                             "threshold": {"type": "offset",
                                                           "base": {"type": "classic"},
                                                           "offsets": [2, 0]},
                                             "max_iter": MAX_ITER}, d, t, r)}
    fails = {"C0": 0, "FRO-2": 0}
    for eid in range(n_err):
        erng = np.random.default_rng(_child_seed(SEED, f"big|{rid}|{t}|err|{ki}", eid))
        e = uniform_fixed_weight(erng, 2 * r, t)
        s = key.syndrome_from_global(e)
        for nm, dec in decs.items():
            if not dec(key, s.copy()).success:
                fails[nm] += 1
    return t, ki, fails


def phase4() -> None:
    print("\n[phase 4] larger-r point "
          f"(r,d)=({BIG['r']},{BIG['d']}), calibrate then run")
    rep = {"phase": 4, "r": BIG["r"], "d": BIG["d"], "seed": SEED,
           "note": "larger r at matched density d/r = 0.0093 (P1' is 0.0094), so the "
                   "point isolates the code-size axis rather than also changing density",
           "calibration": [], "cells": {}}
    # -- calibration on C0 only, 6 keys x 300 errors --
    best = None
    for t in BIG_T_CAND:
        res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(
            _work_big, [("cal", BIG["r"], BIG["d"], t, ki, 300) for ki in range(6)]))
        n = 6 * 300
        c0 = sum(x[2]["C0"] for x in res)
        row = {"t": t, "t_over_r": t / BIG["r"], "trials": n,
               "c0_failures": c0, "c0_dfr": c0 / n}
        rep["calibration"].append(row)
        print(f"  calib t={t} (t/r={t/BIG['r']:.4f}): C0 {c0}/{n} DFR={c0/n:.3e}",
              flush=True)
        if 1e-4 <= c0 / n <= 1e-2 and (best is None or
                                       abs(c0 / n - 1e-3) < abs(rep["calibration"][best]["c0_dfr"] - 1e-3)):
            best = len(rep["calibration"]) - 1
    if best is None:
        print("  !! no t landed C0 in [1e-4,1e-2]; the measurable band for this point "
              "is outside the swept range")
        rep["status"] = "no measurable operating point in the swept t range"
    else:
        tt = rep["calibration"][best]["t"]
        rep["chosen_t"] = tt
        res = list(ProcessPoolExecutor(max_workers=N_WORKERS).map(
            _work_big, [("run", BIG["r"], BIG["d"], tt, ki, BIG_ERR)
                        for ki in range(BIG_KEYS)]))
        n = BIG_KEYS * BIG_ERR
        c0_per = np.array([x[2]["C0"] for x in sorted(res, key=lambda y: y[1])])
        f2_per = np.array([x[2]["FRO-2"] for x in sorted(res, key=lambda y: y[1])])
        c0, f2 = int(c0_per.sum()), int(f2_per.sum())
        boot = cluster_bootstrap_paired(c0_per, f2_per, BIG_ERR, B=10000, seed=20260905)
        cell = {"t": tt, "t_over_r": tt / BIG["r"], "n_keys": BIG_KEYS, "trials": n,
                "c0_failures": c0, "c0_dfr": c0 / n,
                "fro2_failures": f2, "fro2_dfr": f2 / n,
                "rr": boot["point"]["risk_ratio"], "rr_ci95": boot["ci"]["risk_ratio"],
                "rr_excludes_1": boot["rr_excludes_1"],
                "c0_upper95": wilson_upper(c0, n)}
        rep["cells"][str(tt)] = cell
        rr_txt = ("undefined" if cell["rr"] is None
                  else f"{cell['rr']:.3f} [{cell['rr_ci95'][0]:.3f}, {cell['rr_ci95'][1]:.3f}]")
        print(f"  RUN t={tt}: C0 {c0}/{n} DFR={c0/n:.3e}  FRO-2 {f2}/{n}  RR={rr_txt}",
              flush=True)
    with open(OUT / "phase4_larger_r.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="1,2,3")
    a = ap.parse_args()
    t0 = time.time()
    phases = [x.strip() for x in a.phase.split(",") if x.strip()]
    ok = True
    if "1" in phases:
        ok = phase1()
    if "2" in phases:
        phase2()
    if "3" in phases:
        phase3()
    if "4" in phases:
        phase4()
    print(f"\n[done] {OUT}  ({time.time()-t0:.0f} s)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
