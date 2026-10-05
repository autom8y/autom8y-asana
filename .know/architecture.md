---
domain: architecture
generated_at: "2026-10-05T03:00:53Z"
expires_after: "7d"
source_scope:
  - "./src/autom8_asana/__init__.py"
  - "./src/autom8_asana/client.py"
  - "./src/autom8_asana/config.py"
  - "./src/autom8_asana/entrypoint.py"
  - "./src/autom8_asana/errors.py"
  - "./src/autom8_asana/settings.py"
  - "./src/autom8_asana/storage_namespace.py"
  - "./mcp/asana_mcp/__init__.py"
  - "./mcp/asana_mcp/assembly.py"
  - "./mcp/asana_mcp/bridge.py"
  - "./mcp/asana_mcp/context.py"
  - "./mcp/asana_mcp/envelopes.py"
  - "./mcp/asana_mcp/errors.py"
  - "./mcp/asana_mcp/observability.py"
  - "./mcp/asana_mcp/schemas.py"
  - "./mcp/asana_mcp/server.py"
  - "./mcp/asana_mcp/settings.py"
  - "./mcp/asana_mcp/timeouts.py"
  - "./mcp/canary/test_broken_fixture_canary.py"
  - "./mcp/probes/c2_sandbox_reput_probe.py"
  - "./mcp/tests/conftest.py"
  - "./mcp/tests/test_assembly_floor.py"
  - "./mcp/tests/test_bridge_401_fail_clean.py"
  - "./mcp/tests/test_budget_partition_and_rate_cap.py"
  - "./mcp/tests/test_cold_frame_mapping.py"
  - "./mcp/tests/test_composite_write_s3.py"
  - "./mcp/tests/test_confirm_gate_rb1.py"
  - "./mcp/tests/test_discovery_tools.py"
  - "./mcp/tests/test_errors_c3.py"
  - "./mcp/tests/test_errors_passthrough.py"
  - "./mcp/tests/test_errors_substrate_424.py"
  - "./mcp/tests/test_fences.py"
  - "./mcp/tests/test_honesty_passthrough.py"
  - "./mcp/tests/test_import_safety_obs.py"
  - "./mcp/tests/test_import_safety.py"
  - "./mcp/tests/test_instrument_seam.py"
  - "./mcp/tests/test_postures.py"
  - "./mcp/tests/test_query_tools.py"
  - "./mcp/tests/test_readiness_gate.py"
  - "./mcp/tests/test_resolve_tool.py"
  - "./mcp/tests/test_schema_canary.py"
  - "./mcp/tests/test_seam_conformance.py"
  - "./mcp/tests/test_span_and_traceparent.py"
  - "./mcp/tests/test_tag_dual_key_wsb2.py"
  - "./mcp/tests/test_timeout_cascade_invariant.py"
  - "./mcp/tests/test_workflows_disclosure.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "6a8debe2b2650bf405b8e8a3a03e3c969e935410abcd9c5b1c21410fbd76784d"
confidence: 0.80
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@c29f58f4"
land_sources:
  - ".sos/land/initiative-history.md"
land_hash: "62e88f60226e924b7fc0298605ce934fc6c36a3b4090ed524a4ef0d3cc4a05ff"
---

# Codebase Architecture

> Fresh full-observation pass at `origin/main` `c29f58f4` (observed in a detached worktree; all `path:line` cites are relative to the worktree root). Covers `src/autom8_asana/**` (FastAPI service + SDK + Lambda handlers: **610 .py files, 29 top-level packages, 7 root modules**) and the `mcp/**` island (asana-mcp-v1 sidecar: 50 .py incl. tests/canary/probes). Import-graph claims below were computed by an AST walk of every file in `src/autom8_asana` (top-level vs function-local vs `TYPE_CHECKING` imports classified separately); they are measurements, not impressions. Three whole packages are new since the 2026-07-23 pass: `substrate/`, `enrollment/`, `readout/`.

## Package Structure

`autom8_asana` is a Python 3.12 async-first Asana SDK + FastAPI service (`pyproject.toml:1-12`, `requires-python >=3.12`), built with hatchling and packaged as `src/autom8_asana` + the stand-alone `src/autom8_query_cli.py` (`pyproject.toml` `[tool.hatch.build.targets.wheel]`). One console script: `autom8-query = autom8_query_cli:main` (`pyproject.toml` `[project.scripts]`).

### Root modules (`src/autom8_asana/`)
- `__init__.py` — public SDK facade; `__all__` has 83 names; dataframe symbols are lazy-loaded (`_DATAFRAME_EXPORTS`, `__init__.py:25-30`) so polars is not pulled for client-only consumers.
- `client.py` (1118 lines) — `AsanaClient` facade (`client.py:98`); lazy resource-client properties `tasks/projects/sections/custom_fields/users/workspaces/webhooks/teams/attachments/tags/goals/portfolios/stories/batch/search/unified_store` (`client.py:388-743`).
- `entrypoint.py` — dual-mode ECS/Lambda launcher (`entrypoint.py:34,60,75`).
- `settings.py` (1139 lines) — `Settings(Autom8yBaseSettings)` (`settings.py:974`) composed of 13 nested `*Settings` classes (`AsanaSettings`, `CacheSettings`, `RedisSettings`, `S3Settings`, `PacingSettings`, `RateLimitSettings`, `BudgetAllocatorSettings`, `S3RetrySettings`, `DataServiceSettings`, `ObservabilitySettings`, `RuntimeSettings`, `WebhookSettings`, `ProjectOverrideSettings`); `get_settings()` singleton at `settings.py:1096`, `reset_settings()` at `:1116`. **Gotcha:** a *second, unrelated* `get_settings()` exists in `api/config.py:173` returning `ApiSettings` (`api/config.py:36`); callers must pick the right one (`forwarding_stage_census.py:61` and `receipts.py:52` use the API one).
- `config.py` (1034 lines) — frozen-dataclass SDK config (`RateLimitConfig`, `RetryConfig`, `ConcurrencyConfig`, `TimeoutConfig`, `ConnectionPoolConfig`, `CircuitBreakerConfig`, `S3LocationConfig`, `DataFrameConfig`, mutable `CacheConfig`, `BudgetAllocatorConfig`; `config.py:319-831`).
- `errors.py` (604) — `AsanaError` hierarchy (`errors.py:42`; `AuthenticationError`, `NotFoundError`, `RateLimitError`, `CircuitBreakerOpenError`, `Insights*`, `ExportError`, `OperatorTokenError`, ...). `from autom8_asana.errors import` is the single most widely imported module in the tree (54 files).
- `storage_namespace.py` (630) — `StorageNamespaceContract` S3 SSOT, see Key Abstractions.

### Package inventory (files / lines, measured)

