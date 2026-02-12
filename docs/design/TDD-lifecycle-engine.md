# TDD: Lifecycle Engine

**Date**: 2026-02-11
**Status**: Design Complete
**Architect**: Moonshot Architect
**ADRs**: ADR-004, ADR-006, ADR-007, ADR-008
**Depends On**: TDD-resolution-primitives (Phase 1)
**Implements**: Workflow Resolution Platform -- Phase 2

---

## 1. Overview

This TDD defines the lifecycle engine that automates pipeline state transitions, entity creation, dependency wiring, and cascading section updates. It absorbs the existing PipelineConversionRule and provides the foundation for all future lifecycle workflows.

### 1.1 Design Principles

1. **Data-driven routing**: Pipeline DAG defined in YAML, not subclasses
2. **Multi-phase orchestration**: Create -> Configure -> Wire (Asana API requires valid GID before wiring)
3. **Engine delegates creation**: Entity model layer owns entity semantics
4. **Shared primitives**: Uses resolution system from Phase 1
5. **Forgiving**: Handle edge cases gracefully, do not punish users
6. **Idempotent**: Duplicate detection prevents re-creation on retry

### 1.2 File Locations

New files:

| File | Purpose |
|------|---------|
| `src/autom8_asana/lifecycle/__init__.py` | Package exports |
| `src/autom8_asana/lifecycle/engine.py` | LifecycleEngine (main orchestrator) |
| `src/autom8_asana/lifecycle/config.py` | StageConfig, DAG configuration loading |
| `src/autom8_asana/lifecycle/creation.py` | EntityCreationService |
| `src/autom8_asana/lifecycle/wiring.py` | DependencyWiringService |
| `src/autom8_asana/lifecycle/sections.py` | CascadingSectionService |
| `src/autom8_asana/lifecycle/completion.py` | PipelineAutoCompletionService |
| `src/autom8_asana/lifecycle/triggers.py` | AutomationTrigger, trigger types |
| `src/autom8_asana/lifecycle/dispatch.py` | AutomationDispatch (unified entry) |
| `src/autom8_asana/lifecycle/webhook.py` | FastAPI webhook handler |
| `config/lifecycle_stages.yaml` | Pipeline DAG configuration |
| `tests/unit/lifecycle/` | Unit tests |
| `tests/integration/lifecycle/` | Integration tests |

Modified files:

| File | Change |
|------|--------|
| `src/autom8_asana/models/business/process.py` | Add Month1, AccountError, Expansion to ProcessType |
| `src/autom8_asana/models/business/dna.py` | Add minimum viable fields (4 fields) |
| `src/autom8_asana/api/routes/` | Add webhook route |

---

## 2. ProcessType Expansion

Immediate prerequisite. Add missing enum values.

```python
# src/autom8_asana/models/business/process.py (modification)

class ProcessType(str, Enum):
    # Existing
    SALES = "sales"
    OUTREACH = "outreach"
    ONBOARDING = "onboarding"
    IMPLEMENTATION = "implementation"
    RETENTION = "retention"
    REACTIVATION = "reactivation"
    GENERIC = "generic"

    # New (required for lifecycle routing)
    MONTH1 = "month1"
    ACCOUNT_ERROR = "account_error"
    EXPANSION = "expansion"
```

Test impact: Existing tests use `ProcessType.SALES`, `ProcessType.ONBOARDING`, etc. Adding new members does not affect existing tests. New tests needed for the new enum values.

---

## 3. DNA Minimum Viable Modeling

Add 4 fields to the existing DNA stub. No behavioral methods.

```python
# src/autom8_asana/models/business/dna.py (modification)

from autom8_asana.models.business.descriptors import (
    EnumField,
    HolderRef,
    ParentRef,
    TextField,
)

class DNA(BusinessEntity):
    """DNA entity - child of DNAHolder.

    Per TDD-lifecycle-engine: Minimum viable modeling for lifecycle support.
    Adds 4 custom fields from production usage (dna_priority, intercom_link,
    tier_reached, automation).
    """

    _dna_holder: DNAHolder | None = PrivateAttr(default=None)
    _business: Business | None = PrivateAttr(default=None)

    # Navigation descriptors
    business = ParentRef["Business"](holder_attr="_dna_holder")
    dna_holder = HolderRef["DNAHolder"]()

    # Custom field descriptors (minimum viable for lifecycle)
    dna_priority = EnumField(field_name="DNA Priority")
    intercom_link = TextField(field_name="Intercom Link")
    tier_reached = EnumField(field_name="Tier Reached")
    automation = EnumField()
```

Test impact: DNA model currently has zero fields. Adding descriptors is additive. Existing tests that use DNA entities will continue to work because descriptors return None when the custom field is not present.

---

## 4. Stage Configuration

### 4.1 YAML Schema

