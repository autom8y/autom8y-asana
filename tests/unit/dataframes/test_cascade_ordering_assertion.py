"""Interim cascade ordering assertion test (M-04).

Validates that the warm_priority ordering in warmable_entities() respects
the cascade dependency graph: every entity that CONSUMES cascade fields
must warm AFTER the entity that PROVIDES those fields.

This is the safety net for regression risk 1 (SCAR-005/006) until the
full WarmupOrderingError guard ships in WS-4a.
"""

from __future__ import annotations

from collections import defaultdict


def _build_cascade_deps() -> dict[str, set[str]]:
    """Build cascade dependency graph: consumer -> set of providers.

    Mirrors the dependency computation in cascade_warm_phases() but
    returns the raw graph for assertion purposes.
    """
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.models.business.fields import get_cascading_field_registry

    entity_registry = get_registry()
    cascade_registry = get_cascading_field_registry()

    # Build provider lookup: asana_field_name -> provider_entity_type
    provider_for_field: dict[str, str] = {}
    for _norm_name, (owner_class, field_def) in cascade_registry.items():
        for desc in entity_registry.all_descriptors():
            if desc.cascading_field_provider and desc.get_model_class() is owner_class:
                provider_for_field[field_def.name] = desc.name
                break

    # Build dependency graph
    deps: dict[str, set[str]] = defaultdict(set)
    schema_registry = SchemaRegistry.get_instance()

    for desc in entity_registry.warmable_entities():
        try:
            schema = schema_registry.get_schema(desc.effective_schema_key)
        except Exception:  # noqa: BLE001
            continue
        for _col_name, asana_field_name in schema.get_cascade_columns():
            provider = provider_for_field.get(asana_field_name)
            if provider and provider != desc.name:
                deps[desc.name].add(provider)

    return deps


def test_warmable_entities_same_set_as_cascade_warm_phases() -> None:
    """M-04a: warmable_entities() and cascade_warm_phases() cover the same entities."""
    from autom8_asana.core.entity_registry import get_registry
    from autom8_asana.dataframes.cascade_utils import cascade_warm_phases

    registry = get_registry()
    warmable_set = {desc.name for desc in registry.warmable_entities()}
    topo_set = {entity for phase in cascade_warm_phases() for entity in phase}

    assert warmable_set == topo_set, (
        f"Entity set mismatch. "
        f"Only in warmable: {warmable_set - topo_set}. "
        f"Only in topo: {topo_set - warmable_set}."
    )


def test_cascade_providers_warm_before_consumers() -> None:
    """M-04b: No cascade consumer warms before its provider (SCAR-005/006 invariant).

    For every entity that consumes cascade fields, its cascade provider(s)
    must appear EARLIER in the warm_priority ordering. Violating this
    invariant causes null cascade fields at extraction time.

    References:
        - SCAR-005: Cascade Field Null Rate (30% null office_phone)
        - SCAR-006: Cascade Hierarchy Warming Gaps
        - entity_registry.py:293 (warmable_entities docstring)
    """
    from autom8_asana.core.entity_registry import get_registry

    registry = get_registry()
    warmable_order = [desc.name for desc in registry.warmable_entities()]
    warmable_index = {name: idx for idx, name in enumerate(warmable_order)}

    deps = _build_cascade_deps()
    violations: list[str] = []

    for consumer, providers in deps.items():
        if consumer not in warmable_index:
            continue
        consumer_idx = warmable_index[consumer]
        for provider in providers:
            if provider not in warmable_index:
                continue
            provider_idx = warmable_index[provider]
            if provider_idx >= consumer_idx:
                violations.append(
                    f"{consumer} (idx={consumer_idx}) warms BEFORE "
                    f"its cascade provider {provider} (idx={provider_idx})"
                )

    assert not violations, (
        f"CASCADE ORDERING VIOLATION — regression risk 1 (SCAR-005/006).\n"
        f"warm_priority order: {warmable_order}\n"
        f"Cascade deps: {dict(deps)}\n"
        f"Violations:\n" + "\n".join(f"  - {v}" for v in violations)
    )


def test_cascade_dependency_graph_is_nonempty() -> None:
    """M-04c: The cascade dependency graph has entries (sanity check).

    If the graph is empty, this test suite provides no protection.
    At minimum, business -> unit and business -> (offer/contact) cascade
    dependencies must exist.
    """
    deps = _build_cascade_deps()

    assert len(deps) > 0, "Cascade dependency graph is empty — no protection"
    # At minimum, unit depends on business for cascade fields
    assert "unit" in deps, "unit should depend on business for cascade fields"
    assert "business" in deps.get("unit", set()), "unit's cascade deps should include business"
