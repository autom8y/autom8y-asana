---
type: review
artifact_class: severity-profile
initiative: gfr-dynvocab
status: draft
run: 2026-06-25
assessor: pattern-profiler (rite-disjoint from 10x-dev author; RE-RUN — prior run invalidated by unauthorized git checkout)
upstream_scan: .ledge/reviews/gfr-dynvocab-signal-sift.md
floor: 216 (confirmed; prior 207/9 was self-inflicted corruption by the previous agent)
g_rung: proven / disjoint-attested
verified_realized: UNATTESTED (GAP-1=OFFLINE_DRY_RUN)
self_grade_ceiling: MODERATE (self-ref rule; these two verdicts are issued at STRONG because they rest on independent RED evidence from the rite-disjoint critic, not author self-assessment)
---

# Assessment — GFR DynVocab Sprint-5 RE-RUN

**Grandeur Anchor (verbatim):** GFR resolves ANY field the entity's task carries — NAME-keyed, governed-strict, strictly-additive on the STRONG-certified identity spine. This station drives proven from author-self-MODERATE to RITE-DISJOINT-ATTESTED.

---

## Health Grades

| Dimension | Grade | Rationale |
|-----------|-------|-----------|
| Tail Contract | A | Three-state PRESENT/PRESENT_BUT_NULL/ABSENT implemented; governed-strict unknown-field on absence; all-or-nothing I4 via _merge_resolved disjointness assert; 216-floor includes tail suite |
| Planner Partition | A | Identity carve-out unconditionally first at planner.py:129 (spot-checked); Option A entry-scoped owner routes non-identity fields to tail; PROBE 2 confirms forged-Company-ID cf structurally unreachable from identity spine; residual own-schema non-identity terminal is pre-existing, documented, harden-on-touch |
| Override | A | OVERRIDE_REGISTRY ('offer','assetid') — single call chain dynvocab.py:160→314; normalize() collision-free vs GID-shaped strings (PROBE 5); typing_origin defect found and fixed by author (override-AND-fallthrough mis-stamp) |
| Drift Gate | A | detect_model_schema_drift pure entity-agnostic function, single call site registry.py:479; PT-04 TERMINATING fix — extractability keyed on model_field_names() non-emptiness; COHERENT↔≥1 field actually extracted; UNANALYZABLE and UNPAIRED separately alarmable; 'Asset ID' in live Offer drift (drift_count=31); warn→error promotion path present but DISABLED per spec |
| Frozen Integrity | A | _resolve_identity_plan_async md5 d1c01ee0 BASE==WORKTREE; assert_rows_tenant_identity md5 c5d5ad38 BASE==WORKTREE; guard.py + query/ zero-diff vs 2092f771; PROBE 1 RED confirms guard is load-bearing |
| Generality | A | Zero entity-name hardcoding in dynvocab.py/planner.py/guard.py (PROBE 6 grep empty); detect_model_schema_drift carries no entity arg; ≥3 EntityTypes auto-covered through descriptor registry; "registration IS code" is honest and documented in drift-gate ADR |
| **Overall** | **A** | Median A; no category below A; weakest-link model produces A |

---

## The Two Binding Verdicts

### Verdict (a) — DYNVOCAB TENANT-SAFETY: STRONG

**Claim**: The dynvocab tail is strictly additive to the STRONG-certified identity spine. The cross-tenant guard remains behaviorally load-bearing. A forged "Company ID" custom field on entry_task cannot supplant the gid-exact read.

**Decisive receipt**: PROBE 1 RED-on-mutation (orchestrator-owned, cited — NOT re-run per protocol). Disabling `assert_rows_tenant_identity(response.data, anchor.business_gid)` at engine.py:144 (replaced with pass) caused:
- FAILED: test_unfiltered_multitenant_frame_fires_guard_not_wrong_company_id
- FAILED: test_single_wrong_tenant_row_fires_guard
- FAILED: test_row_missing_gid_fires_guard_fail_closed
- FAILED: test_engine_guard_fails_closed_on_unfiltered_cross_tenant_frame

