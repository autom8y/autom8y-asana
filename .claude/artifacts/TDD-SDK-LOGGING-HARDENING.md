# TDD: SDK & Logging Hardening (5-Gap)

**Status**: Draft
**Date**: 2026-02-13
**Author**: Architect Agent
**Upstream**: SPIKE-sdk-version-logging-gaps.md
**PR Strategy**: Single PR, atomic logical commits on main

---

## Overview

This TDD specifies a 5-gap hardening initiative to align autom8_asana's SDK dependencies, type checking, lint rules, and logging primitives with platform standards. The work addresses a production risk (autom8y-auth 1.0.0 JWT crash), SDK feature gaps (autom8y-log 0.3.2 lacks `*args` adapter hardening), lint coverage gaps (no G/LOG rules), and 4 remaining stdlib logging holdouts.

**Scope**: 5 gaps, single PR, approximately 8 files changed + lockfile.

---

## Gap 1: Lockfile & Floor Specs

### Rationale

autom8y-auth 1.0.0 has a known TypeError crash in JWT validation. autom8y-log 0.3.2 lacks the adapter hardening that safely handles `*args` positional formatting. The floor specs in `pyproject.toml` must be bumped to prevent resolution to these broken versions.

### Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Bump floor specs for auth and log |
| `uv.lock` | Re-resolve with upgraded packages |

### Exact Edits

**pyproject.toml line 18** -- change autom8y-log floor:
```
Before: "autom8y-log>=0.3.2",
After:  "autom8y-log>=0.4.0",
```

**pyproject.toml line 41** -- change autom8y-auth floor (in `[project.optional-dependencies] auth`):
```
Before: "autom8y-auth[observability]>=1.0.0",
After:  "autom8y-auth[observability]>=1.0.1",
```

**pyproject.toml line 65** -- change autom8y-auth floor (in `[project.optional-dependencies] dev`):
```
Before: "autom8y-auth[observability]>=1.0.0",  # Required for test_auth tests
After:  "autom8y-auth[observability]>=1.0.1",  # Required for test_auth tests
```

**Lockfile update command**:
```bash
uv lock --upgrade-package autom8y-auth --upgrade-package autom8y-log
```

### Verification

```bash
# Confirm locked versions
grep -A1 'name = "autom8y-auth"' uv.lock | head -4
grep -A1 'name = "autom8y-log"' uv.lock | head -4

# Verify installation resolves correctly
uv sync --all-extras

# Run full test suite to confirm no regressions
.venv/bin/pytest tests/ -x -q --timeout=60
```

---

## Gap 2: mypy Override Removal

### Rationale

`autom8y_telemetry` ships a `py.typed` marker, making the `ignore_missing_imports = true` override unnecessary. Removing it allows mypy to surface any type errors currently hidden by the blanket ignore. The stakeholder decision requires fixing any surfaced type errors in this PR.

### Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Delete the autom8y_telemetry mypy override block |

### Exact Edits

**pyproject.toml lines 117-119** -- delete the entire override block:
```toml
# DELETE these 3 lines:
[[tool.mypy.overrides]]
module = "autom8y_telemetry.*"
ignore_missing_imports = true
```

### Type Error Handling Strategy

The single usage of `autom8y_telemetry` in production code is in `src/autom8_asana/api/main.py` (lines 105-109), where `InstrumentationConfig` and `instrument_app` are imported inside a try/except ImportError block. Since this is a lazy import guarded by try/except, mypy may flag the symbols as potentially unbound in the `except ImportError` `pass` branch. This is already handled correctly -- the lazy import pattern at line 82-86 of `autom8y_telemetry/__init__.py` shows that `InstrumentationConfig` and `instrument_app` may not be defined if the `[fastapi]` extra is not installed.

If mypy surfaces errors:
- For `Cannot find implementation or library stub` errors: These should NOT occur since `py.typed` is present. If they do, investigate the `py.typed` marker location.
- For type mismatch errors on `InstrumentationConfig` or `instrument_app`: Fix the types at the call site in `api/main.py`.
- For any other surfaced errors: Fix inline in this PR per stakeholder decision.

