"""P1' calibration sweep: find t where CLASSIC DFR lands in [1e-2, 1e-4].

Screening-phase calibration (pre-registered as P1' selection procedure):
- parameter r=4801, d=45 fixed; sweep t;
- 4 random keys x 400 errors per t (G0 only);
- decoders: CLASSIC (carrier for H2) + BF30 (reference);
- output: DFR point estimate + Wilson upper bound per t.
Result decides the frozen P1' config. Not a headline experiment.
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
R, D = 4801, 45
T_LIST = [86, 88, 90, 92, 95]
N_KEYS, N_ERR = 4, 400

DECS = {
    "CLASSIC": {"algo": "bf_parallel", "threshold": {"type": "classic"}, "max_iter": 20},
    "BF30": {"algo": "bf_parallel", "threshold": {"type": "fixed", "b": 30}, "max_iter": 20},
}


def main():
    out = {"parameter": {"r": R, "d": D}, "n_keys": N_KEYS, "n_err": N_ERR, "sweep": []}
    for t in T_LIST:
        # identical keys+errors for both decoders at this t
        keys = []
        errs = []
        for ki in range(N_KEYS):
            rng = np.random.default_rng(_child_seed(MASTER_SEED, f"calib|key|{t}", ki))
            keys.append(random_key(rng, R, D, f"calib-{ki:02d}"))
            for ei in range(N_ERR):
                erng = np.random.default_rng(_child_seed(MASTER_SEED, f"calib|err|{t}|{ki}", ei))
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
            print(f"t={t} {name:8s} DFR={fails/N:.4e} U95={row[name]['upper95']:.4e} "
                  f"per_key={per_key.tolist()} ({row[name]['sec_per_decode']*1000:.0f} ms/dec)", flush=True)
        out["sweep"].append(row)
    os.makedirs("results/calib_p1prime", exist_ok=True)
    with open("results/calib_p1prime/sweep.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("saved -> results/calib_p1prime/sweep.json")


if __name__ == "__main__":
    main()
