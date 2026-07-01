---
type: spec
subtype: tdd
artifact_id: TDD-fm5-armb-honest-refusal-contract
title: "FM-5 ARM-B — the honest-refusal consumer-column contract (design-lock)"
created_at: "2026-06-26T00:00:00Z"
author: architect
prd_ref: PRD-fm5-column-fidelity
status: accepted
components:
  - name: ConsumerColumnContract
    type: module
    description: "field_contract_maps.py extension: ingests the vendored consumer manifest and derives the per-(entity_type,endpoint) required-column SET. The SOLE propagation point (G-PROPAGATE)."
    dependencies:
      - name: consumer_column_requirements.vendored.json
        type: internal
  - name: ColumnContractGate
    type: module
    description: "query/engine.py graft at the ONE gate (:247-266): co-derives contract_complete from schema membership vs the declared required set; stamps the sibling meta fields."
    dependencies:
      - name: ConsumerColumnContract
        type: internal
      - name: DataFrameSchema
        type: internal
  - name: RowsContractWire
    type: module
    description: "query/models.py additive surface: RowsRequest.required_columns (optional wire field) + RowsMeta.contract_complete / unservable_required_columns / column_manifest."
    dependencies: []
  - name: ContractFreshnessGuard
    type: script
    description: "CI check (reversed-SNC gen.json pattern): validates the vendored manifest schema and, once the monolith source is handed back, asserts vendored==source (drift => CI-loud RED)."
    dependencies:
      - name: consumer_column_requirements.vendored.json
        type: internal
api_contracts:
  - endpoint: "/v1/query/{entity_type}/rows"
    method: POST
    description: "Additive: accepts optional required_columns; serves with new honest meta fields. A consumer that declares nothing gets today's behavior (two-way door)."
    request:
      body:
        required_columns: "list[str] | null — columns the consumer's code INDEXES and requires served"
    response:
      success:
        status: 200
        body:
          meta:
            contract_complete: "bool — false iff any declared required column is not in the served schema"
            unservable_required_columns: "list[str] — the declared columns the served schema cannot satisfy"
            column_manifest: "object | null — served columns + per-column non-null population (belt-and-braces)"
      errors:
        - status: 400
          description: "UnknownFieldError unchanged — still fires for explicit select of an unknown field (this is a different gate)."
related_adrs:
  - ADR-fm5-armb-contract-locus
schema_version: "1.0"
---

## Overview

ARM-B is the **honest-refusal contract layer**: a consumer declares the columns its code
indexes; `/v1/query` answers, per request, whether the served schema can satisfy that
declaration; if not, it emits a TYPED `contract_complete=False` (the column analogue of
`honest_contract_complete`) plus the named unservable columns — never a silent narrow frame.
ARM-B is **cure-neutral**: it ships the mechanism regardless of whether a given column's data
cure is widen or rebind (those are SEAM-2, operator-held). Decisions are locked in
`ADR-fm5-armb-contract-locus`. Code anchors below were re-located by grep against
origin/main `b9648de4` (the build base) and labelled SVR.

## 1. Real-frame anchors (SVR — re-located on origin/main b9648de4)

- `[SVR git show origin/main:.../field_contract_maps.py | 96 lines; DTYPE_MAP/FIELDCLASS_MAP + parity helpers; SCOPE NOTE :23-25 defers the full FieldContract registry/derivation/generator to Phase-3]` — FM-5 IS that Phase-3 consumer-manifest work, built into this file.
- `[SVR query/engine.py:145 | schema = registry.get_schema(_to_pascal_case(entity_type))]` — the 16-col PROJECT_SCHEMA is the serve boundary.
- `[SVR query/engine.py:204-218 | request.select / default_projection resolution + UnknownFieldError on schema.get_column(col) is None]` — explicit-select already typed-rejects; the no-select path (:209-210) does not.
- `[SVR query/engine.py:235-237 | available=set(df.columns); valid_columns=[c for c in columns if c in available]; df.select(valid_columns)]` — the SILENT-DROP site: a selected column absent from df is dropped with no signal.
- `[SVR query/engine.py:247-266 | honest_contract_complete derive + honest_empty]` — the ONE gate. `[SVR :527 _derive_honest_contract_complete]` — canonical section derivation.
- `[SVR query/models.py:443-446 | "honest_contract_complete=False -> 503"]` — the 503/retry collision that FORBIDS folding column-completeness into honest_contract_complete (ADR D2).
- `[SVR query/models.py:277 RowsRequest extra="forbid"; :371 RowsMeta extra="forbid"; :448-450 bridge ignores unknown meta keys]` — additive RowsRequest/RowsMeta fields are safe + consumer-additive.
- `[SVR dataframes/schemas/project.py:46-54 | PROJECT_SCHEMA = BASE_COLUMNS(13)+[status,office_phone,vertical], version 1.1.0; offer_id ABSENT]`.
- `[SVR dataframes/schemas/section.py:49-57 | SECTION_SCHEMA = BASE_COLUMNS(13)+[status,office_phone,vertical]; project_gid ABSENT; no constant-injection source token]` — Door-C widen is premise-unvalidated (TDD §6.2).
- `[SVR core/entity_registry.py:905-922 | project default_projection = the same 16 cols; offer_id ABSENT]`.
- `[SVR resolution/gfr/engine.py:98 _resolve_identity_plan_async; :144 assert_rows_tenant_identity; guard.py:183 def assert_rows_tenant_identity]` — the FROZEN GFR spine (strictly-additive constraint; untouched).

