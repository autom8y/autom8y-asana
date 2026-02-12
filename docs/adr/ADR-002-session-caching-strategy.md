# ADR-002: Session Caching Strategy -- Automatic Per-Execution

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

Workflows resolve multiple entities across a single execution run. Without caching, the same Business entity might be fetched N times for N ContactHolders in ConversationAuditWorkflow. The stakeholder confirmed automatic caching (no duplicate API calls) is the desired approach.

Process entities are NOT warmable (TTL=60s, warmable=False), meaning workflows operate against mostly cold cache data. The existing S3/Redis cache has task-GID-level granularity.

Two caching strategies were considered:

1. **Automatic session cache**: ResolutionContext maintains an in-memory dict keyed by (entity_type, gid). All resolves within a single execution share results.
2. **Explicit cache**: Callers manage cache manually, passing previously resolved entities.

## Decision

**Automatic session-scoped caching within ResolutionContext, layered on top of the existing S3/Redis cache.**

```python
class ResolutionContext:
    _session_cache: dict[str, BusinessEntity]  # keyed by GID

    async def resolve_entity_async(self, ...) -> ResolutionResult[T]:
        # 1. Check session cache (in-memory, zero cost)
        # 2. Check shared cache (S3/Redis, existing infrastructure)
        # 3. Fetch from Asana API
        # 4. Store in both session cache and shared cache
```

### Cache Hierarchy

| Layer | Scope | TTL | Cost |
|-------|-------|-----|------|
| Session cache | Single execution | Execution lifetime | Zero (in-memory dict) |
| S3/Redis cache | Cross-execution | Per entity type (60s-3600s) | Low (existing infra) |
| Asana API | Authoritative | N/A | High (HTTP calls) |

### Invalidation

- Session cache: invalidated when ResolutionContext exits (context manager `__aexit__`)
- Session cache is never shared between executions
- No cross-session invalidation needed; each run gets fresh data

### Post-Creation Warming

When the lifecycle engine creates a new entity (Process, DNA Play), it immediately stores the entity in the session cache. This prevents a cold-cache re-fetch when subsequent steps in the same execution need that entity.

## Alternatives Considered

### Explicit Cache Management (Rejected)

Callers pass resolved entities between methods:

```python
business = await resolve_business(holder_gid)
phone = business.office_phone
csv = await fetch_csv(phone)
await upload(holder_gid, csv, business=business)  # pass business through
```

This creates parameter threading through the entire call chain. Every function signature grows with entities it does not directly use. It also cannot prevent duplicate fetches when two independent code paths need the same entity.

### Global Singleton Cache (Rejected)

A module-level cache shared across all workflow executions. This creates stale data risk when executions overlap (e.g., Lambda concurrency), and makes testing require explicit cache clearing between test cases.

## Consequences

### Positive

- Zero API call duplication within a single run
- Transparent to callers -- no cache key management
- Composition with existing S3/Redis cache avoids duplicate work across runs
- Post-creation warming eliminates cold-cache round trips for newly created entities

### Negative

- Memory usage grows proportionally to unique entities resolved per execution (bounded: typical workflow touches < 20 unique entities)
- Session cache does not persist across Lambda invocations (acceptable -- Lambda invocations are independent)
