"""Pipeline conversion automation rule.

Per FR-003: PipelineConversionRule triggers on section change to CONVERTED.
Per ADR-0103: Automation Rule Protocol.
Per FR-HIER-001: Hierarchy placement under ProcessHolder.
Per FR-HIER-002: Position new process after source process.
Per FR-ASSIGN-001: Assignee from rep field cascade (Unit.rep -> Business.rep).
Per FR-COMMENT-001: Onboarding comment creation on new Process.

PipelineConversionRule is a built-in rule that automates pipeline transitions,
for example converting a Sales process to an Onboarding process when the
Sales process moves to the "Converted" section.
"""

from __future__ import annotations

import time
from datetime import date
from typing import TYPE_CHECKING, Any, Literal, cast

from autom8y_log import get_logger

from autom8_asana.automation.base import TriggerCondition
from autom8_asana.automation.config import AssigneeConfig
from autom8_asana.automation.events.types import EventType
from autom8_asana.automation.seeding import FieldSeeder
from autom8_asana.automation.validation import ValidationResult
from autom8_asana.core.creation import (
    compute_due_date,
    discover_template_async,
    duplicate_from_template_async,
    generate_entity_name,
    place_in_section_async,
    wait_for_subtasks_async,
)
from autom8_asana.core.exceptions import ASANA_API_ERRORS
from autom8_asana.core.timing import elapsed_ms
from autom8_asana.models.business import Process, ProcessSection, ProcessType
from autom8_asana.persistence.models import AutomationResult
from autom8_asana.persistence.session import SaveSession

if TYPE_CHECKING:
    from autom8_asana.automation.context import AutomationContext
    from autom8_asana.models.base import AsanaResource

logger = get_logger(__name__)


