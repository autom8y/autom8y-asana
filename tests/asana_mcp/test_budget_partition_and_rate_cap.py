"""Contract §2 budget partition + rate cap — two-sided; checklist items 2 & 11.

Partition invariants: ΣSHARE ≤ 1.0 and RATE_RPS×60 ≤ SHARE_MCP×1500. Rate cap:
burst executions GREEN, burst+1 ⇒ exactly one typed MCP_RATE_BUDGET_EXHAUSTED
refusal with retry_after; NEVER queues.
"""

from __future__ import annotations

import time

import pytest

import asana_mcp.observability as m
from asana_mcp.observability import (
    CODE_RATE_BUDGET,
    BudgetPartition,
    BudgetPartitionError,
    RateCap,
    RateCapExceeded,
    validate_partition,
)


# --- GREEN: the contract default partition validates (shares sum to 1.0; 120<=120) ---
def test_default_partition_validates() -> None:
    p = BudgetPartition()  # 0.60 / 0.32 / 0.08 ; rps 2 ; total 1500
    validate_partition(p)  # no raise
    assert abs(p.sum_shares() - 1.0) < 1e-9
    assert p.rate_rps * 60.0 <= p.share_mcp * p.total_rpm + 1e-9


# --- RED (teeth): oversubscribed shares rejected ---
def test_share_oversubscription_rejected() -> None:
    p = BudgetPartition(share_warmers=0.9, share_api=0.9, share_mcp=0.9)
    with pytest.raises(BudgetPartitionError):
        validate_partition(p)


# --- RED (teeth): RPS cap inconsistent with the MCP share rejected ---
def test_rps_exceeds_mcp_share_rejected() -> None:
    p = BudgetPartition(rate_rps=10.0)  # 600/min > 0.08*1500 = 120/min
    with pytest.raises(BudgetPartitionError):
        validate_partition(p)


# --- RED: negative / zero-total rejected ---
def test_zero_total_rejected() -> None:
    with pytest.raises(BudgetPartitionError):
        validate_partition(BudgetPartition(total_rpm=0.0))


# --- R3: burst executions GREEN; burst+1 ⇒ exactly one typed refusal (frozen clock) ---
def test_rate_cap_burst_plus_one_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    now = {"t": 1000.0}
    monkeypatch.setattr(m.time, "monotonic", lambda: now["t"])
    cap = RateCap(rate=2.0, window_s=1.0, burst=10.0)
    results = [cap.try_acquire() for _ in range(11)]  # burst+1
    oks = [ok for ok, _ in results]
    assert sum(oks) == 10  # GREEN: exactly burst succeed
    assert results[-1][0] is False and results[-1][1] > 0  # RED: the excess refused w/ retry_after


# --- R3: over-budget REFUSES immediately (non-blocking, never queues) ---
def test_rate_cap_is_non_blocking() -> None:
    cap = RateCap(rate=1.0, window_s=1.0, burst=1.0)
    t0 = time.monotonic()
    cap.try_acquire()
    ok, retry_after = cap.try_acquire()
    elapsed = time.monotonic() - t0
    assert not ok and retry_after > 0
    assert elapsed < 0.1  # refused immediately, did NOT sleep/queue


# --- the typed refusal carries the contract's code + retry_after ---
def test_rate_cap_exceeded_typed_code() -> None:
    exc = RateCapExceeded(retry_after_s=1.5)
    assert exc.code == CODE_RATE_BUDGET == "MCP_RATE_BUDGET_EXHAUSTED"
    assert exc.retry_after_s == 1.5
