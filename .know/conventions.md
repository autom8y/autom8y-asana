---
domain: conventions
generated_at: "2026-10-05T02:59:00Z"
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
confidence: 0.85
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
observed_ref: "origin/main@c29f58f4"
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "9db9c6f33d48f5c2fce398de7d3359fef30a0a0bd809044f7259f792ee6c4b9e"
---

# Codebase Conventions

> Fresh full-observation pass at `origin/main` `c29f58f4` (2026-10-04). All `path:line` cites are relative to the repo root. Covers `src/autom8_asana` (610 .py, 29 top-level packages + 7 top-level modules), the `mcp/` island (50 .py), `pyproject.toml`, `.semgrep.yml`, `justfile`, `.pre-commit-config.yaml`, and `.github/workflows/test.yml`. Test conventions are owned by `.know/test-coverage.md` and are not duplicated here.

## Error Handling Style

The package carries **four coexisting exception lineages**, not two. A new exception must pick the lineage of the layer it lives in; there is no single universal root.

### Lineage 1 — `AsanaError` (SDK / HTTP-facing, also reused by several domains)
- `AsanaError(Exception)` at `src/autom8_asana/errors.py:42` carries `message`, `status_code`, `response`, `errors` (`:56-66`). `AsanaError.from_response()` (`:68-115`) is the canonical HTTP-to-exception factory: builds a `HTTP {status}, request_id=...` context prefix, parses the Asana `errors[]` body, falls back to a 200-char body snippet on JSON/Unicode decode failure, then dispatches through `_STATUS_CODE_MAP` (`:267-277`: 401 Authentication, 403 Forbidden, 404 NotFound, 410 Gone, 429 RateLimit, 500/502/503/504 Server; anything else stays bare `AsanaError`).
- Direct children (`errors.py:118-590`): `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `GoneError`, `RateLimitError`, `ServerError`, `TimeoutError` (shadows the builtin; callers import it explicitly, e.g. `api/errors.py:41-48`), `ConfigurationError`, `CircuitBreakerOpenError`, `NameNotFoundError`, `HydrationError`, `ResolutionError`, `InsightsError` (+3 subclasses `:412,441,452`), `ExportError`, and `OperatorTokenError` (`:517`) with **3** subclasses (`OperatorMintRefusedError :548`, `OperatorAccessDeniedError :560`, `OperatorBatchVersionSkewError :571`). `SyncInAsyncContextError` (`:194`) is deliberately a `RuntimeError`, not an `AsanaError`.
- Other `AsanaError` subclasses live outside `errors.py`: `persistence/errors.py:18` (`SaveOrchestrationError` and 8 children), `auth/business_token.py` (`MintError` + 6), `automation/workflows/leads_ebid.py` (`EbidInputError` + 2). 18 classes inherit `AsanaError` directly repo-wide.
- Chaining: subclasses that wrap a cause set `self.__cause__ = cause` explicitly (`errors.py:340,378`, `persistence/errors.py:96`) rather than relying on `raise ... from`.

### Lineage 2 — `Autom8Error` (cross-cutting infra, structured context + transient flag)
- `core/errors.py:17` `Autom8Error(Exception)`: `message`, `context: dict`, optional `cause` (sets `__cause__`, `:41`), class attribute `transient: bool = False` (`:28`). `TransportError` (`:49`, transient=True) -> `S3TransportError` (`:76`) / `RedisTransportError` (`:156`); `CacheError` (`:192`, transient=False) -> `CacheConnectionError` (`:220`, transient=True); `AutomationError` (`:231`) -> `RuleExecutionError`/`SeedingError`/`PipelineActionError` (`:254-266`).
- `S3TransportError.transient` is a **computed `@property`** (`:116-118`, `# type: ignore[override]`), permanent for codes like `NoSuchKey`/`AccessDenied`; `S3TransportError.from_boto_error()` (`:131-153`) is the boundary factory (used at `cache/backends/s3.py:748`, `dataframes/storage.py:556,624,683`).
- **Under-adoption (observed, not aspirational):** outside `core/errors.py`, `AutomationError`, `RuleExecutionError`, `SeedingError`, `PipelineActionError` and `CacheConnectionError` have **zero** references anywhere in `src/`; `RedisTransportError` has 1 consumer file; `S3TransportError` 4. Do not assume automation/ code raises the `AutomationError` family — it raises its own `RuntimeError`/`ValueError` subclasses (see Lineage 4).
- Import-safe catch tuples (`core/errors.py:288-328`): `S3_TRANSPORT_ERRORS`, `REDIS_TRANSPORT_ERRORS`, `ALL_TRANSPORT_ERRORS`, `CACHE_TRANSIENT_ERRORS`, `ASANA_API_ERRORS`, built with a default then widened inside `try/except ImportError` (botocore, redis, and `autom8_asana.errors`). `except CACHE_TRANSIENT_ERRORS` appears 44 times (e.g. `clients/base.py:115`, `clients/stories.py:447,590`) — this is the standard "cache is best-effort" catch.

