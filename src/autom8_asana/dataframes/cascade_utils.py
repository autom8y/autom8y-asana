"""Dynamic cascade derivation utilities.

Replaces hardcoded cascade field lists, entity type checks, and warm
ordering with functions that derive everything from the existing metadata:

1. ``DataFrameSchema`` columns with ``source="cascade:..."``
2. ``get_cascading_field_registry()`` mapping field names to providers
3. ``EntityDescriptor.cascading_field_provider`` flag

All imports are deferred inside function bodies to avoid circular deps.
"""

from __future__ import annotations

from collections import defaultdict

from autom8y_log import get_logger

logger = get_logger(__name__)


class WarmupOrderingError(Exception):
    """Raised when warm-up ordering invariant is violated.

    This error is NEVER caught by BROAD-CATCH handlers. It indicates
    a safety-critical invariant violation that would produce corrupted
    cascade data (SCAR-005/006).
    """

    pass


def is_cascade_provider(entity_type: str) -> bool:
    """Check if an entity type provides cascade fields to other entities.

    Queries ``EntityDescriptor.cascading_field_provider`` — currently
    True for ``business``, ``unit``, and ``unit_holder`` (the frame-less
    scheduling-posture provider, OFFER_SCHEMA 1.6.0).

    Args:
        entity_type: Snake-case entity type name (e.g., "business").

    Returns:
        True if the entity provides cascading fields.
    """
    from autom8_asana.core.entity_registry import get_registry

    desc = get_registry().get(entity_type)
    return desc is not None and desc.cascading_field_provider


def cascade_provider_field_mapping(entity_type: str) -> dict[str, str]:
    """Derive the cascade field mapping for a provider entity.

    For a cascade provider (e.g., ``business``), returns a mapping of
    DataFrame column names to Asana custom field names for all fields
    that entity provides to others.

    The mapping is built by cross-referencing the provider's schema
    columns (``source="cf:Office Phone"``) with its
    ``CascadingFieldDef`` declarations.

    Args:
        entity_type: Snake-case entity type name.

    Returns:
        Dict mapping column name to Asana field name.
        E.g., ``{"office_phone": "Office Phone"}``.
        Empty dict if not a cascade provider.
    """
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.core.string_utils import to_pascal_case
    from autom8_asana.dataframes.models.registry import get_schema
    from autom8_asana.models.business.fields import get_cascading_field_registry

    registry = get_registry()
    desc = registry.get(entity_type)
    if desc is None or not desc.cascading_field_provider:
        return {}

    model_class = desc.get_model_class()
    if model_class is None:
        return {}

    # Collect Asana field names this provider declares
    cascade_registry = get_cascading_field_registry()
    provided_fields: set[str] = set()
    for _norm_name, (owner_class, field_def) in cascade_registry.items():
        if owner_class is model_class:
            provided_fields.add(field_def.name)

    if not provided_fields:
        return {}

    # Cross-reference against the provider's schema to find column names.
    # The schema has columns like source="cf:Office Phone" — the part
    # after "cf:" matches CascadingFieldDef.name.
    try:
        schema = get_schema(to_pascal_case(entity_type))
    except Exception:  # noqa: BLE001
        return {}

    mapping: dict[str, str] = {}
    for col in schema.columns:
        if col.source is None:
            continue
        # Match "cf:Office Phone" against provided fields
        if col.source.startswith("cf:"):
            asana_name = col.source[len("cf:") :].strip()
            if asana_name in provided_fields:
                mapping[col.name] = asana_name
        # Also match source_field="name" (Business Name cascades from Task.name)
        # These are columns where source=None but the CascadingFieldDef has
        # source_field set. We handle this by checking all provided field names
        # against the column name as a fallback.

    # Handle CascadingFieldDefs with source_field (e.g., Business Name -> Task.name).
    # These don't appear as "cf:" columns on the provider's schema, so look them
    # up directly from the CascadingFieldDef.
    for _norm_name, (owner_class, field_def) in cascade_registry.items():
        if owner_class is not model_class:
            continue
        # The source_field (e.g., "name") is the Task attribute, not a custom field.
        # The corresponding column name on the schema IS the source_field.
        if (
            field_def.source_field is not None
            and field_def.name not in mapping.values()
            and field_def.source_field in [c.name for c in schema.columns]
        ):
            mapping[field_def.source_field] = field_def.name

    return mapping


def _provider_for_field_map() -> dict[str, str]:
    """Build the shared provider lookup: asana_field_name -> provider entity type.

    Single derivation source for the cascade dependency graph. BOTH the
    warm-phase planner (:func:`cascade_warm_phases`) and the ordering
    guards (:func:`get_cascade_providers` and its consumers) derive from
    this map, so planner and gate can never disagree about who provides
    a cascade field.

    All imports are deferred to avoid circular deps.
    """
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.models.business.fields import get_cascading_field_registry

    entity_registry = get_registry()
    cascade_registry = get_cascading_field_registry()

    provider_for_field: dict[str, str] = {}
    for _norm_name, (owner_class, field_def) in cascade_registry.items():
        # Find the entity descriptor for this owner class
        for desc in entity_registry.all_descriptors():
            if desc.cascading_field_provider and desc.get_model_class() is owner_class:
                provider_for_field[field_def.name] = desc.name
                break
    return provider_for_field


