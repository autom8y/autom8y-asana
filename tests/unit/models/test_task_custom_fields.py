"""Tests for Task model custom fields integration.

Per Phase 3 Implementation Requirements: Custom Fields & SDK Integration.
Per TDD-TRIAGE-FIXES: Issue 14 - Direct custom field modification detection.
Per Initiative B Phase 2: Custom Field Unification naming conventions.
"""

from __future__ import annotations

import logging
import warnings

import pytest

from autom8_asana.models import Task
from autom8_asana.models.custom_field_accessor import CustomFieldAccessor


class TestTaskCustomFieldsEditor:
    """Tests for Task.custom_fields_editor() method.

    Per Initiative B Phase 2: FR-003 - custom_fields_editor() exists and returns accessor.
    """

    def test_custom_fields_editor_returns_accessor(self) -> None:
        """custom_fields_editor returns CustomFieldAccessor instance.

        Per FR-003: custom_fields_editor() exists and returns accessor.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        editor = task.custom_fields_editor()
        assert isinstance(editor, CustomFieldAccessor)

    def test_custom_fields_editor_returns_same_instance(self) -> None:
        """custom_fields_editor returns same accessor instance (cached).

        Per FR-003: Accessor instance is cached for this task.
        """
        task = Task(gid="123", custom_fields=[])
        editor1 = task.custom_fields_editor()
        editor2 = task.custom_fields_editor()
        assert editor1 is editor2

    def test_custom_fields_editor_no_warning(self) -> None:
        """custom_fields_editor does not emit deprecation warning.

        Per FR-003: custom_fields_editor() is the preferred method.
        """
        task = Task(gid="123", custom_fields=[])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            task.custom_fields_editor()
            # No deprecation warnings should be emitted
            deprecation_warnings = [
                warning for warning in w if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) == 0

    def test_custom_fields_editor_with_none_custom_fields(self) -> None:
        """custom_fields_editor works when custom_fields is None."""
        task = Task(gid="123")
        editor = task.custom_fields_editor()
        assert isinstance(editor, CustomFieldAccessor)
        assert len(editor) == 0

    def test_custom_fields_editor_get_value(self) -> None:
        """Editor can get values from task custom_fields."""
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Priority", "text_value": "High"},
                {"gid": "789", "name": "MRR", "number_value": 1000.5},
            ],
        )
        editor = task.custom_fields_editor()
        assert editor.get("Priority") == "High"
        assert editor.get("MRR") == 1000.5

    def test_custom_fields_editor_set_value(self) -> None:
        """Editor can set values."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        editor = task.custom_fields_editor()
        editor.set("Priority", "Low")
        assert editor.get("Priority") == "Low"

    def test_custom_fields_editor_and_get_custom_fields_share_instance(self) -> None:
        """custom_fields_editor() and get_custom_fields() return same instance.

        Per implementation: Both methods use _get_or_create_accessor().
        """
        task = Task(gid="123", custom_fields=[])

        editor = task.custom_fields_editor()

        # Suppress the deprecation warning for this test
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            accessor = task.get_custom_fields()

        assert editor is accessor


