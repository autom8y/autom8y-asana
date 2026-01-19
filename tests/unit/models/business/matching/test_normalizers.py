"""Unit tests for matching normalizers.

Per TDD-BusinessSeeder-v2: Tests for field normalization.
"""

from __future__ import annotations

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

    def test_normalize_10_digit_phone(self) -> None:
        """10-digit phone normalized to E.164."""
        norm = PhoneNormalizer()
        result = norm.normalize("5551234567")
        assert result == "+15551234567"

    def test_normalize_formatted_phone(self) -> None:
        """Formatted phone normalized to E.164."""
        norm = PhoneNormalizer()
        result = norm.normalize("(555) 123-4567")
        assert result == "+15551234567"

    def test_normalize_phone_with_country_code(self) -> None:
        """Phone with +1 country code normalized."""
        norm = PhoneNormalizer()
        result = norm.normalize("+1 555-123-4567")
        assert result == "+15551234567"

    def test_normalize_phone_with_1_prefix(self) -> None:
        """Phone with 1 prefix normalized."""
        norm = PhoneNormalizer()
        result = norm.normalize("1-555-123-4567")
        assert result == "+15551234567"

    def test_normalize_invalid_phone_returns_digits(self) -> None:
        """Invalid phone returns digits only."""
        norm = PhoneNormalizer()
        result = norm.normalize("123")
        assert result == "123"

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

    def test_normalize_lowercases(self) -> None:
        """Domain is lowercased."""
        norm = DomainNormalizer()
        result = norm.normalize("EXAMPLE.COM")
        assert result == "example.com"

    def test_normalize_strips_www(self) -> None:
        """www prefix is stripped."""
        norm = DomainNormalizer()
        result = norm.normalize("www.example.com")
        assert result == "example.com"

    def test_normalize_strips_protocol(self) -> None:
        """Protocol is stripped."""
        norm = DomainNormalizer()
        assert norm.normalize("https://example.com") == "example.com"
        assert norm.normalize("http://example.com") == "example.com"

    def test_normalize_strips_path(self) -> None:
        """Path is stripped."""
        norm = DomainNormalizer()
        result = norm.normalize("example.com/path/to/page")
        assert result == "example.com"

    def test_normalize_strips_query(self) -> None:
        """Query string is stripped."""
        norm = DomainNormalizer()
        result = norm.normalize("example.com?foo=bar")
        assert result == "example.com"

    def test_normalize_full_url(self) -> None:
        """Full URL is normalized to domain."""
        norm = DomainNormalizer()
        result = norm.normalize("https://www.EXAMPLE.COM/path?query=1#hash")
        assert result == "example.com"


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