### Verification

```bash
# Run mypy with strict mode (matches pyproject.toml config)
.venv/bin/mypy src/autom8_asana/ --config-file pyproject.toml

# Compare error count before and after (should be same or fewer)
# If new errors surface, fix them before proceeding
```

---

## Gap 3: Ruff G/LOG Rules

### Rationale

The codebase has no lint enforcement for logging format strings or logging best practices. Adding `G` (flake8-logging-format) and `LOG` (flake8-logging) rule groups catches common logging anti-patterns while respecting the project's intentional `%s` lazy formatting convention (FR-LOG-005).

### Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Add G and LOG to ruff select, configure ignores |

### Exact Edits

**pyproject.toml line 143** -- expand ruff select:
```toml
Before: select = ["E", "F", "I", "UP", "B"]
After:  select = ["E", "F", "I", "UP", "B", "G", "LOG"]
```

**pyproject.toml lines 144-150** -- add G-rule ignores to the existing ignore list:
```toml
Before:
ignore = [
    "E501",   # Line length handled by formatter
    "B904",   # raise-without-from-inside-except - common pattern in HTTP handlers
    "B028",   # stacklevel in warnings - not critical for tests
    "B007",   # unused loop variable - often intentional for unpacking
    "B905",   # zip-without-strict - not needed for equal-length iterables
]

After:
ignore = [
    "E501",   # Line length handled by formatter
    "B904",   # raise-without-from-inside-except - common pattern in HTTP handlers
    "B028",   # stacklevel in warnings - not critical for tests
    "B007",   # unused loop variable - often intentional for unpacking
    "B905",   # zip-without-strict - not needed for equal-length iterables
    "G002",   # %-format in logging is intentional (FR-LOG-005 lazy formatting)
    "G004",   # f-string in logging - we prefer lazy %s but don't ban f-strings
    "G010",   # logging.warn() deprecated -> logging.warning() (auto-fixable)
]
```

### Rule Reference

| Rule | Description | Action |
|------|-------------|--------|
| G001 | logging-string-concat (`"msg" + var`) | **Enabled** -- always wrong |
| G002 | logging-percent-format (`%s`) | **Ignored** -- intentional per FR-LOG-005 |
| G003 | logging-string-format (`.format()`) | **Enabled** -- catches anti-pattern |
| G004 | logging-f-string | **Ignored** -- not banned, but `%s` preferred |
| G010 | logging.warn() deprecated | **Ignored** -- auto-fixable but adds noise; no instances exist in codebase |
| G1xx | Other G rules | **Enabled** by default with G group |
| LOG001-LOG015 | flake8-logging rules | **Enabled** -- logging best practices |

Note on G010: Added to ignore list as a safety net. There are currently zero `logging.warn()` calls in the codebase, but ignoring it prevents false positives from third-party code or future additions. The stakeholder explicitly requested adding G010 to the ignore list.

### Verification

```bash
# Run ruff check to verify no violations with new rules
.venv/bin/ruff check src/ tests/ --select G,LOG

# Verify ignored rules produce no output
.venv/bin/ruff check src/ --select G002,G004,G010

# Full ruff check (should match CI)
.venv/bin/ruff check src/ tests/
```

---

## Gap 4: Middleware Logging Migration

### Design Decision: Migrate Fully to SDK

**Decision**: Replace the hand-rolled `configure_structlog()` function and direct structlog usage in `api/middleware.py` with the SDK's `configure_logging()` via `autom8_asana.core.logging.configure()`, using the SDK's `additional_processors` parameter to inject the `_filter_sensitive_data` processor.

### ADR: Middleware Logging Approach

**Context**: `api/middleware.py` currently maintains its own `configure_structlog()` function that directly calls `structlog.configure()` with a hand-built processor chain. This creates a parallel logging configuration path that bypasses the SDK entirely. The middleware also imports `logging.Logger` for the type hint on the `_filter_sensitive_data` processor's `_logger` parameter.

