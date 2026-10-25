#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fig2_main_results -- v3 top-journal redesign of the primary-result figure
(double column, 7.16 x 2.45 in).

SHIPPING NOTE (2026-10-17): the v3 manuscript ships the
figure_research/complete_set rendering of this figure. Do not re-run this
script into v3/figures; it would overwrite the shipped art.

Contract:
  core conclusion: FRO-2 lowers conditional DFR 4.15-5.47x across all three key
  families; the direction survives key-level resampling and appears on most keys
  individually.

  (a) hero: PAIRED DUMBBELL -- one connector per condition joins the C0 rate
      (circle) and the FRO-2 rate (square) on a log DFR axis; one-sided 95% cap
      whiskers ride each marker; the fold change is printed above each pair.
      Direct arm labels on the first pair; no legend.
  (b) risk-ratio forest: point + 95% key-cluster interval per condition; the
      dashed line at 1 is the neutral value; the region to its right is tinted
      and labelled as favouring FRO-2; point values printed at the right edge.
  (c) PAIRED-DIFFERENCE DOT STRIP: per key-and-condition cell, the difference
      C0 - FRO-2 failures, one dot per cell, stacked at equal values.  Filled
      hero-blue dots right of zero = FRO-2 fails fewer times (233); filled
      near-black dots left of zero = C0 fewer (18); open rings = ties (27).
      Position IS the direction, so no colour-only encoding is needed.

Data: lw-vs/data/t1_formal_main.csv (panels a, b) and t1_per_key.csv (panel c).
Every plotted number is read through style_v3.load(); no recomputation.