```yaml
# config/lifecycle_stages.yaml

stages:
  sales:
    project_gid: "1200944186565610"
    pipeline_stage: 2
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0

    transitions:
      converted: onboarding
      did_not_convert: outreach

    cascading_sections:
      offer: "Sales Process"
      unit: "Next Steps"
      business: "OPPORTUNITY"

    init_actions: []

  outreach:
    project_gid: "1201753128450029"
    pipeline_stage: 1
    template_section: "TEMPLATES"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0

    transitions:
      converted: sales
      did_not_convert: outreach

    self_loop:
      max_iterations: 5

    cascading_sections:
      offer: "Sales Process"
      unit: "Engaged"
      business: "OPPORTUNITY"

    init_actions: []

  onboarding:
    project_gid: "1201319387632570"
    pipeline_stage: 3
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 14

    transitions:
      converted: implementation
      did_not_convert: sales

    cascading_sections:
      offer: "ACTIVATING"
      unit: "Onboarding"
      business: "ONBOARDING"

    init_actions:
      - type: products_check
        condition: "video*"
        action: request_source_videographer

  implementation:
    project_gid: "1201476141989746"
    pipeline_stage: 4
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 30

    transitions:
      converted: month1
      did_not_convert: sales

    cascading_sections:
      offer: "IMPLEMENTING"
      unit: "Implementing"
      business: "IMPLEMENTING"

    init_actions:
      - type: play_creation
        play_type: backend_onboard_a_business
        project_gid: "1207507299545000"
        condition: not_already_linked
      - type: entity_creation
        entity_type: asset_edit
        condition: not_already_linked

  month1:
    project_gid: null  # Uses existing pipeline config
    pipeline_stage: 5
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 30

    transitions:
      converted: null  # Terminal
      did_not_convert: null  # Terminal

    cascading_sections:
      offer: "STAGED"
      unit: "Month 1"
      business: "BUSINESSES"

    init_actions:
      - type: activate_campaign

  retention:
    project_gid: "1201346565918814"
    pipeline_stage: 1
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0

    transitions:
      converted: implementation
      did_not_convert: reactivation

    cascading_sections:
      unit: "Account Review"

    init_actions:
      - type: deactivate_campaign

  reactivation:
    project_gid: "1201265144487549"
    pipeline_stage: 2
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0

    transitions:
      converted: implementation
      did_not_convert: reactivation

    self_loop:
      max_iterations: 5
      delay_schedule: [90, 180, 360]

    cascading_sections:
      unit: "Paused"

    init_actions:
      - type: deactivate_campaign

  account_error:
    project_gid: "1201684018234520"
    pipeline_stage: 6
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0

    transitions:
      converted: null  # Terminal with activation
      did_not_convert: retention

    cascading_sections:
      offer: "ACCOUNT ERROR"
      unit: "Account Error"

    init_actions:
      - type: deactivate_campaign

  expansion:
    project_gid: "1201265144487557"
    pipeline_stage: 6
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0

    transitions:
      converted: null
      did_not_convert: null

    cascading_sections: {}
    init_actions: []

# Dependency wiring rules
dependency_wiring:
  pipeline_default:
    dependents:
      - entity_type: unit
      - entity_type: offer_holder
    dependencies:
      - source: dna_holder
        filter: open_plays

  backend_onboard_a_business:
    dependency_of: implementation

  asset_edit:
    dependency_of: implementation
```

### 4.2 Config Model

```python
# src/autom8_asana/lifecycle/config.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SelfLoopConfig:
    """Configuration for self-loop stages (Outreach, Reactivation)."""
    max_iterations: int = 5
    delay_schedule: list[int] = field(default_factory=list)  # days


@dataclass(frozen=True)
class InitActionConfig:
    """Configuration for init-time actions on a stage."""
    type: str
    condition: str | None = None
    play_type: str | None = None
    project_gid: str | None = None
    entity_type: str | None = None
    action: str | None = None


@dataclass(frozen=True)
class CascadingSectionConfig:
    """Sections to set on related entities during stage init."""
    offer: str | None = None
    unit: str | None = None
    business: str | None = None


@dataclass(frozen=True)
class TransitionConfig:
    """Transition routing for a stage."""
    converted: str | None = None          # target stage name or None
    did_not_convert: str | None = None    # target stage name or None


@dataclass(frozen=True)
class StageConfig:
    """Complete configuration for a lifecycle stage.

    Loaded from lifecycle_stages.yaml.
    """
    name: str
    project_gid: str | None
    pipeline_stage: int
    template_section: str
    target_section: str
    due_date_offset_days: int
    transitions: TransitionConfig
    cascading_sections: CascadingSectionConfig
    init_actions: list[InitActionConfig] = field(default_factory=list)
    self_loop: SelfLoopConfig | None = None

    # Field seeding configuration (from existing PipelineStage)
    business_cascade_fields: list[str] | None = None
    unit_cascade_fields: list[str] | None = None
    process_carry_through_fields: list[str] | None = None
    field_name_mapping: dict[str, str] | None = None
    assignee_gid: str | None = None


@dataclass(frozen=True)
class WiringRuleConfig:
    """Dependency wiring rule."""
    dependents: list[dict[str, str]] = field(default_factory=list)
    dependencies: list[dict[str, str]] = field(default_factory=list)
    dependency_of: str | None = None


class LifecycleConfig:
    """Loads and provides access to lifecycle stage configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._stages: dict[str, StageConfig] = {}
        self._wiring_rules: dict[str, WiringRuleConfig] = {}
        if config_path:
            self._load(config_path)

    def _load(self, path: Path) -> None:
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        for name, stage_data in data.get("stages", {}).items():
            self._stages[name] = self._parse_stage(name, stage_data)

        for name, rule_data in data.get("dependency_wiring", {}).items():
            self._wiring_rules[name] = self._parse_wiring(rule_data)

    def get_stage(self, name: str) -> StageConfig | None:
        """Get stage configuration by name."""
        return self._stages.get(name)

    def get_target_stage(
        self,
        source_stage: str,
        outcome: str,
    ) -> StageConfig | None:
        """Get target stage for a transition.

        Args:
            source_stage: Current stage name (e.g., "sales").
            outcome: Transition outcome ("converted" or "did_not_convert").

        Returns:
            Target StageConfig, or None if terminal.
        """
        source = self._stages.get(source_stage)
        if source is None:
            return None

        target_name = getattr(source.transitions, outcome, None)
        if target_name is None:
            return None

        return self._stages.get(target_name)

    def get_wiring_rules(self, entity_type: str) -> WiringRuleConfig | None:
        """Get wiring rules for an entity type."""
        return self._wiring_rules.get(entity_type)

    def _parse_stage(self, name: str, data: dict[str, Any]) -> StageConfig:
        """Parse stage configuration from YAML dict."""
        transitions = TransitionConfig(
            converted=data.get("transitions", {}).get("converted"),
            did_not_convert=data.get("transitions", {}).get("did_not_convert"),
        )

        cascading = CascadingSectionConfig(
            offer=data.get("cascading_sections", {}).get("offer"),
            unit=data.get("cascading_sections", {}).get("unit"),
            business=data.get("cascading_sections", {}).get("business"),
        )

        init_actions = [
            InitActionConfig(**action)
            for action in data.get("init_actions", [])
        ]

        self_loop = None
        if "self_loop" in data:
            self_loop = SelfLoopConfig(**data["self_loop"])

        return StageConfig(
            name=name,
            project_gid=data.get("project_gid"),
            pipeline_stage=data.get("pipeline_stage", 0),
            template_section=data.get("template_section", "TEMPLATE"),
            target_section=data.get("target_section", "OPPORTUNITY"),
            due_date_offset_days=data.get("due_date_offset_days", 0),
            transitions=transitions,
            cascading_sections=cascading,
            init_actions=init_actions,
            self_loop=self_loop,
        )

    def _parse_wiring(self, data: dict[str, Any]) -> WiringRuleConfig:
        """Parse wiring rule from YAML dict."""
        return WiringRuleConfig(
            dependents=data.get("dependents", []),
            dependencies=data.get("dependencies", []),
            dependency_of=data.get("dependency_of"),
        )
```

