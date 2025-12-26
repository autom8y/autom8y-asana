# ADR-0017: Automation Architecture

## Metadata

- **Status**: Accepted
- **Date**: 2025-12-25
- **Deciders**: Architect, Requirements Analyst
- **Consolidated From**: ADR-0102, ADR-0103
- **Related**: reference/OPERATIONS.md, ADR-0016 (Business Entity Seeding)

## Context

The Automation Layer requires mechanisms to evaluate rules and execute actions after SaveSession commits complete. Business logic examples include:

- Pipeline conversion: When Sales Process moves to "Converted" section, create new Onboarding Process
- Field population: Copy fields from source entity to created entity
- Notifications: Send email when specific entity state changes
- Validation: Enforce business rules after persistence

Current challenges:
1. **No post-commit hook**: SDK has entity-level hooks (on_pre_save, on_post_save, on_error) but lacks session-level post-commit hook
2. **No rule definition pattern**: Need declarative, extensible, type-safe mechanism for defining automation rules
3. **Separation of concerns**: Automation failures should not fail primary SaveSession commit

The automation layer must be:
- **Declarative**: Trigger conditions expressed as data, not code
- **Extensible**: Consumers can create custom rules without SDK changes
- **Type-safe**: Protocol enforcement at runtime with static analysis support
- **Async-first**: Consistent with SDK's async architecture
- **Isolated**: Automation failures must not rollback primary commit

## Decision

### 1. Post-Commit Hook Architecture

**Extend EventSystem with on_post_commit hook type, consistent with existing hook patterns.**

```python
class EventSystem:
    """Event hook system for entity lifecycle events."""

    # Existing hooks
    on_pre_save: list[Callable]
    on_post_save: list[Callable]
    on_error: list[Callable]

    # NEW: Post-commit hook
    on_post_commit: list[Callable]

    def register_post_commit(
        self,
        handler: Callable[[SaveResult], Awaitable[None]]
    ) -> None:
        """Register handler to execute after SaveSession commits.

        Post-commit handlers receive full SaveResult after API calls
        complete successfully. Handlers execute in registration order.

        Failures in post-commit handlers do NOT rollback the commit.
        Use on_error for commit-dependent error handling.

        Args:
            handler: Async function receiving SaveResult
        """
        self.on_post_commit.append(handler)

    async def fire_post_commit(
        self,
        save_result: SaveResult
    ) -> None:
        """Fire all registered post-commit handlers.

        Executes handlers in registration order. Handler failures
        are logged but do not propagate (commit already succeeded).
        """
        for handler in self.on_post_commit:
            try:
                await handler(save_result)
            except Exception as e:
                logger.error(
                    "post_commit_handler_failed",
                    handler=handler.__name__,
                    error=str(e),
                    exc_info=True
                )
```

**Integration with SaveSession**:

```python
class SaveSession:
    async def execute_async(self) -> SaveResult:
        """Execute all actions and return result."""
        # Execute pre-save hooks
        await self._event_system.fire_pre_save(...)

        # Execute API calls
        result = await self._execute_batch()

        # Execute post-save hooks
        await self._event_system.fire_post_save(result)

        # NEW: Execute post-commit hooks
        await self._event_system.fire_post_commit(result)

        return result
```

**AutomationEngine integration**:

```python
class AutomationEngine:
    """Built-in consumer of post-commit hooks."""

    def __init__(self, client: AsanaClient):
        self._client = client
        self._rules: list[AutomationRule] = []

        # Register as post-commit handler
        client.event_system.register_post_commit(
            self._on_post_commit
        )

    async def _on_post_commit(self, result: SaveResult) -> None:
        """Evaluate rules and execute actions."""
        for entity in result.created + result.updated:
            for rule in self._rules:
                if rule.should_trigger(entity, result.event, result.context):
                    await rule.execute_async(entity, result.context)
```

**Rationale**:
- **Consistency**: Follows existing on_pre_save/on_post_save/on_error pattern
- **Extensibility**: Consumers can register custom post-commit handlers beyond automation
- **Separation**: Automation becomes one of potentially many post-commit handlers
- **Error isolation**: Automation failures logged but don't fail primary commit
- **Testability**: Post-commit hooks can be mocked/verified in tests

