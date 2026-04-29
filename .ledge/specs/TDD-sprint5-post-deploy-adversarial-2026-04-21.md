---
title: "TDD — Sprint 5 Post-Deploy Adversarial (S16, WS-6) — 3-Probe Harness"
type: spec
artifact_type: spec
spec_subtype: tdd
status: proposed
phase_state: TDD_FOR_PHASE_3_DISPATCH
owner_rite: 10x-dev
owner_agent: architect
initiative: total-fleet-env-convergance
sprint: S16
workstream: WS-6
potnia_checkpoint: PT-16
target_commit: 0474a60c
target_commit_message: "feat(asana): WS-B1+B2 canonical error envelope + security headers convergence"
target_commit_date: 2026-04-20T21:06+02:00
repo: autom8y-asana
consumes_prd: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-sprint5-post-deploy-adversarial-2026-04-21.md
shape_ref: /Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.shape.md
fleet_coordination_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md
scope_type: ORTHOGONAL
scope_lock: true
date: 2026-04-21
evidence_grade: "[MODERATE]"
evidence_grade_rationale: "Authored within 10x-dev rite (self-ref cap); TDD translates PRD methodology without scope renegotiation."
---

# TDD: Sprint 5 Post-Deploy Adversarial — 3-Probe Harness (S16)

## §1 Status + Source

- **Status**: `proposed` (per ledge-frontmatter-schema valid lifecycle)
- **Source**: PRD at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-sprint5-post-deploy-adversarial-2026-04-21.md` — authored by requirements-analyst Phase 1; 7 sections; 10 FRs; 10 NFRs; 14-row edge-case matrix; scope LOCKED.
- **Consumes**: PRD §Probe Matrix verbatim — no scope renegotiation.
- **Produces**: Implementation-grade specialist dispatch specifications for Phase 3 (principal-engineer Probe A + qa-adversary Probes B+C parallel).
- **Scope-lock invariant**: This TDD translates PRD methodology into concrete dispatch specs. If ambiguity surfaces during Phase 3, specialist MUST escalate to main-thread — NOT invent methodology extension.

## §2 Architecture — 3-Probe Harness

### 2.1 Harness shape

Three probes execute against landed commit `0474a60c`:

| Probe | Specialist | Nature | Target |
|-------|------------|--------|--------|
| A | principal-engineer | Read-only code/git sweep | env-var + service-entry-point surface |
| B | qa-adversary | Local/staging HTTP adversarial requests | WS-B1 canonical error envelope resilience |
| C | qa-adversary | Local/staging HTTP variant responses | WS-B2 security header byte-identity |

### 2.2 Invariants (non-negotiable)

- **Read-only invariant**: All 3 probes are read-only against fleet artifacts. NO code changes. NO branches. NO commits. NO production endpoint access.
- **Artifact-non-overlap invariant**:
  - Probe A writes EXCLUSIVELY to `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-env-surface-discovery-2026-04-21.md`
  - Probes B+C write EXCLUSIVELY to `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-adversarial-probes-2026-04-21.md` (shared artifact; qa-adversary authors both sections in single dispatch)
  - principal-engineer and qa-adversary paths NEVER touch each other's artifacts.
- **Scope-lock invariant**: No PRD scope modification. Specialist escalation on ambiguity is mandated.
- **Fleet-safety invariant**: Zero cross-rite scope-creep. Out-of-scope findings (ecosystem, hygiene, SRE) are FLAGGED in audit, NOT executed.

### 2.3 Parallelization safety analysis

| Resource | Probe A Usage | Probe B+C Usage | Contention? |
|----------|---------------|-----------------|-------------|
| Git working tree | READ (git show, git diff of `0474a60c`) | READ (source reads for router enumeration) | NO — independent read-only reads |
| Source files (3 touched) | READ (grep for env/service patterns) | READ (qa-adversary reads `main.py` for router paths) | NO — concurrent reads safe |
| HTTP port (local test harness) | NOT USED | BIND (TestClient ephemeral) | NO — Probe A does not touch HTTP |
| Artifact paths | `sprint5-env-surface-discovery-2026-04-21.md` | `sprint5-adversarial-probes-2026-04-21.md` | NO — disjoint |
| Python interpreter | Independent process (principal-engineer dispatch) | Independent process (qa-adversary dispatch) | NO — process isolation |

**Verdict**: Parallel dispatch is SAFE. Main-thread dispatches principal-engineer + qa-adversary concurrently in Phase 3.

### 2.4 PT-03 captures ambiguity (SURFACED FOR POTNIA)

PRD cites captures at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/`. Architect verification (2026-04-21): **directory does not exist** at that path. PRD §Assumptions clause 3 pre-anticipates this: "If peer captures are missing, Probe C degrades to self-capture-only with explicit annotation."

