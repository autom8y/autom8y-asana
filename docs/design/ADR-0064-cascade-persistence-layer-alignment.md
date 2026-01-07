---
artifact_id: ADR-0064
title: "ADR: Cascade Field Resolution - Persistence Layer Alignment"
created_at: "2026-01-07T00:00:00Z"
author: architect
status: proposed
complexity: SYSTEM
supersedes: null
related_adrs:
  - ADR-hierarchy-registration-architecture
  - ADR-0063-platform-concurrency-extraction
related_tdds:
  - TDD-unit-cascade-resolution-fix
  - TDD-DATAFRAME-CACHE-001
  - TDD-UNIFIED-CACHE-001
schema_version: "1.0"
---

# ADR-0064: Cascade Field Resolution - Persistence Layer Alignment

## Status

PROPOSED

## Context

We have been debugging cascade field resolution failures for Unit DataFrames across 5+ commits and multiple sessions. The symptom is consistent: the demo script at `/Users/tomtenuta/Code/autom8-s2s-demo/examples/05_gid_lookup.py` returns **0/3 matches** for Unit entity resolution by phone+vertical, when it should return 2/3.

### Problem Statement

Unit DataFrames have NULL values in `office_phone` and `vertical` columns. These are cascade fields that should resolve from the parent Business task. The `GidLookupIndex.from_dataframe()` filters out NULL rows, resulting in an empty lookup index and 0 matches for all queries.

### Previous Fix Attempts (All Failed)

| Commit | Fix | Result |
|--------|-----|--------|
| d5ebb83 | Changed `_populate_store_with_tasks()` to use `put_batch_async(warm_hierarchy=True)` | Still 0/3 |
| 064f3a4 | Bumped `UNIT_SCHEMA.version` from "1.0.0" to "1.1.0" | Still 0/3 |
| 9876257 | Added per-entity schema version lookup from SchemaRegistry | Still 0/3 |

### Why Previous Fixes Failed

The fixes addressed symptoms but not the root cause. The fundamental problem is **architectural**: we have multiple cache/persistence layers that evolved independently and lack coordinated schema version tracking. The resume capability in SectionPersistence loads stale S3 parquets that were written with NULL cascade fields, bypassing all version checks.

## Decision

We will implement a **Unified Version Envelope** pattern that wraps all persistence artifacts with consistent version metadata, and add a **schema version gate** to the SectionManifest to prevent resume from incompatible builds.

### Key Decisions

1. **Add schema_version to SectionManifest** - The manifest must track which schema version was used to build the sections, enabling version-aware resume decisions.

2. **Invalidate stale manifests on schema bump** - When resuming, compare manifest schema version against current SchemaRegistry version. If mismatched, treat as fresh build (discard stale sections).

3. **Single source of truth for schema version** - SchemaRegistry is the canonical source. All persistence layers must query it, not maintain independent version tracking.

4. **Preserve DataFrameCache version checking** - The existing per-entity version validation in DataFrameCache is correct and should remain.

## Architecture Analysis

### Current State: Five Cache/Persistence Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CACHE/PERSISTENCE LAYER INVENTORY                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│   UnifiedTaskStore   │     │   DataFrameCache     │     │ SectionPersistence│
│   (cache/unified.py) │     │ (cache/dataframe_    │     │ (dataframes/      │
│                      │     │  cache.py)           │     │  section_         │
│ Purpose: Task data   │     │ Purpose: Final       │     │  persistence.py)  │
│ with hierarchy       │     │ DataFrames with      │     │ Purpose: Section  │
│                      │     │ tiered storage       │     │ parquets + resume │
│ Version Tracking:    │     │ Version Tracking:    │     │ Version Tracking: │
│ - completeness level │     │ - Per-entity lookup  │     │ - NONE!           │
│ - modified_at        │     │   from SchemaRegistry│     │ - Only manifest   │
│                      │     │                      │     │   .version (int)  │
│ Storage:             │     │ Storage:             │     │   for format      │
│ - In-memory w/TTL    │     │ - Memory tier        │     │                   │
│ - Hierarchy index    │     │ - S3 tier (parquet)  │     │ Storage:          │
│                      │     │                      │     │ - S3 parquet per  │
└──────────────────────┘     └──────────────────────┘     │   section         │
                                                          │ - JSON manifest   │
                                                          └──────────────────┘
           │                          │                          │
           │                          │                          │
           ▼                          ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           S3 BUCKET                                          │
│                                                                              │
│  dataframes/                                                                 │
│  └── {project_gid}/                                                          │
│      ├── manifest.json          # SectionPersistence - NO schema_version     │
│      ├── sections/              # SectionPersistence - NO schema_version     │
│      │   ├── {section_gid_1}.parquet                                        │
│      │   └── {section_gid_2}.parquet                                        │
│      ├── dataframe.parquet      # SectionPersistence final artifact         │
│      ├── watermark.json         # Watermark repo                            │
│      └── gid_lookup_index.json  # Index artifact                            │
│                                                                              │
│  cache/dataframes/              # DataFrameCache S3 tier                     │
│  └── {entity_type}:{project_gid}/                                           │
│      └── entry.parquet          # Has schema_version in metadata            │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐     ┌──────────────────────┐
│   SchemaRegistry     │     │   GidLookupIndex     │
│ (dataframes/models/  │     │ (services/           │
│  registry.py)        │     │  gid_lookup.py)      │
│                      │     │                      │
│ Purpose: Canonical   │     │ Purpose: O(1)        │
│ schema definitions   │     │ phone+vertical→GID   │
│                      │     │                      │
│ Version Tracking:    │     │ Version Tracking:    │
│ - Per-entity version │     │ - NONE! Built from   │
│   (e.g., Unit 1.1.0) │     │   DataFrame, no      │
│                      │     │   version metadata   │
│ Storage:             │     │                      │
│ - In-memory          │     │ Storage:             │
│ - Code-defined       │     │ - In-memory          │
└──────────────────────┘     │ - JSON in S3         │
                             └──────────────────────┘
```

### The Version Gap Problem

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE VERSION GAP CAUSING CASCADE FAILURES                  │
└─────────────────────────────────────────────────────────────────────────────┘

Timeline:
─────────────────────────────────────────────────────────────────────────────
Deployment A (UNIT_SCHEMA.version = "1.0.0", warm_hierarchy broken)
│
├─► SectionPersistence writes sections to S3
│   └─► Manifest: { "version": 1 }  ◄── Format version, NOT schema version
│   └─► Sections: office_phone = NULL, vertical = NULL (cascade failed)
│
│   Container restarts...
│
Deployment B (UNIT_SCHEMA.version = "1.1.0", warm_hierarchy fixed)
│
├─► _preload_dataframe_cache_progressive() starts
│   │
│   ├─► SectionPersistence.get_manifest_async()
│   │   └─► Returns existing manifest (version: 1 = format OK)
│   │
│   ├─► manifest.get_incomplete_section_gids()
│   │   └─► Returns [] (all sections COMPLETE from Deployment A)
│   │
│   ├─► sections_to_fetch = [] (SKIP FETCH!)
│   │
│   ├─► merge_sections_to_dataframe_async()
│   │   └─► Loads stale parquets with NULL cascade fields
│   │
│   ├─► DataFrameCache.put_async() (schema version validated)
│   │   └─► Stores DataFrame (passes check - it's a "fresh" build this session)
│   │       └─► But data is stale! Schema version was never checked at resume
│   │
│   └─► GidLookupIndex.from_dataframe()
│       └─► Filters NULL office_phone/vertical → 0 entries
│
└─► Demo: 0/3 matches
─────────────────────────────────────────────────────────────────────────────
```

### Root Cause: SectionManifest Lacks Schema Version

The `SectionManifest` model has only a format version (`version: int = 1`), not a schema version. This means:

1. **Resume always succeeds** regardless of schema changes
2. **Stale sections are merged** even when cascade resolution was broken
3. **Version bump in SchemaRegistry has no effect** on persisted sections

### Cascade Resolution Data Flow (Current vs Fixed)

