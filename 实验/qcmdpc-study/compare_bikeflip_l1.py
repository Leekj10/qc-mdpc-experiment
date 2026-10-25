"""BIKE-Flip v5.2 spec-exact comparison at BIKE Level-1 (native parameters).

This is the FAIREST BIKE-Flip setting: L1 = (r=12323, d=71, t=134) with the OFFICIAL
spec constants (NbIter=7, delta=3, a=0.006254868353074983, b=11.101432337243956) -- no
derivation, no borrowing, no budget mismatch. Compared against the study carriers
C0 (CLASSIC static-t) and C4 (FRO-2 = first-round +2) on identical (H,e,s), all under
the study's static-t, zero-syndrome semantics.

At L1 every strong decoder is expected to be zero-failure at Python-accessible sample
sizes, so DFR is NON-resolvable (rule-of-three bound only, ~3e-4 at 8k/cell -- weaker
than the C-reference 1e6-1e7 runs, and reported as such). The discriminative signals are
the CONVERGENCE-ITERATION distribution and the WEAK-key behavior: does BIKE-Flip's
gathering-defense delta-floor keep WEAK-12 convergence as fast as RAND, relative to the
carriers? (The C-reference L1 transfer study found FRO-2 makes WEAK-12 need a 3rd
iteration 2.07x more often than RAND; here we get BIKE-Flip's native-profile analogue.)

Output: results/cmp_bf_l1/report.json
Usage:
  python compare_bikeflip_l1.py --keys-per-group 3 --errors-per-key 50 --groups RAND   # smoke
  python compare_bikeflip_l1.py --keys-per-group 16 --errors-per-key 500               # full
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
from qcmdpc.stats import wilson_upper
from qcmdpc.bikeflip import bike_flip, BIKEFLIP_OFFICIAL
from search_m4 import CANDIDATES

OUT = "results/cmp_bf_l1"
PARAM = {"id": "L1", "r": 12323, "d": 71, "t": 134, "n0": 2}
SEED = 20260901
OFF = BIKEFLIP_OFFICIAL[(12323, 71, 134)]   # official Level-1 constants (spec p.14)
GROUPS = {
    "RAND":   {"spec": {"type": "random", "n_keys": None}},
    "WEAK12": {"spec": {"type": "type1", "n_keys": None, "delta": 12}},
    "NCW16":  {"spec": {"type": "ncw", "n_keys": None, "kappa": 16, "max_syn_weight": None,
                        "require_better_than_canonical": True}},
}
CARRIER_ARMS = ["C0_base", "C4_first_p2"]
ARMS = CARRIER_ARMS + ["BIKE_Flip"]


def run_group(gid: str, keys_per_group: int, E: int) -> dict:
    g = GROUPS[gid]
    spec = dict(g["spec"]); spec["n_keys"] = keys_per_group
    t0 = time.time()
    pool = KeyPool(SEED, PARAM, gid, spec)
    decs = {n: build_decoder(n, CANDIDATES[n], PARAM["d"], PARAM["t"], PARAM["r"]) for n in CARRIER_ARMS}
    fails = {n: 0 for n in ARMS}
    iters = {n: {} for n in ARMS}   # convergence-iteration histogram over successes
    n_samples = 0
    for ki, key in enumerate(pool.keys):
        gen = make_error_generator(SEED, gid, key.key_id, PARAM, spec, key, pool.ncws.get(key.key_id))
        for eid in range(E):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            for name in CARRIER_ARMS:
                r = decs[name](key, s0.copy())
                if r.success:
                    iters[name][r.iters_to_success] = iters[name].get(r.iters_to_success, 0) + 1
                else:
                    fails[name] += 1
            bfr = bike_flip(key, s0.copy(), OFF["a"], OFF["b"], OFF["delta"], OFF["nb_iter"])
            if bfr.success:
                iters["BIKE_Flip"][bfr.iters_to_success] = iters["BIKE_Flip"].get(bfr.iters_to_success, 0) + 1
            else:
                fails["BIKE_Flip"] += 1
            n_samples += 1
        if (ki + 1) % 4 == 0 or (ki + 1) == len(pool.keys):
            print(f"  [{gid}] {ki+1}/{len(pool.keys)} keys, {time.time()-t0:.0f}s", flush=True)

    res = {"gid": gid, "n_keys": len(pool.keys), "E_per_key": E, "n_samples": n_samples,
           "seconds": round(time.time() - t0, 1),
           "iters_hist": {n: {str(k): v for k, v in sorted(d.items())} for n, d in iters.items()}}
    for name in ARMS:
        f = fails[name]
        u = wilson_upper(f, n_samples)
        h = iters[name]
        tot = sum(h.values())
        mean_it = (sum(k * v for k, v in h.items()) / tot) if tot else None
        res[name] = {"failures": f, "trials": n_samples, "dfr": f / n_samples,
                     "upper95": u, "mean_conv_iters": mean_it}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys-per-group", type=int, default=16)
    ap.add_argument("--errors-per-key", type=int, default=500)
    ap.add_argument("--groups", default=",".join(GROUPS))
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    print(f"BIKE-Flip L1 OFFICIAL constants: {OFF}", flush=True)
    report = {"param": PARAM, "bikeflip_official": OFF, "E_per_key": args.errors_per_key,
              "keys_per_group": args.keys_per_group, "groups": {}}
    for gid in [x.strip() for x in args.groups.split(",") if x.strip()]:
        print(f"[{gid}] starting ({time.strftime('%H:%M:%S')})", flush=True)
        r = run_group(gid, args.keys_per_group, args.errors_per_key)
        report["groups"][gid] = r
        with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print(f"[{gid}] fails C0={r['C0_base']['failures']} C4={r['C4_first_p2']['failures']} "
              f"BF={r['BIKE_Flip']['failures']} / {r['n_samples']} | mean conv iters "
              f"C0={r['C0_base']['mean_conv_iters']:.2f} C4={r['C4_first_p2']['mean_conv_iters']:.2f} "
              f"BF={r['BIKE_Flip']['mean_conv_iters']:.2f} ({r['seconds']}s)", flush=True)
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("saved ->", os.path.join(args.out, "report.json"))


if __name__ == "__main__":
    main()
