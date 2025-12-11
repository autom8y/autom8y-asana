"""Tests for ChangeTracker.

Per TDD-0010: Verify snapshot-based dirty detection per ADR-0036.
"""

from __future__ import annotations

import pytest

from autom8_asana.models import Task
from autom8_asana.persistence.models import EntityState
from autom8_asana.persistence.tracker import ChangeTracker


# ---------------------------------------------------------------------------
# Tracking Tests
# ---------------------------------------------------------------------------


class TestTracking:
    """Tests for entity tracking operations."""

    def test_track_captures_snapshot(self) -> None:
        """track() captures entity snapshot at call time."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original Name")

        tracker.track(task)

        # Modify entity after tracking
        task.name = "Modified Name"

        # Changes should detect the difference
        changes = tracker.get_changes(task)
        assert "name" in changes
        assert changes["name"] == ("Original Name", "Modified Name")

    def test_track_is_idempotent(self) -> None:
        """Re-tracking same entity does not update snapshot."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original")

        tracker.track(task)
        task.name = "Modified"

        # Re-track should NOT update snapshot
        tracker.track(task)

        changes = tracker.get_changes(task)
        assert "name" in changes
        assert changes["name"] == ("Original", "Modified")

    def test_track_multiple_entities(self) -> None:
        """Multiple entities can be tracked independently."""
        tracker = ChangeTracker()
        task1 = Task(gid="123", name="Task 1")
        task2 = Task(gid="456", name="Task 2")

        tracker.track(task1)
        tracker.track(task2)

        task1.name = "Modified 1"

        # Only task1 should show changes
        changes1 = tracker.get_changes(task1)
        changes2 = tracker.get_changes(task2)

        assert "name" in changes1
        assert changes2 == {}


class TestUntracking:
    """Tests for entity untracking operations."""

    def test_untrack_removes_entity(self) -> None:
        """untrack() removes entity from tracking."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Test")

        tracker.track(task)
        tracker.untrack(task)

        # Should raise when checking state of untracked entity
        with pytest.raises(ValueError, match="Entity not tracked"):
            tracker.get_state(task)

    def test_untrack_entity_not_tracked(self) -> None:
        """untrack() is safe on entities never tracked."""
        tracker = ChangeTracker()
        task = Task(gid="123")

        # Should not raise
        tracker.untrack(task)

    def test_untrack_removes_from_dirty_entities(self) -> None:
        """Untracked entities don't appear in dirty list."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Test")

        tracker.track(task)
        task.name = "Modified"

        # Should be dirty before untrack
        dirty = tracker.get_dirty_entities()
        assert task in dirty

        tracker.untrack(task)

        # Should not be dirty after untrack
        dirty = tracker.get_dirty_entities()
        assert task not in dirty


# ---------------------------------------------------------------------------
# State Management Tests
# ---------------------------------------------------------------------------


class TestEntityStates:
    """Tests for entity state management."""

    def test_new_entity_has_new_state(self) -> None:
        """Entity without GID gets NEW state."""
        tracker = ChangeTracker()
        # Task with temp GID (simulating new entity)
        task = Task(gid="temp_12345", name="New Task")

        tracker.track(task)

        assert tracker.get_state(task) == EntityState.NEW

    def test_existing_entity_has_clean_state(self) -> None:
        """Entity with real GID gets CLEAN state."""
        tracker = ChangeTracker()
        task = Task(gid="1234567890", name="Existing Task")

        tracker.track(task)

        assert tracker.get_state(task) == EntityState.CLEAN

    def test_mark_deleted_sets_state(self) -> None:
        """mark_deleted() sets state to DELETED."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="To Delete")

        tracker.track(task)
        tracker.mark_deleted(task)

        assert tracker.get_state(task) == EntityState.DELETED

    def test_mark_deleted_untracked_entity(self) -> None:
        """mark_deleted() tracks entity if not already tracked."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="To Delete")

        # Not tracked yet
        tracker.mark_deleted(task)

        # Should be tracked and deleted
        assert tracker.get_state(task) == EntityState.DELETED

    def test_mark_clean_resets_state(self) -> None:
        """mark_clean() resets state and updates snapshot."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original")

        tracker.track(task)
        task.name = "Modified"

        # Should be MODIFIED
        assert tracker.get_state(task) == EntityState.MODIFIED

        tracker.mark_clean(task)

        # Should be CLEAN and snapshot updated
        assert tracker.get_state(task) == EntityState.CLEAN
        assert tracker.get_changes(task) == {}

    def test_get_state_detects_modified(self) -> None:
        """get_state() dynamically detects MODIFIED state."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original", completed=False)

        tracker.track(task)
        assert tracker.get_state(task) == EntityState.CLEAN

        # Modify entity
        task.name = "Modified"

        # State should now be MODIFIED (detected dynamically)
        assert tracker.get_state(task) == EntityState.MODIFIED

    def test_get_state_untracked_raises(self) -> None:
        """get_state() raises for untracked entity."""
        tracker = ChangeTracker()
        task = Task(gid="123")

        with pytest.raises(ValueError, match="Entity not tracked"):
            tracker.get_state(task)


# ---------------------------------------------------------------------------
# Change Detection Tests
# ---------------------------------------------------------------------------


