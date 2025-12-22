# Discovery: Pipeline Automation Enhancement

**Initiative**: Pipeline Automation Enhancement - From Exists to Expert
**Session**: 1 of 7 - Discovery
**Date**: 2025-12-18
**Status**: Complete

---

## Executive Summary

This discovery document analyzes the current codebase and Asana API capabilities to answer the 20 open questions from Prompt 0. The findings will directly inform PRD creation in Session 2.

### Key Findings

| Area | Status | Summary |
|------|--------|---------|
| Task Duplication | **GAP** | `duplicate_async()` does NOT exist in TasksClient - must be added |
| Subtask Wait | **GAP** | No wait mechanism exists - polling strategy recommended |
| Field Seeding Write | **GAP** | `FieldSeeder` computes only - `write_fields_async()` needed |
| ProcessHolder Discovery | **EXISTS** | `unit.process_holder` property exists via `HolderRef` descriptor |
| Rep Field | **EXISTS** | `PeopleField` descriptor returns list of user dicts with GIDs |
| Comments | **EXISTS** | `create_comment_async()` fully implemented in StoriesClient |
| set_parent() | **EXISTS** | Supports `insert_after` parameter for ordering |

---

## Open Questions Resolved

### Task Duplication (Q1-Q4)

#### Q1: Does TasksClient have `duplicate_async()` or do we need to add it?

**Answer: NO - Must be added**

**Evidence**: `src/autom8_asana/clients/tasks.py` (1112 lines analyzed)

The TasksClient contains these methods:
- `get_async()` / `get()` (line 86-171)
- `create_async()` / `create()` (line 173-347)
- `update_async()` / `update()` (line 349-449)
- `delete_async()` / `delete()` (line 451-471)
- `list_async()` (line 473-538)
- `subtasks_async()` (line 544-610)
- `dependents_async()` (line 612-664)
- P1 Direct Methods: `add_tag_async()`, `remove_tag_async()`, `move_to_section_async()`, `set_assignee_async()`, `add_to_project_async()`, `remove_from_project_async()`

**No `duplicate_async()` method exists.** A grep for "duplicate" across the entire `src/autom8_asana` directory found only references in error handling and business model code, not in TasksClient.

**Implementation Required**: Add wrapper for Asana's `POST /tasks/{task_gid}/duplicate` endpoint.

---

#### Q2: What duplication options does Asana API support (subtasks, attachments, etc.)?

**Answer: Comprehensive options available**