class TestTaskGetCustomFieldsDeprecation:
    """Tests for Task.get_custom_fields() deprecation warning.

    Per Initiative B Phase 2: FR-004 - get_custom_fields() emits DeprecationWarning.
    """

    def test_get_custom_fields_emits_deprecation_warning(self) -> None:
        """get_custom_fields emits DeprecationWarning.

        Per FR-004: get_custom_fields() emits DeprecationWarning.
        """
        task = Task(gid="123", custom_fields=[])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            task.get_custom_fields()

            # Should emit exactly one deprecation warning
            deprecation_warnings = [
                warning for warning in w if issubclass(warning.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) == 1
            assert "get_custom_fields() is deprecated" in str(deprecation_warnings[0].message)
            assert "custom_fields_editor()" in str(deprecation_warnings[0].message)

    def test_get_custom_fields_warning_stacklevel(self) -> None:
        """get_custom_fields warning points to caller, not implementation.

        Per implementation: stacklevel=2 ensures warning points to caller.
        """
        task = Task(gid="123", custom_fields=[])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            task.get_custom_fields()

            assert len(w) >= 1
            # Warning should reference this test file, not task.py
            warning = w[0]
            assert "test_task_custom_fields.py" in warning.filename

    def test_get_custom_fields_still_works(self) -> None:
        """get_custom_fields still returns accessor despite deprecation.

        Per backward compatibility: Method still works, just warns.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            accessor = task.get_custom_fields()

        assert isinstance(accessor, CustomFieldAccessor)
        assert accessor.get("Priority") == "High"


class TestTaskGetCustomFields:
    """Tests for Task.get_custom_fields() method (legacy tests)."""

    def test_get_custom_fields_accessor(self) -> None:
        """get_custom_fields returns CustomFieldAccessor instance."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            accessor = task.get_custom_fields()
        assert isinstance(accessor, CustomFieldAccessor)

    def test_accessor_cached(self) -> None:
        """get_custom_fields returns same accessor instance (cached)."""
        task = Task(gid="123", custom_fields=[])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            accessor1 = task.get_custom_fields()
            accessor2 = task.get_custom_fields()
        assert accessor1 is accessor2

    def test_accessor_with_none_custom_fields(self) -> None:
        """get_custom_fields works when custom_fields is None."""
        task = Task(gid="123")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            accessor = task.get_custom_fields()
        assert isinstance(accessor, CustomFieldAccessor)
        assert len(accessor) == 0

    def test_accessor_get_value(self) -> None:
        """Accessor can get values from task custom_fields."""
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "456", "name": "Priority", "text_value": "High"},
                {"gid": "789", "name": "MRR", "number_value": 1000.5},
            ],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            accessor = task.get_custom_fields()
        assert accessor.get("Priority") == "High"
        assert accessor.get("MRR") == 1000.5

    def test_accessor_set_value(self) -> None:
        """Accessor can set values."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            accessor = task.get_custom_fields()
        accessor.set("Priority", "Low")
        assert accessor.get("Priority") == "Low"


class TestTaskModelDumpWithCustomFields:
    """Tests for Task.model_dump() with custom field changes."""

    def test_model_dump_includes_changes(self) -> None:
        """model_dump includes custom field modifications.

        Per ADR-0056: Custom fields use dict format {"gid": value} for API payload.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        data = task.model_dump()
        assert "custom_fields" in data
        # ADR-0056: Dict format with GID as key
        assert isinstance(data["custom_fields"], dict)
        assert "456" in data["custom_fields"]
        assert data["custom_fields"]["456"] == "Low"

    def test_model_dump_no_changes(self) -> None:
        """model_dump preserves original format when no accessor used."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        data = task.model_dump()
        # Original format preserved when no accessor used
        assert data["custom_fields"][0]["text_value"] == "High"

    def test_model_dump_no_changes_accessor_accessed(self) -> None:
        """model_dump preserves original format when accessor has no changes."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        # Access accessor but don't make changes
        _ = task.custom_fields_editor()

        data = task.model_dump()
        # Original format preserved when accessor has no changes
        assert data["custom_fields"][0]["text_value"] == "High"

    def test_model_dump_with_added_field(self) -> None:
        """model_dump includes newly added fields.

        Per ADR-0056: Only modifications are included in the dict format.
        The to_api_dict() method only includes modified fields, not all fields.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("789", "New Value")

        data = task.model_dump()
        # ADR-0056: Dict format with only modified fields
        assert isinstance(data["custom_fields"], dict)
        assert "789" in data["custom_fields"]
        assert data["custom_fields"]["789"] == "New Value"

    def test_model_dump_with_removal(self) -> None:
        """model_dump includes None for removed fields.

        Per ADR-0056: Dict format with GID as key, None as value for removals.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.remove("Priority")

        data = task.model_dump()
        # ADR-0056: Dict format with None for removal
        assert isinstance(data["custom_fields"], dict)
        assert "456" in data["custom_fields"]
        assert data["custom_fields"]["456"] is None

    def test_model_dump_exclude_none(self) -> None:
        """model_dump with exclude_none still works correctly.

        Per ADR-0056: Dict format with GID as key.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        data = task.model_dump(exclude_none=True)
        assert "custom_fields" in data
        # ADR-0056: Dict format
        assert isinstance(data["custom_fields"], dict)
        assert data["custom_fields"]["456"] == "Low"


class TestBackwardCompatibility:
    """Tests for backward compatibility with direct custom_fields access."""

    def test_backward_compatible_direct_access(self) -> None:
        """Existing code can still access custom_fields directly."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        # Direct access still works
        assert task.custom_fields is not None
        assert task.custom_fields[0]["name"] == "Priority"
        assert task.custom_fields[0]["text_value"] == "High"

    def test_direct_access_is_original_data(self) -> None:
        """Direct access returns original data, not accessor format."""
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        # Use accessor to make changes
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        # Direct access still returns original structure
        assert task.custom_fields[0]["text_value"] == "High"

    def test_model_validate_preserves_custom_fields(self) -> None:
        """model_validate preserves custom_fields structure."""
        data = {
            "gid": "123",
            "custom_fields": [
                {
                    "gid": "456",
                    "name": "Priority",
                    "type": "enum",
                    "enum_value": {"gid": "ev1", "name": "High"},
                }
            ],
        }
        task = Task.model_validate(data)
        assert task.custom_fields is not None
        assert task.custom_fields[0]["enum_value"]["name"] == "High"

    def test_iteration_and_len_via_accessor(self) -> None:
        """Accessor iteration and len work correctly."""
        task = Task(
            gid="123",
            custom_fields=[
                {"gid": "1", "name": "A", "text_value": "X"},
                {"gid": "2", "name": "B", "text_value": "Y"},
            ],
        )
        accessor = task.custom_fields_editor()
        assert len(accessor) == 2
        names = [cf["name"] for cf in accessor]
        assert names == ["A", "B"]


