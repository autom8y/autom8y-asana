---
type: handoff
status: draft  # canonical lifecycle vocabulary; schema-§1.2 state-machine value is `ATTESTED-PENDING-thermia` until thermia.thermal-monitor writes the §Verification Attestation section. Mapping rationale per LD-P5A-2 (status-vocabulary divergence) in §6.2 below; mirrors predecessor `HANDOFF-thermia-to-10x-dev-2026-04-27.md:3` convention.
handoff_type: validation
schema_version: 1
originating_rite: 10x-dev
receiving_rite: thermia
fallback_rite: sre
originating_session: session-20260427-205201-668a10f4
authored_on: 2026-04-27
authored_by: 10x-dev.potnia (orchestration via general-purpose author)
worktree: .worktrees/cache-freshness-impl/
branch: feat/cache-freshness-impl-2026-04-27
initiative_slug: cache-freshness-impl-from-thermia-2026-04-27
parent_initiative: cache-freshness-procession-2026-04-27
grandparent_initiative: verify-active-mrr-provenance
predecessor_handoff: .ledge/handoffs/HANDOFF-thermia-to-10x-dev-2026-04-27.md
attestation_required: true
attestation_chain: thermia.thermal-monitor (primary), sre.observability-engineer (fallback)
verification_deadline: 2026-05-27
design_references:
  - .ledge/specs/cache-freshness-architecture.tdd.md
  - .ledge/specs/cache-freshness-capacity-spec.md
  - .ledge/specs/cache-freshness-observability.md
  - .ledge/specs/cache-freshness-runbook.md
  - .ledge/decisions/ADR-001-metrics-cli-declares-freshness.md
  - .ledge/decisions/ADR-002-rite-handoff-envelope-thermia.md
  - .ledge/decisions/ADR-003-memorytier-post-force-warm-staleness.md
  - .ledge/decisions/ADR-004-iac-engine-cache-warmer-schedule.md
  - .ledge/decisions/ADR-005-ttl-manifest-schema-and-sidecar.md
  - .ledge/decisions/ADR-006-cloudwatch-namespace-strategy.md
  - .ledge/reviews/QA-impl-close-cache-freshness-2026-04-27.md
