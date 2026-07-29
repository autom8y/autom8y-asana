"""S5 SERVING — the CP-1..6 consumer adapters (DARK).

Bar: TDD §4 Seam 4 [H18] (thin adapters) + FEASIBILITY §4d (CP-1..6 forced through the
choke-point) + DP-3 (424 + Retry-After + shape-hostile bodies; NO Refused-200) +
RC-acceptance CP-1..6. Each adapter routes through the ``SubstrateReader`` by
construction (holds a reader / consumes a ServedNumber) — none touches the store.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autom8_asana.core.types import EntityType
from autom8_asana.substrate.freshness import FreshnessProof
from autom8_asana.substrate.identity import ArtifactId, artifact_key
from autom8_asana.substrate.serve import (
    Provable,
    Refused,
    RefuseReason,
    ServedNumber,
    single_copy_payload,
    sunset_stale_payload,
)
from autom8_asana.substrate.serve_adapters import (
    DATA_INTEGRITY_EXIT_CODE,
    HTTP_STATUS_OK,
    HTTP_STATUS_REFUSED,
    HTTP_STATUS_UNSERVABLE_ENTITY,
    ForceWarmRecheckAdapter,
    OfflineServeAdapter,
    QueryServeAdapter,
    RecheckOutcome,
    SubstratePersistenceReader,
    artifact_cache_key,
    coerce_entity_type,
    refusal_reason_code,
    serve_result_to_cli,
    serve_result_to_http,
    serve_result_to_recheck,
)

NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)
AID = ArtifactId(project_gid="1200000000000001", entity_type=EntityType.OFFER)
_PROOF = FreshnessProof(
    built_from_live_at=NOW - timedelta(seconds=60), content_digest="0" * 64, sla_seconds=3600
)

_ALL_REASONS = [
    RefuseReason.STALE,
    RefuseReason.CORRUPT,
    RefuseReason.MISSING,
    RefuseReason.DIVERGENT,
]

# Fields a status-ignoring client might parse as a served value — none may appear in a
# refusal body (shape-hostility, DP-3 §B).
_DATA_SHAPED_KEYS = {"rows", "value", "data", "aggregate", "result", "records"}


def _provable() -> Provable:
    return Provable(frame=b"the-frame", proof=_PROOF)


def _refused(reason: RefuseReason) -> Refused:
    return Refused(reason=reason, detail=single_copy_payload("v2/offer", 7200.0))


class _FixedReader:
    """A ``SubstrateReader`` that returns a preset ServedNumber (adapters are read-agnostic)."""

    def __init__(self, served: ServedNumber) -> None:
        self._served = served
        self.reads: list[ArtifactId] = []

    async def read(self, aid: ArtifactId) -> ServedNumber:
        self.reads.append(aid)
        return self._served


# ==================================================================== CP-1 =====


def test_cp1_cli_provable_exits_zero_with_frame() -> None:
    result = serve_result_to_cli(_provable())
    assert result.exit_code == 0
    assert result.frame == b"the-frame"


@pytest.mark.parametrize("reason", _ALL_REASONS)
def test_cp1_cli_refused_is_non_zero_data_integrity_and_prints_no_number(
    reason: RefuseReason,
) -> None:
    result = serve_result_to_cli(_refused(reason))
    assert result.exit_code == DATA_INTEGRITY_EXIT_CODE != 0
    assert result.frame is None  # shape-hostile: no fake number on stdout
    assert "DATA-INTEGRITY" in result.message
    # the message names the reason but carries no dollar figure / served value.
    assert "7200" not in result.message


async def test_cp1_offline_adapter_routes_through_the_reader() -> None:
    reader = _FixedReader(_refused(RefuseReason.STALE))
    result = await OfflineServeAdapter(reader).serve_cli(AID)
    assert reader.reads == [AID]  # went through the choke-point
    assert result.exit_code == DATA_INTEGRITY_EXIT_CODE


# ==================================================================== CP-2 =====


def test_cp2_recheck_translation_is_is_provable_based() -> None:
    assert serve_result_to_recheck(_provable()) is RecheckOutcome.PROVABLE
    assert serve_result_to_recheck(_refused(RefuseReason.STALE)) is RecheckOutcome.REFUSED


async def test_cp2_force_warm_recheck_refuses_a_non_provable_recheck() -> None:
    reader = _FixedReader(_refused(RefuseReason.STALE))
    outcome = await ForceWarmRecheckAdapter(reader).recheck(AID)
    assert outcome is RecheckOutcome.REFUSED  # is_provable verdict, never a fresh-mtime lie


# ================================================================ CP-3/4/5 =====


def test_cp345_provable_maps_to_200_with_frame() -> None:
    result = serve_result_to_http(_provable(), retry_after_seconds=180)
    assert result.status_code == HTTP_STATUS_OK
    assert result.frame == b"the-frame"
    assert "Retry-After" not in result.headers


@pytest.mark.parametrize("reason", _ALL_REASONS)
def test_cp345_every_refused_is_424_with_retry_after(reason: RefuseReason) -> None:
    result = serve_result_to_http(_refused(reason), retry_after_seconds=180)
    assert result.status_code == HTTP_STATUS_REFUSED == 424  # non-2xx Failed Dependency
    assert result.headers["Retry-After"] == "180"  # bound to the rebuild schedule (parameterized)
    assert result.frame is None
    assert result.body["reason"] == reason.value
    assert result.body["code"] == refusal_reason_code(reason)


@pytest.mark.parametrize("reason", _ALL_REASONS)
def test_cp345_refusal_body_is_shape_hostile(reason: RefuseReason) -> None:
    """No data-shaped field — a status-ignoring client parses a refusal, not empty success."""
    body = serve_result_to_http(_refused(reason), retry_after_seconds=30).body
    assert body["substrate_refused"] is True
    assert _DATA_SHAPED_KEYS.isdisjoint(body.keys())


def test_cp345_no_input_yields_a_200_for_a_refused() -> None:
    """Two-sided: the stale-200 paradigm (superseded ADR) is unconstructable."""
    for reason in _ALL_REASONS:
        assert serve_result_to_http(_refused(reason), retry_after_seconds=1).status_code != 200


def test_cp345_sunset_breach_marker_crosses_the_wire() -> None:
    """C13: a sunset-breach STALE refusal carries the machine-distinguishable marker."""
    sunset_after = datetime(2026, 6, 1, tzinfo=UTC)
    payload = sunset_stale_payload("v2/offer", 999.0, sunset_after=sunset_after, observed_at=NOW)
    result = serve_result_to_http(
        Refused(reason=RefuseReason.STALE, detail=payload), retry_after_seconds=60
    )
    assert result.status_code == 424
    assert result.body["reason"] == "stale"  # reason stays STALE (no EXPIRED member)
    assert result.body["sunset_breach"]["surface"] == "v2/offer"
    assert result.body["sunset_breach"]["sunset_after"] == sunset_after.isoformat()


def test_cp345_refusal_body_carries_no_topology() -> None:
    """Security: the wire body's plane is a logical label, no S3 key/bucket/path."""
    body = serve_result_to_http(_refused(RefuseReason.STALE), retry_after_seconds=1).body
    assert body["plane"] == "v2/offer"
    assert "dataframes-v2" not in str(body)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("business", EntityType.BUSINESS),
        ("offer", EntityType.OFFER),
        ("unknown", None),  # UNKNOWN is not servable
        ("bogus", None),  # not an EntityType at all
        ("project", None),  # structural, non-servable
    ],
)
def test_cp34_coerce_entity_type_coerces_or_refuses(raw: str, expected: EntityType | None) -> None:
    assert coerce_entity_type(raw) == expected