## 2. System context

```
monolith consumer (business_offers) ──declares──> consumer_column_requirements.json (MONOLITH repo)
                                                              │ vendored + freshness guard
                                                              ▼
   src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json
                                                              │ ingested by
                                                              ▼
        field_contract_maps.py  ── derive_required_columns(entity_type, endpoint) ──┐  (SSOT, SOLE propagation point)
                                                              │                      │
                          ┌───────────────────────────────────┼──────────────────────┤
                          ▼                                   ▼                      ▼
                 CI parity test                      two-sided canary fixture   monolith bridge
              (build-time RED on drift)              (RED arm / GREEN arm)      (populates the wire field — SEAM-2/monolith, NOT receiver)
                          
   runtime: POST /v1/query/{entity}/rows  {required_columns:[...]}  ── engine.py ONE gate ──> meta.contract_complete (+ unservable + column_manifest)
                          completeness = (required ⊆ schema.column_names())     ← SCHEMA, never df.columns
```

## 3. Component design

### 3.1 ConsumerColumnContract (field_contract_maps.py extension)

Activates the file's own Phase-3 SCOPE NOTE. New, clearly-sectioned additions with their own
`__all__` exports (the dtype-parity maps stay untouched):

- `load_consumer_requirements() -> ConsumerRequirements` — reads the vendored JSON, validates the
  v1 schema (`schema_version`, and per-consumer: `consumer_id`, `query_shape{endpoint,entity_type}`,
  `required_columns`, `population_expectation`, `on_missing`). Raises a typed error on malformed
  manifest (fail-loud, never silent).
- `derive_required_columns(entity_type: str, endpoint: str) -> frozenset[str]` — the per-query-shape
  required set = union of `required_columns` over consumer entries whose `query_shape` matches. The
  build-time / canary / CI source of truth. (Runtime enforcement uses the wire field as
  authoritative; this derivation seeds CI + canary + is what the monolith bridge reads to populate
  the wire field.)
- `requirements_drift_check(monolith_source: Path | None) -> DriftReport` — the freshness guard hook
  (§3.4).

Data file: `src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json`,
seeded with the SPEC's two instances (`business_offers.active_offers_frame → offer_id` on
project; `fetch_section_rows → project_gid` on section). This IS the contract's first two
instances (RULING blend item c).

### 3.2 ColumnContractGate (engine.py graft — the EXACT point)

Graft **between** the `honest_contract_complete` derivation (current `:253-255`) and the
`honest_empty` line (current `:266`), i.e. inside the `# 12.5` block. New co-located method near
`:527`:

```python
def _derive_column_contract(
    self,
    *,
    entity_type: str,
    schema: DataFrameSchema,
    required_columns: list[str] | None,
    df: pl.DataFrame,
) -> tuple[bool, list[str], dict[str, object] | None]:
    """Column analogue of honest_contract_complete. Derived from SCHEMA membership
    (schema.column_names()), NEVER df.columns (immune to the 100%-NULL offer_id)."""
    served = set(schema.column_names())
    required = list(required_columns or [])
    unservable = [c for c in required if c not in served]           # SCHEMA, not df
    contract_complete = not unservable
    column_manifest = None
    if required:                                                     # belt-and-braces, only when declared
        column_manifest = {
            "served": sorted(served & set(df.columns)),
            "population": {c: int(df[c].drop_nulls().len()) for c in (served & set(df.columns))},
        }
    return contract_complete, unservable, column_manifest
```

Call site (additive, after `:255`):

```python
contract_complete, unservable_required, column_manifest = self._derive_column_contract(
    entity_type=entity_type, schema=schema,
    required_columns=request.required_columns, df=df,
)
```

and pass `contract_complete=contract_complete, unservable_required_columns=unservable_required,
column_manifest=column_manifest` into `RowsMeta(...)` at `:270`.