### 2. Automation Rule Protocol

**Define AutomationRule as @runtime_checkable Protocol with required attributes and methods.**

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AutomationRule(Protocol):
    """Protocol for automation rules.

    Any class implementing this protocol can be registered as a rule.
    No inheritance required - structural subtyping via duck typing.
    """

    # Required attributes
    id: str
    name: str
    trigger: TriggerCondition

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Determine if rule should execute for entity/event.

        Args:
            entity: Entity that triggered the event
            event: Event type (created, updated, section_changed)
            context: Additional context from SaveResult

        Returns:
            True if rule should execute, False otherwise
        """
        ...

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult:
        """Execute rule action asynchronously.

        Args:
            entity: Entity to operate on
            context: Automation execution context

        Returns:
            Result of automation execution
        """
        ...
```

**TriggerCondition** (declarative specification):

```python
@dataclass(frozen=True)
class TriggerCondition:
    """Declarative trigger specification for rules.

    Defines matching criteria without requiring code evaluation.
    """

    entity_type: str          # "Process", "Offer", etc.
    event: str                # "created", "updated", "section_changed"
    filters: dict[str, Any] = field(default_factory=dict)

    def matches(
        self,
        entity: AsanaResource,
        event: str,
        context: dict
    ) -> bool:
        """Check if entity/event matches trigger condition.

        Evaluates:
        1. Entity type check (exact match)
        2. Event check (exact match)
        3. Filter predicate evaluation (field value comparisons)

        Returns:
            True if all conditions match
        """
        # Entity type check
        if entity.__class__.__name__ != self.entity_type:
            return False

        # Event check
        if event != self.event:
            return False

        # Filter evaluation
        for field, expected_value in self.filters.items():
            actual_value = getattr(entity, field, None)
            if actual_value != expected_value:
                return False

        return True
```

**Example rule implementation**:

```python
from dataclasses import dataclass

@dataclass
class PipelineConversionRule:
    """Rule implementing AutomationRule Protocol via structural subtyping."""

    id: str = "pipeline_conversion"
    name: str = "Convert Sales to Onboarding"

    trigger: TriggerCondition = field(default_factory=lambda: TriggerCondition(
        entity_type="Process",
        event="section_changed",
        filters={"process_type": "SALES", "pipeline_state": "CONVERTED"}
    ))

    def should_trigger(self, entity, event, context) -> bool:
        """Delegate to trigger condition."""
        return self.trigger.matches(entity, event, context)

    async def execute_async(self, entity, context) -> AutomationResult:
        """Create Onboarding process from converted Sales process."""
        # Use BusinessSeeder and FieldSeeder from ADR-0016
        seeder = BusinessSeeder(context.client)
        field_seeder = FieldSeeder()

        # Get parent hierarchy
        business = await entity.get_business_async()
        unit = await entity.get_unit_async()

        # Compute fields
        fields = await field_seeder.seed_fields_async(
            business, unit, source_process=entity
        )

        # Create Onboarding process
        result = await seeder.seed_async(
            business=BusinessData(name=business.name),
            process=ProcessData(
                name=f"Onboarding - {entity.name}",
                process_type=ProcessType.ONBOARDING,
                initial_state=ProcessSection.OPPORTUNITY
            )
        )

        # Apply computed fields
        for field_name, value in fields.items():
            setattr(result.process, field_name, value)

        # Save new process
        session = SaveSession(context.client)
        session.update(result.process)
        await session.execute_async()

        return AutomationResult(
            success=True,
            created_entities=[result.process]
        )
```

**Rationale**:
- **Structural subtyping**: Any class matching protocol works without inheritance
- **Flexibility**: Rules can inherit from anything (dataclass, Pydantic, etc.)
- **Testability**: Easy to create mock rules for testing
- **Type safety**: Static analysis catches missing methods/attributes
- **Composition**: Rules compose with other patterns (dataclass, Pydantic)
- **Runtime checking**: `isinstance(rule, AutomationRule)` validates protocol compliance

## Alternatives Considered

### Alternative A: Abstract Base Class

- **Description**: AutomationRule as ABC with abstract methods
- **Pros**: Forced implementation; clearer inheritance
- **Cons**: Requires inheritance; less flexible; can't compose with dataclass/Pydantic easily
- **Why not chosen**: Protocol allows composition without inheritance burden

### Alternative B: Function-Based Rules

- **Description**: Rules as decorated async functions (`@automation_rule`)
- **Pros**: Simple for basic cases; minimal boilerplate
- **Cons**: Hard to access state; harder to test; no clear trigger specification
- **Why not chosen**: Rules often need state and complex logic; class-based is more maintainable

### Alternative C: Pre-Commit Hooks for Automation

- **Description**: Execute automation before commit in pre_save hook
- **Pros**: Automation part of same transaction
- **Cons**: Automation failures rollback primary commit; tighter coupling
- **Why not chosen**: Primary operations should succeed independent of automation

### Alternative D: Separate Automation Service

- **Description**: Consumer must call automation service after SaveSession
- **Pros**: Explicit; no magic hooks
- **Cons**: Easy to forget; boilerplate in every consumer; no standardization
- **Why not chosen**: Post-commit hooks provide automatic execution without boilerplate

## Consequences

### Positive

- **Consistency**: Post-commit hook follows existing EventSystem patterns
- **Extensibility**: Consumers can register custom post-commit handlers
- **Separation**: Automation is one of potentially many post-commit handlers
- **Error isolation**: Automation failures don't rollback primary commit
- **Flexibility**: AutomationRule Protocol allows any implementation structure
- **Type safety**: Static analysis catches missing protocol methods
- **Testability**: Easy to mock rules and test independently
- **Declarative triggers**: TriggerCondition provides data-driven matching

### Negative

- **Runtime overhead**: @runtime_checkable has slight performance cost for isinstance() checks
- **Discovery**: Protocol doesn't force IDE autocompletion as strongly as ABC
- **Complexity**: Post-commit execution adds another phase to SaveSession lifecycle
- **Debugging**: Failures in post-commit handlers are logged but may be missed

### Neutral

- AutomationEngine integrates as built-in consumer of post-commit hooks
- Rules can be loaded dynamically from config or registered programmatically
- TriggerCondition filters are simple equality checks (can be extended)

## Implementation Guidance

### When adding automation:

1. Register post-commit hooks via EventSystem.register_post_commit()
2. Define rules as classes implementing AutomationRule Protocol
3. Use TriggerCondition for declarative event matching
4. Ensure automation failures are logged but don't propagate
5. Use BusinessSeeder and FieldSeeder for entity creation and field population

### When creating rules:

1. Implement AutomationRule Protocol (id, name, trigger, should_trigger, execute_async)
2. Use dataclass or Pydantic for rule structure
3. Define TriggerCondition with entity_type, event, and filters
4. Delegate should_trigger to trigger.matches() for standard cases
5. Use async/await in execute_async for all I/O operations

### When testing automation:

1. Mock post-commit hooks to verify registration
2. Create test rules with simple trigger conditions
3. Verify should_trigger matches expected entities/events
4. Test execute_async with mocked client/context
5. Verify automation failures don't fail primary commit

## Compliance

- [ ] EventSystem.on_post_commit hook list implemented
- [ ] EventSystem.register_post_commit() method implemented
- [ ] EventSystem.fire_post_commit() executes handlers in order
- [ ] Post-commit handler failures logged but don't propagate
- [ ] SaveSession calls fire_post_commit() after execute_async()
- [ ] AutomationRule Protocol has required attributes (id, name, trigger)
- [ ] AutomationRule Protocol has required methods (should_trigger, execute_async)
- [ ] Protocol is @runtime_checkable
- [ ] TriggerCondition dataclass with entity_type, event, filters
- [ ] TriggerCondition.matches() implements matching logic
- [ ] AutomationEngine registers as post-commit handler
- [ ] Tests verify post-commit hook execution
- [ ] Tests verify automation failures don't fail commit