def test_cp5_cache_key_is_derived_from_the_typed_artifact_id() -> None:
    assert artifact_cache_key(AID) == artifact_key(AID)
    assert artifact_cache_key(AID).startswith("dataframes-v2/")


async def test_cp345_query_adapter_unknown_entity_is_a_422_client_error() -> None:
    reader = _FixedReader(_provable())
    result = await QueryServeAdapter(reader).query(
        "1200000000000001", "bogus", retry_after_seconds=90
    )
    assert result.status_code == HTTP_STATUS_UNSERVABLE_ENTITY == 422  # NOT the 424 data class
    assert reader.reads == []  # never reached the reader — refused at the boundary
    assert _DATA_SHAPED_KEYS.isdisjoint(result.body.keys())


async def test_cp345_query_adapter_provable_maps_to_200() -> None:
    reader = _FixedReader(_provable())
    result = await QueryServeAdapter(reader).query(
        "1200000000000001", "offer", retry_after_seconds=90
    )
    assert result.status_code == 200
    assert reader.reads and reader.reads[0].entity_type is EntityType.OFFER


async def test_cp345_query_adapter_refused_maps_to_424() -> None:
    reader = _FixedReader(_refused(RefuseReason.STALE))
    result = await QueryServeAdapter(reader).query(
        "1200000000000001", "offer", retry_after_seconds=90
    )
    assert result.status_code == 424
    assert result.headers["Retry-After"] == "90"


# ==================================================================== CP-6 =====


async def test_cp6_persistence_wrapper_routes_through_the_choke_point() -> None:
    """The v2 persistence-wrapper takes a typed ArtifactId (no str|None plane-blind surface)."""
    reader = _FixedReader(_provable())
    served = await SubstratePersistenceReader(reader).read_artifact(AID)
    assert reader.reads == [AID]
    assert isinstance(served, Provable)
