# Discovery: SDK Demonstration Suite

> Session 1 Discovery Document - SDK Capability & Test Data Analysis

**Date**: 2025-12-12
**Author**: Requirements Analyst
**Status**: Complete
**Initiative**: SDK Demonstration Suite (sdk-demo-prompt-0)

---

## Executive Summary

This discovery document analyzes the autom8_asana SDK's capabilities relevant to the SDK Demonstration Suite initiative. The analysis confirms that the SDK provides comprehensive support for all 10 planned demonstration categories, with **built-in name resolution for custom fields** but **no built-in resolution for tags or users by name**.

**Key Findings**:
- All action operations (tag, dependency, project, section, parent) are fully implemented
- CustomFieldAccessor provides automatic name-to-GID resolution for custom fields
- Multi-enum fields use **replace-all semantics** (not merge)
- Tag and user name-to-GID resolution requires manual lookup via client APIs
- Test data GIDs are referenced only in planning documents - live verification required

**Recommendation**: Proceed to PRD creation with clear acceptance criteria for name resolution patterns. Test data verification against live Asana workspace is a blocking prerequisite before implementation.

---

## SDK Capability Matrix

### 1. Action Operations (SaveSession Methods)

| Operation | Method | Status | Notes |
|-----------|--------|--------|-------|
| Add tag | `session.add_tag(task, tag_gid_or_object)` | IMPLEMENTED | Accepts GID string or Tag object |
| Remove tag | `session.remove_tag(task, tag_gid_or_object)` | IMPLEMENTED | Accepts GID string or Tag object |
| Add dependency | `session.add_dependency(task, depends_on)` | IMPLEMENTED | Task becomes dependent on target |
| Remove dependency | `session.remove_dependency(task, depends_on)` | IMPLEMENTED | Removes dependency relationship |
| Add dependent | `session.add_dependent(task, dependent_task)` | IMPLEMENTED | Inverse of add_dependency |
| Remove dependent | `session.remove_dependent(task, dependent_task)` | IMPLEMENTED | Inverse of remove_dependency |
| Add to project | `session.add_to_project(task, project)` | IMPLEMENTED | Supports insert_before/insert_after |
| Remove from project | `session.remove_from_project(task, project)` | IMPLEMENTED | |
| Move to section | `session.move_to_section(task, section)` | IMPLEMENTED | Supports insert_before/insert_after |
| Set parent | `session.set_parent(task, parent)` | IMPLEMENTED | Parent=None promotes to top-level |
| Reorder subtask | `session.reorder_subtask(task, insert_before/after)` | IMPLEMENTED | Convenience for set_parent with same parent |
| Add follower | `session.add_follower(task, user)` | IMPLEMENTED | |
| Remove follower | `session.remove_follower(task, user)` | IMPLEMENTED | |
| Add like | `session.add_like(task)` | IMPLEMENTED | Uses authenticated user |
| Remove like | `session.remove_like(task)` | IMPLEMENTED | Uses authenticated user |
| Add comment | `session.add_comment(task, text, html_text=None)` | IMPLEMENTED | Supports HTML formatting |

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (lines 669-1671)

### 2. Custom Field Operations (CustomFieldAccessor)

| Operation | Method | Status | Notes |
|-----------|--------|--------|-------|
| Get value | `accessor.get(name_or_gid, default=None)` | IMPLEMENTED | Case-insensitive name lookup |
| Set value | `accessor.set(name_or_gid, value)` | IMPLEMENTED | Tracks modifications |
| Remove value | `accessor.remove(name_or_gid)` | IMPLEMENTED | Sets to None |
| Check changes | `accessor.has_changes()` | IMPLEMENTED | For dirty detection |
| Clear changes | `accessor.clear_changes()` | IMPLEMENTED | Reset pending modifications |
| Convert to API format | `accessor.to_list()` | IMPLEMENTED | Returns `[{gid, value}, ...]` |

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`

### 3. Direct Field Modifications (Task Model)

| Field | Type | Change Tracking | Notes |
|-------|------|-----------------|-------|
| `name` | str | Via SaveSession tracker | Standard field |
| `notes` | str | Via SaveSession tracker | Task description |
| `html_notes` | str | Via SaveSession tracker | Rich text description |
| `completed` | bool | Via SaveSession tracker | |
| `due_on` | str | Via SaveSession tracker | YYYY-MM-DD format |
| `due_at` | str | Via SaveSession tracker | ISO 8601 datetime |
| `assignee` | NameGid | Via SaveSession tracker | User reference |
| `custom_fields` | list[dict] | Via CustomFieldAccessor | Accessor tracks internally |

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py`

