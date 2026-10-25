# Pre-registration v2: C4 transfer validation at BIKE L1 (C-accelerated)

Date: 2026-09-03 (filed BEFORE any L1 offset run)
Scope: does the first-round conservative offset (selected at P1' as C4=+2)
transfer to BIKE Level-1 parameters? New parameter set => new pre-registration;
the P1' selection result is used ONLY as the primary hypothesis, not as evidence.

## Design
- Implementation: vvasseur/qcmdpc_decoder C reference, ALGO=CLASSIC, patched
  with a documented compile-time flag FIRST_ROUND_OFFSET (adds the integer
  offset to the threshold of iteration 1 only, clipped to BLOCK_WEIGHT).
  No other change. Patch recorded in FROZEN_REFERENCE_SEMANTICS.md §7.
- Parameters: L1 = (r=12323, d=71, t=134) per param.h PRESET_CCA.
- Semantics: C reference semantics throughout (dynamic distance threshold,
  exact-recovery success). Both arms share identical semantics => internally
  consistent; NOT directly comparable to the Python static-t carrier numbers.
- Arms (offsets): {0 (baseline), +2 (primary, transferred from P1'), +4
  (exploratory)}. Selection note: +2 is the pre-registered primary; if +2
  fails and +4 succeeds, that is reported as exploratory-only (no claim swap).
- Conditions (C-native generators, literature-validated):
  - RAND: WEAK=0, ERROR_FLOOR=0 (uniform keys/errors)
  - WEAK12: WEAK=1, WEAK_P=12 (Type-I run of 12 consecutive ones)
  - NCW16: ERROR_FLOOR=1, ERROR_FLOOR_P=16 (errors with 16 intersections
    with a (d,d) near-codeword)
- N = 10^6 instances per (offset, condition) cell; 9 cells total.
- Runs are UNPAIRED (independent C RNG instances); tests are two-proportion
  z / Wilson intervals, not McNemar.

## Decision criteria (fixed now)
- Transfer SUPPORTED if: worst-condition log10 U95 improvement of +2 vs 0
  >= 0.3 log10 AND RAND non-inferiority U(+2) <= 1.2 x U(0).
  (Threshold 0.3, weaker than the 0.5 discovery gate, because this is a
  TRANSFER confirmation, not a discovery; justified now, before data.)
- Otherwise: transfer NOT demonstrated at L1; paper reports P1' result only
  and L1 as open question.

## Reporting
- All 9 cells reported regardless of outcome (no selective reporting);
- iteration distributions and wall-time recorded per cell;
- output: results/l1_c4_transfer/log + summary table in EXECUTION_REPORT.

## Prohibited
- No post-hoc offset values beyond {0,+2,+4};
- No claiming L1 DFR below the rule-of-three resolution of 10^6 (3x10^-6);
- No mixing C-semantics numbers with Python-carrier numbers in one table
  without an explicit semantics column.
