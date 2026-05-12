---
domain: feat/entity-detection
generated_at: "2026-05-08T00:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/business/detection/"
  - "./.know/architecture.md"
generator: theoros
source_hash: "8980bcd7"
confidence: 0.96
format_version: "1.0"
---

# Multi-Tier Entity Type Detection

## Purpose and Design Rationale

The detection subsystem answers: given an Asana task, what business entity type does it represent? This determination is the prerequisite for all downstream behavior — hydration, holder identification, cache TTL selection, DataFrame extraction, and write routing all depend on knowing the entity type.

Asana tasks carry no native "entity type" field. The codebase infers type from extrinsic signals: which project a task belongs to, what its name contains, who its parent is, and (as last resort) what subtask structure it has. Because signals vary in reliability and API cost, the system chains them into a priority-ordered tier hierarchy. Earlier tiers are cheap and authoritative; later tiers are expensive and probabilistic.

### Design Decisions

| Decision | Rationale | Reference |
|---|---|---|
| Tier 1 (project membership) is the canonical, deterministic path | Eliminates entity collision that SCAR-001 introduced when entity classes lacked `PRIMARY_PROJECT_GID` | ADR-0101, SCAR-001 |
| Sync path (Tiers 1-3) is zero-API — no API calls allowed | Keeps the hot path cheap and callable from sync contexts without risk of sync-in-async (SCAR-009) | TDD-DETECTION/FR-DET-007 |
| Async Tier 1 extends static lookup with lazy workspace discovery | Pipeline project GIDs are not always known at boot; discovery on first miss allows dynamic enrollment without restart | ADR-0109, TDD-WORKSPACE-PROJECT-REGISTRY |
| Cache wraps Tier 4 exclusively, not the whole function entry | Tiers 1-3 are already O(1) or O(pattern); caching them would add complexity with no gain. Tier 4 involves an API call (subtask fetch) and is expensive | PRD-CACHE-PERF-DETECTION, FR-CACHE-003 |
| `get_settings()` deferred behind `@functools.cache` in facade | AWS Lambda extension's HTTP listener is not guaranteed ready at module import — settings resolution at module load caused HTTP 400 failures (SCAR-CW-001 layer 4) | PRD-CACHE-PERF-DETECTION FR-VERSION-003, facade.py:76-86 |
| `ENTITY_TYPE_INFO` as single source of truth for `NAME_PATTERNS` and `PARENT_CHILD_MAP` | Prior separate definitions diverged; consolidation ensures pattern-map and parent-child-map always stay in sync with entity type inventory | types.py EntityTypeInfo, config.py |
| Word-boundary regex in Tier 2 (not simple `in` check) | Raw substring matching caused false positives (e.g., "Community" matching "unit") | ADR-0117 |
| UNKNOWN results are never cached | UNKNOWN should be retried on next call — it may be transient (task not yet added to a project); caching it would lock the task into a bad type indefinitely | FR-CACHE-006 |

### Rejected Alternatives

- **Tier 0 (Asana Custom Field)**: The runbook at `docs/runbooks/RUNBOOK-detection-troubleshooting.md` references a historical architecture with a "Tier 0" based on custom field values and an `EntityDetector` class. This design was abandoned. The current codebase has no `Tier 0` and no `EntityDetector` class. The runbook is **stale and not safe for current-state troubleshooting**.
- **Single-tier name-only detection**: Rejected because name collisions across entity types are common; project membership is the only reliable deterministic signal.
- **Full-function result caching (all tiers)**: Rejected because Tiers 1-3 are already cheap; caching at function entry would complicate staleness management for cases where the task moves projects.

---

## Conceptual Model

### The Tier Chain

```
Async Tier 1 (async): WorkspaceProjectRegistry.lookup_or_discover_async()
    ↓ miss
Tier 1 (sync): ProjectTypeRegistry.lookup(project_gid) — O(1), no API, confidence=1.0
    ↓ miss
Tier 2 (sync): Word-boundary name pattern matching (PatternSpec/get_pattern_priority) — confidence=0.6
    ↓ miss
Tier 3 (sync): PARENT_CHILD_MAP lookup (requires caller to supply parent_type) — confidence=0.8
    ↓ miss (or allow_structure_inspection=False)
[Cache check — only on async path when allow_structure_inspection=True]
    ↓ cache miss
Tier 4 (async): client.tasks.subtasks_async(task.gid).collect() — API call, confidence=0.9
    ↓ no match
Tier 5: UNKNOWN — confidence=0.0, needs_healing=True
```

**Sync path (`detect_entity_type`)**: Covers Tiers 1-3. Zero API calls. Safe to call from sync contexts.

