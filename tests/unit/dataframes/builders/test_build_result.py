"""Unit tests for SectionResult, BuildResult, and BuildQuality.

Per TDD-PARTIAL-FAILURE-SIGNALING-001 test strategy:
Tests data types, status classification, computed properties,
immutability, backward compatibility, and DataFrameCache integration.
"""

from __future__ import annotations

from datetime import UTC, datetime

import polars as pl
import pytest

from autom8_asana.dataframes.builders.build_result import (
    BuildQuality,
    BuildResult,
    BuildStatus,
    SectionOutcome,
    SectionResult,
)

# ---------------------------------------------------------------------------
# SectionResult unit tests
# ---------------------------------------------------------------------------


class TestSectionResult:
    """Tests for SectionResult dataclass."""

    def test_section_result_success(self) -> None:
        """SUCCESS outcome with row count and timing."""
        result = SectionResult(
            section_gid="sec-1",
            outcome=SectionOutcome.SUCCESS,
            row_count=42,
            fetch_time_ms=1250.5,
            watermark=datetime(2026, 2, 4, tzinfo=UTC),
        )
        assert result.section_gid == "sec-1"
        assert result.outcome == SectionOutcome.SUCCESS
        assert result.row_count == 42
        assert result.fetch_time_ms == 1250.5
        assert result.watermark is not None
        assert result.error_message is None
        assert result.error_type is None
        assert result.resumed is False

    def test_section_result_error(self) -> None:
        """ERROR outcome with error_message and error_type."""
        result = SectionResult(
            section_gid="sec-2",
            outcome=SectionOutcome.ERROR,
            fetch_time_ms=500.0,
            error_message="429 Too Many Requests",
            error_type="AsanaAPIError",
        )
        assert result.outcome == SectionOutcome.ERROR
        assert result.row_count == 0
        assert result.error_message == "429 Too Many Requests"
        assert result.error_type == "AsanaAPIError"
        assert result.watermark is None

    def test_section_result_skipped(self) -> None:
        """SKIPPED outcome with resumed=True."""
        result = SectionResult(
            section_gid="sec-3",
            outcome=SectionOutcome.SKIPPED,
            resumed=True,
        )
        assert result.outcome == SectionOutcome.SKIPPED
        assert result.resumed is True
        assert result.row_count == 0
        assert result.fetch_time_ms == 0.0

    def test_section_result_is_success_property(self) -> None:
        """is_success returns True only for SUCCESS."""
        success = SectionResult(section_gid="s", outcome=SectionOutcome.SUCCESS)
        error = SectionResult(section_gid="s", outcome=SectionOutcome.ERROR)
        skipped = SectionResult(section_gid="s", outcome=SectionOutcome.SKIPPED)
        assert success.is_success is True
        assert error.is_success is False
        assert skipped.is_success is False

    def test_section_result_is_error_property(self) -> None:
        """is_error returns True only for ERROR."""
        success = SectionResult(section_gid="s", outcome=SectionOutcome.SUCCESS)
        error = SectionResult(section_gid="s", outcome=SectionOutcome.ERROR)
        skipped = SectionResult(section_gid="s", outcome=SectionOutcome.SKIPPED)
        assert success.is_error is False
        assert error.is_error is True
        assert skipped.is_error is False

    def test_section_result_frozen(self) -> None:
        """Cannot mutate fields after creation."""
        result = SectionResult(
            section_gid="sec-1",
            outcome=SectionOutcome.SUCCESS,
            row_count=10,
        )
        with pytest.raises(AttributeError):
            result.row_count = 20  # type: ignore[misc]

    def test_section_result_slots(self) -> None:
        """Instance has __slots__ (memory efficient)."""
        result = SectionResult(section_gid="s", outcome=SectionOutcome.SUCCESS)
        assert hasattr(result, "__slots__")


# ---------------------------------------------------------------------------
# BuildResult unit tests
# ---------------------------------------------------------------------------


