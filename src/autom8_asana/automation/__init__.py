"""Automation Layer for autom8_asana SDK.

Per TDD-AUTOMATION-LAYER: Provides rule-based automation that executes
after SaveSession commits.

Main API:
    AutomationEngine: Orchestrates rule evaluation and execution
    AutomationRule: Protocol for implementing custom rules
    TriggerCondition: Declarative trigger specification
    Action: Action to execute when rule triggers
    AutomationContext: Execution context with loop prevention
    AutomationConfig: Configuration for automation behavior

Example - Basic Usage:
    from autom8_asana.automation import AutomationEngine, AutomationConfig

    # Configure automation
    config = AutomationConfig(
        enabled=True,
        max_cascade_depth=5,
        pipeline_templates={
            "sales": "1234567890123",
            "onboarding": "9876543210987",
        },
    )

    # Access via client
    if client.automation:
        client.automation.register(MyCustomRule())

Example - Custom Rule:
    from autom8_asana.automation import (
        AutomationRule,
        TriggerCondition,
        AutomationContext,
    )
    from autom8_asana.persistence.models import AutomationResult

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
            return AutomationResult(
                rule_id=self.id,
                rule_name=self.name,
                triggered_by_gid=entity.gid,
                triggered_by_type=type(entity).__name__,
                success=True,
            )

    # Register with engine
    client.automation.register(MyCustomRule())
"""

from autom8_asana.automation.base import Action, AutomationRule, TriggerCondition
from autom8_asana.automation.config import AutomationConfig, PipelineStage
from autom8_asana.automation.context import AutomationContext
from autom8_asana.automation.engine import AutomationEngine
from autom8_asana.automation.pipeline import PipelineConversionRule
from autom8_asana.automation.seeding import FieldSeeder
from autom8_asana.automation.templates import TemplateDiscovery
from autom8_asana.automation.waiter import SubtaskWaiter

__all__ = [
    # Main API
    "AutomationEngine",
    "AutomationRule",
    "TriggerCondition",
    "Action",
    "AutomationContext",
    "AutomationConfig",
    "PipelineStage",
    # Phase 2: Pipeline Conversion
    "PipelineConversionRule",
    "TemplateDiscovery",
    "FieldSeeder",
    "SubtaskWaiter",
]
