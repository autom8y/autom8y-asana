"""Tests for selection predicates and selectors."""

from __future__ import annotations

from unittest.mock import MagicMock


from autom8_asana.models.business.process import Process, ProcessType
from autom8_asana.resolution.selection import (
    CompoundPredicate,
    EntitySelector,
    FieldPredicate,
    NewestActivePredicate,
    ProcessSelector,
)
from tests.unit.resolution.conftest import make_business_entity


class TestFieldPredicate:
    """Tests for FieldPredicate."""

    def test_matches_exact_value(self) -> None:
        """Test matching exact field value."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(return_value={"position": "Owner"})

        predicate = FieldPredicate("position", "Owner")
        assert predicate.matches(entity) is True

    def test_no_match(self) -> None:
        """Test no match when values differ."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(return_value={"position": "Manager"})

        predicate = FieldPredicate("position", "Owner")
        assert predicate.matches(entity) is False

    def test_matches_dict_name(self) -> None:
        """Test matching dict with 'name' key."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(
            return_value={"position": {"name": "Owner", "gid": "123"}}
        )

        predicate = FieldPredicate("position", "Owner")
        assert predicate.matches(entity) is True

    def test_matches_dict_display_value(self) -> None:
        """Test matching dict with 'display_value' key."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(
            return_value={"position": {"display_value": "Owner"}}
        )

        predicate = FieldPredicate("position", "Owner")
        assert predicate.matches(entity) is True

    def test_field_not_present(self) -> None:
        """Test behavior when field is not present."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(return_value={})

        predicate = FieldPredicate("position", "Owner")
        assert predicate.matches(entity) is False


class TestCompoundPredicate:
    """Tests for CompoundPredicate."""

    def test_and_operator_all_match(self) -> None:
        """Test AND operator when all predicates match."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(
            return_value={"position": "Owner", "status": "Active"}
        )

        predicate = CompoundPredicate(
            operator="and",
            predicates=[
                FieldPredicate("position", "Owner"),
                FieldPredicate("status", "Active"),
            ],
        )
        assert predicate.matches(entity) is True

    def test_and_operator_partial_match(self) -> None:
        """Test AND operator when only some predicates match."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(
            return_value={"position": "Owner", "status": "Inactive"}
        )

        predicate = CompoundPredicate(
            operator="and",
            predicates=[
                FieldPredicate("position", "Owner"),
                FieldPredicate("status", "Active"),
            ],
        )
        assert predicate.matches(entity) is False

    def test_or_operator_any_match(self) -> None:
        """Test OR operator when any predicate matches."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(
            return_value={"position": "Manager", "status": "Active"}
        )

        predicate = CompoundPredicate(
            operator="or",
            predicates=[
                FieldPredicate("position", "Owner"),
                FieldPredicate("status", "Active"),
            ],
        )
        assert predicate.matches(entity) is True

    def test_or_operator_no_match(self) -> None:
        """Test OR operator when no predicates match."""
        entity = make_business_entity("test-123", "Test")
        entity.get_custom_fields = MagicMock(
            return_value={"position": "Manager", "status": "Inactive"}
        )

        predicate = CompoundPredicate(
            operator="or",
            predicates=[
                FieldPredicate("position", "Owner"),
                FieldPredicate("status", "Active"),
            ],
        )
        assert predicate.matches(entity) is False


class TestNewestActivePredicate:
    """Tests for NewestActivePredicate."""

    def test_always_matches(self) -> None:
        """Test that NewestActivePredicate always matches (logic in selector)."""
        entity = make_business_entity("test-123", "Test")
        predicate = NewestActivePredicate()
        assert predicate.matches(entity) is True


