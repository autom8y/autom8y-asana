"""Fixture infrastructure for Aegis synthetic coverage tests (autom8y-asana).

Provides:
- Module-scoped TestClient with mocked Asana dependencies (no local database)
- Environment setup: AUTH_DEV_MODE, AUTOM8Y_ENV, IDEMPOTENCY_STORE_BACKEND
- Lifespan neutralization: _discover_entity_projects mocked, cache warming no-op
- Memory measurement fixtures (per-endpoint + per-category RSS tracking)
- Coverage summary, JSON report emission, and baseline management
- Per-endpoint regression detection against saved baselines

Ported from autom8y-data Phase 1 (shallow mock strategy per INTEGRATE spike).
Architecture difference: autom8y-asana has NO local database. Instead of
SQLite entity seeding, we mock get_asana_client_from_context globally.

Memory measurement and report generation copied VERBATIM from autom8y-data
conftest (stdlib-only, zero repo-specific imports).
"""

from __future__ import annotations

import datetime
import gc
import json
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# =============================================================================
# Constants
# =============================================================================

REPORT_PATH = Path(__file__).parent.parent.parent / "aegis-report.json"

# Max RSS growth total run (MB) -- asana has ~54 operations vs data's 187
MAX_RSS_GROWTH_MB = 100

# Max RSS growth per individual endpoint (MB)
MAX_RSS_GROWTH_PER_ENDPOINT_MB = 50

# =============================================================================
# Module-level state shared between fixtures and test module
# =============================================================================

# Results accumulator (populated by tests, printed in summary)
_results: list[dict] = []

# Per-category RSS tracking
_category_rss: dict[str, dict] = {}
_current_category: list[str] = [""]

# Memory report data (written by memory_guard, read by coverage_summary)
_memory_report: dict[str, Any] = {}


# =============================================================================
# Environment Setup
# =============================================================================


def _setup_env() -> None:
    """Configure environment variables before create_app().

    Sets test-mode variables that prevent real external connections:
    - AUTOM8Y_ENV=test: application test mode
    - AUTH_DEV_MODE=true: bypass JWT/PAT validation
    - IDEMPOTENCY_STORE_BACKEND=noop: prevent DynamoDB connection
    """
    os.environ["AUTH_DEV_MODE"] = "true"
    os.environ["AUTOM8Y_ENV"] = "test"
    os.environ["IDEMPOTENCY_STORE_BACKEND"] = "noop"


# =============================================================================
# Mock Infrastructure
# =============================================================================


def _build_mock_asana_client() -> MagicMock:
    """Build a shallow MockClientBuilder-style AsanaClient.

    Follows the existing test pattern from tests/conftest.py MockClientBuilder.
    Returns a MagicMock with sub-clients configured to return canned responses
    for the most common operations.
    """
    client = MagicMock()
    client._log = None
    client.default_workspace_gid = "1111111111"

    # HTTP client
    http_mock = AsyncMock()
    http_mock.request = AsyncMock(return_value={"data": {}})
    http_mock.get = AsyncMock(return_value={})
    http_mock.get_paginated = AsyncMock(return_value=([], None))
    client._http = http_mock

    # Tasks sub-client
    tasks_mock = MagicMock()
    default_task = {
        "gid": "2222222222",
        "name": "Test Task",
        "notes": "Task notes",
        "completed": False,
    }
    tasks_mock.get_async = AsyncMock(return_value=default_task)
    tasks_mock.create_async = AsyncMock(return_value=default_task)
    tasks_mock.update_async = AsyncMock(return_value=default_task)
    tasks_mock.delete_async = AsyncMock(return_value=None)
    task_model = MagicMock()
    task_model.model_dump = MagicMock(return_value=default_task)
    tasks_mock.add_tag_async = AsyncMock(return_value=task_model)
    tasks_mock.remove_tag_async = AsyncMock(return_value=task_model)
    tasks_mock.move_to_section_async = AsyncMock(return_value=task_model)
    tasks_mock.set_assignee_async = AsyncMock(return_value=task_model)
    tasks_mock.add_to_project_async = AsyncMock(return_value=task_model)
    tasks_mock.remove_from_project_async = AsyncMock(return_value=task_model)
    tasks_mock.duplicate_async = AsyncMock(return_value=default_task)
    client.tasks = tasks_mock

    # Projects sub-client
    projects_mock = MagicMock()
    default_project = {
        "gid": "3333333333",
        "name": "Test Project",
        "notes": "Project notes",
        "workspace": {"gid": "1111111111", "name": "Test Workspace"},
        "archived": False,
    }
    projects_mock.get_async = AsyncMock(return_value=default_project)
    projects_mock.create_async = AsyncMock(return_value=default_project)
    projects_mock.update_async = AsyncMock(return_value=default_project)
    projects_mock.delete_async = AsyncMock(return_value=None)
    projects_mock.add_members_async = AsyncMock(return_value=default_project)
    projects_mock.remove_members_async = AsyncMock(return_value=default_project)
    mock_iterator = MagicMock()
    mock_iterator.collect = AsyncMock(return_value=[])
    projects_mock.list_async = MagicMock(return_value=mock_iterator)
    client.projects = projects_mock

    # Sections sub-client
    sections_mock = MagicMock()
    default_section = {
        "gid": "4444444444",
        "name": "Test Section",
        "project": {"gid": "3333333333", "name": "Test Project"},
    }
    sections_mock.get_async = AsyncMock(return_value=default_section)
    sections_mock.create_async = AsyncMock(return_value=default_section)
    sections_mock.update_async = AsyncMock(return_value=default_section)
    sections_mock.delete_async = AsyncMock(return_value=None)
    sections_mock.add_task_async = AsyncMock(return_value=None)
    sections_mock.insert_section_async = AsyncMock(return_value=None)
    client.sections = sections_mock

    # Users sub-client
    users_mock = MagicMock()
    users_mock.me_async = AsyncMock(return_value={
        "gid": "1234567890",
        "name": "Test User",
        "email": "test@example.com",
    })
    users_mock.get_async = AsyncMock(return_value={
        "gid": "9876543210",
        "name": "Other User",
        "email": "other@example.com",
    })
    client.users = users_mock

    # Workspaces sub-client
    workspaces_mock = MagicMock()
    workspaces_mock.get_async = AsyncMock(return_value={
        "gid": "1111111111",
        "name": "Test Workspace",
        "is_organization": True,
    })
    client.workspaces = workspaces_mock

    # Batch sub-client
    batch_mock = MagicMock()
    batch_mock.execute_async = AsyncMock(return_value=[])
    client.batch = batch_mock

    # Async context manager support
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    return client


