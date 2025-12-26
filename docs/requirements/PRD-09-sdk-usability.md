# PRD-09: SDK Usability

> PRD for developer experience and API usability improvements.

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: PRD-0012 (SDK Usability Improvements)
- **Related TDD**: TDD-10-operations-usability
- **Original Author**: Requirements Analyst
- **Stakeholders**: SDK users (external developers), SDK maintainers (internal team), Architect, QA

---

## Executive Summary

The autom8_asana SDK is functional but requires excessive boilerplate for simple operations. This PRD defines improvements to reduce developer ceremony from 5-6 lines to 1-2 lines for common tasks, add name-based resolution (eliminating GID requirements), provide dictionary-style custom field access, and enable auto-tracking models with implicit SaveSession management.

**Key outcomes:**

- Single-task operations reduced from 5+ lines to 1-2 lines
- Name-based resolution eliminates GID knowledge requirement
- Dictionary-style custom field access (`task.custom_fields["Priority"] = "High"`)
- Auto-tracking models with `task.save()` and `task.refresh()` methods
- Simplified client constructor with auto-workspace detection
- 100% backward compatibility with existing code

---

## Problem Statement

### Current State

Simple operations require excessive boilerplate code:

**Adding a tag to a task (5-6 lines):**

```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    session.add_tag(task.gid, tag_gid)  # Must know tag GID!
    await session.commit_async()
```

**Setting a custom field (6-7 lines):**

```python
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    cf = task.get_custom_fields()
    cf.set("Priority", "High")
    await session.commit_async()
```

### Pain Points

| Pain Point | Description | Impact |
|------------|-------------|--------|
| Developer ceremony | 5+ lines for single-task operations (vs. 1-2 lines in modern ORMs) | High friction for simple tasks |
| Learning curve | New SDK users must understand SaveSession before doing anything | Slows onboarding |
| GID requirement | Developers forced to know GIDs instead of human-readable names | Error-prone, poor DX |
| Custom field awkwardness | `.get_custom_fields().set("X", Y)` verbose vs dictionary syntax | Unintuitive API |
| Manual session management | No implicit session for simple operations | Unnecessary complexity |

### Who Is Affected

- **New SDK users** learning the library (high friction)
- **Batch operation experts** (SaveSession is still their tool, but should be optional for simple cases)
- **Integration developers** embedding Asana operations in larger workflows

### Impact of Not Solving

- Lower adoption: Developers gravitate toward Asana's official Python library (simpler API)
- Higher support burden: More questions about SaveSession, custom fields, GIDs
- Maintenance debt: Lack of convenience patterns suggests incomplete SDK

---

## Goals and Non-Goals

### Goals

1. **Reduce ceremony**: Single-task operations from 5+ lines to 1-2 lines
2. **Lower learning curve**: Names work out-of-box without GID knowledge
3. **Improve ergonomics**: Dictionary-style custom field access
4. **Maintain power**: SaveSession stays unchanged for batch workflows
5. **100% backward compatibility**: All existing code continues to work

### Non-Goals

- Custom field creation or schema modification (handled by Asana UI)
- Fuzzy matching for names (exact match only, case-insensitive)
- Bulk operation redesign (SaveSession stays as-is for batching)
- Multi-environment configuration beyond client constructor
- Rate limiting or circuit breaker enhancements
- Retry strategies beyond existing patterns

---

## Requirements

### Priority 1: Direct Methods on TasksClient

Convenience methods that wrap SaveSession internally, returning updated Task objects.

| Requirement ID | Description | Acceptance Criteria |
|----------------|-------------|---------------------|
| FR-DIRECT-001 | `add_tag_async(task_gid, tag_gid) -> Task` | Method exists on TasksClient; returns updated Task; raises APIError for invalid GIDs |
| FR-DIRECT-002 | `add_tag()` sync wrapper | Uses `@sync_wrapper` decorator; delegates to async variant |
| FR-DIRECT-003 | `remove_tag_async(task_gid, tag_gid) -> Task` | Method exists; returns updated Task; raises APIError for invalid GIDs |
| FR-DIRECT-004 | `remove_tag()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-DIRECT-005 | `move_to_section_async(task_gid, section_gid, project_gid) -> Task` | Method exists; returns updated Task |
| FR-DIRECT-006 | `move_to_section()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-DIRECT-007 | `set_assignee_async(task_gid, assignee_gid) -> Task` | Method exists; returns updated Task |
| FR-DIRECT-008 | `set_assignee()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-DIRECT-009 | `add_to_project_async(task_gid, project_gid, section_gid=None) -> Task` | Method exists; section optional |
| FR-DIRECT-010 | `add_to_project()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-DIRECT-011 | `remove_from_project_async(task_gid, project_gid) -> Task` | Method exists; returns updated Task |
| FR-DIRECT-012 | `remove_from_project()` sync wrapper | Uses `@sync_wrapper` decorator |

