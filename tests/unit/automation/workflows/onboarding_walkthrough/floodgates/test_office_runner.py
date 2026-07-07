"""Two-phase single-office runner — orchestration teeth (fake the heavy primitives).

Per TDD-floodgates-batch-seam-2026-07-07 §2/§3/§4. The runner COMPOSES proven primitives
(freeze, mint, stage, byte-parity, the 3 posters, the pure-Asana guid bridge); these tests
fake those heavy primitives and exercise the ORCHESTRATION: the two-phase halt/resume seam,
the state machine, idempotency/resumability, and the cross-tenant (C-1) task-binding.

The load-bearing RED teeth:

* **C-1 task-binding** (``test_c1_*``): Phase-2 binds every poster to the office's OWN PLAY
  and threads ONLY the slug; an office whose live-resolved guid ≠ the manifest's recorded
  office REFUSES with ``TaskOfficeMismatch`` (reusing the #205 discipline) — the scar this
  initiative closes BY CONSTRUCTION.
* **Phase-1 HALT** (``test_phase1_*``): ``produce`` stages + surfaces the reserved ``wrangler``
  command and HALTS — no Asana post, no ``curl``, no ``wrangler`` ever executed.
* **byte-parity gate** (``test_phase2_byte_parity_*``): served ≠ frozen → ``BundleParityError``,
  no post (never link a deck that is not byte-identical to what was frozen).
"""

from __future__ import annotations

