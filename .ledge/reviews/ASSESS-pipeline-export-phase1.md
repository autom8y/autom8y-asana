---
type: review
status: draft
initiative: project-asana-pipeline-extraction
phase: 1
sprint: sprint-2-review
created: 2026-04-28
specialist: pattern-profiler
upstream_scan: .ledge/reviews/SCAN-pipeline-export-phase1.md
upstream_qa: .ledge/reviews/QA-pipeline-export-phase1.md
upstream_handoff: .ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md
---

# Assessment: project-asana-pipeline-extraction Phase 1

## §1 Telos Pulse Echo (verbatim)

> "A coworker's ad-hoc request to extract actionable account lists from
> Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana
> service: there is no first-class BI export surface, and any response today
> would be a one-off script with zero reusability. This initiative transitions
> from observation (Iris snapshot) to repeatable, account-grain, CSV-capable
> data extraction codified in the service's dataframe layer."

Source: `.sos/wip/frames/project-asana-pipeline-extraction.md:15`

---

## §2 Inception Anchor Citations

| Artifact | Path | Lines | Role in This Assessment |
|----------|------|-------|-------------------------|
| S1 SCAN | `.ledge/reviews/SCAN-pipeline-export-phase1.md` | 1-216 | Primary signal set; 9 signals across 5 categories |
| Handoff | `.ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md` | §4.2 PP-Q1..Q4 | Assessment question authority |
| Handoff | `.ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md` | §5 | Carry-forward gap inventory |
| Handoff | `.ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md` | §7 | Anti-pattern guards AP-R-1..AP-R-5 |
| QA Report | `.ledge/reviews/QA-pipeline-export-phase1.md` | §3 | DEF-01..DEF-07 (2 MEDIUM + 5 LOW) |
| QA Report | `.ledge/reviews/QA-pipeline-export-phase1.md` | §9-§10 | CONDITIONAL-GO verdict + release conditions |
| main.py | `src/autom8_asana/api/main.py:374-395` | — | DEF-08 direct file read (JWT exclude_paths) |
| exports.py | `src/autom8_asana/api/routes/exports.py:221-228` | — | DEF-08 pat_router factory verification |

---

## §3 PP-Q1: 6-Category Health Grade Table

> **Weakest-link model** per review-ref. Categories are: correctness, security,
> maintainability, performance, observability, test-coverage. This is a 6-category
> extension of the standard 5-category schema to match the handoff PP-Q1 mandate.

### Grade Table

