"""Thin ACTIVE-enumeration batch loop over the single-office runner (TDD §2.1/§8).

The batch is a thin loop: enumerate ACTIVE PLAY tasks, call ``run_office`` per office,
aggregate a green/red report. The load-bearing property is PER-OFFICE ISOLATION — one
office's failure is recorded and the wave CONTINUES (never a fleet halt), and a DONE
office is skipped. ``run_office`` itself is faked here; these tests exercise the loop.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates import batch as fbatch
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.batch import run_batch
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    OfficeState,
    Phase,
    StateStore,
)


def _store(tmp_path: object) -> StateStore:
    return StateStore(tmp_path / "state")  # type: ignore[operator]


def _done_state(play_gid: str) -> OfficeState:
    return OfficeState(
        play_gid=play_gid,
        office_guid_masked="1b271a63…",
        office_guid_sha256="d" * 64,
        clinic="Clinic",
        slug="a" * 32,
        deck_url=f"https://decks.cntently.com/{'a' * 32}/",
        frozen_sha256="b" * 64,
        phase=Phase.DONE,
        posts={"link": "L", "template": "T", "card": "C"},
        updated_at="2026-07-07T00:00:00+00:00",
    )


class TestPerOfficeIsolation:
    async def test_one_office_failure_does_not_halt_the_wave(self, tmp_path) -> None:
        """Office B raises mid-loop → recorded as failed; offices A and C still run (isolation)."""
        store = _store(tmp_path)

        async def _run(_client, *, play_gid, **_kw):
            if play_gid == "B":
                raise RuntimeError("boom on B")
            return SimpleNamespace(play_gid=play_gid, phase=Phase.PRODUCED, outcome="produced")

        with (
            patch.object(
                fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A", "B", "C"])
            ),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=tmp_path / "deploy",
                clinic_map={"A": "Clinic A", "B": "Clinic B", "C": "Clinic C"},
            )

        by_gid = {o.play_gid: o for o in report.offices}
        assert by_gid["A"].status == "ok"
        assert by_gid["C"].status == "ok"
        assert by_gid["B"].status == "failed"
        assert "boom on B" in (by_gid["B"].error or "")

    async def test_corrupt_manifest_for_one_office_fails_isolated_wave_continues(
        self, tmp_path
    ) -> None:
        """RED→GREEN: a corrupt / hand-edited manifest for ONE office raises at ``store.load``.
        Because the load is INSIDE the per-office try, that office is recorded ``failed`` and
        the healthy siblings still process (per-office isolation holds even for a manifest
        deserialize failure — one office's corruption never poisons the wave). Pre-fix (load
        OUTSIDE the try) the deserialize error aborted the WHOLE wave."""
        store = _store(tmp_path)
        # Corrupt B's manifest on disk (invalid JSON) -> store.load("B") raises inside the loop.
        store.state_dir.mkdir(parents=True, exist_ok=True)
        store.path_for("B").write_text("{ not valid json ", encoding="utf-8")

        async def _run(_client, *, play_gid, **_kw):
            return SimpleNamespace(play_gid=play_gid, phase=Phase.PRODUCED, outcome="produced")

        with (
            patch.object(
                fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A", "B", "C"])
            ),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=tmp_path / "deploy",
                clinic_map={"A": "Clinic A", "B": "Clinic B", "C": "Clinic C"},
            )

        by_gid = {o.play_gid: o for o in report.offices}
        assert by_gid["A"].status == "ok"
        assert by_gid["C"].status == "ok"
        assert by_gid["B"].status == "failed"  # the corrupt manifest is isolated, not fatal

    async def test_done_office_is_skipped_not_rerun(self, tmp_path) -> None:
        """An office already at DONE is skipped without invoking the runner (idempotent wave)."""
        store = _store(tmp_path)
        store.save(_done_state("A"))
        run_office = AsyncMock(
            return_value=SimpleNamespace(play_gid="B", phase=Phase.PRODUCED, outcome="produced")
        )
        with (
            patch.object(
                fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A", "B"])
            ),
            patch.object(fbatch, "run_office", new=run_office),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=tmp_path / "deploy",
                clinic_map={"B": "Clinic B"},
            )
        by_gid = {o.play_gid: o for o in report.offices}
        assert by_gid["A"].status == "skipped_done"
        assert by_gid["B"].status == "ok"
        # The runner was called ONLY for B (A was skipped before dispatch).
        assert run_office.await_count == 1
        assert run_office.await_args.kwargs["play_gid"] == "B"

    async def test_produce_without_confirmed_clinic_is_skipped(self, tmp_path) -> None:
        """Phase-1 needs an operator-confirmed clinic name per office; an office absent from
        the clinic map is skipped (never freezes an un-named deck) — not a hard failure."""
        store = _store(tmp_path)
        run_office = AsyncMock(
            return_value=SimpleNamespace(play_gid="A", phase=Phase.PRODUCED, outcome="produced")
        )
        with (
            patch.object(
                fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A", "B"])
            ),
            patch.object(fbatch, "run_office", new=run_office),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=tmp_path / "deploy",
                clinic_map={"A": "Clinic A"},  # B has no confirmed clinic
            )
        by_gid = {o.play_gid: o for o in report.offices}
        assert by_gid["A"].status == "ok"
        assert by_gid["B"].status == "skipped_no_clinic"


class TestScoping:
    async def test_office_scope_targets_one_office_no_enumeration(self, tmp_path) -> None:
        """``--office`` scopes to ONE office (the isolation door) — enumeration is not called."""
        store = _store(tmp_path)
        enumerate_mock = AsyncMock(return_value=["A", "B", "C"])
        run_office = AsyncMock(
            return_value=SimpleNamespace(play_gid="B", phase=Phase.PRODUCED, outcome="produced")
        )
        with (
            patch.object(fbatch, "enumerate_active_play_gids", new=enumerate_mock),
            patch.object(fbatch, "run_office", new=run_office),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=tmp_path / "deploy",
                clinic_map={"B": "Clinic B"},
                office="B",
            )
        enumerate_mock.assert_not_awaited()
        assert [o.play_gid for o in report.offices] == ["B"]
        assert run_office.await_args.kwargs["play_gid"] == "B"
