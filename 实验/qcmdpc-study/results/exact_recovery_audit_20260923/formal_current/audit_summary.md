# Exact-recovery audit summary

Protocol: `exact_recovery_audit_v1`; parameter: `P1prime`; success is reported separately as zero syndrome and exact error recovery.

| Group | Arm | Processed | Zero syndrome | Exact recovery | Exact failures | Zero-syndrome miscorrections |
|:--|:--|--:|--:|--:|--:|--:|
| G0 | C0_base | 276,000 | 275,718 | 275,718 | 282 | 0 |
| G0 | FRO-2 | 276,000 | 275,932 | 275,932 | 68 | 0 |
| G2_d12 | C0_base | 282,000 | 281,628 | 281,628 | 372 | 0 |
| G2_d12 | FRO-2 | 282,000 | 281,932 | 281,932 | 68 | 0 |
| G3 | C0_base | 276,000 | 275,859 | 275,859 | 141 | 0 |
| G3 | FRO-2 | 276,000 | 275,969 | 275,969 | 31 | 0 |

All group rows satisfy `processed = zero_syndrome + nonzero_syndrome` and `exact_recovery_failures = nonzero_syndrome + zero_syndrome_miscorrections`.
No zero-syndrome miscorrections were observed in the completed formal pool.
