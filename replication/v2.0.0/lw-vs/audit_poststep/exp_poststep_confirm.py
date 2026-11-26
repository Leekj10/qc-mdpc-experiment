#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fresh-key confirmation of the post-step interaction.

The P1/P2 factor experiments used G0 keys 54..99.  This script reruns the four
primary arms with a fresh key and error stream (group CF) at the same two work
points, so a replication cannot be attributed to the original key pool.

Arms: plain_0, plain_p2, post_0, post_p2.
Primary estimand: (post_p2 - post_0) - (plain_p2 - plain_0), risk-difference
scale, key-clustered bootstrap.

This is a fresh-key confirmation of a diagnostic pattern, not a production or
official-decoder confirmation.

Run
---
  python -I lw-vs/audit_poststep/exp_poststep_confirm.py --phase smoke --point P1 --nkeys 2 --nerr 100
  python -I lw-vs/audit_poststep/exp_poststep_confirm.py --phase run --point P1 --nkeys 46 --nerr 2000
  python -I lw-vs/audit_poststep/exp_poststep_confirm.py --phase run --point P2 --nkeys 46 --nerr 2000
  python -I lw-vs/audit_poststep/exp_poststep_confirm.py --phase analyze --path <npz>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STUDY = ROOT / "实验" / "qcmdpc-study"
OUT = HERE / "poststep_factor"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(HERE))

from qcmdpc.decoders import bgf_vasseur, build_decoder, make_threshold  # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402
from qcmdpc.stats import cluster_bootstrap_paired  # noqa: E402

from exp_poststep_factor import (POINTS, GROUP_SPEC, SEED, TEST_KEYS,  # noqa: E402
                                 MAX_ITER, factor_decode, bgf_compat_decode)

CONFIRM_GROUP = "CF"
PRIMARY = ["plain_0", "plain_p2", "post_0", "post_p2"]
N_WORKERS = int(os.environ.get("PCF_WORKERS", "8"))

_POOLS = {}


def _get_pool(point_id, group_id):
    key = (point_id, group_id)
    if key not in _POOLS:
        _POOLS[key] = KeyPool(SEED, POINTS[point_id], group_id, GROUP_SPEC)
    return _POOLS[key]


# ------------------------------------------------------------------- per-key job
def _work(job):
    ki, n_err, point_id, group_id = job
    param = POINTS[point_id]
    pool = _get_pool(point_id, group_id)
    key = pool.keys[ki]
    gen = make_error_generator(SEED, group_id, key.key_id, param, GROUP_SPEC, key, None)
    base = make_threshold({"type": "classic"}, param["d"], param["t"], 2 * param["r"])

    fail = {a: np.zeros(n_err, dtype=np.uint8) for a in PRIMARY}
    main_rounds = {a: np.zeros(n_err, dtype=np.int16) for a in PRIMARY}
    total_scans = {a: np.zeros(n_err, dtype=np.int16) for a in PRIMARY}
    first_black = {a: np.zeros(n_err, dtype=np.int16) for a in PRIMARY}

    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        for a in PRIMARY:
            off = 2 if a.endswith("_p2") else 0
            post = "none" if a.startswith("plain") else "both"
            r = factor_decode(key, s0, base, offset=off, poststep=post, maskbase=False)
            fail[a][eid] = 0 if r["success"] else 1
            main_rounds[a][eid] = r["main_rounds"]
            total_scans[a][eid] = r["total_scans"]
            first_black[a][eid] = r["first_black"]
    return ki, fail, main_rounds, total_scans, first_black


# ----------------------------------------------------------------------- gates
def gate_classic_library(nkeys, nerr, point_id, group_id):
    """Factor-mode plain arms must match build_decoder(c0/c2) on fresh keys."""
    param = POINTS[point_id]
    pool = _get_pool(point_id, group_id)
    d, t, r = param["d"], param["t"], param["r"]
    dec0 = build_decoder("c0", {"algo": "bf_parallel",
                                "threshold": {"type": "classic"},
                                "max_iter": MAX_ITER}, d, t, r)
    dec2 = build_decoder("c2", {"algo": "bf_parallel",
                                "threshold": {"type": "offset",
                                              "base": {"type": "classic"},
                                              "offsets": [2, 0]},
                                "max_iter": MAX_ITER}, d, t, r)
    base = make_threshold({"type": "classic"}, d, t, 2 * r)
    total = same0 = same2 = 0
    for ki in TEST_KEYS[:min(3, nkeys)]:
        key = pool.keys[ki]
        gen = make_error_generator(SEED, group_id, key.key_id, param, GROUP_SPEC, key, None)
        for eid in range(min(200, nerr)):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            f0 = factor_decode(key, s0, base, offset=0, poststep="none")["success"]
            f2 = factor_decode(key, s0, base, offset=2, poststep="none")["success"]
            total += 1
            same0 += int(bool(dec0(key, s0.copy()).success) == bool(f0))
            same2 += int(bool(dec2(key, s0.copy()).success) == bool(f2))
    return {"pass": same0 == total and same2 == total,
            "plain_0": f"{same0}/{total}", "plain_p2": f"{same2}/{total}"}


