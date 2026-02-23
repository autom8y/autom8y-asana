# TDD: Explicit Application Bootstrap

## Overview

Replace the import-time `register_all_models()` call at `models/business/__init__.py:66` with an explicit `bootstrap()` function called at each application entry point, and add an `_ensure_bootstrapped()` deferred resolution guard to `ProjectTypeRegistry`. This eliminates fragile import ordering, improves test isolation, reduces Lambda cold start penalty, and follows the Django `django.setup()` pattern.

## Context

- **PRD**: `docs/prd/PRD-bootstrap.md`
- **ADR**: `docs/decisions/ADR-0149-explicit-application-bootstrap.md`
- **Technology Scout**: `docs/rnd/SCOUT-import-side-effect-elimination.md`
- **Integration Fit**: `.claude/wip/q1_arch/INTEGRATION-FIT-ANALYSIS.md` (Gap 5A)

**Constraints**:
- `__init_subclass__` and `__set_name__` descriptor hooks fire at class definition time and MUST NOT be modified
- `register_all_models()` function MUST continue to exist (only the call site at import time is removed)
- `_BOOTSTRAP_COMPLETE` flag, `reset_bootstrap()`, and `is_bootstrap_complete()` MUST remain
- The `_ensure_bootstrapped()` guard MUST be idempotent and thread-safe
- Guard overhead MUST be <1 microsecond after first initialization (single boolean check)
- Backward compatibility: `from autom8_asana.models.business import Business` followed by detection MUST still work via the guard

---

## System Design

### Architecture Diagram

```
BEFORE (import-time side effect):

  models/business/__init__.py
         |
         | line 66: register_all_models()   <-- fires on ANY import
         |
  ProjectTypeRegistry populated
         |
  detection code assumes populated

AFTER (explicit bootstrap + deferred guard):

  Entry Point (API/Lambda/CLI/Test)
         |
         | bootstrap()                      <-- explicit, once per process
         |
  register_all_models()
         |
  ProjectTypeRegistry populated
         |
  _ensure_bootstrapped() on lookup()        <-- safety net if bootstrap() missed
```

### Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `bootstrap()` | Public API for application initialization | `src/autom8_asana/models/business/_bootstrap.py` |
| `_ensure_bootstrapped()` | Deferred guard on ProjectTypeRegistry public methods | `src/autom8_asana/models/business/registry.py` |
| Entry point wiring | Explicit `bootstrap()` call at each entry point | 8 files (see Section 4) |
| `SystemContext.reset_all()` | Already resets bootstrap flag; no change needed | `src/autom8_asana/core/system_context.py` |
| Test fixture | Session-scoped autouse fixture calling `bootstrap()` | `tests/conftest.py` |

---

## 1. `bootstrap()` Function Design

### Location Decision: Co-located in `_bootstrap.py`

**Decision**: Place `bootstrap()` in `src/autom8_asana/models/business/_bootstrap.py` alongside the existing `register_all_models()`, `is_bootstrap_complete()`, and `reset_bootstrap()`.

**Rationale**:
- All bootstrap machinery is already in `_bootstrap.py` -- the idempotency flag, the registration logic, the reset function. Adding `bootstrap()` here keeps the single-responsibility boundary.
- A `core/bootstrap.py` would need to import from `_bootstrap.py` anyway (it is just a forwarding layer), adding one more import path without adding organization value.
- The import path `from autom8_asana.models.business._bootstrap import bootstrap` is already the canonical internal path. The public convenience path is handled via re-export (see FR-S3 below).

### Signature

```python
def bootstrap() -> None:
    """Initialize the autom8_asana application.

    Populates ProjectTypeRegistry with all known entity type -> project GID
    mappings. This is the single public API for application initialization,
    analogous to Django's django.setup().

    MUST be called once at application startup before any entity detection.
    Idempotent: subsequent calls are no-ops.

    The _ensure_bootstrapped() guard on ProjectTypeRegistry provides a safety
    net for code paths that reach detection without explicit bootstrap, but
    explicit bootstrap at the entry point is the expected pattern.

    Example:
        from autom8_asana.models.business._bootstrap import bootstrap
        bootstrap()  # Call once at startup

    See Also:
        reset_bootstrap: Reset for test isolation.
        is_bootstrap_complete: Check bootstrap state.
    """
    if is_bootstrap_complete():
        logger.debug("bootstrap_noop", extra={"reason": "already_complete"})
        return

    logger.info("bootstrap_starting")
    register_all_models()
    logger.info(
        "bootstrap_complete",
        extra={"source": "explicit_bootstrap"},
    )
```

