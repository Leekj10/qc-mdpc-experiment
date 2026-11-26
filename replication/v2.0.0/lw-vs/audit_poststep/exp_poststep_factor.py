#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Post-step factor experiment for the first-round threshold window.

Question
--------
On the CLASSIC carrier, a one-shot round-1 +2 lowers failure.  On the
GRAY_BGF implementation it raises failure.  The two implementations differ in
more than the post-step: BGF also stops on a blocked round and counts its
sub-steps as iterations.  This experiment holds the carrier, instances,
stopping rule, budget accounting and later-round baseline fixed, and switches
only the BGF-style post-step (black re-check + gray step) on or off.

This is a diagnostic experiment.  It is not a confirmatory test of the paper's
main claims and does not modify the frozen experiment library.

Arms
----
plain_0 / plain_p2      classic parallel BF, no post-step
post_0 / post_p2        classic + BGF-style post-step after round one
recheck_0 / recheck_p2  black re-check only (exploratory component)
gray_0 / gray_p2        gray step only (exploratory component)
postmask_p2             post-step with the gray mask taken from the un-offset
                        baseline threshold (exploratory mask control)

Gates
-----
1. plain_* must reproduce the archived CLASSIC per-instance failures exactly.
2. A bgf-compatible replica (sub-steps counted, blocked-stop) must reproduce
   bgf_vasseur and the archived BGF failures exactly on a verification sample.

Run
---
  python -I lw-vs/audit_poststep/exp_poststep_factor.py --phase smoke --nkeys 2 --nerr 100
  python -I lw-vs/audit_poststep/exp_poststep_factor.py --phase run --nkeys 46 --nerr 2000
  python -I lw-vs/audit_poststep/exp_poststep_factor.py --phase analyze
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

from qcmdpc.decoders import bgf_vasseur, make_threshold  # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402
from qcmdpc.stats import cluster_bootstrap_paired, mcnemar_exact  # noqa: E402

SEED = 20260901
POINTS = {
    "P1": {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2},
    "P2": {"id": "P2", "r": 3001, "d": 37, "t": 66, "n0": 2},
}
DEFAULT_POINT = "P1"
DEFAULT_GROUP = "G0"
GROUP_SPEC = {"type": "random", "n_keys": 100}
TEST_KEYS = list(range(54, 100))
E_PER_KEY = 2000
MAX_ITER = 20
GRAY_DELTA = 3
N_WORKERS = int(os.environ.get("PF_WORKERS", "8"))

ARMS = {
    "plain_0": {"offset": 0, "poststep": "none", "maskbase": False},
    "plain_p2": {"offset": 2, "poststep": "none", "maskbase": False},
    "post_0": {"offset": 0, "poststep": "both", "maskbase": False},
    "post_p2": {"offset": 2, "poststep": "both", "maskbase": False},
    "recheck_0": {"offset": 0, "poststep": "recheck", "maskbase": False},
    "recheck_p2": {"offset": 2, "poststep": "recheck", "maskbase": False},
    "gray_0": {"offset": 0, "poststep": "gray", "maskbase": False},
    "gray_p2": {"offset": 2, "poststep": "gray", "maskbase": False},
    "postmask_p2": {"offset": 2, "poststep": "both", "maskbase": True},
}
ARM_ORDER = list(ARMS)

_POOLS = {}


def _get_pool(point_id, group_id):
    key = (point_id, group_id)
    if key not in _POOLS:
        _POOLS[key] = KeyPool(SEED, POINTS[point_id], group_id, GROUP_SPEC)
    return _POOLS[key]


