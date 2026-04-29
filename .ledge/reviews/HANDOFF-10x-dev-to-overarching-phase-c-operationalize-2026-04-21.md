---
type: handoff
artifact_id: HANDOFF-10x-dev-to-overarching-phase-c-operationalize-2026-04-21
schema_version: "1.0"
source_rite: 10x-dev (admin-cli-oauth-migration; session 2026-04-21)
target_rite: ecosystem-rite (total-fleet-env-convergance parent; Phase C operationalization)
handoff_type: knowledge-transfer
priority: high
blocking: false
status: proposed
pr_url: https://github.com/autom8y/autom8y/pull/131
pr_branch: impl/oauth-cli-server-track
base_branch: main
emitted_at: "2026-04-21T~18:30Z"
expires_after: "60d"
initiative_source: admin-cli-oauth-migration (10x-dev; CLOSED)
initiative_target: total-fleet-env-convergance (ecosystem-rite; Phase C entry)
evidence_grade: STRONG
evidence_grade_rationale: |
  Cross-rite cross-session boundary artifact. Synthesizes multi-specialist
  10x-dev sprint at [STRONG] cross-rite grade. Sources: 7 ratified operator
  rulings + 4 review artifacts + 5 ADRs + 82-test suite + Phase 4 AUDIT
  ACCEPTED-WITH-CAVEATS verdict. Main-thread authored (not self-ref capped).