| Package | Files | Lines | Role |
|---|---|---|---|
| `api/` (+`routes/`, `middleware/`, `preload/`) | 63 | 22175 | FastAPI app: factory, lifespan, DI, 28 router mounts, middleware, rate limit, write-authz, status push |
| `automation/` (+`workflows/`, `events/`, `polling/`, `forwarding_stage_backfill/`) | 69 | 19877 | Rules engine, `WorkflowAction` implementations, polling scheduler, forwarding-stage backfill |
| `dataframes/` (+`builders/ extractors/ schemas/ resolver/ views/ models/ contracts/`) | 66 | 21562 | Schema-driven polars frame construction; progressive section builder; S3 section persistence |
| `cache/` (+`backends/ dataframe/ integration/ models/ policies/ providers/`) | 55 | 17513 | Task cache (Redis/memory/S3 backends), DataFrame cache (memory+progressive tiers), coalescing, breakers, invalidation |
| `models/` (+`business/`, `business/detection/`, `business/matching/`) | 61 | 16889 | Pydantic Asana resources + Business/Unit/Offer/Contact hierarchy, 4-tier entity detection, Fellegi-Sunter matching |
| `clients/` (+`data/`, `data/_endpoints/`) | 42 | 14271 | Per-resource Asana clients + `DataServiceClient` (autom8_data) incl. operator-token mint |
| `services/` | 29 | 13905 | Business logic behind routes and lambdas |
| `persistence/` | 20 | 8118 | `SaveSession` unit-of-work: tracker → graph → 5-phase `SavePipeline` → action executor |
| `lambda_handlers/` | 21 | 8287 | 11 independently-deployable handlers + support modules (see Entry Points) |
| `substrate/` **[NEW]** | 12 | 5520 | substrate-v2: five frozen seam contracts for provable-fresh served numbers |
| `lifecycle/` | 18 | 5550 | Stage-transition `LifecycleEngine` + activation smoke gate |
| `core/` | 20 | 4356 | Entity registry, retry orchestrator, errors, scope, warm deadline, system-context resets |
| `metrics/` | 14 | 3970 | Metrics CLI/compute, freshness signal, SLA profile persistence, rebuild gate |
| `resolution/` (+`gfr/`) | 19 | 3805 | Entity resolution strategies + GFR read facade |
| `query/` | 19 | 6248 | Predicate compiler, `QueryEngine`, joins, aggregation, offline CLI |
| `observability/` (+`rail_delivery/`, `rung_receipts/`) | 15 | 2330 | Correlation/decorators + EX-4/EX-6 receipt schemas (new subpackages) |
| `transport/` | 7 | 2316 | HTTP layer over `autom8y_http`, AIMD semaphore, F1a budget allocator |
| `reconciliation/` | 6 | 1604 | Unit↔offer activity reconciliation processor + section registry |
| `enrollment/` **[NEW]** | 3 | 1167 | WS-A enrollment-intent → scheduling-gate projection + governed write client |
| `auth/` | 8 | 1118 | PAT/JWT dual mode, service-token validation, per-business token mint |
| `_defaults/` | 5 | 1016 | Default env/secrets-manager auth, cache, log, observability providers |
| `protocols/` | 9 | 918 | `typing.Protocol` seams (cache, auth, dataframe provider, log, metrics, ...) |
| `search/` | 3 | 914 | `SearchService` over cached project frames |
| `normalizer/` | 3 | 844 | Scheduling-stratum ACL (pure resolver + I/O extractor) |
| `readout/` **[NEW]** | 4 | 790 | Recurring exec readout (item-1a) generation |
| `batch/` | 3 | 672 | Asana Batch API client |
| `patterns/` | 3 | 445 | `async_method` generator, error classification |
| `domain/` | 3 | 549 | Pure forwarding-stage vocabulary |
| `contracts/` | 2 | 114 | Cross-repo vocabulary-sync envelope (distinct from `models/contracts/`) |

Hub/leaf classification is derived from the measured graph (next section), not from naming.

### Packages new or materially changed since the prior pass

**`substrate/`** — "Substrate-v2 — the five FROZEN seam contracts (v1.0-frozen-2026-07-29)", built DARK beside v1's `dataframes/` (`substrate/__init__.py:1-15`). Seams: (1) **Freshness** — `FreshnessProof`, `Provability`, `is_provable` (`freshness.py:92`), `canonical_digest`, `sla_seconds_for` (`freshness.py:293`; reads the per-entity governed `freshness_sla_seconds` descriptor field, falling back to `default_ttl_seconds`); (2) **Identity/Storage** — `ArtifactId`, `artifact_key`, `is_servable` (`identity.py`), `S3ArtifactStore` with pointer CAS (`store.py`; `PointerCASError`, `CASLost`, `ProofDigestMismatch`); (3) **Rebuild** — `Rebuilder`, `PacedAsanaFetcher`, `AcceptancePredicates`, `SingleFlight` (`rebuild.py`); (4) **Serving** — `GatedSubstrateReader`, `Provable`/`Refused`, `RefuseReason`, `SunsetBreach` (`serve.py:374`) plus thin adapters `OfflineServeAdapter`, `ForceWarmRecheckAdapter`, `QueryServeAdapter` (`serve_adapters.py`, labelled DARK); (5) **Observability** — `ScheduledProvabilityEvaluator`, CloudWatch emitters (`observe.py`). Operator tooling lives here too: `live.py` (1336 lines, live-parity arming), `parity_run.py` (window-entry runner, has a `main`), `prov_sweep.py`, `population_floor.py` (`TieredPopulationFloor`). **Only one production consumer exists outside the package**: `lambda_handlers/prov_sweep.py:55-75` (scheduled every 900 s per its docstring). No `api/`, `query/` or `services/` file imports `substrate` — the serving seam is not wired into the request path at this commit (verified by whole-tree grep; the AST graph shows `lambda_handlers → substrate` as the sole inbound edge).

**`enrollment/`** — WS-A: the one intent surface (Asana `custom_cal_status`) reaches the scheduling gate through one governed write path. `intent_projection.py` (792) is PURE (three-frame projection + four refusal predicates `assert_intent_columns_present / assert_frames_fresh / assert_universe_floor / assert_delta_within_ceiling`, `project_enrollment_intent`); `scheduling_client.py` (350) is `SchedulingConfigClient` (the only crossing to `autom8y-scheduling`). It is PHONE-keyed and explicitly NOT the guid-keyed WS-B producer (`enrollment/__init__.py:17-21`). Sole consumer: `lambda_handlers/enrollment_intent_bridge.py:116-140` (DEFAULT-DARK, gate env `ENROLLMENT_INTENT_BRIDGE_ENABLED`, `enrollment_intent_bridge.py:223`).

**`readout/`** — EX-5 item-1a generation: `item_1a.py` (`compute_item_1a`, `enumerate_g4_prime`, `Item1aFigure`), `template.py` (`render_blocks`, `render_fallback_text`), `generation.py` (`render`, `extract_rows_and_meta`, `GeneratedOccurrence`, emits the `report_generated` provenance event). It reads only `POST /v1/query/offer/rows` response bytes (DF-1, `readout/__init__.py:8-10`). **No importer exists in `src/` outside the package itself**; the only external references are unit tests (`tests/unit/test_readout_generation.py`, `test_rail_*.py`, `test_rung_receipts.py`). It imports `observability.payload_hash` and `observability.rung_receipts.schema` (`readout/generation.py:51-52`).

**`observability/rail_delivery/` and `observability/rung_receipts/`** [NEW subpackages] — EX-6 delivery distinguishability/block-budget/occupants and EX-4 durable receipt schema + join query (`rung_receipts/__init__.py`, `rung_receipts/query.py` has a `__main__`). Only `readout` and tests consume them.

**`auth/`** (8 files incl. `__init__`; 1118 lines): `bot_pat.py`, `jwt_validator.py` (`validate_service_token`, `jwt_validator.py:62`), `dual_mode.py` (`detect_token_type`, `dual_mode.py:39`), `service_token.py`, `audit.py`, `business_token.py` (per-business token minter; own exchange client over `POST /tokens/exchange-business`), `per_business_provider.py` (`PerBusinessTokenProvider`, anti-IDOR one-token-per-business).

**`domain/`** (2 modules): `forwarding_stage.py` (365; `ForwardingStage` + `StageTransitionValidator`/`StageDisposition`) and `forwarding_stage_backfill.py` (157; pure `derive_stage`). Consumers: `services/ci_task_resolution.py:55`, `services/forwarding_stage_census.py:81`, `automation/forwarding_stage_backfill/{backfill,cli,evidence_source}.py`. Imports nothing internal except itself (graph: zero out-edges).

**`normalizer/`** (844 lines; `scheduling_stratum.py` 429, `scheduling_extractor.py` 364). Pure resolver (`resolve_stratum`, declarative first-non-empty-wins cascade) + I/O extractor that reads the 8 provider fields via `resolution.gfr.resolve_async` (`scheduling_extractor.py:43`). Consumers: `lambda_handlers/scheduling_stratum_snapshot.py:101`, `services/scheduling_stratum_push.py`, `enrollment/intent_projection.py:150` (reuses `derive_enrolled`).

**`contracts/`**: `vocabulary_sync.py` (`VocabularySyncRequest`), sole importer `services/gid_push.py:24`. Zero internal imports.

**`resolution/gfr/`** (11 files incl. `__init__`, 1988 lines, up from 8/~1725). One public verb `resolve_async(gid, fields) -> ResolvedFields` (`gfr/__init__.py:20-29`); 7-step spine plan → entry → guard → identity-read → posture → optional tier-2 verify → cardinality (`gfr/engine.py:1-35`, `resolve_async` at `engine.py:220`). **Two** external consumers (prior pass found one): `normalizer/scheduling_extractor.py:43` and `automation/workflows/onboarding_walkthrough/identity_guard.py:40-41` (+ `onboarding_walkthrough/workflow.py:80`).