### Lineage 3 — per-domain roots that inherit plain `Exception`
One `errors.py` per package, each rooted directly on `Exception` (NOT `AsanaError`/`Autom8Error`): `services/errors.py:32` `ServiceError`, `dataframes/errors.py:13` `DataFrameError`, `query/errors.py:22` `QueryEngineError`, `resolution/gfr/errors.py:41` `GfrError`, `api/exception_types.py:29` `ApiError`. Total of 30 classes inherit `Exception` directly, 34 `RuntimeError`, 9 `ValueError` (grep of `^class \w+\(X\)`), versus 18 `AsanaError` and 9 `Autom8Error`-family — the *majority* of domain exceptions are outside both named roots.
- `ServiceError` exposes `error_code` and `status_hint` properties and `to_dict()` (`services/errors.py:44-62`); HTTP status is resolved by `get_status_for_error()` walking the MRO against `SERVICE_ERROR_MAP` (`:381-395`).
- GFR keeps a **closed vocabulary**: `UNRESOLVED_REASONS: Final[frozenset[str]]` with 5 members (`resolution/gfr/errors.py:30-38`), and `UnresolvedError.__init__` raises `ValueError` on an out-of-vocabulary reason (`:67-72`). Docstring rule: "no bare `Exception` is raised or caught in the package" (`:3-5`).

### Lineage 4 — local refusal/guard exceptions in feature packages
`substrate/` (`store.py` `ArtifactMissing`, `PointerCASError`/`CASLost`/`PointerAbsent`; `live.py` `ActiveMrrRefused`, `ParityLegRefused`, …), `enrollment/` (`EnrollmentRefusedError`), `lambda_handlers/` (`EvaluationRefusedError`, `SnapshotRefusedError`), `automation/workflows/onboarding_walkthrough/` (`LinkOnPlayRefused`, `TemplateCommentRefused`, `FloodgatesRefused`, `DeployRootRefused`, …), `lifecycle/activation_smoke.py` (`ReferentError` family) — named `*Refused`/`*RefusedError`/`*Mismatch`/`*Ambiguous` and rooted on `RuntimeError`/`Exception`/`ValueError`. A "refusal" is a deliberate, loud, typed fail-closed outcome. `substrate/serve.py:31-102` additionally models refusal **as a value** (`RefuseReason` closed Enum, `RefusePayload`, `Refused` vs `Provable` return types) instead of raising.

### Special roots
- `WarmDeadlineExceeded(BaseException)` (`core/warm_deadline.py:82`) is deliberately a `BaseException` so `except Exception` handlers on the warm path cannot swallow the deadline signal (rationale `:33-38`).
- `McpToolError` — see the `mcp/` section.

### Wrapping, propagation, classification
- Domain error text is an f-string with the offending field/value (`config.py:332` `raise ConfigurationError(f"max_requests must be positive, got {self.max_requests}")`). Validation lives in `__post_init__` of `@dataclass(frozen=True)` config classes (`config.py:319-525`, 213 frozen dataclasses of 327 total).
- Vendor errors are wrapped at the transport boundary into `TransportError` subclasses; botocore/redis types do not travel upward.
- `RetryableErrorMixin` (`patterns/error_classification.py:33`) computes `is_retryable` / `recovery_hint` / `retry_after_seconds` per ADR-0079 (network errors, 429, 5xx retryable; other 4xx not). Consumers: `persistence/models.py:20` and `clients/data/_endpoints/_pacer.py:41,76`. It requires `_get_error()` (`HasError` Protocol, `:15-31`).
- Batch/partial results are **errors-as-values**: `WorkflowItemError` is a `@dataclass` (not an exception) at `automation/workflows/base.py:22-35`; `SaveResult`/`ActionResult` aggregate per-item failures; `PartialSaveError` (`persistence/errors.py:103`) is the raising form.
- `raise ... from` is used at 39 sites; `B904` is **ignored** in ruff (`pyproject.toml:244`), so raise-without-from inside `except` is lint-legal. 15 sites use `from None`.

### Broad-catch policy — a named, tagged convention
This replaces the prior snapshot's "no bare except / one deliberate BLE001" framing, which no longer holds:
- No bare `except:` and no `raise Exception(` exist in `src/` or `mcp/`.
- `except Exception` appears **271** times in `src/`; `BLE001` is selected in ruff (`pyproject.toml:237`) so each is either tagged or suppressed. **257** `# noqa: BLE001` and **207** `# BROAD-CATCH: <category>` comment tags exist. Top categories: `boundary` 56, `isolation` 39, `degrade` 20, `fail-forward` 10, `catch-all-and-degrade` 9, `enrichment` 7 (e.g. `observability/decorators.py:87` `# BROAD-CATCH: enrichment -- ... then re-raises`; `api/routes/intake_create.py:161` `# BROAD-CATCH: boundary`). `ADVISORY:` is a second reason-prefix style on the same marker (`api/middleware/idempotency.py:278,340,385,405,635`). The category vocabulary is free-form (≈36 distinct tokens) — pick an existing one.
- 37 `except Exception` sites carry neither tag (e.g. `reconciliation/engine.py:119`, `clients/data/_policy.py:210`, `cache/dataframe/factory.py:136`); do not copy them.
- Whole-file BLE001 exemption: `services/receipts_service.py` (`pyproject.toml:323`, "a receipt must never fail on the stage write"). `api/middleware/idempotency.py:770` keeps an inert `# noqa: BLE001` protected by a per-file `RUF100` ignore (`pyproject.toml:333-339`) — SCAR-IDEM-001 KEEP-floor; ruff exempts handlers that call `logger.exception()`.
- Fail-open vs fail-closed is a documented per-site decision, ~230 "fail-closed" vs 25 "fail-open" mentions (e.g. fail-OPEN budget allocator wiring at `client.py:80-97` guarded so even the tripwire cannot re-raise).

