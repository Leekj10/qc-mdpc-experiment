# v3 architecture — a from-scratch manuscript of the QC-MDPC first-round-threshold study

> 中文摘要：本文件是 v3 新稿的架构蓝图。框架取自 `文献阅读/` 8 篇范文的写法（逐条标注出处），
> 不参照 lw-vs 旧稿的任何文本。写作者只允许读：本文件、数据摘要 `data_digest.csv`、
> 指定 dossier、以及本文档内的 STYLE_RULES；**严禁阅读 lw-vs/{en,zh,optimized,10.12} 的任何
> 稿件文本**。数字只能引用数据摘要中出现的归档值。

Working title (writers may polish, keep "CLASSIC QC-MDPC bit-flipping" in it):
**"The first round is a two-sided, time-localized window: threshold timing and conditional
decoding failure in CLASSIC QC-MDPC bit-flipping."**

Thesis sentence (everything must serve it): *In the CLASSIC QC-MDPC bit-flipping decoder, the
first round is a sharp two-sided window whose timing structure (which round is touched, and
whether the offset is one-shot or sustained), not its magnitude, governs conditional failure
risk; we establish this with paired instances and inference clustered by key, explain it through
asymmetric false-flip suppression, and delimit it at the capture boundary and at the production
block parameters.*

Structural devices and their sources (all from `文献阅读/` dossiers, dz_0..dz_7):
- **Inverted-causality introduction** — Paiva & Terada, TCHES'22 (dz_3): open with the domain
  problem, then "while characterizing the decoder we noticed X; this study is organized around
  that pair of observations".
- **Benchmark paragraph** — Vasseur thesis 2021 (dz_7): one paragraph, early in the design
  section, that defines instances, arms, the failure metric, the interval method and the
  zero-failure rule, once.
- **Reading sentences** — Watanabe, TIT'24 (dz_2): every quoted number gets a clause saying
  which direction is good; equivalent-translation phrasing where possible.
- **Per-section roadmaps and forward pointers** — Annechini, TIT'26 (dz_5/6): 1-2 sentences at
  each major section opening saying what it establishes; short forward pointers at the end.
- **Negative results as full citizens** — Sendrier & Vasseur, PQCrypto'19 (dz_1) and Paiva
  (dz_3): report what failed with the mechanism of failure.
- **Explicit limitations section** — Vasseur (dz_7) / Arpin CRYPTO'25 (dz_4).
- **Related work inside Background, positioning in prose** — Paiva (dz_3): no bulleted
  claim-scope list; the boundaries are stated as prose in the positioning paragraph and in
  Limitations.

---

## Skeleton (8 sections; ≈ 15 pp two-column)

### 1. Introduction (≈1.2 pp; 5 paragraphs)
1. Domain and gap: BIKE / NIST PQC; DFR target ~2^{-128} at Level-1 is unmeasurable; failures
   are key-conditioned and security-relevant (reaction/timing/weak-key); the real question is
   whether a schedule perturbation changes risk *conditional on the key*.
2. The observation (Paiva style): while characterizing the CLASSIC decoder on failing
   instances we noticed its earliest decision is unexpectedly delicate — ±1 on the round-1
   threshold moves the failure rate severalfold in both directions; and a sustained offset
   leaving round 1 untouched is destructive while the same offset confined to one round helps.
3. What we did: paired (H,e,s) instances, inference clustered by key, risk ratio; define FRO-k /
   FRO-2 in one sentence; one sentence of scope honesty (calibrated rates; no production-tail
   extrapolation).
4. Contributions (4 numbered items, each with hard numbers; last item = the production
   boundary; the counterfactual negative named in a closing sentence).
5. Roadmap (one paragraph, section names only).

