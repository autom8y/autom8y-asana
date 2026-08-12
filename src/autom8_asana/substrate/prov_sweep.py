"""Substrate-v2 — PROV-2 IN-PROCESS SWEEP DRIVER (WU-3 unit 3e; G2 option-a).

The RULING's G2 chose option (a): drive the ``ScheduledProvabilityEvaluator`` (Seam 5,
RC-F) IN-PROCESS from the window loop THIS wave, and DEFER the terraform EventBridge
schedule (option-b) to a post-window packet. This module is that driver: it constructs
the evaluator + the ``CloudWatchProvabilityEmitter`` and runs one sweep, so the PROV-2
dead-man (``EvaluatorHeartbeat``) — and the PROV-1/3/4/5/6 signals — emit on a DENSE,
query-independent cadence while the window is open. PROV-2 ALARMED-as-predicted since
2026-07-30 clears on the FIRST such sweep (C10 quiet-side RC-F-2 evidence).

The ONLY outbound this unit performs is CloudWatch ``put_metric_data`` (via the injectable
``cw_client``); in build/test it is a recording stub — never a live call. The load-bearing
identity contract (the iteration-1 NO-GO at QA-s6-observe-pr282 :164 was a DEAD
``environment`` dimension) is honored HERE: the emitted ``environment`` dimension VALUE is
wired from the SAME value the terraform PROV-* alarms filter on
(``dimensions = { environment = var.environment }``), whose default is ``production`` —
identical to ``observe.DEFAULT_ENVIRONMENT``. A drift on either side un-wires every alarm;
``test_prov_sweep`` string-diffs the .tf var default against the driver's default.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import polars as pl

from autom8_asana.substrate.freshness import _VALUE_COLUMNS, canonical_digest
from autom8_asana.substrate.freshness import is_provable as _default_is_provable
from autom8_asana.substrate.observe import (
    DEFAULT_ENVIRONMENT,
    CloudWatchProvabilityEmitter,
    ScheduledProvabilityEvaluator,
)

if TYPE_CHECKING:
    from typing import Any

    from autom8_asana.substrate.observe import (
        DigestOfFrame,
        EvaluationRun,
        ExpectedSetSource,
        IsProvable,
    )
    from autom8_asana.substrate.store import ArtifactStore

__all__ = [
    "PROV_ENVIRONMENT",
    "build_prov_sweep_evaluator",
    "digest_of_canonical_frame_bytes",
    "run_prov_sweep",
]

# The deployment-scope dimension VALUE the driver stamps on every emitted metric. It MUST
# equal the terraform ``var.environment`` (both default ``production``) or the PROV-* alarms
# bind to a series that never receives a datapoint — the DMS-24h-on-a-dead-metric class the
# iteration-1 NO-GO was. Pinned to ``observe.DEFAULT_ENVIRONMENT`` so the emitter and the
# alarms share ONE source of truth.
PROV_ENVIRONMENT: str = DEFAULT_ENVIRONMENT


def digest_of_canonical_frame_bytes(raw: bytes) -> str:
    """[H19] re-derive the SERVED digest from stored bytes (the ``canonical_frame_bytes`` form).

    Deserializes the rebuild's default ``\\x1e``-joined JSON-row encoding and applies the
    SAME Seam-1 ``canonical_digest`` serving uses — so the sweep catches CORRUPT exactly
    as the serve gate does (a bare ``proof.content_digest`` echo would make CORRUPT
    undetectable). Injectable, so a non-default serializer swaps this out.

    Only the digest-pinned value columns are reconstructed: ``canonical_digest`` consumes
    nothing else, and a full-frame bare-inference ``pl.DataFrame(rows)`` dies on any
    sparse late-typed structural column (a >100-null prefix infers Null dtype, then the
    first real value raises ComputeError — the #313 construction class, observed live on
    ``trackstat_id``; DEFECT-prov-digest-bare-inference-2026-08-12). Full-scan inference
    over the value columns alone is safe: columns serialized from a typed frame are
    type-homogeneous, and the digest's type-erasure pin (freshness F4) makes numeric
    dtype detail irrelevant to the derived digest.
    """
    text = raw.decode("utf-8")
    rows = [json.loads(chunk) for chunk in text.split("\x1e")] if text else []
    if not rows:
        # F1 (MissingValueColumnsError) refuses the empty set loudly — an [H20]
        # indeterminate skip at the evaluator, never a silent green.
        return canonical_digest(pl.DataFrame())
    missing = sorted({column for column in _VALUE_COLUMNS for row in rows if column not in row})
    if missing:
        raise ValueError(
            f"stored rows are missing pinned value column(s) {missing} — refusing to "
            f"re-derive a digest for a partial/foreign artifact"
        )
    value_rows = [{column: row[column] for column in _VALUE_COLUMNS} for row in rows]
    return canonical_digest(pl.DataFrame(value_rows, infer_schema_length=None))


def build_prov_sweep_evaluator(
    *,
    store: ArtifactStore,
    expected_set: ExpectedSetSource,
    environment: str = PROV_ENVIRONMENT,
    cw_client: Any = None,
    is_provable: IsProvable | None = None,
    digest_of_frame: DigestOfFrame | None = None,
) -> ScheduledProvabilityEvaluator:
    """Wire the RC-F ``ScheduledProvabilityEvaluator`` -> ``CloudWatchProvabilityEmitter``.

    ``is_provable`` defaults to the SAME Seam-1 predicate serving uses ([H19]);
    ``digest_of_frame`` defaults to the canonical-frame-bytes re-derivation. ``cw_client`` is
    injectable (a recording stub in tests); production passes ``None`` and boto3 is
    constructed lazily on first emit. ``environment`` MUST match the terraform alarm filter.
    """
    emitter = CloudWatchProvabilityEmitter(environment=environment, cw_client=cw_client)
    return ScheduledProvabilityEvaluator(
        store=store,
        expected_set=expected_set,
        is_provable=is_provable if is_provable is not None else _default_is_provable,
        digest_of_frame=digest_of_frame
        if digest_of_frame is not None
        else digest_of_canonical_frame_bytes,
        emitter=emitter,
    )


async def run_prov_sweep(
    evaluator: ScheduledProvabilityEvaluator, *, now: datetime | None = None
) -> EvaluationRun:
    """Run ONE in-process sweep + emit (heartbeat included). Returns the per-run record.

    The evaluator's emit is best-effort (a CloudWatch failure is logged, never raised — an
    observability emit must not take down the sweep). PROV-2's heartbeat rides EVERY run.
    """
    return await evaluator.evaluate_all(now if now is not None else datetime.now(UTC))