### Boundaries — HTTP and Lambda
- **API three-tier convention (ADR-I6-001)** documented at `api/errors.py:20-23`: Tier 1 SDK exceptions via registered handlers; Tier 2 `raise_service_error(request_id, error)` (`:136-177`) for `ServiceError`; Tier 3 `raise_api_error(request_id, status_code, code, message, *, details, headers)` (`:92-133`, returns `Never`) for route validation. All emit the `ErrorResponse{error:{code,message,details}, meta:{request_id}}` envelope. `raise_api_error`/`raise_service_error` are called 146 times in `api/routes/*.py`; only 2 `raise HTTPException` remain in `api/`.
- Handler registration order is "most specific first, catch-all last" (`api/errors.py:771-831`); `Exception` -> `generic_error_handler` (500, hides internals per FR-ERR-009). Machine codes are `SCREAMING_SNAKE` (`RESOURCE_NOT_FOUND`, `UPSTREAM_TIMEOUT`, `INVALID_ENTITY_TYPE`).
- **Lambda handler contract**: `handler(event: dict[str, Any], context: Any) -> dict[str, Any]` returning `{"statusCode", "body"}`; `body.status` is one of `skipped`/`refused`/`error`; `refused` is a SAFE outcome mapped to 200, only a genuine substrate/config error is 500 (`lambda_handlers/traffic_offer_divergence_tripwire.py:1083-1118`). Sibling `handler_async` for direct async invocation (`cache_warmer.py:1431`, `cache_invalidate.py:391`); `@instrument_lambda` from `autom8y_telemetry.aws` (`cache_warmer.py:1273`); `emit_success_timestamp(namespace)` for dead-man switches; workflow lambdas are one-liners `handler = create_workflow_handler(_config)` (`conversation_audit.py:52`, `insights_export.py:59`, `payment_reconciliation.py:60`, `onboarding_walkthrough.py:118`).
- Logging at error boundaries: `logger.exception(...)` 36 sites, `exc_info=True` 47 sites; error payloads in logs commonly carry `{"error": str(exc), "error_type": type(exc).__name__}`.

### `mcp/` island — a fifth, disjoint taxonomy
`mcp/asana_mcp/errors.py:26` `McpToolError(Exception)` — flat, single class; `kind: str` is a free string with documented set `warming|auth|rate_limit|client|not_found|server|data-integrity-refusal` (comment `:41`; NOT a Literal/Enum — grep shows `kind=` literals at 14 call sites), `retryable: bool`, `status`, `retry_after`, `code`; `to_tool_payload()` (`:48-58`) returns a flat LLM-legible dict. Invariant: 503 -> `warming` (retryable), never `auth` (`:148-149`, the query503 scar). **Correction vs prior**: the `kind` set gained `data-integrity-refusal` (`errors.py:223`, 424 handling). No `logging`/`structlog`/`autom8y_log` import exists anywhere in `mcp/` (grep empty); observability is OpenTelemetry via lazy imports (`mcp/asana_mcp/observability.py:572,588,771`).

## File Organization

### Top-level layout
`src/autom8_asana/` has 7 top-level modules (`__init__.py`, `client.py`, `config.py`, `entrypoint.py`, `errors.py`, `settings.py`, `storage_namespace.py`) and **29** packages: `_defaults`, `api`, `auth`, `automation`, `batch`, `cache`, `clients`, `contracts`, `core`, `dataframes`, `domain`, `enrollment`, `lambda_handlers`, `lifecycle`, `metrics`, `models`, `normalizer`, `observability`, `patterns`, `persistence`, `protocols`, `query`, `readout`, `reconciliation`, `resolution`, `search`, `services`, `substrate`, `transport`. 537 of 610 .py files (88.0%) start with `from __future__ import annotations`. `src/autom8_query_cli.py` is the second wheel entry (`pyproject.toml:117`). NEW since the prior snapshot: `enrollment/`, `readout/`, `substrate/` (+ `metrics/` growth, `lifecycle/activation_*`).

