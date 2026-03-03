# REFACTORING-PLAN: COMPAT-PURGE

**Producer**: architect-enforcer
**Date**: 2026-02-25
**Session**: session-20260225-160455-f6944d8b
**Input**: SMELL-REPORT.md (29 in-scope findings)

---

## Execution Strategy

### Workstream Sequencing

```
WS-DEAD ──→ WS-REEXPORT ──→ (merge checkpoint)
                                    │
         ┌──────────────────────────┤
         ▼                          ▼
    WS-DEPRECATED              WS-DUALPATH
         │                          │
         ▼                          ▼
    WS-BESPOKE              (merge checkpoint)
         │
         ▼
   (final suite)
```

**Dependency**: WS-DEAD must complete before WS-REEXPORT (shared file: `cache/__init__.py`).
All other workstreams have disjoint file scopes and can run in parallel worktrees.

### Scope Adjustments from SMELL-REPORT

**Deferred from WS-DUALPATH** (risk too high for this initiative):
- DP-01: `pipeline_templates` fallback (55 refs — migration, not cleanup)
- DP-02: Cache protocol dual-method surface (protocol change, all implementations)
- DP-03: Cache backend connection manager fallback (runtime DI risk)
- DP-05: HOLDER_KEY_MAP detection fallback (critical path, needs production logs)

**Deferred from WS-BESPOKE**:
- HW-03: `_apply_legacy_mapping` (already uses dynamic algorithm — name is misleading, not actually legacy logic)

**Net scope**: 22 findings across 5 workstreams.

---

## WS-DEAD: Dead Stubs, Aliases & Migration Scaffolding

**Phase**: 1 (execute first)
**Risk**: LOW
**Estimated LOC**: -120 to -180

### File-Scope Contract

| File | Action | Lines | What Changes |
|------|--------|-------|--------------|
| `cache/models/freshness.py` | DELETE | entire | Compat alias module |
| `cache/__init__.py` | EDIT | 142, 190 | Remove `Freshness` import + `__all__` entry |
| `cache/models/__init__.py` | EDIT | 37 | Remove `Freshness` import |
| `lifecycle/engine.py` | EDIT | 832-866 | Remove `_StubReopenService` + try/except |
| `dataframes/cache_integration.py` | EDIT | 451-456 | Remove `warm_struc_async` alias |
| `dataframes/builders/build_result.py` | EDIT | 207-229 | Remove `to_legacy()` method |
| `dataframes/builders/progressive.py` | EDIT | 76-100 | Remove `ProgressiveBuildResult` class |
| `dataframes/builders/__init__.py` | EDIT | 9, 58, 79 | Remove compat shim docstring + import + `__all__` entry |
| `cache/integration/factory.py` | EDIT | 228-229 | Update MIGRATION-PLAN comment |

### Before/After Contracts

**ST-01: freshness.py deletion**
```python
# BEFORE (cache/models/freshness.py — entire file):
"""Backward-compatible alias for FreshnessIntent."""
try:
    from autom8y_cache import Freshness
except ImportError:
    from autom8_asana.cache.models.freshness_unified import FreshnessIntent
    Freshness = FreshnessIntent

# AFTER: File deleted.
# cache/__init__.py: Remove `from autom8_asana.cache.models.freshness import Freshness`
# cache/models/__init__.py: Remove `from autom8_asana.cache.models.freshness import Freshness`
```

**Consumer updates**: Update `tests/unit/cache/test_reorg_imports.py` to remove/update
the Freshness import test (test the canonical path instead).

**ST-02: _StubReopenService removal**
```python
# BEFORE (lifecycle/engine.py:832-866):
def _import_reopen_service(client):
    try:
        from autom8_asana.lifecycle.reopen import ReopenService
        return ReopenService(client)
    except ImportError:
        return _StubReopenService()

class _StubReopenService:
    async def reopen_async(...) -> ReopenResult:
        ...

# AFTER:
def _import_reopen_service(client):
    from autom8_asana.lifecycle.reopen import ReopenService
    return ReopenService(client)
# _StubReopenService class deleted.
```

