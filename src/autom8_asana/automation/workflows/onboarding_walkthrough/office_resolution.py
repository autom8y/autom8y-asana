"""Hierarchy-first office-guid / task->business resolver (the entity-resolution primitive).

Replaces the lossy ``office_phone -> workspace /tasks/search`` bridge that the walkthrough
posters share with an **authoritative ancestor walk**: PLAY -> follow ``parent.gid`` upward
-> the FIRST ancestor that is a ``BUSINESS_PROJECT`` member -> read its ``Company ID`` custom
field. Phone survives only as a labeled fallback + optional shadow crosscheck.

Design of record: ADR-entity-resolution-primitive-2026-07-08 + TDD-entity-resolution-
primitive-2026-07-08. The felt bug: Total Wellness Center PLAY ``1215766139321621`` refused
``ContactCardBusinessAmbiguous`` because ``+13036277995`` aliases the BUSINESS card
``1214127219419742`` AND the opportunity card ``1214420107547660`` -- same practice, two
Business-project matches, correct fail-closed refuse. A PLAY has exactly ONE business
ancestor; the parent chain is the ownership relation, immune to phone aliasing.

**Store-independence is the primary architecture** (the load-bearing constraint). The
walkthrough runs plain ``AsanaClient()`` with NO ``UnifiedTaskStore``, and
``HierarchyIndex.get_ancestor_chain`` returns ``[]`` for an unregistered gid
(hierarchy.py:175) -- the warm-index walk is structurally unavailable here. So the resolver
does a **direct bounded ``parent.gid`` traversal**: it fetches each ancestor live via
``tasks.get_async(raw=True)`` and follows ``parent.gid`` upward, bounded by ``max_depth``
(which also bounds any parent cycle). What it REUSES rather than re-mints is the identity
substrate -- the registry-typed discriminator (``get_registry().get_by_gid``), the
``BUSINESS_PROJECT`` constant, and the raw Asana node shape -- NOT a phone bridge or a
data-service dependency.

The discriminator is **registry-typed**: ``get_registry().get_by_gid(project_gid)``
(entity_registry.py:299) with ``BUSINESS_PROJECT`` (project_registry.py:21) as the fallback
literal. At-most-one BUSINESS ancestor is asserted (LOUD ``BusinessResolutionAmbiguous``
rather than a silent first-match, mirroring ``contact_synthesis.py:406-410``). Depth-
exhaustion and no-business-ancestor raise DISTINCT codes.

Cache pinning (FORK-2): the walk's ``tasks.get_async(opt_fields=[... projects.gid,
custom_fields ...])`` reads are subject to the cross-reader projection-coverage starvation
(DEFECT-taskcache-cross-reader-section-starvation-2026-07-08). Until SIBLING-1's hit-path
coverage check lands fleet-wide, the resolver's CALLERS construct
``AsanaClient(cache_provider=NullCacheProvider())``. This module makes no cache-provider
decision of its own; it walks whatever client it is handed.

Ships BUSINESS-only with a private ``project_gid`` seam (FORK-1); the
``EntityType|EntityCategory`` target generalization is NOT built speculatively (YAGNI until
a second caller ships).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from autom8_asana.core.entity_registry import get_registry
from autom8_asana.core.project_registry import BUSINESS_PROJECT

if TYPE_CHECKING:
    from autom8_asana.client import AsanaClient

__all__ = [
    "BusinessResolution",
    "BusinessResolutionAmbiguous",
    "BusinessResolutionDepthExhausted",
    "BusinessResolutionMissingNoBusiness",
    "DivergentOfficeResolution",
    "resolve_business_gid",
    "resolve_office_guid",
]

# Projection carrying BOTH the walk edge (``parent.gid``) AND the discriminator input
# (``projects.gid``) AND the Company ID reader input (``custom_fields``) in one fetch.
# ``projects.gid`` is the proven-live projection the phone bridge already uses to filter
# Business-project members (contact_synthesis.py:396,402).
_WALK_OPT_FIELDS = [
    "gid",
    "name",
    "parent.gid",
    "projects.gid",
    "custom_fields.name",
    "custom_fields.display_value",
]


@dataclass(frozen=True)
class BusinessResolution:
    """Typed frozen result of an office resolution (ADR §Decision item 1).

    ``method`` is the provenance tag -- an observable fleet signal: a rising
    ``method="phone"`` rate on well-parented offices = hidden hierarchy gaps, surfaced
    not silent (DEFER-WATCH-1). ``ancestor_depth`` is the hop count walked from the PLAY
    to the matched Business (0 = the task itself was the Business). ``candidates`` is the
    ambiguity set carried on a LOUD refusal (never a silent first-match).
    """

    business_gid: str | None
    company_id: str | None
    method: Literal["hierarchy", "phone"]
    ancestor_depth: int | None
    candidates: tuple[str, ...] = field(default_factory=tuple)


class BusinessResolutionAmbiguous(RuntimeError):
    """>1 BUSINESS ancestor found in the walked chain (or >1 phone match).

    NEVER pick a receiver silently -- refuse LOUD with the full candidate set. Mirrors
    ``contact_synthesis.ContactCardBusinessAmbiguous`` (:406-410). NOT transient; callers
    must fail closed. Carries the candidate gid set as a structured ``.candidates`` tuple
    (TDD §2.1) so a programmatic consumer need not parse the message string.
    """

    def __init__(self, message: str, *, candidates: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.candidates: tuple[str, ...] = tuple(candidates)


class BusinessResolutionMissingNoBusiness(RuntimeError):
    """The ancestor chain ENDED (a null parent) with no BUSINESS ancestor found.

    Distinct from :class:`BusinessResolutionDepthExhausted` (FORK-3): an orphan / mis-
    parented PLAY is diagnosably different from a chain that ran past ``max_depth`` with
    a live parent still pending. NOT transient; callers must fail closed.
    """


class BusinessResolutionDepthExhausted(RuntimeError):
    """``max_depth`` was reached with a non-null parent still pending (FORK-3 distinct code).

    A chain deeper than the bound -- as opposed to a chain that simply ended without a
    Business member. NOT transient; callers must fail closed.
    """


class DivergentOfficeResolution(RuntimeError):
    """The optional phone crosscheck disagreed with the hierarchy resolution (LOUD tripwire).

    Off by default (``phone_crosscheck=False``). During rollout a shadow crosscheck proves
    hierarchy ⊇ phone on every ACTIVE office; a divergence here is a hard signal that the
    two resolvers point at different Businesses. NOT transient; callers must fail closed.
    """


def _as_node_dict(node: Any) -> dict[str, Any]:
    """Coerce a ``tasks.get_async`` result to the walk node dict.

    ``get_async(raw=True)`` already returns the raw Asana JSON dict (clients/tasks.py:271);
    a defensive coercion keeps the walk robust to a caller that hands back a Task model.
    """
    if isinstance(node, dict):
        return node
    data = getattr(node, "model_dump", None)
    if callable(data):
        dumped = data()
        if isinstance(dumped, dict):
            return dumped
    return {
        "gid": getattr(node, "gid", None),
        "parent": getattr(node, "parent", None),
        "projects": getattr(node, "projects", None),
        "custom_fields": getattr(node, "custom_fields", None),
    }


def _parent_gid(node: dict[str, Any]) -> str | None:
    """Extract the immediate ``parent.gid`` from a walk node dict, or ``None`` at the root."""
    parent = node.get("parent")
    if parent and isinstance(parent, dict):
        gid = parent.get("gid")
        return str(gid) if gid is not None else None
    return None


def _matches_project(node: dict[str, Any], project_gid: str) -> bool:
    """Registry-typed discriminator: is this node a member of ``project_gid``?

    For each of the node's ``projects[].gid``, look up the entity descriptor via
    ``get_registry().get_by_gid(pgid)`` (entity_registry.py:299). A match iff the
    descriptor's ``primary_project_gid == project_gid`` (auto-tracks any future BUSINESS
    project-GID move). When the registry returns ``None`` for a project gid (an unregistered
    project), fall back to the raw literal compare ``pgid == project_gid`` -- so a bare
    ``BUSINESS_PROJECT`` membership still matches even off-registry.
    """
    registry = get_registry()
    for proj in node.get("projects") or []:
        pgid = (proj or {}).get("gid") if isinstance(proj, dict) else None
        if pgid is None:
            continue
        descriptor = registry.get_by_gid(pgid)
        if descriptor is not None:
            if descriptor.primary_project_gid == project_gid:
                return True
        elif pgid == project_gid:
            return True
    return False


def _company_id_from_node(node: dict[str, Any]) -> str | None:
    """Read the ``Company ID`` custom field (the office guid) off a walk node dict.

    Dict-native mirror of ``template_comment._company_id_from_task`` (which reads a Task
    model's attribute); the walk fetches ``raw=True`` dicts, so the reader is dict-shaped.
    """
    for cf in node.get("custom_fields") or []:
        if not isinstance(cf, dict):
            continue
        if cf.get("name") == "Company ID":
            company_id = cf.get("display_value")
            return str(company_id) if company_id is not None else None
    return None


def _office_phone_from_node(node: dict[str, Any]) -> str | None:
    """Read the ``Office Phone`` custom field off a walk node dict (crosscheck input)."""
    for cf in node.get("custom_fields") or []:
        if not isinstance(cf, dict):
            continue
        if cf.get("name") == "Office Phone":
            phone = cf.get("display_value")
            return str(phone) if phone is not None else None
    return None


async def resolve_business_gid(
    asana_client: AsanaClient,
    *,
    task_gid: str,
    project_gid: str = BUSINESS_PROJECT,
    max_depth: int = 5,
    phone_crosscheck: bool = False,
) -> BusinessResolution:
    """Authoritative walk: task -> first ancestor in ``project_gid`` -> that node.

    Direct bounded ``parent.gid`` traversal from live reads (store-independent by
    construction; the warm-index ``get_ancestor_chain`` needs a ``UnifiedTaskStore`` the
    walkthrough lacks). Returns ``method="hierarchy"`` on success. On no-business-
    ancestor, the CALLER decides fallback-vs-refuse (this fn does not silently phone-
    fallback) -- it returns ``business_gid=None``.

    Args:
        asana_client: the (cache-provider-pinned) Asana client to walk with.
        task_gid: the starting PLAY task gid.
        project_gid: the membership discriminator; ``BUSINESS_PROJECT`` ships (FORK-1 seam).
        max_depth: the ancestor-walk bound (hops above the starting task).
        phone_crosscheck: when True, after a hierarchy success also resolve via the phone
            bridge and assert equality; disagreement raises :class:`DivergentOfficeResolution`.

    Returns:
        A :class:`BusinessResolution`. ``business_gid`` is None when the chain ended with no
        Business member (the caller falls back or refuses).

    Raises:
        BusinessResolutionAmbiguous: >1 ancestor in ``project_gid`` in the walked chain
            (assert-at-most-one; FORK-3).
        BusinessResolutionDepthExhausted: ``max_depth`` reached with a live parent still
            pending (distinct from no-business-ancestor; FORK-3).
        DivergentOfficeResolution: ``phone_crosscheck`` on and the phone bridge disagreed.
    """
    cur: str | None = task_gid
    depth = 0
    parent_gid: str | None = None
    # Each match carries (gid, node_dict, depth_at_match) so the resolution can read the
    # Company ID off the matched Business node and report the hop count.
    matches: list[tuple[str, dict[str, Any], int]] = []

    while cur is not None and depth <= max_depth:
        raw = await asana_client.tasks.get_async(cur, opt_fields=_WALK_OPT_FIELDS, raw=True)
        node = _as_node_dict(raw)
        # Direct bounded traversal: the shipped HierarchyIndex.get_ancestor_chain needs a warm
        # UnifiedTaskStore the walkthrough never constructs (hierarchy.py:175 returns [] for an
        # unregistered gid), so we walk parent.gid directly. ``max_depth`` bounds any cycle.
        # Ensure a "gid" key is present for the match read below.
        node.setdefault("gid", cur)

        if _matches_project(node, project_gid):
            node_gid = node.get("gid")
            matches.append((str(node_gid) if node_gid is not None else cur, node, depth))

        parent_gid = _parent_gid(node)
        if parent_gid is None:
            cur = None
            break
        cur = parent_gid
        depth += 1

    if len(matches) > 1:
        candidate_gids = tuple(g for g, _, _ in matches)
        raise BusinessResolutionAmbiguous(
            f"{len(matches)} ancestors of PLAY {task_gid} are members of project "
            f"{project_gid}; refusing to pick a receiver silently. "
            f"candidates={list(candidate_gids)}",
            candidates=candidate_gids,
        )

    if len(matches) == 1:
        matched_gid, matched_node, depth_at_match = matches[0]
        resolution = BusinessResolution(
            business_gid=matched_gid,
            company_id=_company_id_from_node(matched_node),
            method="hierarchy",
            ancestor_depth=depth_at_match,
        )
        if phone_crosscheck:
            await _assert_phone_agrees(asana_client, task_gid, resolution)
        return resolution

    # No match. Distinguish depth-exhaustion (a live parent still pending past the bound)
    # from a genuinely terminated chain with no Business member (FORK-3).
    if parent_gid is not None:
        raise BusinessResolutionDepthExhausted(
            f"walked {max_depth} ancestors above PLAY {task_gid} without reaching a member "
            f"of project {project_gid}; the chain still has a live parent "
            f"({parent_gid}) -- depth-exhausted, not orphaned."
        )
    return BusinessResolution(
        business_gid=None,
        company_id=None,
        method="hierarchy",
        ancestor_depth=None,
    )


async def _assert_phone_agrees(
    asana_client: AsanaClient,
    task_gid: str,
    resolution: BusinessResolution,
) -> None:
    """Shadow crosscheck: resolve via the phone bridge and assert it agrees (LOUD tripwire).

    Reuses ``contact_synthesis._read_office_phone`` + ``_business_gid_by_phone`` (the S2S
    surface's only tool; LIFTED not deleted). A disagreement raises
    :class:`DivergentOfficeResolution`. Import is local to avoid a module-load cycle with
    ``contact_synthesis`` (which does not import this module at load time, but the callers
    cross-import; keeping it local is defensive).
    """
    from autom8_asana.automation.workflows.onboarding_walkthrough.contact_synthesis import (
        _business_gid_by_phone,
        _read_office_phone,
    )

    office_phone = await _read_office_phone(asana_client, task_gid)
    if not office_phone:
        return
    phone_gid = await _business_gid_by_phone(asana_client, office_phone)
    if phone_gid is not None and phone_gid != resolution.business_gid:
        raise DivergentOfficeResolution(
            f"hierarchy resolved PLAY {task_gid} to Business {resolution.business_gid} but the "
            f"phone bridge resolved {phone_gid}; the two office resolvers disagree -- refusing "
            "to attest a tenant target the resolvers cannot agree on."
        )


async def resolve_office_guid(
    asana_client: AsanaClient,
    *,
    task_gid: str,
    **kw: Any,
) -> str | None:
    """Resolve the office guid (the ``Company ID`` custom field) via the hierarchy walk.

    ``resolve_business_gid`` then read Company ID off the resolved Business node (which the
    walk already carried in the same fetch). Returns ``None`` when the walk finds no Business
    ancestor -- the caller decides fallback-vs-refuse. Additional keyword arguments (e.g.
    ``max_depth``, ``project_gid``, ``phone_crosscheck``) pass through to the walk.
    """
    resolution = await resolve_business_gid(asana_client, task_gid=task_gid, **kw)
    return resolution.company_id
