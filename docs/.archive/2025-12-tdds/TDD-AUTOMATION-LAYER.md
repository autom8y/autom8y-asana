# TDD: Automation Layer

## Metadata

- **TDD ID**: TDD-AUTOMATION-LAYER
- **Status**: Draft
- **Author**: Architect
- **Created**: 2025-12-18
- **Last Updated**: 2025-12-18
- **PRD Reference**: [PRD-AUTOMATION-LAYER](/docs/requirements/PRD-AUTOMATION-LAYER.md)
- **Related TDDs**: TDD-DETECTION, TDD-PROCESS-PIPELINE
- **Related ADRs**: ADR-0035 (UoW Pattern), ADR-0041 (Event Hooks), ADR-0054 (Cascading Fields), ADR-0095 (Self-Healing), ADR-0096 (ProcessType), ADR-0097 (ProcessSection)

## Overview

This design introduces an SDK-native Automation Layer that evaluates rules and executes actions after SaveSession commits. The system provides zero-code pipeline conversion (e.g., Sales to Onboarding), leveraging existing SDK infrastructure: post-commit hooks via EventSystem, field cascade/inheritance patterns, and ProcessSection state matching. The architecture prioritizes failure isolation (automation failures never break primary commits) and extensibility (custom rules via registry).

## Requirements Summary

**From PRD-AUTOMATION-LAYER**: 15 functional requirements across 3 priority levels.

| Priority | Requirements | Count |
|----------|-------------|-------|
| Must (P1) | FR-001 through FR-007 | 7 |
| Should (P2) | FR-008 through FR-012 | 5 |
| Could (P3) | FR-013 through FR-015 | 3 |

**Key Requirements**:
- FR-001: AutomationEngine evaluates rules after commit
- FR-003: PipelineConversionRule triggers on section change to CONVERTED
- FR-005: Field seeding from Business/Unit cascade and source Process carry-through
- NFR-003: Automation failures do not fail primary commit

## System Context

```
                              +-------------------------------------------+
                              |            External Systems               |
                              |  (Webhooks, Scheduled Jobs, CLI Tools)    |
                              +-------------------+-----------------------+
                                                  |
                                                  v
+-----------------------------------------------------------------------------------------+
|                                    autom8_asana SDK                                     |
|                                                                                         |
|  +-------------------+     +-------------------+     +-----------------------------+    |
|  |    AsanaClient    |---->|   SaveSession     |---->|     commit_async()          |    |
|  |                   |     |                   |     |                             |    |
|  | .automation       |     | on_post_commit()  |     | Phase 1: CRUD Operations    |    |
|  | (engine ref)      |     | hook registration |     | Phase 2: Action Operations  |    |
|  +--------+----------+     +-------------------+     | Phase 3: Cascade Operations |    |
|           |                                          | Phase 4: Healing Operations |    |
|           v                                          | Phase 5: Automation (NEW)   |    |
|  +-------------------+                               +-------------+---------------+    |
|  | AutomationEngine  |<--------- post-commit hook -----------------+                    |
|  |                   |                                                                  |
|  | .evaluate()       |     +-------------------------------------------+                |
|  | .register()       |---->|             Rule Registry                 |                |
|  | .rules            |     |                                           |                |
|  +--------+----------+     | +---------------+ +---------------------+ |                |
|           |                | | PipelineRule  | | CustomRule (user)   | |                |
|           |                | +---------------+ +---------------------+ |                |
|           |                +-------------------------------------------+                |
|           v                                                                             |
|  +-------------------+     +-------------------+     +-----------------------------+    |
|  | TemplateDiscovery |     |   FieldSeeder     |     |      AutomationResult       |    |
|  |                   |     |                   |     |                             |    |
|  | find_template()   |     | cascade_from_     |     | .rule_id, .success          |    |
|  | section matching  |     |   hierarchy()     |     | .entities_created           |    |
|  +-------------------+     | carry_through()   |     | .execution_time_ms          |    |
|                            +-------------------+     +-----------------------------+    |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
                                                  |
                                                  v
                              +-------------------------------------------+
                              |              Asana API                    |
                              |  (Tasks, Projects, Sections, Custom Fields)|
                              +-------------------------------------------+
```

## Design

### Component Architecture

```
src/autom8_asana/
+-- automation/                 # NEW: Automation Layer module
|   +-- __init__.py            # Public exports
|   +-- base.py                # AutomationRule protocol, TriggerCondition, Action
|   +-- config.py              # AutomationConfig dataclass
|   +-- engine.py              # AutomationEngine (evaluation, registration)
|   +-- pipeline.py            # PipelineConversionRule (built-in)
|   +-- templates.py           # TemplateDiscovery service
|   +-- seeding.py             # FieldSeeder service
|   +-- context.py             # AutomationContext (execution context)
|
+-- persistence/
|   +-- models.py              # + AutomationResult dataclass
|   +-- events.py              # + PostCommitHook type alias
|   +-- session.py             # + Phase 5 automation, on_post_commit()
|
+-- config.py                  # + AutomationConfig field in AsanaConfig
+-- client.py                  # + client.automation property
```

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `AutomationConfig` | Configuration for automation behavior | `automation/config.py` |
| `AutomationEngine` | Rule evaluation and execution orchestration | `automation/engine.py` |
| `AutomationRule` | Protocol defining rule interface | `automation/base.py` |
| `TriggerCondition` | Declarative trigger specification | `automation/base.py` |
| `PipelineConversionRule` | Built-in Sales->Onboarding rule | `automation/pipeline.py` |
| `TemplateDiscovery` | Finds template sections in target projects | `automation/templates.py` |
| `FieldSeeder` | Computes field values from hierarchy/carry-through | `automation/seeding.py` |
| `AutomationContext` | Execution context with client, config, depth | `automation/context.py` |
| `AutomationResult` | Result of rule execution | `persistence/models.py` |

### Data Model

#### AutomationConfig

