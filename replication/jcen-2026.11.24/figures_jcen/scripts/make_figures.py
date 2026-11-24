# -*- coding: utf-8 -*-
"""Top-journal redraw of the seven JCEN main figures.

Design contract
---------------
* Figure evidence and reproduction steps: see the release README.md.
* Evidence chain: every number comes from the frozen CSVs in ../source_data,
  copied byte-for-byte from the manuscript's archived analysis outputs.
* Archetype: schematic-led composite (Fig. 1), paired slope/forest (Fig. 2),
  grouped bars (Fig. 3), composite bar + forest + histogram (Fig. 4),
  two-panel response curve (Fig. 5), faceted forest (Fig. 6),
  three-panel scope figure (Fig. 7).
* Backend: matplotlib (Python); vector PDF/SVG for the journal, PNG for review.
* Export contract: canvases at the printed size of the manuscript figure
  boxes (160 mm text width), Type-42 embedded fonts, editable SVG text,
  white background, type never below 8 pt.

Colour system ("ink & earth", print-safe):
    navy  = baseline / C0 / original sample / P1'
    ochre = raised threshold / FRO-2 / intervention / fresh sample
    brick = adverse side (permissive offsets, NCW-aware comparator)
    teal  = NCW-shallow condition / P2 transfer
    plum  = TYPE-I condition / P3 transfer
Every fill carries a darker same-hue stroke; series are additionally separated
by marker shape and panel, so colour is never the only channel.  No gridlines:
values are labelled directly, and reference rules mark only the identity (1.0)
and the zero offset.

Run:  python make_figures.py            (all figures)
      FIGS=Fig3,Fig5 python make_figures.py
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
from matplotlib.ticker import NullLocator

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "source_data"
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)

# --------------------------------------------------------------- palette ---
INK = "#1D1B18"
BODY = "#2E2B27"
MUTED = "#6C665D"
RULE = "#D9D3C9"
NAVY, NAVY_D = "#2A4A73", "#182F4B"
AMBER, AMBER_D = "#C0862D", "#855615"
BRICK, BRICK_D = "#A65240", "#793628"
TEAL, TEAL_D = "#3F756E", "#2A4F4A"
PLUM, PLUM_D = "#7A5A7A", "#523B52"
STONE, STONE_D = "#C7C0B4", "#8E877B"

W_NAVY, W_AMBER, W_BRICK, W_TEAL = "#E9EEF4", "#F8EFDD", "#F7E8E3", "#E7EFED"

CONDS = ["RAND", "TYPE-I", "NCW-shallow"]
SHORT = {"RAND": "RAND", "TYPE-I": "TYPE-I", "NCW-shallow": "NCW"}
COND_STYLE = {   # colour, dark stroke, marker, line style
    "RAND": (NAVY, NAVY_D, "o", "-"),
    "TYPE-I": (PLUM, PLUM_D, "s", (0, (5, 2))),
    "NCW-shallow": (TEAL, TEAL_D, "^", (0, (1.4, 1.4))),
}


# ----------------------------------------------------------------- style ---
def setup():
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "mathtext.fontset": "stix",
        "font.size": 8.0,
        "axes.titlesize": 8.4,
        "axes.labelsize": 8.4,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "axes.linewidth": 0.6,
        "axes.edgecolor": "#4A453E",
        "axes.labelcolor": BODY,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "xtick.major.size": 2.4,
        "ytick.major.size": 2.4,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.color": "#4A453E",
        "ytick.color": "#4A453E",
        "xtick.labelcolor": BODY,
        "ytick.labelcolor": BODY,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "lines.linewidth": 1.1,
        "lines.markersize": 4.0,
        "legend.frameon": False,
        "legend.fontsize": 8.0,
        "legend.handlelength": 1.8,
        "legend.handletextpad": 0.55,
        "legend.columnspacing": 1.7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": None,
    })


def load(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def row(rows, **kw):
    return next(r for r in rows if all(r[k] == v for k, v in kw.items()))


def val(rows, key, **kw):
    return float(row(rows, **kw)[key])


def panel(ax, letter, title="", dx=0.0, dy=1.045):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=9.2,
            fontweight="bold", va="bottom", ha="left", color=INK,
            clip_on=False)
    if title:
        ax.text(dx + 0.058, dy + 0.004, title, transform=ax.transAxes,
                fontsize=8.2, va="bottom", ha="left", color=INK, clip_on=False)


def bare(ax, axis="y"):
    getattr(ax, f"{axis}axis").set_minor_locator(NullLocator())


def text_qa(fig, stem):
    """Report text-text overlaps and out-of-page text (units: pt)."""
    fig.canvas.draw()
    ren = fig.canvas.get_renderer()
    k = 72.0 / fig.dpi
    items = list(fig.texts)
    for ax in fig.axes:
        if ax.get_title():
            items.append(ax.title)
        items.extend(ax.texts)
        for axis in (ax.xaxis, ax.yaxis):
            lab = axis.get_label()
            if lab.get_text():
                items.append(lab)
            items.extend([t for t in axis.get_ticklabels() if t.get_text()])
        leg = ax.get_legend()
        if leg is not None:
            items.extend([t for t in leg.get_texts() if t.get_text()])
    for leg in getattr(fig, "legends", []):
        items.extend([t for t in leg.get_texts() if t.get_text()])
    boxes, seen = [], set()
    for t in items:
        bb = t.get_window_extent(ren)
        if bb.width <= 0 or bb.height <= 0 or id(t) in seen:
            continue
        seen.add(id(t))
        boxes.append((t, bb))
    W = fig.get_size_inches()[0] * 72.0
    H = fig.get_size_inches()[1] * 72.0
    issues = []
    for t, bb in boxes:
        x0, x1 = bb.x0 * k, bb.x1 * k
        y0, y1 = (fig.bbox.height - bb.y1) * k, (fig.bbox.height - bb.y0) * k
        if x0 < -0.5 or x1 > W + 0.5 or y0 < -0.5 or y1 > H + 0.5:
            issues.append("OOB %r  x %.1f-%.1f  y %.1f-%.1f"
                          % (t.get_text(), x0, x1, y0, y1))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            t1, b1 = boxes[i]
            t2, b2 = boxes[j]
            dx = min(b1.x1, b2.x1) - max(b1.x0, b2.x0)
            dy = min(b1.y1, b2.y1) - max(b1.y0, b2.y0)
            if dx > 0.8 and dy > 0.8:
                issues.append("HIT %r x %r  (%.1f x %.1f pt)"
                              % (t1.get_text(), t2.get_text(), dx * k, dy * k))
    tag = "OK" if not issues else "%d issue(s)" % len(issues)
    print("[qa] %s: %s" % (stem, tag))
    for s in issues:
        print("     ", s)


def save(fig, stem):
    text_qa(fig, stem)
    fig.savefig(OUT / f"{stem}.pdf")
    fig.savefig(OUT / f"{stem}.eps", dpi=600)
    fig.savefig(OUT / f"{stem}.svg")
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    plt.close(fig)
    print("saved", stem)


def bar(ax, x, v, fill, edge, w=0.36, label=None):
    return ax.bar(x, v, width=w, color=fill, edgecolor=edge, linewidth=0.65,
                  label=label, zorder=3)


def hforest(ax, y, v, lo, hi, fill, edge, marker="o", ms=4.6, mfc=None):
    ax.errorbar(v, y, xerr=[[max(v - lo, 0)], [max(hi - v, 0)]], fmt=marker,
                color=fill, mec=edge, mew=0.75, ms=ms, mfc=mfc or fill,
                ecolor=edge, elinewidth=0.9, capsize=2.0, capthick=0.9,
                zorder=3, linestyle="none")


def vforest(ax, x, v, lo, hi, fill, edge, marker="o", ms=4.8, mfc=None):
    ax.errorbar(x, v, yerr=[[max(v - lo, 0)], [max(hi - v, 0)]], fmt=marker,
                color=fill, mec=edge, mew=0.75, ms=ms, mfc=mfc or fill,
                ecolor=edge, elinewidth=0.9, capsize=2.0, capthick=0.9,
                zorder=3, linestyle="none")


def tint(color, amount):
    """Blend a colour towards white (EPS cannot store alpha)."""
    rgb = mcolors.to_rgb(color)
    return tuple(1 - (1 - c) * amount for c in rgb)


def logfmt(ax, axis="y"):
    bare(ax, axis)


# ------------------------------------------------------------------ Fig 1 ---
def fig1():
    """Restyle the manuscript's original shared-input, four-branch schematic."""
    width, height = 399.12, 198.0  # 0.88 of the 160 mm manuscript width, in pt
    fig = plt.figure(figsize=(width / 72, height / 72))
    # Keep the original relative column coordinates; font sizes remain in pt.
    ax = fig.add_axes((0, 0, 1, 1), xlim=(0, 443.26), ylim=(height, 0))
    ax.set_axis_off()
    ax.set_xticks([])
    ax.set_yticks([])

    data = ("#F4F2EE", "#8A8277")
    process = (W_NAVY, NAVY)
    raised = (W_AMBER, AMBER_D)
    optional = ("#D8E3F0", NAVY)
    bypass = ("#FFFFFF", "#8A8277")
    wire = "#4A453E"
    labels_in_boxes = []

    def label(x, y, value, size=8.2, *, bold=False, color=INK, ha="center", bounds=None):
        artist = ax.text(x, y, value, fontsize=size, ha=ha, va="center",
                         weight="bold" if bold else "normal", color=color, zorder=7)
        if bounds is not None:
            labels_in_boxes.append((artist, bounds))

    def box(x, y, w, h, colors, *, radius=2.5, z=2, dashed=False):
        fill, stroke = colors
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                    boxstyle=f"round,pad=0,rounding_size={radius}",
                                    facecolor=fill, edgecolor=stroke, linewidth=0.7,
                                    linestyle=(0, (3, 2)) if dashed else "solid", zorder=z))
        return x, y, w, h

    def line(*points, color=wire, width=0.7, dashed=False):
        x, y = zip(*points)
        ax.plot(x, y, color=color, linewidth=width, solid_capstyle="butt",
                linestyle=(0, (3, 2)) if dashed else "solid", zorder=3)

    def arrow(x0, y, x1):
        ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>",
                                    mutation_scale=7.2, shrinkA=0, shrinkB=0,
                                    linewidth=0.7, color=wire, zorder=4))

    with mpl.rc_context({"mathtext.fontset": "custom", "mathtext.rm": "Arial",
                         "mathtext.it": "Arial:italic", "mathtext.fallback": None}):
        columns = ((9, 75, "Matched input"), (102, 167, "Initial flips"),
                   (193, 251, "Post-step"), (275, 351, "Finish decoding"),
                   (375, 434, "Final DFR"))
        for x0, x1, name in columns:
            label((x0 + x1) / 2, 13, name, 8.6, bold=True)
            line((x0, 22), (x1, 22), color=RULE)

        box(9, 49, 66, 58, data)
        label(42, 60, "Same trials", 8.7, bold=True)
        for x, symbol in ((15, "$H$"), (34, "$e$"), (53, "$s$")):
            chip = box(x, 71, 16, 17, bypass, radius=1.5, z=3)
            label(x + 8, 79.5, symbol, 9.2, bounds=chip)
        label(42, 97, "All variants", color=MUTED)
        label(42, 116, "Decoder inputs:", color=MUTED)
        label(42, 128, r"$H$ and $s$", color=MUTED)
        line((75, 78), (87, 78))
        line((87, 51), (87, 105))

        # One backdrop for the common rules, but the four rails never merge.
        box(275, 29, 76, 98, process, radius=3, z=1)
        for cy, name, offset, nodes, colors in (
            (51, "Baseline", "0", ((40, "Off"), (62, "On")), process),
            (105, "Raised", "+2", ((94, "Off"), (116, "On")), raised),
        ):
            block = box(102, cy - 16, 65, 32, colors)
            label(134.5, cy - 6, name, 8.8, bold=True, bounds=block)
            label(134.5, cy + 7, f"Offset {offset}", bounds=block)
            arrow(87, cy, 102)
            line((167, cy), (180, cy))
            line((180, nodes[0][0]), (180, nodes[-1][0]))
            for y, mode in nodes:
                enabled = mode == "On"
                branch = box(193, y - 8, 58, 16, optional if enabled else bypass)
                label(222, y, mode, 8.6, bold=enabled, bounds=branch)
                arrow(180, y, 193)
                result = box(375, y - 9.5, 59, 19, data)
                suffix = "post" if enabled else "plain"
                label(404.5, y - 0.4, rf"$f_{{\mathrm{{{suffix}}},{offset}}}$", 11.5, bounds=result)
                arrow(251, y, 375)
        label(313, 78, "Same rules", 8.6, bold=True, color=NAVY_D)

        # The original dashed callout is a magnified detail, not another rail.
        line((222, 124), (222, 132), color=NAVY, dashed=True)
        box(162, 132, 272, 43, ("#FAFBFD", NAVY), radius=3, dashed=True)
        label(174, 142, "Post-step on: detail at both offsets", 8.5, bold=True, ha="left")
        for x, name in ((174, "Black re-check"), (312, "Gray step")):
            block = box(x, 152, 110, 17, optional)
            label(x + 55, 160.5, name, 8.5, bounds=block)
        arrow(284, 160.5, 312)

        for y, colors, name in ((139, data, "Trial / outcome"),
                                (153, process, "Bit-flipping decoder"),
                                (167, optional, "Optional operation")):
            box(12, y - 4, 9, 8, colors, radius=1)
            label(27, y, name, ha="left", color=MUTED)

        line((9, 179), (434, 179), color=RULE)
        label(9, 189, "Held fixed", 8.5, bold=True, ha="left")
        label(61, 189, "Base decoder  ·  Stopping rule  ·  Main-round budget  ·  Later-round threshold rule",
              ha="left", color=MUTED)

        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        for artist, (x, y, w, h) in labels_in_boxes:
            extent = artist.get_window_extent(renderer).transformed(ax.transData.inverted())
            assert x + 1 <= extent.xmin <= extent.xmax <= x + w - 1, artist.get_text()
            assert y <= extent.ymin <= extent.ymax <= y + h, artist.get_text()
        save(fig, "Fig1")


