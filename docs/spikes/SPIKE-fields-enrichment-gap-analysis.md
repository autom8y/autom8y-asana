# SPIKE: Fields Enrichment Gap Analysis

**Date**: 2026-01-10
**Status**: Complete
**Timebox**: 30 minutes

## Question

What is required to wire up the `fields` parameter in resolution requests to return additional entity data beyond just GIDs?

## Decision This Informs

Implementation plan for returning enriched field data (name, vertical, etc.) alongside GIDs in resolution responses.

## Current State

### What's Implemented

| Component | Status | Location |
|-----------|--------|----------|
| `fields` parameter in API request | ✅ Accepted | `routes/resolver.py:162` |
| Field validation against schema | ✅ Works | `routes/resolver.py:476-487` |
| `filter_result_fields()` function | ✅ Exists | `resolver.py:564-616` |
| `ResolutionResult.match_context` | ✅ Defined | `resolution_result.py:46` |
| `ResolutionResult.from_gids(context=)` | ✅ Factory exists | `resolution_result.py:94-115` |
| `to_dict()` includes context | ✅ Works | `resolution_result.py:144-145` |
| Tests for match_context | ✅ Coverage | `test_resolution_result.py:131-151` |

### What's NOT Wired Up

| Gap | Location | Issue |
|-----|----------|-------|
| Index only stores GIDs | `dynamic_index.py:244-245` | No row data retained |
| Strategy ignores DataFrame rows | `universal_strategy.py:150-151` | Only calls `index.lookup()` |
| API discards match_context | `routes/resolver.py:540-547` | Not passed to response model |
| Response model lacks data field | `routes/resolver.py:191-208` | No field for extra data |

## Gap Analysis

### Gap 1: DynamicIndex Only Stores GIDs

**Current**:
```python
# dynamic_index.py:244-245
gid = str(row[value_column])
lookup[key.cache_key].append(gid)  # Only GID stored
```

**Problem**: The index discards all row data except GIDs. To return fields, we'd need to either:
- **Option A**: Store full row dicts in index (memory intensive)
- **Option B**: Do secondary DataFrame lookup using GIDs (extra step)

**Recommendation**: **Option B** - Post-lookup enrichment from DataFrame.

### Gap 2: UniversalResolutionStrategy Doesn't Enrich Results

**Current**:
```python
# universal_strategy.py:150-151
gids = index.lookup(normalized)
results.append(ResolutionResult.from_gids(gids))  # No context passed
```

**Required Change**:
```python
gids = index.lookup(normalized)
if requested_fields and df is not None:
    context = self._enrich_from_dataframe(df, gids, requested_fields)
    results.append(ResolutionResult.from_gids(gids, context=context))
else:
    results.append(ResolutionResult.from_gids(gids))
```

### Gap 3: API Route Doesn't Pass `fields` to Strategy

**Current**:
```python
# routes/resolver.py:514-518
resolution_results = await strategy.resolve(
    criteria=criteria_dicts,
    project_gid=project_gid,
    client=client,
)
```

**Required Change**:
```python
resolution_results = await strategy.resolve(
    criteria=criteria_dicts,
    project_gid=project_gid,
    client=client,
    requested_fields=request_body.fields,  # NEW
)
```

### Gap 4: API Response Model Lacks Data Field

**Current**:
```python
# routes/resolver.py:191-208
class ResolutionResultModel(BaseModel):
    gid: str | None
    gids: list[str] | None = None
    match_count: int = 0
    error: str | None = None
    # No field for additional data!
```

**Required Change**:
```python
class ResolutionResultModel(BaseModel):
    gid: str | None
    gids: list[str] | None = None
    match_count: int = 0
    error: str | None = None
    data: list[dict[str, Any]] | None = None  # NEW: Field data per match
```

### Gap 5: API Route Doesn't Map match_context to Response

**Current**:
```python
# routes/resolver.py:540-547
results = [
    ResolutionResultModel(
        gid=r.gid,
        gids=list(r.gids) if r.gids else None,
        match_count=r.match_count,
        error=r.error,
        # match_context is ignored!
    )
    for r in resolution_results
]
```

