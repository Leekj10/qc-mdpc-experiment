"""BF-Max tie-break probe on the recorded L1 probe failures.

Question: are the BF-Max failures at BIKE L1 (m1_p2_l1_probe) an artifact of
our deterministic smallest-index tie-break, or genuine budget exhaustion?

Method: reconstruct the exact failing (key, error) samples from the frozen
seed derivation, verify the deterministic mode reproduces the failure, then
run N independent PRF tie-break draws (distinct salts) and count recoveries.
Also runs a success-preservation control on samples that decoded fine.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import bf_max
from qcmdpc.generators import KeyPool, make_error_generator

CFG = "configs/m1_p2_l1_probe.json"
RUN = "results/m1_p2_l1_probe"
N_DRAWS = 12
N_CONTROL = 6


def main():
    cfg = json.load(open(CFG, encoding="utf-8"))
    param, seed = cfg["parameter"], cfg["seed"]
    epk = cfg["errors_per_key"]
    budget = param["t"]  # BF-Max budget = t, as in the probe

    # collect recorded BFMAX failures
    failures = []
    for gid in cfg["groups"]:
        p = os.path.join(RUN, gid, "samples_BFMAX.jsonl")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                rec = json.loads(line)
                failures.append((gid, rec["key_id"], rec["error_id"]))
    print(f"recorded BFMAX failures: {failures}")

    pools = {}
    for gid, gspec in cfg["groups"].items():
        if any(f[0] == gid for f in failures) or gid == "G0":
            pools[gid] = KeyPool(seed, param, gid, gspec)

    report = {"budget": budget, "n_draws": N_DRAWS, "failures": [], "controls": []}
    for gid, kid, eid in failures:
        pool = pools[gid]
        ki = int(kid.split("-")[-1])
        key = pool.keys[ki]
        assert key.key_id == kid
        egen = make_error_generator(seed, gid, kid, param, cfg["groups"][gid], key, pool.ncws.get(kid))
        e = egen(eid)
        s0 = key.syndrome_from_global(e)
        t0 = time.time()
        det = bf_max(key, s0.copy(), budget, tie_break="first")
        reproduced = not det.success
        successes = 0
        for i in range(N_DRAWS):
            r = bf_max(key, s0.copy(), budget, tie_break="prf", salt=i.to_bytes(2, "big"))
            successes += int(r.success)
        row = {
            "group": gid, "key_id": kid, "error_id": eid,
            "deterministic_failure_reproduced": reproduced,
            "prf_successes": successes, "prf_draws": N_DRAWS,
            "seconds": round(time.time() - t0, 1),
        }
        report["failures"].append(row)
        print(json.dumps(row), flush=True)

    # control: samples that succeeded deterministically should mostly keep succeeding
    gid = "G0"
    pool = pools[gid]
    key = pool.keys[0]
    egen = make_error_generator(seed, gid, key.key_id, param, cfg["groups"][gid], key, None)
    checked = 0
    for eid in range(epk):
        if checked >= N_CONTROL:
            break
        e = egen(eid)
        s0 = key.syndrome_from_global(e)
        det = bf_max(key, s0.copy(), budget, tie_break="first")
        if det.success:
            succ = 0
            for i in range(4):
                succ += int(bf_max(key, s0.copy(), budget, tie_break="prf", salt=i.to_bytes(2, "big")).success)
            report["controls"].append({"error_id": eid, "prf_successes": succ, "prf_draws": 4})
            checked += 1
            print(f"control err={eid}: prf {succ}/4", flush=True)

    os.makedirs(os.path.join(RUN, "tiebreak"), exist_ok=True)
    with open(os.path.join(RUN, "tiebreak", "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("saved ->", os.path.join(RUN, "tiebreak", "report.json"))


if __name__ == "__main__":
    main()
