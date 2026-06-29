---
type: decision
artifact_class: adr
id: ADR-gfr-dynvocab-drift-gate
initiative: gfr-dynvocab
sprint: SPRINT-4 (drift gate + generality)
title: "Model<->schema drift gate — per-repo, warn-first, import-time; PT-04 fork (per-repo gate vs DEFER-1 fleet cf-contract registry)"
status: proposed
created: 2026-06-25
author: architect (10x-dev)
rite: 10x-dev
code_truth_anchor: "feat/gfr-engine 2092f7717ff6ba866c78df039627f4599cc32796 (worktree /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-gfr) + UNCOMMITTED sprint-1+2+3"
telos_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/telos/gfr-dynvocab.md
tail_scope_adr_ref: .ledge/decisions/ADR-gfr-dynvocab-tail-scope.md
extension_point: "src/autom8_asana/dataframes/models/registry.py:168 (_validate_extractor_coverage)"
honored_decision: "ADR-S4-001 (entity_registry.py:430-432) — keep schemas as separate files; this is a GATE that DETECTS divergence, NOT codegen"
production_driver: "autom8 legacy monolith KeyError 'asset_id' at apis/asana_api/objects/project/models/paid_content/main.py:70 — second consumer of the drift class (S4a trigger FIRED)"
evidence_grade: "[STRUCTURAL | MODERATE]"
escalation_flag: "S4a FIRED — fleet cf-contract registry (DEFER-1) reactivation trigger met; ESCALATE-ONLY to operator/strategy. Per-repo gate (this ADR) is IN-SCOPE."
---

# ADR — gfr-dynvocab model<->schema drift gate (SPRINT-4)

## Status

PROPOSED. Recognized-lifecycle ADR for the SPRINT-4 drift gate (FRAME-005) and
the generality claim (FRAME-006). Design-only; no production code is written by
this ADR. The implementing edit is specified at file:line for the SPRINT-4
principal-engineer.

## Context — the drift this gate prevents (verified by direct inspection, SVR)

The founding smell of the whole initiative is a **model<->schema divergence**:
a field exists on an entity's task *model* but is absent from that entity's
DataFrame *schema*, so the curated vocabulary silently under-represents what the
entity actually carries. Direct inspection confirms the canonical instance:

- **Model side** (`models/business/offer.py:144`): the Offer model declares
  `asset_id = TextField(field_name="Asset ID")`. Sibling cf descriptors at
  `:141-172` (`ad_id`, `campaign_id`, `form_id`, ...) carry the same shape.
- **Schema side** (`dataframes/schemas/offer.py`): the Offer schema declares cf
  columns `office`/`office_phone`/`vertical`/`specialty`/`offer_id`/`platforms`/
  `language`/`name`/`cost`/`mrr` (via `source="cf:..."` / `source="cascade:..."`).
  There is **no `asset_id` column** and **no `source="cf:Asset ID"`**.
- **Result**: "Asset ID" is present 15/15 on real Offer task manifests (PT-01
  live probe, carried in the tail-scope ADR), the *model* knows the field, but
  the *schema/vocabulary* does not — the gap that the dynamic tail (sprint-2/3)
  resolves at runtime but that nothing **detects** at build/import time. This is
  exactly the `verified_realized` COHERENCE predicate in the telos
  (`gfr-dynvocab.md:47`): *"a model<->schema drift gate FAILS (RED) when an
  entity's task-model field set diverges from its schema/vocabulary coverage
  without an explicit exclusion."*

### The NAME-keyed comparison (what the gate compares, mechanically)

The model field set is materialized into `cls.Fields` during
`__init_subclass__` from the `_pending_fields` registry
(`models/business/descriptors.py:49`; assembled at
`models/business/base.py:284-321`). Each entry is `{constant_name: field_name}`
where `field_name` is the Asana custom-field display name (e.g. `"Asset ID"`)
— this is the ADR-0082 Fields auto-gen registry the FRAME-005 directive names.

The schema declares each cf-backed column with `name="asset_id"` and
`source="cf:Asset ID"` (or `source="cascade:Office Phone"`).