implementation_pr: PENDING (draft PR opens at T#43)
index_entry_appended: true
---

# HANDOFF — 10x-dev → thermia (cache-freshness-impl post-impl validation)

This dossier transfers the post-implementation **verification** scope of the
cache-freshness initiative from the 10x-dev rite (P6 implementation phase) back
to the thermia rite for P7 thermal-monitor attestation. Per the parent telos
SQ-3 decision (`.know/telos/cache-freshness-procession-2026-04-27.md`),
verification mode is **BOTH design-review + in-anger-probe**. P7 attestation
discharges the parent telos `verify-active-mrr-provenance` D8 `verified_realized`
gate by 2026-05-27.

The 10x-dev rite has shipped 6 of 8 work items in scope (the 2 deferred items
are by-design cross-repo Terraform coordination, not engineering gaps). Commit
chain `a732487f..e4b5222d` (7 commits ahead of
`origin/thermia/cache-freshness-procession-2026-04-27`) carries the impl + QA
report. The QA-adversary verdict at
`.ledge/reviews/QA-impl-close-cache-freshness-2026-04-27.md` is **GO** with
0 BLOCKING / 0 SERIOUS / 0 MINOR / 1 DEFER-OK defects. 436/1 unit tests pass
(1 environment-skipped); ruff / mypy clean across 66 source files; Phase E
moto end-to-end smoke confirms all 5 CloudWatch metrics land in the namespace.
Probe-4 baseline executes cleanly today.

The fallback rite `sre.observability-engineer` is inherited from the
predecessor dossier §8.1 latent decision #2 (SLO-shaped verification surface).
Activation predicate is mechanically verifiable per
`.ledge/specs/handoff-dossier-schema.tdd.md` §5.1 (ENOENT on
`.claude/agents/thermia/` OR rite absent from `.knossos/KNOSSOS_MANIFEST.yaml`).

## 1. Implementation Summary (8 work items)

Each item below cites the predecessor §1 work-item ID, ship status, and the
file:line landed-anchor. DEFER-OK items are by-design cross-repo coordination
parked for Batch-D apply; they are NOT engineering gaps.

- **WI-1 — Force-warm CLI affordance (PRD NG4)**: SHIPPED at
  `src/autom8_asana/metrics/__main__.py:560-578` (argparse) +
  `src/autom8_asana/metrics/__main__.py:640-701` (handler) +
  `src/autom8_asana/metrics/__main__.py:301-487` (`_execute_force_warm` helper).
  CLI delegates to canonical surface
  `src/autom8_asana/cache/integration/force_warm.py:159-385`
  (PT-2 Option B refactor; LD-P3-2 sole-channel binding). Default async
  (`InvocationType="Event"`); opt-in sync (`InvocationType="RequestResponse"`)
  with `--wait`. Coalescer-routed via `DataFrameCache`
  (`src/autom8_asana/cache/dataframe/coalescer.py`). Pre-validates
  `ASANA_CACHE_S3_BUCKET` BEFORE Lambda invocation.
- **WI-2 — SLA enforcement extension (PRD NG8)**: SHIPPED at
  `src/autom8_asana/metrics/__main__.py:580-592` (argparse `--sla-profile`
  flag) + `src/autom8_asana/metrics/__main__.py:601-621` (precedence
  resolution against existing `--strict` and `--staleness-threshold`).
  4-class taxonomy mapping table at
  `src/autom8_asana/metrics/__main__.py:163-168`
  (`active=21600`, `warm=43200`, `cold=86400`, `near-empty=604800`).
  Default `active` preserves PRD G2 6h behavior (PRD C-2 backwards-compat).
- **WI-3 — TTL persistence (LD-P3-1)**: SHIPPED at
  `src/autom8_asana/metrics/sla_profile.py:1-652`
  (full ADR-005 V-1..V-6 schema validators; manifest + S3 sidecar with
  override precedence). Manifest at
  `.know/cache-freshness-ttl-manifest.yaml` (1.6kB; valid YAML).
  S3 sidecar reader/writer for
  `s3://autom8-s3/dataframes/{project_gid}/cache-freshness-ttl.json`.
  60 unit tests cover schema-version, sla-class, threshold, gid,
  cross-validation, manifest, sidecar, sidecar-precedence-over-manifest,
  parse-error fall-through.
- **WI-4 — CloudWatch metric emissions (P4 §1 + §4 + §10)**: SHIPPED at
  `src/autom8_asana/metrics/cloudwatch_emit.py:1-233`
  (5 metrics in single `put_metric_data` per ADR-006 atomic-timestamp;
  C-6 guard at `cloudwatch_emit.py:88-106` mechanically blocks
  `SectionCoverageDelta` from any alarmable codepath). 5 metrics emitted
  to `Autom8y/FreshnessProbe` namespace:
  `MaxParquetAgeSeconds`, `ForceWarmLatencySeconds`, `SectionCount`,
  `SectionAgeP95Seconds`, `SectionCoverageDelta`. Plus 1 metric
  `CoalescerDedupCount` to `autom8y/cache-warmer` from
  `src/autom8_asana/cache/dataframe/coalescer.py:34-67`.
  P95 computation at `src/autom8_asana/metrics/freshness.py:103-138`
  (nearest-rank P95 over retained `mtimes` tuple from `from_s3_listing`).
- **WI-5 — DMS CloudWatch alarm (LD-P4-1)**: SHIPPED via Path B —
  Terraform `aws_cloudwatch_metric_alarm.cache_warmer_dms_24h` STASHED
  in autom8y repo at `git stash@{0}` on
  `anchor/adr-anchor-001-exemption-grant`. Investigation verdict per
  commit `49740a1f` body: `autom8y_telemetry.aws.emit_success_timestamp`
  does NOT auto-provision the alarm; Path B (manual authoring) chosen.
  Awaits Batch-D cross-repo coordination (un-stash + apply per PT-1 XC-2
  staging guidance).
- **WI-6 — cache_warmer Lambda schedule explicit in IaC (P3 D10)**:
  PENDING-BATCH-D — `.ledge/decisions/ADR-004-iac-engine-cache-warmer-schedule.md`
  records the choice (Terraform). 1-line cron change targets
  `autom8y/terraform/services/asana/variables.tf:67-71` from
  `cron(0 2 * * ? *)` (daily) to `cron(0 */4 * * ? *)` (every 4h).
  External IaC repo apply is POST-IMPL-DEPLOY per PT-1 XC-2 staging
  guidance (deploy alarms with `actions_enabled=false` first; un-suppress
  after Terraform cron lands and observation period). Out-of-worktree
  by-design per HANDOFF predecessor §1 work-item-6.
- **WI-7 — MemoryTier HYBRID per ADR-003**: SHIPPED at
  `src/autom8_asana/cache/integration/force_warm.py:466-493`
  (`_invalidate_l1` helper called only on sync `--wait` success;
  default async path skips L1 invalidation, accepting SWR rebuild lag
  per ADR-003 §Decision). Tests verify
  `test_async_does_not_invalidate_l1_per_adr003`,
  `test_sync_success_invalidates_l1`,
  `test_sync_with_specific_entity_types_invalidates_each`.
- **WI-8 — MINOR-OBS-2 botocore traceback fix**: SHIPPED at
  `src/autom8_asana/metrics/__main__.py:738-780`
  (extends original handler beyond `(ValueError, FileNotFoundError)` to
  catch `botocore.exceptions.ClientError` for `NoSuchBucket`,
  `NoSuchKey`, `AccessDenied`, `InvalidAccessKeyId`,
  `SignatureDoesNotMatch`, unknown codes; AND
  `botocore.exceptions.NoCredentialsError`). 4 tests in
  `TestMinorObs2BotocoreFix` cover all branches.

## 2. Commit Ledger (7 commits with receipt-grammar)

Range: `git log --oneline a732487f..HEAD` (head `e4b5222d`). All commits
verifiable via `git show {sha}` from worktree
`/Users/tomtenuta/Code/a8/repos/autom8y-asana/.worktrees/cache-freshness-impl/`.

| SHA | Phase | Files (load-bearing) | Receipt-grammar |
|---|---|---|---|
| `c116cbc8` | ADR trio | `.ledge/decisions/ADR-004-iac-engine-cache-warmer-schedule.md`, `.ledge/decisions/ADR-005-ttl-manifest-schema-and-sidecar.md`, `.ledge/decisions/ADR-006-cloudwatch-namespace-strategy.md` | architect-shaped artifact-only commit; no impl |
| `2ffed86a` | Batch-A | `src/autom8_asana/metrics/__main__.py`, `tests/unit/metrics/test_main.py` | Force-warm CLI + sla-profile + MINOR-OBS-2 fix initial pass; force-warm/env-var portion **superseded by `49740a1f`** for PT-2 Option B refactor (CLI now delegates to canonical `force_warm()`). |
| `f6dad321` | Batch-C | `src/autom8_asana/metrics/sla_profile.py:1-652`, `src/autom8_asana/cache/integration/force_warm.py:1-493`, `.know/cache-freshness-ttl-manifest.yaml`, `tests/unit/metrics/test_sla_profile.py`, `tests/unit/cache/integration/test_force_warm.py` | TTL persistence (manifest + S3 sidecar w/ ADR-005 V-1..V-6 validators) + canonical force_warm() surface establishment + AP-3 named risk preserved (docstring at `force_warm.py:28-30`) |
| `49740a1f` | **CONFLATED** Batch-B + PT-2 Option B refactor | `src/autom8_asana/metrics/cloudwatch_emit.py:1-233` (+233), `src/autom8_asana/metrics/freshness.py:103-138` (+49 P95 enhancement), `src/autom8_asana/metrics/__main__.py` (+330/-256 refactor + CW emit groundwork), `src/autom8_asana/cache/dataframe/coalescer.py:34-67` (+54), test files | **DUAL CONTENT.** Batch-B half: `cloudwatch_emit.py` (5 metrics in single put_metric_data; ADR-006 atomic-timestamp; C-6 guard at lines 88-106); `freshness.py` mtime tuple retention for P95; coalescer dedup metric; DMS alarm Path B Terraform STASHED in cross-repo. PT-2 Option B refactor half: `__main__.py` `force_warm` import + `_execute_force_warm` + `_resolve_dataframe_cache_for_cli` singleton + LD-P3-2 structural enforcement + `CACHE_WARMER_LAMBDA_ARN` env var canonicalization. **Disambiguation rule**: lines in `cloudwatch_emit.py` = Batch-B; `force_warm` import + LD-P3-2 enforcement in `__main__.py` = PT-2 Option B refactor. **Conflation rationale**: server-side rate-limit caused Batch-A-Refactor's first dispatch to leave uncommitted modifications that Batch-B (retry) absorbed. PT-3 adjudicated **leave-as-is + document** (this entry is the document). No behavioral regression; both halves interdependent (FLAG-1 wiring requires canonical `force_warm()` surface AND CW emission consumes the latency window the canonical surface produces). |
| `7ed89918` | PT-3 BLOCK-1 remediation | `src/autom8_asana/metrics/__main__.py` (+192/-6), `tests/unit/metrics/test_main.py` (+309) | FLAG-1 production wiring closure: `emit_freshness_probe_metrics()` previously dead code; now wired at `__main__.py:472` (force-warm sync recheck site) + `__main__.py:893` (default-mode emission). Safe-emit wrapper at `__main__.py:241-263` absorbs CW failures (single stderr WARNING; no CLI crash). |
| `e4b5222d` | QA report | `.ledge/reviews/QA-impl-close-cache-freshness-2026-04-27.md:1-320` | adversarial QA pass; 0 BLOCKING / 0 SERIOUS / 0 MINOR / 1 DEFER-OK; 436/1 tests; ruff/mypy clean; Phase E moto smoke PASS; Probe-4 baseline PASS; verdict **GO** |

(Note: the 7th commit referenced by the dispatch is `4298849b chore(handoff):
10x-dev attester acceptance — cache-freshness-impl kickoff` which lands the
acceptance-section append on the predecessor dossier prior to the 7-commit
impl chain `a732487f..HEAD`. It is the boundary-marker commit and is included
here for chain-of-custody completeness.)

## 3. SLI / SLO / Alert Status Table

Per PT-4 Concerns 1-3 — mechanical inventory of the observability surface
shipped vs spec'd. Per-item wired/deferred status with code-or-IaC location.

### 3.1 SLIs (5 + 1)

| SLI | Wired status | Code/IaC location | Alarm? | Notes |
|---|---|---|---|---|
| `MaxParquetAgeSeconds` | WIRED | `src/autom8_asana/metrics/cloudwatch_emit.py:1-233` (emit) + `src/autom8_asana/metrics/freshness.py:202` (compute) | YES — ALERT-1, ALERT-2 | namespace `Autom8y/FreshnessProbe` |
| `ForceWarmLatencySeconds` | WIRED | `src/autom8_asana/metrics/cloudwatch_emit.py:1-233` (emit) + `src/autom8_asana/metrics/__main__.py:472` (sync recheck wiring; FLAG-1 boundary spans coalescer wait) | NO-ALARM-TODAY (DEFER-FOLLOWUP) | sync path emits non-None latency; async path emits null/omitted per FLAG-1 boundary contract |
| `SectionCount` | WIRED | `src/autom8_asana/metrics/cloudwatch_emit.py:1-233` + `src/autom8_asana/metrics/freshness.py:153` | NO informational only | baseline ~14 sections at handoff |
| `SectionAgeP95Seconds` | WIRED | `src/autom8_asana/metrics/cloudwatch_emit.py:1-233` + `src/autom8_asana/metrics/freshness.py:103-138` (nearest-rank P95 over retained `mtimes`) | NO low-N discrimination (DEFER-FOLLOWUP) | per-key mtime list retained in `from_s3_listing` enhancement |
| `SectionCoverageDelta` | WIRED | `src/autom8_asana/metrics/cloudwatch_emit.py:88-106` (C-6 guard) | **NO-ALARM** by **C-6 hard constraint** (correctness affordance, NOT a gap) | `c6_guard_check("SectionCoverageDelta")` raises `C6ConstraintViolation` if any caller attempts alarmable use; mechanically blocked |
| `CoalescerDedupCount` (+1) | WIRED | `src/autom8_asana/cache/dataframe/coalescer.py:34-67` | NO informational only | namespace `autom8y/cache-warmer` per ADR-006 |

### 3.2 SLOs (3)

| SLO | Wired status | Source | Notes |
|---|---|---|---|
| `ParquetMaxAgeSLO` (95% < 6h over 7d ACTIVE) | DEFINED in spec; metric WIRED | `.ledge/specs/cache-freshness-observability.md:107-119` | starts in deficit; reaches green ~6h after Batch-D EventBridge schedule applies (per §7 below) |
| `WarmSuccessRateSLO` (95% over 7d entity_type=offer) | DEFINED in spec; metric pre-existing | `src/autom8_asana/lambda_handlers/cache_warmer.py:473,501` | warmer-side metric existed before this initiative |
| `WarmHeartbeatSLO` (>=1 emit_success_timestamp / 24h) | DEFINED in spec; alarm STASHED for Batch-D | `.ledge/specs/cache-freshness-observability.md:139-149`; alarm at autom8y `git stash@{0}` | dead-man's-switch alarm `aws_cloudwatch_metric_alarm.cache_warmer_dms_24h` |

### 3.3 Alerts (6)

| ALERT | Wired status | Code/IaC location | DEFER reason if applicable |
|---|---|---|---|
| ALERT-1 Freshness Breach WARNING | DEFER-BATCH-D | spec at `.ledge/specs/cache-freshness-observability.md:159-181` | requires CloudWatch alarm Terraform apply |
| ALERT-2 Freshness Breach Sustained P1 | DEFER-BATCH-D | spec at `.ledge/specs/cache-freshness-observability.md:184-205` | requires CloudWatch alarm Terraform apply |
| ALERT-3 Warmer Failure Rate (`WarmFailure` >= 1/hr, entity_type=offer) | **OWNERSHIP UNCLEAR** — see §5(c) re-handoff request | spec at `.ledge/specs/cache-freshness-observability.md:209-231` | metrics pre-exist; alarm authoring ownership FLAG |
| ALERT-4 DMS Heartbeat Absent P1 | STASHED-BATCH-D | autom8y `git stash@{0}` Terraform `aws_cloudwatch_metric_alarm.cache_warmer_dms_24h`; spec at `.ledge/specs/cache-freshness-observability.md:235-256` | by-design cross-repo Terraform |
| ALERT-5 S3 IO Error Rate (`FreshnessError` >= 2/hr) | **OWNERSHIP UNCLEAR** — see §5(c) re-handoff request | spec at `.ledge/specs/cache-freshness-observability.md:260-272` | emission codepath wired; alarm authoring ownership FLAG |
| ALERT-6 SectionCoverageDelta | **NO-ALARM** by **C-6 hard constraint** (correctness affordance) | `src/autom8_asana/metrics/cloudwatch_emit.py:88-106` | mechanically blocked, NOT a gap |

## 4. In-Anger Probe Execution Status (P4 §455-602)

Per PT-4 Concern 4 — explicit wiring/deferral status for each of the 5 probes
defined at `.ledge/specs/cache-freshness-observability.md:433-602`.

| Probe | Status | Reason | Required for P7 |
|---|---|---|---|
| Probe-1 (force-warm reduces oldest-parquet age below SLA) | DEFERRED-TO-P7-POST-DEPLOY | Requires deployed Lambda + EventBridge schedule + actual `--force-warm --wait` cycle against `s3://autom8-s3/dataframes/...` | YES — after Batch-D apply |
| Probe-2 (telemetry surfaces alert on max_mtime > SLA threshold) | DEFERRED-TO-P7-POST-DEPLOY | Requires deployed alarms (Batch-D Terraform stash un-suppress) | YES — after Batch-D apply |
| Probe-3 (force-warm + freshness CLI compose; ADR-003 acceptance) | DEFERRED-TO-P7-POST-DEPLOY | Requires deployed Lambda; sync path verified via `tests/unit/cache/integration/test_force_warm.py::TestForceWarmSyncMode::test_sync_success_invalidates_l1` | YES — after Batch-D apply |
| **Probe-4 (`--strict` baseline)** | **RUNNABLE-NOW + PASS** | QA Phase D §6.2 transcript records `--strict` + stale → exit 1; (no `--strict`) + stale → exit 0 / None; behavior matches PRD AC-2.3 | Already discharged at QA gate; thermal-monitor MAY re-run as design-review evidence |
| Probe-5 (section-coverage telemetry emits expected metrics) | PARTIAL — moto verified at QA Phase E-1 | All 5 metrics land in moto CloudWatch backend (transcript at `.ledge/reviews/QA-impl-close-cache-freshness-2026-04-27.md:160-169`); full deployed-system verification awaits Batch-D apply | YES — after Batch-D apply |

## 5. Outstanding Work for thermia P7

Per PT-4 Concerns 3-5 — what thermia P7 thermal-monitor needs to discharge
the D8 verified_realized gate.

### 5(a) Re-engagement trigger

P7 attestation re-engages when ALL of the following are true:
- Draft PR (T#43) merges to main.
- Production deploy completes (Lambda + IaC).
- Batch-D cross-repo coordination completes (autom8y stash pop + apply).

### 5(b) Batch-D coordination (cross-repo Terraform)

Two operations in the autom8y repo (NOT this worktree):

1. **Pop the stash**: `cd /Users/tomtenuta/Code/a8/repos/autom8y && git stash pop`
   on branch `anchor/adr-anchor-001-exemption-grant`. Stash contents:
   Terraform `aws_cloudwatch_metric_alarm.cache_warmer_dms_24h` (DMS alarm
   per ALERT-4).
2. **Edit cron expression**: `autom8y/terraform/services/asana/variables.tf`
   lines 67-71 — change from `cron(0 2 * * ? *)` (daily 02:00 UTC) to
   `cron(0 */4 * * ? *)` (every 4h). This satisfies SLO-1 cadence per
   `.ledge/decisions/ADR-004-iac-engine-cache-warmer-schedule.md`.

Per PT-1 XC-2 staging: deploy alarms with `actions_enabled=false` first;
un-suppress after the Terraform cron lands AND a 1-3 day observation
period confirms baseline stability.

### 5(c) ALERT-3 + ALERT-5 ownership clarification (PT-4 Concern 3 FLAG)

**Re-handoff request**: explicit disposition for the following two alarms.
Each is phrased as a verifiable predicate so thermia can mechanically
adjudicate:

- **ALERT-3 (`WarmFailure` >= 1/hr, dimension `entity_type=offer`)**:
  Is this alarm already provisioned in the existing fleet alarm topology
  (the warmer Lambda's metrics namespace `autom8y/cache-warmer` per
  `src/autom8_asana/lambda_handlers/cache_warmer.py:20`), OR is new
  authoring required as part of Batch-D? Verifiable via
  `aws cloudwatch describe-alarms --alarm-name-prefix "AsanaCacheWarmer-Failure"`.
- **ALERT-5 (`FreshnessError` >= 2/hr)**: Is the `FreshnessErrorCount`
  metric emission codepath (which currently does NOT exist as a separate
  CloudWatch metric — `__main__.py:738-780` emits `botocore.ClientError`
  branches as friendly stderr lines, NOT as a metric with `kind` dimension)
  expected to be added in a follow-on procession, OR does thermia accept
  the present implementation (stderr-only, no CW metric) and the alarm
  becomes a CloudWatch Logs Insights query rather than a metric alarm?
  Verifiable via inspection of `Autom8y/FreshnessProbe` namespace metric
  list AND of the wireframe in `.ledge/specs/cache-freshness-observability.md:260-272`.

## 6. Latent Decisions Disposition

Per PT-4 Concern 8 — full enumeration. Every latent decision surfaced across
the procession is either RESOLVED or DEFER-FOLLOWUP-tagged.

### 6.1 Resolved

- **LD-P2-1** (`--sla-profile` flag naming + 4-class vocabulary) — resolved
  per FLAG-2 in predecessor §3; impl at
  `src/autom8_asana/metrics/__main__.py:163-168`.
- **LD-P2-2** (`CACHE_WARMER_LAMBDA_FUNCTION_NAME` preflight contract) —
  resolved as Option B (settings-field) variant via
  `CACHE_WARMER_LAMBDA_ARN` canonicalization in `49740a1f` PT-2 Option B
  refactor; CLI fails fast if env unset
  (test `test_force_warm_missing_function_name_env_exits_1`).
- **LD-P2-3** (force-warm idempotency: refresh anyway, not no-op) —
  resolved per P2 §4; impl at
  `src/autom8_asana/cache/integration/force_warm.py:159-385`.
- **LD-P3-1** (TTL persistence layered manifest + S3 sidecar w/
  override precedence) — resolved at
  `src/autom8_asana/metrics/sla_profile.py:1-652`.
- **LD-P3-2** (force-warm coalescer-routed; direct boto3 invoke FORBIDDEN) —
  STRUCTURALLY ENFORCED. `grep -n "boto3" src/autom8_asana/metrics/__main__.py`
  returns ONLY 3 docstring mentions (lines 252, 258, 314); zero direct
  boto3 lambda invocations in CLI force-warm paths. CLI delegates to
  `src/autom8_asana/cache/integration/force_warm.py` canonical surface.
- **LD-P4-1** (`autom8y_telemetry.aws.emit_success_timestamp` investigation)
  — resolved as Path B per commit `49740a1f` body: package does NOT
  auto-provision; alarm authored manually in stashed Terraform.
- **LD-P5A-3** (CoalescerDedupCount metric placement) — resolved at
  `src/autom8_asana/cache/dataframe/coalescer.py:34-67`; namespace
  `autom8y/cache-warmer` per ADR-006.
- **3 Batch-A engineer-discretion items** — resolved:
  - sentinel coalescer-key shape (`forcewarm:{entity_type}:{project_gid}`,
    constants at `src/autom8_asana/cache/integration/force_warm.py:54-57`);
  - best-effort L1 invalidation strategy (HYBRID per ADR-003);
  - MINOR-OBS-2 expansion to 6 botocore branches +
    `NoCredentialsError`.
- **Conflated-commit attribution** (commit `49740a1f`) — PT-3 adjudicated
  **leave-as-is + document**; entry in §2 row 4 is the document.
- **Pythia-flagged path error (Concern 6 BLOCK-2)** — closed per QA Phase E-2:
  `cd /Users/tomtenuta/Code/a8/repos/autom8y && git stash list` returns
  `stash@{0}: On anchor/adr-anchor-001-exemption-grant: Batch-B DMS alarm
  (LD-P4-1 Path B) — cross-repo defer`; stash empirically verified.

### 6.2 DEFER-FOLLOWUP

These items are NOT in P6 scope and are NOT in P7 verification scope. They
are surfaced for thermia visibility so future processions can pick them up:

- **LD-P2-4** XFetch beta calibration — beta=1.0 starting per CACHE:SRC-001;
  delta calibration requires production WarmDuration p50/p95 telemetry
  data which becomes available only post-deploy.
- **LD-P3-3** `max_entries=100` raise to 150 — at 14/100 current
  utilization (per predecessor §3.2 working-set sizing) there is no
  immediate pressure; raise becomes load-bearing only at 10x growth
  (~140 sections per P3 §3.2).
- **LD-P5A-1** INDEX ordering — entries appended chronologically per
  schema `.ledge/specs/handoff-dossier-schema.tdd.md:223-234`; no canonical
  ordering policy beyond append.
- **LD-P5A-2** status-vocabulary divergence — predecessor frontmatter uses
  `status: draft` (lifecycle vocabulary) vs this dossier's
  `status: PENDING-THERMIA-P7` (state-machine vocabulary per schema §1.2).
  Raise to ADR post-P6 if the divergence becomes load-bearing across
  more handoffs.
- **`ForceWarmLatencySeconds` no-alarm-today** — informational metric only;
  no SLO target defined yet. Followup: derive SLO post-P3 cadence
  resolution (DEF-2 seam).
- **`SectionAgeP95Seconds` low-N discrimination** — at N=14 current
  sections, P95 = 95th percentile is structurally degenerate (effectively
  the max). Becomes meaningful at N >= ~20 sections.
- **AP-3 named risk** (parquet not invalidated on task mutation) —
  explicitly NOT closed in this procession per
  `.ledge/specs/cache-freshness-architecture.tdd.md` §7;
  docstring at `src/autom8_asana/cache/integration/force_warm.py:28-30`
  records the risk acceptance.

## 7. Operational Constraints

### 7.1 Canary-in-prod (PRD §6 C-1)

Single-bucket (`autom8-s3`); no multi-env deployment topology. The
implementation ships and runs against production directly. No staging
environment exists. Validation occurs via:

- Existing test suite (unit + integration) — 436/1 PASS at HEAD `e4b5222d`.
- Heat-mapper-style manual probe of the production bucket post-deploy.
- P7 thermal-monitor in-anger probes against the deployed system.

### 7.2 Backwards-compat boundary (PRD §6 C-2)

Default-mode CLI output (`python -m autom8_asana.metrics active_mrr` with
no flags) is preserved **byte-for-byte**. Probe-4 baseline empirically
verified the dollar-figure line at `src/autom8_asana/metrics/__main__.py:807-808`
stdout format string is unchanged. Existing CI pipelines and scripts MUST
NOT break.

### 7.3 LD-P3-2 structural enforcement

Zero direct `boto3.client("lambda")` in CLI force-warm paths. Three boto3
references at `src/autom8_asana/metrics/__main__.py` lines 252, 258, 314
are docstring mentions only (verifiable via
`grep -n "boto3" src/autom8_asana/metrics/__main__.py` returning exactly
3 matches, all inside `"""..."""` blocks). The CLI delegates to
`src/autom8_asana/cache/integration/force_warm.py:159-385` canonical surface
which is itself coalescer-routed via `DataFrameCache`.

### 7.4 Rollback boundary

If `--force-warm` causes a regression in production:

- The flag is opt-in; default behavior is unchanged. Operators can simply
  not invoke it (zero-cost rollback).
- For an emergency feature-flag disable, gate the flag behind an env var
  (e.g., `AUTOM8Y_FORCE_WARM_ENABLED=true` required for the flag to be
  recognized). NOT shipped in P6; surface in next-procession scope if
  empirically needed.

### 7.5 SLO-1 starts in deficit (expected, NOT a defect)

Per `.ledge/specs/cache-freshness-observability.md:107-119` SLO-1 and
heat-mapper assessment: 9/14 sections currently exceed 6h staleness.
Until Batch-D 4h cron applies, `ParquetMaxAgeSLO` will NOT meet the
95%<6h target. SLO-1 reaches steady-state (green) approximately 6h
after Batch-D EventBridge schedule applies, assuming the new schedule
executes successfully on its first cycle. The on-call response runbook
(`.ledge/specs/cache-freshness-runbook.md` Stale-1) handles the
post-deploy SLO-1 deficit window.

## 8. Deadline Timeline

- Today: 2026-04-27.
- Verification deadline (parent telos D8): 2026-05-27.

Sequence:
- Re-handoff dossier authored (this artifact): 2026-04-27 (~1 day).
- Draft PR (T#43): immediate.
- Review + merge: 1-7 days (range bounded by reviewer availability).
- Production deploy: ~hours (deploy automation latency).
- Observation period: 1-3 days post-deploy (baseline stability check).
- Batch-D Terraform PR (cross-repo autom8y): 1-2 days.
- Batch-D apply (`terraform apply`): ~hours.
- thermia re-engagement (operator-paced; awaits all of the above).
- P7 design-review (Track A, 11-lens rubric): 1-2 days.
- P7 in-anger probes (Track B, Probe-1/2/3/5): 1-2 days.
- D8 attestation appended to this dossier `## Verification Attestation`
  heading.

Nominal: 8-15 days. Buffer: 15-22 days. Healthy margin against the 30-day
deadline.

## 9. Attester Acceptance Protocol

Per `.ledge/specs/handoff-dossier-schema.tdd.md` §4.3 (acceptance) and §4.4
(verification), the receiving rite appends two h2 headings to this dossier
body when engaging and discharging the handoff. They are reserved as empty
insertion points below:

- `## Attester Acceptance` — written when thermia.thermal-monitor (or
  fallback) engages this dossier.
- `## Verification Attestation` — written at P7 attestation completion
  (or `verification_deadline`, whichever first), recording verdict
  (`ATTESTED` | `ATTESTED-WITH-FLAGS` | `REJECTED-REOPEN`) per schema §4.4.

If the fallback predicate fires per schema §5.1 (mechanically verifiable:
ENOENT on `.claude/agents/thermia/` OR `thermia` absent from
`.knossos/KNOSSOS_MANIFEST.yaml`), the substituting agent
`sre.observability-engineer` (per inherited dossier §8.1 latent
decision #2 — SLO-shaped surface disambiguation) appends a
`## Fallback Activation Record` h3 heading per schema §5.2 BEFORE
discharging the verification gate.

## 10. Pre-existing Observations Carried Forward

Surfaced from the predecessor dossier §7 and the QA report; neither requires
thermia action — both are status-tracking carry-overs.

- **MINOR-OBS-1** (xdist test flake at
  `tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order`):
  handled in the parallel thermia → hygiene secondary handoff at
  `.ledge/handoffs/HANDOFF-thermia-to-hygiene-2026-04-27.md`. NOT in
  10x-dev or thermia P7 scope.
- **MINOR-OBS-2** (botocore traceback): SHIPPED at
  `src/autom8_asana/metrics/__main__.py:738-780` per WI-8. Resolved.

## Attester Acceptance

**Acceptance verdict**: ACCEPTED.
**Engaging agent**: thermia.thermal-monitor (PRIMARY path; fallback predicate negative).
**Engagement timestamp**: 2026-04-27T20:54Z (UTC).
**Engaging session**: `session-20260427-185944-cde32d7b` (resumed from PARKED via moirai; resume exit code 0).
**Receiving worktree**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.worktrees/thermia-cache-procession` on branch `thermia/cache-freshness-procession-2026-04-27`.

### A.1 Mechanical fallback predicate (per `.ledge/specs/handoff-dossier-schema.tdd.md` §5.1)

Verifiable inputs (all checked against thermia worktree HEAD `a732487f` and main repo state at acceptance time):

- `.claude/agents/thermia/` PATH: 5 thermia agents present at main-repo `.claude/agents/` (`potnia.md`, `heat-mapper.md`, `systems-thermodynamicist.md`, `capacity-engineer.md`, `thermal-monitor.md`); thermia worktree-local `.claude/agents/` shows hygiene-rite agents per worktree-config divergence (does NOT alter rite-engagement primary state — verifiable via `ari rite current` from main repo returning `Active Rite: thermia`).
- `.knossos/KNOSSOS_MANIFEST.yaml` content: `active_rite: thermia` (main repo).
- `.knossos/ACTIVE_RITE` content: `thermia` (main repo).

Conclusion: **PRIMARY thermia path engages.** `sre.observability-engineer` fallback NOT invoked. No `## Fallback Activation Record` heading required. NOTE for hygiene rite (delivered via parallel secondary handoff): the worktree-local `.claude/agents/` divergence between main repo and `.worktrees/thermia-cache-procession/` is a worktree-config artifact (worktree last touched while hygiene rite was engaged); recorded for hygiene awareness, NO BLOCKER for P7 acceptance.

### A.2 Inbound dossier acknowledgment

- **8 work items**: 6 SHIPPED (WI-1..WI-4, WI-7, WI-8); 2 PENDING-BATCH-D (WI-5 alarm + WI-6 cron) — by-design cross-repo coordination, not engineering gaps.
- **7-commit chain `a732487f..e4b5222d`** chain-of-custody verified via `git log --oneline a732487f..feat/cache-freshness-impl-2026-04-27` from main repo; 7 commits returned matching dossier §2.
- **Conflated commit `49740a1f`** PT-3 disposition (leave-as-is + document) ACCEPTED — receipt-grammar in §2 row 4 satisfies traceability under the "no behavioral regression" predicate; both halves (Batch-B CW emit + PT-2 Option B refactor) interdependent per the wiring rationale captured in the row.
- **QA verdict GO** (0 BLOCKING / 0 SERIOUS / 0 MINOR / 1 DEFER-OK; 436/1 tests; ruff/mypy clean across 66 source files; Phase E moto smoke PASS; Probe-4 baseline PASS) ACKNOWLEDGED. QA report at `.ledge/reviews/QA-impl-close-cache-freshness-2026-04-27.md` (impl branch commit `e4b5222d`).
- **Pythia BLOCK-1 closure** (FLAG-1 wiring at `7ed89918`) ACKNOWLEDGED — production CLI now invokes `emit_freshness_probe_metrics()` at `__main__.py:472` (sync recheck) and `__main__.py:893` (default-mode emission), absorbed by `_safe_emit_freshness_probe_metrics` wrapper at L241-263.

### A.3 P7 verification mode (per parent telos SQ-3)

Mode: **BOTH** design-review (Track A) + in-anger-probe (Track B). Confirmed.

| Track | Scope | Sequencing | Gating |
|---|---|---|---|
| **A — Design-review** | 11-lens rubric application to P2/P3/P4 specs; receipt-grammar audit; ADR-001..006 consistency check; ALERT-3/5 disposition validation; Probe-4 re-run as evidence | IMMEDIATE (runnable now without deployed Lambda) | None — depends only on tracked artifacts and unit-test reproducibility |
| **B — In-anger-probe** | Probe-1 (force-warm reduces oldest-parquet age); Probe-2 (alarm fires on max_mtime > SLA); Probe-3 (force-warm + freshness CLI compose, ADR-003); Probe-5 (5 metrics land in deployed CW) | DEFERRED until (i) PR #28 merge to main, (ii) production deploy, (iii) Batch-D apply | Per dossier §5(a) re-engagement trigger; Probe-4 already discharged at QA Phase D, MAY re-run as Track A evidence |

### A.4 §5(c) re-handoff request adjudication (ALERT-3 + ALERT-5 ownership FLAGs)

**ALERT-3 (`WarmFailure` >= 1/hr, `entity_type=offer`)** — DEFERRED-PENDING-AWS-VERIFICATION.

- Verifiable predicate (operator-runnable pre-deploy): `aws cloudwatch describe-alarms --alarm-name-prefix "AsanaCacheWarmer-Failure"`.
- IF the predicate returns `MetricAlarms != []`: alarm already provisioned in fleet topology (`Autom8y/AsanaCacheWarmer` namespace); NO new authoring required; Batch-D scope unchanged. Record outcome in §A.4 of the verification attestation.
- IF the predicate returns `MetricAlarms == []`: file as DEFER-FOLLOWUP for a Batch-D successor procession; Track B Probe-2 will detect the gap empirically post-deploy. Adjudicating verdict at attestation: ATTESTED-WITH-FLAGS unless the alarm is provisioned by attestation time.

**ALERT-5 (`FreshnessError` >= 2/hr)** — ACCEPTED present implementation (stderr-only via WI-8 at `__main__.py:738-780`).

- Rationale: the `FreshnessErrorCount` metric does NOT yet exist as a separate CloudWatch metric; the alarm semantically becomes a CloudWatch Logs Insights query rather than a metric alarm.
- Adopting the present implementation as canonical for P6/P7 scope.
- Future procession may add a `FreshnessErrorCount` CW metric with `kind` dimension (mapping to the 6 botocore branches in WI-8) if production volume warrants. Recorded as DEFER-FOLLOWUP item in P7 verification scope; NO BLOCKER for attestation.

### A.5 DEFER-FOLLOWUP enumeration acknowledged (dossier §6.2)

All 6 DEFER-FOLLOWUP items NOT in P7 verification scope; acknowledged for forward visibility:

- **LD-P2-4** XFetch beta calibration — beta=1.0 starting per CACHE:SRC-001; production WarmDuration p50/p95 telemetry post-deploy.
- **LD-P3-3** `max_entries=100` raise to 150 — at 14/100 utilization; load-bearing only at ~10x growth.
- **LD-P5A-1** INDEX ordering — chronological append per schema §223-234.
- **LD-P5A-2** status-vocabulary divergence (frontmatter `status: draft` vs `PENDING-THERMIA-P7`) — raise to ADR if it becomes load-bearing.
- **`ForceWarmLatencySeconds` no-alarm-today** — informational only; SLO post-P3 cadence resolution at DEF-2 seam.
- **`SectionAgeP95Seconds` low-N degeneracy** — meaningful at N >= ~20 sections (current N=14).
- **AP-3 named risk** (parquet not invalidated on task mutation) — explicitly NOT closed; risk-acceptance docstring at `force_warm.py:28-30`.

### A.6 Pre-existing observations (dossier §10)

- **MINOR-OBS-1** (xdist test flake) — handed to hygiene rite via `.ledge/handoffs/HANDOFF-thermia-to-hygiene-2026-04-27.md`. NOT in P7 scope. NO ACTION.
- **MINOR-OBS-2** (botocore traceback) — SHIPPED at WI-8. Resolved. NO ACTION.

### A.7 P7 procession plan (Potnia-dispatched, recorded for chain-of-custody)

- **Phase P7.A — Track A design-review** (immediate; thermal-monitor; nominal 1-2 days).
  - Sub-phase A.1: 11-lens rubric application against P2/P3/P4 specs with receipts.
  - Sub-phase A.2: ADR-001..006 consistency cross-check + receipt-grammar audit on §2 commit ledger.
  - Sub-phase A.3: ALERT-3 predicate execution (operator step) + ALERT-5 disposition recording.
  - Sub-phase A.4: Probe-4 re-run as design-review evidence (already PASS at QA Phase D).
- **Phase P7.B — Track B in-anger-probes** (post-deploy + post-Batch-D apply; thermal-monitor; nominal 1-2 days).
  - Probes 1, 2, 3, 5 against deployed system; Probe-2 specifically validates ALERT-3/4/5 firing semantics.
- **Pythia touchpoints**: PT-A4 (`before_attestation`, fires before P7.A); PT-A5 (`sprint_close`, fires after attestation completes).
- **Verification deadline**: 2026-05-27 (parent telos `verify-active-mrr-provenance` D8). Today: 2026-04-27. Buffer: 30 days; nominal 8-15 day discharge sequence per dossier §8 timeline.

### A.8 Attestation chain commitment

`thermia.thermal-monitor` authors `## Verification Attestation` h2 at P7 close per schema §4.4 with verdict ∈ {`ATTESTED`, `ATTESTED-WITH-FLAGS`, `REJECTED-REOPEN`}.

Failure-mode contingencies:

- IF Track B blocks past 2026-05-27 due to deferred deploy or Batch-D apply: thermal-monitor authors `ATTESTED-WITH-FLAGS` recording (i) Track A discharge, (ii) Track B blocked-pending status with explicit gating predicates, (iii) D8 telos discharge negotiated with operator (extension request OR partial-discharge acceptance).
- IF Track A surfaces a SERIOUS or BLOCKING design defect: thermal-monitor authors `REJECTED-REOPEN` with the defect catalogued and a re-handoff request to either thermia P2/P3/P4 (architecture/capacity/observability redesign) or 10x-dev P6 (impl correction).

### A.9 Receipts

- Resume command exit code: 0 (moirai; `2026-04-27T20:54:18Z`).
- Inbound dossier: extracted from impl branch commit `0ac99aba` via `git checkout 0ac99aba -- .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md`; 452 lines pre-acceptance-append.
- Predecessor handoff `HANDOFF-10x-dev-to-thermia-2026-04-27.md` *kickoff* version (commit `37932b89`) is being superseded at this path; kickoff content remains preserved in git history at `13cf3433` and `37932b89` parents.
- Worktree: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.worktrees/thermia-cache-procession`.
- Branch: `thermia/cache-freshness-procession-2026-04-27`.
- Acceptance commit (this artifact): authored on thermia branch with `git add -f` (gitignore `**/.ledge/*` workaround per scar-tissue from predecessor sprint).

## Verification Attestation

**Attestation status**: `TRACK-A-COMPLETE-TRACK-B-PENDING` (provisional checkpoint per acceptance §A.8 contingency template).
**Attester agent**: `thermia.thermal-monitor` (PRIMARY; `heat-mapper` cross-check on lens-3 per Axiom 1 intra-rite seam).
**Attester rite**: `thermia`.
**Rite-disjoint from authoring**: TRUE (10x-dev built; thermia verifies; Axiom 1 satisfied at outer cross-rite seam).
**Track A close timestamp**: 2026-04-27T~21:00Z.
**Final verdict timestamp**: PENDING — gates on Track B completion (deadline 2026-05-27).

### V.1 Track A — Design-Review — CLOSED

Synthesis at `.ledge/reviews/P7A-track-A-close-2026-04-27.md`. 7 sub-phase artifacts:

- `.ledge/reviews/P7-procession-plan-2026-04-27.md` (Potnia-authored procession plan)
- `.ledge/reviews/P7A-lens-disposition-2026-04-27.md` (CONCUR with Potnia §3 lens table)
- `.ledge/reviews/P7A-design-review-2026-04-27.md` (5 lenses PASS/PASS-WITH-NOTE; lens-3 SUSPENDED)
- `.ledge/reviews/P7A-cross-check-lens3-observability-2026-04-27.md` (heat-mapper PASS-WITH-NOTE; CONCUR)
- `.ledge/reviews/P7A-adr-receipt-audit-2026-04-27.md` (0 DRIFT-FAIL; 6 ADRs verified)
- `.ledge/reviews/P7A-alert-predicates-2026-04-27.md` (LIVE-AWS evidence; 3 NAMED DRIFT items)
- `.ledge/reviews/P7A-probe4-rerun-2026-04-27.md` (PASS-WITH-CAVEAT — QA-receipt-trusted)
- `.ledge/reviews/P7A-defer-adjudication-2026-04-27.md` (CONCUR with Potnia §4 pre-classification)

Verdict for design-grade portion: **all 6 LOAD-BEARING lenses PASS**; **all 4 telos-adjacent DEFERs promoted with named owners**; **0 BLOCKING / 0 SERIOUS / 3 NAMED DRIFT (spec/doc only)**.

### V.2 Track B — In-Anger-Probe — BLOCKED

Track B (Probes 1, 2, 3, 5) cannot execute until all of:

- PRE-1: PR #28 merged to main.
- PRE-2: production deploy completes (deploy lag ≤ 7 days from merge).
- PRE-3: Batch-D xrepo Terraform PR merged (autom8y `anchor/adr-anchor-001-exemption-grant` stash pop + cron edit + 5 ALERT alarm definitions). PR# not yet authored.
- PRE-4: 5 ALERT alarms (ALERT-1..5) provisioned and `ActionsEnabled=true` (currently 0 of 5 exist per P7.A.3 PRED-11 live AWS scan).
- PRE-5: deploy SHA matches PR #28 merge SHA.

Track B observation window opens upon PRE-1..PRE-5 clearing. Probe-4 already discharged at QA Phase D commit `e4b5222d` (see `P7A-probe4-rerun-2026-04-27.md`); only Probes 1, 2, 3, 5 remain for Track B.

### V.3 Carry-forward DRIFT items (3, all spec/doc; filed to hygiene rite)

| ID | Description | Owner | Resolution path | Telos-class |
|---|---|---|---|---|
| DRIFT-1 | P4 §3.3 ALERT-3 namespace mis-spec (`autom8y/cache-warmer` → actual `autom8/lambda::StoryWarmFailure`) | hygiene rite (next `/hygiene` cycle) | P4 spec patch + ADR-007 amending ADR-006 to differentiate CLI / coalescer / warmer namespaces | telos-adjacent |
| DRIFT-2 | Runbook DMS-1 `[DMS_METRIC_NAME]` placeholder unresolved (operator can't run runbook without source) | hygiene rite | 1-line patch with explicit CW query template citing `autom8/lambda::StoryWarmSuccess` per P7.A.3 §4 | telos-adjacent |
| DRIFT-3 | P4 ALERT-5 over-claim (CW metric alarm vs stderr-only impl — accepted §A.4) | hygiene rite | P4 spec patch reframing ALERT-5 as CW Logs Insights query rather than metric alarm | telos-adjacent (already accepted; spec correction only) |

Filed via APPENDIX to `.ledge/handoffs/HANDOFF-thermia-to-hygiene-2026-04-27.md`.

### V.4 Pythia PT-A4 carry-forward FLAG dispositions

All 5 PT-A4 FLAGs dispositioned at Track A close (per `P7A-track-A-close-2026-04-27.md` §5):

- FLAG-1 (self-review surface): RESOLVED via heat-mapper cross-check.
- FLAG-2 (Track B precondition pinning): DOCUMENTED in this attestation §V.2.
- FLAG-3 (11-lens discipline): RESOLVED via P7.A.0 disposition table.
- FLAG-4 (DEFER tagging): RESOLVED via P7.A.5 adjudication.
- FLAG-5 (worktree agent-dir drift): RECORDED for `/hygiene`.

### V.5 Final-verdict completion criteria

When Track B completes, this section is updated with one of:

- **`ATTESTED`**: PRE-1..PRE-5 PASS AND Probes 1, 2, 3, 5 PASS clean AND no Track B observation-window firings on freshness-bound (lens 1) or failure-mode (lens 4) alarms AND DRIFT-1/2/3 patched in hygiene rite.
- **`ATTESTED-WITH-FLAGS`**: PRE-1..PRE-5 PASS AND Probes 1, 2, 3, 5 PASS AND ≤2 telos-adjacent DEFERs / DRIFTs remain open with named owner+date AND no Track B alarm firings on critical lenses.
- **`REJECTED-REOPEN`**: any Probe 1/2/3/5 FAIL OR Track B alarm fires on freshness-bound or failure-mode OR ≥1 telos-adjacent DRIFT unresolved without owner OR deadline 2026-05-27 passed without Track B execution.

### V.6 Operator action checklist (Track B unblock sequence)

1. Hygiene rite engagement: patch DRIFT-1/2/3 (see §V.3 hygiene appendix at `.ledge/handoffs/HANDOFF-thermia-to-hygiene-2026-04-27.md`). NON-blocking for Track B.
2. PR #28 review + merge to main.
3. Production deploy automation runs.
4. Batch-D xrepo PR (autom8y stash pop + cron edit + 5 alarm authoring); apply with `actions_enabled=false` initially.
5. 1-3 day baseline observation; flip `actions_enabled=true`.
6. Re-engage thermia P7.B for in-anger probe execution.
7. Update this attestation block with final verdict.

### V.7 Receipts

- Acceptance commit (predecessor to attestation): `2253ebc1` on `thermia/cache-freshness-procession-2026-04-27`.
- Track A close commit: appended to this dossier in same commit batch as P7.A.0..A.5 + Track A close synthesis + hygiene handoff appendix.
- Live AWS predicate execution: account `696318035277`, IAM `arn:aws:iam::696318035277:user/tom.tenuta`, timestamp 2026-04-27T~21:00Z.
- Cross-check disjoint critic: `heat-mapper` (no authorship surface in P4) per Pythia FLAG-1 remediation.

### V.8 Mid-attestation state update (2026-04-28T~07:00Z)

Procession state has advanced since Track A close. This block records the deltas.

**PR-merge clearance**:

- **PRE-1 ✓** PR #28 (`feat/cache-freshness-impl-2026-04-27`, 10x-dev impl phase) MERGED to main as commit `c00ed989` at 2026-04-27T22:20:59Z.
- **PR #29 (hygiene W2 cleanup)** MERGED to main as commit `8fd0aefb` at 2026-04-27T22:18:33Z. This carries:
  - Area A — D7 env-cruft comment cleanup (3 files; canonical Pydantic field declarations preserved per PRD §6 C-1).
  - Area B — `.gitignore` allow-list for `.ledge/{handoffs,decisions,reviews,specs,spikes}/` (Option A pragmatic; survives `ari sync` regeneration).
  - Area C — Hypothesis seed pin via `derandomize=True` resolving MINOR-OBS-1 xdist flake.

**Hygiene W1 status**: STILL ON THERMIA BRANCH (commit `7fa59aa4`). DRIFT-1/2/3 patches + ADR-007 + P7.A.3 §10 CORRECTION are NOT YET in main; will land via the future thermia-close PR.

**Track B precondition re-evaluation**:

| PRE | Status | Notes |
|---|---|---|
| PRE-1 (PR #28 merged) | **✓ CLEARED** | merge SHA `c00ed989` |
| PRE-2 (deploy lag ≤7d) | ⏳ DEPLOY-PIPELINE-DEPENDENT | ` operator-paced; production CI/CD cycle |
| PRE-3 (Batch-D xrepo PR merged) | ⏳ NOT-YET-AUTHORED | autom8y repo: stash pop + cron edit + 3 fresh metric alarms (ALERT-1, ALERT-2, ALERT-3); ALERT-5 is now Logs Insights query (no metric alarm); ALERT-6 NO ALARM C-6 |
| PRE-4 (5 ALERT alarms `ActionsEnabled=true`) | ⏳ BATCH-D-DEPENDENT | 0 of expected alarms exist today (per P7.A.3 PRED-1, PRED-11) |
| PRE-5 (deploy SHA matches PR #28 merge) | ⏳ DEPLOY-PIPELINE-DEPENDENT | cleared by PRE-2 cycle |

**Two preconditions remain blocked on operator-driven events** (deploy automation, Batch-D Terraform authoring + apply). Track B can begin once PRE-2 + PRE-3/4/5 clear.

**Procession-side discipline note** (carried from hygiene W1.P1 surfacing): the `.ledge/decisions/ADR-007-cw-namespace-tri-partition.md` documents the CORRECTED namespace topology after the thermia P7.A.3 mis-attribution was caught at hygiene W1.P1 source-archaeology. Track B Probe-2 (alarm fires on max_mtime > SLA) should validate ALERT-3 against `autom8y/cache-warmer::WarmFailure` (runtime-config namespace) NOT `autom8/lambda::StoryWarmFailure` (which is a different module's metric). Track B alarm-target verification predicates should be updated to match ADR-007 prior to Probe execution.

**Deadline runway**: today 2026-04-28; deadline 2026-05-27; **29 days remaining**. Nominal Track B execution 1-2 days post-Batch-D apply + 1-3 day baseline observation. Comfortable margin remains.

### V.9 Batch-D xrepo PR opened (2026-04-28)

**autom8y/autom8y#163** ([batch-d/cache-freshness-alarms-2026-04-28](https://github.com/autom8y/autom8y/pull/163)) OPEN at branch HEAD `974c94a2`. CI shows 5/5 SUCCESS at first scan (bifrost-001, dependency-review, gitleaks, Secretspec Cross-Validation, Detect Changes). State: `MERGEABLE`.

Scope:
- 4 alarms (ALERT-1/2/3/4) authored with `actions_enabled=false` per PT-1 XC-2 staging.
- `cache_warmer_schedule` cron edit `cron(0 2 * * ? *)` → `cron(0 */4 * * ? *)` per ADR-004.
- `terraform fmt` + `terraform validate`: PASS.

Operator unblock sequence + 4-probe execution sequence + final-verdict criteria fully spelled out at `.ledge/reviews/P7B-readiness-checklist-2026-04-28.md` (this commit batch).

**Track B precondition status (refreshed 2026-04-28)**:

| PRE | Status |
|---|---|
| PRE-1 | ✓ CLEARED (`c00ed989`) |
| PRE-2 | ⏳ deploy-pipeline cycle |
| PRE-3 | ⏳ #163 awaiting reviewer merge |
| PRE-4 | ⏳ apply + 1-3d observation + flip |
| PRE-5 | ⏳ deploy-pipeline cycle |

Mid-attestation live AWS baseline holds steady (no metric inventory drift between 2026-04-27 and 2026-04-28 scans).