### Key Properties

1. **Idempotent**: Delegates to `register_all_models()` which checks `_BOOTSTRAP_COMPLETE`.
2. **Thin wrapper**: Adds structured logging around the existing registration. Does NOT duplicate registration logic.
3. **No thread lock on hot path**: `is_bootstrap_complete()` is a simple boolean read. Only the first call does work.
4. **No new state**: Uses the existing `_BOOTSTRAP_COMPLETE` flag. No new module-level variables.

### Public Import Path (FR-S3)

Add `bootstrap` to `src/autom8_asana/models/business/__init__.py` exports:

```python
from autom8_asana.models.business._bootstrap import bootstrap
```

And add `"bootstrap"` to the `__all__` list. This enables:

```python
from autom8_asana.models.business import bootstrap
bootstrap()
```

---

## 2. `_ensure_bootstrapped()` Guard Design

### Pattern Reference

Follow the existing `SchemaRegistry._ensure_initialized()` pattern at `src/autom8_asana/dataframes/models/registry.py:104-140`.

Key differences from SchemaRegistry:
- **No threading lock on hot path**: `ProjectTypeRegistry` registration is a simple dict population (~2ms), not a complex initialization with dotted path resolution. The boolean check alone is sufficient for the hot path. A lock is only needed if two threads race on the very first call.
- **WARNING log**: When `_ensure_bootstrapped()` triggers (meaning no explicit `bootstrap()` was called), it logs a WARNING. This makes forgotten `bootstrap()` calls visible without crashing.

### Implementation

Add to `src/autom8_asana/models/business/registry.py`:

```python
import threading

# Module-level lock for thread-safe bootstrap guard (only contended on first call)
_bootstrap_lock = threading.Lock()
```

Add method to `ProjectTypeRegistry` class:

```python
def _ensure_bootstrapped(self) -> None:
    """Lazy bootstrap guard: populates registry on first access if needed.

    Follows the SchemaRegistry._ensure_initialized() pattern.
    Hot path: single boolean check (<1us). Cold path: acquires lock,
    calls register_all_models(), logs WARNING about missing explicit bootstrap.

    Thread-safe via double-checked locking pattern.
    """
    from autom8_asana.models.business._bootstrap import is_bootstrap_complete

    if is_bootstrap_complete():
        return

    with _bootstrap_lock:
        # Double-checked locking: another thread may have completed bootstrap
        if is_bootstrap_complete():
            return

        logger.warning(
            "ensure_bootstrapped_triggered",
            extra={
                "detail": (
                    "ProjectTypeRegistry accessed before explicit bootstrap(). "
                    "Add bootstrap() call to your entry point. "
                    "Falling back to lazy initialization."
                ),
            },
        )

        from autom8_asana.models.business._bootstrap import register_all_models
        register_all_models()
```

### Methods Guarded

Add `self._ensure_bootstrapped()` as the first line of these `ProjectTypeRegistry` methods:

| Method | Line (approx) | Rationale |
|--------|---------------|-----------|
| `lookup()` | 142 | Primary detection path |
| `get_primary_gid()` | 161 | Used by healing, cache warming |
| `is_registered()` | 174 | Used by workspace registry registration |
| `get_all_mappings()` | 185 | Used by debugging, validation |

**Methods NOT guarded**:
- `register()`: Registration is called BY bootstrap, not before it. Guarding it would create infinite recursion.
- `reset()`: Class method for test isolation. Intentionally clears state.

### WorkspaceProjectRegistry

`WorkspaceProjectRegistry.lookup()` (line 602) delegates to `self._type_registry.lookup()`, which will trigger `_ensure_bootstrapped()`. No direct guard needed on `WorkspaceProjectRegistry`.

`WorkspaceProjectRegistry.lookup_or_discover_async()` (line 572) similarly delegates. No change needed.

### Performance Characteristics

