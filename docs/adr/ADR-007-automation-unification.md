# ADR-007: Automation Unification -- Shared Primitives with Unified Dispatch

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

The microservice has three distinct automation subsystems:

1. **PipelineConversionRule** (event-driven, commit-triggered) -- Sales to Onboarding only
2. **Polling ActionExecutor** (scheduled, condition-driven) -- add_tag, add_comment, change_section
3. **WorkflowAction** (batch, schedule-driven) -- ConversationAuditWorkflow

The stakeholder wants unification from the start while full context is fresh. Specifically:
- Actions and Workflows MUST share resolution/selection primitives
- Workflows can trigger Actions AND Actions can trigger Workflows (bidirectional)
- PipelineConversionRule should be absorbed into the lifecycle engine

## Decision

**Unify all three subsystems under shared resolution primitives, with a common dispatch layer for cross-triggering.**

### Architecture

```
                  +-----------------------+
                  |   AutomationDispatch  |
                  |   (unified entry)     |
                  +-----------+-----------+
                              |
              +---------------+---------------+
              |               |               |
    +---------v---+   +-------v-------+   +---v-----------+
    | Lifecycle   |   | ActionExecutor|   | WorkflowAction|
    | Engine      |   | (extended)    |   | (existing)    |
    +---------+---+   +-------+-------+   +---+-----------+
              |               |               |
              +-------+-------+-------+-------+
                      |               |
              +-------v-------+ +-----v--------+
              | Resolution    | | Session      |
              | Context       | | Cache        |
              +---------------+ +--------------+
```

### Shared Primitives

All three subsystems use:
- **ResolutionContext**: Entity resolution with session caching
- **ResolutionResult**: Structured success/failure/partial outcomes
- **SelectionPredicate**: Entity selection within holders
- **ApiBudget**: Bounded API call tracking

### PipelineConversionRule Absorption

PipelineConversionRule becomes the first lifecycle stage handler. The existing rule is refactored into:

```python
# Before (current PipelineConversionRule -- 1000+ lines)
class PipelineConversionRule:
    async def execute_async(self, entity, context): ...

# After (lifecycle engine with stage config)
lifecycle_engine.register_stage("sales", SalesStageHandler())
# SalesStageHandler uses resolution primitives + stage YAML config
```

The absorption is phased:
1. Build lifecycle engine with Sales -> Onboarding as first route
2. Verify parity with existing PipelineConversionRule behavior
3. Remove PipelineConversionRule, point automation engine to lifecycle engine

### Bidirectional Triggering

```python
class AutomationDispatch:
    async def dispatch_async(
        self,
        trigger: AutomationTrigger,
    ) -> AutomationResult:
        """Route trigger to appropriate subsystem."""
        if trigger.is_lifecycle_event:
            return await self._lifecycle_engine.handle_async(trigger)
        elif trigger.is_action:
            return await self._action_executor.execute_async(trigger)
        elif trigger.is_workflow:
            return await self._workflow_registry.execute_async(trigger)
```

Lifecycle engine can emit action triggers (e.g., add_tag after transition). ActionExecutor can emit lifecycle triggers (e.g., section change detected during polling).

### Circular Trigger Prevention

A trigger context carries a `trigger_chain: list[str]` tracking the chain of triggers. If a trigger ID appears in the chain, it is a cycle and the dispatch returns immediately with a diagnostic result.

### Tag Vocabulary Preservation

The `route_*`, `request_*`, `play_*` tag vocabulary is preserved as trigger identifiers in the unified dispatch. Tags map to lifecycle engine handlers:

```yaml
tag_routing:
  route_onboarding: { stage: onboarding, action: lifecycle_transition }
  route_sales: { stage: sales, action: lifecycle_transition }
  request_asset_edit: { action: entity_creation, entity_type: asset_edit }
  play_backend_onboard_a_business: { action: play_creation, play_type: backend_onboard }
```

This preserves the operations team's existing workflow (add tag + complete task = trigger automation) while routing through the unified system.

### Webhook Handler

A FastAPI route receives Asana Rule webhooks:

```python
@router.post("/api/v1/webhooks/asana")
async def handle_asana_webhook(payload: AsanaWebhookPayload) -> WebhookResponse:
    trigger = AutomationTrigger.from_webhook(payload)
    result = await automation_dispatch.dispatch_async(trigger)
    return WebhookResponse(accepted=True, result_id=result.id)
```

The webhook handler is a thin adapter; all business logic lives in the dispatch layer.

## Alternatives Considered

### Keep Three Separate Subsystems (Rejected)

Maintaining PipelineConversionRule, ActionExecutor, and WorkflowAction as independent systems. This prevents code sharing, makes bidirectional triggering impossible, and means every new capability must be built three times.

### Full Merge Into Single System (Rejected)

Replacing all three with a single uber-system. WorkflowAction (batch, schedule-driven) has fundamentally different execution semantics from ActionExecutor (per-task, condition-driven). Forcing them into one interface creates an overcomplicated abstraction.

### New Trigger Mechanism (Replace Tags, Rejected)

Replacing the `route_*`/`request_*`/`play_*` tag vocabulary with a new mechanism. The operations team uses these tags daily. Replacing them requires training and creates migration risk. Tags are a proven, valuable mechanism.

## Consequences

### Positive

- Resolution primitives shared across all automation types
- Bidirectional triggering enables complex workflows (lifecycle -> action -> lifecycle)
- Tag vocabulary preserved for operational continuity
- PipelineConversionRule absorbed eliminates duplicate routing logic
- Webhook handler enables direct Asana Rule routing to microservice

### Negative

- Unified dispatch adds a routing layer (minimal overhead but more code to understand)
- Circular trigger prevention must be explicitly designed (trigger_chain tracking)
- Tag routing YAML must be validated against lifecycle DAG YAML
- Migration requires verifying behavior parity with existing PipelineConversionRule
