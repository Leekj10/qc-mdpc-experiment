from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "v3" / "redesign"
OUT.mkdir(parents=True, exist_ok=True)

BLACK = "#111111"
BLUE = "#4a4a4a"  # retained variable name for compatibility; grayscale FRO-2
GREY = "#858585"
GRID = "#d9dee5"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.linewidth": 0.7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.55,
    "grid.alpha": 0.8,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
})


def rows(name):
    with open(DATA / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def f(row, key):
    return float(row[key])


def main():
    main_rows = rows("t1_formal_main.csv")
    conditions = [("RAND", "RAND"), ("TYPE-I", "TYPE-I"), ("NCW-shallow", "NCW")]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.16, 2.65),
                                    gridspec_kw={"width_ratios": [1.15, 1]},
                                    constrained_layout=True)
    y = np.arange(len(conditions))[::-1]

    # Paired rates: common horizontal scale, with upper confidence caps.
    for yi, (key, label) in zip(y, conditions):
        r = next(x for x in main_rows if x["condition"] == key)
        c0, fro = f(r, "c0_dfr"), f(r, "fro2_dfr")
        c0u, frou = f(r, "c0_upper95"), f(r, "fro2_upper95")
        ax1.plot([c0, fro], [yi, yi], color=GREY, lw=1.1, zorder=1)
        for x, u, color, marker in ((c0, c0u, BLACK, "o"), (fro, frou, BLUE, "s")):
            ax1.plot([x, u], [yi, yi], color=color, lw=1.1, zorder=2)
            ax1.plot([u, u], [yi - .10, yi + .10], color=color, lw=1.1, zorder=2)
            ax1.plot(x, yi, marker=marker, ms=5, color=color, mec="white",
                     mew=.55, zorder=3)
        ax1.text(np.sqrt(c0 * fro), yi + .24, f"{f(r, 'rr'):.2f}×",
                 color=BLUE, ha="center", va="bottom", fontsize=7, fontweight="bold")
    ax1.set_xscale("log")
    ax1.set_yticks(y, [x[1] for x in conditions])
    ax1.set_xlabel("conditional DFR (log scale)")
    ax1.set_title("a", loc="left", fontweight="bold", pad=5)
    ax1.set_xlim(8e-5, 2.4e-3)
    ax1.set_ylim(-0.55, 2.55)
    ax1.grid(axis="y", visible=False)
    ax1.text(.80, 1.02, "C0", transform=ax1.transAxes, color=BLACK, fontsize=7)
    ax1.text(.90, 1.02, "FRO-2", transform=ax1.transAxes, color=BLUE, fontsize=7)

    # Effect-size forest. Use the same blue intervention colour as panel a.
    for yi, (key, label) in zip(y, conditions):
        r = next(x for x in main_rows if x["condition"] == key)
        p, lo, hi = f(r, "rr"), f(r, "rr_lo"), f(r, "rr_hi")
        ax2.plot([lo, hi], [yi, yi], color=BLUE, lw=1.2)
        ax2.plot(p, yi, marker="s", ms=5, color=BLUE, mec="white", mew=.55)
        ax2.text(p, yi + .22, f"{p:.2f}", ha="center", va="bottom",
                 color=BLUE, fontsize=7, fontweight="bold")
    ax2.axvline(1, color=GREY, ls=(0, (3, 2)), lw=.9)
    ax2.axvspan(1, 8.5, color="#777777", alpha=.08, zorder=0)
    ax2.set_xscale("log")
    ax2.set_yticks(y, [x[1] for x in conditions])
    ax2.set_xlabel("risk ratio C0 / FRO-2 (95% key-cluster CI)")
    ax2.set_title("b", loc="left", fontweight="bold", pad=5)
    ax2.set_xlim(.78, 8.5)
    ax2.set_ylim(-0.55, 2.55)
    ax2.grid(axis="y", visible=False)
    ax2.text(.03, .04, "favours FRO-2", transform=ax2.transAxes,
             color=BLUE, fontsize=6.5, ha="left")

    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"fig2_main_results_redesign.{ext}")
    fig.savefig(OUT / "fig2_main_results_redesign.png", dpi=600)
    plt.close(fig)

    # Long table for Origin: one row per condition and arm.
    with open(OUT / "fig2_origin_long.csv", "w", encoding="utf-8", newline="") as f_out:
        w = csv.writer(f_out)
        w.writerow(["condition", "arm", "dfr", "upper95", "rr", "rr_lo", "rr_hi"])
        for key, label in conditions:
            r = next(x for x in main_rows if x["condition"] == key)
            w.writerow([label, "C0", r["c0_dfr"], r["c0_upper95"], "", "", ""])
            w.writerow([label, "FRO-2", r["fro2_dfr"], r["fro2_upper95"], r["rr"], r["rr_lo"], r["rr_hi"]])


if __name__ == "__main__":
    main()
