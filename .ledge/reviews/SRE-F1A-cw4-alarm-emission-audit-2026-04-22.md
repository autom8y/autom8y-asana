---
type: review
status: proposed
---

# SRE-F1A — CW-4 `auth.oauth.scope.cardinality` Alarm / Emission Audit

- **Rite**: SRE / observability-engineer
- **Date**: 2026-04-22
- **Scope**: PR #131 G9 residual — CW-4 alarm-side closure decision
- **Incoming handoff**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-10x-dev-to-sre-pr131-merged-2026-04-22.md` §4 F1
- **Companion runbook gap (CW-9)**: `auth-oauth-scope-cardinality.md` — NOT present on disk, deferred in handoff
- **Evidence grade**: STRONG (reproducible from git; all claims cite file:line)

## 1. Emission Trace

**Result: BLOCKING — the metric is NOT emitted. No callsite exists for any variant of the scope-cardinality signal.**

Two candidate emission surfaces are declared but inert:

1. **`METRIC_OAUTH_SCOPE_CARDINALITY = "auth.oauth.scope.cardinality"`** — declared at `autom8y/services/auth/autom8y_auth_server/services/token_exchange_cw_metrics.py:162`; documented in the `emit_oauth_event` docstring at `token_exchange_cw_metrics.py:544` as a "gauge, distinct observed scopes". **Zero callsites** emit with this metric-name constant. Grep across `autom8y_auth_server/` confirms only the declaration and the docstring reference — no call of `emit_oauth_event(metric_name=METRIC_OAUTH_SCOPE_CARDINALITY, ...)` or equivalent string literal `"auth.oauth.scope.cardinality"` anywhere in production code [STRONG].

2. **`ScopeCardinalityObserved`** — the (A)-variant gauge metric that the commented CW-4 alarm block binds to at `terraform/services/auth/observability/cloudwatch-alarms.tf:410`. **The constant does not exist** in `token_exchange_cw_metrics.py` at all. There is no MetricData dict anywhere in the module that sets `MetricName=ScopeCardinalityObserved`. The alarm would bind to a metric name that the emitter never produces [STRONG].

**Upstream surfaces that could drive emission but don't:**

- `emit_issuance_with_scope` (`token_exchange_cw_metrics.py:485-524`) — the only function that exercises `_cardinality_capped_scope`. It emits the `TokenExchangeIssuanceWithScope` counter, not the scope-cardinality gauge, and itself has **zero callsites** in production code (grep confirms no non-test references). So even the cap's *side-effect log event* (`token_exchange_cw_metrics_scope_cardinality_overflow` at `token_exchange_cw_metrics.py:138`) — which is what shape (B) log-metric-filter would key off — is never triggered in production because the upstream `emit_issuance_with_scope` is never invoked.

- `emit_token_exchange_outcome` (`token_exchange_cw_metrics.py:382`) — also has zero production callsites. This is a PR #131 residual broader than CW-4.

**Material consequence for CW-4 alarm:** if the alarm were uncommented today, it would bind to metric-name `ScopeCardinalityObserved` in namespace `Autom8y/Auth/TokenExchange`. CloudWatch would return `Insufficient data` forever. With `treat_missing_data = "notBreaching"` (line 423), the alarm would remain in OK state permanently — i.e., silent. The alarm would never fire; early-warning for scope-catalog drift would not exist despite appearing to [STRONG].

This is a textbook alarm-would-never-fire risk (symptom-based alerting principle violated: nothing is being alerted on because the underlying signal is not emitted [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72 @ 2026-04-01]).

## 2. Overflow Guard Audit

The in-process overflow guard itself is sound, but it is a defense for a metric path that is currently dead code.

- **Thread-safety**: `_scope_cardinality_lock = Lock()` at `token_exchange_cw_metrics.py:116`; all reads and writes of `_observed_scopes` are wrapped (`:131-135`). Correct for CPython. The lock is taken for a bounded O(1) hash-set membership check; no reentry risk [STRONG].
- **Boundedness**: `SCOPE_CARDINALITY_CAP = 50` at `:113`, enforced at `:134`. Once the set reaches 50, every novel scope is coerced to `SCOPE_OVERFLOW_VALUE = "OTHER"` (`:114, :142`). Set is intentionally non-resetting for the process lifetime (`:126-127` docstring) — repeatable dimension shapes are the design goal [STRONG].
- **Test reset**: `_reset_scope_cardinality_for_tests` (`:145-148`) clears the set under the same lock; production explicitly warned against calling it (`:146`). Tests exercise it at `services/auth/tests/test_oauth_server_track.py:479, 491, 503` within a three-case coverage (first-50-pass-through / 51st-overflows / previously-observed-still-passes) in `TestScopeCardinalityCap` [STRONG].
- **Overflow log line**: `:137-141` structured `log.warning("token_exchange_cw_metrics_scope_cardinality_overflow", scope=..., cap=50)` — this is the exact log event shape (B) of the CW-4 wiring decision would key a `aws_cloudwatch_log_metric_filter` off [STRONG].

**Caveat (audit-surface-only, not a blocker for the guard itself):** `_observed_scopes` is a *per-process* set, not per-task/per-container. In an ECS deployment with N tasks, the fleet will observe up to `N × 50` distinct scope strings globally before every process is coercing to `"OTHER"`. This is working-as-designed per `:126-127`, but it means the CW-4 alarm at "Max > 50" (commented threshold line 418) is a *per-process* signal that CloudWatch will show aggregated across tasks via the `Environment` dimension — a small presentation nuance, not a correctness bug.

## 3. Threshold Recommendation

**Recommendation: TBD with 7d-baseline-calibration comment, matching CW-2a/CW-2b pattern.** Do NOT ship `threshold = 50` today.

Rationale:

- The `> 50` floor in the header comment at `cloudwatch-alarms.tf:363` is **derived from the code-side cap constant** `SCOPE_CARDINALITY_CAP = 50`, not from an observed-production baseline. This is a platform-heuristic threshold, and it's the same anti-pattern that CW-2a/CW-2b already caught and deferred (`:249-258, :285-287`): "PKCE attempts is an observability metric without an a-priori threshold... DECISION DEFERRED TO 10x-dev" [PLATFORM-HEURISTIC: 50-distinct-scopes as a per-process PAGE threshold has no empirical backing in the current codebase].
- The 50-value cap is a **cost-protection ceiling** (cardinality explosion guard), not a production-reasonable operating point. The registered-scopes catalog in the SA YAML is currently on the order of 10–20 values (per the "tens of values" claim at `token_exchange_cw_metrics.py:110`). A healthy steady-state will sit well below 50; a PAGE-at-50 threshold equates PAGE with "the cap just saturated." That's too late — every scope past 50 is already being silently coerced to `"OTHER"` (per-process observability is already lost by the time the alarm fires).
- The right operating threshold is something like "Max distinct scopes > (observed_p95 + safety margin)" — provably below 50 for a healthy fleet, provably catches drift before the cap saturates. That number only exists after 7d of emission.
- Aligning CW-4 with CW-2a/CW-2b (TBD + runbook requires-baseline-calibration note) preserves alarm→runbook identity and matches the existing SRE-CONCURRENCE §3.2 precedent, which is the post-remediation authoritative pattern [SR:SRC-002 Beyer et al. 2018] [STRONG | 0.72 @ 2026-04-01].

The `> 50` floor may survive into the threshold as the *maximum* the alarm can ever reach (because the cap makes larger values impossible), but it should NOT be the *primary* threshold.

## 4. Safe-to-Uncomment Assessment

**NOT safe to uncomment today.** Three independent blockers, any one of which is sufficient to hold:

| # | Blocker | Evidence | Severity |
|---|---------|----------|----------|
| B1 | Metric not emitted (neither `auth.oauth.scope.cardinality` nor `ScopeCardinalityObserved`) | §1 above; zero callsites | BLOCKING |
| B2 | Runbook `auth-oauth-scope-cardinality.md` absent on disk | `cloudwatch-alarms.tf:59-60, :396-399`; ls confirms absence | BLOCKING (anti-pattern "Creating alerts without runbooks") |
| B3 | Threshold 50 is not baseline-calibrated | §3 above | DEGRADE (fires too late; silent pre-fire cardinality loss) |

Destroy-safety of the alarm block itself is fine — the block at `:405-433` has `alarm_actions`/`ok_actions` pointing at the existing shared SNS topic, no dependent resources, and `treat_missing_data = "notBreaching"`. In isolation the Terraform hunk is destroy-safe matching CW-2a/CW-2b explicitly (`:378-380` commentary: "Destroy-safe. Code-side overflow behavior continues regardless of alarm presence"). That class-wide safety property is inherited and preserved [STRONG].

But **destroy-safety is the wrong gate here.** The alarm is apply-UNSAFE in the weaker sense that applying it produces a permanently-silent alarm that violates observability invariants without visible failure (it wouldn't crash the plan; it would just never fire). That's worse than leaving it commented, because it creates a false-confidence dashboard artifact.

## 5. Uncomment Diff (or leave-commented rationale)

**Leave-commented. Do NOT emit a Terraform diff.**

The minimum-viable CW-4 closure is to leave the current stub as-is and pin the three unblock conditions in a `# TODO(CW-4, PENDING)` note at the top of the commented block, so a future reader sees them without re-deriving. Specifically:

**Unblock condition (all three required before uncomment):**

1. **U1 — Emission wired.** 10x-dev chooses between shape (A) (emit `ScopeCardinalityObserved` gauge per successful scope observation, from `_cardinality_capped_scope` or a post-cap probe) and shape (B) (`aws_cloudwatch_log_metric_filter` on the existing `token_exchange_cw_metrics_scope_cardinality_overflow` log event at `token_exchange_cw_metrics.py:137-141`). Either produces a non-empty CloudWatch series. SRE-F1A recommends shape (B) as the minimum-viable unblock (zero application-code change; `aws_cloudwatch_log_metric_filter` + paired alarm resource in the same terraform file; unblocks B2/B3 faster because it keys off an overflow event that is binary rather than requiring baseline calibration).
   - If shape (B) is chosen, the CW-4 alarm's metric_name changes from `ScopeCardinalityObserved` (line 410 of commented block) to whatever the log-metric-filter synthesizes (e.g., `ScopeCardinalityOverflowCount`), and the threshold becomes `Sum > 0 / 5-min / 1 period` (the overflow event is binary — any occurrence is a drift signal). This sidesteps §3 threshold calibration entirely.
   - If shape (A) is chosen, both §1 wiring and §3 baseline calibration must be completed before uncomment.
2. **U2 — Runbook present.** `autom8y/services/auth/runbooks/auth-oauth-scope-cardinality.md` exists and follows the CW-5..CW-8 fleet convention (pending observability-engineer authorship per `cloudwatch-alarms.tf:398`).
3. **U3 — Threshold calibrated OR shape (B) elected.** Either 7d baseline → threshold at `observed_p95 + margin` for shape (A), OR `Sum > 0` for shape (B).