```python
from dataclasses import dataclass, field

@dataclass
class AutomationConfig:
    """Configuration for Automation Layer.

    Per FR-006: Part of AsanaConfig for automation settings.

    Attributes:
        enabled: Master switch for automation (default: True)
        max_cascade_depth: Maximum nested automation depth (default: 5)
        rules_source: Where to load rules from ("inline", "file", "api")
        pipeline_templates: ProcessType to target project GID mapping
    """

    enabled: bool = True
    max_cascade_depth: int = 5
    rules_source: str = "inline"  # "inline" | "file" | "api"
    pipeline_templates: dict[str, str] = field(default_factory=dict)
    # e.g., {"sales": "1234567890123", "onboarding": "9876543210987"}

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_cascade_depth < 1:
            raise ConfigurationError(
                f"max_cascade_depth must be at least 1, got {self.max_cascade_depth}"
            )
        if self.rules_source not in ("inline", "file", "api"):
            raise ConfigurationError(
                f"rules_source must be 'inline', 'file', or 'api', got {self.rules_source}"
            )
```

#### TriggerCondition

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class TriggerCondition:
    """Declarative trigger specification for automation rules.

    Per FR-009: Supports entity type, event type, and filter predicates.

    Attributes:
        entity_type: Target entity type (e.g., "Process", "Offer")
        event: Event type ("created", "updated", "section_changed", "deleted")
        filters: Additional predicates (e.g., {"section": "converted"})

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

    def matches(self, entity: AsanaResource, event: str, context: dict[str, Any]) -> bool:
        """Check if this condition matches the given entity and event.

        Args:
            entity: The entity that triggered the event
            event: The event type that occurred
            context: Additional context (e.g., old_section, new_section)

        Returns:
            True if condition matches, False otherwise
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
            if actual != expected:
                return False

        return True
```

#### Action

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Action:
    """Action to execute when rule triggers.

    Per FR-010: Supports create_process, add_to_project, set_field.

    Attributes:
        type: Action type identifier
        params: Action-specific parameters
    """

    type: str  # "create_process", "add_to_project", "set_field"
    params: dict[str, Any] = field(default_factory=dict)

    # Example params for each type:
    # create_process: {"target_type": "onboarding", "template_section": "Template"}
    # add_to_project: {"project_gid": "1234567890"}
    # set_field: {"field_name": "Status", "value": "Active"}
```

#### AutomationRule Protocol

```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass

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
    """

    id: str
    name: str
    trigger: TriggerCondition

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Check if rule should trigger for this entity/event.

        Args:
            entity: The entity that triggered the event
            event: The event type that occurred
            context: Additional context (old_section, new_section, etc.)

        Returns:
            True if rule should trigger, False otherwise
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
            entity: The entity that triggered the rule
            context: Automation execution context

        Returns:
            AutomationResult with execution details
        """
        ...
```

#### AutomationContext

```python
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

@dataclass
class AutomationContext:
    """Execution context for automation rules.

    Provides access to SDK client, configuration, and cascade tracking.

    Attributes:
        client: AsanaClient for API operations
        config: AutomationConfig with settings
        depth: Current cascade depth (for loop prevention)
        visited: Set of (entity_gid, rule_id) already processed
        save_result: Original SaveResult that triggered automation
    """

    client: AsanaClient
    config: AutomationConfig
    depth: int = 0
    visited: set[tuple[str, str]] = field(default_factory=set)
    save_result: SaveResult | None = None

    def can_continue(self, entity_gid: str, rule_id: str) -> bool:
        """Check if automation can continue without loop.

        Per FR-011/FR-012: Depth and visited set tracking.

        Args:
            entity_gid: GID of entity being processed
            rule_id: ID of rule to execute

        Returns:
            True if safe to continue, False if would loop
        """
        # Check depth limit
        if self.depth >= self.config.max_cascade_depth:
            return False

        # Check visited set
        key = (entity_gid, rule_id)
        if key in self.visited:
            return False

        return True

    def mark_visited(self, entity_gid: str, rule_id: str) -> None:
        """Mark entity/rule pair as visited.

        Args:
            entity_gid: GID of entity being processed
            rule_id: ID of rule executed
        """
        self.visited.add((entity_gid, rule_id))

    def child_context(self) -> AutomationContext:
        """Create child context with incremented depth.

        Returns:
            New AutomationContext with depth + 1, shared visited set
        """
        return AutomationContext(
            client=self.client,
            config=self.config,
            depth=self.depth + 1,
            visited=self.visited,  # Shared reference
            save_result=self.save_result,
        )
```

#### AutomationResult

```python
from dataclasses import dataclass, field

@dataclass
class AutomationResult:
    """Result of automation rule execution.

    Per FR-007: Included in SaveResult after automation.

    Attributes:
        rule_id: Unique identifier of the rule that executed
        rule_name: Human-readable rule name
        triggered_by_gid: GID of entity that triggered the rule
        triggered_by_type: Type name of triggering entity
        actions_executed: List of action type names executed
        entities_created: GIDs of newly created entities
        entities_updated: GIDs of entities that were updated
        success: True if all actions succeeded
        error: Error message if failed (per Open Question 2)
        execution_time_ms: Time taken to execute rule
        skipped_reason: Reason if rule was skipped (e.g., "circular_reference_prevented")
    """

    rule_id: str
    rule_name: str
    triggered_by_gid: str
    triggered_by_type: str
    actions_executed: list[str] = field(default_factory=list)
    entities_created: list[str] = field(default_factory=list)
    entities_updated: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    execution_time_ms: float = 0.0
    skipped_reason: str | None = None

    def __repr__(self) -> str:
        """Return string representation."""
        status = "success" if self.success else f"failed: {self.error}"
        if self.skipped_reason:
            status = f"skipped: {self.skipped_reason}"
        return f"AutomationResult({self.rule_name}, {status})"

    @property
    def was_skipped(self) -> bool:
        """True if rule was skipped (loop prevention, etc.)."""
        return self.skipped_reason is not None
```