### 2. Background and the CLASSIC carrier (≈1.2 pp)
- **2.1 QC-MDPC bit-flipping and the CLASSIC carrier.** Para 1: parameters, syndrome, UPC,
  threshold rule. Para 2: the carrier's name story stated ONCE (no unified name in the BIKE
  literature; its named successors are BGF/Backflip/Black-Gray-Flip/BIKE-Flip; BF in BIKE docs
  = Backflip; our cross-check reference labels it CLASSIC; we write C0), plus the specification
  relationship: BIKE-Flip's threshold `max(f_t(S), T_i(S0))`, floors with margin Δ in EVERY
  iteration, Level-1 Δ=3 / seven iterations, A.2.4 derivation rule (verified against published
  constants), published rationale (failures at iterations 2–3, cited); **FRO-2 is not that
  scheme** (one-shot +2 on CLASSIC's first round).
- **2.2 Failure is conditional on keys and schedules.** Weak-key literature; the response is a
  paired, key-clustered design (one sentence, details in §4).
- **2.3 Related work and positioning.** Two modelling lines (round-state models: Kim & Park,
  Paiva & Terada, Santini, Annechini; failure-rate models: Sendrier–Vasseur, Tillich, Vasseur,
  Arpin, Annechini closed form with its proxy-extrapolation warning) + direct threshold
  optimization (Kichna PSO at the same (4801,45), iterations 5.36→3.01, per-instance); the
  counterfactual-use gap (nobody uses round-one statistics to *predict* another schedule;
  we try and it fails, §5.7). Prose positioning sentences (no bullet list): measured range
  1e-4–1e-3, no level extrapolation; comparators are references, not dominance; capture-prone
  is a stress label; round-one statistics are not a deployable signal.

### 3. A first-order model of the first-round window (≈0.5 pp)
Binomial UPC tails U_{i,j}; p1>p0; tail masses q1/q0; A1, A0 as the two multipliers under
τ1→τ1+2; A0≪A1 prediction + one-clause gloss; three consequences (i)(ii)(iii); the model is
silent on sign/later rounds — (ii)(iii) are experiments, not corollaries.

### 4. Study design (≈1.3 pp)
- **Benchmark paragraph** (Vasseur): instances are (key H, error e, syndrome s); one *arm* = one
  decoder configuration; every arm decodes the same instance; DFR = failed decodings over
  attempted, per arm per condition; uncertainty = 95% key-cluster bootstrap (keys resampled,
  not errors); risk ratio RR = C0 DFR / arm DFR, RR>1 favours the arm; zero-failure cells get
  the rule-of-three bound 3/N, never a zero-risk reading.
- **Operating points table (NEW, compact)**: rows P1' (4801,45,92), P2 (3001,37,66),
  P3 (4001,41,82), large code (6007,56,100), production blocks (12323,71) at t*=172,
  CPA-128 (10163,71) at t=140, native Level-1 (12323,71,134) — columns: point, role, scale.
  (Values from data_digest; the table is new to v3.)
- **Conditions** (one-line gloss each): RAND; TYPE-I (12-consecutive-ones run; adversarial
  probe, not a population estimate); NCW-shallow (κ=12 < d=45 overlap; capture excluded by
  construction with the distance sentence). Mention the separate κ>d stress family (§5.5).
- **Protocol and provenance** (plain narrative, NO tier framework): calibrate where failures
  are measurable → screen nine schedules under the worst-group bound → preregister the gate and
  the pure-fresh subset → measure; frozen seeds (master 20260901, bootstrap 20260905,
  exploratory 20260911, confirmation 20260912); every number reproducible from the archive;
  exploratory cells labelled as such; cross-implementation check (11/20,000 vs 136/200,000,
  z=−0.68; direction reproduced 1.59/2.01 under the dynamic semantics; same-project caveat);
  exact-recovery audit (795 / 167, zero miscorrection) + static-semantics sentence; note that
  exploratory cells and archived prototype runs never carry primary conclusions.

### 5. Results (≈5.2 pp; eight subsections — the evidence has eight axes; prose fresh)
- **5.1 The first round is a two-sided window.** Formal comparison (Table: 3 conditions,
  counts, DFRs, RRs, Holm p; Fig 2 panels a–c named) + round controls: r1+2 (4.15 [3.29,5.38],
  79/92) vs r1−1 (0.126 [0.111,0.142], 92/92 worse); gate sentence 0.687 / 0.679.
- **5.2 Timing, not magnitude: one-shot versus sustained.** R2one 1.21 [1.07,1.36] vs R2plus
  0.0168 [0.0149,0.0187]; spans 1.21–1.45 / 0.012–0.021; the other two conditions (0.109/0.101,
  0.0210/0.0118); expanded confirmation (Table, FRO-1/2/3 + uniform; bold reading; P2/RAND
  FRO-1 2.56 vs FRO-2 2.37 as the not-universal-optimum example); Fig 4.
- **5.3 Mechanism: asymmetric false-flip suppression.** 29/8 → 9/0.8; ratios 9.5× vs 2.7×
  with the reading; residual +6; rescued subset 16 vs 1.4–2.2; failure-mode 30 cells identical
  (by construction: budget always exhausted); diagnostic-status caveat; Fig 3.
- **5.4 Generality.** Transfer P2 (1.95/3.21/2.51; 0.384); sweep 7.00/2.82/1.87 + the
  full-scan disclosure (12 cells, 6 below / 6 above; resolved-contrast-above-1.01 wording);
  6007 (8.13e-3→3.38e-3, 2.41); budgets 7/10/20 (1.72–3.17); dynamic semantics (1.59/2.01,
  z=7.94/11.98, NCW 1.36 unresolved); low-rate endpoint (7.07e-5, 3.71 [2.69,5.57], 60/6/26,
  p=2.7e-12; interval-overlap reading); offset-rule sentence (oracle labels, archived);
  cross-pool 7.00 vs primary-interval note; Fig 5.
- **5.5 Boundary I: capture-prone overlap conditions.** κ definition; 85.31 vs 86.50, RR 0.986;
  κ=60 both fail; NCW-aware dissociation (inert at P1' — 282/372/141, iterations 4.312/4.511/
  4.206; 11.07% vs 85.31% at κ=46, step fired 74.2%; 0.76% at κ=60).
- **5.6 Boundary II: production block parameters.** Raised-weight window (t*=172, 28%;
  4.48 [2.97,7.25] vs 0.162 [0.119,0.209], 94/48,000); production weight itself (no failures,
  bound 9.4e-5; margin 101.2/87.5/13.8 → 2.3 / 25.5 / 31.2; exchange 0.450 vs 0.546;
  convergence 2.446/2.054/2.232; spec-margin ablations 0.09→37.35, 6.14; all zero-failure);
  production-comparator runs (BIKE-Flip 28/13, C0 94, FRO-2 21; McNemar 0.32/0.18; BGF 63
  p=0.013; official-BGF 94.6%; all within ~1 iteration; spec-config degradation 1.10e-2/1.84e-2
  = 6×/9× C0); CPA-128 proximity (t=140, 4.96/0.177, overlap readings, no CCA margin); C cost
  (7,134/6,563, 1.087, 4.191/4.471, P99 6/6, 7–9%; GRAY_BGF mismatch 13.2/47.9%). Table V +
  Fig 7. Nine-million Level-1 zero-failure hold-out (3e-6 bound, dynamic semantics caveat).
- **5.7 A negative result: round-one statistics do not predict other offsets.** Setup (computable
  without running the decoder); AUC 0.995; predicted 0.79/0.16/0.04 vs measured 3.46/3.86/3.97;
  conditioned fit 2.18/1.86/0.83; three further configs 0.21/0.27/0.33 vs 2.82/1.87/2.41;
  diagnosis (post-treatment conditioning); diagnostic-not-predictor.
- **5.8 Positioning against modern decoders.** Table IV (numeric-only; caption carries the
  reading); spec-formula BIKE-Flip 3.007/3.333/2.101 e-4, tie in RAND (p=0.228), pilot
  footnote; budget-favours-comparator disclosure; BGF-C3 0.983/0.951/1.679, +22% iterations;
  affine mismatch 38–60%; Backflip 0-failures <3e-6 stronger; positioning sentence.

### 6. Discussion (≈1 pp)
(a) What the evidence supports: the temporal decomposition implies a single well-placed early
decision changes the state entering later rounds; later rounds cannot absorb sustained
displacement; FRO-2 conservative in the strict sense (fewer flips, fewer wrong flips, more
residual) — caution against early-error-reduction as an objective.
(b) The specification objection: production BIKE-Flip sustains its margin; both statements are
about specific schedules; mid-flight displacement of a per-round-calibrated schedule is
destructive; the spec's shape differs (floor + max, calibration target = whole schedule).
(c) The randomization control (BF30: 4.29% → 19.67%, ±jitter; 50.5–51.8% positive-only;
CLASSIC probe unresolved, Fisher p≥0.54, footnote counts): unstructured mixing is not a
substitute for a positioned deterministic schedule.

### 7. Limitations (≈0.6 pp, explicit section)
Calibrated range only; two operating points + a supplemental third; researcher-defined search
space; same-project cross-check; diagnostic labels use the true error support; Poisson
consistency bound (variance-to-mean 0.98, CV ≤~30%; "key-conditional" = inference level);
production code ≠ operating point (raised weight; bisection samples ⊂ main instances);
production-weight signals = margin + convergence cost; capture not demonstrated; future work.

### 8. Conclusion (≈0.4 pp)
The four-part principle; the ≤2-sentence negative clause; the methods recommendation.

Back matter: Data and Code Availability (archive + mirror; artefact chain; note: keep as
planned — edit only at upload time); Author Contributions; Competing Interests (placeholders).

## Figures (reuse the 10.12 renders — they already follow the field conventions and the v3
contract; NEW captions in v3 voice, floats ordered by appearance = LaTeX renumbers):
fig1_study_design (§4), fig2_main_results (§5.1), fig4_temporal_dissociation (§5.2),
fig3_mechanism (§5.3), fig5_scope_and_boundary (§5.4/5.5), fig7_modern_decoders (§5.6/5.8).
Copy the PDFs into v3/figures; stems unchanged.

