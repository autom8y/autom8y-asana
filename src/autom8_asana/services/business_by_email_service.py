"""Resolve a business-of-record INDIRECTLY, by contact email (OW-10a).

The calendly intake pipeline keys the business-of-record on ``office_phone``.
Seven Calendly call event types collect no office-phone question at all
(SCOPE §5-P3), so those bookings reach the resolve stage with nothing to look
up and fail with ``no_office_phone``. The invitee's *email*, however, is always
carried.

This module closes that gap without inventing a second identity key. It walks
an EXISTING edge rather than minting one:

    contact.contact_email  --(registry key column)-->  contact row
    contact.office_phone   --(cascade from Business)-->  the business's key

Both halves are pre-existing registry facts, not new contract:

  * ``core/entity_registry.py`` declares ``contact`` with
    ``key_columns=("office_phone", "contact_phone", "contact_email")`` -- so a
    ``{"contact_email": ...}`` criterion is registry-LEGAL and gets an O(1)
    index, exactly like the phone path.
  * ``dataframes/schemas/contact.py`` declares ``office_phone`` with
    ``source="cascade:Office Phone"`` -- "CASCADE CONTRACT: sourced from
    Business.office_phone".

So this resolver adds no new key, no new index and no new Asana field. It
reads the generic engine (``UniversalResolutionStrategy``) over the ``contact``
entity and reports the cascaded phone.

UNIQUE-MATCH-ONLY (the load-bearing policy)
-------------------------------------------
The answer this endpoint returns becomes a *business of record* downstream: the
caller feeds ``office_phone`` straight into ``POST /v1/resolve/business``, and
a wrong phone there does not fail -- it SUCCEEDS against the wrong business and
silently binds a booking to a company that never took the call. There is no
downstream check that would catch it.

So a guess is never acceptable, and this module never makes one:

  * 0 contacts                       -> found=false, ``email_not_found``
  * >=2 DISTINCT businesses          -> found=false, ``email_ambiguous``
  * cascade null/blank               -> found=false, ``office_phone_absent``
  * cascade present but not E.164    -> found=false, ``office_phone_malformed``
  * exactly 1 distinct business      -> found=true

Note the discrimination on *distinct businesses*, not on contact rows. Two
contact rows carrying the same email under the SAME office are one business and
one unambiguous answer; the shape that must refuse is one email pointing at two
different companies (a shared receptionist, an agency address, a personal
gmail used at two practices).

THREE-OUTCOME CONTRACT (inherited, ADR-resolve-cure-design-2026-08-08 D-2b)
---------------------------------------------------------------------------
ABSENT and UNAVAILABLE stay DISTINCT here, for the same reason they do on the
business path. ``found=false`` is a positive claim -- "the index was consulted
and this email is genuinely not on it". An index that could not be consulted
is NOT that claim, and is raised as UNAVAILABLE (503) rather than flattened
into ``found=false``. The strategy signals this through
``ResolutionResult.error``: only ``NOT_FOUND`` is ABSENT; ``INDEX_UNAVAILABLE``,
``LOOKUP_ERROR``, ``INVALID_CRITERIA`` and ``RESOLUTION_NULL_SLOT`` are all
"we do not know", and are refused LOUDLY.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

if TYPE_CHECKING:
    from autom8_asana.api.routes.intake_resolve_models import BusinessByEmailResolveResponse
    from autom8_asana.client import AsanaClient

# ★ IMPORT DIRECTION (do not "tidy" these into module-level imports):
# ``api/routes/__init__.py`` imports ``intake_resolve``, which imports THIS
# module. A module-level ``from autom8_asana.api.routes...`` here therefore
# closes a cycle -- importing this module first raises
# ``ImportError: cannot import name ... (most likely due to a circular
# import)``. ``intake_resolve_service`` gets away with the module-level form
# only because nothing imports it ahead of the routes package; that is a
# latent version of the same cycle, not a licence. The response model and the
# E.164 predicate are imported at their use sites below instead.

logger = get_logger(__name__)

__all__ = [
    "ContactIndexUnavailableError",
    "redact_email",
    "resolve_business_by_email",
]

# Registry entity name for the contact leaf. Key columns and project GID are
# read from the descriptor / project registry -- never from a literal here.
_CONTACT_ENTITY = "contact"

# The registry key column this surface forms its criterion from.
_EMAIL_KEY = "contact_email"

# Cascade fields pulled back for the answer. Both are declared on
# CONTACT_SCHEMA; ``office_phone`` is the business's natural key.
_OFFICE_PHONE_FIELD = "office_phone"
_VERTICAL_FIELD = "vertical"

# ``ResolutionResult.error`` values that mean ABSENT (the index WAS consulted).
# Every other error string is UNAVAILABLE and must fail closed. Spelling the
# ABSENT set as the allow-list -- rather than enumerating the failures -- means
# a NEW error code added upstream defaults to fail-closed instead of silently
# becoming a found=false.
_ABSENT_ERRORS = frozenset({"NOT_FOUND"})


class ContactIndexUnavailableError(RuntimeError):
    """UNAVAILABLE: the contact index could not be consulted or built.

    Subclasses ``RuntimeError`` and always carries "not ready" in its message so
    the route's 503 ``INDEX_NOT_READY`` branch converts it, matching the
    established business-path convention (``BusinessIndexUnavailableError``).
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"contact index is not ready: {reason}")


