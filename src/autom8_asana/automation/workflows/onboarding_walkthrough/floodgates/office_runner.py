"""Two-phase single-office runner — the floodgates state machine (TDD §2/§4).

``run_office`` is a per-office **state machine**, not a straight line. It composes the
already-proven onboarding primitives around the operator-gated Cloudflare deploy:

* **Phase 1 ``produce``** (fully automatable; NO Asana writes, NO client contact):
  positive-select the PLAY -> resolve the office guid pure-Asana (task-bound) -> compose
  the gated routing address -> gate the operator-confirmed clinic name (fault-13) ->
  freeze the deck (Node producer) -> assert exclusive tenant-binding -> mint + PIN the
  capability slug (once; SLUG-1) -> host-stage into a per-office deploy root -> commit the
  manifest at ``PRODUCED`` -> **SURFACE the exact ``wrangler pages deploy`` command and
  HALT**. The reserved CF lever is printed, NEVER executed.
* **Phase 2 ``resume``** (after the operator confirms the deck is live): a ★C-1
  manifest-integrity guard (the manifest keyed to this PLAY MUST describe the office the
  live task resolves to, else ``TaskOfficeMismatch``) -> served byte-parity gate (served
  bytes == frozen sha, or ``BundleParityError`` — never link a drifted deck) -> post the
  three marker-idempotent PLAY comments, each TASK-BOUND to THIS office's PLAY with ONLY
  the slug threaded across posters (identity resolved FROM the task, closing the CASE C-1
  cross-tenant leak BY CONSTRUCTION) -> commit ``DONE``.

Reserved-lever boundary: DOES {resolve, freeze, mint, stage, verify-parity, post-comments};
SURFACES {wrangler deploy}; NEVER {runs wrangler, sends the client email}.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from autom8y_core.helpers.routing import format_routing_address
from autom8y_log import get_logger

from autom8_asana.automation.workflows.onboarding_walkthrough.constants import (
    WALKTHROUGH_DECK_DEFAULT,
    WALKTHROUGH_PRODUCER_DIR_ENV_VAR,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.contact_synthesis import (
    post_contact_card,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.deck_manifests import load_title
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    OfficeState,
    Phase,
    StateStore,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import (
    mint_slug,
    stage_deck_bundle,
    verify_bundle_parity,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.link_on_play import (
    DECK_HOST,
    _preflight,
    post_link_on_play,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.personalization_gate import (
    assert_customer_personalization,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    freeze_walkthrough_deck,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.template_comment import (
    _mask_guid,
    _resolve_office_guid,
    post_template_comment,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    TaskOfficeMismatch,
    assert_exclusive_tenant_binding,
)

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

logger = get_logger(__name__)

__all__ = [
    "FloodgatesRefused",
    "OfficeRunResult",
    "run_office",
]


class FloodgatesRefused(RuntimeError):
    """Fail-closed runner refusal (resume-before-produce, unknown phase, served-fetch fail).

    NOT transient for the config/order arms: re-running reproduces them; callers must fail
    closed. The load-bearing cross-tenant refusal is ``TaskOfficeMismatch`` (tenant_binding);
    the byte-parity refusal is ``BundleParityError`` (host_bundle) — both surface directly.
    """


@dataclass
class OfficeRunResult:
    """The outcome of one office run (both phases share the shape; fields phase-dependent).

    ``outcome`` is one of ``"produced"`` | ``"already_produced"`` (Phase-1) |
    ``"posted"`` | ``"dry_run"`` | ``"already_done"`` (Phase-2). ``wrangler_command`` is the
    surfaced reserved-lever command on Phase-1 (``None`` on Phase-2).
    """

    play_gid: str
    phase: Phase
    outcome: str
    slug: str
    deck_url: str
    deploy_root: str
    wrangler_command: str | None
    posts: dict[str, str | None]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _default_producer_dir() -> Path:
    """Resolve the Node producer dir: env override, else the repo-vendored tree.

    CONFIG per ADR-WALK-B2 (never hardcoded to a worktree path). The env var is the
    primary mechanism; the computed vendored path (``<repo>/vendor/deck-producer``) is the
    local-operator convenience default. ``parents[6]`` walks
    ``floodgates -> onboarding_walkthrough -> workflows -> automation -> autom8_asana ->
    src -> <repo>``.
    """
    env = os.environ.get(WALKTHROUGH_PRODUCER_DIR_ENV_VAR)
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[6] / "vendor" / "deck-producer"


def _surface_wrangler_command(office_deploy_root: Path, project_name: str | None) -> str:
    """The exact reserved-lever command to SURFACE (never execute).

    Run by the operator in the CF-authed env (memory scar: ``direnv exec ~/life``). The
    project name is operator-domain; a placeholder is surfaced when it is not supplied.
    """
    project = project_name or "<your-decks-pages-project>"
    return f"wrangler pages deploy {office_deploy_root} --project-name={project}"


async def _fetch_served_bytes(deck_url: str, *, timeout_s: float = 30.0) -> bytes:
    """Fetch the live served deck bytes via ``curl`` (the post-deploy byte-parity source).

    Reserved-lever-adjacent READ only (no mutation). A non-zero curl exit is a fail-closed
    ``FloodgatesRefused`` (a deck that will not fetch cannot be parity-verified, so it is not
    linked). Isolated as a module function so the batch/unit tests fake it.
    """
    proc = await asyncio.create_subprocess_exec(
        "curl",
        "-fsSL",
        "--max-time",
        str(int(timeout_s)),
        deck_url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout_s + 5)
    if proc.returncode != 0:
        detail = (stderr_b or b"").decode("utf-8", "replace").strip()[:200]
        raise FloodgatesRefused(
            f"served-deck fetch failed (curl exit={proc.returncode}) for {deck_url}: {detail}"
        )
    return stdout_b or b""


def _assert_served_parity(*, served_bytes: bytes, slug: str, expected_sha256: str) -> str:
    """Assert served bytes hash-match the frozen sha, reusing ``verify_bundle_parity``.

    Stages the fetched bytes into a throwaway deploy-root layout and runs the SAME proven
    predicate (host_bundle.py:155-180) the stage path uses — never a reimplemented hash
    compare. Raises ``BundleParityError`` on drift.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / slug).mkdir(parents=True)
        (root / slug / "index.html").write_bytes(served_bytes)
        return verify_bundle_parity(deploy_root=root, slug=slug, expected_sha256=expected_sha256)


