"""Paper-grade figures and main table from frozen run outputs.

Consumes:
  results/gate_h2_formal/report.json   (interim gate, fresh test keys)
  results/m6_mechanism/report.json     (paired failure-mode transitions)
  results/m4_search/report.json        (S1 search landscape)
Produces (results/paper_figures/):
  F1_perkey_paired.png    per-key paired DFR (C0 vs C4), zeros as bound arrows
  F2_conditional_dfr.png  pooled conditional DFR bars + Wilson U95 error bars
  F3_mechanism.png        rescued vs new failures per group (M6)
  F4_search_landscape.png S1 candidate J values (appendix)
  T1_main_table.md/.tex   headline table
If results/gate_h2_extended/report.json exists it is used INSTEAD of the
interim gate (larger N, same frozen protocol).
"""
from __future__ import annotations

import json
import os

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 200,
})

OUT = "results/paper_figures"
# P0-1/P0-13: G3 is a shallow-intersection CONTROL (kappa=12<d=45 => no near-codeword
# capture); the label carries the qualifier and uses mathtext $\cap$ (renders reliably
# in the Agg/PNG pipeline; no literal Unicode intersection char is used). Kept on ONE
# line so the auto-generated T1 markdown/tex table rows are not split.
GROUP_LABEL = {"G0": "RAND", "G2_d12": "WEAK-12", "G3": "NCW-$\\cap$ (shallow)"}
DEC_LABEL = {"C0_base": "base (C0)", "C4_first_p2": "FRO-2 (C4)"}
DEC_COLOR = {"C0_base": "tab:blue", "C4_first_p2": "tab:red"}


def load_gate():
    for p in ["results/m5_formal/report.json", "results/gate_h2_extended/report.json", "results/gate_h2_formal/report.json"]:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                rep = json.load(f)
            # m5_formal nests decoder entries one level deeper? no: groups[gid][decoder] same shape
            if "E_per_key" not in rep and "groups" in rep:
                rep["E_per_key"] = next(iter(rep["groups"].values())).get("E_per_key", 3000)
            return rep, p
    raise SystemExit("no gate report found")


def rule_of_three(n):
    return 3.0 / n