def cascade_warm_phases() -> list[list[str]]:
    """Compute topological warm phases from the cascade dependency graph.

    Entities that provide cascade fields must warm before entities that
    consume them. Returns a list of phases (tiers); entities within a
    phase can be parallelized. Phases must execute sequentially.

    The dependency graph is derived from:
    - ``DataFrameSchema.get_cascade_columns()`` to find consumers
    - ``get_cascading_field_registry()`` to find providers

    Only FRAME-WARMABLE entities (``EntityDescriptor.warmable``) are
    scheduled. Frame-less providers (e.g., the HOLDER-category
    ``unit_holder``) never appear in any phase: their cascade data rides
    the unified task store via ancestor hydration during the consumer's
    own build, not a DataFrame warm. The pre-phase gate MUST therefore
    demand only frame-warmable providers — see
    :func:`get_frame_warm_providers` / :func:`assert_l2_pre_phase_gate`.

    Returns:
        List of phases, each a list of entity type names.
        E.g., ``[["business"], ["unit"], ["contact", "offer", ...]]``
    """
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    entity_registry = get_registry()
    provider_for_field = _provider_for_field_map()

    # Build dependency graph: entity_type -> set of entity types it depends on
    deps: dict[str, set[str]] = defaultdict(set)
    warmable_types: list[str] = []
    warmable_priority: dict[str, int] = {}

    schema_registry = SchemaRegistry.get_instance()

    for desc in entity_registry.warmable_entities():
        warmable_types.append(desc.name)
        warmable_priority[desc.name] = desc.warm_priority

        # Get schema for this entity
        try:
            schema = schema_registry.get_schema(desc.effective_schema_key)
        except Exception:  # noqa: BLE001
            continue

        # For each cascade column, add a dependency on its provider
        for _col_name, asana_field_name in schema.get_cascade_columns():
            provider = provider_for_field.get(asana_field_name)
            if provider and provider != desc.name:
                deps[desc.name].add(provider)

    # Topological sort (Kahn's algorithm) into phases
    remaining = set(warmable_types)
    phases: list[list[str]] = []

    while remaining:
        # Find entities with no unsatisfied dependencies
        ready = {e for e in remaining if not (deps.get(e, set()) & remaining)}
        if not ready:
            # Break cycles — should not happen with current data
            logger.warning(
                "cascade_topological_cycle_detected",
                extra={
                    "remaining_count": len(remaining),
                    "remaining_entities": sorted(remaining),
                    "phase_count": len(phases),
                },
            )
            ready = remaining.copy()

        # Sort within phase by warm_priority for determinism
        phase = sorted(ready, key=lambda e: warmable_priority.get(e, 99))
        phases.append(phase)
        remaining -= ready

    return phases


def cascade_warm_order() -> list[str]:
    """Flat cascade-aware warm order for sequential processing.

    Convenience wrapper around :func:`cascade_warm_phases` that flattens
    the phases into a single list. Use for Lambda warmer and CacheWarmer
    which process entities sequentially.

    Returns:
        Flat list of entity type names in cascade-safe order.
    """
    return [entity for phase in cascade_warm_phases() for entity in phase]


def get_cascade_providers(entity_type: str) -> set[str]:
    """Return ALL entity types that provide cascade fields to this entity.

    Builds the same dependency graph as :func:`cascade_warm_phases` (via
    the shared :func:`_provider_for_field_map`) but returns only the
    providers for a single entity type. The result includes FRAME-LESS
    providers (e.g., ``unit_holder``) whose data is satisfied by ancestor
    hydration in the unified task store, NOT by a DataFrame warm.

    Consumers:
    - L3 per-build guard (hierarchy-store probe): uses this UNFILTERED
      set — the store probe is exactly the satisfaction mechanism for
      frame-less providers.
    - L1/L2 frame-warm ordering gates: must NOT use this directly.
      They demand frame-warm completion, so they use
      :func:`get_frame_warm_providers` (else a frame-less provider
      becomes an unsatisfiable demand — the #192 wedge).

    All imports are deferred to avoid circular deps.

    Args:
        entity_type: Snake-case entity type name (e.g., "offer").

    Returns:
        Set of entity type names that provide cascade fields to
        *entity_type*. Empty set if the entity has no cascade deps.
    """
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.dataframes.models.registry import SchemaRegistry

    entity_registry = get_registry()
    provider_for_field = _provider_for_field_map()

    # Find this entity's schema and extract cascade deps
    entity_desc = entity_registry.get(entity_type)
    if entity_desc is None:
        return set()
    desc = entity_desc

    schema_registry = SchemaRegistry.get_instance()
    try:
        schema = schema_registry.get_schema(desc.effective_schema_key)
    except Exception:  # noqa: BLE001
        return set()

    providers: set[str] = set()
    for _col_name, asana_field_name in schema.get_cascade_columns():
        provider = provider_for_field.get(asana_field_name)
        if provider and provider != entity_type:
            providers.add(provider)

    return providers


