# T_cluster: cluster-robust cross-key inference (C0 vs FRO-2)

Cluster bootstrap over keys (B=10000, seed=20260905); RR=DFR_C0/DFR_FRO-2 (>1 favours FRO-2).
Cross-key significance: 95% CI excludes RR=1. Holm across the 3 condition groups.

## Full formal (278-key)

| Condition | keys | RR | RR 95% CI | excl. RR=1 | DFR diff | diff 95% CI | sign i/w/t | sign p | sign p (Holm) | McNemar p | McNemar p (Holm) |
|---|---:|---:|---|:--:|---:|---|---|---:|---:|---:|---:|
| RAND | 92 | 4.15x | [3.29, 5.38] | yes | 7.754e-04 | [6.486e-04, 8.986e-04] | 79/6/7 | 2.44e-17 | 4.88e-17 | 2.84e-34 | 5.67e-34 |
| WEAK-12 | 94 | 5.47x | [4.25, 7.28] | yes | 1.078e-03 | [9.539e-04, 1.202e-03] | 88/3/3 | 1.02e-22 | 3.05e-22 | 8.84e-56 | 2.65e-55 |
| NCW-$\cap$ | 92 | 4.55x | [3.21, 6.82] | yes | 3.986e-04 | [3.080e-04, 4.891e-04] | 66/9/17 | 7.66e-12 | 7.66e-12 | 2.00e-18 | 2.00e-18 |

## Pure-fresh (212-key)

| Condition | keys | RR | RR 95% CI | excl. RR=1 | DFR diff | diff 95% CI | sign i/w/t | sign p | sign p (Holm) | McNemar p | McNemar p (Holm) |
|---|---:|---:|---|:--:|---:|---|---|---:|---:|---:|---:|
| RAND | 68 | 4.69x | [3.58, 6.34] | yes | 8.137e-04 | [6.763e-04, 9.559e-04] | 59/3/6 | 1.72e-14 | 3.45e-14 | n/a | n/a |
| WEAK-12 | 76 | 5.52x | [4.24, 7.52] | yes | 1.110e-03 | [9.605e-04, 1.254e-03] | 71/2/3 | 5.72e-19 | 1.72e-18 | n/a | n/a |
| NCW-$\cap$ | 68 | 3.69x | [2.53, 5.78] | yes | 3.431e-04 | [2.451e-04, 4.412e-04] | 47/7/14 | 2.29e-08 | 2.29e-08 | n/a | n/a |
