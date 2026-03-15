"""Shared fixtures and helpers for DataServiceClient tests.

Extracted from test_client.py as part of D-028 test file restructuring.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def enable_insights_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable insights feature flag for testing."""
    monkeypatch.setenv("AUTOM8Y_DATA_INSIGHTS_ENABLED", "true")


@pytest.fixture
def sample_pvps() -> list:
    """Create sample PhoneVerticalPairs for batch testing."""
    from autom8_asana.models.contracts import PhoneVerticalPair

    return [
        PhoneVerticalPair(office_phone="+17705753103", vertical="chiropractic"),
        PhoneVerticalPair(office_phone="+14155551234", vertical="dental"),
        PhoneVerticalPair(office_phone="+12125559876", vertical="medical"),
    ]


def make_insights_response(factory: str = "account", spend: float = 100.0) -> dict:
    """Create a valid insights response for testing."""
    return {
        "data": [{"spend": spend, "leads": 10}],
        "metadata": {
            "factory": factory,
            "row_count": 1,
            "column_count": 2,
            "columns": [
                {"name": "spend", "dtype": "float64"},
                {"name": "leads", "dtype": "int64"},
            ],
            "cache_hit": False,
            "duration_ms": 50.0,
        },
    }


def make_batch_insights_response(
    pvps: list,
    factory: str = "account",
    spend: float = 100.0,
    failed_indices: list[int] | None = None,
) -> dict:
    """Create a valid batch insights response for testing.

    Per IMP-20: autom8_data returns all PVP results in a single response
    with per-entity office_phone and vertical fields in the data list,
    and per-entity errors in the errors list.

    Args:
        pvps: List of PhoneVerticalPair objects to include in response.
        factory: Factory name for metadata.
        spend: Spend value for each entity.
        failed_indices: Optional list of PVP indices that should fail.
            These will be placed in the errors list instead of data.
    """
    failed_indices = failed_indices or []
    data = []
    errors = []

    for i, pvp in enumerate(pvps):
        if i in failed_indices:
            errors.append(
                {
                    "office_phone": pvp.office_phone,
                    "vertical": pvp.vertical,
                    "error": "No insights found for business",
                }
            )
        else:
            data.append(
                {
                    "office_phone": pvp.office_phone,
                    "vertical": pvp.vertical,
                    "spend": spend,
                    "leads": 10,
                }
            )

    status_code = 207 if errors and data else 200
    response_dict = {
        "data": data,
        "metadata": {
            "factory": factory,
            "row_count": len(data),
            "column_count": 4,
            "columns": [
                {"name": "office_phone", "dtype": "string"},
                {"name": "vertical", "dtype": "string"},
                {"name": "spend", "dtype": "float64"},
                {"name": "leads", "dtype": "int64"},
            ],
            "cache_hit": False,
            "duration_ms": 50.0,
        },
    }
    if errors:
        response_dict["errors"] = errors

    return response_dict, status_code


def _make_disabled_settings_mock() -> MagicMock:
    """Create a mock Settings object with insights disabled.

    Per D-011: Settings reads env vars at construction time and caches the result.
    Tests must patch get_settings() directly rather than setting env vars.
    """
    mock_settings = MagicMock()
    mock_settings.data_service.insights_enabled = False
    return mock_settings
