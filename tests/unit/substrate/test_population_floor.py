"""Tiered population-floor BRIDGE tests (P7, two-sided) — SPIKE-population-floor-scope-2026-08-12.

The bridge rescopes the publish-time floor from the strict economic set
``{cost, mrr, offer_id, weekly_ad_spend}`` to the metric-CONSUMED set
``{mrr, office_phone, vertical}``, demoting the rest to a loud warn channel. Every test
here is discriminating in BOTH directions — the reason the bridge exists is that a null in
a DEMOTED column must SERVE (the exact shape of the three provisioning-lag incident days),
and the reason it is safe is that a null in a BLOCKING column must still REFUSE, including
the two dedup keys the strict floor never protected.

The suite also pins the FROZEN digest set byte-for-byte: the whole point of the decoupling
is that a floor rescope cannot re-key ``sv2-canonical-digest-1``.

CARDINAL P10 boundary: zero network. The PROV-7 emitter is exercised through a fake
CloudWatch client / recording emitter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl
import pytest

from autom8_asana.substrate.freshness import (
    _DIGEST_SCHEME,
    _VALUE_COLUMNS,
    FreshnessProof,
    canonical_digest,
)
from autom8_asana.substrate.live import (
    DataQualityWarningCollector,
    active_offer_rows,
    classifier_active_sections,
    served_active_mrr,
)
from autom8_asana.substrate.observe import (
    DEFAULT_ENVIRONMENT,
    DIMENSION_ENVIRONMENT,
    METRIC_ACTIVE_ROW_ECONOMIC_NULL_COUNT,
    SUBSTRATE_PROVABILITY_NAMESPACE,
    CloudWatchDataQualityEmitter,
)
from autom8_asana.substrate.population_floor import (
    OFFER_PUBLISH_FLOOR,
    STRICT_ECONOMIC_FLOOR,
    ColumnNullWarning,
    TieredPopulationFloor,
)
from autom8_asana.substrate.rebuild import (
    DefaultAcceptancePredicates,
    StagedVersion,
    ValidationFailure,
    ValidationReceipt,
    canonical_frame_bytes,
)
from autom8_asana.substrate.store import VersionId

if TYPE_CHECKING:
    from collections.abc import Sequence

_DAY = datetime(2026, 8, 12, 18, 0, tzinfo=UTC)
_BUILT = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
_INACTIVE_SECTION = "z-retired-inactive"  # asserted NOT in the classifier active set


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------


class _RecordingDataQualityEmitter:
    """A ``DataQualityEmitter`` that records instead of emitting (zero network)."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, datetime | None]] = []

    def emit_active_row_economic_nulls(self, count: int, *, at: datetime | None = None) -> None:
        self.calls.append((count, at))


class _FakeCloudWatch:
    """Minimal ``put_metric_data`` stand-in for the wire-shape proof."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_metric_data(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


def _offer_row(
    section: str,
    *,
    gid: str,
    mrr: float | None = 100.0,
    office_phone: str | None = "p",
    vertical: str | None = "v",
    cost: float | None = 10.0,
    offer_id: str | None = "o",
    weekly_ad_spend: float | None = 5.0,
) -> dict[str, Any]:
    """One offer row carrying every column both tiers of the floor inspect."""
    return {
        "gid": gid,
        "section": section,
        "mrr": mrr,
        "office_phone": office_phone,
        "vertical": vertical,
        "cost": cost,
        "offer_id": offer_id,
        "weekly_ad_spend": weekly_ad_spend,
    }


def _frame(rows: Sequence[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(list(rows))


def _validate(
    frame: pl.DataFrame, predicates: DefaultAcceptancePredicates
) -> ValidationReceipt | ValidationFailure:
    """Run ``validate`` with a well-formed proof so ONLY the population-floor is exercised."""
    proof = FreshnessProof(
        built_from_live_at=_BUILT, content_digest=canonical_digest(frame), sla_seconds=3600
    )
    staged = StagedVersion(
        version_id=VersionId("v-floor-bridge"),
        frame=frame,
        frame_bytes=canonical_frame_bytes(frame),
        proof=proof,
    )
    return predicates.validate(staged, _DAY)


def _offer_predicates(
    sink: DataQualityWarningCollector | None = None,
) -> DefaultAcceptancePredicates:
    """The predicates the offer parity path wires (``live.rebuild_offer_v2``)."""
    return DefaultAcceptancePredicates(
        active_predicate=active_offer_rows, floor=OFFER_PUBLISH_FLOOR, warning_sink=sink
    )


def test_fixture_inactive_section_is_really_inactive() -> None:
    """Fixture guard — the whole suite's active/inactive split depends on this."""
    assert _INACTIVE_SECTION not in classifier_active_sections()
    assert "active" in classifier_active_sections()


