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

import re
import time
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Literal, cast

from autom8y_log import get_logger

from autom8_asana.automation.base import TriggerCondition
from autom8_asana.automation.seeding import FieldSeeder
from autom8_asana.automation.templates import TemplateDiscovery
from autom8_asana.automation.validation import ValidationResult
from autom8_asana.automation.waiter import SubtaskWaiter

# Per TDD-registry-consolidation: Import from package to ensure bootstrap runs
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
            event="section_changed",
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
        enhancement_results: dict[str, bool] = {}

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
                    execution_time_ms=self._elapsed_ms(start_time),
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
                        execution_time_ms=self._elapsed_ms(start_time),
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
                    execution_time_ms=self._elapsed_ms(start_time),
                )

            target_project_gid = stage.project_gid
            actions_executed.append("lookup_target_project")

            # Step 2: Discover template in target project
            template_discovery = TemplateDiscovery(context.client)
            template_task = await template_discovery.find_template_task_async(
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
                    execution_time_ms=self._elapsed_ms(start_time),
                )

            actions_executed.append("discover_template")

            # Get hierarchy references (may be None) - needed for name generation
            business = source_process.business
            unit = source_process.unit

            # Step 3: Duplicate task from template (copies subtasks)
            # Per FR-DUP-001: Use duplicate_async to copy template with subtasks
            # Generate name from template pattern, replacing placeholders with actual values
            new_task_name = self._generate_task_name(
                template_name=template_task.name,
                business=business,
                unit=unit,
            )

            # Step 3a: Get template subtask count for waiter
            template_subtasks = await context.client.tasks.subtasks_async(
                template_task.gid, opt_fields=["gid"]
            ).collect()
            expected_subtask_count = len(template_subtasks)

            # Step 3b: Duplicate the template task with subtasks and notes
            new_task = await context.client.tasks.duplicate_async(
                template_task.gid,
                name=new_task_name,
                include=["subtasks", "notes"],
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
                section_placed = await self._move_to_target_section_async(
                    new_task=new_task,
                    target_project_gid=target_project_gid,
                    target_section_name=stage.target_section,
                    client=context.client,
                )
                if section_placed:
                    actions_executed.append("section_placement")
                enhancement_results["section_placement"] = section_placed

            # Step 3f: Set due date if configured (G4 Gap Fix)
            # Per PipelineStage: Set due date relative to today
            if stage.due_date_offset_days is not None:
                due_date_set = await self._set_due_date_async(
                    new_task=new_task,
                    offset_days=stage.due_date_offset_days,
                    client=context.client,
                )
                if due_date_set:
                    actions_executed.append("set_due_date")
                enhancement_results["due_date_set"] = due_date_set

            # Step 3d: Wait for subtasks to be created (Asana creates them async)
            # Per ADR-0111: Use polling-based wait for subtask availability
            if expected_subtask_count > 0:
                waiter = SubtaskWaiter(context.client)
                subtasks_ready = await waiter.wait_for_subtasks_async(
                    new_task.gid,
                    expected_count=expected_subtask_count,
                    timeout=2.0,
                )
                if subtasks_ready:
                    actions_executed.append("wait_subtasks")
                else:
                    # Timeout is non-fatal - log and continue
                    logger.warning(
                        "Subtask wait timeout for task %s, proceeding",
                        new_task.gid,
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
                        "Field seeding failed for task %s: %s",
                        new_task.gid,
                        write_result.error,
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
            # Use fixed assignee_gid from PipelineStage if configured
            assignee_set = await self._set_assignee_from_rep_async(
                new_task=new_task,
                source_process=source_process,
                unit=unit,
                business=business,
                client=context.client,
                fixed_assignee_gid=stage.assignee_gid,
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
                execution_time_ms=self._elapsed_ms(start_time),
                enhancement_results=enhancement_results,
                pre_validation=pre_validation,
                post_validation=post_validation,
            )

        except Exception as e:
            # Catch-all for unexpected errors
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
                execution_time_ms=self._elapsed_ms(start_time),
                enhancement_results=enhancement_results,
            )

    def _elapsed_ms(self, start_time: float) -> float:
        """Calculate elapsed time in milliseconds.

        Args:
            start_time: Start time from time.perf_counter().

        Returns:
            Elapsed time in milliseconds.
        """
        return (time.perf_counter() - start_time) * 1000

    def _generate_task_name(
        self,
        template_name: str | None,
        business: Any,
        unit: Any,
    ) -> str:
        """Generate task name from template by replacing bracketed placeholders.

        Takes the template task's name and replaces bracketed placeholders with
        actual entity values. Brackets are required around placeholders for
        explicit, robust matching. Replacement inside brackets is case-insensitive.

        Supported placeholders:
        - "[Business Name]" -> business.name
        - "[Unit Name]" -> unit.name
        - "[Business Unit Name]" -> unit.name

        Args:
            template_name: Template task name with bracketed placeholders.
            business: Business entity (may be None).
            unit: Unit entity (may be None).

        Returns:
            Task name with placeholders replaced by actual values.
            Falls back to target type title if template_name is None.

        Example:
            >>> rule._generate_task_name(
            ...     "Onboarding Process - [Business Name]",
            ...     business=Business(name="Acme Corp"),
            ...     unit=None,
            ... )
            "Onboarding Process - Acme Corp"
        """
        if not template_name:
            return f"New {self._target_type.value.title()}"

        result = template_name

        # Get business name with fallback
        business_name: str | None = None
        if business is not None:
            business_name = getattr(business, "name", None)

        # Get unit name with fallback
        unit_name: str | None = None
        if unit is not None:
            unit_name = getattr(unit, "name", None)

        # Replace bracketed placeholders (case-insensitive inside brackets)
        # Entire [placeholder] is replaced with the value (no leftover brackets)
        if business_name:
            # Replace [Business Name] variants
            result = re.sub(
                r"\[business\s*name\]",
                business_name,
                result,
                flags=re.IGNORECASE,
            )

        if unit_name:
            # Replace [Unit Name] or [Business Unit Name] variants
            result = re.sub(
                r"\[(business\s*)?unit\s*name\]",
                unit_name,
                result,
                flags=re.IGNORECASE,
            )

        return result

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

        Args:
            new_task: Newly created task to place in hierarchy.
            source_process: Source process (for sibling ordering).
            unit: Unit entity (may be None).
            client: AsanaClient for API calls.

        Returns:
            True if placement succeeded, False if skipped/failed (graceful degradation).
        """
        # Step 1: Get ProcessHolder reference
        process_holder = None

        # Try from source_process first
        if hasattr(source_process, "process_holder") and source_process.process_holder:
            process_holder = source_process.process_holder
        elif unit is not None:
            # Try from unit.process_holder
            if hasattr(unit, "process_holder") and unit.process_holder:
                process_holder = unit.process_holder
            elif hasattr(unit, "_process_holder") and unit._process_holder:
                process_holder = unit._process_holder
            else:
                # ProcessHolder not hydrated - try on-demand fetch
                try:
                    if hasattr(unit, "_fetch_holders_async"):
                        await unit._fetch_holders_async(client)
                        process_holder = getattr(unit, "_process_holder", None)
                except Exception as e:
                    logger.warning(
                        "Failed to fetch ProcessHolder for unit %s: %s",
                        getattr(unit, "gid", "unknown"),
                        str(e),
                    )

        # FR-HIER-003: Graceful degradation - no ProcessHolder available
        if process_holder is None:
            logger.warning(
                "ProcessHolder not found for hierarchy placement, "
                "new task %s will be top-level",
                new_task.gid,
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
                    "Placed task %s under ProcessHolder %s (after %s)",
                    new_task.gid,
                    process_holder.gid,
                    source_process.gid,
                )
                return True
            else:
                logger.warning(
                    "Hierarchy placement failed for task %s: %d failures",
                    new_task.gid,
                    len(result.failed),
                )
                return False

        except Exception as e:
            # FR-HIER-003: Graceful degradation - log and continue
            logger.warning(
                "Hierarchy placement error for task %s: %s",
                new_task.gid,
                str(e),
            )
            return False

    async def _move_to_target_section_async(
        self,
        new_task: Any,
        target_project_gid: str,
        target_section_name: str,
        client: Any,
    ) -> bool:
        """Move new task to target section in the project.

        Per G3 Gap Fix: Place new task in configured target section.
        Uses case-insensitive matching for section name.
        Graceful degradation if section not found (logs warning, continues).

        Args:
            new_task: Newly created task to move.
            target_project_gid: GID of the target project.
            target_section_name: Name of section to move task to.
            client: AsanaClient for API calls.

        Returns:
            True if task was moved to section, False if section not found or error.
        """
        try:
            # List sections in target project
            sections = await client.sections.list_for_project_async(
                target_project_gid
            ).collect()

            # Find target section by name (case-insensitive)
            target_section_lower = target_section_name.lower()
            target_section = next(
                (
                    s
                    for s in sections
                    if s.name and s.name.lower() == target_section_lower
                ),
                None,
            )

            if target_section is None:
                logger.warning(
                    "Target section '%s' not found in project %s, "
                    "task %s will remain in default section",
                    target_section_name,
                    target_project_gid,
                    new_task.gid,
                )
                return False

            # Move task to target section
            await client.sections.add_task_async(
                target_section.gid,
                task=new_task.gid,
            )

            logger.info(
                "Moved task %s to section '%s' (%s)",
                new_task.gid,
                target_section_name,
                target_section.gid,
            )
            return True

        except Exception as e:
            # Graceful degradation - log and continue
            logger.warning(
                "Failed to move task %s to section '%s': %s",
                new_task.gid,
                target_section_name,
                str(e),
            )
            return False

    async def _set_due_date_async(
        self,
        new_task: Any,
        offset_days: int,
        client: Any,
    ) -> bool:
        """Set due date on new task relative to today.

        Per G4 Gap Fix: Set due date as today + offset_days.
        Supports offset 0 (today), positive (future), and negative (past).
        Graceful degradation if API call fails.

        Args:
            new_task: Newly created task to set due date on.
            offset_days: Number of days from today for due date.
            client: AsanaClient for API calls.

        Returns:
            True if due date was set successfully, False otherwise.
        """
        try:
            due_date = date.today() + timedelta(days=offset_days)
            due_on = due_date.isoformat()  # "YYYY-MM-DD" format

            await client.tasks.update_async(
                new_task.gid,
                due_on=due_on,
            )

            logger.info(
                "Set due date %s on task %s (offset: %d days)",
                due_on,
                new_task.gid,
                offset_days,
            )
            return True

        except Exception as e:
            # Graceful degradation - log and continue
            logger.warning(
                "Failed to set due date on task %s: %s",
                new_task.gid,
                str(e),
            )
            return False

    async def _set_assignee_from_rep_async(
        self,
        new_task: Any,
        source_process: Process,
        unit: Any,
        business: Any,
        client: Any,
        fixed_assignee_gid: str | None = None,
    ) -> bool:
        """Set assignee on new task from rep field cascade or fixed GID.

        Per FR-ASSIGN-001: Set assignee from rep field.
        Per FR-ASSIGN-002: Unit.rep takes precedence over Business.rep.
        Per FR-ASSIGN-003: Fallback to Business.rep if Unit.rep is empty.
        Per FR-ASSIGN-004: First user in rep list used.
        Per FR-ASSIGN-005: Empty rep logs warning, continues.
        Per FR-ASSIGN-006: Graceful degradation on API failure.
        Per ADR-0113: Rep Field Cascade Pattern.

        Args:
            new_task: Newly created task to set assignee on.
            source_process: Source process (not used, kept for consistency).
            unit: Unit entity (may be None).
            business: Business entity (may be None).
            client: AsanaClient for API calls.
            fixed_assignee_gid: Optional fixed assignee GID from PipelineStage.
                When set, skips rep resolution and uses this GID directly.

        Returns:
            True if assignee was set successfully, False otherwise.
        """
        assignee_gid: str | None = None

        # Priority 0: Fixed assignee from PipelineStage (highest priority)
        if fixed_assignee_gid:
            assignee_gid = fixed_assignee_gid
            logger.info(
                "Using fixed assignee_gid %s from PipelineStage",
                assignee_gid,
            )
        else:
            # Priority 1: Unit.rep (FR-ASSIGN-002)
            if unit is not None:
                try:
                    rep_list = getattr(unit, "rep", None)
                    if rep_list and len(rep_list) > 0:
                        # FR-ASSIGN-004: Use first user in list
                        first_rep = rep_list[0]
                        if isinstance(first_rep, dict):
                            assignee_gid = first_rep.get("gid")
                except Exception as e:
                    logger.warning("Failed to access Unit.rep: %s", str(e))

            # Priority 2: Business.rep fallback (FR-ASSIGN-003)
            if assignee_gid is None and business is not None:
                try:
                    rep_list = getattr(business, "rep", None)
                    if rep_list and len(rep_list) > 0:
                        first_rep = rep_list[0]
                        if isinstance(first_rep, dict):
                            assignee_gid = first_rep.get("gid")
                except Exception as e:
                    logger.warning("Failed to access Business.rep: %s", str(e))

        # FR-ASSIGN-005: No rep found, log warning
        if assignee_gid is None:
            logger.warning(
                "No rep found for assignee on task %s, skipping assignment",
                new_task.gid,
            )
            return False

        # Set assignee via API (FR-ASSIGN-001)
        try:
            await client.tasks.set_assignee_async(new_task.gid, assignee_gid)
            logger.info(
                "Set assignee %s on task %s",
                assignee_gid,
                new_task.gid,
            )
            return True
        except Exception as e:
            # FR-ASSIGN-006: Graceful degradation
            logger.warning(
                "Failed to set assignee on task %s: %s",
                new_task.gid,
                str(e),
            )
            return False

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
            logger.info(
                "Created onboarding comment on task %s",
                new_task.gid,
            )
            return True

        except Exception as e:
            # FR-COMMENT-005: Graceful degradation
            logger.warning(
                "Failed to create onboarding comment on task %s: %s",
                new_task.gid,
                str(e),
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
                "Pre-transition validation failed for %s: %s",
                source_process.gid,
                errors,
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
                "Post-transition validation warnings for %s -> %s: %s",
                source_process.gid,
                target_task.gid if hasattr(target_task, "gid") else "unknown",
                warnings,
            )

        return ValidationResult(valid=True, warnings=warnings)
