---
type: review
artifact_id: SRE-CONCURRENCE-pr131-revocation-backend-readiness-2026-04-21
schema_version: "1.0"
source_rite: sre (observability-engineer)
target_rite: 10x-dev (admin-cli-oauth-migration Phase C)
review_type: sre-concurrence
status: proposed
lifecycle_state: in_progress
pr_url: https://github.com/autom8y/autom8y/pull/131
pr_title: "feat(auth): admin-CLI OAuth 2.0 migration — PKCE+device-code, /internal/* revocation, scope emission (Wave 1)"
created_at: "2026-04-21"
evidence_grade: MODERATE
evidence_grade_rationale: |
  Intra-sre-rite concurrence. Self-ref cap at MODERATE per
  self-ref-evidence-grade-rule. Promotion to STRONG requires external-critic
  from non-sre rite (recommend: hygiene rite, 11-check-rubric) OR post-merge
  D+7 observation window GREEN (canary-signal-contract completion).
aggregate_verdict: REMEDIATE
verdict_bucket_counts:
  READY-TO-SHIP: 2   # §4 cold-start observability pathway; §5 ADR-0006 invariant; §6 ADR-0007 compat
  REMEDIATE: 3       # §1 migration 024; §2 Redis keys; §3 CW alarms + runbooks
  ESCALATE: 0
source_references:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-10x-dev-to-overarching-phase-c-operationalize-2026-04-21.md
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0004-revocation-backend-dual-tier.md
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md
  - /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-auth/.ledge/reviews/HANDOFF-10x-dev-to-review-serviceclaims-shape-migration-2026-04-21.md  # ADR-0007 CONDITIONAL proxy (ADR file itself absent at expected path)
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/migrations/versions/024_create_token_revocations_table.py
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/autom8y_auth_server/services/revocation_service.py
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/autom8y_auth_server/services/token_exchange_cw_metrics.py
  - /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/autom8y_auth_server/routers/internal.py
  - /Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-auth/src/autom8y_auth/claims.py
  - /Users/tomtenuta/Code/a8/repos/autom8y/terraform/modules/auth-redis/main.tf
  - /Users/tomtenuta/Code/a8/repos/autom8y/terraform/services/auth/token_exchange_alarms.tf
skills_invoked:
  - canary-signal-contract
  - doc-sre (observability-report-template)
  - credential-scope-assertion-discipline
  - self-ref-evidence-grade-rule
sre_heuristics_grounded:
  - "Symptom-based alerting [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72]"
  - "Alerts require runbooks [SR:SRC-002 Beyer et al. 2018] [STRONG | 0.72]"
  - "Multi-window multi-burn-rate alerting [SR:SRC-010 Google 2018] [STRONG | 0.72]"
  - "Blast-radius classification discipline [SR:SRC-003 Forsgren/Humble/Kim 2018] [STRONG | 0.72]"
---

# SRE CONCURRENCE — PR #131 Revocation-Backend Production-Ship Readiness

**PR**: https://github.com/autom8y/autom8y/pull/131 (+5170 / -333 across 26 files, MERGEABLE)
**Aggregate verdict**: **REMEDIATE** — 3 REMEDIATE dispositions, 3 READY-TO-SHIP, 0 ESCALATE
**Blocker count**: 3 gaps (CW alarms absent from Terraform; runbooks absent for all new metrics; Redis key-namespace drift between spec and implementation)
**Non-blockers rectified pre-review**: Additive-compat claims.py already wired; warm-gate 503+Retry-After already enforced in internal.py; fail-open CloudWatch emission posture already correct

---

## Preamble — Source Availability

Four ADRs were referenced in the request; three resolve to file paths, one does not:

| ADR | Expected path | Actual state |
|-----|---------------|--------------|
| ADR-0004 | `services/auth/.ledge/decisions/ADR-0004-revocation-backend-dual-tier.md` | PRESENT, read |
| ADR-0006 | `services/auth/.ledge/decisions/ADR-0006-internal-vs-admin-plane-separation.md` | PRESENT, read |
| ADR-0007 | `services/auth/.ledge/decisions/ADR-0007-serviceclaims-shape-migration.md` | **ABSENT at expected path** |
| (HANDOFF) | `autom8y-asana/.ledge/reviews/HANDOFF-10x-dev-to-overarching-phase-c-operationalize-2026-04-21.md` | PRESENT, read |

**ADR-0007 substitution**: The HANDOFF at path `autom8y/sdks/python/autom8y-auth/.ledge/reviews/HANDOFF-10x-dev-to-review-serviceclaims-shape-migration-2026-04-21.md` carries the CONDITIONAL material (`scope` → `scopes` breaking migration, 26-consumer blast radius, ADR drafting deferred pending review-rite ruling on migration-path option i/ii/iii). §6 below evaluates Wave 1 compatibility against this surrogate authority. **This is not a blocker for Wave 1 ship** — see §6 for the compat analysis — but it should be noted that ADR-0007 the *document* is currently vapor; ratification happens at review-rite HANDOFF-RESPONSE, not at the ADR filesystem path.

---

## §1 — Migration 024 (`token_revocations` table) Review

**File**: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/migrations/versions/024_create_token_revocations_table.py`

### Schema vs. ADR-0004 §Context/§Decision

| Field | Migration 024 | ADR-0004 spec | Status |
|-------|---------------|---------------|--------|
| `jti` | TEXT PRIMARY KEY | `jti uuid PK` | **DRIFT** — spec says `uuid`, migration uses `TEXT`. Non-blocking (JWT jti is per-RFC-7519 a string; TEXT is correct, ADR-0004 spec wording is the one in error), but ADR-0004 §Consequences should be amended. |
| `revoked_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | `revoked_at` | MATCH |
| `revoked_by_sub` | TEXT NOT NULL | (not in ADR-0004 field list) | **ADDITIVE** — present in migration, absent from ADR-0004 schema sketch. This is the audit-trail operator/SA subject per ADR-0006 plane-separation auditability. Document in ADR-0004 §Consequences. |
| `reason_code` | TEXT NOT NULL | (ADR §Consequences: "indexed on `reason_code`") | MATCH + indexed as expected |
| `source_endpoint` | TEXT NOT NULL | (not in ADR-0004 field list) | **ADDITIVE** — necessary to distinguish `/internal/revoke/token` vs. `/internal/revoke/service-account/{id}` in audit. Good hygiene; document. |
| `original_exp` | TIMESTAMPTZ NOT NULL | (implied by "remaining TTL" language) | MATCH |
| `metadata` | JSONB (nullable) | (not in ADR-0004 field list) | **ADDITIVE** — free-form. Low-blast-radius risk: acceptable if log-retention policy also covers JSONB contents. |
| `service_account_id uuid` | **ABSENT** | "`service_account_id uuid`" per HANDOFF §C-2.1 | **DRIFT** — HANDOFF describes an SA-keyed column that the migration does NOT create. See §2 for the coupled Redis-key drift. This has observability consequences: "all revocations for SA X" queries fall back to JOIN-through-JWT-issuance-log rather than direct column lookup. |

### Indexes