# ---------------------------------------------------------------------------
# (i) THE BRIDGE'S REASON TO EXIST — a demoted-column null on an active row SERVES
# ---------------------------------------------------------------------------


def test_demoted_column_null_on_active_row_serves_with_warning_and_metric() -> None:
    """THE incident shape (three consecutive parity days, spike §"Load-bearing facts" #4):
    a classifier-active row whose ``offer_id`` is null because the Business-Offers
    provisioning trigger has not fired yet, with every metric-consumed column complete.

    Under the STRICT floor this REFUSED — v2 declining a number v1 was serving correctly
    (the W2 over-refusal class). Under the BRIDGE it SERVES, the wound is named per-offer
    in the warning channel, and ``ActiveRowEconomicNullCount`` carries it to PROV-7.
    """
    frame = _frame(
        [
            _offer_row("ACTIVE", gid="1608", offer_id=None),  # provisioning lag
            _offer_row("ACTIVE", gid="1609"),  # healthy neighbour
        ]
    )
    emitter = _RecordingDataQualityEmitter()
    collector = DataQualityWarningCollector(emitter=emitter, at=_DAY)

    # STRICT floor (the pre-bridge behaviour) REFUSES the same frame — the delta is real.
    strict = _validate(frame, DefaultAcceptancePredicates(active_predicate=active_offer_rows))
    assert isinstance(strict, ValidationFailure)
    assert strict.check == "population-floor"
    assert "offer_id" in strict.reason

    # BRIDGE floor SERVES it.
    result = _validate(frame, _offer_predicates(collector))
    assert isinstance(result, ValidationReceipt)

    # (a) receipt channel — per-offer, naming the offending column only (never a value).
    assert collector.fired
    assert collector.blocks() == [{"gid": "1608", "section": "ACTIVE", "null_cols": ["offer_id"]}]

    # (b) metric channel — one emission carrying the wounded-row count.
    assert emitter.calls == [(1, _DAY)]


def test_served_number_is_unchanged_by_the_demoted_null() -> None:
    """The bridge's safety premise: the SERVED number does not read the demoted columns.

    ``active_mrr`` over the incident frame is byte-identical whether ``offer_id`` is null or
    populated — which is precisely why refusing on it was over-refusal.
    """
    wounded = _frame([_offer_row("ACTIVE", gid="1608", offer_id=None, mrr=500.0)])
    healed = _frame([_offer_row("ACTIVE", gid="1608", offer_id="1608", mrr=500.0)])
    assert served_active_mrr(wounded) == served_active_mrr(healed) == (500.0, 1)


# ---------------------------------------------------------------------------
# (ii) + (iii) BLOCKING TIER — sum input and the dedup-collapse guards still REFUSE
# ---------------------------------------------------------------------------


def test_null_mrr_on_active_row_refuses() -> None:
    """(ii) ``mrr`` is the sum input — a null on an active row makes the number wrong."""
    frame = _frame(
        [_offer_row("ACTIVE", gid="a", mrr=None), _offer_row("ACTIVE", gid="b", mrr=100.0)]
    )
    result = _validate(frame, _offer_predicates())
    assert isinstance(result, ValidationFailure)
    assert result.check == "population-floor"
    assert "mrr" in result.reason


@pytest.mark.parametrize("dedup_key", ["office_phone", "vertical"])
def test_null_dedup_key_on_active_row_refuses(dedup_key: str) -> None:
    """(iii) NEW PROTECTION the strict floor never had: the ``(office_phone, vertical)``
    dedup keys are correctness-bearing for the NUMBER, not metadata.

    ``metrics/compute.py:116`` dedups with ``unique(subset, keep="first")``, and polars
    treats nulls as EQUAL — so a null dedup key on two distinct active offers collapses
    them into one row and the sum silently loses the other's mrr.
    """
    frame = _frame(
        [
            _offer_row("ACTIVE", gid="a", **{dedup_key: None}),
            _offer_row("ACTIVE", gid="b", **{dedup_key: None}),
        ]
    )
    result = _validate(frame, _offer_predicates())
    assert isinstance(result, ValidationFailure)
    assert result.check == "population-floor"
    assert dedup_key in result.reason


