"""Tests for authentication providers."""

from __future__ import annotations

import pytest

from autom8_asana._defaults.auth import EnvAuthProvider, NotConfiguredAuthProvider
from autom8_asana.exceptions import AuthenticationError


class TestEnvAuthProvider:
    """Tests for EnvAuthProvider."""

    def test_reads_from_environment_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret reads value from environment variable."""
        monkeypatch.setenv("ASANA_PAT", "my-secret-token")
        provider = EnvAuthProvider()

        result = provider.get_secret("ASANA_PAT")

        assert result == "my-secret-token"

    def test_raises_authentication_error_when_not_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret raises AuthenticationError when env var not set."""
        monkeypatch.delenv("ASANA_PAT", raising=False)
        provider = EnvAuthProvider()

        with pytest.raises(AuthenticationError) as exc_info:
            provider.get_secret("ASANA_PAT")

        assert "ASANA_PAT" in str(exc_info.value)
        assert "not set" in str(exc_info.value)

    def test_raises_authentication_error_for_empty_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret raises AuthenticationError when env var is empty string."""
        monkeypatch.setenv("ASANA_PAT", "")
        provider = EnvAuthProvider()

        with pytest.raises(AuthenticationError) as exc_info:
            provider.get_secret("ASANA_PAT")

        assert "ASANA_PAT" in str(exc_info.value)
        assert "empty" in str(exc_info.value)

    def test_raises_authentication_error_for_whitespace_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret raises AuthenticationError when env var is whitespace only."""
        monkeypatch.setenv("ASANA_PAT", "   \t\n  ")
        provider = EnvAuthProvider()

        with pytest.raises(AuthenticationError) as exc_info:
            provider.get_secret("ASANA_PAT")

        assert "ASANA_PAT" in str(exc_info.value)
        assert "empty" in str(exc_info.value)

    def test_reads_custom_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_secret works with custom environment variable names."""
        monkeypatch.setenv("MY_CUSTOM_TOKEN", "custom-token-value")
        provider = EnvAuthProvider()

        result = provider.get_secret("MY_CUSTOM_TOKEN")

        assert result == "custom-token-value"

    def test_preserves_whitespace_in_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_secret preserves leading/trailing whitespace in non-empty values.

        Note: The token itself has surrounding whitespace, but it's not empty
        after stripping, so it should be returned as-is (the actual token value).
        """
        # Token with content but also some spaces - this is valid
        monkeypatch.setenv("ASANA_PAT", "  token-with-spaces  ")
        provider = EnvAuthProvider()

        # The validation strips to check if empty, but returns the original value
        result = provider.get_secret("ASANA_PAT")

        assert result == "  token-with-spaces  "


class TestNotConfiguredAuthProvider:
    """Tests for NotConfiguredAuthProvider."""

    def test_always_raises_authentication_error(self) -> None:
        """get_secret always raises AuthenticationError."""
        provider = NotConfiguredAuthProvider()

        with pytest.raises(AuthenticationError) as exc_info:
            provider.get_secret("ASANA_PAT")

        assert "authentication" in str(exc_info.value).lower()
        assert "configured" in str(exc_info.value).lower()

    def test_error_message_mentions_token_and_provider(self) -> None:
        """Error message guides user to provide token or auth_provider."""
        provider = NotConfiguredAuthProvider()

        with pytest.raises(AuthenticationError) as exc_info:
            provider.get_secret("any_key")

        message = str(exc_info.value)
        assert "token" in message.lower()
        assert "auth_provider" in message.lower()
