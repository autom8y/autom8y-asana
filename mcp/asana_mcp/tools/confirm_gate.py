"""RB-1 confirm-before-firing gate (operator ruling R5, dispatched under R21).

R5 (RULINGS-operator-interview-telos-ratification-2026-07-20.md:48-55, verbatim
posture): actions known to set off business automations "pause for a human yes".
Today the trigger-capable write is ``add_tag`` — applying a routing label is the
canonical automation trigger. R7 requires any automation-triggering verb to
carry this gate from day one.

V1 TRIGGER POSTURE — ALL tags are treated trigger-capable. The
trigger-classification list is R5's named *maintained boundary*; its ownership
is DELIBERATELY UNASSIGNED at ruling time (RULINGS "deliberately left
undecided" item 3), so v1 refuses to guess which tags are safe: every add_tag
pauses. A narrowing seam (an ``ASANA_MCP_TRIGGER_TAG_ALLOWLIST``-style env list
naming the tags that are actually trigger-capable) can come LATER, once the
list's owner exists — it is intentionally NOT implemented here, so the
boundary cannot silently drift ahead of its owner.

MECHANIC — two-phase confirmation, transport-agnostic and fastmcp-free (the
island's pure-handler discipline):

  1. A call WITHOUT ``confirmation_token`` performs ZERO backend calls. It
     returns a ``confirmation_required`` envelope carrying a single-use,
     TTL-bounded token bound (by fingerprint) to the EXACT write intent, plus
     the instruction to present the pending write to the HUMAN operator.
  2. A call WITH the token and byte-identical intent executes the (unchanged)
     composite chain. A token that is unknown, expired, or bound to a
     DIFFERENT intent refuses again — still zero writes — and burns the token.

The store is in-process (the stdio mount is a per-session, single-process
server); a restart clears pending confirmations, which fails SAFE (the write
simply asks again).

THROWAWAY / REFERENCE-POSTURE PROTOTYPE (charter §5.3): NOT production code.
At tech-transfer reimplement against production contracts (a remote surface
would carry this same gate via MCP elicitation — spike §6 Stage B).
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from collections.abc import Callable
from typing import Any

# Default lifetime of a pending confirmation. Long enough for a human to read
# and answer; short enough that a stale yes cannot fire much later.
DEFAULT_CONFIRMATION_TTL_S: float = 600.0

# Bound the pending store (a misbehaving agent hammering phase-1 must not grow
# memory unboundedly); oldest pending intents are evicted first.
DEFAULT_MAX_PENDING: int = 32

# Redemption outcomes (single-use: any redemption attempt on a known token
# consumes it, whatever the outcome).
REDEEM_OK = "ok"
REDEEM_UNKNOWN = "unknown_token"
REDEEM_EXPIRED = "expired"
REDEEM_MISMATCH = "intent_mismatch"

TRIGGER_POSTURE_V1 = (
    "v1 trigger posture: ALL tags are treated trigger-capable (R5). The "
    "trigger-classification list is a maintained boundary whose owner is not "
    "yet assigned, so no tag is presumed safe; every add_tag pauses for a "
    "human yes."
)

HUMAN_INSTRUCTION = (
    "PRESENT this pending write to the HUMAN operator and wait for their "
    "explicit yes. Only after the human approves, call this tool again with "
    "the SAME arguments plus this confirmation_token. Re-calling without a "
    "human approval violates the R5 confirmation rule; the token is "
    "single-use, expires, and is bound to exactly this write."
)


def intent_fingerprint(
    *,
    task_gid: str,
    tag_gid: str | None,
    tag_name: str | None,
    save_fields: dict[str, Any] | None,
) -> str:
    """Canonical fingerprint of the write intent a confirmation binds to.

    A confirmed yes applies to EXACTLY this (task, tag selector, save fields)
    tuple; any drift between phase 1 and phase 2 is an ``intent_mismatch``.
    """
    canonical = json.dumps(
        {
            "task_gid": task_gid,
            "tag_gid": tag_gid,
            "tag_name": tag_name,
            "save_fields": save_fields or {},
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ConfirmationGate:
    """Single-use, TTL-bounded, intent-bound pending-confirmation store.

    ``clock`` is injectable (monotonic seconds) so tests force expiry
    deterministically — the same seam idiom as ``TagNameCache``.
    """

    def __init__(
        self,
        ttl_s: float = DEFAULT_CONFIRMATION_TTL_S,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_pending: int = DEFAULT_MAX_PENDING,
    ) -> None:
        self._ttl_s = ttl_s
        self._clock = clock
        self._max_pending = max_pending
        # token -> (expires_at, fingerprint); insertion-ordered for eviction.
        self._pending: dict[str, tuple[float, str]] = {}

    @property
    def ttl_s(self) -> float:
        return self._ttl_s

    def issue(self, fingerprint: str) -> str:
        """Mint a single-use token bound to ``fingerprint``."""
        self._prune()
        while len(self._pending) >= self._max_pending:
            oldest = next(iter(self._pending))
            del self._pending[oldest]
        token = secrets.token_urlsafe(16)
        self._pending[token] = (self._clock() + self._ttl_s, fingerprint)
        return token

    def redeem(self, token: str, fingerprint: str) -> str:
        """Attempt redemption. Consumes the token on ANY known-token attempt.

        Returns one of REDEEM_OK / REDEEM_UNKNOWN / REDEEM_EXPIRED /
        REDEEM_MISMATCH. Burning on mismatch is deliberate: a yes given for
        one intent must never remain replayable while arguments are probed.
        """
        entry = self._pending.pop(token, None)
        if entry is None:
            return REDEEM_UNKNOWN
        expires_at, bound_fingerprint = entry
        if self._clock() >= expires_at:
            return REDEEM_EXPIRED
        if bound_fingerprint != fingerprint:
            return REDEEM_MISMATCH
        return REDEEM_OK

    def pending_count(self) -> int:
        self._prune()
        return len(self._pending)

    def _prune(self) -> None:
        now = self._clock()
        for token in [t for t, (exp, _) in self._pending.items() if now >= exp]:
            del self._pending[token]


def build_confirmation_envelope(
    *,
    reason: str,
    token: str,
    ttl_s: float,
    task_gid: str,
    tag_gid: str | None,
    tag_name: str | None,
    save_fields: dict[str, Any] | None,
) -> dict[str, Any]:
    """The zero-writes ``confirmation_required`` envelope (phase 1 / re-ask).

    Top-level keys mirror the assembled write result (status / resolution /
    write / confirmation, all null-write here) so consumers see one stable
    shape; the pending request rides under ``confirmation_request``.
    """
    return {
        "status": "confirmation_required",
        "resolution": None,
        "write": None,
        "confirmation": None,
        "confirmation_request": {
            "reason": reason,
            "confirmation_token": token,
            "expires_in_s": ttl_s,
            "single_use": True,
            "what_will_fire": [
                f"add_tag (POST /api/v1/tasks/{task_gid}/tags) — the trigger-capable step",
                f"push / PUT-save (PUT /api/v1/tasks/{task_gid})",
                f"mark_complete (PUT /api/v1/tasks/{task_gid} completed=true)",
            ],
            "task_gid": task_gid,
            "tag_selector": {"tag_gid": tag_gid, "tag_name": tag_name},
            "save_fields": dict(save_fields or {}),
            "trigger_posture": TRIGGER_POSTURE_V1,
            "consumed_trigger_hazard": (
                "Applying a play/automation tag can FIRE a live business "
                "automation; a consumed trigger re-applied RE-FIRES it."
            ),
            "instruction": HUMAN_INSTRUCTION,
            "note": (
                "No backend call was made. Tag-name resolution (if tag_name "
                "was given) runs AFTER confirmation, with its own honest "
                "refusals (ambiguous / not-found)."
            ),
        },
    }
