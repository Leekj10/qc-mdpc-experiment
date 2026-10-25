"""Formal M5 run (pre-registered decision run, amendment v1).

Protocol:
- P1' (r=4801, d=45, t=92), 100 keys/group, E=3000/key (amendment A1);
- fresh keys only: G0/G3 indices >= 8, G2 >= 6 (never touched by search);
- decoders: C0_base vs C4_first_p2, identical (H,e,s) triples (paired);
- per-sample paired outcomes logged -> exact McNemar on discordant pairs;
- gate: worst-group log10 U0.95 improvement >= 0.5 AND G0 non-inferior <= 1.2x;
- group-level checkpointing: each group's result is written immediately;
  resume with --groups G2_d12 etc. (completed groups are skipped).

Estimated runtime: ~1.8M decodes @ ~17-20ms => 9-10 h (background).
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
from search_m4 import CANDIDATES

OUT = "results/m5_formal"
PARAM = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
SEED = 20260901
E_PER_KEY = 3000
GROUPS = {
    "G0": {"spec": {"type": "random", "n_keys": 100}, "fresh_from": 8},
    "G2_d12": {"spec": {"type": "type1", "n_keys": 100, "delta": 12}, "fresh_from": 6},
    "G3": {"spec": {"type": "ncw", "n_keys": 100, "kappa": 12, "max_syn_weight": None, "require_better_than_canonical": True}, "fresh_from": 8},
}
DECODERS = ["C0_base", "C4_first_p2"]


def mcnemar_exact(b: int, c: int) -> float:
    """Exact two-sided McNemar on discordant counts b (C0-only failures), c (C4-only)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def run_group(gid: str) -> dict:
    g = GROUPS[gid]
    t0 = time.time()
    pool = KeyPool(SEED, PARAM, gid, g["spec"])
    idxs = list(range(g["fresh_from"], len(pool.keys)))
    decs = {n: build_decoder(n, CANDIDATES[n], PARAM["d"], PARAM["t"], PARAM["r"]) for n in DECODERS}
    per_key = {n: [] for n in DECODERS}
    fail_idx = {n: [] for n in DECODERS}  # list of (key_pos, error_id)
    n_samples = 0
    for ki in idxs:
        key = pool.keys[ki]
        gen = make_error_generator(SEED, gid, key.key_id, PARAM, g["spec"], key, pool.ncws.get(key.key_id))
        counts = {n: 0 for n in DECODERS}
        for eid in range(E_PER_KEY):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            for name in DECODERS:
                if not decs[name](key, s0.copy()).success:
                    counts[name] += 1
                    fail_idx[name].append((ki, eid))
            n_samples += 1
        for name in DECODERS:
            per_key[name].append(counts[name])
        if (ki - idxs[0] + 1) % 10 == 0:
            el = time.time() - t0
            print(f"  [{gid}] {ki - idxs[0] + 1}/{len(idxs)} keys, {el:.0f}s elapsed", flush=True)

    s0f, s4f = set(fail_idx["C0_base"]), set(fail_idx["C4_first_p2"])
    b = len(s0f - s4f)  # rescued by C4
    c = len(s4f - s0f)  # new under C4
    both = len(s0f & s4f)
    res = {"gid": gid, "n_keys": len(idxs), "E_per_key": E_PER_KEY, "n_samples": n_samples,
           "paired": {"c0_only": b, "c4_only": c, "both": both,
                      "mcnemar_exact_p": mcnemar_exact(b, c)},
           "seconds": round(time.time() - t0, 1)}
    for name in DECODERS:
        f = len(fail_idx[name])
        u = wilson_upper(f, n_samples)
        res[name] = {"failures": f, "trials": n_samples, "dfr": f / n_samples,
                     "upper95": u, "log10_upper95": float(np.log10(u)),
                     "per_key_failures": per_key[name]}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default=",".join(GROUPS), help="comma list, for resume")
    args = ap.parse_args()
    want = [x.strip() for x in args.groups.split(",") if x.strip()]
    os.makedirs(OUT, exist_ok=True)
    report_path = os.path.join(OUT, "report.json")
    report = json.load(open(report_path, encoding="utf-8")) if os.path.exists(report_path) else {
        "param": PARAM, "E_per_key": E_PER_KEY, "amendment": "configs/pre_register_amendment_v1.md",
        "groups": {}}

    for gid in want:
        gfile = os.path.join(OUT, f"group_{gid}.json")
        if os.path.exists(gfile):
            print(f"[{gid}] already done, skipping (delete {gfile} to rerun)", flush=True)
            report["groups"][gid] = json.load(open(gfile, encoding="utf-8"))
            continue
        print(f"[{gid}] starting ({time.strftime('%H:%M:%S')})", flush=True)
        r = run_group(gid)
        with open(gfile, "w", encoding="utf-8") as f:
            json.dump(r, f)
        report["groups"][gid] = r
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print(f"[{gid}] done: C0={r['C0_base']['failures']}/{r['C0_base']['trials']} "
              f"C4={r['C4_first_p2']['failures']}/{r['C4_first_p2']['trials']} "
              f"McNemar p={r['paired']['mcnemar_exact_p']:.2e} ({r['seconds']}s)", flush=True)

    # final gate over completed groups
    done = [g for g in GROUPS if g in report["groups"]]
    if done:
        j = {n: max(report["groups"][g][n]["log10_upper95"] for g in done) for n in DECODERS}
        report["worst_group_log10U"] = j
        report["improvement_log10"] = j["C0_base"] - j["C4_first_p2"]
        report["gate_improvement_ge_0.5"] = bool(report["improvement_log10"] >= 0.5)
        if "G0" in report["groups"]:
            u0 = report["groups"]["G0"]
            report["gate_noninferior_G0"] = bool(u0["C4_first_p2"]["upper95"] <= 1.2 * u0["C0_base"]["upper95"])
        report["gate_pass"] = bool(report.get("gate_improvement_ge_0.5") and report.get("gate_noninferior_G0"))
        report["groups_completed"] = done
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print("GATE:", {k: report[k] for k in ["improvement_log10", "gate_improvement_ge_0.5", "gate_noninferior_G0", "gate_pass", "groups_completed"]})


if __name__ == "__main__":
    main()
