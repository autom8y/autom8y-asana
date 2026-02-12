# Automation Pipelines

Automate repetitive Asana workflows with event-driven rules and scheduled batch operations.

## Overview

The automation system provides two complementary approaches to workflow automation:

1. **Event-driven rules**: React to entity changes in real-time (e.g., pipeline conversion)
2. **Batch workflows**: Process collections of entities on a schedule (e.g., conversation audits)

Both approaches use the same underlying architecture for configuration, field seeding, and template management.

### When to Use Each Approach

| Use Case | Approach | Why |
|----------|----------|-----|
| Convert sales to onboarding when closed | Event-driven rule | Immediate response to section change |
| Weekly CSV refresh for all contacts | Batch workflow | Scheduled enumeration of all targets |
| Set assignee based on rep field | Field seeding (both) | Automatic data propagation |
| Move stale tasks after N days | Time-based automation | Evaluate conditions on schedule |

### Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (your code)                                │
│  - Register rules: client.automation.register(rule)         │
│  - Run workflows: workflow.execute_async(params)            │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Automation Pipeline                                          │
│  - AutomationEngine: evaluates rules on save events         │
│  - WorkflowAction: batch processing protocol                │
│  - AutomationContext: execution tracking, loop prevention   │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ Support Subsystems                                           │
│  - FieldSeeder: cascade + carry-through field values        │
│  - TemplateDiscovery: find template tasks/sections          │
│  - SaveSession: batch entity writes with automation control │
└─────────────────────────────────────────────────────────────┘
```

## Event-Driven Rules

Rules execute automatically when entities are saved and match trigger conditions.

### Built-in Rule: Pipeline Conversion

The `PipelineConversionRule` automates process type transitions.

**Example: Sales to Onboarding**

```python
from autom8_asana.automation.workflows.pipeline_transition import (
    PipelineConversionRule,
)
from autom8_asana.models.business.process import ProcessType, ProcessSection

# Define conversion rule
rule = PipelineConversionRule(
    source_type=ProcessType.SALES,
    target_type=ProcessType.ONBOARDING,
    trigger_section=ProcessSection.CONVERTED,
)

# Register with client
client.automation.register(rule)
```

**What happens when triggered:**

1. Task moves to CONVERTED section in Sales project
2. Rule discovers Onboarding template task
3. New task created from template (with subtasks)
4. Fields seeded from Business/Unit hierarchy + source process
5. New task placed under ProcessHolder, positioned after source
6. Assignee set from rep field cascade
7. Comment added with conversion context

### Trigger Configuration

Rules define when they execute via `TriggerCondition`:

```python
from autom8_asana.automation.base import TriggerCondition
from autom8_asana.automation.events.types import EventType

trigger = TriggerCondition(
    entity_type="Process",
    event=EventType.SECTION_CHANGED,
    filters={
        "process_type": "sales",
        "section": "converted",
    },
)
```

**Available event types:**

- `SECTION_CHANGED`: Entity moved between sections
- `FIELD_UPDATED`: Custom field value changed
- `CREATED`: New entity created
- `COMPLETED`: Entity marked complete

### Pre-Transition Validation

Validate required fields exist before executing pipeline transitions.

```python
rule = PipelineConversionRule(
    source_type=ProcessType.SALES,
    target_type=ProcessType.ONBOARDING,
    trigger_section=ProcessSection.CONVERTED,
    required_source_fields=["Contact Phone", "Priority"],
    validate_mode="block",  # or "warn"
)
```

**Validation modes:**

- `block`: Return failure result if validation fails (transition does not execute)
- `warn`: Log warnings but proceed with transition (default)

The validation result is included in `AutomationResult.pre_validation` for audit trails.

### Loop Prevention

The automation context prevents circular trigger chains.

```python
# Context tracks depth and visited entities
context = AutomationContext(
    client=client,
    config=config,
    depth=0,
    visited=set(),
)

# Check before executing rule
if context.can_continue(entity.gid, rule.id):
    context.mark_visited(entity.gid, rule.id)
    result = await rule.execute_async(entity, context)
