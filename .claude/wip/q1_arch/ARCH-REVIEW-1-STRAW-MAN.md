# Architectural Review 1: Straw-Man (Architecture Critique)

**Date**: 2026-02-18
**Scope**: Strongest possible critique of the autom8y-asana architecture
**Methodology**: Straw-man analysis -- identifying the most concerning structural weaknesses, inconsistencies, and failure modes
**Review ID**: ARCH-REVIEW-1

---

## 1. Triple Registry Problem

### The Three Registries

The codebase maintains three overlapping registries that must stay synchronized:

| Registry | Source | Purpose | Population |
|----------|--------|---------|------------|
| `ProjectTypeRegistry` | `src/autom8_asana/services/resolver.py` | Maps project GIDs to entity types | Runtime population from config |
| `EntityRegistry` | `src/autom8_asana/core/entity_registry.py` | SSoT for entity metadata (descriptors) | Module-level constant tuple |
| `EntityProjectRegistry` | `src/autom8_asana/services/resolver.py` | Maps entity types to project GIDs + sections | Runtime population from project data |

### The Synchronization Problem

These three registries encode overlapping views of the same truth: "which entity types live in which projects." But they are populated independently:

1. `EntityRegistry` is populated from `ENTITY_DESCRIPTORS` at module load time
2. `ProjectTypeRegistry` is populated at runtime from configuration
3. `EntityProjectRegistry` is populated at runtime from project data

If a new entity type is added to `ENTITY_DESCRIPTORS` but the configuration is not updated, `ProjectTypeRegistry` and `EntityProjectRegistry` will not know about it. If a project GID changes in Asana but `EntityDescriptor.project_gid` is not updated, `EntityRegistry` and `ProjectTypeRegistry` will disagree.

### Divergence Goes Undetected

There is no cross-registry validation. The import-time integrity checks in `entity_registry.py` (checks 6a-6f) validate schema/extractor/row model triads within the EntityRegistry, but they do not validate consistency against ProjectTypeRegistry or EntityProjectRegistry.

A developer could update one registry and forget the others. The system would continue operating with inconsistent entity resolution until a specific query path hits the divergent mapping.

### Impact

- **Silent misclassification**: An entity could be detected as type A by one registry and type B by another
- **Test brittleness**: Tests that depend on registry consistency may pass individually but fail in integration
- **Onboarding friction**: Understanding which registry to update for what purpose requires tribal knowledge

---

## 2. Cache Invalidation Gap

### The Gap

When data is modified directly in the Asana UI (not through the SDK), no invalidation occurs. The system relies exclusively on TTL expiration for these mutations.

### Why This Matters

The system is positioned as a caching layer over Asana, but it cannot observe external mutations. Consider the timeline:

```
T=0:  Business "Acme Corp" cached with name="Acme Corp" (TTL=1h)
T=5m: User renames to "Acme Corporation" in Asana UI
T=10m: SDK returns "Acme Corp" (stale, no invalidation triggered)
T=55m: SDK still returns "Acme Corp" (stale)
T=60m: TTL expires, next read fetches fresh "Acme Corporation"
```

For Business entities (1h TTL), data can be stale for up to 60 minutes after external modification.

### No Webhook Integration

Asana supports webhooks for change notifications. The SDK does not integrate with them. A webhook-driven invalidation would close this gap, but the current architecture has no webhook handler infrastructure.

### The Philosophy Contradiction

The cache subsystem treats freshness as a first-class concept (6 freshness states, 3 freshness modes, SWR semantics). But the only invalidation mechanism for external mutations is TTL expiration -- the simplest possible strategy. The sophistication of the freshness model is undermined by the simplicity of the invalidation model.

### Impact

- **Business decisions on stale data**: If a user changes a business entity's custom field in Asana and another user queries through the SDK within the TTL window, the second user gets stale data
- **Automation on stale state**: Pipeline rules may fire based on stale section membership
- **Silent correctness issues**: No error is raised; the data simply has not updated yet

---

## 3. Forty-Seven Hardcoded Section Names

### Three Parallel Representations

Section names exist in three incompatible forms:

| Representation | Source | Format | Count |
|---------------|--------|--------|-------|
| `SectionClassifier._mapping` | `activity.py` | Lowercase string dict keys | 47 (33 offer + 14 unit) |
| `OfferSection` enum | `sections.py` | Enum members mapping to GIDs | 1 (only ACTIVE) |
| `ProcessSection` enum | `process.py` (related) | Enum members for pipeline stages | Separate domain |

### The Problem

47 section names are hardcoded as string literals in classifier mappings:

```python
OFFER_CLASSIFIER = SectionClassifier(
    entity_type="offer",
    project_gid="...",
    _mapping={
        "active": AccountActivity.ACTIVE,
        "onboarding": AccountActivity.ACTIVATING,
        "paused": AccountActivity.INACTIVE,
        # ... 30 more hardcoded strings
    }
)
```

### CACHE_NOT_WARMED Cliff

When a section name does not match any hardcoded string in the classifier, `classify()` returns `None`. There is no "unknown section" category with degraded behavior. This creates a cliff: known sections work perfectly; unknown sections produce `None` which propagates through the system.

If Asana adds a new section to a project, it will not be classified until the source code is updated with the new section name.

### The Classification Gap

The `OfferSection` enum has only 1 member (`ACTIVE` with its GID) while the `OFFER_CLASSIFIER` has 33 section names. These two representations of "offer sections" are disconnected. There is no mapping from classifier section names to `OfferSection` GIDs.

### Impact

- **Source code deployment required for new sections**: Adding a section in Asana requires a code change, review, and deployment
- **Three places to update**: New sections may need updates in classifier mapping, enum, and potentially query engine section scoping
- **No runtime section discovery**: The system cannot adapt to Asana project structure changes at runtime

---

## 4. Import-Time Side Effects

### The Chain

**Source**: `src/autom8_asana/models/business/__init__.py:60-62`

```python
from autom8_asana.models.business._bootstrap import register_all_models
register_all_models()  # Side effect at import time
```

Any code that does `from autom8_asana.models.business import Business` triggers the full registration cascade.

### The Fragility Surface

| Mechanism | Location | Count | Risk |
|-----------|----------|-------|------|
| `register_all_models()` at import | `models/business/__init__.py:60-62` | 1 | Import order dependency |
| `__getattr__` lazy imports | `automation/__init__.py`, root `__init__.py`, + 4 more | 6+ | Deferred initialization failures |
| Function-body lazy imports | Scattered across `services/`, `persistence/`, `clients/` | 20+ | Circular dependency management |
| `# noqa: E402` suppressions | `models/business/__init__.py`, `clients/data/client.py`, + 3 more | 5 | Import order violations |

### Circular Import Fragility

The codebase manages at least 4 active circular dependency chains via lazy imports:

1. `services/universal_strategy.py` <-> `services/resolver.py` (bidirectional)
2. `models/business/__init__.py` -> `_bootstrap.py` -> entity classes -> `models/business/__init__.py` (registration cycle)
3. `persistence/session.py` -> `persistence/cascade.py` (deferred import at line 191)
4. `automation/__init__.py` -> `automation/pipeline.py` (deferred via `__getattr__`)

Each circular dependency is individually managed, but the aggregate creates a fragile import graph where reordering imports or adding new dependencies can cause import failures that are difficult to diagnose.

### Impact

- **Test isolation difficulty**: Tests that import `models.business` trigger registration; tests that reset registration state must do so carefully
- **Cold start latency**: Import-time registration adds to Lambda cold start time
- **Debugging difficulty**: Import errors manifest as `AttributeError` in `__getattr__` rather than clear `ImportError`

---

## 5. Seven Freshness Types, Two Cache Systems, Two Coalescers

### The Concept Inventory

The caching subsystem employs 31 distinct concepts that a developer must understand:

**Freshness modes** (3):
- `STRICT`: Always validate against source
- `EVENTUAL`: Return if within TTL
- `IMMEDIATE`: Return without validation

**Freshness states** (6):
- `FRESH`, `STALE_SERVABLE`, `STALE_REFRESHING`, `EXPIRED`, `MISSING`, `ERROR`

**Cache tiers** (4):
- Redis hot, S3 cold, Memory LRU, S3 Parquet

**Providers** (5):
- Null, InMemory, Redis, S3, Tiered

**Entry types** (14):
- TASK_RAW through CUSTOM_FIELDS