| Category | Grade | Rationale |
|----------|-------|-----------|
| Correctness | B | No critical logic errors. DEF-05 (MEDIUM: activity-state default suppression on OR/NOT branches semantically broadens result set) and DEF-06 (LOW: empty section IN list) are behavioral correctness concerns. DEF-05 is spec-compliant but produces surprising results for callers using OR/NOT. Op enum ESC-1 design is CONTAINED (SS-Q3: OPERATOR_MATRIX defense-in-depth prevents silent wrong-result). 1 medium finding, 2 low findings → B anchor (0 critical, 0 high, <=5 medium). |
| Security | C | DEF-08 (pattern-profiler-discovered): `/api/v1/exports` is confirmed ABSENT from `jwt_auth_config.exclude_paths` at `main.py:374-395`. The exports PAT mount (`exports_router_api_v1`) is tagged `"exports"` (PAT-classified), which means JWTAuthMiddleware processes it. If the JWT middleware rejects non-JWT Bearer tokens BEFORE the `pat_router` factory's `get_auth_context` DI fires, Vince's PAT-authenticated requests would silently receive 401. All other PAT-tagged route trees (`/api/v1/dataframes/*`, `/api/v1/tasks/*`, `/api/v1/projects/*`, etc.) are explicitly excluded. `/api/v1/exports` is not. This is a structural auth-configuration asymmetry with HIGH concern potential (see DEF-08 grading in §4). 1 structural HIGH concern → C anchor. |
| Maintainability | B | exports.py at 569 LOC triggers the >500-line threshold (SS-Q1). export_handler spans ~188 LOC (SS-Q1). Both are structurally justified by the linear pipeline shape and inline docstring; decomposition would add indirection without clarity gain. `attach_identity_complete` all-False silent fallback (SS-Q2) is a schema-drift maintainability concern (MEDIUM). No mixed-concern indicators. DEF-02 (emptiness semantics) and DEF-07 (dedupe fallback) are LOW documentation/default concerns. Overall: 0 critical, 0 high, 2 medium → B. |
| Performance | A | No new external dependencies. Lazy polars import (SS-Q1) carries negligible per-call cost post-sys.modules caching. ESC-3 size measurement synthetic-fixture verified (2 rows / 46B CSV / 994B Parquet). Live measurement deferred to Sprint 4.5 (DEFER-WATCH-7). No synchronous blocking patterns introduced. 0 critical, 0 high, 0 medium → A. Note: live ESC-3 measurement remains open; if live data exceeds 50k rows / 10MB, Phase 1.5 streaming ADR triggered — this is a known-bounded risk, not a current finding. |
| Observability | A | LEFT-PRESERVATION GUARD wrapper emits `exports_left_preservation_guard_noop` log with Phase 1 metadata (phase, join_active, predicate_join_semantics, entity_type, project_gid, request_id) — verified by S1 SS-Q5 and AP-R-3(c) spot-check. ESC-3 `_emit_export_size_metric` confirmed at `dataframes.py:245-268`. SS-Q2 notes `filter_incomplete_identity` missing-column guard logs a warning but test does not assert emission — this is a LOW test-coverage signal for observability, not an observability gap in production. The observability seam itself fires correctly. 0 critical, 0 high, <=2 medium → A. |
| Test-Coverage | B | 87 tests total; test-to-source LOC ratio 1.08 (well above 0.3 threshold). SS-Q5: `CacheNotWarmError` path in the LEFT-PRESERVATION GUARD wrapper is untested at the wrapper level (`exports.py:264-268`). Handler-level test coverage exists for 400/503 error paths. AP-R-3 spot-checks corroborated behavioral assertions for identity_complete null-key, dual-mount routes, and guard wrapper observability. DEF-01 (canonical multi-project pair not tested as a pair) is MEDIUM for correctness but also a test-coverage concern. Overall: 0 critical, 0 high, 2 medium (wrapper gap + DEF-01 surrogate) → B. |
| **Overall** | **C** | **Weakest-link calculation: grades are B, C, B, A, A, B. Median is B. Security category = C. Applying floor-drag rule: one C category does not trigger cascade (3+ C's required for letter-drop; D/F caps not triggered). Median B, but security C is the weakest category. By weakest-link discipline the overall grade is the median UNLESS floor-drag rules fire OR a single category is D/F. Here: no D, no F, only one C. Per the model, overall = median = B with the security C as the load-bearing risk flag. However, the security finding (DEF-08) is a CONFIRMED structural gap on the load-bearing user path — it directly threatens the telos (Vince's PAT CSV requests). Applying weakest-link principle conservatively: overall = C, matching the security category. The security finding must resolve before an upgrade to B is warranted.** |

### Weakest-Link Calculation Trace

- Grades by category: Correctness=B, Security=C, Maintainability=B, Performance=A, Observability=A, Test-Coverage=B
- Sorted: A, A, B, B, B, C
- Median of 6 values: between position 3 (B) and 4 (B) → median = B
- Floor-drag rule checks:
  - Any F? No → no D cap
  - Any D? No → no C cap
  - 3+ categories at C or below? No (only 1 C) → no letter-drop
- Median alone = B. No cascade rules fire.
- Weakest-link conservative application: security C is the single failing dimension on the load-bearing path (DEF-08 directly blocks telos). Per assessment-methodology P-08 (construct underrepresentation), masking a load-bearing security concern behind an averaged B would underrepresent the actual risk. Overall = **C**.
- [PLATFORM-HEURISTIC: the decision to set overall = C (matching weakest category) rather than B (median) is a conservative weakest-link application. The cascade rules mechanically yield B; this assessment applies the underlying principle — "overall assessment validity limited by weakest inference" (AV:SRC-007 Kane 2013) — to surface the security finding rather than mask it. Case-reporter may revise if DEF-08 resolves before report.]

---

## §4 PP-Q2: Defect Re-Grading Table

> AP-R-1 guard: independent re-grade required. AP-RR-1 requires mapping qa-adversary
> severity to review-rite severity with documented rationale (see §7 for
> severity-model mapping). AP-RR-5: every finding traces to a SCAN signal or
> QA defect ID. DEF-08 is a pattern-profiler-discovered defect from SS-Q4.