# ------------------------------------------------------------------ factor mode
def factor_decode(key, s0, base_thr, offset=0, poststep="none", maskbase=False):
    """Classic carrier with an optional BGF-style post-step after round one.

    Stopping, budget accounting and later-round baseline are the classic ones:
    no blocked-stop, 20 main rounds, post-step scans are extra work.
    """
    d = key.d
    lo, hi = max(1, (d + 1) // 2), d
    bound = (d + 1) // 2 + 1
    s = s0.copy()
    main_rounds = 0
    total_scans = 0
    total_flips = 0
    first_black = 0
    success_at = None

    while main_rounds < MAX_ITER and s.sum() != 0:
        main_rounds += 1
        S = int(s.sum())
        tau0 = int(np.clip(base_thr(main_rounds - 1, S), lo, hi))
        tau = int(np.clip(tau0 + (offset if main_rounds == 1 else 0), lo, hi))
        alpha = key.upc_fast(s)
        total_scans += 1
        black = np.nonzero(alpha >= tau)[0]
        if main_rounds == 1:
            first_black = int(black.size)
        gray = np.empty(0, dtype=np.int64)
        if main_rounds == 1 and poststep in ("both", "gray"):
            mtau = tau0 if maskbase else tau
            gray = np.nonzero((alpha < mtau) & (alpha + GRAY_DELTA >= mtau))[0]

        for p in black:
            s = key.flip(s, int(p))
        total_flips += int(black.size)
        if s.sum() == 0:
            success_at = main_rounds

        if main_rounds == 1 and poststep in ("both", "recheck", "gray") and s.sum() != 0:
            if poststep in ("both", "recheck"):
                alpha2 = key.upc_fast(s)
                total_scans += 1
                reflip = [int(p) for p in black if alpha2[int(p)] >= bound]
                for p in reflip:
                    s = key.flip(s, p)
                total_flips += len(reflip)
                if s.sum() == 0:
                    success_at = main_rounds
            if poststep in ("both", "gray") and s.sum() != 0 and gray.size:
                alpha3 = key.upc_fast(s)
                total_scans += 1
                gflip = [int(p) for p in gray if alpha3[int(p)] >= bound]
                for p in gflip:
                    s = key.flip(s, p)
                total_flips += len(gflip)
                if s.sum() == 0:
                    success_at = main_rounds

    return {
        "success": bool(s.sum() == 0),
        "main_rounds": main_rounds,
        "total_scans": total_scans,
        "total_flips": total_flips,
        "first_black": first_black,
        "success_at": success_at,
    }


# ------------------------------------------------------------- bgf-compatible
def bgf_compat_decode(key, s0, base_thr, offset=0):
    """Exact GRAY_BGF control flow with an optional round-1 offset.

    Used only to validate that the post-step primitives match bgf_vasseur.
    """
    d = key.d
    lo, hi = max(1, (d + 1) // 2), d
    bound = (d + 1) // 2 + 1
    s = s0.copy()
    it = 0
    blocked = False
    success_at = None
    flip_counts = []
    n_black_first = 0

    while it < MAX_ITER and s.sum() != 0 and not blocked:
        it += 1
        alpha = key.upc_fast(s)
        tau = int(np.clip(base_thr(it, int(s.sum())) + (offset if it == 1 else 0), lo, hi))
        blocked = True
        flips = np.nonzero(alpha >= tau)[0]
        black = [int(p) for p in flips]
        gray = [int(p) for p in np.nonzero((alpha < tau) & (alpha + GRAY_DELTA >= tau))[0]]
        if it == 1:
            n_black_first = len(black)
        for p in black:
            s = key.flip(s, p)
        if black:
            blocked = False
        flip_counts.append(len(black))
        if s.sum() == 0 and success_at is None:
            success_at = it
        if it < 2 and it < MAX_ITER and s.sum() != 0:
            it += 1
            alpha2 = key.upc_fast(s)
            reflip = [p for p in black if alpha2[p] >= bound]
            for p in reflip:
                s = key.flip(s, p)
            if reflip:
                blocked = False
            flip_counts.append(len(reflip))
            if s.sum() == 0 and success_at is None:
                success_at = it
            if it < MAX_ITER and s.sum() != 0:
                it += 1
                alpha3 = key.upc_fast(s)
                gflip = [p for p in gray if alpha3[p] >= bound]
                for p in gflip:
                    s = key.flip(s, p)
                if gflip:
                    blocked = False
                flip_counts.append(len(gflip))
                if s.sum() == 0 and success_at is None:
                    success_at = it
    return {
        "success": bool(s.sum() == 0),
        "n_iters_run": it,
        "iters_to_success": success_at,
        "flip_counts": flip_counts,
        "first_black": n_black_first,
    }


# ------------------------------------------------------------------- per-key job
def _work(job):
    ki, n_err, point_id, group_id = job
    param = POINTS[point_id]
    pool = _get_pool(point_id, group_id)
    key = pool.keys[ki]
    gen = make_error_generator(SEED, group_id, key.key_id, param, GROUP_SPEC, key, None)
    base = make_threshold({"type": "classic"}, param["d"], param["t"], 2 * param["r"])

    fail = {a: np.zeros(n_err, dtype=np.uint8) for a in ARM_ORDER}
    main_rounds = {a: np.zeros(n_err, dtype=np.int16) for a in ARM_ORDER}
    total_scans = {a: np.zeros(n_err, dtype=np.int16) for a in ARM_ORDER}
    total_flips = {a: np.zeros(n_err, dtype=np.int32) for a in ARM_ORDER}
    first_black = {a: np.zeros(n_err, dtype=np.int16) for a in ARM_ORDER}

    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        for a in ARM_ORDER:
            spec = ARMS[a]
            r = factor_decode(
                key, s0, base,
                offset=spec["offset"],
                poststep=spec["poststep"],
                maskbase=spec["maskbase"],
            )
            fail[a][eid] = 0 if r["success"] else 1
            main_rounds[a][eid] = r["main_rounds"]
            total_scans[a][eid] = r["total_scans"]
            total_flips[a][eid] = r["total_flips"]
            first_black[a][eid] = r["first_black"]
    return ki, fail, main_rounds, total_scans, total_flips, first_black


# ----------------------------------------------------------------------- gates
def gate_classic(d, nkeys, nerr, point_id=DEFAULT_POINT):
    """Compare factor-mode plain arms with the archived CLASSIC arrays."""
    if point_id != "P1":
        return {"pass": None, "reason": f"no archived CLASSIC array for {point_id}"}
    p = ROOT / "lw-vs" / "results" / "decoder_transfer" / "decoder_transfer_full.npz"
    if not p.exists():
        return {"pass": False, "reason": "archive missing"}
    arc = np.load(p)
    if not np.array_equal(arc["keys"][:nkeys], np.array(TEST_KEYS[:nkeys])):
        return {"pass": False, "reason": "key mismatch"}
    out = {}
    ok = True
    for arm, keyname, firstname in (
        ("plain_0", "fail_classic_0", "first_classic_0"),
        ("plain_p2", "fail_classic_p2", "first_classic_p2"),
    ):
        same = int((arc[keyname][:nkeys, :nerr] == d[f"fail_{arm}"][:nkeys, :nerr]).sum())
        total = int(nkeys * nerr)
        same_first = int((arc[firstname][:nkeys, :nerr] == d[f"first_{arm}"][:nkeys, :nerr]).sum())
        out[arm] = {
            "fail_exact": f"{same}/{total}",
            "first_flip_exact": f"{same_first}/{total}",
            "pass": same == total and same_first == total,
        }
        ok = ok and out[arm]["pass"]
    return {"pass": ok, "cells": out}


def gate_bgf(nkeys, nerr, point_id=DEFAULT_POINT, group_id=DEFAULT_GROUP):
    """Validate the bgf-compatible replica against bgf_vasseur and the archive."""
    param = POINTS[point_id]
    pool = _get_pool(point_id, group_id)
    base = make_threshold({"type": "classic"}, param["d"], param["t"], 2 * param["r"])
    p = ROOT / "lw-vs" / "results" / "decoder_transfer" / "decoder_transfer_full.npz"
    arc = np.load(p) if (point_id == "P1" and p.exists()) else None
    lo, hi = max(1, (param["d"] + 1) // 2), param["d"]

    def thr_for(offset):
        def thr(it, sw):
            return int(np.clip(base(it, sw) + (offset if it == 1 else 0), lo, hi))
        return thr

    total = 0
    same = 0
    same_arc0 = 0
    same_arc2 = 0
    for ki in TEST_KEYS[:min(3, nkeys)]:
        key = pool.keys[ki]
        gen = make_error_generator(SEED, group_id, key.key_id, param, GROUP_SPEC, key, None)
        row = TEST_KEYS.index(ki)
        for eid in range(min(200, nerr)):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            for off, arckey in ((0, "fail_bgf_0"), (2, "fail_bgf_p2")):
                lib = bgf_vasseur(key, s0.copy(), thr_for(off), MAX_ITER, GRAY_DELTA)
                mine = bgf_compat_decode(key, s0, base, offset=off)
                total += 1
                same += int(
                    lib.success == mine["success"]
                    and lib.n_iters_run == mine["n_iters_run"]
                    and lib.iters_to_success == mine["iters_to_success"]
                    and lib.flip_counts == mine["flip_counts"]
                )
                if arc is not None:
                    a = int(arc[arckey][row, eid])
                    b = 0 if mine["success"] else 1
                    same_arc0 += int(a == b and off == 0)
                    same_arc2 += int(a == b and off == 2)
    n_arc = total // 2
    return {
        "pass": same == total and (arc is None or (same_arc0 == n_arc and same_arc2 == n_arc)),
        "replica_vs_library": f"{same}/{total}",
        "replica_vs_archive_off0": (f"{same_arc0}/{n_arc}" if arc is not None else "N/A"),
        "replica_vs_archive_off2": (f"{same_arc2}/{n_arc}" if arc is not None else "N/A"),
    }


# ------------------------------------------------------------------------ run
def phase_run(nkeys, nerr, tag, point_id=DEFAULT_POINT, group_id=DEFAULT_GROUP):
    keys = TEST_KEYS[:nkeys]
    t0 = time.time()
    print(f"[run] point {point_id} group {group_id}, keys {keys[0]}..{keys[-1]} "
          f"({len(keys)}), {nerr} errors/key, {len(ARM_ORDER)} arms, "
          f"workers={N_WORKERS}", flush=True)
    jobs = [(ki, nerr, point_id, group_id) for ki in keys]
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, len(keys))) as ex:
        res = list(ex.map(_work, jobs))
    res.sort(key=lambda x: x[0])

    out = {
        "keys": np.array(keys, dtype=np.int32),
        "e_per_key": np.array([nerr], dtype=np.int32),
        "arms": np.array(ARM_ORDER),
        "point_id": np.array([point_id]),
        "group_id": np.array([group_id]),
    }
    for a in ARM_ORDER:
        out[f"fail_{a}"] = np.stack([r[1][a] for r in res])
        out[f"main_{a}"] = np.stack([r[2][a] for r in res])
        out[f"scans_{a}"] = np.stack([r[3][a] for r in res])
        out[f"flips_{a}"] = np.stack([r[4][a] for r in res])
        out[f"first_{a}"] = np.stack([r[5][a] for r in res])
    p = OUT / f"poststep_factor_{tag}.npz"
    np.savez_compressed(p, **out)
    print(f"[run] saved {p} ({time.time() - t0:.0f}s)", flush=True)
    return p


# -------------------------------------------------------------------- analyze
def _pair(counts, base, treat, E, b=10000, seed=20260905):
    boot = cluster_bootstrap_paired(counts[base], counts[treat], E, B=b, seed=seed)
    b_only = 0
    t_only = 0
    return {
        "base": base,
        "treat": treat,
        "failures_base": int(counts[base].sum()),
        "failures_treat": int(counts[treat].sum()),
        "dfr_base": float(counts[base].sum()) / (len(counts[base]) * E),
        "dfr_treat": float(counts[treat].sum()) / (len(counts[treat]) * E),
        "rr": boot["point"]["risk_ratio"],
        "rr_ci95": boot["ci"]["risk_ratio"],
    }


def _interaction(counts, E, cells, b=10000, seed=20260905):
    """Mean paired interaction on the risk-difference scale.

    cells = ((post_base, post_treat), (plain_base, plain_treat)).
    """
    (pb, pt), (qb, qt) = cells
    x = ((counts[pt] - counts[pb]) - (counts[qt] - counts[qb])) / E
    rng = np.random.default_rng(seed)
    n = len(x)
    idx = rng.integers(0, n, size=(b, n))
    boot = x[idx].mean(axis=1)
    return {
        "definition": f"({pt}-{pb}) - ({qt}-{qb})",
        "point": float(x.mean()),
        "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "per_key": x.tolist(),
    }


def phase_analyze(path=None):
    if path is None:
        full = OUT / "poststep_factor_full.npz"
        pilot = OUT / "poststep_factor_pilot.npz"
        p = full if full.exists() else pilot
    else:
        p = Path(path)
    if not p.exists():
        raise SystemExit("no poststep npz found; run --phase run first")
    d = np.load(p)
    E = int(d["e_per_key"][0])
    nkeys = int(len(d["keys"]))
    point_id = str(d["point_id"][0]) if "point_id" in d else DEFAULT_POINT
    group_id = str(d["group_id"][0]) if "group_id" in d else DEFAULT_GROUP
    param = POINTS.get(point_id, POINTS[DEFAULT_POINT])
    counts = {a: d[f"fail_{a}"].sum(axis=1).astype(np.int64) for a in ARM_ORDER}

    gate1 = gate_classic(d, nkeys, E, point_id)
    gate2 = gate_bgf(nkeys, E, point_id, group_id)
    rep = {
        "source": p.name,
        "point": point_id,
        "group": group_id,
        "params": param,
        "keys": [int(d["keys"][0]), int(d["keys"][-1])],
        "n_keys": nkeys,
        "errors_per_key": E,
        "trials_per_arm": int(nkeys * E),
        "gate_classic": gate1,
        "gate_bgf_replica": gate2,
        "arms": {},
        "contrasts": {},
        "interactions": {},
        "cost": {},
    }

    for a in ARM_ORDER:
        rep["arms"][a] = {
            "failures": int(counts[a].sum()),
            "dfr": float(counts[a].sum()) / (nkeys * E),
            "mean_main_rounds": float(d[f"main_{a}"].mean()),
            "mean_total_scans": float(d[f"scans_{a}"].mean()),
            "mean_first_black": float(d[f"first_{a}"].mean()),
            "mean_total_flips": float(d[f"flips_{a}"].mean()),
        }

    for base, treat in (
        ("plain_0", "plain_p2"),
        ("post_0", "post_p2"),
        ("recheck_0", "recheck_p2"),
        ("gray_0", "gray_p2"),
        ("plain_0", "post_0"),
        ("post_0", "postmask_p2"),
        ("post_p2", "postmask_p2"),
    ):
        rep["contrasts"][f"{treat}_vs_{base}"] = _pair(counts, base, treat, E)

    rep["interactions"]["primary_both"] = _interaction(
        counts, E, (("post_0", "post_p2"), ("plain_0", "plain_p2")))
    rep["interactions"]["recheck_only"] = _interaction(
        counts, E, (("recheck_0", "recheck_p2"), ("plain_0", "plain_p2")))
    rep["interactions"]["gray_only"] = _interaction(
        counts, E, (("gray_0", "gray_p2"), ("plain_0", "plain_p2")))
    rep["interactions"]["maskbase_p2"] = _interaction(
        counts, E, (("post_0", "postmask_p2"), ("plain_0", "plain_p2")))

    prim = rep["interactions"]["primary_both"]
    lo, hi = prim["ci95"]
    if lo > 0:
        verdict = "POSTSTEP_INTERACTION_SUPPORTED"
    elif hi < 0:
        verdict = "POSTSTEP_INTERACTION_SIGN_REVERSED"
    else:
        verdict = "POSTSTEP_INTERACTION_NOT_SUPPORTED"
    rep["verdict"] = {
        "primary": verdict,
        "note": "diagnostic; aligned rules; not a confirmatory test",
    }

    summary_name = ("poststep_factor_summary.json" if point_id == "P1"
                    else f"poststep_factor_summary_{point_id}.json")
    report_name = ("REPORT_zh.md" if point_id == "P1"
                   else f"REPORT_zh_{point_id}.md")
    json.dump(rep, open(OUT / summary_name, "w", encoding="utf-8"), indent=1)
    print(json.dumps(rep, indent=1))

    # Chinese report
    L = []
    L.append("# 首轮后处理因子实验（诊断性，非确证）")
    L.append("")
    L.append(f"- 数据：`{p.name}`，{nkeys} 密钥 × {E} 误差。")
    L.append(f"- 工作点：{point_id} = (r={param['r']}, d={param['d']}, t={param['t']})。"
             "所有臂共用同一 (H,e,s)，仅后处理模块与首轮偏移不同。")
    L.append("- 规则对齐：20 个主轮、无翻转轮继续、后续轮使用普通二项阈值；后处理扫描单独计成本。")
    L.append("")
    L.append("## 0. 闸门")
    g1s = ("N/A (no archive)" if gate1.get("pass") is None
           else ("PASS" if gate1["pass"] else "FAIL"))
    L.append(f"- CLASSIC 复现：{g1s}")
    L.append(f"- BGF 复现（兼容模式）：{'PASS' if gate2['pass'] else 'FAIL'} "
             f"（vs 库 {gate2['replica_vs_library']}；vs 存档 off0/off2 "
             f"{gate2['replica_vs_archive_off0']} / {gate2['replica_vs_archive_off2']}）")
    L.append("")
    L.append("## 1. 各臂")
    L.append("")
    L.append("| 臂 | 失败数 | DFR | 平均主轮 | 平均总扫描 | 首轮主翻 |")
    L.append("|---|---:|---:|---:|---:|---:|")
    for a in ARM_ORDER:
        x = rep["arms"][a]
        L.append(f"| {a} | {x['failures']} | {x['dfr']:.3e} | "
                 f"{x['mean_main_rounds']:.3f} | {x['mean_total_scans']:.3f} | "
                 f"{x['mean_first_black']:.2f} |")
    L.append("")
    L.append("## 2. 组内偏移对比（RR = 基线/变体，>1 有利）")
    L.append("")
    L.append("| 对比 | 失败数（基/变） | RR [95% CI] |")
    L.append("|---|---:|---|")
    for k, x in rep["contrasts"].items():
        rr = x["rr"]
        lo_, hi_ = x["rr_ci95"]
        s = "n/a" if rr is None else f"{rr:.3f} [{lo_:.3f}, {hi_:.3f}]"
        L.append(f"| {k} | {x['failures_base']}/{x['failures_treat']} | {s} |")
    L.append("")
    L.append("## 3. 交互（风险差尺度）")
    L.append("")
    L.append("| 交互 | 点估计 | 95% CI |")
    L.append("|---|---:|---|")
    for k, x in rep["interactions"].items():
        L.append(f"| {k} | {x['point']:.6f} | [{x['ci95'][0]:.6f}, {x['ci95'][1]:.6f}] |")
    L.append("")
    L.append(f"判定：**{verdict}**。")
    L.append("")
    L.append("## 4. 解释边界")
    L.append("")
    L.append("- 这是诊断性重组，不是官方 BGF/BIKE 实现比较。")
    L.append("- 后处理会改变首轮灰集合；`postmask_p2` 单独检验掩码重组的作用。")
    L.append("- 组件对照（recheck-only / gray-only）为探索性，不作确证结论。")
    L.append("- 不含吞吐或生产参数声明。")
    L.append("")
    open(OUT / report_name, "w", encoding="utf-8").write("\n".join(L))
    print(f"[analyze] -> {OUT/summary_name}")
    print(f"[analyze] -> {OUT/report_name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["smoke", "run", "analyze"], required=True)
    ap.add_argument("--nkeys", type=int, default=46)
    ap.add_argument("--nerr", type=int, default=2000)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--point", choices=sorted(POINTS), default=DEFAULT_POINT)
    ap.add_argument("--group", default=DEFAULT_GROUP)
    ap.add_argument("--path", default=None)
    args = ap.parse_args()
    suffix = "" if args.point == DEFAULT_POINT else f"_{args.point}"
    if args.phase == "smoke":
        tag = args.tag or f"pilot{suffix}"
        p = phase_run(args.nkeys, args.nerr, tag, args.point, args.group)
        d = np.load(p)
        g1 = gate_classic(d, args.nkeys, args.nerr, args.point)
        g2 = gate_bgf(args.nkeys, args.nerr, args.point, args.group)
        print("gate_classic:", json.dumps(g1, indent=1))
        print("gate_bgf:", json.dumps(g2, indent=1))
    elif args.phase == "run":
        tag = args.tag or (f"full{suffix}" if args.nkeys == 46 and args.nerr == 2000
                           else f"custom{suffix}")
        p = phase_run(args.nkeys, args.nerr, tag, args.point, args.group)
        d = np.load(p)
        print("gate_classic:", json.dumps(
            gate_classic(d, args.nkeys, args.nerr, args.point), indent=1))
        print("gate_bgf:", json.dumps(
            gate_bgf(args.nkeys, args.nerr, args.point, args.group), indent=1))
    else:
        phase_analyze(args.path)


if __name__ == "__main__":
    main()
