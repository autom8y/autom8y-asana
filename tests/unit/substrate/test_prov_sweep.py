"""WU-3 unit 3e — PROV-2 in-process sweep driver tests (G2 option-a).

CloudWatch ``put_metric_data`` is the ONLY outbound and it is a RECORDING STUB here —
never a live call. The load-bearing assertion is the iteration-1 NO-GO cure (a DEAD
``environment`` dimension): the emitted ``EvaluatorHeartbeat`` (PROV-2 dead-man) carries
the namespace + the ``environment`` dimension VALUE the terraform PROV-* alarms filter on.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import canonical_digest
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.observe import (
    METRIC_EVALUATOR_HEARTBEAT,
    SUBSTRATE_PROVABILITY_NAMESPACE,
)
from autom8_asana.substrate.prov_sweep import (
    PROV_ENVIRONMENT,
    build_prov_sweep_evaluator,
    digest_of_canonical_frame_bytes,
    run_prov_sweep,
)
from autom8_asana.substrate.rebuild import canonical_frame_bytes

_NOW = datetime(2026, 7, 30, 18, 0, tzinfo=UTC)
_TF_SHARED = (
    Path(__file__).resolve().parents[2] / "../terraform/services/asana/observability_alarms.tf"
).resolve()


class _RecordingCloudWatch:
    """Records every ``put_metric_data`` call (Namespace + MetricData) — no AWS touched."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_metric_data(self, *, Namespace: str, MetricData: list[dict[str, Any]]) -> None:
        self.calls.append({"Namespace": Namespace, "MetricData": MetricData})


class _EmptyExpectedSet:
    """A registry ∪ store expected-set of nothing — the sweep still emits the heartbeat."""

    async def registry_targets(self) -> set[ArtifactId]:
        return set()

    async def store_enumeration(self) -> set[ArtifactId]:
        return set()


class _OneArtifactExpectedSet:
    """Registry and store agree on one artifact (a healthy, provable sweep)."""

    def __init__(self, aid: ArtifactId) -> None:
        self._aid = aid

    async def registry_targets(self) -> set[ArtifactId]:
        return {self._aid}

    async def store_enumeration(self) -> set[ArtifactId]:
        return {self._aid}


class _InMemoryStore:
    """Minimal ArtifactStore: read_current returns canonical-frame bytes + a fresh proof."""

    def __init__(self, frame: pl.DataFrame, *, built_at: datetime) -> None:
        from autom8_asana.substrate.freshness import FreshnessProof

        self._bytes = canonical_frame_bytes(frame)
        self._proof = FreshnessProof(
            built_from_live_at=built_at, content_digest=canonical_digest(frame), sla_seconds=3600
        )

    async def read_current(self, _aid: ArtifactId) -> tuple[bytes, Any]:
        return self._bytes, self._proof


def _heartbeat_datum(cw: _RecordingCloudWatch) -> dict[str, Any]:
    for call in cw.calls:
        for datum in call["MetricData"]:
            if datum["MetricName"] == METRIC_EVALUATOR_HEARTBEAT:
                return datum
    raise AssertionError("no EvaluatorHeartbeat datum emitted")


async def test_3e_sweep_emits_heartbeat_with_namespace_and_environment() -> None:
    """The dead-man heartbeat emits to the PROV namespace with the environment dimension."""
    cw = _RecordingCloudWatch()
    unread_frame = pl.DataFrame(
        {"offer_id": ["a"], "cost": [1.0], "mrr": [1.0], "weekly_ad_spend": [1.0]}
    )
    evaluator = build_prov_sweep_evaluator(
        store=_InMemoryStore(unread_frame, built_at=_NOW),  # unread (empty expected-set)
        expected_set=_EmptyExpectedSet(),
        cw_client=cw,
    )
    run = await run_prov_sweep(evaluator, now=_NOW)

    assert cw.calls, "the sweep must emit at least one put_metric_data batch"
    assert all(c["Namespace"] == SUBSTRATE_PROVABILITY_NAMESPACE for c in cw.calls)
    heartbeat = _heartbeat_datum(cw)
    assert heartbeat["Value"] == 1.0  # PROV-2: present on every run
    dims = {d["Name"]: d["Value"] for d in heartbeat["Dimensions"]}
    assert dims == {"environment": PROV_ENVIRONMENT}  # the F-1 dead-dimension cure
    assert run.run_id  # the self-heartbeat identity


async def test_3e_environment_matches_terraform_alarm_filter() -> None:
    """Iteration-1 NO-GO guard: the emitted env VALUE equals the terraform var.environment default.

    A drift on either side un-wires every PROV-* alarm (they filter
    ``dimensions = { environment = var.environment }``).
    """
    tf_default = re.search(
        r'variable\s+"environment"\s*\{(.*?)\n\}', _TF_SHARED.read_text(), re.DOTALL
    )
    assert tf_default, "environment variable not found in observability_alarms.tf"
    value = re.search(r'default\s*=\s*"([^"]*)"', tf_default.group(1))
    assert value and value.group(1) == PROV_ENVIRONMENT == "production"


