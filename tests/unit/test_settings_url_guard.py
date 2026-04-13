"""Unit tests for HAZ-1 fail-fast production URL guard.

Verifies that the Settings class rejects production URLs (containing
'autom8y.io') when AUTOM8Y_ENV is local or test, and
allows them in production/staging.

See TDD-LOCAL-DEV-ENV.md Section 6.3, Section 10 (HAZ-1).
"""

from __future__ import annotations

import pytest

from autom8_asana.settings import Settings, reset_settings


class TestProductionUrlGuard:
    """Verify fail-fast guard rejects production URLs in dev environments."""

    @pytest.fixture(autouse=True)
    def _reset(self):
        reset_settings()
        yield
        reset_settings()

    @pytest.mark.parametrize("env", ["local", "test"])
    def test_dev_env_with_production_data_url_raises(
        self, monkeypatch: pytest.MonkeyPatch, env: str
    ) -> None:
        """Setting a production AUTOM8Y_DATA_URL in dev env must fail."""
        monkeypatch.setenv("AUTOM8Y_ENV", env)
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "https://data.api.autom8y.io")
        # Ensure AUTH_JWKS_URL is NOT set to a production URL
        monkeypatch.delenv("AUTH_JWKS_URL", raising=False)

        with pytest.raises(ValueError, match="FATAL.*Production URL"):
            Settings()

    @pytest.mark.parametrize("env", ["local", "test"])
    def test_dev_env_with_production_jwks_url_raises(
        self, monkeypatch: pytest.MonkeyPatch, env: str
    ) -> None:
        """Setting a production AUTH_JWKS_URL in dev env must fail."""
        monkeypatch.setenv("AUTOM8Y_ENV", env)
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "http://data:8000")
        monkeypatch.setenv(
            "AUTH_JWKS_URL",
            "https://auth.api.autom8y.io/.well-known/jwks.json",
        )

        with pytest.raises(ValueError, match="FATAL.*Production URL.*AUTH_JWKS_URL"):
            Settings()

    @pytest.mark.parametrize("env", ["local", "test"])
    def test_dev_env_with_local_urls_passes(
        self, monkeypatch: pytest.MonkeyPatch, env: str
    ) -> None:
        """Local URLs in a dev environment must not trigger the guard."""
        monkeypatch.setenv("AUTOM8Y_ENV", env)
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "http://data:8000")
        monkeypatch.setenv(
            "AUTH_JWKS_URL",
            "http://auth:8000/.well-known/jwks.json",
        )

        settings = Settings()
        assert settings.data_service.url == "http://data:8000"

    def test_production_env_with_production_urls_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Production URLs in production environment must not trigger the guard."""
        monkeypatch.setenv("AUTOM8Y_ENV", "production")
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "https://data.api.autom8y.io")
        monkeypatch.setenv(
            "AUTH_JWKS_URL",
            "https://auth.api.autom8y.io/.well-known/jwks.json",
        )

        settings = Settings()
        assert settings.data_service.url == "https://data.api.autom8y.io"

    def test_staging_env_with_production_urls_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Production URLs in staging environment must not trigger the guard."""
        monkeypatch.setenv("AUTOM8Y_ENV", "staging")
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "https://data.api.autom8y.io")

        settings = Settings()
        assert settings.data_service.url == "https://data.api.autom8y.io"

    def test_default_development_env_with_default_urls_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default environment (local) with default data URL (localhost) passes.

        The asana DataServiceSettings defaults to http://localhost:8000
        which does NOT contain autom8y.io, so no guard fires.
        """
        monkeypatch.delenv("AUTOM8Y_ENV", raising=False)
        monkeypatch.delenv("AUTOM8Y_DATA_URL", raising=False)
        monkeypatch.delenv("AUTH_JWKS_URL", raising=False)

        settings = Settings()
        assert settings.autom8y_env == "local"
        assert "autom8y.io" not in settings.data_service.url

    def test_unset_env_with_production_urls_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Production URLs with AUTOM8Y_ENV *unset* must NOT fire the guard.

        This is the host-based smoke test scenario: sourcing .env/production
        sets production URLs but does not set AUTOM8Y_ENV. The guard
        only activates on explicit AUTOM8Y_ENV=local/test, not the default value.
        """
        monkeypatch.delenv("AUTOM8Y_ENV", raising=False)
        monkeypatch.setenv("AUTOM8Y_DATA_URL", "https://data.api.autom8y.io")
        monkeypatch.setenv(
            "AUTH_JWKS_URL",
            "https://auth.api.autom8y.io/.well-known/jwks.json",
        )

        settings = Settings()
        assert settings.data_service.url == "https://data.api.autom8y.io"
