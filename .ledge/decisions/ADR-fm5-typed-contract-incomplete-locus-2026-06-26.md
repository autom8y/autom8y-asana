---
type: decision
subtype: adr
status: accepted
title: "ADR — FM-5 typed contract-incomplete: LOCUS (FORK-A=O3 two-layer), One-Gate graft, Door-C rebind-not-widen, RULING-1 re-confirm"
date: 2026-06-26
initiative: receiver-contract-realization
sprint: S3 (WS-FM5 design-lock; 10x-dev architect)
code_truth_anchor: origin/main b9648de494115063161cd1e019ec1a931c05d725  # #114 merge — FieldContract SSOT on main
self_assessment_ceiling: MODERATE  # STRONG is the S4 rite-disjoint review critic's
supersedes: none
inputs:
  - .ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md      # two-layer shape (ratified)
  - .ledge/decisions/OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md    # RULING 1/2/3
  - .ledge/decisions/ORDERING-PIN-114-before-fm5-design-lock-2026-06-11.md     # E1 (satisfied)
  - .know/telos/fm5-column-fidelity.md                                         # Gate-A predicate; RULING-1 re-confirm gate
  - .sos/wip/frames/receiver-contract-realization.shape.md                     # S2-S5, FORK-A, FORK-B/W1
companion_tdd: .ledge/specs/TDD-fm5-column-fidelity-contract-2026-06-26.md
---

# ADR — FM-5 typed contract-incomplete signal: locus, gate-graft, and the widen-vs-rebind ruling

## Grandeur anchor
receiver-contract-realization makes the monolith + fleet CONSUME the GFR-realized honest contract so
the live **$8,775 BusinessOffers fossil dies at root** and the operator denylist bridge becomes
RETIREABLE. This ADR locks **ARM-B**: a requested-but-absent REQUIRED column on `/v1/query` returns a
**typed contract-incomplete signal** — never a silent drop, a daily KeyError, or a $0/7-row fossil.
Proven downstream (S9) by a two-sided discriminating canary run by a rite-disjoint review critic.
`built` (S3) is NOT `verified_realized` (S9/S10).

## Status
Accepted at design-lock (S3 entry). Operator confirms the two telos-integrity Gate-A items in §Consequences
before build dispatch. Self-grade caps MODERATE (G-CRITIC); the authoritative correctness verdict is the
S4 review critic's.

## Context

`/v1/query/{entity_type}/rows` is **column-blind by documented shortcut, not defect**. The S-07 minimal
schema is inscribed at `src/autom8_asana/core/entity_registry.py:881` ("T1.3 — Shortcut S-07 invoked:
minimal schema (3 columns beyond base)") with PG-02 deferral markers at `:901` and `:939` (re-verified at
b9648de4 — line anchors held from fa265ce1). The deferred bill arrives on fleet re-enable: a consumer
indexing a never-selected column gets a silent null or a prod KeyError instead of a typed refusal.

**Premise (S2, EVIDENCED not assumed — see TDD §Premise Receipt):** the BusinessOffers consumer
(`business_offers.active_offers_frame`, monolith `main.py:203`) queries `entity_type=project`
(SPEC §Layer-1 manifest seed) and indexes `offer_id`. The served column set for `entity_type=project`
is `PROJECT_SCHEMA` = `BASE_COLUMNS` (13, `base.py:12-104`) + `{status, office_phone, vertical}`
(`project.py:18-44`) = 16 known columns; the registry `default_projection` is those same 16
(`entity_registry.py:905-922`). **`offer_id` is NOT in that set** — it is defined ONLY in
`offer.py:42` and `asset_edit.py:127` (grep across `dataframes/schemas/`). Therefore any frame the
`SchemaExtractor` builds for `entity_type=project` **cannot** contain `offer_id`. The premise the design
rests on is CONFIRMED (offer_id is genuinely absent on the project arm); the design is NOT built on a
false premise. No HALT.

#114 (FieldContract SSOT `field_contract_maps.py`) is MERGED on main (E1 satisfied;
`git cat-file -e origin/main:src/autom8_asana/dataframes/contracts/field_contract_maps.py` → PRESENT).
FM-5 is the Phase-3 consumer-manifest work built INTO that SSOT (the file's own SCOPE NOTE defers
"the full FieldContract dataclass/registry, schema-FROM-model derivation, and the in-repo generator"
to Phase-3). The SSOT is the SOLE propagation point (G-PROPAGATE) — no per-consumer orphan contract.

## Decision

### D1 — FORK-A locus = **O3 (two-layer)**
The consumer-required-column declaration lives in **two carriers, one truth**:
- **Layer-1 (static seed):** a consumer-owned JSON manifest authored in the **monolith** repo,
  **vendored** into `src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json`
  with a CI freshness guard (the `check_namespaces_gen.sh` pattern, reversed direction). It seeds the
  canary + CI parity check.
