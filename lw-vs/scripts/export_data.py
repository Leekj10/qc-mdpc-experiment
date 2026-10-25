#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export manuscript-facing figure/source tables for the lw-vs package.

Reads ONLY the frozen archives under 实验/qcmdpc-study/results/ and new/*_data*/.
Never recomputes statistics; this script reshapes archived numbers into tidy CSVs
so every figure in lw-vs can be traced back to an archived JSON.

Evidence tiers (see new/innovation_status_audit_zh.md):
  tier 1  formal primary        results/m5_formal/            92-94 keys x 3000
  tier 2  preregistered confirm  new/expanded_data/            50 keys x 1000
  tier 3  exploratory ablation   results/q2_capture, q2_iterablation  12 keys x 400
  tier 4  prototype              new/ncw_adaptive_data_v2, engineering_data_v2
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "实验" / "qcmdpc-study" / "results"
NEW = ROOT / "new"
OUT = ROOT / "lw-vs" / "data"
OUT.mkdir(parents=True, exist_ok=True)

GROUP_LABEL = {"G0": "RAND", "G2_d12": "TYPE-I", "G3": "NCW-shallow"}
GROUP_ORDER = ["G0", "G2_d12", "G3"]
TIER = {"formal": 1, "confirm": 2, "exploratory": 3, "prototype": 4}

_written: list[str] = []


def load(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_csv(name: str, rows: list[dict], fields: list[str] | None = None) -> None:
    if not rows:
        print(f"  !! {name}: no rows, skipped")
        return
    fields = fields or list(rows[0].keys())
    path = OUT / name
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in fields})
    _written.append(name)
    print(f"  ok {name}  ({len(rows)} rows)")


def arm_of(d: dict, *names):
    """Return the first arm present, tolerating C0_base / C0 naming drift."""
    for n in names:
        if n in d:
            return d[n]
    raise KeyError(f"none of {names} in {list(d.keys())}")


# --------------------------------------------------------------------------
# 1. Formal primary results (tier 1)  --  P1' = (4801, 45, 92)
# --------------------------------------------------------------------------
def formal_main() -> None:
    print("[1] formal primary (P1')")
    rep = load(EXP / "m5_formal" / "report.json")
    clus = load(EXP / "m5_formal" / "cluster_stats.json")
    holm_sign = clus["full_formal"]["holm"]["sign_test"]["holm"]
    holm_mcn = clus["full_formal"]["holm"]["mcnemar"]["holm"]
    mc_raw = clus["full_formal"]["holm"]["mcnemar"]["raw"]

    rows = []
    for gid in GROUP_ORDER:
        g = rep["groups"][gid]
        c0, c4 = g["C0_base"], g["C4_first_p2"]
        cs = clus["full_formal"]["groups"][gid]["cluster_bootstrap"]
        rows.append({
            "tier": 1, "source": "results/m5_formal",
            "group": gid, "condition": GROUP_LABEL[gid],
            "n_keys": g["n_keys"], "errors_per_key": rep["E_per_key"],
            "c0_failures": c0["failures"], "c0_trials": c0["trials"],
            "c0_dfr": c0["dfr"], "c0_upper95": c0["upper95"],
            "c0_log10_upper95": c0["log10_upper95"],
            "fro2_failures": c4["failures"], "fro2_trials": c4["trials"],
            "fro2_dfr": c4["dfr"], "fro2_upper95": c4["upper95"],
            "fro2_log10_upper95": c4["log10_upper95"],
            "rr": cs["point"]["risk_ratio"],
            "rr_lo": cs["ci"]["risk_ratio"][0], "rr_hi": cs["ci"]["risk_ratio"][1],
            "dfr_diff": cs["point"]["dfr_diff"],
            "dfr_diff_lo": cs["ci"]["dfr_diff"][0], "dfr_diff_hi": cs["ci"]["dfr_diff"][1],
            "rr_excludes_1": cs["rr_excludes_1"],
            "holm_sign_p": holm_sign[gid],
            "mcnemar_exact_p": mc_raw[gid], "holm_mcnemar_p": holm_mcn[gid],
            "pairing": rep["groups"][gid]["paired"] and "same (H,e,s)",
        })
    write_csv("t1_formal_main.csv", rows)

    # paired-instance discordance table
    prows = []
    for gid in GROUP_ORDER:
        p = rep["groups"][gid]["paired"]
        prows.append({
            "tier": 1, "source": "results/m5_formal",
            "group": gid, "condition": GROUP_LABEL[gid],
            "both_succeed_or_both_fail": p.get("both"),
            "c0_fails_fro2_succeeds": p.get("c0_only"),
            "c0_succeeds_fro2_fails": p.get("c4_only"),
            "mcnemar_exact_p": p.get("mcnemar_exact_p"),
        })
    write_csv("t1_paired_discordance.csv", prows)

    # per-key failures (for the paired per-key panel)
    krows = []
    for gid in GROUP_ORDER:
        g = rep["groups"][gid]
        c0k = g["C0_base"]["per_key_failures"]
        c4k = g["C4_first_p2"]["per_key_failures"]
        for i, (a, b) in enumerate(zip(c0k, c4k)):
            krows.append({"tier": 1, "group": gid, "condition": GROUP_LABEL[gid],
                          "key_index": i, "c0_failures": a, "fro2_failures": b,
                          "errors_per_key": rep["E_per_key"]})
    write_csv("t1_per_key.csv", krows)

    # gate + pure-fresh holdout
    pf = clus["pure_fresh"]
    gate = pf["gate_pure_fresh"]
    grows = [{
        "source": "results/m5_formal/report.json",
        "scope": "full_formal", "worst_group": "G2_d12",
        "worst_log10U_c0": rep["worst_group_log10U"]["C0_base"],
        "worst_log10U_fro2": rep["worst_group_log10U"]["C4_first_p2"],
        "improvement_log10": rep["improvement_log10"],
        "gate_ge_0.5": rep["gate_improvement_ge_0.5"],
        "rand_noninferior": rep["gate_noninferior_G0"],
        "gate_pass": rep["gate_pass"], "total_keys": 278, "samples_per_arm": 834000,
    }, {
        "source": "results/m5_formal/cluster_stats.json",
        "scope": "pure_fresh_test_keys", "worst_group": gate["worst_group_base_gid"],
        "worst_log10U_c0": gate["worst_group_log10U_base"],
        "worst_log10U_fro2": gate["worst_group_log10U_c4"],
        "improvement_log10": gate["improvement_log10"],
        "gate_ge_0.5": gate["gate_improvement_ge_0.5"],
        "rand_noninferior": gate["rand_noninferior"],
        "gate_pass": gate["gate_pass"], "total_keys": gate["total_fresh_keys"],
        "samples_per_arm": gate["total_fresh_samples_per_arm"],
    }]
    write_csv("t1_gate_fresh.csv", grows)
    print(f"      full-pool improvement={rep['improvement_log10']:.4f} "
          f"pass={rep['gate_pass']}")
    print(f"      pure-fresh improvement={gate['improvement_log10']:.4f} "
          f"keys={gate['total_fresh_keys']} pass={gate['gate_pass']}")