@pytest.mark.parametrize("dedup_key", ["office_phone", "vertical"])
def test_null_dedup_key_would_silently_collapse_the_served_sum(dedup_key: str) -> None:
    """The TEETH behind (iii): prove the loss the guard prevents is real, not theoretical.

    Two distinct active offers at $500 each. With the dedup key populated the served number
    is $1,000; with it null on both rows the dedup collapses them and the served number
    reads $500 — a 50% silent loss, the founding wound's exact shape. The floor refuses the
    null variant, so this frame can never reach serving.
    """
    populated = _frame(
        [
            _offer_row("ACTIVE", gid="a", mrr=500.0, **{dedup_key: "one"}),
            _offer_row("ACTIVE", gid="b", mrr=500.0, **{dedup_key: "two"}),
        ]
    )
    collapsed = _frame(
        [
            _offer_row("ACTIVE", gid="a", mrr=500.0, **{dedup_key: None}),
            _offer_row("ACTIVE", gid="b", mrr=500.0, **{dedup_key: None}),
        ]
    )
    assert served_active_mrr(populated) == (1000.0, 2)
    assert served_active_mrr(collapsed) == (500.0, 1)  # the silent loss
    assert isinstance(_validate(collapsed, _offer_predicates()), ValidationFailure)


def test_absent_blocking_column_refuses_fail_closed() -> None:
    """A frame that omits a dedup key entirely cannot be deduped at all — REFUSE, never
    publish a frame whose served number is underivable (mirrors ``ActiveMrrColumnMissing``).
    """
    frame = _frame([_offer_row("ACTIVE", gid="a")]).drop("vertical")
    result = _validate(frame, _offer_predicates())
    assert isinstance(result, ValidationFailure)
    assert "vertical" in result.reason


# ---------------------------------------------------------------------------
# (v) the warn tier is scoped to the SERVED denominator
# ---------------------------------------------------------------------------


def test_demoted_null_on_inactive_row_produces_no_warning() -> None:
    """(v) v1's own frame carries ~2.9k value-column nulls, ALL on inactive-section rows
    (retired/parked offers legitimately have no economics). Warning on those would be pure
    noise, so the warn tier evaluates the SAME classifier-active population the floor does.
    """
    frame = _frame(
        [
            _offer_row("ACTIVE", gid="live"),
            _offer_row(_INACTIVE_SECTION, gid="retired", cost=None, offer_id=None),
        ]
    )
    emitter = _RecordingDataQualityEmitter()
    collector = DataQualityWarningCollector(emitter=emitter, at=_DAY)

    result = _validate(frame, _offer_predicates(collector))
    assert isinstance(result, ValidationReceipt)
    assert collector.warnings == ()
    assert collector.blocks() == []
    # DENSE series: the clean case still emits (0.0), so PROV-7 can return to OK.
    assert emitter.calls == [(0, _DAY)]


def test_warning_fires_even_when_a_blocking_column_refuses() -> None:
    """Loud-always: a demoted wound is surfaced on a run that refuses for a DIFFERENT
    reason, so a blocking failure never masks the data-quality signal.
    """
    frame = _frame([_offer_row("ACTIVE", gid="a", mrr=None, offer_id=None)])
    collector = DataQualityWarningCollector()
    assert isinstance(_validate(frame, _offer_predicates(collector)), ValidationFailure)
    assert collector.blocks() == [{"gid": "a", "section": "ACTIVE", "null_cols": ["offer_id"]}]


def test_collector_distinguishes_never_ran_from_found_nothing() -> None:
    """``null`` (floor never evaluated) vs ``[]`` (floor ran, clean) is an honest
    distinction the receipt must be able to carry — never a fabricated empty list.
    """
    assert DataQualityWarningCollector().blocks() is None
    fired = DataQualityWarningCollector()
    fired(())
    assert fired.blocks() == []


