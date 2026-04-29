---
type: handoff
artifact_id: HANDOFF-sre-to-10x-dev-pr131-11-blocking-remediation-2026-04-22
schema_version: "1.0"
source_rite: sre (Lane 2 revocation-backend readiness + Lane 1 CI diagnosis)
target_rite: 10x-dev
handoff_type: implementation
priority: high
blocking: true  # PR #131 ship-gate blocked on 11 BLOCKING items per SRE-CONCURRENCE §7.2
status: proposed
handoff_status: pending
initiative_parent: autom8y-core-aliaschoices-platformization (Phase C operationalization)
sprint_source: "SRE Lane 1 + Lane 2 close 2026-04-22"
sprint_target: "10x-dev principal-engineer execution of 11 BLOCKING items + 2 Lane 1 PR-specific regressions"
emitted_at: "2026-04-22T00:40Z"
expires_after: "14d"
design_references:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-CONCURRENCE-pr131-revocation-backend-readiness-2026-04-21.md  # REMEDIATE verdict; 11 BLOCKING items in §7.2
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/DIAGNOSIS-ci-failures-3pr-2026-04-21.md  # Lane 1 §4.2 PR #131 specifics
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0004-revocation-backend-dual-tier.md  # observability anchor
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md  # two-tower invariant
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md  # CONDITIONAL STUB (authored 2026-04-22 per operator R3; review-rite adjudicates final terms)
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-10x-dev-to-overarching-phase-c-operationalize-2026-04-21.md  # original admin-CLI Wave 1 HANDOFF with production-ship blockers
depends_on:
  - "main-branch recovery PR (Bundle A per sibling HANDOFF-sre-to-hygiene) merged first — unblocks inherited-from-main CI failures"
evidence_grade: strong
---

# HANDOFF — SRE → 10x-dev (PR #131 11 BLOCKING Remediation)

## 1. Context

Per SRE-CONCURRENCE on PR #131 revocation-backend readiness (`SRE-CONCURRENCE-pr131-revocation-backend-readiness-2026-04-21.md`), the aggregate verdict is **REMEDIATE** (3/3/0). PR #131 admin-CLI OAuth Wave 1 cannot ship until 11 BLOCKING items address gaps in 3 scope areas + 2 Lane 1 PR-specific regressions.

**ADR-0007 CONDITIONAL state**: STUB authored 2026-04-22T00:00Z by SRE main-thread at canonical path per operator R3 ruling. Wave 1 Option (iii) dual-field coexistence semantics remain operative. No downstream activates breaking-shape migration pending review-rite response.

## 2. Scope — 11 BLOCKING + 2 Lane 1 Amendments

### §2.1 Migration 024 (2 items; schema drift + operational readiness)

**M-1**: Reconcile `service_account_id` column presence. HANDOFF §C-2 spec + ADR-0004 field list diverge from migration reality — audit which is authoritative + align. If column present: document in ADR-0004 addendum; if absent: remove references from ADR-0004 §Fields.

**M-2**: Author rollback runbook. Migration 024 currently has no documented rollback path. Author at `autom8y/services/auth/runbooks/revocation-migration-024-rollback.md` covering: (a) backward-compat with prior migration; (b) data preservation during rollback; (c) elapsed-time estimate; (d) trigger conditions.

**M-3** (operational): Staging alembic round-trip evidence. Run migration 024 UP + DOWN + UP on staging; capture `alembic history` output; attach to PR as evidence of rollback safety.

### §2.2 Redis key-patterns (2 items; specification alignment)

**R-1**: Reconcile `revoked:{jti}` vs `revocation:{jti}` keyspace mismatch. Implementation uses `revoked:{jti}`; HANDOFF §C-2 + ADR-0004 spec `revocation:{jti}`. Choose one + update all references (code + spec + HANDOFF addendum).

**R-2**: Document absence of `revocation:sa:*` keyspace (SA mass-revoke is DB-flag-driven, not per-SA cached keys). Update ADR-0004 §Redis-keys to explicitly state this; remove `revocation:sa:*` from HANDOFF §C-2 key-pattern review; document cluster-reconnect replay re-trigger behavior.

### §2.3 CloudWatch alarms + runbooks (HARD SHIP-GATE; 7 items per SRE anti-pattern)

**CW-1 through CW-4**: Author Terraform alarm resources for the 4 metric constants defined in code but NOT provisioned as CW alarms:
- `auth.revocation.replay_completed_ms` (P99 > 45s → page)
- `auth.oauth.pkce.attempts`
- `auth.oauth.device.attempts`
- `auth.oauth.redirect_uri.rejected`
- `auth.oauth.scope.cardinality` (alert at >50 distinct values)

