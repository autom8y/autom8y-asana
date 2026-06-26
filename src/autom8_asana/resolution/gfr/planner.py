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


def _entry_schema_declares(entry_entity_type: EntityType, field: str) -> bool:
    """Return True if the ENTRY entity's OWN schema declares ``field``.

    Entry-scoped ownership (ADR-gfr-dynvocab-tail-scope, Option A): the
    partition criterion is narrowed from "owned by ANY resolvable schema"
    (``_owning_entity``) to "owned by the entry entity's own schema." This is the
    discriminator that lets a *foreign*-schema column (e.g. ``asset_edit`` declaring
    ``asset_id``) NOT suppress dynamic-tail routing for an Offer entry, while a field
    on the entry's own schema (e.g. ``office_phone`` on Offer) stays schema-routed.

    Resolves ONLY the entry entity's descriptor->schema and asks ``get_column``.
    Returns ``False`` if the entry entity has no descriptor or no resolvable schema
    (the field then falls through to the dynamic tail, which judges absence against
    the live manifest — governed-strict). The identity carve-out is handled by the
    caller BEFORE this fallthrough and is unaffected.
    """
    registry = get_registry()
    descriptor = registry.get(entry_entity_type.value)
    if descriptor is None:
        return False
    schema_registry = SchemaRegistry.get_instance()
    try:
        schema = schema_registry.get_schema(descriptor.pascal_name)
    except Exception:  # noqa: BLE001 -- a missing entry schema => route to the tail
        return False
    return schema.get_column(field) is not None


def _owning_entity_for_entry(field: str, entry_entity_type: EntityType) -> str | None:
    """Entry-scoped owner resolution (ADR Option A, the partition predicate).

    Returns the owning snake_case entity name for ``field`` under the entry-scoped
    criterion:

    * an IDENTITY field (``company_id``) -> its certified Business owner via the
      global ``_owning_entity`` (the identity carve-out is UNCHANGED — ``company_id``
      always resolves to a Business identity plan with ``is_identity=True``);
    * a field on the ENTRY entity's OWN schema -> the entry entity itself;
    * otherwise ``None`` -> the planner routes it to ``dynamic_fields`` (the tail).

    The narrowing from ``_owning_entity`` (first resolvable schema, ANY entity) to
    this entry-scoped test is the whole of the Option A change: foreign-schema
    ownership no longer suppresses tail routing. ``_owning_entity`` is retained
    unchanged and is still consulted for the identity carve-out.
    """
    # Identity carve-out FIRST (ADR risk-note mitigation): company_id is
    # Business-owned, NOT entry-owned, yet MUST still resolve to the identity plan.
    if field in IDENTITY_FIELDS:
        return _owning_entity(field)
    # Entry-scoped: a non-identity field is "owned" only if the entry entity's own
    # schema declares it; otherwise it routes to the dynamic tail.
    if _entry_schema_declares(entry_entity_type, field):
        return entry_entity_type.value
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
        A ``ResolutionPlan`` with one ``FieldPlan`` per distinct owning entity and
        a ``dynamic_fields`` list of requested fields with no resolvable schema
        owner (sprint-2 D-T1a).

    Note (sprint-2 D-T1a — interception point moved, caller contract preserved):
        A field with no resolvable schema owner is NOT raised on at plan time. The
        planner is manifest-blind — it cannot distinguish "this is a dynamic custom
        field that lives on the live task" from "this field is genuinely nonexistent"
        without the cf manifest, which only the entry phase produces. So it PARTITIONS
        such fields into ``ResolutionPlan.dynamic_fields`` and defers the
        absent/present verdict to the ``is_identity=False`` dynamic tail
        (``dynvocab.resolve_dynamic_fields``), which judges absence against the real
        manifest (governed-strict). The caller-visible
        ``UnresolvedError(reason="unknown-field")`` for a genuinely-absent field is
        PRESERVED — only the point at which that verdict is reached moves from
        plan-time (premature, manifest-blind) to tail-time (manifest-aware). The
        closed reason vocabulary (``errors.py``) is NOT widened.
    """
    owner_to_fields: dict[str, list[str]] = {}
    dynamic_fields: list[str] = []
    for field in fields:
        # Option A (ADR-gfr-dynvocab-tail-scope): entry-scoped ownership. A
        # non-identity field is "owned" only when the ENTRY entity's OWN schema
        # declares it; a foreign-schema column (e.g. asset_edit owning asset_id) no
        # longer suppresses tail routing for an Offer entry. The identity carve-out
        # (company_id -> Business) is preserved inside _owning_entity_for_entry.
        owner = _owning_entity_for_entry(field, entry_entity_type)
        if owner is None:
            # D-T1a: no entry-scoped owner => route to the dynamic tail, do NOT raise
            # here. The tail makes the governed-strict absent/unknown call against the
            # live manifest; a field genuinely absent there still raises 'unknown-field'.
            dynamic_fields.append(field)
            continue
        owner_to_fields.setdefault(owner, []).append(field)

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

    if dynamic_fields:
        logger.debug(
            "GFR plan: fields routed to dynamic tail (no schema owner)",
            extra={
                "entry_type": entry_entity_type.value,
                "dynamic_fields": dynamic_fields,
            },
        )

    return ResolutionPlan(
        entry_entity_type=entry_entity_type.value,
        field_plans=field_plans,
        dynamic_fields=dynamic_fields,
    )
