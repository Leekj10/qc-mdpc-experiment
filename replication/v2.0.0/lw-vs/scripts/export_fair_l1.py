#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export the design-B fair-comparison claims (results/fair_l1/report.json).

Produces lw-vs/data/t1_fair_l1.csv in the same tier/label/value/sig/source/note
format as the other exports. verify_numbers.check_fair_l1() (added together with
the manuscript paragraph) reads this file.

Run:  python lw-vs/scripts/export_fair_l1.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "lw-vs" / "results" / "fair_l1" / "report.json"
DST = ROOT / "lw-vs" / "data" / "t1_fair_l1.csv"

d = json.loads(SRC.read_text(encoding="utf-8"))
arms = d["arms"]
assert d["pipeline_gate_passed"], "pipeline gate not passed; refuse to export"
for nm, g in d["pipeline_gate"].items():
    assert g["ok"], f"gate mismatch on {nm}: {g}"

rows = []
SRC_TAG = "fair_l1/report.json"


def add(label, value, sig, note="", source=SRC_TAG):
    rows.append({"tier": 1, "label": label, "value": value, "sig": sig,
                 "source": source, "note": note})


# head-to-head claims (points 1-3 of the manuscript paragraph)
add("fair-L1 C0 failures", arms["C0"]["failures"], 4, "pipeline gate arm")
add("fair-L1 FRO-2 failures", arms["FRO-2"]["failures"], 4, "pipeline gate arm")
add("fair-L1 BF-official-20 failures", arms["BF-official-20"]["failures"], 4)
add("fair-L1 BF-derived-20 failures", arms["BF-derived-20"]["failures"], 4)
add("fair-L1 BGF-tangent failures", arms["BGF-tangent"]["failures"], 4)
add("fair-L1 BGF-official failure percent", 100 * arms["BGF-official"]["dfr"], 3,
    "quoted as a percentage in the text")
add("fair-L1 BF-official-7 DFR", arms["BF-official-7"]["dfr"], 3)
add("fair-L1 BF-derived-7 DFR", arms["BF-derived-7"]["dfr"], 3)
add("fair-L1 BF-official-20 vs FRO-2 McNemar p",
    arms["BF-official-20"]["vs_FRO-2"]["mcnemar"]["p"], 2)
add("fair-L1 BF-derived-20 vs FRO-2 McNemar p",
    arms["BF-derived-20"]["vs_FRO-2"]["mcnemar"]["p"], 2)
add("fair-L1 BGF-tangent vs C0 McNemar p",
    arms["BGF-tangent"]["vs_C0"]["mcnemar"]["p"], 2)
add("fair-L1 trials per arm", arms["C0"]["trials"], 4)
add("fair-L1 BF-official-20 mean iterations", arms["BF-official-20"]["mean_iters"], 3,
    "fixed-loop accounting; convergence cost is ~5.5 (see iters_hist_success)")
add("fair-L1 BF-derived-20 mean iterations", arms["BF-derived-20"]["mean_iters"], 3,
    "fixed-loop accounting; convergence cost is ~5.6 (see iters_hist_success)")

# nb20 pilot (P1', 16 keys x 2000): counts quoted in the V-J footnote.
nb = json.loads((ROOT / "实验" / "qcmdpc-study" / "results" / "cmp_bf_p1_nb20"
                 / "report.json").read_text(encoding="utf-8"))
P = "cmp_bf_p1_nb20/report.json"
g0, g2, g3 = nb["groups"]["G0"], nb["groups"]["G2_d12"], nb["groups"]["G3"]
add("nb20 pilot keys", g0["n_keys"], 4, "P1' pilot", P)
add("nb20 pilot errors per key", g0["E_per_key"], 4, "P1' pilot", P)
add("nb20 pilot RAND BIKE-Flip failures", g0["BIKE_Flip"]["failures"], 4, "", P)
add("nb20 pilot RAND FRO-2 failures", g0["C4_first_p2"]["failures"], 4, "", P)
add("nb20 pilot TYPE-I BIKE-Flip failures", g2["BIKE_Flip"]["failures"], 4, "", P)
add("nb20 pilot TYPE-I FRO-2 failures", g2["C4_first_p2"]["failures"], 4, "", P)
add("nb20 pilot NCW BIKE-Flip failures", g3["BIKE_Flip"]["failures"], 4, "", P)
add("nb20 pilot NCW FRO-2 failures", g3["C4_first_p2"]["failures"], 4, "", P)

with DST.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["tier", "label", "value", "sig", "source", "note"])
    w.writeheader()
    w.writerows(rows)
print(f"wrote {DST} ({len(rows)} claims)")
