#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CPA-128 probe: does the decodability edge track t/r? (design-Q5 probe)

The BIKE CPA preset (no CCA margin) is (r,d,t)=(10163,71,134): same d and production
error weight as Level 1, but 17.5% smaller r. At L1 the static C0 band [1e-4,1e-2]
sits at t~170-175 (t/r~0.0138-0.0142). If the edge follows the density t/r, the band
at r=10163 should sit near t~140-144 -- i.e. much closer to the production weight in
absolute t. This scan tests that hypothesis (C0 only, 8 keys x 1000 errors per point).

Reading rules: a negative result (edge does not move with t/r) is as informative as a
positive one and is reported either way; no claim follows for r=12323, which is the
production code.

Run:  python lw-vs/scripts/exp_cpa128_scan.py [--smoke]
Output: lw-vs/results/cpa128_scan/report.json
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
OUT = ROOT / "lw-vs" / "results" / "cpa128_scan"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder                        # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator      # noqa: E402
from qcmdpc.stats import wilson_upper                            # noqa: E402

SEED = 20260901
R, D = 10163, 71                   # BIKE CPA-128 preset (param.h PRESET_CPA)
T_POINTS = (134, 136, 138, 140, 142, 144, 146)
N_KEYS, E_PER_KEY = 8, 1000
MAX_ITER = 20
N_WORKERS = int(os.environ.get("CPA_WORKERS", "6"))

# L1 reference points for the t/r comparison (same static carrier, archived):
L1_REF = {"edge_lo": {"t": 168, "t_over_r": 168 / 12323},
          "band_dfr_1e4": {"t": 170, "t_over_r": 170 / 12323},
          "band_dfr_1e2": {"t": 175, "t_over_r": 175 / 12323}}


def _param(t: int) -> dict:
    return {"id": "CPA128", "r": R, "d": D, "t": t, "n0": 2}


def _work(job):
    ki, t, n_err = job
    pool = KeyPool(SEED, _param(t), "RAND", {"type": "random", "n_keys": N_KEYS})
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "RAND", key.key_id, _param(t),
                               {"type": "random", "n_keys": N_KEYS}, key, None)
    dec = build_decoder("C0", {"algo": "bf_parallel",
                               "threshold": {"type": "classic"},
                               "max_iter": MAX_ITER}, D, t, R)
    fails, iters = 0, 0
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        tr = dec(key, s0.copy())
        iters += tr.n_iters_run
        if not tr.success:
            fails += 1
    return ki, t, fails, iters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()

    global N_KEYS, E_PER_KEY, N_WORKERS, T_POINTS
    if a.smoke:
        N_KEYS, E_PER_KEY, N_WORKERS, T_POINTS = 2, 30, 2, (134, 144)

    # sanity: r must be prime for the QC construction
    assert all(R % p for p in range(2, int(R ** 0.5) + 1)), f"r={R} not prime"

    t0 = time.time()
    print(f"CPA-128 scan (r,d)=({R},{D})  points={list(T_POINTS)}  "
          f"keys={N_KEYS} errors/key={E_PER_KEY}  workers={N_WORKERS}")
    out = {"point": {"r": R, "d": D}, "preset": "CPA-128 (param.h PRESET_CPA)",
           "hypothesis": "the static-C0 band [1e-4,1e-2] follows the density t/r; "
                         "at r=10163 it should sit near t~140-144",
           "l1_reference": L1_REF, "cells": {}, "wall_seconds": None}
    for t in T_POINTS:
        tt = time.time()
        with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
            res = list(ex.map(_work, [(ki, t, E_PER_KEY) for ki in range(N_KEYS)]))
        n = N_KEYS * E_PER_KEY
        k = sum(r[2] for r in res)
        it = sum(r[3] for r in res) / n
        cell = {"t": t, "t_over_r": t / R, "trials": n, "c0_failures": k,
                "c0_dfr": k / n, "upper95": wilson_upper(k, n),
                "mean_iters": it, "seconds": round(time.time() - tt, 1)}
        out["cells"][str(t)] = cell
        print(f"  t={t:3d} (t/r={t/R:.5f}): C0 {k:4d}/{n}  "
              f"dfr={k/n:.3e}  iters={it:.2f}  ({cell['seconds']}s)", flush=True)
    out["wall_seconds"] = round(time.time() - t0, 1)
    path = OUT / ("report_smoke.json" if a.smoke else "report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"[done] {path}  ({out['wall_seconds']:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
