# FROZEN REFERENCE SEMANTICS (extracted from vvasseur/qcmdpc_decoder master, 2026-09-01)

Purpose: the authoritative semantics against which the Python reference and any
future C build must be cross-checked (M0 gate). Do not edit silently; any
change requires a new dated version of this file.

## 1. Verified CMake switches (CMakeLists.txt)
- Options exist: PRESET_CCA, PRESET_CPA, INDEX, BLOCK_LENGTH, BLOCK_WEIGHT,
  ERROR_WEIGHT, OUROBOROS, WEAK, WEAK_P, ERROR_FLOOR, ERROR_FLOOR_P, ALGO,
  TTL_C0, TTL_C1, TTL_SATURATE, THRESHOLD_A0..A4, BP_SCALE, BP_SATURATE,
  THRESHOLD_C0, THRESHOLD_C1, GRAY_SIZE; cmake option AVX defaults ON.
- NOTE: `-DPRESET_CCA=128` and `-DAVX=ON` used in the plan's command templates
  are therefore syntactically valid; AVX applies to x86 toolchains only.
- Historical plan note (superseded): the initial extraction was made before a
  compiler was available. The C baseline was subsequently built with `zig cc`
  using the shims and command recorded in `BUILD_WINDOWS.md`; the cross-
  validation results are frozen in Section 6 (2026-09-03).

## 2. Counter (UPC) definition (decoder.c get_counter)
counter(position p, block k) = sum over support positions a_l of h_k of
    syndrome[(p + a_l) mod r]
-> IDENTICAL to Python qcmdpc.ring.QCKey.upc (verified by unit tests against
   direct definition; cross-checked symbolically against C source).

## 3. Threshold semantics
### CLASSIC (compute_threshold, threshold.c)
- threshold = ceil( (w*(lqbar-lpbar) + ln t - ln(n-t)) / (lp-lq+lqbar-lpbar) )
  with p,q derived from binomial counters (X_val model);
- clipped to [ (BLOCK_WEIGHT+1)/2 , BLOCK_WEIGHT ].
### GRAY_BGF affine (compute_threshold_affine)
- thr = (unsigned)(THRESHOLD_C0 + THRESHOLD_C1 * S)   # TRUNCATION, NOT ceil
- lower bound only: thr = max(thr, (BLOCK_WEIGHT+1)/2); no upper clip.
- Default BGF constants used across literature: C0=13.53, C1=0.0069722.

ACTION: Python affine threshold semantics updated to floor+lower-bound for
`affine_vasseur` type (legacy `affine` type keeps pre-registered ceil+clip for
our own DRIS/CPS schedules; the two types must never be mixed).

## 4. GRAY_BGF iteration structure (decoder.c)
Per outer loop iteration:
1. counters recomputed; threshold = affine(|s|);
2. positions with counter >= threshold flipped immediately (black list);
   positions with counter >= threshold - GRAY_DELTA collected (gray list);
3. if iter < 2 (i.e., first black step only): re-check black positions,
   flip back those whose new counter >= (BLOCK_WEIGHT+1)/2 + 1;
4. gray step (BGF variant): re-check gray positions, flip those whose
   counter >= (BLOCK_WEIGHT+1)/2 + 1;
5. loop exits on zero syndrome, max_iter, or "blocked" (no flips performed);
6. success criterion: decoded word weight == 0 (decoder tracks distance to
   the true error e via e->weight).

## 4b. Defaults extracted from param.h (2026-09-01)
- GRAY_DELTA = 3 (NOT 1); SYNDROME_STOP = 0 (non-ouroboros); ALGO default GRAY_BGF.
- Affine constants by (BLOCK_WEIGHT, ERROR_WEIGHT):
  (71,134): C0=13.53,  C1=0.0069722;  (103,199): C0=15.2588, C1=0.005265;
  (137,264): C0=17.8785, C1=0.00402312.
- PRESET_CCA: L1 (12323, 71, 134); L3 (24659, 103, 199); L5 (40973, 137, 264).
  -> NOTE: L3 d=103 per param.h (some plan documents wrote 101; param.h governs).
- PRESET_CPA (no CCA security margin): L128 (10163, 71, 134); L192 (19853,103,199);
  L256 (32749,137,264). CPA-128 usable as a scaled near-L1 parameter set.
- TTL defaults (Backflip): C0=1.1, C1=0.45, TTL_SATURATE=5.

## 4c. Exact Python port
qcmdpc.decoders.bgf_vasseur implements section 4 + 4b exactly (GRAY_DELTA=3,
affine_vasseur threshold, blocked flag, substep iteration counting). bgf_lite
remains for backwards comparison only and is deprecated for headline numbers.

