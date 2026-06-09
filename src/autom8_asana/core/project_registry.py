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
ACTIVATION_CONSULTATION_PROJECT = "1209247943184021"  # month1 pipeline ("Activation Consultation")

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
            f"Unknown project GID: {gid!r}. This GID is not registered in the project registry."
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


# Body-parameterized entity arms the scheduled consumer `refresh_project_frames`
# bulk run hits per registered project. The receiver serves these cold
# (warmable=False, body_parameterized=True per entity_registry.py:884-940), so
# warming them ahead of the consumer batch moves the burst off the receiver's
# ALB path (TD-005).
BULK_PREMATERIALIZATION_ARMS: tuple[str, ...] = ("project", "section")

# =============================================================================
# Consumer Warm Set (ADR-3, WS-2 §3.1) -- DERIVED FROM THE CONSUMER, NOT FROM
# THE DOMAIN REGISTRY ABOVE.
# =============================================================================
#
# The scheduled consumer `refresh_project_frames._gather_project_classes()`
# (autom8/apis/asana_api/objects/project/refresh_frames.py:10-18) enumerates
# EVERY `Project` subclass in `apis.asana_api.objects.project.models` and calls
# `proj.get_df(sections="ALL")` on each. That is the receiver's true cold-burst
# width. As of 2026-06-02 the consumer yields 34 distinct GID-bearing subclasses
# (the two abstract bases `ProcessProject`/`IsolatedPlayProject` carry no GID and
# are excluded -- they raise on bare instantiation and the consumer swallows it).
#
# The 23-entry `_REGISTRY` above is the receiver's DOMAIN model (resolution +
# PRIMARY_PROJECT_GID parity) and is a strict SUBSET of the consumer's 34
# (set-diff verified == the 11 GIDs in tiers 2/3 below, with 0 receiver-only
# GIDs). It is the WRONG denominator for warming: it omits 11 consumer-queried
# GIDs that the receiver then 503s cold under bulk fan-out (CF-3). The prior
# docstring claimed the 23 keys were "the only width-driving keys the receiver
# serves cold" -- FALSE against consumer source (the consumer hits 34, not 23).
#
# This warm set MUST equal the consumer subclass set (set-diff == 0); the re-gate
# acceptance (VG-004 static-superset-of-live) verifies it against a LIVE
# `refresh_frames` enumeration. It is kept SEPARATE from `_REGISTRY` so adding a
# warm target does NOT widen domain resolution (`get_project_gid`,
# `all_entity_project_gids`, parity) -- a pure-additive warm-path change with no
# resolution-behavior change for the existing 23 (ADR-3 §3.1 one-way-door note).
#
# ORDER IS HEAVIEST-FIRST (CF-2 fix, ADR-3 §3.2(a)). The warmer processes this
# list head-to-tail and, on a partial cycle, checkpoints the *tail*; declaration
# order previously warmed the heavy pipeline/holder GIDs LAST and amputated them
# FIRST. Heaviest-first means a partial warm leaves the EXPENSIVE-to-cold GIDs
# warmed and defers only the cheap tail to the self-invoke continuation. The
# tiers are a documented build-cost heuristic (no persisted row-count metadatum
# exists in the registry); refine the ordering if telemetry contradicts it.
_CONSUMER_WARM_SET_TIER_1_HEAVY: tuple[str, ...] = (
    "1167650840134033",  # BackendClientSuccessDna (DNA holder ~30k rows -- heaviest, OOM driver)
    "1200944186565610",  # Sales pipeline
    "1201753128450029",  # Outreach pipeline
    "1201319387632570",  # Onboarding pipeline
    "1201476141989746",  # Implementation pipeline
    "1201346565918814",  # Retention pipeline
    "1200653012566782",  # Businesses (root hierarchy)
    "1201081073731555",  # BusinessUnits
    "1143843662099250",  # BusinessOffers
    "1200775689604552",  # Contacts
)
_CONSUMER_WARM_SET_TIER_2_MID: tuple[str, ...] = (
    "1201265144487549",  # Reactivation pipeline
    "1201265144487557",  # Expansion pipeline
    "1201684018234520",  # AccountError pipeline
    "1201532776033312",  # Consultation pipeline (registry-absent: +1 of 11)
    "1209247943184017",  # PracticeOfTheWeek pipeline (registry-absent: +2 of 11)
    "1209247943184021",  # ActivationConsultation pipeline
    "1206176773330155",  # VideographerSourcing pipeline (registry-absent: +3 of 11)
    "1204433992667196",  # Units (holder)
    "1210679066066870",  # OfferHolders
    "1201500116978260",  # ContactHolder
    "1203992664400125",  # AssetEditHolder
    "1202204184560785",  # PaidContent
    "1200836133305610",  # Locations
    "1201614578074026",  # Hours
    "1203404998225231",  # Reconciliations
    "1207984018149338",  # VideographyServices
    "1201627461398630",  # Commission (registry-absent: +4 of 11; build-gap GID, 1480 rows -- ADR-2)
)
_CONSUMER_WARM_SET_TIER_3_LIGHT: tuple[str, ...] = (
    "1208231632857419",  # OptimizationNotifications (registry-absent: +5 of 11)
    "1205526136594283",  # QuestionOnPerformance (registry-absent: +6 of 11; isolated play)
    "1207507299545000",  # BackendOnboardABusiness (registry-absent: +7 of 11; isolated play)
    "1209442849265632",  # CalendarIntegrations (registry-absent: +8 of 11; isolated play)
    "1209442727608287",  # AccessProcessing (registry-absent: +9 of 11)
    "1206330409791366",  # PauseABusinessUnit (registry-absent: +10 of 11; interrupted build / honest-empty -- ADR-2)
    "1208848470341588",  # CustomerHealth (registry-absent: +11 of 11; honest-empty -- ADR-1)
)

