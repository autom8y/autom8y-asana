# Hydration and Cache opt_fields Analysis

**Date:** 2025-12-23
**Status:** Discovery Complete
**Analyst:** Requirements Analyst Session

---

## Executive Summary

This analysis identifies three distinct `opt_fields` sets used across the codebase and documents the **critical gap** where `TasksClient._DETECTION_FIELDS` is **missing `parent.gid`**, which is required by the hydration traversal path. The analysis recommends a **Unified Standard Field Set** that can satisfy all use cases.

---

## 1. Opt_Fields Inventory

### 1.1 `_DETECTION_OPT_FIELDS` (hydration.py)

**Location:** `/src/autom8_asana/models/business/hydration.py:63-68`
**Purpose:** Minimal fields for entity type detection during initial fetch and upward traversal.

```python
_DETECTION_OPT_FIELDS: list[str] = [
    "memberships.project.gid",
    "memberships.project.name",
    "name",
    "parent.gid",
]
```

**Used by:**
- `hydrate_from_gid_async()` - Entry point fetch (line 303)
- `_traverse_upward_async()` - Parent traversal fetch (line 696)

### 1.2 `_BUSINESS_FULL_OPT_FIELDS` (hydration.py)

**Location:** `/src/autom8_asana/models/business/hydration.py:73-90`
**Purpose:** Full fields for Business entities including custom_fields for cascading.

```python
_BUSINESS_FULL_OPT_FIELDS: list[str] = [
    "memberships.project.gid",
    "memberships.project.name",
    "name",
    "parent.gid",
    # Custom fields for cascading (Office Phone, Company ID, etc.)
    "custom_fields",
    "custom_fields.name",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.display_value",
    "custom_fields.number_value",
    "custom_fields.text_value",
    "custom_fields.resource_subtype",
    "custom_fields.people_value",
]
```

**Used by:**
- `hydrate_from_gid_async()` - Re-fetch Business with full fields (line 343)
- `_traverse_upward_async()` - Re-fetch Business root with full fields (line 724)

### 1.3 `TasksClient._DETECTION_FIELDS` (tasks.py)

**Location:** `/src/autom8_asana/clients/tasks.py:644-660`
**Purpose:** Fields for entity type detection and field cascading in `subtasks_async()`.

```python
_DETECTION_FIELDS: list[str] = [
    # Detection fields
    "memberships.project.gid",
    "memberships.project.name",
    "name",
    # Custom fields for cascading
    "custom_fields",
    "custom_fields.name",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.display_value",
    "custom_fields.number_value",
    "custom_fields.text_value",
    "custom_fields.resource_subtype",
]
```

**Used by:**
- `subtasks_async()` when `include_detection_fields=True` (lines 708-715)
- Called by `Business._fetch_holders_async()` and `Unit._fetch_holders_async()`

---

## 2. Comparison Table

| Field | Detection (hydration) | Business Full | TasksClient Detection | Required For |
|-------|:--------------------:|:-------------:|:--------------------:|--------------|
| `memberships.project.gid` | Y | Y | Y | Tier 1 detection |
| `memberships.project.name` | Y | Y | Y | ProcessType detection |
| `name` | Y | Y | Y | Tier 2 detection, display |
| `parent.gid` | **Y** | Y | **N** | **Upward traversal** |
| `custom_fields` | N | Y | Y | Cascading |
| `custom_fields.name` | N | Y | Y | Field identification |
| `custom_fields.enum_value` | N | Y | Y | Single-select fields |
| `custom_fields.enum_value.name` | N | Y | Y | Enum display value |
| `custom_fields.multi_enum_values` | N | Y | Y | Multi-select fields |
| `custom_fields.multi_enum_values.name` | N | Y | Y | Multi-enum display |
| `custom_fields.display_value` | N | Y | Y | General display |
| `custom_fields.number_value` | N | Y | Y | Numeric fields |
| `custom_fields.text_value` | N | Y | Y | Text fields |
| `custom_fields.resource_subtype` | N | Y | Y | Field type |
| `custom_fields.people_value` | N | **Y** | **N** | **People fields** |

