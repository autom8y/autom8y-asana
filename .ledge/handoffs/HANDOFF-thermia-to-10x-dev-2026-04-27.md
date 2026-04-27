---
type: handoff
status: draft  # handoff lifecycle state: DRAFT → ATTESTED-PENDING-10x-dev → ATTESTED (per .ledge/specs/handoff-dossier-schema.tdd.md §1.2). Mapped to canonical lifecycle vocabulary `draft` until 10x-dev rite writes Attester Acceptance section.
handoff_type: implementation
schema_version: 1
originating_rite: thermia
receiving_rite: 10x-dev
fallback_rite: null
originating_session: session-20260427-185944-cde32d7b
authored_on: 2026-04-27
authored_by: thermia.potnia (orchestration via general-purpose author)
worktree: .worktrees/thermia-cache-procession/
branch: thermia/cache-freshness-procession-2026-04-27
initiative_slug: cache-freshness-procession-2026-04-27
parent_initiative: verify-active-mrr-provenance
prd_anchor: .ledge/specs/verify-active-mrr-provenance.prd.md
attestation_required: true
attestation_chain: thermia.thermal-monitor (post-impl re-handoff for P7)
verification_deadline: 2026-05-27
design_references:
  - .ledge/specs/cache-freshness-architecture.tdd.md
  - .ledge/specs/cache-freshness-capacity-spec.md
  - .ledge/specs/cache-freshness-observability.md
  - .ledge/specs/cache-freshness-runbook.md
  - .ledge/decisions/ADR-003-memorytier-post-force-warm-staleness.md
  - .sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md
index_entry_appended: true
---

# HANDOFF — thermia → 10x-dev (cache-freshness-procession-2026-04-27)

This dossier transfers the implementation scope of the thermia design
substrate (P1 heat-mapper assessment + P2 architecture TDD + P3 capacity
spec + P4 observability + runbook + ADR-003) to the 10x-dev rite for the
P6 implementation phase. The receiving rite IS the engineering rite; no
fallback rite is declared (engineering work has no rite-disjoint
engineering substitute — only the verification surface requires
disjointness, which is held by thermia.thermal-monitor at P7).

The thermia rite has discharged its design responsibilities for the
parent telos `verify-active-mrr-provenance` D5 + D10 + NG4 + NG8
concerns. The post-impl re-handoff (10x-dev → thermia) triggers P7
thermal-monitor design-review + in-anger-probe attestation, discharging
D8 (`verified_realized` gate) by the 2026-05-27 deadline.

## 1. Implementation scope summary

The 10x-dev rite must build the following work items. Each item carries a
file:line target and a verifiable acceptance predicate (see §4). Items
marked DEFER-FOLLOWUP are surfaced as known horizon items; they are not
in P6 scope but are tracked for future processions.

1. **Force-warm CLI affordance (PRD NG4)** — add `--force-warm` and
   `--wait` flags to `src/autom8_asana/metrics/__main__.py` argparse
   structure. Flag form (not subcommand) per P2 §4. Default async
   (`InvocationType="Event"`); opt-in sync (`InvocationType="RequestResponse"`)
   when `--wait` is set. Coalescer-routed via `DataFrameCache` (per
   LD-P3-2 resolution below). Idempotent: refresh anyway, not no-op
   (P2 §4 idempotency decision). Pre-validates `ASANA_CACHE_S3_BUCKET`
   env var before invoking Lambda (catches MINOR-OBS-2 bucket-typo
   case before reaching the warmer).

2. **SLA enforcement extension (PRD NG8)** — add
   `--sla-profile={active|warm|cold|near-empty}` flag mapping to
   per-class staleness thresholds. Profile names canonicalized per
   FLAG-2 / LD-P2-1 below. Threshold values: ACTIVE=6h, WARM=12h,
   COLD=24h, near-empty=7d (per P3 §2.2). Existing `--strict` flag at
   `src/autom8_asana/metrics/__main__.py:341` is preserved verbatim
   (PRD C-2 backwards-compat). New `--sla-profile` is additive.

3. **TTL persistence implementation (LD-P3-1 resolved below)** — write
   per-section TTL class assignment to manifest at
   `.know/cache-freshness-ttl-manifest.yaml` (canonical default) AND S3
   sidecar at `s3://autom8-s3/dataframes/{project_gid}/cache-freshness-ttl.json`
   (runtime override). Override precedence: S3 sidecar > manifest.
   Engineer implements both; warmer reads from sidecar at warm time;
   CLI reads manifest at startup.

