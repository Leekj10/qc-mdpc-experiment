#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Decoder-transfer pilot for the first-round threshold window.

Question
--------
The paper measures a one-shot first-round threshold window on the CLASSIC BF
carrier: +2 lowers the conditional failure rate ~4x at P1', -2 raises it by two
orders of magnitude, and the effect reverses when sustained.  Does the same
one-shot intervention transfer to other threshold-based BF decoder families?

This is a SCOPE test, not an efficiency benchmark.  Every family is modified
only in its OWN round-one threshold; all later rounds keep their frozen
semantics.  Instances are paired: the same (H,e,s) is decoded by every arm.

Families
--------
CLASSIC   : parallel BF, frozen CLASSIC threshold, 20 rounds.  Arms {0,+2}.
            Gate: must reproduce the archived direction and the S1 per-instance
            failures on the first 2000 errors of keys 54..99.
BIKE-Flip : spec v5.2 schedule, (a,b) from the A.2.4 tangent rule at P1',
            delta=3, static-distance semantics.  Arms {-2,0,+2} at the
            spec-native 7-round budget (primary); optional 20-round arms.
            The baseline already carries delta=3, so +2 means a total
            first-round margin of +5 relative to ft(S0).
BGF       : GRAY_BGF (bgf_vasseur), CLASSIC base, gray_delta=3, 20 rounds.
            Arms {-2,0,+2} on the first main-step threshold only.
BF-Max    : flips one maximum-UPC position per iteration; it has NO threshold,
            so the intervention is undefined.  Reported as an out-of-scope
            boundary, not as a failed transfer.

Pre-registration: results/decoder_transfer/protocol_decoder_transfer.json,
frozen before any decode.

Run
---
  python lw-vs/scripts/exp_decoder_transfer.py --phase verify
  python lw-vs/scripts/exp_decoder_transfer.py --phase run --nkeys 3 --nerr 200   # smoke
  python lw-vs/scripts/exp_decoder_transfer.py --phase run                         # full
  python lw-vs/scripts/exp_decoder_transfer.py --phase analyze
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "实验" / "qcmdpc-study"
OUT = ROOT / "lw-vs" / "results" / "decoder_transfer"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(STUDY))

from qcmdpc.decoders import (TrajectoryResult, bgf_vasseur,  # noqa: E402
                             build_decoder, make_threshold)
from qcmdpc.bikeflip import derive_bikeflip_affine, bike_flip  # noqa: E402
from qcmdpc.generators import KeyPool, make_error_generator  # noqa: E402
from qcmdpc.stats import (cluster_bootstrap_paired, holm_adjust,  # noqa: E402
                          mcnemar_exact)

SEED = 20260901
P1 = {"id": "P1prime", "r": 4801, "d": 45, "t": 92, "n0": 2}
G0_SPEC = {"type": "random", "n_keys": 100}
TEST_KEYS = list(range(54, 100))
E_PER_KEY = 2000
MAX_ITER = 20
BIKE_DELTA = 3
BIKE_NB = 7
N_WORKERS = int(os.environ.get("DT_WORKERS", "10"))
SUF = {-2: "m2", 0: "0", 2: "p2"}

_POOL = None


def _get_pool():
    global _POOL
    if _POOL is None:
        _POOL = KeyPool(SEED, P1, "G0", G0_SPEC)
    return _POOL


