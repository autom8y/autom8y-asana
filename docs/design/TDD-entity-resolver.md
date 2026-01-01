# TDD: Entity Resolver Generalization

## Overview

This document specifies the technical design for the Entity Resolver system, which replaces the existing `/api/v1/internal/gid-lookup` endpoint with a generalized `POST /v1/resolve/{entity_type}` endpoint. The system supports four entity types (Unit, Offer, Contact, Business), discovers project GIDs at startup via workspace discovery, and provides dynamic field filtering through SchemaRegistry integration.

## Context

- **PRD Reference**: `docs/requirements/PRD-entity-resolver.md`
- **Related ADRs**:
  - ADR-0031: Registry and Discovery Architecture (WorkspaceProjectRegistry foundation)
  - ADR-0060: Entity Resolver Project Discovery (new, accompanies this TDD)

### Constraints
- Performance: <10ms single lookup, <100ms batch 100, <1000ms batch 1000
- S2S JWT authentication only (no PAT support)
- Must integrate with existing SchemaRegistry for field filtering
- Startup discovery must complete before first request

### Existing Infrastructure
| Component | Location | Status | Usage in Design |
|-----------|----------|--------|-----------------|
| GidLookupIndex | `services/gid_lookup.py` | Exists | Unit/Business O(1) resolution |
| SchemaRegistry | `dataframes/models/registry.py` | Exists | Field validation and filtering |
| WorkspaceProjectRegistry | `models/business/registry.py` | Exists | Startup project discovery |
| ProjectTypeRegistry | `models/business/registry.py` | Exists | Entity type to project mapping |
| NameResolver | `clients/name_resolver.py` | Exists | Project name to GID resolution |
| internal.py gid-lookup | `api/routes/internal.py` | To be removed | Deprecated by new endpoint |

---

## System Design

### Architecture Diagram

```
                                    ┌─────────────────────────────────────────────────────┐
                                    │                   FastAPI App                        │
                                    │                                                      │
  ┌──────────────┐                 │  ┌─────────────────────────────────────────────┐    │
  │  S2S Client  │────────────────▶│  │     POST /v1/resolve/{entity_type}          │    │
  │  (JWT Auth)  │                 │  │            (resolver.py)                     │    │
  └──────────────┘                 │  └─────────────────────────────────────────────┘    │
                                    │                        │                            │
                                    │                        ▼                            │
                                    │  ┌─────────────────────────────────────────────┐    │
                                    │  │          EntityResolverService              │    │
                                    │  │         (services/resolver.py)              │    │
                                    │  └─────────────────────────────────────────────┘    │
                                    │            │                     │                  │
                                    │            ▼                     ▼                  │
                                    │  ┌─────────────────┐   ┌────────────────────┐      │
                                    │  │ ResolutionRouter │   │ EntityProjectRegistry│    │
                                    │  │  (strategy dispatch)│ │ (app.state)        │    │
                                    │  └─────────────────┘   └────────────────────┘      │
                                    │            │                                        │
                                    │            ▼                                        │
                                    │  ┌──────────────────────────────────────────────┐  │
                                    │  │              Resolution Strategies            │  │
                                    │  ├────────────┬────────────┬─────────┬──────────┤  │
                                    │  │ UnitStrategy│BusinessStrat│OfferStr│ContactStr│  │
                                    │  │ (GidLookup- │(Unit+parent)│(offer_id│(email/   │  │
                                    │  │  Index O(1))│             │ OR pv+d)│ phone)   │  │
                                    │  └────────────┴────────────┴─────────┴──────────┘  │
                                    │                        │                            │
                                    │                        ▼                            │
                                    │  ┌─────────────────────────────────────────────┐    │
                                    │  │              GidLookupIndex                  │    │
                                    │  │           (TTL-cached DataFrame)             │    │
                                    │  └─────────────────────────────────────────────┘    │
                                    │                        │                            │
                                    └────────────────────────│────────────────────────────┘
                                                             │
                                                             ▼
                                    ┌─────────────────────────────────────────────────────┐
                                    │                    Asana API                         │
                                    │               (via AsanaClient)                      │
                                    └─────────────────────────────────────────────────────┘

Startup Flow:
┌──────────────┐     ┌─────────────────────────┐     ┌────────────────────┐
│ lifespan()   │────▶│ WorkspaceProjectRegistry │────▶│ EntityProjectRegistry│
│ (app startup)│     │    .discover_async()     │     │   (app.state)       │
└──────────────┘     └─────────────────────────┘     └────────────────────┘
```

### Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| EntityResolverService | Orchestrates resolution: validates input, dispatches to strategies, assembles response | `services/resolver.py` (new) |
| EntityProjectRegistry | Maps entity_type -> project_gid, populated at startup | `services/resolver.py` (new) |
| ResolutionStrategy (Protocol) | Abstract interface for entity-specific resolution | `services/resolver.py` (new) |
| UnitResolutionStrategy | Phone/vertical O(1) lookup via GidLookupIndex | `services/resolver.py` (new) |
| BusinessResolutionStrategy | Unit resolution + parent navigation | `services/resolver.py` (new) |
| OfferResolutionStrategy | offer_id lookup OR phone/vertical + discriminator | `services/resolver.py` (new) |
| ContactResolutionStrategy | email/phone field search | `services/resolver.py` (new) |
| resolver router | FastAPI router with `/v1/resolve/{entity_type}` | `api/routes/resolver.py` (new) |

---

## Data Model

### EntityProjectRegistry

```python
@dataclass(frozen=True, slots=True)
class EntityProjectConfig:
    """Configuration for a single entity type's project mapping."""
    entity_type: str                    # "unit", "business", "offer", "contact"
    project_gid: str                    # Asana project GID
    project_name: str                   # Human-readable name (for logging)
    schema_task_type: str               # SchemaRegistry key (e.g., "Unit", "Contact")


class EntityProjectRegistry:
    """Singleton registry mapping entity_type -> project configuration.

    Populated at startup via WorkspaceProjectRegistry discovery.
    Thread-safe via immutable design (populated once, read-only after).
    """

    _instance: ClassVar[EntityProjectRegistry | None] = None
    _configs: dict[str, EntityProjectConfig]      # entity_type -> config
    _initialized: bool

    @classmethod
    def get_instance(cls) -> EntityProjectRegistry:
        """Get or create singleton instance."""

    def get_project_gid(self, entity_type: str) -> str | None:
        """Get project GID for entity type. O(1)."""

    def get_config(self, entity_type: str) -> EntityProjectConfig | None:
        """Get full config for entity type. O(1)."""

    def is_ready(self) -> bool:
        """True if startup discovery completed successfully."""

    @classmethod
    def reset(cls) -> None:
        """Reset for testing."""
```

### Resolution Request/Response Models

```python
class ResolutionCriterion(BaseModel):
    """Single lookup criterion - fields vary by entity type."""
    model_config = ConfigDict(extra="forbid")

    # Unit/Business resolution
    phone: str | None = None
    vertical: str | None = None

    # Offer resolution
    offer_id: str | None = None
    offer_name: str | None = None  # For phone/vertical + discriminator

    # Contact resolution
    contact_email: str | None = None
    contact_phone: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_e164(cls, v: str | None) -> str | None:
        """Validate E.164 format: +[1-9][0-9]{1,14}"""


class ResolutionRequest(BaseModel):
    """Request body for entity resolution."""
    model_config = ConfigDict(extra="forbid")

    criteria: list[ResolutionCriterion]  # Max 1000
    fields: list[str] | None = None      # Optional field filtering

    @field_validator("criteria")
    @classmethod
    def validate_batch_size(cls, v: list) -> list:
        """Enforce max 1000 criteria."""


class ResolutionResult(BaseModel):
    """Single resolution result."""
    gid: str | None
    error: str | None = None    # Error code if resolution failed
    multiple: bool | None = None  # True if contact returned multiple matches
    # Additional fields based on `fields` request parameter


class ResolutionMeta(BaseModel):
    """Response metadata."""
    resolved_count: int
    unresolved_count: int
    entity_type: str
    project_gid: str


class ResolutionResponse(BaseModel):
    """Response body for entity resolution."""
    results: list[ResolutionResult]
    meta: ResolutionMeta
```

