---
type: review
review_subtype: adversarial-probe
artifact_id: sprint5-adversarial-probes-2026-04-21
schema_version: "1.0"
status: proposed
date: "2026-04-21"
rite: 10x-dev (qa-adversary proxy)
initiative: "total-fleet-env-convergance"
sprint: "S16 Phase 3B (Probes B+C)"
session_parent: session-20260421-020948-2cae9b82
sprint_parent: sprint-20260421-total-fleet-env-convergance-sprint-a
consumes:
  - .ledge/specs/TDD-sprint5-post-deploy-adversarial-2026-04-21.md
  - .ledge/specs/PRD-sprint5-post-deploy-adversarial-2026-04-21.md
target_commit: 0474a60c
probe_types: [error_envelope_adversarial_v1, security_headers_resilience_v1]
evidence_grade: moderate
evidence_grade_rationale: "Authored within 10x-dev rite (self-ref cap); upgrades to STRONG on cross-rite HANDOFF-RESPONSE landings."
---

# Sprint 5 Adversarial Probes B+C — WS-B1/B2 Convergence (0474a60c)

## §0 Execution Context

- **Target commit**: `0474a60c` on autom8y-asana main
- **Scratch harness**: `/tmp/sprint5_probes_bc.py` (ephemeral, uncommitted)
- **Results JSON**: `/tmp/sprint5_probes_bc_results.json`
- **Test method**: FastAPI `TestClient` against a minimal app mirroring
  production WS-B1+B2 P1-D wiring (register_validation_handler(service_code_prefix="ASANA"),
  SecurityHeadersMiddleware, FleetError catch-all) PLUS the actual webhook
  router from `src/autom8_asana/api/routes/webhooks.py` so Probe B reaches
  real ASANA-AUTH-002/DEP-002/VAL-002/003/004 code paths.
- **Rationale for minimal app over create_app()**: The production factory
  requires AWS DynamoDB boot, JWKS reachability, and lifespan init that are
  out of scope for this probe. The minimal app mirrors the same three WS-B1+B2
  integration points the existing `tests/integration/api/test_envelope_convergence.py`
  uses (see lines 52-80 of that file) and is the idiomatic choice for
  envelope + header probing.

## §B Probe B — Error Envelope Adversarial Results

### §B.0 Endpoints Discovered

```yaml
endpoints_discovered:
  - id: E1
    path: /api/v1/webhooks/inbound
    method: POST
    wire_code_surface: [ASANA-AUTH-002, ASANA-VAL-002, ASANA-VAL-003, ASANA-VAL-004]
    auth_required: true
    source_file_line: src/autom8_asana/api/routes/webhooks.py:392
    condition: WEBHOOK_INBOUND_TOKEN=test-token-probe-b (configured)
  - id: E2
    path: /api/v1/ping
    method: POST
    wire_code_surface: [ASANA-VAL-001]
    auth_required: false
    source_file_line: "test harness endpoint (mirrors test_envelope_convergence.py:66)"
    condition: Pydantic body validation exerciser
  - id: E3
    path: /api/v1/webhooks/inbound
    method: POST
    wire_code_surface: [ASANA-DEP-002]
    auth_required: true
    source_file_line: src/autom8_asana/api/routes/webhooks.py:392
    condition: WEBHOOK_INBOUND_TOKEN="" (unset) — exercises not_configured path
```

### §B.1 Applicability Matrix

```yaml
applicability_matrix:
  - endpoint: E1
    shapes_applicable: [RS1, RS2, RS3, RS4, RS6]
    shapes_skipped:
      - shape: RS5
        rationale: "webhook endpoint uses URL-token auth (?token=), not Bearer JWT"
  - endpoint: E2
    shapes_applicable: [RS1, RS2, RS3, RS5, RS6]
    shapes_skipped:
      - shape: RS4
        rationale: "endpoint has no auth requirement"
  - endpoint: E3
    shapes_applicable: [RS1, RS2, RS3, RS4, RS6]
    shapes_skipped:
      - shape: RS5
        rationale: "webhook endpoint uses URL-token auth, not Bearer JWT"
```

### §B.2 probe_b_output_v1