# --------------------------------------------------------------- BIKE-Flip
def bike_flip_offset(key, s0, a, b, delta, nb_iter, first_round_offset=0,
                     record_flips=False):
    """Bit-identical copy of qcmdpc.bikeflip.bike_flip with a round-1-only
    additive offset.  offset=0 is verified against the frozen library before
    any transfer decode (phase verify)."""
    d = key.d
    lo, hi = (d + 1) // 2, d
    s0 = np.asarray(s0)
    S0 = int(s0.sum())

    def ft(S):
        return a * S + b

    fS0 = ft(S0)
    Ti = [None] * (nb_iter + 1)
    for i in range(1, nb_iter + 1):
        if i == 1:
            Ti[i] = fS0 + delta + first_round_offset
        elif i == 2:
            Ti[i] = (2 * fS0 + lo) / 3 + delta
        elif i == 3:
            Ti[i] = (fS0 + 2 * lo) / 3 + delta
        else:
            Ti[i] = lo + delta

    s = s0.copy()
    res = TrajectoryResult("BIKE-Flip", False, None, 0)
    success_at = None
    for i in range(1, nb_iter + 1):
        S = int(s.sum())
        if S == 0:
            if success_at is None:
                success_at = i - 1
            res.syndrome_weights.append(0)
            res.flip_counts.append(0)
            if record_flips:
                res.flip_positions.append([])
            res.n_iters_run = i
            continue
        T = int(np.clip(math.ceil(max(ft(S), Ti[i])), lo, hi))
        alpha = key.upc_fast(s)
        flips = np.nonzero(alpha >= T)[0]
        for p in flips:
            s = key.flip(s, int(p))
        res.syndrome_weights.append(int(s.sum()))
        res.flip_counts.append(int(flips.size))
        if record_flips:
            res.flip_positions.append([int(p) for p in flips])
        res.n_iters_run = i
        if int(s.sum()) == 0 and success_at is None:
            success_at = i
    res.success = int(s.sum()) == 0
    res.iters_to_success = success_at
    res.extra = {"S0": S0, "delta": delta, "nb_iter": nb_iter, "a": a, "b": b,
                 "first_round_offset": first_round_offset}
    return res


# ------------------------------------------------------------------ helpers
def _bgf_thr(base_thr, offset, lo, hi):
    def thr(it, sw):
        return int(np.clip(base_thr(it, sw) + (offset if it == 1 else 0), lo, hi))
    return thr


def _census(alpha, sup, tau):
    F = alpha >= tau
    nf = int(F.sum())
    nt = int(F[sup].sum())
    return nf, nt, nf - nt


# ------------------------------------------------------------------- verify
def phase_verify() -> None:
    """Local BIKE-Flip offset=0 must be bit-identical to the frozen library."""
    r, d, t = P1["r"], P1["d"], P1["t"]
    a, b, savg = derive_bikeflip_affine(r, d, t)
    print(f"[verify] A.2.4 derived at P1': a={a:.18f}  b={b:.18f}  Savg={savg}")
    pool = KeyPool(SEED, P1, "G0", G0_SPEC)
    mism = 0
    n = 0
    for ki in (54, 60, 70):
        key = pool.keys[ki]
        gen = make_error_generator(SEED, "G0", key.key_id, P1, G0_SPEC, key, None)
        for eid in range(300):
            e = gen(eid)
            s0 = key.syndrome_from_global(e)
            lib = bike_flip(key, s0.copy(), a, b, BIKE_DELTA, BIKE_NB)
            loc = bike_flip_offset(key, s0.copy(), a, b, BIKE_DELTA, BIKE_NB, 0)
            n += 1
            if (lib.success != loc.success or lib.n_iters_run != loc.n_iters_run
                    or lib.iters_to_success != loc.iters_to_success
                    or lib.flip_counts != loc.flip_counts):
                mism += 1
    print(f"[verify] local offset=0 vs library: {n - mism}/{n} exact, {mism} mismatches")
    if mism:
        raise SystemExit("BIKE-Flip local variant is not bit-identical")


