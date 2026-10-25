"""P1-8: formal-scale failure-mode breakdown (review R3-M3.1 / DA alt-explanation (a)).

Question: does FRO-2 (C4) reduce conditional DFR by suppressing a SPECIFIC failure
mechanism (early mis-flips -> genuine mechanism shift) or by uniformly reducing all
failure modes (variance reduction on the first-iteration flip count)? The M6 pilot had
only 7 events; this runs the full formal M5 population.

Two-pass per sample (keeps cost ~= the plain formal run):
  (1) run C0_base and C4_first_p2 WITHOUT flip logging (fast);
  (2) for any arm that FAILS, re-run that arm WITH record_flips (deterministic => identical
      trajectory) and classify the failure mode via qcmdpc.taxonomy.
Also builds the paired C0->C4 transition (rescued / new / both) broken down by mode.

Identical frozen population to formal_m5.py: P1' (4801,45,92), fresh keys (G0/G3 idx>=8,
G2 idx>=6, n_keys=100), 3000 errors/key, identical (H,e,s). The C0/C4 failure totals MUST
reproduce results/m5_formal/report.json (C0 = 282/372/141; C4 = 68/68/31) -- a built-in
reproducibility check on the whole pipeline.

Output: results/m5_mechanism/report.json
Usage:
  python formal_m5_mechanism.py --keys-per-group 8 --errors-per-key 500 --groups G0   # smoke
  python formal_m5_mechanism.py                                                        # formal
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
from qcmdpc.taxonomy import classify_failure, MODES
from search_m4 import CANDIDATES

OUT = "results/m5_mechanism"
PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
SEED = 20260901
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 100}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 100, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 100, "kappa": 12, "max_syn_weight": None,
                    "require_better_than_canonical": True}, "fresh_from": 8},
}
ARMS = ["C0_base", "C4_first_p2"]
FAIL_MODES = [m for m in MODES if m != "success"]
TAXONOMY_MAX_ITER = int(CANDIDATES["C0_base"]["max_iter"])


def run_group(gid: str, E: int, keys_per_group: int) -> dict:
    g = GROUPS[gid]
    t0 = time.time()
    pool = KeyPool(SEED, PARAM, gid, g["spec"])
    idxs = list(range(g["fresh_from"], min(g["fresh_from"] + keys_per_group, len(pool.keys))))
    decs = {n: build_decoder(n, CANDIDATES[n], PARAM["d"], PARAM["t"], PARAM["r"]) for n in ARMS}
    modes = {n: {m: 0 for m in FAIL_MODES} for n in ARMS}
    fails = {n: 0 for n in ARMS}
    trans = {"both_fail": 0, "c0_only_rescued": 0, "c4_only_new": 0, "concordant_ok": 0,
             "rescued_by_c0_mode": {}, "new_by_c4_mode": {}}
    n_samples = 0
    for ki in idxs:
        key = pool.keys[ki]
        gen = make_error_generator(SEED, gid, key.key_id, PARAM, g["spec"], key, pool.ncws.get(key.key_id))
        for eid in range(E):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            r0 = decs["C0_base"](key, s0.copy())
            r4 = decs["C4_first_p2"](key, s0.copy())
            f0, f4 = (not r0.success), (not r4.success)
            m0 = m4 = None
            if f0:
                e_sup = set(int(x) for x in np.nonzero(e)[0])
                rr = decs["C0_base"](key, s0.copy(), record_flips=True)
                m0 = classify_failure(rr, e_sup, max_iter=TAXONOMY_MAX_ITER)
                modes["C0_base"][m0] = modes["C0_base"].get(m0, 0) + 1
                fails["C0_base"] += 1
            if f4:
                e_sup = set(int(x) for x in np.nonzero(e)[0])
                rr = decs["C4_first_p2"](key, s0.copy(), record_flips=True)
                m4 = classify_failure(rr, e_sup, max_iter=TAXONOMY_MAX_ITER)
                modes["C4_first_p2"][m4] = modes["C4_first_p2"].get(m4, 0) + 1
                fails["C4_first_p2"] += 1
            if f0 and f4:
                trans["both_fail"] += 1
            elif f0:
                trans["c0_only_rescued"] += 1
                trans["rescued_by_c0_mode"][m0] = trans["rescued_by_c0_mode"].get(m0, 0) + 1
            elif f4:
                trans["c4_only_new"] += 1
                trans["new_by_c4_mode"][m4] = trans["new_by_c4_mode"].get(m4, 0) + 1
            else:
                trans["concordant_ok"] += 1
            n_samples += 1
        done = ki - idxs[0] + 1
        if done % 8 == 0 or done == len(idxs):
            print(f"  [{gid}] {done}/{len(idxs)} keys, {time.time()-t0:.0f}s, "
                  f"C0 fails={fails['C0_base']} C4 fails={fails['C4_first_p2']}", flush=True)
    return {"gid": gid, "n_keys": len(idxs), "E_per_key": E, "n_samples": n_samples,
            "fails": fails, "failure_modes": modes, "transitions": trans,
            "seconds": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors-per-key", type=int, default=3000)
    ap.add_argument("--keys-per-group", type=int, default=100)
    ap.add_argument("--groups", default=",".join(GROUPS))
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rpath = os.path.join(args.out, "report.json")
    report = {
        "param": PARAM,
        "E_per_key": args.errors_per_key,
        "keys_per_group": args.keys_per_group,
        "arms": ARMS,
        "taxonomy": {
            "priority": ["divergence", "period2", "stagnation", "early_misflip", "other"],
            "early_misflip_window": "ceil(max_iter/4)",
            "max_iter": TAXONOMY_MAX_ITER,
        },
        "groups": {},
    }
    for gid in [x.strip() for x in args.groups.split(",") if x.strip()]:
        gfile = os.path.join(args.out, f"group_{gid}.json")
        if os.path.exists(gfile):
            print(f"[{gid}] already done, skipping", flush=True)
            report["groups"][gid] = json.load(open(gfile, encoding="utf-8"))
            continue
        print(f"[{gid}] starting ({time.strftime('%H:%M:%S')})", flush=True)
        r = run_group(gid, args.errors_per_key, args.keys_per_group)
        with open(gfile, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=1)
        report["groups"][gid] = r
        with open(rpath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print(f"[{gid}] done: C0 fails={r['fails']['C0_base']} modes={r['failure_modes']['C0_base']} | "
              f"C4 fails={r['fails']['C4_first_p2']} modes={r['failure_modes']['C4_first_p2']} | "
              f"rescued={r['transitions']['c0_only_rescued']} (by C0 mode {r['transitions']['rescued_by_c0_mode']}) "
              f"new={r['transitions']['c4_only_new']} both={r['transitions']['both_fail']} ({r['seconds']}s)", flush=True)
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("saved ->", rpath)


if __name__ == "__main__":
    main()
