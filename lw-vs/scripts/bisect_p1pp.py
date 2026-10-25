#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P1PP bracketing bisection: locate the (12323,71) t whose C0 DFR is in
[1e-4,1e-2].  See protocol_P1PP.json amendment-3. C0 only, 6 keys x L1S_E_CAL errors (200 => 1200
trials per point; an earlier docstring said 300, which was wrong)."""
from __future__ import annotations
import json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(Path(__file__).parent))

from exp_tier_upgrade import _work_l1s, OUT, L1S_E_CAL   # reuse the frozen worker

POINTS = (175, 172, 178)     # bisection order, at most two will be used


def main() -> int:
    print("[bisect] P1PP t-bisection (C0 only)")
    for t in POINTS:          # bisect until in band or the candidate list is exhausted
        t0 = time.time()
        with ProcessPoolExecutor(max_workers=2) as ex:
            res = list(ex.map(_work_l1s, [(ki, t, L1S_E_CAL, {"C0": 0}, False)
                                          for ki in range(6)]))
        n = 6 * L1S_E_CAL
        c0 = sum(r[1]["C0"] for r in res)
        dfr = c0 / n
        print(f"  t={t}: C0 {c0}/{n} DFR={dfr:.3e}  ({time.time()-t0:.0f}s)", flush=True)
        if 1e-4 <= dfr <= 1e-2:
            print(f"  -> t*={t} IN BAND")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
