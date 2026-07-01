---
# ============================================================================
# HANDOFF Artifact Schema v1.0 — gfr-dynvocab rnd -> 10x-dev (myron /frame)
# ============================================================================
artifact_id: HANDOFF-rnd-to-10x-dev-2026-06-25
schema_version: "1.0"

source_rite: rnd
target_rite: 10x-dev

handoff_type: implementation       # Research -> Dev (per cross-rite-handoff §Handoff Types)
priority: high
blocking: false                    # rnd cannot proceed past feasibility-proven; the build lever is the user's (MINE). Not blocking rnd.

initiative: gfr-dynvocab
created_at: "2026-06-25T00:00:00Z"
status: draft               # .ledge/ doc-lifecycle status (recognized enum)
handoff_status: pending     # HANDOFF schema v1.0 work-transfer state: pending | in_progress | completed | rejected

type: handoff
from_rite: rnd
to_rite: 10x-dev

source_artifacts:
  - .ledge/specs/gfr-dynvocab-alignment-brief.md          # LOCKED INCEPTION (status: accepted; 12 decisions)
  - .ledge/spikes/gfr-dynvocab-recon.md                   # technology-scout: paradigm recommendation (4-ecosystem convergence)
  - .ledge/spikes/gfr-dynvocab-integration.md             # integration-researcher: hidden-dep map + P0-P5 migration
  - .ledge/spikes/gfr-dynvocab-prototype-findings.md      # prototype-engineer: feasibility-PROVEN, HYP-1/HYP-2 settled
  - .ledge/spikes/gfr-dynvocab-moonshot.md                # moonshot-architect: 5-future stress test + scoped dissent
  - .ledge/specs/gfr-tdd.md                               # certified engine TDD
  - .ledge/reviews/gfr-certification-case-file.md         # certs (never regress)
  - .know/telos/gfr.md                                    # parent-initiative telos (R1 attester pattern carried)

provenance:
  - { source: ".ledge/spikes/gfr-dynvocab-recon.md",      type: artifact, grade: moderate }
  - { source: ".ledge/spikes/gfr-dynvocab-integration.md", type: artifact, grade: moderate }
  - { source: ".ledge/spikes/gfr-dynvocab-prototype-findings.md", type: artifact, grade: moderate }
  - { source: ".ledge/spikes/gfr-dynvocab-moonshot.md",   type: artifact, grade: moderate }
  - { source: ".ledge/specs/gfr-dynvocab-alignment-brief.md", type: spec,  grade: moderate }
evidence_grade: moderate
  # CEILING. rnd-dk caps at MODERATE (4 literature files at 0.68-0.77 confidence; STRONG unavailable in this rite).
  # Self-ref ceiling also caps at MODERATE per self-ref-evidence-grade-rule.
  # STRONG paradigm-LOCK requires the rite-disjoint corroboration at THIS transfer seam (see §GO/NO-GO) — named, never self-granted.

tradeoff_points:
  - attribute: "free-tail (HYP-1) vs payload-width at 100x fields"
    tradeoff: "bare custom_fields opt-field pulls ALL cf for ~0 resolution cost, but widens the entry-fetch wire payload as field count grows"
    rationale: "DEFER the fetch-all-vs-project decision to trigger S1c; default to free-tail. Projecting defeats HYP-1."
  - attribute: "per-repo drift gate (Option A) vs fleet contract registry"
    tradeoff: "Option A is a two-way-door per-repo CI check; a fleet field-contract registry is correct at 5-service scale but a one-way door once 2+ services bind"
    rationale: "Frame Option A as baseline; F-D fleet registry is ESCALATE-on-trigger (S4a/S4c), not a default build."
  - attribute: "schema codegen (Option B) vs additive tail + drift gate (Option A)"
    tradeoff: "codegen would fix drift fleet-wide but REVERSES ADR-S4-001 and cannot synthesize cascade/derived columns"
    rationale: "Option B stays a one-way-door escalation to user/moonshot-architect; NOT defaulted by this handoff."

response_due: "2026-07-02T00:00:00Z"
---

# HANDOFF — gfr-dynvocab: rnd -> 10x-dev (consumed by myron `/frame`)

> **Grandeur anchor (verbatim).** gfr-dynvocab makes any fleet caller resolve a
> gid to ANY field the entity actually carries — reflectively,
> heuristically-typed from cf-type metadata, governed-strict (so 'unknown' means
> genuinely absent) — on top of the STRONG-certified identity spine, never
> regressing it.

