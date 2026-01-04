# TDD: Cache SDK Primitive Generalization

**TDD ID**: TDD-CACHE-SDK-PRIMITIVES-001
**Version**: 1.0
**Date**: 2026-01-04
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: N/A (Technical initiative from SDK generalization spike)

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Spike Findings Summary](#spike-findings-summary)
4. [Goals and Non-Goals](#goals-and-non-goals)
5. [Proposed Architecture](#proposed-architecture)
6. [Component Designs](#component-designs)
7. [API Contracts](#api-contracts)
8. [Migration Strategy](#migration-strategy)
9. [Test Strategy](#test-strategy)
10. [Implementation Phases](#implementation-phases)
11. [Risk Assessment](#risk-assessment)
12. [ADRs](#adrs)
13. [Success Criteria](#success-criteria)

---

## Overview

This TDD defines the extraction of three reusable primitives from autom8_asana's cache implementation into the autom8y-cache SDK. These primitives were identified through spike analysis as generalizable patterns that can benefit any satellite application requiring hierarchical data caching with completeness tracking and configurable freshness semantics.

### Solution Summary

**Extract to autom8y-cache SDK**:
1. **HierarchyTracker** - Generic parent-child relationship tracking with bidirectional traversal
2. **FreshnessMode.IMMEDIATE** - Extend Freshness enum with "return cached without validation" semantics
3. **CompletenessUpgrade Protocol** - Optional callback hook for transparent fetch-on-miss

**Design Philosophy**: These primitives are application-agnostic. They know nothing about Asana, tasks, or any specific domain model. Satellite applications compose these primitives with their domain-specific logic.

---

## Problem Statement

### Current State

The autom8_asana satellite has developed battle-tested caching patterns that are tightly coupled to Asana-specific concepts:

| Component | Location | Domain Coupling |
|-----------|----------|-----------------|
| `HierarchyIndex` | `autom8_asana/cache/hierarchy.py` | References "task", uses `task.get("gid")` |
| `FreshnessMode.IMMEDIATE` | `autom8_asana/cache/freshness_coordinator.py` | Only available in satellite |
| `get_with_upgrade_async()` | `autom8_asana/cache/unified.py` | Tightly coupled to `TasksClient` |

The autom8y-cache SDK currently provides:
- `Freshness` enum with STRICT and EVENTUAL modes only
- `CompletenessLevel` enum (UNKNOWN, MINIMAL, STANDARD, FULL)
- `CacheProvider` protocol for storage backends
- `CacheEntry` dataclass with version tracking

### Gap Analysis

| SDK Capability | autom8_asana Need | Status |
|----------------|-------------------|--------|
| Freshness modes | STRICT, EVENTUAL, IMMEDIATE | Missing IMMEDIATE |
| Hierarchy tracking | Parent-child with bidirectional traversal | Missing entirely |
| Completeness upgrade | Transparent fetch when entry is insufficient | Missing protocol |
| Field-level completeness | MINIMAL/STANDARD/FULL detection | Available (needs registration) |

### Why This Matters

Future satellites (data-platform, integrations) will need the same patterns. Extracting now prevents duplication and establishes SDK-level abstractions that all satellites can build upon.

---

## Spike Findings Summary

Spike analysis identified three primitives for extraction:

### 1. HierarchyIndex (Now: HierarchyTracker)

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy.py`

**Size**: ~200 lines

**Characteristics**:
- Thread-safe (uses `threading.Lock`)
- Bidirectional mapping (parent -> children, child -> parent)
- Ancestor chain traversal with max_depth
- Descendant BFS traversal for cascade invalidation
- No Asana-specific knowledge (only uses `gid` and `parent.gid`)

**Generalization Requirements**:
- Replace "gid" with generic "id"
- Replace "task" references with "entity"
- Add configurable ID extraction function

### 2. FreshnessMode.IMMEDIATE

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/freshness_coordinator.py`

**Size**: ~3 lines (enum addition)

**Semantics**:
- Return cached data immediately without any validation
- No TTL check, no API call, no version comparison
- Used when caller has already validated freshness at a higher level

**Current Usage in autom8_asana**:
- `UnifiedTaskStore.get_async()` with IMMEDIATE mode for pre-validated lookups
- `ProjectDataFrameBuilder` uses IMMEDIATE after hierarchy freshness validation
- `DataFrameView.get_rows_async()` uses IMMEDIATE for batch lookups

### 3. CompletenessUpgrade Protocol

**Location**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/unified.py` (methods `upgrade_async`, `get_with_upgrade_async`)

**Pattern**:
```python
async def get_with_upgrade_async(
    gid: str,
    required_level: CompletenessLevel,
    freshness: FreshnessMode | None = None,
    tasks_client: "TasksClient | None" = None,
) -> dict[str, Any] | None:
    # 1. Try cache first
    result = await self.get_async(gid, freshness, required_level)
    if result is not None:
        return result

    # 2. Upgrade if we have a client (callback)
    if tasks_client is not None:
        return await self.upgrade_async(gid, required_level, tasks_client)

    return None
```

**Generalization Requirements**:
- Define protocol for upgrade callback
- Make it optional (SDK doesn't mandate upgrading)
- Satellite provides implementation

---

## Goals and Non-Goals

### Goals

1. **G1**: Extract HierarchyTracker as a domain-agnostic SDK primitive
2. **G2**: Add FreshnessMode.IMMEDIATE to SDK's Freshness enum
3. **G3**: Define CompletenessUpgrade protocol for transparent fetch-on-miss
4. **G4**: Provide migration path for autom8_asana with zero breaking changes
5. **G5**: Maintain thread-safety guarantees in SDK primitives

### Non-Goals

1. **NG1**: Not extracting FreshnessCoordinator (batch staleness checks are Asana-specific)
2. **NG2**: Not extracting UnifiedTaskStore (orchestration layer is satellite-specific)
3. **NG3**: Not changing existing CacheProvider protocol
4. **NG4**: No new features - extraction and generalization only

---

## Proposed Architecture

### SDK Module Structure

```
autom8y-cache/src/autom8y_cache/
├── __init__.py              # Add new exports
├── freshness.py             # Extend Freshness enum with IMMEDIATE
├── hierarchy.py             # NEW: HierarchyTracker
├── completeness.py          # Existing + upgrade protocol
├── protocols/
│   ├── __init__.py
│   ├── cache.py             # Existing CacheProvider
│   └── upgrade.py           # NEW: CompletenessUpgrader protocol
└── ...
```

### Component Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                     autom8y-cache SDK                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ HierarchyTracker│  │   Freshness  │  │CompletenessUpgrader│ │
│  │                 │  │              │  │    (Protocol)      │ │
│  │ - register()    │  │ - STRICT     │  │                    │ │
│  │ - get_parent()  │  │ - EVENTUAL   │  │ - upgrade_async()  │ │
│  │ - get_children()│  │ - IMMEDIATE  │  │                    │ │
│  │ - get_ancestors│  │              │  │                    │ │
│  │ - get_descendants│ │              │  │                    │ │
│  └─────────────────┘  └──────────────┘  └───────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ imports/uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   autom8_asana (satellite)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   UnifiedTaskStore                       │   │
│  │                                                          │   │
│  │  Composes:                                               │   │
│  │  - HierarchyTracker (from SDK)                          │   │
│  │  - CompletenessUpgrader (implements with TasksClient)   │   │
│  │  - CacheProvider (from SDK)                             │   │
│  │  - FreshnessCoordinator (satellite-specific)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Designs

### 6.1 HierarchyTracker

**Module**: `autom8y_cache/hierarchy.py`

**Design Principles**:
- Generic ID type (string by default, configurable)
- Pluggable ID extraction for registering entities
- Thread-safe with reentrant lock
- No domain knowledge (no "task", "gid", "Asana")

```python
"""Hierarchy tracking for parent-child entity relationships.

Provides bidirectional parent-child mappings for efficient traversal
in both directions. Used for cascade invalidation and ancestor chain
resolution in hierarchical data models.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")  # Entity type
K = TypeVar("K", bound=str)  # ID type (defaults to str)


class HierarchyTracker(Generic[K]):
    """Thread-safe bidirectional hierarchy index.

    Maintains parent-child relationships for entities, enabling:
    - Ancestor chain traversal (for inheritance/cascade resolution)
    - Descendant enumeration (for cascade invalidation)
    - Root detection (entities with no parent)

    Thread Safety:
        All operations are protected by a threading.RLock to ensure
        thread-safe concurrent access with reentrancy support.

    Example:
        >>> tracker = HierarchyTracker[str](
        ...     id_extractor=lambda e: e["id"],
        ...     parent_id_extractor=lambda e: e.get("parent", {}).get("id"),
        ... )
        >>> tracker.register({"id": "child-1", "parent": {"id": "parent-1"}})
        >>> tracker.get_parent_id("child-1")
        'parent-1'
        >>> tracker.get_children_ids("parent-1")
        {'child-1'}
    """

    def __init__(
        self,
        id_extractor: Callable[[Any], K | None] = lambda e: e.get("id"),
        parent_id_extractor: Callable[[Any], K | None] = lambda e: (
            e.get("parent", {}).get("id") if isinstance(e.get("parent"), dict) else None
        ),
    ) -> None:
        """Initialize hierarchy tracker.

        Args:
            id_extractor: Function to extract entity ID from entity dict.
                Defaults to e["id"].
            parent_id_extractor: Function to extract parent ID from entity dict.
                Defaults to e["parent"]["id"] with safe nested access.
        """
        self._id_extractor = id_extractor
        self._parent_id_extractor = parent_id_extractor

        # Map: id -> parent_id (or None for root entities)
        self._parent_map: dict[K, K | None] = {}
        # Map: id -> set of child ids
        self._children_map: dict[K, set[K]] = {}
        # Lock for thread safety (reentrant for nested calls)
        self._lock = threading.RLock()

    def register(self, entity: Any, entity_id: K | None = None) -> None:
        """Register entity and update relationships.

        Args:
            entity: Entity dict to register.
            entity_id: Optional explicit ID (overrides id_extractor).

        Raises:
            ValueError: If entity ID cannot be determined.
        """
        # Implementation follows autom8_asana pattern
        ...

    def get_parent_id(self, entity_id: K) -> K | None:
        """Get immediate parent ID.

        Args:
            entity_id: Entity ID to look up.

        Returns:
            Parent ID if exists, None otherwise.
        """
        with self._lock:
            return self._parent_map.get(entity_id)

    def get_children_ids(self, entity_id: K) -> set[K]:
        """Get immediate children IDs.

        Args:
            entity_id: Entity ID to look up.

        Returns:
            Set of child IDs (may be empty, always returns new set).
        """
        with self._lock:
            children = self._children_map.get(entity_id)
            return set(children) if children else set()

    def get_ancestor_chain(
        self,
        entity_id: K,
        max_depth: int = 10,
    ) -> list[K]:
        """Get ancestor IDs from immediate parent to root.

        Args:
            entity_id: Starting entity ID.
            max_depth: Maximum chain depth (default 10, prevents cycles).

        Returns:
            List of ancestor IDs from immediate parent to root.
            Empty list if entity has no parent or is not registered.
        """
        # Implementation follows autom8_asana pattern
        ...

    def get_descendant_ids(
        self,
        entity_id: K,
        max_depth: int | None = None,
    ) -> set[K]:
        """Get all descendant IDs via BFS traversal.

        Args:
            entity_id: Starting entity ID.
            max_depth: Maximum traversal depth. None for unlimited.

        Returns:
            Set of all descendant IDs (not including starting ID).
        """
        # Implementation follows autom8_asana pattern
        ...

    def get_root_id(self, entity_id: K) -> K | None:
        """Get root ID for this entity's hierarchy.

        Args:
            entity_id: Entity ID to find root for.

        Returns:
            Root ID, or None if entity not registered.
        """
        # Implementation follows autom8_asana pattern
        ...

    def contains(self, entity_id: K) -> bool:
        """Check if entity ID is registered."""
        with self._lock:
            return entity_id in self._parent_map

    def remove(self, entity_id: K) -> None:
        """Remove entity from tracker.

        Cleans up parent and child relationships.
        Note: Children become orphaned (their parent references unchanged).
        """
        # Implementation follows autom8_asana pattern
        ...

    def clear(self) -> None:
        """Clear all entries from tracker."""
        with self._lock:
            self._parent_map.clear()
            self._children_map.clear()

    def __len__(self) -> int:
        """Return number of registered entities."""
        with self._lock:
            return len(self._parent_map)

    def get_stats(self) -> dict[str, int]:
        """Get tracker statistics."""
        with self._lock:
            root_count = sum(
                1 for parent_id in self._parent_map.values() if parent_id is None
            )
            return {
                "entity_count": len(self._parent_map),
                "root_count": root_count,
                "children_map_size": len(self._children_map),
            }
```

### 6.2 Freshness Enum Extension

**Module**: `autom8y_cache/freshness.py`

**Change**: Add IMMEDIATE mode to existing Freshness enum.

```python
"""Cache freshness modes for controlling staleness validation.

This module defines the Freshness enum that controls how cache providers
validate entries against their source data versions.
"""

from __future__ import annotations

from enum import Enum


class Freshness(str, Enum):
    """Cache freshness modes for controlling staleness validation.

    STRICT: Always validate version against source before returning.
            Guarantees up-to-date data at cost of additional API call.

    EVENTUAL: Return cached data if within TTL without validation.
              Faster but may return slightly stale data.

    IMMEDIATE: Return cached data without any validation.
               No TTL check, no version comparison, no API call.
               Use when freshness has been pre-validated at a higher level
               (e.g., hierarchy root already checked).
    """

    STRICT = "strict"
    EVENTUAL = "eventual"
    IMMEDIATE = "immediate"
```

### 6.3 CompletenessUpgrader Protocol

**Module**: `autom8y_cache/protocols/upgrade.py`

**Design**: Protocol-based approach allows satellites to provide their own upgrade implementations.

```python
"""Completeness upgrade protocol for transparent fetch-on-miss.

Defines the protocol for upgrading cache entries to higher completeness
levels when the cached entry is insufficient for the requested operation.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from autom8y_cache.completeness import CompletenessLevel


@runtime_checkable
class CompletenessUpgrader(Protocol):
    """Protocol for upgrading cache entries to higher completeness levels.

    Satellites implement this protocol to provide domain-specific fetch
    logic for upgrading entries. The SDK cache layer calls this protocol
    when a cached entry exists but has insufficient completeness.

    Example (satellite implementation):
        class AsanaTaskUpgrader:
            def __init__(self, tasks_client: TasksClient):
                self.tasks_client = tasks_client

            async def upgrade_async(
                self,
                key: str,
                target_level: CompletenessLevel,
            ) -> dict[str, Any] | None:
                opt_fields = self._get_fields_for_level(target_level)
                return await self.tasks_client.get_async(
                    key, opt_fields=opt_fields, raw=True
                )

            def get_fields_for_level(
                self,
                level: CompletenessLevel,
            ) -> list[str]:
                return ASANA_LEVEL_FIELDS[level]
    """

    async def upgrade_async(
        self,
        key: str,
        target_level: CompletenessLevel,
    ) -> dict[str, Any] | None:
        """Fetch entity data at target completeness level.

        Args:
            key: Entity key/ID to fetch.
            target_level: Desired completeness level.

        Returns:
            Entity data dict if fetch succeeds, None otherwise.
            The returned data should be at or above target_level.
        """
        ...

    def get_fields_for_level(
        self,
        level: CompletenessLevel,
    ) -> list[str]:
        """Get field list for a completeness level.

        Used to determine which fields to request when fetching
        at a specific completeness level.

        Args:
            level: Completeness level to get fields for.

        Returns:
            List of field names to request.
        """
        ...
```

### 6.4 SDK __init__.py Updates

**Module**: `autom8y_cache/__init__.py`

Add new exports:

```python
# Hierarchy tracking
from .hierarchy import HierarchyTracker

# Upgrade protocol
from .protocols.upgrade import CompletenessUpgrader

# Update __all__
__all__ = [
    # ... existing exports ...
    # Hierarchy
    "HierarchyTracker",
    # Upgrade protocol
    "CompletenessUpgrader",
]
```

---

## API Contracts

### 7.1 HierarchyTracker Public API

| Method | Signature | Returns | Thread-Safe |
|--------|-----------|---------|-------------|
| `register` | `(entity: Any, entity_id: K \| None = None) -> None` | None | Yes |
| `get_parent_id` | `(entity_id: K) -> K \| None` | Parent ID or None | Yes |
| `get_children_ids` | `(entity_id: K) -> set[K]` | Set of child IDs | Yes |
| `get_ancestor_chain` | `(entity_id: K, max_depth: int = 10) -> list[K]` | Ordered ancestor IDs | Yes |
| `get_descendant_ids` | `(entity_id: K, max_depth: int \| None = None) -> set[K]` | Set of descendant IDs | Yes |
| `get_root_id` | `(entity_id: K) -> K \| None` | Root ID or None | Yes |
| `contains` | `(entity_id: K) -> bool` | True if registered | Yes |
| `remove` | `(entity_id: K) -> None` | None | Yes |
| `clear` | `() -> None` | None | Yes |
| `__len__` | `() -> int` | Entity count | Yes |
| `get_stats` | `() -> dict[str, int]` | Statistics dict | Yes |

### 7.2 Freshness Enum Values

| Value | String | Behavior |
|-------|--------|----------|
| `STRICT` | `"strict"` | Always validate version against source |
| `EVENTUAL` | `"eventual"` | Return cached if within TTL |
| `IMMEDIATE` | `"immediate"` | Return cached without any validation |

### 7.3 CompletenessUpgrader Protocol Methods

| Method | Signature | Returns | Async |
|--------|-----------|---------|-------|
| `upgrade_async` | `(key: str, target_level: CompletenessLevel) -> dict \| None` | Entity data or None | Yes |
| `get_fields_for_level` | `(level: CompletenessLevel) -> list[str]` | Field names | No |

---

## Migration Strategy

### 8.1 Backward Compatibility Guarantees

| Change | Compatibility | Notes |
|--------|---------------|-------|
| Add `Freshness.IMMEDIATE` | Additive | Existing code unaffected |
| Add `HierarchyTracker` | Additive | New module, no existing dependencies |
| Add `CompletenessUpgrader` | Additive | Protocol only, no required implementation |

### 8.2 autom8_asana Migration Checklist

```markdown
## Migration Tasks

### Phase 1: Import Updates (SDK v0.X.0)

- [ ] Update autom8y-cache dependency to version with new primitives
- [ ] Replace `HierarchyIndex` import with `HierarchyTracker` from SDK
- [ ] Replace `FreshnessMode.IMMEDIATE` with `Freshness.IMMEDIATE` from SDK
- [ ] Keep `FreshnessCoordinator` as satellite-specific (not extracted)

### Phase 2: HierarchyIndex -> HierarchyTracker

Location: `src/autom8_asana/cache/hierarchy.py`

- [ ] Delete local `HierarchyIndex` class
- [ ] Create `HierarchyTracker` instance with Asana-specific extractors:
  ```python
  from autom8y_cache import HierarchyTracker

  # Asana-specific configuration
  asana_hierarchy = HierarchyTracker[str](
      id_extractor=lambda task: task.get("gid"),
      parent_id_extractor=lambda task: (
          task.get("parent", {}).get("gid")
          if isinstance(task.get("parent"), dict) else None
      ),
  )
  ```
- [ ] Update `UnifiedTaskStore` to use `HierarchyTracker`
- [ ] Rename method calls: `get_parent_gid` -> `get_parent_id`, etc.

### Phase 3: Freshness Mode Migration

Location: `src/autom8_asana/cache/freshness_coordinator.py`

- [ ] Remove local `FreshnessMode` enum
- [ ] Import `Freshness` from SDK
- [ ] Find-replace `FreshnessMode.IMMEDIATE` -> `Freshness.IMMEDIATE`
- [ ] Find-replace `FreshnessMode.EVENTUAL` -> `Freshness.EVENTUAL`
- [ ] Find-replace `FreshnessMode.STRICT` -> `Freshness.STRICT`
- [ ] Update type hints throughout codebase

### Phase 4: CompletenessUpgrader Implementation

Location: `src/autom8_asana/cache/upgrader.py` (new file)

- [ ] Create `AsanaTaskUpgrader` implementing `CompletenessUpgrader`:
  ```python
  from autom8y_cache import CompletenessUpgrader, CompletenessLevel

  class AsanaTaskUpgrader:
      def __init__(self, tasks_client: TasksClient):
          self.tasks_client = tasks_client

      async def upgrade_async(
          self,
          key: str,
          target_level: CompletenessLevel,
      ) -> dict[str, Any] | None:
          opt_fields = self.get_fields_for_level(target_level)
          try:
              return await self.tasks_client.get_async(
                  key, opt_fields=opt_fields, raw=True
              )
          except Exception:
              return None

      def get_fields_for_level(self, level: CompletenessLevel) -> list[str]:
          from autom8_asana.cache.completeness import get_fields_for_level
          return get_fields_for_level(level)
  ```
- [ ] Update `UnifiedTaskStore` to accept optional `CompletenessUpgrader`
- [ ] Refactor `upgrade_async` and `get_with_upgrade_async` to use protocol

### Phase 5: Cleanup

- [ ] Delete deprecated local implementations
- [ ] Update `__all__` exports in `cache/__init__.py`
- [ ] Run full test suite
- [ ] Update documentation references
```

### 8.3 Breaking Change Assessment

| Change | Breaking? | Mitigation |
|--------|-----------|------------|
| Method rename `get_parent_gid` -> `get_parent_id` | Yes (internal) | Search-replace in satellite |
| Method rename `get_children_gids` -> `get_children_ids` | Yes (internal) | Search-replace in satellite |
| Method rename `get_descendant_gids` -> `get_descendant_ids` | Yes (internal) | Search-replace in satellite |
| `FreshnessMode` -> `Freshness` | Yes (internal) | Search-replace in satellite |
| `HierarchyIndex` -> `HierarchyTracker` | Yes (internal) | Delete local, use SDK |

All breaking changes are internal to autom8_asana. The SDK addition is purely additive and does not break any external consumers.

---

## Test Strategy

### 9.1 SDK Unit Tests

**Module**: `tests/test_hierarchy.py`

```python
"""Tests for HierarchyTracker."""

import pytest
import threading
from autom8y_cache import HierarchyTracker


class TestHierarchyTracker:
    """Unit tests for hierarchy tracking."""

    def test_register_entity_without_parent(self):
        """Root entities have no parent."""
        tracker = HierarchyTracker[str]()
        tracker.register({"id": "root-1"})

        assert tracker.contains("root-1")
        assert tracker.get_parent_id("root-1") is None
        assert tracker.get_ancestor_chain("root-1") == []

    def test_register_entity_with_parent(self):
        """Child entities reference parent."""
        tracker = HierarchyTracker[str]()
        tracker.register({"id": "parent-1"})
        tracker.register({"id": "child-1", "parent": {"id": "parent-1"}})

        assert tracker.get_parent_id("child-1") == "parent-1"
        assert "child-1" in tracker.get_children_ids("parent-1")

    def test_ancestor_chain_depth(self):
        """Ancestor chain respects max_depth."""
        tracker = HierarchyTracker[str]()
        # Build 5-level hierarchy
        for i in range(5):
            parent = {"id": f"level-{i-1}"} if i > 0 else None
            entity = {"id": f"level-{i}"}
            if parent:
                entity["parent"] = parent
            tracker.register(entity)

        # Full chain
        chain = tracker.get_ancestor_chain("level-4", max_depth=10)
        assert len(chain) == 4

        # Limited depth
        chain = tracker.get_ancestor_chain("level-4", max_depth=2)
        assert len(chain) == 2

    def test_descendant_bfs(self):
        """Descendants found via BFS traversal."""
        tracker = HierarchyTracker[str]()
        tracker.register({"id": "root"})
        tracker.register({"id": "child-1", "parent": {"id": "root"}})
        tracker.register({"id": "child-2", "parent": {"id": "root"}})
        tracker.register({"id": "grandchild-1", "parent": {"id": "child-1"}})

        descendants = tracker.get_descendant_ids("root")
        assert descendants == {"child-1", "child-2", "grandchild-1"}

    def test_thread_safety(self):
        """Concurrent access is thread-safe."""
        tracker = HierarchyTracker[str]()
        errors = []

        def register_batch(start: int, count: int):
            try:
                for i in range(start, start + count):
                    tracker.register({"id": f"entity-{i}"})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_batch, args=(i * 100, 100))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(tracker) == 1000

    def test_custom_extractors(self):
        """Custom ID extractors work correctly."""
        tracker = HierarchyTracker[str](
            id_extractor=lambda e: e.get("gid"),  # Asana-style
            parent_id_extractor=lambda e: e.get("parent", {}).get("gid"),
        )

        tracker.register({"gid": "task-1", "parent": {"gid": "task-0"}})
        assert tracker.get_parent_id("task-1") == "task-0"

    def test_remove_cleanup(self):
        """Remove cleans up relationships."""
        tracker = HierarchyTracker[str]()
        tracker.register({"id": "parent-1"})
        tracker.register({"id": "child-1", "parent": {"id": "parent-1"}})

        tracker.remove("child-1")

        assert not tracker.contains("child-1")
        assert "child-1" not in tracker.get_children_ids("parent-1")
```

**Module**: `tests/test_freshness.py`

```python
"""Tests for Freshness enum."""

from autom8y_cache import Freshness


class TestFreshness:
    """Unit tests for freshness modes."""

    def test_immediate_value(self):
        """IMMEDIATE has correct string value."""
        assert Freshness.IMMEDIATE.value == "immediate"

    def test_all_modes_present(self):
        """All three modes are available."""
        assert hasattr(Freshness, "STRICT")
        assert hasattr(Freshness, "EVENTUAL")
        assert hasattr(Freshness, "IMMEDIATE")

    def test_string_comparison(self):
        """Freshness can be compared to strings."""
        assert Freshness.IMMEDIATE == "immediate"
        assert Freshness.STRICT == "strict"
        assert Freshness.EVENTUAL == "eventual"
```

**Module**: `tests/test_upgrade_protocol.py`

```python
"""Tests for CompletenessUpgrader protocol."""

from autom8y_cache import CompletenessUpgrader, CompletenessLevel


class MockUpgrader:
    """Test implementation of CompletenessUpgrader."""

    async def upgrade_async(self, key: str, target_level: CompletenessLevel):
        return {"id": key, "name": f"Entity {key}"}

    def get_fields_for_level(self, level: CompletenessLevel) -> list[str]:
        return ["id", "name"] if level >= CompletenessLevel.STANDARD else ["id"]


class TestCompletenessUpgrader:
    """Tests for upgrade protocol."""

    def test_protocol_check(self):
        """MockUpgrader satisfies protocol."""
        upgrader = MockUpgrader()
        assert isinstance(upgrader, CompletenessUpgrader)

    async def test_upgrade_async_returns_data(self):
        """upgrade_async returns entity data."""
        upgrader = MockUpgrader()
        result = await upgrader.upgrade_async("key-1", CompletenessLevel.STANDARD)
        assert result == {"id": "key-1", "name": "Entity key-1"}

    def test_get_fields_for_level(self):
        """get_fields_for_level returns appropriate fields."""
        upgrader = MockUpgrader()
        minimal = upgrader.get_fields_for_level(CompletenessLevel.MINIMAL)
        standard = upgrader.get_fields_for_level(CompletenessLevel.STANDARD)

        assert minimal == ["id"]
        assert standard == ["id", "name"]
```

### 9.2 autom8_asana Integration Tests

After migration, verify:

```python
"""Integration tests for SDK primitive usage."""

import pytest
from autom8y_cache import HierarchyTracker, Freshness, CompletenessLevel

from autom8_asana.cache import UnifiedTaskStore


class TestSDKIntegration:
    """Verify SDK primitives work in autom8_asana context."""

    def test_hierarchy_tracker_with_asana_tasks(self):
        """HierarchyTracker handles Asana task structure."""
        tracker = HierarchyTracker[str](
            id_extractor=lambda t: t.get("gid"),
            parent_id_extractor=lambda t: t.get("parent", {}).get("gid"),
        )

        # Simulate Asana task hierarchy
        tracker.register({"gid": "business-1", "name": "Business"})
        tracker.register({
            "gid": "unit-1",
            "name": "Unit",
            "parent": {"gid": "business-1"},
        })

        assert tracker.get_parent_id("unit-1") == "business-1"

    async def test_unified_store_with_immediate_freshness(self, unified_store):
        """UnifiedTaskStore respects Freshness.IMMEDIATE."""
        # Pre-populate cache
        await unified_store.put_async({"gid": "task-1", "name": "Test"})

        # IMMEDIATE should return without validation
        result = await unified_store.get_async(
            "task-1",
            freshness=Freshness.IMMEDIATE,
        )

        assert result is not None
        assert result["name"] == "Test"
```

---

## Implementation Phases

### Phase 1: SDK Extension (1 day)

**Owner**: Platform team

1. Add `Freshness.IMMEDIATE` to `autom8y_cache/freshness.py`
2. Create `autom8y_cache/hierarchy.py` with `HierarchyTracker`
3. Create `autom8y_cache/protocols/upgrade.py` with `CompletenessUpgrader`
4. Update `autom8y_cache/__init__.py` exports
5. Add unit tests for all new components
6. Release SDK version with new primitives

**Deliverables**:
- [ ] `autom8y-cache` v0.X.0 with new primitives
- [ ] 100% test coverage for new modules
- [ ] Updated SDK documentation

### Phase 2: Satellite Migration (1 day)

**Owner**: autom8_asana team

1. Update dependency to new SDK version
2. Follow migration checklist (Section 8.2)
3. Run existing test suite (should pass without changes)
4. Delete deprecated local implementations
5. Update internal documentation

**Deliverables**:
- [ ] autom8_asana using SDK primitives
- [ ] No local `HierarchyIndex` or `FreshnessMode`
- [ ] All tests passing

### Phase 3: Validation (0.5 day)

**Owner**: QA

1. Run full autom8_asana test suite
2. Verify no regressions in cache behavior
3. Test IMMEDIATE mode in production-like scenarios
4. Validate hierarchy operations with real Asana data

**Deliverables**:
- [ ] QA sign-off
- [ ] Performance benchmarks (no regression)

---

## Risk Assessment

### Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Thread-safety regression | Low | High | Comprehensive concurrent tests |
| Breaking change missed | Low | Medium | Full test suite before/after |
| Performance regression | Low | Medium | Benchmark before migration |
| Generic API harder to use | Medium | Low | Provide helper factory functions |
| Migration incomplete | Low | Medium | Checklist with verification steps |

### Rollback Strategy

If issues discovered post-migration:

1. Revert autom8_asana to previous version
2. SDK primitives remain available (additive, non-breaking)
3. Fix issues in satellite code
4. Re-attempt migration

SDK release is safe - it only adds new exports, no existing functionality changed.

---

## ADRs

### ADR-001: Generic vs Asana-Specific Hierarchy Tracker

**Context**: Should `HierarchyTracker` be generic or Asana-specific?

**Decision**: Generic with pluggable extractors.

**Rationale**:
- Other satellites (data-platform) will need hierarchy tracking
- Asana-specific behavior achieved via configuration, not code
- Reduces SDK coupling to any specific domain
- Follows composition over inheritance principle

**Consequences**:
- Slightly more setup code in satellites
- Cleaner SDK with no domain knowledge
- Easier testing (no Asana mocks needed)

### ADR-002: Protocol vs Base Class for CompletenessUpgrader

**Context**: Should upgrade behavior be defined via Protocol or ABC?

**Decision**: Protocol (structural typing).

**Rationale**:
- Satellites may have existing upgrader classes they want to adapt
- Protocol allows duck typing without inheritance
- More flexible for testing (any matching object works)
- Follows Python 3.8+ best practices

**Consequences**:
- No shared implementation code in SDK
- Each satellite implements full upgrade logic
- Runtime `isinstance` checks work via `@runtime_checkable`

### ADR-003: Freshness.IMMEDIATE Semantics

**Context**: What exactly does IMMEDIATE mean?

**Decision**: Return cached data without any validation - no TTL check, no version comparison, no API call.

**Rationale**:
- Use case: Caller has already validated freshness at hierarchy level
- Avoids redundant checks when parent freshness implies child freshness
- Explicit opt-in (caller must request IMMEDIATE mode)

**Consequences**:
- May return stale data if misused
- Caller responsible for appropriate use
- Performance benefit for valid use cases

---

## Success Criteria

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| SDK primitives extracted | 3 | Count: HierarchyTracker, Freshness.IMMEDIATE, CompletenessUpgrader |
| Breaking changes in SDK | 0 | Existing consumers unchanged |
| Test coverage for new modules | 100% | pytest --cov |
| autom8_asana test pass rate | 100% | CI pipeline |

### Qualitative

| Criterion | Validation |
|-----------|------------|
| SDK primitives are domain-agnostic | No "task", "Asana", "gid" in SDK code |
| Migration path is clear | Checklist followed without ambiguity |
| Future satellites can use primitives | Code review by platform team |
| Documentation is complete | README and docstrings updated |

---

## Artifact Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| TDD Document | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-CACHE-SDK-PRIMITIVES-001.md` | Pending |

---

## Appendix A: Current HierarchyIndex Implementation Reference

The current implementation in autom8_asana to be generalized:

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/cache/hierarchy.py`

Key methods to preserve:
- `register(task, entity_type)` - Bidirectional relationship update
- `get_parent_gid(gid)` - Direct parent lookup
- `get_children_gids(gid)` - Direct children lookup
- `get_ancestor_chain(gid, max_depth)` - Upward traversal
- `get_descendant_gids(gid, max_depth)` - BFS downward traversal
- `get_root_gid(gid)` - Find hierarchy root
- `remove(gid)` - Cleanup relationships
- `get_stats()` - Observability

## Appendix B: Freshness Mode Usage in autom8_asana

Current usage patterns of `FreshnessMode.IMMEDIATE`:

```python
# UnifiedTaskStore.get_async - skip validation for pre-validated lookups
if mode == FreshnessMode.IMMEDIATE:
    self._stats["get_hits"] += 1
    return entry.data

# ProjectDataFrameBuilder - after hierarchy freshness check
freshness=FreshnessMode.IMMEDIATE  # Already validated at root level

# DataFrameView.get_rows_async - batch lookup with pre-validation
freshness=FreshnessMode.IMMEDIATE
```

## Appendix C: CompletenessUpgrade Pattern in autom8_asana

Current upgrade pattern to be abstracted:

```python
# UnifiedTaskStore.upgrade_async
async def upgrade_async(
    self,
    gid: str,
    target_level: CompletenessLevel,
    tasks_client: "TasksClient | None" = None,
) -> dict[str, Any] | None:
    opt_fields = get_fields_for_level(target_level)

    if tasks_client is None:
        return None

    task = await tasks_client.get_async(gid, opt_fields=opt_fields, raw=True)
    if task is None:
        return None

    await self.put_async(task, opt_fields=opt_fields)
    return task
```

This pattern becomes the `CompletenessUpgrader.upgrade_async` protocol method.
