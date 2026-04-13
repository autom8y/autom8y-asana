"""Section name resolution for metric scopes.

Resolves human-readable section names (e.g., "Active") to Asana GIDs using
an offline-first strategy: S3 manifest data first, enum fallback second.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autom8_asana.dataframes.section_persistence import SectionPersistence
    from autom8_asana.metrics.metric import Metric


@dataclass(frozen=True)
class SectionIndex:
    """Case-insensitive name → GID index."""

    _name_to_gid: dict[str, str]

    def resolve(self, name: str) -> str | None:
        """Look up a section GID by name (case-insensitive)."""
        return self._name_to_gid.get(name.lower())

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    async def from_manifest_async(
        cls,
        persistence: SectionPersistence,
        project_gid: str,
    ) -> SectionIndex:
        """Build an index from section names stored in the S3 manifest."""
        manifest = await persistence.get_manifest_async(project_gid)
        if manifest is None:
            return cls(_name_to_gid={})
        return cls(_name_to_gid=manifest.get_section_name_index())

    @classmethod
    def from_enum_fallback(cls, entity_type: str) -> SectionIndex:
        """Build an index from hardcoded enum members.

        Currently supports ``entity_type="offer"`` via
        :class:`~autom8_asana.models.business.sections.OfferSection`.
        Returns an empty index for unknown entity types.
        """
        if entity_type == "offer":
            from autom8_asana.models.business.sections import OfferSection

            mapping = {}
            for member in OfferSection:
                name = OfferSection.from_name(member.name)
                if name is not None:
                    mapping[member.name.lower()] = member.value
            return cls(_name_to_gid=mapping)

        return cls(_name_to_gid={})


def resolve_metric_scope(metric: Metric, index: SectionIndex) -> Metric:
    """Return a new Metric with its scope's section GID resolved.

    Resolution rules:
    1. If ``scope.section`` is already set → passthrough (GID wins).
    2. If ``scope.section_name`` is set → look up via *index*.
    3. Raise :class:`ValueError` if the name cannot be resolved.

    The original Metric is never mutated.
    """
    if metric.scope.section is not None:
        return metric

    if metric.scope.section_name is None:
        return metric

    gid = index.resolve(metric.scope.section_name)
    if gid is None:
        msg = (
            f"Cannot resolve section name {metric.scope.section_name!r} for metric {metric.name!r}"
        )
        raise ValueError(msg)

    new_scope = metric.scope.with_resolved_section(gid)
    return replace(metric, scope=new_scope)
