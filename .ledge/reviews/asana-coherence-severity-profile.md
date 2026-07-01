---
type: review
status: draft
phase: assess
slug: asana-coherence
upstream: asana-coherence-signal-sift.md
preflight: PV-PREFLIGHT-asana-ecosystem-coherence-2026-06-24.md
---

# Severity Profile: asana-ecosystem-coherence

**HEAD**: f4f924d2 | **Date**: 2026-06-24 | **Profiler**: pattern-profiler

> **Construct declaration** (AV:SRC-001 Messick 1989 [STRONG]): The A-F grades below
> measure *production-readiness* operationalized across five structural categories.
> "Production-readiness" means: will the system correctly and observably serve its
> intended function under live operational conditions without requiring emergency
> intervention? Grades are NOT surface-tidiness scores. The weakest-link model
> [AV:SRC-007 Kane 2013 [STRONG]] ensures a single failing dimension cannot be
> averaged away.
>
> **G-DENOM caveat** (per pre-flight gate authority): Silence in telemetry cannot
> be equated with proven-zero. Where iris observed flat/absent metrics, that absence
> is rated on what the code structurally produces — not on what was unobservable.
> Rungs are named per G-RUNG discipline (`authored < emitting < alerting < proven
> < merged < live < protecting-prod`).

---

## 1. Rubric (explicit, per mandate)

| Grade | Anchor | Construct meaning |
|-------|--------|-------------------|
| A | 0 critical, 0 high, <=2 medium | Production-ready; residual issues are polish |
| B | 0 critical, 0-1 high, <=5 medium | Good; one isolated risk area; ships with monitoring |
| C | 0 critical, 1-3 high, moderate medium | Shippable with known gaps; remediation planned |
| D | 0-1 critical, 3+ high | Below bar; significant likelihood of production incident |
| F | 2+ critical in category | Do not ship; active correctness/security/operability failure |

**Overall grade calculation** (weakest-link, [PLATFORM-HEURISTIC]):
1. Median across five categories
2. Any F → overall cap D
3. Any D → overall cap C
4. 3+ categories C or below → drop one letter

---

## 2. Health Grades

| Category | Grade | Rationale |
|----------|-------|-----------|
| Complexity | C | cache_warmer.py at 1437 LOC (HIGH) with 3 distinct warm paths gated by event params; no refactor path visible at HEAD |
| Testing | B | Broad test suite across unit/integration/synthetic; gid_push URL-absence path has a test (`test_skips_when_no_data_service_url`); integration tests SKIPPED at HEAD CI per pre-flight |
| Dependencies | B | autom8y-core bumped to 4.6.0 at HEAD; lockfile present; no evidence of rot; SCAR-LP-001 (lockfile-propagator ordering) historical |
| Structure | C | SCAR-REG-001 (sequential placeholder GIDs shipping in production-bound code, HIGH); SCAR-IDEM-001 (finalize-swallow double-exec risk, HIGH); protocols.py interop figure overstated |
| Hygiene | B | 94% broad-except annotation compliance (185/197); 10 unannotated code sites clustered in intake_* services; `protocols.py:42` ~30% figure is authored-not-computed; `.know/` corpus 90-commit stale |
| **Overall** | **C** | Median across five = B/C mix; two HIGH findings in Structure (SCAR-REG-001, SCAR-IDEM-001); Complexity at C; 2 of 5 categories at C triggers no automatic drop but weakest-link forces C floor when 2+ categories are C and findings include HIGH-severity structural correctness risks |

**Overall grade calculation trace**:
- Grades: Complexity=C, Testing=B, Dependencies=B, Structure=C, Hygiene=B
- Median: B (three Bs, two Cs)
- No F category → no F-cap applies
- No D category → no D-cap applies
- 2 categories at C (not 3+) → no automatic drop rule triggers
- However: Structure contains two HIGH findings with production-correctness implications (SCAR-REG-001 sequential GIDs live in prod code; SCAR-IDEM-001 double-exec risk on S2S). Complexity contains one HIGH finding (1437 LOC warmer). Per weakest-link principle [AV:SRC-007 Kane 2013]: the median-B reading would understate the dominant risk surface. Three HIGH findings distributed across two C-graded categories → overall = **C**.
- [PLATFORM-HEURISTIC: the B-vs-C boundary for this configuration; the median alone would yield B but the concentration of HIGH findings in structural-correctness categories warrants C per the weakest-link interpretive chain.]

