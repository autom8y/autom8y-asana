"""Base types for Automation Layer.

Per TDD-AUTOMATION-LAYER: AutomationRule protocol, TriggerCondition, and Action.
Per FR-008: Custom rules implement AutomationRule interface.
Per FR-009: TriggerCondition supports entity type, event type, and filter predicates.
Per FR-010: Action types include create_process, add_to_project, set_field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from autom8_asana.automation.context import AutomationContext
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.models import AutomationResult


@dataclass(frozen=True)
class TriggerCondition:
    """Declarative trigger specification for automation rules.

    Per FR-009: Supports entity type, event type, and filter predicates.

    Attributes:
        entity_type: Target entity type name (e.g., "Process", "Offer").
        event: Event type ("created", "updated", "section_changed", "deleted").
        filters: Additional predicates (e.g., {"section": "converted"}).

    Examples:
        # Trigger when any Process moves to CONVERTED section
        TriggerCondition(
            entity_type="Process",
            event="section_changed",
            filters={"section": "converted", "process_type": "sales"}
        )

        # Trigger when Offer is created
        TriggerCondition(entity_type="Offer", event="created")
    """

    entity_type: str
    event: str
    filters: dict[str, Any] = field(default_factory=dict)

    def matches(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Check if this condition matches the given entity and event.

        Args:
            entity: The entity that triggered the event.
            event: The event type that occurred.
            context: Additional context (e.g., old_section, new_section).

        Returns:
            True if condition matches, False otherwise.
        """
        # Check entity type
        if self.entity_type != type(entity).__name__:
            return False

        # Check event type
        if self.event != event:
            return False

        # Check filters
        for key, expected in self.filters.items():
            actual = context.get(key)
            if actual is None:
                # Try to get from entity attribute
                actual = getattr(entity, key, None)
            # Handle enum values (check after getting attribute)
            if actual is not None and hasattr(actual, "value"):
                actual = actual.value
            if actual != expected:
                return False

        return True


@dataclass
class Action:
    """Action to execute when rule triggers.

    Per FR-010: Supports create_process, add_to_project, set_field.

    Attributes:
        type: Action type identifier.
        params: Action-specific parameters.

    Example params for each type:
        create_process: {"target_type": "onboarding", "template_section": "Template"}
        add_to_project: {"project_gid": "1234567890"}
        set_field: {"field_name": "Status", "value": "Active"}
    """

    type: str  # "create_process", "add_to_project", "set_field"
    params: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AutomationRule(Protocol):
    """Protocol for automation rules.

    Per FR-008: Custom rules implement this interface.

    Implementers must provide:
        - id: Unique rule identifier
        - name: Human-readable name
        - trigger: TriggerCondition for matching
        - should_trigger(): Fine-grained trigger check
        - execute_async(): Async execution of rule actions

    Example:
        class MyCustomRule:
            @property
            def id(self) -> str:
                return "my_custom_rule"

            @property
            def name(self) -> str:
                return "My Custom Rule"

            @property
            def trigger(self) -> TriggerCondition:
                return TriggerCondition(
                    entity_type="Offer",
                    event="created",
                )

            def should_trigger(
                self,
                entity: AsanaResource,
                event: str,
                context: dict[str, Any],
            ) -> bool:
                return self.trigger.matches(entity, event, context)

            async def execute_async(
                self,
                entity: AsanaResource,
                context: AutomationContext,
            ) -> AutomationResult:
                # Implementation here
                ...
    """

    @property
    def id(self) -> str:
        """Unique rule identifier."""
        ...

    @property
    def name(self) -> str:
        """Human-readable rule name."""
        ...

    @property
    def trigger(self) -> TriggerCondition:
        """Trigger condition for this rule."""
        ...

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Check if rule should trigger for this entity/event.

        Args:
            entity: The entity that triggered the event.
            event: The event type that occurred.
            context: Additional context (old_section, new_section, etc.).

        Returns:
            True if rule should trigger, False otherwise.
        """
        ...

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult:
        """Execute rule actions asynchronously.

        Per Open Question 1: Async-only for V1.

        Args:
            entity: The entity that triggered the rule.
            context: Automation execution context.

        Returns:
            AutomationResult with execution details.
        """
        ...