**ST-03: warm_struc_async alias removal**
```python
# BEFORE (cache_integration.py:451-456):
async def warm_struc_async(self, task_project_pairs):
    """Alias for warm_dataframe_async (backward compatibility)."""
    return await self.warm_dataframe_async(task_project_pairs)

# AFTER: Method deleted.
```

**Consumer update**: `tests/unit/dataframes/test_cache_integration.py:743` — change
`warm_struc_async(` → `warm_dataframe_async(`.

**MIG-01: BuildResult.to_legacy() + ProgressiveBuildResult removal**
```python
# BEFORE (build_result.py:207-229):
def to_legacy(self) -> Any:
    """Convert to legacy ProgressiveBuildResult..."""
    ...

# AFTER: Method deleted.
# ProgressiveBuildResult class deleted from progressive.py.
# Import + __all__ entry removed from builders/__init__.py.
```

**Consumer update**: `tests/unit/dataframes/builders/test_build_result.py` — remove
test for `to_legacy()`.

### Verification

```bash
# After all edits:
grep -rn "from autom8_asana.cache.models.freshness import" src/ tests/
grep -rn "_StubReopenService" src/
grep -rn "warm_struc_async" src/ tests/
grep -rn "to_legacy" src/autom8_asana/dataframes/ tests/unit/dataframes/
grep -rn "ProgressiveBuildResult" src/
# All should return zero hits (or only docs/).
```

### Scoped Tests

```bash
pytest tests/unit/cache/ tests/unit/dataframes/ tests/unit/lifecycle/ -x -q
```

---

## WS-REEXPORT: Backward-Compatibility Re-Export Elimination

**Phase**: 2 (after WS-DEAD)
**Risk**: LOW
**Estimated LOC**: -80 to -120
**Depends on**: WS-DEAD (cache/__init__.py overlap)

### File-Scope Contract

| File | Action | Lines | What Changes |
|------|--------|-------|--------------|
| `core/schema.py` | DELETE | entire | Module is pure re-export shim |
| `clients/data/client.py` | EDIT | 66-77 | Remove PII re-exports |
| `automation/seeding.py` | EDIT | 31-36 | Remove field_utils re-exports |
| `api/routes/resolver.py` | EDIT | 76-85 | Remove model re-exports from `__all__` |
| `models/business/detection/types.py` | EDIT | 20-22 | Remove EntityType re-export |
| `models/business/detection/__init__.py` | EDIT | ~75 | Import EntityType from core.types directly |
| `models/business/patterns.py` | EDIT | 132-135 | Remove module-level constant aliases |
| `core/logging.py` | EDIT | 104-106 | Remove module-level logger alias |
| `cache/__init__.py` | EDIT | 295-299 | Remove `__getattr__` lazy-load |
| `cache/models/freshness_unified.py` | EDIT | 10-13 | Remove old-name type aliases |

### Consumer Import Updates (14 total)

**RE-01: core/schema.py deletion** (2 consumers)
| Consumer File | Line | Old Import | New Import |
|--------------|------|-----------|-----------|
| `cache/integration/dataframe_cache.py` | 63 | `from autom8_asana.core.schema import get_schema_version` | `from autom8_asana.dataframes.models.registry import get_schema_version` |
| `cache/dataframe/tiers/progressive.py` | 188 | `from autom8_asana.core.schema import get_schema_version` | `from autom8_asana.dataframes.models.registry import get_schema_version` |

**RE-02: detection/types.py EntityType re-export** (11 consumers → keep in detection/__init__)
```
Strategy: Remove re-export from detection/types.py. Update detection/__init__.py
to import EntityType directly from core.types. Consumers importing from
detection.__init__ (29 files) are unaffected.
```
| Consumer File | Old Import | New Import |
|--------------|-----------|-----------|
| `models/business/detection/config.py:17` | `from ...detection.types import EntityType, EntityTypeInfo` | `from autom8_asana.core.types import EntityType` + keep EntityTypeInfo from types |
| `models/business/_bootstrap.py:54` | `from ...detection.types import EntityType` | `from autom8_asana.core.types import EntityType` |
| `resolution/strategies.py:181,301` | `from ...detection.types import EntityType` | `from autom8_asana.core.types import EntityType` |
| 7 test files | Various | `from autom8_asana.core.types import EntityType` |

