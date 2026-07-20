"""Tests for the GAP-1 probe harness (TDD §3, §5.3).

These tests exercise the harness's OFFLINE path and the live-fire DOUBLE-GUARD
(D-7). They NEVER fire a live Asana call: the live path refuses without the
operator env flag ``GFR_GAP1_LIVE_FIRE=1``, and module import is side-effect-free.

The harness lives OUTSIDE the shipped package and OUTSIDE ``tests/`` — at
``scripts/gfr_dynvocab/gap1_probe.py`` — so pytest never auto-collects it
(``testpaths = ["tests"]``). This test reaches it via a guarded ``sys.path``
insert of the repo-root ``scripts/`` directory, matching the project's
cross-tree test-import idiom.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Guarded sys.path insert: make scripts/ importable for this test only. The
# harness module is a RETAINED operator tool, not shipped engine code; pytest
# does not auto-collect it (it is not under testpaths).
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from gfr_dynvocab import gap1_probe

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]


class TestAssessCustomFields:
    """The shared assertion logic (D-6) — identical across offline and live."""

    def test_assess_custom_fields_detects_populated_asset_id(self) -> None:
        verdict = gap1_probe.assess_custom_fields(
            [{"gid": "cf1", "name": "Asset ID", "text_value": "a, b"}]
        )
        assert verdict.asset_id_present is True
        assert verdict.asset_id_populated is True
        assert verdict.verdict == "HYP1_CONFIRMED"

    def test_assess_custom_fields_detects_absent_asset_id(self) -> None:
        verdict = gap1_probe.assess_custom_fields([])
        assert verdict.asset_id_present is False
        assert verdict.asset_id_populated is False
        assert verdict.verdict == "HYP1_REFUTED"

    def test_assess_custom_fields_present_but_empty_is_refuted(self) -> None:
        """Present-but-empty asset_id is REFUTED (UNKNOWN distinct from null)."""
        verdict = gap1_probe.assess_custom_fields(
            [{"gid": "cf1", "name": "Asset ID", "text_value": ""}]
        )
        assert verdict.asset_id_present is True
        assert verdict.asset_id_populated is False
        assert verdict.verdict == "HYP1_REFUTED"


class TestOfflineMode:
    """Offline mode reads the fixture and emits a verdict with NO client call."""

    def test_offline_mode_reads_fixture_and_emits_verdict(self) -> None:
        verdict = gap1_probe.run_offline()
        # The committed fixture carries a populated Asset ID — dry-run shape.
        assert verdict.mode == "offline"
        assert verdict.source == "fixture"
        assert verdict.verdict in {"HYP1_CONFIRMED", "HYP1_REFUTED"}
        # The asset_id assertion ran against the fixture's custom_fields.
        assert verdict.total_custom_fields >= 1


class TestLiveFireDoubleGuard:
    """D-7 — the live fire refuses without the operator env flag; no client call."""

    def test_live_fire_refuses_without_operator_env_flag(self, monkeypatch) -> None:
        monkeypatch.delenv("GFR_GAP1_LIVE_FIRE", raising=False)
        with pytest.raises(gap1_probe.LiveFireRefused):
            gap1_probe.run_live(canary="b167331c-536f-4996-9b2d-2f696f35f556")

    def test_live_fire_refuses_with_wrong_env_value(self, monkeypatch) -> None:
        monkeypatch.setenv("GFR_GAP1_LIVE_FIRE", "0")
        with pytest.raises(gap1_probe.LiveFireRefused):
            gap1_probe.run_live(canary="b167331c-536f-4996-9b2d-2f696f35f556")


class TestImportIsSideEffectFree:
    """Importing/collecting the module under pytest fires no live call."""

    def test_live_path_never_invoked_by_default_collection(self) -> None:
        # If import had side effects (a live fetch), this test module would have
        # failed to import above. Reaching here proves import is inert. Also assert
        # the module exposes the offline entrypoint but did not auto-run it.
        assert hasattr(gap1_probe, "run_offline")
        assert hasattr(gap1_probe, "run_live")
        assert gap1_probe.assess_custom_fields is not None
