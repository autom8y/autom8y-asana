# TDD: Pipeline Automation Enhancement

## Metadata
- **TDD ID**: TDD-PIPELINE-AUTOMATION-ENHANCEMENT
- **Status**: Draft
- **Author**: Architect (Claude)
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **PRD Reference**: [PRD-PIPELINE-AUTOMATION-ENHANCEMENT](../requirements/PRD-PIPELINE-AUTOMATION-ENHANCEMENT.md)
- **Related TDDs**: [TDD-AUTOMATION-LAYER](TDD-AUTOMATION-LAYER.md)
- **Related ADRs**: [ADR-0110](../decisions/ADR-0110-task-duplication-strategy.md), [ADR-0111](../decisions/ADR-0111-subtask-wait-strategy.md), [ADR-0112](../decisions/ADR-0112-custom-field-gid-resolution.md), [ADR-0113](../decisions/ADR-0113-rep-field-cascade-pattern.md)

## Overview

This design extends the Pipeline Automation Layer to achieve legacy feature parity. We add four new components: `duplicate_async()` in TasksClient for task duplication with subtasks, `SubtaskWaiter` for polling-based subtask readiness detection, `write_fields_async()` in FieldSeeder for persisting computed fields, and integration wiring in `PipelineConversionRule.execute_async()` to orchestrate the complete conversion flow including hierarchy placement, assignee assignment, and onboarding comments.

## Requirements Summary

The PRD defines 46 functional requirements across 7 categories:
- **FR-DUP-***: Task duplication with subtasks (5 requirements)
- **FR-WAIT-***: Subtask wait polling strategy (7 requirements)
- **FR-SEED-***: Field seeding write to API (7 requirements)
- **FR-HIER-***: Hierarchy placement under ProcessHolder (7 requirements)
- **FR-ASSIGN-***: Assignee from rep field cascade (6 requirements)
- **FR-COMMENT-***: Onboarding comment creation (8 requirements)
- **FR-ERR-***: Graceful degradation error handling (6 requirements)

See PRD for complete acceptance criteria.

## System Context

```
                                    ┌─────────────────────────────────┐
                                    │       Asana API                 │
                                    │  - POST /tasks/{gid}/duplicate  │
                                    │  - POST /tasks/{gid}/setParent  │
                                    │  - PUT /tasks/{gid}             │
                                    │  - POST /tasks/{gid}/stories    │
                                    └──────────────┬──────────────────┘
                                                   │
                    ┌──────────────────────────────┴──────────────────────────────┐
                    │                                                              │
         ┌──────────▼──────────┐    ┌──────────────────┐    ┌──────────────────────▼─┐
         │    TasksClient      │    │   StoriesClient   │    │    SaveSession         │
         │  - duplicate_async()│    │  - create_comment │    │  - set_parent()        │
         │  - update_async()   │    │    _async()       │    │    with insert_after   │
         │  - subtasks_async() │    └──────────────────┘    └────────────────────────┘
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │   SubtaskWaiter     │
         │  - wait_for_        │
         │    subtasks_async() │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────────────────────────────────────────────────────────┐
         │                    PipelineConversionRule.execute_async()               │
         │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────┐ │
         │  │ Duplicate │→ │   Wait    │→ │ Hierarchy │→ │   Seed    │→ │Assignee│ │
         │  │   Task    │  │ Subtasks  │  │ Placement │  │  Fields   │  │  + Cmt │ │
         │  └───────────┘  └───────────┘  └───────────┘  └───────────┘  └────────┘ │
         └─────────────────────────────────────────────────────────────────────────┘
                    │
         ┌──────────▼──────────┐
         │    FieldSeeder      │
         │  - seed_fields_async│◄───────── EXISTS (compute only)
         │  - write_fields_    │
         │    async()          │◄───────── NEW (persist to API)
         └─────────────────────┘
```

## Design

### Component Architecture

| Component | Responsibility | Location | Status |
|-----------|---------------|----------|--------|
| `TasksClient.duplicate_async()` | Wrap Asana duplicate API endpoint | `clients/tasks.py` | NEW |
| `SubtaskWaiter` | Poll for subtask creation completion | `automation/waiter.py` | NEW |
| `FieldSeeder.write_fields_async()` | Persist seeded values to API | `automation/seeding.py` | EXTEND |
| `PipelineConversionRule` | Orchestrate full conversion flow | `automation/pipeline.py` | EXTEND |

### Component 1: TasksClient.duplicate_async()

**Purpose**: Wrap Asana's `POST /tasks/{task_gid}/duplicate` endpoint.

**Signature**:
```python
@overload
async def duplicate_async(
    self,
    task_gid: str,
    *,
    name: str,
    include: list[str] | None = None,
    raw: Literal[False] = ...,
) -> Task: ...

@overload
async def duplicate_async(
    self,
    task_gid: str,
    *,
    name: str,
    include: list[str] | None = None,
    raw: Literal[True],
) -> dict[str, Any]: ...

@error_handler
async def duplicate_async(
    self,
    task_gid: str,
    *,
    name: str,
    include: list[str] | None = None,
    raw: bool = False,
) -> Task | dict[str, Any]:
    """Duplicate a task with optional attribute copying.

    Per FR-DUP-001: Wraps Asana's POST /tasks/{task_gid}/duplicate.

    Args:
        task_gid: GID of the task to duplicate.
        name: Name for the new task (required by Asana API).
        include: List of attributes to copy. Valid values:
            - "subtasks": Copy all subtasks
            - "notes": Copy task description
            - "assignee": Copy assignee
            - "attachments": Copy attachments
            - "dates": Copy due dates
            - "dependencies": Copy dependencies
            - "collaborators": Copy followers
            - "tags": Copy tags
        raw: If True, return raw dict instead of Task model.

    Returns:
        Task model (or dict if raw=True) representing the new task.
        The new_task.gid is immediately available.
        Note: Subtasks are created asynchronously by Asana.

    Raises:
        ValidationError: If task_gid is invalid.
        NotFoundError: If source task doesn't exist.
    """
```

**API Request**:
```json
POST /tasks/{task_gid}/duplicate
{
  "data": {
    "name": "New Process Name",
    "include": ["subtasks", "notes"]
  }
}
```

**API Response** (Asana returns job object):
```json
{
  "gid": "job_gid",
  "resource_type": "job",
  "resource_subtype": "duplicate_task",
  "status": "in_progress",
  "new_task": {
    "gid": "new_task_gid",
    "resource_type": "task",
    "name": "New Process Name"
  }
}
```

**Implementation Notes**:
- Extract and return `new_task` from job response
- Subtask duplication is asynchronous - caller must wait separately
- Follow existing TasksClient patterns (overloads, error_handler, validate_gid)

### Component 2: SubtaskWaiter

**Purpose**: Poll for subtask creation completion after task duplication.

**Location**: `src/autom8_asana/automation/waiter.py` (new file)

**Signature**:
```python
class SubtaskWaiter:
    """Utility for waiting on asynchronous subtask creation.

    Per FR-WAIT-001: Provides polling-based wait for subtask availability.
    Per ADR-0111: Chosen over fixed delay or webhooks.

    After duplicating a task with subtasks, Asana creates the subtasks
    asynchronously. This utility polls until the expected subtask count
    is reached or timeout expires.

    Example:
        waiter = SubtaskWaiter(client)

        # Get expected count from template before duplication
        template_subtasks = await client.tasks.subtasks_async(template_gid).collect()
        expected_count = len(template_subtasks)

        # Duplicate and wait
        new_task = await client.tasks.duplicate_async(template_gid, name="New Task")
        ready = await waiter.wait_for_subtasks_async(
            new_task.gid,
            expected_count=expected_count,
            timeout=2.0,
        )
        if not ready:
            logger.warning("Subtask creation timed out, proceeding anyway")
    """

    def __init__(
        self,
        client: AsanaClient,
        *,
        default_timeout: float = 2.0,
        default_poll_interval: float = 0.2,
    ) -> None:
        """Initialize SubtaskWaiter.

        Args:
            client: AsanaClient for API operations.
            default_timeout: Default timeout in seconds (FR-WAIT-003).
            default_poll_interval: Default poll interval in seconds (FR-WAIT-004).
        """

    async def wait_for_subtasks_async(
        self,
        task_gid: str,
        expected_count: int,
        *,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> bool:
        """Wait for subtask count to reach expected value.

        Per FR-WAIT-002: Polls until count matches or timeout.

        Args:
            task_gid: GID of the parent task.
            expected_count: Number of subtasks to wait for.
            timeout: Timeout in seconds (default: 2.0).
            poll_interval: Poll interval in seconds (default: 0.2).

        Returns:
            True if expected count reached, False if timeout.

        Side Effects:
            Logs warning on timeout with current vs expected count.
        """

    async def get_subtask_count_async(self, task_gid: str) -> int:
        """Get current subtask count for a task.

        Per FR-WAIT-007: Uses subtasks_async() to get accurate count.

        Args:
            task_gid: GID of the parent task.

        Returns:
            Current number of subtasks.
        """
```