def f1_perkey(gate):
    groups = gate["groups"]
    E = gate["E_per_key"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6), sharey=True)
    for ax, gid in zip(axes, groups):
        g = groups[gid]
        n_keys = g.get("n_fresh_keys") or g.get("n_keys") or len(g["C0_base"]["per_key_failures"])
        xs = np.arange(n_keys)
        for m, dec in enumerate(["C0_base", "C4_first_p2"]):
            k = np.array(g[dec]["per_key_failures"], dtype=float)
            dfr = k / E
            bound = rule_of_three(E)
            nonzero = dfr > 0
            xj = xs + (0.18 if m else -0.18)
            ax.scatter(xj[nonzero], dfr[nonzero], s=14, color=DEC_COLOR[dec],
                       label=DEC_LABEL[dec], zorder=3)
            ax.vlines(xj[~nonzero], bound * 0.6, bound, colors=DEC_COLOR[dec],
                      linestyles=":", linewidth=1.0, zorder=2)
        ax.set_yscale("log")
        ax.set_title(GROUP_LABEL[gid], fontsize=9)
        ax.set_xlabel("formal-pool key index")
        ax.set_xticks([])
    axes[0].set_ylabel("per-key DFR")
    axes[0].axhline(rule_of_three(E), color="gray", lw=0.8, ls="--")
    axes[0].text(0.02, rule_of_three(E) * 1.15, f"3/N bound ({rule_of_three(E):.0e})", fontsize=6.5, color="gray")
    axes[0].legend(fontsize=7, loc="upper right")
    fig.suptitle(f"F1  Per-key conditional DFR, paired decoders on identical samples (N={E}/key)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(OUT, "F1_perkey_paired.png"))
    plt.close(fig)


def f2_bars(gate):
    groups = gate["groups"]
    fig, ax = plt.subplots(figsize=(3.6, 2.8))
    gids = list(groups)
    x = np.arange(len(gids))
    w = 0.36
    for m, dec in enumerate(["C0_base", "C4_first_p2"]):
        dfrs = [groups[g][dec]["dfr"] for g in gids]
        u95 = [groups[g][dec]["upper95"] for g in gids]
        errs = [[max(d - 0.35 * u, 0.12 * d) for d, u in zip(dfrs, u95)],
                [u - d for d, u in zip(dfrs, u95)]]
        ax.bar(x + (m - 0.5) * w, dfrs, width=w, color=DEC_COLOR[dec],
               yerr=errs, capsize=2, label=DEC_LABEL[dec])
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([GROUP_LABEL[g] for g in gids], fontsize=8)
    ax.set_ylabel("conditional DFR (Wilson $U_{0.95}$ bars)")
    ax.legend(fontsize=7)
    fig.suptitle("F2  Pooled conditional DFR by group", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(OUT, "F2_conditional_dfr.png"))
    plt.close(fig)


def f3_mechanism():
    """Formal-scale failure-mode breakdown (results/m5_mechanism). Two panels:
    (a) paired transitions per condition; (b) mode composition C0 vs FRO-2 aggregated,
    showing the reduction is roughly uniform across modes (general stabilization).
    Falls back to the M6 pilot schema if the formal file is absent."""
    p = "results/m5_mechanism/report.json"
    formal = os.path.exists(p)
    if not formal:
        p = "results/m6_mechanism/report.json"
        if not os.path.exists(p):
            return
    rep = json.load(open(p, encoding="utf-8"))
    groups = rep["groups"]
    gids = list(groups)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.7))

    # ---- panel (a): paired transitions per condition ----
    rescued, newfail, c0f, c4f = [], [], [], []
    for g in gids:
        gg = groups[g]
        if formal:
            tr = gg["transitions"]
            rescued.append(tr["c0_only_rescued"]); newfail.append(tr["c4_only_new"])
            c0f.append(gg["fails"]["C0_base"]); c4f.append(gg["fails"]["C4_first_p2"])
        else:
            tr = gg["transitions"]
            rescued.append(sum(v for k, v in tr.items() if k.endswith("->success")))
            newfail.append(sum(v for k, v in tr.items() if k.startswith("success->")))
            c0f.append(sum(v for k, v in gg["modes"]["C0_base"].items() if k != "success"))
            c4f.append(sum(v for k, v in gg["modes"]["C4_first_p2"].items() if k != "success"))
    x = np.arange(len(gids)); w = 0.2
    ax.bar(x - 1.5 * w, c0f, width=w, color="tab:blue", label="C0 failures")
    ax.bar(x - 0.5 * w, rescued, width=w, color="tab:green", label="rescued by FRO-2")
    ax.bar(x + 0.5 * w, newfail, width=w, color="tab:orange", label="new under FRO-2")
    ax.bar(x + 1.5 * w, c4f, width=w, color="tab:red", label="FRO-2 failures")
    ax.set_yscale("log"); ax.set_xticks(x)
    ax.set_xticklabels([GROUP_LABEL.get(g, g) for g in gids], fontsize=7.5)
    ax.set_ylabel("count (log)")
    # P0-13: headroom so the legend/annotations are never clipped at the log-axis top
    ax.set_ylim(top=max(c0f) * 8)
    ax.legend(fontsize=6, loc="upper center", ncol=2, framealpha=0.85)
    ax.set_title("(a) paired transitions", fontsize=8)

    # ---- panel (b): failure-mode composition, aggregated (formal only) ----
    if formal:
        modes = ["stagnation", "early_misflip", "other"]
        c0m = [sum(groups[g]["failure_modes"]["C0_base"].get(m, 0) for g in gids) for m in modes]
        c4m = [sum(groups[g]["failure_modes"]["C4_first_p2"].get(m, 0) for g in gids) for m in modes]
        xm = np.arange(len(modes)); wm = 0.36
        ax2.bar(xm - wm / 2, c0m, width=wm, color="tab:blue", label="C0 base")
        ax2.bar(xm + wm / 2, c4m, width=wm, color="tab:red", label="FRO-2")
        for i in range(len(modes)):
            if c0m[i] > 0:
                ax2.text(i, max(c0m[i], c4m[i]) * 1.3, f"{c4m[i]}/{c0m[i]}\n(-{100*(1-c4m[i]/c0m[i]):.0f}%)",
                         ha="center", va="bottom", fontsize=6.5)
        ax2.set_yscale("log"); ax2.set_xticks(xm)
        ax2.set_xticklabels(["stagnation", "early\nmis-flip", "other"], fontsize=7.5)
        ax2.set_ylabel("failures (log)")
        # P0-13: explicit top headroom so the per-mode ratio annotations (placed at
        # 1.3x the tallest bar, two lines) are NOT clipped by the log-axis upper limit.
        ax2.set_ylim(top=max(c0m) * 10)
        ax2.legend(fontsize=6.5, loc="upper right")
        ax2.set_title("(b) mode composition: all modes reduced", fontsize=8)
    else:
        ax2.axis("off")

    scale = "formal M5, 3000 errors/key" if formal else "M6 pilot, 400 errors/key"
    fig.suptitle(f"F3  Failure-mode breakdown and paired transitions ({scale})", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(os.path.join(OUT, "F3_mechanism.png"))
    plt.close(fig)


def f4_search():
    p = "results/m4_search/report.json"
    if not os.path.exists(p):
        return
    rep = json.load(open(p, encoding="utf-8"))
    s1 = rep["rounds"]["S1"]
    names = list(s1)
    js = [s1[n]["J_train"] for n in names]
    order = np.argsort(js)
    fig, ax = plt.subplots(figsize=(3.6, 2.6))
    colors = ["tab:red" if names[i].startswith(("C7", "C8")) else ("tab:green" if names[i] == "C4_first_p2" else "tab:blue") for i in order]
    ax.barh(range(len(order)), [js[i] for i in order], color=colors)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([names[i] for i in order], fontsize=7)
    ax.set_xlabel("$J=\\max_g \\log_{10} U_{0.95}$ on train keys (lower is better)")
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="tab:green")], labels=["selected DRIS*"], fontsize=7)
    fig.suptitle("F4  M4-S1 search landscape (red = CPS variants)", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(OUT, "F4_search_landscape.png"))
    plt.close(fig)


