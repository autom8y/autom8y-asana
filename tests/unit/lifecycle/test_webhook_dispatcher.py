"""Unit tests for LifecycleWebhookDispatcher with feature flags and dry-run.

Tests the 4-layer feature flag evaluation:
- Layer 1: Global enable/disable
- Layer 2: Dry-run mode
- Layer 3: Entity type allowlist
- Layer 4: Event type allowlist
Plus loop detection and live dispatch.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from autom8_asana.lifecycle.loop_detector import LoopDetector
from autom8_asana.lifecycle.webhook_dispatcher import (
    LifecycleWebhookDispatcher,
    WebhookDispatcherConfig,
)

# ---------------------------------------------------------------------------
# WebhookDispatcherConfig tests
# ---------------------------------------------------------------------------


class TestWebhookDispatcherConfig:
    """Test config construction and environment variable parsing."""

    def test_defaults_are_maximally_conservative(self) -> None:
        config = WebhookDispatcherConfig()
        assert config.enabled is False
        assert config.dry_run is True
        assert config.allowed_entity_types == frozenset()
        assert config.allowed_event_types == frozenset()

    def test_from_env_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With no env vars set, config is disabled + dry_run."""
        monkeypatch.delenv("WEBHOOK_DISPATCH_ENABLED", raising=False)
        monkeypatch.delenv("WEBHOOK_DISPATCH_DRY_RUN", raising=False)
        monkeypatch.delenv("WEBHOOK_DISPATCH_ENTITY_TYPES", raising=False)
        monkeypatch.delenv("WEBHOOK_DISPATCH_EVENT_TYPES", raising=False)

        config = WebhookDispatcherConfig.from_env()
        assert config.enabled is False
        assert config.dry_run is True

    def test_from_env_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEBHOOK_DISPATCH_ENABLED", "true")
        monkeypatch.setenv("WEBHOOK_DISPATCH_DRY_RUN", "false")
        monkeypatch.setenv("WEBHOOK_DISPATCH_ENTITY_TYPES", "Process,Offer")
        monkeypatch.setenv("WEBHOOK_DISPATCH_EVENT_TYPES", "section_changed,created")

        config = WebhookDispatcherConfig.from_env()
        assert config.enabled is True
        assert config.dry_run is False
        assert config.allowed_entity_types == frozenset({"Process", "Offer"})
        assert config.allowed_event_types == frozenset({"section_changed", "created"})

    def test_from_env_empty_allowlists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEBHOOK_DISPATCH_ENABLED", "true")
        monkeypatch.setenv("WEBHOOK_DISPATCH_ENTITY_TYPES", "")
        monkeypatch.setenv("WEBHOOK_DISPATCH_EVENT_TYPES", "")

        config = WebhookDispatcherConfig.from_env()
        assert config.allowed_entity_types == frozenset()
        assert config.allowed_event_types == frozenset()

    def test_from_env_case_insensitive_booleans(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("WEBHOOK_DISPATCH_ENABLED", "TRUE")
        monkeypatch.setenv("WEBHOOK_DISPATCH_DRY_RUN", "FALSE")

        config = WebhookDispatcherConfig.from_env()
        assert config.enabled is True
        assert config.dry_run is False


# ---------------------------------------------------------------------------
# LifecycleWebhookDispatcher tests
# ---------------------------------------------------------------------------


class TestLifecycleWebhookDispatcher:
    """Test dispatcher feature flag evaluation and dispatch routing."""

    def _make_dispatcher(
        self,
        *,
        enabled: bool = True,
        dry_run: bool = False,
        entity_types: frozenset[str] | None = None,
        event_types: frozenset[str] | None = None,
        dispatch_result: dict | None = None,
    ) -> tuple[LifecycleWebhookDispatcher, AsyncMock, LoopDetector]:
        config = WebhookDispatcherConfig(
            enabled=enabled,
            dry_run=dry_run,
            allowed_entity_types=(
                entity_types if entity_types is not None else frozenset({"Process"})
            ),
            allowed_event_types=(
                event_types
                if event_types is not None
                else frozenset({"section_changed"})
            ),
        )
        mock_dispatch = AsyncMock()
        mock_dispatch.dispatch_async = AsyncMock(
            return_value=dispatch_result or {"success": True}
        )
        loop_detector = LoopDetector(window_seconds=30)

        dispatcher = LifecycleWebhookDispatcher(
            automation_dispatch=mock_dispatch,
            config=config,
            loop_detector=loop_detector,
        )
        return dispatcher, mock_dispatch, loop_detector

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_disabled_short_circuits(self) -> None:
        """Layer 1: disabled config returns immediately."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher(enabled=False)
        result = self._run(
            dispatcher.handle_event("section_changed", "Process", "gid1", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "disabled"
        mock_dispatch.dispatch_async.assert_not_called()

    def test_entity_type_not_allowed(self) -> None:
        """Layer 2: entity type not in allowlist."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher(
            entity_types=frozenset({"Process"})
        )
        result = self._run(
            dispatcher.handle_event("section_changed", "Offer", "gid1", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "entity_type_not_allowed"

    def test_empty_entity_allowlist_blocks_all(self) -> None:
        """Layer 2: empty allowlist means nothing allowed."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher(entity_types=frozenset())
        result = self._run(
            dispatcher.handle_event("section_changed", "Process", "gid1", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "entity_type_not_allowed"

    def test_event_type_not_allowed(self) -> None:
        """Layer 3: event type not in allowlist."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher(
            event_types=frozenset({"section_changed"})
        )
        result = self._run(dispatcher.handle_event("created", "Process", "gid1", {}))
        assert result["dispatched"] is False
        assert result["reason"] == "event_type_not_allowed"

    def test_empty_event_allowlist_blocks_all(self) -> None:
        """Layer 3: empty event allowlist blocks all events."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher(event_types=frozenset())
        result = self._run(
            dispatcher.handle_event("section_changed", "Process", "gid1", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "event_type_not_allowed"

    def test_loop_detection(self) -> None:
        """Layer 4: self-triggered event is detected and skipped."""
        dispatcher, mock_dispatch, loop_detector = self._make_dispatcher()
        loop_detector.record_outbound("gid1")

        result = self._run(
            dispatcher.handle_event("section_changed", "Process", "gid1", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "loop_detected"

    def test_dry_run_logs_but_does_not_dispatch(self) -> None:
        """Layer 5: dry_run mode logs but doesn't dispatch."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher(dry_run=True)

        result = self._run(
            dispatcher.handle_event("section_changed", "Process", "gid1", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "dry_run"
        mock_dispatch.dispatch_async.assert_not_called()

    def test_live_dispatch_success(self) -> None:
        """Full pass-through: all flags allow, dispatch succeeds."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher(
            dispatch_result={"success": True}
        )

        result = self._run(
            dispatcher.handle_event(
                "section_changed",
                "Process",
                "gid1",
                {"section_name": "CONVERTED"},
            )
        )
        assert result["dispatched"] is True
        assert result["reason"] == "live"
        assert result["result"]["success"] is True
        mock_dispatch.dispatch_async.assert_called_once()

    def test_live_dispatch_builds_trigger_with_section(self) -> None:
        """Verify trigger dict includes section_name from payload."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher()

        self._run(
            dispatcher.handle_event(
                "section_changed",
                "Process",
                "gid42",
                {"section_name": "CONVERTED"},
            )
        )

        call_args = mock_dispatch.dispatch_async.call_args[0][0]
        assert call_args["task_gid"] == "gid42"
        assert call_args["type"] == "section_changed"
        assert call_args["section_name"] == "CONVERTED"

    def test_dispatch_exception_is_caught(self) -> None:
        """Dispatch errors are caught and returned as dispatch_error."""
        dispatcher, mock_dispatch, _ = self._make_dispatcher()
        mock_dispatch.dispatch_async.side_effect = RuntimeError("boom")

        result = self._run(
            dispatcher.handle_event("section_changed", "Process", "gid1", {})
        )
        assert result["dispatched"] is False
        assert result["reason"] == "dispatch_error"


# ---------------------------------------------------------------------------
# LoopDetector tests
# ---------------------------------------------------------------------------


class TestLoopDetector:
    """Test LoopDetector time-windowed tracking."""

    def test_untracked_gid_not_self_triggered(self) -> None:
        detector = LoopDetector(window_seconds=30)
        assert detector.is_self_triggered("gid1") is False

    def test_recently_written_gid_is_self_triggered(self) -> None:
        detector = LoopDetector(window_seconds=30)
        detector.record_outbound("gid1")
        assert detector.is_self_triggered("gid1") is True

    def test_expired_gid_is_not_self_triggered(self) -> None:
        """After window expires, GID should not be detected."""
        detector = LoopDetector(window_seconds=0)  # 0-second window
        detector.record_outbound("gid1")
        # Force prune by checking -- 0-second window means immediate expiry
        import time

        time.sleep(0.01)
        assert detector.is_self_triggered("gid1") is False

    def test_tracked_count(self) -> None:
        detector = LoopDetector(window_seconds=30)
        detector.record_outbound("gid1")
        detector.record_outbound("gid2")
        assert detector.tracked_count == 2

    def test_different_gids_independent(self) -> None:
        detector = LoopDetector(window_seconds=30)
        detector.record_outbound("gid1")
        assert detector.is_self_triggered("gid2") is False
        assert detector.is_self_triggered("gid1") is True