**Downstream handling**: Probe C specification below inherits the degrade-to-self-capture path; qa-adversary MUST verify capture existence at probe start and annotate accordingly. This is NOT a TDD blocker — PRD methodology covers this exception class.

## §3 Probe A Specification — env-surface-discovery (principal-engineer)

### 3.1 Dispatch summary

- **Specialist**: principal-engineer
- **Complexity**: FEATURE (bounded methodology; zero code changes)
- **Target commit**: `0474a60c` on autom8y-asana main
- **Target files**: `src/autom8_asana/api/errors.py`, `src/autom8_asana/api/main.py`, `src/autom8_asana/api/routes/webhooks.py`
- **Output artifact**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-env-surface-discovery-2026-04-21.md`
- **Wall-clock budget**: ≤ 15 minutes (per NFR-8)
- **Evidence grade**: `[MODERATE]` (authored within 10x-dev rite)

### 3.2 Step A.1 — Commit diff capture

```bash
cd /Users/tomtenuta/Code/a8/repos/autom8y-asana
git show 0474a60c -- \
  'src/autom8_asana/api/errors.py' \
  'src/autom8_asana/api/main.py' \
  'src/autom8_asana/api/routes/webhooks.py' \
  'pyproject.toml' \
  'secretspec.toml' \
  '.env/' > /tmp/0474a60c-diff.txt 2>/dev/null || true
