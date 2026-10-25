#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Strengthen the (12323,71) waterfall profile: the published calibration used
6 keys x 200 errors per t (1200 trials), which is thin for a paper claim that
"the decodability transition at the production block parameters is confined to
a ~15% window in t".  This reruns the informative points with 12 keys x 500
errors (6000 trials each), C0 only, no arms other than the baseline.

The 12-key pool is prefix-stable, so keys 0..5 and error ids 0..199 are the
SAME instances as the published calibration (a strict superset): the results
here supersede the earlier table without any possibility of contradiction.

Run:  python lw-vs/scripts/strengthen_waterfall.py
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lw-vs" / "scripts"))
sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))

from exp_tier_upgrade import _work_l1s, OUT          # noqa: E402

TS = (168, 170, 172, 175, 180)
N_KEYS, N_ERR = 12, 500
WORKERS = 6


def main() -> int:
    p = OUT / "waterfall_strengthened.json"
    if p.exists():
        print("[waterfall] cached"); return 0
    print(f"[waterfall] (12323,71) C0 at t in {TS}, {N_KEYS} keys x {N_ERR} errors "
          f"({N_KEYS * N_ERR} trials per point)")
    out = {"what": "strengthened waterfall profile at the production block parameters",
           "keys": N_KEYS, "errors_per_key": N_ERR, "trials_per_point": N_KEYS * N_ERR,
           "note": "supersedes the 6x200 calibration scan (a strict subset of these instances)",
           "cells": {}}
    for t in TS:
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=WORKERS) as ex:
            res = list(ex.map(_work_l1s, [(ki, t, N_ERR, {"C0": 0}, False)
                                          for ki in range(N_KEYS)]))
        c0 = sum(r[1]["C0"] for r in res)
        n = N_KEYS * N_ERR
        cell = {"t": t, "t_over_r": t / 12323, "trials": n, "c0_failures": int(c0),
                "c0_dfr": c0 / n, "seconds": round(time.time() - t0, 1)}
        out["cells"][str(t)] = cell
        print(f"    t={t}: C0 {c0}/{n} DFR={c0/n:.3e}  ({cell['seconds']}s)", flush=True)
    json.dump(out, open(p, "w", encoding="utf-8"), indent=1)
    print(f"[waterfall] -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