---

## 5. Lifecycle Engine

### 5.1 Core Engine

```python
# src/autom8_asana/lifecycle/engine.py

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.lifecycle.config import LifecycleConfig, StageConfig
from autom8_asana.lifecycle.creation import EntityCreationService
from autom8_asana.lifecycle.completion import PipelineAutoCompletionService
from autom8_asana.lifecycle.sections import CascadingSectionService
from autom8_asana.lifecycle.wiring import DependencyWiringService
from autom8_asana.models.business.process import ProcessSection, ProcessType
from autom8_asana.persistence.models import AutomationResult
from autom8_asana.resolution.context import ResolutionContext

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.process import Process

logger = get_logger(__name__)


class LifecycleEngine:
    """Orchestrates pipeline lifecycle transitions.

    Handles:
    - CONVERTED transitions (create next stage process)
    - DID NOT CONVERT transitions (route to fallback stage)
    - Cascading section updates (Offer, Unit, Business)
    - Pipeline auto-completion (earlier stages completed)
    - Entity creation (Play, AssetEdit, SourceVideographer)
    - Dependency wiring (post-creation)

    Uses resolution primitives (Phase 1) for all entity access.
    """

    def __init__(
        self,
        client: AsanaClient,
        config: LifecycleConfig,
    ) -> None:
        self._client = client
        self._config = config
        self._creation_service = EntityCreationService(client, config)
        self._wiring_service = DependencyWiringService(client, config)
        self._section_service = CascadingSectionService(client)
        self._completion_service = PipelineAutoCompletionService(client)

    async def handle_transition_async(
        self,
        source_process: Process,
        outcome: str,
    ) -> AutomationResult:
        """Handle a pipeline stage transition.

        This is the main entry point for lifecycle automation.

        Args:
            source_process: Process that transitioned (moved to CONVERTED or DID NOT CONVERT).
            outcome: "converted" or "did_not_convert".

        Returns:
            AutomationResult with execution details.
        """
        start_time = time.perf_counter()
        actions_executed: list[str] = []
        entities_created: list[str] = []
        entities_updated: list[str] = []

        try:
            # Determine source stage from process type
            source_stage_name = source_process.process_type.value
            source_stage = self._config.get_stage(source_stage_name)

            if source_stage is None:
                return self._failure_result(
                    f"No stage config for process type: {source_stage_name}",
                    source_process,
                    start_time,
                )

            # Determine target stage
            target_stage = self._config.get_target_stage(
                source_stage_name, outcome
            )

            if target_stage is None:
                # Terminal state (e.g., Month1 CONVERTED) -- handle terminal actions
                return await self._handle_terminal_async(
                    source_process, source_stage, outcome, start_time
                )

            # Self-loop check
            if target_stage.name == source_stage_name and source_stage.self_loop:
                iteration = await self._get_iteration_count_async(
                    source_process, source_stage_name
                )
                if iteration >= source_stage.self_loop.max_iterations:
                    return self._failure_result(
                        f"Self-loop max iterations reached: "
                        f"{iteration}/{source_stage.self_loop.max_iterations}",
                        source_process,
                        start_time,
                    )

            # Create resolution context
            async with ResolutionContext(
                self._client,
                trigger_entity=source_process,
            ) as ctx:
                # Phase 1: Create target process
                creation_result = await self._creation_service.create_process_async(
                    target_stage, ctx, source_process
                )

                if not creation_result.success:
                    return self._failure_result(
                        f"Process creation failed: {creation_result.error}",
                        source_process,
                        start_time,
                        actions_executed,
                    )

                entities_created.append(creation_result.entity_gid)
                actions_executed.append("create_process")

                # Phase 2: Cascading section updates
                section_result = await self._section_service.cascade_async(
                    target_stage.cascading_sections, ctx
                )
                if section_result.updates:
                    entities_updated.extend(section_result.updates)
                    actions_executed.append("cascade_sections")

                # Phase 3: Pipeline auto-completion
                if target_stage.pipeline_stage > source_stage.pipeline_stage:
                    completion_result = (
                        await self._completion_service.auto_complete_async(
                            source_process, target_stage.pipeline_stage, ctx
                        )
                    )
                    if completion_result.completed:
                        entities_updated.extend(completion_result.completed)
                        actions_executed.append("auto_complete")

                # Phase 4: Init actions (entity creation, products check, etc.)
                for init_action in target_stage.init_actions:
                    action_result = await self._execute_init_action_async(
                        init_action, creation_result.entity_gid, ctx
                    )
                    if action_result.success:
                        actions_executed.append(
                            f"init_{init_action.type}"
                        )
                        if action_result.entity_gid:
                            entities_created.append(action_result.entity_gid)

                # Phase 5: Dependency wiring (after all entities created)
                wiring_result = await self._wiring_service.wire_defaults_async(
                    creation_result.entity_gid,
                    target_stage.name,
                    ctx,
                )
                if wiring_result.wired:
                    actions_executed.append("wire_dependencies")

            return AutomationResult(
                rule_id=f"lifecycle_{source_stage_name}_to_{target_stage.name}",
                rule_name=f"Lifecycle: {source_stage_name.title()} to {target_stage.name.title()}",
                triggered_by_gid=source_process.gid,
                triggered_by_type="Process",
                actions_executed=actions_executed,
                entities_created=entities_created,
                entities_updated=entities_updated,
                success=True,
                execution_time_ms=self._elapsed_ms(start_time),
            )

        except Exception as e:
            logger.error(
                "lifecycle_transition_error",
                source_gid=source_process.gid,
                outcome=outcome,
                error=str(e),
            )
            return self._failure_result(
                str(e), source_process, start_time, actions_executed
            )

    async def _handle_terminal_async(
        self,
        source_process: Process,
        source_stage: StageConfig,
        outcome: str,
        start_time: float,
    ) -> AutomationResult:
        """Handle terminal state transitions (no target stage)."""
        actions_executed: list[str] = []

        # Terminal CONVERTED actions (e.g., Month1 -> Active)
        if outcome == "converted":
            for init_action in source_stage.init_actions:
                if init_action.type == "activate_campaign":
                    actions_executed.append("activate_campaign")

        return AutomationResult(
            rule_id=f"lifecycle_{source_stage.name}_terminal",
            rule_name=f"Lifecycle: {source_stage.name.title()} Terminal",
            triggered_by_gid=source_process.gid,
            triggered_by_type="Process",
            actions_executed=actions_executed,
            success=True,
            execution_time_ms=self._elapsed_ms(start_time),
        )

    def _elapsed_ms(self, start_time: float) -> float:
        return (time.perf_counter() - start_time) * 1000

    def _failure_result(
        self,
        error: str,
        process: Process,
        start_time: float,
        actions: list[str] | None = None,
    ) -> AutomationResult:
        return AutomationResult(
            rule_id="lifecycle_error",
            rule_name="Lifecycle Error",
            triggered_by_gid=process.gid,
            triggered_by_type="Process",
            actions_executed=actions or [],
            success=False,
            error=error,
            execution_time_ms=self._elapsed_ms(start_time),
        )
```