### Entity Type to Project Name Mapping

Per PRD Appendix A, expected project name patterns for discovery:

| entity_type | Project Name Pattern | SchemaRegistry Key |
|-------------|---------------------|-------------------|
| `unit` | "Units" or contains "Unit" | `Unit` |
| `business` | "Business" or contains "Business" | `*` (base schema) |
| `offer` | "Offers" or contains "Offer" | (to be defined) |
| `contact` | "Contacts" or contains "Contact" | `Contact` |

---

## API Contracts

### POST /v1/resolve/{entity_type}

```http
POST /v1/resolve/unit HTTP/1.1
Host: api.autom8.io
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "criteria": [
    {"phone": "+15551234567", "vertical": "dental"},
    {"phone": "+15559876543", "vertical": "medical"}
  ],
  "fields": ["gid", "name", "office_phone"]
}
```

**Path Parameters:**
| Parameter | Type | Required | Values |
|-----------|------|----------|--------|
| entity_type | string | Yes | `unit`, `business`, `offer`, `contact` |

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| criteria | array[object] | Yes | Lookup criteria, max 1000 items |
| fields | array[string] | No | Fields to include (defaults to gid only) |

**Criteria Fields by Entity Type:**

| Entity Type | Required Fields | Optional Fields |
|-------------|-----------------|-----------------|
| unit | phone, vertical | - |
| business | phone, vertical | - |
| offer | (offer_id) OR (phone, vertical, offer_name) | - |
| contact | (contact_email) OR (contact_phone) | - |

**Response (200 OK):**
```json
{
  "results": [
    {"gid": "1234567890123456", "name": "Acme Dental Unit", "office_phone": "+15551234567"},
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

**Error Responses:**

| Status | Error Code | Condition |
|--------|------------|-----------|
| 401 | MISSING_AUTH | No Authorization header |
| 401 | SERVICE_TOKEN_REQUIRED | PAT token provided (S2S only) |
| 401 | JWT_INVALID | JWT validation failed |
| 404 | UNKNOWN_ENTITY_TYPE | entity_type not in allowed values |
| 422 | VALIDATION_ERROR | Invalid request body |
| 422 | INVALID_FIELD | Field in `fields` not in schema |
| 422 | MISSING_REQUIRED_FIELD | Required criteria field missing |
| 422 | BATCH_SIZE_EXCEEDED | criteria array > 1000 |
| 503 | DISCOVERY_INCOMPLETE | Startup discovery not finished |
| 503 | BOT_PAT_UNAVAILABLE | Bot PAT not configured |

---

## Sequence Diagrams

### Startup Discovery Flow

```
┌─────────┐     ┌───────────────┐    ┌────────────────────┐    ┌─────────────────────┐
│lifespan │     │WorkspaceProject│    │EntityProjectRegistry│    │NameResolver         │
│(startup)│     │Registry        │    │                     │    │                     │
└────┬────┘     └───────┬───────┘    └──────────┬──────────┘    └──────────┬──────────┘
     │                  │                        │                          │
     │ discover_async() │                        │                          │
     │─────────────────▶│                        │                          │
     │                  │                        │                          │
     │                  │ list workspace projects│                          │
     │                  │─────────────────────────────────────────────────▶│
     │                  │                        │                          │
     │                  │◀────────projects[]─────────────────────────────────│
     │                  │                        │                          │
     │                  │ match patterns         │                          │
     │                  │ (Units, Business, etc) │                          │
     │                  │──────────────────────▶ │                          │
     │                  │                        │                          │
     │                  │                        │ register(unit, gid)      │
     │                  │                        │ register(business, gid)  │
     │                  │                        │ register(offer, gid)     │
     │                  │                        │ register(contact, gid)   │
     │                  │                        │                          │
     │◀─────────────────│                        │                          │
     │  (discovery done)│                        │                          │
     │                  │                        │                          │
     │ store in         │                        │                          │
     │ app.state        │                        │                          │
     │                  │                        │                          │
