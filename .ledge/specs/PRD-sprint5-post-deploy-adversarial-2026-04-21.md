---
title: "PRD — Sprint 5 Post-Deploy Adversarial (S16, WS-6)"
type: prd
artifact_type: prd
status: draft
phase_state: DRAFT_FOR_ARCHITECT_PHASE_2
owner_rite: 10x-dev
owner_agent: requirements-analyst
initiative: total-fleet-env-convergance
shape_ref: /Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.shape.md
frame_ref: /Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.md
fleet_coordination_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md
retrospective_ref: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/RETROSPECTIVE-env-secret-platformization-closeout-2026-04-21.md
sprint: S16
workstream: WS-6
potnia_checkpoint: PT-16
target_commit: 0474a60c
target_commit_message: "feat(asana): WS-B1+B2 canonical error envelope + security headers convergence"
target_commit_date: 2026-04-20T21:06+02:00
repo: autom8y-asana
scope_type: ORTHOGONAL
cc_session_requirement: cc-restart-required
date: 2026-04-21
impact: high
impact_categories: [security, api_contract, cross_service]
evidence_grade: "[MODERATE]"
evidence_grade_rationale: "Authored within 10x-dev rite (self-ref cap); upgrades to STRONG on cross-rite HANDOFF-RESPONSE landings if H6/H7 emit."
scope_lock: true
---

# PRD: Sprint 5 Post-Deploy Adversarial — WS-B1/B2 Convergence Probing (S16)

## Overview

Adversarially probe the WS-B1 canonical error envelope and WS-B2 security headers surface landed in commit `0474a60c` on autom8y-asana main (2026-04-20T21:06 CEST). Produce a Sprint 5 closure audit that (a) confirms zero-or-enumerated **new env surface** introduced by the commit — the S16 shape's hard acceptance criterion — and (b) verifies envelope + header resilience under adversarial request/response shapes without stack-trace leakage, internal-path disclosure, or missing-header findings.

This is an ORTHOGONAL sprint per S16 shape spec (lines 583-608): its scope is owned by the 10x-dev rite and executes in a separate CC session; its output feeds AP-G1 (S9 hermes-key re-ratification guard) and is a HARD-GATE dependency for S12 via AP-G4.

## Impact Assessment

**impact**: high
**impact_categories**: [security, api_contract, cross_service]

### Impact Determination Rationale

This PRD flags **high impact** because:

- **security**: Probe B (error envelope adversarial) and Probe C (security header resilience) directly interrogate security-sensitive code paths — stack-trace leakage, information disclosure, HSTS/XFO/CSP-header integrity, webhook signature validation (ASANA-AUTH-002). Any finding routes through security-sensitive remediation.
- **api_contract**: The WS-B1 canonical envelope (`{error: {...}, meta: {...}}`) is a cross-fleet API contract surface — byte-identical to ads and scheduling per PT-03 captures at `.ledge/spikes/pt-03-captures/`. Any envelope-shape regression or asymmetry IS a contract break.
- **cross_service**: The probe outputs feed two potential cross-rite HANDOFFs: H6 (to ecosystem rite via eco006-inventory update if NEW_ENV_KEYS) and H7 (to val01b via replan003-update if NEW_SERVICE). S16 shape's AP-G1 guard explicitly couples this sprint's verdict to S9's hermes-key ratification state.

### What This PRD Does NOT Change

This PRD is a **read-only adversarial probing specification**. It authorizes probe execution against a landed commit — it does **not** authorize modification of `0474a60c`'s code surface, branch creation, commit emission, or production endpoint access. All probes are local/staging-only, working-tree-only, zero-commit.

## Background

### Fleet Context

The `total-fleet-env-convergance` initiative (see shape §1-§11) is coordinating env/secret platformization across autom8y-asana, autom8y-scheduling, autom8y-ads, autom8y-data, and autom8y-mcp with a hermes-key ratification gate (S9) that is sensitive to the post-deploy state of satellite services. The S16 shape spec (lines 583-608) specifies:

- **Acceptance**: "Sprint 5 closed per 10x-dev rite definition" + "new env surface checklist item completed (may be empty; must be explicit)" + "HANDOFFs filed if non-empty"
- **Potnia checkpoint PT-16**: "Sprint 5 closed? env surface delta confirmed?"
- **AP-G1 guard**: "if S16 closes AFTER S9 AND surfaces hermes-relevant env keys, S9 must re-ratify"
- **Dependency chain**: "depends on S0; HARD-GATE to S12 (AP-G4)"
- **Throughline binding**: None (orthogonal)
- **Evidence grade**: `[MODERATE]` (scope owned by different rite)

