"""Service for intake resolution operations.

Handles business resolution (office_phone -> GID via the shared
DynamicIndexCache) and contact resolution (email/phone -> contact within
business scope).

Per ADR-INT-001: Never return 404 for not-found; use found=False.
Per ADR-INT-002: Email-then-phone priority, NO name matching.

Per ADR-resolve-cure-design-2026-08-08 the business resolve path has a
THREE-outcome contract, not a two-outcome one:

    RESOLVED     index consulted, key hit          -> 200 found=true + gid
    ABSENT       index consulted OK, key missing   -> 200 found=false
    UNAVAILABLE  index unconsultable / unverified  -> 503 (never found=*)

UNAVAILABLE fails CLOSED (D-2b): the calendly pipeline answers ``found=false``
with CREATE, so downgrading an unknown world-state to ``found=false`` would
guarantee a duplicate production business on every index gap.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from autom8y_api_schemas import LeadPhone, OfficePhone
from autom8y_log import get_logger

from autom8_asana.api.routes.intake_resolve_models import (
    BusinessResolveResponse,
    ContactResolveResponse,
)

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# E.164 phone format: +{country_code}{number}, 7-15 digits total
_E164_PATTERN = re.compile(r"^\+[1-9]\d{6,14}$")

# Custom field names in Asana for contact resolution
_CONTACT_EMAIL_FIELD = "contact_email"
_CONTACT_PHONE_FIELD = "contact_phone"
_COMPANY_ID_FIELD = "company_id"

# Registry entity name for the business-of-record. Key columns, project GID and
# schema all come from the descriptor -- never from a literal in this module.
_BUSINESS_ENTITY = "business"

# Errors a fast-path index READ may legitimately raise. Deliberately narrow:
# anything outside this set is a fail-closed condition, not a cache miss
# (the blanket ``except Exception: pass`` this replaces collapsed cold-index,
# expired-index, build-failed and genuinely-absent into one silent None).
_INDEX_READ_ERRORS = (ImportError, AttributeError, KeyError, TypeError, ValueError)


class BusinessIndexUnavailableError(RuntimeError):
    """UNAVAILABLE: the business index could not be consulted or built.

    Subclasses ``RuntimeError`` and always carries "not ready" in its message
    so the pre-existing 503 ``INDEX_NOT_READY`` branch in
    ``api/routes/intake_resolve.py`` converts it -- the branch is resurrected,
    not replaced.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"business index is not ready: {reason}")


class BusinessVerificationError(Exception):
    """UNAVAILABLE: a GID was resolved but could not be verified as a business.

    Raised when the resolved task cannot be fetched, or when it is not a member
    of the registry's business project (wrong-entity). Never downgraded to
    ``found=false`` -- that answer drives CREATE downstream.
    """

    def __init__(self, reason: str, gid: str) -> None:
        self.reason = reason
        self.gid = gid
        super().__init__(f"business verification failed ({reason}) for gid={gid}")


def _business_descriptor() -> Any:
    """Registry descriptor for the business entity (DIP: no hardcoded ids)."""
    from autom8_asana.core.entity_registry import get_registry

    return get_registry().require(_BUSINESS_ENTITY)


def _business_criterion(office_phone: str) -> dict[str, str]:
    """Build the business lookup criterion from the REGISTRY's key columns.

    The defect this cure closes is a hardcoded key list that diverged from the
    registry (a permanent, silent, structural index miss). So the key columns
    are read from the descriptor, and a divergence the caller cannot satisfy is
    refused LOUDLY rather than issuing a structurally-doomed lookup.

    Args:
        office_phone: E.164 phone number -- the only value this surface holds.

    Returns:
        Criterion dict whose keys are exactly the registry's key columns.

    Raises:
        BusinessIndexUnavailableError: If the registry keys ``business`` on
            anything other than ``office_phone`` alone, i.e. on a criterion this
            surface cannot form. Fail-closed by construction.
    """
    key_columns = list(_business_descriptor().key_columns or ())
    if key_columns != ["office_phone"]:
        raise BusinessIndexUnavailableError(
            f"registry keys {_BUSINESS_ENTITY!r} on {key_columns!r}; this surface can only "
            "form a criterion from office_phone"
        )
    return {"office_phone": office_phone}