4. **CloudWatch metric emissions (P4 §4 + §10)** — emit five metrics
   from CLI to namespace `Autom8y/FreshnessProbe`:
   - `MaxParquetAgeSeconds` (from `FreshnessReport.max_age_seconds`,
     `src/autom8_asana/metrics/freshness.py:202`)
   - `ForceWarmLatencySeconds` (per FLAG-1 instrumentation boundary
     resolution below)
   - `SectionCount` (from `FreshnessReport.parquet_count`,
     `src/autom8_asana/metrics/freshness.py:153`)
   - `SectionAgeP95Seconds` (requires `from_s3_listing` enhancement at
     `src/autom8_asana/metrics/freshness.py:142-157` to retain per-key
     mtime list)
   - `SectionCoverageDelta` (informational only — NO alarm; see
     P4 §4 C-6 guard)
   Plus one additional from coalescer: `CoalescerDedupCount` per P4
   Lens 8.

5. **DMS CloudWatch alarm creation OR verification (LD-P4-1 resolved
   below)** — investigation pathway: read
   `autom8y_telemetry.aws.emit_success_timestamp` source from external
   package; confirm metric name; create CloudWatch alarm per P4 §8
   ALERT-4 config. If `autom8y_telemetry` package auto-provisions the
   alarm, DEFER and document in re-handoff.

6. **cache_warmer Lambda schedule explicit in IaC (P3 D10 deferral
   discharge)** — declare EventBridge rule with cron expression in IaC
   (Terraform/SAM/CDK — engineer chooses based on existing fleet IaC
   topology). Cadence: 4h for ACTIVE-class entity warm cycle (per P3
   §2.2 force-warm cadence row). Schedule must satisfy SLO-1 (95% of
   ACTIVE sections < 6h max age over 7-day rolling window per P4 §2
   SLO-1).

7. **MemoryTier invalidation strategy per ADR-003** — implement HYBRID
   per `--wait` flag: when `--force-warm --wait` succeeds, invalidate
   L1 `MemoryTier` entry for affected `entity_type:project_gid` key
   via `DataFrameCache.invalidate()` or equivalent surface at
   `src/autom8_asana/cache/integration/dataframe_cache.py`. Default
   async mode does NOT invalidate L1 (operator accepts SWR rebuild
   lag).

8. **MINOR-OBS-2 botocore traceback fix** — extend exception handler at
   `src/autom8_asana/metrics/__main__.py:235` to catch
   `botocore.exceptions.ClientError` for the `NoSuchBucket` case;
   emit AC-4.2-shaped friendly stderr line analogous to
   `src/autom8_asana/metrics/freshness.py:164-177` not-found mapping.

9. **DEFER-FOLLOWUP items (NOT in P6 scope)**:
   - **`max_entries=100` raise to 150** (LD-P3-3) — at 14/100 current
     utilization there is no immediate pressure; raise becomes
     load-bearing only at 10x growth (~140 sections per P3 §3.2).
     Surface in re-handoff as known horizon item.
   - **XFetch refresh-ahead beta calibration (LD-P2-4)** — beta=1.0
     starting value per P2 §6 + CACHE:SRC-001. P3 calibration of
     delta requires production WarmDuration p50/p95 data; this is a
     followup procession.
   - **Event-driven re-warm via Asana webhooks** (heat-mapper DEF-5,
     `.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md:460`).

## 2. Design substrate (ground-truth artifacts)

The implementation MUST be grounded in these artifacts. File:line
citations are the authority for behavior; this dossier paraphrases
where helpful but the linked artifacts are normative.

### P1 thermal assessment

`.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md`
(473 lines) — 6-gate framework verdict: **OPERATIONALIZE** (lines
163-172). Mtime histogram classification (lines 44-60) shows 9/14
sections exceed PRD G2 6h threshold at handoff. AP-1 (undocumented
warmer schedule), AP-2 (no per-section TTL), AP-3 (MutationInvalidator
gap) at lines 117-135 + 416-435.

### P2 architecture TDD

`.ledge/specs/cache-freshness-architecture.tdd.md` (759 lines):

- §3 multi-level hierarchy (lines 224-273) — L1 MemoryTier / L2 S3
  parquet / L3 Asana origin
- §4 force-warm CLI affordance design (lines 304-424) — flag form,
  pre-validation, sync vs async, coalescer-routed
- §5 SLA enforcement model (lines 427-514) — `--strict` continuation;
  named SLA profile concept introduced
- §6 XFetch refresh-ahead augmentation (lines 516-585) — beta=1.0
  starting; P6 implementation site
  `src/autom8_asana/cache/dataframe/factory.py`
- §7 AP-3 named risk (lines 587-645) — explicitly NOT closed in this
  procession; tolerable for current scope