# --------------------------------------------------------------------------
# 2. First-round mechanism (tier 1 instrumented)
# --------------------------------------------------------------------------
def mechanism() -> None:
    print("[2] first-round instrumentation")
    rep = load(EXP / "firstround_mech" / "report.json")
    rows = []
    for gid in GROUP_ORDER:
        g = rep["groups"][gid]
        for arm in ("C0_base", "C4_first_p2"):
            a = g["arms"][arm]
            rows.append({
                "tier": 1, "source": "results/firstround_mech",
                "group": gid, "condition": GROUP_LABEL[gid],
                "arm": "C0" if arm == "C0_base" else "FRO-2",
                "n_keys": g["n_keys"], "errors_per_key": g["E_per_key"],
                "n_samples": g["n_samples"],
                "failures": a["failures"],
                "mean_total_first": a["mean_total_first"],
                "mean_correct_first": a["mean_correct_first"],
                "mean_incorrect_first": a["mean_incorrect_first"],
                "mean_residual_r1": a["mean_residual_r1"],
                "mean_iters": a["mean_iters"],
            })
    write_csv("t1_mechanism_firstround.csv", rows)

    # Failure-mode composition. The archived run (results/m5_mechanism, 2026-09-04) used
    # the pre-fix early-misflip window len(flip_positions)//4; the preregistered rerun
    # (lw-vs/results/mechanism_preregistered) uses the frozen ceil(max_iter/4). Counts are
    # identical because parallel bit-flipping runs its full budget on every failure, so
    # len(flip_positions) == max_iter == 20 and both windows equal 5. Both are exported so
    # the reader can check that equivalence rather than take it on trust.
    new = ROOT / "lw-vs" / "results" / "mechanism_preregistered" / "report.json"
    arch = EXP / "m5_mechanism" / "report.json"
    mrows, cmp_rows = [], []
    run = load(new) if new.exists() else load(arch)
    tags = {"archived_pre_fix": load(arch),
            "preregistered_rerun": (load(new) if new.exists() else None)}
    for gid in GROUP_ORDER:
        g = run["groups"][gid]
        for arm in ("C0_base", "C4_first_p2"):
            modes = g["failure_modes"][arm]
            tot = sum(modes.values()) or 1
            armL = "C0" if arm == "C0_base" else "FRO-2"
            for mode, cnt in modes.items():
                mrows.append({
                    "tier": 1,
                    "source": "lw-vs/results/mechanism_preregistered",
                    "classifier": "PREREGISTERED ceil(max_iter/4)",
                    "group": gid, "condition": GROUP_LABEL[gid],
                    "arm": armL, "mode": mode, "count": cnt, "fraction": cnt / tot,
                })
            a = tags["archived_pre_fix"]["groups"][gid]["failure_modes"][arm]
            for mode in modes:
                cmp_rows.append({
                    "group": gid, "condition": GROUP_LABEL[gid], "arm": armL,
                    "mode": mode,
                    "archived_pre_fix_len_div4": a.get(mode, 0),
                    "preregistered_ceil_maxiter4": modes.get(mode, 0),
                    "identical": int(a.get(mode, 0) == modes.get(mode, 0)),
                })
    write_csv("t1_failure_modes.csv", mrows)
    write_csv("t1_failure_modes_classifier_comparison.csv", cmp_rows)
    same = all(r["identical"] for r in cmp_rows)
    print(f"      classifier comparison: {'all cells identical' if same else 'DIFFERS'}"
          f" ({len(cmp_rows)} cells)")

    trows = []
    for gid in GROUP_ORDER:
        t = run["groups"][gid]["transitions"]
        trows.append({
            "tier": 1, "source": "lw-vs/results/mechanism_preregistered",
            "group": gid, "condition": GROUP_LABEL[gid],
            "c0_fails": run["groups"][gid]["fails"]["C0_base"],
            "fro2_fails": run["groups"][gid]["fails"]["C4_first_p2"],
            "rescued_by_fro2": t.get("c0_only_rescued"),
            "new_failures_by_fro2": t.get("c4_only_new"),
            "both_fail": t.get("both_fail"),
            "both_ok": t.get("concordant_ok"),
        })
    write_csv("t1_mechanism_transitions.csv", trows)


