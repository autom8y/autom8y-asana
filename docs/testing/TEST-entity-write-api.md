# Entity Write API - Test Summary and Defect Report

**Test Date**: 2026-02-11
**QA Adversary**: Claude (Opus 4.6)
**Target**: Entity Write API (PATCH /api/v1/entity/{entity_type}/{gid})
**Entities Tested**: Offer (GID 1205571482650639), Process (GID 1209719836385072)

---

## Executive Summary

**Production Readiness: CONDITIONAL GO**

The Entity Write API passes functional validation with 41/43 tests passing, 2 expected failures documenting known cache coherence issues. The core write pipeline (resolve-write-verify) works correctly. Three defects were discovered during adversarial testing, with severity ranging from HIGH to MEDIUM.

### Key Findings

| Category | Pass | XFail | Fail | Total |
|----------|------|-------|------|-------|
| Registry Discovery | 8 | 0 | 0 | 8 |
| Field Name Resolution | 7 | 0 | 0 | 7 |
| Live Writes | 3 | 2 | 0 | 5 |
| Enum Resolution | 5 | 0 | 0 | 5 |
| Error Paths | 8 | 0 | 0 | 8 |
| Partial Success | 2 | 0 | 0 | 2 |
| Process Edge Case | 3 | 0 | 0 | 3 |
| Result Structure | 2 | 0 | 0 | 2 |
| Defect Regression | 3 | 0 | 0 | 3 |
| **TOTAL** | **41** | **2** | **0** | **43** |

---

## Defect Report

### D-EW-001: include_updated Returns Stale Cached Data

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Component** | `FieldWriteService._refetch_updated` + `TasksClient` cache |
| **Status** | OPEN |
| **Regression Test** | `TestDiscoveredDefects::test_d_ew_001_include_updated_returns_stale_cache` |

**Description**:
When `include_updated=True` is passed to `write_async()`, the `_refetch_updated()` method fetches task data to echo back current field values. However, it uses the same `AsanaClient` instance that already cached the task data during the initial `_fetch_task()` call. Since `TasksClient.update_async()` does NOT invalidate the cache, the subsequent `get_async()` call returns stale pre-write data.

**Impact**:
- Callers relying on `result.updated_fields` receive stale pre-write values
- No indication that values are stale
- Workaround exists: re-fetch with a fresh client

**Reproduction Steps**:
1. Call `write_service.write_async(entity_type="offer", gid="...", fields={"asset_id": "NEW-VALUE"}, include_updated=True)`
2. Observe `result.updated_fields["asset_id"]` equals the OLD value, not "NEW-VALUE"
3. Fetch task with a fresh client -- confirms the write DID succeed

**Fix Recommendation**:
Option A: Invalidate task cache after `update_async()` call
Option B: Use `force_refresh=True` parameter (if available) in `_refetch_updated()`
Option C: Create a fresh client for the refetch operation

**Fix Complexity**: LOW (5-10 lines)

---

### D-EW-002: Numeric Enum Option Names Treated as GID Passthroughs

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Component** | `FieldResolver._resolve_single_option` |
| **Status** | OPEN |
| **Regression Test** | `TestDiscoveredDefects::test_d_ew_002_numeric_enum_name_treated_as_gid` |

**Description**:
The `_resolve_single_option()` function checks `value_str.isdigit()` first to detect if the caller passed an enum option GID directly. If true AND the value exists in `name_to_gid`, it returns the raw string as-is. However, `_build_enum_lookup()` maps BOTH option names AND GIDs to the lookup dict. When an enum option has a numeric name (e.g., "1" or "2"), the `isdigit()` check treats the name as a GID and returns it directly instead of mapping to the actual GID.

**Impact**:
- Enum fields with numeric option names (e.g., "Algo Version" with options "1", "2") cannot be written correctly
- Asana API returns `enum_value: Unknown object: 2 (HTTP 400)`
- Affects any restore operation that tries to set the original value back

**Reproduction Steps**:
1. Enum field "Algo Version" has options: name="1" (GID 1209059380430446), name="2" (GID 1209059380430447)
2. Call resolver with value "2"
3. `_resolve_single_option()` returns "2" (not the GID "1209059380430447")
4. Asana rejects payload with "Unknown object: 2"

**Fix Recommendation**:
```python
def _resolve_single_option(value, name_to_gid, enum_options):
    value_str = str(value).lower().strip()

    # Check if value is a REAL GID (numeric AND >= 13 digits, typical Asana GID length)
    if value_str.isdigit() and len(value_str) >= 13:
        if value_str in name_to_gid:
            return value_str
        return None  # Invalid GID

    # Otherwise treat as name lookup (case-insensitive)
    if value_str in name_to_gid:
        return name_to_gid[value_str]
    return None
```

