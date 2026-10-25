#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Assemble every archived and new (config, C0 DFR, RR) cell into one table and
derive the tier-upgrade quantities the report quotes. Read-only over results/;
writes only into results/tier_upgrade/.

Run:  python lw-vs/scripts/analyze_tier_upgrade.py
"""
from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / "lw-vs" / "results"
TU = R / "tier_upgrade"


def _load(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def cells_from_round_controls():
    out = []
    d = _load(R / "round_controls" / "phase1_round_controls.json")
    if d:
        for gid, cell in d["groups"].items():
            for arm, a in cell["arms"].items():
                if arm == "C0":
                    continue
                out.append(dict(axis="round", point="P1'",
                                pool={"RAND": "G0 main 92 keys",
                                      "TYPE-I": "G2_d12 pool",
                                      "NCW-shallow": "G3 pool"}[cell["condition"]],
                                condition=cell["condition"], arm=arm, t=92, budget=20,
                                c0_dfr=a.get("dfr", cell["arms"]["C0"]["dfr"]) if False else cell["arms"]["C0"]["dfr"],
                                rr=a.get("rr_vs_C0"), rr_lo=(a.get("rr_ci95") or [None, None])[0],
                                rr_hi=(a.get("rr_ci95") or [None, None])[1],
                                src="round_controls/phase1"))
    d = _load(R / "round_controls" / "phase2_t_sensitivity.json")
    if d:
        for t, c in d["cells"].items():
            if c.get("rr") is None:
                continue
            out.append(dict(axis="t", point="P1'", pool="tsweep pool 30 keys (per t)",
                            condition="RAND", arm="FRO-2", t=int(t), budget=20,
                            c0_dfr=c["c0_dfr"], rr=c["rr"],
                            rr_lo=c["rr_ci95"][0], rr_hi=c["rr_ci95"][1],
                            src="round_controls/phase2"))
    d = _load(R / "round_controls" / "phase4_larger_r.json")
    if d:
        for t, c in d.get("cells", {}).items():
            if c.get("rr") is None:
                continue
            out.append(dict(axis="t", point="(6007,56)", pool="big-r pool 40 keys",
                            condition="RAND", arm="FRO-2", t=int(t), budget=20,
                            c0_dfr=c["c0_dfr"], rr=c["rr"],
                            rr_lo=c["rr_ci95"][0], rr_hi=c["rr_ci95"][1],
                            src="round_controls/phase4"))
    return out


def cells_from_new():
    out = []
    st = _load(TU / "state_T90.json")
    if st and st["errors_done"]:
        import sys
        sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))
        from qcmdpc.stats import cluster_bootstrap_paired
        per0 = np.array(st["arms"]["C0"]); per2 = np.array(st["arms"]["FRO-2"])
        n = len(per0) * st["errors_done"]
        rr = lo = hi = None
        if per0.sum() > 0 and per2.sum() > 0:
            boot = cluster_bootstrap_paired(per0, per2, st["errors_done"], B=10000,
                                            seed=20260905)
            rr = boot["point"]["risk_ratio"]
            lo, hi = boot["ci"]["risk_ratio"]
        out.append(dict(axis="t", point="P1'", pool="G0 main 92 keys",
                        condition="RAND", arm="FRO-2", t=90, budget=20,
                        c0_dfr=float(per0.sum() / n), rr=rr, rr_lo=lo, rr_hi=hi,
                        src=f"tier_upgrade/T90 (errors/key={st['errors_done']})",
                        c0_failures=int(per0.sum()), fro2_failures=int(per2.sum()),
                        trials=n))
    for p in sorted(glob.glob(str(TU / "budget_B*.json"))):
        c = _load(p)
        out.append(dict(axis="budget", point="P1'", pool="G0 main 92 keys",
                        condition="RAND", arm="FRO-2", t=92, budget=c["budget"],
                        c0_dfr=c["c0_dfr"], rr=c["rr"], rr_lo=c["rr_ci95"][0],
                        rr_hi=c["rr_ci95"][1], src=Path(p).stem,
                        c0_failures=c["c0_failures"], fro2_failures=c["fro2_failures"],
                        trials=c["trials"]))
    # S1: the five-arm same-pool measurement at P1' t=92.  FRO-2 reproduces the
    # archived headline; +1 and +3 at this point are NEW measurements (the
    # archive had FRO-2 only), as is FRONEG (reproduces the archive's 0.126).
    s1 = _load(TU / "surrogate_S1.json")
    if s1:
        import sys
        sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))
        from qcmdpc.stats import cluster_bootstrap_paired
        c0f = s1["arms"]["C0"]["failures"]
        n = s1["arms"]["C0"]["trials"]
        e = s1["arms"]["C0"]["per_key"] and s1["errors_per_key"]
        per0 = np.array(s1["arms"]["C0"]["per_key"], dtype=np.int64)
        for nm in ("FROp1", "FRO-2", "FROp3", "FRONEG"):
            a = s1["arms"][nm]
            rr = lo = hi = None
            if a["failures"]:
                boot = cluster_bootstrap_paired(per0, np.array(a["per_key"], dtype=np.int64),
                                                e, B=10000, seed=20260905)
                rr = boot["point"]["risk_ratio"]
                lo, hi = boot["ci"]["risk_ratio"]
            out.append(dict(axis="round", point="P1'", pool="G0 main 92 keys",
                            condition="RAND", arm=nm, t=92, budget=20,
                            c0_dfr=c0f / n, rr=rr, rr_lo=lo, rr_hi=hi,
                            src="tier_upgrade/S1 (5-arm, same pool)",
                            c0_failures=c0f, fro2_failures=a["failures"], trials=n))
    d = _load(TU / "p1pp_main.json")
    if d:
        for nm, a in d["arms"].items():
            if nm == "C0":
                continue
            out.append(dict(axis="code", point=f"(12323,71,{d['t']})", pool="archived L1 pool",
                            condition="RAND", arm=nm, t=d["t"], budget=20,
                            c0_dfr=d["arms"]["C0"]["dfr"], rr=a.get("rr"),
                            rr_lo=(a.get("rr_ci95") or [None, None])[0],
                            rr_hi=(a.get("rr_ci95") or [None, None])[1],
                            src="tier_upgrade/p1pp_main",
                            c0_failures=d["arms"]["C0"]["failures"],
                            fro2_failures=a["failures"], trials=d["trials"]))
    return out


def rho_table():
    """P1' (t=92) vs L1 (t=134) exchange ratios, the mechanism quantity."""
    rows = []
    b = _load(R / "lowdfr_model" / "phaseB_upc_tails.json") or {}
    m = (b.get("92") or {}).get("model", {})
    for dl in ("1", "2", "3"):
        if dl in m:
            rows.append(dict(point="P1' (4801,45,92)", delta=int(dl),
                             deferred_true=m[dl]["correct_deferred"],
                             avoided_false=m[dl]["incorrect_avoided"],
                             rho=m[dl]["rho"]))
    l1 = _load(TU / "l1a_firstround_margin.json")
    if l1:
        for dl, v in l1["model_rho"].items():
            rows.append(dict(point=f"L1 ({l1['r']},{l1['d']},{l1['t']})", delta=int(dl),
                             deferred_true=v["deferred_true_per_instance"],
                             avoided_false=v["avoided_false_per_instance"],
                             rho=v["rho"] if np.isfinite(v["rho"]) else None))
    return rows


