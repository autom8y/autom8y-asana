"""Unit tests for discovery.discover_entity_projects_async ARN-aware secret resolution.

Verifies that discovery.py mirrors cache_warmer.py:372's resolve_secret_from_env
pattern, recognizing ASANA_WORKSPACE_GID_ARN (SecretsManager ARN form) in
addition to direct ASANA_WORKSPACE_GID env var.

Surfaced by cache-warmer cascade closeout 2026-04-28: discovery.py:107 was
reading workspace_gid via the pydantic-only get_workspace_gid() path which
silently no-op'd in production for ~30 days when only the _ARN form was set.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from autom8_asana.services.discovery import discover_entity_projects_async


@pytest.mark.asyncio
async def test_discovery_uses_arn_resolution_when_arn_env_set(monkeypatch):
    """Given ASANA_WORKSPACE_GID_ARN set + bot PAT available + extension resolves,
    discovery resolves workspace_gid via Lambda extension (not pydantic settings)."""
    # Strip both env vars to control resolution path
    monkeypatch.delenv("ASANA_WORKSPACE_GID", raising=False)
    monkeypatch.setenv(
        "ASANA_WORKSPACE_GID_ARN",
        "arn:aws:secretsmanager:us-east-1:123:secret:autom8y/asana/workspace_gid-AbCdEf",
    )

    # Mock bot PAT so we get past the first early-return
    with patch(
        "autom8_asana.auth.bot_pat.get_bot_pat",
        return_value="test-bot-pat-token-1234567890",
    ), patch(
        # Mock the extension call — this is the ARN-aware path being verified
        "autom8_asana.services.discovery.resolve_secret_from_env",
        return_value="12345",
    ) as mock_resolve, patch(
        # Stub AsanaClient to short-circuit the actual HTTP work; we only
        # need to verify the workspace_gid was resolved via the ARN path
        "autom8_asana.AsanaClient"
    ) as mock_client_cls:
        # Make the async context manager a no-op that raises after entry
        # so we exit before any real Asana work; the assertion is on
        # resolve_secret_from_env being called with the right key
        mock_client_cls.side_effect = RuntimeError("short-circuit-test")

        with pytest.raises(RuntimeError, match="short-circuit-test"):
            await discover_entity_projects_async()

    mock_resolve.assert_called_once_with("ASANA_WORKSPACE_GID")


@pytest.mark.asyncio
async def test_discovery_warns_and_returns_when_no_workspace_gid(monkeypatch, capsys):
    """Given neither ASANA_WORKSPACE_GID nor _ARN set, discovery emits the
    entity_resolver_no_workspace warning and early-returns (preserving
    existing no-workspace behavior)."""
    monkeypatch.delenv("ASANA_WORKSPACE_GID", raising=False)
    monkeypatch.delenv("ASANA_WORKSPACE_GID_ARN", raising=False)

    with patch(
        "autom8_asana.auth.bot_pat.get_bot_pat",
        return_value="test-bot-pat-token-1234567890",
    ):
        # Real resolve_secret_from_env will raise ValueError — the
        # try/except in discovery.py should catch it and treat as None
        result = await discover_entity_projects_async()

    # Returns the singleton registry (empty / unwarmed)
    assert result is not None
    # autom8y_log (structlog) routes through stdout; capsys captures the
    # structured warning emission
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert (
        "entity_resolver_no_workspace" in combined
    ), f"Expected entity_resolver_no_workspace warning in stdout/stderr, got: {combined!r}"