# ------------------------------------------------------------------ Fig 2 ---
def fig2():
    """The offset effect flips sign when the post-step is switched on."""
    rows = load("factor_offset_contrasts.csv")
    samples = {"Original": (NAVY, NAVY_D, "o"),
               "Fresh": (AMBER, AMBER_D, "s")}
    W, H = 440.0, 146.0
    fig, axs = plt.subplots(1, 2, figsize=(W / 72.0, H / 72.0), sharey=True)
    fig.subplots_adjust(left=0.190, right=0.988, bottom=0.215, top=0.780,
                        wspace=0.26)
    dodge = {"Original": -0.13, "Fresh": 0.13}
    for i, (ax, (point, name)) in enumerate(zip(axs, (("P1prime", "P1'"),
                                                      ("P2", "P2")))):
        ax.set_xlim(-2.4, 5.4)
        ax.set_ylim(1.62, -0.62)
        ax.axvline(0, color="#8C857A", lw=0.9, ls=(0, (3, 2.4)), zorder=2)
        ax.set_yticks((0, 1))
        ax.set_yticklabels(("Post-step off", "Post-step on"), fontsize=8.4)
        ax.tick_params(axis="y", length=0, pad=6)
        ax.set_xticks((-2, 0, 2, 4))
        ax.set_xticks((-1, 1, 3), minor=True)
        ax.tick_params(axis="x", which="minor", length=0)
        ax.tick_params(axis="x", labelsize=8.2)
        ax.text(-0.015, 1.075, "ab"[i], transform=ax.transAxes,
                fontweight="bold", fontsize=9.4, color=INK, va="bottom")
        ax.text(0.035, 1.085, name, transform=ax.transAxes, fontsize=8.8,
                color=INK, va="bottom", fontweight="bold")
        for s in ("Original", "Fresh"):
            c, ce, mk = samples[s]
            off = row(rows, point=point, sample=s, postprocessing="Off")
            on = row(rows, point=point, sample=s, postprocessing="On")
            xo = float(off["difference_per_1000"])
            xn = float(on["difference_per_1000"])
            # slope connector: the same sample followed across the two policies
            ax.plot([xo, xn], [0 + dodge[s], 1 + dodge[s]],
                    color=tint(ce, 0.55), lw=0.8, zorder=1.8)
            for r in (off, on):
                yy = 0 if r["postprocessing"] == "Off" else 1
                v, lo, hi = (float(r[k]) for k in
                             ("difference_per_1000", "ci95_low", "ci95_high"))
                hforest(ax, yy + dodge[s], v, lo, hi, c, ce, marker=mk, ms=5.2)
    handles = [Line2D([], [], marker=mk, color=c, mec=ce, mew=0.75, ls="",
                      markersize=5.2, label=f"{s} sample")
               for s, (c, ce, mk) in samples.items()]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.52, 0.998),
               ncol=2, columnspacing=2.6, fontsize=8.4)
    fig.text(0.52, 0.045, "Change in failures per 1,000 decodes (+2 minus 0); "
             "left of zero = fewer failures", ha="center", fontsize=8.0,
             color=BODY)
    save(fig, "Fig2")


