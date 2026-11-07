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
* **D9 name confirmation** (``TestD9NameConfirmation``): produce stops unless the PLAY title's
  clinic part, the parent Business name and ``--clinic`` agree; it freezes the canonical
  Business name, and the already-produced path re-checks against the frozen name.
* **D10(b) rendered-deck check** (``TestD10bRenderCheck``): produce renders the staged deck
  before PRODUCED; a refusal removes the never-deployed slug dir and saves no state, and the
  already-produced path re-runs the check but never deletes a deck that may be live.
"""

from __future__ import annotations

import hashlib
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough import (
    office_resolution,
    render_check,
)
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
from autom8_asana.automation.workflows.onboarding_walkthrough.template_comment import (
    TemplateCommentRefused,
    _mask_guid,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TaskOfficeMismatch,
)

# --- Probe constants (real Sand Lake shapes; GUID is a canonical v4) ---
GUID = "1b271a63-33ff-4135-a92d-f1ef0eeea062"
ADDR = "1b271a63-33ff-4135-a92d-f1ef0eeea062@appointments.contenteapp.com"
FOREIGN_GUID = "b167331c-536f-4996-9b2d-2f696f35f556"
# Shares GUID's first-8 chars ("1b271a63") -> the SAME 8-char mask, but a DIFFERENT full guid:
# the 32-bit mask-prefix collision the ★C-1 guard must catch on the full SHA-256 digest.
COLLIDING_MASK_GUID = "1b271a63-0000-4000-8000-000000000000"
SLUG = "207688021de88a6d7231e1d08ea77a85"
PLAY_GID = "1215823342887129"
CLINIC = "Sand Lake Dental"
DECK_URL = f"https://decks.cntently.com/{SLUG}/"

BUSINESS_GID = "1200000000000042"

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


def _seed_produced(
    store: StateStore, *, frozen_sha256: str, guid: str = GUID, clinic: str = CLINIC
) -> OfficeState:
    """Seed a committed Phase-1 (PRODUCED) manifest — the crash/resume entry state."""
    state = OfficeState(
        play_gid=PLAY_GID,
        office_guid_masked=_mask_guid(guid),
        office_guid_sha256=hashlib.sha256(guid.encode()).hexdigest(),
        clinic=clinic,
        slug=SLUG,
        deck_url=DECK_URL,
        frozen_sha256=frozen_sha256,
        phase=Phase.PRODUCED,
        posts={"link": None, "template": None, "card": None},
        updated_at="2026-07-07T00:00:00+00:00",
    )
    store.save(state)
    return state


def _receipt(slug: str = SLUG) -> render_check.RenderReceipt:
    return render_check.RenderReceipt(
        slug=slug,
        browser_path="/opt/synthetic/chrome-headless-shell",
        browser_kind="headless-shell",
        browser_version="Synthetic Headless 1.0",
        checked_at="2026-11-07T00:00:00+00:00",
        outcome="pass",
    )


def _play_title(clinic_part: str) -> str:
    return f"PLAY: Custom Calendar Integration — {clinic_part}"


def _produce_patches(
    stack: ExitStack,
    *,
    guid: str | None = GUID,
    names: dict[str, tuple[str, str | None]] | None = None,
    business_gid: str | None = BUSINESS_GID,
) -> dict[str, MagicMock]:
    """Patch the Phase-1 heavy collaborators; return the mocks for assertion.

    ``names`` maps a PLAY gid to ``(title clinic part, Business name)`` for the D9 walk;
    the default is the matching ``(CLINIC, CLINIC)`` for ``PLAY_GID``. The Business walk is
    patched at its SOURCE module (``office_resolution``) and returns a duck-typed
    resolution, so these patches also load against a runner that predates D9.
    """
    names = names if names is not None else {PLAY_GID: (CLINIC, CLINIC)}

    async def _preflight(_client: object, gid: str) -> tuple[str, str]:
        return _play_title(names[gid][0]), "ACTIVE"

    async def _walk(_client: object, *, task_gid: str, **_kw: object) -> SimpleNamespace:
        return SimpleNamespace(
            business_gid=business_gid,
            company_id=guid,
            method="hierarchy",
            ancestor_depth=1,
            candidates=(),
            business_name=names[task_gid][1],
        )

    m: dict[str, MagicMock] = {}
    m["preflight"] = stack.enter_context(
        patch.object(orunner, "_preflight", new=AsyncMock(side_effect=_preflight))
    )
    m["walk"] = stack.enter_context(
        patch.object(office_resolution, "resolve_business_gid", new=AsyncMock(side_effect=_walk))
    )
    # The produce path walks ONCE via resolve_business_gid; the phone-fallback resolver must
    # not be reached (asserted by the D9 tests).
    m["resolve"] = stack.enter_context(
        patch.object(orunner, "_resolve_office_guid", new=AsyncMock(return_value=guid))
    )
    m["freeze"] = stack.enter_context(
        patch.object(orunner, "freeze_walkthrough_deck", new=AsyncMock(side_effect=_fake_freeze))
    )
    m["mint"] = stack.enter_context(patch.object(orunner, "mint_slug", return_value=SLUG))
    # D10(b): the render check is faked (no browser in unit tests). ``create=True`` lets the
    # stack load against a runner that predates the check (the teeth-proof RED).
    m["render"] = stack.enter_context(
        patch.object(
            orunner,
            "check_staged_deck",
            create=True,
            side_effect=lambda _root, slug, **_kw: _receipt(slug),
        )
    )
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
        # The reserved lever is SURFACED, not executed — and targets the WAVE-SHARED root
        # (no per-office nesting: per-office deploys orphaned every prior office's deck).
        assert result.wrangler_command == (
            f"wrangler pages deploy {tmp_path / 'deploy'} --project-name=contente-decks"
        )
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
        # Real stage_deck_bundle wrote the served bytes verbatim under the WAVE-SHARED
        # <deploy>/<slug>/ (no per-office nesting — TDD §8 accumulating root).
        served = deploy_base / SLUG / "index.html"
        assert served.is_file()
        assert (deploy_base / "_headers").is_file()
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
        internal = "PLAY: Custom Calendar Integration — Harbor Light"
        with ExitStack() as stack:
            # Title and Business carry the same value, so D9 passes and the
            # personalization gate is what refuses.
            m = _produce_patches(stack, names={PLAY_GID: (internal, internal)})
            with pytest.raises(PersonalizationError):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=internal,
                    phase="produce",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                )
        m["freeze"].assert_not_awaited()
        m["mint"].assert_not_called()
        assert store.load(PLAY_GID) is None  # nothing committed

    async def test_produce_personalization_gate_refuses_control_char_before_freeze(
        self, tmp_path
    ) -> None:
        """The owned personalization gate rejects an embedded control char (newline) in the
        operator-confirmed clinic name BEFORE any freeze/mint/stage — the owned freeze floor
        no longer leans on the vendored producer's CLIENT-CONTROL-CHARS gate alone."""
        store = _store(tmp_path)
        with ExitStack() as stack:
            m = _produce_patches(stack)
            with pytest.raises(PersonalizationError) as excinfo:
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic="Sand Lake\nDental",
                    phase="produce",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                )
        assert excinfo.value.detail == "control_char"
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

    async def test_two_office_wave_accumulates_into_shared_root(self, tmp_path) -> None:
        """WAVE-SHARED root (TDD §8): two offices produce into ONE deploy_base — both slug
        dirs accumulate as siblings, ONE ``_headers``, and both surfaced commands are the
        IDENTICAL shared-root command (per-office nesting would have orphaned office A's
        deck the moment office B deployed: Pages serves latest-deployment-only)."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        slug_b = "fedcba9876543210aabbccddeeff0011"
        play_b = "1215823342887130"
        clinic_b = "Harbor Light Chiropractic"
        with ExitStack() as stack:
            _produce_patches(
                stack, names={PLAY_GID: (CLINIC, CLINIC), play_b: (clinic_b, clinic_b)}
            )
            # Re-patch mint on top: office A gets SLUG, office B gets slug_b.
            stack.enter_context(patch.object(orunner, "mint_slug", side_effect=[SLUG, slug_b]))
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
                play_gid=play_b,
                clinic=clinic_b,
                phase="produce",
                store=store,
                deploy_base=deploy_base,
            )
        # Both decks accumulated as SIBLINGS in the one shared root; office A untouched.
        assert (deploy_base / SLUG / "index.html").is_file()
        assert (deploy_base / slug_b / "index.html").is_file()
        assert {p.name for p in deploy_base.iterdir()} == {"_headers", SLUG, slug_b}
        # ONE identical shared-root command surfaced by both (deck-host default project).
        assert first.wrangler_command == second.wrangler_command
        assert first.wrangler_command == (
            f"wrangler pages deploy {deploy_base} --project-name=deck-host"
        )


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

    async def test_c1_mask_prefix_collision_refuses_task_office_mismatch_no_post(
        self, tmp_path
    ) -> None:
        """RED→GREEN (crown C-1): a foreign office whose live-resolved guid shares the manifest's
        8-char MASK but differs in the FULL guid must be REFUSED. The 8-char mask is only 32 bits
        and collides; the guard decides on the full SHA-256 identity digest, so a mask-prefix
        collision still raises ``TaskOfficeMismatch`` and posts nothing. Pre-fix (mask-only
        guard) this colliding guid SLIPPED THROUGH -> a foreign deck onto this office's PLAY."""
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA, guid=GUID)  # manifest office = GUID
        # The colliding guid genuinely shares the mask but is a different full identity.
        assert _mask_guid(COLLIDING_MASK_GUID) == _mask_guid(GUID)
        assert COLLIDING_MASK_GUID != GUID
        with ExitStack() as stack:
            m = _resume_patches(stack, resolved_guid=COLLIDING_MASK_GUID)
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