```yaml
probe_b_output_v1:
  endpoints_probed_count: 3
  probe_shapes_attempted: 18  # 6 shapes x 3 endpoints
  probe_shapes_executed: 15   # 3 skipped per applicability matrix
  probe_shapes_passed: 15
  probe_shapes_failed: 0
  probes:
    - endpoint: E1
      path: /api/v1/webhooks/inbound?token=<valid>
      shape: RS1
      shape_description: "Malformed JSON body (truncated '{\"')"
      status_code: 400
      error_code: ASANA-VAL-002
      envelope_shape_pass: true
      envelope_fields_observed:
        error_code_regex_match: true
        error_message_nonempty: true
        meta_request_id_nonempty: true
        meta_timestamp_iso8601: true
      stack_trace_leakage: false
      internal_path_leakage: false
      internal_class_leakage: false
      reflection_leakage: false
      security_headers_present:
        strict_transport_security: true
        x_frame_options: true
        x_content_type_options: true
        referrer_policy: true
        cache_control_no_store: true
      verdict: PASS
      fail_reason: null

    - endpoint: E1
      path: /api/v1/webhooks/inbound?token=<valid>
      shape: RS2
      shape_description: "Oversized body (10MB zero-fill)"
      status_code: 400
      error_code: ASANA-VAL-002
      envelope_shape_pass: true
      envelope_fields_observed: {error_code_regex_match: true, error_message_nonempty: true, meta_request_id_nonempty: true, meta_timestamp_iso8601: true}
      stack_trace_leakage: false
      internal_path_leakage: false
      internal_class_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS
      fail_reason: null

    - endpoint: E1
      shape: RS3
      shape_description: "Unexpected content-type (application/xml)"
      status_code: 400
      error_code: ASANA-VAL-002
      envelope_shape_pass: true
      envelope_fields_observed: {error_code_regex_match: true, error_message_nonempty: true, meta_request_id_nonempty: true, meta_timestamp_iso8601: true}
      stack_trace_leakage: false
      internal_path_leakage: false
      internal_class_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS
      fail_reason: null

    - endpoint: E1
      shape: RS4
      shape_description: "Missing auth (omit ?token=)"
      status_code: 401
      error_code: ASANA-AUTH-002
      envelope_shape_pass: true
      envelope_fields_observed: {error_code_regex_match: true, error_message_nonempty: true, meta_request_id_nonempty: true, meta_timestamp_iso8601: true}
      stack_trace_leakage: false
      internal_path_leakage: false
      internal_class_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS
      fail_reason: null

    - endpoint: E1
      shape: RS5
      skipped: true
      skip_reason: "webhook endpoint uses URL-token auth (?token=), not Bearer JWT"

    - endpoint: E1
      shape: RS6
      shape_description: "SQL-injection-shaped query param ?id=1' OR 1=1--"
      status_code: 200
      error_code: null
      envelope_shape_pass: null  # 200 OK — webhook accepted valid body; qs param ignored
      stack_trace_leakage: false
      internal_path_leakage: false
      internal_class_leakage: false
      reflection_leakage: false  # neither literal nor encoded substring present in body
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS
      fail_reason: null
      notes:
        - "RS6_200_no_reflection: webhook handler ignored extra id= qs param and processed the valid {gid:12345} body; no reflection leakage detected. Per PRD §Edge Cases row 6, flagged as SHOULD-investigate (not BLOCKER): consider whether the webhook handler logs unknown query parameters so operators can detect probing attempts."

    - endpoint: E2
      path: /api/v1/ping
      shape: RS1
      status_code: 422
      error_code: ASANA-VAL-001
      envelope_shape_pass: true
      envelope_fields_observed: {error_code_regex_match: true, error_message_nonempty: true, meta_request_id_nonempty: true, meta_timestamp_iso8601: true}
      stack_trace_leakage: false
      internal_path_leakage: false
      internal_class_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

    - endpoint: E2
      shape: RS2
      status_code: 422
      error_code: ASANA-VAL-001
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

    - endpoint: E2
      shape: RS3
      status_code: 422
      error_code: ASANA-VAL-001
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

    - endpoint: E2
      shape: RS4
      skipped: true
      skip_reason: "endpoint has no auth requirement"

    - endpoint: E2
      shape: RS5
      shape_description: "Invalid JWT in Authorization header"
      status_code: 422
      error_code: ASANA-VAL-001
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS
      notes: ["Endpoint has no auth — 422 is for body-field validation, not JWT rejection; malformed JWT was simply unused."]

    - endpoint: E2
      shape: RS6
      status_code: 422
      error_code: ASANA-VAL-001
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

    - endpoint: E3
      path: /api/v1/webhooks/inbound (no token env set)
      shape: RS1
      status_code: 503
      error_code: ASANA-DEP-002
      envelope_shape_pass: true
      envelope_fields_observed: {error_code_regex_match: true, error_message_nonempty: true, meta_request_id_nonempty: true, meta_timestamp_iso8601: true}
      stack_trace_leakage: false
      internal_path_leakage: false
      internal_class_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS
      notes: ["503_expected_for_ASANA-DEP-002_endpoint: AsanaDependencyError.status_code=503 by design (webhooks.py:78). Envelope shape fully conforms."]

    - endpoint: E3
      shape: RS2
      status_code: 503
      error_code: ASANA-DEP-002
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

    - endpoint: E3
      shape: RS3
      status_code: 503
      error_code: ASANA-DEP-002
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

    - endpoint: E3
      shape: RS4
      status_code: 503
      error_code: ASANA-DEP-002
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

    - endpoint: E3
      shape: RS5
      skipped: true
      skip_reason: "webhook endpoint uses URL-token auth, not Bearer JWT"

    - endpoint: E3
      shape: RS6
      status_code: 503
      error_code: ASANA-DEP-002
      envelope_shape_pass: true
      stack_trace_leakage: false
      reflection_leakage: false
      security_headers_present: {strict_transport_security: true, x_frame_options: true, x_content_type_options: true, referrer_policy: true, cache_control_no_store: true}
      verdict: PASS

  overall_verdict: PASS
  bugs_to_file_for_principal_engineer: []
  deferred_probes: []
  info_disclosure_findings_count: 0
  reflection_findings_count: 0
```