# ------------------------------------------------------------------ Fig 3 ---
def fig3():
    """Raising the threshold empties the wrong-bit set, not the right-bit one."""
    rows = load("t1_mechanism_firstround.csv")
    W, H = 453.6, 152.0
    fig, axs = plt.subplots(1, 3, figsize=(W / 72.0, H / 72.0))
    fig.subplots_adjust(left=0.098, right=0.986, top=0.735, bottom=0.215,
                        wspace=0.44)
    metrics = (("mean_incorrect_first", "Incorrect flips"),
               ("mean_correct_first", "Correct flips"),
               ("mean_residual_r1", "Residual errors"))
    for i, (ax, (key, heading)) in enumerate(zip(axs, metrics)):
        x = np.arange(3)
        vals_by_arm = {}
        for arm, dx, fill, edge, lab in (("C0", -0.26, NAVY, NAVY_D, "C0"),
                                         ("FRO-2", 0.26, AMBER, AMBER_D, "FRO-2")):
            vals = [val(rows, key, condition=c, arm=arm) for c in CONDS]
            vals_by_arm[arm] = vals
            bars = bar(ax, x + dx, vals, fill, edge, w=0.40, label=lab)
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v * 1.012,
                        f"{v:.1f}", ha="center", va="bottom", fontsize=8.0,
                        color=BODY)
        vmax = max(vals_by_arm["C0"] + vals_by_arm["FRO-2"])
        ax.set_ylim(0, vmax * 1.36)
        for j, c in enumerate(CONDS):
            c0, fro = vals_by_arm["C0"][j], vals_by_arm["FRO-2"][j]
            ax.text(j, vmax * 1.305, f"{fro / c0:.2f}\u00d7", ha="center",
                    va="top", fontsize=8.6, fontweight="bold", color=INK)
        ax.set_xticks(x)
        ax.set_xticklabels([SHORT[c] for c in CONDS], fontsize=8.4)
        ax.set_yticks([t for t in ax.get_yticks() if t <= vmax * 1.36])
        ax.tick_params(axis="y", labelsize=8.2)
        ax.set_xlim(-0.50, 2.50)
        panel(ax, "abc"[i], heading, dx=0.0, dy=1.035)
        if i == 0:
            ax.set_ylabel("Mean positions per decode", fontsize=8.4,
                          labelpad=2.0)
    fig.legend(handles=[Patch(fc=NAVY, ec=NAVY_D, lw=0.65, label="C0"),
                        Patch(fc=AMBER, ec=AMBER_D, lw=0.65, label="FRO-2")],
               loc="upper center", bbox_to_anchor=(0.54, 0.995), ncol=2,
               handlelength=1.2, fontsize=8.4)
    fig.text(0.098, 0.045, "Ratios above bars: FRO-2 / C0   \u00b7   Each arm: "
             "20 keys \u00d7 1,000 decodes per condition", fontsize=8.0,
             color=MUTED)
    save(fig, "Fig3")