def redact_email(email: str) -> str:
    """Mask an email's local part for logging.

    PII fence: the raw invitee email never reaches a log line. The domain is
    retained because it is the diagnostically useful half (it identifies the
    practice, not the person) and mirrors the business path's phone handling,
    which keeps the country/area prefix and masks the subscriber digits.

    Args:
        email: Raw email address.

    Returns:
        Redacted form, e.g. ``j***@example.com``. Input without an ``@`` is
        masked entirely rather than passed through.
    """
    local, sep, domain = email.partition("@")
    if not sep or not domain:
        return "***"
    head = local[:1] if local else ""
    return f"{head}***@{domain}"


def _contact_descriptor() -> Any:
    """Registry descriptor for the contact entity (DIP: no hardcoded ids)."""
    from autom8_asana.core.entity_registry import get_registry

    return get_registry().require(_CONTACT_ENTITY)


def _email_criterion(email: str) -> dict[str, str]:
    """Build the contact lookup criterion, asserting the registry still keys it.

    The defect this guards is the same one the business path guards: a
    hardcoded key that drifts from the registry becomes a permanent, silent,
    structural index miss -- every lookup returns "no such contact" forever and
    nothing ever errors. A criterion this surface cannot legally form is
    refused LOUDLY instead of issuing a structurally-doomed lookup.

    Args:
        email: Contact email address.

    Returns:
        Criterion dict keyed on the registry's email key column.

    Raises:
        ContactIndexUnavailableError: If the registry no longer declares
            ``contact_email`` among ``contact``'s key columns.
    """
    key_columns = tuple(_contact_descriptor().key_columns or ())
    if _EMAIL_KEY not in key_columns:
        raise ContactIndexUnavailableError(
            f"registry keys {_CONTACT_ENTITY!r} on {list(key_columns)!r}; "
            f"{_EMAIL_KEY!r} is not among them, so this surface cannot form a criterion"
        )
    return {_EMAIL_KEY: email}


def _not_found(reason: str, **extra: Any) -> BusinessByEmailResolveResponse:
    """Build a discriminated found=false answer."""
    from autom8_asana.api.routes.intake_resolve_models import BusinessByEmailResolveResponse

    return BusinessByEmailResolveResponse(found=False, reason=reason, **extra)


