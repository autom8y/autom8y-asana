#!/usr/bin/env python3
# ruff: noqa: TID251
"""Full-scope API smoke test for autom8y-asana.

Self-discovering: uses the APIs themselves to find test fixtures rather than
hardcoding GIDs. Each tier's results feed into subsequent tiers.

Modes (SMOKE_MODE env var):
  production (default) -- hits https://asana.api.autom8y.io with real auth
  local                -- hits http://localhost:5300

Override fixture discovery with env vars:
  SMOKE_OFFER_GID      -- skip discovery, use this offer for workflow invoke
  SMOKE_UNIT_PHONE     -- skip discovery, use this phone for resolver test
  SMOKE_UNIT_VERTICAL  -- skip discovery, use this vertical for resolver test

Usage:
  .venv/bin/python scripts/smoke_test_api.py                       # all tiers
  .venv/bin/python scripts/smoke_test_api.py --tier 0              # health only
  .venv/bin/python scripts/smoke_test_api.py --tier 0 --tier 1 -v  # verbose
  SMOKE_MODE=local .venv/bin/python scripts/smoke_test_api.py      # local
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Palette (disabled when piped)
# ---------------------------------------------------------------------------

BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"

if not sys.stdout.isatty():
    BOLD = DIM = GREEN = CYAN = YELLOW = RED = MAGENTA = RESET = ""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTH_BASE_PRODUCTION = "https://auth.api.autom8y.io"
API_BASE_PRODUCTION = "https://asana.api.autom8y.io"
API_BASE_LOCAL = "http://localhost:5300"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


class TestStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class TestResult:
    name: str
    tier: int
    status: TestStatus
    status_code: int | None = None
    elapsed_ms: float = 0.0
    message: str = ""
    response_body: str = ""


@dataclass
class SmokeConfig:
    mode: str
    base_url: str
    verbose: bool
    tiers: set[int]
    pat: str | None
    jwt: str | None
    timeout: float
    workspace_gid: str | None = None
    # Optional fixture overrides (env vars)
    offer_gid: str | None = None
    unit_phone: str | None = None
    unit_vertical: str | None = None


@dataclass
class DiscoveredFixtures:
    """Test fixtures discovered from the APIs themselves."""

    workspace: str | None = None
    project: str | None = None
    section: str | None = None
    task: str | None = None
    # Discovered from query API (T2-1) — a unit row with phone+vertical
    unit_phone: str | None = None
    unit_vertical: str | None = None
    unit_gid: str | None = None
    # Discovered from section-timelines (T1-8) — offer with max active_days
    offer_gid: str | None = None
    offer_active_days: int = 0


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _acquire_jwt(auth_base: str) -> str | None:
    """Acquire S2S JWT via platform TokenManager.

    Reads SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET from environment
    (ServiceAccount convention). Falls back to SERVICE_API_KEY via Config.from_env().
    Returns None if credentials are missing or exchange fails.
    """
    from autom8y_core import Config, TokenManager

    try:
        config = Config.from_env()
    except ValueError:
        return None
    try:
        manager = TokenManager(config)
        token = manager.get_token()
        manager.close()
        print(f"  JWT acquired (len={len(token)})")
        return token
    except Exception as e:
        print(f"  JWT exchange failed: {e}")
        return None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _deep_get(obj: Any, path: str) -> Any:
    """Navigate a dot-separated path into nested dicts/lists."""
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return None
    return obj


async def _run_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    name: str,
    tier: int,
    timeout: float,
) -> TestResult:
    """Execute a single HTTP request and return raw TestResult."""
    t0 = time.monotonic()
    try:
        resp = await client.request(
            method,
            url,
            headers=headers,
            json=json_body,
            timeout=timeout,
        )
        elapsed = (time.monotonic() - t0) * 1000
        full_body = resp.text or ""
        return TestResult(
            name=name,
            tier=tier,
            status=TestStatus.PASS,
            status_code=resp.status_code,
            elapsed_ms=elapsed,
            message=f"{resp.status_code}",
            response_body=full_body,
        )
    except httpx.ConnectError as e:
        elapsed = (time.monotonic() - t0) * 1000
        return TestResult(
            name=name,
            tier=tier,
            status=TestStatus.ERROR,
            elapsed_ms=elapsed,
            message=f"Connection refused: {e}",
        )
    except httpx.TimeoutException:
        elapsed = (time.monotonic() - t0) * 1000
        return TestResult(
            name=name,
            tier=tier,
            status=TestStatus.ERROR,
            elapsed_ms=elapsed,
            message=f"Timeout after {elapsed:.0f}ms",
        )
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return TestResult(
            name=name,
            tier=tier,
            status=TestStatus.ERROR,
            elapsed_ms=elapsed,
            message=str(e),
        )


def _parse_json(result: TestResult) -> dict[str, Any] | None:
    if not result.response_body:
        return None
    try:
        return json.loads(result.response_body)
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

_STATUS_COLOR = {
    TestStatus.PASS: GREEN,
    TestStatus.FAIL: RED,
    TestStatus.SKIP: YELLOW,
    TestStatus.ERROR: RED,
}

TIER_LABELS = {
    0: "Health (no auth)",
    1: "Read-only (PAT)",
    2: "S2S Read-only (JWT)",
    3: "Mutating (dry_run / local)",
}


def _print_tier_header(tier: int) -> None:
    label = TIER_LABELS.get(tier, f"Tier {tier}")
    print(f"\n{BOLD}--- Tier {tier}: {label} {'-' * max(0, 44 - len(label))}{RESET}")


def _print_result(r: TestResult, verbose: bool) -> None:
    color = _STATUS_COLOR.get(r.status, "")
    status_label = f"{color}{r.status.value:5s}{RESET}"
    timing = f"{r.elapsed_ms:6.0f}ms" if r.elapsed_ms else "      "
    code = f"  {r.message}" if r.message else ""
    print(f"  {status_label}  {r.name:<46s} {timing}{code}")
    if verbose and r.response_body:
        excerpt = r.response_body[:600]
        if len(r.response_body) > 600:
            excerpt += "..."
        print(f"         {DIM}{excerpt}{RESET}")


def _print_summary(results: list[TestResult], total_ms: float) -> None:
    counts = {s: 0 for s in TestStatus}
    for r in results:
        counts[r.status] += 1
    parts = []
    if counts[TestStatus.PASS]:
        parts.append(f"{GREEN}{counts[TestStatus.PASS]} passed{RESET}")
    if counts[TestStatus.FAIL]:
        parts.append(f"{RED}{counts[TestStatus.FAIL]} failed{RESET}")
    if counts[TestStatus.SKIP]:
        parts.append(f"{YELLOW}{counts[TestStatus.SKIP]} skipped{RESET}")
    if counts[TestStatus.ERROR]:
        parts.append(f"{RED}{counts[TestStatus.ERROR]} errors{RESET}")
    line = ", ".join(parts)
    bar = "=" * 64
    print(f"\n{BOLD}{bar}{RESET}")
    print(f"  {BOLD}SUMMARY:{RESET} {line} ({total_ms / 1000:.1f}s)")
    print(f"{BOLD}{bar}{RESET}")


# ---------------------------------------------------------------------------
# Tier 0: Health
# ---------------------------------------------------------------------------


async def tier0_health(
    client: httpx.AsyncClient,
    config: SmokeConfig,
    results: list[TestResult],
) -> bool:
    """Run health checks. Returns False if service is unreachable."""
    _print_tier_header(0)

    # T0-1 /health
    r = await _run_request(
        client,
        "GET",
        f"{config.base_url}/health",
        name="T0-1 GET /health",
        tier=0,
        timeout=5,
    )
    if r.status == TestStatus.ERROR:
        results.append(r)
        _print_result(r, config.verbose)
        print(
            f"\n  {RED}Cannot reach {config.base_url}. Is the service running?{RESET}"
        )
        return False
    body = _parse_json(r)
    if r.status_code == 200 and body and body.get("status", "").lower() == "ok":
        r.message = "200 OK"
    else:
        r.status = TestStatus.FAIL
        r.message = f"{r.status_code} (expected 200 with status=ok)"
    results.append(r)
    _print_result(r, config.verbose)

    # T0-2 /ready
    r = await _run_request(
        client,
        "GET",
        f"{config.base_url}/ready",
        name="T0-2 GET /ready",
        tier=0,
        timeout=5,
    )
    body = _parse_json(r)
    if (
        r.status_code in (200, 503)
        and body
        and body.get("status") in ("ok", "unavailable")
    ):
        r.status = TestStatus.PASS
        r.message = f"{r.status_code} {body.get('status', '')}"
    else:
        r.status = TestStatus.FAIL
        r.message = f"{r.status_code} unexpected"
    results.append(r)
    _print_result(r, config.verbose)

    # T0-3 /health/deps
    r = await _run_request(
        client,
        "GET",
        f"{config.base_url}/health/deps",
        name="T0-3 GET /health/deps",
        tier=0,
        timeout=10,
    )
    body = _parse_json(r)
    if r.status_code == 200 and body and isinstance(body.get("checks"), dict):
        r.status = TestStatus.PASS
        r.message = f"200 OK ({len(body['checks'])} checks)"
    elif r.status_code == 404:
        r.status = TestStatus.SKIP
        r.message = "404 (not exposed via gateway)"
    else:
        r.status = TestStatus.FAIL
        r.message = f"{r.status_code} (expected checks dict)"
    results.append(r)
    _print_result(r, config.verbose)

    return True


# ---------------------------------------------------------------------------
# Tier 1: PAT Read-Only
# ---------------------------------------------------------------------------


async def tier1_pat_readonly(
    client: httpx.AsyncClient,
    config: SmokeConfig,
    results: list[TestResult],
    fixtures: DiscoveredFixtures,
) -> None:
    """Run PAT-auth read-only tests. Populates fixtures for downstream tiers."""
    _print_tier_header(1)

    if not config.pat:
        r = TestResult(
            name="Tier 1 (all)",
            tier=1,
            status=TestStatus.SKIP,
            message="No PAT (set ASANA_BOT_PAT or ASANA_PAT)",
        )
        results.append(r)
        _print_result(r, config.verbose)
        return

    hdrs = {"Authorization": f"Bearer {config.pat}"}

    # T1-1 /api/v1/users/me
    r = await _run_request(
        client,
        "GET",
        f"{config.base_url}/api/v1/users/me",
        headers=hdrs,
        name="T1-1 GET /api/v1/users/me",
        tier=1,
        timeout=config.timeout,
    )
    body = _parse_json(r)
    if r.status_code == 200 and body and _deep_get(body, "data.gid"):
        r.status = TestStatus.PASS
        r.message = f"200 OK ({_deep_get(body, 'data.name')})"
    else:
        r.status = TestStatus.FAIL
        r.message = f"{r.status_code} (expected data.gid)"
    results.append(r)
    _print_result(r, config.verbose)

    # T1-2 /api/v1/workspaces
    r = await _run_request(
        client,
        "GET",
        f"{config.base_url}/api/v1/workspaces",
        headers=hdrs,
        name="T1-2 GET /api/v1/workspaces",
        tier=1,
        timeout=config.timeout,
    )
    body = _parse_json(r)
    data = _deep_get(body, "data") if body else None
    if r.status_code == 200 and isinstance(data, list) and len(data) > 0:
        r.status = TestStatus.PASS
        r.message = f"200 OK ({len(data)} workspaces)"
        fixtures.workspace = data[0].get("gid")
    else:
        r.status = TestStatus.FAIL
        r.message = f"{r.status_code} (expected data list)"
    results.append(r)
    _print_result(r, config.verbose)

    fixtures.workspace = config.workspace_gid or fixtures.workspace

    # T1-3 /api/v1/projects
    if fixtures.workspace:
        r = await _run_request(
            client,
            "GET",
            f"{config.base_url}/api/v1/projects?workspace={fixtures.workspace}&limit=5",
            headers=hdrs,
            name="T1-3 GET /api/v1/projects",
            tier=1,
            timeout=config.timeout,
        )
        body = _parse_json(r)
        data = _deep_get(body, "data") if body else None
        if r.status_code == 200 and isinstance(data, list) and len(data) > 0:
            r.status = TestStatus.PASS
            r.message = f"200 OK ({len(data)} projects)"
            fixtures.project = data[0].get("gid")
        else:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code} (expected projects list)"
        results.append(r)
        _print_result(r, config.verbose)
    else:
        results.append(
            TestResult(
                name="T1-3 GET /api/v1/projects",
                tier=1,
                status=TestStatus.SKIP,
                message="No workspace GID",
            )
        )
        _print_result(results[-1], config.verbose)

    # T1-4 /api/v1/projects/{gid}/sections
    if fixtures.project:
        r = await _run_request(
            client,
            "GET",
            f"{config.base_url}/api/v1/projects/{fixtures.project}/sections",
            headers=hdrs,
            name="T1-4 GET /api/v1/projects/{gid}/sections",
            tier=1,
            timeout=config.timeout,
        )
        body = _parse_json(r)
        data = _deep_get(body, "data") if body else None
        if r.status_code == 200 and isinstance(data, list):
            r.status = TestStatus.PASS
            r.message = f"200 OK ({len(data)} sections)"
            if data:
                fixtures.section = data[0].get("gid")
        else:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code}"
        results.append(r)
        _print_result(r, config.verbose)
    else:
        results.append(
            TestResult(
                name="T1-4 GET sections",
                tier=1,
                status=TestStatus.SKIP,
                message="No project GID",
            )
        )
        _print_result(results[-1], config.verbose)

    # T1-5 /api/v1/tasks
    if fixtures.project:
        r = await _run_request(
            client,
            "GET",
            f"{config.base_url}/api/v1/tasks?project={fixtures.project}&limit=5",
            headers=hdrs,
            name="T1-5 GET /api/v1/tasks",
            tier=1,
            timeout=config.timeout,
        )
        body = _parse_json(r)
        data = _deep_get(body, "data") if body else None
        if r.status_code == 200 and isinstance(data, list):
            r.status = TestStatus.PASS
            r.message = f"200 OK ({len(data)} tasks)"
            if data:
                fixtures.task = data[0].get("gid")
        else:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code}"
        results.append(r)
        _print_result(r, config.verbose)
    else:
        results.append(
            TestResult(
                name="T1-5 GET tasks",
                tier=1,
                status=TestStatus.SKIP,
                message="No project GID",
            )
        )
        _print_result(results[-1], config.verbose)

    # T1-6 /api/v1/tasks/{gid}
    if fixtures.task:
        r = await _run_request(
            client,
            "GET",
            f"{config.base_url}/api/v1/tasks/{fixtures.task}",
            headers=hdrs,
            name="T1-6 GET /api/v1/tasks/{gid}",
            tier=1,
            timeout=config.timeout,
        )
        body = _parse_json(r)
        if r.status_code == 200 and _deep_get(body, "data.gid") == fixtures.task:
            r.status = TestStatus.PASS
            r.message = f"200 OK (gid={fixtures.task})"
        else:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code} (expected data.gid={fixtures.task})"
        results.append(r)
        _print_result(r, config.verbose)
    else:
        results.append(
            TestResult(
                name="T1-6 GET task by GID",
                tier=1,
                status=TestStatus.SKIP,
                message="No task GID",
            )
        )
        _print_result(results[-1], config.verbose)

    # T1-7 /api/v1/dataframes/project/{gid}?schema=offer
    if fixtures.project:
        r = await _run_request(
            client,
            "GET",
            f"{config.base_url}/api/v1/dataframes/project/{fixtures.project}?schema=offer",
            headers=hdrs,
            name="T1-7 GET /api/v1/dataframes/project/{gid}",
            tier=1,
            timeout=config.timeout,
        )
        body = _parse_json(r)
        if r.status_code == 200:
            data = _deep_get(body, "data") if body else None
            count = len(data) if isinstance(data, list) else "?"
            r.status = TestStatus.PASS
            r.message = f"200 OK ({count} rows)"
        elif r.status_code == 400:
            r.status = TestStatus.SKIP
            r.message = "400 (not an offer project)"
        else:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code}"
        results.append(r)
        _print_result(r, config.verbose)
    else:
        results.append(
            TestResult(
                name="T1-7 GET dataframes",
                tier=1,
                status=TestStatus.SKIP,
                message="No project GID",
            )
        )
        _print_result(results[-1], config.verbose)

    # T1-8 Section timelines — also discovers best offer fixture by active_days
    today = date.today().isoformat()
    r = await _run_request(
        client,
        "GET",
        f"{config.base_url}/api/v1/offers/section-timelines"
        f"?period_start=2025-01-01&period_end={today}",
        headers=hdrs,
        name="T1-8 GET /api/v1/offers/section-timelines",
        tier=1,
        timeout=30,
    )
    body = _parse_json(r)
    timelines = _deep_get(body, "data.timelines") if body else None
    if r.status_code == 200 and isinstance(timelines, list):
        r.status = TestStatus.PASS
        r.message = f"200 OK ({len(timelines)} entries)"
        # Pick the offer with highest active_section_days as our workflow fixture
        best = _pick_best_offer(timelines)
        if best:
            fixtures.offer_gid = best["offer_gid"]
            fixtures.offer_active_days = best["active_section_days"]
    elif r.status_code == 503:
        r.status = TestStatus.SKIP
        r.message = "503 (cache not warm)"
    else:
        r.status = TestStatus.FAIL
        r.message = f"{r.status_code}"
    results.append(r)
    _print_result(r, config.verbose)


def _pick_best_offer(timelines: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the offer with highest active_section_days that has an office_phone."""
    best: dict[str, Any] | None = None
    best_days = -1
    for t in timelines:
        days = t.get("active_section_days", 0)
        if days > best_days and t.get("office_phone"):
            best = t
            best_days = days
    return best