# ------------------------------------------------------------------ Fig 4 ---
def fig4():
    """The average gain is carried by a majority of keys, per condition."""
    agg, keys = load("t1_formal_main.csv"), load("t1_per_key.csv")
    W, H = 431.0, 252.0
    fig = plt.figure(figsize=(W / 72.0, H / 72.0))
    gs = fig.add_gridspec(2, 6, left=0.090, right=0.986, bottom=0.185,
                          top=0.900, hspace=0.62, wspace=0.90,
                          height_ratios=[1.0, 1.05])
    a, b = fig.add_subplot(gs[0, :3]), fig.add_subplot(gs[0, 3:])
    x = np.arange(3)
    for arm, dx, fill, edge, lab in (("c0", -0.19, NAVY, NAVY_D, "C0"),
                                     ("fro2", 0.19, AMBER, AMBER_D, "FRO-2")):
        vals = [val(agg, f"{arm}_dfr", condition=c) * 1e4 for c in CONDS]
        bars = bar(a, x + dx, vals, fill, edge, w=0.34, label=lab)
        for bb, v in zip(bars, vals):
            a.text(bb.get_x() + bb.get_width() / 2, v * 1.015, f"{v:.1f}",
                   ha="center", va="bottom", fontsize=8.0, color=BODY)
    a.set_xticks(x)
    a.set_xticklabels([SHORT[c] for c in CONDS], fontsize=8.2)
    a.set_ylabel("Failures per 10,000 decodes", fontsize=8.4, labelpad=2.0)
    a.set_ylim(0, 21.0)
    a.set_yticks([0, 4, 8, 12, 16])
    a.tick_params(axis="y", labelsize=8.2)
    panel(a, "a", "Absolute failure rate", dx=0.0, dy=1.10)
    a.legend(ncol=2, loc="upper left", borderaxespad=0.1, handlelength=1.2,
             fontsize=8.2)

    rr = [val(agg, "rr", condition=c) for c in CONDS]
    lo = [val(agg, "rr_lo", condition=c) for c in CONDS]
    hi = [val(agg, "rr_hi", condition=c) for c in CONDS]
    b.axhline(1, color="#8C857A", lw=0.9, ls=(0, (3, 2.4)), zorder=2)
    for xx, v, l, h in zip(x, rr, lo, hi):
        vforest(b, xx, v, l, h, AMBER, AMBER_D, marker="s", ms=5.2)
        b.text(xx, h + 0.30, f"{v:.2f}", ha="center", va="bottom", fontsize=8.4,
               fontweight="bold", color=INK)
    b.set_xticks(x)
    b.set_xticklabels([SHORT[c] for c in CONDS], fontsize=8.2)
    b.set_ylabel("Risk ratio C0 / FRO-2", fontsize=8.4, labelpad=2.0)
    b.set_ylim(0, 9.6)
    b.set_yticks([0, 2, 4, 6, 8])
    b.set_xlim(-0.62, 2.62)
    b.tick_params(axis="y", labelsize=8.2)
    panel(b, "b", "Relative effect, 95% CI", dx=0.0, dy=1.10)

    for i, c in enumerate(CONDS):
        ax = fig.add_subplot(gs[1, 2 * i:2 * i + 2])
        sub = [r for r in keys if r["condition"] == c]
        counts = Counter(int(r["c0_failures"]) - int(r["fro2_failures"])
                         for r in sub)
        assert sum(counts.values()) == int(row(agg, condition=c)["n_keys"])
        for arm in ("c0", "fro2"):
            assert sum(int(r[f"{arm}_failures"]) for r in sub) == \
                int(row(agg, condition=c)[f"{arm}_failures"])
        for d, n in sorted(counts.items()):
            fill, edge = ((AMBER, AMBER_D) if d > 0 else
                          (BRICK, BRICK_D) if d < 0 else (STONE, STONE_D))
            ax.bar(d, n, width=0.84, color=fill, edgecolor=edge,
                   linewidth=0.55, zorder=3)
        good = sum(n for d, n in counts.items() if d > 0)
        bad = sum(n for d, n in counts.items() if d < 0)
        ax.tick_params(labelsize=8.2)
        ax.set_xlim(-3.0, 11.0)
        ax.set_ylim(0, 46)
        ax.set_xticks([-2, 0, 2, 4, 6, 8, 10])
        ax.set_yticks([0, 10, 20, 30, 40])
        ax.set_xlabel("Failures avoided per key", fontsize=8.4, labelpad=2.0)
        panel(ax, "cde"[i], f"{SHORT[c]}  (n = {len(sub)})", dx=0.0,
              dy=1.075)
        ax.axvline(0, color="#8C857A", lw=0.7, ls=(0, (2, 2)), zorder=2)
        if i == 0:
            ax.set_ylabel("Number of keys", fontsize=8.4, labelpad=2.0)
        ax.text(0.97, 0.955, f"{good} improved\n{bad} worsened\n{counts[0]} tied",
                transform=ax.transAxes, ha="right", va="top", fontsize=8.0,
                color=BODY, linespacing=1.35)
    fig.text(0.090, 0.022, "Paired formal pool: 278 key\u2013condition units   "
             "\u00b7   3,000 decodes per key and schedule", fontsize=8.0,
             color=MUTED)
    save(fig, "Fig4")


