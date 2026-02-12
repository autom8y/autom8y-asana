# TDD: Lifecycle Engine Hardening

**Date**: 2026-02-11
**Status**: Design Complete
**Architect**: Architect (10x-dev rite)
**PRD**: PRD-lifecycle-engine-hardening (30 FRs, 8 SCs)
**Depends On**: TDD-resolution-primitives (stable, production-ready)
**Replaces**: TDD-lifecycle-engine (R&D prototype, reference only)

---

## 1. Overview

### 1.1 Scope

Full production rewrite of all 10 lifecycle engine modules plus absorption of PipelineConversionRule (PCR) for pipeline stages 1-4. This is not an incremental fix of the prototype; it is a clean rewrite of every module in `src/autom8_asana/lifecycle/` using the prototype as behavioral reference while fixing all 9 audit gaps, eliminating stubs, and implementing auto-cascade field seeding.

### 1.2 Architecture Decision

The system retains the **service-per-concern** module structure from the prototype (ADR-ARCH-001 below) but with three structural changes:

1. **Config layer rewritten** from frozen dataclasses to Pydantic BaseModel with startup validation and DAG integrity checking.
2. **Engine pipeline reduced from 5 phases to 4** by merging Wire and Configure (both PUT operations) and adding hierarchy placement as a Configure concern. Comments move to init actions.
3. **Auto-cascade field seeding replaces FieldSeeder's static field lists** with runtime field-name matching at creation time, using YAML only for exclusions and computed fields.

### 1.3 Module Map

```
src/autom8_asana/
  lifecycle/
    __init__.py              Package exports
    config.py                Pydantic config models + YAML loader + DAG validation
    engine.py                LifecycleEngine (4-phase orchestrator)
    creation.py              EntityCreationService (highest-risk module)
    seeding.py               AutoCascadeSeeder (novel design, replaces FieldSeeder usage)
    sections.py              CascadingSectionService
    completion.py            CompletionService (explicit per-transition)
    wiring.py                DependencyWiringService
    init_actions.py          InitActionRegistry + all handlers
    reopen.py                ReopenService (DNC reopen mechanics)
    dispatch.py              AutomationDispatch (trigger routing)
  core/
    project_registry.py      Central project GID registry
  resolution/
    context.py               (enhanced: resolve_holder_async already present)
```

### 1.4 Integration Points

| System | Interface | Direction |
|--------|-----------|-----------|
| Resolution module | `ResolutionContext` async context manager | lifecycle imports resolution |
| Asana client | `AsanaClient` (tasks, sections, stories) | lifecycle imports client |
| Project registry | `core/project_registry.py` | lifecycle imports core |
| YAML config | `config/lifecycle_stages.yaml` | loaded at startup |
| PipelineTransitionWorkflow | Calls `LifecycleEngine.handle_transition_async()` | workflow imports lifecycle |
| AutomationResult | `persistence/models.py` | lifecycle imports persistence |
| Business models | `models/business/*` | lifecycle imports models |
| SaveSession | `persistence/session.py` | lifecycle imports persistence |

### 1.5 Import Graph (Acyclic)

```
lifecycle/ --> resolution/ --> models/business/
lifecycle/ --> core/
lifecycle/ --> models/business/
lifecycle/ --> persistence/
lifecycle/ --> automation/templates.py
lifecycle/ --> automation/waiter.py
```

No reverse dependencies. `models/` does not import from `lifecycle/` or `resolution/`. `resolution/` does not import from `lifecycle/`.

---

## 2. Module Designs

### 2.1 LifecycleConfig (`lifecycle/config.py`)

**Responsibilities**: Load, validate, and provide access to YAML stage configuration. Fail fast on malformed config. Enforce DAG integrity at load time.

**Dependencies**: `pydantic`, `yaml`, `pathlib`

**FR Coverage**: FR-CONFIG-001, FR-CONFIG-002, FR-CONFIG-003, NFR-003, NFR-004

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class SelfLoopConfig(BaseModel):
    """Configuration for self-loop stages."""
    max_iterations: int = 5
    delay_schedule: list[int] = Field(default_factory=list)


class InitActionConfig(BaseModel):
    """Configuration for init-time actions on a stage."""
    type: str
    condition: str | None = None
    play_type: str | None = None
    project_gid: str | None = None
    entity_type: str | None = None
    action: str | None = None
    # Reopen-or-create params
    reopen_if_completed_within_days: int | None = None
    always_create_new: bool = False
    # Comment template
    comment_template: str | None = None
    # Holder type for hierarchy placement
    holder_type: str | None = None
    # Dependency wiring flag
    wire_as_dependency: bool = False


class ValidationRuleConfig(BaseModel):
    """Validation rules for a transition."""
    required_fields: list[str] = Field(default_factory=list)
    mode: Literal["warn", "block"] = "warn"


class ValidationConfig(BaseModel):
    """Pre/post validation for a stage."""
    pre_transition: ValidationRuleConfig | None = None
    post_transition: ValidationRuleConfig | None = None


class CascadingSectionConfig(BaseModel):
    """Sections to set on related entities."""
    offer: str | None = None
    unit: str | None = None
    business: str | None = None


class TransitionConfig(BaseModel):
    """Transition routing for a stage."""
    converted: str | None = None
    did_not_convert: str | None = None
    # Explicit per-transition auto-completion (FR-COMPLETE-001)
    auto_complete_prior: bool = False


class SeedingConfig(BaseModel):
    """Field seeding configuration per stage."""
    exclude_fields: list[str] = Field(default_factory=list)
    computed_fields: dict[str, str] = Field(default_factory=dict)
    # e.g., {"Launch Date": "today", "Status": "New"}


class AssigneeConfig(BaseModel):
    """Assignee resolution per stage."""
    assignee_source: str | None = None  # e.g., "rep", "onboarding_specialist"
    assignee_gid: str | None = None     # fixed fallback GID


class StageConfig(BaseModel):
    """Complete configuration for a lifecycle stage."""
    name: str
    project_gid: str | None = None
    pipeline_stage: int = 0
    template_section: str = "TEMPLATE"
    target_section: str = "OPPORTUNITY"
    due_date_offset_days: int = 0

    transitions: TransitionConfig
    cascading_sections: CascadingSectionConfig = Field(
        default_factory=CascadingSectionConfig
    )
    init_actions: list[InitActionConfig] = Field(default_factory=list)
    self_loop: SelfLoopConfig | None = None
    validation: ValidationConfig | None = None
    seeding: SeedingConfig = Field(default_factory=SeedingConfig)
    assignee: AssigneeConfig = Field(default_factory=AssigneeConfig)

    # DNC routing behavior
    dnc_action: Literal["create_new", "reopen", "deferred"] = "create_new"


class WiringRuleConfig(BaseModel):
    """Dependency wiring rule."""
    dependents: list[dict[str, str]] = Field(default_factory=list)
    dependencies: list[dict[str, str]] = Field(default_factory=list)
    dependency_of: str | None = None