class TestBuildResult:
    """Tests for BuildResult dataclass."""

    @pytest.fixture
    def empty_df(self) -> pl.DataFrame:
        return pl.DataFrame({"gid": []})

    @pytest.fixture
    def sample_df(self) -> pl.DataFrame:
        return pl.DataFrame({"gid": ["1", "2", "3"]})

    @pytest.fixture
    def now(self) -> datetime:
        return datetime.now(UTC)

    def _make_success(self, gid: str, row_count: int = 10) -> SectionResult:
        return SectionResult(
            section_gid=gid,
            outcome=SectionOutcome.SUCCESS,
            row_count=row_count,
            fetch_time_ms=100.0,
        )

    def _make_error(self, gid: str, error_type: str = "AsanaAPIError") -> SectionResult:
        return SectionResult(
            section_gid=gid,
            outcome=SectionOutcome.ERROR,
            fetch_time_ms=50.0,
            error_message="Something failed",
            error_type=error_type,
        )

    def _make_skipped(self, gid: str, resumed: bool = False) -> SectionResult:
        return SectionResult(
            section_gid=gid,
            outcome=SectionOutcome.SKIPPED,
            resumed=resumed,
        )

    def test_build_result_success_status(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """All SUCCESS sections -> BuildStatus.SUCCESS."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1", 20),
                self._make_success("s2", 30),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=5000.0,
            fetch_time_ms=4000.0,
        )
        assert result.status == BuildStatus.SUCCESS

    def test_build_result_partial_status(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """Mix of SUCCESS and ERROR -> BuildStatus.PARTIAL."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1"),
                self._make_error("s2"),
                self._make_success("s3"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=5000.0,
            fetch_time_ms=4000.0,
        )
        assert result.status == BuildStatus.PARTIAL

    def test_build_result_failure_status(
        self, empty_df: pl.DataFrame, now: datetime
    ) -> None:
        """All ERROR sections -> BuildStatus.FAILURE."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_error("s1"),
                self._make_error("s2"),
            ],
            dataframe=empty_df,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=5000.0,
            fetch_time_ms=4000.0,
        )
        assert result.status == BuildStatus.FAILURE

    def test_build_result_no_sections(
        self, empty_df: pl.DataFrame, now: datetime
    ) -> None:
        """Empty sections list -> SUCCESS (empty DataFrame)."""
        result = BuildResult.from_section_results(
            section_results=[],
            dataframe=empty_df,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=100.0,
            fetch_time_ms=0.0,
        )
        assert result.status == BuildStatus.SUCCESS
        assert result.sections == ()

    def test_build_result_only_skipped(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """All SKIPPED (resumed) -> SUCCESS."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_skipped("s1", resumed=True),
                self._make_skipped("s2", resumed=True),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=500.0,
            fetch_time_ms=0.0,
        )
        assert result.status == BuildStatus.SUCCESS

    def test_build_result_skipped_plus_error(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """SKIPPED + ERROR without SUCCESS -> FAILURE."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_skipped("s1", resumed=True),
                self._make_error("s2"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=500.0,
            fetch_time_ms=200.0,
        )
        assert result.status == BuildStatus.FAILURE

    def test_build_result_none_dataframe(self, now: datetime) -> None:
        """None DataFrame -> FAILURE regardless of sections."""
        result = BuildResult.from_section_results(
            section_results=[self._make_success("s1")],
            dataframe=None,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=500.0,
            fetch_time_ms=200.0,
        )
        assert result.status == BuildStatus.FAILURE

    def test_build_result_sections_succeeded(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """sections_succeeded counts correctly."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1"),
                self._make_error("s2"),
                self._make_success("s3"),
                self._make_skipped("s4"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.sections_succeeded == 2

    def test_build_result_sections_failed(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """sections_failed counts correctly."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1"),
                self._make_error("s2"),
                self._make_error("s3"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.sections_failed == 2

    def test_build_result_sections_resumed(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """sections_resumed counts resumed flag."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_skipped("s1", resumed=True),
                self._make_skipped("s2", resumed=True),
                self._make_success("s3"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.sections_resumed == 2

    def test_build_result_total_rows(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """total_rows sums only SUCCESS sections."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1", row_count=20),
                self._make_error("s2"),
                self._make_success("s3", row_count=30),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.total_rows == 50

    def test_build_result_failed_section_gids(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """Returns GIDs of ERROR sections."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1"),
                self._make_error("s2"),
                self._make_error("s3"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.failed_section_gids == ["s2", "s3"]

    def test_build_result_error_summary(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """Groups errors by type correctly."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1"),
                self._make_error("s2", error_type="AsanaAPIError"),
                self._make_error("s3", error_type="S3TransportError"),
                self._make_error("s4", error_type="AsanaAPIError"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.error_summary == {
            "AsanaAPIError": 2,
            "S3TransportError": 1,
        }

    def test_build_result_error_summary_empty(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """error_summary is empty dict when no errors."""
        result = BuildResult.from_section_results(
            section_results=[self._make_success("s1")],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.error_summary == {}

    def test_build_result_is_usable(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """True for SUCCESS and PARTIAL, False for FAILURE."""
        success = BuildResult.from_section_results(
            section_results=[self._make_success("s1")],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        partial = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1"),
                self._make_error("s2"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        failure = BuildResult.from_section_results(
            section_results=[self._make_error("s1")],
            dataframe=None,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert success.is_usable is True
        assert partial.is_usable is True
        assert failure.is_usable is False

    def test_build_result_to_legacy(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """Converts to ProgressiveBuildResult correctly."""
        from autom8_asana.dataframes.builders.progressive import (
            ProgressiveBuildResult,
        )

        result = BuildResult.from_section_results(
            section_results=[
                self._make_skipped("s1", resumed=True),
                self._make_success("s2", row_count=25),
                self._make_success("s3", row_count=15),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=5000.0,
            fetch_time_ms=3000.0,
            sections_probed=2,
            sections_delta_updated=1,
        )
        legacy = result.to_legacy()

        assert isinstance(legacy, ProgressiveBuildResult)
        assert legacy.df is sample_df
        assert legacy.watermark == now
        assert legacy.total_rows == 40  # 25 + 15
        assert legacy.sections_fetched == 2  # succeeded count
        assert legacy.sections_resumed == 1
        assert legacy.fetch_time_ms == 3000.0
        assert legacy.total_time_ms == 5000.0
        assert legacy.sections_probed == 2
        assert legacy.sections_delta_updated == 1

    def test_build_result_to_legacy_failure(self, now: datetime) -> None:
        """to_legacy on FAILURE returns empty DataFrame."""
        result = BuildResult.from_section_results(
            section_results=[self._make_error("s1")],
            dataframe=None,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=100.0,
            fetch_time_ms=50.0,
        )
        legacy = result.to_legacy()
        assert len(legacy.df) == 0
        assert legacy.total_rows == 0

    def test_build_result_from_section_results(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """Factory classifies status correctly for mixed results."""
        result = BuildResult.from_section_results(
            section_results=[
                self._make_success("s1", row_count=10),
                self._make_error("s2"),
            ],
            dataframe=sample_df,
            watermark=now,
            project_gid="proj-1",
            entity_type="offer",
            total_time_ms=5000.0,
            fetch_time_ms=4000.0,
            sections_probed=5,
            sections_delta_updated=2,
        )
        assert result.status == BuildStatus.PARTIAL
        assert result.project_gid == "proj-1"
        assert result.entity_type == "offer"
        assert result.total_time_ms == 5000.0
        assert result.fetch_time_ms == 4000.0
        assert result.sections_probed == 5
        assert result.sections_delta_updated == 2

    def test_build_result_frozen(self, sample_df: pl.DataFrame, now: datetime) -> None:
        """Cannot mutate fields."""
        result = BuildResult(
            status=BuildStatus.SUCCESS,
            sections=(),
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        with pytest.raises(AttributeError):
            result.status = BuildStatus.FAILURE  # type: ignore[misc]

    def test_build_result_sections_is_tuple(
        self, sample_df: pl.DataFrame, now: datetime
    ) -> None:
        """Sections are stored as immutable tuple."""
        result = BuildResult.from_section_results(
            section_results=[self._make_success("s1")],
            dataframe=sample_df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert isinstance(result.sections, tuple)


# ---------------------------------------------------------------------------
# BuildQuality unit tests
# ---------------------------------------------------------------------------


class TestBuildQuality:
    """Tests for BuildQuality dataclass."""

    def test_build_quality_from_build_result(self) -> None:
        """from_build_result extracts correct metadata."""
        now = datetime.now(UTC)
        df = pl.DataFrame({"gid": ["1"]})

        build_result = BuildResult.from_section_results(
            section_results=[
                SectionResult(
                    section_gid="s1",
                    outcome=SectionOutcome.SUCCESS,
                    row_count=10,
                ),
                SectionResult(
                    section_gid="s2",
                    outcome=SectionOutcome.ERROR,
                    error_message="fail",
                    error_type="AsanaAPIError",
                ),
            ],
            dataframe=df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        quality = BuildQuality.from_build_result(build_result)

        assert quality.status == "partial"
        assert quality.sections_total == 2
        assert quality.sections_succeeded == 1
        assert quality.sections_failed == 1
        assert quality.failed_section_gids == ("s2",)
        assert quality.error_summary == {"AsanaAPIError": 1}

    def test_build_quality_success(self) -> None:
        """Success build produces clean quality metadata."""
        now = datetime.now(UTC)
        df = pl.DataFrame({"gid": ["1"]})

        build_result = BuildResult.from_section_results(
            section_results=[
                SectionResult(
                    section_gid="s1",
                    outcome=SectionOutcome.SUCCESS,
                    row_count=10,
                ),
            ],
            dataframe=df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        quality = BuildQuality.from_build_result(build_result)

        assert quality.status == "success"
        assert quality.sections_failed == 0
        assert quality.failed_section_gids == ()
        assert quality.error_summary is None  # empty dict -> None

    def test_build_quality_frozen(self) -> None:
        """Cannot mutate fields after creation."""
        quality = BuildQuality(
            status="success",
            sections_total=1,
            sections_succeeded=1,
            sections_failed=0,
        )
        with pytest.raises(AttributeError):
            quality.status = "partial"  # type: ignore[misc]

    def test_build_quality_slots(self) -> None:
        """Instance has __slots__ (memory efficient)."""
        quality = BuildQuality(
            status="success",
            sections_total=1,
            sections_succeeded=1,
            sections_failed=0,
        )
        assert hasattr(quality, "__slots__")


# ---------------------------------------------------------------------------
# SectionOutcome and BuildStatus enum tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Tests for SectionOutcome and BuildStatus enums."""

    def test_section_outcome_values(self) -> None:
        assert SectionOutcome.SUCCESS.value == "success"
        assert SectionOutcome.ERROR.value == "error"
        assert SectionOutcome.SKIPPED.value == "skipped"

    def test_build_status_values(self) -> None:
        assert BuildStatus.SUCCESS.value == "success"
        assert BuildStatus.PARTIAL.value == "partial"
        assert BuildStatus.FAILURE.value == "failure"

    def test_enums_are_str(self) -> None:
        """Enums are str subclasses for JSON serialization."""
        assert isinstance(SectionOutcome.SUCCESS, str)
        assert isinstance(BuildStatus.SUCCESS, str)


# ---------------------------------------------------------------------------
# Classification edge cases
# ---------------------------------------------------------------------------


class TestClassificationEdgeCases:
    """Edge cases for status classification logic."""

    @pytest.fixture
    def now(self) -> datetime:
        return datetime.now(UTC)

    @pytest.fixture
    def df(self) -> pl.DataFrame:
        return pl.DataFrame({"gid": ["1"]})

    def test_skipped_not_resumed_is_success(
        self, df: pl.DataFrame, now: datetime
    ) -> None:
        """SKIPPED without resumed flag still classified as SUCCESS."""
        result = BuildResult.from_section_results(
            section_results=[
                SectionResult(
                    section_gid="s1",
                    outcome=SectionOutcome.SKIPPED,
                    resumed=False,
                ),
            ],
            dataframe=df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=0.0,
        )
        assert result.status == BuildStatus.SUCCESS

    def test_success_plus_skipped_is_success(
        self, df: pl.DataFrame, now: datetime
    ) -> None:
        """SUCCESS + SKIPPED (no ERROR) -> SUCCESS."""
        result = BuildResult.from_section_results(
            section_results=[
                SectionResult(
                    section_gid="s1",
                    outcome=SectionOutcome.SUCCESS,
                    row_count=5,
                ),
                SectionResult(
                    section_gid="s2",
                    outcome=SectionOutcome.SKIPPED,
                    resumed=True,
                ),
            ],
            dataframe=df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.status == BuildStatus.SUCCESS

    def test_all_three_outcomes_is_partial(
        self, df: pl.DataFrame, now: datetime
    ) -> None:
        """SUCCESS + ERROR + SKIPPED -> PARTIAL (has_success and has_error)."""
        result = BuildResult.from_section_results(
            section_results=[
                SectionResult(
                    section_gid="s1",
                    outcome=SectionOutcome.SUCCESS,
                    row_count=10,
                ),
                SectionResult(
                    section_gid="s2",
                    outcome=SectionOutcome.ERROR,
                    error_type="X",
                ),
                SectionResult(
                    section_gid="s3",
                    outcome=SectionOutcome.SKIPPED,
                    resumed=True,
                ),
            ],
            dataframe=df,
            watermark=now,
            project_gid="p",
            entity_type="e",
            total_time_ms=1.0,
            fetch_time_ms=1.0,
        )
        assert result.status == BuildStatus.PARTIAL
