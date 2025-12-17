# PRD-SDKUX: SDK Usability Overhaul Requirements

## Metadata

- **PRD ID**: PRD-SDKUX
- **Status**: Approved (Session 2)
- **Author**: Requirements Analyst
- **Created**: 2025-12-12
- **Last Updated**: 2025-12-12
- **Stakeholders**: SDK users (external developers), SDK maintainers (internal team), Architect, QA
- **Related PRDs**: None
- **Related Discovery**: DISCOVERY-SDKUX-001

---

## Problem Statement

### Current State

The autom8_asana SDK is **functional but tedious**. Simple operations require excessive boilerplate:

**Adding a tag to a task (5-6 lines)**:
```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    session.add_tag(task.gid, tag_gid)  # Must know tag GID!
    await session.commit_async()
```

**Setting a custom field (6-7 lines)**:
```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    cf = task.get_custom_fields()
    cf.set("Priority", "High")
    await session.commit_async()
```

### Pain Points

1. **Developer ceremony**: 5+ lines for single-task operations (vs. 1-2 lines in modern ORMs)
2. **Learning curve**: New SDK users must understand SaveSession before doing anything
3. **GID requirement**: Developers forced to know GIDs instead of human-readable names
4. **Custom field awkwardness**: `.get_custom_fields().set("X", Y)` is verbose vs. dictionary syntax
5. **Manual session management**: No implicit session for simple operations

### Who Is Affected

- **New SDK users** learning the library (high friction)
- **Batch operation experts** (SaveSession is still their tool, but should be optional for simple cases)
- **Integration developers** embedding Asana operations in larger workflows

### Impact of Not Solving

- **Lower adoption**: Developers gravitate toward Asana's official Python library (simpler API)
- **Higher support burden**: More questions about SaveSession, custom fields, GIDs
- **Maintenance debt**: Lack of convenience patterns suggests incomplete SDK

---

## Target State

### Simple Operations (1-2 lines)

**Adding a tag to a task (1 line)**:
```python
await client.tasks.add_tag_async(task_gid, "Urgent")  # Name or GID
```

**Setting a custom field (2 lines)**:
```python
task = await client.tasks.get(task_gid)
task.custom_fields["Priority"] = "High"
await task.save()  # Auto-tracks and commits
```

### Characteristics

- **Natural APIs**: Methods read like sentences
- **Names work**: Accept human-readable names instead of GIDs
- **Implicit sessions**: Single operations don't require SaveSession
- **Dictionary-like fields**: Custom fields feel like Python dicts
- **Type-safe**: All operations maintain type information

### SaveSession Still Powerful

Explicit SaveSession is still the tool for batch operations:
```python
async with SaveSession(client) as session:
    for task_gid in task_gids:
        session.add_tag(task_gid, "BulkTag")
    await session.commit_async()
```

---

## Goals & Success Metrics

### Goals

1. **Reduce ceremony**: Single-task operations from 5+ lines to 1-2 lines
2. **Lower learning curve**: Names work out-of-box without GID knowledge
3. **Improve ergonomics**: Dictionary-style custom field access
4. **Maintain power**: SaveSession stays unchanged for batch workflows
5. **100% backward compatibility**: All existing code continues to work

### Success Metrics (Quantified)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Lines for tag add | 5-6 | 1 | Code comparison |
| Custom field access | `.get_custom_fields().set("X", Y)` | `["X"] = Y` | API signature |
| GID requirement | 100% (must know GIDs) | 0% (names work) | Method signatures |
| Type safety | - | mypy passes | `mypy src/autom8_asana` exit code 0 |
| Test coverage (new code) | 0% | >80% | `pytest --cov` |
| Backward compat | - | 100% | All pre-existing tests pass |

---

## Scope

### In Scope

**Priority 1: Direct Methods (High Impact / Low Effort)**
- Add convenience methods on TasksClient (`add_tag_async`, `remove_tag_async`, etc.)
- All methods return updated Task objects
- Sync wrappers via `@sync_wrapper` decorator
- Integration point: `src/autom8_asana/clients/tasks.py`

**Priority 2: Property-Style Custom Fields (High Impact / Medium Effort)**
- Dictionary-style access on `task.custom_fields` (get/set)
- Automatic change tracking (marks task dirty)
- Type preservation for enum, number, text, date fields
- Integration points: `src/autom8_asana/models/task.py` + `custom_field_accessor.py`

**Priority 3: Built-in Name Resolution (High Impact / High Effort)**
- Resolve names to GIDs for tags, sections, projects, assignees
- Async and sync methods for each resource type
- Helpful error messages with suggestions via `NameNotFoundError`
- Per-SaveSession caching (zero staleness)
- Update P1 methods to accept names or GIDs polymorphically
- Integration point: New `src/autom8_asana/clients/name_resolver.py`

**Priority 4: Auto-tracking Models (Medium Impact / Medium Effort)**
- `Task.save()` and `Task.save_async()` methods
- `Task.refresh()` and `Task.refresh_async()` methods
- Implicit SaveSession creation and management
- Dirty detection (no-op when clean)
- Integration point: `src/autom8_asana/models/task.py`

**Priority 5: Simplified Client Constructor (Low Impact / Low Effort)**
- Single-argument pattern: `AsanaClient(token)`
- Default workspace detection (if user has exactly one)
- Full constructor still available for advanced cases
- Integration point: `src/autom8_asana/client.py`