import hashlib
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates import (
    office_runner as orunner,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.office_runner import (
    FloodgatesRefused,
    run_office,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    OfficeState,
    Phase,
    StateStore,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import BundleParityError
from autom8_asana.automation.workflows.onboarding_walkthrough.personalization_gate import (
    PersonalizationError,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.template_comment import _mask_guid
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TaskOfficeMismatch,
)

# --- Probe constants (real Sand Lake shapes; GUID is a canonical v4) ---
GUID = "1b271a63-33ff-4135-a92d-f1ef0eeea062"
ADDR = "1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com"
FOREIGN_GUID = "b167331c-536f-4996-9b2d-2f696f35f556"
SLUG = "207688021de88a6d7231e1d08ea77a85"
PLAY_GID = "1215823342887129"
CLINIC = "Sand Lake Dental"
DECK_URL = f"https://decks.cntently.com/{SLUG}/"

SERVED = b"<html>the frozen served deck for Sand Lake Dental</html>"
SERVED_SHA = hashlib.sha256(SERVED).hexdigest()


def _fake_freeze_bytes(gated_address: str, client_name: str) -> bytes:
    """Frozen bytes carrying EXACTLY the gated address (so the exclusivity oracle passes)."""
    return f"<html>deck for {client_name} — booking inbox {gated_address}</html>".encode()


async def _fake_freeze(**kwargs: object) -> bytes:
    return _fake_freeze_bytes(str(kwargs["gated_address"]), str(kwargs["client_name"]))


def _mock_client() -> MagicMock:
    """A bare client — the runner routes all Asana I/O through faked collaborators."""
    return MagicMock()


def _store(tmp_path: object) -> StateStore:
    return StateStore(tmp_path / "state")  # type: ignore[operator]


def _seed_produced(store: StateStore, *, frozen_sha256: str, guid: str = GUID) -> OfficeState:
    """Seed a committed Phase-1 (PRODUCED) manifest — the crash/resume entry state."""
    state = OfficeState(
        play_gid=PLAY_GID,
        office_guid_masked=_mask_guid(guid),
        clinic=CLINIC,
        slug=SLUG,
        deck_url=DECK_URL,
        frozen_sha256=frozen_sha256,
        phase=Phase.PRODUCED,
        posts={"link": None, "template": None, "card": None},
        updated_at="2026-07-07T00:00:00+00:00",
    )
    store.save(state)
    return state


def _produce_patches(stack: ExitStack, *, guid: str = GUID) -> dict[str, MagicMock]:
    """Patch the Phase-1 heavy collaborators; return the mocks for assertion."""
    m: dict[str, MagicMock] = {}
    m["preflight"] = stack.enter_context(
        patch.object(orunner, "_preflight", new=AsyncMock(return_value=("PLAY: …", "ACTIVE")))
    )
    m["resolve"] = stack.enter_context(
        patch.object(orunner, "_resolve_office_guid", new=AsyncMock(return_value=guid))
    )
    m["freeze"] = stack.enter_context(
        patch.object(orunner, "freeze_walkthrough_deck", new=AsyncMock(side_effect=_fake_freeze))
    )
    m["mint"] = stack.enter_context(patch.object(orunner, "mint_slug", return_value=SLUG))
    # posters + curl must never be reached in Phase-1 (the HALT).
    m["link"] = stack.enter_context(patch.object(orunner, "post_link_on_play", new=AsyncMock()))
    m["template"] = stack.enter_context(
        patch.object(orunner, "post_template_comment", new=AsyncMock())
    )
    m["card"] = stack.enter_context(patch.object(orunner, "post_contact_card", new=AsyncMock()))
    m["curl"] = stack.enter_context(patch.object(orunner, "_fetch_served_bytes", new=AsyncMock()))
    return m


def _resume_patches(
    stack: ExitStack, *, resolved_guid: str = GUID, served: bytes = SERVED
) -> dict[str, AsyncMock]:
    """Patch the Phase-2 heavy collaborators; return the mocks for assertion."""
    m: dict[str, AsyncMock] = {}
    m["resolve"] = stack.enter_context(
        patch.object(orunner, "_resolve_office_guid", new=AsyncMock(return_value=resolved_guid))
    )
    m["curl"] = stack.enter_context(
        patch.object(orunner, "_fetch_served_bytes", new=AsyncMock(return_value=served))
    )
    m["link"] = stack.enter_context(
        patch.object(
            orunner,
            "post_link_on_play",
            new=AsyncMock(return_value=SimpleNamespace(story_gid="LINK_STORY", outcome="posted")),
        )
    )
    m["template"] = stack.enter_context(
        patch.object(
            orunner,
            "post_template_comment",
            new=AsyncMock(return_value=SimpleNamespace(story_gid="TMPL_STORY", outcome="posted")),
        )
    )
    m["card"] = stack.enter_context(
        patch.object(
            orunner,
            "post_contact_card",
            new=AsyncMock(return_value=SimpleNamespace(story_gid="CARD_STORY", outcome="posted")),
        )
    )
    return m


# ============================================================ Phase-1 produce (the HALT)


class TestPhase1Produce:
    async def test_produce_halts_without_posting_or_running_wrangler(self, tmp_path) -> None:
        """Phase-1 stages + surfaces the reserved ``wrangler`` command and HALTS: no Asana
        post, no ``curl``, no ``wrangler`` executed. The command is SURFACED (a string in the
        result), never fired."""
        store = _store(tmp_path)
        with ExitStack() as stack:
            m = _produce_patches(stack)
            result = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="produce",
                store=store,
                deploy_base=tmp_path / "deploy",
                project_name="contente-decks",
            )
        assert result.phase is Phase.PRODUCED
        assert result.outcome == "produced"
        assert result.slug == SLUG
        assert result.deck_url == DECK_URL
        # The reserved lever is SURFACED, not executed.
        assert result.wrangler_command is not None
        assert "wrangler pages deploy" in result.wrangler_command
        assert str(tmp_path / "deploy" / PLAY_GID) in result.wrangler_command
        # No post, no curl (the HALT).
        m["link"].assert_not_awaited()
        m["template"].assert_not_awaited()
        m["card"].assert_not_awaited()
        m["curl"].assert_not_awaited()

    async def test_produce_stages_deck_and_records_produced(self, tmp_path) -> None:
        """The frozen deck is staged into the per-office deploy root and the manifest is
        committed at PRODUCED with the pinned slug + frozen sha (the resumability keystone)."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        with ExitStack() as stack:
            _produce_patches(stack)
            await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="produce",
                store=store,
                deploy_base=deploy_base,
            )
        # Real stage_deck_bundle wrote the served bytes verbatim under <deploy>/<play>/<slug>/.
        served = deploy_base / PLAY_GID / SLUG / "index.html"
        assert served.is_file()
        assert (deploy_base / PLAY_GID / "_headers").is_file()
        # Manifest committed: PRODUCED, slug pinned, frozen sha == sha of the staged bytes.
        state = store.load(PLAY_GID)
        assert state is not None
        assert state.phase is Phase.PRODUCED
        assert state.slug == SLUG
        assert state.frozen_sha256 == hashlib.sha256(served.read_bytes()).hexdigest()
        assert state.office_guid_masked == _mask_guid(GUID)
        assert state.office_guid_masked != GUID  # never the full guid at rest

    async def test_produce_personalization_gate_refuses_internal_name_before_freeze(
        self, tmp_path
    ) -> None:
        """The operator-confirmed clinic name is gated (fault-13): an internal-nomenclature
        value refuses at ``assert_customer_personalization`` BEFORE any freeze/mint/stage."""
        store = _store(tmp_path)
        with ExitStack() as stack:
            m = _produce_patches(stack)
            with pytest.raises(PersonalizationError):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic="PLAY: Custom Calendar Integration — Sand Lake",
                    phase="produce",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                )
        m["freeze"].assert_not_awaited()
        m["mint"].assert_not_called()
        assert store.load(PLAY_GID) is None  # nothing committed

    async def test_produce_idempotent_mints_slug_once_reused_on_rerun(self, tmp_path) -> None:
        """SLUG-1: the slug is minted ONCE and pinned. A second ``produce`` reuses it (never
        re-mints — re-minting orphans the deployed deck) and does not re-freeze."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        with ExitStack() as stack:
            m = _produce_patches(stack)
            first = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="produce",
                store=store,
                deploy_base=deploy_base,
            )
            second = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="produce",
                store=store,
                deploy_base=deploy_base,
            )
        assert first.slug == second.slug == SLUG
        assert second.outcome == "already_produced"
        assert m["mint"].call_count == 1  # minted once, never re-minted
        assert m["freeze"].await_count == 1  # not re-frozen on the idempotent re-run


