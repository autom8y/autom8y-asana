---
type: audit
---
# SLOP-CHOP-DEEP Detection Report

**Phase**: 1 — Detection
**Specialist**: hallucination-hunter
**Date**: 2026-02-25
**Scope**: `src/autom8_asana/` + `tests/` + `src/autom8_query_cli.py`
**Initiative Context**: Post ASANA-HYGIENE + REM-ASANA-ARCH + REM-HYGIENE + COMPAT-PURGE

---

## Executive Summary

| Severity | Count | Gate Impact |
|----------|-------|-------------|
| CRITICAL  | 0     | —           |
| HIGH      | 1     | FAIL        |
| MEDIUM    | 1     | Advisory    |
| LOW       | 0     | —           |

**Overall**: 1 blocking finding (HH-DEEP-001), 1 advisory finding (HH-DEEP-002). No phantom imports to non-existent modules. No surviving references to COMPAT-PURGE deleted symbols. Both P1 carry-forward items (H-001, H-002) confirmed FIXED. All new modules introduced since P1 have clean import surfaces. PyYAML dependency drift is an advisory concern with production impact risk.

---

## Findings

### HH-DEEP-001: Fragile phantom-adjacent patch target in health check tests (HIGH)

- **Severity**: HIGH
- **Confidence**: PROBABLE
- **Category**: orphaned-mock
- **Files**:
  - `tests/unit/api/test_health.py:274`
  - `tests/unit/api/test_health.py:289`
  - `tests/unit/api/test_health.py:304`
  - `tests/unit/api/test_health.py:319`
  - `tests/unit/api/test_health.py:328`
  - `tests/unit/api/test_health.py:342`
- **Evidence**:

  Production code in `src/autom8_asana/api/routes/health.py:176-221` wraps all JWKS HTTP calls through `Autom8yHttpClient`:

  ```python
  # health.py:176-182  — imports from autom8y_http, not httpx directly
  from autom8y_http import (
      Autom8yHttpClient,
      HttpClientConfig,
      RequestError,
      TimeoutException,
  )
  ...
  async with Autom8yHttpClient(_jwks_config) as client:
      async with client.raw() as raw_client:
          response = await raw_client.get(jwks_url)
  ```

  The tests patch at the `httpx.AsyncClient` class level and raise bare `httpx` exception types:

  ```python
  # test_health.py:274
  with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
      mock_get.return_value = mock_response

  # test_health.py:289
  with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
      mock_get.side_effect = httpx.TimeoutException("timeout")

  # test_health.py:304
  with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
      mock_get.side_effect = httpx.ConnectError("connection failed")
  ```

  **Why it currently works (exception side)**: Confirmed via runtime introspection that `autom8y_http.TimeoutException` IS `httpx.TimeoutException` — `autom8y_http` re-exports httpx exceptions rather than wrapping them. So raising `httpx.TimeoutException` in the test IS caught by `except TimeoutException` in production. Same for `RequestError`/`ConnectError`.

  **Why it currently works (patch side)**: Confirmed via `inspect.getsource(Autom8yHttpClient.raw)` that `raw()` is typed as `AsyncIterator[httpx.AsyncClient]` and returns the underlying `httpx.AsyncClient` instance. Patching `httpx.AsyncClient.get` at the class level intercepts the method on any instance, including the one returned by `raw()`.

  **Why it is HIGH despite currently working**: The patch bypasses `Autom8yHttpClient` entirely — it reaches through the abstraction and patches the httpx internals directly. This makes the tests:
  1. Dependent on `autom8y_http` re-exporting httpx exceptions (not a contractual guarantee — if `autom8y_http` ever wraps exceptions in its own types, these tests silently stop exercising the catch branches)
  2. Dependent on `raw()` continuing to return a plain `httpx.AsyncClient` rather than a subclass or proxy (any change to the `raw()` implementation breaks the class-level patch)
  3. Misaligned with the canonical mock pattern for this codebase: all other tests that use `Autom8yHttpClient` patch it at the module import site (`autom8_asana.<module>.Autom8yHttpClient`), not at the httpx class level

  The correct patch target — consistent with H-001 and H-002 fixes applied in REM-HYGIENE — is:
  ```python
  with patch("autom8_asana.api.routes.health.Autom8yHttpClient") as mock_cls:
  ```

- **Impact**: Tests for JWKS degradation paths (timeout, connection error, invalid response) are decoupled from the actual call chain. Any `autom8y_http` version bump that changes exception inheritance or the `raw()` return type silently breaks the test assertions without causing test failures. The coverage gap is in the exception-handling branches of `/health/deps`.
- **Interview**: NO

---

### HH-DEEP-002: PyYAML used in production code without declared dependency (MEDIUM)

- **Severity**: MEDIUM
- **Confidence**: DEFINITE
- **Category**: dependency-drift
- **Files**:
  - `src/autom8_asana/lifecycle/config.py:24`
  - `src/autom8_asana/automation/polling/config_loader.py:30`
  - `src/autom8_asana/query/saved.py:16`
