"""Cross-validation: Python bf_classic_dynamic vs C reference CLASSIC binary.

C reference result (qcmdpc_classic_p1p.exe, -T4 -N200000 -i20, 2026-09-03):
    136 failures / 200000 = 6.80e-4  (Wilson U95 ~ 7.8e-4)
This script runs the faithful dynamic-distance port on the same ensemble
(fresh random key + fresh uniform weight-t error per instance, P1' parameters)
and reports DFR + Wilson interval + z-comparison against the C number.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import bf_classic_dynamic
from qcmdpc.generators import random_key, uniform_fixed_weight, _child_seed
from qcmdpc.stats import wilson_upper

R, D, T = 4801, 45, 92
N_INST = int(os.environ.get("XVAL_N", "20000"))
SEED = 20260903
C_REF = {"failures": 136, "trials": 200000}


def main():
    fails = 0
    t0 = time.time()
    dist_hist = {}
    for i in range(N_INST):
        rng = np.random.default_rng(_child_seed(SEED, "xval|key", i))
        key = random_key(rng, R, D)
        e = uniform_fixed_weight(rng, 2 * R, T)
        s0 = key.syndrome_from_global(e)
        r = bf_classic_dynamic(key, s0, e, max_iter=20)
        if not r.success:
            fails += 1
            fd = r.extra.get("final_dist")
            dist_hist[fd] = dist_hist.get(fd, 0) + 1
        if (i + 1) % 2000 == 0:
            print(f"  {i+1}/{N_INST} fails={fails} ({time.time()-t0:.0f}s)", flush=True)
    p = fails / N_INST
    u = wilson_upper(fails, N_INST)
    pc = C_REF["failures"] / C_REF["trials"]
    pooled = (fails + C_REF["failures"]) / (N_INST + C_REF["trials"])
    se = math.sqrt(pooled * (1 - pooled) * (1 / N_INST + 1 / C_REF["trials"]))
    z = (p - pc) / se if se > 0 else float("nan")
    out = {
        "python_dynamic": {"failures": fails, "trials": N_INST, "dfr": p, "upper95": u,
                           "final_dist_hist_of_failures": {str(k): v for k, v in sorted(dist_hist.items(), key=lambda x: (x[0] is None, x[0]))}},
        "c_reference": {**C_REF, "dfr": pc},
        "two_proportion_z": z,
        "verdict": "consistent (|z|<2.5)" if abs(z) < 2.5 else "INCONSISTENT - investigate",
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs("results/crossval", exist_ok=True)
    with open("results/crossval/classic_dynamic_vs_c.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