- ADR-003 (architecture-internal) cache-aside continuation; ADR-004 AP
  positioning

### P3 capacity spec

`.ledge/specs/cache-freshness-capacity-spec.md` (444 lines):

- §1 D10 IaC probe (lines 26-43) — IaC schedule [DEFER — not in
  worktree]
- §2 Per-section TTL design (lines 65-129) — 4-class taxonomy:
  ACTIVE 6h / WARM 12h / COLD 24h / Near-empty 7d
- §3 Working-set sizing (lines 132-189) — current 14 sections /
  ~0.91 MB in-memory
- §4 Force-warm cost envelope (lines 193-235) — < $0.30/month at
  realistic operator load
- §5 Stampede protection (lines 238-286) — Coalescer + Idempotency
  Key (no lease tokens)
- §6 Eviction policy (lines 290-323) — N/A for S3, LRU for MemoryTier

### P4 observability + runbook

`.ledge/specs/cache-freshness-observability.md` (729 lines):

- §1 4 SLI definitions (lines 19-95)
- §2 3 SLO definitions (lines 99-149)
- §3 6 alert designs (lines 153-279) — ALERT-4 DMS heartbeat is
  highest-urgency
- §4 Section-coverage telemetry (lines 282-311) — D5 discharge
- §6 11-lens cross-architecture validation rubric (lines 343-429)
- §7 5 in-anger probes (lines 433-602) — Probe-3 tests ADR-003
  acceptance
- §8 DMS alarm verification + required config (lines 607-655)

`.ledge/specs/cache-freshness-runbook.md` (400 lines) — Stale-1,
Warmer-1, DMS-1, S3-1 operational scenarios.

### ADR-003 (this procession)

`.ledge/decisions/ADR-003-memorytier-post-force-warm-staleness.md` —
HYBRID decision: invalidate L1 on `--force-warm --wait`; accept SWR lag
on default async.

## 3. Resolved load-bearing decisions

This section resolves the four `RESOLVE-AT-P5-HANDOFF` latent decisions
and two PT-A2 FLAGs that were held open through the design phases.

### FLAG-1 — `ForceWarmLatencySeconds` instrumentation boundary

**Resolution**: `ForceWarmLatencySeconds` is measured from the moment
the CLI parses the `--force-warm` flag (start timestamp captured in
argparse post-parse hook in `src/autom8_asana/metrics/__main__.py`) to
the moment a subsequent `FreshnessReport` recheck reports the affected
prefix as fresh (`FreshnessReport.stale == False`). The measurement
**INCLUDES** any time spent waiting on the
`DataFrameCacheCoalescer` (per P3 §5.1 coalescer-routed force-warm).
The measurement **DOES NOT** start from the Lambda invoke timestamp
(too late — misses queue/coalescer wait) and **DOES NOT** end at
Lambda response (too early — does not verify the freshness recheck
observes the new state).

For the `--wait` (sync) path, the measurement runs end-to-end in a
single CLI process. For the default async path, the metric is emitted
as `null` or omitted (no end timestamp available within a single
invocation); SLO-1 (`MaxParquetAgeSeconds`) carries the freshness
verdict instead.

**Impact**: P4 §1 SLI-2 instrumentation (line 47) is now boundary-
defined. P7 Probe-1 and Probe-3 acceptance criteria
(`.ledge/specs/cache-freshness-observability.md:457-538`) consume this
boundary for their pass/fail predicates.

### FLAG-2 — SLA class vocabulary canonicalization

**Resolution**: Adopt **P3's 4-class taxonomy** as canonical across
the procession. The flag is `--sla-profile`; accepted values are
`active|warm|cold|near-empty` (lowercase, hyphenated for `near-empty`).
This supersedes:

- P2 §5 3-class table (active_mrr / informational / archival) at
  `.ledge/specs/cache-freshness-architecture.tdd.md:463-468` — the
  P2 table is treated as informal description; P3's 4-class is
  load-bearing.
- P4 SLO-1 1-class collapse (single 6h ACTIVE threshold across all
  sections) at `.ledge/specs/cache-freshness-observability.md:107-111`
  — P4 SLO-1 stratifies by class once the GID-to-name mapping
  (DEF-1) lands.

P4 SLO-1 stratification post-DEF-1: per-class targets are
ACTIVE < 6h, WARM < 12h, COLD < 24h, near-empty < 7d, evaluated at
95% over rolling 7-day window per class.

**Impact**: §1 work item 2 (SLA enforcement extension) consumes
this taxonomy. The flag and its accepted values are part of the
public CLI surface.

### LD-P2-1 — `--sla-profile` flag naming and 4-class vocabulary

