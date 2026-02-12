# src/autom8_asana/lifecycle/init_actions.py

"""Init action handlers for lifecycle engine.

Per TDD-lifecycle-engine Section 2.9: Implements action handlers for the
5-phase orchestration lifecycle. These handlers execute during Phase 4
(Init Actions) after the target process is created and cascading sections
are updated.

Handler types:
- CommentHandler: Creates pipeline conversion comments on new entities
- PlayCreationHandler: Creates Play tasks with reopen-or-create support
- EntityCreationHandler: Creates related entities via EntityCreationService
- ProductsCheckHandler: Checks products field and conditionally creates entities
- CampaignHandler: Activates/deactivates campaigns (logged for now)

Each handler is responsible for:
1. Condition checking (not_already_linked, pattern match, etc.)
2. Entity creation/action execution
3. Error handling with graceful degradation
4. Returning CreationResult with success/failure details

Signature contract (TDD Section 2.9):
    execute_async(ctx, created_entity_gid, action_config, source_process)

The engine's _DefaultInitActionRegistry passes source_process as the 4th
argument. All handlers accept it.
"""

from __future__ import annotations

import fnmatch
from abc import ABC, abstractmethod
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.project_registry import VIDEOGRAPHY_HOLDER_PROJECT
from autom8_asana.lifecycle.creation import CreationResult

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.lifecycle.config import InitActionConfig, LifecycleConfig
    from autom8_asana.models.business.process import Process
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


class InitActionHandler(ABC):
    """Base handler for lifecycle init actions."""

    def __init__(
        self,
        client: AsanaClient,
        config: LifecycleConfig,
    ) -> None:
        self._client = client
        self._config = config

    @abstractmethod
    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        """Execute the init action.

        Args:
            ctx: Resolution context for entity access.
            created_entity_gid: GID of the newly created process.
            action_config: Action configuration from lifecycle_stages.yaml.
            source_process: The process that triggered the transition.

        Returns:
            CreationResult indicating success/failure.
        """
        ...


class CommentHandler(InitActionHandler):
    """Creates pipeline conversion comments on new entities.

    Per TDD Section 2.9: Generalizable comment templates. Generates a
    pipeline conversion comment containing source link, business name,
    and conversion date. Soft-fails on error (returns success=True).
    """

    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        """Create a pipeline conversion comment on the new entity."""
        try:
            business = await ctx.business_async()
            comment_text = self._build_comment(
                source_process, business, action_config.comment_template
            )
            await self._client.stories.create_comment_async(
                task=created_entity_gid,
                text=comment_text,
            )
            return CreationResult(success=True, entity_gid="")

        except Exception as e:
            logger.warning(
                "lifecycle_comment_failed",
                task_gid=created_entity_gid,
                error=str(e),
            )
            # Soft-fail: comment failure should not block the transition
            return CreationResult(success=True, entity_gid="")

    @staticmethod
    def _build_comment(
        source: Any,
        business: Any,
        template: str | None,
    ) -> str:
        """Build pipeline conversion comment with source link.

        Args:
            source: Source process entity.
            business: Business entity.
            template: Optional comment template (reserved for future use).

        Returns:
            Formatted comment text.
        """
        source_name = source.name or "Unknown"
        business_name = getattr(business, "name", "Unknown") or "Unknown"
        today = date.today().isoformat()

        # Extract source project GID from memberships for deep link
        source_project_gid = "0"
        memberships = getattr(source, "memberships", None) or []
        for m in memberships:
            if isinstance(m, dict):
                p = m.get("project", {})
                if isinstance(p, dict) and p.get("gid"):
                    source_project_gid = p["gid"]
                    break

        source_link = f"https://app.asana.com/0/{source_project_gid}/{source.gid}"

        return (
            f"Pipeline Conversion\n\n"
            f"This process was automatically created when "
            f'"{source_name}" was converted on {today}.\n\n'
            f"Source: {source_link}\n"
            f"Business: {business_name}"
        )


