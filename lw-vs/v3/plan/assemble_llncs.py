# -*- coding: utf-8 -*-
"""Assemble a single-column LNCS (llncs.cls) build of the current manuscript.

Same section fragments as the IEEE build; only the preamble and float
environments change.  Output: lw-vs/v3/llncs/en/main.tex

Build: pdflatex main -> bibtex main -> pdflatex main -> pdflatex main
"""
import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SECT = BASE / "plan" / "sections"
OUT = BASE / "llncs" / "en"
LNCS = BASE.parents[1] / "llncs"
ORDER = ["s01_intro", "s02_background", "s03_model", "s04_design",
         "s05_results_window", "s06_results_mechanism", "s07_results_boundary",
         "s08_results_negatives", "s09_discussion"]

PREAMBLE = r"""% LNCS single-column build (generated from plan/sections/*.tex)
\documentclass[runningheads,a4paper]{llncs}

\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{array}
\usepackage{multirow}
\usepackage{url}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{enumitem}

\graphicspath{{../../figures/}}

% Wide two-column-master figures are scaled to the LNCS text width here.
\newcommand{\dblfig}[3]{%
  \begin{figure}[!tb]\centering
    \includegraphics[width=\textwidth]{#1}%
    \caption{#2}\label{#3}
  \end{figure}}
\newcommand{\onefig}[4]{%
  \begin{figure}[!t]\centering
    \includegraphics[width=\textwidth]{#1}%
    \caption{#2}\label{#3}\vspace{#4}
  \end{figure}}

\begin{document}
\sloppy

\title{The First Round Is a Two-Sided Window: Threshold Timing and
Conditional Decoding Failure in QC-MDPC Bit-Flipping}
\titlerunning{The First Round Is a Two-Sided Window}

\author{[Author names and affiliations to be completed before submission]}
\authorrunning{[Author names to be completed]}
\institute{[Affiliations and e-mail to be completed before submission]}

\maketitle

\begin{abstract}
__ABSTRACT__
\keywords{post-quantum cryptography \and QC-MDPC codes \and bit-flipping
decoding \and decoding failure rate \and first-round threshold \and
key-conditional risk.}
\end{abstract}

"""

BACKMATTER = r"""
% ===========================================================================
\section*{Data and Code Availability}
The implementation, frozen configurations, seed derivation rules, raw per-key counts, and analysis code are archived at \url{https://doi.org/10.5281/zenodo.22296719}, with a development mirror at \url{https://github.com/Leekj10/qc-mdpc-experiment}. The figure source tables and a checking script that re-derives every quoted value from the archived counts are released with the same archive.

\bibliographystyle{splncs04}
\bibliography{refs}

\end{document}
"""


def single_column(tex: str) -> str:
    """Turn two-column float environments into single-column ones."""
    tex = tex.replace(r"\begin{table*}[!t]", r"\begin{table}[!t]")
    tex = tex.replace(r"\end{table*}", r"\end{table}")
    tex = tex.replace(r"\begin{figure*}[!t]", r"\begin{figure}[!t]")
    tex = tex.replace(r"\end{figure*}", r"\end{figure}")
    return tex