```
CURRENT (BROKEN):
─────────────────
API Request → ProgressiveProjectBuilder.build_progressive_async(resume=True)
                │
                ├─► Check manifest → "All COMPLETE" → Skip fetch
                │
                ├─► merge_sections_to_dataframe_async()
                │   └─► Load sections from S3 (NULL cascade fields)
                │
                └─► GidLookupIndex.from_dataframe()
                    └─► Filter NULLs → 0 entries → 0/3 matches

FIXED:
──────
API Request → ProgressiveProjectBuilder.build_progressive_async(resume=True)
                │
                ├─► Check manifest
                │   ├─► manifest.schema_version == "1.0.0"
                │   └─► current_schema.version == "1.1.0"
                │   └─► MISMATCH! → manifest = None (fresh build)
                │
                ├─► sections_to_fetch = ALL sections
                │
                ├─► For each section:
                │   ├─► Fetch tasks from API
                │   ├─► put_batch_async(warm_hierarchy=True) → Fetch Business
                │   └─► Extract rows → office_phone/vertical populated
                │
                └─► GidLookupIndex.from_dataframe()
                    └─► Valid entries → 2/3 matches
```

## Alternatives Considered

### Alternative 1: Force Rebuild on Every Deploy (Rejected)

**Approach**: Disable resume capability entirely.

**Rejected because**:
- Significantly increases cold start time (30s → 5+ minutes for large projects)
- Loses the performance benefit of progressive persistence
- Heavy API load on every container restart

### Alternative 2: Hash-Based Section Validation (Considered but Deferred)

**Approach**: Store content hash of each section, revalidate on resume.

**Deferred because**:
- More complex implementation
- Requires reading section content to validate
- Schema version check is simpler and sufficient for current problem

### Alternative 3: Manifest TTL Expiration (Rejected)

**Approach**: Add TTL to manifests, force rebuild after expiration.

**Rejected because**:
- Doesn't solve version mismatch problem
- Still loads stale data within TTL window
- Arbitrary time-based invalidation less precise than version-based

## Detailed Design

### 1. Extend SectionManifest with Schema Version

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/section_persistence.py`

```python
class SectionManifest(BaseModel):
    """Manifest tracking section completion state for a project."""

    project_gid: str
    entity_type: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sections: dict[str, SectionInfo] = Field(default_factory=dict)
    total_sections: int = 0
    completed_sections: int = 0
    version: int = 1  # Manifest FORMAT version (existing)
    schema_version: str = ""  # NEW: Entity schema version used for build

    # ... existing methods ...

    def is_schema_compatible(self, current_schema_version: str) -> bool:
        """Check if manifest was built with current schema version.

        Args:
            current_schema_version: Current version from SchemaRegistry.

        Returns:
            True if schema versions match, False if rebuild needed.
        """
        if not self.schema_version:
            # Legacy manifest without schema_version - force rebuild
            return False
        return self.schema_version == current_schema_version
```

### 2. Update create_manifest_async to Include Schema Version

```python
async def create_manifest_async(
    self,
    project_gid: str,
    entity_type: str,
    section_gids: list[str],
    schema_version: str,  # NEW: Required parameter
) -> SectionManifest:
    """Create a new manifest for a project build.

    Args:
        project_gid: Asana project GID.
        entity_type: Entity type (e.g., "offer", "contact").
        section_gids: List of section GIDs to track.
        schema_version: Schema version from SchemaRegistry.

    Returns:
        Created SectionManifest.
    """
    manifest = SectionManifest(
        project_gid=project_gid,
        entity_type=entity_type,
        total_sections=len(section_gids),
        sections={gid: SectionInfo() for gid in section_gids},
        schema_version=schema_version,  # NEW
    )
    # ... rest unchanged ...
```

### 3. Update ProgressiveProjectBuilder to Validate Schema Version

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/progressive.py`

```python
async def build_progressive_async(
    self,
    resume: bool = True,
) -> ProgressiveBuildResult:
    """Build DataFrame with progressive section writes to S3."""
    # ... existing setup ...

    # Step 2: Check for existing manifest (resume capability)
    manifest: SectionManifest | None = None
    sections_to_fetch: list[str] = section_gids

    if resume:
        manifest = await self._persistence.get_manifest_async(self._project_gid)
        if manifest is not None:
            # NEW: Validate schema version before resume
            current_schema_version = self._schema.version
            if not manifest.is_schema_compatible(current_schema_version):
                logger.warning(
                    "progressive_build_schema_mismatch",
                    extra={
                        "project_gid": self._project_gid,
                        "manifest_version": manifest.schema_version,
                        "current_version": current_schema_version,
                        "action": "force_fresh_build",
                    },
                )
                # Delete stale manifest and sections
                await self._persistence.delete_manifest_async(self._project_gid)
                await self._persistence.delete_section_files_async(self._project_gid)
                manifest = None  # Force fresh build

            elif manifest is not None:
                # Resume: only fetch incomplete sections (existing logic)
                sections_to_fetch = manifest.get_incomplete_section_gids()
                sections_resumed = manifest.completed_sections
                # ... existing resume logging ...

    # Step 3: Create/update manifest with schema version
    if manifest is None:
        manifest = await self._persistence.create_manifest_async(
            self._project_gid,
            self._entity_type,
            section_gids,
            schema_version=self._schema.version,  # NEW
        )

    # ... rest unchanged ...
```

