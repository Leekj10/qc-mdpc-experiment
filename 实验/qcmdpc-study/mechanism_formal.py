"""P1-8 (review_round1.md): failure-mechanism breakdown at formal scale.

DA alternative-explanation (a): is FRO-2's gain a mechanism shift or just
fewer catastrophic over-flips? M6 had only 7 base failures - too small.
This run reuses the EXACT formal M5 pools (same seeds => same keys; first
1000 error_ids per key = paired subset of the formal 3000) and records,
per sample and arm: success, failure mode (frozen taxonomy), first-round
flip count. Documented scale reduction (E 3000->1000) for this secondary
analysis; ~3h runtime, group-level checkpointing.

Outputs per group/arm: mode distribution, first-round flip-count stats,
paired transition matrix (base mode -> FRO-2 outcome).
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
from qcmdpc.taxonomy import classify_failure
from search_m4 import CANDIDATES
from formal_m5 import GROUPS, PARAM, SEED

OUT = "results/mechanism_formal"
E_SUB = 1000
ARMS = ["C0_base", "C4_first_p2"]
TAXONOMY_MAX_ITER = int(CANDIDATES["C0_base"]["max_iter"])


def run_group(gid: str) -> dict:
    g = GROUPS[gid]
    t0 = time.time()
    pool = KeyPool(SEED, PARAM, gid, g["spec"])
    idxs = list(range(g["fresh_from"], len(pool.keys)))
    decs = {n: build_decoder(n, CANDIDERS[n] if False else CANDIDATES[n], PARAM["d"], PARAM["t"], PARAM["r"]) for n in ARMS}
    modes = {n: {} for n in ARMS}
    trans = {}
    first_flips = {n: [] for n in ARMS}
    n_samples = 0
    for ki in idxs:
        key = pool.keys[ki]
        gen = make_error_generator(SEED, gid, key.key_id, PARAM, g["spec"], key, pool.ncws.get(key.key_id))
        for eid in range(E_SUB):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            e_sup = set(int(x) for x in np.nonzero(e)[0])
            outs = {}
            for name in ARMS:
                r = decs[name](key, s0.copy(), record_flips=True)
                m = classify_failure(r, e_sup, max_iter=TAXONOMY_MAX_ITER)
                modes[name][m] = modes[name].get(m, 0) + 1
                ff = r.flip_counts[0] if r.flip_counts else 0
                first_flips[name].append(ff)
                outs[name] = (m, r.success)
            b, c = outs["C0_base"], outs["C4_first_p2"]
            if not b[1] or not c[1]:
                key_t = f"{b[0]}->{'success' if c[1] else c[0]}"
                trans[key_t] = trans.get(key_t, 0) + 1
            n_samples += 1
        if (ki - idxs[0] + 1) % 20 == 0:
            print(f"  [{gid}] {ki - idxs[0] + 1}/{len(idxs)} keys ({time.time()-t0:.0f}s)", flush=True)
    res = {
        "gid": gid, "n_keys": len(idxs), "E_sub": E_SUB, "n_samples": n_samples,
        "modes": modes, "transitions": trans,
        "first_flip_mean": {n: float(np.mean(v)) for n, v in first_flips.items()},
        "first_flip_p95": {n: float(np.percentile(v, 95)) for n, v in first_flips.items()},
        "seconds": round(time.time() - t0, 1),
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default=",".join(GROUPS))
    args = ap.parse_args()
    want = [x.strip() for x in args.groups.split(",") if x.strip()]
    os.makedirs(OUT, exist_ok=True)
    for gid in want:
        gf = os.path.join(OUT, f"group_{gid}.json")
        if os.path.exists(gf):
            print(f"[{gid}] done, skip", flush=True)
            continue
        print(f"[{gid}] starting {time.strftime('%H:%M:%S')}", flush=True)
        r = run_group(gid)
        with open(gf, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=1)
        print(f"[{gid}] modes_base={r['modes']['C0_base']} modes_fro={r['modes']['C4_first_p2']} "
              f"first_flip_mean={r['first_flip_mean']} ({r['seconds']}s)", flush=True)


if __name__ == "__main__":
    main()
