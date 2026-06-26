"""Tests for the GFR tiered truth-source (TDD §7, §9.3 truth_source.py row).

Tier-2 verify is a BY-GUID lookup (INVARIANT I7), NOT the office_phone analytics
join. These tests verify the ByGuidVerifier port contract: a matching record
verifies, a miss or guid mismatch does not, and the verify path consults only the
by-guid method.
"""

from __future__ import annotations

import pytest

from autom8_asana.resolution.gfr.truth_source import (
    ByGuidVerifier,
    verify_company_id_async,
)
from tests.unit.resolution.gfr.conftest import FakeByGuidVerifier, make_record

pytestmark = [pytest.mark.xdist_group("gfr_resolver")]


class TestVerifierProtocol:
    def test_fake_satisfies_protocol(self) -> None:
        fake = FakeByGuidVerifier()
        assert isinstance(fake, ByGuidVerifier)


class TestVerifyCompanyId:
    @pytest.mark.asyncio
    async def test_matching_guid_verifies(self) -> None:
        fake = FakeByGuidVerifier({"G_A": make_record("G_A")})
        assert await verify_company_id_async("G_A", fake) is True
        # The verify consulted the by-guid method exactly once.
        assert fake.calls == ["G_A"]

    @pytest.mark.asyncio
    async def test_by_guid_miss_does_not_verify(self) -> None:
        fake = FakeByGuidVerifier(records={})  # 200 + data=null envelope on miss
        assert await verify_company_id_async("G_A", fake) is False
        assert fake.calls == ["G_A"]

    @pytest.mark.asyncio
    async def test_guid_mismatch_does_not_verify(self) -> None:
        # Record exists but its guid differs from the candidate company_id.
        fake = FakeByGuidVerifier({"G_A": make_record("G_DIFFERENT")})
        assert await verify_company_id_async("G_A", fake) is False

    @pytest.mark.asyncio
    async def test_verify_uses_only_by_guid_not_phone(self) -> None:
        # The fake exposes ONLY get_business_by_guid_async; if the verify path
        # attempted an office_phone lookup it would AttributeError. Passing here
        # proves identity verify is by-guid (INVARIANT I7), never phone.
        fake = FakeByGuidVerifier({"G_A": make_record("G_A")})
        assert not hasattr(fake, "get_business_by_phone_async")
        assert await verify_company_id_async("G_A", fake) is True