# ---------------------------------------------------------------------- run
def _work(job):
    ki, n_err, do_bike20 = job
    pool = _get_pool()
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "G0", key.key_id, P1, G0_SPEC, key, None)
    r, d, t = P1["r"], P1["d"], P1["t"]
    lo, hi = max(1, (d + 1) // 2), d
    n = 2 * r
    a, b, _ = derive_bikeflip_affine(r, d, t)
    classic = make_threshold({"type": "classic"}, d, t, n)

    arms = ["classic_0", "classic_p2",
            "bike7_m2", "bike7_0", "bike7_p2",
            "bgf_m2", "bgf_0", "bgf_p2"]
    if do_bike20:
        arms += ["bike20_0", "bike20_p2"]

    dec_c0 = build_decoder("c0", {"algo": "bf_parallel",
                                  "threshold": {"type": "classic"},
                                  "max_iter": MAX_ITER}, d, t, r)
    dec_c2 = build_decoder("c2", {"algo": "bf_parallel",
                                  "threshold": {"type": "offset",
                                                "base": {"type": "classic"},
                                                "offsets": [2, 0]},
                                  "max_iter": MAX_ITER}, d, t, r)
    bgf_thr = {dl: _bgf_thr(classic, dl, lo, hi) for dl in (-2, 0, 2)}
    decs = {
        "classic_0": dec_c0,
        "classic_p2": dec_c2,
        "bike7_m2": lambda k, s: bike_flip_offset(k, s, a, b, BIKE_DELTA, BIKE_NB, -2),
        "bike7_0": lambda k, s: bike_flip_offset(k, s, a, b, BIKE_DELTA, BIKE_NB, 0),
        "bike7_p2": lambda k, s: bike_flip_offset(k, s, a, b, BIKE_DELTA, BIKE_NB, 2),
        "bgf_m2": lambda k, s: bgf_vasseur(k, s, bgf_thr[-2], MAX_ITER, 3),
        "bgf_0": lambda k, s: bgf_vasseur(k, s, bgf_thr[0], MAX_ITER, 3),
        "bgf_p2": lambda k, s: bgf_vasseur(k, s, bgf_thr[2], MAX_ITER, 3),
    }
    if do_bike20:
        decs["bike20_0"] = lambda k, s: bike_flip_offset(k, s, a, b, BIKE_DELTA, 20, 0)
        decs["bike20_p2"] = lambda k, s: bike_flip_offset(k, s, a, b, BIKE_DELTA, 20, 2)

    fail = {x: np.zeros(n_err, dtype=np.uint8) for x in arms}
    iters = {x: np.zeros(n_err, dtype=np.int16) for x in arms}
    conv = {x: np.full(n_err, -1, dtype=np.int16) for x in arms}
    first_flips = {x: np.zeros(n_err, dtype=np.int16) for x in arms}

    # round-1 census (diagnostic; uses the true support, matching the paper's
    # existing disclosure for the mechanism analysis)
    census = {}
    for tag in ("classic_0", "classic_p2", "bike_m2", "bike_0", "bike_p2"):
        census[f"{tag}_nf"] = np.zeros(n_err, dtype=np.int16)
        census[f"{tag}_nt"] = np.zeros(n_err, dtype=np.int16)

    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        S0 = int(s0.sum())
        alpha = key.upc_fast(s0)
        sup = e.astype(bool)

        tau_c = int(np.clip(classic(0, S0), lo, hi))
        tau_b = int(np.clip(math.ceil(max(a * S0 + b, a * S0 + b + BIKE_DELTA)), lo, hi))
        for off, tag in ((0, "classic_0"), (2, "classic_p2")):
            nf, nt, _ = _census(alpha, sup, int(np.clip(tau_c + off, lo, hi)))
            census[f"{tag}_nf"][eid] = nf
            census[f"{tag}_nt"][eid] = nt
        for off, tag in ((-2, "bike_m2"), (0, "bike_0"), (2, "bike_p2")):
            nf, nt, _ = _census(alpha, sup, int(np.clip(tau_b + off, lo, hi)))
            census[f"{tag}_nf"][eid] = nf
            census[f"{tag}_nt"][eid] = nt

        for x in arms:
            res = decs[x](key, s0.copy())
            fail[x][eid] = 0 if res.success else 1
            iters[x][eid] = res.n_iters_run
            conv[x][eid] = res.iters_to_success if res.iters_to_success is not None else -1
            first_flips[x][eid] = res.flip_counts[0] if res.flip_counts else 0

    return ki, fail, iters, conv, first_flips, census


def phase_run(nkeys: int, nerr: int, do_bike20: bool) -> None:
    keys = TEST_KEYS[:nkeys]
    t0 = time.time()
    print(f"[run] keys {keys[0]}..{keys[-1]} ({len(keys)}), {nerr} errors/key, "
          f"bike20={do_bike20}, workers={N_WORKERS}")
    jobs = [(ki, nerr, do_bike20) for ki in keys]
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, len(keys))) as ex:
        res = list(ex.map(_work, jobs))
    res.sort(key=lambda x: x[0])

    out = {"keys": np.array(keys, dtype=np.int32),
           "e_per_key": np.array([nerr], dtype=np.int32),
           "bike20": np.array([int(do_bike20)], dtype=np.int8)}
    for x in ("classic_0", "classic_p2", "bike7_m2", "bike7_0", "bike7_p2",
              "bgf_m2", "bgf_0", "bgf_p2"):
        out[f"fail_{x}"] = np.stack([r[1][x] for r in res])
        out[f"iters_{x}"] = np.stack([r[2][x] for r in res])
        out[f"conv_{x}"] = np.stack([r[3][x] for r in res])
        out[f"first_{x}"] = np.stack([r[4][x] for r in res])
    if do_bike20:
        for x in ("bike20_0", "bike20_p2"):
            out[f"fail_{x}"] = np.stack([r[1][x] for r in res])
            out[f"iters_{x}"] = np.stack([r[2][x] for r in res])
            out[f"conv_{x}"] = np.stack([r[3][x] for r in res])
            out[f"first_{x}"] = np.stack([r[4][x] for r in res])
    for k in res[0][5]:
        out[f"census_{k}"] = np.stack([r[5][k] for r in res])

    tag = "pilot" if nkeys < len(TEST_KEYS) or nerr < E_PER_KEY else "full"
    p = OUT / f"decoder_transfer_{tag}.npz"
    np.savez_compressed(p, **out)
    print(f"[run] saved {p}  ({time.time()-t0:.0f}s)")

    # quick console summary
    E = nerr
    for base, treat, label in (("classic_0", "classic_p2", "CLASSIC +2"),
                               ("bike7_0", "bike7_p2", "BIKE-Flip(7) +2"),
                               ("bike7_0", "bike7_m2", "BIKE-Flip(7) -2"),
                               ("bgf_0", "bgf_p2", "BGF +2"),
                               ("bgf_0", "bgf_m2", "BGF -2")):
        fb = out[f"fail_{base}"].sum(axis=1).astype(np.int64)
        ft = out[f"fail_{treat}"].sum(axis=1).astype(np.int64)
        boot = cluster_bootstrap_paired(fb, ft, E, B=10000, seed=20260905)
        rr = boot["point"]["risk_ratio"]
        lo, hi = boot["ci"]["risk_ratio"]
        rrs = "n/a" if rr is None else f"{rr:.3f}"
        cis = "n/a" if lo is None else f"[{lo:.3f}, {hi:.3f}]"
        print(f"  {label:20s} RR={rrs} {cis}  "
              f"fail {int(fb.sum())}/{int(ft.sum())}")


