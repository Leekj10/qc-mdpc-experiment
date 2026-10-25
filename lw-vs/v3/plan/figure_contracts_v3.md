# v3 figure contracts — top-journal redesign (2026-10-13, nature-figure pass)

Backend: **Python (matplotlib)** only (nature-figure backend gate; the project's
whole figure pipeline is Python).  Scripts: `lw-vs/v3/scripts/style_v3.py`,
`lw-vs/v3/scripts/figs/fig*.py`; palette gate `lw-vs/v3/scripts/check_palette_v3.py`.
Outputs: `lw-vs/v3/figures/<stem>.{pdf,svg,png}` (600-dpi png; same stems the
manuscript already includes, so no LaTeX path changes).

## Style system

- Sans-serif (Arial / Helvetica / DejaVu Sans), editable SVG text (`svg.fonttype
  none`), `pdf.fonttype 42`.
- Open axes (no top/right spines), no grid, frame-less legends, thin rules,
  direct labels preferred over legends, light direction washes for region
  cues (alpha ≈ 0.05).
- Colour semantics kept exactly as audited in 10.12 (colour = arm / direction
  only; conditions, operating points and failure modes stay neutral and are
  separated by marker / line style / hatch):

  | slot | hex | role |
  |---|---|---|
  | control | `#111111` | C0, every panel (deep black) |
  | hero | `#0072BD` | FRO-2, every panel (MATLAB blue, as Kichna et al. plot their best threshold) |
  | benign | `#77AC30` | other one-shot arms (R2one) (MATLAB green) |
  | accent | `#D95319` | destructive arms (FRONEG, R2plus, UNIFORM-2) (MATLAB orange, the hue the field exemplars put on their worst performer) |
  | grey | `#767676` | third-party decoders / mid neutral |
  | grey_light | `#A6A6A6` | third condition line (fig7b NCW) |
  | neutral_light | `#CFCECE` | lightest neutral (mode ramp, fills) |

- Palette gate `check_palette_v3.py`: **PASS, 21 pair checks** — every
  co-occurring pair ≥ 0.15 under simulated deuteranopia/protanopia, second
  channel declared per panel (shape or hatch).  Hues were re-sampled on
  2026-10-13 from the three field exemplars (Kichna et al. CommNet'24,
  BF-Max, Cai & Zhang) rendered under `plan/_ref_figs/`, all of which use the
  MATLAB-family defaults; the black baseline keeps the Cai & Zhang / BF-Max
  habit of plotting the reference series in black.  Roles and semantics are
  unchanged.

- **Magnified axes where differences are small** (user request 2026-10-13):
  * fig2(a) x-range tightened to 8.6e-5–2.35e-3 and fig2(b) to 0.78–8.2 so the
    paired differences fill the axis;
  * fig4(a–c) use a **broken log axis** (top 0.45–13 magnifies the one-shot
    cluster, bottom 0.0035–0.05 carries the two-order sustained collapse;
    diagonal break marks on the left spine);
  * fig7(a) y-range tightened to 6e-5–2.4e-3 and the legend moved above the
    axes so bar differences stay legible.

## 2026-10-17: complete-set replacement (AUTHORITATIVE)

The manuscript now ships the **`figure_research/complete_set/`** renderings of
all six figures (same stems; the figures were rebuilt from the archived CSVs
with a Tol High Contrast palette: deep blue `#004488`, gold `#DDAA33`, red
`#BB5566`; Times New Roman embedded; all pages vector-only; data integrity
checked across 35 CSVs). Layout consequences and synchronisation performed:

- All figures are designed at 181.86 mm full width. **fig3_mechanism and
  fig7_modern_decoders were converted from `\onefig` (single column) to
  `\dblfig`** — the old single-column float would have shrunk the composite
  art below legibility.
- Captions (EN + ZH) were rewritten to the new panel organisations, using the
  panel letters present in the art: fig1 (a/b/c), fig2 (a, b--d), fig3
  (upper/lower), fig4 (upper/lower), fig5 (upper, a, b), fig7 (upper/lower).
- In-text panel references were re-synchronised: §V-A "three ways" → "as
  key-cluster intervals and per-key distributions"; §V-C "Figure 4a/b" →
  "upper/lower panel"; §V-D "Figure 5a" → "upper panel"; §V-E/F "Figure 6b" →
  "lower panel".
- `supp_t_sensitivity` was NOT inserted: the manuscript has no supplementary
  figure slot (kept in `figure_research/` for the submission package).
