# PRD: Action Endpoint Support for Save Orchestration

## Metadata
- **PRD ID**: PRD-0006
- **Status**: Draft
- **Version**: 1.0
- **Author**: Requirements Analyst
- **Created**: 2025-12-10
- **Last Updated**: 2025-12-10
- **Stakeholders**: autom8 team, SDK consumers, API integrators
- **Related PRDs**:
  - [PRD-0005](PRD-0005-save-orchestration.md) (Save Orchestration Layer - prerequisite)
- **Related ADRs**:
  - [ADR-0035](../decisions/ADR-0035-unit-of-work-pattern.md) (Unit of Work Pattern)
  - [ADR-0036](../decisions/ADR-0036-change-tracking-strategy.md) (Change Tracking via Snapshot Comparison)

## Problem Statement

The Save Orchestration Layer (PRD-0005) is implemented with 327 tests passing. However, QA triage identified critical gaps where certain Asana operations require **action endpoints** rather than the standard REST CRUD pattern (`PUT /tasks/{gid}`).

**Root Cause**: SaveSession assumes all field modifications can be persisted via `PUT /tasks/{gid}`, but Asana requires dedicated action endpoints for collection fields:

| Field | Current Behavior | Actual Asana API Requirement |
|-------|------------------|------------------------------|
| `task.tags` | Direct modification detected, silently ignored | `POST /tasks/{gid}/addTag`, `POST /tasks/{gid}/removeTag` |
| `task.projects` | Direct modification detected, silently ignored | `POST /tasks/{gid}/addProject`, `POST /tasks/{gid}/removeProject` |
| `task.dependencies` | Not supported | `POST /tasks/{gid}/addDependencies`, `POST /tasks/{gid}/removeDependencies` |
| Section membership | Not supported | `POST /sections/{gid}/addTask` |
| Custom fields | Works correctly | `PUT /tasks/{gid}` with `custom_fields` payload (no change needed) |

**Silent Failure Example**:
```python
async with SaveSession(client) as session:
    task = await client.tasks.get_async("123")
    session.track(task)
    task.tags.append(NameGid(gid="tag_456", name="Priority"))  # Detected as change
    result = await session.commit()  # Silently ignored! Tag not added.
```

**Impact of Not Solving**:
1. **Silent data loss**: Users modify `task.tags` or `task.projects`, changes appear successful but are never persisted
2. **Developer confusion**: Code looks correct, tests may pass, but production data is wrong
3. **Incomplete SDK**: Common Asana operations (tagging, project membership) cannot be performed through SaveSession
4. **Trust erosion**: Silent failures undermine confidence in the SDK

**Scope of Gap**:
- Tags: High-frequency operation in task management workflows
- Projects: Essential for multi-homing tasks across projects
- Dependencies: Critical for project planning and Gantt views
- Sections: Required for kanban-style task organization

## Goals & Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Action endpoint coverage | 100% for Tags, Projects, Dependencies, Sections | Integration tests for each endpoint |
| Unsupported operation detection | 100% of direct modifications detected | Unit tests with direct modification attempts |
| Error message clarity | 100% of errors include correct API suggestion | Error message audit |
| Custom field persistence | 100% of field types have persistence tests | Test matrix coverage |
| Backward compatibility | 0 regressions in existing 327 tests | CI test suite |
| API ergonomics | Fluent method chaining supported | API review |

## Scope

### In Scope

**Action Operations (Fluent API)**:
- Tag operations: `add_tag()`, `remove_tag()`
- Project operations: `add_to_project()`, `remove_from_project()`
- Dependency operations: `add_dependency()`, `remove_dependency()`
- Section operations: `move_to_section()`

**Unsupported Operation Detection**:
- Detect direct modifications to: `task.tags`, `task.projects`, `task.memberships`, `task.dependencies`
- Raise `UnsupportedOperationError` during pre-save validation
- Provide clear error messages with correct API guidance

