#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fig4_temporal_dissociation -- v3 top-journal redesign, magnified axis.

SHIPPING NOTE (2026-10-17): the v3 manuscript ships the
figure_research/complete_set rendering of this figure. Do not re-run this
script into v3/figures; it would overwrite the shipped art.

Semantics (kept from the 10.12 set):
  (a)-(c)  P2/P3 are OPERATING POINTS, not arms -> neutral family
           (P2 = control deep black, filled circles, solid; P3 = grey, hollow
           squares, dashed), second channel = marker + line style.
  (d)      +2-round-1 hero, round-2-only benign, the two destructive arms accent.

Composition:
  (a)-(c)  the five schedules are GROUPED (one-shot left of the separator,
           sustained uniform offset right of it, headers above), and the
           vertical axis is BROKEN: the top segment (0.45-13, log) magnifies
           the one-shot cluster where the differences are small, the bottom
           segment (0.0035-0.05, log) carries the two-order collapse of the
           sustained offset.  Diagonal break marks on the left spine.
  (d)      effect-size caterpillar: one point plus 95% key-cluster interval per
           round-control arm, worse/better half-planes tinted, C0 = 1 reference.

Data (read-only):
  lw-vs/data/t2_temporal_pivot.csv   -> (a)-(c)
  lw-vs/data/t1_round_controls.csv   -> (d)