```

Record: byte size of diff output; list of files present in diff.

### 3.3 Step A.2 — Python env-var pattern grep (scope-bounded)

Apply 5 normative patterns to the 3 touched source files. Use Grep tool with `-n` (line numbers) and `output_mode: content` for evidence capture.

| ID | Pattern | Purpose |
|----|---------|---------|
| PA1 | `os\.environ\[` OR `os\.getenv\(` | Direct env-var reads (Python stdlib) |
| PA2 | `settings\.[a-z_]+` within a `*Settings(BaseSettings)` context | Pydantic Settings field access |
| PA3 | `\b(AUTOM8Y_\|SERVICE_\|AWS_\|SLACK_\|STRIPE_\|CALENDLY_\|GRAFANA_\|AMP_\|OTEL_\|ASANA_)[A-Z_]+\b` | ALL_CAPS env-var identifier namespaces |
| PA4 | `(_API_KEY\|_TOKEN\|_URL\|_SECRET\|_PASSWORD\|_HOST\|_PORT\|_ARN\|_CLIENT_ID\|_CLIENT_SECRET)\b` | Env-var suffix conventions |
| PA5 | `[A-Z_]+_(R0\|R1)\b` | R-0/R-1 rotation pattern per ADR-ENV-NAMING-CONVENTION Decision 8 |

**Scope for all patterns**: `src/autom8_asana/api/errors.py`, `src/autom8_asana/api/main.py`, `src/autom8_asana/api/routes/webhooks.py`. Do NOT expand scope.

For each pattern, record match count and up to 5 sample `{file, line, text}` triples.

### 3.4 Step A.3 — Secretspec delta

```bash
# Check if commit modified secretspec.toml
git show 0474a60c -- secretspec.toml 2>/dev/null > /tmp/secretspec-at-commit.diff

# If empty: secretspec.toml was not modified by this commit — record verdict.
# If non-empty: diff pre/post for new [profiles.*] keys.
git show 0474a60c^:secretspec.toml > /tmp/secretspec-pre.toml 2>/dev/null
git show 0474a60c:secretspec.toml  > /tmp/secretspec-post.toml 2>/dev/null
diff /tmp/secretspec-pre.toml /tmp/secretspec-post.toml > /tmp/secretspec-delta.diff || true
```

Record: secretspec-modified-by-commit (bool); if true, list of new `[profiles.*]` keys.

### 3.5 Step A.4 — Service entry-point discovery

Grep patterns for FastAPI router / Lambda handler introductions:

| ID | Pattern | Purpose |
|----|---------|---------|
| SA1 | `router\.(get\|post\|put\|delete\|patch\|options)\s*\(` | FastAPI router method handlers |
| SA2 | `@app\.(get\|post\|put\|delete\|patch\|options)` | App decorator routes |
| SA3 | `APIRouter\s*\(` | APIRouter declarations |
| SA4 | `add_api_route\s*\(` | Programmatic route registration |
| SA5 | `def\s+lambda_handler\s*\(` | Lambda entry points |
| SA6 | `register_[a-z_]+\s*\(.*app.*\)` | Middleware/handler registrations (catches `register_validation_handler`, etc.) |

**Scope**: Same 3 touched src files. Also run `git show --stat 0474a60c` to confirm no NEW router files introduced by the commit.

### 3.6 Step A.5 — Secretspec.toml presence audit

```bash
# Check if secretspec.toml exists in repo at all
test -f /Users/tomtenuta/Code/a8/repos/autom8y-asana/secretspec.toml && echo "EXISTS" || echo "ABSENT"
```

Record: secretspec-exists-in-repo (bool). If absent AND commit did not introduce it, verdict row for secretspec is "n/a-by-absence".

### 3.7 Step A.6 — Output schema (normative)

Write to `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-env-surface-discovery-2026-04-21.md`. Frontmatter REQUIRED:

```yaml
---
title: "Sprint 5 Probe A — Env Surface Discovery (0474a60c)"
type: review
artifact_type: review
review_subtype: env-surface-probe
status: proposed
owner_rite: 10x-dev
owner_agent: principal-engineer
initiative: total-fleet-env-convergance
sprint: S16
workstream: WS-6
potnia_checkpoint: PT-16
target_commit: 0474a60c
target_commit_date: 2026-04-20T21:06+02:00
repo: autom8y-asana
consumes_tdd: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-sprint5-post-deploy-adversarial-2026-04-21.md
date: 2026-04-21
evidence_grade: "[MODERATE]"
---
```

Body schema (YAML-embedded in markdown, section `§probe-a-output-v1`):

```yaml
probe_a_output_v1:
  commit: 0474a60c
  files_swept:
    - src/autom8_asana/api/errors.py
    - src/autom8_asana/api/main.py
    - src/autom8_asana/api/routes/webhooks.py
  diff_byte_size: <INT>
  patterns_applied:
    PA1_os_environ:
      matches: <INT>
      samples: [{file: <PATH>, line: <INT>, text: <STRING>}, ...]
    PA2_settings_access: {matches: <INT>, samples: [...]}
    PA3_all_caps_identifiers: {matches: <INT>, samples: [...]}
    PA4_suffix_patterns: {matches: <INT>, samples: [...]}
    PA5_rotation_pattern: {matches: <INT>, samples: [...]}
    SA1_router_methods: {matches: <INT>, samples: [...]}
    SA2_app_decorators: {matches: <INT>, samples: [...]}
    SA3_apirouter_decl: {matches: <INT>, samples: [...]}
    SA4_add_api_route: {matches: <INT>, samples: [...]}
    SA5_lambda_handler: {matches: <INT>, samples: [...]}
    SA6_register_funcs: {matches: <INT>, samples: [...]}
  secretspec_modified_by_commit: <BOOL>
  secretspec_exists_in_repo: <BOOL>
  new_env_keys:
    # empty list OR entries per PRD FR-2:
    - name: <STRING>
      file: <PATH>
      line: <INT>
      purpose: <STRING>
      hermes_relevant: <BOOL>
  new_services:
    # empty list OR entries:
    - name: <STRING>
      entry_point: <PATH:LINE>
      secretspec_needed: <BOOL>
  verdict: EMPTY_SURFACE | NEW_ENV_KEYS | NEW_SERVICE | BOTH
  verdict_rationale: |
    <1-2 sentences citing pattern-match counts as evidence>
  hermes_relevance_assessment: |
    <evaluate whether any found env keys touch hermes loader surface;
     this feeds AP-G1 fire-condition in Phase 4 synthesis>
  out_of_scope_flags:
    # list any findings that belong to other rites (ecosystem, hygiene, SRE)
    - []
```

### 3.8 Step A.7 — Verdict resolution logic

- IF `new_env_keys == []` AND `new_services == []` AND `secretspec_modified_by_commit == false` → **EMPTY_SURFACE**
- IF `new_env_keys != []` AND `new_services == []` → **NEW_ENV_KEYS**
- IF `new_env_keys == []` AND `new_services != []` → **NEW_SERVICE**
- IF BOTH non-empty → **BOTH** (escalate per PRD edge-case row 4)

Match-filtering: register-pattern matches (e.g., `register_validation_handler`) that are CONFIGURATION calls on an existing app — NOT a new service entry point — are excluded from `new_services`. Commit message context: `register_validation_handler(app, service_code_prefix="ASANA")` is a handler registration on an existing app, not a new service. Principal-engineer applies judgment here; rationale recorded inline.

### 3.9 Step A.8 — STOP boundaries (Probe A)

- READ-ONLY: no edits to source files, no git branch creation, no commits
- Write EXACTLY ONE artifact path: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-env-surface-discovery-2026-04-21.md`
- Frontmatter fields per §3.7 above
- NO Bash destructive commands (no `rm -rf`, no git force flags, no `git push`)
- If ambiguity surfaces (e.g., a grep match that could be either env-read or config-access), ESCALATE to main-thread — do NOT invent classification.
- On completion, return structured status per PRD dispatch convention.

## §4 Probe B Specification — Error Envelope Adversarial (qa-adversary)

### 4.1 Dispatch summary

- **Specialist**: qa-adversary
- **Co-dispatch with**: Probe C (same specialist, same output artifact, single session)
- **Target commit**: `0474a60c`
- **Output artifact** (shared with Probe C): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-adversarial-probes-2026-04-21.md`
- **Wall-clock budget**: ≤ 30 minutes for B+C combined (per NFR-8)
- **Evidence grade**: `[MODERATE]` (authored within 10x-dev rite)

### 4.2 Pre-step B.0 — Endpoint discovery

qa-adversary reads `src/autom8_asana/api/main.py` to enumerate router mount points and endpoint paths. Expected surfaces (per commit message context):

- Webhook endpoint(s) emitting `ASANA-AUTH-002` (signature_invalid)
- Endpoint(s) emitting `ASANA-VAL-001` (422 service-prefixed validation)
- Endpoint(s) emitting `ASANA-DEP-002` (not_configured)
- Webhook ingress path per `src/autom8_asana/api/routes/webhooks.py`

Record in output artifact §B.0 `endpoints_discovered`:

```yaml
endpoints_discovered:
  - path: <STRING>
    method: <GET|POST|PUT|DELETE|PATCH|OPTIONS>
    wire_code_surface: [ASANA-AUTH-002 | ASANA-VAL-001 | ASANA-VAL-002 | ASANA-VAL-003 | ASANA-VAL-004 | ASANA-DEP-002 | NONE]
    auth_required: <BOOL>
    source_file_line: <PATH:LINE>
```

**Minimum endpoint coverage**: 1 webhook endpoint + 1 representative validation endpoint + 1 representative dependency-config endpoint = 3 endpoints. If fewer are discoverable, qa-adversary records which wire codes could not be reached and notes in `deferred_probes`.

### 4.3 Step B.1 — Adversarial request shape matrix

Six normative request shapes per PRD FR-5, each applied to each discovered endpoint:

| ID | Shape | Construction | Expected 4xx wire code |
|----|-------|--------------|------------------------|
| RS1 | Malformed JSON body | Body: `{"` (truncated) on JSON POST endpoint | ASANA-VAL-001 or similar 422 |
| RS2 | Oversized body | Body: 10 MB zero-fill (`"\x00" * 10_000_000`) | 413 or 400 envelope |
| RS3 | Unexpected content-type | Header `Content-Type: application/xml`; body: `<xml/>` on JSON endpoint | 415 or 422 envelope |
| RS4 | Missing auth | Omit required auth header (e.g., webhook signature) | ASANA-AUTH-002 |
| RS5 | Invalid JWT | `Authorization: Bearer eyJ.MALFORMED.SIG` | ASANA-AUTH-* or 401 |
| RS6 | SQL-injection-shaped params | Query: `?id=1%27%20OR%201=1--` (URL-encoded `1' OR 1=1--`) | 422 envelope; body MUST NOT reflect payload |

**Shape-endpoint applicability matrix**: Not every shape applies to every endpoint (e.g., RS4 only on auth-required endpoints; RS1 only on JSON-accepting endpoints). qa-adversary records applicability in output:

```yaml
applicability_matrix:
  - endpoint: <PATH>
    shapes_applicable: [RS1, RS2, ...]  # per endpoint type
    shapes_skipped: [RS_ID: rationale, ...]
```

### 4.4 Step B.2 — Invocation methodology

**Primary path (RECOMMENDED)**: Local `TestClient` via pytest harness. Reference pattern at `tests/integration/api/test_envelope_convergence.py` (existing in repo; WS-B1/B2 shipping tests). qa-adversary spins an ad-hoc scratch file at `/tmp/sprint5_probes_bc.py` (NOT in repo; NOT committed; NOT part of test suite) with a minimal `TestClient` harness:

```python
# /tmp/sprint5_probes_bc.py — scratch; ephemeral; not committed
from fastapi.testclient import TestClient
from autom8_asana.api.main import app  # reads POST-0474a60c code
client = TestClient(app)
# ... apply RS1-RS6 across discovered endpoints, capture responses ...
```

**Alternative path (DISCOURAGED)**: Extending `tests/integration/api/test_envelope_convergence.py` with adversarial cases. This writes to a TRACKED test file and introduces edit-scope ambiguity with the read-only invariant. Prefer the scratch path.

**Prohibited paths**:
- Production HTTP hosts (categorically)
- Live staging hosts if they mutate shared state
- In-repo test file modifications that would produce commits

### 4.5 Step B.3 — Assertion set (normative regex patterns)

For each (endpoint × shape) probe, capture the response and assert ALL of:

**Status code assertions**:
- Status code: 4xx (reject with structured error) — NOT 5xx EXCEPT if shape RS2 genuinely triggers 5xx via body-size-unhandled path (in which case 5xx IS the finding)

**Envelope shape assertions** (response body JSON):
- `error.code` matches `^ASANA-[A-Z]{3,4}-\d{3}$`
- `error.message` is non-empty string
- `meta.request_id` is non-empty string (UUID/ULID-shaped; regex `^[A-Za-z0-9\-_]{8,}$` minimum)
- `meta.timestamp` is non-empty ISO-8601 string (regex `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}`)

**Information-disclosure assertions** (response body MUST NOT contain):
- `Traceback` (Python stack trace marker)
- `File "/` (Python stack trace line marker)
- `/Users/` OR `/opt/` OR `/app/src/` OR `/home/` (absolute path markers)
- `site-packages` (virtualenv path marker)
- `\braise\s` (raise statement echo)
- Internal class names: `AsanaError`, `FleetError` (wire codes should replace internal type names)

**Reflection-disclosure assertion** (for RS6 specifically):
- Response body MUST NOT contain the literal injection substring `1' OR 1=1--` (URL-decoded) NOR the URL-encoded form `%27%20OR%201=1--`

**Security header assertions** (cross-reference Probe C):
- All 5 required headers present: `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Cache-Control`
- `Cache-Control` value contains `no-store`

### 4.6 Step B.4 — Output schema (normative)

Write to shared artifact `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-adversarial-probes-2026-04-21.md`, section `§probe-b-output-v1`:

```yaml
probe_b_output_v1:
  endpoints_discovered: [...]  # from B.0
  applicability_matrix: [...]  # from B.1
  probes:
    - endpoint: <PATH>
      method: <METHOD>
      shape: RS1 | RS2 | RS3 | RS4 | RS5 | RS6
      status_code: <INT>
      envelope_shape_pass: <BOOL>
      envelope_fields_observed:
        error_code: <STRING or null>
        error_message_nonempty: <BOOL>
        meta_request_id_nonempty: <BOOL>
        meta_timestamp_iso8601: <BOOL>
      stack_trace_leakage: <BOOL>  # MUST be false
      internal_path_leakage: <BOOL>  # MUST be false
      internal_class_leakage: <BOOL>  # MUST be false
      reflection_leakage: <BOOL>  # MUST be false (applies to RS6)
      security_headers_present:
        strict_transport_security: <BOOL>
        x_frame_options: <BOOL>
        x_content_type_options: <BOOL>
        referrer_policy: <BOOL>
        cache_control_no_store: <BOOL>
      verdict: PASS | FAIL
      fail_reason: <STRING or null>
  overall_verdict: PASS | FAIL
  bugs_to_file_for_principal_engineer:
    # empty IF overall_verdict = PASS, else:
    - title: <STRING>
      severity: BLOCKER | SHOULD-INVESTIGATE
      location: <PATH:LINE or ENDPOINT>
      description: <STRING>
      route_to: asana principal-engineer (out-of-S16-scope)
  deferred_probes:
    - endpoint_shape: <STRING>
      reason: <STRING>
```

### 4.7 Step B.5 — STOP boundaries (Probe B)

- LOCAL TestClient/pytest harness ONLY; categorically NO production endpoints
- NEVER live staging hosts that mutate shared state
- Scratch file at `/tmp/sprint5_probes_bc.py` — DO NOT commit; DO NOT persist beyond session
- DO NOT modify any tracked test file (preserves read-only invariant)
- Zero write mutations to test-harness data (probes assume 4xx — data state untouched)
- If BLOCKER findings (stack-trace leakage, reflection, missing envelope fields): FILE explicit bug entry in `bugs_to_file_for_principal_engineer`; do NOT attempt to fix (out of S16 scope per PRD §Out of Scope)
- If endpoint requires mutation to reach adversarial condition: record as `deferred_probes` with rationale; DO NOT invent mutation.
- Single shared output artifact only — NO other file writes, NO branches, NO commits.

## §5 Probe C Specification — Security Header Resilience (qa-adversary)

### 5.1 Dispatch summary

- **Specialist**: qa-adversary (co-dispatched with Probe B)
- **Target commit**: `0474a60c`
- **Output artifact** (shared with Probe B): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-adversarial-probes-2026-04-21.md`
- **Harness reuse**: Same `/tmp/sprint5_probes_bc.py` TestClient instance as Probe B
- **Evidence grade**: `[MODERATE]` (authored within 10x-dev rite)

### 5.2 Step C.1 — Pre-flight capture existence audit

```bash
test -d /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures && echo "CAPTURES_EXIST" || echo "CAPTURES_ABSENT"
ls /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/ 2>/dev/null
```

Record in output: `captures_available: <BOOL>`. Per PRD §Assumptions clause 3, ABSENT captures degrade Probe C to **self-capture-only** with explicit annotation; byte-identity cross-check becomes UNAVAILABLE (marked as such).

### 5.3 Step C.2 — Response-shape variant matrix

| # | Variant | Induction Method | N/A Path |
|---|---------|------------------|----------|
| V1 | 200 OK | GET on `/health` or `/` (if discoverable) | If none: annotate "no public GET-200 surface"; use first discoverable 200 response from any probe |
| V2 | 404 Not Found | GET on `/this-path-does-not-exist-probe-2026-04-21` | n/a |
| V3 | 500 Internal Server Error | Input that bypasses 4xx validation but triggers unhandled exception (exploratory) | If no triggerable 500 path exists: **PASS_BY_EXCEPTION** per PRD §Edge Cases row 10 |
| V4 | OPTIONS Preflight | OPTIONS on any CORS-enabled endpoint | If no CORS surface: annotate and treat as N/A |
| V5 | 3xx Redirect | GET on any known redirect path | If no redirect routes defined: **PASS_BY_ABSENCE** per PRD §Edge Cases row 11 |

### 5.4 Step C.3 — Header byte-identity assertions

For each variant response, capture full response headers. Assert the 5-header set:

| Header | Assertion |
|--------|-----------|
| `Strict-Transport-Security` | Present; value matches fleet-canonical max-age + `includeSubDomains`/`preload` as emitted by `autom8y_api_schemas.middleware` |
| `X-Frame-Options` | Present; value ∈ {`DENY`, `SAMEORIGIN`} |
| `X-Content-Type-Options` | Present; value EXACTLY `nosniff` |
| `Referrer-Policy` | Present; value matches fleet canonical (expected `strict-origin-when-cross-origin` per commit message; treat as byte-identity when captures available) |
| `Cache-Control` | Present; value contains substring `no-store` |

**Byte-identity cross-check (FR-8 SHOULD)**:
IF `captures_available == true`: diff response headers against peer captures at `.ledge/spikes/pt-03-captures/ads-headers.txt` and `.ledge/spikes/pt-03-captures/scheduling-headers.txt`; record per-header diff result.
IF `captures_available == false`: record `byte_identity_cross_check: UNAVAILABLE_CAPTURES_ABSENT`; FR-8 is a SHOULD not MUST, so this does NOT fail Probe C overall verdict.

### 5.5 Step C.4 — Output schema (normative)

Append to shared artifact, section `§probe-c-output-v1`:

```yaml
probe_c_output_v1:
  captures_available: <BOOL>
  captures_checked:
    self: <PATH or null>
    ads: <PATH or null>
    scheduling: <PATH or null>
  variants_probed:
    - variant: V1 | V2 | V3 | V4 | V5
      induction_method: <STRING>
      induction_successful: <BOOL>
      status_code: <INT or null>
      headers_captured:
        strict_transport_security: <STRING or null>
        x_frame_options: <STRING or null>
        x_content_type_options: <STRING or null>
        referrer_policy: <STRING or null>
        cache_control: <STRING or null>
      header_set_complete: <BOOL>  # all 5 present
      byte_identity_match:
        ads: <BOOL | UNAVAILABLE>
        scheduling: <BOOL | UNAVAILABLE>
      verdict: PASS | FAIL | PASS_BY_EXCEPTION | PASS_BY_ABSENCE
      fail_reason: <STRING or null>
  overall_verdict: PASS | FAIL
  bugs_to_file_for_principal_engineer:
    - title: <STRING>
      severity: BLOCKER | SHOULD-INVESTIGATE
      location: <ENDPOINT or MIDDLEWARE>
      description: <STRING>
      route_to: asana principal-engineer (out-of-S16-scope)
```

### 5.6 Step C.5 — STOP boundaries (Probe C)

Identical to Probe B §4.7. Additionally:

- If V3 (500) induction fails across all exploratory inputs: accept `PASS_BY_EXCEPTION` per PRD; do NOT construct mutations to force 500
- If V5 (3xx) has no redirect route in the app: accept `PASS_BY_ABSENCE` per PRD; do NOT invent redirect paths
- If HSTS max-age differs from peer byte-identity: escalate to main-thread per PRD §Edge Cases row 13 (intentional platform evolution vs. regression)
- No other file writes; share output artifact with Probe B.

## §6 Parallelization + Contention Analysis

### 6.1 Dispatch topology (Phase 3)

Main-thread dispatches in parallel:

```
Phase 3 start
  ├── Task(principal-engineer, Probe A spec §3)
  │    └── writes: sprint5-env-surface-discovery-2026-04-21.md
  └── Task(qa-adversary, Probes B+C spec §4+§5)
       └── writes: sprint5-adversarial-probes-2026-04-21.md
Phase 3 end → main-thread synthesis (Phase 4)
```

### 6.2 Shared-resource analysis

| Resource | Probe A | Probe B+C | Contention class |
|----------|---------|-----------|------------------|
| Git working tree (read) | reads commit `0474a60c` + 3 src files | reads `main.py` for endpoint enumeration | NONE (concurrent reads) |
| `/tmp/` scratch files | writes `0474a60c-diff.txt`, `secretspec-*.toml` | writes `sprint5_probes_bc.py` | NONE (disjoint filenames) |
| Localhost HTTP port | NOT BOUND | binds via TestClient (in-process, ephemeral) | NONE (Probe A does not touch HTTP) |
| Python interpreter | principal-engineer subprocess | qa-adversary subprocess | NONE (process isolation) |
| Output artifacts | `sprint5-env-surface-discovery-*.md` | `sprint5-adversarial-probes-*.md` | NONE (disjoint paths) |
| Source file `main.py` | READ only | READ only | NONE (concurrent reads safe) |

### 6.3 Decision: Probes B+C co-located in single qa-adversary dispatch

Rationale:
- Both share the same `TestClient(app)` instance → double-spinning avoids no value
- Both share output artifact → single authoring pass more coherent
- Probe C header assertions overlap Probe B assertion set — combining reduces redundant captures
- Keeps qa-adversary wall-clock budget ≤ 30 min for B+C combined (NFR-8)

### 6.4 Verdict

**PARALLEL DISPATCH SAFE**. No shared mutable state. No artifact collisions. Python process isolation guarantees no in-process contention. Main-thread synthesis (Phase 4) consumes both artifacts after both dispatches return.

## §7 Acceptance Criteria (PT-16 Synthesis Inputs)

TDD is PT-16-preparable (ready to dispatch Phase 3) when all 3 probe specs satisfy:

| Criterion | Probe A | Probe B | Probe C |
|-----------|---------|---------|---------|
| Concrete methodology (no hand-waving) | YES (5 grep patterns + 6 service patterns enumerated) | YES (6 request shapes + explicit construction) | YES (5 response variants + 5-header assertion set) |
| Normative output schema (machine-evaluable) | YES (§3.7 YAML schema) | YES (§4.6 YAML schema) | YES (§5.5 YAML schema) |
| STOP boundaries cited | YES (§3.9) | YES (§4.7) | YES (§5.6) |
| Scope translated verbatim from PRD | YES | YES | YES |
| Zero scope expansion | YES | YES | YES |
| Output artifact path explicit | `sprint5-env-surface-discovery-2026-04-21.md` | `sprint5-adversarial-probes-2026-04-21.md` | (shared with B) |
| Evidence grade declared | MODERATE | MODERATE | MODERATE |

**Phase 4 synthesis inputs** (main-thread synthesizes the AUDIT artifact from):
1. `sprint5-env-surface-discovery-2026-04-21.md` (Probe A output) → feeds `§env-surface-delta` verdict
2. `sprint5-adversarial-probes-2026-04-21.md` §probe-b-output-v1 → feeds `§probe-b-envelope-adversarial`
3. `sprint5-adversarial-probes-2026-04-21.md` §probe-c-output-v1 → feeds `§probe-c-header-resilience`
4. Main-thread composes PT-16 verdict + optional H6/H7 HANDOFFs per PRD FR-3/FR-4

## §8 STOP Boundaries (TDD Authoring Phase — Architect's Scope)

### 8.1 What Architect MAY do
- Read the PRD + shape spec + fleet coordination dashboard + PT-03 capture locations
- Author this TDD at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-sprint5-post-deploy-adversarial-2026-04-21.md`
- Surface ambiguities for main-thread escalation (e.g., PT-03 captures absence noted §2.4)

### 8.2 What Architect MAY NOT do
- Execute ANY probe (Phase 3 work, not Phase 2)
- Modify or extend PRD scope (LOCKED)
- Author the probe output artifacts themselves (Probe A/B/C artifacts are Phase 3; AUDIT is Phase 4)
- Edit the fleet coordination dashboard (main-thread Phase 4 authority)
- Touch any code, branch, commit, push, or knossos artifact
- Dispatch specialists (main-thread authority)
- Make decisions reserved for other rites (ecosystem secretspec edits, hygiene test debt, SRE canary contracts)

### 8.3 TDD scope-lock attestation

The probe specs in §3-§5 translate PRD §Probe Matrix methodology into concrete dispatch instructions. No PRD-implied scope has been added, removed, or renegotiated:

| PRD element | TDD translation |
|-------------|-----------------|
| PRD §Probe Matrix Probe A | TDD §3 (expanded patterns but same sweep scope) |
| PRD §Probe Matrix Probe B | TDD §4 (expanded regex assertions but same 6 shapes) |
| PRD §Probe Matrix Probe C | TDD §5 (expanded capture-absence handling but same 5 variants) |
| PRD §Edge Cases | TDD honors all 14 edge cases verbatim |
| PRD §STOP Boundaries | TDD STOP per-probe subsections re-cite PRD boundaries |
| PRD §Out of Scope | TDD §8.2 re-cites architect exclusions; probe specs re-cite specialist exclusions |

## §9 Links

- **PRD (source)**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-sprint5-post-deploy-adversarial-2026-04-21.md`
- **Shape S16 spec**: `/Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.shape.md` (lines 583-608)
- **Fleet coordination dashboard**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md`
- **Predecessor retrospective**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/RETROSPECTIVE-env-secret-platformization-closeout-2026-04-21.md` (§6 R9/R10)
- **Target commit**: `0474a60c` on autom8y-asana main (2026-04-20T21:06 CEST)
- **PT-03 captures (referenced; absence noted §2.4)**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/`
- **Phase 3 output artifacts**:
  - Probe A: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-env-surface-discovery-2026-04-21.md`
  - Probes B+C: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-adversarial-probes-2026-04-21.md`
- **Phase 4 synthesis artifact (main-thread)**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-sprint5-post-deploy-adversarial-2026-04-21.md`
- **Target repo**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/`
