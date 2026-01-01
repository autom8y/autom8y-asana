# PRD: Entity Resolver Generalization

## Overview

Replace the broken `/api/v1/internal/gid-lookup` endpoint with a generalized `POST /v1/resolve/{entity_type}` endpoint supporting four entity types (Unit, Offer, Contact, Business). The new endpoint discovers project GIDs at startup time, eliminating environment variable configuration, and provides dynamic field filtering support.

## Background

### Current State

The existing `/api/v1/internal/gid-lookup` endpoint is hardcoded to resolve only Unit entities within a single project specified via the `UNIT_PROJECT_GID` environment variable. This creates several problems:

1. **Single Entity Type**: Only Unit resolution is supported; Offer, Contact, and Business entities cannot be resolved
2. **Environment Configuration Dependency**: Requires manual `UNIT_PROJECT_GID` configuration per deployment
3. **No Project Discovery**: Project GIDs are statically configured rather than discovered at runtime
4. **Limited Field Filtering**: Returns fixed response shape with no dynamic field selection

### Business Context

The autom8 ecosystem requires S2S (service-to-service) resolution of business identifiers to Asana task GIDs across multiple entity types. The autom8_data service and other consumers need to:

- Resolve phone/vertical pairs to Unit GIDs (current capability)
- Resolve phone/vertical pairs to Business GIDs (new requirement)
- Resolve offer identifiers to Offer GIDs (new requirement)
- Resolve contact identifiers to Contact GIDs (new requirement)

### Technical Context (Infrastructure ~80% Ready)

| Component | Location | Status |
|-----------|----------|--------|
| SearchService | `search/service.py` | Exists - field-based GID lookup from cached DataFrames |
| SchemaRegistry | `dataframes/models/registry.py` | Exists - task-type to schema mapping |
| NameResolver | `clients/name_resolver.py` | Exists - name/GID resolution with caching |
| WorkspaceProjectRegistry | `models/business/registry.py` | Exists - dynamic project discovery |
| GidLookupIndex | `services/gid_lookup.py` | Exists - O(1) phone/vertical lookup |
| ProjectRegistry | N/A | **Needed** - entity_type to project_gid mapping |

---

## User Stories

### US-001: Unit Resolution (Existing Capability Migration)

**As a** autom8_data service developer
**I want to** resolve phone/vertical pairs to Unit task GIDs via the new endpoint
**So that** I can maintain existing functionality after the endpoint migration

**Acceptance Criteria**:
- [ ] `POST /v1/resolve/unit` accepts phone/vertical pairs in request body
- [ ] Returns Unit task GIDs matching the existing response contract
- [ ] Batch processing up to 1000 pairs per request (existing limit)
- [ ] E.164 phone validation preserved
- [ ] Response order matches input order

### US-002: Business Resolution

**As a** autom8_data service developer
**I want to** resolve phone/vertical pairs to Business task GIDs
**So that** I can access Business-level Asana tasks for a given account

**Acceptance Criteria**:
- [ ] `POST /v1/resolve/business` accepts phone/vertical pairs
- [ ] Resolves to the Business entity containing the matching Unit
- [ ] Returns Business task GID (parent of the Unit)
- [ ] Handles case where Unit exists but Business hierarchy not populated

### US-003: Offer Resolution

**As a** autom8_data service developer
**I want to** resolve offer identifiers to Offer task GIDs
**So that** I can access Offer-level Asana tasks for ad management

**Acceptance Criteria**:
- [ ] `POST /v1/resolve/offer` accepts offer lookup criteria
- [ ] Supports resolution by offer_id custom field
- [ ] Supports resolution by phone/vertical + additional discriminators
- [ ] Returns Offer task GID

### US-004: Contact Resolution

**As a** autom8_data service developer
**I want to** resolve contact identifiers to Contact task GIDs
**So that** I can access Contact-level Asana tasks for CRM operations

**Acceptance Criteria**:
- [ ] `POST /v1/resolve/contact` accepts contact lookup criteria
- [ ] Supports resolution by contact_email or contact_phone
- [ ] Returns Contact task GID
- [ ] Handles multiple contacts per Business (returns first match or all)

### US-005: Startup Project Discovery

