# Engineer Readiness Summary: Session 4 P1 Implementation

**Date:** 2025-12-12
**Status:** READY FOR IMMEDIATE EXECUTION
**Target:** P1 Direct Methods (12 convenience wrappers)

---

## Executive Summary

**Sessions 1-3 are complete.** Discovery, Requirements (PRD-SDKUX), and Architecture (TDD-SDKUX + ADRs) are all done. The TDD has passed quality verification. Engineer is ready to begin Session 4: P1 Implementation.

**P1 Scope:** Add 12 new convenience methods to TasksClient (6 async + 6 sync wrappers) that internally use SaveSession to eliminate boilerplate.

**Complexity:** Module-level. Clear scope, straightforward pattern, no new infrastructure.

**Expected Duration:** 1-2 hours (implementation + tests + verification).

---

## What the Engineer Will Build

### The Ask (Concise)

Add 12 methods to `TasksClient`:

```python
# Async methods
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task
async def remove_tag_async(self, task_gid: str, tag_gid: str) -> Task
async def move_to_section_async(self, task_gid: str, section_gid: str, project_gid: str) -> Task
async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task
async def add_to_project_async(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
async def remove_from_project_async(self, task_gid: str, project_gid: str) -> Task

# Sync wrappers
def add_tag(self, task_gid: str, tag_gid: str) -> Task
def remove_tag(self, task_gid: str, tag_gid: str) -> Task
def move_to_section(self, task_gid: str, section_gid: str, project_gid: str) -> Task
def set_assignee(self, task_gid: str, assignee_gid: str) -> Task
def add_to_project(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
def remove_from_project(self, task_gid: str, project_gid: str) -> Task
```

### The Pattern

Every async method follows this exact template:

```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task without explicit SaveSession."""
    async with SaveSession(self._client) as session:
        session.add_tag(task_gid, tag_gid)
        await session.commit_async()
    return await self.get_async(task_gid)
```

Every sync wrapper follows this exact template:

```python
def add_tag(self, task_gid: str, tag_gid: str) -> Task:
    """Add tag to task (sync)."""
    return self._add_tag_sync(task_gid, tag_gid)

@sync_wrapper("add_tag_async")
async def _add_tag_sync(self, task_gid: str, tag_gid: str) -> Task:
    return await self.add_tag_async(task_gid, tag_gid)
```

That's it. Copy the pattern 12 times, update method names and SaveSession calls. Done.

---

## Ready State Verification

### Code Artifacts Prepared

| Artifact | Location | Status |
|----------|----------|--------|
| Implementation Context | `/docs/initiatives/SESSION-4-IMPLEMENTATION-CONTEXT.md` | ✓ Created |
| Quality Gate Verification | `/docs/initiatives/TDD-QUALITY-GATE-SESSION-4.md` | ✓ Created |
| TDD Full Spec | `/docs/design/TDD-SDKUX.md` | ✓ Ready |
| PRD Requirements | `/docs/design/PRD-SDKUX.md` | ✓ Ready |
| Target File | `/src/autom8_asana/clients/tasks.py` | ✓ Ready |
| Test File | `/tests/unit/test_tasks_client.py` | ✓ Ready |

### Dependency Verification

| Dependency | Status | Available |
|-----------|--------|-----------|
| SaveSession | Implementation verified | ✓ `/persistence/session.py` |
| TasksClient | Current implementation | ✓ `/clients/tasks.py` |
| Task model | Current implementation | ✓ `/models/task.py` |
| @sync_wrapper | Pattern in use | ✓ Existing methods |
| @error_handler | Pattern in use | ✓ Existing methods |
| SaveSession methods (add_tag, remove_tag, etc.) | Already exist | ✓ Verified in code |

**Result:** No blockers. All dependencies available.

### Quality Gate Completion

| Gate | Status |
|------|--------|
| PRD Traceability | ✓ PASS |
| Method Specifications | ✓ PASS |
| Integration Points | ✓ PASS |
| Testing Strategy | ✓ PASS |
| No Blocking Questions | ✓ PASS |
| Scope Boundaries | ✓ PASS |
| Risk Mitigations | ✓ PASS |
| Backward Compatibility | ✓ PASS |

**Overall:** TDD-SDKUX §1 is ready for engineer implementation.

---

## Engineer Success Criteria

### Completion Checklist

**Implementation:**
- [ ] All 12 methods added to TasksClient
- [ ] Async methods (6) use SaveSession pattern
- [ ] Sync wrappers (6) use @sync_wrapper pattern
- [ ] All methods return Task objects
- [ ] All methods use @error_handler decorator
- [ ] All docstrings complete

**Testing:**
- [ ] All P1 tests written and passing
- [ ] test_add_tag_async returns Task
- [ ] test_add_tag_async raises APIError on invalid
- [ ] test_add_tag_sync delegates to async
- [ ] Similar tests for all 6 async methods
- [ ] Similar tests for all 6 sync wrappers
- [ ] Integration test validates SaveSession usage