# --------------------------------------------------------------------------
# 3. Preregistered expanded confirmation = temporal ablation (tier 2)
# --------------------------------------------------------------------------
def expanded() -> None:
    print("[3] expanded confirmation / temporal ablation (50x1000)")
    d = load(NEW / "expanded_data" / "expanded_analysis.json")
    prot = d["protocol"]
    rows = []
    for param in ("P2_expanded", "P3_expanded"):
        p = prot["parameters"]["P2" if param.startswith("P2") else "P3"]
        for gid in GROUP_ORDER:
            cell = d["cells"][param][gid]
            c0 = cell["C0"]
            for dec, c in cell.items():
                rr = c.get("rr_vs_c0") or {}
                rows.append({
                    "tier": 2, "source": "new/expanded_data/expanded_analysis.json",
                    "point": param.split("_")[0], "r": p["r"], "d": p["d"], "t": p["t"],
                    "group": gid, "condition": GROUP_LABEL[gid],
                    "decoder": dec,
                    "n_keys": prot["groups"][gid]["n_keys"],
                    "errors_per_key": prot["errors_per_key"],
                    "failures": c["failures"], "trials": c["trials"],
                    "dfr": c["dfr"], "upper95": c["upper95"],
                    "avg_iters": c["avg_iters"], "ms_per_decode": c["ms_per_decode"],
                    "rr_vs_c0": rr.get("point_rr", ""),
                    "rr_lo": (rr.get("ci95") or ["", ""])[0],
                    "rr_hi": (rr.get("ci95") or ["", ""])[1],
                    "c0_failures": c0["failures"], "c0_dfr": c0["dfr"],
                })
    write_csv("t2_expanded_temporal.csv", rows)

    # pivot: schedule x condition -> DFR, at each point (for the ablation figure)
    prows = []
    for param in ("P2_expanded", "P3_expanded"):
        for gid in GROUP_ORDER:
            cell = d["cells"][param][gid]
            base = cell["C0"]["dfr"]
            for dec in ("C0", "FRO-1", "FRO-2", "FRO-3", "R2-2", "UNIFORM-2"):
                c = cell[dec]
                prows.append({
                    "tier": 2, "point": param.split("_")[0],
                    "group": gid, "condition": GROUP_LABEL[gid],
                    "schedule": dec, "dfr": c["dfr"], "failures": c["failures"],
                    "trials": c["trials"],
                    "rr_vs_c0": c["dfr"] and base / c["dfr"] if c["dfr"] else "",
                    "avg_iters": c["avg_iters"],
                    "c0_dfr": base,
                })
    write_csv("t2_temporal_pivot.csv", prows)


# --------------------------------------------------------------------------
# 4. Transfer, capture boundary, iteration ablation (tiers 2-3)
# --------------------------------------------------------------------------
def scope() -> None:
    print("[4] transfer / capture / iteration ablation")

    # 4a. P2second transfer (formal second operating point)
    rep = load(EXP / "p2second_transfer" / "report.json")
    rows = []
    for gid in GROUP_ORDER:
        g = rep["groups"][gid]
        c0, c4 = g["C0_base"], g["C4_first_p2"]
        rows.append({
            "tier": 1, "source": "results/p2second_transfer",
            "point": "P2", "r": rep["param"]["r"], "d": rep["param"]["d"],
            "t": rep["param"]["t"],
            "group": gid, "condition": GROUP_LABEL[gid],
            "n_keys": g["n_keys"], "errors_per_key": g["E_per_key"],
            "c0_failures": c0["failures"], "c0_trials": c0["trials"],
            "c0_dfr": c0["dfr"], "c0_upper95": c0["upper95"],
            "fro2_failures": c4["failures"], "fro2_trials": c4["trials"],
            "fro2_dfr": c4["dfr"], "fro2_upper95": c4["upper95"],
            "rr": g["cluster_bootstrap"]["point"]["risk_ratio"],
            "rr_lo": g["cluster_bootstrap"]["ci"]["risk_ratio"][0],
            "rr_hi": g["cluster_bootstrap"]["ci"]["risk_ratio"][1],
            "rr_excludes_1": g["cluster_bootstrap"]["rr_excludes_1"],
        })
    write_csv("t2_transfer_p2.csv", rows)

    # 4b. capture gradient at kappa > d
    cap = load(EXP / "q2_capture" / "report.json")
    rows = []
    for key in ("rand", "k12", "k46", "k60"):
        c = cap["constructions"][key]
        c0, c4 = c["C0_base"], c["C4_first_p2"]
        rows.append({
            "tier": 3, "source": "results/q2_capture",
            "construction": key, "kappa": c.get("kappa", 0),
            "n_keys": c["n_keys"], "n_samples": c["n_samples"],
            "c0_failures": c0["failures"], "c0_trials": c0["trials"],
            "c0_dfr": c0["dfr"],
            "fro2_failures": c4["failures"], "fro2_trials": c4["trials"],
            "fro2_dfr": c4["dfr"],
            "rr": c["cluster_bootstrap"]["point"]["risk_ratio"],
            "rr_lo": c["cluster_bootstrap"]["ci"]["risk_ratio"][0],
            "rr_hi": c["cluster_bootstrap"]["ci"]["risk_ratio"][1],
        })
    write_csv("t3_capture_gradient.csv", rows)

    # 4c. iteration budget ablation
    it = load(EXP / "q2_iterablation" / "report.json")
    rows = []
    for gid, g in it["groups"].items():
        for b, cell in g["budgets"].items():
            c0, c4 = cell["C0_base"], cell["C4_first_p2"]
            rows.append({
                "tier": 3, "source": "results/q2_iterablation",
                "group": gid, "condition": GROUP_LABEL.get(gid, gid),
                "budget": int(b),
                "n_samples": cell["n_samples"],
                "c0_failures": c0["failures"], "c0_trials": c0["trials"],
                "c0_dfr": c0["dfr"],
                "fro2_failures": c4["failures"], "fro2_trials": c4["trials"],
                "fro2_dfr": c4["dfr"],
                "rr": cell["cluster_bootstrap"]["point"]["risk_ratio"],
                "rr_lo": cell["cluster_bootstrap"]["ci"]["risk_ratio"][0],
                "rr_hi": cell["cluster_bootstrap"]["ci"]["risk_ratio"][1],
                "rr_excludes_1": cell["cluster_bootstrap"]["rr_excludes_1"],
            })
    write_csv("t3_iteration_budget.csv", rows)


