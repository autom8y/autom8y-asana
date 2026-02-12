---
artifact_id: stakeholder-decisions-GAP-04-aimd
title: "Stakeholder Decisions: AIMD Adaptive Rate Limiting"
created_at: "2026-02-07T17:00:00Z"
author: requirements-analyst
status: confirmed
related_docs:
  - docs/requirements/PRD-GAP-04-aimd-rate-limiting.md
  - docs/GAPS/Q1/GAP-04-aimd-rate-limiting.md
---

# Stakeholder Decisions — PRD-GAP-04: AIMD Adaptive Rate Limiting

## Architecture Decisions

| ID | Decision | Detail |
|----|----------|--------|
| **OQ-1** | **Separate AIMD controllers + shared rate gate** | Independent read/write `AsyncAdaptiveSemaphore` instances (ceiling 50/15 respectively). Shared rate coordination via existing token bucket layer above both. No cross-pool contamination on 429. |
| **OQ-2** | **Replace semaphores in-place** | Swap `_read_semaphore` / `_write_semaphore` inside `AsanaHttpClient` with `AsyncAdaptiveSemaphore`. 429 signal handled directly in `_request()`. No external wrapper. |
| **OQ-3** | **Stub cooldown interface** | Config fields (`cooldown_trigger`, `cooldown_duration_seconds`) + consecutive reject counter + warning log. No actual pause/drain in v1. Activation is a one-line change when production data warrants it. |
| **OQ-4** | **Monotonic epoch coalescing** | Slots stamped with epoch at acquire time. `on_reject()` and `on_success()` ignore stale epochs (epoch < current). One halving per cohort, no tuning parameters. |
| **OQ-5** | **AsyncAdaptiveSemaphore on asyncio.Condition** | Custom class with `acquire() -> Slot` context manager. Internal `asyncio.Condition` + counter. `Slot` carries epoch, reports status on exit. `notify(1)` not `notify_all()`. Window stored as float, compared as int. |

## Scope Decisions

| Item | Decision |
|------|----------|
| **FR-007** (Increase Interval Throttle) | SHOULD-HAVE — include if natural, don't block release |
| **FR-008** (Cooldown Mode) | Stubbed interface only (config + counter + log) |
| **FR-009** (Token Bucket Drain) | Fully deferred — no stub needed |
| **Cross-pool 429 effects** | Completely independent. Asana's 429 is opaque (no type header). |
| **Rate gate layer** | Defer to architect: evaluate whether existing `TokenBucketRateLimiter` suffices or needs augmentation |
| **Non-goals** | Confirmed as-is, with addition: architect should evaluate whether `AsyncAdaptiveSemaphore` belongs in `autom8y` |
| **Platform primitives** | Architect's TDD includes platform-vs-local as a design decision. If platform, split into two initiatives (platform first, then integration). |

## Quality & Execution

| Dimension | Decision |
|-----------|----------|
| **Testing depth** | Thorough unit tests (epoch, halving, floor/ceiling, grace period, stats) + deterministic simulation (SC-003) + integration with mocked HTTP |
| **SC-003 verification** | Deterministic simulation: scripted N requests with M 429s at specific points, compare adaptive vs fixed. CI-safe, reproducible. |
| **Workflow** | Full 10x-dev: TDD → implement → QA |
| **Git strategy** | Direct to main with atomic commits at meaningful boundaries |

## Key Constraints for Architect

1. `AsyncAdaptiveSemaphore` must be testable in isolation with injectable clock (grace period, increase interval)
2. Slot context manager must always release on exit (even on exception)
3. `on_success` must also check epoch staleness (prevent undoing decrease from old cohort)
4. Window as float, admission check as int — allows fractional alpha accumulation
5. `notify(1)` on release/window growth — no thundering herd
6. Asana's 429 response is opaque — no type differentiation possible. Do not attempt to distinguish concurrency vs rate 429s.