# Table bodies re-cut for the 347 pt LNCS text width.  The IEEE build keeps
# its wider originals; these variants only change presentation (row/column
# order, font size, abbreviations), not any number.
LNCS_TABLES = {
    "tab:main": r"""\begin{table}[!tb]
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\caption{Primary comparison at $P_1'=(4801,45,92)$. Cells give failures/decodings and DFR. RR is C0 over FRO-2 with 95\% key-cluster bootstrap intervals; Holm $p$ is the key-clustered sign test across the three conditions.}
\label{tab:main}
\begin{tabular}{@{}lccc@{}}
\toprule
 & RAND & TYPE-I & NCW-shallow \\
\midrule
Keys & 92 & 94 & 92 \\
C0 failures/decodings & 282/276{,}000 & 372/282{,}000 & 141/276{,}000 \\
C0 DFR & $1.02\times10^{-3}$ & $1.32\times10^{-3}$ & $5.11\times10^{-4}$ \\
FRO-2 failures/decodings & 68/276{,}000 & 68/282{,}000 & 31/276{,}000 \\
FRO-2 DFR & $2.46\times10^{-4}$ & $2.41\times10^{-4}$ & $1.12\times10^{-4}$ \\
RR [95\% CI] & 4.15 [3.29, 5.38] & 5.47 [4.25, 7.28] & 4.55 [3.21, 6.82] \\
Holm $p$ & $4.88\times10^{-17}$ & $3.05\times10^{-22}$ & $7.66\times10^{-12}$ \\
\bottomrule
\end{tabular}
\end{table}""",
    "tab:temporal": r"""\begin{table}[!tb]
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\caption{Expanded temporal confirmation at P2 $(3001,37,66)$ and P3 $(4001,41,82)$; NCW = NCW-shallow, UNIF-2 = UNIFORM-2. The C0 column is the absolute DFR; the remaining entries are RR (C0 over the schedule), with intervals in Figure~\ref{fig:temporal}. Each cell uses 50 keys with 1{,}000 errors.}
\label{tab:temporal}
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
Test cell & C0 & FRO-1 & FRO-2 & FRO-3 & R2-2 & UNIF-2 \\
\midrule
P2 RAND & $2.56\times10^{-3}$ & 2.56 & 2.37 & 1.91 & 1.13 & 0.0135 \\
P2 TYPE-I & $3.14\times10^{-3}$ & 2.31 & 2.85 & 2.15 & 1.29 & 0.0188 \\
P2 NCW & $1.20\times10^{-3}$ & 1.76 & 3.00 & 2.50 & 1.36 & 0.00949 \\
P3 RAND & $1.10\times10^{-3}$ & 2.29 & 2.62 & 2.62 & 1.34 & 0.00951 \\
P3 TYPE-I & $1.70\times10^{-3}$ & 3.27 & 3.27 & 2.18 & 1.31 & 0.0165 \\
P3 NCW & $7.40\times10^{-4}$ & 3.70 & 4.62 & 3.08 & 1.54 & 0.00925 \\
\bottomrule
\end{tabular}
\end{table}""",
    "tab:added": r"""\begin{table}[!tb]
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\caption{Production-scale checks. RR is C0 over the variant with 95\% intervals; each row gives failures over decodes per arm. At the production weight, zero events in 32{,}000 decodes give a $9.4\times10^{-5}$ bound per arm, not a security guarantee.}
\label{tab:added}
\begin{tabular}{@{}llrrr@{}}
\toprule
Setting & Variant & Failures & Decodes & RR [95\% CI] \\
\midrule
\multirow{3}{*}{raised $(12323,71,172)$} & C0 & 94 & 48{,}000 & -- \\
 & FRO-2 & 21 & 48{,}000 & 4.48 [2.97, 7.25] \\
 & FRONEG & 582 & 48{,}000 & 0.162 [0.119, 0.209] \\
\midrule
\multirow{2}{*}{production $(12323,71,134)$} & C0 & 0 & 32{,}000 & -- \\
 & FRO-2 & 0 & 32{,}000 & -- \\
\midrule
\multirow{3}{*}{CPA-128 $(10163,71,140)$} & C0 & 134 & 160{,}000 & -- \\
 & FRO-2 & 27 & 160{,}000 & 4.96 [3.68, 7.19] \\
 & FRONEG & 756 & 160{,}000 & 0.177 [0.148, 0.210] \\
\bottomrule
\end{tabular}
\end{table}""",
    "tab:modern": r"""\begin{table}[!tb]
\centering
\footnotesize
\setlength{\tabcolsep}{3pt}
\caption{Modern-decoder comparison at $P_1'=(4801,45,92)$; entries are DFR. C0 and FRO-2 are in Table~\ref{tab:main}. $p$ compares BIKE-Flip with FRO-2 (exact McNemar); RR is C0 over BGF-C3 with a 95\% archived interval. All comparators share paired static instances; BIKE-Flip uses the 20-round budget while the specification stops at seven. Tests are nominal and instance-level, not key-clustered or multiplicity-adjusted.}
\label{tab:modern}
\begin{tabular}{@{}lrrrr@{}}
\toprule
Condition & BIKE-Flip & BGF-C3 & $p$ & RR [95\% CI] \\
\midrule
RAND & $3.007\times10^{-4}$ & $1.040\times10^{-3}$ & $0.228$ & 0.983 [0.836, 1.156] \\
TYPE-I & $3.333\times10^{-4}$ & $1.387\times10^{-3}$ & $0.0292$ & 0.951 [0.837, 1.086] \\
NCW-shallow & $2.101\times10^{-4}$ & $3.043\times10^{-4}$ & $0.00244$ & 1.679 [1.362, 2.111] \\
\bottomrule
\end{tabular}
\end{table}""",
}


