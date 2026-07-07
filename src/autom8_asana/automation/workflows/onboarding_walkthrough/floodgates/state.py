"""Per-office durable state manifest — the resumability keystone (TDD §3).

The capability slug lives between freeze and the first PLAY comment with **no durable
home** (only the deploy-root dir + process memory); a crash there orphans it. This module
is that durable home: one atomically-written manifest **per office, keyed by PLAY gid**
(``<state_dir>/<play_gid>.json``). Per-office files (not one combined batch file) give the
per-office atomic isolation the batch loop depends on — one office's write can never touch
another's, and one office's corruption can never poison the wave.

Atomicity: each ``save`` writes a sibling temp file then ``os.replace``s it into place, so
a crash mid-write leaves the previous committed manifest intact (never a half-written one).
The manifest records the guid MASK (first-8) as a forensic breadcrumb AND a one-way SHA-256
digest of the full guid — the ★C-1 manifest-integrity guard decides tenant identity on the
full digest (the 8-char mask is 32 bits and collides), while neither field spills the full
guid at rest (§3.1). A manifest lacking the digest (legacy / hand-edited) deserializes with
an empty digest, which no real guid can match — so the guard fails closed.
"""

from __future__ import annotations

import enum
import json
import os
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class Phase(enum.StrEnum):
    """The office's committed phase in the two-phase flow (serialized as its string value).

    ``StrEnum`` so the enum round-trips through JSON as a plain, human-readable string.
    """

    PENDING = "pending"  # enumerated, nothing produced yet
    PRODUCED = "produced"  # Phase-1 committed: frozen + minted + staged (awaiting CF deploy)
    DEPLOY_CONFIRMED = "deploy_confirmed"  # Phase-2: served byte-parity verified
    DONE = "done"  # Phase-2: all three PLAY comments posted


@dataclass
class OfficeState:
    """One office's manifest record (keyed by ``play_gid``)."""

    play_gid: str
    office_guid_masked: str  # first-8 + ellipsis; a forensic log breadcrumb only (§3.1)
    office_guid_sha256: str  # full-strength identity digest; the ★C-1 guard DECIDES on THIS
    clinic: str  # operator-confirmed customer-safe display name (personalization-gated)
    slug: str  # minted ONCE, pinned here (SLUG-1); re-runs REUSE, never re-mint
    deck_url: str  # https://decks.cntently.com/<slug>/
    frozen_sha256: str  # the arm-2 byte-parity oracle recorded at freeze
    phase: Phase
    posts: dict[str, str | None]  # {"link": story_gid?, "template": story_gid?, "card": story_gid?}
    updated_at: str  # iso8601

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict (``phase`` as its string value)."""
        data = asdict(self)
        data["phase"] = self.phase.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OfficeState:
        """Deserialize from a manifest dict (``phase`` string -> :class:`Phase`)."""
        return cls(
            play_gid=str(data["play_gid"]),
            office_guid_masked=str(data["office_guid_masked"]),
            # Absent on a legacy / hand-edited manifest -> "" (no real digest matches), so the
            # ★C-1 guard fails closed rather than deserialize-crashing.
            office_guid_sha256=str(data.get("office_guid_sha256", "")),
            clinic=str(data["clinic"]),
            slug=str(data["slug"]),
            deck_url=str(data["deck_url"]),
            frozen_sha256=str(data["frozen_sha256"]),
            phase=Phase(data["phase"]),
            posts=dict(data["posts"]),
            updated_at=str(data["updated_at"]),
        )


class StateStore:
    """A directory of per-office manifests, keyed by PLAY gid (atomic per-office writes)."""

    def __init__(self, state_dir: Path) -> None:
        self._dir = Path(state_dir)

    @property
    def state_dir(self) -> Path:
        return self._dir

    def path_for(self, play_gid: str) -> Path:
        """The manifest path for one office (``<state_dir>/<play_gid>.json``)."""
        return self._dir / f"{play_gid}.json"

    def load(self, play_gid: str) -> OfficeState | None:
        """Return the office's committed manifest, or ``None`` if it has none."""
        path = self.path_for(play_gid)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        return OfficeState.from_dict(data)

    def save(self, state: OfficeState) -> None:
        """Atomically write one office's manifest (temp file + ``os.replace``).

        Crash-safe: the office's stable path either does not exist or holds a fully-written
        manifest — never a half-written one. Per-office: this touches only THIS office's file.
        """
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), indent=2, sort_keys=False)
        tmp = self._dir / f".{state.play_gid}.{secrets.token_hex(4)}.tmp"
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self.path_for(state.play_gid))

    def all_offices(self) -> list[OfficeState]:
        """Load every committed office manifest (skips the transient ``.tmp`` siblings)."""
        if not self._dir.is_dir():
            return []
        offices: list[OfficeState] = []
        for path in sorted(self._dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            offices.append(OfficeState.from_dict(data))
        return offices
