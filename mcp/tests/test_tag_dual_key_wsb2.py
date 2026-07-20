"""Two-sided tests for the WS-B2 dual-key tag argument (asana-mcp-postfelt-hardening).

THROWAWAY test suite (reference posture), same mount discipline as the s3 composite
suite. Bootstraps ``mcp/`` onto sys.path so the non-shipped ``asana_mcp`` package
imports without touching shared pyproject config.

Coverage (per the PT-05 / PLAY bindings):
  - dual-key validation (exactly-one of tag_gid | tag_name)
  - name -> GID resolution happy path
  - not-found vs truncated-scan distinction (page-cap honesty)
  - ambiguous (Asana names are not unique)
  - cache hit / expiry (TTL-bounded, positives only)
  - 429-aware backoff on resolution
  - error-surface passthrough (upstream code/message) + the 503-warming fence
  - PLAY-2 consumed-trigger description content
  - PLAY-3 read-back confirmation (present / absent-after-apply hint / soft failure)

Backend is a programmable httpx.MockTransport fake of the satellite REST surface --
ZERO live Asana calls. Fake sleep + fake clock make backoff and cache-expiry
deterministic (no real waiting).
"""

from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1]  # mcp/ root
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from asana_mcp.errors import McpToolError  # noqa: E402
from asana_mcp.tools.composite_write import (  # noqa: E402
    TOOL_DESCRIPTION,
    execute_tagged_write,
)
from asana_mcp.tools.tag_resolve import (  # noqa: E402
    RES_AMBIGUOUS,
    RES_NOT_FOUND,
    RES_RESOLVED,
    RES_TRUNCATED,
    TagNameCache,
    read_back_tag_state,
    resolve_tag_name,
    validate_tag_selector,
)


# --------------------------------------------------------------------------- #
# Harness
# --------------------------------------------------------------------------- #
@dataclass
class _Ctx:
    http: Any
    settings: Any = None


