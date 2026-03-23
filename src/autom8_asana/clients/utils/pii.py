"""Public PII redaction utilities.

Re-exports PII masking functions for use by bridge workflows and other
consumers that need phone number masking without reaching into
private data-client internals.

Per ADR-bridge-validate-extraction Decision 3 (import cleanup).
Per Obligation 7 (PII Contract): Phone numbers MUST be masked before
logging.
"""

from __future__ import annotations

from autom8_asana.clients.data._pii import (
    mask_canonical_key,
    mask_phone_number,
    mask_pii_in_string,
)

__all__ = [
    "mask_canonical_key",
    "mask_phone_number",
    "mask_pii_in_string",
]
