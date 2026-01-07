# ADR: Entity Registry Consolidation

## Status

Proposed

## Context

The autom8_asana system has evolved to include two separate registries for mapping entity types to Asana project GIDs:

1. **ProjectTypeRegistry** (`models/business/registry.py`)
   - Used by: Detection system (Tier 1 project membership detection)
   - Population: `__init_subclass__` auto-registration when entity classes are imported
   - Maps: `project_gid -> EntityType`

2. **EntityProjectRegistry** (`services/resolver.py`)
   - Used by: Entity Resolver API (`/v1/resolve/{entity_type}`)
   - Population: `_discover_entity_projects()` during API startup
   - Maps: `entity_type (string) -> EntityProjectConfig`

This dual-registry architecture has caused detection failures:

```
Unable to detect type for task 1210979806530397 (Tier 5 fallback)
```

The task is in the "Businesses" project (GID `1200653012566782`), but `ProjectTypeRegistry.lookup()` returns `None` because the `Business` class was not imported when detection ran during cache warming.

### Root Cause Analysis

The `__init_subclass__` auto-registration pattern is fundamentally flawed for this use case:

1. **Import-order dependent**: Registration happens when a class is imported, not when it's defined
2. **No explicit contract**: There's no guarantee registration happens before lookup
3. **Silent failures**: Empty registry returns `None`, triggering Tier 5 fallback without error
4. **Circular dependency risk**: Importing model classes during bootstrap can trigger unintended side effects

### Design Principle Violations

| Principle | Violation |
|-----------|-----------|
| DRY | Same mappings in two places |
| Single Source of Truth | Two registries can disagree |
| Explicit over Implicit | `__init_subclass__` is "magic" |
| Fail-Fast | Silent failures during detection |

## Decision

**Consolidate to a single `ProjectRegistry` with explicit model-first registration.**

### Key Design Choices

1. **Single Registry**: Merge functionality of both registries into unified `ProjectRegistry`

2. **Explicit Registration**: Replace `__init_subclass__` auto-registration with explicit `register_all_models()` function called at module import time

3. **Model as Source of Truth**: Entity model `PRIMARY_PROJECT_GID` class attributes are authoritative; API discovery is supplementary

4. **Guaranteed Initialization Order**: Bootstrap runs at `models/business/__init__.py` import, ensuring registration before any detection calls

### Registration Flow

```
Application Start
       |
       v
+---------------------------+
|  Import models/business   |
|  __init__.py runs:        |
|  - register_all_models()  |
|  - All entity classes     |
|    imported               |
|  - All GIDs registered    |
+---------------------------+
       |
       v
+---------------------------+
|  Detection/Cache Warming  |
|  - registry.lookup() OK   |
|  - Tier 1 detection works |
+---------------------------+
       |
       v
+---------------------------+
|  API Startup (optional)   |
|  - Discovery supplement   |
|  - Pipeline projects      |
|  - Project names added    |
+---------------------------+
```

## Alternatives Considered

### Option A: Fix Import Order (Rejected)

Ensure all entity classes are imported before any detection calls.

**Pros:**
- Minimal code change
- Keeps existing `__init_subclass__` pattern

**Cons:**
- Fragile: Any new code path could break import order
- Doesn't fix the fundamental design flaw
- Hard to enforce: No compile-time guarantee

### Option B: Lazy Registration with Discovery Fallback (Rejected)

Keep `__init_subclass__` but fall back to API discovery if registry empty.

**Pros:**
- Backward compatible
- Self-healing

**Cons:**
- API dependency: Detection requires network calls
- Performance: Discovery adds latency
- Still has implicit registration (same fundamental flaw)

### Option C: Explicit Bootstrap (Chosen)

Replace `__init_subclass__` with explicit `register_all_models()`.

**Pros:**
- Explicit: Clear contract about when registration happens
- Deterministic: Same behavior regardless of import order
- Testable: Can verify registration in isolation
- Fail-fast: Missing registration is caught at startup

**Cons:**
- Requires code change in base classes
- Must update all entity classes (already have `PRIMARY_PROJECT_GID`)
- Breaking change for any external code relying on auto-registration

## Consequences

### Positive

1. **Single Source of Truth**: One registry eliminates synchronization bugs
2. **Deterministic Detection**: Registry state is known at startup
3. **Explicit Initialization**: No reliance on import-time side effects
4. **Testable**: Clear reset/bootstrap lifecycle for testing
5. **Performance**: No API calls needed for core detection

### Negative

1. **Migration Effort**: Must update base classes and test fixtures
2. **Manual Registration**: New entity types must be added to bootstrap
3. **Breaking Change**: External code using `EntityProjectRegistry` must migrate

### Neutral

1. Existing detection API signatures unchanged
2. Performance characteristics unchanged
3. Test patterns similar (just different reset mechanism)

## Implementation

Per TDD-registry-consolidation:

### Phase 1: Explicit Model Registration

1. Create `_bootstrap.py` with `register_all_models()`
2. Call from `models/business/__init__.py`
3. Remove `__init_subclass__` registration
4. Update test fixtures

### Phase 2: Registry Consolidation

1. Extend `ProjectTypeRegistry` to `ProjectRegistry`
2. Add `ProjectConfig`, `get_config()`, backward-compatible methods
3. Create `EntityProjectRegistry` deprecation shim
4. Update API to use unified registry

### Phase 3: Cleanup

1. Remove `EntityProjectRegistry`
2. Remove deprecated helper functions
3. Update documentation

## Compliance

- [ ] Single `ProjectRegistry` replaces both legacy registries
- [ ] `register_all_models()` called at import time
- [ ] Detection works during cache warming
- [ ] Entity Resolver API unchanged
- [ ] Deprecation warnings for old API usage

## Related

- **ADR-0031**: Registry and Discovery Architecture
- **ADR-0060**: Entity Resolver Project Discovery
- **TDD-registry-consolidation**: Implementation specification