**Resolution** (per FLAG-2): Flag name = `--sla-profile`. Accepted
values = `active|warm|cold|near-empty`. Default value = `active`
(strictest) when flag is absent. Engineer implements per P2 §5
named-profile concept (lines 442-471) using P3 §2.2 threshold values:

| Profile | Threshold | Source anchor |
|---|---|---|
| `active` | 21600 (6h) | P3 §2.2 ACTIVE-class |
| `warm` | 43200 (12h) | P3 §2.2 WARM-class |
| `cold` | 86400 (24h) | P3 §2.2 COLD-class |
| `near-empty` | 604800 (7d) | P3 §2.2 Near-empty-class |

Until DEF-1 (GID-to-section-name mapping) is resolved, all sections
are treated as `active`-class for warming-frequency purposes
(conservative bound per P3 §2.1 fallback note).

### LD-P3-1 — TTL persistence mechanism

**Resolution**: Layered persistence with override precedence.

- **Default canonical persistence**: manifest file at
  `.know/cache-freshness-ttl-manifest.yaml`. Read at CLI startup;
  written by an offline IaC/admin process when TTL classes change.
  Schema (per-section): `{section_gid: str, sla_class:
  active|warm|cold|near-empty, threshold_seconds: int}`.
- **Runtime override**: S3 sidecar at
  `s3://autom8-s3/dataframes/{project_gid}/cache-freshness-ttl.json`.
  Same schema. Read by warmer at warm time AND by CLI on the
  freshness-probe path. If sidecar exists, it overrides the manifest
  for that project_gid.
- **Override precedence**: S3 sidecar > manifest > built-in defaults
  (4-class table above).

**Engineer (P6) implements both**. The warmer write path
(`src/autom8_asana/lambda_handlers/cache_warmer.py` — DO NOT modify
warmer per PRD C-4; instead, add the sidecar read path in a new helper
module that the warmer imports). The CLI read path is in
`src/autom8_asana/metrics/__main__.py` startup or in a new
`src/autom8_asana/metrics/sla_profile.py` module (engineer chooses).

### LD-P3-2 — Force-warm coalescer-routing constraint

**Resolution**: Force-warm CLI **MUST** route through `DataFrameCache`
(coalescer-protected). Direct Lambda invoke (bypassing
`DataFrameCacheCoalescer`) is **FORBIDDEN**.

This is load-bearing per P3 §5.1
(`.ledge/specs/cache-freshness-capacity-spec.md:240-256`). The
coalescer at `src/autom8_asana/cache/dataframe/coalescer.py:77`
(`max_wait_seconds=60.0`) prevents in-process thundering herd; the
Lambda idempotency-key window (5-minute) handles cross-process
deduplication (P3 §5.2 hybrid decision).

**Engineer (P6) verifies wiring** by:
1. Adding the force-warm Lambda invocation BEHIND a
   `DataFrameCache.warm_async()` (or equivalent existing API) call,
   not as a direct `boto3.client("lambda").invoke()` adjacent to
   parsing.
2. Confirming the `try_acquire_async()` path is hit before
   `boto3.invoke()` is reached.
3. P7 thermal-monitor probes verify (Probe-3 + Lens 8 in
   `.ledge/specs/cache-freshness-observability.md:399-405`).

### LD-P4-1 — `autom8y_telemetry.aws.emit_success_timestamp` metric name

**Resolution**: Investigation pathway with conditional execution.

Engineer (P6) MUST:

(a) Read the source of
    `autom8y_telemetry.aws.emit_success_timestamp` from the external
    package (likely under
    `~/Code/.../autom8y-telemetry/src/autom8y_telemetry/aws/...`
    or installed in `site-packages`).
(b) Confirm the CloudWatch metric name emitted by the function.
(c) **If the package does NOT auto-provision the alarm**: create the
    CloudWatch alarm matching P4 §8 ALERT-4 config
    (`.ledge/specs/cache-freshness-observability.md:634-655`),
    substituting the confirmed metric name into `MetricName`.
(d) **If the package DOES auto-provision the alarm**: DEFER alarm
    creation; document the auto-provisioning path and alarm name in
    the P6 → P7 re-handoff dossier; P7 thermal-monitor verifies the
    alarm exists in CloudWatch console.

This is the resolution path; the binary outcome (a/b/c/d) is recorded
in the post-impl re-handoff dossier (`HANDOFF-10x-dev-to-thermia-{date}.md`).

## 4. Implementation acceptance criteria

Each work item from §1 declares "DONE" as a verifiable predicate.

### AC-1: Force-warm CLI affordance (NG4)

