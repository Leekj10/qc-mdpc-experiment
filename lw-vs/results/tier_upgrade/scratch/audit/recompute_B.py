#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Auditor A part 2: remaining checks (CI overlap, calibration ratios, staleness)."""
import json, os, math
from pathlib import Path

ROOT = Path("d:/桌面/TOUGAO - c")
TU = ROOT / "lw-vs" / "results" / "tier_upgrade"

# --- CI overlap: tsweep t=92 vs main pool t=92 (and t=90) ---
ts_lo, ts_hi = 3.6363636363636362, 23.5
m92 = (3.2891194916652915, 5.381888111888111)
m90 = (2.6875, 5.565217391304347)
print("tsweep[3.64,23.5] vs main t=92 [3.29,5.38]: overlap =",
      max(ts_lo, m92[0]) < min(ts_hi, m92[1]), "-> overlap region",
      [max(ts_lo, m92[0]), min(ts_hi, m92[1])])
print("tsweep vs main t=90 [2.69,5.57]: overlap =", max(ts_lo, m90[0]) < min(ts_hi, m90[1]))
print("tsweep point 7.00 inside main t=92 CI?", m92[0] <= 7.0 <= m92[1])

# --- calibration table ratios ---
cal = json.load(open(TU / "p1pp_calibration.json", encoding="utf-8"))
for c in cal["candidates"]:
    print(f"t={c['t']:3d} t/r={c['t']/12323:.7f} doc5={c['t']/12323:.5f} trials={c['trials']} "
          f"fails={c['c0_failures']} dfr={c['c0_dfr']:.6e}")
print("rule of three 3/1200 =", 3/1200)
for b in cal["bisection"]:
    print("bisection", b["t"], b["c0_failures"], b["c0_dfr"])

# --- ratio claims ---
print("14x check: 1.0217391304347826e-3/7.065217391304347e-05 =",
      1.0217391304347826e-3/7.065217391304347e-05)
print("1.7x check: 7.0/4.15 =", 7.0/4.15)
print("6x check: 1/0.16151202749140892 =", 1/0.16151202749140892)
print("28% via t*=172: (172-134)/134 =", (172-134)/134)
print("27% via t=170: (170-134)/134 =", (170-134)/134)
print("15% window: (195-170)/170 =", (195-170)/170)
print("1199/1200 =", 1199/1200)

# --- L1a tau at delta=3 ---
l1a = json.load(open(TU / "l1a_firstround_margin.json", encoding="utf-8"))
print("L1a mean tau(+3) =", l1a["per_delta"]["3"]["tau_sum"]/l1a["trials"],
      "(doc annotation says upper clip 45)")

# --- '1.6x' factor hunt ---
cv = 0.29958900782987746
sig = math.sqrt(math.log(1+cv*cv))
print("exp(1.645*sigma_log) =", math.exp(1.645*sig), " exp(sigma_log) =", math.exp(sig),
      " (1+cv)/(1-cv) =", (1+cv)/(1-cv))

# --- phase_T90 vs state consistency + stale-artifact check ---
st = json.load(open(TU / "state_T90.json", encoding="utf-8"))
ph = json.load(open(TU / "phase_T90.json", encoding="utf-8"))
print("phase per_key_c0 == state C0:", ph["per_key_c0"] == st["arms"]["C0"])
print("phase per_key_fro2 == state FRO-2:", ph["per_key_fro2"] == st["arms"]["FRO-2"])
for f in ["REPORT.md", "paper_patch_draft.md", "phase_T90.json", "state_T90.json"]:
    print(f, os.path.getmtime(TU / f))

# --- T90 intermediate rows: verify internal arithmetic consistency of doc values ---
rows = [(4000, 22, 7, 3.14, 1.63, 8.67), (8000, 51, 16, 3.19, 1.81, 7.22),
        (12000, 68, 24, 2.83, 1.83, 5.00), (16000, 98, 31, 3.16, 2.22, 5.00),
        (20000, 130, 35, 3.71, 2.69, 5.57)]
for e, c0f, f2f, rr, lo, hi in rows:
    trials = 92*e
    print(f"E={e:6d} trials={trials:8d} C0dfr={c0f/trials:.3e} RR={c0f/f2f:.4f} (doc {rr})")

# --- archive 2.82/1.87/2.407 (not quoted in docs; verify anyway) ---
ph2 = json.load(open(ROOT / "lw-vs/results/round_controls/phase2_t_sensitivity.json", encoding="utf-8"))
print("phase2 t94 rr =", ph2["cells"]["94"]["rr"], " t96 rr =", ph2["cells"]["96"]["rr"])
ph4 = json.load(open(ROOT / "lw-vs/results/round_controls/phase4_larger_r.json", encoding="utf-8"))
print("phase4 t100 rr =", ph4["cells"]["100"]["rr"])

# --- docs mention check for 2.82/1.87/2.407 ---
for f in ("REPORT.md", "paper_patch_draft.md"):
    t = (TU / f).read_text(encoding="utf-8")
    for s in ("2.82", "1.87", "2.407", "2.4074"):
        if s in t:
            print(f"{f} contains {s}")
print("done B")