class TestChangeDetection:
    """Tests for change detection operations."""

    def test_get_changes_returns_diff(self) -> None:
        """get_changes() returns field-level differences."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original", completed=False)

        tracker.track(task)
        task.name = "Modified"
        task.completed = True

        changes = tracker.get_changes(task)

        assert "name" in changes
        assert changes["name"] == ("Original", "Modified")
        assert "completed" in changes
        assert changes["completed"] == (False, True)
        # GID should not be in changes
        assert "gid" not in changes

    def test_get_changes_empty_when_unchanged(self) -> None:
        """get_changes() returns empty dict when no changes."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original")

        tracker.track(task)

        changes = tracker.get_changes(task)
        assert changes == {}

    def test_get_changes_untracked_returns_empty(self) -> None:
        """get_changes() returns empty dict for untracked entity."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Test")

        changes = tracker.get_changes(task)
        assert changes == {}

    def test_get_changed_fields_returns_new_values(self) -> None:
        """get_changed_fields() returns only new values."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original", notes="Old notes")

        tracker.track(task)
        task.name = "New Name"
        task.notes = "New notes"

        changed_fields = tracker.get_changed_fields(task)

        assert changed_fields == {
            "name": "New Name",
            "notes": "New notes",
        }

    def test_get_changed_fields_empty_when_unchanged(self) -> None:
        """get_changed_fields() returns empty dict when no changes."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original")

        tracker.track(task)

        changed_fields = tracker.get_changed_fields(task)
        assert changed_fields == {}


# ---------------------------------------------------------------------------
# Dirty Entity Collection Tests
# ---------------------------------------------------------------------------


class TestDirtyEntities:
    """Tests for dirty entity collection."""

    def test_get_dirty_entities_returns_new_modified_deleted(self) -> None:
        """get_dirty_entities() returns NEW, MODIFIED, and DELETED entities."""
        tracker = ChangeTracker()

        # NEW entity (temp GID)
        new_task = Task(gid="temp_111", name="New Task")
        tracker.track(new_task)

        # MODIFIED entity
        modified_task = Task(gid="222", name="Original")
        tracker.track(modified_task)
        modified_task.name = "Modified"

        # DELETED entity
        deleted_task = Task(gid="333", name="To Delete")
        tracker.track(deleted_task)
        tracker.mark_deleted(deleted_task)

        # CLEAN entity (should not be in dirty)
        clean_task = Task(gid="444", name="Unchanged")
        tracker.track(clean_task)

        dirty = tracker.get_dirty_entities()

        assert new_task in dirty
        assert modified_task in dirty
        assert deleted_task in dirty
        assert clean_task not in dirty
        assert len(dirty) == 3

    def test_get_dirty_entities_empty_tracker(self) -> None:
        """get_dirty_entities() returns empty list for empty tracker."""
        tracker = ChangeTracker()

        dirty = tracker.get_dirty_entities()
        assert dirty == []

    def test_get_dirty_entities_all_clean(self) -> None:
        """get_dirty_entities() returns empty list when all clean."""
        tracker = ChangeTracker()
        task1 = Task(gid="123", name="Task 1")
        task2 = Task(gid="456", name="Task 2")

        tracker.track(task1)
        tracker.track(task2)

        dirty = tracker.get_dirty_entities()
        assert dirty == []


# ---------------------------------------------------------------------------
# Edge Cases Tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_track_entity_with_none_fields(self) -> None:
        """Tracking works with None field values."""
        tracker = ChangeTracker()
        task = Task(gid="123", name=None, notes=None)

        tracker.track(task)
        task.name = "Now has name"

        changes = tracker.get_changes(task)
        assert "name" in changes
        assert changes["name"] == (None, "Now has name")

    def test_change_field_to_none(self) -> None:
        """Changing field to None is detected."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Has name")

        tracker.track(task)
        task.name = None

        changes = tracker.get_changes(task)
        assert "name" in changes
        assert changes["name"] == ("Has name", None)

    def test_multiple_modifications(self) -> None:
        """Multiple modifications to same field tracked correctly."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="First")

        tracker.track(task)
        task.name = "Second"
        task.name = "Third"

        changes = tracker.get_changes(task)
        assert changes["name"] == ("First", "Third")

    def test_revert_modification(self) -> None:
        """Reverting to original value shows no changes."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Original")

        tracker.track(task)
        task.name = "Modified"
        task.name = "Original"  # Revert

        changes = tracker.get_changes(task)
        assert changes == {}
        assert tracker.get_state(task) == EntityState.CLEAN

    def test_mark_clean_after_delete(self) -> None:
        """mark_clean() after delete resets to CLEAN."""
        tracker = ChangeTracker()
        task = Task(gid="123", name="Test")

        tracker.track(task)
        tracker.mark_deleted(task)
        assert tracker.get_state(task) == EntityState.DELETED

        tracker.mark_clean(task)
        assert tracker.get_state(task) == EntityState.CLEAN

    def test_mark_clean_on_untracked(self) -> None:
        """mark_clean() on untracked entity is safe (no-op)."""
        tracker = ChangeTracker()
        task = Task(gid="123")

        # Should not raise
        tracker.mark_clean(task)

        # Still not tracked
        with pytest.raises(ValueError):
            tracker.get_state(task)

    def test_complex_nested_field_changes(self) -> None:
        """Changes to nested fields (dicts/lists) are detected."""
        tracker = ChangeTracker()
        task = Task(
            gid="123",
            name="Task",
            custom_fields=[{"gid": "cf1", "value": "original"}],
        )

        tracker.track(task)

        # Modify nested structure
        task.custom_fields = [{"gid": "cf1", "value": "modified"}]

        changes = tracker.get_changes(task)
        assert "custom_fields" in changes

    def test_same_object_identity(self) -> None:
        """Same object tracked by id() not by value."""
        tracker = ChangeTracker()

        # Two different objects with same GID
        task1 = Task(gid="123", name="Task 1")
        task2 = Task(gid="123", name="Task 2")

        tracker.track(task1)
        tracker.track(task2)

        # Both should be tracked independently
        task1.name = "Modified 1"

        changes1 = tracker.get_changes(task1)
        changes2 = tracker.get_changes(task2)

        assert "name" in changes1
        assert changes2 == {}
