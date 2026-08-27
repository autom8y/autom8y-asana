"""EMIT-2 scheduled sweep handler tests (option-b of the RULING's G2).

CloudWatch/S3 are RECORDING/FAKE seams here — never a live call (the CARDINAL
P10 boundary parity_run states: ``handler_async`` is the tested composition
point; the real seams are constructed only when the deployed Lambda runs it).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import polars as pl

from autom8_asana.core.types import EntityType
from autom8_asana.lambda_handlers.prov_sweep import (
    REGISTRY_TARGETS,
    S3PointerExpectedSetSource,
    handler_async,
)
from autom8_asana.substrate.freshness import FreshnessProof, canonical_digest
from autom8_asana.substrate.identity import ArtifactId
from autom8_asana.substrate.live import OFFER_PROJECT_GID
from autom8_asana.substrate.observe import (
    METRIC_EVALUATOR_HEARTBEAT,
    METRIC_MAX_STALENESS_AGE_SECONDS,
    SUBSTRATE_PROVABILITY_NAMESPACE,
)
from autom8_asana.substrate.rebuild import canonical_frame_bytes

_NOW = datetime(2026, 8, 27, 6, 0, tzinfo=UTC)
_OFFER_AID = ArtifactId(project_gid=OFFER_PROJECT_GID, entity_type=EntityType.OFFER)


class _RecordingCloudWatch:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_metric_data(self, *, Namespace: str, MetricData: list[dict[str, Any]]) -> None:
        self.calls.append({"Namespace": Namespace, "MetricData": MetricData})


class _OneArtifactExpectedSet:
    def __init__(self, aid: ArtifactId) -> None:
        self._aid = aid

    async def registry_targets(self) -> set[ArtifactId]:
        return {self._aid}

    async def store_enumeration(self) -> set[ArtifactId]:
        return {self._aid}


class _InMemoryStore:
    """Minimal ArtifactStore: canonical-frame bytes + a fresh proof (same shape as
    tests/unit/substrate/test_prov_sweep.py)."""

    def __init__(self, frame: pl.DataFrame, *, built_at: datetime) -> None:
        self._bytes = canonical_frame_bytes(frame)
        self._proof = FreshnessProof(
            built_from_live_at=built_at,
            content_digest=canonical_digest(frame),
            sla_seconds=3600,
        )

    async def read_current(self, _aid: ArtifactId) -> tuple[bytes, Any]:
        return self._bytes, self._proof


def _data(cw: _RecordingCloudWatch, name: str) -> list[dict[str, Any]]:
    return [d for c in cw.calls for d in c["MetricData"] if d["MetricName"] == name]


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {"offer_id": ["a"], "cost": [1.0], "mrr": [500.0], "weekly_ad_spend": [10.0]}
    )


def test_registry_targets_pin_the_offer_artifact() -> None:
    """The pinned registered set IS the live offer artifact — a second entry here
    is a deliberate seam change."""
    assert frozenset({_OFFER_AID}) == REGISTRY_TARGETS


async def test_handler_sweep_emits_heartbeat_and_per_artifact_staleness() -> None:
    """One scheduled invocation = one sweep: PROV-2's heartbeat emits, and the
    EMIT-1 per-artifact staleness series carries the PROV-8 dimension trio."""
    cw = _RecordingCloudWatch()
    summary = await handler_async(
        {},
        None,
        store=_InMemoryStore(_frame(), built_at=_NOW),
        expected_set=_OneArtifactExpectedSet(_OFFER_AID),
        cw_client=cw,
        now=_NOW,
    )

    assert all(c["Namespace"] == SUBSTRATE_PROVABILITY_NAMESPACE for c in cw.calls)
    heartbeats = _data(cw, METRIC_EVALUATOR_HEARTBEAT)
    assert [d["Value"] for d in heartbeats] == [1.0]

    per_artifact = [
        d
        for d in _data(cw, METRIC_MAX_STALENESS_AGE_SECONDS)
        if {dim["Name"] for dim in d["Dimensions"]} == {"environment", "project_gid", "entity_type"}
    ]
    assert len(per_artifact) == 1
    dims = {dim["Name"]: dim["Value"] for dim in per_artifact[0]["Dimensions"]}
    assert dims["project_gid"] == OFFER_PROJECT_GID
    assert dims["entity_type"] == "offer"

    assert summary["expected_count"] == 1
    assert summary["evaluated_count"] == 1
    assert summary["unprovable_count"] == 0
    assert summary["heartbeat_emitted"] is True
    assert summary["evaluation_failed"] is False


async def test_handler_environment_dimension_is_env_var_overridable(
    monkeypatch: Any,
) -> None:
    """SUBSTRATE_PROV_ENVIRONMENT overrides the emitted environment dimension
    VALUE (the terraform alarms filter on var.environment — the two are wired to
    the same deploy-time source in the monorepo module)."""
    monkeypatch.setenv("SUBSTRATE_PROV_ENVIRONMENT", "staging")
    cw = _RecordingCloudWatch()
    summary = await handler_async(
        {},
        None,
        store=_InMemoryStore(_frame(), built_at=_NOW),
        expected_set=_OneArtifactExpectedSet(_OFFER_AID),
        cw_client=cw,
        now=_NOW,
    )

    heartbeat = _data(cw, METRIC_EVALUATOR_HEARTBEAT)[0]
    dims = {d["Name"]: d["Value"] for d in heartbeat["Dimensions"]}
    assert dims == {"environment": "staging"}
    assert summary["environment"] == "staging"


class _FakePaginator:
    def __init__(self, keys: list[str]) -> None:
        self._keys = keys

    def paginate(self, *, Bucket: str, Prefix: str) -> list[dict[str, Any]]:
        assert Prefix == "dataframes-v2/"
        return [{"Contents": [{"Key": k} for k in self._keys]}]


class _FakeS3:
    def __init__(self, keys: list[str]) -> None:
        self._keys = keys

    def get_paginator(self, name: str) -> _FakePaginator:
        assert name == "list_objects_v2"
        return _FakePaginator(self._keys)


async def test_store_enumeration_parses_pointer_keys_and_skips_debris() -> None:
    """Enumeration accepts ONLY well-formed pointer keys that construct a servable
    ``ArtifactId``. The live store carries key debris at the wrong depth (observed
    2026-08-27: ``dataframes-v2/current.json`` and ``dataframes-v2/{gid}/current.json``)
    — none of it may enumerate as an artifact, and none of it may crash the sweep."""
    keys = [
        # THE artifact pointer — the one valid enumeration.
        f"dataframes-v2/{OFFER_PROJECT_GID}/offer/current.json",
        # Version blobs under the artifact — not pointers.
        f"dataframes-v2/{OFFER_PROJECT_GID}/offer/versions/2026/blob",
        # Live-observed debris: pointer-named keys at the wrong depth.
        "dataframes-v2/current.json",
        f"dataframes-v2/{OFFER_PROJECT_GID}/current.json",
        "dataframes-v2/versions/2026/blob",
        # Pointer-shaped but not a servable identity: guarded at construction, skipped loud.
        "dataframes-v2/999/unknown/current.json",
        # Non-numeric gid segment never matches the pointer pattern.
        "dataframes-v2/not-a-gid/offer/current.json",
    ]
    source = S3PointerExpectedSetSource("test-bucket", client=_FakeS3(keys))

    assert await source.store_enumeration() == {_OFFER_AID}
    assert await source.registry_targets() == {_OFFER_AID}


async def test_expected_set_failure_surfaces_as_loud_failed_run() -> None:
    """A broken enumeration (S3 AccessDenied) must NOT crash the handler — it
    flows into evaluate_all's F-2 shape: heartbeat still emits, evaluation_failed
    is disclosed on the summary."""

    class _ExplodingS3:
        def get_paginator(self, name: str) -> Any:
            raise RuntimeError("AccessDenied")

    cw = _RecordingCloudWatch()
    summary = await handler_async(
        {},
        None,
        store=_InMemoryStore(_frame(), built_at=_NOW),
        expected_set=S3PointerExpectedSetSource("test-bucket", client=_ExplodingS3()),
        cw_client=cw,
        now=_NOW,
    )

    assert summary["evaluation_failed"] is True
    assert summary["expected_count"] == 0
    assert [d["Value"] for d in _data(cw, METRIC_EVALUATOR_HEARTBEAT)] == [1.0]
