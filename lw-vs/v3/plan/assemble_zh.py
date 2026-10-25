# -*- coding: utf-8 -*-
"""Assemble v3/zh/main.tex from the mirrored zh fragments (plan/sections_zh)."""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SECT = BASE / "plan" / "sections_zh"
ORDER = ["s01_intro", "s02_background", "s03_model", "s04_design",
         "s05_results_window", "s06_results_mechanism", "s07_results_boundary",
         "s08_results_negatives", "s09_discussion"]

PREAMBLE = r"""% !TEX program = xelatex
% v3 中文镜像稿（架构：plan/architecture.md；对应 en/main.tex 逐节镜像）
% 编译：xelatex main -> bibtex main -> xelatex main -> xelatex main
\documentclass[UTF8,a4paper,10pt,twocolumn]{ctexart}

\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{array}
\usepackage{url}
\usepackage[hidelinks]{hyperref}
\usepackage{enumitem}
\usepackage{algorithm}
\usepackage{algpseudocode}

\usepackage{geometry}
\geometry{a4paper,left=1.6cm,right=1.6cm,top=2.0cm,bottom=2.0cm,columnsep=0.65cm}
\setlength{\parindent}{2em}
\linespread{1.06}

\renewcommand{\figurename}{图}
\graphicspath{{../figures/}}
\renewcommand{\tablename}{表}
\captionsetup{font=small,labelfont=bf,labelsep=quad}

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

\title{\vspace{-1.2em}\heiti\zihao{3} 首轮是一个双向窗口：QC-MDPC\\比特翻转译码中的阈值时序与条件失败}

\author{\zihao{5} [作者姓名待补充]\\[0.2em]
\zihao{6}\mdseries [单位与通讯邮箱待补充]}

\date{}

\begin{document}

\maketitle

\begin{abstract}
BIKE 等 QC-MDPC 方案的安全性论证依赖一个任何模拟都无法测量的失败率目标（约 $2^{-128}$），也依赖译码行为在无法逐一检查的密钥之间保持稳定。本文考察 BF 译码器的阈值调度能在多大程度上控制条件失败。我们把两条调度施加于完全相同的密钥、错误与综合征（配对实例），并在全部推断中重抽密钥而非错误。CLASSIC BF 译码器的首轮是一个陡峭且不对称的双向窗口：把其阈值提高 1 至 3，三个正式条件上的条件失败率下降 2.3--5.5 倍；降低 1，恶化约八倍；降低 2，恶化超过两个数量级。偏移的轮次与持续方式和幅度同等重要：同一偏移只作用于自身那一轮时有益，持续贯穿后续轮次时则使失败率升至约 4--6\%，即便第 1 轮未被触及。首轮记录解释了这一不对称：错误的首轮翻转下降得远多于正确翻转，即干预剔除的是错误决策，而非加速纠错。效应无需重调即迁移到第二个工作点与更大的码，并在所测的捕获倾向构造处止步。在生产块尺寸上，错误重量一经抬高，窗口即复现；在生产重量本身只有决策余量与收敛代价可测。一个首轮代理模型未能预测另一套调度的效应，本文诊断了失败原因。
\end{abstract}

\vspace{0.6em}

\noindent\textbf{关键词：}后量子密码；QC-MDPC 码；比特翻转译码；解码失败率；首轮阈值；阈值时序；密钥条件风险。

\vspace{0.8em}

"""

BACKMATTER = r"""
% ===========================================================================
\section*{数据与代码可用性}
\addcontentsline{toc}{section}{数据与代码可用性}
实现、冻结配置、种子派生规则、逐密钥原始计数与分析代码归档于 \url{https://doi.org/10.5281/zenodo.22296719}，开发镜像见 \url{https://github.com/Leekj10/qc-mdpc-experiment}。图源数据表与把正文引用的每个数值与归档计数逐一重新核对的校验脚本随同一归档发布。

\bibliographystyle{IEEEtran}
\bibliography{refs}

\end{document}
"""


def main():
    parts = []
    for name in ORDER:
        p = SECT / f"{name}.tex"
        assert p.exists(), f"missing zh fragment {p}"
        t = p.read_text(encoding="utf-8").rstrip()
        t = re.sub(r"\\end\{document\}\s*$", "", t).rstrip()
        parts.append(t)
    body = PREAMBLE + "\n".join(parts) + BACKMATTER
    out = BASE / "zh" / "main.tex"
    out.write_text(body, encoding="utf-8")
    print(f"assembled {out}  ({len(body)} chars, {len(ORDER)} fragments)")


if __name__ == "__main__":
    main()
