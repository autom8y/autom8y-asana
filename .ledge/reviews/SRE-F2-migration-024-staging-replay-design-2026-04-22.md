---
type: review
review_subtype: staging-replay-design
artifact_id: SRE-F2-migration-024-staging-replay-design-2026-04-22
status: draft
rite: sre
agent: platform-engineer
initiative: admin-cli-oauth-migration
parent_handoff: /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-RESPONSE-10x-dev-to-sre-pr131-merged-2026-04-22.md
parent_audit: /Users/tomtenuta/Code/a8/repos/autom8y/.worktrees/pr131-lane-migrations/services/auth/.ledge/reviews/AUDIT-migration-024-roundtrip-2026-04-22.md
related_runbook: /Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/revocation-migration-024-rollback.md
created_at: "2026-04-22"
evidence_grade: strong-for-git-mediated-facts-moderate-for-staging-infra-assumptions
verdict: BLOCKED-ON-STAGING-INFRA
---

# SRE F2 — Migration 024 Staging Replay Design (Paper)

## 1. Migration 024 summary

**File**: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/migrations/versions/024_create_token_revocations_table.py` (revision `024`, parent `023`). Pure additive DDL; no existing-row rewrites.

**What it does**: creates `public.token_revocations` — the durable system-of-record for dual-tier revocation (ADR-0004). Postgres-FIRST write order: row commits here before any Redis write; cold-start replay reads back 7 days to rebuild Redis.

**Forward SQL fingerprint** (source: lines 50-88):
- `CREATE TABLE token_revocations (jti TEXT PK, revoked_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_by_sub TEXT NOT NULL, reason_code TEXT NOT NULL, source_endpoint TEXT NOT NULL, original_exp TIMESTAMPTZ NOT NULL, metadata JSONB NULL)`
- `CREATE INDEX idx_revocations_revoked_at ON token_revocations (revoked_at)` (non-unique btree; rolling-window replay scan)
- `CREATE INDEX idx_revocations_reason ON token_revocations (reason_code)` (non-unique btree; dashboard slicing)
- `COMMENT ON TABLE token_revocations IS '...'` (idempotent metadata)

**Reverse SQL fingerprint** (source: lines 91-95):
- `DROP INDEX idx_revocations_reason`
- `DROP INDEX idx_revocations_revoked_at`
- `DROP TABLE token_revocations` (cascades the PK constraint)

**Local dev-Postgres round-trip (what was proven — STRONG per audit §9)**: UP 023→024, DOWN 024→023, UP 023→024 executed against `postgres:15-alpine` container (`auth-postgres`, port 5433). Schema dumps post-up1 and post-up2 are bit-identical on column list, types, nullability, defaults, PK, and both secondary indexes. Downgrade dropped the table + indexes + PK atomically with no residual artifacts. Full transcripts archived at `/tmp/m3-*.log` (local-only; not committed).

## 2. Staging replay procedure (paper — DO NOT execute without infra gating; see §3/§6)

All commands executed from the auth ECS task using the production runbook pattern (`runbooks/PRODUCTION-DATABASE.md`), adapted for a staging cluster. Replace `<STAGING-CLUSTER>` / `<STAGING-SERVICE>` per §6 open question.

**DSN source**: AWS Secrets Manager entry at `autom8y/auth/db-password-staging` (analogue of the documented `autom8y/auth/db-password` production secret — production analogue cited in `PRODUCTION-DATABASE.md` line 74; staging analogue presumed; VERIFY-BEFORE-RUN per §6).

### Steps

1. **Acquire staging task shell**
   ```
   TASK_ARN=$(aws ecs list-tasks --cluster <STAGING-CLUSTER> --service-name auth --query 'taskArns[0]' --output text)
   aws ecs execute-command --cluster <STAGING-CLUSTER> --task "$TASK_ARN" \
     --container auth --interactive --command "/bin/sh"
   ```
   **Expected**: shell prompt inside `/app` working dir.

2. **Resolve DSN + install ephemeral migration toolchain**
   ```
   export DATABASE_URL=$(aws secretsmanager get-secret-value \
     --secret-id autom8y/auth/db-password-staging \
     --query 'SecretString' --output text | jq -r .connection_string)
   pip install alembic pydantic-settings sqlmodel psycopg2-binary
   cd /app
   ```
   **Expected**: `pip install` reports success; `DATABASE_URL` set.

3. **Capture baseline alembic state**
   ```
   alembic history | head -5 > /tmp/staging-history-before.log
   alembic current > /tmp/staging-current-before.log
   ```
   **Expected**: `Rev: 024 (head)` if deploy-gate has already run the entrypoint; `Rev: 023` if pre-migration. Both are valid starting points — branch procedure accordingly.

4. **Phase A — UP (if currently at 023)**: `alembic upgrade head` → capture to `/tmp/staging-up.log`.
   **Expected**: final line `Running upgrade 023 -> 024, Create token_revocations table (durable dual-tier revocation audit log).`

5. **Verification SQL (after UP)** — execute inside `psql $DATABASE_URL`:
   ```sql
   \d token_revocations
   SELECT indexname FROM pg_indexes WHERE tablename='token_revocations' ORDER BY indexname;
   SELECT obj_description('token_revocations'::regclass);
   SELECT count(*) FROM token_revocations;
   ```
   **Expected**: 7 columns with types matching §1 fingerprint; 3 indexes (`idx_revocations_reason`, `idx_revocations_revoked_at`, `token_revocations_pkey`); COMMENT matches lines 82-88; row count finite and bounded (staging traffic is sparse per `token_exchange_alarms.tf:190-193`).

6. **Snapshot before downgrade** (non-optional — staging retains audit rows):
   ```
   pg_dump -t token_revocations --no-owner --no-acl \
     "$DATABASE_URL" > /tmp/staging-token-revocations-pre-down.sql
   ```
   **Expected**: non-empty file; row block present if count > 0.

7. **Phase B — DOWN**: `alembic downgrade -1` → capture to `/tmp/staging-down.log`.
   **Expected**: `Running downgrade 024 -> 023, Create token_revocations table ...`

8. **Verification SQL (after DOWN)**:
   ```sql
   \d token_revocations
   ```
   **Expected**: `Did not find any relation named "token_revocations"` (matches local audit §3 Phase B).

9. **Phase C — UP AGAIN**: `alembic upgrade head` → capture to `/tmp/staging-up2.log`. Re-run the step-5 verification queries into `/tmp/staging-schema-after-up2.log`.
   **Expected**: schema output bit-identical to post-Phase-A capture.

10. **Drift check**: `diff /tmp/staging-schema-after-up.log /tmp/staging-schema-after-up2.log` → expected empty output (structural zero-diff, same discipline as local audit §4).

11. **Re-seed preserved rows** (if pre-down snapshot had rows; idempotent):
    ```
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
      -c "CREATE TEMP TABLE _staging_replay AS SELECT * FROM token_revocations WITH NO DATA;" \
      -f /tmp/staging-token-revocations-pre-down.sql
    ```
    Row-replay uses `INSERT ... ON CONFLICT (jti) DO NOTHING` semantics mirroring rollback runbook §Revert-of-revert.

12. **Archive evidence to S3** (replaces `/tmp/` evidence pattern with durable capture):
    `aws s3 cp /tmp/staging-*.log s3://autom8y-incident-artifacts/auth/migration-024-staging-replay/<ISO-timestamp>/`