**Integration Point**: `src/autom8_asana/clients/tasks.py`

### Priority 2: Property-Style Custom Field Access

Dictionary-style access to custom fields via `task.custom_fields["field_name"]` syntax.

| Requirement ID | Description | Acceptance Criteria |
|----------------|-------------|---------------------|
| FR-CFIELD-001 | Get via dictionary syntax | `task.custom_fields["Priority"]` returns current value; raises KeyError if missing |
| FR-CFIELD-002 | Set via dictionary syntax | `task.custom_fields["Priority"] = "High"` sets value; marks task dirty |
| FR-CFIELD-003 | Change tracking | `CustomFieldAccessor.has_changes()` returns True when modifications exist |
| FR-CFIELD-004 | Type preservation | Enum returns dict with gid/name; number returns float/int; text returns string; date returns ISO string |
| FR-CFIELD-005 | Error handling | KeyError for missing fields; error message includes field name |

**Integration Point**: `src/autom8_asana/models/custom_field_accessor.py`

### Priority 3: Built-in Name Resolution

Resolve human-readable names to GIDs for tags, sections, projects, and assignees.

| Requirement ID | Description | Acceptance Criteria |
|----------------|-------------|---------------------|
| FR-NAMES-001 | `resolve_tag_async(name_or_gid, project_gid=None) -> str` | GID passthrough; name lookup with case-insensitive matching |
| FR-NAMES-002 | `resolve_tag()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-NAMES-003 | `resolve_section_async(name_or_gid, project_gid) -> str` | Project-scoped resolution; project_gid required |
| FR-NAMES-004 | `resolve_section()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-NAMES-005 | `resolve_project_async(name_or_gid, workspace_gid) -> str` | Workspace-scoped resolution |
| FR-NAMES-006 | `resolve_project()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-NAMES-007 | `resolve_assignee_async(name_or_gid, workspace_gid) -> str` | Search by user name or email |
| FR-NAMES-008 | `resolve_assignee()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-NAMES-009 | Update P1 methods to accept names or GIDs | Polymorphic resolution; GID passthrough if pattern matches |
| FR-NAMES-010 | `NameNotFoundError` exception | Extends AsanaError; includes suggestions via difflib.get_close_matches() |
| FR-NAMES-011 | Per-SaveSession caching | Cache cleared on session exit; workspace/project scoped |

**Integration Point**: New `src/autom8_asana/clients/name_resolver.py`

### Priority 4: Auto-tracking Models

Add `save()` and `refresh()` methods to Task model for implicit SaveSession management.

| Requirement ID | Description | Acceptance Criteria |
|----------------|-------------|---------------------|
| FR-TRACK-001 | `Task.save_async() -> Task` | Creates implicit SaveSession; tracks and commits; returns updated Task |
| FR-TRACK-002 | `Task.save()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-TRACK-003 | `Task.refresh_async() -> Task` | Fetches latest state from API; clears pending modifications |
| FR-TRACK-004 | `Task.refresh()` sync wrapper | Uses `@sync_wrapper` decorator |
| FR-TRACK-005 | Client reference storage | `_client` private attribute via PrivateAttr; assigned on Task creation |
| FR-TRACK-006 | Dirty detection | Leverages SaveSession change tracking; no-op when clean |

**Integration Point**: `src/autom8_asana/models/task.py`

### Priority 5: Simplified Client Constructor

Single-argument constructor pattern for common use case.

| Requirement ID | Description | Acceptance Criteria |
|----------------|-------------|---------------------|
| FR-CLIENT-001 | Single-argument constructor | `AsanaClient(token)` pattern works |
| FR-CLIENT-002 | Default workspace detection | Auto-detects if user has exactly one workspace; raises ConfigurationError otherwise |
| FR-CLIENT-003 | Full constructor preserved | Original full constructor unchanged for advanced cases |

**Integration Point**: `src/autom8_asana/client.py`

### Backward Compatibility Requirements

| Requirement ID | Description | Verification |
|----------------|-------------|--------------|
| FR-COMPAT-001 | SaveSession workflows unchanged | All existing SaveSession tests pass |
| FR-COMPAT-002 | Custom field accessor unchanged | All existing custom field tests pass |
| FR-COMPAT-003 | Pre-existing tests pass | `pytest` without modifications passes 100% |
| FR-COMPAT-004 | Exception handling unchanged | All existing error handling tests pass |

---

## User Stories

### Direct Methods (P1)

**As a** developer performing a single task operation,
**I want to** add a tag in one line of code,
**So that** I don't need to manage SaveSession boilerplate for simple operations.

```python
# Before: 5-6 lines
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    session.add_tag(task.gid, tag_gid)
    await session.commit_async()