# ============================================================ Phase-2 resume (post seam)


class TestPhase2Resume:
    async def test_resume_execute_posts_all_three_task_bound_then_done(self, tmp_path) -> None:
        """GREEN: byte-parity confirmed → post link + template + card, each bound to THIS
        office's PLAY (task_gid=play_gid), then mark DONE with the three story gids."""
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA)
        with ExitStack() as stack:
            m = _resume_patches(stack)
            result = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="resume",
                store=store,
                deploy_base=tmp_path / "deploy",
                execute=True,
            )
        assert result.outcome == "posted"
        assert result.phase is Phase.DONE
        # Every poster bound to THIS office's PLAY (task-bound; only the slug threaded).
        assert m["link"].await_args.kwargs["task_gid"] == PLAY_GID
        assert m["template"].await_args.kwargs["task_gid"] == PLAY_GID
        assert m["card"].await_args.kwargs["play_gid"] == PLAY_GID
        assert m["card"].await_args.kwargs["deck_slug"] == SLUG
        for poster in (m["link"], m["template"], m["card"]):
            poster.assert_awaited_once()
            assert poster.await_args.kwargs["execute"] is True
        # DONE committed with the story gids.
        state = store.load(PLAY_GID)
        assert state is not None
        assert state.phase is Phase.DONE
        assert state.posts == {"link": "LINK_STORY", "template": "TMPL_STORY", "card": "CARD_STORY"}

    async def test_resume_dry_run_default_composes_never_posts(self, tmp_path) -> None:
        """Dry-run (execute=False): the posters run in dry-run (execute=False) and DONE is
        never committed — a preview after the operator deploys, before the execute wave."""
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA)
        with ExitStack() as stack:
            m = _resume_patches(stack)
            result = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="resume",
                store=store,
                deploy_base=tmp_path / "deploy",
                execute=False,
            )
        assert result.outcome == "dry_run"
        for poster in (m["link"], m["template"], m["card"]):
            assert poster.await_args.kwargs["execute"] is False
        state = store.load(PLAY_GID)
        assert state is not None
        assert state.phase is not Phase.DONE  # nothing posted -> not done

    async def test_resume_before_produce_refuses(self, tmp_path) -> None:
        """Resuming an office with no committed Phase-1 manifest refuses (produce first)."""
        store = _store(tmp_path)
        with ExitStack() as stack:
            m = _resume_patches(stack)
            with pytest.raises(FloodgatesRefused, match="produce"):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=CLINIC,
                    phase="resume",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                    execute=True,
                )
        m["link"].assert_not_awaited()

    async def test_resume_already_done_skips(self, tmp_path) -> None:
        """A DONE office short-circuits (idempotent skip) — no re-post."""
        store = _store(tmp_path)
        state = _seed_produced(store, frozen_sha256=SERVED_SHA)
        state.phase = Phase.DONE
        store.save(state)
        with ExitStack() as stack:
            m = _resume_patches(stack)
            result = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="resume",
                store=store,
                deploy_base=tmp_path / "deploy",
                execute=True,
            )
        assert result.outcome == "already_done"
        m["link"].assert_not_awaited()
        m["curl"].assert_not_awaited()


