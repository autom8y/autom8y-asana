---
type: review
artifact_id: SRE-PR131-POSTMERGE-REREVIEW-2026-04-22
schema_version: "1.0"
rite: sre
handoff_type: validation
priority: medium
blocking: false
status: accepted
review_of:
  - HANDOFF-RESPONSE-10x-dev-to-sre-pr131-merged-2026-04-22
  - SRE-CONCURRENCE-pr131-revocation-backend-readiness-2026-04-21
initiative: autom8y-core-aliaschoices-platformization-phase-a-post-merge-rereview
pr: 131
merge_commit: cedb9012
emitted_at: "2026-04-22T11:45Z"
evidence_grade: strong
specialists:
  - observability-engineer  # F1a
  - incident-commander       # F1b
  - platform-engineer        # F2
sidecar:
  - canonical-source-integrity-ratification-request  # N=4 → [STRONG] to ecosystem
---

# SRE Post-Merge Re-Review — PR #131

## 0. Header

- **Re-review scope**: SRE-CONCURRENCE §7.2 G6 — post-merge validation of observability emission contracts, runbook completeness, migration 024 staging-replay disposition, and two-tower invariant preservation under integrated code.
- **Merge commit**: `cedb9012` (autom8y/main; squash-merge 2026-04-22T10:14:46Z).
- **Inbound handoff**: `HANDOFF-RESPONSE-10x-dev-to-sre-pr131-merged-2026-04-22.md` §6 requested SRE re-review + F1/F2/F3 residual closure.
- **Ship-gate status going in**: G1..G8 PASS + G9 CONDITIONAL-PASS (4 of 5 alarm-runbook pairs present).
- **Ship-gate status going out**: see §5.

## 1. Executive verdict

**CONCUR** with merge integrity. **REMEDIATE** one new finding surfaced during re-review that is **not a regression** and **not ship-blocking** but MUST route to 10x-dev for disposition: `auth.oauth.scope.cardinality` metric emission is declared but not wired at any production callsite. Ship-gate G9 moves from CONDITIONAL-PASS to **CONDITIONAL-PASS-QUALIFIED** (unchanged verdict; sharpened finding).

Phase A retirement-baseline remains banked. Zero correctness regressions identified. Two-tower invariant (ADR-0006) preserved. ServiceClaims dual-field (ADR-0007) preserved.

## 2. F1 disposition — CW-4 alarm-runbook pair (scope-cardinality)

### 2.1 F1a (observability-engineer sub-artifact)

Full: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-F1A-cw4-alarm-emission-audit-2026-04-22.md`

**Verdict**: `CONCUR-LEAVE-COMMENTED-WITH-UNBLOCK-CONDITION`.

**Key findings**:

1. **BLOCKING-for-activation**: `METRIC_OAUTH_SCOPE_CARDINALITY` is declared at `services/auth/autom8y_auth_server/services/token_exchange_cw_metrics.py:162` and the full emission helper (`emit_issuance_with_scope` at `:485`) exists with overflow guard — but **zero production callsites invoke it**. The commented alarm binds to `ScopeCardinalityObserved` (`cloudwatch-alarms.tf:410`), a metric-name constant that does not exist in the codebase at all. Uncommenting today would produce a permanently-silent alarm.
2. **Overflow guard is sound**: thread-safe (`Lock()` at `:116`), bounded (cap=50 at `:134`), test-covered (`tests/test_oauth_server_track.py:472-507`). The guard protects a dead code path, but the guard itself is correct.
3. **Threshold recommendation**: static `>50` at the alarm level is wrong — it's the in-process cost-protection ceiling, not an operating-baseline. Either (A) TBD + 7d-baseline-calibrate (matching CW-2a/CW-2b pattern at `cloudwatch-alarms.tf:249-258`), or (B) rewire alarm to the existing `token_exchange_cw_metrics_scope_cardinality_overflow` log-event (`:137-141`) as a binary overflow signal (`Sum > 0 / 5-min / 1 period`). Shape (B) sidesteps baseline calibration entirely.
4. **No Terraform edit applied this sprint** — three unblock conditions must all clear before the commented block at `:405-433` can be uncommented:
   - **U1**: emission wired at token-exchange callsite — **10x-dev scope, not SRE** (see §4 cross-rite finding).
   - **U2**: runbook `auth-oauth-scope-cardinality.md` authored — **CLEARED by F1b** (see §2.2).
   - **U3**: threshold shape (A) or (B) decided — partially grounded by F1b's dual-threshold runbook (runbook remains valid under either shape without edit).

### 2.2 F1b (incident-commander sub-artifact)

Full: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-F1B-cw4-runbook-authored-2026-04-22.md`