async def _run_produce(
    client: AsanaClient,
    *,
    play_gid: str,
    clinic: str,
    store: StateStore,
    deploy_base: Path,
    producer_dir: Path,
    deck_template: str,
    project_name: str | None,
) -> OfficeRunResult:
    office_deploy_root = deploy_base / play_gid
    existing = store.load(play_gid)
    if existing is not None and existing.phase in (
        Phase.PRODUCED,
        Phase.DEPLOY_CONFIRMED,
        Phase.DONE,
    ):
        # Already produced: reuse the PINNED slug, re-surface the command, NEVER re-mint
        # (re-minting orphans the deployed deck — SLUG-1) and never re-freeze.
        return OfficeRunResult(
            play_gid=play_gid,
            phase=existing.phase,
            outcome="already_produced",
            slug=existing.slug,
            deck_url=existing.deck_url,
            deploy_root=str(office_deploy_root),
            wrangler_command=_surface_wrangler_command(office_deploy_root, project_name),
            posts=dict(existing.posts),
        )

    # 1. Positive selection (name + ACTIVE membership) — reuse link_on_play preflight.
    await _preflight(client, play_gid)
    # 2. Resolve the office guid pure-Asana, bound to THIS task.
    office_guid = await _resolve_office_guid(client, task_gid=play_gid)
    # 3. Compose the gated routing address (raises ValueError on a malformed guid).
    gated_address = format_routing_address(office_guid)
    # 4. Gate the operator-confirmed clinic name (fault-13) BEFORE freeze.
    assert_customer_personalization(clinic)
    # 5. Freeze — the SOLE freezer (Node producer).
    title = load_title(deck_template)
    frozen_bytes = await freeze_walkthrough_deck(
        producer_dir=producer_dir,
        deck_template=deck_template,
        gated_address=gated_address,
        client_name=clinic,
        title=title,
        out_filename=f"{play_gid}.html",
    )
    # 6. Exclusivity oracle: the frozen deck binds to EXACTLY this office's address.
    assert_exclusive_tenant_binding(frozen=frozen_bytes, gated_address=gated_address)
    # 7. Mint the slug ONCE (reuse a pinned one from a prior partial run — SLUG-1).
    slug = existing.slug if (existing is not None and existing.slug) else mint_slug()
    # 8. Host-stage into the per-office deploy root (audience gate + write-back parity).
    frozen_sha256 = hashlib.sha256(frozen_bytes).hexdigest()
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tf:
        tf.write(frozen_bytes)
        artifact = Path(tf.name)
    try:
        stage_deck_bundle(
            deck_template=deck_template,
            frozen_artifact=artifact,
            slug=slug,
            deploy_root=office_deploy_root,
        )
    finally:
        artifact.unlink(missing_ok=True)

    deck_url = f"https://{DECK_HOST}/{slug}/"
    # 9. Commit PRODUCED (atomic per-office manifest; mask the guid at rest).
    state = OfficeState(
        play_gid=play_gid,
        office_guid_masked=_mask_guid(office_guid),
        clinic=clinic,
        slug=slug,
        deck_url=deck_url,
        frozen_sha256=frozen_sha256,
        phase=Phase.PRODUCED,
        posts={"link": None, "template": None, "card": None},
        updated_at=_now(),
    )
    store.save(state)
    logger.info(
        "floodgates_office_produced",
        play_gid=play_gid,
        slug=slug,
        deploy_root=str(office_deploy_root),
    )
    return OfficeRunResult(
        play_gid=play_gid,
        phase=Phase.PRODUCED,
        outcome="produced",
        slug=slug,
        deck_url=deck_url,
        deploy_root=str(office_deploy_root),
        wrangler_command=_surface_wrangler_command(office_deploy_root, project_name),
        posts=dict(state.posts),
    )