- **Layer-2 (runtime authority):** `RowsRequest` grows an optional `required_columns: list[str] | None`.
  The producer's per-request answer is authoritative and drift-free.
- **Derivation (G-PROPAGATE):** the FieldContract SSOT (`field_contract_maps.py`) ingests the vendored
  manifest and derives `required_columns_for(entity_type)` = union over declaring consumers. This single
  function feeds (i) EntityDescriptor/schema-selection validation, (ii) the coherence canary column
  assertion, (iii) CI parity (a declared column unservable for its shape = build-time RED, not a prod
  KeyError).

### D2 — One-Gate graft (GLINT L1-2), NOT a sibling signal path
The column-completeness check is grafted onto the **existing** `honest_contract_complete` derivation at
`src/autom8_asana/query/engine.py:247-255` (the "12.5 Derive honest_contract_complete" block; canonical
method `_derive_honest_contract_complete` at `:527`). Concretely:

```
honest_contract_complete = section_honest_complete AND column_contract_complete
```

where `column_contract_complete` is True iff every column in the effective required set
(`request.required_columns` ∪ the manifest-derived set for this `entity_type`) is present in the served
frame's `available` columns (computed at `engine.py:235`). No new derivation path; the check reuses the
`available` set already in scope.

### D3 — Typed detail = a structured `contract_incomplete` block on `RowsMeta`
`honest_contract_complete=False` is the GATE; a new typed `RowsMeta.contract_incomplete` block carries the
DISCRIMINATING detail (which columns, and why: `not_in_schema` vs `present_but_unpopulated`, plus the
declared `population_expectation`). This satisfies BOTH "One-Gate" (single boolean gate) and "typed"
(structured, dispatchable detail). The response stays **200** — additive, two-way door. The producer NEVER
hard-fails a live consumer (no grafted unconditional refusal → zero C3 prod-breaker risk); the opted-in
consumer reads the typed block and applies its OWN refusal (the monolith's `.get()`-refusal stands, per
OPERATOR-RULING §Ratified).

### D4 — Door-C (widen-vs-rebind) ruling
- **offer_id @ entity_type=project → REBIND, do NOT widen.** `offer_id` is an offer-domain column with no
  project-entity extractor source; widening `PROJECT_SCHEMA` to add it would be a semantic violation
  (offer-domain column on the project leaf) and is unservable from project task data. The cure is the
  **SEAM-2 rebind** of `business_offers` to `entity_type=offer` (`offer.py:42` natively serves `offer_id`).
  **Consequence: FM-5 performs ZERO receiver schema widening** — it stays schema-selection-NEUTRAL (no
  RULING-3 soak-clock reset for FM-5 itself). FM-5 serves the TYPED REFUSAL on the project arm (ARM-B);
  SEAM-2 serves real economics via rebind to the offer entity (ARM-A). This satisfies shape FORK-B/W1
  ("fold receiver projection widening into FM-5") **vacuously** — there is no receiver widening to fold,
  because the offer entity already serves the column.
- **project_gid @ entity_type=section → DEFER the widen-vs-rebind to SEAM-2/FORK-B.** Per SPEC
  §Out-of-scope and telos DEFER table, the section-consumer cure intersects SEAM-2 (monolith-side) and is
  not the $8,775 fossil. FM-5 serves the TYPED REFUSAL for `project_gid`-on-section as the contract's
  second declared instance. IF SEAM-2 rules a receiver widen, it lands in a receiver PR per W1.

### D5 — RULING-1 RE-CONFIRM (operator-held) against the actual declared union
The declared union at this design-lock is **{`offer_id` (entity_type=project), `project_gid`
(entity_type=section)}** — TWO columns. The column-fidelity check activates ONLY for declared required
columns; it is a **contract-driven subset, NOT eager 30-column PG-02 parity** (RULING-1, re-confirmed).
A consumer that declares nothing keeps today's behavior.

## Alternatives Considered

### Option A: O1 — consumer-side declare+check (each consumer re-implements the column check)
- Pros: no producer change; consumer fully owns its requirement.
- Cons: **REJECT.** Replicates the servability check, which only the producer (owner of schema +
  projection + the loaded frame) can answer authoritatively — the consumer cannot know whether `offer_id`
  is servable for `entity_type=project` without re-deriving `PROJECT_SCHEMA`. Violates C2
  (derive/delegate-never-replicate) and grows a second contract engine. Drift surface: every consumer's
  private copy of "what's servable" drifts from the real schema independently.

### Option B: O2 — `/v1/query` endpoint declare+enforce (runtime wire field only, no static seed)
- Pros: centralized enforcement at the one owner; drift-free at runtime; minimal surface (just the wire
  field + meta).
- Cons: with NO static seed there is nothing for the **canary** and **CI parity** to assert against at
  build time — a declared-but-unservable column only surfaces at runtime, not as a build-time RED. Loses
  SPEC §Layer-1 Derivation (iii). The expressiveness (per-consumer `population_expectation`, code_anchor)
  has no home.

