#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figure 1 (redrawn 2026-10-22) -- study design, Tol palette matching Fig. 2.

Palette (same as the shipped Fig. 2):
    C0   = #004488 (Tol blue)
    FRO2 = #DDAA33 (Tol gold)
    red  = #BB5566 (reserved for harm / boundary; unused here)
    grey = neutral text/rules

Contract: paired instance -> within-instance comparison; one-shot round-one
+2 schedule; four evidence streams. Schematic-led composite, Python only.

Outputs: lw-vs/v3/redesign/fig1_v3/{wide,single}.{pdf,svg,png}
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parents[2] / "redesign" / "fig1_v3"
OUT.mkdir(parents=True, exist_ok=True)

C0 = "#004488"
FRO2 = "#DDAA33"
INK = "#111111"
MUTED = "#6B7280"
HAIR = "#B8BEC5"
SURF = "#F5F6F7"


def _box(ax, xy, w, h, ec=HAIR, fc="white", lw=0.7):
    ax.add_patch(FancyBboxPatch(xy, w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.025",
                                fc=fc, ec=ec, lw=lw, zorder=1))


def _arrow(ax, x0, y0, x1, y1, color=MUTED):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=6, lw=0.7, color=color,
                                 shrinkA=1.0, shrinkB=1.0, zorder=2))


def panel_a(ax):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.01, 0.96, "a", fontsize=8, fontweight="bold", color=INK,
            ha="left", va="top")

    _box(ax, (0.01, 0.34), 0.24, 0.34, fc=SURF)
    ax.text(0.13, 0.565, "instance", ha="center", va="center",
            fontsize=6.4, color=INK, fontweight="bold")
    ax.text(0.13, 0.445, "$(H,\\,e,\\,s)$", ha="center", va="center",
            fontsize=6.8, color=INK)

    _box(ax, (0.36, 0.52), 0.24, 0.15, ec=C0, lw=1.1)
    ax.text(0.48, 0.595, "C0", ha="center", va="center",
            fontsize=6.6, color=C0, fontweight="bold")
    _box(ax, (0.36, 0.35), 0.24, 0.15, ec=FRO2, lw=1.1)
    ax.text(0.48, 0.425, "FRO-2", ha="center", va="center",
            fontsize=6.6, color=FRO2, fontweight="bold")

    _box(ax, (0.71, 0.34), 0.28, 0.34, fc=SURF)
    ax.text(0.85, 0.565, "per-key", ha="center", va="center",
            fontsize=6.2, color=INK, fontweight="bold")
    ax.text(0.85, 0.495, "outcomes", ha="center", va="center",
            fontsize=6.2, color=INK, fontweight="bold")
    ax.text(0.85, 0.405, "$N_{\\mathrm{fail}}^{\\mathrm{C0}}$ vs "
                          "$N_{\\mathrm{fail}}^{\\mathrm{FRO\\text{-}2}}$",
            ha="center", va="center", fontsize=6.0, color=INK)

    _arrow(ax, 0.25, 0.55, 0.36, 0.595)
    _arrow(ax, 0.25, 0.47, 0.36, 0.425)
    _arrow(ax, 0.60, 0.595, 0.71, 0.55)
    _arrow(ax, 0.60, 0.425, 0.71, 0.47)

    ax.text(0.50, 0.17, "same $(H,e,s)$ for both schedules",
            ha="center", va="center", fontsize=6.2, color=MUTED)
    ax.text(0.50, 0.08, "keys, not error draws, are resampled",
            ha="center", va="center", fontsize=6.2, color=MUTED)


