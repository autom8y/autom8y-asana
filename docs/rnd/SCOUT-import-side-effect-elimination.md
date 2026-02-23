# SCOUT-import-side-effect-elimination

## Executive Summary

Six approaches for eliminating import-time side effects from the autom8y-asana codebase (111K LOC, Pydantic v2, 10,500+ tests) were evaluated against the constraints of preserving the descriptor system (ADR-0081/0082), `__init_subclass__` patterns, and Pydantic v2 frozen model semantics. The recommended strategy is a phased combination: **Adopt** Explicit Application Bootstrap (Approach 1) as the primary mechanism, **Adopt** Registry Pattern with Deferred Resolution (Approach 6) to make registries tolerant of access-before-bootstrap, and **Hold** on all other approaches. This combination mirrors the Django app registry pattern -- the most production-proven solution to exactly this class of problem -- while being achievable incrementally within a 3-month window.

---

## Problem Statement

**Type**: Necessity (defensive / maintainability)

The current architecture has import-time side effects that cause:

1. **Fragile import ordering**: Any `from autom8_asana.models.business import X` triggers `register_all_models()`, which must run before any detection calls. This creates invisible coupling documented in the debt ledger (D-029, RF-009).
2. **Test pollution**: Mutable singletons (`ProjectTypeRegistry._instance`, `SchemaRegistry._instance`, `MetricRegistry._instance`, `WorkspaceProjectRegistry._instance`) persist across tests. Currently mitigated by explicit `.reset()` calls in 30+ test locations.
3. **Cold start penalty**: Lambda handlers pay full registration cost even when only needing a subset of functionality.
4. **Circular dependency management**: 6+ `__getattr__` lazy-load sites, 20+ deferred function-body imports, and 4 active circular dependency chains are all symptoms of import-time coupling.

The codebase comment at `models/business/__init__.py:55-58` explicitly acknowledges this as deferred work (RF-009).

---

## Approach-by-Approach Assessment

### Approach 1: Explicit Application Bootstrap

**What it is**: Replace import-time `register_all_models()` with an explicit `app.bootstrap()` call at each entry point. FastAPI `lifespan`, Lambda handler preamble, CLI `__main__`, and test `conftest.py` each call a single `bootstrap()` function.

**Maturity**: Mainstream

**Production references**:
- Django `django.setup()` -- called once before any model access (since Django 1.7, used by every Django application worldwide)
- Flask `create_app()` factory pattern -- explicit initialization at app creation
- SQLAlchemy `configure_mappers()` -- explicit mapper finalization step

**Pydantic v2 compatibility**: Full. `__init_subclass__` and `__set_name__` fire at class definition time (import) regardless. Bootstrap only controls when registries get populated. Pydantic `ConfigDict(ignored_types=...)` continues to work because descriptor types exist at import time; only their *registration into lookup dictionaries* moves to bootstrap.

**Impact on test isolation**: Positive. Bootstrap becomes explicit in `conftest.py`. Tests that need clean registries call `reset_bootstrap()` + `bootstrap()`. No more implicit state from import order. Current 30+ `.reset()` sites remain but become more predictable.

**Impact on cold start (Lambda)**: Positive. Bootstrap can be conditional -- import entity modules without triggering registration. Lambda handlers that only need cache operations skip the business model bootstrap entirely. Estimated 50-100ms savings on Lambda cold starts by avoiding eager registration when not needed.

**Estimated effort**: 2-3 weeks for a 111K LOC codebase.
- Week 1: Create `bootstrap()` function, add calls to lifespan/Lambda/CLI/conftest
- Week 2: Remove `register_all_models()` call from `__init__.py`, fix broken tests
- Week 3: Audit all entry points, fix edge cases, verify CI green

**What breaks during migration**:
- Any code that imports `from autom8_asana.models.business import X` and immediately calls `detect_entity_type()` without bootstrap will get `None` from registry lookups
- Test files that import business models at module level and expect registry population will need bootstrap fixtures
- Scripts and notebooks that `import autom8_asana.models.business` will need a `bootstrap()` call

**Verdict: ADOPT**

**Rationale**: This is the Django pattern. It is the single most proven approach to this exact problem class in the Python ecosystem. The codebase already has the building blocks (`register_all_models()` is idempotent, `reset_bootstrap()` exists, `lifespan()` is the natural hook). The comment at line 55-58 of `models/business/__init__.py` already identifies this as the intended direction.

---

### Approach 2: Plugin/Entry Point Discovery (importlib.metadata)

