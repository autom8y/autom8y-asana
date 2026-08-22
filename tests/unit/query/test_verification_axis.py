"""Wire-level tests for the verification axis on the /rows serve path.

Covers what the derivation-level suite cannot: the axis actually reaching the
response meta, at the request-resolved grain, declared in the capability roster,
without adding an S3 read and without disturbing ``honest_contract_complete``.

The capability-roster literals are spelled out here rather than imported. A test
that imports the constant it is checking cannot catch a rename — and a rename is
exactly the failure this axis is most exposed to, because the consumer matches by
wire field name and a mismatch is silently inert.

CLOCK DISCIPLINE — read before adding a test here
-------------------------------------------------
Every stamp in this file is expressed relative to ``_NOW``, and ``_NOW`` is the
clock the code under test reads: the ``frozen_serve_clock`` autouse fixture binds
it into ``compute_serve_verification``'s documented ``now`` seam. Fixture clock
and derivation clock are ONE clock, so an emitted age is exactly the age the
fixture stamped.

This is not decoration. As landed in #384 this file pinned ``_NOW`` to a fixed
calendar instant while the derivation computed against the real wall clock, so
every emitted ``verification_age_seconds`` was ``wall_clock - _NOW + fixture_age``
— a number that grows without bound. It crossed this file's hard-coded 52566.7s
bound around 2026-08-20T05:30Z and from then on failed every PR and every merge
repo-wide. A fixed calendar instant asserted against a live clock is structurally
incapable of staying true; it does not fail when the code breaks, it fails when
the calendar advances.

So: never assert a wall-clock-derived age against a hard-coded bound. Either
thread the clock (as here and as ``tests/unit/metrics/test_serve_verification.py``
does directly), or assert relative to the same clock the code reads.
``test_the_emitted_age_is_measured_against_the_frozen_clock`` is the tripwire that
fails loudly if this freeze ever detaches, instead of letting the rot return.
"""

from __future__ import annotations

import functools
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionStatus,
)
from autom8_asana.metrics.freshness import compute_serve_verification
from autom8_asana.models.business.activity import (
    OFFER_CLASSIFIER,
    AccountActivity,
    SectionClassifier,
)
from autom8_asana.query.engine import QueryEngine
from autom8_asana.query.models import (
    VERIFICATION_AXIS_FIELDS,
    AggregateMeta,
    AggregateRequest,
    RowsMeta,
    RowsRequest,
    declare_axes,
)
from autom8_asana.services.query_service import EntityQueryService

if TYPE_CHECKING:
    from collections.abc import Iterator

#: The one clock. Both the fixture stamps below and the derivation under test
#: read it — see the module docstring's CLOCK DISCIPLINE note. Held identical to
#: the derivation-level suite's ``_NOW`` so the two suites stay coherent.
_NOW = datetime(2026, 8, 19, 15, 0, 0, tzinfo=UTC)
_PROJECT_GID = "1143843662099250"

#: The engine imports ``compute_serve_verification`` inside the function body, so
#: this module attribute is what it resolves at call time. Spelled once here and
#: shared with the derivation-raises test, which depends on the same target
#: biting — if the engine ever stops resolving through it, that test fails too.
_DERIVATION_TARGET = "autom8_asana.metrics.freshness.compute_serve_verification"


@pytest.fixture(autouse=True)
def frozen_serve_clock() -> Iterator[None]:
    """Bind ``_NOW`` into the derivation's ``now`` seam for every test in this file.

    ``compute_serve_verification`` documents ``now`` as "Override for
    ``datetime.now(tz=UTC)``; injectable for tests" and the derivation-level suite
    threads it on every call. The serve path cannot: ``QueryEngine`` calls the
    derivation with two arguments and owns no clock of its own, so the wire-level
    seat has no argument to pass. Binding the parameter here reaches the same seam
    from the outside.

    Only ``now`` is pinned. The real function runs on the real manifest with the
    real resolved section set — the fold, the missing-count subtraction, the
    backfill rule and the isoformat emission are all untouched production code.
    """
    with patch(_DERIVATION_TARGET, functools.partial(compute_serve_verification, now=_NOW)):
        yield


def _section(name: str, *, last_verified_at: datetime | None) -> SectionInfo:
    return SectionInfo(
        status=SectionStatus.COMPLETE,
        rows=3,
        name=name,
        last_verified_at=last_verified_at,
    )