"""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import ticker
import style_v3 as st

PAL = st.PAL
INK, MUTED = PAL["ink"], PAL["muted"]

SCHED = ["FRO-1", "FRO-2", "FRO-3", "R2-2", "UNIFORM-2"]
XPOS = [0.0, 1.0, 2.0, 3.0, 4.6]

# broken-axis segments (log scale)
Y_TOP = (0.45, 13.0)
Y_BOT = (0.0035, 0.05)

piv = st.load("t2_temporal_pivot.csv")

fig = plt.figure(figsize=(st.DBL_W, 3.0), layout="constrained")
gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1.30], wspace=0.24)

# ---------------------------------------------------------------------------
# (a)-(c) risk ratio vs schedule: one-shot group left of the separator,
# sustained offset right; broken log axis magnifies the one-shot cluster
# ---------------------------------------------------------------------------
for i, cname in enumerate(st.COND):
    inner = gs[0, i].subgridspec(2, 1, height_ratios=[3.1, 1.1], hspace=0.07)
    axT = fig.add_subplot(inner[0])
    axB = fig.add_subplot(inner[1], sharex=axT)

    st.panel(axT, "abc"[i])
    axT.set_title(st.COND_SHORT[cname], loc="center", pad=4, fontsize=6.8,
                  fontweight="normal", color=INK)
    for ax in (axT, axB):
        ax.set_yscale("log")
        st.no_minor_labels(ax, "y")
    axT.set_ylim(*Y_TOP)
    axB.set_ylim(*Y_BOT)
    axT.set_xlim(-0.25, 5.25)
    # break look: top axes lose the bottom spine, bottom axes own the x labels
    axT.spines["bottom"].set_visible(False)
    axT.tick_params(axis="x", bottom=False, labelbottom=False)

    # group separator + group headers on the top segment
    for ax in (axT, axB):
        ax.axvline(3.85, color=PAL["hair"], lw=0.7, ls=(0, (2, 2)), zorder=1)
    axT.text(1.5, 8.6, "one-shot", fontsize=5.4, color=MUTED, ha="center",
             va="center")
    axT.text(4.6, 8.6, "sustained", fontsize=5.4, color=PAL["accent"],
             ha="center", va="center")

    # no-effect reference at RR = 1 (top segment only)
    axT.axhline(1.0, color=PAL["hair"], lw=0.7, ls=(0, (3, 2)), zorder=1)
    axT.text(0.08, 1.05, "RR = 1", fontsize=5.2, color=MUTED,
             ha="left", va="bottom", zorder=2)
    axB.text(3.5, 0.033, "harmful", fontsize=5.5, color=PAL["accent"],
             ha="center", fontweight="bold")

    # series drawn on BOTH segments; each axes clips at the break
    for ax in (axT, axB):
        for pt, col, mfc, mew in (("P3", PAL["grey"], "white", 0.7),
                                  ("P2", PAL["control"], PAL["control"], 0.5)):
            mk, ls = st.mstyle(pt)
            xs, ys = [], []
            for si, s in enumerate(SCHED):
                r = next((r for r in piv if r["condition"] == cname
                          and r["schedule"] == s and r["point"] == pt), None)
                if r is None:
                    continue
                xs.append(XPOS[si]); ys.append(st.f(r["rr_vs_c0"]))
            ax.plot(xs, ys, ls, color=col, lw=1.0, marker=mk, ms=3.4,
                    markerfacecolor=mfc, markeredgecolor=col, markeredgewidth=mew,
                    zorder=2.5 if pt == "P3" else 3.0)
    # direct series labels at the sustained end (bottom segment)
    for pt, col, dy, va in (("P2", PAL["control"], 4.0, "bottom"),
                            ("P3", PAL["grey"], -4.0, "top")):
        r = next((r for r in piv if r["condition"] == cname
                  and r["schedule"] == "UNIFORM-2" and r["point"] == pt), None)
        axB.annotate(pt, xy=(XPOS[-1], st.f(r["rr_vs_c0"])), xytext=(4.0, dy),
                     textcoords="offset points", ha="left", va=va,
                     fontsize=5.5, color=col, zorder=4)

    # segment ticks
    axT.set_yticks([0.5, 1, 2, 5, 10])
    axT.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    axB.set_yticks([0.005, 0.01, 0.02, 0.05])
    axB.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    axB.set_xticks(XPOS)
    axB.set_xticklabels(SCHED, rotation=32, ha="right", fontsize=5.8)

    # break marks on the left spine (dash sizes match across the two heights)
    dT, dB = 0.014, 0.040
    axT.plot([-dT, dT], [-dT, dT], transform=axT.transAxes, color=INK,
             clip_on=False, lw=0.7)
    axB.plot([-dB, dB], [1 - dB, 1 + dB], transform=axB.transAxes, color=INK,
             clip_on=False, lw=0.7)

    if i == 0:
        axT.set_ylabel("risk ratio  C0 / arm")
        # coordinates once, in the first panel; the bottom segment's left side
        # is empty (the series only enters it at x ~ 4.2), so the notes stack
        # vertically there and never touch the break marks or each other
        axB.text(0.02, 0.72, "P2 (3001,37,66)", transform=axB.transAxes,
                 ha="left", va="center", fontsize=5.0, color=PAL["control"], zorder=4)
        axB.text(0.02, 0.44, "P3 (4001,41,82)", transform=axB.transAxes,
                 ha="left", va="center", fontsize=5.0, color=PAL["grey"], zorder=4)
        axB.text(0.02, 0.14, "n = 50,000 trials per point",
                 transform=axB.transAxes, ha="left", va="center",
                 fontsize=5.0, color=MUTED)

# ---------------------------------------------------------------------------
# (d) round controls at P1' (RAND): effect-size caterpillar
# ---------------------------------------------------------------------------
ax = fig.add_subplot(gs[0, 3])
st.panel(ax, "d")
ax.set_xscale("log"); st.no_minor_labels(ax, "x")
rc = [r for r in st.load("t1_round_controls.csv") if r["condition"] == "RAND"]
by = {r["arm"]: r for r in rc}
order = ["FRO-2", "R2one", "FRONEG", "R2plus"]
xlab = {"FRO-2": "+2 round 1", "R2one": "+2 round 2",
        "FRONEG": "-1 round 1", "R2plus": "+2 rounds 2+"}
col = {"FRO-2": PAL["hero"], "R2one": PAL["benign"],
       "FRONEG": PAL["accent"], "R2plus": PAL["accent"]}
xl = (0.008, 14.0)
ax.axvspan(xl[0], 1.0, facecolor=PAL["accent"], alpha=0.05, lw=0, zorder=0.3)
ax.axvspan(1.0, xl[1], facecolor=PAL["hero"], alpha=0.05, lw=0, zorder=0.3)
ax.axvline(1.0, color=PAL["hair"], lw=0.8, ls=(0, (3, 2)), zorder=1)
ys = list(range(len(order)))[::-1]
for y, n in zip(ys, order):
    r = by[n]
    p, lo, hi = st.f(r["rr_vs_c0"]), st.f(r["rr_lo"]), st.f(r["rr_hi"])
    mk, _ = st.mstyle(n)
    ax.plot([lo, hi], [y, y], color=col[n], lw=1.0, solid_capstyle="butt",
            zorder=2)
    ax.plot([p], [y], mk, color=col[n], ms=4.4, zorder=3,
            markeredgecolor="white", markeredgewidth=0.5)
    ax.text(hi * 1.14, y, f"{p:.3g}", fontsize=5.6, color=col[n], ha="left",
            va="center", zorder=4)
ax.set_yticks(ys)
ax.set_yticklabels([xlab[n] for n in order], fontsize=5.8)
for tick, n in zip(ax.get_yticklabels(), order):
    tick.set_color(col[n])
ax.set_ylim(-0.55, 3.75)
ax.set_xlim(*xl)
ax.xaxis.set_major_locator(ticker.FixedLocator([0.01, 0.1, 1, 10]))
ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
ax.set_xlabel("risk ratio  C0 / arm\n(95% key-cluster CI)")
ax.text(0.012, 3.30, "worse", fontsize=5.4, color=PAL["accent"], ha="left",
        va="center", fontweight="bold")
ax.text(5.5, 3.30, "better", fontsize=5.4, color=PAL["hero"], ha="center",
        va="center", fontweight="bold")
ax.text(1.03, 3.30, "C0 = 1", fontsize=5.2, color=MUTED, ha="left",
        va="center")
ax.text(0.012, -0.42, "n = 92 keys", fontsize=5.2, color=MUTED, ha="left",
        va="center")

st.save(fig, "fig4_temporal_dissociation")