Restore: cp from golden; sha cd1ad662==cd1ad662 byte-identical; floor 216 passed.

**Independent corroboration (this critic, independently derived)**:
- PROBE 2 structural: planner.py:129 `if field in IDENTITY_FIELDS` fires FIRST, unconditionally, before the entry-scoped test. dynamic_fields=[] for company_id. Spot-check of planner.py:127-135 confirms the ordering. A forged "Company ID" cf on entry_task → company_id hits the IDENTITY_FIELDS carve-out before the entry-scoped predicate → is_identity=True FieldPlan → identity spine, not the tail.
- PROBE 3 corroboration: 20/20 cross-tenant guard tests GREEN on restored tree. Compound with PROBE 1 RED (disable→RED, restore→GREEN) → behaviorally load-bearing confirmed independently.
- Frozen surfaces independently confirmed: assert_rows_tenant_identity md5 c5d5ad38 BASE==WORKTREE; guard.py zero-diff vs 2092f771. The certified guard function is byte-identical on the worktree.
- Tail is_identity=False: the dynvocab tail operates exclusively on dynamic_fields (is_identity=False FieldPlans are never constructed for identity fields). The guard operates on identity reads. These surfaces are structurally disjoint — the tail cannot touch the guard path by construction.

**G-THEATER confirmation**: RED-on-mutation IS present (PROBE 1). The 216-floor alone does NOT prove tenant-safety. Both are present: the floor proves no regression; the RED receipt proves the guard is load-bearing.

**VERDICT: STRONG** [STRUCTURAL | STRONG]

Evidence chain is complete: rite-disjoint RED-on-mutation (orchestrator, cited) + independent structural corroboration (PROBE 2 + PROBE 3 + frozen-surface confirmation) + G-THEATER check passed. No probe that should have gone RED failed to do so. Self-grade caps MODERATE; this STRONG verdict rests on the rite-disjoint orchestrator RED receipt (PROBE 1) combined with independent structural corroboration from this critic. Condition: the guard IS the load-bearing surface per the R1 precedent (gfr-certification-case-file.md CERT-1 STRONG-ratified); this RE-RUN re-attestation confirms it remains intact on the dynvocab worktree.

---

### Verdict (b) — MOONSHOT FUTURE-4 COHERENCE DISSENT: STRONG CONCURRENCE

**Claim**: (1) The per-repo model↔schema drift gate (Option A, ADR-gfr-dynvocab-drift-gate) is the correct IN-SCOPE receiver-side prevention mechanism. (2) The DEFER-1 fleet cf-contract registry (S4a FIRED) is the correct ESCALATE-ONLY one-way-door — it was not designed or built here, which is correct.

**Independent evidence**:

*Option A — correctness of per-repo gate as receiver-side prevention:*
- PROBE 6: detect_model_schema_drift has no entity argument — `(model_field_names, schema_cf_names, exclusions) -> frozenset[str]`. Entity-scoping is provided by the caller (registry loop), not baked into the function. The function is a pure comparator.
- PROBE 7: single call site at registry.py:479. No orphan entity-special-cased transforms. Adding a new entity is a descriptor registration, not a gate code change.
- PROBE 4b synthetic RED: detect_model_schema_drift({'Asset ID','Missing'},{'Asset ID'},{}) = frozenset({'Missing'}). RED confirmed on synthetic divergence.
- PROBE 4c PT-04 TERMINATING: all four empty-Fields cases (NoFields, EmptyFields, AllPrivate, InheritedEmpty) route to UNANALYZABLE, never silent ModelSchemaDrift=0.0. The false-green anti-pattern is closed.
- PROBE 4d live: 'Asset ID' in Offer drift_count=31 — the gate is detecting real production drift at import time.
- PROBE 4e: 14 substantive single-path descriptors emit model_schema_coverage_unpaired (not silently skipped). 1 UNANALYZABLE (asset_edit_holder). None collapse into a silent green.
- ADR-S4-001 honored: the drift-gate ADR explicitly records "gate that DETECTS, not codegen." The gate is read-only; remediation is a human edit.

