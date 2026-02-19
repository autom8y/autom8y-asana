# src/autom8_asana/lifecycle/wiring.py

"""Dependency wiring service for lifecycle Phase 4 (WIRE).

Per TDD-lifecycle-engine-hardening Section 2.7:
- Wires standard dependents (Unit, OfferHolder) and dependencies (open DNA plays)
- Wires init-action-produced entity dependencies
- Fail-forward: wiring failures produce warnings, not hard failures

FR Coverage: FR-WIRE-001, FR-WIRE-002

Error Contract:
- ConnectionError for Asana API transport failures (narrowed from Exception)
- Outer try/except remains as fail-forward boundary guard per engine contract
- All failures produce warnings and partial WiringResult (never raises)
"""

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
    """Result of dependency wiring.

    Canonical definition -- engine.py has a duplicate for protocol typing
    but this is the authoritative version.
    """

    wired: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


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
        if not pipeline_rules:
            return result

        # Wire dependents (Unit, OfferHolder)
        for dep_config in pipeline_rules.dependents:
            entity_type: str = dep_config.get("entity_type", "")
            try:
                dependent_gid = await self._resolve_dependent_gid(entity_type, ctx)
                if dependent_gid:
                    await self._client.tasks.add_dependent_async(  # type: ignore[attr-defined]
                        entity_gid, dependent_gid
                    )
                    result.wired.append(dependent_gid)
            except (ConnectionError, TimeoutError, OSError) as e:
                msg = f"Failed to wire dependent '{entity_type}': {e}"
                logger.warning(
                    "lifecycle_wire_dependent_failed",
                    entity_type=entity_type,
                    error=str(e),
                )
                result.warnings.append(msg)
            except Exception as e:  # BROAD-CATCH: fail-forward boundary
                msg = f"Unexpected error wiring dependent '{entity_type}': {e}"
                logger.warning(
                    "lifecycle_wire_dependent_failed",
                    entity_type=entity_type,
                    error=str(e),
                )
                result.warnings.append(msg)

        # Wire dependencies (open DNA plays)
        for dep_config in pipeline_rules.dependencies:
            source = dep_config.get("source")
            filter_type = dep_config.get("filter")
            if source == "dna_holder" and filter_type == "open_plays":
                await self._wire_open_plays(entity_gid, ctx, result)

        return result

    async def _wire_open_plays(
        self,
        entity_gid: str,
        ctx: ResolutionContext,
        result: WiringResult,
    ) -> None:
        """Wire open DNA plays as dependencies of the newly created entity.

        Resolves DNAHolder from the business entity. If business.dna_holder
        is None, attempts resolution via ctx.resolve_holder_async.
        """
        try:
            business = await ctx.business_async()
            dna_holder = business.dna_holder

            # If dna_holder is not populated, try resolving it
            if dna_holder is None:
                from autom8_asana.models.business.business import DNAHolder

                dna_holder = await ctx.resolve_holder_async(DNAHolder)  # type: ignore[type-var]  # DNAHolder satisfies Holder protocol at runtime
                if dna_holder is not None:
                    business.dna_holder = dna_holder  # type: ignore[misc]  # property setter exists at runtime

            if dna_holder is None:
                return

            await ctx.hydrate_branch_async(business, "dna_holder")

            for dna in dna_holder.children:
                if not dna.completed:
                    try:
                        await self._client.tasks.add_dependency_async(  # type: ignore[attr-defined]
                            entity_gid, dna.gid
                        )
                        result.wired.append(dna.gid)
                    except (ConnectionError, TimeoutError, OSError) as e:
                        msg = f"Failed to wire DNA play '{dna.gid}': {e}"
                        logger.warning(
                            "lifecycle_wire_play_failed",
                            play_gid=dna.gid,
                            error=str(e),
                        )
                        result.warnings.append(msg)

        except (ConnectionError, TimeoutError, OSError) as e:
            msg = f"Failed to wire open plays: {e}"
            logger.warning(
                "lifecycle_wire_open_plays_failed",
                error=str(e),
            )
            result.warnings.append(msg)
        except Exception as e:  # BROAD-CATCH: fail-forward boundary
            msg = f"Unexpected error wiring open plays: {e}"
            logger.warning(
                "lifecycle_wire_open_plays_failed",
                error=str(e),
            )
            result.warnings.append(msg)

    async def wire_entity_as_dependency_async(
        self,
        created_gid: str,
        target_entity_gid: str,
        dependency_of_stage: str,
    ) -> WiringResult:
        """Wire a created entity as a dependency of a target entity.

        Used for init-action entities that need dependency wiring, e.g.:
        BOAB play (created_gid) -> dependency of Implementation (target_entity_gid).

        Args:
            created_gid: GID of the newly created entity (the dependency).
            target_entity_gid: GID of the entity that depends on created_gid.
            dependency_of_stage: Stage name for logging context.

        Returns:
            WiringResult with wired GID or warning on failure.
        """
        result = WiringResult()

        if not target_entity_gid:
            msg = (
                f"No target entity GID for wiring '{created_gid}' "
                f"as dependency of stage '{dependency_of_stage}'"
            )
            logger.warning(
                "lifecycle_wire_entity_dependency_skipped",
                created_gid=created_gid,
                stage=dependency_of_stage,
            )
            result.warnings.append(msg)
            return result

        try:
            await self._client.tasks.add_dependency_async(  # type: ignore[attr-defined]  # generated by @async_method
                target_entity_gid,
                created_gid,
            )
            result.wired.append(created_gid)
        except (ConnectionError, TimeoutError, OSError) as e:
            msg = (
                f"Failed to wire '{created_gid}' as dependency "
                f"of '{target_entity_gid}': {e}"
            )
            logger.warning(
                "lifecycle_wire_entity_dependency_failed",
                created_gid=created_gid,
                target_gid=target_entity_gid,
                stage=dependency_of_stage,
                error=str(e),
            )
            result.warnings.append(msg)
        except Exception as e:  # BROAD-CATCH: fail-forward boundary
            msg = (
                f"Unexpected error wiring '{created_gid}' as dependency "
                f"of '{target_entity_gid}': {e}"
            )
            logger.warning(
                "lifecycle_wire_entity_dependency_failed",
                created_gid=created_gid,
                target_gid=target_entity_gid,
                stage=dependency_of_stage,
                error=str(e),
            )
            result.warnings.append(msg)

        return result

    async def _resolve_dependent_gid(
        self,
        entity_type: str,
        ctx: ResolutionContext,
    ) -> str | None:
        """Resolve GID for a dependent entity.

        Args:
            entity_type: Type identifier ("unit" or "offer_holder").
            ctx: Resolution context.

        Returns:
            GID string or None if entity not available.
        """
        if entity_type == "unit":
            unit = await ctx.unit_async()
            return unit.gid
        elif entity_type == "offer_holder":
            unit = await ctx.unit_async()
            if unit.offer_holder:
                return unit.offer_holder.gid
        return None
