# Pre-registration amendment v1 (dated BEFORE the formal M5 run)

Date: 2026-09-03
Status: amendment to configs/pre_register.json (original frozen 2026-09-01)

## A1. Formal-decision sample size (throughput amendment)
Original: full M1 pool = 100 keys/group x 10^4 errors/key.
Amended : 100 keys/group x 3,000 errors/key (3x10^5 samples per group per decoder).
Reason  : Python reference implementation throughput (~17-20 ms/decode at P1');
          10^4/key would require ~33 CPU-hours x 3 groups, impractical before the
          C toolchain is available. Rule-of-three resolution at 3x10^5 is 1x10^-5,
          sufficient to separate the observed effect sizes (base ~1x10^-3,
          C4 ~1-3x10^-4). NOT outcome-driven: chosen before seeing any M5 data.
The 10^4/key version remains the target once the C baseline is built; results
are directly comparable (same frozen seeds/pools/generators, error_id prefix).

## A2. Per-sample paired outcome logging (addition)
The formal run records, for every (key_id, error_id), the outcome of BOTH
decoders, enabling:
- exact McNemar test on discordant pairs (primary paired significance);
- per-key dispersion analysis;
This adds evidence only; no decision rule changes.

## A3. Decision rules (unchanged from pre_register.json)
- H2 gate: worst-group log10 U0.95 improvement >= 0.5 AND G0 non-inferiority
  U(C4) <= 1.20 x U(C0);
- keys: fresh indices only (G0/G3 >= 8, G2 >= 6); search data never reused;
- zero failures -> rule-of-three upper bound.

## A4. Statistical correction record (transparency)
Session-8 informal claim "G3 significantly lower than G0 (z=-3.1)" is WITHDRAWN:
it used an unconditional approximation. The correct conditional Poisson test
gives z=-1.71 (not significant at 0.05). Verified numbers are in
results/gate_h2_extended/stats_verification.json.

## A5. New observation to be reported (not a rule change)
Under C4, group G2 shows over-dispersion (ratio 1.94, z=+2.74): residual
failures concentrate on few keys. This will be reported as an observation
("schedule improvement unmasks residual key-concentrated risk") and motivates
future work on combining schedules with key screening. No post-hoc analysis
of new schedules is performed under this protocol.
