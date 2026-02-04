# TDD: Unified CacheEntry Hierarchy

**Status**: Draft
**Author**: Architect (Claude)
**Date**: 2026-02-04
**Sprint**: S4 (Cache Consolidation)
**Task**: S4-001

---

## 1. Overview

### 1.1 Problem Statement

The cache subsystem has two separate `CacheEntry` classes and a flat `EntryType` enum that has grown to 15 members covering fundamentally different caching domains:

1. **`cache/models/entry.py::CacheEntry`** -- Frozen dataclass for versioned entity caching (tasks, sections, users, custom fields, stories, subtasks, dependencies, detections, GID enumerations). Used by Redis/S3 backends, tiered provider, client base class, and dataframe builders. Carries `entry_type: EntryType`, `version: datetime`, `project_gid: str | None`, and `metadata: dict`.

2. **`cache/integration/dataframe_cache.py::CacheEntry`** -- Mutable dataclass for DataFrame caching. Carries `project_gid: str`, `entity_type: str`, `dataframe: pl.DataFrame`, `watermark: datetime`, `schema_version: str`, and `build_quality: BuildQuality | None`. Completely different fields, different lifetime, different storage tiers (memory + progressive vs. Redis + S3).

The problems:

- **Naming collision**: Two unrelated classes named `CacheEntry` in the same package. Import disambiguation requires full module paths or aliases. The DataFrame `CacheEntry` shadows the versioned `CacheEntry` in any module that needs both.

- **Overloaded EntryType enum**: 15 members spanning four conceptual domains (task relationships, entity lookups, dataframe builds, detection results). A `match` statement on `EntryType` must handle all 15 cases even when only 5 are relevant. The enum cannot carry domain-specific metadata (e.g., "does this type have `modified_at`?") without a parallel lookup table.

- **Type-unsafe field access**: `project_gid` is `str | None` on the versioned `CacheEntry` because only DATAFRAME entries use it. `metadata` is `dict[str, Any]` carrying `schema_version`, `completeness_level`, and `opt_fields_used` without type safety. Consumers must know which entry types populate which metadata keys.

- **Serialization fragility**: Redis and S3 backends manually reconstruct `CacheEntry` from JSON dicts, passing `entry_type` as a positional discriminator but ignoring type-specific validation. A DATAFRAME entry deserialized without `project_gid` silently produces an invalid object.

### 1.2 Goals

1. Replace the flat `CacheEntry` + `EntryType` enum with a polymorphic hierarchy using a common base class and typed subclasses.
2. Provide type-safe field access: `project_gid` only on entries that require it, `schema_version` as a first-class field rather than metadata, `build_quality` only on DataFrame entries.
3. Resolve the naming collision between the two `CacheEntry` classes.
4. Introduce a serialization format with a `_type` discriminator that enables round-trip fidelity.
5. Maintain backward compatibility for all ~40 source import sites and ~45 test import sites.
6. Ensure `FreshnessPolicy.evaluate()` continues to work with any entry subclass.

### 1.3 Non-Goals

- Merging the versioned cache path (Redis/S3) with the DataFrame cache path (memory/progressive). These are architecturally distinct and should remain so.
- Changing TTL resolution logic or the `FreshnessPolicy` algorithm.
- Migrating persisted cache data. Existing Redis/S3 entries without `_type` will be treated as legacy and deserialized using the current logic.

### 1.4 Constraints

- Python 3.11+ (per `pyproject.toml`).
- Frozen dataclasses for thread safety (existing invariant).
- Must not break `dataclasses.replace()` usage in `TieredCacheProvider._promote_entry()`.
- Must not introduce circular imports between `cache/models/`, `cache/backends/`, and `cache/integration/`.
- The `cache/entry.py` shim must continue to work for backward compatibility.

---

## 2. Current State Analysis

### 2.1 EntryType Usage by Domain

| Domain | EntryType Members | Count | Typical Usage |
|--------|------------------|-------|---------------|
| Task relationships | TASK, SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS | 6 | `clients/base.py`, `cache/providers/unified.py`, `cache/integration/loader.py` |
| Entity lookups | PROJECT, SECTION, USER, CUSTOM_FIELD | 4 | `clients/projects.py`, `clients/sections.py`, `clients/users.py`, `clients/custom_fields.py` |
| DataFrame builds | DATAFRAME, PROJECT_SECTIONS, GID_ENUMERATION | 3 | `dataframes/cache_integration.py`, `dataframes/builders/parallel_fetch.py` |
| Detection | DETECTION | 1 | `models/business/detection/facade.py` |
| Insights | INSIGHTS | 1 | External integration |