---

## 3. Critical Gaps Identified

### 3.1 **`parent.gid` Missing from TasksClient._DETECTION_FIELDS**

**Severity:** HIGH
**Impact:** Cache entries populated by `subtasks_async(include_detection_fields=True)` will **NOT** have `parent.gid`, which is required for:

1. **Upward traversal** in `_traverse_upward_async()` - requires `current.parent.gid` (line 676)
2. **Asana task relationship tracking** - parent-child hierarchy

**Current Behavior:**
- When `subtasks_async()` fetches children with detection fields, cached entries lack `parent.gid`
- Subsequent `get_async()` call returns cached data without `parent.gid`
- `hydrate_from_gid_async()` relies on `parent.gid` for traversal

**Risk:** If a task is fetched via `subtasks_async()` first (which populates cache), then later used for upward traversal via `get_async()` (which returns cached data), the traversal will fail with a `NoneType` error or incorrect behavior.

### 3.2 **`custom_fields.people_value` Missing from TasksClient._DETECTION_FIELDS**

**Severity:** MEDIUM
**Impact:** People field values (used for cascading Owner assignments) won't be available in cached entries from subtask fetches.

---

## 4. Cache Behavior Analysis

### 4.1 When Is TasksClient Cache Populated?

The cache is populated in `TasksClient.get_async()`:

```python
# Cache miss: fetch from API
params = self._build_opt_fields(opt_fields)
data = await self._http.get(f"/tasks/{task_gid}", params=params)

# Store in cache with entity-type TTL
ttl = self._resolve_entity_ttl(data)
self._cache_set(task_gid, data, EntryType.TASK, ttl=ttl)
```

**Key Observations:**
1. Cache stores **exactly what was returned by the API** with the requested `opt_fields`
2. **No normalization** - if you request fewer fields, fewer fields are cached
3. **No field validation** on cache retrieval - whatever is in cache is returned

### 4.2 When Is Cache Checked?

Cache is checked in `TasksClient.get_async()` **before** making any API call:

```python
# FR-CLIENT-001: Check cache first
cached_entry = self._cache_get(task_gid, EntryType.TASK)
if cached_entry is not None:
    # Cache hit - return cached data
    data = cached_entry.data
    if raw:
        return data
    task = Task.model_validate(data)
    task._client = self._client
    return task
```

**Critical Issue:** Cache returns **ignore the `opt_fields` parameter** - the cached data is returned regardless of what fields were requested.

### 4.3 Cache Is NOT Populated by subtasks_async()

`subtasks_async()` does NOT populate the individual task cache. It returns tasks with specified fields but does not cache them. Only direct `get_async()` calls populate the cache.

---

## 5. Detection Field Requirements

### 5.1 Tier 1: Project Membership Detection

**Required Fields:**
- `memberships.project.gid` - Primary key for registry lookup
- `memberships.project.name` - For ProcessType detection via project name matching

**Location:** `/src/autom8_asana/models/business/detection/tier1.py`

### 5.2 Tier 2: Name Pattern Detection

**Required Fields:**
- `name` - Task name for pattern matching

**Location:** `/src/autom8_asana/models/business/detection/tier2.py`

### 5.3 Tier 3: Parent Inference Detection

**Required Fields:**
- None directly, but relies on parent_type being known from prior detection

**Location:** `/src/autom8_asana/models/business/detection/tier3.py`

### 5.4 Tier 4: Structure Inspection Detection

**Required Fields (for subtasks):**
- `name` - To match structure indicators ("contacts", "units", "offers", etc.)

**Location:** `/src/autom8_asana/models/business/detection/tier4.py`

### 5.5 Full Detection + Hydration

**Required Fields:**
- All Tier 1-4 fields
- `parent.gid` - For upward traversal
- `custom_fields.*` - For field cascading

