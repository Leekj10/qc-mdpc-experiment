# lw-vs — QC-MDPC 首轮阈值时序（当前交付包）

本目录的当前稿件是 `v3/`。旧版 `en/`、`zh/`、`10.12/`、`optimized/` 以及旧图、
评审报告和图件候选已于 2026-10-23 清理，不再保留。

## 当前文章

| 版本 | 路径 | 页数 |
|---|---|---|
| 双栏 EN | `v3/en/main.pdf` | 10 |
| 双栏 ZH | `v3/zh/main.pdf` | 9 |
| 单栏 EN | `v3/single/en/main.pdf` | 11 |
| 单栏 ZH | `v3/single/zh/main.pdf` | 10 |
| LNCS 单栏 EN | `v3/llncs/en/main.pdf` | 18 |

- 6 张图、4 张表（Table I–IV）。
- 单栏版为 IEEEtran `onecolumn`，版心宽约 7.16 in，图保持原始尺寸；
  中文单栏为 ctexart `onecolumn`。
- LNCS 版为 `llncs.cls` 单栏（版心 4.82 in），六张图按版心缩放，
  四张表为窄版重排（Table 1 转置、Table 4 省略已在 Table 1 的 C0/FRO-2 两列），
  数值不变。
- 数值门禁：`python lw-vs/scripts/verify_numbers.py`（默认检查 `v3/en` 与 `v3/zh`），
  当前 **382 PASS**。

## 构建

```bash
# 双栏
python lw-vs/v3/plan/assemble.py
cd lw-vs/v3/en && pdflatex main && bibtex main && pdflatex main && pdflatex main

python lw-vs/v3/plan/assemble_zh.py
cd lw-vs/v3/zh && xelatex main && bibtex main && xelatex main && xelatex main

# 单栏（从当前双栏稿生成）
python lw-vs/v3/plan/_make_single.py
cd lw-vs/v3/single/en && pdflatex main && bibtex main && pdflatex main && pdflatex main
cd lw-vs/v3/single/zh && xelatex main && bibtex main && xelatex main && xelatex main

# LNCS 单栏（同一套英文分节源，窄版表格由 assemble_llncs.py 重排）
python lw-vs/v3/plan/assemble_llncs.py
cd lw-vs/v3/llncs/en && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

## 目录

- `v3/plan/sections/`, `v3/plan/sections_zh/` — 分节源文件
- `v3/plan/assemble.py`, `assemble_zh.py`, `_make_single.py`, `assemble_llncs.py` — 组装脚本
- `v3/llncs/en/` — LNCS 单栏稿（`llncs.cls`、`splncs04.bst` 随稿复制）
- `v3/refs_pdf/` — 正文 26 篇参考文献的 PDF（按引用编号命名，`README.md` 列出未获取的 8 篇及链接）
- `v3/figures/` — 正文实际引用的图（`fig1`–`fig6`，PDF/SVG/PNG）
- `v3/figure_redesign_2026-10-23/` — 最新图件源包与图注/核验记录
- `v3/scripts/` — 图件生成与调色板校验
- `data/` — 图源 CSV；`results/` — 实验归档；`scripts/` — 导出与数值门禁
- `实验/qcmdpc-study/` — 译码实验与参考实现代码
- `new/` — 早期分析脚本与数据（保留，不属于当前稿件）
- `文献阅读/` — 领域参考文献

## 归档

当前归档为 `../zenodo_stage/qc-mdpc-experiment-v3/`（含上传 zip），
可由 `../zenodo_stage/build_zenodo_package_v3.py` 从当前 `lw-vs/`、`实验/`、`new/` 重建；
包内 `README.md` 与 `MANIFEST.md` 给出“声明 → 路径”和“稿件条目 → 数据链 → 门禁”的对照。
旧的 `qc-mdpc-experiment-v2/` 对应 2026-10-11 的旧稿，不再使用。
项目根目录的 `代码与数据索引.md` 是同一份索引的简版。