def is_valid_e164(phone: str) -> bool:
    """Validate E.164 phone format."""
    return bool(_E164_PATTERN.match(phone))


def _extract_custom_field(custom_fields: list[dict[str, Any]], field_name: str) -> str | None:
    """Extract a custom field value by name from Asana custom_fields list."""
    for cf in custom_fields:
        # strip() both sides so a trailing/leading-space CF rename cannot silently
        # miss on the read side and compound the stamp-side miss (DEF-QA-3).
        if cf.get("name", "").strip().lower() == field_name.strip().lower():
            # Check text_value first, then number_value, then enum display value
            if cf.get("text_value") is not None:
                return str(cf["text_value"])
            if cf.get("display_value") is not None:
                return str(cf["display_value"])
            if cf.get("number_value") is not None:
                return str(cf["number_value"])
    return None


def resolve_gid_from_index(office_phone: str) -> str | None:
    """Fast-path read of an ALREADY-WARM business index.

    Module-level function to enable clean patching in tests.

    Consults the shared ``DynamicIndexCache`` for the ``business`` entity,
    keyed on the columns the entity registry declares (``office_phone`` alone
    today). There is deliberately NO unit fallback: ``business`` is a ROOT
    entity with its own project and its own key columns, and ``unit`` is its
    CHILD -- a business is never "indexed under unit", so the fallback could
    only ever return a UNIT gid to a caller that assigns it to ``business_gid``.

    A ``None`` here is NOT an answer. It means "not served from the warm
    index" and the caller MUST fall through to
    :meth:`IntakeResolveService.resolve_business`'s build-on-miss, which is the
    only surface that can discriminate ABSENT from UNAVAILABLE.

    Args:
        office_phone: E.164 phone number.

    Returns:
        GID string on a warm-index hit, ``None`` otherwise.

    Raises:
        BusinessIndexUnavailableError: If the registry's business key columns
            diverge from what this surface can supply (see
            :func:`_business_criterion`).
    """
    criterion = _business_criterion(office_phone)

    try:
        from autom8_asana.services.universal_strategy import get_shared_index_cache

        index = get_shared_index_cache().get(_BUSINESS_ENTITY, list(criterion))
        if index is None:
            return None
        gids = index.lookup(criterion)
    except _INDEX_READ_ERRORS as exc:
        logger.warning(
            "business_index_fast_path_failed",
            extra={"error": str(exc), "error_type": type(exc).__name__},
        )
        return None

    return str(gids[0]) if gids else None


