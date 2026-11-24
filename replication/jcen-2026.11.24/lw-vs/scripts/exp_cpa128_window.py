#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The two-sided first-round window at a published BIKE preset, ~5% above the
production error weight of that preset (CPA-128 proximity measurement).

Context: the CPA-128 probe (exp_cpa128_scan.py) showed the static-C0 decodability
edge tracks the density t/r: at (r,d)=(10163,71) the [1e-4,1e-2] band opens at
t~138-142, only ~3-6% above the preset's production error weight t=134 (compare
+26-28% at Level 1). This run measures the C0 / FRO-2 / FRONEG contrast at
t=140 (t/r = 0.01378, the same density as Level-1's t=170) on 32 keys x 5000
errors, static semantics, common 20-iteration budget.

Reading rules: CPA-128 is a published BIKE preset (no CCA margin); the error weight
is raised ~4.5% from its production value to reach the measurable band. No claim
follows for Level-1 (12323) parameters, which remain the production code.

Run:  python lw-vs/scripts/exp_cpa128_window.py [--smoke]
Output: lw-vs/results/cpa128_window/report.json
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
OUT = ROOT / "lw-vs" / "results" / "cpa128_window"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import build_decoder                        # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator      # noqa: E402
from qcmdpc.stats import (wilson_upper, cluster_bootstrap_paired,  # noqa: E402
                          sign_test_paired)

SEED = 20260901
R, D, T_STAR = 10163, 71, 140
N_KEYS, E_PER_KEY = 32, 5000
MAX_ITER = 20
N_WORKERS = int(os.environ.get("CPA_WORKERS", "6"))

ARMS = {"C0": [0], "FRO-2": [2, 0], "FRONEG": [-1, 0]}

# cross-check: the scan measured C0 5/8000 = 6.25e-4 at (10163,71,140)
SCAN_DFR = 6.25e-4


def _param(t):
    return {"id": "CPA128", "r": R, "d": D, "t": t, "n0": 2}


def _work(job):
    ki, t, n_err = job
    pool = KeyPool(SEED, _param(t), "RAND", {"type": "random", "n_keys": N_KEYS})
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "RAND", key.key_id, _param(t),
                               {"type": "random", "n_keys": N_KEYS}, key, None)
    decs = {nm: build_decoder(nm, {"algo": "bf_parallel",
                                   "threshold": {"type": "offset",
                                                 "base": {"type": "classic"},
                                                 "offsets": off},
                                   "max_iter": MAX_ITER}, D, t, R)
            for nm, off in ARMS.items()}
    fails = {nm: np.zeros(n_err, dtype=np.uint8) for nm in ARMS}
    it_sum = {nm: 0 for nm in ARMS}
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        for nm, dec in decs.items():
            tr = dec(key, s0.copy())
            it_sum[nm] += tr.n_iters_run
            if not tr.success:
                fails[nm][eid] = 1
    return ki, fails, it_sum


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()

    global N_KEYS, E_PER_KEY, N_WORKERS, T_STAR
    if a.smoke:
        N_KEYS, E_PER_KEY, N_WORKERS = 2, 60, 2

    t0 = time.time()
    print(f"CPA-128 window: (r,d,t)=({R},{D},{T_STAR})  t/r={T_STAR/R:.5f}  "
          f"keys={N_KEYS} errors/key={E_PER_KEY}  workers={N_WORKERS}")
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        res = list(ex.map(_work, [(ki, T_STAR, E_PER_KEY) for ki in range(N_KEYS)]))
    res.sort(key=lambda r: r[0])
    n = N_KEYS * E_PER_KEY

    per_key = {nm: np.array([r[1][nm].sum() for r in res], dtype=np.int64)
               for nm in ARMS}
    fail_vec = {nm: np.concatenate([r[1][nm] for r in res]) for nm in ARMS}
    it_sum = {nm: sum(r[2][nm] for r in res) for nm in ARMS}

    out = {"point": {"r": R, "d": D, "t": T_STAR, "t_over_r": T_STAR / R},
           "preset": "CPA-128 (BIKE preset without CCA margin); production weight "
                     "of this preset is t=134 (raised +4.5% here)",
           "protocol": {"keys": N_KEYS, "errors_per_key": E_PER_KEY,
                        "arms": {k: str(v) for k, v in ARMS.items()},
                        "budget": MAX_ITER, "success": "zero residual syndrome"},
           "scan_crosscheck": {"t140_scan_dfr": SCAN_DFR,
                               "trials": 8000, "failures": 5},
           "arms": {}, "wall_seconds": None}

    for nm in ARMS:
        k = int(per_key[nm].sum())
        cell = {"failures": k, "trials": n, "dfr": k / n,
                "upper95": wilson_upper(k, n),
                "mean_iters": it_sum[nm] / n,
                "per_key_failures": per_key[nm].tolist()}
        if nm != "C0" and per_key["C0"].sum() > 0 and k > 0:
            boot = cluster_bootstrap_paired(per_key["C0"], per_key[nm], E_PER_KEY,
                                            B=10000, seed=20260905)
            cell["rr"] = boot["point"]["risk_ratio"]
            cell["rr_ci95"] = boot["ci"]["risk_ratio"]
            cell["sign_test"] = sign_test_paired(per_key["C0"], per_key[nm])
        out["arms"][nm] = cell
        line = f"  {nm:7s} {k:5d}/{n}  DFR={k/n:.3e}  iters={cell['mean_iters']:.3f}"
        if "rr" in cell:
            line += (f"  RR={cell['rr']:.3f} "
                     f"[{cell['rr_ci95'][0]:.3f}, {cell['rr_ci95'][1]:.3f}]")
        print(line, flush=True)

    # cross-check the C0 cell against the scan point (pooled two-sample z)
    k0 = int(per_key["C0"].sum())
    p1, n1, p2, n2 = k0 / n, n, SCAN_DFR, 8000
    p = (k0 + 5) / (n + 8000)
    import math
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se if se > 0 else 0.0
    out["scan_crosscheck"]["z"] = round(z, 3)
    print(f"  cross-check vs scan point: z={z:.2f}")

    out["wall_seconds"] = round(time.time() - t0, 1)
    path = OUT / ("report_smoke.json" if a.smoke else "report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"[done] {path}  ({out['wall_seconds']:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
