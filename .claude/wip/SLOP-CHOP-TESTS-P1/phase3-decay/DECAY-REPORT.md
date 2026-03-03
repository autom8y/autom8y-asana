# Phase 3: Decay Report — Temporal Debt Detection

**Scope**: tests/unit/ (389 files, ~184K LOC, 9795 tests)
**Agent**: cruft-cutter
**Date**: 2026-02-23

## Summary

| Category | Findings | Action |
|----------|----------|--------|
| Stale skip markers | 0 | — |
| Dead TODO/FIXME/HACK | 0 | — |
| Dead helper functions | 3 | DELETE |
| Orphaned conftest fixtures | 0 | — |
| Commented-out test code | 0 | — |
| Migration-era temporal shims | 0 actionable | — |
| **Total actionable** | **3** | **3 deletions** |

**Verdict**: The test suite is remarkably clean of temporal debt. The hygiene-rite structural cleanup was thorough.

---

## Confirmed Findings

### [C-001] Dead helper: `_make_mock_cache_provider`
- **File**: `tests/unit/api/test_routes_resolver.py:42`
- **Content**: `def _make_mock_cache_provider(mock_df: pl.DataFrame):` — 12-line helper
- **Rationale**: Defined but never called in the file or anywhere in `tests/unit/`. 0 references outside the definition.
- **Action**: DELETE

### [C-002] Dead helper: `make_watermark_json`
- **File**: `tests/unit/cache/dataframe/test_progressive_tier.py:43`
- **Content**: `def make_watermark_json(watermark: str = "2024-01-15T12:00:00+00:00") -> bytes:` — helper to construct watermark JSON
- **Rationale**: Defined but never called. Tests in the file use `make_watermark_metadata` instead. 0 references outside the definition.
- **Action**: DELETE

### [C-003] Dead helper: `_make_request_no_state`
- **File**: `tests/unit/api/test_error_helpers.py:51`
- **Content**: `def _make_request_no_state() -> MagicMock:` — constructs mock request without app state
- **Rationale**: Defined but never called. Tests use different mock request construction. 0 references outside the definition.
- **Action**: DELETE

---

## Investigated and Dismissed

### Skip markers — All legitimate
3 skip markers found, all conditional on optional test dependencies:
- `tests/unit/persistence/test_reorder.py:269` — `@pytest.mark.skipif(not _HAS_HYPOTHESIS, reason="hypothesis not installed")` — ACTIVE, hypothesis is optional
- `tests/unit/cache/test_s3_backend.py:718` — `@pytest.mark.skipif(not MOTO_AVAILABLE, reason="moto not installed")` — ACTIVE, moto is optional
- `tests/unit/cache/test_redis_backend.py:311` — `@pytest.mark.skipif(not FAKEREDIS_AVAILABLE, reason="fakeredis not installed")` — ACTIVE, fakeredis is optional

### TODO/FIXME/HACK — None found
`grep -r "TODO\|FIXME\|HACK" tests/unit/` → 0 matches in test code. All were cleaned in prior sprints.

### TDD/ADR provenance comments — Documentation, not cruft
Multiple test files have module docstrings like `Per TDD-0007:`, `Per TDD-0010:`, `Per D-028:`. These are provenance references documenting which design document drove the test creation. They reference completed items but serve as architectural documentation linking tests to decisions. NOT temporal debt.

### Backwards-compatibility test classes — Testing active shims
Tests like `TestNameGidBackwardsCompatibility` test `gid` property shims that are still active in production code. These are testing live backwards-compat behavior, not obsolete code.

### Migration-era references — Historical record in test names
RF-008/RF-009/RF-010/RF-011/RF-012 references appear in git commit messages from the hygiene sprint. They are part of version control history, not test code. No in-code migration shims remain.

### `_apply_legacy_mapping` — Active production code
`tests/unit/dataframes/test_universal_strategy.py` references legacy field mapping. The production `_apply_legacy_mapping` function still exists and is live, so the test is valid.

### Pipeline template references — Active degraded-mode path
Tests referencing `pipeline_templates` test an active (though legacy) pipeline mode per ADR-011. Not temporal debt.

---

## Estimated LOC Impact
- 3 dead helpers: ~25 lines to delete
- Net impact: **-25 LOC**