# ------------------------------------------------------------------ Fig 5 ---
def fig5():
    """Threshold window: absolute DFR (a) and grouped risk ratios (b).

    Match the reference's offset x-axis and log-RR y-axis. Offset groups have
    three separated marker/interval columns; horizontal displacement is for
    readability only. The archived key-cluster intervals are unchanged.
    """
    rows = load("t1_offset_scan_p1p.csv")
    offsets = [-2, -1, 0, 1, 2, 3]
    arms = ["FRONEG2", "FRONEG", "C0", "FRO-1", "FRO-2", "FRO-3"]
    W, H = 453.54, 300.0
    fig = plt.figure(figsize=(W / 72.0, H / 72.0), facecolor="white")
    gs = fig.add_gridspec(1, 2, left=0.098, right=0.986, bottom=0.150,
                          top=0.845, width_ratios=[1.0, 1.0], wspace=0.40)
    a, b = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])

    a.axvspan(-2.45, 0, facecolor=W_BRICK, edgecolor="none", lw=0, zorder=0)
    a.axvspan(0, 3.45, facecolor=W_AMBER, edgecolor="none", lw=0, zorder=0)
    for ax in (a, b):
        ax.set_xlim(-2.45, 3.45)
        ax.set_xticks(offsets)
        ax.set_xticklabels(["\u22122", "\u22121", "0", "+1", "+2", "+3"],
                           fontsize=8.0)
        ax.set_xlabel("Round-one threshold offset", fontsize=8.4, labelpad=3.0)
        ax.tick_params(axis="x", length=2.6, width=0.6)
    a.axvline(0, color="#8C857A", lw=0.9, ls=(0, (2.6, 2.4)), zorder=1)
    a.text(0.03, 0.965, "permissive", transform=a.transAxes,
           fontsize=8.0, color=BRICK_D, ha="left", va="top")
    a.text(0.97, 0.965, "conservative", transform=a.transAxes,
           fontsize=8.0, color=AMBER_D, ha="right", va="top")

    # (a) absolute failure rate -------------------------------------------
    for c in CONDS:
        col, ce, mk, ls = COND_STYLE[c]
        vals = [val(rows, "dfr", condition=c, arm=arm) for arm in arms]
        a.plot(offsets, vals, color=col, marker=mk, ls=ls, lw=1.1, ms=4.6,
               mec=ce, mew=0.7, label=SHORT[c], zorder=3)
    a.set_yscale("log")
    a.set_ylim(6e-5, 1.25)
    a.set_yticks([1e-4, 1e-3, 1e-2, 1e-1, 1])
    a.set_yticklabels(["0.0001", "0.001", "0.01", "0.1", "1"], fontsize=8.0)
    a.set_ylabel("Absolute failure rate", fontsize=8.4, labelpad=2.0)
    logfmt(a)
    a.tick_params(axis="y", length=2.6, width=0.6)
    panel(a, "a", "", dx=-0.115, dy=1.035)

    # (b) grouped point–interval plot, following the reference -----------
    b.axvspan(-2.45, 0, facecolor=W_BRICK, edgecolor="none", lw=0, zorder=0)
    b.axvspan(0, 3.45, facecolor=W_AMBER, edgecolor="none", lw=0, zorder=0)
    b.axvline(0, color="#8C857A", lw=0.9, ls=(0, (2.6, 2.4)), zorder=1)
    b.axhline(1.0, color="#8C857A", lw=0.9, ls=(0, (3.0, 2.4)), zorder=1)
    b.set_yscale("log")
    b.set_ylim(7e-4, 24)
    b.set_yticks([1e-3, 1e-2, 1e-1, 1, 10])
    b.set_yticklabels(["0.001", "0.01", "0.1", "1", "10"], fontsize=8.0)
    b.set_ylabel("Risk ratio, C0 / variant", fontsize=8.4, labelpad=2.0)
    logfmt(b)
    b.tick_params(axis="y", length=2.6, width=0.6)
    dodge = {"RAND": -0.23, "TYPE-I": 0.0, "NCW-shallow": 0.23}
    for off, arm in zip(offsets, arms):
        if arm == "C0":
            # Shared definition (not a fitted estimate), so no interval.
            b.plot(0, 1, marker="o", ms=4.6, mfc="white", mec=MUTED,
                   mew=0.9, ls="none", zorder=3)
            continue
        for c in CONDS:
            col, ce, mk, _ = COND_STYLE[c]
            r = row(rows, condition=c, arm=arm)
            v, lo, hi = (float(r[k]) for k in ("rr_vs_c0", "rr_lo", "rr_hi"))
            vforest(b, off + dodge[c], v, lo, hi, col, ce, marker=mk, ms=4.4)
        rand = val(rows, "rr_vs_c0", condition="RAND", arm=arm)
        # Put annotations in a clear band above/below each entire group.
        if off == -1:
            near = min(val(rows, "rr_lo", condition=c, arm=arm) for c in CONDS)
            label_y, align = near / 1.35, "top"
        else:
            near = max(val(rows, "rr_hi", condition=c, arm=arm) for c in CONDS)
            label_y, align = near * 1.35, "bottom"
        label_x = off + 0.18 if off == offsets[0] else off
        b.text(label_x, label_y, f"{rand:.3g}", fontsize=8.0, color=NAVY_D,
               ha="center", va=align)
    panel(b, "b", "", dx=-0.13, dy=1.035)

    handles = [Line2D([], [], marker=mk, color=c, mec=ce, ls="", ms=5.0,
                      label=SHORT[k]) for k, (c, ce, mk, _) in COND_STYLE.items()]
    fig.legend(handles=handles, loc="upper center", ncol=3, fontsize=8.2,
               bbox_to_anchor=(0.53, 0.995), columnspacing=2.6,
               handletextpad=0.7)
    fig.text(0.53, 0.045, "Error bars: 95% key-cluster intervals. "
             "Numbers: RAND estimates. Open circle: C0.",
             ha="center", fontsize=8.0, color=MUTED)
    save(fig, "Fig5")