**Options Evaluated**:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A. Keep structlog direct | Leave middleware.py as-is | Zero change risk | Two logging configs competing; `structlog.configure()` is last-writer-wins, creating boot-order bugs between `core.logging.configure()` and `configure_structlog()` |
| B. Hybrid: SDK configure + structlog logger | Use SDK for config, keep `structlog.get_logger()` for the module-level logger | Eliminates dual-configure | Still imports structlog directly; sensitive filter still needs wiring |
| C. Full SDK migration | Replace configure + logger with SDK equivalents; pass filter as `additional_processors` | Single config path; eliminates direct structlog import; `_filter_sensitive_data` signature already matches structlog processor protocol | Must verify SDK supports the processor; must verify debug-mode console rendering |

**Analysis of Option C feasibility** (based on SDK source code review):

1. **Does SDK `get_logger()` return a structlog BoundLogger?**
   Yes. `StructlogBackend.get_logger()` calls `structlog.get_logger(name)` and returns it typed as `LoggerProtocol`. The underlying object is a structlog `FilteringBoundLogger` (created via `structlog.make_filtering_bound_logger()`). It supports `.info()`, `.error()`, `.warning()`, `.bind()`, and keyword argument structured logging -- exactly the API middleware.py already uses.

2. **Can the SDK logger support custom processors (sensitive field filtering)?**
   Yes. `configure_logging()` accepts an `additional_processors: list[Processor] | None` parameter. These are inserted into the structlog processor chain after `add_log_level` and `add_otel_trace_ids` but before `PositionalArgumentsFormatter`. The `_filter_sensitive_data` function already has the correct structlog processor signature `(logger, method_name, event_dict) -> event_dict`. However, the type hint on `_logger` must change from `logging.Logger` to `Any` (the structlog processor protocol uses `Any` for the logger parameter).

3. **Can it respect debug-mode console rendering toggle?**
   Yes. The SDK's `LogConfig` has `format="auto"` by default, which resolves to `"console"` when stderr is a TTY (dev) and `"json"` when not (production). This matches the existing `settings.debug` toggle behavior, but uses TTY detection instead of a settings flag. For explicit debug-mode control, pass `format="console"` when `settings.debug` is True.

4. **Boot-order concern**: Currently, `api/lifespan.py` calls `configure_structlog()` (from middleware) at startup (line 62), and separately `autom8_asana.core.logging.configure()` may be called elsewhere. Both call `structlog.configure()`, creating a last-writer-wins race. Migrating middleware to use `core.logging.configure()` eliminates this by making it the single configuration point. The idempotent guard (`_configured` flag) in `core.logging.configure()` ensures exactly-once configuration.

**Decision**: Option C -- Full SDK migration.

**Rationale**: The stakeholder explicitly stated that if the platform primitives cannot support a satellite requirement, that indicates a lower-level issue. The SDK demonstrably supports all three requirements (structured logging, custom processors, debug-mode rendering). The migration eliminates the dual-configure boot-order bug and removes the only direct `structlog` import in production code outside infrastructure modules.

**Consequences**:
- `configure_structlog()` is removed from middleware.py and its export from `__all__`
- `api/lifespan.py` must be updated to call `core.logging.configure()` instead of `configure_structlog()`
- The `_filter_sensitive_data` processor is passed via `additional_processors` to `core.logging.configure()`
- `import logging` and `import structlog` are both removed from middleware.py
- Tests that mock or call `configure_structlog()` must be updated (none found in test suite)

### Files Changed

| File | Change |
|------|--------|
| `src/autom8_asana/api/middleware.py` | Remove `configure_structlog()`, `import logging`, `import structlog`; change module logger to SDK; update filter signature |
| `src/autom8_asana/api/lifespan.py` | Replace `configure_structlog()` with `core.logging.configure()` with additional_processors |
| `src/autom8_asana/core/logging.py` | Update `configure()` to accept and forward `additional_processors` |

### Exact Edits

#### `src/autom8_asana/core/logging.py`

Update the `configure()` function to accept `additional_processors`:

```python
# Change the function signature (line 53-57):
# Before:
def configure(
    level: str = "INFO",
    format: str = "auto",
    intercept_stdlib: bool = True,
) -> None:

# After:
def configure(
    level: str = "INFO",
    format: str = "auto",
    intercept_stdlib: bool = True,
    additional_processors: list[Any] | None = None,
) -> None:
```

Add `from typing import Any` to the imports (or add `Any` to existing typing import if present).

Update the `configure_logging()` call inside `configure()` (around line 87-93):

```python
# Before:
    config = LogConfig(
        backend="structlog",
        level=level,  # type: ignore[arg-type]
        format=format,  # type: ignore[arg-type]
        intercept_stdlib=intercept_stdlib,
    )
    configure_logging(config)

# After:
    config = LogConfig(
        backend="structlog",
        level=level,  # type: ignore[arg-type]
        format=format,  # type: ignore[arg-type]
        intercept_stdlib=intercept_stdlib,
    )
    configure_logging(config, additional_processors=additional_processors)
```

Update `__all__` -- no change needed (configure is already exported).

Update docstring to document the new parameter.

#### `src/autom8_asana/api/middleware.py`

**Remove** the following:
- `import logging` (line 19)
- `import structlog` (line 24)
- The entire `configure_structlog()` function (lines 61-95)
- `"configure_structlog"` from `__all__` (line 211)

**Change** module-level logger (line 99):
```python
# Before:
logger = structlog.get_logger(__name__)

# After:
from autom8_asana.core.logging import get_logger
logger = get_logger(__name__)
```

Note: The `get_logger` import can be placed with the other imports at the top of the file. The import of `structlog` is then fully removed.

**Change** `_filter_sensitive_data` type hint (line 38):
```python
# Before:
def _filter_sensitive_data(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:

# After:
def _filter_sensitive_data(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
```

The `Any` type is already imported from `typing` on line 22.

**Final imports section** of middleware.py after edits:
```python
import time
import uuid
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from autom8_asana.core.logging import get_logger
from .config import get_settings
```

**Final `__all__`**:
```python
__all__ = [
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "SLOW_REQUEST_THRESHOLD_MS",
    "_filter_sensitive_data",
    "SENSITIVE_FIELDS",
]
```

Note: `_filter_sensitive_data` and `SENSITIVE_FIELDS` are added to `__all__` so that `lifespan.py` can import the filter processor. Since the function name starts with `_`, adding it to `__all__` makes the intent explicit. Alternatively, the filter can be imported directly without being in `__all__` -- the principal engineer should choose the cleaner approach.

#### `src/autom8_asana/api/lifespan.py`

**Change** the import and startup call:
```python
# Before (line 18):
from .middleware import configure_structlog

# After:
from autom8_asana.core.logging import configure as configure_logging
from .middleware import _filter_sensitive_data
```

```python
# Before (line 62):
    configure_structlog()

# After:
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        format="console" if settings.debug else "auto",
        additional_processors=[_filter_sensitive_data],
    )
```

Note: The `settings = get_settings()` call on line 63 already exists; the configure call should use that same settings reference. Move `settings = get_settings()` BEFORE the `configure_logging()` call and remove the duplicate.

### Verification

```bash
# Verify no direct structlog imports remain in production code (excluding infra)
grep -rn "import structlog" src/autom8_asana/ --include="*.py" \
  | grep -v "structured_logger.py"  # polling module is Gap 5

# Verify no logging.Logger type hint remains in middleware
grep -n "logging.Logger" src/autom8_asana/api/middleware.py

# Run middleware-related tests
.venv/bin/pytest tests/unit/api/ -x -q --timeout=60

# Verify the sensitive field filter still works by running auth tests
.venv/bin/pytest tests/test_auth/ -x -q --timeout=60

# Full test suite
.venv/bin/pytest tests/ -x -q --timeout=60
```

---

## Gap 5: Polling Module Stdlib Migration

### Rationale

Three files in `src/autom8_asana/automation/polling/` use stdlib `logging` for initialization (`basicConfig`) while the module body already uses SDK loggers. The migration aligns these files with the SDK while preserving the graceful degradation to stdlib in `structured_logger.py` (stakeholder decision).

