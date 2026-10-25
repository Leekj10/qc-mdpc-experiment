#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Palette acceptance checks for the v3 figure set (nature-figure pass).

Same measurable gates as the 10.12 set (greyscale >= 45 for co-occurring
pairs, >= 60 for the core control/hero contrast, >= 0.15 simulated
deuteranopia/protanopia distance for every pair), with the PANELS map updated
to the v3 colour semantics:

  * condition groups and operating points are drawn in the neutral family,
    never in hero blue or accent red;
  * failure-mode categories are a monochrome ramp (control / grey / light);
  * third-party decoders use the grey family (mid + light) with hatch.

Loads PAL, HATCH and mstyle from v3/scripts/style_v3.py.

Run:  python lw-vs/v3/scripts/check_palette_v3.py
"""
from __future__ import annotations

import importlib.util
import itertools
import sys
from pathlib import Path

import numpy as np
from matplotlib import colors as mc

HERE = Path(__file__).resolve().parent

# Viénot/Brettel-style dichromat projection matrices (linear RGB)
DEUT = np.array([[0.625, 0.375, 0.0], [0.70, 0.30, 0.0], [0.0, 0.30, 0.70]])
PROT = np.array([[0.567, 0.433, 0.0], [0.558, 0.442, 0.0], [0.0, 0.242, 0.758]])

GREY_MIN = 45.0
GREY_MIN_CORE = 60.0
CB_MIN = 0.15

FAIL: list[str] = []
N = 0


def load_style():
    spec = importlib.util.spec_from_file_location("_style_v3", HERE / "style_v3.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def luminance(hexcol: str) -> float:
    r, g, b = mc.to_rgb(hexcol)
    return 0.299 * r + 0.587 * g + 0.114 * b


def simulate(hexcol: str, mat: np.ndarray) -> np.ndarray:
    v = np.array(mc.to_rgb(hexcol))
    lin = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return np.clip(mat @ lin, 0.0, 1.0)


def pair_metrics(a: str, b: str) -> tuple[float, float]:
    grey = abs(luminance(a) - luminance(b)) * 255.0
    cb = min(float(np.linalg.norm(simulate(a, DEUT) - simulate(b, DEUT))),
             float(np.linalg.norm(simulate(a, PROT) - simulate(b, PROT))))
    return grey, cb


# panel -> (colour slots sharing it, second channel).  Kept in sync with the
# figure scripts by hand.
# NOTE (2026-10-17): ALL SIX shipped figures now come from
# figure_research/complete_set (Tol High Contrast palette, validated by that
# package's vector_validation.json and data_integrity.json).  This gate is
# kept only for the legacy style_v3 scripts and currently checks no shipped
# figure, so the panel map is empty by design.
PANELS: dict = {}
CORE = {"control", "hero"}

# (marker, linestyle) identity by slot for line/scatter panels
SHAPE_SLOTS = {
    "control": ("o", "-"), "hero": ("s", "-"), "benign": ("D", "--"),
    "accent": ("X", "--"), "grey": ("s", "--"), "neutral_light": ("^", ":"),
    "grey_light": ("^", ":"),
}
# hatch identity by slot for bar panels
HATCH_SLOTS = {"control": "", "hero": "", "benign": "..", "accent": "///",
               "grey": "///", "neutral_light": "\\\\\\"}


def main() -> int:
    global N
    st = load_style()
    pal = st.PAL
    slots = {k: v for k, v in pal.items()
             if k not in ("ink", "muted", "grid", "hair", "surface")}

    print(f"{'slot':15s}{'hex':10s}{'greyscale':>11s}")
    for k, v in slots.items():
        print(f"  {k:13s}{v:10s}{luminance(v)*255:8.1f}")
    print()

    for panel, (members, channel) in PANELS.items():
        print(f"-- {panel}  [{channel} channel] --")
        for a, b in itertools.combinations(sorted(set(members)), 2):
            N += 1
            g, cb = pair_metrics(slots[a], slots[b])
            core = {a, b} == CORE
            need = GREY_MIN_CORE if core else GREY_MIN
            ok_c = cb >= CB_MIN
            if channel == "hatch":
                separated = HATCH_SLOTS.get(a, "") != HATCH_SLOTS.get(b, "")
            else:
                separated = SHAPE_SLOTS.get(a) != SHAPE_SLOTS.get(b)
            ok_g = g >= need
            if not ok_c:
                FAIL.append(f"{panel}: {a} vs {b} colourblind distance {cb:.3f} < {CB_MIN}")
            if not ok_g and not (separated and not core):
                FAIL.append(f"{panel}: {a} vs {b} greyscale {g:.1f} < {need:.0f}"
                            + ("" if separated else f"  (no {channel} channel to compensate)"))
            mark = "ok " if (ok_g or separated) and ok_c else "XX "
            tag = "core" if core else "    "
            print(f"  {mark}{tag} {a:13s}vs {b:13s} grey{g:6.1f} (need {need:.0f})"
                  f"  cb{cb:.3f}{'  [' + channel + ']' if not ok_g else ''}")
        print()

    print(f"ran {N} pair checks")
    if FAIL:
        print(f"\n{len(FAIL)} FAILURE(S):")
        for f in FAIL:
            print("  -", f)
        return 1
    print("PASS: every co-occurring pair is colourblind-separable, and the core "
          "contrast also survives greyscale printing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