The gate is **NAME-keyed**: it compares the model's `field_name` set (the cf
display names the model claims) against the schema's covered cf-names (the
`cf:`/`cascade:` source suffixes the schema declares, plus any `name=` columns).
A model `field_name` with no corresponding schema coverage is **drift**. This
mirrors the entire tail resolution path, which is itself NAME-keyed
(tail-scope ADR §"What this does NOT change": "the tail's NAME-keyed manifest").

### The extension point (verified)

`src/autom8_asana/dataframes/models/registry.py:168` —
`SchemaRegistry._validate_extractor_coverage()` is **already** an import-time,
**warn-first, non-fatal** coverage validator. It is invoked from
`_ensure_initialized()` (`:157`) inside a `try/except Exception` that, per the
in-code R1.1 invariant, logs `"schema_validation_failed"` and continues —
**"Validation MUST NOT crash startup"** (`registry.py:158-166`). The existing
method warns on **schema→extractor** coverage gaps via a structured
`get_logger(__name__).warning("schema_using_generic_extractor", extra={...})`
(`:195-207`). The drift gate is a **sibling validator** added at this same
extension point: where `_validate_extractor_coverage` warns on schema→extractor
gaps, the new `_validate_model_schema_coverage` warns on **model→schema** gaps.
It inherits the existing non-fatal wrapper verbatim — no new startup-safety
machinery is invented.

The WARN-vs-ERROR convention this gate adopts is the **established** one at
`core/entity_registry.py:1026-1032` (`_validate_registry_integrity`):
check **6d "schema without extractor"** is a **WARNING** (partial wiring);
check **6f "extractor without schema"** is an **ERROR** (nonsensical). A model
field with no schema coverage is the **partial-wiring class (WARN)** — the model
legitimately declares more than the curated schema chose to materialize — not the
nonsensical class. This is why warn-first is the correct default and not a
concession.

## CRITICAL CONSTRAINT — warn-first / non-fatal (how the 184 floor stays GREEN)

There is **known, real, pre-existing drift** in production: `asset_id` on the
Offer model, absent from the Offer schema (the canonical smell above), plus the
sibling `ad_id`/`campaign_id`/`form_id` family. If the gate **raised** at real
import time, it would crash `SchemaRegistry._ensure_initialized()` on every
process that touches a DataFrame — breaking prod startup AND the 184-test floor
(`tests/unit/resolution/gfr/`, `tests/integration/test_gfr_tenant_roundtrip.py`),
since those imports transitively initialize the registry.

Therefore the gate **MUST NOT raise on real import**. The design guarantees this
two ways:

1. **Behavioral**: on divergence the gate emits a **structured observable
   warn-level signal** and returns normally. It never raises into
   `_ensure_initialized`. (And even if it had a bug that raised, the existing
   `try/except` wrapper at `registry.py:158-166` swallows it to a warning — a
   second, defense-in-depth layer the gate inherits for free.)
