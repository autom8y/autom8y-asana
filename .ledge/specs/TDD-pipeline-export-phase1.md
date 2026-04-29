---
type: tdd
initiative: project-asana-pipeline-extraction
phase: 1
sprint: sprint-2
created: 2026-04-28
rite: 10x-dev
specialist: architect
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
upstream_artifacts:
  - .ledge/specs/PRD-pipeline-export-phase1.md
  - .ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md
  - .sos/wip/frames/project-asana-pipeline-extraction.md
  - .sos/wip/frames/project-asana-pipeline-extraction.shape.md
  - .sos/wip/inquisitions/phase1-orchestration-touchstones.md
downstream_consumer: principal-engineer (Sprint 3)
companion_adr: .ledge/decisions/ADR-engine-left-preservation-guard.md
verification_deadline: "2026-05-11"
rite_disjoint_attester: theoros@know
impact: high
impact_categories: [api_contract, auth, data_model]
self_ref_cap: MODERATE
---

# TDD — Phase 1 Pipeline Export Technical Design

## §1 Inception Context

### 1.1 Telos Pulse (verbatim from frame.md:15)

> "A coworker's ad-hoc request to extract actionable account lists from
> Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana
> service: there is no first-class BI export surface, and any response today
> would be a one-off script with zero reusability. This initiative transitions
> from observation (Iris snapshot) to repeatable, account-grain, CSV-capable
> data extraction codified in the service's dataframe layer."

### 1.2 PRD Reference

This TDD satisfies `.ledge/specs/PRD-pipeline-export-phase1.md` AC-1..AC-16
(L515-590). Each TDD section maps to one or more PRD acceptance criteria;
§4 Seam Location Table is the canonical mapping.

### 1.3 Spike Handoff Anchors (binding citations)

This TDD is the immediate downstream of the PRD; the PRD is the immediate
downstream of the Phase 0 spike verdict carrier. Binding spike anchors:

- **§3 verdict (HYBRID; boundary_predicate Phase 2):** `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:111` (decision: hybrid; boundary_predicate at L157-184).
- **§3 ENGINE-DESIGN-Q1 escalation (LEFT-PRESERVATION GUARD selection):** `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:227-237` — RESOLVED in companion ADR (§10 below).
- **§4 phase_2_boundary (files Phase 1 MUST NOT touch):** `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:311-321` — enforced in §11.
- **§6 phase_1_constraints (P1-C-01..P1-C-07):** `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:514-637` — each constraint mapped in §4.
- **§9 entry conditions (EC-04 binds this TDD specifically):** `.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md:801-849` — EC-04 satisfaction at §10.

### 1.4 Throughline (Phase 1 contribution)

Phase 1 ships single-entity, dual-mount, parameterized export verifiable by
Vince reproducing his original Reactivation+Outreach CSV ask by 2026-05-11.
Phase 2 cross-entity work (boundary_predicate dispatch + LEFT-preservation
guard implementation) is deferred behind the HYBRID spike verdict; this TDD
must not foreclose it.

## §2 Architecture Overview

### 2.1 High-Level Shape

```
                              dual-mount
                ┌───────────────────────────────┐
   PAT caller ──┤  pat_router  /api/v1/exports  ├─┐
                └───────────────────────────────┘ │
                ┌───────────────────────────────┐ │   shared
   S2S caller ──┤  s2s_router  /v1/exports      ├─┼── handler ──▶ ExportService
                └───────────────────────────────┘ │
                                                  │
                                                  ▼
                                       (eager pl.DataFrame)
                                                  │
                                                  ▼
                            ┌─────────────────────────────────────┐
                            │ existing engine path (unchanged)    │
                            │ engine.py:159-161 eager filter      │
                            │ (NO modification — P1-C-04)         │
                            └─────────────────────────────────────┘
                                                  │
                                                  ▼
                            ┌─────────────────────────────────────┐
                            │ identity_complete column compute    │
                            │ (route-handler / formatter helper)  │
                            │ NOT in cascade_validator (P1-C-05)  │
                            └─────────────────────────────────────┘
                                                  │
                                                  ▼
                            ┌─────────────────────────────────────┐
                            │ dedupe by (office_phone, vertical)  │
                            └─────────────────────────────────────┘
                                                  │
                                                  ▼
                            ┌─────────────────────────────────────┐
                            │ _format_dataframe_response          │
                            │  dataframes.py:111 — extended       │
                            │  branches: JSON | CSV | Parquet     │
                            │  (P1-C-06; eager-only)              │
                            └─────────────────────────────────────┘
                                                  │
                                                  ▼
                                       HTTP Response (negotiated MIME)
```

### 2.2 Layer Responsibilities

| Layer | Responsibility | Location | New / Extend / Read-only |
|---|---|---|---|
| Router (PAT) | Receive PAT-authed ExportRequest; mount under `/api/v1/exports` | `src/autom8_asana/api/routes/exports.py` (NEW) | NEW |
| Router (S2S) | Receive S2S-authed ExportRequest; mount under `/v1/exports` | `src/autom8_asana/api/routes/exports.py` (NEW) | NEW |
| Mount registration | Register both routers via RouterMount alongside FleetQuery precedent | `src/autom8_asana/api/main.py` near L414-415 | EXTEND |
| Shared handler | Validate, dispatch into engine, post-process, format | `src/autom8_asana/api/routes/exports.py` (NEW; co-located with router) | NEW |
| Engine call | Existing eager path — single-entity filter | `src/autom8_asana/query/engine.py:159-161` | READ-ONLY (P1-C-04) |
| Identity / dedupe helper | Compute `identity_complete`; dedupe by `(office_phone, vertical)` | `src/autom8_asana/api/routes/_exports_helpers.py` (NEW) | NEW |
| Format negotiation | Add CSV + Parquet branches alongside existing JSON / Polars-binary | `src/autom8_asana/api/routes/dataframes.py:111` | EXTEND (P1-C-06) |
| Predicate AST | Add additive Op enum members (BETWEEN, DATE_GTE, DATE_LTE); free-form `Comparison.field` unchanged | `src/autom8_asana/query/models.py:27-39` (Op enum only) | EXTEND (additive only; P1-C-03) |
| Date predicate compile | Lift date-operator interpretation from temporal.py to compiler | `src/autom8_asana/query/compiler.py` (read-only outside the date-op compile site; `compiler.py:53-63,192-241` is FORBIDDEN per §11) | OUT-OF-SCOPE except minimal additive op-handler block (see §5.4) |

### 2.3 Phase 2 Non-Foreclosure Posture