### Target Commit

**Commit**: `0474a60c` on autom8y-asana main
**Message**: "feat(asana): WS-B1+B2 canonical error envelope + security headers convergence"
**Date**: 2026-04-20T21:06 CEST
**Version bump**: autom8y-asana 1.1.0 → 1.2.0
**Test state on ship**: 1442 passed (tests/unit/api + tests/integration/api + tests/unit/lifecycle)

### Files Touched by 0474a60c

- `src/autom8_asana/api/errors.py` — canonical error vocabulary + 5 typed FleetError subclasses:
  - `ASANA-AUTH-002` (signature_invalid)
  - `ASANA-DEP-002` (not_configured)
  - `ASANA-VAL-001/002/003/004` (validation errors)
- `src/autom8_asana/api/main.py` — SecurityHeadersMiddleware install + `fleet_error_handler` registration + service-prefixed validation handler
- `src/autom8_asana/api/routes/webhooks.py` — webhook ingress FleetError migration off HTTPException/`raise_api_error`
- `tests/integration/api/test_envelope_convergence.py` + `tests/unit/api/routes/test_webhooks.py` + `tests/unit/api/test_error_helpers.py` + `tests/unit/api/test_tasks.py`
- `pyproject.toml` (autom8y-api-schemas 1.6.0→1.9.0; editable path source)
- `CHANGELOG.md` + `uv.lock`

### Shipped Artifacts (reference for Probe C byte-identity diffing)

- Canonical envelope: `{error: {code, message, retryable, retry_after_seconds}, meta: {request_id, timestamp}}`
- 5-header security set: HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Cache-Control: no-store — byte-identical to ads and scheduling
- PT-03 captures: `.ledge/spikes/pt-03-captures/asana-envelope.json`, `asana-headers.txt`, `asana-webhook-envelope.json` (plus peer captures from ads and scheduling for diff baselines)

### Predecessor Retrospective Bindings

Per retrospective `RETROSPECTIVE-env-secret-platformization-closeout-2026-04-21.md` §6:
- **R9**: S16 must confirm explicit "new env surface" checklist state — empty OR enumerated. Silence is not acceptable.
- **R10**: S16 is ORTHOGONAL — its post-deploy adversarial scope must not conflate with other satellite sprints' env work; feed results back via HANDOFF if and only if non-empty.

## User Stories

- As the **fleet-potnia coordinator**, I want explicit confirmation of whether commit `0474a60c` introduces new env-var consumers or new service entry points, so that AP-G1 (S9 re-ratification) and AP-G4 (S12 HARD-GATE) guards can evaluate deterministically.
- As the **10x-dev rite closure audit authority**, I want adversarial probe results on the WS-B1 envelope and WS-B2 headers, so that Sprint 5 can close with evidence of security-sensitive code path resilience rather than code-coverage-only sign-off.
- As the **ecosystem rite receiver** (in the event H6 emits), I want a cross-rite HANDOFF artifact enumerating any new env keys with hermes-relevance flag, so that eco006-inventory updates can proceed deterministically.
- As the **val01b rite receiver** (in the event H7 emits), I want a cross-rite HANDOFF artifact enumerating any new service entry point with secretspec-needed flag, so that replan003-update can proceed deterministically.
- As the **asana principal-engineer**, I want any information-disclosure or missing-header findings filed as explicit bugs (out-of-S16-scope), so that follow-up remediation has unambiguous starting artifacts.

## Functional Requirements

### Must Have

#### FR-1: Sprint 5 Closure Audit Artifact Exists

The artifact `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-sprint5-post-deploy-adversarial-2026-04-21.md` MUST exist at Phase 4 (main-thread synthesis) close, containing all 4 probe outputs synthesized.

**Fit criterion**: File exists at path; contains sections `§env-surface-delta`, `§probe-a-env-surface-discovery`, `§probe-b-envelope-adversarial`, `§probe-c-header-resilience`, `§pt-16-verdict`.

#### FR-2: §env-surface-delta Checklist EXPLICIT