**Custom Field Persistence Tests**:
- Test coverage for all 6 custom field types
- CREATE and UPDATE operations for each type
- Change detection and payload generation verification

### Out of Scope

**Deferred to Future PRDs**:
- Attachment operations (`POST /tasks/{gid}/addAttachment`) - requires multipart handling
- Follower operations (`POST /tasks/{gid}/addFollowers`, `POST /tasks/{gid}/removeFollowers`)
- Like/Heart operations
- Story/Comment creation via action endpoints
- Subtask creation via action endpoint (`POST /tasks/{gid}/subtasks`) - already handled via parent field

**Not Planned**:
- Automatic conversion of direct modifications to action operations (too magical)
- Batch support for action endpoints (Asana limitation - action endpoints not batch-eligible)

---

## Requirements

### Functional Requirements

#### Action Operation Requirements (FR-ACTION-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-ACTION-001 | SDK shall provide `session.add_tag(task, tag)` to add a tag to a task | Must | Calling `add_tag()` queues action; on commit, `POST /tasks/{gid}/addTag` is called |
| FR-ACTION-002 | SDK shall provide `session.remove_tag(task, tag)` to remove a tag from a task | Must | Calling `remove_tag()` queues action; on commit, `POST /tasks/{gid}/removeTag` is called |
| FR-ACTION-003 | SDK shall provide `session.add_to_project(task, project)` to add a task to a project | Must | Calling `add_to_project()` queues action; on commit, `POST /tasks/{gid}/addProject` is called |
| FR-ACTION-004 | SDK shall provide `session.remove_from_project(task, project)` to remove a task from a project | Must | Calling `remove_from_project()` queues action; on commit, `POST /tasks/{gid}/removeProject` is called |
| FR-ACTION-005 | SDK shall provide `session.add_dependency(task, depends_on)` to add a task dependency | Must | Calling `add_dependency()` queues action; on commit, `POST /tasks/{gid}/addDependencies` is called |
| FR-ACTION-006 | SDK shall provide `session.remove_dependency(task, depends_on)` to remove a task dependency | Must | Calling `remove_dependency()` queues action; on commit, `POST /tasks/{gid}/removeDependencies` is called |
| FR-ACTION-007 | SDK shall provide `session.move_to_section(task, section)` to move a task to a section | Must | Calling `move_to_section()` queues action; on commit, `POST /sections/{gid}/addTask` is called |
| FR-ACTION-008 | Action methods shall accept entity objects or GID strings | Must | `add_tag(task, tag_obj)` and `add_tag(task, "tag_gid")` both work |
| FR-ACTION-009 | Action methods shall return self for fluent chaining | Should | `session.add_tag(t, tag1).add_tag(t, tag2)` chains correctly |
| FR-ACTION-010 | Action operations shall be queued and executed on commit | Must | No API calls made until `commit()` is called |
| FR-ACTION-011 | Action operations shall execute after standard CRUD operations | Must | CREATE/UPDATE/DELETE execute first, then action operations |
| FR-ACTION-012 | Action operations shall support newly created entities (temp GIDs) | Must | `add_tag(new_task, tag)` resolves `new_task.gid` after creation |