def get_frame_warm_providers(entity_type: str) -> set[str]:
    """Cascade providers of *entity_type* that are FRAME-WARMABLE.

    Filters :func:`get_cascade_providers` through the SAME predicate the
    warm-phase planner uses to schedule work —
    ``EntityRegistry.warmable_entities()`` membership. By construction,
    every provider this function returns is schedulable by
    :func:`cascade_warm_phases`, so a gate demanding this set can always
    be satisfied by running the planner's phases in order.

    Frame-less providers (``warmable=False``, no DataFrame schema —
    e.g., the HOLDER-category ``unit_holder``) are excluded: their
    cascade data is consumed via the unified task store hydrated during
    the CONSUMER's own build (``warm_ancestors``), so demanding their
    frame-warm completion is structurally unsatisfiable.

    Args:
        entity_type: Snake-case entity type name (e.g., "offer").

    Returns:
        Subset of :func:`get_cascade_providers` restricted to
        frame-warmable entities.
    """
    from autom8_asana.core.entity_registry import get_registry

    providers = get_cascade_providers(entity_type)
    if not providers:
        return providers

    frame_warmable = {d.name for d in get_registry().warmable_entities()}
    return providers & frame_warmable


def assert_l2_pre_phase_gate(
    phase_idx: int,
    phase_entity_types: list[str],
    completed_entities: set[str],
) -> None:
    """L2 pre-phase gate: fail closed if a frame-warm provider is missing.

    Before a preload phase runs, every entity in the phase must have all
    of its FRAME-WARMABLE cascade providers already completed
    (frame-warmed in an earlier phase). A missing frame-warm provider
    means cascade fields would extract null (SCAR-005/006), so this
    raises :class:`WarmupOrderingError` — which is NEVER caught by
    BROAD-CATCH handlers.

    The demand set is :func:`get_frame_warm_providers` — the planner's
    own schedulability predicate — NOT the unfiltered
    :func:`get_cascade_providers`. Frame-less providers (e.g.,
    ``unit_holder``) are satisfied by ancestor hydration during the
    consumer's build and never appear in any phase, so demanding them
    here would wedge the preload permanently (the #192 defect).

    This function lives beside :func:`cascade_warm_phases` deliberately:
    planner and gate derive from the same module-local dependency graph
    and the same warmability predicate, so they cannot drift.

    Args:
        phase_idx: Index of the phase about to run (for diagnostics).
        phase_entity_types: Entity types scheduled in this phase.
        completed_entities: Entity types whose phases have completed.

    Raises:
        WarmupOrderingError: If any entity in the phase has a
            frame-warmable cascade provider not in *completed_entities*.
    """
    for entity_type in phase_entity_types:
        missing_providers = get_frame_warm_providers(entity_type) - completed_entities
        if missing_providers:
            raise WarmupOrderingError(
                f"L2 pre-phase gate: entity '{entity_type}' in phase "
                f"{phase_idx} requires frame-warm cascade providers "
                f"{missing_providers} which have not completed. "
                f"Completed so far: {completed_entities}."
            )


def validate_cascade_ordering() -> None:
    """Validate that warm_priority ordering matches cascade dependency graph.

    Called from lifespan.py during ECS startup and lambda_handlers during
    cold start. Raises ValueError if warm_priority conflicts with cascade
    dependencies.

    This is L1 of the three-layer defense-in-depth for the cascade
    warm-up ordering invariant (SCAR-005/006).

    The check verifies that for every warmable entity, all of its
    FRAME-WARMABLE cascade providers (:func:`get_frame_warm_providers` —
    the same predicate the planner and the L2 gate use) appear EARLIER
    in the warm_priority ordering. A violation means a misconfiguration
    that would cause null cascade fields. Frame-less providers are
    outside the frame-warm ordering by definition (their data rides the
    unified task store), so they carry no ordering constraint here.

    Raises:
        ValueError: If warm_priority ordering conflicts with cascade
            dependencies. This is a misconfiguration error, not a
            runtime failure (hence ValueError, not WarmupOrderingError).
    """
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()

    # Build warm_priority ordering
    warmable_order = [desc.name for desc in registry.warmable_entities()]
    warmable_index = {name: idx for idx, name in enumerate(warmable_order)}

    # Check each entity's frame-warm cascade providers appear earlier in
    # the order. get_frame_warm_providers filters via the same
    # warmable_entities() predicate that built warmable_index, so every
    # provider it returns is indexable (defensive .get for patched
    # registries in tests).
    violations: list[str] = []
    for entity_name in warmable_order:
        providers = get_frame_warm_providers(entity_name)
        entity_idx = warmable_index[entity_name]
        for provider in providers:
            provider_idx = warmable_index.get(provider)
            if provider_idx is None:
                continue
            if provider_idx >= entity_idx:
                violations.append(
                    f"{entity_name} (priority_idx={entity_idx}) warms BEFORE "
                    f"its cascade provider {provider} (priority_idx={provider_idx})"
                )

    if violations:
        raise ValueError(
            "CASCADE ORDERING MISCONFIGURATION (L1 startup check).\n"
            f"warm_priority order: {warmable_order}\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )
