# Lifecycle Engine Guide

This guide explains how entities move through lifecycle stages and how to trigger transitions programmatically or via webhooks.

## Overview

The Lifecycle Engine automates pipeline state transitions for business processes. When a process moves to a terminal section (CONVERTED or DID NOT CONVERT), the engine creates new entities, updates related records, wires dependencies, and executes configured actions.

### What the Engine Does

The engine orchestrates four phases when a process transitions to a new lifecycle stage:

1. **CREATE**: Creates a new process entity from a template in the target stage project
2. **CONFIGURE**: Updates cascading sections on related entities, auto-completes the source process, seeds custom fields
3. **ACTIONS**: Executes init actions like creating DNA plays, asset edits, or requesting videography
4. **WIRE**: Wires dependency relationships between the new process and related entities

### When to Use

Use the Lifecycle Engine for:

- **Pipeline automation**: Move deals through sales stages (Outreach, Sales, Onboarding, Implementation)
- **Account management**: Transition units through retention, reactivation, and account error flows
- **Workflow orchestration**: Trigger cascading entity creation based on stage transitions
- **State management**: Maintain consistent state across Business, Unit, Offer, and Process hierarchies

Do not use the Lifecycle Engine for:

- Ad-hoc task creation (use entity write endpoints instead)
- Real-time event processing (designed for webhook-triggered batch processing)
- Complex branching logic (keep stage transitions linear with DNC fallbacks)

---

## Lifecycle Stages

Stages are configured in `config/lifecycle_stages.yaml`. Each stage defines a project, transitions, cascading sections, and init actions.

### Primary Pipeline Stages

Stages 1-4 represent the core customer acquisition pipeline:

| Stage | Pipeline # | Project | Purpose |
|-------|------------|---------|---------|
| Outreach | 1 | Outreach Project | Initial contact, lead qualification |
| Sales | 2 | Sales Project | Active deal pursuit |
| Onboarding | 3 | Onboarding Project | Customer activation |
| Implementation | 4 | Implementation Project | Launch and integration |

After Implementation, the pipeline reaches a terminal state. Units continue through Month 1, Retention, and other stages not covered here.

### Stage Configuration

Each stage includes:

- **project_gid**: Target Asana project where new processes are created
- **pipeline_stage**: Numeric stage identifier (1-10)
- **template_section**: Section name containing template tasks to duplicate
- **target_section**: Section where new processes are placed
- **transitions**: Routing for CONVERTED and DID NOT CONVERT outcomes
- **cascading_sections**: Section names to set on Offer, Unit, and Business entities
- **dnc_action**: Routing behavior for DID NOT CONVERT transitions (create_new, reopen, deferred)
- **init_actions**: Actions to execute after process creation

Example stage configuration:

```yaml
sales:
  project_gid: "1200944186565610"
  pipeline_stage: 2
  template_section: "TEMPLATE"
  target_section: "OPPORTUNITY"
  due_date_offset_days: 0
  dnc_action: create_new

  transitions:
    converted: onboarding
    did_not_convert: outreach
    auto_complete_prior: true

  cascading_sections:
    offer: "Sales Process"
    unit: "Next Steps"
    business: "OPPORTUNITY"

  init_actions:
    - type: create_comment
```

### DNC Routing Actions

When a process moves to DID NOT CONVERT, the engine routes based on `dnc_action`:

- **create_new**: Standard creation flow (same as CONVERTED). Used by Sales and Implementation stages.
- **reopen**: Find and reopen an existing process in the target stage. Used by Onboarding DNC to reopen Sales.
- **deferred**: Log the event and return without action. Used by Outreach self-loop.

---

## Transitions

Transitions occur when a process task moves to a terminal section in Asana. The engine detects the section change and routes the process through the configured stages.

### Triggering Transitions

Three methods trigger lifecycle transitions:

1. **Webhook (recommended)**: Asana Rules send webhook POST to `/api/v1/webhooks/asana` when tasks move to CONVERTED or DID NOT CONVERT sections.
2. **Workflow batch processing**: PipelineTransitionWorkflow scans pipeline projects and processes all tasks in terminal sections.
3. **Direct API call**: POST to `/api/v1/lifecycle/transition` with process GID and outcome.

### Transition Flow

The engine determines the target stage by consulting the YAML configuration:

```
Source Process in "CONVERTED" section
  -> LifecycleEngine.handle_transition_async(process, outcome="converted")
  -> Resolve source stage (Sales)
  -> Resolve target stage (Onboarding)
  -> Run 4-phase pipeline
  -> Return AutomationResult
```

### Pre-Transition Validation

Stages can define validation rules that check required fields before allowing transitions:

```yaml
onboarding:
  validation:
    pre_transition:
      required_fields: ["Contact Phone"]
      mode: warn  # or "block"
```

Validation modes:

- **warn**: Log missing fields as warnings but allow transition
- **block**: Return error and prevent transition if required fields are missing

### Auto-Completion

When `auto_complete_prior: true` is set in a transition, the engine marks the source process as complete after creating the target process. This keeps projects tidy by preventing duplicate active processes.

Example: Sales to Onboarding transition auto-completes the Sales process.

---

## REST API

The Lifecycle Engine exposes endpoints for webhook ingestion and direct transition requests.

### Webhook Endpoint

Receive Asana Rule webhooks when tasks move to terminal sections.

```http
POST /api/v1/webhooks/asana
Content-Type: application/json

{
  "task_gid": "1234567890123",
  "task_name": "Business Name - Sales",
  "section_name": "CONVERTED",
  "project_gid": "1200944186565610"
}
```

**Response**:

```json
{
  "accepted": true,
  "message": "Dispatched: true"
}
```

The webhook handler extracts the outcome from `section_name` (CONVERTED or DID NOT CONVERT), fetches the full process entity, and routes it to the LifecycleEngine.

### Direct Transition Endpoint

Trigger a transition programmatically.

```http
POST /api/v1/lifecycle/transition
Content-Type: application/json

{
  "process_gid": "1234567890123",
  "outcome": "converted"
}
```

**Parameters**:

- `process_gid`: Asana task GID of the process
- `outcome`: "converted" or "did_not_convert"

**Response**:

```json
{
  "success": true,
  "rule_id": "lifecycle_sales_to_onboarding",
  "actions_executed": ["create_process", "cascade_sections", "auto_complete_source"],
  "entities_created": ["1234567890124"],
  "entities_updated": ["1234567890100", "1234567890101"],
  "execution_time_ms": 1234.5
}
```

---

## SDK Usage

Use the LifecycleEngine programmatically for batch processing or custom workflows.

### Basic Setup

```python
from pathlib import Path
from autom8_asana.client import AsanaClient
from autom8_asana.lifecycle.config import LifecycleConfig, load_config
from autom8_asana.lifecycle.engine import LifecycleEngine
from autom8_asana.models.business.process import Process

# Initialize
client = AsanaClient.from_environment()
config = load_config()  # Loads config/lifecycle_stages.yaml
engine = LifecycleEngine(client, config)
```

### Trigger a Transition

```python
# Fetch the process that moved to CONVERTED
process_gid = "1234567890123"
task_data = await client.tasks.get_async(process_gid)
process = Process.model_validate(task_data.model_dump())

# Handle transition
result = await engine.handle_transition_async(
    source_process=process,
    outcome="converted"
)

print(f"Success: {result.success}")
print(f"Actions: {result.actions_executed}")
print(f"Created: {result.entities_created}")
print(f"Updated: {result.entities_updated}")
```

### Batch Processing with PipelineTransitionWorkflow

Process all tasks in terminal sections across all pipeline projects:

```python
from autom8_asana.automation.workflows.pipeline_transition import (
    PipelineTransitionWorkflow,
)

workflow = PipelineTransitionWorkflow(client, config)

# Validate configuration
validation_errors = await workflow.validate_async()
if validation_errors:
    raise ValueError(f"Validation failed: {validation_errors}")

# Execute workflow
result = await workflow.execute_async({
    "pipeline_project_gids": ["1200944186565610"],  # Optional filter
    "max_concurrency": 3,
    "converted_section": "CONVERTED",
    "dnc_section": "DID NOT CONVERT",
})

print(f"Processed: {result.items_processed}")
print(f"Succeeded: {result.items_succeeded}")
print(f"Errors: {len(result.errors)}")
```

### Custom Service Injection

Override default services for testing or custom behavior:

```python
from autom8_asana.lifecycle.creation import EntityCreationService

class CustomCreationService(EntityCreationService):
    async def create_process_async(self, stage_config, ctx, source_process):
        # Custom logic here
        return await super().create_process_async(stage_config, ctx, source_process)

engine = LifecycleEngine(
    client,
    config,
    creation_service=CustomCreationService(client, config),
)
```

---

## Events and Hooks

The Lifecycle Engine emits structured log events at key points in the transition lifecycle. These events are suitable for observability, auditing, and triggering downstream workflows.

### Key Events

**lifecycle_transition_start**

Emitted when a transition begins:

```json
{
  "event": "lifecycle_transition_start",
  "source_stage": "sales",
  "target_stage": "onboarding",
  "outcome": "converted",
  "source_gid": "1234567890123"
}
```

**lifecycle_transition_complete**

Emitted when a transition succeeds:

```json
{
  "event": "lifecycle_transition_complete",
  "source_stage": "sales",
  "target_stage": "onboarding",
  "outcome": "converted",
  "actions": ["create_process", "cascade_sections", "auto_complete_source"],
  "entities_created": ["1234567890124"],
  "warnings": [],
  "duration_ms": 1234.5
}
```

**lifecycle_phase_warning**

Emitted for soft failures (non-blocking):

```json
{
  "event": "lifecycle_phase_warning",
  "warning": "Cascade sections failed: 404 Not Found"
}
```

**lifecycle_transition_error**

Emitted for hard failures:

```json
{
  "event": "lifecycle_transition_error",
  "source_gid": "1234567890123",
  "outcome": "converted",
  "error": "Process creation failed: Template not found"
}
```

### Init Action Events

Each init action type emits its own events:

**lifecycle_comment_failed** (soft failure)

**lifecycle_play_created**

**lifecycle_entity_created**

**lifecycle_products_check_matched**

### Observability

All events use `autom8y-log` structured logging. Configure a JSON log handler to capture events for analysis:

```python
import logging
from autom8y_log import setup_logging

setup_logging(level=logging.INFO, format="json")
```

Events include:

- **Trace context**: Request IDs for distributed tracing
- **Entity GIDs**: All created and updated entity identifiers
- **Timing**: Execution time for performance monitoring
- **Warnings**: Soft failures that did not block the transition

---

## Error Handling

The Lifecycle Engine uses a fail-forward error model. Soft failures produce warnings but allow the transition to complete. Hard failures block the transition and return an error.

### Soft Failures (Warnings)

These failures log warnings but do not prevent success:

- **Cascade sections failed**: Section update errors on related entities
- **Init action failed**: Individual action failures (comment creation, products check)
- **Dependency wiring failed**: Wiring errors when linking entities
- **Auto-completion failed**: Errors when marking source process complete

Warnings appear in the AutomationResult:

```python
result = await engine.handle_transition_async(process, "converted")
if result.warnings:
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

### Hard Failures (Errors)

These failures set `success=False` and populate the `error` field:

- **Process creation failed**: Template not found or blank task creation failed
- **Unknown stage**: Source stage not defined in lifecycle_stages.yaml
- **Validation blocked**: Pre-transition validation failed with mode=block
- **Unhandled exceptions**: Unexpected errors during transition processing

Example error handling:

```python
result = await engine.handle_transition_async(process, "converted")
if not result.success:
    logger.error(f"Transition failed: {result.error}")
    raise TransitionError(result.error)
```

### Duplicate Detection

The engine detects duplicate processes before creating new ones. If a process with the same ProcessType and Unit already exists in the target stage, the engine returns the existing GID:

```python
result = await engine.handle_transition_async(process, "converted")
if result.was_reopened:
    print(f"Reused existing process: {result.entity_gid}")
```

### Validation Errors

Pre-transition validation checks required fields. When mode is "block", missing fields prevent the transition:

```python
# In lifecycle_stages.yaml:
# validation:
#   pre_transition:
#     required_fields: ["Contact Phone"]
#     mode: block

result = await engine.handle_transition_async(process, "converted")
if not result.success:
    # Error: "Pre-validation failed: ['Contact Phone']"
    print(result.error)
```

### Terminal State Handling

When a stage has no target (e.g., Implementation CONVERTED for stages 1-4), the engine enters terminal state handling:

```python
# transitions:
#   converted: null  # Terminal