#### Unsupported Operation Detection Requirements (FR-UNSUP-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-UNSUP-001 | SDK shall detect direct modifications to `task.tags` | Must | Modifying `task.tags` list and calling commit raises `UnsupportedOperationError` |
| FR-UNSUP-002 | SDK shall detect direct modifications to `task.projects` | Must | Modifying `task.projects` list and calling commit raises `UnsupportedOperationError` |
| FR-UNSUP-003 | SDK shall detect direct modifications to `task.memberships` | Must | Modifying `task.memberships` list and calling commit raises `UnsupportedOperationError` |
| FR-UNSUP-004 | SDK shall detect direct modifications to `task.dependencies` | Should | Modifying `task.dependencies` (if present) and calling commit raises `UnsupportedOperationError` |
| FR-UNSUP-005 | Detection shall occur during pre-save validation (before API calls) | Must | Error raised before any API requests are made |
| FR-UNSUP-006 | `UnsupportedOperationError` shall include field name in message | Must | Error message includes which field was modified |
| FR-UNSUP-007 | `UnsupportedOperationError` shall include correct API guidance | Must | Error message suggests correct action method (e.g., "Use session.add_tag() instead") |
| FR-UNSUP-008 | Detection shall not affect unmodified fields | Must | Task with unchanged `tags` list does not trigger error |
| FR-UNSUP-009 | Detection shall work with snapshot comparison | Must | Comparison of original vs current state detects list modifications |

#### Custom Field Persistence Test Requirements (FR-CF-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-CF-001 | SDK shall have persistence tests for text custom fields | Must | CREATE and UPDATE tests pass for text field type |
| FR-CF-002 | SDK shall have persistence tests for number custom fields | Must | CREATE and UPDATE tests pass for number field type |
| FR-CF-003 | SDK shall have persistence tests for enum custom fields | Must | CREATE and UPDATE tests pass for enum field type |
| FR-CF-004 | SDK shall have persistence tests for multi-enum custom fields | Must | CREATE and UPDATE tests pass for multi-enum field type |
| FR-CF-005 | SDK shall have persistence tests for date custom fields | Must | CREATE and UPDATE tests pass for date field type |
| FR-CF-006 | SDK shall have persistence tests for people custom fields | Must | CREATE and UPDATE tests pass for people field type |
| FR-CF-007 | Tests shall verify changes detected by ChangeTracker | Must | Each test verifies `get_changes()` returns expected diff |
| FR-CF-008 | Tests shall verify correct payload generated | Must | Each test verifies serialized payload matches Asana API spec |
| FR-CF-009 | Tests shall verify API response processed correctly | Must | Each test verifies entity updated with response data |

#### Exception Requirements (FR-EXC-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-EXC-001 | SDK shall define `UnsupportedOperationError` exception | Must | Exception class exists in `persistence/exceptions.py` |
| FR-EXC-002 | `UnsupportedOperationError` shall inherit from `SaveOrchestrationError` | Must | Inheritance chain verified |
| FR-EXC-003 | `UnsupportedOperationError` shall include `field_name` attribute | Must | `error.field_name` returns the problematic field |
| FR-EXC-004 | `UnsupportedOperationError` shall include `suggested_method` attribute | Must | `error.suggested_method` returns the correct action method name |
| FR-EXC-005 | Exception shall be importable from `autom8_asana.persistence.exceptions` | Must | `from autom8_asana.persistence.exceptions import UnsupportedOperationError` works |

#### Preview Integration Requirements (FR-PREV-*)

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-PREV-001 | `session.preview()` shall include queued action operations | Must | Preview returns PlannedOperation for each action |
| FR-PREV-002 | Preview shall show action operations after CRUD operations | Must | Action operations appear after CREATE/UPDATE/DELETE in preview list |
| FR-PREV-003 | Preview shall detect unsupported direct modifications | Must | Preview raises `UnsupportedOperationError` same as commit |

---

### Non-Functional Requirements

#### Compatibility Requirements (NFR-COMPAT-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-COMPAT-001 | All 327 existing tests shall pass | 0 failures | CI test suite |
| NFR-COMPAT-002 | Existing SaveSession API unchanged | No breaking changes | API diff analysis |
| NFR-COMPAT-003 | Action methods additive to existing API | No removals/renames | API diff analysis |
| NFR-COMPAT-004 | Exception hierarchy compatible with existing handlers | `UnsupportedOperationError` caught by `SaveOrchestrationError` handler | Unit test |

