# -*- coding: utf-8 -*-
"""Auditor D: protocol-compliance spot verification (read-only).

Checks:
 1. S1 gate "bit-exact" claim: archive per_key arrays vs surrogate_S1 per_key arrays.
 2. T90 final state: sums, chunk structure, cap; recompute wilson upper,
    cluster bootstrap CI and sign test with the frozen stats module.
 3. T90 report claims: nonzero-key count (72), intermediate checkpoints absence.
 4. P1PP calibration arithmetic (1200-trial bookkeeping, band membership).
 5. P1PP main: recompute bootstrap CIs with frozen module.
 6. S7 leave-one-out grading rule re-accounting.
 7. S4 prediction cells: inside-CI / factor accounting per frozen grading.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:/桌面/TOUGAO - c")
TU = ROOT / "lw-vs" / "results" / "tier_upgrade"
STUDY = ROOT / "实验" / "qcmdpc-study"
sys.path.insert(0, str(STUDY))

from qcmdpc.stats import (wilson_upper, cluster_bootstrap_paired,  # noqa: E402
                          sign_test_paired)

failures = []


def report(name, ok, detail=""):
    tag = "OK  " if ok else "FAIL"
    print(f"[{tag}] {name} {detail}")
    if not ok:
        failures.append((name, detail))


# ---------------------------------------------------------------- 1. S1 gate
arch = json.load(open(ROOT / "lw-vs" / "results" / "round_controls" /
                      "phase1_round_controls.json", encoding="utf-8"))
s1 = json.load(open(TU / "surrogate_S1.json", encoding="utf-8"))
for arm in ("C0", "FRO-2", "FRONEG"):
    a = arch["groups"]["G0"]["arms"][arm]["per_key_failures"]
    b = s1["arms"][arm]["per_key"]
    report(f"S1 gate per-key equality {arm}", list(a) == list(b),
           f"arch_sum={sum(a)} s1_sum={sum(b)}")

# ---------------------------------------------------------------- 2. T90
st = json.load(open(TU / "state_T90.json", encoding="utf-8"))
ph = json.load(open(TU / "phase_T90.json", encoding="utf-8"))
per0 = np.array(st["arms"]["C0"], dtype=np.int64)
per2 = np.array(st["arms"]["FRO-2"], dtype=np.int64)
e = st["errors_done"]
report("T90 n_keys=92, errors_done=20000", len(per0) == 92 and e == 20000,
       f"n={len(per0)} e={e}")
report("T90 chunk structure all 4000",
       all(c["hi"] - c["lo"] == 4000 for c in st["chunks"]) and
       st["chunks"][0]["lo"] == 0 and st["chunks"][-1]["hi"] == 20000 and
       len(st["chunks"]) == 5, str(st["chunks"]))
report("T90 cap respected (20000 <= 100000)", e <= 100000)
report("T90 target reached (130 >= 120)", int(per0.sum()) == 130 and 130 >= 120,
       f"c0={int(per0.sum())}")
report("T90 FRO-2 total 35", int(per2.sum()) == 35, f"fro2={int(per2.sum())}")
trials = 92 * e
w = wilson_upper(int(per0.sum()), trials)
report("T90 wilson_upper matches", abs(w - ph["c0_upper95"]) < 1e-15,
       f"recomputed {w} vs file {ph['c0_upper95']}")
boot = cluster_bootstrap_paired(per0, per2, e, B=10000, seed=20260905)
rr = boot["point"]["risk_ratio"]
ci = boot["ci"]["risk_ratio"]
report("T90 bootstrap RR matches", abs(rr - ph["rr"]) < 1e-9 and
       abs(ci[0] - ph["rr_ci95"][0]) < 1e-9 and abs(ci[1] - ph["rr_ci95"][1]) < 1e-9,
       f"recomputed {rr} {ci} vs file {ph['rr']} {ph['rr_ci95']}")
sg = sign_test_paired(per0, per2)
report("T90 sign test matches",
       sg["improved"] == ph["sign_test"]["improved"] and
       sg["worse"] == ph["sign_test"]["worse"] and
       sg["tied"] == ph["sign_test"]["tied"] and
       abs(sg["p_two_sided"] - ph["sign_test"]["p_two_sided"]) < 1e-15,
       f"recomputed {sg}")

# nonzero keys
nz = int((per0 > 0).sum())
nz2 = int(((per0 > 0) | (per2 > 0)).sum())
print(f"     T90 nonzero C0 keys = {nz}; nonzero in either arm = {nz2}")
# report claims 72 keys carry the failures
report("T90 '72 keys' claim", nz == 72, f"nonzero C0 keys = {nz}")

# intermediate checkpoints traceable? search all tier_upgrade json
checkpoints = ["51", "98", "12000", "16000"]
found = []
for p in TU.glob("*.json"):
    txt = p.read_text(encoding="utf-8")
    if "736000" in txt or "1,472,000" in txt or "1472000" in txt:
        found.append(p.name)
print(f"     files containing intermediate T90 totals (736000/1472000): {found}")

# ---------------------------------------------------------------- 4. P1PP cal
cal = json.load(open(TU / "p1pp_calibration.json", encoding="utf-8"))
rows = {c["t"]: c for c in cal["candidates"]}
report("cal cand t=180: 162/1200", rows[180]["c0_failures"] == 162 and
       rows[180]["trials"] == 1200, "")
report("cal cand extension trials recorded 1200 (code L1S_E_CAL=200)",
       all(c["trials"] == 1200 for c in cal["candidates"]),
       str([(c['t'], c['trials']) for c in cal['candidates']]))
bis = {b["t"]: b for b in cal["bisection"]}
report("bisection t=175 17/1200 above band", bis[175]["c0_failures"] == 17 and
       bis[175]["trials"] == 1200 and bis[175]["c0_dfr"] > 1e-2, "")
report("bisection t=172 2/1200 in band", bis[172]["c0_failures"] == 2 and
       bis[172]["trials"] == 1200 and 1e-4 <= bis[172]["c0_dfr"] <= 1e-2, "")
report("chosen_t=172 in band true", cal["chosen_t"] == 172 and cal["in_band"] is True)
report("flawed-rule selection recorded as 150", cal["chosen_t_by_flawed_rule"] == 150)

# ---------------------------------------------------------------- 5. P1PP main
pm = json.load(open(TU / "p1pp_main.json", encoding="utf-8"))
p0 = np.array(pm["arms"]["C0"]["per_key_failures"], dtype=np.int64)
for arm in ("FRO-2", "FRONEG"):
    pa = np.array(pm["arms"][arm]["per_key_failures"], dtype=np.int64)
    b2 = cluster_bootstrap_paired(p0, pa, 1500, B=10000, seed=20260905)
    rr2 = b2["point"]["risk_ratio"]
    ci2 = b2["ci"]["risk_ratio"]
    f = pm["arms"][arm]
    okv = (abs(rr2 - f["rr"]) < 1e-9 and abs(ci2[0] - f["rr_ci95"][0]) < 1e-9 and
           abs(ci2[1] - f["rr_ci95"][1]) < 1e-9)
    report(f"P1PP main bootstrap {arm} matches", okv,
           f"recomputed {rr2:.4f} {ci2} vs file {f['rr']:.4f} {f['rr_ci95']}")
report("P1PP main params", pm["n_keys"] == 32 and pm["errors_per_key"] == 1500 and
       pm["t"] == 172)

# ---------------------------------------------------------------- 6. S7 grading
s7 = json.load(open(TU / "surrogate_S7_leaveoneout.json", encoding="utf-8"))
log15 = np.log(1.5)
inside = 0
within = 0
sign_err = 0
n = 0
for arm, f in s7["folds"].items():
    n += 1
    lo, hi = f["measured_rr_ci95"]
    if lo <= f["predicted_rr_vs_C0"] <= hi:
        inside += 1
    fac = f["predicted_rr_vs_C0"] / f["measured_rr"]
    if abs(np.log(fac)) <= log15:
        within += 1
    if (f["predicted_rr_vs_C0"] - 1) * (f["measured_rr"] - 1) < 0:
        sign_err += 1
print(f"     S7 re-account: n={n} inside_ci={inside} within_1.5x={within} sign_err={sign_err}")
g = s7["grading"]
report("S7 grading counters match re-account",
       g["n_folds"] == n and g["inside_ci"] == inside and g["within_1.5x"] == within,
       f"file {g}")
# frozen rule: FAILURE if majority outside CI or sign error in any cell
frozen_fail = (inside < (n + 1) // 2) or sign_err >= 1
report("S7 verdict FAILURE follows frozen rule", frozen_fail and g["verdict"] == "FAILURE")

# ---------------------------------------------------------------- 7. S4 cells
s4 = json.load(open(TU / "surrogate_S4_fit.json", encoding="utf-8"))
inside4 = 0
n4 = 0
sign4 = 0
for arm, f in s4["predictions"].items():
    n4 += 1
    lo, hi = f["measured_rr_ci95"]
    ins = lo <= f["predicted_rr_vs_C0"] <= hi
    inside4 += int(ins)
    if (f["predicted_rr_vs_C0"] - 1) * (f["measured_rr"] - 1) < 0:
        sign4 += 1
    print(f"     S4 cell {arm}: pred {f['predicted_rr_vs_C0']:.4f} meas {f['measured_rr']:.4f} "
          f"CI {f['measured_rr_ci95']} inside={ins}")
print(f"     S4 re-account: n={n4} inside_ci={inside4} sign_err={sign4}")
print(f"     S4 file contains explicit verdict: {'grading' in s4 or 'verdict' in s4}")

print()
print("=== SUMMARY ===")
print(f"failures: {len(failures)}")
for nm, det in failures:
    print(" -", nm, det)