**Fix Complexity**: LOW (5-10 lines)

---

### D-EW-003: Offer.algo_version Declared as TextField but is Enum in Asana

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Component** | `Offer` model definition (`offer.py` line 180) |
| **Status** | OPEN |
| **Regression Test** | `TestDiscoveredDefects::test_d_ew_003_algo_version_model_type_mismatch` |

**Description**:
The Offer model declares `algo_version = TextField()` but the actual Asana custom field "Algo Version" has `resource_subtype='enum'` with options ["1", "2"]. This type mismatch causes:
1. Text values written to `algo_version` fail with "Enum value not found"
2. Combined with D-EW-002, restoring the original enum value triggers Asana 400

**Impact**:
- Cannot use the Entity Write API to set algo_version to arbitrary text values
- Original design intent unclear -- was this meant to be an enum or text field?

**Fix Recommendation**:
Either:
A. Update model: `algo_version = EnumField()` (matches Asana)
B. Update Asana: Change "Algo Version" custom field to text type

**Fix Complexity**: LOW (1 line model change) or MEDIUM (Asana admin change)

---

## Test Plan Details

### Category 1: Registry Discovery (8 tests)

Tests verify `EntityWriteRegistry` correctly discovers writable entity types from model descriptors.

| Test | Status | Notes |
|------|--------|-------|
| `test_offer_is_writable` | PASS | Offer discovered as writable |
| `test_offer_project_gid_correct` | PASS | Project GID matches constant |
| `test_offer_descriptor_index_contains_expected_fields` | PASS | Key fields present in index |
| `test_offer_descriptor_index_display_names` | PASS | snake_case maps to display names |
| `test_process_is_not_writable` | PASS | Process excluded (PRIMARY_PROJECT_GID=None) |
| `test_is_writable_returns_false_for_nonexistent` | PASS | Unknown types return False |
| `test_writable_types_returns_sorted_list` | PASS | Sorted list includes offer |
| `test_core_fields_on_offer_info` | PASS | CORE_FIELD_NAMES exposed |

### Category 2: Field Name Resolution (7 tests)

Tests verify `FieldResolver` resolves business-domain field names to Asana API payloads.

| Test | Status | Notes |
|------|--------|-------|
| `test_descriptor_name_resolves` | PASS | "asset_id" -> "Asset ID" |
| `test_display_name_resolves_case_insensitive` | PASS | Case-insensitive matching |
| `test_case_variations_resolve` | PASS | "ASSET ID", "asset id", etc. |
| `test_snake_case_descriptor_maps_correctly` | PASS | "weekly_ad_spend" -> "Weekly AD Spend" |
| `test_core_fields_resolve` | PASS | "name", "notes" as core fields |
| `test_invalid_field_returns_skipped_with_suggestions` | PASS | Unknown field with fuzzy suggestions |
| `test_typo_field_suggests_correct_name` | PASS | "assset_id" suggests "Asset ID" |

### Category 3: Live Writes (5 tests)

Tests write to real Asana entity with save/restore semantics.

| Test | Status | Notes |
|------|--------|-------|
| `test_text_field_write` | XFAIL | Write succeeds, include_updated returns stale (D-EW-001) |
| `test_number_field_write` | XFAIL | Write succeeds, include_updated returns stale (D-EW-001) |
| `test_core_field_write_notes` | PASS | Core field write works |
| `test_null_clear_text_field` | PASS | Null clear works for text fields |
| `test_mixed_write_multiple_fields` | PASS | Multi-field write in single call |

### Category 4: Enum Resolution (5 tests)

Tests enum and multi-enum field handling.

| Test | Status | Notes |
|------|--------|-------|
| `test_enum_options_discoverable` | PASS | Can inspect enum options |
| `test_enum_write_by_name` | PASS | Write by option name works |
| `test_enum_write_case_insensitive` | PASS | Case-insensitive enum matching |
| `test_invalid_enum_value_returns_skipped` | PASS | Invalid enum -> skipped with suggestions |
| `test_multi_enum_write_list` | PASS | Multi-select enum write works |

### Category 5: Error Paths (8 tests)

Tests error handling and edge cases.