---

## 6. Entity Creation Service

```python
# src/autom8_asana/lifecycle/creation.py

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.seeding import FieldSeeder
from autom8_asana.automation.templates import TemplateDiscovery
from autom8_asana.automation.waiter import SubtaskWaiter
from autom8_asana.lifecycle.config import LifecycleConfig, StageConfig

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.process import Process
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


@dataclass
class CreationResult:
    """Result of entity creation."""
    success: bool
    entity_gid: str = ""
    error: str = ""


class EntityCreationService:
    """Creates entities during lifecycle transitions.

    Handles:
    - Template-based process creation (most entities)
    - Field seeding from hierarchy
    - Section placement
    - Due date setting
    - Hierarchy placement under ProcessHolder
    - Duplicate detection

    Uses existing infrastructure:
    - TemplateDiscovery: Find template tasks in target projects
    - FieldSeeder: Copy fields from hierarchy and source process
    - SubtaskWaiter: Wait for Asana async subtask creation
    """

    def __init__(
        self,
        client: AsanaClient,
        config: LifecycleConfig,
    ) -> None:
        self._client = client
        self._config = config

    async def create_process_async(
        self,
        stage_config: StageConfig,
        ctx: ResolutionContext,
        trigger_process: Process,
    ) -> CreationResult:
        """Create a new process entity from template.

        Multi-phase orchestration:
        1. RESOLVE: Get Business, Unit for context
        2. DUPLICATE CHECK: Ensure entity does not already exist
        3. CREATE: Duplicate template task
        4. CONFIGURE: Seed fields, place in hierarchy, set assignee
        """
        try:
            # Phase 1: Resolve context entities
            business = await ctx.business_async()
            unit = await ctx.unit_async()

            # Phase 2: Duplicate check
            if stage_config.project_gid:
                existing = await self._check_duplicate_async(
                    stage_config.project_gid,
                    business,
                    unit,
                )
                if existing:
                    logger.info(
                        "lifecycle_duplicate_detected",
                        project_gid=stage_config.project_gid,
                        existing_gid=existing,
                    )
                    return CreationResult(
                        success=True,
                        entity_gid=existing,
                    )

            # Phase 3: Create from template
            template_discovery = TemplateDiscovery(self._client)
            template = await template_discovery.find_template_task_async(
                stage_config.project_gid,
                template_section=stage_config.template_section,
            )

            if not template:
                return CreationResult(
                    success=False,
                    error=f"No template in project {stage_config.project_gid}",
                )

            # Generate name
            new_name = self._generate_name(
                template.name, business, unit
            )

            # Count subtasks for waiter
            template_subtasks = await self._client.tasks.subtasks_async(
                template.gid, opt_fields=["gid"]
            ).collect()

            # Duplicate template
            new_task = await self._client.tasks.duplicate_async(
                template.gid,
                name=new_name,
                include=["subtasks", "notes"],
            )

            # Add to project
            await self._client.tasks.add_to_project_async(
                new_task.gid, stage_config.project_gid
            )

            # Phase 4: Configure
            await self._configure_async(
                new_task, stage_config, ctx,
                trigger_process, business, unit,
                len(template_subtasks),
            )

            # Cache created entity in resolution context
            ctx.cache_entity(new_task)

            return CreationResult(
                success=True,
                entity_gid=new_task.gid,
            )

        except Exception as e:
            logger.error(
                "lifecycle_creation_error",
                stage=stage_config.name,
                error=str(e),
            )
            return CreationResult(success=False, error=str(e))

    async def _configure_async(
        self,
        new_task: Any,
        stage_config: StageConfig,
        ctx: ResolutionContext,
        trigger_process: Process,
        business: Any,
        unit: Any,
        expected_subtask_count: int,
    ) -> None:
        """Configure created entity: fields, section, due date, hierarchy."""
        from datetime import date, timedelta

        from autom8_asana.persistence.session import SaveSession

        # Move to target section
        if stage_config.target_section:
            sections = await self._client.sections.list_for_project_async(
                stage_config.project_gid
            ).collect()
            target = next(
                (s for s in sections
                 if s.name and s.name.lower() == stage_config.target_section.lower()),
                None,
            )
            if target:
                await self._client.sections.add_task_async(
                    target.gid, task=new_task.gid
                )

        # Set due date
        if stage_config.due_date_offset_days is not None:
            due_date = date.today() + timedelta(
                days=stage_config.due_date_offset_days
            )
            await self._client.tasks.update_async(
                new_task.gid, due_on=due_date.isoformat()
            )

        # Wait for subtasks
        if expected_subtask_count > 0:
            waiter = SubtaskWaiter(self._client)
            await waiter.wait_for_subtasks_async(
                new_task.gid,
                expected_count=expected_subtask_count,
                timeout=2.0,
            )

        # Seed fields
        field_seeder = FieldSeeder(
            self._client,
            business_cascade_fields=stage_config.business_cascade_fields,
            unit_cascade_fields=stage_config.unit_cascade_fields,
            process_carry_through_fields=stage_config.process_carry_through_fields,
        )
        seeded = await field_seeder.seed_fields_async(
            business=business,
            unit=unit,
            source_process=trigger_process,
        )
        if seeded:
            await field_seeder.write_fields_async(
                new_task.gid, seeded,
                field_name_mapping=stage_config.field_name_mapping,
            )

        # Hierarchy placement under ProcessHolder
        process_holder = trigger_process.process_holder
        if process_holder is not None:
            try:
                async with SaveSession(
                    self._client, automation_enabled=False
                ) as session:
                    session.set_parent(
                        new_task, process_holder,
                        insert_after=trigger_process,
                    )
                    await session.commit_async()
            except Exception as e:
                logger.warning(
                    "lifecycle_hierarchy_placement_failed",
                    task_gid=new_task.gid,
                    error=str(e),
                )

        # Set assignee from rep cascade
        await self._set_assignee_async(
            new_task, trigger_process, unit, business,
            stage_config.assignee_gid,
        )

    async def _check_duplicate_async(
        self,
        project_gid: str,
        business: Any,
        unit: Any,
    ) -> str | None:
        """Check if entity already exists in target project.

        Returns GID if found, None otherwise.
        """
        # List recent incomplete tasks in target project
        page_iter = self._client.tasks.list_for_project_async(
            project_gid,
            opt_fields=["name", "completed"],
            completed_since="now",
        )
        tasks = await page_iter.collect()

        business_name = getattr(business, "name", "") or ""
        for task in tasks:
            if business_name and business_name in (task.name or ""):
                if not task.completed:
                    return task.gid

        return None

    def _generate_name(
        self,
        template_name: str | None,
        business: Any,
        unit: Any,
    ) -> str:
        """Generate task name from template with placeholder replacement."""
        import re

        if not template_name:
            return "New Process"

        result = template_name
        business_name = getattr(business, "name", None)
        unit_name = getattr(unit, "name", None)

        if business_name:
            result = re.sub(
                r"\[business\s*name\]", business_name,
                result, flags=re.IGNORECASE,
            )
        if unit_name:
            result = re.sub(
                r"\[(business\s*)?unit\s*name\]", unit_name,
                result, flags=re.IGNORECASE,
            )

        return result

    async def _set_assignee_async(
        self,
        new_task: Any,
        source_process: Any,
        unit: Any,
        business: Any,
        fixed_assignee_gid: str | None,
    ) -> None:
        """Set assignee from rep cascade or fixed GID."""
        assignee_gid = fixed_assignee_gid

        if not assignee_gid and unit:
            rep_list = getattr(unit, "rep", None)
            if rep_list and len(rep_list) > 0:
                first_rep = rep_list[0]
                if isinstance(first_rep, dict):
                    assignee_gid = first_rep.get("gid")

        if not assignee_gid and business:
            rep_list = getattr(business, "rep", None)
            if rep_list and len(rep_list) > 0:
                first_rep = rep_list[0]
                if isinstance(first_rep, dict):
                    assignee_gid = first_rep.get("gid")

        if assignee_gid:
            try:
                await self._client.tasks.set_assignee_async(
                    new_task.gid, assignee_gid
                )
            except Exception as e:
                logger.warning(
                    "lifecycle_set_assignee_failed",
                    task_gid=new_task.gid,
                    error=str(e),
                )
```

