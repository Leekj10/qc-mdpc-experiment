# Fair Modern-Decoder Comparison Protocol

This protocol records the comparison layers used in the revised manuscript.

| Layer | Decoders | Parameters | Semantics | Pairing | Interpretation |
|---|---|---|---|---|---|
| Matched static comparison | C0, FRO-2, specification-formula BIKE-Flip | P1'=(4801,45,92) | Static target weight, zero-syndrome success, common 20-iteration budget (BIKE-Flip's published setting is 7) | Identical (H,e,s), full formal key pool | Algorithm-level comparison; BIKE-Flip coefficients at P1' are derived by the specification's A.2.4 rule (validated against the official Level-1/3/5 constants), not published values |
| Native production reference | C0, FRO-2, spec-exact BIKE-Flip | Level 1=(12323,71,134) | Native official BIKE-Flip constants; carrier arms use the study static rule | Identical paired instances | Production-boundary and convergence check; DFR is unresolved at zero failures |
| Semantic reference | C0, FRO-2, Backflip | P1' | C-reference semantics: CLASSIC arms use the dynamic-distance rule (simulation-privileged); Backflip uses its own state-based threshold | Same generated instances within the reference run | Not deployable-equivalent for the CLASSIC arms (threshold consults true-error distance); Backflip's differences are the exact-recovery success criterion and Level-1 TTL constants (corrected 2026-10-10 after reading decoder.c:186-190) |
| Engineering reference | C0, FRO-2, STLR, SR-NCW, BGF-C3 | P2/P3 | Static CLASSIC threshold, common 20-round budget | Identical paired instances per cell | Cost/DFR reference; BGF-C3 is not official tuned BGF |

All pairwise comparisons use the same failure criterion within a layer. Key-cluster bootstrap, not error-instance resampling, is used for uncertainty. The copied BIKE-Flip reports are `modern_comparison_data/bikeflip_p1_formal_report.json` and `modern_comparison_data/bikeflip_l1_report.json`; the engineering pairwise intervals are in `engineering_data_v2/engineering_pairwise_rr.csv`.