#: A manifest section that is in the offer classifier's `inactive` group, so it
#: falls in NEITHER requested classification. Stamped absurdly old on purpose.
_OUT_OF_SCOPE_SECTION = "COMPLETE"
_OUT_OF_SCOPE_AGE = 99999.0


def _divergent_manifest(*, active_age: float, activating_age: float) -> SectionManifest:
    """Per-pool stamps that DIFFER — the only fixture that can discriminate grain.

    Production cannot: one ``now`` is taken for a whole warm pass, so every
    section carries the identical instant and every candidate grain yields the
    same number regardless of which pool the fold walked.

    Built from the REAL offer classifier's pools so that coverage is complete
    (zero in-scope sections absent from the manifest), matching the live shape.
    A partial fixture would route through AXIS-NULL and test nothing about grain.
    """
    active = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE)
    activating = OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVATING)

    sections: dict[str, SectionInfo] = {}
    for i, name in enumerate(sorted(active)):
        sections[f"a{i}"] = _section(
            name.upper(), last_verified_at=_NOW - timedelta(seconds=active_age)
        )
    for i, name in enumerate(sorted(activating)):
        sections[f"g{i}"] = _section(
            name.upper(), last_verified_at=_NOW - timedelta(seconds=activating_age)
        )
    sections["out0"] = _section(
        _OUT_OF_SCOPE_SECTION, last_verified_at=_NOW - timedelta(seconds=_OUT_OF_SCOPE_AGE)
    )

    return SectionManifest(
        project_gid=_PROJECT_GID,
        entity_type="offer",
        sections=sections,
        total_sections=len(sections),
        completed_sections=len(sections),
        schema_version="1.6.0",
    )


@pytest.fixture
def offer_schema() -> DataFrameSchema:
    return DataFrameSchema(
        name="offer",
        task_type="Offer",
        columns=[
            ColumnDef("gid", "Utf8", nullable=False),
            ColumnDef("name", "Utf8", nullable=True),
            ColumnDef("section", "Utf8", nullable=True),
        ],
    )


@pytest.fixture
def offer_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "gid": ["1", "2", "3", "4"],
            "name": ["A", "B", "C", "D"],
            "section": ["ACTIVE", "STAGING", "ACTIVATING", "COMPLETE"],
        }
    )


def _make_engine(
    df: pl.DataFrame,
    *,
    manifest: Any,
    raise_on_read: BaseException | None = None,
) -> tuple[QueryEngine, AsyncMock]:
    """Engine over a service whose SectionPersistence is a controllable double."""
    service = EntityQueryService()
    service.get_dataframe = AsyncMock(return_value=df)  # type: ignore[method-assign]

    persistence = MagicMock()
    if raise_on_read is not None:
        persistence.get_manifest_async = AsyncMock(side_effect=raise_on_read)
    else:
        persistence.get_manifest_async = AsyncMock(return_value=manifest)
    object.__setattr__(service, "_section_persistence", persistence)

    return QueryEngine(provider=service), persistence.get_manifest_async


async def _run_rows(
    engine: QueryEngine,
    schema: DataFrameSchema,
    *,
    classification: str | None,
) -> RowsMeta:
    body: dict[str, Any] = {}
    if classification is not None:
        body["classification"] = classification
    request = RowsRequest.model_validate(body)
    with patch("autom8_asana.query.engine.SchemaRegistry") as registry_cls:
        registry = MagicMock()
        registry.get_schema.return_value = schema
        registry_cls.get_instance.return_value = registry
        result = await engine.execute_rows(
            entity_type="offer",
            project_gid=_PROJECT_GID,
            client=AsyncMock(),
            request=request,
        )
    return result.meta


class TestCapabilityRosterLiterals:
    """CAP-SIG spelling. A token mismatch here is silently inert in production."""

    def test_the_three_literals_are_pinned(self) -> None:
        assert list(VERIFICATION_AXIS_FIELDS) == [
            "verified_at",
            "verification_age_seconds",
            "verification_backfill_used",
        ]

    def test_no_collapsed_single_axis_token(self) -> None:
        """The roster names WIRE FIELDS, not an axis nickname.

        The consumer tests membership by wire field name. A roster carrying
        "verification" would answer False to every field-name query, the
        consumer would read AXIS-ABSENT, and the cure would go dark with a
        passing gate and no alarm.
        """
        assert "verification" not in VERIFICATION_AXIS_FIELDS
        assert "verification_axis" not in VERIFICATION_AXIS_FIELDS

    def test_declare_axes_is_a_union_not_an_assignment(self) -> None:
        """A second roster must ADD to the first, never replace it."""
        content_roster = ("content_watermark", "content_age_seconds")

        roster = declare_axes(content_roster, VERIFICATION_AXIS_FIELDS)

        assert roster == [
            "content_watermark",
            "content_age_seconds",
            "verified_at",
            "verification_age_seconds",
            "verification_backfill_used",
        ]
        for axis in content_roster:
            assert axis in roster, "an assignment here would silently un-declare a live axis"

    def test_declare_axes_dedupes_and_preserves_order(self) -> None:
        assert declare_axes(("a", "b"), ("b", "c"), ("a",)) == ["a", "b", "c"]

    def test_declare_axes_of_nothing_is_empty(self) -> None:
        assert declare_axes((), ()) == []


