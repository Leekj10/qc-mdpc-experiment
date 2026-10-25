"""M4 schedule search: successive halving on P1' TRAIN keys, selection on VAL keys.

Pre-registered protocol (configs/pre_register.json):
- objective J(theta) = max_g log10 U_0.95,g(theta) over groups {G0, G2_d12, G3}
- constraint: U_0.95,G0(theta) <= 1.20 * U_0.95,G0(base)
- whole-key split 60/20/20 (train/val/test) by frozen index; TEST keys are
  never touched here (single final confirmation run happens after locking).
- candidate set frozen below BEFORE any evaluation.

Rounds:
  S1 coarse : all candidates x train keys x E1 errors -> keep top K + anchor
  S2 middle : survivors x (train+val) keys x E2 errors -> select by VAL J
Outputs DRIS* (best deterministic offset) and CPS* (best dual-table CPS),
or reports that none beats the base anchor under the constraint.
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

BASE_CFG = "configs/h2_p1prime_cps.json"
OUT = "results/m4_search"
E1, E2 = 200, 600
KEEP_S1 = 3
NONINFER_RATIO = 1.20

# ---- frozen candidate set (integer offsets on the CLASSIC base) ----
def _off(offsets):
    return {"algo": "bf_parallel", "threshold": {"type": "offset", "base": {"type": "classic"}, "offsets": offsets}, "max_iter": 20, "fixed_iters": False}

def _cps(offsets, jitters):
    return {"algo": "cps", "base_threshold": {"type": "offset", "base": {"type": "classic"}, "offsets": offsets}, "jitters": jitters, "max_iter": 20, "fixed_iters": False}

CANDIDATES = {
    "C0_base":      _off([0]),
    "C1_unif_p1":   _off([1]),
    "C2_unif_p2":   _off([2]),
    "C3_unif_m1":   _off([-1]),
    "C4_first_p2":  _off([2, 0]),
    "C5_first_p4":  _off([4, 0]),
    "C6_f2_r1":     _off([2, 1]),
    "C7_cps_0_2":   _cps([0], [0, 2]),
    "C8_cps_0_1":   _cps([0], [0, 1]),
}
ANCHOR = "C0_base"


def split_keys(n: int):
    tr = int(n * 0.6)
    va = max(1, int(n * 0.8) - tr) if n >= 5 else 0
    train = list(range(tr))
    val = list(range(tr, tr + va))
    test = list(range(tr + va, n))
    return train, val, test


def evaluate(spec, pools, gens, key_idx_by_group, errors_per_key, param):
    """Returns per-group (failures, trials) pooled over the given key indices."""
    dec = build_decoder("X", spec, param["d"], param["t"], param["r"])
    out = {}
    for gid, idxs in key_idx_by_group.items():
        pool, gen_map = pools[gid], gens[gid]
        fails = 0
        trials = 0
        for ki in idxs:
            key = pool.keys[ki]
            gen = gen_map[key.key_id]
            for eid in range(errors_per_key):
                e = gen(eid)
                s0 = key.syndrome_from_global(e)
                if not dec(key, s0).success:
                    fails += 1
                trials += 1
        out[gid] = (fails, trials)
    return out


def objective(per_group):
    us = {g: wilson_upper(f, n) for g, (f, n) in per_group.items()}
    j = max(np.log10(u) for u in us.values())
    return float(j), us


def main():
    cfg = json.load(open(BASE_CFG, encoding="utf-8"))
    param, seed, groups = cfg["parameter"], cfg["seed"], cfg["groups"]
    os.makedirs(OUT, exist_ok=True)

    pools, gens, splits = {}, {}, {}
    for gid, gspec in groups.items():
        pool = KeyPool(seed, param, gid, gspec)
        pools[gid] = pool
        gens[gid] = {
            k.key_id: make_error_generator(seed, gid, k.key_id, param, gspec, k, pool.ncws.get(k.key_id))
            for k in pool.keys
        }
        splits[gid] = split_keys(len(pool.keys))
    print("splits:", {g: [len(x) for x in s] for g, s in splits.items()}, flush=True)

    report = {"E1": E1, "E2": E2, "candidates": list(CANDIDATES), "rounds": {}}

    # ---------------- S1: coarse on TRAIN ----------------
    train_idx = {g: splits[g][0] for g in groups}
    s1 = {}
    t0 = time.time()
    for name, spec in CANDIDATES.items():
        per_group = evaluate(spec, pools, gens, train_idx, E1, param)
        j, us = objective(per_group)
        s1[name] = {"J_train": j, "U": us, "counts": per_group}
        print(f"S1 {name:12s} J={j:.3f} U={ {g: f'{u:.2e}' for g, u in us.items()} }", flush=True)
    report["rounds"]["S1"] = s1
    ranked = sorted(s1, key=lambda k: s1[k]["J_train"])
    survivors = list(dict.fromkeys([ANCHOR] + ranked[:KEEP_S1]))
    print("S1 survivors:", survivors, f"({time.time()-t0:.0f}s)", flush=True)

    # ---------------- S2: middle on TRAIN+VAL, select by VAL ----------------
    trval_idx = {g: splits[g][0] + splits[g][1] for g in groups}
    val_idx = {g: splits[g][1] for g in groups}
    s2 = {}
    t0 = time.time()
    for name in survivors:
        spec = CANDIDATES[name]
        pg_all = evaluate(spec, pools, gens, trval_idx, E2, param)
        j_all, us_all = objective(pg_all)
        pg_val = evaluate(spec, pools, gens, val_idx, E2, param) if any(len(v) for v in val_idx.values()) else pg_all
        j_val, us_val = objective(pg_val)
        s2[name] = {"J_trainval": j_all, "U_trainval": us_all, "J_val": j_val, "U_val": us_val, "counts": pg_all}
        print(f"S2 {name:12s} J_val={j_val:.3f} J_all={j_all:.3f} U={ {g: f'{u:.2e}' for g, u in us_all.items()} }", flush=True)
    report["rounds"]["S2"] = s2

    # ---------------- constraint + selection ----------------
    base_u_g0 = s2[ANCHOR]["U_trainval"]["G0"]
    feasible = {
        n: v for n, v in s2.items()
        if v["U_trainval"]["G0"] <= NONINFER_RATIO * base_u_g0
    }
    report["constraint"] = {"base_U_G0": base_u_g0, "ratio": NONINFER_RATIO, "feasible": list(feasible)}
    dris_pool = {n: v for n, v in feasible.items() if not n.startswith(("C7", "C8"))}
    cps_pool = {n: v for n, v in feasible.items() if n.startswith(("C7", "C8"))}
    dris_star = min(dris_pool, key=lambda n: dris_pool[n]["J_val"]) if dris_pool else None
    cps_star = min(cps_pool, key=lambda n: cps_pool[n]["J_val"]) if cps_pool else None
    base_j = s2[ANCHOR]["J_val"]
    report["selection"] = {
        "DRIS_star": dris_star,
        "CPS_star": cps_star,
        "DRIS_beats_base": bool(dris_star and dris_pool[dris_star]["J_val"] < base_j - 1e-12),
        "CPS_beats_base": bool(cps_star and cps_pool[cps_star]["J_val"] < base_j - 1e-12),
    }
    with open(os.path.join(OUT, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print("selection:", report["selection"], flush=True)
    print("saved ->", os.path.join(OUT, "report.json"))


if __name__ == "__main__":
    main()