Terraform resources at `autom8y/terraform/services/auth/observability/cloudwatch-alarms.tf` or equivalent path.

**CW-5 through CW-8**: Author operational runbooks per alarm. Required per sre-Potnia "Creating alerts without runbooks" anti-pattern. Target path: `autom8y/services/auth/runbooks/{alarm-name}.md`. Minimum fields: (a) trigger interpretation; (b) triage steps; (c) escalation threshold; (d) fix playbook.

### §2.4 Lane 1 PR #131 specifics (2 items)

**D-9-1**: Regenerate OpenAPI spec for new `/oauth/token` + `/oauth/device` + `/internal/revoke` endpoints. Spec-check CI gate fails because new endpoints lack spec entries. Run spec-generator + commit regenerated spec file.

**D-9-2**: Add `metadata` JSONB column to `TokenRevocation` SQLAlchemy model. Migration 024 declares the column but model omits it (D9 Schema Parity catch). Add `metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)` or equivalent.

## 3. Acceptance Criteria

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All 11 BLOCKING items addressed per §2.1-§2.3 | SRE re-review verdict CONCUR |
| 2 | Both Lane 1 D-9 items addressed per §2.4 | spec-check + model tests green |
| 3 | PR #131 CI green post-rebase on main-recovery | statusCheckRollup passing |
| 4 | ADR-0006 two-tower invariant preserved (no observability config unifies planes) | SRE §5 re-verification |
| 5 | ADR-0007 CONDITIONAL compatibility preserved (dual-field coexistence; no breaking migration) | SRE §6 re-verification |
| 6 | All 8 new alarms have runbook references per "Creating alerts without runbooks" anti-pattern | Runbook files present + linked from Terraform |
| 7 | Security rite concurrence on threat-model closure (parallel gate) | Security HANDOFF-RESPONSE present |
| 8 | Review-rite ADR-0007 response landed OR explicit "Wave 2 deferred until response" noted | Review-rite HANDOFF-RESPONSE OR Wave 2 deferral memo |

## 4. Entry Conditions

1. Read this HANDOFF + SRE-CONCURRENCE (primary) + DIAGNOSIS §4.2 (Lane 1 specifics)
2. Read ADR-0004 (revocation backend architecture) + ADR-0006 (two-tower) + ADR-0007 STUB
3. Read 10x-dev admin-CLI Wave 1 HANDOFF §C-2 (original production-ship blockers)
4. 10x-dev Potnia orchestrates principal-engineer + qa-adversary cycle
5. **PREREQUISITE**: Bundle A main-recovery PR merges first (per sibling HANDOFF-sre-to-hygiene). Without that, inherited-from-main CI failures will mask PR #131 remediation validation.

## 5. Escalation Triggers

| Trigger | Action |
|---------|--------|
| ADR-0007 review-rite response activates breaking migration during this sprint | Pause; re-scope PR #131 per new shape; may require Wave 1 amendment |
| Migration 024 schema-drift reconciliation surfaces 3rd authoritative source (beyond ADR-0004 + implementation) | ESCALATE; consult ADR-0006 or create ADR-0008 |
| Terraform alarm authoring conflicts with existing fleet CW alarm namespace | Consult sre platform-engineer (cross-rite-handoff back to sre) |
| Security rite concurrence returns BLOCKING on threat-model items | Standard REMEDIATE cycle per critique-iteration-protocol |

## 6. Response Protocol

10x-dev Potnia emits at session close:
- Path: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-10x-dev-pr131-11-blocking-to-sre-{date}.md`
- Verdict: ACCEPTED-WITH-MERGE / PARTIAL / REMEDIATE+DELTA / ESCALATE
- Includes per-item remediation evidence + SRE re-review request
- CC restart to SRE rite required for re-review (operator's autonomous charter)

## 7. Evidence Grade

`[STRONG]` at emission.

## 8. Artifact Links

- SRE-CONCURRENCE: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-CONCURRENCE-pr131-revocation-backend-readiness-2026-04-21.md`
- DIAGNOSIS: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/DIAGNOSIS-ci-failures-3pr-2026-04-21.md`
- ADR-0007 STUB: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md`
- PR #131: `https://github.com/autom8y/autom8y/pull/131`
- Sibling HANDOFF (hygiene main-recovery): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-sre-to-hygiene-main-recovery-plus-pr136-amendment-2026-04-22.md`

---

*Emitted 2026-04-22T00:40Z SRE Lane 1+2 close → 10x-dev dispatch. Depends on hygiene main-recovery merge first.*
