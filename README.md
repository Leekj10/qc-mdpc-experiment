# qc-mdpc-experiment — data and code

Data and analysis code for the manuscript *The First Round Is a Two-Sided Window:
Threshold Timing and Conditional Decoding Failure in QC-MDPC Bit-Flipping*.

This repository is the development mirror of the citable archive. It contains the
implementation, the frozen experiment archives, the exported tables, the figure
source data and the numeric gate. It intentionally does **not** contain manuscript
PDFs, LaTeX templates or figure build artifacts.

## Layout

```
lw-vs/
  data/                  exported CSV tables behind every quoted number
  data/figure_source/    per-cell source tables behind the figures and tables
  results/               frozen paper-level experiment archives (JSON)
  scripts/               experiment drivers, exporters, numeric gate
  scripts/replication/   same-pool independent C replication (exact per-key check)
  paper/                 only main.tex (EN/ZH), used as input by the gate
实验/
  qcmdpc-study/          Python reference implementation, configs, tests, raw results
  qcmdpc_decoder_ref/    C reference implementation (source)
new/                     comparison data shares
```

## Verify the numbers

```bash
python lw-vs/scripts/verify_numbers.py
```

The gate recomputes every quoted value from `lw-vs/data/*.csv` and checks it
against the manuscript source. With no compiled PDFs in this repository, the
PDF-level checks are skipped automatically; the numeric checks all run.
Expected result: **382 checks, PASS**.

## Code map

| Component | Path |
|---|---|
| Python reference decoder | `实验/qcmdpc-study/qcmdpc/` |
| Experiment runner and analyses | `实验/qcmdpc-study/*.py`, `tests/` |
| Frozen configurations / preregistration | `实验/qcmdpc-study/configs/` |
| Seed derivation | `实验/qcmdpc-study/qcmdpc/generators.py` (master seed `20260901`, SHA-256) |
| Export / analysis / gate | `lw-vs/scripts/` |
| Independent same-pool C replication | `lw-vs/scripts/replication/` |
| C reference decoder | `实验/qcmdpc_decoder_ref/qcmdpc_decoder-master/` |
| Static-semantics C carrier | `实验/qcmdpc-study/static_build/` |

## Data map

| Data | Path |
|---|---|
| Number-source CSV tables | `lw-vs/data/` |
| Per-cell figure/table sources | `lw-vs/data/figure_source/` |
| Frozen paper-level archives | `lw-vs/results/` |
| Raw study outputs (per-run JSON) | `实验/qcmdpc-study/results/` |
| Comparison data | `new/` |

The item-by-item map from manuscript claim to data chain and gate check is in
[MANIFEST.md](MANIFEST.md).
