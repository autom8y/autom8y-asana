---
type: review
status: accepted
artifact_id: CRITIQUE-recurring-readout-2026-08-13
initiative: exec-insight-delivery (asana-native-insight-delivery)
sprint: EX-5 (WS-2 — DESIGN limb; EXIT HELD pending operator Q-2)
rite: eunomia (rite-disjoint critic)
critic_seat: verification-auditor
subject_author_seat: 10x-dev / requirements-analyst (DISJOINT — eunomia != 10x-dev; Axiom-1 satisfied)
subjects:
  - .ledge/decisions/PROPOSAL-readout-cadence-2026-08-13.md
  - .ledge/specs/SPEC-recurring-readout-template-2026-08-13.md
date: 2026-08-13
evidence_grade: MODERATE (rite-disjoint attestation cap; self-ref-evidence-grade-rule). STRONG only on the own-hands mechanical re-derivations explicitly marked [STRONG — own-hands] below.
binding_verdict: NR-5 = NARROWS (§3) — the BINDING verdict per §A.2 is eunomia's; the author sweep was input only.
design_limb_verdict: CONCUR-WITH-FLAGS (§1) — no BLOCK; two design-completeness FLAGs (F-1 enumeration gap, F-2 truncation branch) + one hygiene FLAG (F-3 withheld-item citation).
fences_honoured: CR-1, CR-2, CR-5 (no credential call, no s3 read, no forbidden git), monorepo-trap (this repo working-tree authoritative — subject is autom8y-asana, NOT the divergent autom8y sibling), C-9 (cadence recorded UNRULED), no infra mutation, no git write.
---

# CRITIQUE — the recurring exec readout (EX-5 DESIGN limb)

Rite-disjoint critic: **eunomia / verification-auditor**. Author: **10x-dev /
requirements-analyst**. Disjointness holds (Axiom-1). This artifact renders the
**BINDING NR-5 verdict** (§3) — the author's own §A sweep is treated as CONTEXT,
never inherited as EVIDENCE (dispatcher-critic-degeneracy guard). Every
load-bearing claim below was re-derived own-hands; the receipts are pasted.

**Scope fence.** Design-limb only. Exit criterion 1 (a live worked render from a
real call) and criterion 3 (a generation-BUILD receipt) are Phase-2 and are NOT
in scope here — they are assessed only as *specified*, not as *built*. No
authenticated/credential-bearing call was fired (CR-5). The subject repo is
`autom8y-asana`; the monorepo trap governs the `autom8y` sibling and does not
apply — this working tree is authoritative (4b converse). `.ledge/decisions/` is
the canonical CONTRACT path; the `.sos/wip/` copy was not read.

---

## §1 — Design verdict per EX-5 exit criterion (design-limb scope)

Shape anchor: `.sos/wip/frames/exec-insight-delivery.shape.md:375-405`.

| EX-5 exit criterion | design-limb disposition | verdict |
|---|---|---|
| 2 — cadence proposal + reasoning; **DF-2 discharged** (UV-P-E-1 derivable) | proposal present, DF-2 formula sound, C-9 honoured; **one structurally-distinct option unenumerated (F-1)** | **CONCUR-WITH-FLAG** |
| 4 — **G4′ sign enumeration** per-number AND per-render (C-5) | structural (slot rides on the number, malformed without it); single-signed PASS re-derived; **truncation branch under-marked (F-2)** | **CONCUR-WITH-FLAG** |
| 5 — denominator honours **C-6** (`k of n` = denominator only) | **DENOM-FENCE is genuinely typed** — refusable, not merely debatable | **CONCUR** |
| 6 — extension point **declared and empty**, EX-2 disposition bound (C-4/DF-5/DF-4) | declared, typed, attested-empty, DF-4 movement-class forbidden | **CONCUR** |
| 1 (design of) — worked render under DR-2 | specified (SC-2); live figure correctly deferred to Phase-2 | **CONCUR (as specified)** |
| 3 (design of) — generation path, no human assembly | specified (§7, SC-8); BUILD correctly deferred to Phase-2 | **CONCUR (as specified)** |
| must-not — rule its own cadence (C-9) | **does NOT rule**; recorded PROPOSAL, decision_owner OPERATOR, divergence recorded | **CONCUR** |

### 1a — Cadence PROPOSAL

**Option-enumeration grade (per `option-enumeration-discipline` §5/§6): CONCUR-WITH-FLAG.**
The slate resolves to **three structurally-distinct scheduling mechanisms** —
fixed calendar interval [A/B/C/D], event-trigger [E], human-pull [F] — plus the
null (F, explicitly labelled) plus the externally-prompted option (E, explicitly
labelled). A/B/C/D are correctly understood by the author as ONE mechanism at
four parameters (not four distinct options), so the minimum-viable-slate
structural bars are technically met.

