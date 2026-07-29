"""Substrate-v2 Seam 5 — OBSERVABILITY (infra). RC-F.

FROZEN v1.0-frozen-2026-07-29 per TDD-substrate-v2 §4 Seam 5. Protocol signature
ONLY; the scheduled evaluator body is owned by S5.

``EvaluationRun`` is a referenced-but-undrawn return type landed as an
owner-filled placeholder. The terraform alarm-provisioning limb is the EXISTING
Door #4 — out of this seam's CODE scope ([H23]).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime


class EvaluationRun:
    """Result of one scheduled provability sweep. Seam 5, FROZEN v1.0.

    Referenced but not drawn in §4 — SEAM-0 lands the NAME so the frozen
    ``ProvabilityEvaluator`` signature resolves under mypy; the field surface
    (heartbeat run_count, evaluated_count, completeness) is owned by S5. No
    fields are invented here.
    """


class ProvabilityEvaluator(Protocol):
    """Query-independent scheduled provability evaluator (RC-F). Seam 5, FROZEN v1.0.

    Consumes the SAME ``is_provable`` + ``Provability`` (Seam 1) that Seam 4
    serving calls ([H19]) — the mechanical basis of "cannot read green while
    serving refuses."
    """

    async def evaluate_all(self, now: datetime) -> EvaluationRun:
        """expected-set = registry-warm-targets ∪ store-enumeration(dataframes-v2/) (C7 two-sided).

        per-aid: read_current + is_provable → emit provable=1/0; ArtifactMissing → provable=0 (never silence).
        run-level: emit heartbeat(run_count) AND evaluated_count; evaluated_count < len(expected) FIRES; either-set-only member FIRES.
        """
        ...
