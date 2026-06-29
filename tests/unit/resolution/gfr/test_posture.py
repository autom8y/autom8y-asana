"""Tests for the GFR posture/provenance layer (TDD §6.2, §9.3 posture.py row).

Covers stale=resolved (INVARIANT I4), serve-stale derivation from the RowsMeta
freshness side-channel, provenance round-trip {value,status,source,as_of}
(INVARIANT I7), and the empty-frame all-or-nothing failure (INVARIANT I4).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from autom8_asana.query.models import RowsMeta
from autom8_asana.resolution.gfr.errors import UnresolvedError
from autom8_asana.resolution.gfr.models import FieldStatus, TruthTier
from autom8_asana.resolution.gfr.posture import assemble_rows, derive_status

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]


def _meta(*, stale_served: bool = False, freshness: str | None = "fresh") -> RowsMeta:
    return RowsMeta(
        total_count=1,
        returned_count=1,
        limit=100,
        offset=0,
        entity_type="business",
        project_gid="1200653012566782",
        query_ms=1.0,
        freshness=freshness,
        stale_served=stale_served,
    )


class TestDeriveStatus:
    def test_fresh_when_not_stale(self) -> None:
        assert derive_status(_meta(stale_served=False, freshness="fresh")) is FieldStatus.FRESH

    def test_stale_served_flag_maps_to_stale(self) -> None:
        assert derive_status(_meta(stale_served=True, freshness="fresh")) is FieldStatus.STALE

    def test_stale_freshness_string_maps_to_stale(self) -> None:
        assert derive_status(_meta(stale_served=False, freshness="stale")) is FieldStatus.STALE

    def test_lkg_freshness_maps_to_stale(self) -> None:
        assert derive_status(_meta(stale_served=False, freshness="lkg")) is FieldStatus.STALE

    def test_none_freshness_defaults_fresh(self) -> None:
        assert derive_status(_meta(stale_served=False, freshness=None)) is FieldStatus.FRESH


class TestAssembleRows:
    def test_provenance_round_trips(self) -> None:
        as_of = datetime.now(UTC)
        result = assemble_rows(
            gid="O",
            fields=["company_id"],
            data=[{"company_id": "G_A", "gid": "B"}],
            meta=_meta(),
            source=TruthTier.CACHE,
            as_of=as_of,
        )
        assert result.row_count == 1
        fwp = result.rows[0]["company_id"]
        assert fwp.value == "G_A"
        assert fwp.status is FieldStatus.FRESH
        assert fwp.source is TruthTier.CACHE
        assert fwp.as_of == as_of

    def test_stale_present_value_is_resolved(self) -> None:
        # INVARIANT I4: stale-but-present counts as RESOLVED, status=stale.
        result = assemble_rows(
            gid="O",
            fields=["company_id"],
            data=[{"company_id": "G_A"}],
            meta=_meta(stale_served=True),
            source=TruthTier.CACHE,
            as_of=None,
        )
        assert result.rows[0]["company_id"].status is FieldStatus.STALE
        assert result.rows[0]["company_id"].value == "G_A"

    def test_empty_frame_raises_all_or_nothing(self) -> None:
        with pytest.raises(UnresolvedError) as exc:
            assemble_rows(
                gid="O",
                fields=["company_id"],
                data=[],
                meta=_meta(),
                source=TruthTier.CACHE,
                as_of=None,
            )
        assert exc.value.reason == "empty-frame"
        assert exc.value.fields == ["company_id"]

    def test_row_set_native_multiple_rows(self) -> None:
        # INVARIANT I5: 1..N rows preserved, never collapsed.
        result = assemble_rows(
            gid="O",
            fields=["company_id"],
            data=[{"company_id": "A"}, {"company_id": "B"}],
            meta=_meta(),
            source=TruthTier.CACHE,
            as_of=None,
        )
        assert result.row_count == 2
        assert [r["company_id"].value for r in result.rows] == ["A", "B"]

    def test_verified_source_stamped(self) -> None:
        result = assemble_rows(
            gid="O",
            fields=["company_id"],
            data=[{"company_id": "G_A"}],
            meta=_meta(),
            source=TruthTier.VERIFIED,
            as_of=None,
        )
        assert result.rows[0]["company_id"].source is TruthTier.VERIFIED
