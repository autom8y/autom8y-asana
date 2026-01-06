# QA Validation Report: Hotfix 2500444

**Date**: 2026-01-06
**Target**: Production API (`https://asana.api.autom8y.io`)
**Hotfix**: 2500444 - Project discovery and schema dispatch

---

## Executive Summary

| Verdict | Details |
|---------|---------|
| **NO-GO** | Critical defects remain - Contact endpoint still timing out |

---

## What Was Changed (Hotfix 2500444)

1. Project discovery now uses normalized name matching (handles "Business Offers", "Business Units", etc.)
2. Schema dispatch uses SchemaRegistry - Contact uses CONTACT_SCHEMA, Offer uses OFFER_SCHEMA
3. Should fix Contact timeout and Offer PROJECT_NOT_CONFIGURED

---

## Test Results

### Entity Resolution Endpoints

| Entity Type | Status Code | Response Time | Result | Notes |
|-------------|-------------|---------------|--------|-------|
| **Unit** | 200 | 0.47-30.3s | PASS | First request slow (cold start), subsequent fast |
| **Contact** | 200/Timeout | 22.9s-TIMEOUT | **FAIL** | 2 of 3 attempts TIMEOUT (30s+), returns DATAFRAME_UNAVAILABLE |
| **Offer** | 200/Timeout | 2.8-30s | **PARTIAL** | Returns DATAFRAME_UNAVAILABLE, intermittent timeouts |
| **Business** | 200 | 0.48-0.54s | PASS | Consistent fast response |

### Success Criteria Validation

| Criterion | Expected | Actual | Status |
|-----------|----------|--------|--------|
| All 4 entity types respond (no 503 PROJECT_NOT_CONFIGURED) | No 503 errors | Unit/Business: No 503; Contact/Offer: DATAFRAME_UNAVAILABLE | **PARTIAL** |
| Contact endpoint responds WITHOUT timeout | < 30s | 2 of 3 attempts TIMEOUT | **FAIL** |
| Response times under 5 seconds | < 5s | Unit cold: 30s, Contact: TIMEOUT | **FAIL** |
| Demo script completes successfully | Complete | N/A (env var issue) | **NOT RUN** |

---

## Defect Reports

### DEF-001: Contact Endpoint Still Timing Out (CRITICAL)

**Severity**: Critical
**Priority**: P1

**Description**: The Contact endpoint (`/v1/resolve/contact`) is still experiencing timeouts, exactly matching the pre-hotfix behavior. This was the primary issue the hotfix was intended to fix.

**Reproduction Steps**:
1. Acquire S2S token
2. POST to `https://asana.api.autom8y.io/v1/resolve/contact`
3. Body: `{"criteria":[{"contact_phone":"+15551234567"}]}`
4. Observe timeout after 30+ seconds

**Expected Behavior**: Response within 5 seconds

**Actual Behavior**:
- 2 of 3 attempts: TIMEOUT after 30+ seconds
- 1 of 3 attempts: Response after 22.9 seconds with `DATAFRAME_UNAVAILABLE` error

**Impact**: Contact resolution is unusable for production S2S communication.

---

### DEF-002: Offer Endpoint Returns DATAFRAME_UNAVAILABLE (HIGH)

**Severity**: High
**Priority**: P2

**Description**: The Offer endpoint successfully responds (200) but returns `DATAFRAME_UNAVAILABLE` error instead of resolution results.

**Reproduction Steps**:
1. Acquire S2S token
2. POST to `https://asana.api.autom8y.io/v1/resolve/offer`
3. Body: `{"criteria":[{"offer_id":"OFF-12345"}]}`

**Expected Behavior**: Either successful resolution or `NOT_FOUND`

**Actual Behavior**:
```json
{
  "results": [{"gid": null, "error": "DATAFRAME_UNAVAILABLE", "multiple": null}],
  "meta": {...}
}
```

**Impact**: Offer resolution is not functional. The hotfix was supposed to configure OFFER_SCHEMA via SchemaRegistry.

---

### DEF-003: Contact Endpoint Returns DATAFRAME_UNAVAILABLE (HIGH)

**Severity**: High
**Priority**: P2

**Description**: When Contact endpoint doesn't timeout, it returns `DATAFRAME_UNAVAILABLE` instead of resolution results.