class TestTaskCustomFieldsEdgeCases:
    """Edge case tests for Task custom fields."""

    def test_empty_custom_fields_list(self) -> None:
        """Task with empty custom_fields list works."""
        task = Task(gid="123", custom_fields=[])
        accessor = task.custom_fields_editor()
        assert len(accessor) == 0
        assert not accessor.has_changes()

    def test_accessor_after_model_copy_deep(self) -> None:
        """Accessor behavior after deep model_copy.

        Pydantic's model_copy(deep=True) copies private attributes including
        their internal state. This means accessor modifications are preserved
        in the copy. If you need a clean copy, use model_copy without
        modifications or create a new Task from the original data.

        Per ADR-0056: model_dump() with accessor changes produces API payload
        format (dict), not Task initialization format (list). This is
        intentional - model_dump() is for API submission, not round-tripping.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        # Deep copy task - Pydantic copies private attributes too
        task_copy = task.model_copy(deep=True)

        # Original task should still have changes
        assert task.custom_fields_editor().get("Priority") == "Low"

        # Deep copied task also has the accessor with its modifications
        copy_accessor = task_copy.custom_fields_editor()
        assert copy_accessor is not accessor  # Different object
        assert copy_accessor.get("Priority") == "Low"  # But same modifications

        # model_dump() with changes produces API format (dict), not Task format (list)
        # This is correct per ADR-0056 - model_dump is for API payloads
        data = task.model_dump(exclude_none=True)
        assert isinstance(data["custom_fields"], dict)
        assert data["custom_fields"]["456"] == "Low"

    def test_model_dump_to_json_with_changes(self) -> None:
        """JSON serialization via model_dump works with custom field changes.

        Note: model_dump_json() does not use model_dump() internally in Pydantic v2,
        so for JSON serialization with accessor changes, use json.dumps(task.model_dump()).
        This is the pattern used by SaveSession for API payloads.

        Per ADR-0056: Custom fields use dict format {"gid": value} for API payload.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        import json

        # Use model_dump then json.dumps (pattern used by SaveSession)
        json_str = json.dumps(task.model_dump())
        parsed = json.loads(json_str)

        # ADR-0056: Dict format for API payload
        assert isinstance(parsed["custom_fields"], dict)
        assert parsed["custom_fields"]["456"] == "Low"


# ---------------------------------------------------------------------------
# TDD-TRIAGE-FIXES Issue 14: Direct Custom Field Modification Detection
# ---------------------------------------------------------------------------


