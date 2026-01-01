# ADR-0060: Entity Resolver Project Discovery

## Status

Accepted

## Context

The Entity Resolver system (per PRD-entity-resolver) requires mapping entity types (unit, business, offer, contact) to their corresponding Asana project GIDs. The existing `/api/v1/internal/gid-lookup` endpoint uses an environment variable (`UNIT_PROJECT_GID`) for configuration, creating operational burden:

1. **Configuration Drift**: Each deployment environment requires manual project GID configuration
2. **Single Entity Type**: Only Unit resolution is supported; adding entity types means adding more env vars
3. **Discovery Gap**: Project GIDs are static values, not discovered from the actual workspace
4. **Deployment Friction**: Ops engineers must know and configure Asana project GIDs for each entity

The autom8_asana ecosystem already has `WorkspaceProjectRegistry` (per ADR-0031) for dynamic project discovery at runtime. The question is: should Entity Resolver continue the env var pattern or adopt startup discovery?

## Decision

**Entity Resolver will discover project GIDs at startup via WorkspaceProjectRegistry, not environment variables.**

The discovery flow:

1. During FastAPI lifespan startup, call `WorkspaceProjectRegistry.discover_async()`
2. Match discovered projects to entity types via name pattern matching
3. Populate `EntityProjectRegistry` with entity_type -> project_gid mappings
4. Store registry in `app.state.entity_project_registry` for request-time access
5. If discovery fails or required projects not found, **fail startup** (fail-fast)

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # ... existing startup ...

    try:
        await _discover_entity_projects(app)
    except Exception as e:
        logger.error("entity_resolver_discovery_failed", extra={"error": str(e)})
        raise RuntimeError(f"Entity resolver discovery failed: {e}") from e

    yield
