#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fig3_mechanism -- first-round flip accounting and failure-mode composition
(single column, 3.5 x 3.6 in), v3 redraw (nature-figure pass).

SHIPPING NOTE (2026-10-17): the v3 manuscript ships the
figure_research/complete_set rendering of this figure. Do not re-run this
script into v3/figures; it would overwrite the shipped art.

Panel (a): paired HORIZONTAL bars, C0 vs FRO-2, for total / correct /
incorrect first-round flips and the post-round-1 residual, with direct value
labels and a right-hand C0/FRO-2 ratio column (x3.3 / x2.7 / x9.5 / x0.93).
Only the two callouts the manuscript makes (9.5x incorrect, 2.7x correct) are
bold.  RAND rows only, exactly as the archived function: averaging the three
conditions would give 9.3x / 2.6x and contradict the 9.5x / 2.7x gate values.

Panel (b): failure-mode composition, monochrome neutral ramp -- stagnation =
control solid, early misflip = grey '///', other = neutral_light '...' (the
always-zero divergence / period2 categories are kept in the mapping but draw
nothing).  The "preregistered window" note stays as a small axis note at the
top-right inside the panel; the frame-less legend keeps the band below the
axes to itself.

Data (read-only, via style_v3.load): t1_mechanism_firstround.csv,
t1_failure_modes.csv.  No recomputation beyond the archived function (means
over RAND rows per arm; ratio = C0 / FRO-2).  Output goes to
lw-vs/v3/figures/ (pdf + svg + 600 dpi png).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import style_v3 as st

C0, FRO2 = st.C0, st.FRO2
NEUT, NEUT_LIGHT = st.NEUT, st.PAL["neutral_light"]
MUTED, INK = st.PAL["muted"], st.INK


def _fmt(v):
    """Counts: one decimal at >= 1, two below (0.84 must not print as 0.8)."""
    return f"{v:.1f}" if v >= 1 else f"{v:.2f}"