**Algorithm**:
```
START
  start_time = now()
  while (now() - start_time) < timeout:
    current_count = get_subtask_count_async(task_gid)
    if current_count >= expected_count:
      return True
    await asyncio.sleep(poll_interval)

  log.warning("Subtask timeout: expected=%d, actual=%d", expected_count, current_count)
  return False
END
```

### Component 3: FieldSeeder.write_fields_async()

**Purpose**: Persist seeded field values to the target task via API.

**Signature** (added to existing FieldSeeder class):
```python
async def write_fields_async(
    self,
    target_task_gid: str,
    fields: dict[str, Any],
    *,
    target_project_gid: str | None = None,
) -> WriteResult:
    """Write seeded field values to target task.

    Per FR-SEED-001: Persists computed field values to API.
    Per FR-SEED-002: Uses single update_async() call.
    Per ADR-0112: Uses CustomFieldAccessor for GID resolution.

    Args:
        target_task_gid: GID of the task to update.
        fields: Dict of field name to value (from seed_fields_async).
        target_project_gid: Optional project GID for enum option resolution.

    Returns:
        WriteResult with success status and details.

    Side Effects:
        - Logs warning for fields not found on target (FR-SEED-005)
        - Single API call to update_async() (FR-SEED-002)
    """

@dataclass
class WriteResult:
    """Result of field write operation."""
    success: bool
    fields_written: list[str]
    fields_skipped: list[str]  # Not found on target
    error: str | None = None
```

**Algorithm**:
```
START
  # Step 1: Fetch target task with custom field definitions
  target_task = await client.tasks.get_async(
    target_task_gid,
    opt_fields=["custom_fields", "custom_fields.enum_options"]
  )

  # Step 2: Build accessor from target's field definitions
  accessor = CustomFieldAccessor(
    data=target_task.custom_fields,
    strict=False,  # Don't fail on unknown fields
  )
  available_fields = set(accessor.list_available_fields())

  # Step 3: Filter and resolve fields
  fields_to_write = {}
  fields_skipped = []

  for name, value in fields.items():
    if name not in available_fields:
      log.warning("Field '%s' not found on target, skipping", name)
      fields_skipped.append(name)
      continue

    # Set value (accessor handles GID resolution and type conversion)
    accessor.set(name, value)
    fields_to_write.append(name)

  # Step 4: Single API call with all fields (FR-SEED-002)
  if accessor.has_changes():
    await client.tasks.update_async(
      target_task_gid,
      custom_fields=accessor.to_api_dict()
    )

  return WriteResult(
    success=True,
    fields_written=fields_to_write,
    fields_skipped=fields_skipped,
  )
END
```

### Component 4: PipelineConversionRule.execute_async() Enhancement

**Purpose**: Orchestrate the complete conversion flow with all enhancement steps.

**Enhanced Algorithm**:
```python
async def execute_async(
    self,
    entity: AsanaResource,
    context: AutomationContext,
) -> AutomationResult:
    """Execute pipeline conversion with full enhancements.

    Per PRD: Orchestrates all enhancement steps with graceful degradation.

    Algorithm:
    1. Lookup target project from config
    2. Discover template in target project
    3. Get template subtask count (for wait strategy)
    4. Duplicate template with subtasks (NEW - FR-DUP-005)
    5. Wait for subtasks to be created (NEW - FR-WAIT-006)
    6. Discover ProcessHolder from source Unit (FR-HIER-001)
    7. Set parent to ProcessHolder with insert_after (FR-HIER-002, FR-HIER-003)
    8. Seed and write fields (FR-SEED-001)
    9. Resolve and set assignee from rep (FR-ASSIGN-001)
    10. Add onboarding comment (FR-COMMENT-001)

    Each step is wrapped in try/except for graceful degradation (FR-ERR-001).
    """
```

