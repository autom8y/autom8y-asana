# ADR-0103: Automation Rule Protocol

## Status

Accepted

## Context

The Automation Layer needs a mechanism for defining and executing automation rules. Rules must be:
1. Declarative (trigger conditions expressed as data)
2. Extensible (consumers can create custom rules)
3. Type-safe (protocol enforcement at runtime)
4. Async-first (consistent with SDK's async architecture)

**Requirements**:
- FR-008: Rule registry for custom rules
- FR-009: TriggerCondition with entity type, event, filters
- FR-010: Action types (create_process, add_to_project, set_field)

**Options Considered**:

1. **Option A: Abstract Base Class** - AutomationRule as ABC with abstract methods
2. **Option B: Runtime-Checkable Protocol** - AutomationRule as typing.Protocol
3. **Option C: Function-Based Rules** - Rules as decorated async functions

## Decision

**We will use Option B: Runtime-Checkable Protocol.**

AutomationRule is defined as a `@runtime_checkable` Protocol with required attributes (`id`, `name`, `trigger`) and methods (`should_trigger`, `execute_async`). This allows structural subtyping and duck-typing while maintaining type safety.

## Consequences

### Positive

- **Flexibility**: Any class matching the protocol works; no inheritance required
- **Testability**: Easy to create mock rules for testing
- **Type Safety**: Static analysis catches missing methods/attributes
- **Composition**: Rules can inherit from anything (dataclass, Pydantic, etc.)

### Negative

- **Runtime Overhead**: `@runtime_checkable` has slight performance cost for isinstance() checks
- **Discovery**: Protocol doesn't force IDE autocompletion as strongly as ABC

### Implementation

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AutomationRule(Protocol):
    """Protocol for automation rules."""

    id: str
    name: str
    trigger: TriggerCondition

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool: ...

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult: ...
```

### TriggerCondition Design

Declarative specification for matching:

```python
@dataclass(frozen=True)
class TriggerCondition:
    entity_type: str  # "Process", "Offer", etc.
    event: str        # "created", "updated", "section_changed"
    filters: dict[str, Any] = field(default_factory=dict)

    def matches(self, entity: AsanaResource, event: str, context: dict) -> bool:
        # Entity type check, event check, filter predicate evaluation
```

## References

- TDD-AUTOMATION-LAYER (AutomationRule Protocol section)
- PRD-AUTOMATION-LAYER (FR-008, FR-009, FR-010)
- ADR-0001: Protocol Extensibility (established pattern)