```

Project name pattern matching:

| Entity Type | Project Name Patterns (case-insensitive) |
|-------------|------------------------------------------|
| unit | "units", "unit" |
| business | "business", "businesses" |
| offer | "offers", "offer" |
| contact | "contacts", "contact" |

## Alternatives Considered

### Option A: Environment Variables (Current Pattern)

Continue using `UNIT_PROJECT_GID` and add `BUSINESS_PROJECT_GID`, `OFFER_PROJECT_GID`, `CONTACT_PROJECT_GID`.

**Pros:**
- Familiar pattern (already used for Unit)
- Zero startup latency (no API call)
- Works in environments where Asana API is slow/unavailable at startup
- Explicit configuration = explicit control

**Cons:**
- Four env vars to configure per environment
- Configuration drift risk (env var stale after project rename)
- No validation that project actually exists until first request
- Ops burden: must know Asana project GIDs
- No discovery = no visibility into workspace structure

### Option B: Hybrid (Env Var Override + Discovery Fallback)

Attempt discovery, but allow env var overrides. If `{ENTITY}_PROJECT_GID` set, use it; otherwise discover.

**Pros:**
- Backward compatible with existing Unit configuration
- Allows override for edge cases
- Gradual migration path

**Cons:**
- Two code paths to maintain
- Confusion about which source is authoritative
- Override may mask discovery failures
- More complex testing matrix

### Option C: Startup Discovery (Chosen)

Discover all entity projects at startup, fail if not found.

**Pros:**
- Zero configuration for standard deployments
- Single source of truth (workspace projects)
- Self-documenting (logs discovered mappings)
- Fail-fast if workspace misconfigured
- Consistent with WorkspaceProjectRegistry pattern
- Validates project existence at startup, not first request

**Cons:**
- Startup latency (~1-3 seconds for discovery API call)
- Requires workspace to have correctly named projects
- No override mechanism for non-standard naming

## Rationale

**We chose Option C (Startup Discovery) for these reasons:**

1. **Operational Simplicity**: Zero env vars means zero configuration drift. Deploy the service, it discovers projects automatically.

2. **Fail-Fast Validation**: Discovery failure at startup surfaces misconfiguration immediately, not on first user request hours later.

3. **Consistency with ADR-0031**: The `WorkspaceProjectRegistry` pattern is already established for pipeline project discovery. Entity Resolver follows the same pattern.

4. **Self-Documenting**: Startup logs show exactly which projects were discovered:
   ```
   INFO entity_project_registered entity_type=unit project_gid=1201081073731555 pattern=units
   INFO entity_project_registered entity_type=business project_gid=1200653012566782 pattern=business
   ```

5. **Workspace as Source of Truth**: Projects are user-managed in Asana. Discovery respects this rather than requiring external configuration to stay synchronized.

**Why not hybrid?** The hybrid approach adds complexity without proportional benefit. The override escape hatch is rarely needed - if projects are correctly named (which they should be for autom8 ecosystem), discovery works. Non-standard naming is an edge case better addressed by documentation than code complexity.

**Startup latency is acceptable** because:
- Discovery runs once at startup, not per-request
- 1-3 seconds is negligible compared to container startup time
- Discovery can be parallelized with other startup tasks if needed

## Consequences

### Positive

- **Zero configuration**: Entity Resolver "just works" when deployed to workspaces with standard project naming
- **Fail-fast**: Misconfiguration surfaces at startup, not first request
- **Single source of truth**: Workspace projects are authoritative; no env var drift
- **Consistent pattern**: Follows established WorkspaceProjectRegistry approach
- **Improved observability**: Startup logs document discovered mappings

### Negative

- **Startup latency**: ~1-3 second delay for discovery API call
- **Naming constraint**: Projects must follow naming patterns (Units, Business, Offers, Contacts)
- **No override**: Non-standard project names require workspace rename, not configuration
- **API dependency at startup**: Service cannot start if Asana API unavailable

### Neutral

- Existing `UNIT_PROJECT_GID` env var becomes obsolete (breaking change for existing deployments)
- Discovery code adds ~50 lines to lifespan (acceptable complexity)
- Testing requires mock WorkspaceProjectRegistry or real workspace

## Implementation Notes

### Discovery Integration

```python
async def _discover_entity_projects(app: FastAPI) -> None:
    """Discover and register entity type project mappings."""
    from autom8_asana.auth.bot_pat import get_bot_pat
    from autom8_asana.models.business.registry import get_workspace_registry
    from autom8_asana.services.resolver import EntityProjectRegistry

    bot_pat = get_bot_pat()
    async with AsanaClient(token=bot_pat) as client:
        workspace_registry = get_workspace_registry()
        await workspace_registry.discover_async(client)

        entity_registry = EntityProjectRegistry.get_instance()

        PATTERNS = {
            "unit": ["units", "unit"],
            "business": ["business", "businesses"],
            "offer": ["offers", "offer"],
            "contact": ["contacts", "contact"],
        }

        for entity_type, patterns in PATTERNS.items():
            for pattern in patterns:
                gid = workspace_registry.get_by_name(pattern)
                if gid:
                    entity_registry.register(entity_type, gid, pattern)
                    break

        app.state.entity_project_registry = entity_registry
```

### Startup Failure Logging

```python
logger.error(
    "entity_resolver_discovery_failed",
    extra={
        "error": str(e),
        "remediation": (
            "Ensure workspace contains projects with names: "
            "Units (or Unit), Business (or Businesses), "
            "Offers (or Offer), Contacts (or Contact)"
        ),
    },
)
```

### Testing

Tests should use `WorkspaceProjectRegistry.reset()` and `EntityProjectRegistry.reset()` fixtures:

```python
@pytest.fixture(autouse=True)
def reset_registries():
    WorkspaceProjectRegistry.reset()
    EntityProjectRegistry.reset()
    yield
    WorkspaceProjectRegistry.reset()
    EntityProjectRegistry.reset()
```

## Related Decisions

- **ADR-0031**: Registry and Discovery Architecture (WorkspaceProjectRegistry foundation)
- **TDD-entity-resolver**: Technical design document for Entity Resolver
- **PRD-entity-resolver**: Requirements document mandating startup discovery

## References

- PRD-entity-resolver FR-004: Startup Project Discovery
- PRD-entity-resolver FR-005: ProjectRegistry Component
- PRD-entity-resolver US-005: Startup Project Discovery user story
