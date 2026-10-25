from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "v3" / "story_redesign"
OUT.mkdir(parents=True, exist_ok=True)

# Paul Tol High Contrast: baseline, intervention, harmful direction.
INK = "#004488"       # C0 / reference
DARK = "#DDAA33"      # FRO-2 / intervention
MID = "#777777"       # neutral annotation
LIGHT = "#D9D9D9"     # connector / interval background
PALE = "#F3E7C0"      # neutral-to-favourable wash
HARM = "#BB5566"      # harmful direction
GRID = "#D5D5D5"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8,
    "axes.labelsize": 8, "axes.titlesize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.linewidth": .75, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": False,
    "pdf.fonttype": 42, "svg.fonttype": "none",
})


def read(name):
    with open(DATA / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(row, key):
    return float(row[key])


def export(fig, name):
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"{name}.{ext}")
    fig.savefig(OUT / f"{name}.png", dpi=600)
    plt.close(fig)


def panel_letter(ax, letter):
    ax.text(-.08, 1.04, letter, transform=ax.transAxes, fontsize=10,
            fontweight="bold", ha="left", va="bottom")


def main_result():
    rows = read("t1_formal_main.csv")
    conds = [("RAND", "RAND"), ("TYPE-I", "TYPE-I"), ("NCW-shallow", "NCW")]
    fig = plt.figure(figsize=(7.16, 2.8), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, .9], wspace=.3)
    ax = fig.add_subplot(gs[0, 0]); panel_letter(ax, "a")
    ax.set_xscale("log")
    y = np.arange(len(conds))[::-1]
    for yi, (key, label) in zip(y, conds):
        r = next(r for r in rows if r["condition"] == key)
        c0, f2 = num(r, "c0_dfr"), num(r, "fro2_dfr")
        ax.plot([f2, c0], [yi, yi], color=LIGHT, lw=2.4, zorder=1)
        ax.plot(c0, yi, "o", ms=6, color=INK, mec="white", mew=.6, zorder=3)
        ax.plot(f2, yi, "s", ms=6, color=DARK, mec="white", mew=.6, zorder=3)
        ax.text(np.sqrt(c0*f2), yi+.22, f"{num(r, 'rr'):.2f}×", ha="center",
                fontsize=7.5, fontweight="bold")
        ax.text(c0*1.08, yi-.18, f"{c0:.2g}", color=INK, fontsize=6, ha="left")
        ax.text(f2*1.08, yi-.18, f"{f2:.2g}", color=DARK, fontsize=6, ha="left")
    ax.set_yticks(y, [x[1] for x in conds])
    ax.set_ylim(-.6, 2.55); ax.set_xlim(7e-5, 2.8e-3)
    ax.set_xlabel("conditional decoding-failure rate (log scale)")
    ax.set_title("paired DFRs (same H, e, s)", loc="left", pad=8)
    ax.grid(axis="x", color=GRID, lw=.5)
    ax.text(.72, 1.03, "● C0    ■ FRO-2", transform=ax.transAxes,
            color=INK, fontsize=7, ha="left")

    ax = fig.add_subplot(gs[0, 1]); panel_letter(ax, "b")
    pts, lo, hi = [], [], []
    for key, _ in conds:
        r = next(r for r in rows if r["condition"] == key)
        pts.append(num(r, "rr")); lo.append(num(r, "rr_lo")); hi.append(num(r, "rr_hi"))
    yy = np.arange(3)[::-1]
    ax.axvspan(1, 8.5, color=PALE, zorder=0)
    ax.axvline(1, color=INK, lw=.8, ls=(0, (3, 2)))
    for yi, p, l, h in zip(yy, pts, lo, hi):
        ax.plot([l, h], [yi, yi], color=DARK, lw=1.5)
        ax.plot(p, yi, "s", color=INK, ms=6, mec="white", mew=.6)
        ax.text(p, yi+.22, f"{p:.2f}", ha="center", fontsize=7, fontweight="bold")
    ax.set_xscale("log"); ax.set_xlim(.75, 8.8); ax.set_ylim(-.55, 2.55)
    ax.set_yticks(yy, [x[1] for x in conds])
    ax.set_xlabel("risk ratio C0 / FRO-2 (95% key-cluster CI)")
    ax.set_title("the direction is stable across conditions", loc="left", pad=8)
    ax.text(1.08, -.35, "neutral", fontsize=6, color=MID)
    ax.text(2.4, -.35, "all intervals exclude 1", fontsize=6, color=INK)
    ax.grid(axis="x", color=GRID, lw=.5)
    export(fig, "fig2_main_story")


