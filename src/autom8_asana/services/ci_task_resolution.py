"""Shared CI-task (Calendar Integrations) resolution + current-stage read.

Extracted from :mod:`autom8_asana.services.receipts_service` so BOTH the
receipts route AND the S4 forwarding-stage backfill can reuse the SECOND
resolution (``company_id -> Calendar Integrations task gid``) and the
current-stage read WITHOUT importing the whole ``ReceiptsService`` (DIP: the
backfill would otherwise have to construct a receipts service just to reach two
resolvers). ``ReceiptsService`` delegates to these functions.

Join-key repair (entity-descend ruling, 2026-07-09): the original extraction
resolved the CI task by the SAME Company-ID workspace search filtered to the
Calendar Integrations project. That join is FALSIFIED -- the Company ID custom
field is NOT on the Calendar Integrations project (S4 verifier BLOCK), so the
search could never return a CI row. The ruled replacement descends the entity
tree from the Business (dna_holder) card instead: Business -> subtasks (the
"{Clinic} PLAYS/REQUESTS" holder) -> subtasks (the PLAY tasks, multi-homed into
Calendar Integrations), filtered by PROJECT MEMBERSHIP, never by name. The
public contract is unchanged: same signature, ``None`` on zero/ambiguous
(fail-closed).

Purity note: these functions take the ``AsanaClient`` + the resolved GIDs/maps
as EXPLICIT parameters (rather than reaching through ``self``), so they carry no
service state and are directly testable. The Forwarding-Stage single-select
field lives on the Calendar Integrations task (NOT the Business task), so
advancing the stage needs this second resolution keyed on the same Company ID
custom-field value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from autom8y_log import get_logger

from autom8_asana.core.project_registry import BUSINESS_PROJECT, CALENDAR_INTEGRATIONS_PROJECT
from autom8_asana.domain.forwarding_stage import ForwardingStage

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# The Forwarding-Stage single-select field lives on the Calendar Integrations
# task, NOT the Business task (§2 architectural crux). Advancing the stage needs
# a SECOND resolution (company_id -> CI task) anchored on this project.
_CALENDAR_INTEGRATIONS_PROJECT_GID = CALENDAR_INTEGRATIONS_PROJECT  # "1209442849265632"

# The Businesses-project discriminator: a Business task's Company ID lives here.
# The entity-descend join starts at the Business (dna_holder) card -- the SAME
# proven first-hop the receipts comment leg uses (_resolve_business_gid idiom).
_BUSINESSES_PROJECT_GID = BUSINESS_PROJECT  # "1200653012566782"

# Bounded descend (the S4 cap-abort discipline): the ruled join is exactly two
# hops (Business -> "{Clinic} PLAYS/REQUESTS" holder -> PLAY task), so depth is
# STRUCTURALLY capped at 2. Each subtask listing requests ONE page of at most
# _SUBTASK_PAGE_CAP rows; a FULL page cannot prove completeness, so it aborts
# LOUDLY (mirror of the backfill's DenominatorCapError: row_count == cap =>
# cap_hit) rather than resolving against a truncated denominator.
_DESCEND_DEPTH_CAP = 2
_SUBTASK_PAGE_CAP = 100  # Asana's max page size


class SubtaskPageCapExceeded(RuntimeError):
    """A subtask listing during the entity descend filled the page cap.

    Fail-LOUD truncation guard (the S4 cap-abort discipline): a full page means
    the child set MAY be incomplete, and an exactly-one resolution over an
    incomplete set could silently pick the wrong receiver. Callers that must not
    throw (the receipts stage-write leg) swallow-and-log via their no-throw
    wrapper; the backfill aborts the run, mirroring ``DenominatorCapError``.
    """

    def __init__(self, parent_gid: str, depth: int, cap: int) -> None:
        self.parent_gid = parent_gid
        self.depth = depth
        self.cap = cap
        super().__init__(
            f"subtask listing under task {parent_gid} (depth {depth}) filled the "
            f"page cap ({cap}); refusing to resolve against a possibly-truncated "
            f"child set"
        )


@dataclass(frozen=True)
class UnknownStage:
    """Sentinel for a CI-task option GID that is NOT in the config option map.

    Deliberately NOT a ``ForwardingStage`` so ``StageTransitionValidator.evaluate``
    fail-CLOSES (its ``isinstance(current, ForwardingStage)`` guard rejects it as
    an unknown/unmapped option) rather than guessing an advance. Carries the raw
    GID for the LOUD log line.
    """

    option_gid: str


def _rows(data: Any) -> list[dict[str, Any]]:
    """Dual-handle a ``{"data": [...]}`` envelope and a bare list (shape drift)."""
    raw = data.get("data", []) if isinstance(data, dict) else (data or [])
    return [r for r in raw if isinstance(r, dict)]


def _is_ci_member(row: dict[str, Any]) -> bool:
    """Membership is the filter -- NEVER task names (name-free by ruling)."""
    return any(
        (p or {}).get("gid") == _CALENDAR_INTEGRATIONS_PROJECT_GID
        for p in (row.get("projects") or [])
    )


async def _list_subtasks(
    client: AsanaClient,
    task_gid: str,
    *,
    depth: int,
) -> list[dict[str, Any]]:
    """One bounded page of subtasks (task-scope GET; guest-PAT safe).

    429s are retried with ``Retry-After`` backoff by the transport
    (``AsanaHttpClient._request``), same as every other GET here. A FULL page
    (row_count == cap) cannot prove completeness -> loud abort (never resolve
    against a truncated child set).
    """
    data = await client.http.get(
        f"/tasks/{task_gid}/subtasks",
        params={"opt_fields": "projects.gid", "limit": _SUBTASK_PAGE_CAP},
    )
    rows = _rows(data)
    if len(rows) >= _SUBTASK_PAGE_CAP:
        raise SubtaskPageCapExceeded(task_gid, depth, _SUBTASK_PAGE_CAP)
    return rows


async def resolve_ci_task_gid(
    client: AsanaClient,
    company_id: str,
    *,
    company_id_field_gid: str,
) -> str | None:
    """Resolve ``company_id`` -> the single Calendar Integrations task gid.

    The SECOND resolution (§2), via the ruled ENTITY-DESCEND join (the prior
    Company-ID-search-filtered-to-CI-project join is FALSIFIED: the Company ID
    field is NOT on the Calendar Integrations project, so it matched nothing):

    1. Resolve ``company_id`` -> the single Business (dna_holder) task via the
       PROVEN LIVE ``tasks/search`` on the Company ID custom field, filtered to
       the Businesses project (the ``_resolve_business_gid`` idiom).
    2. DESCEND the entity tree in reverse (like the resolver goes UP, go DOWN):
       list the Business task's subtasks (depth 1: the "{Clinic} PLAYS/REQUESTS"
       holder by convention), then each child's subtasks (depth 2: the PLAY
       tasks, multi-homed into Calendar Integrations), collecting every
       descendant whose project memberships include the Calendar Integrations
       project. Depth-1 children that are themselves CI members are ALSO
       collected (robustness when a clinic links the PLAY directly).
    3. Exactly ONE collected match -> its gid. Zero -> ``None`` (fail-closed,
       never guesses a receiver). More than one -> ambiguous refuse (``None``,
       counted in the log line).

    Bounded: depth is structurally capped at ``_DESCEND_DEPTH_CAP`` (2) and each
    listing is one page capped at ``_SUBTASK_PAGE_CAP`` with a LOUD
    :class:`SubtaskPageCapExceeded` abort on a full page. Guest-PAT scope
    honored (task/project-scope ``tasks/search`` + ``/tasks/{gid}/subtasks``; no
    workspace-level listing). 429s back off on ``Retry-After`` in the transport.
    """
    workspace_gid = client.default_workspace_gid
    if not workspace_gid:
        logger.info(
            "stage_ci_task_no_workspace",
            extra={"company_id": company_id},
        )
        return None

    # ── 1. company_id -> Business (dna_holder) card: the PROVEN half ───────
    data = await client.http.get(
        f"/workspaces/{workspace_gid}/tasks/search",
        params={
            f"custom_fields.{company_id_field_gid}.value": company_id,
            "opt_fields": "name,projects.gid",
        },
    )
    businesses = [
        t
        for t in _rows(data)
        if any((p or {}).get("gid") == _BUSINESSES_PROJECT_GID for p in (t.get("projects") or []))
    ]
    if len(businesses) != 1 or businesses[0].get("gid") is None:
        logger.info(
            "stage_ci_business_not_resolved",
            extra={"company_id": company_id, "match_count": len(businesses)},
        )
        return None
    business_gid = str(businesses[0]["gid"])

    # ── 2. DESCEND (membership-filtered, depth-capped at 2) ────────────────
    matches: set[str] = set()
    children = await _list_subtasks(client, business_gid, depth=1)
    for child in children:
        child_gid = child.get("gid")
        if child_gid is None:
            continue
        if _is_ci_member(child):
            matches.add(str(child_gid))
        # Depth 2 == _DESCEND_DEPTH_CAP: grandchildren are collected but NEVER
        # descended into further (a CI member at depth 3 is out of scope).
        grandchildren = await _list_subtasks(client, str(child_gid), depth=_DESCEND_DEPTH_CAP)
        for grandchild in grandchildren:
            grandchild_gid = grandchild.get("gid")
            if grandchild_gid is not None and _is_ci_member(grandchild):
                matches.add(str(grandchild_gid))

    # ── 3. exactly-one or fail-closed ───────────────────────────────────────
    if len(matches) > 1:
        logger.warning(
            "stage_ci_task_ambiguous",
            extra={
                "company_id": company_id,
                "business_gid": business_gid,
                "match_count": len(matches),
            },
        )
        return None
    if not matches:
        logger.info(
            "stage_ci_task_not_resolved",
            extra={"company_id": company_id, "business_gid": business_gid, "match_count": 0},
        )
        return None
    return next(iter(matches))


async def read_current_stage(
    client: AsanaClient,
    ci_gid: str,
    *,
    field_gid: str,
    option_gids: dict[str, str],
) -> ForwardingStage | UnknownStage | None:
    """Read the CI task's current Forwarding-Stage value.

    Returns ``None`` when the field is unset (a fresh clinic), a
    :class:`ForwardingStage` when the read option GID maps into the config option
    map, or an :class:`UnknownStage` sentinel when the task carries an option GID
    ABSENT from the config map -- so the validator fail-CLOSES rather than
    guessing an advance (T-M5 / T-W6 fail-closed).
    """
    raw = await client.tasks.get_async(ci_gid, raw=True, opt_fields=["custom_fields"])
    custom_fields = (raw or {}).get("custom_fields") or []
    for cf in custom_fields:
        if (cf or {}).get("gid") != field_gid:
            continue
        enum_value = (cf or {}).get("enum_value")
        if not enum_value:
            return None  # field present but unset
        option_gid = enum_value.get("gid")
        if not option_gid:
            return None
        # Invert the config map: option GID -> stage value.
        for stage_value, cfg_gid in option_gids.items():
            if cfg_gid == option_gid:
                return ForwardingStage(stage_value)
        # Present option GID not in our config map -> unknown; fail closed.
        return UnknownStage(option_gid)
    return None  # field not on the task at all


__all__ = [
    "SubtaskPageCapExceeded",
    "UnknownStage",
    "read_current_stage",
    "resolve_ci_task_gid",
]
