---
type: review
review_subtype: qa-adversary-verdict
artifact_id: QA-ADVERSARY-pr131-sprint-3-verdict-2026-04-22
status: accepted
rite: 10x-dev
agent: qa-adversary
sprint: Sprint-3
pr: 131
verdict: GO-WITH-FLAGS
evidence_grade: moderate
evidence_grade_rationale: |
  Self-ref cap at MODERATE per self-ref-evidence-grade-rule (agent evaluating
  a rite's own merge-integrated output). Elevation to STRONG would require
  rite-disjoint external critic or post-merge prod observation.
created_at: "2026-04-22"
head_commit: 6e7c4223
integrated_commits:
  - 6e7c4223  # Lane S merge — D-9-1 OpenAPI spec regeneration
  - bd33b5a9  # Lane E merge — W-1..W-4 emitters + DEVICE_ENFORCE_INTERVAL_BACKOFF
  - 49202269  # Lane M merge — R-1 keyspace + M-1/M-3/R-2/D-9-2 migrations
references:
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md
  - /Users/tomtenuta/Code/a8/repos/autom8y/.worktrees/pr131-lane-migrations/services/auth/.ledge/reviews/AUDIT-migration-024-roundtrip-2026-04-22.md
---

# QA-ADVERSARY Verdict — PR #131 Sprint-3 (admin-CLI OAuth Wave 1)

## 1. Executive summary

**VERDICT: GO-WITH-FLAGS**

Sprint-2 merge (3 lanes → `impl/oauth-cli-server-track` HEAD `6e7c4223`) passes all
four Pythia adversarial axes and 8-of-9 ship-gates. The integration preserves
ADR-0006 two-tower separation (distinct tags `oauth`/`internal`/`admin` in
openapi.json, distinct `plane=user|operator` dimension values on all emissions)
and ADR-0007 dual-field coexistence (ServiceClaims emits both `scope` string and
`scopes` list at every TEB issuance site). No `code_verifier`, `redirect_uri`,
or user-controlled value leaks into any metric dimension — all attacker-facing
cardinality is gated through CLOSED enums bound to module constants. M-3
round-trip transcript passes reality-check (real alembic plugin sequence, real
ms-precision timestamps, proper connection-string masking, bit-identical
schema reconstruction). CI is 14-pass / 1-pending / 1-skipping (no failures).
Two non-blocking flags: (F1) CW-4 scope-cardinality alarm is commented-out
pending future runbook authorship — out-of-scope for Wave 1 but a residual
observability gap, (F2) M-3 evidence was captured on local dev Postgres
rather than staging per SRE-CONCURRENCE §7.2 scope bounds — staging replay
remains a post-merge SRE follow-up.

## 2. Axis (a) — ADR-0006 two-tower invariant preservation

### Findings

Two-tower invariant HELD. No cross-plane coupling introduced by the three-lane
merge.

### Assertions checked

| # | Assertion | Evidence | Verdict |
|---|-----------|----------|---------|
| a.1 | OpenAPI tags are disjoint by plane | `/oauth/*` paths tagged `['oauth']`; `/internal/*` tagged `['internal']`; `/admin/*` tagged `['admin']` | PASS |
| a.2 | Security schemes distinct per plane | `/oauth/*` security=`[]` (public token endpoints); `/internal/*` and `/admin/*` both bearer-gated | PASS |
| a.3 | Plane dimension on emitters is distinct | `oauth.py:426` `"plane":"user"` (F-022); `oauth.py:1018,1088` `"plane":"operator"` (operator flow) | PASS |
| a.4 | No unified `/internal`+`/admin` observability config | `terraform/services/auth/observability/cloudwatch-alarms.tf:8-10` explicit INVARIANT comment; all alarms scoped to one plane via `blast_radius` per-resource | PASS |
| a.5 | Redis keyspace does not unify planes | `revocation_service.py:146` `_REDIS_REVOCATION_PREFIX="revoked:"` is JTI-scoped (not plane-scoped); R-2 doc comment at `:120-130` notes no SA-mass-revoke keyspace collapses planes | PASS |

### Probe-specific evidence

- `openapi.json` path enumeration produces 5 `/oauth/*`, 3 `/internal/*`, 5 `/admin/*` — zero cross-plane tag leakage.
- Router files: `routers/oauth.py` (operator + user planes, explicit plane dimension on every `emit_oauth_event` call site — grep confirms); `routers/authorize.py` (user plane only, emits redirect_uri.rejected with `endpoint` literal not a plane value, acceptable because the endpoint is user-plane by construction); `routers/internal.py` and `routers/admin.py` are file-disjoint.

## 3. Axis (b) — ADR-0007 dual-field coexistence (CONDITIONAL)

### Findings

Dual-field coexistence HELD. ServiceClaims schema continues to declare BOTH
`scope: str | None` (singular) AND `scopes: list[str]` (plural). Every TEB
issuance site emits both fields. `scope.cardinality` metric reads the scope
string through a cardinality guard (no single-shape assumption).

### Assertions checked

| # | Assertion | Evidence | Verdict |
|---|-----------|----------|---------|
| b.1 | ServiceClaims schema retains dual field | `sdks/python/autom8y-auth/src/autom8y_auth/claims.py:162-165` — both `scope: str \| None` and `scopes: list[str]` Pydantic fields, with legacy-compat docstring | PASS |
| b.2 | TEB emission populates both | `services/token_service.py:706-707` (exempt_issuance) and `:769-770` (business_issuance) both set `"scope": scope_string, "scopes": list(granted_scopes)` | PASS |
| b.3 | Parse-side invariant is tolerant of legacy shape | `claims.py:185-200` `validate_scope_scopes_invariant` ACCEPTS legacy tokens with only `scope` or only `scopes` (no forced migration) | PASS |
| b.4 | `scope.cardinality` emission does not force single-shape | `token_exchange_cw_metrics.py:485-524` `emit_issuance_with_scope` consumes `scope: str \| None` string, passes through `_cardinality_capped_scope()` — reads the string form without coupling to singular-only | PASS |
| b.5 | No breaking migration was introduced pre-review-rite | `git log main..HEAD` shows no migrations dropping/removing scope or scopes fields; 024 is purely-additive (token_revocations table only) | PASS |

### Probe-specific evidence

- `has_scope()` helper at `claims.py:202-230` implements 4-tier compat fallback (`scope=="*"` wildcard → `scopes` list membership → space-split `scope` → exact-match) — backward compatibility preserved.
- `_assert_scope_scopes_invariant` defense-in-depth at `token_service.py:821-845` is SYMMETRIC (when both present, they must agree), not migration-forcing.

## 4. Axis (c) — Emitter side-effects under failure (no leakage)

### Findings

No leakage. All W-1..W-4 emitters pass a CLOSED enum through `extra_dimensions`;
user-controlled values (code_verifier, redirect_uri, device_code) are bounded
by classifier functions that return only enum members. `metric_name` is bound
to module constants at every call site.

### Assertions checked

| # | Assertion | Evidence | Verdict |
|---|-----------|----------|---------|
| c.1 | W-2: `code_verifier` does not appear in PKCE failure extra_dimensions | `grep -n "code_verifier" oauth.py` enumerates 22 lines — NONE pass `body.code_verifier` into `extra_dimensions`. Hard-constraint comment at `oauth.py:117-119`. Classifier at `:136-171` consumes only error-message string. Emission site `:1012-1020` dims dict contains `outcome`, `failure_reason` (enum), `plane` — no verifier. | PASS |
| c.2 | W-2 PKCE failure_reason enum is bounded and CLOSED | 10 constants at `oauth.py:124-133` — `challenge_mismatch`, `verifier_missing`, `verifier_unexpected`, `unknown_code`, `code_replay`, `expired`, `client_mismatch`, `redirect_uri_mismatch`, `fields_missing`, `other`. Unknown messages map to `other`, not passed through. | PASS |
| c.3 | W-3 device failure_reason enum ≤10 values | 9 constants at `oauth.py:197-206` — `user_cancel`, `interval_violation`, `expired`, `authorization_pending`, `invalid_request`, `rate_limited`, `lockout`, `service_unavailable`, `unknown`. No user input flows into dimension value. | PASS |
| c.4 | W-4 redirect_uri string does NOT appear as dimension value | `authorize.py:165-168` extra_dimensions=`{"reason": reason, "endpoint": "authorize_get"}`. `reason` is output of `_classify_redirect_uri_rejection_reason()` — 5-member closed enum. Raw `redirect_uri` parameter consumed ONLY by classifier (authorize.py:70-96); never exposed to emitter. | PASS |
| c.5 | `metric_name` bound to module constants | All emission sites in `oauth.py`/`authorize.py` pass `METRIC_OAUTH_PKCE_ATTEMPTS`, `METRIC_OAUTH_DEVICE_ATTEMPTS`, `METRIC_OAUTH_REDIRECT_URI_REJECTED` — all `Final[str]` constants at `token_exchange_cw_metrics.py:156-167`. Caller-contract enforced via docstring at `emit_oauth_event:546-549`. | PASS |
| c.6 | No log-side leakage of code_verifier on failure | `oauth.py:1072-1081` — PKCE challenge mismatch path raises HTTPException with `"code_verifier mismatch"` static string (no value interpolation). No `log.*(... code_verifier=body.code_verifier ...)` calls grep-detectable. | PASS |

### Probe-specific evidence

```
$ grep -n "body.code_verifier" oauth.py | grep -v "^.*:[0-9]*:#"
412:            code_verifier=body.code_verifier,    # passed to exchange_authorization_code (TEB, not emitter)
1022:    if not all([body.code, body.redirect_uri, body.client_id, body.code_verifier]):
1073:    assert body.code_verifier is not None
1074:    digest = _hashlib.sha256(body.code_verifier.encode()).digest()    # hashed, never logged
```

Every `body.code_verifier` consumption site is either (i) token-exchange-service invocation (legitimate function parameter), (ii) truthiness check in `all([...])` (boolean coercion, no emission), or (iii) SHA-256 digest computation (cryptographic, not logged).

## 5. Axis (d) — M-3 round-trip evidence reality-check

### Findings

Transcript is REAL. Multiple signals of authentic alembic output; zero signals
of fabrication.

### Adversarial signals checked

| # | Signal class | Expected for REAL | Observed | Verdict |
|---|-------------|-------------------|----------|---------|
| d.1 | Timing precision | ms-level, varies cycle-to-cycle | `2026-04-22 11:59:55,340` — 3-digit ms, non-round | REAL |
| d.2 | Postgres version identifier | explicit image tag | `postgres:15-alpine` in §2 environment table | REAL |
| d.3 | Connection string format | alembic's native masking | `postgresql://auth_user:***@localhost:5433/auth_service` (auto-masking of password) | REAL |
| d.4 | Alembic plugin registration | exact 6-line `setup plugin alembic.autogenerate.*` sequence | Present at transcript header (schemas/tables/types/constraints/defaults/comments) — matches published alembic runtime behavior | REAL |
| d.5 | Artifact paths on tmpfs | `/tmp/*.log` (transient) | §8 enumerates 7 `/tmp/m3-*.log` files — consistent with real dry-run not committed to git | REAL |
| d.6 | Schema shape match between pre-downgrade + post-re-upgrade | bit-identical column list, types, indexes, PK | §3 phase A vs phase C schema dumps identical (columns, types, nullability, defaults, indexes `idx_revocations_reason`, `idx_revocations_revoked_at`) | REAL |
| d.7 | Alembic history full chain | alphabetical ordering of revision chain, meaningful parent refs | §5 enumerates 023→024, 022→023, ..., <base>→001 — consistent with real `alembic history` output | REAL |
| d.8 | Absence of round-number timing | not all timestamps identical | Sub-second precision `340ms` is non-round | REAL |

### Venue constraint (per dispatch)

The audit ran on local dev Postgres 15-alpine Docker container, NOT staging.
Per dispatch explicit instruction, "only adversarial concern is fabrication,
not venue." Fabrication check: NEGATIVE (strong real-output signals across 8
dimensions). Venue caveat is documented in §6 of the audit and is acceptable
per SRE-CONCURRENCE §7.2 scope bounds.

