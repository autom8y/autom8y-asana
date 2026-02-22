# Test Summary: SectionTimeline Endpoint -- Production Validation

## Overview
- **Test Period**: 2026-02-19 22:13 - 23:10 UTC-5 (~57 minutes)
- **Tester**: QA Adversary
- **Build/Version**: Commit `dda1c2f` (includes `b025d64`, `aa00da7`)
- **Environment**: Production (`asana.api.autom8y.io`)
- **Endpoint**: `GET /api/v1/offers/section-timelines`

---

## Results Summary

| Category | Pass | Fail | Blocked | Not Run |
|----------|------|------|---------|---------|
| Acceptance Criteria | 2 | 3 | 3 | 0 |
| Edge Cases | 3 | 1 | 1 | 0 |
| Security / Auth | 2 | 0 | 0 | 0 |
| Performance / NFR | 0 | 2 | 0 | 0 |
| Health Check | 1 | 0 | 0 | 0 |

---

## Test Cases

### TC-01: Health Check (Phase 4)

**Requirement**: Service availability
**Priority**: High
**Type**: Functional

**Steps**: `curl -s https://asana.api.autom8y.io/health`

**Expected Result**: 200 OK with `{"status": "OK"}`
**Actual Result**: 200 OK -- `{"status":"OK","timestamp":1771536873.99}` -- **PASS**

---

### TC-02: 503 TIMELINE_NOT_READY During Warm-Up (AC-6.7, AC-7.4, SC-3)

**Requirement**: PRD AC-6.7, AC-7.4
**Priority**: High
**Type**: Functional

**Steps**: Hit endpoint immediately after deployment during warm-up.

**Expected Result**: 503 with `TIMELINE_NOT_READY`, `retry_after_seconds: 30`, `Retry-After` header.
**Actual Result**: 503 -- `{"detail":{"error":"TIMELINE_NOT_READY","message":"Section timeline story caches are still warming up","request_id":"bffa6de3324d4a67","retry_after_seconds":30}}` -- **PASS**

**Notes**: Response shape correct. However, the `Retry-After` HTTP header was not verified in response headers (curl `-D` output was empty due to timeout on follow-up attempts). The `retry_after_seconds` field in the JSON body is present and correct.

---

### TC-03: Warm-Up Completes and Endpoint Returns 200 (SC-4, NFR-1)

**Requirement**: PRD SC-4, NFR-1 (< 5s p95 latency)
**Priority**: Critical
**Type**: Functional / Performance

**Steps**: Poll every 30s for up to 20 minutes.

**Expected Result**: 200 OK with valid `SuccessResponse[SectionTimelinesResponse]` within 15 minutes.
**Actual Result**: **FAIL -- CRITICAL**

Observed pattern across 3 ECS task cycles:

**Cycle 1** (22:13 - 22:25):
- 503 NOT_READY for 22 polls (~11 min)
- 504 Gateway Timeout at poll 23 (elapsed 671s)
- Service crashed, went to 502 Bad Gateway

**Cycle 2** (22:36 - 23:01):
- 503 NOT_READY for 20 polls (~10 min)
- 504 Gateway Timeout for 4 polls (warm-up completed, but request computation exceeds 60s ALB timeout)
- 502 UPSTREAM_ERROR for 3 polls (application-level Asana API failure)
- Service crashed, went to 502/503 infrastructure errors

**Cycle 3** (23:02 - 23:10+):
- 503 NOT_READY for 15+ polls and counting
- Still warming after 8+ minutes of observation

The endpoint NEVER returned 200 in 57 minutes of testing across 3 service restarts.

**Root Cause Analysis**: The `get_section_timelines()` function performs a full enumeration of ~3,773 tasks (`tasks.list_async().collect()`) plus per-offer story fetches (`list_for_task_cached_async()`) on every request. Even with `_REQUEST_CONCURRENCY = 10` semaphore, the total wall time exceeds the ALB's 60-second idle timeout. Diagnostic curl showed:
- `connect_time: 0.1s` (connection succeeds)
- `time_to_first_byte: 60.4s` (exactly the ALB timeout)
- `http_code: 504` (ALB kills the connection)

---

### TC-04: Response Shape Validation (AC-5.2, FR-6)

**Requirement**: PRD AC-5.2 -- `offer_gid`, `office_phone`, `active_section_days`, `billable_section_days`
**Priority**: High
**Type**: Functional

