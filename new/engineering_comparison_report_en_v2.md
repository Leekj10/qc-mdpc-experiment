# Corrected Engineering Comparison Report

The corrected protocol recomputes UPC after a stagnation trigger and includes this extra pass in the cost counters. Strictly better-than-canonical near-codeword support is used only for G3; RAND and TYPE-I no longer receive a fabricated NCW candidate. BGF-C3 is a black/gray baseline with the same static CLASSIC threshold and a frozen gray delta of 3.

| Point | Condition | C0 | FRO-2 | STLR | SR-NCW | BGF-C3 |
|---|---|---:|---:|---:|---:|---:|
| P2 | RAND | 35/15000 | 14/15000 | 12/15000 | 12/15000 | 34/15000 |
| P2 | TYPE-I | 36/15000 | 24/15000 | 23/15000 | 23/15000 | 64/15000 |
| P2 | NCW-shallow | 19/15000 | 9/15000 | 8/15000 | 8/15000 | 13/15000 |
| P3 | RAND | 19/15000 | 13/15000 | 11/15000 | 11/15000 | 22/15000 |
| P3 | TYPE-I | 25/15000 | 9/15000 | 9/15000 | 9/15000 | 24/15000 |
| P3 | NCW-shallow | 7/15000 | 1/15000 | 1/15000 | 1/15000 | 4/15000 |

STLR and SR-NCW remain nearly identical after correction; restricting candidates to a near-codeword support does not produce a stable additional gain. BGF-C3 uses 5.07--5.62 UPC calls per decoding, compared with 4.1--5.0 for C0/FRO-2, and records more failures than C0 at P2 TYPE-I. This is an engineering cost/DFR reference under matched static semantics, not a ranking of official BGF parameters or production implementations.

The preregistered BIKE Level-1 holdout uses `(12323,71,134)` and one million trials per cell. Offsets 0, +2, and +4 record zero failures for RAND, TYPE-I, and NCW, giving only the per-cell rule-of-three bound DFR `<3e-6`; larger offsets slow two-round convergence. The holdout resolves no degradation but does not establish a production DFR improvement.