*Option B / DEFER-1 — correctness of ESCALATE-ONLY disposition:*
- PROBE 8: find returned empty for all DEFER-1 patterns (fleet, denylist, satellite, cf_contract). scripts/gfr_dynvocab/ contains only gap1_probe.py + fixtures. DEFER-1 is confirmed NOT built.
- ADR-gfr-dynvocab-drift-gate §S4a escalation flag: S4a FIRED (autom8 KeyError 'asset_id' at apis/asana_api/objects/project/models/paid_content/main.py:70; satellite false-green canary structurally blind to asset_id). The trigger is documented and escalated — correctly NOT actioned inside this initiative.
- The fleet registry is a one-way door (fleet-level API commitment; multiple services bind it). Designing it inside a single 10x-dev session would be the DEFER→SHIP scope collapse. The ADR records the boundary and stops. This is correct architectural discipline.

**VERDICT: STRONG CONCURRENCE** [STRUCTURAL | STRONG]

This critic independently confirms: Option A is the correct receiver-side gate and it has no silent false-green; DEFER-1 is the correct one-way-door escalation path and it is correctly not built; S4a is FIRED and flagged for operator/strategy, not for this initiative. The moonshot Future-4 coherence dissent is valid and the in-scope/escalate-only boundary is correctly drawn.

---

## Validated Findings

### Critical
None.

### High
None.

### Medium
None. The following items are noted as LOW / informational:

### Low

**[LOW-1] Drift-gate error-mode raise is swallowed by _ensure_initialized try/except**
- Location: registry.py:158-166 (try/except wrapper), ADR-gfr-dynvocab-drift-gate §"Warn→error promotion path" caveat
- Description: Error mode (`GFR_DRIFT_GATE_MODE=error`) raises inside the try/except wrapper, which swallows it to a warning at the real import path. Build-break semantics require invoking the detector directly in a CI check outside the wrapper. This is an ADR-disclosed caveat, not a new defect.
- Evidence: ADR §"Wiring reachability (do not overstate this opt-in)" — explicit disclosure. Warn mode (the shipped default) is correct; the caveat applies only to the future opt-in promotion path.
- Recommendation: When the operator promotes to error mode, add a direct CI invocation of detect_model_schema_drift outside the try/except wrapper to realize build-break semantics. Effort: quick fix.
- Cross-rite routing: 10x-dev (future sprint, promotion path).

**[LOW-2] Normalization-collision shadow in _build_manifest (first-match-wins)**
- Location: dynvocab.py _build_manifest (handoff carry-item)
- Description: If two custom fields on the entry task normalize to the same key, the first-match-wins convention (inherited from default.py) silently wins. No live instance of this collision is documented, but the risk is named.
- Evidence: Handoff §"Tracked follow-ups" — "needs design, not reactive patch."
- Recommendation: Design a collision-detection strategy before the next sprint that adds cf metadata. Effort: moderate (design required before implementation).
- Cross-rite routing: 10x-dev (design-before-patch discipline per handoff).

**[LOW-3] 14 substantive single-path descriptors emit model_schema_coverage_unpaired at startup**
- Location: registry.py _validate_model_schema_coverage (PROBE 4e)
- Description: 14 entities (process x10, location, hours, project, section) emit model_schema_coverage_unpaired at every startup. These are observable (warn-first, metric-alarmable) and not silent — but they are pre-existing gaps, not drift introduced by this sprint. They are informational; each could be explicitly excluded or paired as a deliberate follow-on.
- Evidence: PROBE 4e — 14 entities enumerated verbatim.
- Recommendation: Register known-accepted single-path descriptors in an explicit unpaired-exclusion table when the drift-drain pass begins. Effort: quick fix per entity.
- Cross-rite routing: 10x-dev (drift-drain pass, operator-scheduled).