@dataclass
class AsanaBackend:
    """Programmable fake of the satellite REST surface (tags + tasks routes).

    ``tags_by_name`` maps an exact name -> the match list the #246 route returns.
    ``fail_next`` queues forced non-2xx responses per (method, path-substring).
    ``strip_on_add`` models a CONSUMED-trigger tag: add_tag succeeds but the tag is
    NOT reflected onto the task, so the read-back observes it absent.
    """

    tags_by_name: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    tags_meta: dict[str, Any] | None = None
    strip_on_add: bool = False
    malformed_read_back: bool = False
    calls: list[tuple[str, str, dict]] = field(default_factory=list)
    tagged: set[str] = field(default_factory=set)
    task_tags: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    _fail: dict[tuple[str, str], list[dict[str, Any]]] = field(default_factory=dict)

    def fail_next(
        self,
        method: str,
        path_contains: str,
        status_code: int,
        *,
        times: int = 1,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        spec = {"status": status_code, "body": body, "headers": headers}
        self._fail.setdefault((method, path_contains), []).extend([spec] * times)

    def _maybe_fail(self, method: str, path: str) -> dict[str, Any] | None:
        for (m, sub), queue in self._fail.items():
            if m == method and sub in path and queue:
                return queue.pop(0)
        return None

    def handler(self, request: httpx.Request) -> httpx.Response:
        method, path = request.method, request.url.path
        params = dict(request.url.params)
        body = json.loads(request.content) if request.content else {}
        self.calls.append((method, path, {**params, **body}))

        forced = self._maybe_fail(method, path)
        if forced is not None:
            return httpx.Response(
                forced["status"],
                json=forced["body"] or {"error": {"code": "FORCED", "message": "forced"}},
                headers=forced["headers"] or {},
            )

        if path == "/ready":
            return httpx.Response(200, json={"status": "ready"})

        # GET /api/v1/tags?name=... — name resolution (#246)
        if method == "GET" and path == "/api/v1/tags":
            name = params.get("name", "")
            matches = self.tags_by_name.get(name, [])
            meta = (
                self.tags_meta
                if self.tags_meta is not None
                else {"pagination": {"has_more": False, "next_offset": None}}
            )
            return httpx.Response(200, json={"data": matches, "meta": meta})

        # POST /api/v1/tasks/{gid}/tags — add_tag (idempotent)
        if method == "POST" and path.endswith("/tags"):
            gid = path.split("/")[-2]
            self.tagged.add(gid)
            tag_gid = body.get("tag_gid")
            if not self.strip_on_add:
                existing = {t["gid"] for t in self.task_tags.get(gid, [])}
                if tag_gid not in existing:
                    self.task_tags.setdefault(gid, []).append(
                        {"gid": tag_gid, "name": "reflected-tag"}
                    )
            return httpx.Response(200, json={"data": {"gid": gid, "tag": tag_gid}, "meta": {}})

        # PUT /api/v1/tasks/{gid} — push / mark_complete
        if method == "PUT" and "/tasks/" in path:
            gid = path.split("/")[-1]
            return httpx.Response(200, json={"data": {"gid": gid}, "meta": {}})

        # GET /api/v1/tasks/{gid} — read-back (PLAY-3)
        if method == "GET" and "/tasks/" in path:
            gid = path.split("/")[-1]
            if self.malformed_read_back:
                # 200 but a non-JSON body — the read-back parse must soft-fail, not crash.
                return httpx.Response(
                    200, content=b"<html>not json</html>", headers={"content-type": "text/html"}
                )
            return httpx.Response(
                200, json={"data": {"gid": gid, "tags": self.task_tags.get(gid, [])}, "meta": {}}
            )

        return httpx.Response(404, json={"error": {"code": "UNMAPPED", "message": path}})


@pytest.fixture
async def ctx_factory():
    clients: list[httpx.AsyncClient] = []

    def _make(backend: AsanaBackend) -> _Ctx:
        client = httpx.AsyncClient(
            base_url="http://asana-rest.local", transport=httpx.MockTransport(backend.handler)
        )
        clients.append(client)
        return _Ctx(http=client)

    yield _make
    for c in clients:
        await c.aclose()


def _one_match(gid: str = "TAG123", name: str = "play_launch") -> list[dict[str, Any]]:
    return [{"gid": gid, "name": name, "color": "green", "permalink_url": "http://x/y"}]


async def _noop_sleep(_delay: float) -> None:
    return None


# --------------------------------------------------------------------------- #
# 1 — Dual-key validation (exactly-one)
# --------------------------------------------------------------------------- #
def test_validate_selector_both_rejected():
    assert validate_tag_selector("TAG1", "name") is not None


def test_validate_selector_neither_rejected():
    assert validate_tag_selector(None, None) is not None
    assert validate_tag_selector("  ", "  ") is not None  # whitespace counts as absent


def test_validate_selector_only_gid_ok():
    assert validate_tag_selector("TAG1", None) is None


def test_validate_selector_only_name_ok():
    assert validate_tag_selector(None, "play_launch") is None


async def test_orchestrator_both_keys_refuses_before_any_backend_call(ctx_factory):
    backend = AsanaBackend()
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_gid="TAG1", tag_name="play_launch")
    assert out["status"] == "refused_incomplete"
    assert out["resolution"]["outcome"] == "invalid_selector"
    assert out["write"] is None and out["confirmation"] is None
    assert backend.calls == []  # nothing attempted


async def test_orchestrator_neither_key_refuses_before_any_backend_call(ctx_factory):
    backend = AsanaBackend()
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111")
    assert out["status"] == "refused_incomplete"
    assert out["resolution"]["outcome"] == "invalid_selector"
    assert backend.calls == []


