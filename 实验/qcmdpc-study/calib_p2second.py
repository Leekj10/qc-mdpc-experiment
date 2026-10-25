"""Second measurable scaled operating point: calibration sweep (review round-3, B1).

Purpose
-------
Check whether the first-round stabilization (FRO-2 = +2 on the iteration-1
threshold only) transfers to a scaled operating point OTHER than P1'
(r=4801, d=45, t=92). This is the study's main generalization gap (single
calibrated point).

Protocol (mirrors calib_p1prime.py, screening-phase calibration):
- NEW (r, d) pair, deliberately different from P1' so the point is not a mere
  t-shift of the same code; sweep t to land the C0 (CLASSIC) carrier in the
  measurable band [1e-4, 1e-2] (target ~1e-3);
- ONLY t is calibrated (for measurability). The FRO-2 offset (+2, first round
  only) is FROZEN from P1' and is NOT re-searched / re-tuned here;
- 4 random keys x 400 errors per t (G0 only), identical (H, e, s) for both arms;
- output: DFR point estimate + Wilson upper bound per (t, arm).

The chosen t is then frozen into configs/p2second_transfer.json for the formal
transfer run (transfer_p2second.py). Not a headline experiment.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import random_key, uniform_fixed_weight, _child_seed
from qcmdpc.stats import wilson_upper

MASTER_SEED = 20260901
# Second scaled set: different (r, d) from P1' (4801, 45). Smaller r keeps the
# Python-scale sweep affordable; (6007, 53) is the alternative if the C binary is used.
R, D = 3001, 37
# First sweep (2026-09-05) showed the CLASSIC carrier is already at 2.4e-2 by t=68 and
# climbs steeply above, so the measurable band [1e-4,1e-2] for (3001,37) lies BELOW 2*d.
# Sweep downward to bracket C0 ~ 1e-3.
T_LIST = [60, 62, 64, 66, 68]
N_KEYS, N_ERR = 4, 400

# C0 = CLASSIC base; FRO-2 = frozen first-round +2 offset (offsets [2,0]), NOT re-tuned.
DECS = {
    "C0_base": {"algo": "bf_parallel", "threshold": {"type": "classic"}, "max_iter": 20},
    "C4_first_p2": {"algo": "bf_parallel",
                    "threshold": {"type": "offset", "base": {"type": "classic"}, "offsets": [2, 0]},
                    "max_iter": 20},
}


def main():
    out = {"parameter": {"r": R, "d": D}, "n_keys": N_KEYS, "n_err": N_ERR,
           "note": "second-point calibration; only t is calibrated, FRO-2 (+2) frozen",
           "sweep": []}
    for t in T_LIST:
        keys, errs = [], []
        for ki in range(N_KEYS):
            rng = np.random.default_rng(_child_seed(MASTER_SEED, f"calib2|key|{t}", ki))
            keys.append(random_key(rng, R, D, f"calib2-{ki:02d}"))
            for ei in range(N_ERR):
                erng = np.random.default_rng(_child_seed(MASTER_SEED, f"calib2|err|{t}|{ki}", ei))
                errs.append((ki, uniform_fixed_weight(erng, 2 * R, t)))
        row = {"t": t}
        for name, spec in DECS.items():
            dec = build_decoder(name, spec, D, t, R)
            t0 = time.time()
            fails = 0
            per_key = np.zeros(N_KEYS, dtype=np.int64)
            for ki, e in errs:
                s0 = keys[ki].syndrome_from_global(e)
                if not dec(keys[ki], s0).success:
                    fails += 1
                    per_key[ki] += 1
            N = len(errs)
            row[name] = {
                "dfr": fails / N,
                "upper95": wilson_upper(fails, N),
                "per_key_failures": per_key.tolist(),
                "sec_per_decode": round((time.time() - t0) / N, 4),
            }
            print(f"t={t} {name:12s} DFR={fails/N:.4e} U95={row[name]['upper95']:.4e} "
                  f"per_key={per_key.tolist()} ({row[name]['sec_per_decode']*1000:.0f} ms/dec)", flush=True)
        out["sweep"].append(row)
    os.makedirs("results/calib_p2second", exist_ok=True)
    with open("results/calib_p2second/sweep.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    # recommend the t whose C0 DFR is closest to 1e-3 inside the measurable band
    cand = [r for r in out["sweep"] if 1e-4 <= r["C0_base"]["dfr"] <= 1e-2]
    if cand:
        best = min(cand, key=lambda r: abs(np.log10(r["C0_base"]["dfr"]) + 3))
        print(f"\n[recommend] freeze t={best['t']} (C0 DFR={best['C0_base']['dfr']:.3e}); "
              f"set configs/p2second_transfer.json parameter.t accordingly", flush=True)
    else:
        print("\n[warn] no t landed C0 in [1e-4,1e-2]; widen T_LIST and rerun", flush=True)
    print("saved -> results/calib_p2second/sweep.json")


if __name__ == "__main__":
    main()
