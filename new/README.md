# New manuscript package

This folder contains a fully rewritten manuscript based on the archived QC-MDPC experiments. No pre-existing paper file was edited.

Current recommended title: **QC-MDPC 比特翻转译码的时序阈值整形：最小首轮干预下的条件 DFR 降低**.

English title: **Temporal Threshold Shaping for QC-MDPC Bit-Flipping Decoding: Conditional DFR Reduction with a Minimal First-Round Intervention**.

## Main files

- `manuscript.md`: source manuscript.
- `manuscript.tex`: standalone LaTeX source generated from the new manuscript.
- `manuscript_final.docx`: editable Word version with embedded figures and repaired OOXML image declarations. Regenerate after any source edit.
- `manuscript_en_final_v4.pdf`: English export generated from the current source after the rebuild step below; it is not a source of truth.
- `manuscript_zh.md`: complete Chinese translation of the rewritten manuscript.
- `manuscript_zh_final.docx`: Chinese Word export generated from the current source after the rebuild step below.
- `manuscript.html`, `manuscript_zh.html`: self-contained HTML sources used for the current PDF renders.
- `manuscript_zh_final_v4.pdf`: Chinese PDF export generated from the current source after the rebuild step below.
- `manuscript_zh_final_v3.pdf`: historical Chinese export; do not use it for submission.

## Journal-style deliverables

- `manuscript_en_journal_v4.tex`: updated IEEEtran-oriented English LaTeX entrypoint with the fairness partition, production-boundary check, pairwise uncertainty table, and claim--evidence map.
- `manuscript_zh_journal_v4.tex`: updated two-column ctexart Chinese LaTeX entrypoint with the same additions.
- The rewrite uses a shorter, result-led abstract; defines C0 at first use; presents the theory as a local UPC-tail model with testable predictions; and separates fair decoder comparison from production-reference evidence.

The current PDF deliverables are `manuscript_en_final_v4.pdf` and `manuscript_zh_final_v4.pdf`.
- `title_strategy_zh.md`: title-selection rationale and English correspondence.
- `comparison_with_bike_weakkey_zh.md`: comparison with the TIFS BIKE weak-key literature and prioritized optimization list.
- `reproducibility_terms_zh.md`: definitions of regression validation, cross-implementation checks, and independent-laboratory replication.
- `review_and_readiness_zh.md`: SCI Q2/Q3 peer-review-style assessment in Chinese.
- `quality_control.md`: section and manuscript quality checks.
- `figure_notes.md`: captions, alt text, integrity notes, and provenance.
- `build_repro_manifest.py`: writes a relative-path SHA-256 manifest for the
  source, experiment code, configurations, result summaries, and rebuild
  environment.
- `reproducibility_manifest.json`: generated provenance manifest; regenerate
  it after changing source, code, configuration, or result summaries.
- `make_figures.py`: deterministic figure and source-table generator.
- `publication_figures/`: final PDF, SVG, and 600-dpi PNG figures.
- `data/`: manuscript-facing CSV tables generated from archived JSON.
- `publication_figure_manifest.json`: final figure provenance and export settings.
- `supplemental_experiment_report_zh.md`: 新增时序位置、偏移幅度和第三工作点实验报告。
- `supplemental_experiments.py`, `analyze_supplemental.py`: 可重复的补充实验与密钥聚类分析脚本。
- `supplemental_data_full/`: 新种子 `20260911` 生成的逐条件矩阵和分析结果。
- `ncw_adaptive_experiment.py`: 固定预算的通用停滞触发—局部恢复原型；它不检测近码字结构，因此不作为 near-codeword-aware 方法声称。
- `ncw_adaptive_data_v2/`: 修正版 STLR 协议生成的 18 个实验单元、预注册协议、逐密钥计数和 post-round UPC 成本统计。
- `ncw_adaptive_data/`: 旧版 v1 结果归档，仅用于审计比较。
- `ncw_adaptive_report_zh.md`, `ncw_adaptive_report_en.md`: STLR 修正版实验的中英文报告。
- `publication_figures/fig6_ncw_adaptive.{pdf,svg,png}`: 通用停滞触发局部恢复原型的补充比较图（可作为补充图，不是主文必需图）。
- `engineering_compare_v2.py`, `analyze_engineering_v2.py`: 修正版 C0/FRO-2/STLR/SR-NCW/BGF-C3 工程对照；恢复后的 UPC 重算计入成本，G3 才使用严格近码字支持。
- `engineering_data_v2/engineering_cost_table.csv`: 由逐单元 JSON 自动汇总的 30 行工程成本表，包含失败数、DFR、迭代、UPC、试探、触发率、接受率和参考时间。
- `engineering_data_v2/engineering_pairwise_rr.csv`: 工程控制相对 C0/FRO-2 的密钥聚类 bootstrap 风险比区间。
- `fair_modern_decoder_protocol_en.md`, `fair_modern_decoder_protocol_zh.md`: 现代译码器比较的公平性分层、生产参考和语义边界。
- `modern_comparison_data/`: 包内复制的正式 BIKE-Flip P1' 和原生 Level-1 JSON 报告，便于独立核对比较数字。
- `实验/qcmdpc-study/results/exact_recovery_audit_20260923/`: formal P1' audit of zero-syndrome success versus exact error recovery; `formal_current/` is the latest merged replay and `formal_full/` is the earlier merged archive.
- `实验/qcmdpc-study/merge_exact_recovery_audit.py`: validates and merges independently completed exact-recovery groups into `formal_current/report.json`; it rejects protocol, parameter, key-range, per-key-count, and error-count mismatches. The current archive records compatible reporting-revision hashes by group and does not call them a single-hash rerun.
- `实验/qcmdpc-study/formal_m5_mechanism.py`: preregistered failure-mode rerun. The archived `results/m5_mechanism/` was generated before the corrected `ceil(max_iter/4)` window and remains exploratory until this script is rerun into a new directory.
- `实验/qcmdpc-study/reference/`: frozen C semantics, build command, and cross-validation record; the top-level provenance manifest hashes the C headers/sources and these reference notes.
- `engineering_comparison_report_zh_v2.md`, `engineering_comparison_report_en_v2.md`: 修正版工程对照结果的中英文报告。
- `engineering_data_v2/native_l1_holdout.json`: 原生 BIKE Level-1 非调参 hold-out 边界结果。
- `publication_figures/fig7_engineering_comparison.{pdf,svg,png}`: 五种译码器的 DFR 与平均迭代成本比较图。
- `verification_report.json`: automated package verification results.
- `repair_docx_zh.py`: Chinese Word image-content-type repair wrapper.

