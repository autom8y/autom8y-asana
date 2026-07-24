---
domain: conventions
generated_at: "2026-07-23T14:56:44Z"
expires_after: "7d"
source_scope:
  - "./src/**/*.py"
  - "./mcp/**/*.py"
  - "./pyproject.toml"
generator: theoros
source_hash: "70d45434e1e79ce7bc380936e47a4e265447ffd4db88dc37cd8b37edc70b862f"
confidence: 0.86
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 3
land_sources:
  - ".sos/land/workflow-patterns.md"
land_hash: "9db9c6f33d48f5c2fce398de7d3359fef30a0a0bd809044f7259f792ee6c4b9e"
---

# Codebase Conventions

> Fresh full-observation pass at synced HEAD `d0c8b662` (2026-07-23). Covers `src/autom8_asana` conventions plus the domain idioms (GFR, normalizer ACL, `contracts/`), the semgrep layer model, the full lint/type/coverage pipeline, and the `mcp/` island's participation (or non-participation) in each.

## Error Handling Style

Two coexisting hierarchy roots in `src/autom8_asana`, plus a **third, wholly separate** hierarchy in the `mcp/` island.

### Exception Hierarchy — `src/autom8_asana`

1. **`AsanaError(Exception)`** (`errors.py`, 587 lines) — SDK/HTTP-facing root; `message`/`status_code`/`response`/`errors`. `from_response()` is the canonical HTTP→exception factory via `_STATUS_CODE_MAP` (401→Authentication, 403→Forbidden, 404→NotFound, 410→Gone, 429→RateLimit, 5xx→Server). Subclasses incl. `GoneError`, `NameNotFoundError`, `HydrationError`, `InsightsError`+3, `ExportError`, and 4 `OperatorTokenError` subclasses (incl. `OperatorBatchVersionSkewError`).
2. **`Autom8Error(Exception)`** (`core/errors.py`) — cross-cutting infra root; `message`/`context`/`cause` (sets `__cause__` explicitly). Declares `transient: bool` class var (`TransportError`→`S3TransportError`/`RedisTransportError` computed classification; `CacheError`; `AutomationError`→`RuleExecutionError`/`SeedingError`/`PipelineActionError`).

**Per-domain error modules** (one `errors.py` per package): `services/errors.py` (`ServiceError`→…`CacheNotWarmError`), `persistence/errors.py`, `dataframes/errors.py`, `query/errors.py`, `api/exception_types.py` (`ApiError`→`ApiAuthError`), `resolution/gfr/errors.py` (`GfrError` family + closed-vocab `UNRESOLVED_REASONS`).

### Error Creation, Wrapping, Classification
- Domain errors: `raise DomainSpecificError(f"…{field}")`. Config validation in `__post_init__` of frozen dataclasses.
- Transport-boundary wrapping: vendor errors (botocore, redis) wrapped into `TransportError` subclasses (`S3TransportError.from_boto_error`); upstream never imports vendor types.
- Import-safe tuple constants in `core/errors.py` (`CACHE_TRANSIENT_ERRORS`, `S3_TRANSPORT_ERRORS`, etc.) built with try/except `ImportError`.
- `RetryableErrorMixin` (`patterns/error_classification.py`) computes `is_retryable`/`recovery_hint`/`retry_after_seconds` per ADR-0079 (429/5xx retryable). Requires `HasError(Protocol)`.
- No bare `raise Exception(...)` at domain-logic sites; no bare `except:` in `src/autom8_asana`. `except CACHE_TRANSIENT_ERRORS as exc: logger.warning(...)` swallows only transient cache errors. `services/receipts_service.py` carries a deliberate `noqa: BLE001` blind-except boundary ("a receipt must never fail on the stage write"); `idempotency.py:770` keeps an inert `# noqa: BLE001` as a SCAR-IDEM-001 regression guard.

### `mcp/` — a Third, Disjoint Error Taxonomy
`mcp/asana_mcp/errors.py` defines **`McpToolError(Exception)`** — does NOT subclass `AsanaError`/`Autom8Error`. Flat single-class taxonomy distinguished by a `kind` field (`warming|auth|rate_limit|client|not_found|server`), `retryable: bool`, and `to_tool_payload()` (LLM-legible flat dict). Load-bearing invariant: a cold-frame `503` surfaces as `kind="warming"` (retryable), NEVER auth-shaped (the `query503` scar), asserted disjoint by `mcp/tests/test_errors_c3.py`. **No `get_logger`/`logging`/`structlog` import anywhere in `mcp/asana_mcp/*.py`** — the island has NO structured logging surface; error context travels only via the payload + OTel spans.

