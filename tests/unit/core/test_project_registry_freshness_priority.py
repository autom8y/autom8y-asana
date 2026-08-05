"""F1a offer-frame priority carve-out teeth.

The ASR offer frame (project 1143843662099250, BusinessOffers) is the 9th GID in the
heaviest-first warm set, so its (project/section) keys land at positions 17-18 of 68 --
one key PAST the 16-key per-link budget -- and are perpetually deferred to a later
continuation. When that continuation strands (a 429-storm hard timeout) the frame goes
stale for hours (the sawtooth). The carve-out front-loads the freshness-contract GID so
its keys are in the FIRST key-budget window every invocation.

TEETH:
  * RED on main: the ASR GID sits at positions 17-18 (past the 16-key budget).
  * GREEN: positions 0-1 (first window, warmed every cycle).
GUARD (named -- 'other frames must not regress'): the reorder is a strict PERMUTATION --
set-equal to the baseline, same 68 keys, no drop -- so no other project's frame is starved
out of the sweep; and an empty priority set is byte-identical to origin/main ordering
(env-only instant revert).
"""

from __future__ import annotations

import pytest

from autom8_asana.core.project_registry import (
    bulk_prematerialization_keys,
    consumer_warm_set_gids,
    freshness_priority_gids,
    prioritize_freshness_gids,
    section_only_prematerialization_keys,
)
from autom8_asana.lambda_handlers.cache_warmer import _DEFAULT_BULK_KEY_BUDGET

_ASR_GID = "1143843662099250"


def _baseline_bulk_keys() -> list[tuple[str, str]]:
    """The origin/main ordering: heaviest-first GIDs x (project, section), no carve-out."""
    return [(gid, arm) for gid in consumer_warm_set_gids() for arm in ("project", "section")]


def test_default_priority_is_the_asr_offer_frame():
    assert freshness_priority_gids() == (_ASR_GID,)


def test_asr_gid_lands_in_first_key_budget_window():
    """GREEN: the ASR GID's keys are in the first key-budget window (positions 0-1)."""
    keys = bulk_prematerialization_keys()
    positions = [i for i, (gid, _arm) in enumerate(keys) if gid == _ASR_GID]
    assert positions == [0, 1]
    assert max(positions) < _DEFAULT_BULK_KEY_BUDGET  # 16


def test_main_ordering_would_strand_asr_gid_past_budget():
    """Documents the RED baseline: on origin/main the ASR GID is PAST the 16-key budget."""
    baseline = _baseline_bulk_keys()
    positions = [i for i, (gid, _arm) in enumerate(baseline) if gid == _ASR_GID]
    assert positions == [16, 17]
    assert min(positions) >= _DEFAULT_BULK_KEY_BUDGET  # past the first window -> deferred


def test_reorder_is_a_permutation_no_frame_dropped():
    """GUARD: set-equal to baseline (no add, no drop) -- no other frame is starved out."""
    reordered = bulk_prematerialization_keys()
    baseline = _baseline_bulk_keys()
    assert len(reordered) == len(baseline) == 68
    assert set(reordered) == set(baseline)


def test_non_priority_gids_keep_heaviest_first_order():
    """The tail (everything after the front-loaded ASR GID) keeps heaviest-first order."""
    reordered_gids = [gid for gid, arm in bulk_prematerialization_keys() if arm == "project"]
    baseline_gids = list(consumer_warm_set_gids())
    assert reordered_gids[0] == _ASR_GID
    assert reordered_gids[1:] == [g for g in baseline_gids if g != _ASR_GID]


def test_section_lane_also_front_loads_the_frame():
    keys = section_only_prematerialization_keys()
    assert keys[0] == (_ASR_GID, "section")
    assert len(keys) == len(consumer_warm_set_gids())
    assert set(keys) == {(g, "section") for g in consumer_warm_set_gids()}


def test_empty_priority_is_byte_identical_to_main(monkeypatch):
    """INERT/REVERT: an explicitly empty priority set restores origin/main ordering exactly."""
    monkeypatch.setenv("ASANA_FRESHNESS_PRIORITY_GIDS", "")
    assert freshness_priority_gids() == ()
    assert bulk_prematerialization_keys() == _baseline_bulk_keys()


def test_env_override_front_loads_in_declaration_order(monkeypatch):
    """A custom priority list front-loads in declaration order, preserving the rest."""
    heavy_first = consumer_warm_set_gids()[0]  # the current heaviest (OOM driver)
    monkeypatch.setenv("ASANA_FRESHNESS_PRIORITY_GIDS", f"{_ASR_GID}, {heavy_first}")
    ordered = prioritize_freshness_gids(consumer_warm_set_gids())
    assert ordered[0] == _ASR_GID
    assert ordered[1] == heavy_first
    assert set(ordered) == set(consumer_warm_set_gids())


def test_unknown_priority_gid_is_ignored(monkeypatch):
    """A priority GID not in the warm set is a no-op (no phantom key injected)."""
    monkeypatch.setenv("ASANA_FRESHNESS_PRIORITY_GIDS", "9999999999999999")
    assert bulk_prematerialization_keys() == _baseline_bulk_keys()