# --------------------------------------------------------------------------
# 5. Modern-decoder comparison (tier 1 matched + production references)
# --------------------------------------------------------------------------
def modern() -> None:
    print("[5] modern decoders")
    bf = load(EXP / "cmp_bf_p1_formal" / "report.json")
    rows = []
    for gid in GROUP_ORDER:
        g = bf["groups"][gid]
        c0, c4, bfa = g["C0_base"], g["C4_first_p2"], g["BIKE_Flip"]
        rows.append({
            "tier": 1, "source": "results/cmp_bf_p1_formal",
            "point": "P1'", "semantics": "static",
            "group": gid, "condition": GROUP_LABEL[gid],
            "n_keys": g["n_keys"], "trials_per_arm": c0["trials"],
            "c0_failures": c0["failures"], "c0_dfr": c0["dfr"],
            "fro2_failures": c4["failures"], "fro2_dfr": c4["dfr"],
            "bikeflip_failures": bfa["failures"], "bikeflip_dfr": bfa["dfr"],
            "bf_vs_c0_mcnemar_p": g["paired"]["BF_vs_C0_base"]["mcnemar_exact_p"],
            "bf_vs_fro2_mcnemar_p": g["paired"]["BF_vs_C4_first_p2"]["mcnemar_exact_p"],
            "bf_convergence_iters": json.dumps(g["bf_convergence_iters"]),
        })
    write_csv("t1_modern_scaled.csv", rows)
    for r in rows:
        print(f"      {r['condition']:12s} C0={r['c0_dfr']:.4e} "
              f"FRO2={r['fro2_dfr']:.4e} BIKE-Flip={r['bikeflip_dfr']:.4e} "
              f"p(BFvsFRO2)={r['bf_vs_fro2_mcnemar_p']:.3f}")

    # native Level-1 production boundary
    l1 = load(EXP / "cmp_bf_l1" / "report.json")
    rows = []
    for gid, g in l1["groups"].items():
        row = {"tier": 1, "source": "results/cmp_bf_l1",
               "point": "BIKE Level-1", "r": l1["param"]["r"], "d": l1["param"]["d"],
               "t": l1["param"]["t"], "group": gid,
               "n_keys": g["n_keys"], "errors_per_key": g["E_per_key"],
               "n_samples": g["n_samples"]}
        for arm in ("C0_base", "C4_first_p2", "BIKE_Flip"):
            a = g[arm]
            tag = {"C0_base": "c0", "C4_first_p2": "fro2", "BIKE_Flip": "bikeflip"}[arm]
            row[f"{tag}_failures"] = a["failures"]
            row[f"{tag}_trials"] = a["trials"]
            row[f"{tag}_upper95"] = a["upper95"]
            row[f"{tag}_mean_conv_iters"] = a.get("mean_conv_iters", "")
        rows.append(row)
    write_csv("t1_native_l1.csv", rows)

    # production-scale offset hold-out (convergence cost signal)
    hold = load(NEW / "engineering_data_v2" / "native_l1_holdout.json")

    def _flatten(o, path="", acc=None):
        acc = acc if acc is not None else {}
        if isinstance(o, dict):
            for k, v in o.items():
                _flatten(v, f"{path}/{k}" if path else k, acc)
        else:
            acc[path] = o
        return acc

    flat = _flatten(hold)
    rows = [{"path": k, "value": v} for k, v in flat.items()]
    write_csv("t1_native_l1_holdout_flat.csv", rows)
    print("      native_l1_holdout flat keys:")
    for k, v in list(flat.items())[:14]:
        print(f"        {k} = {v}")


# --------------------------------------------------------------------------
# 6. Prototype / engineering comparisons (tier 4)
# --------------------------------------------------------------------------
def prototypes() -> None:
    print("[6] prototype decoders")
    eng = load(NEW / "engineering_data_v2" / "engineering_analysis.json")
    rows = []
    for param, gs in eng["cells"].items():
        p = eng["protocol"]["parameters"][param.split("_")[0]]
        for gid, meths in gs.items():
            for meth, c in meths.items():
                rows.append({
                    "tier": 4, "source": "new/engineering_data_v2/engineering_analysis.json",
                    "point": param.split("_")[0],
                    "r": p["r"], "d": p["d"], "t": p["t"],
                    "group": gid, "condition": GROUP_LABEL.get(gid, gid),
                    "method": meth,
                    "failures": c.get("failures"), "trials": c.get("trials"),
                    "dfr": c.get("dfr"), "upper95": c.get("upper95"),
                    "avg_iters": c.get("avg_iters"), "p99_iters": c.get("p99_iters"),
                    "avg_upc_calls": c.get("avg_upc_calls"),
                    "avg_probes": c.get("avg_probes"),
                    "trigger_rate": c.get("trigger_rate"),
                    "recovery_accept_rate": c.get("recovery_accept_rate"),
                    "ms_per_decode": c.get("ms_per_decode"),
                })
    write_csv("t4_engineering_cells.csv", rows)

    # STLR v2 dedicated run (adds rr_vs_fro2: the "no added benefit" evidence)
    stlr = load(NEW / "ncw_adaptive_data_v2" / "stlr_analysis.json")
    rows = []
    for param, gs in stlr["cells"].items():
        for gid, decs in gs.items():
            for dec, c in decs.items():
                rows.append({
                    "tier": 4, "source": "new/ncw_adaptive_data_v2/stlr_analysis.json",
                    "point": param.split("_")[0],
                    "group": gid, "condition": GROUP_LABEL.get(gid, gid),
                    "decoder": dec, "dfr": c.get("dfr"),
                    "failures": c.get("failures"), "trials": c.get("trials"),
                    "avg_iters": c.get("avg_iters"),
                })
    write_csv("t4_stlr_cells.csv", rows)

    # engineering pairwise risk ratios (cleanest forest input)
    src = NEW / "engineering_data_v2" / "engineering_pairwise_rr.csv"
    with open(src, encoding="utf-8-sig") as fh:
        rr = list(csv.DictReader(fh))
    write_csv("t4_engineering_pairwise.csv", rr)


