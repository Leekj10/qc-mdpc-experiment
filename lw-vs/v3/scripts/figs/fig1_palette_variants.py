#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Two muted palette variants of Figure 1, for visual comparison.

A: muted blue  + muted ochre   (#3A5A80 / #B08A3E)
B: muted blue  + muted terracotta (#3A5A80 / #A8674F)

Both keep the semantic roles of Fig. 2 (blue = C0, warm = FRO-2) but lower
saturation. Outputs go to redesign/fig1_v3/palette_variants/.
"""
from pathlib import Path
import shutil

import fig1_study_design_v3 as f

BASE = Path(f.OUT)


def run(tag, c0, fro):
    out = BASE / "palette_variants" / tag
    out.mkdir(parents=True, exist_ok=True)
    f.C0, f.FRO2 = c0, fro
    f.OUT = out
    f.build_wide()
    f.build_single()
    for stem in ("fig1_v3_wide", "fig1_v3_single"):
        for ext in ("pdf", "svg", "png"):
            src = out / f"{stem}.{ext}"
            dst = out / f"{stem.replace('fig1_v3', 'fig1_' + tag)}.{ext}"
            if src.exists():
                shutil.move(str(src), str(dst))
    print(tag, "->", out)


if __name__ == "__main__":
    run("muted_a", "#3A5A80", "#B08A3E")
    run("muted_b", "#3A5A80", "#A8674F")
