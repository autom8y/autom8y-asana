"""Thin ACTIVE-enumeration batch loop over the single-office runner (TDD §2.1/§8).

The batch is a thin loop: enumerate ACTIVE PLAY tasks, call ``run_office`` per office,
aggregate a green/red report. The load-bearing property is PER-OFFICE ISOLATION — one
office's failure is recorded and the wave CONTINUES (never a fleet halt), and a DONE
office is skipped. ``run_office`` itself is faked here; these tests exercise the loop.

The wave-shared accumulating deploy (TDD §8) adds a second load-bearing property: produce
waves surface exactly ONE ``wrangler`` command, and ONLY after the fail-closed deploy-root
guard (hygiene allowlist + ``_headers`` parity + no-orphan predicate) passes — a refusal
surfaces NO command anywhere (per-office copies stripped) and exits RED.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates import batch as fbatch
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.batch import (
    BatchReport,
    OfficeReport,
    run_batch,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    OfficeState,
    Phase,
    StateStore,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import (
    HEADERS_FILE_CONTENT,
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


SLUG_A = "1f2e3d4c5b6a798801234567890abcde"
SLUG_B = "fedcba9876543210aabbccddeeff0011"


def _make_shared_root(tmp_path: Path, slugs: list[str]) -> Path:
    """A guard-GREEN wave-shared root (``public/`` + sibling ``config/`` ledger)."""
    root = tmp_path / "deck-host" / "public"
    root.mkdir(parents=True, exist_ok=True)
    (root / "_headers").write_text(HEADERS_FILE_CONTENT, encoding="utf-8")
    for slug in slugs:
        (root / slug).mkdir(exist_ok=True)
        (root / slug / "index.html").write_text(f"<html>{slug}</html>", encoding="utf-8")
    config = root.parent / "config"
    config.mkdir(exist_ok=True)
    (config / "deck-manifest.json").write_text(
        json.dumps({"version": 1, "decks": {slug: {"status": "active"} for slug in slugs}}),
        encoding="utf-8",
    )
    return root


def _produced(
    play_gid: str,
    deploy_root: Path,
    *,
    slug: str | None = None,
    outcome: str = "produced",
) -> SimpleNamespace:
    """A fake produce-phase OfficeRunResult carrying the SHARED-root wrangler command.

    ``slug`` opts the fake into the wave-slug cross-check (the real ``OfficeRunResult``
    always carries the pinned slug); slug-less fakes exercise the other guard legs.
    """
    ns = SimpleNamespace(
        play_gid=play_gid,
        phase=Phase.PRODUCED,
        outcome=outcome,
        wrangler_command=f"wrangler pages deploy {deploy_root} --project-name=deck-host",
    )
    if slug is not None:
        ns.slug = slug
    return ns


class TestWaveDeployGate:
    async def test_wave_surfaces_exactly_one_command_post_guard(self, tmp_path) -> None:
        """Two produce-ok offices, guard-GREEN root: the report carries ONE wave-level
        command (identical to the shared-root command every office computed)."""
        store = _store(tmp_path)
        root = _make_shared_root(tmp_path, [SLUG_A, SLUG_B])

        async def _run(_client, *, play_gid, deploy_base, **_kw):
            return _produced(play_gid, deploy_base)

        with (
            patch.object(
                fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A", "B"])
            ),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=root,
                clinic_map={"A": "Clinic A", "B": "Clinic B"},
            )
        assert report.deploy_refusal is None
        assert report.wrangler_command == (f"wrangler pages deploy {root} --project-name=deck-host")

    async def test_guard_refusal_surfaces_no_command_and_strips_per_office(self, tmp_path) -> None:
        """A stray file in the shared root: LOUD refusal — NO wave command, and every
        per-office wrangler_command is stripped (fail-closed; no copy of the lever survives)."""
        store = _store(tmp_path)
        root = _make_shared_root(tmp_path, [SLUG_A])
        (root / "stray-notes.txt").write_text("oops", encoding="utf-8")

        async def _run(_client, *, play_gid, deploy_base, **_kw):
            return _produced(play_gid, deploy_base)

        with (
            patch.object(fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A"])),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=root,
                clinic_map={"A": "Clinic A"},
            )
        assert report.wrangler_command is None
        assert report.deploy_refusal is not None
        assert "root-hygiene REFUSED" in report.deploy_refusal
        for office in report.ok:
            assert office.result is not None
            assert office.result.wrangler_command is None  # stripped, fail-closed

    async def test_orphaned_active_ledger_slug_refuses_wave(self, tmp_path) -> None:
        """An active ledger slug missing from the staged root would 404 a LIVE client deck
        on deploy — the no-orphan predicate refuses BEFORE any command is surfaced."""
        store = _store(tmp_path)
        root = _make_shared_root(tmp_path, [SLUG_A, SLUG_B])
        # Simulate the partial-root hazard: an active ledger slug's dir is absent.
        (root / SLUG_B / "index.html").unlink()
        (root / SLUG_B).rmdir()

        async def _run(_client, *, play_gid, deploy_base, **_kw):
            return _produced(play_gid, deploy_base)

        with (
            patch.object(fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A"])),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=root,
                clinic_map={"A": "Clinic A"},
            )
        assert report.wrangler_command is None
        assert report.deploy_refusal is not None
        assert "no-orphan REFUSED" in report.deploy_refusal
        assert SLUG_B in report.deploy_refusal

    async def test_absent_ledger_refuses_wave_fail_closed(self, tmp_path) -> None:
        """No committed ledger next to the root: absence is NOT permission — refuse."""
        store = _store(tmp_path)
        root = _make_shared_root(tmp_path, [SLUG_A])
        (root.parent / "config" / "deck-manifest.json").unlink()

        async def _run(_client, *, play_gid, deploy_base, **_kw):
            return _produced(play_gid, deploy_base)

        with (
            patch.object(fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A"])),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=root,
                clinic_map={"A": "Clinic A"},
            )
        assert report.wrangler_command is None
        assert report.deploy_refusal is not None
        assert "missing/unreadable" in report.deploy_refusal

    async def test_explicit_deck_manifest_param_overrides_default(self, tmp_path) -> None:
        """``deck_manifest`` overrides the ``<deploy_base>/../config`` default location."""
        store = _store(tmp_path)
        root = _make_shared_root(tmp_path, [SLUG_A])
        (root.parent / "config" / "deck-manifest.json").unlink()  # default path gone
        elsewhere = tmp_path / "ledger.json"
        elsewhere.write_text(
            json.dumps({"decks": {SLUG_A: {"status": "active"}}}), encoding="utf-8"
        )

        async def _run(_client, *, play_gid, deploy_base, **_kw):
            return _produced(play_gid, deploy_base)

        with (
            patch.object(fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A"])),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=root,
                clinic_map={"A": "Clinic A"},
                deck_manifest=elsewhere,
            )
        assert report.deploy_refusal is None
        assert report.wrangler_command is not None

    async def test_already_produced_office_absent_from_root_refuses_wave(self, tmp_path) -> None:
        """The ledger-blind ``already_produced`` window: office B is at PRODUCED so the
        runner re-surfaces the command WITHOUT re-staging, the root lacks B's slug dir,
        and B's slug is NOT yet in the committed ledger (the ledger update is an operator
        lever) — the no-orphan predicate is blind, but the wave-slug cross-check refuses
        BEFORE the command is surfaced (a deploy here would ship without B's deck)."""
        store = _store(tmp_path)
        root = _make_shared_root(tmp_path, [SLUG_A])  # ledger + root carry ONLY A's slug

        async def _run(_client, *, play_gid, deploy_base, **_kw):
            if play_gid == "A":
                return _produced("A", deploy_base, slug=SLUG_A)
            return _produced("B", deploy_base, slug=SLUG_B, outcome="already_produced")

        with (
            patch.object(
                fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A", "B"])
            ),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=root,
                clinic_map={"A": "Clinic A", "B": "Clinic B"},
            )
        assert report.wrangler_command is None
        assert report.deploy_refusal is not None
        assert "wave-slug cross-check REFUSED" in report.deploy_refusal
        assert SLUG_B in report.deploy_refusal
        for office in report.ok:
            assert office.result is not None
            assert office.result.wrangler_command is None  # stripped, fail-closed

    async def test_already_produced_office_present_in_root_surfaces(self, tmp_path) -> None:
        """Positive control: both pinned slugs staged in the shared root — the wave-slug
        cross-check passes and the ONE wave command surfaces."""
        store = _store(tmp_path)
        root = _make_shared_root(tmp_path, [SLUG_A, SLUG_B])

        async def _run(_client, *, play_gid, deploy_base, **_kw):
            if play_gid == "A":
                return _produced("A", deploy_base, slug=SLUG_A)
            return _produced("B", deploy_base, slug=SLUG_B, outcome="already_produced")

        with (
            patch.object(
                fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A", "B"])
            ),
            patch.object(fbatch, "run_office", new=AsyncMock(side_effect=_run)),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=root,
                clinic_map={"A": "Clinic A", "B": "Clinic B"},
            )
        assert report.deploy_refusal is None
        assert report.wrangler_command == (f"wrangler pages deploy {root} --project-name=deck-host")

    async def test_no_staged_offices_means_no_guard_no_command(self, tmp_path) -> None:
        """A wave with nothing staged (all skipped) surfaces nothing and refuses nothing —
        even over a root that would fail the guard (there is no deploy to gate)."""
        store = _store(tmp_path)
        store.save(_done_state("A"))
        with (
            patch.object(fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A"])),
            patch.object(fbatch, "run_office", new=AsyncMock()),
        ):
            report = await run_batch(
                MagicMock(),
                phase="produce",
                store=store,
                deploy_base=tmp_path / "nonexistent-root",
                clinic_map={},
            )
        assert report.wrangler_command is None
        assert report.deploy_refusal is None

    async def test_resume_phase_never_runs_the_guard(self, tmp_path) -> None:
        """Resume surfaces no deploy command, so the guard must not run (a resume against
        a root that would fail hygiene must not manufacture a refusal)."""
        store = _store(tmp_path)
        run_office = AsyncMock(
            return_value=SimpleNamespace(
                play_gid="A", phase=Phase.DONE, outcome="posted", wrangler_command=None
            )
        )
        with (
            patch.object(fbatch, "enumerate_active_play_gids", new=AsyncMock(return_value=["A"])),
            patch.object(fbatch, "run_office", new=run_office),
        ):
            report = await run_batch(
                MagicMock(),
                phase="resume",
                store=store,
                deploy_base=tmp_path / "nonexistent-root",
                clinic_map={},
                execute=True,
            )
        assert report.wrangler_command is None
        assert report.deploy_refusal is None


class TestCliWaveSurface:
    def _cli_report(self, command: str | None, refusal: str | None) -> BatchReport:
        results = [
            OfficeReport(
                gid,
                "ok",
                outcome="produced",
                result=SimpleNamespace(  # type: ignore[arg-type]
                    play_gid=gid,
                    phase=Phase.PRODUCED,
                    outcome="produced",
                    wrangler_command=command,
                ),
            )
            for gid in ("A", "B")
        ]
        return BatchReport(offices=results, wrangler_command=command, deploy_refusal=refusal)

    def test_produce_prints_exactly_one_wave_banner(self, tmp_path, capsys) -> None:
        """Two ok offices, ONE surfaced command: the banner (and the command) print ONCE."""
        command = f"wrangler pages deploy {tmp_path} --project-name=deck-host"
        report = self._cli_report(command, None)
        with (
            patch.object(fbatch, "run_batch", new=AsyncMock(return_value=report)),
            patch.object(fbatch, "AsanaClient"),
        ):
            rc = fbatch.main(["--phase", "produce", "--deploy-base", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == 0
        assert out.count("wrangler pages deploy") == 1  # ONE command for the whole wave
        assert out.count(command) == 1
        assert out.count("[HALT — reserved operator lever]") == 1
        assert "2 deck(s) staged into the wave-shared root" in out

    def test_produce_refusal_prints_loud_banner_no_command_exits_red(
        self, tmp_path, capsys
    ) -> None:
        """A guard refusal is LOUD: [REFUSED] banner, ZERO wrangler commands, exit 1."""
        report = self._cli_report(None, "no-orphan REFUSED: ledger slug(s) ['x'] absent")
        with (
            patch.object(fbatch, "run_batch", new=AsyncMock(return_value=report)),
            patch.object(fbatch, "AsanaClient"),
        ):
            rc = fbatch.main(["--phase", "produce", "--deploy-base", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == 1  # a refused wave is RED even with zero per-office failures
        assert "[REFUSED — no deploy command surfaced]" in out
        assert "no-orphan REFUSED" in out
        assert "wrangler pages deploy" not in out  # NO command surfaced anywhere


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