async def _run_resume(
    client: AsanaClient,
    *,
    play_gid: str,
    store: StateStore,
    deploy_base: Path,
    execute: bool,
) -> OfficeRunResult:
    office_deploy_root = str(deploy_base / play_gid)
    state = store.load(play_gid)
    if state is None or state.phase is Phase.PENDING:
        raise FloodgatesRefused(
            f"office {play_gid} has no committed Phase-1 manifest; run --phase produce first"
        )
    if state.phase is Phase.DONE:
        return OfficeRunResult(
            play_gid=play_gid,
            phase=Phase.DONE,
            outcome="already_done",
            slug=state.slug,
            deck_url=state.deck_url,
            deploy_root=office_deploy_root,
            wrangler_command=None,
            posts=dict(state.posts),
        )

    # ★ C-1 manifest-integrity guard: the manifest keyed to play_gid MUST describe the office
    #   whose LIVE PLAY task is play_gid. Re-resolve the guid FROM the task and assert its mask
    #   equals the recorded mask; a mismatch means this manifest belongs to another office
    #   (mis-keyed / crash-swap) -> TaskOfficeMismatch (reuse #205), refuse BEFORE any curl/post.
    task_office_guid = await _resolve_office_guid(client, task_gid=play_gid)
    if _mask_guid(task_office_guid) != state.office_guid_masked:
        raise TaskOfficeMismatch(
            f"manifest for PLAY {play_gid} records office {state.office_guid_masked} but the live "
            f"task resolves to {_mask_guid(task_office_guid)}; refusing fail-closed — this "
            "manifest does not belong to this PLAY's office (mis-keyed / crash-swap)."
        )

    # Byte-parity gate: served bytes == frozen sha, or BundleParityError (never link a deck
    # whose served bytes are not byte-identical to what was frozen). A READ, safe in dry-run.
    served_bytes = await _fetch_served_bytes(state.deck_url)
    _assert_served_parity(
        served_bytes=served_bytes, slug=state.slug, expected_sha256=state.frozen_sha256
    )
    if execute and state.phase is not Phase.DEPLOY_CONFIRMED:
        state.phase = Phase.DEPLOY_CONFIRMED
        state.updated_at = _now()
        store.save(state)

    # Post the three kits, TASK-BOUND: task_gid is THIS office's PLAY and ONLY the slug (via
    # deck_url / deck_slug) is threaded across posters. The template poster is called WITHOUT a
    # precomputed office_guid — it resolves identity FROM the task, so a scrambled (guid, task)
    # pairing is impossible (the CASE C-1 cross-tenant leak, closed by construction).
    link = await post_link_on_play(
        client, task_gid=play_gid, deck_url=state.deck_url, execute=execute
    )
    if execute:
        state.posts["link"] = link.story_gid
        state.updated_at = _now()
        store.save(state)

    template = await post_template_comment(
        client, task_gid=play_gid, deck_url=state.deck_url, clinic=state.clinic, execute=execute
    )
    if execute:
        state.posts["template"] = template.story_gid
        state.updated_at = _now()
        store.save(state)

    card = await post_contact_card(client, play_gid=play_gid, deck_slug=state.slug, execute=execute)
    if execute:
        state.posts["card"] = card.story_gid
        state.phase = Phase.DONE
        state.updated_at = _now()
        store.save(state)
        logger.info("floodgates_office_done", play_gid=play_gid, slug=state.slug)

    return OfficeRunResult(
        play_gid=play_gid,
        phase=state.phase,
        outcome="posted" if execute else "dry_run",
        slug=state.slug,
        deck_url=state.deck_url,
        deploy_root=office_deploy_root,
        wrangler_command=None,
        posts=dict(state.posts),
    )


async def run_office(
    client: AsanaClient,
    *,
    play_gid: str,
    clinic: str,
    phase: str,
    store: StateStore,
    deploy_base: Path,
    producer_dir: Path | None = None,
    deck_template: str = WALKTHROUGH_DECK_DEFAULT,
    project_name: str | None = None,
    execute: bool = False,
) -> OfficeRunResult:
    """Run ONE office through the requested phase (``"produce"`` or ``"resume"``).

    ``produce`` never writes to Asana and never contacts the client — it stages the deck and
    SURFACES the reserved ``wrangler`` command (HALT). ``resume`` posts the three PLAY comments
    (``execute=True``) or previews them (dry-run, the default) after the operator has deployed.
    """
    deploy_base = Path(deploy_base)
    if phase == "produce":
        return await _run_produce(
            client,
            play_gid=play_gid,
            clinic=clinic,
            store=store,
            deploy_base=deploy_base,
            producer_dir=producer_dir or _default_producer_dir(),
            deck_template=deck_template,
            project_name=project_name,
        )
    if phase == "resume":
        return await _run_resume(
            client,
            play_gid=play_gid,
            store=store,
            deploy_base=deploy_base,
            execute=execute,
        )
    raise FloodgatesRefused(f"unknown phase {phase!r}; expected 'produce' or 'resume'")