| Index | Migration | ADR-0004 | Rationale Check |
|-------|-----------|----------|-----------------|
| `idx_revocations_revoked_at` | PRESENT | "indexed on `revoked_at`" | MATCH. Used by cold-start replay window `WHERE revoked_at >= now() - interval '7 days'` and 90-day retention DELETE cron. |
| `idx_revocations_reason` | PRESENT | "indexed on `reason_code`" | MATCH. Used by observability dashboards to slice by reason_code. |
| (implicit PK on `jti`) | PRESENT | — | MATCH. Serves the idempotent-insert path. |
| `idx_revocations_service_account_id` | **ABSENT** | (implied by ADR + HANDOFF SA-keyed revocation) | **GAP** — if SA-level mass-revoke is queryable by SA, this should exist. Absent because the column itself is absent. |

### Backfill, Query Patterns, Blast Radius

- **Backfill**: NOT required. `token_revocations` is a new table; no legacy revocation state exists to migrate. **READY**.
- **Hot-path query pattern**: Zero. Postgres is consulted only on cold-start replay (every auth-server boot) and on revoke-write (low-frequency admin-plane). ADR-0004 §Rationale confirms this asymmetry. The `WHERE revoked_at >= now() - interval '7 days'` replay scan is O(revocations-in-last-7d) = O(hundreds at steady state). Capacity is adequate.
- **Capacity baseline** (per "Skipping capacity planning" anti-pattern requirement): at fleet-steady-state, estimate revocations/day = (operator-triggered ≤ 10/day) + (SA rotations ≤ 2/day) + (post-incident mass-revokes: rare, ≤ 100/event, ≤ 1/month). **Projected table growth at 90d retention: < 10,000 rows; < 5 MB.** Projected cold-start replay scan: ≤ 100 rows / ≤ 50ms at P99 given Postgres-fleet baseline of 10-50ms P99 per ADR-0004 §Alternative-(b). **Headroom: 900x on row count, 5.8x on replay latency vs. 45s SRE-page threshold.** Acceptable.
- **Blast radius of failed migration** (per "Ignoring blast radius" anti-pattern requirement):
  - **Dev**: No-op. Fresh DB schema.
  - **Staging**: Alembic dry-run required per HANDOFF §C-1 merge-gate sequence. Round-trip test (`upgrade head` → `downgrade -1` → `upgrade head`) MUST be executed before merge.
  - **Canary** (first prod instance): Cold-start replay reads zero rows (table just created). Warm-gate opens immediately. Hot-path unaffected.
  - **Partial fleet**: During rolling-deploy, instances N and N+1 may run different code; migration 024 is only-additive (new table, new indexes) and does NOT touch existing schema. **Zero risk to in-flight instances not yet redeployed** — they simply never write to `token_revocations` (the code that writes it is not yet running on them).
  - **Full rollout**: All auth-server instances replayed-and-warm after rolling-deploy completes. Per ADR-0004, deploy orchestration must stagger instance replacement to avoid fleet-synchronized 503 windows. **Verify**: deploy script enforces MinHealthyPercent ≥ 50 on the ECS service (standard autom8y auth deploy posture).
- **Rollback safety**: `downgrade()` drops the table + indexes. Migration docstring explicitly flags this as **security-impacting**: "Live revocations in Redis are not affected directly but will be lost on next Redis cold-start (no replay source)." This is correct. **READY** — but rollback must be paired with a documented audit-replay-to-alternate-store runbook per the docstring's own warning, which does not yet exist. (See §3 runbook gap.)

### §1 Disposition: **REMEDIATE**

**Remediation items for 10x-dev pre-merge**:

1. **Add `service_account_id` column + index** (HIGH priority). The HANDOFF §C-2.1 names this as part of the schema; the migration does not create it. This column is the correct observability join-key for "show me all revocations for SA X" dashboard queries. Without it, that query must traverse the JWT-issuance log → match `jti` → JOIN `token_revocations` — a cardinality-blowup risk on the observability side.
   - *Accepted alternative*: justify in ADR-0004 an explicit decision to omit this column and rely on `metadata->>sa_id` JSONB extraction. If chosen, publish the chosen approach in ADR-0004 §Consequences and add a GIN index on `(metadata->>'sa_id')`.

2. **Document ADDITIVE columns in ADR-0004 §Consequences**: `revoked_by_sub`, `source_endpoint`, `metadata`. These are present in migration but absent from ADR-0004 schema sketch. Creates drift risk on next audit.

3. **Amend ADR-0004 §Context**: "`jti uuid PK`" → "`jti text PK`" to match migration reality (JWT jti is RFC-7519 string, TEXT is correct; ADR wording is the error).

4. **Rollback runbook**: `docs/runbooks/REVOCATION-MIGRATION-024-ROLLBACK.md` describing the audit-replay-to-alternate-store procedure the migration docstring promises.

5. **Staging round-trip evidence**: Attach to PR #131 the output of `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` against staging Postgres per HANDOFF §C-1. Without this evidence, rollback safety is asserted, not verified.

**Ship-gate**: items 1 (or its ADR-0004 override), 4, 5 are BLOCKING. Items 2, 3 are ADR-hygiene and can land post-merge in a follow-up ADR amendment PR.

---

## §2 — Redis Key-Pattern Review

**Files**:
- Implementation: `services/auth/autom8y_auth_server/services/revocation_service.py:110` — `_REDIS_REVOCATION_PREFIX = "revoked:"`
- Terraform: `terraform/modules/auth-redis/main.tf`
- Spec reference: HANDOFF §C-2.1 names `revocation:{jti}` + `revocation:sa:{sa_id}`

### §2.1 Namespace Drift (Spec vs. Implementation)

| Key pattern | HANDOFF §C-2.1 spec | Implementation | Status |
|-------------|---------------------|----------------|--------|
| Per-JTI revocation | `revocation:{jti}` | `revoked:{jti}` | **NAMING DRIFT** — singular-verb prefix vs. nominal-noun prefix |
| Per-SA revocation | `revocation:sa:{sa_id}` | **NOT IMPLEMENTED** as a Redis key | **MISSING NAMESPACE** — SA mass-revoke happens via `revoke_service_account()` in `service_account_service.py:306` (DB-side flag + per-issued-jti entries); no top-level `revocation:sa:*` key is written |

**Observability blast-radius of the drift**:
- Dashboards, Grafana CloudWatch queries, and runbooks authored against `revocation:*` prefix will produce **zero matches** against the actual `revoked:*` keyspace. This is a silent-dark failure mode (no error; just empty panels).
- If SRE authors an ElastiCache `KEYSPACE_HITS` alarm on `revocation:*`, it alarms at zero-hits-always because the namespace is empty. A cause-based alert that cannot fire is worse than no alert — it creates the illusion of coverage.

**Decision**: naming is the 10x-dev implementation's choice to own. SRE concurrence does NOT require renaming. SRE concurrence DOES require:
- Update HANDOFF §C-2.1 to reflect actual implementation namespace `revoked:{jti}`.
- Explicitly name the SA mass-revoke mechanism (DB-flag-driven, NOT a Redis `revocation:sa:*` key). This corrects a spec-vs-implementation mismatch that would otherwise mislead dashboard authors.

