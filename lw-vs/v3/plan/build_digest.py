# -*- coding: utf-8 -*-
"""Build the v3 writer-facing data digest from the frozen archives.

- data_digest.csv : every lw-vs/data CSV concatenated with file headers (the
  only numbers writers may quote).
- allowed_numbers.txt : every numeric token recoverable from the archives
  (values + parameters), used for the post-assembly novel-number scan.
"""
import csv
import re
import shutil
from pathlib import Path

BASE = Path(r"D:/桌面/TOUGAO - c/lw-vs")
DATA = BASE / "data"
V3 = BASE / "v3"
PLAN = V3 / "plan"
PLAN.mkdir(exist_ok=True)

NUM = re.compile(r"[0-9]+(?:\.[0-9]+)?")

digest = []
allowed = set()
for p in sorted(DATA.glob("*.csv")):
    text = p.read_text(encoding="utf-8-sig")
    digest.append(f"===== {p.name} =====\n{text}")
    for tok in NUM.findall(text):
        allowed.add(tok)
        # also add integer-rounded renderings commonly used in prose
        try:
            fv = float(tok)
            allowed.add(str(int(fv)) if fv == int(fv) else tok)
        except ValueError:
            pass

(PLAN / "data_digest.csv").write_text("\n".join(digest), encoding="utf-8")

# structural constants that are experiment definitions, not measurements
extra = [
    "20",    # iteration budget T
    "12",    # run length; NCW overlap kappa = 12 (also in CSVs)
    "46", "60",   # kappa stress values (also in CSVs)
    "7",     # spec iteration count; budget arm
    "10",    # budget arm
    "3",     # Delta; rule of three
    "2",     # +2
    "1",     # +1 / minus one
    "4801", "45", "92", "3001", "37", "66", "4001", "41", "82",
    "6007", "56", "100", "12323", "71", "134", "10163", "140", "172",
    "9602", "90", "84",   # Misoczki set
    "128",                # 2^-128 target
]
allowed.update(extra)
(PLAN / "allowed_numbers.txt").write_text(
    "\n".join(sorted(allowed, key=lambda s: (len(s), s))), encoding="utf-8")
print("digest bytes:", (PLAN / "data_digest.csv").stat().st_size)
print("allowed number tokens:", len(allowed))

# copy figures and bibliography for a self-contained folder
FIG_SRC = BASE / "10.12" / "figures"
for stem in ("fig1_study_design", "fig2_main_results", "fig3_mechanism",
             "fig4_temporal_dissociation", "fig5_scope_and_boundary",
             "fig7_modern_decoders"):
    for ext in ("pdf", "svg", "png"):
        src = FIG_SRC / f"{stem}.{ext}"
        if src.exists():
            shutil.copy2(src, V3 / "figures" / src.name)
shutil.copy2(BASE / "en" / "refs.bib", V3 / "en" / "refs.bib")
shutil.copy2(BASE / "zh" / "refs.bib", V3 / "zh" / "refs.bib")
print("figures + refs.bib copied")