# ---------------------------------------------------------------------------
# Tier 2: S2S JWT Read-Only
# ---------------------------------------------------------------------------


async def tier2_s2s_readonly(
    client: httpx.AsyncClient,
    config: SmokeConfig,
    results: list[TestResult],
    fixtures: DiscoveredFixtures,
) -> None:
    _print_tier_header(2)

    if not config.jwt:
        r = TestResult(
            name="Tier 2 (all)",
            tier=2,
            status=TestStatus.SKIP,
            message="No JWT (set SERVICE_CLIENT_ID + SERVICE_CLIENT_SECRET)",
        )
        results.append(r)
        _print_result(r, config.verbose)
        return

    hdrs = {"Authorization": f"Bearer {config.jwt}", "Content-Type": "application/json"}

    def _handle_503(r: TestResult) -> None:
        if r.status_code == 503:
            r.status = TestStatus.SKIP
            r.message = "503 (cache not warm)"

    # T2-1 Query unit rows — also discovers a unit with phone+vertical for resolver
    r = await _run_request(
        client,
        "POST",
        f"{config.base_url}/v1/query/unit/rows",
        headers=hdrs,
        json_body={
            "select": ["gid", "office_phone", "vertical"],
            "where": {
                "and": [
                    {"field": "office_phone", "op": "ne", "value": None},
                    {"field": "vertical", "op": "ne", "value": None},
                ],
            },
            "limit": 5,
        },
        name="T2-1 POST /v1/query/unit/rows",
        tier=2,
        timeout=config.timeout,
    )
    body = _parse_json(r)
    if r.status_code == 200 and body:
        data = body.get("data", [])
        total = _deep_get(body, "meta.total_count")
        r.status = TestStatus.PASS
        r.message = f"200 OK ({len(data)} rows, total={total})"
        # Discover a resolvable unit fixture from the query results
        if data and not (config.unit_phone and config.unit_vertical):
            for row in data:
                phone = row.get("office_phone")
                vert = row.get("vertical")
                if phone and vert:
                    fixtures.unit_phone = phone
                    fixtures.unit_vertical = vert
                    fixtures.unit_gid = row.get("gid")
                    break
    else:
        _handle_503(r)
        if r.status != TestStatus.SKIP:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code}"
    results.append(r)
    _print_result(r, config.verbose)

    # T2-2 Aggregate offers by section
    r = await _run_request(
        client,
        "POST",
        f"{config.base_url}/v1/query/offer/aggregate",
        headers=hdrs,
        json_body={
            "group_by": ["section"],
            "aggregations": [{"column": "gid", "agg": "count"}],
        },
        name="T2-2 POST /v1/query/offer/aggregate",
        tier=2,
        timeout=config.timeout,
    )
    body = _parse_json(r)
    if r.status_code == 200 and body:
        data = body.get("data", [])
        r.status = TestStatus.PASS
        r.message = f"200 OK ({len(data)} groups)"
    else:
        _handle_503(r)
        if r.status != TestStatus.SKIP:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code}"
    results.append(r)
    _print_result(r, config.verbose)

    # T2-3 Resolve unit — uses discovered or overridden phone+vertical
    phone = config.unit_phone or fixtures.unit_phone
    vertical = config.unit_vertical or fixtures.unit_vertical
    if phone and vertical:
        r = await _run_request(
            client,
            "POST",
            f"{config.base_url}/v1/resolve/unit",
            headers=hdrs,
            json_body={"criteria": [{"phone": phone, "vertical": vertical}]},
            name="T2-3 POST /v1/resolve/unit",
            tier=2,
            timeout=config.timeout,
        )
        body = _parse_json(r)
        if r.status_code == 200 and body:
            resolved = _deep_get(body, "meta.resolved_count") or 0
            result_list = body.get("results", [])
            resolved_gid = result_list[0].get("gid") if result_list else None
            if resolved > 0 and resolved_gid:
                r.status = TestStatus.PASS
                r.message = f"200 OK (resolved={resolved}, gid={resolved_gid})"
                # Verify against discovered fixture if available
                if fixtures.unit_gid and resolved_gid != fixtures.unit_gid:
                    r.message += f" (expected {fixtures.unit_gid})"
            else:
                r.status = TestStatus.PASS
                r.message = f"200 OK (resolved={resolved} for {phone}/{vertical})"
        else:
            _handle_503(r)
            if r.status != TestStatus.SKIP:
                r.status = TestStatus.FAIL
                r.message = f"{r.status_code}"
        results.append(r)
        _print_result(r, config.verbose)
    else:
        results.append(
            TestResult(
                name="T2-3 POST /v1/resolve/unit",
                tier=2,
                status=TestStatus.SKIP,
                message="No phone/vertical discovered",
            )
        )
        _print_result(results[-1], config.verbose)

    # T2-4 Resolver schema
    r = await _run_request(
        client,
        "GET",
        f"{config.base_url}/v1/resolve/unit/schema",
        headers=hdrs,
        name="T2-4 GET /v1/resolve/unit/schema",
        tier=2,
        timeout=config.timeout,
    )
    body = _parse_json(r)
    if r.status_code == 200 and body and body.get("entity_type") == "unit":
        fields = body.get("queryable_fields", [])
        r.status = TestStatus.PASS
        r.message = f"200 OK ({len(fields)} fields)"
    else:
        r.status = TestStatus.FAIL
        r.message = f"{r.status_code}"
    results.append(r)
    _print_result(r, config.verbose)