# ------------------------------------------------------------------ Fig 6 ---
def fig6():
    """Moving the raise to later rounds removes the harmful interaction."""
    primary = load("t1_round_controls.csv")
    expanded = load("t2_expanded_temporal.csv")
    W, H = 431.0, 268.0
    fig, axs = plt.subplots(1, 3, figsize=(W / 72.0, H / 72.0), sharey=True)
    fig.subplots_adjust(left=0.255, right=0.982, bottom=0.205, top=0.830,
                        wspace=0.12)
    prim_arms = ["FRO-2", "R2one", "FRONEG", "R2plus"]
    prim_lab = ["Round 1: +2", "Round 2: +2", "Round 1: \u22121",
                "Rounds 2+: +2"]
    extra = ["FRO-1", "FRO-2", "FRO-3", "R2-2", "UNIFORM-2"]
    extra_lab = ["Round 1: +1", "Round 1: +2", "Round 1: +3",
                 "Round 2: +2", "All rounds: +2"]
    y_prim = [8.4, 7.4, 6.4, 5.4]
    y_ext = [3.7, 2.7, 1.7, 0.7, -0.3]
    for i, (ax, c) in enumerate(zip(axs, CONDS)):
        ax.axvspan(0.0045, 1, facecolor=W_BRICK, edgecolor="none", lw=0, zorder=0)
        ax.axvline(1, color="#8C857A", lw=0.9, ls=(0, (3, 2.4)), zorder=2)
        ax.axhline(4.45, color=RULE, lw=0.75, zorder=2)
        for arm, y in zip(prim_arms, y_prim):
            r = row(primary, condition=c, arm=arm)
            hforest(ax, y, float(r["rr_vs_c0"]), float(r["rr_lo"]),
                    float(r["rr_hi"]), NAVY, NAVY_D, marker="D", ms=4.4)
        for arm, y in zip(extra, y_ext):
            for point, dy, fill, edge, mk, mfc in (
                    ("P2", 0.19, TEAL, TEAL_D, "o", TEAL),
                    ("P3", -0.19, "white", PLUM_D, "s", "white")):
                r = row(expanded, condition=c, point=point, decoder=arm)
                hforest(ax, y + dy, float(r["rr_vs_c0"]), float(r["rr_lo"]),
                        float(r["rr_hi"]), fill, edge, marker=mk, ms=4.0,
                        mfc=mfc)
        ax.set_xscale("log")
        ax.set_xlim(0.0045, 16)
        ax.set_ylim(-1.6, 9.6)
        ax.set_xticks([0.01, 0.1, 1, 10])
        ax.set_xticklabels(["0.01", "0.1", "1", "10"], fontsize=8.0)
        ax.tick_params(axis="x", length=2.6, width=0.6)
        logfmt(ax, "x")
        panel(ax, "abc"[i], SHORT[c], dx=-0.135, dy=1.025)
    axs[0].set_yticks(y_prim + y_ext)
    axs[0].set_yticklabels(prim_lab + extra_lab, fontsize=8.0)
    axs[0].tick_params(axis="y", length=0, pad=5)
    handles = [Line2D([], [], marker="D", color=NAVY, mec=NAVY_D, ls="", ms=4.6,
                      label="P1' (primary)"),
               Line2D([], [], marker="o", color=TEAL, mec=TEAL_D, ls="", ms=4.2,
                      label="P2 (transfer)"),
               Line2D([], [], marker="s", mfc="white", mec=PLUM_D,
                      color=PLUM_D, ls="", ms=4.2, label="P3 (transfer)")]
    fig.legend(handles=handles, loc="upper center", ncol=3,
               bbox_to_anchor=(0.58, 0.997), columnspacing=2.4, fontsize=8.4)
    fig.text(0.58, 0.108, "Risk ratio C0 / intervention "
             "(95% key-cluster intervals)", ha="center", fontsize=8.0,
             color=BODY)
    fig.text(0.58, 0.048, "Below 1: more failures with the intervention      |"
             "      Above 1: fewer failures", ha="center", fontsize=8.0,
             color=MUTED)
    save(fig, "Fig6")


