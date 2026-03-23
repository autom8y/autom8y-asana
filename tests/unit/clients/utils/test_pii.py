"""Tests for public PII redaction utilities.

Per TDD sprint-2 Item 2: Verify that the public re-export path
``autom8_asana.clients.utils.pii`` exposes all PII masking functions
and produces correct output identical to the private ``_pii`` module.

Per ADR-bridge-validate-extraction Decision 3 (import cleanup).
"""

from __future__ import annotations

import pytest

from autom8_asana.clients.utils.pii import (
    mask_canonical_key,
    mask_phone_number,
    mask_pii_in_string,
)


class TestPublicPiiImports:
    """Tests that the public PII re-export module works correctly."""

    def test_mask_phone_number_is_callable(self) -> None:
        """mask_phone_number is importable and callable."""
        assert callable(mask_phone_number)

    def test_mask_canonical_key_is_callable(self) -> None:
        """mask_canonical_key is importable and callable."""
        assert callable(mask_canonical_key)

    def test_mask_pii_in_string_is_callable(self) -> None:
        """mask_pii_in_string is importable and callable."""
        assert callable(mask_pii_in_string)

    @pytest.mark.parametrize(
        "phone,expected",
        [
            pytest.param("+17705753103", "+1770***3103", id="standard-us-phone"),
            pytest.param("+447911123456", "+4479***3456", id="international-phone"),
            pytest.param("", "", id="empty-string"),
            pytest.param("7705753103", "7705753103", id="non-e164-unchanged"),
        ],
    )
    def test_mask_phone_number_produces_expected_output(
        self, phone: str, expected: str
    ) -> None:
        """Public mask_phone_number produces same output as private _pii module."""
        assert mask_phone_number(phone) == expected

    def test_mask_canonical_key_produces_expected_output(self) -> None:
        """Public mask_canonical_key masks phone in canonical key."""
        result = mask_canonical_key("pv1:+17705753103:chiropractic")
        assert result == "pv1:+1770***3103:chiropractic"

    def test_mask_pii_in_string_produces_expected_output(self) -> None:
        """Public mask_pii_in_string masks all phone numbers in string."""
        result = mask_pii_in_string("Call +17705753103 and +14155551234")
        assert "+17705753103" not in result
        assert "+14155551234" not in result
        assert "+1770***3103" in result
        assert "+1415***1234" in result

    def test_functions_are_same_objects_as_private_module(self) -> None:
        """Public re-exports are the exact same function objects as _pii module."""
        from autom8_asana.clients.data._pii import (
            mask_canonical_key as private_mck,
        )
        from autom8_asana.clients.data._pii import (
            mask_phone_number as private_mpn,
        )
        from autom8_asana.clients.data._pii import (
            mask_pii_in_string as private_mpis,
        )

        assert mask_phone_number is private_mpn
        assert mask_canonical_key is private_mck
        assert mask_pii_in_string is private_mpis
