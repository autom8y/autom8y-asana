# ADR-0059: Direct Methods vs. SaveSession Actions

**Status:** Accepted
**Date:** 2025-12-12
**Context:** Session 3 Architecture Design (PRD-SDKUX, P1)

---

## Problem

Priority 1 requires convenience methods on TasksClient for common operations (add_tag, remove_tag, move_to_section, etc.). Two architectural approaches:

1. **Direct Methods on TasksClient:** Add methods that wrap SaveSession internally
   - Example: `await client.tasks.add_tag_async(task_gid, tag_gid)`
   - Pattern: Method creates SaveSession, commits, returns updated Task

2. **Enhance SaveSession with convenience methods:** Add static methods to SaveSession
   - Example: `async with SaveSession(client) as s: await s.add_tag_convenience(...)`
   - Pattern: SaveSession becomes the center of all operations

## Decision

Implement **Direct Methods on TasksClient**, not SaveSession enhancements.

Each method wraps SaveSession internally and returns updated Task objects.

```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    async with SaveSession(self._client) as session:
        session.add_tag(task_gid, tag_gid)
        await session.commit_async()
    return await self.get_async(task_gid)
```

## Rationale

### 1. SaveSession is for Batch Operations
SaveSession's core purpose is to batch multiple operations. Adding convenience methods violates separation of concerns.

**Discovery Evidence:** Lines 118-155 in `persistence/session.py` show SaveSession is initialized with batch_size and max_concurrent parameters. It's explicitly designed for batch semantics.

### 2. Users Already Understand TasksClient
The SDK has existing methods on TasksClient (get_async, create_async, update_async, list_async). Adding new methods there is intuitive and consistent.

**Discovery Evidence:** Lines 24-342 in `clients/tasks.py` show TasksClient already returns Task objects. Users expect that pattern.

### 3. Composition Wins Over Extension
SaveSession should remain a focused unit-of-work pattern. Direct methods compose SaveSession, don't extend it.

- Easier to test: Task operations can be tested independently
- Easier to understand: Each component has clear purpose
- Easier to extend: New operations add methods, not SaveSession state

### 4. "Best of Both Worlds"
Direct methods get simplicity (1-2 lines) while SaveSession remains for advanced batch operations.

Users can:
- Use direct methods for single operations: `await client.tasks.add_tag_async(gid, tag)`
- Use SaveSession for batch: `async with SaveSession(client) as s: [batch operations]`

## Consequences

### Positive
- TasksClient grows by 12 methods (add_tag, remove_tag, move_to_section, set_assignee, add_to_project, remove_from_project × 2 for async/sync), but responsibility remains clear
- SaveSession unchanged, reduces risk
- Users have intuitive two-level API (convenience vs. power)
- Consistent with existing TasksClient patterns

### Negative
- Direct methods create implicit SaveSession instances (small memory overhead, acceptable)
- Users cannot batch direct method calls (must use explicit SaveSession for batching)

### Neutral
- Each direct method call creates one SaveSession (no pooling needed; sessions are lightweight)
- Network calls bundled by SaveSession batching, not by direct method calls

## Implementation

Each async method follows this pattern:
```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task without explicit SaveSession."""
    async with SaveSession(self._client) as session:
        session.add_tag(task_gid, tag_gid)
        await session.commit_async()
    return await self.get_async(task_gid)
```

Sync wrappers use `@sync_wrapper` decorator:
```python
def add_tag(self, task_gid: str, tag_gid: str) -> Task:
    return self._add_tag_sync(task_gid, tag_gid)

@sync_wrapper("add_tag_async")
async def _add_tag_sync(self, task_gid: str, tag_gid: str) -> Task:
    return await self.add_tag_async(task_gid, tag_gid)
```

## Alternatives Considered

### Alternative A: SaveSession Convenience Methods
```python
async with SaveSession(client) as session:
    await session.add_tag_convenience(task_gid, tag_gid)
```

**Rejected:** Violates SaveSession's single responsibility (batch operations). Adds complexity to session lifecycle.

### Alternative B: Task Methods Only
```python
task = await client.tasks.get(task_gid)
await task.add_tag(tag_gid)
```

**Rejected:** Requires client reference on Task before P4. Tighter coupling between Task and client.

### Alternative C: Both (Direct Methods + SaveSession Methods)
**Rejected:** Duplication; violates DRY principle. Maintenance burden if either changes.

## Validation

**Discovery Question Q1 (Line 24-36):** "Is it technically feasible to add async methods that wrap SaveSession internally?"

**Answer:** ✓ YES. Lines 28-36 show TasksClient already follows this pattern (get_async returns Task; create_async returns Task; update_async returns Task).

**Discovery Question Q2 (Lines 61-92):** "Do existing TasksClient methods return Task objects?"

**Answer:** ✓ YES. All current methods return Task objects or dict with raw=True. Direct methods can follow same pattern.

## Decision Log

- **2025-12-12:** Architect chose Direct Methods after weighing SaveSession cohesion vs. API intuitiveness
- **Blocking Questions:** None remaining (all answered in DISCOVERY-SDKUX-001)

---
