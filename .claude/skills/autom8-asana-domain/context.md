# SDK Context

> Why autom8_asana exists and how it fits into the larger system

---

## What Is autom8_asana?

**autom8_asana** is a standalone Python SDK wrapper for the Asana API, extracted from the monolithic autom8 platform's `apis/asana_api/` module (~800 files).

### Purpose

1. **Decouple Asana operations from business logic** - Pure API wrapper, no domain rules
2. **Enable reuse across services** - Other microservices can use the SDK without pulling in autom8
3. **Demonstrate SDK extraction pattern** - Prototype for extracting other APIs (Meta, Google, OpenAI)

### What Moved vs What Stayed

| Moved to SDK | Stayed in autom8 |
|--------------|------------------|
| API clients (tasks, projects, sections) | Domain models (Offer, Business, Unit) |
| Pydantic resource models | Business logic managers |
| Batch API support | SQL integrations |
| SaveSession (Unit of Work) | AWS cache integrations |
| Transport layer (retry, pooling) | Slack/OpenAI/Meta integrations |

---

## Architecture Overview

```
Consumer Application (autom8, other services)
                    |
                    v
    +---------------------------------------+
    |          autom8_asana SDK             |
    |  +-------------------------------+    |
    |  | SaveSession (Unit of Work)    |    |  <-- Deferred batch saves
    |  +-------------------------------+    |
    |  +-------------------------------+    |
    |  | Resource Clients (TasksClient,|    |  <-- Type-safe API access
    |  | ProjectsClient, etc.)         |    |
    |  +-------------------------------+    |
    |  +-------------------------------+    |
    |  | Transport (httpx, retry)      |    |  <-- HTTP layer
    |  +-------------------------------+    |
    +---------------------------------------+
                    |
                    v
            Asana API (api.asana.com)
```

---

## Current State

**Stage**: Prototype (greenfield extraction)

| Metric | Status |
|--------|--------|
| Test coverage | ~0% (test infrastructure being built) |
| API parity | Core operations implemented |
| SaveSession | Fully implemented per TDD-0010, TDD-0011 |
| Batch API | Implemented per TDD-0005 |
| Documentation | ADRs and TDDs in /docs/ |

### Active Work

- **PRD-0009**: GA Readiness (final polish before production use)
- **TDD-0014**: Latest design documents
- **ADR-0035+**: Save Orchestration decisions

---

## Key Design Decisions

### 1. Async-First with Sync Wrappers (ADR-0002)

All primary interfaces are async. Sync wrappers use `sync_wrapper` decorator:

```python
# Primary interface
async def commit_async(self) -> SaveResult:
    ...

# Sync wrapper (auto-generated)
def commit(self) -> SaveResult:
    return sync_wrapper(self.commit_async)()
```

### 2. SaveSession Unit of Work (ADR-0035)

Deferred save pattern inspired by Django ORM:
- Track entities explicitly via `session.track(entity)`
- Snapshot-based dirty detection
- Dependency graph for parent-child relationships
- Automatic placeholder GID resolution for new entities

### 3. Protocol-Based Injection

SDK defines protocols; consumers implement:
- `AuthProtocol` - Token providers (PAT, OAuth)
- `CacheProtocol` - Cache backends (in-memory, Redis)

### 4. No Business Logic

Hard constraint: SDK contains zero domain rules. Business logic (what is an "Offer", campaign rules, etc.) stays in consumers.

---

## Extraction Constraints

| Constraint | Impact |
|------------|--------|
| Asana API rate limits | 1,500 req/min per PAT - must support backoff/retry |
| Backward compatibility | autom8 depends on current patterns; incremental adoption |
| Python 3.10+ | Match autom8 runtime (not 3.12+) |
| No SQL/AWS deps | SDK must be standalone, no autom8 infrastructure deps |

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Import footprint | Zero sql/, contente_api/, aws_api/ imports | Achieved |
| Test coverage | >=80% core modules | ~0% |
| Package size | <5MB wheel | On track |
| Cold import | <500ms | Not measured |
