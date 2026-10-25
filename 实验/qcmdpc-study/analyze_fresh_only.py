"""Pure-fresh-key verification of the formal M5 gate (review round-2, P0-1 / DA-CRITICAL-1).

Motivation
----------
The formal decision run (formal_m5.py) evaluates keys with fresh_from = 8 (G0/G3)
and 6 (G2). Those indices are provably disjoint from the M4 SEARCH (0-5 / 0-3) and
the S4 CONFIRMATION (6-7 / 4-5). However, the interim gate runs
(gate_h2_formal.py: G0/G3 idx 8-19, G2 idx 6-14; gate_h2_extended.py: G0/G3 idx
8-31, G2 idx 6-23) evaluated a subset of the same keys that the formal run reuses.
The interim result (Delta=0.504) informed the decision to proceed to the formal run.

This script isolates the keys that NO interim run ever touched:
    G0/G3 : pool index >= 32   (per_key position >= 24, since fresh_from = 8)
    G2    : pool index >= 24   (per_key position >= 18, since fresh_from = 6)
and recomputes the pre-registered gate statistic on that clean subset. Because the
archive stores per-key failure counts (not per-sample discordant pairs) the exact
McNemar cannot be subset; we instead report the cluster-robust per-key exact sign
test, which is the more appropriate key-level inference anyway (review R1-M1.3).

This is a ROBUSTNESS/Subgroup analysis of the SAME pre-registered gate metric on a
cleaner key subset. It adds evidence; it changes no decision rule, no parameter, no
metric definition, and no headline number.

Also recomputes the condition-gradient z with the CORRECT conditional-binomial
variance (review P0-4): the descriptive poisson_z in verify_stats.py used sqrt(e1)
(unconditional) instead of sqrt(e1*(1-p)); the corrected z is larger in magnitude,
so all prior gradient conclusions were conservative and remain unchanged.

Output: results/m5_formal/fresh_only_verification.json
Usage : python analyze_fresh_only.py [path/to/m5_formal/report.json]
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qcmdpc.stats import wilson_upper  # same frozen Wilson/rule-of-three as the gate

REPORT = sys.argv[1] if len(sys.argv) > 1 else "results/m5_formal/report.json"
OUT = os.path.join(os.path.dirname(REPORT), "fresh_only_verification.json")

E_PER_KEY = 3000

# pool index at which each group's keys become "never touched by any interim run"
#   G0/G3: interim (formal+extended) used pool idx 8..31  -> pure-fresh idx >= 32
#   G2   : interim used pool idx 6..23                    -> pure-fresh idx >= 24
# per_key_failures[i] corresponds to pool index (fresh_from + i), fresh_from = 8/6/8.
PURE_FRESH_POS = {"G0": 32 - 8, "G2_d12": 24 - 6, "G3": 32 - 8}  # = 24 / 18 / 24


def sign_test_paired(a, b):
    """Exact two-sided binomial sign test on per-key paired counts (a=base, b=C4)."""
    imp = sum(1 for x, y in zip(a, b) if y < x)
    wor = sum(1 for x, y in zip(a, b) if y > x)
    tie = sum(1 for x, y in zip(a, b) if y == x)
    n = imp + wor
    if n == 0:
        return {"improved": imp, "worse": wor, "tied": tie, "n_discordant": 0, "p_two_sided": 1.0}
    k = min(imp, wor)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return {"improved": imp, "worse": wor, "tied": tie, "n_discordant": n,
            "p_two_sided": min(1.0, 2 * tail)}


def cond_poisson_z(f1, n1, f2, n2):
    """Two-sample Poisson rate test, CONDITIONAL on the total (correct variance).

    Under H0 (equal rates), f1 | (f1+f2) ~ Binomial(f1+f2, p=n1/(n1+n2));
    Var = tot*p*(1-p). The buggy descriptive version used Var = e1 = tot*p,
    which understates |z| by 1/sqrt(1-p) (~1.41x for n1~n2). Corrected here.
    """
    tot = f1 + f2
    if tot == 0:
        return float("nan"), float("nan")
    p = n1 / (n1 + n2)
    e1 = tot * p
    var = tot * p * (1.0 - p)
    z = (f1 - e1) / math.sqrt(var)
    ratio = (f1 / n1) / (f2 / n2) if f2 > 0 else float("inf")
    return ratio, z


def slice_stats(per_key, start):
    counts = per_key[start:]
    fails = int(sum(counts))
    n_keys = len(counts)
    trials = n_keys * E_PER_KEY
    u = wilson_upper(fails, trials)
    return {"n_keys": n_keys, "failures": fails, "trials": trials,
            "dfr": fails / max(1, trials), "upper95": u,
            "log10_upper95": float(math.log10(u)) if u > 0 else None,
            "per_key_failures": counts}


def main():
    rep = json.load(open(REPORT, encoding="utf-8"))
    groups = rep["groups"]
    out = {"source": REPORT, "E_per_key": E_PER_KEY,
           "pure_fresh_start_pos": PURE_FRESH_POS, "groups": {}}

    print("== pure-fresh-key verification (never touched by any interim gate) ==")
    for gid, start in PURE_FRESH_POS.items():
        g = groups[gid]
        base = slice_stats(g["C0_base"]["per_key_failures"], start)
        c4 = slice_stats(g["C4_first_p2"]["per_key_failures"], start)
        sign = sign_test_paired(base["per_key_failures"], c4["per_key_failures"])
        # aggregate rate ratio base/C4 on the clean subset
        ratio = (base["dfr"] / c4["dfr"]) if c4["dfr"] > 0 else float("inf")
        out["groups"][gid] = {"C0_base": base, "C4_first_p2": c4,
                              "improvement_ratio": ratio, "per_key_sign_test": sign}
        print(f"[{gid}] fresh keys idx>=({start}+fresh_from): {base['n_keys']} keys, "
              f"{base['trials']} samples/arm")
        print(f"      C0 {base['failures']}/{base['trials']} = {base['dfr']:.3e} "
              f"(log10U={base['log10_upper95']:+.4f})")
        print(f"      C4 {c4['failures']}/{c4['trials']} = {c4['dfr']:.3e} "
              f"(log10U={c4['log10_upper95']:+.4f})  ratio={ratio:.2f}x")
        print(f"      sign test: imp/wor/tie = {sign['improved']}/{sign['worse']}/{sign['tied']} "
              f"p={sign['p_two_sided']:.2e}")

    # ---- pre-registered gate on the pure-fresh subset ----
    j_base = max(out["groups"][g]["C0_base"]["log10_upper95"] for g in PURE_FRESH_POS)
    j_c4 = max(out["groups"][g]["C4_first_p2"]["log10_upper95"] for g in PURE_FRESH_POS)
    worst_gid_base = max(PURE_FRESH_POS, key=lambda g: out["groups"][g]["C0_base"]["log10_upper95"])
    worst_gid_c4 = max(PURE_FRESH_POS, key=lambda g: out["groups"][g]["C4_first_p2"]["log10_upper95"])
    delta = j_base - j_c4
    g0 = out["groups"]["G0"]
    delta_rand = g0["C0_base"]["log10_upper95"] - g0["C4_first_p2"]["log10_upper95"]
    noninfer = g0["C4_first_p2"]["upper95"] <= 1.2 * g0["C0_base"]["upper95"]
    gate_pass = bool(delta >= 0.5 and noninfer)

    out["gate_pure_fresh"] = {
        "worst_group_log10U_base": j_base, "worst_group_base_gid": worst_gid_base,
        "worst_group_log10U_c4": j_c4, "worst_group_c4_gid": worst_gid_c4,
        "improvement_log10": delta, "gate_improvement_ge_0.5": bool(delta >= 0.5),
        "rand_only_improvement_log10": delta_rand, "rand_noninferior": bool(noninfer),
        "gate_pass": gate_pass,
        "total_fresh_samples_per_arm": sum(out["groups"][g]["C0_base"]["trials"] for g in PURE_FRESH_POS),
        "total_fresh_keys": sum(out["groups"][g]["C0_base"]["n_keys"] for g in PURE_FRESH_POS),
    }
    print("\n-- pre-registered gate on PURE-FRESH keys only --")
    print(f"worst-group log10U: base {j_base:+.4f} ({worst_gid_base}) -> "
          f"C4 {j_c4:+.4f} ({worst_gid_c4})")
    print(f"Delta = {delta:.4f}  (gate >= 0.5: {delta >= 0.5})")
    print(f"RAND-only Delta = {delta_rand:.4f}  (>= 0.5: {delta_rand >= 0.5}); "
          f"RAND non-inferior: {noninfer}")
    print(f"GATE_PASS (pure-fresh) = {gate_pass}")
    print(f"clean subset: {out['gate_pure_fresh']['total_fresh_keys']} keys, "
          f"{out['gate_pure_fresh']['total_fresh_samples_per_arm']} samples/arm")

    # ---- corrected condition-gradient z (P0-4), full formal + pure-fresh ----
    grads = {}
    for label, sl in [("full_formal", 0), ("pure_fresh", None)]:
        gg = {}
        for gid in ["G2_d12", "G3"]:
            if sl is None:
                start = PURE_FRESH_POS[gid]; g0s = PURE_FRESH_POS["G0"]
                f1 = out["groups"][gid]["C0_base"]["failures"]; n1 = out["groups"][gid]["C0_base"]["trials"]
                f2 = out["groups"]["G0"]["C0_base"]["failures"]; n2 = out["groups"]["G0"]["C0_base"]["trials"]
            else:
                f1 = groups[gid]["C0_base"]["failures"]; n1 = groups[gid]["C0_base"]["trials"]
                f2 = groups["G0"]["C0_base"]["failures"]; n2 = groups["G0"]["C0_base"]["trials"]
            rr, z = cond_poisson_z(f1, n1, f2, n2)
            gg[f"{gid}_vs_G0"] = {"rate_ratio": rr, "z_corrected": z}
        grads[label] = gg
    out["base_gradient_corrected"] = grads
    print("\n-- corrected conditional-Poisson gradient z (base arm, vs RAND) --")
    for label, gg in grads.items():
        for k, v in gg.items():
            print(f"[{label}] {k}: rate ratio={v['rate_ratio']:.3f}  z={v['z_corrected']:+.3f}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("\nsaved ->", OUT)


if __name__ == "__main__":
    main()