**Steps**: Validate the JSON structure of a 200 response.
**Actual Result**: **BLOCKED** -- Endpoint never returned 200.

---

### TC-05: Invariant: billable_section_days >= active_section_days (AC-4.1, AC-4.2)

**Requirement**: PRD AC-4.1, AC-4.2 (billable includes ACTIVE + ACTIVATING; active is ACTIVE only)
**Priority**: High
**Type**: Functional

**Steps**: For every entry in the response, verify `billable_section_days >= active_section_days`.
**Actual Result**: **BLOCKED** -- Endpoint never returned 200.

---

### TC-06: POC Offer GID 1205925604226368 Has active_section_days > 0 (SC-1)

**Requirement**: PRD SC-1
**Priority**: Medium
**Type**: Functional

**Steps**: Search response for `offer_gid == "1205925604226368"` and verify `active_section_days > 0`.
**Actual Result**: **BLOCKED** -- Endpoint never returned 200.

---

### TC-07: Missing Query Parameters Returns 422 (AC-6.4)

**Requirement**: PRD AC-6.4
**Priority**: Medium
**Type**: Edge Case

**Steps**: `curl -H "Authorization: Bearer $PAT" "https://asana.api.autom8y.io/api/v1/offers/section-timelines"`

**Expected Result**: 422 with validation error for missing params.
**Actual Result**: 422 -- `{"detail":[{"type":"missing","loc":["query","period_start"],"msg":"Field required"},{"type":"missing","loc":["query","period_end"],"msg":"Field required"}]}` -- **PASS**

---

### TC-08: Invalid Date Format Returns 422 (AC-6.4)

**Requirement**: PRD AC-6.4
**Priority**: Medium
**Type**: Edge Case

**Steps**: `curl -H "Authorization: Bearer $PAT" ".../section-timelines?period_start=not-a-date&period_end=2026-01-31"`

**Expected Result**: 422 with date parsing error.
**Actual Result**: 422 -- `{"detail":[{"type":"date_from_datetime_parsing","loc":["query","period_start"],"msg":"Input should be a valid date or datetime, invalid character in year"}]}` -- **PASS**

---

### TC-09: Reversed Date Range Returns 422 (AC-6.5, EC-8)

**Requirement**: PRD AC-6.5
**Priority**: Medium
**Type**: Edge Case

**Steps**: `curl -H "Authorization: Bearer $PAT" ".../section-timelines?period_start=2026-02-01&period_end=2026-01-01"`

**Expected Result**: 422 with `VALIDATION_ERROR` and message about constraint.
**Actual Result**: **FAIL (infrastructure)** -- 502 Bad Gateway (HTML, not application response). The service had crashed during the cycle when this test ran. This is an infrastructure timing issue, not a code defect. The validation code in the route handler (`if period_start > period_end: raise_api_error(...)`) is correctly implemented per code review of `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py:125-131`.

**Verdict**: Code is correct; test could not be validated in production due to service instability. **INCONCLUSIVE (code review PASS, runtime BLOCKED)**.

---

### TC-10: Single Day Period (EC-7)

**Requirement**: PRD EC-7 -- `period_start == period_end`
**Priority**: Medium
**Type**: Edge Case

**Steps**: `curl -H "Authorization: Bearer $PAT" ".../section-timelines?period_start=2026-01-15&period_end=2026-01-15"`

**Expected Result**: 200 with valid response (0 or 1 for each count).
**Actual Result**: 504 Gateway Timeout (same root cause as TC-03). **FAIL** -- computation exceeds ALB timeout.

---

### TC-11: Missing Auth Header Returns 401 (AC-6.8)

**Requirement**: PRD AC-6.8
**Priority**: High
**Type**: Security

**Steps**: `curl -s ".../section-timelines?period_start=2026-01-01&period_end=2026-01-31"` (no Authorization header)

**Expected Result**: 401 with `MISSING_AUTH`.
**Actual Result**: When service was alive: 401 -- `{"detail":{"error":"MISSING_AUTH","message":"Authorization header required"}}` -- **PASS**

(When service was crashed: 502 Bad Gateway from ALB -- expected infrastructure behavior.)

---

### TC-12: Invalid Token Returns 401 (AC-6.8)

**Requirement**: PRD AC-6.8
**Priority**: High
**Type**: Security

**Steps**: `curl -s -H "Authorization: Bearer short" ".../section-timelines?period_start=2026-01-01&period_end=2026-01-31"` (token < 10 chars)

