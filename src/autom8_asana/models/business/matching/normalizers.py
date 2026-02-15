"""Field value normalizers for matching engine.

Per TDD FR-M-007, FR-M-008, FR-M-009: Field normalization for comparison.
Uses Protocol pattern for testability and extensibility.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Protocol


class Normalizer(Protocol):
    """Field value normalizer protocol.

    Normalizers transform raw field values into canonical forms
    suitable for comparison.
    """

    def normalize(self, value: str | None) -> str | None:
        """Normalize value for comparison.

        Args:
            value: Raw field value.

        Returns:
            Normalized value, or None if value is empty/whitespace.
        """
        ...


class PhoneNormalizer:
    """E.164 phone normalization with fallback.

    Per FR-M-008: Normalize phone numbers to E.164 format.
    Falls back to digits-only if phonenumbers library unavailable.

    Example:
        >>> norm = PhoneNormalizer()
        >>> norm.normalize("+1 (555) 123-4567")
        '+15551234567'
        >>> norm.normalize("555-123-4567")
        '+15551234567'  # Assumes US
    """

    def normalize(self, value: str | None) -> str | None:
        """Normalize phone number to E.164 format.

        Args:
            value: Raw phone number string.

        Returns:
            E.164 formatted phone, or digits-only as fallback.
            None if value is empty/whitespace.
        """
        if not value or not value.strip():
            return None

        value = value.strip()

        # Try phonenumbers library first (optional dependency)
        try:
            import phonenumbers

            parsed = phonenumbers.parse(value, "US")
            if phonenumbers.is_valid_number(parsed):
                formatted: str = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
                return formatted
            # Invalid number - fall through to digits-only
        except ImportError:
            pass  # phonenumbers not installed
        except (ValueError, TypeError):  # vendor-polymorphic -- phonenumbers raises diverse parsing errors
            pass

        # Fallback: extract digits only
        digits = "".join(c for c in value if c.isdigit())
        if not digits:
            return None

        # Normalize to 10-digit US number format
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]  # Remove country code
        if len(digits) == 10:
            return f"+1{digits}"

        # Return digits as-is if can't normalize
        return digits if digits else None


class EmailNormalizer:
    """Email normalization for comparison.

    Per FR-M-009: Normalize email addresses before comparison.
    Lowercases, trims whitespace, extracts domain.

    Example:
        >>> norm = EmailNormalizer()
        >>> norm.normalize("  John.Doe@GMAIL.COM  ")
        'john.doe@gmail.com'
    """

    def normalize(self, value: str | None) -> str | None:
        """Normalize email address.

        Args:
            value: Raw email string.

        Returns:
            Lowercase, trimmed email, or None if invalid/empty.
        """
        if not value or not value.strip():
            return None

        # Lowercase and trim
        result = value.strip().lower()

        # Basic validation - must have @ and something on each side
        if "@" not in result:
            return None

        parts = result.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            return None

        return result

    def extract_domain(self, value: str | None) -> str | None:
        """Extract domain from email address.

        Args:
            value: Raw or normalized email.

        Returns:
            Domain part of email, or None if invalid.
        """
        normalized = self.normalize(value)
        if not normalized:
            return None

        return normalized.split("@")[1]


class BusinessNameNormalizer:
    """Normalize business names for comparison.

    Per FR-M-007: Strip legal suffixes, normalize whitespace/case.

    Example:
        >>> norm = BusinessNameNormalizer()
        >>> norm.normalize("ACME Corp, Inc.")
        'acme corp'
        >>> norm.normalize("Joe's Pizza LLC")
        'joes pizza'
    """

    # Legal suffixes to strip (lowercase)
    LEGAL_SUFFIXES: frozenset[str] = frozenset(
        [
            "inc",
            "llc",
            "ltd",
            "corp",
            "corporation",
            "company",
            "co",
            "llp",
            "lp",
            "pllc",
            "incorporated",
            "limited",
            "pc",
            "pa",
            "pllp",
        ]
    )

    def normalize(self, value: str | None) -> str | None:
        """Normalize business name for comparison.

        Args:
            value: Raw business name.

        Returns:
            Normalized name, or None if empty.
        """
        if not value or not value.strip():
            return None

        # Normalize unicode to NFD form
        result = unicodedata.normalize("NFD", value)

        # Lowercase
        result = result.lower()

        # Remove punctuation (keep letters, numbers, whitespace)
        result = re.sub(r"[^\w\s]", "", result)

        # Normalize whitespace to single spaces
        result = " ".join(result.split())

        # Strip legal suffixes from end
        words = result.split()
        while words and words[-1] in self.LEGAL_SUFFIXES:
            words.pop()

        result = " ".join(words).strip()
        return result if result else None


class DomainNormalizer:
    """Normalize domain names for comparison.

    Strips www prefix, lowercases, removes trailing slashes.

    Example:
        >>> norm = DomainNormalizer()
        >>> norm.normalize("WWW.Example.COM/")
        'example.com'
    """

    def normalize(self, value: str | None) -> str | None:
        """Normalize domain name.

        Args:
            value: Raw domain or URL.

        Returns:
            Normalized domain, or None if empty/invalid.
        """
        if not value or not value.strip():
            return None

        result = value.strip().lower()

        # Remove protocol if present
        for prefix in ("https://", "http://", "//"):
            if result.startswith(prefix):
                result = result[len(prefix) :]
                break

        # Remove www prefix
        if result.startswith("www."):
            result = result[4:]

        # Remove path/query/fragment
        result = result.split("/")[0]
        result = result.split("?")[0]
        result = result.split("#")[0]

        # Remove trailing dots
        result = result.rstrip(".")

        return result if result else None


class AddressNormalizer:
    """Normalize address components for comparison.

    Normalizes city, state, and zip for composite address comparison.
    """

    # Common state abbreviation mappings
    STATE_ABBREV: dict[str, str] = {
        "alabama": "al",
        "alaska": "ak",
        "arizona": "az",
        "arkansas": "ar",
        "california": "ca",
        "colorado": "co",
        "connecticut": "ct",
        "delaware": "de",
        "florida": "fl",
        "georgia": "ga",
        "hawaii": "hi",
        "idaho": "id",
        "illinois": "il",
        "indiana": "in",
        "iowa": "ia",
        "kansas": "ks",
        "kentucky": "ky",
        "louisiana": "la",
        "maine": "me",
        "maryland": "md",
        "massachusetts": "ma",
        "michigan": "mi",
        "minnesota": "mn",
        "mississippi": "ms",
        "missouri": "mo",
        "montana": "mt",
        "nebraska": "ne",
        "nevada": "nv",
        "new hampshire": "nh",
        "new jersey": "nj",
        "new mexico": "nm",
        "new york": "ny",
        "north carolina": "nc",
        "north dakota": "nd",
        "ohio": "oh",
        "oklahoma": "ok",
        "oregon": "or",
        "pennsylvania": "pa",
        "rhode island": "ri",
        "south carolina": "sc",
        "south dakota": "sd",
        "tennessee": "tn",
        "texas": "tx",
        "utah": "ut",
        "vermont": "vt",
        "virginia": "va",
        "washington": "wa",
        "west virginia": "wv",
        "wisconsin": "wi",
        "wyoming": "wy",
        "district of columbia": "dc",
    }

    def normalize_city(self, value: str | None) -> str | None:
        """Normalize city name.

        Args:
            value: Raw city name.

        Returns:
            Lowercase, trimmed city name.
        """
        if not value or not value.strip():
            return None
        return value.strip().lower()

    def normalize_state(self, value: str | None) -> str | None:
        """Normalize state to 2-letter abbreviation.

        Args:
            value: State name or abbreviation.

        Returns:
            2-letter lowercase abbreviation, or original if unknown.
        """
        if not value or not value.strip():
            return None

        result = value.strip().lower()

        # Already an abbreviation?
        if len(result) == 2:
            return result

        # Look up full name
        return self.STATE_ABBREV.get(result, result)

    def normalize_zip(self, value: str | None) -> str | None:
        """Normalize zip code to 5-digit format.

        Args:
            value: Raw zip code.

        Returns:
            5-digit zip code (strips +4 extension).
        """
        if not value or not value.strip():
            return None

        # Extract digits only
        digits = "".join(c for c in value if c.isdigit())

        # Take first 5 digits
        if len(digits) >= 5:
            return digits[:5]

        return digits if digits else None
