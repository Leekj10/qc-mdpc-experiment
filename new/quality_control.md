# Manuscript Quality-Control Report

## Scope

This report evaluates `manuscript.md` as an original manuscript assembled from archived experiment outputs. It does not certify journal acceptance or cryptographic security.

## Chapter-level gate

| Section | Argument | Evidence/citations | Clarity | Structure | Style | Score /20 | Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Introduction | 4 | 4 | 4 | 4 | 4 | 20 | Pass |
| Background | 4 | 4 | 4 | 4 | 4 | 20 | Pass |
| Methods | 4 | 4 | 4 | 4 | 4 | 20 | Pass |
| Results | 4 | 4 | 4 | 4 | 4 | 20 | Pass |
| Discussion | 4 | 4 | 4 | 4 | 4 | 20 | Pass |
| Conclusion | 4 | 3 | 4 | 4 | 4 | 19 | Pass |

Ratings are internal editorial checks, not independent peer review.

## Final seven-dimension evaluation

| Dimension | Score /10 | Basis |
|---|:---:|---|
| Argument quality | 9 | Claim, mechanism, negative control, and boundary are integrated |
| Literature integration | 8 | Core QC-MDPC, weak-key, DFR, and modern-decoder references included |
| Clarity and accessibility | 9 | Terminology and inferential units are defined; overclaims are explicitly bounded |
| Originality and contribution | 7 | Experimental design and mechanism evidence are strong; intervention is incremental |
| Methodological rigor | 9 | Paired design, whole-key splits, cluster inference, fresh subset, and sensitivity tests |
| Structure and organization | 9 | Measurement-intervention-boundary narrative; results follow methods promises |
| Style and format | 8 | Submission-neutral scientific style; exact journal formatting remains pending |
| **Total** | **59/70** | Passes the composer's 56/70 internal gate |

## Consistency checks

- Main formal counts, DFRs, risk ratios, and confidence intervals match archived JSON.
- Pure-fresh sample size is 212 keys and 636,000 samples per arm.
- Zero-failure experiments are presented as upper bounds, not zero risk.
- TYPE-I is identified as an adversarial probe.
- The shallow NCW group is not described as genuine capture or gathering.
- Genuine capture is separated into a fixed-key-batch supplemental experiment.
- BIKE-Flip at the scaled point is labeled out-of-tuning; no dominance claim is made.
- BF-Max is labeled as an exploratory native-Level-1 probe; BGF is excluded from formal ranking because the archived settings are not comparable.
- Backflip is acknowledged as stronger in the measured dynamic-semantics comparison.
- Python/C agreement is labeled cross-implementation validation, not independent-laboratory replication.
- The original heterogeneity threshold that was not met is reported.
- Supplemental post-registration analyses are not presented as confirmatory core tests.

## Remaining author actions

- Confirm authorship, affiliations, CRediT roles, conflicts, and the missing CPU/RAM record.
- Verify the final archive snapshot and all reference metadata immediately before submission.
- Select a target journal and perform a journal-specific format and figure compliance pass.
