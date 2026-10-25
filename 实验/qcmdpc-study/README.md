# qcmdpc-study

Key-dependent decoding-failure heterogeneity in QC-MDPC bit-flipping decoders:
measurement and constrained pseudorandom scheduling.

Python reference implementation + experiment pipeline for the pre-registered
plan (see `configs/pre_register.json` and `reference/FROZEN_REFERENCE_SEMANTICS.md`).

## Layout
```
qcmdpc/         core library
  ring.py         F2[x]/(x^r-1) ring ops: syndrome, flip, UPC (NUPC)
  generators.py   key pools (random / Type-I / near-codeword) + error pools,
                  SHA-256 seed derivation, structural self-validation
  decoders.py     unified decoders: bf_parallel, bgf_lite (preliminary),
                  bf_max; threshold specs: fixed / affine / affine_vasseur
  taxonomy.py     failure-mode classifier (pre-registered priority)
  stats.py        per-key DFR, Wilson one-sided 95% upper bound, rule of three
runner.py       fixed-key x error-pool matrix runner -> JSONL + summaries
analyze_pilot.py  per-key DFR CDF figure + analysis report
tests/test_core.py  M0 self-tests (must pass before any statistics)
configs/          frozen pre-registration + run configs
reference/        frozen semantics extracted from vvasseur/qcmdpc_decoder
results/          per-run outputs (manifest.json, summaries, samples, figures)
```

## Quick start (Windows PowerShell)
```powershell
Set-Location .\实验\qcmdpc-study
python tests\test_core.py                                  # M0 gate
python runner.py --config configs\pilot_p0.json --out results\pilot_p0
python analyze_pilot.py --run results\pilot_p0 --config configs\pilot_p0.json
```

The formal exact-recovery audit uses the same fresh-key pools as the P1'
decision run and records zero-syndrome misc corrections separately:

```powershell
python exact_recovery_audit.py --full --out results\exact_recovery_audit_20260923\formal_full
```

The corrected generic local-recovery prototype is maintained in the package
root and reads `new\ncw_adaptive_data_v2` by default:

```powershell
Set-Location ..\..
python new\analyze_ncw_adaptive.py
```

## C reference baseline
The reference source is bundled at `..\qcmdpc_decoder_ref\qcmdpc_decoder-master`. The frozen semantics note and `results/crossval/` contain the completed 2026-09-03 Python/C cross-validation. The commands below are for rebuilding the reference binary on a new machine; they are not a statement that the cross-validation is still pending.
After installing cmake + a C compiler:
```powershell
Set-Location ..\qcmdpc_decoder_ref\qcmdpc_decoder-master
cmake -S . -B build\bgf-p1 -DINDEX=2 -DBLOCK_LENGTH=4801 -DBLOCK_WEIGHT=45 -DERROR_WEIGHT=84 -DWEAK=0 -DERROR_FLOOR=0 -DTHRESHOLD_C0=13.53 -DTHRESHOLD_C1=0.0069722 -DALGO=GRAY_BGF
cmake --build build\bgf-p1 --config Release
```
The headline BGF results use the exact `bgf_vasseur` port and the completed
cross-validation. `bgf_lite` remains a deprecated historical approximation and
must not be used for new headline statistics.

## Rules (pre-registered, do not violate)
- zero failures -> report Wilson/3-N upper bound, never "DFR = 0";
- whole-key 60/20/20 holdout; search only on train keys;
- all decoders run on identical (H, e, s) pairs;
- no post-hoc parameters/metrics/decoders after results exist.