**Sequence Diagram**:
```
User          PipelineRule    TasksClient    SubtaskWaiter   FieldSeeder    SaveSession   StoriesClient
  |               |               |               |               |              |              |
  |--move to---->|               |               |               |              |              |
  |  CONVERTED   |               |               |               |              |              |
  |               |               |               |               |              |              |
  |               |--get target--|               |               |              |              |
  |               |  project GID |               |               |              |              |
  |               |               |               |               |              |              |
  |               |--find------->|               |               |              |              |
  |               |  template    |--get_async()--|               |              |              |
  |               |               |<--template---|               |              |              |
  |               |               |               |               |              |              |
  |               |--get subtask |               |               |              |              |
  |               |  count       |--subtasks_async()              |              |              |
  |               |               |<--count=5----|               |              |              |
  |               |               |               |               |              |              |
  |               |--duplicate-->|               |               |              |              |
  |               |  with        |--duplicate_async()             |              |              |
  |               |  subtasks    |  include=["subtasks","notes"]  |              |              |
  |               |               |<--new_task---|               |              |              |
  |               |               |  (gid ready)  |               |              |              |
  |               |               |               |               |              |              |
  |               |--wait for----|-------------->|               |              |              |
  |               |  subtasks    |               |--poll---------|              |              |
  |               |               |               |  until ready  |              |              |
  |               |               |               |<--ready=True--|              |              |
  |               |               |               |               |              |              |
  |               |--get--------|               |               |              |              |
  |               |  ProcessHolder               |               |              |              |
  |               |  from unit   |               |               |              |              |
  |               |               |               |               |              |              |
  |               |--set parent--|---------------|---------------|------------->|              |
  |               |  with        |               |               |  set_parent()|              |
  |               |  insert_after|               |               |  insert_after|              |
  |               |               |               |               |              |              |
  |               |--seed and----|---------------|-------------->|              |              |
  |               |  write fields|               |  write_fields_async()        |              |
  |               |               |               |               |<--done-------|              |
  |               |               |               |               |              |              |
  |               |--resolve-----|               |               |              |              |
  |               |  rep from    |               |               |              |              |
  |               |  Unit->Bus   |               |               |              |              |
  |               |               |               |               |              |              |
  |               |--set-------->|               |               |              |              |
  |               |  assignee    |--set_assignee_async()         |              |              |
  |               |               |<--done-------|               |              |              |
  |               |               |               |               |              |              |
  |               |--add---------|---------------|---------------|--------------|------------->|
  |               |  comment     |               |               |              |create_comment|
  |               |               |               |               |              |  _async()   |
  |               |               |               |               |              |<--done------|
  |               |               |               |               |              |              |
  |<--result-----|               |               |               |              |              |
```

### Data Model

#### WriteResult (new dataclass)
```python
@dataclass
class WriteResult:
    """Result of a field write operation."""
    success: bool
    fields_written: list[str]
    fields_skipped: list[str]
    error: str | None = None
```

#### AutomationResult (extended)
```python
@dataclass
class AutomationResult:
    # Existing fields
    rule_id: str
    rule_name: str
    triggered_by_gid: str
    triggered_by_type: str
    actions_executed: list[str] = field(default_factory=list)
    entities_created: list[str] = field(default_factory=list)
    entities_updated: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    execution_time_ms: float = 0.0

    # NEW: Enhancement tracking (FR-ERR-004)
    enhancement_results: dict[str, bool] = field(default_factory=dict)
    # e.g., {"subtask_wait": True, "hierarchy_placement": False, "field_seeding": True}
```

### API Contracts

#### duplicate_async Request/Response