```

**Protection mechanisms:**

- **Max cascade depth** (default: 5): Prevents unbounded recursion
- **Visited tracking**: Prevents same (entity, rule) pair executing twice

Configure depth limit:

```python
config = AutomationConfig(
    enabled=True,
    max_cascade_depth=3,
)
```

## Field Seeding

Automatically populate new process fields from hierarchy and source data.

### Seeding Layers

Fields are collected from multiple sources with later layers overriding earlier:

```
1. Business cascade fields (company-level data)
       ↓ (overridden by)
2. Unit cascade fields (location/vertical data)
       ↓ (overridden by)
3. Process carry-through fields (copied from source)
       ↓ (overridden by)
4. Computed fields (e.g., Launch Date = today)
```

### Default Field Lists

```python
# Business cascade (empty by default - configure per pipeline)
DEFAULT_BUSINESS_CASCADE_FIELDS = []

# Unit cascade (common fields)
DEFAULT_UNIT_CASCADE_FIELDS = ["Vertical"]

# Process carry-through (task-specific)
DEFAULT_PROCESS_CARRY_THROUGH_FIELDS = ["Contact Phone", "Priority"]
```

### Custom Field Configuration

Override defaults for specific pipelines:

```python
from autom8_asana.automation.seeding import FieldSeeder

seeder = FieldSeeder(
    client,
    business_cascade_fields=["Company Name", "Office Phone"],
    unit_cascade_fields=["Vertical", "Location"],
    process_carry_through_fields=["Contact Phone", "Priority", "Notes"],
)

# Seed fields from hierarchy
fields = await seeder.seed_fields_async(
    business=business,
    unit=unit,
    source_process=sales_process,
)

# Write to target task
result = await seeder.write_fields_async(
    target_task_gid=new_task.gid,
    fields=fields,
)
```

### Field Name Mapping

Map field names when source and target projects use different names:

```python
# Configure via PipelineStage
stage = PipelineStage(
    project_gid="1234567890123",
    field_name_mapping={
        "Office Phone": "Business Phone",
        "Contact Phone": "Phone Number",
    },
)

# Or pass directly to write_fields_async
result = await seeder.write_fields_async(
    target_task_gid=new_task.gid,
    fields=fields,
    field_name_mapping={"Office Phone": "Business Phone"},
)
```

### Field Resolution

The seeder normalizes field values for correct API format:

| Field Type | Input | Output |
|------------|-------|--------|
| Enum | `"High"` | GID resolved via enum_options |
| Multi-enum | `["Option1", "Option2"]` | List of GIDs |
| People | List of user dicts | List of user GIDs |
| Text | `"Value"` | String value |
| Number | `123` | Numeric value |

Missing fields are skipped with warning logs. The seeder never fails the entire operation for missing fields.

## Template System

Discover and clone template tasks for new process creation.

### Template Section Discovery

Templates live in sections matching patterns: "template", "templates", "template tasks" (case-insensitive).

```python
from autom8_asana.automation.templates import TemplateDiscovery

discovery = TemplateDiscovery(client)

# Find template section automatically
section = await discovery.find_template_section_async("project_gid")

# Or find by exact name
section = await discovery.find_template_section_async(
    "project_gid",
    section_name="Template"
)
```

### Template Task Discovery

```python
# Find first task in template section
template = await discovery.find_template_task_async("project_gid")

# Find by specific name
template = await discovery.find_template_task_async(
    "project_gid",
    template_name="Onboarding Template"
)

# Find in specific section
template = await discovery.find_template_task_async(
    "project_gid",
    template_section="Template"
)
```

### Task Duplication

Clone templates with subtasks and notes:

```python
# Duplicate task from template
new_task = await client.tasks.duplicate_async(
    template_task.gid,
    name="New Task Name",
    include=["subtasks", "notes"],
)

# Add to target project
await client.tasks.add_to_project_async(
    new_task.gid,
    target_project_gid,
)