# --------------------------------------------------------------------------
# 7. Exact-recovery audit (tier 1)
# --------------------------------------------------------------------------
def recovery() -> None:
    print("[7] exact-recovery audit")
    base = EXP / "exact_recovery_audit_20260923" / "formal_current"
    rep = load(base / "report.json")
    rows = []
    for gid, g in rep["groups"].items():
        for arm, a in g["arms"].items():
            rows.append({
                "tier": 1, "source": "results/exact_recovery_audit_20260923/formal_current",
                "group": gid, "condition": GROUP_LABEL.get(gid, gid),
                "arm": "C0" if "c0" in arm.lower() or "base" in arm.lower() else "FRO-2",
                "trials": a["trials"],
                "zero_syndrome": a["zero_syndrome"],
                "nonzero_syndrome": a["nonzero_syndrome"],
                "zero_syndrome_rate": a["zero_syndrome_rate"],
                "zero_syndrome_miscorrections": a["zero_syndrome_miscorrections"],
                "exact_recovery": a["exact_recovery"],
                "exact_recovery_failures": a["exact_recovery_failures"],
            })
    write_csv("t1_exact_recovery.csv", rows)
    tot = {}
    for r in rows:
        tot.setdefault(r["arm"], []).append(r["exact_recovery_failures"])
    for arm, v in tot.items():
        print(f"      {arm}: total exact-recovery failures = {sum(v)}")



# --------------------------------------------------------------------------
# 8. Prespecified offset-selection rule, validated at held-out point P4 (tier 1)
# --------------------------------------------------------------------------
def offset_rule() -> None:
    print("[8] prespecified offset rule at P4")
    path = ROOT / "lw-vs" / "results" / "offset_rule" / "report.json"
    if not path.exists():
        print("  !! results/offset_rule/report.json missing; run exp_offset_rule.py")
        return
    rep = load(path)
    pt = rep["protocol"]["point"]
    prof = []
    for row in rep["rule"]["table"]:
        prof.append({
            "tier": 1, "source": "results/offset_rule", "point": "P4",
            "r": pt["r"], "d": pt["d"], "t": pt["t"],
            "delta": row["delta"], "rho": row["rho"],
            "A1": row["A1"], "A0": row["A0"],
            "expected_incorrect_avoided": row["expected_incorrect_avoided"],
            "expected_correct_deferred": row["expected_correct_deferred"],
            "selected": int(row["delta"] == rep["rule"]["delta_star"]),
        })
    write_csv("t1_offset_rule_profile.csv", prof)

    val = []
    for label, a in rep["validation"]["arms"].items():
        val.append({
            "tier": 1, "source": "results/offset_rule", "point": "P4",
            "r": pt["r"], "d": pt["d"], "t": pt["t"],
            "arm": label,
            "n_keys": rep["validation"]["n_keys"],
            "errors_per_key": rep["validation"]["errors_per_key"],
            "failures": a["failures"], "trials": a["trials"],
            "dfr": a["dfr"], "upper95": a["upper95"],
            "rr_vs_c0": a.get("rr_vs_C0", ""),
            "rr_lo": (a.get("rr_ci95") or ["", ""])[0],
            "rr_hi": (a.get("rr_ci95") or ["", ""])[1],
            "rr_excludes_1": a.get("rr_excludes_1", ""),
            "sign_improved": (a.get("sign_test") or {}).get("improved", ""),
            "sign_worse": (a.get("sign_test") or {}).get("worse", ""),
        })
    write_csv("t1_offset_rule_validation.csv", val)
    dstar = rep["rule"]["delta_star"]
    rho = [r["rho"] for r in prof]
    print(f"      delta*={dstar}  rho profile=" +
          ", ".join(f"{x:.3f}" for x in rho) +
          f"  monotone_decreasing={all(rho[i] > rho[i+1] for i in range(len(rho)-1))}")
    for r in val:
        if r["arm"] != "C0":
            print(f"      {r['arm']:7s} {r['failures']}/{r['trials']} "
                  f"RR={float(r['rr_vs_c0']):.2f} [{float(r['rr_lo']):.2f}, "
                  f"{float(r['rr_hi']):.2f}] excludes1={r['rr_excludes_1']}")