### 2.2 CacheEntry Construction Sites (Versioned)

| Location | EntryType Used | Key Observations |
|----------|---------------|------------------|
| `clients/base.py:160` | Parameterized | Generic `_cache_set()` for all client types |
| `clients/sections.py:326` | SECTION | Batch section cache on list fetch |
| `cache/providers/unified.py:424,496` | TASK | Task-specific with hierarchy metadata |
| `cache/integration/loader.py:97,290` | Parameterized | Generic load/warm operations |
| `cache/integration/stories.py:114` | STORIES | Stories-specific |
| `cache/integration/autom8_adapter.py:287,381` | TASK | Adapter for external consumers |
| `cache/integration/staleness_coordinator.py:245` | Parameterized | Reconstructed from stale check |
| `cache/backends/redis.py:324` | Parameterized | Deserialized from Redis hash |
| `cache/backends/s3.py:374` | Parameterized | Deserialized from S3 object |
| `dataframes/cache_integration.py:331,389` | DATAFRAME | DataFrame-specific with project_gid |
| `dataframes/builders/task_cache.py:283` | TASK | Task cache for builder |
| `dataframes/builders/parallel_fetch.py:313,486` | PROJECT_SECTIONS, GID_ENUMERATION | Builder-specific lookup caching |
| `models/business/detection/facade.py:157` | DETECTION | Detection result caching |

### 2.3 The Two CacheEntry Problem

```
cache/models/entry.py::CacheEntry          cache/integration/dataframe_cache.py::CacheEntry
+---------------------------+              +---------------------------+
| key: str                  |              | project_gid: str          |
| data: dict[str, Any]      |              | entity_type: str          |
| entry_type: EntryType     |              | dataframe: pl.DataFrame   |
| version: datetime         |              | watermark: datetime       |
| cached_at: datetime       |              | created_at: datetime      |
| ttl: int | None           |              | schema_version: str       |
| project_gid: str | None   |              | row_count: int (computed)  |
| metadata: dict[str, Any]  |              | build_quality: Any        |
| freshness_stamp: ... | None|              +---------------------------+
+---------------------------+
```

These share zero fields. They are not polymorphically related. The naming collision is the only connection.

---

## 3. Proposed Design

### 3.1 Decision: Rename, Do Not Merge

The two `CacheEntry` classes serve fundamentally different purposes with zero field overlap. Merging them into a single hierarchy would be a forced abstraction that adds complexity without value.

**Instead:**
1. Rename the DataFrame class to `DataFrameCacheEntry` (in place, in `cache/integration/dataframe_cache.py`).
2. Restructure the versioned `CacheEntry` into a hierarchy with typed subclasses.
3. Keep `EntryType` as a discriminator but group it into domain enums.

### 3.2 Versioned CacheEntry Hierarchy

```
CacheEntry (base, frozen dataclass)
|
+-- EntityCacheEntry        # For single-entity lookups (TASK, PROJECT, SECTION, USER, CUSTOM_FIELD)
|   +-- key: str
|   +-- entity_gid: str     # Alias for key (semantic clarity)
|
+-- RelationshipCacheEntry  # For relationship lists (SUBTASKS, DEPENDENCIES, DEPENDENTS, STORIES, ATTACHMENTS)
|   +-- parent_gid: str     # The entity these relationships belong to
|   +-- relationship_count: int  # len(data) for overflow checks
|
+-- DataFrameMetaCacheEntry # For dataframe-related lookups (DATAFRAME, PROJECT_SECTIONS, GID_ENUMERATION)
|   +-- project_gid: str    # Required (not Optional)
|
+-- DetectionCacheEntry     # For detection results (DETECTION)
|   +-- task_gid: str       # The task this detection is for
|   +-- detection_type: str  # "unit", "offer", etc.
```

### 3.3 Base CacheEntry Definition

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from autom8_asana.cache.models.freshness_stamp import FreshnessStamp