async def test_3e_healthy_sweep_is_all_provable() -> None:
    """A provable artifact reads provable via the real is_provable + canonical-bytes digest."""
    aid = ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)
    frame = pl.DataFrame(
        {"offer_id": ["a"], "cost": [1.0], "mrr": [500.0], "weekly_ad_spend": [10.0]}
    )
    cw = _RecordingCloudWatch()
    evaluator = build_prov_sweep_evaluator(
        store=_InMemoryStore(frame, built_at=_NOW),
        expected_set=_OneArtifactExpectedSet(aid),
        cw_client=cw,
    )
    run = await run_prov_sweep(evaluator, now=_NOW)

    assert run.expected_count == 1
    assert run.unprovable_count == 0  # digest re-derives; age within sla -> PROVABLE
    assert run.expected_set_mismatch_count == 0
    assert _heartbeat_datum(cw)["Value"] == 1.0


def test_3e_digest_of_canonical_frame_bytes_roundtrips() -> None:
    """[H19] the digest re-derived from stored bytes equals the Seam-1 digest of the frame."""
    frame = pl.DataFrame(
        {
            "offer_id": ["a", "b"],
            "cost": [1.0, 2.0],
            "mrr": [500.0, 600.0],
            "weekly_ad_spend": [10.0, 20.0],
        }
    )
    raw = canonical_frame_bytes(frame)
    assert digest_of_canonical_frame_bytes(raw) == canonical_digest(frame)


def _sparse_late_typed_frame(n_rows: int = 150) -> pl.DataFrame:
    """The live wound shape (DEFECT-prov-digest-bare-inference-2026-08-12): a structural
    column null past polars' default 100-row inference prefix, first real value a str —
    bare ``pl.DataFrame(rows)`` infers Null dtype then raises ComputeError on the append.

    ``canonical_frame_bytes`` sorts the row ENCODINGS lexicographically, so the poison
    row must sort LAST to land past the prefix: every field before ``mrr`` is identical
    across rows and the poison row carries the lexicographically-largest ``mrr``.
    """
    sparse = [None] * (n_rows - 1) + ["BETTER25CTWA"]
    return pl.DataFrame(
        {
            "offer_id": [f"o{i:03d}" for i in range(n_rows)],
            "cost": [10.0] * n_rows,
            "mrr": [500.0 + i for i in range(n_rows - 1)] + [999.0],
            "weekly_ad_spend": [10.0] * n_rows,
            "trackstat_id": sparse,
        }
    )


def test_3e_digest_rederivation_survives_sparse_late_typed_column() -> None:
    """The re-derivation must not depend on inferring NON-value columns: a sparse
    late-typed structural column (the exact live artifact shape that zeroed completeness
    on cycles 1-2 of the S8-2 window) still yields the Seam-1 digest.
    """
    frame = _sparse_late_typed_frame()
    raw = canonical_frame_bytes(frame)
    # Teeth guard (QA-#351 L2): the fixture only discriminates while the poison row
    # sorts PAST polars' 100-row inference prefix — an innocent edit that varies an
    # earlier JSON field would silently migrate it inside and the test would pass on
    # pre-fix code too.
    chunks = raw.decode("utf-8").split("\x1e")
    poison_index = next(i for i, chunk in enumerate(chunks) if "BETTER25CTWA" in chunk)
    assert poison_index >= 100, "fixture lost its teeth: poison row inside the inference prefix"
    assert digest_of_canonical_frame_bytes(raw) == canonical_digest(frame)


def test_3e_digest_rederivation_refuses_rows_missing_a_value_column() -> None:
    """A stored artifact whose rows lack a pinned value column is partial/foreign —
    refuse loudly (→ an [H20] indeterminate skip at the evaluator), never null-fill.
    """
    import json as json_mod

    import pytest

    rows = [{"offer_id": "a", "cost": 1.0, "weekly_ad_spend": 10.0}]  # no mrr
    raw = "\x1e".join(
        json_mod.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows
    ).encode("utf-8")
    with pytest.raises(ValueError, match="mrr"):
        digest_of_canonical_frame_bytes(raw)


async def test_3e_sweep_evaluates_artifact_with_sparse_late_typed_column() -> None:
    """Loop-level regression of the live wound: with the poisoned-shape artifact stored,
    the sweep must produce a VERDICT (completeness 100, provable), not an indeterminate
    skip (completeness 0.0 / evaluated 0 — the exact cycles-1/2 PROV reading).
    """
    aid = ArtifactId(project_gid="1143843662099250", entity_type=EntityType.OFFER)
    frame = _sparse_late_typed_frame()
    cw = _RecordingCloudWatch()
    evaluator = build_prov_sweep_evaluator(
        store=_InMemoryStore(frame, built_at=_NOW),
        expected_set=_OneArtifactExpectedSet(aid),
        cw_client=cw,
    )
    run = await run_prov_sweep(evaluator, now=_NOW)

    assert run.evaluated_count == 1
    assert run.completeness == 100.0
    assert run.unprovable_count == 0
    assert not run.unevaluated