# ============================================================ byte-parity gate (RED teeth)


class TestPhase2ByteParityGate:
    async def test_byte_parity_mismatch_refuses_no_post(self, tmp_path) -> None:
        """served ≠ frozen → BundleParityError, and NO comment is posted (never link a deck
        whose served bytes are not byte-identical to what was frozen)."""
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA)
        drifted = SERVED + b"<!-- CF re-rendered / drifted -->"
        with ExitStack() as stack:
            m = _resume_patches(stack, served=drifted)
            with pytest.raises(BundleParityError):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=CLINIC,
                    phase="resume",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                    execute=True,
                )
        m["link"].assert_not_awaited()
        m["template"].assert_not_awaited()
        m["card"].assert_not_awaited()
        state = store.load(PLAY_GID)
        assert state is not None
        assert state.phase is not Phase.DONE


# ============================================================ C-1 task-binding (RED teeth)


class TestC1TaskBinding:
    async def test_c1_own_guid_posts_template_without_precomputed_pairing(self, tmp_path) -> None:
        """GREEN C-1: the office's live-resolved guid matches the manifest → posts. The runner
        threads ONLY the slug and calls the template poster WITHOUT a precomputed office_guid
        (office_guid=None) — the poster resolves identity FROM the task, so a scrambled
        (guid, task) pairing is impossible by construction (the CASE C-1 leak, closed)."""
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA, guid=GUID)
        with ExitStack() as stack:
            m = _resume_patches(stack, resolved_guid=GUID)
            await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="resume",
                store=store,
                deploy_base=tmp_path / "deploy",
                execute=True,
            )
        m["template"].assert_awaited_once()
        kwargs = m["template"].await_args.kwargs
        assert kwargs["task_gid"] == PLAY_GID
        # STRUCTURAL teeth: no precomputed guid is ever threaded — identity is task-resolved.
        assert kwargs.get("office_guid") is None

    async def test_c1_foreign_guid_refuses_task_office_mismatch_no_post(self, tmp_path) -> None:
        """RED C-1 (the scar): the PLAY task at play_gid live-resolves to a DIFFERENT office
        than the manifest recorded (a mis-keyed / crash-swapped manifest) → TaskOfficeMismatch,
        BEFORE the byte-parity curl and BEFORE any post. Reuses the #205 exception."""
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA, guid=GUID)  # manifest office = GUID
        with ExitStack() as stack:
            m = _resume_patches(stack, resolved_guid=FOREIGN_GUID)  # live task resolves to another
            with pytest.raises(TaskOfficeMismatch):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=CLINIC,
                    phase="resume",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                    execute=True,
                )
        m["curl"].assert_not_awaited()  # refused before the parity curl
        m["link"].assert_not_awaited()
        m["template"].assert_not_awaited()
        m["card"].assert_not_awaited()


# ============================================================ crash-resume (Phase-committed)


class TestCrashResume:
    async def test_crash_from_produced_runs_only_phase2(self, tmp_path) -> None:
        """A committed PRODUCED manifest (Phase-1 done, then crash) + ``resume`` runs ONLY
        Phase-2: it reuses the pinned slug (no re-mint/re-freeze) and posts, reaching DONE."""
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA)
        with ExitStack() as stack:
            # freeze/mint patched to ASSERT they are NOT called on the resume leg.
            freeze = stack.enter_context(
                patch.object(orunner, "freeze_walkthrough_deck", new=AsyncMock())
            )
            mint = stack.enter_context(patch.object(orunner, "mint_slug", new=MagicMock()))
            _resume_patches(stack)
            result = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="resume",
                store=store,
                deploy_base=tmp_path / "deploy",
                execute=True,
            )
        assert result.phase is Phase.DONE
        assert result.slug == SLUG  # reused, not re-minted
        freeze.assert_not_awaited()
        mint.assert_not_called()