**`lifecycle/`** gained `activation_smoke.py` (906) + `activation_referent.py` (127): a referent-injected gate on the "activating" transition; its docstring states `STATUS: NOT WIRED` (`activation_smoke.py:78`) and a whole-tree grep finds no production importer.

**`api/`** additions: `write_authz.py` (`WriteClass` {tasks/projects/sections/intake/receipts:write, workflows:execute}, `AuthzMode` ENFORCE/OBSERVE, unset/malformed ⇒ ENFORCE; `write_authz.py:100-172`), `status_push.py` (`AccountStatusPushLoop`, 4-hour cadence, `:231`), `fleet_query_adapter.py`, `sli_heartbeat.py`, `event_loop_monitor.py`, `client_pool.py` (token-keyed `ClientPool`), `rate_limit.py` (SlowAPI limiter, SA namespace 600/min override on `/rows`, `routes/query.py:~321-345`).

**`lambda_handlers/`**: 21 files — 11 independently deployable handlers (see Entry Points) + 8 support modules used by `cache_warmer` (`checkpoint`, `cloudwatch`, `pipeline_stage_aggregator`, `push_orchestrator`, `reconciliation_runner`, `story_warmer`, `timeout`, `workflow_handler` factory) + `offer_warm_amp` (emit helper, no `handler`).

**Other new/changed single files**: `services/scheduling_stratum_push.py`, `services/ci_task_resolution.py`, `services/receipts_service.py`, `services/forwarding_stage_census.py`, `services/tag_service.py`, `services/gid_push.py` (1581), `transport/budget_allocator.py` (F1a advisory allocator), `core/warm_deadline.py`, `cache/durable_task_cache.py` (`DurableTaskCacheReader`), `dataframes/builders/{fail_closed_write,null_number_recovery,post_build_population_receipt}.py`, `metrics/{freshness,sla_profile,rebuild_gate}.py`, `models/business/identity_supply.py`.

## MCP Sidecar Surfaces (`mcp/`)

A separate project (own `mcp/pyproject.toml`, name `asana-mcp` 0.1.0, `fastmcp>=3.4.4,<3.5.0`) — a REFERENCE/throwaway POC FastMCP process, NOT a FastAPI route table. It speaks HTTP only to the satellite's own REST surface and never imports `autom8_asana` (constraint 5, `mcp/pyproject.toml:1-13`). Layout: `mcp/asana_mcp/{server,assembly,bridge,context,envelopes,errors,observability,schemas,settings,timeouts}.py`, `mcp/asana_mcp/tools/*`, `mcp/serve_stdio.py`, `mcp/tests/` (24 test files), `mcp/canary/test_broken_fixture_canary.py`, `mcp/probes/c2_sandbox_reput_probe.py`.

- **Assembly order** (frozen mount-seam): `create_server()` → `register(...)` per tool → `instrument(...)` (`mcp/asana_mcp/assembly.py:44-60`). `create_server` (`server.py:34-58`) registers **6 read tools** via `register(mcp, ctx)`: `list_entity_types`, `describe_entity` (`tools/discovery.py:55,66`; GET `/v1/query/entities`, `/v1/query/{et}/fields|relations|sections`), `query_rows`, `query_aggregate` (`tools/query.py:42,55`; POST `/v1/query/{et}/rows|aggregate`), `resolve_entity` (`tools/resolve.py:39`; POST `/v1/resolve/{et}`), `list_report_workflows` (`tools/workflows.py:104`; GET `/api/v1/workflows/` — trailing slash load-bearing, `workflows.py:46`; read/disclosure only, invocation is deliberately not exposed). `_match_business_stub.py` is the inert tool-6 stub (`:23`). (The `server.py` comment still says "tools (1-5)" — the code registers six.)
- **Write path**: `tools/composite_write.py` registers `asana_complete_tagged_task` only when `ASANA_MCP_ENABLE_WRITE_SURFACE` is truthy (default OFF; `composite_write.py:98`, `register` at `:451`). `tools/confirm_gate.py` implements the two-phase confirmation token (`DEFAULT_CONFIRMATION_TTL_S=600.0` at `:49`, `DEFAULT_MAX_PENDING=32` at `:53`); `tools/tag_resolve.py` is the dual-key (gid|name) tag resolver.
- **Auth bridge**: `bridge.py` mints S2S JWTs through `autom8y_core.TokenManager` (lazy import); `_classify_mint_failure` (`bridge.py:27`) maps `InvalidServiceKeyError` by MRO class-name (`bridge.py:48`) into a non-retryable 401 `McpToolError`, other mint failures into retryable 503.
- **Launcher**: `mcp/serve_stdio.py` (stdio MCP mount, `--smoke` inventory, `--fake-token`).
- **CI posture CORRECTED**: the island *is* now collected in CI — `.github/workflows/test.yml:489` defines the `mcp-island` job (installs `./mcp[dev]`, runs `mcp/tests`, then runs `mcp/canary` and requires pytest rc==1, i.e. a deliberately broken fixture must trip; `test.yml:577-602`), with a local twin `just test-mcp` (`justfile:145-158`). It remains outside `mypy_targets` (`test.yml:101` = `src/autom8_asana` only) and outside the root coverage `source` (`pyproject.toml` `[tool.coverage.run]`), and `ruff` per-file-ignores carve it out of TID251/TC00x (`pyproject.toml` `[tool.ruff.lint.per-file-ignores]`).

## Layer Boundaries

### Documented layer model (declared, partly enforced)
The semgrep rules name the layers. `.semgrep.yml:25-60` (`autom8y.asana-no-lower-imports-api`): `api/` is "Layer 5, the outermost boundary" and 19 listed packages must not import `autom8_asana.api` (`core, models, protocols, transport, clients, batch, _defaults, observability, cache, dataframes, resolution, search, query, metrics, patterns, persistence, services, lifecycle, automation`). `.semgrep.yml:61-85` (`autom8y.no-models-import-upper`): `models/`, `protocols/`, `transport/` ("Layers 1-2") must not import `services/`, `persistence/`, `lifecycle/`, `automation/` ("Layers 3-4"). Packages **not** covered by either rule: `auth, contracts, domain, enrollment, lambda_handlers, normalizer, readout, reconciliation, substrate` (and root modules). Enforcement is **pre-commit only** (`.pre-commit-config.yaml:26-34`); no `semgrep` appears in `.github/workflows/` or `justfile`. `mypy --strict` runs over `src/autom8_asana` in pre-commit and `test.yml:101`. There is no import-linter config and no import-graph test in `tests/arch/` (that directory holds only `test_namespace_contract.py` and `test_namespace_gen.py`).

```
ENTRY      entrypoint.py · api/main.py:create_app · lambda_handlers/* · query/__main__ + autom8_query_cli.py · metrics/__main__ · substrate/parity_run · mcp/serve_stdio.py
   ↓
API (L5)   api/ — routes, DI (api/dependencies.py), middleware, lifespan, write_authz, status_push
   ↓
SERVICES / ORCHESTRATION (L3-4)  services/ · lifecycle/ · automation/ · persistence/ · reconciliation/ · enrollment/ · readout/ · substrate/ · normalizer/ · domain/(pure)
   ↓
DOMAIN / DATA (L2-3)  models/ · dataframes/ · query/ · resolution/(+gfr) · metrics/ · search/ · cache/ · observability/
   ↓
INFRA (L1-2)  clients/ · transport/ · batch/ · _defaults/ · auth/
   ↓
FOUNDATION  core/ · protocols/ · patterns/ · errors.py · settings.py · config.py · storage_namespace.py · contracts/
   ⟂  mcp/  (separate project; HTTP-only consumer of the API layer)
```
This diagram is the *intended* direction. The measured graph below shows it is a one-way DAG only for the module-top-level skeleton; function-local and `TYPE_CHECKING` imports create many back-edges.

### Measured import graph (AST walk, all 610 files)
Distinct importing packages per target (any import kind / module-top-level only):

