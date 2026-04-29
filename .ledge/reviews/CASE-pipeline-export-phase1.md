---
type: review
status: accepted
initiative: project-asana-pipeline-extraction
phase: 1
created: 2026-04-28
specialist: case-reporter
upstream_scan: .ledge/reviews/SCAN-pipeline-export-phase1.md
upstream_assess: .ledge/reviews/ASSESS-pipeline-export-phase1.md
upstream_qa: .ledge/reviews/QA-pipeline-export-phase1.md
upstream_handoff: .ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md
verdict: CONDITIONAL-GO
---

# Case File: project-asana-pipeline-extraction Phase 1

## §1 Telos Pulse Echo (verbatim)

> "A coworker's ad-hoc request to extract actionable account lists from Reactivation and
> Outreach pipelines has exposed a gap in the autom8y-asana service: there is no first-class
> BI export surface, and any response today would be a one-off script with zero reusability.
> This initiative transitions from observation (Iris snapshot) to repeatable, account-grain,
> CSV-capable data extraction codified in the service's dataframe layer."

Source: `.sos/wip/frames/project-asana-pipeline-extraction.md:15`

---

## §2 Inception Anchor Citations

| Artifact | Path | Lines | Role |
|----------|------|-------|------|
| HANDOFF | `.ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md` | 1-332 | Primary inception anchor; §4.3 CR-Q1..Q4; §5 gap inventory; §7 AP guards |
| SCAN (S1) | `.ledge/reviews/SCAN-pipeline-export-phase1.md` | 1-216 | 9 structural signals across 5 categories; SS-Q1..Q5 answers; AP-R-3 spot-checks |
| ASSESS (S2) | `.ledge/reviews/ASSESS-pipeline-export-phase1.md` | 1-251 | 6-category grade table; DEF-08 discovery; PP-Q1..Q4; weakest-link C grade |
| QA Report | `.ledge/reviews/QA-pipeline-export-phase1.md` | 1-382 | DEF-01..07; CONDITIONAL-GO baseline; §9 conditions; §10 handoff envelope |
| DEF-08 direct read | `src/autom8_asana/api/main.py:374-395` | — | jwt_auth_config.exclude_paths confirmed absent of `/api/v1/exports` |
| DEF-08 direct read | `src/autom8_asana/api/routes/exports.py:221-228` | — | exports_router_api_v1 PAT factory confirmed |

---

## §3 Executive Summary

Phase 1 of the pipeline-export initiative has delivered a structurally sound, well-tested dual-mount export endpoint that substantially fulfills the telos: a parameterized, account-grain, CSV-capable extraction surface codified in the service's dataframe layer. The build achieved 87 tests passing (12,422 full suite), respected all 7 P1-C-NN engine-isolation constraints, and produced a clean rite-to-rite procession from frame through QA. However, the rite-disjoint review uncovered one HIGH finding (DEF-08) that qa-adversary missed: `/api/v1/exports` is absent from `jwt_auth_config.exclude_paths` at `main.py:381-388`, creating a structural auth-configuration gap that may silently block PAT-authenticated requests — the primary user path Vince will exercise at the telos verification deadline of 2026-05-11. The overall health grade is **C** (Security drag; weakest-link conservative per ASSESS §3). The binding verdict is **CONDITIONAL-GO**: the codebase is releasable contingent on DEF-08 verification and four Sprint 4.5 conditions; if the PAT auth gap is confirmed live, work back-routes to 10x-dev before release rite proceeds. Three DEFER-WATCH items (dedupe winner policy, column projection, ACTIVATING-state default) require explicit Vince elicitation before release, not silent default acceptance.

---

## §4 CR-Q1: Binding Verdict

### Machine-Parseable Block