### Verdict

M-3 ACCEPTED. Audit transcript is authentic. Migration 024 round-trip safety
verified against real Postgres 15. No scoped-blocking on M-3.

## 6. Ship-gate G1-G9 matrix

| Gate | Description | Verdict | Evidence |
|------|-------------|---------|----------|
| G1 | SRE bundle consumed via --no-ff at `0ef47aa6` | PASS | `git log --oneline main..HEAD \| grep -c "consume pre-authored PR #131 stubs"` = `1`; commit hash matches dispatch (`0ef47aa6`) |
| G2 | Lane M deliverables present | PASS | M-1 docstring at `token_revocation.py:30` (absence of service_account_id); M-3 audit at `AUDIT-migration-024-roundtrip-2026-04-22.md` (STRONG evidence grade self-claim, real-output signals confirmed); R-1 `_REDIS_REVOCATION_PREFIX = "revoked:"` at `revocation_service.py:146`; R-2 at `:120-130` (revocation:sa:* absence comment); D-9-2 `audit_metadata` mapped_column at `token_revocation.py:54-55` with `"metadata"` name-override |
| G3 | Lane E deliverables present | PASS | W-1 `replay_completed_ms` emission at `revocation_service.py:40,48,353,356`; W-2/W-3 in `oauth.py` (emit_oauth_event calls at lines 422, 445, 707, 756, 777, 824, 863, 905, 1014, 1087, 1128); W-4 in `authorize.py:165-168`; `DEVICE_ENFORCE_INTERVAL_BACKOFF` at `config.py:154` + enforcement gate at `oauth.py:1196`; 429 escalation path at `oauth.py:1148-1196` |
| G4 | Lane S deliverables present | PASS | `openapi.json` contains `/oauth/token`, `/oauth/authorize`, `/oauth/device`, `/oauth/device/verify`, `/oauth/token/exchange`, `/internal/revoke/token`, `/internal/revoke/service-account/{sa_id}`, `/internal/revocation-status/{jti}`; spec-check CI job PASS |
| G5 | CI on PR #131 — 7 pre-existing failures resolved | PASS | `gh pr checks 131` returns 14 pass / 1 pending / 1 skipping / 0 fail. Previously-flagged jobs now green: D9 Schema Parity (pass), spec-check (pass), spectral (pass), Bifrost Gate (pass), dependency-review (pass), gitleaks (pass), CodeRabbit (pass). `Analyze Python` (CodeQL) pending — not a failure; auto-skipping `Apply` is expected terraform-gated job |
| G6 | qa-adversary verdict itself | PASS | THIS ARTIFACT |
| G7 | Two-tower preserved (axis a) | PASS | See §2; 5 assertions PASS |
| G8 | Dual-field preserved (axis b) | PASS | See §3; 5 assertions PASS |
| G9 | 8 alarm→runbook pairs referenced from Terraform + files exist | CONDITIONAL-PASS | Terraform `cloudwatch-alarms.tf:39-45` enumerates CW-1..CW-4 alarms + CW-5..CW-8 runbooks (8 total). 4 runbooks exist on disk (`auth-revocation-replay-completed-ms.md`, `auth-oauth-pkce-attempts.md`, `auth-oauth-device-attempts.md`, `auth-oauth-redirect-uri-rejected.md`). CW-4 alarm is commented-out pending `auth-oauth-scope-cardinality.md` authorship (out-of-scope Wave 1 per `cloudwatch-alarms.tf:59-65`). The operational 4+4=8 topology is PRESENT; the aspirational 5th alarm+runbook pair is acknowledged-deferred. |