**RE-04: clients/data/client.py PII re-exports** (3 consumers)
| Consumer File | Old Import | New Import |
|--------------|-----------|-----------|
| `automation/workflows/insights_formatter.py:31` | `from ...clients.data.client import mask_phone_number` | `from autom8_asana.clients.data._pii import mask_phone_number` |
| `clients/data/_endpoints/export.py:175` | `from ...clients.data.client import mask_phone_number` | `from autom8_asana.clients.data._pii import mask_phone_number` |
| `tests/unit/clients/data/test_pii.py:34` | `from ...clients.data.client import mask_phone_number` | `from autom8_asana.clients.data._pii import mask_phone_number` |

**RE-05: automation/seeding.py field_utils re-exports** (5 consumers, test-only)
| Consumer File | Old Import | New Import |
|--------------|-----------|-----------|
| `tests/unit/automation/test_seeding.py:807,816,824,839,851` | `from ...automation.seeding import get_field_attr` | `from autom8_asana.core.field_utils import get_field_attr` |

**RE-07: api/routes/resolver.py model re-exports** (4 consumers, test-only)
| Consumer File | Old Import | New Import |
|--------------|-----------|-----------|
| `tests/unit/api/test_routes_resolver.py:538,548,557,564` | `from ...api.routes.resolver import ResolutionCriterion` | `from autom8_asana.api.routes.resolver_models import ResolutionCriterion` |

**RE-08: patterns.py constant aliases** — grep for consumers before removing
**RE-09: logging.py logger alias** — zero consumers (confirmed), safe to remove
**RE-06: cache/__init__.py lazy-load** — grep for `from autom8_asana.cache import dataframe_cache`

### Verification

```bash
# After all edits — each should return zero hits:
grep -rn "from autom8_asana.core.schema import" src/ tests/
grep -rn "from autom8_asana.clients.data.client import mask_phone" src/ tests/
grep -rn "from autom8_asana.automation.seeding import get_field_attr" src/ tests/
grep -rn "from autom8_asana.automation.seeding import normalize_custom_fields" src/ tests/
grep -rn "from autom8_asana.api.routes.resolver import Resolution" tests/
```

### Scoped Tests

```bash
pytest tests/unit/cache/ tests/unit/api/ tests/unit/automation/ \
       tests/unit/clients/ tests/unit/models/ tests/unit/core/ \
       tests/unit/dataframes/ -x -q
```

---

## WS-DEPRECATED: Deprecated Code Removal

**Phase**: 3 (parallel, independent files)
**Risk**: MEDIUM
**Estimated LOC**: -60 to -100

### File-Scope Contract

| File | Action | Lines | What Changes |
|------|--------|-------|--------------|
| `dataframes/resolver/protocol.py` | EDIT | 72-92 | Remove `expected_type` param |
| `dataframes/resolver/default.py` | EDIT | 150-200 | Remove `expected_type` param + coercion path |
| `dataframes/resolver/mock.py` | EDIT | 247-270 | Remove `expected_type` param |
| `models/business/process.py` | EDIT | 86, 445, 454 | Remove `GENERIC` enum + fallback returns |
| `models/custom_field_accessor.py` | EDIT | 37-57, 324-386 | Remove `strict` param, always strict |

### Before/After Contracts

**DEP-01: expected_type removal**
```python
# BEFORE (protocol.py):
def extract_value(self, ..., expected_type: type | None = None, column_def: ColumnDef | None = None):

# AFTER:
def extract_value(self, ..., column_def: ColumnDef | None = None):
```

Update: `tests/unit/dataframes/test_resolver.py:837, 1287` — remove `expected_type=` args.

**DEP-02: ProcessType.GENERIC removal**
```python
# BEFORE (process.py):
GENERIC = "generic"  # preserved for backward compatibility
...
return ProcessType.GENERIC  # fallback

# AFTER:
# GENERIC removed from enum.
# Fallback returns ProcessType.UNKNOWN or raises ValueError (check existing UNKNOWN member).
```

**Prerequisite check**: Verify `ProcessType` has an `UNKNOWN` or similar fallback member.

