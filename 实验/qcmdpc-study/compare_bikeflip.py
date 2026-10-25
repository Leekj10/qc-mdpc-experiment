"""BIKE-Flip v5.2 (plan D0) empirical comparator at P1' -- closes review R2-M2.2 / D1.

Runs CLASSIC base (C0), FRO-2 (C4), and the spec-exact BIKE-Flip port on IDENTICAL
(H,e,s) triples (same frozen seeds / pools / generators as formal_m5.py), so all three
arms are paired. BIKE-Flip constants for P1' (4801,45,92) are DERIVED from the spec
A.2.4 affine-tangent formula (validated: reproduces official L1/L3/L5 constants and
their integer thresholds exactly; see tests/test_bikeflip.py). delta=3 (Level-1 value,
the nearest official level) and NbIter=7 (spec) are documented choices -- no official
BIKE-Flip constants exist for the scaled P1' set, exactly as for BGF at P1.

Success criterion is the study's (zero residual syndrome), identical for all three arms
and equal to BIKE-Flip Algorithm 1's `s = eH^T` check.

Output: results/compare_bikeflip/report.json
Usage:
  python compare_bikeflip.py --keys-per-group 16 --errors-per-key 500     # probe
  python compare_bikeflip.py --keys-per-group 92 --errors-per-key 3000    # formal scale
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.decoders import build_decoder
from qcmdpc.generators import KeyPool, make_error_generator
from qcmdpc.stats import wilson_upper
from qcmdpc.bikeflip import bike_flip, derive_bikeflip_affine
from search_m4 import CANDIDATES

OUT = "results/compare_bikeflip"
PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
SEED = 20260901
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": None}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": None, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": None, "kappa": 12, "max_syn_weight": None,
                    "require_better_than_canonical": True}, "fresh_from": 8},
}
CARRIER_ARMS = ["C0_base", "C4_first_p2"]
BF_DELTA = 3       # Level-1 delta (nearest official level); documented choice for P1'
BF_NBITER = 7      # spec NbIter (all official levels use 7)


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def run_group(gid: str, keys_per_group: int, E: int, bf_ab, bf_delta: int, bf_nbiter: int) -> dict:
    g = GROUPS[gid]
    spec = dict(g["spec"])
    n_keys = min(g["fresh_from"] + keys_per_group, 100)  # 100 = formal M5 pool; --keys-per-group 94 reproduces the exact formal key ranges (G0/G3 8-99, G2 6-99)
    spec["n_keys"] = n_keys
    t0 = time.time()
    pool = KeyPool(SEED, PARAM, gid, spec)
    idxs = list(range(g["fresh_from"], n_keys))
    decs = {n: build_decoder(n, CANDIDATES[n], PARAM["d"], PARAM["t"], PARAM["r"]) for n in CARRIER_ARMS}
    a, b = bf_ab
    arms = CARRIER_ARMS + ["BIKE_Flip"]
    per_key = {n: [] for n in arms}
    fail_idx = {n: set() for n in arms}
    bf_conv_iters = {}   # convergence-iteration histogram for BIKE-Flip
    n_samples = 0
    for ki in idxs:
        key = pool.keys[ki]
        gen = make_error_generator(SEED, gid, key.key_id, PARAM, spec, key, pool.ncws.get(key.key_id))
        counts = {n: 0 for n in arms}
        for eid in range(E):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            for name in CARRIER_ARMS:
                if not decs[name](key, s0.copy()).success:
                    counts[name] += 1
                    fail_idx[name].add((ki, eid))
            bfres = bike_flip(key, s0.copy(), a, b, bf_delta, bf_nbiter)
            if not bfres.success:
                counts["BIKE_Flip"] += 1
                fail_idx["BIKE_Flip"].add((ki, eid))
            else:
                ci = bfres.iters_to_success
                bf_conv_iters[ci] = bf_conv_iters.get(ci, 0) + 1
            n_samples += 1
        for name in arms:
            per_key[name].append(counts[name])
        done = ki - idxs[0] + 1
        if done % 4 == 0 or done == len(idxs):
            print(f"  [{gid}] {done}/{len(idxs)} keys, {time.time()-t0:.0f}s", flush=True)

    res = {"gid": gid, "n_keys": len(idxs), "E_per_key": E, "n_samples": n_samples,
           "bf_convergence_iters": {str(k): v for k, v in sorted(bf_conv_iters.items(), key=lambda x: (x[0] is None, x[0]))},
           "seconds": round(time.time() - t0, 1)}
    for name in arms:
        f = len(fail_idx[name])
        u = wilson_upper(f, n_samples)
        res[name] = {"failures": f, "trials": n_samples, "dfr": f / n_samples,
                     "upper95": u, "log10_upper95": float(np.log10(u)),
                     "per_key_failures": per_key[name]}
    # paired McNemar: BIKE-Flip vs each carrier arm (identical H,e,s)
    res["paired"] = {}
    for base in CARRIER_ARMS:
        bb = len(fail_idx[base] - fail_idx["BIKE_Flip"])   # base-only failures (BF rescued)
        cc = len(fail_idx["BIKE_Flip"] - fail_idx[base])   # BF-only failures (BF new)
        res["paired"][f"BF_vs_{base}"] = {"base_only": bb, "bf_only": cc,
                                          "both": len(fail_idx[base] & fail_idx["BIKE_Flip"]),
                                          "mcnemar_exact_p": mcnemar_exact(bb, cc)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys-per-group", type=int, default=16)
    ap.add_argument("--errors-per-key", type=int, default=500)
    ap.add_argument("--groups", default=",".join(GROUPS))
    ap.add_argument("--bf-delta", type=int, default=BF_DELTA)
    ap.add_argument("--bf-nbiter", type=int, default=BF_NBITER)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    a, b, Savg = derive_bikeflip_affine(PARAM["r"], PARAM["d"], PARAM["t"])
    print(f"BIKE-Flip P1' derived affine: a={a:.12g} b={b:.12g} Savg={Savg} "
          f"delta={args.bf_delta} NbIter={args.bf_nbiter}", flush=True)
    os.makedirs(args.out, exist_ok=True)
    report = {"param": PARAM, "E_per_key": args.errors_per_key, "keys_per_group": args.keys_per_group,
              "bikeflip": {"a": a, "b": b, "Savg": Savg, "delta": args.bf_delta, "nb_iter": args.bf_nbiter,
                           "source": "spec v5.2 A.2.4 derived; validated in tests/test_bikeflip.py"},
              "groups": {}}
    want = [x.strip() for x in args.groups.split(",") if x.strip()]
    for gid in want:
        print(f"[{gid}] starting ({time.strftime('%H:%M:%S')})", flush=True)
        r = run_group(gid, args.keys_per_group, args.errors_per_key, (a, b), args.bf_delta, args.bf_nbiter)
        report["groups"][gid] = r
        with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        c0, c4, bf = r["C0_base"], r["C4_first_p2"], r["BIKE_Flip"]
        print(f"[{gid}] C0={c0['failures']}/{c0['trials']}={c0['dfr']:.3e}  "
              f"C4={c4['failures']}/{c4['trials']}={c4['dfr']:.3e}  "
              f"BF={bf['failures']}/{bf['trials']}={bf['dfr']:.3e}  ({r['seconds']}s)", flush=True)

    # summary table + worst-group
    print("\n=== BIKE-Flip vs C0 vs C4 (P1', identical H,e,s) ===")
    for gid, r in report["groups"].items():
        print(f"{gid:8s} C0 {r['C0_base']['dfr']:.3e} | C4 {r['C4_first_p2']['dfr']:.3e} | "
              f"BF {r['BIKE_Flip']['dfr']:.3e} | BF conv iters {r['bf_convergence_iters']}")
    arms = CARRIER_ARMS + ["BIKE_Flip"]
    j = {n: max(report["groups"][g][n]["log10_upper95"] for g in report["groups"]) for n in arms}
    report["worst_group_log10U"] = j
    print("worst-group log10 U95:", {k: round(v, 4) for k, v in j.items()})
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("saved ->", os.path.join(args.out, "report.json"))


if __name__ == "__main__":
    main()