```yaml
verdict:
  decision: CONDITIONAL-GO
  rationale_summary: >
    Phase 1 implementation is structurally complete: 87 tests pass, all 7 P1-C-NN
    engine-isolation constraints verified, dual-mount registration correct, ESC-1/2/3
    all CONCUR. The review rite independently discovered DEF-08 (HIGH): /api/v1/exports
    is absent from jwt_auth_config.exclude_paths (main.py:381-388), creating a
    structural PAT-auth gap that may silently block Vince's primary use case. This
    finding was absent from qa-adversary's CONDITIONAL-GO (AP-R-1 guard: review rite
    independently re-graded, not rubber-stamping). The gap must be verified and
    remediated before release rite proceeds. Two MEDIUM defects (DEF-01, DEF-05) and
    five LOW defects (DEF-02..04, DEF-06, DEF-07) are conditionally resolvable in
    Sprint 4.5. Overall health C per weakest-link model. CONDITIONAL-GO with five
    named conditions.
  conditions:
    - id: COND-01
      description: >
        DEF-08 verification and remediation: confirm whether pat_router factory
        independently bypasses JWTAuthMiddleware (read _security.py /
        autom8y_api_middleware). If bypass is NOT independent, add
        /api/v1/exports/* to jwt_auth_config.exclude_paths (main.py:381-388)
        and add a TestClient-based PAT-to-/api/v1/exports fixture confirming
        HTTP 200 (not 401) for a valid PAT Bearer token.
      blocker_for_release: yes
      owner_rite: 10x-dev (with arch confirmation of pat_router semantics)
      verification_method: >
        Direct read of _security.py pat_router factory for middleware-bypass
        logic; if gap is live, TestClient fixture returning 200 on PAT path.
        File:line receipt required before release rite accepts handoff.

    - id: COND-02
      description: >
        Sprint 4.5 live-smoke: execute canonical Reactivation+Outreach pair
        (project_gids [1201265144487549, 1201753128450029]) end-to-end against
        warm Asana cache, format=csv. Closes DEF-01 and surfaces any live
        auth failure from DEF-08 if COND-01 is not fully resolved.
      blocker_for_release: yes
      owner_rite: 10x-dev
      verification_method: >
        Live request with both canonical gids; assert CSV response with
        deduped account-grain rows, identity_complete column, ACTIVE-scoped.
        ESC-3 size measurement piggybacked (row_count < 50k, bytes < 10MB).

    - id: COND-03
      description: >
        Vince elicitation for DEFER-WATCH-1 (dedupe winner policy),
        DEFER-WATCH-2 (column projection default), DEFER-WATCH-3
        (ACTIVATING-state default + DEF-05 OR/NOT semantics). Pre-release
        elicitation required per AP-R-4 guard. These three defaults shape
        the output Vince receives and cannot be silently accepted.
      blocker_for_release: yes
      owner_rite: 10x-dev (elicitation) + theoros@know (persistence)
      verification_method: >
        Vince interview notes documenting signoff on all three defaults,
        or explicit recorded acceptance in session artifact.

    - id: COND-04
      description: >
        DEF-05 activity-state default suppression on OR/NOT branches:
        document current semantic in PRD §4.3 OR tighten rule per Vince
        elicitation (DEFER-WATCH-3). Pre-release documentation or behavioral
        fix required to avoid caller-surprise at telos verification.
      blocker_for_release: yes (deferred documentation is acceptable;
        behavioral change is optional pending Vince preference)
      owner_rite: 10x-dev
      verification_method: >
        Updated PRD §4.3 text committed OR behavioral fix with test coverage.

    - id: COND-05
      description: >
        DEF-03 cross-auth runtime test: add TestClient-based cross-auth
        fixture OR explicitly cite inheritance from existing platform-middleware
        integration suite with file:line receipt.
      blocker_for_release: no (LOW severity; structural dual-mount verified;
        COND-01 live-smoke partially covers this path)
      owner_rite: 10x-dev
      verification_method: >
        TestClient fixture file:line, or citation to existing platform
        middleware integration test that covers PAT/S2S cross-rejection.

  reconciliation_with_qa_adversary: >
    qa-adversary issued CONDITIONAL-GO with 0 HIGH / 2 MEDIUM / 5 LOW defects
    and four Sprint 4.5 conditions. The review rite independently re-graded
    DEF-01..07 (AP-R-1 guard) and confirmed all seven at their original tiers
    under review-rite severity semantics. The review rite additionally
    discovered DEF-08 (HIGH) via cross-file correlation of SS-Q4's
    jwt_auth_config.exclude_paths signal — a structural auth gap qa-adversary
    did not inspect because DEF-03 was framed as a runtime cross-auth probe
    rather than a static exclude_paths audit. DEF-08 promotes the overall
    verdict conditions from qa-adversary's four Sprint-4.5 tasks to five
    named conditions with COND-01 as a hard release blocker. The review rite
    does NOT simply re-issue qa-adversary's verdict. AP-R-1 satisfied.
```

