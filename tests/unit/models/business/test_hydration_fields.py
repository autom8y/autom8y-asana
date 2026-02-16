"""Tests for task opt_fields constants.

Per PRD-CACHE-PERF-HYDRATION and TDD-CACHE-PERF-HYDRATION:
Validates the unified field set constants for cache coherence.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.fields import (
    DETECTION_OPT_FIELDS,
    STANDARD_TASK_OPT_FIELDS,
)


class TestStandardTaskOptFields:
    """Tests for STANDARD_TASK_OPT_FIELDS constant."""

    def test_is_tuple(self) -> None:
        """FR-FIELDS-006: Field set is immutable (tuple, not list)."""
        assert isinstance(STANDARD_TASK_OPT_FIELDS, tuple)

    def test_field_count(self) -> None:
        """FR-FIELDS-001: Contains exactly 15 required fields."""
        assert len(STANDARD_TASK_OPT_FIELDS) == 15

    def test_includes_parent_gid(self) -> None:
        """FR-FIELDS-003: Includes parent.gid for upward traversal."""
        assert "parent.gid" in STANDARD_TASK_OPT_FIELDS

    def test_includes_name(self) -> None:
        """Core identification field is present."""
        assert "name" in STANDARD_TASK_OPT_FIELDS

    def test_includes_detection_fields(self) -> None:
        """FR-FIELDS-005: Includes all Tier 1 detection fields."""
        assert "memberships.project.gid" in STANDARD_TASK_OPT_FIELDS
        assert "memberships.project.name" in STANDARD_TASK_OPT_FIELDS

    def test_includes_people_value(self) -> None:
        """FR-FIELDS-004: Includes custom_fields.people_value for Owner cascading."""
        assert "custom_fields.people_value" in STANDARD_TASK_OPT_FIELDS

    def test_includes_custom_fields_base(self) -> None:
        """Includes custom_fields base field."""
        assert "custom_fields" in STANDARD_TASK_OPT_FIELDS

    def test_includes_custom_fields_subfields(self) -> None:
        """Includes all custom_fields subfields for cascading."""
        expected_subfields = [
            "custom_fields.name",
            "custom_fields.enum_value",
            "custom_fields.enum_value.name",
            "custom_fields.multi_enum_values",
            "custom_fields.multi_enum_values.name",
            "custom_fields.display_value",
            "custom_fields.number_value",
            "custom_fields.text_value",
            "custom_fields.resource_subtype",
        ]
        for field in expected_subfields:
            assert field in STANDARD_TASK_OPT_FIELDS, f"Missing field: {field}"

    def test_immutable(self) -> None:
        """Verify tuple cannot be modified."""
        with pytest.raises(TypeError):
            STANDARD_TASK_OPT_FIELDS[0] = "modified"  # type: ignore[index]


class TestDetectionOptFields:
    """Tests for DETECTION_OPT_FIELDS constant."""

    def test_is_tuple(self) -> None:
        """Detection field set is immutable (tuple, not list)."""
        assert isinstance(DETECTION_OPT_FIELDS, tuple)

    def test_field_count(self) -> None:
        """FR-DETECT-003: Contains exactly 4 minimal fields."""
        assert len(DETECTION_OPT_FIELDS) == 4

    def test_includes_parent_gid(self) -> None:
        """Detection includes parent.gid for traversal preparation."""
        assert "parent.gid" in DETECTION_OPT_FIELDS

    def test_includes_name(self) -> None:
        """Detection includes name for Tier 2 detection."""
        assert "name" in DETECTION_OPT_FIELDS

    def test_includes_membership_fields(self) -> None:
        """Detection includes membership fields for Tier 1 detection."""
        assert "memberships.project.gid" in DETECTION_OPT_FIELDS
        assert "memberships.project.name" in DETECTION_OPT_FIELDS

    def test_is_subset_of_standard(self) -> None:
        """FR-DETECT-001: Detection fields are subset of standard fields."""
        detection_set = set(DETECTION_OPT_FIELDS)
        standard_set = set(STANDARD_TASK_OPT_FIELDS)
        assert detection_set.issubset(standard_set)

    def test_immutable(self) -> None:
        """Verify tuple cannot be modified."""
        with pytest.raises(TypeError):
            DETECTION_OPT_FIELDS[0] = "modified"  # type: ignore[index]


class TestFieldSetConsistency:
    """Tests for consistency between field sets."""

    def test_detection_subset_of_standard(self) -> None:
        """FR-DETECT-001: All detection fields exist in standard set."""
        for field in DETECTION_OPT_FIELDS:
            assert field in STANDARD_TASK_OPT_FIELDS, (
                f"Detection field '{field}' not in standard set"
            )

    def test_no_duplicate_fields_in_standard(self) -> None:
        """Standard field set has no duplicates."""
        assert len(STANDARD_TASK_OPT_FIELDS) == len(set(STANDARD_TASK_OPT_FIELDS))

    def test_no_duplicate_fields_in_detection(self) -> None:
        """Detection field set has no duplicates."""
        assert len(DETECTION_OPT_FIELDS) == len(set(DETECTION_OPT_FIELDS))

    def test_all_fields_are_strings(self) -> None:
        """All fields in both sets are strings."""
        for field in STANDARD_TASK_OPT_FIELDS:
            assert isinstance(field, str), f"Non-string field: {field}"
        for field in DETECTION_OPT_FIELDS:
            assert isinstance(field, str), f"Non-string field: {field}"


class TestHydrationModuleCompatibility:
    """Tests for backward compatibility with hydration module constants."""

    def test_hydration_business_full_derives_from_canonical(self) -> None:
        """hydration._BUSINESS_FULL_OPT_FIELDS derives from STANDARD_TASK_OPT_FIELDS."""
        from autom8_asana.models.business.hydration import _BUSINESS_FULL_OPT_FIELDS

        assert set(_BUSINESS_FULL_OPT_FIELDS) == set(STANDARD_TASK_OPT_FIELDS)

    def test_hydration_uses_full_fields_for_detection(self) -> None:
        """Per IMP-23: hydration no longer has _DETECTION_OPT_FIELDS alias."""
        import autom8_asana.models.business.hydration as hydration_mod

        assert not hasattr(hydration_mod, "_DETECTION_OPT_FIELDS")


class TestTasksClientCompatibility:
    """Tests for TasksClient field consistency with standard set."""

    def test_tasks_client_detection_equals_standard(self) -> None:
        """FR-CACHE-003: TasksClient._DETECTION_FIELDS equals STANDARD_TASK_OPT_FIELDS."""
        from autom8_asana.clients.tasks import TasksClient

        assert set(TasksClient._DETECTION_FIELDS) == set(STANDARD_TASK_OPT_FIELDS)

    def test_tasks_client_has_parent_gid(self) -> None:
        """FR-CACHE-001: TasksClient._DETECTION_FIELDS includes parent.gid."""
        from autom8_asana.clients.tasks import TasksClient

        assert "parent.gid" in TasksClient._DETECTION_FIELDS

    def test_tasks_client_has_people_value(self) -> None:
        """FR-CACHE-002: TasksClient._DETECTION_FIELDS includes people_value."""
        from autom8_asana.clients.tasks import TasksClient

        assert "custom_fields.people_value" in TasksClient._DETECTION_FIELDS