### Placement rules (derived from the tree)
- **`{entity}_service.py`** in `services/` for entity services (`entity_service.py`, `task_service.py`, `tag_service.py`, `section_service.py`, …) but several services break the pattern (`resolver.py`, `gid_push.py`, `discovery.py`, `dynamic_index.py`) — the `_service` suffix is the majority pattern (19 `*Service` classes), not a rule.
- **Resource clients** one per Asana resource in `clients/{resource}s.py` (`tasks.py`, `sections.py`, `tags.py`, …) subclassing `BaseClient` (`clients/base.py:23`), which injects `http`, `config`, `auth_provider`, optional `cache_provider`/`log_provider`. The data-service client is a subpackage `clients/data/` with private submodule dir `_endpoints/` (the only `_`-prefixed package besides `_defaults/`).
- **Routes**: `api/routes/{resource}.py` with optional sibling `{resource}_models.py` (`receipts_models.py`, `resolver_models.py`, `intake_*_models.py`, `matching_models.py`, …); shared models in `api/models.py`; each route module defines `router = pat_router(...)` (PAT, `/api/v1/*`) or `router = s2s_router(...)` (service JWT, `/v1/*`) from `api/routes/_security.py:40-50`; only `health.py` and `webhooks.py` use plain `APIRouter`. Dependencies are `Annotated[..., Depends(...)]` aliases ending in `Dep` (`api/dependencies.py:414-585`: `EntityServiceDep`, `AuthContextDep`, `RequestId`).
- **Entity-parallel triads**: a new Asana entity touches `models/business/{entity}.py`, `dataframes/schemas/{entity}.py`, `dataframes/extractors/{entity}.py`, and one `EntityDescriptor(...)` in `core/entity_registry.py` (30 descriptors; the "single source of truth", import-time validation `:1-30`). Schemas and extractors are auto-discovered by descriptor path strings, not hardcoded imports.
- **Registration is explicit, not hook-driven**: `models/business/_bootstrap.py:9-10` — "the ONLY place where entity types should be registered. Do NOT add registration logic to `__init_subclass__`".
- **Config vs settings**: `config.py` = `@dataclass(frozen=True)` SDK knobs with `__post_init__` validation raising `ConfigurationError`; `settings.py` = `Autom8yBaseSettings` Pydantic-settings classes each with a distinct `env_prefix` (`ASANA_`, `ASANA_CACHE_`, `ASANA_CACHE_S3_`, `ASANA_PACING_`, `ASANA_RATELIMIT_`, `ASANA_RUNTIME_`, `REDIS_`, `AUTOM8Y_DATA_`, `WEBHOOK_`, …) and a `get_settings()`/`reset_settings()` singleton pair (`settings.py:1096,1116`). 125 `os.environ`/`os.getenv` reads across 55 files coexist with this (feature flags and lambda env vars read directly).
- **Package `__init__.py`**: 61 of 67 define `__all__`; the 6 that do not: `contracts`, `automation/forwarding_stage_backfill`, `automation/workflows/onboarding_walkthrough/floodgates`, `metrics/definitions`, `clients/utils`, `clients/data/_endpoints`. `enrollment/__init__.py` has `__all__: list[str] = []` (intentional empty export). Pure re-export `__init__`s import from sibling modules and list names alphabetically.
- **Imports**: `if TYPE_CHECKING:` blocks for annotation-only imports; ruff `TCH`/`TID` selected (`pyproject.toml:232-235`); `# noqa: E402` for deliberate delayed imports with per-file entries (`pyproject.toml:305-310`; `client.py`, `config.py`, `api/dependencies.py`, `services/resolver.py`, `services/universal_strategy.py`, `reconciliation/processor.py`).
- **Large files exist** (top: `dataframes/builders/progressive.py` 2000, `persistence/session.py` 1820, `query/__main__.py` 1724, `automation/workflows/insights/formatter.py` 1587, `services/gid_push.py` 1581, `lambda_handlers/cache_warmer.py` 1498) — no size cap is enforced.
- **Test discovery**: `testpaths=["tests"]` (`pyproject.toml:119`); `tests/` has `_shared`, `arch`, `benchmarks`, `contracts`, `fixtures`, `harness`, `integration`, `synthetic`, `unit`, `validation`; 726 `test_*.py`.

### `mcp/` island
Top-level dir with its own `mcp/pyproject.toml` (`asana-mcp 0.1.0`, `fastmcp>=3.4.4,<3.5.0`, `autom8y-core>=4.2.0`): `mcp/asana_mcp/` (assembly, bridge, context, envelopes, errors, observability, schemas, server, settings, timeouts, `tools/` with 10 files), `mcp/probes/`, `mcp/canary/`, `mcp/tests/` (26 files incl. `conftest.py`), `mcp/serve_stdio.py`. REFERENCE/THROWAWAY posture (`mcp/README.md:3-7`; `pyproject.toml:254-262`). Constraint-5 invariant: `asana_mcp` never imports `autom8_asana` (no such import found) and speaks HTTP only to the REST S2S surface; raw `httpx` is imported in 5 `asana_mcp` files (`bridge.py`, `context.py`, `errors.py`, `tools/_common.py`, `tools/tag_resolve.py`) plus the probe. **Correction vs prior**: mcp tests ARE now in CI — `test.yml:489` job `mcp-island` (hard gate, with a polarity-inverted "teeth canary" where pytest rc==1 on `mcp/canary/` is GREEN) and `just test-mcp` (`justfile:145-160`).

## Domain-Specific Idioms