## 5. Status of the Python BGF implementation
qcmdpc.decoders.bgf_vasseur is the exact port of GRAY_BGF per sections 4/4b
(syndrome-level semantics; success here = zero syndrome, whereas C tracks
distance to e; equivalence on (H,e,s) triples holds for correctable errors).
**STATISTICALLY VALIDATED 2026-09-03** (section 6 below).
qcmdpc.decoders.bgf_lite is a preliminary two-state approximation, deprecated.

## 6. C cross-validation results (2026-09-03, zig cc build)
Build: see BUILD_WINDOWS.md. Two minimal shims, zero algorithmic changes
(cli.c signal() for sigaction/SIGHUP; win_compat.h aligned_alloc->malloc,
safe because AVX is disabled so alignment is a pure perf hint).

### 6.1 GRAY_BGF at P1 (4801, 45, 84), C0=13.53, C1=0.0069722
- C binary: 1596/20000 = 7.98e-2 (-T4 -N20000 -i20)
- Python bgf_vasseur (prescreen G0): 179/2400 = 7.46e-2, 95% CI [6.5, 8.5]e-2
- two-proportion z ~= 0.89 -> CONSISTENT. Port validated in the measurable regime.

### 6.2 CLASSIC at P1' (4801, 45, 92): semantic difference identified
- C binary: 136/200000 = 6.80e-4
- Python study carrier (bf_parallel + static-t classic, zero-syndrome success):
  71/72000 = 9.86e-4 (extended gate G0)
- ROOT CAUSE (read from decoder.c): C CLASSIC computes
  compute_threshold(syndrome_weight, dec->e->weight) where e->weight is the
  CURRENT distance to the true error - simulation-privileged dynamic info;
  success = exact recovery (!e->weight); plus blocked-exit. Our carrier uses
  static t and zero-syndrome success (no privileged info) - a strictly weaker,
  deployment-realistic decoder. Faithful parity port added:
  qcmdpc.decoders.bf_classic_dynamic (crossval run in results/crossval/).
- IMPLICATION FOR THE PAPER: headline carriers (C0_base/C4) are the static-t
  no-privileged-info semantics (frozen protocol, internally consistent for both
  arms); the C reference confirms ring/UPC/threshold mechanics; the dynamic-t
  variant is documented as the reference-implementation semantic and its DFR
  (6.8e-4) is the correct comparison point for bf_classic_dynamic only.

### 6.3 Success-criterion note
C uses exact error recovery everywhere; Python carriers use zero syndrome.
Agreement at P1 (6.1) indicates the zero-syndrome-but-wrong-word gap is
negligible at these parameters; at L1 the C run (10^7 samples) provides the
exact-recovery ground truth for the paper's methodology appendix.
**RESULT (2026-09-03 15:55)**: 10^7 GRAY_BGF decodes at L1 (official affine
constants, -T3 -i20): ZERO failures; iteration distribution 4 (70.8%) / 5
(29.2%) => rule-of-three bound DFR < 3e-7 (95%). Independent confirmation of
the 10^-7 regime for L1 BGF-class decoding.

## 7. Research patch: FIRST_ROUND_OFFSET (pre-registration v2, 2026-09-03)
decoder.c CLASSIC branch only: when compiled with -DFIRST_ROUND_OFFSET=n,
the threshold of iteration 1 (dec->iter == 1) is increased by n, clipped to
BLOCK_WEIGHT. Used exclusively for the L1 transfer study of the C4 schedule
(configs/pre_register_v2_l1_transfer.md). Upstream semantics otherwise
untouched; binaries named qcmdpc_l1_o{0,2,4}_{RAND,WEAK12,NCW16}.exe.

## 8. Local source snapshot and build hashes

The bundled source tree is a vendored snapshot rather than a Git checkout.
For the current package, the principal patched/reference files hash to:

- `src/decoder.c`: `b55794b35459398380fbe2e7fb31503aa9f9f35449261be3afef76fcc7b1d5e3`
- `src/cli.c`: `2aadff3c3a11511c6292941bb08fb947feda47d3c62675062e7d43e52e99938a7a`
- `include/win_compat.h`: `9158fff5c3a11511c6292941bb08fb6f578809df5428b92d6c543351d1af0fe0`

The complete source and build notes are included in the top-level provenance
manifest. The package does not claim an upstream commit hash for this detached
snapshot; source hashes and `BUILD_WINDOWS.md` are the identity record.