class PlayCreationHandler(InitActionHandler):
    """Creates a Play task in the specified project.

    Per lifecycle_stages.yaml: implementation stage has play_creation action
    with play_type="backend_onboard_a_business", project_gid="1207507299545000",
    and condition="not_already_linked".

    Supports reopen-or-create via reopen_if_completed_within_days:
    - If set, searches for completed plays in the project completed within
      the threshold and reopens the most recent one instead of creating new.
    - If no recent play found or threshold not set, creates a new play.

    Steps:
    1. Check if play already exists as dependency (not_already_linked condition)
    2. If reopen_if_completed_within_days set, check for recent completions
    3. If not, create play task from template in the target project
    4. Wire as dependency of the created process
    """

    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        """Create a Play task if not already linked."""
        try:
            # Check condition: not_already_linked
            if action_config.condition == "not_already_linked":
                # Check if play already exists as dependency
                created_task = await self._client.tasks.get_async(
                    created_entity_gid,
                    opt_fields=["dependencies", "dependencies.gid"],
                )
                dependencies = getattr(created_task, "dependencies", []) or []

                # Check if any dependency is in the play project
                for dep in dependencies:
                    dep_gid = dep.gid if hasattr(dep, "gid") else dep.get("gid")
                    if dep_gid:
                        dep_task = await self._client.tasks.get_async(
                            dep_gid, opt_fields=["memberships"]
                        )
                        memberships = getattr(dep_task, "memberships", []) or []
                        for membership in memberships:
                            proj = membership.get("project", {})
                            if proj.get("gid") == action_config.project_gid:
                                logger.info(
                                    "lifecycle_play_already_linked",
                                    created_gid=created_entity_gid,
                                    play_gid=dep_gid,
                                )
                                return CreationResult(success=True, entity_gid=dep_gid)

            # Reopen-or-create: check for recently completed plays
            if action_config.reopen_if_completed_within_days is not None:
                reopened = await self._try_reopen_recent_play_async(
                    created_entity_gid, action_config
                )
                if reopened is not None:
                    return reopened

            # Create play from template
            from autom8_asana.automation.templates import TemplateDiscovery

            template_discovery = TemplateDiscovery(self._client)
            template = await template_discovery.find_template_task_async(
                action_config.project_gid  # type: ignore[arg-type]  # project_gid validated non-None by action_config
            )

            if not template:
                logger.warning(
                    "lifecycle_play_template_not_found",
                    project_gid=action_config.project_gid,
                )
                return CreationResult(
                    success=False,
                    error=(f"No play template in project {action_config.project_gid}"),
                )

            # Get business for name generation
            business = await ctx.business_async()
            business_name = getattr(business, "name", None) or "Unknown"

            # Duplicate template
            play_name = f"{action_config.play_type} - {business_name}"
            new_play = await self._client.tasks.duplicate_async(
                template.gid,
                name=play_name,
                include=["subtasks", "notes"],
            )

            # Add to project
            await self._client.tasks.add_to_project_async(
                new_play.gid,
                action_config.project_gid,  # type: ignore[arg-type]  # project_gid validated non-None by action_config
            )

            # Wire as dependency
            await self._client.tasks.add_dependencies_async(  # type: ignore[attr-defined]
                created_entity_gid, [new_play.gid]
            )

            logger.info(
                "lifecycle_play_created",
                play_gid=new_play.gid,
                play_type=action_config.play_type,
                created_gid=created_entity_gid,
            )

            return CreationResult(success=True, entity_gid=new_play.gid)

        except Exception as e:
            logger.error(
                "lifecycle_play_creation_error",
                play_type=action_config.play_type,
                error=str(e),
            )
            return CreationResult(success=False, error=str(e))

    async def _try_reopen_recent_play_async(
        self,
        created_entity_gid: str,
        action_config: InitActionConfig,
    ) -> CreationResult | None:
        """Search for completed plays within threshold and reopen if found.

        Args:
            created_entity_gid: GID of the new process to wire dependency.
            action_config: Action config with reopen_if_completed_within_days.

        Returns:
            CreationResult if a play was reopened, None if no candidate found.
        """
        threshold_days = action_config.reopen_if_completed_within_days
        if threshold_days is None:
            return None

        try:
            cutoff = date.today() - timedelta(days=threshold_days)

            # Search for completed tasks in the play project
            tasks = await self._client.tasks.search_async(  # type: ignore[attr-defined]
                project=action_config.project_gid,
                completed=True,
                completed_since=cutoff.isoformat(),
                opt_fields=["gid", "completed", "completed_at"],
            )
            task_list = await tasks.collect() if hasattr(tasks, "collect") else tasks

            if not task_list:
                return None

            # Take the first (most recent) completed task
            candidate = task_list[0]
            candidate_gid = (
                candidate.gid if hasattr(candidate, "gid") else candidate.get("gid")
            )

            if not candidate_gid:
                return None

            # Reopen by marking incomplete
            await self._client.tasks.update_async(candidate_gid, completed=False)

            # Wire as dependency
            await self._client.tasks.add_dependencies_async(  # type: ignore[attr-defined]
                created_entity_gid, [candidate_gid]
            )

            logger.info(
                "lifecycle_play_reopened",
                play_gid=candidate_gid,
                play_type=action_config.play_type,
                created_gid=created_entity_gid,
            )

            return CreationResult(
                success=True,
                entity_gid=candidate_gid,
                was_reopened=True,
            )

        except Exception as e:
            # Reopen failure is non-fatal; fall through to create new
            logger.warning(
                "lifecycle_play_reopen_failed",
                play_type=action_config.play_type,
                error=str(e),
            )
            return None


