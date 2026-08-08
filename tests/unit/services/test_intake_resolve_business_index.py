"""Discriminating fixtures for the business resolve path.

Every fixture here builds a REAL ``DynamicIndex.from_dataframe`` and seeds the
REAL shared ``DynamicIndexCache``. Nothing re-implements the key format -- a
local re-implementation of the key can only ever assert that the test agrees
with itself, which is how the pre-cure oracle passed while the production key
was structurally dead.

Coverage (HANDOFF §5 / ADR-resolve-cure-design-2026-08-08 BE-1..BE-5):

(a) vertical-mismatch misses           -- the pre-cure structural miss
(b) null-vertical rows absent          -- nothing indexes as ""
(c) office_phone-keyed business hits   -- the cured key
A-1 wrong-entity                       -- a unit-warmed instance must not yield
                                          a business, and a unit TASK must not
                                          be returned as a business of record
A-2 discriminator (two-sided)          -- ABSENT is 200 found=false, UNAVAILABLE
                                          is a raised fail-closed error; the ONLY
                                          difference between the arms is whether
                                          the index could be consulted
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

# NOTE: `autom8_asana.api` must be imported before
# `autom8_asana.services.intake_resolve_service` -- the service module imports
# its response models from `api.routes`, and `api.routes.intake_create` imports
# back from the service. Importing the service FIRST hits the half-initialised
# module. Pre-existing structural coupling; not introduced by this cure.
from autom8_asana.api.routes.intake_resolve_models import BusinessResolveResponse
from autom8_asana.core.entity_registry import get_registry
from autom8_asana.services.dynamic_index import DynamicIndex
from autom8_asana.services.intake_resolve_service import (
    BusinessIndexUnavailableError,
    BusinessVerificationError,
    IntakeResolveService,
    resolve_gid_from_index,
)
from autom8_asana.services.universal_strategy import (
    get_shared_index_cache,
    reset_shared_index_cache,
)

OFFICE_PHONE = "+18433570125"
UNSEEDED_PHONE = "+15550000001"
BUSINESS_GID = "1200000000000001"
UNIT_GID = "1201000000000002"
LIVE_VERTICAL = "chiropractic"


# ---------------------------------------------------------------------------
# Registry-sourced constants (never a literal in the assertions)
# ---------------------------------------------------------------------------


def _business_project_gid() -> str:
    gid = get_registry().require("business").primary_project_gid
    assert gid is not None
    return gid


def _unit_project_gid() -> str:
    gid = get_registry().require("unit").primary_project_gid
    assert gid is not None
    return gid


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_index_cache():
    reset_shared_index_cache()
    yield
    reset_shared_index_cache()


def _business_frame(vertical: str | None = LIVE_VERTICAL) -> pl.DataFrame:
    """A business frame. `vertical` is carried only so the (a)/(b) fixtures can
    exercise the pre-cure two-column key against real data."""
    return pl.DataFrame(
        {
            "office_phone": [OFFICE_PHONE],
            "vertical": pl.Series([vertical], dtype=pl.Utf8),
            "gid": [BUSINESS_GID],
        }
    )


def _unit_frame(vertical: str | None = LIVE_VERTICAL) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "office_phone": [OFFICE_PHONE],
            "vertical": pl.Series([vertical], dtype=pl.Utf8),
            "gid": [UNIT_GID],
        }
    )


def _unseeded_unit_frame() -> pl.DataFrame:
    """A unit row for a phone the BUSINESS index does not carry -- so a business
    lookup misses and any post-lookup fallback would hit."""
    return pl.DataFrame(
        {
            "office_phone": [UNSEEDED_PHONE],
            "vertical": pl.Series([LIVE_VERTICAL], dtype=pl.Utf8),
            "gid": [UNIT_GID],
        }
    )


def _warm(entity_type: str, key_columns: list[str], df: pl.DataFrame) -> DynamicIndex:
    index = DynamicIndex.from_dataframe(df=df, key_columns=key_columns, value_column="gid")
    get_shared_index_cache().put(entity_type, key_columns, index)
    return index


def _task(gid: str, project_gid: str, name: str = "Real Office") -> dict[str, Any]:
    return {
        "gid": gid,
        "name": name,
        "custom_fields": [{"name": "company_id", "text_value": "guid-1", "gid": "cf_1"}],
        "memberships": [{"project": {"gid": project_gid, "name": "Project"}}],
    }


def _client(task_data: dict[str, Any] | Exception) -> MagicMock:
    client = MagicMock()
    if isinstance(task_data, Exception):
        client.tasks.get_async = AsyncMock(side_effect=task_data)
    else:
        client.tasks.get_async = AsyncMock(return_value=task_data)
    subtasks = MagicMock()
    subtasks.collect = AsyncMock(return_value=[])
    client.tasks.subtasks_async = MagicMock(return_value=subtasks)
    return client


# ---------------------------------------------------------------------------
# (c) the cured key: business index keyed on office_phone alone HITS
# ---------------------------------------------------------------------------


class TestOfficePhoneKeyedBusinessIndex:
    def test_office_phone_keyed_business_index_hits(self) -> None:
        """(c) A business index keyed on office_phone alone is HIT by the probe."""
        _warm("business", ["office_phone"], _business_frame())

        assert resolve_gid_from_index(OFFICE_PHONE) == BUSINESS_GID

    def test_unseeded_phone_misses_a_warm_index(self) -> None:
        """A warm index with a different phone is a genuine key miss, not an error."""
        _warm("business", ["office_phone"], _business_frame())

        assert resolve_gid_from_index(UNSEEDED_PHONE) is None

    def test_probe_key_matches_the_registry_not_a_literal(self) -> None:
        """The probe's key columns come from the registry descriptor.

        This is the defect being cured: a hardcoded key list that silently
        diverged from the registry produced a permanent structural miss.
        """
        registry_key = list(get_registry().require("business").key_columns)
        _warm("business", registry_key, _business_frame())

        assert resolve_gid_from_index(OFFICE_PHONE) == BUSINESS_GID

    def test_registry_drift_fails_closed(self) -> None:
        """If the registry keys business on something this surface cannot supply,
        refuse LOUDLY rather than issue a structurally-doomed lookup."""
        drifted = MagicMock()
        drifted.key_columns = ("office_phone", "vertical")

        registry = MagicMock()
        registry.require.return_value = drifted

        with (
            patch("autom8_asana.core.entity_registry.get_registry", return_value=registry),
            pytest.raises(BusinessIndexUnavailableError) as exc,
        ):
            resolve_gid_from_index(OFFICE_PHONE)

        assert "office_phone" in str(exc.value)


# ---------------------------------------------------------------------------
# (a) + (b) the pre-cure structural miss, proven against real index data
# ---------------------------------------------------------------------------


class TestPreCureStructuralMiss:
    def test_vertical_mismatch_misses(self) -> None:
        """(a) A two-column index warmed with a real vertical cannot be hit by a
        probe that sends vertical="" -- the pre-cure query shape."""
        index = _warm("unit", ["office_phone", "vertical"], _unit_frame(LIVE_VERTICAL))

        assert index.lookup({"office_phone": OFFICE_PHONE, "vertical": LIVE_VERTICAL}) == [UNIT_GID]
        assert index.lookup({"office_phone": OFFICE_PHONE, "vertical": ""}) == []

    def test_null_vertical_rows_are_absent_from_the_index(self) -> None:
        """(b) Rows with a null vertical are DROPPED from a vertical-keyed index.

        So nothing indexes as "" -- an unset vertical is not reachable by ANY
        vertical value, empty string included.
        """
        two_col = DynamicIndex.from_dataframe(
            df=_unit_frame(None), key_columns=["office_phone", "vertical"], value_column="gid"
        )

        assert two_col.entry_count == 0
        assert two_col.lookup({"office_phone": OFFICE_PHONE, "vertical": ""}) == []

        # ...while the SAME row is present in an office_phone-keyed index. This
        # is the whole cure in one assertion pair.
        one_col = DynamicIndex.from_dataframe(
            df=_unit_frame(None), key_columns=["office_phone"], value_column="gid"
        )
        assert one_col.lookup({"office_phone": OFFICE_PHONE}) == [UNIT_GID]


# ---------------------------------------------------------------------------
# A-1 wrong-entity: no unit fallback, and a positive business assertion
# ---------------------------------------------------------------------------


class TestWrongEntityIsUnrepresentable:
    def test_unit_warmth_does_not_leak_when_no_business_index_exists(self) -> None:
        """A-1 RED arm 1 -- the deleted fallback's FIRST reachable position.

        reconcile-spend warms unit(office_phone, vertical) on some instances.
        With no business index at all, the pre-cure code fell through to the
        unit index. It must now return nothing.
        """
        _warm("unit", ["office_phone", "vertical"], _unit_frame(LIVE_VERTICAL))
        _warm("unit", ["office_phone"], _unit_frame(LIVE_VERTICAL))

        assert resolve_gid_from_index(OFFICE_PHONE) is None

    def test_unit_warmth_does_not_leak_on_a_business_index_key_miss(self) -> None:
        """A-1 RED arm 2 -- the deleted fallback's SECOND reachable position.

        A business index EXISTS but does not carry this phone. Arm 1 alone does
        not cover this: it short-circuits on `index is None` before any
        post-lookup fallback would run, so a fallback re-introduced after the
        business lookup would survive arm 1 undetected.
        """
        _warm("business", ["office_phone"], _business_frame())  # carries OFFICE_PHONE only
        _warm("unit", ["office_phone"], _unseeded_unit_frame())  # carries UNSEEDED_PHONE

        assert resolve_gid_from_index(UNSEEDED_PHONE) is None

    @pytest.mark.asyncio
    async def test_unit_warmed_instance_fails_closed_rather_than_resolving(self) -> None:
        """A-1 end-to-end: on a unit-warmed, business-cold instance the WHOLE
        path fails closed. It never answers found=true with a UNIT gid (silently
        wrong, strictly worse than today's loud miss) and never answers
        found=false (which drives a duplicate CREATE)."""
        _warm("unit", ["office_phone", "vertical"], _unit_frame(LIVE_VERTICAL))
        _warm("unit", ["office_phone"], _unit_frame(LIVE_VERTICAL))
        service = IntakeResolveService(_client(_task(UNIT_GID, _unit_project_gid())))

        with (
            patch(
                "autom8_asana.services.universal_strategy."
                "UniversalResolutionStrategy._get_dataframe",
                AsyncMock(return_value=None),
            ),
            pytest.raises(BusinessIndexUnavailableError),
        ):
            await service.resolve_business(office_phone=OFFICE_PHONE)

    def test_business_warmed_instance_does_yield_the_business_gid(self) -> None:
        """A-1 GREEN arm (the no-defect variant): identical call, business index
        warm -> the probe resolves. The guard bites only on the defect."""
        _warm("unit", ["office_phone", "vertical"], _unit_frame(LIVE_VERTICAL))
        _warm("business", ["office_phone"], _business_frame())

        assert resolve_gid_from_index(OFFICE_PHONE) == BUSINESS_GID

    @pytest.mark.asyncio
    async def test_a_unit_task_is_refused_as_a_business_of_record(self) -> None:
        """D-1b: even if a non-business GID reaches the fetch, membership of the
        business project is positively asserted before found=True is claimed."""
        _warm("business", ["office_phone"], _business_frame())
        service = IntakeResolveService(_client(_task(BUSINESS_GID, _unit_project_gid())))

        with pytest.raises(BusinessVerificationError) as exc:
            await service.resolve_business(office_phone=OFFICE_PHONE)

        assert exc.value.reason == "not_in_business_project"

    @pytest.mark.asyncio
    async def test_a_business_task_passes_the_assertion(self) -> None:
        """Two-sided: same path, membership in the business project -> found=True."""
        _warm("business", ["office_phone"], _business_frame())
        service = IntakeResolveService(_client(_task(BUSINESS_GID, _business_project_gid())))

        result = await service.resolve_business(office_phone=OFFICE_PHONE)

        assert isinstance(result, BusinessResolveResponse)
        assert result.found is True
        assert result.task_gid == BUSINESS_GID

    @pytest.mark.asyncio
    async def test_task_fetch_failure_never_claims_found_true(self) -> None:
        """D-1c: the fetch-failure branch returned found=True with an unverified
        bare GID. It now fails closed."""
        _warm("business", ["office_phone"], _business_frame())
        service = IntakeResolveService(_client(RuntimeError("asana 500")))

        with pytest.raises(BusinessVerificationError) as exc:
            await service.resolve_business(office_phone=OFFICE_PHONE)

        assert exc.value.reason == "task_fetch_failed"


# ---------------------------------------------------------------------------
# A-2 discriminator: ABSENT vs UNAVAILABLE, two-sided
# ---------------------------------------------------------------------------


class TestAbsentVersusUnavailable:
    """The two arms below differ in EXACTLY one fact: whether an index could be
    consulted. Everything else -- criterion, phone, client, patches -- is byte
    identical. Pre-cure both arms produced `found=false`, which the calendly
    pipeline answers with CREATE.
    """

    @pytest.mark.asyncio
    async def test_absent_is_found_false(self) -> None:
        """ABSENT: index consulted successfully, key genuinely missing -> 200
        found=false. Downstream CREATE is the CORRECT answer here."""
        _warm("business", ["office_phone"], _business_frame())
        service = IntakeResolveService(_client(_task(BUSINESS_GID, _business_project_gid())))

        with patch(
            "autom8_asana.services.universal_strategy.UniversalResolutionStrategy._get_dataframe",
            AsyncMock(return_value=None),
        ):
            result = await service.resolve_business(office_phone=UNSEEDED_PHONE)

        assert result.found is False
        assert result.task_gid is None

    @pytest.mark.asyncio
    async def test_unavailable_fails_closed(self) -> None:
        """UNAVAILABLE: the index could not be consulted OR built (cold
        DataFrameCache -- business is not body_parameterized, so a frame miss is
        terminal). Fails closed instead of answering found=false."""
        service = IntakeResolveService(_client(_task(BUSINESS_GID, _business_project_gid())))

        with (
            patch(
                "autom8_asana.services.universal_strategy."
                "UniversalResolutionStrategy._get_dataframe",
                AsyncMock(return_value=None),
            ),
            pytest.raises(BusinessIndexUnavailableError) as exc,
        ):
            await service.resolve_business(office_phone=UNSEEDED_PHONE)

        assert "INDEX_UNAVAILABLE" in str(exc.value)

    @pytest.mark.asyncio
    async def test_unavailable_error_reaches_the_route_503_branch(self) -> None:
        """The resurrected 503 branch keys on a RuntimeError whose message says
        "not ready". Pin that coupling -- it is the whole reason the branch was
        structurally dead for 138 days."""
        err = BusinessIndexUnavailableError("resolution strategy reported INDEX_UNAVAILABLE")

        assert isinstance(err, RuntimeError)
        assert "not ready" in str(err).lower()

    @pytest.mark.asyncio
    async def test_build_on_miss_requests_inactive_businesses_too(self) -> None:
        """C-10 RATIFIED: active_only=False. An INACTIVE business still EXISTS;
        filtering it out yields found=false, which drives a duplicate CREATE."""
        captured: dict[str, Any] = {}

        async def _capture(**kwargs: Any) -> list[Any]:
            captured.update(kwargs)
            from autom8_asana.services.resolution_result import ResolutionResult

            return [ResolutionResult.not_found()]

        service = IntakeResolveService(_client(_task(BUSINESS_GID, _business_project_gid())))

        with patch(
            "autom8_asana.services.universal_strategy.UniversalResolutionStrategy.resolve",
            AsyncMock(side_effect=_capture),
        ):
            result = await service.resolve_business(office_phone=UNSEEDED_PHONE)

        assert result.found is False
        assert captured["active_only"] is False
        assert captured["criteria"] == [{"office_phone": UNSEEDED_PHONE}]
        assert captured["project_gid"] == _business_project_gid()