```
Hot path (bootstrap complete):
  is_bootstrap_complete() -> reads _BOOTSTRAP_COMPLETE (bool)
  -> return immediately
  Cost: ~50 nanoseconds (single global variable read)

Cold path (first access, no explicit bootstrap):
  is_bootstrap_complete() -> False
  acquire _bootstrap_lock
  is_bootstrap_complete() -> False (double-check)
  register_all_models() -> ~2-5ms (16 entity type dict inserts)
  release _bootstrap_lock
  Cost: ~5ms (one-time, amortized to zero)
```

---

## 3. Tier-1 Defensive Guard Strategy

### Decision: Replace with `_ensure_bootstrapped()` (Option B from PRD FR-M6)

The existing defensive guard at `src/autom8_asana/models/business/detection/tier1.py:91-105` currently:

```python
from autom8_asana.models.business._bootstrap import (
    is_bootstrap_complete,
    register_all_models,
)
from autom8_asana.models.business.registry import get_registry

if not is_bootstrap_complete():
    logger.info("tier1_bootstrap_triggered", ...)
    register_all_models()
```

After the guard is added to `ProjectTypeRegistry.lookup()`, this code is redundant: the `registry.lookup(project_gid)` call on line 132 will trigger `_ensure_bootstrapped()` if bootstrap has not completed.

**Action**: Remove the defensive guard block (lines 91-105) from `tier1.py`. The subsequent `registry.lookup()` call provides the same safety net.

**Rationale**:
- Eliminates duplicated bootstrap logic (DRY)
- The guard is now a registry-level concern, not a detection-level concern
- The `_ensure_bootstrapped()` WARNING log replaces the tier1 INFO log with a more informative message
- The diagnostic block at lines 116-130 (registry anomaly detection) remains useful and is kept

---

## 4. Entry Point Wiring

### 4.1 API Lifespan (`src/autom8_asana/api/lifespan.py`)

Insert `bootstrap()` call early in the startup sequence, before `_discover_entity_projects()`.

**Insertion point**: After logging configuration, before entity resolver discovery (line ~128).

```python
# Bootstrap business model registry
from autom8_asana.models.business._bootstrap import bootstrap
bootstrap()
```

**Note**: The lifespan currently does not call `register_all_models()` or import `models.business` directly. It relies on `_discover_entity_projects()` which internally may trigger detection. The explicit bootstrap here ensures the registry is populated before any discovery or detection calls.

### 4.2 Cache Warmer Lambda (`src/autom8_asana/lambda_handlers/cache_warmer.py`)

**Current state**: Has its own `_ensure_bootstrap()` function (lines 55-91) that does `import autom8_asana.models.business` (side-effect import), plus cross-registry validation.

**Change**: Replace the body of `_ensure_bootstrap()` to call the canonical `bootstrap()`:

```python
def _ensure_bootstrap() -> None:
    """Lazy bootstrap initialization for Lambda cold starts."""
    global _bootstrap_initialized
    if not _bootstrap_initialized:
        try:
            from autom8_asana.models.business._bootstrap import bootstrap
            bootstrap()
            _bootstrap_initialized = True

            # Cross-registry validation (QW-4)
            from autom8_asana.core.registry_validation import (
                validate_cross_registry_consistency,
            )
            validation = validate_cross_registry_consistency(
                check_project_type_registry=True,
                check_entity_project_registry=False,
            )
            if not validation.ok:
                logger.error(
                    "cross_registry_validation_failed",
                    extra={"errors": validation.errors},
                )
        except ImportError as e:
            logger.warning(
                "bootstrap_failed",
                error=str(e),
                impact="Detection may fall through to Tier 5 (unknown)",
            )
```

**Key preservation**: The `_bootstrap_initialized` local flag and the try/except ImportError are cache_warmer-specific resilience. The cross-registry validation is cache_warmer-specific business logic. Both are preserved.

### 4.3 Cache Invalidate Lambda (`src/autom8_asana/lambda_handlers/cache_invalidate.py`)

**Current state**: No bootstrap call. This handler does not use business model detection -- it clears caches.

**Change**: No change needed. The cache_invalidate handler does not import business models or use entity detection. Adding `bootstrap()` would add unnecessary cold start cost. If detection is ever needed in the future, `_ensure_bootstrapped()` provides the safety net.