class EntityCreationHandler(InitActionHandler):
    """Creates related entities (e.g., asset_edit) via EntityCreationService.

    Per TDD Section 2.9: Fully delegates to EntityCreationService.create_entity_async()
    which handles template discovery, duplication, section placement, field seeding,
    hierarchy placement, and assignee resolution.
    """

    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        """Create an entity via EntityCreationService."""
        try:
            from autom8_asana.lifecycle.creation import EntityCreationService

            creation_service = EntityCreationService(self._client, self._config)

            project_gid = action_config.project_gid
            holder_type = action_config.holder_type or "asset_edit_holder"
            template_section = "TEMPLATE"

            # Get stage config from source process type
            source_stage_name = source_process.process_type.value
            stage_config = self._config.get_stage(source_stage_name)

            if stage_config is None:
                logger.error(
                    "lifecycle_entity_creation_no_stage_config",
                    entity_type=action_config.entity_type,
                    stage_name=source_stage_name,
                )
                return CreationResult(
                    success=False,
                    error=(f"No stage config for '{source_stage_name}'"),
                )

            result = await creation_service.create_entity_async(
                project_gid=project_gid,  # type: ignore[arg-type]  # project_gid validated non-None by stage_config
                template_section=template_section,
                holder_type=holder_type,
                ctx=ctx,
                source_process=source_process,
                stage_config=stage_config,
            )
            return result

        except Exception as e:
            logger.error(
                "lifecycle_entity_creation_error",
                entity_type=action_config.entity_type,
                error=str(e),
            )
            return CreationResult(success=False, error=str(e))