**As a** ops engineer deploying autom8_asana
**I want to** have project GIDs discovered automatically at startup
**So that** I don't need to configure environment variables for each entity type

**Acceptance Criteria**:
- [ ] Application discovers project GIDs from workspace at startup
- [ ] No `UNIT_PROJECT_GID` environment variable required
- [ ] Discovery completes before first request is served
- [ ] Discovery failure results in clear startup error with remediation guidance
- [ ] Discovered projects logged at INFO level

### US-006: Dynamic Field Filtering

**As a** API consumer
**I want to** request only specific fields in the response
**So that** I can reduce payload size and improve response times

**Acceptance Criteria**:
- [ ] Optional `fields` parameter in request body
- [ ] When specified, response includes only requested fields plus `gid`
- [ ] When omitted, returns default field set (backward compatible)
- [ ] Invalid field names return 422 with available field list

### US-007: Old Endpoint Removal

**As a** codebase maintainer
**I want to** remove the old `/api/v1/internal/gid-lookup` endpoint
**So that** there's a single, consistent resolution interface

**Acceptance Criteria**:
- [ ] Old endpoint removed from `internal.py`
- [ ] Old tests migrated or deleted
- [ ] No backward compatibility shim (clean break per initiative scope)

---

## Functional Requirements

### Must Have

#### FR-001: Unified Resolution Endpoint

The API shall expose `POST /v1/resolve/{entity_type}` where `entity_type` is one of: `unit`, `offer`, `contact`, `business`.

```
POST /v1/resolve/unit
POST /v1/resolve/offer
POST /v1/resolve/contact
POST /v1/resolve/business
```

#### FR-002: Request Schema

