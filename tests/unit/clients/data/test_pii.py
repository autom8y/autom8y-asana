"""Tests for DataServiceClient PII redaction helpers.

Extracted from test_client.py as part of D-028 test file restructuring.
Maps to: mask_phone_number, _mask_canonical_key in client.py
"""

from __future__ import annotations


class TestMaskPhoneNumber:
    """Tests for mask_phone_number PII redaction helper (Story 1.9)."""

    def test_masks_standard_us_phone(self) -> None:
        """Standard US phone number is masked correctly."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("+17705753103")

        assert result == "+1770***3103"

    def test_masks_phone_keep_first_five_last_four(self) -> None:
        """Keeps first 5 chars and last 4 chars, masks middle."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("+14155551234")

        assert result == "+1415***1234"
        assert result.startswith("+1415")
        assert result.endswith("1234")

    def test_returns_short_phone_unchanged(self) -> None:
        """Short phone numbers (< 9 chars) are returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        # Too short to mask meaningfully
        result = mask_phone_number("+123456")

        assert result == "+123456"

    def test_returns_empty_string_unchanged(self) -> None:
        """Empty string is returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("")

        assert result == ""

    def test_returns_none_phone_unchanged(self) -> None:
        """None-like empty value is handled."""
        from autom8_asana.clients.data.client import mask_phone_number

        # Empty string edge case
        result = mask_phone_number("")

        assert result == ""

    def test_returns_non_e164_unchanged(self) -> None:
        """Non-E.164 format strings without + prefix are returned unchanged."""
        from autom8_asana.clients.data.client import mask_phone_number

        result = mask_phone_number("7705753103")

        # No + prefix, returned as-is
        assert result == "7705753103"

    def test_masks_international_phone(self) -> None:
        """International phone numbers are masked correctly."""
        from autom8_asana.clients.data.client import mask_phone_number

        # UK number
        result = mask_phone_number("+447911123456")

        assert result == "+4479***3456"


class TestMaskCanonicalKey:
    """Tests for _mask_canonical_key helper (Story 1.9)."""

    def test_masks_phone_in_canonical_key(self) -> None:
        """Phone number in canonical key is masked."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("pv1:+17705753103:chiropractic")

        assert result == "pv1:+1770***3103:chiropractic"

    def test_preserves_version_and_vertical(self) -> None:
        """Version prefix and vertical are preserved."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("pv1:+14155551234:dental")

        assert result.startswith("pv1:")
        assert result.endswith(":dental")

    def test_returns_non_pv1_unchanged(self) -> None:
        """Non-pv1 keys are returned unchanged."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("other:+17705753103:vertical")

        assert result == "other:+17705753103:vertical"

    def test_returns_malformed_key_unchanged(self) -> None:
        """Malformed keys are returned unchanged."""
        from autom8_asana.clients.data.client import _mask_canonical_key

        result = _mask_canonical_key("notakey")

        assert result == "notakey"