---

## 3. Validated Findings

### 3.1 Severity: HIGH

---

**H-1: SCAR-REG-001 — Sequential placeholder GIDs shipping in production-bound code**

- **Location**: `src/autom8y_asana/reconciliation/section_registry.py:94–107` (EXCLUDED_SECTION_GIDS), `:128–150` (UNIT_SECTION_GIDS)
- **Description**: `EXCLUDED_SECTION_GIDS` and `UNIT_SECTION_GIDS` contain visibly sequential numeric strings (e.g., `1201081073731600`..`1201081073731603`, `1201081073731610`..`1201081073731624`) annotated with `VERIFY-BEFORE-PROD (SCAR-REG-001)`. These GIDs have never been verified against the live Asana API. If wrong, reconciliation incorrectly routes units — silently processing tasks into excluded sections or silently skipping active processing sections.
- **Evidence**: `section_registry.py:94–99` and `:128–131` contain explicit `VERIFY-BEFORE-PROD` markers. Pre-flight P1 receipt confirmed code-present. G-RUNG: defect `proven` present in code; live-Asana verification rung `PENDING`.
- **Severity rationale**: Correctness risk at the reconciliation routing boundary. If EXCLUDED_SECTION_GIDS are wrong, units that should be excluded (Templates, Account Error) enter the processor. If UNIT_SECTION_GIDS are wrong, active units are silently skipped. Both produce silent data errors with no metric surfacing.
- **Construct-validity caveat**: This grade measures production-readiness, not the intent of the `VERIFY-BEFORE-PROD` marker. The marker demonstrates awareness; the GIDs not being verified is the production risk.
- **Recommendation**: Run `GET /projects/1201081073731555/sections` via iris, map section names to actual GIDs, replace all 19 placeholder entries. Effort: **quick fix** (single API call + constant replacement) once live-Asana access is available.
- **Cross-rite routing**: `iris` (live Asana GID lookup), `10x-dev` (constant replacement + test fixture update)
- **G-RUNG**: `proven` (defect in code); live verification `PENDING` per G-DENOM

---

**H-2: SCAR-IDEM-001 — Idempotency finalize() swallowed — double-execution risk on S2S retry**

- **Location**: `src/autom8_asana/api/middleware/idempotency.py:719`
- **Description**: `DynamoDBIdempotencyStore.finalize()` is wrapped in a bare `except Exception` that swallows the exception with only a `logger.exception` call. If `finalize()` fails, the idempotency key is NOT persisted. A client retry then re-executes the mutation. The inline SCAR comment explicitly names the risk: "a client retry will re-execute the mutation (double-execution risk). Acceptable only if … upstream caller is a human or idempotent system. For S2S callers with strict-once semantics this must be promoted to an error metric."
- **Evidence**: `idempotency.py:719` confirmed in code read. Pre-flight P2 receipt confirmed. G-RUNG: risk `proven` open.
- **Severity rationale**: Double-execution of mutations (create/update/delete operations) on S2S retry paths is a correctness failure, not a maintainability concern. The middleware is the system-wide idempotency contract — a gap here affects every POST endpoint covered by the middleware.
- **Construct-validity caveat**: The risk is conditional (S2S with strict-once semantics). For human-triggered idempotent callers the impact is lower. Grade reflects the worst-case path (S2S retry) because the middleware cannot distinguish caller type.
- **Recommendation**: Emit a CloudWatch error metric when `finalize()` fails (not just a log line); add alerting threshold. For strict-once S2S callers, consider propagating the finalize failure as a 500 to force the caller to NOT retry. Effort: **moderate** (metric wire-up + alerting + caller contract review).
- **Cross-rite routing**: `sre` (missing error metric / alerting), `10x-dev` (promote log to metric, add 500 propagation path for S2S)
- **G-RUNG**: `proven` (defect in code)

---

**H-3: StatusPush* structurally unreachable when AUTOM8Y_DATA_URL absent — undetectable silent non-publication**

