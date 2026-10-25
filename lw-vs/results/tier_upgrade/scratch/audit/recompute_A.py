#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Auditor A: recompute every headline number from raw per-key arrays."""
import json, sys, math
from pathlib import Path
import numpy as np

ROOT = Path("d:/桌面/TOUGAO - c")
TU = ROOT / "lw-vs" / "results" / "tier_upgrade"
sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))
from qcmdpc.stats import cluster_bootstrap_paired, sign_test_paired, wilson_upper

out = []

def rec(tag, doc, src, srcfile, sev="?"):
    match = (abs(float(doc) - float(src)) < 1e-9) if (doc is not None and src is not None) else (doc == src)
    out.append((tag, doc, src, srcfile, "OK" if match else "MISMATCH", sev))
    print(f"{'OK ' if match else '*** MISMATCH ***'} {tag}: doc={doc!r} src={src!r} [{srcfile}]")

# ---------------- T90 ----------------
st = json.load(open(TU / "state_T90.json", encoding="utf-8"))
per0 = np.array(st["arms"]["C0"], dtype=np.int64)
per2 = np.array(st["arms"]["FRO-2"], dtype=np.int64)
E = st["errors_done"]
n = len(per0)
trials = n * E
print(f"T90: keys={n} E={E} trials={trials} C0sum={per0.sum()} FRO2sum={per2.sum()}")
rec("T90 C0 failures doc=130", 130, int(per0.sum()), "state_T90.json")
rec("T90 FRO-2 failures doc=35", 35, int(per2.sum()), "state_T90.json")
rec("T90 trials doc=1,840,000", 1840000, trials, "state_T90.json")
rec("T90 C0 DFR 7.07e-5", 7.07e-5, per0.sum()/trials, "state_T90.json")
boot = cluster_bootstrap_paired(per0, per2, E, B=10000, seed=20260905)
rr, (lo, hi) = boot["point"]["risk_ratio"], boot["ci"]["risk_ratio"]
print(f"T90 recomputed: RR={rr:.6f} CI=[{lo:.6f}, {hi:.6f}]")
rec("T90 RR 3.71 (round)", 3.71, round(rr, 2), "recompute")
ph = json.load(open(TU / "phase_T90.json", encoding="utf-8"))
rec("T90 phase rr stored", ph["rr"], rr, "phase_T90.json vs recompute")
rec("T90 phase CI lo stored", ph["rr_ci95"][0], lo, "phase_T90.json vs recompute")
rec("T90 phase CI hi stored", ph["rr_ci95"][1], hi, "phase_T90.json vs recompute")
rec("T90 CI lo doc 2.69", 2.69, round(lo, 2), "recompute")
rec("T90 CI hi doc 5.57", 5.57, round(hi, 2), "recompute")
sg = sign_test_paired(per0, per2)
print("T90 sign test:", sg)
rec("T90 sign improved 60", 60, sg["improved"], "recompute")
rec("T90 sign worse 6", 6, sg["worse"], "recompute")
rec("T90 sign tied 26", 26, sg["tied"], "recompute")
rec("T90 sign p 2.7e-12", 2.7e-12, sg["p_two_sided"], "recompute")
nk = int((per0 > 0).sum())
print("T90 keys with >=1 C0 failure:", nk, "(doc says 72)")
rec("T90 failures on 72 keys", 72, nk, "recompute")

# ---------------- P1PP ----------------
pp = json.load(open(TU / "p1pp_main.json", encoding="utf-8"))
E3 = pp["errors_per_key"]
per0p = np.array(pp["arms"]["C0"]["per_key_failures"], dtype=np.int64)
print(f"P1PP: keys={pp['n_keys']} E={E3} trials={pp['trials']} C0={per0p.sum()}")
rec("P1PP C0 94", 94, int(per0p.sum()), "p1pp_main.json")
rec("P1PP C0 DFR 1.958e-3", 1.958e-3, per0p.sum()/pp["trials"], "p1pp_main.json")
for nm, docfail in (("FRO-2", 21), ("FRONEG", 582)):
    a = pp["arms"][nm]
    pera = np.array(a["per_key_failures"], dtype=np.int64)
    boot = cluster_bootstrap_paired(per0p, pera, E3, B=10000, seed=20260905)
    rr, (lo, hi) = boot["point"]["risk_ratio"], boot["ci"]["risk_ratio"]
    s = sign_test_paired(per0p, pera)
    print(f"P1PP {nm}: recomputed RR={rr:.6f} CI=[{lo:.6f},{hi:.6f}] fail={pera.sum()} "
          f"dfr={pera.sum()/pp['trials']:.6e} sign={s['improved']}/{s['worse']}/{s['tied']}")
    rec(f"P1PP {nm} failures", docfail, int(pera.sum()), "p1pp_main.json")
    rec(f"P1PP {nm} stored rr", a["rr"], rr, "p1pp_main.json vs recompute")
    rec(f"P1PP {nm} stored ci lo", a["rr_ci95"][0], lo, "p1pp_main.json vs recompute")
    rec(f"P1PP {nm} stored ci hi", a["rr_ci95"][1], hi, "p1pp_main.json vs recompute")