- **Evidence**:

  Three production source files import `yaml` at module level:

  ```python
  # lifecycle/config.py:24
  import yaml

  # automation/polling/config_loader.py:30
  import yaml

  # query/saved.py:16
  import yaml
  from pydantic import BaseModel, Field, model_validator
  ```

  `pyproject.toml` `[project.dependencies]` does NOT include `PyYAML` or `pyyaml`:

  ```toml
  dependencies = [
      "httpx>=0.25.0",
      "pydantic>=2.0.0",
      "pydantic-settings>=2.0.0",
      "asana>=5.0.3",
      "polars>=0.20.0",
      "arrow>=1.3.0",
      "autom8y-config>=0.4.0",
      "autom8y-http[otel]>=0.5.0",
      "autom8y-cache>=0.4.0",
      "autom8y-log>=0.5.5",
      "opentelemetry-instrumentation-httpx>=0.42b0",
      "autom8y-core>=1.1.0",
      "autom8y-telemetry[fastapi]>=0.3.0",
      "boto3>=1.42.19",
  ]
  ```

  `pyproject.toml` contains a mypy override to suppress `yaml` type errors:
  ```toml
  [[tool.mypy.overrides]]
  module = "yaml.*"
  ignore_missing_imports = true
  ```
  This indicates awareness that `yaml` lacks stubs, but does not substitute for a dependency declaration.

  `uv.lock` confirms `pyyaml 6.0.3` is present in the resolved environment, but only as a transitive dependency of `moto>=5.0.0` (a dev-only testing dependency). Verified by tracing `uv.lock` dependency chains for all 14 production packages: none declare `pyyaml` as a direct or transitive dependency.

  Production dependency chain for all 14 declared packages (verified via `uv.lock`):
  - `autom8y-config 0.4.0` → `pydantic`, `pydantic-settings` (no yaml)
  - `autom8y-core 1.1.0` → `httpx`, `pydantic` (no yaml)
  - `autom8y-http 0.5.0` → `autom8y-log`, `httpx` (no yaml)
  - `autom8y-cache`, `autom8y-log`, `autom8y-telemetry`, `autom8y-auth` → no yaml
  - `boto3`, `asana`, `polars`, `arrow`, `pydantic`, `pydantic-settings` → no yaml

  `pyyaml` only appears in the lockfile as a dependency of `moto` (dev extra) and `responses` (also dev).

- **Impact**: `ImportError: No module named 'yaml'` at runtime in production deployments. Specifically:
  - `autom8-query run <name>` CLI fails at the `import yaml` in `query/saved.py` on first use of the `run` subcommand
  - Lifecycle config parsing (`lifecycle/config.py`) fails on service startup if YAML config files are present
  - Polling config loader (`automation/polling/config_loader.py`) fails when polling mode is activated
  The failure mode is silent in dev/test environments (where `moto` is installed via dev extras and pulls in PyYAML transitively), making this undetectable without clean-environment testing.
- **Interview**: NO

---

## Carry-Forward Verification

### H-001: Phantom `autom8_asana.clients.data.client.httpx.AsyncClient` patch target

**Status: FIXED**

P1 (SLOP-CHOP-TESTS-P1) found `tests/unit/clients/data/test_client.py` was patching the non-existent `autom8_asana.clients.data.client.httpx.AsyncClient` at 10+ sites. Current state verified: all sites now correctly patch `autom8_asana.clients.data.client.Autom8yHttpClient`.

Confirmed patch targets at lines 213, 242, 271, 294, 317, 334, 351, 372, 389, 524 — all corrected. H-001 fully resolved.

---

### H-002: Phantom `autom8_asana.services.gid_push.httpx.AsyncClient` patch target

**Status: FIXED**

P1 found `tests/unit/services/test_gid_push.py` was patching `autom8_asana.services.gid_push.httpx.AsyncClient`. Current state verified: tests now patch `autom8_asana.services.gid_push.Autom8yHttpClient` (correct).

The file still contains `import httpx` and uses `httpx.Response(...)` as mock return value constructors — this is legitimate. `httpx` is a declared production dependency (`httpx>=0.25.0`), and `httpx.Response` is the natural object to construct test response fixtures. No phantom here. H-002 fully resolved.

---

## Clean Areas

The following areas were scanned and showed no import resolution failures, phantom references, or dependency drift:

**COMPAT-PURGE orphan sweep — all CLEAN:**