- **Location**: `src/autom8_asana/services/gid_push.py:498–504`
- **Description**: `push_status_to_data_service()` returns `False` at Gate 2 if `AUTOM8Y_DATA_URL` is absent from the Lambda environment. The return is silent: one `logger.warning("status_push_skipped", reason="AUTOM8Y_DATA_URL not configured")` is emitted, but NO CloudWatch metric is emitted. `StatusPushSuccess` and `StatusPushFailure` (emitted at `push_orchestrator.py:192–198`) are therefore structurally unreachable in this configuration. Iris observed zero `StatusPush*` events — this gate is the most probable explanation.
- **Evidence**: `gid_push.py:498–504` validated in code read; `push_orchestrator.py:192–198` confirms metric emission only on the success/failure branch of `push_status_to_data_service()`. Unit test `test_skips_when_no_data_service_url` confirms the False-return behavior. G-RUNG: gate logic `proven`; prod env-config state `UNVERIFIABLE` from code alone per G-DENOM.
- **Severity rationale**: The operational blind spot is the severity driver, not the gate itself. When `AUTOM8Y_DATA_URL` is absent, the entire push-seam goes dark with only a warning log — no CloudWatch metric means no alert, no dashboard signal, and no SRE visibility. An env-config gap silently disables a cross-service data sync path with zero observable signal to the on-call engineer.
- **Construct-validity caveat**: If `AUTOM8Y_DATA_URL` is intentionally absent (push not yet configured for an environment), the silent skip is by design. The HIGH rating reflects the observability gap, not the feature flag. Production environments where this sync is expected must have the env var present AND a metric emitted on skip.
- **Recommendation**: Add a CloudWatch metric (`StatusPushSkipped` or increment a `StatusPushConfigMissing` counter) inside each Gate 2/3 early-return path in `_push_to_data_service_internal()`. Effort: **quick fix** (two `emit_metric` calls). Also: add an SRE alarm on `StatusPushSkipped` > 0 in production.
- **Cross-rite routing**: `sre` (alarm gap on silent push-skip), `10x-dev` (add emit_metric to gate-exit paths)
- **G-RUNG**: gate logic `proven`; prod env state `emitting` (warning log only, not `alerting`)

---

**H-4: cache_warmer.py 1437 LOC — three distinct warm paths in a single Lambda handler**