# ------------------------------------------------------------------ analyze
def _pair(d, base, treat, E):
    fb = d[f"fail_{base}"].astype(np.int64).sum(axis=1)
    ft = d[f"fail_{treat}"].astype(np.int64).sum(axis=1)
    boot = cluster_bootstrap_paired(fb, ft, E, B=10000, seed=20260905)
    b_only = int(((d[f"fail_{base}"] == 1) & (d[f"fail_{treat}"] == 0)).sum())
    t_only = int(((d[f"fail_{base}"] == 0) & (d[f"fail_{treat}"] == 1)).sum())
    out = {
        "base": base, "treat": treat,
        "failures_base": int(fb.sum()), "failures_treat": int(ft.sum()),
        "trials": int(len(fb) * E),
        "dfr_base": float(fb.sum()) / (len(fb) * E),
        "dfr_treat": float(ft.sum()) / (len(fb) * E),
        "rr_base_over_treat": boot["point"]["risk_ratio"],
        "rr_ci95": boot["ci"]["risk_ratio"],
        "mcnemar_base_only": b_only, "mcnemar_treat_only": t_only,
        "mcnemar_p": mcnemar_exact(b_only, t_only),
        "mean_iters_base": float(d[f"iters_{base}"].mean()),
        "mean_iters_treat": float(d[f"iters_{treat}"].mean()),
    }
    for tag, arm in (("base", base), ("treat", treat)):
        m = (d[f"fail_{arm}"] == 0) & (d[f"conv_{arm}"] >= 0)
        out[f"mean_conv_{tag}"] = float(d[f"conv_{arm}"][m].mean()) if m.any() else None
        out[f"mean_first_flip_{tag}"] = float(d[f"first_{arm}"].mean())
    return out