# The authoritative warm set: heaviest-first, consumer-derived, set-diff(consumer)==0.
CONSUMER_WARM_SET_GIDS: tuple[str, ...] = (
    _CONSUMER_WARM_SET_TIER_1_HEAVY
    + _CONSUMER_WARM_SET_TIER_2_MID
    + _CONSUMER_WARM_SET_TIER_3_LIGHT
)


def consumer_warm_set_gids() -> tuple[str, ...]:
    """Return the consumer-derived warm-set GIDs in heaviest-first order (ADR-3).

    This is the receiver's true cold-burst width: the GID of every ``Project``
    subclass the scheduled consumer ``refresh_project_frames`` queries. It is a
    SUPERSET of the 23-entry domain ``_REGISTRY`` (the 11 extra GIDs are
    consumer-queried projects the receiver does not model as named domain
    projects but still must warm). Order is heaviest-first so a partial warm
    cycle defers only the cheap tail (CF-2).

    Returns:
        Tuple of project GID strings, heaviest-first.
    """
    return CONSUMER_WARM_SET_GIDS


def bulk_prematerialization_keys(
    arms: tuple[str, ...] = BULK_PREMATERIALIZATION_ARMS,
) -> list[tuple[str, str]]:
    """Enumerate the (project_gid, entity_type) keys to pre-materialize (TD-005).

    Produces the full consumer-derived warm set for the scheduled consumer bulk
    run: every GID the consumer ``refresh_project_frames`` queries
    (:func:`consumer_warm_set_gids`, 34 GIDs as of 2026-06-02) crossed with each
    body-parameterized arm. With the two-arm default this enumerates
    34 x 2 = 68 keys.

    The set is the CONSUMER's subclass set, NOT the 23-entry domain ``_REGISTRY``
    (ADR-3 §3.1, CF-3): the registry is a strict subset and omits 11
    consumer-queried GIDs that the receiver would otherwise 503 cold under bulk
    fan-out. Reconciliation keeps the warm denominator consumer-aligned by
    construction.

    Order is deterministic AND heaviest-first: GIDs in
    :func:`consumer_warm_set_gids` order (descending build-cost), arms in the
    given order. Determinism matters because the handler's checkpoint/self-invoke
    machinery resumes a partially-processed list by set-difference, so a stable
    ordering keeps "completed" vs "pending" coherent across self-invokes; the
    heaviest-first ordering means a partial warm leaves the expensive GIDs warmed
    and defers only the cheap tail (CF-2 fix, ADR-3 §3.2(a)).

    Args:
        arms: Body-parameterized entity types to enumerate per GID. Defaults to
            ``("project", "section")`` -- the arms the consumer bulk run hits.

    Returns:
        List of ``(project_gid, entity_type)`` tuples, length ``len(GIDs) * len(arms)``.
    """
    gids = consumer_warm_set_gids()
    return [(gid, arm) for gid in gids for arm in arms]


