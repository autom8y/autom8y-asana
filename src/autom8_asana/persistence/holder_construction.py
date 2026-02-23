"""Holder entity construction and detection for write-path auto-creation.

Per TDD-GAP-01 Section 3.3, 3.4, 5: Pure construction function and async
detection function for the ENSURE_HOLDERS pipeline phase.

This module provides:
- HOLDER_REGISTRY: Registry mapping holder_key to holder class (9 entries).
- register_holder(): Registration function called by each Holder module.
- construct_holder(): Pure function building typed holder entities.
- detect_existing_holders(): Async function checking Asana API for existing holders.

The detection function reuses identify_holder_type from the detection facade
to guarantee consistency between read and write paths (FR-001).

The construction function uses HOLDER_KEY_MAP metadata to determine:
- Holder class (ContactHolder, UnitHolder, etc.)
- Name (conventional name from the tuple, no emoji in name)
- Parent reference (NameGid with real or temp GID)
- Project assignment (PRIMARY_PROJECT_GID where available)

Per R-009 (REM-ASANA-ARCH WS-DFEX): Each Holder module self-registers via
register_holder() at module level, following the register_reset() pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.models.common import NameGid

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource

logger = get_logger(__name__)


# Public registry: populated by each Holder module at import time.
# Each Holder file calls register_holder(key, cls) at module level.
HOLDER_REGISTRY: dict[str, type] = {}


def register_holder(holder_key: str, holder_class: type) -> None:
    """Register a Holder class for the given holder_key.

    Called at module level in each Holder file so that importing the file
    automatically populates HOLDER_REGISTRY. Duplicates are silently ignored.

    Args:
        holder_key: Canonical key (e.g., "contact_holder", "unit_holder").
        holder_class: The Holder class to register.
    """
    if holder_key not in HOLDER_REGISTRY:
        HOLDER_REGISTRY[holder_key] = holder_class


def reset_holder_registry() -> None:
    """Reset HOLDER_REGISTRY to empty state.

    For test isolation. Registered with SystemContext.reset_all()
    so tests can call SystemContext.reset_all() and get a clean slate.

    Note: After reset, Holder modules have already been imported and their
    module-level register_holder() calls have run. The registry is rebuilt
    lazily on next get_holder_class_map() call by re-importing the Holder
    modules (which are cached in sys.modules and re-run their side effects
    via _ensure_registered() on the Holder base class, or here via a
    re-population step).
    """
    HOLDER_REGISTRY.clear()
    # Re-populate from modules already in sys.modules
    _repopulate_from_imported_modules()


def _repopulate_from_imported_modules() -> None:
    """Repopulate HOLDER_REGISTRY from already-imported Holder modules.

    Called after reset_holder_registry() to restore the registry without
    re-importing modules (which would be a no-op since Python caches imports).
    Uses deferred imports to trigger module-level register_holder() side effects,
    which are idempotent (duplicates are ignored).
    """
    # Import the Holder files; their module-level register_holder() calls
    # will re-populate HOLDER_REGISTRY. Since modules are cached in
    # sys.modules, Python re-executes only if the module was cleared.
    # We force re-registration via direct import of each Holder class.
    from autom8_asana.models.business.business import (  # noqa: F401
        AssetEditHolder,
        DNAHolder,
        ReconciliationHolder,
        VideographyHolder,
    )
    from autom8_asana.models.business.contact import ContactHolder  # noqa: F401
    from autom8_asana.models.business.location import LocationHolder  # noqa: F401
    from autom8_asana.models.business.offer import OfferHolder  # noqa: F401
    from autom8_asana.models.business.process import ProcessHolder  # noqa: F401
    from autom8_asana.models.business.unit import UnitHolder  # noqa: F401

    # Explicitly register in case module caching prevented side-effect re-runs
    register_holder("contact_holder", ContactHolder)
    register_holder("unit_holder", UnitHolder)
    register_holder("location_holder", LocationHolder)
    register_holder("dna_holder", DNAHolder)
    register_holder("reconciliation_holder", ReconciliationHolder)
    register_holder("asset_edit_holder", AssetEditHolder)
    register_holder("videography_holder", VideographyHolder)
    register_holder("offer_holder", OfferHolder)
    register_holder("process_holder", ProcessHolder)


def get_holder_class_map() -> dict[str, type]:
    """Get the holder class map from the registry.

    Lazily populates the registry if empty (e.g., on first call or
    after reset_holder_registry()).

    Returns:
        Dict mapping holder_key to holder class (9 entries).
        Populated by each Holder module's register_holder() call at import time.
    """
    if not HOLDER_REGISTRY:
        _repopulate_from_imported_modules()
    return HOLDER_REGISTRY


# Self-register reset function with SystemContext for test isolation.
from autom8_asana.core.system_context import register_reset  # noqa: E402

register_reset(reset_holder_registry)


def construct_holder(
    holder_key: str,
    holder_key_map: dict[str, tuple[str, str]],
    parent_entity: AsanaResource,
) -> AsanaResource:
    """Construct a typed holder entity for a given holder_key.

    Per TDD-GAP-01 Section 5.1: Build a typed holder entity programmatically.

    Uses HOLDER_KEY_MAP metadata to determine:
    - Holder class (ContactHolder, UnitHolder, etc.)
    - Name (from the tuple: e.g., "Contacts", "Business Units")
    - Parent reference (set to parent_entity via NameGid)

    The holder is created with a temp GID (Option A from TDD Section 4.4) so
    that the pipeline's GID resolution chain works correctly.

    Per TDD Section 5.3: Project assignment uses PRIMARY_PROJECT_GID where
    available. Holders with PRIMARY_PROJECT_GID = None get no projects.

    Args:
        holder_key: Key from HOLDER_KEY_MAP (e.g., "contact_holder").
        holder_key_map: The HOLDER_KEY_MAP dict from the parent entity.
        parent_entity: The Business or Unit that owns this holder.

    Returns:
        A typed holder entity with:
        - gid = temp_{id(holder)} (explicit temp GID for pipeline resolution)
        - name = conventional name from HOLDER_KEY_MAP
        - parent = NameGid with parent's real or temp GID
        - resource_type = "task"
        - projects = [NameGid(gid=PRIMARY_PROJECT_GID)] if available

    Raises:
        KeyError: If holder_key is not in holder_key_map or HOLDER_CLASS_MAP.
    """
    class_map = get_holder_class_map()

    if holder_key not in class_map:
        raise KeyError(f"Unknown holder type: {holder_key}")

    holder_class = class_map[holder_key]
    conventional_name, _emoji = holder_key_map[holder_key]

    # Construct holder with empty GID (Pydantic requires gid field)
    holder: AsanaResource = holder_class(
        gid="",
        name=conventional_name,
        resource_type="task",
    )

    # Assign explicit temp GID for pipeline resolution (Option A)
    object.__setattr__(holder, "gid", f"temp_{id(holder)}")

    # Set parent reference for dependency graph
    parent_gid = parent_entity.gid
    if parent_gid and not parent_gid.startswith("temp_"):
        # Parent has real GID
        object.__setattr__(holder, "parent", NameGid(gid=parent_gid))
    else:
        # Parent also new -- use temp_{id(parent)} for payload serialization
        object.__setattr__(holder, "parent", NameGid(gid=f"temp_{id(parent_entity)}"))

    # Wire holder -> parent business reference
    from autom8_asana.models.business.business import Business

    if isinstance(parent_entity, Business):
        object.__setattr__(holder, "_business", parent_entity)
    else:
        # For Unit-level holders, propagate _business from parent
        object.__setattr__(
            holder, "_business", getattr(parent_entity, "_business", None)
        )

    # Project assignment (FR-008, TDD Section 5.3)
    primary_project_gid = getattr(holder_class, "PRIMARY_PROJECT_GID", None)
    if primary_project_gid is not None:
        object.__setattr__(holder, "projects", [NameGid(gid=primary_project_gid)])

    logger.info(
        "holder_construction_complete",
        parent_gid=parent_gid,
        holder_type=holder_key,
        temp_gid=holder.gid,
        holder_name=conventional_name,
        has_project=primary_project_gid is not None,
    )

    return holder


async def detect_existing_holders(
    client: AsanaClient,
    parent_gid: str,
    holder_key_map: dict[str, tuple[str, str]],
) -> dict[str, AsanaResource]:
    """Detect which holders already exist as subtasks of parent.

    Per TDD-GAP-01 Section 3.4: Calls the subtasks API once per parent,
    then uses identify_holder_type() (same logic as the read path) to
    match each subtask.

    Args:
        client: AsanaClient for subtasks_async call.
        parent_gid: GID of the parent entity (Business or Unit).
        holder_key_map: The HOLDER_KEY_MAP to match against.

    Returns:
        Dict of holder_key -> typed holder entity for existing holders.
        Missing holder types are absent from the dict.
    """
    from autom8_asana.models.business.detection import identify_holder_type

    logger.info(
        "holder_detection_start",
        parent_gid=parent_gid,
    )

    # Fetch subtasks once per parent
    subtasks = await client.tasks.subtasks_async(
        parent_gid, include_detection_fields=True
    ).collect()

    existing: dict[str, Any] = {}

    for subtask in subtasks:
        holder_key = identify_holder_type(subtask, holder_key_map, filter_to_map=True)
        if holder_key:
            existing[holder_key] = subtask
            logger.info(
                "holder_detected_existing",
                parent_gid=parent_gid,
                holder_type=holder_key,
                holder_gid=subtask.gid,
            )

    existing_count = len(existing)
    missing_count = len(holder_key_map) - existing_count

    logger.info(
        "holder_detection_complete",
        parent_gid=parent_gid,
        existing=existing_count,
        missing=missing_count,
    )

    return existing
