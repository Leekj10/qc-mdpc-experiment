#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Round-1 census for the post-step factor experiment.

Records, for the same 46 keys x 2000 errors used in exp_poststep_factor.py:
  - black sets at offset 0 and +2;
  - gray sets at offset 0 and +2;
  - true/false composition of each set;
  - overlap between the +2 gray band and the baseline black set;
  - how many gray positions the gray step actually re-admits;
  - residual error weight after the round-one policy.

This is a descriptive mechanism census, not a confirmatory test.  The true
error support is used only offline; it is not a deployable statistic.
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

from qcmdpc.decoders import make_threshold  # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402

SEED = 20260901
POINTS = {
    "P1": {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2},
    "P2": {"id": "P2", "r": 3001, "d": 37, "t": 66, "n0": 2},
}
DEFAULT_POINT = "P1"
DEFAULT_GROUP = "G0"
GROUP_SPEC = {"type": "random", "n_keys": 100}
TEST_KEYS = list(range(54, 100))
GRAY_DELTA = 3
N_WORKERS = int(os.environ.get("PC_WORKERS", "8"))

_POOLS = {}


def _get_pool(point_id, group_id):
    key = (point_id, group_id)
    if key not in _POOLS:
        _POOLS[key] = KeyPool(SEED, POINTS[point_id], group_id, GROUP_SPEC)
    return _POOLS[key]


def _apply(s, key, positions):
    for p in positions:
        s = key.flip(s, int(p))
    return s


