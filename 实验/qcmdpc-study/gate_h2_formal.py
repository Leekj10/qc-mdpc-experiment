"""Interim formal H2 gate: C0_base vs C4_first_p2 on FRESH test keys, high N.

Key isolation: M4 search used pool indices [0, train+val) of the 8/6/8-key
pools; S4 confirmation used indices train+val..n of the same pools. This run
extends the pools (20/15/20 keys; prefix-identical by frozen seed derivation)
and evaluates ONLY on indices >= 8 (G0/G3) and >= 6 (G2) - keys never touched
by any search or previous confirmation.

Gate (pre-registered): worst-group log10 U0.95 improvement >= 0.5 AND
G0 non-inferiority U(C4) <= 1.2 * U(C0).
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
from search_m4 import CANDIDATES

OUT = "results/gate_h2_formal"
PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
SEED = 20260901
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 20}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 15, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 20, "kappa": 12, "max_syn_weight": None, "require_better_than_canonical": True}, "fresh_from": 8},
}
E_PER_KEY = 2500
DECODERS = ["C0_base", "C4_first_p2"]


def main():
    os.makedirs(OUT, exist_ok=True)
    decs = {n: build_decoder(n, CANDIDATES[n], PARAM["d"], PARAM["t"], PARAM["r"]) for n in DECODERS}
    report = {"param": PARAM, "E_per_key": E_PER_KEY, "decoders": DECODERS, "groups": {}}

    for gid, g in GROUPS.items():
        pool = KeyPool(SEED, PARAM, gid, g["spec"])
        idxs = list(range(g["fresh_from"], len(pool.keys)))
        gens = {
            pool.keys[i].key_id: make_error_generator(SEED, gid, pool.keys[i].key_id, PARAM, g["spec"], pool.keys[i], pool.ncws.get(pool.keys[i].key_id))
            for i in idxs
        }
        g_out = {"n_fresh_keys": len(idxs), "key_ids": [pool.keys[i].key_id for i in idxs]}
        for name in DECODERS:
            dec = decs[name]
            fails, trials = 0, 0
            per_key = []
            t0 = time.time()
            for i in idxs:
                key = pool.keys[i]
                gen = gens[key.key_id]
                kf = 0
                for eid in range(E_PER_KEY):
                    e = gen(eid)
                    s0 = key.syndrome_from_global(e)
                    if not dec(key, s0).success:
                        fails += 1
                        kf += 1
                    trials += 1
                per_key.append(kf)
            u = wilson_upper(fails, trials)
            g_out[name] = {
                "failures": fails, "trials": trials, "dfr": fails / trials,
                "upper95": u, "log10_upper95": float(np.log10(u)),
                "per_key_failures": per_key, "seconds": round(time.time() - t0, 1),
            }
            print(f"[{gid}] {name}: {fails}/{trials} DFR={fails/trials:.3e} U95={u:.3e} ({g_out[name]['seconds']}s)", flush=True)
        report["groups"][gid] = g_out

    j = {n: max(report["groups"][g][n]["log10_upper95"] for g in GROUPS) for n in DECODERS}
    report["worst_group_log10U"] = j
    report["improvement_log10"] = j["C0_base"] - j["C4_first_p2"]
    report["gate_improvement_ge_0.5"] = bool(report["improvement_log10"] >= 0.5)
    u0 = report["groups"]["G0"]
    report["gate_noninferior_G0"] = bool(u0["C4_first_p2"]["upper95"] <= 1.2 * u0["C0_base"]["upper95"])
    report["gate_pass"] = report["gate_improvement_ge_0.5"] and report["gate_noninferior_G0"]
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("GATE:", {k: report[k] for k in ["improvement_log10", "gate_improvement_ge_0.5", "gate_noninferior_G0", "gate_pass"]})
    print("saved ->", os.path.join(OUT, "report.json"))


if __name__ == "__main__":
    main()