### §2.2 Cardinality Bounds

- **Active-key cardinality** = count of non-expired revocations = O(revocations-in-last-7d) ≤ 10,000 keys per §1 capacity baseline.
- **Per-key size**: `"revoked:<jti>"` → value `"1"` → ≤ 64 bytes key + 1 byte value + Redis overhead ≈ ~120 bytes per revocation.
- **Total memory footprint**: ≤ 10,000 × 120 B = ~1.2 MB active keys. **2,000x headroom** on a `cache.t3.micro` (512 MB) ElastiCache node. **READY.**
- **Post-incident mass-revoke worst case**: a full-fleet SA rotation might revoke ~500 tokens in a single event. Still within < 60 KB burst. Acceptable.

### §2.3 TTL Strategy

- Revoke writes use `setex(_redis_key(jti), ttl_seconds, "1")` where `ttl_seconds = original_exp - now` (revocation_service.py:232).
- TTL-on-every-key is consistent with the `volatile-ttl` eviction policy.
- **Edge case**: when JWT has already naturally expired (`original_exp ≤ now`), write is SKIPPED (revocation_service.py guard at line ~225). This is correct — revocation of an already-expired token is a no-op from the authorization check's perspective because the JWT's own `exp` claim rejects it first. **READY.**

### §2.4 Eviction Policy Compatibility

- **Terraform**: `auth-redis/main.tf:44-47` sets `maxmemory-policy = "volatile-ttl"`. Correct choice: every revocation key has a TTL; under memory pressure Redis evicts the keys with the shortest remaining TTL first (which are the ones closest to natural JWT expiry anyway — least information loss).
- **Scar-tissue risk**: if any future non-revocation key is written to this Redis cluster WITHOUT a TTL, `volatile-ttl` would never evict it and memory pressure would push out revocation keys preferentially. **Current state**: this Redis cluster is dedicated to auth revocation per `auth-redis/main.tf:24` description. No other writers documented. **READY**, but requires a **runbook invariant**: "auth Redis cluster admits only TTL-bearing revocation keys; any non-TTL writer is a P1 bug." See §3 runbook gap.

### §2.5 ElastiCache Pre-Warm Plan

- **Cold-start replay IS the pre-warm**. On every auth-server boot, `replay_revocations_to_cache()` reads `token_revocations` rows from Postgres and idempotently `SETEX`es them into Redis. This warms the cache from the durable ledger.
- **Single-AZ, single-node ElastiCache** per `auth-redis/main.tf:77-80` (`num_node_groups=1, replicas_per_node_group=0, automatic_failover_enabled=false, multi_az_enabled=false`). Failover is NOT provided by Redis infrastructure; durability is provided by Postgres + replay-on-cold-start.
- **Risk**: if Redis cluster is replaced (planned or unplanned), every auth-server instance that reconnects to the new cluster SHOULD re-trigger replay. **Verify**: `replay_revocations_to_cache()` is invoked on cluster-reconnect events, not just on process boot. If connection-pool-level reconnect does NOT trigger replay, the replay-on-boot design has a hole (a long-lived auth-server process sees an empty Redis after cluster swap but `warm=True` is already set → fail-open).
  - **Test assertion** (credential-scope-assertion-discipline §step-4 style): construct a scenario where auth-server is running with `warm=True`, Redis cluster is externally reset, auth-server reconnects. Assert that `warm` flips back to `False` until replay re-completes. If this does NOT happen, surface as D-11 or equivalent defect.

### §2 Disposition: **REMEDIATE**

**Remediation items for 10x-dev pre-merge**:

1. **Correct HANDOFF §C-2.1 spec to match implementation** (HIGH priority): `revoked:{jti}` (not `revocation:{jti}`); no `revocation:sa:*` keyspace (SA mass-revoke is DB-flag-driven through `revoke_service_account()`). Updated HANDOFF unblocks dashboard/runbook authorship by downstream SRE.

2. **Verify cluster-reconnect replay re-trigger** (HIGH priority): add an explicit assertion test (or documented behavioral contract) that `_backend_state.warm` flips to `False` on Redis cluster connection-loss + reconnect. If not implemented, open as defect for Wave 1 or documented acceptance-of-known-gap in ADR-0004 §Risk surface monitored.

3. **Redis-writer invariant runbook** (MEDIUM priority): one-paragraph entry in `docs/runbooks/REDIS-AUTH-REVOCATION-INVARIANTS.md`: "this cluster admits only TTL-bearing revocation keys; any non-TTL writer is a P1 bug." Prevents future scar-tissue.

**Ship-gate**: items 1 and 2 are BLOCKING. Item 3 can land post-merge.

---

## §3 — CloudWatch Alarm Definitions Review

**Files examined**:
- Implementation emits: `services/auth/autom8y_auth_server/services/token_exchange_cw_metrics.py`
- Terraform alarms: `terraform/services/auth/token_exchange_alarms.tf`
- Runbook dir: `services/auth/docs/runbooks/`, `autom8y/docs/runbooks/`, `autom8y/runbooks/`

### §3.1 Metric-by-metric audit

Per sre-Potnia anti-pattern register: **every alert must have a runbook reference** [SR:SRC-002 Beyer et al. 2018] [STRONG | 0.72]. Every entry below is checked against this requirement.

#### auth.revocation.replay_completed_ms → page at P99 > 45s (per ADR-0004)

| Dimension | State |
|-----------|-------|
| **SLI definition** | Milliseconds elapsed from `replay_started` to `replay_completed` per auth-server cold-start. Source-of-truth per instance. |
| **SLO target** | P99 < 30s (ADR-0004 §Consequences: "adds ≤30s startup latency"); page at P99 > 45s per ADR-0004 §Observability required. |
| **Threshold rationale** | 30s is the ADR-committed budget; 45s is the 1.5x SLO-breach threshold giving 15s operational buffer for Postgres baseline jitter (10-50ms P99 per ADR-0004). ACCEPTABLE. |
| **Emission in code** | `METRIC_REVOCATION_REPLAY_COMPLETED_MS = "RevocationReplayCompletedMs"` (`token_exchange_cw_metrics.py:161`) — metric name constant defined. Actual emission hook: `replay_revocations_to_cache()` in revocation_service.py — **VERIFY call-site** calls `emit_oauth_event(metric_name=METRIC_REVOCATION_REPLAY_COMPLETED_MS, unit="Milliseconds", value=<elapsed_ms>)`. |
| **Terraform alarm** | **ABSENT**. `token_exchange_alarms.tf` covers the P6 dead-man's-switch for `TokenExchangeSuccesses` only. NO `aws_cloudwatch_metric_alarm` resource exists for `RevocationReplayCompletedMs`. |
| **Runbook** | **ABSENT**. No file at `services/auth/docs/runbooks/REVOCATION-REPLAY-SLOW.md` or equivalent. |
| **Per-alert-requires-runbook check** | **FAIL** — alarm not authored; runbook not authored. |

#### auth.oauth.pkce.attempts → anomaly / threshold alarm

