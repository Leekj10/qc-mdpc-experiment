# Figure Captions, Accessibility, and Provenance

## Figure 1: Study architecture

**Core finding:** The experiment preserves pairing from seeded key/error generation through decoder comparison and uses keys as clusters for inference.

**Alt text:** A four-stage horizontal flow diagram shows frozen seeded keys and errors, paired C0 and FRO-2 decoder arms, linked failure outcomes, and key-cluster bootstrap plus held-out confirmation.

## Figure 2: Main results

**Core finding:** FRO-2 lowers conditional DFR in all three formal conditions, and all key-cluster risk-ratio intervals exclude 1.

**Alt text:** Three panels compare C0 and FRO-2. The first shows lower log-scale DFR values for FRO-2 in random, Type-I, and shallow near-codeword conditions. The second shows risk ratios from about 4.1 to 5.5 with 95% intervals above 1. The third shows per-key failure fractions, with lower medians under FRO-2.

**Integrity note:** A 0.5/3,000 correction is used only to place zero-count keys on the log-scale display. It is not used for estimates or tests.

## Figure 3: Mechanism

**Core finding:** FRO-2 makes approximately nine times fewer incorrect first-round flips while leaving a larger immediate residual, then recovers in later rounds.

**Alt text:** Paired markers show that total and incorrect first-round flips fall sharply under FRO-2, while residual errors after round one increase. Stacked bars show stagnation remains the largest failure category, although absolute failure counts decline across all modes.

**Integrity note:** True error support is simulation-privileged and is used only for diagnostic logging.

## Figure 4: Scope, transfer, and boundary

**Core finding:** The frozen offset transfers to a second point and remains effective under tested budgets, but provides no protection once near-codeword intersection exceeds the block weight and capture dominates.

**Alt text:** A forest plot shows transfer risk ratios above 1. A log-scale line plot shows both schedules rising from low DFR to roughly 85% at kappa 46 and 100% at kappa 60. A budget plot shows risk ratios above 1 for random and Type-I conditions at budgets 7, 10, and 20.

**Missing-data note:** The archived iteration-budget experiment contains RAND and TYPE-I only; no NCW curve is drawn.

## Figure 5: Temporal placement and offset magnitude

**Core finding:** The expanded fresh-key matrix separates first-round placement from a uniform threshold shift: FRO-2 remains beneficial across the tested P2/P3 cells, whereas Uniform +2 is strongly adverse and Round-2 +2 is not consistently beneficial.

**Alt text:** Two panels compare five threshold schedules at two calibrated points. The log-scale DFR panel shows first-round +2 below the control in each condition, uniform +2 much higher, and round-2 +2 without a stable improvement. The second panel shows the mean iteration cost pooled over the three conditions at each point.

**Integrity note:** Each point uses 50 fresh keys and 1,000 paired errors per key. Zero-count cells are plotted at the displayed resolution only; the archived JSON contains the raw counts and one-sided bounds.

## Figure 6: STLR local-recovery prototype

**Core finding:** The corrected STLR v2 prototype is an exploratory generic heuristic. It recomputes UPC after the normal round, counts that pass and all probes, and does not inspect near-codeword structure. It does not establish an advantage over FRO-2.

**Alt text:** Six grouped cells compare C0, FRO-2, and STLR at P2 and P3 under RAND, Type-I, and shallow-intersection conditions. STLR has low observed failure counts and a small additional probe cost; the companion panel shows its mean iteration cost.

**Integrity note:** The plotted data come from `ncw_adaptive_data_v2/stlr_analysis.json` (seed 20260913). The earlier `ncw_adaptive_data` run is retained as a separate v1 audit record.

## Figure 7: Engineering comparison

**Core finding:** FRO-2 preserves the low state and UPC cost of the CLASSIC carrier, while STLR, SR-NCW, and BGF-C3 add recovery or substep work without a resolved additional DFR benefit in the six reported cells.

**Alt text:** Paired bar panels compare C0, FRO-2, STLR, SR-NCW, and BGF-C3 across P2/P3 and three error conditions. The left panel reports observed DFR in units of 10^-3; the right panel reports mean iteration count. All reported cells have nonzero failures.

**Integrity note:** Engineering values are generated from `engineering_data_v2/engineering_analysis.json`; recovery UPC recomputation is included in the reported cost. These are matched static-semantic comparisons, not a ranking of official production parameters.

## Export

Figures are provided as PDF and SVG vector files and 600-dpi PNG fallbacks. `publication_figure_manifest.json` records source roots, uncertainty, zero handling, palette, and output formats. Final publisher compliance must be checked after selecting the exact journal and submission phase.
