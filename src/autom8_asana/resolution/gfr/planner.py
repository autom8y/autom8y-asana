"""GFR planner — pure/synchronous hop planning (INVARIANT I1, TDD §5).

Given the entry entity type and the requested fields, the planner:

1. partitions the requested fields by their OWNING entity via ``SchemaRegistry``
   (the field-legality source of truth — INVARIANT I4 ``unknown-field``); and
2. classifies the HOP CLASS by which each owner is reached from the entry entity
   (TDD §5.1): ``LOCAL`` (own row), ``IN_FRAME_PARENT`` (owner reachable via the
   in-frame ``parent_gid``), or ``PARENT_CHAIN`` (owner reachable only via the
   live ``_traverse_upward_async`` chain — the offer->Business case, §5.2).

The planner is PURE and SYNCHRONOUS — it performs no I/O and never reaches the
Asana API. ``office_phone`` is NEVER used to plan an identity hop (INVARIANT I1):
identity (``company_id``) is always owned by Business and always reached by the
parent chain + gid-exact row read, so its plan element is marked ``is_identity``.

Why offer is ``PARENT_CHAIN`` and not ``IN_FRAME_PARENT`` (TDD §5.2): the in-frame
``parent_gid`` of an offer points at its OfferHolder, not Business, and there is
no in-frame column carrying the Business gid. The only collision-free path to
``company_id`` from an offer is the live parent chain.
"""

from __future__ import annotations

from typing import Final

from autom8y_log import get_logger

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.core.types import EntityType
from autom8_asana.dataframes.models.registry import SchemaRegistry
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import FieldPlan, HopClass, ResolutionPlan

logger = get_logger(__name__)

# Tenant-identity field(s). ``company_id`` lives ONLY on the Business schema
# (``business.py:8-13``); reaching it is the load-bearing identity hop guarded by
# INVARIANT I1. Declared as a frozenset so the guard and planner agree on the set.
IDENTITY_FIELDS: Final[frozenset[str]] = frozenset({"company_id"})

# Entity types whose in-frame ``parent_gid`` IS / reaches the owner in one hop
# (TDD §5.1 / §5.2). Offer is deliberately ABSENT: its in-frame parent is the
# OfferHolder, so offer->Business is a PARENT_CHAIN hop, not an in-frame hop.
_IN_FRAME_PARENT_ENTITIES: Final[frozenset[EntityType]] = frozenset(
    {
        EntityType.BUSINESS,
        EntityType.UNIT,
        EntityType.CONTACT,
        EntityType.ASSET_EDIT,
    }
)


def _owning_entity(field: str) -> str | None:
    """Return the snake_case entity name whose schema declares ``field``.

    Resolves against the resolvable dataframe entities (those with a schema).
    Returns ``None`` if no resolvable schema declares the field (FM5 / INVARIANT
    I4 ``unknown-field``).

    Owner-ambiguity note (TDD R-7): a field may appear on multiple schemas via
    BASE_COLUMNS. Identity fields (``company_id``) are Business-only, so they are
    never ambiguous; for non-identity fields the FIRST resolvable owner in
    registry definition order wins deterministically (the planner never makes a
    silent wrong-owner pick — an un-owned field raises ``unknown-field``).
    """
    registry = get_registry()
    schema_registry = SchemaRegistry.get_instance()
    for name in registry.dataframe_entities():
        descriptor = registry.get(name)
        if descriptor is None:
            continue
        try:
            schema = schema_registry.get_schema(descriptor.pascal_name)
        except Exception:  # noqa: BLE001 -- a missing schema means this entity cannot own the field
            continue
        if schema.get_column(field) is not None:
            return name
    return None


def _classify_hop(entry_entity_type: EntityType, owner: str) -> HopClass:
    """Classify how ``owner`` is reached from the entry entity (TDD §5.1).

    Args:
        entry_entity_type: Detected type of the entry gid.
        owner: snake_case owning entity name for the field set.

    Returns:
        ``LOCAL`` if the owner is the entry entity itself; ``IN_FRAME_PARENT`` if
        the entry entity carries an in-frame ``parent_gid`` that reaches the
        owner in one hop; otherwise ``PARENT_CHAIN`` (offer->Business and any
        entry whose in-frame parent does not reach the owner).
    """
    if entry_entity_type.value == owner:
        return HopClass.LOCAL
    if entry_entity_type in _IN_FRAME_PARENT_ENTITIES:
        return HopClass.IN_FRAME_PARENT
    return HopClass.PARENT_CHAIN


def plan_resolution(entry_entity_type: EntityType, fields: list[str]) -> ResolutionPlan:
    """Build the resolution plan for a set of requested fields (TDD §4 step 3).

    Args:
        entry_entity_type: Detected type of the entry gid (from the entry phase).
        fields: Requested schema-declared field names.

    Returns:
        A ``ResolutionPlan`` with one ``FieldPlan`` per distinct owning entity.

    Raises:
        UnresolvedError(reason="unknown-field"): if any requested field is not
            declared by any resolvable schema (FM5 / INVARIANT I4 all-or-nothing
            — the WHOLE call fails, carrying the offending field(s)).
    """
    owner_to_fields: dict[str, list[str]] = {}
    unknown: list[str] = []
    for field in fields:
        owner = _owning_entity(field)
        if owner is None:
            unknown.append(field)
            continue
        owner_to_fields.setdefault(owner, []).append(field)

    if unknown:
        # All-or-nothing: a single unknown field fails the whole call.
        raise UnresolvedError(fields=unknown, reason="unknown-field")

    field_plans: list[FieldPlan] = []
    for owner, owned_fields in owner_to_fields.items():
        hop = _classify_hop(entry_entity_type, owner)
        is_identity = any(f in IDENTITY_FIELDS for f in owned_fields)
        field_plans.append(
            FieldPlan(owner=owner, fields=owned_fields, hop=hop, is_identity=is_identity)
        )
        logger.debug(
            "GFR plan: owner classified",
            extra={
                "entry_type": entry_entity_type.value,
                "owner": owner,
                "hop": hop.value,
                "is_identity": is_identity,
                "fields": owned_fields,
            },
        )

    return ResolutionPlan(
        entry_entity_type=entry_entity_type.value,
        field_plans=field_plans,
    )