**What it is**: Use `importlib.metadata.entry_points(group='autom8_asana.entity_types')` to discover and register entity classes at runtime. Each entity declares itself via `pyproject.toml` entry points.

**Maturity**: Mainstream (for plugin systems), Experimental (for internal model registration)

**Production references**:
- pytest plugin discovery
- setuptools console_scripts
- OpenStack stevedore
- Apache Airflow provider discovery

**Pydantic v2 compatibility**: Full. Entry points load classes which trigger `__init_subclass__` on import. No conflict with frozen models or descriptors.

**Impact on test isolation**: Neutral to negative. Entry points are package metadata -- they cannot be easily overridden per-test without monkeypatching `importlib.metadata`. Test isolation becomes harder, not easier.

**Impact on cold start (Lambda)**: Negative. `entry_points()` scans installed package metadata. On Lambda with many dependencies, this adds 20-50ms. The entities are in the same package, so there is no discovery benefit -- we already know what they are.

**Estimated effort**: 3-4 weeks.
- Complex `pyproject.toml` changes for each entity type
- Entry point groups need to be defined and documented
- Discovery function replaces `register_all_models()`
- Test infrastructure needs mocking of entry points

**What breaks during migration**:
- Build tooling must regenerate entry points on every entity change
- `editable` installs (`pip install -e .`) may not refresh entry points without reinstall
- Development workflow friction: add entity -> reinstall package -> test

**Verdict: HOLD**

**Rationale**: Entry points solve a different problem -- discovering plugins across package boundaries. All 16 entity types live in the same package (`autom8_asana.models.business`). Using entry points adds build tooling complexity and development friction for zero discovery benefit. The explicit bootstrap (Approach 1) is simpler and more appropriate for intra-package registration.

---

### Approach 3: Dependency Injection Container (dependency-injector, injector, lagom)

**What it is**: Replace singletons with a DI container that manages initialization order and lifecycle. Wire registries and services at application startup.

**Maturity**: Growing (Python DI ecosystem), Mainstream (in Java/.NET)

**Production references**:
- `dependency-injector`: Used by some Python microservice teams, 3.5K GitHub stars, Cython-based performance
- `lagom`: Type-based auto-wiring, newer but well-designed
- `injector`: Google's Python DI library, name-based matching

