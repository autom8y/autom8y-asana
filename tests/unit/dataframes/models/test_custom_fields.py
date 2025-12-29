"""Tests for custom_fields module.

This module is deprecated (per ADR-0034) but retained for backward
compatibility. These tests verify the deprecation warning and the
validate_gids_configured() function behavior.
"""

from __future__ import annotations

import warnings

import pytest


class TestCustomFieldsDeprecation:
    """Tests for deprecation warning on module import."""

    def test_module_import_emits_deprecation_warning(self) -> None:
        """Importing the module should emit a DeprecationWarning."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # Re-import to trigger warning
            import importlib
            import sys

            # Remove from cache to force re-import
            module_name = "autom8_asana.dataframes.models.custom_fields"
            if module_name in sys.modules:
                del sys.modules[module_name]

            import autom8_asana.dataframes.models.custom_fields  # noqa: F401

            # Re-add to avoid affecting other tests
            importlib.reload(sys.modules.get(module_name))

        # Check that a deprecation warning was issued
        deprecation_warnings = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_warnings) >= 1, "Should emit DeprecationWarning on import"

        # Verify the warning message mentions ADR-0034
        warning_msg = str(deprecation_warnings[0].message)
        assert "deprecated" in warning_msg.lower()


class TestGIDConstants:
    """Tests for GID constant definitions."""

    def test_mrr_gid_is_string(self) -> None:
        """MRR_GID should be a string."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from autom8_asana.dataframes.models.custom_fields import MRR_GID

        assert isinstance(MRR_GID, str)

    def test_all_gid_constants_are_strings(self) -> None:
        """All *_GID constants should be strings."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from autom8_asana.dataframes.models import custom_fields

        gid_constants = [
            name for name in dir(custom_fields)
            if name.endswith("_GID") and not name.startswith("_")
        ]

        assert len(gid_constants) > 0, "Should have at least one GID constant"

        for name in gid_constants:
            value = getattr(custom_fields, name)
            assert isinstance(value, str), f"{name} should be a string"

    def test_gid_constants_are_placeholders(self) -> None:
        """All GID constants should be placeholder values (for MVP)."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from autom8_asana.dataframes.models import custom_fields

        gid_constants = [
            name for name in dir(custom_fields)
            if name.endswith("_GID") and not name.startswith("_")
        ]

        for name in gid_constants:
            value = getattr(custom_fields, name)
            assert value.startswith("PLACEHOLDER_"), (
                f"{name} should be a placeholder value, got {value}"
            )


class TestValidateGidsConfigured:
    """Tests for validate_gids_configured() function."""

    def test_returns_list_of_placeholders(self) -> None:
        """validate_gids_configured() should return list of placeholder GIDs."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from autom8_asana.dataframes.models.custom_fields import (
                validate_gids_configured,
            )

        placeholders = validate_gids_configured()

        assert isinstance(placeholders, list)
        assert len(placeholders) > 0, "Should detect placeholder values"

    def test_returns_expected_placeholder_names(self) -> None:
        """validate_gids_configured() should return names of unconfigured GIDs."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from autom8_asana.dataframes.models.custom_fields import (
                validate_gids_configured,
            )

        placeholders = validate_gids_configured()

        # All known GID constants should be in the placeholder list
        expected_gids = [
            "MRR_GID",
            "WEEKLY_AD_SPEND_GID",
            "PRODUCTS_GID",
            "LANGUAGES_GID",
            "DISCOUNT_GID",
            "VERTICAL_GID",
            "SPECIALTY_GID",
            "FULL_NAME_GID",
            "NICKNAME_GID",
            "CONTACT_PHONE_GID",
            "CONTACT_EMAIL_GID",
            "POSITION_GID",
            "EMPLOYEE_ID_GID",
            "CONTACT_URL_GID",
            "TIME_ZONE_GID",
            "CITY_GID",
        ]

        for expected in expected_gids:
            assert expected in placeholders, f"{expected} should be in placeholders"

    def test_returns_empty_list_when_all_configured(self, monkeypatch) -> None:
        """validate_gids_configured() should return empty list when configured."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from autom8_asana.dataframes.models import custom_fields
            from autom8_asana.dataframes.models.custom_fields import (
                validate_gids_configured,
            )

        # Patch all GID constants to be non-placeholder values
        gid_constants = [
            name for name in dir(custom_fields)
            if name.endswith("_GID") and not name.startswith("_")
        ]

        for name in gid_constants:
            monkeypatch.setattr(custom_fields, name, "1234567890123")

        placeholders = validate_gids_configured()

        assert placeholders == [], "Should return empty list when all GIDs configured"

    def test_detects_mixed_configuration(self, monkeypatch) -> None:
        """validate_gids_configured() should detect partially configured GIDs."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from autom8_asana.dataframes.models import custom_fields
            from autom8_asana.dataframes.models.custom_fields import (
                validate_gids_configured,
            )

        # Configure only MRR_GID
        monkeypatch.setattr(custom_fields, "MRR_GID", "1234567890123")

        placeholders = validate_gids_configured()

        assert "MRR_GID" not in placeholders, "Configured GID should not be in list"
        assert len(placeholders) > 0, "Other GIDs should still be placeholders"