---

## §5 CR-Q2: Gap-Routing Table

> Every row anchored to a specific finding per AP-RR-4. All DEF-NN, DEFER-WATCH-NN,
> Sprint 4.5 items, PRC-NN, and procession items covered.

| Gap ID | Severity | Owner Rite | Target Artifact | Priority | Anchor |
|--------|----------|------------|-----------------|----------|--------|
| DEF-08 | HIGH | 10x-dev + arch | `main.py:381-388` fix + `_security.py` read + TestClient PAT fixture | P0 | ASSESS §4 DEF-08; main.py:381-388; exports.py:221-228 |
| DEF-01 | MEDIUM | 10x-dev | Sprint 4.5 test fixture: canonical pair [1201265144487549, 1201753128450029]; test_exports_handler.py addendum | P0 (release blocker via COND-02) | QA §3 DEF-01; test_exports_handler.py:255-294 |
| DEF-05 | MEDIUM | 10x-dev + Vince elicitation | PRD §4.3 update OR _exports_helpers.py:228-251 behavioral fix | P0 (documentation required pre-release per COND-04) | QA §3 DEF-05; _exports_helpers.py:228-251 |
| DEF-02 | LOW | 10x-dev | PRD §5.3 documentation update OR Vince elicitation; _exports_helpers.py:141-145 | P2 | QA §3 DEF-02; _exports_helpers.py:141-145 |
| DEF-03 | LOW | 10x-dev | TestClient cross-auth fixture OR platform-middleware inheritance citation | P1 (COND-05 non-blocking but tracked) | QA §3 DEF-03; exports.py:540-543 |
| DEF-04 | LOW (BY-DESIGN) | docs | OpenAPI summary update documenting body-field-only format contract; exports.py:487-495 | P2 | QA §3 DEF-04; exports.py:487-495 |
| DEF-06 | LOW | 10x-dev | Validation-time rejection of empty IN list OR documentation; _exports_helpers.py:265-269 | P2 | QA §3 DEF-06; _exports_helpers.py:265-269 |
| DEF-07 | LOW (BY-DESIGN) | 10x-dev | Warning log extension when modified_at absent; _exports_helpers.py:174-205 | P2 | QA §3 DEF-07; _exports_helpers.py:174-205 |
| DEFER-WATCH-1 | — | 10x-dev + Vince | Vince elicitation notes; dedupe contract documentation | P0 (pre-release per COND-03) | HANDOFF §5.3 DEFER-WATCH-1; _exports_helpers.py:174-205 |
| DEFER-WATCH-2 | — | 10x-dev + Vince | Vince elicitation notes; column projection documentation | P0 (pre-release per COND-03) | HANDOFF §5.3 DEFER-WATCH-2; exports.py:101-109 |
| DEFER-WATCH-3 | — | 10x-dev + Vince | Vince elicitation notes; PRD §4.3 update (ties to DEF-05) | P0 (pre-release per COND-03 + COND-04) | HANDOFF §5.3 DEFER-WATCH-3; _exports_helpers.py:228-251 |
| DEFER-WATCH-4 | — | Accepted / no work | No action required | P2 (post-release informational) | HANDOFF §5.3 DEFER-WATCH-4 |
| DEFER-WATCH-5 | — | Accepted / no work | JSON default implemented and confirmed | P2 (informational) | HANDOFF §5.3 DEFER-WATCH-5 |
| DEFER-WATCH-6 | — | 10x-dev (informational) | No action for Phase 1; pagination ADR deferred to Phase 1.5 if needed | P2 | HANDOFF §5.3 DEFER-WATCH-6 |
| DEFER-WATCH-7 | — | sre + 10x-dev | Sprint 4.5 live-smoke ESC-3 measurement; Phase 1.5 streaming ADR trigger if >50k rows / >10MB | P1 (non-blocking; piggybacks on COND-02 live-smoke) | HANDOFF §5.3 DEFER-WATCH-7; dataframes.py:245-268 |
| SPRINT-4.5-LIVE-SMOKE | HIGH risk | 10x-dev | Live end-to-end against canonical gids; see COND-02 | P0 (release blocker) | HANDOFF §5.2; QA §9 condition 1 |
| SPRINT-4.5-ESC-3-LIVE-MEASUREMENT | LOW-MEDIUM risk | sre + 10x-dev | Piggyback on live-smoke; log signal export_format_serialized to SRE dashboard advisory | P1 (non-blocking) | HANDOFF §5.2; QA §8 |
| SPRINT-4.5-ROUTED-ELICITATION | MEDIUM aggregate | 10x-dev | DEF-05 elicitation (Vince); DEF-03 test-add; DEF-02 documentation | P0-P1 per sub-item (DEF-05 P0; DEF-03 P1; DEF-02 P2) | HANDOFF §5.2; QA §9 conditions 2-4 |
| PRC-1 | — | theoros@know | `.know/api.md` FleetQuery section correction (dual-AUTH claim error) | P1 (knowledge hygiene; not release-blocking) | HANDOFF §5.4 PRC-1; ASSESS §6 |
| PRC-2 | — | naxos | Session hygiene triage: stale PARKED sessions session-20260303-* x2 + session-20260427-232025-634f0913 | P2 (housekeeping; not release-blocking) | HANDOFF §5.4 PRC-2 |
| PRC-3 | — | theoros@know | Evaluate promoting workflow + shape files to `.know/` for cross-session reuse via `/land` | P2 (knowledge synthesis; not release-blocking) | HANDOFF §5.4 PRC-3 |
| SS-Q2 filter_incomplete_identity unlogged warning | LOW | 10x-dev | test_exports_helpers.py: add assertion that warning fires in missing-column case | P2 | SCAN SS-Q2; _exports_helpers.py:162-170 |
| SS-Q3 _build_expr pragma:no cover | LOW | 10x-dev | Add regression test: InvalidOperatorError fires on date-op Comparison via PredicateCompiler | P2 | SCAN SS-Q3; compiler.py:125-148 |
| SS-Q5 CacheNotWarmError wrapper path | LOW | 10x-dev | Optional wrapper-level unit test; handler-level coverage exists | P2 | SCAN SS-Q5; exports.py:264-268 |
| SCAR-WS8 exclude_paths discipline gap | — | 10x-dev + theoros | Extend SCAR-WS8 doc to cover exclude_paths synchronization as PAT-route-add checklist step | P1 | ASSESS §6 procession-quality; main.py:374-395; .know/scar-tissue.md:148 |