**Pydantic v2 compatibility**: Problematic. `dependency-injector` has [open issues with Pydantic v2](https://github.com/ets-labs/python-dependency-injector/issues/726) -- the `.from_pydantic()` method broke when `BaseSettings` moved to `pydantic-settings`. The `@inject` + `Provide[]` pattern does not interoperate cleanly with Pydantic's `model_config` or `ConfigDict`. The descriptor system (ADR-0081/0082) would need careful compatibility testing.

**Impact on test isolation**: Strongly positive. DI containers natively support per-test container overrides. This is the strongest argument for DI -- it eliminates `_instance = None` reset patterns entirely.

**Impact on cold start (Lambda)**: Neutral to negative. Container initialization adds overhead. `dependency-injector`'s Cython compilation may add import time. Lambda cold starts would not improve.

**Estimated effort**: 8-12 weeks (high risk).
- Week 1-2: Select library, prototype with one registry
- Week 3-6: Migrate 4 singleton registries to container
- Week 7-10: Wire container into all entry points, update 10,500+ tests
- Week 11-12: Performance testing, edge case fixes

**What breaks during migration**:
- Every `get_registry()` / `get_workspace_registry()` / `SchemaRegistry.get_instance()` call site (hundreds) must change
- Global state access patterns incompatible with container patterns
- `__init_subclass__` hooks that call `get_registry()` need careful sequencing with container lifecycle
- DI library maintenance risk: `dependency-injector` has had periods of slow maintenance

**Verdict: HOLD**

**Rationale**: DI containers solve a broader problem than what we have. The codebase has 4 singleton registries, not 40 services. The test isolation benefit is real but achievable more cheaply via Approach 1 + Approach 6 (explicit bootstrap + deferred resolution). The Pydantic v2 compatibility issues, 8-12 week effort, and library maintenance risk make this a poor fit for a 6-month runway. Revisit if codebase grows to 20+ injectable services.

---

### Approach 4: Lazy Module Pattern (PEP 562 `__getattr__`)

**What it is**: Formalize the existing ad-hoc `__getattr__` lazy imports into a consistent pattern using PEP 562. Use `lazy_loader` library or manual `__getattr__` in all `__init__.py` files to defer all imports until first access.

**Maturity**: Mainstream (PEP 562 since Python 3.7)

**Production references**:
- scikit-image: Adopted lazy loading for entire package
- NetworkX: Full lazy loading implementation
- MNE-Python: Large scientific package with lazy imports
- Already partially used in this codebase: `autom8_asana/__init__.py`, `automation/__init__.py`, `cache/__init__.py`

**Pydantic v2 compatibility**: Partial. Lazy module loading defers *when* classes are imported. But Pydantic model validation triggers `__init_subclass__` at class definition time -- you cannot make class definition lazy without also making the class itself lazy. The descriptor `__set_name__` protocol fires at class body execution, not at import. This means lazy loading a module containing Pydantic models will fire all metaclass hooks the moment the module actually loads, just *later*.

**Impact on test isolation**: None. Lazy imports do not change singleton lifecycle -- they only change when the singleton is first created. The underlying state management problem remains.

**Impact on cold start (Lambda)**: Moderate positive. If Lambda handlers only access a subset of the package, unused modules are never loaded. Estimated 100-200ms improvement for handlers that do not touch business models. However, any handler that accesses *any* business entity triggers the full cascade.

**Estimated effort**: 2-3 weeks.
- Formalize existing 3 `__getattr__` sites
- Add `__getattr__` to `models/business/__init__.py` (the 85-export barrel)
- Add `__dir__` for IDE autocompletion
- Test with all entry points

**What breaks during migration**:
- IDE autocompletion may degrade without proper `__dir__` implementation
- `from autom8_asana.models.business import *` becomes unpredictable
- Static analysis tools (mypy, pyright) may lose type information
- Debugging import errors becomes harder (stack traces show `__getattr__` instead of real import path)

**Verdict: HOLD**

**Rationale**: Lazy loading treats the symptom (import time) rather than the disease (import-time side effects). The codebase already uses this pattern in 3 places for specific circular dependency breaks. Formalizing it everywhere adds complexity without solving test isolation or singleton management. The real win is from Approach 1 (explicit bootstrap) which eliminates the need for most lazy imports. Keep existing lazy import sites; do not proliferate the pattern.

---

### Approach 5: Import Graph Restructuring

**What it is**: Break circular dependencies by introducing interface packages (protocols-only modules) that both sides import. Create a `models/business/protocols.py` that defines `RegistryProtocol`, `EntityProtocol`, etc. Both `registry.py` and `detection/` import from protocols instead of from each other.

**Maturity**: Mainstream

**Production references**:
- Every large Python codebase with clean architecture (FastAPI, SQLAlchemy, Django)
- typing.Protocol (PEP 544) is the standard mechanism since Python 3.8
- This codebase already uses `TYPE_CHECKING` guards extensively

**Pydantic v2 compatibility**: Full. Protocol classes are runtime-checkable but do not trigger Pydantic model creation. `__init_subclass__` and `__set_name__` are unaffected.

**Impact on test isolation**: Neutral. Restructuring imports does not change singleton lifecycle.

**Impact on cold start (Lambda)**: Minimal. Eliminates deferred imports (saving microseconds per import) but does not change the total amount of code loaded.

**Estimated effort**: 4-6 weeks (high risk of cascading changes).
- Audit all 6 circular dependency chains
- Create protocol modules for each cycle
- Migrate 20+ deferred imports to top-level imports
- Verify no regressions across 10,500+ tests

**What breaks during migration**:
- Every deferred import site must be carefully validated
- Protocol compatibility must match actual implementations exactly
- Some cycles may be fundamental (e.g., `models.business` <-> `cache` <-> `automation`) and not solvable with protocols alone
- Risk of introducing new cycles while fixing old ones

**Verdict: ASSESS**

**Rationale**: Import graph restructuring is the correct long-term direction for code health, but it is a prerequisite-free improvement -- it can be done at any time and does not gate the bootstrap pattern. The current 6 circular dependency chains have stabilized (no new cycles in 3+ months). Recommend tackling this after Approach 1+6 are in place, when each deferred import can be evaluated: does the bootstrap eliminate the need for it, or does a protocol module still help? Time-box assessment to 2 days.

---

### Approach 6: Registry Pattern with Deferred Resolution

**What it is**: Keep registries but make them tolerant of pre-bootstrap access. Registration happens at import (via `__init_subclass__`), but resolution (looking up related types, validating cross-references) defers until first access. Failed lookups before bootstrap return `None` / empty rather than crashing.

**Maturity**: Mainstream

**Production references**:
- Django ORM app registry: `lazy_model_operation()` queues callbacks until models are ready, `get_registered_model()` is safe at import time
- SQLAlchemy mapper configuration: `_post_configure_properties()` defers configuration until all mappers exist
- Celery task registry: Tasks register at import, but task graph resolution defers until worker startup
- This codebase's `SchemaRegistry._ensure_initialized()`: Already implements deferred resolution (lazy init on first `get_schema()` call)

**Pydantic v2 compatibility**: Full. Deferred resolution is orthogonal to Pydantic. `__init_subclass__` continues to fire at class definition, but instead of calling `get_registry().register()` (which currently is a no-op because registration moved to `_bootstrap.py`), it could queue pending registrations. Resolution happens at first lookup or explicit bootstrap.

**Impact on test isolation**: Positive. Deferred resolution means tests that never touch detection do not need bootstrap. Tests that do touch detection get explicit control via `bootstrap()` + `reset()`.

**Impact on cold start (Lambda)**: Positive. Lambda handlers that import business models but only need field access (not detection) skip the resolution step entirely.

**Estimated effort**: 1-2 weeks (low risk).
- Add `_ensure_bootstrapped()` guard to `ProjectTypeRegistry.lookup()` (similar to `SchemaRegistry._ensure_initialized()`)
- Make `register_all_models()` callable from `_ensure_bootstrapped()` on first lookup, OR from explicit `bootstrap()`
- Remove `register_all_models()` from `__init__.py` import time

**What breaks during migration**:
- Code that accesses registry *between* import and bootstrap gets `None` instead of populated data (but this is the correct behavior -- it was getting populated data only due to import-time side effects)
- Minor performance: first registry lookup after bootstrap pays initialization cost

**Verdict: ADOPT**

**Rationale**: This is the natural complement to Approach 1. While explicit bootstrap handles the "when" (application startup), deferred resolution handles the "what if someone forgets" (graceful degradation). The codebase already has this pattern in `SchemaRegistry._ensure_initialized()` -- extending it to `ProjectTypeRegistry` and `WorkspaceProjectRegistry` is straightforward. Combined with Approach 1, this creates a robust two-layer defense: explicit bootstrap at entry points, lazy bootstrap as fallback.

---

## Comparison Matrix

| Criteria | Status Quo | 1. Explicit Bootstrap | 2. Entry Points | 3. DI Container | 4. PEP 562 Lazy | 5. Import Restructure | 6. Deferred Resolution |
|----------|------------|----------------------|-----------------|-----------------|-----------------|----------------------|----------------------|
| **Eliminates import-time side effects** | No | Yes | Yes | Yes | Partially | No (just fixes cycles) | Partially |
| **Test isolation improvement** | Baseline | Moderate | Worse | Strong | None | None | Moderate |
| **Lambda cold start impact** | Baseline | +50-100ms | -20-50ms | Neutral | +100-200ms | Minimal | +20-50ms |
| **Pydantic v2 compatibility** | N/A | Full | Full | Problematic | Partial | Full | Full |
| **Descriptor system preserved** | N/A | Yes | Yes | Unknown | Yes | Yes | Yes |
| **`__init_subclass__` preserved** | N/A | Yes | Yes | Yes | Yes | Yes | Yes |
| **Effort (weeks)** | 0 | 2-3 | 3-4 | 8-12 | 2-3 | 4-6 | 1-2 |
| **Migration risk** | N/A | Low | Medium | High | Medium | High | Low |
| **Incremental migration** | N/A | Yes | No (all or nothing) | No | Yes | Yes | Yes |
| **Production precedent** | N/A | Django, Flask, SQLAlchemy | pytest, Airflow | Spring (Java) | scikit-image | Generic best practice | Django ORM, Celery |
| **Addresses root cause** | N/A | Yes | Yes | Yes | No | Partially | Yes |

---

## Recommended Strategy

### Phase 1: Foundation (Weeks 1-3) -- ADOPT

Implement Approach 1 (Explicit Bootstrap) + Approach 6 (Deferred Resolution) together:

1. **Week 1**: Add `_ensure_bootstrapped()` to `ProjectTypeRegistry.lookup()` following the existing `SchemaRegistry._ensure_initialized()` pattern. This is the safety net.

2. **Week 2**: Create `autom8_asana.bootstrap()` function that calls `register_all_models()`. Add calls to:
   - `api/lifespan.py` -- before entity discovery (line 129)
   - Lambda handler preambles (`cache_warmer.py`, `cache_invalidate.py`, workflow handlers)
   - Test root `conftest.py` -- as a session-scoped fixture
   - Remove `register_all_models()` call from `models/business/__init__.py:66`

3. **Week 3**: Fix broken tests (estimated 50-100 tests affected based on current `.reset()` usage patterns), verify CI green, verify Lambda cold starts.

### Phase 2: Cleanup (Weeks 4-5) -- ASSESS

Assess which of the 20+ deferred function-body imports and 6 `__getattr__` lazy-load sites are still needed after bootstrap is explicit. Many were workarounds for import-time registration; with registration moved to bootstrap, direct top-level imports may now work.

### Phase 3: Graph Health (Month 3+) -- ASSESS

Time-boxed (2 days) assessment of the 4 active circular dependency chains. For each, determine whether:
- The bootstrap pattern resolved it (remove deferred import)
- A protocol module would help (introduce interface package)
- The cycle is fundamental and the deferred import is the correct solution (document and keep)

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests fail due to missing bootstrap | High | Medium | Session-scoped `conftest.py` fixture; `_ensure_bootstrapped()` fallback |
| Lambda handlers miss bootstrap call | Medium | High | `_ensure_bootstrapped()` lazy fallback ensures correctness; add integration test |
| Third-party code imports business models without bootstrap | Low | Medium | Deferred resolution (Approach 6) handles this transparently |
| Performance regression from deferred initialization | Low | Low | First lookup adds <5ms; dominated by network I/O in all real paths |
| Developer confusion about when to call bootstrap | Medium | Low | Document in CLAUDE.md, add `RuntimeError` if detection called pre-bootstrap without fallback |

---

## Ecosystem Assessment

- **Community**: Python's explicit initialization pattern is universally understood. No new libraries required.
- **Documentation**: Django's `django.setup()` pattern is extensively documented. Our implementation is simpler (single `bootstrap()` function).
- **Tooling**: No new tooling. Existing mypy, pytest, ruff all work unchanged.
- **Adoption**: Every Django application (hundreds of thousands) uses this pattern. FastAPI's `lifespan` context manager is the standard hook.

---

## The Acid Test

*"If we do not adopt this now, will we regret it in two years?"*

**Yes.** The import-time side effects are a growing liability:
- Every new entity type adds to the registration cascade
- Every new developer hits the "why does import order matter" learning curve
- Every Lambda handler pays the full initialization cost
- The 30+ test `.reset()` calls are a maintenance burden that scales linearly with test count

The fix is well-understood, low-risk, and follows the most proven pattern in the Python ecosystem. Delaying increases the migration cost as the codebase grows.

---

## Fit Assessment

- **Philosophy Alignment**: Strong. The codebase values explicit initialization (see `lifespan()`, `bootstrap()` in registry consolidation). This extends that philosophy.
- **Stack Compatibility**: Perfect. FastAPI `lifespan` is the natural hook. Pydantic v2 frozen models and descriptors are unaffected. `__init_subclass__` continues to work.
- **Team Readiness**: High. The team already implemented `register_all_models()` with idempotency guards, `reset_bootstrap()` for testing, and `_ensure_initialized()` in `SchemaRegistry`. The patterns are familiar.

---

## Sources

- [Pydantic v2 Import Performance (Issue #7263)](https://github.com/pydantic/pydantic/issues/7263)
- [Pydantic v2 Import Time Reduction (Issue #7409)](https://github.com/pydantic/pydantic/issues/7409)
- [Django Applications Documentation](https://docs.djangoproject.com/en/6.0/ref/applications/)
- [Django Apps Registry Source](https://github.com/django/django/blob/main/django/apps/registry.py)
- [PEP 562 - Module __getattr__ and __dir__](https://peps.python.org/pep-0562/)
- [Scientific Python SPEC 1 - Lazy Loading](https://scientific-python.org/specs/spec-0001/)
- [dependency-injector Pydantic v2 Compatibility Issue](https://github.com/ets-labs/python-dependency-injector/issues/726)
- [SQLAlchemy ORM Mapped Class Configuration](https://docs.sqlalchemy.org/en/21/orm/mapper_config.html)
- [Python Packaging: Creating and Discovering Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)
- [Fixing Circular Imports with Protocol](https://pythontest.com/fix-circular-import-python-typing-protocol/)
- [AWS Lambda Cold Start Optimization 2025](https://zircon.tech/blog/aws-lambda-cold-start-optimization-in-2025-what-actually-works/)
- [Lagom DI - Comparison to Alternatives](https://lagom-di.readthedocs.io/en/stable/comparison/)
