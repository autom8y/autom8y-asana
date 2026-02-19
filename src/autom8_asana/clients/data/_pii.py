"""PII redaction primitives for DataServiceClient.

Private module holding phone-number masking functions used across
the clients/data package. Extracted to break circular imports between
client.py and submodules (_cache.py, _retry.py, etc.).

PII redaction contract (XR-003).

These functions are NOT part of the public API — they are re-exported
from client.py for backward compatibility.
"""

from __future__ import annotations

import re

# Pattern matches E.164 phone numbers: +{country code}{digits}
_PHONE_PATTERN = re.compile(r"\+\d{10,15}")


def mask_phone_number(phone: str) -> str:
    """Mask middle digits of phone number for PII protection.

    Redact phone numbers in logs.
    Pattern: +17705753103 -> +1770***3103 (keep first 5 + last 4 digits)

    Args:
        phone: E.164 formatted phone number (e.g., +17705753103).

    Returns:
        Masked phone number with middle digits replaced by asterisks.
        Returns original string if not a valid phone format.
    """
    if not phone or len(phone) < 9:
        return phone

    if phone.startswith("+") and len(phone) >= 9:
        prefix = phone[:5]
        suffix = phone[-4:]
        return f"{prefix}***{suffix}"

    return phone


def mask_canonical_key(canonical_key: str) -> str:
    """Mask phone number in canonical key for PII protection.

    Args:
        canonical_key: PVP canonical key (e.g., pv1:+17705753103:chiropractic).

    Returns:
        Canonical key with phone number masked.
    """
    parts = canonical_key.split(":")
    if len(parts) >= 3 and parts[0] == "pv1":
        parts[1] = mask_phone_number(parts[1])
        return ":".join(parts)
    return canonical_key


def mask_pii_in_string(s: str) -> str:
    """Replace all E.164 phone numbers in an arbitrary string with masked versions.

    Per XR-003: Defense-in-depth for cache keys, error messages, and any
    freeform string that might contain PII.

    Args:
        s: Any string that may contain E.164 phone numbers.

    Returns:
        String with all phone matches replaced via mask_phone_number.
    """
    return _PHONE_PATTERN.sub(lambda m: mask_phone_number(m.group()), s)
