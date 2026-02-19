"""Shared creation primitives for pipeline and lifecycle entity creation.

Both automation/pipeline.py and lifecycle/creation.py use these functions
for the common steps: name generation, template discovery, task duplication,
section placement, due date computation, and subtask waiting.

Seeding is intentionally NOT shared -- automation uses FieldSeeder (explicit
field lists), lifecycle uses AutoCascadeSeeder (zero-config matching).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.core import Task

logger = get_logger(__name__)


def generate_entity_name(
    template_name: str | None,
    business: Any,
    unit: Any,
    fallback_name: str = "New Process",
) -> str:
    """Generate task name by replacing [Business Name] and [Unit Name] placeholders.

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
        fallback_name: Name to return when template_name is None or empty.
            Defaults to "New Process". Pass a custom value to override
            (e.g., pipeline.py passes f"New {target_type.value.title()}").

    Returns:
        Task name with placeholders replaced by actual values.
        Falls back to fallback_name if template_name is None or empty.

    Example:
        >>> generate_entity_name(
        ...     "Onboarding Process - [Business Name]",
        ...     business=Business(name="Acme Corp"),
        ...     unit=None,
        ... )
        "Onboarding Process - Acme Corp"
    """
    if not template_name:
        return fallback_name

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


async def discover_template_async(
    client: AsanaClient,
    project_gid: str,
    template_section: str | None = None,
    template_section_gid: str | None = None,
) -> Task | None:
    """Discover template task in project. Wraps TemplateDiscovery.

    Per FR-004: Template discovery with fuzzy matching.
    IMP-13: Includes num_subtasks in opt_fields to avoid a separate API call.

    Args:
        client: AsanaClient for API operations.
        project_gid: GID of the target project.
        template_section: Optional section name to restrict search.
        template_section_gid: Optional pre-configured section GID from YAML.
            When provided, skips runtime section discovery entirely.

    Returns:
        Template Task if found (with num_subtasks populated), else None.
    """
    from autom8_asana.automation.templates import TemplateDiscovery

    discovery = TemplateDiscovery(client)
    return await discovery.find_template_task_async(
        project_gid,
        template_section=template_section,
        template_section_gid=template_section_gid,
        opt_fields=["num_subtasks"],
    )


async def duplicate_from_template_async(
    client: AsanaClient,
    template: Task,
    name: str,
) -> Task:
    """Duplicate template task with subtasks and notes.

    Per FR-DUP-001: Use duplicate_async to copy template with subtasks.

    Args:
        client: AsanaClient for API operations.
        template: Template Task to duplicate.
        name: Name for the duplicated task.

    Returns:
        Newly duplicated Task.
    """
    return await client.tasks.duplicate_async(
        template.gid,
        name=name,
        include=["subtasks", "notes"],
    )


async def place_in_section_async(
    client: AsanaClient,
    task_gid: str,
    project_gid: str,
    section_name: str,
) -> bool:
    """Move task to named section in project.

    Per G3 Gap Fix: Place new task in configured target section.
    Uses case-insensitive matching for section name.
    Graceful degradation if section not found (logs warning, returns False).

    Args:
        client: AsanaClient for API operations.
        task_gid: GID of the task to move.
        project_gid: GID of the project containing the section.
        section_name: Name of the target section (case-insensitive match).

    Returns:
        True if task was moved to section, False if section not found or error.
    """
    try:
        sections = await client.sections.list_for_project_async(
            project_gid,
        ).collect()
        section_name_lower = section_name.lower()
        target = next(
            (s for s in sections if s.name and s.name.lower() == section_name_lower),
            None,
        )
        if target:
            await client.sections.add_task_async(  # type: ignore[attr-defined]
                target.gid,
                task=task_gid,
            )
            return True
        else:
            logger.warning(
                "creation_section_not_found",
                section=section_name,
                project_gid=project_gid,
                task_gid=task_gid,
            )
            return False
    except Exception as e:  # BROAD-CATCH: non-fatal config step
        logger.warning(
            "creation_section_placement_failed",
            task_gid=task_gid,
            section=section_name,
            error=str(e),
        )
        return False


def compute_due_date(offset_days: int) -> str:
    """Compute due date as ISO string from today + offset.

    Per G4 Gap Fix: Set due date relative to today.

    Args:
        offset_days: Number of days from today for due date.
            0 = today, positive = future, negative = past.

    Returns:
        ISO date string in "YYYY-MM-DD" format.
    """
    due_date = date.today() + timedelta(days=offset_days)
    return due_date.isoformat()


async def wait_for_subtasks_async(
    client: AsanaClient,
    task_gid: str,
    expected_count: int,
    timeout: float = 2.0,
) -> bool:
    """Wait for Asana to finish creating subtasks after duplication.

    Per ADR-0111: Polling-based wait for subtask availability.
    After duplicating a task with subtasks, Asana creates subtasks asynchronously.

    Args:
        client: AsanaClient for API operations.
        task_gid: GID of the parent task.
        expected_count: Number of subtasks to wait for.
        timeout: Timeout in seconds (default 2.0).

    Returns:
        True if expected count reached within timeout, False otherwise.
    """
    from autom8_asana.automation.waiter import SubtaskWaiter

    waiter = SubtaskWaiter(client)
    return await waiter.wait_for_subtasks_async(
        task_gid,
        expected_count=expected_count,
        timeout=timeout,
    )
