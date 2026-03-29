"""Shared fixtures for reconciliation tests.

Per REVIEW-reconciliation-deep-audit TC-9 / P0-C:
ALL DataFrame fixtures use the canonical "section" column name from
schemas/base.py:84. ZERO instances of "section_name" in column definitions.

The "section_name" column was a processor-local misnomer that masked
production failures. Production DataFrames always carry "section".
"""

from __future__ import annotations

import polars as pl
import pytest


@pytest.fixture
def make_unit_df():
    """Factory fixture for unit DataFrames with canonical column names.

    Returns a callable that creates unit DataFrames with the "section"
    column (NOT "section_name") matching production DataFrame shape.
    """

    def _make_unit_df(
        *,
        gids: list[str] | None = None,
        sections: list[str | None] | None = None,
        section_gids: list[str | None] | None = None,
        phones: list[str | None] | None = None,
        verticals: list[str | None] | None = None,
    ) -> pl.DataFrame:
        n = len(gids) if gids else 1
        data: dict[str, list] = {
            "gid": gids or [f"unit_{i}" for i in range(n)],
            # P0-C: Canonical "section" column (NOT "section_name")
            "section": sections if sections is not None else ["Active"] * n,
            "office_phone": phones if phones is not None else ["+15551234567"] * n,
            "vertical": verticals if verticals is not None else ["dental"] * n,
        }
        if section_gids is not None:
            data["section_gid"] = section_gids
        return pl.DataFrame(data)

    return _make_unit_df


@pytest.fixture
def make_offer_df():
    """Factory fixture for offer DataFrames with canonical column names.

    Returns a callable that creates offer DataFrames with the "section"
    column (NOT "section_name") matching production DataFrame shape.
    """

    def _make_offer_df(
        *,
        gids: list[str] | None = None,
        sections: list[str | None] | None = None,
        phones: list[str | None] | None = None,
        verticals: list[str | None] | None = None,
    ) -> pl.DataFrame:
        n = len(gids) if gids else 1
        data: dict[str, list] = {
            "gid": gids or [f"offer_{i}" for i in range(n)],
            # P0-C: Canonical "section" column (NOT "section_name")
            "section": sections if sections is not None else ["ACTIVE"] * n,
            "office_phone": phones if phones is not None else ["+15551234567"] * n,
            "vertical": verticals if verticals is not None else ["dental"] * n,
        }
        return pl.DataFrame(data)

    return _make_offer_df


@pytest.fixture
def make_pipeline_summary_df():
    """Factory fixture for pipeline summary DataFrames.

    Returns a callable that creates pipeline summary DataFrames matching
    the output shape of pipeline_stage_aggregator._aggregate_pipeline_stages.
    """

    def _make_pipeline_summary_df(
        *,
        phones: list[str] | None = None,
        verticals: list[str] | None = None,
        process_types: list[str] | None = None,
        process_sections: list[str] | None = None,
    ) -> pl.DataFrame:
        n = len(phones) if phones else 1
        return pl.DataFrame({
            "office_phone": phones or ["+15551234567"] * n,
            "vertical": verticals or ["dental"] * n,
            "latest_process_type": process_types or ["onboarding"] * n,
            "latest_process_section": process_sections or ["ACTIVE"] * n,
        })

    return _make_pipeline_summary_df


@pytest.fixture
def sample_unit_df(make_unit_df):
    """Pre-built unit DataFrame with 3 rows for basic tests."""
    return make_unit_df(
        gids=["unit_1", "unit_2", "unit_3"],
        sections=["Active", "Onboarding", "Templates"],
        phones=["+15551111111", "+15552222222", "+15553333333"],
        verticals=["dental", "chiropractic", "dental"],
    )


@pytest.fixture
def sample_offer_df(make_offer_df):
    """Pre-built offer DataFrame with 2 rows for basic tests."""
    return make_offer_df(
        gids=["offer_1", "offer_2"],
        sections=["ACTIVE", "STAGING"],
        phones=["+15551111111", "+15552222222"],
        verticals=["dental", "chiropractic"],
    )