```

### Unit Resolution Flow

```
┌──────┐    ┌─────────┐    ┌───────────────────┐    ┌──────────────┐    ┌──────────────┐
│Client│    │resolver │    │EntityResolverSvc  │    │UnitStrategy  │    │GidLookupIndex│
│      │    │router   │    │                   │    │              │    │              │
└──┬───┘    └────┬────┘    └─────────┬─────────┘    └──────┬───────┘    └──────┬───────┘
   │             │                   │                     │                   │
   │ POST /v1/resolve/unit           │                     │                   │
   │ {criteria: [...]}               │                     │                   │
   │────────────────────────────────▶│                     │                   │
   │             │                   │                     │                   │
   │             │ validate_request()│                     │                   │
   │             │──────────────────▶│                     │                   │
   │             │                   │                     │                   │
   │             │                   │ resolve(criteria)   │                   │
   │             │                   │────────────────────▶│                   │
   │             │                   │                     │                   │
   │             │                   │                     │ get_or_build_index()
   │             │                   │                     │──────────────────▶│
   │             │                   │                     │                   │
   │             │                   │                     │◀──GidLookupIndex──│
   │             │                   │                     │                   │
   │             │                   │                     │ index.get_gids()  │
   │             │                   │                     │──────────────────▶│
   │             │                   │                     │                   │
   │             │                   │                     │◀──{pair: gid}─────│
   │             │                   │                     │                   │
   │             │                   │◀──ResolutionResult[]│                   │
   │             │                   │                     │                   │
   │             │◀──────────────────│                     │                   │
   │             │  ResolutionResponse                     │                   │
   │◀────────────│                   │                     │                   │
   │  200 OK     │                   │                     │                   │
```

### Business Resolution Flow

```
┌──────┐    ┌───────────────────┐    ┌────────────────┐    ┌──────────────┐
│Client│    │EntityResolverSvc  │    │BusinessStrategy│    │UnitStrategy  │
│      │    │                   │    │                │    │              │
└──┬───┘    └─────────┬─────────┘    └───────┬────────┘    └──────┬───────┘
   │                  │                      │                    │
   │ POST /v1/resolve/business               │                    │
   │─────────────────▶│                      │                    │
   │                  │                      │                    │
   │                  │ resolve(criteria)    │                    │
   │                  │─────────────────────▶│                    │
   │                  │                      │                    │
   │                  │                      │ delegate to UnitStrategy
   │                  │                      │───────────────────▶│
   │                  │                      │                    │
   │                  │                      │◀──unit_gid─────────│
   │                  │                      │                    │
   │                  │                      │ if unit_gid:       │
   │                  │                      │   fetch unit task  │
   │                  │                      │   navigate to parent│
   │                  │                      │   (task.parent.gid)│
   │                  │                      │                    │
   │                  │◀─business_gid────────│                    │
   │                  │                      │                    │
   │◀─────────────────│                      │                    │
   │ 200 OK           │                      │                    │
```

---

## Non-Functional Considerations

### Performance

**Targets (from PRD NFR-001):**
| Metric | Target | Approach |
|--------|--------|----------|
| Single criterion latency | <10ms | O(1) GidLookupIndex |
| Batch 100 criteria | <100ms | Batch index lookup |
| Batch 1000 criteria | <1000ms | Single DataFrame scan for large batches |
| Startup discovery | <5 seconds | Single workspace API call |
| Memory per entity type | <10MB | DataFrame-backed index |

**Caching Strategy:**
- `GidLookupIndex` per project with 1-hour TTL (existing pattern from internal.py)
- Index rebuilt on cache miss or staleness
- Module-level cache dict: `_gid_index_cache: dict[str, GidLookupIndex]`

**Bulk Optimization (FR-014):**
For batch requests >100 criteria, use DataFrame scan instead of N index lookups:
```python
if len(criteria) > 100:
    return self._bulk_resolve_via_dataframe(criteria, df)
else:
    return self._resolve_via_index(criteria, index)
