"""Two-sided tests for the fail-closed wave-shared deploy-root guard (TDD §8).

Three predicates, each proven from BOTH sides:

* **Root-hygiene allowlist**: ONLY ``_headers`` + ``^[0-9a-f]{32}$`` dirs (each holding
  ``index.html``). Stray file / non-hex / 31-hex / uppercase / the dead base32 legacy
  shape (CH-01) all REFUSE — anything else in the root would be PUBLISHED by wrangler.
* **``_headers`` cross-repo byte-parity**: drift from ``HEADERS_FILE_CONTENT`` is a
  guard-header regression on ALL decks — refused.
* **Manifest-superset no-orphan predicate**: every non-revoked ledger slug must be staged
  or the deploy would 404 a LIVE client deck; a missing/unreadable ledger REFUSES
  (absence of the ledger is not permission).

Plus ONE read-only live-leg test against the real deck-host workspace (skips gracefully
when the checkout is absent). The guard never mutates — all fixtures are tmp_path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.deploy_root_guard import (
    DeployRootRefused,
    assert_deploy_root_ready,
    assert_headers_parity,
    assert_manifest_superset,
    assert_root_hygiene,
    assert_wave_slugs_staged,
    default_manifest_path,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import (
    HEADERS_FILE_CONTENT,
)

SLUG_A = "1f2e3d4c5b6a798801234567890abcde"
SLUG_B = "fedcba9876543210aabbccddeeff0011"
#: The SUPERSEDED-DEAD legacy base32 slug shape (CH-01): refusing it is CORRECT.
BASE32_SLUG = "od67utt5a5gdbidn6b5dszjjoi"


def _make_root(tmp_path: Path, slugs: list[str]) -> Path:
    """A guard-GREEN deploy root: ``_headers`` + slug dirs each holding index.html."""
    root = tmp_path / "public"
    root.mkdir(parents=True, exist_ok=True)
    (root / "_headers").write_text(HEADERS_FILE_CONTENT, encoding="utf-8")
    for slug in slugs:
        (root / slug).mkdir()
        (root / slug / "index.html").write_bytes(b"<html>deck %s</html>" % slug.encode())
    return root


def _write_manifest(root: Path, decks: dict[str, dict[str, str]]) -> Path:
    """Write a committed-ledger-shaped manifest at the DEFAULT location (<root>/../config)."""
    config = root.parent / "config"
    config.mkdir(parents=True, exist_ok=True)
    path = config / "deck-manifest.json"
    path.write_text(json.dumps({"version": 1, "decks": decks}), encoding="utf-8")
    return path


# ============================================================ root-hygiene allowlist


class TestRootHygieneAllowlist:
    def test_green_headers_plus_hex_slug_dirs_pass(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A, SLUG_B])
        assert_root_hygiene(root)  # no raise

    def test_missing_root_refused(self, tmp_path: Path) -> None:
        with pytest.raises(DeployRootRefused, match="missing"):
            assert_root_hygiene(tmp_path / "nowhere")

    @pytest.mark.parametrize(
        "stray_name",
        [
            "README.md",  # stray file: would be PUBLISHED at a guessable path
            "notes.txt",
            ".DS_Store",
            "index.html",  # a root-level index would serve at the domain apex
        ],
    )
    def test_stray_file_refused(self, tmp_path: Path, stray_name: str) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        (root / stray_name).write_text("stray", encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="root-hygiene REFUSED"):
            assert_root_hygiene(root)

    @pytest.mark.parametrize(
        "bad_dir",
        [
            "assets",  # non-hex dir
            BASE32_SLUG,  # the dead base32 legacy shape — refusing it is CORRECT (CH-01)
            "1f2e3d4c5b6a798801234567890abcd",  # 31 hex (one short)
            "1f2e3d4c5b6a798801234567890abcdef",  # 33 hex (one long)
            "ABCDEF0123456789ABCDEF0123456789",  # uppercase (case-unstable; distinct from
            # SLUG_A so a case-insensitive filesystem cannot collapse the two dirs)
            "b167331c-536f-4996-9b2d-2f696f35f556",  # uuid dashes (identity-shaped)
        ],
    )
    def test_non_capability_dir_refused(self, tmp_path: Path, bad_dir: str) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        (root / bad_dir).mkdir()
        (root / bad_dir / "index.html").write_text("x", encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="root-hygiene REFUSED"):
            assert_root_hygiene(root)

    def test_slug_dir_without_index_refused(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        (root / SLUG_B).mkdir()  # empty slug dir: would deploy a 404 at the capability URL
        with pytest.raises(DeployRootRefused, match="lack index.html"):
            assert_root_hygiene(root)

    def test_headers_as_directory_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "public"
        (root / "_headers").mkdir(parents=True)  # _headers must be a FILE
        with pytest.raises(DeployRootRefused, match="root-hygiene REFUSED"):
            assert_root_hygiene(root)

    # ------------------------------------------------ recursive-exact slug-dir contents
    # `wrangler pages deploy` publishes slug-dir contents WHOLESALE at <slug>/<name>, so
    # a nested stray is the same hazard class as a root-level stray (unreviewed,
    # parity-unverified bytes at a live capability path — the stale-deck-variant /
    # silent-wrong-outcome class). The allowlist must be recursive-exact: EXACTLY
    # index.html per slug dir, nothing else.

    @pytest.mark.parametrize(
        "nested_name",
        [
            "draft-internal.html",  # a stale/unreviewed deck variant, served live
            "index.html.bak",  # editor backup — the PREVIOUS deck bytes, served live
            ".DS_Store",  # Finder metadata (root-level .DS_Store already refused;
            # nested must not be the inconsistent-posture hole)
        ],
    )
    def test_nested_stray_file_inside_slug_dir_refused(
        self, tmp_path: Path, nested_name: str
    ) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        (root / SLUG_A / nested_name).write_text("stale variant", encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="EXACTLY index.html"):
            assert_root_hygiene(root)

    def test_nested_subdir_inside_slug_dir_refused(self, tmp_path: Path) -> None:
        """A nested subdir (e.g. ``assets/``) gets published wholesale — refused."""
        root = _make_root(tmp_path, [SLUG_A])
        (root / SLUG_A / "assets").mkdir()
        (root / SLUG_A / "assets" / "app.js").write_text("evil()", encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="EXACTLY index.html"):
            assert_root_hygiene(root)

    def test_slug_dirs_holding_exactly_index_html_pass(self, tmp_path: Path) -> None:
        """Positive control for the recursive-exact check: the staged shape
        (``stage_deck_bundle`` writes exactly ``<slug>/index.html``) stays GREEN."""
        root = _make_root(tmp_path, [SLUG_A, SLUG_B])
        assert_root_hygiene(root)  # no raise

    def test_symlinked_slug_dir_refused(self, tmp_path: Path) -> None:
        """A 32-hex-NAMED symlink to an external directory passes ``is_dir()`` + the regex
        but would publish its TARGET tree — refused as a stray (never followed)."""
        root = _make_root(tmp_path, [SLUG_A])
        target = tmp_path / "external-tree"
        target.mkdir()
        (target / "index.html").write_text("outside bytes", encoding="utf-8")
        (root / SLUG_B).symlink_to(target, target_is_directory=True)
        with pytest.raises(DeployRootRefused, match="root-hygiene REFUSED"):
            assert_root_hygiene(root)

    def test_symlinked_index_html_leaf_refused(self, tmp_path: Path) -> None:
        """A real slug DIR whose index.html is a SYMLINK to an external file passes
        ``is_file()`` (path-following at the leaf) but would publish the TARGET's bytes
        at the capability URL — refused (QA residual closed 2026-07-09)."""
        root = _make_root(tmp_path, [SLUG_A])
        outside = tmp_path / "outside.html"
        outside.write_text("outside bytes", encoding="utf-8")
        (root / SLUG_B).mkdir()
        (root / SLUG_B / "index.html").symlink_to(outside)
        with pytest.raises(DeployRootRefused, match="root-hygiene REFUSED"):
            assert_root_hygiene(root)


# ============================================================ _headers byte-parity


class TestHeadersParity:
    def test_green_byte_identical_passes(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        assert_headers_parity(root)  # no raise

    def test_missing_headers_refused(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        (root / "_headers").unlink()
        with pytest.raises(DeployRootRefused, match="_headers missing"):
            assert_headers_parity(root)

    def test_drifted_headers_refused(self, tmp_path: Path) -> None:
        """A single dropped guard header (or ANY byte drift) refuses — drift here would
        regress noindex/no-store/no-referrer/nosniff on EVERY deck at once."""
        root = _make_root(tmp_path, [SLUG_A])
        drifted = HEADERS_FILE_CONTENT.replace("  Cache-Control: no-store\n", "")
        (root / "_headers").write_text(drifted, encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="NOT byte-identical"):
            assert_headers_parity(root)

    def test_trailing_byte_drift_refused(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        (root / "_headers").write_text(HEADERS_FILE_CONTENT + "\n", encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="NOT byte-identical"):
            assert_headers_parity(root)


# ============================================================ no-orphan predicate


class TestManifestSupersetNoOrphan:
    def test_green_all_active_slugs_staged_passes(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A, SLUG_B])
        _write_manifest(
            root,
            {
                SLUG_A: {"status": "active"},
                SLUG_B: {"status": "active"},
            },
        )
        assert_manifest_superset(root)  # default <root>/../config path derivation

    def test_active_slug_missing_from_root_refused(self, tmp_path: Path) -> None:
        """The killer failure: a partial root would 404 a LIVE client deck — refused."""
        root = _make_root(tmp_path, [SLUG_A])  # SLUG_B active in ledger but NOT staged
        _write_manifest(
            root,
            {
                SLUG_A: {"status": "active"},
                SLUG_B: {"status": "active"},
            },
        )
        with pytest.raises(DeployRootRefused, match="no-orphan REFUSED") as excinfo:
            assert_manifest_superset(root)
        assert SLUG_B in str(excinfo.value)

    def test_revoked_slug_missing_is_exempt(self, tmp_path: Path) -> None:
        """A revoked ledger entry (e.g. the superseded od67 base32 slug) need not be
        staged — revocation IS the exemption; its absence never blocks the wave."""
        root = _make_root(tmp_path, [SLUG_A])
        _write_manifest(
            root,
            {
                SLUG_A: {"status": "active"},
                BASE32_SLUG: {"status": "revoked"},
            },
        )
        assert_manifest_superset(root)  # no raise

    def test_absent_manifest_refused_fail_closed(self, tmp_path: Path) -> None:
        """Absence of the ledger is NOT permission — refuse before surfacing anything."""
        root = _make_root(tmp_path, [SLUG_A])  # no config/deck-manifest.json written
        with pytest.raises(DeployRootRefused, match="missing/unreadable"):
            assert_manifest_superset(root)

    def test_unreadable_manifest_refused_fail_closed(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        path = _write_manifest(root, {})
        path.write_text("{ not valid json", encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="missing/unreadable"):
            assert_manifest_superset(root)

    def test_manifest_without_decks_object_refused(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        path = _write_manifest(root, {})
        path.write_text(json.dumps({"version": 1}), encoding="utf-8")
        with pytest.raises(DeployRootRefused, match="no 'decks' object"):
            assert_manifest_superset(root)

    def test_unknown_status_treated_as_live_fail_closed(self, tmp_path: Path) -> None:
        """Only an explicit ``revoked`` exempts an entry: an unrecognized status must be
        staged (not-explicitly-revoked could be live; a 404 on it is the harm)."""
        root = _make_root(tmp_path, [SLUG_A])
        _write_manifest(root, {SLUG_B: {"status": "paused"}, SLUG_A: {"status": "active"}})
        with pytest.raises(DeployRootRefused, match="no-orphan REFUSED"):
            assert_manifest_superset(root)

    def test_explicit_manifest_path_overrides_default(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        elsewhere = tmp_path / "elsewhere" / "ledger.json"
        elsewhere.parent.mkdir(parents=True)
        elsewhere.write_text(
            json.dumps({"decks": {SLUG_A: {"status": "active"}}}), encoding="utf-8"
        )
        assert_manifest_superset(root, manifest_path=elsewhere)  # no raise

    def test_default_manifest_path_shape(self, tmp_path: Path) -> None:
        root = tmp_path / "deck-host" / "public"
        assert default_manifest_path(root) == root / ".." / "config" / "deck-manifest.json"


# ============================================================ wave-slug cross-check


class TestWaveSlugsStaged:
    """The ledger-blind ``already_produced`` window: an office at PRODUCED re-surfaces the
    wave command WITHOUT re-staging, and a slug not yet in the committed ledger is
    invisible to the no-orphan predicate — this cross-check refuses the surface instead."""

    def test_all_pinned_slugs_present_passes(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A, SLUG_B])
        assert_wave_slugs_staged(root, {"office-a": SLUG_A, "office-b": SLUG_B})  # no raise

    def test_missing_pinned_slug_refused_naming_office_and_slug(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])  # office-b's pinned slug is NOT staged
        with pytest.raises(DeployRootRefused, match="wave-slug cross-check REFUSED") as excinfo:
            assert_wave_slugs_staged(root, {"office-a": SLUG_A, "office-b": SLUG_B})
        assert "office-b" in str(excinfo.value)
        assert SLUG_B in str(excinfo.value)

    def test_slug_dir_present_but_empty_refused(self, tmp_path: Path) -> None:
        """The dir alone is not the deck — ``<slug>/index.html`` is what deploys."""
        root = _make_root(tmp_path, [SLUG_A])
        (root / SLUG_B).mkdir()
        with pytest.raises(DeployRootRefused, match="wave-slug cross-check REFUSED"):
            assert_wave_slugs_staged(root, {"office-b": SLUG_B})

    def test_empty_wave_mapping_passes(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        assert_wave_slugs_staged(root, {})  # nothing pinned -> nothing to cross-check


# ============================================================ composite gate


class TestDeployRootReadyComposite:
    def test_green_full_gate_passes(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A, SLUG_B])
        _write_manifest(root, {SLUG_A: {"status": "active"}, SLUG_B: {"status": "active"}})
        assert_deploy_root_ready(root)  # no raise

    def test_any_leg_failing_refuses(self, tmp_path: Path) -> None:
        root = _make_root(tmp_path, [SLUG_A])
        _write_manifest(root, {SLUG_A: {"status": "active"}})
        (root / "stray.txt").write_text("x", encoding="utf-8")
        with pytest.raises(DeployRootRefused):
            assert_deploy_root_ready(root)


# ============================================================ live leg (read-only)

_DECK_HOST_WORKSPACE = Path(
    os.environ.get("DECK_HOST_WORKSPACE", str(Path.home() / "Code" / "a8t" / "deck-host"))
)


@pytest.mark.skipif(
    not (_DECK_HOST_WORKSPACE / "public").is_dir()
    or not (_DECK_HOST_WORKSPACE / "config" / "deck-manifest.json").is_file(),
    reason="real deck-host workspace not present (live-leg fixture; read-only)",
)
class TestLiveDeckHostWorkspace:
    """READ-ONLY live leg: the real backfilled deck-host workspace passes the full gate.

    This is the fixture the accumulating deploy will actually run against: the backfilled
    ``public/`` (live 32-hex slug set + one ``_headers``) and the committed ledger with the
    superseded od67 base32 entry ``revoked``. The guard must pass it AS-IS — and this test
    NEVER writes into the workspace.
    """

    def test_real_workspace_passes_full_gate(self) -> None:
        assert_deploy_root_ready(_DECK_HOST_WORKSPACE / "public")

    def test_real_ledger_revoked_base32_is_exempt_not_staged(self) -> None:
        manifest = json.loads(
            (_DECK_HOST_WORKSPACE / "config" / "deck-manifest.json").read_text(encoding="utf-8")
        )
        od67 = manifest["decks"].get(BASE32_SLUG)
        if od67 is None:  # ledger may eventually drop the dead entry — nothing to assert
            pytest.skip("od67 entry no longer in the ledger")
        assert od67["status"] == "revoked"
        assert not (_DECK_HOST_WORKSPACE / "public" / BASE32_SLUG).exists()