- `check_palette_v3.py` is superseded for the shipped set (the figure_research
  package carries its own vector/data validation); the legacy style_v3 scripts
  and the per-figure contracts below are retained only as design records.

Verification: numeric gate 382 checks PASS; `[?]`/`??` = 0 in both PDFs;
Overfull \hbox/\vbox = 0; EN 13 pp / ZH 12 pp.

## Per-figure contracts (LEGACY design records — see 2026-10-17 section)

### fig1_study_design — schematic-led composite, 182 mm × 2.0 in
Core: every comparison is paired on identical (H,e,s); the intervention is a
one-shot round-1 raise; five run streams carry the numbers.
- (a) pairing flow (C0 / FRO-2 chips), per-key aggregation, resampling unit.
- (b) threshold schedule step plot, one-shot +2 in round 1, "identical thereafter".
- (c) **stage-line timeline** (replaces the 10.12 evidence-tier table, which the
  v3 manuscript no longer contains): screening (9 schedules) → frozen gate
  (212 keys × 3,000) → formal pool (278 keys × 3,000) → confirmation
  (50 × 1,000, P2 & P3) → held-out check (48 × 1,000, P4); labels alternate
  above/below one directed line.
- In-script QA: no text outside canvas, no overlaps, all labels inside their
  declared bands.

### fig2_main_results — quantitative grid, 182 mm × 2.45 in
**NOT SHIPPED (2026-10-14): the manuscript ships the 10.12 rendering of this
figure** (same content; user chose the 10.12 layout). The design below is kept
as the record only; the shipped art + captions match the 10.12 panel forms.

Core: FRO-2 lowers conditional DFR 4.15–5.47× in all three conditions, per key,
intervals excluding 1.
- (a) **paired dumbbell**: C0 circle ↔ FRO-2 square joined per condition on a
  log DFR axis; one-sided 95% caps as horizontal whiskers closed by vertical
  ticks (the DFR lives on the x axis); fold change above each pair; direct arm
  labels on the first pair; no legend.
- (b) risk-ratio forest with the beyond-1 half-plane tinted ("favours FRO-2"),
  values above each point, dashed null at 1.
- (c) **paired-difference dot strip**: one dot per key-and-condition cell at
  C0 − FRO-2 failures, stacked at equal values; filled hero dots right of zero
  (233), filled near-black left (18), open rings at zero (27).  Position IS
  the direction, so no colour-only encoding.  Counts as three short lines in
  the empty top-right corner.
Data: `t1_formal_main.csv`, `t1_per_key.csv`.

### fig3_mechanism — quantitative grid, 89 mm × 3.6 in
Core: the gain is asymmetric false-flip suppression, not faster correction.
- (a) horizontal bars total / correct / incorrect / residual + ratio column
  (×3.3 / ×2.7 / ×9.5 / ×0.93), RAND only;
- (b) failure-mode shares, monochrome neutral ramp + hatch.
Data: `t1_mechanism_firstround.csv`, `t1_failure_modes.csv`.
(Composition retained from the 10.12 set; already top-journal-adequate.)

### fig4_temporal_dissociation — quantitative grid, 182 mm × 2.75 in
**NOT SHIPPED (2026-10-14): the manuscript ships the 10.12 rendering**
(captions re-aligned to its ungrouped lines + bar panel d). The design below is
the record only.

Core: timing, not magnitude — one-shot helps, sustained destroys, two-sided round 1.
- (a–c) **grouped crossover**: the four one-shot schedules left of a hairline
  separator, the sustained uniform offset right of it, group headers above —
  the dissociation is the visual main clause.  P2 filled / P3 open, direct
  end labels, RR = 1 dashed, coordinates stacked bottom-left of panel (a).
- (d) **effect-size caterpillar**: one point + 95% key-cluster interval per
  round-control arm on a log risk-ratio axis; worse/better half-planes tinted,
  reference at C0 = 1, values beside each interval, arm labels colour-coded.
Data: `t2_temporal_pivot.csv`, `t1_round_controls.csv`.

### fig5_scope_and_boundary — quantitative grid, 182 mm × 2.1 in
Core: transfer without retuning; the benefit stops at capture-prone overlaps.
- (a) P2 forest (hero); (b) capture gradient vs κ with the NCW-aware comparator,
  the κ = d rule and a light wash over the capture-prone region beyond it.
  *(Panel (c), the iteration-budget sensitivity, was cut in the 2026-10-14 trim
  round; its numbers survive as one sentence in Section V-D.)*