class TestEntitySelector:
    """Tests for EntitySelector."""

    def test_select_returns_first_when_no_predicate(self) -> None:
        """Test select returns first child when no predicate."""
        children = [
            make_business_entity("1", "First"),
            make_business_entity("2", "Second"),
        ]
        selector = EntitySelector()
        result = selector.select(children)
        assert result == children[0]

    def test_select_returns_none_for_empty_list(self) -> None:
        """Test select returns None for empty list."""
        selector = EntitySelector()
        result = selector.select([])
        assert result is None

    def test_select_with_predicate(self) -> None:
        """Test select with matching predicate."""
        entity1 = make_business_entity("1", "First")
        entity1.get_custom_fields = MagicMock(return_value={"type": "A"})

        entity2 = make_business_entity("2", "Second")
        entity2.get_custom_fields = MagicMock(return_value={"type": "B"})

        children = [entity1, entity2]
        selector = EntitySelector()
        result = selector.select(children, FieldPredicate("type", "B"))
        assert result == entity2

    def test_select_no_match_returns_none(self) -> None:
        """Test select returns None when no match."""
        entity = make_business_entity("1", "Test")
        entity.get_custom_fields = MagicMock(return_value={"type": "A"})

        selector = EntitySelector()
        result = selector.select([entity], FieldPredicate("type", "B"))
        assert result is None

    def test_select_all_returns_all_when_no_predicate(self) -> None:
        """Test select_all returns all children when no predicate."""
        children = [
            make_business_entity("1", "First"),
            make_business_entity("2", "Second"),
        ]
        selector = EntitySelector()
        result = selector.select_all(children)
        assert result == children

    def test_select_all_with_predicate(self) -> None:
        """Test select_all with predicate."""
        entity1 = make_business_entity("1", "First")
        entity1.get_custom_fields = MagicMock(return_value={"active": "true"})

        entity2 = make_business_entity("2", "Second")
        entity2.get_custom_fields = MagicMock(return_value={"active": "false"})

        entity3 = make_business_entity("3", "Third")
        entity3.get_custom_fields = MagicMock(return_value={"active": "true"})

        children = [entity1, entity2, entity3]
        selector = EntitySelector()
        result = selector.select_all(children, FieldPredicate("active", "true"))
        assert len(result) == 2
        assert result == [entity1, entity3]


class TestProcessSelector:
    """Tests for ProcessSelector."""

    def test_select_current_newest(self) -> None:
        """Test selecting newest process."""
        proc1 = Process(
            gid="1",
            name="Older",
            resource_type="task",
            created_at="2024-01-01T00:00:00Z",
            completed=False,
        )
        proc2 = Process(
            gid="2",
            name="Newer",
            resource_type="task",
            created_at="2024-02-01T00:00:00Z",
            completed=False,
        )

        selector = ProcessSelector()
        result = selector.select_current([proc1, proc2])
        assert result == proc2

    def test_select_current_incomplete_over_completed(self) -> None:
        """Test incomplete process wins over newer completed."""
        proc1 = Process(
            gid="1",
            name="Older Incomplete",
            resource_type="task",
            created_at="2024-01-01T00:00:00Z",
            completed=False,
        )
        proc2 = Process(
            gid="2",
            name="Newer Completed",
            resource_type="task",
            created_at="2024-02-01T00:00:00Z",
            completed=True,
        )

        selector = ProcessSelector()
        result = selector.select_current([proc1, proc2])
        assert result == proc1  # Incomplete beats completed

    def test_select_current_completed_if_all_completed(self) -> None:
        """Test newest completed is selected if all completed."""
        proc1 = Process(
            gid="1",
            name="Older",
            resource_type="task",
            created_at="2024-01-01T00:00:00Z",
            completed=True,
        )
        proc2 = Process(
            gid="2",
            name="Newer",
            resource_type="task",
            created_at="2024-02-01T00:00:00Z",
            completed=True,
        )

        selector = ProcessSelector()
        result = selector.select_current([proc1, proc2])
        assert result == proc2

    def test_select_current_with_process_type_filter(self) -> None:
        """Test filtering by process type."""
        # Create processes with memberships that will resolve to different types
        proc1 = Process(
            gid="1",
            name="Sales Process",
            resource_type="task",
            created_at="2024-01-01T00:00:00Z",
            completed=False,
            memberships=[
                {
                    "project": {
                        "gid": "sales-proj-123",
                        "name": "Sales Pipeline",
                        "resource_type": "project",
                    }
                }
            ],
        )

        proc2 = Process(
            gid="2",
            name="Onboarding Process",
            resource_type="task",
            created_at="2024-02-01T00:00:00Z",
            completed=False,
            memberships=[
                {
                    "project": {
                        "gid": "onboard-proj-456",
                        "name": "Onboarding Pipeline",
                        "resource_type": "project",
                    }
                }
            ],
        )

        selector = ProcessSelector()
        result = selector.select_current([proc1, proc2], ProcessType.SALES)
        assert result == proc1

    def test_select_current_returns_none_for_empty(self) -> None:
        """Test returns None for empty list."""
        selector = ProcessSelector()
        result = selector.select_current([])
        assert result is None

    def test_select_current_returns_none_for_no_match(self) -> None:
        """Test returns None when process type filter has no match."""
        proc = Process(
            gid="1",
            name="Sales",
            resource_type="task",
            created_at="2024-01-01T00:00:00Z",
            memberships=[
                {
                    "project": {
                        "gid": "sales-proj-123",
                        "name": "Sales Pipeline",
                        "resource_type": "project",
                    }
                }
            ],
        )

        selector = ProcessSelector()
        result = selector.select_current([proc], ProcessType.ONBOARDING)
        assert result is None