---

## 7. Cascading Section Service

```python
# src/autom8_asana/lifecycle/sections.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.lifecycle.config import CascadingSectionConfig

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


@dataclass
class CascadeResult:
    """Result of cascading section updates."""
    updates: list[str] = field(default_factory=list)  # GIDs updated


class CascadingSectionService:
    """Updates Offer, Unit, and Business sections during stage transitions.

    Per production data (Appendix B of spike):
    - Each stage has specific section mappings for Offer, Unit, Business
    - Not all stages update all three entities
    - Section names are case-insensitive matched
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def cascade_async(
        self,
        config: CascadingSectionConfig,
        ctx: ResolutionContext,
    ) -> CascadeResult:
        """Apply cascading section updates.

        Args:
            config: Section names for offer/unit/business.
            ctx: Resolution context for entity access.

        Returns:
            CascadeResult with list of updated entity GIDs.
        """
        result = CascadeResult()

        # Update Offer section
        if config.offer:
            try:
                offer = await ctx.offer_async()
                await self._move_to_section_async(
                    offer, config.offer
                )
                result.updates.append(offer.gid)
            except Exception as e:
                logger.warning(
                    "cascade_offer_section_failed",
                    section=config.offer,
                    error=str(e),
                )

        # Update Unit section
        if config.unit:
            try:
                unit = await ctx.unit_async()
                await self._move_to_section_async(
                    unit, config.unit
                )
                result.updates.append(unit.gid)
            except Exception as e:
                logger.warning(
                    "cascade_unit_section_failed",
                    section=config.unit,
                    error=str(e),
                )

        # Update Business section
        if config.business:
            try:
                business = await ctx.business_async()
                await self._move_to_section_async(
                    business, config.business
                )
                result.updates.append(business.gid)
            except Exception as e:
                logger.warning(
                    "cascade_business_section_failed",
                    section=config.business,
                    error=str(e),
                )

        return result

    async def _move_to_section_async(
        self,
        entity: Any,
        section_name: str,
    ) -> None:
        """Move entity to named section in its primary project."""
        if not entity.memberships:
            return

        # Get project GID from first membership
        project_gid = None
        for m in entity.memberships:
            p = m.get("project", {})
            if p.get("gid"):
                project_gid = p["gid"]
                break

        if not project_gid:
            return

        # Find section by name
        sections = await self._client.sections.list_for_project_async(
            project_gid
        ).collect()

        target = next(
            (s for s in sections
             if s.name and s.name.lower() == section_name.lower()),
            None,
        )

        if target:
            await self._client.sections.add_task_async(
                target.gid, task=entity.gid
            )
```