def _populate_test_registry():
    """Reset and re-populate EntityProjectRegistry with test data.

    Mirrors the pattern from tests/unit/api/conftest.py.
    """
    from autom8_asana.services.resolver import EntityProjectRegistry

    EntityProjectRegistry.reset()
    registry = EntityProjectRegistry.get_instance()
    for entity_type, gid, name in [
        ("offer", "1143843662099250", "Business Offers"),
        ("unit", "1201081073731555", "Business Units"),
        ("contact", "1200775689604552", "Contacts"),
        ("business", "1234567890123456", "Business"),
    ]:
        registry.register(
            entity_type=entity_type,
            project_gid=gid,
            project_name=name,
        )
    return registry


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def synthetic_client():
    """Module-scoped TestClient with shallow Asana mock overrides.

    Creates the full app stack once per module:
    1. Environment setup (AUTH_DEV_MODE, IDEMPOTENCY_STORE_BACKEND)
    2. Mock _discover_entity_projects to avoid live Asana API call
    3. Mock get_asana_client_from_context for all route handlers
    4. Mock get_auth_context for auth bypass

    No database setup needed -- autom8y-asana is API-passthrough architecture.
    """
    _setup_env()

    _mock_client = _build_mock_asana_client()

    with patch(
        "autom8_asana.api.lifespan._discover_entity_projects",
        new_callable=AsyncMock,
    ) as mock_discover:

        async def setup_registry(app):
            registry = _populate_test_registry()
            app.state.entity_project_registry = registry

        mock_discover.side_effect = setup_registry

        from autom8_asana.api.main import create_app
        from autom8_asana.api.dependencies import (
            AuthContext,
            get_auth_context,
            get_asana_client_from_context,
        )
        from autom8_asana.auth.dual_mode import AuthMode

        app = create_app()

        # Override auth context to bypass JWT/PAT validation
        async def _mock_get_auth_context() -> AuthContext:
            return AuthContext(
                mode=AuthMode.JWT,
                asana_pat="test_bot_pat",
                caller_service="autom8_data",
            )

        app.dependency_overrides[get_auth_context] = _mock_get_auth_context

        # Override Asana client to return shallow mock
        async def _mock_get_asana_client():
            yield _mock_client

        app.dependency_overrides[get_asana_client_from_context] = _mock_get_asana_client

        with TestClient(app, raise_server_exceptions=False) as client:
            yield client


# =============================================================================
# Memory Measurement Helpers (VERBATIM from autom8y-data conftest)
# =============================================================================