def rho_vs_rr():
    """Pair the exchange ratio rho(delta) with the MEASURED risk ratio of that
    delta at every work point where both exist.  This is the weakest form of the
    model: does rho order the effect across offsets and across operating points?"""
    rho = _load(TU / "rho_workpoints.json", {}).get("points", {})
    # measured FRO-1/2/3 risk ratios from the tier-2 expanded confirmation
    rr_meas = {}
    try:
        rows = list(csv.DictReader(open(ROOT / "lw-vs" / "data" / "t2_expanded_temporal.csv",
                                        encoding="utf-8-sig")))
        c0 = {}
        for r in rows:
            if r["condition"] != "RAND":
                continue
            key = r["point"]
            if r["decoder"] == "C0":
                c0[key] = float(r["dfr"])
            elif r["decoder"] in ("FRO-1", "FRO-2", "FRO-3"):
                d = int(r["decoder"].split("-")[1])
                rr_meas.setdefault(key, {})[d] = c0.get(key, float("nan")) / float(r["dfr"])
    except Exception as e:
        print("  (t2_expanded_temporal.csv not readable:", e, ")")
    # P1': same-pool RRs for all three positive offsets come from S1 (the 5-arm run);
    # note the rho for this row is computed on a DIFFERENT 12-key pool, a mismatch
    # that is disclosed in the report rather than papered over.
    s1 = _load(TU / "surrogate_S1.json")
    if s1:
        c0f = s1["arms"]["C0"]["failures"]
        for d, arm in ((1, "FROp1"), (2, "FRO-2"), (3, "FROp3")):
            f = s1["arms"][arm]["failures"]
            if f:
                rr_meas.setdefault("P1prime", {})[d] = c0f / f
    out = []
    for pid, cell in rho.items():
        for d in (1, 2, 3):
            r = cell["rho"].get(str(d), {})
            out.append({"point": pid, "r": cell["r"], "d": cell["d"], "t": cell["t"],
                        "delta": d, "rho": r.get("rho"),
                        "deferred_true": r.get("deferred_true_per_instance"),
                        "avoided_false": r.get("avoided_false_per_instance"),
                        "rr_measured": rr_meas.get(pid, {}).get(d)})
    return out


def key_heterogeneity():
    """Quantify what the main pool says about per-key DFR heterogeneity.

    The paper's original heterogeneity gate (P90-P10 >= 3 log10) failed and is
    reported as such.  This turns the failure into a measured bound: is the
    per-key count distribution distinguishable from homogeneous Poisson, and
    what CV of per-key DFR does the data exclude?  Also: are the keys that fail
    under C0 the same keys that fail under FRO-2?"""
    from scipy.stats import spearmanr, chi2, norm
    d = _load(R / "round_controls" / "phase1_round_controls.json")
    if not d:
        return None
    c0 = np.array(d["groups"]["G0"]["arms"]["C0"]["per_key_failures"], dtype=float)
    f2 = np.array(d["groups"]["G0"]["arms"]["FRO-2"]["per_key_failures"], dtype=float)
    n, nk = 3000, len(c0)
    mean, var = c0.mean(), c0.var(ddof=1)
    se = mean * np.sqrt(2 / (nk - 1))
    z = (var - mean) / se
    var_hi = var * (nk - 1) / chi2.ppf(0.05, nk - 1)
    pbar = c0.sum() / (n * nk)
    cv_hi = np.sqrt(max(var_hi - mean, 0) / (n * n)) / pbar
    cv_det = np.sqrt(1.645 * se / (n * n)) / pbar
    rho = spearmanr(c0, f2)
    rng = np.random.default_rng(20260905)
    null = np.array([spearmanr(rng.poisson(mean, nk), rng.poisson(f2.mean(), nk)).statistic
                     for _ in range(2000)])
    out = {"n_keys": nk, "errors_per_key": n, "c0_total": int(c0.sum()),
           "fro2_total": int(f2.sum()),
           "homogeneity": {"var_over_mean": float(var / mean), "z": float(z),
                           "p_two_sided": float(2 * (1 - norm.cdf(abs(z))))},
           "per_key_cv_upper95": float(cv_hi), "per_key_cv_detectable": float(cv_det),
           "c0_vs_fro2_per_key_spearman": float(rho.statistic),
           "c0_vs_fro2_p": float(rho.pvalue),
           "null_spearman_ci95": [float(np.percentile(null, 2.5)),
                                  float(np.percentile(null, 97.5))]}
    return out


def main():
    cells = cells_from_round_controls() + cells_from_new()
    with open(TU / "analysis_cells.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cells[0].keys()), extrasaction="ignore")
        w.writeheader()
        for c in cells:
            w.writerow(c)
    print(f"cells: {len(cells)} -> {TU/'analysis_cells.csv'}")
    for c in sorted(cells, key=lambda x: (x["axis"], x["t"], x.get("budget", 0))):
        rr = "-" if c.get("rr") is None else f"{c['rr']:.3f}"
        lo = c.get("rr_lo"); hi = c.get("rr_hi")
        ci = f"[{lo:.3f},{hi:.3f}]" if lo is not None and hi is not None else ""
        print(f"  {c['axis']:7s} {c['point']:16s} t={c['t']:3d} B={c.get('budget','-'):>2} "
              f"{c['arm']:7s} DFR={c['c0_dfr']:.3e} RR={rr} {ci}  ({c['src']})")

    rows = rho_table()
    if rows:
        print("\nexchange ratios (deferred true vs avoided false per instance):")
        for r in rows:
            rho = "inf" if r["rho"] is None else f"{r['rho']:.3f}"
            print(f"  {r['point']:22s} delta {r['delta']:+d}: "
                  f"deferred {r['deferred_true']:7.3f}  avoided {r['avoided_false']:7.3f}  rho={rho}")

    rv = rho_vs_rr()
    if rv:
        print("\nrho vs measured RR (per work point and delta):")
        for q in sorted(rv, key=lambda x: (x["point"], x["delta"])):
            rr = "-" if q["rr_measured"] is None else f"{q['rr_measured']:.2f}"
            rho_t = "-" if q["rho"] is None else f"{q['rho']:.3f}"
            print(f"  {q['point']:9s} (r={q['r']:5d},d={q['d']:2d},t={q['t']:3d}) "
                  f"delta +{q['delta']}: rho={rho_t}  RR_measured={rr}")

    kh = key_heterogeneity()
    if kh:
        print("\nper-key heterogeneity on the main pool (archived, 92 keys x 3000):")
        print(f"  var/mean = {kh['homogeneity']['var_over_mean']:.3f}  "
              f"z = {kh['homogeneity']['z']:.2f}  p = {kh['homogeneity']['p_two_sided']:.3f} "
              f"(Poisson-consistent)")
        print(f"  95% upper bound on per-key DFR CV = {kh['per_key_cv_upper95']*100:.1f}% "
              f"(detectable: {kh['per_key_cv_detectable']*100:.1f}%)")
        print(f"  Spearman(C0 per-key, FRO-2 per-key) = "
              f"{kh['c0_vs_fro2_per_key_spearman']:.3f} "
              f"(independent-Poisson null CI95 {kh['null_spearman_ci95'][0]:.3f}.."
              f"{kh['null_spearman_ci95'][1]:.3f})")

    summary = {"n_cells": len(cells), "cells": cells, "rho": rows,
               "rho_vs_rr": rv, "key_heterogeneity": kh}
    json.dump(summary, open(TU / "analysis_summary.json", "w", encoding="utf-8"), indent=1)
    print(f"\n-> {TU/'analysis_summary.json'}")


if __name__ == "__main__":
    main()