```json
{
  "criteria": [
    {
      "phone": "+15551234567",
      "vertical": "dental"
    }
  ],
  "fields": ["gid", "name", "office_phone"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `criteria` | `array[object]` | Yes | Lookup criteria (max 1000 items) |
| `criteria[].phone` | `string` | Conditional | E.164 phone (required for unit/business) |
| `criteria[].vertical` | `string` | Conditional | Business vertical (required for unit/business) |
| `criteria[].offer_id` | `string` | Conditional | Offer ID (alternative for offer lookup) |
| `criteria[].contact_email` | `string` | Conditional | Email (alternative for contact lookup) |
| `criteria[].contact_phone` | `string` | Conditional | Phone (alternative for contact lookup) |
| `fields` | `array[string]` | No | Fields to include in response |

#### FR-003: Response Schema

```json
{
  "results": [
    {
      "gid": "1234567890123456",
      "name": "Acme Dental Unit",
      "office_phone": "+15551234567"
    },
    {
      "gid": null,
      "error": "NOT_FOUND"
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 1,
    "entity_type": "unit",
    "project_gid": "1201081073731555"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `results` | `array[object]` | Results in same order as input criteria |
| `results[].gid` | `string\|null` | Task GID or null if not found |
| `results[].error` | `string` | Error code if resolution failed |
| `meta.resolved_count` | `int` | Number of successful resolutions |
| `meta.unresolved_count` | `int` | Number of failed resolutions |
| `meta.entity_type` | `string` | Entity type that was resolved |
| `meta.project_gid` | `string` | Project GID used for resolution |

#### FR-004: Startup Project Discovery

The application shall discover project GIDs for each entity type at startup using the existing `WorkspaceProjectRegistry`:

1. On `lifespan` startup, call `registry.discover_async(client)`
2. Build `ProjectRegistry` mapping: `entity_type -> project_gid`
3. Use `NameResolver.resolve_project_async()` to map project names to GIDs
4. Store mapping in `app.state.project_registry`

#### FR-005: ProjectRegistry Component

Create a new `ProjectRegistry` class that:

- Maps `entity_type` (string) to `project_gid` (string)
- Populated at startup via workspace discovery
- Provides `get_project_gid(entity_type: str) -> str | None`
- Thread-safe singleton pattern (matches existing registries)

#### FR-006: S2S Authentication

The endpoint shall require service token (S2S JWT) authentication:

- Reuse existing `require_service_claims` dependency
- PAT tokens rejected with 401 `SERVICE_TOKEN_REQUIRED`
- Log caller service name for audit

#### FR-007: Batch Size Limit

The endpoint shall enforce a maximum batch size of 1000 criteria per request (preserving existing limit).

#### FR-008: Input Validation

- E.164 phone format: `^\+[1-9]\d{1,14}$`
- Vertical: non-empty string
- Entity type: one of `unit`, `offer`, `contact`, `business`
- Fields: valid field names for the entity type's schema

#### FR-009: Old Endpoint Removal

Remove the following from `internal.py`:
- `POST /api/v1/internal/gid-lookup` endpoint
- Associated request/response models (`GidLookupRequest`, `GidLookupResponse`, etc.)
- Module-level `_gid_index_cache` (migrate to new architecture)

### Should Have

#### FR-010: Resolution Strategies by Entity Type

| Entity Type | Primary Resolution Strategy |
|-------------|----------------------------|
| `unit` | Phone/vertical lookup via GidLookupIndex |
| `business` | Resolve Unit, then navigate to `unit.business` |
| `offer` | offer_id lookup OR phone/vertical + offer discriminator |
| `contact` | contact_email OR contact_phone lookup |

#### FR-011: Graceful Degradation

If resolution fails for a criterion:
- Return `gid: null` with error code
- Continue processing remaining criteria
- Never fail entire request due to individual resolution failure

#### FR-012: Index Caching

Maintain TTL-based caching for resolution indexes:
- Default TTL: 1 hour (3600 seconds)
- Per-project caching (different TTL per entity type possible)
- Cache invalidation on startup discovery

### Could Have

#### FR-013: Resolution Strategy Selection

Allow callers to specify resolution strategy:

```json
{
  "criteria": [...],
  "strategy": "DEPENDENT_TASKS"
}
```

Strategies: `AUTO` (default), `INDEX_LOOKUP`, `DEPENDENT_TASKS`, `CUSTOM_FIELD_MAPPING`

#### FR-014: Bulk Resolution Optimization

For batch requests >100 criteria, use optimized bulk resolution:
- Single DataFrame scan instead of N index lookups
- Concurrent resolution across entity types

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target |
|--------|--------|
| Single criterion latency (index hit) | < 10ms |
| Batch 100 criteria latency | < 100ms |
| Batch 1000 criteria latency | < 1000ms |
| Startup discovery time | < 5 seconds |
| Memory overhead per entity type | < 10MB |

### NFR-002: Reliability

| Metric | Target |
|--------|--------|
| Availability | 99.9% (matches API SLA) |
| Error rate | < 0.1% (excluding NOT_FOUND) |
| Cache hit rate | > 95% after warm-up |

### NFR-003: Security

- S2S JWT authentication required (no PAT support)
- Request/response logging with PII masking for phone numbers
- Rate limiting: inherit global API rate limits (60 RPM default)

### NFR-004: Observability

- Structured logging with correlation IDs
- Metrics: resolution_count, resolution_latency_ms, cache_hit_rate
- Error codes: `NOT_FOUND`, `INVALID_CRITERIA`, `DISCOVERY_FAILED`

---

## Edge Cases

| Case | Expected Behavior |
|------|------------------|
| Empty criteria array | Return 200 with empty results |
| Unknown entity_type in path | Return 404 with valid entity types |
| Phone without vertical | Return 422 with required field error |
| Phone/vertical pair not found | Return result with `gid: null, error: "NOT_FOUND"` |
| Multiple matches for criteria | Return first match (unit/business) or all (contact) |
| Project discovery fails at startup | Fail startup with clear error message |
| Index cache expired mid-request | Rebuild index, continue request (may add latency) |
| Invalid field name in `fields` | Return 422 with available field names |
| Bot PAT unavailable | Return 503 with `BOT_PAT_UNAVAILABLE` error |
| Workspace projects exceed 1000 | Handle pagination in discovery |
| Concurrent startup discovery | Singleton pattern prevents duplicate discovery |

---

## Success Criteria

- [ ] All 4 entity types resolvable via single endpoint pattern
- [ ] Old `/api/v1/internal/gid-lookup` endpoint removed entirely
- [ ] Project GIDs discovered at startup (no env vars required)
- [ ] Dynamic field filtering supported via `fields` parameter
- [ ] Existing S2S demo updated to use new endpoint
- [ ] All existing tests pass or are migrated
- [ ] New tests achieve >90% coverage for resolution logic
- [ ] Performance targets met (latency, throughput)
- [ ] Documentation updated with new endpoint contract

---

## Out of Scope

| Item | Rationale |
|------|-----------|
| Backward compatibility shim | Clean break per initiative scope |
| GraphQL resolution endpoint | REST sufficient for current consumers |
| Real-time cache invalidation | TTL-based refresh sufficient |
| Multi-workspace support | Single workspace per deployment |
| Resolution confidence scoring | Binary found/not-found sufficient |
| WebSocket streaming for large batches | Batch API sufficient for 1000 limit |

---

## Open Questions

*All questions should be resolved before handoff to Architecture.*

1. ~~Should Business resolution return the Business GID even if Unit not found?~~ **Resolved**: No, require Unit match first (Business is navigated via Unit hierarchy)

2. ~~What discriminator fields for Offer resolution beyond offer_id?~~ **Resolved**: Support phone/vertical + offer_name as secondary strategy

3. ~~Should Contact resolution return multiple matches or first match?~~ **Resolved**: Return all matches with `multiple: true` flag in result

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| WorkspaceProjectRegistry | Implemented | Dynamic project discovery |
| SchemaRegistry | Implemented | Entity type schemas |
| GidLookupIndex | Implemented | O(1) phone/vertical lookup |
| NameResolver | Implemented | Project name resolution |
| SearchService | Implemented | Field-based DataFrame search |
| S2S JWT validation | Implemented | `validate_service_token()` |
| Bot PAT provider | Implemented | `get_bot_pat()` |

---

## Appendix A: Entity Type to Project Mapping

| Entity Type | Expected Project Name Pattern | Schema |
|-------------|------------------------------|--------|
| `unit` | "Units" or contains "Unit" | UNIT_SCHEMA |
| `offer` | "Offers" or contains "Offer" | (to be defined) |
| `contact` | "Contacts" or contains "Contact" | CONTACT_SCHEMA |
| `business` | "Business" or contains "Business" | (base schema) |

---

## Appendix B: Migration Path

### Phase 1: New Endpoint Implementation
1. Create `POST /v1/resolve/{entity_type}` endpoint
2. Implement ProjectRegistry with startup discovery
3. Implement Unit resolution (feature parity)
4. Add integration tests

### Phase 2: Extended Entity Support
1. Implement Business resolution (via Unit navigation)
2. Implement Offer resolution
3. Implement Contact resolution
4. Add field filtering support

### Phase 3: Cleanup
1. Remove old `/api/v1/internal/gid-lookup` endpoint
2. Migrate S2S demo to new endpoint
3. Update documentation
4. Archive deprecated code

---

## Appendix C: Request/Response Examples

### Unit Resolution

**Request**:
```http
POST /v1/resolve/unit HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "criteria": [
    {"phone": "+15551234567", "vertical": "dental"},
    {"phone": "+15559876543", "vertical": "medical"}
  ]
}
```

**Response**:
```json
{
  "results": [
    {"gid": "1234567890123456"},
    {"gid": null, "error": "NOT_FOUND"}
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 1,
    "entity_type": "unit",
    "project_gid": "1201081073731555"
  }
}
```

### Business Resolution with Fields

**Request**:
```http
POST /v1/resolve/business HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "criteria": [
    {"phone": "+15551234567", "vertical": "dental"}
  ],
  "fields": ["gid", "name", "office_phone", "vertical"]
}
```

**Response**:
```json
{
  "results": [
    {
      "gid": "9876543210987654",
      "name": "Acme Dental",
      "office_phone": "+15551234567",
      "vertical": "dental"
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 0,
    "entity_type": "business",
    "project_gid": "1200653012566782"
  }
}
```

### Contact Resolution

**Request**:
```http
POST /v1/resolve/contact HTTP/1.1
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "criteria": [
    {"contact_email": "john@example.com"}
  ]
}
```

**Response**:
```json
{
  "results": [
    {
      "gid": "1111111111111111",
      "multiple": false
    }
  ],
  "meta": {
    "resolved_count": 1,
    "unresolved_count": 0,
    "entity_type": "contact",
    "project_gid": "1200775689604552"
  }
}
```