class TestDirectCustomFieldModificationDetection:
    """Tests for direct custom_fields modification detection.

    Per TDD-TRIAGE-FIXES Issue 14: model_dump() should detect direct list
    modifications, not just accessor changes.
    """

    def test_direct_modification_detected(self) -> None:
        """Direct modification to custom_fields list is detected.

        Per ADR-0067: _has_direct_custom_field_changes() returns True
        when custom_fields list is mutated directly.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Modify directly (not via accessor)
        task.custom_fields[0]["text_value"] = "Low"

        # Detection method should return True
        assert task._has_direct_custom_field_changes() is True

    def test_no_modification_not_detected(self) -> None:
        """No modification means detection returns False.

        Per ADR-0067: _has_direct_custom_field_changes() returns False
        when custom_fields list is unchanged.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # No modification
        assert task._has_direct_custom_field_changes() is False

    def test_accessor_modification_detected_via_has_changes(self) -> None:
        """Accessor modification is detected via accessor.has_changes().

        Per ADR-0067: Accessor changes use existing has_changes() method.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        # Accessor reports changes
        assert accessor.has_changes() is True

    def test_direct_changes_persisted_in_model_dump(self) -> None:
        """Direct modifications appear in model_dump() output.

        Per TDD-TRIAGE-FIXES: model_dump() should include direct modifications.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Modify directly
        task.custom_fields[0]["text_value"] = "Low"

        # model_dump should include the change
        data = task.model_dump()
        assert "custom_fields" in data
        # API format: dict with gid as key
        assert isinstance(data["custom_fields"], dict)
        assert "456" in data["custom_fields"]
        assert data["custom_fields"]["456"] == "Low"

    def test_accessor_takes_precedence_over_direct(self) -> None:
        """Accessor changes take precedence when both are present.

        Per ADR-0067: Accessor is the explicit API, so it wins.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Direct modification
        task.custom_fields[0]["text_value"] = "DirectValue"

        # Accessor modification (should win)
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "AccessorValue")

        # model_dump should use accessor value
        data = task.model_dump()
        assert data["custom_fields"]["456"] == "AccessorValue"

    def test_warning_logged_on_conflict(self, caplog: pytest.LogCaptureFixture) -> None:
        """Warning is logged when both accessor and direct changes exist.

        Per ADR-0067: Log warning for user awareness.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Both modifications
        task.custom_fields[0]["text_value"] = "DirectValue"
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "AccessorValue")

        # Trigger model_dump with warning capture
        with caplog.at_level(logging.WARNING):
            task.model_dump()

        # Check warning was logged
        assert "accessor and direct custom_field modifications" in caplog.text.lower()

    def test_snapshot_is_deep_copy(self) -> None:
        """Snapshot is a deep copy, not affected by later modifications.

        Per ADR-0067: Must use deepcopy to detect nested dict changes.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Verify snapshot was captured
        assert task._original_custom_fields is not None
        assert task._original_custom_fields[0]["text_value"] == "High"

        # Modify the current custom_fields
        task.custom_fields[0]["text_value"] = "Modified"

        # Snapshot should NOT be modified (deep copy)
        assert task._original_custom_fields[0]["text_value"] == "High"

    def test_empty_custom_fields_no_false_positive(self) -> None:
        """Empty custom_fields list doesn't cause false positive.

        Per ADR-0067: Empty list unchanged is not a change.
        """
        task = Task(gid="123", custom_fields=[])

        # No changes made
        assert task._has_direct_custom_field_changes() is False

    def test_none_custom_fields_handled(self) -> None:
        """None custom_fields doesn't cause errors.

        Per ADR-0067: Handle None custom_fields gracefully.
        """
        task = Task(gid="123")  # custom_fields is None

        # Snapshot should be None
        assert task._original_custom_fields is None

        # Detection should return False (no changes from None)
        assert task._has_direct_custom_field_changes() is False

    def test_setting_none_to_list_detected(self) -> None:
        """Setting None custom_fields to a list is detected as change.

        Per ADR-0067: If initially None and then set to list, that's a change.
        """
        task = Task(gid="123")  # custom_fields is None
        task.custom_fields = [{"gid": "456", "name": "Priority", "text_value": "High"}]

        # This should be detected as a change
        assert task._has_direct_custom_field_changes() is True

    def test_adding_new_field_via_direct_modification(self) -> None:
        """Adding a new field directly is detected.

        Per TDD-TRIAGE-FIXES: New fields added directly should be persisted.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Add a new field directly
        task.custom_fields.append({"gid": "789", "name": "Status", "text_value": "New"})

        # Should be detected
        assert task._has_direct_custom_field_changes() is True

        # model_dump should include both fields
        data = task.model_dump()
        assert isinstance(data["custom_fields"], dict)
        assert "789" in data["custom_fields"]
        assert data["custom_fields"]["789"] == "New"

    def test_enum_value_extraction(self) -> None:
        """Enum values are extracted correctly for API format.

        Per TDD-TRIAGE-FIXES: _extract_field_value handles enum_value.
        """
        task = Task(
            gid="123",
            custom_fields=[
                {
                    "gid": "456",
                    "name": "Status",
                    "enum_value": {"gid": "ev1", "name": "Done"},
                }
            ],
        )

        # Modify the enum value
        task.custom_fields[0]["enum_value"] = {"gid": "ev2", "name": "In Progress"}

        data = task.model_dump()
        # Enum is extracted to just the GID
        assert data["custom_fields"]["456"] == "ev2"

    def test_number_value_extraction(self) -> None:
        """Number values are extracted correctly for API format.

        Per TDD-TRIAGE-FIXES: _extract_field_value handles number_value.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "MRR", "number_value": 1000.0}],
        )

        # Modify the number value
        task.custom_fields[0]["number_value"] = 2000.0

        data = task.model_dump()
        assert data["custom_fields"]["456"] == 2000.0

    def test_clearing_field_via_direct_modification(self) -> None:
        """Clearing a field value directly results in None.

        Per TDD-TRIAGE-FIXES: Cleared fields should be None in API output.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Clear the value
        task.custom_fields[0]["text_value"] = None

        data = task.model_dump()
        assert data["custom_fields"]["456"] is None


