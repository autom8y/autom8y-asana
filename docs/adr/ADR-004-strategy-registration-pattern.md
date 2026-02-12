# ADR-004: Strategy Registration -- Registry with Declarative Config

**Status**: Accepted
**Date**: 2026-02-11
**Deciders**: Moonshot Architect (delegated authority from stakeholder)

## Context

Both the resolution system and the lifecycle engine need registration patterns:

1. **Resolution strategies**: How do traversal strategies register for entity types?
2. **Lifecycle stages**: How do pipeline stages register their transition rules?
3. **Entity selection**: How do selection strategies register for holder types?

The stakeholder leaned toward a strategy registry pattern. The codebase already uses registry patterns (EntityProjectRegistry, WorkspaceProjectRegistry, SchemaRegistry) established in the entity resolution hardening initiative.

## Decision

**Use a strategy registry pattern with declarative YAML configuration for lifecycle stages, and code-based registration for resolution strategies.**

### Resolution Strategy Registry

```python
class ResolutionStrategyRegistry:
    _strategies: dict[type[BusinessEntity], list[ResolutionStrategy]]

    def register(
        self,
        target_type: type[BusinessEntity],
        strategy: ResolutionStrategy,
        *,
        priority: int = 100,
    ) -> None: ...

    def get_chain(
        self,
        target_type: type[BusinessEntity],
    ) -> list[ResolutionStrategy]: ...
```

Strategies register at bootstrap time. The registry returns an ordered chain for each target entity type. Default chains are provided; callers can override for specific use cases.

### Lifecycle Stage Registry

```python
# YAML configuration (declarative)
pipeline_stages:
  sales:
    project_gid: "1200944186565610"
    converted_route: onboarding
    did_not_convert_route: outreach
    cascading_sections:
      offer: "Sales Process"
      unit: "Next Steps"
      business: "OPPORTUNITY"
    init_actions:
      - type: play_backend_onboard  # only on specific stages
```

Stage configuration is declarative YAML rather than code-based because:
- Stage routing is pure data (source -> target mapping)
- Non-developer operators may need to adjust section mappings
- Adding a new pipeline stage should not require code changes

### Entity Selection Registry

Selection strategies are code-based (registered at bootstrap) because selection logic varies by entity type and involves business rules:

```python
class SelectionStrategyRegistry:
    _strategies: dict[type[HolderFactory], SelectionStrategy]

    def register(
        self,
        holder_type: type[HolderFactory],
        strategy: SelectionStrategy,
    ) -> None: ...
```

## Alternatives Considered

### Decorator-Based Registration (Rejected)

```python
@register_strategy(target_type=Business)
class HierarchyResolutionStrategy:
    ...
```

Decorator registration is import-order-dependent. The codebase already moved away from `__init_subclass__` registration (TDD-registry-consolidation) to explicit bootstrap for this reason.

### Class-Based Stage Configuration (Rejected)

```python
class SalesStage(PipelineStage):
    source_type = ProcessType.SALES
    converted_route = ProcessType.ONBOARDING
    ...
```

Class-per-stage creates N files for N stages with nearly identical structure. The legacy codebase has 9 stage classes (sales, outreach, onboarding, implementation, month1, retention, reactivation, account_error, expansion) -- each with 80% identical code. YAML config eliminates this duplication.

### Pure YAML for Everything (Rejected)

Resolution strategies involve complex logic (API calls, hierarchy traversal, predicate evaluation) that cannot be expressed in YAML. Code-based registration is necessary for behavioral components.

## Consequences

### Positive

- Explicit bootstrap avoids import-order issues
- YAML config for stages is auditable and diffable
- Code-based strategies support complex resolution logic
- Registry pattern is consistent with existing codebase conventions
- Adding new pipeline stages requires only YAML changes

### Negative

- Two registration mechanisms (code + YAML) to understand
- YAML config must be validated at startup (schema validation needed)
- Registry state must be reset in tests (same pattern as existing registry resets in conftest)