**Async path (`detect_entity_type_async`)**: Executes async Tier 1 first (with lazy discovery), then falls through to sync Tiers 2-3, then optionally executes Tier 4 with cache integration (only when `allow_structure_inspection=True`). The cache check occurs _after_ Tiers 1-3 pass (not at function entry).

### DetectionResult Contract

Every tier produces a `DetectionResult` (frozen dataclass, `slots=True`):

| Field | Type | Meaning |
|---|---|---|
| `entity_type` | `EntityType` | Detected type or `EntityType.UNKNOWN` |
| `confidence` | `float` | Tier-specific constant: 1.0/0.6/0.8/0.9/0.0 |
| `tier_used` | `int` | Which tier succeeded (1-5) |
| `needs_healing` | `bool` | `False` only for Tier 1; `True` for all others (entity lacks expected project membership) |
| `expected_project_gid` | `str \| None` | Project GID the entity should be in for Tier 1 detection |

`DetectionResult.__bool__` returns `False` for `UNKNOWN`, `True` otherwise — enabling natural `if result:` checks. `is_deterministic` property is `True` only for `tier_used == 1`.

### Key Terminology

| Term | Definition |
|---|---|
| `EntityType` | Enum in `core/types.py`. Values: BUSINESS, CONTACT, CONTACT_HOLDER, UNIT, UNIT_HOLDER, OFFER, OFFER_HOLDER, PROCESS, PROCESS_HOLDER, LOCATION, LOCATION_HOLDER, DNA_HOLDER, RECONCILIATIONS_HOLDER, ASSET_EDIT_HOLDER, VIDEOGRAPHY_HOLDER, HOURS, UNKNOWN |
| `EntityTypeInfo` | Frozen dataclass (config.py) that is the **single source of truth** for each entity type's name_pattern, holder_attr, child_type, emoji, and has_project flag |
| `ENTITY_TYPE_INFO` | Module-level dict mapping `EntityType → EntityTypeInfo` — drives both `NAME_PATTERNS` and `PARENT_CHILD_MAP` derivation |
| `NAME_PATTERNS` | Derived `dict[str, EntityType]` for Tier 2 simple-substring matching (not the full word-boundary matcher — see `patterns.py`) |
| `PARENT_CHILD_MAP` | Derived `dict[EntityType, EntityType]` for Tier 3 parent→child inference |
| `PatternSpec` | Dataclass in `models/business/patterns.py` holding tuple of patterns + `word_boundary` flag |
| `needs_healing` | A task `needs_healing=True` means it should be assigned to the `expected_project_gid` but currently isn't; the persistence layer handles healing writes |
| `identify_holder_type` | Facade function — wraps detection system + falls back to legacy `HOLDER_KEY_MAP` matching with a `detection_fallback_holder_key_map` warning log |

### Inter-Feature Relationships

**Provides to**:
- `models/business/business.py` — `Business._identify_holder` → `identify_holder_type()`
- `models/business/unit.py` — `Unit._identify_holder` → `identify_holder_type()` (with `filter_to_map=True`)
- `models/business/hydration.py` — `detect_entity_type_async()` for traversal decisions
- `dataframes/resolver/cascading.py` — `detect_entity_type()` for cascade field resolution
- `dataframes/views/cascade_view.py` — `detect_entity_type()` and dict variant
- `dataframes/views/dataframe_view.py` — `detect_entity_type_from_dict()` for parent type
- `clients/task_ttl.py` — `detect_entity_type_from_dict()` for TTL selection
- `dataframes/builders/task_cache.py` — `detect_entity_type_from_dict()` for cache-key routing

**Consumes from**:
- `core/entity_registry.py` — `EntityRegistry.get_primary_gid()` (Tier 1 static lookup)
- `models/business/registry.py` — `get_registry()`, `get_workspace_registry()` (Tier 1 async discovery)
- `models/business/patterns.py` — `get_pattern_config()`, `get_pattern_priority()`, `STRIP_PATTERNS` (Tier 2)
- `client.tasks.subtasks_async()` — Asana API (Tier 4)
- `cache/models/entry.py` — `CacheEntry`, `EntryType.DETECTION` (cache integration)
- `settings.py` — `get_settings().cache.ttl_detection` (lazy-loaded, `ASANA_CACHE_TTL_DETECTION` env var)

---

## Implementation Map

### File Inventory

