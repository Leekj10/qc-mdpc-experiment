# -*- coding: utf-8 -*-
"""One-off: pull the archive rows needed to adjudicate v3 drafting numbers."""
import csv
from pathlib import Path

DATA = Path(r"D:/桌面/TOUGAO - c/lw-vs/data")


def rows(name, pred=None, cols=None):
    p = DATA / name
    if not p.exists():
        print(f"!! {name} missing"); return
    out = []
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        if pred is None or pred(r):
            out.append({k: r.get(k) for k in (cols or r.keys())})
    print(f"== {name} ==")
    for r in out[:8]:
        print("  ", r)


# 1) round controls: FRONEG hi, R2one/R2plus RAND failures, sign p, key split
rows("t1_round_controls.csv",
     lambda r: r.get("condition") == "RAND",
     ["condition", "arm", "failures", "trials", "rr_vs_c0", "rr_lo", "rr_hi",
      "sign_p", "improved", "worsened", "tied", "mean_iters"])

# 2) expanded confirmation cells (R2-2 intervals; uniform cells)
rows("t2_expanded_temporal.csv",
     lambda r: r.get("decoder") in ("R2-2", "UNIFORM-2"),
     ["point", "condition", "decoder", "rr_vs_c0", "rr_lo", "rr_hi"])

# 3) ncw-aware capture cells
rows("t1_ncw_aware_capture.csv")

# 4) offset-rule validation
rows("t1_offset_rule_validation.csv")

# 5) modern scaled (BIKE-Flip mcnemar; BGF cells)
rows("t1_modern_scaled.csv")

# 6) bgf baseline (affine variant? percentages)
rows("t1_bgf_baseline.csv")

# 7) cpa128 window + scan sheets
rows("t1_cpa128.csv")

# 8) c cost
rows("t1_c_cost.csv")

# 9) fair l1 (iterations 5.5 / accounted 20)
rows("t1_fair_l1.csv")
