---
type: spec
subtype: tdd
status: accepted
title: "TDD — FM-5 ARM-B: typed contract-incomplete signal on /v1/query, built INTO the FieldContract SSOT"
date: 2026-06-26
rite: 10x-dev
station: S3 design-lock (architect)
initiative: receiver-contract-realization / fm5-column-fidelity
code_truth_anchor: origin/main b9648de494115063161cd1e019ec1a931c05d725
self_assessment_ceiling: MODERATE
adr: .ledge/decisions/ADR-fm5-armb-required-column-contract-locus-2026-06-26.md
---

# TDD — FM-5 ARM-B: typed contract-incomplete on /v1/query

## Overview

A consumer declares the columns it INDEXES (`required_columns`); when a declared required column
is **absent/unservable** on the served frame, `/v1/query/*/rows` returns a **typed
contract-incomplete signal** on the response meta — the *column analogue* of
`honest_contract_complete=False` — instead of a silent narrow frame, a daily `KeyError`, or a
`$0/7-row` fossil. The signal is grafted at the **One-Gate SITE** as a sibling field, derived from
the **FieldContract SSOT** (`field_contract_maps.py`, the sole propagation point), seeded by a
vendored consumer manifest with a freshness guard. Additive and two-way-door: undeclared consumers
see byte-identical behavior.

This TDD is the BUILT surface for principal-engineer (S3). It does **not** realize ARM-B —
realization is the S9 two-sided canary RUN by the rite-disjoint review critic. Decisions: see the
companion ADR (D1 LOCUS=O3, D2 sibling-field, D3 Door-C ruling).

## Context

- PREMISE (S2, verified LIVE): `offer_id` is NOT served by the `entity_type=project` frame
  (16-col `PROJECT_SCHEMA`); 100%-NULL on the project parquet (0/1380), 26.7% on the offer frame.
  Receipt: `.claude/agent-memory/architect/project_fm5_offer_id_serve_premise.md`.
- SSOT home on main (E1): `src/autom8_asana/dataframes/contracts/field_contract_maps.py` (96 lines)
  — docstring scopes the FieldContract registry / consumer-manifest derivation to Phase-3 (= this work).
- Constraints (frame C1-C6): strictly-additive on the GFR spine; derive/delegate-never-replicate;
  WARN-first drift gate (codegen-from-model FORBIDDEN, reverses ADR-S4-001); atomic per-repo PR.

## System Design

### Architecture Diagram

```
  MONOLITH repo (consumer-owned)                 autom8y-asana (producer, receiver)
  ┌───────────────────────────────┐              ┌──────────────────────────────────────────────┐
  │ consumer_column_requirements  │  vendor +    │ contracts/consumer_column_requirements.        │
  │ .json  (Layer-1 seed)         │──freshness──▶│   vendored.json        (vendored copy)         │
  └───────────────────────────────┘  guard (CI)  │                                                │
                                                  │ contracts/field_contract_maps.py  (THE SSOT)   │
   request body (Layer-2, authoritative)         │   required_columns_for_shape(endpoint,         │
  ┌───────────────────────────────┐              │     entity_type) -> frozenset[str]             │
  │ POST /v1/query/{e}/rows        │              │   door_c_disposition(entity_type, col) -> enum │
  │   { ..., required_columns:[..] }│─────────────┼──┐  (sole propagation point, G-PROPAGATE)      │
  └───────────────────────────────┘              │  │                                             │
                                                  │  ▼                                             │
                              query/engine.py execute_rows  ── ONE-GATE (:247-255) ──┐             │
                                schema(:145) + available(:235) + request.required_columns          │
                                derive required_columns_complete + missing_required_columns        │
                                          │                                                        │
                                          ▼   RowsMeta (sibling field, additive)                   │
                              { honest_contract_complete (section, 503-mapped),                    │
                                required_columns_complete (column, NOT 503-mapped),                │
                                missing_required_columns:[...], served_columns:[...] }             │
                                                  └──────────────────────────────────────────────┘
            feeds (i) engine One-Gate  (ii) two-sided canary fixture  (iii) CI parity test
```

### Components