> **What this HANDOFF is.** The rnd inquisition reached the rung
> **META-OPTIMAL-PARADIGM-SELECTED + FEASIBILITY-PROVEN** at evidence grade
> **MODERATE**. It packages the paradigm recommendation, the production gaps the
> throwaway prototype deliberately shortcut, and a **GO** verdict for proceeding
> to `myron /frame`. It does NOT build, merge, or lock the paradigm — those
> levers are the user's (10x-dev + MINE). The certified `feat/gfr-engine` spine
> was never touched by the prototype.

> **⚠️ POST-HANDOFF OPERATOR CORRECTION (2026-06-25) — KEYING AXIS = NAME, NOT gid.**
> The operator overturned the recon's "key by cf `gid` not name" (Iceberg field-ID)
> refinement as a domain misfit. **Supersedes the gid-keying in §1.1(b), GAP-4, and
> FRAME-002 wherever it appears below.** The vocabulary + override registry + coherence
> gate key by the **canonical business-field NAME** (the model's `field_name` /
> `NameNormalizer.normalize(cf.name)`) — the grain the whole codebase already follows
> (`field_resolver.py:61` `name_to_gid`; `default.py:92` `_index[normalize(name)]=gid`;
> schema `source="cf:Name"`; model `field_name="..."`). cf `gid` is a **runtime
> intra-task value handle only** (opaque + per-workspace + non-portable). Rename-stability
> comes from the model-`field_name`-as-source-of-truth + the coherence drift-gate, NOT
> gid-keying. Full rationale: `.ledge/specs/gfr-dynvocab-alignment-brief.md` §"Post-inquisition
> CORRECTION". myron `/frame` MUST inherit name-keying.

---

## 1. Consolidated Paradigm Recommendation

### 1.1 The recommended paradigm (evidence-graded)

A **(f) + (d-bounded) + (b-governance) composite**, named verbatim from the recon
and prototype-confirmed:

- **(f) Asana `resource_subtype`-driven reflective coercion** for the GFR-layer
  dynamic tail — served off the already-hydrated entry task. This is the typing
  ground truth; it is **~80% already in-tree** (`DefaultCustomFieldResolver._extract_raw_value`,
  `src/autom8_asana/dataframes/resolver/default.py:234-287`). [PLATFORM-HEURISTIC — Asana-coupled]