- **DONE when**:
  - `python -m autom8_asana.metrics --force-warm` exits 0 (async; emits
    "force-warm invoked (async); monitor DMS metric" to stderr per P2
    §4 step 5).
  - `python -m autom8_asana.metrics --force-warm --wait` exits 0 on
    Lambda success; exits 1 on Lambda failure.
  - Pre-validation: when `ASANA_CACHE_S3_BUCKET` is unset or set to a
    non-existent bucket, exits 1 with friendly stderr line (NOT a raw
    botocore traceback) BEFORE Lambda invocation.
- **Lands at**: `src/autom8_asana/metrics/__main__.py` (argparse
  additions + new handler function); engineer chooses module
  decomposition.
- **Verification**: P7 Probe-1, Probe-3 in
  `.ledge/specs/cache-freshness-observability.md:457-538`.

### AC-2: SLA enforcement extension (NG8)

- **DONE when**:
  - `python -m autom8_asana.metrics active_mrr --sla-profile=warm
    --strict` uses 12h threshold (43200s) instead of 6h default;
    exits 1 if `max_age > 43200`.
  - `--sla-profile` defaults to `active` when absent (preserves PRD
    G2 6h behavior; PRD C-2 backwards-compat).
  - Existing `--staleness-threshold` numeric override still works
    (takes precedence over `--sla-profile`).
- **Lands at**: `src/autom8_asana/metrics/__main__.py` argparse +
  threshold-resolution logic adjacent to line 341.
- **Verification**: P7 Probe-4
  (`.ledge/specs/cache-freshness-observability.md:541-561`) executable
  today against `--strict`; new sla-profile semantics verified by
  unit test asserting per-profile threshold value.

### AC-3: TTL persistence (LD-P3-1)

- **DONE when**:
  - Manifest at `.know/cache-freshness-ttl-manifest.yaml` exists with
    valid YAML matching schema (per-section: `section_gid`,
    `sla_class`, `threshold_seconds`).
  - S3 sidecar at
    `s3://autom8-s3/dataframes/1143843662099250/cache-freshness-ttl.json`
    is readable by the CLI; absent sidecar falls back to manifest.
  - Sidecar overrides manifest when both exist.
- **Lands at**: new file (engineer chooses path; suggestion
  `src/autom8_asana/cache/sla_profile.py` or
  `src/autom8_asana/metrics/sla_profile.py`).
- **Verification**: unit test exercising sidecar > manifest >
  built-in-default precedence; integration test with mock S3.

### AC-4: CloudWatch metric emissions (P4)

- **DONE when** each metric is verifiable in CloudWatch:
  - `MaxParquetAgeSeconds` emitted to `Autom8y/FreshnessProbe`
    namespace per CLI invocation (verifiable via
    `aws cloudwatch get-metric-statistics --namespace
    Autom8y/FreshnessProbe --metric-name MaxParquetAgeSeconds`).
  - `ForceWarmLatencySeconds` emitted on `--force-warm --wait`
    success per FLAG-1 boundary.
  - `SectionCount` emitted per CLI invocation (value approximately
    14 at current scale).
  - `SectionAgeP95Seconds` emitted; requires `from_s3_listing`
    enhancement at `src/autom8_asana/metrics/freshness.py:142-157`
    to retain per-key mtime list.
  - `SectionCoverageDelta` emitted but NO alarm wired (C-6 guard).
  - `CoalescerDedupCount` emitted from
    `src/autom8_asana/cache/dataframe/coalescer.py` when dedup fires.
- **Lands at**:
  - CLI emission: `src/autom8_asana/metrics/__main__.py` after
    `report` is built (between the existing freshness emission lines
    around 291 and exit-code resolution at line 341).
  - `from_s3_listing` enhancement:
    `src/autom8_asana/metrics/freshness.py:142-157`.
  - Coalescer metric:
    `src/autom8_asana/cache/dataframe/coalescer.py`.
- **Verification**: P7 Probe-2 + Probe-5
  (`.ledge/specs/cache-freshness-observability.md:486-589`).

### AC-5: DMS alarm creation OR verification (LD-P4-1)

- **DONE when**:
  - If alarm created by P6: alarm name `AsanaCacheWarmer-DMS-24h`
    visible in CloudWatch console; in OK state (warmer is healthy)
    or ALARM state (warmer absent — would itself indicate the gap
    being measured).
  - If `autom8y_telemetry` auto-provisions: documented in re-handoff
    with package source citation and the auto-provisioned alarm
    name; P7 confirms alarm exists.
- **Lands at**: IaC (Terraform/SAM/CDK) or boto3 admin script;
  engineer chooses based on existing fleet IaC topology.