Run:  python lw-vs/v3/scripts/figs/fig2_main_results.py
"""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker
import style_v3 as st

COND, COND_SHORT = st.COND, st.COND_SHORT


def fig2_main():
    main = {r["condition"]: r for r in st.load("t1_formal_main.csv")}
    perkey = st.load("t1_per_key.csv")
    fig = plt.figure(figsize=(st.DBL_W, 2.45), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.00, 1.05, 1.06], wspace=0.30)

    # -- (a) paired dumbbell: C0 -> FRO-2 per condition ----------------------
    ax = fig.add_subplot(gs[0, 0]); st.panel(ax, "a")
    ax.set_xscale("log")
    ax.yaxis.set_major_locator(ticker.FixedLocator([0, 1, 2]))
    ax.set_yticklabels([COND_SHORT[c] for c in COND][::-1])
    ax.set_ylim(-0.55, 2.95)

    capw = 0.055
    for i, cname in enumerate(COND):
        y = 2 - i
        r = main[cname]
        c0d, c0u = st.f(r["c0_dfr"]), st.f(r["c0_upper95"])
        f2d, f2u = st.f(r["fro2_dfr"]), st.f(r["fro2_upper95"])
        # connector between the paired rates (the pairing made visual)
        ax.plot([c0d, f2d], [y, y], color=st.PAL["hair"], lw=0.9,
                solid_capstyle="butt", zorder=1.5)
        for d, u, col, mk in ((c0d, c0u, st.C0, "o"), (f2d, f2u, st.FRO2, "s")):
            # one-sided 95% upper cap: the DFR lives on the x axis, so the
            # whisker is horizontal from the rate to the cap, closed by a
            # small vertical tick at the cap
            ax.plot([d, u], [y, y], color=col, lw=0.85, solid_capstyle="butt",
                    zorder=2)
            ax.plot([u, u], [y - 0.085, y + 0.085], color=col, lw=0.9,
                    solid_capstyle="butt", zorder=2)
            ax.plot([d], [y], mk, color=col, ms=4.6, zorder=4,
                    markeredgecolor="white", markeredgewidth=0.55)
        # fold change above the pair (value = rr from the CSV)
        mid = 10 ** ((math.log10(c0d) + math.log10(f2d)) / 2)
        ax.text(mid, y + 0.30, f"$\\times${st.f(r['rr']):.2f}", fontsize=6.2,
                color=st.FRO2, ha="center", va="bottom", fontweight="bold", zorder=5)
    # direct arm labels once, on the first pair
    r0 = main[COND[0]]
    ax.text(st.f(r0["c0_dfr"]), 2.52, "C0", color=st.C0, fontsize=6.2,
            ha="center", va="bottom", zorder=5)
    ax.text(st.f(r0["fro2_dfr"]), 2.52, "FRO-2", color=st.FRO2, fontsize=6.2,
            ha="center", va="bottom", fontweight="bold", zorder=5)
    ax.set_ylabel("conditional DFR")
    # tight range: the paired differences occupy most of the axis
    ax.set_xlim(8.6e-5, 2.35e-3)
    ax.set_ylim(-0.55, 3.05)
    ax.xaxis.set_major_locator(ticker.LogLocator(base=10, numticks=4))
    st.no_minor_labels(ax, "x")
    ax.text(0.98, 0.03, "whiskers: one-sided 95% cap", transform=ax.transAxes,
            fontsize=5.2, color=st.MUTED, ha="right", va="bottom")

    # -- (b) risk-ratio forest with a direction band -------------------------
    ax = fig.add_subplot(gs[0, 1]); st.panel(ax, "b")
    labels = [COND_SHORT[c] for c in COND]
    pts = [st.f(main[c]["rr"]) for c in COND]
    los = [st.f(main[c]["rr_lo"]) for c in COND]
    his = [st.f(main[c]["rr_hi"]) for c in COND]
    ax.set_xscale("log")
    st.no_minor_labels(ax, "x")
    xlim = (0.78, 8.2)
    # tinted half-plane: everything right of 1 favours FRO-2
    ax.axvspan(1.0, xlim[1], facecolor=st.FRO2, alpha=0.05, lw=0, zorder=0.4)
    st.forest(ax, labels, pts, los, his, [st.FRO2] * 3, marker=st.mstyle("FRO-2")[0],
              xlabel="risk ratio  C0 / FRO-2  (95% key-cluster CI)", xlim=xlim)
    for yi, p in zip([2, 1, 0], pts):
        ax.text(p, yi + 0.30, f"{p:.2f}", fontsize=6.0, color=st.FRO2,
                ha="center", va="bottom", zorder=5, fontweight="bold")
    ax.text(3.9, -0.62, "favours FRO-2", fontsize=5.4, color=st.FRO2, ha="center",
            va="center")
    ax.text(0.955, -0.62, "no effect", fontsize=5.2, color=st.MUTED, ha="right",
            va="center")

    # -- (c) paired-difference dot strip -------------------------------------
    ax = fig.add_subplot(gs[0, 2]); st.panel(ax, "c")
    diffs = [int(r["c0_failures"]) - int(r["fro2_failures"]) for r in perkey]
    win = sum(1 for d in diffs if d > 0)
    lose = sum(1 for d in diffs if d < 0)
    tie = sum(1 for d in diffs if d == 0)
    from collections import Counter
    cnt = Counter(diffs)
    ymax = max(cnt.values())
    for v, n in sorted(cnt.items()):
        if v == 0:
            ys = [i - (n - 1) / 2.0 for i in range(n)]
            ax.plot([0] * n, ys, "o", ms=2.1, mfc="white", mec=st.NEUT, mew=0.5,
                    zorder=4, linestyle="none")
        else:
            col = st.FRO2 if v > 0 else st.C0
            ys = [i - (n - 1) / 2.0 for i in range(n)]
            ax.plot([v] * n, ys, "o", ms=2.2, mfc=col, mec="none", zorder=3.5,
                    linestyle="none")
    ax.axvline(0, color=st.PAL["hair"], lw=0.8, zorder=1)
    ax.set_xlim(-3.4, 10.4)
    ax.set_ylim(-ymax / 2.0 - 2.4, ymax / 2.0 + 2.6)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xticks([-2, 0, 2, 4, 6, 8, 10])
    ax.set_xlabel("C0 failures minus FRO-2 failures, per key")
    # counts in the empty top-right corner (short lines only, so they never
    # reach the tall left-hand columns)
    ax.text(0.98, 0.97, f"FRO-2 fewer: {win} cells", fontsize=5.5,
            color=st.FRO2, ha="right", va="top", transform=ax.transAxes,
            fontweight="bold")
    ax.text(0.98, 0.895, f"C0 fewer: {lose}  ·  tied: {tie}", fontsize=5.2,
            color=st.MUTED, ha="right", va="top", transform=ax.transAxes)
    ax.text(0.98, 0.825, "(278 cells, one dot each)", fontsize=5.0,
            color=st.MUTED, ha="right", va="top", transform=ax.transAxes)
    print(f"  (c) differences: FRO-2 fewer {win}, C0 fewer {lose}, tied {tie}, "
          f"max stack {ymax}")

    st.save(fig, "fig2_main_results")


if __name__ == "__main__":
    fig2_main()