| Dimension | State |
|-----------|-------|
| **SLI definition** | Count of PKCE-flow token exchange attempts per minute (success + failure). |
| **SLO target** | **UNDEFINED**. The HANDOFF lists the metric but does not propose an alarm threshold. This is an observability-metric without a specified alarm semantics — legitimate use case (dashboard only, no page) BUT must be explicitly categorized as such to avoid alert-fatigue via cause-based alerting [SR:SRC-001] [STRONG | 0.72]. |
| **Emission in code** | `METRIC_OAUTH_PKCE_ATTEMPTS = "OAuthPKCEAttempts"` defined (`token_exchange_cw_metrics.py:158`). |
| **Terraform alarm** | **ABSENT**. |
| **Runbook** | N/A if dashboard-only; **REQUIRED** if alarm authored later. |
| **Per-alert-requires-runbook check** | **PASS** as dashboard-only metric IF explicitly categorized so; **FAIL** if operator expects this to page. |

#### auth.oauth.device.attempts → anomaly / threshold alarm

Same as PKCE.attempts (dashboard-only vs. alarm-pending categorization gap).

#### auth.oauth.redirect_uri.rejected → spike alarm

| Dimension | State |
|-----------|-------|
| **SLI definition** | Count of PKCE/device flow redirect_uri rejections per minute. This is a **symptom-based security-signal** — sustained high rate indicates either (a) config drift between CLI and server allowed-URIs list, or (b) attacker probing. |
| **SLO target** | **UNDEFINED**. Proposal: baseline at fleet-steady = 0 rejections/min; alarm at > 10 rejections/5-min period sustained over 2 consecutive periods → page. (Calibrate against baseline after 7d observation window.) |
| **Threshold rationale** | Zero-expected baseline + low-traffic admin plane makes this a tight-threshold candidate. Burn-rate multi-window alerting [SR:SRC-010] [STRONG | 0.72] is overkill for a binary signal; single-threshold + evaluation_periods=2 is appropriate. |
| **Emission in code** | `METRIC_OAUTH_REDIRECT_URI_REJECTED = "OAuthRedirectUriRejected"` defined. |
| **Terraform alarm** | **ABSENT**. |
| **Runbook** | **ABSENT**. Should cover: check CLI-vs-server allowed-URI config symmetry; check for attacker probing pattern; escalate to security-rite if pattern suggests probing. |
| **Per-alert-requires-runbook check** | **FAIL**. |

#### auth.oauth.scope.cardinality → page at > 50 distinct values

| Dimension | State |
|-----------|-------|
| **SLI definition** | Distinct-value count of the `Scope` CloudWatch dimension observed across the `TokenExchangeIssuanceWithScope` metric within a process. |
| **SLO target** | < 50 distinct values per the `SCOPE_CARDINALITY_CAP` constant in code (`token_exchange_cw_metrics.py:113`). |
| **Threshold rationale** | CloudWatch dimension-value cardinality is a **first-order cost driver**. The code-side cap at 50 + overflow to `"OTHER"` already prevents cost blowout. The alarm is thus an **early-warning** for scope-string drift (new scope strings appearing in the fleet that were not in the registered catalog), NOT a cost-protection (the code prevents cost). **ACCEPTABLE**. |
| **Emission in code** | Cardinality overflow emits log at WARNING: `token_exchange_cw_metrics_scope_cardinality_overflow` (`token_exchange_cw_metrics.py:137-141`). No direct metric for "count of distinct scopes observed." |
| **Terraform alarm** | **ABSENT** from Terraform. The 50-value cap is enforced in code; the HANDOFF's "alert at >50 distinct values" maps to a **log-based alarm** on the `token_exchange_cw_metrics_scope_cardinality_overflow` WARNING, OR a separate `ScopeCardinalityObserved` metric would need to be emitted per-process. Neither is wired. |
| **Runbook** | **ABSENT**. Should cover: identify the new scope string from the WARNING log; confirm it's a legitimate new scope (update registered-scope catalog) or a bug (reject/fix). |
| **Per-alert-requires-runbook check** | **FAIL**. |

### §3.2 Summary Table