#### Performance Requirements (NFR-PERF-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-PERF-001 | No performance regression in save operations | < 5% overhead | Benchmark comparison |
| NFR-PERF-002 | Action operation queueing | O(1) per operation | Algorithm analysis |
| NFR-PERF-003 | Unsupported operation detection | < 1ms per entity | Profiler measurement |

#### Documentation Requirements (NFR-DOC-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-DOC-001 | All new methods documented with docstrings | 100% coverage | Doc audit |
| NFR-DOC-002 | Docstrings include usage examples | 1+ example per method | Doc audit |
| NFR-DOC-003 | Error messages actionable | Include correct method suggestion | Error message review |

#### Error Message Requirements (NFR-ERR-*)

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR-ERR-001 | Error messages clear and actionable | 100% include solution | Message review |
| NFR-ERR-002 | Error messages include field name | 100% specify which field | Message review |
| NFR-ERR-003 | Error messages include correct API | 100% suggest correct method | Message review |

---

## User Stories / Use Cases

### US-001: Add Tags to Task

As a developer, I want to add tags to a task through SaveSession so that tagging operations are batched with other changes.

**Scenario**:
1. Developer retrieves a task
2. Developer calls `session.add_tag(task, tag)` for each tag
3. Developer calls `commit()`
4. SDK executes `POST /tasks/{gid}/addTag` for each tag
5. Task now has the new tags

**Acceptance**: Tags are added via action endpoint, not silently ignored.

### US-002: Multi-Home Task Across Projects

As a developer, I want to add a task to multiple projects so that the task appears in each project's task list.

**Scenario**:
1. Developer has a task in Project A
2. Developer calls `session.add_to_project(task, project_b)`
3. Developer calls `session.add_to_project(task, project_c)`
4. Developer calls `commit()`
5. Task now appears in Projects A, B, and C

**Acceptance**: Task membership in multiple projects works correctly.

### US-003: Create Task with Dependencies

As a developer, I want to set task dependencies so that the task shows as blocked in Asana's dependency view.

**Scenario**:
1. Developer has tasks A, B, and C
2. Developer calls `session.add_dependency(task_c, task_a)` (C depends on A)
3. Developer calls `session.add_dependency(task_c, task_b)` (C depends on B)
4. Developer calls `commit()`
5. Task C shows as blocked by A and B in Asana

**Acceptance**: Dependencies created via action endpoint.

### US-004: Move Task to Section

As a developer, I want to move a task to a different section so that the task appears in the correct kanban column.

**Scenario**:
1. Developer has a task in "To Do" section
2. Developer calls `session.move_to_section(task, done_section)`
3. Developer calls `commit()`
4. Task now appears in "Done" section

**Acceptance**: Task moved via `POST /sections/{gid}/addTask`.

### US-005: Prevented Direct Tag Modification

As a developer, I want clear errors when I try to modify tags directly so that I learn the correct API and avoid silent failures.

**Scenario**:
1. Developer retrieves a task
2. Developer modifies `task.tags.append(tag)` directly
3. Developer calls `commit()`
4. SDK raises `UnsupportedOperationError`
5. Error message says: "Direct modification of 'tags' is not supported. Use session.add_tag() or session.remove_tag() instead."

**Acceptance**: Clear error prevents silent failure and teaches correct usage.

### US-006: Chain Multiple Action Operations

As a developer, I want to chain action operations for cleaner code.

**Scenario**:
```python
async with SaveSession(client) as session:
    session.add_tag(task, urgent_tag) \
           .add_tag(task, priority_tag) \
           .add_to_project(task, backlog_project) \
           .move_to_section(task, in_progress_section)
    result = await session.commit()
```

**Acceptance**: Fluent chaining works; all operations execute on commit.

---

## Design Decisions

### Decision 1: Explicit Action Methods over Automatic Conversion