def gate_bgf_port(nkeys, nerr, point_id, group_id):
    param = POINTS[point_id]
    pool = _get_pool(point_id, group_id)
    base = make_threshold({"type": "classic"}, param["d"], param["t"], 2 * param["r"])
    lo, hi = max(1, (param["d"] + 1) // 2), param["d"]

    def thr_for(offset):
        def thr(it, sw):
            return int(np.clip(base(it, sw) + (offset if it == 1 else 0), lo, hi))
        return thr

    total = same = 0
    for ki in TEST_KEYS[:min(3, nkeys)]:
        key = pool.keys[ki]
        gen = make_error_generator(SEED, group_id, key.key_id, param, GROUP_SPEC, key, None)
        for eid in range(min(200, nerr)):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            for off in (0, 2):
                lib = bgf_vasseur(key, s0.copy(), thr_for(off), MAX_ITER, 3)
                mine = bgf_compat_decode(key, s0, base, offset=off)
                total += 1
                same += int(lib.success == mine["success"]
                            and lib.n_iters_run == mine["n_iters_run"]
                            and lib.iters_to_success == mine["iters_to_success"]
                            and lib.flip_counts == mine["flip_counts"])
    return {"pass": same == total, "replica_vs_library": f"{same}/{total}"}


# ------------------------------------------------------------------------ run
def phase_run(point_id, nkeys, nerr, tag, group_id=CONFIRM_GROUP):
    keys = TEST_KEYS[:nkeys]
    t0 = time.time()
    print(f"[confirm] point {point_id} group {group_id}, keys {keys[0]}..{keys[-1]} "
          f"({len(keys)}), {nerr} errors/key, arms={PRIMARY}, workers={N_WORKERS}",
          flush=True)
    jobs = [(ki, nerr, point_id, group_id) for ki in keys]
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, len(keys))) as ex:
        res = list(ex.map(_work, jobs))
    res.sort(key=lambda x: x[0])

    out = {"keys": np.array(keys, dtype=np.int32),
           "e_per_key": np.array([nerr], dtype=np.int32),
           "arms": np.array(PRIMARY),
           "point_id": np.array([point_id]),
           "group_id": np.array([group_id])}
    for a in PRIMARY:
        out[f"fail_{a}"] = np.stack([r[1][a] for r in res])
        out[f"main_{a}"] = np.stack([r[2][a] for r in res])
        out[f"scans_{a}"] = np.stack([r[3][a] for r in res])
        out[f"first_{a}"] = np.stack([r[4][a] for r in res])
    p = OUT / f"poststep_confirm_{point_id}_{tag}.npz"
    np.savez_compressed(p, **out)
    print(f"[confirm] saved {p} ({time.time() - t0:.0f}s)", flush=True)
    return p


# -------------------------------------------------------------------- analyze
def _pair(counts, base, treat, E, b=10000, seed=20260905):
    boot = cluster_bootstrap_paired(counts[base], counts[treat], E, B=b, seed=seed)
    return {
        "base": base, "treat": treat,
        "failures_base": int(counts[base].sum()),
        "failures_treat": int(counts[treat].sum()),
        "dfr_base": float(counts[base].sum()) / (len(counts[base]) * E),
        "dfr_treat": float(counts[treat].sum()) / (len(counts[treat]) * E),
        "rr": boot["point"]["risk_ratio"],
        "rr_ci95": boot["ci"]["risk_ratio"],
    }


def _interaction(counts, E, b=10000, seed=20260905):
    x = ((counts["post_p2"] - counts["post_0"])
         - (counts["plain_p2"] - counts["plain_0"])) / E
    rng = np.random.default_rng(seed)
    n = len(x)
    idx = rng.integers(0, n, size=(b, n))
    boot = x[idx].mean(axis=1)
    return {
        "point": float(x.mean()),
        "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "per_key": x.tolist(),
    }