- **Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:1–1437`
- **Description**: The Lambda handler is 1437 LOC containing three structurally distinct execution paths (entity-type warm, bulk prematerialization, section prematerialization) gated by event parameters at `:1291–1304`. The AIMD governor logic, WarmResponse dataclass, push side-effects, and checkpoint machinery are all colocated in a single file. The pre-flight dd8e43ab commit was a 702-line diff touching this file and 10 others — changes of this scope in a 1437-LOC file create high merge-conflict risk and increase the cognitive load for future AIMD/push/checkpoint changes.
- **Evidence**: `wc -l` receipt confirmed 1437 LOC. Three warm paths confirmed at `:1291–1304`. 702-line diff scope confirmed in pre-flight commit record.
- **Severity rationale**: HIGH rather than MEDIUM because the file is actively changing (702-line diffs), the three warm paths share AIMD and checkpoint state, and the C-1/C-2/C-5 bugs in dd8e43ab demonstrate that this coupling produces observable production defects (AIMD dark, semaphore multiply). The complexity is load-bearing fault territory, not cosmetic.
- **Recommendation**: Decompose into: `_warm_entity_type.py`, `_warm_bulk_set.py`, `_warm_section_set.py` with shared `_warm_shared.py` for AIMD/checkpoint primitives. The handler file becomes a thin dispatcher. Effort: **significant** (refactor with test fixture updates across 8+ test files).
- **Cross-rite routing**: `10x-dev` (decomposition), `sre` (observability stays correct through refactor)
- **G-RUNG**: `proven` (LOC confirmed by receipt)

---

### 3.2 Severity: MEDIUM

---

**M-1: Interop coverage overstated at ~30%; true ratio is ~14%**

- **Location**: `src/autom8_asana/automation/workflows/protocols.py:42`
- **Description**: The module docstring states "Interop covers ~30% of the client surface." Re-quantification at HEAD shows 2/14 public methods have any interop coverage (`is_healthy` partial, `get_insights_async` partial). True ratio: ~14%. The `INTEGRATE-ecosystem-dispatch Section 1.4` spike doc referenced at `:44` is not present in this repo, so the original calculation basis is unverifiable.
- **Evidence**: `protocols.py:42` confirmed. 14-method enumeration from `clients/data/client.py` confirmed. G-RUNG: re-quantification `proven`; original 30% basis `UNVERIFIABLE` per G-DENOM/UV-P.
- **Severity**: MEDIUM — the discrepancy affects migration decision framing ("Do NOT migrate DataServiceClient to interop protocols" is premised on this figure). At ~14% actual coverage, the migration pressure may be understated. No functional defect in production code.
- **Recommendation**: Update `protocols.py:42` to `~14% (2/14 public methods)` with a note that the ~30% figure may have been computed on a different surface (capability classes vs method count). Effort: **quick fix** (one-line doc update + note). Also: recover or re-author the INTEGRATE-ecosystem-dispatch spike doc.
- **Cross-rite routing**: `docs` (doc correction), `know` (spike doc gap)

---

**M-2: .know/ corpus 90-commit stale; P5 cache features absent from feat/INDEX.md**

- **Location**: `.know/` (all domains expired), `.know/feat/INDEX.md`
- **Description**: The `.know/` corpus was generated at source hash `8980bcd7` (2026-05-06), 90 commits before HEAD. All 7d-expiry domains are expired. `feat/INDEX.md` contains zero references to: `cure`, `governor`, `dead-man`, `honest-empty`, `serve-stale`, `PRESERVE`, `StorageNamespace`. These are all active production features shipped in PRs #127/#128/#139/#141. Any agent consuming `.know/architecture.md` or `.know/feat/INDEX.md` operates on a 49-day-stale model of the codebase — including this review rite, which has treated all `.know/` files as non-authoritative.
- **Evidence**: Pre-flight P5 receipt: `git rev-list --count 8980bcd7..HEAD = 90`. `INDEX.md` grep receipts confirmed. G-RUNG: staleness `proven`.
- **Severity**: MEDIUM — affects agent operational awareness, not production code correctness. However, stale `.know/` creates real risk: future reviews or architecture changes may rely on it.
- **Recommendation**: Run `/know --all` to regenerate. Tag `.know/` regeneration as part of the standard post-sprint hygiene gate. Effort: **quick fix** (one command; output pipeline already exists).
- **Cross-rite routing**: `know` (regeneration), `10x-dev` (add `.know/` staleness check to pre-review checklist)

---

**M-3: 10 unannotated broad-except sites — 5% convention non-compliance**

- **Location**: `src/autom8_asana/services/intake_resolve_service.py:229,316`; `services/intake_create_service.py:529`; `services/intake_custom_field_service.py:126`; `services/section_timeline_service.py:482`; `api/routes/section_timelines.py:166`; `reconciliation/engine.py:119`; `metrics/freshness.py:398`; `clients/data/_policy.py:210`; `cache/dataframe/factory.py:136`
- **Description**: Project convention requires `except Exception` clauses to carry `# noqa: BLE001` or `# BROAD-CATCH` annotation. 10 code sites (5% of 197 total) are unannotated. All observed cases log the exception; none silently swallow. Cluster in `services/intake_*` (4 sites).
- **Evidence**: Census confirmed by signal-sifter grep receipt. G-RUNG: `proven`.
- **Severity**: MEDIUM — no safety issue (all sites log); non-compliance with project convention creates BLE001 linting ambiguity and erodes the annotation-as-documentation practice. `clients/data/_policy.py:210` is borderline-intentional (delegates to pre-execute handler).
- **Recommendation**: Add `# noqa: BLE001 — {reason}` to each unannotated site. The `reconciliation/engine.py:119` and `cache/dataframe/factory.py:136` sites use `logger.exception()` (includes traceback) and are functionally documented by log behavior — annotation is low-effort confirmation. Effort: **quick fix** (10 one-line comments).
- **Cross-rite routing**: `hygiene` (convention enforcement)

---

**M-4: Bridge-fleet success gap — LastSuccessTimestamp stale since 2026-06-18**

