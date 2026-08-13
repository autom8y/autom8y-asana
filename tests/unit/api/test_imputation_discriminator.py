"""Limb (iii): the imputed-vs-observed discriminator reaches the wire and a
consumer branches on it.

FINDING-option-g-imputation-indistinguishable-2026-08-12: today
``OfferTimelineEntry`` is seven scalars under ``extra="forbid"`` and
``story_count`` is dropped at the response boundary, so a 100%-imputed payload
is byte-identical to a 0%-imputed one. This module proves:

  1. ``story_count`` and the computed ``imputed`` flag now reach the serialized
     wire (the discriminator is present on the consumable surface).
  2. An imputed entry and an observed entry that are otherwise identical are now
     DISTINGUISHABLE in the payload (the negative "unmeasurable from the
     payload" no longer holds for this contract).
  3. A consumer (``summarize_imputation``) demonstrably BRANCHES on the
     discriminator — flipping a single entry's imputation changes its output,
     which a non-branching consumer could not do.
  4. The reported rate is labeled INFERRED, never measured.
  5. The branch runs on the LIVE endpoint path, not as dead code.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from autom8_asana.api.dependencies import AsanaClientDualMode, RequestId
from autom8_asana.api.routes.section_timelines import (
    SectionTimelinesResponse,
    router,
    summarize_imputation,
)
from autom8_asana.client import AsanaClient
from autom8_asana.models.business.section_timeline import (
    ImputationSummary,
    OfferTimelineEntry,
)


def _entry(offer_gid: str, story_count: int) -> OfferTimelineEntry:
    """An entry identical in every scalar except story_count (the discriminator)."""
    return OfferTimelineEntry(
        offer_gid=offer_gid,
        office_phone="+15550001000",
        offer_id="OFR-001",
        active_section_days=18,
        billable_section_days=22,
        current_section="ACTIVE",
        current_classification="active",
        story_count=story_count,
    )


# ---------------------------------------------------------------------------
# 1 + 2: the discriminator reaches the wire and makes imputed distinguishable
# ---------------------------------------------------------------------------


class TestDiscriminatorOnTheWire:
    def test_imputed_flag_computed_from_story_count(self) -> None:
        assert _entry("a", story_count=0).imputed is True
        assert _entry("b", story_count=5).imputed is False

    def test_story_count_and_imputed_serialize(self) -> None:
        """Both reach model_dump() and model_dump_json() (the wire)."""
        data = _entry("a", story_count=0).model_dump()
        assert data["story_count"] == 0
        assert data["imputed"] is True

        raw = _entry("b", story_count=5).model_dump_json()
        assert '"story_count":5' in raw
        assert '"imputed":false' in raw

    def test_imputed_and_observed_now_distinguishable(self) -> None:
        """Refutes the negative: two entries identical in the seven original
        scalars but differing in imputation are now distinct on the wire."""
        imputed = _entry("same", story_count=0).model_dump()
        observed = _entry("same", story_count=5).model_dump()

        # Identical in every field the payload carried BEFORE this sprint...
        seven_original = (
            "offer_gid",
            "office_phone",
            "offer_id",
            "active_section_days",
            "billable_section_days",
            "current_section",
            "current_classification",
        )
        for field in seven_original:
            assert imputed[field] == observed[field]

        # ...yet now distinguishable via the discriminator.
        assert imputed["imputed"] != observed["imputed"]
        assert imputed["story_count"] != observed["story_count"]


# ---------------------------------------------------------------------------
# 3 + 4: a consumer branches on the discriminator; the rate is INFERRED
# ---------------------------------------------------------------------------


class TestConsumerBranchesOnDiscriminator:
    def test_all_imputed(self) -> None:
        summary = summarize_imputation([_entry(f"i{n}", 0) for n in range(3)])
        assert summary.imputed_offers == 3
        assert summary.observed_offers == 0
        assert summary.inferred_imputation_rate == 1.0

    def test_all_observed(self) -> None:
        summary = summarize_imputation([_entry(f"o{n}", 5) for n in range(4)])
        assert summary.imputed_offers == 0
        assert summary.observed_offers == 4
        assert summary.inferred_imputation_rate == 0.0

    def test_mixed_partition(self) -> None:
        entries = [_entry("i", 0), _entry("o1", 5), _entry("o2", 2), _entry("i2", 0)]
        summary = summarize_imputation(entries)
        assert summary.total_offers == 4
        assert summary.imputed_offers == 2
        assert summary.observed_offers == 2
        assert summary.inferred_imputation_rate == 0.5

    def test_empty(self) -> None:
        summary = summarize_imputation([])
        assert summary.total_offers == 0
        assert summary.inferred_imputation_rate == 0.0

    def test_branch_flips_readout(self) -> None:
        """Show the branch: flipping ONE entry's imputation changes the summary.

        A consumer that ignored the discriminator would produce identical output
        for a fully-observed and a partly-imputed set. This one does not.
        """
        all_observed = [_entry("x", 5), _entry("y", 5)]
        one_imputed = [_entry("x", 0), _entry("y", 5)]  # single flip: 5 -> 0

        before = summarize_imputation(all_observed)
        after = summarize_imputation(one_imputed)

        assert before.inferred_imputation_rate == 0.0
        assert after.inferred_imputation_rate == 0.5
        assert before.imputed_offers != after.imputed_offers

    def test_rate_is_labeled_inferred_not_measured(self) -> None:
        """Exit criterion 5: the rate is reported as INFERRED, never measured."""
        summary = summarize_imputation([_entry("i", 0)])
        assert summary.basis == "inferred-from-story-cache-warmth"
        # The field name itself carries the inference caveat.
        assert (
            "inferred" in type(summary).model_fields["inferred_imputation_rate"].description.lower()
        )
        # And there is no field claiming a measured/live value.
        assert "measured_imputation_rate" not in type(summary).model_fields


# ---------------------------------------------------------------------------
# 5: the branch runs on the LIVE endpoint path (not dead code)
# ---------------------------------------------------------------------------


def _create_test_app() -> FastAPI:
    app = FastAPI()
    mock_client = MagicMock(spec=AsanaClient)

    async def override_client() -> AsanaClient:
        return mock_client

    async def override_request_id() -> str:
        return "test-request-id"

    app.dependency_overrides[AsanaClientDualMode.__metadata__[0].dependency] = override_client  # type: ignore[index]
    app.dependency_overrides[RequestId.__metadata__[0].dependency] = override_request_id  # type: ignore[index]
    app.include_router(router)
    return app


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(_create_test_app())


class TestImputationSummaryOnLivePath:
    def test_endpoint_emits_imputation_block(self, test_client: TestClient) -> None:
        """The endpoint populates the imputation summary by branching on entries."""
        entries = [_entry("i", 0), _entry("o1", 5), _entry("o2", 3)]
        with patch(
            "autom8_asana.api.routes.section_timelines.get_or_compute_timelines",
            new_callable=AsyncMock,
            return_value=entries,
        ):
            response = test_client.get(
                "/api/v1/offers/section-timelines",
                params={"period_start": "2025-01-01", "period_end": "2025-01-31"},
            )

        assert response.status_code == 200
        data = response.json()["data"]

        # Per-entry discriminator on the wire.
        by_gid = {t["offer_gid"]: t for t in data["timelines"]}
        assert by_gid["i"]["imputed"] is True
        assert by_gid["o1"]["imputed"] is False

        # Response-level summary, produced by the branching consumer.
        imputation = data["imputation"]
        assert imputation["total_offers"] == 3
        assert imputation["imputed_offers"] == 1
        assert imputation["observed_offers"] == 2
        assert imputation["inferred_imputation_rate"] == pytest.approx(1 / 3)
        assert imputation["basis"] == "inferred-from-story-cache-warmth"

    def test_envelope_requires_imputation(self) -> None:
        """The envelope contract carries the summary (not optional)."""
        assert "imputation" in SectionTimelinesResponse.model_fields
        assert SectionTimelinesResponse.model_fields["imputation"].is_required()
        assert SectionTimelinesResponse.model_fields["imputation"].annotation is ImputationSummary