**Expected Result**: 401 with `INVALID_TOKEN`.
**Actual Result**: When service was alive, auth validation rejects tokens < 10 chars per code at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/dependencies.py:117-122`. Runtime test hit during crash window (502). Code review confirms correct behavior. **PASS (code review)**.

---

## Critical Defects

### DEF-006: Endpoint Computation Exceeds ALB 60s Timeout -- CRASH LOOP

**Severity**: CRITICAL / P0
**Component**: `section_timeline_service.py:get_section_timelines()`
**Reproduction**:
1. Deploy commit `dda1c2f` to production
2. Wait for warm-up to complete (10-13 min)
3. Send GET request to `/api/v1/offers/section-timelines?period_start=2026-01-01&period_end=2026-01-31`
4. Request hangs for 60s, ALB returns 504

**Expected**: Response within 5s per NFR-1.
**Actual**: Response takes >60s, triggering ALB 504 Gateway Timeout.

**Evidence**:
```
connect_time: 0.107628s
time_to_first_byte: 60.427884s (exactly ALB timeout)
http_code: 504
```

**Impact**: The endpoint is completely unusable in production. After 1-3 requests time out, the service crashes and enters a warm-up -> timeout -> crash restart loop. No consumer can ever get data.

**Root Cause**: `get_section_timelines()` at `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py:303-407` does two expensive operations on every request:

1. **Task enumeration** (line 326-329): `client.tasks.list_async(project=..., opt_fields=_TASK_OPT_FIELDS).collect()` -- enumerates ~3,773 tasks from Asana API. This is a paginated API call that may take 5-15s depending on cache state.

2. **Per-offer story fetch** (lines 346-393): For each of the ~3,773 offers, calls `build_timeline_for_offer()` which calls `list_for_task_cached_async()`. Even with `_REQUEST_CONCURRENCY = 10` semaphore and `max_cache_age_seconds=7200`, if ANY offers have cache misses (expired, evicted, or never warmed), those misses trigger Asana API calls that are rate-limited (~100ms+ each). With even 5% cache misses (189 offers), that is 189 * 100ms / 10 concurrency = ~1.9s just for misses. But the overhead of 3,773 cache HITS at 5ms each with sem=10 is already ~1.9s. Combined with task enumeration, serialization of ~3,773 OfferTimelineEntry objects, and `model_dump()` per task, total wall time exceeds 60s.

**TDD vs. Reality Discrepancy**: The TDD (Section 12) assumes "~1-2 minutes for ~500 offers" and NFR-1 claims "< 5s p95 with pre-warmed caches." The actual production scale is ~3,773 offers (7.5x the TDD estimate of 500), which was not adequately load-tested before deployment.

**Remediation Options** (for principal-engineer):
1. **Pre-compute and cache results**: Compute timeline entries during warm-up or on a periodic schedule, store in memory/Redis, and serve from cache on request. This eliminates per-request computation entirely.
2. **Stream results**: Use FastAPI's `StreamingResponse` to begin sending data before computation completes, avoiding ALB timeout.
3. **Increase ALB timeout**: Increase ALB idle timeout from 60s to 120s or 300s. This is a band-aid that does not fix the root cause.
4. **Reduce per-request work**: Pre-enumerate tasks during warm-up and store the task list on `app.state`, eliminating the task enumeration API call per request.

---

### DEF-007: Service Crash Loop After Timeline Request Timeout

**Severity**: HIGH / P1
**Component**: ECS task / lifespan interaction
**Reproduction**: Occurs as a consequence of DEF-006. When the timeline endpoint request times out:
1. ALB returns 504 to client
2. The in-flight asyncio task continues running server-side
3. Multiple timed-out requests accumulate, exhausting memory or event loop capacity
4. Service becomes unresponsive (502 from ALB = target health check fails)
5. ECS restarts the task, triggering fresh warm-up (10-15 min)
6. Cycle repeats

**Expected**: Timed-out requests should be cancelled server-side; service should remain healthy.
**Actual**: Service crashes after 1-3 timed-out requests, entering a crash-restart loop.

**Evidence**: Observed 3 full crash-restart cycles during 57 minutes of testing:
- Cycle 1: 22:13 - 22:25 (crash at 22:25)
- Cycle 2: 22:36 - 23:01 (crash at 23:01)
- Cycle 3: 23:02 - ongoing (still in warm-up at 23:10)

**Impact**: Each crash costs 10-15 minutes of warm-up time. The service is effectively unusable. Other endpoints (query, entity write, workflows) may also be affected during crashes.

**Remediation**: Add server-side request timeout middleware. When ALB kills the connection, the handler should be cancelled. Consider `asyncio.timeout()` context manager wrapping the computation in the route handler with a 55s limit (under ALB's 60s).

---

### DEF-008: on_progress Callback Only Fires After All Warm-Up Completes

**Severity**: MEDIUM / P2
**Component**: `section_timeline_service.py:warm_story_caches()`
**Evidence**: Code review of `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py:468-476`:

```python
results = await asyncio.gather(
    *[_warm_one(task.gid) for task in tasks],
    return_exceptions=True,
)
warmed = sum(1 for r in results if r is True)
if on_progress is not None:
    on_progress(warmed, total)