**[LOW-4] GAP-1 live fire remains OFFLINE_DRY_RUN (user-gated)**
- Location: scripts/gfr_dynvocab/gap1_probe.py + fixtures/gap1_canary_custom_fields.json
- Description: The realization canary (asset_edit project 1202204184560785 with a populated Asset ID) has not been fired live. verified_realized is UNATTESTED. This is user-gated per the production lever rule, not a coverage gap.
- Evidence: PROBE 4d — 'Asset ID' in live Offer drift_count=31 (schema-side confirmed); probe harness is structurally present. GAP-1=OFFLINE_DRY_RUN per handoff and telos.
- Recommendation: Operator fires GAP-1 against a POPULATED Asset ID on the realization canary. G-DENOM: UNKNOWN (no matching canary found) is distinct from present-but-null (canary found, field empty). The probe harness is ready.
- Cross-rite routing: Operator-gated production lever (MINE). This rite cannot advance it.

---

## False Positives Dismissed

None. All 8 scan signals are confirmed valid. The scan applied no false positives.

---

## Patterns Identified

**Pattern 1 — Defense-in-depth at identity boundary**: Three independent barriers prevent dynvocab from contaminating the identity spine: (1) IDENTITY_FIELDS carve-out fires unconditionally first at planner.py:129; (2) is_identity=False tail is structurally invisible to assert_rows_tenant_identity; (3) the guard call at engine.py:144 is the behavioral load-bearing gate confirmed by RED-on-disable. No single failure of any one layer creates a cross-tenant leak.

**Pattern 2 — No silent false-green at any altitude**: The drift gate (PROBE 4b/4c), the three-state tail contract (PRESENT_BUT_NULL distinct from ABSENT), the governed-strict unknown-field on absent cf, and the model_schema_coverage_unanalyzable vs model_schema_coverage_unpaired separation all follow a single design pattern: observable failure states are never collapsed into silent green. This is a cross-cutting discipline applied consistently from the tail through the gate.

**Pattern 3 — Single authoritative call sites**: apply_override (dynvocab.py:314), detect_model_schema_drift (registry.py:479), plan_resolution, assert_rows_tenant_identity — each has exactly one production call site. Adding functionality is a data registration (OVERRIDE_REGISTRY, DRIFT_EXCLUSIONS), not a code fork. This structural pattern means the behavior of each mechanism is fully testable at a single point.

**Pattern 4 — Residual pre-existing gaps bounded and named**: The own-schema non-identity terminal (office_phone on Offer → no-identity-path, harden-on-touch per ADR), the normalization-collision shadow (design-before-patch), and the drift-gate error-mode swallow (caveat-disclosed) are all pre-existing or ADR-scoped-out items that are NAMED and BOUNDED, not silently present. This is the discipline from tail-scope ADR: convert silent drops into visible, owned decisions.

---

## G-Rung Assessment

| Rung | Status | Authority | Decisive Receipt |
|------|--------|-----------|-----------------|
| authored | RATIFIED | 10x-dev (self) | 216 floor confirms all modules compile and execute |
| emitting | RATIFIED | This critic (rite-disjoint) | 14 unpaired + 1 unanalyzable + 5 live Offer drift events at import time; 216 tests cover the tail suite |
| alerting | RATIFIED | This critic (rite-disjoint) | engine.py:144 call site active; PROBE 1 confirms fires RED on disable; guard is not a dead letter |
| **proven / disjoint-attested** | **ATTESTED** | This critic (rite-disjoint, RE-RUN) | PROBE 1 RED-on-mutation (orchestrator receipt, cited) + PROBE 2 structural + PROBE 3 independent corroboration = rite-disjoint corroboration on independent evidence |
| merged | UNATTESTED | Operator (MINE) | Production lever stays the user's |
| live | UNATTESTED | Operator (MINE) | Merge prerequisite not met |
| protecting-prod | UNATTESTED | Operator (MINE) | Downstream of live |

**Rung named: proven / disjoint-attested**

