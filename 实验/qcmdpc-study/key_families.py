"""Q2-D: key-FAMILY comparison under a FIXED error construction (review round-3, Q2 priority-2).

Broadens the weak-key evidence beyond Type-I. Three key families are compared under
the SAME uniform weight-t error construction (so the error distribution is held fixed
and only the KEY family varies):
    random   : plain random keys
    type1    : Type-I weak keys (run of delta=12 ones in h0)
    ncwadm   : near-codeword-ADMISSIBLE keys (admit a better-than-canonical (d,d)
               near-codeword) -- a capture-prone, gathering-ADJACENT structural
               weak-key family. NOTE: this is NOT the exact WWW2023 'gathering'
               class; it is labelled honestly as a near-codeword-rich proxy.
For each family: C0_base vs C4_first_p2 (frozen +2) on identical (H,e,s); per-key
counts, paired sign test, key-cluster bootstrap RR CI. Reports the C0 DFR gradient
across families (key-family severity under plain errors) and whether FRO-2 helps in
every family.

Output: results/q2_keyfamilies/report.json
Usage : python key_families.py [--config configs/q2_key_families.json]
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
from qcmdpc.generators import (KeyPool, _child_seed, make_error_generator,
                               uniform_fixed_weight)
from qcmdpc.stats import (cluster_bootstrap_paired, holm_adjust, mcnemar_exact,
                          sign_test_paired, wilson_upper)

OUT = "results/q2_keyfamilies"
BOOT_SEED = 20260905


def run(cfg):
    param, seed = cfg["parameter"], cfg["seed"]
    E = cfg["errors_per_key"]
    K = cfg["keys_per_group"]
    names = list(cfg["decoders"])
    n = 2 * param["r"]
    t0 = time.time()
    report = {"config": cfg.get("_path", "configs/q2_key_families.json"),
              "param": param, "E_per_key": E, "keys_per_group": K,
              "note": ("key-family comparison under FIXED uniform errors; ncwadm = "
                       "near-codeword-admissible (capture-prone, gathering-ADJACENT), "
                       "NOT the exact WWW2023 gathering class"),
              "families": {}}
    err_spec = {"type": "random"}  # hold the error construction fixed across families
    for fam, fspec in cfg["families"].items():
        spec = dict(fspec); spec["n_keys"] = K
        pool = KeyPool(seed, param, fam, spec)
        decs = {nm: build_decoder(nm, d, param["d"], param["t"], param["r"])
                for nm, d in cfg["decoders"].items()}
        per_key = {nm: [] for nm in names}
        fail_idx = {nm: [] for nm in names}
        n_samples = 0
        for ki, key in enumerate(pool.keys):
            counts = {nm: 0 for nm in names}
            for eid in range(E):
                rng = np.random.default_rng(_child_seed(seed, f"err|{fam}|{key.key_id}", eid))
                e = uniform_fixed_weight(rng, n, param["t"])
                s0 = key.syndrome_from_global(e)
                for nm in names:
                    if not decs[nm](key, s0.copy()).success:
                        counts[nm] += 1
                        fail_idx[nm].append((ki, eid))
                n_samples += 1
            for nm in names:
                per_key[nm].append(counts[nm])
        b, c = names[0], names[1]
        s0f, s4f = set(fail_idx[b]), set(fail_idx[c])
        entry = {"n_keys": K, "n_samples": n_samples,
                 "paired": {"c0_only": len(s0f - s4f), "c4_only": len(s4f - s0f),
                            "both": len(s0f & s4f),
                            "mcnemar_exact_p": mcnemar_exact(len(s0f - s4f), len(s4f - s0f))}}
        for nm in names:
            f = len(fail_idx[nm])
            u = wilson_upper(f, n_samples)
            entry[nm] = {"failures": f, "trials": n_samples, "dfr": f / n_samples,
                         "upper95": u, "log10_upper95": float(np.log10(u)),
                         "per_key_failures": per_key[nm]}
        entry["sign_test"] = sign_test_paired(per_key[b], per_key[c])
        entry["cluster_bootstrap"] = cluster_bootstrap_paired(per_key[b], per_key[c], E,
                                                              B=10000, seed=BOOT_SEED)
        report["families"][fam] = entry
        print(f"[{fam:7s}] C0={entry[b]['failures']}/{n_samples} ({entry[b]['dfr']:.3e})  "
              f"FRO2={entry[c]['failures']}/{n_samples} ({entry[c]['dfr']:.3e})  "
              f"RR={entry['cluster_bootstrap']['point']['risk_ratio']:.2f} "
              f"CI[{entry['cluster_bootstrap']['ci']['risk_ratio'][0]:.2f},"
              f"{entry['cluster_bootstrap']['ci']['risk_ratio'][1]:.2f}] "
              f"({time.time()-t0:.0f}s)", flush=True)
    # C0 key-family severity gradient vs random
    base = report["families"]["random"][names[0]]["dfr"]
    report["c0_family_gradient"] = {f: {"c0_dfr": report["families"][f][names[0]]["dfr"],
                                        "ratio_vs_random": (report["families"][f][names[0]]["dfr"] / base) if base > 0 else None}
                                    for f in cfg["families"]}
    sp = [report["families"][f]["sign_test"]["p_two_sided"] for f in cfg["families"]]
    report["holm_sign"] = {f: p for f, p in zip(cfg["families"], holm_adjust(sp))}
    report["seconds"] = round(time.time() - t0, 1)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/q2_key_families.json")
    args = ap.parse_args()
    cfg = json.load(open(args.config, encoding="utf-8"))
    cfg["_path"] = args.config
    os.makedirs(OUT, exist_ok=True)
    rep = run(cfg)
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print("\n== C0 key-family gradient (vs random, uniform errors) ==")
    for f, g in rep["c0_family_gradient"].items():
        print(f"  {f:7s} C0 DFR={g['c0_dfr']:.3e}  x{g['ratio_vs_random']:.2f}")
    print("saved ->", os.path.join(OUT, "report.json"))


if __name__ == "__main__":
    main()