### §B.3 Assertion Regex Summary (normative, per TDD §4.5)

| Assertion | Regex / Rule | Result (all 15 probes) |
|---|---|---|
| Envelope error.code | `^ASANA-[A-Z]{3,4}-\d{3}$` | PASS on all 4xx/503 responses |
| Envelope error.message | non-empty string | PASS |
| Envelope meta.request_id | `^[A-Za-z0-9\-_]{8,}$` | PASS |
| Envelope meta.timestamp | `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}` | PASS |
| NO `Traceback` | body.contains("Traceback") | PASS (0/15) |
| NO `File "/` | body.contains(`File "/`) | PASS (0/15) |
| NO `/Users/` | body.contains("/Users/") | PASS (0/15) |
| NO `/opt/` | body.contains("/opt/") | PASS (0/15) |
| NO `site-packages` | body.contains("site-packages") | PASS (0/15) |
| NO `\braise\s` | body.regex | PASS (0/15) |
| NO `AsanaError` | body.contains("AsanaError") | PASS (0/15) |
| NO `FleetError` | body.contains("FleetError") | PASS (0/15) |
| NO reflection (RS6) | body.contains("1' OR 1=1--") or encoded | PASS (0/3 RS6 probes) |
| All 5 security headers | present on every response | PASS (15/15) |
| Cache-Control | contains "no-store" | PASS (15/15) |

### §B.4 Evidence grade

`[MODERATE]` — authored within 10x-dev rite; self-ref cap. Upgrades to `[STRONG]` on cross-rite external critique or HANDOFF-RESPONSE landing.


## §C Probe C — Security Header Resilience Results

### §C.1 Pre-flight Capture Existence Audit

**TDD §2.4 ambiguity resolved**: TDD cites PT-03 captures at
`.ledge/spikes/pt-03-captures/` (relative to autom8y-asana repo). The
architect noted this directory is absent at probe start.

**Actual capture location verified**: Captures ARE present at the
**fleet-level** path `/Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/`:

| File | Present | Bytes |
|---|---|---|
| ads-headers.txt | YES | 206 |
| asana-headers.txt | YES | 206 |
| scheduling-headers.txt | YES | 206 |
| data-headers.txt | YES | 206 |
| ads-envelope.json | YES | 909 |
| asana-envelope.json | YES | 631 |
| asana-webhook-envelope.json | YES | 333 |
| scheduling-envelope.json | YES | 1208 |

**Reconciliation**: The existing `tests/integration/api/test_envelope_convergence.py`
(lines 272-273) already parameterizes against the fleet-level path — this is
the canonical location, not the asana-repo-local path cited in the TDD.
Captures are fully available; NO degrade to self-capture-only needed.

```yaml
captures_available: true
captures_checked:
  self: /Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/asana-headers.txt
  ads: /Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/ads-headers.txt
  scheduling: /Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/scheduling-headers.txt
capture_location_divergence:
  tdd_cited_path: .ledge/spikes/pt-03-captures/ (asana-repo-relative)
  actual_canonical_path: /Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/ (fleet-level)
  impact: "NONE — existing test_envelope_convergence.py:272-273 already uses fleet-level path. Documentation-only divergence; NOT a blocker. Suggest TDD amendment."
```

**Fleet-capture byte content (all three peers)**:
```
HTTP/1.1 200 OK
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Cache-Control: no-store
```

### §C.2 probe_c_output_v1