## 3. Pre-flight gates (must ALL be true before step 1)

- [ ] **Staging DB snapshot taken**: `aws rds create-db-snapshot --db-instance-identifier <STAGING-RDS> --db-snapshot-identifier m024-staging-replay-<date>` AND snapshot reports `available` status.
- [ ] **Lock-timeout envelope**: `SET lock_timeout='5s'; SET statement_timeout='60s';` appended to the alembic session (DDL on a table with zero to low rows; 5s lock-timeout bounds blast radius).
- [ ] **No long-running writers**: `SELECT count(*) FROM pg_stat_activity WHERE state='active' AND query ILIKE '%token_revocations%';` returns 0 at start.
- [ ] **Deploy-freeze window open**: no in-flight auth-service deploys on staging (otherwise entrypoint `alembic upgrade head` in `scripts/entrypoint.sh:18` races the manual replay).
- [ ] **IC awareness posted**: replay is read-only for production but produces a brief staging `/internal/*` inconsistency window between step 7 and step 9; post in `#sre-ops` for recordkeeping.
- [ ] **Staging DSN verified**: `autom8y/auth/db-password-staging` resolves to a staging RDS endpoint (NOT `autom8y-auth-db.cojxm3unmbon.us-east-1.rds.amazonaws.com` — that is production per `PRODUCTION-DATABASE.md:80`).

## 4. Success criteria