```

### Security

**Authentication (FR-006):**
- Reuse existing `require_service_claims` dependency from internal.py
- S2S JWT required, PAT tokens rejected with 401 `SERVICE_TOKEN_REQUIRED`
- Caller service name logged for audit

**PII Handling (NFR-003):**
- Phone numbers logged with masking: `+1555***4567`
- Request/response logging via existing RequestLoggingMiddleware

**Input Validation:**
- E.164 phone format: `^\+[1-9]\d{1,14}$`
- Entity type path parameter: enum validation
- Field names: validated against SchemaRegistry
- Batch size: max 1000 criteria

### Reliability

**Graceful Degradation (FR-011):**
- Individual resolution failures return `{gid: null, error: "NOT_FOUND"}`
- Never fail entire request due to single criterion failure
- Cache rebuild mid-request adds latency but continues

**Startup Failure Handling:**
- Discovery failure: Fail startup with clear error message (fail-fast)
- Log ERROR with remediation guidance:
  ```
  ERROR: Entity resolver discovery failed.
  Ensure workspace contains projects matching: Units, Business, Offers, Contacts
  ```

**Error Codes:**
| Code | Description |
|------|-------------|
| NOT_FOUND | Criterion resolved but no match |
| INVALID_CRITERIA | Criterion missing required fields |
| DISCOVERY_FAILED | Startup discovery error |
| STRATEGY_ERROR | Strategy-specific resolution error |

### Observability

**Structured Logging:**
```python
logger.info(
    "entity_resolution_batch_complete",
    extra={
        "entity_type": "unit",
        "criteria_count": 50,
        "resolved_count": 48,
        "unresolved_count": 2,
        "duration_ms": 45,
        "caller_service": "autom8_data",
        "cache_hit": True,
        "request_id": "req-abc123",
    }
)
```

**Metrics (to be implemented via observability hooks):**
- `entity_resolver_requests_total{entity_type, status}`
- `entity_resolver_duration_seconds{entity_type}`
- `entity_resolver_cache_hit_rate{entity_type}`
- `entity_resolver_batch_size{entity_type}`

---

## Implementation Guidance

### File Structure

```
src/autom8_asana/
├── services/
│   ├── resolver.py           # NEW: EntityResolverService, strategies, registry
│   └── gid_lookup.py         # EXISTS: GidLookupIndex (reused)
├── api/
│   └── routes/
│       ├── resolver.py       # NEW: /v1/resolve/{entity_type} router
│       ├── internal.py       # MODIFIED: Remove gid-lookup endpoint
│       └── __init__.py       # MODIFIED: Add resolver_router
└── api/
    └── main.py               # MODIFIED: Add startup discovery to lifespan
```

### Strategy Pattern Implementation

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class ResolutionStrategy(Protocol):
    """Protocol for entity-specific resolution logic."""

    async def resolve(
        self,
        criteria: list[ResolutionCriterion],
        project_gid: str,
        client: AsanaClient,
    ) -> list[ResolutionResult]:
        """Resolve criteria to entity GIDs."""
        ...

    def validate_criteria(self, criterion: ResolutionCriterion) -> str | None:
        """Return error message if criterion invalid, None if valid."""
        ...


class UnitResolutionStrategy:
    """Unit resolution via GidLookupIndex O(1) lookup."""

    async def resolve(
        self,
        criteria: list[ResolutionCriterion],
        project_gid: str,
        client: AsanaClient,
    ) -> list[ResolutionResult]:
        index = await self._get_or_build_index(project_gid, client)
        pairs = [self._to_phone_vertical_pair(c) for c in criteria]
        gid_map = index.get_gids(pairs)
        return [
            ResolutionResult(gid=gid_map.get(p), error="NOT_FOUND" if not gid_map.get(p) else None)
            for p in pairs
        ]

    def validate_criteria(self, criterion: ResolutionCriterion) -> str | None:
        if not criterion.phone or not criterion.vertical:
            return "phone and vertical required for unit resolution"
        return None


class BusinessResolutionStrategy:
    """Business resolution: Unit lookup + parent navigation."""

    def __init__(self, unit_strategy: UnitResolutionStrategy):
        self._unit_strategy = unit_strategy

    async def resolve(
        self,
        criteria: list[ResolutionCriterion],
        project_gid: str,
        client: AsanaClient,
    ) -> list[ResolutionResult]:
        # First resolve to units
        unit_results = await self._unit_strategy.resolve(
            criteria,
            self._get_unit_project_gid(),  # Use unit project, not business
            client,
        )

        # Navigate to parent for each resolved unit
        results = []
        for unit_result in unit_results:
            if unit_result.gid:
                business_gid = await self._get_parent_gid(unit_result.gid, client)
                results.append(ResolutionResult(gid=business_gid))
            else:
                results.append(unit_result)  # Pass through NOT_FOUND
        return results


# Strategy dispatch (simple dict, not over-engineered)
RESOLUTION_STRATEGIES: dict[str, ResolutionStrategy] = {}

def get_strategy(entity_type: str) -> ResolutionStrategy:
    """Get resolution strategy for entity type."""
    if entity_type not in RESOLUTION_STRATEGIES:
        raise ValueError(f"Unknown entity type: {entity_type}")
    return RESOLUTION_STRATEGIES[entity_type]

def register_strategies():
    """Register all strategies (called at module load)."""
    unit_strategy = UnitResolutionStrategy()
    RESOLUTION_STRATEGIES["unit"] = unit_strategy
    RESOLUTION_STRATEGIES["business"] = BusinessResolutionStrategy(unit_strategy)
    RESOLUTION_STRATEGIES["offer"] = OfferResolutionStrategy()
    RESOLUTION_STRATEGIES["contact"] = ContactResolutionStrategy()
```