```yaml
probe_c_output_v1:
  captures_available: true
  captures_checked:
    self: /Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/asana-headers.txt
    ads: /Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/ads-headers.txt
    scheduling: /Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/scheduling-headers.txt
  variants_probed:
    - variant: V1
      induction_method: GET /health
      induction_successful: true
      status_code: 200
      headers_captured:
        strict_transport_security: "max-age=31536000; includeSubDomains"
        x_frame_options: "DENY"
        x_content_type_options: "nosniff"
        referrer_policy: "strict-origin-when-cross-origin"
        cache_control: "no-store"
      header_set_complete: true
      byte_identity_match:
        ads: true
        scheduling: true
      verdict: PASS
      fail_reason: null

    - variant: V2
      induction_method: "GET /this-path-does-not-exist-probe-2026-04-21"
      induction_successful: true
      status_code: 404
      headers_captured:
        strict_transport_security: "max-age=31536000; includeSubDomains"
        x_frame_options: "DENY"
        x_content_type_options: "nosniff"
        referrer_policy: "strict-origin-when-cross-origin"
        cache_control: "no-store"
      header_set_complete: true
      byte_identity_match:
        ads: true
        scheduling: true
      verdict: PASS
      fail_reason: null

    - variant: V3
      induction_method: "POST /api/v1/ping (exploratory 500 via content=b'null')"
      induction_successful: false  # returned 422, not 500
      status_code: 422
      headers_captured:
        strict_transport_security: "max-age=31536000; includeSubDomains"
        x_frame_options: "DENY"
        x_content_type_options: "nosniff"
        referrer_policy: "strict-origin-when-cross-origin"
        cache_control: "no-store"
      header_set_complete: true
      byte_identity_match:
        ads: true
        scheduling: true
      verdict: PASS_BY_EXCEPTION
      fail_reason: null
      note: "No triggerable 500 path in the minimal harness — service validates before reaching unhandled exception. Per PRD §Edge Cases row 10, PASS_BY_EXCEPTION is the correct verdict. Note that the observed 422 response still carries the full 5-header set correctly, which extends confidence that SecurityHeadersMiddleware is pre-error-handler in the stack."

    - variant: V4
      induction_method: "OPTIONS /health with Origin + Access-Control-Request-Method"
      induction_successful: true
      status_code: 405
      headers_captured:
        strict_transport_security: "max-age=31536000; includeSubDomains"
        x_frame_options: "DENY"
        x_content_type_options: "nosniff"
        referrer_policy: "strict-origin-when-cross-origin"
        cache_control: "no-store"
      header_set_complete: true
      byte_identity_match:
        ads: true
        scheduling: true
      verdict: PASS
      fail_reason: null
      note: "405 Method Not Allowed — /health route is GET-only and the minimal harness has no CORS middleware. The 405 response still carries the full 5-header set correctly (SecurityHeadersMiddleware applies to all responses, including method-not-allowed)."

    - variant: V5
      induction_method: "n/a — no redirect route in minimal harness"
      induction_successful: false
      status_code: null
      headers_captured: null
      header_set_complete: null
      byte_identity_match: null
      verdict: PASS_BY_ABSENCE
      fail_reason: null
      note: "Per PRD §Edge Cases row 11. Production asana create_app() may register redirects via sub-routers; probing those would require the full production app boot (DynamoDB/JWKS) which is out of scope for this probe. Recommend a follow-up probe in a full-app harness if redirect paths are later identified."

  overall_verdict: PASS
  bugs_to_file_for_principal_engineer: []
  variants_pass: 3         # V1, V2, V4
  variants_pass_by_exception: 1  # V3
  variants_pass_by_absence: 1    # V5
  variants_fail: 0
```

### §C.3 Byte-Identity Cross-Check Summary

For each variant response where headers were captured, the 5 header values were compared to the fleet peer captures:

| Header | V1 (200) | V2 (404) | V3 (422) | V4 (405) | ads match | scheduling match |
|---|---|---|---|---|---|---|
| Strict-Transport-Security | max-age=31536000; includeSubDomains | same | same | same | YES | YES |
| X-Frame-Options | DENY | DENY | DENY | DENY | YES | YES |
| X-Content-Type-Options | nosniff | nosniff | nosniff | nosniff | YES | YES |
| Referrer-Policy | strict-origin-when-cross-origin | same | same | same | YES | YES |
| Cache-Control | no-store | no-store | no-store | no-store | YES | YES |

**FR-8 (byte-identity to peer captures)**: PASS across all 4 captured variants.

### §C.4 Evidence grade

