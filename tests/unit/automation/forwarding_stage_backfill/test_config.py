"""BackfillConfig calibration-sentinel teeth (S4 pre-live condition).

  - T-CFG1  a config still bearing ``<...>`` placeholder tokens REFUSES
            (``is_calibrated`` is False)
  - T-CFG2  a config with a VALID CloudWatch Insights named-capture regex
            (``(?<inbox>...)``) PASSES (``is_calibrated`` is True) -- the
            sentinel must not false-positive on legitimate calibrated grammar
            just because it contains ``<``

Two-sided per T-CFG1/T-CFG2: the placeholder-token SHAPE
(``<UPPER_SNAKE_CASE>``) is rejected; a lowercase named-capture group embedded
in a real regex is accepted.
"""

from __future__ import annotations

import dataclasses

from autom8_asana.automation.forwarding_stage_backfill.config import BackfillConfig


class TestIsCalibratedSentinel:
    def test_default_config_is_uncalibrated(self) -> None:
        """T-CFG1: the default config (all ``<...>`` placeholders) REFUSES.

        RED side: a sentinel that reports the ruled-default config as
        calibrated FAILS -- the evidence source would run against unpinned
        grammar and silently report an empty book.
        """
        cfg = BackfillConfig()
        assert cfg.is_calibrated is False

    def test_partial_calibration_still_refuses(self) -> None:
        """T-CFG1b: even ONE remaining placeholder keeps the config uncalibrated."""
        cfg = dataclasses.replace(
            BackfillConfig(),
            booking_predicate="@message like /booking-pipeline-entered/",
            forwarding_confirmation_predicate="@message like /forwarding-confirmed/",
            # inbox_capture_regex left at its default placeholder.
        )
        assert cfg.is_calibrated is False

    def test_valid_named_capture_regex_is_calibrated(self) -> None:
        """T-CFG2: a VALID CloudWatch Insights named-capture regex PASSES.

        RED side: a sentinel doing a bare ``"<" in value`` substring check
        FAILS here -- ``(?<inbox>...)`` legitimately contains ``<`` as part of
        calibrated CloudWatch Insights ``parse`` grammar, not an unpinned
        ``<UPPER_SNAKE_CASE>`` placeholder token.
        """
        cfg = dataclasses.replace(
            BackfillConfig(),
            booking_predicate="@message like /booking-pipeline-entered/",
            forwarding_confirmation_predicate="@message like /forwarding-confirmed/",
            inbox_capture_regex=r".*to:(?<inbox>[a-f0-9-]+)@appointments\..*",
        )
        assert cfg.is_calibrated is True