# Wait for subtasks to be created (async by Asana)
from autom8_asana.automation.waiter import SubtaskWaiter

waiter = SubtaskWaiter(client)
ready = await waiter.wait_for_subtasks_async(
    new_task.gid,
    expected_count=5,
    timeout=2.0,
)
```

### Task Name Generation

Generate names from template placeholders:

```python
# Template name: "Onboarding - [Business Name]"
# Result: "Onboarding - Acme Corporation"

# Supported placeholders (case-insensitive):
# - [Business Name] -> business.name
# - [Unit Name] -> unit.name
# - [Business Unit Name] -> unit.name
```

## Batch Workflows

Process collections of entities on a schedule or on demand.

### Workflow Protocol

All workflows implement `WorkflowAction`:

```python
from autom8_asana.automation.workflows.base import (
    WorkflowAction,
    WorkflowResult,
    WorkflowItemError,
)

class MyWorkflow(WorkflowAction):
    @property
    def workflow_id(self) -> str:
        return "my-workflow"

    async def validate_async(self) -> list[str]:
        """Pre-flight checks. Return errors or empty list."""
        errors = []
        if not self.is_configured():
            errors.append("Missing configuration")
        return errors

    async def execute_async(self, params: dict[str, Any]) -> WorkflowResult:
        """Main execution. Return structured result."""
        started_at = datetime.now(timezone.utc)

        # Enumerate targets
        items = await self._enumerate_items()

        # Process each item
        succeeded = 0
        failed = 0
        skipped = 0
        errors = []

        for item in items:
            try:
                result = await self._process_item(item)
                if result.success:
                    succeeded += 1
                else:
                    skipped += 1
            except Exception as e:
                failed += 1
                errors.append(WorkflowItemError(
                    item_id=item.gid,
                    error_type="processing_error",
                    message=str(e),
                    recoverable=True,
                ))

        completed_at = datetime.now(timezone.utc)

        return WorkflowResult(
            workflow_id=self.workflow_id,
            started_at=started_at,
            completed_at=completed_at,
            total=len(items),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            errors=errors,
        )
```

### Built-in Workflow: Conversation Audit

Weekly CSV refresh for ContactHolders.

```python
from autom8_asana.automation.workflows.conversation_audit import (
    ConversationAuditWorkflow,
)
from autom8_asana.clients.data.client import DataServiceClient
from autom8_asana.clients.attachments import AttachmentsClient

# Initialize workflow
workflow = ConversationAuditWorkflow(
    asana_client=client,
    data_client=DataServiceClient(base_url="..."),
    attachments_client=AttachmentsClient(client),
)

# Validate
errors = await workflow.validate_async()
if errors:
    print(f"Validation failed: {errors}")

# Execute
result = await workflow.execute_async({
    "max_concurrency": 5,
    "date_range_days": 30,
    "attachment_pattern": "conversations_*.csv",
})

print(f"Total: {result.total}")
print(f"Succeeded: {result.succeeded}")
print(f"Failed: {result.failed}")
print(f"Duration: {result.duration_seconds:.2f}s")
```

**Workflow steps:**

1. Enumerate active ContactHolder tasks
2. For each holder (with concurrency control):
   - Resolve parent Business to get office_phone
   - Fetch 30-day conversation CSV from autom8_data
   - Upload new CSV attachment
   - Delete old matching attachments
3. Return WorkflowResult with per-item tracking

### Built-in Workflow: Pipeline Transition

Batch-process pipeline transitions for tasks in terminal sections.

```python
from autom8_asana.automation.workflows.pipeline_transition import (
    PipelineTransitionWorkflow,
)
from autom8_asana.lifecycle.config import LifecycleConfig

# Load lifecycle config
config = LifecycleConfig(Path("config/lifecycle_stages.yaml"))

# Initialize workflow
workflow = PipelineTransitionWorkflow(client, config)

# Execute
result = await workflow.execute_async({
    "pipeline_project_gids": ["1200944186565610"],
    "max_concurrency": 3,
    "converted_section": "CONVERTED",
    "dnc_section": "DID NOT CONVERT",
})
```

**Workflow steps:**

1. Enumerate processes in CONVERTED/DID NOT CONVERT sections
2. For each process:
   - Determine outcome (converted/did_not_convert)
   - Route to LifecycleEngine.handle_transition_async()
3. Return WorkflowResult with per-item success/failure tracking

The workflow is idempotent. Re-running will re-process tasks still in terminal sections (safe due to duplicate detection).

### Concurrency Control

Workflows use semaphores to limit concurrent processing:

```python
import asyncio

semaphore = asyncio.Semaphore(max_concurrency)

async def process_one(item):
    async with semaphore:
        return await self._process_item(item)

results = await asyncio.gather(*[process_one(item) for item in items])
```

This prevents overwhelming the Asana API or external services.

### Error Isolation

Each item is processed independently. One failure does not prevent processing other items.

```python
# Gather with exception handling
results = await asyncio.gather(*tasks, return_exceptions=True)

# Classify results
for result in results:
    if isinstance(result, Exception):
        failed += 1
        errors.append(WorkflowItemError(
            item_id="unknown",
            error_type="workflow_exception",
            message=str(result),
            recoverable=True,
        ))
    elif result.success:
        succeeded += 1
    else:
        skipped += 1
```

## Pipeline Configuration

Configure pipeline stages with project GIDs, sections, and field mappings.

### Basic Configuration

```python
from autom8_asana.automation.config import AutomationConfig, PipelineStage

config = AutomationConfig(
    enabled=True,
    max_cascade_depth=5,
    pipeline_stages={
        "onboarding": PipelineStage(
            project_gid="1234567890123",
            template_section="Template",
            target_section="Opportunity",
        ),
    },
)
```

### Advanced Configuration

```python
stage = PipelineStage(
    project_gid="1234567890123",
    template_section="Template",
    target_section="Opportunity",
    due_date_offset_days=7,  # Due in 7 days
    assignee_gid="123456789",  # Fixed assignee
    business_cascade_fields=["Company Name", "Office Phone"],
    unit_cascade_fields=["Vertical", "Location"],
    process_carry_through_fields=["Contact Phone", "Priority"],
    field_name_mapping={
        "Office Phone": "Business Phone",
    },
)

config = AutomationConfig(
    enabled=True,
    pipeline_stages={"onboarding": stage},
)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `project_gid` | str | Required | Target project GID |
| `template_section` | str | "Template" | Section containing templates |
| `target_section` | str | "Opportunity" | Section for new tasks |
| `due_date_offset_days` | int | None | Days from today for due date |
| `assignee_gid` | str | None | Fixed assignee (overrides rep cascade) |
| `business_cascade_fields` | list[str] | None | Override default Business fields |
| `unit_cascade_fields` | list[str] | None | Override default Unit fields |
| `process_carry_through_fields` | list[str] | None | Override default Process fields |
| `field_name_mapping` | dict | {} | Map source to target field names |

## Integration with Lifecycle Engine

Pipeline automation integrates with the lifecycle engine for outcome-driven transitions.

### Lifecycle Stages

Define stages in YAML config:

```yaml
# config/lifecycle_stages.yaml
stages:
  - name: sales
    process_type: sales
    terminal_sections:
      - name: CONVERTED
        outcome: converted
      - name: DID NOT CONVERT
        outcome: did_not_convert

  - name: onboarding
    process_type: onboarding
    terminal_sections:
      - name: COMPLETE
        outcome: success
```

### Outcome-Driven Rules

Link pipeline stages via outcomes:

```python
from autom8_asana.lifecycle.config import LifecycleConfig
from autom8_asana.lifecycle.engine import LifecycleEngine

# Load config
config = LifecycleConfig(Path("config/lifecycle_stages.yaml"))

# Initialize engine
engine = LifecycleEngine(client, config)

# Handle transition
result = await engine.handle_transition_async(
    process=sales_process,
    outcome="converted",
)
```