**Required Change**:
```python
results = [
    ResolutionResultModel(
        gid=r.gid,
        gids=list(r.gids) if r.gids else None,
        match_count=r.match_count,
        error=r.error,
        data=list(r.match_context) if r.match_context else None,  # NEW
    )
    for r in resolution_results
]
```

## Implementation Plan

### Files to Modify

| File | Changes | LOC Est. |
|------|---------|----------|
| `universal_strategy.py` | Add `requested_fields` param, add enrichment method | ~40 |
| `routes/resolver.py` | Update model, pass fields, map context | ~15 |
| `tests/unit/services/test_universal_strategy.py` | Add enrichment tests | ~50 |
| `tests/api/test_routes_resolver.py` | Add fields request tests | ~30 |

### Implementation Steps

1. **Update `UniversalResolutionStrategy.resolve()` signature**
   ```python
   async def resolve(
       self,
       criteria: list[dict[str, Any]],
       project_gid: str,
       client: "AsanaClient",
       requested_fields: list[str] | None = None,  # NEW
   ) -> list[ResolutionResult]:
   ```

2. **Add enrichment method to strategy**
   ```python
   def _enrich_from_dataframe(
       self,
       df: "pl.DataFrame",
       gids: list[str],
       fields: list[str],
   ) -> list[dict[str, Any]]:
       """Extract field values from DataFrame for matched GIDs."""
       # Filter DF to matching GIDs
       # Select only requested fields + gid
       # Return list of dicts
   ```

3. **Wire enrichment into resolve loop**
   - After `index.lookup()`, if `requested_fields` and `df` available
   - Call `_enrich_from_dataframe()`
   - Pass result as `context` to `ResolutionResult.from_gids()`

4. **Update `ResolutionResultModel`**
   - Add `data: list[dict[str, Any]] | None = None`

5. **Update route to pass fields**
   - Pass `request_body.fields` to `strategy.resolve()`
   - Map `r.match_context` to `data` in response model

6. **Apply `filter_result_fields` if needed**
   - The enrichment already filters to requested fields
   - But can use for validation

### Example Response After Implementation

**Request**:
```json
POST /v1/resolve/unit
{
  "criteria": [{"phone": "+14242690670", "vertical": "chiropractic"}],
  "fields": ["name", "vertical", "office_phone"]
}
```

**Response**:
```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "data": [
        {
          "gid": "1234567890123456",
          "name": "Total Vitality Group",
          "vertical": "chiropractic",
          "office_phone": "+14242690670"
        }
      ]
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 0,
    "entity_type": "unit",
    "project_gid": "1201081073731555"
  }
}
```

## Performance Considerations

### Current Flow (GID-only)
```
criterion → normalize → index.lookup() → GIDs → response
```

### With Field Enrichment
```
criterion → normalize → index.lookup() → GIDs → df.filter(gid in GIDs).select(fields) → response
```

**Impact**:
- Additional O(m) DataFrame filter where m = number of matches
- Polars filter is highly optimized (lazy evaluation)
- Only runs when `fields` is specified
- Existing GID-only requests unchanged

## Complexity Assessment

| Metric | Value |
|--------|-------|
| Files changed | 4 |
| New methods | 1 (`_enrich_from_dataframe`) |
| API contract change | Additive (backwards compatible) |
| Risk level | Low (all additions, no breaking changes) |
| Estimated effort | 2-3 hours |

## Recommendation

**Proceed with implementation.** The infrastructure is 80% in place:
- `ResolutionResult.match_context` already designed for this
- `filter_result_fields()` validation already exists
- Tests for context handling already exist

The remaining work is wiring:
1. Add `requested_fields` parameter to strategy
2. Implement DataFrame enrichment method
3. Update API response model
4. Map match_context to response

This is a straightforward feature completion, not architectural change.

## Follow-Up Actions

| Action | Priority | Owner |
|--------|----------|-------|
| Create TDD for fields enrichment | High | architect |
| Implement `_enrich_from_dataframe()` | High | principal-engineer |
| Update API models and route | High | principal-engineer |
| Add integration tests | Medium | qa-adversary |
| Update demo script | Low | - |