---

## 8. Pipeline Auto-Completion Service

```python
# src/autom8_asana/lifecycle/completion.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.process import Process
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


@dataclass
class CompletionResult:
    """Result of auto-completion."""
    completed: list[str] = field(default_factory=list)  # GIDs completed


class PipelineAutoCompletionService:
    """Auto-completes earlier pipeline stages when later stages begin.

    Business rule: When Implementation starts, Sales and Onboarding
    (if still open) are auto-completed. This prevents orphaned
    incomplete processes from earlier stages.

    Algorithm:
    1. Get all processes in ProcessHolder
    2. Filter to Pipeline processes (not DNA, not Consultations)
    3. Find any with pipeline_stage < new stage that are not completed
    4. Complete them and move to COMPLETED section
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def auto_complete_async(
        self,
        source_process: Process,
        new_pipeline_stage: int,
        ctx: ResolutionContext,
    ) -> CompletionResult:
        """Auto-complete earlier pipeline stages.

        Args:
            source_process: Process being transitioned.
            new_pipeline_stage: Pipeline stage of the new process.
            ctx: Resolution context for entity access.

        Returns:
            CompletionResult with list of completed process GIDs.
        """
        result = CompletionResult()

        try:
            unit = await ctx.unit_async()
            processes = unit.processes

            for process in processes:
                # Skip self
                if process.gid == source_process.gid:
                    continue

                # Skip already completed
                if process.completed:
                    continue

                # Skip processes from later or equal stages
                stage = self._get_pipeline_stage(process)
                if stage >= new_pipeline_stage:
                    continue

                # Auto-complete
                await self._client.tasks.update_async(
                    process.gid, completed=True
                )
                result.completed.append(process.gid)

                logger.info(
                    "lifecycle_auto_completed",
                    process_gid=process.gid,
                    process_name=process.name,
                    stage=stage,
                )

        except Exception as e:
            logger.warning(
                "lifecycle_auto_complete_failed",
                error=str(e),
            )

        return result

    def _get_pipeline_stage(self, process: Process) -> int:
        """Get pipeline stage number for a process."""
        from autom8_asana.models.business.process import ProcessType

        stage_map = {
            ProcessType.OUTREACH: 1,
            ProcessType.SALES: 2,
            ProcessType.ONBOARDING: 3,
            ProcessType.IMPLEMENTATION: 4,
            ProcessType.MONTH1: 5,
            ProcessType.RETENTION: 1,
            ProcessType.REACTIVATION: 2,
            ProcessType.ACCOUNT_ERROR: 6,
            ProcessType.EXPANSION: 6,
        }
        return stage_map.get(process.process_type, 0)
```

---

## 9. Dependency Wiring Service

```python
# src/autom8_asana/lifecycle/wiring.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.lifecycle.config import LifecycleConfig

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


@dataclass
class WiringResult:
    """Result of dependency wiring."""
    wired: list[str] = field(default_factory=list)  # dependency GIDs wired


class DependencyWiringService:
    """Wires Asana dependencies between entities after creation.

    Key constraint: Entity MUST have a valid GID before dependency
    API calls can reference it. Wiring is always Phase 4 (after creation).

    Production data: Dependencies are SPARSE (0-1 per process).
    Primary pattern: Play -> Implementation (Play blocks Implementation).
    """

    def __init__(
        self,
        client: AsanaClient,
        config: LifecycleConfig,
    ) -> None:
        self._client = client
        self._config = config

    async def wire_defaults_async(
        self,
        entity_gid: str,
        stage_name: str,
        ctx: ResolutionContext,
    ) -> WiringResult:
        """Wire default dependencies for a newly created entity.

        Args:
            entity_gid: GID of the newly created entity.
            stage_name: Stage name (e.g., "onboarding").
            ctx: Resolution context for entity access.

        Returns:
            WiringResult with list of wired dependency GIDs.
        """
        result = WiringResult()

        # Get wiring rules for pipeline default
        pipeline_rules = self._config.get_wiring_rules("pipeline_default")
        if pipeline_rules:
            # Wire dependents (Unit, OfferHolder)
            for dep_config in pipeline_rules.dependents:
                entity_type = dep_config.get("entity_type")
                try:
                    dependent_gid = await self._resolve_dependent_gid(
                        entity_type, ctx
                    )
                    if dependent_gid:
                        await self._client.tasks.add_dependent_async(
                            entity_gid, dependent_gid
                        )
                        result.wired.append(dependent_gid)
                except Exception as e:
                    logger.warning(
                        "lifecycle_wire_dependent_failed",
                        entity_type=entity_type,
                        error=str(e),
                    )

            # Wire dependencies (open DNA plays)
            for dep_config in pipeline_rules.dependencies:
                source = dep_config.get("source")
                filter_type = dep_config.get("filter")
                if source == "dna_holder" and filter_type == "open_plays":
                    try:
                        business = await ctx.business_async()
                        if business.dna_holder:
                            await ctx.hydrate_branch_async(
                                business, "dna_holder"
                            )
                            for dna in business.dna_holder.children:
                                if not dna.completed:
                                    await self._client.tasks.add_dependency_async(
                                        entity_gid, dna.gid
                                    )
                                    result.wired.append(dna.gid)
                    except Exception as e:
                        logger.warning(
                            "lifecycle_wire_open_plays_failed",
                            error=str(e),
                        )

        return result

    async def wire_entity_as_dependency_async(
        self,
        created_gid: str,
        dependency_of_stage: str,
        ctx: ResolutionContext,
    ) -> WiringResult:
        """Wire a created entity as a dependency of another entity.

        Used for: BackendOnboardABusiness -> dependency of Implementation.

        Args:
            created_gid: GID of the newly created entity.
            dependency_of_stage: Stage that the entity blocks.
            ctx: Resolution context.

        Returns:
            WiringResult.
        """
        result = WiringResult()

        try:
            # Find the target process (e.g., Implementation)
            # The created entity should be a dependency of the target
            await self._client.tasks.add_dependency_async(
                ctx._trigger_entity.gid if ctx._trigger_entity else "",
                created_gid,
            )
            result.wired.append(created_gid)
        except Exception as e:
            logger.warning(
                "lifecycle_wire_entity_dependency_failed",
                created_gid=created_gid,
                stage=dependency_of_stage,
                error=str(e),
            )

        return result

    async def _resolve_dependent_gid(
        self,
        entity_type: str,
        ctx: ResolutionContext,
    ) -> str | None:
        """Resolve GID for a dependent entity."""
        if entity_type == "unit":
            unit = await ctx.unit_async()
            return unit.gid
        elif entity_type == "offer_holder":
            unit = await ctx.unit_async()
            if unit.offer_holder:
                return unit.offer_holder.gid
        return None
```

