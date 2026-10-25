#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""fig5_scope_and_boundary -- v3 redraw (transfer and boundary; nature-figure pass).

SHIPPING NOTE (2026-10-17): the v3 manuscript ships the
figure_research/complete_set rendering of this figure. Do not re-run this
script into v3/figures; it would overwrite the shipped art.

Data mapping is copied exactly from the archived function (read-only); the
only ratio computed here is the archived C0 / arm ratio for the NCW-aware
series.  Semantics kept from the 10.12 set:

  (b) the "kappa = d = 45" label sits beside the rule line (x = 1.56,
      ha = left) at a height (y = 12.5) clear of every series; the
      "kappa > d" note carries a white pocket so the rule line does not
      pierce the glyphs.

Two panels only: the iteration-budget panel (c) was cut in the
2026-10-14 trim round (its numbers survive as one sentence in the text).

Run:  python lw-vs/v3/scripts/figs/fig5_scope_and_boundary.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import style_v3 as st


def main() -> None:
    tr = st.load("t2_transfer_p2.csv")
    cap = st.load("t3_capture_gradient.csv")

    fig = plt.figure(figsize=(st.DBL_W, 2.1), layout="constrained")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.14], wspace=0.36)

    # -- (a) transfer to the second operating point (hero only) ------------
    ax = fig.add_subplot(gs[0, 0])
    st.panel(ax, "a")
    order = [c for c in st.COND if any(r["condition"] == c for r in tr)]
    st.forest(ax, [st.COND_SHORT[c] for c in order],
              [st.f(next(r for r in tr if r["condition"] == c)["rr"]) for c in order],
              [st.f(next(r for r in tr if r["condition"] == c)["rr_lo"]) for c in order],
              [st.f(next(r for r in tr if r["condition"] == c)["rr_hi"]) for c in order],
              [st.FRO2] * len(order),
              xlabel="risk ratio  C0 / FRO-2", xlim=(0.72, 9.0))
    ax.text(0.985, 0.97, "$P_2=(3001,37,66)$\nno retuning", transform=ax.transAxes,
            fontsize=5.7, color=st.MUTED, va="top", ha="right")

    # -- (b) capture gradient vs overlap ------------------------------------
    ax = fig.add_subplot(gs[0, 1])
    st.panel(ax, "b")
    ax.set_yscale("log")
    st.no_minor_labels(ax, "y")
    ax.axhline(1.0, color=st.NEUT, lw=0.7, ls=(0, (3, 2)), zorder=1)
    # light wash marks the capture-prone region beyond kappa = d
    ax.axvspan(1.5, len(cap) - 0.55, facecolor=st.ACC, alpha=0.05, lw=0,
               zorder=0.3)
    ax.axvline(1.5, color=st.ACC, lw=0.7, ls=(0, (1.5, 1.5)), zorder=1)
    xs = list(range(len(cap)))
    rr = [st.f(r["rr"]) for r in cap]
    lo = [st.f(r["rr_lo"]) for r in cap]
    hi = [st.f(r["rr_hi"]) for r in cap]
    mk, ls = st.mstyle("FRO-2")
    eb = ax.errorbar(xs, rr,
                     yerr=[[max(r - l, 0) for r, l in zip(rr, lo)],
                           [max(h - r, 0) for r, h in zip(rr, hi)]],
                     fmt=mk + ls, color=st.FRO2, ms=4.0, lw=1.0, capsize=1.6,
                     elinewidth=0.8, markeredgecolor="white", markeredgewidth=0.5,
                     label="FRO-2 (threshold timing)", zorder=3)
    nw = st.load("t1_ncw_aware_capture.csv")
    nwr = [st.f(r["c0_dfr"]) / st.f(r["ncw_exact_recovery_dfr"])
           if st.f(r["ncw_exact_recovery_dfr"]) > 0 else float("nan") for r in nw]
    mk, ls = st.mstyle("NCW-aware")
    ln, = ax.plot(xs, nwr, color=st.NEUT, ms=3.6, lw=1.0, marker=mk, linestyle=ls,
                  markeredgecolor="white", markeredgewidth=0.4,
                  label="NCW-aware (structural)", zorder=2)
    ax.text(1.56, 12.5, "$\\kappa = d = 45$", fontsize=5.7, color=st.ACC,
            ha="left", va="center", zorder=4)
    # white pocket so the kappa = d rule line does not pierce the glyphs
    ax.text(2.0, 0.62, "$\\kappa>d$: capture-prone", fontsize=5.6, color=st.ACC,
            ha="center", va="center", zorder=4,
            bbox=dict(boxstyle="square,pad=0.25", facecolor="white",
                      edgecolor="none"))
    ax.set_xlabel("overlap with the near-codeword, $\\kappa$")
    ax.set_ylabel("risk ratio  C0 / arm")
    ax.set_ylim(0.5, 70)
    ax.set_xlim(-0.45, len(cap) - 0.55)
    ax.set_xticks(xs)
    ax.set_xticklabels(["uniform", "12", "46", "60"])
    ax.legend([ln, eb], ["NCW-aware (structural)", "FRO-2 (threshold timing)"],
              loc="upper left", fontsize=5.4, handletextpad=0.3, handlelength=1.5,
              bbox_to_anchor=(-0.02, 1.005))

    st.save(fig, "fig5_scope_and_boundary")


if __name__ == "__main__":
    main()