| Target | Fan-in any / top | Target | Fan-in any / top |
|---|---|---|---|
| `errors.py` | 19 / 19 | `persistence` | 7 / 5 |
| `core` | 18 / 16 | `transport` | 7 / 4 |
| `models` | 18 / 13 | `services` | 6 / 3 |
| `client.py` | 17 / 3 | `auth` | 6 / 3 |
| `protocols` | 15 / 3 (mostly `TYPE_CHECKING`) | `query` | 6 / 2 |
| `cache` | 13 / 6 | `storage_namespace` | 5 / 5 |
| `clients` | 13 / 6 | `resolution` | 5 / 4 |
| `dataframes` | 12 / 7 | `api` | 5 / 2 |
| `settings.py` | 10 / 9 | `normalizer`, `lambda_handlers`, `observability` | 3 / 3 |

Fan-out (distinct packages imported): `services` 19, `api` 18, `lambda_handlers` 17, `cache` 15, `automation` 15, `clients` 12, `dataframes` 12, `models` 11, `query` 9, `persistence` 9, `substrate` 7, `resolution` 7. **Hubs** (high fan-in): `errors.py`, `core/`, `models/`, `protocols/` (type-only), `settings.py`. File-level hubs by importer-file count: `core/entity_registry.py` (35 files), `core/errors.py` (34), `settings.py` (33), `models/task.py` (38), `protocols/cache.py` (28), `api/dependencies.py` (27), `api/models.py` (22), `query/models.py` (14). **Pure leaves** (no internal imports): `domain/` (zero out-edges), `contracts/`, `patterns/` (only `errors`), `observability/` (only `protocols`, type-only). **Top-of-graph orchestrators**: `lambda_handlers` (imports 17 packages incl. `substrate`, `enrollment`, `normalizer`), `services`, `api`.

