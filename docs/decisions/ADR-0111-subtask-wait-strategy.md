# ADR-0111: Subtask Wait Strategy

## Metadata
- **Status**: Accepted
- **Author**: Architect (Claude)
- **Date**: 2025-12-18
- **Deciders**: Engineering Team
- **Related**: [PRD-PIPELINE-AUTOMATION-ENHANCEMENT](../requirements/PRD-PIPELINE-AUTOMATION-ENHANCEMENT.md), [TDD-PIPELINE-AUTOMATION-ENHANCEMENT](../design/TDD-PIPELINE-AUTOMATION-ENHANCEMENT.md), [ADR-0110](ADR-0110-task-duplication-strategy.md)

## Context

Per ADR-0110, we use Asana's `POST /tasks/{gid}/duplicate` endpoint to create new Processes with their subtasks. However, Asana's duplicate operation is **asynchronous**: the API returns immediately with the new task's GID, but subtask creation happens in the background.

From [Asana API documentation](https://developers.asana.com/reference/duplicatetask):
> "Duplicating a task is asynchronous. [...] The new_task property contains the GID of the duplicated task, but some fields like subtasks may not be immediately populated."

This creates a race condition: if we immediately proceed to field seeding or hierarchy placement, the subtasks may not exist yet. We need a strategy to wait for subtasks before continuing.

**Forces at play**:
- Subtasks must exist before the conversion is "complete" for users
- Some subsequent operations (like comments) are fine without subtasks
- Conversion should complete within 3 seconds total
- Typical templates have 1-10 subtasks
- Asana subtask creation typically completes within 1-2 seconds
- We want to avoid unnecessary delays

## Decision

**Use polling with a configurable timeout to wait for subtask creation.**

Specifically:
```python
class SubtaskWaiter:
    async def wait_for_subtasks_async(
        self,
        task_gid: str,
        expected_count: int,
        *,
        timeout: float = 2.0,      # Default 2 seconds
        poll_interval: float = 0.2, # Check every 200ms
    ) -> bool:
        """Poll until subtask count matches expected or timeout."""
```

Algorithm:
1. Before duplication: Get template subtask count via `subtasks_async(template_gid).collect()`
2. After duplication: Poll `subtasks_async(new_task_gid).collect()` every 200ms
3. Return `True` when count >= expected, or `False` after timeout
4. On timeout: Log warning and proceed (graceful degradation)

## Rationale

Polling is the right approach because:

1. **Simplicity**: No external dependencies (webhooks, queues, infrastructure).

2. **Predictability**: We know when we're done (count matches expected) rather than guessing.

3. **Configurable**: Timeout and interval can be tuned per environment or use case.

4. **Graceful Degradation**: If timeout expires, we proceed anyway. Subtasks will eventually appear; the conversion isn't blocked.

5. **Proven Pattern**: Similar polling strategies are used throughout the SDK (e.g., batch job completion).

6. **Low Overhead**: 10 polls at 200ms each = 2 seconds max, with only a lightweight `subtasks_async()` call per poll.

## Alternatives Considered

### Alternative 1: Fixed Delay

- **Description**: Sleep for a fixed duration (e.g., 1.5 seconds) after duplication before proceeding.
- **Pros**:
  - Simplest implementation (single `asyncio.sleep()`)
  - No API calls during wait
- **Cons**:
  - Wastes time if subtasks are ready quickly
  - May be insufficient for large templates
  - No way to know if subtasks are actually ready
  - Hard to tune: too short = race condition, too long = slow conversions
- **Why not chosen**: Inefficient and unreliable. The fixed delay doesn't adapt to actual subtask creation time.

### Alternative 2: Webhook-Based Notification

- **Description**: Register a webhook to receive notifications when subtasks are created, then wait for those events.
- **Pros**:
  - Event-driven, no polling
  - Immediate notification when ready
- **Cons**:
  - Requires webhook infrastructure (endpoint, event routing)
  - Complex setup: need to correlate events to specific duplication operations
  - Overkill for a 1-2 second wait
  - Webhook reliability issues (missed events, delays)
  - Adds external dependency
- **Why not chosen**: Massive complexity for marginal benefit. The 2-second polling window is well within acceptable latency.

### Alternative 3: Poll Until Stable Count

- **Description**: Poll until the subtask count remains the same for 2 consecutive checks (without knowing expected count).
- **Pros**:
  - Works even if we don't know expected count
  - Adapts to any template size
- **Cons**:
  - Slower: must wait for 2 stable checks even after all subtasks exist
  - Could be fooled by slow creation (thinks stable when not done)
  - More complex algorithm
- **Why not chosen**: We can easily get the expected count from the template before duplication. Explicit count matching is more reliable.

### Alternative 4: Job Polling

- **Description**: Poll the job object returned by duplicate endpoint until status changes from "in_progress" to "succeeded".
- **Pros**:
  - Asana's intended mechanism
  - Authoritative: Asana tells us when done
- **Cons**:
  - Job endpoint may not be publicly documented/stable
  - Job status may indicate completion before subtasks are queryable
  - Additional API call type to implement
- **Why not chosen**: Job status doesn't guarantee subtasks are immediately queryable. Direct subtask count is more reliable.

### Alternative 5: No Wait (Fire and Forget)

- **Description**: Proceed immediately after duplicate_async() returns, don't wait for subtasks.
- **Pros**:
  - Fastest possible conversion
  - Simplest code
- **Cons**:
  - Subsequent operations may fail if they depend on subtasks
  - User sees incomplete task if they check immediately
  - Doesn't meet "subtask duplication rate = 100%" requirement (at conversion time)
- **Why not chosen**: Violates the requirement that new Processes have their subtasks present when conversion completes.

## Consequences

### Positive
- **Reliable Detection**: Know exactly when subtasks are ready via count comparison.
- **Fast Happy Path**: If subtasks exist on first poll (200ms), we proceed immediately.
- **Configurable**: Operations team can tune timeout for their template complexity.
- **Graceful Failure**: Timeout doesn't fail conversion, just logs warning.

### Negative
- **Polling Overhead**: 5-10 API calls during wait (but lightweight `subtasks_async()` calls).
- **Timeout Risk**: Large templates (20+ subtasks) may exceed 2-second default timeout.
- **Not Real-Time**: 200ms granularity means up to 200ms delay after subtasks are ready.

### Neutral
- **New Utility Class**: `SubtaskWaiter` is simple and reusable for future wait scenarios.
- **Configuration Parameters**: `subtask_wait_timeout_seconds` and `subtask_poll_interval_seconds` added to config.

## Compliance

- [ ] `SubtaskWaiter.wait_for_subtasks_async()` is called after every `duplicate_async()` that includes subtasks
- [ ] Timeout warning is logged with expected vs actual count
- [ ] Default timeout is 2.0 seconds, configurable via `AutomationConfig`
- [ ] Unit tests cover: immediate ready, timeout, partial count