**Actual Response** (when successful):
```json
{
  "results": [{"gid": null, "error": "DATAFRAME_UNAVAILABLE", "multiple": null}],
  "meta": {...}
}
```

**Impact**: Even when Contact doesn't timeout, it cannot resolve entities.

---

### DEF-004: Unit Endpoint Cold Start is 30+ Seconds (MEDIUM)

**Severity**: Medium
**Priority**: P3

**Description**: First request to Unit endpoint after service restart takes 30+ seconds.

**Reproduction Steps**:
1. Wait for service cold start (or force restart)
2. POST to `/v1/resolve/unit`
3. First request: 30.3 seconds
4. Subsequent requests: 0.47 seconds

**Expected Behavior**: All requests under 5 seconds

**Actual Behavior**: First request 30.3s, subsequent ~0.5s

**Impact**: User experience degradation on cold starts; may cause timeout cascades.

---

## API Stability Observations

| Observation | Details |
|-------------|---------|
| Intermittent 503/504 | Load balancer occasionally returns 503/504 (service temporarily unavailable) |
| Health endpoint always healthy | `/health` consistently returns 200 OK |
| Multiple container instances | Evidence of load balancing between healthy and unhealthy targets |
| Cold start latency | First request to cached endpoints takes 30+ seconds |

---

## Root Cause Analysis (Suspected)

1. **DATAFRAME_UNAVAILABLE**: The DataFrame cache for Contact and Offer entities is not being populated at startup. This could indicate:
   - Schema dispatch is working but DataFrame build is failing
   - Project GID is found but data fetch is failing
   - Async initialization race condition

2. **Contact Timeout**: The timeout occurs before `DATAFRAME_UNAVAILABLE` is returned, suggesting:
   - DataFrame build is being attempted on each request (not cached)
   - No timeout/circuit breaker on DataFrame fetch
   - Possible retry loop exhausting the 30s window

3. **Cold Start Latency**: Unit endpoint has 30s first-request latency, indicating:
   - Lazy initialization of DataFrame cache
   - Full DataFrame build on first access

---

## Recommendations

### Immediate (Before Re-deploy)

1. **Add logging** to identify where Contact/Offer DataFrame builds are failing
2. **Verify project GID discovery** logs show successful resolution for all 4 entity types
3. **Check SchemaRegistry** initialization to confirm CONTACT_SCHEMA and OFFER_SCHEMA are registered

### Short-term

1. Implement eager DataFrame initialization at startup (not lazy)
2. Add circuit breaker for DataFrame fetch to fail fast instead of timeout
3. Add structured health check that validates all DataFrames are ready

### Testing

1. Add integration tests that verify DataFrame availability before marking healthy
2. Add smoke tests for all 4 entity types in deployment pipeline

---

## Test Artifacts

| File | Description |
|------|-------------|
| `/Users/tomtenuta/Code/autom8_asana/tmp/qa_hotfix_test.py` | Initial test script |
| `/Users/tomtenuta/Code/autom8_asana/tmp/qa_individual_tests.py` | Verbose individual endpoint tests |
| `/Users/tomtenuta/Code/autom8_asana/tmp/qa_stability_check.py` | Multi-attempt stability check |

---

## Attestation

| Artifact | Path | Verified |
|----------|------|----------|
| QA Report | `/Users/tomtenuta/Code/autom8_asana/docs/test-plans/QA-REPORT-hotfix-2500444.md` | Yes |
| Test Script 1 | `/Users/tomtenuta/Code/autom8_asana/tmp/qa_hotfix_test.py` | Yes |
| Test Script 2 | `/Users/tomtenuta/Code/autom8_asana/tmp/qa_individual_tests.py` | Yes |
| Test Script 3 | `/Users/tomtenuta/Code/autom8_asana/tmp/qa_stability_check.py` | Yes |

---

## Conclusion

**Release Recommendation: NO-GO**

The hotfix has partially addressed the PROJECT_NOT_CONFIGURED issue (no more 503s from the application), but has not resolved the core problems:

1. **Contact endpoint still times out** (2 of 3 attempts)
2. **Contact and Offer return DATAFRAME_UNAVAILABLE** instead of resolution results
3. **Cold start latency is 30+ seconds** for cached endpoints

The hotfix should not be considered complete until Contact and Offer endpoints can successfully resolve entities with response times under 5 seconds.

---

*QA Adversary - 2026-01-06*