class TestStagedInRoot:
    """An already-produced office must have its pinned deck in THIS root, byte-exact."""

    def _leaf(self, root, slug, body: bytes):
        (root / slug).mkdir(parents=True)
        (root / slug / "index.html").write_bytes(body)

    def test_present_and_matching_passes(self, tmp_path) -> None:
        import hashlib

        from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates import (
            office_runner as orun,
        )

        slug = "c" * 32
        self._leaf(tmp_path, slug, b"<html>deck</html>")
        orun._assert_staged_in_root(
            tmp_path, slug=slug, frozen_sha256=hashlib.sha256(b"<html>deck</html>").hexdigest()
        )

    def test_missing_leaf_refuses(self, tmp_path) -> None:
        import pytest

        from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates import (
            office_runner as orun,
        )

        with pytest.raises(orun.StagedDeckMissing, match="different --deploy-base"):
            orun._assert_staged_in_root(tmp_path, slug="c" * 32, frozen_sha256="0" * 64)

    def test_drifted_leaf_refuses(self, tmp_path) -> None:
        import pytest

        from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates import (
            office_runner as orun,
        )

        slug = "c" * 32
        self._leaf(tmp_path, slug, b"<html>tampered</html>")
        with pytest.raises(orun.StagedDeckMissing, match="drifted"):
            orun._assert_staged_in_root(tmp_path, slug=slug, frozen_sha256="0" * 64)