**Request**:
```http
POST /tasks/{task_gid}/duplicate
Content-Type: application/json

{
  "data": {
    "name": "Acme Corp - Onboarding",
    "include": ["subtasks", "notes"]
  }
}
```

**Response**:
```json
{
  "data": {
    "gid": "1234567890",
    "resource_type": "job",
    "resource_subtype": "duplicate_task",
    "status": "in_progress",
    "new_task": {
      "gid": "9876543210",
      "resource_type": "task",
      "name": "Acme Corp - Onboarding"
    }
  }
}
```

#### update_async with custom_fields

**Request**:
```http
PUT /tasks/{task_gid}
Content-Type: application/json

{
  "data": {
    "custom_fields": {
      "1234567890": "555-1234",
      "2345678901": {"gid": "opt_dental"},
      "3456789012": "2025-12-18"
    }
  }
}
```

### Data Flow: Complete Conversion

```
Source Process (Sales)
        │
        ▼
┌───────────────────┐
│ Template Discovery│
│   find_template   │
│   _task_async()   │
└────────┬──────────┘
         │ template_task
         ▼
┌───────────────────┐
│ Get Subtask Count │
│ subtasks_async()  │──► expected_count = 5
│   .collect()      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Duplicate Task    │
│ duplicate_async() │──► new_task (gid available immediately)
│ include=subtasks  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Wait for Subtasks │
│ wait_for_subtasks │──► poll until count=5 or timeout=2s
│   _async()        │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Hierarchy Discover│
│ unit.process_     │──► ProcessHolder
│   holder          │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Set Parent        │
│ session.set_parent│──► new_task is subtask of ProcessHolder
│ (insert_after=    │    positioned after source_process
│  source_process)  │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Seed Fields       │
│ seed_fields_async │──► computed values dict
│ (compute)         │
└────────┬──────────┘
         │ fields dict
         ▼
┌───────────────────┐
│ Write Fields      │
│ write_fields_async│──► API update with custom_fields
│ (persist)         │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Resolve Rep       │
│ Unit.rep ||       │──► assignee_gid
│ Business.rep      │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Set Assignee      │
│ set_assignee_async│──► assignee set on new_task
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Add Comment       │
│ create_comment    │──► onboarding comment with context
│   _async()        │
└────────┬──────────┘
         │
         ▼
   AutomationResult
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Task creation method | `duplicate_async()` over `create_async()` | Subtask duplication handled by Asana API, preserves template structure | [ADR-0110](../decisions/ADR-0110-task-duplication-strategy.md) |
| Subtask readiness detection | Polling with timeout | Simpler than webhooks, more efficient than fixed delay | [ADR-0111](../decisions/ADR-0111-subtask-wait-strategy.md) |
| Custom field name resolution | `CustomFieldAccessor._resolve_gid()` | Reuses existing proven pattern, handles name-to-GID mapping | [ADR-0112](../decisions/ADR-0112-custom-field-gid-resolution.md) |
| Rep field resolution | Unit.rep -> Business.rep cascade | Unit-level rep takes precedence, falls back to business-level | [ADR-0113](../decisions/ADR-0113-rep-field-cascade-pattern.md) |

## Complexity Assessment

**Level: Module**

This is a module-level enhancement, not a service or platform:
- Extends existing automation layer, not a new system
- 4 components with clear boundaries
- No new external dependencies
- No independent deployment needs
- Single consumer (PipelineConversionRule)

**Escalation Signals Not Present**:
- No multiple consumers requiring different behaviors
- No external API contract beyond existing SDK patterns
- No cross-service coordination

## Implementation Plan

### Phase 1: Core Components (Day 1)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `duplicate_async()` in TasksClient | Existing TasksClient patterns | 2 hours |
| Sync wrapper `duplicate()` | `duplicate_async()` | 30 min |
| Unit tests for duplicate | Test fixtures | 1 hour |

### Phase 2: Wait Strategy (Day 1)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `SubtaskWaiter` class | TasksClient | 1.5 hours |
| Unit tests for waiter | Mock client | 1 hour |

### Phase 3: Field Seeding Write (Day 2)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| `write_fields_async()` in FieldSeeder | CustomFieldAccessor | 2 hours |
| `WriteResult` dataclass | None | 15 min |
| Unit tests for write | Mock accessor | 1 hour |

### Phase 4: Pipeline Integration (Day 2)

| Deliverable | Dependencies | Estimate |
|-------------|--------------|----------|
| Enhance `execute_async()` | All Phase 1-3 | 3 hours |
| Hierarchy placement logic | SaveSession | 1 hour |
| Assignee resolution logic | PeopleField | 1 hour |
| Comment generation | StoriesClient | 30 min |
| Integration tests | Full stack | 2 hours |

### Migration Strategy

No migration needed - all changes are additive. Existing automation consumers are unaffected:
- `duplicate_async()` is a new method
- `write_fields_async()` is a new method
- `execute_async()` gains steps but maintains same signature and result type

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Asana duplicate API returns before subtasks ready | High | High | Polling with timeout (ADR-0111) |
| ProcessHolder not hydrated when needed | Medium | Medium | On-demand fetch via `unit._fetch_holders_async()` |
| Custom field not on target project | Low | Medium | Skip with warning, continue (FR-SEED-005) |
| Rep field empty | Low | Low | Leave assignee unset with warning (FR-ASSIGN-005) |
| Rate limiting during polling | Medium | Low | Respect poll interval, graceful timeout |
| Subtask wait timeout exceeded | Medium | Medium | Proceed anyway, subtasks will appear eventually |

## Observability

### Metrics
- `pipeline_conversion_total`: Counter for conversions (labels: rule_id, success)
- `pipeline_conversion_duration_seconds`: Histogram for full conversion time
- `pipeline_step_duration_seconds`: Histogram per step (labels: step_name)
- `pipeline_step_success_total`: Counter per step (labels: step_name, success)
- `subtask_wait_timeout_total`: Counter for wait timeouts

### Logging
```python
# Structured logging for each step
log.info("pipeline_duplicate",
    rule_id=self.id,
    template_gid=template_task.gid,
    new_task_gid=new_task.gid,
    duration_ms=elapsed,
)