The manuscript uses five core figures (Figures 1--5) and treats Figures 6--7 as supplemental engineering/prototype figures unless the target journal requests them in the main text. The manifest records all seven available exports. Figure 5 summarizes temporal placement and offset magnitude at two supplemental points. The manuscript uses NCW-shallow for the shallow-intersection control and reserves capture-prone wording for conditions with explicit $\\kappa>d$.

## Rebuild

From the repository root, install the pinned Python dependencies in `requirements.txt`, then run the generators and audit gates in this order:

```powershell
python -m pip install -r new\requirements.txt
python new\make_figures.py
python new\make_supplemental_figure.py
python new\analyze_expanded.py
python new\analyze_ncw_adaptive.py
python new\make_ncw_adaptive_figure.py
python new\make_engineering_figure.py
Set-Location 实验\qcmdpc-study
python tests\test_core.py
python exact_recovery_audit.py --full --group G0 --out results/exact_recovery_audit_20260923/formal_current
python exact_recovery_audit.py --full --group G2_d12 --out results/exact_recovery_audit_20260923/parallel_G2
python exact_recovery_audit.py --full --group G3 --out results/exact_recovery_audit_20260923/parallel_G3
python merge_exact_recovery_audit.py --formal results/exact_recovery_audit_20260923/formal_current --source results/exact_recovery_audit_20260923
Set-Location ..\..
Set-Location new
pandoc manuscript.md --standalone --resource-path=. -o manuscript.docx
pandoc manuscript.md --standalone --resource-path=. -o manuscript.tex
pandoc manuscript.md --standalone --resource-path=. -o manuscript.html
python repair_docx.py
pandoc manuscript_zh.md --standalone --resource-path=. -o manuscript_zh.docx
pandoc manuscript_zh.md --standalone --resource-path=. -o manuscript_zh.html
pandoc manuscript_zh.md --standalone --resource-path=. -o manuscript_zh.tex
python repair_docx_zh.py manuscript_zh.docx manuscript_zh_final.docx
Set-Location ..
python new\build_repro_manifest.py
python new\verify_package.py --source-only
```

`verify_package.py --source-only` checks source, figures, Word exports, exact-recovery evidence, and provenance without requiring a PDF. After exporting fresh bilingual PDFs, run `python new\verify_package.py` in strict mode; it requires the PDFs and DOCX exports to contain the current source marker. The current v4 PDFs are fresh Edge HTML print exports and pass the strict package gate, but they do not establish that the two-column journal TeX compiles. Use a real LaTeX engine or LibreOffice/Word PDF export for the submission build; HTML rendering alone is not a substitute for validating the journal entrypoint. The journal TeX entrypoints include a guarded full-width `table*` wrapper for Pandoc's generated `longtable` blocks; compile them with the target journal class and inspect float placement before submission.

The corrected taxonomy is implemented in `实验/qcmdpc-study/qcmdpc/taxonomy.py` and covered by the M0 test suite. Do not overwrite `results/m5_mechanism/` with a new classification silently. Run `formal_m5_mechanism.py --out results/m5_mechanism_preregistered` and then deliberately regenerate Figure 3 and its source tables after reviewing the new counts. The exact-recovery audit and the mechanism rerun are separate gates: passing one does not imply that the other is complete.
