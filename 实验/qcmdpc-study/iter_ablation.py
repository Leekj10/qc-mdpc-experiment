"""Q2-B: iteration-budget ablation (review round-3, Q2 priority-4).

Keys, errors and thresholds are FIXED; only the maximum iteration budget varies
(7 / 10 / 20). Purpose: (i) show the C0-vs-FRO-2 contrast is not an artifact of the
iteration budget (NbIter fairness, cf. the BIKE-Flip NbIter=7-vs-20 discussion);
(ii) quantify how much of each arm's failure mass lives in the >7-iteration tail.

Reuses a small paired pool (P1' formal-pool prefix) on RAND and WEAK-12. For each
(group, budget, arm): failures/trials/DFR/Wilson U95 + per-key counts; per
(group, budget): paired sign test and key-cluster bootstrap RR CI.

Output: results/q2_iterablation/report.json
Usage : python iter_ablation.py [--config configs/q2_iter_ablation.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, make_error_generator
from qcmdpc.stats import cluster_bootstrap_paired, sign_test_paired, wilson_upper

OUT = "results/q2_iterablation"
BOOT_SEED = 20260905


def run(cfg):
    param, seed = cfg["parameter"], cfg["seed"]
    E = cfg["errors_per_key"]
    K = cfg["keys_per_group"]
    budgets = cfg["budgets"]
    names = list(cfg["decoders"])
    t0 = time.time()
    report = {"config": cfg.get("_path", "configs/q2_iter_ablation.json"),
              "param": param, "E_per_key": E, "keys_per_group": K,
              "budgets": budgets, "groups": {}}
    for gid, gspec in cfg["groups"].items():
        fresh_from = cfg["fresh_from"][gid]
        spec = dict(gspec); spec["n_keys"] = fresh_from + K
        pool = KeyPool(seed, param, gid, spec)
        idxs = list(range(fresh_from, fresh_from + K))
        gens = {pool.keys[ki].key_id: make_error_generator(seed, gid, pool.keys[ki].key_id,
                                                          param, spec, pool.keys[ki],
                                                          pool.ncws.get(pool.keys[ki].key_id))
                for ki in idxs}
        grep = {"gid": gid, "budgets": {}}
        for budget in budgets:
            decs = {}
            for nm, d in cfg["decoders"].items():
                dd = dict(d); dd["max_iter"] = budget
                decs[nm] = build_decoder(nm, dd, param["d"], param["t"], param["r"])
            per_key = {nm: [] for nm in names}
            n_samples = 0
            for ki in idxs:
                key = pool.keys[ki]
                gen = gens[key.key_id]
                counts = {nm: 0 for nm in names}
                for eid in range(E):
                    e = gen(eid)
                    s0 = key.syndrome_from_global(e)
                    for nm in names:
                        if not decs[nm](key, s0.copy()).success:
                            counts[nm] += 1
                    n_samples += 1
                for nm in names:
                    per_key[nm].append(counts[nm])
            b, c = names[0], names[1]
            entry = {"n_samples": n_samples}
            for nm in names:
                f = sum(per_key[nm])
                u = wilson_upper(f, n_samples)
                entry[nm] = {"failures": f, "trials": n_samples, "dfr": f / n_samples,
                             "upper95": u, "per_key_failures": per_key[nm]}
            entry["sign_test"] = sign_test_paired(per_key[b], per_key[c])
            entry["cluster_bootstrap"] = cluster_bootstrap_paired(per_key[b], per_key[c], E,
                                                                  B=10000, seed=BOOT_SEED)
            grep["budgets"][str(budget)] = entry
            print(f"[{gid} budget={budget}] C0={entry[b]['failures']}/{n_samples} "
                  f"({entry[b]['dfr']:.3e})  FRO2={entry[c]['failures']}/{n_samples} "
                  f"({entry[c]['dfr']:.3e})  RR={entry['cluster_bootstrap']['point']['risk_ratio']:.2f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        report["groups"][gid] = grep
    report["seconds"] = round(time.time() - t0, 1)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/q2_iter_ablation.json")
    args = ap.parse_args()
    cfg = json.load(open(args.config, encoding="utf-8"))
    cfg["_path"] = args.config
    os.makedirs(OUT, exist_ok=True)
    rep = run(cfg)
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print("saved ->", os.path.join(OUT, "report.json"))


if __name__ == "__main__":
    main()