### Startup Discovery Integration

```python
# In api/main.py

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle with entity resolver discovery."""

    configure_structlog()
    settings = get_settings()

    logger.info("api_starting", extra={"service": "autom8_asana"})

    # Entity resolver startup discovery (FR-004, FR-005)
    try:
        await _discover_entity_projects(app)
    except Exception as e:
        logger.error(
            "entity_resolver_discovery_failed",
            extra={
                "error": str(e),
                "remediation": "Ensure workspace contains: Units, Business, Offers, Contacts projects",
            },
        )
        raise RuntimeError(f"Entity resolver discovery failed: {e}") from e

    yield

    logger.info("api_stopping", extra={"service": "autom8_asana"})


async def _discover_entity_projects(app: FastAPI) -> None:
    """Discover and register entity type project mappings."""
    from autom8_asana import AsanaClient
    from autom8_asana.auth.bot_pat import get_bot_pat
    from autom8_asana.models.business.registry import get_workspace_registry
    from autom8_asana.services.resolver import EntityProjectRegistry

    bot_pat = get_bot_pat()

    async with AsanaClient(token=bot_pat) as client:
        # Use existing WorkspaceProjectRegistry discovery
        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(client)

        # Map discovered projects to entity resolver registry
        entity_registry = EntityProjectRegistry.get_instance()

        # Pattern matching for entity type projects
        ENTITY_PATTERNS = {
            "unit": ["units", "unit"],
            "business": ["business", "businesses"],
            "offer": ["offers", "offer"],
            "contact": ["contacts", "contact"],
        }

        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                project_gid = workspace_registry.get_by_name(pattern)
                if project_gid:
                    entity_registry.register(entity_type, project_gid, pattern)
                    logger.info(
                        "entity_project_registered",
                        extra={
                            "entity_type": entity_type,
                            "project_gid": project_gid,
                            "pattern": pattern,
                        },
                    )
                    break
            else:
                logger.warning(
                    "entity_project_not_found",
                    extra={"entity_type": entity_type, "patterns": patterns},
                )

        # Store registry in app.state for request access
        app.state.entity_project_registry = entity_registry
```

### Field Filtering via SchemaRegistry