**DEP-03: strict=False removal**
```python
# BEFORE:
def __init__(self, ..., strict: bool = True):

# AFTER:
def __init__(self, ...,):
    # Always strict behavior. NameNotFoundError on unknown names.
```

**Prerequisite check**: grep for `strict=False` in tests to identify test fixtures to update.

### Verification

```bash
grep -rn "expected_type" src/autom8_asana/dataframes/resolver/
grep -rn "ProcessType.GENERIC" src/
grep -rn "strict=False" src/autom8_asana/models/custom_field_accessor.py tests/
```

### Scoped Tests

```bash
pytest tests/unit/dataframes/test_resolver.py tests/unit/models/business/test_process*.py \
       tests/unit/models/test_custom_field*.py -x -q
```

---

## WS-DUALPATH: Dual-Path Collapse (Reduced Scope)

**Phase**: 3 (parallel, independent files)
**Risk**: LOW-MEDIUM
**Estimated LOC**: -40 to -60

### Scope (2 items from original 6)

Only safe, well-scoped items retained:
- DP-04: `_children_cache` dual-write
- DP-06: `LEGACY_ATTACHMENT_PATTERN` cleanup

### File-Scope Contract

| File | Action | Lines | What Changes |
|------|--------|-------|--------------|
| `models/business/base.py` | EDIT | 145-147, 175-177 | Remove dual-write to `_children_cache` |
| `resolution/context.py` | EDIT | 430-434 | Use `CHILDREN_ATTR` instead of `_children_cache` fallback |
| `automation/workflows/insights_export.py` | EDIT | 56-62, 574-582 | Remove `LEGACY_ATTACHMENT_PATTERN` + dual cleanup |

### Before/After Contracts

**DP-04: _children_cache dual-write removal**
```python
# BEFORE (base.py:145-147):
setattr(self, children_attr, children)
if children_attr != "_children_cache":
    self._children_cache = children  # ← dual-write

# AFTER:
setattr(self, children_attr, children)
# No dual-write. Only the subclass CHILDREN_ATTR is set.
```

```python
# BEFORE (context.py:430):
if holder is not None and not getattr(holder, "_children_cache", None):

# AFTER:
children_attr = getattr(holder.__class__, "CHILDREN_ATTR", "_children_cache")
if holder is not None and not getattr(holder, children_attr, None):
```

```python
# BEFORE (base.py:175-177):
setattr(self, children_attr, [])
self._children_cache = None

# AFTER:
setattr(self, children_attr, [])
# If children_attr != "_children_cache", don't also set _children_cache
```

**DP-06: LEGACY_ATTACHMENT_PATTERN removal**
```python
# BEFORE (insights_export.py:56-62):
DEFAULT_ATTACHMENT_PATTERN = "insights_export_*.html"
LEGACY_ATTACHMENT_PATTERN = "insights_export_*.md"

# AFTER:
DEFAULT_ATTACHMENT_PATTERN = "insights_export_*.html"
# LEGACY_ATTACHMENT_PATTERN deleted
```

```python
# BEFORE (insights_export.py:578-582):
if attachment_pattern != LEGACY_ATTACHMENT_PATTERN:
    await self._delete_old_attachments(
        offer_gid, LEGACY_ATTACHMENT_PATTERN, exclude_name=filename
    )

# AFTER: Dual cleanup block removed entirely.
```

### Verification

```bash
grep -rn "_children_cache" src/
grep -rn "LEGACY_ATTACHMENT_PATTERN" src/
```

### Scoped Tests

```bash
pytest tests/unit/models/business/ tests/unit/resolution/ \
       tests/unit/automation/ -x -q
```

---

## WS-BESPOKE: Hardcoded Bespoke Workarounds

**Phase**: 3 (parallel, independent files)
**Risk**: LOW-MEDIUM
**Estimated LOC**: -20 to -40

### Scope (2 items — HW-03 deferred)

- HW-01: "address" legacy alias in config
- HW-02: Hardcoded key columns in gid_lookup

### File-Scope Contract

| File | Action | Lines | What Changes |
|------|--------|-------|--------------|
| `config.py` | EDIT | 104-117 | Remove "address" alias + `_LEGACY_TTL_EXCLUDE` |
| `services/gid_lookup.py` | EDIT | 252-276 | Remove hardcoded default key_columns |