- **Verification**: P7 thermal-monitor reads CloudWatch `describe-alarms`
  output and confirms ALERT-4 alarm matches P4 §8 config.

### AC-6: cache_warmer Lambda schedule explicit in IaC (P3 D10)

- **DONE when**:
  - EventBridge rule (or equivalent IaC schedule primitive) declared
    in fleet IaC repo. Cadence: 4h for ACTIVE-class entity warm
    cycle. Cron expression engineer-chosen (suggestion:
    `cron(0 */4 * * ? *)` for every 4 hours).
  - IaC declaration is grep-able; the rule name and target Lambda
    ARN are recorded in the re-handoff.
- **Lands at**: external IaC repo (NOT in this worktree per heat-mapper
  §G2 line 124 + P3 §1.1 IaC probe verdict).
- **Verification**: P7 Lens 6 + Lens 4 (P3-dependency lenses) in
  `.ledge/specs/cache-freshness-observability.md:369-394` — confirm
  `warmer cadence * expected execution time < 21600`.

### AC-7: MemoryTier invalidation per ADR-003

- **DONE when**:
  - `--force-warm --wait` followed by a CLI re-read shows fresh L1
    state (Probe-3 acceptance criterion at
    `.ledge/specs/cache-freshness-observability.md:516-538`).
  - Default `--force-warm` (no `--wait`) does NOT invalidate L1; SWR
    rebuild on next read picks up fresh L2 data.
- **Lands at**: force-warm completion handler in
  `src/autom8_asana/metrics/__main__.py` (or new module);
  invalidation call against
  `src/autom8_asana/cache/integration/dataframe_cache.py` invalidate
  surface.
- **Verification**: P7 Probe-3 with `--wait` flag; integration test
  asserting L1 entry absence post-invalidation.

### AC-8: MINOR-OBS-2 botocore traceback fix

- **DONE when**:
  - Setting `ASANA_CACHE_S3_BUCKET=nonexistent-bucket-xyz` and
    invoking `python -m autom8_asana.metrics active_mrr` exits 1
    with friendly stderr line (no raw botocore traceback).
  - Existing exception handler at
    `src/autom8_asana/metrics/__main__.py:235` extended to also catch
    `botocore.exceptions.ClientError` and dispatch to
    AC-4.2-shaped friendly error per
    `src/autom8_asana/metrics/freshness.py:164-177`.
- **Lands at**: `src/autom8_asana/metrics/__main__.py:235` (extend
  existing `except (ValueError, FileNotFoundError)` clause).
- **Verification**: integration test with mock botocore raising
  `ClientError(NoSuchBucket)`.

## 5. Latent decisions inherited (engineer-discretion)

These remain open as engineer-discretion items. They are not
RESOLVE-AT-P5-HANDOFF — the engineer chooses the implementation shape
within the constraints below.

### LD-P2-2 — `CACHE_WARMER_LAMBDA_FUNCTION_NAME` preflight contract

The force-warm CLI affordance (P2 §4 line 339-342) requires resolving
the warmer Lambda's function name or ARN. Two implementation options:

- **Option A** — preflight env var check: require
  `CACHE_WARMER_LAMBDA_FUNCTION_NAME` in environment; fail fast at
  CLI startup if absent.
- **Option B** — settings-field contract: extend
  `src/autom8_asana/settings.py` with a `cache_warmer_lambda_function_name`
  field; resolve from settings (which itself reads env or
  defaults).

Engineer chooses based on fleet conventions for similar CLI surfaces.
The constraint: the resolution path MUST be discoverable from
`--help` output or settings documentation; an undocumented env var is
not acceptable.

### LD-P2-4 — XFetch vs deterministic SWR coexistence

DEFER-FOLLOWUP per PT-A2 verdict. The XFetch augmentation (P2 §6) can
be implemented as an OR-trigger augmenting the existing
`approaching_threshold = 0.75` deterministic check in
`src/autom8_asana/cache/dataframe/factory.py:40-117`. Beta=1.0 default
per CACHE:SRC-001. Beta calibration requires production WarmDuration
p50/p95 — followup procession scope.

If engineer ships XFetch in P6: place at
`src/autom8_asana/cache/dataframe/factory.py` `_swr_build_callback`
trigger condition. If engineer DEFERs XFetch to followup: document in
re-handoff under "deferred work items".

## 6. Operational constraints

### Canary-in-production reference

PRD §6 C-1: canary-in-production discipline. Single bucket
(`autom8-s3`); no multi-env deployment topology. The implementation
ships and runs against production directly. Validation occurs via:

- Existing test suite (unit + integration) in CI.
- Heat-mapper-style manual probe of the production bucket post-deploy
  by the implementing engineer.