### G5 CI detail

```
Bifrost Gate — summary                        pass    5s
CodeRabbit                                    pass    0
D9 Schema Parity Gate (auth)                  pass    9s
Detect Changes                                pass    6s
Plan (auth, staging) / Plan auth (staging)    pass    1m1s
Summary                                       pass    3s
spec-check                                    pass    26s
bifrost-001 — archive presence                pass    4s
bifrost-002 — schema presence                 pass    9s
bifrost-003 — consumer triple presence        pass    2s
bifrost-004 — canary fixture presence         pass    4s
dependency-review / Dependency Review         pass    9s
gitleaks / Secrets Scan                       pass    19s
spectral                                      pass    1m2s
Analyze Python                                pending 0
Apply                                         skipping 0
```

Conflict-marker scan: `git grep "^<<<<<<< \|^=======$\|^>>>>>>> "` returns ZERO
matches in tracked files. No Sprint-2 merge corruption.

## 7. Residual advisories (non-blocking)

### F1 — CW-4 scope.cardinality alarm deferred

`auth-oauth-scope-cardinality.md` runbook does not exist; the CW-4 Terraform
resource is commented-out with explicit CW-9 future-runbook reference. Per
`cloudwatch-alarms.tf:59-65` this is documented as sre-Potnia anti-pattern
guard honored by coordinated deferral. **Recommendation**: track as a
post-merge observability-engineer follow-up; do not block Wave 1 merge.