# ------------------------------------------------------------------ Fig 7 ---
def fig7():
    """Transfer to a new parameter set, and where the effect saturates."""
    transfer = load("t2_transfer_p2.csv")
    capture = load("t3_capture_gradient.csv")
    ncw = load("t1_ncw_aware_capture.csv")
    W, H = 435.5, 180.0
    fig = plt.figure(figsize=(W / 72.0, H / 72.0))
    gs = fig.add_gridspec(1, 3, left=0.115, right=0.985, bottom=0.255,
                          top=0.760, width_ratios=[1, 1, 1], wspace=0.60)
    a, b, cax = (fig.add_subplot(gs[0, i]) for i in range(3))

    for j, cnd in enumerate(CONDS):
        r = row(transfer, condition=cnd)
        v, l, h = (float(r[k]) for k in ("rr", "rr_lo", "rr_hi"))
        hforest(a, 2 - j, v, l, h, AMBER, AMBER_D, marker="s", ms=5.0)
        a.text(h + 0.18, 2 - j, f"{v:.2f}", fontsize=8.2, color=BODY,
               va="center", ha="left")
    a.axvline(1, color="#8C857A", lw=0.9, ls=(0, (3, 2.4)), zorder=2)
    a.set_yticks([2, 1, 0])
    a.set_yticklabels([SHORT[c] for c in CONDS], fontsize=8.2)
    a.tick_params(axis="y", length=0, pad=5)
    a.set_xlim(0, 6.0)
    a.set_ylim(-0.7, 2.7)
    a.set_xticks([0, 1, 2, 3, 4])
    a.set_xticklabels(["0", "1", "2", "3", "4"], fontsize=8.2)
    a.set_xlabel("C0 / FRO-2 (95% CI)", fontsize=8.4, labelpad=2.0)
    panel(a, "a", "Transfer to P2", dx=-0.155)

    series = (("C0", capture, "c0_dfr", NAVY, NAVY_D, "o", -1.7),
              ("FRO-2", capture, "fro2_dfr", AMBER, AMBER_D, "s", 0.0),
              ("NCW-aware", ncw, "ncw_exact_recovery_dfr", BRICK, BRICK_D,
               "^", 1.7))
    for name, src, key, fill, edge, mk, dx in series:
        xs = np.array([int(r["kappa"]) for r in src]) + dx
        ys = [float(r[key]) for r in src]
        b.scatter(xs, ys, c=fill, edgecolors=edge, marker=mk, s=30,
                  linewidths=0.75, zorder=3, label=name)
    b.axhline(1, color="#8C857A", lw=0.7, ls=(0, (2, 2)), zorder=1)
    b.axvline(45, color=AMBER_D, lw=0.7, ls=(0, (1.4, 1.6)), zorder=1)
    b.set_yscale("log")
    b.set_ylim(5e-5, 4.0)
    b.set_xlim(-5, 66)
    b.set_xticks([0, 12, 46, 60])
    b.set_xticklabels(["0", "12", "46", "60"], fontsize=8.2)
    b.set_yticks([1e-4, 1e-2, 1])
    b.set_yticklabels(["0.0001", "0.01", "1"], fontsize=8.2)
    b.set_xlabel("Constructed overlap \u03ba", fontsize=8.4, labelpad=2.0)
    b.set_ylabel("Absolute failure rate", fontsize=8.4, labelpad=2.0)
    logfmt(b)
    panel(b, "b", "Reliability boundary", dx=-0.175)

    for j, r in enumerate(capture):
        if int(r["kappa"]) == 60:
            continue
        v, l, h = (float(r[k]) for k in ("rr", "rr_lo", "rr_hi"))
        hforest(cax, 3 - j, v, l, h, AMBER, AMBER_D, marker="s", ms=4.8)
        if int(r["kappa"]) == 46:
            cax.text(h * 1.12, 3 - j, "0.99", fontsize=8.0, color=BODY,
                     ha="left", va="center")
    cax.axvline(1, color="#8C857A", lw=0.9, ls=(0, (3, 2.4)), zorder=2)
    cax.set_xscale("log")
    cax.set_xlim(0.62, 30)
    cax.set_ylim(-0.85, 3.9)
    cax.set_yticks([3, 2, 1, 0])
    cax.set_yticklabels(["0", "12", "46", "60"], fontsize=8.2)
    cax.set_xticks([1, 5, 20])
    cax.set_xticklabels(["1", "5", "20"], fontsize=8.2)
    cax.set_xlabel("C0 / FRO-2 (95% CI)", fontsize=8.4, labelpad=2.0)
    cax.set_ylabel("Overlap \u03ba", fontsize=8.4, labelpad=2.0)
    logfmt(cax, "x")
    panel(cax, "c", "Relative effect", dx=-0.245)
    cax.text(1.15, 0.0, "both saturated", fontsize=8.0,
             color=MUTED, ha="left", va="center")

    fig.legend(handles=b.get_legend_handles_labels()[0],
               labels=b.get_legend_handles_labels()[1], loc="upper center",
               bbox_to_anchor=(0.60, 0.998), ncol=3, columnspacing=1.8,
               handletextpad=0.4, fontsize=8.4)
    fig.text(0.115, 0.075, "P2: 30 keys \u00d7 3,000 decodes per condition   "
             "\u00b7   Boundary: 40,000 decodes per construction",
             fontsize=8.0, color=MUTED)
    fig.text(0.115, 0.030, "Above 1: fewer failures. Dashed rule in (b): "
             "\u03ba = d = 45. NCW-aware: exact-recovery failure.",
             fontsize=8.0, color=MUTED)
    save(fig, "Fig7")


