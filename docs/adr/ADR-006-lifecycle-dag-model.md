# ADR-006: Lifecycle DAG Model -- Static Config with Dynamic Products Branching

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

The lifecycle engine must model pipeline transitions as a DAG (not a linear chain). The Products field (MultiEnumField) on Process entities determines which downstream entities get created.

The stakeholder leaned toward "static base + dynamic overrides."

Production data shows:
- 6 active products (Meta Marketing, TikTok Marketing, Newsletter Product, Videography, Video Session, FB & IG Marketing)
- Only Videography and Video Session trigger non-standard entity creation
- The routing DAG has self-loops (Outreach, Reactivation) requiring max-iteration guards
- Dependencies are sparse (0-1 per process)

## Decision

**Static YAML-configured DAG for core routing, with Products-driven dynamic branching for entity creation.**

### Static DAG (YAML)

```yaml
lifecycle_dag:
  sales:
    converted: onboarding
    did_not_convert: outreach
  outreach:
    converted: sales
    did_not_convert: outreach  # self-loop
    max_iterations: 5
  onboarding:
    converted: implementation
    did_not_convert: sales
    init_actions:
      - type: products_check
        condition: "video*"
        action: request_source_videographer
  implementation:
    converted: month1
    did_not_convert: sales
    init_actions:
      - type: play_backend_onboard_a_business
        condition: not_already_linked
      - type: request_asset_edit
        condition: not_already_linked
  month1:
    converted: null  # terminal
    did_not_convert: null  # terminal
    init_actions:
      - type: activate_campaign
  retention:
    converted: implementation
    did_not_convert: reactivation
    init_actions:
      - type: deactivate_campaign
  reactivation:
    converted: implementation
    did_not_convert: reactivation  # self-loop
    max_iterations: 5
    delay_schedule: [90, 180, 360]  # graduated days
    init_actions:
      - type: deactivate_campaign
  account_error:
    converted: null  # terminal with activate
    did_not_convert: retention
    init_actions:
      - type: deactivate_campaign
  expansion:
    converted: null
    did_not_convert: null
```

### Dynamic Branching

Products-driven entity creation is a code-based plugin, not YAML:

```python
class ProductsBranchingPlugin:
    """Evaluate Products field to determine entity creation."""

    async def evaluate_async(
        self,
        process: Process,
        context: ResolutionContext,
    ) -> list[EntityCreationRequest]:
        products = process.products  # MultiEnumField descriptor
        requests = []
        if any(p.lower().startswith("video") for p in products):
            requests.append(EntityCreationRequest(
                entity_type="source_videographer",
                holder_type=VideographyHolder,
            ))
        return requests
```

This separates the "which products exist" data question from the "what to create" logic question.

### Self-Loop Guards

Self-loops (Outreach -> Outreach, Reactivation -> Reactivation) include:
- `max_iterations`: Hard cap per Unit (prevents infinite loops)
- `delay_schedule`: Graduated delay for Reactivation (90 -> 180 -> 360 days)

## Alternatives Considered

### Pure Dynamic DAG (Rejected)

Build the entire DAG at runtime from per-process data. This makes the system behavior unpredictable and untestable. The routing graph is fundamentally static (Sales always goes to Onboarding on CONVERTED) -- only the entity creation branches vary.

### Pure Static DAG (Rejected)

No dynamic branching at all. This cannot handle Products-driven entity creation without hardcoding every product combination. New products would require code changes.

### Class-Per-Stage (Rejected, Legacy Pattern)

The legacy has 9 Pipeline subclasses (Sales, Onboarding, Implementation...) each overriding `init_process()`. This creates 80% code duplication and requires modifying the class hierarchy to add new stages. YAML config eliminates this.

## Consequences

### Positive

- Core routing is auditable YAML (no code reading needed to understand the DAG)
- Products-driven branching is isolated to a single plugin
- Self-loop guards are configurable per stage
- Adding new stages is a YAML change; adding new product-driven entities is a plugin
- DAG can be visualized from YAML for documentation

### Negative

- Two layers of configuration (YAML + code plugins) to understand
- YAML must be schema-validated at startup to catch misconfiguration
- Delay scheduling requires a scheduling mechanism (not yet built)