**FLAG F-1 (enumeration gap — the expected failure mode fired).** One
structurally-distinct option is **not enumerated**: a **bounded-adaptive /
hybrid** cadence — a fixed weekly *floor* with event-escalation when the
`min`-floor as-of crosses a staleness bound. It is a *third* scheduling category
(bounded-adaptive), distinct from pure-fixed and pure-event, and it is the one
option that could hold BOTH derivability (the weekly floor keeps UV-P-E-1
computable) AND the responsiveness the runner-up (A/daily) was reaching for — so
it sits exactly on the A↔B tension the proposal frames as its core tradeoff. It
is **rejectable on the proposal's own AL-5 ground** (the escalation limb is an
alarm, and alarming is owned by the PROV-family successor, `CONTRACT…:742-753`,
re-derived own-hands §2) — but `option-enumeration-discipline` §6 requires a gap
option be **enumerated-and-rejected explicitly**, not left silent. A secondary,
weaker gap: a **delegation** option (ride an existing scheduler rather than mint
a new schedule), distinct from F (pull). Disposition: because ratification is the
operator's **Q-2** (not this seat's — C-9), F-1 does not BLOCK; it rides as input
so the operator sees the complete slate. **Recommendation: add the hybrid
enumerated-and-rejected before Q-2.**

