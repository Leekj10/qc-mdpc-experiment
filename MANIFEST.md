# MANIFEST — data and code release (2026-10-25)

## Tree

```
qc-mdpc-experiment/
├── README.md
├── MANIFEST.md
├── LICENSE
├── lw-vs/
│   ├── data/                  exported CSV tables (36 files)
│   ├── data/figure_source/    per-cell figure/table source tables
│   ├── results/               frozen paper-level archives
│   ├── scripts/               experiment drivers, exporters, numeric gate
│   └── paper/                 main.tex (EN/ZH) only, as gate input
├── 实验/
│   ├── qcmdpc-study/          Python implementation, configs, tests, raw results
│   └── qcmdpc_decoder_ref/    C reference implementation (source)
└── new/                       comparison data shares
```

## Reproducibility chain (claim → data → gate)

| Manuscript item | Source chain | Gate check |
|---|---|---|
| Table I, Figure 2: primary formal comparison | `实验/qcmdpc-study/results/m5_formal/` → `lw-vs/data/t1_formal_main.csv`, `t1_per_key.csv`, `t1_gate_fresh.csv` | `check_formal` |
| Table II: expanded temporal confirmation | `lw-vs/results/round_controls/` + `实验/qcmdpc-study/results/p2second_transfer/` → `lw-vs/data/t2_expanded_temporal.csv`, `t2_temporal_pivot.csv` | `check_temporal` |
| Figure 3: offset window (figure-only) | `lw-vs/results/offset_scan_p1p/` → `lw-vs/data/t1_offset_scan_p1p.csv` | figure source only |
| Round controls | `lw-vs/results/round_controls/` → `lw-vs/data/t1_round_controls.csv` | `check_round_controls` |
| Figure 5: first-round mechanism | `实验/qcmdpc-study/results/firstround_mech/` → `t1_mechanism_firstround.csv`, `t1_mechanism_transitions.csv`, `t1_failure_modes*.csv` | `check_mechanism` |
| Figure 6: transfer, sweep, low-rate end | `实验/qcmdpc-study/results/p2second_transfer/` + `lw-vs/results/tier_upgrade/` → `t2_transfer_p2.csv`, `t3_iteration_budget.csv`, `t1_t_sensitivity.csv`, `t1_larger_r.csv`, `t3_parameter_sweep.csv` | `check_scope`, `check_robustness`, `check_parameter_sweep` |
| Table III: raised / native / CPA-128 | `lw-vs/results/tier_upgrade/`, `fair_l1/`, `cpa128_window/`, `cpa128_scan/` → `t5_tier_upgrade.csv`, `t1_fair_l1.csv`, `t1_cpa128.csv` | `check_tier_upgrade`, `check_fair_l1`, `check_cpa128` |
| Table IV: modern decoders | `new/modern_comparison_data/` + `lw-vs/results/bgf_baseline/` → `t1_modern_scaled.csv`, `t1_bgf_baseline.csv`, `t1_bgf_affine_boundary.csv` | `check_modern`, `check_bgf_baseline` |
| C reference cost | `lw-vs/results/c_cost/` → `t1_c_cost.csv`, `t1_c_cost_relative.csv` | `check_c_cost` |
| NCW-aware capture | `lw-vs/results/ncw_aware/` → `t1_ncw_aware_p1p.csv`, `t1_ncw_aware_capture.csv` | `check_ncw_aware` |
| Exact-recovery audit | `实验/qcmdpc-study/results/exact_recovery_audit_20260923/` → `t1_exact_recovery.csv` | `check_formal` |
| Offset-selection rule (archive only) | `lw-vs/results/offset_rule/` → `t1_offset_rule_profile.csv`, `t1_offset_rule_validation.csv` | `check_offset_rule` (presence-conditional) |
| Figure source tables | `lw-vs/data/figure_source/*.csv` | raw cells behind every table and figure |
| Seeds | master seed `20260901`, SHA-256 derivation in `实验/qcmdpc-study/qcmdpc/generators.py` | — |

Every gate check maps a manuscript value onto the CSV exports and requires agreement
within 0.6% (3-significant-figure convention).

## Gate status

```
python lw-vs/scripts/verify_numbers.py
```

At release: **382 checks, PASS**. PDF-level checks are skipped when the compiled
PDFs are absent, as in this repository; they run in the full manuscript package.

## Notes

- The static-semantics C build (`实验/qcmdpc-study/static_build/decoder_static.c`)
  is included for reruns; its L1 counts are archived but not quoted in the paper.
- C reference timings used `zig cc -O2`, AVX disabled, single-threaded; only the
  C0/FRO-2 ratio is interpreted.
- The offset scan backs Figure 3; its exact per-cell intervals are archived in
  `lw-vs/data/t1_offset_scan_p1p.csv`.

## Not included

Manuscript PDFs, LaTeX templates, figure build artifacts, old drafts, debug
symbols, Windows binaries and third-party paper PDFs.
