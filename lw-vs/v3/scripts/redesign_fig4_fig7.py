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

BLACK, BLUE, GREY, LIGHT, RED, GRID = "#111111", "#444444", "#777777", "#aaaaaa", "#333333", "#d9d9d9"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.2, "axes.labelsize": 7.2,
                     "xtick.labelsize": 6.4, "ytick.labelsize": 6.4, "axes.linewidth": .7,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": .5,
                     "pdf.fonttype": 42, "svg.fonttype": "none"})


def rows(name):
    with open(DATA / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def val(r, key):
    return float(r[key])


def save(fig, stem):
    for ext in ("pdf", "svg"):
        fig.savefig(OUT / f"{stem}.{ext}")
    fig.savefig(OUT / f"{stem}.png", dpi=600)
    plt.close(fig)


def fig4():
    piv = rows("t2_temporal_pivot.csv")
    rc = [r for r in rows("t1_round_controls.csv") if r["condition"] == "RAND"]
    schedules = ["FRO-1", "FRO-2", "FRO-3", "R2-2", "UNIFORM-2"]
    points = ["P2", "P3"]
    conds = [("RAND", "RAND"), ("TYPE-I", "TYPE-I"), ("NCW-shallow", "NCW")]
    x = np.arange(len(schedules))
    fig = plt.figure(figsize=(7.16, 3.0), constrained_layout=True)
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1.15])
    for i, (cond, label) in enumerate(conds):
        ax = fig.add_subplot(gs[0, i])
        ax.set_title(label, pad=4)
        for point, color, marker, ls in (("P2", BLACK, "o", "-"), ("P3", GREY, "s", "--")):
            y = []
            for schedule in schedules:
                r = next(r for r in piv if r["condition"] == cond and r["point"] == point and r["schedule"] == schedule)
                y.append(val(r, "rr_vs_c0"))
            ax.plot(x, y, marker=marker, ls=ls, color=color, ms=3.8, lw=1.0,
                    markerfacecolor=color if point == "P2" else "white", markeredgewidth=.6,
                    label=point)
        ax.axhline(1, color=LIGHT, ls=(0, (3, 2)), lw=.8)
        ax.axvline(3.5, color=LIGHT, ls=(0, (2, 2)), lw=.7)
        ax.set_yscale("log"); ax.set_ylim(.005, 13)
        ax.set_xticks(x, ["FRO-1", "FRO-2", "FRO-3", "R2-2", "U-2"], rotation=35, ha="right")
        ax.grid(axis="x", visible=False)
        if i == 0:
            ax.set_ylabel("risk ratio C0 / arm")
            ax.legend(frameon=False, fontsize=6, loc="upper left")
        else:
            ax.set_yticklabels([])
    ax = fig.add_subplot(gs[0, 3])
    order = ["FRO-2", "R2one", "FRONEG", "R2plus"]
    labels = ["+2 round 1", "+2 round 2", "-1 round 1", "+2 rounds 2+"]
    colors = [BLACK, "#666666", RED, RED]
    y = np.arange(len(order))[::-1]
    by = {r["arm"]: r for r in rc}
    for yi, arm, color in zip(y, order, colors):
        r = by[arm]
        p, lo, hi = val(r, "rr_vs_c0"), val(r, "rr_lo"), val(r, "rr_hi")
        ax.plot([lo, hi], [yi, yi], color=color, lw=1.0)
        ax.plot(p, yi, "s", color=color, mec="white", mew=.5, ms=4.4)
        ax.text(max(hi * 1.08, .012), yi, f"{p:.3g}", color=color, fontsize=5.8, va="center")
    ax.axvline(1, color=LIGHT, ls=(0, (3, 2)), lw=.8)
    ax.set_xscale("log"); ax.set_xlim(.008, 14); ax.set_ylim(-.55, 3.55)
    ax.set_yticks(y, labels); ax.set_xlabel("risk ratio C0 / arm\n95% key-cluster CI")
    ax.grid(axis="y", visible=False)
    ax.set_title("d", loc="left", fontweight="bold", pad=4)
    save(fig, "fig4_temporal_redesign")
    with open(OUT / "fig4_origin_long.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["condition", "point", "schedule", "risk_ratio"])
        for r in piv: w.writerow([r["condition"], r["point"], r["schedule"], r["rr_vs_c0"]])


def fig7():
    mod = rows("t1_modern_scaled.csv")
    bgf = {r["condition"]: r for r in rows("t1_bgf_baseline.csv") if r["arm"] == "BGF-C3"}
    hold = {r["path"]: r["value"] for r in rows("t1_native_l1_holdout_flat.csv")}
    conds = [("RAND", "RAND"), ("TYPE-I", "TYPE-I"), ("NCW-shallow", "NCW")]
    arms = [("c0_dfr", "C0", BLACK, "o"), ("fro2_dfr", "FRO-2", BLUE, "s"),
            ("bikeflip_dfr", "BIKE-Flip", GREY, "D"), (None, "BGF-C3", LIGHT, "^")]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.16, 2.8), constrained_layout=True,
                                    gridspec_kw={"width_ratios": [1.15, 1]})
    offsets = np.linspace(-.24, .24, len(arms))
    for gi, (cond, label) in enumerate(conds):
        r = next(r for r in mod if r["condition"] == cond)
        for off, (key, arm, color, marker) in zip(offsets, arms):
            dfr = val(bgf[cond], "dfr") if key is None else val(r, key)
            ax1.plot(gi + off, dfr, marker=marker, color=color, ms=5, mec=BLACK, mew=.55,
                     linestyle="none", label=arm if gi == 0 else None)
            ax1.text(gi + off, dfr * 1.18, f"{dfr:.2g}", fontsize=5.1, ha="center", color=color)
    ax1.set_yscale("log"); ax1.set_xlim(-.55, 2.55); ax1.set_ylim(7e-5, 2.5e-3)
    ax1.set_xticks(range(3), [x[1] for x in conds]); ax1.set_ylabel("DFR at P1'")
    ax1.set_title("a", loc="left", fontweight="bold", pad=4); ax1.grid(axis="x", visible=False)
    ax1.legend(frameon=False, ncol=2, fontsize=5.7, loc="upper center")
    offs = [0, 2, 4]
    series = [("RAND", BLACK, "o", "-"), ("TYPE-I", GREY, "s", "--"), ("NCW", LIGHT, "^", ":")]
    for cond, color, marker, ls in series:
        ys = [float(hold[f"two_round_convergence_percent/offset_{o}/{cond}"]) for o in offs]
        ax2.plot(offs, ys, color=color, marker=marker, ls=ls, ms=4, lw=1.0, label=cond)
    ax2.set_ylim(-3, 103); ax2.set_xticks(offs, ["+0", "+2", "+4"])
    ax2.set_xlabel("first-round threshold offset"); ax2.set_ylabel("2-round convergence (%)")
    ax2.set_title("b", loc="left", fontweight="bold", pad=4); ax2.legend(frameon=False, fontsize=5.7)
    ax2.text(.98, .5, "BIKE Level-1\n10^6 runs/cell\n0 failures", transform=ax2.transAxes,
             ha="right", va="center", color=GREY, fontsize=5.7)
    save(fig, "fig7_modern_redesign")
    with open(OUT / "fig7_origin_long.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["condition", "arm", "dfr"])
        for cond, label in conds:
            r = next(r for r in mod if r["condition"] == cond)
            for key, arm, _, _ in arms:
                w.writerow([label, arm, val(bgf[cond], "dfr") if key is None else val(r, key)])


if __name__ == "__main__":
    fig4(); fig7()
