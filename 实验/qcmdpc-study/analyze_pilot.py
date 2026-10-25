"""Pilot analysis: per-key DFR distributions, Wilson upper bounds, and the
first heterogeneity figure (main-figure prototype F1-lite).

Reads results/<run>/<group>/samples_<decoder>.jsonl (failure-level records)
and reconstructs per-key failure counts against the frozen errors_per_key.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qcmdpc.stats import wilson_upper

DEC_STYLES = {
    "BF": ("tab:blue", "-", "o"), "BGF": ("tab:green", "--", "s"), "BFMAX": ("tab:red", "-.", "^"),
    "BF30": ("tab:blue", "-", "o"), "CLASSIC": ("tab:purple", "-", "D"),
    "BGFV": ("tab:green", "--", "s"), "BF28": ("tab:cyan", "-", "o"),
}
_PALETTE = ["tab:olive", "tab:brown", "tab:pink", "tab:gray"]


def _style(dec: str, extra_idx: int):
    if dec in DEC_STYLES:
        return DEC_STYLES[dec]
    return (_PALETTE[extra_idx % len(_PALETTE)], "-", "x")
GROUP_MARK = {"G0": "", "G2": " (Type-I d=4)", "G3": " (NCW kappa=6)"}


def load_per_key(run_dir: str, group: str, decoder: str, n_keys_expected: int, errors_per_key: int):
    path = os.path.join(run_dir, group, f"samples_{decoder}.jsonl")
    fails = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                fails[rec["key_id"]] = fails.get(rec["key_id"], 0) + 1
    # key ids are "<group>-NNNN" in order
    kid_counts = []
    for i in range(n_keys_expected):
        kid_counts.append(fails.get(f"{group}-{i:04d}", 0))
    return np.array(kid_counts, dtype=np.int64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="results/pilot_p0")
    ap.add_argument("--config", default="configs/pilot_p0.json")
    ap.add_argument("--out-fig", default=None)
    args = ap.parse_args()
    cfg = json.load(open(args.config, encoding="utf-8"))
    epk = cfg["errors_per_key"]
    param = cfg["parameter"]
    decoders = list(cfg["decoders"].keys())
    groups = cfg["groups"]

    report = {"parameter": param, "errors_per_key": epk, "groups": {}}
    plt.figure(figsize=(7.2, 4.6), dpi=150)
    extra_idx = 0

    for gid, gspec in groups.items():
        n_keys = gspec["n_keys"]
        report["groups"][gid] = {}
        for dec in decoders:
            k = load_per_key(args.run, gid, dec, n_keys, epk)
            n = epk
            dfr = k / n
            ub = np.array([wilson_upper(int(ki), n) for ki in k])
            # plotting value: point estimate if failures>0 else upper bound (marked hollow)
            vals = np.where(k > 0, dfr, ub)
            c, ls, mk = _style(dec, extra_idx)
            x = np.sort(vals)
            y = np.arange(1, len(x) + 1) / len(x)
            first_group = gid == list(groups.keys())[0]
            if first_group:
                plt.step(x, y, where="post", color=c, ls=ls, lw=1.6, label=dec)
                extra_idx += 1
            else:
                plt.step(x, y, where="post", color=c, ls=":", lw=1.2, alpha=0.9)
                plt.scatter([x[-1]], [1.0], color=c, marker="*", s=70, zorder=5)
            nz = k > 0
            report["groups"][gid][dec] = {
                "per_key_failures": k.tolist(),
                "per_key_dfr": dfr.tolist(),
                "per_key_upper95": ub.tolist(),
                "keys_with_failures": int(nz.sum()),
                "log10_dfr_min_nonzero": float(np.log10(dfr[nz].min())) if nz.any() else None,
                "log10_dfr_max_nonzero": float(np.log10(dfr[nz].max())) if nz.any() else None,
                "max_upper95_zero_keys": float(ub[~nz].max()) if (~nz).any() else None,
            }

    plt.xscale("log")
    plt.xlabel("per-key DFR (point estimate; upper 95% bound when zero failures)")
    plt.ylabel("fraction of keys (CDF)")
    plt.title(
        f"Per-key decoding failure rate  |  {param.get('id','?')}: r={param['r']}, d={param['d']}, t={param['t']}, N={epk}/key\n"
        "solid = first condition group; dotted+star = worst key of each other group"
    )
    plt.grid(alpha=0.3, which="both")
    plt.legend(fontsize=9)
    plt.tight_layout()
    out_fig = args.out_fig or os.path.join(args.run, "fig_pilot_perkey_dfr.png")
    plt.savefig(out_fig)
    with open(os.path.join(args.run, "analysis_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1)[:4000])
    print("figure ->", out_fig)


if __name__ == "__main__":
    main()
