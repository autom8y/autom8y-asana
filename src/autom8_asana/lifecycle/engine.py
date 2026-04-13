"""LifecycleEngine: 4-phase pipeline orchestrator for lifecycle transitions.

Per TDD-lifecycle-engine-hardening Section 2.2:
- Orchestrates Create -> Configure -> Actions -> Wire pipeline
- Routes DNC transitions: create_new, reopen, deferred
- Accumulates phase results into composite AutomationResult
- Fail-forward with diagnostics (hard fail only on Phase 1 creation failure)

FR Coverage: FR-ROUTE-001..004, FR-DNC-001..004, FR-ERR-001, FR-AUDIT-001

Error Contract:
- Top-level except Exception at handle_transition_async boundary (boundary guard)
- Phase methods catch their own exceptions and report as warnings (fail-forward)
- Hard failure only on entity creation failure (Phase 1)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from autom8y_log import get_logger

from autom8_asana.core.timing import elapsed_ms

# Re-export canonical result types from their authoritative modules so that
# callers importing from engine (e.g., tests) continue to work unchanged.
from autom8_asana.lifecycle.completion import (
    CompletionResult as CompletionResult,  # noqa: TC001
)
from autom8_asana.lifecycle.creation import (
    CreationResult as CreationResult,  # noqa: TC001
)
from autom8_asana.lifecycle.reopen import ReopenResult as ReopenResult  # noqa: TC001
from autom8_asana.lifecycle.sections import (
    CascadeResult as CascadeResult,  # noqa: TC001
)
from autom8_asana.lifecycle.wiring import WiringResult as WiringResult  # noqa: TC001
from autom8_asana.persistence.models import AutomationResult
from autom8_asana.resolution.context import ResolutionContext

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.config import (
        CascadingSectionConfig,
        InitActionConfig,
        LifecycleConfig,
        StageConfig,
    )
    from autom8_asana.lifecycle.observation import StageTransitionEmitter
    from autom8_asana.models.business.process import Process

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Service result data classes
# ---------------------------------------------------------------------------


@dataclass
class LifecycleActionResult:
    """Result of a single init action (Phase 3)."""

    success: bool
    entity_gid: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Service protocols -- implementations live in sibling modules
# ---------------------------------------------------------------------------


@runtime_checkable
class CreationServiceProtocol(Protocol):
    """Protocol for entity creation (Phase 1)."""

    async def create_process_async(
        self,
        target_stage: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
    ) -> CreationResult: ...


@runtime_checkable
class SectionServiceProtocol(Protocol):
    """Protocol for cascading section updates (Phase 2)."""

    async def cascade_async(
        self,
        cascading_sections: CascadingSectionConfig,
        ctx: ResolutionContext,
    ) -> CascadeResult: ...


@runtime_checkable
class CompletionServiceProtocol(Protocol):
    """Protocol for source process auto-completion (Phase 2)."""

    async def complete_source_async(
        self,
        source_process: Process,
    ) -> CompletionResult: ...


@runtime_checkable
class InitActionRegistryProtocol(Protocol):
    """Protocol for init action execution (Phase 3)."""

    async def execute_actions_async(
        self,
        actions: list[InitActionConfig],
        created_entity_gid: str,
        ctx: ResolutionContext,
        source_process: Process,
    ) -> list[LifecycleActionResult]: ...


@runtime_checkable
class WiringServiceProtocol(Protocol):
    """Protocol for dependency wiring (Phase 4)."""

    async def wire_defaults_async(
        self,
        entity_gid: str,
        stage_name: str,
        ctx: ResolutionContext,
    ) -> WiringResult: ...


@runtime_checkable
class ReopenServiceProtocol(Protocol):
    """Protocol for DNC reopen mechanics."""

    async def reopen_async(
        self,
        target_stage: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
    ) -> ReopenResult: ...


# ---------------------------------------------------------------------------
# TransitionResult accumulator
# ---------------------------------------------------------------------------


class TransitionResult:
    """Accumulator for transition phase results.

    Tracks actions, created/updated entities, warnings, and hard failures
    across all 4 pipeline phases. Success is determined by absence of a
    hard_failure -- soft failures (warnings) do not prevent success.
    """

    def __init__(self, source_process_gid: str) -> None:
        self.source_process_gid = source_process_gid
        self.actions_executed: list[str] = []
        self.entities_created: list[str] = []
        self.entities_updated: list[str] = []
        self.warnings: list[str] = []
        self.hard_failure: str | None = None

    @property
    def success(self) -> bool:
        """True if no hard failure occurred."""
        return self.hard_failure is None

    def add_warning(self, msg: str) -> None:
        """Record a soft failure (non-blocking)."""
        self.warnings.append(msg)
        logger.warning("lifecycle_phase_warning", warning=msg)

    def add_action(self, action: str) -> None:
        """Record a completed action."""
        self.actions_executed.append(action)

    def add_entity_created(self, gid: str) -> None:
        """Record a created entity GID."""
        self.entities_created.append(gid)

    def add_entity_updated(self, gid: str) -> None:
        """Record an updated entity GID."""
        self.entities_updated.append(gid)

    def fail(self, error: str) -> None:
        """Record a hard failure (blocks success)."""
        self.hard_failure = error


# ---------------------------------------------------------------------------
# LifecycleEngine
# ---------------------------------------------------------------------------


class LifecycleEngine:
    """Orchestrates pipeline lifecycle transitions.

    4-phase pipeline:
      Phase 1: CREATE    -- Template-based entity creation
      Phase 2: CONFIGURE -- Cascading sections, auto-completion, field seeding
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
        *,
        creation_service: CreationServiceProtocol | None = None,
        section_service: SectionServiceProtocol | None = None,
        completion_service: CompletionServiceProtocol | None = None,
        init_action_registry: InitActionRegistryProtocol | None = None,
        wiring_service: WiringServiceProtocol | None = None,
        reopen_service: ReopenServiceProtocol | None = None,
        transition_emitter: StageTransitionEmitter | None = None,
    ) -> None:
        self._client = client
        self._config = config

        # Service dependencies -- injected or lazily constructed from
        # concrete implementations in sibling modules.
        self._creation_service = creation_service or _import_creation_service(client, config)
        self._section_service = section_service or _import_section_service(client)
        self._completion_service = completion_service or _import_completion_service(client, config)
        self._init_action_registry = init_action_registry or _DefaultInitActionRegistry(
            client, config
        )
        self._wiring_service = wiring_service or _import_wiring_service(client, config)
        self._reopen_service = reopen_service or _import_reopen_service(client)

        # Observation layer -- optional, fire-and-forget
        self._transition_emitter = transition_emitter

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def handle_transition_async(
        self,
        source_process: Process,
        outcome: str,
    ) -> AutomationResult:
        """Handle a pipeline stage transition.

        This is the main entry point for lifecycle automation.

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
                logger.error(
                    "lifecycle_unknown_stage",
                    stage=source_stage_name,
                    source_gid=source_process.gid,
                )
                return self._build_result(
                    f"lifecycle_{source_stage_name}_unknown",
                    source_process,
                    start_time,
                    result,
                    error=f"No stage config for: {source_stage_name}",
                )

            # --- Resolve target stage ---
            target_stage = self._config.get_target_stage(source_stage_name, outcome)

            if target_stage is None:
                # Terminal state (e.g., Implementation CONVERTED for stages 1-4)
                return await self._handle_terminal_async(
                    source_process, source_stage, outcome, start_time, result
                )

            logger.info(
                "lifecycle_transition_start",
                source_stage=source_stage_name,
                target_stage=target_stage.name,
                outcome=outcome,
                source_gid=source_process.gid,
            )

            # --- Pre-transition validation ---
            if source_stage.validation and source_stage.validation.pre_transition:
                validation = source_stage.validation.pre_transition
                missing = self._check_required_fields(source_process, validation.required_fields)
                if missing:
                    if validation.mode == "block":
                        return self._build_result(
                            f"lifecycle_{source_stage_name}_validation_blocked",
                            source_process,
                            start_time,
                            result,
                            error=f"Pre-validation failed: {missing}",
                        )
                    result.add_warning(f"Pre-validation: missing {missing}")
                result.add_action("pre_validation")

            # --- DNC routing decision ---
            if outcome == "did_not_convert":
                return await self._handle_dnc_async(
                    source_process,
                    source_stage,
                    target_stage,
                    start_time,
                    result,
                )

            # --- CONVERTED: Standard 4-phase creation pipeline ---
            async with ResolutionContext(
                self._client,
                trigger_entity=source_process,
            ) as ctx:
                await self._run_pipeline_async(
                    source_stage, target_stage, ctx, source_process, result
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
                duration_ms=elapsed_ms(start_time),
            )

            automation_result = self._build_result(
                f"lifecycle_{source_stage_name}_to_{target_stage.name}",
                source_process,
                start_time,
                result,
            )

            # --- Emit stage transition observation ---
            await self._emit_transition(
                source_process=source_process,
                source_stage_name=source_stage_name,
                target_stage_name=target_stage.name,
                target_pipeline_stage=target_stage.pipeline_stage,
                transition_type=outcome,
                automation_result=automation_result,
            )

            return automation_result

        except Exception as e:  # BROAD-CATCH: boundary guard at orchestrator level
            logger.error(
                "lifecycle_transition_error",
                source_gid=source_process.gid,
                outcome=outcome,
                error=str(e),
            )
            result.fail(str(e))
            return self._build_result(
                "lifecycle_error",
                source_process,
                start_time,
                result,
            )

    # ------------------------------------------------------------------
    # 4-phase pipeline
    # ------------------------------------------------------------------

    async def _run_pipeline_async(
        self,
        source_stage: StageConfig,
        target_stage: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
        result: TransitionResult,
    ) -> None:
        """Run the 4-phase creation pipeline.

        Phase ordering is load-bearing:
          1. CREATE  -- must produce entity GID before anything else
          2. CONFIGURE -- sections, auto-complete, field seeding
          3. ACTIONS -- init actions (BOAB, AssetEdit, etc.)
          4. WIRE -- dependency wiring (requires all GIDs)
        """
        # Phase 1: CREATE
        creation_result = await self._creation_service.create_process_async(
            target_stage, ctx, source_process
        )
        if not creation_result.success:
            result.fail(f"Process creation failed: {creation_result.error}")
            return

        entity_gid = creation_result.entity_gid or ""
        result.add_entity_created(entity_gid)
        result.add_action("create_process")

        # Phase 2: CONFIGURE
        await self._phase_configure_async(source_stage, target_stage, ctx, source_process, result)

        # Phase 3: ACTIONS
        await self._phase_actions_async(target_stage, entity_gid, ctx, source_process, result)

        # Phase 4: WIRE
        await self._phase_wire_async(target_stage, entity_gid, ctx, result)

    async def _phase_configure_async(
        self,
        source_stage: StageConfig,
        target_stage: StageConfig,
        ctx: ResolutionContext,
        source_process: Process,
        result: TransitionResult,
    ) -> None:
        """Phase 2: Cascading sections + auto-completion.

        Cascading sections update Offer, Unit, and Business sections
        for the target stage. Auto-completion marks the source process
        as complete when the transition config says auto_complete_prior: true.
        """
        # Cascading sections
        try:
            section_result = await self._section_service.cascade_async(
                target_stage.cascading_sections, ctx
            )
            if section_result.updates:
                for gid in section_result.updates:
                    result.add_entity_updated(gid)
                result.add_action("cascade_sections")
        except Exception as e:  # BROAD-CATCH: fail-forward
            result.add_warning(f"Cascade sections failed: {e}")

        # Auto-completion (explicit per-transition flag, FR-COMPLETE-001)
        if source_stage.transitions.auto_complete_prior:
            try:
                completion_result = await self._completion_service.complete_source_async(
                    source_process
                )
                if completion_result.completed:
                    for gid in completion_result.completed:
                        result.add_entity_updated(gid)
                    result.add_action("auto_complete_source")
            except Exception as e:  # BROAD-CATCH: fail-forward
                result.add_warning(f"Auto-completion failed: {e}")

    async def _phase_actions_async(
        self,
        target_stage: StageConfig,
        created_entity_gid: str,
        ctx: ResolutionContext,
        source_process: Process,
        result: TransitionResult,
    ) -> None:
        """Phase 3: Init actions.

        Delegates to InitActionRegistry which dispatches each action_config
        to its registered handler. Unknown action types produce warnings.
        """
        if not target_stage.init_actions:
            return

        try:
            action_results = await self._init_action_registry.execute_actions_async(
                target_stage.init_actions,
                created_entity_gid,
                ctx,
                source_process,
            )
            for i, action_result in enumerate(action_results):
                action_type = target_stage.init_actions[i].type
                if isinstance(action_result, BaseException):
                    result.add_warning(f"Init action {action_type} failed: {action_result}")
                elif action_result.success:
                    result.add_action(f"init_{action_type}")
                    if action_result.entity_gid:
                        result.add_entity_created(action_result.entity_gid)
                else:
                    result.add_warning(f"Init action {action_type} failed: {action_result.error}")
        except Exception as e:  # BROAD-CATCH: fail-forward
            result.add_warning(f"Init actions phase failed: {e}")

    async def _phase_wire_async(
        self,
        target_stage: StageConfig,
        entity_gid: str,
        ctx: ResolutionContext,
        result: TransitionResult,
    ) -> None:
        """Phase 4: Dependency wiring.

        Wires standard dependents (Unit, OfferHolder) and dependencies
        (open DNA plays) plus any init-action-produced entity dependencies.
        """
        try:
            wiring_result = await self._wiring_service.wire_defaults_async(
                entity_gid, target_stage.name, ctx
            )
            if wiring_result.wired:
                result.add_action("wire_dependencies")
        except Exception as e:  # BROAD-CATCH: fail-forward
            result.add_warning(f"Dependency wiring failed: {e}")

    # ------------------------------------------------------------------
    # DNC routing
    # ------------------------------------------------------------------

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
            automation_result = self._build_result(
                f"lifecycle_{source_stage.name}_dnc_deferred",
                source_process,
                start_time,
                result,
            )
            await self._emit_transition(
                source_process=source_process,
                source_stage_name=source_stage.name,
                target_stage_name=source_stage.name,  # self-loop
                target_pipeline_stage=source_stage.pipeline_stage,
                transition_type="did_not_convert",
                automation_result=automation_result,
            )
            return automation_result

        if dnc_action == "reopen":
            async with ResolutionContext(
                self._client,
                trigger_entity=source_process,
            ) as ctx:
                try:
                    reopen_result = await self._reopen_service.reopen_async(
                        target_stage, ctx, source_process
                    )
                    if reopen_result.success:
                        result.add_action("reopen_process")
                        if reopen_result.entity_gid:
                            result.add_entity_updated(reopen_result.entity_gid)
                    else:
                        result.add_warning(f"Reopen failed: {reopen_result.error}")
                except Exception as e:  # BROAD-CATCH: fail-forward
                    result.add_warning(f"Reopen failed: {e}")

            logger.info(
                "lifecycle_dnc_reopen_complete",
                source_stage=source_stage.name,
                target_stage=target_stage.name,
                actions=result.actions_executed,
                duration_ms=elapsed_ms(start_time),
            )

            automation_result = self._build_result(
                f"lifecycle_{source_stage.name}_dnc_reopen",
                source_process,
                start_time,
                result,
            )
            await self._emit_transition(
                source_process=source_process,
                source_stage_name=source_stage.name,
                target_stage_name=target_stage.name,
                target_pipeline_stage=target_stage.pipeline_stage,
                transition_type="reopen",
                automation_result=automation_result,
            )
            return automation_result

        # dnc_action == "create_new" -- same pipeline as CONVERTED
        async with ResolutionContext(
            self._client,
            trigger_entity=source_process,
        ) as ctx:
            await self._run_pipeline_async(source_stage, target_stage, ctx, source_process, result)

        logger.info(
            "lifecycle_dnc_create_complete",
            source_stage=source_stage.name,
            target_stage=target_stage.name,
            outcome="did_not_convert",
            actions=result.actions_executed,
            entities_created=result.entities_created,
            duration_ms=elapsed_ms(start_time),
        )

        automation_result = self._build_result(
            f"lifecycle_{source_stage.name}_dnc_{target_stage.name}",
            source_process,
            start_time,
            result,
        )
        await self._emit_transition(
            source_process=source_process,
            source_stage_name=source_stage.name,
            target_stage_name=target_stage.name,
            target_pipeline_stage=target_stage.pipeline_stage,
            transition_type="did_not_convert",
            automation_result=automation_result,
        )
        return automation_result

    # ------------------------------------------------------------------
    # Terminal handling
    # ------------------------------------------------------------------

    async def _handle_terminal_async(
        self,
        source_process: Process,
        source_stage: StageConfig,
        outcome: str,
        start_time: float,
        result: TransitionResult,
    ) -> AutomationResult:
        """Handle terminal state (no target stage).

        Terminal transitions produce no new entities. They may trigger
        auto-completion of the source process.
        """
        # Auto-complete source if configured (Fixes D-LC-004: actually call
        # CompletionService instead of just recording the action string)
        if outcome == "converted" and source_stage.transitions.auto_complete_prior:
            try:
                completion_result = await self._completion_service.complete_source_async(
                    source_process
                )
                if completion_result.completed:
                    for gid in completion_result.completed:
                        result.add_entity_updated(gid)
                    result.add_action("auto_complete_source")
            except Exception as e:  # BROAD-CATCH: fail-forward
                result.add_warning(f"Terminal auto-completion failed: {e}")

        result.add_action("terminal")

        logger.info(
            "lifecycle_terminal",
            source_stage=source_stage.name,
            outcome=outcome,
            duration_ms=elapsed_ms(start_time),
        )

        automation_result = self._build_result(
            f"lifecycle_{source_stage.name}_terminal",
            source_process,
            start_time,
            result,
        )
        await self._emit_transition(
            source_process=source_process,
            source_stage_name=source_stage.name,
            target_stage_name=source_stage.name,  # terminal: stays in same stage
            target_pipeline_stage=source_stage.pipeline_stage,
            transition_type="terminal",
            automation_result=automation_result,
        )
        return automation_result

    # ------------------------------------------------------------------
    # Observation emission
    # ------------------------------------------------------------------

    async def _emit_transition(
        self,
        source_process: Process,
        source_stage_name: str,
        target_stage_name: str,
        target_pipeline_stage: int,
        transition_type: str,
        automation_result: AutomationResult,
    ) -> None:
        """Emit a stage transition observation record (fire-and-forget).

        Called after _build_result() for successful transitions. Swallows all
        exceptions to preserve the fail-forward contract.
        """
        if self._transition_emitter is None:
            return

        if not automation_result.success:
            return

        try:
            from datetime import UTC, datetime

            from autom8_asana.lifecycle.observation import StageTransitionRecord

            record = StageTransitionRecord(
                entity_gid=source_process.gid,
                entity_type="Process",
                business_gid=getattr(source_process, "business_gid", None),
                from_stage=source_stage_name,
                to_stage=target_stage_name,
                pipeline_stage_num=target_pipeline_stage,
                transition_type=transition_type,
                entered_at=datetime.now(UTC),
                exited_at=None,
                automation_result_id=automation_result.rule_id,
                duration_ms=automation_result.execution_time_ms,
            )
            await self._transition_emitter.emit(record)
        except Exception:  # BROAD-CATCH: fire-and-forget (fail-forward)
            logger.warning(
                "stage_transition_emission_failed",
                source_gid=source_process.gid,
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_required_fields(self, process: Process, required_fields: list[str]) -> list[str]:
        """Check required fields on process. Returns list of missing."""
        missing = []
        for field_name in required_fields:
            value = getattr(process, field_name.lower().replace(" ", "_"), None)
            if value is None or isinstance(value, str) and not value.strip():
                missing.append(field_name)
        return missing

    def _build_result(
        self,
        rule_id: str,
        process: Process,
        start_time: float,
        tr: TransitionResult,
        error: str | None = None,
    ) -> AutomationResult:
        """Build AutomationResult from TransitionResult accumulator."""
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
            execution_time_ms=elapsed_ms(start_time),
        )


# ---------------------------------------------------------------------------
# Default init action registry adapter
# ---------------------------------------------------------------------------


class _DefaultInitActionRegistry:
    """Adapts the existing HANDLER_REGISTRY dict to InitActionRegistryProtocol.

    Dispatches each init action config to the matching handler from the
    registry. Unknown types produce a failed LifecycleActionResult with a warning.
    """

    def __init__(self, client: AsanaClient, config: LifecycleConfig) -> None:
        self._client = client
        self._config = config

    async def execute_actions_async(
        self,
        actions: list[InitActionConfig],
        created_entity_gid: str,
        ctx: ResolutionContext,
        source_process: Process,
    ) -> list[LifecycleActionResult]:
        """Execute all init actions in parallel with bounded concurrency."""
        from autom8_asana.core.concurrency import gather_with_semaphore
        from autom8_asana.lifecycle.init_actions import HANDLER_REGISTRY

        coros = [
            self._execute_one(
                action_config,
                created_entity_gid,
                ctx,
                source_process,
                HANDLER_REGISTRY,
            )
            for action_config in actions
        ]
        return await gather_with_semaphore(coros, concurrency=4, label="init_actions")

    async def _execute_one(
        self,
        action_config: InitActionConfig,
        created_entity_gid: str,
        ctx: ResolutionContext,
        source_process: Process,
        handler_registry: dict[str, Any],
    ) -> LifecycleActionResult:
        """Execute a single init action, returning LifecycleActionResult."""
        handler_cls = handler_registry.get(action_config.type)
        if handler_cls is None:
            return LifecycleActionResult(
                success=False,
                error=f"Unknown init action: {action_config.type}",
            )

        handler = handler_cls(self._client, self._config)
        try:
            creation_result = await handler.execute_async(
                ctx, created_entity_gid, action_config, source_process
            )
            return LifecycleActionResult(
                success=creation_result.success,
                entity_gid=creation_result.entity_gid or "",
                error=creation_result.error or "",
            )
        except Exception as e:  # BROAD-CATCH: per-action isolation
            return LifecycleActionResult(success=False, error=str(e))


# ---------------------------------------------------------------------------
# Lazy service constructors (avoids import-time coupling)
# ---------------------------------------------------------------------------


def _import_creation_service(
    client: AsanaClient, config: LifecycleConfig
) -> CreationServiceProtocol:
    """Lazily import and construct EntityCreationService."""
    from autom8_asana.lifecycle.creation import EntityCreationService

    return EntityCreationService(client, config)


def _import_section_service(client: AsanaClient) -> SectionServiceProtocol:
    """Lazily import and construct CascadingSectionService."""
    from autom8_asana.lifecycle.sections import CascadingSectionService

    return CascadingSectionService(client)


def _import_completion_service(
    client: AsanaClient, config: LifecycleConfig
) -> CompletionServiceProtocol:
    """Lazily import and construct CompletionService."""
    from autom8_asana.lifecycle.completion import CompletionService

    return CompletionService(client)


def _import_wiring_service(client: AsanaClient, config: LifecycleConfig) -> WiringServiceProtocol:
    """Lazily import and construct DependencyWiringService."""
    from autom8_asana.lifecycle.wiring import DependencyWiringService

    return DependencyWiringService(client, config)


def _import_reopen_service(client: AsanaClient) -> ReopenServiceProtocol:
    """Import and construct ReopenService."""
    from autom8_asana.lifecycle.reopen import ReopenService

    return ReopenService(client)
