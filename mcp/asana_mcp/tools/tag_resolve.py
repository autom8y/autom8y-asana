"""Tag name->GID resolution for the composite write surface (WS-B2).

The composite write tool (``composite_write.py``) requires a ``tag_gid``, but agents
and humans think in tag NAMES. This module is the SIDECAR half of the dual-key fix
(the SATELLITE half is the #246 ``GET /api/v1/tags?name=`` read surface): it resolves
an exact tag name to its GID through the SAME S2S client/auth path the sidecar already
uses (``ctx.http``), then the unchanged add_tag verb consumes the resolved GID.

HARD FENCE (WS-B2): resolution is READ-ONLY. It adds NO write verb. The only write
remains the existing add_tag (``POST /api/v1/tasks/{gid}/tags``). Creating tags (TAG-2)
stays out of scope (defer-watch).

Three honesty properties this module owns:

* Page-cap honesty (binding PT-05 #1). The satellite name scan caps at 100 pages
  (``tag_service.py:51`` ``_MAX_NAME_SCAN_PAGES``). On a NAME query the #246 route
  returns ``has_more=False`` for BOTH a genuine miss AND a cap-truncated scan --
  truncation is satellite-log-only (``tag_service.py:173-178``), never in the HTTP
  body. So a miss is surfaced as ``not_found`` carrying an explicit page-cap
  DISCLOSURE (it never over-claims proven absence); a DISTINCT ``truncated_scan``
  status is emitted only when the response positively signals truncation
  (``meta.scan_truncated`` or a name-query ``has_more``/``next_offset``) -- forward
  compatible with a satellite that later surfaces the signal the current route does
  not. See ``_scan_truncated``.
* Resolution cost (binding PT-05 #2). Successful name->GID resolutions are cached
  in-process, TTL-bounded (``TagNameCache``); resolution calls are 429-aware with
  exponential backoff (``resolve_tag_name``). A renamed tag may resolve STALE until
  the TTL expires -- documented in the tool description.
* Error passthrough. A non-200 tags response is mapped by ``map_http_error`` so the
  satellite's own code/message/recovery hint reaches the caller (the ``_upstream_suffix``
  pattern), while the 503-warming attribution stays curated (the C3 fence).

Constraint-5 fence: this module NEVER imports the ``autom8_asana`` domain SDK and makes
ZERO direct Asana calls -- it speaks HTTP only to the satellite REST surface via
``ctx.http``. Tag payloads are parsed as raw dicts, never domain models.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import httpx

from asana_mcp.errors import McpToolError, map_http_error

# Satellite read surface for name resolution (#246). Same /api/v1 prefix as the
# tasks write routes the composite tool already calls.
TAGS_RESOLVE_PATH = "/api/v1/tags"

# Explicit opt_fields for the read-back GET (PLAY-3). A bare passthrough GET returns
# None for unrequested fields, so the tag subfields MUST be named explicitly or the
# confirmation receipt would be blind.
READ_BACK_OPT_FIELDS = "tags.name,tags.gid"

# Mirror of the satellite scan bound (``tag_service.py:51`` _MAX_NAME_SCAN_PAGES = 100).
# Surfaced in the not_found / truncated disclosure so the caller learns the exact
# boundary rather than a vague "not found". 100 pages * 100 tags/page ~= 10k tags.
SATELLITE_NAME_SCAN_PAGE_CAP = 100
_SATELLITE_PAGE_SIZE = 100

# Cache + backoff defaults (in-process; no new env surface).
DEFAULT_NAME_CACHE_TTL_S = 300.0
DEFAULT_MAX_RESOLUTION_RETRIES = 3
DEFAULT_BACKOFF_BASE_S = 0.5

# Resolution outcome vocabulary (CLOSED).
RES_RESOLVED = "resolved"
RES_NOT_FOUND = "not_found"
RES_AMBIGUOUS = "ambiguous"
RES_TRUNCATED = "truncated_scan"

_CACHE_HIT = "hit"
_CACHE_MISS = "miss"
_CACHE_NA = "n/a"


class TagNameCache:
    """TTL-bounded in-process cache of exact tag name -> resolved GID.

    ONLY successful single-match resolutions are cached; misses / ambiguous /
    truncated outcomes are NEVER cached (so a just-created tag is not masked by a
    stale negative). Staleness caveat (documented in the tool description): a tag
    RENAMED at the source will keep resolving to its old GID until the TTL expires.

    ``clock`` is injectable so tests can force expiry deterministically.
    """

    def __init__(
        self,
        ttl_s: float = DEFAULT_NAME_CACHE_TTL_S,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl_s = ttl_s
        self._clock = clock
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, name: str) -> str | None:
        """Return the cached GID for ``name`` if present and unexpired, else None."""
        entry = self._store.get(name)
        if entry is None:
            return None
        expiry, gid = entry
        if self._clock() >= expiry:
            del self._store[name]
            return None
        return gid

    def put(self, name: str, gid: str) -> None:
        """Cache ``name`` -> ``gid`` with a fresh TTL window."""
        self._store[name] = (self._clock() + self._ttl_s, gid)


@dataclass
class TagResolution:
    """The outcome of resolving a tag name to a GID -- an honest, structured receipt."""

    status: str
    tag_gid: str | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)
    detail: str = ""
    cache: str = _CACHE_NA
    scan_page_cap: int = SATELLITE_NAME_SCAN_PAGE_CAP

    @property
    def resolved(self) -> bool:
        return self.status == RES_RESOLVED and bool(self.tag_gid)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "tag_gid": self.tag_gid,
            "candidates": self.candidates,
            "detail": self.detail,
            "cache": self.cache,
            "scan_page_cap": self.scan_page_cap,
        }


def validate_tag_selector(tag_gid: str | None, tag_name: str | None) -> str | None:
    """Dual-key contract: accept EXACTLY ONE of ``tag_gid`` | ``tag_name``.

    Returns a typed validation-error message when both or neither is supplied
    (whitespace-only counts as absent), else None. Empty is the refusal; the caller
    turns a non-None return into a pre-flight refusal before any backend call.
    """
    has_gid = bool(tag_gid and str(tag_gid).strip())
    has_name = bool(tag_name and str(tag_name).strip())
    if has_gid and has_name:
        return "Provide exactly one of tag_gid or tag_name, not both."
    if not has_gid and not has_name:
        return "Provide exactly one of tag_gid or tag_name; neither was supplied."
    return None


def _retry_after_hint(resp: httpx.Response) -> float | None:
    """Read the ``Retry-After`` header (seconds) for 429 backoff, if present."""
    header = resp.headers.get("retry-after")
    if not header:
        return None
    try:
        return float(header)
    except ValueError:
        return None


def _extract_matches(body: Any) -> list[dict[str, Any]]:
    """The #246 envelope is ``{"data": [ {gid, name, ...}, ... ], "meta": {...}}``.

    The name-query ``data`` list is the COMPLETE exact-match set (Asana tag names are
    not unique, so it may hold more than one).
    """
    data = body.get("data") if isinstance(body, dict) else None
    return [m for m in data if isinstance(m, dict)] if isinstance(data, list) else []


def _scan_truncated(body: Any) -> bool:
    """Did the satellite positively signal that its name scan was truncated?

    THE CONTRACT REALITY (read at #246): on a NAME query ``_resolve_by_name`` returns
    ``has_more=False`` / ``next_offset=None`` for BOTH a genuine miss AND a cap-truncated
    scan -- truncation is written to the satellite log only (``tag_service.py:173-178``),
    NOT to the response body. So this detector returns False for every response the
    CURRENT route produces on a name query, and the reachable miss path is ``not_found``
    (which carries the page-cap disclosure -- it never claims proven absence).

    It reads ``meta.scan_truncated`` and a name-query ``has_more``/``next_offset`` so that
    IF the satellite is later enhanced to surface truncation, the sidecar emits a DISTINCT
    ``truncated_scan`` status instead of a false ``not_found`` -- no sidecar change needed.
    """
    if not isinstance(body, dict):
        return False
    meta = body.get("meta")
    if not isinstance(meta, dict):
        return False
    if meta.get("scan_truncated") is True:
        return True
    pagination = meta.get("pagination")
    if isinstance(pagination, dict):
        if pagination.get("has_more") is True:
            return True
        if pagination.get("next_offset"):
            return True
    return False


def _not_found_detail(name: str) -> str:
    cap = SATELLITE_NAME_SCAN_PAGE_CAP
    return (
        f"No tag exactly named {name!r} was found. Matching is exact and "
        f"case-sensitive (byte-for-byte). NOTE: the satellite name scan is bounded at "
        f"{cap} pages (~{cap * _SATELLITE_PAGE_SIZE} tags) and does not report truncation "
        f"on name queries, so in a workspace exceeding that size a matching tag beyond the "
        f"scan boundary is indistinguishable from absent. If you expect this tag to exist, "
        f"pass its tag_gid directly."
    )


def _truncated_detail(name: str) -> str:
    cap = SATELLITE_NAME_SCAN_PAGE_CAP
    return (
        f"The satellite name scan was truncated at its {cap}-page cap before locating "
        f"{name!r}; a matching tag may exist beyond the scanned range. This is NOT a "
        f"definitive not-found -- pass the tag_gid directly, or narrow the workspace tag "
        f"set."
    )


def _ambiguous_detail(name: str, candidates: list[dict[str, Any]]) -> str:
    gids = ", ".join(str(c.get("gid")) for c in candidates)
    return (
        f"{len(candidates)} tags share the exact name {name!r} (Asana tag names are not "
        f"unique); resolution is ambiguous. Pass the intended tag_gid directly. "
        f"Candidate GIDs: {gids}."
    )


def _classify(name: str, body: Any, *, cache_state: str) -> TagResolution:
    """Map a 200 tags response body to a typed resolution outcome."""
    matches = _extract_matches(body)
    if not matches:
        # Zero matches is the ONLY case where not-found vs truncated is undecided.
        if _scan_truncated(body):
            return TagResolution(
                status=RES_TRUNCATED, detail=_truncated_detail(name), cache=cache_state
            )
        return TagResolution(
            status=RES_NOT_FOUND, detail=_not_found_detail(name), cache=cache_state
        )
    if len(matches) == 1:
        gid_raw = matches[0].get("gid")
        gid = str(gid_raw) if gid_raw else None
        if not gid:
            # A single match with no GID is a malformed row -- refuse rather than
            # resolve to an empty GID.
            return TagResolution(
                status=RES_NOT_FOUND,
                detail=(
                    f"The single match for {name!r} carried no GID (malformed satellite "
                    f"row); cannot resolve. Pass tag_gid directly."
                ),
                cache=cache_state,
            )
        return TagResolution(status=RES_RESOLVED, tag_gid=gid, cache=cache_state)
    candidates = [{"gid": m.get("gid"), "name": m.get("name")} for m in matches]
    return TagResolution(
        status=RES_AMBIGUOUS,
        candidates=candidates,
        detail=_ambiguous_detail(name, candidates),
        cache=cache_state,
    )


async def _get_tags_by_name(
    ctx: Any,
    name: str,
    *,
    sleep: Callable[[float], Awaitable[None]],
    max_retries: int,
    backoff_base_s: float,
) -> Any:
    """GET the #246 name-resolution route with 429-aware exponential backoff.

    Non-200 responses are mapped by ``map_http_error`` (upstream code/message passthrough;
    503-warming stays curated). A transport failure is a retryable server-class refusal.
    Returns the parsed JSON body on 200.
    """
    resp: httpx.Response | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = await ctx.http.get(TAGS_RESOLVE_PATH, params={"name": name})
        except httpx.HTTPError as exc:
            raise McpToolError(
                f"Transport error reaching the tag-resolution surface: {exc}",
                kind="server",
                retryable=True,
            ) from exc
        if resp.status_code != 429 or attempt == max_retries:
            break
        delay = _retry_after_hint(resp) or backoff_base_s * (2**attempt)
        await sleep(delay)

    assert resp is not None  # loop runs at least once (max_retries >= 0)
    if resp.status_code != 200:
        raise map_http_error(resp)
    return resp.json()


async def resolve_tag_name(
    ctx: Any,
    name: str,
    *,
    cache: TagNameCache | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    max_retries: int = DEFAULT_MAX_RESOLUTION_RETRIES,
    backoff_base_s: float = DEFAULT_BACKOFF_BASE_S,
) -> TagResolution:
    """Resolve an exact tag ``name`` to a GID via the satellite read surface.

    Matching is EXACT and case-sensitive, so ``name`` is sent to the satellite as-is
    (never trimmed) to preserve byte-for-byte fidelity. On a cache hit the cached GID is
    returned without a network call. Raises ``McpToolError`` on a non-200 / transport
    failure (upstream context preserved; 503-warming fence intact).
    """
    if cache is not None:
        cached_gid = cache.get(name)
        if cached_gid is not None:
            return TagResolution(status=RES_RESOLVED, tag_gid=cached_gid, cache=_CACHE_HIT)

    if sleep is None:
        sleep = asyncio.sleep

    cache_state = _CACHE_MISS if cache is not None else _CACHE_NA
    body = await _get_tags_by_name(
        ctx, name, sleep=sleep, max_retries=max_retries, backoff_base_s=backoff_base_s
    )
    resolution = _classify(name, body, cache_state=cache_state)
    if resolution.resolved and cache is not None and resolution.tag_gid is not None:
        cache.put(name, resolution.tag_gid)
    return resolution


async def read_back_tag_state(ctx: Any, task_gid: str, expected_tag_gid: str) -> dict[str, Any]:
    """PLAY-3 confirmation: read the task back and observe whether the tag applied.

    ALWAYS requests explicit ``opt_fields`` (a bare passthrough GET returns None for
    unrequested fields, so the tag subfields must be named or the receipt is blind).
    A read-back failure is SOFT: the write already committed, so a failed confirmation
    downgrades to "unavailable" -- it never retracts the write.

    If the tag is absent after a committed apply, the hint names the consumed-trigger
    hazard (PLAY-2): a play/automation tag may have been stripped when the automation
    fired; re-applying would RE-FIRE it.
    """
    try:
        resp = await ctx.http.get(
            f"/api/v1/tasks/{task_gid}", params={"opt_fields": READ_BACK_OPT_FIELDS}
        )
    except httpx.HTTPError as exc:
        return {
            "checked": False,
            "tag_present": None,
            "observed_tags": None,
            "opt_fields": READ_BACK_OPT_FIELDS,
            "detail": f"read-back unavailable: transport error: {exc}",
        }
    if resp.status_code != 200:
        return {
            "checked": False,
            "tag_present": None,
            "observed_tags": None,
            "opt_fields": READ_BACK_OPT_FIELDS,
            "detail": f"read-back unavailable: task GET returned HTTP {resp.status_code}",
        }

    body = resp.json()
    data = body.get("data") if isinstance(body, dict) else None
    raw_tags = data.get("tags") if isinstance(data, dict) else None
    observed = (
        [
            {"gid": str(t.get("gid")) if t.get("gid") else None, "name": t.get("name")}
            for t in raw_tags
            if isinstance(t, dict)
        ]
        if isinstance(raw_tags, list)
        else []
    )
    present = any(o["gid"] == str(expected_tag_gid) for o in observed)
    if present:
        detail = "Tag observed present on the task (apply confirmed via read-back)."
    else:
        detail = (
            "Tag NOT observed on the task after a committed apply. If this tag is a "
            "play/automation trigger, the automation may have already CONSUMED (stripped) "
            "it when it fired -- do NOT blindly re-apply, because re-applying RE-FIRES the "
            "automation and can double-trigger a real business workflow."
        )
    return {
        "checked": True,
        "tag_present": present,
        "observed_tags": observed,
        "opt_fields": READ_BACK_OPT_FIELDS,
        "detail": detail,
    }