class ProductsCheckHandler(InitActionHandler):
    """Checks products custom field for pattern match.

    Per TDD Section 2.9: When products match the condition pattern (e.g.,
    "video*"), creates a SourceVideographer entity under VideographyHolder
    via EntityCreationService.

    Steps:
    1. Get products custom field from Business
    2. Check if any product matches the condition pattern (fnmatch)
    3. If match, create entity via EntityCreationService
    """

    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        """Check products field and conditionally create entity."""
        try:
            # Get Business
            business = await ctx.business_async()

            # Get products custom field
            products = getattr(business, "products", None)
            if not products:
                logger.info(
                    "lifecycle_products_check_no_products",
                    created_gid=created_entity_gid,
                )
                return CreationResult(success=True, entity_gid="")

            # Check pattern match
            pattern = action_config.condition or ""
            matched = False

            # Products can be a list of strings or a single string
            if isinstance(products, list):
                for product in products:
                    if fnmatch.fnmatch(str(product).lower(), pattern.lower()):
                        matched = True
                        break
            elif isinstance(products, str):
                if fnmatch.fnmatch(products.lower(), pattern.lower()):
                    matched = True

            if not matched:
                logger.info(
                    "lifecycle_products_check_no_match",
                    pattern=pattern,
                    products=products,
                )
                return CreationResult(success=True, entity_gid="")

            # Match found: create entity via EntityCreationService
            from autom8_asana.lifecycle.creation import EntityCreationService

            creation_service = EntityCreationService(self._client, self._config)

            project_gid = action_config.project_gid or VIDEOGRAPHY_HOLDER_PROJECT
            holder_type = action_config.holder_type or "videography_holder"

            source_stage_name = source_process.process_type.value
            stage_config = self._config.get_stage(source_stage_name)

            if stage_config is None:
                logger.warning(
                    "lifecycle_products_check_no_stage_config",
                    stage_name=source_stage_name,
                )
                return CreationResult(
                    success=False,
                    error=(f"No stage config for '{source_stage_name}'"),
                )

            result = await creation_service.create_entity_async(
                project_gid=project_gid,
                template_section="TEMPLATE",
                holder_type=holder_type,
                ctx=ctx,
                source_process=source_process,
                stage_config=stage_config,
            )

            logger.info(
                "lifecycle_products_check_entity_created",
                action=action_config.action,
                pattern=pattern,
                entity_gid=result.entity_gid,
                created_gid=created_entity_gid,
            )

            return result

        except Exception as e:
            logger.error(
                "lifecycle_products_check_error",
                condition=action_config.condition,
                error=str(e),
            )
            return CreationResult(success=False, error=str(e))


class CampaignHandler(InitActionHandler):
    """Activates/deactivates campaigns.

    Used by:
    - month1: activate_campaign (terminal CONVERTED)
    - retention/reactivation/account_error: deactivate_campaign

    For now: log the action and return success.
    Actual campaign API integration is deferred to production implementation.
    """

    async def execute_async(
        self,
        ctx: ResolutionContext,
        created_entity_gid: str,
        action_config: InitActionConfig,
        source_process: Process,
    ) -> CreationResult:
        """Log campaign action (activation/deactivation)."""
        try:
            # Get Business for context
            business = await ctx.business_async()
            business_name = getattr(business, "name", None) or "Unknown"

            # Log the action
            logger.info(
                "lifecycle_campaign_action",
                action_type=action_config.type,
                business_name=business_name,
                business_gid=business.gid,
                created_gid=created_entity_gid,
            )

            return CreationResult(success=True, entity_gid="")

        except Exception as e:
            logger.error(
                "lifecycle_campaign_action_error",
                action_type=action_config.type,
                error=str(e),
            )
            return CreationResult(success=False, error=str(e))


# Handler registry -- maps action type strings from lifecycle_stages.yaml
# to handler classes. The engine's _DefaultInitActionRegistry uses this
# to dispatch init actions.
HANDLER_REGISTRY: dict[str, type[InitActionHandler]] = {
    "play_creation": PlayCreationHandler,
    "entity_creation": EntityCreationHandler,
    "products_check": ProductsCheckHandler,
    "activate_campaign": CampaignHandler,
    "deactivate_campaign": CampaignHandler,
    "create_comment": CommentHandler,
}