---

## §6 CR-Q3: Vince Signoff List

> AP-R-4 guard: DEFER-WATCH-1, -2, -3 require explicit pre-release Vince elicitation.
> Silent default acceptance is AP-R-4 violation.

| DEFER-WATCH | Item | Signoff Required | Timing | Rationale |
|-------------|------|-----------------|--------|-----------|
| **DEFER-WATCH-1** | Dedupe winner policy: most-recent-by-modified_at default; falls back to row-order when modified_at absent | **YES — pre-release** | Before live-smoke (COND-02) so canonical pair output can be validated against Vince's expectation | Frame Q4 explicitly flagged this; dedupe policy directly shapes the account rows Vince receives. Default is an engineering choice not yet confirmed by the user whose telos anchors the initiative. [UNATTESTED — DEFER-POST-HANDOFF pending COND-03 execution] |
| **DEFER-WATCH-2** | Column projection: PHASE_1_DEFAULT_COLUMNS set at exports.py:101-109 | **YES — pre-release** | Before or concurrent with live-smoke | Frame Q5 explicitly flagged this as dependent on Vince's tooling. The column set is what Vince's BI consumer will see. An incorrect default requires a breaking change post-ship. [UNATTESTED — DEFER-POST-HANDOFF pending COND-03 execution] |
| **DEFER-WATCH-3** | ACTIVE-only default injection; ACTIVATING caller-elective; OR/NOT suppression semantic (DEF-05) | **YES — pre-release** | Before or concurrent with live-smoke; DEF-05 elicitation is the natural carrier | Frame Q1 surfaced this in Round 1 interview; DEF-05 specifically shows that OR/NOT predicates suppress the default in a potentially surprising way. Vince must confirm whether "ACTIVE-default unless section explicitly addressed" is the intended contract or whether OR/NOT branches should be handled differently. [UNATTESTED — DEFER-POST-HANDOFF pending COND-03 execution] |
| DEFER-WATCH-4 | Inline flag column (identity_complete) with opt-in suppression | NO | Post-release or never | Already adjudicated in interview Q3; P1-C-05 source-of-truth design confirmed. No further Vince input required. |
| DEFER-WATCH-5 | JSON default format | NO | Resolved | Sensible default; implementation confirmed. No elicitation required. |
| DEFER-WATCH-6 | CSV full-body, no streaming | CONDITIONAL — post-release | Post-release if ESC-3 live measurement exceeds thresholds | Acceptable for current scale per QA. If DEFER-WATCH-7 live-smoke reveals >10MB payloads, pagination/streaming ADR is triggered and Vince would be involved in that Phase 1.5 decision. Not a pre-release blocker. |
| DEFER-WATCH-7 | Max result size threshold (50k rows / 10MB trigger) | NO — pre-release; YES — conditional post-release | Sprint 4.5 live-smoke measurement determines if Phase 1.5 ADR fires | The threshold itself is engineering-set. If exceeded, Phase 1.5 streaming ADR triggers and Vince would participate in that scope decision. Not a blocker for Phase 1 release. |