### 4. Preview and Confirmation Pattern

```python
# Idiomatic preview pattern from session.py
crud_ops, action_ops = session.preview()

# CRUD operations are PlannedOperation objects
for op in crud_ops:
    print(f"{op.operation.value} {type(op.entity).__name__}(gid={op.entity.gid})")
    print(f"  Payload: {op.payload}")
    print(f"  Dependency level: {op.dependency_level}")

# Action operations are ActionOperation objects
for action in action_ops:
    print(f"{action.action.value} on task {action.task.gid}")
    print(f"  Target: {action.target_gid}")
```

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (lines 426-465)

---

## Open Questions Analysis

### SDK Capability Questions

#### Q1: Does SDK have built-in tag name-to-GID resolution?

**Status**: RESOLVED - NO

**Finding**: The SDK does **not** provide automatic tag name-to-GID resolution. `session.add_tag()` accepts either a Tag object or a GID string directly:

```python
# From session.py line 691
tag_gid = tag if isinstance(tag, str) else tag.gid
```

**Recommendation**: Demo script must use `TagsClient.list_for_workspace_async()` to find tag by name:

```python
async for tag in client.tags.list_for_workspace_async(workspace_gid):
    if tag.name == "optimize":
        target_tag_gid = tag.gid
        break
```

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py`

---

#### Q2: How to resolve user display names to GIDs?

**Status**: RESOLVED - Manual lookup required

**Finding**: The SDK provides `UsersClient.list_for_workspace_async()` for user enumeration but no name-based lookup method:

```python
# From users.py - available methods
async def get_async(user_gid, ...)  # Get by GID
async def me_async(...)  # Get current user
def list_for_workspace_async(workspace_gid, ...)  # List all users
```

**Recommendation**: Demo script must iterate workspace users to resolve names:

```python
async for user in client.users.list_for_workspace_async(workspace_gid):
    if user.name == "Tom Tenuta":
        target_user_gid = user.gid
        break
```

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py`

---

#### Q3: Is enum option name-to-GID built into CustomFieldAccessor?

**Status**: RESOLVED - PARTIAL

**Finding**: CustomFieldAccessor resolves **custom field names** to GIDs (case-insensitive), but enum **option values** must be provided as GIDs or the accessor passes them through as-is:

```python
# From custom_field_accessor.py line 55-63
def set(self, name_or_gid: str, value: Any) -> None:
    """Set custom field value by name or GID."""
    gid = self._resolve_gid(name_or_gid)  # Resolves FIELD name, not option
    self._modifications[gid] = value  # Value passed through directly
```

The value for enum fields should be the option GID. The accessor does **not** resolve enum option names to GIDs.

**Recommendation**: For enum fields, the demo script must either:
1. Use enum option GIDs directly, or
2. Fetch the custom field definition and build an option name-to-GID map

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py`

---

#### Q4: Multi-enum set semantics: replace all or merge?

**Status**: RESOLVED - REPLACE ALL

**Finding**: Setting a multi-enum custom field **replaces all values**, it does not merge with existing values. The CustomFieldAccessor stores the value directly in modifications:

```python
# From custom_field_accessor.py line 113-115
if gid in self._modifications:
    # Modified field - uses new value as-is
    result.append({"gid": gid, "value": self._modifications[gid]})
```

For multi-enum, you pass a list of option GIDs. The entire list replaces the current values.

**Example semantics**:
```python
# Current: ["option_a", "option_b"]
accessor.set("Disabled Questions", ["option_c"])  # Result: ["option_c"]
accessor.set("Disabled Questions", ["option_a", "option_c"])  # Result: ["option_a", "option_c"]
accessor.set("Disabled Questions", None)  # Result: [] (cleared)
```

**Implication**: To "add" an option, demo must read current values, append, and set. To "remove", read current, filter, and set.

---

### Test Data Questions

#### Q5: Does tag "optimize" exist?

**Status**: UNRESOLVED - Requires live verification

**Finding**: The tag "optimize" is referenced only in planning documents (`sdk-demo-prompt-0.md`), not in test fixtures or code. No evidence of its existence in the Asana workspace.

**Risk**: Tag may not exist. Demo may need to create it.

**Recommendation**:
1. At script startup, check if tag exists in workspace
2. If not found, prompt user: "Tag 'optimize' not found. Create it? (y/n)"
3. Track created resources for cleanup

---

#### Q6: Can current field values be determined from test fixtures?

**Status**: UNRESOLVED - No fixture data found

**Finding**: Test data GIDs are referenced only in planning documents. No fixture files contain actual field values for the target entities:
- Business `1203504488813198`
- Unit `1203504489143268`

**Risk**: Cannot know current state without live API calls.

**Recommendation**: Demo script must capture initial state at startup for restoration:

```python
# Capture state pattern
initial_state = {
    "business": {
        "notes": business.notes,
        "custom_fields": business.custom_fields.copy(),
        "tags": [tag.gid for tag in business.tags],
    }
}
```

---

#### Q7: Subtask siblings under Reconciliation Holder - how to find?

**Status**: RESOLVED - Via TasksClient

**Finding**: SDK provides subtask listing through parent GID:

```python
# List subtasks of a parent
subtasks = await client.tasks.list_async(parent=parent_gid)
async for subtask in subtasks:
    print(f"{subtask.name}: {subtask.gid}")
