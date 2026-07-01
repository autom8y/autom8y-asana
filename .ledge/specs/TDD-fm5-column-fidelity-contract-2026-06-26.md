---
type: spec
subtype: tdd
status: accepted
lifecycle_stage: design-lock
title: "TDD — FM-5 column-fidelity contract: typed contract-incomplete on /v1/query (ARM-B)"
date: 2026-06-26
initiative: receiver-contract-realization
sprint: S3 (WS-FM5 build; 10x-dev)
code_truth_anchor: origin/main b9648de494115063161cd1e019ec1a931c05d725
self_assessment_ceiling: MODERATE
companion_adr: .ledge/decisions/ADR-fm5-typed-contract-incomplete-locus-2026-06-26.md
implements: .ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md
realizes_arm: ARM-B (typed contract-incomplete; ARM-A real-economics is SEAM-2)
---

# TDD — FM-5 column-fidelity contract (ARM-B)

## Overview
Graft a **column-completeness** check onto the existing `honest_contract_complete` gate so that a
`/v1/query/{entity_type}/rows` request declaring a REQUIRED column the served frame cannot provide returns
a **typed contract-incomplete signal** (200 + `honest_contract_complete=False` + a structured
`RowsMeta.contract_incomplete` block) instead of a silent narrow frame / downstream KeyError / fossil. The
declaration is two-layer (vendored consumer manifest seeds canary+CI; an optional `required_columns` wire
field is the runtime authority), derived through the #114 FieldContract SSOT (G-PROPAGATE). The change is
strictly-additive and schema-selection-neutral.

## Context
- PRD/decision context: companion ADR (FORK-A=O3, One-Gate graft, Door-C rebind-not-widen, RULING-1
  re-confirm). Ratified shape input: `SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md`.
- Constraints (frame C1-C6): strictly-additive on the GFR spine; derive/delegate-never-replicate;
  WARN-first drift gate (codegen-from-model FORBIDDEN, ADR-S4-001); premise-validation before design-lock
  (satisfied, below); atomic per-repo PR; proven-by-RED by a rite-disjoint critic (self caps MODERATE).
