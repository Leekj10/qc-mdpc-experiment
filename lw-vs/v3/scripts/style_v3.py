#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared style, palette and helpers for the v3 figure set (nature-figure pass).

The 10.12 set established the semantic rule that v3 keeps unchanged:

    COLOUR CARRIES THE ARM / DIRECTION ONLY.
      control (near-black) = C0, the paired control, in every panel
      hero    (blue)       = FRO-2, the intervention, in every panel
      benign  (green)      = other one-shot / recovery arms
      accent  (red)        = destructive configurations
      grey family          = third-party decoders (mid + light, with hatch)

Condition groups (RAND / TYPE-I / NCW), operating points (P2 / P3) and
failure-mode categories are NOT arms: they stay in the neutral family and are
separated by marker, line style and hatch only.

What changed for v3 (nature-figure backend contract):
  * sans-serif type (Arial / Helvetica / DejaVu Sans) with editable SVG text;
  * palette values taken from the nature-figure PALETTE (neutral_black control,
    blue_secondary hero, delta_up benign, red_strong accent, neutral_mid grey);
  * open axes (no top/right spines), no grid, frame-less legends, thin rules.

Gates: check_palette_v3.py re-checks greyscale (>= 60 core / >= 45 other) and
simulated deuteranopia/protanopia distance (>= 0.15) for every co-occurring
pair, with the second channel (shape or hatch) declared per panel.