def phase_analyze(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"no npz at {p}")
    d = np.load(p)
    E = int(d["e_per_key"][0])
    nkeys = int(len(d["keys"]))
    point_id = str(d["point_id"][0])
    group_id = str(d["group_id"][0])
    param = POINTS[point_id]
    counts = {a: d[f"fail_{a}"].sum(axis=1).astype(np.int64) for a in PRIMARY}

    g1 = gate_classic_library(nkeys, E, point_id, group_id)
    g2 = gate_bgf_port(nkeys, E, point_id, group_id)
    rep = {
        "source": p.name, "point": point_id, "group": group_id,
        "params": param, "n_keys": nkeys, "errors_per_key": E,
        "trials_per_arm": nkeys * E,
        "gate_classic_library": g1,
        "gate_bgf_port": g2,
        "arms": {a: {"failures": int(counts[a].sum()),
                     "dfr": float(counts[a].sum()) / (nkeys * E)}
                 for a in PRIMARY},
        "contrasts": {},
        "interaction": _interaction(counts, E),
    }
    for base, treat in (("plain_0", "plain_p2"), ("post_0", "post_p2"),
                        ("plain_0", "post_0"), ("plain_p2", "post_p2")):
        rep["contrasts"][f"{treat}_vs_{base}"] = _pair(counts, base, treat, E)

    prim = rep["interaction"]
    lo, hi = prim["ci95"]
    if lo > 0:
        verdict = "CONFIRMED_ON_FRESH_KEYS"
    elif hi < 0:
        verdict = "SIGN_REVERSED_ON_FRESH_KEYS"
    else:
        verdict = "NOT_CONFIRMED_ON_FRESH_KEYS"
    rep["verdict"] = {"status": verdict,
                      "note": "fresh-key confirmation of a diagnostic pattern; not production"}

    x = counts["post_p2"] - counts["post_0"]
    y = counts["plain_p2"] - counts["plain_0"]
    rep["per_key_direction"] = {
        "post_p2_vs_post_0_worse_equal_better":
            [int((x > 0).sum()), int((x == 0).sum()), int((x < 0).sum())],
        "plain_p2_vs_plain_0_worse_equal_better":
            [int((y > 0).sum()), int((y == 0).sum()), int((y < 0).sum())],
    }

    out_json = OUT / f"poststep_confirm_summary_{point_id}.json"
    out_md = OUT / f"REPORT_zh_confirm_{point_id}.md"
    json.dump(rep, open(out_json, "w", encoding="utf-8"), indent=1)
    print(json.dumps(rep, indent=1))

    L = ["# 新鲜密钥确认（诊断性）", "",
         f"- 数据：`{p.name}`，{nkeys} 密钥 × {E} 误差；group {group_id}，"
         f"point {point_id}=(r={param['r']},d={param['d']},t={param['t']})。",
         f"- CLASSIC 库对照：{g1}",
         f"- BGF 兼容复现：{g2}", "",
         "## 1. 各臂", "", "| 臂 | 失败数 | DFR |", "|---|---:|---:|"]
    for a in PRIMARY:
        L.append(f"| {a} | {rep['arms'][a]['failures']} | {rep['arms'][a]['dfr']:.3e} |")
    L += ["", "## 2. 对比（RR>1 有利）", "",
          "| 对比 | 失败数 | RR [95% CI] |", "|---|---:|---|"]
    for k, v in rep["contrasts"].items():
        rr, (lo_, hi_) = v["rr"], v["rr_ci95"]
        L.append(f"| {k} | {v['failures_base']}/{v['failures_treat']} | "
                 f"{rr:.3f} [{lo_:.3f}, {hi_:.3f}] |")
    L += ["", "## 3. 交互", "",
          f"- 点估计 {prim['point']:.6f}，95% CI "
          f"[{prim['ci95'][0]:.6f}, {prim['ci95'][1]:.6f}]",
          f"- 判定：**{verdict}**",
          f"- 逐钥方向：{rep['per_key_direction']}", "",
          "## 4. 边界", "",
          "- 新鲜密钥降低密钥池伪影风险，但不是生产参数或官方译码器确认。",
          "- 仍为诊断性结果；论文中保留 diagnostic 标签。"]
    open(out_md, "w", encoding="utf-8").write("\n".join(L))
    print(f"[analyze] -> {out_json}")
    print(f"[analyze] -> {out_md}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["smoke", "run", "analyze"], required=True)
    ap.add_argument("--point", choices=sorted(POINTS), default="P1")
    ap.add_argument("--nkeys", type=int, default=46)
    ap.add_argument("--nerr", type=int, default=2000)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--group", default=CONFIRM_GROUP)
    ap.add_argument("--path", default=None)
    args = ap.parse_args()
    if args.phase == "smoke":
        p = phase_run(args.point, args.nkeys, args.nerr, args.tag or "pilot",
                      args.group)
        d = np.load(p)
        print("gate_classic_library:", json.dumps(
            gate_classic_library(args.nkeys, args.nerr, args.point, args.group), indent=1))
        print("gate_bgf_port:", json.dumps(
            gate_bgf_port(args.nkeys, args.nerr, args.point, args.group), indent=1))
    elif args.phase == "run":
        tag = args.tag or ("full" if args.nkeys == 46 and args.nerr == 2000 else "custom")
        p = phase_run(args.point, args.nkeys, args.nerr, tag, args.group)
        print("gate_classic_library:", json.dumps(
            gate_classic_library(args.nkeys, args.nerr, args.point, args.group), indent=1))
        print("gate_bgf_port:", json.dumps(
            gate_bgf_port(args.nkeys, args.nerr, args.point, args.group), indent=1))
    else:
        phase_analyze(args.path)


if __name__ == "__main__":
    main()