### Before/After Contracts

**HW-01: address legacy alias removal**
```python
# BEFORE (config.py):
_LEGACY_TTL_EXCLUDE = {"location"}
DEFAULT_ENTITY_TTLS = { ... }
DEFAULT_ENTITY_TTLS["address"] = 3600  # Legacy alias for location

# AFTER:
# _LEGACY_TTL_EXCLUDE deleted.
# "address" key removed from DEFAULT_ENTITY_TTLS.
# Only canonical "location" key remains.
```

**Prerequisite check**: grep for `DEFAULT_ENTITY_TTLS["address"]` or `DEFAULT_ENTITY_TTLS.get("address")`
to find consumers relying on the alias.

**HW-02: gid_lookup hardcoded defaults**
```python
# BEFORE (gid_lookup.py:275-276):
if key_columns is None:
    key_columns = ["office_phone", "vertical"]

# AFTER:
if key_columns is None:
    raise ValueError("key_columns is required")
# OR: derive from schema/entity metadata
```

**Prerequisite check**: grep for `.from_dataframe(` without `key_columns=` arg to find
callers relying on the default.

### Verification

```bash
grep -rn '"address"' src/autom8_asana/config.py
grep -rn "_LEGACY_TTL_EXCLUDE" src/
grep -rn "office_phone.*vertical" src/
```

### Scoped Tests

```bash
pytest tests/unit/test_config*.py tests/unit/services/test_gid*.py -x -q
```

---

## Deferred Items (Not In This Initiative)

| Item | Reason | Trigger |
|------|--------|---------|
| DP-01: `pipeline_templates` | 55 refs, migration not cleanup | Dedicated migration initiative |
| DP-02: Cache protocol dual-methods | All implementations affected | Cache architecture initiative |
| DP-03: Backend connection fallback | Runtime DI risk | Cache architecture initiative |
| DP-05: HOLDER_KEY_MAP fallback | Critical detection path | Production log analysis |
| HW-03: `_apply_legacy_mapping` | Already uses dynamic algorithm | Rename, not remove |
| D-GETCF: `get_custom_fields()` | 161 consumers | Separate deprecation initiative |
| D-QUERY: Deprecated endpoint | CloudWatch gate | Ops verification |
| D-PRELOAD: legacy.py | ADR-011 active | Production incident trigger |

---

## Cross-Workstream File Isolation Matrix

No file appears in more than one workstream (verified via exhaustive overlap analysis).

| File | WS-DEAD | WS-REEXPORT | WS-DEPRECATED | WS-DUALPATH | WS-BESPOKE |
|------|---------|-------------|---------------|-------------|------------|
| cache/__init__.py | EDIT (L142,190) | EDIT (L295-299) | — | — | — |
| builders/__init__.py | EDIT (L9,58,79) | — | — | — | — |

**Exception**: `cache/__init__.py` is edited by both WS-DEAD (remove Freshness import) and
WS-REEXPORT (remove lazy-load). These are different line ranges. **Sequencing resolves**:
WS-DEAD runs first, WS-REEXPORT runs second.

---

## Execution Checklist

### Per-Workstream Protocol

1. Start from updated `main` (merge previous WS if sequential)
2. Create worktree: `.claude/worktrees/COMPAT-PURGE-WS-{ID}`
3. Execute edits per file-scope contract
4. Run grep verification (zero consumers of removed symbols)
5. Run scoped tests (must pass)
6. Atomic commit per concern
7. Merge to main, update TRACKER.md

### Full Suite Gate

After all workstreams merged: `pytest --tb=short -q 2>/dev/null | grep -v '^{'`
Must match baseline: `11675 passed, 42 skipped`

---

## Summary

| Metric | Value |
|--------|-------|
| Workstreams | 5 |
| In-scope findings | 22 |
| Deferred findings | 8 |
| Files modified | ~30 (src + tests) |
| Files deleted | 2 (freshness.py, core/schema.py) |
| Import updates | 14 |
| Estimated LOC reduction | -320 to -500 |
| Risk | LOW overall (highest: WS-DEPRECATED MEDIUM) |
