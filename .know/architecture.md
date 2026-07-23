---
domain: architecture
generated_at: "2026-07-23T14:56:44Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./mcp/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "70d45434e1e79ce7bc380936e47a4e265447ffd4db88dc37cd8b37edc70b862f"
confidence: 0.72
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "62e88f60226e924b7fc0298605ce934fc6c36a3b4090ed524a4ef0d3cc4a05ff"
---

# Codebase Architecture

> Fresh full-observation pass at synced HEAD `d0c8b662` (2026-07-23). Covers both `src/autom8_asana/**` (FastAPI service + SDK, 564 .py) and the NEW top-level `mcp/**` island (asana-mcp-v1 sidecar, 48 .py, shipped 2026-07-20, unified under `mcp/` per #242 — `src/asana_mcp/` and `tests/asana_mcp/` are gone). This pass also closes four long-standing whole-package omissions never covered before — `domain/`, `normalizer/`, top-level `contracts/`, and `resolution/gfr/` — and updates the MCP section for the modular `tools/` breakdown, `list_report_workflows` (#268), and the RB-1 confirm-before-firing gate (#263).

## Package Structure

The `autom8_asana` package lives under `src/autom8_asana/` — a large Python 3.12 async-first Asana SDK + FastAPI service, **26 top-level packages**. Plus a structurally separate `mcp/` root (the sidecar).

### Root-Level Coordination Files (`src/autom8_asana/`)

`client.py` (`AsanaClient` facade), `entrypoint.py` (dual-mode ECS/uvicorn vs Lambda/awslambdaric), `config.py` (frozen-dataclass SDK config), `settings.py` (`Settings` + `get_settings()` pydantic-settings singleton), `errors.py` (top-level SDK error hierarchy), `storage_namespace.py` (the 12-namespace `StorageNamespaceContract` S3 SSOT — see Key Abstractions).

### Package Inventory

**Unchanged from prior observation** (accurate, re-verified): `_defaults/`, `api/`, `api/routes/`, `automation/`, `batch/`, `cache/`, `clients/`, `core/`, `dataframes/`, `lambda_handlers/`, `lifecycle/`, `metrics/`, `models/`, `observability/`, `patterns/`, `persistence/`, `protocols/`, `query/`, `reconciliation/`, `search/`, `services/`, `transport/`.

**`auth/`** [CORRECTED — 7 files, not 5]: `bot_pat.py`, `jwt_validator.py`, `dual_mode.py`, `service_token.py`, `audit.py`, plus:
- `business_token.py` — per-business token minter for the grain-bridge leads consumer; hand-built exchange client over `POST /tokens/exchange-business` (NOT the pinned `autom8y-auth` TokenManager, whose exchange sends an empty body). `requested_scopes` frozen to `["data:read"]` per mint.
- `per_business_provider.py` — `PerBusinessTokenProvider`, an anti-IDOR `AuthProvider` wrapping exactly ONE minted single-tenant token per business; never reused across tenants.

**`domain/`** [NEW] (2 files, 522 lines) — Pure domain logic, zero infrastructure deps (DIP):
- `forwarding_stage.py` (365 lines) — `ForwardingStage` StrEnum (`Sent→Approved→Verified→Stalled→Flowing→Live` + `Inactive`); reconciles the human-onboarded Asana custom-field vocabulary with the EBI `ReceiptKind` machine lifecycle as an asserted-by-test contract. `StageTransitionValidator` enforces never-downgrade / fail-closed / idempotence.
- `forwarding_stage_backfill.py` (157 lines) — pure evidence→stage `derive_stage` for the S4 backfill.

**`normalizer/`** [NEW] (2 files, 715 lines) — Phase-2 ACL for the legacy `CustomCalUrl` scheduling cascade:
- `scheduling_stratum.py` (358 lines) — pure, side-effect-free resolver; declarative first-non-empty-wins walk over 8 provider fields (`CASCADE_PRIORITY` is data, not branch logic). Zero I/O/persistence/concurrency/mutation.
- `scheduling_extractor.py` (364 lines) — the I/O boundary; reads the 8 provider source values via GFR's by-name resolution (`resolution/gfr/resolve_async`).

**`contracts/`** [NEW, top-level — distinct from `models/contracts/`] (1 file, 101 lines):
- `vocabulary_sync.py` — typed cross-repo envelope (`VocabularySyncRequest`) for the dynamic enum-option-set sync (producer=autom8y-asana, consumer=autom8y-data). Three locks: `field_key: Literal["vertical"]` + `extra="forbid"` (Lock-2); `vertical_key = normalize(option.name)` portable key never a GID (Lock-3); `enabled` for drift-observability only. Deliberately zero internal imports (`[PROPOSE — promote to autom8y-core]`).

**`resolution/gfr/`** [NEW, subpackage of `resolution/`] (8 files, ~1725 lines) — GID Field Resolver: gid-first, field-declarative READ facade:
- `__init__.py` — ONE public verb `resolve_async(gid, fields) -> ResolvedFields`. Hides entity-tree topology entirely (topology types not re-exported).
- `engine.py` (325 lines) — 7-step spine: plan → entry (single accounted Asana-API read: hydrate + type-detect + parent-walk to Business gid) → guard (identity-path purity) → identity-read (GID-EXACT `RowsRequest`, `join=None`) → posture (per-field provenance) → optional tier-2 verification → cardinality (`AmbiguousCardinalityError` on `row_count != 1`). Cache-only hard line: all Asana-API reads happen in the entry phase; a downstream cache miss returns `UnresolvedError` with zero further API calls.
- `dynvocab.py`/`dynvocab_overrides.py` — by-name field resolution (case/space/underscore-insensitive). `models.py` (`FieldWithProvenance`, `ResolvedFields`). `errors.py` (`UnresolvedError`, `AmbiguousCardinalityError`, closed-vocab `UNRESOLVED_REASONS`). `guard.py`, `planner.py`, `posture.py`, `entry.py`, `truth_source.py` support the spine.

## MCP Sidecar Surfaces (asana-mcp-v1)

v1 SHIPPED 2026-07-20; a REFERENCE-POSTURE throwaway POC island under `mcp/`, unified since #242. A FastMCP process (NOT a FastAPI route table). Speaks HTTP only to the satellite's own S2S surface — never imports the `autom8_asana` domain SDK, makes zero direct Asana API calls (constraint 5). Participates in ZERO of semgrep / mypy-strict / coverage / CI-test-collection (see Design Constraints + Test Coverage domains).

**`mcp/asana_mcp/server.py` `create_server()`** registers **6 read tools** via the modular `tools/` package:
- `tools/discovery.py` — `list_entity_types`, `describe_entity` (thin tier)
- `tools/query.py` — `query_rows`, `query_aggregate` (rich native tier; proxies satellite `/v1/query`)
- `tools/resolve.py` — `resolve_entity` (proxies `/v1/resolve/{entity_type}`)
- `tools/workflows.py` [NEW — #268] — `list_report_workflows`: PURE read/disclosure tool reading the live `GET /api/v1/workflows` oracle. Deliberately does NOT expose invocation (`POST /api/v1/workflows/{id}/invoke` is a declared write-verb that uploads/deletes Asana attachments and can re-fire a consuming listener — SCAR-CANDIDATE-PLAY-CONSUMED-TRIGGER).
- `tools/_match_business_stub.py` — tool 6, deliberately NOT registered.

**`tools/composite_write.py`** — `asana_complete_tagged_task`, the sole write path; requires `ASANA_MCP_ENABLE_WRITE_SURFACE` (default OFF) AND, since #263, a two-phase confirm-token exchange for `add_tag`. Consumes `tools/tag_resolve.py` (dual-key `gid|name` resolver, #249).

**`tools/confirm_gate.py` (211 lines) [NEW — #263, RB-1 gate, ruling R5/R21]**: two-phase confirmation, transport-agnostic. A call WITHOUT `confirmation_token` performs zero backend calls and returns a `confirmation_required` envelope carrying a single-use, TTL-bounded (600s), intent-fingerprint-bound token; a call with the token and byte-identical intent executes the composite chain. In-process store (`DEFAULT_MAX_PENDING=32`); restart clears pending confirmations (fails safe). V1 posture: ALL tags treated trigger-capable (no narrowing allowlist — deliberately unowned).

**`mcp/asana_mcp/bridge.py`** — mints S2S JWTs via the fleet `autom8y_core.TokenManager` (lazy-imported for import-safety, C9a). #264 fail-clean-on-401 (`_classify_mint_failure`): distinguishes `InvalidServiceKeyError` (→ `McpToolError kind=auth, 401, non-retryable, S2S_MINT_CREDENTIALS_INVALID`) from auth-infra-down (→ `kind=server, 503, retryable`), by exception-class-name across the MRO (no live `autom8y_core` import). Readiness gate is fail-closed (proxies satellite `/ready`).

`mcp/tests/` is ~24 files (`test_confirm_gate_rb1.py`, `test_bridge_401_fail_clean.py`, `test_workflows_disclosure.py`, `test_errors_c3.py`, etc.). Root CI collects none of it.

## Layer Boundaries

```
ENTRY POINTS ─ entrypoint.py, api/main.py, lambda_handlers/, query/__main__.py, autom8_query_cli.py, mcp/serve_stdio.py
        ↓
API LAYER (api/) ─ Routes, middleware, DI, OpenAPI enrichment
        ↓
SERVICE LAYER (services/) ─ Business logic; lifecycle/, automation/, query/, persistence/
        ↓
DOMAIN LAYER (models/, dataframes/, resolution/ incl. gfr/, reconciliation/, domain/ [pure])
        ↓
INFRASTRUCTURE (clients/, transport/, cache/, batch/, normalizer/ [extractor half])
        ↓
CROSS-CUTTING (core/, protocols/, observability/, patterns/, contracts/, auth/)
        ⟂  mcp/ (out-of-tree sidecar; HTTP-only consumer of the API layer, zero domain-SDK coupling)
```

**Import direction**: `api/routes/*` → `services/*` → `clients/*` → `transport/*`. `resolution/gfr/` is a leaf-facing sub-layer within `resolution/`; `normalizer/scheduling_extractor.py` → `resolution/gfr/resolve_async` is the only cross-package consumer found. `domain/` packages are pure (zero infrastructure imports, the purest leaves). The semgrep layer rules (`.semgrep.yml`) enforce this only for 19 of 26 non-`api` packages — `auth/`, `contracts/`, `domain/`, `lambda_handlers/`, `normalizer/`, `reconciliation/` are NOT in the include list (see Design Constraints TENSION-014).

**Layer boundary violation (TENSION-002)**: services import request/response models from `api/routes/*_models.py` — now **5 files** (added `services/receipts_service.py:40`).

**Structural-invariant enforcement**: `tests/arch/test_namespace_contract.py` (t1-t5, StorageNamespaceContract) makes the S3-prefix layering a compile-time-adjacent invariant.

**Hub packages**: `core/entity_registry.py`, `protocols/cache.py`, `settings.py`, `models/task.py`, `api/models.py`, `cache/integration/factory.py`, `storage_namespace.py`. **Leaf packages**: `core/` utilities, `protocols/*`, `models/base.py`, `resolution/gfr/` public surface, `normalizer/scheduling_stratum.py` (import-pure), `domain/*`.

## Entry Points and API Surface

### Primary Entry Points
- **ECS (uvicorn)**: `entrypoint.py:main()` → `run_ecs_mode()` → `_bootstrap.bootstrap()` → `uvicorn.run("autom8_asana.api.main:create_app", factory=True)`.
- **Lambda (awslambdaric)**: `entrypoint.py:main()` → `run_lambda_mode(handler)`.
- **MCP stdio**: `mcp/serve_stdio.py` (stdio launcher, `--smoke` inventory).

### Router Inventory (26 routers, 4 dual-mounted) [CORRECTED — was 24]
The prior 24-row table plus two rows: `tags_router` (PAT, `/api/v1/tags`, list + `?name=` resolve to GID, #246) and `receipts_router` (S2S, `POST /v1/receipts`, EBI OI-2 forwarding-receipt threading a lifecycle receipt as an Asana comment on the Business task). CRITICAL mount order unchanged: `fleet_query_router_*` and `exports_router_*` before `query_router`'s wildcard (`_assert_fleet_query_mount_order`, `api/main.py:316`).

### Lambda Handlers (17): cache_warmer, cache_invalidate, workflow_handler, insights_export, conversation_audit, payment_reconciliation, reconciliation_runner, push_orchestrator, pipeline_stage_aggregator, story_warmer, checkpoint, cloudwatch, timeout, leads_consumer, offer_warm_amp, onboarding_walkthrough, scheduling_stratum_snapshot.

## Key Abstractions

**`AsanaClient`**, **`EntityDescriptor`** (frozen dataclass; `body_parameterized`, `default_projection` fields), **`ResolutionResult`**, **`DataFrameBuilder`**, **`CacheProvider`**, **`SavePipeline`**, **`LifecycleEngine`**, **`UniversalResolutionStrategy`**, **`PredicateNode`** — carried forward, all accurate.

**`StorageNamespaceContract`** (`storage_namespace.py`) — the 12-namespace S3 SSOT (`REGISTRY_NAMESPACE_COUNT=12`), the closest thing to a schema catalog; every S3 prefix in `src/` must route through it (t3-enforced). See db domain.

**`resolve_async` / GFR facade** (`resolution/gfr/__init__.py`) — one-verb read facade hiding entity-tree topology.

**`ForwardingStage`** (`domain/forwarding_stage.py`) — pure StrEnum vocabulary + `StageTransitionValidator`; the reconciliation contract between human Asana custom-field language and EBI's `ReceiptKind` lifecycle.

**Two-phase confirmation-token gate** (`mcp/asana_mcp/tools/confirm_gate.py`) — unconfirmed call → zero-side-effect `confirmation_required` envelope with TTL-bound intent-fingerprinted token → confirmed call with byte-identical intent → execute. In-process, restart-safe (fails closed).

**`VocabularySyncRequest`** (`contracts/vocabulary_sync.py`), **`BusinessTokenMinter`/`PerBusinessTokenProvider`** (`auth/`), **`OperatorClaims` mint** (`clients/data/_operator_mint.py`), **`DurableTaskCacheReader`** (`cache/durable_task_cache.py`) — carried forward.

## Data Flow

Pipelines carried forward: (1) API Request, (2) DataFrame Build (+3 post-build stages: null_number_recovery, post_build_population_receipt, fail_closed_write), (3) Entity Resolution (S2S), (4) Exports, (5) Startup Initialization, (6) Cache Invalidation.

### 7. GFR Resolution Pipeline
```
normalizer/scheduling_extractor.py (I/O boundary)
  → resolution.gfr.resolve_async(gid, fields)
    → plan → entry (single accounted Asana-API read; hydrate + parent-walk to Business gid)
    → guard (identity-path purity) → identity-read (GID-EXACT RowsRequest, join=None)
    → posture (per-field provenance) → optional tier-2 → cardinality check
  → ResolvedFields (per-field provenance)
```

### 8. RB-1 Confirm-Before-Firing Flow (MCP composite write)
```
asana_complete_tagged_task(no confirmation_token)
  → zero backend calls → confirmation_required envelope (TTL-bound, intent-fingerprinted, single-use)
asana_complete_tagged_task(confirmation_token, byte-identical intent)
  → composite chain: add_tag → push(PUT-save) → mark_complete
```

## External Dependencies

`autom8y-api-middleware[rate-limit]`, `autom8y-config`, `autom8y-http[otel]`, `autom8y-cache`, `autom8y-log`, `autom8y-guid`, `opentelemetry-instrumentation-httpx`, `autom8y-core>=4.2.0,<5.0.0`, `autom8y-telemetry[aws,fastapi,otlp,remote-write]`, `boto3`, `pyyaml`, `openpyxl`, `phonenumbers`. The `mcp/` island imports `httpx` directly (sanctioned TID251 exception).

## Experiential Observations (from `.sos/land/initiative-history.md`)

Cross-session corpus (18 sessions, dominant rite 10x-dev). Confirmed against code this pass: GFR procession → the materialized `resolution/gfr/` package; grain-bridge/operator-plane → `auth/business_token.py` + `clients/data/_operator_mint.py`; dyn-enum-contract → `contracts/vocabulary_sync.py`; onboarding-walkthrough → `automation/workflows/onboarding_walkthrough/`; the MCP arc → the `mcp/` island. F1a floor-gate now has real production call sites (`d11ae574`) — treat as GO-LIVE wiring (see Design Constraints LBC-017).

## Knowledge Gaps

- `resolution/gfr/dynvocab.py`/`dynvocab_overrides.py` by-name resolution algorithm not read in depth.
- `mcp/asana_mcp/tools/tag_resolve.py` (429 lines) dual-key logic not read beyond purpose.
- `mcp/tests/` exact per-file diff not individually re-verified (count-only).
- `automation/forwarding_stage_backfill/` (backfill.py, cli.py, config.py, evidence_source.py) infrastructure half not read.
- Carried gaps: `clients/data/_endpoints/*`, `automation/polling/` internals, `autom8_query_cli.py`, `reconciliation/` depth, `cache/dataframe/` build/coalescing internals, `models/business/matching/` algorithm detail.