def _rss_mb() -> float:
    """Process peak (high-water mark) RSS in megabytes.

    Uses resource.getrusage(RUSAGE_SELF).ru_maxrss which returns the maximum
    RSS the process has ever used. This is monotonically non-decreasing:
    - macOS: ru_maxrss is in bytes
    - Linux: ru_maxrss is in kilobytes

    Use this ONLY for the total-run peak-RSS assertion (memory_guard) where
    the high-water mark is the correct metric. Do NOT use for per-endpoint
    delta measurement -- peak RSS cannot decrease between endpoints, making
    deltas always zero after the first peak. Use _current_rss_mb() instead.
    """
    usage = resource.getrusage(resource.RUSAGE_SELF)
    if sys.platform == "darwin":
        return usage.ru_maxrss / (1024 * 1024)  # macOS: bytes
    return usage.ru_maxrss / 1024  # Linux: kilobytes


def _current_rss_mb() -> float:
    """Current (not peak) process RSS in megabytes.

    Returns the actual resident set size at the moment of the call. This is
    the PRIMARY measurement function for all per-endpoint and per-category
    delta tracking, since it can both increase and decrease between calls.

    Platform behavior:
    - macOS: subprocess call to `ps -o rss=` (~5ms overhead per call).
      With 54 operations, total overhead is ~0.3s, within budget.
    - Linux: reads /proc/self/statm (near-zero overhead, no subprocess).
    """
    if sys.platform == "darwin":
        out = subprocess.check_output(
            ["ps", "-p", str(os.getpid()), "-o", "rss="],
            text=True,
        )
        return int(out.strip()) / 1024  # KB -> MB
    else:
        with open(f"/proc/{os.getpid()}/statm") as f:
            resident_pages = int(f.read().split()[1])
        return resident_pages * resource.getpagesize() / (1024 * 1024)


def _record_category_boundary(new_category: str) -> None:
    """Record RSS at a category transition boundary."""
    old_category = _current_category[0]

    gc.collect()
    rss_now = _current_rss_mb()

    if old_category and old_category in _category_rss:
        _category_rss[old_category]["rss_after"] = rss_now

    if new_category:
        gc.collect()
        rss_now = _current_rss_mb()
        _category_rss[new_category] = {
            "rss_before": rss_now,
            "rss_after": 0.0,
            "operations": 0,
        }

    _current_category[0] = new_category


# =============================================================================
# Memory Guard Fixture (VERBATIM from autom8y-data conftest)
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def memory_guard(synthetic_client: TestClient) -> None:
    """Measure RSS before/after all tests; assert total growth < budget."""
    gc.collect()
    baseline = _rss_mb()
    baseline_current = _current_rss_mb()
    yield
    # Close out the final category
    if _current_category[0] and _current_category[0] in _category_rss:
        gc.collect()
        _category_rss[_current_category[0]]["rss_after"] = _current_rss_mb()

    gc.collect()
    final = _rss_mb()
    final_current = _current_rss_mb()
    growth = final - baseline

    _memory_report["baseline_rss_mb"] = round(baseline_current, 1)
    _memory_report["final_rss_mb"] = round(final_current, 1)
    _memory_report["peak_rss_baseline_mb"] = round(baseline, 1)
    _memory_report["peak_rss_final_mb"] = round(final, 1)
    _memory_report["total_growth_mb"] = round(growth, 1)

    print(f"\n[memory_guard] Peak RSS baseline={baseline:.1f}MB final={final:.1f}MB growth={growth:.1f}MB")
    print(f"[memory_guard] Current RSS baseline={baseline_current:.1f}MB final={final_current:.1f}MB")

    print("\n[memory_guard] Per-category RSS deltas:")
    for cat, info in sorted(_category_rss.items()):
        delta = info["rss_after"] - info["rss_before"]
        print(
            f"  {cat:<25} before={info['rss_before']:.1f}MB "
            f"after={info['rss_after']:.1f}MB delta={delta:+.1f}MB "
            f"({info['operations']} ops)"
        )

    assert growth < MAX_RSS_GROWTH_MB, (
        f"Total RSS growth {growth:.1f}MB exceeds {MAX_RSS_GROWTH_MB}MB limit. "
        f"OOM regression detected."
    )


# =============================================================================
# Coverage Summary + JSON Report (VERBATIM from autom8y-data conftest)
# =============================================================================


# Baseline file location for regression detection
BASELINES_DIR = Path(__file__).parent.parent.parent / ".know" / "aegis"
BASELINES_PATH = BASELINES_DIR / "baselines.json"

# Regression threshold: flag if current delta exceeds baseline by 50%
REGRESSION_THRESHOLD = 1.5


