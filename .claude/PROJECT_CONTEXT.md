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

---

## Current State

| Metric | Status |
|--------|--------|
| Stage | Prototype |
| Test coverage | ~0% (infrastructure being built) |
| SaveSession | Implemented (TDD-0010, TDD-0011) |
| Batch API | Implemented (TDD-0005) |

**Active work**: PRD-0009 (GA Readiness), ADR-0035+ (Save Orchestration)

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

SDK-specific patterns, Asana domain model, code conventions, and repository structure are in the **autom8-asana-domain** skill:

- `skills/autom8-asana-domain/context.md` - Full extraction context
- `skills/autom8-asana-domain/asana-domain.md` - Asana resource hierarchy
- `skills/autom8-asana-domain/glossary.md` - SDK terminology
- `skills/autom8-asana-domain/code-conventions.md` - Code patterns
- `skills/autom8-asana-domain/repository-map.md` - Where code lives
- `skills/autom8-asana-domain/tech-stack.md` - Dependencies

---

## Living Documentation

All PRDs, TDDs, ADRs, and Test Plans are indexed at `/docs/INDEX.md`.