```

The Reconciliation Holder `1203504488912317` is the parent. Its subtasks can be enumerated to find siblings for positioning.

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` (list_async method)

---

#### Q8: Exact section names in Businesses project?

**Status**: UNRESOLVED - Requires live verification

**Finding**: Section names referenced in planning docs include "BUSINESSES", "OTHER", "OPPORTUNITY" but these are not verified against actual workspace.

**Recommendation**: At startup, fetch sections for the target project:

```python
sections = await client.sections.list_for_project_async(project_gid).collect()
for section in sections:
    print(f"{section.name}: {section.gid}")
```

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py`

---

### Script Design Questions

#### Q9: Idiomatic confirmation pattern?

**Status**: RESOLVED

**Finding**: The SDK provides `session.preview()` for dry-run inspection before commit:

```python
# Idiomatic confirmation pattern
crud_ops, action_ops = session.preview()

# Display planned operations
print("Planned CRUD operations:")
for op in crud_ops:
    print(f"  {op.operation.value}: {type(op.entity).__name__}")

print("Planned action operations:")
for action in action_ops:
    print(f"  {action.action.value}: task={action.task.gid}, target={action.target_gid}")

# Confirm with user
if input("Execute? (y/n): ").lower() == 'y':
    result = await session.commit_async()
```

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` (preview method, lines 426-465)

---

#### Q10: State capture: once at start or per-operation?

**Status**: RESOLVED - Once at start, update after successful operations

**Recommendation**: Capture full entity state at script start, then update snapshot after each successful operation to enable accurate rollback:

```python
class DemoStateManager:
    def __init__(self):
        self.initial_state = {}  # Captured at start
        self.current_state = {}  # Updated after each operation

    async def capture_initial(self, entity):
        """Capture state at demo start."""
        self.initial_state[entity.gid] = await self._snapshot(entity)
        self.current_state[entity.gid] = self.initial_state[entity.gid].copy()

    async def update_current(self, entity):
        """Update current state after successful operation."""
        self.current_state[entity.gid] = await self._snapshot(entity)

    async def restore_all(self):
        """Restore all entities to initial state."""
        for gid, initial in self.initial_state.items():
            if initial != self.current_state[gid]:
                # Restore this entity
                ...
```

---

#### Q11: Partial failure handling patterns?

**Status**: RESOLVED

**Finding**: SaveSession uses "commit-and-report" semantics. `SaveResult` contains both succeeded and failed operations:

```python
# From models.py SaveResult class
@dataclass
class SaveResult:
    succeeded: list[AsanaResource]  # Successfully saved entities
    failed: list[SaveError]  # Failed operations with details

    @property
    def success(self) -> bool:
        """True if all operations succeeded."""
        return len(self.failed) == 0

    @property
    def partial(self) -> bool:
        """True if some but not all operations succeeded."""
        return len(self.succeeded) > 0 and len(self.failed) > 0
```

**Recommended pattern**:
```python
result = await session.commit_async()

if result.success:
    print(f"All {len(result.succeeded)} operations succeeded")
elif result.partial:
    print(f"Partial success: {len(result.succeeded)} succeeded, {len(result.failed)} failed")
    for error in result.failed:
        print(f"  Failed: {error.entity.gid} - {error.error}")
else:
    print("All operations failed")
    for error in result.failed:
        print(f"  {error.entity.gid}: {error.error}")
```

**Source**: `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py` (lines 112-166)

---

## Test Data Verification

### Entity GID References in Codebase