The engine:

1. Validates process is in terminal section for outcome
2. Determines next stage from lifecycle config
3. Executes pipeline conversion rule
4. Returns structured result with created entities

### Webhook Integration

Connect webhooks to lifecycle events:

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhooks/asana")
async def handle_webhook(request: Request):
    payload = await request.json()

    events = payload.get("events", [])
    for event in events:
        if event["action"] == "changed":
            # Check if section changed
            changes = event.get("change", {})
            if "section" in changes:
                # Process with lifecycle engine
                result = await engine.handle_transition_async(
                    process=Process.model_validate(event["resource"]),
                    outcome=determine_outcome(changes["section"]),
                )
```

See the webhooks guide for complete webhook setup.

## Deployment Patterns

### Event-Driven Rules (Production)

Register rules at application startup:

```python
# app/startup.py
from autom8_asana.client import AsanaClient
from autom8_asana.automation.workflows.pipeline_transition import (
    PipelineConversionRule,
)

client = AsanaClient.from_env()

# Register conversion rules
client.automation.register(
    PipelineConversionRule(
        source_type=ProcessType.SALES,
        target_type=ProcessType.ONBOARDING,
        trigger_section=ProcessSection.CONVERTED,
    )
)
```

Rules execute automatically when SaveSession commits trigger events.

### Batch Workflows (Cron)

Schedule workflows with cron:

```bash
# Daily at 2 AM UTC
0 2 * * * cd /app && python -m autom8_asana.workflows.run conversation-audit
```

```python
# autom8_asana/workflows/run.py
import asyncio
import sys
from autom8_asana.client import AsanaClient
from autom8_asana.automation.workflows.conversation_audit import (
    ConversationAuditWorkflow,
)

async def main():
    workflow_name = sys.argv[1]

    if workflow_name == "conversation-audit":
        workflow = ConversationAuditWorkflow(...)
        result = await workflow.execute_async({})
        print(f"Completed: {result.succeeded}/{result.total}")

asyncio.run(main())
```

### Feature Flags

Control workflow execution with environment variables:

```bash
# Enable/disable workflows
export AUTOM8_AUDIT_ENABLED=true
export AUTOM8_PIPELINE_TRANSITION_ENABLED=true

# Configure behavior
export AUTOM8_MAX_CONCURRENCY=5
export AUTOM8_DATE_RANGE_DAYS=30
```

```python
import os

enabled = os.environ.get("AUTOM8_AUDIT_ENABLED", "true").lower() != "false"

if enabled:
    result = await workflow.execute_async(params)
else:
    print("Workflow disabled via environment variable")
```

## Monitoring and Observability

### Structured Logging

All automation events use structured logging:

```python
from autom8y_log import get_logger

logger = get_logger(__name__)

logger.info(
    "pipeline_conversion_started",
    source_gid=source_process.gid,
    target_type=target_type.value,
)

logger.warning(
    "field_seeding_skipped",
    field_name="Office Phone",
    reason="not_found_on_target",
)

logger.error(
    "pipeline_conversion_failed",
    source_gid=source_process.gid,
    error=str(e),
)
```

### Result Tracking

`WorkflowResult` provides structured outcome data:

```python
result = await workflow.execute_async(params)

# Aggregate metrics
print(f"Total: {result.total}")
print(f"Succeeded: {result.succeeded}")
print(f"Failed: {result.failed}")
print(f"Skipped: {result.skipped}")
print(f"Duration: {result.duration_seconds:.2f}s")
print(f"Failure rate: {result.failure_rate:.2%}")

# Per-item errors
for error in result.errors:
    print(f"Item {error.item_id}: {error.error_type} - {error.message}")
    print(f"  Recoverable: {error.recoverable}")
```

### Automation Result Tracking

Event-driven rules return `AutomationResult`:

```python
from autom8_asana.persistence.models import AutomationResult

result = await rule.execute_async(entity, context)