# After: 1 line
await client.tasks.add_tag_async(task_gid, "Urgent")
```

### Custom Field Access (P2)

**As a** developer working with custom fields,
**I want to** use dictionary syntax to get and set values,
**So that** the API feels natural and Pythonic.

```python
# Before: 6-7 lines
async with SaveSession(client) as session:
    task = await client.tasks.get(task_gid)
    session.track(task)
    cf = task.get_custom_fields()
    cf.set("Priority", "High")
    await session.commit_async()

# After: 3 lines
task = await client.tasks.get(task_gid)
task.custom_fields["Priority"] = "High"
await task.save()
```

### Name Resolution (P3)

**As a** developer integrating with Asana,
**I want to** use human-readable names instead of GIDs,
**So that** I don't need to look up GIDs before every operation.

```python
# Before: GID required
tag_gid = "1234567890abcdef"  # Must know GID!
await client.tasks.add_tag_async(task_gid, tag_gid)

# After: Names work
await client.tasks.add_tag_async(task_gid, "Urgent")
```

### Auto-tracking (P4)

**As a** developer modifying tasks,
**I want to** call `task.save()` directly,
**So that** I don't need explicit SaveSession management for single-task operations.

```python
# Before: explicit SaveSession
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    await session.commit_async()

# After: implicit
task.name = "Updated"
await task.save()
```

### Simplified Constructor (P5)

**As a** developer setting up the SDK,
**I want to** create a client with just my token,
**So that** I don't need to specify workspace when I only have one.

```python
# Before: full constructor
client = AsanaClient(
    token="0/1234567890abcdef1234567890abcdef",
    workspace_gid="1234567890abcdef",
)

# After: simplified
client = AsanaClient("0/1234567890abcdef1234567890abcdef")
```

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Lines for tag add | 5-6 | 1 | Code comparison |
| Custom field access | `.get_custom_fields().set("X", Y)` | `["X"] = Y` | API signature |
| GID requirement | 100% (must know GIDs) | 0% (names work) | Method signatures |
| Type safety | - | mypy passes | `mypy src/autom8_asana` exit code 0 |
| Test coverage (new code) | 0% | >80% | `pytest --cov` |
| Backward compat | - | 100% | All pre-existing tests pass |

### Non-Functional Requirements

| NFR ID | Requirement | Target | Measurement |
|--------|-------------|--------|-------------|
| NFR-SAFETY-001 | Type Safety | mypy compliance on all new code | `mypy src/autom8_asana` exit code 0 |
| NFR-SAFETY-002 | Test Coverage | >80% for new code | `pytest --cov` report |
| NFR-SAFETY-003 | Documentation | 100% docstring coverage for public APIs | Manual review |
| NFR-PERF-001 | No Performance Regressions | Latency p50 < 5% regression | Benchmark comparison |
| NFR-PERF-002 | Name Resolution Caching | 100% cache hit rate for repeated names | Trace API calls |

---

## Dependencies

### Dependency Graph

```
P1 Direct Methods (independent)
  |
  v (uses)
  SaveSession (existing, unchanged)

P2 Custom Field Access (independent)
  |
  v (uses)
  CustomFieldAccessor (existing, unchanged)