### 4. Update GidLookupIndex Serialization with Schema Version (Optional Enhancement)

For completeness, the GidLookupIndex should also track schema version:

```python
def serialize(self) -> dict[str, Any]:
    """Serialize index to JSON-compatible dict for S3 persistence."""
    return {
        "version": "1.0",  # Format version
        "schema_version": self._schema_version,  # NEW: Track source schema
        "created_at": self._created_at.isoformat(),
        "entry_count": len(self._lookup),
        "lookup": self._lookup,
    }
```

## Component Interaction After Fix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FIXED DATA FLOW WITH SCHEMA VERSION GATE                  │
└─────────────────────────────────────────────────────────────────────────────┘

_preload_dataframe_cache_progressive()
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SchemaRegistry.get_instance().get_schema("Unit")                           │
│  └─► UNIT_SCHEMA.version = "1.1.0"                                          │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SectionPersistence.get_manifest_async()                                     │
│  └─► Returns manifest: { schema_version: "1.0.0" }                           │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  manifest.is_schema_compatible("1.1.0")                                      │
│  └─► "1.0.0" != "1.1.0" → False                                              │
│  └─► LOG: progressive_build_schema_mismatch                                  │
│  └─► DELETE: manifest.json, sections/*.parquet                               │
│  └─► manifest = None → FORCE FRESH BUILD                                     │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ProgressiveProjectBuilder builds fresh:                                     │
│  ├─► Fetch all sections from API                                             │
│  ├─► put_batch_async(warm_hierarchy=True)                                    │
│  │   └─► Fetch Business parent → Cache with custom_fields                    │
│  ├─► Extract rows → office_phone/vertical POPULATED                          │
│  └─► Write sections + manifest with schema_version: "1.1.0"                  │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  GidLookupIndex.from_dataframe()                                             │
│  └─► office_phone/vertical are populated → Valid entries                     │
│  └─► Demo: 2/3 matches (as expected)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Migration Strategy

### Phase 1: Non-Breaking - Add Schema Version to Manifest (Immediate)

1. Add `schema_version` field to `SectionManifest` with default `""`
2. Update `create_manifest_async` to accept and store schema version
3. Add `is_schema_compatible()` method
4. Existing manifests without schema_version will fail compatibility check and trigger fresh build

**Risk**: Low - Legacy manifests force rebuild (one-time cost)

### Phase 2: Update Progressive Builder (Immediate)

1. Add schema version validation before resume
2. Delete stale manifest/sections on version mismatch
3. Pass schema version to `create_manifest_async`

**Risk**: Low - Fresh builds work correctly with current warm_hierarchy fix

### Phase 3: Optional - Extend to Other Artifacts (Future)

1. Add schema_version to GidLookupIndex serialization
2. Add schema_version to DataFrameCache S3 tier metadata
3. Consider content hashing for more granular validation

**Risk**: Low - Additive changes for extra safety

## Consequences

### Positive

1. **Cascade resolution will work** - Fresh builds always use current warm_hierarchy logic
2. **Schema evolution is safe** - Version bumps automatically invalidate stale caches
3. **Single source of truth** - SchemaRegistry version controls all persistence layers
4. **Audit trail** - Manifest logs which schema version built each section

### Negative

1. **One-time rebuild cost** - All existing manifests will be invalidated
2. **Increased deploy time** - First container start after schema bump takes longer
3. **S3 storage** - Stale sections remain until cleanup (can add TTL later)

### Neutral

1. **API call volume** - Same as fresh build; cached after first successful build
2. **Complexity** - Minimal - adding one field and one comparison

## Implementation Checklist

| Task | File | Priority |
|------|------|----------|
| Add `schema_version` to `SectionManifest` | `section_persistence.py` | P0 |
| Add `is_schema_compatible()` method | `section_persistence.py` | P0 |
| Update `create_manifest_async` signature | `section_persistence.py` | P0 |
| Add schema version validation in builder | `progressive.py` | P0 |
| Pass schema version to create_manifest | `progressive.py` | P0 |
| Add INFO logging for schema mismatch | `progressive.py` | P0 |
| Unit tests for schema compatibility | `tests/unit/` | P1 |
| Integration test for version-aware resume | `tests/integration/` | P1 |
| Update GidLookupIndex serialization (optional) | `gid_lookup.py` | P2 |

## Success Criteria

1. **SC-001**: Demo script returns 2/3 matches (not 0/3)
2. **SC-002**: Unit DataFrame `office_phone` column has non-NULL values
3. **SC-003**: Unit DataFrame `vertical` column has non-NULL values
4. **SC-004**: Schema version bump triggers manifest invalidation (logged)
5. **SC-005**: Fresh build populates cascade fields correctly

## Related Documents

- `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unit-cascade-resolution-fix.md`
- `/Users/tomtenuta/Code/autom8_asana/docs/design/ADR-hierarchy-registration-architecture.md`
- `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/schemas/unit.py`

## Decision Record

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-07 | Add schema_version to SectionManifest | Root cause is missing version tracking in resume path |
| 2026-01-07 | SchemaRegistry as single source of truth | Prevents version drift between layers |
| 2026-01-07 | Delete stale artifacts on mismatch | Cleaner than incremental migration |
| 2026-01-07 | Defer content hashing | Schema version check is sufficient for current problem |

---

## Appendix A: Questions from Architecture Analysis

### Q1: Do we have too many cache layers?

**Analysis**: We have 5 layers with different purposes:

| Layer | Purpose | Appropriate? |
|-------|---------|--------------|
| UnifiedTaskStore | Single task cache with hierarchy | Yes - needed for cascade resolution |
| DataFrameCache | Final DataFrame storage | Yes - needed for fast resolution |
| SectionPersistence | Progressive build resume | Yes - needed for fast cold start |
| SchemaRegistry | Schema definitions | Yes - single source of truth |
| GidLookupIndex | O(1) lookup | Yes - performance optimization |

**Conclusion**: The layers serve distinct purposes. The problem is not redundancy but **missing coordination** (schema version propagation).

### Q2: Should SectionPersistence and DataFrameCache be unified?

**Analysis**: They serve different purposes:
- SectionPersistence: Intermediate build artifacts for resume
- DataFrameCache: Final DataFrames for serving

**Recommendation**: Keep separate but ensure both validate against SchemaRegistry.

### Q3: Is resume at odds with schema evolution?

**Analysis**: Yes, without version tracking. The fix adds version tracking to make them compatible.

### Q4: Is hierarchy warming happening at the right point?

**Analysis**: Yes - `put_batch_async(warm_hierarchy=True)` is called during section fetch. The problem was stale sections being loaded without re-fetch.

### Q5: Should GidLookupIndex be built from DataFrameCache or UnifiedTaskStore?

**Analysis**: From DataFrame (current approach is correct). The DataFrame is the materialized view; the index is derived from it.

### Q6: What is the single source of truth?

**Answer after fix**:
- **Schema version**: SchemaRegistry
- **Task data**: UnifiedTaskStore
- **DataFrame data**: SectionPersistence (during build) → DataFrameCache (after build)
- **Lookup index**: GidLookupIndex (derived from DataFrame)

---

## Appendix B: Existing TDD Fix Status

The TDD at `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-unit-cascade-resolution-fix.md` documents fixes for the hierarchy warming logic itself. Those fixes appear to be implemented based on the code review:

| TDD Fix | Status | Evidence |
|---------|--------|----------|
| Fix 1: Cache check in put_batch_async | Implemented | unified.py:547 checks cache.get_versioned |
| Fix 2: Cache check in warm_ancestors_async | Implemented | hierarchy_warmer.py:177 checks cache.get_versioned |
| Fix 3: Diagnostic logging | Implemented | INFO-level logging present |
| Fix 4: Import EntryType | Implemented | hierarchy_warmer.py:14 |

**Why still failing**: The fixes work for **fresh builds** but stale S3 sections bypass the fix entirely via resume. This ADR addresses the resume path.
