"""The projects D6 registers webhooks on, and the trigger kinds it registers (section 3).

Design of record: TDD-asana-bench-D6-shadow-receiver-20261110 r4.6, section 3 (W F-10).

Until the W F-10 Rules read, the watched projects are AssetEdit and Offer ONLY. The
project gids come from ``ProjectTypeRegistry.get_primary_gid``
(models/business/registry.py:213). A watched type with no registered gid refuses loudly;
it is never skipped.

The per-project trigger map is an EXPLICIT input, empty by default (auth-bench A2-4,
verdict c886fc3cefa0). A project with no map row registers NOTHING: its
``trigger_kinds`` is empty, and the registrar makes no Asana call for it. A row names
which of Tom's two kinds (48f28bd7b63f Q9) the project fires: completions, section moves,
or both. No map ships in this PR, so registration registers zero webhooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final, Protocol

from autom8_asana.core.types import EntityType

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class TriggerKind(StrEnum):
    COMPLETION = "completion"
    SECTION_MOVE = "section_move"


# Section 3 filters, one webhook per watched project. Asana's filter grammar cannot say
# "the parent is a section", so the section-move filter registers task ``added`` and the
# decide path admits only a section parent (section 5 step 2, fixture SM-F1). ``removed``
# is never registered.
TRIGGER_FILTERS: Final[Mapping[TriggerKind, Mapping[str, Any]]] = {
    TriggerKind.COMPLETION: {"resource_type": "task", "action": "changed", "fields": ["completed"]},
    TriggerKind.SECTION_MOVE: {"resource_type": "task", "action": "added"},
}

# AssetEdit and Offer only, until the W F-10 Rules read (section 3).
WATCHED_ENTITY_TYPES: Final[tuple[EntityType, ...]] = (EntityType.ASSET_EDIT, EntityType.OFFER)

# The shipped map: empty. A project with no row registers nothing (auth A2-4).
EMPTY_TRIGGER_MAP: Final[Mapping[str, tuple[TriggerKind, ...]]] = {}


class WatchedProjectUnresolved(LookupError):
    """A watched entity type has no primary project gid registered."""


class PrimaryGidSource(Protocol):
    def get_primary_gid(self, entity_type: EntityType) -> str | None: ...


@dataclass(frozen=True)
class WatchedProject:
    entity_type: EntityType
    project_gid: str
    trigger_kinds: tuple[TriggerKind, ...] = ()

    def filters(self) -> list[dict[str, Any]]:
        return [dict(TRIGGER_FILTERS[kind]) for kind in self.trigger_kinds]


def _default_source() -> PrimaryGidSource:
    from autom8_asana.models.business.registry import get_registry

    return get_registry()


def watched_projects(
    source: PrimaryGidSource | None = None,
    *,
    trigger_map: Mapping[str, Sequence[TriggerKind]] = EMPTY_TRIGGER_MAP,
) -> tuple[WatchedProject, ...]:
    """The watched projects, in ``WATCHED_ENTITY_TYPES`` order.

    ``trigger_map`` is keyed by project gid. A project with no row (or an empty row) gets
    no trigger kinds, so nothing is registered for it.
    """
    registry = _default_source() if source is None else source
    projects: list[WatchedProject] = []
    for entity_type in WATCHED_ENTITY_TYPES:
        gid = registry.get_primary_gid(entity_type)
        if not gid:
            raise WatchedProjectUnresolved(
                f"no primary project gid is registered for {entity_type.value}"
            )
        kinds = tuple(dict.fromkeys(TriggerKind(k) for k in trigger_map.get(gid, ())))
        projects.append(
            WatchedProject(entity_type=entity_type, project_gid=gid, trigger_kinds=kinds)
        )
    return tuple(projects)