### Severity-Model Mapping (abbreviated — full mapping in §7)

- qa-adversary CRITICAL → review-rite Critical (same: blocks correctness/security/operability)
- qa-adversary HIGH → review-rite High (same: significant maintainability/reliability risk)
- qa-adversary MEDIUM → review-rite Medium **OR** High depending on whether the finding "significantly impacts maintainability or reliability" vs. "clear improvement opportunity"
- qa-adversary LOW → review-rite Low or Medium depending on operational impact

### Re-Grade Table

| ID | qa-adv Severity | Review-Rite Severity | Escalation? | Rationale | Signal Trace |
|----|-----------------|---------------------|-------------|-----------|--------------|
| DEF-01 | MEDIUM | **Medium** | No | Inception-anchor canonical multi-project pair not exercised together. The multi-project union code path (pl.concat how='diagonal_relaxed') is tested with synthetic gids but not the canonical Reactivation+Outreach pair. This is a test completeness concern on a non-trivial code path; it is a clear improvement opportunity, NOT a significant reliability risk (the code path executes correctly per synthetic tests). Stays Medium. | QA §3 DEF-01; SS-Q5 context |
| DEF-02 | LOW | **Low** | No | Empty-string and whitespace-only identity_complete semantics pass as complete. PRD §5.3 defines IS-NOT-NULL semantics — the implementation is spec-compliant. This is an informational edge-case observation pending Vince elicitation, not a defect in the current spec. Stays Low. | QA §3 DEF-02; _exports_helpers.py:141-145 |
| DEF-03 | LOW | **Low** | No | Cross-auth runtime probe not executable in QA session. Structural dual-mount guard verified; runtime auth is platform middleware responsibility. This is a NOT-EXECUTABLE observation with deferred verification path, not a code defect. Stays Low. | QA §3 DEF-03; main.py:438-439 |
| DEF-04 | LOW (BY-DESIGN) | **Low** | No | Export route ignores Accept header — body-field-only contract per PRD §8.3 mechanism (1). This is a documented design choice, not a defect. Stays Low. | QA §3 DEF-04; exports.py:493 |
| DEF-05 | MEDIUM | **Medium** | No | Activity-state default suppression on OR/NOT branches semantically broadens result set. The behavior is consistent with the current implementation's design (predicate_references_field walks the tree uniformly) but produces surprising semantics for callers using OR/NOT. This is a behavioral clarity concern and DEFER-WATCH-3 elicitation item — a clear improvement opportunity with medium caller-surprise risk. Does NOT rise to High because (a) no silent data loss — rows are RETURNED not lost, (b) the behavior is deterministic and consistent, (c) it is spec-pending (DEFER-WATCH-3 documents this explicitly). Stays Medium. | QA §3 DEF-05; _exports_helpers.py:228-251 |
| DEF-06 | LOW | **Low** | No | Empty section IN list suppresses default but matches no rows. Low-priority validation gap; the result is empty rows, not corrupted data. No user-visible silent error. Stays Low. | QA §3 DEF-06; _exports_helpers.py:265-269 |
| DEF-07 | LOW (DOCUMENTED-BY-DESIGN) | **Low** | No | Dedupe winner policy falls back to row-order when modified_at absent. PHASE_1_DEFAULT_COLUMNS includes modified_at so this is not a Phase 1 risk. Documented by design per DEFER-WATCH-1. Stays Low. | QA §3 DEF-07; _exports_helpers.py:174-205 |
| DEF-08 | *(NEW — not in qa-adversary report)* | **High** | NEW HIGH | See full grading below. SS-Q4 PAT auth middleware exclusion gap. `/api/v1/exports` absent from `jwt_auth_config.exclude_paths`. Direct file read confirmed: `main.py:381-388` lists 7 PAT-tagged path prefixes (dataframes, tasks, projects, sections, users, workspaces, offers) — `/api/v1/exports` is not among them. The exports_router_api_v1 is tagged `"exports"` (PAT-classified per main.py tag taxonomy). If JWT middleware evaluates PAT Bearer tokens before `get_auth_context` DI fires, Vince's CSV requests receive 401 silently. Confidence upgrades from S1's MEDIUM to HIGH after direct file read confirms the structural gap (see DEF-08 detail block below). | SS-Q4; main.py:374-395; exports.py:221-228 |