| Removed symbol | Search result |
|---|---|
| `ProcessType.GENERIC` | 0 references in src/ or tests/ |
| `LEGACY_ATTACHMENT_PATTERN` | 0 references in src/ or tests/ |
| `ProgressiveBuildResult` | 0 references in src/ or tests/ |
| `warm_struc_async` | 0 references in src/ or tests/ |
| `_StubReopenService` | 0 references in src/ or tests/ |
| `from autom8_asana.core.schema import ...` | 0 references — `core/schema.py` deleted, no orphaned imports |
| `from autom8_asana.cache import dataframe_cache` | 0 references — lazy-load removed, `__getattr__` now only handles `register_asana_schemas` |
| `from autom8_asana.cache import Freshness` (old lazy-load path) | 0 references — `Freshness` now directly imported from `autom8y_cache` at top of `cache/__init__.py` |
| `from autom8_asana.clients.data.client import mask_phone_number` | 0 references — all callers import from canonical `autom8_asana.clients.data._pii` |
| `from autom8_asana.models.business.detection.types import EntityType` | 0 references — `EntityType` re-export removed; `detection/types.py` still exists for its own types |
| `from autom8_asana.automation.seeding import <field_utils symbols>` | 0 references |
| `from autom8_asana.models.business.patterns import <constant aliases>` | 0 references |
| `from autom8_asana.cache.models.freshness import ...` | 0 references — `cache/models/freshness.py` confirmed deleted |

**REM-ASANA-ARCH import drift — all CLEAN:**
- All imports from `autom8_asana.models.business.detection.types` reference types that still live there (`DetectionResult`, `EntityTypeInfo`, confidence constants) — 9 files verified
- `core/types.py`, `core/string_utils.py`, `core/field_utils.py`, `core/registry.py` — all present
- `protocols/insights.py`, `protocols/metrics.py`, `protocols/dataframe_provider.py` — directory intact

**New module import verification — all CLEAN (except HH-DEEP-002):**

| Module | Import issues |
|---|---|
| `query/offline_provider.py` | None — all imports resolve |
| `query/temporal.py` | None — stdlib + TYPE_CHECKING guards only |
| `query/saved.py` | PyYAML undeclared (HH-DEEP-002) |
| `query/cli.py` | None — delegates to `query.__main__` |
| `query/__main__.py` | None — all lazy imports verified present; `httpx` use is intentional with TID251 suppression |
| `dataframes/offline.py` | None — `boto3` and `polars` both declared |
| `metrics/__main__.py` | None — all imports resolve |
| `metrics/compute.py` | None — `polars` declared, TYPE_CHECKING guard on `Metric` |
| `autom8_query_cli.py` (root) | None — stdlib only + lazy `query.__main__` |

**httpx phantom sweep — CLEAN (with scope note):**
- No test files patch `httpx.AsyncClient` as a module-level name on a production module that does not import httpx
- `test_health.py` patch of `httpx.AsyncClient.get` is valid at present (see HH-DEEP-001 for fragility analysis)
- `test_cli.py` patches `httpx.post` — correct because `query/__main__.py` imports `httpx` at runtime for `--live` mode
- `test_gid_push.py` uses `httpx.Response(...)` as fixture constructors only — legitimate

**Declared dependency cross-reference — CLEAN (except HH-DEEP-002):**
- All platform SDK imports (`autom8y_http`, `autom8y_log`, `autom8y_cache`, `autom8y_config`, `autom8y_core`, `autom8y_telemetry`, `autom8y_auth`) — declared in `pyproject.toml`
- `boto3`, `polars`, `arrow`, `pydantic`, `pydantic-settings`, `asana`, `httpx` — all declared
- `autom8y_core.errors.TokenAcquisitionError`, `autom8y_core.Config`, `autom8y_core.TokenManager` — used in `query/__main__.py` and `auth/service_token.py`; `autom8y-core>=1.1.0` declared

---

## Interview Escalation Items

None.

**Ambiguities resolved internally (confidence log):**

1. **`httpx.AsyncClient.get` patch in health tests** — Initially flagged as potential phantom. Resolved via `inspect.getsource(Autom8yHttpClient.raw)` confirming return type is `httpx.AsyncClient`, and via runtime MRO inspection confirming `autom8y_http.TimeoutException is httpx.TimeoutException`. Retained as HIGH for fragility, not CRITICAL (currently functional). Confidence: PROBABLE.

2. **`_children_cache` references** — Scanned post-COMPAT-PURGE. Confirmed `_children_cache` still exists as a legitimate `PrivateAttr` in `models/business/base.py:85`. COMPAT-PURGE removed the *dual-write* shim (writing to both old and new attribute names simultaneously), not the attribute itself. Not a finding.

3. **`autom8_asana.cache.dataframe_cache` patch targets** — P1 flagged as H-FP-001 (not a hallucination, worked via `__getattr__` lazy-load). Confirmed `__getattr__` now only handles `register_asana_schemas`; searched for any remaining `autom8_asana.cache.dataframe_cache` patch targets — none found. The legacy targets were cleaned up during REM-HYGIENE. Not a finding.

---

## Handoff Checklist

- [x] Every file in review scope scanned for import/dependency issues
- [x] Each finding includes file path, line number, resolution failure reason
- [x] Dependency manifest (`pyproject.toml`) cross-referenced against all new module imports
- [x] Lockfile (`uv.lock`) analyzed to determine transitive vs. direct dependency status for PyYAML
- [x] Severity assigned: HIGH (fragile mock — HH-DEEP-001), MEDIUM (undeclared dep — HH-DEEP-002)
- [x] No files skipped without documented reason

**Ready for logic-surgeon.**
