#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verify that numbers quoted in the lw-vs manuscripts match the exported archives.

For every claim we recompute the expected value from lw-vs/data/*.csv (itself
exported from the frozen experiment archives by export_data.py) and check that
the manuscript renders it. A number retyped by hand into LaTeX is exactly the
kind of thing that silently drifts, so this is a hard gate, not a report.

Run:  python lw-vs/scripts/verify_numbers.py      (exit 0 = all checks pass)
"""
from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "lw-vs" / "data"
EN = ROOT / "lw-vs" / "v3" / "en" / "main.tex"
ZH = ROOT / "lw-vs" / "v3" / "zh" / "main.tex"

FAILURES: list[str] = []
CHECKS = 0


def load(name):
    with open(DATA / name, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(v):
    return float(v)


def normalize(s: str) -> str:
    """Collapse LaTeX spacing so substring tests are robust."""
    s = s.replace("{,}", ",").replace("\\,", "").replace("~", " ")
    s = re.sub(r"\\times\s*10\^", "E", s)
    s = re.sub(r"E\{(-?[0-9]+)\}", r"E\1", s)   # 7.40\times10^{-4} -> 7.40E-4
    s = re.sub(r"\\text\{([^}]*)\}", r"\1", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s


EN_TXT = normalize(EN.read_text(encoding="utf-8"))
ZH_TXT = normalize(ZH.read_text(encoding="utf-8"))


NUM_RE = re.compile(
    r"([0-9]*\.?[0-9]+)E(-?[0-9]+)"                    # normalized \times10^{n}
    r"|([0-9]{1,3}(?:,[0-9]{3})+(?:\.?[0-9]+)?)"          # thousands-separated
    r"|([0-9]*\.?[0-9]+)")                              # plain decimal


def numbers_in(txt: str) -> set[float]:
    """Every number appearing in the manuscript, parsed to a float.

    Handles both the plain decimal form and the \times10^{n} form, which
    normalize() has already rewritten to <mantissa>E<exp>.
    """
    vals: set[float] = set()
    for m in NUM_RE.finditer(txt):
        try:
            if m.group(2) is not None:
                vals.add(float(m.group(1)) * 10 ** int(m.group(2)))
            elif m.group(3) is not None:
                vals.add(float(m.group(3).replace(",", "")))
            else:
                vals.add(float(m.group(4)))
        except (ValueError, OverflowError):
            pass
    return vals


EN_NUMS = numbers_in(EN_TXT)
ZH_NUMS = numbers_in(ZH_TXT)
print(f"parsed {len(EN_NUMS)} distinct numeric tokens (en), "
      f"{len(ZH_NUMS)} (zh)\n")


def has_value(nums: set[float], v: float, tol: float = 6e-3) -> bool:
    """True if the manuscript quotes v to within `tol` relative error
    (6e-3 accommodates the 3-significant-digit convention used throughout)."""
    if v == 0:
        return 0.0 in nums
    return any(abs(n - v) <= tol * abs(v) for n in nums)


def check_value(label: str, v: float, where: str = "both", sig: int = 3) -> None:
    global CHECKS
    CHECKS += 1
    tol = 6e-3 if sig >= 3 else 10 ** -(sig - 1)
    targets = []
    if where in ("both", "en"):
        targets.append(("en", EN_NUMS))
    if where in ("both", "zh"):
        targets.append(("zh", ZH_NUMS))
    for tag, nums in targets:
        if not has_value(nums, v, tol):
            FAILURES.append(f"[{tag}] {label}: {v!r} not found in any rendering")


def check_value_both(label: str, v: float, sig: int = 3) -> None:
    check_value(label, v, "en", sig)
    check_value(label, v, "zh", sig)


def check_str(label: str, needle: str, where: str = "both") -> None:
    global CHECKS
    CHECKS += 1
    needle = normalize(needle)
    targets = []
    if where in ("both", "en"):
        targets.append(("en", EN_TXT))
    if where in ("both", "zh"):
        targets.append(("zh", ZH_TXT))
    for tag, txt in targets:
        if needle not in txt:
            FAILURES.append(f"[{tag}] {label}: expected to find {needle!r}")


def check_absent(label: str, needle: str) -> None:
    """Guard against stale claims that a correction should have removed."""
    global CHECKS
    CHECKS += 1
    needle = normalize(needle)
    for tag, txt in (("en", EN_TXT), ("zh", ZH_TXT)):
        if needle in txt:
            FAILURES.append(f"[{tag}] {label}: stale text still present: {needle!r}")


def ratio(c0: float, arm: float) -> float:
    return c0 / arm


# ---------------------------------------------------------------------------
def check_formal() -> None:
    print("[1] primary formal comparison")
    rows = {r["condition"]: r for r in load("t1_formal_main.csv")}
    for cond, r in rows.items():
        c0f, c0t = int(r["c0_failures"]), int(r["c0_trials"])
        f2f, f2t = int(r["fro2_failures"]), int(r["fro2_trials"])
        tag = f"formal {cond}"
        check_str(f"{tag} C0 counts", f"{c0f}/{c0t:,}".replace(",", "{,}"))
        check_str(f"{tag} FRO-2 counts", f"{f2f}/{f2t:,}".replace(",", "{,}"))
        check_value_both(f"{tag} RR", f(r["rr"]), sig=3)
        check_value_both(f"{tag} C0 DFR", f(r["c0_dfr"]))
        check_value_both(f"{tag} FRO-2 DFR", f(r["fro2_dfr"]))
        check_value_both(f"{tag} RR lower CI", f(r["rr_lo"]), sig=3)
        check_value_both(f"{tag} RR upper CI", f(r["rr_hi"]), sig=3)
        print(f"  {cond:12s} C0={c0f}/{c0t} FRO-2={f2f}/{f2t} RR={f(r['rr']):.2f}")

    pk = load("t1_per_key.csv")
    win = sum(1 for r in pk if int(r["fro2_failures"]) < int(r["c0_failures"]))
    lose = sum(1 for r in pk if int(r["fro2_failures"]) > int(r["c0_failures"]))
    tie = len(pk) - win - lose
    for label, v in (("keys favouring FRO-2", win), ("keys favouring C0", lose),
                     ("tied keys", tie), ("total keys", len(pk))):
        check_value_both(f"per-key {label}", float(v), sig=4)
    print(f"  per-key: FRO-2 better={win} C0 better={lose} tie={tie} total={len(pk)}")

    gate = {r["scope"]: r for r in load("t1_gate_fresh.csv")}
    pf = f(gate["pure_fresh_test_keys"]["improvement_log10"])
    full = f(gate["full_formal"]["improvement_log10"])
    check_value_both("pure-fresh gate improvement", pf)
    check_value_both("full-pool improvement", full)
    check_value_both("fresh key count", float(gate["pure_fresh_test_keys"]["total_keys"]),
                     sig=4)
    print(f"  gate: pure-fresh={pf:.3f} full-pool={full:.3f}")

    rec = load("t1_exact_recovery.csv")
    tot = {}
    for r in rec:
        tot[r["arm"]] = tot.get(r["arm"], 0) + int(r["exact_recovery_failures"])
    check_value_both("C0 exact-recovery failures", float(tot["C0"]), sig=4)
    check_value_both("FRO-2 exact-recovery failures", float(tot["FRO-2"]), sig=4)
    print(f"  exact recovery: C0={tot['C0']} FRO-2={tot['FRO-2']}")


def check_mechanism() -> None:
    print("[2] first-round mechanism")
    mech = load("t1_mechanism_firstround.csv")
    rand = {r["arm"]: r for r in mech if r["condition"] == "RAND"}
    inc = ratio(f(rand["C0"]["mean_incorrect_first"]), f(rand["FRO-2"]["mean_incorrect_first"]))
    cor = ratio(f(rand["C0"]["mean_correct_first"]), f(rand["FRO-2"]["mean_correct_first"]))
    # the manuscripts quote the across-condition ratios (9.5x / 2.7x)
    agg = {}
    for r in mech:
        agg.setdefault(r["arm"], []).append(r)
    mean = lambda arm, col: sum(f(r[col]) for r in agg[arm]) / len(agg[arm])
    inc_all = ratio(mean("C0", "mean_incorrect_first"), mean("FRO-2", "mean_incorrect_first"))
    cor_all = ratio(mean("C0", "mean_correct_first"), mean("FRO-2", "mean_correct_first"))
    # Match the ratio WITH its 	imes suffix. A bare "9.3" once matched an unrelated
    # TYPE-I DFR (9.333e-4) and made this check pass vacuously.
    BS = chr(92)
    check_str("RAND incorrect-flip ratio", f"${inc:.1f}" + BS + "times$")
    check_str("RAND correct-flip ratio", f"${cor:.1f}" + BS + "times$")
    check_str("RAND incorrect-flip ratio (zh)", f"${inc:.1f}" + BS + "times$", "zh")
    check_str("RAND correct-flip ratio (zh)", f"${cor:.1f}" + BS + "times$", "zh")
    print(f"  ratios: incorrect={inc_all:.2f}x correct={cor_all:.2f}x "
          f"(RAND-only: {inc:.2f}x / {cor:.2f}x)")

    # -- confirmatory failure-mode counts and the classifier equivalence --------
    modes = load("t1_failure_modes.csv")
    cmp_rows = load("t1_failure_modes_classifier_comparison.csv")
    n_cells = len(cmp_rows)
    if not all(r["identical"] == "1" for r in cmp_rows):
        FAILURES.append("classifier comparison has non-identical cells; the manuscripts "
                        "claim all 30 mode cells are identical")
    check_str("mode-cell count", str(n_cells))
    check_str("all-cells-identical claim (en)", "identical", "en")
    for cond, gid in (("RAND", "G0"), ("TYPE-I", "G2_d12"), ("NCW-shallow", "G3")):
        c0 = sum(int(r["count"]) for r in modes
                 if r["group"] == gid and r["arm"] == "C0" and r["mode"] == "stagnation")
        tot = sum(int(r["count"]) for r in modes if r["group"] == gid and r["arm"] == "C0")
        check_str(f"{cond} stagnation/C0-failures", f"{c0}/{tot}")
        print(f"  {cond:12s} stagnation {c0}/{tot} C0 failures")
    # the mechanism rerun must reproduce the archived failure totals (pipeline check)
    tr = load("t1_mechanism_transitions.csv")
    for r in tr:
        check_value_both(f"mechanism {r['condition']} C0 failures", float(r["c0_fails"]), sig=4)
        check_value_both(f"mechanism {r['condition']} FRO-2 failures", float(r["fro2_fails"]), sig=3)
    for arm, key in (("C0", "mean_total_first"), ("FRO-2", "mean_total_first"),
                     ("C0", "mean_incorrect_first"), ("FRO-2", "mean_incorrect_first")):
        pass  # figure-only values; not required in prose


def check_temporal() -> None:
    print("[3] temporal dissociation")
    piv = load("t2_temporal_pivot.csv")
    ext = load("t2_expanded_temporal.csv")
    first_rr, uni_rr, r2_rr = [], [], []
    for pt in ("P2", "P3"):
        for cond in ("RAND", "TYPE-I", "NCW-shallow"):
            cell = {r["schedule"]: r for r in piv
                    if r["point"] == pt and r["condition"] == cond}
            c0 = f(cell["C0"]["dfr"])
            check_value_both(f"temporal {pt}/{cond} C0 DFR", c0)
            for s in ("FRO-1", "FRO-2", "FRO-3"):
                rr = ratio(c0, f(cell[s]["dfr"]))
                first_rr.append(rr)
                check_value_both(f"temporal {pt}/{cond}/{s} RR", rr, sig=3)
            uni_rr.append(f(cell["UNIFORM-2"]["dfr"]))
            r2_rr.append(ratio(c0, f(cell["R2-2"]["dfr"])))
    # quoted spans
    check_str("first-round RR span (lower)", f"{min(first_rr):.2f}")
    check_str("first-round RR span (upper)", f"{max(first_rr):.2f}")
    # the revised section V-A quotes the uniform offset as a RISK-RATIO span rather
    # than an absolute DFR span; check what the text actually claims
    uni_rr_span = []
    for pt in ("P2", "P3"):
        for cond in ("RAND", "TYPE-I", "NCW-shallow"):
            cell = {r["schedule"]: r for r in piv
                    if r["point"] == pt and r["condition"] == cond}
            uni_rr_span.append(ratio(f(cell["C0"]["dfr"]), f(cell["UNIFORM-2"]["dfr"])))
    check_str("uniform RR span (lower)", f"{min(uni_rr_span):.3f}")
    check_str("uniform RR span (upper)", f"{max(uni_rr_span):.3f}")
    print(f"  uniform offset RR span {min(uni_rr_span):.3f}--{max(uni_rr_span):.3f}, "
          f"DFR {min(uni_rr):.3f}--{max(uni_rr):.3f}")
    check_str("round-2 RR span (lower)", f"{min(r2_rr):.2f}")
    check_str("round-2 RR span (upper)", f"{max(r2_rr):.2f}")
    # FRO-2 selected-schedule span, quoted as 2.37-4.62
    f2 = []
    for pt in ("P2", "P3"):
        for cond in ("RAND", "TYPE-I", "NCW-shallow"):
            cell = {r["schedule"]: r for r in piv
                    if r["point"] == pt and r["condition"] == cond}
            f2.append(ratio(f(cell["C0"]["dfr"]), f(cell["FRO-2"]["dfr"])))
    check_str("selected FRO-2 RR span (lower)", f"{min(f2):.2f}")
    check_str("selected FRO-2 RR span (upper)", f"{max(f2):.2f}")
    print(f"  first-round RR span {min(first_rr):.2f}--{max(first_rr):.2f}; "
          f"FRO-2 {min(f2):.2f}--{max(f2):.2f}; round-2 {min(r2_rr):.2f}--{max(r2_rr):.2f}")
    print(f"  uniform +2 DFR span {min(uni_rr):.3f}--{max(uni_rr):.3f}")
    # how many round-2 cells resolve
    n_r2 = sum(1 for r in ext if r["decoder"] == "R2-2"
               and (f(r["rr_lo"]) > 1 or f(r["rr_hi"]) < 1))
    n_f2 = sum(1 for r in ext if r["decoder"] == "FRO-2"
               and (f(r["rr_lo"]) > 1 or f(r["rr_hi"]) < 1))
    print(f"  cells excluding 1: FRO-2 {n_f2}/6, R2-2 {n_r2}/6")
    check_str("round-2 resolved-cell count (en)", f"four of the six cells", "en")
    check_str("round-2 resolved-cell count (zh)", "四个单元", "zh")
    check_absent("stale 'no stable benefit' claim EN", "yields no stable benefit")
    check_absent("stale 'no stable benefit' claim ZH", "无稳定收益")


def check_scope() -> None:
    print("[4] transfer, capture boundary, iteration budget")
    tr = load("t2_transfer_p2.csv")
    for r in tr:
        check_value_both(f"transfer {r['condition']} RR", f(r["rr"]), sig=3)
        check_value_both(f"transfer {r['condition']} RR lower CI", f(r["rr_lo"]), sig=3)
        check_value_both(f"transfer {r['condition']} RR upper CI", f(r["rr_hi"]), sig=3)
        check_value_both(f"transfer {r['condition']} C0 DFR", f(r["c0_dfr"]))
        check_value_both(f"transfer {r['condition']} FRO-2 DFR", f(r["fro2_dfr"]))
    cap = load("t3_capture_gradient.csv")
    for r in cap:
        k, rr = f(r["kappa"]), f(r["rr"])
        if k in (0.0, 12.0):
            check_value_both(f"capture kappa={k:g} RR", rr, sig=3)
        elif k == 46.0:
            check_value_both("capture kappa=46 RR", rr, sig=3)
            c0p = 100.0 * f(r["c0_failures"]) / f(r["c0_trials"])
            f2p = 100.0 * f(r["fro2_failures"]) / f(r["fro2_trials"])
            check_str("kappa=46 C0 failure percent", f"{c0p:.2f}")
            check_str("kappa=46 FRO-2 failure percent", f"{f2p:.2f}")
            print(f"  kappa=46: C0 fails {c0p:.2f}%, FRO-2 fails {f2p:.2f}%")
    itb = load("t3_iteration_budget.csv")
    rrs = [f(r["rr"]) for r in itb]
    check_str("budget RR span lower", f"{min(rrs):.2f}")
    check_str("budget RR span upper", f"{max(rrs):.2f}")
    if not all(r["rr_excludes_1"] == "True" for r in itb):
        FAILURES.append("some iteration-budget CI includes 1; text claims all exclude 1")
    print(f"  budget RR span {min(rrs):.2f}--{max(rrs):.2f}, all exclude 1")


def check_modern() -> None:
    print("[5] modern decoders and the production boundary")
    mod = load("t1_modern_scaled.csv")
    scale = {"RAND": "scale", "TYPE-I": "01", "NCW-shallow": "10"}
    for r in mod:
        cond = r["condition"]
        check_value_both(f"scaled {cond} C0 DFR", f(r["c0_dfr"]))
        check_value_both(f"scaled {cond} FRO-2 DFR", f(r["fro2_dfr"]))
        check_value_both(f"scaled {cond} BIKE-Flip DFR", f(r["bikeflip_dfr"]))
        print(f"  {cond:12s} C0={f(r['c0_dfr']):.4e} FRO2={f(r['fro2_dfr']):.4e} "
              f"BF={f(r['bikeflip_dfr']):.4e} p(BFvsFRO2)={f(r['bf_vs_fro2_mcnemar_p']):.3f}")
    rand_p = f(next(r for r in mod if r["condition"] == "RAND")["bf_vs_fro2_mcnemar_p"])
    check_str("RAND BIKE-Flip-vs-FRO-2 p", f"{rand_p:.2f}")

    hold = {r["path"]: r["value"] for r in load("t1_native_l1_holdout_flat.csv")}
    for cond in ("RAND", "TYPE-I", "NCW"):
        for off in (0, 2, 4):
            v = f(hold[f"two_round_convergence_percent/offset_{off}/{cond}"])
            check_value_both(f"L1 convergence offset{off} {cond}", v)
    print("  L1 two-round convergence quoted for all three conditions at all offsets")


def check_engineering() -> None:
    """Section V-L: engineering comparison.

    Presence-conditional (2026-10-11): the STLR/SR-NCW block moved to the archive in
    the optimized manuscripts (cost paragraph merged into V-K); the original
    manuscripts keep it.
    """
    print("[6] engineering comparison")
    if "STLR" not in EN_TXT and "STLR" not in ZH_TXT:
        print("  (engineering block moved to the archive; skipped)")
        return
    rows = load("t4_engineering_cells.csv")
    want = {
        ("P2", "RAND"): (35, 14, 12, 12, 34),
        ("P2", "TYPE-I"): (36, 24, 23, 23, 64),
        ("P2", "NCW-shallow"): (19, 9, 8, 8, 13),
        ("P3", "RAND"): (19, 13, 11, 11, 22),
        ("P3", "TYPE-I"): (25, 9, 9, 9, 24),
        ("P3", "NCW-shallow"): (7, 1, 1, 1, 4),
    }
    order = ["C0", "FRO-2", "STLR", "SR-NCW", "BGF-C3"]
    for (pt, cond), expect in want.items():
        got = []
        for m in order:
            r = next((r for r in rows if r["point"] == pt and r["condition"] == cond
                      and r["method"] == m), None)
            got.append(int(r["failures"]) if r else -1)
        if got != list(expect):
            FAILURES.append(f"engineering {pt}/{cond}: archive={got} expected={list(expect)}")
        for m, n in zip(order, got):
            if n >= 0:
                check_str(f"eng {pt}/{cond}/{m}", f"{n}/15{{,}}000")
    print(f"  {len(want)} cells cross-checked against the archive")

    pw = load("t4_engineering_pairwise.csv")
    for comp, expect_sig in (("C0/FRO-2", 4), ("C0/BGF-C3", 1),
                             ("FRO-2/STLR", 0), ("FRO-2/SR-NCW", 0)):
        sub = [r for r in pw if r["comparison"] == comp]
        if not sub:
            FAILURES.append(f"pairwise: no rows for {comp}")
            continue
        sig = sum(1 for r in sub if f(r["rr_lo"]) > 1 or f(r["rr_hi"]) < 1)
        if sig != expect_sig:
            FAILURES.append(f"pairwise {comp}: archive says {sig}/6 exclude 1, "
                            f"expected {expect_sig}/6")
        print(f"  pairwise {comp}: {sig}/{len(sub)} cells exclude 1")
        if expect_sig == 0:
            check_str(f"pairwise {comp} zero-count claim", "0/6")



def check_offset_rule() -> None:
    """Section V-E: the prespecified rule and its held-out validation at P4.

    Presence-conditional (2026-10-11): the rule's full block was pruned to a single
    archived pointer paragraph in the optimized manuscripts; the original ones keep
    it, so the block runs only when the rho profile is still in the text.
    """
    print("[7] prespecified offset rule at P4")
    if "decreases monotonically over" not in EN_TXT and "单调递减" not in ZH_TXT:
        print("  (manuscripts carry only the archived pointer; block skipped)")
        return
    prof = load("t1_offset_rule_profile.csv")
    val = {r["arm"]: r for r in load("t1_offset_rule_validation.csv")}
    rho = [f(r["rho"]) for r in prof]
    mono = all(rho[i] > rho[i + 1] for i in range(len(rho) - 1))
    if not mono:
        FAILURES.append("rho is not monotone decreasing; the manuscript claims it is")
    for r in prof:
        check_value_both(f"rule rho delta={r['delta']}", f(r["rho"]))
    # the manuscript states the criterion selects the smallest offset in range
    check_str("rule selection claim (en)", "decreases monotonically over", "en")
    check_str("rule selection claim (zh)", "单调递减", "zh")
    pt = prof[0]
    for label, v in (("P4 r", float(pt["r"])), ("P4 d", float(pt["d"])),
                     ("P4 t", float(pt["t"]))):
        check_str(label, f"{int(v)}")
    print(f"  rho = {', '.join(f'{x:.3f}' for x in rho)}  monotone={mono}")

    for arm, a in val.items():
        check_str(f"{arm} failures/trials", f"{int(a['failures'])}/{int(a['trials']):,}".replace(",", "{,}"))
        check_value_both(f"{arm} DFR", f(a["dfr"]))
        if arm != "C0":
            check_value_both(f"{arm} RR vs C0", f(a["rr_vs_c0"]), sig=3)
            check_value_both(f"{arm} RR lower CI", f(a["rr_lo"]), sig=3)
            check_value_both(f"{arm} RR upper CI", f(a["rr_hi"]), sig=3)
            check_str(f"{arm} CI excludes 1", "excluding one", "en")
            print(f"  {arm:7s} {int(a['failures'])}/{int(a['trials'])} "
                  f"RR={f(a['rr_vs_c0']):.2f} [{f(a['rr_lo']):.2f}, {f(a['rr_hi']):.2f}]")
    check_str("validation key count", str(int(val["C0"]["n_keys"])))
    check_str("development key count", "12 development keys", "en")
    check_str("development key count (zh)", "12 把开发密钥", "zh")



def check_bgf_baseline() -> None:
    """Section V-G: fair structural BGF-C3 at P1' and the affine-constant boundary."""
    print("[8] fair modern baseline BGF-C3 at P1'")
    rows = load("t1_bgf_baseline.csv")
    bnd = load("t1_bgf_affine_boundary.csv")
    c0_iters = {"RAND": 4.312, "TYPE-I": 4.511, "NCW-shallow": 4.206}
    for r in rows:
        if r["arm"] != "BGF-C3":
            continue
        cond = r["condition"]
        # the manuscript reports all four arms as one combined cell, e.g. 282 / 68 / 83 / 287
        c0f = next(int(x["failures"]) for x in rows
                   if x["condition"] == cond and x["arm"] == "C0")
        f2f = next(int(x["failures"]) for x in rows
                   if x["condition"] == cond and x["arm"] == "FRO-2")
        bff = int(next(x for x in load("t1_modern_scaled.csv")
                       if x["condition"] == cond)["bikeflip_failures"])
        check_str(f"BGF-C3 {cond} combined failure cell",
                  f"{c0f} / {f2f} / {bff} / {int(r['failures'])}")
        check_value_both(f"BGF-C3 {cond} RR", f(r["rr_vs_c0"]), sig=3)
        check_value_both(f"BGF-C3 {cond} RR lower", f(r["rr_lo"]), sig=3)
        check_value_both(f"BGF-C3 {cond} RR upper", f(r["rr_hi"]), sig=3)
        check_value_both(f"BGF-C3 {cond} mean iters", f(r["avg_iters"]), sig=3)
        check_value_both(f"C0 {cond} mean iters", c0_iters[cond], sig=3)
        print(f"  {cond:12s} BGF-C3 {int(r['failures']):4d}/{int(r['trials'])} "
              f"RR={f(r['rr_vs_c0']):.3f} [{f(r['rr_lo']):.3f}, {f(r['rr_hi']):.3f}] "
              f"excl1={r['rr_excludes_1']} iters={f(r['avg_iters']):.3f}")
    n_ok = sum(1 for r in rows if r["arm"] == "BGF-C3" and r["rr_excludes_1"] == "False")
    if n_ok != 2:
        FAILURES.append(f"expected 2 BGF-C3 cells unresolved vs C0, data shows {n_ok}")
    check_str("BGF-C3 unresolved-cell claim (en)", "indistinguishable from C0", "en")
    check_str("BGF-C3 unresolved-cell claim (zh)", "统计不可分辨", "zh")
    # iteration-cost ratio quoted as ~22%
    its = [f(r["avg_iters"]) for r in rows if r["arm"] == "BGF-C3"]
    base = [c0_iters[r["condition"]] for r in rows if r["arm"] == "BGF-C3"]
    ratios = [a / b for a, b in zip(its, base)]
    check_str("BGF-C3 iteration cost ratio", f"{100 * (sum(ratios) / len(ratios) - 1):.0f}")

    # affine boundary: quoted as a 38-60% failure range
    dfrs = [100 * f(r["dfr"]) for r in bnd]
    lo, hi = round(min(dfrs)), round(max(dfrs))
    check_str("affine boundary lower", f"{lo}")
    check_str("affine boundary upper", f"{hi}")
    print(f"  affine boundary DFR range {min(dfrs):.1f}--{max(dfrs):.1f}% "
          f"(text quotes {lo}--{hi}%)")



def check_c_cost() -> None:
    """Section V-H: deployment-level cost measured in the C reference."""
    print("[9] C reference deployment cost")
    rows = {r["build"]: r for r in load("t1_c_cost.csv")}
    rel = load("t1_c_cost_relative.csv")[0]
    for name in ("C0", "FRO-2", "BGF"):
        r = rows.get(name)
        if r is None:
            FAILURES.append(f"c_cost: missing build {name}")
            continue
        # only C0 and FRO-2 throughputs are quoted in the prose; BGF's is not
        if name in ("C0", "FRO-2"):
            check_value_both(f"{name} throughput", float(r["decodes_per_second"]), sig=4)
        check_value_both(f"{name} mean iters", float(r["mean_iters"]), sig=3)
        check_str(f"{name} p99 iters", str(int(r["p99_iters"])))
        print(f"  {name:6s} {float(r['decodes_per_second']):7.0f} dec/s  "
              f"mean_iters={float(r['mean_iters']):.3f}  p99={r['p99_iters']}")
    for k, label in (("iteration_cost_ratio", "iteration cost ratio"),
                     ("throughput_ratio", "throughput ratio")):
        v = float(rel[k])
        check_value_both(f"FRO-2/C0 {label}", v, sig=3)
        print(f"  FRO-2/C0 {label}: {v:.3f}")
    # the manuscript quotes the cost as a 7-9% band
    lo = round(100 * (float(rel["iteration_cost_ratio"]) - 1))
    hi = round(100 * (float(rel["throughput_ratio"]) - 1))
    check_str("cost band (en)", f"{lo}--{hi}\%", "en")
    check_str("cost band (zh)", f"{lo}--{hi}\%", "zh")
    # BGF budget-exhaustion fraction quoted as 47.9%
    frac = 100 * float(rows["BGF"]["budget_exhaustion_fraction"])
    check_str("BGF budget exhaustion", f"{frac:.1f}")



def check_ncw_aware() -> None:
    """Section V-F: near-codeword-aware decoder, inert at P1' and decisive at kappa>d."""
    print("[10] near-codeword-aware decoder")
    rows = load("t1_ncw_aware_p1p.csv")
    cap = {int(r["kappa"]): r for r in load("t1_ncw_aware_capture.csv")}
    # P1': the step must be completely inert and reproduce C0 exactly
    fired = sum(int(r["ncw_triggered"]) for r in rows)
    if fired != 0:
        FAILURES.append(f"NCW step fired {fired} times at P1'; text claims it never fires")
    seq = " / ".join(str(int(r["c0_failures"])) for r in rows)
    check_str("NCW-aware reproduces C0 failure sequence", seq)
    for r in rows:
        check_value_both(f"NCW-aware {r['condition']} mean iters",
                         float(r["ncw_avg_iters"]), sig=3)
    print(f"  P1': step fired {fired} times across all cells (text claims 0)")

    # only kappa=46 quotes both arms' rates; kappa=60 quotes the NCW success only
    check_value_both("kappa=46 C0 DFR pct", 100 * float(cap[46]["c0_dfr"]), sig=3)
    check_value_both("kappa=46 NCW exact-recovery failure pct",
                     100 * float(cap[46]["ncw_exact_recovery_dfr"]), sig=3)
    for k in (46, 60):
        print(f"  kappa={k}: C0 fails {100*float(cap[k]['c0_dfr']):.2f}%, "
              f"NCW-aware fails {100*float(cap[k]['ncw_exact_recovery_dfr']):.2f}%")
    check_value_both("kappa=46 trigger rate pct",
                     100 * float(cap[46]["ncw_trigger_rate"]), sig=3)
    check_value_both("kappa=60 zero-syndrome success pct",
                     100 * float(cap[60]["ncw_zero_syndrome_dfr"]), sig=3)
    # no miscorrection in any cell: zero-syndrome count equals exact-recovery count
    for k, r in cap.items():
        zs, n, ex = int(r["ncw_zero_syndrome"]), int(r["trials"]),             int(r["ncw_exact_recovery_failures"])
        if zs != n - ex:
            FAILURES.append(f"kappa={k}: zero-syndrome {zs} != exact-recovery {n-ex}; "
                            f"text claims no miscorrection was observed")



def check_pso() -> None:
    """Section II-D: the PSO threshold-selection citation (same (4801,45) point).

    Presence-conditional: the original manuscripts do not cite kichna2025pso, so the
    block is skipped for them. Values are from the PSO paper's summary table
    (JIAS 20(2), 2025, pp. 58-73; verified against the local PDF on 2026-10-10).
    """
    global CHECKS
    print("[16] PSO threshold selection (related work)")
    if "kichna2025pso" not in EN_TXT and "kichna2025pso" not in ZH_TXT:
        print("  (manuscripts do not cite kichna2025pso; block skipped)")
        return
    check_str("PSO citation (en)", "kichna2025pso", "en")
    check_str("PSO citation (zh)", "kichna2025pso", "zh")
    check_value_both("PSO baseline mean iterations", 5.36, sig=3)
    check_value_both("PSO method mean iterations", 3.01, sig=3)


def check_fair_l1() -> None:
    """Section V-K: the design-B fair comparison at the production block parameters.

    Presence-conditional on the inserted paragraph's sentinel phrase. Claims are
    exported by export_fair_l1.py from results/fair_l1/report.json (pipeline gate:
    C0 94 / FRO-2 21 / FRONEG 582 of 48,000 reproduced exactly, 2026-10-10).
    """
    global CHECKS
    print("[17] fair comparison at the production code parameters (design B)")
    if ("specification-conforming BIKE-Flip" not in EN_TXT
            and "规范一致的 BIKE-Flip" not in ZH_TXT):
        print("  (manuscripts do not contain the fair-comparison paragraph; skipped)")
        return
    rows = load("t1_fair_l1.csv")
    for r in rows:
        check_value_both(f"fair-L1 {r['label']}", f(r["value"]), sig=int(r["sig"]))
    print(f"  {len(rows)} claims checked from t1_fair_l1.csv")


def check_cpa128() -> None:
    """Section V-K: the CPA-128 proximity measurement (closest to production weight).

    Presence-conditional on the paragraph's sentinel. Claims exported by
    export_cpa128.py from results/cpa128_window + results/cpa128_scan (2026-10-10).
    """
    global CHECKS
    print("[18] CPA-128 proximity window (production-adjacent preset)")
    if "CPA-128" not in EN_TXT and "CPA-128" not in ZH_TXT:
        print("  (manuscripts do not contain the CPA-128 paragraph; skipped)")
        return
    rows = load("t1_cpa128.csv")
    for r in rows:
        check_value_both(f"CPA-128 {r['label']}", f(r["value"]), sig=int(r["sig"]))
    print(f"  {len(rows)} claims checked from t1_cpa128.csv")


def check_source_bytes() -> None:
    """Guard against lone CR bytes in the manuscript sources.

    Motivation (2026-10-10): both optimized manuscripts once contained a literal
    carriage return where "\\ref" was intended (an escape handler ate the two
    characters "\\r"). read_text()'s universal-newline translation hides lone CRs,
    so this check must read raw bytes. Any lone CR in a .tex source is a defect.
    """
    global CHECKS
    print("[11b] source bytes (lone CR guard)")
    for tag, path in (("en", EN), ("zh", ZH)):
        CHECKS += 1
        raw = path.read_bytes()
        lone = raw.count(b"\r") - raw.count(b"\r\n")
        if lone:
            FAILURES.append(f"[{tag}] {path.name} contains {lone} lone CR byte(s); "
                            f"an escape sequence was likely corrupted")
        else:
            print(f"  {tag}: 0 lone CR bytes")


def check_pdf_output() -> None:
    """Verify the COMPILED PDFs, not just the sources.

    Motivation: two blocking defects once survived every source-level check -- a stray
    double-backslash-percent in the Chinese manuscript commented out 171 characters of a
    paragraph, and a split \ref printed the literal string "effig:temporal" in the body.
    Both are invisible in the .tex and only appear after compilation, so the pipeline must
    inspect the build output.
    """
    print("[11] compiled PDF output")
    import fitz
    try:
        docs = {}
        for tag, path in (("en", EN.parent / "main.pdf"), ("zh", ZH.parent / "main.pdf")):
            if not path.exists():
                FAILURES.append(f"[{tag}] PDF not built: {path.name}")
                continue
            docs[tag] = "".join(pg.get_text() for pg in fitz.open(path))
    except ImportError:
        print("  (PyMuPDF unavailable; skipping PDF-level checks)")
        return
    if not docs:
        return

    for tag, txt in docs.items():
        # 1) no broken cross-references rendered as literal text.
        #    "efsec" added 2026-10-10: a "\ref" whose "\r" had been turned into a
        #    literal carriage return by an escape handler rendered as
        #    "Section efsec:background" and slipped past the earlier sentinel list.
        for bad in ("effig", "eftab", "ef{fig", "ef{tab}", "efsec", "??"):
            if bad in txt:
                FAILURES.append(f"[{tag}] PDF contains broken cross-reference text {bad!r}")
        # 2) no LaTeX markup leaked into the body
        for bad in ("\\", "\%", "\emph", "\cite"):
            if bad in txt:
                FAILURES.append(f"[{tag}] PDF contains raw LaTeX markup {bad!r}")
        print(f"  {tag}: {len(txt)} chars, no broken refs or leaked markup")

    # 3) sentinel numbers from each new experiment must actually appear in BOTH PDFs,
    #    which is what catches content silently commented out during compilation
    sentinels = ["11.07", "74.2", "0.76", "4.29", "19.67", "1.067", "0.687", "0.679", "85.31"]
    for tag, txt in docs.items():
        missing = [x for x in sentinels if x not in txt]
        if missing:
            FAILURES.append(f"[{tag}] PDF is missing sentinel values {missing} -- "
                            f"content was probably dropped at compile time")
        else:
            print(f"  {tag}: all {len(sentinels)} sentinel values present in the PDF")

    # 4) the two PDFs must agree on the same sentinel set
    if len(docs) == 2:
        a = {x for x in sentinels if x in docs["en"]}
        b = {x for x in sentinels if x in docs["zh"]}
        if a != b:
            FAILURES.append(f"EN/ZH PDFs disagree on sentinels: en-only={a-b}, zh-only={b-a}")



def check_round_controls() -> None:
    """Section V-A: the two-sided first round and the cost of sustained offsets."""
    print("[12] round controls at P1'")
    rows = load("t1_round_controls.csv")
    by = {(r["condition"], r["arm"]): r for r in rows}
    for cond in ("RAND", "TYPE-I", "NCW-shallow"):
        for arm in ("FRO-2", "FRONEG", "R2plus", "R2one"):
            r = by.get((cond, arm))
            if r is None:
                FAILURES.append(f"round_controls: missing {cond}/{arm}")
                continue
            # absolute DFRs are quoted for RAND only; the other two conditions are
            # reported as risk ratios
            if arm in ("FRONEG", "R2plus"):
                if cond == "RAND":
                    check_value_both(f"{cond} {arm} DFR", float(r["dfr"]))
                check_value_both(f"{cond} {arm} RR", float(r["rr_vs_c0"]), sig=3)
            # unanimous key-level direction is the strongest form of the claim
            # unanimous key-level direction is claimed only for the two destructive arms
            if arm in ("FRONEG", "R2plus") and int(r["keys_worse"]) != int(r["n_keys"]):
                FAILURES.append(f"{cond}/{arm}: keys_worse {r['keys_worse']} != n_keys "
                                f"{r['n_keys']}; text claims every key is worse")
        print(f"  {cond:12s} FRONEG RR={float(by[(cond,'FRONEG')]['rr_vs_c0']):.4f} "
              f"R2plus RR={float(by[(cond,'R2plus')]['rr_vs_c0']):.4f} (both 0 keys improved) | "
              f"R2one RR={float(by[(cond,'R2one')]['rr_vs_c0']):.3f} "
              f"(excludes1={by[(cond,'R2one')]['rr_excludes_1']})")
    # the same-pool contrast: one-shot round-2 helps, sustained round-2 destroys
    for cond in ("RAND", "TYPE-I", "NCW-shallow"):
        one = float(by[(cond, "R2one")]["rr_vs_c0"])
        sus = float(by[(cond, "R2plus")]["rr_vs_c0"])
        if not (one > 1 > sus):
            FAILURES.append(f"{cond}: one-shot {one:.3f} and sustained {sus:.3f} are not on "
                            f"opposite sides of unity as the text claims")
        if by[(cond, "R2one")]["rr_excludes_1"] != "True":
            FAILURES.append(f"{cond}: one-shot round-2 interval does not exclude 1")
    check_str("one-shot round-2 span lower", "1.21")
    check_str("one-shot round-2 span upper", "1.45")
    r = by[("RAND", "FRO-2")]
    check_value_both("RAND FRO-2 RR (round controls)", float(r["rr_vs_c0"]), sig=3)
    check_value_both("RAND FRONEG RR lower", float(by[("RAND","FRONEG")]["rr_lo"]), sig=3)
    check_value_both("RAND FRONEG RR upper", float(by[("RAND","FRONEG")]["rr_hi"]), sig=4)
    check_str("FRONEG 8-fold claim (en)", "eightfold", "en")
    check_str("FRONEG 8-fold claim (zh)", "八倍", "zh")
    # the "60-fold" statement for R2plus in RAND is 0.0608 / 0.00102
    ratio = float(by[("RAND","R2plus")]["dfr"]) / float(by[("RAND","C0")]["dfr"])
    check_str("R2plus fold-change claim", f"{ratio:.0f}")



def check_robustness() -> None:
    """Section V-D: t-sensitivity and the larger-r replication."""
    print("[13] operating-point robustness")
    ts = {int(r["t"]): r for r in load("t1_t_sensitivity.csv")}
    for t, r in sorted(ts.items()):
        if r["rr"] == "":
            continue
        # only the risk ratios are quoted for the t-sweep, not the absolute C0 DFRs
        check_value_both(f"t={t} RR", float(r["rr"]), sig=3)
        print(f"  t={t}: C0 DFR={float(r['c0_dfr']):.3e} RR={float(r['rr']):.3f} "
              f"[{float(r['rr_lo']):.3f}, {float(r['rr_hi']):.3f}]")
    resolved = [r for r in ts.values() if r["rr"] != ""]
    if len(resolved) != 3:
        FAILURES.append(f"t-sweep: expected 3 resolved cells, found {len(resolved)}")
    # the monotone-shrink claim
    rrs = [float(r["rr"]) for r in sorted(resolved, key=lambda x: int(x["t"]))]
    if rrs != sorted(rrs, reverse=True):
        FAILURES.append(f"t-sweep RRs are not monotone decreasing: {rrs}")

    lr = load("t1_larger_r.csv")[0]
    check_value_both("larger-r RR", float(lr["rr"]), sig=3)
    check_value_both("larger-r RR lower", float(lr["rr_lo"]), sig=3)
    check_value_both("larger-r RR upper", float(lr["rr_hi"]), sig=3)
    check_value_both("larger-r C0 DFR", float(lr["c0_dfr"]))
    check_value_both("larger-r FRO-2 DFR", float(lr["fro2_dfr"]))
    check_str("larger-r r value", str(int(lr["r"])))
    print(f"  larger r: (r={int(lr['r'])},d={int(lr['d'])},t={int(lr['t'])}) "
          f"RR={float(lr['rr']):.3f}")



def check_parameter_sweep() -> None:
    """Section V-D: the full phase-3 sweep, including the cells that missed the band.

    This check exists because an earlier draft mis-stated the miss counts ("three below,
    one above") from memory; the archive says six and six. The counts are now derived
    from the data rather than restated.
    """
    print("[14] parameter sweep (including misses)")
    rows = load("t3_parameter_sweep.csv")
    below = [r for r in rows if float(r["c0_dfr"]) < 1e-4]
    above = [r for r in rows if float(r["c0_dfr"]) > 1e-2]
    inside = [r for r in rows if 1e-4 <= float(r["c0_dfr"]) <= 1e-2]
    check_str("sweep cell count", str(len(rows)))
    check_str("cells below the band", str(len(below)))
    check_str("cells above the band", str(len(above)))
    print(f"  {len(rows)} cells: {len(below)} below, {len(inside)} inside, {len(above)} above")
    # the three resolvable cells and their monotone decay
    # The manuscript quotes the three Q2 cells (d=45, t=98/102/106), where C0 failure is
    # high enough for a meaningful ratio but not total. Other cells can also yield a
    # finite risk ratio (e.g. 1.000 when both arms fail everywhere), so we do not count
    # "resolvable" cells; we verify exactly the cells the text quotes.
    quoted = [r for r in rows if r["rr"] != "" and int(r["t"]) in (98, 102, 106)
              and int(r["d"]) == 45]
    if len(quoted) != 3:
        FAILURES.append(f"sweep: expected the 3 quoted Q2 cells, found {len(quoted)}")
    for r in sorted(quoted, key=lambda x: int(x["t"])):
        check_value_both(f"sweep t={r['t']} RR", float(r["rr"]), sig=3)
        print(f"    (r={r['r']},d={r['d']},t={r['t']}) C0 DFR={float(r['c0_dfr']):.3f} "
              f"RR={float(r['rr']):.3f}")
    rrs = [float(r["rr"]) for r in sorted(quoted, key=lambda x: int(x["t"]))]
    if rrs != sorted(rrs, reverse=True):
        FAILURES.append(f"sweep RRs do not decay monotonically toward unity: {rrs}")


def check_tier_upgrade() -> None:
    """Section VI-H..I and the discussion: the 2026-10-07 tier-upgrade results.

    These claims exist only in the optimised manuscript (lw-vs/optimized/).
    The gate is presence-conditional: if the production-parameter section is
    absent from the manuscript being checked, the block is skipped with a note
    rather than failing, so that the original manuscript still passes.
    """
    global CHECKS
    print("[15] tier-upgrade results (production parameters, low DFR, model failure)")
    p = DATA / "t5_tier_upgrade.csv"
    if not p.exists():
        print("  (t5_tier_upgrade.csv absent; skipped)"); return
    en_has = any(s in EN_TXT for s in ("production code parameters", "The production code parameters"))
    zh_has = "生产码参数" in ZH_TXT
    if not (en_has or zh_has):
        print("  (manuscript does not contain the tier-upgrade section; "
              f"{sum(1 for _ in open(p, encoding='utf-8-sig')) - 1} checks skipped)")
        return
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    n_ok = 0
    for r in rows:
        check_value_both(f"tier-upgrade {r['label']}", f(r["value"]), sig=int(r["sig"]))
        n_ok += 1
    add = [x for x in FAILURES if x.startswith("[") and "tier-upgrade" in x]
    print(f"  {n_ok} claims checked from {p.name}; "
          f"{len(add)} failure(s) so far in this block")


def main() -> int:
    global EN, ZH, EN_TXT, ZH_TXT, EN_NUMS, ZH_NUMS
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--en", default=str(EN), help="path to the English manuscript")
    ap.add_argument("--zh", default=str(ZH), help="path to the Chinese manuscript")
    a = ap.parse_args()
    if Path(a.en) != EN or Path(a.zh) != ZH:
        EN, ZH = Path(a.en), Path(a.zh)
        EN_TXT = normalize(EN.read_text(encoding="utf-8"))
        ZH_TXT = normalize(ZH.read_text(encoding="utf-8"))
        EN_NUMS = numbers_in(EN_TXT)
        ZH_NUMS = numbers_in(ZH_TXT)
    print(f"verifying {EN.name} and {ZH.name} against {DATA}\n")
    check_formal(); print()
    check_mechanism(); print()
    check_temporal(); print()
    check_scope(); print()
    check_modern(); print()
    check_engineering(); print()
    check_offset_rule(); print()
    check_bgf_baseline(); print()
    check_c_cost(); print()
    check_ncw_aware(); print()
    check_round_controls(); print()
    check_robustness(); print()
    check_parameter_sweep(); print()
    check_tier_upgrade(); print()
    check_pso(); print()
    check_fair_l1(); print()
    check_cpa128(); print()
    check_source_bytes(); print()
    check_pdf_output(); print()
    print(f"ran {CHECKS} checks")
    if FAILURES:
        print(f"\n{len(FAILURES)} FAILURE(S):")
        for x in FAILURES:
            print("  -", x)
        return 1
    print("PASS: every numeric claim matches the exported archives")
    return 0


if __name__ == "__main__":
    sys.exit(main())