**Rationale update**: The PRD cataloged 8 entry points including cache_invalidate. After inspecting the code, cache_invalidate has no dependency on `ProjectTypeRegistry`. Adding bootstrap here would be cargo-cult. Omit it.

### 4.4 Workflow Handler (`src/autom8_asana/lambda_handlers/workflow_handler.py`)

**Current state**: No bootstrap call. The generic workflow handler defers to per-workflow Lambda modules.

**Change**: No change to the generic handler. The workflow-specific handlers (conversation_audit, insights_export) handle their own bootstrap.

### 4.5 Conversation Audit Lambda (`src/autom8_asana/lambda_handlers/conversation_audit.py`)

**Current state**: Line 17: `import autom8_asana.models.business  # noqa: F401 - bootstrap side effect`

**Change**: Replace the side-effect import with explicit bootstrap:

```python
from autom8_asana.models.business._bootstrap import bootstrap
bootstrap()
```

This runs at module scope (same timing as the current import), which is fine because `create_workflow_handler()` is also called at module scope (line 49). The bootstrap must complete before `handler` is returned.

### 4.6 Insights Export Lambda (`src/autom8_asana/lambda_handlers/insights_export.py`)

**Current state**: No explicit bootstrap. Imports from `autom8_asana.automation.workflows.insights_export` which does not transitively import `models.business`.

**Change**: Add explicit bootstrap at module scope before handler creation:

```python
from autom8_asana.models.business._bootstrap import bootstrap
bootstrap()
```

**Rationale**: The insights export workflow enumerates businesses, which requires entity detection. Currently works because some other import path triggers the `models.business.__init__.py` side effect, but this is fragile. The explicit call makes the dependency visible.

### 4.7 CLI Entrypoint (`src/autom8_asana/entrypoint.py`)

**Current state**: No bootstrap call. In ECS mode, delegates to uvicorn which loads the FastAPI app (which has lifespan). In Lambda mode, delegates to awslambdaric.

**Change**: Add bootstrap in `run_ecs_mode()` before uvicorn starts:

```python
def run_ecs_mode() -> None:
    """Start uvicorn API server for ECS deployment."""
    from autom8_asana.models.business._bootstrap import bootstrap
    bootstrap()

    import uvicorn
    # ... rest unchanged
```

**Note**: The lifespan also calls `bootstrap()`. This is intentionally redundant -- `bootstrap()` is idempotent. The entrypoint call ensures bootstrap runs even if something accesses the registry before uvicorn fully starts (e.g., module-level code).

For Lambda mode, no change: each Lambda handler module handles its own bootstrap.

### 4.8 Test Conftest (`tests/conftest.py`)

**Current state**: `reset_all_singletons` autouse fixture calls `SystemContext.reset_all()` which calls `reset_bootstrap()`. No explicit `bootstrap()` call exists.

**Change**: Add a session-scoped autouse fixture that calls `bootstrap()` once per test session. This runs after collection but before any test function executes. The existing per-test `reset_all_singletons` fixture resets all singletons before each test, but the `_ensure_bootstrapped()` guard will re-populate on first registry access.

```python
@pytest.fixture(autouse=True, scope="session")
def _bootstrap_session():
    """Bootstrap the application once per test session.

    Populates ProjectTypeRegistry before any tests run. Individual tests
    that call SystemContext.reset_all() will get re-populated via
    _ensure_bootstrapped() on first registry access.
    """
    from autom8_asana.models.business._bootstrap import bootstrap
    bootstrap()
```

**Interaction with reset_all_singletons**: The session fixture runs ONCE before any tests. The per-test `reset_all_singletons` fixture (function-scoped) resets all singletons including `_BOOTSTRAP_COMPLETE` before/after each test. The `_ensure_bootstrapped()` guard then lazily re-populates the registry on the first lookup within each test. This means:

1. Session start: `bootstrap()` populates registry
2. Before each test: `SystemContext.reset_all()` resets everything (including `_BOOTSTRAP_COMPLETE = False`)
3. First registry access in test: `_ensure_bootstrapped()` re-populates (WARNING suppressed -- see below)
4. After each test: `SystemContext.reset_all()` resets everything