def _census_stats(d, tag):
    nf = d[f"census_{tag}_nf"].mean()
    nt = d[f"census_{tag}_nt"].mean()
    return {"mean_nflip": float(nf), "mean_ntrue": float(nt),
            "mean_nfalse": float(nf - nt)}


def phase_analyze() -> None:
    p_full = OUT / "decoder_transfer_full.npz"
    p_pilot = OUT / "decoder_transfer_pilot.npz"
    p = p_full if p_full.exists() else p_pilot
    if not p.exists():
        raise SystemExit("no decoder_transfer npz found; run --phase run first")
    d = np.load(p)
    E = int(d["e_per_key"][0])
    keys = d["keys"]
    rep = {"source": p.name, "keys": [int(keys[0]), int(keys[-1])],
           "n_keys": int(len(keys)), "errors_per_key": E,
           "trials_per_arm": int(len(keys) * E), "families": {}}

    # gate: compare CLASSIC failures to the archived S1 npz on the common prefix
    gate = {}
    s1p = ROOT / "lw-vs" / "results" / "tier_upgrade" / "surrogate_S1.npz"
    if s1p.exists():
        s1 = np.load(s1p)
        s1_keys = s1["keys"]
        idx = np.isin(s1_keys, keys)
        n_common = min(E, s1["fail_0"].shape[1])
        same0 = int((s1["fail_0"][idx][:, :n_common] == d["fail_classic_0"][:, :n_common]).sum())
        same2 = int((s1["fail_2"][idx][:, :n_common] == d["fail_classic_p2"][:, :n_common]).sum())
        total = int(idx.sum() * n_common)
        gate = {"s1_file": str(s1p), "common_trials": total,
                "classic_0_exact": f"{same0}/{total}",
                "classic_p2_exact": f"{same2}/{total}",
                "pass": same0 == total and same2 == total}
    rep["gate"] = gate

    pairs = [("CLASSIC", "classic_0", "classic_p2", "primary"),
             ("BIKE-Flip(7)", "bike7_0", "bike7_p2", "primary"),
             ("BIKE-Flip(7)", "bike7_0", "bike7_m2", "secondary_negative"),
             ("BGF", "bgf_0", "bgf_p2", "primary"),
             ("BGF", "bgf_0", "bgf_m2", "secondary_negative")]
    if "fail_bike20_0" in d:
        pairs += [("BIKE-Flip(20)", "bike20_0", "bike20_p2", "secondary_budget")]

    for fam, base, treat, role in pairs:
        rep["families"].setdefault(fam, {})
        rep["families"][fam][f"{treat}_vs_{base}"] = {
            "role": role, **_pair(d, base, treat, E)}

    # census + actual first-round flip count check
    rep["census"] = {
        "CLASSIC_0": _census_stats(d, "classic_0"),
        "CLASSIC_p2": _census_stats(d, "classic_p2"),
        "BIKE_m2": _census_stats(d, "bike_m2"),
        "BIKE_0": _census_stats(d, "bike_0"),
        "BIKE_p2": _census_stats(d, "bike_p2"),
    }
    rep["census_check"] = {}
    for fam, arm, tag in (("CLASSIC", "classic_0", "classic_0"),
                          ("CLASSIC", "classic_p2", "classic_p2"),
                          ("BIKE-Flip(7)", "bike7_m2", "bike_m2"),
                          ("BIKE-Flip(7)", "bike7_0", "bike_0"),
                          ("BIKE-Flip(7)", "bike7_p2", "bike_p2")):
        same = int((d[f"first_{arm}"] == d[f"census_{tag}_nf"]).sum())
        rep["census_check"][arm] = f"{same}/{int(d[f'first_{arm}'].size)}"

    # suppression ratios (the mechanism signature)
    def ratio(a, b):
        return float(a / b) if b else None
    c = rep["census"]
    rep["suppression"] = {
        "CLASSIC_false_ratio_p2_over_0": ratio(c["CLASSIC_p2"]["mean_nfalse"],
                                               c["CLASSIC_0"]["mean_nfalse"]),
        "CLASSIC_true_ratio_p2_over_0": ratio(c["CLASSIC_p2"]["mean_ntrue"],
                                              c["CLASSIC_0"]["mean_ntrue"]),
        "BIKE_false_ratio_p2_over_0": ratio(c["BIKE_p2"]["mean_nfalse"],
                                            c["BIKE_0"]["mean_nfalse"]),
        "BIKE_true_ratio_p2_over_0": ratio(c["BIKE_p2"]["mean_ntrue"],
                                           c["BIKE_0"]["mean_ntrue"]),
        "BIKE_false_ratio_m2_over_0": ratio(c["BIKE_m2"]["mean_nfalse"],
                                            c["BIKE_0"]["mean_nfalse"]),
        "BIKE_true_ratio_m2_over_0": ratio(c["BIKE_m2"]["mean_ntrue"],
                                           c["BIKE_0"]["mean_ntrue"]),
    }

    # Holm across the two primary +2 tests
    pv = [rep["families"]["BIKE-Flip(7)"]["bike7_p2_vs_bike7_0"]["mcnemar_p"],
          rep["families"]["BGF"]["bgf_p2_vs_bgf_0"]["mcnemar_p"]]
    adj = holm_adjust(pv)
    rep["holm_primary_plus2"] = {
        "BIKE-Flip(7)": adj[0], "BGF": adj[1],
        "note": "exact McNemar is instance-level and nominal; Holm is reported "
                "for completeness, the key-clustered CI remains primary"}

    # verdict
    def supported(fam, treat):
        x = rep["families"][fam][f"{treat}_vs_{'bike7_0' if fam == 'BIKE-Flip(7)' else 'bgf_0'}"]
        lo, hi = x["rr_ci95"]
        rr = x["rr_base_over_treat"]
        return rr is not None and rr > 1 and lo is not None and lo > 1
    v = {"BIKE-Flip(7)_plus2_supported": supported("BIKE-Flip(7)", "bike7_p2"),
         "BGF_plus2_supported": supported("BGF", "bgf_p2")}
    v["n_supported"] = int(v["BIKE-Flip(7)_plus2_supported"]) + int(v["BGF_plus2_supported"])
    v["verdict"] = ("TRANSFER_SUPPORTED" if v["n_supported"] == 2 else
                    "PARTIAL_TRANSFER" if v["n_supported"] == 1 else
                    "TRANSFER_NOT_SUPPORTED")
    rep["verdict"] = v

    json.dump(rep, open(OUT / "decoder_transfer_summary.json", "w", encoding="utf-8"),
              indent=1)
    print(json.dumps(rep, indent=1))

    # ---- Chinese markdown report ----
    lines = ["# 首轮阈值规律的译码器迁移检验（预注册结果）", ""]
    lines.append(f"- 数据：`{p.name}`，{len(keys)} 个密钥 × {E} 个误差 = {len(keys)*E:,} 配对实例/臂。")
    lines.append("- 工作点：P1′ = (4801, 45, 92)；密钥 54–99（S1 留出集）。")
    lines.append("- 每个族只改自己首轮的阈值，后续轮次不变；同一 `(H,e,s)` 配对。")
    lines.append("")
    lines.append("## 0. 闸门")
    if gate:
        lines.append(f"- CLASSIC 与 S1 存档逐实例一致：C0 {gate['classic_0_exact']}，"
                     f"FRO-2 {gate['classic_p2_exact']} → "
                     f"**{'PASS' if gate['pass'] else 'FAIL'}**。")
    else:
        lines.append("- 未找到 S1 存档，未做逐实例闸门。")
    lines.append("")
    lines.append("## 1. 主结果")
    lines.append("")
    lines.append("| 族 | 对比 | DFR 基线 | DFR 变体 | RR (基线/变体) [95% CI] | 失败数 (基/变) |")
    lines.append("|---|---|---:|---:|---|---:|")
    for fam, base, treat, role in pairs:
        x = rep["families"][fam][f"{treat}_vs_{base}"]
        lo, hi = x["rr_ci95"]
        rr = x["rr_base_over_treat"]
        cis = (f"{rr:.3f} [{lo:.3f}, {hi:.3f}]"
               if (rr is not None and lo is not None) else "n/a (zero-event arm)")
        lines.append(f"| {fam} | {treat} vs {base} | {x['dfr_base']:.3e} | "
                     f"{x['dfr_treat']:.3e} | {cis} | {x['failures_base']}/{x['failures_treat']} |")
    lines.append("")
    lines.append("## 2. 首轮翻转集（机制签名）")
    lines.append("")
    lines.append("| 臂 | 平均翻转数 | 其中真误差 | 其中假翻转 |")
    lines.append("|---|---:|---:|---:|")
    for k, v2 in rep["census"].items():
        lines.append(f"| {k} | {v2['mean_nflip']:.2f} | {v2['mean_ntrue']:.2f} | "
                     f"{v2['mean_nfalse']:.2f} |")
    lines.append("")
    sp = rep["suppression"]
    lines.append(f"- CLASSIC +2：假翻转 ×{sp['CLASSIC_false_ratio_p2_over_0']:.3f}，"
                 f"真翻转 ×{sp['CLASSIC_true_ratio_p2_over_0']:.3f}（非对称抑制）。")
    lines.append(f"- BIKE-Flip +2：假翻转 ×{sp['BIKE_false_ratio_p2_over_0']:.3f}，"
                 f"真翻转 ×{sp['BIKE_true_ratio_p2_over_0']:.3f}。")
    lines.append(f"- BIKE-Flip −2：假翻转 ×{sp['BIKE_false_ratio_m2_over_0']:.3f}，"
                 f"真翻转 ×{sp['BIKE_true_ratio_m2_over_0']:.3f}。")
    lines.append("")
    lines.append("## 3. 判定")
    lines.append("")
    lines.append(f"- 结论：**{v['verdict']}**（两个主检验中支持 {v['n_supported']}/2）。")
    lines.append("- 判定规则（预注册）：+2 的 RR>1 且密钥 cluster 95% CI 排除 1 才算支持；"
                 "RR<1 且 CI 排除 1 是“过冲/边界”结果，不是实验失败。")
    lines.append("")
    lines.append("## 4. 解释与限制")
    lines.append("")
    lines.append("- 这是 Python 参考载体的结果，不构成吞吐或生产实现声明；成本看平均迭代/首轮翻转数。")
    lines.append("- BIKE-Flip 基线自带 Δ=3；+2 对应首轮总余量 +5，−2 对应 +1。"
                 "若两侧都变差，说明规范常数落在窗口内部（内点最优）；若 +2 仍变好，说明规范在该点偏保守不足。")
    lines.append("- BGF 的 gray step 会在首轮主步之后重新接纳阈值下方的位置，"
                 "因此 +2 的净效应可能被部分抵消。")
    lines.append("- BF-Max 没有阈值，偏移无定义，属于规律的适用边界，不是阴性结果。")
    lines.append("- McNemar 是实例级、名义的；主推断是密钥 cluster bootstrap。")
    lines.append("")
    open(OUT / "REPORT_zh.md", "w", encoding="utf-8").write("\n".join(lines))
    print(f"[analyze] -> {OUT/'decoder_transfer_summary.json'}")
    print(f"[analyze] -> {OUT/'REPORT_zh.md'}")


