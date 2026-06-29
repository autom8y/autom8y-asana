"""Unit tests for compute_ebid (local ebid derivation; transform parity)."""

from __future__ import annotations

import pytest
from autom8y_guid import normalize_chiropractor_guid

from autom8_asana.automation.workflows.leads_ebid import (
    EbidInputAbsent,
    EbidInputNull,
    compute_ebid,
)


def test_uuid_passthrough_lowercased() -> None:
    raw = "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
    assert compute_ebid(raw) == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def test_numeric_116_cohort_converts_to_uuid5() -> None:
    # The 116 numeric cohort routes through the uuid5 branch.
    ebid = compute_ebid("116")
    expected, was_converted = normalize_chiropractor_guid("116")
    assert was_converted is True
    assert ebid == expected


def test_transform_parity_with_producer() -> None:
    # Proves the consumer's transform == the producer's (no drift, R5): compute
    # the ebid directly via autom8y_guid and assert equality for several inputs.
    for company_id in ["123", "00000000-0000-0000-0000-000000000001", "987654"]:
        direct, _ = normalize_chiropractor_guid(company_id)
        assert compute_ebid(company_id) == direct


def test_none_company_id_raises_input_absent() -> None:
    with pytest.raises(EbidInputAbsent):
        compute_ebid(None)


def test_empty_company_id_raises_input_null() -> None:
    with pytest.raises(EbidInputNull):
        compute_ebid("")


def test_whitespace_company_id_raises_input_null() -> None:
    with pytest.raises(EbidInputNull):
        compute_ebid("   ")
