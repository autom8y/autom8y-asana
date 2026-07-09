"""Service orchestration for the EBI OI-2 receipts route.

Threads an internal, redacted forwarding-lifecycle receipt onto a clinic's
Business task as an Asana comment. Three phases:

  1. RESOLVE  ``company_id`` -> the single Business ``task_gid`` via a
     store-independent LIVE ``tasks/search`` on the "Company ID" custom field,
     filtered to the Businesses project, FAIL-CLOSED on zero/ambiguous matches
     (the ``_business_gid_by_phone`` idiom adapted from Office Phone). This is
     the decisive design choice (FORK-R / ADR D-3): the cache-backed
     ``SearchService`` fails OPEN-as-not-found on a cold cache, which in a
     receipts route would silently drop a real clinic's receipt. Live search is
     authoritative on every call.

  2. DEDUP    scan the task's existing stories for THIS receipt's marker
     (the ``link_on_play`` marker-in-text pattern). Present ⇒ skip (idempotent).

  3. POST     ``create_comment`` (bot PAT) with the marker-prefixed body.

D12: the comment threads onto the TEAM's INTERNAL Business task -- never a
client-facing message. The provider adds no PII (the consumer already redacts).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.api.routes.receipts_models import ReceiptKind, ReceiptPostResponse
from autom8_asana.core.project_registry import BUSINESS_PROJECT

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# The Businesses-project discriminator: a Business task's Company ID lives here.
# Offer/Process/Commission rows can also carry a Company ID cascade, so the
# project membership is the deterministic filter (same anchor the resolver
# hierarchy walk and _business_gid_by_phone use).
_BUSINESSES_PROJECT_GID = BUSINESS_PROJECT  # "1200653012566782"

_MARKER_PREFIX = "RCPT"


class ReceiptResolutionError(RuntimeError):
    """Base for company-resolution failures (mapped to 4xx/503 in the route)."""


class CompanyIdFieldUnconfigured(ReceiptResolutionError):
    """The "Company ID" custom-field definition GID is not configured (OI-2b).

    Mapped to 503 -- an activation prerequisite, not a client error. The route
    refuses to guess a receiver rather than resolving against an unknown field.
    """


class CompanyNotResolved(ReceiptResolutionError):
    """No Business task carries this ``company_id`` (fail-closed 404).

    Never guess, never thread onto a fallback task.
    """


class CompanyAmbiguous(ReceiptResolutionError):
    """More than one Business task carries this ``company_id`` (fail-closed 409).

    Never pick a receiver silently.
    """

    def __init__(self, company_id: str, gids: list[str]) -> None:
        self.company_id = company_id
        self.gids = gids
        super().__init__(
            f"{len(gids)} Business tasks match company_id after the "
            f"Businesses-project discriminator; refusing to pick a receiver "
            f"silently. gids={gids}"
        )


class NoWorkspaceConfigured(ReceiptResolutionError):
    """No default workspace on the client (mapped to 503; refuse rather than guess)."""


def _marker(company_id: str, kind: str, bucket: str) -> str:
    """Deterministic idempotency marker embedded as a prefix line in the comment.

    Grammar ``RCPT|<company_id>|<kind>|<bucket>``. The three once-per-clinic
    lifecycle kinds use an empty bucket (idempotent forever); ``nudge`` uses a
    coarse UTC-date bucket so it re-fires once per clinic per day (the
    loud-recurring intent). See ADR D-5 / OI-2a watch.
    """
    return f"{_MARKER_PREFIX}|{company_id}|{kind}|{bucket}"


def _bucket_for(kind: str) -> str:
    """Bucket component of the marker (see :func:`_marker`)."""
    if kind == ReceiptKind.NUDGE.value:
        return datetime.now(UTC).strftime("%Y-%m-%d")
    return ""


class ReceiptsService:
    """Resolve -> dedup -> post orchestration for a single receipt."""

    def __init__(self, client: AsanaClient, *, company_id_field_gid: str) -> None:
        self._client = client
        self._company_id_field_gid = company_id_field_gid

    async def _resolve_business_gid(self, company_id: str) -> str:
        """Resolve ``company_id`` -> the single Business ``task_gid`` (fail-closed).

        Store-independent LIVE ``tasks/search`` keyed on the Company ID
        custom-field value, filtered to the Businesses project. Raises
        :class:`CompanyNotResolved` on zero matches (404),
        :class:`CompanyAmbiguous` on >1 (409),
        :class:`CompanyIdFieldUnconfigured` (503) when the field GID is absent,
        :class:`NoWorkspaceConfigured` (503) when no workspace is set.
        """
        if not self._company_id_field_gid:
            raise CompanyIdFieldUnconfigured(
                "ASANA_API_COMPANY_ID_FIELD_GID is not configured; refusing to "
                "resolve a receipt receiver against an unknown custom field "
                "(OI-2b activation prerequisite)."
            )

        workspace_gid = self._client.default_workspace_gid
        if not workspace_gid:
            raise NoWorkspaceConfigured(
                "no default workspace configured for the Business lookup; "
                "refusing rather than guessing a workspace."
            )

        data = await self._client.http.get(
            f"/workspaces/{workspace_gid}/tasks/search",
            params={
                f"custom_fields.{self._company_id_field_gid}.value": company_id,
                "opt_fields": "name,projects.gid",
            },
        )
        # http.get unwraps the {"data": ...} envelope; on a list result the
        # else-branch takes it, on a dict the .get does -- same dual-handling as
        # _business_gid_by_phone (defensive against envelope-shape drift).
        results = data.get("data", []) if isinstance(data, dict) else (data or [])
        matches = [
            t
            for t in results
            if any(
                (p or {}).get("gid") == _BUSINESSES_PROJECT_GID for p in (t.get("projects") or [])
            )
        ]
        if not matches:
            raise CompanyNotResolved(f"no Business task carries company_id={company_id!r}")
        if len(matches) > 1:
            raise CompanyAmbiguous(company_id, [str(m.get("gid")) for m in matches])
        gid = matches[0].get("gid")
        if gid is None:  # pragma: no cover - Asana always returns a gid on a hit
            raise CompanyNotResolved(
                f"matched Business for company_id={company_id!r} but it carries no gid"
            )
        return str(gid)

    async def thread_receipt(self, *, company_id: str, kind: str, body: str) -> ReceiptPostResponse:
        """Resolve, dedup, and post one receipt. Raises on Asana wire error.

        The marker is a hidden-ish prefix LINE on the comment text; the
        operator's glance still reads the receipt body below it.
        """
        business_gid = await self._resolve_business_gid(company_id)

        marker = _marker(company_id, kind, _bucket_for(kind))
        text = f"{marker}\n{body}"

        # Idempotency: list stories, skip if this marker already present.
        stories = await self._client.stories.list_for_task_async(
            business_gid, opt_fields=["text", "created_at"]
        ).collect()
        existing = next((s for s in stories if marker in (s.text or "")), None)
        if existing is not None:
            logger.info(
                "forwarding_receipt_skipped_duplicate",
                extra={"business_gid": business_gid, "kind": kind},
            )
            return ReceiptPostResponse(
                business_gid=business_gid,
                story_gid=existing.gid,
                outcome="skipped_duplicate",
            )

        story = await self._client.stories.create_comment_async(task=business_gid, text=text)
        logger.info(
            "forwarding_receipt_posted",
            extra={"business_gid": business_gid, "story_gid": story.gid, "kind": kind},
        )
        return ReceiptPostResponse(
            business_gid=business_gid,
            story_gid=story.gid,
            outcome="posted",
        )
