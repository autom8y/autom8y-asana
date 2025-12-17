"""Change tracking via snapshot comparison.

Per ADR-0036: Snapshot-based dirty detection using model_dump().
Per ADR-0078: GID-based entity identity for deduplication.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from autom8_asana.persistence.models import EntityState

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class ChangeTracker:
    """Tracks entity changes via snapshot comparison.

    Per ADR-0036: Snapshot-based dirty detection using model_dump().
    Per ADR-0078: GID-based entity identity for deduplication.

    Responsibilities:
    - Store snapshots at track() time
    - Detect dirty entities by comparing current state to snapshot
    - Compute field-level change sets
    - Track entity lifecycle states
    - Deduplicate entities by GID

    Uses GID as primary key for identity, with fallback to __id_{id()}
    for entities without GIDs.
    """

    def __init__(self) -> None:
        """Initialize empty tracker state."""
        # key -> snapshot dict (key is GID or __id_{id})
        self._snapshots: dict[str, dict[str, Any]] = {}
        # key -> EntityState
        self._states: dict[str, EntityState] = {}
        # key -> entity reference
        self._entities: dict[str, AsanaResource] = {}
        # temp_gid -> real_gid (transition map for lookups)
        self._gid_transitions: dict[str, str] = {}
        # id(entity) -> key (reverse lookup for entity-to-key)
        self._entity_to_key: dict[int, str] = {}
        # Optional logger (injected by SaveSession)
        self._log: Any = None

    def _get_key(self, entity: AsanaResource) -> str:
        """Generate tracking key for entity.

        Per ADR-0078: GID-based entity identity.

        Priority:
        1. Use entity's GID if it exists (works for real and temp_ GIDs)
        2. Fall back to f"__id_{id(entity)}" for truly GID-less entities

        Args:
            entity: The entity to generate a key for.

        Returns:
            String key for tracking dictionaries.
        """
        gid: str | None = getattr(entity, "gid", None)
        if gid:
            return gid
        # Edge case: entity has no GID at all
        return f"__id_{id(entity)}"

    def track(self, entity: AsanaResource) -> AsanaResource:
        """Register entity and capture snapshot.

        Per FR-CHANGE-001: Capture original state at track time.
        Per FR-CHANGE-003: Detect new entities by GID.
        Per NFR-REL-002: Re-tracking same entity is idempotent.
        Per ADR-0078/FR-EID-006: Return existing entity if GID already tracked.

        Args:
            entity: The AsanaResource to track.

        Returns:
            The tracked entity (may be existing if same GID was already tracked).

        Raises:
            ValidationError: If GID format is invalid.
        """
        key = self._get_key(entity)

        # Check for existing entity with same GID
        if key in self._entities:
            existing = self._entities[key]
            if existing is not entity:
                # Same GID, different object - this is a re-fetch
                # Per FR-EID-007: Log at DEBUG level
                if self._log:
                    self._log.debug(
                        "tracker_duplicate_gid",
                        gid=key,
                        message="Entity re-tracked with same GID; updating reference",
                    )
                # Update reverse lookup for old entity
                old_id = id(existing)
                if old_id in self._entity_to_key:
                    del self._entity_to_key[old_id]
                # Update entity reference, keep original snapshot
                self._entities[key] = entity
                self._entity_to_key[id(entity)] = key
                return entity
            else:
                # Same entity object, already tracked - idempotent
                return entity

        # New tracking
        self._entities[key] = entity
        self._entity_to_key[id(entity)] = key
        self._snapshots[key] = entity.model_dump()

        # Determine initial state based on GID
        # New entities have no GID or a temp_* GID
        gid = entity.gid
        if not gid or gid.startswith("temp_"):
            self._states[key] = EntityState.NEW
        else:
            self._states[key] = EntityState.CLEAN

        return entity

    def untrack(self, entity: AsanaResource) -> None:
        """Remove entity from tracking.

        Per FR-CHANGE-008: Support untracking.

        Args:
            entity: Previously tracked entity.
        """
        key = self._get_key(entity)
        self._snapshots.pop(key, None)
        self._states.pop(key, None)
        self._entities.pop(key, None)
        self._entity_to_key.pop(id(entity), None)

    def mark_deleted(self, entity: AsanaResource) -> None:
        """Mark entity for deletion.

        Per FR-CHANGE-004: Set state to DELETED.

        Args:
            entity: Entity to mark for deletion.
        """
        key = self._get_key(entity)

        # If not tracked, track it first
        if key not in self._entities:
            self.track(entity)

        self._states[key] = EntityState.DELETED

    def mark_clean(self, entity: AsanaResource) -> None:
        """Mark entity as clean (unmodified) and update snapshot.

        Per FR-CHANGE-009: Reset state after successful save.

        Args:
            entity: Entity to mark as clean.
        """
        key = self._get_key(entity)

        if key in self._entities:
            # Update snapshot to current state
            self._snapshots[key] = entity.model_dump()
            self._states[key] = EntityState.CLEAN

    def get_state(self, entity: AsanaResource) -> EntityState:
        """Get entity lifecycle state.

        Per FR-UOW-008: Track entity lifecycle state.

        This method dynamically detects MODIFIED state by comparing
        current entity state to snapshot. If entity is CLEAN but
        has changes, it returns MODIFIED.

        Args:
            entity: Tracked entity.

        Returns:
            Current EntityState.

        Raises:
            ValueError: If entity is not tracked.
        """
        key = self._get_key(entity)

        if key not in self._states:
            raise ValueError(f"Entity not tracked: {type(entity).__name__}")

        state = self._states[key]

        # CLEAN might have become MODIFIED
        if state == EntityState.CLEAN and self._is_modified(entity):
            return EntityState.MODIFIED

        return state

    def get_changes(
        self,
        entity: AsanaResource,
    ) -> dict[str, tuple[Any, Any]]:
        """Compute field-level changes.

        Per FR-CHANGE-002: Return {field: (old, new)} dict.

        Args:
            entity: Tracked entity.

        Returns:
            Dict of {field_name: (old_value, new_value)} for changed fields.
            Empty dict if entity is not tracked or has no changes.
        """
        key = self._get_key(entity)

        if key not in self._snapshots:
            return {}

        original = self._snapshots[key]
        current = entity.model_dump()

        changes: dict[str, tuple[Any, Any]] = {}

        # Check all fields from both dicts
        all_field_keys = set(original.keys()) | set(current.keys())

        for field_key in all_field_keys:
            old_val = original.get(field_key)
            new_val = current.get(field_key)

            if old_val != new_val:
                changes[field_key] = (old_val, new_val)

        return changes

    def get_dirty_entities(self) -> list[AsanaResource]:
        """Get all entities with pending changes.

        Per FR-CHANGE-005: Skip clean (unmodified) entities.

        Returns:
            List of entities that need to be saved (NEW, MODIFIED, DELETED).
        """
        dirty: list[AsanaResource] = []

        for key, entity in self._entities.items():
            state = self._states.get(key, EntityState.CLEAN)

            if state == EntityState.DELETED:
                dirty.append(entity)
            elif state == EntityState.NEW:
                dirty.append(entity)
            elif state == EntityState.CLEAN:
                # Check if actually modified since tracking
                if self._is_modified(entity):
                    dirty.append(entity)

        return dirty

    def get_changed_fields(
        self,
        entity: AsanaResource,
    ) -> dict[str, Any]:
        """Get only the changed field values for minimal payload.

        Per FR-CHANGE-006: Generate minimal payloads.

        Args:
            entity: Tracked entity.

        Returns:
            Dict of {field_name: new_value} for changed fields.
        """
        changes = self.get_changes(entity)
        return {field: new_val for field, (_, new_val) in changes.items()}

    def _is_modified(self, entity: AsanaResource) -> bool:
        """Check if entity has changes since snapshot.

        Args:
            entity: Entity to check.

        Returns:
            True if entity differs from snapshot.
        """
        key = self._get_key(entity)

        if key not in self._snapshots:
            return False

        original = self._snapshots[key]
        current = entity.model_dump()

        return original != current

    # --- GID Transition Support (ADR-0078) ---

    def update_gid(self, entity: AsanaResource, old_key: str, new_gid: str) -> None:
        """Re-key entity after temp GID becomes real GID.

        Per ADR-0078/FR-EID-004: Support temp GID transition.

        Called by pipeline after successful CREATE operation.
        Maintains transition map for temp GID lookups.

        Args:
            entity: The entity being re-keyed.
            old_key: The original key (temp GID or __id_*).
            new_gid: The real GID assigned by Asana.
        """
        if old_key not in self._entities:
            return

        # Transfer all state to new key
        self._entities[new_gid] = self._entities.pop(old_key)
        self._snapshots[new_gid] = self._snapshots.pop(old_key)
        self._states[new_gid] = self._states.pop(old_key)

        # Record transition for lookup
        self._gid_transitions[old_key] = new_gid

        # Update reverse lookup
        self._entity_to_key[id(entity)] = new_gid

        if self._log:
            self._log.debug(
                "tracker_gid_transition",
                old_gid=old_key,
                new_gid=new_gid,
            )

    # --- Entity Lookup (ADR-0078) ---

    def find_by_gid(self, gid: str) -> AsanaResource | None:
        """Look up entity by GID.

        Per FR-EL-001: Provide find_by_gid() method.
        Per FR-EL-003: Return entity for transitioned temp GID.

        Searches direct entities first, then checks transition map
        for temp GIDs that have been resolved to real GIDs.

        Args:
            gid: The GID to look up (real or temp).

        Returns:
            Tracked entity or None if not found.
        """
        # Direct lookup
        if gid in self._entities:
            return self._entities[gid]

        # Check if it's a transitioned temp GID
        if gid in self._gid_transitions:
            real_gid = self._gid_transitions[gid]
            return self._entities.get(real_gid)

        return None

    def is_tracked(self, gid: str) -> bool:
        """Check if GID is currently tracked.

        Per FR-EL-005: Provide is_tracked() method.

        Args:
            gid: The GID to check.

        Returns:
            True if entity with this GID is tracked.
        """
        return self.find_by_gid(gid) is not None
