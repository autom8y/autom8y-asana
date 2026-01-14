# PRD: Entity Query Endpoint

## Metadata

| Field | Value |
|-------|-------|
| **PRD ID** | PRD-entity-query-endpoint |
| **Status** | Draft |
| **Created** | 2026-01-14 |
| **Author** | Requirements Analyst |
| **Impact** | low |
| **Impact Categories** | N/A |

---

## Overview

Add a new `POST /v1/query/{entity_type}` endpoint that enables list/filter operations on the pre-warmed DataFrame cache. This complements the existing `/v1/resolve/{entity_type}` batch resolution endpoint by providing a way to query entities without knowing specific lookup keys upfront.

---

## Background

### Current State

The existing `/v1/resolve/{entity_type}` endpoint provides **batch resolution** - mapping N lookup criteria to N results in input order. This serves the use case of "I have specific identifiers, give me the corresponding GIDs."

However, there is no way to **query/list** entities with arbitrary filtering from the pre-warmed DataFrame cache. Common scenarios requiring this capability:

1. "Give me all offers in the ACTIVE section"
2. "List all contacts with a specific vertical"
3. "Find all units modified in the last 24 hours"

### Why Two Endpoints

| Aspect | `/v1/resolve/{entity}` (Existing) | `/v1/query/{entity}` (New) |
|--------|-----------------------------------|----------------------------|
| **Purpose** | Batch key-to-GID resolution | List/filter entities |
| **Input** | N criteria (lookup keys) | Single `where` clause |
| **Output** | N results (same order as input) | M matching records |
| **Semantics** | 1:1 mapping, order preserved | Set query, order undefined |
| **Use Case** | "I have 100 phone+vertical pairs, find each GID" | "Give me all offers in ACTIVE section" |
| **Result Count** | Always N (one per criterion, may be null) | Variable (0 to all matching) |

### Technical Context

The infrastructure required is largely in place:

| Component | Location | Status |
|-----------|----------|--------|
| DataFrameCache | `cache/dataframe_cache.py` | Ready - tiered storage singleton |
| UniversalResolutionStrategy._get_dataframe() | `services/universal_strategy.py` | Ready - cache access method |
| SchemaRegistry | `dataframes/models/registry.py` | Ready - entity schema definitions |
| EntityProjectRegistry | `services/resolver.py` | Ready - entity-to-project mapping |
| S2S JWT Authentication | `api/routes/internal.py` | Ready - require_service_claims |

---

## User Stories

### US-001: Query Offers by Section

**As a** n8n workflow developer
**I want to** retrieve all Offer entities from a specific section
**So that** I can build automated reporting without knowing specific lookup keys upfront

**Acceptance Criteria**:
- [ ] `POST /v1/query/offer` accepts `where.section` filter
- [ ] Returns all offers matching the section filter
- [ ] Response includes cascade-resolved fields (office_phone, vertical)
- [ ] Data comes from pre-warmed cache (no direct Asana API calls)

### US-002: Select Specific Fields

**As an** API consumer
**I want to** specify which fields to include in the response
**So that** I can reduce payload size and focus on relevant data

**Acceptance Criteria**:
- [ ] Optional `select` array limits returned fields
- [ ] When omitted, returns default field set (gid, name, section)
- [ ] Invalid field names return 422 with available fields
- [ ] `gid` is always included regardless of select

### US-003: Paginate Large Result Sets

**As an** API consumer
**I want to** paginate through large result sets
**So that** I can handle entity types with thousands of records

**Acceptance Criteria**:
- [ ] `limit` parameter controls max results per page (default 100, max 1000)
- [ ] `offset` parameter enables pagination
- [ ] Response `meta.total_count` indicates total matching records
- [ ] Empty result set returns 200 with empty `data` array

### US-004: Query Any Registered Entity Type

**As a** developer integrating with the autom8_asana API
**I want to** query any entity type registered in SchemaRegistry
**So that** I have a consistent interface across all entity types

**Acceptance Criteria**:
- [ ] Supports: unit, business, offer, contact, asset_edit, asset_edit_holder
- [ ] Unknown entity types return 404 with available types
- [ ] Entity type determines available filter and select fields

### US-005: Filter by Multiple Criteria

**As an** API consumer
**I want to** filter by multiple field values simultaneously
**So that** I can narrow down results to specific subsets

**Acceptance Criteria**:
- [ ] Multiple fields in `where` clause are AND-ed together
- [ ] Supports equality filtering on any schema column
- [ ] Returns only records matching ALL specified criteria

---

## Functional Requirements

### Must Have

#### FR-001: Query Endpoint

The API shall expose `POST /v1/query/{entity_type}` where `entity_type` matches any type registered in SchemaRegistry:

```
POST /v1/query/unit
POST /v1/query/business
POST /v1/query/offer
POST /v1/query/contact
POST /v1/query/asset_edit
POST /v1/query/asset_edit_holder
```

#### FR-002: Request Schema

```json
{
  "where": {
    "section": "ACTIVE",
    "vertical": "dental"
  },
  "select": ["gid", "name", "office_phone", "vertical", "section"],
  "limit": 100,
  "offset": 0
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `where` | `object` | No | `{}` | Filter criteria (AND semantics) |
| `select` | `array[string]` | No | `["gid", "name", "section"]` | Fields to include |
| `limit` | `integer` | No | 100 | Max results per page (1-1000) |
| `offset` | `integer` | No | 0 | Skip N results for pagination |

#### FR-003: Response Schema

```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Acme Dental Offer",
      "office_phone": "+15551234567",
      "vertical": "dental",
      "section": "ACTIVE"
    }
  ],
  "meta": {
    "total_count": 47,
    "limit": 100,
    "offset": 0,
    "entity_type": "offer",
    "project_gid": "1143843662099250"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data` | `array[object]` | Matching records with selected fields |
| `meta.total_count` | `integer` | Total matching records (before pagination) |
| `meta.limit` | `integer` | Limit used for this request |
| `meta.offset` | `integer` | Offset used for this request |
| `meta.entity_type` | `string` | Entity type queried |
| `meta.project_gid` | `string` | Project GID used |

#### FR-004: Cache-Based Resolution

The endpoint shall use the existing DataFrameCache singleton:

1. Get project GID from EntityProjectRegistry for entity type
2. Call `DataFrameCache.get_async(project_gid, entity_type)` to retrieve cached DataFrame
3. Apply `where` filters using Polars DataFrame operations
4. Select requested columns
5. Apply `limit`/`offset` pagination
6. Return results

No direct Asana API calls shall be made for query operations.

#### FR-005: S2S Authentication

The endpoint shall require service token (S2S JWT) authentication:

- Reuse existing `require_service_claims` dependency from resolver endpoint
- PAT tokens rejected with 401 `SERVICE_TOKEN_REQUIRED`
- Log caller service name for audit

#### FR-006: Input Validation

- `entity_type`: Must be registered in SchemaRegistry
- `where` field names: Must exist in entity schema
- `select` field names: Must exist in entity schema
- `limit`: Integer 1-1000
- `offset`: Integer >= 0

#### FR-007: Equality Filtering Only (v1)

Version 1 supports only equality filtering:

```json
{"where": {"section": "ACTIVE"}}  // section == "ACTIVE"
{"where": {"vertical": "dental", "section": "ACTIVE"}}  // vertical == "dental" AND section == "ACTIVE"
```

Complex operators (>, <, LIKE, IN, OR) are out of scope for v1.

### Should Have

#### FR-008: Empty Where Returns All (with Pagination)

When `where` is empty or omitted:

```json
{"limit": 100, "offset": 0}
```

Return all records for the entity type, subject to pagination limits.

#### FR-009: Consistent Field Casing

- Accept camelCase or snake_case in request (normalize to snake_case internally)
- Return snake_case in response (consistent with schema definitions)

#### FR-010: Cache Miss Handling

If DataFrame is not in cache:

1. Return 503 `CACHE_NOT_WARMED` with message indicating retry after cache warm
2. Do NOT trigger synchronous cache build (query endpoint is read-only)

### Could Have

#### FR-011: Sort Parameter

```json
{
  "where": {"section": "ACTIVE"},
  "sort": {"field": "name", "direction": "asc"}
}
```

Deferred to v2 - current implementation returns results in cache order.

#### FR-012: Field Aliasing

Support schema-aware field aliasing (e.g., `phone` -> `office_phone`) consistent with resolve endpoint.

Deferred to v2 - use canonical field names for now.

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target |
|--------|--------|
| Query latency (cache hit, <100 results) | < 50ms |
| Query latency (cache hit, 1000 results) | < 200ms |
| Memory overhead per request | < 5MB |
| No additional Asana API calls | 0 calls |

### NFR-002: Reliability

| Metric | Target |
|--------|--------|
| Availability | 99.9% (matches API SLA) |
| Error rate (excluding client errors) | < 0.1% |
| Cache-dependent availability | Graceful 503 on cache miss |

### NFR-003: Security

- S2S JWT authentication required (no PAT support)
- Request/response logging with PII masking
- Rate limiting: inherit global API rate limits

### NFR-004: Observability

Structured logging with:
- `request_id`: Correlation ID
- `entity_type`: Queried entity type
- `where_fields`: Fields used in filter (not values)
- `result_count`: Number of matching records
- `duration_ms`: Query latency
- `cache_status`: hit/miss
- `caller_service`: Service name from JWT

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Empty `where` clause | Return all records (paginated) |
| `where` with non-existent value | Return empty `data` array with `total_count: 0` |
| Unknown entity_type | Return 404 with available entity types |
| Unknown field in `where` | Return 422 with available field names |
| Unknown field in `select` | Return 422 with available field names |
| `limit` > 1000 | Clamp to 1000, proceed |
| `limit` < 1 | Return 422 validation error |
| `offset` > total_count | Return empty `data` with correct `total_count` |
| Cache not warmed for entity | Return 503 `CACHE_NOT_WARMED` |
| Project not registered for entity | Return 503 `PROJECT_NOT_CONFIGURED` |
| Concurrent requests to same entity | Both use same cached DataFrame (thread-safe) |
| DataFrame has null values in filter column | Null != any filter value (excluded from results) |

---

## Success Criteria

- [ ] `POST /v1/query/offer` with `where.section=ACTIVE` returns offers with cascade fields populated
- [ ] Response includes `office_phone` and `vertical` from pre-warmed cache (not NULL for populated records)
- [ ] Existing `/v1/resolve/offer` endpoint unchanged (backwards compatible)
- [ ] Query uses DataFrameCache singleton - no redundant API calls to Asana
- [ ] Supports all entity types registered in SchemaRegistry (unit, business, offer, contact, asset_edit, asset_edit_holder)
- [ ] Standard pagination via `limit`/`offset` works correctly
- [ ] Total count in metadata accurate regardless of pagination
- [ ] Performance targets met: <50ms for typical queries
- [ ] Integration tests cover all entity types
- [ ] API documentation updated with new endpoint

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Complex query operators (>, <, LIKE, IN, OR) | Keep v1 simple; equality sufficient for initial use cases |
| Real-time cache invalidation | Use existing TTL-based cache invalidation |
| Sort/order by clause | Deferred to v2; cache order sufficient for v1 |
| Aggregation queries (COUNT, SUM, GROUP BY) | Not needed for initial use cases |
| Cross-entity joins | Each query targets single entity type |
| Modifying /v1/resolve endpoint | Separate concern, intentionally unchanged |
| GraphQL interface | REST sufficient for current consumers |
| Streaming/cursor-based pagination | Offset pagination sufficient for cache sizes |

---

## Open Questions

*All questions resolved - ready for Architecture handoff.*

1. ~~Should query support nested field filtering (e.g., `where.platforms[0]="facebook"`)?~~ **Resolved**: No, v1 supports only top-level equality. List fields can be filtered by exact match of entire list.

2. ~~What happens if cache is being rebuilt during query?~~ **Resolved**: DataFrameCache uses request coalescing and returns stale data during rebuild. If no cache exists at all, return 503.

3. ~~Should query endpoint trigger cache warm on miss?~~ **Resolved**: No, query is read-only. Return 503 and let scheduled cache warmer or resolve endpoint populate cache.

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| DataFrameCache singleton | Implemented | `cache/dataframe_cache.py` |
| SchemaRegistry | Implemented | Entity schema definitions |
| EntityProjectRegistry | Implemented | Entity to project mapping |
| UniversalResolutionStrategy._get_dataframe() | Implemented | Cache access pattern |
| S2S JWT validation | Implemented | `require_service_claims` |
| Lambda Cache Warmer | Implemented | Ensures cache is populated |

---

## Appendix A: Supported Entity Types and Fields

### Unit

| Field | Type | Filterable | Description |
|-------|------|------------|-------------|
| gid | Utf8 | Yes | Task identifier |
| name | Utf8 | Yes | Task name |
| section | Utf8 | Yes | Section name |
| office_phone | Utf8 | Yes | Office phone (E.164) |
| vertical | Utf8 | Yes | Business vertical |
| mrr | Utf8 | Yes | Monthly recurring revenue |
| weekly_ad_spend | Utf8 | Yes | Weekly advertising spend |

### Offer

| Field | Type | Filterable | Description |
|-------|------|------------|-------------|
| gid | Utf8 | Yes | Task identifier |
| name | Utf8 | Yes | Offer name |
| section | Utf8 | Yes | Section name (e.g., ACTIVE) |
| office_phone | Utf8 | Yes | Office phone (cascade from Business) |
| vertical | Utf8 | Yes | Business vertical (cascade) |
| offer_id | Utf8 | Yes | Offer identifier |
| specialty | Utf8 | Yes | Business specialty |
| platforms | List[Utf8] | Yes* | Platform list (*exact match) |
| language | Utf8 | Yes | Offer language |
| cost | Utf8 | Yes | Offer cost |
| mrr | Utf8 | Yes | MRR (cascade from Unit) |

### Contact

| Field | Type | Filterable | Description |
|-------|------|------------|-------------|
| gid | Utf8 | Yes | Task identifier |
| name | Utf8 | Yes | Contact name |
| section | Utf8 | Yes | Section name |
| email | Utf8 | Yes | Contact email |

### Business

| Field | Type | Filterable | Description |
|-------|------|------------|-------------|
| gid | Utf8 | Yes | Task identifier |
| name | Utf8 | Yes | Business name |
| section | Utf8 | Yes | Section name |
| office_phone | Utf8 | Yes | Office phone |
| vertical | Utf8 | Yes | Business vertical |

---

## Appendix B: Request/Response Examples

### Query Offers by Section

**Request**:
```http
POST /v1/query/offer HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "where": {
    "section": "ACTIVE"
  },
  "select": ["gid", "name", "office_phone", "vertical", "section"],
  "limit": 100,
  "offset": 0
}
```

**Response**:
```json
{
  "data": [
    {
      "gid": "1234567890123456",
      "name": "Acme Dental - Facebook Campaign",
      "office_phone": "+15551234567",
      "vertical": "dental",
      "section": "ACTIVE"
    },
    {
      "gid": "1234567890123457",
      "name": "Beta Medical - Google Ads",
      "office_phone": "+15559876543",
      "vertical": "medical",
      "section": "ACTIVE"
    }
  ],
  "meta": {
    "total_count": 47,
    "limit": 100,
    "offset": 0,
    "entity_type": "offer",
    "project_gid": "1143843662099250"
  }
}
```

### Query Units with Multiple Filters

**Request**:
```http
POST /v1/query/unit HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "where": {
    "vertical": "dental",
    "section": "ACTIVE"
  },
  "select": ["gid", "name", "office_phone", "mrr"],
  "limit": 50
}
```

**Response**:
```json
{
  "data": [
    {
      "gid": "9876543210987654",
      "name": "Acme Dental Unit",
      "office_phone": "+15551234567",
      "mrr": "5000"
    }
  ],
  "meta": {
    "total_count": 1,
    "limit": 50,
    "offset": 0,
    "entity_type": "unit",
    "project_gid": "1201081073731555"
  }
}
```

### Query All Contacts (No Filter)

**Request**:
```http
POST /v1/query/contact HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "select": ["gid", "name", "email"],
  "limit": 100,
  "offset": 200
}
```

**Response**:
```json
{
  "data": [
    {
      "gid": "1111111111111111",
      "name": "John Smith",
      "email": "john@example.com"
    },
    {
      "gid": "2222222222222222",
      "name": "Jane Doe",
      "email": "jane@example.com"
    }
  ],
  "meta": {
    "total_count": 523,
    "limit": 100,
    "offset": 200,
    "entity_type": "contact",
    "project_gid": "1200775689604552"
  }
}
```

### Error Response: Unknown Entity Type

**Request**:
```http
POST /v1/query/unknown HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{}
```

**Response** (404):
```json
{
  "error": "UNKNOWN_ENTITY_TYPE",
  "message": "Unknown entity type: unknown",
  "available_types": ["asset_edit", "asset_edit_holder", "business", "contact", "offer", "unit"]
}
```

### Error Response: Invalid Field

**Request**:
```http
POST /v1/query/offer HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "where": {
    "invalid_field": "value"
  }
}
```

**Response** (422):
```json
{
  "error": "INVALID_FIELD",
  "message": "Unknown field 'invalid_field' in where clause",
  "available_fields": ["gid", "name", "section", "office_phone", "vertical", "offer_id", "specialty", "platforms", "language", "cost", "mrr", "weekly_ad_spend"]
}
```

### Error Response: Cache Not Warmed

**Request**:
```http
POST /v1/query/offer HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "where": {"section": "ACTIVE"}
}
```

**Response** (503):
```json
{
  "error": "CACHE_NOT_WARMED",
  "message": "DataFrame cache not available for entity type: offer. Cache warming may be in progress. Please retry after a few minutes.",
  "entity_type": "offer"
}
```

---

## Appendix C: Implementation Notes

### Recommended Module Structure

```
src/autom8_asana/api/routes/query.py  # New file
```

### Key Integration Points

1. **Cache Access**: Reuse `get_dataframe_cache_provider()` from `cache/dataframe/factory.py`
2. **Schema Discovery**: Use `SchemaRegistry.get_instance().get_schema(entity_type.capitalize())`
3. **Project Mapping**: Use `EntityProjectRegistry.get_instance().get_project_gid(entity_type)`
4. **Authentication**: Reuse `require_service_claims` from `api/routes/internal.py`

### DataFrame Filtering Pattern

```python
# Pseudocode for filter application
df = cache.get_async(project_gid, entity_type).dataframe

# Apply where filters
for field, value in where.items():
    df = df.filter(pl.col(field) == value)

# Get total before pagination
total_count = len(df)

# Apply pagination
df = df.slice(offset, limit)

# Select fields
df = df.select(select_fields)
```
