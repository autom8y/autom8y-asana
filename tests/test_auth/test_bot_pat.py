"""Tests for bot_pat.py secure PAT access.

Per TDD-S2S-001 Section 12.1:
- Environment variable access
- Error handling for missing/invalid PAT
- Cache behavior
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest

from autom8_asana.auth.bot_pat import BotPATError, clear_bot_pat_cache, get_bot_pat


@pytest.fixture(autouse=True)
def reset_cache() -> Generator[None, None, None]:
    """Reset the bot PAT cache before and after each test."""
    clear_bot_pat_cache()
    yield
    clear_bot_pat_cache()


class TestGetBotPat:
    """Test bot PAT retrieval from environment."""

    def test_get_bot_pat_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Successfully retrieves PAT from environment."""
        # Arrange
        test_pat = "0/1234567890abcdef1234567890abcdef"
        monkeypatch.setenv("ASANA_PAT", test_pat)
        clear_bot_pat_cache()

        # Act
        result = get_bot_pat()

        # Assert
        assert result == test_pat

    def test_get_bot_pat_missing_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises BotPATError when ASANA_PAT is not set."""
        # Arrange
        monkeypatch.delenv("ASANA_PAT", raising=False)
        clear_bot_pat_cache()

        # Act & Assert
        with pytest.raises(BotPATError) as exc_info:
            get_bot_pat()

        assert "ASANA_PAT environment variable is required" in str(exc_info.value)

    def test_get_bot_pat_empty_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises BotPATError when ASANA_PAT is empty."""
        # Arrange
        monkeypatch.setenv("ASANA_PAT", "")
        clear_bot_pat_cache()

        # Act & Assert
        with pytest.raises(BotPATError) as exc_info:
            get_bot_pat()

        assert "ASANA_PAT environment variable is required" in str(exc_info.value)

    def test_get_bot_pat_too_short_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Raises BotPATError when ASANA_PAT is too short."""
        # Arrange
        monkeypatch.setenv("ASANA_PAT", "short")
        clear_bot_pat_cache()

        # Act & Assert
        with pytest.raises(BotPATError) as exc_info:
            get_bot_pat()

        assert "too short" in str(exc_info.value)

    def test_get_bot_pat_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PAT is cached after first retrieval."""
        # Arrange
        test_pat = "0/1234567890abcdef1234567890abcdef"
        monkeypatch.setenv("ASANA_PAT", test_pat)
        clear_bot_pat_cache()

        # Act
        result1 = get_bot_pat()
        # Change env var - should NOT affect cached result
        monkeypatch.setenv("ASANA_PAT", "0/different_pat_value_here")
        result2 = get_bot_pat()

        # Assert
        assert result1 == test_pat
        assert result2 == test_pat  # Still the original cached value

    def test_clear_cache_allows_reload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clearing cache allows PAT to be reloaded."""
        # Arrange
        test_pat1 = "0/1234567890abcdef1234567890abcdef"
        test_pat2 = "1/different_pat_value_here1234567"
        monkeypatch.setenv("ASANA_PAT", test_pat1)
        clear_bot_pat_cache()

        # Act
        result1 = get_bot_pat()
        monkeypatch.setenv("ASANA_PAT", test_pat2)
        clear_bot_pat_cache()  # Clear cache to force reload
        result2 = get_bot_pat()

        # Assert
        assert result1 == test_pat1
        assert result2 == test_pat2


class TestBotPATError:
    """Test BotPATError exception."""

    def test_error_message_no_credential_leak(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Error messages never contain credential material."""
        # Arrange
        monkeypatch.delenv("ASANA_PAT", raising=False)
        clear_bot_pat_cache()

        # Act
        try:
            get_bot_pat()
        except BotPATError as e:
            error_message = str(e)

        # Assert - message contains helpful info but no secrets
        assert "ASANA_PAT" in error_message
        assert "0/" not in error_message
        assert "1/" not in error_message

    def test_error_is_exception_subclass(self) -> None:
        """BotPATError is a proper Exception subclass."""
        # Arrange & Act
        error = BotPATError("test message")

        # Assert
        assert isinstance(error, Exception)
        assert str(error) == "test message"


class TestGetBotPatExtensionResolution:
    """Test bot PAT retrieval via Lambda extension ARN resolution."""

    def test_resolves_via_arn_when_set(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Resolves PAT via Lambda extension when ASANA_PAT_ARN is set."""
        test_pat = "0/resolved_from_extension_1234567890"
        monkeypatch.setenv("ASANA_PAT_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:pat")
        monkeypatch.delenv("ASANA_PAT", raising=False)
        clear_bot_pat_cache()

        with patch(
            "autom8y_config.lambda_extension.resolve_secret_arn",
            return_value=test_pat,
        ):
            result = get_bot_pat()

        assert result == test_pat

    def test_falls_back_to_direct_env_when_no_arn(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Falls back to ASANA_PAT env var when no ARN is set."""
        test_pat = "0/direct_env_var_pat_1234567890abc"
        monkeypatch.delenv("ASANA_PAT_ARN", raising=False)
        monkeypatch.setenv("ASANA_PAT", test_pat)
        clear_bot_pat_cache()

        result = get_bot_pat()

        assert result == test_pat

    def test_raises_when_neither_arn_nor_env_set(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Raises BotPATError when no secret source is available."""
        monkeypatch.delenv("ASANA_PAT_ARN", raising=False)
        monkeypatch.delenv("ASANA_PAT", raising=False)
        clear_bot_pat_cache()

        with pytest.raises(BotPATError):
            get_bot_pat()