#### SaveResult Extension

```python
@dataclass
class SaveResult:
    """Result of a commit operation.

    Extended per FR-007 for automation results.
    """

    succeeded: list[AsanaResource] = field(default_factory=list)
    failed: list[SaveError] = field(default_factory=list)
    action_results: list[ActionResult] = field(default_factory=list)
    cascade_results: list[CascadeResult] = field(default_factory=list)
    healing_report: HealingReport | None = None
    automation_results: list[AutomationResult] = field(default_factory=list)  # NEW

    @property
    def automation_succeeded(self) -> int:
        """Count of successful automation rule executions."""
        return sum(1 for r in self.automation_results if r.success and not r.was_skipped)

    @property
    def automation_failed(self) -> int:
        """Count of failed automation rule executions."""
        return sum(1 for r in self.automation_results if not r.success)

    @property
    def automation_skipped(self) -> int:
        """Count of skipped automation rules (loop prevention)."""
        return sum(1 for r in self.automation_results if r.was_skipped)
```

### API Contracts

#### AutomationEngine

```python
from typing import Callable

class AutomationEngine:
    """Orchestrates automation rule evaluation and execution.

    Per FR-001: Evaluates registered rules after SaveSession commit.

    The engine maintains a registry of rules and evaluates them against
    committed entities. Rules are evaluated in registration order.

    Example:
        engine = AutomationEngine(config)
        engine.register(PipelineConversionRule())
        engine.register(custom_rule)

        # Called by SaveSession after commit
        results = await engine.evaluate_async(save_result, context)
    """

    def __init__(self, config: AutomationConfig) -> None:
        """Initialize automation engine.

        Args:
            config: AutomationConfig with settings
        """
        self._config = config
        self._rules: list[AutomationRule] = []
        self._enabled = config.enabled

    def register(self, rule: AutomationRule) -> None:
        """Register an automation rule.

        Per FR-008: Rule registry for custom rules.

        Args:
            rule: AutomationRule implementation

        Raises:
            ValueError: If rule with same ID already registered
        """
        for existing in self._rules:
            if existing.id == rule.id:
                raise ValueError(f"Rule with ID '{rule.id}' already registered")
        self._rules.append(rule)

    def unregister(self, rule_id: str) -> bool:
        """Unregister a rule by ID.

        Args:
            rule_id: ID of rule to remove

        Returns:
            True if rule was found and removed, False otherwise
        """
        for i, rule in enumerate(self._rules):
            if rule.id == rule_id:
                del self._rules[i]
                return True
        return False

    @property
    def rules(self) -> list[AutomationRule]:
        """Get list of registered rules (read-only copy)."""
        return list(self._rules)

    async def evaluate_async(
        self,
        save_result: SaveResult,
        client: AsanaClient,
    ) -> list[AutomationResult]:
        """Evaluate all rules against committed entities.

        Per FR-001: Called after SaveSession commit completes.
        Per NFR-003: Failures do not propagate (isolated execution).

        Args:
            save_result: SaveResult from completed commit
            client: AsanaClient for rule execution

        Returns:
            List of AutomationResult for each rule evaluated
        """
        if not self._enabled:
            return []

        results: list[AutomationResult] = []
        context = AutomationContext(
            client=client,
            config=self._config,
            depth=0,
            visited=set(),
            save_result=save_result,
        )

        for entity in save_result.succeeded:
            # Detect event type from entity state
            event = self._detect_event(entity, save_result)
            event_context = self._build_event_context(entity, event, save_result)

            for rule in self._rules:
                # Check if rule should trigger
                if not rule.should_trigger(entity, event, event_context):
                    continue

                # Check loop prevention
                if not context.can_continue(entity.gid, rule.id):
                    results.append(AutomationResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        triggered_by_gid=entity.gid,
                        triggered_by_type=type(entity).__name__,
                        success=True,
                        skipped_reason="circular_reference_prevented",
                    ))
                    continue

                # Execute rule with isolation
                context.mark_visited(entity.gid, rule.id)
                try:
                    result = await rule.execute_async(entity, context)
                    results.append(result)
                except Exception as e:
                    # Per NFR-003: Capture failure, don't propagate
                    results.append(AutomationResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        triggered_by_gid=entity.gid,
                        triggered_by_type=type(entity).__name__,
                        success=False,
                        error=str(e),
                    ))

        return results

    def _detect_event(self, entity: AsanaResource, result: SaveResult) -> str:
        """Detect event type for entity."""
        # Check action_results for section changes
        for action in result.action_results:
            if (action.entity_gid == entity.gid and
                action.action_type == ActionType.MOVE_TO_SECTION and
                action.success):
                return "section_changed"

        # Check entity state
        if hasattr(entity, "_is_new") and entity._is_new:
            return "created"

        return "updated"

    def _build_event_context(
        self,
        entity: AsanaResource,
        event: str,
        result: SaveResult,
    ) -> dict[str, Any]:
        """Build context dict for event matching."""
        context: dict[str, Any] = {"event": event}

        if event == "section_changed":
            # Find section from action results
            for action in result.action_results:
                if (action.entity_gid == entity.gid and
                    action.action_type == ActionType.MOVE_TO_SECTION):
                    # Get section name and normalize
                    section_gid = action.target_gid
                    # Resolve section name (cached via NameResolver)
                    section = ProcessSection.from_name(action.extra.get("section_name"))
                    if section:
                        context["section"] = section.value

        # Add entity-specific context
        if hasattr(entity, "process_type"):
            context["process_type"] = entity.process_type.value

        return context
```

#### TemplateDiscovery

