# PRD: SDK Functional Parity Initiative

## Metadata
- **PRD ID**: PRD-0007
- **Status**: Draft
- **Version**: 1.0
- **Author**: Requirements Analyst
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **Stakeholders**: autom8 team, SDK consumers, API integrators
- **Related PRDs**:
  - [PRD-0005](PRD-0005-save-orchestration.md) (Save Orchestration Layer - prerequisite)
  - [PRD-0006](PRD-0006-action-endpoint-support.md) (Action Endpoint Support - current implementation)
- **Related ADRs**:
  - [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) (Unit of Work Pattern)
  - [ADR-0040](../decisions/ADR-0040-partial-failure-handling.md) (Partial Failure Handling)
  - [ADR-0042](../decisions/ADR-0042-action-operation-types.md) (ActionType Enum)
  - [ADR-0009](../decisions/ADR-0009-attachment-multipart-handling.md) (Attachment Handling)

---

## Problem Statement

The autom8_asana SDK persistence layer has achieved core Save Orchestration functionality with 327 tests passing. However, developers still cannot perform common Asana operations through SaveSession, forcing them to use direct API calls outside the deferred execution model.

**Current Coverage Gap**:

| Operation Category | Asana API Coverage | SaveSession Coverage | Gap |
|--------------------|-------------------|---------------------|-----|
| Tags | 100% | 100% | None |
| Projects | 100% | 100% | None |
| Dependencies | 50% (add/remove) | 50% | Dependents missing |
| Sections | 100% | 100% | None |
| Followers | 100% | 0% | Full gap |
| Likes | 100% | 0% | Full gap |
| Comments | 100% | 0% | Full gap |
| Positioning | 100% | 0% | Full gap |

**Developer Pain Points**:

1. **Workflow Disruption**: Developers must exit SaveSession to add followers or comments, breaking the Unit of Work pattern.

```python
# Current painful pattern
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)
    task.name = "Updated"
    await session.commit_async()

# Must make separate calls outside session
await client.tasks.add_followers_async("123", followers=["user_gid"])
await client.stories.create_async("123", text="Comment")
```

2. **Inconsistent Error Handling**: Actions outside SaveSession don't benefit from partial failure semantics.

3. **Lost Batching Opportunity**: Even though action endpoints are not batch-eligible, having them in the session provides consistent execution ordering and logging.

4. **Positioning Limitations**: Cannot specify task ordering when adding to projects or sections.

**Target State**:

```python
# Desired pattern - all operations through SaveSession
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)
    task.name = "Updated"

    session.add_follower(task, "user_gid") \
           .add_comment(task, "Status update") \
           .add_to_project(task, project, insert_after=other_task)

    result = await session.commit_async()
```

**Impact of Not Solving**:
1. Developers bypass SaveSession for common operations, reducing SDK value
2. Error handling becomes fragmented across multiple call sites
3. Logging and observability are inconsistent
4. SDK perceived as incomplete compared to raw API usage

---

## Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Action endpoint coverage | 92% of Asana task actions | Endpoint audit vs implementation |
| New action method count | 9 new methods + 2 extended | API surface review |
| Backward compatibility | 0 regressions | All 327 existing tests pass |
| Type safety | 100% mypy strict compliance | CI mypy check |
| Documentation coverage | 100% of new methods documented | Docstring audit |
| Error message clarity | 100% include resolution guidance | Error message review |

---

## Scope

### In Scope

**Follower Management**:
- `add_follower(task, user)` - Add single follower
- `remove_follower(task, user)` - Remove single follower
- `add_followers(task, users)` - Add multiple followers
- `remove_followers(task, users)` - Remove multiple followers

**Dependent Relationship Management** (inverse of dependencies):
- `add_dependent(task, dependent_task)` - Add a task that depends on this task
- `remove_dependent(task, dependent_task)` - Remove a dependent task

**Like/Unlike Operations**:
- `add_like(task)` - Like task as current authenticated user
- `remove_like(task)` - Unlike task