2. **Test-provable RED**: RED-on-divergence is proven not by a real-import crash
   but by a **deliberately-divergent fixture** in the test suite (see
   §"RED-on-divergence is provable"). A broken entity makes the gate's
   **detector** return a non-empty drift set, which the test **asserts** on. The
   detector (pure function: "given a model field-name set and a schema cf-name
   set, return the uncovered model fields") is separated from the **emitter**
   (the warn-logging side effect). The test exercises the detector directly and
   asserts it fires; production exercises the emitter and observes a metric — and
   neither path raises.

This is the discriminating-canary discipline applied at the model<->schema
altitude: a signal that PROVES the integrated path is functional (the detector
catches a real divergence) rather than merely alive (the gate ran without error).

## Observable signal shape (warn-first emission)

On divergence the gate emits one structured warning per drifted entity:

```
get_logger(__name__).warning(
    "model_schema_drift_detected",
    extra={
        "entity": <entity name, e.g. "offer">,
        "entity_type": <EntityType name or None>,
        "drifted_fields": <sorted tuple of model field_names absent from schema,
                           e.g. ("Active Ads URL", "Ad ID", "Asset ID", ...)>,
        "drift_count": <int>,
        "schema_name": <schema.name>,
        "has_explicit_exclusion": <bool — see exclusion registry below>,
        "note": "model declares cf field(s) with no schema/vocabulary coverage; "
                "the dynvocab tail resolves these at runtime but the curated "
                "schema under-represents the entity. Add a schema column or an "
                "explicit drift exclusion. See ADR-gfr-dynvocab-drift-gate.",
    },
)
```

Paired deploy-gate metric (mirrors the existing `ColumnContractFailure`
convention at `autom8/.../satellite/getdf_signals.py:284`):

```
metrics={"ModelSchemaDrift": float(drift_count)}   # 0.0 == coherent; >0 == drift
```

This metric is the **observable, alarmable** surface. Unlike the legacy
`contract_held` boolean — which is computed only over `_CONTRACT_COLUMNS` and is
**structurally incapable** of seeing `asset_id` drift (the false-green canary, see
§Production-driver) — `ModelSchemaDrift` is computed over the model's
**`cls.Fields`-declared cf field set** (the ADR-0082 `_pending_fields`
materialization). It is therefore false-green-proof for any field the model
declares *through* `cls.Fields`. A model whose cf fields cannot be extracted is
**not silently passed as coherent**: the gate's `model_fields_are_extractable`
guard — which keys on the **non-emptiness of `model_field_names`** — emits a
DISTINCT `model_schema_coverage_unanalyzable` signal so COHERENT (analyzed, no
drift) and UNANALYZABLE (could-not-extract) are never conflated into a silent
`ModelSchemaDrift=0.0`. See §"PT-04 false-green remediation" for the exact
end-state (coherent ⟺ ≥1 field name actually extracted) and §"Unpaired
single-path observability" for the sibling single-path coverage-gap signal.

**Explicit-exclusion registry**: the telos predicate says drift fails *"without
an explicit exclusion."* A small per-entity allowlist (e.g.
`DRIFT_EXCLUSIONS: dict[str, frozenset[str]]` keyed by entity name → set of
model `field_name`s intentionally not in the schema) lets a maintainer mark a
known, accepted gap. An excluded field emits at **debug** (still observable) and
does **not** count toward `ModelSchemaDrift`. This is the named-deferral surface
that converts a silent gap into a visible, owned decision — the same discipline
the tail-scope ADR applied to silent drops.

## PT-04 false-green remediation (TERMINATING) + unpaired single-path observability

The gate has **no silent false-green path**. This section is the accurate
end-state after the TERMINATING remediation closed the residual false-green an
earlier partial fix left open. It is stated precisely — neither overstated nor
understated.

### PT-04 false-green remediation

The extractability decision is keyed on **`model_field_names(model_class)`
NON-EMPTINESS**, via `model_fields_are_extractable`. It is **NOT** keyed on the
presence of a `cls.Fields` class. The earlier predicate
(`getattr(model_class, "Fields", None) is not None`) tested Fields-class
*presence*, which let an **empty** / **all-private** / **inherited-empty**
`Fields` class (`Fields` not None, yet `model_field_names() == frozenset()`)
report extractable=True. The validator then compared the schema's cf coverage
against an empty model set, found no drift, and reported the entity COHERENT with
a silent `ModelSchemaDrift=0.0` — a verdict reached **without a single field name
ever being extracted to compare**. That was the residual silent-false-green.

The exact, accurate end-state:

- **COHERENT ⟺ ≥1 field name was actually extracted** and every extracted name is
  schema-covered or exclusion-registered. Coherence is reachable *only* after a
  real comparison over a non-empty model field set.
- **UNANALYZABLE** is its strictly disjoint complement: when the schema declares
  cf/cascade column(s) (`schema_cf_cascade_count > 0`) but `model_field_names`
  extracts **zero** names — for *any* reason: no `Fields` class (a
  `HolderFactory` entity), an empty `Fields` class, an all-private/non-str
  `Fields` class, or an inherited-empty `Fields` class. Every such entity emits
  the DISTINCT `model_schema_coverage_unanalyzable` signal +
  `ModelSchemaCoverageUnanalyzable=1.0` metric, **never** a silent
  `ModelSchemaDrift=0.0`. The whole empty-extraction class is closed; no narrower
  false-green case survives.

This is **behavior-preserving for every live entity**: all five both-path models
with declared cf fields (asset_edit, business, contact, offer, unit) have a
non-empty `model_field_names` and stay analyzable; `asset_edit_holder` (no
`Fields`) stays UNANALYZABLE. No live entity changes classification — the residual
empty-but-present-`Fields` shape does not occur in this repo's live data; the fix
is a structural guarantee against its future introduction.

### Unpaired single-path observability