## File Organization

`src/autom8_asana/` — 26 top-level packages (563 .py, 492 with `from __future__ import annotations`). NEW since prior snapshot: `normalizer/` (scheduling ACL), `contracts/` (cross-repo envelope), `domain/` (`forwarding_stage.py`, `forwarding_stage_backfill.py`), `resolution/gfr/`.

Naming: service files `{entity}_service.py`; clients `{resource}s.py`; error modules `errors.py`; route models `{route}_models.py`; internal helpers `_`-prefixed; CLI `__main__.py`. `config.py` (frozen dataclasses + `__post_init__`) vs `settings.py` (Pydantic-settings env binding) kept structurally separate. `__all__` present in all major `__init__.py`.

### `mcp/` Island — Structurally Separate Root
`mcp/` is its OWN top-level directory (not a subpackage of `src/autom8_asana/`): `mcp/asana_mcp/` (assembly, bridge, context, envelopes, errors, observability, schemas, server, settings, timeouts), `mcp/probes/`, `mcp/tests/` (26 test files + conftest), `mcp/serve_stdio.py`. 48 .py total. Imports `httpx` directly (3 files); documented as a REFERENCE-POSTURE PROTOTYPE ("throwaway, never promoted") with a ZERO-domain-SDK-coupling invariant (never imports `autom8_asana`).

## Domain-Specific Idioms

- **Dual sync/async surface**: `_async` suffix; `SyncInAsyncContextError` when sync-inside-async detected.
- **GID as string**: always `str`, `r"^\d{1,64}$"` (strict prod, relaxed test); `GidStr` Pydantic v2 annotated alias.
- **GFR (`resolution/gfr/`)**: 7-step orchestration spine (plan → entry [single accounted Asana-API read] → guard [identity-path purity] → identity read [gid-exact, `join=None`] → posture → optional tier-2 → cardinality). Cache-only hard line (I3): a downstream miss returns `UnresolvedError`, zero further API calls. Closed-vocab `UNRESOLVED_REASONS` frozenset — every failure is a named domain subclass; no bare Exception raised/caught in the package.
- **Normalizer ACL (`normalizer/`)**: strict one-way split — `scheduling_stratum.py` pure resolver (import-pure: no persistence/service-client/HTTP/AWS-SDK/threading, no mutation) + `scheduling_extractor.py` I/O boundary. Pure module imports NOTHING from the extractor.
- **`contracts/vocabulary_sync.py`**: typed producer-side envelope, zero internal imports (`[PROPOSE — promote to autom8y-core]`); Lock-2 (`field_key: Literal["vertical"]` + `extra="forbid"`) and Lock-3 (`vertical_key = normalize(option.name)`, never a GID) as inline named invariants.
- **Config as frozen dataclasses**, **Protocol-based DI** (`@runtime_checkable` where `isinstance` needed), **Result types as dataclasses**, **Import-safe tuple constants** — carried forward.
- **Logging via `autom8y_log`**: `logger = get_logger(__name__)` module-level. Keyword-arg/structlog style preferred; `extra={}` style in `api/errors.py`. `autom8y_log`/stdlib logging/structlog/loguru all banned repo-wide via `TID251`; `mcp/**` is a carve-out (and uses no logging at all). 2 `_logger` outliers (`dataframes/cache_integration.py:40`, `models/business/fields.py:20`) — do not replicate.
- **Anti-patterns named in-repo**: GLINT-002 config-during-init cold-start (defer to `@functools.cache` lazy accessor; regression-gated by `test_import_safety.py`); CSI-001 Pydantic `Field(examples=[...])` plural-only; SCAR-DISCRIMINATOR-001 (`query/models.py` dict-only discriminator, still unfixed); `CacheNotWarmError` no local redefinition.

## Naming Patterns

`{Noun}Service`, `{Action}{Resource}Request`/`{Resource}Response`, `{Noun}Result`, `{Specific}Error`, `{Domain}Config`, `{Resource}sClient`, `{Noun}Protocol`. Async `_async` suffix; audit fns `audit_`; health checks `check_`; GFR guards `assert_`; normalizer `derive_`/`format_`/`build_`. Logger canonical name `logger`. `logger`-parameter T-06: 4 sites still unmigrated (`clients/data/_response.py:65,197`, `persistence/holder_ensurer.py:72`, `persistence/cache_invalidator.py:41`, `services/vertical_backfill.py:63`). Machine-readable error codes `SCREAMING_SNAKE_CASE`.

