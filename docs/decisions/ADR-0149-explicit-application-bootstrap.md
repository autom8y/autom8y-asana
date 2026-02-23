# ADR-0149: Explicit Application Bootstrap

## Status

Proposed

## Context

The autom8_asana codebase registers 16 entity types into `ProjectTypeRegistry` as a side effect of importing `autom8_asana.models.business`. The call at `models/business/__init__.py:66` (`register_all_models()`) fires whenever any code does `from autom8_asana.models.business import X`. This import-time side effect causes four categories of harm:

1. **Fragile import ordering**: Any import of business models triggers registration, which must complete before any detection call succeeds. This creates invisible coupling documented in the debt ledger (D-029, RF-009). The comment at `models/business/__init__.py:55-58` explicitly acknowledges this as deferred work.

2. **Test pollution via mutable singletons**: `ProjectTypeRegistry._instance` persists across tests. Currently mitigated by `SystemContext.reset_all()` in the root conftest (which resets `_BOOTSTRAP_COMPLETE`), but the implicit bootstrap means the first test that imports business models re-triggers registration as a side effect.

3. **Lambda cold start penalty**: Lambda handlers pay full registration cost even when they only need a subset of functionality. The cache_invalidate handler, for example, never uses entity detection but would pay registration cost if it imported any business model.

4. **Circular dependency management burden**: 6+ `__getattr__` lazy-load sites, 20+ deferred function-body imports, and 4 active circular dependency chains are symptoms of import-time coupling.

The codebase already has the building blocks for explicit initialization:
- `register_all_models()` is idempotent via the `_BOOTSTRAP_COMPLETE` flag
- `reset_bootstrap()` and `is_bootstrap_complete()` exist for test isolation
- `SchemaRegistry._ensure_initialized()` and `MetricRegistry._ensure_initialized()` already implement the deferred resolution pattern -- `ProjectTypeRegistry` is the only registry without this guard
- The defensive call in `detection/tier1.py:93-105` already implements a bootstrap guard, confirming the need is recognized in the codebase
- The cache_warmer Lambda already has its own `_ensure_bootstrap()` function wrapping the side-effect import

This pattern has been identified in multiple architecture reviews (ARCH-REVIEW-1 Section 3.1, debt ledger items D-029 and RF-009) and formally assessed in `SCOUT-import-side-effect-elimination.md` which evaluated six approaches against the codebase constraints.

## Decision

Replace import-time registration with explicit bootstrap, combining two approaches from the technology scout:

1. **Explicit Application Bootstrap** (SCOUT Approach 1 -- ADOPT): Create a `bootstrap()` function called at each application entry point.
2. **Registry Pattern with Deferred Resolution** (SCOUT Approach 6 -- ADOPT): Add `_ensure_bootstrapped()` guard to `ProjectTypeRegistry` public methods as a safety net.

This mirrors the Django `django.setup()` pattern -- the most production-proven solution to this class of problem in the Python ecosystem.

### Specific Design Choices

**bootstrap() location**: Co-located in `models/business/_bootstrap.py` alongside existing `register_all_models()`, `reset_bootstrap()`, and `is_bootstrap_complete()`. A `core/bootstrap.py` was considered but rejected because it would only forward to `_bootstrap.py`, adding an indirection without organizational benefit.

**Tier-1 defensive guard**: Replaced by `_ensure_bootstrapped()` on `ProjectTypeRegistry.lookup()`. The existing guard at `detection/tier1.py:91-105` is removed because `registry.lookup()` now provides the same safety net at a lower layer. This eliminates duplicated bootstrap logic (DRY).

**cache_invalidate Lambda**: Omitted from entry point wiring. This handler does not use entity detection or `ProjectTypeRegistry`. Adding `bootstrap()` would be unnecessary cold start cost.

## Alternatives Considered

### Option 1: Plugin/Entry Point Discovery (importlib.metadata)

Use `importlib.metadata.entry_points(group='autom8_asana.entity_types')` to discover entity types from package metadata.

- **Pros**: Standard Python packaging mechanism, works across package boundaries
- **Cons**: All 16 entity types are in the same package (no discovery benefit), adds build tooling complexity, development friction (entity change requires package reinstall), 20-50ms overhead from metadata scanning, test isolation becomes harder
- **Verdict**: HOLD. Solves a different problem (cross-package plugin discovery).

### Option 2: Dependency Injection Container

Replace singleton registries with a DI container (dependency-injector, lagom, or injector).

- **Pros**: Strongest test isolation (per-test container overrides), eliminates all singleton reset patterns
- **Cons**: Pydantic v2 compatibility issues (dependency-injector `from_pydantic()` broken), 8-12 week effort, hundreds of `get_registry()` call sites to migrate, library maintenance risk, neutral-to-negative Lambda cold start impact
- **Verdict**: HOLD. The codebase has 4 singleton registries, not 40 injectable services. The benefit/cost ratio is unfavorable. Revisit if codebase grows to 20+ injectable services.