```python
def filter_result_fields(
    result: dict[str, Any],
    requested_fields: list[str] | None,
    entity_type: str,
) -> dict[str, Any]:
    """Filter result to requested fields only."""
    if not requested_fields:
        # Default: gid only
        return {"gid": result.get("gid")}

    # Validate fields against schema
    registry = SchemaRegistry.get_instance()
    schema = registry.get_schema(entity_type.title())  # "unit" -> "Unit"
    valid_fields = {col.name for col in schema.columns}

    invalid = set(requested_fields) - valid_fields - {"gid"}
    if invalid:
        raise ValueError(f"Invalid fields: {invalid}. Available: {valid_fields}")

    # Always include gid
    fields_to_include = set(requested_fields) | {"gid"}

    return {k: v for k, v in result.items() if k in fields_to_include}
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Startup discovery latency exceeds 5s | Low | Medium | Workspace API is fast; single call. Monitor and add timeout. |
| Project naming doesn't match patterns | Medium | High | Log warning for missing mappings; document expected patterns. |
| GidLookupIndex memory growth | Low | Medium | TTL-based eviction (existing pattern); <10MB per project. |
| Parent navigation for Business adds latency | Medium | Low | Cache parent GIDs in Unit DataFrame or add parent_gid column. |
| Concurrent requests during cache rebuild | Low | Low | First request rebuilds; others wait or get stale data (acceptable). |
| S2S clients using old endpoint after removal | Medium | High | Coordinate deprecation with autom8_data team; staged rollout. |

---

## ADRs

| ADR | Title | Status |
|-----|-------|--------|
| ADR-0031 | Registry and Discovery Architecture | Accepted (foundation) |
| ADR-0060 | Entity Resolver Project Discovery | Proposed (companion to this TDD) |

---

## Open Items

| Item | Owner | Status |
|------|-------|--------|
| Define OFFER_SCHEMA in SchemaRegistry | Architect | Pending - not blocking MVP |
| Coordinate old endpoint deprecation with autom8_data | Tech Lead | Pending |
| Add parent_gid column to UNIT_SCHEMA for Business perf | Architect | Future optimization |

---

## Appendix A: Migration Checklist

### Phase 1: New Endpoint (Week 1)
- [ ] Create `services/resolver.py` with EntityProjectRegistry, strategies
- [ ] Create `api/routes/resolver.py` with POST /v1/resolve/{entity_type}
- [ ] Integrate startup discovery in lifespan
- [ ] Implement Unit resolution (feature parity)
- [ ] Add integration tests for Unit resolution
- [ ] Deploy to staging

### Phase 2: Extended Entity Support (Week 2)
- [ ] Implement Business resolution strategy
- [ ] Implement Offer resolution strategy
- [ ] Implement Contact resolution strategy
- [ ] Add field filtering support
- [ ] Add integration tests for all entity types

### Phase 3: Cleanup (Week 3)
- [ ] Coordinate with autom8_data on endpoint migration
- [ ] Remove old `/api/v1/internal/gid-lookup` endpoint
- [ ] Remove deprecated models from internal.py
- [ ] Update S2S demo to use new endpoint
- [ ] Archive deprecated code

---

## Appendix B: Test Matrix

| Test Case | Entity Type | Input | Expected |
|-----------|-------------|-------|----------|
| TC-001 | unit | Valid phone/vertical | Returns GID |
| TC-002 | unit | Unknown phone/vertical | Returns null, NOT_FOUND |
| TC-003 | unit | Invalid E.164 | 422 VALIDATION_ERROR |
| TC-004 | unit | Missing vertical | 422 MISSING_REQUIRED_FIELD |
| TC-005 | unit | Batch 1000 | Returns 1000 results <1000ms |
| TC-006 | business | Valid phone/vertical | Returns parent GID |
| TC-007 | business | Unit exists, no parent | Returns null, error |
| TC-008 | offer | Valid offer_id | Returns GID |
| TC-009 | offer | phone/vertical + offer_name | Returns GID |
| TC-010 | contact | Valid email | Returns GID |
| TC-011 | contact | Multiple matches | Returns all with multiple=true |
| TC-012 | any | PAT token | 401 SERVICE_TOKEN_REQUIRED |
| TC-013 | any | Empty criteria | 200, empty results |
| TC-014 | any | Invalid entity_type | 404 UNKNOWN_ENTITY_TYPE |
| TC-015 | any | Invalid field name | 422 INVALID_FIELD |
| TC-016 | startup | Discovery fails | Startup fails with clear error |