Data: `t2_transfer_p2.csv`, `t3_capture_gradient.csv`, `t1_ncw_aware_capture.csv`.

### fig7_modern_decoders — quantitative grid, 89 mm × 3.4 in
**NOT SHIPPED (2026-10-14): the manuscript ships the 10.12 rendering** (caption
unchanged, already matched both forms). The design below is the record only.

Core: FRO-2 is a minimal perturbation — tied with spec-derived BIKE-Flip in RAND,
modest separation elsewhere; third-party decoders use the grey family.
- (a) log DFR bars (C0 / FRO-2 / BIKE-Flip `#767676 ///` / BGF-C3 `#CFCECE \\\`);
  n.s. tags mark BGF-C3 statistically indistinguishable from C0 (RAND, TYPE-I).
- (b) two-round convergence vs offset (conditions neutral, shape channel).
Data: `t1_modern_scaled.csv`, `t1_bgf_baseline.csv`,
`t1_native_l1_holdout_flat.csv`.

## Text sync performed this pass

Captions edited in `plan/sections/` + `plan/sections_zh/` (source of truth),
regenerated via the assemblers; diffs vs the pre-edit main.tex show exactly the
edited captions per language and nothing else:

1. fig1 (c): now describes the stage line (screening → frozen gate → formal
   pool → expanded confirmation → held-out rule check).
2. fig2: panels re-described (paired dumbbell with cap whiskers and fold change;
   tinted favouring region; paired-difference dot strip with 233 / 18 / 27).
3. fig4: one-shot/sustained grouping and separator; panel (d) re-described as
   the risk-ratio caterpillar with 95% intervals and direction half-planes;
   later edit notes the **broken** vertical axis.
4. fig7: the n.s. sentence was corrected (BGF-C3 vs C0, not BIKE-Flip vs
   FRO-2); the stale axis-range phrase ("from 1e-4 to 1e-2") was dropped when
   the range was tightened.

No experiment, CSV or number touched; body prose unaffected beyond captions.

## Verification (2026-10-13)

- `check_palette_v3.py` PASS (21 pairs).
- `verify_numbers.py --en …/en/main.tex --zh …/zh/main.tex` → **382 checks PASS**.
- `scan_numbers.py en/main.tex` → 0 genuinely novel tokens.
- EN 12 pp / ZH 11 pp; both compile with 0 errors; all six figures embedded.
- fig2(c) counts printed by the script: FRO-2 fewer 233, C0 fewer 18, tied 27
  — identical to the manuscript counts.

## Float-overflow repair (2026-10-13, late — "figures running into the text")

Two single-column table floats were wider than the IEEEtran column (252 pt) and
bled across the adjacent column / off the page:

| float | section | natural width | overfull |
|---|---|---|---|
| `tab:added` (Table IV) | s07 (EN+ZH) | ~443 pt | 191 pt (EN) / 188 pt (ZH) |
| `tab:modern` (Table V) | s08 (EN+ZH) | ~393 pt | 141 pt (EN) / 153 pt (ZH) |

Fix: `\begin{table}[t]` → `\begin{table*}[t]` (+ matching `\end{table*}`) in
`sections/s07,s08` and `sections_zh/s07,s08` — layout only, content and captions
untouched.  Reassembled (diff = 4 begin/end pairs per language, nothing else),
recompiled, and the compile logs now report **0 Overfull \hbox / 0 Overfull
\vbox in both languages**; gate 382 PASS; scan 0.

Lesson recorded: the numeric gate cannot see layout.  After every compile,
`grep "Overfull \\hbox\|Overfull \\vbox"` the log; a suspected rule-through-text
on Table III at 110 dpi was re-checked at 300 dpi and was a render artefact —
zoom before editing.

## Rebuild

```bash
python lw-vs/v3/scripts/check_palette_v3.py
for f in fig1_study_design fig2_main_results fig3_mechanism \
         fig4_temporal_dissociation fig5_scope_and_boundary fig7_modern_decoders; do
  python lw-vs/v3/scripts/figs/$f.py
done
# sections are the source of truth for the manuscripts:
python lw-vs/v3/plan/assemble.py && python lw-vs/v3/plan/assemble_zh.py
# then pdflatex ×3 in v3/en/ and xelatex ×3 in v3/zh/, then the gate:
python lw-vs/scripts/verify_numbers.py --en lw-vs/v3/en/main.tex --zh lw-vs/v3/zh/main.tex
```