def panel_b(ax):
    ax.text(0.02, 0.96, "b", transform=ax.transAxes, fontsize=8,
            fontweight="bold", color=INK, ha="left", va="top")
    rounds = [1, 2, 3, 4, 5, 6]
    c0 = [0, 0, 0, 0, 0, 0]
    fr = [2, 0, 0, 0, 0, 0]

    ax.axhline(0, color="#DCE0E5", lw=0.6, zorder=0)
    ax.step(rounds, c0, where="post", color=C0, lw=1.3, marker="o",
            ms=2.8, zorder=2)
    ax.step(rounds, fr, where="post", color=FRO2, lw=1.5, marker="s",
            ms=2.8, zorder=3)

    ax.annotate("round 1 only", xy=(1.0, 2.03), xytext=(1.55, 2.45),
                ha="left", va="center", fontsize=6.2, color=FRO2,
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color=FRO2,
                                shrinkA=1.0, shrinkB=1.0))
    ax.text(5.85, 0.22, "C0", ha="right", va="bottom", fontsize=6.6, color=C0,
            fontweight="bold")
    ax.text(1.12, 1.62, "FRO-2", ha="left", va="bottom", fontsize=6.6,
            color=FRO2, fontweight="bold")
    ax.text(3.25, 0.22, "same baseline from round 2", ha="center", va="bottom",
            fontsize=5.8, color=MUTED)

    ax.set_xticks(rounds)
    ax.set_yticks([0, 2])
    ax.set_yticklabels(["0", "+2"])
    ax.set_xlabel("round", fontsize=6.4)
    ax.set_ylabel("threshold offset", fontsize=6.4)
    ax.set_xlim(0.8, 6.2)
    ax.set_ylim(-0.35, 2.75)
    ax.tick_params(labelsize=6.0, length=2.5, width=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def panel_c(ax):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.01, 0.96, "c", fontsize=8, fontweight="bold", color=INK,
            ha="left", va="top")

    rows = [
        ("formal pool", "278", "3,000", "primary"),
        ("fresh subset", "212", "3,000", "gate"),
        ("P2 / P3", "50", "1,000", "transfer"),
        ("P4 held-out", "48", "1,000", "rule check"),
    ]
    x = [0.02, 0.46, 0.68, 0.84]
    y0, dy = 0.80, 0.19
    ax.text(x[0], y0, "stream", fontsize=6.2, color=MUTED, fontweight="bold")
    ax.text(x[1], y0, "keys", fontsize=6.2, color=MUTED, fontweight="bold",
            ha="right")
    ax.text(x[2], y0, "errors/key", fontsize=6.2, color=MUTED, fontweight="bold",
            ha="right")
    ax.text(x[3], y0, "role", fontsize=6.2, color=MUTED, fontweight="bold")

    for i, (name, keys, errs, role) in enumerate(rows):
        y = y0 - (i + 1) * dy
        ax.plot([0.01, 0.99], [y + 0.065, y + 0.065], color=HAIR, lw=0.5,
                zorder=0)
        ax.text(x[0], y, name, fontsize=6.6, color=INK, va="center")
        ax.text(x[1], y, keys, fontsize=6.6, color=INK, va="center", ha="right")
        ax.text(x[2], y, errs, fontsize=6.6, color=INK, va="center", ha="right")
        ax.text(x[3], y, role, fontsize=6.2, color=MUTED, va="center")


def build_wide():
    fig = plt.figure(figsize=(7.16, 2.45), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.18, 0.92, 1.30])
    panel_a(fig.add_subplot(gs[0, 0]))
    panel_b(fig.add_subplot(gs[0, 1]))
    panel_c(fig.add_subplot(gs[0, 2]))
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"fig1_v3_wide.{ext}", dpi=600, bbox_inches="tight")
    plt.close(fig)


def build_single():
    fig = plt.figure(figsize=(4.8, 4.6), layout="constrained")
    gs = fig.add_gridspec(3, 1, height_ratios=[1.0, 0.9, 1.0])
    panel_a(fig.add_subplot(gs[0]))
    panel_b(fig.add_subplot(gs[1]))
    panel_c(fig.add_subplot(gs[2]))
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"fig1_v3_single.{ext}", dpi=600, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    build_wide()
    build_single()
    print("wrote", OUT)
