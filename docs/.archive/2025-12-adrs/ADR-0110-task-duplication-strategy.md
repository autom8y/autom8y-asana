# ADR-0110: Task Duplication vs Creation Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect (Claude)
- **Date**: 2025-12-18
- **Deciders**: Engineering Team
- **Related**: [PRD-PIPELINE-AUTOMATION-ENHANCEMENT](../requirements/PRD-PIPELINE-AUTOMATION-ENHANCEMENT.md), [TDD-PIPELINE-AUTOMATION-ENHANCEMENT](../design/TDD-PIPELINE-AUTOMATION-ENHANCEMENT.md)

## Context

When the Pipeline Automation Layer converts a Process (e.g., Sales to Onboarding), it must create a new Process in the target project. The current implementation uses `create_async()` to create a new task and manually copies over template properties like notes.

However, template tasks often have subtasks (checklist items) that represent the standard workflow for that ProcessType. For example, an "Onboarding Template" might have 5 subtasks:
1. Welcome call
2. Account setup
3. Training session
4. First order placed
5. Follow-up survey

These subtasks must appear on every new Onboarding Process. The question is: how should we create the new Process with its subtasks?

**Forces at play**:
- Subtask duplication is labor-intensive if done manually via multiple API calls
- Template subtasks may have their own subtasks (nested hierarchy)
- Template structure changes should automatically apply to future conversions
- Conversion should complete quickly (<3s total)
- API rate limits apply to the Asana API

## Decision

**Use `duplicate_async()` (wrapping Asana's `POST /tasks/{gid}/duplicate`) instead of `create_async()` for new Process creation.**

Specifically:
```python
new_task = await client.tasks.duplicate_async(
    template_gid,
    name=source_process.name,
    include=["subtasks", "notes"],
)
```

## Rationale

Duplication is the right approach because:

1. **Atomic Operation**: Asana's duplicate API creates the parent task and all subtasks in one request, reducing complexity and API calls.

2. **Hierarchy Preservation**: Nested subtasks and subtask properties (notes, assignees, dates) are automatically copied without additional logic.

3. **Template Evolution**: When the template changes (new subtasks added, existing ones modified), future conversions automatically get the updated structure.

4. **Single API Call**: One request triggers the entire duplication, vs N+1 calls for manual creation (1 parent + N subtasks).

5. **Asana-Native Pattern**: Uses the same mechanism Asana users employ when duplicating tasks manually, ensuring consistent behavior.

## Alternatives Considered

### Alternative 1: create_async() with Manual Subtask Creation

- **Description**: Use `create_async()` for the parent task, then iterate through template subtasks and create each one individually.
- **Pros**:
  - Full control over which subtasks to include
  - Can modify subtask properties during creation
- **Cons**:
  - N+1 API calls (1 parent + N subtasks)
  - Complex code to handle nested subtasks
  - Race conditions if subtask creation is parallelized
  - Doesn't capture template changes automatically
- **Why not chosen**: Too many API calls, complex implementation, doesn't scale with template complexity.

### Alternative 2: create_async() with Bulk Insert via Batch API

- **Description**: Use the Batch API to create parent and all subtasks in a single request.
- **Pros**:
  - Single HTTP request
  - Full control over properties
- **Cons**:
  - Batch API has complexity around ordering and dependencies
  - Still requires fetching template subtasks first
  - Doesn't handle nested subtasks elegantly
  - More code to build the batch request
- **Why not chosen**: Adds complexity without benefit over native duplication.

### Alternative 3: No Subtask Copying

- **Description**: Create only the parent task, expecting users to manually add subtasks.
- **Pros**:
  - Simplest implementation
  - No subtask wait complexity
- **Cons**:
  - Defeats the purpose of templates
  - Increases manual work for operations team
  - Doesn't match legacy system behavior
- **Why not chosen**: Violates core requirement of legacy feature parity (PRD success criteria: "Subtask duplication rate = 100%").

## Consequences

### Positive
- **Simpler Code**: One method call replaces complex subtask iteration logic.
- **Fewer API Calls**: Single request vs potentially 10+ calls for complex templates.
- **Automatic Updates**: Template changes propagate to future conversions without code changes.
- **Consistent Behavior**: Matches what users experience when duplicating in Asana UI.

### Negative
- **Asynchronous Subtask Creation**: Asana creates subtasks asynchronously after the duplicate request returns. We must wait for subtasks before subsequent operations (addressed in ADR-0111).
- **Limited Control**: Cannot selectively include/exclude specific subtasks in one duplication (all or nothing per `include` flag).
- **Potential for Large Duplication**: Templates with many subtasks take longer; timeout may be reached.

### Neutral
- **New API Method**: Requires implementing `duplicate_async()` in TasksClient (straightforward wrapper).
- **Include Parameter Flexibility**: The `include` array can be expanded (attachments, dates, etc.) if needed later.

## Compliance

- [ ] `duplicate_async()` is the only method used for Process creation in PipelineConversionRule
- [ ] Code review checklist: "If creating Process from template, use duplicate_async(), not create_async()"
- [ ] Unit test verifies `include=["subtasks", "notes"]` is passed
