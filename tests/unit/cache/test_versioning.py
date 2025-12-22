"""Tests for version comparison utilities."""

from datetime import datetime, timezone

import pytest

from autom8_asana.cache.versioning import (
    compare_versions,
    format_version,
    is_current,
    is_stale,
    parse_version,
    version_to_timestamp,
)


class TestCompareVersions:
    """Tests for compare_versions function."""

    def test_cached_older_than_current(self) -> None:
        """Test returns -1 when cached is older."""
        cached = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        assert compare_versions(cached, current) == -1

    def test_cached_newer_than_current(self) -> None:
        """Test returns 1 when cached is newer."""
        cached = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        assert compare_versions(cached, current) == 1

    def test_cached_equals_current(self) -> None:
        """Test returns 0 when versions are equal."""
        version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        assert compare_versions(version, version) == 0

    def test_compare_string_versions(self) -> None:
        """Test comparing string versions."""
        cached = "2025-01-01T10:00:00+00:00"
        current = "2025-01-01T12:00:00+00:00"

        assert compare_versions(cached, current) == -1

    def test_compare_mixed_versions(self) -> None:
        """Test comparing datetime and string versions."""
        cached = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        current = "2025-01-01T12:00:00+00:00"

        assert compare_versions(cached, current) == -1

    def test_compare_with_z_suffix(self) -> None:
        """Test comparing versions with Z suffix."""
        cached = "2025-01-01T10:00:00Z"
        current = "2025-01-01T12:00:00Z"

        assert compare_versions(cached, current) == -1


class TestIsStale:
    """Tests for is_stale function."""

    def test_stale_when_older(self) -> None:
        """Test returns True when cached is older."""
        cached = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        assert is_stale(cached, current) is True

    def test_not_stale_when_equal(self) -> None:
        """Test returns False when versions are equal."""
        version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        assert is_stale(version, version) is False

    def test_not_stale_when_newer(self) -> None:
        """Test returns False when cached is newer."""
        cached = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        assert is_stale(cached, current) is False


class TestIsCurrent:
    """Tests for is_current function."""

    def test_current_when_equal(self) -> None:
        """Test returns True when versions are equal."""
        version = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        assert is_current(version, version) is True

    def test_current_when_newer(self) -> None:
        """Test returns True when cached is newer."""
        cached = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

        assert is_current(cached, current) is True

    def test_not_current_when_older(self) -> None:
        """Test returns False when cached is older."""
        cached = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        assert is_current(cached, current) is False

    def test_is_current_inverse_of_is_stale(self) -> None:
        """Test is_current and is_stale are inverse when not equal."""
        cached = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        current = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        assert is_current(cached, current) != is_stale(cached, current)


class TestParseVersion:
    """Tests for parse_version function."""

    def test_parse_datetime_passthrough(self) -> None:
        """Test datetime is returned as-is with timezone."""
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = parse_version(dt)

        assert result == dt

    def test_parse_naive_datetime_adds_utc(self) -> None:
        """Test naive datetime gets UTC timezone added."""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = parse_version(dt)

        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 1

    def test_parse_iso_string(self) -> None:
        """Test parsing ISO format string."""
        result = parse_version("2025-01-15T10:30:00+00:00")

        assert result == datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_parse_z_suffix(self) -> None:
        """Test parsing string with Z suffix."""
        result = parse_version("2025-01-15T10:30:00Z")

        assert result == datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    def test_parse_without_timezone(self) -> None:
        """Test parsing string without timezone adds UTC."""
        result = parse_version("2025-01-15T10:30:00")

        assert result.tzinfo == timezone.utc

    def test_parse_with_microseconds(self) -> None:
        """Test parsing string with microseconds."""
        result = parse_version("2025-01-15T10:30:00.123456+00:00")

        assert result.microsecond == 123456

    def test_parse_invalid_raises(self) -> None:
        """Test parsing invalid string raises ValueError."""
        with pytest.raises(ValueError):
            parse_version("not a date")


class TestFormatVersion:
    """Tests for format_version function."""

    def test_format_utc_datetime(self) -> None:
        """Test formatting UTC datetime."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_version(dt)

        assert result == "2025-01-15T10:30:00+00:00"

    def test_format_naive_datetime_adds_utc(self) -> None:
        """Test formatting naive datetime adds UTC."""
        dt = datetime(2025, 1, 15, 10, 30, 0)
        result = format_version(dt)

        assert "+00:00" in result

    def test_format_with_microseconds(self) -> None:
        """Test formatting datetime with microseconds."""
        dt = datetime(2025, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = format_version(dt)

        assert "123456" in result

    def test_format_roundtrip(self) -> None:
        """Test format then parse returns equivalent datetime."""
        original = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        formatted = format_version(original)
        parsed = parse_version(formatted)

        assert parsed == original


class TestVersionToTimestamp:
    """Tests for version_to_timestamp function."""

    def test_datetime_to_timestamp(self) -> None:
        """Test converting datetime to timestamp."""
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = version_to_timestamp(dt)

        assert isinstance(result, float)
        assert result > 0

    def test_string_to_timestamp(self) -> None:
        """Test converting string to timestamp."""
        result = version_to_timestamp("2025-01-01T00:00:00Z")

        assert isinstance(result, float)
        assert result > 0

    def test_timestamp_ordering(self) -> None:
        """Test timestamps maintain ordering."""
        earlier = version_to_timestamp("2025-01-01T00:00:00Z")
        later = version_to_timestamp("2025-01-02T00:00:00Z")

        assert earlier < later