```python
class TemplateDiscovery:
    """Discovers template sections and processes in target projects.

    Per FR-004: Template discovery with fuzzy matching.
    Per Open Question 4: Template sections contain "template" (case-insensitive).

    Template discovery finds a "Template" section in the target project
    and returns tasks within it that can be cloned for new processes.
    """

    TEMPLATE_PATTERNS = ["template", "templates", "template tasks"]

    def __init__(self, client: AsanaClient) -> None:
        """Initialize template discovery.

        Args:
            client: AsanaClient for API operations
        """
        self._client = client

    async def find_template_section_async(
        self,
        project_gid: str,
    ) -> Section | None:
        """Find template section in project.

        Per Open Question 4: Section name contains "template" (case-insensitive).

        Args:
            project_gid: GID of project to search

        Returns:
            Section if found, None otherwise
        """
        sections = await self._client.sections.list_async(project_gid)

        for section in sections:
            section_name_lower = section.name.lower()
            for pattern in self.TEMPLATE_PATTERNS:
                if pattern in section_name_lower:
                    return section

        return None

    async def find_template_task_async(
        self,
        project_gid: str,
        template_name: str | None = None,
    ) -> Task | None:
        """Find template task in project's template section.

        Args:
            project_gid: GID of project to search
            template_name: Optional specific template name to match

        Returns:
            Task suitable for cloning, or None if not found
        """
        section = await self.find_template_section_async(project_gid)
        if section is None:
            return None

        # Get tasks in template section
        tasks = await self._client.tasks.list_for_section_async(section.gid)

        if not tasks:
            return None

        if template_name:
            # Find specific template by name (case-insensitive)
            template_name_lower = template_name.lower()
            for task in tasks:
                if task.name.lower() == template_name_lower:
                    return task
            return None

        # Return first task as default template
        return tasks[0]
```

#### FieldSeeder

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.models.business import Business, Unit, Process

class FieldSeeder:
    """Computes field values for new entities from hierarchy and carry-through.

    Per FR-005: Field seeding from Business/Unit cascade and source Process.
    Per Open Question 3: New FieldSeeder abstraction (more focused than BusinessSeeder).

    FieldSeeder computes field values by combining:
    1. Cascade fields: Business/Unit fields that cascade to descendants
    2. Carry-through fields: Fields copied from source Process
    3. Computed fields: Values derived at runtime (e.g., due dates)
    """

    # Cascade fields from Business
    BUSINESS_CASCADE_FIELDS = [
        "Office Phone",
        "Company ID",
        "Business Name",
        "Primary Contact Phone",
    ]

    # Cascade fields from Unit
    UNIT_CASCADE_FIELDS = [
        "Vertical",
        "Platforms",
        "Booking Type",
    ]

    # Carry-through fields from source Process
    PROCESS_CARRY_THROUGH_FIELDS = [
        "Contact Phone",
        "Priority",
        "Assigned To",
    ]

    def __init__(self, client: AsanaClient) -> None:
        """Initialize field seeder.

        Args:
            client: AsanaClient for field resolution
        """
        self._client = client

    async def cascade_from_hierarchy_async(
        self,
        business: Business | None,
        unit: Unit | None,
    ) -> dict[str, Any]:
        """Compute cascade field values from Business/Unit hierarchy.

        Args:
            business: Business entity (optional)
            unit: Unit entity (optional)

        Returns:
            Dict of field_name -> value for cascade fields
        """
        fields: dict[str, Any] = {}

        if business:
            # Cascade from Business
            if business.office_phone:
                fields["Office Phone"] = business.office_phone
            if business.company_id:
                fields["Company ID"] = business.company_id
            if business.name:
                fields["Business Name"] = business.name
            if business.primary_contact_phone:
                fields["Primary Contact Phone"] = business.primary_contact_phone

        if unit:
            # Cascade from Unit (may override Business values)
            if unit.vertical:
                fields["Vertical"] = unit.vertical.value if hasattr(unit.vertical, "value") else unit.vertical
            if unit.platforms:
                fields["Platforms"] = unit.platforms
            if unit.booking_type:
                fields["Booking Type"] = unit.booking_type

        return fields

    async def carry_through_from_process_async(
        self,
        source_process: Process,
    ) -> dict[str, Any]:
        """Compute carry-through field values from source Process.

        Args:
            source_process: Process being converted

        Returns:
            Dict of field_name -> value for carry-through fields
        """
        fields: dict[str, Any] = {}

        # Get contact phone from source
        if hasattr(source_process, "contact_phone") and source_process.contact_phone:
            fields["Contact Phone"] = source_process.contact_phone

        # Get priority
        if source_process.priority:
            fields["Priority"] = source_process.priority.value if hasattr(source_process.priority, "value") else source_process.priority

        # Get assigned user
        if source_process.assigned_to:
            fields["Assigned To"] = source_process.assigned_to

        return fields

    async def compute_fields_async(
        self,
        source_process: Process,
    ) -> dict[str, Any]:
        """Compute derived field values.

        Args:
            source_process: Process being converted

        Returns:
            Dict of field_name -> computed value
        """
        import arrow

        fields: dict[str, Any] = {}

        # Set started_at to current date
        fields["Started At"] = arrow.now().format("YYYY-MM-DD")

        return fields

    async def seed_fields_async(
        self,
        business: Business | None,
        unit: Unit | None,
        source_process: Process,
    ) -> dict[str, Any]:
        """Compute all seeded fields for a new Process.

        Combines cascade, carry-through, and computed fields.

        Args:
            business: Business entity (optional)
            unit: Unit entity (optional)
            source_process: Process being converted

        Returns:
            Dict of field_name -> value for all seeded fields
        """
        fields: dict[str, Any] = {}

        # Layer 1: Cascade from hierarchy
        cascade_fields = await self.cascade_from_hierarchy_async(business, unit)
        fields.update(cascade_fields)

        # Layer 2: Carry-through from source (may override)
        carry_through_fields = await self.carry_through_from_process_async(source_process)
        fields.update(carry_through_fields)

        # Layer 3: Computed fields
        computed_fields = await self.compute_fields_async(source_process)
        fields.update(computed_fields)

        return fields