## The Layer Model — `.semgrep.yml` (Enforced Only Inside `src/autom8_asana`)

3 architecture rules (all `severity: ERROR`, run via pre-commit):
1. `autom8y.no-logger-positional-args` — bans positional args to `logger.*` (excl. tests).
2. `autom8y.asana-no-lower-imports-api` — 19 named lower packages must not import `autom8_asana.api` (Layer 5). **NOTE (gap)**: `auth/`, `contracts/`, `domain/`, `lambda_handlers/`, `normalizer/`, `reconciliation/` are NOT in the `paths.include` — 6 of 26 non-api packages are structurally invisible to this guard (see Design Constraints TENSION-014).
3. `autom8y.no-models-import-upper` — `models/`/`protocols/`/`transport/` (Layers 1-2) must not import `services/`/`persistence/`/`lifecycle/`/`automation/` (Layers 3-4).

Both content rules' `paths.include` globs are `**/src/autom8_asana/{subpackage}/` — for files under `mcp/` no rule pattern matches, so semgrep is a silent no-op there.

## Full Lint / Format / Type-Check Pipeline

- **Ruff** (`pyproject.toml`): `line-length=100`, `target-version=py312`, `src=["src"]`, `extend-exclude=["examples/","prototypes/","scripts/","tmp/","docs/"]` (`mcp/` NOT excluded — default rule set applies to `mcp/**` with per-file carve-outs). `mcp/**` per-file-ignores: `TID251` (sanctioned httpx), `TC001/TC002/TC003`, `ERA001`, `SIM105`. `mcp/serve_stdio.py`/`mcp/probes/*` also `T201`. `tests/**/*.py` broad relaxation — but `mcp/tests/**` is NOT listed separately, so it inherits only the `mcp/**` carve-outs.
- **Mypy** `strict=true` — scoped to `src/autom8_asana` (pre-commit `mypy src/autom8_asana --strict`; CI `mypy_targets: 'src/autom8_asana'`). **`mcp/` is not type-checked by this pipeline at all** (`mcp/pyproject.toml` has no `[tool.mypy]`).
- **Coverage**: `source=["src/autom8_asana"]`, `branch=true`, `fail_under=80`. CI aggregate gate combines 4 shards. **`mcp/` has zero coverage instrumentation.**
- **Test collection**: `testpaths=["tests"]`, `addopts="--dist=loadgroup"`. `mcp/tests/` (26 files) is NOT collected by root pytest, `just test`, or any CI workflow (grep confirms zero `mcp` references across `.github/workflows/`) — a genuinely disjoint test island.
- **Pre-commit**: trailing-whitespace/eof/check-yaml/check-added-large-files → ruff (`--fix`) + ruff-format (repo-wide incl. `mcp/`) → semgrep (src-scoped) → mypy (src-scoped) → gitleaks (repo-wide) → hadolint-docker.
- **`just`**: `fmt` (`ruff format .`), `lint` (`ruff check . --fix`, repo-wide), a dedicated `ruff check src/ --extend-select RUF100` noqa-drift check, `type-check` (`mypy src/ --strict`), `test*` (all `tests/`-rooted). RUF100 drift also a CI job pinned to `ruff@0.15.4`.

## Knowledge Gaps

- `mcp/tests/**` per-file-ignore scoping (inherits only `mcp/**`, not the broad `tests/**` relaxations) — intentional-vs-oversight unresolved.
- `automation/` sub-packages, `lifecycle/engine.py` Protocol inventory, `search/`, `batch/` surfaces not individually re-traced.
- Whether `autom8y-core`'s cited `VerticalsListResponse` precedent has landed (out of repo scope).
- `mcp/` CI execution: confirmed absent from `.github/workflows/*.yml` + `justfile`; whether it runs via an external/manual satellite pipeline not verifiable from within this repo.

## Experiential Observations (from `.sos/land/workflow-patterns.md`)

Cross-session corpus (18 sessions): Bash-dominant tooling; Edit correlates with productive sessions. SCAR test cluster: the land file's "33 inviolable" is stale — direct grep at `d0c8b662` = **46** `@pytest.mark.scar` across 17 files. Parametrize adoption: 91 of 739 test files (~12.3%), past the ≥8% target. [Experiential; the 86.8%-local-fixture-ratio anti-pattern claim not re-verified this pass.]