# Result details
print(f"Success: {result.success}")
print(f"Rule: {result.rule_name}")
print(f"Actions: {result.actions_executed}")
print(f"Created: {result.entities_created}")
print(f"Updated: {result.entities_updated}")
print(f"Duration: {result.execution_time_ms:.2f}ms")

# Validation results
if result.pre_validation:
    print(f"Pre-validation: {result.pre_validation.valid}")
    print(f"Errors: {result.pre_validation.errors}")
if result.post_validation:
    print(f"Post-validation warnings: {result.post_validation.warnings}")
```

## Troubleshooting

### Rules Not Triggering

**Symptoms:** Pipeline conversion does not execute when expected.

**Checklist:**

1. Verify automation enabled: `config.enabled == True`
2. Check rule registration: Rule added to client.automation
3. Validate trigger conditions match entity state
4. Review loop prevention: Check depth and visited set
5. Enable debug logging: `logging.getLogger("autom8_asana.automation").setLevel(logging.DEBUG)`

### Field Seeding Failures

**Symptoms:** Fields not populated on new tasks.

**Solutions:**

1. Check field exists on target project
2. Verify field name mapping if names differ between projects
3. Review field value normalization (enums need GID resolution)
4. Enable seeding logs: `logging.getLogger("autom8_asana.automation.seeding").setLevel(logging.DEBUG)`

### Template Not Found

**Symptoms:** "No template found in project" error.

**Solutions:**

1. Verify template section exists with correct name pattern
2. Check template task exists in template section
3. Review section name configuration in PipelineStage
4. Use explicit section name instead of pattern matching

### Workflow Performance Issues

**Symptoms:** Batch workflows take too long or timeout.

**Solutions:**

1. Reduce `max_concurrency` to avoid API rate limits
2. Add timeouts to external service calls
3. Filter enumeration to reduce total items
4. Process in smaller batches with multiple workflow runs

## Related Guides

- **Business Models** (`business-models.md`): Entity hierarchy and relationships
- **Lifecycle Engine** (`lifecycle-engine.md`): Outcome-driven process transitions
- **Webhooks** (`webhooks.md`): Real-time event integration
- **Field Resolution** (`entity-write-api.md`): Custom field GID resolution
- **Business Seeder** (`GUIDE-businessseeder-v2.md`): Hierarchy creation with deduplication

## Example: Complete Pipeline Setup

```python
from pathlib import Path
from autom8_asana.client import AsanaClient
from autom8_asana.automation.config import AutomationConfig, PipelineStage
from autom8_asana.automation.workflows.pipeline_transition import (
    PipelineConversionRule,
)
from autom8_asana.models.business.process import ProcessType, ProcessSection

# Initialize client
client = AsanaClient.from_env()

# Configure automation
config = AutomationConfig(
    enabled=True,
    max_cascade_depth=5,
    pipeline_stages={
        "onboarding": PipelineStage(
            project_gid="1234567890123",
            template_section="Template",
            target_section="Opportunity",
            due_date_offset_days=7,
            business_cascade_fields=["Company Name", "Office Phone"],
            unit_cascade_fields=["Vertical", "Location"],
            process_carry_through_fields=["Contact Phone", "Priority"],
            field_name_mapping={
                "Office Phone": "Business Phone",
            },
        ),
    },
)

# Register conversion rule
rule = PipelineConversionRule(
    source_type=ProcessType.SALES,
    target_type=ProcessType.ONBOARDING,
    trigger_section=ProcessSection.CONVERTED,
    required_source_fields=["Contact Phone", "Priority"],
    validate_mode="warn",
)
client.automation.register(rule)

# Now when a Sales process moves to CONVERTED:
# 1. Rule validates Contact Phone and Priority exist
# 2. Template discovered in Onboarding project
# 3. New task created from template
# 4. Fields seeded from hierarchy + source process
# 5. Task placed in Opportunity section
# 6. Due date set to 7 days from today
# 7. Assignee set from rep cascade
# 8. All actions logged for audit trail
```