# --------------------------------------------------------------- palette ---
def palette_sheet():
    """Swatch sheet: fill, same-hue stroke and the meaning of each colour."""
    fig = plt.figure(figsize=(6.67, 2.35))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 6.67)
    ax.set_ylim(0, 2.35)
    ax.set_axis_off()
    entries = (
        ("navy", NAVY, NAVY_D, "baseline \u00b7 C0 \u00b7 original sample \u00b7 P1'"),
        ("ochre", AMBER, AMBER_D, "raised threshold \u00b7 FRO-2 \u00b7 fresh sample"),
        ("brick", BRICK, BRICK_D, "permissive side \u00b7 NCW-aware comparator"),
        ("teal", TEAL, TEAL_D, "NCW-shallow condition \u00b7 P2 transfer"),
        ("plum", PLUM, PLUM_D, "TYPE-I condition \u00b7 P3 transfer"),
        ("stone", STONE, STONE_D, "ties \u00b7 neutral reference"),
    )
    ax.text(0.06, 2.22, "JCEN figure palette \u2014 ink & earth", fontsize=10,
            color=INK, fontweight="bold", va="center")
    ax.text(0.06, 2.03, "fill / same-hue stroke, lower row; colour is always "
            "backed by shape or line style", fontsize=6.8, color=MUTED,
            va="top")
    for i, (name, fill, edge, desc) in enumerate(entries):
        y = 1.74 - i * 0.285
        ax.add_patch(plt.Rectangle((0.06, y - 0.085), 0.30, 0.17,
                                   facecolor=fill, edgecolor=edge,
                                   linewidth=0.8))
        ax.text(0.42, y, name, fontsize=8.2, color=INK, va="center")
        ax.text(1.00, y, f"{fill}   stroke {edge}", fontsize=6.8, color=MUTED,
                va="center", family="monospace")
        ax.text(2.60, y, desc, fontsize=6.8, color=MUTED, va="center")
    for ext in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"palette.{ext}", dpi=600,
                    **({"bbox_inches": "tight"} if ext == "png" else {}))
    plt.close(fig)
    print("saved palette")


# ------------------------------------------------------------------ main ---
def main():
    setup()
    want = [w.strip() for w in os.environ.get("FIGS", "").split(",") if w.strip()]
    fns = {"Fig1": fig1, "Fig2": fig2, "Fig3": fig3, "Fig4": fig4,
           "Fig5": fig5, "Fig6": fig6, "Fig7": fig7}
    if not want:
        want = list(fns) + ["palette"]
    for name in want:
        if name == "palette":
            palette_sheet()
        else:
            fns[name]()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