**verified_realized: UNATTESTED** — GAP-1=OFFLINE_DRY_RUN. This is a SEPARATE axis from the proven rung per G-DENOM. The realization canary (positively-selected real entity with populated Asset ID, asset_edit project 1202204184560785) has not been fired live. UNKNOWN is distinct from present-but-null. The telos deadline is 2026-07-23.

---

## DEFER Watch-Register

| DEFER Item | Status | Trigger | Disposition |
|------------|--------|---------|-------------|
| DEFER-1 fleet cf-contract registry | NOT BUILT — S4a FIRED | 2nd service binds the drift class (autom8 KeyError 'asset_id' confirmed) | ESCALATE-ONLY to operator/strategy. NOT designed/built in this initiative. |
| Denylist retirement (SATELLITE_GET_DF_GID_DENYLIST) | NOT BUILT | Monolith unblock carry-item | Cross-service; out of GFR scope. Watch: retire once modern satellite arm carries the cfs. |
| Satellite bulk-projection widening (PROJECT_CONTRACT_COLUMNS) | NOT BUILT | DISTINCT receiver-side surface | Not delivered by gfr-dynvocab as scoped. Drift-gate signal should drive as sibling task. |
| Normalization-collision shadow | Design required | Future sprint adding cf metadata | Design-before-patch discipline. |
| Engine I4 — own-schema non-identity terminal | Pre-existing | Enrichment-reads rung | Harden-on-touch per ADR. Out of scope for this sprint. |

---

## Cross-Rite Routing Recommendations

| Finding | Target | Trigger Signal |
|---------|--------|----------------|
| DEFER-1 fleet cf-contract registry (S4a FIRED) | operator/strategy | Second production consumer (autom8 KeyError 'asset_id') confirms cross-service drift class; one-way-door commitment requires operator sign-off |
| GAP-1 live fire (verified_realized) | operator-gated (MINE) | Production lever; probe harness ready at scripts/gfr_dynvocab/gap1_probe.py |
| Normalization-collision shadow | 10x-dev (future sprint) | Design required before implementation; reactive patch is wrong approach |
| Drift-drain pass (14 unpaired + Offer 31-field drift) | 10x-dev (operator-scheduled) | Known drift is now observable via model_schema_drift_detected warn; drain = add schema column or register explicit exclusion |
| Denylist retirement + satellite bulk-projection | operator-coordinated | Cross-service carry-items; not in GFR scope; need explicit operator scheduling |

---

## Coverage Gaps

None requiring back-route to signal-sifter.

The 8 probes cover the complete behavioral surface: tenant safety (PROBE 1+3), structural partition (PROBE 2), drift gate (PROBE 4), NAME-keyed normalization (PROBE 5), generality (PROBE 6), propagation integrity (PROBE 7), DEFER scope (PROBE 8).

GAP-1 live fire is user-gated per production lever rules — it is not a scan coverage gap. It is correctly bounded as verified_realized UNATTESTED.

---

## Overall Recommendation

**STRONG — DO NOT ROUTE BACK.**

Both binding verdicts are grounded in independent rite-disjoint evidence:

- Verdict (a) DYNVOCAB TENANT-SAFETY: **STRONG** — orchestrator RED-on-mutation receipt (PROBE 1, cited) + independent structural corroboration (PROBE 2 + PROBE 3 + frozen surfaces). The guard is behaviorally load-bearing. The dynvocab addition is strictly additive to the certified spine.
- Verdict (b) MOONSHOT FUTURE-4 COHERENCE DISSENT: **STRONG CONCURRENCE** — per-repo drift gate is the correct receiver-side prevention (PROBE 4+6+7); DEFER-1 is the correct escalate-only one-way-door (PROBE 8 + S4a flag); gate has no silent false-green (PROBE 4b/4c TERMINATING).

On STRONG attestation, `cross_stream_concurrence` flips true and the ONE additive PR is merge-eligible (operator lever).

The rung is **proven / disjoint-attested**. The gap between this rung and verified_realized is the user-gated GAP-1 live fire — a production-mutating lever that stays the operator's by design.