# --------------------------------------------------- BIKE-Flip 20-round check
def _work_bike20(job):
    """Only the 20-round BIKE-Flip arms, on the same keys/errors as the main run."""
    ki, n_err = job
    pool = _get_pool()
    key = pool.keys[ki]
    gen = make_error_generator(SEED, "G0", key.key_id, P1, G0_SPEC, key, None)
    r, d, t = P1["r"], P1["d"], P1["t"]
    a, b, _ = derive_bikeflip_affine(r, d, t)
    arms = ["bike20_0", "bike20_p2"]
    decs = {
        "bike20_0": lambda k, s: bike_flip_offset(k, s, a, b, BIKE_DELTA, 20, 0),
        "bike20_p2": lambda k, s: bike_flip_offset(k, s, a, b, BIKE_DELTA, 20, 2),
    }
    fail = {x: np.zeros(n_err, np.uint8) for x in arms}
    iters = {x: np.zeros(n_err, np.int16) for x in arms}
    conv = {x: np.full(n_err, -1, np.int16) for x in arms}
    first = {x: np.zeros(n_err, np.int16) for x in arms}
    for eid in range(n_err):
        e = gen(eid)
        s0 = key.syndrome_from_global(e)
        for x in arms:
            res = decs[x](key, s0.copy())
            fail[x][eid] = 0 if res.success else 1
            iters[x][eid] = res.n_iters_run
            conv[x][eid] = res.iters_to_success if res.iters_to_success is not None else -1
            first[x][eid] = res.flip_counts[0] if res.flip_counts else 0
    return ki, fail, iters, conv, first


