"""Unit tests for matching normalizers.

Per TDD-BusinessSeeder-v2: Tests for field normalization.
"""

from __future__ import annotations

import pytest

from autom8_asana.models.business.matching.normalizers import (
    AddressNormalizer,
    BusinessNameNormalizer,
    DomainNormalizer,
    EmailNormalizer,
    PhoneNormalizer,
)


class TestPhoneNormalizer:
    """Tests for PhoneNormalizer."""

    def test_normalize_none_returns_none(self) -> None:
        """None input returns None."""
        norm = PhoneNormalizer()
        assert norm.normalize(None) is None

    def test_normalize_empty_returns_none(self) -> None:
        """Empty string returns None."""
        norm = PhoneNormalizer()
        assert norm.normalize("") is None
        assert norm.normalize("   ") is None

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            pytest.param("5551234567", "+15551234567", id="10-digit"),
            pytest.param("(555) 123-4567", "+15551234567", id="formatted"),
            pytest.param("+1 555-123-4567", "+15551234567", id="with-country-code"),
            pytest.param("1-555-123-4567", "+15551234567", id="with-1-prefix"),
            pytest.param("123", "123", id="invalid-returns-digits"),
        ],
    )
    def test_normalize_phone(self, input_val: str, expected: str) -> None:
        """Verify phone normalization for various input formats."""
        norm = PhoneNormalizer()
        assert norm.normalize(input_val) == expected

    def test_normalize_non_numeric_only_returns_none(self) -> None:
        """Non-numeric input returns None."""
        norm = PhoneNormalizer()
        assert norm.normalize("call me") is None


class TestEmailNormalizer:
    """Tests for EmailNormalizer."""

    def test_normalize_none_returns_none(self) -> None:
        """None input returns None."""
        norm = EmailNormalizer()
        assert norm.normalize(None) is None

    def test_normalize_empty_returns_none(self) -> None:
        """Empty string returns None."""
        norm = EmailNormalizer()
        assert norm.normalize("") is None
        assert norm.normalize("   ") is None

    def test_normalize_lowercases_email(self) -> None:
        """Email is lowercased."""
        norm = EmailNormalizer()
        result = norm.normalize("John.Doe@EXAMPLE.COM")
        assert result == "john.doe@example.com"

    def test_normalize_trims_whitespace(self) -> None:
        """Whitespace is trimmed."""
        norm = EmailNormalizer()
        result = norm.normalize("  test@example.com  ")
        assert result == "test@example.com"

    def test_normalize_invalid_email_returns_none(self) -> None:
        """Invalid email returns None."""
        norm = EmailNormalizer()
        assert norm.normalize("not-an-email") is None
        assert norm.normalize("@example.com") is None
        assert norm.normalize("test@") is None

    def test_extract_domain(self) -> None:
        """Domain is extracted correctly."""
        norm = EmailNormalizer()
        assert norm.extract_domain("test@example.com") == "example.com"
        assert norm.extract_domain("John.Doe@GMAIL.COM") == "gmail.com"
        assert norm.extract_domain(None) is None
        assert norm.extract_domain("invalid") is None


