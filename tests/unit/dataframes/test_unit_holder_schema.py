"""Contract tests for UNIT_HOLDER_SCHEMA (WS-B PR-1).

DIAG-ws-b-offer-frame-collapse-2026-08-05: the scheduling-posture producer could
not reach the posture through the OFFER frame because the ancestor walk that
delivers ``cascade:`` values terminates at depth 1 -- hops 3 (UnitHolder) and 4
(Business) are never visited. Measured on the live offer frame:
``custom_cal_status`` 2/4191 non-null (0.05%), the eight provider columns 0/4191.

The cure gives UnitHolder a frame of its OWN whose posture columns are sourced
``cf:`` off the UnitHolder's own manifest -- zero ancestor traversal.

These tests are the SOURCE-LEVEL guard. The single most dangerous regression is a
silent revert to the OFFER_SCHEMA 1.5.0 defect class: a column that LOOKS wired
but resolves null on every row because it is sourced at the wrong LEVEL
(``cascade:`` instead of ``cf:``) or under the wrong NAME (snake_case instead of
the exact live Asana Title Case display name). Both produce a schema that
type-checks, builds, and pushes a fully degenerate frame.
"""

from __future__ import annotations

import pytest

from autom8_asana.dataframes.schemas.base import BASE_COLUMNS
from autom8_asana.dataframes.schemas.unit_holder import (
    UNIT_HOLDER_COLUMNS,
    UNIT_HOLDER_SCHEMA,
)
from autom8_asana.models.business.unit import UnitHolder

# The nine posture columns: DataFrame column name -> EXACT live Asana display name.
# Verified live (DIAG R-7) on two independent ACTIVE offices' UnitHolder tasks.
EXPECTED_POSTURE_SOURCES: dict[str, str] = {
    "custom_cal_status": "Custom Cal Status",
    "reviewwave_id": "ReviewWave ID",
    "acuity_cal_url": "Acuity Cal URL",
    "calendly_url": "Calendly URL",
    "janeapp_url": "JaneApp URL",
    "ehr_cal_url": "EHR Cal URL",
    "trackstat_id": "TrackStat ID",
    "sked_id": "Sked ID",
    "custom_ghl_id": "Custom GHL ID",
}


class TestUnitHolderSchemaShape:
    """Structural contract of the frame the producer will read."""

    def test_declares_exactly_nine_posture_columns(self) -> None:
        assert len(UNIT_HOLDER_COLUMNS) == 9
        assert {c.name for c in UNIT_HOLDER_COLUMNS} == set(EXPECTED_POSTURE_SOURCES)

    def test_column_count_is_base_plus_nine(self) -> None:
        assert len(UNIT_HOLDER_SCHEMA.columns) == len(BASE_COLUMNS) + 9

    def test_task_type_matches_registry_pascal_name(self) -> None:
        assert UNIT_HOLDER_SCHEMA.task_type == "UnitHolder"
        assert UNIT_HOLDER_SCHEMA.name == "unit_holder"

    def test_parent_gid_join_key_present_and_not_redeclared(self) -> None:
        """parent_gid (the join key onto business.gid) rides BASE_COLUMNS.

        The producer joins unit_holder.parent_gid -> business.gid; measured
        2082/2082 = 100.0% complete on today's frames.
        """
        names = [c.name for c in UNIT_HOLDER_SCHEMA.columns]
        assert names.count("parent_gid") == 1
        assert "parent_gid" not in {c.name for c in UNIT_HOLDER_COLUMNS}

    def test_company_id_is_absent(self) -> None:
        """company_id lives on the BUSINESS ancestor, not on UnitHolder.

        DIAG R-7: the UnitHolder task carries ``Company ID=None``. Declaring it
        here would resolve null on every row and reintroduce the 1.5.0 defect.
        """
        assert "company_id" not in {c.name for c in UNIT_HOLDER_SCHEMA.columns}

    def test_all_posture_columns_are_nullable(self) -> None:
        """An office genuinely lacking a field reads null -> normalizer treats
        it as absent -> fail-safe to GHL by absence."""
        for col in UNIT_HOLDER_COLUMNS:
            assert col.nullable is True, f"{col.name} must be nullable"

    def test_all_posture_columns_are_utf8(self) -> None:
        for col in UNIT_HOLDER_COLUMNS:
            assert col.dtype == "Utf8", f"{col.name} must be Utf8"


class TestUnitHolderSchemaSourceLevel:
    """The 1.5.0 defect class: right column, wrong source level or name."""

    @pytest.mark.parametrize(
        ("column_name", "asana_display_name"),
        sorted(EXPECTED_POSTURE_SOURCES.items()),
        ids=sorted(EXPECTED_POSTURE_SOURCES),
    )
    def test_posture_column_sourced_cf_with_exact_display_name(
        self, column_name: str, asana_display_name: str
    ) -> None:
        """Each posture column is ``cf:<exact Title Case display name>``."""
        col = next(c for c in UNIT_HOLDER_COLUMNS if c.name == column_name)
        assert col.source == f"cf:{asana_display_name}"

    def test_no_posture_column_is_sourced_cascade(self) -> None:
        """RED-guard for the ancestor-walk dependency this PR exists to escape.

        A ``cascade:`` source here would route the value back through the
        depth-1 ancestor walk -- i.e. reproduce the exact darkness measured on
        the offer frame (0/4191 on eight of nine columns).
        """
        cascade_sourced = [
            c.name for c in UNIT_HOLDER_COLUMNS if (c.source or "").startswith("cascade:")
        ]
        assert not cascade_sourced, (
            "UnitHolder posture columns must be cf: (own manifest), never "
            f"cascade: (ancestor walk). Offenders: {cascade_sourced}"
        )

    def test_schema_declares_zero_cascade_columns(self) -> None:
        """Whole-schema form: unit_holder is a cascade PROVIDER, not a consumer.

        This is what keeps it free of frame-warm ordering constraints of its own
        (``get_frame_warm_providers("unit_holder") == set()``).
        """
        assert UNIT_HOLDER_SCHEMA.get_cascade_columns() == []

    def test_display_names_match_the_model_cascading_field_defs(self) -> None:
        """Cross-check against UnitHolder.CascadingFields, the in-tree authority.

        Guards against a rename drifting the two apart: the custom-field match is
        lower()/strip(), so a snake_case or reworded name matches NOTHING and the
        column silently resolves null on every row.
        """
        model_names = {fd.name for fd in UnitHolder.CascadingFields.all()}
        schema_names = {(c.source or "").removeprefix("cf:") for c in UNIT_HOLDER_COLUMNS}
        assert schema_names == model_names

    def test_no_snake_case_source_names(self) -> None:
        """The literal 1.5.0 defect: snake_case names matched nothing."""
        offenders = [
            c.name for c in UNIT_HOLDER_COLUMNS if "_" in (c.source or "").removeprefix("cf:")
        ]
        assert not offenders, f"snake_case custom-field names match nothing in Asana: {offenders}"