# --------------------------------------------------------------------------- #
# 2 — Name -> GID resolution happy path
# --------------------------------------------------------------------------- #
async def test_resolve_single_match_returns_gid(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    ctx = ctx_factory(backend)
    res = await resolve_tag_name(ctx, "play_launch", sleep=_noop_sleep)
    assert res.status == RES_RESOLVED
    assert res.tag_gid == "TAG123"
    assert res.resolved is True


async def test_dual_key_by_name_completes_chain(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(
        ctx, task_gid="111", tag_name="play_launch", save_fields={"notes": "x"}
    )
    assert out["status"] == "completed"
    assert out["resolution"]["selector"] == "tag_name"
    assert out["resolution"]["outcome"] == "resolved"
    assert out["resolution"]["tag_gid"] == "TAG123"
    assert out["write"]["committed"] == ["add_tag", "push", "mark_complete"]
    # the resolved GID reached the add_tag verb
    assert backend.tagged == {"111"}
    add_tag_call = next(c for c in backend.calls if c[0] == "POST" and c[1].endswith("/tags"))
    assert add_tag_call[2]["tag_gid"] == "TAG123"


async def test_dual_key_by_gid_still_works_and_reads_back(ctx_factory):
    backend = AsanaBackend()
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_gid="RAW9")
    assert out["status"] == "completed"
    assert out["resolution"]["selector"] == "tag_gid"
    assert out["resolution"]["outcome"] == "provided"
    # no name-resolution GET was made for the gid path
    assert not any(c for c in backend.calls if c[0] == "GET" and c[1] == "/api/v1/tags")


# --------------------------------------------------------------------------- #
# 3 — not-found vs truncated-scan distinction (page-cap honesty)
# --------------------------------------------------------------------------- #
async def test_resolve_not_found_carries_page_cap_disclosure(ctx_factory):
    backend = AsanaBackend(tags_by_name={})  # miss -> empty data
    ctx = ctx_factory(backend)
    res = await resolve_tag_name(ctx, "ghost", sleep=_noop_sleep)
    assert res.status == RES_NOT_FOUND
    assert res.tag_gid is None
    # honest: names the 100-page bound and does NOT claim proven absence
    assert "100 pages" in res.detail
    assert "indistinguishable from absent" in res.detail
    assert res.scan_page_cap == 100


async def test_resolve_truncated_scan_distinct_from_not_found(ctx_factory):
    # Empty data BUT the response positively signals more pages -> truncated_scan
    backend = AsanaBackend(
        tags_by_name={}, tags_meta={"pagination": {"has_more": True, "next_offset": "cur"}}
    )
    ctx = ctx_factory(backend)
    res = await resolve_tag_name(ctx, "ghost", sleep=_noop_sleep)
    assert res.status == RES_TRUNCATED
    assert res.status != RES_NOT_FOUND
    assert "truncated" in res.detail.lower()
    assert "NOT a definitive not-found" in res.detail


async def test_resolve_truncated_via_scan_truncated_flag(ctx_factory):
    backend = AsanaBackend(tags_by_name={}, tags_meta={"scan_truncated": True})
    ctx = ctx_factory(backend)
    res = await resolve_tag_name(ctx, "ghost", sleep=_noop_sleep)
    assert res.status == RES_TRUNCATED


async def test_orchestrator_name_not_found_refuses_no_write(ctx_factory):
    backend = AsanaBackend(tags_by_name={})
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="ghost")
    assert out["status"] == "refused_incomplete"
    assert out["resolution"]["outcome"] == RES_NOT_FOUND
    assert out["write"] is None and out["confirmation"] is None
    assert backend.tagged == set()  # no write attempted


# --------------------------------------------------------------------------- #
# 4 — Ambiguous (Asana tag names are not unique)
# --------------------------------------------------------------------------- #
async def test_resolve_ambiguous_multiple_matches(ctx_factory):
    backend = AsanaBackend(
        tags_by_name={"dupe": [{"gid": "A1", "name": "dupe"}, {"gid": "B2", "name": "dupe"}]}
    )
    ctx = ctx_factory(backend)
    res = await resolve_tag_name(ctx, "dupe", sleep=_noop_sleep)
    assert res.status == RES_AMBIGUOUS
    assert res.tag_gid is None
    assert {c["gid"] for c in res.candidates} == {"A1", "B2"}


async def test_orchestrator_ambiguous_refuses_and_lists_candidates(ctx_factory):
    backend = AsanaBackend(
        tags_by_name={"dupe": [{"gid": "A1", "name": "dupe"}, {"gid": "B2", "name": "dupe"}]}
    )
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="dupe")
    assert out["status"] == "refused_incomplete"
    assert out["resolution"]["outcome"] == RES_AMBIGUOUS
    assert "candidates" in out["resolution"]
    assert backend.tagged == set()


# --------------------------------------------------------------------------- #
# 5 — Cache hit / expiry (TTL-bounded, positives only)
# --------------------------------------------------------------------------- #
def _count_tag_gets(backend: AsanaBackend) -> int:
    return sum(1 for c in backend.calls if c[0] == "GET" and c[1] == "/api/v1/tags")