def test_multiple_demoted_nulls_are_named_per_offer_and_per_column() -> None:
    """The digest line is per-offer AND per-column — an operator can act on it directly."""
    frame = _frame(
        [
            _offer_row("ACTIVE", gid="a", offer_id=None, cost=None),
            _offer_row("ACTIVE", gid="b"),
            _offer_row("ACTIVE", gid="c", weekly_ad_spend=None),
        ]
    )
    collector = DataQualityWarningCollector()
    assert isinstance(_validate(frame, _offer_predicates(collector)), ValidationReceipt)
    assert collector.blocks() == [
        {"gid": "a", "section": "ACTIVE", "null_cols": ["cost", "offer_id"]},
        {"gid": "c", "section": "ACTIVE", "null_cols": ["weekly_ad_spend"]},
    ]


def test_warning_payload_carries_no_cell_values() -> None:
    """PII discipline (§6 #8): only gid / section / column NAMES ever leave the floor —
    ``office_phone`` is blocking-tier, so it can never even appear as a warned column name.
    """
    frame = _frame([_offer_row("ACTIVE", gid="a", office_phone="+1-555-0100", offer_id=None)])
    collector = DataQualityWarningCollector()
    _validate(frame, _offer_predicates(collector))
    assert "555-0100" not in str(collector.blocks())
    assert "office_phone" not in OFFER_PUBLISH_FLOOR.warning


# ---------------------------------------------------------------------------
# (iv) the FROZEN digest set is byte-untouched — the decoupling's whole point
# ---------------------------------------------------------------------------


def test_digest_value_columns_and_scheme_tag_are_byte_untouched() -> None:
    """(iv) ``_VALUE_COLUMNS`` and ``_DIGEST_SCHEME`` are the FROZEN ``sv2-canonical-digest-1``
    pins. The floor rescope MUST NOT have moved either — a change here silently re-keys
    every stored artifact's content digest and is a digest-scheme version event.
    """
    assert _VALUE_COLUMNS == ("cost", "mrr", "offer_id", "weekly_ad_spend")
    assert _DIGEST_SCHEME == "sv2-canonical-digest-1"


def test_offer_floor_is_decoupled_from_the_digest_set() -> None:
    """The two sets now answer different questions and have genuinely diverged: the floor
    added the dedup keys (invisible to the digest) and dropped three economic columns
    (still pinned by the digest). Neither is derivable from the other.
    """
    digest_set = set(_VALUE_COLUMNS)
    blocking = set(OFFER_PUBLISH_FLOOR.blocking)
    assert blocking != digest_set
    assert blocking - digest_set == {"office_phone", "vertical"}  # floor-only
    assert digest_set - blocking == {"cost", "offer_id", "weekly_ad_spend"}  # digest-only
    # …and the demoted columns are exactly the digest-only remainder, not silently dropped.
    assert set(OFFER_PUBLISH_FLOOR.warning) == digest_set - blocking


def test_pinned_digest_is_stable_across_a_demoted_null() -> None:
    """Belt-and-braces: the digest still SEES the demoted columns. The bridge changed what
    BLOCKS, not what is hashed — a frame whose ``offer_id`` flips to null gets a DIFFERENT
    digest (content identity is intact) while still publishing.
    """
    healed = _frame([_offer_row("ACTIVE", gid="a", offer_id="o")])
    wounded = _frame([_offer_row("ACTIVE", gid="a", offer_id=None)])
    assert canonical_digest(healed) != canonical_digest(wounded)


# ---------------------------------------------------------------------------
# non-regression: the default floor is unchanged and fail-closed
# ---------------------------------------------------------------------------


def test_unwired_predicates_keep_the_strict_pre_bridge_floor() -> None:
    """A caller that declares no floor is NEVER weakened by the bridge: the default is the
    strict economic set, so a demoted-column null still refuses for anything but the offer
    plane that explicitly opted in.
    """
    assert DefaultAcceptancePredicates().floor is STRICT_ECONOMIC_FLOOR
    assert STRICT_ECONOMIC_FLOOR.blocking == ("cost", "mrr", "offer_id", "weekly_ad_spend")
    assert STRICT_ECONOMIC_FLOOR.warning == ()

    frame = _frame([_offer_row("ACTIVE", gid="a", offer_id=None)])
    assert isinstance(_validate(frame, DefaultAcceptancePredicates()), ValidationFailure)


