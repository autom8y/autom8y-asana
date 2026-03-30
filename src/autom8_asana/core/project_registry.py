"""Central project registry -- single source of truth for all Asana project GIDs.

Per STAKEHOLDER-CONTEXT Section 10: All project GIDs centralized in one module.
Entity classes reference these values via PRIMARY_PROJECT_GID class attributes.
Lifecycle YAML references logical names resolved via get_project_gid().

Migration strategy: Entity classes retain their own PRIMARY_PROJECT_GID for now.
Parity tests verify that entity class values match registry values. Future sprints
will migrate entity classes to reference the registry directly.

Module: src/autom8_asana/core/project_registry.py
"""

from __future__ import annotations

# =============================================================================
# Entity Projects
# =============================================================================

# Business hierarchy root
BUSINESS_PROJECT = "1200653012566782"

# Unit entities and their holder
UNIT_PROJECT = "1201081073731555"
UNIT_HOLDER_PROJECT = "1204433992667196"

# Offer entities and their holder
OFFER_PROJECT = "1143843662099250"
OFFER_HOLDER_PROJECT = "1210679066066870"

# Contact entities and their holder
CONTACT_PROJECT = "1200775689604552"
CONTACT_HOLDER_PROJECT = "1201500116978260"

# AssetEdit entities and their holder
ASSET_EDIT_PROJECT = "1202204184560785"
ASSET_EDIT_HOLDER_PROJECT = "1203992664400125"

# Location entities (LocationHolder has no dedicated project)
LOCATION_PROJECT = "1200836133305610"

# Hours entities
HOURS_PROJECT = "1201614578074026"

# DNA holder
DNA_HOLDER_PROJECT = "1167650840134033"

# Reconciliation holder
RECONCILIATION_HOLDER_PROJECT = "1203404998225231"

# Videography holder
VIDEOGRAPHY_HOLDER_PROJECT = "1207984018149338"

# =============================================================================
# Pipeline Projects (from lifecycle_stages.yaml)
# =============================================================================

SALES_PIPELINE_PROJECT = "1200944186565610"
OUTREACH_PIPELINE_PROJECT = "1201753128450029"
ONBOARDING_PIPELINE_PROJECT = "1201319387632570"
IMPLEMENTATION_PIPELINE_PROJECT = "1201476141989746"
RETENTION_PIPELINE_PROJECT = "1201346565918814"
REACTIVATION_PIPELINE_PROJECT = "1201265144487549"
ACCOUNT_ERROR_PIPELINE_PROJECT = "1201684018234520"
EXPANSION_PIPELINE_PROJECT = "1201265144487557"
ACTIVATION_CONSULTATION_PROJECT = (
    "1209247943184021"  # month1 pipeline ("Activation Consultation")
)

# =============================================================================
# Lookup Tables
# =============================================================================

# Forward lookup: logical name -> GID
_REGISTRY: dict[str, str] = {
    # Entity projects
    "BUSINESS_PROJECT": BUSINESS_PROJECT,
    "UNIT_PROJECT": UNIT_PROJECT,
    "UNIT_HOLDER_PROJECT": UNIT_HOLDER_PROJECT,
    "OFFER_PROJECT": OFFER_PROJECT,
    "OFFER_HOLDER_PROJECT": OFFER_HOLDER_PROJECT,
    "CONTACT_PROJECT": CONTACT_PROJECT,
    "CONTACT_HOLDER_PROJECT": CONTACT_HOLDER_PROJECT,
    "ASSET_EDIT_PROJECT": ASSET_EDIT_PROJECT,
    "ASSET_EDIT_HOLDER_PROJECT": ASSET_EDIT_HOLDER_PROJECT,
    "LOCATION_PROJECT": LOCATION_PROJECT,
    "HOURS_PROJECT": HOURS_PROJECT,
    "DNA_HOLDER_PROJECT": DNA_HOLDER_PROJECT,
    "RECONCILIATION_HOLDER_PROJECT": RECONCILIATION_HOLDER_PROJECT,
    "VIDEOGRAPHY_HOLDER_PROJECT": VIDEOGRAPHY_HOLDER_PROJECT,
    # Pipeline projects
    "SALES_PIPELINE_PROJECT": SALES_PIPELINE_PROJECT,
    "OUTREACH_PIPELINE_PROJECT": OUTREACH_PIPELINE_PROJECT,
    "ONBOARDING_PIPELINE_PROJECT": ONBOARDING_PIPELINE_PROJECT,
    "IMPLEMENTATION_PIPELINE_PROJECT": IMPLEMENTATION_PIPELINE_PROJECT,
    "RETENTION_PIPELINE_PROJECT": RETENTION_PIPELINE_PROJECT,
    "REACTIVATION_PIPELINE_PROJECT": REACTIVATION_PIPELINE_PROJECT,
    "ACCOUNT_ERROR_PIPELINE_PROJECT": ACCOUNT_ERROR_PIPELINE_PROJECT,
    "EXPANSION_PIPELINE_PROJECT": EXPANSION_PIPELINE_PROJECT,
    "ACTIVATION_CONSULTATION_PROJECT": ACTIVATION_CONSULTATION_PROJECT,
}

# Reverse lookup: GID -> logical name
_REVERSE_REGISTRY: dict[str, str] = {gid: name for name, gid in _REGISTRY.items()}


def get_project_gid(logical_name: str) -> str:
    """Resolve a logical project name to its GID.

    Args:
        logical_name: Registry key (e.g. "BUSINESS_PROJECT", "SALES_PIPELINE_PROJECT").

    Returns:
        The Asana project GID string.

    Raises:
        KeyError: If the logical name is not registered.
    """
    try:
        return _REGISTRY[logical_name]
    except KeyError:
        raise KeyError(
            f"Unknown project logical name: {logical_name!r}. "
            f"Available names: {sorted(_REGISTRY.keys())}"
        ) from None


def get_project_name(gid: str) -> str:
    """Resolve a project GID to its logical name (reverse lookup).

    Useful for logging and diagnostics -- turns opaque GID strings into
    human-readable names.

    Args:
        gid: Asana project GID string.

    Returns:
        The logical name registered for this GID.

    Raises:
        KeyError: If the GID is not registered.
    """
    try:
        return _REVERSE_REGISTRY[gid]
    except KeyError:
        raise KeyError(
            f"Unknown project GID: {gid!r}. "
            f"This GID is not registered in the project registry."
        ) from None


def all_project_gids() -> frozenset[str]:
    """Return all registered project GIDs.

    Returns:
        Frozen set of all GID strings in the registry.
    """
    return frozenset(_REGISTRY.values())


def all_pipeline_project_gids() -> list[str]:
    """Return all pipeline project GIDs in declaration order.

    Returns:
        List of pipeline project GID strings.
    """
    return [
        SALES_PIPELINE_PROJECT,
        OUTREACH_PIPELINE_PROJECT,
        ONBOARDING_PIPELINE_PROJECT,
        IMPLEMENTATION_PIPELINE_PROJECT,
        RETENTION_PIPELINE_PROJECT,
        REACTIVATION_PIPELINE_PROJECT,
        ACCOUNT_ERROR_PIPELINE_PROJECT,
        EXPANSION_PIPELINE_PROJECT,
        ACTIVATION_CONSULTATION_PROJECT,
    ]


def all_entity_project_gids() -> list[str]:
    """Return all entity (non-pipeline) project GIDs.

    Returns:
        List of entity project GID strings.
    """
    pipeline_gids = set(all_pipeline_project_gids())
    return [gid for gid in _REGISTRY.values() if gid not in pipeline_gids]
