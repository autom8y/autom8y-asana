"""Per-office durable state manifest — the resumability keystone (TDD §3).

The slug lives between freeze and the first post with no durable home; a crash there
orphans it (TDD §3.1). ``StateStore`` is the durable, per-office, atomically-written
manifest keyed by PLAY gid that makes the two-phase flow crash-resumable. One file per
office (``<state_dir>/<play_gid>.json``) so one office's write never touches another's —
the per-office isolation the batch loop depends on.
"""

from __future__ import annotations

from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    OfficeState,
    Phase,
    StateStore,
)

PLAY_GID = "1215823342887129"


def _make_state(**overrides: object) -> OfficeState:
    base: dict[str, object] = dict(
        play_gid=PLAY_GID,
        office_guid_masked="1b271a63…",
        office_guid_sha256="c" * 64,
        clinic="Sand Lake Dental",
        slug="207688021de88a6d7231e1d08ea77a85",
        deck_url="https://decks.cntently.com/207688021de88a6d7231e1d08ea77a85/",
        frozen_sha256="a" * 64,
        phase=Phase.PRODUCED,
        posts={"link": None, "template": None, "card": None},
        updated_at="2026-07-07T00:00:00+00:00",
    )
    base.update(overrides)
    return OfficeState(**base)  # type: ignore[arg-type]


class TestRoundTrip:
    def test_save_then_load_round_trips(self, tmp_path) -> None:
        store = StateStore(tmp_path / "state")
        state = _make_state()
        store.save(state)
        loaded = store.load(PLAY_GID)
        assert loaded is not None
        assert loaded == state
        assert loaded.phase is Phase.PRODUCED

    def test_load_missing_office_returns_none(self, tmp_path) -> None:
        store = StateStore(tmp_path / "state")
        assert store.load("9999") is None

    def test_phase_serializes_as_its_string_value(self, tmp_path) -> None:
        """Phase persists as a plain string enum value (stable, human-readable on disk)."""
        store = StateStore(tmp_path / "state")
        store.save(_make_state(phase=Phase.DONE))
        raw = store.path_for(PLAY_GID).read_text(encoding="utf-8")
        assert '"phase": "done"' in raw


class TestAtomicity:
    def test_save_is_atomic_no_tmp_left_behind(self, tmp_path) -> None:
        """Atomic temp-file + rename: after a save only the final file exists (no .tmp litter)."""
        store = StateStore(tmp_path / "state")
        store.save(_make_state())
        state_dir = tmp_path / "state"
        files = sorted(p.name for p in state_dir.iterdir())
        assert files == [f"{PLAY_GID}.json"]

    def test_second_save_overwrites_in_place(self, tmp_path) -> None:
        store = StateStore(tmp_path / "state")
        store.save(_make_state(phase=Phase.PRODUCED))
        store.save(
            _make_state(phase=Phase.DONE, posts={"link": "S1", "template": "S2", "card": "S3"})
        )
        loaded = store.load(PLAY_GID)
        assert loaded is not None
        assert loaded.phase is Phase.DONE
        assert loaded.posts == {"link": "S1", "template": "S2", "card": "S3"}


class TestPerOfficeIsolation:
    def test_all_offices_lists_each_manifest_once(self, tmp_path) -> None:
        store = StateStore(tmp_path / "state")
        store.save(_make_state(play_gid="A"))
        store.save(_make_state(play_gid="B", phase=Phase.DONE))
        offices = {o.play_gid: o for o in store.all_offices()}
        assert set(offices) == {"A", "B"}
        assert offices["A"].phase is Phase.PRODUCED
        assert offices["B"].phase is Phase.DONE

    def test_one_office_file_is_independent_of_another(self, tmp_path) -> None:
        """Writing office B never mutates office A's file (per-office atomic isolation)."""
        store = StateStore(tmp_path / "state")
        store.save(_make_state(play_gid="A", slug="a" * 32))
        a_before = store.path_for("A").read_bytes()
        store.save(_make_state(play_gid="B", slug="b" * 32))
        assert store.path_for("A").read_bytes() == a_before