```

The `on_progress` callback fires exactly ONCE -- after `asyncio.gather()` completes (all 3,773 tasks). This means `app.state.timeline_warm_count` stays at 0 and `app.state.timeline_total` stays at 0 throughout the entire warm-up period. The 50% readiness gate (AC-7.4) is therefore never satisfied incrementally; it jumps from 0% to 100% (or to `timeline_warm_failed`) in a single step.

**Impact**: The endpoint returns `TIMELINE_NOT_READY` for the entire warm-up duration even if 99% of offers are cached. The 50% threshold design (AC-7.4) is effectively bypassed.

**Expected (per TDD Section 6.2)**: Progress tracked incrementally so the endpoint becomes available once 50% are warmed.

**Remediation**: Move progress tracking inside the gather loop. Either use `asyncio.as_completed()` or update a shared counter from within `_warm_one()`.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Timeline endpoint permanently unusable at current scale | **Certain** | **Critical** | DEF-006 must be fixed before any consumer can use this |
| Other endpoints impacted by crash loop | **High** | **High** | DEF-007 -- other routes (query, entity-write) go down during restarts |
| Asana API rate limit exhaustion from warm-up retries | **High** | **Medium** | Each crash-restart triggers a new ~3,773-offer warm-up cycle |
| Memory pressure from accumulated timed-out requests | **Medium** | **High** | No server-side request timeout; handlers run indefinitely |

---

## Release Recommendation

**NO-GO**

### Rationale

The SectionTimeline endpoint is completely non-functional in production. It has never returned a 200 response in 57 minutes of testing across 3 service restart cycles. The root cause (DEF-006) is a fundamental scaling issue: the per-request computation for ~3,773 offers exceeds the ALB's 60-second timeout. The service enters a crash-restart loop (DEF-007) that degrades availability for all endpoints.

The TDD/PRD estimated ~500 offers; production has ~3,773 (7.5x). The architecture does not scale to actual production cardinality.

### Blocking Defects

| ID | Severity | Summary |
|----|----------|---------|
| DEF-006 | CRITICAL | Endpoint computation exceeds 60s ALB timeout -- never returns 200 |
| DEF-007 | HIGH | Service crash-restart loop after timed-out requests |
| DEF-008 | MEDIUM | Readiness gate bypassed -- progress callback fires only once |

### What Passed

| Test | Status |
|------|--------|
| Health check | PASS |
| 503 TIMELINE_NOT_READY shape | PASS |
| Missing params -> 422 | PASS |
| Invalid date format -> 422 | PASS |
| Missing auth -> 401 | PASS |
| Invalid token -> 401 | PASS (code review) |

### What Was Blocked

- Response shape validation (never got 200)
- billable >= active invariant check (never got 200)
- POC offer GID verification (never got 200)
- Offer count validation (~3,773 expected) (never got 200)
- Reversed date range 422 (service crashed during test window)

---

## Documentation Impact

None. The endpoint is not yet functional and should not be documented for consumers until DEF-006 and DEF-007 are resolved.

---

## Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| QA Report | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/QA-REPORT-SECTION-TIMELINE-PRODUCTION.md` | Yes (written) |
| PRD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/PRD-SECTION-TIMELINE.md` | Yes (Read-verified) |
| TDD | `/Users/tomtenuta/Code/autom8y-asana/.claude/wip/TDD-SECTION-TIMELINE.md` | Yes (Read-verified) |
| Route handler | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/routes/section_timelines.py` | Yes (Read-verified) |
| Service | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/services/section_timeline_service.py` | Yes (Read-verified) |
| Lifespan | `/Users/tomtenuta/Code/autom8y-asana/src/autom8_asana/api/lifespan.py` | Yes (Read-verified) |
