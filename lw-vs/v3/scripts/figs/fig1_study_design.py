#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Figure 1 (v3 set, nature-figure pass) -- study design; schematic-led composite,
double column (7.16 x 2.0 in):

SHIPPING NOTE (2026-10-17): the v3 manuscript ships the
figure_research/complete_set rendering of this figure. Do not re-run this
script into v3/figures; it would overwrite the shipped art.
  (a) paired-protocol flow: key H + error e -> syndrome s = He^T (one draw) ->
      the identical instance (H, e, s) into both arm chips (C0 control, FRO-2
      hero) -> outcomes aggregated per key;
  (b) threshold schedule step plot: C0 vs FRO-2 over iterations 0..6, one-shot
      +2 in round 1 only and back to tau from round 2 on (identical to C0),
      shaded "identical thereafter" region, one annotation;
  (c) measurement streams by role (thin rules): role / keys / errors per key
      for the formal pool, the fresh-key gate, the expanded confirmation and
      the held-out rule check.

v3 change vs the 10.12 render: panel (c) used to be the evidence-tier table
(tier / role / scale / authority).  The v3 manuscript carries no tier
framework, so the panel is rebuilt as the run-streams table the v3 caption
already describes.

Data mapping: the threshold panel is the normalised schematic (tau vs tau+2;
no CSV supplies these); the streams table carries manuscript values only --
278 = 92 RAND + 94 TYPE-I + 92 NCW keys, 3,000 errors per key (834,000
decodings per arm); the fresh-key gate 212 keys x 3,000 (636,000 per arm);
the expanded confirmation 50 keys x 1,000 errors at P2 and P3; the held-out
rule check 48 keys x 1,000 errors at P4.  No value is invented; no
measurement is recomputed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.text import Text

import style_v3 as st

# Texts (with their allowed axis-fraction x-bands) that the QA pass checks for
# horizontal overflow inside their own panel; filled while the figure is built.
_QA_BANDS = []


# ---------------------------------------------------------------------------
# small drawing helpers
# ---------------------------------------------------------------------------
def _flow_box(ax, y0, h, x0=0.02, w=0.96):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.02",
                                fc=st.PAL["surface"], ec=st.PAL["hair"], lw=0.6,
                                zorder=1))


def _flow_arrow(ax, x, y0, y1):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>",
                                 mutation_scale=5.5, lw=0.7, color=st.MUTED,
                                 shrinkA=0.0, shrinkB=0.0, zorder=2))


def _chip(ax, x0, y0, w, h, label, color):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h,
                                boxstyle="round,pad=0.006,rounding_size=0.02",
                                fc="white", ec=color, lw=1.0, zorder=3))
    ax.text(x0 + w / 2.0, y0 + h / 2.0, label, ha="center", va="center",
            fontsize=6.6, color=color, fontweight="bold", zorder=4)


# ---------------------------------------------------------------------------
# (a) paired-protocol flow
# ---------------------------------------------------------------------------
def _panel_a(ax):
    ax.axis("off")
    st.panel(ax, "a")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    # step 1 -- one draw of the instance
    _flow_box(ax, 0.730, 0.270)
    ax.text(0.50, 0.930, "key $H$  +  error $e$", ha="center", va="center",
            fontsize=6.6, color=st.INK, fontweight="bold")
    ax.text(0.50, 0.810, "syndrome  $s = H e^{\\top}$,  one draw", ha="center",
            va="center", fontsize=5.9, color=st.MUTED)

    _flow_arrow(ax, 0.50, 0.729, 0.664)

    # step 2 -- the identical instance enters both arms
    _flow_box(ax, 0.410, 0.253)
    ax.text(0.50, 0.600, "identical instance  $(H, e, s)$", ha="center",
            va="center", fontsize=6.6, color=st.INK, fontweight="bold")
    _chip(ax, 0.060, 0.430, 0.400, 0.115, "C0", st.C0)
    _chip(ax, 0.540, 0.430, 0.400, 0.115, "FRO-2", st.FRO2)

    _flow_arrow(ax, 0.26, 0.408, 0.345)
    _flow_arrow(ax, 0.74, 0.408, 0.345)

    # step 3 -- per-key aggregation
    _flow_box(ax, 0.230, 0.113)
    ax.text(0.50, 0.2865, "outcomes aggregated per key", ha="center",
            va="center", fontsize=6.4, color=st.INK, fontweight="bold")

    # protocol footnotes (contract: keep both statements)
    ax.text(0.50, 0.160, "resampling unit = key, not the individual error draw",
            ha="center", va="center", fontsize=5.7, color=st.MUTED)
    ax.text(0.50, 0.090, "true $e$ used for instrumentation only",
            ha="center", va="center", fontsize=5.7, color=st.MUTED)