class TestConsumerCoherenceContract:
    """What the SDK parser refuses. Pinned here so the producer cannot drift into it.

    The consumer does not merely read these fields — it cross-checks them, and
    every incoherence is a REFUSE. Three of its guards bite on the producer's
    emission rule directly, and two of them fail in the direction that would
    take down every production response at once. They are asserted at the wire,
    on real serialized JSON, not on the Python object.
    """

    #: Spellings that NAME the axis but are not its spelling. A roster carrying
    #: one of these while declaring none of the real three is a producer that
    #: meant to declare the axis and got the token wrong — which the consumer
    #: refuses on rather than letting it read as AXIS-ABSENT.
    _NEAR_MISS_TOKENS = (
        "verification",
        "verification_axis",
        "verification_seconds",
        "verif_age",
        "v_age",
        "verified_age_seconds",
        "last_verified_at",
        "verification_watermark",
        "verified_watermark",
    )

    async def test_derived_response_serializes_backfill_used_as_literal_false(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """The single highest-blast-radius assertion in this file.

        A null companion on a DERIVED axis is refused by the consumer. If the
        derived arm emitted null — or dropped the key — every production
        response would refuse and the cure would land dead while looking
        deployed. Asserted on serialized JSON so a serializer-level
        ``exclude_none``/``exclude_unset`` would break it too.
        """
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")
        wire = json.loads(meta.model_dump_json())

        assert "verification_backfill_used" in wire, "the key must be on the wire, not dropped"
        assert wire["verification_backfill_used"] is False, (
            "a derived axis must disclose literal false, never null"
        )
        assert wire["verified_at"] is not None
        assert wire["verification_age_seconds"] is not None

    async def test_backfill_flag_is_never_true_alongside_a_stamp(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """A reached-for value must never gate."""
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verified_at is not None
        assert meta.verification_backfill_used is False

    @pytest.mark.parametrize(
        ("manifest", "raise_on_read", "classification"),
        [
            (None, None, "active"),
            (None, RuntimeError("s3 exploded"), "active"),
            (
                _divergent_manifest(active_age=100.0, activating_age=200.0),
                None,
                "active",
            ),
        ],
        ids=["axis-null-absent", "axis-null-raised", "axis-derived"],
    )
    async def test_the_stamp_and_the_age_are_null_together_or_neither(
        self,
        offer_df: pl.DataFrame,
        offer_schema: DataFrameSchema,
        manifest: Any,
        raise_on_read: BaseException | None,
        classification: str,
    ) -> None:
        """The age is null iff the stamp is null. Any other pairing is refused."""
        engine, _ = _make_engine(offer_df, manifest=manifest, raise_on_read=raise_on_read)

        meta = await _run_rows(engine, offer_schema, classification=classification)

        assert (meta.verified_at is None) == (meta.verification_age_seconds is None)

    @pytest.mark.parametrize(
        ("manifest", "raise_on_read"),
        [
            (None, None),
            (None, RuntimeError("s3 exploded")),
            (_divergent_manifest(active_age=100.0, activating_age=200.0), None),
        ],
        ids=["axis-null-absent", "axis-null-raised", "axis-derived"],
    )
    async def test_the_roster_is_all_three_or_nothing_on_every_arm(
        self,
        offer_df: pl.DataFrame,
        offer_schema: DataFrameSchema,
        manifest: Any,
        raise_on_read: BaseException | None,
    ) -> None:
        """A strict subset is a malformed roster, not a partial capability.

        The consumer refuses a partial declaration. Every emission arm must
        therefore declare the whole axis or none of it — there is no arm where
        the producer declares two names.
        """
        engine, _ = _make_engine(offer_df, manifest=manifest, raise_on_read=raise_on_read)

        meta = await _run_rows(engine, offer_schema, classification="active")

        declared = [
            name
            for name in ("verified_at", "verification_age_seconds", "verification_backfill_used")
            if name in meta.axes_present
        ]
        assert len(declared) == 3, f"partial declaration {declared!r} is refused by the consumer"

    async def test_the_roster_carries_no_near_miss_token(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """A near-miss spelling is refused; it must never be emitted."""
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        for token in self._NEAR_MISS_TOKENS:
            assert token not in meta.axes_present

    async def test_verified_at_is_offset_bearing_iso_8601(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """``verified_at`` is the load-bearing instant: the consumer re-derives from it.

        The consumer computes its OWN ``now - verified_at`` and gates on that;
        the emitted age is disclosure. So the instant must be unambiguous — an
        offset-less string would be interpreted against the consumer's own
        assumption rather than the producer's.
        """
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verified_at is not None
        parsed = datetime.fromisoformat(meta.verified_at)
        assert parsed.tzinfo is not None, "an offset-less instant is ambiguous to the consumer"
        assert parsed.utcoffset() == timedelta(0)
        assert parsed == _NOW - timedelta(seconds=100.0)

    async def test_a_naive_manifest_stamp_never_reaches_the_wire(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """A timezone-less stamp refuses rather than emitting an ambiguous instant.

        The consumer would otherwise re-derive an age from a string whose zone
        it has to guess. Refusing is the only honest arm.
        """
        naive = datetime(2026, 8, 19, 14, 58, 20)  # noqa: DTZ001  # deliberately naive INPUT
        manifest = SectionManifest(
            project_gid=_PROJECT_GID,
            entity_type="offer",
            sections={
                f"a{i}": _section(name.upper(), last_verified_at=naive)
                for i, name in enumerate(
                    sorted(OFFER_CLASSIFIER.sections_for(AccountActivity.ACTIVE))
                )
            },
            total_sections=22,
            completed_sections=22,
            schema_version="1.6.0",
        )
        engine, _ = _make_engine(offer_df, manifest=manifest)

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verified_at is None
        assert meta.verification_age_seconds is None
        assert meta.axes_present == [
            "verified_at",
            "verification_age_seconds",
            "verification_backfill_used",
        ], "still declared: a refusal, not a silent disappearance"


class TestBothMetasDeclareTheFields:
    """Both metas are extra='forbid' and share the freshness side-channel spread.

    A field declared on one and not the other RAISES the moment the other path
    carries it. Declaring on both is what makes the aggregate path's
    AXIS-ABSENT state expressible instead of an exception.
    """

    def test_rows_meta_accepts_the_four_fields(self) -> None:
        meta = RowsMeta(
            total_count=0,
            returned_count=0,
            limit=100,
            offset=0,
            entity_type="offer",
            project_gid=_PROJECT_GID,
            query_ms=1.0,
            verified_at="2026-08-19T14:46:32.232624+00:00",
            verification_age_seconds=1132.4,
            verification_backfill_used=False,
            axes_present=list(VERIFICATION_AXIS_FIELDS),
        )

        assert meta.verification_age_seconds == pytest.approx(1132.4)
        assert meta.axes_present == list(VERIFICATION_AXIS_FIELDS)

    def test_aggregate_meta_accepts_the_four_fields(self) -> None:
        meta = AggregateMeta(
            group_count=0,
            aggregation_count=0,
            group_by=[],
            entity_type="offer",
            project_gid=_PROJECT_GID,
            query_ms=1.0,
            verified_at=None,
            verification_age_seconds=None,
            verification_backfill_used=None,
            axes_present=[],
        )

        assert meta.axes_present == []

    def test_both_default_to_axis_absent(self) -> None:
        rows = RowsMeta(
            total_count=0,
            returned_count=0,
            limit=100,
            offset=0,
            entity_type="offer",
            project_gid=_PROJECT_GID,
            query_ms=1.0,
        )
        agg = AggregateMeta(
            group_count=0,
            aggregation_count=0,
            group_by=[],
            entity_type="offer",
            project_gid=_PROJECT_GID,
            query_ms=1.0,
        )

        for meta in (rows, agg):
            assert meta.axes_present == []
            assert meta.verified_at is None
            assert meta.verification_age_seconds is None
            assert meta.verification_backfill_used is None


class TestGrainOnTheServePath:
    """The emitted axis is folded over THIS request's resolved section set."""

    @pytest.mark.parametrize(
        ("active_age", "activating_age"),
        [(5000.0, 100.0), (100.0, 5000.0)],
        ids=["variant-1-active-older", "variant-2-activating-older"],
    )
    async def test_each_classification_gets_its_own_pool(
        self,
        offer_df: pl.DataFrame,
        offer_schema: DataFrameSchema,
        active_age: float,
        activating_age: float,
    ) -> None:
        manifest = _divergent_manifest(active_age=active_age, activating_age=activating_age)

        engine, _ = _make_engine(offer_df, manifest=manifest)
        active_meta = await _run_rows(engine, offer_schema, classification="active")

        engine, _ = _make_engine(offer_df, manifest=manifest)
        activating_meta = await _run_rows(engine, offer_schema, classification="activating")

        assert active_meta.verified_at == (_NOW - timedelta(seconds=active_age)).isoformat()
        assert activating_meta.verified_at == (_NOW - timedelta(seconds=activating_age)).isoformat()
        assert active_meta.verified_at != activating_meta.verified_at

    async def test_out_of_scope_section_does_not_drag_the_axis(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """COMPLETE is stamped at 99999s and is in neither requested pool."""
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verified_at == (_NOW - timedelta(seconds=100.0)).isoformat()

    async def test_neither_fixed_pool_helper_is_called_on_the_serve_path(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """A fixed union ignores the request and breaks co-sourcing.

        ``billable_sections()`` returns the right NUMBER for the two-call
        consumer only by coincidence; on a single-classification request it
        folds over sections absent from that response's own bytes. Neither it
        nor ``active_sections()`` may be reached from the serve path.
        """
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        with (
            patch.object(
                SectionClassifier,
                "billable_sections",
                side_effect=AssertionError("billable_sections() must not be called on serve"),
            ),
            patch.object(
                SectionClassifier,
                "active_sections",
                side_effect=AssertionError("active_sections() must not be called on serve"),
            ),
        ):
            meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verified_at is not None

    async def test_whole_frame_request_scopes_to_the_manifest(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """No classification -> the frame's own section set, including COMPLETE."""
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification=None)

        assert meta.verified_at == (_NOW - timedelta(seconds=99999)).isoformat()


class TestOneManifestReadPerRequest:
    """The axis rides the read the serve path already performs.

    The memo inside SectionPersistence is written ONLY on the success branch,
    so a second derivation that re-called ``get_manifest_async`` would repeat
    the whole read on every degraded path — absent manifest, parse failure,
    raise. Threading the result makes the zero-added-GET property hold
    unconditionally rather than only on the happy path.
    """

    async def test_single_read_on_the_success_path(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        engine, get_manifest = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert get_manifest.await_count == 1
        assert meta.verified_at is not None
        assert meta.honest_contract_complete is True

    async def test_single_read_when_the_manifest_is_ABSENT(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """The negative-caching path: the memo stays empty, so a re-call would re-read."""
        engine, get_manifest = _make_engine(offer_df, manifest=None)

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert get_manifest.await_count == 1, "a second call would repeat the S3 read sequence"
        assert meta.verified_at is None
        assert meta.honest_contract_complete is False

    async def test_single_read_when_the_read_RAISES(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        engine, get_manifest = _make_engine(
            offer_df, manifest=None, raise_on_read=RuntimeError("s3 exploded")
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert get_manifest.await_count == 1
        assert meta.verified_at is None
        assert meta.honest_contract_complete is False


class TestAxisNullIsDeclaredNotDropped:
    """AXIS-NULL (declared, value null) must stay distinguishable from AXIS-ABSENT."""

    @pytest.mark.parametrize(
        ("manifest", "raise_on_read"),
        [
            (None, None),
            (None, RuntimeError("s3 exploded")),
        ],
        ids=["manifest-absent", "read-raised"],
    )
    async def test_roster_is_declared_even_when_the_axis_is_null(
        self,
        offer_df: pl.DataFrame,
        offer_schema: DataFrameSchema,
        manifest: Any,
        raise_on_read: BaseException | None,
    ) -> None:
        engine, _ = _make_engine(offer_df, manifest=manifest, raise_on_read=raise_on_read)

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.axes_present == [
            "verified_at",
            "verification_age_seconds",
            "verification_backfill_used",
        ], "an undeclared axis reads as 'old producer image', not as 'cannot derive'"
        assert meta.verified_at is None
        assert meta.verification_age_seconds is None

    async def test_roster_is_declared_when_the_derivation_itself_raises(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """The defensive catch must degrade to AXIS-NULL, never to AXIS-ABSENT.

        Dropping the roster on this path would make an internal defect read as
        "this producer image predates the axis" — the consumer would stay
        dormant and keep gating on the old signal, with nothing refusing and
        nothing to alarm on.
        """
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        with patch(_DERIVATION_TARGET, side_effect=RuntimeError("derivation exploded")):
            meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.axes_present == [
            "verified_at",
            "verification_age_seconds",
            "verification_backfill_used",
        ]
        assert meta.verified_at is None
        assert meta.verification_age_seconds is None
        assert meta.verification_backfill_used is None
        assert meta.honest_contract_complete is True, "the sibling derivation is unaffected"

    async def test_unstamped_section_sets_the_backfill_disclosure(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        manifest = SectionManifest(
            project_gid=_PROJECT_GID,
            entity_type="offer",
            sections={
                "g1": _section("ACTIVE", last_verified_at=_NOW - timedelta(seconds=100)),
                "g2": SectionInfo(
                    status=SectionStatus.COMPLETE,
                    rows=3,
                    name="STAGING",
                    written_at=_NOW,
                    last_verified_at=None,
                ),
            },
            total_sections=2,
            completed_sections=2,
            schema_version="1.6.0",
        )
        engine, _ = _make_engine(offer_df, manifest=manifest)

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verified_at is None
        assert meta.verification_age_seconds is None
        assert meta.verification_backfill_used is True

    async def test_axis_is_emitted_alongside_a_stale_content_axis(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """The two axes never coalesce: a stale cache with a fresh probe is GREEN.

        This combination — quiet business, healthy warmer — is the state the
        mutation axis can never produce and the whole reason the verification
        axis exists.

        The content axis is stamped stale (52566.7s, ratio 14.6) and the probe
        fresh (100s). Both numbers are fixture-owned, and the probe age is read
        off the same clock that stamped it, so the ordering asserted below is a
        property of the emission — not of what day the suite happens to run on.
        """
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )
        freshness = MagicMock()
        freshness.freshness = "stale"
        freshness.data_age_seconds = 52566.7
        freshness.staleness_ratio = 14.6
        object.__setattr__(engine.provider, "_last_freshness_info", freshness)

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.data_age_seconds == pytest.approx(52566.7)
        assert meta.stale_served is True
        assert meta.verified_at is not None
        assert meta.verification_age_seconds is not None
        # The probe carries the age the fixture stamped, not a wall-clock drift.
        assert meta.verification_age_seconds == pytest.approx(100.0)
        # The load-bearing discrimination: the two axes did not coalesce.
        assert meta.verification_age_seconds < meta.data_age_seconds


class TestTheFixtureClockIsTheDerivationClock:
    """Anti-rot tripwire for the #384 landmine. See the module docstring.

    These do not test the axis. They test that this FILE cannot rot the way it
    rotted once: they fail the moment the emitted age stops being measured
    against ``_NOW``, which is the only condition under which a fixture-relative
    assertion elsewhere in this file can start drifting with the calendar.

    Without the freeze the ages below are ``wall_clock - _NOW + age``. At the
    moment #384 landed that was ~0 and every assertion passed; three days later
    it was 226129.9 and the suite failed repo-wide. A tripwire that only bites
    after the damage is not a tripwire — so these assert the exact value, which
    is wrong immediately rather than eventually.
    """

    @pytest.mark.parametrize("age", [100.0, 5000.0, 99999.0])
    async def test_the_emitted_age_is_measured_against_the_frozen_clock(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema, age: float
    ) -> None:
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=age, activating_age=age + 1.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verification_age_seconds == pytest.approx(age), (
            "the derivation is reading a clock this file does not control — "
            "a fixture-relative age has become a wall-clock age and every "
            "bounded assertion in this file is now on a countdown"
        )

    async def test_the_stamp_and_the_age_agree_on_the_same_instant(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        """``now - verified_at`` must reproduce the emitted age exactly.

        The consumer re-derives its own age from ``verified_at`` and gates on
        that. If the producer's age were measured against a different instant
        than the one it discloses, the two would disagree in production and the
        disclosure would be a lie — invisible to every other test here, all of
        which check the two fields independently.
        """
        engine, _ = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.verified_at is not None
        assert meta.verification_age_seconds is not None
        re_derived = (_NOW - datetime.fromisoformat(meta.verified_at)).total_seconds()
        assert meta.verification_age_seconds == pytest.approx(re_derived)


class TestAggregatePathDeclaresNothing:
    """execute_aggregate reads no manifest, so it must not claim the axis."""

    async def test_aggregate_meta_is_axis_absent(
        self, offer_df: pl.DataFrame, offer_schema: DataFrameSchema
    ) -> None:
        engine, get_manifest = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )
        request = AggregateRequest.model_validate(
            {
                "group_by": ["section"],
                "aggregations": [{"column": "gid", "agg": "count", "alias": "n"}],
            }
        )

        with patch("autom8_asana.query.engine.SchemaRegistry") as registry_cls:
            registry = MagicMock()
            registry.get_schema.return_value = offer_schema
            registry_cls.get_instance.return_value = registry
            result = await engine.execute_aggregate(
                entity_type="offer",
                project_gid=_PROJECT_GID,
                client=AsyncMock(),
                request=request,
            )

        assert result.meta.axes_present == []
        assert result.meta.verified_at is None
        assert result.meta.verification_age_seconds is None
        assert get_manifest.await_count == 0


class TestFieldsAreNotRoutedThroughTheFreshnessSideChannel:
    """The freshness side-channel has no manifest access and is shared with aggregate.

    Routing the axis through it would either force a manifest read into the
    aggregate path or emit nulls on a path that never declares the axis — which
    the consumer would read as AXIS-NULL and refuse on.
    """

    def test_freshness_meta_carries_no_verification_key(self, offer_df: pl.DataFrame) -> None:
        service = EntityQueryService()
        freshness = MagicMock()
        freshness.freshness = "fresh"
        freshness.data_age_seconds = 12.0
        freshness.staleness_ratio = 0.1
        object.__setattr__(service, "_last_freshness_info", freshness)
        engine = QueryEngine(provider=service)

        meta = engine._get_freshness_meta()

        for field_name in (*VERIFICATION_AXIS_FIELDS, "axes_present"):
            assert field_name not in meta


class TestHonestContractCompleteIsUnchanged:
    """The 503-driving boolean must keep its exact value through the refactor."""

    @pytest.mark.parametrize(
        ("statuses", "expected"),
        [
            ([SectionStatus.COMPLETE, SectionStatus.COMPLETE], True),
            ([SectionStatus.COMPLETE, SectionStatus.FAILED], False),
            ([SectionStatus.IN_PROGRESS, SectionStatus.COMPLETE], False),
        ],
        ids=["all-complete", "one-failed", "one-in-progress"],
    )
    async def test_value_matches_the_manifest(
        self,
        offer_df: pl.DataFrame,
        offer_schema: DataFrameSchema,
        statuses: list[SectionStatus],
        expected: bool,
    ) -> None:
        manifest = SectionManifest(
            project_gid=_PROJECT_GID,
            entity_type="offer",
            sections={
                f"g{i}": SectionInfo(
                    status=status,
                    rows=3,
                    name=name,
                    last_verified_at=_NOW - timedelta(seconds=100),
                )
                for i, (status, name) in enumerate(
                    zip(statuses, ("ACTIVE", "STAGING"), strict=True)
                )
            },
            total_sections=len(statuses),
            completed_sections=sum(s == SectionStatus.COMPLETE for s in statuses),
            schema_version="1.6.0",
        )
        engine, _ = _make_engine(offer_df, manifest=manifest)

        meta = await _run_rows(engine, offer_schema, classification="active")

        assert meta.honest_contract_complete is expected

    async def test_standalone_call_still_performs_its_own_read(
        self, offer_df: pl.DataFrame
    ) -> None:
        """Callers outside execute_rows keep the pre-existing contract."""
        engine, get_manifest = _make_engine(
            offer_df, manifest=_divergent_manifest(active_age=100.0, activating_age=200.0)
        )

        result = await engine._derive_honest_contract_complete(_PROJECT_GID, "offer")

        assert result is True
        assert get_manifest.await_count == 1