- **Dual sync/async from one body**: `@async_method` (`patterns/async_method.py`) stacked on `@error_handler` (`observability/decorators.py:23`) generates `{name}_async()` + `{name}()`; the sync wrapper raises `SyncInAsyncContextError` inside a running loop (ADR-0002). 21 files use `@async_method`, 49 `@error_handler` sites; typing needs `@overload` stubs, and `# type: ignore[no-overload-impl]` appears 48 times as the accepted cost. `error_handler` wraps each call with a correlation id, start/finish debug logs, and an enrichment re-raise tagged `BROAD-CATCH: enrichment`.
- **GID as string**: `GidStr = Annotated[str, StringConstraints(pattern=...)]` (`api/models.py:51-54`); pattern `^\d{1,64}$` is **disabled** (`None`) when `AUTOM8Y_ENV` is `test`/`local`/`LOCAL` (`:45-50`). Variables/params named `*_gid` (6624 occurrences) vs `*_GID` constants (203).
- **Pydantic model config**: Asana wire models use `extra="ignore"` for forward compatibility (`models/base.py:41-42`, ADR-0005); request/response/API models use `ConfigDict(extra="forbid")` (41 sites) or `frozen=True` (20); `extra="allow"` is rare (2). `Field(examples=...)` plural form is the one in use (1 `Field(examples` site, 0 singular `example=` in `Field(...)`); the CSI-001 rule is documented in `.know/scar-tissue.md` and not lint-enforced.
- **Business-model descriptors** (`models/business/descriptors.py`): `CustomFieldDescriptor[T]` base (`:300`) with typed subclasses `TextField`, `PhoneTextField`, `EnumField`, `MultiEnumField`, `NumberField`, `IntField`, `PeopleField`, `DateField`; navigation descriptors `ParentRef[T]`, `HolderRef[T]`. Declaring `build_call_link = TextField()` on a `BusinessEntity` subclass auto-generates a nested `Fields` class of SCREAMING_SNAKE constants via `__set_name__` + `_pending_fields` (ADR-0082, `:48-66`); `field_name="Contact URL"` overrides the Asana display name. `PRIMARY_PROJECT_GID: ClassVar[str | None]` on each entity class (`models/business/contact.py:54`) feeds registration. `CascadingFields` nested class lists cascading definitions; `HolderFactory` (`models/business/holder_factory.py`) replaces hand-written holders.
- **Provider/Protocol seams**: `protocols/` defines `AuthProvider`, `CacheProvider`, `LogProvider`, `ObservabilityHook`, `InsightsProvider`, `ItemLoader`, `DataFrameProvider` (53 `(Protocol)` classes repo-wide); `_defaults/` holds the default/Null implementations (`DefaultLogProvider`, `EnvAuthProvider`, `NullObservabilityHook`, `NullCacheProvider`) wired in `client.py:11-13`.
- **Settings singletons are lazy and import-safe**: `get_settings()` (`settings.py:1096`) plus `lru_cache`/`functools.cache` accessors (15 sites, e.g. `api/config.py:172`, `auth/bot_pat.py:52`, `substrate/live.py:162,168`). Module bodies must not call `get_settings()` at import — regression test `tests/unit/lambda_handlers/test_import_safety.py:1-10` (SCAR-CW-001 / CP-01 on `services/universal_strategy`); `mcp/tests/test_import_safety*.py` and `mcp` lazy OTel imports apply the same rule. (The prior snapshot's label "GLINT-002" is not found anywhere in `src/` or `tests/` — only in `.know/*.md`; use SCAR-CW-001 for the in-repo anchor.)
- **DEFAULT-DARK / built-inert**: features are env-gated and ship disabled; docstrings state `DEFAULT-DARK: skipped (200) unless <X>_ENABLED is truthy` (`traffic_offer_divergence_tripwire.py:1085-1088`); ~176 "dark/inert" mentions and ~28 `*_ENABLED` env gates. "Byte-identical when inert" is an explicit design goal (`client.py:60-63`). `substrate/__init__.py:1-14` is the model: FROZEN seam contracts (`v1.0-frozen-2026-07-29`), "built DARK beside v1", unfinished bodies raise `NotImplementedError` with an owner tag.
- **Pure-core / I/O-edge split with enforced purity**: `normalizer/scheduling_stratum.py` is import-pure (no persistence, HTTP, AWS SDK, threading, mutation; "TL-A1/B1/B2/B5 enforced by the normalizer fitness tests", `:14-24`); cascade is DATA (`CASCADE_PRIORITY`, `SOURCE_TO_STRATUM`), not a branch chain; `scheduling_extractor.py` is the I/O boundary and the dependency points one way (`normalizer/__init__.py:12-14`). `enrollment/intent_projection.py` and `domain/` follow the same pure-layer rule (`domain/__init__.py:1-6`: "depend on NOTHING in the infrastructure layer"). `contracts/` is deliberately free of repo-internal imports so promotion to `autom8y-core` is a `git mv` (`contracts/__init__.py:1-9`).
- **GFR spine** (`resolution/gfr/engine.py:1-33`): 7 steps — plan, entry (single accounted Asana-API read), guard (identity-path purity), identity read (gid-exact `join=None`), posture, optional tier-2 verify, cardinality. Cache-only hard line (INVARIANT I3): a miss after entry returns `UnresolvedError`, zero further API calls. Invariants are referred to by number (I1-I7).
- **Docstring provenance tags** are pervasive: `Per ADR-####`, `Per TDD-...`, `Per FR-...`, `PRD-...` (≈1096 TDD, 1079 ADR, 1022 FR references across `src`), `SCAR-*` (23) and `RUL-*` (19) markers. New code should cite the governing ADR/TDD the same way; frozen contracts say `FROZEN <version>`.
- **Domain vocabulary** (project-specific meanings): *Business/Unit/Contact/Offer/Process/AssetEdit* + `*Holder` hierarchy (Business root, holders as containers); *cascading field* (field value inherited down the hierarchy); *section* (Asana board column used as lifecycle stage); *stratum* (scheduling provider tier); *posture* (per-field provenance/freshness classification in GFR); *refusal* (typed fail-closed outcome); *warm*/*warmer* (pre-population of the dataframe cache); *dark* (shipped but inert); *receipt* (durable proof record, e.g. `ReceiptPostRequest`, `GenerationReceipt`); *tripwire*; *floodgates*; *DMS* (dead-man switch metric via `emit_success_timestamp`).
- **StrEnum for closed vocabularies** (48 `StrEnum`, 0 `(str, Enum)`, 19 plain `Enum`/`IntEnum`); `Final[frozenset[str]]` for closed string sets (`UNRESOLVED_REASONS`, 9 `: Final` sites total). `UP046/UP047` PEP 695 rules are ignored (`pyproject.toml:249-250`).
- **Builders/options**: configuration is passed as frozen dataclass objects (`RetryConfig`, `TimeoutConfig`, `ConcurrencyConfig`, `CircuitBreakerConfig`) not kwargs; protocol-typed retry (`core/retry.py:143` `RetryPolicy(Protocol)`, `DefaultRetryPolicy :184`, `RetryOrchestrator :564`).
- **Frozen-structure notes**: `query/__main__.py` and `dataframes/builders/progressive.py` are large single files; `substrate/` seam value objects are version-frozen.

## Logging Conventions
- `from autom8y_log import get_logger`; `logger = get_logger(__name__)` at module level — 248 files import it directly (13 import via `autom8_asana.core.logging`, a re-export shim, `core/logging.py:36-40`). 5 modules use explicit names (`"autom8_asana.audit"`, `"autom8_asana.auth"`, `"autom8_asana.api"`, `"autom8_asana.api.write_authz"` at `auth/audit.py:33`, `auth/bot_pat.py:36`, `auth/jwt_validator.py:26`, `api/write_authz.py:85`, `api/dependencies.py:43`). 2 `_logger` outliers: `dataframes/cache_integration.py:40`, `models/business/fields.py:20` — do not replicate.
- **Style (measured via AST over 1,526 `logger.<level>` calls)**: first positional arg is a **snake_case event name** (1,343) rather than a sentence (138) or f-string (32); structured fields go in `extra={...}` (1,024 calls, e.g. `services/ci_task_resolution.py:267-273`) **or** as keyword args (422 calls); 80 calls are message-only. **Correction vs prior**: `extra={}` is the *dominant* style, not an `api/errors.py` outlier. Positional arguments to logger methods are banned by `autom8y.no-logger-positional-args` (`.semgrep.yml:4-23`, excl. tests).
- `autom8y_log`/`logging`/`structlog`/`loguru`/`httpx`/`requests` are banned via ruff `TID251` banned-api (`pyproject.toml:349-363`); carve-outs: `mcp/**` (`:263-270`), `tests/**` (`:288-306`), `_defaults/log.py` (stdlib logging, `pyproject.toml` per-file ignore), `query/__main__.py` T201. `core/logging.py:12-30` documents `intercept_stdlib=True` routing third-party stdlib logs through the pipeline.

## Naming Patterns

- **Types**: `{Noun}Service` (19), `{Resource}sClient` (`TasksClient`, `SectionsClient`), `{Specific}Error`, `{Domain}Config` (frozen dataclass, SDK knobs) vs `{Domain}Settings` (env-bound Pydantic), `{Noun}Result`/`{Noun}Outcome`/`{Noun}Report`/`{Noun}Receipt`, `{Verb}{Resource}Request`/`{Resource}Response` (`CreateTaskRequest`, `RowsResponse`). Protocols are inconsistent: `*Provider` (`AuthProvider`, `LogProvider`), `*Protocol` (`TTLResolverProtocol`, `CreationServiceProtocol`), or role names (`Rebuilder`, `ArtifactStore`, `SingleFlight`, `IdempotencyStore`) — prefer the role/`*Provider` form already used in the package you touch.
- **Refusals/guards**: exceptions and results that fail closed end in `Refused`/`RefusedError`/`Ambiguous`/`Mismatch`; 20 `*Refus*` classes. Guards are `assert_*` functions (26 defs, e.g. `lambda_handlers/scheduling_stratum_snapshot.py:485,946`); other verb prefixes by count: `get_` 63, `build_` 23, `resolve_` 20, `is_` 18, `emit_` 17, `parse_` 14, `format_`/`derive_`/`compute_` 9 each, `check_` 8, `audit_` 3. Async methods use the `_async` suffix (378 defs).
- **Acronyms**: class names use *capitalized-first* form — `Gid*`, `Api*`, `Http*`, `Ttl*`, `Gfr*`, `Mrr*` (counts 6/6/4/5/1/2); ALL-CAPS only in constants and function parameters (`*_GID`). Outliers to avoid spreading: `AIMDConfig`, `TTLSettings`, `TTLResolverProtocol` (ALL-CAPS acronyms in class names; `Ttl` is 5 vs `TTL` 3).
- **Constants**: `SCREAMING_SNAKE` module-level (≈611 definitions); default families `DEFAULT_*` (66), `MAX_*` (13), `MIN_*` (3); env-var-name constants end in `_ENV_VAR` (`TRAFFIC_WINDOW_DAYS_ENV_VAR`); machine error codes `SCREAMING_SNAKE`. Enums are `StrEnum` members in `SCREAMING_SNAKE`.
- **Privacy**: leading underscore for module-private helpers (471 of 1,059 top-level `def`s start with `_`), private modules (`_security.py`, `_response.py`, `_pacer.py`, `_bootstrap.py`, 14 files) and test-only types; `_`-private result types exist (`_UnitOutcome`, `_OfferResult`).
- **Files**: `snake_case.py`; `errors.py` for per-package exceptions (the API package splits `exception_types.py` = typed exceptions and `errors.py` = handlers); `__main__.py` for CLIs (`query/__main__.py`, `metrics/__main__.py`); `cli.py` in `automation/polling/`.
- **Lambda/handler modules**: one module per handler in `lambda_handlers/`, each exporting `handler` (+ optional `handler_async`); package `__init__` re-exports as `{name}_handler` (`lambda_handlers/__init__.py:12-33`).
- **Tag grammar in comments**: `# BROAD-CATCH: <category> -- <reason>`, `# noqa: RULE -- <reason>` (a reason is expected after `--`), `# type: ignore[code]` (321 sites; top: `arg-type` 73, `attr-defined` 68, `no-overload-impl` 48) — `warn_unused_ignores=true` (`pyproject.toml:152`) enforces that stale ignores fail mypy.

## The Layer Model — `.semgrep.yml` (enforced only inside `src/autom8_asana`)

3 rules, all `severity: ERROR`, run in pre-commit with `--error` (`.pre-commit-config.yaml:29-37`):
1. `autom8y.no-logger-positional-args` (`.semgrep.yml:4`).
2. `autom8y.asana-no-lower-imports-api` (`:25`): 19 listed lower packages (`core, models, protocols, transport, clients, batch, _defaults, observability, cache, dataframes, resolution, search, query, metrics, patterns, persistence, services, lifecycle, automation` — `:31-49`) must not import `autom8_asana.api`. **Gap**: 9 of the 28 non-`api` packages are outside `paths.include` and unchecked — `auth`, `contracts`, `domain`, `enrollment`, `lambda_handlers`, `normalizer`, `readout`, `reconciliation`, `substrate` (prior snapshot listed 6; `enrollment`, `readout`, `substrate` are new).
3. `autom8y.no-models-import-upper` (`:61`): `models/`, `protocols/`, `transport/` must not import `services/`/`persistence/`/`lifecycle/`/`automation/`.
Both path globs are `**/src/autom8_asana/{pkg}/`, so semgrep is a no-op for `mcp/`. The file header says the canonical copy is `autom8y/.semgrep.yml` and vendored copies are synced manually (`:2-3`).

## Lint / Format / Type / Coverage Pipeline

- **Ruff** (`pyproject.toml:223-251`): `line-length=100`, `target-version=py312`, `src=["src"]`, `extend-exclude=["examples/","prototypes/","scripts/","tmp/","docs/"]` (`mcp/` NOT excluded). Selected: `E F I UP B G LOG TCH TID SIM T201 ERA`, security subset `S102 S105 S106 S107 S301 S307 S501 S602`, and `BLE001`. Ignored: `E501 B904 B028 B007 B905 G002 G004 G010 G101 UP046 UP047`. Per-file ignores: `mcp/**` (`TID251 TC001-3 ERA001 SIM105`, `:263-270`), `mcp/serve_stdio.py` + `mcp/probes/*.py` (`T201`), `tests/**/*.py` (`F841 E402 F821 E711 F811 F401 B015 B017 B023 TID251 SIM117 SIM102 T201 S`, `:288-306`; does not apply to `mcp/tests` beyond the `mcp/**` entry), `T201` for CLI entry points, `RUF100` for `api/middleware/idempotency.py`.
- **Mypy** `strict = true`, `python_version = "3.12"` (`pyproject.toml:148-152`), `warn_unused_ignores`; scoped to `src/autom8_asana` (pre-commit `uv run mypy src/autom8_asana --ignore-missing-imports --strict`, CI `mypy_targets: 'src/autom8_asana'` at `test.yml:101`, `just typecheck` -> `mypy src/ --strict`, `justfile:90-92`). `mcp/` has no mypy config. A comment states "All ignore_errors overrides removed — mypy strict enforced on all modules" (`pyproject.toml:221`); the only remaining overrides are `ignore_missing_imports` for vendored libs and `follow_imports="silent"` for `tests.harness.substrate_gate.*`.
- **Coverage**: `source=["src/autom8_asana"]`, `branch=true`, `fail_under=80` (`:134-140`); CI per-shard threshold is `0` and an aggregate gate of 80 combines shards (`test.yml:106-109`).
- **Pytest**: `asyncio_mode="auto"`, `timeout=60`, `timeout_method="thread"`, `addopts="--dist=loadgroup"`; markers `slow`, `integration`, `benchmark`, `fuzz`, `scar`, `worker_isolated` (`:117-132`).
- **Pre-commit** (`.pre-commit-config.yaml`): whitespace/EOF/yaml/large-file -> ruff (`--fix --exit-non-zero-on-fix`) + ruff-format (v0.15.2) -> semgrep -> mypy -> gitleaks (v8.30.0) -> hadolint-docker.
- **`just`**: `fmt` (`ruff format .`), `fmt-check`, `lint` (`ruff check . --fix`), `typecheck`, `lint-noqa-drift` (`ruff check src/ --extend-select RUF100`), `test`, `test-cov`, `fitness`, `test-mcp`, composite `check: fmt lint typecheck lint-noqa-drift test` (`justfile:165`). **Correction vs prior**: the recipe is `typecheck`, not `type-check`. RUF100 drift is also a CI job pinned to `ruff@0.15.4` (`test.yml:432-486`); pre-commit ruff is `v0.15.2` — a known lockstep gap.

## Knowledge Gaps

- **Changes since prior version (2026-07-23, d0c8b662 -> c29f58f4)** — material corrections:
  1. `mcp/` tests are no longer an unrun island: CI job `mcp-island` (`.github/workflows/test.yml:489`) and `just test-mcp` (`justfile:145`) exist; `McpToolError.kind` gained `data-integrity-refusal`.
  2. BLE001 is **not** rare: 257 `noqa: BLE001` + 207 `BROAD-CATCH` tags (a named tagging convention); only `receipts_service.py` has a file-level ignore.
  3. Logging style inverted: `extra={...}` is dominant (1,024 vs 422 keyword-arg calls); the prior "keyword-arg preferred" was wrong.
  4. Error lineages: four in `src/` (not two); `ServiceError`/`DataFrameError`/`QueryEngineError`/`GfrError`/`ApiError` root on `Exception`, not `AsanaError`/`Autom8Error`; the `AutomationError`/`CacheConnectionError` family has zero consumers outside `core/errors.py`; `OperatorTokenError` has 3 (not 4) subclasses.
  5. Package/file counts: 29 packages (not 26), 610 .py (not 563), 537 `from __future__` files; new `enrollment/`, `readout/`, `substrate/`; semgrep layer gap grew from 6 to 9 packages.
  6. Dropped as unverifiable in code: the "T-06 logger-parameter" unmigrated-site list (none of the 4 cited sites carries a `logger` parameter at this ref), the `SCAR-DISCRIMINATOR-001` "still unfixed" note (not re-verified; `query/models.py:136-173` shows a callable `Discriminator` on `PredicateNode`), and the `GLINT-002` label.
  7. `just` recipe is `typecheck`; `TimeoutError` shadow and `ErrorDetail` envelope details were re-verified.
- Not exhaustively traced: variable-level naming (receiver names, abbreviations) beyond acronym/prefix conventions; `automation/` sub-package internal structure beyond file lists; `cache/` and `dataframes/` internal layering; `search/`, `batch/` surfaces.
- The free-form `BROAD-CATCH` category vocabulary has no registry file in `src/`; the authoritative taxonomy is only referenced from `.know/scar-tissue.md` and `docs/runbooks/RUNBOOK-freshness-verification-recency.md`.
- `api/errors.py` defines `fleet_error_handler` (`:677`) but it is not in `register_exception_handlers` (`:771-831`); whether it is registered by `autom8y_api_middleware` was not traced.
- Whether the in-CI `mcp-island` job also installs `mypy`/semgrep for `mcp/` — it does not (job runs pytest only); typing/lint rule parity for `mcp/` is therefore ruff-only.

## Experiential Observations (from `.sos/land/workflow-patterns.md`)

Cross-session corpus (18 sessions, generated 2026-04-28; 14d expiry long lapsed): Bash-dominant tooling (417 Bash vs 185 Edit vs 42 Write across 8 grepped sessions). The land file's "33 inviolable SCAR tests" is stale versus code: `pytest.mark.scar` occurs **46** times across 17 test files at this ref (unchanged from the prior pass). Parametrize adoption measured at this ref: 115 of 726 `test_*.py` files (15.8%) use `pytest.mark.parametrize` (261 uses; prior pass: 91 of 739). The land file's file-change hotspots (`api/models.py`, `api/routes/tasks.py`, `clients/data/*`, `services/gid_push.py`) coincide with the large-file list above. The land file's "86.8% local-fixture ratio" anti-pattern claim is an experiential observation and was not re-verified (test-coverage domain).