| Signal | PASS | FAIL |
|--------|------|------|
| `alembic current` post-UP | `Rev: 024 (head)` | any other value |
| `\d token_revocations` post-UP | 7 columns match §1 fingerprint; 3 indexes present | any column missing / extra / wrong type |
| `\d token_revocations` post-DOWN | relation absent | relation present → downgrade did not complete |
| `alembic current` post-UP-again | `Rev: 024 (head)` | any other value |
| diff schema-after-up vs schema-after-up2 | empty | any non-empty diff |
| Row preservation (step 11) | count pre-DOWN == count post-reseed | count differs (forensic flag; investigate per `revocation-migration-024-rollback.md` §Data-preservation) |
| Lock contention | no `lock_timeout` errors in step-4/7/9 logs | any `canceling statement due to lock timeout` |
| Index creation | `CREATE INDEX` completes synchronously (table size on staging is tiny) | any `ERROR: could not create unique index` — indexes are non-unique so this should not happen; escalate if observed |
| FK / constraint violations | none (migration is additive, no FKs) | any `violates foreign key` — escalate immediately |

Overall PASS = all rows PASS. Any FAIL → §5.

## 5. Rollback on failure (ordered — no improvisation)

### 5A. Failure during UP (step 4 or step 9)

1. `alembic current` — determine partial state.
2. If `Rev: 023`: UP did not commit (alembic wraps DDL in a tx). No action required; abort procedure.
3. If `Rev: 024` but schema verification (§4) fails: `alembic downgrade -1`. Re-run step-8 verification. Confirm clean revert.
4. If alembic errors prevent downgrade: restore from pre-flight RDS snapshot (§3 gate 1) per AWS RDS restore-from-snapshot runbook. IC-escalate.
5. Do NOT attempt re-UP until the failure root cause is understood.

### 5B. Failure during DOWN (step 7)

1. `alembic current` — determine state.
2. If `Rev: 024`: DOWN did not commit. Aborting is safe — staging is still in the working post-UP state.
3. If `Rev: 023` but table still exists (partial downgrade): execute explicit cleanup `DROP INDEX IF EXISTS idx_revocations_reason; DROP INDEX IF EXISTS idx_revocations_revoked_at; DROP TABLE IF EXISTS token_revocations;` inside a transaction. Re-assert `alembic current = 023`.
4. Immediately execute step 9 (UP again) to restore working state. Follow with step-5 verification.
5. If UP-again fails: restore from §3 RDS snapshot. IC-escalate.

### 5C. Lock contention / statement timeout

1. Cancel session. `alembic current` should show pre-statement revision.
2. Run `SELECT pid, query, state, wait_event FROM pg_stat_activity WHERE query ILIKE '%token_revocations%' OR waiting;` to identify the blocker.
3. Do not re-run until blocker is resolved (common cause: in-flight entrypoint migration from a rolling deploy; wait for deploy to complete).
4. Re-attempt from step 3 (re-baseline).

## 6. CI-integration hook — minimum-viable automation

**Open question before any CI work fires**: staging infrastructure is **NOT obviously wired** from the repo. Evidence:

- `/Users/tomtenuta/Code/a8/repos/autom8y/terraform/environments/` contains only `production/` — no `staging/` Terraform workspace.
- `services/auth/variables.tf:12-17` accepts `staging` as a valid `environment` value, but no staging tfvars / backend / RDS instance is materialized in git.
- `secretspec.toml` names `AUTOM8Y_ENV=staging` as legal, and `just deploy-full env="staging"` in `just/deploy.just:61` claims to deploy there — but the destination RDS and Secrets Manager binding is not repo-resolvable.
- `PRODUCTION-DATABASE.md` names only the production RDS endpoint; no staging analogue documented.

**v1 — one-shot manual run (RECOMMENDED if staging cluster + RDS exist but are invisible to repo)**: execute §2 procedure by-hand on the next natural maintenance window. Human operator follows §3 gates and §5 rollback. Evidence archived to S3 per step 12. No automation built. Cost: ~45 min operator time once.

