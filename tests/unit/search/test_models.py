"""Tests for search models.

Per TDD-search-interface: Tests for SearchCriteria, SearchHit,
SearchResult, and FieldCondition models.
"""

from __future__ import annotations

from autom8_asana.search.models import (
    FieldCondition,
    SearchCriteria,
    SearchHit,
    SearchResult,
)


class TestFieldCondition:
    """Tests for FieldCondition model."""

    def test_default_operator_is_eq(self) -> None:
        """Default operator should be 'eq'."""
        condition = FieldCondition(field="Vertical", value="Medical")
        assert condition.operator == "eq"

    def test_eq_operator(self) -> None:
        """Should support equality operator."""
        condition = FieldCondition(field="Status", value="Active", operator="eq")
        assert condition.field == "Status"
        assert condition.value == "Active"
        assert condition.operator == "eq"

    def test_contains_operator(self) -> None:
        """Should support contains operator."""
        condition = FieldCondition(
            field="Description",
            value="important",
            operator="contains",
        )
        assert condition.operator == "contains"

    def test_in_operator_with_list(self) -> None:
        """Should support 'in' operator with list of values."""
        condition = FieldCondition(
            field="Status",
            value=["Active", "Pending"],
            operator="in",
        )
        assert condition.operator == "in"
        assert condition.value == ["Active", "Pending"]

    def test_value_can_be_list(self) -> None:
        """Value can be a list for OR matching."""
        condition = FieldCondition(
            field="Category",
            value=["A", "B", "C"],
        )
        assert condition.value == ["A", "B", "C"]


class TestSearchCriteria:
    """Tests for SearchCriteria model."""

    def test_minimal_criteria(self) -> None:
        """Minimal criteria requires project_gid."""
        criteria = SearchCriteria(project_gid="proj123")
        assert criteria.project_gid == "proj123"
        assert criteria.conditions == []
        assert criteria.combinator == "AND"
        assert criteria.entity_type is None
        assert criteria.limit is None

    def test_criteria_with_conditions(self) -> None:
        """Criteria with field conditions."""
        criteria = SearchCriteria(
            project_gid="proj123",
            conditions=[
                FieldCondition(field="Vertical", value="Medical"),
                FieldCondition(field="Status", value="Active"),
            ],
        )
        assert len(criteria.conditions) == 2
        assert criteria.conditions[0].field == "Vertical"

    def test_criteria_with_or_combinator(self) -> None:
        """Criteria with OR combinator."""
        criteria = SearchCriteria(
            project_gid="proj123",
            conditions=[
                FieldCondition(field="Status", value="Active"),
                FieldCondition(field="Status", value="Pending"),
            ],
            combinator="OR",
        )
        assert criteria.combinator == "OR"

    def test_criteria_with_entity_type(self) -> None:
        """Criteria with entity type filter."""
        criteria = SearchCriteria(
            project_gid="proj123",
            entity_type="Offer",
        )
        assert criteria.entity_type == "Offer"

    def test_criteria_with_limit(self) -> None:
        """Criteria with result limit."""
        criteria = SearchCriteria(
            project_gid="proj123",
            limit=10,
        )
        assert criteria.limit == 10


class TestSearchHit:
    """Tests for SearchHit model."""

    def test_minimal_hit(self) -> None:
        """Minimal hit requires GID."""
        hit = SearchHit(gid="task123")
        assert hit.gid == "task123"
        assert hit.entity_type is None
        assert hit.name is None
        assert hit.matched_fields == {}

    def test_hit_with_all_fields(self) -> None:
        """Hit with all fields populated."""
        hit = SearchHit(
            gid="task123",
            entity_type="Offer",
            name="Medical Clinic Offer",
            matched_fields={
                "Vertical": "Medical",
                "Status": "Active",
            },
        )
        assert hit.gid == "task123"
        assert hit.entity_type == "Offer"
        assert hit.name == "Medical Clinic Offer"
        assert hit.matched_fields["Vertical"] == "Medical"
        assert hit.matched_fields["Status"] == "Active"


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_empty_result(self) -> None:
        """Empty result with defaults."""
        result = SearchResult()
        assert result.hits == []
        assert result.total_count == 0
        assert result.query_time_ms == 0.0
        assert result.from_cache is False

    def test_result_with_hits(self) -> None:
        """Result with hits."""
        result = SearchResult(
            hits=[
                SearchHit(gid="task1", name="Task 1"),
                SearchHit(gid="task2", name="Task 2"),
            ],
            total_count=2,
            query_time_ms=1.5,
            from_cache=True,
        )
        assert len(result.hits) == 2
        assert result.total_count == 2
        assert result.query_time_ms == 1.5
        assert result.from_cache is True

    def test_result_iteration(self) -> None:
        """Can iterate over hits."""
        result = SearchResult(
            hits=[
                SearchHit(gid="task1"),
                SearchHit(gid="task2"),
                SearchHit(gid="task3"),
            ],
            total_count=3,
        )
        gids = [hit.gid for hit in result.hits]
        assert gids == ["task1", "task2", "task3"]
