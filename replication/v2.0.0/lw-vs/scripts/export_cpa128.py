#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Export the CPA-128 proximity claims (results/cpa128_window/report.json + scan).

Produces lw-vs/data/t1_cpa128.csv; verify_numbers.check_cpa128() reads it.
Run:  python lw-vs/scripts/export_cpa128.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIN = ROOT / "lw-vs" / "results" / "cpa128_window" / "report.json"
SCAN = ROOT / "lw-vs" / "results" / "cpa128_scan" / "report.json"
DST = ROOT / "lw-vs" / "data" / "t1_cpa128.csv"

w = json.loads(WIN.read_text(encoding="utf-8"))
s = json.loads(SCAN.read_text(encoding="utf-8"))
a = w["arms"]
assert w["point"] == {"r": 10163, "d": 71, "t": 140, "t_over_r": 140 / 10163}, w["point"]

rows = []
W = "cpa128_window/report.json"
S = "cpa128_scan/report.json"


def add(label, value, sig, source=W, note=""):
    rows.append({"tier": 1, "label": label, "value": value, "sig": sig,
                 "source": source, "note": note})


add("CPA-128 r", w["point"]["r"], 4)
add("CPA-128 d", w["point"]["d"], 4)
add("CPA-128 t", w["point"]["t"], 4)
add("CPA-128 production weight", 134, 3, W, "same production weight as Level 1")
add("CPA-128 trials per arm", a["C0"]["trials"], 4)
add("CPA-128 keys", 32, 4)
add("CPA-128 C0 failures", a["C0"]["failures"], 4)
add("CPA-128 C0 DFR", a["C0"]["dfr"], 3)
add("CPA-128 FRO-2 failures", a["FRO-2"]["failures"], 4)
add("CPA-128 FRO-2 RR", a["FRO-2"]["rr"], 3)
add("CPA-128 FRO-2 RR lower", a["FRO-2"]["rr_ci95"][0], 3)
add("CPA-128 FRO-2 RR upper", a["FRO-2"]["rr_ci95"][1], 3)
add("CPA-128 FRONEG failures", a["FRONEG"]["failures"], 4)
add("CPA-128 FRONEG RR", a["FRONEG"]["rr"], 3)
add("CPA-128 FRONEG RR lower", a["FRONEG"]["rr_ci95"][0], 3)
add("CPA-128 FRONEG RR upper", a["FRONEG"]["rr_ci95"][1], 3)
add("CPA-128 band open lower t", 138, 4, S, "scan: first nonzero at t=138")
add("CPA-128 band open upper t", 142, 4, S, "scan: 3.75e-3 at t=142")

with DST.open("w", newline="", encoding="utf-8-sig") as f:
    wtr = csv.DictWriter(f, fieldnames=["tier", "label", "value", "sig", "source", "note"])
    wtr.writeheader()
    wtr.writerows(rows)
print(f"wrote {DST} ({len(rows)} claims)")
