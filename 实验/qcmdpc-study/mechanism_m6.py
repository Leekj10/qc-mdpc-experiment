"""M6 mechanism analysis: which failure classes does C4 (first-round +2) eliminate?

Paired design: identical (H, e, s) samples decoded by C0_base and C4_first_p2.
Output:
- failure-mode distribution per (group, decoder);
- transition matrix: C0 failure mode -> C4 outcome (success / mode);
- iteration statistics.
Keys: train+val indices of the frozen P1' pools (test keys stay untouched for
the formal gate). Mechanism evidence, not a headline DFR claim.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, make_error_generator
from qcmdpc.taxonomy import classify_failure
from search_m4 import CANDIDATES, split_keys

BASE_CFG = "configs/h2_p1prime_cps.json"
OUT = "results/m6_mechanism"
E_PER_KEY = 400
PAIRS = [("C0_base", "C4_first_p2")]
TAXONOMY_MAX_ITER = int(CANDIDATES["C0_base"]["max_iter"])


def main():
    cfg = json.load(open(BASE_CFG, encoding="utf-8"))
    param, seed, groups = cfg["parameter"], cfg["seed"], cfg["groups"]
    os.makedirs(OUT, exist_ok=True)
    decs = {n: build_decoder(n, CANDIDATES[n], param["d"], param["t"], param["r"]) for n in ["C0_base", "C4_first_p2"]}

    report = {"E_per_key": E_PER_KEY, "groups": {}}
    for gid, gspec in groups.items():
        pool = KeyPool(seed, param, gid, gspec)
        tr, va, _ = split_keys(len(pool.keys))
        idxs = tr + va
        g_out = {
            "n_keys": len(idxs),
            "modes": {n: {} for n in decs},
            "transitions": {},
            "iters": {n: [] for n in decs},
        }
        t0 = time.time()
        for ki in idxs:
            key = pool.keys[ki]
            gen = make_error_generator(seed, gid, key.key_id, param, gspec, key, pool.ncws.get(key.key_id))
            for eid in range(E_PER_KEY):
                e = gen(eid)
                s0 = key.syndrome_from_global(e)
                e_sup = set(int(x) for x in np.nonzero(e)[0])
                r0 = decs["C0_base"](key, s0.copy(), record_flips=True)
                r4 = decs["C4_first_p2"](key, s0.copy(), record_flips=True)
                m0 = classify_failure(r0, e_sup, max_iter=TAXONOMY_MAX_ITER)
                m4 = classify_failure(r4, e_sup, max_iter=TAXONOMY_MAX_ITER)
                g_out["modes"]["C0_base"][m0] = g_out["modes"]["C0_base"].get(m0, 0) + 1
                g_out["modes"]["C4_first_p2"][m4] = g_out["modes"]["C4_first_p2"].get(m4, 0) + 1
                g_out["iters"]["C0_base"].append(r0.n_iters_run)
                g_out["iters"]["C4_first_p2"].append(r4.n_iters_run)
                if m0 != "success":
                    key_t = f"{m0}->{m4}"
                    g_out["transitions"][key_t] = g_out["transitions"].get(key_t, 0) + 1
                elif m4 != "success":
                    key_t = f"success->{m4}"
                    g_out["transitions"][key_t] = g_out["transitions"].get(key_t, 0) + 1
        g_out["iters"] = {n: float(np.mean(v)) for n, v in g_out["iters"].items()}
        g_out["seconds"] = round(time.time() - t0, 1)
        report["groups"][gid] = g_out
        print(f"[{gid}] modes_C0={g_out['modes']['C0_base']} modes_C4={g_out['modes']['C4_first_p2']}", flush=True)
        print(f"[{gid}] transitions={g_out['transitions']} iters={g_out['iters']} ({g_out['seconds']}s)", flush=True)

    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("saved ->", os.path.join(OUT, "report.json"))


if __name__ == "__main__":
    main()