# --------------------------------------------------------------------------
# 9. Fair modern baseline (GRAY_BGF + matched static threshold) at P1' (tier 1)
# --------------------------------------------------------------------------
def bgf_baseline() -> None:
    print("[9] fair modern baseline BGF-C3 at P1'")
    path = ROOT / "lw-vs" / "results" / "bgf_baseline" / "report.json"
    if not path.exists():
        print("  !! results/bgf_baseline/report.json missing; run exp_bgf_baseline.py")
        return
    rep = load(path)
    rows = []
    for gid in GROUP_ORDER:
        c = rep["groups"][gid]
        for arm, a in c["arms"].items():
            rows.append({
                "tier": 1, "source": "lw-vs/results/bgf_baseline",
                "point": "P1'", "r": rep["param"]["r"], "d": rep["param"]["d"],
                "t": rep["param"]["t"],
                "group": gid, "condition": c["condition"],
                "arm": arm, "n_keys": c["n_keys"],
                "errors_per_key": rep["errors_per_key"],
                "failures": a["failures"], "trials": a["trials"],
                "dfr": a["dfr"], "upper95": a["upper95"],
                "avg_iters": a["avg_iters"],
                "rr_vs_c0": a.get("rr_vs_C0", ""),
                "rr_lo": (a.get("rr_ci95") or ["", ""])[0],
                "rr_hi": (a.get("rr_ci95") or ["", ""])[1],
                "rr_excludes_1": a.get("rr_excludes_1", ""),
                "sign_improved": (a.get("sign_test") or {}).get("improved", ""),
                "sign_worse": (a.get("sign_test") or {}).get("worse", ""),
            })
    write_csv("t1_bgf_baseline.csv", rows)

    bnd = []
    for gid, c in rep.get("boundary_affine_bgf", {}).get("cells", {}).items():
        a = list(c["arms"].values())[0]
        bnd.append({
            "tier": 1, "source": "lw-vs/results/bgf_baseline",
            "note": "spec-exact affine BGF with published BIKE Level-1 constants; "
                    "mis-scaled for d=45, documented boundary not a comparator",
            "condition": c["condition"], "n_keys": c["n_keys"],
            "errors_per_key": c["errors_per_key"],
            "failures": a["failures"], "trials": a["trials"],
            "dfr": a["dfr"], "avg_iters": a["avg_iters"],
        })
    write_csv("t1_bgf_affine_boundary.csv", bnd)

    print(f"      reproducibility gate passed = {rep['reproducibility_gate_passed']}")
    for r in rows:
        if r["arm"] == "BGF-C3":
            print(f"      {r['condition']:12s} BGF-C3 {r['failures']}/{r['trials']} "
                  f"RR={float(r['rr_vs_c0']):.3f} "
                  f"[{float(r['rr_lo']):.3f}, {float(r['rr_hi']):.3f}] "
                  f"excl1={r['rr_excludes_1']} iters={float(r['avg_iters']):.3f}")



# --------------------------------------------------------------------------
# 10. Deployment-level cost in the C reference (tier 1)
# --------------------------------------------------------------------------
def c_cost() -> None:
    print("[10] C reference deployment cost")
    path = ROOT / "lw-vs" / "results" / "c_cost" / "c_cost_report.json"
    if not path.exists():
        print("  !! results/c_cost/c_cost_report.json missing; run exp_c_cost.py")
        return
    rep = load(path)
    rows = []
    for name, b in rep["builds"].items():
        rows.append({
            "tier": 1, "source": "lw-vs/results/c_cost",
            "build": name, "note": b["note"],
            "r": rep["protocol"]["parameter"]["r"],
            "d": rep["protocol"]["parameter"]["d"],
            "t": rep["protocol"]["parameter"]["t"],
            "max_iter": rep["protocol"]["max_iter"],
            "decodes": b["decodes"],
            "decodes_per_second": b["decodes_per_second"],
            "mean_iters": b["mean_iters"], "p50_iters": b["p50_iters"],
            "p95_iters": b["p95_iters"], "p99_iters": b["p99_iters"],
            "p99_is_at_least_budget": b["p99_is_at_least_budget"],
            "over_max_iter": b["over_max_iter"],
            "budget_exhaustion_fraction": b["max_iter_reached_fraction"],
            "dfr_dynamic_semantics": b["dfr_dynamic_semantics"],
            "best_wall_seconds": b["best_wall_seconds"],
        })
    write_csv("t1_c_cost.csv", rows)
    rel = rep.get("relative_cost_FRO2_over_C0", {})
    write_csv("t1_c_cost_relative.csv", [{
        "tier": 1, "source": "lw-vs/results/c_cost",
        "comparison": "FRO-2 / C0",
        "iteration_cost_ratio": rel.get("iteration_cost_ratio"),
        "wall_cost_ratio": rel.get("wall_cost_ratio"),
        "throughput_ratio": rel.get("throughput_ratio"),
        "p99_iteration_delta": rel.get("p99_iteration_delta"),
        "semantics": rep["protocol"]["semantics"],
    }])
    for r in rows:
        print(f"      {r['build']:6s} {r['decodes_per_second']:7.0f} dec/s  "
              f"mean_iters={float(r['mean_iters']):.3f}  p99={r['p99_iters']}  "
              f"over={100*float(r['budget_exhaustion_fraction']):.2f}%")
    print(f"      FRO-2/C0: iterations x{rel.get('iteration_cost_ratio'):.3f}  "
          f"throughput x{rel.get('throughput_ratio'):.3f}")



