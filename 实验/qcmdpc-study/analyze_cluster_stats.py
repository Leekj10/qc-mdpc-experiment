"""Cluster-robust statistics for the formal M5 gate (review round-3, P0-6/P0-7/P0-8).

Motivation
----------
Each key contributes E=3000 paired error draws, so the independent unit for
CROSS-KEY inference is the KEY, not the individual error sample. The archived
sample-level Wilson bound and exact McNemar are conditional on the sampled keys;
the pre-registered gate (worst-group Wilson U_0.95) is unchanged by this file.

This script adds the cluster-robust layer requested by the review, reusing ONLY
the archived per-key failure counts (no new decoding):

  1. cluster bootstrap over KEYS (B=10000, deterministic seed) for the paired
     C0-vs-FRO-2 contrast -> risk ratio (RR), DFR difference, log10(RR) with
     percentile 95% CIs, on BOTH the full formal pool and the 212-key pure-fresh
     subset;
  2. exact two-sided per-key sign tests (recomputed here from the counts);
  3. Holm-Bonferroni correction across the three condition groups for the
     sample-level McNemar p-values (full pool) and the per-key sign-test
     p-values (both pools).

Cross-key significance criterion: the 'no improvement' reference (RR=1,
diff=0, log10RR=0) lies OUTSIDE the 95% CI. Results are reported honestly even
where a CI includes the reference (e.g. a shallow-intersection control).

Outputs:
  results/m5_formal/cluster_stats.json
  results/paper_figures/T_cluster.md
  results/paper_figures/T_cluster.tex
Usage:
  python analyze_cluster_stats.py [m5_formal/report.json] [fresh_only_verification.json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.stats import cluster_bootstrap_paired, holm_adjust, sign_test_paired

REPORT = sys.argv[1] if len(sys.argv) > 1 else "results/m5_formal/report.json"
FRESH = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(REPORT), "fresh_only_verification.json")
OUT_JSON = os.path.join(os.path.dirname(REPORT), "cluster_stats.json")
OUT_TAB = "results/paper_figures"

GIDS = ["G0", "G2_d12", "G3"]
GLABEL = {"G0": "RAND", "G2_d12": "WEAK-12", "G3": "NCW-$\\cap$"}
BOOT_SEED = 20260905  # review date; deterministic, documented
B = 10000
BASE, TREAT = "C0_base", "C4_first_p2"


def _fmt(x, spec=".3e"):
    return "n/a" if x is None else format(x, spec)


def analyse_pool(groups: dict, e_per_key: int, has_mcnemar: bool) -> dict:
    """Cluster bootstrap + sign test per group; Holm across the 3 groups."""
    out = {"E_per_key": e_per_key, "groups": {}}
    for gid in GIDS:
        g = groups[gid]
        base = g[BASE]["per_key_failures"]
        treat = g[TREAT]["per_key_failures"]
        boot = cluster_bootstrap_paired(base, treat, e_per_key, B=B, seed=BOOT_SEED)
        sign = sign_test_paired(base, treat)
        entry = {"cluster_bootstrap": boot, "sign_test": sign}
        if has_mcnemar and "paired" in g:
            entry["mcnemar_exact_p"] = g["paired"]["mcnemar_exact_p"]
            entry["mcnemar_discordant"] = {"base_only": g["paired"]["c0_only"],
                                           "treat_only": g["paired"]["c4_only"],
                                           "both": g["paired"]["both"]}
        out["groups"][gid] = entry

    # Holm across the three condition groups
    holm = {}
    sign_p = [out["groups"][g]["sign_test"]["p_two_sided"] for g in GIDS]
    holm["sign_test"] = {"raw": {g: p for g, p in zip(GIDS, sign_p)},
                         "holm": {g: p for g, p in zip(GIDS, holm_adjust(sign_p))}}
    if has_mcnemar and all("mcnemar_exact_p" in out["groups"][g] for g in GIDS):
        mn_p = [out["groups"][g]["mcnemar_exact_p"] for g in GIDS]
        holm["mcnemar"] = {"raw": {g: p for g, p in zip(GIDS, mn_p)},
                           "holm": {g: p for g, p in zip(GIDS, holm_adjust(mn_p))}}
    out["holm"] = holm
    return out


def main():
    rep = json.load(open(REPORT, encoding="utf-8"))
    e_full = int(rep.get("E_per_key", 3000))
    full = analyse_pool(rep["groups"], e_full, has_mcnemar=True)

    fresh = None
    e_fresh = 3000
    if os.path.exists(FRESH):
        fr = json.load(open(FRESH, encoding="utf-8"))
        e_fresh = int(fr.get("E_per_key", 3000))
        # fresh_only_verification nests per-group C0_base/C4_first_p2 with counts
        fresh = analyse_pool(fr["groups"], e_fresh, has_mcnemar=False)
        fresh["total_fresh_keys"] = fr.get("gate_pure_fresh", {}).get("total_fresh_keys")
        fresh["gate_pure_fresh"] = fr.get("gate_pure_fresh", {})
    else:
        print(f"[warn] pure-fresh file not found: {FRESH}", flush=True)

    out = {
        "source": {"formal": REPORT, "pure_fresh": FRESH if fresh else None},
        "method": {
            "cluster_bootstrap": {"unit": "key", "B": B, "seed": BOOT_SEED, "ci": 0.95,
                                  "statistics": ["risk_ratio", "dfr_diff", "log10_risk_ratio"]},
            "sign_test": "exact two-sided binomial on per-key paired counts",
            "multiplicity": "Holm-Bonferroni across the 3 condition groups",
            "note": ("Supports the pre-registered worst-group Wilson gate; changes no "
                     "decision rule, parameter, metric definition or headline number."),
        },
        "full_formal": full,
        "pure_fresh": fresh,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    _console(out)
    os.makedirs(OUT_TAB, exist_ok=True)
    _write_tables(out)
    print("\nsaved ->", OUT_JSON)
    print("saved ->", os.path.join(OUT_TAB, "T_cluster.md"), "/", "T_cluster.tex")


def _console(out):
    for pool_name in ["full_formal", "pure_fresh"]:
        pool = out.get(pool_name)
        if not pool:
            continue
        print(f"\n== cluster-robust stats: {pool_name} (E/key={pool['E_per_key']}, B={B}, seed={BOOT_SEED}) ==")
        for gid in GIDS:
            e = pool["groups"][gid]
            cb = e["cluster_bootstrap"]
            st = e["sign_test"]
            rr = cb["point"]["risk_ratio"]
            ci = cb["ci"]["risk_ratio"]
            print(f"[{GLABEL[gid]:8s}] keys={cb['n_keys']:3d}  RR={_fmt(rr,'.2f')} "
                  f"95%CI[{_fmt(ci[0],'.2f')},{_fmt(ci[1],'.2f')}]  "
                  f"excl1={cb['rr_excludes_1']}  |  sign i/w/t={st['improved']}/{st['worse']}/{st['tied']} "
                  f"p={st['p_two_sided']:.2e}"
                  + (f"  McNemar p={e['mcnemar_exact_p']:.2e}" if "mcnemar_exact_p" in e else ""))
        for kind in ["sign_test", "mcnemar"]:
            if kind in pool["holm"]:
                h = pool["holm"][kind]
                raw = "  ".join(f"{GLABEL[g]}={h['raw'][g]:.2e}" for g in GIDS)
                adj = "  ".join(f"{GLABEL[g]}={h['holm'][g]:.2e}" for g in GIDS)
                print(f"  Holm[{kind}] raw : {raw}")
                print(f"  Holm[{kind}] adj : {adj}")


def _write_tables(out):
    md = ["# T_cluster: cluster-robust cross-key inference (C0 vs FRO-2)",
          "",
          f"Cluster bootstrap over keys (B={B}, seed={BOOT_SEED}); RR=DFR_C0/DFR_FRO-2 (>1 favours FRO-2).",
          "Cross-key significance: 95% CI excludes RR=1. Holm across the 3 condition groups.",
          ""]
    tex = ["% T_cluster: cluster-robust cross-key inference (auto-generated by analyze_cluster_stats.py)",
           "\\begin{tabular}{llrrrrr}", "\\toprule",
           "Pool & Condition & keys & RR (95\\% CI) & $\\Delta$DFR (95\\% CI) & sign $p$ (Holm) & McNemar $p$ (Holm) \\\\",
           "\\midrule"]
    for pool_name, pool_label in [("full_formal", "Full formal (278-key)"), ("pure_fresh", "Pure-fresh (212-key)")]:
        pool = out.get(pool_name)
        if not pool:
            continue
        md += [f"## {pool_label}", "",
               "| Condition | keys | RR | RR 95% CI | excl. RR=1 | DFR diff | diff 95% CI | sign i/w/t | sign p | sign p (Holm) | McNemar p | McNemar p (Holm) |",
               "|---|---:|---:|---|:--:|---:|---|---|---:|---:|---:|---:|"]
        for gid in GIDS:
            e = pool["groups"][gid]
            cb, st = e["cluster_bootstrap"], e["sign_test"]
            rr, rrc = cb["point"]["risk_ratio"], cb["ci"]["risk_ratio"]
            dfd, dfdc = cb["point"]["dfr_diff"], cb["ci"]["dfr_diff"]
            sh = pool["holm"]["sign_test"]["holm"][gid]
            mh = pool["holm"].get("mcnemar", {}).get("holm", {}).get(gid)
            mr = e.get("mcnemar_exact_p")
            md.append(f"| {GLABEL[gid]} | {cb['n_keys']} | {_fmt(rr,'.2f')}x | "
                      f"[{_fmt(rrc[0],'.2f')}, {_fmt(rrc[1],'.2f')}] | {'yes' if cb['rr_excludes_1'] else 'no'} | "
                      f"{_fmt(dfd,'.3e')} | [{_fmt(dfdc[0],'.3e')}, {_fmt(dfdc[1],'.3e')}] | "
                      f"{st['improved']}/{st['worse']}/{st['tied']} | {st['p_two_sided']:.2e} | {sh:.2e} | "
                      f"{(f'{mr:.2e}' if mr is not None else 'n/a')} | {(f'{mh:.2e}' if mh is not None else 'n/a')} |")
            rr_ci = f"{_fmt(rr,'.2f')}\\,[{_fmt(rrc[0],'.2f')},{_fmt(rrc[1],'.2f')}]"
            d_ci = f"{_fmt(dfd,'.2e')}\\,[{_fmt(dfdc[0],'.1e')},{_fmt(dfdc[1],'.1e')}]"
            tex.append(f"{pool_label.split(' (')[0]} & {GLABEL[gid]} & {cb['n_keys']} & ${rr_ci}$ & ${d_ci}$ & "
                       f"${st['p_two_sided']:.1e}$\\,(${sh:.1e}$) & "
                       f"{('$'+format(mr,'.1e')+'$\\,($'+format(mh,'.1e')+'$)' if mr is not None else '---')} \\\\")
        md.append("")
    tex += ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(OUT_TAB, "T_cluster.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    with open(os.path.join(OUT_TAB, "T_cluster.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(tex))


if __name__ == "__main__":
    main()