def main():
    plt.rcParams["hatch.linewidth"] = 0.5
    mech = st.load("t1_mechanism_firstround.csv")
    modes = st.load("t1_failure_modes.csv")
    mech = [r for r in mech if r.get("condition") == "RAND"]

    fig = plt.figure(figsize=(st.COL_W, 3.6), layout="constrained")
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.0], hspace=0.14)

    # ---- (a) paired horizontal bars: C0 vs FRO-2, first-round accounting ----
    ax = fig.add_subplot(gs[0, 0]); st.panel(ax, "a")
    metrics = [("total", "total\nflips"), ("correct", "correct\nflips"),
               ("incorrect", "incorrect\nflips"), ("residual", "residual\nerrors")]
    colkey = {"total": "mean_total_first", "correct": "mean_correct_first",
              "incorrect": "mean_incorrect_first", "residual": "mean_residual_r1"}
    agg = {}
    for r in mech:
        agg.setdefault(r["arm"], []).append(r)
    armcol = {"C0": C0, "FRO-2": FRO2}
    xr = 96.0                                   # ratio column anchor (data units)
    for i, (m, _lab) in enumerate(metrics):
        y = 3 - i
        vals = {a: sum(st.f(r[colkey[m]]) for r in agg[a]) / len(agg[a])
                for a in ("C0", "FRO-2")}
        # C0 always the upper bar of the pair, FRO-2 the lower
        for a, dy in (("C0", 0.19), ("FRO-2", -0.19)):
            ax.barh(y + dy, vals[a], height=0.30, color=armcol[a],
                    edgecolor=INK, lw=0.35, zorder=3)
            ax.text(vals[a] + 1.3, y + dy, _fmt(vals[a]), va="center",
                    ha="left", fontsize=5.6, color=armcol[a], zorder=4)
        ratio = vals["C0"] / vals["FRO-2"]
        cell = "$\\times$" + (f"{ratio:.1f}" if ratio >= 1 else f"{ratio:.2f}")
        ax.text(xr, y, cell, va="center", ha="left", fontsize=6.0, color=INK,
                fontweight="bold" if m in ("incorrect", "correct") else "normal",
                zorder=4)
        if m == "residual":
            ax.text(xr + 12.0, y, "(grows)", va="center", ha="left",
                    fontsize=5.0, color=MUTED, zorder=4)
        print(f"  (a) {m:9s} C0 {vals['C0']:8.4f}  FRO-2 {vals['FRO-2']:8.4f}"
              f"  ratio {ratio:.4f}  -> {cell}")
    ax.set_yticks([3, 2, 1, 0])
    ax.set_yticklabels([lab for _, lab in metrics], fontsize=6.0)
    ax.set_xlim(0, 120)
    ax.set_xticks([0, 20, 40, 60, 80])
    ax.set_ylim(-0.95, 4.05)
    ax.set_xlabel("mean count per decode (RAND, first round)", fontsize=6.5)
    ax.text(xr, 3.70, "C0/FRO-2", fontsize=5.6, color=MUTED, ha="left",
            va="center")
    handles = [Patch(facecolor=armcol[a], edgecolor=INK, lw=0.35, label=a)
               for a in ("C0", "FRO-2")]
    ax.legend(handles=handles, loc="upper left", ncol=2, fontsize=5.4,
              handlelength=1.1, handleheight=0.7, borderpad=0.3,
              columnspacing=0.7, handletextpad=0.35)
    ax.text(0.985, 0.015, "fewer incorrect flips = better",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=5.2, color=MUTED)

    # ---- (b) failure-mode composition, monochrome ramp ---------------------
    ax = fig.add_subplot(gs[1, 0]); st.panel(ax, "b")
    # divergence / period2 are 0.0 in every cell of the CSV and never draw
    order = ["stagnation", "early_misflip", "divergence", "period2", "other"]
    shade = {"stagnation": C0, "early_misflip": NEUT, "other": NEUT_LIGHT}
    xpos, xticks, xlabels, centers = 0.0, [], [], []
    for cname in st.COND:
        first = xpos
        for arm in ("C0", "FRO-2"):
            sub = [r for r in modes if r["condition"] == cname and r["arm"] == arm]
            bot = 0.0
            for m in order:
                v = next((st.f(r["fraction"]) for r in sub if r["mode"] == m), 0.0)
                if v <= 0:
                    continue
                ax.bar(xpos, v, bottom=bot, width=0.68, color=shade[m],
                       edgecolor=INK, lw=0.35, hatch=st.HATCH.get(m, ""),
                       zorder=3,
                       label=m.replace("_", " ") if cname == "RAND" and arm == "C0"
                       else None)
                bot += v
            xticks.append(xpos); xlabels.append(arm)
            xpos += 1.0
        centers.append((first + xpos - 1.0) / 2.0)
        xpos += 0.55
    ax.set_xticks(xticks); ax.set_xticklabels(xlabels, fontsize=6.0)
    ax.set_xlim(xticks[0] - 0.75, xticks[-1] + 0.75)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylim(0, 1.16)
    ax.set_ylabel("share among failures", fontsize=7)
    for c, cname in zip(centers, st.COND):
        ax.text(c, 1.02, st.COND_SHORT[cname], transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=6.0, color=MUTED)
    # archived footer note, relocated to a small top-right axis note
    ax.text(0.985, 0.985,
            "preregistered window $\\lceil T/4 \\rceil$; identical counts to the "
            "pre-fix classifier",
            transform=ax.transAxes, ha="right", va="top", fontsize=5.2,
            color=MUTED)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.145), ncol=3,
              fontsize=5.8, columnspacing=1.0, handletextpad=0.4,
              handlelength=1.2, handleheight=0.8)

    st.save(fig, "fig3_mechanism")


if __name__ == "__main__":
    main()