# --------------------------------------------------------------------------
# 11. Near-codeword-aware decoder (Baldelli et al. 2026 Alg. 2), matched (tier 1)
# --------------------------------------------------------------------------
def ncw_aware() -> None:
    print("[11] near-codeword-aware decoder")
    path = ROOT / "lw-vs" / "results" / "ncw_aware" / "report.json"
    if not path.exists():
        print("  !! results/ncw_aware/report.json missing; run exp_ncw_aware.py")
        return
    rep = load(path)
    rows = []
    for gid, c in rep["groups"].items():
        rows.append({
            "tier": 1, "source": "lw-vs/results/ncw_aware", "phase": "P1prime",
            "condition": c["condition"], "kappa": 12, "n_keys": c["n_keys"],
            "trials": c["trials"],
            "c0_failures": c["c0_failures"], "c0_archived": c["c0_archived"],
            "c0_exact_recovery_failures": c["c0_exact_recovery_failures"],
            "ncw_zero_syndrome": c["ncw_zero_syndrome"],
            "ncw_zero_syndrome_dfr": c["ncw_zero_syndrome_dfr"],
            "ncw_exact_recovery_failures": c["ncw_exact_recovery_failures"],
            "ncw_exact_recovery_dfr": c["ncw_exact_recovery_dfr"],
            "ncw_miscorrections": c["ncw_miscorrections"],
            "ncw_triggered": c["ncw_triggered"],
            "ncw_trigger_rate": c["ncw_trigger_rate"],
            "ncw_avg_iters": c["ncw_avg_iters"],
        })
    write_csv("t1_ncw_aware_p1p.csv", rows)

    cap = []
    for cons, c in rep.get("capture", {}).get("cells", {}).items():
        cap.append({
            "tier": 1, "source": "lw-vs/results/ncw_aware", "phase": "capture",
            "construction": cons, "kappa": c["kappa"], "trials": c["trials"],
            "c0_failures": c["c0_failures"], "c0_dfr": c["c0_dfr"],
            "c0_exact_recovery_failures": c["c0_exact_recovery_failures"],
            "ncw_zero_syndrome": c["ncw_zero_syndrome"],
            "ncw_zero_syndrome_dfr": c["ncw_zero_syndrome_dfr"],
            "ncw_exact_recovery_failures": c["ncw_exact_recovery_failures"],
            "ncw_exact_recovery_dfr": c["ncw_exact_recovery_dfr"],
            "ncw_triggered": c["ncw_triggered"],
            "ncw_trigger_rate": c["ncw_trigger_rate"],
        })
    write_csv("t1_ncw_aware_capture.csv", cap)
    print(f"      gate={rep['gate_passed']}  P1' cells: NCW step fired "
          f"{sum(int(r['ncw_triggered']) for r in rows)} times total")
    for r in cap:
        print(f"      kappa={int(r['kappa']):3d}  C0 {100*float(r['c0_dfr']):6.2f}%  ->  "
              f"NCW-aware {100*float(r['ncw_zero_syndrome_dfr']):6.2f}%  "
              f"(exact-recovery fail {100*float(r['ncw_exact_recovery_dfr']):6.2f}%, "
              f"fired {100*float(r['ncw_trigger_rate']):5.1f}%)")



# --------------------------------------------------------------------------
# 12. Round controls: round-2-onwards and first-round-negative arms (tier 1)
# --------------------------------------------------------------------------
def round_controls() -> None:
    print("[12] round controls (missing temporal arms)")
    path = ROOT / "lw-vs" / "results" / "round_controls" / "phase1_round_controls.json"
    if not path.exists():
        print("  !! results/round_controls/phase1_round_controls.json missing")
        return
    rep = load(path)
    rows = []
    for gid, c in rep["groups"].items():
        for n, a in c["arms"].items():
            row = {
                "tier": 1, "source": "lw-vs/results/round_controls",
                "condition": c["condition"], "arm": n,
                "offsets": json.dumps(rep["arms"][n]["offsets"]),
                "note": rep["arms"][n]["note"],
                "n_keys": c["n_keys"], "trials": c["trials"],
                "failures": a["failures"], "dfr": a["dfr"],
                "upper95": a["upper95"],
            }
            # every row must carry the same keys: write_csv takes its header from rows[0],
            # so a C0 row without these fields would silently drop the columns
            if "rr_vs_C0" in a:
                row.update({
                    "rr_vs_c0": a["rr_vs_C0"],
                    "rr_lo": a["rr_ci95"][0], "rr_hi": a["rr_ci95"][1],
                    "rr_excludes_1": a["rr_excludes_1"],
                    "keys_improved": a["sign_test"]["improved"],
                    "keys_worse": a["sign_test"]["worse"],
                    "keys_tied": a["sign_test"]["tied"],
                    "sign_p": a["sign_test"]["p_two_sided"],
                })
            else:
                row.update({"rr_vs_c0": "", "rr_lo": "", "rr_hi": "",
                            "rr_excludes_1": "", "keys_improved": "",
                            "keys_worse": "", "keys_tied": "", "sign_p": ""})
            rows.append(row)
    write_csv("t1_round_controls.csv", rows)
    print(f"      gate={rep['gate_passed']}")
    for r in rows:
        if r["arm"] in ("R2plus", "FRONEG"):
            print(f"      {r['condition']:12s} {r['arm']:7s} {r['failures']:6d}/{r['trials']} "
                  f"RR={float(r['rr_vs_c0']):.4f} "
                  f"improved={r['keys_improved']} worse={r['keys_worse']}")


# --------------------------------------------------------------------------
# 13. P1' local offset scan: +/-1..3 and -2 at the primary point (2026-10-18)
# --------------------------------------------------------------------------
def offset_scan_p1p() -> None:
    print("[13] P1' local offset scan (FRO-1/2/3, FRONEG, FRONEG2)")
    path = ROOT / "lw-vs" / "results" / "offset_scan_p1p" / "phase1_round_controls.json"
    if not path.exists():
        print("  !! results/offset_scan_p1p/phase1_round_controls.json missing")
        return
    rep = load(path)
    rows = []
    for gid, c in rep["groups"].items():
        for n, a in c["arms"].items():
            row = {
                "tier": 1, "source": "lw-vs/results/offset_scan_p1p",
                "condition": c["condition"], "arm": n,
                "offsets": json.dumps(rep["arms"][n]["offsets"]),
                "note": rep["arms"][n]["note"],
                "n_keys": c["n_keys"], "trials": c["trials"],
                "failures": a["failures"], "dfr": a["dfr"],
                "upper95": a["upper95"],
            }
            if "rr_vs_C0" in a:
                row.update({
                    "rr_vs_c0": a["rr_vs_C0"],
                    "rr_lo": a["rr_ci95"][0], "rr_hi": a["rr_ci95"][1],
                    "rr_excludes_1": a["rr_excludes_1"],
                    "keys_improved": a["sign_test"]["improved"],
                    "keys_worse": a["sign_test"]["worse"],
                    "keys_tied": a["sign_test"]["tied"],
                    "sign_p": a["sign_test"]["p_two_sided"],
                })
            else:
                row.update({"rr_vs_c0": "", "rr_lo": "", "rr_hi": "",
                            "rr_excludes_1": "", "keys_improved": "",
                            "keys_worse": "", "keys_tied": "", "sign_p": ""})
            rows.append(row)
    write_csv("t1_offset_scan_p1p.csv", rows)
    print(f"      gate={rep['gate_passed']}")
    for r in rows:
        if r["arm"] != "C0":
            print(f"      {r['condition']:12s} {r['arm']:8s} {r['failures']:6d}/{r['trials']} "
                  f"RR={float(r['rr_vs_c0']):.4g} "
                  f"[{float(r['rr_lo']):.4g}, {float(r['rr_hi']):.4g}]")