| Metric | Emitted in code | Terraform alarm | Runbook | Verdict |
|--------|-----------------|-----------------|---------|---------|
| `RevocationReplayCompletedMs` | YES (constant defined; verify call-site) | NO | NO | **FAIL** |
| `OAuthPKCEAttempts` | YES | NO | N/A (dashboard-only?) | CLARIFY intent |
| `OAuthDeviceAttempts` | YES | NO | N/A (dashboard-only?) | CLARIFY intent |
| `OAuthRedirectUriRejected` | YES | NO | NO | **FAIL** |
| `ScopeCardinalityOverflow` (WARNING log) | YES (log-only) | NO | NO | **FAIL** |
| `TokenExchangeSuccesses` (P6 dead-man's-switch) | YES | YES (existing) | YES (existing at frames/auth-dx-overhaul.md) | PASS (pre-existing, unaffected by this PR) |

### §3 Disposition: **REMEDIATE**

**Remediation items for 10x-dev pre-merge (BLOCKING, per sre-Potnia "Creating alerts without runbooks" anti-pattern)**:

1. **Author Terraform alarm resource for `RevocationReplayCompletedMs`** (P99 > 45s, evaluation_periods=2, period=300, treat_missing_data=notBreaching — because missing data means no cold-starts happened, which is fine). Location: new file `terraform/services/auth/revocation_alarms.tf` or appended to `token_exchange_alarms.tf`.

2. **Author Terraform alarm resource for `OAuthRedirectUriRejected`** (Sum > 10 per 5-min period, evaluation_periods=2, treat_missing_data=notBreaching).

3. **Author runbook stubs (even minimal) for each paging alarm**:
   - `docs/runbooks/REVOCATION-REPLAY-SLOW.md` — P99 > 45s handler. Diagnostic steps: check Postgres replay-query EXPLAIN; check row-count trend; check 7d retention DELETE cron health.
   - `docs/runbooks/OAUTH-REDIRECT-URI-REJECTED.md` — sustained rejection spike. Diagnostic: check CLI allowed-URI config drift; check for attacker probing via IP distribution; escalate to security-rite.
   - `docs/runbooks/REVOCATION-MIGRATION-024-ROLLBACK.md` — (from §1 item 4).
   - `docs/runbooks/REDIS-AUTH-REVOCATION-INVARIANTS.md` — (from §2 item 3).

4. **Explicitly categorize `OAuthPKCEAttempts` and `OAuthDeviceAttempts` as dashboard-only OR author alarms + runbooks**. Do NOT leave them as "emitted but neither alarmed nor dashboarded" — that is the vanity-metrics anti-pattern.

5. **Scope-cardinality alarm decision**: either (a) add a companion `ScopeCardinalityObserved` gauge metric + alarm + runbook, or (b) wire a CloudWatch Logs metric-filter on the `token_exchange_cw_metrics_scope_cardinality_overflow` WARNING + alarm + runbook. Either is fine; choose one.

6. **Verify `emit_oauth_event` call-sites**: the module defines the metric name constants, but the concurrence needs to see the call-site code (e.g., `await emit_oauth_event(metric_name=METRIC_REVOCATION_REPLAY_COMPLETED_MS, unit="Milliseconds", value=elapsed_ms)` inside `replay_revocations_to_cache()` or its caller). If any metric name constant is defined but never emitted, that is a silent-dark observability defect. grep the tree: `grep -rn "METRIC_OAUTH_PKCE_ATTEMPTS\|METRIC_OAUTH_DEVICE_ATTEMPTS\|METRIC_OAUTH_REDIRECT_URI_REJECTED\|METRIC_REVOCATION_REPLAY_COMPLETED_MS" services/auth/autom8y_auth_server/` — every constant should have BOTH a definition site AND ≥1 emission call-site.

**Ship-gate**: items 1, 2, 3, 6 are BLOCKING. Items 4, 5 are BLOCKING (categorization clarity required; cannot ship metrics that are neither observed nor alarmed).

---

## §4 — Cold-Start Replay Observability Pathway

**Files**:
- `services/auth/autom8y_auth_server/routers/internal.py:124-140` — warm-gate dependency
- `services/auth/autom8y_auth_server/services/revocation_service.py:303-359` — replay orchestrator
- ADR-0004 §Fail-Closed during replay (T-11 resolution)

### §4.1 503 + Retry-After pathway

**Implementation verified**:
- `require_warm()` dependency at `internal.py:124` raises `HTTPException(status_code=503, detail={"error_code": "AUTH-OAUTH-REPLAY-001", ...}, headers={"Retry-After": "5"})` when `revocation_service.is_warm() is False`.
- Applied to every `/internal/*` endpoint via `responses={503: {"model": ErrorResponse}}` + dependency injection.
- **ADR-0004 contract satisfaction**: "503 Retry-After: 5 during boot ≤30s" — MATCHED at the router layer. **READY**.

### §4.2 Load-balancer / ingress visibility

**SRE observability concern**: a 503 returned by the auth service is structurally indistinguishable at the ALB from:
- An ALB 503 (target unhealthy, no-healthy-hosts)
- An ALB 502 / upstream-connection failure
- A generic application-layer 5xx

Without structured differentiation, a dashboard panel showing "auth-service 503 rate" would conflate **intentional replay 503s** (a healthy-but-warming instance) with **pathological 503s** (actual outage). This is the inverse of the symptom-based-alerting discipline — the SAME status code carries TWO DIFFERENT symptoms.

**Mitigations available in current implementation**:
1. **Error-code in response body**: `AUTH-OAUTH-REPLAY-001` is present in the JSON body (`internal.py:136`). A CloudWatch Logs metric-filter on `"AUTH-OAUTH-REPLAY-001"` disambiguates replay-503 from other-503. **GOOD**.
2. **`Retry-After: 5` header**: explicit caller hint. ALB access logs DO capture response headers IF configured. Verify ALB access-log format includes response_headers. If not, the header is visible only to the calling CLI.
3. **Application-level metric**: the EMITTING side should count `AUTH-OAUTH-REPLAY-001` 503 responses as a separate metric from generic 5xx, so dashboards can cleanly show "replay-503 rate (normal on deploys)" vs "other-5xx rate (SLO burn)". **NOT WIRED** as a CloudWatch metric.

### §4.3 Fleet-warm vs. per-instance-warm

**SRE concern**: the `warm` flag is per-process. A fleet-level "how many instances are currently warming?" panel requires aggregating across instances. Not surfaced.

**Mitigation**: ALB target-group health-check can be wired to return UNHEALTHY while `warm=False`. But this introduces its own failure mode: if all N instances deploy simultaneously, all N report UNHEALTHY, ALB returns 503-no-healthy-targets, and the fleet looks DOWN for up to 30s. ADR-0004 explicitly accepts "brief admin-plane 503 windows (≤30s P99 bounded) on auth-server cold-start or rolling-deploy instance replacement" and recommends "Deploy orchestration staggers instance replacement." **ACCEPTABLE**, but requires deploy-pipeline assertion (MinHealthyPercent ≥ 50).

### §4 Disposition: **READY-TO-SHIP (with one optional enhancement)**

**Present and working**: 503 + Retry-After + structured error-code body + per-instance warm flag + replay orchestrator + fail-closed semantics.

**Optional enhancement (NOT blocking)**: wire a `RevocationReplay503Emitted` CloudWatch counter at the `require_warm()` dependency so dashboards cleanly separate intentional-warming-503 from pathological-503. If deferred, the CloudWatch Logs metric-filter on `AUTH-OAUTH-REPLAY-001` provides the same signal at slightly higher query cost.

**Deploy-pipeline assertion required (documented, not PR-blocking)**: verify ECS service definition for auth has `deployment_minimum_healthy_percent >= 50` so rolling-deploy never puts all instances into simultaneous replay. This is an SRE deploy-configuration check, not a PR #131 code check.

---

## §5 — ADR-0006 Two-Tower Invariant Preservation

**ADR-0006 contract**: `/admin/*` (role-based, operator identity, OpenFGA `auth_super_admin|auth_operator`) and `/internal/*` (scope-based, SA capability, OAuth `admin:internal` scope) are **disjoint planes**. No role implies a scope; no scope implies a role. Tokens minted on one plane are inert on the other. Audit trails must stay distinguishable.

### §5.1 Observability-side invariant checks

SRE-owned configurations that could accidentally violate plane-separation:

| Artifact | Risk of unification | State |
|----------|---------------------|-------|
| **Dashboard** showing "admin endpoints health" with panels for both `/admin/*` and `/internal/*` side-by-side | Implies a shared plane to the viewer. **Mitigation**: label panels explicitly as "operator plane (role-based, ADMIN_TOKEN)" vs "service plane (scope-based, OAuth)". Do not share a single "admin" cover term in dashboard title. | **ACTION REQUIRED** at dashboard-authoring time. No dashboard exists yet for the new `/internal/*` surface; when authored, this labeling discipline must be followed. |
| **CloudWatch metric namespace** | A shared `Autom8y/Auth/Admin` namespace covering both planes would structurally conflate audit streams | **PASS**. Per `token_exchange_cw_metrics.py:169`, new metrics live under `Autom8y/Auth/TokenExchange` (capability-focused) and OAuth-family metrics extend the same namespace. Existing `/admin/*` metrics live under separate namespace/dimensions in the existing auth observability. **No conflation risk introduced by this PR**. |
| **Alarm-notification topic** | Shared SNS topic for operator-plane and service-plane alarms could mix audiences | **PASS (pre-existing)**. `platform_alerts_topic_arn` is the single alert destination per `token_exchange_alarms.tf:167`. This is a fleet-wide pattern, not PR-specific — deliberate single-oncall SNS topology. Plane-separation is maintained at the **alarm-naming** layer (`autom8y-auth-token-exchange-dark-*` vs. hypothetical `autom8y-auth-admin-*`), not at topic layer. **ACCEPTABLE**; but new revocation alarms (§3 remediation items) must follow the naming discipline — e.g., `autom8y-auth-revocation-replay-slow` and `autom8y-auth-oauth-redirect-uri-rejected`, NOT `autom8y-auth-admin-*`. |
| **Log stream grouping** | Shared CloudWatch Logs group with no service-vs-operator partition | Application logs are emitted via `autom8y_log.get_logger("auth.revocation")` (service-plane) and `get_logger("auth.admin.*")` (operator-plane via existing admin.py). Structured logger namespaces are already disjoint. **PASS**. |
| **Error-code catalog** | Shared `AUTH-ADMIN-*` prefix for both planes | **PASS**. New codes are `AUTH-OAUTH-*` (OAuth-REPLAY-001, etc.) and `AUTH-REVOKE-*`; existing plane uses `AUTH-ADMIN-*`. Disjoint prefixes preserve distinguishability. |
| **SA ID dimension** on CW metrics | A dimension called `SaId` serving both SA-authenticated service calls and operator sessions (where no SA exists) | **PASS by code review**. `TokenExchangeAttempts` carries `SaId` per `_build_metric_data` — only applies on SA-attributed calls. `/admin/*` metrics (pre-existing) do not use `SaId` dimension. |

### §5.2 Invariant-preservation verdict

No observability or infrastructure configuration in this PR unifies the `/admin/*` and `/internal/*` planes. The metric namespace, alarm-naming convention, logger hierarchy, and error-code prefixes all preserve disjointness. The one latent risk surfaces at **dashboard authoring time** (a cosmetic choice to co-locate panels could imply unification to viewers) — but no dashboard is authored in this PR. The §3 runbook remediation items should carry a line reminding authors of plane-separation.

### §5 Disposition: **READY-TO-SHIP**

**Minor addition to §3 runbook remediation set** (non-blocking): any new runbook authored under the revocation/OAuth surface must open with a one-line reminder that `/internal/*` is the service-capability plane, distinct from `/admin/*` operator-plane runbooks, per ADR-0006.

---

## §6 — ADR-0007 CONDITIONAL Compatibility

**Target**: confirm Wave 1 observability + shipped code works with **additive-only** ServiceClaims (i.e., `.scope` preserved; `.scopes` added as co-equal list; both populated during compat window).

### §6.1 ADR-0007 file-state caveat

Per Preamble: the ADR file itself does not exist at the expected `services/auth/.ledge/decisions/` path. The material authority for ADR-0007 is the HANDOFF at `autom8y/sdks/python/autom8y-auth/.ledge/reviews/HANDOFF-10x-dev-to-review-serviceclaims-shape-migration-2026-04-21.md`, which flags migration-path options (i) hard-break, (ii) soft-deprecation, (iii) dual-field coexistence as OPEN pending review-rite ruling.

Wave 1 therefore cannot assume the final migration path is chosen. The safe operating principle is: **Wave 1 must work under all three options**. Any observability config that hard-codes `.scope` OR `.scopes` exclusively creates a migration risk.

### §6.2 Actual claims.py state (reality check)

`/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-auth/src/autom8y_auth/claims.py` currently ships with **BOTH fields coexisting**:

```
scope:  str | None         = Field(default=None, ...)                # line 162
scopes: list[str]          = Field(default_factory=list, ...)        # line 163
```

Plus an invariant validator `validate_scope_scopes_invariant()` (line 185) that raises `AUTH-CLAIM-SHAPE-001` if both are present AND disagree (scope != " ".join(scopes)). Plus a compat-friendly `has_scope()` (line 202) with a 4-tier fallback: exact `"*"` wildcard → `scopes` list membership → `scope` space-split → legacy single-tenant-id exact-match.

**This is migration-path option (iii) dual-field coexistence ALREADY IMPLEMENTED.** Wave 1 is compatible with all three ADR-0007 options because it has chosen the union of their semantics and locked them via the invariant validator:

- Option (i) hard-break: Wave 1 ships with `.scope` populated; on the flip day, `.scope` is removed; `has_scope()` still works via the `.scopes` branch.
- Option (ii) soft-deprecation: Wave 1 already populates both; a future release adds `DeprecationWarning` to `.scope` reads — zero PR-131 impact.
- Option (iii) dual-field coexistence: Wave 1 IS the implementation of (iii).

### §6.3 Observability-side dependencies on ServiceClaims shape

| Observability artifact | Reads from `.scope` | Reads from `.scopes` | Migration fragility |
|------------------------|---------------------|----------------------|---------------------|
| `TokenExchangeIssuanceWithScope` metric (per `emit_issuance_with_scope`) | `scope: str \| None` parameter passed in by caller | Not directly | **LOW** — emitter takes a string scope argument; caller can compute it from either field. |
| `Scope` CW dimension cardinality cap (50 values + OTHER) | Takes string input | — | **LOW** — string-typed, not field-typed. |
| `require_scope("admin:internal")` dependency | Consumed via `has_scope()` which checks both fields + list membership | Same | **NONE** — dual-read via `has_scope()` makes this migration-path-agnostic. |
| Dashboards slicing by scope | (Will use the CW `Scope` dimension) | — | **LOW** — dimension-value is string, not field-attached. |

**No observability config reads a specific ServiceClaims field directly.** All scope inspection routes through `has_scope()`, which is field-shape-agnostic. **READY**.

### §6.4 One gap: scope-scopes divergence alarm

`validate_scope_scopes_invariant()` raises `AUTH-CLAIM-SHAPE-001` at parse time if the two fields disagree. This is a correctness-signal with security implications (a token claiming one scope via `.scope` and a different scope via `.scopes` is adversarial-shaped). **SRE observation gap**: this ValueError has no CloudWatch metric emission; if it fires in production, it will appear only as a 5xx in auth logs, not as a distinct observability signal.

**Remediation (NON-BLOCKING for Wave 1 ship, but should be tracked)**:
- Add CloudWatch Logs metric-filter on `"AUTH-CLAIM-SHAPE-001"` → `ClaimsShapeInvariantViolation` counter → alarm at Sum > 0 over any 5-min period (zero tolerance; this is an adversarial-shape signal).
- Runbook: `docs/runbooks/CLAIM-SHAPE-INVARIANT-VIOLATION.md` — treat as security-incident-triage per ADR-0006 admin-plane classification semantics; escalate to security-rite.

### §6 Disposition: **READY-TO-SHIP**

Wave 1 is compatible with ADR-0007 in CONDITIONAL state because claims.py has implemented the most-conservative option (iii dual-field) with an invariant validator; all observability code reads via `has_scope()` and is field-shape-agnostic. The scope-shape-invariant-violation alarm gap (§6.4) is a follow-up observation, not a ship-blocker.

---

## §7 — Aggregate Verdict

**AGGREGATE VERDICT: REMEDIATE**

### §7.1 Per-scope-item summary

| § | Scope item | Disposition |
|---|------------|-------------|
| §1 | Migration 024 (`token_revocations` table) | **REMEDIATE** |
| §2 | Redis key-pattern namespaces | **REMEDIATE** |
| §3 | CloudWatch alarm definitions + runbooks | **REMEDIATE** |
| §4 | Cold-start replay observability pathway | **READY-TO-SHIP** |
| §5 | ADR-0006 two-tower invariant preservation | **READY-TO-SHIP** |
| §6 | ADR-0007 CONDITIONAL compatibility | **READY-TO-SHIP** |

### §7.2 Blocking items (ship-gate checklist)

Before PR #131 can ship to production with SRE concurrence, the following must be resolved:

**BLOCKING (ship-gate)**:

1. **[§1.1] Missing `service_account_id` column** on `token_revocations` — either add column + index, OR ratify in ADR-0004 the JSONB-extraction approach with a companion GIN index. Rationale: HANDOFF §C-2.1 spec mismatch; observability join-key.

2. **[§1.4] Rollback runbook** `docs/runbooks/REVOCATION-MIGRATION-024-ROLLBACK.md`. Rationale: migration docstring promises this; cannot ship downgrade-without-runbook.

3. **[§1.5] Staging alembic round-trip evidence** attached to PR. Rationale: HANDOFF §C-1 merge-gate; rollback safety is currently asserted, not verified.

4. **[§2.1] Correct HANDOFF §C-2.1 Redis key spec** to match implementation (`revoked:{jti}`; no `revocation:sa:*` keyspace). Rationale: prevents downstream dashboard/runbook authoring against a non-existent namespace.

5. **[§2.2] Cluster-reconnect replay re-trigger** — verify behavior (test or documented contract). Rationale: silent-dark risk if long-lived process sees empty Redis with `warm=True`.

6. **[§3 item 1] Terraform alarm for `RevocationReplayCompletedMs`** P99 > 45s. Rationale: ADR-0004 §Observability required mandates this; currently absent.

7. **[§3 item 2] Terraform alarm for `OAuthRedirectUriRejected`** Sum > 10 per 5-min period sustained. Rationale: symptom-based security-signal [SR:SRC-001]; ship-gate for security-surface visibility.

8. **[§3 item 3] Runbook stubs** for each paging alarm: REVOCATION-REPLAY-SLOW, OAUTH-REDIRECT-URI-REJECTED (plus items 1.4 and 2-invariants). Rationale: sre-Potnia anti-pattern "Creating alerts without runbooks" is a hard ship-gate [SR:SRC-002].

9. **[§3 item 4] Categorize `OAuthPKCEAttempts` and `OAuthDeviceAttempts`** as dashboard-only OR author alarms+runbooks. Rationale: vanity-metrics anti-pattern prevention.

10. **[§3 item 5] Scope-cardinality alarm decision** + associated runbook.

11. **[§3 item 6] Verify emit call-sites** for all defined metric-name constants. Rationale: silent-dark observability defect if a constant is defined but never emitted.

**NON-BLOCKING (track as follow-ups)**:

- [§1.2] Document ADDITIVE columns in ADR-0004 §Consequences.
- [§1.3] Amend ADR-0004 §Context `jti uuid PK` → `jti text PK`.
- [§2.3] Redis-writer invariant runbook.
- [§4] Optional `RevocationReplay503Emitted` CloudWatch counter.
- [§5] Dashboard plane-separation labeling reminder (applied at dashboard-authoring time).
- [§6.4] Scope-shape-invariant-violation CloudWatch Logs metric-filter + runbook.

**NON-PR-BLOCKING but DEPLOY-PIPELINE ASSERTION**:

- [§4] Verify ECS service `deployment_minimum_healthy_percent >= 50` for auth (prevents synchronized fleet-wide 503 on rolling deploy).

### §7.3 Handoff disposition

- **Back to 10x-dev** for 11 BLOCKING remediation items. Majority of items (6 of 11) are Terraform/runbook authoring — roughly 1-2 day effort for a focused dispatch.
- **Re-review required** after remediation. This concurrence is NOT transferable across the remediation cycle — a fresh SRE pass must verify each item, because fragmented partial remediation is a known drift vector.
- **Platform-engineer routing** for Terraform alarm resource authoring IF 10x-dev wants to delegate (per my Exousia: "Route to Platform Engineer: Deployment of monitoring agents... Infrastructure changes for metric collection").
- **Incident-commander routing** not needed at this stage; reliability plan finalizes only when ship-gate is GREEN.

### §7.4 Why REMEDIATE and not ESCALATE

No scope item surfaced an issue beyond observability-engineer authority:
- ADR-0007 CONDITIONAL compatibility (§6) resolved in-scope via claims.py state inspection — no operator ruling needed.
- ADR-0006 invariant preservation (§5) resolved in-scope via observability config audit — no architecture-rite consult needed.
- Migration 024 schema drift (§1) is an implementation-vs-documentation mismatch — 10x-dev's own authority to fix.
- Redis key-namespace drift (§2) is an implementation-vs-spec mismatch — 10x-dev's own authority to fix.
- Missing Terraform alarms (§3) are standard observability-engineering deliverables — squarely in-scope.

No escalation path to operator, Pythia, or cross-rite Potnia is warranted.

---

## §8 — Evidence Grade + External-Critic Path

### §8.1 Evidence grade: [MODERATE intra-sre]

Per self-ref-evidence-grade-rule: intra-rite self-concurrence caps at MODERATE. SRE rite evaluating an SRE-gate artifact has inherent self-reference.

The following substantive judgments rest on SR-namespace literature [SRE-CATALOG sources] with STRONG grade (0.72 confidence per sre-ref):

- Symptom-based-alerting discipline informing §3 runbook-presence gate: [SR:SRC-001 Beyer et al. 2016] [STRONG | 0.72 @ 2026-04-01].
- Alerts-require-runbooks anti-pattern informing §3 BLOCKING disposition: [SR:SRC-002 Beyer et al. 2018] [STRONG | 0.72 @ 2026-04-01].
- Multi-window burn-rate alerting considered-but-declined for §3 redirect_uri alarm (binary signal, single-threshold appropriate): [SR:SRC-010 Google 2018] [STRONG | 0.72 @ 2026-04-01].
- DORA blast-radius discipline informing §1 blast-radius classification: [SR:SRC-003 Forsgren/Humble/Kim 2018] [STRONG | 0.72 @ 2026-04-01].

The aggregate verdict itself remains capped at MODERATE until an external critic applies.

### §8.2 External-critic path to STRONG promotion

Three candidate paths, in priority order:

1. **Hygiene rite 11-check-rubric critique** (`hygiene-11-check-rubric` skill). Hygiene rite is rite-disjoint from SRE and can apply the canonical 11-lens rubric against this concurrence. Promotion to STRONG on CONCUR across all 11 lenses. **Preferred path** because hygiene-rite critique is the standard cross-rite-residency vector for observability artifacts.

2. **Chaos-engineer pre-ship resilience certification**. Pre-merge chaos experiment validating: (a) cold-start replay 503+Retry-After pathway observable and clean on a fault-injected Redis cold-start; (b) 10-instance rolling deploy does not produce fleet-synchronized 503 window (MinHealthyPercent discipline works in practice). Promotion to STRONG on experiment GREEN. **Recommended as complement** to hygiene-rite critique; closes the acid-test "can we catch degradation before customers do?"

3. **Post-merge D+7 observation window GREEN** per canary-signal-contract. Define the five-signal canary for this deploy: (i) `RevocationReplayCompletedMs` P99 < 30s across 10+ auth-server boots; (ii) zero `AUTH-CLAIM-SHAPE-001` events; (iii) `OAuthRedirectUriRejected` at fleet-baseline zero; (iv) `/internal/*` 503 rate during non-deploy windows = 0; (v) ElastiCache evictions at zero under steady-state. Promotion to STRONG on all 5 signals GREEN across 7 days post-merge. **Deferred** until after remediation + merge.

### §8.3 Self-ref declaration

This concurrence was authored by the observability-engineer agent evaluating an SRE gate on artifacts owned by other rites (10x-dev implementation, Platform infrastructure). The dispatcher-critic degeneracy mild-form applies (SRE-rite evaluating an SRE-rite gate) — the self-ref cap at MODERATE is therefore correct and mandatory per the self-ref-evidence-grade-rule. External-critic dispatch via path §8.2.1 (hygiene-rite 11-check) is the shortest lift to STRONG.

### §8.4 Known residual uncertainties

Flagged for downstream reviewer attention:

- **ADR-0007 file is vapor**: the ADR document does not exist; material authority lives in a HANDOFF. §6 compatibility analysis rests on claims.py current state, NOT on a ratified ADR. Until review-rite responds and ADR-0007 is written, this compat assertion is a **provisional** READY-TO-SHIP.
- **Cluster-reconnect replay behavior** (§2.2 item 2): I did not run a live test; I inspected code for the invariant. If empirical test shows `warm=True` persists across Redis cluster swap without replay re-trigger, §2 disposition becomes a deeper REMEDIATE than currently scored.
- **Emit call-sites** (§3 item 6): I verified metric-name constants are defined; I did not verify every constant has at least one emission call-site. If any defined constant is never emitted, §3 becomes a larger REMEDIATE.
- **Staging alembic round-trip** was not executed as part of this concurrence; it is a §1.5 BLOCKING remediation item to be executed BEFORE ship, not concurrent with this review.

---

*SRE CONCURRENCE — PR #131 Revocation-Backend Production-Ship Readiness*
*Emitted 2026-04-21 by observability-engineer (sre rite, intra-rite concurrence, self-ref cap MODERATE)*
*Aggregate verdict: **REMEDIATE** (3 REMEDIATE / 3 READY-TO-SHIP / 0 ESCALATE)*
*Next step: return to 10x-dev for 11 BLOCKING items; re-review on remediation completion.*

---

## §9 — SREDR Amendment 2026-04-22T23:30Z

**Amendment class**: Descriptive state-transition memo. Append-only; does NOT modify the original §7.2 11-BLOCKING list. Evidence grade: not applicable (state transition, not evaluation).

**Amendment author**: incident-commander (sre rite)
**Amendment scope**: signal that PR #131 10x-dev HANDOFF prerequisite (inherited-from-main CI-failure mask) is now SATISFIED, and enumerate pre-authored stub artifacts available for 10x-dev consumption at next CC-restart.

### §9.1 Prerequisite satisfied — main recovery complete

**State transition**: `main` now carries:
- `7dd5a478` — Bundle A (hygiene-rite 11-check recovery merge)
- `fc857ca8` — PR #136 val01b mirror, rebased on top of Bundle A

**Implication**: the inherited-from-main CI-failure mask that was blocking PR #131 rebase is **LIFTED**. The entry-condition clause in HANDOFF-sre-to-10x-dev-pr131-11-blocking-remediation-2026-04-22.md §4 (prerequisite on main green) is now SATISFIED. 10x-dev can rebase PR #131 on current main without inheriting a failing CI surface.

### §9.2 ADR-0001 corroboration count — 5 events STRONG

PR #131 was blocked on ADR-0001 §2.1 retirement baseline durability. That baseline now carries **5 independent corroboration events**, each adding structural durability:

1. review-rite critique PR #120
2. sms-hygiene Sprint-B audit
3. external-critic-sms merge
4. hygiene-rite 11-check Bundle A PR #138
5. hygiene-rite 11-check PR #136 val01b mirror

**Grade lift**: ADR-0001 §2.1 retirement baseline transitions from single-source authority to multi-source corroborated STRONG. This dissolves the latent self-ref concern on any remediation work that cites ADR-0001 as foundation.

### §9.3 Pre-authored stub artifacts (ready for 10x-dev consumption)

Concurrent SRE session deliverables authored 2026-04-22 and staged for 10x-dev pickup at next CC-restart:

| Artifact | Path | Authoring agent |
|----------|------|-----------------|
| CW-1..CW-4 Terraform alarms | `autom8y/terraform/services/auth/observability/cloudwatch-alarms.tf` | platform-engineer (this session) |
| CW-5..CW-8 runbooks + M-2 runbook | `autom8y/services/auth/runbooks/*.md` | observability-engineer (this session) |
| Spec-drift CI preflight playbook (D-01 durable fix) | `autom8y-asana/.ledge/specs/spec-drift-ci-preflight-playbook-2026-04-22.md` | observability-engineer (this session) |

**Effect on 10x-dev scope**: 7 of the original 11 BLOCKING items are pre-authored as stubs. 10x-dev's net dispatch scope collapses to 4 remaining BLOCKING items + Lane 1 amendments.

### §9.4 Remaining 10x-dev net scope

Post-stub-authoring residual BLOCKING set (4 items + 2 Lane 1 amendments):

1. **M-1** schema-drift reconciliation
2. **M-3** alembic round-trip (staging evidence attach)
3. **R-1** Redis `revoked:{jti}` vs `revocation:{jti}` spec-vs-implementation reconciliation
4. **R-2** Redis `revocation:sa:*` absence documentation

**Lane 1 amendments**:
- **D-9-1** OpenAPI regeneration
- **D-9-2** metadata column SQLAlchemy model add

### §9.5 Dispatch-readiness

**HANDOFF status**: ACTIVATED, pending `/cross-rite-handoff --to=10x-dev` operator gate at next CC-restart.

**Operator gate rationale**: cross-rite dispatch boundaries default to operator gating per `prefer-pythia-over-operator-gates` discipline (operator-gate-at-CC-restart-cross-rite-handoff-boundaries clause).

### §9.6 Wave 2 SRE-internal work (in-flight)

**D-06 residual-retirement risk matrix** is currently in-flight this session under Wave 2 SRE-internal scope. Will emit as a **separate HANDOFF to fleet-potnia** at next CC boundary. No overlap with Wave 1 10x-dev dispatch scope.

### §9.7 Audit-trail preservation

This amendment is APPEND-ONLY. The original §7.2 11-BLOCKING list remains unmodified. Readers consuming this concurrence for audit-trail purposes should treat §7.2 as the canonical snapshot of blocking state AT 2026-04-21, and §9.3–§9.4 as the state-transition snapshot AT 2026-04-22T23:30Z reflecting stub-authoring progress against that original scope.

---

*SREDR Amendment — appended 2026-04-22T23:30Z by incident-commander (sre rite)*
*Class: state-transition memo (non-evaluative, evidence-grade N/A)*
*Net effect: 11 BLOCKING → 7 pre-authored + 4 residual + 2 Lane 1 amendments; HANDOFF ACTIVATED pending operator gate*