### Downstream Consumer Analysis

The polling module is consumed by:
- **Internal module imports**: `__init__.py` re-exports all public symbols; `cli.py`, `polling_scheduler.py`, `action_executor.py` all import from sibling modules within the package.
- **Tests**: 8 test files under `tests/unit/automation/polling/` and 3 under `tests/integration/automation/polling/`.
- **`__main__` blocks**: `polling_scheduler.py` has an `if __name__ == "__main__"` block (line 626) and `cli.py` has one (line 329). No `__main__.py` file exists for the package.
- **CI/cron/scripts**: No YAML, TOML, or shell script references to `autom8_asana.automation.polling` were found outside the Python source tree.
- **Cron usage**: The docstrings reference `python -m autom8_asana.automation.polling.polling_scheduler` as a cron entry. This is a development/deployment pattern, not a CI reference.

**Conclusion**: The polling module is used in dev/test contexts only. No external CI or production cron configurations reference it directly. The migration is safe.

### Files Changed

| File | Change |
|------|--------|
| `src/autom8_asana/automation/polling/cli.py` | Replace `logging.basicConfig()` with SDK `configure()` |
| `src/autom8_asana/automation/polling/structured_logger.py` | Replace `logging.basicConfig()` and `logging.getLogger()` with SDK; preserve stdlib fallback |
| `src/autom8_asana/automation/polling/polling_scheduler.py` | Replace `logging.basicConfig()` in `__main__` with SDK `configure()` |

### Exact Edits

#### `src/autom8_asana/automation/polling/cli.py`

**Line 27**: Remove `import logging`:
```python
# Before:
import logging

# After:
# (removed)
```

**Lines 241-244**: Replace `logging.basicConfig()` with SDK configure:
```python
# Before:
    # Configure basic logging for CLI
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

# After:
    # Configure logging via SDK (idempotent guard prevents double-configure)
    from autom8_asana.core.logging import configure
    configure(level="WARNING")
```

The idempotent `_configured` guard in `core.logging.configure()` ensures this is safe even if `StructuredLogger.configure()` (called in `evaluate_command`) also triggers configuration. The SDK's `intercept_stdlib=True` default means any stdlib loggers from third-party libraries are captured automatically.

#### `src/autom8_asana/automation/polling/structured_logger.py`

This file requires careful handling because it must preserve graceful degradation to stdlib when structlog is not installed (stakeholder decision).

**Lines 46-48**: Change stdlib imports to conditional:
```python
# Before:
import logging
import sys
from datetime import UTC, datetime

# After:
import sys
from datetime import UTC, datetime
```

Note: `logging` is still needed in the stdlib fallback path. Keep it as a local import inside `_configure_stdlib` and `_StdlibLoggerAdapter.__init__`.

Actually, since the `_StdlibLoggerAdapter` class (line 444) uses `logging.Logger` as a type hint and `_configure_stdlib` (line 162) calls `logging.basicConfig`, the `import logging` must stay at the module level. The migration for this file is more targeted:

**Lines 155-160**: Replace `logging.basicConfig()` in `_configure_structlog`:
```python
# Before:
        # Configure stdlib logging for structlog integration
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, level, logging.INFO),
        )

# After:
        # Stdlib logging is intercepted by SDK when core.logging.configure()
        # has been called with intercept_stdlib=True (the default).
        # No explicit basicConfig needed here -- the SDK's InterceptHandler
        # routes stdlib loggers through the structured pipeline.
```

Wait -- this is incorrect. The `_configure_structlog` method in `StructuredLogger` calls `structlog.configure()` directly, creating the same dual-configure problem as middleware. The right approach is:

**Migration approach for structured_logger.py**:

1. When structlog IS available: Replace `_configure_structlog()` to delegate to `autom8_asana.core.logging.configure()` via the idempotent guard, rather than calling `structlog.configure()` directly. The SDK's `configure()` sets up structlog with all processors. The `StructuredLogger.configure()` method becomes a thin wrapper that calls the SDK configure and records `_configured = True`.