**Comment Operations**:
- `add_comment(task, text, *, html_text=None)` - Add comment with deferred execution

**Positioning Extensions**:
- Extend `add_to_project()` with `insert_before` and `insert_after` parameters
- Extend `move_to_section()` with `insert_before` and `insert_after` parameters

**Error Handling Enhancements**:
- Invalid user GID detection
- Invalid task GID detection
- Positioning conflict detection (both insert_before and insert_after specified)
- Session closed state validation

### Out of Scope

**Explicitly Excluded from PRD-0007**:
- Attachments - Already handled via AttachmentsClient per ADR-0009 (multipart doesn't fit action pattern)
- Story/comment editing - Asana API limitation (stories are immutable after creation)
- Subtask creation via action endpoint - Already handled via parent field in standard CRUD
- Batch execution of action endpoints - Asana API limitation

**Deferred to Future PRDs**:
- Webhook integration for follower/comment notifications
- Comment threading/replies
- Rich text comment editing interface
- Bulk follower operations across multiple tasks

---

## Requirements

### Positioning Requirements (FR-POS-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-POS-001 | `add_to_project()` shall accept optional `insert_before` parameter | Must | Parameter accepts Task, NameGid, or GID string |
| FR-POS-002 | `add_to_project()` shall accept optional `insert_after` parameter | Must | Parameter accepts Task, NameGid, or GID string |
| FR-POS-003 | SDK shall raise `PositioningConflictError` when both `insert_before` and `insert_after` are specified | Must | Clear error message: "Cannot specify both insert_before and insert_after" |
| FR-POS-004 | `move_to_section()` shall accept optional `insert_before` parameter | Must | Parameter accepts Task, NameGid, or GID string |
| FR-POS-005 | `move_to_section()` shall accept optional `insert_after` parameter | Must | Parameter accepts Task, NameGid, or GID string |
| FR-POS-006 | Positioning parameters shall support temp GID resolution | Must | If referencing newly-created task, temp GID resolved before API call |
| FR-POS-007 | Positioning parameters shall be included in API payload | Must | `insert_before` or `insert_after` added to request body |
| FR-POS-008 | Omitting both positioning parameters shall maintain existing behavior | Must | Task added at default position (end of list) |

### Follower Management Requirements (FR-FOL-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-FOL-001 | SDK shall provide `session.add_follower(task, user)` method | Must | Queues ADD_FOLLOWER action; executes on commit |
| FR-FOL-002 | SDK shall provide `session.remove_follower(task, user)` method | Must | Queues REMOVE_FOLLOWER action; executes on commit |
| FR-FOL-003 | SDK shall provide `session.add_followers(task, users)` method for batch adding | Must | Creates one ActionOperation per user in list |
| FR-FOL-004 | SDK shall provide `session.remove_followers(task, users)` method for batch removal | Must | Creates one ActionOperation per user in list |
| FR-FOL-005 | Follower methods shall accept User model, NameGid, or GID string | Must | All three input types work correctly |
| FR-FOL-006 | Follower methods shall return self for fluent chaining | Must | `session.add_follower(t, u1).add_follower(t, u2)` works |
| FR-FOL-007 | ADD_FOLLOWER shall call `POST /tasks/{gid}/addFollowers` | Must | API endpoint verified via integration test |
| FR-FOL-008 | REMOVE_FOLLOWER shall call `POST /tasks/{gid}/removeFollowers` | Must | API endpoint verified via integration test |
| FR-FOL-009 | Each user in batch methods shall generate individual ActionOperation | Must | Clear error attribution per user if failure |
| FR-FOL-010 | Follower operations shall support temp GID for newly-created tasks | Must | Temp GID resolved before API call |

### Dependent Relationship Requirements (FR-DEP-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-DEP-001 | SDK shall provide `session.add_dependent(task, dependent_task)` method | Must | Queues ADD_DEPENDENT action; executes on commit |
| FR-DEP-002 | SDK shall provide `session.remove_dependent(task, dependent_task)` method | Must | Queues REMOVE_DEPENDENT action; executes on commit |
| FR-DEP-003 | ADD_DEPENDENT shall call `POST /tasks/{gid}/addDependents` | Must | API endpoint verified via integration test |
| FR-DEP-004 | REMOVE_DEPENDENT shall call `POST /tasks/{gid}/removeDependents` | Must | API endpoint verified via integration test |
| FR-DEP-005 | `add_dependent(A, B)` shall make B depend on A | Must | Relationship: B is blocked until A completes |
| FR-DEP-006 | Dependent methods shall accept Task model or GID string | Must | Both input types work correctly |
| FR-DEP-007 | Dependent methods shall return self for fluent chaining | Must | `session.add_dependent(a, b).add_dependent(a, c)` works |
| FR-DEP-008 | Dependent operations shall support temp GID resolution | Must | Temp GIDs resolved before API call |
| FR-DEP-009 | Interface shall be symmetric with existing dependency methods | Should | `add_dependent` is inverse of `add_dependency` |

### Like/Unlike Requirements (FR-LIK-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-LIK-001 | SDK shall provide `session.add_like(task)` method | Must | Queues ADD_LIKE action; executes on commit |
| FR-LIK-002 | SDK shall provide `session.remove_like(task)` method | Must | Queues REMOVE_LIKE action; executes on commit |
| FR-LIK-003 | ADD_LIKE shall call `POST /tasks/{gid}/addLike` | Must | No request body needed per Asana API |
| FR-LIK-004 | REMOVE_LIKE shall call `POST /tasks/{gid}/removeLike` | Must | No request body needed per Asana API |
| FR-LIK-005 | Like operations shall use current authenticated user | Must | No user parameter required; uses OAuth context |
| FR-LIK-006 | Like methods shall return self for fluent chaining | Must | `session.add_like(t1).add_like(t2)` works |
| FR-LIK-007 | Like operations shall be idempotent | Should | Liking already-liked task does not error |
| FR-LIK-008 | Unlike operations shall be idempotent | Should | Unliking non-liked task does not error |
| FR-LIK-009 | Like operations shall support temp GID for newly-created tasks | Must | Temp GID resolved before API call |

### Comment Requirements (FR-CMT-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CMT-001 | SDK shall provide `session.add_comment(task, text)` method | Must | Queues ADD_COMMENT action; executes on commit |
| FR-CMT-002 | `add_comment()` shall accept optional `html_text` parameter | Should | Rich text support via optional keyword argument |
| FR-CMT-003 | ADD_COMMENT shall call `POST /tasks/{gid}/stories` | Must | Creates story of type "comment" |
| FR-CMT-004 | Comment text shall be included in request payload | Must | `{"data": {"text": "...", "html_text": "..."}}` |
| FR-CMT-005 | Comments shall use deferred execution | Must | Comment not created until commit() called |
| FR-CMT-006 | `add_comment()` shall return self for fluent chaining | Must | `session.add_comment(t, "A").add_comment(t, "B")` works |
| FR-CMT-007 | Comment operations shall support temp GID for newly-created tasks | Must | Temp GID resolved before API call |
| FR-CMT-008 | Empty comment text shall raise validation error | Must | Error raised during action queuing, not at commit |
| FR-CMT-009 | html_text without text shall work (Asana extracts plain text) | Should | Only html_text provided is valid |

### Error Handling Requirements (FR-ERR-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ERR-001 | Invalid user GID shall produce clear error message | Must | Error includes "Invalid user GID" and the GID value |
| FR-ERR-002 | Invalid task GID shall produce clear error message | Must | Error includes "Invalid task GID" and the GID value |
| FR-ERR-003 | PositioningConflictError shall be raised for conflicting positioning | Must | Both insert_before and insert_after specified |
| FR-ERR-004 | Session closed operations shall raise SessionClosedError | Must | All new methods check session state |
| FR-ERR-005 | Rate limit errors shall be handled by existing infrastructure | Must | TokenBucketRateLimiter handles retries |
| FR-ERR-006 | Action errors shall include action type in error context | Must | `error.action_type` available for debugging |
| FR-ERR-007 | Temp GID resolution failures shall produce clear error | Must | Error: "Cannot resolve temp GID: {gid}" |
| FR-ERR-008 | Empty follower list in batch methods shall be no-op | Should | No error raised; no API calls made |

---

### Non-Functional Requirements

#### Type Safety Requirements (NFR-TYPE-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-TYPE-001 | 100% mypy strict compliance | 0 errors | CI mypy --strict |
| NFR-TYPE-002 | All method parameters typed | 100% coverage | Type annotation audit |
| NFR-TYPE-003 | Return types specified | 100% coverage | Type annotation audit |
| NFR-TYPE-004 | Union types for flexible inputs | User \| NameGid \| str | API review |

#### Performance Requirements (NFR-PERF-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Individual action operation | < 500ms p95 | Profiler excluding network |
| NFR-PERF-002 | Action queuing overhead | < 1ms per operation | Profiler measurement |
| NFR-PERF-003 | Temp GID resolution | < 1ms per resolution | Profiler measurement |
| NFR-PERF-004 | No performance regression for existing methods | < 5% overhead | Benchmark comparison |

#### Reliability Requirements (NFR-REL-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-REL-001 | Partial failure handling | Per ADR-0040 | Integration test with intentional failures |
| NFR-REL-002 | Idempotent like/unlike | No error on repeat operation | Unit test |
| NFR-REL-003 | Thread safety | Zero race conditions | Concurrent test suite |
| NFR-REL-004 | Resource cleanup | No memory leaks | 24-hour stability test |

#### Backward Compatibility Requirements (NFR-COMPAT-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | Existing 327 tests pass | 0 failures | CI test suite |
| NFR-COMPAT-002 | Existing method signatures unchanged | 0 breaking changes | API diff analysis |
| NFR-COMPAT-003 | Extended methods default to current behavior | Omitting new params = old behavior | Unit test |
| NFR-COMPAT-004 | ActionType enum extends existing values | No renumbering | Enum audit |

#### Documentation Requirements (NFR-DOC-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-DOC-001 | All new methods have docstrings | 100% coverage | Docstring audit |
| NFR-DOC-002 | Docstrings include usage examples | 1+ example per method | Docstring audit |
| NFR-DOC-003 | Error conditions documented | All exceptions listed | Docstring audit |
| NFR-DOC-004 | API endpoint documented in docstring | Endpoint path included | Docstring audit |

---

## User Stories / Use Cases

### US-001: Add Followers to Task

As a developer, I want to add followers to a task through SaveSession so that follower assignments are deferred with other changes.

**Scenario**:
1. Developer retrieves a task
2. Developer calls `session.add_follower(task, user)` for each follower
3. Developer calls `commit()`
4. SDK executes `POST /tasks/{gid}/addFollowers` for each follower
5. Task now has the new followers

**Acceptance**: Followers added via action endpoint within SaveSession.

### US-002: Add Multiple Followers at Once

As a developer, I want to add multiple followers in a single method call for cleaner code.

**Scenario**:
```python
async with SaveSession(client) as session:
    session.add_followers(task, [user_a, user_b, user_c])
    result = await session.commit_async()

    # If user_b GID is invalid, user_a and user_c still added
    # result.failed shows user_b failure
```

**Acceptance**: Each follower creates individual ActionOperation; partial failures attributed correctly.

### US-003: Create Dependent Task Relationship

As a developer, I want to specify that tasks depend on the current task (dependents) without mental gymnastics about relationship direction.

**Scenario**:
```python
# Task C depends on Task A (A must complete before C can start)
# Current way (confusing): add_dependency(C, A)
# New way (clearer): add_dependent(A, C)  # A has C as dependent

session.add_dependent(milestone_task, subtask_1)
session.add_dependent(milestone_task, subtask_2)
await session.commit_async()
```

**Acceptance**: `add_dependent(A, B)` creates relationship where B depends on A.

### US-004: Like a Task

As a developer, I want to like tasks through SaveSession for consistent deferred execution.

**Scenario**:
```python
async with SaveSession(client) as session:
    session.add_like(important_task)
    session.add_like(flagged_task)
    await session.commit_async()
```

**Acceptance**: Like operations execute on commit; use current authenticated user.

### US-005: Add Comment to Task

As a developer, I want to add comments through SaveSession so comments are created with proper sequencing after task updates.

**Scenario**:
```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Completed: Original Name"
    task.completed = True

    session.add_comment(task, "Marking as complete per review feedback")
    await session.commit_async()
```

**Acceptance**: Comment created after task update; appears in task's story feed.

### US-006: Position Task When Adding to Project

As a developer, I want to specify where a task appears in the project list.

**Scenario**:
```python
async with SaveSession(client) as session:
    # Add task after the header task
    session.add_to_project(task, project, insert_after=header_task)

    # Add another task before the footer
    session.add_to_project(other_task, project, insert_before=footer_task)

    await session.commit_async()
```

**Acceptance**: Tasks positioned correctly in project view.

### US-007: Position Task in Section

As a developer, I want to control task order when moving to a section.

**Scenario**:
```python
async with SaveSession(client) as session:
    # Move to top of section
    session.move_to_section(urgent_task, in_progress_section, insert_before=first_task)
    await session.commit_async()
```

**Acceptance**: Task appears at specified position in section.

### US-008: Chain Multiple Action Operations

As a developer, I want fluent chaining for concise code.

**Scenario**:
```python
async with SaveSession(client) as session:
    session.add_follower(task, reviewer) \
           .add_comment(task, "Ready for review") \
           .add_like(task) \
           .move_to_section(task, review_section, insert_before=oldest_review)

    await session.commit_async()
```

**Acceptance**: All chained methods return self; all operations execute on commit.

---

## Design Decisions

### Decision 1: One ActionOperation Per Follower

**Decision**: `add_followers(task, [u1, u2, u3])` creates three ActionOperations, not one with a list.

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Individual operations (chosen)** | Clear error attribution; partial success possible | More ActionOperation objects |
| **Single operation with list** | Fewer objects; closer to API | All-or-nothing failure; unclear which user failed |

Error attribution is more important than object count. If user_2 has an invalid GID, developers need to know exactly which follower failed.

### Decision 2: Deferred Comment Execution

**Decision**: Comments are queued and executed on commit, not immediately.

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Deferred (chosen)** | Consistent with other actions; proper sequencing | Comment not visible until commit |
| **Immediate** | Instant feedback | Breaks Unit of Work pattern; inconsistent |

Comments should follow the same deferred pattern as all other SaveSession operations. This ensures proper ordering (e.g., task update before comment).

### Decision 3: Like Operations Require No User Parameter

**Decision**: `add_like(task)` uses the authenticated user automatically.

**Rationale**: The Asana API `/tasks/{gid}/addLike` uses the OAuth token's user. Requiring a user parameter would be:
1. Confusing (can only like as yourself)
2. Error-prone (passing wrong user would fail)
3. Inconsistent with API behavior

### Decision 4: Positioning Conflict Raises Error

**Decision**: Specifying both `insert_before` and `insert_after` raises `PositioningConflictError`.

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Raise error (chosen)** | Clear developer feedback; fail-fast | Requires input validation |
| **Prefer one parameter** | No error | Confusing behavior; silent ignore |
| **Chain operations** | Technically possible | Complex; unpredictable result |

Explicit conflict detection with clear error message is better than silent behavior.

### Decision 5: Symmetric Dependency/Dependent Interface

**Decision**: `add_dependent(A, B)` is the inverse of `add_dependency(B, A)`.

**Rationale**: Both methods exist because developers think about relationships in both directions:
- "Task C depends on Task A" -> `add_dependency(C, A)`
- "Task A has Task C as dependent" -> `add_dependent(A, C)`

Having both reduces cognitive load and API lookup.

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Follower endpoints accept single-user arrays | Asana API documentation; tested behavior |
| Like/unlike are idempotent | Asana API tested behavior |
| Comments via stories endpoint work for task comments | Asana API documentation |
| Positioning parameters are optional in API | Asana API documentation |
| Action endpoints remain non-batch-eligible | Asana API limitation; confirmed in PRD-0006 |

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| SaveSession (PRD-0005) | autom8 team | Complete | 327 tests passing |
| ActionExecutor (PRD-0006) | autom8 team | Complete | 7 action types implemented |
| ActionType enum | autom8 team | Complete | Needs extension for 7 new types |
| AsyncHTTPClient | autom8 team | Complete | Used by ActionExecutor |
| User model | autom8 team | Complete | `src/autom8_asana/models/user.py` |
| NameGid model | autom8 team | Complete | `src/autom8_asana/models/common.py` |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-001: Action endpoints not batch-able | Higher API call count | Confirmed | Document limitation; group related operations |
| R-002: Like idempotency changes in API | Silent failures | Low | Integration test verification |
| R-003: Comment creation rate limiting | Throttled operations | Medium | Use existing TokenBucketRateLimiter |
| R-004: Positioning conflicts not detected early | Late errors | Low | Validate at queue time, not commit time |
| R-005: Complex temp GID chains | Resolution failures | Medium | Comprehensive resolution testing |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should positioning support "first" and "last" special values? | Architect | TDD phase | Design decision |
| Should add_comment support @mentions with user resolution? | Architect | TDD phase | Scope decision |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Requirements Analyst | Initial draft with 6 FR categories, 4 NFR categories |

---

## Appendix A: New ActionType Values

```python
class ActionType(str, Enum):
    # Existing (PRD-0006)
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ADD_TO_PROJECT = "add_to_project"
    REMOVE_FROM_PROJECT = "remove_from_project"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"
    MOVE_TO_SECTION = "move_to_section"

    # New (PRD-0007)
    ADD_FOLLOWER = "add_follower"
    REMOVE_FOLLOWER = "remove_follower"
    ADD_DEPENDENT = "add_dependent"
    REMOVE_DEPENDENT = "remove_dependent"
    ADD_LIKE = "add_like"
    REMOVE_LIKE = "remove_like"
    ADD_COMMENT = "add_comment"
```

---

## Appendix B: Asana API Endpoint Reference

### Follower Operations

```
POST /tasks/{task_gid}/addFollowers
Body: { "data": { "followers": ["user_gid_1", "user_gid_2"] } }
Response: { "data": { ... task object ... } }

POST /tasks/{task_gid}/removeFollowers
Body: { "data": { "followers": ["user_gid"] } }
Response: { "data": { ... task object ... } }
```

### Dependent Operations

```
POST /tasks/{task_gid}/addDependents
Body: { "data": { "dependents": ["task_gid_1", "task_gid_2"] } }
Response: { "data": [{ "gid": "...", ... }] }

POST /tasks/{task_gid}/removeDependents
Body: { "data": { "dependents": ["task_gid"] } }
Response: { "data": {} }
```

### Like Operations

```
POST /tasks/{task_gid}/addLike
Body: { "data": {} }
Response: { "data": { ... task object with likes ... } }

POST /tasks/{task_gid}/removeLike
Body: { "data": {} }
Response: { "data": { ... task object ... } }
```

### Comment Operations

```
POST /tasks/{task_gid}/stories
Body: { "data": { "text": "Comment text", "html_text": "<body>Rich text</body>" } }
Response: { "data": { "gid": "story_gid", "type": "comment", ... } }
```

### Extended Positioning

```
POST /tasks/{task_gid}/addProject
Body: {
    "data": {
        "project": "project_gid",
        "insert_before": "task_gid",  // OR
        "insert_after": "task_gid"    // (mutually exclusive)
    }
}

POST /sections/{section_gid}/addTask
Body: {
    "data": {
        "task": "task_gid",
        "insert_before": "task_gid",  // OR
        "insert_after": "task_gid"    // (mutually exclusive)
    }
}
```

---

## Appendix C: New Method Signatures

```python
class SaveSession:
    # --- Follower Methods ---

    def add_follower(
        self,
        task: Task | str,
        user: User | NameGid | str,
    ) -> SaveSession:
        """Add a follower to a task.

        Args:
            task: Task entity or GID string.
            user: User entity, NameGid, or user GID string.

        Returns:
            Self for fluent chaining.

        Raises:
            SessionClosedError: If session is closed.

        Example:
            session.add_follower(task, reviewer)
        """
        ...

    def remove_follower(
        self,
        task: Task | str,
        user: User | NameGid | str,
    ) -> SaveSession:
        """Remove a follower from a task.

        Args:
            task: Task entity or GID string.
            user: User entity, NameGid, or user GID string.

        Returns:
            Self for fluent chaining.
        """
        ...

    def add_followers(
        self,
        task: Task | str,
        users: list[User | NameGid | str],
    ) -> SaveSession:
        """Add multiple followers to a task.

        Creates one ActionOperation per user for clear error attribution.

        Args:
            task: Task entity or GID string.
            users: List of User entities, NameGids, or GID strings.

        Returns:
            Self for fluent chaining.
        """
        ...

    def remove_followers(
        self,
        task: Task | str,
        users: list[User | NameGid | str],
    ) -> SaveSession:
        """Remove multiple followers from a task.

        Args:
            task: Task entity or GID string.
            users: List of User entities, NameGids, or GID strings.

        Returns:
            Self for fluent chaining.
        """
        ...

    # --- Dependent Methods ---

    def add_dependent(
        self,
        task: Task | str,
        dependent_task: Task | str,
    ) -> SaveSession:
        """Add a task as dependent (it depends on this task).

        This is the inverse of add_dependency. After this call,
        dependent_task will be blocked until task is completed.

        Args:
            task: Task entity or GID (the prerequisite task).
            dependent_task: Task entity or GID (the task that depends on this one).

        Returns:
            Self for fluent chaining.

        Example:
            # subtask depends on milestone (milestone must complete first)
            session.add_dependent(milestone, subtask)
        """
        ...

    def remove_dependent(
        self,
        task: Task | str,
        dependent_task: Task | str,
    ) -> SaveSession:
        """Remove a task as dependent.

        Args:
            task: Task entity or GID.
            dependent_task: Task entity or GID to remove as dependent.

        Returns:
            Self for fluent chaining.
        """
        ...

    # --- Like Methods ---

    def add_like(self, task: Task | str) -> SaveSession:
        """Like a task as the current authenticated user.

        No user parameter needed; uses OAuth token's user.

        Args:
            task: Task entity or GID string.

        Returns:
            Self for fluent chaining.

        Note:
            Liking an already-liked task is a no-op (idempotent).
        """
        ...

    def remove_like(self, task: Task | str) -> SaveSession:
        """Unlike a task.

        Args:
            task: Task entity or GID string.

        Returns:
            Self for fluent chaining.

        Note:
            Unliking a non-liked task is a no-op (idempotent).
        """
        ...

    # --- Comment Methods ---

    def add_comment(
        self,
        task: Task | str,
        text: str,
        *,
        html_text: str | None = None,
    ) -> SaveSession:
        """Add a comment to a task.

        Comments are created as stories via deferred execution.
        The comment will be created when commit() is called.

        Args:
            task: Task entity or GID string.
            text: Plain text comment content.
            html_text: Optional rich text content in Asana's HTML format.

        Returns:
            Self for fluent chaining.

        Raises:
            ValueError: If text is empty and html_text is None.
            SessionClosedError: If session is closed.

        Example:
            session.add_comment(task, "Status update: in progress")
            session.add_comment(task, "", html_text="<body><strong>Done!</strong></body>")
        """
        ...

    # --- Extended Existing Methods ---

    def add_to_project(
        self,
        task: Task | str,
        project: Project | NameGid | str,
        *,
        insert_before: Task | NameGid | str | None = None,
        insert_after: Task | NameGid | str | None = None,
    ) -> SaveSession:
        """Add a task to a project with optional positioning.

        Args:
            task: Task entity or GID string.
            project: Project entity, NameGid, or GID string.
            insert_before: Position task before this task (mutually exclusive with insert_after).
            insert_after: Position task after this task (mutually exclusive with insert_before).

        Returns:
            Self for fluent chaining.

        Raises:
            PositioningConflictError: If both insert_before and insert_after specified.
        """
        ...

    def move_to_section(
        self,
        task: Task | str,
        section: Section | NameGid | str,
        *,
        insert_before: Task | NameGid | str | None = None,
        insert_after: Task | NameGid | str | None = None,
    ) -> SaveSession:
        """Move a task to a section with optional positioning.

        Args:
            task: Task entity or GID string.
            section: Section entity, NameGid, or GID string.
            insert_before: Position task before this task (mutually exclusive with insert_after).
            insert_after: Position task after this task (mutually exclusive with insert_before).

        Returns:
            Self for fluent chaining.

        Raises:
            PositioningConflictError: If both insert_before and insert_after specified.
        """
        ...
```

---

## Appendix D: Exception Additions

```python
class PositioningConflictError(SaveOrchestrationError):
    """Raised when both insert_before and insert_after are specified.

    Attributes:
        insert_before: The insert_before value that was provided.
        insert_after: The insert_after value that was provided.
    """

    def __init__(
        self,
        insert_before: str,
        insert_after: str,
    ) -> None:
        self.insert_before = insert_before
        self.insert_after = insert_after
        super().__init__(
            "Cannot specify both insert_before and insert_after. "
            f"Got insert_before={insert_before}, insert_after={insert_after}"
        )
```

---

## Appendix E: Traceability Matrix

| Requirement | Implementation Component | Test File |
|-------------|--------------------------|-----------|
| FR-POS-001 | `SaveSession.add_to_project()` | `test_positioning.py` |
| FR-POS-002 | `SaveSession.add_to_project()` | `test_positioning.py` |
| FR-POS-003 | `PositioningConflictError` | `test_positioning.py` |
| FR-POS-004 | `SaveSession.move_to_section()` | `test_positioning.py` |
| FR-POS-005 | `SaveSession.move_to_section()` | `test_positioning.py` |
| FR-FOL-001 | `SaveSession.add_follower()` | `test_follower_actions.py` |
| FR-FOL-002 | `SaveSession.remove_follower()` | `test_follower_actions.py` |
| FR-FOL-003 | `SaveSession.add_followers()` | `test_follower_actions.py` |
| FR-FOL-004 | `SaveSession.remove_followers()` | `test_follower_actions.py` |
| FR-DEP-001 | `SaveSession.add_dependent()` | `test_dependent_actions.py` |
| FR-DEP-002 | `SaveSession.remove_dependent()` | `test_dependent_actions.py` |
| FR-LIK-001 | `SaveSession.add_like()` | `test_like_actions.py` |
| FR-LIK-002 | `SaveSession.remove_like()` | `test_like_actions.py` |
| FR-CMT-001 | `SaveSession.add_comment()` | `test_comment_actions.py` |
| FR-CMT-002 | `SaveSession.add_comment()` | `test_comment_actions.py` |
| NFR-TYPE-001 | All new methods | `mypy --strict` |
| NFR-COMPAT-001 | Existing tests | CI test suite |