# doc values
rec("P1PP FRO-2 doc RR 4.476", 4.476, pp["arms"]["FRO-2"]["rr"], "p1pp_main.json")
rec("P1PP FRO-2 doc CI lo 2.967", 2.967, round(pp["arms"]["FRO-2"]["rr_ci95"][0], 3), "p1pp_main.json")
rec("P1PP FRO-2 doc CI hi 7.250", 7.250, round(pp["arms"]["FRO-2"]["rr_ci95"][1], 3), "p1pp_main.json")
rec("P1PP FRONEG doc RR 0.162", 0.162, round(pp["arms"]["FRONEG"]["rr"], 3), "p1pp_main.json")
rec("P1PP FRONEG doc CI lo 0.119", 0.119, round(pp["arms"]["FRONEG"]["rr_ci95"][0], 3), "p1pp_main.json")
rec("P1PP FRONEG doc CI hi 0.209", 0.209, round(pp["arms"]["FRONEG"]["rr_ci95"][1], 3), "p1pp_main.json")
rec("P1PP FRO-2 DFR doc 4.375e-4", 4.375e-4, pp["arms"]["FRO-2"]["dfr"], "p1pp_main.json")
rec("P1PP FRONEG DFR doc 1.213e-2", 1.213e-2, round(pp["arms"]["FRONEG"]["dfr"], 6), "p1pp_main.json")

# ---------------- S1 five-arm ----------------
s1 = json.load(open(TU / "surrogate_S1.json", encoding="utf-8"))
E2 = s1["errors_per_key"]
per0s = np.array(s1["arms"]["C0"]["per_key"], dtype=np.int64)
print(f"S1: keys={s1['n_keys']} E={E2} trials={s1['arms']['C0']['trials']} C0={per0s.sum()}")
docs = {"FROp1": (83, 3.40, 2.74, 4.28), "FRO-2": (68, 4.15, 3.29, 5.38),
        "FROp3": (73, 3.86, 3.05, 5.07), "FRONEG": (2235, 0.126, 0.111, 0.141)}
for nm, (df, drr, dlo, dhi) in docs.items():
    a = s1["arms"][nm]
    pera = np.array(a["per_key"], dtype=np.int64)
    boot = cluster_bootstrap_paired(per0s, pera, E2, B=10000, seed=20260905)
    rr, (lo, hi) = boot["point"]["risk_ratio"], boot["ci"]["risk_ratio"]
    print(f"S1 {nm}: fail={pera.sum()} dfr={pera.sum()/276000:.6e} RR={rr:.6f} CI=[{lo:.6f},{hi:.6f}]")
    rec(f"S1 {nm} failures", df, int(pera.sum()), "surrogate_S1.json")
    rec(f"S1 {nm} doc RR", drr, round(rr, 2), "recompute")
    rec(f"S1 {nm} doc CI lo", dlo, round(lo, 2), "recompute")
    rec(f"S1 {nm} doc CI hi", dhi, round(hi, 2), "recompute")

# reproduction gate: bit-identical per-key arrays vs archive phase1 G0
arch = json.load(open(ROOT / "lw-vs/results/round_controls/phase1_round_controls.json", encoding="utf-8"))
g0 = arch["groups"]["G0"]["arms"]
a0 = np.array(g0["C0"]["per_key_failures"], dtype=np.int64)
a2 = np.array(g0["FRO-2"]["per_key_failures"], dtype=np.int64)
print("S1 C0 identical to phase1:", bool((a0 == per0s).all()))
print("S1 FRO-2 identical to phase1:", bool((a2 == np.array(s1['arms']['FRO-2']['per_key'])).all()))
rec("S1 C0 per-key bit-identical 282", True, bool((a0 == per0s).all() and a0.sum() == 282), "phase1_round_controls.json")
rec("S1 FRO-2 per-key bit-identical 68", True, bool((a2 == np.array(s1['arms']['FRO-2']['per_key'])).all() and a2.sum() == 68), "phase1_round_controls.json")
# archive headline RR recompute from phase1 arrays
boota = cluster_bootstrap_paired(a0, a2, 3000, B=10000, seed=20260905)
print("phase1 G0 FRO-2 RR recomputed:", boota["point"]["risk_ratio"], boota["ci"]["risk_ratio"],
      " stored:", g0["FRO-2"]["rr_vs_C0"], g0["FRO-2"]["rr_ci95"])