```

#### PipelineConversionRule

```python
import time
from typing import Any

from autom8_asana.automation.base import AutomationRule, TriggerCondition, Action
from autom8_asana.automation.context import AutomationContext
from autom8_asana.automation.templates import TemplateDiscovery
from autom8_asana.automation.seeding import FieldSeeder
from autom8_asana.models.business.process import Process, ProcessSection, ProcessType
from autom8_asana.persistence.models import AutomationResult

class PipelineConversionRule(AutomationRule):
    """Built-in rule for Sales -> Onboarding pipeline conversion.

    Per FR-003: Triggers when Process section changes to CONVERTED.
    Per FR-004: Uses template discovery for target project.
    Per FR-005: Seeds fields from hierarchy and carry-through.

    This rule automates the common workflow where a Sales Process
    converting triggers creation of an Onboarding Process.
    """

    def __init__(
        self,
        source_type: ProcessType = ProcessType.SALES,
        target_type: ProcessType = ProcessType.ONBOARDING,
        trigger_section: ProcessSection = ProcessSection.CONVERTED,
    ) -> None:
        """Initialize pipeline conversion rule.

        Args:
            source_type: Source ProcessType (default: SALES)
            target_type: Target ProcessType (default: ONBOARDING)
            trigger_section: Section that triggers conversion (default: CONVERTED)
        """
        self._source_type = source_type
        self._target_type = target_type
        self._trigger_section = trigger_section

    @property
    def id(self) -> str:
        """Unique rule identifier."""
        return f"pipeline_{self._source_type.value}_to_{self._target_type.value}"

    @property
    def name(self) -> str:
        """Human-readable rule name."""
        return f"Pipeline: {self._source_type.value.title()} to {self._target_type.value.title()}"

    @property
    def trigger(self) -> TriggerCondition:
        """Trigger condition for this rule."""
        return TriggerCondition(
            entity_type="Process",
            event="section_changed",
            filters={
                "section": self._trigger_section.value,
                "process_type": self._source_type.value,
            },
        )

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Check if rule should trigger.

        Args:
            entity: The entity that triggered the event
            event: The event type
            context: Event context

        Returns:
            True if should trigger
        """
        # Must be a Process
        if not isinstance(entity, Process):
            return False

        # Must be section_changed event
        if event != "section_changed":
            return False

        # Must be correct source process type
        if entity.process_type != self._source_type:
            return False

        # Must be moving to trigger section
        section = context.get("section")
        if section != self._trigger_section.value:
            return False

        return True

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult:
        """Execute pipeline conversion.

        Args:
            entity: Process that triggered the rule
            context: Automation execution context

        Returns:
            AutomationResult with execution details
        """
        start_time = time.perf_counter()
        process = entity  # Type narrowing (we know it's Process)

        try:
            # Get target project GID from config
            target_project_gid = context.config.pipeline_templates.get(
                self._target_type.value
            )
            if not target_project_gid:
                return AutomationResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    triggered_by_gid=process.gid,
                    triggered_by_type="Process",
                    success=False,
                    error=f"No target project configured for {self._target_type.value}",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                )

            # Discover template in target project
            discovery = TemplateDiscovery(context.client)
            template_task = await discovery.find_template_task_async(target_project_gid)

            if not template_task:
                return AutomationResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    triggered_by_gid=process.gid,
                    triggered_by_type="Process",
                    success=False,
                    error=f"No template found in project {target_project_gid}",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                )

            # Load hierarchy for field seeding
            business = await process.business_async if hasattr(process, "business_async") else None
            unit = await process.unit_async if hasattr(process, "unit_async") else None

            # Compute seeded fields
            seeder = FieldSeeder(context.client)
            seeded_fields = await seeder.seed_fields_async(business, unit, process)

            # Clone template task as new Process
            new_task = await context.client.tasks.duplicate_async(
                template_task.gid,
                name=f"{process.name} - {self._target_type.value.title()}",
            )

            # Apply seeded fields to new task
            # (This uses the custom field update pattern from existing SDK)
            await self._apply_seeded_fields(context.client, new_task.gid, seeded_fields)

            # Move to appropriate section (not Template)
            # Find first non-template section
            sections = await context.client.sections.list_async(target_project_gid)
            target_section = None
            for section in sections:
                if "template" not in section.name.lower():
                    target_section = section
                    break

            if target_section:
                await context.client.tasks.add_to_section_async(
                    new_task.gid,
                    section_gid=target_section.gid,
                )

            return AutomationResult(
                rule_id=self.id,
                rule_name=self.name,
                triggered_by_gid=process.gid,
                triggered_by_type="Process",
                actions_executed=["discover_template", "clone_task", "seed_fields", "move_to_section"],
                entities_created=[new_task.gid],
                success=True,
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        except Exception as e:
            return AutomationResult(
                rule_id=self.id,
                rule_name=self.name,
                triggered_by_gid=process.gid,
                triggered_by_type="Process",
                success=False,
                error=str(e),
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    async def _apply_seeded_fields(
        self,
        client: AsanaClient,
        task_gid: str,
        fields: dict[str, Any],
    ) -> None:
        """Apply seeded fields to a task.

        Args:
            client: AsanaClient for updates
            task_gid: GID of task to update
            fields: Field name -> value mapping
        """
        # Resolve field names to GIDs and update
        # This leverages existing custom field infrastructure
        if not fields:
            return

        # Build custom_fields payload
        custom_fields: dict[str, Any] = {}
        for field_name, value in fields.items():
            # Resolve field name to GID (uses NameResolver cache)
            try:
                field_gid = await client.name_resolver.resolve_custom_field_async(field_name)
                custom_fields[field_gid] = value
            except Exception:
                # Skip fields that can't be resolved
                pass

        if custom_fields:
            await client.tasks.update_async(task_gid, custom_fields=custom_fields)
```

### Integration Points

#### SaveSession Integration

```python
# In session.py

from autom8_asana.persistence.events import PostCommitHook

class SaveSession:
    def __init__(
        self,
        client: AsanaClient,
        batch_size: int = 10,
        max_concurrent: int = 15,
        auto_heal: bool = False,
        automation_enabled: bool | None = None,  # NEW: Per-session override
    ) -> None:
        # ... existing init ...
        self._automation_enabled = (
            automation_enabled
            if automation_enabled is not None
            else client._config.automation.enabled
        )

    def on_post_commit(
        self,
        func: PostCommitHook,
    ) -> Callable[..., Any]:
        """Register post-commit hook (decorator).

        Per FR-002: Post-commit hooks receive SaveResult.

        Post-commit hooks are called after the entire commit operation
        completes, including CRUD, actions, cascades, and healing.
        They receive the full SaveResult for inspection.

        Args:
            func: Hook function receiving (SaveResult). Can be sync or async.

        Returns:
            The decorated function.

        Example:
            @session.on_post_commit
            async def log_automation(result: SaveResult) -> None:
                for auto_result in result.automation_results:
                    logger.info("Rule %s: %s", auto_result.rule_name, auto_result.success)
        """
        return self._events.register_post_commit(func)

    async def commit_async(self) -> SaveResult:
        """Commit all pending changes.

        Extended per FR-001 for Phase 5: Automation.
        """
        # ... existing Phase 1-4 ...

        # Phase 5: Automation (NEW)
        if self._automation_enabled and self._client.automation:
            try:
                automation_results = await self._client.automation.evaluate_async(
                    crud_result,
                    self._client,
                )
                crud_result.automation_results = automation_results
            except Exception as e:
                # Per NFR-003: Automation failures don't fail commit
                logger.warning("Automation evaluation failed: %s", e)

        # Emit post-commit hooks
        await self._events.emit_post_commit(crud_result)

        return crud_result
```

#### EventSystem Extension

```python
# In events.py

from autom8_asana.persistence.models import SaveResult

PostCommitHook = (
    Callable[[SaveResult], None]
    | Callable[[SaveResult], Coroutine[Any, Any, None]]
)

class EventSystem:
    def __init__(self) -> None:
        self._pre_save_hooks: list[PreSaveHook] = []
        self._post_save_hooks: list[PostSaveHook] = []
        self._error_hooks: list[ErrorHook] = []
        self._post_commit_hooks: list[PostCommitHook] = []  # NEW

    def register_post_commit(
        self,
        func: PostCommitHook,
    ) -> Callable[..., Any]:
        """Register post-commit hook.

        Per FR-002: Called after entire commit completes with SaveResult.
        """
        self._post_commit_hooks.append(func)
        return func

    async def emit_post_commit(self, result: SaveResult) -> None:
        """Emit post-commit event with full SaveResult.

        Post-commit hooks cannot fail the commit (it already succeeded).
        All exceptions are swallowed.
        """
        for hook in self._post_commit_hooks:
            try:
                hook_result = hook(result)
                if asyncio.iscoroutine(hook_result):
                    await hook_result
            except Exception:
                # Post-commit hooks should not fail
                pass

    def clear_hooks(self) -> None:
        """Clear all registered hooks."""
        self._pre_save_hooks.clear()
        self._post_save_hooks.clear()
        self._error_hooks.clear()
        self._post_commit_hooks.clear()  # NEW
```

#### AsanaConfig Integration

```python
# In config.py

from autom8_asana.automation.config import AutomationConfig

@dataclass
class AsanaConfig:
    """Main configuration for AsanaClient."""

    base_url: str = "https://app.asana.com/api/1.0"
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)  # NEW
    token_key: str = "ASANA_PAT"
```

#### AsanaClient Integration

```python
# In client.py

class AsanaClient:
    def __init__(
        self,
        token: str | None = None,
        *,
        workspace_gid: str | None = None,
        auth_provider: AuthProvider | None = None,
        cache_provider: CacheProvider | None = None,
        log_provider: LogProvider | None = None,
        config: AsanaConfig | None = None,
        observability_hook: ObservabilityHook | None = None,
    ) -> None:
        self._config = config or AsanaConfig()
        # ... existing init ...

        # Initialize automation engine
        self._automation: AutomationEngine | None = None
        if self._config.automation.enabled:
            from autom8_asana.automation.engine import AutomationEngine
            self._automation = AutomationEngine(self._config.automation)

    @property
    def automation(self) -> AutomationEngine | None:
        """Access automation engine for rule registration.

        Returns:
            AutomationEngine if enabled, None otherwise

        Example:
            client.automation.register(PipelineConversionRule())
        """
        return self._automation
```

### Data Flow

#### Pipeline Conversion Flow

```
+-----------------------------------------------------------------------------------+
|                          Sales Process Converts                                    |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 1. External webhook triggers SDK                                                  |
|    - Receives: task_gid, section change event                                     |
|    - Loads: Sales Process with hydration                                          |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 2. SaveSession tracks section change                                              |
|    session.track(sales_process)                                                   |
|    sales_process.move_to_section(ProcessSection.CONVERTED)                        |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 3. commit_async() executes                                                        |
|    Phase 1: CRUD - Updates Process task                                           |
|    Phase 2: Actions - Move to section via add_to_section API                      |
|    Phase 3: Cascades - (none in this flow)                                        |
|    Phase 4: Healing - (if auto_heal=True)                                         |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 4. Phase 5: Automation                                                            |
|    AutomationEngine.evaluate_async(save_result, client)                           |
|                                                                                   |
|    For each succeeded entity:                                                     |
|    - Detect event type (section_changed)                                          |
|    - Build event context (section=converted, process_type=sales)                  |
|    - Match against registered rules                                               |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 5. PipelineConversionRule matches                                                 |
|    trigger: entity_type=Process, event=section_changed,                           |
|             filters={section: converted, process_type: sales}                     |
|                                                                                   |
|    should_trigger() returns True                                                  |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 6. execute_async() runs                                                           |
|                                                                                   |
|    a. Get target project GID from config.pipeline_templates["onboarding"]         |
|                                                                                   |
|    b. TemplateDiscovery.find_template_task_async(project_gid)                     |
|       - Find section with "template" in name                                      |
|       - Return first task in template section                                     |
|                                                                                   |
|    c. Load hierarchy for seeding                                                  |
|       - business = await sales_process.business_async                             |
|       - unit = await sales_process.unit_async                                     |
|                                                                                   |
|    d. FieldSeeder.seed_fields_async(business, unit, sales_process)                |
|       - Cascade: Office Phone, Company ID, Business Name, Vertical                |
|       - Carry-through: Contact Phone, Priority, Assigned To                       |
|       - Computed: Started At = today                                              |
|                                                                                   |
|    e. Duplicate template task                                                     |
|       new_task = await client.tasks.duplicate_async(template.gid, name=...)       |
|                                                                                   |
|    f. Apply seeded fields                                                         |
|       await client.tasks.update_async(new_task.gid, custom_fields=...)            |
|                                                                                   |
|    g. Move to non-template section                                                |
|       await client.tasks.add_to_section_async(new_task.gid, section_gid=...)      |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 7. AutomationResult returned                                                      |
|    {                                                                              |
|      rule_id: "pipeline_sales_to_onboarding",                                     |
|      rule_name: "Pipeline: Sales to Onboarding",                                  |
|      triggered_by_gid: "1234567890123",                                           |
|      triggered_by_type: "Process",                                                |
|      actions_executed: ["discover_template", "clone_task", ...],                  |
|      entities_created: ["9876543210987"],                                         |
|      success: True,                                                               |
|      execution_time_ms: 250.5                                                     |
|    }                                                                              |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| 8. SaveResult.automation_results populated                                        |
|    Post-commit hooks fire with complete SaveResult                                |
|    Consumer receives full result for logging/observability                        |
+-----------------------------------------------------------------------------------+
```

#### Loop Prevention Flow

```
+-----------------------------------------------------------------------------------+
| AutomationContext initialized                                                     |
|   depth: 0                                                                        |
|   visited: set()                                                                  |
|   max_cascade_depth: 5                                                            |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| Rule A triggers on Process P1                                                     |
|                                                                                   |
| 1. context.can_continue(P1.gid, "rule_a") -> True                                 |
|    - depth (0) < max_cascade_depth (5)                                            |
|    - (P1.gid, "rule_a") not in visited                                            |
|                                                                                   |
| 2. context.mark_visited(P1.gid, "rule_a")                                         |
|    visited: {(P1.gid, "rule_a")}                                                  |
|                                                                                   |
| 3. Rule A executes, creates Process P2                                            |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| P2 creation triggers Rule B                                                       |
|                                                                                   |
| 1. child_context = context.child_context()                                        |
|    depth: 1                                                                       |
|    visited: {(P1.gid, "rule_a")}  (shared reference)                              |
|                                                                                   |
| 2. child_context.can_continue(P2.gid, "rule_b") -> True                           |
|                                                                                   |
| 3. child_context.mark_visited(P2.gid, "rule_b")                                   |
|    visited: {(P1.gid, "rule_a"), (P2.gid, "rule_b")}                              |
|                                                                                   |
| 4. Rule B executes, would create P1 (circular)                                    |
+-----------------------------------------------------------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------------------+
| Rule B would trigger Rule A on new P1                                             |
|                                                                                   |
| 1. child_context.can_continue(P1.gid, "rule_a") -> FALSE                          |
|    - (P1.gid, "rule_a") already in visited set                                    |
|                                                                                   |
| 2. Return AutomationResult with:                                                  |
|    skipped_reason: "circular_reference_prevented"                                 |
+-----------------------------------------------------------------------------------+
```

## Technical Decisions

| Decision | Choice | Rationale | ADR |
|----------|--------|-----------|-----|
| Async-only execution | V1 is async-only | Simplifies implementation; all SDK clients are async; sync wrapper pattern available if needed | Open Question 1 |
| Partial failure handling | Per-action success/failure in AutomationResult | Matches SaveResult pattern; allows consumers to inspect partial success | Open Question 2 |
| Field seeding abstraction | New FieldSeeder class | More focused than BusinessSeeder; clear separation of concerns | Open Question 3 |
| Template naming convention | Contains "template" (case-insensitive) | Matches existing project naming conventions; flexible | Open Question 4 |
| Post-commit hook location | EventSystem extension | Consistent with existing pre_save/post_save/error hooks; reuses event infrastructure | Discovery |
| Rule registry pattern | List with registration order | Simple; rules evaluated in order; custom rules can be prioritized | FR-008 |
| Loop prevention | Depth + visited set | Two-layer protection; depth prevents unbounded recursion; visited prevents same trigger twice | FR-011/FR-012 |

## Complexity Assessment

**Complexity Level**: Module

**Justification**:
- Clear module boundary (`automation/`) with well-defined public API
- Multiple components with distinct responsibilities
- Integration with existing SDK infrastructure (SaveSession, EventSystem)
- No external service dependencies beyond Asana API
- No persistence requirements (rules are registered at runtime)

**Why not Script?**
- Multiple interacting components (engine, rules, seeder, discovery)
- State management for loop prevention
- Integration points with SaveSession required

**Why not Service?**
- No independent deployment needed
- No cross-process coordination
- No complex configuration management beyond AutomationConfig

## Implementation Plan

### Phase 1: Core Infrastructure (Must-Have)

**Deliverables**:
- `automation/base.py`: AutomationRule protocol, TriggerCondition, Action
- `automation/config.py`: AutomationConfig dataclass
- `automation/context.py`: AutomationContext with loop prevention
- `automation/engine.py`: AutomationEngine with evaluate_async
- `persistence/models.py`: AutomationResult dataclass
- `persistence/events.py`: PostCommitHook type, emit_post_commit
- `persistence/session.py`: Phase 5 automation integration, on_post_commit

**Requirements Addressed**: FR-001, FR-002, FR-006, FR-007, FR-011, FR-012, NFR-003

**Estimate**: 6-8 hours

**Dependencies**: None (builds on existing EventSystem)

### Phase 2: Pipeline Conversion (Must-Have)

**Deliverables**:
- `automation/pipeline.py`: PipelineConversionRule implementation
- `automation/templates.py`: TemplateDiscovery service
- `automation/seeding.py`: FieldSeeder service

**Requirements Addressed**: FR-003, FR-004, FR-005

**Estimate**: 4-6 hours

**Dependencies**: Phase 1

### Phase 3: Extensibility (Should-Have)

**Deliverables**:
- Enhanced TriggerCondition with filter predicates
- Action type implementations (create_process, add_to_project, set_field)
- Rule enable/disable support
- AsanaConfig.automation integration
- client.automation property

**Requirements Addressed**: FR-008, FR-009, FR-010, FR-014

**Estimate**: 3-4 hours

**Dependencies**: Phase 1

### Phase 4: Advanced Features (Could-Have)

**Deliverables**:
- File-based rule configuration (YAML/JSON)
- Observability hooks for automation metrics
- Rule priority ordering

**Requirements Addressed**: FR-013, FR-015

**Estimate**: 4-6 hours

**Dependencies**: Phase 3

### Migration Strategy

1. **Non-breaking addition**: All new code; no changes to existing public APIs
2. **Opt-in activation**: AutomationConfig.enabled defaults to True but no rules registered by default
3. **Gradual adoption**: Consumers register rules as needed
4. **Testing compatibility**: Existing tests unaffected

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Circular trigger loops | High | Medium | Max cascade depth (FR-011), visited set tracking (FR-012), logging on skip |
| Rate limiting during cascades | Medium | Medium | Respect RateLimitConfig; batch operations where possible |
| Partial failures in multi-step automation | Medium | Medium | Per-action success/failure in AutomationResult; detailed logging |
| Section name mismatch in templates | Low | Low | Fuzzy matching with multiple patterns; clear error messages |
| Template task not found | Medium | Medium | Clear error in AutomationResult; consumer can add template |
| Field resolution failures | Low | Low | Skip unresolvable fields; log warning; continue execution |
| Performance regression from automation | Medium | Low | Async execution; benchmark tests; execution_time_ms tracking |

## Observability

### Metrics

- `automation.rules_registered` gauge: Number of registered rules
- `automation.evaluations_total` counter: Total rule evaluations
- `automation.executions_total` counter: Total rule executions (labeled by rule_id, success)
- `automation.skipped_total` counter: Skipped executions (labeled by reason)
- `automation.execution_duration_ms` histogram: Rule execution latency (labeled by rule_id)

### Logging

```python
# Rule registration (info)
logger.info("Registered automation rule: %s", rule.name,
            extra={"rule_id": rule.id, "trigger": str(rule.trigger)})

# Rule trigger (debug)
logger.debug("Rule %s triggered by %s", rule.name, entity.gid,
             extra={"rule_id": rule.id, "entity_type": type(entity).__name__})

# Rule execution success (info)
logger.info("Rule %s executed successfully", rule.name,
            extra={"rule_id": rule.id, "entities_created": result.entities_created,
                   "execution_time_ms": result.execution_time_ms})

# Rule execution failure (warning)
logger.warning("Rule %s execution failed: %s", rule.name, result.error,
               extra={"rule_id": rule.id, "triggered_by": result.triggered_by_gid})

# Rule skipped (debug)
logger.debug("Rule %s skipped: %s", rule.name, result.skipped_reason,
             extra={"rule_id": rule.id, "entity_gid": result.triggered_by_gid})

# Automation evaluation (debug)
logger.debug("Automation evaluation complete: %d rules, %d succeeded, %d failed, %d skipped",
             len(results), save_result.automation_succeeded,
             save_result.automation_failed, save_result.automation_skipped)
```

### Alerting

- Alert if automation.execution_duration_ms > 5000ms for any rule
- Alert if automation.skipped_total (reason=circular_reference) > 10 in 5 minutes
- Alert if automation.executions_total (success=false) > 5 in 5 minutes

## Testing Strategy

### Unit Tests

- AutomationConfig validation
- TriggerCondition.matches() with various entity/event combinations
- AutomationContext.can_continue() depth and visited checks
- AutomationEngine.register() and unregister()
- AutomationEngine.evaluate_async() with mock rules
- FieldSeeder cascade, carry-through, computed fields
- TemplateDiscovery section matching
- PipelineConversionRule.should_trigger() conditions

### Integration Tests

- Full Sales -> Onboarding pipeline conversion with mocked Asana API
- SaveSession Phase 5 execution
- Post-commit hook invocation
- Loop prevention across multiple rules
- Partial failure handling

### Performance Tests

- Single rule evaluation < 100ms (NFR-001)
- 10 rule registry with 100 entity evaluation < 1000ms
- Template discovery caching effectiveness

### Edge Case Tests

- No template section in target project
- Empty template section
- Missing pipeline_templates config
- Null/empty field values in seeding
- Circular rule references
- Max cascade depth reached

## Open Questions

| Question | Owner | Due Date | Resolution |
|----------|-------|----------|------------|
| ~~Async-only or sync support?~~ | Architect | TDD Session | Async-only for V1 (simplicity, all clients are async) |
| ~~Partial failures handling?~~ | Architect | TDD Session | Per-action success/failure in AutomationResult |
| ~~BusinessSeeder vs FieldSeeder?~~ | Architect | TDD Session | New FieldSeeder (more focused, clear separation) |
| ~~Template naming convention?~~ | Product | TDD Session | Contains "template" (case-insensitive) |

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-18 | Architect | Initial design based on PRD-AUTOMATION-LAYER |