def phase_run20(nkeys: int, nerr: int) -> None:
    keys = TEST_KEYS[:nkeys]
    t0 = time.time()
    print(f"[bike20] keys {keys[0]}..{keys[-1]} ({len(keys)}), {nerr} errors/key")
    jobs = [(ki, nerr) for ki in keys]
    with ProcessPoolExecutor(max_workers=min(N_WORKERS, len(keys))) as ex:
        res = list(ex.map(_work_bike20, jobs))
    res.sort(key=lambda x: x[0])
    out = {"keys": np.array(keys, dtype=np.int32),
           "e_per_key": np.array([nerr], dtype=np.int32)}
    for x in ("bike20_0", "bike20_p2"):
        out[f"fail_{x}"] = np.stack([r[1][x] for r in res])
        out[f"iters_{x}"] = np.stack([r[2][x] for r in res])
        out[f"conv_{x}"] = np.stack([r[3][x] for r in res])
        out[f"first_{x}"] = np.stack([r[4][x] for r in res])
    p = OUT / "decoder_transfer_bike20.npz"
    np.savez_compressed(p, **out)
    print(f"[bike20] saved {p}  ({time.time()-t0:.0f}s)")


def phase_analyze20() -> None:
    p = OUT / "decoder_transfer_bike20.npz"
    if not p.exists():
        raise SystemExit("no decoder_transfer_bike20.npz; run --phase bike20 first")
    d = np.load(p)
    E = int(d["e_per_key"][0])
    x = _pair(d, "bike20_0", "bike20_p2", E)
    rep = {"source": p.name, "n_keys": int(len(d["keys"])),
           "errors_per_key": E, "pair": x}
    json.dump(rep, open(OUT / "bike20_summary.json", "w", encoding="utf-8"), indent=1)
    rr = x["rr_base_over_treat"]
    lo, hi = x["rr_ci95"]
    cis = (f"{rr:.3f} [{lo:.3f}, {hi:.3f}]"
           if (rr is not None and lo is not None) else "n/a (zero-event arm)")
    lines = ["", "## 5. BIKE-Flip 20 轮敏感性（论文比较预算）", "",
             f"- DFR：基线 {x['dfr_base']:.3e} → +2 {x['dfr_treat']:.3e}；"
             f"RR {cis}；失败 {x['failures_base']}/{x['failures_treat']}。",
             f"- 平均收敛轮次：{x['mean_conv_base']:.3f} → {x['mean_conv_treat']:.3f}；"
             f"首轮翻转：{x['mean_first_flip_base']:.2f} → {x['mean_first_flip_treat']:.2f}。",
             "- 解释：若 20 轮下 +2 仍显著变差，过冲不是“回收轮次不足”；"
             "若转为中性/有益，则 7 轮结论受预算调节，必须按预算分层表述。"]
    with open(OUT / "REPORT_zh.md", "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(rep, indent=1))
    print(f"[bike20] -> {OUT/'bike20_summary.json'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="verify,run,analyze")
    ap.add_argument("--nkeys", type=int, default=len(TEST_KEYS))
    ap.add_argument("--nerr", type=int, default=E_PER_KEY)
    ap.add_argument("--bike20", action="store_true")
    a = ap.parse_args()
    ph = [x.strip().lower() for x in a.phase.split(",") if x.strip()]
    t0 = time.time()
    if "verify" in ph:
        phase_verify()
    if "run" in ph:
        phase_run(a.nkeys, a.nerr, a.bike20)
    if "analyze" in ph:
        phase_analyze()
    if "bike20" in ph:
        phase_run20(a.nkeys, a.nerr)
    if "analyze20" in ph:
        phase_analyze20()
    print(f"[done] {OUT}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