---

## 6. Recommended Standard Field Set

### 6.1 Unified Field Set

A single field set that satisfies **all use cases**:

```python
STANDARD_TASK_OPT_FIELDS: list[str] = [
    # Core identification
    "name",
    "parent.gid",

    # Detection (Tier 1)
    "memberships.project.gid",
    "memberships.project.name",

    # Custom fields (cascading)
    "custom_fields",
    "custom_fields.name",
    "custom_fields.enum_value",
    "custom_fields.enum_value.name",
    "custom_fields.multi_enum_values",
    "custom_fields.multi_enum_values.name",
    "custom_fields.display_value",
    "custom_fields.number_value",
    "custom_fields.text_value",
    "custom_fields.resource_subtype",
    "custom_fields.people_value",
]
```

**Total Fields:** 15 (vs current max of 14)

### 6.2 Why Unified?

1. **Consistency:** All cached entries have the same field coverage
2. **Predictability:** Any code path can rely on fields being present
3. **Cache Reuse:** First fetch populates with all needed fields
4. **API Efficiency:** One consistent request pattern
5. **Maintenance:** Single source of truth for field requirements

---

## 7. Normalization Strategy Recommendation

### 7.1 Immediate Fix (Blocking)

**Add `parent.gid` to `TasksClient._DETECTION_FIELDS`:**

```python
_DETECTION_FIELDS: list[str] = [
    # Detection fields
    "memberships.project.gid",
    "memberships.project.name",
    "name",
    "parent.gid",  # ADDED: Required for upward traversal
    # ... rest unchanged
]
```

This is the minimum change to prevent traversal failures.

### 7.2 Strategic Normalization (Recommended)

**Option A: Centralized Field Registry**
- Define `STANDARD_TASK_OPT_FIELDS` in a central location (e.g., `autom8_asana/models/business/fields.py`)
- Import and use everywhere fields are needed
- Single source of truth

**Option B: Field Inheritance**
- `_DETECTION_OPT_FIELDS` = base detection fields
- `_BUSINESS_FULL_OPT_FIELDS` = `_DETECTION_OPT_FIELDS` + custom fields
- `TasksClient._DETECTION_FIELDS` = `_DETECTION_OPT_FIELDS` + custom fields

### 7.3 Cache Strategy Consideration

Current cache behavior stores exactly what was fetched. Two options:

1. **Status Quo:** Accept that different fetch patterns cache different field sets. Risk: Field mismatch on cache hit.

2. **Normalized Storage:** Always request full field set on `get_async()`, ensuring cache entries are complete. Cost: Larger responses.

---

## 8. Open Questions

1. **Should cache be field-aware?** When `get_async(gid, opt_fields=X)` is called, should we check if cached entry has all fields in X?

2. **Performance impact of unified fields?** The additional `parent.gid` field is minimal, but full custom_fields adds significant response size.

3. **Should subtasks_async() populate individual task cache?** Currently it does not, which may be intentional for performance.

---

## 9. Appendix: Code References

### File Locations

| File | Purpose |
|------|---------|
| `/src/autom8_asana/models/business/hydration.py` | Hydration orchestration, opt_fields definitions |
| `/src/autom8_asana/clients/tasks.py` | TasksClient, cache integration, _DETECTION_FIELDS |
| `/src/autom8_asana/clients/base.py` | BaseClient with cache helpers |
| `/src/autom8_asana/models/business/detection/` | Detection tier implementations |
| `/src/autom8_asana/models/business/business.py` | Business._fetch_holders_async |
| `/src/autom8_asana/models/business/unit.py` | Unit._fetch_holders_async |

### Related Documentation

- `ADR-0094`: Detection field requirements
- `ADR-0101`: ProcessType detection via project name
- `TDD-HYDRATION`: Hydration algorithm specification
- `PRD-CACHE-PERF-DETECTION`: Detection cache integration