- **Location**: `Autom8y/AsanaBridgeFleet :: LastSuccessTimestamp` (CloudWatch metric, not code)
- **Description**: Iris observed `LastSuccessTimestamp` last datapoint at 2026-06-18T13:32:06; no datapoints 2026-06-19 through 2026-06-24 (~6 days). `BridgeFleetHealth` observed only in `{environment: staging, workflow_id: insights-export}`. No production bridge fleet health signal visible.
- **Evidence**: Pre-flight bonus signal receipt. G-RUNG: observation `emitting` (metric visible to iris); root cause `authored` (hypotheses only); no code path directly explains this via code inspection alone.
- **Severity**: MEDIUM per G-DENOM discipline — the silence is observed but cannot be classified as a production failure without ruling out: (a) bridge fleet intentionally idle in the observed window, (b) telemetry namespace gap (staging-only `BridgeFleetHealth`), (c) `AUTOM8Y_DATA_URL` gate cascade from the push-seam (H-3). The medium rating reflects an unresolved operational signal requiring iris follow-up.
- **Recommendation**: Dispatch iris to query `AsanaBridgeFleet` namespace for all available dimensions; check whether `insights-export/staging` is the only registered workflow or if production is missing. Effort: **quick fix** (iris query).
- **Cross-rite routing**: `iris` (live metric query), `sre` (alerting gap if bridge fleet silent for 6+ days)

---

**M-5: /v1/query/{entity_type} sunset lapsed (2026-06-01) — route live, usage unverifiable from metrics**

- **Location**: `src/autom8_asana/api/main.py:470` (route mounted), `src/autom8_asana/api/routes/query.py:881` (Sunset header)
- **Description**: The deprecated query endpoint carries `Sunset: 2026-06-01` and `Deprecation: true` headers (confirmed in pre-flight P3). The sunset date has lapsed 23 days. Usage is logged via `logger.info("deprecated_query_endpoint_used")` — NOT as a CloudWatch metric — making usage verification impossible from `list-metrics` alone.
- **Evidence**: Route mounted at `api/main.py:470`; header at `query.py:881`. Pre-flight G-DENOM catch: usage is a log line, not a metric. G-RUNG: route `live`; usage `UNVERIFIABLE` from code/metrics alone.
- **Severity**: MEDIUM — the endpoint is live and could be used (lapsed sunset means clients who relied on the sunset date may still be calling). Unverifiable usage is the core risk: the team cannot safely retire without a Logs Insights query.
- **Recommendation**: (1) Run a Logs Insights query over the last 30 days for `deprecated_query_endpoint_used` events. (2) If zero hits: retire the route. (3) If hits found: extend sunset, notify callers, add a CloudWatch metric for future sunset tracking. Effort: **quick fix** for the logs query; **moderate** for retirement coordination.
- **Cross-rite routing**: `iris` (Logs Insights query), `sre` (sunset enforcement alarm), `10x-dev` (route retirement)

---

### 3.3 Severity: LOW

---

**L-1: AIMD governor (C-1) pre-dd8e43ab — AIMD dark; now fixed**

- **Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:147–176`
- **Description**: C-1 bug (semaphore_logger=None → AIMD attestation dark) was fixed in dd8e43ab (merged 2026-06-19). `_sample_aimd_engaged()` now correctly returns `bool | None`. The post-fix code is validated and correct. Rated LOW for residual documentation value only — the fix introduced the correct pattern at `:174` (`# noqa: BLE001 -- attestation must never crash the warm`).
- **G-RUNG**: fix `merged`; observability `emitting` (post-fix)
- **Cross-rite routing**: none required (fixed)

---

**L-2: H4 governor-throttle hypothesis code-refuted**

- **Location**: `src/autom8_asana/lambda_handlers/cache_warmer.py:163–176`
- **Description**: Hypothesis that the AIMD governor caused the ~06-18/19 quiescence is CODE-REFUTED. `_sample_aimd_engaged()` is a read-only attestation probe. The AIMD semaphore in `transport/adaptive_semaphore.py` slows but cannot zero-output the warmer. Documented here for completeness — case-reporter should not report this as an open finding.
- **G-RUNG**: refutation `proven` (code read)
- **Cross-rite routing**: none

---

## 4. Patterns Identified

### Pattern A: Coherence Decay — The Cross-Cutting Theme

**Theme**: P5 (undocumented cache features + 90-commit drift) → SCAR-005/006 cascade zone → ~06-18/19 subsystem-quiet → dark push-seam / zero bridge-fleet-health are instances of a single **coherence decay** dynamic, not independent incidents.