**v2 — GH Actions workflow (propose ONLY after v1 succeeds)**: new workflow `.github/workflows/auth-migration-roundtrip.yml` (the pattern prefigured in local audit §6):
- Trigger: `workflow_dispatch` only (NOT `on: pull_request` — that would run every PR that touches any file, wasting cycles; the actual migration already ran at ship-gate per entrypoint). Manual gate is the correct v2 shape.
- Job: spin up `postgres:15-alpine` service container, run the identical Phase-A/B/C sequence against the ephemeral CI Postgres (NOT staging RDS — see note below).
- Assert: `diff` post-up vs post-up2 schema dumps returns empty.
- Auth: no secrets needed for the ephemeral-CI form.
- Note on why CI does NOT hit staging RDS: running the round-trip against the real staging DB from CI requires staging Secrets Manager access from GitHub runners, staging VPC reachability (bastion / SSM), and a lock-coordination story with the auth-service entrypoint. These are step-up complexity. Ephemeral-CI-Postgres gives 90% of the signal (the migration code is DDL-deterministic against any Postgres 15) for 10% of the build cost. Actual staging-RDS runs stay manual (v1) until a deploy-gate case demands otherwise.

**Don't-over-build**: ephemeral-CI round-trip is sufficient as continuous regression. Staging-RDS round-trip is a human-gated deploy-smoke, not a per-PR artifact.

## 7. Scope-deferred items

- **Production replay**: explicitly OUT of F2 scope. Forward path for prod is guarded by the existing `runbooks/revocation-migration-024-rollback.md` — which covers rollback (DOWN) but NOT a round-trip exercise. A production round-trip is never free: DOWN discards live revocation rows (data loss; security-impacting per migration-file docstring lines 33-36). Recommend documenting "no production round-trip; forward-only" as the standing posture. Revisit **2026-07-22** (90 days) OR on any ADR-0004 schema amendment, whichever first.
- **Automated staging RDS round-trip from CI**: DEFER until staging infra is IaC-resolvable (see §6 open question). Revisit when a `terraform/environments/staging/` workspace appears OR fleet-potnia formally scopes staging-IaC uplift.
- **Multi-region replay**: N/A — auth runs single-region (us-east-1 per production runbook §Database connection details).

## 8. Verdict

**`BLOCKED-ON-STAGING-INFRA`**.

Rationale: §2 procedure is fully specified and executable *given a staging cluster + staging RDS + staging Secrets Manager entry*. None of the three is discoverable from the repo — terraform has production-only, secretspec documents only variable names not instances, and the auth service's production runbook does not have a staging sibling. The paper design is replay-ready; the environment to execute against is not infra-confirmed.

**Ask to SRE infra team / fleet-potnia** (blocks unblock):
1. Confirm whether a staging RDS instance exists for auth (identifier + endpoint).
2. If yes: provide Secrets Manager path (propose `autom8y/auth/db-password-staging`) and ECS cluster + service names.
3. If no: confirm that "no staging" is a permanent architectural choice, in which case the verdict collapses to `REPLAY-READY-MANUAL-V1` against ephemeral-CI-Postgres only and F2 closes with the ephemeral-CI v2 workflow as the singular execution path.

Once the above is unblocked, verdict upgrades to `REPLAY-READY-MANUAL-V1` (execute §2 by-hand at next maintenance window) with a follow-on ticket for `REPLAY-READY-CI-V2` (ephemeral-CI round-trip workflow). The HANDOFF characterized F2 as LOW priority; that classification stands. No reliability blocker. PR #131 ship-gate is not retroactively affected.

## 9. Evidence grade

- **STRONG** for all git-mediated claims (migration SQL, alembic config, Justfile targets, production runbook DSN, Terraform environments directory listing, round-trip local audit contents).
- **MODERATE** for staging-infra assumptions (presumed Secrets Manager secret name; presumed ECS cluster and service naming; presumed RDS snapshot procedure transferability). These are surfaced in §6 as the unblock-ask rather than assumed into the v1 procedure.
- No claims graded WEAK or PLATFORM-HEURISTIC.

## 10. Artifact locations

- This design doc (paper deliverable): `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-F2-migration-024-staging-replay-design-2026-04-22.md`
- Migration source: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/migrations/versions/024_create_token_revocations_table.py`
- Local round-trip audit (context): `/Users/tomtenuta/Code/a8/repos/autom8y/.worktrees/pr131-lane-migrations/services/auth/.ledge/reviews/AUDIT-migration-024-roundtrip-2026-04-22.md`
- Rollback runbook (sibling artifact): `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/revocation-migration-024-rollback.md`
- Production DB access reference: `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/runbooks/PRODUCTION-DATABASE.md`
- Entrypoint (shows where `alembic upgrade head` runs on deploy): `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/scripts/entrypoint.sh`
- Alembic env config (DSN-normalization — strips `+asyncpg` for sync migrations): `/Users/tomtenuta/Code/a8/repos/autom8y/services/auth/migrations/env.py`
