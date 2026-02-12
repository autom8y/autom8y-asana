"""Entity creation service for lifecycle transitions.

Per TDD-lifecycle-engine-hardening Section 2.3:
- Highest-risk module: template discovery, task duplication, blank fallback,
  name generation, section placement, due date, subtask waiting, auto-cascade
  field seeding, hierarchy placement, and assignee resolution.

FR Coverage: FR-CREATE-001 through FR-CREATE-004, FR-SEED-001 through
FR-SEED-003, FR-ASSIGN-001, FR-HIER-001, FR-TMPL-001, FR-DUP-001,
FR-DUP-002, FR-ERR-002

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

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.automation.templates import TemplateDiscovery
from autom8_asana.automation.waiter import SubtaskWaiter
from autom8_asana.lifecycle.config import AssigneeConfig, LifecycleConfig, StageConfig
from autom8_asana.lifecycle.seeding import AutoCascadeSeeder

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.business.process import Process
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


@dataclass(frozen=True)
class CreationResult:
    """Result of entity creation.

    Frozen dataclass -- immutable after construction. Provides full
    diagnostics for the engine to accumulate into TransitionResult.

    Attributes:
        success: Whether creation (or reopen) succeeded.
        entity_gid: GID of the created or reopened task, or None on failure.
        entity_name: Name of the created task, or None on failure.
        was_reopened: True if an existing entity was reopened (duplicate).
        fields_seeded: Names of fields that were cascaded to the target.
        fields_skipped: Names of fields not found on target or excluded.
        warnings: Non-fatal issues encountered during creation.
        error: Error message if success is False, None otherwise.
    """

    success: bool
    entity_gid: str | None = None
    entity_name: str | None = None
    was_reopened: bool = False
    fields_seeded: list[str] = field(default_factory=list)
    fields_skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


class EntityCreationService:
    """Creates entities during lifecycle transitions.

    Handles:
    - Template-based process creation (most entities)
    - Blank task fallback when template not found
    - Auto-cascade field seeding from hierarchy
    - Section placement
    - Due date setting
    - Hierarchy placement under ProcessHolder
    - Duplicate detection (ProcessType + Unit match)
    - YAML-configurable assignee resolution

    Uses existing infrastructure:
    - TemplateDiscovery: Find template tasks in target projects
    - SubtaskWaiter: Wait for Asana async subtask creation
    - AutoCascadeSeeder: Zero-config field name matching + enum resolution
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

        Args:
            stage_config: Target stage configuration from YAML.
            ctx: ResolutionContext for hierarchy traversal and caching.
            source_process: The process that triggered the transition.

        Returns:
            CreationResult with full diagnostics.
        """
        warnings: list[str] = []

        try:
            # 1. Resolve context entities
            business = await ctx.business_async()
            unit = await ctx.unit_async()

            # 2. Duplicate check (ProcessType + Unit in ProcessHolder)
            existing_gid = await self._check_process_duplicate_async(
                ctx,
                source_process,
                stage_config.name,
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
                    was_reopened=True,
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
                business,
                unit,
            )

            if template:
                # Count subtasks before duplication (for waiter)
                template_subtasks = await self._client.tasks.subtasks_async(
                    template.gid, opt_fields=["gid"]
                ).collect()
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
                warnings.append(
                    f"Template not found in project "
                    f"{stage_config.project_gid}; created blank task"
                )
                new_task = await self._client.tasks.create_async(
                    name=new_name,
                )
                expected_subtask_count = 0

            # Add to target project
            if stage_config.project_gid:
                await self._client.tasks.add_to_project_async(
                    new_task.gid,
                    stage_config.project_gid,
                )

            # 5. Configure
            (
                configure_warnings,
                fields_seeded,
                fields_skipped,
            ) = await self._configure_async(
                new_task,
                stage_config,
                ctx,
                source_process,
                business,
                unit,
                expected_subtask_count,
            )
            warnings.extend(configure_warnings)

            ctx.cache_entity(new_task)

            return CreationResult(
                success=True,
                entity_gid=new_task.gid,
                entity_name=new_name,
                fields_seeded=fields_seeded,
                fields_skipped=fields_skipped,
                warnings=warnings,
            )

        except (
            Exception
        ) as e:  # BROAD-CATCH: boundary -- top-level creation must return result
            logger.error(
                "lifecycle_creation_error",
                stage=stage_config.name,
                error=str(e),
            )
            return CreationResult(
                success=False,
                error=str(e),
                warnings=warnings,
            )

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

        Args:
            project_gid: Target project GID for template discovery.
            template_section: Section name containing the template.
            holder_type: Holder type string for hierarchy placement.
            ctx: ResolutionContext for hierarchy traversal.
            source_process: Source process that triggered creation.
            stage_config: Stage configuration for seeding/assignee.

        Returns:
            CreationResult with full diagnostics.
        """
        warnings: list[str] = []

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
                business,
                unit,
            )

            if template:
                template_subtasks = await self._client.tasks.subtasks_async(
                    template.gid, opt_fields=["gid"]
                ).collect()
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
                warnings.append(
                    f"Template not found in project {project_gid}; created blank task"
                )
                new_task = await self._client.tasks.create_async(
                    name=new_name,
                )
                expected_subtask_count = 0

            if project_gid:
                await self._client.tasks.add_to_project_async(
                    new_task.gid,
                    project_gid,
                )

            (
                configure_warnings,
                fields_seeded,
                fields_skipped,
            ) = await self._configure_async(
                new_task,
                stage_config,
                ctx,
                source_process,
                business,
                unit,
                expected_subtask_count,
                holder_type=holder_type,
            )
            warnings.extend(configure_warnings)

            return CreationResult(
                success=True,
                entity_gid=new_task.gid,
                entity_name=new_name,
                fields_seeded=fields_seeded,
                fields_skipped=fields_skipped,
                warnings=warnings,
            )

        except (
            Exception
        ) as e:  # BROAD-CATCH: boundary -- entity creation must return result
            logger.error(
                "lifecycle_entity_creation_error",
                holder_type=holder_type,
                error=str(e),
            )
            return CreationResult(
                success=False,
                error=str(e),
                warnings=warnings,
            )

    # ------------------------------------------------------------------
    # Phase 5: Configure
    # ------------------------------------------------------------------

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
    ) -> tuple[list[str], list[str], list[str]]:
        """Configure created entity: section, due date, subtasks,
        fields, hierarchy, assignee.

        Returns:
            Tuple of (warnings, fields_seeded, fields_skipped).
        """
        from autom8_asana.persistence.session import SaveSession

        warnings: list[str] = []
        fields_seeded: list[str] = []
        fields_skipped: list[str] = []

        # a. Section placement
        if stage_config.target_section and stage_config.project_gid:
            section_ok = await self._move_to_section_async(
                new_task.gid,
                stage_config.project_gid,
                stage_config.target_section,
            )
            if not section_ok:
                warnings.append(
                    f"Section '{stage_config.target_section}' not found "
                    f"in project {stage_config.project_gid}"
                )

        # b. Due date
        if stage_config.due_date_offset_days is not None:
            due = date.today() + timedelta(
                days=stage_config.due_date_offset_days,
            )
            try:
                await self._client.tasks.update_async(
                    new_task.gid,
                    due_on=due.isoformat(),
                )
            except Exception as e:  # BROAD-CATCH: non-fatal config step
                logger.warning(
                    "lifecycle_set_due_date_failed",
                    task_gid=new_task.gid,
                    error=str(e),
                )
                warnings.append(f"Due date set failed: {e}")

        # c. Wait for subtasks
        if expected_subtask_count > 0:
            waiter = SubtaskWaiter(self._client)
            ready = await waiter.wait_for_subtasks_async(
                new_task.gid,
                expected_count=expected_subtask_count,
                timeout=2.0,
            )
            if not ready:
                warnings.append("Subtask wait timed out (2s)")

        # d. Auto-cascade field seeding
        seeder = AutoCascadeSeeder(self._client)
        try:
            seeding_result = await seeder.seed_async(
                target_task_gid=new_task.gid,
                business=business,
                unit=unit,
                source_process=source_process,
                exclude_fields=stage_config.seeding.exclude_fields,
                computed_fields=stage_config.seeding.computed_fields,
            )
            fields_seeded = seeding_result.fields_seeded
            fields_skipped = seeding_result.fields_skipped
            warnings.extend(seeding_result.warnings)
        except (
            Exception
        ) as e:  # BROAD-CATCH: non-fatal -- seeding failure does not block creation
            logger.warning(
                "lifecycle_field_seeding_failed",
                task_gid=new_task.gid,
                error=str(e),
            )
            warnings.append(f"Field seeding failed: {e}")

        # e. Hierarchy placement
        holder = await self._resolve_holder_for_placement(
            ctx,
            holder_type,
            source_process,
        )
        if holder is not None:
            try:
                async with SaveSession(
                    self._client,
                    automation_enabled=False,
                ) as session:
                    session.set_parent(
                        new_task,
                        holder,
                        insert_after=source_process,
                    )
                    await session.commit_async()
            except Exception as e:  # BROAD-CATCH: non-fatal hierarchy step
                logger.warning(
                    "lifecycle_hierarchy_placement_failed",
                    task_gid=new_task.gid,
                    error=str(e),
                )
                warnings.append(f"Hierarchy placement failed: {e}")
        else:
            warnings.append("No holder resolved for hierarchy placement")

        # f. Assignee resolution
        assignee_warning = await self._set_assignee_async(
            new_task,
            source_process,
            unit,
            business,
            stage_config.assignee,
        )
        if assignee_warning:
            warnings.append(assignee_warning)

        return warnings, fields_seeded, fields_skipped

    # ------------------------------------------------------------------
    # Duplicate Detection
    # ------------------------------------------------------------------

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
                opt_fields=[
                    "name",
                    "completed",
                    "custom_fields",
                    "custom_fields.name",
                    "custom_fields.display_value",
                ],
            ).collect()

            for task in subtasks:
                if task.completed:
                    continue
                # Match by process_type in custom fields
                if self._matches_process_type(task, target_stage_name):
                    return task.gid

        except (
            Exception
        ) as e:  # BROAD-CATCH: non-fatal -- duplicate check failure means create new
            logger.warning(
                "lifecycle_duplicate_check_failed",
                error=str(e),
            )

        return None

    # ------------------------------------------------------------------
    # Section Placement
    # ------------------------------------------------------------------

    async def _move_to_section_async(
        self,
        task_gid: str,
        project_gid: str,
        section_name: str,
    ) -> bool:
        """Move task to named section (case-insensitive).

        Returns True if section found and task moved, False otherwise.
        """
        try:
            sections = await self._client.sections.list_for_project_async(
                project_gid,
            ).collect()
            target = next(
                (
                    s
                    for s in sections
                    if s.name and s.name.lower() == section_name.lower()
                ),
                None,
            )
            if target:
                await self._client.sections.add_task_async(
                    target.gid,
                    task=task_gid,
                )
                return True
            else:
                logger.warning(
                    "lifecycle_section_not_found",
                    section=section_name,
                    project_gid=project_gid,
                )
                return False
        except Exception as e:  # BROAD-CATCH: non-fatal config step
            logger.warning(
                "lifecycle_section_placement_failed",
                task_gid=task_gid,
                section=section_name,
                error=str(e),
            )
            return False

    # ------------------------------------------------------------------
    # Hierarchy Placement
    # ------------------------------------------------------------------

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

        # Map holder_type string to class for non-process entities
        holder_class_map: dict[str, str] = {
            "dna_holder": ("autom8_asana.models.business.dna.DNAHolder"),
            "asset_edit_holder": (
                "autom8_asana.models.business.asset_edit.AssetEditHolder"
            ),
            "videography_holder": (
                "autom8_asana.models.business.videography.VideographyHolder"
            ),
        }
        class_path = holder_class_map.get(holder_type)
        if class_path:
            import importlib

            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            holder_cls = getattr(module, class_name)
            return await ctx.resolve_holder_async(holder_cls)

        return None

    # ------------------------------------------------------------------
    # Name Generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_name(
        template_name: str | None,
        business: Any,
        unit: Any,
    ) -> str:
        """Generate task name by replacing [Business Name] and [Unit Name] placeholders.

        Replacement is case-insensitive within brackets. Falls back to
        "New Process" if no template name provided.

        Args:
            template_name: Template task name with placeholders.
            business: Business entity (may be None).
            unit: Unit entity (may be None).

        Returns:
            Task name with placeholders replaced.
        """
        if not template_name:
            return "New Process"

        result = template_name
        business_name = getattr(business, "name", None)
        unit_name = getattr(unit, "name", None)

        if business_name:
            result = re.sub(
                r"\[business\s*name\]",
                business_name,
                result,
                flags=re.IGNORECASE,
            )
        if unit_name:
            result = re.sub(
                r"\[(business\s*)?unit\s*name\]",
                unit_name,
                result,
                flags=re.IGNORECASE,
            )
        return result

    # ------------------------------------------------------------------
    # Assignee Resolution
    # ------------------------------------------------------------------

    async def _set_assignee_async(
        self,
        new_task: Any,
        source_process: Any,
        unit: Any,
        business: Any,
        assignee_config: AssigneeConfig,
    ) -> str | None:
        """Set assignee using YAML-configurable cascade.

        Resolution order (FR-ASSIGN-001):
          1. Stage-specific field (assignee_source) from source process
          2. Fixed GID (assignee_gid) from YAML
          3. Unit.rep[0]
          4. Business.rep[0]
          5. None with warning

        Returns:
            Warning string if no assignee found or API failed, None on success.
        """
        assignee_gid: str | None = None

        # 1. Stage-specific field from assignee_source
        if assignee_config.assignee_source:
            attr_name = assignee_config.assignee_source.lower().replace(" ", "_")
            # Try on source process first
            source_field = getattr(source_process, attr_name, None)
            if source_field:
                assignee_gid = self._extract_user_gid(source_field)
            # Try on unit if not found on process
            if not assignee_gid and unit:
                unit_field = getattr(unit, attr_name, None)
                if unit_field:
                    assignee_gid = self._extract_user_gid(unit_field)

        # 2. Fixed GID from YAML
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
                    new_task.gid,
                    assignee_gid,
                )
                return None  # success, no warning
            except Exception as e:  # BROAD-CATCH: non-fatal
                logger.warning(
                    "lifecycle_set_assignee_failed",
                    task_gid=new_task.gid,
                    error=str(e),
                )
                return f"Set assignee failed: {e}"
        else:
            logger.warning(
                "lifecycle_no_assignee_found",
                task_gid=new_task.gid,
            )
            return "No assignee found in resolution chain"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        """Extract first rep GID from entity's rep field."""
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
            name = (
                cf.get("name", "") if isinstance(cf, dict) else getattr(cf, "name", "")
            )
            if name.lower() in ("process type", "processtype"):
                display = (
                    cf.get("display_value", "")
                    if isinstance(cf, dict)
                    else getattr(cf, "display_value", "")
                )
                if display and display.lower() == stage_name.lower():
                    return True
        return False