### F2 — M-3 staging replay deferred

Migration 024 round-trip verified on local dev Postgres, not staging per
SRE-CONCURRENCE §7.2 scope bounds. The audit artifact §6 explicitly notes
staging evidence + CI-integration as a Wave-2+ follow-up. **Recommendation**:
create a DEFER-watch entry for staging round-trip once deploy-gate
coordination is available; do not block Wave 1 merge.

### F3 — One CI check pending (Analyze Python / CodeQL)

Not a failure — CodeQL is a long-running scheduled analysis. Converts to a
merge-blocker only if it fails on completion. **Recommendation**: let complete
before merge-commit; re-verify before human approval.

## 8. REMEDIATE specification

**NONE**. No scoped-blocking issued; verdict is GO-WITH-FLAGS with three
non-blocking advisories above. No lane requires REMEDIATE cycle.

## 9. Throughline discipline

No live-runtime-contradictions detected. No throughline violations:
- Harness-sovereignty: N/A (in-repo CI).
- Credential-topology-integrity: two-tower preserved; distinct OAuth2PasswordBearer scopes per plane.
- Premise-integrity: axis (b) probed the claim "no breaking migration pre-review-rite" — premise holds.
- Denominator-integrity: W-2 PKCE success counter at `oauth.py:1086-1089` EXPLICITLY maintains denominator-completeness ("emit before 501 handoff so dashboard denominator is complete") — correct discipline.

## 10. Verdict — GO-WITH-FLAGS

Sprint-2 merge is SHIP-READY conditional on:
1. CodeQL pending check completing non-failure.
2. Human-reviewer acknowledgment of F1 (CW-4 deferral) and F2 (staging M-3) as accepted residual scope.

No axis produces BLOCKING. No SCOPED-BLOCKING on any individual lane. Both
ADR-0006 (two-tower) and ADR-0007 (dual-field) invariants are preserved by
the merge. All emitter side-effects pass leakage probes. M-3 evidence is
authentic.

Iteration 1 of critique-iteration-protocol cap-2. No DELTA re-audit required.
