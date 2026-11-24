# QC-MDPC threshold and post-processing experiments

**Article:** First-Round Post-Processing Can Reverse the Effect of a Higher Threshold in QC-MDPC Bit-Flipping Decoding
**Journal:** Journal of Cryptographic Engineering (manuscript submission)
**Authors:** Guangfu Wu, Kangjun Li, and Rui Wu
**Corresponding author:** Rui Wu, School of Industrial Software, Jiangxi University of Science and Technology, Nanchang, Jiangxi, China; wuruiset_cn@163.com
**Dataset version:** 2026.11.24

This archive contains simulation outputs, configurations, analysis code, and the inputs, script and vector outputs for the seven manuscript figures. The manuscript's supplementary PDF is supplied separately. The two primary work points use 46 keys and 2,000 matched error samples per key in each sample pool. Original and confirmation pools are stored separately.

## Reproduce the results from the saved outputs

1. Use Python 3.12, NumPy and Matplotlib. The exact plotting environment is in `figures_jcen/requirements.txt`. Arial is recommended for matching typography; Matplotlib can fall back to DejaVu Sans.
2. From the extracted archive root, run `python -I figures_jcen/scripts/check_factor.py`. This recomputes Tables 2–3 and the Figure 2 inputs from the four stored `.npz` files, then verifies the values against the included CSVs. It does not rerun decoding.
3. To re-render Figures 1–7, run `python -I figures_jcen/scripts/make_figures.py`. New renders go to `figures_jcen/figures/`; the vector files submitted with the manuscript are in `figures_jcen/final_pdf/` and are not overwritten. Matching data and geometry do not require byte-identical PDF metadata across systems.
4. For a selective integrity check, compare any file against `SHA256SUMS.txt`. The manifest covers all content files in this release except itself.

## Manuscript-to-data index

| Manuscript evidence | Source in the archive |
| --- | --- |
| Fig. 1: factorial design | `figures_jcen/scripts/make_figures.py` |
| Fig. 2 and Tables 2–3: post-step interaction, confirmation and work counts | `figures_jcen/source_data/factor_offset_contrasts.csv`, `factor_interaction.csv`, `factor_counts_and_work.csv`; paired outputs in `lw-vs/audit_2026-11-11/poststep_factor/` |
| Fig. 3: separate initial-flip census | `figures_jcen/source_data/t1_mechanism_firstround.csv` |
| Table 4 and Supplementary Tables S2, S3 and S6: first-round composition, components and masks | `lw-vs/audit_2026-11-11/poststep_factor/poststep_census_summary*.json`, the corresponding `.npz` files and factor summaries |
| Fig. 4, Table 5 and Supplementary Table S8: aggregate and per-key reference-schedule results | `figures_jcen/source_data/t1_formal_main.csv`, `t1_per_key.csv`; C replication checks in `lw-vs/scripts/replication/results/` |
| Fig. 5: local offset scan | `figures_jcen/source_data/t1_offset_scan_p1p.csv` |
| Fig. 6 and Supplementary Table S9: offset timing | `figures_jcen/source_data/t1_round_controls.csv`, `t2_expanded_temporal.csv`; additional outputs in `new/expanded_data/` |
| Fig. 7 and Supplementary Sections S11–S13: transfer and boundary results | `figures_jcen/source_data/t2_transfer_p2.csv`, `t3_capture_gradient.csv`, `t1_ncw_aware_capture.csv`; production-block inputs `lw-vs/data/t1_cpa128.csv`, `lw-vs/data/t1_native_l1.csv` |
| Table 6 and Supplementary Table S7: within-decoder contrasts | `lw-vs/results/decoder_transfer/` |
| Supplementary Table S10: common-budget comparison | `lw-vs/data/t1_modern_scaled.csv` and `实验/qcmdpc-study/results/` |
| Simulation configurations and implementation | `实验/qcmdpc-study/configs/`, `实验/qcmdpc-study/qcmdpc/`, `实验/qcmdpc_decoder_ref/qcmdpc_decoder-master/`, `lw-vs/audit_2026-11-11/exp_poststep_*.py` and `lw-vs/scripts/` |

The archived simulation scripts sometimes use platform-specific build or compiler settings. For those scripts, see `实验/qcmdpc-study/reference/BUILD_WINDOWS.md` and `new/requirements.txt`. This release contains no full manuscript PDF, publisher PDFs, or binary executables. See `LICENSE` and the bundled notices under `实验/qcmdpc_decoder_ref/qcmdpc_decoder-master/` for software licensing.