**WARNING suppression in tests**: The `_ensure_bootstrapped()` guard logs a WARNING when it triggers. In tests, this will fire on every test that touches detection (after reset_all_singletons clears the bootstrap flag). To avoid noisy WARNING logs in test output, we have two options:

- **Option A**: Suppress the WARNING in test mode (check for `_PYTEST_RUNNING` flag) -- adds coupling to test runner
- **Option B**: Accept the WARNINGs in tests -- they are informational, not errors

**Decision**: Option B. The WARNINGs in test output are acceptable because:
- They are DEBUG/INFO level noise in structured logging (not visible in default pytest output)
- They confirm the guard is working correctly
- Adding test-mode detection would be unnecessary coupling

---

## 5. `__init__.py` Modification

### Remove Import-Time Side Effect

**File**: `src/autom8_asana/models/business/__init__.py`

**Remove** line 66: `register_all_models()`

**Keep** line 64: `from autom8_asana.models.business._bootstrap import register_all_models`

**Add**: `from autom8_asana.models.business._bootstrap import bootstrap`

**Update** the module docstring comment block (lines 55-63) to reflect the new pattern:

```python
# ARCHITECTURE: Bootstrap registration is now EXPLICIT, not import-time.
# Call bootstrap() at your application entry point (API lifespan, Lambda
# handler, CLI, test conftest). If you forget, _ensure_bootstrapped() on
# ProjectTypeRegistry will lazily populate the registry on first access
# and log a WARNING.
#
# Per TDD-registry-consolidation (superseded by TDD-bootstrap):
# register_all_models() is called by bootstrap(), not at import time.
from autom8_asana.models.business._bootstrap import bootstrap, register_all_models
```

**Update `__all__`**: Add `"bootstrap"` and `"register_all_models"` to the exports list.

---

## 6. Migration Strategy

### Safe Ordering: Additive Before Subtractive

The migration MUST be incremental. The key insight: `_ensure_bootstrapped()` and explicit `bootstrap()` calls can be added BEFORE removing the import-time call. This creates a period where both mechanisms are active (harmless due to idempotency).

### Phase 1: Add Guards (Non-Breaking)

1. Add `_ensure_bootstrapped()` to `ProjectTypeRegistry.lookup()`, `get_primary_gid()`, `is_registered()`, `get_all_mappings()`
2. Add `bootstrap()` function to `_bootstrap.py`
3. Add `bootstrap` export to `models/business/__init__.py`

**At this point**: Nothing changes in behavior. The import-time call at line 66 still fires. The guard on lookup methods is a no-op (bootstrap is already complete by the time any lookup runs).

### Phase 2: Add Entry Point Calls (Non-Breaking)

4. Add `bootstrap()` to API lifespan
5. Update `cache_warmer._ensure_bootstrap()` to call canonical `bootstrap()`
6. Update `conversation_audit.py` to use `bootstrap()` instead of side-effect import
7. Add `bootstrap()` to `insights_export.py`
8. Add `bootstrap()` to `entrypoint.py` (ECS mode)
9. Add session-scoped bootstrap fixture to `tests/conftest.py`

**At this point**: `bootstrap()` is called at every entry point AND at import time. All calls are idempotent no-ops after the first. Completely non-breaking.

### Phase 3: Remove Import-Time Call (The Switch)

10. Remove `register_all_models()` from `models/business/__init__.py:66`
11. Remove tier-1 defensive guard from `detection/tier1.py:91-105`
12. Update module docstring in `__init__.py`

**At this point**: Bootstrap is explicit. `_ensure_bootstrapped()` is the safety net. The tier-1 guard is redundant (lookup triggers the guard).

### Phase 4: Test Verification

13. Run full test suite (10,552+ tests)
14. Fix any tests that break (expect 0-5 based on analysis -- see Section 7)
15. Verify Lambda handlers work via integration tests

### Rollback Plan

If Phase 3 causes problems, rollback is a single line: re-add `register_all_models()` to `models/business/__init__.py:66`. All other changes (entry point calls, `_ensure_bootstrapped()` guard) are additive and harmless.

---

## 7. Test Infrastructure Design

### Session-Scoped Fixture

```python
# tests/conftest.py

@pytest.fixture(autouse=True, scope="session")
def _bootstrap_session():
    """Bootstrap the application once per test session."""
    from autom8_asana.models.business._bootstrap import bootstrap
    bootstrap()
```