# ---------------------------------------------------------------------------
# (b) threshold timing
# ---------------------------------------------------------------------------
def _panel_b(ax):
    st.panel(ax, "b")

    it = list(range(0, 7))
    thr_c0 = [1.0] * len(it)                      # normalised tau
    # FRO-2 is a ONE-SHOT offset: +2 in round 1 only, then the schedule drops
    # back to tau and is identical to C0 for every later round.
    thr_fr = [1.0, 2.0] + [1.0] * (len(it) - 2)

    # "identical thereafter" region: no further offset after round 1
    ax.axvspan(1, 6, facecolor=st.GRID, alpha=0.5, lw=0.0, zorder=0)

    mk_c0, ls_c0 = st.mstyle("C0")
    mk_fr, ls_fr = st.mstyle("FRO-2")
    ax.step(it, thr_c0, where="post", color=st.C0, lw=1.2, marker=mk_c0,
            ms=2.8, zorder=2)
    # FRO-2: dashed where it coincides with C0, so the shared segment reads as
    # both schedules on one path; the round-1 episode is overdrawn solid.
    ax.step(it, thr_fr, where="post", color=st.FRO2, lw=1.0, ls=(0, (3, 1.6)),
            marker=mk_fr, ms=2.6, zorder=4)
    ax.step(it[:2], thr_fr[:2], where="post", color=st.FRO2, lw=1.5, zorder=5)

    # single annotation for the offset: points at the round-1 jump
    ax.annotate("one-shot: $+2$ in round 1 only", xy=(1.0, 2.03),
                xytext=(1.05, 2.95), ha="left", va="center", fontsize=5.9,
                color=st.FRO2,
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color=st.FRO2,
                                shrinkA=1.0, shrinkB=1.0))

    # direct labels (no legend box over the data)
    ax.text(5.90, 1.12, "C0", ha="right", va="bottom", fontsize=6.2,
            color=st.C0)
    ax.text(0.48, 2.12, "FRO-2", ha="center", va="bottom", fontsize=6.2,
            color=st.FRO2)
    ax.text(3.55, 1.12, "identical thereafter", ha="center", va="bottom",
            fontsize=5.8, color=st.MUTED)

    ax.set_yticks([1, 2])
    ax.set_yticklabels(["$\\tau$", "$\\tau\\!+\\!2$"])
    ax.set_xticks(it)
    ax.set_xlabel("iteration $i$")
    ax.set_ylabel("threshold $\\tau$")
    ax.set_xlim(-0.15, 6.1)
    ax.set_ylim(0.55, 3.35)