- P7 thermal-monitor in-anger probes against the deployed system.

### Backwards-compat boundary (PRD §6 C-2)

The default-mode CLI output (`python -m autom8_asana.metrics
active_mrr` with no flags) MUST be preserved verbatim. This means:

- stdout format unchanged (existing dollar figure + freshness lines).
- Exit-code behavior unchanged when no new flags are passed.
- New flags (`--force-warm`, `--wait`, `--sla-profile`) are additive.

Existing consumers (CI pipelines, scripts) MUST NOT break.

### Rollback boundary

If `--force-warm` causes regression in production:

- The flag is opt-in; default behavior is unchanged. Operators can
  simply not invoke it.
- For an emergency disable, gate the flag behind an env var (e.g.,
  `AUTOM8Y_FORCE_WARM_ENABLED=true` required for the flag to be
  recognized). Engineer chooses whether to add this defensively;
  surface in re-handoff if added.

### SLO-1 starts in deficit

Per P4 SLO-1 (`.ledge/specs/cache-freshness-observability.md:107-119`)
and Lens 6 (`.ledge/specs/cache-freshness-observability.md:390-394`):
9/14 sections currently exceed 6h staleness. SLO-1 is **expected to
breach immediately** in production until AC-6 (cache_warmer schedule
explicit in IaC) lands and a full warm cycle restores freshness.

This is **expected, not a defect**. The on-call response runbook
(`.ledge/specs/cache-freshness-runbook.md` Stale-1) handles the
post-deploy SLO-1 deficit window. SLO-1 reaches steady-state
(green) approximately 6h after AC-6 deploys, assuming the new
schedule executes successfully on its first cycle.

## 7. Pre-existing observations

Surfaced from heat-mapper Q5 (`.sos/wip/thermia/heat-mapper-assessment-cache-freshness-2026-04-27.md:312-332`)
and predecessor dossier §8.2.

### MINOR-OBS-1 — xdist test flake

`tests/unit/persistence/test_reorder.py::test_property_moves_produce_desired_order`
fails intermittently under xdist parallel execution; passes
deterministically in isolation. **Disposition**: hygiene secondary
handoff (P5b parallel to this dossier). Confirmed NOT
cache-architecture-relevant per heat-mapper §Q5. NOT in 10x-dev P6
scope; carried into the thermia → hygiene dossier
(`HANDOFF-thermia-to-hygiene-2026-04-27.md`, listed in INDEX.md).

### MINOR-OBS-2 — botocore traceback (thermia absorbs)

`load_project_dataframe` at `src/autom8_asana/metrics/__main__.py:234`
raises raw botocore `ClientError(NoSuchBucket)` traceback when
`ASANA_CACHE_S3_BUCKET` is set to a non-existent bucket; the
existing handler at line 235 catches only `(ValueError,
FileNotFoundError)`. **Disposition**: thermia absorbs — promoted to
implementation work item AC-8 (§4). One-line fix: extend the except
clause to include `botocore.exceptions.ClientError` with
`NoSuchBucket` mapping to friendly stderr line. P4 §3 ALERT-5 note
references this gap.

## 8. Attester acceptance protocol

### 10x-dev rite acknowledgement

Upon engaging this dossier (rite switch + CC restart + procession
kickoff in 10x-dev mode), the 10x-dev rite writes a `## Attester
Acceptance` section in this dossier per the schema TDD §4.3
(`.ledge/specs/handoff-dossier-schema.tdd.md:236-254`). The section
MUST contain:

- Accepting rite (`10x-dev`).
- Activation predicate result (PRIMARY engaged; no fallback
  rite declared).
- Engaging agent(s) — typically `principal-engineer` for
  implementation work; engineer-discretion if pantheon-fit
  substitution applies.
- Acceptance timestamp (ISO-8601 UTC).
- Receiving session ID.
- Receiving worktree + branch.
- Initiative slug (typically continues
  `cache-freshness-procession-2026-04-27` or branches a new slug;
  engineer chooses).
- Scope acknowledgement — explicit list of work items from §1
  accepted.
- Initial-pass scope question for Potnia (optional).

### Post-impl re-handoff (10x-dev → thermia)

After P6 implementation completes, 10x-dev opens a new dossier
`HANDOFF-10x-dev-to-thermia-{date}.md` (impl → verify direction).
This dossier:

- Cites which §1 items shipped (with file:line landed-anchors) and
  which DEFERred (per PT-A4 concerns about scope-collapse).
- Records the FLAG-1 / FLAG-2 implementation receipts (the boundary
  declarations in §3 are normative; the impl artifact must show
  receipts).
