"""Unit tests for ProgressiveProjectBuilder._warn_unclassified_sections.

Tests the N4 freshness warning feature that logs unclassified section names
against the entity-type classifier during progressive builds.

Covers:
- Warning emitted for section names the classifier cannot map (returns None)
- No warning for section names the classifier recognizes
- No warning when no classifier is registered for the entity type
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autom8_asana.dataframes.builders.progressive import ProgressiveProjectBuilder


def _make_builder(
    entity_type: str = "offer",
    project_gid: str = "proj_123",
) -> ProgressiveProjectBuilder:
    """Create a minimal ProgressiveProjectBuilder for testing the warning helper.

    Only the fields accessed by _warn_unclassified_sections are relevant:
    ``self._entity_type`` and ``self._project_gid``.
    """
    client = MagicMock()
    schema = MagicMock()
    schema.version = "1.0.0"
    persistence = MagicMock()

    return ProgressiveProjectBuilder(
        client=client,
        project_gid=project_gid,
        entity_type=entity_type,
        schema=schema,
        persistence=persistence,
    )


def _make_section(gid: str, name: str | None) -> MagicMock:
    """Create a mock Section with gid and name attributes."""
    section = MagicMock()
    section.gid = gid
    section.name = name
    return section


class TestWarnUnclassifiedSections:
    """Tests for ProgressiveProjectBuilder._warn_unclassified_sections."""

    @patch("autom8_asana.dataframes.builders.progressive.get_classifier")
    @patch("autom8_asana.dataframes.builders.progressive.logger")
    def test_warning_emitted_for_unclassified_section(
        self,
        mock_logger: MagicMock,
        mock_get_classifier: MagicMock,
    ) -> None:
        """Unclassified section name produces a WARNING log with required extra keys."""
        # Arrange: classifier returns None for unknown section
        classifier = MagicMock()
        classifier.classify.return_value = None
        mock_get_classifier.return_value = classifier

        builder = _make_builder(entity_type="offer", project_gid="proj_123")
        sections = [_make_section("sec_1", "UNKNOWN SECTION")]

        # Act
        builder._warn_unclassified_sections(sections)

        # Assert
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        # Positional arg is the event name
        assert call_args[0][0] == "unclassified_section_name"

        # Extra dict contains PT-02 gate key and other required fields
        extra = call_args[1]["extra"]
        assert extra["unclassified_section"] == "UNKNOWN SECTION"
        assert extra["project_gid"] == "proj_123"
        assert extra["entity_type"] == "offer"
        assert extra["section_gid"] == "sec_1"
        assert extra["section_name"] == "UNKNOWN SECTION"

    @patch("autom8_asana.dataframes.builders.progressive.get_classifier")
    @patch("autom8_asana.dataframes.builders.progressive.logger")
    def test_no_warning_for_classified_section(
        self,
        mock_logger: MagicMock,
        mock_get_classifier: MagicMock,
    ) -> None:
        """Classified section name does not produce any warning log."""
        # Arrange: classifier returns a valid activity for a known section
        classifier = MagicMock()
        classifier.classify.return_value = "active"
        mock_get_classifier.return_value = classifier

        builder = _make_builder(entity_type="offer")
        sections = [_make_section("sec_1", "ACTIVE")]

        # Act
        builder._warn_unclassified_sections(sections)

        # Assert: no warning call at all
        mock_logger.warning.assert_not_called()

    @patch("autom8_asana.dataframes.builders.progressive.get_classifier")
    @patch("autom8_asana.dataframes.builders.progressive.logger")
    def test_no_warning_when_no_classifier_registered(
        self,
        mock_logger: MagicMock,
        mock_get_classifier: MagicMock,
    ) -> None:
        """Entity type with no registered classifier emits no warnings."""
        # Arrange: no classifier for this entity type
        mock_get_classifier.return_value = None

        builder = _make_builder(entity_type="contact")
        sections = [_make_section("sec_1", "Some Section")]

        # Act
        builder._warn_unclassified_sections(sections)

        # Assert: no warning call
        mock_logger.warning.assert_not_called()

    @patch("autom8_asana.dataframes.builders.progressive.get_classifier")
    @patch("autom8_asana.dataframes.builders.progressive.logger")
    def test_section_with_none_name_skipped(
        self,
        mock_logger: MagicMock,
        mock_get_classifier: MagicMock,
    ) -> None:
        """Section with name=None is silently skipped (no classify call, no warning)."""
        classifier = MagicMock()
        mock_get_classifier.return_value = classifier

        builder = _make_builder(entity_type="offer")
        sections = [_make_section("sec_1", None)]

        # Act
        builder._warn_unclassified_sections(sections)

        # Assert: classify never called, no warning
        classifier.classify.assert_not_called()
        mock_logger.warning.assert_not_called()

    @patch("autom8_asana.dataframes.builders.progressive.get_classifier")
    @patch("autom8_asana.dataframes.builders.progressive.logger")
    def test_mixed_sections_only_warn_unclassified(
        self,
        mock_logger: MagicMock,
        mock_get_classifier: MagicMock,
    ) -> None:
        """Mix of classified and unclassified sections: warning only for unclassified ones."""
        classifier = MagicMock()
        # Map: "ACTIVE" -> "active", "UNKNOWN" -> None
        classifier.classify.side_effect = lambda name: (
            "active" if name == "ACTIVE" else None
        )
        mock_get_classifier.return_value = classifier

        builder = _make_builder(entity_type="offer", project_gid="proj_456")
        sections = [
            _make_section("sec_1", "ACTIVE"),
            _make_section("sec_2", "UNKNOWN"),
            _make_section("sec_3", "ALSO UNKNOWN"),
        ]

        # Act
        builder._warn_unclassified_sections(sections)

        # Assert: exactly two warnings
        assert mock_logger.warning.call_count == 2

        # First warning for sec_2
        first_extra = mock_logger.warning.call_args_list[0][1]["extra"]
        assert first_extra["section_gid"] == "sec_2"
        assert first_extra["unclassified_section"] == "UNKNOWN"

        # Second warning for sec_3
        second_extra = mock_logger.warning.call_args_list[1][1]["extra"]
        assert second_extra["section_gid"] == "sec_3"
        assert second_extra["unclassified_section"] == "ALSO UNKNOWN"