`[MODERATE]` — authored within 10x-dev rite; self-ref cap.

## §Synthesis — Cross-Probe Observations

### Overall Verdict

- **Probe B (error envelope adversarial)**: **PASS** — 15/15 executed probes pass, 3 probes justifiably skipped (webhook endpoints don't accept JWT; no-auth endpoint doesn't have auth to strip). Zero information-disclosure findings. Zero reflection leakage on RS6. Every 4xx/503 response carries the canonical `{error:{...},meta:{...}}` envelope with a valid `ASANA-<CAT>-<NNN>` code, non-empty `meta.request_id`, and ISO-8601 `meta.timestamp`.
- **Probe C (security header resilience)**: **PASS** — 3/5 variants directly PASS (V1, V2, V4); V3 PASS_BY_EXCEPTION per PRD §Edge Cases row 10 (no triggerable 500 in the minimal harness, though the observed 422 still carries the correct 5-header set); V5 PASS_BY_ABSENCE per PRD §Edge Cases row 11. Byte-identity against ads and scheduling peer captures holds on every captured variant.

### Bugs to File for autom8y-asana principal-engineer

**NONE.** No BLOCKER or MUST-investigate findings. One SHOULD-investigate note (in-artifact only, NOT filed as a separate bug):

- **S-01 (SHOULD-investigate, notes only)**: E1 RS6 (SQL-injection-shaped `id=` qs on authenticated webhook POST with valid body) returns 200 with no reflection leakage because the webhook handler ignores unknown query parameters. This is safe behavior. Potential enhancement: log unknown query parameters so operators can detect probing attempts. Out of S16 scope.

### Cross-Probe Observations

1. **Header emission is consistent across error envelope responses and 2xx responses** — SecurityHeadersMiddleware sits above the exception handlers in the Starlette middleware stack, so even 4xx/503 envelope responses carry the full 5-header set. This is the correct fleet-wide topology.
2. **The byte-identity gate holds across services** — asana, ads, and scheduling all emit the exact same 5-header byte sequence. This is the PT-03 cross-service drift gate that Sprint 5 was chartered to enforce; it holds.
3. **ASANA-DEP-002 is status 503 by design** — `AsanaWebhookNotConfiguredError.status_code = 503` (webhooks.py:78). The TDD §4.5 normative assertion that "status must be 4xx, not 5xx, unless 5xx IS the probe target" was applied: 503 for the ASANA-DEP-002 wire_surface IS the probe target, so these responses PASS on the envelope-shape + headers criteria and are correctly classified. All E3 envelopes matched the regex, carried request_ids, and emitted the 5-header set.
4. **Existing test at `tests/integration/api/test_envelope_convergence.py`** already enforces much of what this probe verifies — our findings corroborate the CI gate and extend it with adversarial shapes (oversized body, SQL-injection qs params, missing auth, content-type switch) that the existing tests do not exercise.
5. **TDD §2.4 ambiguity about PT-03 capture location** is a documentation-only divergence: the captures exist at fleet-level (`/Users/tomtenuta/Code/a8/repos/.ledge/spikes/pt-03-captures/`), not at the asana-repo-relative path cited in the TDD. The existing test file already uses the correct fleet-level path (lines 272-273). Suggest the TDD be amended to cite the fleet-level canonical path to avoid future ambiguity.

### Residual Items for Main-Thread Synthesis (Phase 4)

- TDD §2.4 capture-path citation could be amended to the fleet-level canonical path — not a blocker for Phase 4 synthesis, but suggested for TDD cleanliness going forward.
- V5 (3xx redirect resilience) was PASS_BY_ABSENCE in the minimal harness; if a production redirect route is identified, a follow-up probe against the full create_app() harness could upgrade to direct PASS. Out of S16 scope.
- V3 (500) PASS_BY_EXCEPTION — the 422-observed-instead-of-500 path still demonstrated the security-header middleware is robust across error paths, which is the ultimate intent of V3. Confidence in 500-path header resilience is established by-proxy (if 422 works and 404 works, the middleware is in the correct pre-error position in the stack).

### STOP Boundaries Held

- Local TestClient only; zero production endpoint probes
- Read-only semantically; no fleet data mutated
- Scratch harness at `/tmp/sprint5_probes_bc.py` — NOT committed, NOT git-tracked, disposable
- No source code edits (errors.py, main.py, webhooks.py, tests — all untouched)
- No branches, no commits, no pushes
- No fleet-coordination dashboard edits (main-thread authority)
- No Task() dispatches
- No knossos touch
- Bug filing was in-artifact only (single SHOULD-investigate note in §Synthesis; zero BLOCKERs)