## STYLE_RULES (binding for every writer; distilled from the dossiers + nature-writing)
- Sentences 12–25 words, one proposition each; no em-dash punctuation; no unicode dashes.
- Every quoted number: one reading clause saying which direction is good; rotate patterns
  (equivalent translation / crossover / relative multiple / risk-ratio sentence).
- Define each term, symbol and label at first use in one intuitive clause.
- Results = observations; Discussion = interpretation. Hedging only at evidence boundaries;
  exact numbers carry no hedging.
- First person allowed ("we ran", "we were unable to"); facts in present tense.
- British spelling; keep capitalisation of arm names (C0, FRO-2, TYPE-I, NCW, BGF-C3, BIKE-Flip,
  Backflip, BF-Max); RAND/TYPE-I/NCW are condition names, not arms.
- Do not invent any number, seed, count, percentage or parameter. Quote only values present in
  `data_digest.csv`; every quoted number goes into the section's numbers-ledger with its
  digest row.
- Claim boundaries (never cross): no production-grade DFR improvement; no dominance over modern
  decoders; no error-floor/capture/gathering detection; no universally optimal offset; FRO-2 is
  never presented as the specification's own first-round protection.
- No references to any other version of this manuscript; write fresh sentences.

## Number rendering conventions
`2.464\times10^{-4}` style for rates; `834{,}000` for counts; `[lo, hi]` for intervals;
`%` escaped as `\%`; parameters as `$(r,d,t)=(4801,45,92)$`; `$P_1'$` with the prime.
