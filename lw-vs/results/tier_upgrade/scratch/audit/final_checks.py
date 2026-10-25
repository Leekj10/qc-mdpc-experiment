import json, sys
from pathlib import Path
import numpy as np
ROOT = Path("d:/桌面/TOUGAO - c")
sys.path.insert(0, str(ROOT / "实验" / "qcmdpc-study"))
from qcmdpc.stats import cluster_bootstrap_paired

TU = ROOT / "lw-vs" / "results" / "tier_upgrade"
s1 = json.load(open(TU / "surrogate_S1.json", encoding="utf-8"))
arch = json.load(open(ROOT / "lw-vs/results/round_controls/phase1_round_controls.json", encoding="utf-8"))
per0 = np.array(s1["arms"]["C0"]["per_key"], dtype=np.int64)
for nm, key, ref in [("FRO-2", "FRO-2", arch["groups"]["G0"]["arms"]["FRO-2"]),
                     ("FRONEG", "FRONEG", arch["groups"]["G0"]["arms"]["FRONEG"])]:
    a = np.array(s1["arms"][nm]["per_key"], dtype=np.int64)
    boot = cluster_bootstrap_paired(per0, a, 3000, B=10000, seed=20260905)
    lo, hi = boot["ci"]["risk_ratio"]
    print(nm, "recomputed CI:", lo, hi)
    print(nm, "archive stored CI:", ref["rr_ci95"])
    print(nm, "exact equal:", lo == ref["rr_ci95"][0] and hi == ref["rr_ci95"][1])
    print(nm, "rr exact equal:", boot["point"]["risk_ratio"] == ref["rr_vs_C0"])

# REPORT pattern scan for damage-like sequences
import re
txt = open(TU / "REPORT.md", encoding="utf-8").read()
for pat in ["imes", "ext{", "rac{", chr(7), "\\t"]:
    print("REPORT contains", repr(pat), ":", pat in txt)

# where does '2.82'/'1.87'/'2.407' appear (should be nowhere in the two docs)
for f in ["REPORT.md", "paper_patch_draft.md"]:
    t = open(TU / f, encoding="utf-8").read()
    print(f, {s: (s in t) for s in ("2.82", "1.87", "2.407")})
