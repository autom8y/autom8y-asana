---
type: review
status: accepted
---

# RENDER-PARITY label-map — Sprint 2 receipt (`provenance-to-the-human`)

> Rite: data-analyst (READOUT track, Potnia-downgraded post-supersession; option (b) per the Pythia fork ruling).
> Author role: integrity-guard-author (SPINE build-half). This artifact authors NO oracle / discriminating
> canary / broken fixture and grades NO guard firing — that is the disjoint numerical-adversary
> (critic-never-author). See §PENDING.
> Worktree: `autom8y-asana-wt-prov-s2`, branch `prov/s2-render-parity`, off origin/main `08d9800d`.
> Grandeur anchor honored: DISCLOSE the construction the founder reads; move NO weight value (Reading-A).
> Evidence self-cap: **[STRUCTURAL | MODERATE]** per `self-ref-evidence-grade-rule` (same-rite authorship);
> data-side claims re-graded MODERATE as first-hand file-reads, never STRONG.

## SHA pins (SVR substrate — every claim below resolves against one of these)

| Ref | SHA | What |
|-----|-----|------|
| asana consumer (this worktree base) | `08d9800dad4a682c8a714d0e5438cf85a1e9900f` | `autom8_asana` origin/main; formatter.py + tests read here |
| #216 superseding artifact | `5fc06793c0f59a623d089f5f84dc2f7d42c4bd0b` | `fix(insights): honest cps display labels and tooltips (#216)` (2026-07-08) |
| autom8y-data (denominator registry) | `0df77858aa00ac9c0d8ca4e6d736a413c00d265f` | `autom8y-data` origin/main; `core/metrics/library.py` read here |
| autom8y-data metrics.md alignment HEAD | `513150d7` | ancestor of `0df77858` (verified `git merge-base --is-ancestor` → YES); metrics.md semantics hold, line-anchors have drifted forward ~40-150 lines since |

---

## (a) SUPERSESSION record — chartered collision premise FALSIFIED at HEAD → CLOSED-BY-SUPERSESSION

The Sprint charter framed an SVR-4 premise that the ecps/xcps render surface still carried the pre-split
label collision (ecps mislabeled "Expected CPS", colliding with the net-new xcps). **That premise is
FALSIFIED at `08d9800d`**: the collision was already resolved by #216 `5fc06793` on 2026-07-08, which is
therefore the **superseding artifact** for the chartered Sprint-2 core.

Verification at `08d9800d` (asana `formatter.py`), first-hand file-read:

- `_DISPLAY_LABELS["ecps"] == "Effective CPS"` — `formatter.py:78`.
- `_DISPLAY_LABELS["xcps"] == "Expected CPS"` — `formatter.py:79`.
- GAP-2 rationale comment ("ecps is the STATUS-FILTER metric … xcps is the NET-NEW probabilistic
  show-weight metric spend/solid_scheds") — `formatter.py:74-77`.
- #216 commit body confirms: "ecps display label 'Expected CPS' -> 'Effective CPS' … Add xcps -> 'Expected
  CPS' … count locks updated (labels 27 -> 28, tooltips 10 -> 12)" — `git show 5fc06793` commit message.
- Invariant test present: `test_display_labels_honest_cps_naming` asserting `ecps != xcps` labels —
  `tests/unit/automation/workflows/test_insights_formatter.py:1300-1311`.

Disposition: **SVR-4 premise → CLOSED-BY-SUPERSESSION.** No rebuild of labels+tooltips+invariant-test
performed (they LANDED at #216). Sprint scope reduced to R3 prose + this receipt per the fork ruling
(READOUT track).

> [UV-P: exact charter §-anchor for the SVR-4 collision premise | METHOD: deferred — charter/frame artifact
> carried in the Sprint-2 dispatch prose (Pythia fork ruling), not resolvable to a fetchable file at
> `08d9800d` in either worktree | REASON: no on-disk frame file matched `render-parity`/`prov-s2`/`SVR-4` under
> a `git ls-files` + `find` probe of both the asana consumer and the data-analyst rite worktree; the
> supersession FACT is receipted above against live code+commit, only the charter's own §-locator is deferred.]

## (b) UV-P-3 disposition — xcps absence DISCHARGED-BY-PRESENCE

The charter carried UV-P-3: "xcps label/tooltip may be ABSENT at the consumed render." **Discharged by
presence** at `08d9800d`:

- xcps label present — `formatter.py:79` (`"xcps": "Expected CPS"`).
- xcps tooltip present — `formatter.py:112` (`"xcps": "Expected CPS: Spend ÷ probability-weighted expected shows"`).

Disposition: **UV-P-3 → DISCHARGED-BY-PRESENCE** (RULE-1 consumed-within-initiative; the deferred claim is
answered by a subsequent first-hand read in the same initiative). xcps is registered AND rendered; it is not
absent.

## (c) R3 closure receipt — tooltip denominator prose corrected (Reading-A: prose only, no value moved)

**Defect (verified live at `08d9800d`):** the founder-facing tooltips the founder reads AT THE POINT OF
ACTION misstated the four rate metrics' own construction. All four rates divide by the probability-weighted
`solid_scheds` denominator in the autom8y-data registry, NOT the bare scheduled/shown/lead counts the
tooltips named.

Data-side registered denominators (autom8y-data `core/metrics/library.py` @ `0df77858`, first-hand read):

| Metric | name @ | `total="solid_scheds"` @ | positive-floor guard `min_denominator=` @ | true formula |
|--------|--------|--------------------------|-------------------------------------------|--------------|
| `ns_rate`  | `library.py:2466` | `library.py:2470` | `library.py:2471` | `ns / solid_scheds × 100` |
| `nc_rate`  | `library.py:2502` | `library.py:2506` | `library.py:2507` | `nc / solid_scheds × 100` |
| `conv_rate`| `library.py:2536` | `library.py:2540` | `library.py:2541` | `convs / solid_scheds × 100` |
| `nsr_ncr`  | `library.py:2575` | `library.py:2579` | `library.py:2580` | `ns_nc / solid_scheds × 100` |

`solid_scheds` itself: `name="solid_scheds"`, description "Probabilistically-weighted scheduled appointments
denominator", `ProbabilisticDenominatorFormula` — `library.py:2386-2387`. This is the honest denominator
concept the corrected prose names.

**Before → after** (asana `formatter.py` `_COLUMN_TOOLTIPS`, this worktree):

| key | line | BEFORE (`08d9800d`) | AFTER (this commit) |
|-----|------|---------------------|---------------------|
| `conv_rate` | :117 (before) / :125 (after) | `Conversion Rate: Conversions ÷ total leads` | `Conversion Rate: Conversions ÷ probability-weighted scheduled appointments` |
| `ns_rate` | :118 / :126 | `No-Show Rate: No-shows ÷ scheduled appointments` | `No-Show Rate: No-shows ÷ probability-weighted scheduled appointments` |
| `nc_rate` | :119 / :127 | `No-Close Rate: No-closes ÷ shown appointments` | `No-Close Rate: No-closes ÷ probability-weighted scheduled appointments` |
| `nsr_ncr` | (absent) / :128 | *(no tooltip existed)* | `NSR/NCR: Lost appointments (no-shows + no-closes) ÷ probability-weighted scheduled appointments` |

Rationale per touched tooltip:

- **`conv_rate`** — doubly wrong at HEAD: the tooltip named `Conversions ÷ total leads`, but the registered
  `conv_rate` is `convs / solid_scheds` (`library.py:2540`), NOT `convs / leads`. Corrected to name the
  weighted denominator. **Explicitly NOT conflated** with the sibling `conversion_rate` metric
  (`scheds / leads`, `formula=PercentageFormula(metric="scheds", total="leads")` at `library.py:2107-2109`),
  which correctly divides by leads and carries NO tooltip at HEAD — left untouched. The name-collision is
  real and is documented data-side at `library.py` conv_rate `semantic_note` ("distinct from conversion_rate
  … which is (scheds / leads)").
- **`ns_rate`** — named "scheduled appointments"; the true denominator is the probability-weighted
  `solid_scheds` (`library.py:2470`). Corrected.
- **`nc_rate`** — named "shown appointments"; doubly wrong — the registered `nc_rate` denominator is
  `solid_scheds` (scheduled-weighted, `library.py:2506`), not "shown". Corrected to the weighted-scheduled
  denominator.
- **`nsr_ncr`** — the #1 client-health lost-appointment metric had a LABEL ("NSR/NCR", `formatter.py:84`) but
  NO tooltip. Added one line with honest weighted semantics (`ns_nc / solid_scheds`, `library.py:2579`), IN
  scope per max-value. This is the only ADDITION; it moves the tooltip map from 12 → 13 entries.

Idiom fidelity: "probability-weighted" mirrors #216's xcps tooltip ("probability-weighted expected shows",
`formatter.py:112`) and the data-side `solid_scheds` description ("Probabilistically-weighted scheduled
appointments", `library.py:2387`). Founder-readable, denominator honest.

**Reading-A honored:** prose only. No weight value moved, no metric registration touched, no value emitted.
Runtime-parsed confirmation (package env, `uv run`): the four tooltips now read the corrected prose;
`conversion_rate` still `<NO TOOLTIP>`; tooltip count 13, label count 28 (unchanged).

**Count-lock kept honest** (mechanical lock maintenance — NOT a discriminating fixture; see §PENDING):

- `test_column_tooltips_populated` `len(_COLUMN_TOOLTIPS) == 12` → `== 13` — `test_insights_formatter.py:1330`.
- `test_column_tooltips_count` (`TestPhase6QA`) `== 12` → `== 13` — `test_insights_formatter.py:2545`
  (a SECOND lock, surfaced ONLY by running the suite — the initial grep found `:1330` alone).
- `test_display_labels_count == 28` (`:2541`) and `test_section_subtitles_count == 12` (`:2549`) left
  UNCHANGED — no labels or subtitles touched.

## (d) DEFER-6 — narrowed to R4-ONLY, owner re-attributed to Sprint-1 asOf render leg

DEFER-6 is narrowed to **R4-ONLY** and its owner **re-attributed to Sprint-1's asOf-carry render leg** per
the Pythia fork ruling + Sprint-1 contract's R4 note. R4 is the `_SECTION_SUBTITLES` asOf-carry seam
(`formatter.py:124-137`) — HANDS-OFF this sprint (I touched none of those 12 subtitle lines; verified: a
`git diff` grep for `_SECTION_SUBTITLES` returns 0). Registered as a `defer-watch-manifest` item:

- **Item**: R4 asOf-carry into `_SECTION_SUBTITLES` render.
- **Owner-rite**: Sprint-1 asOf render leg (NOT this READOUT sprint).
- **Watch-trigger**: any Sprint-1 asOf-carry activation touching `formatter.py:124-137`.
- **Deferral-rationale**: disjoint render seam; folding it here would violate the fork ruling's hands-off
  boundary and re-open a proven surface.

> [UV-P: exact Sprint-1 contract §-anchor for the R4 note + the DEFER-6 origin locator | METHOD: deferred —
> Sprint-1 contract carried in dispatch prose | REASON: not resolvable to a fetchable file under
> `git ls-files`/`find` at `08d9800d`; the R4 boundary is receipted by the untouched-subtitles diff above.]

## (e) WS-6 — glint supersession annotation (a8/a8) + metrics.md re-anchor DEFERRED as F2-drift-watch

**AUDIT #1 correction (recorded):** the earlier attribution of the UNRATIFIED-lineage to `ecps` /
`esp20m` → `effective_scheds` was WRONG. `ecps = spend / effective_scheds` is a STATUS-FILTER (deterministic
six-status count), which is ratified-by-construction. The TRUE UNRATIFIED weight lineage is
**`nsr_ncr` + xcps** (and the rate family), because those consume the **probability-weighted `solid_scheds`**
whose show-probability weights are the un-ratified lever (`weights_version` /
`weights_provenance_inherited_from: "solid_scheds"`, e.g. `ns_rate` ai_metadata at `library.py:2493-2495`).
The glint supersession annotation carrying this correction was applied in `a8/a8`; the correction traces to
the Sprint frame §4 R2/SVR-1.

> [UV-P: frame §4 R2/SVR-1 exact anchor + the a8/a8 glint file path | METHOD: deferred — frame carried in
> dispatch prose; the a8/a8 glint lives in the sibling monorepo outside this worktree's read scope | REASON:
> `find`/`git ls-files` in this worktree returns no `render-parity` frame; the correction's SUBSTANCE
> (ecps=effective_scheds ratified vs nsr_ncr+xcps=solid_scheds UNRATIFIED) is receipted first-hand against
> `library.py` @ `0df77858` above.]

**metrics.md re-anchor — DEFERRED as named F2-drift-watch.** autom8y-data `.know/metrics.md` is
**semantically correct at HEAD** (its supersession blocks correctly flip xcps/solid_scheds claims to PRESENT
and name the R3 floor + the four rates as solid_scheds consumers — `metrics.md:88-95, 121, 124`). What has
drifted is its LINE-ANCHORS: metrics.md aligned to `513150d7` and records `MIN_SOLID_SCHEDS_DENOMINATOR` at
`library.py:89` and the floor sites at `:2421/2452/2483/2519`; at CURRENT origin/main `0df77858` the constant
is at `library.py:95` and the `min_denominator=` sites are `:2471/2507/2541/2580`. Content correct;
anchors-only drift; recurring class (documented ~40-150-line drift per merge).

- **Registered as `defer-watch-manifest` item F2-drift-watch**: metrics.md line-anchor re-alignment.
- **Deferral-rationale**: content is semantically correct at HEAD; only line-numbers drift. The recurring
  drift class is owned by the **systemic `.know`-align fix** (autom8y-data ZETA `.know`-alignment cadence),
  NOT by a manual per-anchor wave in THIS asana sprint. Manual re-anchoring here would be a bandaid over a
  systemic drift.
- **Watch-trigger**: next autom8y-data `.know`-align cycle, OR any consumer that reads a metrics.md
  line-anchor and finds it >1 metric-block stale.
- **Owner-rite**: autom8y-data `.know`-align (systemic), not data-analyst READOUT.

## (f) PENDING — two-sided proof OWED by the disjoint numerical-adversary (critic-never-author)

This artifact **builds** the R3 disclosure and keeps the mechanical count-lock honest. It authors **NO**
discriminating canary and grades **NO** guard firing. The following are OWED by the DISJOINT
numerical-adversary (SPINE prove-half), armed against the named seams below:

1. **R3 prose fixture (honest-naming discriminating canary)** — a two-sided, TEST-ONLY canary on the
   already-working tooltip surface: a **mislabeled-map RED** (a deliberately-wrong denominator string in the
   fixture's copy of the map → CAUGHT) paired with the **ruled-correct map GREEN** (the four
   "probability-weighted scheduled appointments" tooltips + xcps pass). Per `discriminating-canary-doctrine`
   mode (1): NO defect is injected into #216's working surface or into the shipped `_COLUMN_TOOLTIPS`; the
   RED is a broken INPUT the assertion correctly rejects. The canary must bite ONLY on the mislabel and the
   correct-map variant must pass (teeth, not presence).

2. **Named seams the adversary arms against** (G3/G4 guards — built and LANDED data-side; I name where they
   fire, I do NOT grade whether they bite):
   - **G3 edge-ordered guard** — the degenerate `solid_scheds ∈ (0, 0.5)` residual arm is ordered BEFORE the
     division via the positive minimum-support floor `MIN_SOLID_SCHEDS_DENOMINATOR = 0.5`
     (`library.py:95`), applied at each rate's `min_denominator=` site (`library.py:2471/2507/2541/2580`) so
     `spend/0.2`-class inflation is UNREPRESENTABLE. Rationale verbatim at `library.py:84-95` ("a tiny
     POSITIVE residual (e.g. 0.2) … passes a naked `== 0` check … below 0.5 the denominator is a
     discounting-residual, not a real cohort"). Input class the guard refuses: `0 < solid_scheds < 0.5`.
   - **G4 typed refusal** — the division family mints a typed None/null refusal (not a fabricated number)
     when the denominator is below-floor or within declared zero-tolerance; the tolerance is a NAMED module
     constant (declared, not naked float-equality). Data-side attestation: metrics.md R3/R4 rows
     (`metrics.md:124, 128`) + the min-support-floor table (`metrics.md:121`).
   - Adversary's teeth suite (data-side, DISJOINT-owned, NOT authored/graded here):
     `tests/ci_guards/test_division_family_r3_teeth.py` (the `0<x<0.5` refuse regime) and
     `..._r4_equivalence.py` (scalar↔vectorized zero-classification equivalence), per
     `.ledge/decisions/RULING-division-family-guards-2026-07-08.md` and `metrics.md:130`.

3. **Consumed-render proof obligation (grandeur anchor)** — the two-sided proof must land at the ACTUAL
   consumed render (provenance-stripped RED-CAUGHT / disclosed GREEN), NOT emission-side CI, NOT a green
   merge, NOT a field-exists-in-payload check. That render-altitude proof is the adversary's, not built here.

## Disjointness note

Per SPINE build/prove split and `critic-never-author`: this artifact names the seams each guard fires at and
records the R3 disclosure. It authors NO oracle, NO discriminating canary, NO deliberately-broken fixture,
and grades NO firing. Building the guard AND grading whether it bites in one soul is the FORBIDDEN merge
(self-attestation) — the disjoint numerical-adversary owns §PENDING items 1-3.
