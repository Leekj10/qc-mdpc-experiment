#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fig7_modern_decoders -- modern-decoder comparison and the production
boundary (single column, 3.5 x 3.4 in); v3 redraw (nature-figure pass).

SHIPPING NOTE (2026-10-17): the v3 manuscript ships the
figure_research/complete_set rendering of this figure. Do not re-run this
script into v3/figures; it would overwrite the shipped art.

Panel (a): archived data mapping and arm semantics (C0 / FRO-2 / BIKE-Flip /
BGF-C3 at P1', log DFR, hatch as second channel, the two "n.s." tags).
Third-party decoders use the grey family: BIKE-Flip = neutral_mid with '///',
BGF-C3 = neutral_light with '\\\\\\' and a muted edge.

Panel (b): RAND / TYPE-I / NCW are CONDITION groups, not arms -> neutral
family with marker + line style only --
    RAND   = control near-black, filled circles, solid
    TYPE-I = grey, hollow squares, dashed
    NCW    = grey_light, filled triangles, dotted
The "BIKE Level-1" note and the zero-failure statement are kept unchanged.

Data (read-only, via style_v3.load): t1_modern_scaled.csv,
t1_bgf_baseline.csv, t1_native_l1_holdout_flat.csv.  No recomputation
beyond the archived function.  Output: lw-vs/v3/figures/ (pdf+svg+png).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker

import style_v3 as st

C0, FRO2, NEUT = st.C0, st.FRO2, st.NEUT
NEUT_LIGHT = st.PAL["neutral_light"]
GREY_LIGHT = st.PAL["grey_light"]
MUTED, INK, ACC = st.PAL["muted"], st.INK, st.ACC


def main():
    mod = st.load("t1_modern_scaled.csv")
    hold = {r["path"]: r["value"]
            for r in st.load("t1_native_l1_holdout_flat.csv")}

    fig = plt.figure(figsize=(st.COL_W, 3.4), layout="constrained")
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.82], hspace=0.12)

    # -- (a) scaled comparison at P1' (arms; hatch = second channel) -------
    ax = fig.add_subplot(gs[0, 0]); st.panel(ax, "a")
    ax.set_yscale("log"); st.no_minor_labels(ax, "y")
    bgf = {r["condition"]: r for r in st.load("t1_bgf_baseline.csv")
           if r["arm"] == "BGF-C3"}
    arms = [("C0", "c0", C0, "white"), ("FRO-2", "fro2", FRO2, "white"),
            ("BIKE-Flip", "bikeflip", NEUT, INK),
            ("BGF-C3", None, NEUT_LIGHT, MUTED)]
    w = 0.20
    for gi, cname in enumerate(st.COND):
        r = next((r for r in mod if r["condition"] == cname), None)
        if r is None:
            continue
        for ai, (lab, key, col, ec) in enumerate(arms):
            xpos = gi + (ai - 1.5) * w
            val = st.f(bgf[cname]["dfr"]) if key is None else st.f(r[f"{key}_dfr"])
            h = st.HATCH.get(lab, "")
            ax.bar(xpos, val, width=w * 0.88, color=col,
                   edgecolor=ec, lw=0.35, hatch=h,
                   label=lab if gi == 0 else None)
        # BGF-C3 is unresolved against C0 in the first two conditions
        if bgf[cname]["rr_excludes_1"] == "False":
            ax.text(gi + 1.5 * w, st.f(bgf[cname]["dfr"]) * 1.25, "n.s.",
                    ha="center", va="bottom", fontsize=5.6, color=ACC,
                    fontweight="bold")
    ax.set_xticks(range(len(st.COND)))
    ax.set_xticklabels([st.COND_SHORT[c] for c in st.COND])
    ax.set_ylabel("DFR at $P_1'$")
    # tight range about the data (1.1e-4..1.4e-3): bar differences stay legible
    ax.set_ylim(6e-5, 2.4e-3)
    ax.yaxis.set_major_locator(ticker.LogLocator(base=10, numticks=4))
    # legend ABOVE the axes: with the tight range the bar tops and n.s. tags
    # own the panel interior
    ax.legend(loc="lower center", ncol=4, handletextpad=0.3, columnspacing=0.9,
              fontsize=5.6, bbox_to_anchor=(0.5, 1.01))

    # -- (b) convergence cost at native BIKE Level-1 -----------------------
    ax = fig.add_subplot(gs[1, 0]); st.panel(ax, "b")
    offs = [0, 2, 4]
    series = [
        # name, colour, marker face, marker edge
        ("RAND",   C0,         C0,         "white"),
        ("TYPE-I", NEUT,       "white",    NEUT),
        ("NCW",    GREY_LIGHT, GREY_LIGHT, GREY_LIGHT),
    ]
    for cname, col, mfc, mec in series:
        mk, ls = st.mstyle(cname)
        ys = [st.f(hold.get(f"two_round_convergence_percent/offset_{o}/{cname}"))
              for o in offs]
        ax.plot(offs, ys, color=col, linestyle=ls, marker=mk, ms=3.6,
                markeredgecolor=mec, markeredgewidth=0.5, markerfacecolor=mfc,
                dash_capstyle="round", label=cname, lw=1.0)
    ax.set_xlabel("first-round threshold offset")
    ax.set_ylabel("2-round convergence (%)")
    ax.set_xticks(offs); ax.set_xticklabels(["+0", "+2", "+4"])
    ax.set_ylim(-3, 103)
    ax.legend(loc="lower left", ncol=3, columnspacing=0.7, handletextpad=0.3,
              bbox_to_anchor=(-0.01, 0.0))
    ax.text(0.985, 0.55, "BIKE Level-1\n$10^6$ runs/cell, 0 failures",
            transform=ax.transAxes, ha="right", va="center", fontsize=5.7,
            color=MUTED)

    st.save(fig, "fig7_modern_decoders")


if __name__ == "__main__":
    main()