The AUDIT artifact's `§env-surface-delta` section MUST resolve to exactly one of these four values:

1. **EMPTY_SURFACE** — no new env keys AND no new service entry points
   - Inline rationale MUST cite Probe A methodology
   - Inline rationale MUST include exact grep patterns used
   - Inline rationale MUST list exact file paths swept
2. **NEW_ENV_KEYS** — new env keys enumerated
   - Each entry: `{name, file:line, purpose, hermes-relevant: bool}`
3. **NEW_SERVICE** — new service entry points enumerated
   - Each entry: `{name, entry-point file, secretspec-needed: bool}`
4. **BOTH** — compound; both lists populated

**Fit criterion**: Grep `§env-surface-delta` in AUDIT artifact; verdict token matches one of the four; enumeration schema populated if non-empty.

#### FR-3: H6 Emitted IFF NEW_ENV_KEYS

A cross-rite HANDOFF artifact `HANDOFF-sprint5-adversarial-to-ecosystem-eco006-inventory-2026-04-21.md` MUST be authored if and only if `§env-surface-delta` includes `NEW_ENV_KEYS`.

**Fit criterion**: If verdict ∈ {NEW_ENV_KEYS, BOTH}, HANDOFF artifact exists at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/handoffs/` (or fleet equivalent), schema-compliant with `cross-rite-handoff` skill, receiving_rite=ecosystem. If verdict ∈ {EMPTY_SURFACE, NEW_SERVICE}, this artifact MUST NOT exist.

#### FR-4: H7 Emitted IFF NEW_SERVICE (WITH OPERATOR PRE-RATIFICATION)

A cross-rite HANDOFF artifact `HANDOFF-sprint5-adversarial-to-val01b-replan003-update-2026-04-21.md` MUST be authored if and only if `§env-surface-delta` includes `NEW_SERVICE` **AND** operator pre-ratifies emission (because H7 would reopen the closed R9 REPLAN-003 decision per retrospective §6).

**Fit criterion**: If verdict ∈ {NEW_SERVICE, BOTH}, Phase 4 synthesis thread MUST escalate to user with message "S16 Probe A detected NEW_SERVICE; H7 emission would reopen R9 REPLAN-003 — pre-ratify?" BEFORE artifact authoring. If verdict ∈ {EMPTY_SURFACE, NEW_ENV_KEYS}, this artifact MUST NOT exist.

#### FR-5: Probe B Envelope Resilience Verdicts

Probe B (qa-adversary, Phase 3) MUST produce: 6 adversarial request shapes × N endpoints; a PASS/FAIL verdict per shape on envelope-shape assertion; zero information-disclosure findings OR an explicit bug filed.

**Fit criterion**: AUDIT artifact §probe-b-envelope-adversarial contains a table with columns `{endpoint, adversarial-shape, status-code, envelope-match, info-disclosure, verdict}`; at least 6 adversarial shapes × at least 1 endpoint = 6 rows minimum; zero FAIL rows OR explicit bug reference (file path + bug title) in §probe-b-findings.

#### FR-6: Probe C Header Resilience Verdicts

Probe C (qa-adversary, Phase 3) MUST produce: 5 response-shape variants; a PASS/FAIL verdict per variant for each of 5 required headers; zero missing-header findings OR an explicit bug filed.

**Fit criterion**: AUDIT artifact §probe-c-header-resilience contains a matrix with rows = {200, 404, 500, OPTIONS, 3xx-redirect} and columns = {HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Cache-Control}; each cell is PASS (byte-identical to baseline capture) or FAIL (with captured value); zero FAIL cells OR explicit bug reference in §probe-c-findings.

#### FR-7: Zero Production Mutations; Zero Commits; Zero Cross-Rite Scope-Creep

All S16 probing MUST be local/staging-only, working-tree-only, and scope-bounded to WS-B1/B2 surface.

**Fit criterion**: `git -C /Users/tomtenuta/Code/a8/repos/autom8y-asana log --oneline 0474a60c..HEAD` at Phase 4 close MUST show zero new commits authored by this sprint's specialists. No HTTP requests against production hostnames in probe traces. Any out-of-scope finding (ecosystem, hygiene, SRE rite surface) is flagged in AUDIT §out-of-scope-flags, NOT executed.

### Should Have

#### FR-8: Baseline Byte-Identity Diff Against Peer Captures

Probe C SHOULD diff asana response headers against ads and scheduling captures at `.ledge/spikes/pt-03-captures/{ads,scheduling}-headers.txt` to confirm fleet-wide byte-identity.

**Fit criterion**: AUDIT §probe-c-header-resilience includes a §byte-identity-cross-check subsection reporting diff results for each of 5 headers against at least one peer (ads or scheduling) capture.

#### FR-9: AP-G1 State Recording in Dashboard

Main-thread synthesis (Phase 4) SHOULD update `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md` §4 AP register with AP-G1 state (FIRED if NEW_ENV_KEYS includes hermes-relevant OR NOT-FIRED otherwise) and §8 Update Log with S16 closure entry.

**Fit criterion**: Dashboard §4 contains AP-G1 row with state ∈ {FIRED, NOT-FIRED} and timestamp 2026-04-21; §8 Update Log contains entry "S16 CLOSED — PT-16 PASS — [EMPTY|NON-EMPTY]".

### Could Have

#### FR-10: Probe B Extension to Rate-Limit Shapes

Probe B COULD extend adversarial request shapes to include rate-limit boundary conditions (e.g., burst-429 responses). Deferred unless baseline 6 shapes surface a pattern suggesting rate-limit-specific regression.

## Non-Functional Requirements

- **NFR-1 (Security)**: Zero stack-trace content in any 4xx/5xx response body across all 6 adversarial Probe B shapes.
- **NFR-2 (Security)**: Zero internal file-path disclosure (e.g., `/Users/`, `/opt/`, `/app/src/`) in any response body across all 6 adversarial Probe B shapes.
- **NFR-3 (Security)**: Zero SQL query fragment echo in response body for Probe B shape #6 (SQL-injection-shaped query params).
- **NFR-4 (API contract)**: `meta.request_id` non-empty on every Probe B response; `meta.timestamp` ISO-8601 format.
- **NFR-5 (API contract)**: `error.code` matches pattern `^ASANA-[A-Z]+-\d{3}$` on every Probe B response.
- **NFR-6 (Security)**: All 5 security headers present on every Probe C response variant (including 500 and OPTIONS).
- **NFR-7 (API contract)**: HSTS header value byte-identical to ads and scheduling peer captures (max-age value and includeSubDomains/preload flags).
- **NFR-8 (Operational)**: Phase 3 total wall-clock ≤ 45 minutes (principal-engineer Probe A: ≤15 min; qa-adversary Probes B+C: ≤30 min combined).
- **NFR-9 (Operational)**: Phase 4 synthesis ≤ 20 minutes (main-thread AUDIT authoring).
- **NFR-10 (Auditability)**: Every probe output artifact frontmatter cites target commit `0474a60c` and target commit date `2026-04-20T21:06+02:00`.

## Probe Matrix

### Probe A — env-surface-discovery (principal-engineer, Phase 3)

**Hypothesis**: Commit `0474a60c` introduces zero new env-var consumers. WS-B1 is a code-path reorg (error envelope conformance); WS-B2 is middleware wiring (SecurityHeadersMiddleware install). Neither pattern typically introduces env reads.

**Methodology**:

1. Diff the commit:
   ```
   git -C /Users/tomtenuta/Code/a8/repos/autom8y-asana diff 0474a60c^..0474a60c -- 'src/**' 'pyproject.toml' 'secretspec.toml' '.env/**'
   ```
2. Within the diff, grep for env-access patterns:
   - Python: `os\.environ|os\.getenv|settings\.[a-z_]+|\bSettings\(\)|Config\.|AUTOM8Y_|SERVICE_|_API_KEY|_TOKEN|_URL|AWS_|SLACK_`
   - `secretspec.toml`: diff pre/post for new `[profiles.*]` keys
   - `pyproject.toml`: check for any env-var default in `[tool.*]` sections
3. Grep the 3 touched source files (`errors.py`, `main.py`, `webhooks.py`) for FastAPI router / Lambda handler introductions:
   - Pattern: `router\.(get|post|put|delete|patch|options)|@app\.(get|post|put|delete|patch|options)|APIRouter|add_api_route|def lambda_handler|register_`
4. Resolve to output schema:
   ```yaml
   new_env_keys: list[{name, file, line, purpose, hermes_relevant: bool}]
   new_services: list[{name, entry_point, secretspec_needed: bool}]
   verdict: EMPTY_SURFACE | NEW_ENV_KEYS | NEW_SERVICE | BOTH
   ```

**STOP boundaries**:
- Read-only sweep; NO code touch; NO branch; NO commit
- Single artifact written: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-env-surface-discovery-2026-04-21.md`

