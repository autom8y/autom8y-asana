"""Change tracking via snapshot comparison.

Per ADR-0036: Snapshot-based dirty detection using model_dump().
"""

from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING

from autom8_asana.persistence.models import EntityState
from autom8_asana.persistence.exceptions import ValidationError

# GID format: numeric string or temp_<number> for new entities
# Per ADR-0049: Validate at track time for fail-fast behavior
GID_PATTERN = re.compile(r"^(temp_\d+|\d+)$")

if TYPE_CHECKING:
    from autom8_asana.models.base import AsanaResource


class ChangeTracker:
    """Tracks entity changes via snapshot comparison.

    Per ADR-0036: Snapshot-based dirty detection using model_dump().

    Responsibilities:
    - Store snapshots at track() time
    - Detect dirty entities by comparing current state to snapshot
    - Compute field-level change sets
    - Track entity lifecycle states

    Uses id(entity) for identity to handle entities that may not
    have GIDs yet (new entities) or may have duplicate GIDs in
    different sessions.
    """

    def __init__(self) -> None:
        """Initialize empty tracker state."""
        # id(entity) -> snapshot dict
        self._snapshots: dict[int, dict[str, Any]] = {}
        # id(entity) -> EntityState
        self._states: dict[int, EntityState] = {}
        # id(entity) -> entity (for retrieval)
        self._entities: dict[int, AsanaResource] = {}

    def track(self, entity: AsanaResource) -> None:
        """Register entity and capture snapshot.

        Per FR-CHANGE-001: Capture original state at track time.
        Per FR-CHANGE-003: Detect new entities by GID.
        Per NFR-REL-002: Re-tracking same entity is idempotent.

        Args:
            entity: The AsanaResource to track.

        Raises:
            ValidationError: If GID format is invalid.
        """
        entity_id = id(entity)

        # Idempotent: if already tracked, don't re-capture
        if entity_id in self._entities:
            return

        # Validate GID format before tracking
        self._validate_gid_format(entity.gid)

        self._entities[entity_id] = entity
        self._snapshots[entity_id] = entity.model_dump()

        # Determine initial state based on GID
        # New entities have no GID or a temp_* GID
        gid = entity.gid
        if not gid or gid.startswith("temp_"):
            self._states[entity_id] = EntityState.NEW
        else:
            self._states[entity_id] = EntityState.CLEAN

    def untrack(self, entity: AsanaResource) -> None:
        """Remove entity from tracking.

        Per FR-CHANGE-008: Support untracking.

        Args:
            entity: Previously tracked entity.
        """
        entity_id = id(entity)
        self._snapshots.pop(entity_id, None)
        self._states.pop(entity_id, None)
        self._entities.pop(entity_id, None)

    def mark_deleted(self, entity: AsanaResource) -> None:
        """Mark entity for deletion.

        Per FR-CHANGE-004: Set state to DELETED.

        Args:
            entity: Entity to mark for deletion.
        """
        entity_id = id(entity)

        # If not tracked, track it first
        if entity_id not in self._entities:
            self.track(entity)

        self._states[entity_id] = EntityState.DELETED

    def mark_clean(self, entity: AsanaResource) -> None:
        """Mark entity as clean (unmodified) and update snapshot.

        Per FR-CHANGE-009: Reset state after successful save.

        Args:
            entity: Entity to mark as clean.
        """
        entity_id = id(entity)

        if entity_id in self._entities:
            # Update snapshot to current state
            self._snapshots[entity_id] = entity.model_dump()
            self._states[entity_id] = EntityState.CLEAN

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
        entity_id = id(entity)

        if entity_id not in self._states:
            raise ValueError(f"Entity not tracked: {type(entity).__name__}")

        state = self._states[entity_id]

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
        entity_id = id(entity)

        if entity_id not in self._snapshots:
            return {}

        original = self._snapshots[entity_id]
        current = entity.model_dump()

        changes: dict[str, tuple[Any, Any]] = {}

        # Check all fields from both dicts
        all_keys = set(original.keys()) | set(current.keys())

        for key in all_keys:
            old_val = original.get(key)
            new_val = current.get(key)

            if old_val != new_val:
                changes[key] = (old_val, new_val)

        return changes

    def get_dirty_entities(self) -> list[AsanaResource]:
        """Get all entities with pending changes.

        Per FR-CHANGE-005: Skip clean (unmodified) entities.

        Returns:
            List of entities that need to be saved (NEW, MODIFIED, DELETED).
        """
        dirty: list[AsanaResource] = []

        for entity_id, entity in self._entities.items():
            state = self._states[entity_id]

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
        entity_id = id(entity)

        if entity_id not in self._snapshots:
            return False

        original = self._snapshots[entity_id]
        current = entity.model_dump()

        return original != current

    def _validate_gid_format(self, gid: str | None) -> None:
        """Validate GID format.

        Per ADR-0049: Validates GID format at track time.

        Args:
            gid: The GID to validate. None is allowed for new entities.

        Raises:
            ValidationError: If GID format is invalid.
        """
        if gid is None:
            return  # New entities have no GID yet

        if gid == "":
            raise ValidationError(
                "GID cannot be empty string. Use None for new entities."
            )

        if not GID_PATTERN.match(gid):
            raise ValidationError(
                f"Invalid GID format: {gid!r}. "
                f"GID must be a numeric string or temp_<number> for new entities."
            )