rec("archive RR 4.15", 4.15, round(boota["point"]["risk_ratio"], 2), "phase1_round_controls.json recompute")
rec("archive CI lo 3.29", 3.29, round(boota["ci"]["risk_ratio"][0], 2), "phase1_round_controls.json recompute")
rec("archive CI hi 5.38", 5.38, round(boota["ci"]["risk_ratio"][1], 2), "phase1_round_controls.json recompute")

# ---------------- key heterogeneity ----------------
from scipy.stats import spearmanr, chi2, norm
c0 = a0.astype(float)
f2 = a2.astype(float)
n2, nk2 = 3000, len(c0)
mean, var = c0.mean(), c0.var(ddof=1)
se = mean * math.sqrt(2 / (nk2 - 1))
z = (var - mean) / se
var_hi = var * (nk2 - 1) / chi2.ppf(0.05, nk2 - 1)
pbar = c0.sum() / (n2 * nk2)
cv_hi = math.sqrt(max(var_hi - mean, 0) / (n2 * n2)) / pbar
cv_det = math.sqrt(1.645 * se / (n2 * n2)) / pbar
rho_s = spearmanr(c0, f2)
rng = np.random.default_rng(20260905)
null = np.array([spearmanr(rng.poisson(mean, nk2), rng.poisson(f2.mean(), nk2)).statistic
                 for _ in range(2000)])
print(f"KEYHET: var/mean={var/mean:.6f} z={z:.6f} p={2*(1-norm.cdf(abs(z))):.6f} "
      f"cv_hi={cv_hi:.6f} cv_det={cv_det:.6f} spearman={rho_s.statistic:.6f} "
      f"null CI=[{np.percentile(null,2.5):.6f},{np.percentile(null,97.5):.6f}]")
rec("var/mean 0.981", 0.981, round(var/mean, 3), "recompute")
rec("z -0.13", -0.13, round(z, 2), "recompute")
rec("p 0.90", 0.90, round(2*(1-norm.cdf(abs(z))), 2), "recompute")
rec("CV upper 30%", 30.0, round(cv_hi*100, 1), "recompute")
rec("CV detectable 28%", 28.0, round(cv_det*100, 1), "recompute")
rec("Spearman 0.093", 0.093, round(rho_s.statistic, 3), "recompute")
rec("null lo -0.21", -0.21, round(np.percentile(null, 2.5), 2), "recompute")
rec("null hi 0.21", 0.21, round(np.percentile(null, 97.5), 2), "recompute")

# ---------------- L1a ----------------
l1a = json.load(open(TU / "l1a_firstround_margin.json", encoding="utf-8"))
tr = l1a["trials"]
pd_ = l1a["per_delta"]
print("L1a trials:", tr, "true_flag_positions:", l1a["true_flag_positions"], "false:", l1a["false_positions"])
for d in ("-1", "0", "1", "2", "3"):
    v = pd_[d]
    tot = (v["true"] + v["false"]) / tr
    tv = v["true"] / tr
    fv = v["false"] / tr
    print(f"  delta {d}: flips/inst={tot:.4f} true={tv:.4f} false={fv:.4f} tau_mean={v['tau_sum']/tr:.4f}")
fr = {d: pd_[d]["false"] for d in pd_}
rec("L1a d=0 flips 101.24", 101.24, round((pd_["0"]["true"]+pd_["0"]["false"])/tr, 2), "l1a json")
rec("L1a d=0 true 87.47", 87.47, round(pd_["0"]["true"]/tr, 2), "l1a json")
rec("L1a d=0 false 13.77", 13.77, round(pd_["0"]["false"]/tr, 2), "l1a json")
rec("L1a d=-1 flips 129.88", 129.88, round((pd_["-1"]["true"]+pd_["-1"]["false"])/tr, 2), "l1a json")
rec("L1a d=-1 true 98.69", 98.69, round(pd_["-1"]["true"]/tr, 2), "l1a json")
rec("L1a d=-1 false 31.19", 31.19, round(pd_["-1"]["false"]/tr, 2), "l1a json")
rec("L1a d=1 flips 80.77", 80.77, round((pd_["1"]["true"]+pd_["1"]["false"])/tr, 2), "l1a json")
rec("L1a d=1 true 74.99", 74.99, round(pd_["1"]["true"]/tr, 2), "l1a json")
rec("L1a d=1 false 5.78", 5.78, round(pd_["1"]["false"]/tr, 2), "l1a json")
rec("L1a d=2 flips 64.30", 64.30, round((pd_["2"]["true"]+pd_["2"]["false"])/tr, 2), "l1a json")
rec("L1a d=2 true 61.99", 61.99, round(pd_["2"]["true"]/tr, 2), "l1a json")
rec("L1a d=2 false 2.30", 2.30, round(pd_["2"]["false"]/tr, 2), "l1a json")
rec("L1a d=3 flips 50.14", 50.14, round((pd_["3"]["true"]+pd_["3"]["false"])/tr, 2), "l1a json")
rec("L1a d=3 true 49.28", 49.28, round(pd_["3"]["true"]/tr, 2), "l1a json")
rec("L1a d=3 false 0.86", 0.86, round(pd_["3"]["false"]/tr, 2), "l1a json")
rec("L1a false ratio -1 x2.26", 2.26, round(fr["-1"]/fr["0"], 2), "l1a json")
rec("L1a false ratio +1 div2.4", 2.4, round(fr["0"]/fr["1"], 1), "l1a json")
rec("L1a false ratio +2 div6.0", 6.0, round(fr["0"]/fr["2"], 1), "l1a json")
rec("L1a false ratio +3 div16.0", 16.0, round(fr["0"]/fr["3"], 1), "l1a json")
rec("L1a tau1~42", 42, round(pd_["0"]["tau_sum"]/tr, 0), "l1a json")
# rho from counts
for d in ("1", "2", "3"):
    defd = (pd_["0"]["true"] - pd_[d]["true"]) / tr
    avf = (pd_["0"]["false"] - pd_[d]["false"]) / tr
    r = avf / defd
    mr = l1a["model_rho"][d]
    print(f"  rho({d}): recomputed={r:.6f} json={mr['rho']:.6f} "
          f"deferred={defd:.6f}/{mr['deferred_true_per_instance']:.6f} avoided={avf:.6f}/{mr['avoided_false_per_instance']:.6f}")
    rec(f"L1a rho({d})", mr["rho"], r, "l1a json recompute")
rec("L1a rho(+1) doc 0.640", 0.640, round(l1a["model_rho"]["1"]["rho"], 3), "l1a json")
rec("L1a rho(+2) doc 0.450", 0.450, round(l1a["model_rho"]["2"]["rho"], 3), "l1a json")
rec("L1a rho(+3) doc 0.338", 0.338, round(l1a["model_rho"]["3"]["rho"], 3), "l1a json")

# ---------------- L1b ----------------
l1b = json.load(open(TU / "l1b_classic_carrier.json", encoding="utf-8"))
for nm, doc_it, doc_2r in (("C0", 2.054, 94.6), ("FRO-2", 2.446, 55.4), ("FRONEG", 2.232, 76.8)):
    a = l1b["arms"][nm]
    it = float(np.mean(a["per_key_mean_iters"]))
    print(f"L1b {nm}: mean_iters stored={a['mean_iters']} recomputed-from-per-key={it:.6f} "
          f"2r={a['two_round_fraction']}")
    rec(f"L1b {nm} mean iters doc {doc_it}", doc_it, round(a["mean_iters"], 3), "l1b json")
    rec(f"L1b {nm} mean iters self-consistent", round(a["mean_iters"], 6), round(it, 6), "recompute")
    rec(f"L1b {nm} two-round doc {doc_2r}", doc_2r, round(a["two_round_fraction"]*100, 1), "l1b json")
rec("L1b rule-of-three 9.4e-5", 9.4e-5, l1b["arms"]["C0"]["upper95"], "l1b json")

# ---------------- L1c ----------------
l1c = json.load(open(TU / "l1c_bikeflip_firstround_ablation.json", encoding="utf-8"))
doc = {"spec": (0.09, 99.98, 2.999), "no_first_round_delta": (37.35, 100.0, 2.627),
       "double_first_round_delta": (0.0, 86.8, 3.132), "first_round_delta_only": (6.14, 100.0, 2.939)}
for nm, (d2, d3, dit) in doc.items():
    a = l1c["arms"][nm]
    it = float(np.mean(a["per_key_conv_iters"]))
    print(f"L1c {nm}: 2r={a['two_round_fraction']} 3r={a['three_round_fraction']} "
          f"mean={a['mean_conv_iters']} recomp={it:.6f} fails={a['failures']}")
    rec(f"L1c {nm} two-round doc {d2}", d2, round(a["two_round_fraction"]*100, 2), "l1c json")
    rec(f"L1c {nm} three-round doc {d3}", d3, round(a["three_round_fraction"]*100, 2), "l1c json")
    rec(f"L1c {nm} mean doc {dit}", dit, round(a["mean_conv_iters"], 3), "l1c json")
    rec(f"L1c {nm} mean self-consistent", round(a["mean_conv_iters"], 6), round(it, 6), "recompute")

print("\nDONE part 1")