# ---------------------------------------------------------------------------
# (c) run streams as a stage timeline (no tier language; all values in text)
# ---------------------------------------------------------------------------
def _panel_c(ax):
    ax.axis("off")
    st.panel(ax, "c")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    Y_LINE = 0.52
    # the protocol as one directed line; stages alternate above/below
    ax.add_patch(FancyArrowPatch((0.03, Y_LINE), (0.985, Y_LINE),
                                 arrowstyle="-|>", mutation_scale=6.5, lw=0.9,
                                 color=st.PAL["hair"], shrinkA=0.0, shrinkB=0.0,
                                 zorder=1))
    stages = [
        (0.13, True, "screening", "9 schedules"),
        (0.31, False, "frozen gate", "212 keys $\\times$ 3,000"),
        (0.52, True, "formal pool", "278 keys $\\times$ 3,000"),
        (0.71, False, "confirmation", "50 $\\times$ 1,000, P2 & P3"),
        (0.89, True, "held-out check", "48 $\\times$ 1,000 (P4)"),
    ]
    for x, above, name, sub in stages:
        ax.plot([x], [Y_LINE], "o", ms=3.0, color=st.INK, zorder=3)
        if above:
            ym, ys_, va_main, va_sub = 0.635, 0.715, "bottom", "bottom"
        else:
            ym, ys_, va_main, va_sub = 0.395, 0.315, "top", "top"
        t1 = ax.text(x, ym, name, fontsize=5.6, color=st.INK, ha="center",
                     va=va_main, fontweight="bold", zorder=4)
        t2 = ax.text(x, ys_, sub, fontsize=5.0, color=st.MUTED, ha="center",
                     va=va_sub, zorder=4)
        _QA_BANDS.append((ax, t1, name, (x - 0.16, x + 0.16)))
        _QA_BANDS.append((ax, t2, sub, (x - 0.17, x + 0.17)))


# ---------------------------------------------------------------------------
# QA pass: text overflow / overlap report (printed, never drawn)
# ---------------------------------------------------------------------------
def _qa(fig):
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    texts = [t for t in fig.findobj(Text)
             if t.get_visible() and t.get_text().strip()
             and t.get_fontsize() > 0 and t.axes is not None]
    boxes = []
    for t in texts:
        try:   # base-class extent: for Annotation this excludes the arrow
            bb = Text.get_window_extent(t, rend)
        except Exception:
            bb = t.get_window_extent(rend)
        boxes.append((t, bb))

    fw, fh = fig.canvas.get_width_height()
    out = [t.get_text() for t, bb in boxes
           if bb.x0 < -0.5 or bb.y0 < -0.5 or bb.x1 > fw + 0.5 or bb.y1 > fh + 0.5]
    print(f"QA outside canvas: {out if out else 'none'}")

    ovl = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i][1], boxes[j][1]
            w = min(a.x1, b.x1) - max(a.x0, b.x0)
            h = min(a.y1, b.y1) - max(a.y0, b.y0)
            if w > 0 and h > 0 and w * h > 4:
                fa = boxes[i][0].get_text()[:28]
                fb = boxes[j][0].get_text()[:28]
                ovl.append(f"{fa!r}<->{fb!r} ({w * h:.0f}px2)")
    print("QA overlaps:")
    for s in ovl:
        print("   ", s)
    if not ovl:
        print("    none")

    bad = []
    for ax, t, s, (lo, hi) in _QA_BANDS:
        try:
            bb = Text.get_window_extent(t, rend)
        except Exception:
            bb = t.get_window_extent(rend)
        x0 = ax.transAxes.transform((lo, 0.0))[0]
        x1 = ax.transAxes.transform((hi, 0.0))[0]
        if bb.x0 < x0 - 0.5 or bb.x1 > x1 + 0.5:
            bad.append(f"{s!r} [{bb.x0:.0f},{bb.x1:.0f}] vs band [{x0:.0f},{x1:.0f}]")
    print("QA table cells inside column bands:" )
    for s in bad:
        print("    BAND", s)
    if not bad:
        print("    all inside")


def fig1_study_design():
    fig = plt.figure(figsize=(st.DBL_W, 2.0), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.22, 0.90, 1.28], wspace=0.28)

    _panel_a(fig.add_subplot(gs[0, 0]))
    _panel_b(fig.add_subplot(gs[0, 1]))
    _panel_c(fig.add_subplot(gs[0, 2]))

    _qa(fig)
    st.save(fig, "fig1_study_design")


if __name__ == "__main__":
    fig1_study_design()