### Option C: O3 — two-layer (vendored manifest seeds; wire field enforces) — **SELECTED**
- Pros: consumer declares (O1 expressiveness) WITHOUT replicating the CHECK (respects C2); endpoint
  enforces (O2 centralization); the manifest seeds canary + CI (build-time RED); the wire field is the
  runtime authority (drift-free per request); rides the #114 FieldContract SSOT (G-PROPAGATE). Matches the
  ratified SPEC and OPERATOR-RULING §Cross-repo reciprocity.
- Cons: two carriers ⇒ a manifest↔source drift surface — bounded by the CI freshness guard (drift is
  CI-LOUD, never silent). One additional vendored artifact to maintain.

## Rationale
O3 is the only option that makes the servability answer come from the **one owner that can answer it
authoritatively** (the producer, via the SSOT-derived served set) while letting the **consumer own the
declaration** of need. The real-frame evidence sharpens the rejection of O1: because `offer_id` is
absent from `PROJECT_SCHEMA`, the check is fundamentally a producer-schema question — a consumer-side
check (O1) would have to vendor the producer's schema, which IS O3's manifest pointed the wrong way.
O2-pure forfeits the build-time RED that the discriminating canary and CI parity need. The One-Gate graft
(D2) is mandated by GLINT L1-2 and is also the lowest-surface choice: it reuses the `available` set and the
single existing meta gate, so honest_empty (`engine.py:266`) and the S7 GetDfFallback disaggregation
compose correctly (a column-incomplete frame is correctly NOT attested honest_empty). The 200+meta shape
(D3) is the additive, two-way-door, C3-prod-breaker-free realization of "typed contract-incomplete."
Rebind-not-widen (D4) keeps FM-5 schema-selection-neutral, which is a STRONGER outcome than FORK-B/W1
anticipated — it removes FM-5 from the soak-clock-reset path entirely.

## Consequences

### Positive
- The $8,775 fossil's silent-null/KeyError mode is replaced by a loud, typed, dispatchable signal at the
  one owner. ARM-B is realizable without ANY receiver schema change.
- FM-5 is schema-selection-NEUTRAL → no RULING-3 soak-clock reset for the FM-5 deploy itself.
- Strictly-additive: `required_columns=None` ⇒ today's behavior byte-for-byte (two-way door). The 105 GFR
  spine, `assert_rows_tenant_identity` RED-on-bypass, and `_resolve_identity_plan_async` are untouched.
- ARM-A (real economics, SEAM-2) uses `entity_type=offer` (native `offer_id`); the canary GREEN side needs
  no fixture widening.

### Negative
- One vendored artifact (`consumer_column_requirements.vendored.json`) + a CI freshness guard to maintain.
  Mitigation: the guard makes drift CI-loud; the artifact is small and consumer-owned upstream.
- `honest_contract_complete` semantics broaden from "sections complete" to "sections complete AND declared
  columns served." Mitigation: only fires when a consumer opts in via `required_columns`/manifest; the
  typed block disambiguates the cause for any reader.

### Neutral / watch-register (G-DEFER — do NOT build here)
- **Operator-confirm #1 (telos-integrity Gate A):** `verification_deadline` recalculates to design-lock+21d
  = **2026-07-17** (telos rule; 2026-07-31 is the outer bound). Confirm before build dispatch.
- **Operator-confirm #2:** `rite_disjoint_attester` binding — telos says `eunomia`, shape says `review-rite`.
  Surfaced for Potnia; NOT resolved here (cross-rite coordination, outside design-lock exousia).
- **DEFER-1 (OOS-1):** fleet cf-contract registry — escalate-only one-way door; NOT pulled in.
- **OOS-2:** denylist POPULATION (operator bridge) — this crusade RETIRES, never sets.
- **SEAM-2 (S6-S8):** the offer_id rebind + the project_gid widen-vs-rebind ruling — watch-registered, not built.
- **Security gate:** NOT triggered. The change is additive metadata on an existing **S2S-only**
  (`require_service_claims`) endpoint: no new endpoint, no auth/crypto/PII/session change, no new data
  disclosure (the typed block echoes only the requester's OWN declared columns + schema-public names already
  exposed via `UnknownFieldError.available`). Documented decline within architect exousia (INVOKE point).

## Anti-pattern self-audit (option-enumeration-discipline)
- Three genuinely-distinct architectures enumerated (O1 consumer-locus / O2 endpoint-only / O3 two-layer) —
  they differ on WHERE the authoritative servability answer is computed, not on one cosmetic axis.
- One-way-door audit: D3 keeps the response 200/additive (two-way door); D4 keeps FM-5 schema-neutral
  (no irreversible schema-selection deploy). No one-way door is opened by FM-5; the genuine one-way door
  (codegen-from-model, ADR-S4-001) is explicitly FORBIDDEN (drift gate stays WARN-first).