**Quality:**
- [ ] pytest passes (all tests including existing)
- [ ] mypy passes (type safe)
- [ ] ruff passes (linting)
- [ ] No regressions in existing tests
- [ ] Backward compatible

**Verification Commands:**
```bash
# Run tests
pytest tests/unit/test_tasks_client.py -v

# Type check
mypy src/autom8_asana/clients/tasks.py

# Lint
ruff check src/autom8_asana/clients/tasks.py

# Full suite (ensure no regressions)
pytest
```

---

## What Engineer Must Know

### Key Points

1. **SaveSession methods already exist.** Don't implement them. Just call them:
   - `session.add_tag(task_gid, tag_gid)`
   - `session.remove_tag(task_gid, tag_gid)`
   - `session.move_to_section(task_gid, section_gid, project_gid)`
   - `session.set_assignee(task_gid, assignee_gid)`
   - `session.add_to_project(task_gid, project_gid, section_gid)`
   - `session.remove_from_project(task_gid, project_gid)`

2. **This is P1 only.** Don't start P2, P3, P4, P5. They'll be next sessions.

3. **All 12 methods follow the same pattern.** No variation. Boring, repetitive work is good here.

4. **No new imports needed.** SaveSession already imported in TasksClient. Use `self._client` for client reference.

5. **Tests are independent from implementation.** Can write tests first or after; both work.

6. **Backward compatibility guaranteed.** All existing tests must pass. If any fail, file a blocker.

### Non-Goals

Do NOT do in Session 4:
- Create new files (P1 only touches TasksClient)
- Modify Task model (that's P4)
- Add CustomFieldAccessor methods (that's P2)
- Create NameResolver (that's P3)
- Enhance AsanaClient constructor (that's P5)

### What to Do If Stuck

1. **Type error?** Check the pattern in existing methods (`get_async`, `create_async`). Copy the style.
2. **SaveSession method not found?** Double-check spelling and location.
3. **Test failing?** Mock the SaveSession call and `get_async` call (see examples in SESSION-4-IMPLEMENTATION-CONTEXT.md).
4. **Scope question?** Check this doc or TDD-SDKUX. If still unclear, post blocker.

---

## Next Steps After Session 4

After P1 is complete and committed:

1. **Session 5a (Parallel):** P2 - CustomFieldAccessor dict syntax enhancement
2. **Session 5b (After P1):** P3 - NameResolver and name resolution integration
3. **Session 6a (After P2):** P4 - Task.save() and Task.refresh() auto-tracking
4. **Session 6b (Anytime):** P5 - AsanaClient constructor enhancement

Each session builds on prior work but P1 is standalone. Once P1 is done, P2 and P5 can run in parallel.

---

## File Locations (Copy-Paste Ready)

### Target Files

```
Implementation:
  /Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py
  (Insert P1 methods after line 419, before list_async)

Tests:
  /Users/tomtenuta/Code/autom8_asana/tests/unit/test_tasks_client.py
  (Add P1 test cases)

SaveSession (reference):
  /Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py
  (Don't modify; just study the add_tag, remove_tag, etc. methods)
```

### Reference Documents

```
TDD Spec:
  /Users/tomtenuta/Code/autom8_asana/docs/design/TDD-SDKUX.md

PRD Requirements:
  /Users/tomtenuta/Code/autom8_asana/docs/design/PRD-SDKUX.md

Implementation Context (this session):
  /Users/tomtenuta/Code/autom8_asana/docs/initiatives/SESSION-4-IMPLEMENTATION-CONTEXT.md

Quality Gate:
  /Users/tomtenuta/Code/autom8_asana/docs/initiatives/TDD-QUALITY-GATE-SESSION-4.md
```

---

## Handoff Communication

When invoking @principal-engineer:

```
@principal-engineer

**Session 4: P1 Direct Methods - Immediate Start**

**What you're building:**
12 convenience methods on TasksClient (6 async + 6 sync wrappers).
Each wraps SaveSession internally, returns Task.

**Where:**
/src/autom8_asana/clients/tasks.py (insert after line 419)

**Pattern:**
- Async: `async with SaveSession(...) as session: session.METHOD(); return Task`
- Sync: Use @sync_wrapper decorator

**Tests:**
/tests/unit/test_tasks_client.py

**Success:**
All 12 methods implemented, tests passing, no regressions.

**Documents:**
- Implementation context: docs/initiatives/SESSION-4-IMPLEMENTATION-CONTEXT.md
- TDD spec: docs/design/TDD-SDKUX.md §1
- Quality gate: docs/initiatives/TDD-QUALITY-GATE-SESSION-4.md

Ready to go. No blockers.
```

---

## Sign-Off

**Orchestrator Assessment:**
- TDD-SDKUX is complete and verified ✓
- Quality gates all passing ✓
- Integration points clear ✓
- No blockers or ambiguities ✓
- Engineer can start immediately ✓

**Recommendation:**
Proceed with immediate @principal-engineer invocation for Session 4 P1 Implementation.

---