**Decision**: Provide explicit action methods (`add_tag()`, `remove_tag()`, etc.) rather than automatically converting direct modifications to action calls.

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Explicit methods (chosen)** | Clear intent; no magic; predictable; matches Asana API mental model | More verbose for simple cases |
| **Automatic conversion** | Less code; feels like regular field assignment | Hidden complexity; hard to debug; unpredictable order |
| **Hybrid (detect and convert)** | Best of both worlds | Complexity; inconsistent behavior; testing nightmare |

Explicit methods align with Python's philosophy and make the SDK's behavior predictable. Developers can trace exactly what API calls will be made.

### Decision 2: Strict Enforcement via UnsupportedOperationError

**Decision**: Raise `UnsupportedOperationError` when detecting direct modifications to action-endpoint fields, rather than silently ignoring or warning.

**Rationale**:

| Approach | Pros | Cons |
|----------|------|------|
| **Strict error (chosen)** | Prevents silent data loss; teaches correct usage; fail-fast | Breaking for code with silent bugs |
| **Warning only** | Non-breaking; gradual migration | Silent failures continue; logs ignored |
| **Silent ignore** | Non-breaking | Silent data loss; terrible UX |

Silent failures are worse than loud failures. Users deserve to know when their code won't work as expected. The error message provides the solution.

### Decision 3: Action Operations Execute After CRUD Operations

**Decision**: Action operations execute after standard CREATE/UPDATE/DELETE operations within a commit.

