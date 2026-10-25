# MANIFEST — release v3.0 (2026-10-25)

## Tree (top three levels)

```
qc-mdpc-experiment-v3/                      ~22 MB, 745 files
├── README.md                               guide: statement → actual path
├── MANIFEST.md                             this file
├── LICENSE                                 MIT (c) 2026 LeeKJ
├── lw-vs/
│   ├── v3/{en,zh,single,llncs}             current manuscripts (tex + pdf + bib)
│   ├── v3/plan/                            section sources + assemblers
│   ├── v3/figures/                         six body figures (PDF/SVG/PNG)
│   ├── v3/figure_redesign_2026-10-23/      build_figures.py, captions.json, source_data/
│   ├── data/                               36 CSV number-source tables
│   ├── results/                            frozen paper-level archives
│   └── scripts/                            experiment drivers, exports, numeric gate
├── 实验/
│   ├── qcmdpc-study/                       Python reference implementation, configs, results, static_build
│   └── qcmdpc_decoder_ref/qcmdpc_decoder-master/   C reference (source only)
├── new/                                    audit docs + comparison data shares
└── llncs/                                  LNCS class + bibliography style
```

## Reproducibility chain (paper item → source → gate)

| Manuscript item | Source chain | Gate check |
|---|---|---|
| Table I, Figure 2: primary formal comparison | `实验/qcmdpc-study/results/m5_formal/` → `lw-vs/data/t1_formal_main.csv`, `t1_per_key.csv`, `t1_gate_fresh.csv` | `check_formal` |
| Table II: expanded temporal confirmation | `lw-vs/results/round_controls/` + `实验/qcmdpc-study/results/p2second_transfer/` → `lw-vs/data/t2_expanded_temporal.csv`, `t2_temporal_pivot.csv` | `check_temporal` |
| Figure 3: offset window (figure-only; exact CIs archived) | `lw-vs/results/offset_scan_p1p/` → `lw-vs/data/t1_offset_scan_p1p.csv` | not a quoted numeric claim; source exported for the figure |
| Round controls (RR at round 2, sustained offset) | `lw-vs/results/round_controls/` → `t1_round_controls.csv` | `check_round_controls` |
| Figure 5: first-round mechanism | `实验/qcmdpc-study/results/firstround_mech/` → `t1_mechanism_firstround.csv`, `t1_mechanism_transitions.csv`, `t1_failure_modes*.csv` | `check_mechanism` |
| Figure 6: transfer, sweep, low-rate end | `实验/qcmdpc-study/results/p2second_transfer/` + `lw-vs/results/tier_upgrade/` → `t2_transfer_p2.csv`, `t3_iteration_budget.csv`, `t1_t_sensitivity.csv`, `t1_larger_r.csv`, `t3_parameter_sweep.csv` | `check_scope`, `check_robustness`, `check_parameter_sweep` |
| Table III: raised weight / native weight / CPA-128 | `lw-vs/results/tier_upgrade/`, `fair_l1/`, `cpa128_window/`, `cpa128_scan/` → `t5_tier_upgrade.csv`, `t1_fair_l1.csv`, `t1_cpa128.csv` | `check_tier_upgrade`, `check_fair_l1`, `check_cpa128` |
| Table IV: modern decoders | `new/modern_comparison_data/` + `lw-vs/results/bgf_baseline/` → `t1_modern_scaled.csv`, `t1_bgf_baseline.csv`, `t1_bgf_affine_boundary.csv` | `check_modern`, `check_bgf_baseline` |
| C reference cost paragraph | `lw-vs/results/c_cost/` → `t1_c_cost.csv`, `t1_c_cost_relative.csv` | `check_c_cost` |
| NCW-aware capture | `lw-vs/results/ncw_aware/` → `t1_ncw_aware_p1p.csv`, `t1_ncw_aware_capture.csv` | `check_ncw_aware` |
| Exact-recovery audit | `实验/qcmdpc-study/results/exact_recovery_audit_20260923/` → `t1_exact_recovery.csv` | `check_formal` |
| Offset-selection rule (archive only) | `lw-vs/results/offset_rule/` → `t1_offset_rule_profile.csv`, `t1_offset_rule_validation.csv` | `check_offset_rule` (presence-conditional) |
| Figure source tables | `lw-vs/v3/figure_redesign_2026-10-23/source_data/*.csv` | raw cells behind every table and figure |
| Seeds | master seed `20260901`, SHA-256 derivation in `实验/qcmdpc-study/qcmdpc/generators.py` | — |

Every gate check maps a manuscript value onto the CSV exports and requires agreement
within 0.6% (3-significant-figure convention). `verify_numbers.py` also checks the
compiled PDFs (broken references, leaked markup, sentinel values, lone-CR guard).

## Current gate status

Run inside this directory:

```
python lw-vs/scripts/verify_numbers.py
```

Result at packaging time: **382 checks, PASS**.

## Instrumentation notes

- The static-semantics C build (`实验/qcmdpc-study/static_build/decoder_static.c`,
  2-line `#ifdef STATIC_SEMANTICS` patch) is included for reruns. Its L1 counts are
  archived but not quoted in the current manuscript.
- The C reference calendar measurements (`lw-vs/results/c_cost/`) used
  `zig cc -O2`, AVX disabled, single-threaded; only the C0-vs-FRO-2 ratio is
  interpreted in the paper.
- The dynamic-semantics cross-checks used the reference implementation's
  `compute_threshold(syndrome_weight, e->weight)` branch; see
  `实验/qcmdpc-study/reference/FROZEN_REFERENCE_SEMANTICS.md`.
- The offset scan (`lw-vs/results/offset_scan_p1p/`) backs Figure 3. Its exact
  per-cell intervals are not printed in the current text; the CSV is included so
  the figure can be regenerated and the values audited.

## Exclusions

Third-party paper PDFs (`lw-vs/v3/refs_pdf/`, `实验/参考文献/`), intermediate
figure candidates, old manuscript drafts (`实验/qcmdpc-study/paper/`),
`__pycache__`, `*.pdb`, Windows binaries and LaTeX aux/log files are not included.