**Summary**: DEFER-WATCH-1, -2, -3 require documented Vince sign-off BEFORE live-smoke executes (COND-03). Shipping without this elicitation risks Vince receiving an output that doesn't match his expected dedupe policy, column set, or section-filter semantics — invalidating the telos verification at 2026-05-11.

---

## §7 CR-Q4: Knowledge Persistence + ADR-Amendment + Legomenon Promotion

### .know/ Corrections Required

**MANDATORY — AP-R-5 guard:**

| Item | Action | Path | Anchor |
|------|--------|------|--------|
| PRC-1: FleetQuery dual-AUTH claim error | Correct `.know/api.md` FleetQuery section: the Phase 0 explore-swarm incorrectly claimed FleetQuery is PAT-only; TDD §15.2 corrected this to true dual-AUTH (PAT + S2S). The correction must be persisted to prevent future rites from repeating the error. | `.know/api.md` — FleetQuery section | HANDOFF §5.4 PRC-1; ASSESS §6 |
| SCAR-WS8 exclude_paths discipline gap | Extend `.know/scar-tissue.md` SCAR-WS8 entry (currently at `:148`) to add: "Adding a new PAT-tagged route tree requires BOTH (a) registration-order before query_router AND (b) addition to jwt_auth_config.exclude_paths. DEF-08 (2026-04-28 review) was the first empirical instance where only (a) was applied." | `.know/scar-tissue.md` | ASSESS §6; SCAN SS-Q4; main.py:374-395 |

**Recommended (not mandatory):**

| Item | Action | Path |
|------|--------|------|
| PRC-3: workflow + shape files | If theoros assesses these as cross-session reusable meta-orchestration patterns (not initiative-specific scaffolding), promote to `.know/` via `/land`. Requires theoros judgment call. | `.sos/wip/frames/project-asana-pipeline-extraction.workflow.md`, `.shape.md` |
| Phase 1 export contract documentation | After Vince elicitation closes DEFER-WATCH-1/2/3, persist the confirmed defaults (dedupe policy, column projection, section-filter semantics) to `.know/api.md` or a new `.know/export-contract.md` for future callers. | `.know/api.md` (new subsection) |