# ---------------------------------------------------------------------------
# ADR-0074: Custom Field Tracking Reset Tests
# ---------------------------------------------------------------------------


class TestResetCustomFieldTracking:
    """Tests for Task.reset_custom_field_tracking() method.

    Per ADR-0074: Unified custom field tracking with proper reset after commit.
    """

    def test_reset_clears_accessor_modifications(self) -> None:
        """reset_custom_field_tracking() clears accessor _modifications (System 2).

        Per FR-001: After commit, accessor.has_changes() returns False.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        # Accessor has changes before reset
        assert accessor.has_changes() is True

        # Reset clears changes
        task.reset_custom_field_tracking()

        # Accessor has no changes after reset
        assert accessor.has_changes() is False

    def test_reset_updates_snapshot(self) -> None:
        """reset_custom_field_tracking() updates _original_custom_fields snapshot (System 3).

        Per FR-002: After commit, _has_direct_custom_field_changes() returns False.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Modify directly
        task.custom_fields[0]["text_value"] = "Low"

        # Direct changes detected before reset
        assert task._has_direct_custom_field_changes() is True

        # Reset updates snapshot
        task.reset_custom_field_tracking()

        # No direct changes after reset (snapshot now matches current)
        assert task._has_direct_custom_field_changes() is False
        # Verify snapshot was updated to new value
        assert task._original_custom_fields[0]["text_value"] == "Low"

    def test_reset_is_idempotent(self) -> None:
        """reset_custom_field_tracking() is safe to call multiple times.

        Per ADR-0074: Method is idempotent - repeated calls have no effect.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "Low")

        # Call reset multiple times
        task.reset_custom_field_tracking()
        task.reset_custom_field_tracking()
        task.reset_custom_field_tracking()

        # State remains clean
        assert accessor.has_changes() is False
        assert task._has_direct_custom_field_changes() is False

    def test_reset_with_no_accessor(self) -> None:
        """reset_custom_field_tracking() works when accessor was never created.

        Per ADR-0074: Safe to call even if get_custom_fields() was never called.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Verify accessor is None
        assert task._custom_fields_accessor is None

        # Reset should not raise
        task.reset_custom_field_tracking()

        # Accessor still None (not created by reset)
        assert task._custom_fields_accessor is None
        # Snapshot was updated
        assert task._original_custom_fields is not None

    def test_reset_with_none_custom_fields(self) -> None:
        """reset_custom_field_tracking() handles None custom_fields gracefully."""
        task = Task(gid="123")  # No custom_fields
        assert task.custom_fields is None

        # Reset should not raise
        task.reset_custom_field_tracking()

        # Snapshot is None
        assert task._original_custom_fields is None

    def test_reset_clears_both_systems_simultaneously(self) -> None:
        """reset_custom_field_tracking() clears both accessor AND snapshot.

        Per ADR-0074: Both System 2 and System 3 are reset together.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Make changes via accessor (System 2)
        accessor = task.custom_fields_editor()
        accessor.set("Priority", "AccessorValue")

        # Make direct changes (System 3)
        task.custom_fields[0]["text_value"] = "DirectValue"

        # Both systems show changes
        assert accessor.has_changes() is True
        assert task._has_direct_custom_field_changes() is True

        # Single reset clears both
        task.reset_custom_field_tracking()

        # Both systems are clean
        assert accessor.has_changes() is False
        assert task._has_direct_custom_field_changes() is False

    def test_update_custom_fields_snapshot_method(self) -> None:
        """_update_custom_fields_snapshot() is a deep copy.

        Per FR-002: Snapshot must be independent of current custom_fields.
        """
        task = Task(
            gid="123",
            custom_fields=[{"gid": "456", "name": "Priority", "text_value": "High"}],
        )

        # Manually update snapshot
        task._update_custom_fields_snapshot()

        # Modify current custom_fields
        task.custom_fields[0]["text_value"] = "Modified"

        # Snapshot should NOT be affected (deep copy)
        assert task._original_custom_fields[0]["text_value"] == "High"
