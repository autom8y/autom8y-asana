"""Pydantic models for the EBI OI-2 receipts route.

Contract constraint: the request shape is FROZEN by the EBI consumer
(``autom8y`` branch ``ebi/s4-loud-receipt-nudge`` @ ``2b76085c``,
``services/email-booking-intake/src/email_booking_intake/receipts/asana_leg.py``):
the consumer POSTs exactly ``{"company_id", "kind", "body"}`` (three strings) and
raises on any wire error but otherwise ignores the response body (the
``FanOutReceiptSink`` wraps the leg no-throw). The response shape here exists for
observability + the operator's audit glance, not for consumer control flow.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ReceiptKind(StrEnum):
    """Echo of the EBI consumer ``ReceiptKind`` StrEnum.

    The satellite owns its OWN copy (no cross-repo import, per the
    no-cross-repo-import discipline). If EBI ships a new receipt kind without a
    provider update, an unknown ``kind`` surfaces LOUD as a 422
    ``UNKNOWN_RECEIPT_KIND`` (fail-loud on contract drift), not a silent
    malformed comment.
    """

    VERIFIED = "verified"  # vf- link resolved + binding row written
    MAIL_OBSERVED = "mail_observed"  # first real (non-forwarding) inbound seen
    FIRST_BOOKING = "first_booking"  # first booking completed for this clinic
    NUDGE = "nudge"  # verified but silent past N hours (probably not enabled)


class ReceiptPostRequest(BaseModel):
    """The frozen 3-field consumer body.

    ``company_id`` is the ONLY tenant key (LB-NO-RERESOLVE); an empty value is a
    422 both at the Pydantic layer (``min_length=1``) and semantically (never an
    anonymous receipt). ``kind`` is a bare ``str`` (NOT the enum) so an unknown
    value produces OUR domain 422 (``UNKNOWN_RECEIPT_KIND``) with the valid set,
    mirroring the ``UNKNOWN_PROCESS_TYPE`` idiom, rather than a generic Pydantic
    enum-validation message.

    Field sizes are BOUNDED at the Pydantic layer to close the unbounded-body
    DoS gap: an oversize payload is rejected as a clean 422 BEFORE any Asana call
    is attempted (no resolve, no search, no comment). ``body`` caps at 16384
    chars (a forwarding-lifecycle receipt is a few short lines; the ceiling is
    ~64x headroom over the largest legitimate receipt); ``company_id`` caps at
    256 chars (an office GUID is far shorter -- 256 is a generous identifier
    ceiling). ``kind`` is unbounded here because it is separately constrained to
    the four ``ReceiptKind`` literals by the route's domain check.
    """

    company_id: str = Field(min_length=1, max_length=256)
    kind: str
    body: str = Field(min_length=1, max_length=16384)


class ReceiptPostResponse(BaseModel):
    """Auditable result of threading the receipt.

    ``outcome`` is ``"posted"`` when a new comment story was created, or
    ``"skipped_duplicate"`` when the idempotency marker was already present on the
    task (a re-delivered receipt).
    """

    business_gid: str
    story_gid: str
    outcome: str