class TestBusinessNameNormalizer:
    """Tests for BusinessNameNormalizer."""

    def test_normalize_none_returns_none(self) -> None:
        """None input returns None."""
        norm = BusinessNameNormalizer()
        assert norm.normalize(None) is None

    def test_normalize_empty_returns_none(self) -> None:
        """Empty string returns None."""
        norm = BusinessNameNormalizer()
        assert norm.normalize("") is None
        assert norm.normalize("   ") is None

    def test_normalize_lowercases(self) -> None:
        """Name is lowercased."""
        norm = BusinessNameNormalizer()
        result = norm.normalize("ACME CORP")
        assert result == "acme"  # 'corp' is stripped as legal suffix

    def test_normalize_strips_legal_suffixes(self) -> None:
        """Legal suffixes are stripped."""
        norm = BusinessNameNormalizer()
        assert norm.normalize("Acme Inc.") == "acme"
        assert norm.normalize("Acme LLC") == "acme"
        assert norm.normalize("Acme Corporation") == "acme"
        assert norm.normalize("Acme Corp") == "acme"
        assert norm.normalize("Acme Company") == "acme"
        assert norm.normalize("Acme Ltd") == "acme"

    def test_normalize_multiple_legal_suffixes(self) -> None:
        """Multiple legal suffixes are stripped."""
        norm = BusinessNameNormalizer()
        result = norm.normalize("Acme Inc LLC")
        assert result == "acme"

    def test_normalize_removes_punctuation(self) -> None:
        """Punctuation is removed."""
        norm = BusinessNameNormalizer()
        result = norm.normalize("Joe's Pizza!")
        assert result == "joes pizza"

    def test_normalize_whitespace(self) -> None:
        """Whitespace is normalized."""
        norm = BusinessNameNormalizer()
        result = norm.normalize("Acme   Corp   Inc")
        assert result == "acme"  # 'corp' and 'inc' stripped

    def test_normalize_preserves_real_content(self) -> None:
        """Real business content is preserved."""
        norm = BusinessNameNormalizer()
        result = norm.normalize("Joe's Pizza Palace")
        assert result == "joes pizza palace"


class TestDomainNormalizer:
    """Tests for DomainNormalizer."""

    def test_normalize_none_returns_none(self) -> None:
        """None input returns None."""
        norm = DomainNormalizer()
        assert norm.normalize(None) is None

    def test_normalize_empty_returns_none(self) -> None:
        """Empty string returns None."""
        norm = DomainNormalizer()
        assert norm.normalize("") is None
        assert norm.normalize("   ") is None

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            pytest.param("EXAMPLE.COM", "example.com", id="lowercases"),
            pytest.param("www.example.com", "example.com", id="strips-www"),
            pytest.param("https://example.com", "example.com", id="strips-https"),
            pytest.param("http://example.com", "example.com", id="strips-http"),
            pytest.param("example.com/path/to/page", "example.com", id="strips-path"),
            pytest.param("example.com?foo=bar", "example.com", id="strips-query"),
            pytest.param(
                "https://www.EXAMPLE.COM/path?query=1#hash",
                "example.com",
                id="full-url",
            ),
        ],
    )
    def test_normalize_domain(self, input_val: str, expected: str) -> None:
        """Verify domain normalization for various input formats."""
        norm = DomainNormalizer()
        assert norm.normalize(input_val) == expected


class TestAddressNormalizer:
    """Tests for AddressNormalizer."""

    def test_normalize_city(self) -> None:
        """City is normalized."""
        norm = AddressNormalizer()
        assert norm.normalize_city("Austin") == "austin"
        assert norm.normalize_city("  NEW YORK  ") == "new york"
        assert norm.normalize_city(None) is None
        assert norm.normalize_city("") is None

    def test_normalize_state_abbreviation(self) -> None:
        """State abbreviation is normalized."""
        norm = AddressNormalizer()
        assert norm.normalize_state("TX") == "tx"
        assert norm.normalize_state("tx") == "tx"

    def test_normalize_state_full_name(self) -> None:
        """State full name is converted to abbreviation."""
        norm = AddressNormalizer()
        assert norm.normalize_state("Texas") == "tx"
        assert norm.normalize_state("CALIFORNIA") == "ca"
        assert norm.normalize_state("New York") == "ny"

    def test_normalize_state_unknown(self) -> None:
        """Unknown state is returned as-is."""
        norm = AddressNormalizer()
        assert norm.normalize_state("Unknown") == "unknown"
        assert norm.normalize_state(None) is None

    def test_normalize_zip(self) -> None:
        """Zip is normalized to 5 digits."""
        norm = AddressNormalizer()
        assert norm.normalize_zip("78701") == "78701"
        assert norm.normalize_zip("78701-1234") == "78701"
        assert norm.normalize_zip("  78701  ") == "78701"
        assert norm.normalize_zip(None) is None
        assert norm.normalize_zip("") is None

    def test_normalize_zip_short(self) -> None:
        """Short zip returns as-is."""
        norm = AddressNormalizer()
        assert norm.normalize_zip("123") == "123"