- **(d-bounded) dynamic-ORM-style tail reflection**, explicitly **bounded** per
  entity (the manifest = the task's own cf keys) so it cannot become
  Elastic-style "mapping explosion." [MODERATE | rnd-dk ceiling]
- **(b) Iceberg-style dataframe-coherence governance** as a drift gate for the
  dataframe layer. **[CORRECTED 2026-06-25 — keyed by canonical field NAME**
  (model `field_name` ↔ schema `cf:Name`), NOT cf `gid`. The static model/schema
  layer carries no runtime gids; the codebase keys by name throughout. Iceberg's
  *rename-stability* kernel is kept via model-as-source-of-truth + this gate, not
  gid-keying.] [MODERATE | rnd-dk ceiling]

**Overall evidence grade: MODERATE.** This is the rnd-dk ceiling (STRONG is
structurally unavailable in this rite) AND the self-ref ceiling. Four ecosystems
(data-lake, lakehouse, document-store, dynamic-ORM) independently converge on the
typed-core + bounded-heuristic-tail hybrid; the Elastic counter-case names the one
failure mode (unbounded tail) the brief's governed-strict manifest already guards.
Sources cited in `.ledge/spikes/gfr-dynvocab-recon.md` (Iceberg schema projection,
Delta Lake schema enforcement, schema-drift/data-contracts, Elastic field
explosion, SQLAlchemy automap, Asana custom-fields guide, Apollo GraphQL resolvers).

### 1.2 Feasibility verdict: PROVEN

The throwaway prototype (`.sos/wip/spikes/gfr-dynvocab/proto_dynvocab.py`,
scratch — never committed to `feat/gfr-engine`) **resolved the HARD case**:
`asset_id` (cf-type `text`, raw `"a1, a2 ,a3,a4 "`) -> `{'a1','a2','a3','a4'}`
(set), via the comma-split override — receipt pasted in
`.ledge/spikes/gfr-dynvocab-prototype-findings.md`. This is the G-THEATER guard
discharged: feasibility is proven by a WORKING prototype resolving the hard case
on a real canary manifest + HYP-1/HYP-2 receipts, NOT by a citation-with-no-code
or a demo that dodged `asset_id`. [Evidence: prototype run output, pasted at
`.ledge/spikes/gfr-dynvocab-prototype-findings.md` lines 92-105.]

- **HYP-1 SETTLED YES (the tail is FREE).** `_BUSINESS_FULL_OPT_FIELDS =
  list(STANDARD_TASK_OPT_FIELDS)` (`src/autom8_asana/models/business/hydration.py:69`)
  and `STANDARD_TASK_OPT_FIELDS` (`src/autom8_asana/models/business/fields.py:232-251`)
  requests the bare `custom_fields` array PLUS every typed value sub-field. The
  entry task already carries every cf with values; `asset_id`'s value is fetched
  then discarded for want of a schema column. Settles brief OPEN FORK #2.
  [Structural receipt; one residual UV-P — see §2 GAP-1.]
- **HYP-2 SETTLED YES (marginal cost ~0).** 20 fields resolve in 5.5µs vs a
  ~200-500ms API fetch baseline — ~40,000x cheaper, O(1) dict scan, zero
  additional network I/O. [Prototype benchmark, pasted at findings lines 73-82.]
- **Generality CONFIRMED (>=2 EntityTypes).** Same `DynVocabResolver` class +
  heuristic table resolved Offer (canary `b167331c-536f-4996-9b2d-2f696f35f556`)
  AND Business with no entity-special-casing. G-DENOM satisfied. [Findings lines 124-144.]
- **Governed-strict CONFIRMED.** Absent field -> `UNKNOWN` sentinel, distinct from
  present-but-null -> `None`. 'unknown' means genuinely absent. [Findings lines 152-162.]

### 1.3 Reconciliation against the brief's 12 locked decisions

The inquisition **CONFIRMS the brief's favoured approach — no locked decision is
violated.** Per-decision check (brief at `.ledge/specs/gfr-dynvocab-alignment-brief.md`):

| Brief decision | Inquisition disposition |
|---|---|
| Dynamism = hybrid (typed core + heuristic tail) | CONFIRMED — paradigm (f)+(d-bounded) is exactly this |
| Source of truth = open to paradigm shift, grounded by rnd | DISCHARGED — rnd grounded it (4-ecosystem convergence, evidence-graded) |
| Unknown-field posture = governed-strict | CONFIRMED — prototype demonstrated UNKNOWN-vs-None distinction |
| Blast radius = BOTH layers | CONFIRMED — drift is fleet-wide systemic, not asset_id-only (integration map §4) |
| Tail timing/home = hybrid manifest + lazy, off hydrated entry task | CONFIRMED — HYP-1 settled YES, tail is free off the entry task |
| Tail typing = cf-type heuristic table + override registry | CONFIRMED — table ~80% in-tree; override mechanism proven |
| PROOF OVERRIDE: asset_id text -> comma-split set | CONFIRMED — hard case resolved live on canary |
| Typing provenance = per-field typing-origin tag | CONFIRMED feasible — additive `FieldWithProvenance` field (gap, see §2) |
| Spine safety = strictly additive, 105 tests are the gate | CONFIRMED — tail is `is_identity=False`, invisible to identity guard |
| Initiative shape = sibling, own frame/shape/telos, same branch | CONFIRMED — this handoff feeds that frame |
| Coherence scope = BOTH layers (drift gate or codegen) | CONFIRMED w/ SCOPED DISSENT — see §1.4 |
| Generality = all-entities by design | CONFIRMED — >=2 EntityTypes proven; "without code change" qualified (see §1.4) |

### 1.4 Did rnd surface a BETTER paradigm than the brief favored?

**For the TAIL: no — the brief's favoured (f)+(d-bounded) is meta-optimal and
unbeaten at horizon.** All five 2-yr futures confirm tail paradigm-stability
(moonshot §Per-Scenario Stress Test).

**For the COHERENCE LAYER: yes, a scoped refinement — moonshot CONFIRMED-WITH-
SCOPED-DISSENT, not plain CONFIRM.** The recon graded per-repo **Option A**
(drift CI gate) meta-optimal but folded only HALF of its own SRC-002 (Iceberg)
evidence — the "field-ID not name" half — and dropped the **contract-registry**
half. At single-repo scale Option A is correct. At fleet scale (5 autom8y
services, which the brief itself scopes) Option A **breaks as a doctrine**: 5
independent hand-maintained allow-lists is not coherence. The horizon answer is a
**shared cf-`gid` -> typed-contract registry** (Iceberg in full). This is a
truncated-option-slate gap per `option-enumeration-discipline`. **This dissent does
NOT reopen ADR-S4-001** (codegen stays a one-way-door escalation; the registry is
orthogonal and generates no schema files).

**The frame must carry this as a NAMED FUTURE COMMITMENT with a defined trigger
(F-D), not a default build.** See §4 and the DEFER register.

---

## 2. Production Gaps (prototype shortcuts -> frame requirements)

> The throwaway prototype is **REFERENCE ONLY** — production must be reimplemented
> against production contracts (the `entity_registry.py:136` resolver hook + the
> certified entry seam). The prototype code must NEVER be committed to
> `feat/gfr-engine`. Every gap below has severity, effort, and impact-if-unaddressed.

| ID | Gap (prototype shortcut) | Severity | Effort | Impact if unaddressed | Acceptance criterion (frame requirement) |
|----|--------------------------|----------|--------|-----------------------|-------------------------------------------|
| **GAP-1** | **Live-Asana fetch** — prototype used a fixture dict, not a live `client.tasks.get_async`. Single residual UV-P: does the live bare `custom_fields` opt-field actually return `asset_id` populated for canary `b167331c-...`? | **HIGH** (blocks the realization predicate; settles the one platform UV-P) | <1 dev-day | If Asana does NOT return all workspace cfs on the bare opt-field, the free-tail premise (HYP-1) is wrong -> frame-based fallback at ~2x effort | A live fetch against real Asana confirms `asset_id` populated in the API response for the canary; OR the frame-based fallback is scoped. **This is the FIRST build-phase probe (P1 entry-criterion).** |
| **GAP-2** | **EntryAnchor threading** — prototype bypassed the `entry.py:111-116` seam that discards `custom_fields`. | MEDIUM | ~1 dev-day | Tail has no task to read off; the free tail is unreachable in production | `EntryAnchor` additively extended with one optional `entry_task` field; task threaded past `entry.py:111-116`; 105 tests stay green. Strictly additive. |
| **GAP-3** | **Resolver-hook wiring** — prototype reimplemented logic inline, no `autom8_asana` imports. | LOW | ~1 dev-day | Duplicated logic drifts from the certified resolver | Production wires into `entity_registry.py:136` `custom_field_resolver_class_path`; reuses `DefaultCustomFieldResolver._extract_raw_value` (`default.py:234-287`). |
| **GAP-4** | **Override registry NOT EntityType-scoped** (moonshot D4) — cross-entity dtype divergence (`offer_id` Utf8 on Offer, Int64 on AssetEdit) cannot be expressed. *(The shortcut-#4 "key by name" is now the CORRECT production choice per the 2026-06-25 operator correction — name-keying is retained, NOT switched to gid.)* | **MEDIUM** (downgraded — name-keying is correct; only EntityType-scoping + rename-drift-detection remain) | ~1 dev-day | Cross-entity dtype divergence unexpressed; an Asana cf rename mis-routes an override until the coherence gate flags it | Override registry keyed by **canonical field NAME** (`NameNormalizer.normalize(cf.name)`, matching the model `field_name`) AND **EntityType-scoped**; cf rename caught by the coherence drift-gate (FRAME-005), not by gid-keying. |
| **GAP-5** | **`date_value` NOT in opt-fields (moonshot D2 — a LIVE gap, not hypothetical).** grep `date_value` in `fields.py` = 0 matches, yet `_extract_raw_value` `case "date"` reads it. | **HIGH** | <0.5 dev-day | A `date` cf resolves to `None` on the LIVE fetch TODAY — masked in the prototype by a fixture that hand-supplied `date_value`. Governed-strict is violated: present-but-typed-date looks absent. | `custom_fields.date_value` added to `STANDARD_TASK_OPT_FIELDS` (`fields.py:232-251`); a live `date` cf resolves to its value, not `None`. |
| **GAP-6** | **No FieldWithProvenance / typing-origin tag** (brief Phase-2 decision; shortcut #5). | MEDIUM | ~1 dev-day | A caller cannot distinguish a schema-validated value from a heuristically-coerced one | Resolved payload carries `typing_origin: Literal['schema','heuristic','override','absent','fallback']`; `extra="forbid"`-safe additive field. |
| **GAP-7** | **No name-collision policy** (moonshot D3 — first-match-wins + warn, `default.py:84-90`). | MEDIUM | ~2 dev-days | At 100x fields, two cf normalizing to one name silently drop the loser | DEFER to trigger S1a/S1b (manifest-build p99 > 5ms OR entry payload > ~500 cf). Watch-registered. Until then, gid-keying (GAP-4) already mitigates by construction. |
| **GAP-8** | **No fallthrough observability** for unknown cf subtypes (moonshot S5a; `case _ -> display_value`). | LOW | <0.5 dev-day | Asana's yearly new cf subtypes silently degrade to strings unobserved | Fallthrough counter + `typing_origin: 'fallback'` tag on the `case _` branch; makes S5a observable. |
| **GAP-9** | **Dataframe-coherence mechanism is unbuilt** (Option A drift gate). | MEDIUM | ~2-4 dev-days (Approach 1) | Model<->schema drift recurs silently (the original `asset_id` smell) | Extend existing import-time `_validate_extractor_coverage` (`registry.py:168`) using `_pending_fields`/`Fields` auto-gen registry (ADR-0082). Warn-first, then promote. Honors ADR-S4-001. **Option B (codegen) is ESCALATE-only.** |
| **GAP-10** | **No error-handling/operability hardening** — prototype had no logging, no metrics, no graceful-degradation telemetry. | MEDIUM | folded into P1-P3 | Production tail failures are invisible; no rollback signal beyond the 105-test gate | Tail emits structured logging on resolution; manifest-build time + `len(custom_fields)` metrics at the entry seam (also feeds S1 triggers); the 105 certified tests are the mechanical non-regression rollback trigger. |
| **GAP-11** | **No 105-test regression gate run by the prototype** (shortcut #6). | n/a (discipline, not a code gap) | continuous | A production change could silently regress the certified spine | Every P1-P4 phase runs `./.venv/bin/python -m pytest tests/unit/resolution/gfr/ tests/integration/test_gfr_tenant_roundtrip.py` (NOT `uv run` — CodeArtifact 401) GREEN as the continuous rollback trigger. |

**Non-negotiable constraints (what MUST stay the same — as load-bearing as the
requirements):**

1. **The STRONG-certified GFR spine is strictly-additive-protected and FROZEN.**
   Worktree `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr`, branch
   `feat/gfr-engine`, tip `2092f771`. The tail is a separate `is_identity=False`
   layer; it MUST NOT enter `_resolve_identity_plan_async` or the GAP-1
   `assert_rows_tenant_identity` guard. company_id stays `is_identity=True` on the
   gid-exact frame path. **WHY**: this is what the 105 certified tests validate;
   regressing it reopens CERT-1/CERT-3.
2. **Cache-only contract** (`body_parameterized=False`, offer-domain HARD line) —
   the tail inherits it: NO new Asana call beyond the accounted entry read. **WHY**:
   HYP-1's "free tail" rests on the entry fetch being the only accounted read.
3. **The 105 certified tests are the regression gate** — run with `./.venv/bin/python`,
   never `uv run` (CodeArtifact 401). **WHY**: mechanical non-regression invariant.
4. **ADR-S4-001 (schemas NOT generated from descriptor metadata) holds** unless
   explicitly escalated. **WHY**: codegen is a one-way door + cannot synthesize
   cascade/derived columns.

---

## 3. GO / NO-GO Verdict

**VERDICT: GO** — proceed to `myron /frame` for the gfr-dynvocab envelope.

**Realization rung reached (named, not rounded up):**
**FEASIBILITY-PROVEN + META-OPTIMAL-PARADIGM-SELECTED** at evidence grade
**MODERATE**. On the G-RUNG ladder (authored < emitting < alerting < proven <
merged < live < protecting-prod), this inquisition reaches **proven** (feasibility)
+ **paradigm-recommended**. It explicitly does NOT reach merged/live — those are
10x-dev + MINE.

**Conditions on the GO (this is a GO with conditions, not unconditional):**

1. **GAP-1 (live-Asana fetch) is the FIRST build-phase probe.** It is the single
   HIGH-severity platform UV-P. If it refutes HYP-1, the frame must pivot to the
   frame-based fallback (~2x effort). GO is conditional on this probe running
   before P1 tail build commits.
2. **GAP-4, GAP-5 (HIGH severity) close in Phase F-A before any scaling work** —
   both are cheap, future-independent, and GAP-5 is a LIVE governed-strict
   violation today (`date` cf resolves None).
3. **The MODERATE -> STRONG paradigm-LOCK upgrade requires the rite-disjoint
   corroboration AT THIS TRANSFER SEAM — named, never self-granted: the
   `tech-transfer -> review-rite external critic`** (rite-disjoint from the rnd
   author), per the same R1 binding the parent GFR telos uses
   (`.know/telos/gfr.md` `rite_disjoint_attester` = review-rite external critic).
   The specific claim requiring STRONG corroboration is the **moonshot Future-4
   coherence-layer dissent** (Option A breaks as a fleet doctrine). Until that
   critic concurs, the coherence-layer re-scope stays MODERATE and F-D stays a
   trigger-gated escalation, NOT a build.

**Adoption J-curve expectation (set for the consuming rite)** [PE:SRC-007 DORA
team 2024 | MODERATE]: the tail is strictly additive and flag-gateable, so the
J-curve is shallow — the dominant integration cost is GAP-1/GAP-2 (entry-seam
threading + live probe), estimated ~8-12 dev-days for the favored path (Tail
Option C + Dataframe Option A + provenance + 2-entity generality), MEDIUM
confidence. Phases P1-P4 are independently revertible with the 105-test gate as
the continuous rollback trigger.

**Why not NO-GO / CONDITIONAL-GO-blocking:** no gap is CRITICAL severity. The two
HIGH gaps (GAP-4, GAP-5) are cheap and future-independent. The free-tail premise
(GAP-1) has a clear fallback. The certified spine is untouched. Feasibility is
proven on the hard case + the real canary + >=2 EntityTypes. The verdict is an
honest GO with the three conditions above carried into the frame.

---

## 4. Frame-Requirements (what `myron /frame` must scope)

> Items below are the implementation work-units. The myron frame must scope BOTH
> layers (tail + dataframe coherence), carry the strictly-additive constraint,
> the asset_id proof-override, and generality across EntityTypes.

### items (HANDOFF schema — type: implementation, each carries design_references)

- **id: FRAME-001 — Dynamic tail resolver (the core paradigm)**
  - summary: Build the additive `is_identity=False` tail that reflects the entity's
    cf manifest off the already-hydrated entry task, heuristically typed from
    cf-type metadata, governed-strict.
  - priority: high
  - design_references:
    - `.ledge/spikes/gfr-dynvocab-prototype-findings.md` (HYP-1/HYP-2, hard case, generality)
    - `src/autom8_asana/dataframes/resolver/default.py:234-287` (reuse `_extract_raw_value`)
    - `src/autom8_asana/core/entity_registry.py:136` (`custom_field_resolver_class_path` hook)
    - `.ledge/spikes/gfr-dynvocab-integration.md` §"Minimal additive GFR-tail surface"
  - acceptance: resolves a requested field the entity carries to a correctly-typed
    value; absent field -> truthful `UnresolvedError(unknown-field)`; 105 tests green.
  - addresses: GAP-2, GAP-3, GAP-10, GAP-11; constraints 1-3.

- **id: FRAME-002 — asset_id proof-override (the worked example)**
  - summary: Per-field override registry keyed by **canonical field NAME**
    (`NameNormalizer.normalize(cf.name)`, matching the model `field_name`),
    **EntityType-scoped**; `asset_id` (text) -> whitespace-agnostic comma-split -> set.
    **[CORRECTED 2026-06-25 — NAME-keyed, NOT gid-keyed; cf gid is the runtime value
    handle only. See the brief's "Post-inquisition CORRECTION".]**
  - priority: high
  - design_references:
    - `.ledge/specs/gfr-dynvocab-alignment-brief.md` (PROOF OVERRIDE decision + §"Post-inquisition CORRECTION": keying axis = NAME)
    - `.ledge/spikes/gfr-dynvocab-prototype-findings.md` lines 88-116 (proven receipt — prototype name-keyed)
    - `src/autom8_asana/resolution/field_resolver.py:61` + `dataframes/resolver/default.py:92` (name-keyed grain)
    - `.ledge/spikes/gfr-dynvocab-moonshot.md` D4 (EntityType-scoped rationale)
  - acceptance: `asset_id` resolves as a set on the live canary; the registry is
    EntityType-scoped (expresses per-entity dtype divergence); a cf rename is caught
    by the coherence drift-gate (FRAME-005), not by gid-keying.
  - addresses: GAP-4.

- **id: FRAME-003 — opt-fields completeness (close the LIVE date gap)**
  - summary: Add `custom_fields.date_value` to `STANDARD_TASK_OPT_FIELDS`; add a
    fallthrough counter + `typing_origin: 'fallback'` tag.
  - priority: high
  - design_references:
    - `src/autom8_asana/models/business/fields.py:232-251`
    - `.ledge/spikes/gfr-dynvocab-moonshot.md` D2/D5 (live date hole; S5a observability)
  - acceptance: a live `date` cf resolves to its value (not `None`); fallthrough
    count is observable.
  - addresses: GAP-5, GAP-8.

- **id: FRAME-004 — typing-origin provenance**
  - summary: Additive `FieldWithProvenance` field — `typing_origin` alongside
    `{value,status,source,as_of}`.
  - priority: medium
  - design_references:
    - `.ledge/specs/gfr-dynvocab-alignment-brief.md` (Typing provenance decision)
    - `.ledge/spikes/gfr-dynvocab-prototype-findings.md` shortcut #5
  - acceptance: a caller can distinguish schema-validated from heuristically-coerced
    values; `extra="forbid"`-safe.
  - addresses: GAP-6.

- **id: FRAME-005 — dataframe-coherence drift gate (Option A, per-repo)**
  - summary: Extend import-time `_validate_extractor_coverage` (`registry.py:168`)
    using the `_pending_fields`/`Fields` auto-gen registry (ADR-0082); warn-first,
    then promote. Honors ADR-S4-001.
  - priority: medium
  - design_references:
    - `.ledge/spikes/gfr-dynvocab-integration.md` §"Dataframe-coherence mechanism options" (Option A)
    - `src/autom8_asana/core/entity_registry.py:430-432` (ADR-S4-001 boundary)
  - acceptance: model<->schema drift fails the import-time gate (warn then error);
    Option B (codegen) is NOT built — it is escalated.
  - addresses: GAP-9; constraint 4.
  - notes: **The Future-4 fleet-registry re-scope (F-D) is OUT of this frame's
    build scope** — it is a DEFER/ESCALATE item (see register). Frame Option A as
    the baseline only.

- **id: FRAME-006 — generality across EntityTypes**
  - summary: Prove the tail resolves generically across >=2 EntityTypes through the
    resolver hook (Offer + Business + ideally a third), with EntityType-scoped
    override context.
  - priority: medium
  - design_references:
    - `.ledge/spikes/gfr-dynvocab-prototype-findings.md` lines 120-144 (>=2 EntityTypes proven)
    - `.ledge/spikes/gfr-dynvocab-moonshot.md` Future-2 ("without code change" is half-true — registration IS code)
  - acceptance: a newly-registered EntityType's carried field resolves via the hook
    with only an `EntityConfig` + override-context addition (the honest claim, not
    "zero code change").
  - addresses: GAP-7 mitigation by gid-keying; Future-2 honesty.

### 4.1 Open forks — RESOLVED by the inquisition vs STILL-OPEN

**RESOLVED (the frame can treat these as decided):**

| Brief fork | Resolution | Evidence |
|---|---|---|
| **#2 Entry-fetch completeness** | **RESOLVED — free tail.** The certified entry fetch already pulls all cf with values. | HYP-1 structural receipt (`hydration.py:69` + `fields.py:232-251`); 1 residual UV-P (GAP-1). |
| **#1 Tail source** (task-based vs frame-based) | **RESOLVED — task-based.** Off the hydrated entry task; ~0 marginal cost; cache-only contract preserved. | HYP-2 benchmark (5.5µs/20 fields); integration map §1.4. Frame-based is the FALLBACK only if GAP-1 refutes HYP-1. |
| **#4 Manifest source** (task cf keys vs registry) | **RESOLVED — task cf keys** (bounded per-entity by the task's own manifest; the bound that prevents Elastic explosion). | Recon (d-bounded); prototype `build_manifest` off task. |
| **#3 Dataframe-coherence mechanism** (PARTIAL) | **RESOLVED for the per-repo baseline: Option A drift gate (gid-keyed), NOT codegen.** | Integration map Approach 1; moonshot Option A as horizon-start. |

**STILL-OPEN (the frame must NOT pre-decide these — carry as decision points /
DEFER):**

| Open question | Why still open | Disposition |
|---|---|---|
| **GAP-1 live-Asana UV-P** | Asana platform semantic ("bare custom_fields returns all workspace cfs") is not statically confirmable | FIRST build-phase probe; frame as P1 entry-criterion. |
| **Fork #3 at FLEET scale** (Option A vs fleet contract registry) | moonshot Future-4 scoped dissent: Option A breaks as a 5-service doctrine | DEFER -> ESCALATE on trigger S4a/S4c. Needs the rite-disjoint review-rite critic for STRONG. |
| **Fetch-all vs projected opt-fields** | Free-tail vs payload-width tension only matters at 100x fields | DEFER -> decision point at trigger S1c. |
| **Region/residency spine guard** | Residency is a SPINE guard, not a tail concern; OUT of dynvocab scope | ROUTE-BACK to spine owner if S3a fires. |
| **Schema codegen (Option B / ADR-S4-001 reversal)** | One-way door; reverses an ADR; cannot synthesize derived columns | ESCALATE to user/moonshot-architect only; NOT a default. |

---

## 5. DEFER / Watch Register (per defer-watch-manifest discipline)

> These are deliberately NOT built in the frame's first sprint. Each carries a
> watch-trigger, escalation-path, and owner-rite. Surfacing them as visible-deferred
> prevents DEFER -> SHIP scope collapse.

| DEFER id | Item | Watch-trigger (observable) | Escalation path | Owner-rite |
|----------|------|----------------------------|-----------------|------------|
| **DEFER-1** | Fleet cf-`gid` contract registry (F-D) — the moonshot Future-4 re-scope | **S4a**: a 2nd autom8y service hits the drift class; OR **S4c**: a coherence-doctrine RFC | ESCALATE to user/leadership BEFORE the 2nd service binds (one-way door once 2+ bind) | strategy / leadership |
| **DEFER-2** | Name-collision policy (GAP-7, moonshot D3) | **S1a**: entry payload > ~500 cf; OR **S1b**: manifest-build p99 > 5ms | 10x-dev F-B phase; gid-keying (FRAME-002) mitigates until then | 10x-dev |
| **DEFER-3** | Fetch-all vs projected opt-fields | **S1c**: entry-fetch payload dominates latency | 10x-dev decision point; default free-tail | 10x-dev |
| **DEFER-4** | Region-scoped spine read-gate | **S3a**: signed EU tenant or compliance residency requirement | ROUTE-BACK to spine/migration owner (NOT dynvocab scope) | spine owner |
| **DEFER-5** | Schema codegen (Option B) | ADR-S4-001 reversal proposed | ESCALATE to user/moonshot-architect (one-way door) | user / moonshot-architect |
| **DEFER-6** | **Telos declaration `.know/telos/gfr-dynvocab.md`** — does NOT exist yet | myron `/frame gfr-dynvocab` invocation (Gate-A fires) | **BLOCKING at frame inception** — see §6 | user (sovereign) + myron |

---

## 6. Telos-Integrity Gate Status (telos-integrity-ref)

**Gate-C (handoff-gate) check on THIS HANDOFF:** Gate-C's trigger condition is "the
originating initiative has `.know/telos/{slug}.md`." A check confirms
`.know/telos/gfr-dynvocab.md` **does NOT exist** (only the parent `.know/telos/gfr.md`
exists, for the sibling `gfr` initiative). **Therefore Gate-C does not fire on this
HANDOFF** — there is no per-initiative telos to attest claims against. Every
"PROVEN/CONFIRMED/RESOLVED/settled" claim in this body is nonetheless backed by an
artifact path or `file:line` anchor or pasted prototype run per the receipt-grammar
discipline, OR explicitly tagged DEFER (DEFER-1 through DEFER-6).

**Gate-A (inception-gate) WILL fire on the consumer side.** When myron invokes
`/frame gfr-dynvocab`, the inception gate REQUIRES `.know/telos/gfr-dynvocab.md` to
exist with non-stub required fields. It does NOT exist. This is **DEFER-6 / a
BLOCKING inception condition for the consumer**:

> **INCEPTION-GAP SURFACED TO MYRON**: `gfr-dynvocab` has no per-initiative telos.
> The brief carries a DRAFT realization predicate
> (`.ledge/specs/gfr-dynvocab-alignment-brief.md` §"Realization predicate") but it
> is NOT yet a ratified `.know/telos/gfr-dynvocab.md`. Per telos-integrity-ref §3
> Gate-A, the user must author the per-item telos declaration (the realization
> predicate is the seed) BEFORE `/frame` completes — and the dispatching rite MUST
> NOT author the user-sovereign fields on the user's behalf. The
> `rite_disjoint_attester` should mirror the parent's binding: the **review-rite
> external critic**.

---

## 7. Operator Rite-Switch (SURFACE ONLY — do NOT execute)

To move from rnd to the implementation rite, the operator runs:

```
ari sync --rite=10x-dev
```

This is the operator's lever (MINE). This handoff does not switch the rite, build,
merge, or lock the paradigm.

---

## 8. Attestation Table (absolute paths, verified this pass)

| Artifact | Absolute path | Verification |
|----------|---------------|--------------|
| This HANDOFF | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/handoffs/gfr-dynvocab-rnd-to-10x-handoff.md` | authored this pass |
| Locked inception brief | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/gfr-dynvocab-alignment-brief.md` | READ this pass — status: accepted, 12 decisions |
| Recon (paradigm rec) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/gfr-dynvocab-recon.md` | carried via station summary (recon) |
| Integration map | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/gfr-dynvocab-integration.md` | carried via station summary (integration) |
| Prototype findings (feasibility) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/gfr-dynvocab-prototype-findings.md` | READ this pass — PROVEN, receipts pasted |
| Moonshot (5-future + dissent) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/gfr-dynvocab-moonshot.md` | READ this pass — CONFIRMED-WITH-SCOPED-DISSENT |
| Parent GFR telos (R1 attester pattern) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/telos/gfr.md` | READ this pass — review-rite external critic binding |
| Cross-rite HANDOFF schema | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.claude/skills/cross-rite-handoff/schema.md` | READ this pass — schema v1.0 conformance |
| Certified base (DO NOT TOUCH) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr` branch `feat/gfr-engine` tip `2092f771` | FROZEN CLEAN; 105 tests GREEN; prototype never committed here |

---

*tech-transfer | rnd rite | transfer seam | self-grade [STRUCTURAL | MODERATE]
(rnd-dk MODERATE ceiling + self-ref cap). STRONG paradigm-LOCK on the coherence-layer
dissent requires the rite-disjoint review-rite external critic — named, never
self-granted. This rite does NOT build/merge/lock the paradigm — user-sovereign
(10x-dev + MINE).*