### Option 3: PEP 562 Lazy Module Loading

Formalize the existing ad-hoc `__getattr__` lazy imports into a consistent pattern across all `__init__.py` files.

- **Pros**: Improves cold start for handlers that access a subset of the package
- **Cons**: Does not solve test isolation (singleton lifecycle unchanged), degrades IDE autocompletion, static analysis loses type information, treats symptom (import time) not disease (import-time side effects), any access to business models triggers full cascade anyway
- **Verdict**: HOLD. Keep existing lazy import sites; do not proliferate the pattern.

### Option 4: Import Graph Restructuring

Break circular dependencies by introducing protocol-only interface packages.

- **Pros**: Correct long-term direction for code health, eliminates deferred imports
- **Cons**: 4-6 week effort with high cascading change risk, does not address test isolation, some cycles may be fundamental, can be done independently at any time
- **Verdict**: ASSESS. Tackle after bootstrap is explicit, when each deferred import can be evaluated: does the bootstrap eliminate the need for it, or does a protocol module still help?

### Option 5: Status Quo

Keep import-time registration.

- **Pros**: Zero effort, known behavior
- **Cons**: Growing liability as entity types are added, developer learning curve, Lambda cold start penalty, test isolation burden scales linearly with test count
- **Verdict**: REJECT. The debt is growing and the fix is low-risk.

## Rationale

The explicit bootstrap + deferred resolution combination was selected because:

1. **Production-proven**: The Django `django.setup()` pattern has been used by hundreds of thousands of applications since Django 1.7 (2014). It is the most battle-tested solution to exactly this class of problem.

2. **Minimal blast radius**: The codebase already has all building blocks (`register_all_models()` with idempotency, `reset_bootstrap()`, `_BOOTSTRAP_COMPLETE` flag, `SchemaRegistry._ensure_initialized()` pattern). The implementation is additive in Phases 1-2 and subtractive only in Phase 3 (removing one line).

3. **Two-layer defense**: Explicit `bootstrap()` at entry points handles the "when" (application startup). `_ensure_bootstrapped()` handles the "what if someone forgets" (graceful degradation with WARNING log). No code path can reach detection with an empty registry.

4. **Incremental migration**: Entry point calls and guards can be added BEFORE removing the import-time call. The migration is a series of non-breaking additive changes followed by a single subtractive change (removing line 66).

5. **Instant rollback**: If the subtractive change causes problems, rollback is one line: re-add `register_all_models()` to `__init__.py:66`.

6. **Low effort, high confidence**: 8-11 developer-days per integration fit analysis. Uncertainty is concentrated in test fixes (3-5 days), which the `_ensure_bootstrapped()` guard minimizes by automatically re-populating the registry after resets.

## Consequences

### Positive

- **Import safety**: `from autom8_asana.models.business import Business` no longer triggers a 16-entity registration cascade. Imports are pure (no side effects beyond class definition).
- **Test isolation**: `SystemContext.reset_all()` + `_ensure_bootstrapped()` provides clean, automatic registry repopulation per test. No more hidden dependencies on import order determining registry state.
- **Lambda efficiency**: Handlers that do not use entity detection (e.g., cache_invalidate) no longer pay registration cost. Handlers that do use detection have explicit, debuggable initialization.
- **Debuggability**: Bootstrap failures appear in handler logs with structured context and clear stack traces from the entry point, rather than cryptic import-time errors.
- **Pattern alignment**: `ProjectTypeRegistry` now follows the same `_ensure_initialized()` pattern as `SchemaRegistry` and `MetricRegistry`. One pattern to learn, three registries that follow it.

### Negative

- **Developer ceremony**: Every new entry point (new Lambda handler, new CLI command, new script) must include a `bootstrap()` call. This is the same requirement as Django's `django.setup()` -- universally understood but occasionally forgotten.
- **WARNING noise in tests**: The `_ensure_bootstrapped()` guard fires after `SystemContext.reset_all()` in every test that touches detection, producing a WARNING log. This is informational, not actionable, but adds log volume in test runs.
- **Slightly more complex mental model**: Developers must understand that importing business models no longer populates the registry. The `_ensure_bootstrapped()` guard makes this transparent for most code paths, but awareness is needed for code that inspects registry contents directly.

### Neutral

- **No performance change for API server**: The API lifespan already runs initialization before accepting traffic. Moving registration from import-time to `bootstrap()` in lifespan is a timing change, not a latency change.
- **`register_all_models()` continues to exist**: The function is unchanged. It is called by `bootstrap()` and by `_ensure_bootstrapped()`. It can still be called directly in tests for explicit control.
- **`__init_subclass__` and `__set_name__` hooks unchanged**: These fire at class definition time (import) regardless of bootstrap. They are orthogonal to this decision.