### Interaction with Existing Fixtures

The existing `reset_all_singletons` fixture (function-scoped, autouse) calls `SystemContext.reset_all()` which includes:
- `ProjectTypeRegistry.reset()` -- clears singleton instance
- `reset_bootstrap()` -- sets `_BOOTSTRAP_COMPLETE = False`

After reset, the first `ProjectTypeRegistry.lookup()` call in any test triggers `_ensure_bootstrapped()`, which calls `register_all_models()`. This is transparent to the test.

### Test Files That Call `reset()` Directly

Found 4 test files with explicit `ProjectTypeRegistry.reset()` or `reset_bootstrap()` calls:

| File | Current Pattern | Change Needed |
|------|----------------|---------------|
| `tests/unit/models/business/test_registry.py` | Tests registry behavior after reset | None -- `_ensure_bootstrapped()` handles re-population on next lookup |
| `tests/unit/models/business/test_workspace_registry.py` | Resets workspace registry | None -- workspace delegates to type registry |
| `tests/integration/test_workspace_registry.py` | Integration test with resets | None -- guard handles lazy repopulation |
| `tests/unit/models/business/test_registry_consolidation.py` | Tests bootstrap/reset cycle | May need update: tests that assert empty registry after reset will now find populated registry on first lookup |

### Expected Test Changes

**`test_registry_consolidation.py`**: Tests that verify the registry is empty after `reset_bootstrap()` + `ProjectTypeRegistry.reset()` and then manually call `register_all_models()` will still work, but any test that asserts "registry is empty" and then does a `lookup()` will find the registry populated (because `_ensure_bootstrapped()` fires). These tests may need:
- Assert emptiness BEFORE any lookup call, OR
- Directly access `registry._gid_to_type` (bypassing the guard) to verify internal state

**Estimated scope**: 0-5 test method updates. Most tests that call `reset()` do so to start fresh and then re-register manually. The guard is transparent to this pattern.

### New Test: Verify `_ensure_bootstrapped()` Fallback

Add a test (per SC-8) that verifies the guard works:

```python
# tests/unit/models/business/test_bootstrap.py

def test_detection_works_without_explicit_bootstrap():
    """SC-8: Detection succeeds via _ensure_bootstrapped() fallback."""
    from autom8_asana.models.business._bootstrap import reset_bootstrap
    from autom8_asana.models.business.registry import ProjectTypeRegistry

    # Reset everything
    ProjectTypeRegistry.reset()
    reset_bootstrap()

    # Do NOT call bootstrap() -- rely on guard
    registry = ProjectTypeRegistry()
    # This should trigger _ensure_bootstrapped()
    result = registry.lookup("some_known_project_gid")
    # Registry should now be populated
    assert registry.get_all_mappings()  # Non-empty
```

---

## 8. File-Level Change Map

| # | File | Change Type | Description |
|---|------|-------------|-------------|
| 1 | `src/autom8_asana/models/business/_bootstrap.py` | **Add function** | Add `bootstrap()` function (~15 lines) wrapping `register_all_models()` with structured logging |
| 2 | `src/autom8_asana/models/business/registry.py` | **Add method + module variable** | Add `_bootstrap_lock` (threading.Lock), add `_ensure_bootstrapped()` method to `ProjectTypeRegistry`, add `import threading` |
| 3 | `src/autom8_asana/models/business/registry.py` | **Modify methods** | Add `self._ensure_bootstrapped()` as first line of `lookup()`, `get_primary_gid()`, `is_registered()`, `get_all_mappings()` |
| 4 | `src/autom8_asana/models/business/__init__.py` | **Remove line** | Remove `register_all_models()` call at line 66 |
| 5 | `src/autom8_asana/models/business/__init__.py` | **Modify import + exports** | Add `bootstrap` to import and `__all__` list, update docstring comment |
| 6 | `src/autom8_asana/models/business/detection/tier1.py` | **Remove lines** | Remove defensive guard block at lines 91-105 (imports + bootstrap check) |
| 7 | `src/autom8_asana/api/lifespan.py` | **Add lines** | Add `bootstrap()` import and call before `_discover_entity_projects()` |
| 8 | `src/autom8_asana/lambda_handlers/cache_warmer.py` | **Modify function** | Replace `_ensure_bootstrap()` body to use canonical `bootstrap()` instead of side-effect import |
| 9 | `src/autom8_asana/lambda_handlers/conversation_audit.py` | **Modify import** | Replace `import autom8_asana.models.business` side-effect with `bootstrap()` call |
| 10 | `src/autom8_asana/lambda_handlers/insights_export.py` | **Add lines** | Add `bootstrap()` import and call at module scope |
| 11 | `src/autom8_asana/entrypoint.py` | **Add lines** | Add `bootstrap()` import and call in `run_ecs_mode()` |
| 12 | `tests/conftest.py` | **Add fixture** | Add session-scoped `_bootstrap_session` autouse fixture |
| 13 | `tests/unit/models/business/test_bootstrap.py` | **New file** | Test for `_ensure_bootstrapped()` fallback behavior (SC-8) |
| 14 | `tests/unit/models/business/test_registry_consolidation.py` | **Possible modifications** | Update tests that assert empty registry after reset if they do lookups |