class EntryType(str, Enum):
    """Cache entry type discriminator.

    Retained for backward compatibility and serialization.
    New code should use isinstance() checks on CacheEntry subclasses.
    """
    # Entity lookups
    TASK = "task"
    PROJECT = "project"
    SECTION = "section"
    USER = "user"
    CUSTOM_FIELD = "custom_field"

    # Relationship lists
    SUBTASKS = "subtasks"
    DEPENDENCIES = "dependencies"
    DEPENDENTS = "dependents"
    STORIES = "stories"
    ATTACHMENTS = "attachments"

    # DataFrame-related
    DATAFRAME = "dataframe"
    PROJECT_SECTIONS = "project_sections"
    GID_ENUMERATION = "gid_enumeration"

    # Domain-specific
    DETECTION = "detection"
    INSIGHTS = "insights"


@dataclass(frozen=True)
class CacheEntry:
    """Base cache entry for all versioned cache entries.

    Common fields shared by all entry types. Subclasses add
    domain-specific fields with type safety.

    This base class remains directly constructible for backward
    compatibility. New code should prefer typed subclasses.
    """

    key: str
    data: dict[str, Any]
    entry_type: EntryType
    version: datetime
    cached_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ttl: int | None = 300
    project_gid: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    freshness_stamp: FreshnessStamp | None = None

    # Registry of subclass discriminators for deserialization
    _type_registry: ClassVar[dict[str, type[CacheEntry]]] = {}

    def __init_subclass__(cls, entry_types: tuple[EntryType, ...] = (), **kwargs: Any) -> None:
        """Register subclass for deserialization dispatch."""
        super().__init_subclass__(**kwargs)
        for et in entry_types:
            CacheEntry._type_registry[et.value] = cls

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if entry has exceeded its TTL."""
        if self.ttl is None:
            return False
        now = now or datetime.now(UTC)
        cached_at = self.cached_at
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        elapsed = (now - cached_at).total_seconds()
        return elapsed > self.ttl

    def is_current(self, current_version: datetime | str) -> bool:
        """Check if cached version matches or is newer than current."""
        if isinstance(current_version, str):
            current_version = _parse_datetime(current_version)
        cached_version = self.version
        if isinstance(cached_version, str):
            cached_version = _parse_datetime(cached_version)
        if cached_version.tzinfo is None:
            cached_version = cached_version.replace(tzinfo=UTC)
        if current_version.tzinfo is None:
            current_version = current_version.replace(tzinfo=UTC)
        return cached_version >= current_version

    def is_stale(self, current_version: datetime | str) -> bool:
        """Check if entry is stale compared to current version."""
        return not self.is_current(current_version)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict with _type discriminator."""
        result = {
            "_type": self.entry_type.value,
            "_class": type(self).__name__,
            "key": self.key,
            "data": self.data,
            "entry_type": self.entry_type.value,
            "version": self.version.isoformat(),
            "cached_at": self.cached_at.isoformat(),
            "ttl": self.ttl,
            "project_gid": self.project_gid,
            "metadata": self.metadata,
        }
        if self.freshness_stamp is not None:
            result["freshness_stamp"] = {
                "last_verified_at": self.freshness_stamp.last_verified_at.isoformat(),
                "source": self.freshness_stamp.source.value,
                "staleness_hint": self.freshness_stamp.staleness_hint,
            }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Deserialize from dict, dispatching to correct subclass.

        If _type is present and a subclass is registered for it,
        delegates to the subclass. Otherwise constructs base CacheEntry
        (backward compatibility for legacy serialized data).
        """
        entry_type_str = data.get("_type") or data.get("entry_type")
        target_cls = cls._type_registry.get(entry_type_str, cls) if entry_type_str else cls
        # Delegate to subclass from_dict if it defines one
        if target_cls is not cls and hasattr(target_cls, "_from_dict_impl"):
            return target_cls._from_dict_impl(data)
        # Base CacheEntry construction (legacy path)
        return _deserialize_base(data)
```

### 3.4 Subclass Definitions

```python
@dataclass(frozen=True)
class EntityCacheEntry(
    CacheEntry,
    entry_types=(
        EntryType.TASK, EntryType.PROJECT, EntryType.SECTION,
        EntryType.USER, EntryType.CUSTOM_FIELD,
    ),
):
    """Cache entry for single Asana entity lookups.

    Provides semantic alias for the entity GID and supports
    completeness tracking via typed fields rather than metadata dict.
    """
    completeness_level: str | None = None  # "minimal", "standard", "full"
    opt_fields: tuple[str, ...] | None = None

    @property
    def entity_gid(self) -> str:
        """Semantic alias for key."""
        return self.key

    @property
    def has_modified_at(self) -> bool:
        """Whether this entity type carries modified_at for version comparison."""
        return self.entry_type in (EntryType.TASK, EntryType.PROJECT)


@dataclass(frozen=True)
class RelationshipCacheEntry(
    CacheEntry,
    entry_types=(
        EntryType.SUBTASKS, EntryType.DEPENDENCIES,
        EntryType.DEPENDENTS, EntryType.STORIES,
        EntryType.ATTACHMENTS,
    ),
):
    """Cache entry for relationship lists (subtasks, dependencies, etc.).

    Carries the parent entity GID and the relationship count for
    overflow threshold checks via OverflowSettings.
    """
    parent_gid: str | None = None  # Defaults to key
    relationship_count: int = 0

    def __post_init__(self) -> None:
        """Compute relationship_count from data if not provided."""
        if self.relationship_count == 0 and isinstance(self.data, dict):
            items = self.data.get("data", self.data)
            if isinstance(items, list):
                object.__setattr__(self, "relationship_count", len(items))

    @property
    def effective_parent_gid(self) -> str:
        """Parent GID (falls back to key)."""
        return self.parent_gid or self.key


@dataclass(frozen=True)
class DataFrameMetaCacheEntry(
    CacheEntry,
    entry_types=(
        EntryType.DATAFRAME, EntryType.PROJECT_SECTIONS,
        EntryType.GID_ENUMERATION,
    ),
):
    """Cache entry for DataFrame-related metadata lookups.

    project_gid is required (not Optional) since all DataFrame
    operations are scoped to a project.

    Note: This is NOT the DataFrame cache entry (which holds a
    pl.DataFrame). This caches metadata about DataFrames in the
    versioned Redis/S3 tier.
    """
    # project_gid is inherited from base but we enforce it
    schema_version: str | None = None

    def __post_init__(self) -> None:
        """Validate project_gid is set for DataFrame entries."""
        if self.project_gid is None:
            raise ValueError(
                f"project_gid is required for {self.entry_type.value} entries"
            )


@dataclass(frozen=True)
class DetectionCacheEntry(
    CacheEntry,
    entry_types=(EntryType.DETECTION,),
):
    """Cache entry for business detection results.

    Scoped to a task and a detection type (unit, offer, etc.).
    """
    detection_type: str | None = None

    @property
    def task_gid(self) -> str:
        """Semantic alias for key."""
        return self.key
```

### 3.5 DataFrame Cache Entry Rename

In `cache/integration/dataframe_cache.py`:

```python
# BEFORE
@dataclass
class CacheEntry:
    project_gid: str
    entity_type: str
    ...

# AFTER
@dataclass
class DataFrameCacheEntry:
    """DataFrame cache entry for memory/progressive tier storage.

    Distinct from CacheEntry (versioned Redis/S3 cache). This holds
    an actual pl.DataFrame with watermark-based freshness tracking.
    """
    project_gid: str
    entity_type: str
    dataframe: pl.DataFrame
    watermark: datetime
    created_at: datetime
    schema_version: str
    row_count: int = field(init=False)
    build_quality: Any = None

    def __post_init__(self) -> None:
        self.row_count = len(self.dataframe)
    ...

# Backward compatibility alias
CacheEntry = DataFrameCacheEntry  # Deprecated: use DataFrameCacheEntry
```

---

## 4. Serialization Format

### 4.1 JSON Structure with _type Discriminator

```json
{
    "_type": "task",
    "_class": "EntityCacheEntry",
    "key": "1234567890",
    "data": {"gid": "1234567890", "name": "Task"},
    "entry_type": "task",
    "version": "2026-01-15T10:00:00+00:00",
    "cached_at": "2026-02-04T12:00:00+00:00",
    "ttl": 300,
    "project_gid": null,
    "metadata": {},
    "completeness_level": "standard",
    "opt_fields": ["gid", "name", "custom_fields"],
    "freshness_stamp": {
        "last_verified_at": "2026-02-04T12:00:00+00:00",
        "source": "api_fetch",
        "staleness_hint": null
    }
}
```

### 4.2 Deserialization Strategy

```
1. Read _type field from JSON dict
2. Look up registered subclass in CacheEntry._type_registry
3. If found: construct subclass with type-specific fields
4. If not found: construct base CacheEntry (legacy compatibility)
5. Ignore unknown fields (forward compatibility)
```

### 4.3 Backend Integration

Redis and S3 backends currently construct `CacheEntry` directly. The change:

```python
# BEFORE (redis.py:324, s3.py:374)
return CacheEntry(
    key=key,
    data=entry_data,
    entry_type=entry_type,
    version=version,
    ...
)

# AFTER
return CacheEntry.from_dict({
    "_type": entry_type.value,
    "key": key,
    "data": entry_data,
    "version": version.isoformat(),
    ...
})
```

For the initial implementation, both old-style direct construction and new-style `from_dict` will work. Direct construction produces the base `CacheEntry`; `from_dict` produces the correct subclass if registered.

---

## 5. Migration Strategy

### 5.1 Phase 1: Non-Breaking Foundation (This Sprint)

1. Add subclass definitions to `cache/models/entry.py` below existing `CacheEntry`.
2. Add `to_dict()` and `from_dict()` to base `CacheEntry`.
3. Add `__init_subclass__` registry mechanism.
4. Rename `CacheEntry` to `DataFrameCacheEntry` in `cache/integration/dataframe_cache.py` with alias.
5. Update `cache/dataframe/tiers/memory.py` and `cache/dataframe/tiers/progressive.py` type hints.

**Zero import changes required.** All 40+ source imports and 45+ test imports continue to work because:
- `CacheEntry` base class is still directly constructible with all original fields.
- `EntryType` enum is unchanged.
- The `cache/entry.py` shim redirects to `cache/models/entry.py` which still exports both.
- DataFrame `CacheEntry` alias preserves backward compatibility.

### 5.2 Phase 2: Gradual Adoption (Next Sprints)

1. Update construction sites to use typed subclasses where the `EntryType` is known at call time.
2. Update `isinstance()` checks to use subclass types instead of `entry.entry_type == EntryType.TASK`.
3. Move completeness metadata from `metadata: dict` to `EntityCacheEntry.completeness_level` field.
4. Update Redis/S3 deserialization to use `CacheEntry.from_dict()`.

### 5.3 Phase 3: Deprecation Cleanup (Future)

1. Add `DeprecationWarning` to base `CacheEntry` constructor when used with entry types that have registered subclasses.
2. Migrate remaining direct `CacheEntry(...)` construction to subclass constructors.
3. Remove the `CacheEntry = DataFrameCacheEntry` alias after all internal consumers are updated.

### 5.4 Import Compatibility Matrix

| Import Path | Phase 1 | Phase 2 | Phase 3 |
|-------------|---------|---------|---------|
| `from autom8_asana.cache.entry import CacheEntry` | Works (shim) | Works | Works |
| `from autom8_asana.cache.models.entry import CacheEntry` | Works (canonical) | Works | Works |
| `from autom8_asana.cache import CacheEntry` | Works (re-export) | Works | Works |
| `from autom8_asana.cache.entry import EntryType` | Works | Works | Works |
| `from autom8_asana.cache.models.entry import EntityCacheEntry` | NEW | Works | Works |
| `from autom8_asana.cache import EntityCacheEntry` | NEW | Works | Works |
| `from autom8_asana.cache.integration.dataframe_cache import CacheEntry` | Works (alias) | Works (deprecated) | Removed |
| `from autom8_asana.cache.integration.dataframe_cache import DataFrameCacheEntry` | NEW | Works | Works |

---

## 6. FreshnessPolicy Integration

`FreshnessPolicy.evaluate()` accepts `CacheEntry` (the base type). Because all subclasses inherit from `CacheEntry`, no changes are needed to the policy itself.

```python
# FreshnessPolicy._get_ttl currently reads entry.metadata and entry.ttl
# Both are on the base class. No change needed.

# The entity_type parameter is already explicit:
policy.evaluate(entry, entity_type="unit")  # Works for any CacheEntry subclass
```

The `evaluate_stamp()` method takes a `FreshnessStamp` directly and is unaffected.

---

## 7. OverflowSettings Integration

`OverflowSettings.get_threshold()` and `should_cache()` take `EntryType` as parameter, not `CacheEntry`. No changes needed.

For `RelationshipCacheEntry`, the `relationship_count` field enables a cleaner check:

```python
# BEFORE
if not settings.should_cache(EntryType.SUBTASKS, len(subtask_list)):
    return

# AFTER (Phase 2, optional improvement)
entry = RelationshipCacheEntry(...)
if not settings.should_cache(entry.entry_type, entry.relationship_count):
    return
```

---

## 8. Sequence Diagrams

### 8.1 Cache Write with Typed Entry

```
Client.get_task()
    |
    v
Client._cache_set(gid, data, EntryType.TASK, ttl)
    |
    v
CacheEntry(key=gid, data=data, entry_type=TASK, version=...)
    |  [Phase 1: base CacheEntry, works unchanged]
    |  [Phase 2: EntityCacheEntry with completeness_level]
    v
TieredCacheProvider.set_versioned(key, entry)
    |
    +---> RedisCacheProvider.set_versioned(key, entry)
    |         [Serializes entry.to_dict() to Redis hash]
    |
    +---> S3CacheProvider.set_versioned(key, entry)
              [Serializes entry.to_dict() to S3 object]
```

### 8.2 Cache Read with Typed Deserialization

```
TieredCacheProvider.get_versioned(key, EntryType.TASK)
    |
    v
RedisCacheProvider.get_versioned(key, EntryType.TASK)
    |
    v
[Redis hash -> dict]
    |
    v
CacheEntry.from_dict(dict)
    |
    v
[_type_registry lookup: "task" -> EntityCacheEntry]
    |
    v
EntityCacheEntry(key=..., data=..., entry_type=TASK, ...)
    |
    v
FreshnessPolicy.evaluate(entry)  # Works: EntityCacheEntry is-a CacheEntry
    |
    v
Return to caller
```

---

## 9. ADRs

### ADR-S4-001: Rename Instead of Merge for DataFrame CacheEntry

**Context**: The codebase has two `CacheEntry` classes with zero field overlap. One option is to create a common ancestor; another is to rename.

**Decision**: Rename `cache/integration/dataframe_cache.py::CacheEntry` to `DataFrameCacheEntry` with backward-compatible alias.

**Rationale**: A shared base class would be a forced abstraction. The two classes have different mutability (frozen vs. mutable), different storage backends (Redis/S3 vs. memory/progressive), different lifetime semantics (TTL-based vs. watermark-based), and zero shared fields. A common ancestor would carry no useful methods or fields, serving only to satisfy a naming convention. The rename resolves the collision directly.

**Consequences**:
- (+) No forced abstraction; each class evolves independently.
- (+) `DataFrameCacheEntry` name makes the distinction explicit in code.
- (+) Backward-compatible alias means zero immediate migration cost.
- (-) Two unrelated cache entry types remain (but they genuinely are unrelated).

**Status**: Proposed

---

### ADR-S4-002: Subclass Registry via __init_subclass__ for Deserialization

**Context**: Redis and S3 backends must reconstruct CacheEntry objects from JSON. With a hierarchy, the backend needs to know which subclass to construct.

**Decision**: Use `__init_subclass__` with an `entry_types` parameter to build a `_type_registry` mapping `EntryType.value -> subclass`. Deserialization uses `CacheEntry.from_dict()` which dispatches based on the `_type` field.

**Alternatives Considered**:
- **Manual registry (dict literal)**: Simpler but requires maintaining the mapping in two places (class definition and registry dict). Risks drift.
- **Factory function with match/case**: Explicit but verbose. Requires updating the factory every time a subclass is added.
- **`__init_subclass__` auto-registration**: Declarative, co-located with class definition, no separate registry to maintain.

**Rationale**: `__init_subclass__` is idiomatic Python 3.6+ and keeps the registration co-located with the class definition. A new subclass automatically registers by declaring `entry_types=(EntryType.FOO,)` in its class statement. The pattern is well-established in serialization libraries (Pydantic, attrs, marshmallow).

**Consequences**:
- (+) Zero-maintenance registry: adding a subclass auto-registers it.
- (+) Deserialization dispatch is O(1) dict lookup.
- (-) Slightly magical: registration happens at class definition time.
- (-) All subclasses must be imported before `from_dict()` is called (solved by importing from `cache/models/entry.py` which defines them all).

**Status**: Proposed

---

### ADR-S4-003: Retain EntryType Enum for Backward Compatibility

**Context**: With subclasses, the `EntryType` enum is partially redundant. We could remove it and use `isinstance()` checks instead.

**Decision**: Retain `EntryType` as-is. It continues to serve as the serialization discriminator, API method parameter (e.g., `get_versioned(key, entry_type)`), and logging/metrics tag.

**Alternatives Considered**:
- **Remove EntryType, use isinstance()**: Breaking change to ~60 call sites. Backend APIs would need to accept `type[CacheEntry]` instead of `EntryType`. Serialization discriminator would need a replacement.
- **Replace with domain-specific enums**: `EntityType`, `RelationshipType`, etc. More precise but doubles the number of enum imports and creates a migration burden.

**Rationale**: `EntryType` is deeply embedded in the codebase (60+ usage sites across source and tests). Removing it would be a large-scope change with no functional benefit -- subclasses and `EntryType` can coexist, with subclasses providing type safety and `EntryType` providing string-based discrimination. Over time, `isinstance()` checks can replace `entry.entry_type == EntryType.TASK` checks incrementally.

**Consequences**:
- (+) Zero breaking changes to existing code.
- (+) Serialization format uses familiar `EntryType.value` strings.
- (-) Mild redundancy between `isinstance(entry, EntityCacheEntry)` and `entry.entry_type == EntryType.TASK`.
- This redundancy resolves naturally as Phase 2 migration progresses.

**Status**: Proposed

---

### ADR-S4-004: Phased Migration with No Big Bang

**Context**: ~85 import sites reference `CacheEntry` or `EntryType`. A big-bang migration risks regressions and conflicts with concurrent development.

**Decision**: Three-phase migration. Phase 1 is purely additive (new subclasses, rename with alias). Phase 2 is gradual adoption. Phase 3 is deprecation cleanup.

**Rationale**: Phase 1 delivers the hierarchy without touching any existing consumer code. This is the critical constraint: the team can ship Phase 1 in one sprint with full backward compatibility, then adopt subclasses incrementally as files are touched for other reasons. No "migration sprint" required.

**Consequences**:
- (+) Zero risk Phase 1 -- purely additive code.
- (+) Phase 2 can be spread across sprints as opportunistic refactoring.
- (-) Coexistence period where both base `CacheEntry(...)` and `EntityCacheEntry(...)` are used for the same purpose.

**Status**: Proposed

---

## 10. Test Specifications

### 10.1 Unit Tests for Hierarchy

| Test | Description | Location |
|------|-------------|----------|
| `test_entity_cache_entry_construction` | Construct `EntityCacheEntry` for each entity type, verify fields | `tests/unit/cache/test_entry_hierarchy.py` |
| `test_relationship_cache_entry_count` | Verify `relationship_count` auto-computed from data | same |
| `test_dataframe_meta_entry_requires_project_gid` | `DataFrameMetaCacheEntry` raises `ValueError` without project_gid | same |
| `test_detection_cache_entry_task_gid` | `task_gid` property returns key | same |
| `test_subclass_isinstance` | All subclasses are `isinstance(entry, CacheEntry)` | same |
| `test_base_methods_on_subclasses` | `is_expired()`, `is_current()`, `is_stale()` work on all subclasses | same |
| `test_replace_preserves_subclass` | `dataclasses.replace(entry, ttl=600)` returns same subclass type | same |
| `test_frozen_immutability` | Assignment to field on any subclass raises `FrozenInstanceError` | same |

### 10.2 Serialization Tests

| Test | Description | Location |
|------|-------------|----------|
| `test_to_dict_includes_type_discriminator` | `entry.to_dict()["_type"]` matches `entry_type.value` | `tests/unit/cache/test_entry_serialization.py` |
| `test_from_dict_dispatches_to_subclass` | `CacheEntry.from_dict({"_type": "task", ...})` returns `EntityCacheEntry` | same |
| `test_from_dict_legacy_no_type_field` | Dict without `_type` produces base `CacheEntry` | same |
| `test_round_trip_all_subclasses` | `from_dict(entry.to_dict()) == entry` for all subclass types | same |
| `test_freshness_stamp_survives_round_trip` | FreshnessStamp serialized and deserialized correctly | same |
| `test_unknown_fields_ignored` | Extra fields in dict do not raise | same |

### 10.3 Backward Compatibility Tests

| Test | Description | Location |
|------|-------------|----------|
| `test_base_cache_entry_still_constructible` | `CacheEntry(key=..., entry_type=EntryType.TASK, ...)` still works | `tests/unit/cache/test_entry_compat.py` |
| `test_shim_import_path` | `from autom8_asana.cache.entry import CacheEntry` works | same |
| `test_package_import_path` | `from autom8_asana.cache import CacheEntry` works | same |
| `test_dataframe_cache_entry_alias` | `from autom8_asana.cache.integration.dataframe_cache import CacheEntry` works | same |
| `test_entrytype_enum_unchanged` | All 15 EntryType members present with original values | same |
| `test_freshness_policy_accepts_subclasses` | `FreshnessPolicy.evaluate(entity_entry)` works | same |

### 10.4 Integration Tests

| Test | Description | Location |
|------|-------------|----------|
| `test_redis_round_trip_subclass` | Write EntityCacheEntry to Redis, read back, verify type | `tests/unit/cache/test_redis_entry_hierarchy.py` |
| `test_s3_round_trip_subclass` | Write EntityCacheEntry to S3, read back, verify type | `tests/unit/cache/test_s3_entry_hierarchy.py` |
| `test_tiered_promotion_preserves_subclass` | `_promote_entry` on EntityCacheEntry returns EntityCacheEntry | `tests/unit/cache/test_tiered_entry_hierarchy.py` |

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `dataclasses.replace()` does not preserve subclass type | Low | High | Python dataclasses.replace() creates instance of the same type as input. Verified in CPython 3.11+. Add explicit test. |
| `__init_subclass__` registration order dependency | Low | Medium | All subclasses are defined in the same module (`cache/models/entry.py`), imported atomically. No cross-module import timing issues. |
| DataFrame `CacheEntry` alias causes confusion | Medium | Low | Alias emits no warning in Phase 1. Phase 2 adds `DeprecationWarning`. Phase 3 removes alias. |
| Serialized data in Redis lacks `_type` field | Certain | Low | `from_dict()` falls back to base `CacheEntry` when `_type` is absent. Existing entries work without migration. New writes include `_type`. |
| Performance regression from subclass dispatch | Low | Low | `from_dict()` dispatch is a single dict lookup. Construction cost is identical (frozen dataclass). |
| Concurrent PR conflicts during Phase 1 | Medium | Medium | Phase 1 only adds new code to `cache/models/entry.py` and a rename+alias in `dataframe_cache.py`. No modifications to existing function signatures. Conflict surface is minimal. |

---

## 12. File Manifest

### New Files

| File | Purpose |
|------|---------|
| `tests/unit/cache/test_entry_hierarchy.py` | Unit tests for subclass construction and behavior |
| `tests/unit/cache/test_entry_serialization.py` | Serialization round-trip tests |
| `tests/unit/cache/test_entry_compat.py` | Backward compatibility verification |

### Modified Files

| File | Change |
|------|--------|
| `src/autom8_asana/cache/models/entry.py` | Add subclass definitions, `to_dict()`, `from_dict()`, `__init_subclass__` |
| `src/autom8_asana/cache/integration/dataframe_cache.py` | Rename class to `DataFrameCacheEntry`, add `CacheEntry` alias |
| `src/autom8_asana/cache/models/__init__.py` | Re-export new subclass names |
| `src/autom8_asana/cache/__init__.py` | Re-export new subclass names |

### Unchanged Files (Phase 1)

All ~40 source files and ~45 test files that import `CacheEntry` or `EntryType` remain unchanged in Phase 1. No import modifications required.

---

## 13. Attestation

| Artifact | Absolute Path | Verified |
|----------|--------------|----------|
| TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unified-cacheentry-hierarchy.md` | Written |
| Current CacheEntry (versioned) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/entry.py` | Read |
| Current CacheEntry (DataFrame) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/integration/dataframe_cache.py` | Read |
| Shim module | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/entry.py` | Read |
| FreshnessStamp | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/freshness_stamp.py` | Read |
| FreshnessPolicy | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/policies/freshness_policy.py` | Read |
| BuildResult/BuildQuality | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/build_result.py` | Read |
| TieredCacheProvider | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/providers/tiered.py` | Read |
| CacheSettings | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/models/settings.py` | Read |
| Redis backend | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/redis.py` | Read (deserialization) |
| S3 backend | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/backends/s3.py` | Read (deserialization) |
| Client base | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/base.py` | Read (construction pattern) |