When all three clear, the uncomment is a plain single-hunk `#` removal of lines `:405-433` plus `:449-451` output-absence note update. No other edits needed to the enclosing file (namespace, SNS topic, tags-block, variable surface are all already declared and reused by CW-1 / CW-3 today).

**Why leave-commented beats an aspirational uncomment:**

- An uncommented CW-4 today binds to a metric that doesn't exist → permanently-silent alarm → false confidence in observability coverage → defeats the entire purpose of the observability-engineer gate [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72 @ 2026-04-01].
- The anti-pattern "Unactionable alerts" ("If you cannot do anything about it, do not page someone") applies in reverse: if the alert *cannot fire at all*, it is worse than nothing — it displaces the felt need for real coverage.
- The CW-2a/CW-2b precedent in the same file is explicit that COMMENTED-STUB-WITH-RATIONALE is the correct posture for metrics awaiting baseline-or-decision inputs (`:260-262`, `:286-293`).

## Verdict

**CONCUR-LEAVE-COMMENTED-WITH-UNBLOCK-CONDITION.**

Three unblock conditions U1 (emission wired; recommend shape (B) log-metric-filter as minimum-viable), U2 (runbook authored), U3 (threshold calibrated OR shape (B) elected). All three must clear before CW-4 is uncommented. The existing commented block is structurally correct and matches CW-2a/CW-2b destroy-safety; it does not need a Terraform diff today. The residual action is a one-line `# TODO(CW-4, PENDING)` note inside the commented block enumerating U1/U2/U3, which the main thread can apply verbatim if it elects to harden the stub further — but even without that note, the current state is safe to close F1a against.

Blocking finding to surface to the main thread: **the scope-cardinality metric has no emission path in production code** — a larger PR #131 residual than CW-4 alone (it's shared with `emit_issuance_with_scope` and `emit_token_exchange_outcome`, which are both declared-but-never-called). That is a separate track for 10x-dev (emission wiring), not an observability-engineer deliverable, and should be surfaced in the F1 close note as "observability-engineer declines to uncomment; unblock is 10x-dev emission work."
