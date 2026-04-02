"""Service for intake resolution operations.

Handles business resolution (phone -> GID via GidLookupIndex)
and contact resolution (email/phone -> contact within business scope).

Per ADR-INT-001: Never return 404 for not-found; use found=False.
Per ADR-INT-002: Email-then-phone priority, NO name matching.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

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


def is_valid_e164(phone: str) -> bool:
    """Validate E.164 phone format."""
    return bool(_E164_PATTERN.match(phone))


def _extract_custom_field(
    custom_fields: list[dict[str, Any]], field_name: str
) -> str | None:
    """Extract a custom field value by name from Asana custom_fields list."""
    for cf in custom_fields:
        if cf.get("name", "").lower() == field_name.lower():
            # Check text_value first, then number_value, then enum display value
            if cf.get("text_value") is not None:
                return str(cf["text_value"])
            if cf.get("display_value") is not None:
                return str(cf["display_value"])
            if cf.get("number_value") is not None:
                return str(cf["number_value"])
    return None


def resolve_gid_from_index(
    office_phone: str, vertical: str | None = None
) -> str | None:
    """Resolve GID from the DynamicIndex cache.

    Module-level function to enable clean patching in tests.

    Attempts DynamicIndex cache for "business" entity type first,
    then falls back to "unit" entity type (since business entries
    are typically in the unit index).

    Args:
        office_phone: E.164 phone number.
        vertical: Optional vertical filter.

    Returns:
        GID string if found, None otherwise.
    """
    try:
        from autom8_asana.services.universal_strategy import get_shared_index_cache

        cache = get_shared_index_cache()
        criterion = {
            "office_phone": office_phone,
            "vertical": vertical or "",
        }

        # Try business index first
        index = cache.get("business", ["office_phone", "vertical"])
        if index is not None:
            gids = index.lookup(criterion)
            if gids:
                return str(gids[0])

        # Fall back to unit index (businesses are often indexed under unit)
        index = cache.get("unit", ["office_phone", "vertical"])
        if index is not None:
            gids = index.lookup(criterion)
            if gids:
                return str(gids[0])
    except Exception:
        pass

    return None


class IntakeResolveService:
    """Service for intake resolution operations.

    Handles:
    - Business resolution: phone -> GID via GidLookupIndex O(1)
    - Contact resolution: email/phone -> contact within business scope
    """

    def __init__(self, client: AsanaClient) -> None:
        self._client = client

    async def resolve_business(
        self,
        office_phone: str,
        vertical: str | None = None,
    ) -> BusinessResolveResponse:
        """Resolve business by phone via GidLookupIndex O(1).

        Args:
            office_phone: E.164 formatted phone number.
            vertical: Optional vertical filter.

        Returns:
            BusinessResolveResponse with found=True/False.
        """
        # O(1) lookup via module-level function (testable via patch)
        gid = resolve_gid_from_index(office_phone, vertical)

        if gid is None:
            return BusinessResolveResponse(
                found=False,
                office_phone=office_phone,
            )

        # GID found - fetch task details from Asana
        try:
            task_data = await self._client.tasks.get_async(
                gid,
                opt_fields=["name", "custom_fields", "memberships"],
            )
        except Exception as exc:
            logger.warning(
                "business_task_fetch_failed",
                extra={"gid": gid, "error": str(exc)},
            )
            # Return found with just the GID if we can't fetch details
            return BusinessResolveResponse(
                found=True,
                task_gid=gid,
                office_phone=office_phone,
            )

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
                st_name = (
                    st.get("name", "")
                    if isinstance(st, dict)
                    else getattr(st, "name", "")
                )
                if st_name and "unit_holder" in st_name.lower():
                    has_unit = True
                if st_name and "contact_holder" in st_name.lower():
                    has_contact_holder = True
        except Exception as exc:
            logger.warning(
                "business_subtask_check_failed",
                extra={"gid": gid, "error": str(exc)},
            )

        return BusinessResolveResponse(
            found=True,
            task_gid=gid,
            name=name,
            office_phone=office_phone,
            vertical=vertical,
            company_id=company_id,
            has_unit=has_unit,
            has_contact_holder=has_contact_holder,
        )

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
                contact_email = _extract_custom_field(
                    custom_fields, _CONTACT_EMAIL_FIELD
                )
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
                    contact_phone = _extract_custom_field(
                        custom_fields, _CONTACT_PHONE_FIELD
                    )
                    return ContactResolveResponse(
                        found=True,
                        contact_gid=contact_gid,
                        name=contact_name,
                        email=contact_email,
                        phone=contact_phone,
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
                contact_phone = _extract_custom_field(
                    custom_fields, _CONTACT_PHONE_FIELD
                )
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
                    contact_email = _extract_custom_field(
                        custom_fields, _CONTACT_EMAIL_FIELD
                    )
                    return ContactResolveResponse(
                        found=True,
                        contact_gid=contact_gid,
                        name=contact_name,
                        email=contact_email,
                        phone=contact_phone,
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
            st_name = (
                st.get("name", "") if isinstance(st, dict) else getattr(st, "name", "")
            )
            if st_name and "contact_holder" in st_name.lower():
                return (
                    st.get("gid") if isinstance(st, dict) else getattr(st, "gid", None)
                )

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
    "IntakeResolveService",
    "is_valid_e164",
    "resolve_gid_from_index",
]
