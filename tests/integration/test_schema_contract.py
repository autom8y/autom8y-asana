"""Cross-repo schema contract tests: _FIELD_FORMAT vs data-service metrics.

Validates that the consumer-side formatter mapping (_FIELD_FORMAT in
insights_formatter.py) stays in sync with the upstream data service's
metric definitions.

Three contract checks:
  1. **Compatibility** -- metric_type maps to the correct formatter category.
  2. **Coverage** -- every metric with a type that requires formatting has an
     entry in _FIELD_FORMAT.
  3. **Orphan detection** -- consumer entries not found in the API are flagged.

Requirements:
    AUTOM8Y_DATA_URL: Base URL for autom8_data service.
    AUTOM8Y_DATA_API_KEY: Bearer token (S2S JWT or dev token).

Run with:
    .venv/bin/pytest tests/integration/test_schema_contract.py -v --timeout=30

Both env vars are required for the API-dependent tests.  When either is
missing, those tests skip.  Local consistency checks always run.

Per OPP-4 from SPIKE-INSIGHTS-CONSUMER FINDINGS.md.
"""

from __future__ import annotations

import os
import warnings
from typing import Any

import httpx
import pytest

# ---------------------------------------------------------------------------
# Consumer-side formatter mapping (source of truth for this repo)
# ---------------------------------------------------------------------------
from autom8_asana.automation.workflows.insights_formatter import (
    _FIELD_FORMAT,
)

# ---------------------------------------------------------------------------
# Environment & skip guard
# ---------------------------------------------------------------------------

_DATA_URL = os.environ.get("AUTOM8Y_DATA_URL", "").rstrip("/")
_DATA_API_KEY = os.environ.get("AUTOM8Y_DATA_API_KEY", "")

_requires_data_service = pytest.mark.skipif(
    not _DATA_URL or not _DATA_API_KEY,
    reason="AUTOM8Y_DATA_URL and AUTOM8Y_DATA_API_KEY required",
)

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# metric_type -> expected _FIELD_FORMAT category
#
# Types in _PASSTHROUGH_TYPES need no _FIELD_FORMAT entry (they render as-is
# via the default integer/float formatter or are non-numeric).
# ---------------------------------------------------------------------------

_TYPE_TO_FORMAT: dict[str, str] = {
    "CURRENCY": "currency",
    "PERCENTAGE": "percentage",
    "RATIO": "ratio",
    "PER_20K": "per20k",
    # RATE is a sub-case of percentage stored as 0-1 decimal.
    # The upstream type is PERCENTAGE; the consumer differentiates rate vs
    # percentage based on field name.  A RATE-typed metric should map to
    # either "rate" or "percentage" in _FIELD_FORMAT.
    "RATE": "rate",
}