This is **the one-gate graft, not a sibling path** (ADR D2): same gate, SSOT-fed, no new endpoint
or control-flow branch. `UnknownFieldError` (`:213-218`) is a DIFFERENT gate (field-vs-schema on
explicit select) and is unchanged — ARM-B adds the consumer-DECLARED-contract check the no-select
path lacks.

### 3.3 RowsContractWire (models.py additive surface)

- `RowsRequest.required_columns: list[str] | None = Field(default=None, ...)` (after `:294`). Declared
  field, compatible with `extra="forbid"`.
- `RowsMeta.contract_complete: bool = Field(default=True, ...)` — default **True** so non-declaring
  consumers get today's behavior. `unservable_required_columns: list[str] = Field(default_factory=list)`.
  `column_manifest: dict[str, object] | None = Field(default=None)`.

Additive + two-way-door: a request with no `required_columns` yields `contract_complete=True`,
empty `unservable`, `column_manifest=None` — byte-equivalent meta semantics to today for all
existing callers.

### 3.4 ContractFreshnessGuard (reversed-SNC pattern)

CI check that (a) validates the vendored JSON against the v1 schema, (b) once the monolith source
is handed back, asserts `vendored == source` (drift => RED). Until hand-back (telos DEFER), the
guard runs in (a)-mode and records the expected `declared_at`/sha. The monolith-source binding is
a watch-registered DEFER input (the cross-repo round-trip step 1).

## 4. Key design decisions (full rationale in ADR)

- **4.1 LOCUS = O3** over O1/O2/O4(null)/O5(server-inversion)/O6(existing-select). O5 proves consumer
  knowledge is load-bearing; O6 proves the no-select + build-gate + canary-seed gaps justify the
  manifest layer.
- **4.2 Distinct sibling field, NOT a honest_contract_complete mutation.** Folding column-completeness
  into honest_contract_complete routes a STRUCTURAL gap into 503/retry (`models.py:443-446`) — a
  retry-forever conflation. **The single item for the S4 rite-disjoint critic to confirm.**
- **4.3 Completeness from `schema.column_names()`, never `df.columns`** — the 100%-NULL production
  `offer_id` would fool a presence check (premise §SURPRISE).

## 5. Two-sided discriminating canary (design; PE authors the fixture, S4 critic RUNS)

Per discriminating-canary-doctrine. The RED arm is a deliberately-broken INPUT the live surface
correctly rejects — NEVER a defect injected into production code.

| Arm | Input | Expected | Asserts |
|-----|-------|----------|---------|
| RED (bites) | request `required_columns=["offer_id"]` against an `entity_type=project` frame | `meta.contract_complete == False` AND `"offer_id" in meta.unservable_required_columns` | a declared-but-unservable column raises the typed signal — not KeyError, not silent-drop, not fossil |
| GREEN (passes) | request `required_columns=["office_phone"]` (a served column) against the same frame | `meta.contract_complete == True` AND `unservable_required_columns == []` | a declared-and-served column passes; the gate does not over-fire |

Two-sidedness is mandatory: the RED arm bites ONLY on the defect; the GREEN arm passes. A
fixture that cannot fire both sides is rejected (G-HALT). The GREEN arm uses an already-served
column (`office_phone`) so it does NOT depend on any Door-C widen landing.

## 6. RULING-1 re-confirm + widen-vs-rebind (operator-surfaced)

### 6.1 RULING-1 — contract-driven SUBSET (re-confirmed)

Required set = the actual declared union = 2 instances (`offer_id` on project, `project_gid` on
section). NOT eager 30-column PG-02 parity. Expand only as a consumer declares. The monolith
manifest hand-back finalizes the union; the freshness guard makes drift CI-loud.

### 6.2 Widen-vs-rebind DATA-CURE — DEFERRED to SEAM-2 (operator-held) — OPERATOR-NOTE

- `offer_id` / project: widen is USELESS (100% NULL on the project frame). Schema stays unwidened →
  ARM-B emits a **permanent loud `contract_complete=False`**, which is the intended driver of the
  SEAM-2 rebind of `business_offers` onto `entity_type=offer` (`offer_id` 26.7% populated there).
  Designing a widen here would manufacture a presence-check-fooling no-value column — explicitly
  rejected.
- `project_gid` / section: widen is potentially useful but **premise-unvalidated** (S2 validated only
  `offer_id`; SECTION_SCHEMA lacks project_gid and there is no constant-injection source token). The
  widen recipe (inject the scoping `project_gid` as a constant section column, section schema bump
  1.1.0→1.2.0) is receiver-owned (C2/W1) and pre-designed, but its **APPLICATION is SEAM-2
  operator-held**, gated on premise-validation of section project_gid population + the manifest
  hand-back. Until then `project_gid`-on-section also emits the honest loud signal (correct behavior).