---

## 10. Automation Dispatch

```python
# src/autom8_asana/lifecycle/dispatch.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.engine import LifecycleEngine

logger = get_logger(__name__)


class AutomationDispatch:
    """Unified entry point for all automation triggers.

    Routes:
    - Section change events -> LifecycleEngine
    - Tag-based triggers -> LifecycleEngine (via tag routing config)
    - Action requests -> ActionExecutor (existing)
    - Workflow requests -> WorkflowAction registry (existing)

    Circular trigger prevention via trigger_chain tracking.
    """

    def __init__(
        self,
        client: AsanaClient,
        lifecycle_engine: LifecycleEngine,
    ) -> None:
        self._client = client
        self._lifecycle_engine = lifecycle_engine

    async def dispatch_async(
        self,
        trigger: dict[str, Any],
        trigger_chain: list[str] | None = None,
    ) -> dict[str, Any]:
        """Route trigger to appropriate subsystem.

        Args:
            trigger: Trigger data (from webhook, polling, or internal).
            trigger_chain: Chain of trigger IDs for circular prevention.

        Returns:
            Result dict from the handling subsystem.
        """
        chain = trigger_chain or []
        trigger_id = trigger.get("id", "unknown")

        # Circular trigger prevention
        if trigger_id in chain:
            logger.warning(
                "circular_trigger_detected",
                trigger_id=trigger_id,
                chain=chain,
            )
            return {"success": False, "error": "circular_trigger"}

        chain.append(trigger_id)

        trigger_type = trigger.get("type")

        if trigger_type == "section_changed":
            return await self._handle_section_change(trigger, chain)
        elif trigger_type == "tag_added":
            return await self._handle_tag_trigger(trigger, chain)

        return {"success": False, "error": f"unknown_trigger_type: {trigger_type}"}

    async def _handle_section_change(
        self,
        trigger: dict[str, Any],
        chain: list[str],
    ) -> dict[str, Any]:
        """Route section change to lifecycle engine."""
        from autom8_asana.models.business.process import Process, ProcessSection

        task_gid = trigger.get("task_gid")
        section_name = trigger.get("section_name", "").lower()

        # Determine outcome from section
        if "converted" == section_name:
            outcome = "converted"
        elif "did not convert" in section_name or "did_not_convert" in section_name:
            outcome = "did_not_convert"
        else:
            return {"success": False, "error": f"unhandled_section: {section_name}"}

        # Fetch process
        task_data = await self._client.tasks.get_async(task_gid)
        process = Process.model_validate(task_data.model_dump())

        result = await self._lifecycle_engine.handle_transition_async(
            process, outcome
        )
        return {"success": result.success, "result": result}

    async def _handle_tag_trigger(
        self,
        trigger: dict[str, Any],
        chain: list[str],
    ) -> dict[str, Any]:
        """Route tag-based trigger to lifecycle engine."""
        tag_name = trigger.get("tag_name", "")

        if tag_name.startswith("route_"):
            stage = tag_name.replace("route_", "")
            # Route to lifecycle engine as a "converted" transition
            # targeting the specified stage
            return {"success": True, "routed_to": f"lifecycle:{stage}"}

        return {"success": False, "error": f"unhandled_tag: {tag_name}"}
```

---

## 11. Webhook Handler

