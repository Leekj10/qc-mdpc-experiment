# -*- coding: utf-8 -*-
"""Assemble v3/en/main.tex from the freshly drafted section fragments.

The preamble, abstract and back matter are written here (framework code, not
article prose).  Section fragments come from plan/sections/s*.tex in order.
"""
import io
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SECT = BASE / "plan" / "sections"
ORDER = ["s01_intro", "s02_background", "s03_model", "s04_design",
         "s05_results_window", "s06_results_mechanism", "s07_results_boundary",
         "s08_results_negatives", "s09_discussion"]

PREAMBLE = r"""% v3 manuscript (fresh draft; architecture: plan/architecture.md)
% Build: pdflatex main -> bibtex main -> pdflatex main -> pdflatex main
\documentclass[lettersize,journal]{IEEEtran}

\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{array}
\usepackage{multirow}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{algorithm}
\usepackage{algpseudocode}

\graphicspath{{../figures/}}

\newcommand{\dblfig}[3]{%
  \begin{figure*}[!t]\centering
    \includegraphics[width=\textwidth]{#1}%
    \caption{#2}\label{#3}
  \end{figure*}}
\newcommand{\onefig}[4]{%
  \begin{figure}[!t]\centering
    \includegraphics[width=\columnwidth]{#1}%
    \caption{#2}\label{#3}\vspace{#4}
  \end{figure}}

\begin{document}

\title{The First Round Is a Two-Sided Window: Threshold Timing and
Conditional Decoding Failure in QC-MDPC Bit-Flipping}

\author{[Author names and affiliations to be completed before submission]%
\thanks{[Corresponding-author e-mail to be completed.]}}

\maketitle

\begin{abstract}

__ABSTRACT__

\end{abstract}

\begin{IEEEkeywords}
post-quantum cryptography, QC-MDPC codes, bit-flipping decoding, decoding
failure rate, first-round threshold, threshold timing, key-conditional risk.
\end{IEEEkeywords}

"""

BACKMATTER = r"""
% ===========================================================================
\section*{Data and Code Availability}
The implementation, frozen configurations, seed derivation rules, raw per-key counts, and analysis code are archived at \url{https://doi.org/10.5281/zenodo.22296719}, with a development mirror at \url{https://github.com/Leekj10/qc-mdpc-experiment}. The figure source tables and a checking script that re-derives every quoted value from the archived counts are released with the same archive.

\bibliographystyle{IEEEtran}
\bibliography{refs}

\end{document}
"""


def main(abstract: str | None = None):
    parts = []
    for name in ORDER:
        p = SECT / f"{name}.tex"
        assert p.exists(), f"missing fragment {p}"
        t = p.read_text(encoding="utf-8").rstrip()
        t = re.sub(r"\\end\{document\}\s*$", "", t).rstrip()
        parts.append(t)
    if abstract is None:
        ap = BASE / "plan" / "abstract.txt"
        abstract = ap.read_text(encoding="utf-8").strip() if ap.exists() else "[ABSTRACT PENDING]"
    body = PREAMBLE.replace("__ABSTRACT__", abstract) + "\n".join(parts) + BACKMATTER
    out = BASE / "en" / "main.tex"
    out.write_text(body, encoding="utf-8")
    print(f"assembled {out}  ({len(body)} chars, {len(ORDER)} fragments)")


if __name__ == "__main__":
    main()