- E1 satisfied: `field_contract_maps.py` PRESENT on main (b9648de4 = #114 merge).

## Premise Receipt (S2 — premise-validation-discipline; EVIDENCED, not assumed)

**Question:** does the `/v1/query` `entity_type=project` frame for BusinessOffers (GID 1143843662099250)
serve `offer_id`, or is it dropped by the S-07 minimal schema?

**Deterministic answer (load-bearing, in-repo, b9648de4):**
- Served column set for `entity_type=project` = `PROJECT_SCHEMA` = `BASE_COLUMNS` (13:
  `gid, name, type, date, created, due_on, is_completed, completed_at, url, last_modified, section, tags,
  parent_gid` — `dataframes/schemas/base.py:12-104`) + `PROJECT_EXTRA_COLUMNS` `{status, office_phone,
  vertical}` (`dataframes/schemas/project.py:18-44`) = **16 known columns**. Registry
  `default_projection` is those same 16 (`core/entity_registry.py:905-922`).
- **`offer_id` ∉ that set.** `grep -rn offer_id dataframes/schemas/` → matches ONLY `offer.py:42` and
  `asset_edit.py:127`. The generic `SchemaExtractor` (`entity_registry.py:902`) emits only schema columns,
  so any project frame (at-rest or on-demand) cannot carry `offer_id`.
- Failure modes today: (a) explicit `select=["offer_id"]` → `UnknownFieldError` at `engine.py:213-218`
  (`schema.get_column` is None) — a hard 4xx, NOT the contract-incomplete signal; (b) default projection
  (no offer_id) → the consumer's own code indexes `offer_id` → KeyError / silent null (the fossil). The
  silent-drop at `engine.py:235-237` is a sibling latent risk for schema-known-but-df-absent columns.

**Live confirmation (AWS `tom.tenuta` / acct 696318035277):**
- `aws s3 ls s3://autom8-s3/asana-cache/dataframes/1143843662099250/` → EMPTY; `project-frames/1143843662099250/`
  → EMPTY; `tasks/1143843662099250/` → EMPTY. The BusinessOffers GID has **no built receiver frame** in S3
  — consistent with the GID being on `SATELLITE_GET_DF_GID_DENYLIST` (the $8,775/7-row fossil is the legacy
  satellite SDK path, NOT a receiver DataFrame). Positive live receipt that the fossil is the denylisted
  legacy arm.
- `[UV-P: column-by-column inspection of the SERVED entity_type=project frame for this GID | METHOD:
  read-only S3 parquet DESCRIBE | REASON: the project/offer leaf entities are warmable=False
  (entity_registry.py:898/936) and build on-demand only; no at-rest parquet exists to inspect, and invoking
  the live endpoint for a denylisted GID would trigger an on-demand build (a write/compute) outside
  read-only scope. The deterministic PROJECT_SCHEMA answer is authoritative.]`
- Cross-repo corroboration (inherited, not first-party): the monolith `OfferIdAbsent`/`AssetIdAbsent`
  emitter (`getdf_signals.py:297-298`, per shape S10) exists precisely because `offer_id` is absent on the
  satellite arm.

**Verdict:** premise CONFIRMED — `offer_id` is genuinely absent on the project arm. The design is NOT built
on a false premise (no G-PREMISE/G-HALT trip). PT-02 satisfiable.

## System Design

### Architecture Diagram
```
 monolith consumer (business_offers, fetch_section_rows)
   │  declares required need
   ▼
 [Layer-1] consumer_column_requirements.json  (MONOLITH repo, consumer-owned)
   │  vendored + freshness guard (reversed gen.json)
   ▼
 src/autom8_asana/dataframes/contracts/
   ├─ consumer_column_requirements.vendored.json   (NEW seed artifact)
   └─ field_contract_maps.py  (SSOT, #114 home)  ── required_columns_for(entity_type)  ◄── G-PROPAGATE sole point
            │ derives per-shape required set                                   │
            │                                                                  ├─► CI parity test (declared-but-unservable = build RED)
            ▼                                                                  └─► two-sided canary fixture seed
 [Layer-2 runtime]  RowsRequest.required_columns (optional)  ──►  EntityQueryService.execute_rows
                                                                     │  (engine.py:235  available = df.columns)
                                                                     ▼  12.5 ONE-GATE graft (engine.py:247-255)
                              honest_contract_complete = section_honest AND column_contract_complete
                                                                     ▼
                              RowsResponse(200) .meta.honest_contract_complete=False
                                              .meta.contract_incomplete = {missing:[offer_id reason=not_in_schema ...]}
```

### Components
| Component | Responsibility | File (b9648de4 anchors) |
|-----------|----------------|--------------------------|
| Consumer manifest (vendored) | Static seed of per-consumer required columns + population_expectation | NEW `dataframes/contracts/consumer_column_requirements.vendored.json` |
| SSOT derivation | Ingest manifest → `required_columns_for(entity_type)` union; servability classification | EXTEND `dataframes/contracts/field_contract_maps.py` |
| Freshness guard | CI-loud vendored↔monolith-source drift detection (reversed `check_namespaces_gen.sh`) | NEW CI script + `tests/` parity |
| Wire field | Optional per-request declaration | EXTEND `query/models.py:274` `RowsRequest` |
| Typed meta block | Structured contract-incomplete detail | EXTEND `query/models.py:368` `RowsMeta` (new `ContractIncomplete` model) |
| One-Gate graft | Fold column-completeness into `honest_contract_complete`; build typed block | EXTEND `query/engine.py:247-255` (reuse `available` from `:235`) |

### Data Model
- **`ContractIncomplete`** (new Pydantic model, `query/models.py`):
  ```
  class IncompleteColumn(BaseModel):
      column: str
      reason: Literal["not_in_schema", "present_but_unpopulated"]
      population_expectation: str | None  # from manifest; null when runtime-only declaration
  class ContractIncomplete(BaseModel):
      missing: list[IncompleteColumn]   # non-empty by construction when present
      entity_type: str
  ```
- **`RowsRequest`** += `required_columns: list[str] | None = Field(default=None, ...)` (additive;
  `extra="forbid"`-compatible because it is a declared field).
- **`RowsMeta`** += `contract_incomplete: ContractIncomplete | None = Field(default=None, ...)`. Present
  iff `column_contract_complete is False`.
- **Manifest schema v1** = SPEC §Layer-1 verbatim (`consumer_id, code_anchor, query_shape, required_columns,
  population_expectation, on_missing`). Seed entries: `offer_id`@project, `project_gid`@section.

### API Contracts
`POST /v1/query/{entity_type}/rows` (S2S-only, `require_service_claims` — unchanged):
- Request (additive): `{"required_columns": ["offer_id"], ...existing...}`. Omitted/null ⇒ today's behavior.
- Response 200 (complete): `meta.honest_contract_complete` reflects section state; `meta.contract_incomplete`
  absent (null).
- Response 200 (incomplete): `meta.honest_contract_complete=false`;
  `meta.contract_incomplete={"entity_type":"project","missing":[{"column":"offer_id","reason":"not_in_schema","population_expectation":"nonnull_over_active_subset"}]}`.
- **Never** a non-200 for a declared-missing column (no hard-fail; two-way door). `select` of an unknown
  column remains a 4xx `UnknownFieldError` (separate, pre-existing channel — `required_columns` is a
  contract assertion, NOT a projection selector).

### Sequence (incomplete-column path)
1. Request arrives with `required_columns=["offer_id"]`, `entity_type=project`.
2. Engine loads frame, projects, computes `available = set(df.columns)` (`engine.py:235`).
3. Effective required set = `request.required_columns ∪ required_columns_for("project")` (SSOT-derived).
4. `column_contract_complete = required_set ⊆ available`; for each missing col, classify reason via
   `schema.column_names()` (`not_in_schema` if absent from schema, else `present_but_unpopulated`).
5. `honest_contract_complete = section_honest AND column_contract_complete` (One-Gate).
6. `honest_empty` (`engine.py:266`) composes correctly: an incomplete frame is NOT attested honest_empty.
7. Build `RowsMeta.contract_incomplete` when incomplete; return 200.

## Non-Functional Considerations

### Performance
- Added work per request when `required_columns`/manifest non-empty: one set-subset over `available`
  (≤16 cols today) + ≤N schema lookups (N = declared count, currently 1-2). **Target: added P95 latency
  < 1ms** (pure in-memory set ops; no I/O — the `available` set and schema are already in scope). Measured
  by the existing engine micro-bench / query unit timing. Zero added work when `required_columns is None`
  and the manifest-derived set for the shape is empty.

### Security
- No new endpoint, no auth/crypto/PII/session change. Endpoint remains S2S-only (`require_service_claims`).
- Disclosure constraint (binding): `contract_incomplete.missing[].column` echoes ONLY the requester's OWN
  declared columns (+ schema-public names already exposed via `UnknownFieldError.available`). It MUST NOT
  enumerate undisclosed schema internals. Security gate NOT triggered (ADR §Consequences).

### Reliability
- Failure-safe: the column check is pure and total; an exception in derivation must NOT block the response
  (mirror the existing `_derive_honest_contract_complete` BROAD-CATCH at `engine.py:590-594` →
  conservative `column_contract_complete=False` only if a required set was declared, else no-op True).
- Additive default: `required_columns=None` + empty manifest set ⇒ identical bytes to today (two-way door).

## Implementation Guidance — exact build surface for principal-engineer

| # | File | Change |
|---|------|--------|
| 1 | `dataframes/contracts/field_contract_maps.py` | ADD `load_consumer_requirements()` (read vendored JSON) + `required_columns_for(entity_type: str) -> frozenset[str]` (union over declaring consumers) + a servability classifier helper. Pure functions; no import of `query/` (preserve dependency direction). Extend module docstring SCOPE NOTE (Phase-3 now in-scope for the manifest-ingestion slice). |
| 2 | `dataframes/contracts/consumer_column_requirements.vendored.json` | NEW. Seed = SPEC §Layer-1 two entries (`offer_id`@project, `project_gid`@section). Until the monolith hand-back lands, seed is design-locked here and the freshness guard compares against it. |
| 3 | `query/models.py` | ADD `IncompleteColumn`, `ContractIncomplete` models; `RowsRequest.required_columns`; `RowsMeta.contract_incomplete`. |
| 4 | `query/engine.py` (12.5 block, `:247-255`) | GRAFT: compute effective required set, `column_contract_complete`, AND into `honest_contract_complete`; build `contract_incomplete`. REUSE `available` (`:235`). NO sibling code path. NO change to `_resolve_identity_plan_async`, `assert_rows_tenant_identity`, or the section-derivation method body. |
| 5 | CI freshness guard | NEW script (reversed `check_namespaces_gen.sh`) + wiring; vendored↔monolith-source drift ⇒ CI RED. |
| 6 | `tests/` | (a) two-sided discriminating canary fixture (below); (b) CI parity: a manifest column unservable for its shape ⇒ build RED; (c) additive-default regression: `required_columns=None` ⇒ unchanged meta. |

## Two-sided discriminating canary DESIGN (principal-engineer authors; rite-disjoint review critic RUNS)
Per discriminating-canary-doctrine — the RED is a deliberately-broken **INPUT** the live surface correctly
rejects, NEVER a defect injected into prod code. The canary has TEETH (two-sided):
- **RED side (bites):** `POST /v1/query/project/rows` with `required_columns=["offer_id"]` against a
  project-shaped frame (offer_id genuinely unservable). ASSERT `meta.honest_contract_complete is False`
  AND `meta.contract_incomplete.missing[0].column == "offer_id"` AND `reason == "not_in_schema"`. The RED
  is the assertion that the typed signal FIRES on the missing-column input.
- **GREEN side (passes):** `POST /v1/query/offer/rows` with `required_columns=["offer_id"]` against an
  offer-entity frame (`offer.py:42` natively serves `offer_id`). ASSERT `meta.contract_incomplete is None`
  AND `meta.honest_contract_complete` reflects section state (True for a complete frame). NO column
  refusal fires.
- **Discrimination:** the canary bites ONLY on the missing-column input; the complete-column input passes.
  The GREEN frame reads FRESH (never a stale legacy-arm S3 cache — R2 guard).
- S3 in-rite proof: qa-adversary authors the adversarial RED assertions (agent-disjoint, caps MODERATE).
  S9 verified-realized: the SAME two-sided shape, run by the rite-disjoint **review** critic against the
  integrated live system — NEVER the builder, NEVER qa-adversary.

## mypy / arch implications
- New Pydantic models are fully typed (`Literal` reasons, no `Any`). `extra="forbid"` on `RowsRequest`/
  `RowsMeta` holds (additive declared fields).
- Dependency direction preserved (DIP): `query/engine.py` (policy) → `dataframes/contracts/field_contract_maps.py`
  (detail) — the contracts module must NOT import from `query/` (it stays a pure leaf). Verify no cycle.
- Strictly-additive: GFR spine (105 tests), `assert_rows_tenant_identity` RED-on-bypass, and
  `_resolve_identity_plan_async` are not touched. Drift gate stays WARN-first (NO codegen-from-model).

## Test Plan (run via `./.venv/bin/python -m pytest`, NEVER `uv run`)
1. Two-sided canary (above) — RED bites, GREEN passes.
2. Additive default: `required_columns=None` and empty manifest ⇒ `meta` identical to pre-FM-5 (regression).
3. CI parity: a manifest entry whose column the shape cannot serve ⇒ build-time RED (not a runtime KeyError).
4. Freshness guard: vendored ≠ monolith-source ⇒ CI RED.
5. `present_but_unpopulated` path: a schema-known column absent from `available` ⇒ `reason="present_but_unpopulated"`.
6. honest_empty composition: a 0-row frame missing a required column is NOT `honest_empty`.
7. Failure-safe: derivation exception ⇒ does not block the 200 response.
8. GFR spine unchanged: the 105 certified tests GREEN; `assert_rows_tenant_identity` fires RED-on-bypass.

## Risks and Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `honest_contract_complete` semantic broadening confuses existing readers | M | M | Fires only on opt-in `required_columns`/manifest; typed block disambiguates; honest_empty composes correctly |
| Vendored manifest ↔ monolith source drift | M | M | CI freshness guard makes drift LOUD (build RED) |
| Grafting a guard that hard-fails a live consumer (C3 prod-breaker) | L | Critical | D3 keeps response 200/additive; producer never raises on missing required column |
| Canary reads a stale legacy-arm cache (false-green) | M | H | GREEN side reads a FRESH offer-entity frame (R2); S9 disjoint critic verifies freshness |
| Scope creep into eager 30-col parity | L | M | RULING-1 re-confirmed: contract-driven subset (offer_id + project_gid only) |

## ADRs
- `.ledge/decisions/ADR-fm5-typed-contract-incomplete-locus-2026-06-26.md` (FORK-A=O3; One-Gate graft;
  Door-C rebind-not-widen; RULING-1 re-confirm; security-gate decline).

## Open Items (operator / Potnia — NOT build blockers for the architecture, but gate the S3 dispatch)
1. Operator confirm `verification_deadline` = design-lock+21d = **2026-07-17** (telos-integrity Gate A).
2. Operator/Potnia resolve `rite_disjoint_attester` (telos=`eunomia` vs shape=`review-rite`).
3. Monolith manifest hand-back (file path + sha) — cross-repo round-trip step 1; until then the vendored
   seed is design-locked from SPEC §Layer-1.
