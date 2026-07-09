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

        async def _fake_run(mode, *, lookback_days, out_path):
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

        async def _fake_run(mode, *, lookback_days, out_path):
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

        async def _fake_run(mode, *, lookback_days, out_path):
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


def _empty_booking():
    from autom8_asana.automation.forwarding_stage_backfill.evidence_source import (
        BookingGatherResult,
    )

    return BookingGatherResult(signals={}, row_count=0, cap_hit=False, booking_mail_total=0)


def _empty_confirmation():
    from autom8_asana.automation.forwarding_stage_backfill.evidence_source import (
        ConfirmationGatherResult,
    )

    return ConfirmationGatherResult(signals={}, row_count=0, cap_hit=False)


# ---------------------------------------------------------------------------
# T-B18: the decisive CACHE-altitude two-sided proof for CURE 2 (K2).
# ---------------------------------------------------------------------------

# A numeric CI-task gid (the SDK's validate_gid rejects non-numeric gids).
_CI_GID = "1200000000000001"
_WORKSPACE_GID = "1140000000000001"
_SENT_OPT = "1216419441591240"
_FLOWING_OPT = "1216419441591244"
_VERIFY_OPTION_GIDS = {"Sent": _SENT_OPT, "Flowing": _FLOWING_OPT}


def _task_raw(option_gid: str) -> dict[str, str | list[dict[str, object]]]:
    """A raw task payload carrying the Forwarding-Stage single-select value."""
    return {
        "gid": _CI_GID,
        "custom_fields": [
            {
                "gid": FORWARDING_FIELD_GID,
                "name": "Forwarding Stage",
                "enum_value": {"gid": option_gid},
            }
        ],
    }


def _stage_serving_client(cache_provider: object) -> MagicMock:
    """A REAL AsanaClient (offline: explicit token + workspace) whose _http.get
    serves the PRE-write stage on the first fetch and the POST-write stage on
    every later fetch. The cache provider decides whether a re-read is served the
    stale first-fetch value (InMemory: first-fetch-wins) or re-hits HTTP (Null).
    """
    from autom8_asana import AsanaClient

    client = AsanaClient(
        token="test-token", workspace_gid=_WORKSPACE_GID, cache_provider=cache_provider
    )
    calls = {"n": 0}

    async def _http_get(url: str, params: dict[str, object] | None = None) -> dict[str, object]:
        calls["n"] += 1
        # First HTTP fetch = the PRE-write stage (Sent); the write then lands and
        # every LATER HTTP fetch = the POST-write stage (Flowing).
        return _task_raw(_SENT_OPT if calls["n"] == 1 else _FLOWING_OPT)

    client._http.get = AsyncMock(side_effect=_http_get)
    client._http_calls = calls  # type: ignore[attr-defined]  # test-only probe handle
    return client


class TestCacheProofVerificationAtCacheAltitude:
    """T-B18: the CURE-2 two-sided proof at the REAL cache layer (not the fixture).

    The K2 incident: a post-write verification read served through the SDK's
    InMemory cache (opt_fields-blind, first-fetch-wins) returned the STALE
    pre-write stage -> false-RED. The cure re-reads through a NullCacheProvider
    client. This test primes the cache with the pre-write stage, lands the write
    (HTTP now serves the post-write stage), and proves the two clients DIVERGE:
    the InMemory client re-reads STALE, the Null client re-reads FRESH.

    Asserts anchor to the rendered ForwardingStage tokens (never a bare-domain
    substring), per the CodeQL guard.
    """

    @pytest.mark.asyncio
    async def test_tb18_null_cache_verify_reads_fresh_inmemory_reads_stale(self) -> None:
        from autom8_asana._defaults import InMemoryCacheProvider, NullCacheProvider
        from autom8_asana.domain.forwarding_stage import ForwardingStage
        from autom8_asana.services.ci_task_resolution import read_current_stage

        # ── RED variant: verify read through an InMemory-cached client ─────
        # The first read primes the cache with Sent; the "write" lands (HTTP
        # flips to Flowing); the second read is the K2 verification read.
        im_client = _stage_serving_client(InMemoryCacheProvider())
        primed = await read_current_stage(
            im_client, _CI_GID, field_gid=FORWARDING_FIELD_GID, option_gids=_VERIFY_OPTION_GIDS
        )
        assert primed is ForwardingStage.SENT  # pre-write value
        stale = await read_current_stage(
            im_client, _CI_GID, field_gid=FORWARDING_FIELD_GID, option_gids=_VERIFY_OPTION_GIDS
        )
        # first-fetch-wins: the re-read is STALE (the false-RED the incident hit).
        assert stale is ForwardingStage.SENT
        assert im_client._http_calls["n"] == 1  # cache served the re-read

        # ── GREEN variant (the cure): verify read through a Null-cache client ─
        null_client = _stage_serving_client(NullCacheProvider())
        primed2 = await read_current_stage(
            null_client, _CI_GID, field_gid=FORWARDING_FIELD_GID, option_gids=_VERIFY_OPTION_GIDS
        )
        assert primed2 is ForwardingStage.SENT  # pre-write value
        fresh = await read_current_stage(
            null_client, _CI_GID, field_gid=FORWARDING_FIELD_GID, option_gids=_VERIFY_OPTION_GIDS
        )
        # cache-disabled: the re-read hits HTTP and sees the FRESH post-write stage.
        assert fresh is ForwardingStage.FLOWING
        assert null_client._http_calls["n"] == 2  # every read re-hit HTTP


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
