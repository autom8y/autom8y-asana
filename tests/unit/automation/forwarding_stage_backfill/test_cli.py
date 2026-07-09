"""CLI teeth for the backfill (TDD S4 §8 T-C*).

  - T-C1  dry-run is the DEFAULT (plan subcommand -> ZERO Asana writes)
  - T-C2  apply refuses when the write config is inactive (loud, exit 1, names
          the missing setting)
  - T-C3  apply requires an explicit `apply` subcommand + active config to write

These test the CLI wiring + the apply-config gate. The heavy orchestrator logic
is covered in test_backfill.py; here the teeth are on argument routing and the
inactive-config refusal (which the orchestrator raises and the CLI surfaces as
exit 1).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.forwarding_stage_backfill.backfill import (
    BackfillMode,
    BackfillWriteConfig,
    BackfillWriteConfigInactive,
    ForwardingStageBackfill,
)
from autom8_asana.automation.forwarding_stage_backfill.cli import (
    build_write_config,
    main,
)

FORWARDING_FIELD_GID = "1216419441591239"
STAGE_OPTION_GIDS = {"Flowing": "1216419441591244", "Verified": "1216419441591242"}


def _settings(*, enabled: bool, field_gid: str, option_gids: dict[str, str]) -> MagicMock:
    s = MagicMock()
    s.forwarding_stage_write_enabled = enabled
    s.forwarding_stage_field_gid = field_gid
    s.forwarding_stage_option_gids = option_gids
    s.forwarding_stage_disposition = {}
    s.company_id_field_gid = "1200000000000099"
    return s


class TestBuildWriteConfig:
    """build_write_config maps ApiSettings.forwarding_stage_* -> BackfillWriteConfig."""

    def test_active_when_all_gates_set(self) -> None:
        """RED side: a build that drops a gate (e.g. ignores option_gids) would
        report is_active when it should not, or vice-versa."""
        with patch(
            "autom8_asana.api.config.get_settings",
            return_value=_settings(
                enabled=True, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
            ),
        ):
            cfg = build_write_config()
        assert cfg.is_active is True
        assert cfg.field_gid == FORWARDING_FIELD_GID
        assert cfg.option_gids == STAGE_OPTION_GIDS

    def test_inactive_when_switch_off(self) -> None:
        """The master switch OFF -> inactive even with field + options set."""
        with patch(
            "autom8_asana.api.config.get_settings",
            return_value=_settings(
                enabled=False, field_gid=FORWARDING_FIELD_GID, option_gids=STAGE_OPTION_GIDS
            ),
        ):
            cfg = build_write_config()
        assert cfg.is_active is False

    def test_inactive_when_options_empty(self) -> None:
        """Empty option map -> inactive even with switch on + field set."""
        with patch(
            "autom8_asana.api.config.get_settings",
            return_value=_settings(enabled=True, field_gid=FORWARDING_FIELD_GID, option_gids={}),
        ):
            cfg = build_write_config()
        assert cfg.is_active is False


class TestApplyConfigGate:
    """T-C2: apply on an inactive config raises BackfillWriteConfigInactive."""

    @pytest.mark.asyncio
    async def test_tc2_apply_refuses_when_config_inactive(self) -> None:
        """RED side: apply silently no-op'ing when is_active=False FAILS -- the
        operator asked to WRITE, so the refusal must be loud (and name the gap)."""
        inactive = BackfillWriteConfig(enabled=False, field_gid="", option_gids={})
        orch = ForwardingStageBackfill(
            evidence_source=MagicMock(),  # never reached (gate is at the top)
            client=MagicMock(),
            company_id_field_gid="x",
            write_config=inactive,
        )
        with pytest.raises(BackfillWriteConfigInactive) as exc:
            await orch.run(mode=BackfillMode.APPLY, window_days=21)
        # Names the missing setting(s).
        assert any("write_enabled" in m for m in exc.value.missing)

    @pytest.mark.asyncio
    async def test_apply_gate_does_not_fire_in_plan_mode(self) -> None:
        """plan mode with an inactive config does NOT refuse (plan can preview
        before the switch is flipped)."""
        inactive = BackfillWriteConfig(enabled=False, field_gid="", option_gids={})
        evidence = MagicMock()
        evidence.booking_mail_counts.return_value = _empty_booking()
        evidence.forwarding_confirmations.return_value = _empty_confirmation()
        orch = ForwardingStageBackfill(
            evidence_source=evidence,
            client=MagicMock(),
            company_id_field_gid="x",
            write_config=inactive,
        )
        plan = await orch.run(mode=BackfillMode.PLAN, window_days=21)
        assert plan.mode == "plan"  # no refusal


class TestMainRouting:
    """T-C1 / T-C3: subcommand routing + exit codes."""

    def test_tc1_plan_is_dry_run_no_writes(self) -> None:
        """T-C1: `plan` runs in PLAN mode (dry-run) and emits an artifact with
        zero Asana writes.

        RED side: routing `plan` to APPLY mode (or writing on a bare plan) FAILS.
        """
        captured = {}

        async def _fake_run(mode, *, lookback_days, out_path):  # noqa: ANN001
            captured["mode"] = mode
            return 0

        with patch(
            "autom8_asana.automation.forwarding_stage_backfill.cli._run",
            side_effect=_fake_run,
        ):
            rc = main(["plan"])
        assert rc == 0
        assert captured["mode"] is BackfillMode.PLAN

    def test_tc3_apply_routes_to_apply_mode(self) -> None:
        """T-C3: `apply` routes to APPLY mode (the only path that can write).

        RED side: `apply` routing to PLAN (never writing) FAILS.
        """
        captured = {}

        async def _fake_run(mode, *, lookback_days, out_path):  # noqa: ANN001
            captured["mode"] = mode
            return 0

        with patch(
            "autom8_asana.automation.forwarding_stage_backfill.cli._run",
            side_effect=_fake_run,
        ):
            rc = main(["apply"])
        assert rc == 0
        assert captured["mode"] is BackfillMode.APPLY

    def test_lookback_days_flag_forwarded(self) -> None:
        """--lookback-days overrides the DD-2 default and reaches the run."""
        captured = {}

        async def _fake_run(mode, *, lookback_days, out_path):  # noqa: ANN001
            captured["lookback_days"] = lookback_days
            return 0

        with patch(
            "autom8_asana.automation.forwarding_stage_backfill.cli._run",
            side_effect=_fake_run,
        ):
            rc = main(["plan", "--lookback-days", "7"])
        assert rc == 0
        assert captured["lookback_days"] == 7

    def test_no_subcommand_errors(self) -> None:
        """A bare invocation with no subcommand exits non-zero (argparse required).

        RED side: a default-to-apply on a bare invocation would be catastrophic;
        argparse requires an explicit subcommand.
        """
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code != 0


def _empty_booking():  # noqa: ANN202
    from autom8_asana.automation.forwarding_stage_backfill.evidence_source import (
        BookingGatherResult,
    )

    return BookingGatherResult(signals={}, row_count=0, cap_hit=False, booking_mail_total=0)


def _empty_confirmation():  # noqa: ANN202
    from autom8_asana.automation.forwarding_stage_backfill.evidence_source import (
        ConfirmationGatherResult,
    )

    return ConfirmationGatherResult(signals={}, row_count=0, cap_hit=False)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