class LifecycleConfigModel(BaseModel):
    """Top-level Pydantic model for lifecycle_stages.yaml."""
    stages: dict[str, StageConfig]
    dependency_wiring: dict[str, WiringRuleConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dag_integrity(self) -> LifecycleConfigModel:
        """Validate that all transition targets reference defined stages."""
        stage_names = set(self.stages.keys())
        errors: list[str] = []
        for name, stage in self.stages.items():
            if stage.transitions.converted and stage.transitions.converted not in stage_names:
                errors.append(
                    f"Stage '{name}' converted target "
                    f"'{stage.transitions.converted}' is not a defined stage"
                )
            if stage.transitions.did_not_convert and stage.transitions.did_not_convert not in stage_names:
                errors.append(
                    f"Stage '{name}' did_not_convert target "
                    f"'{stage.transitions.did_not_convert}' is not a defined stage"
                )
        if errors:
            raise ValueError(
                f"DAG integrity check failed: {'; '.join(errors)}"
            )
        return self


class LifecycleConfig:
    """Loads and provides access to lifecycle stage configuration.

    Validates at load time via Pydantic. Raises ValidationError on
    malformed YAML (fail-fast, not fail-at-transition).
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._model: LifecycleConfigModel | None = None
        if config_path:
            self._load(config_path)

    def _load(self, path: Path) -> None:
        """Load and validate configuration from YAML file.

        Raises:
            pydantic.ValidationError: On malformed config.
            ValueError: On DAG integrity failure.
            FileNotFoundError: If config file missing.
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        # Inject stage names into stage dicts before validation
        for name, stage_data in data.get("stages", {}).items():
            stage_data["name"] = name

        self._model = LifecycleConfigModel.model_validate(data)

    def get_stage(self, name: str) -> StageConfig | None:
        if self._model is None:
            return None
        return self._model.stages.get(name)

    def get_target_stage(
        self, source_stage: str, outcome: str
    ) -> StageConfig | None:
        source = self.get_stage(source_stage)
        if source is None:
            return None
        target_name = getattr(source.transitions, outcome, None)
        if target_name is None:
            return None
        return self.get_stage(target_name)

    def get_wiring_rules(self, entity_type: str) -> WiringRuleConfig | None:
        if self._model is None:
            return None
        return self._model.dependency_wiring.get(entity_type)

    @property
    def stages(self) -> dict[str, StageConfig]:
        if self._model is None:
            return {}
        return self._model.stages
```

**Error Contract**:
- `pydantic.ValidationError` on malformed YAML at load time (not caught by config)
- `ValueError` on DAG integrity failure (not caught by config)
- `FileNotFoundError` if YAML file is missing (not caught by config)
- All three are hard-fail at startup. No runtime config errors.

---

### 2.2 LifecycleEngine (`lifecycle/engine.py`)

**Responsibilities**: Orchestrate the 4-phase pipeline for a single transition. Route DNC transitions to either create-new or reopen. Accumulate results from each phase into a composite `AutomationResult`.

**Dependencies**: All lifecycle services, `ResolutionContext`, `AutomationResult`, `autom8y_log`

**FR Coverage**: FR-ROUTE-001 through FR-ROUTE-004, FR-DNC-001 through FR-DNC-004, FR-ERR-001, FR-AUDIT-001

```python
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.lifecycle.config import LifecycleConfig, StageConfig
from autom8_asana.lifecycle.creation import EntityCreationService, CreationResult
from autom8_asana.lifecycle.completion import CompletionService
from autom8_asana.lifecycle.sections import CascadingSectionService
from autom8_asana.lifecycle.wiring import DependencyWiringService
from autom8_asana.lifecycle.reopen import ReopenService
from autom8_asana.persistence.models import AutomationResult
from autom8_asana.resolution.context import ResolutionContext

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.process import Process

logger = get_logger(__name__)


class TransitionResult:
    """Accumulator for transition phase results."""

    def __init__(self, source_process_gid: str) -> None:
        self.source_process_gid = source_process_gid
        self.actions_executed: list[str] = []
        self.entities_created: list[str] = []
        self.entities_updated: list[str] = []
        self.warnings: list[str] = []
        self.hard_failure: str | None = None

    @property
    def success(self) -> bool:
        return self.hard_failure is None

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning("lifecycle_phase_warning", warning=msg)

    def add_action(self, action: str) -> None:
        self.actions_executed.append(action)

    def add_entity_created(self, gid: str) -> None:
        self.entities_created.append(gid)

    def add_entity_updated(self, gid: str) -> None:
        self.entities_updated.append(gid)

    def fail(self, error: str) -> None:
        self.hard_failure = error


class LifecycleEngine:
    """Orchestrates pipeline lifecycle transitions.

    4-phase pipeline:
      Phase 1: CREATE    -- Template-based entity creation
      Phase 2: CONFIGURE -- Field seeding, section, due date, hierarchy, assignee
      Phase 3: ACTIONS   -- Init actions (BOAB, AssetEdit, Videographer, Comment)
      Phase 4: WIRE      -- Dependency wiring (defaults + init action deps)

    DNC routing:
      - create_new: Standard creation flow (Sales DNC, Impl DNC)
      - reopen: Find + reopen existing process (Onboarding DNC)
      - deferred: Log and return (Outreach DNC self-loop)
    """

    def __init__(
        self,
        client: AsanaClient,
        config: LifecycleConfig,
    ) -> None:
        self._client = client
        self._config = config
        self._creation_service = EntityCreationService(client, config)
        self._section_service = CascadingSectionService(client)
        self._completion_service = CompletionService(client, config)
        self._wiring_service = DependencyWiringService(client, config)
        self._reopen_service = ReopenService(client)

    async def handle_transition_async(
        self,
        source_process: Process,
        outcome: str,
    ) -> AutomationResult:
        """Main entry point for lifecycle automation.

        Args:
            source_process: Process that moved to CONVERTED or DID NOT CONVERT.
            outcome: "converted" or "did_not_convert".

        Returns:
            AutomationResult with execution details.
        """
        start_time = time.perf_counter()
        result = TransitionResult(source_process.gid)

        try:
            # --- Resolve source stage ---
            source_stage_name = source_process.process_type.value
            source_stage = self._config.get_stage(source_stage_name)
            if source_stage is None:
                return self._build_result(
                    f"lifecycle_{source_stage_name}_unknown",
                    source_process, start_time, result,
                    error=f"No stage config for: {source_stage_name}",
                )

            # --- Resolve target stage ---
            target_stage = self._config.get_target_stage(
                source_stage_name, outcome
            )

            if target_stage is None:
                # Terminal state (stages 1-4 scope: Implementation CONVERTED)
                return await self._handle_terminal_async(
                    source_process, source_stage, outcome, start_time, result
                )

            # --- Pre-transition validation ---
            if source_stage.validation and source_stage.validation.pre_transition:
                validation = source_stage.validation.pre_transition
                # Validation logic (check required fields on source)
                missing = self._check_required_fields(
                    source_process, validation.required_fields
                )
                if missing:
                    if validation.mode == "block":
                        return self._build_result(
                            f"lifecycle_{source_stage_name}_validation_blocked",
                            source_process, start_time, result,
                            error=f"Pre-validation failed: {missing}",
                        )
                    result.add_warning(f"Pre-validation: missing {missing}")
                result.add_action("pre_validation")

            # --- DNC routing decision ---
            if outcome == "did_not_convert":
                return await self._handle_dnc_async(
                    source_process, source_stage, target_stage,
                    start_time, result,
                )

            # --- CONVERTED: Standard creation pipeline ---
            async with ResolutionContext(
                self._client,
                trigger_entity=source_process,
            ) as ctx:
                # Phase 1: CREATE
                creation_result = (
                    await self._creation_service.create_process_async(
                        target_stage, ctx, source_process
                    )
                )
                if not creation_result.success:
                    result.fail(
                        f"Process creation failed: {creation_result.error}"
                    )
                    return self._build_result(
                        f"lifecycle_{source_stage_name}_to_{target_stage.name}",
                        source_process, start_time, result,
                    )

                result.add_entity_created(creation_result.entity_gid)
                result.add_action("create_process")

                # Phase 2: CONFIGURE (sections, auto-complete)
                await self._phase_configure_async(
                    source_stage, target_stage, ctx,
                    source_process, result,
                )

                # Phase 3: ACTIONS (init actions)
                await self._phase_actions_async(
                    target_stage, creation_result.entity_gid,
                    ctx, source_process, result,
                )

                # Phase 4: WIRE (dependencies)
                await self._phase_wire_async(
                    target_stage, creation_result.entity_gid,
                    ctx, result,
                )

            # --- Structured audit log ---
            logger.info(
                "lifecycle_transition_complete",
                source_stage=source_stage_name,
                target_stage=target_stage.name,
                outcome=outcome,
                actions=result.actions_executed,
                entities_created=result.entities_created,
                warnings=result.warnings,
                duration_ms=self._elapsed_ms(start_time),
            )

            return self._build_result(
                f"lifecycle_{source_stage_name}_to_{target_stage.name}",
                source_process, start_time, result,
            )

        except Exception as e:
            logger.error(
                "lifecycle_transition_error",
                source_gid=source_process.gid,
                outcome=outcome,
                error=str(e),
            )
            result.fail(str(e))
            return self._build_result(
                "lifecycle_error",
                source_process, start_time, result,
            )

    async def _handle_dnc_async(
        self,
        source_process: Process,
        source_stage: StageConfig,
        target_stage: StageConfig,
        start_time: float,
        result: TransitionResult,
    ) -> AutomationResult:
        """Handle DID NOT CONVERT transitions.

        Routes based on source_stage.dnc_action:
        - "create_new": Standard creation pipeline (same as CONVERTED)
        - "reopen": Find and reopen existing process
        - "deferred": Log and return (no action)
        """
        dnc_action = source_stage.dnc_action

        if dnc_action == "deferred":
            result.add_action("dnc_deferred")
            logger.info(
                "lifecycle_dnc_deferred",
                source_stage=source_stage.name,
            )
            return self._build_result(
                f"lifecycle_{source_stage.name}_dnc_deferred",
                source_process, start_time, result,
            )

        if dnc_action == "reopen":
            async with ResolutionContext(
                self._client,
                trigger_entity=source_process,
            ) as ctx:
                reopen_result = await self._reopen_service.reopen_async(
                    target_stage, ctx, source_process,
                )
                if reopen_result.success:
                    result.add_action("reopen_process")
                    if reopen_result.entity_gid:
                        result.add_entity_updated(reopen_result.entity_gid)
                else:
                    result.add_warning(
                        f"Reopen failed: {reopen_result.error}"
                    )

            return self._build_result(
                f"lifecycle_{source_stage.name}_dnc_reopen",
                source_process, start_time, result,
            )

        # dnc_action == "create_new" -- same pipeline as CONVERTED
        async with ResolutionContext(
            self._client,
            trigger_entity=source_process,
        ) as ctx:
            creation_result = (
                await self._creation_service.create_process_async(
                    target_stage, ctx, source_process
                )
            )
            if not creation_result.success:
                result.fail(
                    f"DNC creation failed: {creation_result.error}"
                )
                return self._build_result(
                    f"lifecycle_{source_stage.name}_dnc_{target_stage.name}",
                    source_process, start_time, result,
                )

            result.add_entity_created(creation_result.entity_gid)
            result.add_action("create_process")

            await self._phase_configure_async(
                source_stage, target_stage, ctx,
                source_process, result,
            )
            await self._phase_wire_async(
                target_stage, creation_result.entity_gid,
                ctx, result,
            )

        return self._build_result(
            f"lifecycle_{source_stage.name}_dnc_{target_stage.name}",
            source_process, start_time, result,
        )

    async def _handle_terminal_async(
        self,
        source_process: Process,
        source_stage: StageConfig,
        outcome: str,
        start_time: float,
        result: TransitionResult,
    ) -> AutomationResult:
        """Handle terminal state (no target stage)."""
        # Auto-complete source if configured
        if outcome == "converted" and source_stage.transitions.auto_complete_prior:
            result.add_action("auto_complete_source")

        result.add_action("terminal")
        return self._build_result(
            f"lifecycle_{source_stage.name}_terminal",
            source_process, start_time, result,
        )

    async def _phase_configure_async(
        self,
        source_stage: StageConfig,
        target_stage: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
        result: TransitionResult,
    ) -> None:
        """Phase 2: Cascading sections + auto-completion."""
        # Cascading sections
        section_result = await self._section_service.cascade_async(
            target_stage.cascading_sections, ctx
        )
        if section_result.updates:
            for gid in section_result.updates:
                result.add_entity_updated(gid)
            result.add_action("cascade_sections")

        # Auto-completion (explicit per-transition flag)
        if source_stage.transitions.auto_complete_prior:
            completion_result = (
                await self._completion_service.complete_source_async(
                    source_process
                )
            )
            if completion_result.completed:
                for gid in completion_result.completed:
                    result.add_entity_updated(gid)
                result.add_action("auto_complete_source")

    async def _phase_actions_async(
        self,
        target_stage: StageConfig,
        created_entity_gid: str,
        ctx: ResolutionContext,
        source_process: Process,
        result: TransitionResult,
    ) -> None:
        """Phase 3: Init actions."""
        from autom8_asana.lifecycle.init_actions import HANDLER_REGISTRY

        for action_config in target_stage.init_actions:
            handler_cls = HANDLER_REGISTRY.get(action_config.type)
            if handler_cls is None:
                result.add_warning(f"Unknown init action: {action_config.type}")
                continue

            handler = handler_cls(self._client, self._config)
            action_result = await handler.execute_async(
                ctx, created_entity_gid, action_config, source_process
            )
            if action_result.success:
                result.add_action(f"init_{action_config.type}")
                if action_result.entity_gid:
                    result.add_entity_created(action_result.entity_gid)
            else:
                result.add_warning(
                    f"Init action {action_config.type} failed: "
                    f"{action_result.error}"
                )

    async def _phase_wire_async(
        self,
        target_stage: StageConfig,
        entity_gid: str,
        ctx: ResolutionContext,
        result: TransitionResult,
    ) -> None:
        """Phase 4: Dependency wiring."""
        wiring_result = await self._wiring_service.wire_defaults_async(
            entity_gid, target_stage.name, ctx,
        )
        if wiring_result.wired:
            result.add_action("wire_dependencies")

    def _check_required_fields(
        self, process: Process, required_fields: list[str]
    ) -> list[str]:
        """Check required fields on process. Returns list of missing."""
        missing = []
        for field_name in required_fields:
            value = getattr(process, field_name.lower().replace(" ", "_"), None)
            if value is None:
                missing.append(field_name)
            elif isinstance(value, str) and not value.strip():
                missing.append(field_name)
        return missing

    def _elapsed_ms(self, start_time: float) -> float:
        return (time.perf_counter() - start_time) * 1000

    def _build_result(
        self,
        rule_id: str,
        process: Process,
        start_time: float,
        tr: TransitionResult,
        error: str | None = None,
    ) -> AutomationResult:
        effective_error = error or tr.hard_failure
        return AutomationResult(
            rule_id=rule_id,
            rule_name=rule_id.replace("_", " ").title(),
            triggered_by_gid=process.gid,
            triggered_by_type="Process",
            actions_executed=tr.actions_executed,
            entities_created=tr.entities_created,
            entities_updated=tr.entities_updated,
            success=effective_error is None,
            error=effective_error or "",
            execution_time_ms=self._elapsed_ms(start_time),
        )
```

**Error Contract**:
- Top-level `except Exception` at `handle_transition_async` boundary (boundary guard, kept broad per project convention)
- Phase methods catch their own exceptions and report to `TransitionResult` as warnings (fail-forward)
- Hard failure only on entity creation failure (Phase 1) -- everything else is soft-fail

---

### 2.3 EntityCreationService (`lifecycle/creation.py`)

This is the **highest-risk module**. It handles template discovery, task duplication, blank fallback, name generation, section placement, due date, subtask waiting, field seeding, hierarchy placement, and assignee resolution -- all for a single entity creation.

**Responsibilities**: Create one entity (Process, AssetEdit, Play, Videographer) from template with full configuration.

**Dependencies**: `TemplateDiscovery`, `SubtaskWaiter`, `AutoCascadeSeeder`, `SaveSession`, `ResolutionContext`

**FR Coverage**: FR-CREATE-001 through FR-CREATE-004, FR-SEED-001 through FR-SEED-003, FR-ASSIGN-001, FR-HIER-001, FR-TMPL-001, FR-ERR-002

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.templates import TemplateDiscovery
from autom8_asana.automation.waiter import SubtaskWaiter
from autom8_asana.lifecycle.config import LifecycleConfig, StageConfig
from autom8_asana.lifecycle.seeding import AutoCascadeSeeder

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
    was_duplicate: bool = False


class EntityCreationService:
    """Creates entities during lifecycle transitions.

    Creation flow:
    1. RESOLVE context (Business, Unit via ResolutionContext)
    2. DUPLICATE CHECK (ProcessType + Unit match in ProcessHolder)
    3. TEMPLATE discovery (target project template section)
    4. CREATE (duplicate template or blank fallback)
    5. CONFIGURE:
       a. Move to target section in project
       b. Set due date
       c. Wait for subtasks (async Asana duplication)
       d. Auto-cascade field seeding
       e. Hierarchy placement (set_parent under holder)
       f. Set assignee (YAML-configurable cascade)
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
        source_process: Process,
    ) -> CreationResult:
        """Create a new process entity from template.

        This is the main creation method used by the engine for both
        CONVERTED and DNC create-new transitions.
        """
        try:
            # 1. Resolve context entities
            business = await ctx.business_async()
            unit = await ctx.unit_async()

            # 2. Duplicate check (ProcessType + Unit in ProcessHolder)
            existing_gid = await self._check_process_duplicate_async(
                ctx, source_process, stage_config.name,
            )
            if existing_gid:
                logger.info(
                    "lifecycle_duplicate_detected",
                    stage=stage_config.name,
                    existing_gid=existing_gid,
                )
                return CreationResult(
                    success=True,
                    entity_gid=existing_gid,
                    was_duplicate=True,
                )

            # 3. Template discovery
            template_discovery = TemplateDiscovery(self._client)
            template = await template_discovery.find_template_task_async(
                stage_config.project_gid,
                template_section=stage_config.template_section,
            )

            # 4. Create (template or blank fallback)
            new_name = self._generate_name(
                template.name if template else None,
                business, unit,
            )

            if template:
                # Count subtasks before duplication (for waiter)
                template_subtasks = (
                    await self._client.tasks.subtasks_async(
                        template.gid, opt_fields=["gid"]
                    ).collect()
                )
                expected_subtask_count = len(template_subtasks)

                new_task = await self._client.tasks.duplicate_async(
                    template.gid,
                    name=new_name,
                    include=["subtasks", "notes"],
                )
            else:
                # FR-ERR-002: Blank fallback with warning
                logger.warning(
                    "lifecycle_template_not_found",
                    stage=stage_config.name,
                    project_gid=stage_config.project_gid,
                )
                new_task = await self._client.tasks.create_async(
                    name=new_name,
                )
                expected_subtask_count = 0

            # Add to target project
            if stage_config.project_gid:
                await self._client.tasks.add_to_project_async(
                    new_task.gid, stage_config.project_gid,
                )

            # 5. Configure
            await self._configure_async(
                new_task, stage_config, ctx,
                source_process, business, unit,
                expected_subtask_count,
            )

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

    async def create_entity_async(
        self,
        project_gid: str,
        template_section: str,
        holder_type: str,
        ctx: ResolutionContext,
        source_process: Process,
        stage_config: StageConfig,
    ) -> CreationResult:
        """Create a non-process entity (AssetEdit, Play, Videographer).

        Used by init action handlers. Same flow as create_process_async
        but places entity under a different holder type.
        """
        try:
            business = await ctx.business_async()
            unit = await ctx.unit_async()

            template_discovery = TemplateDiscovery(self._client)
            template = await template_discovery.find_template_task_async(
                project_gid,
                template_section=template_section,
            )

            new_name = self._generate_name(
                template.name if template else None,
                business, unit,
            )

            if template:
                template_subtasks = (
                    await self._client.tasks.subtasks_async(
                        template.gid, opt_fields=["gid"]
                    ).collect()
                )
                new_task = await self._client.tasks.duplicate_async(
                    template.gid,
                    name=new_name,
                    include=["subtasks", "notes"],
                )
                expected_subtask_count = len(template_subtasks)
            else:
                logger.warning(
                    "lifecycle_entity_template_not_found",
                    project_gid=project_gid,
                    holder_type=holder_type,
                )
                new_task = await self._client.tasks.create_async(
                    name=new_name,
                )
                expected_subtask_count = 0

            if project_gid:
                await self._client.tasks.add_to_project_async(
                    new_task.gid, project_gid,
                )

            await self._configure_async(
                new_task, stage_config, ctx,
                source_process, business, unit,
                expected_subtask_count,
                holder_type=holder_type,
            )

            return CreationResult(
                success=True,
                entity_gid=new_task.gid,
            )

        except Exception as e:
            logger.error(
                "lifecycle_entity_creation_error",
                holder_type=holder_type,
                error=str(e),
            )
            return CreationResult(success=False, error=str(e))

    async def _configure_async(
        self,
        new_task: Any,
        stage_config: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
        business: Any,
        unit: Any,
        expected_subtask_count: int,
        holder_type: str = "process_holder",
    ) -> None:
        """Configure created entity: section, due date, subtasks,
        fields, hierarchy, assignee."""
        from autom8_asana.persistence.session import SaveSession

        # a. Section placement
        if stage_config.target_section and stage_config.project_gid:
            await self._move_to_section_async(
                new_task.gid, stage_config.project_gid,
                stage_config.target_section,
            )

        # b. Due date
        if stage_config.due_date_offset_days is not None:
            due = date.today() + timedelta(
                days=stage_config.due_date_offset_days
            )
            try:
                await self._client.tasks.update_async(
                    new_task.gid, due_on=due.isoformat()
                )
            except Exception as e:
                logger.warning(
                    "lifecycle_set_due_date_failed",
                    task_gid=new_task.gid, error=str(e),
                )

        # c. Wait for subtasks
        if expected_subtask_count > 0:
            waiter = SubtaskWaiter(self._client)
            await waiter.wait_for_subtasks_async(
                new_task.gid,
                expected_count=expected_subtask_count,
                timeout=2.0,
            )

        # d. Auto-cascade field seeding
        seeder = AutoCascadeSeeder(self._client)
        try:
            await seeder.seed_async(
                target_task_gid=new_task.gid,
                business=business,
                unit=unit,
                source_process=source_process,
                exclude_fields=stage_config.seeding.exclude_fields,
                computed_fields=stage_config.seeding.computed_fields,
            )
        except Exception as e:
            logger.warning(
                "lifecycle_field_seeding_failed",
                task_gid=new_task.gid, error=str(e),
            )

        # e. Hierarchy placement
        holder = await self._resolve_holder_for_placement(
            ctx, holder_type, source_process,
        )
        if holder is not None:
            try:
                async with SaveSession(
                    self._client, automation_enabled=False
                ) as session:
                    session.set_parent(
                        new_task, holder,
                        insert_after=source_process,
                    )
                    await session.commit_async()
            except Exception as e:
                logger.warning(
                    "lifecycle_hierarchy_placement_failed",
                    task_gid=new_task.gid, error=str(e),
                )

        # f. Assignee resolution
        await self._set_assignee_async(
            new_task, source_process, unit, business,
            stage_config.assignee,
        )

    async def _resolve_holder_for_placement(
        self,
        ctx: ResolutionContext,
        holder_type: str,
        source_process: Process,
    ) -> Any | None:
        """Resolve the holder for hierarchy placement.

        For process_holder: use source_process.process_holder or
        resolve_holder_async(ProcessHolder).
        For other holder types: use resolve_holder_async with the
        appropriate holder class.
        """
        if holder_type == "process_holder":
            holder = getattr(source_process, "process_holder", None)
            if holder is not None:
                return holder
            # Fallback: resolve via context
            from autom8_asana.models.business.process import ProcessHolder
            return await ctx.resolve_holder_async(ProcessHolder)

        # Map holder_type string to class
        holder_class_map = {
            "dna_holder": "autom8_asana.models.business.dna.DNAHolder",
            "asset_edit_holder": "autom8_asana.models.business.asset_edit.AssetEditHolder",
            "videography_holder": "autom8_asana.models.business.videography.VideographyHolder",
        }
        class_path = holder_class_map.get(holder_type)
        if class_path:
            import importlib
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            holder_cls = getattr(module, class_name)
            return await ctx.resolve_holder_async(holder_cls)

        return None

    async def _set_assignee_async(
        self,
        new_task: Any,
        source_process: Any,
        unit: Any,
        business: Any,
        assignee_config: Any,
    ) -> None:
        """Set assignee using YAML-configurable cascade.

        Resolution order (FR-ASSIGN-001):
        1. Stage-specific field (assignee_source) from source process
        2. Fixed GID (assignee_gid) from YAML
        3. Unit.rep[0]
        4. Business.rep[0]
        5. None with warning
        """
        assignee_gid: str | None = None

        # 1. Stage-specific field
        if assignee_config.assignee_source:
            attr_name = assignee_config.assignee_source.lower().replace(" ", "_")
            # Try on source process first
            source_field = getattr(source_process, attr_name, None)
            if source_field:
                assignee_gid = self._extract_user_gid(source_field)
            # Try on unit
            if not assignee_gid and unit:
                unit_field = getattr(unit, attr_name, None)
                if unit_field:
                    assignee_gid = self._extract_user_gid(unit_field)

        # 2. Fixed GID
        if not assignee_gid and assignee_config.assignee_gid:
            assignee_gid = assignee_config.assignee_gid

        # 3. Unit.rep[0]
        if not assignee_gid and unit:
            assignee_gid = self._extract_first_rep(unit)

        # 4. Business.rep[0]
        if not assignee_gid and business:
            assignee_gid = self._extract_first_rep(business)

        # 5. Apply or warn
        if assignee_gid:
            try:
                await self._client.tasks.set_assignee_async(
                    new_task.gid, assignee_gid
                )
            except Exception as e:
                logger.warning(
                    "lifecycle_set_assignee_failed",
                    task_gid=new_task.gid, error=str(e),
                )
        else:
            logger.warning(
                "lifecycle_no_assignee_found",
                task_gid=new_task.gid,
            )

    async def _check_process_duplicate_async(
        self,
        ctx: ResolutionContext,
        source_process: Process,
        target_stage_name: str,
    ) -> str | None:
        """Check ProcessHolder for existing non-completed process
        with same ProcessType (FR-DUP-001).

        Similarity: same ProcessType + same Unit (not Business).
        Only non-completed processes are duplicates.
        DNC processes are terminal and not candidates.
        """
        holder = getattr(source_process, "process_holder", None)
        if holder is None:
            return None

        try:
            subtasks = await self._client.tasks.subtasks_async(
                holder.gid,
                opt_fields=["name", "completed", "custom_fields",
                             "custom_fields.name", "custom_fields.display_value"],
            ).collect()

            for task in subtasks:
                if task.completed:
                    continue
                # Match by process_type in custom fields
                if self._matches_process_type(task, target_stage_name):
                    return task.gid

        except Exception as e:
            logger.warning(
                "lifecycle_duplicate_check_failed",
                error=str(e),
            )

        return None

    async def _move_to_section_async(
        self, task_gid: str, project_gid: str, section_name: str,
    ) -> None:
        """Move task to named section (case-insensitive)."""
        try:
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
                    target.gid, task=task_gid,
                )
        except Exception as e:
            logger.warning(
                "lifecycle_section_placement_failed",
                task_gid=task_gid, section=section_name, error=str(e),
            )

    def _generate_name(
        self,
        template_name: str | None,
        business: Any,
        unit: Any,
    ) -> str:
        """Replace [Business Name] and [Unit Name] placeholders."""
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

    @staticmethod
    def _extract_user_gid(field_value: Any) -> str | None:
        """Extract user GID from a people field value."""
        if isinstance(field_value, list) and field_value:
            first = field_value[0]
            if isinstance(first, dict):
                return first.get("gid")
            return getattr(first, "gid", None)
        if isinstance(field_value, dict):
            return field_value.get("gid")
        return None

    @staticmethod
    def _extract_first_rep(entity: Any) -> str | None:
        rep_list = getattr(entity, "rep", None)
        if rep_list and len(rep_list) > 0:
            first = rep_list[0]
            if isinstance(first, dict):
                return first.get("gid")
        return None

    @staticmethod
    def _matches_process_type(task: Any, stage_name: str) -> bool:
        """Check if task's ProcessType custom field matches stage_name."""
        cfs = getattr(task, "custom_fields", None) or []
        for cf in cfs:
            name = cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            if name.lower() in ("process type", "processtype"):
                display = (
                    cf.get("display_value", "")
                    if isinstance(cf, dict)
                    else getattr(cf, "display_value", "")
                )
                if display and display.lower() == stage_name.lower():
                    return True
        return False
```

---

### 2.4 AutoCascadeSeeder (`lifecycle/seeding.py`)

This is the **most novel module**. It replaces the FieldSeeder's static field lists with runtime field-name matching.

**Design Principle**: Fields with matching names on both source and target cascade automatically with zero config. YAML config is only needed for exclusions and computed fields.

**FR Coverage**: FR-SEED-001, FR-SEED-002, FR-SEED-003

```python
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.seeding import (
    FieldSeeder,
    _get_field_attr,
    _normalize_custom_fields,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business import Business, Process, Unit

logger = get_logger(__name__)


class AutoCascadeSeeder:
    """Auto-cascade field seeding with zero-config matching.

    Algorithm:
    1. Fetch target task's custom field definitions (names + types)
    2. Build target field name set (lowered for case-insensitive matching)
    3. For each cascade layer (Business -> Unit -> Process -> Computed):
       a. Inspect entity's custom fields
       b. For each field name that exists on BOTH source entity and target:
          - If not in exclude_fields: cascade the value
       c. Later layers override earlier (dict.update semantics)
    4. Resolve enum string values to GIDs using target's enum_options
    5. Write all matched fields in single API call

    This replaces FieldSeeder's static field lists. The existing
    FieldSeeder infrastructure (enum resolution, write_fields_async,
    CustomFieldAccessor) is reused for the write step.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def seed_async(
        self,
        target_task_gid: str,
        business: Business | None,
        unit: Unit | None,
        source_process: Process,
        exclude_fields: list[str] | None = None,
        computed_fields: dict[str, str] | None = None,
    ) -> None:
        """Seed fields from hierarchy to target using auto-cascade.

        Args:
            target_task_gid: GID of the newly created task.
            business: Business entity (layer 1).
            unit: Unit entity (layer 2).
            source_process: Source process (layer 3).
            exclude_fields: Field names to skip (from YAML).
            computed_fields: Computed values (layer 4, highest priority).
        """
        excludes = {f.lower() for f in (exclude_fields or [])}

        # Fetch target custom field definitions
        target_task = await self._client.tasks.get_async(
            target_task_gid,
            opt_fields=[
                "custom_fields",
                "custom_fields.name",
                "custom_fields.resource_subtype",
                "custom_fields.enum_options",
            ],
        )

        target_fields = _normalize_custom_fields(target_task.custom_fields)
        target_field_names = {
            _get_field_attr(f, "name", "").lower(): f
            for f in target_fields
            if _get_field_attr(f, "name", "")
        }

        if not target_field_names:
            logger.info("auto_cascade_no_target_fields", task_gid=target_task_gid)
            return

        # Build cascaded values from each layer
        seeded: dict[str, Any] = {}

        # Layer 1: Business cascade
        if business is not None:
            business_values = self._extract_matching_fields(
                business, target_field_names, excludes,
            )
            seeded.update(business_values)

        # Layer 2: Unit cascade (overrides Business)
        if unit is not None:
            unit_values = self._extract_matching_fields(
                unit, target_field_names, excludes,
            )
            seeded.update(unit_values)

        # Layer 3: Source process carry-through (overrides Unit)
        process_values = self._extract_matching_fields(
            source_process, target_field_names, excludes,
        )
        seeded.update(process_values)

        # Layer 4: Computed fields (overrides everything)
        for field_name, computation in (computed_fields or {}).items():
            if field_name.lower() in excludes:
                continue
            value = self._compute_field(computation)
            if value is not None:
                seeded[field_name] = value

        if not seeded:
            logger.info("auto_cascade_no_matching_fields", task_gid=target_task_gid)
            return

        logger.info(
            "auto_cascade_fields_matched",
            task_gid=target_task_gid,
            field_count=len(seeded),
            fields=list(seeded.keys()),
        )

        # Write using FieldSeeder infrastructure (enum resolution + API call)
        field_seeder = FieldSeeder(self._client)
        await field_seeder.write_fields_async(target_task_gid, seeded)

    def _extract_matching_fields(
        self,
        entity: Any,
        target_field_names: dict[str, Any],
        excludes: set[str],
    ) -> dict[str, Any]:
        """Extract field values from entity that match target fields.

        Matching is case-insensitive on custom field name.
        """
        matched: dict[str, Any] = {}

        # Get entity's custom fields
        entity_cfs = getattr(entity, "custom_fields", None) or []
        entity_fields = _normalize_custom_fields(entity_cfs)

        for field_dict in entity_fields:
            field_name = _get_field_attr(field_dict, "name", "")
            if not field_name:
                continue

            field_name_lower = field_name.lower()

            # Check exclusion
            if field_name_lower in excludes:
                continue

            # Check if field exists on target
            if field_name_lower not in target_field_names:
                continue

            # Extract value based on field type
            value = self._extract_field_value(field_dict)
            if value is not None:
                matched[field_name] = value

        return matched

    @staticmethod
    def _extract_field_value(field_dict: dict[str, Any]) -> Any:
        """Extract the display value from a custom field dict."""
        subtype = _get_field_attr(field_dict, "resource_subtype", "")

        if subtype == "enum":
            enum_value = _get_field_attr(field_dict, "enum_value", None)
            if enum_value:
                return _get_field_attr(enum_value, "name", None)
            return None

        if subtype == "multi_enum":
            multi_values = _get_field_attr(field_dict, "multi_enum_values", [])
            if multi_values:
                return [
                    _get_field_attr(v, "name", "")
                    for v in multi_values
                    if _get_field_attr(v, "name", "")
                ]
            return None

        if subtype == "people":
            people = _get_field_attr(field_dict, "people_value", [])
            if people:
                return [
                    {"gid": _get_field_attr(p, "gid", "")}
                    for p in people
                    if _get_field_attr(p, "gid", "")
                ]
            return None

        if subtype == "date":
            date_val = _get_field_attr(field_dict, "date_value", None)
            if date_val:
                return _get_field_attr(date_val, "date", None)
            return None

        if subtype == "text":
            return _get_field_attr(field_dict, "text_value", None)

        if subtype == "number":
            return _get_field_attr(field_dict, "number_value", None)

        # Fallback: display_value
        return _get_field_attr(field_dict, "display_value", None)

    @staticmethod
    def _compute_field(computation: str) -> Any:
        """Resolve a computed field specification to a value."""
        if computation == "today":
            return date.today().isoformat()
        # Extensible: add more computation types as needed
        return computation
```

**Key Design Decisions**:
- Matching is by custom field **name** (case-insensitive), not GID. This works because the stakeholder confirmed field names are consistent across projects (Interview R9).
- Values are extracted as display names (strings for enums), then the existing FieldSeeder `write_fields_async` resolves them to target-project-specific GIDs at write time. This handles cross-project enum field resolution correctly.
- People fields cascade as `[{"gid": "..."}]` format, which the CustomFieldAccessor handles natively.
- Date fields cascade as ISO date strings.

---

### 2.5 CascadingSectionService (`lifecycle/sections.py`)

Unchanged from prototype. The design is clean and handles all section update needs.

**FR Coverage**: FR-ROUTE-001 AC-4, FR-ROUTE-002 AC-4, FR-ROUTE-003 AC-4

**Error Contract**: Each entity section update is wrapped in its own try/except. Failure is logged as warning and skipped (fail-forward).

---

### 2.6 CompletionService (`lifecycle/completion.py`)

**Rewritten** to use explicit per-transition `auto_complete_prior` flag instead of stage-number comparison (FR-COMPLETE-001). The stage-number duplication in `_get_pipeline_stage()` is eliminated.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.config import LifecycleConfig
    from autom8_asana.models.business.process import Process

logger = get_logger(__name__)


@dataclass
class CompletionResult:
    completed: list[str] = field(default_factory=list)


class CompletionService:
    """Handles explicit per-transition auto-completion.

    Per FR-COMPLETE-001: Auto-completion is controlled by
    auto_complete_prior flag on each transition, not derived
    from stage number comparison.
    """

    def __init__(
        self, client: AsanaClient, config: LifecycleConfig
    ) -> None:
        self._client = client
        self._config = config

    async def complete_source_async(
        self, source_process: Process
    ) -> CompletionResult:
        """Mark the source process as complete.

        Only called when transition config has auto_complete_prior=true.
        """
        result = CompletionResult()

        if source_process.completed:
            return result

        try:
            await self._client.tasks.update_async(
                source_process.gid, completed=True
            )
            result.completed.append(source_process.gid)
            logger.info(
                "lifecycle_auto_completed",
                process_gid=source_process.gid,
                process_name=source_process.name,
            )
        except Exception as e:
            logger.warning(
                "lifecycle_auto_complete_failed",
                process_gid=source_process.gid,
                error=str(e),
            )

        return result
```

---

### 2.7 DependencyWiringService (`lifecycle/wiring.py`)

Structurally identical to prototype but with narrower exception catches.

**FR Coverage**: FR-WIRE-001, FR-WIRE-002

---

### 2.8 ReopenService (`lifecycle/reopen.py`)

**New module** for DNC reopen mechanics.

**FR Coverage**: FR-DNC-002

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.lifecycle.creation import CreationResult

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.config import StageConfig
    from autom8_asana.models.business.process import Process
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


class ReopenService:
    """Handles DNC reopen mechanics.

    When Onboarding DNC fires, instead of creating a new process,
    the engine finds the most recent Sales process under the
    ProcessHolder, marks it incomplete, and moves it to the
    Opportunity section in the Sales project.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def reopen_async(
        self,
        target_stage: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
    ) -> CreationResult:
        """Find and reopen the most recent process of the target type.

        Steps:
        1. Search ProcessHolder subtasks for most recent process
           matching target ProcessType
        2. Mark it incomplete (completed = false)
        3. Move to Opportunity section in target project

        Returns CreationResult (reuses type for consistency).
        """
        try:
            holder = getattr(source_process, "process_holder", None)
            if holder is None:
                from autom8_asana.models.business.process import ProcessHolder
                holder = await ctx.resolve_holder_async(ProcessHolder)

            if holder is None:
                return CreationResult(
                    success=False,
                    error="Cannot resolve ProcessHolder for reopen",
                )

            # List ProcessHolder subtasks
            subtasks = await self._client.tasks.subtasks_async(
                holder.gid,
                opt_fields=[
                    "name", "completed", "created_at",
                    "custom_fields", "custom_fields.name",
                    "custom_fields.display_value",
                ],
            ).collect()

            # Find most recent process matching target stage ProcessType
            candidates = []
            for task in subtasks:
                if self._matches_process_type(task, target_stage.name):
                    candidates.append(task)

            if not candidates:
                logger.warning(
                    "lifecycle_reopen_no_candidate",
                    target_stage=target_stage.name,
                    holder_gid=holder.gid,
                )
                return CreationResult(
                    success=False,
                    error=f"No {target_stage.name} process found to reopen",
                )

            # Sort by created_at descending, pick most recent
            candidates.sort(
                key=lambda t: getattr(t, "created_at", "") or "",
                reverse=True,
            )
            target_process = candidates[0]

            # Mark incomplete
            await self._client.tasks.update_async(
                target_process.gid, completed=False,
            )

            # Move to Opportunity section
            if target_stage.project_gid:
                await self._move_to_section_async(
                    target_process.gid,
                    target_stage.project_gid,
                    "OPPORTUNITY",
                )

            logger.info(
                "lifecycle_process_reopened",
                process_gid=target_process.gid,
                target_stage=target_stage.name,
            )

            return CreationResult(
                success=True,
                entity_gid=target_process.gid,
            )

        except Exception as e:
            logger.error(
                "lifecycle_reopen_error",
                target_stage=target_stage.name,
                error=str(e),
            )
            return CreationResult(success=False, error=str(e))

    async def _move_to_section_async(
        self, task_gid: str, project_gid: str, section_name: str,
    ) -> None:
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
                target.gid, task=task_gid,
            )

    @staticmethod
    def _matches_process_type(task: Any, stage_name: str) -> bool:
        cfs = getattr(task, "custom_fields", None) or []
        for cf in cfs:
            name = cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            if name.lower() in ("process type", "processtype"):
                display = (
                    cf.get("display_value", "")
                    if isinstance(cf, dict)
                    else getattr(cf, "display_value", "")
                )
                if display and display.lower() == stage_name.lower():
                    return True
        return False
```

---

### 2.9 Init Action Handlers (`lifecycle/init_actions.py`)

**Rewritten** with all handlers implemented (no more stubs).

**Handler Registry**:

| Handler | Type Key | Entity Created | Condition |
|---------|----------|---------------|-----------|
| `CommentHandler` | `create_comment` | None | Always |
| `PlayCreationHandler` | `play_creation` | BOAB play | Reopen-or-create (90d) |
| `EntityCreationHandler` | `entity_creation` | AssetEdit | Duplicate check in holder |
| `ProductsCheckHandler` | `products_check` | SourceVideographer | `video*` in Unit.products |

**Key Changes from Prototype**:
1. `EntityCreationHandler` -- now fully implemented, creates AssetEdit from template under AssetEditHolder with duplicate detection
2. `ProductsCheckHandler` -- now creates SourceVideographer entity (not just a log)
3. `CommentHandler` -- new handler, generalizable comment templates
4. All handlers receive `source_process` parameter for comment generation context

```python
# Signature change: execute_async now receives source_process
class InitActionHandler(ABC):
    @abstractmethod
    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        ...
```

**CommentHandler** implements FR-COMMENT-001 and FR-COMMENT-002:

```python
class CommentHandler(InitActionHandler):
    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        try:
            business = await ctx.business_async()
            comment_text = self._build_comment(
                source_process, business,
                action_config.comment_template,
            )
            await self._client.stories.create_comment_async(
                task=created_entity_gid,
                text=comment_text,
            )
            return CreationResult(success=True, entity_gid="")
        except Exception as e:
            logger.warning(
                "lifecycle_comment_failed",
                task_gid=created_entity_gid, error=str(e),
            )
            return CreationResult(success=True, entity_gid="")  # soft-fail

    def _build_comment(
        self,
        source: Process,
        business: Any,
        template: str | None,
    ) -> str:
        from datetime import date as date_cls
        source_name = source.name or "Unknown"
        business_name = getattr(business, "name", "Unknown") or "Unknown"
        today = date_cls.today().isoformat()

        # Extract source project GID for link
        source_project_gid = "0"
        memberships = getattr(source, "memberships", None) or []
        for m in memberships:
            if isinstance(m, dict):
                p = m.get("project", {})
                if isinstance(p, dict) and p.get("gid"):
                    source_project_gid = p["gid"]
                    break

        source_link = (
            f"https://app.asana.com/0/{source_project_gid}/{source.gid}"
        )

        return (
            f"Pipeline Conversion\n\n"
            f'This process was automatically created when '
            f'"{source_name}" was converted on {today}.\n\n'
            f"Source: {source_link}\n"
            f"Business: {business_name}"
        )
```

**PlayCreationHandler** implements FR-CREATE-003 with reopen-or-create:

The handler checks `reopen_if_completed_within_days` from YAML. If a completed BOAB exists within that threshold, it reopens it instead of creating new.

**EntityCreationHandler** implements FR-CREATE-002:

Uses `EntityCreationService.create_entity_async()` to create AssetEdit under AssetEditHolder, then wires as dependency.

**ProductsCheckHandler** implements FR-CREATE-004:

Checks Unit.products against `video*` pattern (fnmatch). If matched, creates SourceVideographer entity under VideographyHolder.

---

### 2.10 Central Project Registry (`core/project_registry.py`)

**FR Coverage**: FR-CONFIG-001

```python
"""Central project GID registry.

All project GIDs in one place. Entity classes reference this instead
of declaring their own PRIMARY_PROJECT_GID (backward-compatible shim retained).
"""

from __future__ import annotations


class ProjectRegistry:
    """Central registry for all Asana project GIDs."""

    # Pipeline stages
    OUTREACH = "1201753128450029"
    SALES = "1200944186565610"
    ONBOARDING = "1201319387632570"
    IMPLEMENTATION = "1201476141989746"

    # Holder projects
    ASSET_EDIT_HOLDER = "1203992664400125"
    DNA_HOLDER = "1207507299545000"
    VIDEOGRAPHY_HOLDER = "1207984018149338"

    # Lifecycle stages 5+
    RETENTION = "1201346565918814"
    REACTIVATION = "1201265144487549"
    ACCOUNT_ERROR = "1201684018234520"
    EXPANSION = "1201265144487557"

    @classmethod
    def get_stage_project_gid(cls, stage_name: str) -> str | None:
        """Get project GID for a stage name."""
        mapping = {
            "outreach": cls.OUTREACH,
            "sales": cls.SALES,
            "onboarding": cls.ONBOARDING,
            "implementation": cls.IMPLEMENTATION,
            "retention": cls.RETENTION,
            "reactivation": cls.REACTIVATION,
            "account_error": cls.ACCOUNT_ERROR,
            "expansion": cls.EXPANSION,
        }
        return mapping.get(stage_name.lower())
```

---

## 3. Data Models

### 3.1 TransitionRequest (Engine Input)

The engine receives a `Process` entity and an `outcome` string. No separate request model is needed -- the engine signature is:

```python
async def handle_transition_async(
    self,
    source_process: Process,
    outcome: str,  # "converted" | "did_not_convert"
) -> AutomationResult
```

### 3.2 TransitionResult (Internal Accumulator)

Defined in `engine.py` (Section 2.2 above). Accumulates results from all phases, then converts to `AutomationResult` for the caller.

### 3.3 AutomationResult (Engine Output)

Existing model in `persistence/models.py`. No changes needed.

### 3.4 CreationResult (Internal)

Defined in `creation.py`. Extended with `was_duplicate: bool` flag.

---

## 4. Auto-Cascade Field Seeding Design (Detailed)

### 4.1 How Matching Fields Are Discovered

**Runtime inspection**. The seeder fetches the target task's custom field definitions (names, subtypes, enum_options) and compares them against each source entity's custom fields. No compile-time configuration needed.

### 4.2 How Type Compatibility Is Determined

Field matching is by **name only** (case-insensitive). Type compatibility is enforced at write time by the existing `FieldSeeder.write_fields_async()` which uses `CustomFieldAccessor` and handles enum-to-GID resolution. If a field value cannot be written (e.g., text value to enum field with no matching option), the field is skipped with a warning.

### 4.3 Precedence Layers

```
Layer 1: Business.custom_fields  (lowest priority)
Layer 2: Unit.custom_fields      (overrides Business)
Layer 3: source_process.custom_fields  (overrides Unit)
Layer 4: computed_fields from YAML  (highest priority)
```

Later layers override earlier layers via `dict.update()`. Only non-empty values override.

### 4.4 Exclusions in YAML

```yaml
stages:
  onboarding:
    seeding:
      exclude_fields:
        - "Internal Notes"
        - "Admin Tags"
```

Excluded fields are skipped during matching, even if the name exists on both source and target.

### 4.5 Enum GID Resolution for Cross-Project Fields

Enum fields store values as display names (strings) at extraction time, not GIDs. The existing `FieldSeeder._resolve_enum_value()` resolves these strings to the correct GIDs for the target project at write time using the target task's `enum_options`. This handles the cross-project case correctly because each project may have different GIDs for the same enum option name.

### 4.6 Edge Cases

| Case | Handling |
|------|----------|
| Multi-enum | Extracted as `["Option A", "Option B"]`. Each resolved to GID at write time. |
| People fields | Extracted as `[{"gid": "123"}]`. Written directly (GIDs are global). |
| Date fields | Extracted as ISO string. Written directly. |
| Missing field on target | Skipped with warning log. |
| Empty value on source | Not cascaded (None check). |
| Same field on Business and Process | Process value wins (later layer). |

---

## 5. DNC Routing Design

### 5.1 Routing Table

| Source | Outcome | Target | Action | dnc_action |
|--------|---------|--------|--------|------------|
| Sales | DNC | Outreach | Create new | `create_new` |
| Onboarding | DNC | Sales | Reopen existing | `reopen` |
| Implementation | DNC | Outreach | Create new | `create_new` |
| Outreach | DNC | Outreach | Deferred (self-loop) | `deferred` |

### 5.2 How the Engine Distinguishes Create-New vs Reopen

The `dnc_action` field on `StageConfig` controls the behavior. This is set per source stage:

```yaml
stages:
  onboarding:
    dnc_action: reopen
    transitions:
      did_not_convert: sales
  sales:
    dnc_action: create_new
    transitions:
      did_not_convert: outreach
  implementation:
    dnc_action: create_new
    transitions:
      did_not_convert: outreach
  outreach:
    dnc_action: deferred
    transitions:
      did_not_convert: outreach
```

### 5.3 How "Find Most Recent Sales in ProcessHolder" Works

`ReopenService.reopen_async()`:
1. Resolve ProcessHolder from source_process or via `resolve_holder_async`
2. List ProcessHolder subtasks with `custom_fields` opt_fields
3. Filter to tasks where ProcessType custom field matches target stage name ("sales")
4. Sort by `created_at` descending
5. Pick first (most recent)
6. Mark incomplete, move to Opportunity section

---

## 6. Reopen-or-Create Pattern

### 6.1 Generic Pattern

```python
async def reopen_or_create(
    holder_gid: str,
    entity_type: str,
    staleness_days: int | None,
    create_fn: Callable,
) -> CreationResult:
    # 1. Search holder subtasks for matching entity type
    # 2. If found non-completed: return existing (already active)
    # 3. If found completed within staleness_days: reopen (mark incomplete)
    # 4. Otherwise: create new via create_fn
```

### 6.2 Usage by BOAB

```yaml
- type: play_creation
  play_type: backend_onboard_a_business
  project_gid: "1207507299545000"
  reopen_if_completed_within_days: 90
```

PlayCreationHandler checks DNAHolder for existing BOAB. If found completed within 90 days, reopens it. Otherwise creates new.

### 6.3 Usage by AssetEdit

```yaml
- type: entity_creation
  entity_type: asset_edit
  project_gid: "1203992664400125"
  holder_type: asset_edit_holder
  always_create_new: false
  wire_as_dependency: true
```

EntityCreationHandler checks AssetEditHolder for existing AssetEdit. If found non-completed, returns existing GID (duplicate detection).

### 6.4 DNC Reopen (Special Case)

DNC reopen is handled at the engine level (not init action level) because it replaces the entire creation pipeline rather than being an additional action.

---

## 7. Phase Pipeline Design

### 7.1 4-Phase Pipeline

```
Phase 1: CREATE
  - Template discovery
  - Task duplication (or blank fallback)
  - Add to project
  HARD-FAIL: If creation fails, transition aborts

Phase 2: CONFIGURE
  - Move to target section
  - Set due date
  - Wait for subtasks
  - Auto-cascade field seeding
  - Hierarchy placement (set_parent under holder)
  - Set assignee
  - Cascading section updates (Offer, Unit, Business)
  - Auto-complete source (if auto_complete_prior: true)
  SOFT-FAIL: Each sub-step logs warning on failure, continues

Phase 3: ACTIONS
  - Init action handlers (BOAB, AssetEdit, Videographer, Comment)
  - Each handler returns CreationResult
  SOFT-FAIL: Handler failures logged, transition continues

Phase 4: WIRE
  - Pipeline default wiring (Unit + OfferHolder dependents, DNA dependencies)
  - Init action dependency wiring (BOAB, AssetEdit -> Implementation)
  SOFT-FAIL: Wiring failures logged, transition continues
```

### 7.2 Rationale for 4 Phases (Not 5)

The prototype had 5 phases: Create, Configure, Wire, Actions, Dependencies. The stakeholder noted that Wire and Configure are both PUT calls and could be merged. Additionally, `set_subtask` (hierarchy placement) was missing and needed to be a Configure concern.

The redesign:
- **Merges** Wire (dependents/dependencies) into Phase 4 (after all entities exist)
- **Adds** hierarchy placement to Phase 2 (Configure)
- **Moves** Comments from built-in to init action handler (Phase 3)
- **Separates** init actions (Phase 3) from default wiring (Phase 4) because init actions may create entities that need to be wired

---

## 8. YAML Schema

### 8.1 Full Schema

```yaml
# config/lifecycle_stages.yaml

stages:
  outreach:
    project_gid: "1201753128450029"
    pipeline_stage: 1
    template_section: "TEMPLATES"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0
    dnc_action: deferred  # Self-loop deferred

    transitions:
      converted: sales
      did_not_convert: outreach
      auto_complete_prior: false

    cascading_sections:
      offer: "Sales Process"
      unit: "Engaged"
      business: "OPPORTUNITY"

    seeding:
      exclude_fields: []
      computed_fields: {}

    assignee:
      assignee_source: rep

    self_loop:
      max_iterations: 5

    init_actions:
      - type: create_comment

  sales:
    project_gid: "1200944186565610"
    pipeline_stage: 2
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 0
    dnc_action: create_new

    transitions:
      converted: onboarding
      did_not_convert: outreach
      auto_complete_prior: true

    cascading_sections:
      offer: "Sales Process"
      unit: "Next Steps"
      business: "OPPORTUNITY"

    seeding:
      exclude_fields: []
      computed_fields: {}

    assignee:
      assignee_source: rep

    init_actions:
      - type: create_comment

  onboarding:
    project_gid: "1201319387632570"
    pipeline_stage: 3
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 14
    dnc_action: reopen  # Reopen Sales on DNC

    transitions:
      converted: implementation
      did_not_convert: sales
      auto_complete_prior: true

    cascading_sections:
      offer: "ACTIVATING"
      unit: "Onboarding"
      business: "ONBOARDING"

    seeding:
      exclude_fields: []
      computed_fields:
        "Launch Date": "today"

    assignee:
      assignee_source: onboarding_specialist

    validation:
      pre_transition:
        required_fields: ["Contact Phone"]
        mode: warn

    init_actions:
      - type: products_check
        condition: "video*"
        action: request_source_videographer
        project_gid: "1207984018149338"
        holder_type: videography_holder
      - type: create_comment

  implementation:
    project_gid: "1201476141989746"
    pipeline_stage: 4
    template_section: "TEMPLATE"
    target_section: "OPPORTUNITY"
    due_date_offset_days: 30
    dnc_action: create_new

    transitions:
      converted: null  # Terminal for stages 1-4
      did_not_convert: outreach  # CORRECTED from 'sales'
      auto_complete_prior: true

    cascading_sections:
      offer: "IMPLEMENTING"
      unit: "Implementing"
      business: "IMPLEMENTING"

    seeding:
      exclude_fields: []
      computed_fields:
        "Launch Date": "today"

    assignee:
      assignee_source: implementation_lead

    init_actions:
      - type: play_creation
        play_type: backend_onboard_a_business
        project_gid: "1207507299545000"
        holder_type: dna_holder
        reopen_if_completed_within_days: 90
        wire_as_dependency: true
      - type: entity_creation
        entity_type: asset_edit
        project_gid: "1203992664400125"
        holder_type: asset_edit_holder
        wire_as_dependency: true
      - type: create_comment

# Dependency wiring rules
dependency_wiring:
  pipeline_default:
    dependents:
      - entity_type: unit
      - entity_type: offer_holder
    dependencies:
      - source: dna_holder
        filter: open_plays
```

### 8.2 YAML Correction

The current `lifecycle_stages.yaml` has `implementation.transitions.did_not_convert: sales`. Per stakeholder confirmation (Interview R13, R14), the correct target is `outreach`. This is corrected in the schema above.

---

## 9. Integration with Project Registry

### 9.1 How Lifecycle Config References Projects

The YAML uses `project_gid` directly (string GID). The central project registry (`core/project_registry.py`) provides the canonical source of GIDs, but the YAML stores them explicitly for two reasons:

1. YAML is the single source of truth for lifecycle configuration
2. GID resolution at config load time avoids runtime lookups

### 9.2 GID Resolution Timing

GIDs are resolved at YAML authoring time (static values in the file), not at runtime. The project registry is used for validation and for non-lifecycle code that needs project GIDs.

---

## 10. Error Handling Contract

### 10.1 Hard-Fail Operations

| Operation | When | Recovery |
|-----------|------|----------|
| Entity creation (Phase 1) | Task duplication/creation API fails | Transition aborts, error returned |
| Config validation | Malformed YAML at startup | Application fails to start |
| DAG integrity check | Invalid transition targets | Application fails to start |

### 10.2 Soft-Fail Operations

| Operation | When | Recovery |
|-----------|------|----------|
| Field seeding | Field not found on target | Warning logged, field skipped |
| Section placement | Section not found | Warning logged, task stays in default section |
| Due date setting | API error | Warning logged, no due date |
| Hierarchy placement | ProcessHolder not found or API error | Warning logged, task not nested |
| Assignee resolution | No assignee found | Warning logged, task unassigned |
| Init action execution | Handler error | Warning logged, transition continues |
| Comment creation | Stories API error | Warning logged, no comment |
| Dependency wiring | API error | Warning logged, no dependency |

### 10.3 Structured Log Events

| Event | Level | Fields |
|-------|-------|--------|
| `lifecycle_transition_complete` | INFO | source_stage, target_stage, outcome, actions, entities_created, warnings, duration_ms |
| `lifecycle_transition_error` | ERROR | source_gid, outcome, error |
| `lifecycle_duplicate_detected` | INFO | stage, existing_gid |
| `lifecycle_template_not_found` | WARN | stage, project_gid |
| `lifecycle_field_seeding_failed` | WARN | task_gid, error |
| `lifecycle_hierarchy_placement_failed` | WARN | task_gid, error |
| `lifecycle_set_assignee_failed` | WARN | task_gid, error |
| `lifecycle_no_assignee_found` | WARN | task_gid |
| `lifecycle_auto_completed` | INFO | process_gid, process_name |
| `lifecycle_process_reopened` | INFO | process_gid, target_stage |
| `lifecycle_dnc_deferred` | INFO | source_stage |
| `auto_cascade_fields_matched` | INFO | task_gid, field_count, fields |

---

## 11. Test Strategy

### 11.1 Unit Tests Per Module

| Module | Test File | Min Coverage |
|--------|-----------|-------------|
| `config.py` | `test_config.py` | Pydantic validation, DAG check, malformed YAML, missing keys |
| `engine.py` | `test_engine.py` | All 8 transition paths, terminal handling, DNC routing, fail-forward |
| `creation.py` | `test_creation.py` | Template creation, blank fallback, duplicate detection, configure phases |
| `seeding.py` | `test_seeding.py` | Auto-cascade matching, exclusions, computed fields, all field types |
| `sections.py` | `test_sections.py` | Cascading for each stage, failure handling |
| `completion.py` | `test_completion.py` | Explicit completion, already-completed skip |
| `wiring.py` | `test_wiring.py` | Default wiring, init action wiring |
| `reopen.py` | `test_reopen.py` | Find most recent, mark incomplete, move section, no-candidate case |
| `init_actions.py` | `test_init_actions.py` | All 4 handlers, conditions, reopen-or-create |

### 11.2 Integration Test Design

| Test | Coverage |
|------|----------|
| `test_outreach_to_sales.py` | Full CONVERTED flow: Outreach -> Sales |
| `test_sales_to_onboarding.py` | PCR parity: Sales -> Onboarding with all fields, sections, comments |
| `test_onboarding_to_implementation.py` | Full flow including BOAB, AssetEdit, Videographer |
| `test_implementation_terminal.py` | Terminal CONVERTED (no forward route) |
| `test_sales_dnc_outreach.py` | DNC create-new flow |
| `test_onboarding_dnc_reopen.py` | DNC reopen mechanics |
| `test_implementation_dnc_outreach.py` | DNC create-new from Implementation |
| `test_full_chain.py` | End-to-end: PipelineTransitionWorkflow -> Engine -> Asana mock |

### 11.3 Quality Gates

| Sprint | Gate | Criteria |
|--------|------|----------|
| Config + Registry | Gate 1 | Pydantic validation tests pass, DAG check works, all 8588+ existing tests pass |
| Engine + Creation + Seeding | Gate 2 | All 8 transition paths tested, auto-cascade seeding verified, PCR parity for Sales->Onboarding |
| Init Actions + Reopen | Gate 3 | All init action handlers tested, DNC reopen verified |
| Integration + Wiring | Gate 4 | Full chain integration tests pass, zero regressions |

---

## 12. Architecture Decision Records

### ADR-ARCH-001: Module Structure -- Service-per-Concern

**Status**: Accepted

**Context**: The prototype established a service-per-concern pattern (separate service class for creation, sections, completion, wiring). The alternatives are: (a) consolidated engine with inline logic, (b) pipeline-of-functions pattern, (c) keep service-per-concern.

**Decision**: Keep service-per-concern with one new service (ReopenService) and one new module (AutoCascadeSeeder).

**Rationale**:
- Each service has a clear single responsibility and can be tested in isolation
- Services are stateless (depend only on client + config), making them easy to construct in tests
- The prototype already established this pattern, and the lifecycle tests follow it
- A consolidated engine would make the 400+ line engine even larger
- A pipeline-of-functions pattern would lose the ability to inject different services for testing

**Consequences**:
- 10 source files in `lifecycle/` (same as prototype)
- Each service has its own test file
- Services communicate via the engine, not directly

---

### ADR-ARCH-002: Auto-Cascade Field Seeding (Runtime Matching)

**Status**: Accepted

**Context**: The existing `FieldSeeder` uses static field lists configured per pipeline stage (`business_cascade_fields`, `unit_cascade_fields`, `process_carry_through_fields`). The stakeholder requires zero-config field cascading where matching field names cascade automatically. Three approaches: (a) static lists in YAML (current), (b) runtime field-name matching, (c) schema registry mapping.

**Decision**: Runtime field-name matching with YAML exclusions only.

**Rationale**:
- Static lists require updating YAML every time a new custom field is added to Asana
- Schema registry would add complexity for no benefit (field names are consistent across projects, confirmed Interview R9)
- Runtime matching discovers fields automatically, reducing maintenance burden to zero for the common case
- YAML still controls exclusions and computed fields for the edge cases
- The existing `FieldSeeder.write_fields_async()` handles enum-to-GID resolution correctly, so the seeder only needs to provide field names + display values

**Consequences**:
- New `AutoCascadeSeeder` module replaces direct `FieldSeeder` usage in creation service
- `FieldSeeder` is retained as infrastructure for write/resolve operations
- One additional API call per creation (fetch target task custom field definitions)
- Adding a new custom field to Asana projects requires zero code changes

**Risks**:
- Field name collision across entity types could cascade incorrect values. Mitigated by exclusion lists.
- Performance: one extra API call per creation. Acceptable given lifecycle transitions are low-volume (tens per day, not thousands).

---

### ADR-ARCH-003: DNC Routing -- `dnc_action` per Source Stage

**Status**: Accepted

**Context**: DNC transitions have three distinct behaviors: create new process, reopen existing process, or defer (self-loop). The prototype treated all DNC transitions as create-new (same as CONVERTED). Three approaches: (a) detect from target stage properties, (b) add `dnc_action` field to source stage, (c) separate DNC routing table.

**Decision**: Add `dnc_action` field to `StageConfig` with values `create_new | reopen | deferred`.

**Rationale**:
- The DNC behavior is a property of the *source* stage (Onboarding always reopens, Sales always creates new)
- Adding it to the source stage config keeps routing logic in one place
- A separate routing table would duplicate stage references
- Detecting from target properties would require complex heuristics

**Consequences**:
- New `dnc_action` field on `StageConfig` Pydantic model
- Engine routes DNC to `_handle_dnc_async()` which dispatches on `dnc_action`
- New `ReopenService` handles the reopen case
- YAML must include `dnc_action` for all stages 1-4

---

### ADR-ARCH-004: Phase Pipeline -- 4 Phases (Merged)

**Status**: Accepted

**Context**: The prototype had 5 phases: Create, Configure, Wire, Actions, Dependencies. The stakeholder noted Wire and Configure are both PUT calls, and hierarchy placement (set_subtask) was missing. Three approaches: (a) keep 5 phases, (b) merge to 4 phases, (c) merge to 3 phases.

**Decision**: 4 phases: Create, Configure, Actions, Wire.

**Rationale**:
- Configure absorbs hierarchy placement (set_parent), section updates, and auto-completion
- Actions (Phase 3) must come before Wire (Phase 4) because init actions create entities that need to be wired as dependencies
- Merging all the way to 3 phases (Configure + Wire) would mean wiring happens before init action entities exist, violating the Asana constraint that entities need valid GIDs before wiring

**Consequences**:
- Comments move from built-in engine phase to init action handler
- Hierarchy placement moves from standalone step to Configure phase
- Phase ordering matches Asana API constraints (create GID, then PUT, then wire dependencies)

---

### ADR-ARCH-005: Reopen-or-Create as Init Action Pattern

**Status**: Accepted

**Context**: BOAB play creation uses a reopen-or-create pattern (find completed within 90 days, reopen vs create new). This same pattern applies to AssetEdit. Three approaches: (a) hardcode in handler, (b) make it a generic pattern, (c) configure via YAML.

**Decision**: Generic pattern configured via YAML `reopen_if_completed_within_days` and `always_create_new` params on `InitActionConfig`.

**Rationale**:
- Both BOAB and future entity types need this pattern
- YAML params make the threshold configurable without code changes
- `always_create_new: true` provides an escape hatch for entities that should never reopen
- The generic pattern is simple (search holder subtasks, check completion date, decide)

**Consequences**:
- `InitActionConfig` gains `reopen_if_completed_within_days` and `always_create_new` fields
- PlayCreationHandler and EntityCreationHandler share the reopen-or-create logic
- Future entity types (DNA plays, etc.) can use the same pattern via YAML config

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| PRD (spec) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-lifecycle-engine-hardening.md` | Read |
| Stakeholder Context | `/Users/tomtenuta/Code/autom8_asana/docs/planning/STAKEHOLDER-CONTEXT-lifecycle-hardening.md` | Read |
| Audit Report | `/Users/tomtenuta/Code/autom8_asana/docs/planning/AUDIT-workflow-resolution-platform.md` | Read |
| Transfer Doc | `/Users/tomtenuta/Code/autom8_asana/docs/transfer/TRANSFER-workflow-resolution-platform.md` | Read |
| Prototype TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-lifecycle-engine.md` | Read |
| Resolution TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-resolution-primitives.md` | Read |
| PCR (legacy) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/pipeline.py` | Read |
| FieldSeeder (legacy) | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/seeding.py` | Read |
| TemplateDiscovery | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/templates.py` | Read |
| SubtaskWaiter | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/automation/waiter.py` | Read |
| Prototype engine | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/engine.py` | Read |
| Prototype creation | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/creation.py` | Read |
| Prototype config | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/config.py` | Read |
| Prototype init_actions | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/init_actions.py` | Read |
| Prototype sections | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/sections.py` | Read |
| Prototype completion | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/completion.py` | Read |
| Prototype wiring | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/wiring.py` | Read |
| Prototype dispatch | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/lifecycle/dispatch.py` | Read |
| YAML config | `/Users/tomtenuta/Code/autom8_asana/config/lifecycle_stages.yaml` | Read |
| Resolution context | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/resolution/context.py` | Read |
| This TDD | `/Users/tomtenuta/Code/autom8_asana/docs/design/TDD-lifecycle-engine-hardening.md` | Written |

---

## FR Traceability

| PRD FR-ID | TDD Section | Module |
|-----------|-------------|--------|
| FR-ROUTE-001 | 2.2, 8.1 | engine.py |
| FR-ROUTE-002 | 2.2, 8.1 | engine.py |
| FR-ROUTE-003 | 2.2, 8.1 | engine.py |
| FR-ROUTE-004 | 2.2, 8.1 | engine.py |
| FR-DNC-001 | 2.2, 5.1 | engine.py |
| FR-DNC-002 | 2.8, 5.3 | reopen.py |
| FR-DNC-003 | 2.2, 5.1 | engine.py |
| FR-DNC-004 | 2.2, 5.1 | engine.py |
| FR-CREATE-001 | 2.3 | creation.py |
| FR-CREATE-002 | 2.9 | init_actions.py |
| FR-CREATE-003 | 2.9, 6.2 | init_actions.py |
| FR-CREATE-004 | 2.9 | init_actions.py |
| FR-DUP-001 | 2.3 | creation.py |
| FR-DUP-002 | 6.1 | init_actions.py |
| FR-SEED-001 | 2.4, 4.1 | seeding.py |
| FR-SEED-002 | 2.4, 4.3 | seeding.py |
| FR-SEED-003 | 2.3 | creation.py |
| FR-ASSIGN-001 | 2.3 | creation.py |
| FR-HIER-001 | 2.3 | creation.py |
| FR-COMMENT-001 | 2.9 | init_actions.py |
| FR-COMMENT-002 | 2.9 | init_actions.py |
| FR-VALID-001 | 2.2 | engine.py |
| FR-COMPLETE-001 | 2.6 | completion.py |
| FR-TMPL-001 | 2.3 | creation.py |
| FR-CONFIG-001 | 2.10 | project_registry.py |
| FR-CONFIG-002 | 2.1 | config.py |
| FR-CONFIG-003 | 2.1 | config.py |
| FR-WIRE-001 | 2.7 | wiring.py |
| FR-WIRE-002 | 2.9 | init_actions.py |
| FR-ERR-001 | 2.2, 10.1, 10.2 | engine.py |
| FR-ERR-002 | 2.3 | creation.py |
| FR-AUDIT-001 | 2.2, 10.3 | engine.py |