| Entity | GID | Found In | Status |
|--------|-----|----------|--------|
| Business | `1203504488813198` | `sdk-demo-prompt-0.md` only | PLANNING ONLY |
| Unit | `1203504489143268` | `sdk-demo-prompt-0.md` only | PLANNING ONLY |
| Dependency Task | `1211596978294356` | `sdk-demo-prompt-0.md` only | PLANNING ONLY |
| Subtask | `1203996810236966` | `sdk-demo-prompt-0.md` only | PLANNING ONLY |
| Reconciliation Holder | `1203504488912317` | `sdk-demo-prompt-0.md` only | PLANNING ONLY |

**Critical Finding**: None of these GIDs appear in test fixtures, unit tests, or integration tests. They are referenced only in the initiative planning document.

### Verification Requirements

Before implementation can proceed, the following must be verified against the live Asana workspace:

| Check | Entity/Resource | Required Info |
|-------|-----------------|---------------|
| Entity exists | Business `1203504488813198` | Confirm task exists and is accessible |
| Entity exists | Unit `1203504489143268` | Confirm task exists with Disabled Questions field |
| Entity exists | Dependency Task `1211596978294356` | Confirm task exists in same workspace |
| Entity exists | Subtask `1203996810236966` | Confirm is subtask of Reconciliation Holder |
| Entity exists | Reconciliation Holder `1203504488912317` | Confirm task exists with subtasks |
| Tag exists | "optimize" | Confirm tag exists or define creation strategy |
| Custom field exists | "Disabled Questions" on Unit | Confirm field exists with enum options |
| Section names | Businesses project | Get exact section names and GIDs |
| Workspace GID | Primary workspace | Required for tag/user lookups |
| Project GID | Businesses project | Required for section/membership demos |

---

## Gaps and Risks

### SDK Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| No tag name-to-GID resolution | Low | Build lookup helper using TagsClient |
| No user name-to-GID resolution | Low | Build lookup helper using UsersClient |
| No enum option name-to-GID resolution | Medium | Fetch custom field definition, build option map |
| Multi-enum uses replace semantics | Low | Document clearly, build add/remove helpers |

### Data Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test entities deleted/modified | Medium | High | Verify at startup, fail gracefully |
| Tag "optimize" doesn't exist | High | Low | Create if missing (with user confirmation) |
| Custom field definitions changed | Low | Medium | Fetch current definitions at runtime |
| Section names changed | Low | Medium | Fetch current sections at runtime |

### Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rate limiting during demo | Medium | Medium | Add delays between operations, use batch where possible |
| Concurrent modifications | Low | High | Capture state, warn if external changes detected |
| Incomplete state restoration | Medium | High | Track all modifications, test restore thoroughly |

---

## Recommendations

### Blocking Prerequisites (Must Complete Before Session 2)

1. **Live Workspace Verification**: Execute verification script to confirm all test entities exist and are accessible

2. **Tag Strategy Decision**: Confirm whether tag "optimize" exists, or specify creation/cleanup behavior

3. **Custom Field Definition Capture**: Fetch and document exact enum options for:
   - Enum fields on Business
   - "Disabled Questions" multi-enum on Unit

### PRD Requirements to Define

1. **Name Resolution Helpers**: Specify helper functions for tag/user/enum option lookup by name

2. **State Management**: Define state capture and restoration patterns with specific fields per entity type

3. **Error Recovery**: Specify behavior on partial failure - continue, abort, or prompt user

4. **Interactive Flow**: Define confirmation prompt format and skip/abort options

### Architecture Considerations

1. **Utility Module**: Create `_demo_utils.py` with:
   - Name resolution helpers (tags, users, enum options)
   - State capture/restore manager
   - Confirmation prompt utilities
   - Operation logging

2. **Demo Structure**: Each demo category should:
   - Capture initial state of affected entities
   - Preview operations before execution
   - Prompt for confirmation
   - Execute with error handling
   - Update state tracker
   - Provide rollback capability

---

## Appendix: Source File References

| File | Purpose | Key Sections |
|------|---------|--------------|
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` | SaveSession implementation | Action methods (669-1671), preview (426-465), commit (469-553) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/custom_field_accessor.py` | Custom field get/set/remove | _resolve_gid (135-166), set (55-63) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/task.py` | Task model with custom fields | get_custom_fields (117-134) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tags.py` | Tag client operations | list_for_workspace_async (379-411) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/users.py` | User client operations | list_for_workspace_async (216-254) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/tasks.py` | Task client operations | list_async (421-486) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/clients/sections.py` | Section client operations | list_for_project_async (392-430) |
| `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/models.py` | SaveResult, ActionOperation | SaveResult (112-166), ActionOperation (219-388) |

---

## Document Status

**Created**: 2025-12-12
**Discovery Phase**: Complete
**Next Session**: PRD Creation (Session 2) - Requires live workspace verification first