### ADR-Amendments Required

| ADR | Amendment | Trigger |
|-----|-----------|---------|
| ADR-engine-left-preservation-guard.md | No amendment required for Phase 1. Phase 2 (joins active) will require a new ADR or amendment when mechanism (a) becomes non-trivial. Flag for Phase 2 entry. | ASSESS §6 HYBRID verdict; LEFT-PRESERVATION GUARD wrapper at exports.py:236-284 |
| (New ADR recommended) | If Phase 1.5 streaming is triggered by ESC-3 threshold breach, a new ADR is required per TDD §15.3. Not currently triggered. | DEFER-WATCH-7; dataframes.py:245-268 |

### Legomenon Promotion Candidates

**SCAR-WS8 exclude_paths synchronization pattern** — not a fleet-level legomenon candidate at this stage (N=1 empirical instance), but a strong candidate for promotion after a second satellite instance. The discipline is: "Every PAT-tagged route addition to a JWT-middleware-wrapped FastAPI app requires exclude_paths synchronization; structural route registration and auth-middleware exclusion are orthogonal concerns that must both be maintained." This is a general pattern applicable to any service using split PAT/S2S routing with JWT middleware. If theoros finds a second instance in the fleet, promote to a shared scar-tissue legomenon.

No other findings in this procession rise to fleet-level canonization at this time.

---

## §8 Pending-Critic Chain Forward

### Immediate: Release Rite (or 10x-dev if NO-GO)

**This verdict: CONDITIONAL-GO.** The release rite consumes this case file.

Release rite entry conditions:
1. COND-01 closed: DEF-08 verified (pat_router middleware bypass confirmed, or exclude_paths patched + TestClient fixture green). File:line receipt required.
2. COND-02 closed: Sprint 4.5 live-smoke executed against canonical pair; CSV response confirmed; no 401 from PAT path.
3. COND-03 closed: Vince elicitation documented for DEFER-WATCH-1, -2, -3.
4. COND-04 closed: DEF-05 documented in PRD §4.3 or behavioral fix committed.
5. COND-05 tracked (non-blocking): DEF-03 cross-auth test-add or inheritance citation.

If COND-01 surfaces a live PAT-auth failure (401 on /api/v1/exports), the initiative back-routes to 10x-dev for `main.py:381-388` patch before release rite may proceed.

### Ultimate STRONG-Lift: Vince User-Report Verification

- **Event**: Vince user-report verification
- **Deadline**: 2026-05-11
- **Attester**: `theoros@know` per `.sos/wip/frames/project-asana-pipeline-extraction.md:15` telos block
- **Verification method**: user-report (Vince confirms the canonical Reactivation+Outreach CSV ask is fulfilled)
- **AP-TI-2 compliance**: This verification is attested by `theoros@know`, NOT by the review rite. The review rite does NOT claim `verified_realized`. [UNATTESTED — DEFER-POST-HANDOFF: verified_realized_definition.rite_disjoint_attester = theoros@know @ 2026-05-11]

---

## §9 Cross-Rite Handoff Envelope

