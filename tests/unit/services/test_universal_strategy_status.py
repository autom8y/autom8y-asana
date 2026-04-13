"""Unit tests for status-aware entity resolution in UniversalResolutionStrategy.

Per TDD-STATUS-AWARE-RESOLUTION:
Tests for _classify_gids(), active_only filtering, ACTIVITY_PRIORITY sorting,
and no-classifier graceful degradation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from autom8_asana.models.business.activity import AccountActivity
from autom8_asana.services.dynamic_index import DynamicIndexCache
from autom8_asana.services.universal_strategy import (
    _ACTIVE_STATUSES,
    _PRIORITY_MAP,
    _UNKNOWN_PRIORITY,
    UniversalResolutionStrategy,
    reset_shared_index_cache,
)

# ---------------------------------------------------------------------------
# Test DataFrames
# ---------------------------------------------------------------------------


def make_unit_df_with_status() -> pl.DataFrame:
    """Create a Unit DataFrame with section and is_completed columns."""
    return pl.DataFrame(
        {
            "gid": [
                "u-active",
                "u-activating",
                "u-inactive",
                "u-ignored",
                "u-null-section",
                "u-completed",
            ],
            "office_phone": [
                "+11111111111",
                "+12222222222",
                "+13333333333",
                "+14444444444",
                "+15555555555",
                "+16666666666",
            ],
            "vertical": [
                "dental",
                "dental",
                "dental",
                "dental",
                "dental",
                "dental",
            ],
            "section": [
                "Active",
                "Onboarding",
                "Paused",
                "Templates",
                None,
                "Active",
            ],
            "is_completed": [False, False, False, False, False, True],
            "name": [
                "Active Unit",
                "Activating Unit",
                "Inactive Unit",
                "Ignored Unit",
                "Null Section Unit",
                "Completed Unit",
            ],
        }
    )


@pytest.fixture
def unit_status_df() -> pl.DataFrame:
    """Fixture for Unit DataFrame with status-relevant columns."""
    return make_unit_df_with_status()


@pytest.fixture
def index_cache() -> DynamicIndexCache:
    """Fixture for fresh DynamicIndexCache."""
    return DynamicIndexCache(max_per_entity=5, ttl_seconds=3600)


@pytest.fixture
def mock_client() -> MagicMock:
    """Fixture for mock AsanaClient."""
    client = MagicMock()
    client.unified_store = MagicMock()
    return client


@pytest.fixture(autouse=True)
def cleanup() -> None:  # type: ignore[misc]
    """Clean up shared state after each test."""
    yield  # type: ignore[misc]
    reset_shared_index_cache()


# ---------------------------------------------------------------------------
# Classification Tests
# ---------------------------------------------------------------------------


class TestClassifyGids:
    """Tests for _classify_gids() method.

    Per TDD-STATUS-AWARE-RESOLUTION / FR-2, FR-5, FR-6, FR-7.
    """

    def test_classify_gids_active_section(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Section 'Active' -> AccountActivity.ACTIVE.value.

        Per FR-2: SectionClassifier maps section names to AccountActivity.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["u-active"], "unit")

        assert len(result) == 1
        assert result[0] == ("u-active", AccountActivity.ACTIVE.value)

    def test_classify_gids_activating_section(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Section 'Onboarding' -> 'activating'.

        Per FR-2, FR-3: Activating sections classified correctly.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["u-activating"], "unit")

        assert result[0] == ("u-activating", "activating")

    def test_classify_gids_inactive_section(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Section 'Paused' -> 'inactive'.

        Per FR-2: Inactive sections classified correctly.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["u-inactive"], "unit")

        assert result[0] == ("u-inactive", "inactive")

    def test_classify_gids_ignored_section(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Section 'Templates' -> 'ignored'.

        Per FR-2: Ignored sections classified correctly.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["u-ignored"], "unit")

        assert result[0] == ("u-ignored", "ignored")

    def test_classify_gids_null_section_returns_none(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """section=None -> None (UNKNOWN).

        Per FR-5, SCAR-005/006: Null section from cascade warming gaps.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["u-null-section"], "unit")

        assert result[0] == ("u-null-section", None)

    def test_classify_gids_unknown_section_name_returns_none(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """Section 'New Section XYZ' -> None (UNKNOWN).

        Per EC-9: Unrecognized section name not in classifier mapping.
        """
        df = pl.DataFrame(
            {
                "gid": ["u-unknown"],
                "section": ["New Section XYZ"],
                "is_completed": [False],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(df, ["u-unknown"], "unit")

        assert result[0] == ("u-unknown", None)

    def test_classify_gids_completed_overrides_active_section(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """is_completed=True + section 'Active' -> 'inactive'.

        Per FR-6, SD-6: is_completed is terminal override.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["u-completed"], "unit")

        # u-completed has section="Active" but is_completed=True
        assert result[0] == ("u-completed", AccountActivity.INACTIVE.value)

    def test_classify_gids_completed_overrides_null_section(
        self, index_cache: DynamicIndexCache
    ) -> None:
        """is_completed=True + section=None -> 'inactive'.

        Per FR-6: Completion override applies even when section is null.
        """
        df = pl.DataFrame(
            {
                "gid": ["u-comp-null"],
                "section": [None],
                "is_completed": [True],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(df, ["u-comp-null"], "unit")

        assert result[0] == ("u-comp-null", "inactive")

    def test_classify_gids_no_classifier_returns_all_none(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """get_classifier() returns None -> all None.

        Per FR-7: No classifier for entity type.
        """
        strategy = UniversalResolutionStrategy(entity_type="business", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["u-active", "u-inactive"], "business")

        assert all(status is None for _, status in result)
        assert len(result) == 2

    def test_classify_gids_gid_not_in_dataframe_returns_none(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """GID from index not found in DF (defensive) -> None.

        Per SCAR-005: Missing data treated as unclassifiable.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(unit_status_df, ["nonexistent-gid"], "unit")

        assert result[0] == ("nonexistent-gid", None)

    def test_classify_gids_mixed_statuses(
        self, unit_status_df: pl.DataFrame, index_cache: DynamicIndexCache
    ) -> None:
        """Mix of ACTIVE, INACTIVE, null -> correct per-GID classification.

        Per FR-2: Each GID classified independently.
        """
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        gids = ["u-active", "u-inactive", "u-null-section", "u-completed"]
        result = strategy._classify_gids(unit_status_df, gids, "unit")

        assert result[0] == ("u-active", "active")
        assert result[1] == ("u-inactive", "inactive")
        assert result[2] == ("u-null-section", None)
        assert result[3] == ("u-completed", "inactive")

    def test_classify_gids_case_insensitive_section(self, index_cache: DynamicIndexCache) -> None:
        """Section 'active' vs 'Active' vs 'ACTIVE' all classify correctly.

        Per NFR-2: SectionClassifier uses case-insensitive matching.
        The classifier lowercases the section name before lookup, so any
        case variant that matches a lowercase key should classify correctly.
        """
        # The UNIT_CLASSIFIER has "active" (lowercase) in its mapping.
        # SectionClassifier.classify() lowercases the input.
        df = pl.DataFrame(
            {
                "gid": ["g1", "g2"],
                "section": ["active", "ACTIVE"],
                "is_completed": [False, False],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)

        result = strategy._classify_gids(df, ["g1", "g2"], "unit")

        assert result[0][1] == "active"
        assert result[1][1] == "active"


# ---------------------------------------------------------------------------
# Filtering and Sorting Tests
# ---------------------------------------------------------------------------


class TestFilteringAndSorting:
    """Tests for active_only filtering and ACTIVITY_PRIORITY sorting.

    Per TDD-STATUS-AWARE-RESOLUTION / FR-1, FR-8, FR-9, FR-11.
    """

    @pytest.mark.asyncio
    async def test_active_only_true_filters_inactive_and_ignored(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """Only ACTIVE + ACTIVATING remain when active_only=True.

        Per FR-1: active_only filters to active statuses.
        """
        df = make_unit_df_with_status()
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"office_phone": "+11111111111"},
                errors=[],
            )
            # Build an index that returns multiple GIDs
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(
                df=df,
                key_columns=["office_phone"],
                value_column="gid",
            )
            # Manually add all GIDs to be returned for a single phone lookup
            # Instead, use the full DataFrame with vertical="dental" as key
            strategy._cached_dataframe = df

            # Use vertical=dental which matches all 6 rows
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"vertical": "dental"},
                errors=[],
            )
            index = DynamicIndex.from_dataframe(
                df=df,
                key_columns=["vertical"],
                value_column="gid",
            )
            index_cache.put(
                entity_type="unit",
                key_columns=["vertical"],
                index=index,
            )

            results = await strategy.resolve(
                criteria=[{"vertical": "dental"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        assert len(results) == 1
        result = results[0]
        # Only ACTIVE and ACTIVATING should remain
        assert result.status_annotations is not None
        for status in result.status_annotations:
            assert status in _ACTIVE_STATUSES
        # u-inactive, u-ignored, u-null-section, u-completed should be filtered
        assert result.match_count == 2
        assert set(result.gids) == {"u-active", "u-activating"}

    @pytest.mark.asyncio
    async def test_active_only_true_filters_unknown_null_status(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """None status excluded from active_only=True results.

        Per FR-5, SD-5: UNKNOWN (None) excluded from active-only.
        """
        df = pl.DataFrame(
            {
                "gid": ["g-null"],
                "vertical": ["dental"],
                "section": [None],
                "is_completed": [False],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"vertical": "dental"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["vertical"], value_column="gid")
            index_cache.put(entity_type="unit", key_columns=["vertical"], index=index)

            results = await strategy.resolve(
                criteria=[{"vertical": "dental"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        assert results[0].error == "NOT_FOUND"
        assert results[0].gid is None

    @pytest.mark.asyncio
    async def test_active_only_true_all_inactive_returns_not_found(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """All filtered out -> NOT_FOUND.

        Per EC-1, FR-9: Empty after filtering returns NOT_FOUND.
        """
        df = pl.DataFrame(
            {
                "gid": ["g1", "g2"],
                "vertical": ["dental", "dental"],
                "section": ["Paused", "Cancelled"],
                "is_completed": [False, False],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"vertical": "dental"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["vertical"], value_column="gid")
            index_cache.put(entity_type="unit", key_columns=["vertical"], index=index)

            results = await strategy.resolve(
                criteria=[{"vertical": "dental"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        assert results[0].error == "NOT_FOUND"
        assert results[0].match_count == 0

    @pytest.mark.asyncio
    async def test_active_only_false_returns_all_with_annotations(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """All GIDs returned, each annotated when active_only=False.

        Per US-2: Diagnostic mode returns all matches with status.
        """
        df = make_unit_df_with_status()
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"vertical": "dental"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["vertical"], value_column="gid")
            index_cache.put(entity_type="unit", key_columns=["vertical"], index=index)

            results = await strategy.resolve(
                criteria=[{"vertical": "dental"}],
                project_gid="test-project",
                client=mock_client,
                active_only=False,
            )

        result = results[0]
        assert result.status_annotations is not None
        assert result.match_count == 6
        assert len(result.gids) == 6
        assert len(result.status_annotations) == 6
        # total_match_count is None when active_only=False
        assert result.total_match_count is None

    def test_sort_order_active_before_activating(self) -> None:
        """ACTIVE sorts before ACTIVATING.

        Per FR-8: ACTIVITY_PRIORITY ordering.
        """
        assert _PRIORITY_MAP["active"] < _PRIORITY_MAP["activating"]

    def test_sort_order_unknown_last(self) -> None:
        """None status sorts after IGNORED.

        Per FR-8, AC-5.4: UNKNOWN sorts last.
        """
        assert _PRIORITY_MAP["ignored"] < _UNKNOWN_PRIORITY
        assert _PRIORITY_MAP["inactive"] < _UNKNOWN_PRIORITY
        assert _PRIORITY_MAP["active"] < _UNKNOWN_PRIORITY

    def test_sort_preserves_intra_priority_order(self) -> None:
        """Two ACTIVE GIDs maintain original order.

        Per AC-4.4: Stable sort within same priority level.
        """
        # Verify Python's sort is stable by checking the priority map
        # produces equal keys for same-status items
        pairs = [
            ("gid-first", "active"),
            ("gid-second", "active"),
            ("gid-third", "activating"),
        ]
        sorted_pairs = sorted(
            pairs,
            key=lambda p: _PRIORITY_MAP.get(p[1], _UNKNOWN_PRIORITY),
        )

        # ACTIVE items preserve original order
        assert sorted_pairs[0][0] == "gid-first"
        assert sorted_pairs[1][0] == "gid-second"
        assert sorted_pairs[2][0] == "gid-third"

    @pytest.mark.asyncio
    async def test_mixed_status_six_gids_sorted_and_filtered(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """EC-6: 1 ACTIVE + 1 ACTIVATING + 2 INACTIVE = 2 returned.

        Per EC-6: Mixed statuses filtered and sorted correctly.
        """
        df = pl.DataFrame(
            {
                "gid": ["g-act", "g-ing", "g-ina1", "g-ina2"],
                "vertical": ["dental", "dental", "dental", "dental"],
                "section": ["Active", "Onboarding", "Paused", "Cancelled"],
                "is_completed": [False, False, False, False],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"vertical": "dental"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["vertical"], value_column="gid")
            index_cache.put(entity_type="unit", key_columns=["vertical"], index=index)

            results = await strategy.resolve(
                criteria=[{"vertical": "dental"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        result = results[0]
        assert result.match_count == 2
        assert result.gids[0] == "g-act"  # ACTIVE first
        assert result.gids[1] == "g-ing"  # ACTIVATING second
        assert result.total_match_count == 4  # Pre-filter count

    @pytest.mark.asyncio
    async def test_total_match_count_set_when_active_only(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """total_match_count = pre-filter count when active_only=True.

        Per FR-11: Diagnostic metadata.
        """
        df = pl.DataFrame(
            {
                "gid": ["g1", "g2", "g3"],
                "vertical": ["dental", "dental", "dental"],
                "section": ["Active", "Paused", "Cancelled"],
                "is_completed": [False, False, False],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"vertical": "dental"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["vertical"], value_column="gid")
            index_cache.put(entity_type="unit", key_columns=["vertical"], index=index)

            results = await strategy.resolve(
                criteria=[{"vertical": "dental"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        result = results[0]
        assert result.total_match_count == 3  # All 3 before filtering
        assert result.match_count == 1  # Only Active passes filter

    @pytest.mark.asyncio
    async def test_total_match_count_null_when_active_only_false(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """total_match_count = None when active_only=False.

        Per FR-11: No filtering -> no pre-filter count needed.
        """
        df = pl.DataFrame(
            {
                "gid": ["g1", "g2"],
                "vertical": ["dental", "dental"],
                "section": ["Active", "Paused"],
                "is_completed": [False, False],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="unit", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"vertical": "dental"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["vertical"], value_column="gid")
            index_cache.put(entity_type="unit", key_columns=["vertical"], index=index)

            results = await strategy.resolve(
                criteria=[{"vertical": "dental"}],
                project_gid="test-project",
                client=mock_client,
                active_only=False,
            )

        result = results[0]
        assert result.total_match_count is None
        assert result.match_count == 2


# ---------------------------------------------------------------------------
# No-Classifier Degradation Tests
# ---------------------------------------------------------------------------


class TestNoClassifierDegradation:
    """Tests for graceful degradation when no classifier exists.

    Per TDD-STATUS-AWARE-RESOLUTION / FR-7.
    """

    @pytest.mark.asyncio
    async def test_no_classifier_active_only_ignored(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """active_only=True but no classifier -> all returned.

        Per FR-7, AC-7.1: active_only effectively ignored.
        """
        df = pl.DataFrame(
            {
                "gid": ["g1", "g2"],
                "name": ["Entity A", "Entity B"],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="business", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"name": "Entity A"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["name"], value_column="gid")
            index_cache.put(entity_type="business", key_columns=["name"], index=index)

            results = await strategy.resolve(
                criteria=[{"name": "Entity A"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        result = results[0]
        assert result.gid == "g1"
        assert result.match_count == 1

    @pytest.mark.asyncio
    async def test_no_classifier_no_status_annotations(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """status_annotations is None when no classifier.

        Per AC-7.2: No annotations produced.
        """
        df = pl.DataFrame(
            {
                "gid": ["g1"],
                "name": ["Entity A"],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="business", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"name": "Entity A"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["name"], value_column="gid")
            index_cache.put(entity_type="business", key_columns=["name"], index=index)

            results = await strategy.resolve(
                criteria=[{"name": "Entity A"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        assert results[0].status_annotations is None

    @pytest.mark.asyncio
    async def test_no_classifier_gid_returns_first(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """gid = gids[0] (not priority-sorted) when no classifier.

        Per AC-7.3: Preserves existing order.
        """
        df = pl.DataFrame(
            {
                "gid": ["g1", "g2"],
                "category": ["cat-a", "cat-a"],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="business", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"category": "cat-a"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["category"], value_column="gid")
            index_cache.put(entity_type="business", key_columns=["category"], index=index)

            results = await strategy.resolve(
                criteria=[{"category": "cat-a"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        result = results[0]
        assert result.gid == result.gids[0]

    @pytest.mark.asyncio
    async def test_no_classifier_no_error(
        self, index_cache: DynamicIndexCache, mock_client: MagicMock
    ) -> None:
        """No error in result when no classifier.

        Per AC-7.4: Graceful degradation, no error raised.
        """
        df = pl.DataFrame(
            {
                "gid": ["g1"],
                "name": ["Entity A"],
            }
        )
        strategy = UniversalResolutionStrategy(entity_type="business", index_cache=index_cache)
        strategy._cached_dataframe = df

        with patch("autom8_asana.services.resolver.validate_criterion_for_entity") as mock_validate:
            mock_validate.return_value = MagicMock(
                is_valid=True,
                normalized_criterion={"name": "Entity A"},
                errors=[],
            )
            from autom8_asana.services.dynamic_index import DynamicIndex

            index = DynamicIndex.from_dataframe(df=df, key_columns=["name"], value_column="gid")
            index_cache.put(entity_type="business", key_columns=["name"], index=index)

            results = await strategy.resolve(
                criteria=[{"name": "Entity A"}],
                project_gid="test-project",
                client=mock_client,
                active_only=True,
            )

        assert results[0].error is None