def temporal():
    rows = read("t2_temporal_pivot.csv")
    conds = [("RAND", "RAND"), ("TYPE-I", "TYPE-I"), ("NCW-shallow", "NCW")]
    sched = ["FRO-1", "FRO-2", "FRO-3", "R2-2", "UNIFORM-2"]
    fig = plt.figure(figsize=(7.16, 3.05), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, .8], wspace=.35)
    ax = fig.add_subplot(gs[0, 0]); panel_letter(ax, "a")
    mat = np.zeros((3, 5))
    for i, (key, _) in enumerate(conds):
        for j, s in enumerate(sched):
            r = next(r for r in rows if r["condition"] == key and r["point"] == "P2" and r["schedule"] == s)
            mat[i, j] = num(r, "rr_vs_c0")
    # log10 effect, with neutral centered at 0; grayscale plus hatch for harmful cells
    norm = np.clip(np.log10(mat), -2.2, 0.65)
    # RR sign is the story: Tol blue for benefit, gold near neutral, red for harm.
    im = ax.imshow(np.zeros_like(mat), cmap="Greys", vmin=0, vmax=1, aspect="auto")
    for i in range(3):
        for j in range(5):
            value = mat[i, j]
            if value < 1:
                cell_color = HARM
            elif value < 1.5:
                cell_color = DARK
            else:
                cell_color = INK
            ax.add_patch(Rectangle((j-.5, i-.5), 1, 1, facecolor=cell_color,
                                   edgecolor="white", lw=.8, zorder=1))
            # Gold is light enough for dark blue text; blue and red need white text.
            text_color = INK if 1 <= value < 1.5 else "white"
            ax.text(j, i, f"{value:.2g}", ha="center", va="center", fontsize=7,
                    color=text_color, fontweight="bold")
            if value < 1:
                ax.add_patch(Rectangle((j-.48, i-.48), .96, .96, fill=False,
                                       hatch="///", edgecolor="white", lw=.0, zorder=3))
    ax.axvline(3.5, color=INK, lw=1.0)
    ax.axhline(2.5, color=INK, lw=.0)
    ax.set_xticks(range(5), ["FRO-1", "FRO-2", "FRO-3", "R2-2", "uniform +2"], rotation=25, ha="right")
    ax.set_yticks(range(3), [x[1] for x in conds])
    ax.set_ylim(-.5, 3.0)
    ax.set_title("timing changes the sign", loc="left", pad=8)
    ax.set_xlabel("threshold offset schedule; values are C0 / arm risk ratios")
    ax.text(1.5, 2.78, "one-shot window", ha="center", va="center", fontsize=7,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
    ax.text(4.0, 2.78, "sustained", ha="center", va="center", fontsize=7, color=HARM,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5))

    ax = fig.add_subplot(gs[0, 1]); panel_letter(ax, "b")
    rc = [r for r in read("t1_round_controls.csv") if r["condition"] == "RAND"]
    order = ["FRONEG", "R2plus", "R2one", "FRO-2"]
    labels = ["-1, round 1", "+2, rounds 2+", "+2, round 2", "+2, round 1"]
    colors = [HARM, HARM, MID, INK]
    y = np.arange(4)[::-1]
    by = {r["arm"]: r for r in rc}
    for yi, arm, lab, c in zip(y, order, labels, colors):
        r = by[arm]; p, l, h = num(r, "rr_vs_c0"), num(r, "rr_lo"), num(r, "rr_hi")
        ax.plot([l, h], [yi, yi], color=c, lw=1.4)
        ax.plot(p, yi, "o", color=c, ms=5, mec="white", mew=.5)
        ax.text(h*1.10 if h < 1 else h*1.04, yi, f"{p:.3g}", color=c, fontsize=6.4, va="center")
    ax.axvline(1, color=INK, lw=.8, ls=(0, (3,2)))
    ax.set_xscale("log"); ax.set_xlim(.008, 14); ax.set_ylim(-.5, 3.5)
    ax.set_yticks(y, labels); ax.set_xlabel("risk ratio C0 / arm")
    ax.set_title("same +2, opposite outcomes", loc="left", pad=8)
    ax.text(.02, -.19, "harmful", transform=ax.transAxes, color=HARM, fontsize=7)
    ax.text(.85, -.19, "beneficial", transform=ax.transAxes, color=INK, fontsize=7)
    ax.grid(axis="x", color=GRID, lw=.5)
    export(fig, "fig4_temporal_story")