### Inverted (lower→higher) edges — the real boundary exceptions
1. `services/ → api/` at module top-level (5 files import request/response DTOs from `api/routes/*_models.py`): `services/intake_create_service.py:23`, `intake_resolve_service.py:30`, `matching_service.py:21`, `receipts_service.py:40`, `intake_custom_field_service.py:16`; plus lazy `business_by_email_service.py:70,183,209`, `universal_strategy.py:855,884,1033,1083,1195` (→ `api.metrics`, `api.exception_types`). `services` is inside the semgrep rule's include list, so these sites would be flagged if the rule ran over the tree; it is not run in CI. (TENSION-002 count was 5 top-level files; still 5, now with a 6th lazy file.)
2. `auth/ → api/`: `auth/dual_mode.py:24` (top-level `ApiAuthError`), `auth/audit.py:29` and `auth/__init__.py:14` (the latter two with `nosemgrep: autom8y.no-lower-imports-api` — note the rule's actual id is `autom8y.asana-no-lower-imports-api`, so the suppression comment does not match the rule name; `auth/` is outside the include list anyway).
3. Function-local `cache/→api` (`cache/dataframe/decorator.py:147,192,212,247`; `cache/integration/dataframe_cache.py:762`), `dataframes/→api` (`dataframes/concurrency.py:79`), `automation/forwarding_stage_backfill/cli.py:62,90 → api.config`.
4. `core/ → models|services|automation` (all function-local: `core/registry_validation.py:113,148,199`, `core/creation.py:21,124,249`) — the foundation layer reaches upward lazily.
5. `models/ → cache` (top-level, `models/business/detection/facade.py:24`) and `models/ → persistence` (lazy, `models/task.py:414-417`, `models/custom_field_accessor.py:421`, both with `nosemgrep: autom8y.no-models-import-upper`).
6. `services/ → lambda_handlers/`: `services/gid_push.py:29` (top-level `cloudwatch.emit_metric`) and `:868` (lazy `traffic_offer_divergence_tripwire`).
7. `cache ↔ dataframes ↔ clients ↔ models` are mutually referencing via lazy/`TYPE_CHECKING` imports (e.g. `models→cache` top, `cache→models` lazy/top, `dataframes→cache` top, `cache→dataframes` top). Treat these four as one tightly-coupled core, not a stack.
8. `lifecycle ↔ automation` are co-dependent: `lifecycle → automation` is imported at module top-level (graph: `lifecycle/` imports `automation` lazy+top), while `automation/workflows/pipeline_transition.py:50-51,194` imports `lifecycle.config`/`lifecycle.engine` (TYPE_CHECKING + lazy). The only in-`src` construction site of `LifecycleEngine` is `automation/workflows/pipeline_transition.py:194` inside `PipelineTransitionWorkflow` (`:64`), and a whole-tree grep finds no other reference to that class or module; separately `api/routes/webhooks.py:184` still binds `_dispatcher = NoOpDispatcher()` and `set_dispatcher` (`:187`) has no caller in `src/`, so `lifecycle/webhook_dispatcher.py` is not attached to the inbound webhook route. (Experiential corroboration: the operator memory records the lifecycle engine as DARK in production; code-side this pass confirms the missing wiring, not the runtime state.)

### Circular-import avoidance patterns in use
`from __future__ import annotations` + `TYPE_CHECKING` blocks (ubiquitous, e.g. `substrate/serve.py:24-26`); function-local imports for upward reaches; `protocols/` (`CacheProvider`, `AuthProvider`, `DataFrameProvider`) as inversion seams; `# nosemgrep` / `# noqa` annotations at sanctioned violations; `core/system_context.register_reset` self-registration of singleton resets (`core/system_context.py`, used by `models/business/_bootstrap.py:189`, `registry.py:740`); `QueryEngine` takes a `DataFrameProvider` protocol "decoupling from the services layer" (`query/engine.py:114-123`). A compile-time-adjacent S3-prefix invariant exists in `tests/arch/test_namespace_contract.py` (t1–t5) plus generator test `test_namespace_gen.py`.

## Entry Points and API Surface

### Primary entry points
- **Container ENTRYPOINT (production image)**: `Dockerfile:131,183` copies `scripts/entrypoint.sh` to `/app/entrypoint.sh` as `ENTRYPOINT`; it branches on `AWS_LAMBDA_RUNTIME_API` — absent ⇒ `exec python -m uvicorn autom8_asana.api.main:create_app --factory` (`scripts/entrypoint.sh:45-56`); present ⇒ `exec python -m awslambdaric "${HANDLER}"` (`:81`), default `CMD` = `autom8_asana.lambda_handlers.cache_warmer.handler` (`Dockerfile:187`). `Dockerfile:176` HEALTHCHECK hits `localhost:8000/health`.
- **Python twin `entrypoint.py`** (not the Docker ENTRYPOINT; used for `python -m autom8_asana.entrypoint`): `main()` (`:75`) → no `AWS_LAMBDA_RUNTIME_API` ⇒ `run_ecs_mode()` (`:34`) → `models.business._bootstrap.bootstrap()` (`:38`) → `uvicorn.run("autom8_asana.api.main:create_app", factory=True)`; Lambda ⇒ `run_lambda_mode(handler)` (`:60`) after validating `argv[1]` as a dotted path. Because the shell script bypasses `entrypoint.py`, `bootstrap()` is guaranteed on the production path only via the lifespan call (`api/lifespan.py:121`; defined `models/business/_bootstrap.py:135`).
- **Offline/ops CLIs**: `autom8-query` / `python -m autom8_query_cli` (`src/autom8_query_cli.py:main`; sets `AUTOM8Y_DATA_URL`, `ASANA_WORKSPACE_GID`, `LOG_LEVEL` *before* importing the package) → `query/__main__.py:main` (`:1666`) with subcommands `rows, aggregate, entities, fields, relations, sections, data-sources, timeline, list-queries, run` (`query/__main__.py:1353-1553`); `query/cli.py` is an in-package shim. `python -m autom8_asana.metrics` (`metrics/__main__.py:511`, offline S3-parquet metric compute + freshness line). `automation/polling/cli.py` (`validate`, `status`, `evaluate`; `:268-290`). `automation/forwarding_stage_backfill/cli.py` (`plan`, `apply`; `:212,220`). `substrate/parity_run.py:main`. `observability/rung_receipts/query.py:run_query`. `scripts/` holds ~25 operational scripts (`warm_cache.py`, `invoke_workflow.py`, `generate_openapi.py`, `gen_namespace_config.py`, canary/certification/gfr_dynvocab dirs) — not part of the wheel.
- **MCP stdio**: `mcp/serve_stdio.py`.

### Application factory and middleware
`api/main.py:create_app()` (`:378`) builds `IdempotencyMiddleware` (DynamoDB store by default, in-memory/noop selectable via `IDEMPOTENCY_STORE_BACKEND`, falls back to noop on construction failure; `api/main.py:393-440`), CORS, a `JWTAuthConfig` with `require_business_scope=True` whose `exclude_paths` carve out the PAT trees (`/api/v1/{tasks,projects,sections,users,workspaces,dataframes,offers,exports,tags}/*`) and `/api/v1/webhooks/*` so PAT/URL-token routes bypass the JWT-only middleware (`api/main.py:~446-480`; comment cites SCAR-WS8 for new PAT trees), then `create_fleet_app(...)` with the router list. Post-build: `_assert_fleet_query_mount_order(app)` (`:350` def, call at `:556`), `register_exception_handlers`, `register_validation_handler(app, service_code_prefix="ASANA")`, `SecurityHeadersMiddleware` (`:579`), `RequestIDMiddleware` (`:592`, the only production writer of `request.state.request_id`), a `FleetError` catch-all handler, a `custom_openapi()` enrichment (OAS 3.2, tag-classified FAIL_CLOSED security via `_PAT_TAGS/_S2S_TAGS/_TOKEN_TAGS`), and `instrument_app` (metrics, added last/outermost; comment `api/main.py:~930`). Note `/api/v1/workflows` is a `pat_router` (`api/routes/workflows.py:46`) but its prefix is **not** in the JWT `exclude_paths` list — S2S callers (e.g. the MCP `list_report_workflows` tool) reach it through the JWT middleware; a PAT-only caller would not bypass it.

### Router inventory (28 `RouterMount`s at `api/main.py:490-530`; ~72 route operations; 4 mounts are dual-mount pairs)
Auth scheme is encoded in the factory: `pat_router()` = PAT bearer (user token passed through to Asana), `s2s_router()` = S2S JWT (`api/routes/_security.py:37-48`; both return `SecureRouter`).

| # | Router (file) | Prefix | Auth | Operations |
|---|---|---|---|---|
| 1 | `health` | `/` | none | `GET /health`, `/ready`, `/health/deps` |
| 2-8 | `users`, `workspaces`, `dataframes`, `tasks`, `tags`, `projects`, `sections` | `/api/v1/<name>` | PAT | 3, 2, 4, 14, 1, 8, 6 ops (tasks: CRUD, subtasks, dependents, duplicate, tags, section, assignee, projects; tags: list + `?name=` resolve) |
| 9 | `internal` | `/api/v1/internal` | S2S | hosts `ServiceClaims`/`require_service_claims` (the S2S auth dependency used by most `/v1` routes), no routes of its own in the inventory |
| 10 | `intake_resolve` | `/v1` | S2S | `POST /resolve/business`, `/resolve/contact`, `/resolve/business-by-email` — mounted BEFORE `resolver` |
| 11 | `resolver` (+ `schema_router` via `include_router`, `resolver.py:93`) | `/v1/resolve` | S2S | `POST /{entity_type}`; `GET /{et}/schema`, `/{et}/schema/enums/{field}` |
| 12 | `query_introspection` | `/v1/query` | S2S | `GET /entities`, `/data-sources`, `/data-sources/{factory}/fields`, `/{et}/fields|relations|sections` |
| 13-14 | `fleet_query_router_v1` / `_api_v1` | `/v1/query`, `/api/v1/query` | S2S | `POST /entities` (FleetQuery via `api/fleet_query_adapter.py`) |
| 15-16 | `exports_router_v1` (S2S) / `_api_v1` (PAT) | `/v1/exports`, `/api/v1/exports` | S2S / PAT | `POST ""` |
| 17 | `query` | `/v1/query` | S2S | `POST /{et}/rows`, `/{et}/aggregate` (wildcard — must come after 13-16) |
| 18 | `admin` | `/v1/admin` | S2S | `POST /cache/refresh` |
| 19 | `webhooks` | `/api/v1/webhooks` | URL token | `POST /inbound` (background cache invalidation + dispatch) |
| 20 | `workflows` | `/api/v1/workflows` | PAT | `GET /`, `POST /{workflow_id}/invoke` |
| 21 | `entity_write` | `/api/v1/entity` | S2S | `PATCH /{entity_type}/{gid}` |
| 22 | `section_timelines` | `/api/v1/offers` | PAT | `GET /section-timelines` |
| 23-24 | `intake_custom_fields`, `intake_create` | `/v1/tasks`, `/v1/intake` | S2S | `POST /{task_gid}/custom-fields`; `POST /business`, `/route` |
| 25 | `receipts` | `/v1` | S2S | `POST /receipts` (EBI forwarding receipt → Asana comment) |
| 26 | `forwarding_stage_census` | `/v1/forwarding-stage` | S2S | `GET /census` (read-only) |
| 27 | `matching` | `/v1/matching` | S2S | `POST /query` |
| 28 | `identity_supply` | `/v1/identity-supply` | S2S | `GET /{offer_gid}` (id-walk identity evidence for the substrate) |

Load-bearing mount order (FastAPI first-match): `intake_resolve` before `resolver`; `fleet_query_*` and `exports_*` before `query`'s `/{entity_type}` wildcard; the latter enforced at startup by `_assert_fleet_query_mount_order` (`api/main.py:350-375`, raises `RuntimeError`). Write routes are gated by `require_write_authz(WriteClass.X)` (`api/write_authz.py`) — present on `tasks`, `projects`, `sections`, `workflows`, `entity_write`, `intake_create`, `intake_custom_fields`, `receipts`.

Auth dependency (`api/dependencies.py:134 get_auth_context`): `detect_token_type(token)` → PAT ⇒ pass-through `AuthContext(mode=PAT, asana_pat=token)`; else lazy `auth.jwt_validator.validate_service_token` → `AuthContext` carrying the bot PAT (`ASANA_BOT_PAT`) for downstream Asana calls; circuit-open / SDK-missing ⇒ `ApiServiceUnavailableError`. Service DI factories (`get_entity_service`, `get_task_service`, `get_section_service`, `get_dataframe_service`, `get_tag_service`, `get_data_service_client`; `dependencies.py:424-545`) are the DI seam from `api/` to `services/`.

### Lambda handlers (11 independently deployable; `lambda_handlers/`)
`cache_warmer.handler` (`:1274`; the big one, 1498 lines — warms entity-type frames, checkpoint-resume, pushes GID/account-status via `push_orchestrator`, prematerialize bulk-set), `cache_invalidate.handler` (`:299`), `conversation_audit`, `insights_export`, `payment_reconciliation`, `onboarding_walkthrough` (all four built via `workflow_handler.create_workflow_handler(WorkflowHandlerConfig)`, `workflow_handler.py:87`), `leads_consumer.handler` (`:50`), `prov_sweep.handler` (`:222`, substrate provability sweep), `enrollment_intent_bridge.handler` (`:699`, DEFAULT-DARK), `scheduling_stratum_snapshot.handler` (`:1245`, DEFAULT-DARK, 1329 lines), `traffic_offer_divergence_tripwire.handler` (`:1083`, DEFAULT-DARK). `lambda_handlers/__init__.py` eagerly re-exports six of them. Terraform for deployment lives in the autom8y monorepo; this repo's `terraform/services/asana/` only carries alarm definitions (`observability_alarms.tf`, `story_warm_dead_alarm.tf`, `warmer_cache_degraded_alarm.tf`, `substrate_v2_provability_alarms.tf`) and the generated `namespaces.gen.json`.

### Key exported contracts between packages
`protocols/cache.py:19 CacheProvider`, `protocols/auth.py:6 AuthProvider`, `protocols/dataframe_provider.py:25 DataFrameProvider` (consumed by `query/engine.py`, `cache/`, `services/`), `resolution/gfr.resolve_async`, `substrate.{is_provable,artifact_key,GatedSubstrateReader,S3ArtifactStore}`, `core.entity_registry.get_registry()`, `storage_namespace.REGISTRY`, `settings.get_settings()`.

## Key Abstractions

| Abstraction | Where | What it is / who uses it |
|---|---|---|
| `AsanaClient` | `client.py:98` | Facade owning config, `AsanaHttpClient` (`transport/asana_http.py:91`), cache provider, lazy per-resource clients (`clients/*`), `BatchClient`, `SearchService`, optional `AutomationEngine` and `UnifiedTaskStore`. Context-manager (`__aenter__` `:1041`), sync wrappers via `patterns/async_method.py`. Constructed per-request via `api/dependencies.get_asana_client_from_context` (`:299`) or pooled in `api/client_pool.py`. |
| `EntityDescriptor` / `EntityRegistry` | `core/entity_registry.py:96,245`; `get_registry()` `:1262`; 30 descriptors in `ENTITY_DESCRIPTORS` (`:460`) | Frozen+slotted per-entity metadata: `name, pascal_name, entity_type, category (root/composite/leaf/holder), primary_project_gid, body_parameterized, model_class_path, parent_entity, holder_for, name_pattern, emoji, schema_key, default_ttl_seconds, freshness_sla_seconds (governed, substrate C8/C17), warmable, warm_priority, aliases`. Includes holders, 8 process subtypes, `stage_transition`, `project`, `section`. `_bind_entity_types()` (`:1052`) late-binds `EntityType`; `_validate_registry_integrity` (`:1095`) runs at load. Hub of the codebase (35 importer files). |
| `StorageNamespaceContract` | `storage_namespace.py:184`; `REGISTRY` `:520`; `REGISTRY_NAMESPACE_COUNT = 12` `:540` | Typed S3 prefix/lifecycle/writer/IAM contract. 12 entries: `TASK_CACHE`, `DATAFRAMES_V2`, `CHECKPOINTS`, `CHECKPOINTS_BULK`, `CHECKPOINTS_SECTION_FAST`, `E2E_TEST_DATAFRAMES`, and six `*_FOSSIL` namespaces (`PROJECT_FRAMES_FOSSIL`, `TASK_CACHE_LEGACY_FOSSIL`, `TASK_DATA_CACHE_V3_FOSSIL`, `INSIGHTS_FRAMES_FOSSIL`, `NAME_GID_MAPPINGS_FOSSIL`, `ASANA_CACHE_DATAFRAMES_FOSSIL`). Import-time guards `_validate_registry` (`:569-590`) + t1–t5 tests + `KNOWN_DRIFTS` (`:548`) + generated `terraform/services/asana/namespaces.gen.json`. The `substrate/` artifact keys (`substrate/store.py:255-262`) build their own `versions/` prefixes and are **not** a registry entry. |
| `DataFrameBuilder` / `ProgressiveProjectBuilder` | `dataframes/builders/base.py:87`, `builders/progressive.py` (2000 lines) | Schema-driven polars frame construction; progressive builder persists per-section parquet + `SectionManifest` (`dataframes/section_persistence.py:119`), resume-capable. |
| `DataFrameCache` (+`BuildCoordinator`, `CircuitBreaker`, `DataFrameCacheCoalescer`) | `cache/integration/dataframe_cache.py`, `cache/dataframe/{build_coordinator,circuit_breaker,coalescer}.py` | Tiered frame cache: `MemoryTier` → `ProgressiveTier` (reads the same `SectionPersistence` location the builder writes; `cache/dataframe/tiers/`), entity-aware TTL + stale-while-revalidate (`FRESH / APPROACHING_STALE / STALE`), per-project circuit breaker with last-known-good fallback (`_get_circuit_lkg`), memory-tier population-degraded soft-reject (`_memory_get_serviceable`). |
| `CacheProvider` (protocol) + backends | `protocols/cache.py:19`; `cache/backends/{memory,redis,s3}.py`; `cache/providers/{unified,tiered}.py`; factory `cache/integration/factory.py` | Task-level cache. `UnifiedTaskStore` (`cache/providers/unified.py`) is the single-source task store; `TieredCacheProvider` is effectively Redis-only (S3 cold tier retired, `cache/providers/tiered.py:1-5`). |
| `DataFrameProvider` (protocol) | `protocols/dataframe_provider.py:25` | Lets `QueryEngine` read frames without importing services. |
| `QueryEngine` | `query/engine.py:114` (`execute_rows` `:130`, `execute_aggregate` `:386`) | depth guard → classification/section resolution → `provider.get_dataframe` → `PredicateCompiler` (`PredicateNode` discriminated union `query/models.py:168`) → filter → join (entity or data-service) → pagination → select → verification meta. One `_read_serve_manifest` per request (`:625`). |
| `UniversalResolutionStrategy` | `services/universal_strategy.py:113` (`resolve` `:162`) | Schema-driven S2S resolution: validate+group by key columns → build `DynamicIndex` once per key set (`services/dynamic_index.py`) → gather-limited lookups → ordered results; `active_only` default. **Name collisions:** three distinct `ResolutionResult` classes (`models/business/resolution.py:81`, `resolution/result.py:28`, `services/resolution_result.py:19`) and two `ResolutionStrategy` types (`models/business/resolution.py:38` StrEnum; `resolution/strategies.py:27` ABC). |
| `SaveSession` / `SavePipeline` | `persistence/session.py:69` (1820 lines), `persistence/pipeline.py:58` | Unit-of-work: `ChangeTracker` → `DependencyGraph` → 5 phases VALIDATE / PREPARE / EXECUTE (via `BatchExecutor`) / ACTIONS (via `ActionExecutor`) / CONFIRM (`pipeline.py:1-13`); unsupported-field redirection map `UNSUPPORTED_FIELDS` (`:48`). |
| `LifecycleEngine` | `lifecycle/engine.py:199` | Stage-transition engine: creation, cascading sections, completion, dependency wiring, reopen, init-action `HANDLER_REGISTRY` (`:806`), `StageTransitionEmitter`. Config-driven (`lifecycle/config.py`). See wiring caveats under Layer Boundaries #8. |
| `WorkflowAction` / `BridgeWorkflowAction` | `automation/workflows/base.py:106`, `bridge_base.py:68` | Batch workflow contract; registry `automation/workflows/registry.py`; Lambda wrapper `create_workflow_handler`. Implementations: `conversation_audit`, `insights`, `payment_reconciliation`, `onboarding_walkthrough`, `leads_consumer`, `pipeline_transition`, `active_offer_enumeration`. |
| `AutomationEngine` / `PipelineConversionRule` | `automation/engine.py:30`, `automation/pipeline.py:49` | Rule-based post-save automation attached to `AsanaClient.automation`. |
| Business hierarchy | `models/business/{business,unit,offer,contact,location,hours,process,asset_edit,...}.py`; detection `models/business/detection/tier1-4.py`; hydration `models/business/hydration.py` | Business → holders (Unit/Contact/Location/DNA/Reconciliation/AssetEdit/Videography/Offer/Process) → leaves; 4-tier entity detection with facade cache; upward hydration; `_bootstrap.bootstrap()` registers models with the project registry (replaces `__init_subclass__` auto-registration). Matching: Fellegi-Sunter `models/business/matching/engine.py`. |
| `resolve_async` / GFR | `resolution/gfr/` | See Package Structure; guarantees GFR-IDENTITY-1 (identity read by GID-exact Business row, never `office_phone` join) and cache-only post-entry (INVARIANT I3). |
| `substrate` seam objects | `substrate/` | `FreshnessProof(built_from_live_at, content_digest, sla_seconds)` (`freshness.py:62`) with `[H2]` tz-reject `__post_init__`; `is_provable` = PROVABLE iff age ≤ SLA and digest matches, else STALE/CORRUPT (`freshness.py:92-117`); `fold_built_from_live_at` = MIN over *content-fetch* instants only (probes cannot freshen, `:120`); `SubstrateRebuilder` stage-validate-swap with CAS retries (`rebuild.py:508`); `GatedSubstrateReader` re-runs the gate on every read, returns `Provable | Refused`, infra faults propagate rather than becoming refusals (`serve.py:374`). |
| `ServiceClaims` / `AuthContext` / `WriteClass` | `api/routes/internal.py` (claims; carries `client_id`), `api/dependencies.py:46`, `api/write_authz.py:100` | Principal model + deny-by-default write-class allowlist, ENFORCE unless `observe` literal. |
| `VocabularySyncRequest`, `ForwardingStage`, `EnrollmentIntent`, `OperatorClaims` mint (`clients/data/_operator_mint.py`), `DurableTaskCacheReader` (`cache/durable_task_cache.py`), `BudgetAllocator` (`transport/budget_allocator.py`), two-phase confirm gate (`mcp/asana_mcp/tools/confirm_gate.py`) | various | Cross-repo envelopes / vocabularies / auth mints, carried forward and re-located above. |

**Design patterns evidenced**: frozen+slotted dataclasses for registries and value objects; `typing.Protocol` seams (`protocols/`, `substrate/*` capability-typed `Rebuilder` vs `SubstrateReader`, `[H9]`); *PURE core / I/O boundary split* (`enrollment/intent_projection` vs `scheduling_client`, `normalizer/scheduling_stratum` vs `scheduling_extractor`, `domain/` vs `automation/forwarding_stage_backfill`, `metrics/rebuild_gate`, `dataframes/builders/fail_closed_write`); *DEFAULT-DARK* activation gates on newer Lambdas (`ENROLLMENT_INTENT_BRIDGE_ENABLED`, scheduling-stratum, tripwire, walkthrough) that emit a dead-man metric even when dark; *refuse-loud typed refusals* (`EnrollmentRefusedError`, `Refused`, `UnresolvedError`, `AmbiguousCardinalityError`); *registry + `register_reset`* singleton lifecycle; secure-router factory (`pat_router` / `s2s_router`) encoding auth scheme at the router.

## Data Flow

### 1. API request (S2S JWT)
`create_fleet_app` (fleet-standard stack from `autom8y_api_middleware`, not re-derived here; `IdempotencyMiddleware` passed as `extra_middleware`) plus app-level `add_middleware` calls `SecurityHeadersMiddleware` (`api/main.py:579`) and `RequestIDMiddleware` (`:592`), with `instrument_app`'s `MetricsMiddleware` added last as the outermost wrapper (`api/main.py:927-931` comment) → `JWTAuthMiddleware` (`require_business_scope=True`; PAT/webhook paths excluded) → router → `Depends(require_service_claims)` (`api/routes/internal.py`) → `get_auth_context` (`api/dependencies.py:134`; PAT pass-through or validate JWT → bot PAT) → `require_write_authz` on write classes → service via DI (`dependencies.py:424-545`) → `AsanaClient`/cache/engine → `SuccessResponse[...]` envelope (`api/models.build_success_response`) → exception handlers (`api/errors.py`: `raise_api_error`, `raise_service_error`, `fleet_error_handler`).

### 2. `/v1/query/{entity}/rows` read path
`api/routes/query.py:query_rows` (rate limit 600/min SA namespace) → `EntityServiceDep.validate_entity_type` → body-`project_gid` precedence over registry GID; `body_parameterized` entities (`project`,`section`) require it → `EntityQueryService.query` (`services/query_service.py:341`) → `QueryEngine.execute_rows` (`query/engine.py:130`): depth guard → section/classification → `DataFrameCache.get_async` (memory → progressive/S3 → SWR/STALE; breaker LKG) → on miss `BuildCoordinator` single-flight build → compile predicate → filter → join → paginate → select → `RowsResponse` with verification fields (`verified_at`, `verification_age_seconds`, `axes_present`) derived from ONE per-request `SectionManifest` read.

### 3. DataFrame build / warm
Triggers: ECS lifespan background task `_preload_dataframe_cache_progressive(app)` (`api/lifespan.py:340`, impl `api/preload/progressive.py`; sets `app.state.cache_warming_task`; `/ready` 503 until warm), request-time build-on-miss, `cache_warmer` Lambda (`_warm_cache_async`, `lambda_handlers/cache_warmer.py:724`, checkpoint resume via `lambda_handlers/checkpoint.py`, `core/warm_deadline.py` deadline yield), SWR refresh. Build: `ProgressiveProjectBuilder.build_progressive_async` (`builders/progressive.py:1005`): list sections → resume/probe freshness → ensure manifest → fetch+persist incomplete sections (`_fetch_and_persist_section*`, checkpointed) → merge → reconstruct/warm hierarchy (5.25–5.3) → cascade validation (5.5) → path-canon numeric recovery (`null_number_recovery`, 5.65) → value-population receipt (5.7, warn-first) → fail-closed write decision against prior-good frame (5.8) → write final artifacts (6, `_finalize_artifacts_write_async` `:764`). Persistence: `S3DataFrameStorage` (`dataframes/storage.py`) / `SectionPersistence` under `DATAFRAMES_V2`.

### 4. Entity resolution (S2S)
`POST /v1/resolve/{entity_type}` → `services/resolver.py` (criterion validation, `EntityProjectRegistry` populated at startup by `_discover_entity_projects`, `api/startup.py:117`) → `get_universal_strategy(entity_type)` (`services/universal_strategy.py:1405`) → `UniversalResolutionStrategy.resolve` (3 phases: validate+group, parallel index build+lookup, ordered return; status-aware `active_only`).

### 5. GFR resolution
`normalizer/scheduling_extractor` or `onboarding_walkthrough/identity_guard` → `resolution.gfr.resolve_async(gid, fields)` → plan → entry (the *only* Asana API read: hydrate + type-detect + parent-walk to Business gid) → guard (identity-path purity) → identity read (`RowsRequest where gid == business_gid`, `join=None`, via `QueryEngine.execute_rows`) → posture/provenance → optional tier-2 by-guid verification (`truth_tier=VERIFIED`) → cardinality (`scalar=True` ⇒ `AmbiguousCardinalityError` on `row_count != 1`) → `ResolvedFields`.

### 6. Writes and cache invalidation
`PATCH /api/v1/entity/{et}/{gid}` → `FieldWriteService` (`services/field_write_service.py`): registry lookup → fetch task → membership check → `FieldResolver` → payload → one `TasksClient.update_async` → optional re-fetch → emit `MutationEvent` → `MutationInvalidator` (`cache/integration/mutation_invalidator.py`) evicts task + frame entries. SDK-side writes use `SaveSession` (flow above). Inbound Asana webhook (`api/routes/webhooks.py:392`): token verify → background cache invalidation if `modified_at` newer → `_dispatcher.dispatch` (currently the `NoOpDispatcher`, `webhooks.py:166-184`).

### 7. Outbound pushes to autom8_data
Account-status/GID mappings: `services/gid_push.py` (`push_gid_mappings_to_data_service` `:701`, `push_status_to_data_service` `:1075`; gate `STATUS_PUSH_ENABLED` read per process, `:112,833`; dedicated status-push service-account token provider `:455-555`). Two ECS firing points (preload tail + `AccountStatusPushLoop`, 4 h; `api/status_push.py:166,231`; started in lifespan `api/lifespan.py:388`) and the Lambda lane (`push_orchestrator`). Scheduling-stratum snapshot: `lambda_handlers/scheduling_stratum_snapshot.handler` → warmed UnitHolder×Business frames → `normalizer.resolve_stratum` → `services/scheduling_stratum_push.py`. Vocabulary sync: `contracts.VocabularySyncRequest` via `gid_push` (`_is_vocab_sync_enabled` `:1217`).

### 8. Substrate-v2 (DARK except provability sweep)
rebuild (`SubstrateRebuilder.rebuild`: paced Asana fetch → stage → acceptance predicates/floor → CAS pointer swap LAST) → `S3ArtifactStore` (versioned prefix + pointer) → `GatedSubstrateReader.read` (digest at bytes-ingress → `is_provable` → `Provable|Refused`) → thin adapters (`serve_adapters.py`: CLI/recheck/HTTP). Live in production only: `lambda_handlers/prov_sweep.handler` → `substrate/prov_sweep.run_prov_sweep` → `ScheduledProvabilityEvaluator` → CloudWatch emitters → alarms in `terraform/services/asana/substrate_v2_provability_alarms.tf`. Operator tools `substrate/live.py` and `parity_run.py` arm/open the live-parity window.

### 9. Configuration
`Settings` (pydantic-settings via `Autom8yBaseSettings`) env-driven; many modules still read `os.environ` directly with `# ENV-DIRECT` justification (e.g. `entrypoint.py`, `api/main.py` idempotency vars, `api/status_push.py:STATUS_PUSH_INTERVAL_ENV_VAR`). Merge points: `settings.Settings` → `config.AsanaConfig`/`CacheConfig` (via `transport/config_translator.py` into `autom8y_http` config); governed freshness: `EntityDescriptor.freshness_sla_seconds` → `substrate.sla_seconds_for` (falls back to `default_ttl_seconds`).

## External Dependencies

Runtime (`pyproject.toml:14-55`): `httpx`, `anyio`, `pydantic`, `pydantic-settings`, `asana>=5.0.3`, `polars`, `arrow`, platform SDKs `autom8y-api-middleware[rate-limit]`, `autom8y-config`, `autom8y-http[otel]`, `autom8y-cache`, `autom8y-log` (242 import sites — the most-used internal-fleet dependency), `autom8y-guid`, `autom8y-core>=4.2.0,<5`, `autom8y-telemetry[aws,fastapi,otlp,remote-write]`, `opentelemetry-instrumentation-httpx`, plus `boto3`, `pyyaml`, `openpyxl`, `phonenumbers`, `pyjwt>=2.15,<3`. Extras: `api` (fastapi, starlette, `autom8y-api-schemas`, uvicorn, slowapi), `auth` (`autom8y-auth[observability]`), `redis`, `events`, `interop`, `scheduler`, `lambda` (`awslambdaric`). Import-site counts across `src/`: `autom8y_log` 242, `autom8y_api_schemas` 25, `autom8y_telemetry` 17, `autom8y_http` 16, `autom8y_config` 11, `autom8y_core` 6, `autom8y_cache` 3, `autom8y_auth` 2. The `mcp/` island adds `fastmcp>=3.4.4,<3.5.0` and uses `httpx` directly (ruff TID251 exception). Tooling: mypy `--strict` (`pyproject.toml` `[tool.mypy]`), ruff (rules incl. `TCH`, `TID`, `BLE001`), pytest (`asyncio_mode=auto`, `--dist=loadgroup`, markers `slow/integration/benchmark/fuzz/scar/worker_isolated`), coverage `fail_under=80`.

## Experiential Observations (from `.sos/land/initiative-history.md`)

The land file (generated 2026-04-28, 18 sessions, 10x-dev dominant) predates nearly all structure above, so it can only corroborate older lineage: `asana-phantom-materialization` and `project-crucible` precede the `dataframes/builders/progressive.py` and test-suite shape; the `project-asana-pipeline-extraction` Phase 1 session (telos_deadline 2026-05-11) is the origin of the dual-mounted `/exports` routers (`api/routes/exports.py`, comments cite "Sprint 3 (project-asana-pipeline-extraction Phase 1)", `api/main.py:~512`); `Status-Aware Entity Resolution` (commit `1f83e85`) matches `active_only` / ACTIVE+ACTIVATING filtering in `UniversalResolutionStrategy.resolve`. Its observations that 50% of sessions park at "requirements" and 1/18 reach "complete" are experiential and not verifiable from code. It contains **nothing** about `substrate/`, `enrollment/`, `readout/`, GFR, MCP, or the lifecycle activation smoke — those are code-verified here only. Operator memory (not code) additionally asserts the lifecycle engine is dark in production and that write-authz runs in observe mode; this pass verifies only the code-side facts (no `set_dispatcher` caller; `AuthzMode` defaults to ENFORCE when unset, so observe mode would be an env setting not visible in source).

## Knowledge Gaps

- Not read in depth: `resolution/gfr/dynvocab*.py` algorithm, `mcp/asana_mcp/tools/tag_resolve.py`, `clients/data/_endpoints/*`, `automation/polling/*` internals, `automation/workflows/onboarding_walkthrough/*` (large subpackage: floodgates, deck manifests, producer), `models/business/matching/*` algorithm detail, `reconciliation/processor.py` depth, `cache/dataframe/*` coalescing internals, `metrics/freshness.py` + `sla_profile.py` bodies, `substrate/live.py` (1336 lines; skimmed docstrings and class names only), `services/intake_*` bodies.
- Deployment topology (Lambda schedules, ECS task defs) lives in the autom8y monorepo; only alarms are in this repo's `terraform/`. Which handlers are actually scheduled/enabled in production is not derivable from this tree.
- The per-package fan-in/fan-out numbers come from a one-off AST script over `src/autom8_asana` (relative imports resolved; `from autom8_asana import X` counted as a root-module edge); `importlib`/string-based dynamic imports (e.g. `core/entity_registry._resolve_dotted_path`, `:61`) are invisible to it.
- `readout/`, `observability/rail_delivery|rung_receipts`, `substrate` serve path, `lifecycle/activation_smoke`, `PipelineTransitionWorkflow`, and `NoOpDispatcher` replacement are all *present in the tree but without a production importer in `src/`*; whether other repos import them is unknown.

### Changes since prior version (2026-07-23, `d0c8b662` → `c29f58f4`)
- **Counts**: 26 → 29 top-level packages (+`substrate`, `enrollment`, `readout`); 564 → 610 `src` .py files; MCP 48 → 50 .py; routers: prior count 26, now 28 `RouterMount`s (28 incl. both halves of the two dual-mount pairs); `forwarding_stage_census`, `matching`, `identity_supply` are absent from the prior's named additions (prior row table not re-diffed row-by-row); ~72 route operations (previously uncounted).
- **CORRECTED — MCP CI**: prior stated "Root CI collects none of it"; false now. `test.yml:489` `mcp-island` job + `just test-mcp` run the 24-file suite and a rc==1 teeth canary. Still outside mypy/coverage/semgrep.
- **CORRECTED — GFR consumers**: prior said `normalizer/scheduling_extractor.py` is "the only cross-package consumer"; `automation/workflows/onboarding_walkthrough/identity_guard.py:40` and `workflow.py:80` also import it. GFR is 11 files / 1988 lines, not 8 / ~1725.
- **CORRECTED — entry flow**: prior implied `entrypoint.py` is the entry; the production image's ENTRYPOINT is `scripts/entrypoint.sh` which execs `python -m uvicorn ... create_app --factory` directly (`scripts/entrypoint.sh:53`), bypassing `entrypoint.py`'s pre-uvicorn `bootstrap()`; bootstrap is guaranteed by the lifespan (`api/lifespan.py:121`).
- **CORRECTED — Lambda handlers**: prior "17 handlers"; this pass counts 11 independently deployable handlers + 8 cache-warmer support modules + `offer_warm_amp` (no `handler`), with 3 new entries (`prov_sweep`, `enrollment_intent_bridge`, `traffic_offer_divergence_tripwire`) and the prior list's `cache_warmer`-support names (checkpoint, cloudwatch, push_orchestrator, ...) reclassified as support modules.
- **CORRECTED — semgrep layer scope**: prior "19 of 26 non-api packages are in the include list; `auth/ contracts/ domain/ lambda_handlers/ normalizer/ reconciliation/` are not" — the include list is still 19 packages; the uncovered set is now those six plus `enrollment/ readout/ substrate/` (nine of 28 non-api packages). Enforcement is pre-commit only (not CI). `nosemgrep` comments in `auth/` name a rule id (`autom8y.no-lower-imports-api`) that does not match the vendored rule's id (`autom8y.asana-no-lower-imports-api`).
- **NEW**: measured import-graph section (fan-in/out, inverted-edge inventory), `substrate/` seam model, `write_authz`, `status_push`, activation-smoke "NOT WIRED" status, `NoOpDispatcher` still unreplaced, two same-named `get_settings()`, three `ResolutionResult` classes.
- **Dropped as unverifiable this pass**: prior "`models/task.py`, `api/models.py`, `cache/integration/factory.py` hub" assertions were replaced with measured importer-file counts; `cache/integration/factory.py` was not re-measured and is no longer asserted as a hub.
- **Unchanged and re-verified**: `StorageNamespaceContract` with 12 namespaces and t1–t5 tests; `_assert_fleet_query_mount_order` guard; MCP 6 read tools + exposure-gated write tool + confirm gate (TTL 600 s, max 32 pending) + 401 fail-clean classification; `ForwardingStage`/`contracts` description; `SavePipeline` phases.