> OPERATOR-NOTE: this diverges from the shape S3 line "fold Door-C widening HERE" by treating the
> project_gid widen as receiver-owned-but-application-deferred rather than applied-in-S3. Reason:
> premise-integrity (no validated premise for project_gid) + Pythia's S2→S3 routing deferring
> widen-vs-rebind to SEAM-2 operator-held + RULING-1 (expand only against the confirmed union). The
> contract mechanism is complete and cure-neutral without it; surfaced for the operator's RULING-1
> re-confirm, not a build blocker.

## 7. Strictly-additive proof plan (f)

- **GFR spine GREEN**: the `resolution/gfr/` suite (15 files; integration `test_gfr_tenant_roundtrip.py`
  + 14 unit files — the certified spine, carried from gfr-dynvocab e49c30d7) must stay GREEN. ARM-B
  touches ZERO `resolution/gfr/` files. PE runs the full gfr suite and confirms no regression.
- **`assert_rows_tenant_identity` RED-on-bypass intact** (`guard.py:183`) — untouched; its bypass
  test must still fire RED.
- **`_resolve_identity_plan_async` frozen** (`engine.py:98` in resolution/gfr) — untouched.
- **No model-codegen** — the drift gate is WARN-FIRST only (`requirements_drift_check`); codegen-from-
  model reverses ADR-S4-001 (one-way door) and is FORBIDDEN.
- **Additive-only edits**: `field_contract_maps.py` (extend), new vendored JSON, `models.py` (optional
  fields, defaults preserve behavior), `engine.py` (graft at the one gate). Build base: a fresh
  worktree off origin/main `b9648de4` (NOT the session tree, which lacks e49c30d7).

## 8. EXACT build surface for principal-engineer (g)

| # | File | Change | Notes |
|---|------|--------|-------|
| 1 | `src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json` | NEW — SPEC v1 seed (2 entries) | the contract's first two instances |
| 2 | `src/autom8_asana/dataframes/contracts/field_contract_maps.py` | ADD `load_consumer_requirements`, `derive_required_columns`, `requirements_drift_check` + `__all__` | activates the file's Phase-3 SCOPE NOTE; SOLE propagation point |
| 3 | `src/autom8_asana/query/models.py` | ADD `RowsRequest.required_columns`; `RowsMeta.contract_complete`/`unservable_required_columns`/`column_manifest` | additive, defaults preserve behavior |
| 4 | `src/autom8_asana/query/engine.py` | ADD `_derive_column_contract` (near :527) + graft call between :255 and :266; pass 3 meta fields at :270 | one-gate graft; schema membership not df.columns |
| 5 | `tests/unit/query/` | NEW two-sided canary fixture (§5) + the no-select-path silent-drop regression | qa-adversary authors; S4 critic RUNS for verified-realized |
| 6 | `tests/unit/dataframes/contracts/` | NEW CI parity test (derivation correctness; build-time RED on UNEXPECTED servability drift; `offer_id` asserted to fire loud, not block) + freshness-guard test | build-time RED, not prod KeyError |

**mypy --strict**: `_derive_column_contract` returns a typed tuple; `column_manifest` typed
`dict[str, object] | None`; new Pydantic fields fully annotated. **arch**: no new cross-layer
dependency — `field_contract_maps.py` (contracts) is imported by `engine.py` (query) which already
depends on `dataframes` schemas; no inversion. Run the FULL gate locally (mypy --strict + tests/ +
arch/) before pushing — the GFR floor is narrower than CI.

## 9. Risks

| Risk | Mitigation |
|------|------------|
| S4 critic rejects the D2 distinct-field reconciliation of GLINT L1-2 | Rationale (503/retry collision, models.py:443-446) documented §4.2; if rejected, the fallback is a single richer field — but that re-opens the conflation. Surfaced explicitly. |
| Vendored manifest drifts from the (future) monolith source | `requirements_drift_check` CI guard; watch-registered DEFER on the hand-back. |
| `column_manifest` population scan adds latency | Only computed when `required_columns` is declared; non-declaring callers pay nothing. |

## Handoff

DESIGN-LOCK-READY. PE implements §8 off a fresh worktree on origin/main `b9648de4`; qa-adversary
authors the §5 two-sided canary fixture (in-rite, caps MODERATE); the S4 review rite RUNS it for
the rite-disjoint verdict. Door-C application + the monolith manifest hand-back are watch-registered
SEAM-2 / DEFER items.