def _load_baselines() -> dict | None:
    """Load existing baselines.json for regression comparison."""
    if not BASELINES_PATH.exists():
        return None
    try:
        with open(BASELINES_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[aegis] WARNING: Could not load baselines: {e}")
        return None


def _detect_regressions(
    results: list[dict], baselines: dict | None
) -> list[dict]:
    """Detect per-endpoint memory regressions against baselines and budget."""
    regressions: list[dict] = []
    baseline_data = baselines.get("baselines", {}) if baselines else {}

    for r in results:
        rss_delta = r.get("rss_delta_mb", 0.0)
        endpoint_key = f"{r['method']} {r['path']}"

        if rss_delta > MAX_RSS_GROWTH_PER_ENDPOINT_MB:
            regressions.append({
                "endpoint": endpoint_key,
                "rss_delta_mb": rss_delta,
                "reason": f"exceeds per-endpoint budget ({MAX_RSS_GROWTH_PER_ENDPOINT_MB}MB)",
            })
            continue

        if endpoint_key in baseline_data:
            baseline_delta = baseline_data[endpoint_key].get("rss_delta_mb", 0.0)
            if baseline_delta > 0.1 and rss_delta > baseline_delta * REGRESSION_THRESHOLD:
                regressions.append({
                    "endpoint": endpoint_key,
                    "rss_delta_mb": rss_delta,
                    "baseline_delta_mb": baseline_delta,
                    "reason": (
                        f"regression: {rss_delta:.1f}MB vs baseline {baseline_delta:.1f}MB "
                        f"(>{REGRESSION_THRESHOLD:.0%} threshold)"
                    ),
                })

    return regressions


def _write_baselines(results: list[dict]) -> None:
    """Write per-endpoint baseline file for future regression detection."""
    baselines: dict[str, dict] = {}
    for r in results:
        endpoint_key = f"{r['method']} {r['path']}"
        baselines[endpoint_key] = {
            "rss_delta_mb": round(r.get("rss_delta_mb", 0.0), 2),
            "duration_ms": round(r.get("duration_ms", 0.0), 1),
        }

    baseline_doc = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "platform": platform.system().lower(),
        "spec_path": str(
            Path(__file__).parent.parent.parent / "docs" / "api-reference" / "openapi.json"
        ),
        "total_operations": len(results),
        "baselines": baselines,
    }

    try:
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        with open(BASELINES_PATH, "w") as f:
            json.dump(baseline_doc, f, indent=2)
        print(f"[aegis] Baselines written to {BASELINES_PATH}")
    except Exception as e:
        print(f"[aegis] WARNING: Failed to write baselines: {e}")


