"""HolderEnsurer - orchestrates detection, construction, and tracking of holders.

Per TDD-GAP-01 Section 3.2: Stateless collaborator used by SavePipeline during
the ENSURE_HOLDERS phase. Instantiated per commit cycle with needed collaborators.

Per PRD SC-001: When a parent entity (Business, Unit) with HOLDER_KEY_MAP is in
the dirty list, ALL missing holders are ensured to exist. This guarantees the
holder hierarchy is complete in Asana for any saved parent entity.

Per TDD-GAP-01 Sprint 2 (SC-006, SC-007): Multi-level holder creation supports
the full 5-level chain: Business -> UnitHolder -> Unit -> OfferHolder -> Offer.
The ensure phase runs in waves to handle cascading holder creation when both
Business-level and Unit-level holders are needed in a single commit.

The ensurer is the integration point between:
- holder_construction.py (detect + construct)
- ChangeTracker (track new holders)
- HolderConcurrencyManager (prevent duplicate creation)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.persistence.holder_construction import (
    construct_holder,
    detect_existing_holders,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient
    from autom8_asana.models.base import AsanaResource
    from autom8_asana.persistence.holder_concurrency import HolderConcurrencyManager
    from autom8_asana.persistence.tracker import ChangeTracker

logger = get_logger(__name__)


# Map holder_key -> child collection attribute name
_HOLDER_CHILDREN_ATTR: dict[str, str] = {
    "contact_holder": "_contacts",
    "unit_holder": "_units",
    "location_holder": "_locations",
    "dna_holder": "_children",
    "reconciliation_holder": "_children",
    "asset_edit_holder": "_asset_edits",
    "videography_holder": "_children",
    "offer_holder": "_offers",
    "process_holder": "_processes",
}


class HolderEnsurer:
    """Detects missing holders and constructs them for tracked entities.

    Per TDD-GAP-01 Section 3.2: Stateless -- instantiated per commit cycle
    with the needed collaborators.

    Example:
        ensurer = HolderEnsurer(client, tracker, concurrency)
        combined = await ensurer.ensure_holders_for_entities(dirty_entities)
        # combined includes original dirty + newly created holders
    """

    def __init__(
        self,
        client: AsanaClient,
        tracker: ChangeTracker,
        concurrency: HolderConcurrencyManager,
        log: Any | None = None,
    ) -> None:
        """Initialize with required collaborators.

        Args:
            client: AsanaClient for subtasks API call in detection.
            tracker: ChangeTracker for registering new holders.
            concurrency: HolderConcurrencyManager for lock coordination.
            log: Optional structured logger.
        """
        self._client = client
        self._tracker = tracker
        self._concurrency = concurrency
        self._log = log

    async def ensure_holders_for_entities(
        self,
        dirty_entities: list[AsanaResource],
    ) -> list[AsanaResource]:
        """Detect and construct missing holders for all dirty entities.

        Per TDD-GAP-01 Section 3.2 Algorithm, extended for Sprint 2 multi-level:

        Runs in **waves** to support the full 5-level chain:
        Business -> UnitHolder -> Unit -> OfferHolder -> Offer

        Wave 1 processes all parents with HOLDER_KEY_MAP in the original dirty
        list (Business and Unit entities). Wave 2 checks if any newly created
        holders introduced new parent entities (Units from UnitHolder children)
        that also need their own holders. Waves repeat until no new parents
        are discovered (typically 1-2 waves).

        Per-wave algorithm:
        1. Collect unique parent entities that have HOLDER_KEY_MAP.
        2. For each parent, determine which holder types are missing.
        3. For each needed holder type:
           a. Acquire asyncio.Lock for (parent_gid, holder_type).
           b. Check if holder already tracked in session.
           c. If not, call detect_existing_holders() to check Asana API.
           d. If not found in Asana, call construct_holder() to build.
           e. Track the holder (new or existing) via ChangeTracker.
           f. Wire parent reference on children.
           g. Release lock.
        4. Collect any new parent entities from children wired to new holders.
        5. If new parents found, repeat from step 1 with the new parents only.

        Args:
            dirty_entities: Entities with pending changes from the tracker.

        Returns:
            Combined list: original dirty_entities + newly created holders.
        """
        if not dirty_entities:
            return dirty_entities

        all_new_holders: list[AsanaResource] = []
        # Track which parent entity ids we have already processed to avoid re-processing
        processed_parent_ids: set[int] = set()
        # The full combined entity list grows as waves add holders
        combined_entities = list(dirty_entities)

        # Maximum waves to prevent infinite loops (Business + Unit = 2 levels)
        max_waves = 3
        wave = 0

        while wave < max_waves:
            wave += 1

            # Collect parents with HOLDER_KEY_MAP that haven't been processed yet
            parents_with_holders: dict[int, AsanaResource] = {}
            for entity in combined_entities:
                entity_id = id(entity)
                if entity_id in processed_parent_ids:
                    continue
                holder_key_map = getattr(entity, "HOLDER_KEY_MAP", None)
                if holder_key_map:
                    parents_with_holders[entity_id] = entity

            if not parents_with_holders:
                break

            logger.info(
                "holder_ensure_wave_start",
                wave=wave,
                parent_count=len(parents_with_holders),
            )

            # Process each parent in this wave
            wave_new_holders: list[AsanaResource] = []
            dirty_set = set(id(e) for e in combined_entities)

            for parent in parents_with_holders.values():
                processed_parent_ids.add(id(parent))
                new_holders_for_parent = await self._ensure_holders_for_parent(
                    parent=parent,
                    dirty_set=dirty_set,
                    dirty_entities=combined_entities,
                )
                wave_new_holders.extend(new_holders_for_parent)

            if not wave_new_holders:
                break

            all_new_holders.extend(wave_new_holders)
            combined_entities.extend(wave_new_holders)

            logger.info(
                "holder_ensure_wave_complete",
                wave=wave,
                new_holders=len(wave_new_holders),
            )

        return dirty_entities + all_new_holders

    async def _ensure_holders_for_parent(
        self,
        parent: AsanaResource,
        dirty_set: set[int],
        dirty_entities: list[AsanaResource],
    ) -> list[AsanaResource]:
        """Ensure all needed holders exist for a single parent entity.

        Per TDD-GAP-01 Section 3.2: Extracted from ensure_holders_for_entities
        to support wave-based multi-level processing.

        Args:
            parent: Entity with HOLDER_KEY_MAP (Business or Unit).
            dirty_set: Set of id() values for all current dirty entities.
            dirty_entities: All dirty entities (for child wiring).

        Returns:
            List of newly constructed holders for this parent.
        """
        holder_key_map = parent.HOLDER_KEY_MAP  # type: ignore[attr-defined]
        parent_gid = parent.gid or f"temp_{id(parent)}"

        # Determine which holder types are missing
        needed_holder_keys = self._find_needed_holders(
            parent, holder_key_map, dirty_set
        )

        if not needed_holder_keys:
            return []

        # Detect existing holders from Asana (only if parent has real GID)
        existing_holders: dict[str, AsanaResource] = {}
        if parent.gid and not parent.gid.startswith("temp_"):
            try:
                existing_holders = await detect_existing_holders(
                    self._client, parent.gid, holder_key_map
                )
            except Exception:
                # Per TDD Section 9.1: If detection fails, proceed without
                # detection -- create the holder. Worst case: duplicate.
                logger.warning(
                    "holder_detection_failed",
                    parent_gid=parent_gid,
                    exc_info=True,
                )

        # Ensure each needed holder type
        new_holders: list[AsanaResource] = []

        for holder_key in needed_holder_keys:
            lock = self._concurrency.get_lock(parent_gid, holder_key)

            async with lock:
                logger.debug(
                    "holder_lock_acquired",
                    parent_gid=parent_gid,
                    holder_type=holder_key,
                )

                holder = await self._ensure_single_holder(
                    parent=parent,
                    holder_key=holder_key,
                    holder_key_map=holder_key_map,
                    existing_holders=existing_holders,
                    dirty_entities=dirty_entities,
                )

                if holder is not None:
                    new_holders.append(holder)

                logger.debug(
                    "holder_lock_released",
                    parent_gid=parent_gid,
                    holder_type=holder_key,
                )

        return new_holders

    def _find_needed_holders(
        self,
        parent: AsanaResource,
        holder_key_map: dict[str, tuple[str, str]],
        dirty_ids: set[int],
    ) -> list[str]:
        """Determine which holder types need to be ensured for a parent.

        Per PRD SC-001: When a Business (or Unit) with HOLDER_KEY_MAP is being
        saved, ALL missing holders are created -- not just those with dirty
        children. This guarantees the holder hierarchy exists in Asana for
        any saved parent entity.

        A holder is needed if:
        - It is not already populated on the parent AND tracked in the session.

        The dirty_ids parameter is accepted for interface compatibility but is
        not used for determining which holders to create. Child wiring (setting
        child.parent to the holder) happens in _wire_children_parent using the
        dirty_entities list.

        Args:
            parent: Entity with HOLDER_KEY_MAP.
            holder_key_map: The parent's HOLDER_KEY_MAP.
            dirty_ids: Set of id() values for dirty entities (reserved for
                future use; child wiring uses dirty_entities directly).

        Returns:
            List of holder_key strings that need to be ensured.
        """
        needed: list[str] = []

        for holder_key in holder_key_map:
            private_attr = f"_{holder_key}"
            holder = getattr(parent, private_attr, None)

            # If holder is already populated and tracked, skip.
            if holder is not None:
                holder_gid = getattr(holder, "gid", None) or ""
                if self._tracker.is_tracked(holder_gid):
                    logger.info(
                        "holder_already_tracked",
                        parent_gid=parent.gid,
                        holder_type=holder_key,
                        holder_gid=holder_gid,
                    )
                    continue

            # Holder is either not populated or populated but not tracked.
            # Per PRD SC-001: ensure it exists.
            needed.append(holder_key)

        return needed

    async def _ensure_single_holder(
        self,
        parent: AsanaResource,
        holder_key: str,
        holder_key_map: dict[str, tuple[str, str]],
        existing_holders: dict[str, AsanaResource],
        dirty_entities: list[AsanaResource],
    ) -> AsanaResource | None:
        """Ensure a single holder type exists, detecting or constructing as needed.

        Args:
            parent: The parent entity.
            holder_key: The holder type to ensure.
            holder_key_map: The parent's HOLDER_KEY_MAP.
            existing_holders: Holders already found in Asana.
            dirty_entities: All dirty entities (for child wiring).

        Returns:
            Newly constructed holder if one was created, or None if holder
            already existed (in session or Asana).
        """
        parent_gid = parent.gid or f"temp_{id(parent)}"

        # Check if holder was already tracked in session (another coroutine
        # may have created it between our initial check and acquiring the lock)
        private_attr = f"_{holder_key}"
        existing_on_parent = getattr(parent, private_attr, None)
        if existing_on_parent is not None:
            holder_gid = getattr(existing_on_parent, "gid", None) or ""
            if self._tracker.is_tracked(holder_gid):
                return None

        # Check if holder already exists in Asana
        if holder_key in existing_holders:
            existing = existing_holders[holder_key]
            # Track the existing holder so children can reference it
            self._tracker.track(existing)
            # Wire it onto the parent
            setattr(parent, private_attr, existing)
            # Wire children's parent reference to this holder
            self._wire_children_parent(parent, holder_key, existing, dirty_entities)
            logger.info(
                "holder_reused_existing",
                parent_gid=parent_gid,
                holder_type=holder_key,
                holder_gid=existing.gid,
            )
            return None

        # Construct new holder
        holder = construct_holder(holder_key, holder_key_map, parent)

        # Track the new holder (ChangeTracker will assign EntityState.NEW)
        self._tracker.track(holder)

        # Wire it onto the parent entity
        setattr(parent, private_attr, holder)

        # Wire children's parent reference to the new holder
        self._wire_children_parent(parent, holder_key, holder, dirty_entities)

        logger.info(
            "holder_construction_start",
            parent_gid=parent_gid,
            holder_type=holder_key,
            temp_gid=holder.gid,
        )

        return holder

    def _wire_children_parent(
        self,
        parent: AsanaResource,
        holder_key: str,
        holder: AsanaResource,
        dirty_entities: list[AsanaResource],
    ) -> None:
        """Wire children's parent reference to point to the holder.

        Per TDD-GAP-01 Section 4.4 (Option A): Set child.parent to a NameGid
        with the holder's temp GID so that _prepare_operations resolves it.

        Children are found from two sources:
        1. The holder itself (if it was an existing holder with populated children).
        2. Dirty entities that have a back-reference (_business or holder ref)
           pointing to the parent, and whose type matches the holder's child type.

        Only dirty children (those in dirty_entities) get their parent rewired.

        Args:
            parent: The parent entity (Business or Unit).
            holder_key: The holder type key.
            holder: The holder entity (existing or newly constructed).
            dirty_entities: All dirty entities (for identifying children).
        """
        from autom8_asana.models.common import NameGid

        children_attr = _HOLDER_CHILDREN_ATTR.get(holder_key)
        if not children_attr:
            return

        dirty_ids = set(id(e) for e in dirty_entities)
        holder_gid = holder.gid or f"temp_{id(holder)}"

        # Source 1: Children already on the holder (e.g., reused existing holder
        # that was populated during hydration)
        holder_children = getattr(holder, children_attr, None)
        if holder_children and isinstance(holder_children, list):
            for child in holder_children:
                if id(child) in dirty_ids:
                    child.parent = NameGid(gid=holder_gid)

        # Source 2: Dirty entities that belong under this holder.
        # Use the holder class's child type to match. The holder back-reference
        # attribute (e.g., _contact_holder) on the child should point to the
        # old or no holder, and _business should match our parent.
        from autom8_asana.persistence.holder_construction import get_holder_class_map

        holder_class = get_holder_class_map().get(holder_key)
        if holder_class is None:
            return

        child_class_name = getattr(holder_class, "_CHILD_CLASS_NAME", None)
        if not child_class_name:
            return

        parent_ref_name = getattr(holder_class, "PARENT_REF_NAME", None)

        for entity in dirty_entities:
            # Match by class name (type checking without importing all child classes)
            entity_class_name = type(entity).__name__
            if entity_class_name != child_class_name:
                continue

            # Verify this child belongs to our parent via _business reference
            child_business = getattr(entity, "_business", None)
            if child_business is not None and child_business is not parent:
                # For Unit-level holders, check if child's _business matches
                # the parent's _business (parent here is a Unit)
                parent_business = getattr(parent, "_business", None)
                if child_business is not parent_business:
                    continue

            # Wire the child's parent reference to the holder
            entity.parent = NameGid(gid=holder_gid)

            # Also wire the holder back-reference on the child
            if parent_ref_name:
                setattr(entity, parent_ref_name, holder)

            logger.debug(
                "holder_child_wired",
                child_gid=entity.gid,
                holder_gid=holder_gid,
                holder_type=holder_key,
            )