The validator's loop only analyzes descriptors carrying **both** a
`model_class_path` and a `schema_module_path` — a **single-path** descriptor has
no counterpart, so drift analysis is genuinely undefined and is **not attempted**.
But silently dropping a single-path descriptor with a bare `continue` reproduced
the same anti-silent-coverage-gap failure class one altitude up: a schema-only
descriptor declaring cf/cascade columns, or a model-only descriptor declaring ≥1
cf field, carries real coverage substance whose counterpart is missing.

A single-path descriptor whose present side carries cf/cascade **substance** now
emits a DISTINCT `model_schema_coverage_unpaired` warning +
`ModelSchemaCoverageUnpaired=1.0` metric, naming the descriptor, the present side,
and the missing side. It is **warn-first** (never raises; a resolution failure on
the present side is itself logged as `model_schema_coverage_unpaired_resolve_failed`
and swallowed so one broken descriptor cannot abort the rest) and it does **not**
attempt drift analysis. A single-path descriptor with **no** substance (e.g. a
`*_holder` model extracting zero field names) is correctly silent — there is
nothing to surface. At this repo's import time the signal fires for the 14
substantive single-path descriptors (`process`, `location`, `hours` model-only; 9
`process_*` stages, `project`, `section` schema-only).

### Three separately-alarmable states

COHERENT (drift compared, `ModelSchemaDrift`), UNANALYZABLE (paired but model
unextractable, `ModelSchemaCoverageUnanalyzable`), and UNPAIRED (single-path with
substance, `ModelSchemaCoverageUnpaired`) are three distinct, separately-alarmable
states. None collapses into a silent green.

## Decision — the gate design

Adopt **Option 1 (warn-only by default) + the promotion path of Option 2** as a
configurable, documented escalation — i.e. **warn-first with a documented
warn→error threshold promotion that ships DISABLED**. Concretely:

1. Add `SchemaRegistry._validate_model_schema_coverage()` adjacent to
   `_validate_extractor_coverage()` (`dataframes/models/registry.py:168`),
   invoked from the same `_ensure_initialized()` `try/except` block at `:157`.
2. Factor the comparison into a **pure detector**
   `detect_model_schema_drift(model_field_names, schema_cf_names, exclusions)
   -> frozenset[str]` (no I/O, no logging) so the test can assert RED directly.
3. The validator iterates entity descriptors that have BOTH a `model_class_path`
   and a `schema_module_path`, resolves the model's `Fields`/`_pending_fields`
   field-name set and the schema's cf-name set, calls the detector, and emits the
   warn-level signal + `ModelSchemaDrift` metric for any non-empty,
   non-excluded result.
4. **Default failure mode = WARN-ONLY.** A module-level threshold knob
   (`DRIFT_GATE_MODE: Literal["warn", "error"] = "warn"`, overridable by env e.g.
   `GFR_DRIFT_GATE_MODE`) exists but defaults to `"warn"` and is **not** set to
   `"error"` in any shipped config. In `"error"` mode the gate would raise — but
   that mode is gated behind a deliberate operator opt-in and behind the
   prerequisite that all current real drift is either schema-covered or
   exclusion-registered (see promotion path).

### Failure-mode options enumerated (>=3) — required before recommending

| # | Option | Behavior on divergence | 184 floor | Prod startup | Verdict |
|---|--------|------------------------|-----------|--------------|---------|
| **1** | **Warn-only** | Emit structured warn + `ModelSchemaDrift` metric; never raise | GREEN (no raise) | Safe (no raise) | **RECOMMENDED default** |
| **2** | **Warn-then-error-by-threshold** | Warn while `drift_count <= T` or `MODE=="warn"`; raise once a configured threshold/mode is crossed | GREEN *only while MODE=="warn"* | Safe *only while MODE=="warn"*; promotion is opt-in | **RECOMMENDED as the documented promotion path, shipped DISABLED** |
| **3** | **Hard-error** | Raise immediately on any divergence | **RED — breaks the floor and prod** (asset_id drift is real and present today) | **Crashes startup** | **REJECTED** |

**Why 3 is rejected**: the divergence it would fire on is **real and present
right now** (asset_id + the ad-id family). A hard-error gate is dead-on-arrival —
it cannot be merged without simultaneously closing every existing drift, which is
out of SPRINT-4 scope and would re-open the certified spine the telos forbids
(`gfr-dynvocab.md:76`). It also inverts the telos architecture: the dynamic tail
*exists precisely to resolve* drifted fields at runtime; hard-failing on their
presence at import time would contradict the initiative's own design.

**Why 1 is the default and 2 is the path**: warn-first makes the gate **shippable
today** (floor stays GREEN, prod stays up) while making the drift **observable
and alarmable** for the first time. Option 2 is the same code with the
mode/threshold knob; it gives operators a documented, opt-in route to RED once
the fleet is clean, without a second design cycle. Shipping 1 with 2's mechanism
present-but-disabled is strictly more reversible than shipping 1 alone and
re-architecting later.

### Warn -> error promotion path (operator discretion per shape §7 emergent)

Promotion from WARN to ERROR is a **per-repo, opt-in, monotone** path with a
named precondition:

1. **Observe** (warn-first, default): `ModelSchemaDrift` is alarmable in
   telemetry. Operators see which entities drift and by how much.
2. **Drain**: for each drifted field, either (a) add the schema column /
   `source="cf:..."` so it is covered, or (b) register it in `DRIFT_EXCLUSIONS`
   as an accepted gap. Each drain event reduces `ModelSchemaDrift` toward 0.
3. **Precondition for promotion**: `ModelSchemaDrift == 0` across all entities
   for a sustained window (operator-set; suggested >= one warm cycle / soak
   window, by analogy to the deploy-gate soak convention). I.e. every model field
   is either schema-covered or explicitly excluded.
4. **Promote**: set `GFR_DRIFT_GATE_MODE=error` (per-repo). Now a *new* divergence
   — a model field added without schema coverage or exclusion — turns the drift
   class into a **build break for new drift** while leaving accepted gaps excluded.

   **Caveat — wiring reachability (do not overstate this opt-in):** invoked from
   inside `_ensure_initialized`'s `try/except` (the floor-safety wrapper at
   `registry.py:158-166`), an `error`-mode raise is **swallowed to a warning** at
   the real `get_schema()` import path — so error mode does NOT break runtime
   startup as-wired. That is a deliberate floor-safety property, but it means the
   "build break" is **not** automatic at import. To realize the build-break
   semantics, the promotion step must ALSO invoke the validator/detector
   **directly** in a dedicated CI / deploy-gate check (outside the swallowing
   wrapper), or relocate the error-mode raise above it — itself a future change,
   NOT shipped in SPRINT-4. Threshold semantics: `error` raises iff
   `drift_count - len(matched_exclusions) > 0`.
5. **Reversibility**: promotion is a single env/config flip in one repo; demotion
   to `warn` restores warn-first. Two-way door. No schema migration, no API
   contract change.

The default ships at step 1. SPRINT-4 does **not** promote; promotion is operator
discretion once a repo's drift is drained.

## ADR-S4-001 honored — gate that DETECTS, not codegen

`core/entity_registry.py:430-432` records ADR-S4-001's rationale: schemas are kept
as **separate hand-authored files**, auto-discovered via `schema_module_path`,
**NOT generated from descriptor metadata**. This ADR **does not reverse that.**
The drift gate is a **read-only comparator**: it reads the model field set and the
schema cf-name set and reports divergence. It **never writes a schema, never
generates a column, never mutates a descriptor.** Remediation (add a column /
register an exclusion) is a **human edit** to the hand-authored schema file —
exactly the workflow ADR-S4-001 protects. The telos states this constraint
explicitly: *"schema codegen-from-model reverses ADR-S4-001 (one-way door) — the
drift gate (warn-first) is the recommended mechanism, NOT codegen"*
(`gfr-dynvocab.md:75`). This ADR is the gate; it is the non-codegen side of that
fork by construction.

## FRAME-006 — generality across >=2 EntityTypes

The drift gate and the underlying heuristic-tail + override mechanism are
**entity-agnostic** because both operate off the **descriptor-driven registry**,
not per-entity branches:

- **The gate** iterates `get_registry().all_descriptors()` (the same loop the
  existing schema auto-wire uses at `dataframes/models/registry.py:143`). Any
  descriptor with both `model_class_path` and `schema_module_path` is checked.
  No entity is special-cased. Today that set includes **Offer, Business, Unit,
  Contact, Process** (and holders) — comfortably **>=3 EntityTypes**. The
  worked example is **Offer** (asset_id drift); **Business** and **Unit** are
  checked by the identical loop with zero added code.
- **The tail's override mechanism** resolves arbitrary cfs across EntityTypes via
  the `custom_field_resolver_class_path` seam on the EntityDescriptor
  (`core/entity_registry.py:136`). The resolver is selected per descriptor
  (`_get_custom_field_resolver()` dynamically imports the configured class
  "instead of hardcoding entity type checks" — `entity_registry.py:138-139`), and
  the EntityType-scoped override context is the descriptor's own resolver +
  alias chain. The same `_extract_raw_value` cf-type match-table
  (`dataframes/resolver/default.py:234-287`) coerces text/number/enum/multi_enum/
  date/people for **any** entity; the SET override for `asset_id` is one entry in
  the override context, not an Offer-special-case.

### HONEST claim — registration IS code (not "zero code change")

Adding a **new** EntityType to the generality surface is **NOT zero-code**. It
requires:

1. An **EntityDescriptor** entry in `ENTITY_DESCRIPTORS`
   (`core/entity_registry.py:435+`) with `model_class_path` + `schema_module_path`
   set (the 2-file pattern ADR-S4-001 documents at `:426-432`).
2. An **override-context addition** if that entity has cfs needing non-default
   coercion (e.g. another SET-typed field) — an entry keyed by canonical field
   NAME (`NameNormalizer.normalize`) in the entity's override registry. The cf gid
   is a runtime intra-task value handle only, never a key (operator NAME-keying
   correction 2026-06-25; supersedes the original Iceberg "type-by-id-not-name"
   framing). Ratified in telos `gfr-dynvocab.md:44`.

What IS zero-code is that **the gate and the tail then cover the new entity
automatically** — no new gate branch, no new tail branch, no per-entity drift
check. The generality is *"the same mechanism resolves >=2 (here >=3) EntityTypes
through the descriptor registry with no entity-special-casing in the gate or
tail,"* NOT *"a new EntityType needs no code."* The telos's GENERIC predicate is
worded to match: *"with NO entity-special-casing"* (`gfr-dynvocab.md:44`) — the
special-casing is absent; the **registration** is present and is honest code.

## PT-04 FORK — per-repo drift gate (Option A) vs DEFER-1 fleet cf-contract registry (moonshot Future-4)

This is a one-way-door fork. It is **enumerated, not pre-collapsed**:

### Option A — per-repo model<->schema drift gate (THIS build's scope)

The gate designed above. Per-repo: it lives in autom8y-asana, checks
autom8y-asana's own model<->schema coherence at autom8y-asana's import time.
- **Scope**: one repo's receiver-side coherence.
- **Reversibility**: two-way door (predicate + warn emitter in a non-frozen pure
  function; mode flip per repo).
- **Cost**: a sibling validator + a pure detector + a test fixture. Bounded.
- **What it CANNOT do**: it cannot see the **producer side** (the autom8 satellite
  `_CONTRACT_COLUMNS`), and it cannot enforce a contract **across** services. A
  drift introduced in the autom8 producer is invisible to autom8y-asana's
  import-time gate until the data arrives malformed at runtime.

### Option B — DEFER-1 fleet cf-contract registry (moonshot Future-4, the scoped dissent)

A **cross-service** cf-gid contract registry: a single authoritative source of
truth for which cfs each entity carries and which columns each consumer requires,
covering BOTH the satellite `_CONTRACT_COLUMNS` **producer** side AND every
**consumer's** needs, so a drift is caught at the contract boundary before it
reaches any consumer.
- **Scope**: fleet-wide; multiple repos and services bind one registry.
- **Reversibility**: **ONE-WAY DOOR.** A shared cross-service contract is a
  coherence-doctrine commitment: once services depend on it, removing it
  re-introduces silent cross-service drift, and its schema becomes a fleet-level
  API. This is the moonshot Future-4 dissent's own framing
  (`gfr-dynvocab.md:74`): *"fleet-scale coherence wants a cf-gid contract
  registry, not per-repo drift-gate alone — DEFER-registered, escalate when a 2nd
  service binds the drift class."*
- **Disposition**: **ESCALATE-ONLY. NOT designed or built here.** Designing it
  inside a single 10x-dev session would be exactly the DEFER->SHIP scope collapse
  the shape §9 R-DEFER-COLLAPSE guard forbids. This ADR records the boundary and
  the escalation triggers; it does not architect the registry.

### The boundary (load-bearing)

**Option A is IN-SCOPE and SHIPPED this build. Option B is OUT-OF-SCOPE,
ESCALATE-ONLY, and a one-way door.** The per-repo gate is the **receiver-side
prevention** for THIS repo's instance of the drift class; the fleet registry is
the only thing that prevents the class **across** services, and it is precisely
the kind of irreversible fleet commitment that requires operator/strategy
sign-off, not an architect's in-session decision.

### Escalation triggers (recorded, per DEFER-1)

- **S4a — 2nd service hits the drift class** → **FIRED** (see Production-driver).
  The autom8 legacy monolith is a second production consumer of the exact
  `asset_id` / `_CONTRACT_COLUMNS` drift. Trigger met → **operator/strategy
  escalation** for the DEFER-1 fleet registry. This ADR does NOT act on it beyond
  raising the flag.
- **S4c — coherence-doctrine RFC** → if/when a fleet coherence doctrine is
  drafted, the cf-contract registry is its natural home. Escalate to that RFC.

## Production-driver linkage — the empirical S4a trigger (FIRED)

The DEFER-1 reactivation trigger is **firing now**, verified by direct inspection
of both repos:

- **The live bug**: `autom8/apis/asana_api/objects/project/models/paid_content/main.py:70`
  computes `df = df[df["office_phone"].notna() & df["asset_id"].notna()]`. When the
  satellite `get_df` arm produces a frame whose columns are limited to
  `_CONTRACT_COLUMNS = ("office_phone", "vertical", "gid")`
  (`autom8/apis/asana_api/satellite/getdf_signals.py:77`), the `df["asset_id"]`
  access raises **`KeyError: 'asset_id'`** — `asset_id` is a custom field the
  contract **drops**.
- **The silent false-green**: the satellite's canary computes
  `contract_held = has_office_phone and has_vertical and has_gid`
  (`getdf_signals.py:282`) and emits `ColumnContractFailure = 0.0` when those
  three hold (`:284`). Because `asset_id` is **not in the contract**, the canary
  is **structurally incapable** of seeing its absence — `contract_held: true` even
  as the consumer is about to `KeyError`. This is the discriminating-canary
  anti-pattern: a signal that proves "alive" but not "functional."
- **The mirror in the receiver**: autom8y-asana's own deploy gate carries the
  **identical** contract:
  `tests/unit/canary/test_deploy_gate_content_binding.py:71` asserts
  `canary.PROJECT_CONTRACT_COLUMNS == ("office_phone", "vertical", "gid")`,
  explicitly mirroring `getdf_signals.py` (`:70` comment). The same three columns;
  the same blind spot to `asset_id`.

**The linkage**: the model<->schema drift gate is the **per-repo, receiver-side
prevention for THIS class** — it makes autom8y-asana's own `asset_id`-style drift
(Offer model declares "Asset ID"; Offer schema omits it) **observable at import
time**, where today nothing detects it. It does **not** fix the autom8 producer or
the cross-service contract — that is the DEFER-1 fleet registry (Option B,
escalate-only). The existence of a **second** consumer (autom8) hitting the exact
drift class is the empirical S4a trigger, and this ADR flags it.

## S4a escalation flag

```
ESCALATION: S4a FIRED
  trigger: "2nd service binds the drift class"
  evidence:
    - autom8 KeyError 'asset_id' @ apis/asana_api/objects/project/models/paid_content/main.py:70
    - silent false-green canary @ apis/asana_api/satellite/getdf_signals.py:77,282,284
    - mirrored contract in receiver @ tests/unit/canary/test_deploy_gate_content_binding.py:71
  consequence: DEFER-1 fleet cf-contract registry reactivation condition MET
  disposition: ESCALATE-ONLY to operator/strategy. NOT designed/built in this initiative.
  in-scope-instead: per-repo drift gate (Option A, this ADR) ships as warn-first prevention for autom8y-asana's instance.
```

## RED-on-divergence is provable (the behavioral activation probe)

A test in the SPRINT-4 suite proves the gate is **behaviorally active**, not inert:

- **Deliberately-divergent fixture**: register a throwaway test entity (or
  monkeypatch a descriptor) whose model declares a `field_name` (e.g.
  `"Deliberately Missing"`) with NO corresponding schema column.
- **Assert RED on the detector**: `detect_model_schema_drift(model_names,
  schema_cf_names, exclusions)` returns a frozenset **containing**
  `"Deliberately Missing"` → the test asserts the set is non-empty and contains
  the planted field. This is the assertable RED.
- **Assert warn-first on the emitter**: with the real (drifted) registry, calling
  `_validate_model_schema_coverage()` **does not raise** and the captured log
  contains a `"model_schema_drift_detected"` record with
  `drifted_fields` including `"Asset ID"`. (Real drift → observed warning, no
  crash.)
- **Assert the floor**: the 184-test floor stays GREEN because import never
  raises (the gate warns; the `try/except` wrapper is a second guard).

This separates the **detector** (RED-assertable in test) from the **emitter**
(warn-only in prod), satisfying both the warn-first prod constraint AND the
test-provable RED requirement.

## What this does NOT change (frozen surfaces — byte-identical)

- **ADR-S4-001**: schemas remain separate hand-authored files; NOT codegen.
  The gate is read-only.
- **The certified identity spine**: `_resolve_identity_plan_async`,
  `assert_rows_tenant_identity`/GAP-1 guard, `query/{engine,join,compiler}.py`,
  `IDENTITY_FIELDS` — UNTOUCHED. The gate runs in `SchemaRegistry`
  initialization, not in the resolution path.
- **The dynvocab three-state contract** (`DynFieldState`) and the tail
  (`dynvocab.py`) — UNTOUCHED. The gate observes coverage; it does not resolve.
- **The tail-scope ADR partition** (Option A entry-scoped ownership) — UNTOUCHED.
  Routing is orthogonal to detection.
- **The closed `errors.py` reason vocabulary** — NOT widened. The gate emits logs/
  metrics, not GFR resolution errors.
- **`_validate_extractor_coverage`** (the existing schema→extractor validator) —
  UNCHANGED. The new validator is a sibling, not a rewrite.

## Risk note

- **Primary risk**: a bug in the gate that raises into `_ensure_initialized`.
  Mitigation: the existing `try/except Exception` wrapper at `registry.py:158-166`
  swallows any raise to a `"schema_validation_failed"` warning — the gate cannot
  crash startup even if it has a bug. Plus the gate is written to never raise in
  `warn` mode by construction.
- **Secondary risk**: NAME-keying mismatches (model `field_name` "Asset ID" vs
  schema `source` suffix "Asset ID"). Mitigation: normalize both sides through the
  same normalization the tail uses (whitespace-agnostic; the
  `models/business/registry.py` alias chain), and accept `cascade:` sources as
  coverage (a cascaded field IS covered, just from an ancestor). False-positive
  drift (a covered field reported as drift) is a WARN, not a RED — it costs noise,
  not a crash; tune the exclusion/normalization, no floor risk.
- **Reversibility**: two-way door. The validator is a new pure function + a warn
  emitter behind a default-`warn` mode flag. Removing it or flipping the mode is a
  one-line change; no schema migration, no API contract, no irreversible
  commitment. (Contrast Option B, the fleet registry: one-way door — hence
  escalate-only.)

## Telos-scope adjudication — escalation flag

**Option A (per-repo gate): IN-SCOPE. No operator re-ratification required.**
It makes precisely the ratified COHERENCE predicate true
(`gfr-dynvocab.md:47`) and nothing more: it does not change verification_method,
deadline, or attester; does not touch the certified spine
(*"strictly-additive ... must never re-open"*, `:76`); does not reverse ADR-S4-001
(*"NOT codegen"*, `:75`).

**Option B (fleet cf-contract registry / DEFER-1): OUT-OF-SCOPE, ESCALATE-ONLY,
one-way door.** S4a has FIRED (second consumer confirmed). The reactivation
condition is met, but the design/build of the fleet registry is an
operator/strategy decision, not an architect's in-session call. This ADR raises
the flag and stops.

Evidence grade: `[STRUCTURAL | MODERATE]` — design-time ADR; the COHERENCE
RED/GREEN realization is attested by the rite-disjoint review-rite critic at close
(telos `verified_realized`), not by this author.