Every layer above is reversible at zero structural cost: the new exports
router can be removed without affecting any existing route; the
`_format_dataframe_response` extension is a 3-branch addition (per shape §2);
the Op enum extension is purely additive; the identity / dedupe helper is a
free-standing module. The Phase 2 boundary_predicate dispatch logic
(spike handoff §3:157-184) and the LEFT-preservation guard mechanism
(spike handoff §3:201-237; companion ADR §4) are NOT touched.


## §3 Component Specifications

### 3.1 Component: ExportRequest model

- **Location:** `src/autom8_asana/api/routes/exports.py` (NEW, Pydantic v2 BaseModel co-located with the route module). Reuses `PredicateNode` from `src/autom8_asana/query/models.py:112-118` (free-form union; not modified beyond Op enum additive extension per §5).
- **Public interface (Pydantic schema):**
  - `entity_type: str` — required; PRD AC-9 maps unknown values to HTTP 400 `unknown_entity_type`.
  - `project_gids: list[int]` — required, `min_length=1`; PRD §3.1.
  - `predicate: PredicateNode | None = None` — reuses existing AST; PRD §3.1.
  - `format: Literal["json", "csv", "parquet"] = "json"` — PRD §8 + AC-7.
  - `options: ExportOptions` — see §3.2.
- **Forward-compatibility decision (resolves PRD §6 P1-C-02):** Pydantic model with `model_config = ConfigDict(extra="allow")`. This admits future `predicate_join_semantics` field without breaking-change validation; satisfies PRD AC-13. Pattern (1) of PRD §6.2 chosen. Closed-enum (`extra="forbid"`) on `options` is FORBIDDEN per spike handoff §6 P1-C-02 at L533-549.
- **Dependencies consumed:** `query.models.PredicateNode` (READ-ONLY at the type-import level; the union type binding is unchanged); FastAPI / Pydantic v2 (existing).
- **Test surface:** Unit — schema validation matrix (valid request, missing required, unknown format, malformed predicate); contract — round-trip serialize/deserialize; forward-compat — author a hypothetical Phase 2 request with `options.predicate_join_semantics: "preserve-outer"` and verify it parses without error (PRD AC-13).

### 3.2 Component: ExportOptions model

- **Location:** `src/autom8_asana/api/routes/exports.py` (NEW, Pydantic v2 sub-model).
- **Public interface:**
  - `include_incomplete_identity: bool = True` — PRD §3.1 + AC-5/AC-6.
  - `dedupe_key: list[str] = ["office_phone", "vertical"]` — PRD §5.1.
  - `model_config = ConfigDict(extra="allow")` — Phase 2 reservation surface (P1-C-02 binding).
- **Test surface:** Unit — defaults populate when omitted; explicit values override defaults; unknown member admitted via `extra="allow"` and surfaces in `model_extra`.

### 3.3 Component: ExportService (shared handler)

- **Location:** `src/autom8_asana/api/routes/exports.py` (NEW, `async def export_handler` shared between PAT and S2S route registrations; both call the SAME callable).
- **Public interface:**
  ```python
  async def export_handler(
      request: ExportRequest,
      *,
      request_id: str,
      accept: str | None = None,
      ...,
  ) -> Response
  ```
- **Behavior (procedural):**
  1. Validate `entity_type` against `SchemaRegistry.get_instance().get_schema(...)` (existing surface; same lookup as `dataframes.py` path; raises domain error on unknown entity).
  2. Build a `RowsRequest`-equivalent (or call into the existing engine entry per the route's chosen seam — see §6.4) with `predicate` and `project_gids`.
  3. Receive eager `pl.DataFrame` from existing engine path at `query/engine.py:159-161` (READ-ONLY consumption per P1-C-04).
  4. Apply the identity / dedupe transformations via the helper at §3.4.
  5. Hand the resulting eager DataFrame to `_format_dataframe_response` (extended per §7) with the negotiated format selection.
- **Dependencies consumed (READ-ONLY):** `query.engine` (call surface only — NOT modified); `dataframes.SchemaRegistry`; `dataframes.py:111 _format_dataframe_response` (extended per §7).
- **Test surface:** Integration — fixture project with mixed null/non-null identity rows; assert (a) row count post-dedupe correctness, (b) identity_complete column present, (c) format selection branches reach correct MIME type. Adversarial — null-key suppression toggle (AC-5/AC-6); unknown entity type (AC-9); malformed predicate (AC-10).

### 3.4 Component: identity_dedupe helper

- **Location:** `src/autom8_asana/api/routes/_exports_helpers.py` (NEW). Module placement intentional: it lives in the route layer per P1-C-05 (extraction-time, NOT extractor-time). Source-of-truth boundary at §8 below.
- **Public interface:**
  ```python
  def attach_identity_complete(df: pl.DataFrame) -> pl.DataFrame
  def filter_incomplete_identity(df: pl.DataFrame, *, include: bool) -> pl.DataFrame
  def dedupe_by_key(df: pl.DataFrame, *, keys: list[str]) -> pl.DataFrame
  ```
- **Behavior:** All three operate on eager `pl.DataFrame` (P1-C-06 binding). `attach_identity_complete` adds boolean column `identity_complete = pl.col("office_phone").is_not_null() & pl.col("vertical").is_not_null()`. `filter_incomplete_identity` drops `identity_complete=false` rows when `include=false`. `dedupe_by_key` applies a deterministic dedupe (DEFER-WATCH-1 disposition: see §12) with a stable winner policy.
- **Test surface:** Unit — pure DataFrame transforms with fixture frames covering null/non-null identity, single/multi-pipeline collisions on same dedupe key.

### 3.5 Component: dual-mount router pair

- **Location:** `src/autom8_asana/api/routes/exports.py` (NEW) builds two router instances via the factories at `_security.py:37` (`pat_router`) and `_security.py:45` (`s2s_router`). Mounting at `src/autom8_asana/api/main.py` near L414-415 alongside the FleetQuery precedent (`fleet_query_router_v1` and `fleet_query_router_api_v1` at L414-415; verified pattern at `src/autom8_asana/api/routes/fleet_query.py:76-81`).
- **Public interface:** Two route registrations:
  - PAT: `POST /api/v1/exports/{entity_type}` — body is ExportRequest minus `entity_type` (it's the path parameter), or accepts the full body for caller convenience (architect Sprint 3 finalizes per §6.4).
  - S2S: `POST /v1/exports/{entity_type}` — same body shape; same handler.
- **Test surface:** Integration — PAT call returns 200 with PAT-token; S2S call returns 200 with JWT; same request body produces logically-identical response across both routes (PRD AC-2 + AC-3).


## §4 Seam Location Table

Every file Phase 1 touches, with modification type and the corresponding PRD acceptance criterion (and binding spike-handoff constraint) satisfied. Read-only references appear in §11 (out-of-scope).

| # | File:line | Modification | PRD AC | P1-C constraint | Notes |
|---|---|---|---|---|---|
| S1 | `src/autom8_asana/api/routes/exports.py` (NEW file) | NEW | AC-1, AC-2, AC-3, AC-12 | P1-C-01, P1-C-07 | Hosts ExportRequest/ExportOptions/export_handler + the two routers built via PAT/S2S factories. |
| S2 | `src/autom8_asana/api/routes/_exports_helpers.py` (NEW file) | NEW | AC-4, AC-5, AC-6, AC-14 | P1-C-05 | identity_complete + dedupe transforms on eager DataFrame. |
| S3 | `src/autom8_asana/api/routes/__init__.py` | EXTEND (export new router names) | AC-16 | P1-C-07 | Adds `exports_router_v1`, `exports_router_api_v1` to `__all__` + module exports (mirrors fleet_query precedent at `__init__.py:32-33,57-58`). |
| S4 | `src/autom8_asana/api/main.py` near L414-415 | EXTEND (RouterMount additions) | AC-2, AC-3, AC-16 | P1-C-07 | Two new `RouterMount(router=exports_router_v1)` and `RouterMount(router=exports_router_api_v1)` lines alongside FleetQuery mounts. Match registration-order discipline noted in main.py:407-413 comment block. |
| S5 | `src/autom8_asana/api/routes/dataframes.py:111` (`_format_dataframe_response`) | EXTEND (additive CSV + Parquet branches) | AC-4, AC-7, AC-11, AC-15 | P1-C-06 | 3-line branch addition shape per shape §2 Sprint 2. Eager-only (P1-C-06 binding). |
| S6 | `src/autom8_asana/query/models.py:27-39` (Op enum) | EXTEND (additive members BETWEEN, DATE_GTE, DATE_LTE) | (Sprint 2 additive — PRD §3.1 operators_admitted_sprint_2) | P1-C-03 | Pure additive enum extension. `Comparison.field` at L47 stays free-form string (P1-C-03 binding). |
| S7 | `src/autom8_asana/query/temporal.py` (READ for parser semantics) | READ-ONLY consumption + lift of date-string parsing helpers (`parse_date_or_relative` at L83-118) | (Sprint 2 additive) | P1-C-03 | Date operators lift INTO the predicate compile path; the temporal.py module continues to host the parsing primitives. NO restructuring of temporal.py. |
| S8 | Test surface: `tests/api/test_exports_dual_mount.py` (NEW) | NEW | AC-2, AC-3, AC-16 | P1-C-07 | Sprint 4 territory; named here so qa-adversary can locate it. |
| S9 | Test surface: `tests/api/test_exports_format_negotiation.py` (NEW) | NEW | AC-7, AC-11 | P1-C-06 | Sprint 4 territory. |
| S10 | Test surface: `tests/api/test_exports_identity_complete.py` (NEW) | NEW | AC-4, AC-5, AC-6 | P1-C-05 | Sprint 4 territory. |
| S11 | Test surface: `tests/query/test_predicate_node_date_operators.py` (NEW) | NEW | (Sprint 2 additive) | P1-C-03 | Sprint 4 territory; date operator round-trip + AST stability assertion. |

**Anchor counts**: 11 seams enumerated; 9 file:line anchors (S5 `dataframes.py:111`, S6 `models.py:27-39`, S7 `temporal.py:83-118`, S4 `main.py:414-415`, S3 `__init__.py:32-33,57-58`); plus auxiliary anchors at `_security.py:37,45` (S1), `query/engine.py:159-161` (read-only consumption — see §11), `cascade_validator.py:46-176` (read-only boundary — see §8), `models.py:47` (P1-C-03 binding — Comparison.field stays free-form — see §5). Anti-theater rubric (touchstones §2.2 line 114, "≥8 anchors"): SATISFIED.


## §5 PredicateNode Date Operator Extension

### 5.1 Design Constraint (P1-C-03 binding)

The PredicateNode AST at `src/autom8_asana/query/models.py:27-123` MUST stay shape-stable. The extension is **additive Op enum members only**. Spike handoff §6 P1-C-03 at L551-567:

> "Comparison.field stays free-form string at L47 (no entity-prefix syntax introduced); no new node types added beyond what the date-operator extension requires per shape §2 Sprint 2."

### 5.2 Op Enum Extension (file:line target)

At `src/autom8_asana/query/models.py:27-39`, append three new members to the `Op` `StrEnum`:

```python
class Op(StrEnum):
    # ... existing members EQ, NE, GT, LT, GTE, LTE, IN, NOT_IN, CONTAINS, STARTS_WITH unchanged
    BETWEEN = "between"      # value: [date_lo, date_hi] (inclusive)
    DATE_GTE = "date_gte"    # value: ISO date or relative string per temporal.parse_date_or_relative
    DATE_LTE = "date_lte"    # value: ISO date or relative string per temporal.parse_date_or_relative
```

The `Comparison` model at `models.py:42-49` is UNCHANGED. `Comparison.field` (L47) stays `str`. `Comparison.value: Any` (L49) accepts the new value shapes without schema change.

### 5.3 How temporal.py:50-74 Lifts into the Predicate Tree

Current state (verified by Read at `src/autom8_asana/query/temporal.py:40-80`): the `_interval_matches` method on a `SectionTimelineFilter` performs `since` / `until` date filtering against `interval.entered_at.date()` (L61-64). This is **isolated to the section-timeline subsystem** — it is not wired into PredicateNode.

The Sprint 2 extension lifts the **date-parsing primitive** (`temporal.parse_date_or_relative` at L83-118; verified — accepts ISO date or relative duration like `"30d"`/`"4w"`) into the predicate-compile path. The predicate AST itself does NOT gain date-aware nodes; the compile site (Sprint 3 implementation territory; see §11 forbidden-files note for engine boundaries) translates `Op.BETWEEN | Op.DATE_GTE | Op.DATE_LTE` into Polars expression-level date comparisons.

Sprint 3 implementation note (PRELIMINARY — principal-engineer finalizes location): the date-op handler block sits at the same compiler surface that currently dispatches existing operators. Sprint 3 must NOT touch `query/compiler.py:53-63` `OPERATOR_MATRIX` or `query/compiler.py:192-241 _compile_comparison` per spike handoff §4 phase_1_must_not_touch at L313-314. The principal-engineer Sprint 3 ADR addendum decides whether the additive op-handler block is a same-file insertion within an admissible window or a separate compile-helper module.

**DELTA-SCOPE ESCALATION (rite-disjoint critic surface):** This constraint is tight. The spike handoff §4:313-314 forbids `compiler.py:53-63` AND `compiler.py:192-241` — those line ranges encompass the OPERATOR_MATRIX dispatch and the `_compile_comparison` body. A purely-additive Sprint 3 implementation may need an architect-Sprint-3-ADR-addendum identifying the exact insertion site OR reframing the date-op compile as a new helper module that the route handler invokes pre-engine. **Architect recommendation to Potnia:** route this to Sprint 3 principal-engineer as an explicit pre-implementation ADR question (NOT a Sprint 2 question — Sprint 2 only commits to the AST-additive shape). This ESCALATION is surfaced per spike handoff §10 pending_critic role.

### 5.4 Backwards Compatibility with FleetQuery

`FleetQuery` at `src/autom8_asana/api/routes/fleet_query.py:76-81,224-255` consumes `PredicateNode` through the same union type. Adding three additive `Op` members is non-breaking for FleetQuery: existing FleetQuery requests do not use the new members; the discriminator `_predicate_discriminator` at `models.py:80-95` switches on dict-key shape (`and|or|not|field`), not on Op value, so no discriminator change. The `Comparison.value: Any` annotation at L49 admits the new value shapes (`[date_lo, date_hi]` for BETWEEN; ISO date string for DATE_GTE/DATE_LTE) without schema-validation regression for existing callers.

**FleetQuery test contract**: Sprint 4 qa-adversary MUST run a regression assertion that an existing FleetQuery request with operators in the original Op set (EQ, NE, GT, LT, GTE, LTE, IN, NOT_IN, CONTAINS, STARTS_WITH) returns identical results pre/post extension.

## §6 Dual-Mount /exports Router Design

### 6.1 Endpoint Contract

| Auth class | Method | Path | Handler |
|---|---|---|---|
| PAT | POST | `/api/v1/exports/{entity_type}` | `export_handler` (shared, §3.3) |
| S2S | POST | `/v1/exports/{entity_type}` | `export_handler` (shared, §3.3) |

Path naming rationale: the prefix split `/v1/{verb}/` (S2S) vs `/api/v1/{resource}/` (PAT) follows the existing platform pattern verified at `api/routes/fleet_query.py:76-81` (FleetQuery dual-mount precedent). Resource segment `exports/{entity_type}` mirrors the entity-parameterized contract; entity_type is required (PRD §3.1 + AC-9).

**Body shape:** ExportRequest body (§3.1). Two design options for entity_type carrier:

- **Option A (RECOMMENDED):** `entity_type` IN BODY only — path is `/api/v1/exports` and `/v1/exports`. Single source of truth; matches PRD §3.1 ("`entity_type` is required on every ExportRequest").
- **Option B:** `entity_type` AS PATH PARAMETER — must reconcile with body field; risk of mismatch.

This TDD selects **Option A** to eliminate path/body reconciliation risk. Final paths:

- PAT: `POST /api/v1/exports`
- S2S: `POST /v1/exports`

### 6.2 Router Construction (FleetQuery precedent)

Construction site at `src/autom8_asana/api/routes/exports.py` (NEW), mirroring `fleet_query.py:76-81`:

```python
from autom8_asana.api.routes._security import pat_router, s2s_router

exports_router_v1 = s2s_router(
    prefix="/v1/exports",
    tags=["exports", "internal"],
)

exports_router_api_v1 = pat_router(
    prefix="/api/v1/exports",
    tags=["exports"],
)

@exports_router_v1.post("", response_model=None)
@exports_router_api_v1.post("", response_model=None)
async def post_export(request: ExportRequest, ...) -> Response:
    return await export_handler(request, ...)
```

Note: the **handler implementation function is the SAME callable** invoked from both decorated registrations. This is the load-bearing dual-mount pattern; asymmetric mounting (PAT-only or S2S-only) violates P1-C-07 per spike handoff §6:624-636. AP-3 (dual-mount asymmetry per touchstones §4) is structurally precluded by sharing the handler.

### 6.3 Mount Registration in main.py

At `src/autom8_asana/api/main.py` near L414-415, add two `RouterMount` lines alongside the FleetQuery mounts:

```python
# Existing pattern at L414-415:
RouterMount(router=fleet_query_router_v1),
RouterMount(router=fleet_query_router_api_v1),
# NEW additions:
RouterMount(router=exports_router_v1),
RouterMount(router=exports_router_api_v1),
RouterMount(router=query_router),  # L416 unchanged
```

**Registration-order discipline (verified at main.py:407-413 comment block):** FastAPI matches routes in registration order. The new exports routers MUST mount BEFORE any router with a `/v1/{wildcard}` or `/api/v1/{wildcard}` path that would shadow `/v1/exports` or `/api/v1/exports`. Sprint 3 W2 verifies via integration test (no shadow); Sprint 4 qa-adversary asserts the mount order in code review.

### 6.4 Handler Body — Engine Call Surface

The handler's engine-call seam is the existing eager surface at `query/engine.py:159-161` (verified Read at L130-181: filter → optional join → total_count → pagination → column-select). Phase 1 path:

- The handler builds an existing `RowsRequest`-equivalent with `where=request.predicate`, `project_gids=request.project_gids`, `entity_type=request.entity_type`, **AND `join=None`** (P1-C-01 single-entity hard-lock — verified by reading `engine.py:163-178` join branch — Phase 1 ExportRequest has no `join` field, so the engine's join branch never fires for /exports calls).
- Result: eager `pl.DataFrame` returned to handler. NO modification to `engine.py:139-178` or `engine.py:181` per P1-C-04 (verified §11 forbidden-files list).

### 6.5 Auth Asymmetry Check (rite-disjoint critic surface)

The PRD §7.3 declares both PAT and S2S "first-class." However, the existing query router at `src/autom8_asana/api/routes/query.py` (per agent memory file note: "Query router S2S restriction prevents privilege escalation: DataFrame cache built from bot PAT may contain data exceeding individual PAT permissions") is S2S-only on a deliberate security basis.

**DELTA-SCOPE FINDING (rite-disjoint critic role):** The /exports endpoint operates on the SAME DataFrame cache as the query router (it consumes the same `query.engine` path). The same privilege-escalation argument that gates the query router to S2S-only POTENTIALLY APPLIES to /exports. **However**, the FleetQuery precedent at `fleet_query.py:76-81` is **S2S-only on BOTH mounts** (`s2s_router` for both `_v1` and `_api_v1` per the verified read of `fleet_query.py:76-81`) — i.e., FleetQuery is dual-PATH but single-AUTH (S2S).

This contradicts PRD §7.3's reading of FleetQuery as the dual-AUTH precedent. **Resolution proposal (architect surfaces to Potnia for elicitation BEFORE Sprint 3):**

- **Option (i)**: Honor PRD §7.3 verbatim. PAT mount is built via `pat_router(...)`. S2S mount is built via `s2s_router(...)`. Caller-class-distinction is preserved at the auth layer. **REQUIRES** that the data exposed via /exports does not exceed individual PAT permissions for the project_gids supplied (Sprint 3 W2 must verify the auth-scope check inside the engine's project-gid loading path — this may require an existing scope-check that already gates `dataframes.py`).
- **Option (ii)**: Match FleetQuery precedent — both mounts are S2S-only via `s2s_router(...)`. Pure-PAT callers (Vince's tooling) reach via gateway-fronted S2S forwarding. **Violates** PRD §7.3 §AC-2 ("PAT-authenticated request to the export route succeeds"); requires PRD amendment.

**Architect recommendation:** Option (i). PRD §7.3 binds the architect, and the throughline "every future PAT or S2S caller" (frame.md L33) is dispositive. The DELTA-SCOPE FINDING is that **Sprint 3 W2 MUST verify** the per-call auth-scope check is sufficient when /exports is invoked under PAT. This ESCALATION is recorded for Potnia / Vince elicitation; the TDD commits to Option (i) as the design baseline pending elicitation reversal.


## §7 Format Negotiation Surface

### 7.1 Extension Site (P1-C-06 binding)

`_format_dataframe_response` at `src/autom8_asana/api/routes/dataframes.py:111` is the canonical extension point per PRD §8.1 + spike handoff §6 P1-C-06 at L605-622. Verified Read at L111-164: the function currently has TWO branches — `_should_use_polars_format(accept)` at L138-153 (Polars JSON) and an `else` branch at L154-164 (standard JSON via `build_success_response`).

### 7.2 Branch Addition Shape

The Sprint 2 design adds TWO additional branches alongside the existing two. Total: 4 branches dispatched on `format` selector (passed through to `_format_dataframe_response` via a new optional argument or via Accept-header parse — see §7.4). Sketch:

```python
def _format_dataframe_response(
    df: pl.DataFrame,
    request_id: str,
    limit: int,
    has_more: bool,
    next_offset: str | None,
    accept: str | None,
    *,
    format: Literal["json", "csv", "parquet"] | None = None,  # NEW kwarg
) -> Response:
    # Existing pagination block at L132-136 unchanged.
    pagination = PaginationMeta(...)

    if format == "csv":
        return _format_csv_response(df, request_id)             # NEW
    if format == "parquet":
        return _format_parquet_response(df, request_id)         # NEW
    if _should_use_polars_format(accept):
        # existing block at L138-153 unchanged
        ...
    # else: existing JSON branch at L154-164 unchanged
    ...
```

Default behavior when `format=None` is preserved (Polars-or-JSON fallback). This satisfies PRD §8.1 + AC-7 (3-format matrix) while keeping the existing dataframes.py callers (FleetQuery, query_router, etc.) untouched (additive kwarg with default None).

### 7.3 CSV / Parquet Helper Implementation

CSV: reuse `pl.DataFrame.write_csv()` directly (verified pattern at `formatters.py:122-129` `CsvFormatter._write_csv`). Wrap in `Response(content=df.write_csv(), media_type="text/csv")`. NO need to import `formatters.CsvFormatter` — that class targets `RowsResponse`/`AggregateResponse` shapes; the export route operates on raw `pl.DataFrame` per P1-C-06.

Parquet: reuse `pl.DataFrame.write_parquet(buffer)` to a `BytesIO`; verify the existing builder pattern at `dataframes/builders/base.py:751-777` (`to_parquet` method) — that method writes to a Path; the Response variant writes to a BytesIO and emits with `media_type="application/vnd.apache.parquet"`. NO new dependency; Polars is already a runtime requirement.

### 7.4 Format Selector Plumbing (Query Param vs Accept Header)

PRD §8.3 admits both. **Architect decision: query parameter `?format={json|csv|parquet}` is the primary mechanism**, with Accept-header negotiation as a secondary fallback (matches existing dataframes.py:99-108 `_should_use_polars_format` pattern when `format` query param is absent).

Rationale: Vince's CSV ask (PRD §3.2 inception-anchor fixture) is more naturally expressed as `?format=csv` for BI-tool compatibility (URL-inspectable, log-greppable). The Accept-header path stays as the existing precedent for Polars-binary clients.

Default: missing `format` → JSON (PRD §8.3 + DEFER-WATCH-5; matches existing dataframes.py behavior).

### 7.5 Streaming vs In-Memory Decision (DEFER-WATCH-6 disposition)

For Phase 1: **in-memory body for all formats**. PRD §3.2 fixture (Reactivation+Outreach pipelines) is bounded by Vince's project membership (~thousands of rows), well within FastAPI default response-body memory limits. Streaming Parquet over HTTP requires chunk-encoding plus a Polars-side streaming sink; out-of-scope for Phase 1 per shape §3 PT-05 implicit (large-dataframe behavior) and DEFER-WATCH-7.

**DELTA-SCOPE NOTE (rite-disjoint critic):** if Phase 1 fixtures grow beyond ~50k rows post-deployment, the in-memory body decision must be revisited — Phase 2 streaming is a separate ADR. Recorded; not blocking for Sprint 2.

## §8 identity_complete Extraction Surface

### 8.1 Source-of-Truth (P1-C-05 binding)

The `identity_complete` column is computed at **extraction time**, in the route-handler pipeline via `attach_identity_complete` at `src/autom8_asana/api/routes/_exports_helpers.py` (NEW per §3.4). The computation is:

```python
def attach_identity_complete(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        identity_complete=(
            pl.col("office_phone").is_not_null()
            & pl.col("vertical").is_not_null()
        )
    )
```

This is the SINGLE source-of-truth for the column. PRD §5.3 + AC-14 binding.

### 8.2 NOT-Locations (HC-01 boundary preserved)

The column source-of-truth is **EXPLICITLY NOT** any of:

- `src/autom8_asana/dataframes/extractors/cascade_resolver.py` — parked SPIKE; out of scope per spike handoff §4 phase_1_must_not_touch L319.
- `src/autom8_asana/dataframes/builders/cascade_validator.py:46-176` — verified Read: this is `validate_cascade_fields_async`, the warmup-time cascade validation surface. P1-C-05 binding from spike handoff §6:587-603 plus PROTO Evidence Trail #7: cascade_validator stays warmup-time only. Adding `identity_complete` here would conflate extraction-time signal with warmup-time validation — that is the HC-01 silent-degradation risk the spike SR-01 (handoff L646-668) named.
- `src/autom8_asana/dataframes/builders/cascade_validator.py:185-191` — `_CASCADE_SOURCE_MAP` hardcoded dict. Modifying this would (a) destabilize the warmed-cache invariant per Claim 5 CONCUR (spike handoff §3 + §8 evidence row 20), (b) push the column out of extraction-time and into warmup-time. EXPLICITLY REFUSED.

### 8.3 Transparency Invariant (SCAR-005/006 throughline)

`include_incomplete_identity` defaults to `true` (PRD §3.1 + §5.3 + AC-5). Rows with `identity_complete=false` are NEVER silently dropped under the default. Caller may opt-in to suppression via `include_incomplete_identity=false` (PRD AC-6). Implementation:

```python
# In ExportService handler (§3.3):
df = attach_identity_complete(df)                    # always
df = filter_incomplete_identity(                     # opt-in suppression
    df,
    include=request.options.include_incomplete_identity,
)
df = dedupe_by_key(df, keys=request.options.dedupe_key)
```

Order matters: `attach_identity_complete` runs FIRST (so the dedup step has the flag column available); `filter_incomplete_identity` runs SECOND (transparency-respecting suppression); `dedupe_by_key` runs LAST (so the surviving row retains a valid identity_complete value).


## §9 Activity-State Predicate Wiring

### 9.1 Vocabulary Source-of-Truth

The canonical activity-state vocabulary lives at `src/autom8_asana/models/business/activity.py:282-303` (`_DEFAULT_PROCESS_SECTIONS`; verified Read at L282-303). Four classes: `active`, `activating`, `inactive`, `ignored`. Section names per PRD §4.1.

### 9.2 Caller-Supplied Subset (NOT server-hardcoded)

The activity-state filter is a **caller-supplied subset over the activity.py:282 vocabulary** (PRD §4.2 binding). The caller expresses it via the standard PredicateNode AST as a `Comparison` with `field="section"`, `op=Op.IN`, `value=[<section names>]` — exactly as PRD §3.2 fixture demonstrates.

The route handler MUST NOT:
- Inject a server-side hardcoded `section IN [...]` predicate when the caller already provides one.
- Substitute the default predicate when the caller's predicate omits the `section` field on purpose.
- Silently drop sections the caller named explicitly.

### 9.3 Default Predicate (when caller omits section filter)

When `request.predicate` is None OR `request.predicate` does not constrain `section`, the handler proposes a **caller-elective default**: ACTIVE-only (`section IN active-class-sections` per PRD §4.3 + DEFER-WATCH-3 disposition). The default is applied via predicate composition (AND-merge with caller predicate if present); the handler's response meta SHOULD echo whether the default was applied so callers can see the extension.

**DEFER-WATCH-3 disposition (architect):** RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE. The TDD ships ACTIVE-only as the engineering default, with response meta indicating the default was applied. Vince elicitation may reverse this; the implementation surface (a flag in handler config OR a request-time override) keeps the door open. Architect commits to the default; Sprint 4 qa-adversary verifies AC-8 (activity-state-parameterized predicate respect).

### 9.4 Section-Vocabulary Validation

PRD §9.2 + §AC-N (failure mode `unknown_section_value` at HTTP 400) requires that section values supplied by the caller MUST be members of the activity.py:282 vocabulary. Implementation: a validator helper in `_exports_helpers.py` that walks the predicate tree (AndGroup/OrGroup/NotGroup recursion) and flags any `Comparison` with `field="section"` whose value (or list-member) is not in `flatten(_DEFAULT_PROCESS_SECTIONS.values())`. Sprint 3 W1 territory.

## §10 ENGINE-DESIGN-Q1 ADR Reference

The ENGINE-DESIGN-Q1 escalation from spike handoff §3:227-237 (LEFT-PRESERVATION GUARD mechanism (a) PRIMARY DEFENSE vs (b) ESCAPE VALVE) is RESOLVED in the standalone companion ADR at:

**`.ledge/decisions/ADR-engine-left-preservation-guard.md`** (created concurrently with this TDD).

The ADR §4 selects **HYBRID** — mechanism (a) post-EXPLAIN assertion + anti-join restoration is the engine's default Phase 2 behavior; mechanism (b) caller opt-in via `ExportRequest.options.predicate_join_semantics` is the explicit escape valve. See ADR §4 for the binding decision and §5 for rationale.

**EC-04 satisfaction (spike handoff §9 entry condition at L831-839):** This TDD §10 + the companion ADR explicitly acknowledge the s3_s4_divergence_resolution mechanism as a Phase 2 design requirement. ENGINE-DESIGN-Q1 appears in the ADR's §6 Consequences section as a Phase 2 forward-binding constraint. Phase 1 does NOT implement either mechanism (P1-C-04 + spike handoff §3:230-232 — "Phase 1 ships single-entity export so the LEFT-rewrite question does not fire in Phase 1 proper, BUT the Sprint 1 ExportRequest contract MUST NOT foreclose either (a) or (b)"). The Phase 1 ExportRequest at §3.1 honors this via `ExportOptions.model_config = ConfigDict(extra="allow")` (mechanism (b) future-field reservation per P1-C-02).

## §11 Out of Scope (P1-C-04 enforcement)

This section is binding. The following files MUST NOT be modified by Sprint 3 implementation. Spike handoff §4 phase_1_must_not_touch at L311-321:

| # | File:line (forbidden) | Source citation | Reason |
|---|---|---|---|
| F1 | `src/autom8_asana/query/engine.py:139-178` | spike handoff §4:315 | Phase 2 C5 seam — filter+join composition. |
| F2 | `src/autom8_asana/query/engine.py:181` | spike handoff §4:316 | Phase 2 lazy-chain dependency — total_count materialization. |
| F3 | `src/autom8_asana/query/join.py` (any line) | spike handoff §4:312 | Phase 2 strong-form lazy execute_join extension. |
| F4 | `src/autom8_asana/query/compiler.py:53-63` | spike handoff §4:313 | OPERATOR_MATRIX — Path B classifier territory. |
| F5 | `src/autom8_asana/query/compiler.py:192-241` | spike handoff §4:314 | `_compile_comparison` + UnknownFieldError raise — Phase 2. |
| F6 | `src/autom8_asana/query/models.py:42-123` (Comparison body, AndGroup/OrGroup/NotGroup, PredicateNode union) | spike handoff §4:317 | PredicateNode AST — DSL stability through Phase 2 per CONSTRAINT-5. ONLY the Op enum extension at L27-39 is admitted (additive members per §5). |
| F7 | `src/autom8_asana/dataframes/builders/cascade_validator.py:185-191` | spike handoff §4:318 + §8 evidence #12 | HC-01 _CASCADE_SOURCE_MAP — only edit if new cascade field added (OUT of Phase 1 scope per P1-C-05). |
| F8 | `src/autom8_asana/dataframes/extractors/cascade_resolver.py:199-275` | spike handoff §4:319 | Cascade resolver — Phase 2 if Path A branch invoked. |
| F9 | `src/autom8_asana/reconciliation/section_registry.py` | spike handoff §4:320 | SCAR-REG-001 out-of-scope per shape §7. |
| F10 | Any file under `src/autom8_asana/dataframes/extractors/` touching CascadingFieldResolver root cause | spike handoff §4:321 | Parked SPIKE; keep parked per shape §7. |

**Read-only consumption** of the engine path is admitted: the export handler CALLS into `query.engine` at the existing eager surface (`engine.py:159-161`) but does NOT modify any line. Sprint 4 qa-adversary verifies via PT-04 git-diff guard per shape §3.

## §12 DEFER-WATCH Disposition

For each PRD §10 DEFER-WATCH item, this TDD's stance:

| ID | Item | TDD Disposition | Rationale |
|---|---|---|---|
| DEFER-WATCH-1 | Dedupe winner policy on multi-hit accounts | RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE | TDD §3.4 ships **most-recent-by-modified_at** as the engineering default (PRD §10 placeholder), implemented via `pl.DataFrame.sort("modified_at", descending=True).unique(subset=keys, keep="first")`. Vince elicitation may revise. |
| DEFER-WATCH-2 | Column projection minimum viable set | RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE | Ship PRD §5.2 minimum (`office_phone, vertical, name, pipeline_type, section, gid, identity_complete`). Sprint 3 implements; Vince Sprint 4-5 elicitation may add. |
| DEFER-WATCH-3 | ACTIVATING-state default inclusion | RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE | TDD §9.3: ACTIVE-only default; ACTIVATING is caller-elective. Server NEVER injects ACTIVATING. |
| DEFER-WATCH-4 | Null-key handling beyond the flag | RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE | Inline with flag column per PRD §5.3 + AC-5; opt-in suppression via `include_incomplete_identity=false`. Separate-CSV-section variant deferred. |
| DEFER-WATCH-5 | Format default | RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE | JSON default per PRD §8.3, matching dataframes.py precedent. Vince's CSV need is opt-in via `?format=csv`. |
| DEFER-WATCH-6 | Pagination behavior on CSV | RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE | TDD §7.5: full body for CSV (BI-tool friendly); JSON keeps existing pagination. Streaming deferred to Phase 2 ADR. |
| DEFER-WATCH-7 | Maximum result size threshold | DEFER-TO-SPRINT-3 | No cap in Phase 1 per PRD placeholder; Sprint 3 measures fixture sizes; if measurements exceed prudent-threshold, principal-engineer surfaces a Phase 1.5 ADR. Recorded as Sprint-3 watch-trigger. |

Architect commits to the engineering defaults above; Vince elicitation BEFORE Sprint 3 (per touchstones §3 PT-02 reviewer guidance) may reverse any RESOLVE-WITH-DEFAULT-FLAGGED-FOR-VINCE item.


## §13 Test Plan Skeleton

High-level test categories Sprint 4 qa-adversary will execute. Per shape §3 PT-03 gate, parameterization matrix is named here so qa-adversary can construct the matrix from the TDD without re-deriving from PRD AC.

### 13.1 Contract Tests (PRD AC-12, AC-13, AC-14, AC-15, AC-16)

- ExportRequest schema accepts/rejects per §3.1.
- ExportRequest contract has NO `join` field, NO `target_entity` field (AC-12).
- Hypothetical `options.predicate_join_semantics: "preserve-outer"` parses without error (AC-13; `extra="allow"` verification).
- Implementation inspection shows `identity_complete` computed in `_exports_helpers.attach_identity_complete`, NOT in `cascade_resolver.py` or `cascade_validator.py` (AC-14).
- No LazyFrame consumer surface exposed on `_format_dataframe_response` extension (AC-15).
- Both routers exported from `routes/__init__.py`; both mounted in `main.py:414-415` block (AC-16).

### 13.2 Dual-Mount Auth Tests (PRD AC-2, AC-3)

| Auth | Path | Expected |
|---|---|---|
| Valid PAT | `POST /api/v1/exports` | 200 with response body |
| Missing PAT | `POST /api/v1/exports` | 401 (existing PAT_BEARER_SCHEME) |
| Valid S2S JWT | `POST /v1/exports` | 200 with response body |
| Invalid S2S JWT | `POST /v1/exports` | 401 (existing SERVICE_JWT_SCHEME) |
| PAT against S2S route | `POST /v1/exports` | 401/403 (auth-class mismatch) |
| S2S against PAT route | `POST /api/v1/exports` | 401/403 (auth-class mismatch) |

Same ExportRequest body to PAT vs S2S returns logically-identical row sets (AC-2 + AC-3).

### 13.3 Format Negotiation Matrix (PRD AC-7, AC-11)

Cartesian product: `format ∈ {json, csv, parquet, missing, "xml"}` × `auth ∈ {PAT, S2S}` × `predicate ∈ {fixture-A non-empty, fixture-B empty-result}`.

Expected: 200 + correct MIME for valid; 400 `unsupported_format` for `"xml"`; default JSON for missing format. Empty-result returns 200 + empty body + `meta.row_count=0` (PRD §9.3).

### 13.4 identity_complete + Null-Key Surface Tests (PRD AC-4, AC-5, AC-6)

- Fixture with mixed (office_phone, vertical) null/non-null permutations.
- `include_incomplete_identity=true` (default): all rows present; `identity_complete=false` rows visible.
- `include_incomplete_identity=false`: `identity_complete=false` rows absent.
- Every output row in every format carries `identity_complete` column (AC-4).

### 13.5 Activity-State Parameterization Tests (PRD AC-8)

- Caller predicate `section IN [SCHEDULED, DELAYED, REQUESTED]`: response contains ONLY ACTIVATING sections; NO ACTIVE injection.
- Caller omits `section` filter: default ACTIVE-only applied; response meta surfaces this.
- Caller passes section value not in `_DEFAULT_PROCESS_SECTIONS`: 400 `unknown_section_value` (PRD §9.2).

### 13.6 Error Envelope Tests (PRD AC-9, AC-10, AC-11 + §9.2)

One test per failure-mode row in PRD §9.2 (9 rows). Verify HTTP status + `error.code`.

### 13.7 Large-Dataframe Streaming / In-Memory Behavior (DEFER-WATCH-7)

Sprint 3 measures fixture sizes; Sprint 4 verifies in-memory body returns within FastAPI default limits for the inception-anchor query. If measured fixture exceeds 50k rows, qa-adversary escalates to architect for Phase 1.5 ADR.

### 13.8 Predicate Date-Operator Regression (PRD §3.1 operators_admitted_sprint_2)

- Round-trip: ExportRequest with `op: BETWEEN`, `value: ["2026-01-01", "2026-04-01"]` parses, compiles, executes, returns expected rows from a date-bearing fixture.
- AST stability: existing FleetQuery requests with original Op set produce identical results pre/post extension (per §5.4).

## §14 Acceptance Criteria (TDD-level, beyond PRD AC)

- **TDD-AC-1**: All Sprint 3 implementation lands within seams named in §4. PT-04 git-diff guard verifies no commits to §11 forbidden files.
- **TDD-AC-2**: ENGINE-DESIGN-Q1 mechanism selection per companion ADR §4 (HYBRID) is reflected in the Phase 1 ExportOptions contract — `model_config = ConfigDict(extra="allow")` permits future `predicate_join_semantics` field addition.
- **TDD-AC-3**: Both PAT and S2S routers built via factories at `_security.py:37,45`; both mounted in `main.py:414-415` block; both invoke the same `export_handler` callable (AP-3 dual-mount asymmetry structurally precluded).
- **TDD-AC-4**: `_format_dataframe_response` extension at `dataframes.py:111` is purely additive (existing 2 branches unchanged; 2 new branches added behind a new `format` kwarg with default `None` preserving existing behavior for current callers).
- **TDD-AC-5**: `identity_complete` source-of-truth is `_exports_helpers.attach_identity_complete`. Sprint 3 grep audit: zero references to `identity_complete` outside `routes/_exports_helpers.py` and `routes/exports.py` and the new test files.
- **TDD-AC-6**: Op enum at `models.py:27-39` extended with exactly 3 additive members (BETWEEN, DATE_GTE, DATE_LTE); no other changes to `query/models.py`.
- **TDD-AC-7**: DELTA-SCOPE escalations recorded in §5.3 (compile-site question), §6.5 (PAT auth-scope question), and §7.5 (in-memory streaming question) are routed to Potnia for elicitation BEFORE Sprint 3 entry (per touchstones §3 PT-02 reviewer guidance).

## §15 DELTA-SCOPE ESCALATIONS (Rite-Disjoint Critic Surface)

Per spike handoff §10 pending_critic role, the architect surfaces the following foreclosure risks NOT anticipated by the spike verdict:

### 15.1 ESC-1 — Date-op compile site is tightly fenced (§5.3)

The §5 PredicateNode AST extension is purely additive at the Op enum, but the COMPILE site (where the new operators translate to Polars expressions) is tightly fenced by spike handoff §4:313-314 forbidding `compiler.py:53-63` (OPERATOR_MATRIX) AND `compiler.py:192-241` (`_compile_comparison`). Sprint 3 W1 needs an architect-Sprint-3-ADR-addendum identifying the precise insertion site OR reframing the compile as a route-handler-side helper that translates date-op Comparisons to filter expressions BEFORE engine call. Status: ROUTE-TO-POTNIA-FOR-SPRINT-3-ADR.

### 15.2 ESC-2 — Dual-mount auth-class assumption divergence (§6.5)

PRD §7.3 reads FleetQuery as the dual-AUTH precedent, but verified Read of `fleet_query.py:76-81` shows FleetQuery is dual-PATH/single-AUTH (S2S-only on both mounts). The TDD's Option (i) (honor PRD §7.3 verbatim — true dual-AUTH) requires Sprint 3 W2 to verify per-call auth-scope check sufficiency under PAT for /exports. Option (ii) (match FleetQuery — both mounts S2S-only) violates PRD AC-2. Status: ROUTE-TO-POTNIA-FOR-VINCE-ELICITATION.

### 15.3 ESC-3 — Large-dataframe in-memory threshold (§7.5)

DEFER-WATCH-7 placeholder is "no cap in Phase 1." TDD §7.5 commits to in-memory bodies for all formats. If Phase 1 fixture sizes exceed ~50k rows post-deployment, the in-memory decision becomes load-bearing. Status: SPRINT-3-MEASURE; SPRINT-4-VERIFY; PHASE-1.5-ADR-IF-EXCEEDED.

## §16 Self-Verification Handoff Criteria

- [x] TDD covers all PRD §11 acceptance criteria AC-1..AC-16 (mapped in §4 + §13).
- [x] Component boundaries clear (§3 four components named with file:line).
- [x] Data model defined: ExportRequest + ExportOptions + ExportResponse (PRD §5.4 envelope; format-negotiated body per §7).
- [x] API contracts specified (§6 endpoint contract + §7 format negotiation).
- [x] ADR cited at §10; standalone ADR at `.ledge/decisions/ADR-engine-left-preservation-guard.md`.
- [x] Risks identified with mitigations (§15 DELTA-SCOPE escalations + §11 forbidden files).
- [x] Principal Engineer can implement without architectural questions UNLESS one of §15 escalations resolves Vince elicitation reversal — those are explicitly routed to Potnia.
- [x] All artifacts verified via Read tool (PRD §1 verbatim citation; spike handoff §3/§4/§6/§9 verbatim citations; source seams models.py:27-123, temporal.py:40-118, dataframes.py:85-164, _security.py:15-50, main.py:405-429, fleet_query.py:64-81, formatters.py:110-129, base.py:740-797, engine.py:130-189, cascade_validator.py:40-69, activity.py:275-309 all directly inspected).
- [x] Telos pulse quoted verbatim (§1.1).
- [x] Spike handoff cited path:line ≥ 6 times across this TDD: §1.3 (verdict L111; ENGINE-DESIGN-Q1 L227-237; phase_2_boundary L311-321; phase_1_constraints L514-637; entry conditions L801-849); §11 (each F-N row); §10 (EC-04 L831-839); §15 (pending_critic role).
- [x] Zero pending markers.

## §17 Attestation Table

| Artifact | Absolute path | Role |
|---|---|---|
| This TDD | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-pipeline-export-phase1.md` | Phase 1 technical design (Sprint 2 exit artifact) |
| Companion ADR | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/decisions/ADR-engine-left-preservation-guard.md` | ENGINE-DESIGN-Q1 resolution |
| PRD | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-pipeline-export-phase1.md` | Sprint 1 contract (input to this TDD) |
| Spike handoff | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md` | Phase 0 verdict carrier (binding constraints + ENGINE-DESIGN-Q1 escalation) |
| Frame | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/frames/project-asana-pipeline-extraction.md` | Telos source-of-truth (L15) |
| Shape | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/frames/project-asana-pipeline-extraction.shape.md` | Sprint procession |
| Touchstones | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/inquisitions/phase1-orchestration-touchstones.md` | Anti-pattern guards |

End of TDD. Zero pending markers. Sprint 2 exit-artifact criteria satisfied per shape §2 Sprint 2 exit_criteria; PT-03 hard-gate evidence covered at §3-§9 (component designs + file:line anchors), §5 (PredicateNode AST stability), §6 (dual-mount with FleetQuery precedent), §7 (format negotiation extension), §8 (identity_complete source-of-truth at extraction time, NOT in cascade resolver/validator), §10 (ENGINE-DESIGN-Q1 explicitly acknowledged + companion ADR), §11 (engine seam isolation forbidden-files list), §15 (rite-disjoint critic DELTA-SCOPE surfaces).
