# Project Context

> Quick orientation to the autom8_asana project

---

## What Is This?

**autom8_asana** is a standalone Python SDK wrapper for the Asana API, extracted from the monolithic autom8 platform's `apis/asana_api/` module.

### Purpose

- **Decouple** Asana operations from business logic
- **Enable reuse** across microservices without autom8 dependencies
- **Demonstrate** SDK extraction pattern for other APIs

### Key Constraint

**No business logic.** This is a pure API wrapper. Domain rules stay in consumers.

### Core Architecture

This SDK implements the **Asana-as-database** paradigm—treating Asana as a structured data store rather than just a project management tool. See [paradigm.md](skills/autom8-asana-domain/paradigm.md) for the foundational architecture.

---

## Current State

| Metric | Status |
|--------|--------|
| Stage | Production |
| Test files | 188 test files |
| Test coverage | Extensive (business model, detection, persistence) |
| SaveSession | Implemented (TDD-0010, TDD-0011) |
| Batch API | Implemented (TDD-0005) |
| Detection System | Implemented (TDD-DETECTION, ADR-0093/0094/0095) |

### Test Organization

| Module | Test Files | Focus |
|--------|-----------|-------|
| cache | 18 | Cache backends, staleness detection |
| dataframes | 15 | Polars DataFrame operations |
| persistence | 16 | SaveSession, change tracking, dependency graph |
| models/business | 20 | Entity models, detection, hydration, holders |
| clients | 8 | Resource client operations |
| transport | 4 | HTTP transport, retry, sync wrappers |

**Living docs**: See `/docs/INDEX.md` for current PRDs, TDDs, and ADRs

---

## Tech Stack Summary

| Component | Choice |
|-----------|--------|
| Python | 3.10+ |
| HTTP | httpx |
| Models | Pydantic v2 |
| Data | Polars |
| Tests | pytest-asyncio |

See `autom8-asana-domain/tech-stack.md` for full details.

---

## Core Patterns

### SaveSession (Unit of Work)

Deferred batch saves:

```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()
```

### Async-First

All interfaces are async; sync wrappers available via `sync_wrapper` decorator.

---

## For Full Details

### SDK Infrastructure (autom8-asana-domain skill)
- `skills/autom8-asana-domain/context.md` - Full extraction context
- `skills/autom8-asana-domain/asana-domain.md` - Asana resource hierarchy
- `skills/autom8-asana-domain/glossary.md` - SDK terminology
- `skills/autom8-asana-domain/code-conventions.md` - Code patterns
- `skills/autom8-asana-domain/repository-map.md` - Where code lives
- `skills/autom8-asana-domain/tech-stack.md` - Dependencies

### Business Entities (autom8-asana-business skill)
- `skills/autom8-asana-business/entity-lifecycle.md` - Define, detect, populate, navigate, persist
- `skills/autom8-asana-business/entity-reference.md` - All 7 entity types
- `skills/autom8-asana-business/detection.md` - 5-tier entity type detection
- `skills/autom8-asana-business/savesession.md` - SaveSession with business hierarchies
- `skills/autom8-asana-business/glossary.md` - Business terminology

---

## Living Documentation

All PRDs, TDDs, ADRs, and Test Plans are indexed at `/docs/INDEX.md`.