P3 Name Resolution (optionally integrates with P1)
  |
  v (enhances)
  P1 Direct Methods
  |
  v (depends on)
  NameResolver (new)

P4 Auto-tracking (depends on P2)
  |
  v (uses)
  P2 Custom Fields
  |
  v (uses)
  SaveSession (existing)

P5 Client Constructor (independent)
  |
  v (no dependencies)
```

### Implementation Sequence

1. **Session 4**: Implement P1 (Direct Methods) - Independent, no blockers
2. **Session 5a**: Implement P2 (Custom Field Access) - Independent, parallel with P1
3. **Session 5b**: Implement P3 (Name Resolution) - Integrates with P1, can run after P1 complete
4. **Session 6a**: Implement P4 (Auto-tracking) - Depends on P2, can run after P2 complete
5. **Session 6b**: Implement P5 (Client Constructor) - Independent, can run anytime

**Critical Path**: P2 -> P4 (Custom Fields needed for auto-tracking)

### Internal Dependencies

| Component | Depends On | Status |
|-----------|------------|--------|
| P1 Direct Methods | SaveSession | Existing, unchanged |
| P2 Custom Field Access | CustomFieldAccessor | Existing, unchanged |
| P3 Name Resolution | NameResolver (new) | To be implemented |
| P4 Auto-tracking | P2 Custom Fields, SaveSession | P2 must complete first |
| P5 Client Constructor | None | Independent |

---

## Testing Strategy

### P1 Direct Methods

**Test File**: `tests/unit/clients/test_tasks_direct_methods.py`

- `test_add_tag_async_returns_task` - Method returns updated Task
- `test_add_tag_async_raises_on_invalid_gid` - Raises APIError for invalid task GID
- `test_add_tag_sync_uses_decorator` - Sync wrapper delegates to async
- Similar for all 12 direct methods
- Integration test: Full round-trip with mocked API

### P2 Custom Field Access

**Test File**: `tests/unit/models/test_custom_field_dict_access.py`

- `test_get_by_name_returns_value` - Dictionary access works
- `test_get_missing_raises_key_error` - Raises KeyError for missing field
- `test_set_marks_dirty` - Setting value marks task dirty
- `test_type_preservation_enum` - Enum values preserved
- `test_backward_compat_get_custom_fields` - Existing methods still work

### P3 Name Resolution

**Test File**: `tests/unit/clients/test_name_resolver.py`

- `test_resolve_tag_name_returns_gid` - Name lookup succeeds
- `test_resolve_tag_gid_passthrough` - GID passthrough works
- `test_resolve_tag_missing_raises_error` - Raises NameNotFoundError with suggestions
- `test_caching_per_session` - Cache hit within session
- `test_cache_cleared_on_session_exit` - Cache cleared when SaveSession exits

### P4 Auto-tracking

**Test File**: `tests/unit/models/test_task_save.py`

- `test_save_async_commits_changes` - Field changes persisted
- `test_save_async_dirty_detection` - No API call if no changes
- `test_save_requires_client_reference` - Raises ValueError if _client is None
- `test_refresh_async_fetches_latest` - Latest state from API

### P5 Client Constructor

**Test File**: `tests/unit/client/test_constructor.py`

- `test_single_arg_constructor` - Simplified constructor works
- `test_auto_detect_single_workspace` - Auto-detects if exactly one
- `test_error_multiple_workspaces` - Raises ConfigurationError if >1
- `test_full_constructor_still_works` - Original constructor unchanged

---

## Assumptions

1. **Task model can store client references**: Pydantic PrivateAttr allows storing non-serializable fields
2. **Name resolution should be case-insensitive**: Standard practice in UIs
3. **Per-SaveSession caching is sufficient**: Advanced use cases can add per-Client TTL cache in future
4. **Direct methods are convenience wrappers**: They use SaveSession internally, don't bypass it
5. **Single workspace detection is helpful**: 90% of users have exactly one workspace
6. **Dirty detection via SaveSession is sufficient**: No Task-level dirty flag needed
7. **GID passthrough is smart**: If string matches GID pattern, treat as GID; else resolve name

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Requirements Analyst | Initial PRD based on DISCOVERY-SDKUX-001 |
| 2.0 | 2025-12-25 | Tech Writer | Consolidated into PRD-09 |