**DF-2 / UV-P-E-1 derivability — DISCHARGED (design-limb).** The formula
(`PROPOSAL §3`) reduces the deadline to `first_occurrence + (N−1)×cadence_interval
+ margins`, with **cadence_interval as the operator-ruled free variable**.
Options A–D make it derivable (constant interval); **E and F correctly FAIL
derivability** — E has no fixed interval so the `(N−1)×interval` term is
uncomputable, F has no schedule at all. This is sound. One precision note (not a
defect): `first_automated_occurrence_date` (D0) is ALSO a free variable, unknown
until the Phase-2 build — the proposal itself caveats this (§3, "stated as a
variable, not asserted"), so "the deadline is a function of a single ruled
variable" is honest in intent: Q-2 fixes the *form*; D0 fixes the *date* at
Phase-2. DF-2 is discharged as *derivability*, correctly not as a fixed date.

**C-9 — HONOURED.** The proposal does not rule cadence: `status: proposed`,
`decision_owner: OPERATOR`, recommendation marked as recommendation throughout,
and **recommendation divergence recorded** (§2: the operator may weight
speed-to-RUNG-E above signal-grain; this seat cannot see that weighting). No
suppressed dissent detected.

### 1b — Template / denominator SPEC

**DF-1 — PRESERVED (own-hands, §2 below). CONCUR.** The four binding constraints
(§1.1) are faithfully grounded against the response contract; `/v1/query/offer/rows`
is genuinely a surface disjoint from the story cache, `section-timelines`, and
`TemporalFilter`.

**C-5 (G4′ per-number AND per-render) — structural, not cosmetic. CONCUR-WITH-FLAG.**
The `g4_prime_bound` slot rides ON the number and regenerates WITH it every
occurrence ("a render that carries the figure without its bound statement is
malformed", §3). This is the structural per-render binding C-5 asks for. The
single-signed PASS (overstate-age only; understate structurally impossible via
the copy relationship) was re-derived own-hands and matches `PREDICATE…:1214-1232`.
See **FLAG F-2** (truncation branch) below.

**C-6 / DENOM-FENCE — genuinely typed, refusable. CONCUR.** The denominator slot
is a **typed** `k`,`n` integers + "sections" unit that "cannot carry an age or a
rate" (§4). This makes the "it is a different kind of claim" argument — the exact
argument R-8 fences (`RULING…:105-108`, re-derived own-hands §2) — **refusable by
construction** rather than debatable: a fourth number cannot enter through the
typed denominator slot; it must route through §5 + a new ruling. This is the
correct realization of the fence.

**C-4 / DF-5 / DF-4 (extension point) — declared, typed, empty-attested. CONCUR.**
The band is a named region; its disposition is bound to EX-2; the empty state is
*attested empty* (EX-2 disposition field populated), not merely blank; DF-4
forbids any movement-class number entering (preserving DF-1). "Still one" is
recorded as a **legitimate passing outcome (DF-5)**, not a failure.

---

## §2 — Own-hands DF-1 check (the receipts)

The task warns DF-1 is "the single easiest thing in this envelope to get wrong."
I verified the four binding constraints (`SPEC §1.1`) against the code and the
frozen CONTRACT, inheriting none of the author's citations.

**Receipt 1 — `last_modified` is a copied, non-nullable column [STRONG — own-hands].**
`src/autom8_asana/dataframes/schemas/base.py:76-82`:
`ColumnDef(name="last_modified", dtype="Datetime", nullable=False,
source="modified_at", …)`. The column is Asana's own `modified_at` copied into
the row — it cannot lead the source it is copied from. This grounds SPEC §1.1
provenance and the single-signed sign (§3).

**Receipt 2 — `/rows` is a side-effect-free surface disjoint from the temporal path [STRONG — own-hands].**
`src/autom8_asana/api/routes/query.py:322-343`: the `POST /v1/query/{entity_type}/rows`
handler (`query_rows`) declares `openapi_extra={"x-fleet-side-effects": []}` and
resolves via `entity_service` / `data_service_client`. `grep` of `query.py`
imports returns **no** `temporal`, `section_timeline`, or `story` import.
`TemporalFilter` lives in `src/autom8_asana/query/temporal.py:25` and is imported
ONLY by `query/__main__.py:875` (the CLI section-timelines path) and by
`api/routes/_exports_helpers.py:46` (which imports `parse_date_or_relative` ONLY,
not the filter class). `section-timelines` is a **separate** route
(`api/routes/section_timelines.py:76,83`). Corroborating contract test:
`tests/unit/dataframes/contracts/test_consumer_column_contract.py:73` asserts
`derive_required_columns("offer", "/v1/query/offer/rows") == frozenset()`.
**Conclusion: item 1a's surface touches neither the story cache, `section-timelines`,
nor `TemporalFilter`. DF-1 is correctly specified.**

**Receipt 3 — constraint 4 (pure function of the bytes) is grounded [STRONG — own-hands].**
SPEC §1.1 constraint 4 ("pure function of the `/rows` response bytes — same
discipline as Lane-G co-sourcing") maps exactly to `CONTRACT…:519-524`: "*if
`content_watermark = max(frame['last_modified'])` is computed from the served
frame at emit time, co-sourcing is not a rule anyone can violate — the signal is
a pure function of the bytes.*" And `CONTRACT…:227-228` records the same column
`base.py:76-82 (nullable=False, source="modified_at")` as the `content_watermark`
axis. The SPEC's DF-1 is not a bare assertion; it inherits the frozen contract's
own co-sourcing guarantee.

**DF-1 verdict: PASS own-hands** — the four constraints are consistent with code
reality and the `/rows` surface is genuinely independent of the broken substrate.

**FLAG F-2 (own-hands — a truncation branch the G4′ table under-marks).** The
SPEC §3 G4′ table marks `clipping / truncation | none on the value | — (neutral)`.
But `/rows` responses ARE subject to filter+limit truncation, and the frozen
CONTRACT carries a **§1.2b truncation guard (T-GUARD)** precisely for this:
`CONTRACT…:404` ("§1.2b Which content axis gates — and the truncation guard
(frozen)"), `:421` ("*watermark is computed over an arbitrary window and MUST NOT
be used to advance*"), and the telos itself records the corrected anchor
(`.know/telos/asana-native-insight-delivery.md:198`: "*a watermark over a
truncated result is a watermark over an arbitrary window*"). Item 1a is a
watermark-class figure (`min` over per-section `max(last_modified)`), so it
inherits exactly this hazard: truncation that drops the **max-bearing row** in a
present section pushes that section's `max` — and hence the `min` floor —
**OLDER**. The **sign is preserved** (older = overstate-age = the alarm-safe,
stale direction), so the single-signed G4′ PASS **survives**. But the branch is
mis-marked "neutral/none on the value" when it is in fact another **overstate-age
contributor**, and — critically — the `k of n` denominator discloses
**section-level** completeness (a section is counted in `k` if it contributed any
non-null value, SPEC §4) and therefore **does NOT surface intra-section
truncation**. **Recommendation (Phase-2-binding):** enumerate the truncation
branch in the G4′ table as an overstate-age contributor, and bind the §1.2b
T-GUARD so the render either carries a truncation disclosure or is gated by it.
This is a design-completeness FLAG, not a DF-1 independence failure.

---

## §3 — The BINDING NR-5 verdict (§A.2)

**Negative under test:** *"the say-able supply is ONE."*

### Verdict: **NARROWS** (independently confirmed, then sharpened — not rubber-stamped).

The bare negative STANDS only under three scope corrections. The author proposed
"say-able NUMBER-class supply is ONE; currency pending EX-2; renderable ≠
say-able." I **confirm** it and **sharpen** two of the three legs own-hands:

1. **NUMBER-class scoped, and renderable ⊋ say-able (strict superset, not merely ≠).**
   R-8 / D-6 (`RULING…:101-108`, re-derived own-hands) rules a `k of n`
   denominator is a completeness statement, **not a number**. Therefore the
   RENDERABLE surface = { item-1a number, `k of n` denominator, the G4′ bound
   statement, orientation text } is a **strict superset** of the say-able
   NUMBER-class = { item 1a }. The D-6 exception changes what is **renderable**
   without changing what is **say-able**. The design encodes this correctly (the
   typed denominator slot, §4). Sharpening: the author's "≠" is precisely "⊋".

2. **Currency: ONE is current as of PREDICATE rev-5 (2026-08-12) and unchanged by
   R-8 (2026-08-13); it is PENDING EX-2, not final.** Re-derived own-hands: the
   say-able set is `PREDICATE-sayable-set-…-2026-08-12.md` **revision 5, final:true**
   (only revision present; no rev-6 exists), item 1a `SAY-ABLE`, item 1b
   `WITHHELD-**PENDING**` with a *named, code-level* condition — "*the binding
   constraint is the event-class mismatch, which no fence ruling can dissolve*"
   (`PREDICATE…:1177`). R-8 is dated one day later (2026-08-13) and does **not**
   touch the count (it rules on denominators, which are not numbers). **EX-2 has
   NOT exited** (no EX-2 exit artifact, no `PREDICATE` rev-6, no telos "1b
   promoted" disposition — searched, all NULL). So "ONE" is a **snapshot at
   PREDICATE-authoring time, pending EX-2's re-derivation of the event-class
   mismatch** — it cannot be closed as final-forever now. The design encodes this
   correctly (extension point declared-empty, EX-2 disposition bound, §5).

3. **The design is BUILT for the narrowed scope.** The NARROWS is not a defect —
   the extension point (pending-EX-2) and the typed denominator (non-number)
   together make the design faithful to exactly the narrowed claim. NR-5 does not
   fall; it narrows, and the narrowing is already load-bearing in the artifacts.

**Why not STANDS-unqualified:** the bare "the say-able supply is ONE" is
ambiguous between number-class and renderable-surface, and between
final-vs-pending — both ambiguities resolve against a naive reading (renderable
is larger; the count is pending). **Why not FALLS:** the say-able NUMBER-class
supply is, in fact, ONE at every date checked; nothing promotes 1b. Hence
**NARROWS**.

---

## §4 — §A.3 reporting duty (receipt grammar)

**(1) Refuters swept + what each returned, including NULLS.**

- **Refuter (a) — currency.** Swept `PREDICATE` rev-5 (2026-08-12) vs R-8
  (2026-08-13) vs EX-2 exit. Returned: item 1a `SAY-ABLE`; item 1b
  `WITHHELD-PENDING` (`:1177`); R-8 does not move the count. **NULL** on any EX-2
  exit artifact / `PREDICATE` rev-6 / telos "1b promoted" (none exist). Result:
  ONE is current-as-of-authoring, **pending EX-2**.
- **Refuter (b) — renderable vs say-able.** Swept R-8 / D-6 (`RULING…:101-108`).
  Returned: denominator renderable but not a number ⇒ **renderable ⊋ say-able**.
  D-6 changes renderable, not say-able. No NULL.
- **Refuter (a′) — 5a labelling wrinkle (swept, NULL-on-impact).** The PREDICATE
  say-able-set line (`:47-48`) lists `5a` under `WITHHELD-PENDING` while `:1182`
  marks 5a `WITHDRAWN at rev-5`. An internal inconsistency in the **inherited**
  PREDICATE — **NULL** on the EX-5 design (1b, not 5a, governs the extension
  point). Noted, not load-bearing here.

**(2) The hop one past where the argument stopped, named concretely.** The
say-able=ONE rests on 1b being `WITHHELD-PENDING`. One hop past 1b's status is
**`src/autom8_asana/query/temporal.py:51-70`** — the `TemporalFilter`
`moved_to` / `idx==0` guard that reads an imputed interval (`entered_at =
created_at`) as a false move (the live defect
`DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`). That is the exact
event-class mechanism **EX-2 must resolve before 1b can promote**; it is a
code-level gate "no fence ruling can dissolve" (`PREDICATE…:1177`). The say-able
count's closure is deferred there, not in this artifact.

**(3) Refuters I ADDED (not in the author sweep).**
- **F-1 enumeration-completeness refuter** (does the cadence slate omit a
  structurally-distinct option?) → **YES**: the bounded-adaptive hybrid (§1a).
  Returns a design FLAG, rejectable on AL-5, add-before-Q-2.
- **F-2 truncation refuter** (does item 1a inherit the §1.2b T-GUARD hazard?) →
  **YES** (§2). Sign stays stale-safe so G4′ PASS survives; the branch is
  under-marked and the denominator does not disclose intra-section truncation.
- **F-3 withheld-item-citation refuter** (does the recommendation rest on a
  WITHHELD/WITHDRAWN item?) → the cadence PROPOSAL cites item **5a** (withdrawn
  at rev-5) as a "for" bullet — the "Monday-morning weekend digest" framing
  (`PROPOSAL…:84-85` → `PREDICATE…:1182`). **NULL on recommendation-material
  impact**: the load-bearing legs (§2 signal-grain / orientation / RUNG-E-
  derivability / separation-of-concerns) do not depend on it. Real but **minor**
  hygiene flag: it imports a withdrawn item's aura. Recommendation: drop it, or
  note explicitly that only the cadence-framing (not 5a's say-ability) is cited.

**(4) Verdict: NARROWS**, corrected scope per §3 — say-able **NUMBER-class**
supply is ONE; **renderable ⊋ say-able** (strict); currency is a rev-5 snapshot
**pending EX-2** (code gate at `temporal.py:51-70`), not final. DISSENT not
softened: the bare claim as written would over-read; the design already carries
the corrections, so the outcome is a narrow, not a block.

---

## §5 — Findings summary & recommendations

| id | finding | severity | disposition |
|---|---|---|---|
| **F-1** | Cadence slate omits the bounded-adaptive (weekly-floor + event-escalation) option — sits on the A↔B tension | FLAG (design-completeness) | Add enumerated-and-rejected (AL-5 ground) **before** operator Q-2 |
| **F-2** | G4′ table marks truncation "neutral/none"; `/rows` §1.2b T-GUARD hazard can move the `min`-floor older; `k of n` discloses only section-level completeness | FLAG (design-completeness) | Phase-2-binding: enumerate the branch; bind §1.2b T-GUARD; disclose/gate on truncation |
| **F-3** | Cadence PROPOSAL cites withdrawn item 5a (`PREDICATE:1182`) as a "for" bullet | FLAG (hygiene, minor) | Drop or scope-note (cadence-framing only, not 5a say-ability) |

**No BLOCK.** The design-limb verdict is **CONCUR-WITH-FLAGS**: DF-1 preserved
own-hands, DF-2 derivability discharged, C-5 per-render structural, C-6
DENOM-FENCE typed/refusable, C-4/DF-5/DF-4 extension point declared-empty-attested,
C-9 not violated. The three FLAGs are inputs to Phase-2 and to operator Q-2; none
halts the design limb (which is HELD on Q-2 regardless).

**Cross-rite / governance note.** F-2 touches the frozen CONTRACT §1.2b T-GUARD
surface and the live `DEFECT-temporal-filter-imputed-false-move` — both already
operator-routed; this critique surfaces the linkage, it does not re-adjudicate
them.

---

## §6 — Evidence grades & self-attestation cap

- **[STRONG — own-hands]**: the mechanical re-derivations in §2 (code file:line
  reads at `base.py:76-82`, `query.py:322-343`, `temporal.py:25`,
  `section_timelines.py:76`, `test_consumer_column_contract.py:73`) and §3 leg 2
  (PREDICATE revision/date, R-8 date, absence of EX-2 exit) — mechanical,
  re-runnable, non-judgmental (per `self-ref-evidence-grade-rule` §Step-2:
  mechanical outputs may retain STRONG).
- **MODERATE** (ceiling) on all design-adequacy JUDGMENTS (enumeration
  completeness, whether F-1/F-2/F-3 are recommendation-material, the NARROWS
  disposition). eunomia is rite-disjoint from 10x-dev (Axiom-1 lifts this above
  pure self-attestation) but this is an in-fleet attestation of a satellite
  design — **STRONG is not claimed** on any judgment. `self-ref-evidence-grade-rule`
  MODERATE ceiling enforced.

**Acid test.** Would I stake my reputation that this design, as specified,
preserves item 1a's independence from the broken substrate and carries exactly
one say-able number under a typed, refusable fence — and that its remaining gaps
(hybrid enumeration, truncation disclosure, one withdrawn-item citation) are
named and non-fatal? **Yes** — with the three FLAGs carried as recorded input,
and NR-5 rendered **NARROWS**.
