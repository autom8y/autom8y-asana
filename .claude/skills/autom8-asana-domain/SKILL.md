# autom8_asana SDK Domain

> Async-first Asana API client with Unit of Work pattern

---

## Activation Triggers

**Use this skill when**:
- Working with SaveSession, Unit of Work, or batch save patterns
- Implementing Asana resource operations (tasks, projects, sections, custom fields)
- Designing async client patterns or sync wrappers
- Adding cache backends or transport layer modifications
- Understanding SDK directory structure and module organization
- Writing Pydantic v2 models for Asana resources
- Working with action operations (add_tag, move_to_section, add_dependency)

**Keywords**: SaveSession, ActionOperation, batch operation, Asana resource, Unit of Work, async client, httpx, Pydantic v2, cache protocol, async-first, pagination cursor

**File patterns**: `src/autom8_asana/**/*.py`, `tests/**/*.py`

---

## What This SDK Is

**autom8_asana** is a standalone Python SDK wrapper for the Asana API, extracted from the monolithic autom8 platform. It provides:

- **SaveSession**: Unit of Work pattern for deferred, batched saves
- **Resource Clients**: Type-safe async clients for each Asana resource type
- **Batch API**: Efficient bulk operations with automatic chunking
- **Cache Protocol**: Pluggable caching backends (in-memory, Redis)
- **Action Operations**: Tag, project, section, and dependency management

**Not business logic** - this is a pure API wrapper. Domain rules stay in consumers.

---

## Quick Reference

| I need to... | See |
|--------------|-----|
| Understand SDK purpose and extraction context | [context.md](context.md) |
| Work with SaveSession or batch operations | [code-conventions.md](code-conventions.md) |
| Understand Asana resource hierarchy | [asana-domain.md](asana-domain.md) |
| Check SDK-specific terminology | [glossary.md](glossary.md) |
| Find where code lives | [repository-map.md](repository-map.md) |
| Check dependencies and tools | [tech-stack.md](tech-stack.md) |

---

## Key Constraints

- **Python 3.10+** (not 3.12+ - must support autom8 runtime)
- **Async-first** with sync wrappers via `sync_wrapper` decorator
- **No business logic** - pure API wrapper, domain rules stay in consumers
- **Protocol-based DI** - consumers implement `AuthProtocol`, `CacheProtocol`
- **Pydantic v2** for all models (not v1)
- **httpx** for HTTP transport (not requests/aiohttp)

---

## Core Patterns

### SaveSession (Unit of Work)

```python
async with SaveSession(client) as session:
    session.track(task)           # Register for change tracking
    task.name = "Updated"         # Modify tracked entity
    session.track(new_task)       # Track new entity (temp GID)
    result = await session.commit_async()  # Execute all changes
```

### Action Operations

```python
session.add_tag(task_gid, tag_gid)
session.remove_tag(task_gid, tag_gid)
session.add_to_project(task_gid, project_gid, section_gid=None)
session.move_to_section(task_gid, section_gid)
session.add_dependency(task_gid, dependency_gid)
```

### Resource Client Pattern

```python
# All clients follow this pattern
tasks = await client.tasks.list(project_gid, opt_fields=["name", "completed"])
task = await client.tasks.get(task_gid)
await client.tasks.update(task_gid, name="New Name")
```

---

## Progressive References

| Document | Lines | Content |
|----------|-------|---------|
| [context.md](context.md) | ~90 | SDK extraction context, architecture, why it exists |
| [asana-domain.md](asana-domain.md) | ~100 | Asana resource hierarchy, API patterns |
| [glossary.md](glossary.md) | ~100 | SaveSession, GID, ActionOperation, EntityState |
| [code-conventions.md](code-conventions.md) | ~120 | Async patterns, Pydantic v2, error handling |
| [repository-map.md](repository-map.md) | ~80 | /batch, /cache, /clients, /models, /persistence |
| [tech-stack.md](tech-stack.md) | ~80 | httpx, Pydantic v2, Polars, pytest-asyncio |

---

## When to Use Standards Skill Instead

The **standards** skill contains generic patterns that may not apply to this SDK:
- Its `repository-map.md` describes `/api`, `/domain`, `/infrastructure` structure
- Its `code-conventions.md` focuses on web API patterns

For SDK-specific patterns, use **this skill**. For general Python/testing patterns, standards may still apply.
