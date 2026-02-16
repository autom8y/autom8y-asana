"""Cascading section updates during lifecycle transitions.

Per TDD-lifecycle-engine-hardening Section 2.5:
- Unchanged from prototype design (clean and handles all section update needs)
- Each stage has specific section mappings for Offer, Unit, Business
- Not all stages update all three entities
- Section names are case-insensitive matched

FR Coverage: FR-ROUTE-001 AC-4, FR-ROUTE-002 AC-4, FR-ROUTE-003 AC-4

Error Contract:
- Each entity section update is wrapped in its own try/except
- Failure is logged as warning and skipped (fail-forward)
- Section not found in project logs a warning and continues
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.lifecycle.config import CascadingSectionConfig

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.resolution.context import ResolutionContext

logger = get_logger(__name__)


@dataclass
class CascadeResult:
    """Result of cascading section updates.

    Attributes:
        updates: GIDs of entities successfully moved to new sections.
        warnings: Description of any non-fatal issues encountered.
    """

    updates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class CascadingSectionService:
    """Updates Offer, Unit, and Business sections during stage transitions.

    Per stakeholder Appendix C, section mappings by stage:

    | Stage          | Offer Section  | Unit Section | Business Section |
    |----------------|---------------|--------------|------------------|
    | Outreach       | Sales Process | Engaged      | OPPORTUNITY      |
    | Sales          | Sales Process | Next Steps   | OPPORTUNITY      |
    | Onboarding     | ACTIVATING    | Onboarding   | ONBOARDING       |
    | Implementation | IMPLEMENTING  | Implementing | IMPLEMENTING     |

    Fail-forward: if any section update fails, log warning and continue
    with remaining updates. A partial success is better than total failure.
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def cascade_async(
        self,
        config: CascadingSectionConfig,
        ctx: ResolutionContext,
    ) -> CascadeResult:
        """Apply cascading section updates for a stage transition.

        Resolves Offer, Unit, and Business entities via ResolutionContext,
        then moves each to the section name specified in config.

        Args:
            config: Section names for offer/unit/business from StageConfig.
            ctx: Resolution context for entity access.

        Returns:
            CascadeResult with list of updated entity GIDs and any warnings.
        """
        result = CascadeResult()

        # Update Offer section
        if config.offer:
            await self._update_entity_section_async(
                ctx.offer_async, config.offer, "offer", result
            )

        # Update Unit section
        if config.unit:
            await self._update_entity_section_async(
                ctx.unit_async, config.unit, "unit", result
            )

        # Update Business section
        if config.business:
            await self._update_entity_section_async(
                ctx.business_async, config.business, "business", result
            )

        return result

    async def _update_entity_section_async(
        self,
        resolve_fn: Any,
        section_name: str,
        entity_type: str,
        result: CascadeResult,
    ) -> None:
        """Resolve an entity and move it to the named section.

        Args:
            resolve_fn: Async callable that resolves the entity (e.g. ctx.offer_async).
            section_name: Target section name (case-insensitive match).
            entity_type: Label for logging ("offer", "unit", "business").
            result: CascadeResult to accumulate updates and warnings.
        """
        try:
            entity = await resolve_fn()
            moved = await self._move_to_section_async(entity, section_name, entity_type)
            if moved:
                result.updates.append(entity.gid)
            else:
                result.warnings.append(
                    f"Section '{section_name}' not found for {entity_type}"
                )
        except (
            Exception
        ) as e:  # BROAD-CATCH: boundary -- cascade section update soft-fails per entity
            logger.warning(
                f"cascade_{entity_type}_section_failed",
                section=section_name,
                error=str(e),
            )
            result.warnings.append(f"Failed to update {entity_type} section: {e}")

    async def _move_to_section_async(
        self,
        entity: Any,
        section_name: str,
        entity_type: str,
    ) -> bool:
        """Move entity to named section in its primary project.

        Finds the entity's project from its memberships, lists all sections
        in that project, and moves the entity to the section matching
        section_name (case-insensitive).

        Args:
            entity: The entity to move (must have .gid and .memberships).
            section_name: Target section name to match (case-insensitive).
            entity_type: Label for logging ("offer", "unit", "business").

        Returns:
            True if entity was moved, False if section not found.
        """
        if not entity.memberships:
            logger.warning(
                f"cascade_{entity_type}_no_memberships",
                entity_gid=entity.gid,
                section=section_name,
            )
            return False

        # Get project GID from first membership
        project_gid = None
        for m in entity.memberships:
            p = m.get("project", {})
            if p.get("gid"):
                project_gid = p["gid"]
                break

        if not project_gid:
            logger.warning(
                f"cascade_{entity_type}_no_project",
                entity_gid=entity.gid,
                section=section_name,
            )
            return False

        # Find section by name (case-insensitive)
        sections = await self._client.sections.list_for_project_async(
            project_gid
        ).collect()

        target = next(
            (s for s in sections if s.name and s.name.lower() == section_name.lower()),
            None,
        )

        if not target:
            logger.warning(
                f"cascade_{entity_type}_section_not_found",
                entity_gid=entity.gid,
                project_gid=project_gid,
                section=section_name,
            )
            return False

        # Move entity to target section
        await self._client.sections.add_task_async(target.gid, task=entity.gid)  # type: ignore[attr-defined]

        logger.info(
            f"cascade_{entity_type}_section_updated",
            entity_gid=entity.gid,
            section_gid=target.gid,
            section_name=section_name,
        )
        return True
