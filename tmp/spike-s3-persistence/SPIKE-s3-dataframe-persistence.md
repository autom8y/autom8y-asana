# SPIKE: S3 DataFrame Persistence Integration

**Date**: 2026-01-05
**Timebox**: 4 hours
**Status**: COMPLETE
**Question**: Can we wire S3 persistence into the DataFrame builder?

---

## Answer

**YES.** Constructor injection works cleanly. Implementation complete with 4 passing tests.

---

## Approach Summary

| Phase | Agent | Output |
|-------|-------|--------|
| 1. Technology Selection | technology-scout | `tech-assessment-s3-testing.md` |
| 2. Integration Mapping | integration-researcher | `integration-map.md` |
| 3. Prototype Implementation | prototype-engineer | Code + tests |

---

## Key Findings

### What Worked

1. **moto is the right choice**: Already a dependency (`moto>=5.0.0`), existing patterns in `tests/unit/cache/test_s3_backend.py`, zero infrastructure overhead
2. **Constructor injection fits existing patterns**: Matches `cache_integration` parameter pattern in `ProjectDataFrameBuilder`
3. **Silent fallback already implemented**: `DataFramePersistence` handles degradation gracefully - no new error handling needed
4. **Watermark coordination is free**: `save_dataframe()` persists watermark metadata automatically

### Surprises

1. **No double-write risk at builder level**: The builder only saves after `_build_with_unified_store_async()`; `api/main.py` handles its own persistence separately (no conflict if both enabled)
2. **Async save is nearly free**: Non-blocking fire-and-forget pattern; no measurable build time impact

---

## Implementation Summary

### Files Changed

| File | Change |
|------|--------|
| `src/autom8_asana/dataframes/builders/project.py` | Added `persistence` constructor param, `_persist_dataframe_async()` method, save trigger after build |

### Files Created

| File | Purpose |
|------|---------|
| `tests/unit/dataframes/test_persistence_integration.py` | 4 test cases covering happy path, no-op, failure fallback, round-trip |
| `tmp/spike-s3-persistence/tech-assessment-s3-testing.md` | Technology decision rationale |
| `tmp/spike-s3-persistence/integration-map.md` | Integration points and effort estimates |

### Test Coverage

```
tests/unit/dataframes/test_persistence_integration.py
  - test_automatic_persistence_on_build        PASS
  - test_persistence_none_does_not_save        PASS
  - test_persistence_failure_silent_fallback   PASS
  - test_round_trip_persistence                PASS
```

### Code Pattern (from project.py)

```python
# Constructor accepts optional persistence
def __init__(
    self,
    ...
    persistence: "DataFramePersistence | None" = None,
) -> None:
    self._persistence = persistence

# Save triggered after successful build
if self._persistence is not None:
    await self._persist_dataframe_async(
        project_gid=project_gid,
        df=df,
        watermark=datetime.now(timezone.utc),
    )
```

---

## Production Readiness

### Ready Now

- [x] Constructor injection (backward compatible - optional param)
- [x] Silent fallback on S3 failures
- [x] Watermark persistence
- [x] moto-based test suite

### Remaining for Production

| Gap | Effort | Priority |
|-----|--------|----------|
| Wire persistence in `api/main.py` call sites | 1 hour | P1 |
| Add `create_with_auto_persistence()` factory method | 30 min | P2 |
| E2E test with real S3 bucket | 1 hour | P2 |
| Documentation in docstrings | 30 min | P3 |
| Remove duplicate save calls in `_preload_dataframe_cache()` | 30 min | P3 |

### Production Constraints (validated)

- S3 bucket must exist and be accessible (graceful degradation if not)
- AWS credentials via environment/IAM (standard boto3 credential chain)
- No index persistence - rebuild index on load (per design decision)

---

## Follow-up Actions

1. **Create PRD** for production integration (covers `api/main.py` wiring)
2. **Add factory method** `create_with_auto_persistence()` for convenience
3. **Update api/main.py** to pass persistence to builder instead of manual save calls
4. **Run against real S3** in staging environment before production deploy

---

## Artifacts

| Artifact | Path |
|----------|------|
| This summary | `/Users/tomtenuta/Code/autom8_asana/tmp/spike-s3-persistence/SPIKE-s3-dataframe-persistence.md` |
| Tech assessment | `/Users/tomtenuta/Code/autom8_asana/tmp/spike-s3-persistence/tech-assessment-s3-testing.md` |
| Integration map | `/Users/tomtenuta/Code/autom8_asana/tmp/spike-s3-persistence/integration-map.md` |
| Test file | `/Users/tomtenuta/Code/autom8_asana/tests/unit/dataframes/test_persistence_integration.py` |
| Modified builder | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/dataframes/builders/project.py` |

---

## Recommendation

**GO for production implementation.** The spike validated the approach with minimal risk. Estimated production effort: 3-4 hours including wiring and cleanup.