### DEF-08 Full Grading Block

**Finding**: `/api/v1/exports` missing from `jwt_auth_config.exclude_paths`

**Verification performed by pattern-profiler** (direct file reads per crime-scene protocol):

1. Read `main.py:374-395`: The `jwt_auth_config.exclude_paths` list at lines 381-388 contains exactly:
   - `/redoc`
   - `/api/v1/webhooks/*`
   - `/api/v1/tasks/*`
   - `/api/v1/projects/*`
   - `/api/v1/sections/*`
   - `/api/v1/users/*`
   - `/api/v1/workspaces/*`
   - `/api/v1/dataframes/*`
   - `/api/v1/offers/*`

   `/api/v1/exports` (or `/api/v1/exports/*`) is **confirmed absent**.

2. Read `exports.py:221-228`: `exports_router_api_v1 = pat_router(prefix="/api/v1/exports", tags=["exports"])`. The PAT mount uses `pat_router` factory with tag `"exports"`.

3. Read `main.py:419-439`: Router registration order shows `exports_router_api_v1` mounted BEFORE `query_router` (correct ordering per the SCAR-WS8 discipline) — but this addresses path shadowing, not JWT auth exclusion.

**Middleware-bypass behavior assessment**: S1 SCAN correctly flagged at MEDIUM confidence that the risk "depends on JWTAuthConfig middleware semantics and whether pat_router factory explicitly bypasses the JWT middleware." After reviewing exports.py, the pat_router factory invocation does NOT inject middleware bypass logic at the router level — it creates an APIRouter with tag classification. The JWTAuthMiddleware exclusion operates at the path-glob level in `jwt_auth_config.exclude_paths`. The structural gap is confirmed: the PAT mount path is not excluded.

**Severity determination**: The review-rite severity model defines High as "Significant maintainability or reliability risk." However, DEF-08 more closely maps to a security/operability concern: if the gap is live, PAT-authenticated requests to `/api/v1/exports` would receive 401 rejections from the JWT middleware, blocking Vince's primary use case (the telos user path). The finding sits between the High and Critical definitions:
- It is NOT Critical (does not confirm "blocks correctness, security, or operability" as a live fact — the middleware behavior remains INFERRED; the S2S route at `/v1/exports` is unaffected)
- It IS High (significant reliability risk: the load-bearing user path for Phase 1 may be silently broken in production if the middleware gap is exploited)

**Review-rite severity: HIGH** [MODERATE confidence ceiling: the middleware-bypass behavior of `pat_router` cannot be confirmed without reading `_security.py` or `autom8y_api_middleware` internals — not in Phase 1 scan scope. The structural gap in `exclude_paths` is confirmed HIGH confidence; the actual runtime failure mode is MODERATE confidence. Per self-ref-evidence-grade-rule, STRONG severity claims require external corroboration or full runtime verification. Assigning HIGH (not Critical) reflects this ceiling.]

**GO/NO-GO impact**: This finding does NOT change the trajectory from CONDITIONAL-GO to NO-GO on its own, for two reasons: (1) runtime behavior is MODERATE confidence — if `pat_router` has an internal middleware bypass mechanism not visible from `exports.py`, the gap is benign; (2) the Sprint 4.5 live-smoke task will surface a 401 failure immediately if the gap is live. The finding SHOULD be added to the CONDITIONAL-GO conditions as a Sprint 4.5 verification item. Case-reporter owns the final verdict.

---

## §5 PP-Q3: Sprint 4.5 Deferral Risk Assessment

### SPRINT-4.5-LIVE-SMOKE