result = await engine.handle_transition_async(process, "converted")
# Result contains:
#   actions_executed: ["terminal", "auto_complete_source"]
#   entities_created: []  # No new entities
```

### Recovery

The engine is idempotent. Re-processing a task in a terminal section is safe:

- Duplicate detection prevents creating multiple processes for the same Unit
- Auto-completion is idempotent (already-complete tasks are skipped)
- Cascading sections overwrite previous values (last-write-wins)

To recover from a partial failure, move the source process back to the terminal section and trigger the workflow again.

---

## Configuration Reference

### Field Seeding

The engine auto-cascades custom fields from the source process to the newly created process. Field matching uses exact field name matching with enum resolution.

Exclude fields from seeding:

```yaml
onboarding:
  seeding:
    exclude_fields: ["Status", "Priority"]
```

Add computed fields:

```yaml
onboarding:
  seeding:
    computed_fields:
      "Launch Date": "today"
      "Status": "New"
```

Computed field values:

- `"today"`: Current date in ISO format (YYYY-MM-DD)
- Static strings: Any other value is set as-is

### Init Actions

Available init action types:

**create_comment**

Creates a pipeline conversion comment with source link and business name.

```yaml
init_actions:
  - type: create_comment
```

**play_creation**

Creates a DNA play task with reopen-or-create support.

```yaml
init_actions:
  - type: play_creation
    play_type: backend_onboard_a_business
    project_gid: "1207507299545000"
    holder_type: dna_holder
    reopen_if_completed_within_days: 90
    wire_as_dependency: true
```

**entity_creation**

Creates a related entity (AssetEdit, etc.).

```yaml
init_actions:
  - type: entity_creation
    entity_type: asset_edit
    project_gid: "1203992664400125"
    holder_type: asset_edit_holder
    wire_as_dependency: true
```

**products_check**

Conditionally creates an entity if the products field matches a pattern.

```yaml
init_actions:
  - type: products_check
    condition: "video*"
    action: request_source_videographer
    project_gid: "1207984018149338"
    holder_type: videography_holder
```

### Self-Loop Configuration

Stages can loop back to themselves with iteration limits and delay schedules:

```yaml
reactivation:
  self_loop:
    max_iterations: 5
    delay_schedule: [90, 180, 360]
```

After 5 iterations, the stage becomes terminal.

### Dependency Wiring

Default wiring rules apply to all pipeline stages:

```yaml
dependency_wiring:
  pipeline_default:
    dependents:
      - entity_type: unit
      - entity_type: offer_holder
    dependencies:
      - source: dna_holder
        filter: open_plays
```

This wires the new process as:

- Dependent on: Open DNA plays (BlockedBy relationship)
- Dependency of: Unit task and OfferHolder task (Blocking relationship)

---

## Best Practices

### Stage Design

- Keep transitions linear with fallback DNC routing
- Use validation rules to enforce data quality at stage boundaries
- Set auto_complete_prior: true to prevent duplicate active processes
- Define clear terminal states (null transitions)

### Field Management

- Use auto-cascade seeding to propagate critical fields across stages
- Exclude volatile fields (Status, Priority) from seeding
- Use computed fields for stage-specific defaults (Launch Date: today)

### Init Actions

- Order actions from lowest to highest dependency (comments first, wiring last)
- Use wire_as_dependency: true for entities that should block the process
- Soft-fail by default (comment failures do not block transitions)

### Error Handling

- Monitor lifecycle_phase_warning events for degraded automation
- Alert on lifecycle_transition_error events for hard failures
- Use validation mode: block sparingly (only for critical fields)

### Performance

- Batch process transitions using PipelineTransitionWorkflow
- Set max_concurrency based on API rate limits (default: 3)
- Use webhook triggers for real-time processing (more efficient than polling)

### Testing

- Inject mock services for unit tests
- Use validation mode: warn during development
- Test DNC routing for all stages (create_new, reopen, deferred)
- Verify auto-completion behavior with stage-specific tests

---

## Related Documentation

- [Entity Resolution Guide](./entity-resolution.md) - Understanding ResolutionContext
- [Save Session Guide](./save-session.md) - Batch entity updates
- [Entity Write Guide](./entity-write.md) - Direct entity creation endpoints
- [Workflows Guide](./workflows.md) - Batch processing patterns