| Component | Responsibility | File (origin/main) |
|---|---|---|
| FieldContract SSOT (extend) | Add `required_columns_for_shape()` + `door_c_disposition()` + a typed `DoorCDisposition` enum; read the vendored manifest. SOLE propagation point. | `src/autom8_asana/dataframes/contracts/field_contract_maps.py` (96 lines today) |
| Vendored manifest (new) | The consumer-owned declaration, vendored. Data, not code. | `src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json` (ABSENT today — FM-5 creates) |
| Freshness guard (new) | CI-loud drift detection (reversed SNC `check_namespaces_gen.sh` pattern). | `tests/unit/dataframes/test_consumer_manifest_freshness.py` (new) |
| Request field (extend) | Optional `required_columns: list[str] \| None` (default None → today's behavior). | `src/autom8_asana/query/models.py:274` `RowsRequest` (`extra="forbid"`, `:277`) |
| Response meta (extend) | Sibling typed field: `required_columns_complete: bool=True` + `missing_required_columns: list[str]=[]` (+ optional `served_columns`). | `src/autom8_asana/query/models.py:368` `RowsMeta` (`:432/:451` additive precedent) |
| One-Gate graft (extend) | Derive the column-completeness sibling field at the section-gate SITE. | `src/autom8_asana/query/engine.py:247-255` (graft point) |
| CI parity test (new) | Every declared column is servable-by-schema OR Door-C-ruled; else build-RED. | `tests/unit/dataframes/test_consumer_required_column_parity.py` (new) |
| Two-sided canary fixture (new) | RED arm (missing-required-column INPUT → typed signal) + GREEN arm (complete frame passes). Fixture authored by principal-engineer; RUN by S4/S9 review critic. | `tests/integration/test_fm5_required_column_contract.py` (new) |

### Data Model

**Vendored manifest** (`consumer_column_requirements.vendored.json`, SPEC §Layer-1 schema v1):
one entry per get_df call-site class — `{consumer_id, code_anchor, query_shape:{endpoint,
entity_type}, required_columns:[str], population_expectation, on_missing:"typed_incomplete"}`.

**SSOT additions** (`field_contract_maps.py`, purely additive — Phase-1 maps untouched):

```python
class DoorCDisposition(StrEnum):
    SERVABLE = "servable"          # column in served schema; consumer gets data
    WIDEN = "widen"                # receiver SHOULD widen projection (cheap, receiver-owned)
    REBIND_SEAM2 = "rebind_seam2"  # cure is a consumer rebind to another entity_type (out of scope)

# v1 ruling (ADR D3), the contract-driven subset — NOT eager PG-02 parity:
DOOR_C_RULING: dict[tuple[str, str], DoorCDisposition] = {
    ("project", "offer_id"): DoorCDisposition.REBIND_SEAM2,
    ("section", "project_gid"): DoorCDisposition.WIDEN,
}

def required_columns_for_shape(endpoint: str, entity_type: str) -> frozenset[str]:
    """Union of declared required_columns across manifest consumers for a query shape."""

def door_c_disposition(entity_type: str, column: str) -> DoorCDisposition | None:
    """The ruled disposition for a declared column, or None (→ CI build-RED: unruled gap)."""
```

`required_columns_for_shape` reads the vendored JSON (build/canary/CI input). The engine runtime
reads the **authoritative wire field** `request.required_columns` (Layer-2) — NOT the manifest —
so runtime stays decoupled from the vendored file.

### API Contracts

**Request** (additive; `RowsRequest`, `extra="forbid"` so the field must be declared):
```python
required_columns: list[str] | None = Field(
    default=None,
    description="Columns the caller INDEXES and requires present+servable. When any declared "
                "column is absent/unservable, meta.required_columns_complete is False and "
                "meta.missing_required_columns names them. Null = no contract (today's behavior).",
)
```

**Response meta** (additive sibling field; `RowsMeta`):
```python
required_columns_complete: bool = Field(
    default=True,
    description="Column analogue of honest_contract_complete. True iff every declared "
                "required column is servable (in the schema-derived served set AND materialized). "
                "Default True when no required_columns declared. DISTINCT from "
                "honest_contract_complete: a False here is a PERMANENT contract gap, NOT a "
                "transient build-in-progress — it does NOT map to 503/retry.",
)
missing_required_columns: list[str] = Field(
    default_factory=list,
    description="Declared required columns that were absent/unservable on the served frame. "
                "Empty when required_columns_complete is True.",
)
served_columns: list[str] | None = Field(
    default=None,
    description="The schema-validated served column set (SPEC §Layer-2 option-e manifest), so "
                "consumers can fail fast loudly. Null when no required_columns declared.",
)
```

### Sequence (the One-Gate graft, `execute_rows`)

1. `:145` resolve `schema = registry.get_schema(...)` (the served contract — 16 cols for project).
2. `:235` `available = set(df.columns)` (the materialized frame columns, pre-`select`-narrowing).
3. **GRAFT at `:247-255` (the One-Gate SITE), AFTER the section derivation, BEFORE building meta at `:268`:**
   ```python
   # 12.6 Column-contract completeness — the One-Gate COLUMN analogue (FM-5 ARM-B).
   # SIBLING FIELD at the SAME gate as honest_contract_complete; kept DISTINCT so a
   # PERMANENT column gap is never read as a TRANSIENT section-build gap (models.py:446 -> 503).
   required_columns_complete = True
   missing_required_columns: list[str] = []
   served_columns: list[str] | None = None
   if request.required_columns is not None:
       served_columns = valid_columns  # the schema-validated served set (:236)
       for col in request.required_columns:
           # SERVABILITY = contract (schema) AND materialization (frame). Schema gates first:
           # immune to the 100%-NULL parquet superset (premise implication #1) because the
           # 16-col PROJECT_SCHEMA — not df.columns — is the authoritative contract surface.
           if schema.get_column(col) is None or col not in available:
               missing_required_columns.append(col)
       required_columns_complete = not missing_required_columns
   ```
4. `:268` thread `required_columns_complete`, `missing_required_columns`, `served_columns` into
   `RowsMeta(...)`.

No change to `honest_contract_complete` / `honest_empty`. No new HTTP status. No second derivation
site.

## Non-Functional Considerations

### Performance
Zero-cost when `required_columns is None` (the guard short-circuits — undeclared path is byte-
identical). When declared: O(len(required_columns)) dict lookups against an in-memory schema +
set-membership; no new I/O on the serve path (the vendored manifest is read only at build/canary/CI
time, never per-request). P95 serve latency delta target: **< 1 ms** (measured by the existing
query latency test harness under the standard fixture).

### Security
No auth surface change. The new request field is data-plane only; `extra="forbid"` already rejects
unknown fields, so the field is opt-in and validated. No PII, no crypto, no new endpoint — below the
FEATURE security-gate trigger for this slice.

### Reliability
- Failure mode converted: silent narrow frame / `KeyError` → typed `required_columns_complete=False`
  + named columns (loud, retry-safe).
- The signal NEVER maps to 503 (distinct from the section boolean) — a consumer cannot be driven
  into an infinite retry on a permanent gap.
- Producer-first sequencing (SPEC round-trip step 4): the producer serves the signal before the
  monolith wires the wire field, so the field never hard-fails a live consumer.

## Implementation Guidance

- Extend the SSOT **additively** — Phase-1 `DTYPE_MAP`/`FIELDCLASS_MAP`/parity check are untouched.
  Keep the consumer-manifest derivation in `field_contract_maps.py` (sole propagation point); the
  vendored JSON is a sibling data file in `contracts/`.
- `DoorCDisposition` via `enum.StrEnum` (py3.11+), fully typed; `required_columns_for_shape` returns
  `frozenset[str]`; no `Any` on the new surface (mypy --strict clean).
- The freshness guard mirrors the existing dtype-parity test pattern
  (`tests/unit/dataframes/test_field_contract_parity.py`) — a pure CHECK, **not** codegen.
- Do NOT touch `resolution/gfr/` (the spine), `_resolve_identity_plan_async`,
  `assert_rows_tenant_identity`, or the drop-mask monolith sites (out of repo).

## The two-sided discriminating canary (DESIGN; fixture by principal-engineer, RUN by S4/S9 critic)

Per discriminating-canary-doctrine (mode-1: test-only canary on a working surface). The RED-before is
a **deliberately-broken INPUT the live serve path correctly rejects** — NEVER a defect injected into
prod code.

- **RED arm (bites):** `POST /v1/query/project/rows` with `required_columns=["offer_id"]` against
  the real `entity_type=project` shape. `offer_id ∉ PROJECT_SCHEMA` (`schemas/project.py:46-54`) →
  assert `meta.required_columns_complete is False` AND `meta.missing_required_columns == ["offer_id"]`
  AND HTTP **200** (NOT 503, NOT KeyError, NOT silent). Deterministic; immune to the null parquet
  because servability gates on the schema.
- **GREEN arm (passes):** same shape with `required_columns=["status"]` (a column IN
  `PROJECT_SCHEMA`) → assert `meta.required_columns_complete is True` AND
  `meta.missing_required_columns == []`. The discriminator is PURELY the column dimension; hold the
  section manifest constant (section-complete) across both arms so only the column varies.
- **Teeth (two-sided):** the canary bites ONLY on the broken input; the no-defect variant passes —
  satisfying the G-THEATER + discriminating-canary doctrine. The S9 integrated canary additionally
  reads a FRESH offer_id-bearing frame (R2 false-green guard) for the ARM-A side.

## Strictly-additive proof plan (f)

| Invariant | Proof | Receipt anchor |
|---|---|---|
| 105 GFR spine GREEN | `pytest tests/` full run; FM-5 surface (`query/`, `dataframes/contracts/`) is DISJOINT from `resolution/gfr/` | spine at `resolution/gfr/guard.py:183`, `engine.py:98` — untouched |
| `assert_rows_tenant_identity` RED-on-bypass intact | the GFR tenant round-trip integration test still RED on bypass | `tests/integration/test_gfr_tenant_roundtrip.py` |
| `_resolve_identity_plan_async` frozen | no edit under `resolution/gfr/` | `resolution/gfr/engine.py:98` |
| Additive request/response | new fields default None/True/empty under `extra="forbid"`; undeclared path byte-identical | `query/models.py:277` (RowsRequest), `:371` (RowsMeta) |
| WARN-first drift gate, NO codegen | the consumer-manifest derivation is a parity CHECK; no schema generated from a model | mirrors `tests/unit/dataframes/test_field_contract_parity.py`; ADR-S4-001 honored |
| mypy --strict + arch clean | typed enum + `frozenset[str]` returns; no `Any` | new SSOT surface |

**Full local gate before push** (GFR floor is narrower than CI): `mypy --strict` + `tests/` + `arch/`,
format with `uvx ruff@0.15.4 format`. Tests via `.venv/bin/python -m pytest` (NEVER `uv run`).

## EXACT build surface for principal-engineer (g)

**Mutate (5 files):**
1. `src/autom8_asana/dataframes/contracts/field_contract_maps.py` — add `DoorCDisposition`,
   `DOOR_C_RULING`, `required_columns_for_shape()`, `door_c_disposition()` (additive; Phase-1 maps
   untouched). Update `__all__`.
2. `src/autom8_asana/dataframes/contracts/__init__.py` — export the new symbols.
3. `src/autom8_asana/query/models.py` — `RowsRequest` (+`required_columns`, after `:294`);
   `RowsMeta` (+`required_columns_complete`, `missing_required_columns`, `served_columns`, after `:459`).
4. `src/autom8_asana/query/engine.py` — graft block at `:247-255` (the One-Gate SITE); thread 3
   fields into `RowsMeta(...)` at `:268-282`.
5. (Door-C WIDEN, separable/optional) `src/autom8_asana/dataframes/schemas/section.py` +
   the section extractor — add `project_gid` column populated from query context. **Gate behind its
   own commit; NOT on the keystone-canary path.** May be a fast-follow PR.

**Create (4 files):**
6. `src/autom8_asana/dataframes/contracts/consumer_column_requirements.vendored.json` — the vendored
   seed (offer_id/project + project_gid/section entries per SPEC §Layer-1).
7. `tests/unit/dataframes/test_consumer_manifest_freshness.py` — freshness guard (CI-loud drift).
8. `tests/unit/dataframes/test_consumer_required_column_parity.py` — CI parity: every declared
   column is servable OR Door-C-ruled, else build-RED.
9. `tests/integration/test_fm5_required_column_contract.py` — the two-sided canary fixture (RED +
   GREEN arms above). Fixture authored here; the AUTHORITATIVE RUN is the S4/S9 rite-disjoint critic.

**mypy --strict implications:** `StrEnum` (py3.11+); `door_c_disposition` returns `| None`; the
engine graft introduces only `bool`/`list[str]`/`list[str]|None` locals. No `Any`. **arch:** the
SSOT stays a leaf under `dataframes/contracts/`; the engine depends inward on the SSOT (Dependency
Rule preserved — `query/` → `dataframes/contracts/`, never the reverse).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Folding column-gap into `honest_contract_complete` corrupts 503/retry logic | M | High | D2 sibling FIELD; explicit DISTINCT-from-503 doc at the graft + `models.py` field |
| Servability check fooled by 100%-NULL parquet `offer_id` | M | High | Schema gates first (D3: no widen of project→offer_id); `schema.get_column` is the authoritative surface, NOT `df.columns` |
| CI parity reds on the (intentionally unservable) `offer_id/project` entry | M | Med | Door-C ruling makes REBIND_SEAM2 a VALID disposition; parity asserts typed-refusal behavior, not servability, for ruled columns |
| Scope creep into SEAM-2 / population enforcement | M | Med | Population designed-but-deferred; `project_gid` WIDEN separable; SEAM-2/denylist/DEFER-1 watch-register only |
| 4xx envelope hard-fails live consumers on monolith wire-up | L | High | D2 rejects 4xx; 200-meta + producer-first sequencing (SPEC step 4) |

## ADRs
- `.ledge/decisions/ADR-fm5-armb-required-column-contract-locus-2026-06-26.md` (D1/D2/D3 + OPERATOR-SURFACE).

## Open Items (for design-lock ratification, NOT implementation blockers)
- **OPERATOR-SURFACE**: ratify REBIND (D3) vs WIDEN (D3-B) for `offer_id` (recommend REBIND).
- `verification_deadline` operator-confirm (telos Gate A) before S3 build per the shape.
- `project_gid` WIDEN: confirm in-scope-this-PR vs fast-follow (recommend separable commit).
- Population-dimension (`population_expectation`) runtime enforcement: confirm deferred to fast-follow.
