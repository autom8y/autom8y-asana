"""Regression tests for SCAR-REG-001: Section Registry GID validation.

SCAR-REG-001 (RESOLVED by W-REG): EXCLUDED_SECTION_GIDS and UNIT_SECTION_GIDS
formerly contained sequential placeholder values that had NOT been verified
against the live Asana API. W-REG replaced them with live-verified GIDs sourced
from the W-IRIS ``GET /sections`` receipt, derived through the import-time NAME
join (``_build_live_registry``). The fabricated-placeholder heuristic
(``_looks_sequential``) is removed: the real UNIT set contains a legitimate
consecutive run (…565→…571), so the heuristic would emit a FALSE
``section_registry_gids_appear_fabricated`` warning on correct live data.

These tests verify the post-W-REG contract:
1. ``_validate_gid_set()`` still calls ``logger.error`` for non-numeric GIDs
   (the format-validation path is retained).
2. Valid Asana-format GIDs produce ZERO warning/error at validation.
3. The live EXCLUDED_SECTION_GIDS / UNIT_SECTION_GIDS emit ZERO fabricated
   warning at module validation (the false-positive the heuristic would have
   raised) and every live GID passes ``_ASANA_GID_PATTERN``.
4. The dead ``_looks_sequential`` heuristic is GONE (guard against
   reintroduction of the false-positive path).

Note on logging: autom8_asana uses structlog (via autom8y_log). Structlog's
BoundLoggerLazyProxy does not propagate to Python's stdlib logging, so pytest
caplog cannot capture it. Tests use unittest.mock.patch to assert on logger
calls instead.

Regression test for: src/autom8_asana/reconciliation/section_registry.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import autom8_asana.reconciliation.section_registry as section_registry
from autom8_asana.reconciliation.section_registry import (
    _ASANA_GID_PATTERN,
    EXCLUDED_SECTION_GIDS,
    UNIT_SECTION_GIDS,
    _validate_gid_set,
)

_SECTION_REGISTRY_LOGGER_PATH = "autom8_asana.reconciliation.section_registry.logger"


# =============================================================================
# _validate_gid_set logging tests (format-validation path retained)
# =============================================================================


class TestValidateGidSet:
    """Tests for _validate_gid_set() startup validation logging.

    _validate_gid_set() is called at module import time and calls
    logger.error(...) for non-numeric GIDs that fail format validation. The
    fabricated-placeholder warning path was removed with _looks_sequential.

    Uses unittest.mock.patch because autom8_asana uses structlog (via
    autom8y_log), which does not propagate to Python's stdlib logging and
    therefore cannot be captured with pytest's caplog fixture.
    """

    @pytest.mark.scar
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

    @pytest.mark.scar
    def test_valid_gids_emit_no_logs(self) -> None:
        """Valid-format GIDs produce no warning or error calls."""
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
# Live GID sets: no false fabricated-warning, all format-valid (W-REG)
# =============================================================================


class TestLiveGidSetsCleanValidation:
    """The live W-REG GID sets validate cleanly.

    This is the bound outcome of removing _looks_sequential: the real UNIT set
    has a legitimate consecutive run (…565→…571). The old heuristic returned
    True on that run and emitted a FALSE ``section_registry_gids_appear_fabricated``
    warning at every import. With the heuristic gone, the live sets validate
    with ZERO warning/error.
    """

    @pytest.mark.scar
    def test_live_excluded_gids_emit_no_warning_or_error(self) -> None:
        """EXCLUDED_SECTION_GIDS validate with no warning and no error."""
        mock_logger = MagicMock()
        with patch(_SECTION_REGISTRY_LOGGER_PATH, mock_logger):
            _validate_gid_set(EXCLUDED_SECTION_GIDS, "EXCLUDED_SECTION_GIDS")

        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.scar
    def test_live_unit_gids_emit_no_warning_or_error(self) -> None:
        """UNIT_SECTION_GIDS validate with no warning and no error.

        Guards the removed false-positive: the live UNIT set's consecutive run
        (…565→…571) must NOT be flagged as fabricated.
        """
        mock_logger = MagicMock()
        with patch(_SECTION_REGISTRY_LOGGER_PATH, mock_logger):
            _validate_gid_set(UNIT_SECTION_GIDS, "UNIT_SECTION_GIDS")

        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.scar
    def test_all_live_gids_are_asana_format(self) -> None:
        """Every live excluded and unit GID matches the Asana GID pattern."""
        for gid in EXCLUDED_SECTION_GIDS | UNIT_SECTION_GIDS:
            assert _ASANA_GID_PATTERN.match(gid), (
                f"live GID {gid!r} does not match the Asana GID format "
                f"{_ASANA_GID_PATTERN.pattern!r}"
            )


# =============================================================================
# Dead-heuristic removal guard
# =============================================================================


class TestLooksSequentialRemoved:
    """The fabricated-placeholder heuristic must stay removed.

    _looks_sequential produced a false positive on the real UNIT set's
    legitimate consecutive run. Reintroducing it would re-emit a spurious
    fabricated-GID warning at every import.
    """

    @pytest.mark.scar
    def test_looks_sequential_symbol_absent(self) -> None:
        """The module no longer defines _looks_sequential."""
        assert not hasattr(section_registry, "_looks_sequential"), (
            "_looks_sequential was reintroduced. It emits a FALSE "
            "'section_registry_gids_appear_fabricated' warning on the live UNIT "
            "set's legitimate consecutive run (…565→…571). Keep it removed."
        )

    @pytest.mark.scar
    def test_sequential_threshold_symbol_absent(self) -> None:
        """The heuristic's threshold constant is also removed."""
        assert not hasattr(section_registry, "_SEQUENTIAL_SUFFIX_THRESHOLD")