async def test_cache_hit_skips_second_network_call(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    ctx = ctx_factory(backend)
    cache = TagNameCache()
    r1 = await resolve_tag_name(ctx, "play_launch", cache=cache, sleep=_noop_sleep)
    r2 = await resolve_tag_name(ctx, "play_launch", cache=cache, sleep=_noop_sleep)
    assert r1.tag_gid == r2.tag_gid == "TAG123"
    assert r1.cache == "miss" and r2.cache == "hit"
    assert _count_tag_gets(backend) == 1  # second resolve served from cache


async def test_cache_expiry_reresolves(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    ctx = ctx_factory(backend)
    now = [1000.0]
    cache = TagNameCache(ttl_s=100.0, clock=lambda: now[0])
    await resolve_tag_name(ctx, "play_launch", cache=cache, sleep=_noop_sleep)
    now[0] += 101.0  # advance past TTL
    r2 = await resolve_tag_name(ctx, "play_launch", cache=cache, sleep=_noop_sleep)
    assert r2.cache == "miss"
    assert _count_tag_gets(backend) == 2  # expired -> re-scanned


async def test_cache_does_not_store_negatives(ctx_factory):
    backend = AsanaBackend(tags_by_name={})  # miss
    ctx = ctx_factory(backend)
    cache = TagNameCache()
    await resolve_tag_name(ctx, "ghost", cache=cache, sleep=_noop_sleep)
    await resolve_tag_name(ctx, "ghost", cache=cache, sleep=_noop_sleep)
    assert _count_tag_gets(backend) == 2  # not_found never cached


# --------------------------------------------------------------------------- #
# 6 — 429-aware backoff
# --------------------------------------------------------------------------- #
async def test_429_then_200_backs_off_and_resolves(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    backend.fail_next("GET", "/api/v1/tags", 429, times=2)
    ctx = ctx_factory(backend)
    delays: list[float] = []

    async def rec_sleep(d: float) -> None:
        delays.append(d)

    res = await resolve_tag_name(
        ctx, "play_launch", sleep=rec_sleep, max_retries=3, backoff_base_s=0.5
    )
    assert res.status == RES_RESOLVED
    assert len(delays) == 2  # two 429s -> two backoffs
    assert delays == [0.5, 1.0]  # exponential base*2**attempt


async def test_429_exhausted_raises_rate_limit(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    backend.fail_next("GET", "/api/v1/tags", 429, times=5)
    ctx = ctx_factory(backend)
    with pytest.raises(McpToolError) as ei:
        await resolve_tag_name(ctx, "play_launch", sleep=_noop_sleep, max_retries=2)
    assert ei.value.kind == "rate_limit"
    assert ei.value.retryable is True


async def test_429_honors_retry_after_header(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    backend.fail_next("GET", "/api/v1/tags", 429, times=1, headers={"retry-after": "7"})
    ctx = ctx_factory(backend)
    delays: list[float] = []

    async def rec_sleep(d: float) -> None:
        delays.append(d)

    res = await resolve_tag_name(ctx, "play_launch", sleep=rec_sleep)
    assert res.status == RES_RESOLVED
    assert delays == [7.0]  # header wins over exponential (7 < 30 cap, so honored as-is)


async def test_429_retry_after_header_is_capped(ctx_factory):
    """A pathological upstream Retry-After is capped at _MAX_BACKOFF_S (30s), so it
    cannot stall the tool call to timeout."""
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    backend.fail_next("GET", "/api/v1/tags", 429, times=1, headers={"retry-after": "99999"})
    ctx = ctx_factory(backend)
    delays: list[float] = []

    async def rec_sleep(d: float) -> None:
        delays.append(d)

    res = await resolve_tag_name(ctx, "play_launch", sleep=rec_sleep)
    assert res.status == RES_RESOLVED
    assert delays == [30.0]  # 99999 capped to the 30s ceiling


async def test_429_backoff_surfaces_through_orchestrator(ctx_factory):
    """Exhausted 429 during name resolution surfaces as a resolution_error refusal."""
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    backend.fail_next("GET", "/api/v1/tags", 429, times=6)
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    assert out["status"] == "refused_incomplete"
    assert out["resolution"]["outcome"] == "resolution_error"
    assert out["resolution"]["error"]["kind"] == "rate_limit"
    assert backend.tagged == set()


# --------------------------------------------------------------------------- #
# 7 — Error-surface passthrough + 503-warming fence
# --------------------------------------------------------------------------- #
async def test_resolution_404_carries_upstream_context(ctx_factory):
    backend = AsanaBackend()
    backend.fail_next(
        "GET",
        "/api/v1/tags",
        404,
        body={"error": {"code": "TAGS_ROUTE_GONE", "message": "route retired"}},
    )
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    assert out["resolution"]["outcome"] == "resolution_error"
    err = out["resolution"]["error"]
    assert err["kind"] == "not_found"
    assert "TAGS_ROUTE_GONE" in err["message"]  # upstream code passed through
    assert "route retired" in err["message"]  # upstream message passed through


async def test_resolution_503_warming_stays_curated_and_does_not_leak(ctx_factory):
    """The 503-warming fence: warming text is curated, upstream prose does NOT leak."""
    backend = AsanaBackend()
    backend.fail_next(
        "GET",
        "/api/v1/tags",
        503,
        body={"error": {"code": "CACHE_NOT_WARMED", "message": "do-not-leak-this-prose"}},
    )
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    err = out["resolution"]["error"]
    assert err["kind"] == "warming"
    assert err["retryable"] is True
    assert "warming" in err["message"].lower()
    assert "do-not-leak-this-prose" not in err["message"]  # fence holds


# --------------------------------------------------------------------------- #
# 8 — PLAY-2 consumed-trigger description content
# --------------------------------------------------------------------------- #
def test_tool_description_warns_consumed_trigger():
    d = TOOL_DESCRIPTION
    assert "CONSUMED" in d
    assert "RE-FIRES" in d
    assert "double-trigger" in d.lower() or "DOUBLE-TRIGGER" in d


def test_tool_description_documents_dual_key_page_cap_and_cache():
    d = TOOL_DESCRIPTION
    assert "EXACTLY ONE" in d  # dual-key
    assert "100 pages" in d  # page-cap honesty
    assert "NOT proven absent" in d
    assert "RENAMED" in d and "expires" in d  # cache staleness caveat


# --------------------------------------------------------------------------- #
# 9 — PLAY-3 read-back confirmation
# --------------------------------------------------------------------------- #
async def test_read_back_confirms_tag_present(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    conf = out["confirmation"]
    assert conf is not None
    assert conf["checked"] is True
    assert conf["tag_present"] is True
    assert any(t["gid"] == "TAG123" for t in conf["observed_tags"])


async def test_read_back_absent_after_apply_hints_consumed_trigger(ctx_factory):
    # strip_on_add models a consumed-trigger tag: add succeeds, tag not on the task.
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()}, strip_on_add=True)
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    conf = out["confirmation"]
    assert conf["checked"] is True
    assert conf["tag_present"] is False
    assert "CONSUMED" in conf["detail"]
    assert "RE-FIRES" in conf["detail"]


async def test_read_back_uses_explicit_opt_fields(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    ctx = ctx_factory(backend)
    await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    read_back = next(c for c in backend.calls if c[0] == "GET" and c[1] == "/api/v1/tasks/111")
    assert read_back[2].get("opt_fields") == "tags.name,tags.gid"


async def test_read_back_soft_failure_does_not_retract_write(ctx_factory):
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()})
    backend.fail_next("GET", "/api/v1/tasks/111", 500)  # read-back GET fails
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    # the write still completed; only the confirmation is unavailable
    assert out["status"] == "completed"
    assert out["write"]["committed"] == ["add_tag", "push", "mark_complete"]
    assert out["confirmation"]["checked"] is False
    assert "unavailable" in out["confirmation"]["detail"]


async def test_read_back_direct_helper_soft_on_transport_error():
    def _boom(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client = httpx.AsyncClient(base_url="http://x.local", transport=httpx.MockTransport(_boom))
    try:
        result = await read_back_tag_state(_Ctx(http=client), "111", "TAG123")
    finally:
        await client.aclose()
    assert result["checked"] is False
    assert result["tag_present"] is None


async def test_read_back_malformed_200_body_does_not_retract_write(ctx_factory):
    """C-2: a 200 read-back with a non-JSON body must SOFT-fail (checked=False) and
    leave the committed write result intact — never crash the caller post-write."""
    backend = AsanaBackend(tags_by_name={"play_launch": _one_match()}, malformed_read_back=True)
    ctx = ctx_factory(backend)
    out = await execute_tagged_write(ctx, task_gid="111", tag_name="play_launch")
    # the write survives; only the confirmation degrades
    assert out["status"] == "completed"
    assert out["write"]["committed"] == ["add_tag", "push", "mark_complete"]
    assert out["confirmation"]["checked"] is False
    assert out["confirmation"]["tag_present"] is None
    assert "malformed/non-JSON" in out["confirmation"]["detail"]


async def test_read_back_direct_helper_malformed_body_soft():
    def _html_200(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>")

    client = httpx.AsyncClient(base_url="http://x.local", transport=httpx.MockTransport(_html_200))
    try:
        result = await read_back_tag_state(_Ctx(http=client), "111", "TAG123")
    finally:
        await client.aclose()
    assert result["checked"] is False
    assert result["tag_present"] is None
    assert "malformed/non-JSON" in result["detail"]