@pytest.fixture(scope="module", autouse=True)
def coverage_summary() -> None:
    """Print per-run coverage summary, emit aegis-report.json, and manage baselines."""
    yield

    if not _results:
        return

    total = len(_results)
    passed = sum(1 for r in _results if r["outcome"] == "PASSED")
    expected_5xx = sum(1 for r in _results if r["outcome"] == "EXPECTED-5xx")
    failed = sum(1 for r in _results if r["outcome"] == "FAILED")
    skipped = sum(1 for r in _results if r["outcome"].startswith("SKIPPED"))

    schema_checked = sum(1 for r in _results if r.get("schema_valid") is not None)
    schema_valid_count = sum(1 for r in _results if r.get("schema_valid") is True)
    schema_invalid_count = sum(1 for r in _results if r.get("schema_valid") is False)

    active_count = passed + expected_5xx + skipped
    active_pct = round(100 * active_count / total, 1) if total else 0

    lines = [
        "",
        "=" * 70,
        "AEGIS SYNTHETIC COVERAGE SUMMARY",
        "=" * 70,
        f"  Total operations: {total}",
        f"  PASSED (2xx/4xx): {passed} ({100*passed//total}%)",
        f"  EXPECTED-5xx:     {expected_5xx} ({100*expected_5xx//total}%)",
        f"  SKIPPED:          {skipped} ({100*skipped//total}%)",
        f"  FAILED:           {failed} ({100*failed//total}%)",
        (
            f"  Effective coverage (passed+expected+skipped): "
            f"{active_count}/{total} "
            f"({active_pct}%)"
        ),
        "",
        f"  Schema validation: {schema_checked} checked, "
        f"{schema_valid_count} valid, {schema_invalid_count} invalid",
        "",
    ]

    # Per-category breakdown
    categories: dict[str, dict] = {}
    for r in _results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "expected_5xx": 0, "failed": 0, "skipped": 0}
        categories[cat]["total"] += 1
        outcome = r["outcome"]
        if outcome == "PASSED":
            categories[cat]["passed"] += 1
        elif outcome == "EXPECTED-5xx":
            categories[cat]["expected_5xx"] += 1
        elif outcome == "FAILED":
            categories[cat]["failed"] += 1
        elif outcome.startswith("SKIPPED"):
            categories[cat]["skipped"] += 1

    lines.append(f"  {'Category':<30} {'Total':>5} {'Pass':>5} {'Exp5':>5} {'Skip':>5} {'Fail':>5}")
    lines.append(f"  {'-'*30} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5}")
    for cat, counts in sorted(categories.items()):
        lines.append(
            f"  {cat:<30} {counts['total']:>5} {counts['passed']:>5} "
            f"{counts['expected_5xx']:>5} {counts['skipped']:>5} {counts['failed']:>5}"
        )

    # Schema validation findings
    schema_invalids = [r for r in _results if r.get("schema_valid") is False]
    if schema_invalids:
        lines.append("")
        lines.append("  SCHEMA VALIDATION FINDINGS (spec-implementation drift):")
        for r in schema_invalids:
            lines.append(f"    {r['method']:<7} {r['path']} -> {r['status']}")
            if r.get("schema_error"):
                lines.append(f"           {r['schema_error'][:80]}")

    # Per-endpoint memory regressions
    baselines = _load_baselines()
    regressions = _detect_regressions(_results, baselines)
    if regressions:
        lines.append("")
        lines.append("  MEMORY REGRESSIONS:")
        for reg in regressions:
            lines.append(f"    {reg['endpoint']}: {reg['reason']}")

    lines.append("")
    if failed > 0:
        lines.append("  FAILED OPERATIONS:")
        for r in _results:
            if r["outcome"] == "FAILED":
                lines.append(f"    {r['method']:<7} {r['path']} -> {r['status']}")
                if "note" in r:
                    lines.append(f"           {r['note']}")
    lines.append("=" * 70)

    print("\n".join(lines))

    # ---- Emit aegis-report.json ----
    per_category_report = {}
    for cat, info in sorted(_category_rss.items()):
        delta = info["rss_after"] - info["rss_before"]
        per_category_report[cat] = {
            "rss_before": round(info["rss_before"], 1),
            "rss_after": round(info["rss_after"], 1),
            "delta_mb": round(delta, 1),
            "operations": info["operations"],
        }

    report = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "spec_path": str(Path(__file__).parent.parent.parent / "docs" / "api-reference" / "openapi.json"),
        "total_operations": total,
        "coverage": {
            "passed": passed,
            "expected_5xx": expected_5xx,
            "skipped": skipped,
            "failed": failed,
            "active_coverage_pct": active_pct,
        },
        "schema_validation": {
            "checked": schema_checked,
            "valid": schema_valid_count,
            "invalid": schema_invalid_count,
            "findings": [
                {
                    "path": r["path"],
                    "method": r["method"],
                    "status": r["status"],
                    "error": r.get("schema_error", ""),
                }
                for r in schema_invalids
            ],
        },
        "memory": {
            "baseline_rss_mb": _memory_report.get("baseline_rss_mb", 0.0),
            "final_rss_mb": _memory_report.get("final_rss_mb", 0.0),
            "total_growth_mb": _memory_report.get("total_growth_mb", 0.0),
            "budget_mb": MAX_RSS_GROWTH_MB,
            "per_endpoint_budget_mb": MAX_RSS_GROWTH_PER_ENDPOINT_MB,
            "per_category": per_category_report,
            "regressions": [
                {
                    "endpoint": reg["endpoint"],
                    "rss_delta_mb": reg["rss_delta_mb"],
                    "reason": reg["reason"],
                    **({"baseline_delta_mb": reg["baseline_delta_mb"]}
                       if "baseline_delta_mb" in reg else {}),
                }
                for reg in regressions
            ],
        },
        "operations": [
            {
                "path": r["path"],
                "method": r["method"],
                "category": r["category"],
                "status": r.get("status"),
                "outcome": r["outcome"],
                "duration_ms": r.get("duration_ms", 0.0),
                "rss_before_mb": r.get("rss_before_mb", 0.0),
                "rss_after_mb": r.get("rss_after_mb", 0.0),
                "rss_delta_mb": r.get("rss_delta_mb", 0.0),
                **({"schema_valid": r["schema_valid"]} if "schema_valid" in r else {}),
            }
            for r in _results
        ],
    }

    try:
        with open(REPORT_PATH, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[aegis] Report written to {REPORT_PATH}")
    except Exception as e:
        print(f"\n[aegis] WARNING: Failed to write report: {e}")

    # ---- Write baselines ----
    _write_baselines(_results)