**Verdict**: `RUNBOOK-AUTHORED`.

**Artifact**: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/auth-oauth-scope-cardinality.md` (~180 lines, CW-9; structurally parity-matched to CW-6/7/8 templates).

**Structure** (H2 TOC):
- (a) Trigger Interpretation — dual-signal (gauge + overflow counter); 4 hypotheses (attacker, client regression, enum drift, restart over-counting); explicit NOT-`/admin/*`-plane per ADR-0006.
- (b) Triage Steps — 10 ordered, executable today (CW Logs Insights, aws-cli ECS, overflow-log `scope` field extraction).
- (c) Escalation Threshold — 6-row matrix; intentionally NO SEV-1 path (scope-cardinality is correctness/cost-adjacent, not outage).
- (d) Fix Playbook — enum-drift forward-sync / client rollback / auth-server revert / attacker-probe preservation; "Do NOT do" block protects `SCOPE_CARDINALITY_CAP=50` integrity.
- (e) Security-rite handoff trigger — attacker-probe + enumeration + CW-8 co-fire.
- (f) False-positive suppression — 4h default; deploy-induced transient + CI load test seed list.

**Three judgment calls** (documented in audit §4):
1. Threshold dual-interpretation (static + post-baseline) — runbook stays valid across F1a's U3 finalization without edit.
2. Overflow-counter as paired signal in triage steps 1 & 9; §(d) instructs root-cause BEFORE task-rotation (rotation clears in-process set and masks signal — metric-specific foot-gun).
3. No SEV-1 path by design — pre-empts severity-inflation anti-pattern; SEV-1 only fires via co-classification through another runbook.

**G9 residual F1 half-closed**: runbook side complete. Alarm side remains pending U1 (10x-dev).

### 2.3 F1 consolidated disposition

- Runbook: **AUTHORED** (committable today).
- Alarm: **LEAVE-COMMENTED** until U1 clears.
- Paired G9 status: **CONDITIONAL-PASS-QUALIFIED** — the qualification is specific and small (one emission-wiring task, 10x-dev-scoped, not SRE-scoped).

## 3. F2 disposition — Migration 024 staging alembic replay

Full: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-F2-migration-024-staging-replay-design-2026-04-22.md`

**Verdict**: `BLOCKED-ON-STAGING-INFRA`.

**What was produced**:
- 12-step replay procedure adapted from `runbooks/PRODUCTION-DATABASE.md` ECS-exec pattern (DSN via Secrets Manager; Phase A/B/C mirror the local audit).
- 6 pre-flight gates: RDS snapshot / `lock_timeout=5s` / no-writers / deploy-freeze / IC-awareness / staging DSN verification.
- 9-row PASS/FAIL table.
- Ordered §5A/5B/5C rollback decision tree (no-improvisation rule).
- Two-tier CI plan: v1 one-shot manual → v2 ephemeral `postgres:15-alpine` service container on `workflow_dispatch` (explicitly NOT against real staging RDS — that stays manual).

**Why BLOCKED-ON-STAGING-INFRA**:
- `terraform/environments/` has **only** `production/` — no staging workspace materialized.
- `variables.tf` accepts `staging` as legal but no tfvars/RDS/backend is present.
- `PRODUCTION-DATABASE.md` has no staging analogue.
- No `autom8y/auth/db-password-staging` Secrets Manager path confirmed.

**Unblock ask** (routed to SRE infra / fleet-potnia via §4.2 follow-up handoff):
- Confirm staging RDS existence + Secrets Manager path + ECS cluster/service names — OR confirm "no staging" is permanent. If permanent, verdict collapses to `REPLAY-READY-MANUAL-V1` against ephemeral-CI-Postgres only (no staging promotion, which is acceptable given F2 priority is LOW per HANDOFF §4).

**Ship-gate impact**: none. F2 was scope-deferred at merge; the deferral remains defensible.

## 4. New finding (re-review surfaced)

### 4.1 Emission-wiring gap (systemic, beyond CW-4)

F1a identified that `emit_issuance_with_scope` and `emit_token_exchange_outcome` are both declared-but-never-called in production code. This is broader than the single CW-4 alarm residual:

- The telemetry-plane contract is **partially paper** — the helpers and metric-name constants exist, the alarm topology exists, but the token-exchange code path does not call them.
- This does NOT regress PR #131's four other alarm-runbook pairs (CW-1 revocation replay, CW-2a PKCE, CW-2b device, CW-3 redirect-uri) — those pairs have their emission-side wired at merge. Only CW-4's emission side is phantom.
- This does NOT re-open G9. The HANDOFF-RESPONSE §3 row G9 was scored CONDITIONAL-PASS on the basis that four pairs shipped + one deferred. The emission-wiring gap is a property of the deferred pair, not a property of the four shipped pairs.

### 4.2 Follow-up handoffs emitted

- **To 10x-dev** (new): `HANDOFF-sre-to-10x-dev-cw4-emission-wiring-2026-04-22.md` requesting emission-wiring work at token-exchange callsite (U1 from §2.1). Priority LOW; non-blocking for Phase A retirement close. See §6 for handoff frontmatter and item.
- **To fleet-potnia / SRE infra** (new, coupled with F2): `HANDOFF-sre-to-fleet-potnia-staging-infra-clarification-2026-04-22.md` asking whether staging environment is intended-to-exist or not (§3 unblock ask). Priority LOW.
- **To ecosystem rite** (sidecar): `canonical-source-integrity` N=4 → [STRONG] ratification request. See §7.

## 5. Ship-gate G1..G9 re-scored

| Gate | Original | Re-review | Delta |
|------|----------|-----------|-------|
| G1 SRE bundle `--no-ff` merged | PASS | PASS | — |
| G2 Lane M (M-1 / M-3 / R-1 / R-2 / D-9-2) | PASS | PASS | — |
| G3 Lane E (W-1..W-4 + flag + 429) | PASS | PASS | — |
| G4 Lane S (D-9-1 OpenAPI regen) | PASS | PASS | — |
| G5 CI 0-failure (17/17 green at merge) | PASS | PASS | — |
| G6 qa-adversary Sprint-3 verdict | PASS (GO-WITH-FLAGS) | PASS | — |
| G7 ADR-0006 two-tower invariant | PASS | PASS | — |
| G8 ADR-0007 ServiceClaims dual-field | PASS | PASS | — |
| G9 alarm-runbook pairs | CONDITIONAL-PASS | **CONDITIONAL-PASS-QUALIFIED** | runbook half closed; alarm-side gated on 10x-dev U1 |

Phase A retirement-baseline: **signed** at re-review close. No G1..G8 regression.

## 6. New handoff — emission-wiring to 10x-dev

```yaml
---
artifact_id: HANDOFF-sre-to-10x-dev-cw4-emission-wiring-2026-04-22
schema_version: "1.0"
source_rite: sre
target_rite: 10x-dev
handoff_type: execution
priority: low
blocking: false
initiative: autom8y-core-aliaschoices-platformization-phase-a
created_at: "2026-04-22T11:45Z"
status: pending
items:
  - id: CW4-EMIT-001
    summary: Wire auth.oauth.scope.cardinality emission at token-exchange callsite (currently declared-but-unused in token_exchange_cw_metrics.py).
    priority: low
    acceptance_criteria:
      - emit_issuance_with_scope() is called from /oauth/token success path once per successful token issuance, passing the scope string set observed.
      - ScopeCardinalityObserved metric-name constant either (a) added to token_exchange_cw_metrics.py and exposed as the CloudWatch metric name, or (b) alarm rewired to auth.oauth.scope.cardinality (consistent with the declared METRIC_OAUTH_SCOPE_CARDINALITY constant) — decision must be documented in the PR.
      - Test coverage added asserting emission fires on success path (reuse existing overflow test fixtures in tests/test_oauth_server_track.py).
      - After this lands, SRE re-activates CW-4 alarm via single-hunk uncomment at cloudwatch-alarms.tf:405-433 and removes the CW-4 "# (commented)" rationale block.
    notes: "Runbook auth-oauth-scope-cardinality.md already authored (CW-9); threshold-shape decision (A or B) is part of the acceptance criteria above."
evidence_grade: strong
---
```

## 7. Sidecar — canonical-source-integrity ratification request (to ecosystem rite)

### 7.1 Request

`canonical-source-integrity` throughline (`/Users/tomtenuta/Code/knossos/mena/throughlines/canonical-source-integrity.md`) is at **N_applied = 4** with grade `[MODERATE + rite-disjoint-specialist-corroborated]` and declared **ELIGIBLE for grade promotion to `[STRONG]`** per the registry's own `promotion_threshold` language (Pythia ruling 2026-04-17 agentId a43b8197cd7f46af7). The ceremonial gate is **ecosystem-rite ratification** OR S17 convergence attestation. This sidecar requests ecosystem-rite ratification.

### 7.2 Nodes cited in evidence chain

1. Node 1 (2026-04-17): bedrock-meta-extraction Transition-1.5 intercept; forge rite; 4 distinct anti-pattern writes prevented.
2. Node 2 (2026-04-20): autom8y-asana PLAYBOOK v2 Disposition B ratification; hygiene rite; commit `1a86007f`; rite-disjoint from Node 1.
3. Node 3 (2026-04-21): AP-9 materialization defect self-catching on workflows-stack-env-tag-reconciliation; rite-disjoint H-1 critic BLOCK verdict triggered canonical re-authoring. Recursive-dogfooding instance.
4. Node 4 (2026-04-21): val01b ADR-ENV-NAMING-CONVENTION.md with Decision 13 canonical-source-integrity clause; hygiene rite (val01b fleet-replan CC context); rite-disjointness of **authorship** at source-of-truth altitude (the authorship-rite disjointness that Node 3 alone did not satisfy).

### 7.3 What ratification means

- Grade transitions `[MODERATE + rite-disjoint-specialist-corroborated]` → `[STRONG]`.
- `status: CANDIDATE` → `status: RATIFIED`.
- Registry frontmatter updates reflected back across projections via `ari sync`.
- Blocks open: ceremonial-only — no new authorship required; Pythia's 2026-04-17 ruling already prescribed the conditions; the N=4 node already fired.

### 7.4 Requested Pythia action

Ecosystem-rite Pythia consult to:
1. Review Nodes 1-4 against promotion_threshold criteria (4-of-4 independence axes satisfaction).
2. Decide: ratify-to-STRONG / hold-at-ELIGIBLE-pending-S17 / REMEDIATE (if any independence axis analysis is contested).
3. On ratify: update `canonical-source-integrity.md` frontmatter (`status: STRONG`, `evidence_grade: "[STRONG]"`, update `corroboration_notes` with ratification bite) + trigger `ari sync`.
4. Emit ratification artifact at `/Users/tomtenuta/Code/a8/repos/.ledge/reviews/THROUGHLINE-RATIFICATION-canonical-source-integrity-2026-04-22.md` for audit trail.

### 7.5 Priority posture

LOW-urgency, HIGH-leverage. The N=4 bite has already been taken; the grandeur sits one ceremonial step from realization. Non-ratification does not regress anything; ratification captures yield already earned.

## 8. Provenance and evidence grades

| Claim | Source | Grade |
|-------|--------|-------|
| PR #131 merged at cedb9012 | git log autom8y/main | STRONG |
| 17/17 CI green at merge | GH Actions record | STRONG |
| G1..G8 re-review PASS | this artifact §5 + sub-artifacts | STRONG |
| CW-4 emission not wired | F1a sub-artifact grep-of-codebase evidence | STRONG |
| Overflow guard thread-safe + bounded | F1a sub-artifact code-read evidence | STRONG |
| Runbook auth-oauth-scope-cardinality.md authored | F1b sub-artifact + write confirmation | STRONG |
| Staging infrastructure absent | F2 sub-artifact terraform/environments/ audit | STRONG |
| canonical-source-integrity N_applied=4 | mena/throughlines/ registry frontmatter line 11 | STRONG |
| Grade promotion ELIGIBLE | mena/throughlines/ registry frontmatter + Pythia ruling 2026-04-17 | STRONG |

Evidence-grade ceiling: STRONG (this artifact re-reviews git-reproducible artifacts; no self-referential consultation).

## 9. Close

SRE rite signs Phase A post-merge re-review. G1..G8 PASS; G9 CONDITIONAL-PASS-QUALIFIED with small, scoped follow-up to 10x-dev. F2 dispositioned as BLOCKED-ON-STAGING-INFRA pending fleet-potnia clarification. Sidecar ratification request dispatched to ecosystem rite.

No action required of user other than routing: ratification handoff to ecosystem, emission-wiring handoff to 10x-dev, staging-infra handoff to fleet-potnia.

**Phase A retirement-baseline: SIGNED.**

---

*Emitted 2026-04-22T11:45Z by SRE rite main-thread (Potnia-role orchestration). Specialists: observability-engineer (F1a), incident-commander (F1b), platform-engineer (F2). Sidecar owner: ecosystem-rite Pythia.*