**Completeness levels** (4):
- MINIMAL, STANDARD, FULL, CUSTOM

### 3x Conceptual Density

A typical application cache has:
- 1-2 freshness modes (cached / expired)
- 1-2 cache tiers (memory / external)
- 3-5 entry types
- No completeness tracking

Total: ~10 concepts.

This system has ~31 concepts -- roughly 3x the typical density. Every new concept adds cognitive load for every developer who touches the cache layer.

### Two Cache Systems

The entity cache (Redis/S3) and DataFrame cache (Memory/S3) are architecturally separate systems with different:
- Freshness models (3-mode vs 6-state)
- Invalidation strategies (TTL+mutation vs SWR)
- Storage formats (JSON vs Parquet)
- Eviction policies (TTL vs LRU)

A developer working on "caching" must learn two different mental models.

### Impact

- **Onboarding cost**: New developers face ~31 caching concepts before they can confidently modify cache behavior
- **Cross-cutting changes are expensive**: A change to cache invalidation logic must consider both systems
- **Documentation debt**: The two systems share terminology (e.g., "freshness") but mean different things

---

## 6. Philosophy Contradiction: Freshness as First-Class vs. Best-Effort Invalidation

### The Aspiration

The cache architecture treats freshness as a sophisticated, multi-dimensional concept:
- 3 freshness modes for controlling validation behavior
- 6 freshness states for nuanced lifecycle tracking
- SWR for seamless background refresh
- Completeness levels for progressive enhancement
- Watermarks for incremental sync

### The Reality

The only actual invalidation mechanisms are:
1. **TTL expiration** (passive, time-based)
2. **MutationInvalidator** (fire-and-forget, SDK mutations only)
3. **CacheInvalidator** (SaveSession commit only)

External mutations (Asana UI, other integrations) have zero invalidation. The sophisticated freshness model tracks *how stale* data is, but it cannot *reduce* staleness for data modified outside the SDK.

### The Contradiction

Investing in 6 freshness states and SWR semantics implies "we care deeply about data freshness." Not implementing webhook-based invalidation implies "we accept potentially long staleness windows for external mutations." These positions are in tension.

### The Counter-Argument

The steel-man response is that this is intentional: the system optimizes for *resilience* (always serve something) not *consistency* (always serve fresh data). But if that is the intent, the 6-state freshness model is over-engineered for an AP (availability/partition-tolerance) system that accepts eventual consistency.

---

## 7. Pydantic Frozen Escape Hatches

### The Aspiration

Entity models are declared as `frozen=True` Pydantic v2 models, establishing immutability as an architectural principle.

### The Escape Hatches

Several patterns violate the frozen contract:

| Pattern | Locations | Purpose |
|---------|-----------|---------|
| `extra="allow"` on select models | Various entity models | Accept unknown fields from Asana API |
| `object.__setattr__()` calls | Descriptor system, hydration | Bypass Pydantic's frozen check for initialization |
| `PrivateAttr` mutation | Navigation properties | Set parent/holder references after construction |
| `model_post_init()` mutation | Entity initialization | Set computed fields after Pydantic validation |

### "Frozen Except When We Need to Change It"

The pattern is:
1. Declare model `frozen=True`
2. Use `PrivateAttr` for fields that need mutation
3. Use `object.__setattr__()` when even `PrivateAttr` is insufficient
4. Document the escape hatch as "necessary for initialization"

This creates a de facto two-phase initialization: Pydantic validates and freezes fields, then post-initialization code uses escape hatches to set additional state. The model is not truly frozen; it is frozen *after initialization completes*.

### Impact

- **False sense of immutability**: A developer reading `frozen=True` expects immutable objects, but `PrivateAttr` values can change after construction
- **Thread safety uncertainty**: If frozen models are shared across threads (they are, in the cache), mutation of `PrivateAttr` values during post-initialization could race with reads
- **Testing difficulty**: Models that look immutable but have mutable private state are harder to reason about in tests

---

## 8. Singleton Constellation

### The Singletons

6 `ClassVar` singletons + 1 module-level singleton:

| Singleton | Source | Population | Reset Mechanism |
|-----------|--------|------------|-----------------|
| `EntityRegistry._instance` | `core/entity_registry.py` | Module load (constant) | `reset()` classmethod |
| `SchemaRegistry._instance` | `dataframes/models/registry.py` | Lazy init on first access | `reset()` classmethod |
| `ProjectTypeRegistry._instance` | `services/resolver.py` | Runtime from config | `reset()` classmethod |
| `EntityProjectRegistry._instance` | `services/resolver.py` | Runtime from project data | `reset()` classmethod |
| `WatermarkRepository._instance` | `dataframes/watermark.py` | Lazy init | `reset()` classmethod |
| `_pending_fields` | `models/business/descriptors.py` | Module-level dict | No explicit reset |
| `_BOOTSTRAP_COMPLETE` | `models/business/_bootstrap.py` | Module-level bool | `reset_bootstrap()` |

### No Coordinator

The 6+ singletons have no coordinator or lifecycle manager. Each manages its own initialization and reset independently. There is no `SystemContext.initialize()` or `SystemContext.reset()` that ensures all singletons are in a consistent state.

### Test Reset Order-Sensitivity

Test fixtures must reset singletons in a specific order:

```python
# conftest.py (approximate)
EntityRegistry.reset()
SchemaRegistry.reset()
ProjectTypeRegistry.reset()
EntityProjectRegistry.reset()
WatermarkRepository.reset()
reset_bootstrap()
```

If reset order changes (e.g., SchemaRegistry reset before EntityRegistry), tests may see stale cross-references.

### Impact

- **Hidden global state**: 6+ singletons represent hidden global state that any code path can depend on
- **Test fragility**: Singleton reset ordering is a source of flaky tests
- **Startup ordering**: The singletons must initialize in a specific order, creating implicit startup dependencies

---

## 9. Async/Sync Duality

### The Pattern

The codebase maintains dual sync/async APIs throughout:

| Metric | Count | Source |
|--------|-------|--------|
| Sync bridge pattern occurrences | 88 | `_run_sync()`, `asyncio.run()`, `loop.run_until_complete()` |
| `threading.Lock` instances | 14 | Various singletons and registries |
| Async methods | Hundreds | `*_async()` suffix convention |
| Sync mirrors | Hundreds | Matching `method()` for each `method_async()` |

### The Problem

Every async method needs a sync mirror for consumers that cannot use `async/await`. This creates:

1. **Double API surface**: Every public method exists in two forms
2. **Sync bridge overhead**: `_run_sync()` creates a new event loop per call in sync context
3. **Lock contention**: `threading.Lock` in singletons can contend when sync bridge creates new threads
4. **Docstring duplication**: Some sync mirrors duplicate the full docstring (e.g., `DataServiceClient.get_insights` duplicates `get_insights_async`'s 13 parameter descriptions)

### Impact

- **API surface bloat**: Double the methods means double the documentation, double the tests, double the maintenance
- **Performance overhead**: Sync bridges that create event loops per call have measurable overhead
- **Confusion**: Developers must choose between sync and async APIs, with no clear guidance on when to use which

---

## 10. Summary: Where Complexity Is Unearned

| Issue | Complexity Cost | Root Cause | Severity |
|-------|----------------|-----------|----------|
| Triple registry | Cognitive + maintenance | No single source of truth for project<->type mapping | HIGH |
| Cache invalidation gap | Correctness risk | No webhook integration, TTL-only for external mutations | HIGH |
| 47 hardcoded sections | Maintenance + deployment | No runtime section discovery | MEDIUM |
| Import-time side effects | Fragility + debugging | Registration at import, circular deps | MEDIUM |
| 31 caching concepts | Cognitive load | Two separate cache systems with overlapping terminology | HIGH |
| Freshness vs. invalidation | Philosophy contradiction | Sophisticated tracking with primitive invalidation | MEDIUM |
| Frozen escape hatches | False guarantees | Pydantic v2 constraints on mutation | LOW |
| Singleton constellation | Test fragility + hidden state | No lifecycle coordinator | MEDIUM |
| Async/sync duality | API surface bloat | Dual-consumer requirement | LOW (inherent in the problem) |

The unearned complexity concentrates in two areas:

1. **Registry and configuration management**: Three registries, 47 hardcoded names, and 6+ singletons all encode overlapping truths about the domain model without a unified source
2. **Caching conceptual density**: 31 concepts across two systems with different mental models, sophisticated freshness tracking undermined by primitive invalidation