**Source**: [Asana API Documentation](https://developers.asana.com/reference/duplicatetask) and [Forum Discussion](https://forum.asana.com/t/now-available-project-and-task-duplication/49371)

**Required Parameter**:
- `name` - Name for the duplicated task

**Optional Parameters**:
- `team` - Specify a team for the new task
- `include` - Array of attributes to copy over
- `schedule_dates` - Automatic due-date shifting with `due_on`/`start_on` and `should_skip_weekends`

**`include` Parameter Options** (for tasks):
- `"notes"` - Copy task notes
- `"assignee"` - Copy assignee
- `"subtasks"` - **Copy subtasks (critical for our use case)**
- `"attachments"` - Copy attachments
- `"dates"` - Copy due dates
- `"dependencies"` - Copy task dependencies
- `"collaborators"` - Copy followers
- `"tags"` - Copy tags

**Response**: Returns a **job object** with `resource_subtype: "duplicate_task"` and `status: "in_progress"`. The `new_task` object with GID is available immediately in the response.

---

#### Q3: How long should we wait for subtasks? Fixed delay vs. polling?

**Answer: Polling recommended, with 2-second configurable timeout**

**Rationale**:
1. Asana duplication is **asynchronous** - the endpoint returns a job, and subtask creation happens in the background
2. Fixed delay is wasteful for simple tasks and insufficient for complex ones
3. The new task GID is available immediately, so we can poll `subtasks_async()` to count children

**Recommended Strategy**:
```python
async def wait_for_subtasks_async(
    task_gid: str,
    expected_count: int,
    timeout_seconds: float = 2.0,
    poll_interval: float = 0.2,
) -> bool:
    """Poll until subtask count matches expected or timeout."""
```

**Configuration**: Add to `AutomationConfig`:
- `subtask_wait_timeout_seconds: float = 2.0`
- `subtask_poll_interval_seconds: float = 0.2`

---

#### Q4: Do we know expected subtask count from template, or poll until stable?

**Answer: Get expected count from template, then poll until match**

**Evidence**: `src/autom8_asana/automation/pipeline.py` lines 222-226

```python
# Step 2: Discover template in target project
template_discovery = TemplateDiscovery(context.client)
template_task = await template_discovery.find_template_task_async(
    target_project_gid
)
```

**Strategy**:
1. After finding template, fetch `template_task.num_subtasks` (available in Task model, line 76 in `task.py`)
2. Alternatively, call `subtasks_async(template_gid).collect()` to get exact count
3. Poll duplicated task until subtask count matches template count

**Fallback**: If template subtask count unavailable, poll until count stabilizes (same count for 2 consecutive checks).

---

### Field Seeding (Q5-Q8)

#### Q5: How do we map field names to GIDs for update_async()?

**Answer: CustomFieldAccessor handles resolution via `_resolve_gid()`**

**Evidence**: `src/autom8_asana/models/custom_field_accessor.py` lines 297-361

```python
def _resolve_gid(self, name_or_gid: str) -> str:
    """Resolve field name to GID with optional strict validation."""
    # Check if this looks like a GID (all digits)
    if name_or_gid.isdigit():
        return name_or_gid

    # Try local index first (case-insensitive lookup)
    normalized = name_or_gid.lower().strip()
    if normalized in self._name_to_gid:
        return self._name_to_gid[normalized]

    # Try resolver if available
    if self._resolver:
        resolved = self._resolver.resolve(name_or_gid)
        if resolved:
            return resolved
```

**Key Methods**:
- `to_api_dict()` (line 205-217): Converts modifications to `{gid: value}` format for API
- `_format_value_for_api()` (line 219-259): Handles type conversion (Decimal, lists, enums)

**Strategy for write_fields_async()**:
1. Get target task's `custom_fields` list via `get_async()` with `opt_fields=["custom_fields"]`
2. Build `CustomFieldAccessor` from target task's fields
3. Set values by name - accessor resolves to GIDs
4. Call `update_async()` with `custom_fields=accessor.to_api_dict()`

---

#### Q6: Single update_async() with all fields, or multiple calls?

**Answer: Single update_async() call**

**Evidence**: `src/autom8_asana/clients/tasks.py` lines 371-394

```python
@error_handler
async def update_async(
    self,
    task_gid: str,
    *,
    raw: bool = False,
    **kwargs: Any,
) -> Task | dict[str, Any]:
    """Update a task."""
    result = await self._http.put(f"/tasks/{task_gid}", json={"data": kwargs})
```

Asana API accepts all custom fields in a single `custom_fields` dict:
```python
await client.tasks.update_async(
    task_gid,
    custom_fields={
        "gid_1": "value_1",
        "gid_2": 123,
        "gid_3": "enum_option_gid",
    }
)
```

**Recommendation**: Single call for efficiency. Performance target: <300ms.

---

#### Q7: Enum fields require option GID - how to resolve value to GID?

**Answer: Enum options are embedded in custom_fields response**

**Evidence**: `src/autom8_asana/models/custom_field_accessor.py` lines 364-380

When a task is fetched with `opt_fields=["custom_fields.enum_options"]`, each enum field includes its available options:

```json
{
  "gid": "field_gid",
  "name": "Vertical",
  "resource_subtype": "enum",
  "enum_options": [
    {"gid": "opt_1", "name": "Dental"},
    {"gid": "opt_2", "name": "Medical"},
    {"gid": "opt_3", "name": "Legal"}
  ],
  "enum_value": {"gid": "opt_1", "name": "Dental"}
}
```

**Resolution Strategy**:
1. When setting enum by display name, search `enum_options` for matching name
2. Extract GID from matching option
3. Pass GID to API

**CustomFieldAccessor already handles this** - it accepts either GID or dict with `gid` key (line 426-437).

---

#### Q8: What if target project doesn't have a field that source had?

**Answer: Skip missing fields gracefully, log warning**

**Evidence**: FieldSeeder design pattern at `src/autom8_asana/automation/seeding.py` lines 213-250

```python
def _get_field_value(self, entity: Any, field_name: str) -> Any:
    """Get field value from entity, handling enums and various sources."""
    # ... tries multiple sources ...
    return None  # Returns None if not found
```

**Strategy**:
1. Build target task's available field names via `accessor.list_available_fields()`
2. Filter seeded fields to only those that exist on target
3. Log warning for skipped fields:
   ```
   WARNING: Field 'Legacy Status' not found on target project, skipping
   ```
4. Continue with remaining fields - don't fail the conversion

---

### Hierarchy (Q9-Q12)

#### Q9: Does `unit.process_holder` property exist? Or need to fetch?

**Answer: Property EXISTS via HolderRef descriptor**

**Evidence**: `src/autom8_asana/models/business/unit.py` lines 78-79

```python
# Navigation descriptors (TDD-HARDENING-C, ADR-0075)
process_holder = HolderRef["ProcessHolder"]()
```

And the private attribute (line 72):
```python
_process_holder: ProcessHolder | None = PrivateAttr(default=None)
```

**Access Pattern**:
```python
# If unit is hydrated (from Business.from_gid_async or unit.to_business_async)
process_holder = unit.process_holder  # Returns ProcessHolder or None

# If not hydrated, need to fetch
if unit.process_holder is None:
    await unit._fetch_holders_async(client)
    process_holder = unit.process_holder
```

**Discovery from Source Process**:
```python
source_process: Process
# Navigate upward
unit = source_process.unit  # Via cached reference
process_holder = unit.process_holder if unit else None
```

---

#### Q10: How to identify preceding Process? By created_at? Position?

**Answer: By created_at (oldest first), then name for stability**

**Evidence**: `src/autom8_asana/models/business/process.py` lines 347-359

```python
def _populate_children(self, subtasks: list[Task]) -> None:
    """Populate processes from fetched subtasks."""
    # Sort by created_at (oldest first), then by name for stability
    sorted_tasks = sorted(
        subtasks,
        key=lambda t: (t.created_at or "", t.name or ""),
    )
```

**Strategy to find preceding Process**:
```python
processes = process_holder.processes  # Already sorted by created_at
source_index = next(
    (i for i, p in enumerate(processes) if p.gid == source_process.gid),
    -1
)
preceding_process = processes[source_index] if source_index >= 0 else None
# OR: Insert at end if source not found
```

**Note**: The source process (Sales) becomes the "preceding" process for the new process (Onboarding) in the hierarchy.

---

#### Q11: Does `set_parent(insert_after=X)` put new task immediately after X?

**Answer: YES**

**Evidence**: `src/autom8_asana/persistence/session.py` lines 1747-1835

```python
def set_parent(
    self,
    task: AsanaResource,
    parent: AsanaResource | str | None,
    *,
    insert_before: AsanaResource | str | None = None,
    insert_after: AsanaResource | str | None = None,
) -> SaveSession:
    """Set or change the parent of a task.
    ...
    - Reorder subtask: `set_parent(task, same_parent, insert_after=sibling)`
    """
```

The method builds `extra_params` (lines 1807-1816):
```python
if insert_after is not None:
    extra_params["insert_after"] = (
        insert_after if isinstance(insert_after, str) else insert_after.gid
    )
```

**Usage Pattern**:
```python
async with SaveSession(client) as session:
    session.set_parent(
        new_process,
        process_holder,
        insert_after=source_process,  # Places new process after source
    )
    await session.commit_async()
```

This maps to Asana's `POST /tasks/{task_gid}/setParent` with `insert_after` parameter.

---

#### Q12: What happens if ProcessHolder is missing? Create or fail gracefully?

**Answer: Log warning and fail gracefully (do NOT create)**

**Per Prompt 0 Scope**: "ProcessHolder auto-creation (if missing, log warning)" is **explicitly out of scope**.

**Recommended Behavior**:
```python
process_holder = unit.process_holder if unit else None
if process_holder is None:
    logger.warning(
        "ProcessHolder not found for unit %s, skipping hierarchy placement",
        unit.gid if unit else "unknown"
    )
    # Continue with conversion - new process will be top-level in project
    # This is acceptable degradation, not a failure
```

**Rationale**: ProcessHolder absence indicates data hygiene issue. Auto-creation would mask the problem. Log the warning so it can be investigated and fixed.

---

### Assignee (Q13-Q16)

#### Q13: What does `business.rep` return? List of dicts? Single GID?

**Answer: List of user dicts with GID, name, etc.**

**Evidence**: `src/autom8_asana/models/business/business.py` line 296

```python
# People fields (1)
rep = PeopleField()
```

And `src/autom8_asana/models/business/descriptors.py` defines PeopleField (analyzed):

The `PeopleField` descriptor returns `list[dict[str, Any]]` - the raw `people_value` from Asana's custom field response:

```json
[
  {"gid": "123456789", "name": "John Smith", "resource_type": "user"},
  {"gid": "987654321", "name": "Jane Doe", "resource_type": "user"}
]
```

**Access Pattern**:
```python
rep_users = business.rep  # Returns list[dict] or None
if rep_users and len(rep_users) > 0:
    assignee_gid = rep_users[0]["gid"]  # First rep
```

---

#### Q14: Different rep for Sales vs Implementation vs Retention?

**Answer: NEEDS CLARIFICATION - Currently same field on Business**

**Evidence**: Only one `rep` field found on Business (line 296). Unit also has `rep` (line 107 in unit.py):

```python
# In unit.py
rep = PeopleField()
```

**Current State**:
- `Business.rep` - Single rep field
- `Unit.rep` - Single rep field (may inherit or override)

**Open Question for User**:
1. Is there a separate "Implementation Rep" or "Sales Rep" field?
2. Should we use `Business.rep` for all ProcessTypes?
3. Or should we look at `Unit.rep` for unit-specific assignment?

**Recommendation**: Default to `Unit.rep` if populated, fallback to `Business.rep`.

---

#### Q15: Is rep always on Unit, or varies by ProcessType?

**Answer: Rep exists on both Business and Unit**

**Evidence**:
- `Business.rep` (business.py line 296)
- `Unit.rep` (unit.py line 107)

**Lookup Chain** (recommended):
1. Try `source_process.unit.rep` first
2. Fallback to `source_process.business.rep`
3. If both empty, leave assignee unset (log warning)

**Note**: Process does not have a `rep` field - only `assigned_to`:
```python
# process.py line 236
assigned_to = PeopleField()
```

---

#### Q16: What's the fallback if rep field is empty?

**Answer: Leave assignee unset, log warning**

**Recommendation**:
```python
rep_users = unit.rep or business.rep if business else None
if not rep_users:
    logger.warning(
        "No rep found for conversion %s -> %s, leaving assignee unset",
        source_process.gid,
        new_process.gid,
    )
    # Don't set assignee - better than wrong assignment
else:
    assignee_gid = rep_users[0]["gid"]
    await client.tasks.set_assignee_async(new_process.gid, assignee_gid)
```

---

### Comments (Q17-Q20)

#### Q17: What should the onboarding comment say?

**Answer: Template with conversion context**

**Recommended Template** (from Prompt 0):
```
This {ProcessType} process was automatically created when "{Source Process Name}"
was converted on {Date}.

Source: {Source Project Name} > Converted
```

**Example**:
```
This Onboarding process was automatically created when "Acme Corp - Sales"
was converted on 2025-12-18.

Source: Sales Pipeline > Converted
```

**Extended Template** (optional - adds contact info):
```
This Onboarding process was automatically created when "Acme Corp - Sales"
was converted on 2025-12-18.

Source: Sales Pipeline > Converted
Contact: {Contact Name} ({Contact Phone})
Unit: {Unit Name}
```

---

#### Q18: Include link to source Process in comment?

**Answer: YES - Include Asana task URL**

**Format**:
```
Source Process: https://app.asana.com/0/{project_gid}/{task_gid}
```

**Example**:
```
This Onboarding process was automatically created when "Acme Corp - Sales"
was converted on 2025-12-18.

Source Process: https://app.asana.com/0/1234567890/9876543210
```

**Implementation**:
```python
source_link = f"https://app.asana.com/0/{source_project_gid}/{source_process.gid}"
```

---

#### Q19: Comment timing - before or after field seeding?

**Answer: AFTER field seeding and hierarchy placement**

**Rationale**:
1. Comment should reflect final state of the process
2. If field seeding fails, we may want to include that in the comment
3. Comment creation is "nice to have" - if it fails, the conversion is still valid

**Order**:
1. Duplicate task with subtasks
2. Wait for subtasks
3. Set ProcessHolder parent
4. Seed and write fields
5. Set assignee
6. **Add comment (last)**

---

#### Q20: If comment fails, continue or fail conversion?

**Answer: Log warning and CONTINUE**

**Per Prompt 0 Constraint**: "Graceful Degradation: If any enhancement step fails, log and continue (don't break conversion)"

**Implementation**:
```python
try:
    await client.stories.create_comment_async(
        task=new_process.gid,
        text=comment_text,
    )
    actions_executed.append("add_onboarding_comment")
except Exception as e:
    logger.warning(
        "Failed to add onboarding comment to %s: %s",
        new_process.gid,
        str(e),
    )
    # Continue - comment is non-critical
```

**Evidence** for `create_comment_async`: `src/autom8_asana/clients/stories.py` lines 352-392

```python
async def create_comment_async(
    self,
    *,
    task: str,
    text: str,
    raw: bool = False,
    html_text: str | None = None,
    is_pinned: bool | None = None,
) -> Story | dict[str, Any]:
    """Create a comment on a task."""
```

---

## Gap Analysis Summary

### Gap 1: Task Duplication with Subtasks

| Aspect | Current | Required | Effort |
|--------|---------|----------|--------|
| Method | `create_async()` | `duplicate_async()` | Medium |
| Subtasks | None | Full duplication | Included |
| API Endpoint | `POST /tasks` | `POST /tasks/{gid}/duplicate` | Medium |

**Implementation**:
```python
# New method in TasksClient
async def duplicate_async(
    self,
    task_gid: str,
    *,
    name: str,
    include: list[str] | None = None,  # ["subtasks", "notes", "assignee", ...]
    raw: bool = False,
) -> Task | dict[str, Any]:
    """Duplicate a task with optional attributes."""
```

### Gap 2: Subtask Wait Strategy

| Aspect | Current | Required | Effort |
|--------|---------|----------|--------|
| Wait Mechanism | None | Polling utility | Low |
| Timeout | N/A | Configurable (default 2s) | Low |
| Detection | N/A | Count-based match | Low |

**Implementation**:
```python
# New utility class
class SubtaskWaiter:
    async def wait_for_subtasks_async(
        self,
        task_gid: str,
        expected_count: int,
        timeout: float = 2.0,
    ) -> bool:
        """Poll until subtasks match expected count or timeout."""
```

### Gap 3: Field Seeding Write

| Aspect | Current | Required | Effort |
|--------|---------|----------|--------|
| Compute | `seed_fields_async()` | Keep | None |
| Write | None | `write_fields_async()` | Medium |
| GID Resolution | `CustomFieldAccessor` exists | Use it | Low |

**Implementation**:
```python
# Extend FieldSeeder
async def write_fields_async(
    self,
    target_task_gid: str,
    fields: dict[str, Any],
) -> bool:
    """Write seeded field values to target task via API."""
```

### Gap 4: Hierarchy Placement

| Aspect | Current | Required | Effort |
|--------|---------|----------|--------|
| ProcessHolder Discovery | `unit.process_holder` exists | Use it | None |
| set_parent() | Exists with `insert_after` | Use it | None |
| Integration | None | Wire into pipeline | Low |

### Gap 5: Assignee Assignment

| Aspect | Current | Required | Effort |
|--------|---------|----------|--------|
| Rep Field | `PeopleField` exists | Use it | None |
| set_assignee_async | Exists | Use it | None |
| Integration | None | Wire into pipeline | Low |

### Gap 6: Onboarding Comment

| Aspect | Current | Required | Effort |
|--------|---------|----------|--------|
| create_comment_async | Exists | Use it | None |
| Template | None | Define template | Low |
| Integration | None | Wire into pipeline | Low |

---

## Implementation Dependencies

```
duplicate_async() [NEW]
       |
       v
SubtaskWaiter [NEW]
       |
       v
write_fields_async() [NEW] --> CustomFieldAccessor [EXISTS]
       |
       v
set_parent() [EXISTS] <-- ProcessHolder discovery [EXISTS]
       |
       v
set_assignee_async() [EXISTS] <-- rep field [EXISTS]
       |
       v
create_comment_async() [EXISTS]
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Asana duplicate API returns before subtasks ready | High | High | Polling with configurable timeout |
| ProcessHolder not populated on source Process | Medium | Medium | Fetch via `unit._fetch_holders_async()` on demand |
| Custom field name doesn't exist on target project | Medium | Low | Skip field, log warning |
| Rep field empty | Low | Low | Leave assignee unset, log warning |
| Comment creation fails | Low | Low | Log warning, continue |
| Subtask wait timeout exceeded | Medium | Medium | Log warning, proceed anyway (subtasks will appear eventually) |

---

## Blocking Issues

**None identified.** All 20 questions have been answered with sufficient detail for PRD creation.

---

## Recommendations for Session 2 (PRD)

1. **FR-DUP-***: Define `duplicate_async()` requirements with explicit `include` options
2. **FR-WAIT-***: Define configurable timeout strategy with sensible defaults
3. **FR-SEED-***: Define field write requirements with graceful degradation
4. **FR-HIER-***: Define ProcessHolder discovery and ordering requirements
5. **FR-ASSIGN-***: Define rep resolution chain (Unit -> Business -> skip)
6. **FR-COMMENT-***: Define comment template and content requirements
7. **NFR-***: Performance targets per operation

---

## Quality Gate Checklist

- [x] All 20 open questions answered or explicitly marked as needing user input
- [x] Gap analysis complete for all 6 enhancement areas
- [x] ProcessHolder discovery pattern documented
- [x] Rep field mapping documented
- [x] Custom field GID resolution strategy defined
- [x] No blocking issues for Session 2

---

## Files Analyzed

| File | Lines | Key Findings |
|------|-------|--------------|
| `src/autom8_asana/automation/pipeline.py` | 313 | `execute_async()` flow identified, insertion points clear |
| `src/autom8_asana/automation/seeding.py` | 280 | `FieldSeeder` design understood, extension point identified |
| `src/autom8_asana/clients/tasks.py` | 1112 | No `duplicate_async()`, `update_async()` accepts custom_fields |
| `src/autom8_asana/persistence/session.py` | 2193 | `set_parent()` with `insert_after` confirmed |
| `src/autom8_asana/clients/stories.py` | 463 | `create_comment_async()` fully implemented |
| `src/autom8_asana/models/business/unit.py` | 535 | `process_holder` property exists via `HolderRef` |
| `src/autom8_asana/models/business/process.py` | 360 | ProcessHolder structure, `_populate_children()` sorting |
| `src/autom8_asana/models/business/business.py` | 787 | `rep = PeopleField()` confirmed |
| `src/autom8_asana/models/custom_field_accessor.py` | 470 | GID resolution, `to_api_dict()` format |

---

## Sources

- [Asana API - Duplicate Task](https://developers.asana.com/reference/duplicatetask)
- [Asana Forum - Project and Task Duplication](https://forum.asana.com/t/now-available-project-and-task-duplication/49371)
- [Asana Forum - Duplication with Subtasks](https://forum.asana.com/t/duplication-of-task-with-subtasks-and-subsections-with-the-api/98629)