**Backward Compatibility Requirements**
- All existing SaveSession workflows unchanged
- All existing custom field accessor methods unchanged
- All pre-existing tests pass without modification
- All exception handling unchanged
- No breaking import path changes

### Out of Scope

- Custom field creation or schema modification (handled by Asana UI)
- Fuzzy matching for names (exact match only, case-insensitive)
- Bulk operation redesign (SaveSession stays as-is for batching)
- Multi-environment configuration beyond client constructor
- Rate limiting or circuit breaker enhancements
- Retry strategies beyond existing patterns

---

## Requirements

### Priority 1: Direct Methods on TasksClient

**Overview**: Add convenience methods to TasksClient that wrap SaveSession internally, returning updated Task objects.

#### FR-DIRECT-001: add_tag_async()

**Description**: Add tag to task without explicit SaveSession (async)

**Signature**:
```python
async def add_tag_async(self, task_gid: str, tag_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Accepts `task_gid` and `tag_gid` as string parameters
- [ ] Returns updated Task object (not SaveResult)
- [ ] Raises `APIError` if task or tag doesn't exist
- [ ] Internally creates SaveSession and calls `session.add_tag()`
- [ ] Located in `src/autom8_asana/clients/tasks.py`

**Integration Point**: `src/autom8_asana/clients/tasks.py` - Add after existing methods (around line 400)

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-002: add_tag() - Sync Wrapper

**Description**: Add tag to task without explicit SaveSession (sync)

**Signature**:
```python
def add_tag(self, task_gid: str, tag_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Uses `@sync_wrapper("add_tag_async")` decorator
- [ ] Delegates to `add_tag_async()` internally
- [ ] Returns updated Task object (not SaveResult)
- [ ] Same error handling as async variant

**Integration Point**: `src/autom8_asana/clients/tasks.py` (immediately after `add_tag_async()`)

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-003: remove_tag_async()

**Description**: Remove tag from task without explicit SaveSession (async)

**Signature**:
```python
async def remove_tag_async(self, task_gid: str, tag_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Accepts `task_gid` and `tag_gid` as string parameters
- [ ] Returns updated Task object
- [ ] Raises `APIError` if task or tag doesn't exist
- [ ] Internally creates SaveSession and calls `session.remove_tag()`

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-004: remove_tag() - Sync Wrapper

**Description**: Remove tag from task without explicit SaveSession (sync)

**Signature**:
```python
def remove_tag(self, task_gid: str, tag_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Uses `@sync_wrapper("remove_tag_async")` decorator
- [ ] Delegates to `remove_tag_async()` internally
- [ ] Returns updated Task object

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-005: move_to_section_async()

**Description**: Move task to section without explicit SaveSession (async)

**Signature**:
```python
async def move_to_section_async(self, task_gid: str, section_gid: str, project_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Accepts `task_gid`, `section_gid`, `project_gid` as string parameters
- [ ] Returns updated Task object
- [ ] Raises `APIError` if task, section, or project doesn't exist
- [ ] Internally creates SaveSession and calls `session.move_to_section()`

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-006: move_to_section() - Sync Wrapper

**Description**: Move task to section without explicit SaveSession (sync)

**Signature**:
```python
def move_to_section(self, task_gid: str, section_gid: str, project_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Uses `@sync_wrapper("move_to_section_async")` decorator
- [ ] Delegates to `move_to_section_async()` internally
- [ ] Returns updated Task object

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-007: set_assignee_async()

**Description**: Set task assignee without explicit SaveSession (async)

**Signature**:
```python
async def set_assignee_async(self, task_gid: str, assignee_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Accepts `task_gid` and `assignee_gid` as string parameters
- [ ] Returns updated Task object
- [ ] Raises `APIError` if task or assignee doesn't exist
- [ ] Internally creates SaveSession and calls `session.set_assignee()`

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-008: set_assignee() - Sync Wrapper

**Description**: Set task assignee without explicit SaveSession (sync)

**Signature**:
```python
def set_assignee(self, task_gid: str, assignee_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Uses `@sync_wrapper("set_assignee_async")` decorator
- [ ] Delegates to `set_assignee_async()` internally
- [ ] Returns updated Task object

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-009: add_to_project_async()

**Description**: Add task to project without explicit SaveSession (async)

**Signature**:
```python
async def add_to_project_async(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Accepts `task_gid`, `project_gid`, optional `section_gid` as string parameters
- [ ] Returns updated Task object
- [ ] Raises `APIError` if task or project doesn't exist
- [ ] Section is optional; if provided, adds to that section; if not, adds to default
- [ ] Internally creates SaveSession and calls `session.add_to_project()`

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-010: add_to_project() - Sync Wrapper

**Description**: Add task to project without explicit SaveSession (sync)

**Signature**:
```python
def add_to_project(self, task_gid: str, project_gid: str, section_gid: str | None = None) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Uses `@sync_wrapper("add_to_project_async")` decorator
- [ ] Delegates to `add_to_project_async()` internally
- [ ] Returns updated Task object

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-011: remove_from_project_async()

**Description**: Remove task from project without explicit SaveSession (async)

**Signature**:
```python
async def remove_from_project_async(self, task_gid: str, project_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Accepts `task_gid` and `project_gid` as string parameters
- [ ] Returns updated Task object
- [ ] Raises `APIError` if task or project doesn't exist
- [ ] Internally creates SaveSession and calls `session.remove_from_project()`

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-DIRECT-012: remove_from_project() - Sync Wrapper

**Description**: Remove task from project without explicit SaveSession (sync)

**Signature**:
```python
def remove_from_project(self, task_gid: str, project_gid: str) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on TasksClient
- [ ] Uses `@sync_wrapper("remove_from_project_async")` decorator
- [ ] Delegates to `remove_from_project_async()` internally
- [ ] Returns updated Task object

**Integration Point**: `src/autom8_asana/clients/tasks.py`

**Backward Compatibility**: N/A (new method)

---

### Priority 2: Property-Style Custom Field Access

**Overview**: Enable dictionary-style access to custom fields via `task.custom_fields["field_name"]` syntax.

#### FR-CFIELD-001: Custom Field Get via Dictionary Syntax

**Description**: Access custom field value using `["field_name"]` syntax

**Acceptance Criteria**:
- [ ] `task.custom_fields["Priority"]` returns current value
- [ ] Works for any custom field name
- [ ] Raises `KeyError` if field doesn't exist (consistent with dict behavior)
- [ ] Type is preserved (enum returns enum dict, number returns number, text returns string, date returns string)
- [ ] Integrates with existing `CustomFieldAccessor` via new `__getitem__()` method
- [ ] Works alongside existing `task.get_custom_fields().get("Priority")` (backward compat)

**Integration Point**: `src/autom8_asana/models/custom_field_accessor.py` - Add `__getitem__()` method

**Backward Compatibility**: Existing `task.get_custom_fields()` unchanged; new method is addition

---

#### FR-CFIELD-002: Custom Field Set via Dictionary Syntax

**Description**: Set custom field value using `["field_name"] = value` syntax

**Acceptance Criteria**:
- [ ] `task.custom_fields["Priority"] = "High"` sets the value
- [ ] Works for any custom field name
- [ ] Internally calls existing `CustomFieldAccessor.set()` method
- [ ] Marks task as dirty (for `task.save()` in P4)
- [ ] Type is preserved on round-trip (value stored and later retrieved with same type)
- [ ] Integrates via new `__setitem__()` method

**Integration Point**: `src/autom8_asana/models/custom_field_accessor.py` - Add `__setitem__()` method

**Backward Compatibility**: Existing `.set()` method unchanged

---

#### FR-CFIELD-003: Custom Field Change Tracking

**Description**: Track when custom fields are modified (marks task dirty for saving)

**Acceptance Criteria**:
- [ ] When `task.custom_fields["X"] = Y` is called, `CustomFieldAccessor._modifications` is updated
- [ ] `CustomFieldAccessor.has_changes()` returns `True` when modifications exist
- [ ] When `Task.save()` is called (P4), includes only modified fields in API payload
- [ ] If task has no custom field changes, `save()` still commits other field changes

**Integration Point**: Already implemented in `CustomFieldAccessor._modifications` and `has_changes()` methods; P2 just requires using it

**Backward Compatibility**: Existing change tracking unchanged

---

#### FR-CFIELD-004: Type Preservation for Custom Fields

**Description**: Maintain type information for custom field values (enum, number, text, date)

**Acceptance Criteria**:
- [ ] Enum fields: `task.custom_fields["Status"]` returns enum dict with `{gid, name}` structure
- [ ] Number fields: `task.custom_fields["Budget"]` returns number as float/int
- [ ] Text fields: `task.custom_fields["Notes"]` returns string
- [ ] Date fields: `task.custom_fields["Due"]` returns ISO date string
- [ ] Multi-enum fields: `task.custom_fields["Tags"]` returns list of enum dicts
- [ ] People fields: `task.custom_fields["Reviewers"]` returns list of user dicts

**Integration Point**: `CustomFieldAccessor._extract_value()` already implements this; P2 uses it via `__getitem__`

**Backward Compatibility**: Type extraction unchanged

---

#### FR-CFIELD-005: Custom Field Error Handling

**Description**: Raise appropriate errors when accessing missing or invalid fields

**Acceptance Criteria**:
- [ ] `task.custom_fields["NonexistentField"]` raises `KeyError` (consistent with dict)
- [ ] Error message includes field name: `"KeyError: 'NonexistentField'"`
- [ ] Setting an unknown field creates new entry (dict behavior): `task.custom_fields["NewField"] = X` is allowed
- [ ] Getting with default (if `get()` method exists): `task.custom_fields.get("Field", "default")` returns default if missing

**Integration Point**: `custom_field_accessor.py` - Enhance `__getitem__()` to raise `KeyError`

**Backward Compatibility**: Existing error handling in `.get()` method unchanged

---

### Priority 3: Built-in Name Resolution

**Overview**: Resolve human-readable names to GIDs for tags, sections, projects, and assignees. Update P1 methods to accept names or GIDs polymorphically.

#### FR-NAMES-001: resolve_tag_async()

**Description**: Resolve tag name to GID (async)

**Signature**:
```python
async def resolve_tag_async(self, name_or_gid: str, project_gid: str | None = None) -> str
```

**Acceptance Criteria**:
- [ ] If `name_or_gid` is already a GID (36 alphanumeric chars), return it unchanged
- [ ] If `name_or_gid` is a name, list workspace tags and find exact match (case-insensitive)
- [ ] Return tag GID if found
- [ ] Raise `NameNotFoundError` if name not found, with suggestions
- [ ] Located in `src/autom8_asana/clients/name_resolver.py`
- [ ] Supports caching (per-SaveSession)

**Integration Point**: New `src/autom8_asana/clients/name_resolver.py` - NameResolver class

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-002: resolve_tag() - Sync Wrapper

**Description**: Resolve tag name to GID (sync)

**Signature**:
```python
def resolve_tag(self, name_or_gid: str, project_gid: str | None = None) -> str
```

**Acceptance Criteria**:
- [ ] Uses `@sync_wrapper("resolve_tag_async")` decorator
- [ ] Delegates to `resolve_tag_async()` internally
- [ ] Returns GID string

**Integration Point**: `src/autom8_asana/clients/name_resolver.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-003: resolve_section_async()

**Description**: Resolve section name to GID (async)

**Signature**:
```python
async def resolve_section_async(self, name_or_gid: str, project_gid: str) -> str
```

**Acceptance Criteria**:
- [ ] If `name_or_gid` is already a GID, return it unchanged
- [ ] If `name_or_gid` is a name, list project sections and find exact match (case-insensitive)
- [ ] Return section GID if found
- [ ] Raise `NameNotFoundError` if name not found, with suggestions
- [ ] `project_gid` is required (sections are project-scoped)
- [ ] Supports caching (per-SaveSession, project-scoped)

**Integration Point**: `src/autom8_asana/clients/name_resolver.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-004: resolve_section() - Sync Wrapper

**Description**: Resolve section name to GID (sync)

**Signature**:
```python
def resolve_section(self, name_or_gid: str, project_gid: str) -> str
```

**Acceptance Criteria**:
- [ ] Uses `@sync_wrapper("resolve_section_async")` decorator
- [ ] Delegates to `resolve_section_async()` internally
- [ ] Returns GID string

**Integration Point**: `src/autom8_asana/clients/name_resolver.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-005: resolve_project_async()

**Description**: Resolve project name to GID (async)

**Signature**:
```python
async def resolve_project_async(self, name_or_gid: str, workspace_gid: str) -> str
```

**Acceptance Criteria**:
- [ ] If `name_or_gid` is already a GID, return it unchanged
- [ ] If `name_or_gid` is a name, list workspace projects and find exact match (case-insensitive)
- [ ] Return project GID if found
- [ ] Raise `NameNotFoundError` if name not found, with suggestions
- [ ] Supports caching (per-SaveSession, workspace-scoped)

**Integration Point**: `src/autom8_asana/clients/name_resolver.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-006: resolve_project() - Sync Wrapper

**Description**: Resolve project name to GID (sync)

**Signature**:
```python
def resolve_project(self, name_or_gid: str, workspace_gid: str) -> str
```

**Acceptance Criteria**:
- [ ] Uses `@sync_wrapper("resolve_project_async")` decorator
- [ ] Delegates to `resolve_project_async()` internally
- [ ] Returns GID string

**Integration Point**: `src/autom8_asana/clients/name_resolver.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-007: resolve_assignee_async()

**Description**: Resolve assignee name to GID (async)

**Signature**:
```python
async def resolve_assignee_async(self, name_or_gid: str, workspace_gid: str) -> str
```

**Acceptance Criteria**:
- [ ] If `name_or_gid` is already a GID, return it unchanged
- [ ] If `name_or_gid` is a name, search by user name or email (case-insensitive)
- [ ] Return user GID if found
- [ ] Raise `NameNotFoundError` if name not found, with suggestions (including similar emails/names)
- [ ] Supports caching (per-SaveSession, workspace-scoped)

**Integration Point**: `src/autom8_asana/clients/name_resolver.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-008: resolve_assignee() - Sync Wrapper

**Description**: Resolve assignee name to GID (sync)

**Signature**:
```python
def resolve_assignee(self, name_or_gid: str, workspace_gid: str) -> str
```

**Acceptance Criteria**:
- [ ] Uses `@sync_wrapper("resolve_assignee_async")` decorator
- [ ] Delegates to `resolve_assignee_async()` internally
- [ ] Returns GID string

**Integration Point**: `src/autom8_asana/clients/name_resolver.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-NAMES-009: Update P1 Methods to Accept Names or GIDs

**Description**: Modify P1 direct methods to accept names or GIDs polymorphically

**Acceptance Criteria**:
- [ ] `add_tag_async(task_gid, tag_name_or_gid)` - If string looks like GID, use it; else resolve name
- [ ] `move_to_section_async(task_gid, section_name_or_gid, project_gid)` - Same resolution logic
- [ ] `set_assignee_async(task_gid, assignee_name_or_gid)` - Same resolution logic
- [ ] `add_to_project_async(task_gid, project_name_or_gid, section_name_or_gid=None)` - Same resolution logic
- [ ] Error messages from name resolution bubble up as `NameNotFoundError`
- [ ] Type hints updated to reflect `str | Literal["GID"]` or just `str` (polymorphic)

**Integration Point**: `src/autom8_asana/clients/tasks.py` - Modify P1 method implementations

**Backward Compatibility**: GID-only usage still works (GID passthrough); new names feature is addition

---

#### FR-NAMES-010: NameNotFoundError Exception

**Description**: New exception for name resolution failures with helpful suggestions

**Signature**:
```python
class NameNotFoundError(AsanaError):
    def __init__(
        self,
        name: str,
        resource_type: str,  # "tag", "project", "user", "section"
        scope: str,          # workspace GID or project GID
        suggestions: list[str] | None = None,
        available_names: list[str] | None = None,
    ) -> None: ...
```

**Acceptance Criteria**:
- [ ] Exception class added to `src/autom8_asana/exceptions.py`
- [ ] Extends `AsanaError` base class
- [ ] Error message format: `"Could not find {resource_type} named '{name}' in scope {scope}. Did you mean: {suggestions}? Available: {available_names}"`
- [ ] Suggestions generated via `difflib.get_close_matches()` (fuzzy matching, 3 max, 60% cutoff)
- [ ] Caught as `AsanaError` for backward compatibility
- [ ] Attributes stored: `name`, `resource_type`, `scope`, `suggestions`, `available_names`

**Integration Point**: `src/autom8_asana/exceptions.py` - Add after existing exception hierarchy

**Backward Compatibility**: New exception, doesn't affect existing error handling

---

#### FR-NAMES-011: Name Resolution Caching (Per-SaveSession)

**Description**: Cache name resolution within SaveSession context (zero staleness)

**Acceptance Criteria**:
- [ ] NameResolver instance stored on SaveSession or AsanaClient
- [ ] Per-SaveSession cache: When session exits, cache is cleared
- [ ] Workspace-scoped names (tags, projects, users) cached per workspace GID
- [ ] Project-scoped names (sections) cached per project GID
- [ ] Cache hit: Return cached GID without API call
- [ ] Cache miss: Fetch list, resolve name, store result, return
- [ ] Cache is case-insensitive on lookup but stores exact names

**Integration Point**: `src/autom8_asana/clients/name_resolver.py` + `src/autom8_asana/persistence/session.py`

**Backward Compatibility**: Caching is internal optimization; no API changes

---

### Priority 4: Auto-tracking Models

**Overview**: Add `save()` and `refresh()` methods to Task model for implicit SaveSession management.

#### FR-TRACK-001: Task.save_async()

**Description**: Save task changes using implicit SaveSession (async)

**Signature**:
```python
async def save_async(self) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on Task model
- [ ] Creates implicit SaveSession internally (no user-visible session)
- [ ] Tracks task via `session.track(self)` (captures current state)
- [ ] Commits changes via `session.commit_async()`
- [ ] Returns updated Task object (same instance with refreshed state)
- [ ] Raises `PartialSaveError` if commit fails (with error details)
- [ ] Requires `Task._client` reference to be set (raises `ValueError` if None)
- [ ] Works with field changes and custom field modifications

**Integration Point**: `src/autom8_asana/models/task.py` - Add method to Task class

**Backward Compatibility**: N/A (new method)

---

#### FR-TRACK-002: Task.save()

**Description**: Save task changes using implicit SaveSession (sync)

**Signature**:
```python
def save(self) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on Task model
- [ ] Uses `@sync_wrapper("save_async")` decorator
- [ ] Delegates to `save_async()` internally
- [ ] Returns updated Task object
- [ ] Same error handling as async variant

**Integration Point**: `src/autom8_asana/models/task.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-TRACK-003: Task.refresh_async()

**Description**: Re-fetch task from API, discarding local changes (async)

**Signature**:
```python
async def refresh_async(self) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on Task model
- [ ] Fetches latest task state from API via `self._client.tasks.get_async(self.gid)`
- [ ] Updates all local fields with API response data
- [ ] Returns self (same instance, updated fields)
- [ ] Clears any pending custom field modifications
- [ ] Requires `Task._client` reference (raises `ValueError` if None)
- [ ] Useful before saving to avoid conflicts with concurrent updates

**Integration Point**: `src/autom8_asana/models/task.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-TRACK-004: Task.refresh()

**Description**: Re-fetch task from API, discarding local changes (sync)

**Signature**:
```python
def refresh(self) -> Task
```

**Acceptance Criteria**:
- [ ] Method exists on Task model
- [ ] Uses `@sync_wrapper("refresh_async")` decorator
- [ ] Delegates to `refresh_async()` internally
- [ ] Returns updated Task object

**Integration Point**: `src/autom8_asana/models/task.py`

**Backward Compatibility**: N/A (new method)

---

#### FR-TRACK-005: Task Client Reference Storage

**Description**: Store client reference on Task instance via PrivateAttr

**Acceptance Criteria**:
- [ ] Task model has `_client` private attribute: `_client: Any = PrivateAttr(default=None)`
- [ ] Uses Pydantic PrivateAttr (not serialized, not validated)
- [ ] Reference assigned when Task is created via TasksClient (in `get_async()`, `create_async()`, etc.)
- [ ] Does not create circular import (use `TYPE_CHECKING` for type hints)
- [ ] Does not affect model serialization (`model_dump()`, `model_dump_json()`)
- [ ] Follows same pattern as existing `_custom_fields_accessor`

**Integration Point**: `src/autom8_asana/models/task.py` - Add attribute definition

**Backward Compatibility**: PrivateAttr is not serialized, so no API impact

---

#### FR-TRACK-006: Dirty Detection (SaveSession ChangeTracker)

**Description**: Leverage existing SaveSession change tracking (no-op when clean)

**Acceptance Criteria**:
- [ ] When `task.save()` is called, SaveSession.track(task) captures snapshot
- [ ] SaveSession automatically detects which fields changed since snapshot
- [ ] Only modified fields are included in API payload
- [ ] If no fields changed, commit succeeds but makes no API call (no-op)
- [ ] Custom field modifications tracked by CustomFieldAccessor._modifications
- [ ] No new dirty tracking logic needed in Task; SaveSession handles it

**Integration Point**: SaveSession already implements this; P4 just leverages it

**Backward Compatibility**: No changes to SaveSession; just new use pattern

---

### Priority 5: Simplified Client Constructor

**Overview**: Provide single-argument constructor pattern for common use case.

#### FR-CLIENT-001: Single-Argument Constructor

**Description**: Create AsanaClient with just token (simplified pattern)

**Signature**:
```python
client = AsanaClient(token="0/1234567890abcdef1234567890abcdef")
```

**Acceptance Criteria**:
- [ ] `AsanaClient.__init__(token: str)` pattern works
- [ ] Auto-detects workspace if user has exactly one
- [ ] Raises error if user has multiple workspaces (ambiguous)
- [ ] Raises error if user has no workspaces (configuration issue)
- [ ] All other parameters (batch_size, max_concurrent, etc.) use defaults

**Integration Point**: `src/autom8_asana/client.py` - Modify `__init__()` signature

**Backward Compatibility**: Existing full constructor still works; just adds new pattern

---

#### FR-CLIENT-002: Default Workspace Detection

**Description**: Auto-detect user's workspace when exactly one exists

**Acceptance Criteria**:
- [ ] Call `client.users.get_user_async()` to get current user info
- [ ] Call `client.workspaces.list_async()` to list user's workspaces
- [ ] If exactly 1 workspace: Use it as default (`client.default_workspace_gid = workspace_gid`)
- [ ] If 0 workspaces: Raise `ConfigurationError("User has no workspaces")`
- [ ] If >1 workspace: Raise `ConfigurationError("User has multiple workspaces; specify one explicitly")`
- [ ] Default workspace is used by methods that need a workspace GID (e.g., name resolution)

**Integration Point**: `src/autom8_asana/client.py` - Add to `__init__()`

**Backward Compatibility**: Optional feature; full constructor still requires explicit workspace

---

#### FR-CLIENT-003: Full Constructor Still Available

**Description**: Preserve existing full constructor for advanced cases

**Acceptance Criteria**:
- [ ] Original full constructor signature unchanged: `AsanaClient(token, workspace_gid=None, batch_size=10, max_concurrent=15, ...)`
- [ ] Can pass `workspace_gid` explicitly to skip auto-detection
- [ ] Can pass `batch_size`, `max_concurrent`, and other params
- [ ] Backward compatibility: Existing code using full constructor works unchanged

**Integration Point**: `src/autom8_asana/client.py`

**Backward Compatibility**: No breaking changes; just adds optional pattern

---

### Backward Compatibility Requirements

#### FR-COMPAT-001: SaveSession Workflows Unchanged

**Acceptance Criteria**:
- [ ] Existing `async with SaveSession(client) as session:` context manager works unchanged
- [ ] `session.track()`, `session.add_tag()`, `session.commit_async()` work unchanged
- [ ] SaveSession parameters (batch_size, max_concurrent) work unchanged
- [ ] All existing tests using SaveSession pass without modification
- [ ] Exception handling unchanged (PartialSaveError, CyclicDependencyError, etc.)

**Measurement**: Run existing SaveSession tests; all should pass

---

#### FR-COMPAT-002: Custom Field Accessor Unchanged

**Acceptance Criteria**:
- [ ] Existing `task.get_custom_fields()` method works unchanged
- [ ] Existing `.get()`, `.set()`, `.to_list()`, `.to_api_dict()` methods work unchanged
- [ ] All existing custom field tests pass without modification
- [ ] New `__getitem__()` and `__setitem__()` are additions, not replacements

**Measurement**: Run existing custom field tests; all should pass

---

#### FR-COMPAT-003: Pre-existing Tests Pass

**Acceptance Criteria**:
- [ ] All tests in `tests/` directory pass without modification
- [ ] No breaking changes to method signatures
- [ ] No breaking changes to exception types
- [ ] No breaking changes to import paths
- [ ] Test coverage maintained (no regressions in what's tested)

**Measurement**: `pytest` without modifications; should pass 100%

---

#### FR-COMPAT-004: Exception Handling Unchanged

**Acceptance Criteria**:
- [ ] Existing exception types (APIError, NotFoundError, etc.) work unchanged
- [ ] New NameNotFoundError is addition to hierarchy (caught as AsanaError)
- [ ] All existing error handling code works unchanged
- [ ] No changes to exception messages (except new NameNotFoundError)

**Measurement**: Run error handling tests; all should pass

---

## Non-Functional Requirements

### NFR-SAFETY-001: Type Safety

**Requirement**: All new code passes mypy with no `Any` outside TYPE_CHECKING sections

**Target**: mypy compliance on all new code

**Acceptance Criteria**:
- [ ] `mypy src/autom8_asana` exit code is 0 (all checks pass)
- [ ] No `type: ignore` comments except where unavoidable
- [ ] All function parameters and returns are typed
- [ ] All local variables inferred or explicitly typed
- [ ] TYPE_CHECKING block used for circular import avoidance

**Measurement**: Run `mypy src/autom8_asana` after implementation

---

### NFR-SAFETY-002: Test Coverage

**Requirement**: All new code has >80% test coverage (measured by pytest-cov)

**Target**: >80% coverage for new code

**Acceptance Criteria**:
- [ ] All new methods have tests (happy path + error cases)
- [ ] All branches tested (if statements, try/except, etc.)
- [ ] Edge cases covered (empty lists, missing fields, etc.)
- [ ] Integration tests verify end-to-end workflows

**Measurement**: Run `pytest --cov src/autom8_asana` and review coverage report

---

### NFR-SAFETY-003: Documentation

**Requirement**: All new methods have docstrings with examples

**Target**: 100% docstring coverage for public APIs

**Acceptance Criteria**:
- [ ] All public methods have docstrings (following Google style)
- [ ] Docstrings include: description, args, returns, raises, examples
- [ ] README updated with new patterns (P1-P5 examples)
- [ ] Integration guide updated with simplified patterns
- [ ] Type hints visible in IDE autocomplete

**Measurement**: Manual review + `pydoc` validation

---

### NFR-PERF-001: No Performance Regressions

**Requirement**: Existing operations (get, update, batch) maintain current performance

**Target**: Latency p50 < 5% regression from baseline

**Acceptance Criteria**:
- [ ] Task.get() latency unchanged (still single API call)
- [ ] Task.update() latency unchanged (still single API call)
- [ ] SaveSession.commit_async() latency unchanged (still batch operation)
- [ ] No additional memory overhead for Task instances
- [ ] Name resolution caching prevents repeated API calls

**Measurement**: Benchmark existing operations before/after implementation

---

### NFR-PERF-002: Name Resolution Caching

**Requirement**: Per-SaveSession cache means zero API calls for repeated names in same session

**Target**: 100% cache hit rate for repeated names within session

**Acceptance Criteria**:
- [ ] First name resolution: API call to list_for_workspace_async() or similar
- [ ] Second name resolution (same workspace/project): Cache hit, no API call
- [ ] Cache cleared when SaveSession exits
- [ ] Cache memory <1MB for typical workspace (100-1000 names)

**Measurement**: Trace API calls in test; verify cache hits

---

## Testing Strategy

### P1 Direct Methods Testing

**Test Files**: `tests/unit/clients/test_tasks_direct_methods.py`

**Test Cases**:
- [ ] `test_add_tag_async_returns_task` - Method returns updated Task
- [ ] `test_add_tag_async_raises_on_invalid_gid` - Raises APIError for invalid task GID
- [ ] `test_add_tag_sync_uses_decorator` - Sync wrapper delegates to async
- [ ] Similar for all 12 direct methods
- [ ] Integration test: `test_add_tag_async_integration` - Full round-trip with mocked API

---

### P2 Custom Field Access Testing

**Test Files**: `tests/unit/models/test_custom_field_dict_access.py`

**Test Cases**:
- [ ] `test_get_by_name_returns_value` - `custom_fields["Priority"]` works
- [ ] `test_get_missing_raises_key_error` - Raises KeyError for missing field
- [ ] `test_set_marks_dirty` - Setting value marks task dirty
- [ ] `test_type_preservation_enum` - Enum values preserved with gid/name
- [ ] `test_type_preservation_number` - Number values preserved
- [ ] `test_type_preservation_date` - Date strings preserved
- [ ] `test_backward_compat_get_custom_fields` - Existing `.get_custom_fields()` still works

---

### P3 Name Resolution Testing

**Test Files**: `tests/unit/clients/test_name_resolver.py`

**Test Cases**:
- [ ] `test_resolve_tag_name_returns_gid` - Name lookup succeeds
- [ ] `test_resolve_tag_gid_passthrough` - GID passthrough works
- [ ] `test_resolve_tag_missing_raises_error` - Raises NameNotFoundError with suggestions
- [ ] `test_resolve_tag_suggestions_fuzzy_match` - Error includes similar names
- [ ] `test_caching_per_session` - Same workspace cache hit within session
- [ ] `test_cache_cleared_on_session_exit` - Cache cleared when SaveSession exits
- [ ] Similar for resolve_project, resolve_section, resolve_assignee

---

### P4 Auto-tracking Testing

**Test Files**: `tests/unit/models/test_task_save.py`

**Test Cases**:
- [ ] `test_save_async_commits_changes` - Field changes persisted
- [ ] `test_save_async_dirty_detection` - No API call if no changes
- [ ] `test_save_requires_client_reference` - Raises ValueError if _client is None
- [ ] `test_refresh_async_fetches_latest` - Latest state from API
- [ ] `test_refresh_clears_modifications` - Pending changes discarded
- [ ] `test_save_with_custom_fields` - Custom field changes included
- [ ] Integration test: `test_save_refresh_cycle` - Full save/refresh round-trip

---

### P5 Client Constructor Testing

**Test Files**: `tests/unit/client/test_constructor.py`

**Test Cases**:
- [ ] `test_single_arg_constructor` - `AsanaClient(token)` works
- [ ] `test_auto_detect_single_workspace` - Auto-detects if exactly one
- [ ] `test_error_multiple_workspaces` - Raises ConfigurationError if >1 workspace
- [ ] `test_error_no_workspaces` - Raises ConfigurationError if 0 workspaces
- [ ] `test_full_constructor_still_works` - Original full constructor unchanged

---

### Backward Compatibility Testing

**Test Files**: Existing test suite (unchanged)

**Test Cases**:
- [ ] All existing SaveSession tests pass
- [ ] All existing custom field tests pass
- [ ] All existing TasksClient tests pass
- [ ] All existing exception tests pass
- [ ] No import path changes

---

## Assumptions

1. **Task model can store client references**: Pydantic PrivateAttr allows storing non-serializable fields (verified in Discovery)

2. **Name resolution should be case-insensitive**: Standard practice in UIs; implemented via `.lower()` comparison

3. **Per-SaveSession caching is sufficient**: Advanced use cases can add per-Client TTL cache in future (not blocking P3)

4. **Direct methods are convenience wrappers**: They use SaveSession internally, don't bypass it; existing SaveSession semantics preserved

5. **Single workspace detection is helpful**: 90% of users have exactly one workspace; multi-workspace users can use full constructor

6. **Dirty detection via SaveSession is sufficient**: No Task-level dirty flag needed; SaveSession's snapshot-based detection works

7. **GID passthrough is smart**: If string matches GID pattern, treat as GID; else resolve name (avoids separate methods)

---

## Dependencies & Sequencing

### Dependency Graph

```
P1 Direct Methods (independent)
  ↓ (uses)
  SaveSession (existing, unchanged)

P2 Custom Field Access (independent)
  ↓ (uses)
  CustomFieldAccessor (existing, unchanged)

P3 Name Resolution (optionally integrates with P1)
  ↓ (enhances)
  P1 Direct Methods
  ↓ (depends on)
  NameResolver (new)

P4 Auto-tracking (depends on P2)
  ↓ (uses)
  P2 Custom Fields
  ↓ (uses)
  SaveSession (existing)

P5 Client Constructor (independent)
  ↓ (no dependencies)
```

### Implementation Sequence (Recommended)

1. **Session 4**: Implement P1 (Direct Methods) - Independent, no blockers
2. **Session 5a**: Implement P2 (Custom Field Access) - Independent, parallel with P1
3. **Session 5b**: Implement P3 (Name Resolution) - Integrates with P1, can run after P1 complete
4. **Session 6a**: Implement P4 (Auto-tracking) - Depends on P2, can run after P2 complete
5. **Session 6b**: Implement P5 (Client Constructor) - Independent, can run anytime

**Critical Path**: P2 → P4 (Custom Fields needed for auto-tracking)

---

## Open Questions

None - All 6 critical architectural questions answered in DISCOVERY-SDKUX-001.

---

## Success Metrics Summary

| Metric | Current | Target | Session 7 Validation |
|--------|---------|--------|----------------------|
| Tag add code | 5-6 lines | 1 line | Code sample comparison |
| Custom field access | `.get_custom_fields().set("X", Y)` | `["X"] = Y` | API comparison |
| GID requirement | 100% (must know GIDs) | 0% (names work) | Method signature review |
| Type safety | - | mypy passes | `mypy src/autom8_asana` exit code 0 |
| Test coverage (new) | 0% | >80% | `pytest --cov` report |
| Backward compat | - | 100% | All pre-existing tests pass |

---

## Approval Criteria for Architect Handoff (Session 3)

This PRD is ready for Session 3 Architecture when:

- [x] All P1-P5 requirements documented (12 + 5 + 11 + 6 + 3 = 37 FRs + 4 FR-COMPAT + 5 NFRs)
- [x] Every requirement has specific, testable acceptance criteria
- [x] Integration points specified (which files, which lines)
- [x] Backward compatibility explicitly referenced in relevant requirements
- [x] Success metrics are quantified with measurable targets
- [x] Testing strategy outlined per priority
- [x] Dependency graph and implementation sequence provided
- [x] No blocking open questions (all 6 from Discovery answered)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Requirements Analyst | Initial PRD based on DISCOVERY-SDKUX-001 |

---

## Appendix: Code Examples

### P1: Direct Methods

**Current Pattern (5-6 lines)**:
```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    session.add_tag(task.gid, tag_gid)
    await session.commit_async()
```

**Target Pattern (1 line)**:
```python
await client.tasks.add_tag_async(task_gid, "Urgent")
```

---

### P2: Custom Field Access

**Current Pattern (6-7 lines)**:
```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    cf = task.get_custom_fields()
    cf.set("Priority", "High")
    await session.commit_async()
```

**Target Pattern (3 lines)**:
```python
task = await client.tasks.get(task_gid)
task.custom_fields["Priority"] = "High"
await task.save()
```

---

### P3: Name Resolution

**Current Pattern (GID required)**:
```python
tag_gid = "1234567890abcdef"  # Must know GID!
await client.tasks.add_tag_async(task_gid, tag_gid)
```

**Target Pattern (Names work)**:
```python
await client.tasks.add_tag_async(task_gid, "Urgent")  # Name resolution
```

---

### P4: Auto-tracking

**Current Pattern (explicit SaveSession)**:
```python
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()
```

**Target Pattern (implicit)**:
```python
task.name = "Updated"
await task.save()
```

---

### P5: Client Constructor

**Current Pattern (full constructor)**:
```python
client = AsanaClient(
    token="0/1234567890abcdef1234567890abcdef",
    workspace_gid="1234567890abcdef",
)
```

**Target Pattern (simplified)**:
```python
client = AsanaClient("0/1234567890abcdef1234567890abcdef")
```

---