- Records LD-P4-1 binary-outcome (alarm created vs.
  auto-provisioned).
- Lists any DEFER-FOLLOWUP items the engineer surfaced beyond §5
  (e.g., XFetch ship-or-defer choice).
- Provides empirical telemetry baselines (post-deploy metric
  values) to seed P7 thermal-monitor in-anger probes.

### P7 thermal-monitor attestation

thermia.thermal-monitor's P7 attestation executes against the
deployed system. Per telos SQ-3 decision
(`.know/telos/cache-freshness-procession-2026-04-27.md:54-59`),
verification mode is **BOTH design-review + in-anger-probe**:

- **Track A** (design-review): apply 11-lens rubric
  (`.ledge/specs/cache-freshness-observability.md:343-429`) to P2
  + P3 + P4 artifacts. Produces evidence artifact at
  `.ledge/reviews/design-review-P7-cache-freshness-{date}.md`.
- **Track B** (in-anger probes): execute Probe-1 through Probe-5
  (`.ledge/specs/cache-freshness-observability.md:455-602`)
  against deployed CLI + Lambda + CloudWatch. Probes 1, 3, 5 require
  AC-1, AC-3, AC-4, AC-7 to be DONE; Probe-2 requires AC-4; Probe-4
  is executable today.

### Verification deadline + fallback

- **Verification deadline**: 2026-05-27 (per parent telos D8).
- **Fallback attester** (inherited from predecessor dossier §8.1
  latent decision #2): `sre.observability-engineer` if the thermia
  rite is not registered at platform-manifest level at attestation
  time. Activation predicate per
  `.ledge/specs/handoff-dossier-schema.tdd.md:286-306` (mechanically
  verifiable: ENOENT on `.claude/agents/thermia/` OR rite absent
  from `.knossos/KNOSSOS_MANIFEST.yaml`).

## Attester Acceptance

- **Accepting rite**: 10x-dev (active per `ari rite current` post-CC-restart — pantheon: potnia, requirements-analyst, architect, principal-engineer, qa-adversary)
- **Activation predicate result**: PRIMARY path engaged. 10x-dev rite is registered (`.claude/agents/` populated; `ari rite current` reports `10x-dev`). No fallback required (cleanup-handoff variant declares `fallback_rite: null` since 10x-dev IS the engineering rite).
- **Acceptance timestamp**: 2026-04-27T20:30:00Z (approximate; recorded at 10x-dev impl procession kickoff)
- **Receiving session**: NEW (to be created via moirai with rite=10x-dev at impl phase start; session_id will be back-filled to this entry on creation, mirroring the predecessor handoff back-fill convention)
- **Receiving worktree**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.worktrees/cache-freshness-impl/` on `feat/cache-freshness-impl-2026-04-27` (branched off `thermia/cache-freshness-procession-2026-04-27` at HEAD `a732487f` so all design substrate is co-resident)
- **Initiative slug**: cache-freshness-impl-from-thermia-2026-04-27 (downstream of `cache-freshness-procession-2026-04-27`, parent=`verify-active-mrr-provenance`)
- **Scope acknowledgement**: 10x-dev accepts ownership of 8 implementation work items per §1 (force-warm CLI affordance, SLA enforcement extension, TTL persistence, 5 CloudWatch metric emissions, DMS alarm creation/verification, Lambda schedule IaC, MemoryTier invalidation HYBRID per ADR-003, MINOR-OBS-2 botocore fix). Engineer-discretion latent decisions per §5 inherited (LD-P2-2 preflight contract pattern, LD-P2-4 XFetch beta calibration deferred-followup).
- **Resolved load-bearing inputs accepted**: 4 RESOLVE-AT-P5-HANDOFF items (LD-P2-1 sla-profile vocabulary, LD-P3-1 hybrid TTL persistence, LD-P3-2 coalescer-routed force-warm, LD-P4-1 emit_success_timestamp investigation) + 2 PT-A2 FLAGs (FLAG-1 ForceWarmLatency includes coalescer wait, FLAG-2 4-class taxonomy canonical) treated as DECIDED, not re-litigated.
- **Re-handoff commitment**: At impl phase close, 10x-dev will author `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-{date}.md` (impl→verify analog) citing per-§1-item shipped vs deferred status with file:line receipts. This re-handoff triggers thermia.thermal-monitor's P7 attestation (BOTH design-review + in-anger-probe per SQ-3) discharging D8 by 2026-05-27.
- **Critical constraint locked**: force-warm MUST route via `DataFrameCache` coalescer-protected path (LD-P3-2). Direct Lambda invoke FORBIDDEN. Wiring to be verified by qa-adversary at impl-phase QA gate.

## Verification Attestation