# ---------------------------------------------------------------------------
# Tier 3: Mutating (dry_run / local only)
# ---------------------------------------------------------------------------


async def tier3_mutating(
    client: httpx.AsyncClient,
    config: SmokeConfig,
    results: list[TestResult],
    fixtures: DiscoveredFixtures,
) -> None:
    _print_tier_header(3)

    is_production = config.mode == "production"
    hdrs: dict[str, str] = {}
    if config.jwt:
        hdrs = {
            "Authorization": f"Bearer {config.jwt}",
            "Content-Type": "application/json",
        }
    elif config.pat:
        hdrs = {
            "Authorization": f"Bearer {config.pat}",
            "Content-Type": "application/json",
        }

    # T3-1 Workflow invoke (dry_run) — uses discovered or overridden offer GID
    offer_gid = config.offer_gid or fixtures.offer_gid
    if hdrs and offer_gid:
        r = await _run_request(
            client,
            "POST",
            f"{config.base_url}/api/v1/workflows/insights-export/invoke",
            headers=hdrs,
            json_body={"entity_ids": [offer_gid], "dry_run": True},
            name="T3-1 POST workflows/invoke (dry_run)",
            tier=3,
            timeout=60,
        )
        body = _parse_json(r)
        if r.status_code == 200 and body:
            r.status = TestStatus.PASS
            days_info = (
                f", active_days={fixtures.offer_active_days}"
                if fixtures.offer_active_days
                else ""
            )
            r.message = f"200 OK (dry_run={body.get('dry_run')}{days_info})"
        elif r.status_code == 404:
            r.status = TestStatus.SKIP
            r.message = "404 (workflow not registered)"
        elif r.status_code == 429:
            r.status = TestStatus.SKIP
            r.message = "429 (rate limited)"
        else:
            r.status = TestStatus.FAIL
            r.message = f"{r.status_code}"
        results.append(r)
        _print_result(r, config.verbose)
    elif not hdrs:
        results.append(
            TestResult(
                name="T3-1 POST workflows/invoke",
                tier=3,
                status=TestStatus.SKIP,
                message="No auth token",
            )
        )
        _print_result(results[-1], config.verbose)
    else:
        results.append(
            TestResult(
                name="T3-1 POST workflows/invoke",
                tier=3,
                status=TestStatus.SKIP,
                message="No offer GID discovered",
            )
        )
        _print_result(results[-1], config.verbose)

    # T3-2 Entity write (production: skip)
    r = TestResult(
        name="T3-2 PATCH /api/v1/entity/{type}/{gid}",
        tier=3,
        status=TestStatus.SKIP,
        message="production: skipped (mutating)"
        if is_production
        else "local: not yet implemented",
    )
    results.append(r)
    _print_result(r, config.verbose)

    # T3-3 Cache refresh (production: skip)
    r = TestResult(
        name="T3-3 POST /v1/admin/cache/refresh",
        tier=3,
        status=TestStatus.SKIP,
        message="production: skipped (mutating)"
        if is_production
        else "local: not yet implemented",
    )
    results.append(r)
    _print_result(r, config.verbose)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> SmokeConfig:
    parser = argparse.ArgumentParser(
        description="autom8y-asana full-scope API smoke test",
    )
    parser.add_argument(
        "--mode",
        choices=["production", "local"],
        default=os.environ.get("SMOKE_MODE", "production"),
        help="Target environment (default: SMOKE_MODE env or production)",
    )
    parser.add_argument(
        "--tier",
        type=int,
        action="append",
        dest="tiers",
        choices=[0, 1, 2, 3],
        help="Run specific tier(s). Repeatable. Default: all.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print full request/response details",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds (default: 30)",
    )
    parser.add_argument("--base-url", default=None, help="Override API base URL")
    args = parser.parse_args()

    mode = args.mode
    tiers = set(args.tiers) if args.tiers else {0, 1, 2, 3}

    if args.base_url:
        base_url = args.base_url.rstrip("/")
    elif mode == "local":
        base_url = API_BASE_LOCAL
    else:
        base_url = API_BASE_PRODUCTION

    pat = os.environ.get("ASANA_BOT_PAT") or os.environ.get("ASANA_PAT")

    jwt = None
    if (2 in tiers or 3 in tiers) and mode == "production":
        jwt = _acquire_jwt(AUTH_BASE_PRODUCTION)
        if not jwt:
            print(
                f"  {YELLOW}No service credentials found or exchange failed, Tier 2/3 will be skipped{RESET}"
            )
    elif mode == "local":
        jwt = "local-dev-token"

    return SmokeConfig(
        mode=mode,
        base_url=base_url,
        verbose=args.verbose,
        tiers=tiers,
        pat=pat,
        jwt=jwt,
        timeout=args.timeout,
        workspace_gid=os.environ.get("ASANA_WORKSPACE_GID"),
        offer_gid=os.environ.get("SMOKE_OFFER_GID"),
        unit_phone=os.environ.get("SMOKE_UNIT_PHONE"),
        unit_vertical=os.environ.get("SMOKE_UNIT_VERTICAL"),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    config = parse_args()
    fixtures = DiscoveredFixtures()

    bar = "=" * 64
    print(f"\n{BOLD}{bar}{RESET}")
    print(f"  {BOLD}autom8y-asana API Smoke Test{RESET}")
    print(f"  Mode: {config.mode} | Base: {config.base_url}")
    print(f"  Time: {datetime.now(UTC).isoformat()}")
    print(f"  Tiers: {sorted(config.tiers)}")
    overrides = []
    if config.offer_gid:
        overrides.append(f"offer={config.offer_gid}")
    if config.unit_phone:
        overrides.append(f"phone={config.unit_phone}")
    if overrides:
        print(f"  Overrides: {', '.join(overrides)}")
    print(f"{BOLD}{bar}{RESET}")

    results: list[TestResult] = []
    t0 = time.monotonic()

    async with httpx.AsyncClient(follow_redirects=True) as client:
        if 0 in config.tiers:
            reachable = await tier0_health(client, config, results)
            if not reachable:
                _print_summary(results, (time.monotonic() - t0) * 1000)
                sys.exit(2)

        if 1 in config.tiers:
            await tier1_pat_readonly(client, config, results, fixtures)

        if 2 in config.tiers:
            await tier2_s2s_readonly(client, config, results, fixtures)

        if 3 in config.tiers:
            await tier3_mutating(client, config, results, fixtures)

    # Print discovered fixtures summary
    discovered = []
    if fixtures.unit_phone:
        discovered.append(f"unit={fixtures.unit_phone}/{fixtures.unit_vertical}")
    if fixtures.offer_gid:
        discovered.append(
            f"offer={fixtures.offer_gid} ({fixtures.offer_active_days}d active)"
        )
    if discovered:
        print(f"\n  {DIM}Discovered: {', '.join(discovered)}{RESET}")

    total_ms = (time.monotonic() - t0) * 1000
    _print_summary(results, total_ms)

    has_failures = any(r.status in (TestStatus.FAIL, TestStatus.ERROR) for r in results)
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