Data is read-only from lw-vs/data/.
Output goes to lw-vs/v3/figures/ (the manuscript's graphicspath ../figures/).
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import ticker

ROOT = Path(__file__).resolve().parents[2]          # lw-vs/
DATA = ROOT / "data"
OUT = ROOT / "v3" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# IEEE two-column widths (89 mm single / 182 mm double)
# ---------------------------------------------------------------------------
COL_W, DBL_W = 3.5, 7.16

# ---------------------------------------------------------------------------
# Palette.  Six semantic slots -- see module docstring.  Hues follow the
# palette this literature actually publishes (sampled from the three
# field exemplars under lw-vs/v3/plan/_ref_figs: Kichna et al. CommNet'24,
# BF-Max, and Cai & Zhang 2024, all MATLAB-family): MATLAB blue #0072BD for
# the intervention, MATLAB green #77AC30 for the benign arm, MATLAB orange
# #D95319 -- the hue those papers put on their worst performer -- for the
# destructive arm, and a near-black baseline, matching the black series that
# Cai & Zhang and BF-Max plot first.  Gates live in check_palette_v3.py.
# ---------------------------------------------------------------------------
PAL = {
    "control": "#111111",   # C0, the paired control in every panel (deep black)
    "hero":    "#0072BD",   # FRO-2, the intervention (MATLAB blue)
    "benign":  "#77AC30",   # other one-shot / recovery arms (R2one, STLR, SR-NCW)
    "grey":    "#767676",   # third-party decoders (BIKE-Flip, BGF, NCW-aware)
    "grey_light": "#A6A6A6",  # third neutral level (3rd condition line in fig7b)
    "accent":  "#D95319",   # destructive configurations (R2plus, FRONEG, UNIFORM-2)
    "ink":     "#1A1A1A",
    "muted":   "#6B7280",
    "grid":    "#DCE0E5",
    "hair":    "#B8BEC5",
    "surface": "#F5F6F7",
    # Lightest neutral step for condition / mode series (NOT arms).
    "neutral_light": "#CFCECE",
}
C0, FRO2, NEUT, ACC, BENIGN = (PAL["control"], PAL["hero"], PAL["grey"],
                                PAL["accent"], PAL["benign"])
INK, MUTED, GRID = PAL["ink"], PAL["muted"], PAL["grid"]

STYLE = {
    "C0":         ("o", "-"),   "FRO-2":      ("s", "-"),
    "FRO-1":      ("^", "-"),   "FRO-3":      ("v", "-"),
    "R2one":      ("D", "--"),  "R2plus":     ("X", "--"),
    "FRONEG":     ("P", ":"),   "UNIFORM-2":  ("*", ":"),
    "BIKE-Flip":  ("d", (0, (5, 1, 1, 1))),  "BGF-C3":  ("h", (0, (3, 1, 3, 1))),
    "STLR":       ("^", "--"),  "SR-NCW":     ("v", ":"),
    "NCW-aware":  ("D", (0, (4, 2))),  "Backflip": ("p", (0, (1, 1))),
    # neutral series for conditions / operating points (NOT arms):
    "RAND":       ("o", "-"),   "TYPE-I":     ("s", "--"),  "NCW": ("^", ":"),
    "P2":         ("o", "-"),   "P3":         ("s", "--"),
}
HATCH = {"C0": "", "FRO-2": "", "FRO-1": "", "FRO-3": "", "R2one": "..",
         "FRONEG": "///", "R2plus": "\\\\\\", "UNIFORM-2": "xxx",
         "BIKE-Flip": "///", "BGF-C3": "\\\\\\", "STLR": "", "SR-NCW": "",
         "NCW-aware": "",
         # failure-mode categories (monochrome ramp)
         "stagnation": "", "early_misflip": "///", "other": "..."}


def mstyle(arm: str):
    """(marker, linestyle) for a named series; falls back to a circle/solid."""
    return STYLE.get(arm, ("o", "-"))


mpl.rcParams.update({
    # nature-figure backend contract: sans-serif, editable SVG text
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "Liberation Sans"],
    "mathtext.fontset": "dejavusans",
    "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6,
    # open axes, no grid, thin rules
    "axes.linewidth": 0.7, "axes.spines.top": False, "axes.spines.right": False,
    "axes.axisbelow": True,
    "axes.grid": False,
    "xtick.direction": "out", "ytick.direction": "out",
    "xtick.major.width": 0.7, "ytick.major.width": 0.7,
    "xtick.major.size": 2.4, "ytick.major.size": 2.4,
    "xtick.minor.size": 1.2, "ytick.minor.size": 1.2,
    "axes.edgecolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "axes.labelcolor": INK,
    # frame-less legends
    "legend.frameon": False, "legend.framealpha": 1.0,
    "legend.handlelength": 1.6, "legend.borderpad": 0.3, "legend.labelspacing": 0.32,
    "lines.linewidth": 1.0, "lines.markersize": 3.2,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

COND = ["RAND", "TYPE-I", "NCW-shallow"]
COND_SHORT = {"RAND": "RAND", "TYPE-I": "TYPE-I", "NCW-shallow": "NCW"}


def panel(ax, s, pad=4):
    """Panel letter above the axes bbox (never collides with the y-label)."""
    ax.set_title(s, loc="left", fontweight="bold", fontsize=8, pad=pad)


def no_minor_labels(ax, which="x"):
    a = ax.xaxis if which == "x" else ax.yaxis
    a.set_minor_formatter(ticker.NullFormatter())


def save(fig, stem):
    """One layout pass; no bbox_inches='tight' (conflicts with constrained_layout)."""
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"{stem}.{ext}")
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    plt.close(fig)
    print(f"  ok {stem}.pdf/.svg/.png")


def load(name):
    with open(DATA / name, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(v, default=float("nan")):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def forest(ax, labels, points, los, his, colors, ref=1.0, xlabel="", xlim=None,
           is_log=True, marker="o"):
    """Reusable horizontal risk-ratio forest with a visible null line."""
    y = list(range(len(labels)))[::-1]
    if is_log:
        ax.set_xscale("log")
        no_minor_labels(ax)
    for yi, p, lo, hi, c in zip(y, points, los, his, colors):
        ax.plot([lo, hi], [yi, yi], color=c, lw=1.1, solid_capstyle="butt", zorder=2)
        ax.plot([p], [yi], marker, color=c, ms=4.2, zorder=3,
                markeredgecolor="white", markeredgewidth=0.5)
    ax.axvline(ref, color=PAL["hair"], lw=0.7, ls=(0, (3, 2)), zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_ylim(-0.7, len(labels) - 0.3)
    if xlim:
        ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    if is_log:
        ax.xaxis.set_major_locator(ticker.FixedLocator(
            [t for t in (0.5, 1, 2, 3, 5, 10, 20, 50) if xlim is None or xlim[0] <= t <= xlim[1]]))
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