# --------------------------------------------------------------------------
# 13. Operating-point robustness: t-sensitivity and larger-r replication (tier 1)
# --------------------------------------------------------------------------
def robustness() -> None:
    print("[13] operating-point robustness")
    base = ROOT / "lw-vs" / "results" / "round_controls"
    ts = base / "phase2_t_sensitivity.json"
    if ts.exists():
        rep = load(ts)
        rows = []
        for t, c in rep["cells"].items():
            rows.append({
                "tier": 1, "source": "lw-vs/results/round_controls/phase2",
                "r": rep["r"], "d": rep["d"], "t": c["t"],
                "t_over_r": c["t_over_r"], "n_keys": rep["n_keys"],
                "errors_per_key": rep["errors_per_key"], "trials": c["trials"],
                "c0_failures": c["c0_failures"], "c0_dfr": c["c0_dfr"],
                "c0_upper95": c["c0_upper95"],
                "fro2_failures": c["fro2_failures"], "fro2_dfr": c["fro2_dfr"],
                "rr": c["rr"] if c["rr"] is not None else "",
                "rr_lo": (c["rr_ci95"] or ["", ""])[0] or "",
                "rr_hi": (c["rr_ci95"] or ["", ""])[1] or "",
                "rr_excludes_1": c["rr_excludes_1"] if c["rr"] is not None else "",
            })
        write_csv("t1_t_sensitivity.csv", rows)
        res = [r for r in rows if r["rr"] != "" and bool(r["rr_excludes_1"])]
        vals = [float(r["rr"]) for r in res]
        print(f"      t-sweep: {len(res)}/{len(rows)} cells resolved; "
              + (f"RR {min(vals):.2f}--{max(vals):.2f}" if vals else "none resolved"))

    p3 = base / "phase3_parameter_sweep.json"
    if p3.exists():
        rep = load(p3)
        rows = []
        for pid, pt in rep["points"].items():
            for t, c in pt["cells"].items():
                rows.append({
                    "tier": 3, "source": "lw-vs/results/round_controls/phase3",
                    "point_id": pid, "note": pt["note"],
                    "r": pt["r"], "d": pt["d"], "t": c["t"],
                    "t_over_r": c["t_over_r"], "n_keys": rep["n_keys"],
                    "errors_per_key": rep["errors_per_key"], "trials": c["trials"],
                    "c0_failures": c["c0_failures"], "c0_dfr": c["c0_dfr"],
                    "fro2_failures": c["fro2_failures"], "fro2_dfr": c["fro2_dfr"],
                    "rr": c["rr"] if c.get("rr") is not None else "",
                    "in_measurable_band": int(1e-4 <= c["c0_dfr"] <= 1e-2),
                })
        write_csv("t3_parameter_sweep.csv", rows)
        below = sum(1 for r in rows if r["c0_dfr"] < 1e-4)
        above = sum(1 for r in rows if r["c0_dfr"] > 1e-2)
        ins = sum(1 for r in rows if r["in_measurable_band"])
        print(f"      phase-3 sweep: {len(rows)} cells = {below} below band + "
              f"{ins} inside + {above} above")

    big = base / "phase4_larger_r.json"
    if big.exists():
        rep = load(big)
        rows = []
        for t, c in rep.get("cells", {}).items():
            rows.append({
                "tier": 1, "source": "lw-vs/results/round_controls/phase4",
                "r": rep["r"], "d": rep["d"], "t": c["t"],
                "t_over_r": c["t_over_r"], "n_keys": c["n_keys"],
                "errors_per_key": rep.get("errors_per_key", ""), "trials": c["trials"],
                "c0_failures": c["c0_failures"], "c0_dfr": c["c0_dfr"],
                "fro2_failures": c["fro2_failures"], "fro2_dfr": c["fro2_dfr"],
                "rr": c["rr"], "rr_lo": c["rr_ci95"][0], "rr_hi": c["rr_ci95"][1],
                "rr_excludes_1": c["rr_excludes_1"],
                "note": "largest r in the study; density d/r matches P1' but t/r is lower",
            })
        write_csv("t1_larger_r.csv", rows)
        for r in rows:
            print(f"      larger r: (r={r['r']},d={r['d']},t={r['t']}) "
                  f"C0={float(r['c0_dfr']):.3e} RR={float(r['rr']):.3f} "
                  f"[{float(r['rr_lo']):.3f}, {float(r['rr_hi']):.3f}]")



def main() -> int:
    print(f"root = {ROOT}")
    print(f"out  = {OUT}\n")
    formal_main()
    mechanism()
    expanded()
    scope()
    modern()
    prototypes()
    recovery()
    offset_rule()
    bgf_baseline()
    c_cost()
    ncw_aware()
    round_controls()
    offset_scan_p1p()
    robustness()
    print(f"\nwrote {len(_written)} tables to lw-vs/data/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