- **Description**: Canonical Reactivation+Outreach pair end-to-end with warm Asana cache
- **Blocker for release**: YES — per HANDOFF §5.2, qa-adversary explicitly marked `blocker_for_release: yes — Vince's verification depends on this`. The telos verified-realized-definition requires Vince user-report verification at 2026-05-11 with `attester: theoros@know`. Without live-smoke, DEF-01 (canonical pair unverified) and DEF-08 (PAT auth exclusion gap) both remain unverified in production conditions. The live-smoke task is also the mechanism that would surface a 401 from the DEF-08 middleware gap if it fires.
- **Risk if skipped**: HIGH — the telos pivot-point (Vince's original request) would ship unverified against canonical project IDs. Combined with DEF-08 uncertainty, a 401-producing auth misconfiguration could silently block the primary use case.
- **Recommendation for case-reporter**: Retain as hard release condition (qa-adversary's original verdict). Do not downgrade.

### SPRINT-4.5-ESC-3-LIVE-MEASUREMENT

- **Description**: Live row count + serialized size measurement; threshold check (>50k rows or >10MB → Phase 1.5 streaming ADR)
- **Blocker for release**: NO — qa-adversary correctly assessed this as non-blocking. The ESC-3 emit-block is verified by synthetic fixture; the Phase 1.5 streaming-ADR trigger threshold is a known-bounded future decision point, not a current defect. The measurement infrastructure is in place; the threshold check is a data-driven governance step.
- **Risk if skipped before release**: LOW-MEDIUM — if live data exceeds thresholds and this isn't caught before Vince's first production use, the user experience degrades (large unserialized response). The risk is observable (users experience slow/timeout) and the streaming ADR trigger is documented. This is a planned follow-up, not a silent failure mode.
- **Recommendation for case-reporter**: Non-blocking. Retain as Sprint 4.5 task with clear owner. If live-smoke is running (see above), ESC-3 measurement piggybacks at zero incremental cost.

### SPRINT-4.5-ROUTED-ELICITATION

- **Description**: 3 routed elicitation/test-add items per QA defect report (DEF-05 elicitation via DEFER-WATCH-3, DEF-03 cross-auth test, DEF-02 documentation)
- **Blocker for release**: PARTIAL — the 3 items have different risk profiles:
  - **DEF-05 elicitation (DEFER-WATCH-3)**: Non-blocking. The current behavior is deterministic and documented; Vince elicitation is required to close DEFER-WATCH-3 but the behavior does not prevent Phase 1 from being useful. Medium risk.
  - **DEF-03 cross-auth test**: Non-blocking per qa-adversary. Structural dual-mount is verified; runtime auth is platform middleware territory. Low risk. The DEF-08 live-smoke will partially cover this path.
  - **DEF-02 documentation**: Non-blocking. PRD §5.3 documentation update or Vince elicitation. Low risk.
- **Risk if all 3 skipped**: MEDIUM aggregate — DEF-05 elicitation is the highest-risk item because if Vince's downstream use cases involve OR/NOT section predicates, the unexpected semantics will surface as a data quality complaint post-release. Pre-release elicitation is cheaper than post-release remediation.
- **Recommendation for case-reporter**: Non-blocking as a group, but DEF-05 elicitation should be prioritized before or concurrent with Vince's live-smoke session.

---

## §6 PP-Q4: Procession-Quality Methodology Signal

### Procession Trace Assessment

The Phase 1 cross-rite procession followed: frame → shape → workflow → spike → PRD → TDD → ADR → impl → QA → SCAN.

**Spike HYBRID verdict resolution**: The spike correctly surfaced the HYBRID verdict (LEFT-PRESERVATION GUARD mechanism, no Phase 1 joins) and produced clean escalations (ESC-1/ESC-2/ESC-3) that all resolved within Phase 1. The ESC-1 "date ops translated outside compiler" design is architecturally sound (OPERATOR_MATRIX defense-in-depth confirmed by SS-Q3). No over-escalation or under-escalation detected. CLEAN.

**Sprint 2 architect DELTA-SCOPE escalations**: HANDOFF §5.4 PRC-1 documents a factual error in the Phase 0 explore-swarm output (FleetQuery dual-AUTH claim). The Sprint 2 architect caught and corrected this in TDD §15.2 — the right rite caught the error at the right altitude. No impact on Phase 1 ship. The correction was not persisted to `.know/api.md` (PRC-1 still open) — a knowledge hygiene miss, not a procession failure.

**P1-C-04 principal-engineer compliance**: QA P-9 independently verified zero modifications to all 6 forbidden files (engine.py, join.py, compiler.py, cascade_resolver.py, cascade_validator.py, section_registry.py). The constraint was respected under adversarial spot-check. CLEAN.

**qa-adversary CONDITIONAL-GO and real risk surfaces**: The qa-adversary verdict surfaced real risk: DEF-01 (canonical pair unverified) and DEF-05 (OR/NOT default suppression) are non-trivial findings that required independent review. The CONDITIONAL-GO conditions are appropriately bounded. However, **qa-adversary missed DEF-08** (the JWT auth exclusion gap for `/api/v1/exports`). This is the most significant procession-level observation: the within-rite qa-adversary explicitly verified dual-mount auth scope (P-3: "Per-call auth-scope enforcement delegated to existing PAT/S2S middleware — NOT verified at runtime in this session — see DEF-03 NOT-EXECUTABLE") but did NOT inspect the jwt_auth_config.exclude_paths list at main.py:374-395. DEF-03 was framed as a runtime cross-auth probe; the exclude_paths structural gap was a separate signal that required cross-file correlation (exports.py auth tag → main.py exclude_paths). The rite-disjoint review rite catching this gap is exactly the purpose of the terminal adversarial review.

**Methodology-level concern — SCAR-WS8 pattern propagation**: The SCAR-WS8 route-ordering constraint (documented in `.know/scar-tissue.md:148`) was correctly applied for path shadowing (exports mounts before query_router) but the parallel concern — adding new PAT-tagged route trees requires updating jwt_auth_config.exclude_paths — was NOT propagated as an explicit checklist item in the TDD or implementation documentation. The SCAR-WS8 discipline should be extended to cover both the ordering constraint AND the exclude_paths synchronization. This is a procession-level knowledge gap, not a code defect.

**Procession Quality Grade: B**

Rationale: The procession is well-structured with clean rite-to-rite handoffs, strong constraint compliance (P1-C-04), and a spike that resolved to a clean phase boundary. The CONDITIONAL-GO verdict from qa-adversary is appropriate. One HIGH finding (DEF-08) slipped through qa-adversary's review — explainable by the within-rite self-attestation ceiling (MODERATE per qa-adversary §1.3) and the cross-file correlation required to surface the gap. The review rite caught it as designed. The SCAR-WS8 knowledge gap is a documentation debt item. Overall: a well-run procession that fulfilled its rite-disjoint critic mandate.

---

## §7 Severity-Model Mapping (AP-RR-1 Documentation)

The qa-adversary report uses CRITICAL/HIGH/MEDIUM/LOW nomenclature. The review-rite severity model uses the same tier names but with slightly different operative definitions. Mapping applied in this assessment:

| qa-adversary Tier | Review-Rite Tier | Operative Difference | Applied Mapping |
|-------------------|-----------------|----------------------|-----------------|
| CRITICAL | Critical | qa-adversary: "zero critical defects" — no instances in this report | No qa-adversary Critical findings to map |
| HIGH | High | qa-adversary: "significant maintainability risk"; review-rite adds reliability risk explicitly | No qa-adversary HIGH findings; DEF-08 is a pattern-profiler-discovered HIGH |
| MEDIUM | Medium or High | qa-adversary MEDIUM = "significant enough to warrant Sprint 4.5 action"; review-rite MEDIUM = "clear improvement opportunity"; review-rite HIGH = "significant reliability risk" | DEF-01 and DEF-05 remain Medium — they are improvement opportunities, not reliability blockers |
| LOW (NOT-EXECUTABLE) | Low | qa-adversary NOT-EXECUTABLE tag = cannot confirm behavior in session; review-rite Low = informational/opportunistic | DEF-03, DEF-04 stay Low |
| LOW (BY-DESIGN) | Low | qa-adversary BY-DESIGN = accepted deviation from pattern; review-rite Low = nice-to-have | DEF-04, DEF-07 stay Low |
| LOW | Low | Standard alignment | DEF-02, DEF-06 stay Low |

**Net re-grade deltas**: DEF-01 through DEF-07 all remain at their original tiers under review-rite semantics. DEF-08 is a new HIGH finding not present in qa-adversary's report (AP-R-1 guard satisfied — zero deltas on DEF-01..07 is acceptable given the introduction of a new HIGH finding DEF-08 that qa-adversary missed).

---

## §8 Cross-Rite Routing Hints

> Routing hints only. Case-reporter (Sprint 3) makes binding routing decisions.

| Finding | Target Rite | Trigger Signal |
|---------|-------------|----------------|
| DEF-08 (jwt_auth_config.exclude_paths gap) | arch + 10x-dev | Structural auth-configuration gap requires: (a) arch to confirm pat_router factory middleware bypass behavior; (b) 10x-dev to add `/api/v1/exports/*` to exclude_paths if bypass is not independent, and add a TestClient-based test confirming PAT Bearer accepted on PAT route |
| DEF-05 (OR/NOT default suppression semantics) | 10x-dev + docs | Principal-engineer fix or PRD §4.3 documentation; DEFER-WATCH-3 elicitation with Vince before or concurrent with live-smoke |
| SS-Q2 filter_incomplete_identity unlogged warning | 10x-dev | Test-add: assert log warning fires in the missing-column case (low priority) |
| SS-Q3 _build_expr pragma:no cover | 10x-dev | Test-add: regression test confirming InvalidOperatorError fires on date-op Comparison routed through PredicateCompiler (defense-in-depth verification) |
| SS-Q5 CacheNotWarmError wrapper path | 10x-dev | Test-add: wrapper-level unit test for None return path (optional; handler-level coverage exists) |
| SPRINT-4.5-ESC-3-LIVE-MEASUREMENT | sre | SRE ADVISORY: export_format_serialized log signal available for SLO/SLI dashboards; Phase 1.5 streaming ADR threshold is 50k rows / 10MB |
| PRC-1 FleetQuery .know factual error | theoros | Knowledge persistence: update .know/api.md FleetQuery section with corrected dual-AUTH claim |
| SCAR-WS8 exclude_paths discipline gap | 10x-dev + theoros | Add exclude_paths synchronization step to the PAT-route-add TDD checklist; persist as SCAR-WS8 extension in .know/scar-tissue.md |

---

## §9 Evidence Trail

| Grade/Finding | Signal Source | File:Line | Confidence |
|---------------|--------------|-----------|------------|
| Security = C | DEF-08 (pattern-profiler-discovered via SS-Q4) | main.py:374-395; exports.py:221-228 | HIGH (direct file read) |
| DEF-08 severity = HIGH | Direct file read of jwt_auth_config.exclude_paths | main.py:381-388 | HIGH structural gap confirmed; MODERATE runtime failure mode |
| Correctness = B | DEF-05 (MEDIUM), DEF-06 (LOW), SS-Q3 (CONTAINED) | _exports_helpers.py:228-251; compiler.py:53-63,125-148 | HIGH |
| Maintainability = B | SS-Q1 (569 LOC, 188-LOC function), SS-Q2 (silent all-False fallback) | exports.py:1-569; _exports_helpers.py:130-139 | HIGH |
| Performance = A | SS-Q1 lazy import (LOW/Hygiene), ESC-3 synthetic verify | exports.py:336; dataframes.py:245-268 | HIGH |
| Observability = A | SS-Q5 guard wrapper log verified, ESC-3 size emit verified | test_exports_handler.py:75-109; dataframes.py:245-268 | HIGH |
| Test-Coverage = B | SS-Q5 (wrapper gap), DEF-01 (canonical pair gap) | exports.py:264-268; test_exports_handler.py:255-294 | HIGH |
| Overall = C | Weakest-link: Security C is load-bearing telos-path risk | §3 grade table | HIGH (structural); MODERATE (runtime confirmation pending) |
| DEF-01 Medium (retained) | QA §3 DEF-01; test_exports_handler.py:255-294 | grep "1201753128450029" = 0 | HIGH |
| DEF-05 Medium (retained) | QA §3 DEF-05; _exports_helpers.py:228-251 | Static analysis | HIGH |
| DEF-02,03,04,06,07 Low (retained) | QA §3 respective findings | As cited in QA report | HIGH (structural) |
| Procession Quality = B | PRC-1 open, DEF-08 qa-adv miss, SCAR-WS8 gap | HANDOFF §5.4; QA §3 P-3 | MODERATE (self-ref-evidence-grade-rule: rite-internal assessment) |

---

## Coverage Gaps

**No back-route to signal-sifter required.** All five S1 scan questions (SS-Q1..SS-Q5) are answered with file:line evidence. The DEF-08 finding was surfaced from within the SS-Q4 signal set — it is a validation of an existing signal, not a new scan.

**One documentation gap noted**: `_security.py` / `autom8y_api_middleware` internals were not in scope for S1 scan (Phase 1 artifact boundary). The pat_router factory middleware-bypass behavior is INFERRED, not confirmed. Case-reporter should note this as a DEF-08 sub-uncertainty in the routing recommendation to arch.

---

*No pending markers. Artifact complete.*