**Evidence chain**:

1. **SCAR-005** (CascadingFieldResolver 30% null rate) and **SCAR-006** (cascade hierarchy warming gaps) are cache coherence failures — the warm path did not produce consistent observable state. Both required multiple fix commits. These are the historical template for what happens when the warm path's internal state diverges from what the metrics surface.

2. **P5 (90-commit drift)** means that four major cache features shipped since the `.know/` baseline — PRESERVE (#128), observable AIMD governor (#141), dead-man (#139), honest-empty/cure (#127) — are absent from `feat/INDEX.md`. These are exactly the features that govern *how the warmer reports its own health*. An agent or engineer consulting `.know/` would be operating on a model of the cache that does not include the observability instrumentation.

3. **dd8e43ab and the C-1 bug**: The C-1 bug (AIMD dark pre-fix) is a direct descendant of the SCAR-005/006 pattern — a warm path that was running but whose internal state (AIMD engagement) was not observable. The 06-18/19 quiescence window coincides exactly with the dd8e43ab merge window. H1+H2 (AIMD dark + deploy gap) is most probable.

4. **StatusPush* silence and the dark push-seam**: Gate 2 (`AUTOM8Y_DATA_URL` absent → silent False return) means the push-seam from warmer → autom8_data can be entirely non-functional with zero CloudWatch signal. This is structurally identical to the SCAR-005/006 pattern: a subsystem that appears healthy (no errors) because its failure mode is silent non-emission rather than error emission.

5. **Bridge-fleet health zero since 2026-06-18**: The `AsanaBridgeFleet :: LastSuccessTimestamp` gap aligns with the same window. The bridge fleet's health signal depends on the push-seam delivering cross-service state. If Gate 2 silenced the push, the bridge fleet health metric downstream may also be dark — not because the fleet failed, but because the observability seam feeding it was misconfigured.

**Structural interpretation**: This is not five independent bugs. It is one **coherence decay** pattern at the observability seam: the system's actual operational state (warm running, AIMD governing, push occurring) diverges from what CloudWatch can observe, because the telemetry emission paths have env-config dependencies and annotation conventions that, when absent, produce silence rather than error. SCAR-005/006 established this pattern for cache coherence; the current audit reveals it has propagated to the AIMD observability layer (C-1), the push-seam metric layer (H-3), and likely the bridge-fleet health layer (M-4).

**Evidence grade for theme**: [STRUCTURAL | MODERATE] — three structurally independent observations (C-1 fix, Gate 2 behavior, bridge fleet gap) converge on the same pattern; no single conclusive proof; G-DENOM prohibits elevating to STRONG without live CloudWatch receipt.

---

### Pattern B: VERIFY-BEFORE-PROD markers at production boundaries

**Theme**: Both SCAR-REG-001 (section GIDs) and SCAR-IDEM-001 (finalize swallow) carry explicit `VERIFY-BEFORE-PROD` inline markers. These markers are the codebase's own signal that these findings were known at authoring time but deferred. The markers are functioning as intended — they are visible and actionable. The production risk is not that the code is broken unknowingly; it is that the verification step has not been completed.

**Implication**: The pre-flight goal of advancing SCAR-REG-001 and SCAR-IDEM-001 from `authored` toward `proven` remains the highest-priority remediation action.

---

### Pattern C: Convention erosion at service boundaries

**Theme**: The 10 unannotated broad-excepts (M-3) cluster in `services/intake_*` — the intake processing layer that handles external user-facing data creation and resolution. This is the highest-correctness-sensitivity zone (intake errors mean data never enters the system). The convention erosion is modest (5%) but concentrated in the zone where exception handling discipline matters most.

---

## 5. Cross-Rite Routing Recommendations

| Finding | Target Rite | Trigger Signal |
|---------|-------------|----------------|
| H-1: SCAR-REG-001 GID verification | iris | Live Asana API call needed: `GET /projects/1201081073731555/sections` |
| H-1: SCAR-REG-001 constant replacement | 10x-dev | Post-iris: replace 19 placeholder GID constants, update test fixtures |
| H-2: SCAR-IDEM-001 error metric + S2S propagation | sre + 10x-dev | Missing CloudWatch metric on finalize failure; double-exec risk for S2S |
| H-3: StatusPush* silent non-publication | sre | No alarm exists for `AUTOM8Y_DATA_URL` absent; observability gap |
| H-3: StatusPush* metric on gate-exit | 10x-dev | Add `emit_metric("StatusPushSkipped")` at gid_push.py:503 |
| H-4: cache_warmer.py decomposition | 10x-dev | 1437 LOC handler; three warm paths; high change velocity |
| M-1: protocols.py ~30% figure correction | docs | One-line doc update; spike doc recovery |
| M-2: .know/ regeneration | know | `/know --all` post-sprint regeneration |
| M-3: unannotated broad-except | hygiene | 10 convention-violating sites in intake_* and api/routes/ |
| M-4: bridge-fleet health gap investigation | iris | `AsanaBridgeFleet` namespace query across all dimensions |
| M-4: bridge-fleet alerting | sre | 6-day metric gap with no alarm |
| M-5: /v1/query sunset enforcement | iris | Logs Insights query for `deprecated_query_endpoint_used` |
| M-5: route retirement or extension | 10x-dev | Post-iris: retire or extend based on usage evidence |

---

## 6. Coverage Gaps

**No back-route to signal-sifter required.** The signal-sifter artifact covers the pre-flight's five audit loci thoroughly. The following areas are noted as out-of-scope for this scan but may warrant future review:

1. **transport/adaptive_semaphore.py** — modified in dd8e43ab (C-2 warm-cycle-shared semaphore fix) but not scanned at file level. If the AIMD coherence decay pattern (Pattern A) is to be fully characterized, this file's semaphore implementation warrants a structural review.

2. **api/middleware/idempotency.py beyond line 719** — the finalize-swallow (SCAR-IDEM-001) was confirmed but the full idempotency state machine (pre-check → execute → finalize) was not mapped. A dedicated idempotency correctness audit would surface whether other state transitions have analogous gaps.

3. **autom8y-core 4.6.0 bump (f4f924d2)** — the HEAD commit bumps autom8y-core. No breaking change analysis was performed. If autom8y-core introduces interface changes affecting `DefaultLogProvider` (relevant to C-1 / logger protocol), a dependency contract review is warranted.

4. **PIPELINE_TYPE_BY_PROJECT_GID mapping** — Gate 4 (`push_orchestrator.py:183`) requires project GIDs to be in this mapping. The mapping was not enumerated. If production project GIDs are absent from the mapping, StatusPush* is silently suppressed (same coherence decay pattern).

---

## 7. Severity Matrix (summary)

| ID | Finding | Severity | Category | G-RUNG | Routing |
|----|---------|----------|----------|--------|---------|
| H-1 | SCAR-REG-001 sequential placeholder GIDs in prod code | HIGH | Structure | proven (defect); live verification PENDING | iris → 10x-dev |
| H-2 | SCAR-IDEM-001 finalize() swallowed — double-exec S2S | HIGH | Structure | proven | sre + 10x-dev |
| H-3 | StatusPush* structurally unreachable if AUTOM8Y_DATA_URL absent; silent | HIGH | Hygiene / Observability | gate proven; prod env UNVERIFIABLE | sre + 10x-dev |
| H-4 | cache_warmer.py 1437 LOC; 3 warm paths; active fault zone | HIGH | Complexity | proven | 10x-dev |
| M-1 | protocols.py ~30% interop figure overstated; true ~14% | MEDIUM | Hygiene | proven (re-quantification) | docs + know |
| M-2 | .know/ corpus 90-commit stale; P5 features absent from INDEX | MEDIUM | Hygiene | proven | know |
| M-3 | 10 unannotated broad-excepts in intake_* / api/routes | MEDIUM | Hygiene | proven | hygiene |
| M-4 | Bridge-fleet LastSuccessTimestamp dark since 2026-06-18 | MEDIUM | Observability | emitting (metric gap); root cause authored | iris + sre |
| M-5 | /v1/query sunset lapsed 23 days; usage unverifiable from metrics | MEDIUM | Structure | route live; usage UNVERIFIABLE | iris + 10x-dev |
| L-1 | C-1 AIMD dark (pre-dd8e43ab) — now fixed | LOW | Complexity | fix merged | — |
| L-2 | H4 governor-throttle hypothesis — code-refuted | LOW | — | refutation proven | — |
