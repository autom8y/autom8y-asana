"""Typed cross-repo envelope for the dynamic enum-option-set sync.

The ONE spec both build halves consume: the producer (autom8y-asana, sprint-1)
constructs ``VocabularySyncRequest`` against it; the consumer (autom8y-data,
sprint-2) parses it and drives an additive-upsert into ``verticals``.

Grounding: model shapes are verbatim from ADR-dyn-enum-contract-shared-contract
§2 (the typed envelope, :101-113). The three compose-up locks live here:

* **Lock-2** — ``field_key: Literal["vertical"]`` + ``extra="forbid"``: the
  discriminator is present from row one, so a 2nd vocabulary is a *data*
  addition (a new ``field_key`` value), not a code change (ADR §2 :82-87).
* **Lock-3** — ``vertical_key = normalize(option.name)``: the cross-service key
  is the portable NAME-key, NEVER ``enum_option.gid`` / ``vertical_id`` (both
  per-side handles that orphan on the other side) (ADR §2 :89-96).

``enabled`` rides the envelope for drift-observability ONLY; it is NOT a stored
column (the ``verticals`` schema is id/key/name only). A disabled-but-referenced
option is a drift WARN, never a DELETE (ADR §2 :109,:116-118).

[PROPOSE — promote to autom8y-core] This module is the interim SINGLE
definition of the contract (autom8y-core is not co-located in this worktree —
installed package 4.6.0 only). Per ADR §6 (G-PROPAGATE), the SOLE propagation
point is an autom8y-core minor bump homing these models; both repos' existing
``autom8y-core>=4.2.0,<5.0.0`` pins absorb it with no pin-range edit. Promotion
is a MOVE (``git mv`` + re-export), never a per-repo duplicate. Precedent:
``VerticalsListResponse`` at autom8y-core ``clients/data_intake.py:473``. The
consumer sprint-2 imports these models from ``autom8y_core`` post-promotion —
the core bump is a cross-repo sequencing dependency (escalated to potnia).

This module is intentionally free of autom8y-asana-internal imports (only stdlib
``typing`` + ``pydantic``) so the promotion stays a mechanical move.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class VocabularyOption(BaseModel):
    """One option in the vocabulary option-SET.

    ``vertical_key`` is the Lock-3 NAME-key (``normalize(option.name)``); it is
    NEVER the Asana ``enum_option.gid`` nor the consumer's ``vertical_id``.
    """

    vertical_key: str
    """Lock-3: ``normalize(option.name)``; the FK-safe cross-service key."""

    name: str
    """Display name — the consumer's UPDATE-name target (unique=True consumer-side)."""

    enabled: bool | None = None
    """Drift-observability ONLY (ADR §2); NOT a stored column."""


class VocabularySyncRequest(BaseModel):
    """POST /api/v1/vocabularies/sync request envelope (the generic plural path).

    ``extra="forbid"`` (NFR-003 / BC-1) makes an unknown field a 422 rather than
    a silently-ignored drift, protecting the Lock-2 discriminator's integrity.
    """

    model_config = ConfigDict(extra="forbid")

    field_key: Literal["vertical"]
    """Lock-2: the discriminator, valued ``"vertical"`` for this instance, from row one."""

    options: list[VocabularyOption]
    """The full option-SET (not the selected value)."""


class RefusedRow(BaseModel):
    """A single per-row refusal in the additive-only sync accounting.

    Emitted by the consumer when a row cannot be applied additively (e.g. a
    name-collision against the ``vertical_name`` unique constraint — FR-007).
    """

    vertical_key: str
    reason: str


class VocabularySyncResponse(BaseModel):
    """POST /api/v1/vocabularies/sync response envelope (additive-only accounting).

    ``extra="forbid"`` is safe here despite the producer's other response
    envelopes using ``extra="ignore"``: the model is homed ONCE in the SDK
    (ADR §6), so a future field addition is a single atomic bump moving BOTH
    sides together — no producer/consumer skew (the exact skew ``extra="ignore"``
    defends against). The push seam is broad-catch non-blocking regardless, so a
    parse mismatch degrades to a logged non-fatal, never a crash.
    """

    model_config = ConfigDict(extra="forbid")

    inserted: int
    updated: int
    refused: list[RefusedRow]
