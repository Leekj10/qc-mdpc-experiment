"""S4 confirmation: C0_base vs C4_first_p2 on TEST keys only (single run, pre-registered).

Formal H2 gate decision requires the full-scale M1 pools (100 keys/group);
this run completes the S1->S2->S4 structure on the current small pools and
gives the first test-key estimate. TEST keys were never used in S1/S2.
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
from qcmdpc.stats import wilson_upper
from search_m4 import CANDIDATES, split_keys

BASE_CFG = "configs/h2_p1prime_cps.json"
OUT = "results/m4_search"
E_TEST = 1000


def main():
    cfg = json.load(open(BASE_CFG, encoding="utf-8"))
    param, seed, groups = cfg["parameter"], cfg["seed"], cfg["groups"]
    report = {"E_test": E_TEST, "candidates": ["C0_base", "C4_first_p2"], "groups": {}}

    for gid, gspec in groups.items():
        pool = KeyPool(seed, param, gid, gspec)
        test_idx = split_keys(len(pool.keys))[2]
        report["groups"][gid] = {"test_key_ids": [pool.keys[i].key_id for i in test_idx]}
        for name in ["C0_base", "C4_first_p2"]:
            dec = build_decoder(name, CANDIDATES[name], param["d"], param["t"], param["r"])
            fails, trials = 0, 0
            per_key = []
            t0 = time.time()
            for ki in test_idx:
                key = pool.keys[ki]
                gen = make_error_generator(seed, gid, key.key_id, param, gspec, key, pool.ncws.get(key.key_id))
                kf = 0
                for eid in range(E_TEST):
                    e = gen(eid)
                    s0 = key.syndrome_from_global(e)
                    if not dec(key, s0).success:
                        fails += 1
                        kf += 1
                    trials += 1
                per_key.append(kf)
            u = wilson_upper(fails, trials)
            entry = {
                "failures": fails, "trials": trials, "dfr": fails / max(1, trials),
                "upper95": u, "log10_upper95": float(np.log10(u)), "per_key_failures": per_key,
                "seconds": round(time.time() - t0, 1),
            }
            report["groups"][gid][name] = entry
            print(f"{gid:8s} {name:12s} DFR={entry['dfr']:.3e} U95={u:.3e} per_key={per_key} ({entry['seconds']}s)", flush=True)

    # worst-group comparison (H2 metric direction)
    j = {}
    for name in ["C0_base", "C4_first_p2"]:
        j[name] = max(report["groups"][g][name]["log10_upper95"] for g in groups)
    report["worst_group_log10U"] = j
    report["improvement_log10"] = j["C0_base"] - j["C4_first_p2"]
    report["gate_0.5_log10_met"] = bool(report["improvement_log10"] >= 0.5)
    report["note"] = "small-pool probe; formal gate decision requires full M1 pools (100 keys/group)"
    with open(os.path.join(OUT, "confirm_test.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("worst-group log10U:", j, "improvement:", report["improvement_log10"])
    print("saved ->", os.path.join(OUT, "confirm_test.json"))


if __name__ == "__main__":
    main()