class TestMissingCardIsNotDone:
    """No contact card -> NOT done, so the runbook's 'add a contact, re-run' actually retries."""

    async def _resume(self, tmp_path, store, card_ns):
        with ExitStack() as stack:
            m = _resume_patches(stack)
            m["card"].return_value = card_ns
            return await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=CLINIC,
                phase="resume",
                store=store,
                deploy_base=tmp_path / "deploy",
                execute=True,
            )

    async def test_no_card_stays_deploy_confirmed_then_retry_reaches_done(self, tmp_path) -> None:
        store = _store(tmp_path)
        _seed_produced(store, frozen_sha256=SERVED_SHA)
        first = await self._resume(
            tmp_path, store, SimpleNamespace(story_gid=None, outcome="no_contacts")
        )
        state = store.load(PLAY_GID)
        assert state is not None
        assert first.phase is Phase.DEPLOY_CONFIRMED
        assert state.phase is Phase.DEPLOY_CONFIRMED  # not DONE: a re-run must re-enter resume
        assert state.posts["card"] is None
        assert state.posts["link"] == "LINK_STORY"

        # Operator adds the contact; the re-run retries the card and only then reaches DONE.
        second = await self._resume(
            tmp_path, store, SimpleNamespace(story_gid="CARD_STORY", outcome="posted")
        )
        state = store.load(PLAY_GID)
        assert state is not None
        assert second.phase is Phase.DONE
        assert state.phase is Phase.DONE
        assert state.posts["card"] == "CARD_STORY"


# ============================================================ D9 name confirmation (RED teeth)