| Test | Status | Notes |
|------|--------|-------|
| `test_wrong_entity_type_raises_mismatch` | PASS | EntityTypeMismatchError raised |
| `test_nonexistent_gid_raises_not_found` | PASS | TaskNotFoundError raised |
| `test_all_invalid_fields_raises_no_valid_fields` | PASS | NoValidFieldsError raised |
| `test_empty_fields_validation` | PASS | Pydantic rejects empty fields |
| `test_wrong_type_for_number_field` | PASS | Type validation for numbers |
| `test_wrong_type_for_text_field` | PASS | Type validation for text |
| `test_wrong_type_for_enum_field` | PASS | Type validation for enums |
| `test_unwritable_entity_type_raises_value_error` | PASS | ValueError for non-writable types |

### Category 6: Partial Success (2 tests)

Tests partial success behavior with mixed valid/invalid fields.

| Test | Status | Notes |
|------|--------|-------|
| `test_mixed_valid_and_invalid_fields` | PASS | Valid fields written, invalid skipped |
| `test_partial_with_type_error` | PASS | Type error doesn't block valid fields |

### Category 7: Process Edge Case (3 tests)

Tests Process entity (PRIMARY_PROJECT_GID=None) behavior.

| Test | Status | Notes |
|------|--------|-------|
| `test_process_excluded_from_writable` | PASS | Not in writable_types() |
| `test_process_get_returns_none` | PASS | get("process") returns None |
| `test_process_has_descriptors` | PASS | Exclusion is project GID, not missing descriptors |

### Category 8: Result Structure (2 tests)

Tests WriteFieldsResult object structure.

| Test | Status | Notes |
|------|--------|-------|
| `test_result_has_correct_metadata` | PASS | All metadata fields populated |
| `test_resolved_field_has_gid_for_custom` | PASS | Custom field GID in ResolvedField |

### Category 9: Defect Regression (3 tests)

Tests that expose and document discovered defects.

| Test | Status | Notes |
|------|--------|-------|
| `test_d_ew_001_include_updated_returns_stale_cache` | PASS | Confirms D-EW-001 bug exists |
| `test_d_ew_002_numeric_enum_name_treated_as_gid` | PASS | Confirms D-EW-002 bug exists |
| `test_d_ew_003_algo_version_model_type_mismatch` | PASS | Confirms D-EW-003 mismatch |

---

## Lifecycle Engine Validation (Supplementary)

The hardened lifecycle engine (per user request to validate Sales process GID 1209719836385072) was also validated.

**Test File**: `tests/integration/test_lifecycle_smoke.py`
**Results**: 82 passed, 1 xfailed

| Category | Tests | Status |
|----------|-------|--------|
| YAML Config Integrity | 12 | PASS |
| Live Process Inspection | 1 | PASS |
| CompletionService | 3 | PASS |
| CascadingSectionService | 5 | PASS |
| DependencyWiringService | 4 | PASS |
| EntityCreationService | 9 | PASS |
| Init Action Handlers | 5 | PASS |
| LifecycleEngine Integration | 11 | PASS |
| PipelineAutoCompletionService | 3 | PASS |
| Edge Cases / Adversarial | 29 | PASS |

**No defects found** in lifecycle engine hardening.

---

## Recommendations

### Ship with Caveats (CONDITIONAL GO)

The Entity Write API is production-ready with the following caveats:

1. **D-EW-001**: Do NOT rely on `include_updated=True` returning accurate post-write values. If callers need confirmed values, re-fetch with a separate client.

2. **D-EW-002**: Avoid enum fields with numeric option names until fix is deployed. Currently affects only "Algo Version" field.

3. **D-EW-003**: The `algo_version` field on Offer model is misconfigured. Either update the model or avoid writing to this field.

### Pre-Release Actions (RECOMMENDED)

| Priority | Action | Effort |
|----------|--------|--------|
| P1 | Fix D-EW-002 (numeric enum GID check) | 30 min |
| P1 | Fix D-EW-001 (cache invalidation) | 30 min |
| P2 | Fix D-EW-003 (model type mismatch) | 15 min |
| P2 | Update unit tests to cover numeric enum names | 1 hr |

### Documentation Updates

- Add warning to `include_updated` parameter docstring about cache coherence
- Document known issues in API changelog

---

## Test Artifacts

| Artifact | Location |
|----------|----------|
| Test File | `tests/integration/test_entity_write_smoke.py` |
| This Report | `docs/testing/TEST-entity-write-api.md` |
| Lifecycle Tests | `tests/integration/test_lifecycle_smoke.py` |

---

*Generated by QA Adversary (Claude Opus 4.6) - 2026-02-11*