**Evidence grade**: `[MODERATE]` (authored within 10x-dev rite)

---

### Probe B — error envelope adversarial (qa-adversary, Phase 3)

**Hypothesis**: The FleetError catch-all registered at WS-B1 (`fleet_error_handler` in `main.py`) produces the canonical `{error: {...}, meta: {...}}` envelope under adversarial request shapes without stack-trace leakage or internal-path exposure.

**Methodology — 6 adversarial request shapes per endpoint**:

| # | Shape | Example |
|---|-------|---------|
| 1 | Malformed JSON body | `{"` truncated |
| 2 | Oversized body | 10 MB payload |
| 3 | Unexpected content-type | `application/xml` on JSON endpoint |
| 4 | Missing auth header | Unsigned webhook request |
| 5 | Invalid JWT | Malformed signature |
| 6 | SQL-injection-shaped query params | `?id=1' OR 1=1--` |

**Endpoint set**: Webhook endpoint + representative ASANA-VAL-001 endpoint + representative ASANA-DEP-002 endpoint. Exact paths determined at Phase 3 by reading `src/autom8_asana/api/main.py` router registrations.

**Assertions per probe**:
- Response status is 4xx (never 5xx; exception is shape #6 if it genuinely produces 5xx via an unhandled path, which itself is a finding)
- Envelope has: `error.code` matches `^ASANA-[A-Z]+-\d{3}$`, `error.message` non-empty, `meta.request_id` non-empty, `meta.timestamp` ISO-8601
- **No** stack trace in response body (regex: `Traceback|File "/|  at .+\.py:`)
- **No** internal file path in response body (regex: `/Users/|/opt/|/app/src/|/home/`)
- **No** SQL query fragment echo in response body for shape #6 (regex matching the injected payload substring)
- All 5 security headers present on every response (cross-reference Probe C assertions)

**STOP boundaries**:
- Local / staging HTTP endpoints only — determined at Phase 3 by env config. NEVER production.
- Read-only probes; zero write mutations.
- If an endpoint requires mutation to probe (e.g., POST-only endpoint with state side-effects), Phase 3 MUST request clarification — do NOT invent mutations.
- Single shared artifact written: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/sprint5-adversarial-probes-2026-04-21.md` (shared with Probe C).

**Evidence grade**: `[MODERATE]` (authored within 10x-dev rite)

---

### Probe C — security header resilience (qa-adversary, Phase 3)

**Hypothesis**: The 5-header security set (WS-B2 SecurityHeadersMiddleware) holds byte-identical across 5 response-shape variants.

**Methodology — 5 response-shape variants × 5 required headers = 25-cell matrix**:

| # | Response shape | Trigger |
|---|----------------|---------|
| 1 | Normal 200 | Representative GET endpoint |
| 2 | 404 | Unknown path |
| 3 | 500 | Force internal error (via invalid input; if no such path, document as N/A-exception with rationale) |
| 4 | OPTIONS preflight | CORS path |
| 5 | 3xx redirect | Any redirect route (if none exists, document as N/A-by-absence with rationale) |

**Required headers** (each must be present and byte-identical to baseline per variant):

- **HSTS** (`Strict-Transport-Security`): match peer capture at `.ledge/spikes/pt-03-captures/ads-headers.txt` and `.ledge/spikes/pt-03-captures/scheduling-headers.txt`
- **X-Frame-Options**: DENY or SAMEORIGIN (byte-identical to peer)
- **X-Content-Type-Options**: `nosniff`
- **Referrer-Policy**: `strict-origin-when-cross-origin` (or byte-identical to peer)
- **Cache-Control**: `no-store`

**Baseline diff references**:
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/asana-headers.txt` (self-reference)
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/ads-headers.txt` (peer; expected byte-identical)
- `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/scheduling-headers.txt` (peer; expected byte-identical)

**STOP boundaries**: Same as Probe B — local/staging only, read-only, single shared artifact.

**Evidence grade**: `[MODERATE]` (authored within 10x-dev rite)

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Probe A grep returns zero matches AND secretspec.toml unchanged AND no new router registrations | Verdict: EMPTY_SURFACE with inline rationale citing methodology + patterns + files swept |
| Probe A finds a new env-var reference that's a rename of an existing one (e.g., `SLACK_TOKEN` → `SLACK_BOT_TOKEN`) | Enumerate as NEW_ENV_KEYS with `purpose: rename-of-<old-name>`; flag for ecosystem rite confirmation |
| Probe A finds a new env key that is clearly NOT hermes-relevant (e.g., a log-level flag) | Enumerate with `hermes_relevant: false`; H6 still emits but ecosystem receiver deprioritizes |
| Probe A finds both NEW_ENV_KEYS AND NEW_SERVICE (verdict BOTH) | Phase 4 MUST escalate to user BEFORE H6/H7 emission (compound scope; requires operator scope-lock confirmation) |
| Probe B endpoint requires mutation to reach adversarial condition | Phase 3 requests clarification from main-thread; does NOT invent mutation; documents as DEFERRED_PROBE |
| Probe B shape #6 (SQL injection) returns 200 with empty result (no leakage) | PASS; but flag `§probe-b-findings` subsection with "SQL-shape reached handler layer — investigate parameterization depth" as SHOULD-investigate (not BLOCKER) |
| Probe B returns 5xx on shape #1 (malformed JSON) with stack trace | FAIL → BLOCKER; file explicit bug; route back to asana principal-engineer (out of S16 scope) |
| Probe B returns 4xx envelope missing `meta.request_id` | FAIL → BLOCKER; file explicit bug |
| Probe C 500-response-shape variant cannot be triggered (no path to invalid-input-induced 500) | Document as N/A-exception; annotate with "no-triggerable-500-path in public surface"; verdict PASS-BY-EXCEPTION |
| Probe C 3xx-redirect-response-shape variant has no redirect routes | Document as N/A-by-absence; verdict PASS-BY-ABSENCE |
| Probe C header missing on one variant, present on others | FAIL → BLOCKER; file explicit bug; route back to asana principal-engineer |
| Probe C HSTS max-age differs from peer byte-identity | FAIL (or SHOULD-investigate if diff is intentional platform policy evolution) → escalate to user |
| Staging endpoint unreachable (no local server, no staging access) | Phase 3 escalates to user for environment dispatch; S16 transitions to ESCALATED_env_unavailable |
| Probe surfaces ecosystem-rite or hygiene-rite or SRE-rite work | FLAG in AUDIT §out-of-scope-flags; do NOT execute; defer to appropriate rite intake |
| Operator rejects H7 pre-ratification | AUDIT annotates "NEW_SERVICE detected; H7 emission declined by operator; S16 closes with flagged-non-emission; val01b intake deferred" |

## Success Criteria (PT-16 Gate)

### PASS Conditions (all required)

- [ ] AUDIT-sprint5 artifact exists at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/AUDIT-sprint5-post-deploy-adversarial-2026-04-21.md`
- [ ] AUDIT §env-surface-delta resolves to exactly one of {EMPTY_SURFACE, NEW_ENV_KEYS, NEW_SERVICE, BOTH} with explicit schema-compliant enumeration if non-empty
- [ ] H6 HANDOFF filed iff §env-surface-delta ∈ {NEW_ENV_KEYS, BOTH} (schema-compliant with `cross-rite-handoff` skill)
- [ ] H7 HANDOFF filed iff §env-surface-delta ∈ {NEW_SERVICE, BOTH} AND operator pre-ratification recorded
- [ ] AUDIT §probe-b-envelope-adversarial: zero information-disclosure findings OR explicit bug filed with file path + title
- [ ] AUDIT §probe-c-header-resilience: zero missing-header findings OR explicit bug filed with file path + title
- [ ] AP-G1 state recorded (FIRED | NOT-FIRED) in FLEET-COORDINATION dashboard §4
- [ ] AP-G4 gate signal: FLEET-COORDINATION dashboard §8 Update Log contains entry "S16 CLOSED — PT-16 PASS — [EMPTY|NON-EMPTY]"
- [ ] Zero new commits authored in autom8y-asana by S16 specialists (verified via git log)

### BLOCKER Conditions (escalate to user, do NOT self-close)

- [ ] Probe B discovers information disclosure → BLOCK; file bug; route back to asana principal-engineer follow-up (bug tracking is out-of-S16-scope)
- [ ] Probe C discovers missing security headers on significant response shapes (200, 404, 500, or OPTIONS) → BLOCK; file bug
- [ ] Probe A verdict BOTH (compound scope) → escalate BEFORE emission for operator scope-lock confirmation
- [ ] Probe B endpoint not accessible (staging gate closed / no local server available) → escalate for dispatch environment

### Rollback Path

All probe artifacts are working-tree-only. Operator rejects S16 closure via non-commit. FLEET-COORDINATION dashboard row S16 flips NOT_STARTED → ESCALATED_{reason}. No in-repo state change requires inverse migration.

## Out of Scope

The following items are **explicitly excluded** from S16 Phase 3/4 execution. Any finding in these domains MUST be flagged in AUDIT §out-of-scope-flags and deferred to the appropriate rite intake — NOT executed by S16 specialists.

- **Auth subsystems beyond webhook ASANA-AUTH-002 envelope probing**: e.g., OAuth flows, JWT rotation, session management — route to security rite
- **Data layer**: database schema, migrations, cache layer, DuckDB / RDS inspection — route to data rite or ecosystem
- **Production endpoints**: all probes are local/staging-only; production mutation is CATEGORICALLY PROHIBITED
- **Branch creation, commits, pushes**: S16 is working-tree-only; operator commits at sprint close IF any
- **Knossos edits**: `.claude/skills/`, `.claude/agents/`, throughline registry — S17-gated ratification
- **Ecosystem-rite work**: secretspec.toml edits, hermes-key registrations, eco006-inventory direct updates — emit H6 HANDOFF; do NOT execute
- **Hygiene-rite work**: test debt, fixture cleanup, CI workflow changes — flag; defer
- **SRE-rite work**: canary contracts, SLO definitions, incident runbooks, IaC changes — flag; defer
- **Files outside WS-B1/B2 touched set**: unless co-located for probe methodology (e.g., reading other files in `src/autom8_asana/api/` to determine router paths is permitted for Probe A methodology)
- **PRD scope modification by Phase 2+ (architect TDD)**: scope is LOCKED by this PRD at Phase 1 close; architect TDD translates scope into design, does NOT renegotiate it

## STOP Boundaries (Global — Non-Negotiable)

- **Working-tree edits only**: zero commits from any Phase (operator commits at sprint close)
- **No branches; no pushes**
- **No production probes**: staging/local only
- **No cross-rite scope-creep**: if a probe surfaces ecosystem-rite or hygiene-rite or SRE-rite work, flag in AUDIT §out-of-scope-flags; do NOT execute
- **No knossos writes**: throughline ratification is S17-gated
- **No main-thread-only artifacts written by specialists**: FLEET-COORDINATION dashboard updates are main-thread-only (Phase 4); specialists write only to their designated artifacts
- **Scope-lock invariant**: Phase 2 (architect TDD) and Phase 3 (principal-engineer + qa-adversary) MUST NOT modify this PRD's scope. If scope ambiguity surfaces, escalate to user for PRD amendment.

## Evidence Grade Expectations

Per `self-ref-evidence-grade-rule` and S16 shape line 607:

| Artifact | Baseline Grade | Upgrade Path |
|----------|---------------|--------------|
| AUDIT-sprint5-post-deploy-adversarial | `[MODERATE]` | Capped by self-reference; upgrades require external rite concurrence |
| §env-surface-delta checklist | `[MODERATE]` | Authored within 10x-dev rite |
| H6 HANDOFF (ecosystem) | `[MODERATE]` at emission → `[STRONG]` on HANDOFF-RESPONSE landing | Ecosystem rite concurrence in eco006-inventory update |
| H7 HANDOFF (val01b) | `[MODERATE]` at emission → `[STRONG]` on HANDOFF-RESPONSE landing | val01b rite concurrence + operator ratification |
| PT-16 overall verdict | `[MODERATE]` | Capped at rite authorship until S17 external attestation |
| Probe A methodology | `[MODERATE]` | grep-pattern set and file-scope list externally reviewable |
| Probe B adversarial matrix | `[MODERATE]` | 6-shape × N-endpoint table externally reviewable; info-disclosure assertions use regex patterns auditable by any reviewer |
| Probe C header resilience matrix | `[MODERATE]` | byte-identity diff against peer captures provides cross-satellite corroboration (same-rite still; caps at MODERATE) |

**Upgrade trigger to STRONG**: Cross-rite HANDOFF-RESPONSE landings (if H6/H7 emit) carry the intake rite's concurrence, which lifts the corresponding handoff grade to STRONG. The AUDIT itself remains MODERATE until S17 convergence-attestation.

## Assumptions (Stakeholder-Confirmed)

1. **Commit scope is verified**: Main-thread pre-flight (per dispatch brief) confirmed `0474a60c` file list, wire codes, PT-03 captures, and 1442-pass test state. This PRD does NOT re-verify commit scope; Phase 3 may read source files for methodology purposes but does NOT re-validate the commit's assertions.
- **Confirmation**: Dispatch brief from main-thread potnia, 2026-04-21T07:30Z+.
2. **Local/staging endpoint access is available to qa-adversary**: Probe B and Probe C execute against a local or staging autom8y-asana HTTP server. Production is prohibited.
- **Confirmation**: Assumed per 10x-dev rite convention. If false at Phase 3, escalate per §Success Criteria BLOCKER conditions.
3. **Byte-identity captures for peers (ads, scheduling) exist**: Probe C diffs against `.ledge/spikes/pt-03-captures/{ads,scheduling}-headers.txt`. If peer captures are missing, Probe C degrades to self-capture-only with explicit annotation.
- **Confirmation**: Per commit `0474a60c` message claim; Phase 3 verifies file existence at probe start.
4. **H7 emission requires operator pre-ratification**: Because H7 would reopen R9 REPLAN-003, Phase 4 escalates BEFORE authoring H7. This is NOT a blocker for H6.
- **Confirmation**: Retrospective §6 R9; dispatch brief acceptance criterion 4.
5. **PRD scope is LOCKED at Phase 1 close**: Phase 2 architect TDD translates this scope; Phase 2+ does NOT renegotiate. Ambiguity → escalation → PRD amendment.
- **Confirmation**: Dispatch brief STOP boundary.

## Open Questions

**None at Phase 1 close.** All ambiguities enumerated in the dispatch brief have been resolved via the structural decisions encoded in §Edge Cases and §Assumptions. The following are explicitly DEFERRED to Phase 3 by methodology (not open questions):

- Exact endpoint paths for Probe B: determined at Phase 3 by reading `src/autom8_asana/api/main.py` router registrations.
- Exact 500-response-shape-inducing input for Probe C variant #3: determined at Phase 3 by qa-adversary exploration, OR documented as N/A-exception.
- Exact 3xx-redirect route for Probe C variant #5: determined at Phase 3 by route enumeration, OR documented as N/A-by-absence.

## Attestation Table

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| S16 shape spec | `/Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.shape.md` (lines 583-608) | Read by requirements-analyst Phase 1 |
| Frame WS-6 scope | `/Users/tomtenuta/Code/a8/repos/.sos/wip/frames/total-fleet-env-convergance.md` (§3 WS-6) | Referenced via dispatch brief |
| Fleet coordination dashboard | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md` | Referenced via dispatch brief |
| Predecessor retrospective | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/RETROSPECTIVE-env-secret-platformization-closeout-2026-04-21.md` (§6 R9/R10) | Referenced via dispatch brief |
| Target commit | `0474a60c` on autom8y-asana main | Verified via dispatch brief main-thread pre-flight |
| PT-03 captures (self) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/asana-envelope.json`, `asana-headers.txt`, `asana-webhook-envelope.json` | Referenced per commit claim |
| PT-03 captures (peers) | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/pt-03-captures/{ads,scheduling}-headers.txt` | Phase 3 verifies existence at probe start |
| This PRD | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-sprint5-post-deploy-adversarial-2026-04-21.md` | Written by requirements-analyst Phase 1 |

## Handoff To Phase 2 (Architect TDD)

This PRD establishes scope, acceptance criteria, and probe matrix. Phase 2 (architect) receives this PRD and produces a TDD at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-sprint5-post-deploy-adversarial-2026-04-21.md` that translates §Probe Matrix methodology into concrete specialist dispatch specifications (Probe A → principal-engineer with exact grep commands and file paths; Probes B+C → qa-adversary with exact adversarial-shape construction and assertion regex patterns). The TDD MUST NOT renegotiate scope.

**Scope lock confirmed**: Yes. PRD scope is LOCKED.