# =============================================================================
# Section-Only Warm Lane (ADR §B — ≤10-min SECTION freshness lane)
# =============================================================================
#
# The SECTION entity_type carries a freshness contract of 576s (~10 min, i.e.
# SECTION_DF_REFRESH_HOURS=0.16 × 3600 per caching.py:39). The bulk warmer's
# 30-min tick yields an inter-warm interval of ~46 min for the heaviest GID —
# far beyond the 576s contract. Neither the bulk sweep nor the held fast lane
# (#97, 2-GID only at 15-min) meets the 576s/600s contract for all 34 GIDs.
#
# A dedicated SECTION-arm-only lane over the full 34-GID warm set, running at
# ≤10-min cadence, is the only design that satisfies the contract across the
# full width (ADR §B.2). The key shape is identical to bulk_prematerialization_keys
# but arm-restricted to ("section",): 34 GIDs × 1 arm = 34 keys.
#
# The same generic _prematerialize_bulk_set_async coroutine drives the section
# lane via a third key_source injection (no new build/merge/coverage code
# required). Lane isolation is achieved at the edges: a disjoint
# CACHE_WARMER_CHECKPOINT_PREFIX (set per-Lambda in TF, following #96) gives
# the section lane its own latest.json, plus a dedicated reserved_concurrency
# pool (ADR §B.3.a) disjoint from the bulk warmer's ReservedConcurrentExecutions=1.
#
# Backstop invariant: every section-lane key is a subset of the bulk sweep's
# section arm. The bulk 30-min sweep remains the backstop: if the section lane
# stalls, every section key is still covered by the bulk sweep.


def section_only_prematerialization_keys() -> list[tuple[str, str]]:
    """Enumerate the section-arm-only (project_gid, "section") keys (ADR §B lane).

    Produces the full consumer-derived warm set restricted to the ``"section"``
    arm: every GID in :func:`consumer_warm_set_gids` (34 GIDs as of 2026-06-02)
    paired with ``"section"`` — 34 keys total. This is the section lane's own
    coverage denominator (distinct from the bulk 68-key and fast 4-key
    denominators).

    Key shape is identical to :func:`bulk_prematerialization_keys` (both yield
    ``(gid, entity_type)`` tuples), so the identical
    ``_prematerialize_bulk_set_async`` coroutine drives the section lane without
    modification — only the ``key_source`` callable and the
    ``prematerialize_section_set`` event flag differ.

    Order is heaviest-first (matching :func:`consumer_warm_set_gids` declaration
    order), so a partial section sweep under checkpoint/self-invoke defers only
    the cheap-tail GIDs while the expensive ones are already warm.

    Backstop invariant: every (gid, "section") key produced here is also a
    member of the full bulk sweep's section arm — confirmed at call time by
    module-load assertion so a GID drift is caught at import, not in prod.

    Returns:
        List of ``(project_gid, "section")`` tuples, length
        ``len(consumer_warm_set_gids())`` (34 with the current warm set).
    """
    return [(gid, "section") for gid in consumer_warm_set_gids()]


# Structural backstop invariant: the section lane keys are a strict subset of
# the bulk sweep's section arm, so the 30-min bulk sweep remains the backstop
# for every section key even if the section lane is disabled or stalled.
# Asserted at module load so a divergence between the warm set and the bulk
# sweep is caught at import (mirroring the fast-lane guard pattern).
_SECTION_LANE_KEYS_AT_LOAD: frozenset[tuple[str, str]] = frozenset(
    section_only_prematerialization_keys()
)
_BULK_SECTION_KEYS_AT_LOAD: frozenset[tuple[str, str]] = frozenset(
    bulk_prematerialization_keys(arms=("section",))
)
assert _SECTION_LANE_KEYS_AT_LOAD <= _BULK_SECTION_KEYS_AT_LOAD, (
    "section_only_prematerialization_keys produced keys not in bulk section arm — "
    "consumer_warm_set_gids and bulk_prematerialization_keys have diverged; "
    f"orphaned section keys: {sorted(_SECTION_LANE_KEYS_AT_LOAD - _BULK_SECTION_KEYS_AT_LOAD)}"
)