| File | Role | Key Exports |
|---|---|---|
| `detection/types.py` | Type definitions | `DetectionResult`, `EntityTypeInfo`, `CONFIDENCE_TIER_1..5` |
| `detection/config.py` | Entity type master config | `ENTITY_TYPE_INFO`, `NAME_PATTERNS` (derived), `PARENT_CHILD_MAP` (derived), `get_holder_attr()`, `entity_type_to_holder_attr()` |
| `detection/tier1.py` | Project membership (sync + async with lazy workspace discovery) | `detect_by_project_membership`, `_detect_tier1_project_membership_async`, `detect_by_project_membership_async` |
| `detection/tier2.py` | Name pattern (word-boundary regex, LRU-cached compilation) | `detect_by_name_pattern`, `_detect_by_name_pattern`, `_compile_word_boundary_pattern`, `_strip_decorations` |
| `detection/tier3.py` | Parent inference (`PARENT_CHILD_MAP` lookup) | `detect_by_parent_inference` |
| `detection/tier4.py` | Structure inspection (async, API subtask fetch) | `detect_by_structure_inspection`; internal constants `BUSINESS_INDICATORS`, `UNIT_INDICATORS` |
| `detection/facade.py` | Orchestration + cache integration + holder identification | `detect_entity_type`, `detect_entity_type_async`, `detect_entity_type_from_dict`, `identify_holder_type`, `detect_by_project`, `detect_by_parent`, `detect_by_structure_async`, `_get_cached_detection`, `_cache_detection_result`, `_detection_cache_ttl` |
| `detection/__init__.py` | Package re-export surface | Re-exports facade and types |

All entity types are re-exported from `models/business/__init__.py` (lines 91-93, 204).

### Data Flow

**Sync primary path**:
```
Task(gid, name, memberships)
  → facade.detect_entity_type(task, parent_type=None)
  → tier1.detect_by_project_membership(task)
      → _extract_project_gid(task)  [task.memberships[0]["project"]["gid"]]
      → registry.lookup(project_gid)  [O(1) ProjectTypeRegistry]
      → DetectionResult(tier=1, confidence=1.0, needs_healing=False)
  [on miss] → tier2._detect_by_name_pattern(task)
      → patterns.get_pattern_priority()  [entity type order list]
      → patterns.get_pattern_config()    [PatternSpec per entity type]
      → _strip_decorations(task.name)
      → _compile_word_boundary_pattern(pattern)  [@lru_cache]
      → DetectionResult(tier=2, confidence=0.6, needs_healing=True)
  [on miss] → tier3.detect_by_parent_inference(task, parent_type)
      → PARENT_CHILD_MAP.get(parent_type)
      → registry.get_primary_gid(inferred_type)
      → DetectionResult(tier=3, confidence=0.8, needs_healing=True)
  [all miss] → _make_unknown_result(task)
      → DetectionResult(tier=5, confidence=0.0, needs_healing=True)
```

**Async path with structure inspection**:
```
Task + AsanaClient
  → facade.detect_entity_type_async(task, client, allow_structure_inspection=True)
  → tier1._detect_tier1_project_membership_async(task, client)
      → get_workspace_registry().lookup_or_discover_async(project_gid, client)
      → [triggers discovery if GID not in static registry]
      → DetectionResult(tier=1) on hit
  [on miss] → detect_entity_type(task, parent_type)  [Tiers 2-3]
  [on UNKNOWN and allow_structure_inspection=True]
      → _get_cached_detection(task.gid, cache)  [CacheEntry.DETECTION lookup]
      → [on cache hit] return cached DetectionResult
      → [on cache miss] tier4.detect_by_structure_inspection(task, client)
          → client.tasks.subtasks_async(task.gid).collect()
          → subtask_names & BUSINESS_INDICATORS  ["contacts", "units", "location"]
          → subtask_names & UNIT_INDICATORS       ["offers", "processes"]
          → DetectionResult(tier=4, confidence=0.9, needs_healing=True) or None
      → [Tier 4 success] _cache_detection_result(task, result, cache)
          → CacheEntry(key=task.gid, entry_type=DETECTION, ttl=_detection_cache_ttl())
          → version = task.modified_at or datetime.now(UTC)
```

**Dict convenience path** (for pre-hydration callers):
```
detect_entity_type_from_dict(data: dict)
  → Task.model_validate(data)  [lazy import to avoid circular deps]
  → detect_entity_type(task).entity_type.value
  → str (e.g., "business") or None on validation failure
```

### Public API Surface

Functions consumed outside `detection/`:

| Export | Consumers |
|---|---|
| `detect_entity_type` | `hydration.py`, `cascade_view.py`, `cascading.py`, `business.py` (via `identify_holder_type`) |
| `detect_entity_type_async` | `hydration.py` |
| `detect_entity_type_from_dict` | `task_ttl.py`, `task_cache.py`, `dataframe_view.py` |
| `identify_holder_type` | `business.py:Business._identify_holder`, `unit.py:Unit._identify_holder` |

### Test Coverage

| File | Tests | Scope |
|---|---|---|
| `tests/unit/models/business/test_detection.py` | 50 | Unit tests: tier chain, edge cases, process detection, async Tier 1 with lazy discovery (`TestAsyncTier1WithLazyDiscovery`, `TestDetectEntityTypeAsyncWithLazyDiscovery`) |
| `tests/unit/detection/test_detection_cache.py` | 26 | Cache integration: `_get_cached_detection`, `_cache_detection_result`, TTL expiry, UNKNOWN not cached, degradation on cache errors |
| `tests/integration/test_detection.py` | 28 | Integration: full tier chain across registered + unregistered projects, async Tier 4 with mocked API |

Total: **104 tests**. No separate "adversarial" test file exists; adversarial/edge-case coverage lives in `TestEdgeCases` (lines 635-688 of unit test file) and within the cache test class. The census source description ("adversarial tests") referred to this inline adversarial coverage in the unit test, not a separate file.

---

## Boundaries and Failure Modes

### What This Feature Does NOT Do

- Does **not** mutate the task — detection is read-only; healing writes are performed by the persistence layer
- Does **not** detect entity type from Asana custom fields (the old Tier 0 / `EntityDetector` architecture was abandoned; the runbook is stale)
- Does **not** perform batch detection — callers invoke single-task functions in a loop; no `detect_batch()` function exists
- Does **not** fallback to Tier 4 on the sync path — `detect_entity_type()` ends at Tier 5 UNKNOWN; callers that want structure inspection must use `detect_entity_type_async(allow_structure_inspection=True)`
- Does **not** cache Tiers 1-3 results — the cache layer wraps Tier 4 exclusively
- Does **not** cache UNKNOWN results — per FR-CACHE-006 (`_cache_detection_result` returns early on `EntityType.UNKNOWN`)

### Known Failure Modes and Scars

| Failure Mode | Evidence | Recovery |
|---|---|---|
| **Entity collision via name normalization** (SCAR-001) | Entity/holder class lacked `PRIMARY_PROJECT_GID`; caused Tier 1 miss and downstream collision | Tier 1 now primary; ADR-0101 requires `PRIMARY_PROJECT_GID` on all entities |
| **Sync-in-async context** (SCAR-009) | Tests missing `ASANA_WORKSPACE_GID` triggered sync auto-detect in wrong async context | Lazy-load pattern; never call sync auto-detect from async callers |
| **Lambda init-time settings failure** (SCAR-CW-001 layer 4) | `get_settings()` at module-level caused HTTP 400 on Lambda cold start; Extension HTTP listener not ready at import time | `@functools.cache` on `_detection_cache_ttl()` defers settings resolution to first call (`facade.py:78-86`) |
| **Stale runbook** | `docs/runbooks/RUNBOOK-detection-troubleshooting.md` references `EntityDetector`, `Tier 0: Custom Field`, 5-tier numbering offset from current architecture | Do not use runbook for current-state troubleshooting |
| **Tier 4 returns `None`** | Structure inspection finds no indicator subtasks → returns `None` (not `DetectionResult`) | Caller falls through to Tier 5 UNKNOWN |
| **Cache degradation** | `CACHE_TRANSIENT_ERRORS` caught in both `_get_cached_detection` and `_cache_detection_result` | Detection proceeds normally — cache errors are logged and swallowed |

### Error Return Paths

- `detect_entity_type()` **never raises** — returns `DetectionResult(UNKNOWN)` on all misses
- `detect_entity_type_async()` **never raises** — same guarantee; Tier 4 returns `None` on no match
- `detect_entity_type_from_dict()` catches `ImportError`, `ValidationError`, `KeyError`, `AttributeError` — returns `None`
- `_get_cached_detection()` catches `CACHE_TRANSIENT_ERRORS` — returns `None`
- `_cache_detection_result()` catches `CACHE_TRANSIENT_ERRORS` — logs warning, does not re-raise

### Configuration Boundaries

| Setting | Env Var | Default | Scope |
|---|---|---|---|
| Detection cache TTL | `ASANA_CACHE_TTL_DETECTION` | 300s (matches task cache, per FR-VERSION-003) | Tier 4 results only |
| `allow_structure_inspection` | Code-level flag on `detect_entity_type_async()` | `False` | Enables Tier 4 |

Invalid `EntityType` string in a cached `DetectionResult` will raise `ValueError` at deserialization in `_get_cached_detection` — caught by `CACHE_TRANSIENT_ERRORS`.

### Interaction Points With Adjacent Features

- **`models/business/registry.py`** (`WorkspaceProjectRegistry.lookup_or_discover_async`): The async Tier 1 mechanism. If discovery fails, async Tier 1 returns `None` and the chain falls through. The `WorkspaceProjectRegistry` internals (how discovery enumerates workspace projects) are not traced in this document — see architecture.md knowledge gap.
- **`models/business/patterns.py`** (`PatternSpec`, `get_pattern_config`, `get_pattern_priority`): Tier 2 delegates pattern ordering and word-boundary configuration to this module. The priority ordering rationale (why `CONTACT_HOLDER` comes before `UNIT_HOLDER`) is not documented in source code.
- **`persistence/` layer**: The `needs_healing=True` flag on Tiers 2-5 results signals to the persistence layer that the task should be moved to its `expected_project_gid`. Detection does not initiate healing.
- **`cache/models/entry.py`**: The `EntryType.DETECTION` enum value scopes cached detection results separately from task and DataFrame cache entries.

### Knowledge Gaps (Remaining)

1. **`WorkspaceProjectRegistry` internals**: The async Tier 1 discovery mechanism (`lookup_or_discover_async`) — how it enumerates workspace projects and populates the static registry — is not traced.
2. **Tier 2 priority ordering rationale**: `get_pattern_priority()` in `patterns.py` defines a fixed order; no comment explains why entity types are ordered as they are.
3. **Runbook accuracy**: `docs/runbooks/RUNBOOK-detection-troubleshooting.md` references a `Tier 0 (Custom Field)` and `EntityDetector` class that do not exist in the current codebase. It is stale and unsafe for current-state troubleshooting.

```metadata
source_files_read:
  - src/autom8_asana/models/business/detection/facade.py
  - src/autom8_asana/models/business/detection/types.py
  - src/autom8_asana/models/business/detection/config.py
  - src/autom8_asana/models/business/detection/tier1.py
  - src/autom8_asana/models/business/detection/tier2.py
  - src/autom8_asana/models/business/detection/tier3.py
  - src/autom8_asana/models/business/detection/tier4.py
  - .know/architecture.md
  - .know/scar-tissue.md
  - tests/unit/models/business/test_detection.py
  - tests/unit/detection/test_detection_cache.py
  - tests/integration/test_detection.py
  - docs/runbooks/RUNBOOK-detection-troubleshooting.md
  - src/autom8_asana/models/business/patterns.py (partial)
  - src/autom8_asana/models/business/business.py (partial)
  - src/autom8_asana/models/business/unit.py (partial)
  - src/autom8_asana/models/business/hydration.py (partial)
test_counts:
  unit_detection: 50
  unit_cache: 26
  integration: 28
  total: 104
decision_references:
  - ADR-0094 (async detection, Tier 4)
  - ADR-0101 (ProjectTypeRegistry as sole Tier 1 source)
  - ADR-0109 (lazy workspace discovery on first unregistered GID)
  - ADR-0117 (word-boundary matching for Tier 2)
  - ADR-0119 (identify_holder_type consolidation)
  - PRD-CACHE-PERF-DETECTION (Tier 4 caching contract)
  - TDD-DETECTION (tier chain spec)
  - TDD-WORKSPACE-PROJECT-REGISTRY (async Tier 1 spec)
scar_references:
  - SCAR-001 (entity collision, motivates Tier 1 primacy)
  - SCAR-009 (sync-in-async context)
  - SCAR-CW-001 layer 4 (init-time settings, motivates lazy-load in facade)
changes_from_prior_version:
  - source_hash updated c213958 → 8980bcd7
  - lazy-load refactor (SCAR-CW-001 layer 4) now explicitly documented with code location
  - async Tier 1 (ADR-0109 WorkspaceProjectRegistry) fully traced and documented
  - detect_entity_type_async cache behavior documented with full sub-flow
  - EntityTypeInfo as single source of truth for NAME_PATTERNS/PARENT_CHILD_MAP documented
  - PatternSpec/patterns.py Tier 2 dependency surfaced
  - "adversarial tests" clarified — inline edge-case coverage in unit test, not a separate file
  - Runbook staleness re-confirmed and documented in boundaries
  - Consumer inventory expanded (task_ttl.py, task_cache.py, dataframe_view.py, cascading.py, cascade_view.py)
  - Configuration table added (ASANA_CACHE_TTL_DETECTION)
  - Error return paths documented per function
```
