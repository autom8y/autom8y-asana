# TDD: Fields Enrichment for Resolution API

**TDD ID**: TDD-FIELDS-ENRICHMENT-001
**Version**: 1.0
**Date**: 2026-01-10
**Author**: Architect
**Status**: DRAFT
**PRD Reference**: N/A (Feature completion from SPIKE-fields-enrichment-gap-analysis)
**Sprint**: Fields Enrichment
**Spike Reference**: SPIKE-fields-enrichment-gap-analysis

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Goals and Non-Goals](#goals-and-non-goals)
4. [Proposed Architecture](#proposed-architecture)
5. [Component Designs](#component-designs)
6. [Interface Contracts](#interface-contracts)
7. [Data Flow Diagrams](#data-flow-diagrams)
8. [Non-Functional Considerations](#non-functional-considerations)
9. [Test Strategy](#test-strategy)
10. [Implementation Phases](#implementation-phases)
11. [Risk Assessment](#risk-assessment)
12. [ADRs](#adrs)
13. [Success Criteria](#success-criteria)

---

## Overview

This TDD specifies the technical design for wiring up the `fields` parameter in the resolution API to return additional entity data beyond just GIDs. The infrastructure is 80% complete; this design covers the remaining wiring needed to enable field enrichment.

### Solution Summary

| Component | Change Type | Purpose |
|-----------|-------------|---------|
| `UniversalResolutionStrategy.resolve()` | Modified | Accept `requested_fields` parameter |
| `UniversalResolutionStrategy._enrich_from_dataframe()` | New | Extract field values from DataFrame |
| `ResolutionResultModel` | Modified | Add `data` field for enriched data |
| `resolve_entities` route | Modified | Pass `fields` to strategy, map `match_context` to response |

### Traceability

| Spike Gap | Component | Section |
|-----------|-----------|---------|
| Gap 2: Strategy ignores fields | `UniversalResolutionStrategy` | 5.1 |
| Gap 3: API doesn't pass fields | Route modification | 5.2 |
| Gap 4: Response model lacks data | `ResolutionResultModel` | 5.2 |
| Gap 5: match_context not mapped | Route response mapping | 5.2 |

---

## Problem Statement

### Current State

The `fields` parameter is accepted in resolution requests and validated against the schema, but the field values are never returned in the response.

**What's Implemented**:

| Component | Status | Location |
|-----------|--------|----------|
| `fields` parameter in API request | Accepted | `routes/resolver.py:162` |
| Field validation against schema | Works | `routes/resolver.py:476-487` |
| `filter_result_fields()` function | Exists | `resolver.py:564-616` |
| `ResolutionResult.match_context` | Defined | `resolution_result.py:46` |
| `ResolutionResult.from_gids(context=)` | Factory exists | `resolution_result.py:94-115` |

**What's NOT Wired Up**:

| Gap | Location | Issue |
|-----|----------|-------|
| Strategy ignores fields | `universal_strategy.py:80-85` | `resolve()` has no `requested_fields` param |
| API discards match_context | `routes/resolver.py:540-547` | Not mapped to response model |
| Response model lacks data field | `routes/resolver.py:191-208` | No field for extra data |

### Example Request (Current - Fields Ignored)

```json
POST /v1/resolve/unit
{
  "criteria": [{"phone": "+14242690670", "vertical": "chiropractic"}],
  "fields": ["name", "vertical", "office_phone"]
}
```

**Current Response** (fields ignored):
```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "error": null
    }
  ],
  "meta": { ... }
}
```

---

## Goals and Non-Goals

### Goals

| ID | Goal | Rationale |
|----|------|-----------|
| G1 | Return requested field values in response | Enable callers to get entity data without additional API calls |
| G2 | Zero cost for GID-only requests | Existing behavior unchanged when `fields` not specified |
| G3 | Leverage existing infrastructure | Use `ResolutionResult.match_context` and `filter_result_fields()` |
| G4 | Backwards compatibility | Response structure additive (new `data` field) |
| G5 | Correlation via GID | Always include `gid` in enriched data for result correlation |

### Non-Goals

| ID | Non-Goal | Reason |
|----|----------|--------|
| NG1 | Store fields in DynamicIndex | Memory overhead; post-lookup enrichment is sufficient |
| NG2 | Modify DynamicIndex structure | Index only stores GIDs by design |
| NG3 | Support computed/derived fields | Only schema columns supported |
| NG4 | Field-level caching | DataFrame-level caching sufficient |

---

## Proposed Architecture

### System Diagram

```
POST /v1/resolve/{entity_type}
         |
         | fields: ["name", "vertical"]
         v
+--------------------------------------------------+
|              resolve_entities route               |
|  - Validates fields against schema (existing)    |
|  - Passes fields to strategy (NEW)               |
+--------------------------------------------------+
         |
         v
+--------------------------------------------------+
|          UniversalResolutionStrategy              |
|                                                   |
|  resolve(criteria, project_gid, client,          |
|          requested_fields)  <-- NEW param        |
|                                                   |
|  +-------------------------------------------+   |
|  |            DynamicIndex                   |   |
|  |           index.lookup()                  |   |
|  +-------------------------------------------+   |
|                     |                            |
|                     v GIDs                       |
|  +-------------------------------------------+   |
|  |      _enrich_from_dataframe() <-- NEW    |   |
|  |  - Filter DataFrame by matched GIDs       |   |
|  |  - Select requested fields                |   |
|  |  - Return list of dicts                   |   |
|  +-------------------------------------------+   |
|                     |                            |
|                     v context                    |
|  +-------------------------------------------+   |
|  |   ResolutionResult.from_gids(gids,       |   |
|  |                              context=)    |   |
|  +-------------------------------------------+   |
+--------------------------------------------------+
         |
         v match_context populated
+--------------------------------------------------+
|              Route Response Mapping               |
|  - Maps match_context to data field (NEW)        |
|  - Returns ResolutionResultModel with data       |
+--------------------------------------------------+
```

### Data Flow

```
                    ┌─────────────────┐
                    │  Request with   │
                    │  fields param   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Field Validation│ (existing)
                    │ via schema      │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Strategy.resolve│
                    │ with fields     │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             │
    ┌─────────────────┐                     │
    │  index.lookup() │                     │
    │  returns GIDs   │                     │
    └────────┬────────┘                     │
             │                              │
             ▼                              │
    ┌─────────────────┐          ┌─────────▼─────────┐
    │ _enrich_from_   │◀─────────│    DataFrame      │
    │   dataframe()   │          │  (from cache)     │
    └────────┬────────┘          └───────────────────┘
             │
             │ context: [{gid, name, vertical}, ...]
             │
             ▼
    ┌─────────────────┐
    │ResolutionResult │
    │ .from_gids(...  │
    │   context=...)  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │   API Response  │
    │   with data     │
    └─────────────────┘
```

---

## Component Designs

### 5.1 UniversalResolutionStrategy Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py`

#### 5.1.1 Updated resolve() Signature

```python
async def resolve(
    self,
    criteria: list[dict[str, Any]],
    project_gid: str,
    client: "AsanaClient",
    requested_fields: list[str] | None = None,  # NEW
) -> list[ResolutionResult]:
    """Resolve criteria to entity GIDs with optional field enrichment.

    Per TDD-FIELDS-ENRICHMENT-001:
    When requested_fields is provided, returns field values from the
    DataFrame for each matched GID via match_context.

    Args:
        criteria: List of criterion dicts.
        project_gid: Target project GID.
        client: AsanaClient for DataFrame building.
        requested_fields: Optional list of field names to return.

    Returns:
        List of ResolutionResult in same order as input.
        If requested_fields provided, match_context contains field data.
    """
```

#### 5.1.2 New Enrichment Method

```python
def _enrich_from_dataframe(
    self,
    df: "pl.DataFrame",
    gids: list[str],
    fields: list[str],
) -> list[dict[str, Any]]:
    """Extract requested field values from DataFrame for matched GIDs.

    Per TDD-FIELDS-ENRICHMENT-001:
    Post-lookup enrichment from DataFrame. Only runs when fields requested.
    Always includes 'gid' in returned data for correlation.

    Args:
        df: Entity DataFrame with all columns.
        gids: List of matched GIDs to enrich.
        fields: Requested field names to extract.

    Returns:
        List of dicts with field values, one per GID in same order.
        Each dict contains 'gid' plus requested fields.
        Returns empty list if no GIDs or DataFrame unavailable.

    Example:
        >>> context = strategy._enrich_from_dataframe(
        ...     df=unit_df,
        ...     gids=["123", "456"],
        ...     fields=["name", "vertical"],
        ... )
        >>> context
        [
            {"gid": "123", "name": "Acme Dental", "vertical": "dental"},
            {"gid": "456", "name": "Beta Medical", "vertical": "medical"},
        ]
    """
    if not gids or df is None:
        return []

    # Ensure gid is always included
    all_fields = list(set(["gid"] + fields))

    # Filter to only columns that exist in DataFrame
    available_columns = set(df.columns)
    valid_fields = [f for f in all_fields if f in available_columns]

    if "gid" not in valid_fields:
        # gid column must exist for filtering
        logger.warning(
            "enrichment_missing_gid_column",
            extra={"entity_type": self.entity_type},
        )
        return []

    try:
        # Filter DataFrame to matching GIDs
        gid_set = set(gids)
        filtered = df.filter(df["gid"].is_in(gid_set))

        # Select only requested fields
        selected = filtered.select(valid_fields)

        # Convert to list of dicts, maintaining GID order
        result_map = {
            row["gid"]: {k: v for k, v in row.items()}
            for row in selected.iter_rows(named=True)
        }

        # Return in same order as input GIDs
        return [result_map.get(gid, {"gid": gid}) for gid in gids]

    except Exception as e:
        logger.warning(
            "enrichment_extraction_failed",
            extra={
                "entity_type": self.entity_type,
                "error": str(e),
                "gid_count": len(gids),
            },
        )
        return []
```

#### 5.1.3 Integration in Resolve Loop

Modify the resolve loop to wire enrichment after lookup:

```python
# In resolve() method, after index.lookup():

# Perform lookup
gids = index.lookup(normalized)

# Enrich if fields requested and DataFrame available
context: list[dict[str, Any]] | None = None
if requested_fields and gids:
    df = self._cached_dataframe or await self._get_dataframe(
        project_gid, client
    )
    if df is not None:
        context = self._enrich_from_dataframe(df, gids, requested_fields)

results.append(ResolutionResult.from_gids(gids, context=context))
```

### 5.2 API Layer Changes

**File**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py`

#### 5.2.1 Updated ResolutionResultModel

```python
class ResolutionResultModel(BaseModel):
    """Single resolution result.

    Per TDD-FIELDS-ENRICHMENT-001: Added data field for enriched field values.

    Attributes:
        gid: First matching GID or None if not found (backwards compat)
        gids: All matching GIDs (multi-match support)
        match_count: Number of matches
        error: Error code if resolution failed
        data: Field data for each match (NEW - only when fields requested)
    """

    model_config = ConfigDict(extra="forbid")

    gid: str | None  # Backwards compatible - first match
    gids: list[str] | None = None  # All matches
    match_count: int = 0
    error: str | None = None
    data: list[dict[str, Any]] | None = None  # NEW: Field data per match
```

#### 5.2.2 Updated Route to Pass Fields

```python
# In resolve_entities(), update the strategy.resolve() call:

async with AsanaClient(token=bot_pat) as client:
    resolution_results = await strategy.resolve(
        criteria=criteria_dicts,
        project_gid=project_gid,
        client=client,
        requested_fields=request_body.fields,  # NEW
    )
```

#### 5.2.3 Updated Response Mapping

```python
# In resolve_entities(), update the result mapping:

# Convert ResolutionResult to ResolutionResultModel
results = [
    ResolutionResultModel(
        gid=r.gid,  # Backwards compat: first match
        gids=list(r.gids) if r.gids else None,
        match_count=r.match_count,
        error=r.error,
        data=list(r.match_context) if r.match_context else None,  # NEW
    )
    for r in resolution_results
]
```

---

## Interface Contracts

### 6.1 Request Schema (Existing)

```json
{
  "criteria": [
    {"phone": "+14242690670", "vertical": "chiropractic"}
  ],
  "fields": ["name", "vertical", "office_phone"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `criteria` | `array[object]` | Yes | Lookup criteria (max 1000 items) |
| `fields` | `array[string]` | No | Field names to return (validated against schema) |

### 6.2 Response Schema (Enhanced)

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "error": null,
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

| Field | Type | Description |
|-------|------|-------------|
| `results[*].gid` | `string\|null` | First match (backwards compat) |
| `results[*].gids` | `array[string]\|null` | All matching GIDs |
| `results[*].match_count` | `integer` | Number of matches |
| `results[*].error` | `string\|null` | Error code if failed |
| `results[*].data` | `array[object]\|null` | **NEW**: Field data per match |
| `results[*].data[*].gid` | `string` | GID for correlation (always included) |
| `results[*].data[*].<field>` | `any` | Requested field value |

### 6.3 Error Responses (Existing)

| Status | Error Code | When |
|--------|------------|------|
| 422 | `INVALID_FIELD` | Requested field not in schema |

Validation already handled by existing `filter_result_fields()` call in route.

### 6.4 UniversalResolutionStrategy.resolve() Contract

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `criteria` | `list[dict[str, Any]]` | Yes | Lookup criteria |
| `project_gid` | `str` | Yes | Target project GID |
| `client` | `AsanaClient` | Yes | For DataFrame building |
| `requested_fields` | `list[str] \| None` | No | **NEW**: Fields to return |

**Returns**: `list[ResolutionResult]` with `match_context` populated when `requested_fields` provided.

---

## Data Flow Diagrams

### 7.1 Request Without Fields (Unchanged)

```
Request (no fields)
        │
        ▼
┌─────────────────┐
│   Strategy      │
│   .resolve()    │
│ requested_fields│
│   = None        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ index.lookup()  │
└────────┬────────┘
         │ GIDs
         ▼
┌─────────────────┐
│ ResolutionResult│
│ .from_gids(gids)│
│ context=None    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Response      │
│   data=null     │
└─────────────────┘
```

### 7.2 Request With Fields (New Flow)

```
Request (fields=["name", "vertical"])
        │
        ▼
┌─────────────────┐
│ Field Validation│ (existing - filter_result_fields)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Strategy.resolve(                 │
│     criteria, project_gid, client,  │
│     requested_fields=["name",       │
│                       "vertical"])  │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ index.lookup()  │
└────────┬────────┘
         │ GIDs: ["123", "456"]
         ▼
┌─────────────────────────────────────┐
│   _enrich_from_dataframe(           │
│     df, gids, ["name", "vertical"]) │
└────────┬────────────────────────────┘
         │
         │ context: [
         │   {gid:"123", name:"A", vertical:"dental"},
         │   {gid:"456", name:"B", vertical:"medical"}
         │ ]
         ▼
┌─────────────────────────────────────┐
│ ResolutionResult.from_gids(         │
│   gids, context=context)            │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Response                          │
│   data: [{gid, name, vertical}, ...]│
└─────────────────────────────────────┘
```

### 7.3 Multi-Match Enrichment

```
Criterion matches 3 GIDs
        │
        ▼
┌─────────────────┐
│ index.lookup()  │
│ returns 3 GIDs  │
└────────┬────────┘
         │ GIDs: ["A", "B", "C"]
         ▼
┌─────────────────────────────────────┐
│   _enrich_from_dataframe(           │
│     df, ["A","B","C"], ["name"])    │
└────────┬────────────────────────────┘
         │
         │ Filter: df.filter(gid in ["A","B","C"])
         │ Select: df.select(["gid", "name"])
         │
         ▼
┌─────────────────────────────────────┐
│   context: [                        │
│     {gid:"A", name:"Acme"},         │
│     {gid:"B", name:"Beta"},         │
│     {gid:"C", name:"Gamma"}         │
│   ]                                 │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Response:                         │
│   gid: "A"         (first)          │
│   gids: ["A","B","C"]               │
│   match_count: 3                    │
│   data: [...] (all 3 enriched)      │
└─────────────────────────────────────┘
```

---

## Non-Functional Considerations

### 8.1 Performance Targets

| Metric | Target | Approach |
|--------|--------|----------|
| GID-only lookup (no fields) | <5ms p95 | Zero additional overhead |
| Enrichment overhead (10 matches) | <10ms | Polars filter is O(m) where m=matches |
| Enrichment overhead (100 matches) | <50ms | DataFrame filter + select |
| Memory per enrichment | ~0 | Uses cached DataFrame (no copy) |

### 8.2 Performance Analysis

**GID-Only Requests** (existing behavior):
- No change to current flow
- `requested_fields=None` skips enrichment entirely
- Zero performance regression

**Enriched Requests**:
- DataFrame filter: O(n) where n = DataFrame rows, but Polars lazy evaluation optimizes this
- Select: O(1) - column selection is metadata operation
- Convert to dicts: O(m) where m = matched rows
- Order preservation: O(m) using dict lookup

**Typical Case** (1-10 matches, 10K row DataFrame):
- Filter: ~1-5ms (Polars optimized)
- Dict conversion: <1ms
- Total enrichment: <10ms additional latency

### 8.3 Memory Efficiency

The design avoids memory overhead by:

1. **Using existing cached DataFrame**: No duplication of data
2. **Post-lookup enrichment**: Only extracts fields when needed
3. **No index modification**: DynamicIndex remains GID-only
4. **Lazy column selection**: Polars doesn't materialize unused columns

### 8.4 Observability

**Logging**:

| Event | Level | When |
|-------|-------|------|
| `enrichment_requested` | DEBUG | Fields parameter provided |
| `enrichment_missing_gid_column` | WARN | DataFrame lacks gid column |
| `enrichment_extraction_failed` | WARN | Polars operation failed |
| `enrichment_complete` | DEBUG | Enrichment succeeded |

**Metrics** (future enhancement):

| Metric | Type | Description |
|--------|------|-------------|
| `resolution_enrichment_duration_ms` | Histogram | Time spent in enrichment |
| `resolution_enrichment_field_count` | Histogram | Number of fields requested |
| `resolution_enrichment_match_count` | Histogram | Matches enriched per request |

---

## Test Strategy

### 9.1 Unit Tests

**Module**: `tests/unit/services/test_universal_strategy.py`

```python
"""Unit tests for UniversalResolutionStrategy field enrichment."""

import pytest
import polars as pl
from unittest.mock import AsyncMock, MagicMock

from autom8_asana.services.universal_strategy import UniversalResolutionStrategy
from autom8_asana.services.dynamic_index import DynamicIndexCache


class TestEnrichFromDataframe:
    """Tests for _enrich_from_dataframe method."""

    def test_enrichment_returns_requested_fields(self):
        """Enrichment returns only requested fields plus gid."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        df = pl.DataFrame({
            "gid": ["123", "456", "789"],
            "name": ["A", "B", "C"],
            "vertical": ["dental", "medical", "chiro"],
            "mrr": [100.0, 200.0, 300.0],
        })

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123", "456"],
            fields=["name", "vertical"],
        )

        assert len(result) == 2
        assert result[0] == {"gid": "123", "name": "A", "vertical": "dental"}
        assert result[1] == {"gid": "456", "name": "B", "vertical": "medical"}
        # mrr not included (not requested)
        assert "mrr" not in result[0]

    def test_enrichment_always_includes_gid(self):
        """GID is always included even if not in requested fields."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        df = pl.DataFrame({
            "gid": ["123"],
            "name": ["Test"],
        })

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123"],
            fields=["name"],  # gid not in list
        )

        assert "gid" in result[0]
        assert result[0]["gid"] == "123"

    def test_enrichment_preserves_gid_order(self):
        """Results returned in same order as input GIDs."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        df = pl.DataFrame({
            "gid": ["123", "456", "789"],
            "name": ["A", "B", "C"],
        })

        # Request in different order than DataFrame
        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["789", "123", "456"],
            fields=["name"],
        )

        assert result[0]["gid"] == "789"
        assert result[1]["gid"] == "123"
        assert result[2]["gid"] == "456"

    def test_enrichment_handles_missing_gid(self):
        """Missing GID returns dict with just gid."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        df = pl.DataFrame({
            "gid": ["123"],
            "name": ["A"],
        })

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123", "999"],  # 999 not in DataFrame
            fields=["name"],
        )

        assert len(result) == 2
        assert result[0] == {"gid": "123", "name": "A"}
        assert result[1] == {"gid": "999"}  # Only gid returned

    def test_enrichment_empty_gids(self):
        """Empty GID list returns empty result."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        df = pl.DataFrame({"gid": ["123"], "name": ["A"]})

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=[],
            fields=["name"],
        )

        assert result == []

    def test_enrichment_none_dataframe(self):
        """None DataFrame returns empty result."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        result = strategy._enrich_from_dataframe(
            df=None,
            gids=["123"],
            fields=["name"],
        )

        assert result == []

    def test_enrichment_skips_missing_columns(self):
        """Missing columns in DataFrame are skipped gracefully."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        df = pl.DataFrame({
            "gid": ["123"],
            "name": ["A"],
            # no 'vertical' column
        })

        result = strategy._enrich_from_dataframe(
            df=df,
            gids=["123"],
            fields=["name", "vertical"],  # vertical doesn't exist
        )

        assert result[0] == {"gid": "123", "name": "A"}
        # vertical not in result (column doesn't exist)


class TestResolveWithFields:
    """Tests for resolve() with requested_fields."""

    @pytest.mark.asyncio
    async def test_resolve_without_fields_no_enrichment(self):
        """Resolve without fields returns no data."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        # Mock the necessary components
        mock_client = AsyncMock()
        strategy._cached_dataframe = pl.DataFrame({
            "gid": ["123"],
            "name": ["Test"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })

        # Pre-build index
        from autom8_asana.services.dynamic_index import DynamicIndex
        index = DynamicIndex.from_dataframe(
            strategy._cached_dataframe,
            ["office_phone", "vertical"],
        )
        strategy.index_cache.put("unit", ["office_phone", "vertical"], index)

        results = await strategy.resolve(
            criteria=[{"office_phone": "+15551234567", "vertical": "dental"}],
            project_gid="test-project",
            client=mock_client,
            requested_fields=None,  # No fields
        )

        assert len(results) == 1
        assert results[0].gid == "123"
        assert results[0].match_context is None

    @pytest.mark.asyncio
    async def test_resolve_with_fields_returns_data(self):
        """Resolve with fields returns enriched data."""
        strategy = UniversalResolutionStrategy(
            entity_type="unit",
            index_cache=DynamicIndexCache(),
        )

        mock_client = AsyncMock()
        strategy._cached_dataframe = pl.DataFrame({
            "gid": ["123"],
            "name": ["Test Company"],
            "office_phone": ["+15551234567"],
            "vertical": ["dental"],
        })

        from autom8_asana.services.dynamic_index import DynamicIndex
        index = DynamicIndex.from_dataframe(
            strategy._cached_dataframe,
            ["office_phone", "vertical"],
        )
        strategy.index_cache.put("unit", ["office_phone", "vertical"], index)

        results = await strategy.resolve(
            criteria=[{"office_phone": "+15551234567", "vertical": "dental"}],
            project_gid="test-project",
            client=mock_client,
            requested_fields=["name"],  # Request name field
        )

        assert len(results) == 1
        assert results[0].gid == "123"
        assert results[0].match_context is not None
        assert len(results[0].match_context) == 1
        assert results[0].match_context[0]["gid"] == "123"
        assert results[0].match_context[0]["name"] == "Test Company"
```

### 9.2 Integration Tests

**Module**: `tests/integration/api/test_resolver_fields.py`

```python
"""Integration tests for resolution API field enrichment."""

import pytest
from httpx import AsyncClient


class TestResolverFieldsEnrichment:
    """Integration tests for fields parameter."""

    @pytest.mark.asyncio
    async def test_resolve_with_fields_returns_data(
        self,
        async_client: AsyncClient,
        service_auth_headers: dict,
    ):
        """Request with fields returns data array."""
        response = await async_client.post(
            "/v1/resolve/unit",
            json={
                "criteria": [
                    {"phone": "+15551234567", "vertical": "dental"}
                ],
                "fields": ["name", "vertical"],
            },
            headers=service_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Check data field is present
        result = data["results"][0]
        if result["gid"] is not None:  # If match found
            assert "data" in result
            assert result["data"] is not None
            assert len(result["data"]) == result["match_count"]
            # Each data item has gid for correlation
            for item in result["data"]:
                assert "gid" in item

    @pytest.mark.asyncio
    async def test_resolve_without_fields_no_data(
        self,
        async_client: AsyncClient,
        service_auth_headers: dict,
    ):
        """Request without fields returns no data."""
        response = await async_client.post(
            "/v1/resolve/unit",
            json={
                "criteria": [
                    {"phone": "+15551234567", "vertical": "dental"}
                ],
                # No fields parameter
            },
            headers=service_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        result = data["results"][0]
        assert result.get("data") is None

    @pytest.mark.asyncio
    async def test_invalid_field_returns_422(
        self,
        async_client: AsyncClient,
        service_auth_headers: dict,
    ):
        """Invalid field name returns 422."""
        response = await async_client.post(
            "/v1/resolve/unit",
            json={
                "criteria": [
                    {"phone": "+15551234567", "vertical": "dental"}
                ],
                "fields": ["nonexistent_field"],
            },
            headers=service_auth_headers,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["detail"]["error"] == "INVALID_FIELD"

    @pytest.mark.asyncio
    async def test_multi_match_enriches_all(
        self,
        async_client: AsyncClient,
        service_auth_headers: dict,
    ):
        """Multi-match returns data for each match."""
        # This test requires setup that produces multiple matches
        # for the same criterion

        response = await async_client.post(
            "/v1/resolve/contact",
            json={
                "criteria": [
                    {"email": "test@example.com"}
                ],
                "fields": ["name", "email"],
            },
            headers=service_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        result = data["results"][0]
        if result["match_count"] > 1:
            assert len(result["data"]) == result["match_count"]
            # All data items have unique GIDs
            gids = [item["gid"] for item in result["data"]]
            assert len(gids) == len(set(gids))
```

### 9.3 Test Matrix

| Test Case | Scenario | Expected Result |
|-----------|----------|-----------------|
| TC-001 | Request with `fields` | `data` array populated |
| TC-002 | Request without `fields` | `data` is null (existing behavior) |
| TC-003 | Invalid field name | 422 INVALID_FIELD (existing validation) |
| TC-004 | Multi-match with fields | `data` array has entry per match |
| TC-005 | No matches with fields | `data` is null (no enrichment) |
| TC-006 | Field column missing in DF | Field omitted from result |
| TC-007 | GID not in DataFrame | Returns dict with just gid |
| TC-008 | Performance (10 matches) | Enrichment < 10ms |

---

## Implementation Phases

### Phase 1: Strategy Enhancement (0.5 days)

- [ ] Add `requested_fields` parameter to `resolve()` signature
- [ ] Implement `_enrich_from_dataframe()` method
- [ ] Wire enrichment into resolve loop
- [ ] Add unit tests for enrichment

### Phase 2: API Layer Changes (0.5 days)

- [ ] Add `data` field to `ResolutionResultModel`
- [ ] Pass `fields` to `strategy.resolve()` in route
- [ ] Map `match_context` to `data` in response
- [ ] Add integration tests

### Phase 3: Validation (0.5 days)

- [ ] Manual testing with demo script
- [ ] Performance verification
- [ ] Documentation update

**Total**: 1.5 days

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance regression | Low | Medium | Enrichment only runs when fields requested |
| DataFrame unavailable | Low | Low | Graceful degradation (empty data) |
| Column name mismatch | Low | Low | Skip missing columns, log warning |
| Memory pressure | Very Low | Low | No data copying, uses existing DF |
| Breaking change | Very Low | High | Response change is additive (new field) |

---

## ADRs

### ADR-FIELDS-ENRICHMENT-001: Post-Lookup Enrichment Pattern

**Context**: Should field data be stored in the DynamicIndex or extracted from the DataFrame after lookup?

**Decision**: Extract from DataFrame after lookup (post-lookup enrichment).

**Rationale**:
- **Memory efficiency**: DynamicIndex stores only GIDs (~10KB per 10K entries) vs full row data (~1MB+)
- **Zero cost for GID-only**: No overhead when `fields` not requested
- **Leverages existing cache**: DataFrame already cached by @dataframe_cache decorator
- **Flexible field selection**: Any schema column available, not fixed at index build time

**Consequences**:
- Positive: Memory-efficient, zero overhead for existing callers
- Positive: Any field can be requested without index rebuild
- Negative: Small latency for enrichment (mitigated by Polars performance)
- Neutral: Requires DataFrame to be available for enrichment

### ADR-FIELDS-ENRICHMENT-002: Always Include GID in Enriched Data

**Context**: Should `gid` always be included in the `data` array, or only if explicitly requested?

**Decision**: Always include `gid` in enriched data, regardless of `fields` parameter.

**Rationale**:
- **Correlation**: Callers need to correlate data items with the GID list
- **Multi-match scenarios**: Essential when `match_count > 1`
- **Consistency**: Same structure for all data items
- **No ambiguity**: Clear which data belongs to which match

**Consequences**:
- Positive: Unambiguous correlation between `gids[]` and `data[]`
- Positive: Works naturally with multi-match results
- Negative: Slight response size increase (gid duplicated)
- Neutral: Consistent with existing `context` patterns in codebase

### ADR-FIELDS-ENRICHMENT-003: Graceful Degradation for Missing Data

**Context**: What should happen if a GID is in the index but not in the DataFrame?

**Decision**: Return a dict with only `gid` for missing rows.

**Rationale**:
- **Robustness**: Index and DataFrame could be briefly out of sync
- **Partial success**: Better to return what we have than fail entirely
- **Correlation preserved**: Caller can still correlate by GID
- **Logging**: Warning logged for investigation

**Consequences**:
- Positive: API never fails due to data sync issues
- Positive: Caller always gets a data entry per GID
- Negative: Incomplete data possible (rare edge case)
- Neutral: Logging enables debugging

---

## Success Criteria

### Quantitative

| Metric | Target | Measurement |
|--------|--------|-------------|
| Enrichment latency (10 matches) | < 10ms | Timing in tests |
| GID-only request overhead | 0ms | No code path change |
| Test coverage | > 90% | pytest-cov |
| Response size increase | < 5% for GID-only | No change if fields not requested |

### Qualitative

| Criterion | Validation |
|-----------|------------|
| Fields parameter returns data | Integration test TC-001 |
| Backwards compatible | Existing tests pass |
| GID always in data | Unit test TC-003 |
| Multi-match works | Integration test TC-004 |
| Error handling | Unit tests for edge cases |

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| TDD Document | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-fields-enrichment.md` | Pending |
| Spike Reference | `/Users/tomtenuta/Code/autom8_asana/docs/spikes/SPIKE-fields-enrichment-gap-analysis.md` | Yes |
| Strategy File | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/universal_strategy.py` | Yes |
| Route File | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/api/routes/resolver.py` | Yes |
| Resolution Result | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/services/resolution_result.py` | Yes |

---

## Appendix A: Example Request/Response

### Request

```bash
curl -X POST https://api.example.com/v1/resolve/unit \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": [
      {"phone": "+14242690670", "vertical": "chiropractic"}
    ],
    "fields": ["name", "vertical", "office_phone"]
  }'
```

### Response (Match Found)

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456"],
      "match_count": 1,
      "error": null,
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

### Response (No Match)

```json
{
  "results": [
    {
      "gid": null,
      "gids": null,
      "match_count": 0,
      "error": "NOT_FOUND",
      "data": null
    }
  ],
  "meta": {
    "resolved_count": 0,
    "unresolved_count": 1,
    "entity_type": "unit",
    "project_gid": "1201081073731555"
  }
}
```

### Response (Multi-Match)

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "gids": ["1234567890123456", "9876543210987654"],
      "match_count": 2,
      "error": null,
      "data": [
        {
          "gid": "1234567890123456",
          "name": "Location A",
          "vertical": "dental",
          "office_phone": "+15551234567"
        },
        {
          "gid": "9876543210987654",
          "name": "Location B",
          "vertical": "dental",
          "office_phone": "+15551234567"
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

## Appendix B: Files to Modify

| File | Change Type | Lines Affected |
|------|-------------|----------------|
| `src/autom8_asana/services/universal_strategy.py` | Modify + Add | ~80-85 (signature), ~new method |
| `src/autom8_asana/api/routes/resolver.py` | Modify | ~191-208 (model), ~514-518 (call), ~540-547 (mapping) |
| `tests/unit/services/test_universal_strategy.py` | Add | New test class |
| `tests/integration/api/test_resolver_fields.py` | Add | New test file |

## Appendix C: Existing Infrastructure Reference

| Component | Location | Usage in Design |
|-----------|----------|-----------------|
| `ResolutionResult.match_context` | `resolution_result.py:46` | Store enriched data |
| `ResolutionResult.from_gids(context=)` | `resolution_result.py:94-115` | Factory with context |
| `filter_result_fields()` | `resolver.py:564-616` | Field validation |
| `DynamicIndex.lookup()` | `dynamic_index.py:244-245` | GID lookup |
| `@dataframe_cache` | `cache/dataframe/decorator.py` | DataFrame caching |