def census_instance(key, e, s0, base_thr):
    d = key.d
    lo, hi = max(1, (d + 1) // 2), d
    bound = (d + 1) // 2 + 1
    alpha = key.upc_fast(s0)
    S0 = int(s0.sum())
    tau0 = int(np.clip(base_thr(0, S0), lo, hi))
    tau2 = int(np.clip(tau0 + 2, lo, hi))
    sup = np.asarray(e, dtype=bool)

    black0 = alpha >= tau0
    black2 = alpha >= tau2
    gray0 = (alpha < tau0) & (alpha + GRAY_DELTA >= tau0)
    gray2 = (alpha < tau2) & (alpha + GRAY_DELTA >= tau2)
    overlap = gray2 & black0

    def tf(mask):
        m = np.asarray(mask, dtype=bool)
        return int(m.sum()), int((m & sup).sum())

    # plain offset 0: black0 only
    s = _apply(s0.copy(), key, np.nonzero(black0)[0])
    plain0_eff = black0.copy()
    plain0_res = int(e.sum()) - tf(plain0_eff)[1] + (tf(plain0_eff)[0] - tf(plain0_eff)[1])
    # plain +2: black2 only
    s = _apply(s0.copy(), key, np.nonzero(black2)[0])
    plain2_eff = black2.copy()
    n2, t2 = tf(plain2_eff)
    plain2_res = int(e.sum()) - t2 + (n2 - t2)

    # post offset 0: black0 -> recheck -> gray0
    s = _apply(s0.copy(), key, np.nonzero(black0)[0])
    alpha1 = key.upc_fast(s)
    reflip0 = black0 & (alpha1 >= bound)
    s = _apply(s, key, np.nonzero(reflip0)[0])
    alpha2 = key.upc_fast(s)
    gflip0 = gray0 & (alpha2 >= bound)
    s = _apply(s, key, np.nonzero(gflip0)[0])
    post0_eff = black0 ^ reflip0 ^ gflip0
    n0, t0 = tf(post0_eff)
    post0_res = int(e.sum()) - t0 + (n0 - t0)

    # post +2: black2 -> recheck -> gray2
    s = _apply(s0.copy(), key, np.nonzero(black2)[0])
    alpha1 = key.upc_fast(s)
    reflip2 = black2 & (alpha1 >= bound)
    s = _apply(s, key, np.nonzero(reflip2)[0])
    alpha2 = key.upc_fast(s)
    gflip2 = gray2 & (alpha2 >= bound)
    s = _apply(s, key, np.nonzero(gflip2)[0])
    post2_eff = black2 ^ reflip2 ^ gflip2
    n2p, t2p = tf(post2_eff)
    post2_res = int(e.sum()) - t2p + (n2p - t2p)

    def pack(mask):
        n, t = tf(mask)
        return n, t, n - t

    return {
        "tau0": tau0,
        "tau2": tau2,
        "S0": S0,
        "black0_n": pack(black0)[0], "black0_true": pack(black0)[1], "black0_false": pack(black0)[2],
        "black2_n": pack(black2)[0], "black2_true": pack(black2)[1], "black2_false": pack(black2)[2],
        "gray0_n": pack(gray0)[0], "gray0_true": pack(gray0)[1], "gray0_false": pack(gray0)[2],
        "gray2_n": pack(gray2)[0], "gray2_true": pack(gray2)[1], "gray2_false": pack(gray2)[2],
        "overlap_n": pack(overlap)[0], "overlap_true": pack(overlap)[1], "overlap_false": pack(overlap)[2],
        "reflip0_n": pack(reflip0)[0], "reflip0_true": pack(reflip0)[1],
        "reflip2_n": pack(reflip2)[0], "reflip2_true": pack(reflip2)[1],
        "gflip0_n": pack(gflip0)[0], "gflip0_true": pack(gflip0)[1], "gflip0_false": pack(gflip0)[2],
        "gflip2_n": pack(gflip2)[0], "gflip2_true": pack(gflip2)[1], "gflip2_false": pack(gflip2)[2],
        "plain0_res": plain0_res, "plain2_res": plain2_res,
        "post0_res": post0_res, "post2_res": post2_res,
        "plain0_n": pack(plain0_eff)[0], "plain0_true": pack(plain0_eff)[1], "plain0_false": pack(plain0_eff)[2],
        "plain2_n": pack(plain2_eff)[0], "plain2_true": pack(plain2_eff)[1], "plain2_false": pack(plain2_eff)[2],
        "post0_n": pack(post0_eff)[0], "post0_true": pack(post0_eff)[1], "post0_false": pack(post0_eff)[2],
        "post2_n": pack(post2_eff)[0], "post2_true": pack(post2_eff)[1], "post2_false": pack(post2_eff)[2],
    }


KEYS = [
    "tau0", "tau2", "S0",
    "black0_n", "black0_true", "black0_false",
    "black2_n", "black2_true", "black2_false",
    "gray0_n", "gray0_true", "gray0_false",
    "gray2_n", "gray2_true", "gray2_false",
    "overlap_n", "overlap_true", "overlap_false",
    "reflip0_n", "reflip0_true", "reflip2_n", "reflip2_true",
    "gflip0_n", "gflip0_true", "gflip0_false",
    "gflip2_n", "gflip2_true", "gflip2_false",
    "plain0_res", "plain2_res", "post0_res", "post2_res",
    "plain0_n", "plain0_true", "plain0_false",
    "plain2_n", "plain2_true", "plain2_false",
    "post0_n", "post0_true", "post0_false",
    "post2_n", "post2_true", "post2_false",
]


def _work(job):
    ki, n_err, point_id, group_id = job
    param = POINTS[point_id]
    pool = _get_pool(point_id, group_id)
    key = pool.keys[ki]
    gen = make_error_generator(SEED, group_id, key.key_id, param, GROUP_SPEC, key, None)
    base = make_threshold({"type": "classic"}, param["d"], param["t"], 2 * param["r"])
    rows = {k: np.zeros(n_err, dtype=np.int32) for k in KEYS}
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        r = census_instance(key, e, s0, base)
        for k in KEYS:
            rows[k][eid] = r[k]
    return ki, rows


def phase_run(nkeys, nerr, tag, point_id=DEFAULT_POINT, group_id=DEFAULT_GROUP):
    keys = TEST_KEYS[:nkeys]
    t0 = time.time()
    print(f"[census] point {point_id} group {group_id}, keys {keys[0]}..{keys[-1]} "
          f"({len(keys)}), {nerr} errors/key, workers={N_WORKERS}", flush=True)
    jobs = [(ki, nerr, point_id, group_id) for ki in keys]
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, len(keys))) as ex:
        res = list(ex.map(_work, jobs))
    res.sort(key=lambda x: x[0])
    out = {"keys": np.array(keys, dtype=np.int32),
           "e_per_key": np.array([nerr], dtype=np.int32),
           "point_id": np.array([point_id]),
           "group_id": np.array([group_id])}
    for k in KEYS:
        out[k] = np.stack([r[1][k] for r in res])
    p = OUT / f"poststep_census_{tag}.npz"
    np.savez_compressed(p, **out)
    print(f"[census] saved {p} ({time.time() - t0:.0f}s)", flush=True)
    return p