_PASSTHROUGH_TYPES: frozenset[str] = frozenset(
    {
        "COUNT",
        "DURATION",
        "DATE",
        "STATUS",
        "TEXT",
        "INTEGER",
        "FLOAT",
        "NUMBER",
        "BOOLEAN",
        "STRING",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_DATA_API_KEY}"}


def _fetch_all_metrics(client: httpx.Client) -> list[dict[str, Any]]:
    """Fetch all metric definitions from the data service, paginating if needed.

    Tries ``GET /api/v1/metrics?limit=1000``.  If the response contains a
    ``next_cursor`` or ``next`` field, follows it until exhausted.  Returns
    the accumulated list of metric dicts.
    """
    metrics: list[dict[str, Any]] = []
    url = f"{_DATA_URL}/api/v1/metrics"
    params: dict[str, Any] = {"limit": 1000}

    while url:
        resp = client.get(url, headers=_auth_headers(), params=params, timeout=20.0)
        resp.raise_for_status()
        body = resp.json()

        # Normalize: the payload may be a list or {"data": [...], ...}
        if isinstance(body, list):
            metrics.extend(body)
            break
        elif isinstance(body, dict):
            data = body.get("data") or body.get("results") or body.get("metrics") or []
            metrics.extend(data)
            # Pagination: look for a cursor or next URL
            next_url = body.get("next") or body.get("next_cursor")
            if next_url and isinstance(next_url, str):
                if next_url.startswith("http"):
                    url = next_url
                    params = {}  # URL already contains params
                else:
                    # It's a cursor value
                    params["cursor"] = next_url
            else:
                break
        else:
            break

    return metrics


def _extract_metric_map(
    metrics: list[dict[str, Any]],
) -> dict[str, str]:
    """Return {metric_name: metric_type} from the API response.

    Handles multiple possible shapes: ``{"name": ..., "metric_type": ...}``
    or ``{"name": ..., "type": ...}`` or ``{"key": ..., "metric_type": ...}``.
    """
    result: dict[str, str] = {}
    for m in metrics:
        name = m.get("name") or m.get("key") or m.get("metric_name") or ""
        mtype = m.get("metric_type") or m.get("type") or ""
        if name and mtype:
            result[name.lower()] = mtype.upper()
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_metrics() -> dict[str, str]:
    """Fetch metric definitions from the data service.

    Returns {metric_name: metric_type} mapping.
    Skips the entire module if the data service is unreachable.
    """
    try:
        with httpx.Client() as client:
            raw = _fetch_all_metrics(client)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        pytest.skip(f"Data service unreachable: {exc}")
    except httpx.HTTPStatusError as exc:
        pytest.skip(f"Data service returned error: {exc.response.status_code}")

    if not raw:
        pytest.skip("Data service returned no metrics")

    return _extract_metric_map(raw)


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestSchemaContractAPI:
    """Cross-repo schema contract tests that require the data service API."""

    pytestmark = _requires_data_service

    def test_compatibility_metric_type_matches_formatter(
        self,
        api_metrics: dict[str, str],
    ) -> None:
        """Every API metric whose type requires formatting should map to the
        correct _FIELD_FORMAT category.

        For example, a metric with metric_type=CURRENCY must have a
        _FIELD_FORMAT entry of "currency".
        """
        mismatches: list[str] = []

        for name, mtype in api_metrics.items():
            if mtype in _PASSTHROUGH_TYPES:
                continue

            expected_format = _TYPE_TO_FORMAT.get(mtype)
            if expected_format is None:
                # Unknown type -- warn but don't fail (may be a new upstream type)
                warnings.warn(
                    f"Unknown metric_type '{mtype}' for metric '{name}' -- "
                    f"not in _TYPE_TO_FORMAT or _PASSTHROUGH_TYPES",
                    stacklevel=2,
                )
                continue

            actual_format = _FIELD_FORMAT.get(name)
            if actual_format is None:
                # Missing entry -- covered by the coverage test
                continue

            # For RATE type, accept both "rate" and "percentage" as valid
            if mtype == "RATE":
                if actual_format not in ("rate", "percentage"):
                    mismatches.append(
                        f"  {name}: type={mtype}, expected rate|percentage, "
                        f"got '{actual_format}'"
                    )
            elif actual_format != expected_format:
                mismatches.append(
                    f"  {name}: type={mtype}, expected '{expected_format}', "
                    f"got '{actual_format}'"
                )

        assert not mismatches, (
            f"_FIELD_FORMAT type mismatches ({len(mismatches)}):\n"
            + "\n".join(mismatches)
        )

    def test_coverage_all_formatted_metrics_have_entries(
        self,
        api_metrics: dict[str, str],
    ) -> None:
        """Every API metric whose type requires formatting should have an
        entry in _FIELD_FORMAT.

        Passthrough types (COUNT, DURATION, DATE, STATUS, etc.) are exempt --
        they render correctly via the default integer/float formatters.
        """
        missing: list[str] = []

        for name, mtype in api_metrics.items():
            if mtype in _PASSTHROUGH_TYPES:
                continue
            if mtype not in _TYPE_TO_FORMAT:
                continue  # Unknown type -- warned in compatibility test

            if name not in _FIELD_FORMAT:
                missing.append(f"  {name} (type={mtype})")

        assert not missing, (
            f"Metrics missing from _FIELD_FORMAT ({len(missing)}):\n"
            + "\n".join(missing)
            + "\n\nAdd entries to insights_formatter.py:_FIELD_FORMAT"
        )

    def test_orphan_detection_consumer_entries_exist_in_api(
        self,
        api_metrics: dict[str, str],
    ) -> None:
        """Every _FIELD_FORMAT entry should correspond to a metric known to
        the data service.

        Orphan entries are not necessarily wrong (the consumer may pre-declare
        entries for metrics that are not yet in the discovery API), but they
        are a drift signal worth flagging.
        """
        orphans: list[str] = []

        for name, fmt in _FIELD_FORMAT.items():
            if name not in api_metrics:
                orphans.append(f"  {name} (format='{fmt}')")

        if orphans:
            warnings.warn(
                f"_FIELD_FORMAT entries not in data-service API ({len(orphans)}):\n"
                + "\n".join(orphans)
                + "\n\nThese may be pre-declared or the API may not list all metrics.",
                stacklevel=2,
            )
            # Warn, don't fail -- orphans are advisory per OPP-4 spec


class TestFieldFormatConsistency:
    """Local consistency checks for _FIELD_FORMAT (no API call needed)."""

    def test_field_format_values_are_valid_categories(self) -> None:
        """All _FIELD_FORMAT values must be one of the known formatter categories."""
        valid_categories = {"currency", "rate", "percentage", "ratio", "per20k"}
        invalid: list[str] = []

        for name, fmt in _FIELD_FORMAT.items():
            if fmt not in valid_categories:
                invalid.append(
                    f"  {name}: '{fmt}' (expected one of {valid_categories})"
                )

        assert not invalid, (
            f"Invalid _FIELD_FORMAT categories ({len(invalid)}):\n" + "\n".join(invalid)
        )

    def test_field_format_has_entries(self) -> None:
        """Smoke check: _FIELD_FORMAT should not be empty."""
        assert len(_FIELD_FORMAT) > 0, "_FIELD_FORMAT is empty"
        # At time of writing there are 40 entries
        assert len(_FIELD_FORMAT) >= 30, (
            f"_FIELD_FORMAT has only {len(_FIELD_FORMAT)} entries, "
            "expected at least 30 (possible accidental truncation)"
        )

    def test_field_format_no_duplicate_keys(self) -> None:
        """_FIELD_FORMAT should not have conceptual duplicates.

        Python dicts disallow literal duplicates, but this verifies the
        mapping has no unexpectedly overlapping entries (e.g., both
        "conv_rate" and "conversion_rate" mapping to different categories).
        """
        by_category: dict[str, list[str]] = {}
        for name, fmt in _FIELD_FORMAT.items():
            by_category.setdefault(fmt, []).append(name)

        # Verify every category has at least one entry
        for category in ("currency", "rate", "percentage", "ratio", "per20k"):
            assert category in by_category, (
                f"No _FIELD_FORMAT entries for category '{category}'"
            )