log.info("pipeline_subtask_wait",
    task_gid=new_task.gid,
    expected_count=expected,
    actual_count=actual,
    ready=ready,
    duration_ms=elapsed,
)

log.warning("pipeline_step_failed",
    step="hierarchy_placement",
    error=str(e),
    continuing=True,
)
```

### Alerting
- Alert on `pipeline_conversion_total{success="false"}` rate > 5%
- Alert on `subtask_wait_timeout_total` rate > 10%
- Alert on `pipeline_conversion_duration_seconds` p99 > 5s

## Testing Strategy

### Unit Tests

**Scope**: Individual component behavior in isolation.

| Component | Test File | Key Cases |
|-----------|-----------|-----------|
| `duplicate_async()` | `tests/unit/clients/test_tasks_duplicate.py` | Success, raw mode, validation errors |
| `SubtaskWaiter` | `tests/unit/automation/test_waiter.py` | Immediate ready, timeout, count mismatch |
| `write_fields_async()` | `tests/unit/automation/test_seeding_write.py` | Full write, partial skip, empty fields |
| Rep resolution | `tests/unit/automation/test_rep_resolution.py` | Unit.rep, Business.rep fallback, empty |

**Mock Strategy**: Mock HTTP layer and client methods, test component logic.

### Integration Tests

**Scope**: Component interaction with real API responses (mocked at HTTP level).

| Test File | Key Scenarios |
|-----------|---------------|
| `tests/integration/test_pipeline_conversion.py` | Full conversion flow with all steps |
| `tests/integration/test_pipeline_degradation.py` | Graceful degradation when steps fail |

**Mock Strategy**: Use `respx` or similar to mock HTTP responses with realistic Asana payloads.

### Performance Tests

| Test | Target | Measurement |
|------|--------|-------------|
| Duplicate latency | <500ms | Time `duplicate_async()` call |
| Subtask wait latency | <2.0s | Time `wait_for_subtasks_async()` call |
| Field write latency | <300ms | Time `write_fields_async()` call |
| Full conversion | <3.0s | Time `execute_async()` call |

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| None | - | - | All questions resolved in Discovery |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Architect | Initial draft |