async def resolve_business_by_email(
    email: str,
    client: AsanaClient,
) -> BusinessByEmailResolveResponse:
    """Resolve the office phone of the business a contact email belongs to.

    Args:
        email: Contact email address (exact match; the index is the authority
            on normalization).
        client: AsanaClient used for DataFrame/index construction.

    Returns:
        BusinessByEmailResolveResponse. ``found=True`` only on a single
        distinct, E.164-valid business phone; every other outcome is
        ``found=False`` with a discriminating ``reason``.

    Raises:
        ContactIndexUnavailableError: UNAVAILABLE -- the contact index could
            not be consulted, or the registry no longer supports the criterion.
            Never downgraded to ``found=False``.
    """
    from autom8_asana.api.routes.intake_resolve_models import BusinessByEmailResolveResponse
    from autom8_asana.services.intake_resolve_service import is_valid_e164
    from autom8_asana.services.resolver import EntityProjectRegistry, get_strategy

    criterion = _email_criterion(email)

    project_registry = EntityProjectRegistry.get_instance()
    if not project_registry.is_ready():
        raise ContactIndexUnavailableError("entity project discovery has not completed")

    project_gid = project_registry.get_project_gid(_CONTACT_ENTITY)
    if project_gid is None:
        raise ContactIndexUnavailableError(f"no project registered for {_CONTACT_ENTITY!r}")

    strategy = get_strategy(_CONTACT_ENTITY)
    if strategy is None:
        raise ContactIndexUnavailableError(f"no resolution strategy for {_CONTACT_ENTITY!r}")

    # active_only=False is DELIBERATE and load-bearing, not a default carried in
    # by accident. The unique-match policy is only sound if it sees EVERY
    # candidate: a status filter that quietly narrowed two businesses to one
    # would manufacture a false "unique" and mint exactly the wrong
    # business-of-record this endpoint exists to refuse. ``contact`` has no
    # entry in ``models/business/activity.py::CLASSIFIERS`` today, so this is
    # currently a no-op -- pinning it means registering a contact classifier
    # later cannot silently change the ambiguity semantics.
    results = await strategy.resolve(
        criteria=[criterion],
        project_gid=project_gid,
        client=client,
        requested_fields=[_OFFICE_PHONE_FIELD, _VERTICAL_FIELD],
        active_only=False,
    )

    if not results:
        raise ContactIndexUnavailableError("strategy returned no result slot for the criterion")

    result = results[0]

    # UNAVAILABLE gate: anything that is not a positive ABSENT fails closed.
    if result.error is not None and result.error not in _ABSENT_ERRORS:
        raise ContactIndexUnavailableError(f"contact lookup returned {result.error}")

    if not result.gids:
        return _not_found("email_not_found")

    contexts: tuple[dict[str, Any], ...] = result.match_context or ()

    # Distinct businesses, not distinct contact rows (see module docstring).
    # Blank-but-present cascades collapse to "absent" rather than counting as a
    # distinct business -- an empty string is not an office.
    phones: list[str] = []
    for ctx in contexts:
        raw = ctx.get(_OFFICE_PHONE_FIELD)
        if raw is None:
            continue
        value = str(raw).strip()
        if value:
            phones.append(value)

    distinct_phones = sorted(set(phones))

    if not distinct_phones:
        # Contacts exist, but none carries the cascade. This is the FIND-005
        # shape that CONTACT_SCHEMA names on the office_phone column, where a
        # null cascade degrades into a silent not-found. It is surfaced here as
        # its own reason rather than folded into email_not_found, because the
        # remedies differ: this is a warm or cascade gap on a contact that DOES
        # exist, not a missing contact.
        return _not_found("office_phone_absent", match_count=result.match_count)

    if len(distinct_phones) > 1:
        return _not_found(
            "email_ambiguous",
            match_count=result.match_count,
            distinct_business_count=len(distinct_phones),
        )

    office_phone = distinct_phones[0]

    if not is_valid_e164(office_phone):
        # Refuse rather than hand the caller a phone that POST
        # /v1/resolve/business would reject with 400 INVALID_PHONE_FORMAT
        # anyway. Discriminating it here names the real defect (a malformed
        # Office Phone on the business task) instead of surfacing it
        # downstream as a generic bad request.
        return _not_found(
            "office_phone_malformed",
            match_count=result.match_count,
            distinct_business_count=1,
        )

    # vertical is best-effort context, not part of the found decision. Only
    # claimed when unambiguous across the matched rows.
    verticals = sorted(
        {
            str(ctx.get(_VERTICAL_FIELD)).strip()
            for ctx in contexts
            if ctx.get(_VERTICAL_FIELD) is not None and str(ctx.get(_VERTICAL_FIELD)).strip()
        }
    )

    return BusinessByEmailResolveResponse(
        found=True,
        office_phone=office_phone,  # type: ignore[arg-type]  # branded NewType
        vertical=verticals[0] if len(verticals) == 1 else None,
        contact_gid=result.gids[0] if result.match_count == 1 else None,
        reason="unique_match",
        match_count=result.match_count,
        distinct_business_count=1,
    )