def phase_analyze(path=None):
    if path is None:
        full = OUT / "poststep_census_full.npz"
        pilot = OUT / "poststep_census_pilot.npz"
        p = full if full.exists() else pilot
    else:
        p = Path(path)
    if not p.exists():
        raise SystemExit("no census npz found; run --phase run first")
    d = np.load(p)
    E = int(d["e_per_key"][0])
    nk = int(len(d["keys"]))
    point_id = str(d["point_id"][0]) if "point_id" in d else DEFAULT_POINT
    group_id = str(d["group_id"][0]) if "group_id" in d else DEFAULT_GROUP
    param = POINTS.get(point_id, POINTS[DEFAULT_POINT])
    mean = {k: float(d[k].mean()) for k in KEYS}
    rep = {"source": p.name, "point": point_id, "group": group_id,
           "params": param, "n_keys": nk, "errors_per_key": E,
           "trials": nk * E, "means": mean}
    # ratios that structure the mechanism paragraph
    rep["derived"] = {
        "black0_true_frac": mean["black0_true"] / mean["black0_n"] if mean["black0_n"] else None,
        "black0_false_frac": mean["black0_false"] / mean["black0_n"] if mean["black0_n"] else None,
        "black2_true_frac": mean["black2_true"] / mean["black2_n"] if mean["black2_n"] else None,
        "black2_false_frac": mean["black2_false"] / mean["black2_n"] if mean["black2_n"] else None,
        "gray2_share_from_baseline_black": mean["overlap_n"] / mean["gray2_n"] if mean["gray2_n"] else None,
        "gray2_readmit_rate": mean["gflip2_n"] / mean["gray2_n"] if mean["gray2_n"] else None,
        "gray2_readmit_false_rate": mean["gflip2_false"] / mean["gflip2_n"] if mean["gflip2_n"] else None,
        "gray0_readmit_rate": mean["gflip0_n"] / mean["gray0_n"] if mean["gray0_n"] else None,
        "gray0_readmit_false_rate": mean["gflip0_false"] / mean["gflip0_n"] if mean["gflip0_n"] else None,
        "post2_minus_black0_n": mean["post2_n"] - mean["black0_n"],
        "post2_false_minus_black0_false": mean["post2_false"] - mean["black0_false"],
    }
    summary_name = ("poststep_census_summary.json" if point_id == "P1"
                    else f"poststep_census_summary_{point_id}.json")
    report_name = ("CENSUS_zh.md" if point_id == "P1"
                   else f"CENSUS_zh_{point_id}.md")
    json.dump(rep, open(OUT / summary_name, "w", encoding="utf-8"), indent=1)
    print(json.dumps(rep["means"], indent=1))
    print(json.dumps(rep["derived"], indent=1))

    L = ["# 首轮后处理组成普查（描述性）", "",
         f"- 数据：`{p.name}`，{nk} 密钥 × {E} 误差。",
         f"- 工作点 {point_id} = (r={param['r']}, d={param['d']}, t={param['t']})；"
         "真误差支持仅用于离线诊断。", "",
         "## 1. 首轮集合均值", "",
         "| 集合 | 大小 | 真误差 | 误翻 |", "|---|---:|---:|---:|"]
    for name in ("black0", "black2", "gray0", "gray2", "overlap"):
        L.append(f"| {name} | {mean[name+'_n']:.2f} | {mean[name+'_true']:.2f} | {mean[name+'_false']:.2f} |")
    L += ["", "## 2. 重入与有效集合", "",
          "| 量 | 均值 |", "|---|---:|",
          f"| gray0 重入 | {mean['gflip0_n']:.2f} |",
          f"| gray0 重入中的误翻 | {mean['gflip0_false']:.2f} |",
          f"| gray2 重入 | {mean['gflip2_n']:.2f} |",
          f"| gray2 重入中的误翻 | {mean['gflip2_false']:.2f} |",
          f"| post2 有效集合 | {mean['post2_n']:.2f} |",
          f"| post2 有效集合中的误翻 | {mean['post2_false']:.2f} |",
          f"| black0 集合 | {mean['black0_n']:.2f} |",
          f"| black0 集合中的误翻 | {mean['black0_false']:.2f} |",
          "", "## 3. 首轮残余差错", "",
          "| 策略 | 残余 |", "|---|---:|",
          f"| plain0 | {mean['plain0_res']:.2f} |",
          f"| plain2 | {mean['plain2_res']:.2f} |",
          f"| post0 | {mean['post0_res']:.2f} |",
          f"| post2 | {mean['post2_res']:.2f} |",
          "", "## 4. 解释边界", "",
          "- 描述性普查，不是确证检验。",
          "- 真/假翻转使用仿真中的真实误差支持，仅用于离线机制分析。",
          "- gray2 与 baseline black 的重叠说明 +2 的灰带会包含基线黑步本会翻转的位置。",
          "- 重入率只说明灰度步骤的即时行为，不直接预测最终 DFR。"]
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
        phase_run(args.nkeys, args.nerr, args.tag or f"pilot{suffix}",
                  args.point, args.group)
    elif args.phase == "run":
        tag = args.tag or (f"full{suffix}" if args.nkeys == 46 and args.nerr == 2000
                           else f"custom{suffix}")
        phase_run(args.nkeys, args.nerr, tag, args.point, args.group)
    else:
        phase_analyze(args.path)


if __name__ == "__main__":
    main()
