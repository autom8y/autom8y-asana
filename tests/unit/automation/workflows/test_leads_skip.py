"""Unit tests for the WS-SKIP taxonomy (emit_skip: log + metric, PII-masked)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from autom8_asana.automation.workflows.leads_skip import (
    SKIP_METRIC_NAME,
    SkipClass,
    emit_skip,
)


def _collect_metrics() -> tuple[Any, list[tuple[str, float, dict[str, str]]]]:
    sink: list[tuple[str, float, dict[str, str]]] = []

    def hook(name: str, value: float, labels: dict[str, str]) -> None:
        sink.append((name, value, labels))

    return hook, sink


def test_emit_skip_logs_and_counts_metric() -> None:
    log = MagicMock()
    hook, sink = _collect_metrics()
    emit_skip(
        log,
        hook,
        klass=SkipClass.RESOLUTION_MISS,
        office_phone="+17705551234",
        sub_reason="server_404",
    )
    log.warning.assert_called_once()
    name, value, labels = sink[0]
    assert name == SKIP_METRIC_NAME
    assert value == 1.0
    assert labels == {"class": "resolution_miss", "sub_reason": "server_404"}


def test_emit_skip_masks_phone_in_log() -> None:
    log = MagicMock()
    hook, _ = _collect_metrics()
    emit_skip(
        log,
        hook,
        klass=SkipClass.MINT_UNAVAILABLE,
        office_phone="+17705551234",
        sub_reason="rate_limited",
    )
    _event, kwargs = log.warning.call_args
    masked = kwargs["office_phone"]
    # Raw E.164 middle digits must NOT appear.
    assert masked != "+17705551234"
    assert "***" in masked
    assert "5551" not in masked


def test_emit_skip_without_metrics_hook_does_not_raise() -> None:
    log = MagicMock()
    emit_skip(
        log,
        None,
        klass=SkipClass.INACTIVE_OR_EMPTY,
        office_phone="+17705551234",
        sub_reason="empty_leads",
    )
    log.warning.assert_called_once()


def test_skip_class_is_closed_four_class() -> None:
    assert {c.value for c in SkipClass} == {
        "resolution_miss",
        "collision_conflict",
        "inactive_or_empty",
        "mint_unavailable",
    }