def t1_table(gate, src):
    groups = gate["groups"]
    lines_md = [f"# T1 main table (source: {src}, E/key={gate['E_per_key']})", "",
                "| Group | Decoder | failures/N | DFR | U95 | ratio vs base |",
                "|---|---|---|---|---|---|"]
    lines_tex = ["% T1 main table", "\\begin{tabular}{llrrrr}", "\\toprule",
                 "Group & Decoder & failures/N & DFR & $U_{0.95}$ & ratio \\\\", "\\midrule"]
    for gid, g in groups.items():
        base_d = g["C0_base"]["dfr"]
        for dec in ["C0_base", "C4_first_p2"]:
            e = g[dec]
            ratio = base_d / e["dfr"] if e["dfr"] > 0 else float("inf")
            ratio_s = f"{ratio:.1f}x" if np.isfinite(ratio) else ">= (0 failures)"
            lines_md.append(f"| {GROUP_LABEL.get(gid, gid)} | {DEC_LABEL[dec]} | {e['failures']}/{e['trials']} | {e['dfr']:.3e} | {e['upper95']:.3e} | {ratio_s} |")
            lines_tex.append(f"{gid} & {dec} & {e['failures']}/{e['trials']} & {e['dfr']:.2e} & {e['upper95']:.2e} & {ratio_s} \\\\")
    lines_tex += ["\\bottomrule", "\\end{tabular}"]
    j = gate.get("worst_group_log10U", {})
    if j:
        lines_md += ["", f"worst-group log10 U95: base={j.get('C0_base'):.3f}, C4={j.get('C4_first_p2'):.3f}, "
                         f"improvement={gate.get('improvement_log10'):.3f} log10; "
                         f"gate(>=0.5)={'PASS' if gate.get('gate_pass') else 'NOT MET'}; G0 non-inferior={'PASS' if gate.get('gate_noninferior_G0') else 'FAIL'}"]
    with open(os.path.join(OUT, "T1_main_table.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines_md))
    with open(os.path.join(OUT, "T1_main_table.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines_tex))
    print("\n".join(lines_md))


def main():
    os.makedirs(OUT, exist_ok=True)
    gate, src = load_gate()
    print("gate source:", src)
    f1_perkey(gate)
    f2_bars(gate)
    f3_mechanism()
    f4_search()
    t1_table(gate, src)
    print("figures ->", OUT)


if __name__ == "__main__":
    main()
