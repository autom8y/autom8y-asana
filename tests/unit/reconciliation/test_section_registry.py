"""Regression tests for SCAR-REG-001: Section Registry GID validation.

SCAR-REG-001: EXCLUDED_SECTION_GIDS and UNIT_SECTION_GIDS contained
sequential placeholder values that had not been verified against the live
Asana API. The fix (commit e89875f) adds _validate_gid_set() called at
module import time to warn on suspicious placeholder GIDs.

These tests verify:
1. _looks_sequential() correctly identifies sequential integer GID sets
   (the fabricated-placeholder pattern).
2. _looks_sequential() correctly rejects non-sequential production GIDs.
3. _validate_gid_set() calls logger.warning for sequential GIDs.
4. _validate_gid_set() calls logger.error for non-numeric GIDs.
5. The current placeholder EXCLUDED_SECTION_GIDS / UNIT_SECTION_GIDS are
   detected as sequential (they ARE placeholders and must be replaced before
   production deployment -- VERIFY-BEFORE-PROD annotation in the module).

Note on logging: autom8_asana uses structlog (via autom8y_log). Structlog's
BoundLoggerLazyProxy does not propagate to Python's stdlib logging, so pytest
caplog cannot capture it. Tests use unittest.mock.patch to assert on logger
calls instead.

Regression test for: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from autom8_asana.reconciliation.section_registry import (
    EXCLUDED_SECTION_GIDS,
    UNIT_SECTION_GIDS,
    _looks_sequential,
    _validate_gid_set,
)

# =============================================================================
# _looks_sequential unit tests
# =============================================================================


class TestLooksSequential:
    """Unit tests for _looks_sequential() heuristic.

    The heuristic returns True when 4+ consecutive pairs in the sorted GID
    set differ by exactly 1 (fabricated placeholder pattern).
    """

    def test_returns_true_for_sequential_placeholder_gids(self) -> None:
        """Sequential integer GIDs (the fabricated pattern) are detected."""
        sequential = frozenset(
            {
                "1201081073731600",
                "1201081073731601",
                "1201081073731602",
                "1201081073731603",
            }
        )
        assert _looks_sequential(sequential) is True

    def test_returns_true_for_longer_sequential_run(self) -> None:
        """Longer sequential runs are also detected."""
        sequential = frozenset(
            {
                "1201081073731610",
                "1201081073731611",
                "1201081073731612",
                "1201081073731613",
                "1201081073731614",
                "1201081073731615",
            }
        )
        assert _looks_sequential(sequential) is True

    def test_returns_false_for_non_sequential_production_gids(self) -> None:
        """Realistic Asana production GIDs are not flagged as sequential.

        Real Asana section GIDs are large non-sequential integers assigned
        by Asana's distributed ID generator. These test values use realistic
        spacing to confirm the heuristic does not produce false positives.
        """
        non_sequential = frozenset(
            {
                "1201819073701410",
                "1201819073701427",
                "1201819073701389",
                "1201819073701365",
            }
        )
        assert _looks_sequential(non_sequential) is False

    def test_returns_false_for_single_gid(self) -> None:
        """Single-element sets cannot be sequential."""
        assert _looks_sequential(frozenset({"1201081073731600"})) is False

    def test_returns_false_for_empty_set(self) -> None:
        """Empty sets are not sequential."""
        assert _looks_sequential(frozenset()) is False

    def test_returns_false_for_two_element_non_consecutive(self) -> None:
        """Two GIDs with a gap > 1 are not sequential."""
        assert _looks_sequential(frozenset({"1000000000000000", "1000000000000005"})) is False

    def test_returns_false_for_invalid_non_numeric(self) -> None:
        """Non-numeric GIDs cannot be checked for sequence; returns False."""
        assert _looks_sequential(frozenset({"abc", "def", "ghi", "jkl"})) is False

    def test_mixed_sequential_and_non_sequential(self) -> None:
        """A large set where fewer than the threshold pairs are sequential.

        The heuristic uses min(threshold, len(diffs)) as the required count,
        so for a 3-element set that has 2 diffs, 2 sequential diffs meets
        min(4, 2)=2. A 4+ element set needs at least 4 sequential pairs.
        This test uses 5 elements where only 2 of 4 pairs are sequential.
        """
        mixed = frozenset(
            {
                "1201081073731600",
                "1201081073731601",
                "1201081073731700",
                "1201081073731900",
                "1201081073732100",
            }
        )
        # 5 elements, 4 pairs. Only 1 sequential pair (600->601).
        # threshold = min(4, 4) = 4. sequential_diffs=1 < 4 -> False
        assert _looks_sequential(mixed) is False


# =============================================================================
# _validate_gid_set logging tests
# =============================================================================

_SECTION_REGISTRY_LOGGER_PATH = "autom8_asana.reconciliation.section_registry.logger"


class TestValidateGidSet:
    """Tests for _validate_gid_set() startup validation logging.

    _validate_gid_set() is called at module import time and calls:
    - logger.warning(...) for sequential/fabricated placeholder GIDs
    - logger.error(...) for non-numeric GIDs that fail format validation

    Uses unittest.mock.patch because autom8_asana uses structlog (via
    autom8y_log), which does not propagate to Python's stdlib logging and
    therefore cannot be captured with pytest's caplog fixture.
    """

    def test_sequential_gids_call_logger_warning(self) -> None:
        """Sequential placeholder GIDs cause logger.warning at startup validation."""
        sequential = frozenset(
            {
                "1201081073731600",
                "1201081073731601",
                "1201081073731602",
                "1201081073731603",
            }
        )
        mock_logger = MagicMock()
        with patch(_SECTION_REGISTRY_LOGGER_PATH, mock_logger):
            _validate_gid_set(sequential, "TEST_REGISTRY")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        event_name = call_args[0][0]
        assert "fabricated" in event_name or "sequential" in event_name or "appear" in event_name, (
            f"Expected warning event about fabricated GIDs; got: {event_name!r}"
        )

    def test_sequential_gids_warning_passes_registry_name(self) -> None:
        """Warning call passes registry name in extra kwargs for diagnostic tracing."""
        sequential = frozenset(
            {
                "1201081073731600",
                "1201081073731601",
                "1201081073731602",
                "1201081073731603",
            }
        )
        mock_logger = MagicMock()
        with patch(_SECTION_REGISTRY_LOGGER_PATH, mock_logger):
            _validate_gid_set(sequential, "MY_REGISTRY")

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        extra = call_kwargs.get("extra", {})
        assert extra.get("registry") == "MY_REGISTRY", (
            f"Expected extra['registry']='MY_REGISTRY'; got extra={extra}"
        )

    def test_non_numeric_gids_call_logger_error(self) -> None:
        """Non-numeric GIDs that fail the Asana format pattern cause logger.error."""
        invalid = frozenset({"placeholder-gid", "not-a-number"})
        mock_logger = MagicMock()
        with patch(_SECTION_REGISTRY_LOGGER_PATH, mock_logger):
            _validate_gid_set(invalid, "INVALID_REGISTRY")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        event_name = call_args[0][0]
        assert "invalid" in event_name or "format" in event_name, (
            f"Expected error event about invalid GID format; got: {event_name!r}"
        )

    def test_valid_non_sequential_gids_emit_no_logs(self) -> None:
        """Non-sequential, valid-format GIDs produce no warning or error calls."""
        valid = frozenset(
            {
                "1201819073701410",
                "1201819073701427",
                "1201819073701389",
                "1201819073701365",
            }
        )
        mock_logger = MagicMock()
        with patch(_SECTION_REGISTRY_LOGGER_PATH, mock_logger):
            _validate_gid_set(valid, "VALID_REGISTRY")

        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()


# =============================================================================
# Production GID set regression -- detects placeholder state
# =============================================================================


class TestProductionGidSetsAreSequential:
    """Regression test: current EXCLUDED_SECTION_GIDS and UNIT_SECTION_GIDS
    are sequential placeholders.

    SCAR-REG-001 documents that these GIDs were fabricated and have NOT been
    verified against the live Asana API. This test confirms the detection
    mechanism works and that the placeholder values remain flagged until
    real GIDs replace them.

    When production GIDs are verified and replaced, these tests will flip to
    False (expected). At that point, update or remove this test class and
    add a test verifying the new GIDs pass _ASANA_GID_PATTERN and are NOT
    sequential. See VERIFY-BEFORE-PROD annotation in section_registry.py.
    """

    def test_excluded_section_gids_are_detected_as_sequential(self) -> None:
        """Current EXCLUDED_SECTION_GIDS are sequential placeholders (SCAR-REG-001).

        This test MUST pass (sequential=True) while placeholders are in use.
        Flip this assertion to False after replacing with verified production GIDs.
        """
        assert _looks_sequential(EXCLUDED_SECTION_GIDS) is True, (
            "EXCLUDED_SECTION_GIDS are no longer sequential. If you have replaced "
            "placeholders with verified production GIDs, update this test to assert False "
            "and remove the VERIFY-BEFORE-PROD annotation in section_registry.py."
        )

    def test_unit_section_gids_are_detected_as_sequential(self) -> None:
        """Current UNIT_SECTION_GIDS are sequential placeholders (SCAR-REG-001).

        This test MUST pass (sequential=True) while placeholders are in use.
        Flip this assertion to False after replacing with verified production GIDs.
        """
        assert _looks_sequential(UNIT_SECTION_GIDS) is True, (
            "UNIT_SECTION_GIDS are no longer sequential. If you have replaced "
            "placeholders with verified production GIDs, update this test to assert False "
            "and remove the VERIFY-BEFORE-PROD annotation in section_registry.py."
        )

    def test_excluded_section_gids_warn_at_module_validation(self) -> None:
        """_validate_gid_set() calls logger.warning for current EXCLUDED_SECTION_GIDS.

        This is the key regression test for SCAR-REG-001: the startup warning
        MUST fire for the current placeholder GIDs. If this test fails it means
        either the GIDs were replaced with verified values (good — update the
        test) or the detection was removed (bad — restore it).
        """
        mock_logger = MagicMock()
        with patch(_SECTION_REGISTRY_LOGGER_PATH, mock_logger):
            _validate_gid_set(EXCLUDED_SECTION_GIDS, "EXCLUDED_SECTION_GIDS")

        assert mock_logger.warning.called, (
            "SCAR-REG-001 regression: _validate_gid_set must call logger.warning "
            "for placeholder EXCLUDED_SECTION_GIDS. Detection was not triggered. "
            "If GIDs were replaced with verified values, update this assertion to "
            "assert_not_called() and remove the VERIFY-BEFORE-PROD annotation."
        )
