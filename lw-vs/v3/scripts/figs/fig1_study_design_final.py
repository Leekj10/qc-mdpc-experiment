#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figure 1, final two-panel version (2026-10-22).

(a) paired instance: the same (H,e,s) enters C0 and FRO-2, outcomes per key;
(b) one-shot schedule: +2 in round one only, baseline thereafter.

Palette follows the paper's Tol scheme (Fig. 2):
C0 = #004488, FRO-2 = #DDAA33.  No red; no third colour.

Outputs replace v3/figures/fig1_study_design.{pdf,svg,png}; the previous
three-panel art is backed up under redesign/fig1_old/.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 8,
    "mathtext.fontset": "custom",
    "mathtext.rm": "Times New Roman",
    "mathtext.it": "Times New Roman:italic",
    "mathtext.bf": "Times New Roman:bold",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
})

FIG = Path(__file__).resolve().parents[2] / "figures"
OLD = Path(__file__).resolve().parents[2] / "redesign" / "fig1_old"
OUT = Path(__file__).resolve().parents[2] / "redesign" / "fig1_final"
for d in (OLD, OUT):
    d.mkdir(parents=True, exist_ok=True)

C0 = "#004488"
FRO2 = "#DDAA33"
INK = "#111111"
MUTED = "#6B7280"
HAIR = "#B8BEC5"
SURF = "#F5F6F7"


def _box(ax, xy, w, h, ec=HAIR, fc="white", lw=0.8):
    ax.add_patch(FancyBboxPatch(xy, w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.025",
                                fc=fc, ec=ec, lw=lw, zorder=1))


def _arrow(ax, x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=6, lw=0.7, color=MUTED,
                                 shrinkA=1.0, shrinkB=1.0, zorder=2))


def panel_a(ax):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.01, 0.96, "a", fontsize=9.0, fontweight="bold", color=INK,
            ha="left", va="top")

    _box(ax, (0.03, 0.36), 0.24, 0.32, fc=SURF)
    ax.text(0.15, 0.565, "instance", ha="center", va="center",
            fontsize=8.0, color=INK, fontweight="bold")
    ax.text(0.15, 0.445, "$(H,\\,e,\\,s)$", ha="center", va="center",
            fontsize=8.2, color=INK)

    _box(ax, (0.37, 0.53), 0.24, 0.14, ec=C0, lw=1.2)
    ax.text(0.49, 0.60, "C0", ha="center", va="center",
            fontsize=8.0, color=C0, fontweight="bold")
    _box(ax, (0.37, 0.36), 0.24, 0.14, ec=FRO2, lw=1.2)
    ax.text(0.49, 0.43, "FRO-2", ha="center", va="center",
            fontsize=8.0, color=FRO2, fontweight="bold")

    _box(ax, (0.71, 0.36), 0.26, 0.32, fc=SURF)
    ax.text(0.84, 0.565, "per-key", ha="center", va="center",
            fontsize=7.6, color=INK, fontweight="bold")
    ax.text(0.84, 0.495, "outcomes", ha="center", va="center",
            fontsize=7.6, color=INK, fontweight="bold")
    ax.text(0.84, 0.405, "$N_{\\mathrm{fail}}^{\\mathrm{C0}}$ vs "
                          "$N_{\\mathrm{fail}}^{\\mathrm{FRO\\text{-}2}}$",
            ha="center", va="center", fontsize=7.4, color=INK)

    _arrow(ax, 0.27, 0.56, 0.37, 0.60)
    _arrow(ax, 0.27, 0.48, 0.37, 0.43)
    _arrow(ax, 0.61, 0.60, 0.71, 0.56)
    _arrow(ax, 0.61, 0.43, 0.71, 0.48)

    ax.text(0.50, 0.19, "same $(H,e,s)$ for both schedules",
            ha="center", va="center", fontsize=7.4, color=MUTED)
    ax.text(0.50, 0.10, "keys, not error draws, are resampled",
            ha="center", va="center", fontsize=7.4, color=MUTED)


def panel_b(ax):
    ax.text(0.02, 0.96, "b", transform=ax.transAxes, fontsize=9.0,
            fontweight="bold", color=INK, ha="left", va="top")
    rounds = [1, 2, 3, 4, 5, 6]
    c0 = [0, 0, 0, 0, 0, 0]
    fr = [2, 0, 0, 0, 0, 0]

    ax.axhline(0, color="#DCE0E5", lw=0.6, zorder=0)
    ax.step(rounds, c0, where="post", color=C0, lw=1.4, marker="o",
            ms=3.0, zorder=2)
    ax.step(rounds, fr, where="post", color=FRO2, lw=1.6, marker="s",
            ms=3.0, zorder=3)

    ax.annotate("round 1 only", xy=(1.0, 2.03), xytext=(1.5, 2.45),
                ha="left", va="center", fontsize=7.4, color=FRO2,
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color=FRO2,
                                shrinkA=1.0, shrinkB=1.0))
    ax.text(5.85, 0.22, "C0", ha="right", va="bottom", fontsize=7.8, color=C0,
            fontweight="bold")
    ax.text(1.12, 1.62, "FRO-2", ha="left", va="bottom", fontsize=7.8,
            color=FRO2, fontweight="bold")
    ax.text(3.25, 0.22, "same baseline from round 2", ha="center", va="bottom",
            fontsize=7.0, color=MUTED)

    ax.set_xticks(rounds)
    ax.set_yticks([0, 2])
    ax.set_yticklabels(["0", "+2"])
    ax.set_xlabel("round", fontsize=7.6)
    ax.set_ylabel("threshold offset", fontsize=7.6)
    ax.set_xlim(0.8, 6.2)
    ax.set_ylim(-0.35, 2.75)
    ax.tick_params(labelsize=6.2, length=2.5, width=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def build_wide():
    fig = plt.figure(figsize=(7.16, 2.05), layout="constrained")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1.0])
    panel_a(fig.add_subplot(gs[0, 0]))
    panel_b(fig.add_subplot(gs[0, 1]))
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"fig1_final_wide.{ext}", dpi=600)
    plt.close(fig)


def build_single():
    fig = plt.figure(figsize=(4.8, 3.1), layout="constrained")
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.0])
    panel_a(fig.add_subplot(gs[0]))
    panel_b(fig.add_subplot(gs[1]))
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"fig1_final_single.{ext}", dpi=600)
    plt.close(fig)


def install():
    # back up the shipped three-panel art once
    for ext in ("pdf", "svg", "png"):
        src = FIG / f"fig1_study_design.{ext}"
        if src.exists():
            dst = OLD / f"fig1_study_design.{ext}"
            if not dst.exists():
                shutil.copy2(src, dst)
    for ext in ("pdf", "svg", "png"):
        shutil.copy2(OUT / f"fig1_final_wide.{ext}",
                     FIG / f"fig1_study_design.{ext}")
    print("installed", FIG / "fig1_study_design.pdf")


if __name__ == "__main__":
    build_wide()
    build_single()
    install()
