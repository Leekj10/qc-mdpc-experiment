# Stagnation-triggered local recovery (STLR) prototype

The corrected v2 experiment is a minimal, testable generic trigger--recovery prototype. It is not a near-codeword-aware decoder, not a production BIKE implementation, and not a reproduction of any particular 2026 decoder. The earlier `ncw_adaptive_data/` run is retained as an archived v1 audit record.

The decoder first runs FRO-2. After a no-flip or non-decreasing-syndrome round, it triggers at most one recovery event, recomputes UPC on the post-round syndrome, probes the four highest positions from that new vector, and accepts only a strict syndrome-weight decrease. The extra UPC call and all four probes are counted. It does not detect, score, or use near-codeword structure. The decoder never reads the true error support; that support is used only for paired-instance generation and offline success labeling. The trigger, beam width, and recovery budget were frozen before execution.

Two calibrated points were tested: P2=`(3001,37,66)` and P3=`(4001,41,82)`. RAND, TYPE-I (`delta=12`), and NCW-shallow (`kappa=12`) conditions used 30 fresh keys and 500 errors per key. C0, FRO-2, and STLR yielded 18 cells and 90,000 paired decodes under master seed `20260913`.

| Point | Condition | C0 | FRO-2 | STLR | STLR/C0 RR [95% CI] | STLR/FRO-2 RR [95% CI] |
|---|---|---:|---:|---:|---:|---:|
| P2 | RAND | 30/15,000 | 9/15,000 | 5/15,000 | 6.00 [2.63, 29.00] | 1.80 [1.00, 5.00] |
| P2 | TYPE-I | 35/15,000 | 13/15,000 | 11/15,000 | 3.18 [1.94, 6.33] | 1.18 [1.00, 1.57] |
| P2 | NCW-shallow | 17/15,000 | 5/15,000 | 5/15,000 | 3.40 [1.50, 10.50] | 1.00 [0.50, 2.00] |
| P3 | RAND | 21/15,000 | 5/15,000 | 3/15,000 | 7.00 [2.33, 27.00] | 1.67 [1.00, 5.00] |
| P3 | TYPE-I | 26/15,000 | 5/15,000 | 4/15,000 | 6.50 [2.80, 28.00] | 1.25 [1.00, 2.50] |
| P3 | NCW-shallow | 15/15,000 | 5/15,000 | 4/15,000 | 3.75 [1.00, 11.00] | 1.25 [1.00, 2.50] |

STLR never exceeded C0's observed DFR, and its point-estimate reduction relative to C0 was 3.18--7.00x. Relative to the stronger FRO-2 baseline, point estimates range from 1.00 to 1.80 and all intervals include no resolved separation. These corrected counts support feasibility of a bounded generic recovery heuristic, not near-codeword awareness or superiority over FRO-2, BF-Max, BGF, or Backflip.

The prototype is data-dependent and should not be called constant-time. STLR used 9--67 recovery triggers per cell, with 0.0024--0.0179 probes per decode and a correspondingly small UPC-call overhead. P2/P3 are measurable stress points rather than BIKE production parameters, and NCW-shallow is a structural proxy rather than an exact gathering-key construction. A fair modern-decoder comparison requires matched semantics, budgets, and paired error pools.

Code and raw data: `ncw_adaptive_experiment.py`, `ncw_adaptive_data_v2/preregistration.json`, `ncw_adaptive_data_v2/P*_stlr_v2__*.json`, `ncw_adaptive_data_v2/stlr_analysis.json`, and `ncw_adaptive_data_v2/stlr_summary.csv`. The archived v1 files remain under `ncw_adaptive_data/` for audit comparison.
