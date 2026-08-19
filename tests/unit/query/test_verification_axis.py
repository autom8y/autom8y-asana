"""Wire-level tests for the verification axis on the /rows serve path.

Covers what the derivation-level suite cannot: the axis actually reaching the
response meta, at the request-resolved grain, declared in the capability roster,
without adding an S3 read and without disturbing ``honest_contract_complete``.

The capability-roster literals are spelled out here rather than imported. A test
that imports the constant it is checking cannot catch a rename — and a rename is
exactly the failure this axis is most exposed to, because the consumer matches by
wire field name and a mismatch is silently inert.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.models.schema import ColumnDef, DataFrameSchema
from autom8_asana.dataframes.section_persistence import (
    SectionInfo,
    SectionManifest,
    SectionStatus,
)
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

_NOW = datetime(2026, 8, 19, 15, 0, 0, tzinfo=UTC)
_PROJECT_GID = "1143843662099250"


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

        with patch(
            "autom8_asana.metrics.freshness.compute_serve_verification",
            side_effect=RuntimeError("derivation exploded"),
        ):
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
        assert meta.verification_age_seconds < meta.data_age_seconds


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