class PipelineConversionRule:
    """Built-in rule for Sales -> Onboarding pipeline conversion.

    Per FR-003: Implements pipeline conversion automation.
    Per ADR-0103: Implements AutomationRule protocol.

    This rule triggers when:
    1. Entity is a Process
    2. Event is "section_changed"
    3. Process type matches source_type (e.g., SALES)
    4. New section matches trigger_section (e.g., CONVERTED)

    When triggered, it:
    1. Finds the target project for the target process type
    2. Discovers template task in target project
    3. Creates new process from template
    4. Seeds fields from hierarchy (Business, Unit) and source process
    5. Links new process to unit hierarchy

    Example:
        rule = PipelineConversionRule(
            source_type=ProcessType.SALES,
            target_type=ProcessType.ONBOARDING,
            trigger_section=ProcessSection.CONVERTED,
        )

        # Register with automation engine
        client.automation.register(rule)

        # Rule triggers when Sales process moves to Converted section
    """

    def __init__(
        self,
        source_type: ProcessType = ProcessType.SALES,
        target_type: ProcessType = ProcessType.ONBOARDING,
        trigger_section: ProcessSection = ProcessSection.CONVERTED,
        required_source_fields: list[str] | None = None,
        validate_mode: Literal["warn", "block"] = "warn",
    ) -> None:
        """Initialize PipelineConversionRule.

        Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT/ADR-0018: Optional validation.

        Args:
            source_type: Process type that triggers conversion (default: SALES).
            target_type: Process type to create (default: ONBOARDING).
            trigger_section: Section that triggers conversion (default: CONVERTED).
            required_source_fields: Optional list of field names that must be
                present and non-empty on the source process before transition.
                Validation is performed via _validate_pre_transition().
            validate_mode: Validation behavior on failure:
                - "warn" (default): Log warnings but proceed with transition.
                - "block": Return failure result, do not execute transition.
        """
        self._source_type = source_type
        self._target_type = target_type
        self._trigger_section = trigger_section
        self._required_source_fields = required_source_fields or []
        self._validate_mode = validate_mode

        # Build trigger condition
        self._trigger = TriggerCondition(
            entity_type="Process",
            event=EventType.SECTION_CHANGED,
            filters={
                "process_type": source_type.value,
                "section": trigger_section.value,
            },
        )

    @property
    def id(self) -> str:
        """Unique rule identifier.

        Returns:
            Rule ID in format "pipeline_{source}_to_{target}".
        """
        return f"pipeline_{self._source_type.value}_to_{self._target_type.value}"

    @property
    def name(self) -> str:
        """Human-readable rule name.

        Returns:
            Rule name in format "Pipeline: {Source} to {Target}".
        """
        return (
            f"Pipeline: {self._source_type.value.title()} "
            f"to {self._target_type.value.title()}"
        )

    @property
    def trigger(self) -> TriggerCondition:
        """Trigger condition for this rule.

        Returns:
            TriggerCondition that matches Process section changes.
        """
        return self._trigger

    def should_trigger(
        self,
        entity: AsanaResource,
        event: str,
        context: dict[str, Any],
    ) -> bool:
        """Check if rule should trigger for this entity/event.

        Per FR-003: Validates Process type, event, and section.

        Args:
            entity: The entity that triggered the event.
            event: The event type that occurred.
            context: Additional context (e.g., old_section, new_section).

        Returns:
            True if rule should trigger, False otherwise.
        """
        # Check basic trigger condition match
        if not self._trigger.matches(entity, event, context):
            return False

        # Additional validation: verify it's actually a Process (or MockProcess in tests)
        entity_type_name = type(entity).__name__
        if entity_type_name not in ("Process", "MockProcess"):
            return False

        # Verify process type matches source type
        if hasattr(entity, "process_type"):
            process_type = entity.process_type
            # Handle enum value comparison
            actual_type = (
                process_type.value if hasattr(process_type, "value") else process_type
            )
            if actual_type != self._source_type.value:
                return False

        return True

    async def execute_async(
        self,
        entity: AsanaResource,
        context: AutomationContext,
    ) -> AutomationResult:
        """Execute pipeline conversion.

        Per FR-003: Creates target process from template with seeded fields.

        Algorithm:
        1. Get target project GID from config
        2. Discover template in target project
        3. Create new task from template
        4. Seed fields from hierarchy and source process
        5. Return result with created entity info

        Args:
            entity: The Process that triggered the rule.
            context: Automation execution context.

        Returns:
            AutomationResult with execution details.
        """
        start_time = time.perf_counter()

        actions_executed: list[str] = []
        entities_created: list[str] = []
        entities_updated: list[str] = []
        enhancement_results: dict[str, bool | int] = {}

        try:
            # Check entity type by name (supports both real Process and mocks)
            entity_type_name = type(entity).__name__
            if entity_type_name not in ("Process", "MockProcess"):
                return AutomationResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    triggered_by_gid=entity.gid,
                    triggered_by_type=entity_type_name,
                    success=False,
                    error=f"Expected Process, got {entity_type_name}",
                    execution_time_ms=elapsed_ms(start_time),
                )

            # Cast to Process for type checker - we've verified the type above
            # This also works with MockProcess in tests since we check class name
            source_process = cast(Process, entity)

            # Pre-transition validation (ADR-0018)
            pre_validation: ValidationResult | None = None
            if self._required_source_fields:
                pre_validation = self._validate_pre_transition(source_process)
                actions_executed.append("pre_validation")

                if not pre_validation.valid and self._validate_mode == "block":
                    # Validation failed and mode is "block" - stop transition
                    return AutomationResult(
                        rule_id=self.id,
                        rule_name=self.name,
                        triggered_by_gid=entity.gid,
                        triggered_by_type="Process",
                        actions_executed=actions_executed,
                        success=False,
                        error=f"Pre-transition validation failed: {pre_validation.errors}",
                        execution_time_ms=elapsed_ms(start_time),
                        pre_validation=pre_validation,
                    )
                # If mode is "warn", continue with transition even if validation failed

            # Step 1: Get target stage configuration from config
            stage = context.config.get_pipeline_stage(self._target_type.value)
            if not stage:
                return AutomationResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    triggered_by_gid=entity.gid,
                    triggered_by_type="Process",
                    success=False,
                    error=(
                        f"No target project configured for "
                        f"{self._target_type.value} pipeline"
                    ),
                    execution_time_ms=elapsed_ms(start_time),
                )

            target_project_gid = stage.project_gid
            actions_executed.append("lookup_target_project")

            # Step 2: Discover template in target project
            # IMP-13: discover_template_async includes num_subtasks in opt_fields
            # to avoid a separate subtasks_async call for the subtask count.
            template_task = await discover_template_async(
                context.client,
                target_project_gid,
                template_section=stage.template_section,
            )

            if not template_task:
                return AutomationResult(
                    rule_id=self.id,
                    rule_name=self.name,
                    triggered_by_gid=entity.gid,
                    triggered_by_type="Process",
                    success=False,
                    error=(
                        f"No template found in project {target_project_gid} "
                        f"for {self._target_type.value} pipeline"
                    ),
                    execution_time_ms=elapsed_ms(start_time),
                )

            actions_executed.append("discover_template")

            # Get hierarchy references (may be None) - needed for name generation
            business = source_process.business
            unit = source_process.unit

            # Step 3: Duplicate task from template (copies subtasks)
            # Per FR-DUP-001: Use duplicate_async to copy template with subtasks
            # Generate name from template pattern, replacing placeholders with actual values
            new_task_name = generate_entity_name(
                template_name=template_task.name,
                business=business,
                unit=unit,
                fallback_name=f"New {self._target_type.value.title()}",
            )

            # Step 3a: Get template subtask count for waiter
            # IMP-13: Use num_subtasks from template discovery response
            # instead of making a separate subtasks_async API call.
            expected_subtask_count = getattr(template_task, "num_subtasks", 0) or 0

            # Step 3b: Duplicate the template task with subtasks and notes
            new_task = await duplicate_from_template_async(
                context.client,
                template_task,
                new_task_name,
            )

            entities_created.append(new_task.gid)
            actions_executed.append("duplicate_task")

            # Step 3c: Add new task to target project
            # (duplicate creates task in same project as template, we need target project)
            await context.client.tasks.add_to_project_async(
                new_task.gid,
                target_project_gid,
            )
            actions_executed.append("add_to_project")

            # Step 3e: Move task to target section (G3 Gap Fix)
            # Per PipelineStage: Place new task in configured target section
            if stage.target_section:
                section_placed = await place_in_section_async(
                    context.client,
                    new_task.gid,
                    target_project_gid,
                    stage.target_section,
                )
                if section_placed:
                    actions_executed.append("section_placement")
                enhancement_results["section_placement"] = section_placed

            # Step 3f: Set due date if configured (G4 Gap Fix)
            # Per PipelineStage: Set due date relative to today
            if stage.due_date_offset_days is not None:
                due_date_set = False
                try:
                    due_on = compute_due_date(stage.due_date_offset_days)
                    await context.client.tasks.update_async(
                        new_task.gid,
                        due_on=due_on,
                    )
                    logger.info(
                        "pipeline_due_date_set",
                        due_on=due_on,
                        task_gid=new_task.gid,
                        offset_days=stage.due_date_offset_days,
                    )
                    due_date_set = True
                except ASANA_API_ERRORS as e:
                    logger.warning(
                        "pipeline_set_due_date_failed",
                        task_gid=new_task.gid,
                        error=str(e),
                    )
                if due_date_set:
                    actions_executed.append("set_due_date")
                enhancement_results["due_date_set"] = due_date_set

            # Step 3d: Wait for subtasks to be created (Asana creates them async)
            # Per ADR-0111: Use polling-based wait for subtask availability
            if expected_subtask_count > 0:
                subtasks_ready = await wait_for_subtasks_async(
                    context.client,
                    new_task.gid,
                    expected_subtask_count,
                )
                if subtasks_ready:
                    actions_executed.append("wait_subtasks")
                else:
                    # Timeout is non-fatal - log and continue
                    logger.warning(
                        "pipeline_subtask_timeout",
                        task_gid=new_task.gid,
                    )

            # Step 4: Seed fields from hierarchy and source process
            # Use configurable field lists from PipelineStage if specified
            field_seeder = FieldSeeder(
                context.client,
                business_cascade_fields=stage.business_cascade_fields,
                unit_cascade_fields=stage.unit_cascade_fields,
                process_carry_through_fields=stage.process_carry_through_fields,
            )

            seeded_fields = await field_seeder.seed_fields_async(
                business=business,
                unit=unit,
                source_process=source_process,
            )

            # Apply seeded fields if any
            if seeded_fields:
                # Write seeded fields to target task
                write_result = await field_seeder.write_fields_async(
                    new_task.gid,
                    seeded_fields,
                    field_name_mapping=stage.field_name_mapping,
                )
                if write_result.success:
                    actions_executed.append("seed_fields")
                    if write_result.fields_written:
                        entities_updated.append(new_task.gid)
                else:
                    # Log warning but continue - field seeding failure is non-fatal
                    logger.warning(
                        "pipeline_field_seeding_failed",
                        task_gid=new_task.gid,
                        error=write_result.error,
                    )

            # Step 5: Hierarchy placement (FR-HIER-001, FR-HIER-002, FR-HIER-003)
            # Place new task under ProcessHolder with insert_after=source_process
            hierarchy_placed = await self._place_in_hierarchy_async(
                new_task=new_task,
                source_process=source_process,
                unit=unit,
                client=context.client,
            )
            if hierarchy_placed:
                actions_executed.append("hierarchy_placement")
            enhancement_results["hierarchy_placement"] = hierarchy_placed

            # Step 6: Resolve rep and set assignee (FR-ASSIGN-001 through FR-ASSIGN-006)
            # Construct AssigneeConfig from PipelineStage.assignee_gid (no assignee_source
            # for automation -- stages are Python-configured, not YAML-driven).
            assignee_config = AssigneeConfig(assignee_gid=stage.assignee_gid)
            assignee_set = await self._set_assignee_from_rep_async(
                new_task=new_task,
                source_process=source_process,
                unit=unit,
                business=business,
                client=context.client,
                assignee_config=assignee_config,
            )
            if assignee_set:
                actions_executed.append("set_assignee")
            enhancement_results["assignee_set"] = assignee_set

            # Step 7: Create onboarding comment (FR-COMMENT-001 through FR-COMMENT-005)
            comment_created = await self._create_onboarding_comment_async(
                new_task=new_task,
                source_process=source_process,
                target_process_type=self._target_type,
                business=business,
                target_project_gid=target_project_gid,
                client=context.client,
            )
            if comment_created:
                actions_executed.append("create_comment")
            enhancement_results["comment_created"] = comment_created

            # Post-transition validation (ADR-0018)
            post_validation: ValidationResult | None = None
            if self._required_source_fields:
                post_validation = self._validate_post_transition(
                    source_process=source_process,
                    target_task=new_task,
                    seeded_fields=seeded_fields,
                )
                actions_executed.append("post_validation")

            # Success result
            return AutomationResult(
                rule_id=self.id,
                rule_name=self.name,
                triggered_by_gid=entity.gid,
                triggered_by_type="Process",
                actions_executed=actions_executed,
                entities_created=entities_created,
                entities_updated=entities_updated,
                success=True,
                execution_time_ms=elapsed_ms(start_time),
                enhancement_results=enhancement_results,
                pre_validation=pre_validation,
                post_validation=post_validation,
            )

        except Exception as e:  # BROAD-CATCH: isolation -- catch-all for unexpected errors in rule execution
            return AutomationResult(
                rule_id=self.id,
                rule_name=self.name,
                triggered_by_gid=entity.gid,
                triggered_by_type=type(entity).__name__,
                actions_executed=actions_executed,
                entities_created=entities_created,
                entities_updated=entities_updated,
                success=False,
                error=str(e),
                execution_time_ms=elapsed_ms(start_time),
                enhancement_results=enhancement_results,
            )

    async def _place_in_hierarchy_async(
        self,
        new_task: Any,
        source_process: Process,
        unit: Any,
        client: Any,
    ) -> bool:
        """Place new task in hierarchy under ProcessHolder.

        Per FR-HIER-001: Discovers ProcessHolder from source_process.unit.process_holder.
        Per FR-HIER-002: Uses set_parent() with insert_after=source_process for ordering.
        Per FR-HIER-003: Graceful degradation if ProcessHolder missing or placement fails.

        Resolution strategy chain (mirrors lifecycle pattern):
          1. source_process.process_holder (public property)
          2. unit.process_holder (public property)
          3. ctx.resolve_holder_async(ProcessHolder) (public API, session-cached)

        Args:
            new_task: Newly created task to place in hierarchy.
            source_process: Source process (for sibling ordering).
            unit: Unit entity (may be None).
            client: AsanaClient for API calls.

        Returns:
            True if placement succeeded, False if skipped/failed (graceful degradation).
        """
        # Step 1: Get ProcessHolder reference using public API strategy chain
        # per lifecycle pattern (lifecycle/creation.py _resolve_holder_for_placement).

        # Strategy 1: source_process.process_holder (public property)
        process_holder = getattr(source_process, "process_holder", None)

        # Strategy 2: unit.process_holder (public property)
        if process_holder is None and unit is not None:
            process_holder = getattr(unit, "process_holder", None)

        # Strategy 3: resolve_holder_async via ResolutionContext (session-cached,
        # public API). For ProcessHolder (PRIMARY_PROJECT_GID=None) this returns None,
        # preserving graceful degradation per FR-HIER-003.
        if process_holder is None:
            from autom8_asana.models.business.process import ProcessHolder
            from autom8_asana.resolution.context import ResolutionContext

            business_gid: str | None = None
            business = getattr(source_process, "business", None)
            if business is not None:
                business_gid = getattr(business, "gid", None)

            ctx = ResolutionContext(
                client=client,
                trigger_entity=source_process,
                business_gid=business_gid,
            )
            process_holder = await ctx.resolve_holder_async(ProcessHolder)

        # FR-HIER-003: Graceful degradation - no ProcessHolder available
        if process_holder is None:
            logger.warning(
                "pipeline_no_process_holder",
                task_gid=new_task.gid,
            )
            return False

        # Step 2: Use SaveSession.set_parent() for placement
        try:
            async with SaveSession(client, automation_enabled=False) as session:
                session.set_parent(
                    new_task,
                    process_holder,
                    insert_after=source_process,
                )
                result = await session.commit_async()

            if result.success:
                logger.info(
                    "pipeline_hierarchy_placed",
                    task_gid=new_task.gid,
                    process_holder_gid=process_holder.gid,
                    after_gid=source_process.gid,
                )
                return True
            else:
                logger.warning(
                    "pipeline_hierarchy_placement_failed",
                    task_gid=new_task.gid,
                    failure_count=len(result.failed),
                )
                return False

        except ASANA_API_ERRORS as e:
            # FR-HIER-003: Graceful degradation - log and continue
            logger.warning(
                "pipeline_hierarchy_error",
                task_gid=new_task.gid,
                error=str(e),
            )
            return False

    def _resolve_assignee_gid(
        self,
        source_process: Any,
        unit: Any,
        business: Any,
        assignee_config: AssigneeConfig,
    ) -> str | None:
        """Resolve assignee GID from AssigneeConfig cascade (no API call).

        Per FR-ASSIGN-001 through FR-ASSIGN-004: Configurable cascade.
        Per ADR-0113: Rep Field Cascade Pattern.

        Resolution order mirrors lifecycle _resolve_assignee_gid:
          1. assignee_config.assignee_source field on source_process / unit
             (skipped when None -- automation stages are Python-configured)
          2. assignee_config.assignee_gid  (fixed GID from PipelineStage)
          3. unit.rep[0]
          4. business.rep[0]

        Args:
            source_process: Source process (for assignee_source field lookup).
            unit: Unit entity (may be None).
            business: Business entity (may be None).
            assignee_config: Configurable assignee cascade settings.

        Returns:
            Assignee GID if resolved, None otherwise.
        """
        assignee_gid: str | None = None

        # Step 1: Stage-specific field (assignee_source) -- mirrors lifecycle step 1.
        # Automation stages are Python-configured (not YAML), so assignee_source is
        # None in practice. Included for parity so the cascade is a strict superset.
        if assignee_config.assignee_source:
            attr_name = assignee_config.assignee_source.lower().replace(" ", "_")
            source_field = getattr(source_process, attr_name, None)
            if source_field:
                assignee_gid = self._extract_user_gid(source_field)
            if not assignee_gid and unit is not None:
                unit_field = getattr(unit, attr_name, None)
                if unit_field:
                    assignee_gid = self._extract_user_gid(unit_field)

        # Step 2: Fixed GID from AssigneeConfig (FR-ASSIGN-001)
        if not assignee_gid and assignee_config.assignee_gid:
            assignee_gid = assignee_config.assignee_gid
            logger.info("pipeline_using_fixed_assignee", assignee_gid=assignee_gid)

        # Step 3: Unit.rep[0] (FR-ASSIGN-002)
        if not assignee_gid and unit is not None:
            assignee_gid = self._extract_first_rep(unit)

        # Step 4: Business.rep[0] (FR-ASSIGN-003)
        if not assignee_gid and business is not None:
            assignee_gid = self._extract_first_rep(business)

        return assignee_gid

    async def _set_assignee_from_rep_async(
        self,
        new_task: Any,
        source_process: Process,
        unit: Any,
        business: Any,
        client: Any,
        assignee_config: AssigneeConfig | None = None,
    ) -> bool:
        """Set assignee on new task via AssigneeConfig cascade.

        Per FR-ASSIGN-001: Set assignee from rep field.
        Per FR-ASSIGN-002: Unit.rep takes precedence over Business.rep.
        Per FR-ASSIGN-003: Fallback to Business.rep if Unit.rep is empty.
        Per FR-ASSIGN-004: First user in rep list used.
        Per FR-ASSIGN-005: Empty rep logs warning, continues.
        Per FR-ASSIGN-006: Graceful degradation on API failure.
        Per ADR-0113: Rep Field Cascade Pattern.

        Args:
            new_task: Newly created task to set assignee on.
            source_process: Source process (for assignee_source field lookup).
            unit: Unit entity (may be None).
            business: Business entity (may be None).
            client: AsanaClient for API calls.
            assignee_config: Configurable assignee cascade. Defaults to empty
                AssigneeConfig (rep-only cascade) when not provided.

        Returns:
            True if assignee was set successfully, False otherwise.
        """
        config = assignee_config if assignee_config is not None else AssigneeConfig()
        assignee_gid = self._resolve_assignee_gid(source_process, unit, business, config)

        # FR-ASSIGN-005: No rep found, log warning
        if assignee_gid is None:
            logger.warning("pipeline_no_rep_for_assignee", task_gid=new_task.gid)
            return False

        # Set assignee via API (FR-ASSIGN-001)
        try:
            await client.tasks.set_assignee_async(new_task.gid, assignee_gid)
            logger.info(
                "pipeline_assignee_set",
                assignee_gid=assignee_gid,
                task_gid=new_task.gid,
            )
            return True
        except ASANA_API_ERRORS as e:
            # FR-ASSIGN-006: Graceful degradation
            logger.warning(
                "pipeline_set_assignee_failed",
                task_gid=new_task.gid,
                error=str(e),
            )
            return False

    @staticmethod
    def _extract_user_gid(field_value: Any) -> str | None:
        """Extract user GID from a people field value.

        Mirrors lifecycle EntityCreationService._extract_user_gid.
        """
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
        """Extract first rep GID from entity's rep field.

        Per FR-ASSIGN-004: Use first user in list.
        Mirrors lifecycle EntityCreationService._extract_first_rep.
        """
        rep_list = getattr(entity, "rep", None)
        if rep_list and len(rep_list) > 0:
            first = rep_list[0]
            if isinstance(first, dict):
                return first.get("gid")
        return None

    async def _create_onboarding_comment_async(
        self,
        new_task: Any,
        source_process: Process,
        target_process_type: ProcessType,
        business: Any,
        target_project_gid: str,
        client: Any,
    ) -> bool:
        """Create onboarding comment on new task.

        Per FR-COMMENT-001: Comment added to new Process.
        Per FR-COMMENT-002: Include ProcessType, source name, date.
        Per FR-COMMENT-003: Include link to source Process.
        Per FR-COMMENT-004: Added after all other operations.
        Per FR-COMMENT-005: Failure doesn't stop conversion.

        Args:
            new_task: Newly created task to add comment to.
            source_process: Source process for context.
            target_process_type: ProcessType of the new process.
            business: Business entity (may be None).
            target_project_gid: Target project GID for link construction.
            client: AsanaClient for API calls.

        Returns:
            True if comment was created successfully, False otherwise.
        """
        try:
            # Build comment text (FR-COMMENT-002)
            comment_text = self._build_onboarding_comment(
                source_process=source_process,
                target_process_type=target_process_type,
                business=business,
            )

            # Create comment via StoriesClient (FR-COMMENT-001)
            await client.stories.create_comment_async(
                task=new_task.gid,
                text=comment_text,
            )
            logger.info("pipeline_comment_created", task_gid=new_task.gid)
            return True

        except ASANA_API_ERRORS as e:
            # FR-COMMENT-005: Graceful degradation
            logger.warning(
                "pipeline_create_comment_failed",
                task_gid=new_task.gid,
                error=str(e),
            )
            return False

    def _build_onboarding_comment(
        self,
        source_process: Process,
        target_process_type: ProcessType,
        business: Any,
    ) -> str:
        """Build the onboarding comment text.

        Per FR-COMMENT-002: Include ProcessType, source name, date, and link.

        Args:
            source_process: Source process for context.
            target_process_type: ProcessType of the new process.
            business: Business entity (may be None).

        Returns:
            Formatted comment text.
        """
        # Get source name with fallback
        source_name = source_process.name or "Unknown"

        # Get target type name
        target_type = target_process_type.value.title()

        # Get current date
        today = date.today().isoformat()

        # Get business name with fallback
        business_name = "Unknown"
        if business is not None:
            business_name = getattr(business, "name", None) or "Unknown"

        # Build source link (FR-COMMENT-003)
        # Format: https://app.asana.com/0/{project_gid}/{task_gid}
        # Note: We need the source process's project GID for the link
        source_project_gid = "0"  # Default fallback
        if hasattr(source_process, "memberships") and source_process.memberships:
            for membership in source_process.memberships:
                if isinstance(membership, dict):
                    project = membership.get("project")
                    if isinstance(project, dict) and project.get("gid"):
                        source_project_gid = project["gid"]
                        break
                elif hasattr(membership, "project"):
                    project = membership.project
                    if hasattr(project, "gid") and project.gid:
                        source_project_gid = project.gid
                        break

        source_link = (
            f"https://app.asana.com/0/{source_project_gid}/{source_process.gid}"
        )

        # Build comment text
        comment = f"""Pipeline Conversion

This {target_type} process was automatically created when "{source_name}" was converted on {today}.

Source: {source_link}
Business: {business_name}"""

        return comment

    def _validate_pre_transition(
        self,
        source_process: Process,
    ) -> ValidationResult:
        """Validate source process before transition.

        Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT/ADR-0018: Pre-transition validation
        checks that required fields are present and non-empty on the source process.

        Args:
            source_process: The process being transitioned.

        Returns:
            ValidationResult indicating validation outcome.
            - valid=True if all required fields are present and non-empty.
            - valid=False with errors listing missing/empty fields.
        """
        if not self._required_source_fields:
            # No required fields configured, validation passes
            return ValidationResult.success()

        errors: list[str] = []
        warnings: list[str] = []

        for field_name in self._required_source_fields:
            # Try to get field value from process
            # Use getattr to access descriptor-based fields
            field_value = getattr(source_process, field_name, None)

            # Check if field is missing or empty
            if field_value is None:
                errors.append(f"Missing required field: {field_name}")
            elif isinstance(field_value, str) and not field_value.strip():
                errors.append(f"Empty required field: {field_name}")
            elif isinstance(field_value, (list, dict)) and len(field_value) == 0:
                errors.append(f"Empty required field: {field_name}")

        if errors:
            logger.warning(
                "pre_transition_validation_failed",
                process_gid=source_process.gid,
                errors=errors,
            )
            return ValidationResult.failure(errors)

        return ValidationResult(valid=True, warnings=warnings)

    def _validate_post_transition(
        self,
        source_process: Process,
        target_task: Any,
        seeded_fields: dict[str, Any] | None,
    ) -> ValidationResult:
        """Validate transition after target task creation.

        Per TDD-PIPELINE-AUTOMATION-ENHANCEMENT/ADR-0018: Post-transition validation
        verifies that expected fields were successfully carried through to the target.

        This method checks that seeded fields match expected values. It is advisory
        only (warnings, not blocking errors) since the transition has already occurred.

        Args:
            source_process: The source process that was transitioned.
            target_task: The newly created target task.
            seeded_fields: Dictionary of field names to values that were seeded.

        Returns:
            ValidationResult with warnings for any discrepancies.
            Always returns valid=True since post-validation is advisory only.
        """
        warnings: list[str] = []

        # Check if seeding was attempted but no fields were seeded
        if self._required_source_fields and not seeded_fields:
            warnings.append(
                "No fields were seeded to target despite required fields configured"
            )

        # Check that required fields were included in seeded fields
        if seeded_fields:
            for field_name in self._required_source_fields:
                if field_name not in seeded_fields:
                    warnings.append(
                        f"Required field '{field_name}' was not carried through to target"
                    )

        if warnings:
            logger.info(
                "pipeline_post_validation_warnings",
                source_gid=source_process.gid,
                target_gid=target_task.gid
                if hasattr(target_task, "gid")
                else "unknown",
                warnings=warnings,
            )

        return ValidationResult(valid=True, warnings=warnings)