```yaml
handoff:
  type: validation
  outgoing_rite: review
  incoming_rite: release  # back-routes to 10x-dev if COND-01 surfaces live auth failure
  initiative_slug: project-asana-pipeline-extraction
  phase: 1
  verdict: CONDITIONAL-GO

  telos_pulse_carrier:
    throughline: >
      Vince and every future caller can produce a parameterized account-grain export
      via dual-mount endpoint without custom scripting; Phase 1 verifies against the
      original Reactivation+Outreach CSV ask by 2026-05-11.
    verification_deadline: "2026-05-11"
    rite_disjoint_attester: theoros@know

  artifacts_inventory:
    - path: .ledge/reviews/CASE-pipeline-export-phase1.md
      role: binding case file (this document)
    - path: .ledge/reviews/ASSESS-pipeline-export-phase1.md
      role: S2 pattern-profiler grade table + DEF-08 grading
    - path: .ledge/reviews/SCAN-pipeline-export-phase1.md
      role: S1 structural signals (SS-Q1..Q5)
    - path: .ledge/reviews/QA-pipeline-export-phase1.md
      role: qa-adversary DEF-01..07 + CONDITIONAL-GO baseline
    - path: .ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md
      role: gap inventory + acceptance criteria + anti-pattern guards

  acceptance_criteria_for_release_rite:
    - id: RC-01
      description: COND-01 closed — DEF-08 resolved (file:line receipt required)
      blocker: yes
    - id: RC-02
      description: COND-02 closed — Sprint 4.5 live-smoke successful (canonical pair CSV confirmed)
      blocker: yes
    - id: RC-03
      description: COND-03 closed — Vince elicitation documented for DEFER-WATCH-1/2/3
      blocker: yes
    - id: RC-04
      description: COND-04 closed — DEF-05 documented in PRD §4.3 or behavioral fix committed
      blocker: yes
    - id: RC-05
      description: COND-05 tracked — DEF-03 cross-auth test-add or inheritance citation
      blocker: no

  back_route_trigger:
    condition: COND-01 surfaces live PAT-auth failure (401 on /api/v1/exports)
    incoming_rite_on_back_route: 10x-dev
    work_scope: >
      Add /api/v1/exports/* to jwt_auth_config.exclude_paths at main.py:381-388;
      add TestClient PAT fixture confirming HTTP 200 on /api/v1/exports POST;
      re-run full suite (12422+); re-handoff to release rite.
```

---

## §10 Evidence Trail

> Every verdict claim traced to file:line or defect ID per AP-TI-1.
> AP-TI-2 compliance: verified_realized is NOT claimed by the review rite.

| Claim | Source | File:Line / Defect ID | Grade |
|-------|--------|-----------------------|-------|
| Overall health grade = C | ASSESS §3 weakest-link; Security category = C | ASSESS §3 grade table; main.py:374-395 (DEF-08) | HIGH structural; MODERATE runtime |
| Security = C | DEF-08 pattern-profiler-discovered; jwt_auth_config.exclude_paths confirmed absent | main.py:381-388 (direct read) | HIGH (structural gap confirmed); MODERATE (runtime failure mode inferred) |
| DEF-08 severity = HIGH | ASSESS §4 DEF-08 grading block | ASSESS §4; main.py:381-388; exports.py:221-228 | HIGH structural; MODERATE runtime per self-ref-evidence-grade-rule |
| DEF-01 = Medium (retained) | QA §3; ASSESS §4 re-grade | QA-pipeline-export-phase1.md §3 DEF-01; test_exports_handler.py:255-294 | HIGH |
| DEF-05 = Medium (retained) | QA §3; ASSESS §4 re-grade | QA-pipeline-export-phase1.md §3 DEF-05; _exports_helpers.py:228-251 | HIGH |
| DEF-02/03/04/06/07 = Low (retained) | QA §3; ASSESS §4 re-grade | QA-pipeline-export-phase1.md §3 respective findings | HIGH (structural) |
| AP-R-3(a) identity_complete behavioral test | SCAN AP-R-3 spot-check | test_exports_helpers.py:65-76 | HIGH |
| AP-R-3(b) dual-mount contract tests | SCAN AP-R-3 spot-check | test_exports_contract.py:154-186 | HIGH |
| AP-R-3(c) LEFT-PRESERVATION GUARD observable | SCAN AP-R-3 spot-check | test_exports_handler.py:75-109 | HIGH |
| P1-C-04 forbidden files unmodified | QA §5 P-9; 12422 tests passing | QA-pipeline-export-phase1.md §5; HANDOFF §3 test_status | HIGH |
| Route registration order correct | SCAN SS-Q4; inline comment | main.py:432-437 | HIGH |
| CacheNotWarmError wrapper path untested at wrapper level | SCAN SS-Q5 | exports.py:264-268; test_exports_handler.py:53-109 | HIGH (gap confirmed); MEDIUM (risk level) |
| DEFER-WATCH-1/2/3 require pre-release Vince signoff | HANDOFF §5.3 AP-R-4 guard | HANDOFF §5.3 DEFER-WATCH-1/2/3 | [UNATTESTED — DEFER-POST-HANDOFF: signoff event is future] |
| PRC-1 FleetQuery error must correct .know/api.md | HANDOFF §5.4; ASSESS §6 | HANDOFF §5.4 PRC-1 | HIGH (factual error documented) |
| SCAR-WS8 exclude_paths gap must extend .know/scar-tissue.md | ASSESS §6 procession-quality; main.py:374-395 | main.py:374-395; .know/scar-tissue.md:148 | HIGH structural |
| Procession quality = B | ASSESS §6 | ASSESS-pipeline-export-phase1.md §6 | MODERATE (self-ref per evidence-grade-rule) |
| Vince user-report attested by theoros@know NOT review rite | AP-TI-2 compliance | frame.telos.verified_realized_definition; HANDOFF §8 | [UNATTESTED — DEFER-POST-HANDOFF: 2026-05-11 theoros@know] |

