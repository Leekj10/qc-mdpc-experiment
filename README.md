# qc-mdpc-experiment-v3 — 数据与代码归档

发布日期：2026-10-25。对应当前稿件 `lw-vs/v3/`（双栏 EN/ZH、单栏 EN/ZH、LNCS EN）。

本包保留项目原始的相对目录结构（`lw-vs/`、`实验/`、`new/`），解压后所有脚本的
相对路径和数值门禁都可直接运行，无需改路径。

## 数据与代码可用性声明 → 实际位置

| 声明中的项目 | 实际位置 |
|---|---|
| 实现（Python 参考译码器） | `实验/qcmdpc-study/qcmdpc/`：`ring.py`、`generators.py`、`decoders.py`、`stats.py`、`taxonomy.py`、`bikeflip.py` |
| 冻结配置与预注册 | `实验/qcmdpc-study/configs/`（`pre_register.json`、各次运行配置） |
| 种子派生规则 | `实验/qcmdpc-study/qcmdpc/generators.py`；主种子 `20260901`，SHA-256 派生 |
| 原始逐钥计数 | `实验/qcmdpc-study/results/`（每次运行的 JSONL/summary/manifest）+ `lw-vs/results/`（论文级冻结归档） |
| 分析代码 | `lw-vs/scripts/`（实验驱动 `exp_*.py`、导出 `export_*.py`、门禁 `verify_numbers.py`）+ `实验/qcmdpc-study/*.py`（runner 与分析脚本） |
| 图源表 | `lw-vs/v3/figure_redesign_2026-10-23/source_data/`（逐表单元格）+ `lw-vs/data/`（正文引用的 CSV） |
| 校验脚本 | `lw-vs/scripts/verify_numbers.py`：从归档 CSV 重算每个引用值，并检查编译 PDF |
| 稿件源码 | `lw-vs/v3/plan/sections/`、`sections_zh/` 与 `assemble.py`、`assemble_zh.py`、`_make_single.py`、`assemble_llncs.py` |
| C 参考实现 | `实验/qcmdpc_decoder_ref/qcmdpc_decoder-master/`（源码，含 `CMakeLists.txt`） |
| 静态语义 C 载体 | `实验/qcmdpc-study/static_build/`（`decoder_static.c` 与构建说明） |

## 快速校验

```bash
# 数值门禁：382 项检查，期望 PASS
python lw-vs/scripts/verify_numbers.py

# Python 参考实现自检
cd 实验/qcmdpc-study && python tests/test_core.py
```

当前状态：**382 PASS**（在解压后的本目录内实测通过）。

## 目录

```
qc-mdpc-experiment-v3/
├── README.md                本文件
├── MANIFEST.md              稿件条目 → 数据链 → 门禁检查 对照表
├── LICENSE
├── lw-vs/
│   ├── v3/                  当前稿件源码、图、组装脚本
│   │   ├── plan/            分节源、abstract、allowed_numbers、组装脚本
│   │   ├── en/ zh/          双栏稿（tex + pdf + refs.bib）
│   │   ├── single/          单栏稿（IEEEtran/ctexart onecolumn）
│   │   ├── llncs/en/        LNCS 单栏稿
│   │   ├── figures/         正文六张图（PDF/SVG/PNG）
│   │   └── figure_redesign_2026-10-23/  当前图件生成器 + source_data
│   ├── data/                正文数值来源 CSV（36 个）
│   ├── results/             冻结实验归档（round_controls、offset_scan、tier_upgrade、fair_l1、cpa128、c_cost、ncw_aware、bgf_baseline 等）
│   └── scripts/             实验驱动、导出、数值门禁
├── 实验/
│   ├── qcmdpc-study/        Python 参考实现、预注册配置、运行结果、static_build
│   └── qcmdpc_decoder_ref/qcmdpc_decoder-master/   C 参考实现源码
├── new/                     审计文档 + 比较数据（modern / engineering / ncw_adaptive）
└── llncs/                   LNCS 模板（llncs.cls、splncs04.bst），供 assemble_llncs.py 使用
```

## 与旧版 v2 包的关系

`qc-mdpc-experiment-v2`（2026-10-11）对应旧的双栏稿与旧图件，**不包含** v3 稿、
2026-10-18 的局部偏移扫描和 2026-10-23 的图件重做；不要再用它核对当前正文。
本 v3 包是当前唯一与 `lw-vs/v3` 数值一致的归档。

## 未包含

- 第三方论文 PDF（`lw-vs/v3/refs_pdf/`、`实验/参考文献/`）：版权原因不入归档，
  引用清单见稿件参考文献。
- `figure_redesign_2026-10-23/` 的中间候选图、调色板预览和候选 PDF/ZIP：只保留
  `build_figures.py`、`captions.json`、`source_data/` 和审计记录。
- 旧稿件草稿（`实验/qcmdpc-study/paper/`）、`__pycache__`、`*.pdb`、Windows 二进制。