# Synthetic names only (this repo is public).
D9_CLINIC = "Harbor Light Chiropractic"


class TestD9NameConfirmation:
    """Produce stops unless title clinic == Business name == --clinic (FORK-S1 rule).

    The refusal tests match ``RuntimeError`` + "D9" (not the new exception class), so they
    load against a runner that predates D9: there they FAIL with "DID NOT RAISE", which is
    the pre-change RED of the teeth proof.
    """

    async def test_matching_names_produce_and_freeze_the_canonical_business_name(
        self, tmp_path
    ) -> None:
        """GREEN: the three names agree up to invisible differences (B carries a zero-width
        character and a double space, --clinic a trailing space). Produce runs, the deck
        freezes the CANONICAL Business name, the manifest records it, and the one walk
        supplies the Company ID (the phone-fallback resolver is never reached)."""
        store = _store(tmp_path)
        business = "Harbor Light  Chiropractic\u200b"
        with ExitStack() as stack:
            m = _produce_patches(stack, names={PLAY_GID: (D9_CLINIC, business)})
            result = await run_office(
                _mock_client(),
                play_gid=PLAY_GID,
                clinic=D9_CLINIC + " ",
                phase="produce",
                store=store,
                deploy_base=tmp_path / "deploy",
            )
        assert result.outcome == "produced"
        m["freeze"].assert_awaited_once()
        assert m["freeze"].await_args.kwargs["client_name"] == D9_CLINIC
        assert m["freeze"].await_args.kwargs["gated_address"] == ADDR
        m["walk"].assert_awaited_once()
        m["resolve"].assert_not_awaited()
        state = store.load(PLAY_GID)
        assert state is not None
        assert state.clinic == D9_CLINIC

    async def test_near_miss_business_name_refuses_before_freeze_and_mint(self, tmp_path) -> None:
        """RED: the title says "Centre", the Business says "Center", and --clinic copied the
        title. A visible difference: stop and ask. No freeze, no mint, nothing committed."""
        store = _store(tmp_path)
        title_part = "Harbor Light Family Wellness Centre"
        business = "Harbor Light Family Wellness Center"
        with ExitStack() as stack:
            m = _produce_patches(stack, names={PLAY_GID: (title_part, business)})
            with pytest.raises(RuntimeError, match="D9") as excinfo:
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=title_part,
                    phase="produce",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                )
        message = str(excinfo.value)
        assert PLAY_GID in message
        assert BUSINESS_GID in message
        assert ascii(title_part) in message
        assert ascii(business) in message
        assert "ask the operator" in message
        m["freeze"].assert_not_awaited()
        m["mint"].assert_not_called()
        assert store.load(PLAY_GID) is None

    async def test_no_business_parent_refuses_before_freeze(self, tmp_path) -> None:
        """RED: the walk finds no Business parent. A phone match is not a parent, so the
        name cannot be confirmed: refuse D9 (no phone fallback on the produce path)."""
        store = _store(tmp_path)
        with ExitStack() as stack:
            m = _produce_patches(stack, business_gid=None, names={PLAY_GID: (CLINIC, None)})
            with pytest.raises(RuntimeError, match="D9"):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=CLINIC,
                    phase="produce",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                )
        m["freeze"].assert_not_awaited()
        m["mint"].assert_not_called()

    async def test_confirmed_name_without_company_id_refuses_before_freeze(self, tmp_path) -> None:
        """The name is confirmed but the Business carries no Company ID: refuse (no routing
        address can be composed), and never fall back to a second resolver."""
        store = _store(tmp_path)
        with ExitStack() as stack:
            m = _produce_patches(stack, guid=None)
            with pytest.raises(TemplateCommentRefused, match="no Company ID"):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=CLINIC,
                    phase="produce",
                    store=store,
                    deploy_base=tmp_path / "deploy",
                )
        m["freeze"].assert_not_awaited()
        m["resolve"].assert_not_awaited()

    async def test_already_produced_refuses_when_business_name_differs_from_frozen_clinic(
        self, tmp_path
    ) -> None:
        """RED: the office was produced as "Harbor Light Chiropractic"; since then the title
        and the Business were renamed. Re-surfacing the deploy command would ship a deck with
        the old name, so the already-produced path re-checks D9 against the FROZEN name."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        body = b"<html>staged deck</html>"
        (deploy_base / SLUG).mkdir(parents=True)
        (deploy_base / SLUG / "index.html").write_bytes(body)
        _seed_produced(store, frozen_sha256=hashlib.sha256(body).hexdigest(), clinic=D9_CLINIC)
        renamed = "Harbor Light Spine Center"
        with ExitStack() as stack:
            m = _produce_patches(stack, names={PLAY_GID: (renamed, renamed)})
            with pytest.raises(RuntimeError, match="D9") as excinfo:
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=renamed,
                    phase="produce",
                    store=store,
                    deploy_base=deploy_base,
                )
        assert ascii(D9_CLINIC) in str(excinfo.value)  # the frozen name is the --clinic witness
        m["freeze"].assert_not_awaited()
        m["mint"].assert_not_called()


# ============================================================ D10(b) rendered-deck check (RED teeth)

# Synthetic names only (this repo is public).
D10_CLINIC = "Juniper Ridge Dental"


class TestD10bRenderCheck:
    """Produce renders the staged deck before PRODUCED (FORK-S2 (c), produce step 8b).

    The refusal tests catch the exception and assert the cleanup FIRST, so against a runner
    that predates the check they FAIL on "the staged dir survived" (the teeth-proof RED).
    """

    async def _produce(self, tmp_path, store, deploy_base, m_overrides=None):
        with ExitStack() as stack:
            m = _produce_patches(stack, names={PLAY_GID: (D10_CLINIC, D10_CLINIC)})
            for name, kwargs in (m_overrides or {}).items():
                m[name].configure_mock(**kwargs)
            raised: BaseException | None = None
            try:
                result = await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=D10_CLINIC,
                    phase="produce",
                    store=store,
                    deploy_base=deploy_base,
                )
            except Exception as exc:  # noqa: BLE001 -- the test asserts on it below
                raised, result = exc, None
        return m, result, raised

    async def test_produce_checks_once_with_frozen_sha_and_canonical_clinic(self, tmp_path) -> None:
        """GREEN: the check runs ONCE, on the wave root and the minted slug, with the sha of
        the office guid and the clinic that was frozen; the result carries the receipt."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        m, result, raised = await self._produce(tmp_path, store, deploy_base)
        assert raised is None
        assert result is not None
        assert result.outcome == "produced"
        m["render"].assert_called_once()
        args, kwargs = m["render"].call_args
        assert args == (deploy_base, SLUG)
        assert kwargs == {
            "office_guid_sha256": hashlib.sha256(GUID.encode()).hexdigest(),
            "clinic": D10_CLINIC,
        }
        assert kwargs["clinic"] == m["freeze"].await_args.kwargs["client_name"]
        assert result.render_receipt == _receipt(SLUG)
        state = store.load(PLAY_GID)
        assert state is not None
        assert state.phase is Phase.PRODUCED
        assert (deploy_base / SLUG / "index.html").is_file()

    @pytest.mark.parametrize(
        "exc",
        [
            render_check.RenderCheckRefused("foreign_address", "masked detail"),
            render_check.BrowserUnavailable("browser_not_found", "no browser found"),
        ],
        ids=["RenderCheckRefused", "BrowserUnavailable"],
    )
    async def test_refusal_removes_staged_dir_saves_no_state_and_reraises(
        self, tmp_path, exc
    ) -> None:
        """RED: the check refuses after staging. The never-deployed slug dir is GONE (it would
        ride the next wave deploy), no state file exists, and the same exception surfaces."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        m, result, raised = await self._produce(
            tmp_path, store, deploy_base, {"render": {"side_effect": exc}}
        )
        assert not (deploy_base / SLUG).exists(), "the staged dir survived the refusal"
        assert not store.path_for(PLAY_GID).exists(), "state was saved despite the refusal"
        assert raised is exc
        assert result is None
        # The refusal came AFTER staging: freeze and mint ran, and the root itself survives.
        m["freeze"].assert_awaited_once()
        m["mint"].assert_called_once()
        assert (deploy_base / "_headers").is_file()

    async def test_interrupt_during_check_also_unstages(self, tmp_path) -> None:
        """A KeyboardInterrupt (not an Exception) during the check still removes the staged dir
        and saves no state: the cleanup catches BaseException. Kills the except-Exception mutant."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        with ExitStack() as stack:
            m = _produce_patches(stack, names={PLAY_GID: (D10_CLINIC, D10_CLINIC)})
            m["render"].configure_mock(side_effect=KeyboardInterrupt())
            with pytest.raises(KeyboardInterrupt):
                await run_office(
                    _mock_client(),
                    play_gid=PLAY_GID,
                    clinic=D10_CLINIC,
                    phase="produce",
                    store=store,
                    deploy_base=deploy_base,
                )
        assert not (deploy_base / SLUG).exists(), "the staged dir survived the interrupt"
        assert not store.path_for(PLAY_GID).exists()

    async def test_unexpected_error_from_check_also_unstages(self, tmp_path) -> None:
        """ANY exception from the check unstages, not only the two named refusals."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        boom = OSError("synthetic render crash")
        _m, _result, raised = await self._produce(
            tmp_path, store, deploy_base, {"render": {"side_effect": boom}}
        )
        assert not (deploy_base / SLUG).exists()
        assert not store.path_for(PLAY_GID).exists()
        assert raised is boom

    async def test_refusal_on_pinned_slug_unstages_but_keeps_existing_state(self, tmp_path) -> None:
        """A prior partial run left a PENDING manifest with a pinned slug. The re-run re-stages
        into that slug; a refusal removes the dir and leaves the manifest byte-identical."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        pinned = "0123456789abcdef0123456789abcdef"
        seeded = _seed_produced(store, frozen_sha256="0" * 64, clinic=D10_CLINIC)
        seeded.phase = Phase.PENDING
        seeded.slug = pinned
        store.save(seeded)
        before = store.path_for(PLAY_GID).read_bytes()
        m, _result, raised = await self._produce(
            tmp_path,
            store,
            deploy_base,
            {"render": {"side_effect": render_check.RenderCheckRefused("empty_interp", "x")}},
        )
        assert isinstance(raised, render_check.RenderCheckRefused)
        m["mint"].assert_not_called()  # the pinned slug was reused
        assert m["render"].call_args.args == (deploy_base, pinned)
        assert not (deploy_base / pinned).exists()
        assert store.path_for(PLAY_GID).read_bytes() == before

    async def test_already_produced_rechecks_with_frozen_identity_and_carries_receipt(
        self, tmp_path
    ) -> None:
        """GREEN: the re-surface path re-runs the check with the manifest's sha and clinic
        (the full guid is never at rest), and the result carries the receipt."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        body = b"<html>staged deck</html>"
        (deploy_base / SLUG).mkdir(parents=True)
        (deploy_base / SLUG / "index.html").write_bytes(body)
        seeded = _seed_produced(
            store, frozen_sha256=hashlib.sha256(body).hexdigest(), clinic=D10_CLINIC
        )
        m, result, raised = await self._produce(tmp_path, store, deploy_base)
        assert raised is None
        assert result is not None
        assert result.outcome == "already_produced"
        m["render"].assert_called_once_with(
            deploy_base,
            SLUG,
            office_guid_sha256=seeded.office_guid_sha256,
            clinic=seeded.clinic,
        )
        assert result.render_receipt == _receipt(SLUG)

    async def test_already_produced_refusal_raises_without_deleting_or_changing_state(
        self, tmp_path
    ) -> None:
        """RED: a PRODUCED deck may already be live, so a refusal on the re-surface path raises
        (no deploy command) but leaves the staged dir and the manifest exactly as they were."""
        store = _store(tmp_path)
        deploy_base = tmp_path / "deploy"
        body = b"<html>staged deck</html>"
        (deploy_base / SLUG).mkdir(parents=True)
        (deploy_base / SLUG / "index.html").write_bytes(body)
        _seed_produced(store, frozen_sha256=hashlib.sha256(body).hexdigest(), clinic=D10_CLINIC)
        before = store.path_for(PLAY_GID).read_bytes()
        refusal = render_check.RenderCheckRefused("prepared_for_missing", "x")
        m, result, raised = await self._produce(
            tmp_path, store, deploy_base, {"render": {"side_effect": refusal}}
        )
        assert raised is refusal, "the already-produced path re-surfaced without the check"
        assert result is None
        assert (deploy_base / SLUG / "index.html").read_bytes() == body
        assert store.path_for(PLAY_GID).read_bytes() == before
        m["freeze"].assert_not_awaited()