```python
# src/autom8_asana/lifecycle/webhook.py

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from autom8y_log import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class AsanaWebhookPayload(BaseModel):
    """Payload from Asana Rule webhook."""
    task_gid: str
    task_name: str | None = None
    project_gid: str | None = None
    section_name: str | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class WebhookResponse(BaseModel):
    """Response to Asana webhook."""
    accepted: bool
    message: str = ""


@router.post("/asana")
async def handle_asana_webhook(
    payload: AsanaWebhookPayload,
    request: Request,
) -> WebhookResponse:
    """Receive Asana Rule webhook and dispatch to automation.

    This endpoint receives webhook POST from Asana Rules when:
    - A task moves between sections (CONVERTED, DID NOT CONVERT)
    - A tag is added to a task (route_*, request_*, play_*)

    The full task object is in the payload (custom fields, section,
    projects). Subtasks, dependencies, and stories require separate
    API calls.

    Args:
        payload: Parsed webhook payload.
        request: FastAPI request (for accessing app state).

    Returns:
        WebhookResponse indicating acceptance.
    """
    logger.info(
        "webhook_received",
        task_gid=payload.task_gid,
        section=payload.section_name,
        tags=payload.tags,
    )

    # Get dispatch from app state
    dispatch = request.app.state.automation_dispatch

    # Build trigger from payload
    trigger: dict[str, Any] = {
        "id": f"webhook_{payload.task_gid}_{payload.section_name}",
        "task_gid": payload.task_gid,
    }

    if payload.section_name:
        trigger["type"] = "section_changed"
        trigger["section_name"] = payload.section_name
    elif payload.tags:
        trigger["type"] = "tag_added"
        trigger["tag_name"] = payload.tags[0] if payload.tags else ""

    result = await dispatch.dispatch_async(trigger)

    return WebhookResponse(
        accepted=True,
        message=f"Dispatched: {result.get('success', False)}",
    )
```

---

## 12. PipelineConversionRule Absorption Plan

### 12.1 Current State

`PipelineConversionRule` at `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/pipeline.py` is 1084 lines covering Sales -> Onboarding only.

### 12.2 Absorption Steps

| Step | Action | Risk |
|------|--------|------|
| 1 | Build lifecycle engine with Sales -> Onboarding as first route | None (additive) |
| 2 | Write integration tests comparing lifecycle engine output vs PipelineConversionRule output | None (test-only) |
| 3 | Verify behavior parity: same task name, same fields, same hierarchy placement | Low |
| 4 | Point automation engine to lifecycle engine for Sales -> Onboarding | Medium (switchover) |
| 5 | Remove PipelineConversionRule (or mark deprecated) | Low (after step 4 verified) |

### 12.3 Behavior Parity Checklist

Every behavior of PipelineConversionRule must be replicated:

| Behavior | PipelineConversionRule | Lifecycle Engine |
|----------|----------------------|------------------|
| Template discovery | `TemplateDiscovery.find_template_task_async()` | Same (reused) |
| Task duplication | `client.tasks.duplicate_async()` | Same (reused) |
| Project addition | `client.tasks.add_to_project_async()` | Same (reused) |
| Section placement | `_move_to_target_section_async()` | `CascadingSectionService` |
| Due date | `_set_due_date_async()` | `EntityCreationService._configure_async()` |
| Subtask wait | `SubtaskWaiter.wait_for_subtasks_async()` | Same (reused) |
| Field seeding | `FieldSeeder.seed_fields_async()` | Same (reused) |
| Hierarchy placement | `_place_in_hierarchy_async()` | `EntityCreationService._configure_async()` |
| Assignee | `_set_assignee_from_rep_async()` | `EntityCreationService._set_assignee_async()` |
| Comment | `_create_onboarding_comment_async()` | Init action plugin |
| Pre/post validation | `_validate_pre/post_transition()` | Validation plugin |

---

## 13. Test Strategy

### 13.1 Unit Tests

| Test Module | Coverage |
|-------------|----------|
| `test_config.py` | YAML loading, stage parsing, DAG navigation |
| `test_engine.py` | Transition routing, terminal handling, self-loop guards |
| `test_creation.py` | Template discovery, duplication, naming, duplicate detection |
| `test_sections.py` | Cascading section updates per stage |
| `test_completion.py` | Auto-completion of earlier stages |
| `test_wiring.py` | Dependency wiring rules, open plays detection |
| `test_dispatch.py` | Trigger routing, circular prevention |
| `test_webhook.py` | Payload parsing, dispatch integration |

### 13.2 Integration Tests

| Test Module | Coverage |
|-------------|----------|
| `test_sales_to_onboarding.py` | Full Sales -> Onboarding parity with PipelineConversionRule |
| `test_full_lifecycle.py` | Sales -> Onboarding -> Implementation -> Month1 chain |
| `test_self_loops.py` | Outreach and Reactivation self-loop with guards |
| `test_products_branching.py` | Videography products trigger SourceVideographer creation |

### 13.3 Existing Test Compatibility

- ProcessType enum expansion: New members do not affect existing tests
- DNA model field additions: Additive, descriptors return None when field absent
- PipelineConversionRule: Remains unchanged until absorption step 4
- All 8500+ existing tests continue to pass without modification

---

## 14. Rollback Strategy

The lifecycle engine is a new module (`src/autom8_asana/lifecycle/`). Rollback:

1. **ProcessType expansion**: Keep (no downside to having the enum values)
2. **DNA fields**: Keep (additive, no impact on existing code)
3. **Lifecycle module**: Delete `src/autom8_asana/lifecycle/` entirely
4. **Webhook route**: Remove route registration from FastAPI app
5. **PipelineConversionRule**: Remains unchanged until explicit absorption

The only irreversible change is the ProcessType expansion, which is universally beneficial.

---

## 15. Implementation Sequence

| Order | Component | Dependencies | Effort |
|-------|-----------|-------------|--------|
| 1 | ProcessType expansion | None | 1 day |
| 2 | DNA model fields | None | 1 day |
| 3 | Stage config (YAML + loader) | None | 3-5 days |
| 4 | EntityCreationService | Resolution primitives (Phase 1) | 1 week |
| 5 | CascadingSectionService | Resolution primitives | 3-5 days |
| 6 | PipelineAutoCompletionService | Resolution primitives | 2-3 days |
| 7 | DependencyWiringService | Resolution primitives | 3-5 days |
| 8 | LifecycleEngine (orchestrator) | Steps 3-7 | 3-5 days |
| 9 | AutomationDispatch | LifecycleEngine | 2-3 days |
| 10 | Webhook handler | AutomationDispatch | 1-2 days |
| 11 | PipelineConversionRule absorption | Steps 8-9, parity tests | 3-5 days |