### Files NOT Changed

| File | Reason |
|------|--------|
| `src/autom8_asana/lambda_handlers/cache_invalidate.py` | Does not use entity detection or ProjectTypeRegistry |
| `src/autom8_asana/lambda_handlers/workflow_handler.py` | Generic factory; per-workflow modules handle bootstrap |
| `src/autom8_asana/core/system_context.py` | Already resets bootstrap flag; no change needed |
| `src/autom8_asana/dataframes/models/registry.py` | SchemaRegistry pattern is reference only; no changes |
| `src/autom8_asana/metrics/registry.py` | MetricRegistry pattern is reference only; no changes |

---

## 9. Non-Functional Considerations

### Performance

- **Hot path overhead**: Single `is_bootstrap_complete()` call (boolean read) per registry access. Measured at ~50ns. Well within the <1us requirement.
- **Cold path overhead**: `register_all_models()` runs once per process. Measured at ~2-5ms (16 entity types, dict inserts). Dominated by network I/O in all real paths (50-500ms per Asana API call).
- **Lambda cold start**: Explicit `bootstrap()` at handler entry moves registration from import-time to explicit-call-time. Net effect: zero change for handlers that need detection (same work, different timing). Positive effect for `cache_invalidate` which no longer pays registration cost.

### Security

No security implications. This change is internal initialization pattern only. No auth, crypto, PII, or external integration changes.

### Reliability

- **Failure mode**: If `register_all_models()` fails (e.g., missing entity module), the failure now happens at explicit `bootstrap()` call rather than at import time. This makes the error more visible (appears in handler logs with structured context) and debuggable (clear stack trace from entry point).
- **Recovery**: Same as today -- the process logs an error and either crashes (Lambda) or starts with degraded detection (API).
- **Monitoring**: The `bootstrap_complete` and `ensure_bootstrapped_triggered` log events provide observability into bootstrap behavior. The WARNING from `_ensure_bootstrapped()` can be monitored to detect missing `bootstrap()` calls.

---

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests that assert empty registry after reset + lookup | Medium | Low | Tests can inspect `_gid_to_type` directly or assert before lookup. At most 0-5 tests affected. |
| Lambda handler missing `bootstrap()` call | Low | Low | `_ensure_bootstrapped()` fallback ensures correctness. WARNING log makes omission visible. |
| Developer confusion about when to call `bootstrap()` | Low | Low | Pattern is identical to Django's `django.setup()`. Updated module docstring explains. |
| Concurrent access during first `_ensure_bootstrapped()` | Very Low | None | Double-checked locking with `_bootstrap_lock` prevents duplicate registration. |
| Rollback needed mid-migration | Low | None | Re-add `register_all_models()` to `__init__.py:66`. All other changes are additive. |

---

## 11. ADRs

- **ADR-0149**: Explicit Application Bootstrap -- documents the decision, alternatives considered, and consequences. See `docs/decisions/ADR-0149-explicit-application-bootstrap.md`.

---

## 12. Open Items

None. All design decisions resolved in this document. The implementation is straightforward -- a thin wrapper function, a guard method following an existing pattern, and 8 entry point wiring changes.