2. When structlog is NOT available (fallback): Keep `_configure_stdlib()` as-is. This path uses `logging.basicConfig()` intentionally -- it is the graceful degradation path.

**Revised edits for structured_logger.py**:

**Lines 113-118** -- change the configure dispatch:
```python
# Before:
        if _STRUCTLOG_AVAILABLE:
            cls._configure_structlog(json_format, cls._level)
        else:
            cls._configure_stdlib(cls._level)

# After:
        if _STRUCTLOG_AVAILABLE:
            # Delegate to SDK configure (idempotent, respects _configured guard)
            from autom8_asana.core.logging import configure as sdk_configure
            fmt = "json" if json_format else "console"
            sdk_configure(level=cls._level, format=fmt)
        else:
            cls._configure_stdlib(cls._level)
```

**Lines 121-153** -- the `_configure_structlog` classmethod can be removed entirely since it is no longer called.

**Lines 206-213** -- change `get_logger` when structlog is available to use SDK:
```python
# Before:
        if _STRUCTLOG_AVAILABLE:
            return structlog.get_logger().bind(**bound_context)
        else:
            # Return adapted stdlib logger
            return _StdlibLoggerAdapter(
                logging.getLogger("autom8_asana.automation.polling"),
                bound_context,
            )

# After:
        if _STRUCTLOG_AVAILABLE:
            from autom8_asana.core.logging import get_logger as sdk_get_logger
            return sdk_get_logger("autom8_asana.automation.polling").bind(**bound_context)
        else:
            # Return adapted stdlib logger (graceful degradation)
            return _StdlibLoggerAdapter(
                logging.getLogger("autom8_asana.automation.polling"),
                bound_context,
            )
```

Note: `sdk_get_logger()` returns a `LoggerProtocol` which has `.bind()` -- this is compatible. The structlog `FilteringBoundLogger` underlying the SDK logger supports `.bind()` with `**kwargs` and returns a new bound logger, matching the existing behavior.

**`_StdlibLoggerAdapter` class (line 444+)**: No changes. This class remains as the fallback path and correctly uses `logging.Logger` in its type hints since it wraps a stdlib logger.

**`import logging` at module level (line 46)**: Retained. It is used by `_configure_stdlib` and `_StdlibLoggerAdapter`.

#### `src/autom8_asana/automation/polling/polling_scheduler.py`

**Line 39**: Remove `import logging`:
```python
# Before:
import logging

# After:
# (removed)
```

Note: `logging` is NOT used anywhere in the module body -- `get_logger` from `autom8y_log` is already used at line 47 for the module-level `logger`. The only usage is in the `__main__` block.

**Lines 629-632**: Replace `logging.basicConfig()` in `__main__` block:
```python
# Before:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# After:
    from autom8_asana.core.logging import configure
    configure(level="INFO")
```

The SDK's `configure()` with `intercept_stdlib=True` (default) ensures that any stdlib loggers from APScheduler or other libraries are routed through the structured pipeline.

**Line 627**: Add the SDK configure import inside the `__main__` block:
```python
if __name__ == "__main__":
    import argparse

    from autom8_asana.core.logging import configure
    configure(level="INFO")
```

### Verification

```bash
# Run polling module unit tests
.venv/bin/pytest tests/unit/automation/polling/ -x -q --timeout=60

# Run polling module integration tests
.venv/bin/pytest tests/integration/automation/polling/ -x -q --timeout=60

# Verify no stdlib logging.basicConfig remains in production code
# (except structured_logger.py _configure_stdlib which is intentional fallback)
grep -rn "logging.basicConfig" src/autom8_asana/ --include="*.py"
# Expected: only structured_logger.py:_configure_stdlib

# Verify the __main__ blocks still work
python -c "import autom8_asana.automation.polling.cli"
python -c "import autom8_asana.automation.polling.polling_scheduler"
```

---

## Commit Sequence

The single PR contains the following logical commits, ordered for safe incremental application and easy revert of individual changes:

| # | Commit | Files | Rationale |
|---|--------|-------|-----------|
| 1 | `fix(deps): bump autom8y-auth floor to >=1.0.1 and autom8y-log to >=0.4.0` | `pyproject.toml`, `uv.lock` | Gap 1. Foundation -- must land first since later gaps depend on SDK v0.4.0 features. Run full test suite after. |
| 2 | `fix(types): remove unnecessary mypy override for autom8y_telemetry` | `pyproject.toml`, possibly `src/` files if type errors surface | Gap 2. Independent of other gaps but depends on Gap 1 lockfile (telemetry SDK must be installable). |
| 3 | `feat(lint): add G and LOG ruff rules for logging format enforcement` | `pyproject.toml` | Gap 3. Pure config change, no source edits. Can be verified immediately. |
| 4 | `refactor(middleware): migrate logging from direct structlog to SDK` | `src/autom8_asana/api/middleware.py`, `src/autom8_asana/api/lifespan.py`, `src/autom8_asana/core/logging.py` | Gap 4. The core design change. Eliminates dual-configure boot-order issue. |
| 5 | `refactor(polling): migrate stdlib logging init to SDK configure` | `src/autom8_asana/automation/polling/cli.py`, `src/autom8_asana/automation/polling/structured_logger.py`, `src/autom8_asana/automation/polling/polling_scheduler.py` | Gap 5. Final migration of remaining stdlib holdouts. |

### Commit Ordering Rationale

- **Commit 1 before 4/5**: The SDK migration in Gaps 4-5 assumes autom8y-log >= 0.4.0 is installed. The lockfile must be updated first.
- **Commit 2 independent**: The mypy override removal is orthogonal. Placed after lockfile update to ensure telemetry SDK is at correct version.
- **Commit 3 independent**: Ruff rule changes do not affect source code. Placed between mypy and source changes for clean separation.
- **Commits 4 and 5 separate**: Middleware (Gap 4) and polling (Gap 5) are independent subsystems. Separating them allows targeted revert if one causes issues.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SDK version not published to CodeArtifact | Low | Blocks PR | Verify `uv lock` resolves before proceeding (pre-flight check) |
| mypy override removal surfaces many errors | Low | Delays PR | Only one production file uses telemetry; type errors are likely minimal |
| Ruff G/LOG rules flag existing code | Low | Minor rework | The `%s` pattern is ignored via G002/G004; run `ruff check` before committing |
| Middleware filter processor not called in correct order | Medium | Silent security regression | Verify via test: log a message with `authorization` key, assert it is `[REDACTED]` |
| StructuredLogger stdlib fallback broken by refactor | Low | Polling breaks without structlog | The fallback path is NOT modified; only the structlog-available path changes |
| Double-configure race between lifespan and StructuredLogger | Low | Duplicate warnings | Both use idempotent guards; SDK's `_configured` flag and StructuredLogger's `_configured` flag prevent double-init |

---

## Test Impact

### Existing Tests That May Need Updates

1. **`tests/unit/automation/polling/test_structured_logger.py`**: Tests the `StructuredLogger.configure()` method. The internal `_configure_structlog()` is being replaced with SDK delegation. Tests that mock `structlog.configure()` directly may need to mock `autom8_asana.core.logging.configure` instead. Review all test methods before implementing.

2. **`tests/unit/automation/polling/test_cli.py`**: Tests CLI commands. The `logging.basicConfig()` call is being replaced. Tests that check log output format may need adjustment. The `main()` function's logging setup changes from `logging.WARNING` level to SDK-managed level.

3. **`tests/unit/automation/polling/test_polling_scheduler.py`**: Tests scheduler behavior. The `__main__` block changes are not tested (it is a script entry point). No test impact expected for the class methods.

4. **No middleware-specific test files exist** that test `configure_structlog()` or `_filter_sensitive_data`. The filter processor should have test coverage added, but that is out of scope for this hardening PR (recommend adding as follow-up).

### New Test Coverage Recommended (Out of Scope)

- Unit test for `_filter_sensitive_data` processor confirming SENSITIVE_FIELDS are redacted
- Integration test confirming SDK `additional_processors` are invoked during request logging
- Test confirming idempotent configure behavior when called from multiple entry points
