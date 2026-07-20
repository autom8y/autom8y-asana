"""Fail-closed pre-surface predicates for the WAVE-SHARED deck-host deploy root (TDD §8).

Cloudflare Pages custom domains serve the LATEST deployment only, and ``wrangler pages
deploy <root>`` publishes the WHOLE tree as an immutable snapshot. Two consequences are
load-bearing once the deploy root is shared and accumulating (Option B, stage-INTO-deck-host):

* **Anything in the root gets PUBLISHED** — a stray file or a non-capability-shaped dir
  becomes a guessable public path on the deck host. The allowlist here is therefore
  exhaustive AND recursive-exact: ``_headers`` + non-symlink directories matching
  ``^[0-9a-f]{32}$`` (each holding EXACTLY ``index.html``, nothing else), NOTHING else.
  A nested stray (``<slug>/draft.html``, ``<slug>/.DS_Store``, ``<slug>/assets/``) would
  be published verbatim at ``https://<host>/<slug>/<name>`` — unreviewed,
  parity-unverified bytes at a live capability path — so it refuses exactly like a
  root-level stray. The dead legacy base32 slug shape is refused by design
  (CH-01: ``od67utt5…`` is SUPERSEDED-DEAD; a base32 dir in the root is a staging error).
* **Anything MISSING from the root gets 404'd** — a partial-root deploy orphans every
  LIVE client deck it omits. The no-orphan predicate demands the staged root be a
  SUPERSET of the committed deck-host ledger's non-revoked slugs BEFORE the wrangler
  command is surfaced. A missing/unreadable ledger is REFUSAL, not permission.
* **``_headers`` drift is a guard-header regression on ALL decks** — the shared root's
  ``_headers`` must be byte-identical to :data:`host_bundle.HEADERS_FILE_CONTENT`.

Every predicate raises :class:`DeployRootRefused` (LOUD, fail-closed) and the batch then
surfaces NO wrangler command. The guard never mutates the root — it only reads.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, NoReturn

from autom8y_log import get_logger

from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import (
    HEADERS_FILE_CONTENT,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

logger = get_logger(__name__)

__all__ = [
    "DeployRootRefused",
    "assert_deploy_root_ready",
    "assert_headers_parity",
    "assert_manifest_superset",
    "assert_root_hygiene",
    "assert_wave_slugs_staged",
    "default_manifest_path",
]

#: The deploy-root allowlist dir shape — identical to ``host_bundle._SLUG_RE`` by contract
#: (32 lowercase hex; 128-bit capability token). Re-stated here so the guard is a pure
#: reader with no dependence on staging internals.
_SLUG_DIR_RE = re.compile(r"^[0-9a-f]{32}$")

_HEADERS_NAME = "_headers"


class DeployRootRefused(RuntimeError):
    """Fail-closed refusal: the deploy root is NOT fit to surface a wrangler command for."""


def default_manifest_path(deploy_root: Path) -> Path:
    """The committed deck-host ledger location relative to the deploy root.

    ``<deploy_root>/../config/deck-manifest.json`` — the deck-host checkout layout
    (``public/`` beside ``config/``; SVR: wrangler.toml ``pages_build_output_dir=public``).
    """
    return deploy_root / ".." / "config" / "deck-manifest.json"


def assert_root_hygiene(deploy_root: Path) -> None:
    """Fail-closed allowlist: ONLY ``_headers`` + 32-lowercase-hex slug dirs, RECURSIVE-EXACT.

    Each slug dir must contain EXACTLY ``index.html`` (an empty/partial slug dir would
    deploy a 404-at-the-capability-URL; anything BEYOND ``index.html`` — a nested stray
    file like ``draft-internal.html``/``index.html.bak``/``.DS_Store`` or a nested subdir
    like ``assets/`` — would be PUBLISHED verbatim at ``<slug>/<name>``: unreviewed,
    parity-unverified bytes at a live capability path). ANY other root entry — stray
    file, non-hex dir, 31-hex, uppercase, a 32-hex-named SYMLINK (its target tree would
    be published), the dead base32 legacy shape — refuses LOUDLY: ``wrangler pages
    deploy`` would publish it verbatim at a guessable non-capability path.

    Raises:
        DeployRootRefused: missing root, stray entries, a slug dir without index.html,
            or a slug dir holding anything beyond index.html.
    """
    if not deploy_root.is_dir():
        _refuse("deploy_root_missing", f"deploy root missing or not a directory: {deploy_root}")

    strays: list[str] = []
    slugless: list[str] = []
    nonexact: list[str] = []
    for child in sorted(deploy_root.iterdir()):
        name = child.name
        if name == _HEADERS_NAME and child.is_file():
            continue
        if child.is_dir() and not child.is_symlink() and _SLUG_DIR_RE.fullmatch(name):
            contents = sorted(entry.name for entry in child.iterdir())
            # A symlinked index.html LEAF would pass is_file() (path-following) and
            # publish its TARGET's bytes at the capability URL — refuse like any
            # other unreviewed-bytes vector (QA residual closed 2026-07-09).
            if (child / "index.html").is_symlink():
                nonexact.append(f"{name}/{{index.html -> symlink}}")
            elif not (child / "index.html").is_file():
                slugless.append(name)
            elif contents != ["index.html"]:
                extras = [entry for entry in contents if entry != "index.html"]
                nonexact.append(f"{name}/{{{', '.join(extras)}}}")
            continue
        strays.append(name)
    if strays:
        _refuse(
            "root_hygiene_stray",
            f"root-hygiene REFUSED for {deploy_root}: non-allowlisted entr(y/ies) {strays!r} — "
            "the allowlist is `_headers` + non-symlink dirs matching ^[0-9a-f]{32}$; anything "
            "else would be PUBLISHED by `wrangler pages deploy` at a guessable non-capability "
            "path (the dead base32 legacy shape is refused by design, CH-01; a 32-hex-named "
            "symlink would publish its TARGET tree)",
        )
    if slugless:
        _refuse(
            "slug_dir_missing_index",
            f"root-hygiene REFUSED for {deploy_root}: slug dir(s) {slugless!r} lack index.html "
            "— deploying would 404 those capability URLs",
        )
    if nonexact:
        _refuse(
            "slug_dir_contents_not_exact",
            f"root-hygiene REFUSED for {deploy_root}: slug dir(s) {nonexact!r} hold entries "
            "beyond index.html — slug dirs must hold EXACTLY index.html; `wrangler pages "
            "deploy` would PUBLISH every nested byte live at <slug>/<name> (unreviewed, "
            "parity-unverified content at a live capability path)",
        )


def assert_headers_parity(deploy_root: Path) -> None:
    """The shared root's ``_headers`` must be byte-identical to ``HEADERS_FILE_CONTENT``.

    Drift here is a guard-header regression (noindex/no-store/no-referrer/nosniff) on
    EVERY deck in the root at once — refused, never deployed.

    Raises:
        DeployRootRefused: ``_headers`` missing or byte-drifted.
    """
    headers = deploy_root / _HEADERS_NAME
    if not headers.is_file():
        _refuse("headers_missing", f"_headers missing from deploy root {deploy_root} (fail-closed)")
    if headers.read_bytes() != HEADERS_FILE_CONTENT.encode("utf-8"):
        _refuse(
            "headers_drift",
            f"_headers at {headers} is NOT byte-identical to host_bundle.HEADERS_FILE_CONTENT — "
            "cross-repo drift would regress the guard headers on ALL decks; refusing to surface "
            "the deploy",
        )


def assert_manifest_superset(deploy_root: Path, *, manifest_path: Path | None = None) -> None:
    """No-orphan predicate: every non-revoked ledger slug MUST be staged in the root.

    The committed deck-host ledger (``config/deck-manifest.json``) is the record of LIVE
    client decks. Deploying a root that omits any non-revoked slug would 404 a live client
    deck (Pages serves whole-tree snapshots). ``status=="revoked"`` entries are exempt;
    every OTHER status is treated as live (fail-closed: not-explicitly-revoked means the
    deploy must carry it). A missing or unreadable ledger REFUSES — absence of the ledger
    is not permission.

    Args:
        deploy_root: The staged wave-shared root.
        manifest_path: Explicit ledger path; default ``<deploy_root>/../config/deck-manifest.json``.

    Raises:
        DeployRootRefused: unreadable/malformed ledger, or any non-revoked slug absent.
    """
    path = manifest_path if manifest_path is not None else default_manifest_path(deploy_root)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _refuse(
            "manifest_unreadable",
            f"deck-manifest ledger missing/unreadable at {path}: {exc} — absence of the ledger "
            "is NOT permission; refusing to surface the deploy (fail-closed)",
        )
    decks = raw.get("decks") if isinstance(raw, dict) else None
    if not isinstance(decks, dict):
        _refuse(
            "manifest_malformed",
            f"deck-manifest ledger at {path} has no 'decks' object — refusing (fail-closed)",
        )
    orphans: list[str] = []
    for slug, entry in decks.items():
        if not isinstance(entry, dict):
            _refuse(
                "manifest_malformed",
                f"deck-manifest entry for slug {slug!r} at {path} is not an object — refusing",
            )
        if entry.get("status") == "revoked":
            continue
        if not (deploy_root / slug / "index.html").is_file():
            orphans.append(slug)
    if orphans:
        _refuse(
            "manifest_orphans",
            f"no-orphan REFUSED: ledger slug(s) {orphans!r} (status != revoked) absent from "
            f"deploy root {deploy_root} — deploying would 404 LIVE client deck(s)",
        )


def assert_wave_slugs_staged(deploy_root: Path, slugs_by_office: Mapping[str, str]) -> None:
    """Wave-level cross-check: every staged-ok office's PINNED slug dir must be in the root.

    Closes the ledger-blind ``already_produced`` window: an office already at ``PRODUCED``
    re-surfaces the wave command WITHOUT re-staging, so if ``--deploy-base`` points at a
    root that lacks that office's slug dir AND the slug is not yet in the committed
    deck-host ledger (the ledger update is an operator lever), the no-orphan predicate
    cannot see the omission — the surfaced deploy would ship WITHOUT that deck. This
    predicate refuses instead: every office the wave reports as staged-ok must have
    ``<deploy_root>/<slug>/index.html`` present before the command is surfaced.

    Args:
        deploy_root: The wave-shared root the command would deploy.
        slugs_by_office: ``{play_gid: pinned_slug}`` for every staged-ok office of the wave.

    Raises:
        DeployRootRefused: any pinned slug dir absent from the root.
    """
    missing = {
        office: slug
        for office, slug in sorted(slugs_by_office.items())
        if not (deploy_root / slug / "index.html").is_file()
    }
    if missing:
        _refuse(
            "wave_slug_missing",
            f"wave-slug cross-check REFUSED: staged-ok office(s) {missing!r} have no "
            f"<slug>/index.html under deploy root {deploy_root} — the wave command would "
            "deploy WITHOUT those decks (ledger-blind already_produced window); re-run "
            "--phase produce against the accumulating deck-host root",
        )


def assert_deploy_root_ready(deploy_root: Path, *, manifest_path: Path | None = None) -> None:
    """The wave-level pre-surface gate: hygiene, ``_headers`` parity, then no-orphan.

    ALL predicates must pass before the batch surfaces the single wave-level
    ``wrangler pages deploy`` command; any refusal means NO command is surfaced.

    Raises:
        DeployRootRefused: any predicate refused (message names the failing predicate).
    """
    assert_root_hygiene(deploy_root)
    assert_headers_parity(deploy_root)
    assert_manifest_superset(deploy_root, manifest_path=manifest_path)
    logger.info("floodgates_deploy_root_ready", deploy_root=str(deploy_root))


def _refuse(reason: str, message: str) -> NoReturn:
    logger.error("floodgates_deploy_root_refused", reason=reason, detail=message)
    raise DeployRootRefused(message)