def test_floor_construction_guards() -> None:
    """A floor with no blocking tier is not a floor; overlapping tiers are incoherent."""
    with pytest.raises(ValueError, match="no blocking columns"):
        TieredPopulationFloor(blocking=())
    with pytest.raises(ValueError, match="disjoint"):
        TieredPopulationFloor(blocking=("mrr",), warning=("mrr", "cost"))


def test_a_second_consumer_can_declare_its_own_tiering() -> None:
    """The operator's BINDING extensibility qualifier: the substrate serves MANY consumers
    and must not be pigeonholed to ``active_mrr``. The floor is a value object injected at
    the seam — a different consumer declares different tiers over the SAME frame and gets a
    different verdict, with no edit to the validator.
    """
    frame = _frame([_offer_row("ACTIVE", gid="a", offer_id=None, cost=None)])
    spend_consumer = TieredPopulationFloor(blocking=("cost",), warning=("offer_id",))

    refused = _validate(
        frame,
        DefaultAcceptancePredicates(active_predicate=active_offer_rows, floor=spend_consumer),
    )
    assert isinstance(refused, ValidationFailure)  # cost blocks for THIS consumer
    assert isinstance(_validate(frame, _offer_predicates()), ValidationReceipt)  # not for offer


def test_warning_tier_ignores_absent_columns() -> None:
    """A warn column absent from the frame has no per-row attribution — skipped, not
    reported (the digest's ``MissingValueColumnsError`` already refuses it upstream).
    """
    floor = TieredPopulationFloor(blocking=("mrr",), warning=("nonexistent_column",))
    assert floor.null_warnings(_frame([_offer_row("ACTIVE", gid="a")])) == ()


def test_warnings_tolerate_a_frame_without_identity_columns() -> None:
    """A frame lacking ``gid``/``section`` still produces warnings (with null identity) —
    the channel degrades to un-attributed rather than crashing the publish path.
    """
    frame = pl.DataFrame(
        {"mrr": [1.0], "offer_id": [None]}, schema={"mrr": pl.Float64, "offer_id": pl.Utf8}
    )
    floor = TieredPopulationFloor(blocking=("mrr",), warning=("offer_id",))
    assert floor.null_warnings(frame) == (
        ColumnNullWarning(gid=None, section=None, null_columns=("offer_id",)),
    )


# ---------------------------------------------------------------------------
# PROV-7 emission wire shape
# ---------------------------------------------------------------------------


def test_data_quality_emitter_wire_shape_matches_the_prov_suite() -> None:
    """The emitted datum MUST carry the exact identity PROV-7 queries:
    (namespace, ``ActiveRowEconomicNullCount``, dimensions == {environment}).
    """
    client = _FakeCloudWatch()
    CloudWatchDataQualityEmitter(cw_client=client).emit_active_row_economic_nulls(3, at=_DAY)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["Namespace"] == SUBSTRATE_PROVABILITY_NAMESPACE
    (datum,) = call["MetricData"]
    assert datum["MetricName"] == METRIC_ACTIVE_ROW_ECONOMIC_NULL_COUNT
    assert datum["Value"] == 3.0
    assert datum["Unit"] == "Count"
    assert datum["Timestamp"] == _DAY
    assert datum["Dimensions"] == [{"Name": DIMENSION_ENVIRONMENT, "Value": DEFAULT_ENVIRONMENT}]


def test_data_quality_emitter_is_best_effort() -> None:
    """A CloudWatch failure must NEVER fail a publish the floor already accepted."""

    class _Exploding:
        def put_metric_data(self, **_kwargs: Any) -> None:
            raise RuntimeError("cloudwatch throttled")

    CloudWatchDataQualityEmitter(cw_client=_Exploding()).emit_active_row_economic_nulls(1)


def test_collector_without_emitter_still_feeds_the_receipt() -> None:
    """No CloudWatch client → the receipt channel is untouched (no silent double-loss)."""
    collector = DataQualityWarningCollector(emitter=None)
    collector((ColumnNullWarning(gid="a", section="ACTIVE", null_columns=("cost",)),))
    assert collector.blocks() == [{"gid": "a", "section": "ACTIVE", "null_cols": ["cost"]}]
