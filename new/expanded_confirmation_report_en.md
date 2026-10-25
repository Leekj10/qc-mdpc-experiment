# Expanded confirmation experiment

The confirmation run used a fresh master seed (`20260912`), 50 new keys per condition, and 1,000 paired errors per key at the two calibrated points P2=`(3001,37,66)` and P3=`(4001,41,82)`. RAND, TYPE-I (`delta=12`), and NCW-shallow (`kappa=12`) conditions were evaluated with C0, FRO-1, FRO-2, FRO-3, round-2-only +2, and uniform +2 schedules. Every schedule received identical `(H,e,s)` instances within a cell; keys were the bootstrap cluster unit.

The run contains 36 decoder-arm cells and 300 fresh keys. The six schedules share 300,000 unique paired `(H,e,s)` inputs, yielding 1,800,000 decoder-arm runs. FRO-2/C0 risk-ratio estimates were:

| Point | Condition | C0 failures | FRO-2 failures | Risk ratio [95% key-cluster bootstrap CI] |
|---|---|---:|---:|---:|
| P2 | RAND | 128/50,000 | 54/50,000 | 2.37 [1.86, 3.06] |
| P2 | TYPE-I | 157/50,000 | 55/50,000 | 2.85 [2.09, 4.07] |
| P2 | NCW-shallow | 60/50,000 | 20/50,000 | 3.00 [2.03, 5.00] |
| P3 | RAND | 55/50,000 | 21/50,000 | 2.62 [1.67, 4.29] |
| P3 | TYPE-I | 85/50,000 | 26/50,000 | 3.27 [2.15, 5.79] |
| P3 | NCW-shallow | 37/50,000 | 8/50,000 | 4.62 [2.36, 11.25] |

All six cellwise 95% intervals exclude one. They are marginal intervals and do not constitute an unadjusted simultaneous 95% coverage statement. Uniform +2 produced DFRs of 0.080–0.190 and was consistently harmful; round-2-only +2 showed no stable benefit. First-round offsets remained favorable, but the best magnitude varied by operating point and key condition. These results support a temporal threshold-shaping mechanism, not a claim that FRO-2 is a universal optimum or that BIKE production-parameter DFR has been established.

Raw cells are in `expanded_data/P*_expanded__*.json`; the preregistration is `expanded_data/preregistration.json`; aggregation is `expanded_data/expanded_analysis.json` and `expanded_data/expanded_summary.csv`.