**Rationale**:
- Entity must exist before action can be performed (e.g., can't add tag to non-existent task)
- Temp GID resolution happens during CRUD phase
- Clear, predictable execution order

### Decision 4: Action Operations Not Batch-Eligible

**Decision**: Action operations execute as individual API calls, not through batch API.

**Rationale**: Asana's Batch API only supports standard CRUD operations (`GET`, `POST`, `PUT`, `DELETE` on resource endpoints). Action endpoints (`/tasks/{gid}/addTag`, etc.) are not batch-eligible per Asana API documentation.

---

## Assumptions

| Assumption | Basis |
|------------|-------|
| Action endpoints are not batch-eligible | Asana API documentation; tested behavior |
| Tags, projects, dependencies use action endpoints | Asana API documentation |
| Section membership uses `POST /sections/{gid}/addTask` | Asana API documentation |
| Custom fields persist via standard PUT | Existing implementation works correctly |
| Direct modification detection via snapshot comparison is sufficient | ADR-0036 approach |

---

## Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| SaveSession (PRD-0005) | autom8 team | Complete | 327 tests passing |
| ChangeTracker | autom8 team | Complete | `src/autom8_asana/persistence/tracker.py` |
| Task model with typed fields | autom8 team | Complete | `src/autom8_asana/models/task.py` |
| Asana API action endpoints | Asana | Available | Documented in Asana API reference |

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| R-001: Action operations not batch-able increases API calls | Performance | High | Document limitation; recommend grouping related changes |
| R-002: Detection of direct modifications has false positives | Developer frustration | Low | Precise comparison; comprehensive tests |
| R-003: Breaking change for code relying on silent ignore | Migration burden | Medium | Clear error messages; migration guide |
| R-004: Complex interaction between CRUD and action ops | Bugs | Medium | Clear execution order; extensive integration tests |

---

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| Should action operations support rollback on failure? | Architect | TDD phase | Per existing partial-commit semantics |
| Should we validate tag/project GIDs before commit? | Architect | TDD phase | Design decision |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-10 | Requirements Analyst | Initial draft with action operations, unsupported detection, and custom field test requirements |

---

## Appendix A: Asana API Action Endpoint Reference

### Tag Operations

```
POST /tasks/{task_gid}/addTag
Body: { "data": { "tag": "tag_gid" } }
Response: { "data": {} }

POST /tasks/{task_gid}/removeTag
Body: { "data": { "tag": "tag_gid" } }
Response: { "data": {} }
```

### Project Operations

```
POST /tasks/{task_gid}/addProject
Body: { "data": { "project": "project_gid" } }
Response: { "data": {} }

POST /tasks/{task_gid}/removeProject
Body: { "data": { "project": "project_gid" } }
Response: { "data": {} }
```

### Dependency Operations

```
POST /tasks/{task_gid}/addDependencies
Body: { "data": { "dependencies": ["task_gid_1", "task_gid_2"] } }
Response: { "data": [{ "gid": "...", ... }] }

POST /tasks/{task_gid}/removeDependencies
Body: { "data": { "dependencies": ["task_gid_1"] } }
Response: { "data": {} }
```

### Section Operations

```
POST /sections/{section_gid}/addTask
Body: { "data": { "task": "task_gid" } }
Response: { "data": {} }
```

---

## Appendix B: UnsupportedOperationError API

```python
class UnsupportedOperationError(SaveOrchestrationError):
    """Raised when attempting unsupported direct modification.

    Certain Asana fields (tags, projects, dependencies, memberships) cannot
    be modified via PUT requests and require action endpoints instead.

    Attributes:
        field_name: The field that was modified directly
        suggested_method: The correct session method to use
    """

    FIELD_SUGGESTIONS = {
        "tags": ("add_tag", "remove_tag"),
        "projects": ("add_to_project", "remove_from_project"),
        "memberships": ("add_to_project", "remove_from_project", "move_to_section"),
        "dependencies": ("add_dependency", "remove_dependency"),
    }

    def __init__(self, field_name: str) -> None:
        self.field_name = field_name
        suggestions = self.FIELD_SUGGESTIONS.get(field_name, ())
        self.suggested_methods = suggestions

        if suggestions:
            methods = " or ".join(f"session.{m}()" for m in suggestions)
            message = (
                f"Direct modification of '{field_name}' is not supported. "
                f"Use {methods} instead."
            )
        else:
            message = f"Direct modification of '{field_name}' is not supported."

        super().__init__(message)
```

---

## Appendix C: Action Method API Draft

```python
class SaveSession:
    # ... existing methods ...

    def add_tag(self, task: Task | str, tag: Tag | NameGid | str) -> SaveSession:
        """Add a tag to a task.

        Queues an action operation to add the tag. Executed on commit().

        Args:
            task: Task entity or GID string
            tag: Tag entity, NameGid, or GID string

        Returns:
            Self for fluent chaining

        Example:
            session.add_tag(task, urgent_tag).add_tag(task, priority_tag)
        """
        ...

    def remove_tag(self, task: Task | str, tag: Tag | NameGid | str) -> SaveSession:
        """Remove a tag from a task.

        Args:
            task: Task entity or GID string
            tag: Tag entity, NameGid, or GID string

        Returns:
            Self for fluent chaining
        """
        ...

    def add_to_project(
        self,
        task: Task | str,
        project: Project | NameGid | str,
        *,
        section: Section | NameGid | str | None = None,
    ) -> SaveSession:
        """Add a task to a project.

        Args:
            task: Task entity or GID string
            project: Project entity, NameGid, or GID string
            section: Optional section within the project

        Returns:
            Self for fluent chaining
        """
        ...

    def remove_from_project(
        self,
        task: Task | str,
        project: Project | NameGid | str,
    ) -> SaveSession:
        """Remove a task from a project.

        Args:
            task: Task entity or GID string
            project: Project entity, NameGid, or GID string

        Returns:
            Self for fluent chaining
        """
        ...

    def add_dependency(
        self,
        task: Task | str,
        depends_on: Task | str,
    ) -> SaveSession:
        """Add a dependency (task depends on another task).

        Args:
            task: Task entity or GID string (the dependent task)
            depends_on: Task entity or GID string (the prerequisite task)

        Returns:
            Self for fluent chaining

        Example:
            # Task C depends on Tasks A and B
            session.add_dependency(task_c, task_a).add_dependency(task_c, task_b)
        """
        ...

    def remove_dependency(
        self,
        task: Task | str,
        depends_on: Task | str,
    ) -> SaveSession:
        """Remove a dependency.

        Args:
            task: Task entity or GID string (the dependent task)
            depends_on: Task entity or GID string (the prerequisite task)

        Returns:
            Self for fluent chaining
        """
        ...

    def move_to_section(
        self,
        task: Task | str,
        section: Section | NameGid | str,
    ) -> SaveSession:
        """Move a task to a section.

        Args:
            task: Task entity or GID string
            section: Section entity, NameGid, or GID string

        Returns:
            Self for fluent chaining
        """
        ...
```

---

## Appendix D: Custom Field Persistence Test Matrix

| Field Type | CREATE Test | UPDATE Test | Payload Format |
|------------|-------------|-------------|----------------|
| Text | `test_create_task_with_text_custom_field` | `test_update_text_custom_field` | `{"gid": "cf_gid", "text_value": "value"}` |
| Number | `test_create_task_with_number_custom_field` | `test_update_number_custom_field` | `{"gid": "cf_gid", "number_value": 42}` |
| Enum | `test_create_task_with_enum_custom_field` | `test_update_enum_custom_field` | `{"gid": "cf_gid", "enum_value": {"gid": "opt_gid"}}` |
| Multi-Enum | `test_create_task_with_multi_enum_custom_field` | `test_update_multi_enum_custom_field` | `{"gid": "cf_gid", "multi_enum_values": [{"gid": "opt_gid"}]}` |
| Date | `test_create_task_with_date_custom_field` | `test_update_date_custom_field` | `{"gid": "cf_gid", "date_value": "2025-12-10"}` |
| People | `test_create_task_with_people_custom_field` | `test_update_people_custom_field` | `{"gid": "cf_gid", "people_value": [{"gid": "user_gid"}]}` |

Each test shall verify:
1. **Change Detection**: `session.get_changes(task)` includes custom field modification
2. **Payload Generation**: Serialized payload matches format above
3. **API Response Processing**: Entity updated with response data after commit

---

## Appendix E: Traceability Matrix

| Requirement | Implementation Component | Test File |
|-------------|--------------------------|-----------|
| FR-ACTION-001 | `SaveSession.add_tag()` | `test_action_operations.py` |
| FR-ACTION-002 | `SaveSession.remove_tag()` | `test_action_operations.py` |
| FR-ACTION-003 | `SaveSession.add_to_project()` | `test_action_operations.py` |
| FR-ACTION-004 | `SaveSession.remove_from_project()` | `test_action_operations.py` |
| FR-ACTION-005 | `SaveSession.add_dependency()` | `test_action_operations.py` |
| FR-ACTION-006 | `SaveSession.remove_dependency()` | `test_action_operations.py` |
| FR-ACTION-007 | `SaveSession.move_to_section()` | `test_action_operations.py` |
| FR-UNSUP-001 | `ChangeTracker._validate_changes()` | `test_unsupported_operations.py` |
| FR-UNSUP-002 | `ChangeTracker._validate_changes()` | `test_unsupported_operations.py` |
| FR-UNSUP-003 | `ChangeTracker._validate_changes()` | `test_unsupported_operations.py` |
| FR-EXC-001 | `UnsupportedOperationError` | `test_exceptions.py` |
| FR-CF-001 | `custom_fields` persistence | `test_custom_field_persistence.py` |
| FR-CF-002 | `custom_fields` persistence | `test_custom_field_persistence.py` |
| FR-CF-003 | `custom_fields` persistence | `test_custom_field_persistence.py` |
| FR-CF-004 | `custom_fields` persistence | `test_custom_field_persistence.py` |
| FR-CF-005 | `custom_fields` persistence | `test_custom_field_persistence.py` |
| FR-CF-006 | `custom_fields` persistence | `test_custom_field_persistence.py` |