def temporal_quadrant():
    """Recast the round-control result as a four-quadrant mechanism figure."""
    rows = [r for r in read("t1_round_controls.csv") if r["condition"] in {"RAND", "TYPE-I", "NCW-shallow"}]
    conditions = [("RAND", "RAND", "o", INK),
                  ("TYPE-I", "TYPE-I", "s", DARK),
                  ("NCW-shallow", "NCW", "D", HARM)]
    fig, ax = plt.subplots(figsize=(6.6, 3.65))
    fig.subplots_adjust(left=.13, right=.97, bottom=.18, top=.84)
    by = {(r["condition"], r["arm"]): r for r in rows}
    offsets = {"RAND": (-5, 14), "TYPE-I": (0, 14), "NCW-shallow": (0, -30)}
    for key, label, marker, color in conditions:
        first_row, later_row = by[(key, "FRO-2")], by[(key, "R2plus")]
        first, later = num(first_row, "rr_vs_c0"), num(later_row, "rr_vs_c0")
        ax.errorbar(first, later,
                    xerr=[[first-num(first_row, "rr_lo")], [num(first_row, "rr_hi")-first]],
                    yerr=[[later-num(later_row, "rr_lo")], [num(later_row, "rr_hi")-later]],
                    fmt=marker, ms=8, color=color, ecolor=color, elinewidth=1.5,
                    capsize=3, mec="white", mew=.8, zorder=4)
        ax.annotate(f"{label}  ({first:.2f}, {later:.4f})", (first, later),
                    xytext=offsets[key], textcoords="offset points", fontsize=8,
                    color=INK if color == DARK else color, ha="center", fontweight="bold",
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
    ax.set_xlim(2.9, 7.65); ax.set_ylim(.0075, .029)
    ax.set_xticks([3, 4, 5, 6, 7])
    ax.set_yticks([.01, .015, .02, .025], ["0.010", "0.015", "0.020", "0.025"])
    ax.set_xlabel("Round 1: risk ratio C0 / FRO-2", fontsize=9)
    ax.set_ylabel("Rounds 2+: risk ratio C0 / sustained arm", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(color=GRID, lw=.5, axis="both", alpha=.6)
    ax.set_axisbelow(True)
    fig.text(.13, .95, "Early benefit, later harm", fontsize=12, fontweight="bold", color=INK)
    fig.text(.13, .89, "Expanded data view · horizontal / vertical bars: marginal 95% key-cluster CIs",
             fontsize=8, color="#444444")

    # A small conceptual key preserves the quadrant logic without compressing data.
    inset = ax.inset_axes([.73, .67, .24, .27])
    inset.set_xlim(-1, 1); inset.set_ylim(-1, 1)
    inset.add_patch(Rectangle((-1, -1), 2, 2, facecolor="#F5F5F5", edgecolor="none"))
    inset.add_patch(Rectangle((0, -1), 1, 1, facecolor=DARK, alpha=.45, edgecolor="none"))
    inset.axvline(0, color=INK, lw=.7); inset.axhline(0, color=INK, lw=.7)
    inset.plot(.5, -.5, "o", color=INK, ms=5)
    inset.set_xticks([]); inset.set_yticks([])
    inset.set_title("Schematic: boundaries at RR = 1", fontsize=6, pad=4)
    inset.text(.5, -.86, "data", fontsize=7, ha="center", color=INK)
    for spine in inset.spines.values():
        spine.set_visible(False)
    export(fig, "fig4_temporal_quadrant")


def mechanism():
    rows = read("t1_mechanism_firstround.csv")
    c0 = next(r for r in rows if r["condition"] == "RAND" and r["arm"] == "C0")
    f2 = next(r for r in rows if r["condition"] == "RAND" and r["arm"] == "FRO-2")
    fig = plt.figure(figsize=(7.16, 3.0), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.1, .9], wspace=.32)
    metrics = [("mean_incorrect_first", "incorrect flips", "removed"),
               ("mean_correct_first", "correct flips", "deferred"),
               ("mean_residual_r1", "residual errors", "carried forward")]
    for i, (key, label, note) in enumerate(metrics):
        ax = fig.add_subplot(gs[0, i]); panel_letter(ax, "abc"[i])
        a, b = num(c0, key), num(f2, key)
        ax.barh([1, 0], [a, b], color=[INK, DARK], height=.48, edgecolor="white")
        ax.set_yticks([1, 0], ["C0", "FRO-2"])
        ax.set_xlim(0, max(a, b)*1.35); ax.set_xlabel("mean count per decode")
        ax.set_title(label, loc="left", pad=8)
        ax.text(a, 1, f"{a:.1f}", va="center", ha="left", fontsize=7)
        ax.text(b, 0, f"{b:.1f}", va="center", ha="left", fontsize=7)
        ratio = a/b
        ax.text(.98, .06, f"C0/FRO-2 = {ratio:.1f}×\n{note}", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6.5, color=HARM if key == "mean_incorrect_first" else MID)
        ax.spines["left"].set_visible(False); ax.grid(axis="x", color=GRID, lw=.5)
    fig.suptitle("the first-round offset removes false flips more strongly than true flips", x=.02, ha="left", fontsize=9, fontweight="bold")
    export(fig, "fig3_mechanism_story")


def boundary():
    rows = read("t3_capture_gradient.csv")
    fig, ax = plt.subplots(figsize=(7.16, 2.75), constrained_layout=True)
    panel_letter(ax, "a")
    k = np.array([float(r["kappa"]) for r in rows]); rr = np.array([float(r["rr"]) for r in rows])
    lo = np.array([float(r["rr_lo"]) for r in rows]); hi = np.array([float(r["rr_hi"]) for r in rows])
    ax.axhspan(.85, 1.0, color=PALE, zorder=0)
    ax.axhline(1, color=INK, lw=.8, ls=(0, (3, 2)))
    ax.axvspan(45, 65, color="#eeeeee", zorder=0)
    ax.axvline(45, color=HARM, lw=1.1, ls=(0, (3, 2)))
    ax.plot(k, rr, "o-", color=INK, lw=1.2, ms=5)
    ax.vlines(k, lo, hi, color=DARK, lw=1.0)
    for x, y in zip(k, rr): ax.text(x, y*1.08 if y < 3 else y*.86, f"{y:.2g}", ha="center", fontsize=6)
    ax.set_yscale("log"); ax.set_xlim(-3, 63); ax.set_ylim(.7, 25)
    ax.set_xlabel("overlap with near-codeword, κ")
    ax.set_ylabel("risk ratio C0 / FRO-2")
    ax.set_title("the gain ends at the capture boundary", loc="left", pad=8)
    ax.text(45.8, 12, "κ = d = 45", color=HARM, fontsize=7)
    ax.text(50, 1.4, "capture-prone", color=HARM, fontsize=7, ha="center")
    ax.text(9, .78, "neutral RR = 1", color=MID, fontsize=6)
    ax.grid(axis="y", color=GRID, lw=.5)
    export(fig, "fig5_boundary_story")


if __name__ == "__main__":
    main_result(); temporal(); temporal_quadrant(); mechanism(); boundary()