---

## Health Report Card (Final)

| Category | Grade | Key Finding |
|----------|-------|-------------|
| Correctness | B | DEF-05 (Medium: OR/NOT default suppression broadens result set); DEF-06 (Low: empty section IN); Op ESC-1 CONTAINED |
| Security | C | DEF-08 (HIGH): /api/v1/exports absent from jwt_auth_config.exclude_paths — may block PAT user path |
| Maintainability | B | exports.py 569 LOC (justified pipeline structure); export_handler ~188 LOC; attach_identity_complete all-False silent fallback |
| Performance | A | No new dependencies; lazy import via sys.modules cache; ESC-3 synthetic verified |
| Observability | A | LEFT-PRESERVATION GUARD log verified (test_exports_handler.py:75-109); ESC-3 size emit confirmed (dataframes.py:245-268) |
| Test-Coverage | B | 87 tests / 1.08 ratio; CacheNotWarmError wrapper gap (exports.py:264-268); DEF-01 canonical pair gap |
| **Overall** | **C** | **Security DEF-08 is the weakest-link load-bearing risk. Weakest-link conservative per ASSESS §3 P-08. Upgrades to B when DEF-08 closes.** |

---

## Metrics Dashboard

| Metric | Value |
|--------|-------|
| Files scanned | 10 (6 created, 4 modified) |
| Total findings | 9 scan signals + 8 defects (1 HIGH + 2 MEDIUM + 5 LOW) |
| Critical defects | 0 |
| High defects | 1 (DEF-08, pattern-profiler-discovered) |
| Medium defects | 2 (DEF-01, DEF-05) |
| Low defects | 5 (DEF-02, DEF-03, DEF-04, DEF-06, DEF-07) |
| Test-to-source LOC ratio | 1.08 (87 tests; 1106 test LOC : 1023 source LOC) |
| Full suite | 12422 passed / 2 skipped / 0 failed |
| New external dependencies | 0 |
| P1-C-04 forbidden files modified | 0 |
| Review complexity | FULL |

---

*Review mode: FULL | Generated by review rite case-reporter | 2026-04-28*
*AP-R-1 satisfied: DEF-08 breaks rubber-stamp; verdict is not qa-adversary's CONDITIONAL-GO re-issued.*
*AP-R-4 satisfied: DEFER-WATCH-1/2/3 Vince-signoff requirements explicit in §6 and COND-03.*
*AP-R-5 satisfied: .know/api.md PRC-1 correction recommended in §7 (mandatory).*
*AP-TI-1 satisfied: all verdict claims carry file:line, defect ID, or [UNATTESTED — DEFER-POST-HANDOFF] tag.*
*AP-TI-2 satisfied: verified_realized attested by theoros@know @ 2026-05-11, NOT by review rite.*