class IntakeResolveService:
    """Service for intake resolution operations.

    Handles:
    - Business resolution: office_phone -> GID via the shared DynamicIndexCache,
      with a build-on-miss through the universal resolution strategy
    - Contact resolution: email/phone -> contact within business scope
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def resolve_business(
        self,
        office_phone: str,
        vertical: str | None = None,
    ) -> BusinessResolveResponse:
        """Resolve a business of record by office phone.

        Three-outcome contract (ADR-resolve-cure-design-2026-08-08 D-2a):

        1. Fast path -- read an already-warm business index (O(1), no I/O).
        2. On a fast-path miss, the universal resolution strategy is
           authoritative: it serves the cached index if warm, otherwise builds
           one and caches it. Its result discriminates ABSENT (NOT_FOUND) from
           UNAVAILABLE (index unbuildable).
        3. Any GID that reaches the caller is positively asserted to be a member
           of the registry's business project before ``found=True`` is claimed.

        Args:
            office_phone: E.164 formatted phone number.
            vertical: Echoed onto the response. NOT part of the business index
                key -- the registry keys business on office_phone alone.

        Returns:
            BusinessResolveResponse with found=True (RESOLVED) or found=False
            (ABSENT).

        Raises:
            BusinessIndexUnavailableError: UNAVAILABLE -- the index could not be
                consulted or built. Fails closed (503), never ``found=false``.
            BusinessVerificationError: UNAVAILABLE -- a GID was resolved but
                could not be verified as a business of record.
        """
        # O(1) fast path via module-level function (testable via patch).
        gid = resolve_gid_from_index(office_phone)

        # Fast-path miss is not an answer -- the strategy is authoritative and
        # is the only surface that separates ABSENT from UNAVAILABLE.
        if gid is None:
            gid = await self._resolve_gid_build_on_miss(office_phone)

        if gid is None:
            return BusinessResolveResponse(
                found=False,
                office_phone=OfficePhone(office_phone) if office_phone else None,
            )

        # GID found - fetch task details from Asana.
        # opt_fields is UNCHANGED: TasksClient unions `memberships.project.gid`
        # into every narrowed fetch (clients/tasks.py _MINIMUM_OPT_FIELDS), so
        # the entity assertion below costs zero extra API calls.
        try:
            task_data = await self._client.tasks.get_async(
                gid,
                opt_fields=["name", "custom_fields", "memberships"],
            )
        except Exception as exc:
            logger.error(
                "business_task_fetch_failed",
                extra={"gid": gid, "error": str(exc), "error_type": type(exc).__name__},
            )
            # FAIL CLOSED. Returning `found=True` with an unverified bare GID is
            # the silent-wrong-outcome class on the business-of-record path.
            raise BusinessVerificationError("task_fetch_failed", gid) from exc

        self._assert_business_entity(gid, task_data)

        # Extract fields from task
        if isinstance(task_data, dict):
            name = task_data.get("name")
            custom_fields = task_data.get("custom_fields", [])
        else:
            name = getattr(task_data, "name", None)
            custom_fields = getattr(task_data, "custom_fields", []) or []

        company_id = _extract_custom_field(custom_fields, _COMPANY_ID_FIELD)

        # Check for subtasks (unit, contact_holder)
        has_unit = False
        has_contact_holder = False
        try:
            subtasks = await self._client.tasks.subtasks_async(
                gid,
                opt_fields=["name"],
            ).collect()
            subtask_list = self._to_list(subtasks)
            for st in subtask_list:
                st_name = st.get("name", "") if isinstance(st, dict) else getattr(st, "name", "")
                if st_name and "unit_holder" in st_name.lower():
                    has_unit = True
                if st_name and "contact_holder" in st_name.lower():
                    has_contact_holder = True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "business_subtask_check_failed",
                extra={"gid": gid, "error": str(exc)},
            )

        return BusinessResolveResponse(
            found=True,
            task_gid=gid,
            name=name,
            office_phone=OfficePhone(office_phone) if office_phone else None,
            vertical=vertical,
            company_id=company_id,
            has_unit=has_unit,
            has_contact_holder=has_contact_holder,
        )

    async def _resolve_gid_build_on_miss(self, office_phone: str) -> str | None:
        """Authoritative resolve: serve the cached index, or build it.

        Routed through ``UniversalResolutionStrategy.resolve`` rather than
        ``DynamicIndexCache.get_or_build`` (ADR D-4): only the strategy carries
        DataFrame acquisition, criterion validation, cascade-health gating, and
        the ``put`` back into the SHARED index cache -- so a build warms the
        index for subsequent requests instead of producing a throwaway. Using
        ``get_or_build`` directly would add a second writer to that singleton
        with different validation semantics.

        ``active_only=False`` (C-10, RATIFIED): an INACTIVE business still
        EXISTS. Filtering it out yields ``found=false``, which the calendly
        pipeline answers with CREATE -- re-opening DOUBLE-BUSINESSES for every
        churned office. That is the exact class this cure closes.

        Args:
            office_phone: E.164 phone number.

        Returns:
            GID string (RESOLVED) or ``None`` (ABSENT -- index consulted
            successfully, key genuinely missing).

        Raises:
            BusinessIndexUnavailableError: UNAVAILABLE.
        """
        from autom8_asana.services.universal_strategy import get_universal_strategy

        criterion = _business_criterion(office_phone)
        project_gid = _business_descriptor().primary_project_gid
        if not project_gid:
            raise BusinessIndexUnavailableError(
                f"registry descriptor for {_BUSINESS_ENTITY!r} carries no primary_project_gid"
            )

        strategy = get_universal_strategy(_BUSINESS_ENTITY)
        try:
            results = await strategy.resolve(
                criteria=[criterion],
                project_gid=project_gid,
                client=self._client,
                active_only=False,
            )
        except Exception as exc:
            logger.exception(
                "business_index_build_raised",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )
            raise BusinessIndexUnavailableError(
                f"resolution strategy raised {type(exc).__name__}"
            ) from exc

        if not results:
            raise BusinessIndexUnavailableError("resolution strategy returned no result slot")

        result = results[0]
        if result.error is None:
            return result.gid
        if result.error == "NOT_FOUND":
            # The index WAS consulted successfully; the key is genuinely absent.
            return None

        # INDEX_UNAVAILABLE / LOOKUP_ERROR / INVALID_CRITERIA / null slot: the
        # index could not be consulted. Fail closed.
        raise BusinessIndexUnavailableError(f"resolution strategy reported {result.error}")

    @staticmethod
    def _assert_business_entity(gid: str, task_data: Any) -> None:
        """Assert the resolved task is a member of the business project.

        Deleting the unit fallback removes the KNOWN wrong-entity path; this
        makes wrong-entity structurally unrepresentable on the way out. The
        expected project GID comes from the registry descriptor, never a literal.

        Args:
            gid: Resolved task GID.
            task_data: Task payload from ``tasks.get_async``.

        Raises:
            BusinessVerificationError: If the task is not a member of the
                business project (wrong entity, or memberships unavailable).
        """
        expected_gid = _business_descriptor().primary_project_gid
        if not expected_gid:
            raise BusinessVerificationError("business_project_gid_unknown", gid)

        if isinstance(task_data, dict):
            memberships = task_data.get("memberships") or []
        else:
            memberships = getattr(task_data, "memberships", None) or []

        observed: set[str] = set()
        for membership in memberships:
            project = (
                membership.get("project")
                if isinstance(membership, dict)
                else getattr(membership, "project", None)
            )
            if project is None:
                continue
            project_gid = (
                project.get("gid") if isinstance(project, dict) else getattr(project, "gid", None)
            )
            if project_gid:
                observed.add(str(project_gid))

        if expected_gid not in observed:
            logger.error(
                "business_entity_assertion_failed",
                extra={
                    "gid": gid,
                    "expected_project_gid": expected_gid,
                    "observed_project_gids": sorted(observed),
                },
            )
            raise BusinessVerificationError("not_in_business_project", gid)

    async def resolve_contact(
        self,
        business_gid: str,
        email: str | None = None,
        phone: str | None = None,
    ) -> ContactResolveResponse:
        """Resolve contact within a business scope.

        Algorithm (ADR-INT-002):
        1. email exact match on contact_email
        2. phone exact match on contact_phone
        3. No match -> found=False

        Name matching is deliberately excluded.

        Args:
            business_gid: Asana task GID of the business.
            email: Email for exact match.
            phone: E.164 phone for exact match.

        Returns:
            ContactResolveResponse with found=True/False and match details.
        """
        # Find the contact_holder subtask
        contact_holder_gid = await self._find_contact_holder(business_gid)
        if contact_holder_gid is None:
            return ContactResolveResponse(found=False)

        # Fetch all contacts under the contact_holder
        try:
            contacts_result = await self._client.tasks.subtasks_async(
                contact_holder_gid,
                opt_fields=["name", "custom_fields"],
            ).collect()
            contacts = self._to_list(contacts_result)
        except Exception as exc:
            logger.warning(
                "contact_fetch_failed",
                extra={
                    "business_gid": business_gid,
                    "contact_holder_gid": contact_holder_gid,
                    "error": str(exc),
                },
            )
            raise

        # Priority match: email first, then phone (ADR-INT-002)
        # Step 1: Email match
        if email:
            for contact in contacts:
                custom_fields = (
                    contact.get("custom_fields", [])
                    if isinstance(contact, dict)
                    else getattr(contact, "custom_fields", []) or []
                )
                contact_email = _extract_custom_field(custom_fields, _CONTACT_EMAIL_FIELD)
                if contact_email and contact_email.lower() == email.lower():
                    contact_gid = (
                        contact.get("gid")
                        if isinstance(contact, dict)
                        else getattr(contact, "gid", None)
                    )
                    contact_name = (
                        contact.get("name")
                        if isinstance(contact, dict)
                        else getattr(contact, "name", None)
                    )
                    contact_phone = _extract_custom_field(custom_fields, _CONTACT_PHONE_FIELD)
                    return ContactResolveResponse(
                        found=True,
                        contact_gid=contact_gid,
                        name=contact_name,
                        email=contact_email,
                        phone=LeadPhone(contact_phone) if contact_phone else None,
                        match_field="email",
                    )

        # Step 2: Phone match
        if phone:
            for contact in contacts:
                custom_fields = (
                    contact.get("custom_fields", [])
                    if isinstance(contact, dict)
                    else getattr(contact, "custom_fields", []) or []
                )
                contact_phone = _extract_custom_field(custom_fields, _CONTACT_PHONE_FIELD)
                if contact_phone and contact_phone == phone:
                    contact_gid = (
                        contact.get("gid")
                        if isinstance(contact, dict)
                        else getattr(contact, "gid", None)
                    )
                    contact_name = (
                        contact.get("name")
                        if isinstance(contact, dict)
                        else getattr(contact, "name", None)
                    )
                    contact_email = _extract_custom_field(custom_fields, _CONTACT_EMAIL_FIELD)
                    return ContactResolveResponse(
                        found=True,
                        contact_gid=contact_gid,
                        name=contact_name,
                        email=contact_email,
                        phone=LeadPhone(contact_phone),
                        match_field="phone",
                    )

        # Step 3: No match
        return ContactResolveResponse(found=False)

    async def _find_contact_holder(self, business_gid: str) -> str | None:
        """Find the contact_holder subtask GID for a business.

        Returns:
            Contact holder GID, or None if not found.
        """
        try:
            subtasks_result = await self._client.tasks.subtasks_async(
                business_gid,
                opt_fields=["name"],
            ).collect()
            subtasks = self._to_list(subtasks_result)
        except Exception as exc:
            logger.warning(
                "contact_holder_lookup_failed",
                extra={"business_gid": business_gid, "error": str(exc)},
            )
            raise

        for st in subtasks:
            st_name = st.get("name", "") if isinstance(st, dict) else getattr(st, "name", "")
            if st_name and "contact_holder" in st_name.lower():
                return st.get("gid") if isinstance(st, dict) else getattr(st, "gid", None)

        return None

    @staticmethod
    def _to_list(result: Any) -> list[Any]:
        """Convert Asana API result to a plain list."""
        if isinstance(result, list):
            return result
        if hasattr(result, "collect"):
            # AsyncIterator pattern -- can't await in sync static method,
            # but our tests return plain lists so this branch won't execute.
            return list(result)
        return list(result)


__all__ = [
    "BusinessIndexUnavailableError",
    "BusinessVerificationError",
    "IntakeResolveService",
    "is_valid_e164",
    "resolve_gid_from_index",
]