def recut_tables(tex: str) -> str:
    """Replace each table float with its LNCS-width variant, matched by label."""
    def repl(m):
        block = m.group(0)
        for label, new in LNCS_TABLES.items():
            if r"\label{%s}" % label in block:
                return new
        return block

    return re.sub(r"\\begin\{table\}\[!t\].*?\\end\{table\}", repl, tex, flags=re.S)


NUM_RE = re.compile(
    r"([0-9]*\.?[0-9]+)E(-?[0-9]+)"
    r"|([0-9]{1,3}(?:,[0-9]{3})+(?:\.?[0-9]+)?)"
    r"|([0-9]*\.?[0-9]+)")


def numeric_tokens(text: str) -> set[float]:
    text = text.replace("{,}", ",").replace("\\,", "").replace("~", " ")
    text = re.sub(r"\\times\s*10\^", "E", text)
    text = re.sub(r"E\{(-?[0-9]+)\}", r"E\1", text)
    out = set()
    for m in NUM_RE.finditer(text):
        try:
            if m.group(1) is not None:
                out.add(float(m.group(1)) * 10 ** int(m.group(2)))
            elif m.group(3) is not None:
                out.add(float(m.group(3).replace(",", "")))
            else:
                out.add(float(m.group(4)))
        except (ValueError, OverflowError):
            pass
    return out


def main():
    parts = []
    for name in ORDER:
        p = SECT / f"{name}.tex"
        assert p.exists(), f"missing fragment {p}"
        t = p.read_text(encoding="utf-8").rstrip()
        t = re.sub(r"\\end\{document\}\s*$", "", t).rstrip()
        parts.append(recut_tables(single_column(t)))
    ap = BASE / "plan" / "abstract.txt"
    abstract = ap.read_text(encoding="utf-8").strip() if ap.exists() else "[ABSTRACT PENDING]"
    body = PREAMBLE.replace("__ABSTRACT__", abstract) + "\n".join(parts) + BACKMATTER

    # Move Table 4 next to its first reference so it does not drift two pages
    # downstream in the single-column build.
    modern = LNCS_TABLES["tab:modern"]
    marker = "while the specification stops at seven."
    if modern in body and marker in body:
        body = body.replace(modern, "", 1)
        body = body.replace(marker, marker + "\n\n" + modern, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "main.tex").write_text(body, encoding="utf-8")
    shutil.copyfile(BASE / "en" / "refs.bib", OUT / "refs.bib")
    shutil.copyfile(LNCS / "llncs.cls", OUT / "llncs.cls")
    shutil.copyfile(LNCS / "splncs04.bst", OUT / "splncs04.bst")

    # The recut tables are hand-copied; guard against a value that is not also
    # in the numerically gated IEEE build.
    ieee = (BASE / "en" / "main.tex").read_text(encoding="utf-8")
    extra = numeric_tokens(body) - numeric_tokens(ieee)
    if extra:
        print("WARNING: LNCS numbers absent from the gated IEEE source:",
              sorted(extra))
    else:
        print("numeric check: every LNCS number also appears in the IEEE source")

    print(f"assembled {OUT / 'main.tex'}  ({len(body)} chars, {len(ORDER)} fragments)")


if __name__ == "__main__":
    main()