cold_landing_evidence:
  # SPRINT FOUNDATION (read in order)
  - path: autom8y/services/auth/.ledge/specs/PRD-admin-cli-oauth-migration-2026-04-21.md
    role: Requirements; 7 ratified operator rulings (Q1-Q4 + R1-R3); scope boundary
  - path: autom8y/services/auth/.ledge/specs/TDD-admin-cli-oauth-migration-2026-04-21.md
    role: Design authority; 14 sections; 43-test catalog + 2 amendment rounds
  # KEY DECISIONS (5 ratified, 1 conditional)
  - path: autom8y/services/auth/.ledge/decisions/ADR-0002-auth-login-pkce-device-code-hybrid-strategy.md
    role: Strategic shift: getpass → PKCE+device-code (R1=B ruling)
  - path: autom8y/services/auth/.ledge/decisions/ADR-0003-oauth-router-plane-separation.md
    role: routers/oauth.py dedicated; not bolted onto tokens.py
  - path: autom8y/services/auth/.ledge/decisions/ADR-0004-revocation-backend-dual-tier.md
    role: Postgres-first, Redis hot, fail-closed cold-start replay
  - path: autom8y/services/auth/.ledge/decisions/ADR-0005-autom8y-cli-binary-location.md
    role: autom8y/cli/ as new monorepo binary package
  - path: autom8y/services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md
    role: /internal/* scope-gated (OAuth M2M) vs /admin/* role-gated (RBAC) — DO NOT UNIFY
  - path: autom8y/services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md
    role: "CONDITIONAL: .scope→.scopes breaking migration; awaiting review-rite response"
  # QUALITY EVIDENCE
  - path: autom8y/services/auth/.ledge/reviews/PHASE-4-AUDIT-oauth-cli-2026-04-21.md
    role: Synthesis AUDIT; ACCEPTED-WITH-CAVEATS; 7 sections; STRONG-promotion path named
  - path: autom8y/services/auth/.ledge/reviews/QA-REPORT-oauth-cli-phase-3b-2026-04-21.md
    role: 82 tests passing; 10 defects (D-01+D-05 fixed); GO verdict
  - path: autom8y/services/auth/.ledge/reviews/THREAT-MODEL-oauth-surface-2026-04-21.md
    role: 21 STRIDE threats; T-03/T-07/T-11 BLOCKERs resolved
  - path: autom8y/services/auth/.ledge/reviews/ADVERSARIAL-BRIEF-oauth-cli-pre-impl-2026-04-21.md
    role: 47 edge cases; LRC-2/3/4 resolved; 6 amendments applied
  # CROSS-RITE HANDOFFS (3 emitted)
  - path: autom8y/sdks/python/autom8y-auth/.ledge/reviews/HANDOFF-10x-dev-to-review-serviceclaims-shape-migration-2026-04-21.md
    role: "review-rite gate: ServiceClaims shape; 26-consumer blast radius; UNACK'd"
  - path: autom8y/services/auth/.ledge/reviews/HANDOFF-10x-dev-to-ariadne-thread-auth-login-rewrite-2026-04-21.md
    role: Ariadne-thread courtesy; no required action
  - path: autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-10x-admin-cli-oauth-to-fleet-potnia-2026-04-21.md
    role: Sprint terminal HANDOFF-RESPONSE; Q2 escalation loop closed
  # UPSTREAM AUTHORITY (do not re-litigate)
  - path: autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md
    role: Fleet-level authority for SERVICE_API_KEY retirement + OAuth primacy
  - path: autom8y-val01b/.ledge/decisions/ADR-ENV-NAMING-CONVENTION.md
    role: Canonical env-var naming (Decision 4 scope string, Decision 13 boundary)
---

# HANDOFF — Phase C Operationalization + Clean Landing

## What Was Built (Phase A–B: Design + Implementation)

The 10x-dev sprint (2026-04-21) executed the full admin-CLI OAuth 2.0 migration lifecycle, closing the Q2 Zero-Trust-uniform-retire escalation from ADR-0001 §5.4. **Wave 1 is implementation-complete and staged for merge** via PR #131.

### Sprint deliverables in 30 seconds

| Layer | What landed |
|-------|-------------|
| **CLI** | `auth_login.py` rewritten (233→1237 lines): hybrid PKCE+device-code state machine. New `autom8y/cli/` binary: `autom8y login` = `just auth-login`. |
| **OAuth server** | 5 new endpoints in `routers/oauth.py` (PKCE + device-code flow); 3 revoke endpoints in `routers/internal.py` (scope-gated) |
| **Revocation** | Dual-tier backend: Postgres-first (durable) + Redis hot-path; migration 024 (`token_revocations` table); fail-closed replay on cold-start |
| **Scope** | `token_service.py` emits `scope` + `scopes` claims at TEB; `claims.py` additive compat `.scopes: list[str]` |
| **Tests** | 82/82 passing (46 server + 24 CLI-auth + 12 CLI-binary); AST single-spine invariant GREEN |
| **ADRs** | 5 ratified (0002-0006); 1 CONDITIONAL (0007 pending review-rite) |
| **Evidence** | Threat-model + Adversarial brief + QA report + Phase 4 AUDIT |

### What's NOT in Wave 1 (explicitly deferred)

1. `/oauth/token` JWT mint paths (3x 501 placeholders) — Wave 2
2. `ServiceClaims` breaking shape migration (`.scope` → `.scopes`) — Wave 2, awaiting review-rite
3. Credential cache at `~/.autom8y/credentials` — operator R3=B deferred to future sprint
4. External-audience SERVICE_API_KEY migration guide — R-QA-10 follow-up

---

## Phase C Scope: Operationalize + Land

Phase C is the **operationalization arc** — everything between "implementation-complete" and "running in production with confidence." Three parallel workstreams:

### Workstream C-1: Merge + CI Gate (immediate)

**Owner**: principal-engineer / main-thread

Pre-merge checklist (all must be GREEN):
- [x] PR #131 created: https://github.com/autom8y/autom8y/pull/131
- [x] 82/82 tests passing (verified locally; CI will re-run)
- [x] D-01 (CSRF) + D-05 (Redis fail-closed) fixed pre-merge
- [ ] CI green on PR #131
- [ ] Review-rite sign-off on additive-only SDK change (`claims.py` + `dependencies.py`)
- [ ] Alembic dry-run: `alembic upgrade head` + `alembic downgrade -1` on staging Postgres

**Merge gate command sequence** (for Phase C session entry):
```bash
# 1. CI check
gh pr checks 131

# 2. Alembic round-trip dry-run
cd autom8y/services/auth
uv run alembic upgrade head    # migration 024
uv run alembic downgrade -1    # rollback safe
uv run alembic upgrade head    # re-apply

# 3. Smoke test OAuth endpoints on staging
just auth-login --non-interactive  # ENV/SSM tier
autom8y login --non-interactive    # binary delegation parity

# 4. Merge when ready
gh pr merge 131 --squash --delete-branch
```

### Workstream C-2: SRE Gate (production-ship blocker)

**Owner**: SRE rite (recommend: dispatch `sre-rite HANDOFF` at merge)

**What SRE needs to sign off on**:

1. **Migration 024** (`token_revocations` table)
   - New Redis key namespace: `revocation:{jti}`, `revocation:sa:{sa_id}`
   - New Postgres table: `token_revocations (jti uuid PK, service_account_id uuid, revoked_at, expires_at)`
   - Alembic migration at `services/auth/migrations/versions/024_create_token_revocations_table.py`

2. **Cold-start replay behavior** (ADR-0004 §Fail-Closed)
   - During boot (≤30s), `/internal/*` returns 503 Retry-After: 5
   - CloudWatch metric: `auth.revocation.replay_completed_ms`
   - SRE alarm: P99 > 45s → page (threshold in `token_exchange_cw_metrics.py`)

3. **New CloudWatch metrics**
   - `auth.oauth.pkce.attempts`, `auth.oauth.device.attempts`
   - `auth.oauth.redirect_uri.rejected`
   - `auth.revocation.replay_completed_ms`
   - `auth.oauth.scope.cardinality` (alert at >50 distinct values)

4. **New Redis keys** to warm into elasticache pre-deploy

**Recommended HANDOFF dispatch**:
```
Target: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/
File: HANDOFF-10x-dev-to-sre-revocation-backend-2026-04-21.md
```
(not yet authored — Phase C first action)

### Workstream C-3: Security Concurrence (MODERATE → STRONG lift)

**Owner**: security rite (via `/security-review` skill or cross-rite HANDOFF)

Read-order for security reviewer:
1. `reviews/THREAT-MODEL-oauth-surface-2026-04-21.md` (21 threats; T-03/T-07/T-11 resolved)
2. `reviews/QA-REPORT-oauth-cli-phase-3b-2026-04-21.md` §4 (security probe: zero exploitable vulns found)
3. `reviews/ADVERSARIAL-BRIEF-oauth-cli-pre-impl-2026-04-21.md` §3 (live-runtime-contradiction register)
4. `reviews/PHASE-4-AUDIT-oauth-cli-2026-04-21.md` §6 (evidence-grade assessment)

Security concurrence = MODERATE → STRONG evidence grade lift on threat-model + defect disposition.

### Workstream C-4: Wave 2 Dispatch (post-review-rite response)

**Owner**: 10x-dev follow-on sprint (new session)

**Trigger**: review-rite HANDOFF response received (expected 2026-04-24) for `HANDOFF-10x-dev-to-review-serviceclaims-shape-migration-2026-04-21.md`

Wave 2 scope:
1. `/oauth/token` PKCE+device-code JWT mint (replace 501 placeholders in `routers/oauth.py`)
2. `ServiceClaims.scope: str` → `.scopes: list[str]` breaking migration per review-rite migration-path ruling (i/ii/iii from HANDOFF §3.2)
3. 26-consumer migration PRs (monorepo: single workspace bump; sibling repos: per-consumer PRs)
4. `ServiceClaims.tenant_scope` semantic rename (second-order; ADR-0007 design)

**Cold-landing context for Wave 2 session**:
```
Read:
  @autom8y/services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md
  @autom8y/sdks/python/autom8y-auth/.ledge/reviews/HANDOFF-10x-dev-to-review-serviceclaims-shape-migration-2026-04-21.md
  @[review-rite HANDOFF response when available]
  @autom8y/services/auth/.ledge/reviews/PHASE-4-AUDIT-oauth-cli-2026-04-21.md §3 (defect residual risk, D-09 timing-attack)
```

---

## Parent Initiative Dashboard Amendments (total-fleet-env-convergance)

When ecosystem-rite resumes `total-fleet-env-convergance` (parked at session-20260421-020948-2cae9b82), apply:

**File**: `autom8y-asana/.ledge/specs/FLEET-COORDINATION-total-fleet-env-convergance.md`

| Section | Update |
|---------|--------|
| §2 S12 row | Flip `PENDING-Q2-DISPOSITION` → `admin-CLI-rite sprint COMPLETE 2026-04-21; PR #131` |
| §5 Open-escalations | Remove Q2-admin-CLI entry (closed by HANDOFF-RESPONSE-10x) |
| §8 Update Log | Append `2026-04-21 admin-cli-oauth-migration Wave 1 delivered; 5 ADRs; 82 tests; ACCEPTED-WITH-CAVEATS; Wave 2 pending review-rite` |

**File**: `autom8y-asana/.ledge/reviews/CHECKPOINT-post-s12-pre-calendar-gate-2026-04-21.md`

| Section | Update |
|---------|--------|
| §2 What Landed | Append admin-CLI OAuth migration Wave 1 deliverables with PR #131 |
| §5 Resume Options | Mark Option α (Phase A admin-CLI) COMPLETE; Option β (ecosystem ADR-0004-retirement) unchanged |

---

## Critical Do-Not-Forget Items for Phase C

**1. ADR-0007 is CONDITIONAL** — Do NOT activate ServiceClaims breaking migration before review-rite responds. The additive-only compat skeleton (`claims.py`) is safe to merge with Wave 1. Breaking migration requires separate Wave 2 PR + coordinated 26-consumer migration.

**2. AST single-spine invariant MUST hold** — Any new code touching `resolve_admin_token()` or reading `ADMIN_TOKEN` env MUST pass `test_zero_raw_admin_token_env_reads_outside_resolver`. This test is at `services/auth/tests/test_sa_cli_adversarial.py`. Green it before any merge on auth scripts.

**3. Revocation plane separation** — ADR-0006 is a permanent two-tower architecture. `/internal/*` accepts OAuth M2M tokens with `admin:internal` scope; `/admin/*` accepts operator RBAC tokens with `auth_super_admin`/`auth_operator` role. **Do NOT merge these planes.** Any future admin endpoint design must pick a tower and document it.

**4. `/oauth/token` 501 placeholders** — Do not ship `/oauth/token` to production with placeholders live. Either complete Wave 2 or gate behind feature flag with clear error. Current placeholder emits structured `501 Not Implemented` with `AUTH-OAUTH-NOT-IMPL-001` so clients get clean failure.

**5. Feature flag topology** (from PHASE-4-AUDIT §4.2): 11 flags defined. OAuth endpoints default OFF until SRE deployment gate. `/internal/*` default OFF until `ADMIN_INTERNAL_SCOPE` populated in issued tokens (post-TEB scope emission deploy).

---

## Quick Orientation for Incoming Session

You are picking up Phase C of the admin-cli-oauth-migration sprint. The design + implementation arc (Phases 0–4) is CLOSED. Wave 1 is in PR #131. Your three immediate actions:

**Action 1** (5 min): Check PR #131 CI status
```bash
gh pr checks 131 --watch
```

**Action 2** (15 min): Draft SRE-rite HANDOFF
```
Path: autom8y-asana/.ledge/reviews/HANDOFF-10x-dev-to-sre-revocation-backend-2026-04-21.md
Scope: migration 024 + Redis key plan + CW metrics + cold-start replay alarm
Use: cross-rite-handoff skill
```

**Action 3** (2 min): Check if review-rite HANDOFF has been acknowledged
```bash
ls autom8y/sdks/python/autom8y-auth/.ledge/reviews/HANDOFF-RESPONSE-review-to-10x-dev-*
```

If acknowledged → unblock Wave 2 dispatch. If not → proceed with C-1 and C-2, Wave 2 waits.

---

## Full Artifact Inventory (14 canonical artifacts + 2 cross-rite HANDOFFs)

### Design + Decision
- `@autom8y/services/auth/.ledge/specs/PRD-admin-cli-oauth-migration-2026-04-21.md`
- `@autom8y/services/auth/.ledge/specs/TDD-admin-cli-oauth-migration-2026-04-21.md`
- `@autom8y/services/auth/.ledge/decisions/ADR-0002-auth-login-pkce-device-code-hybrid-strategy.md`
- `@autom8y/services/auth/.ledge/decisions/ADR-0003-oauth-router-plane-separation.md`
- `@autom8y/services/auth/.ledge/decisions/ADR-0004-revocation-backend-dual-tier.md`
- `@autom8y/services/auth/.ledge/decisions/ADR-0005-autom8y-cli-binary-location.md`
- `@autom8y/services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md`
- `@autom8y/services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md` (CONDITIONAL)

### Reviews
- `@autom8y/services/auth/.ledge/reviews/THREAT-MODEL-oauth-surface-2026-04-21.md`
- `@autom8y/services/auth/.ledge/reviews/ADVERSARIAL-BRIEF-oauth-cli-pre-impl-2026-04-21.md`
- `@autom8y/services/auth/.ledge/reviews/QA-REPORT-oauth-cli-phase-3b-2026-04-21.md`
- `@autom8y/services/auth/.ledge/reviews/PHASE-4-AUDIT-oauth-cli-2026-04-21.md`

### Cross-Rite HANDOFFs
- `@autom8y/sdks/python/autom8y-auth/.ledge/reviews/HANDOFF-10x-dev-to-review-serviceclaims-shape-migration-2026-04-21.md`
- `@autom8y/services/auth/.ledge/reviews/HANDOFF-10x-dev-to-ariadne-thread-auth-login-rewrite-2026-04-21.md`
- `@autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-10x-admin-cli-oauth-to-fleet-potnia-2026-04-21.md`

### Upstream Authority
- `@autom8y/sdks/python/autom8y-core/.ledge/decisions/ADR-0001-retire-service-api-key-oauth-primacy.md`
- `@autom8y-val01b/.ledge/decisions/ADR-ENV-NAMING-CONVENTION.md`

### Code
- PR #131: https://github.com/autom8y/autom8y/pull/131 (`impl/oauth-cli-server-track` → `main`)

---

*Emitted 2026-04-21T~18:30Z. Phase A–B (design + implementation) CLOSED. Phase C (operationalize) enters with this HANDOFF as primary context bundle.*
