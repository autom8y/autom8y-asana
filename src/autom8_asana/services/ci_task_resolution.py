"""Shared CI-task (Calendar Integrations) resolution + current-stage read.

Extracted from :mod:`autom8_asana.services.receipts_service` so BOTH the
receipts route AND the S4 forwarding-stage backfill can reuse the SECOND
resolution (``company_id -> Calendar Integrations task gid``) and the
current-stage read WITHOUT importing the whole ``ReceiptsService`` (DIP: the
backfill would otherwise have to construct a receipts service just to reach two
resolvers). The behaviour is byte-identical to the S1 methods; ``ReceiptsService``
delegates to these functions, and the S1 receipts tests re-assert them
unchanged.

Purity note: these functions take the ``AsanaClient`` + the resolved GIDs/maps
as EXPLICIT parameters (rather than reaching through ``self``), so they carry no
service state and are directly testable. The Forwarding-Stage single-select
field lives on the Calendar Integrations task (NOT the Business task), so
advancing the stage needs this second resolution keyed on the same Company ID
custom-field value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autom8y_log import get_logger

from autom8_asana.core.project_registry import CALENDAR_INTEGRATIONS_PROJECT
from autom8_asana.domain.forwarding_stage import ForwardingStage

if TYPE_CHECKING:
    from autom8_asana import AsanaClient

logger = get_logger(__name__)

# The Forwarding-Stage single-select field lives on the Calendar Integrations
# task, NOT the Business task (§2 architectural crux). Advancing the stage needs
# a SECOND resolution (company_id -> CI task) filtered to this project.
_CALENDAR_INTEGRATIONS_PROJECT_GID = CALENDAR_INTEGRATIONS_PROJECT  # "1209442849265632"


@dataclass(frozen=True)
class UnknownStage:
    """Sentinel for a CI-task option GID that is NOT in the config option map.

    Deliberately NOT a ``ForwardingStage`` so ``StageTransitionValidator.evaluate``
    fail-CLOSES (its ``isinstance(current, ForwardingStage)`` guard rejects it as
    an unknown/unmapped option) rather than guessing an advance. Carries the raw
    GID for the LOUD log line.
    """

    option_gid: str


async def resolve_ci_task_gid(
    client: AsanaClient,
    company_id: str,
    *,
    company_id_field_gid: str,
) -> str | None:
    """Resolve ``company_id`` -> the single Calendar Integrations task gid.

    The SECOND resolution (§2): the same LIVE ``tasks/search`` idiom as the
    Business resolution but filtered to the Calendar Integrations project instead
    of the Businesses project (keying on the SAME Company ID cascade value).
    Best-effort: returns ``None`` on 0 or >1 matches (never guesses a receiver),
    logging for operator visibility. Guest-PAT scope honored (task/project-scope
    ``tasks/search``; no workspace-level call).
    """
    workspace_gid = client.default_workspace_gid
    if not workspace_gid:
        logger.info(
            "stage_ci_task_no_workspace",
            extra={"company_id": company_id},
        )
        return None

    data = await client.http.get(
        f"/workspaces/{workspace_gid}/tasks/search",
        params={
            f"custom_fields.{company_id_field_gid}.value": company_id,
            "opt_fields": "name,projects.gid",
        },
    )
    results = data.get("data", []) if isinstance(data, dict) else (data or [])
    matches = [
        t
        for t in results
        if any(
            (p or {}).get("gid") == _CALENDAR_INTEGRATIONS_PROJECT_GID
            for p in (t.get("projects") or [])
        )
    ]
    if len(matches) != 1:
        logger.info(
            "stage_ci_task_not_resolved",
            extra={"company_id": company_id, "match_count": len(matches)},
        )
        return None
    gid = matches[0].get("gid")
    return str(gid) if gid is not None else None


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
    "UnknownStage",
    "read_current_stage",
    "resolve_ci_task_gid",
]
