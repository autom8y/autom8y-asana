---
type: handoff
status: accepted
handoff_type: execution
source_rite: review
target_rite: 10x-dev
created: 2026-04-28
initiative: project-asana-pipeline-extraction
phase: 1.1-remediation
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
incoming_session_inception_anchor: .ledge/reviews/CASE-pipeline-export-phase1.md#§9
remediation_mandate: patch DEF-08 (PAT auth middleware exclusion) + DEF-05 (PRD documentation OR behavioral fix)
verdict_authority_upstream: review_rite_case_reporter (already issued CONDITIONAL-GO)
ultimate_lift_event: Vince user-report verification at 2026-05-11 (attester theoros@know per frame.telos)
---

# HANDOFF — review → 10x-dev (Phase 1.1 Remediation Sprint)

## §1 Telos Pulse Reroot (verbatim from frame.md:15)

> "A coworker's ad-hoc request to extract actionable account lists from Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana service: there is no first-class BI export surface, and any response today would be a one-off script with zero reusability. This initiative transitions from observation (Iris snapshot) to repeatable, account-grain, CSV-capable data extraction codified in the service's dataframe layer."

**Phase 1.1 status**: review rite issued CONDITIONAL-GO at `.ledge/reviews/CASE-pipeline-export-phase1.md`. 10x-dev rite consumes the 2 P0 blockers within its scope (DEF-08 + DEF-05) and remediates. After this sprint closes, work returns to release rite for Sprint 4.5 live-smoke + Vince elicitation per the original case-reporter routing.

## §2 Inception Context for Incoming 10x-dev Potnia

| Tier | Path | Why |
|------|------|-----|
| 1 | `.ledge/reviews/CASE-pipeline-export-phase1.md` | Verdict carrier — §4 binding verdict, §5 gap-routing, §9 cross-rite handoff envelope |
| 2 | `.ledge/reviews/ASSESS-pipeline-export-phase1.md` | DEF-08 grade rationale (HIGH severity, file:line evidence) |
| 3 | `.ledge/reviews/SCAN-pipeline-export-phase1.md` | SS-Q4 structural finding (DEF-08 origin) + coverage gap on exports.py:264-268 |
| 4 | `.ledge/handoffs/HANDOFF-10xdev-to-review-2026-04-28.md` | Outgoing 10x-dev → review handoff (for context — what review consumed) |
| 5 | `.sos/wip/frames/project-asana-pipeline-extraction.md` | Telos block |
| 6 | `.sos/wip/inquisitions/phase1-orchestration-touchstones.md` | Existing 10x-dev orchestration discipline (inherits, no re-author needed) |

## §3 Remediation Items (REQUIRED PER ITEM: acceptance_criteria)

### Item R-1 — DEF-08 PAT Auth Middleware Exclusion Patch

```yaml
remediation_item:
  id: R-1
  origin_defect: DEF-08
  severity: HIGH (per S2 ASSESS)
  source_finding:
    artifact: .ledge/reviews/SCAN-pipeline-export-phase1.md (SS-Q4)
    file_line_evidence: src/autom8_asana/api/main.py:381-388
    description: |
      `/api/v1/exports` is absent from `jwt_auth_config.exclude_paths`.
      Every other PAT-tagged route tree (dataframes, tasks, projects, sections,
      users, workspaces, offers) is explicitly excluded. Without exclusion, the
      JWT middleware may reject Vince's PAT-authenticated requests before
      `pat_router` DI fires — silent 401 on the load-bearing user path.
  acceptance_criteria:
    - id: AC-R1-1
      criterion: "`/api/v1/exports` is added to `jwt_auth_config.exclude_paths` at main.py:381-388"
      verification: file_line_diff_inspection
      blocking: yes
    - id: AC-R1-2
      criterion: "Path is added in alphabetical or registration order consistent with neighboring entries"
      verification: code_review
      blocking: no
    - id: AC-R1-3
      criterion: "Unit or integration test added that exercises PAT-authenticated request to `/api/v1/exports/{entity_type}` and asserts 200 (NOT 401) for valid PAT"
      verification: pytest_pass
      blocking: yes
    - id: AC-R1-4
      criterion: "Full unit suite still passes (12,422+ tests)"
      verification: pytest_pass
      blocking: yes
    - id: AC-R1-5
      criterion: "DEF-08 marked RESOLVED in remediation summary with file:line citation"
      verification: artifact_inspection
      blocking: yes
  out_of_scope:
    - JWT middleware itself (autom8y_api_middleware) — exclude_paths is the user-side surface
    - Other route trees not currently broken
    - Phase 2 work
  estimated_effort: ~20 LOC (patch + test); ~30 minutes focused
```

### Item R-2 — DEF-05 Activity-State Default-Suppression Documentation/Fix

```yaml
remediation_item:
  id: R-2
  origin_defect: DEF-05
  severity: MEDIUM (per S2 ASSESS — no escalation; deterministic, no silent data loss)
  source_finding:
    artifact: .ledge/reviews/QA-pipeline-export-phase1.md (DEF-05)
    description: |
      When the caller's predicate has section-IN clauses inside OR/NOT branches,
      the ACTIVE-only default is NOT applied (correct behavior per current logic),
      but this semantically BROADENS the result set in ways the caller may not
      anticipate. Result set may include INACTIVE/IGNORED rows when caller
      probably expected ACTIVE-only as the implicit default.
  resolution_choice: "documentation OR behavioral fix" (case-reporter accepted either)
  recommended: documentation (faster, no behavioral change risk during remediation)
  acceptance_criteria:
    - id: AC-R2-1
      criterion: |
        PRD §4 (Activity-State Parameterization) includes explicit subsection
        documenting OR/NOT branch behavior. Specifically: when caller-supplied
        predicate contains any section-IN clause anywhere in the AST (including
        OR/NOT branches), the server-side ACTIVE-only default is NOT injected,
        and the caller's full predicate is honored as-given.
      verification: PRD_inspection
      blocking: yes
    - id: AC-R2-2
      criterion: |
        PRD acceptance criterion AC-8 is amended (or a new AC-8b added) to assert
        the documented OR/NOT behavior explicitly. Existing AC-8 test still passes.
      verification: PRD_inspection + pytest_pass
      blocking: yes
    - id: AC-R2-3
      criterion: |
        DEF-05 marked RESOLVED in remediation summary with PRD section citation.
      verification: artifact_inspection
      blocking: yes
  out_of_scope:
    - Behavioral change to OR/NOT branch handling (current behavior is correct;
      this is a documentation gap, not a logic gap)
    - Sprint 2 architect TDD revision (architect TDD already references PRD §4
      by reference; PRD update flows through transitively)
  estimated_effort: ~10 lines of PRD addition; ~10 minutes focused
```

## §4 Out-of-Scope for This Remediation (binding)

The following review-rite conditions are NOT in 10x-dev's scope here — they route to other rites or to direct user elicitation:

```yaml
out_of_10xdev_scope:
  - id: COND-02
    item: Sprint 4.5 live-smoke against Reactivation+Outreach project pair
    owner: release_rite (or 10x-dev test-add as alternative)
    rationale: Requires warm Asana cache + canonical project access; closer to release execution
  - id: COND-03
    item: Vince elicitation for DEFER-WATCH-1/-2/-3 (dedupe winner, column projection, ACTIVATING default)
    owner: direct_user_elicitation
    rationale: Stakeholder decision, not engineering remediation
  - id: COND-05
    item: DEF-03 cross-auth runtime probe test-add OR inheritance citation
    owner: hygiene_rite (P1 non-blocking)
    rationale: Not blocking release; can run in parallel hygiene cycle
  - id: PRC-1_known_correction
    item: .know/api.md FleetQuery dual-AUTH correction
    owner: hygiene_rite OR theoros (/know skill)
    rationale: Knowledge persistence, not code change
  - id: SCAR-WS8_extension
    item: .know/scar-tissue.md SCAR-WS8 extension (exclude_paths sync requirement)
    owner: hygiene_rite OR theoros (/know skill)
    rationale: Knowledge persistence, not code change. Note: this scar-tissue
      entry is INDIRECTLY related to R-1 (DEF-08 is exactly the kind of bug
      this scar would have caught); recommend authoring after R-1 lands so
      the scar reflects the live remediation event.
```

## §5 Sprint Topology for Remediation

```yaml
sprint_topology:
  - sprint: 1
    name: remediation_sprint
    specialist: principal-engineer
    scope: [R-1, R-2]
    rationale: |
      Both items are small. R-1 is ~20 LOC code+test patch. R-2 is documentation
      update. Single principal-engineer sprint covers both efficiently. No
      architect intervention needed — neither item changes the contract or seam
      locations beyond what's already in TDD/ADR.
    exit_artifacts:
      - src/autom8_asana/api/main.py (R-1 patch)
      - tests/unit/api/test_exports_handler.py OR new test file (R-1 test)
      - .ledge/specs/PRD-pipeline-export-phase1.md (R-2 documentation update)
      - .ledge/reviews/REMEDIATION-pipeline-export-phase1.md (sprint summary)
  - sprint: 2
    name: PT-final-remediation-gate
    type: checkpoint
    purpose: verify both AC-R1-1..5 + AC-R2-1..3 satisfied; verify EC-05 still holds (no P1-C-04 forbidden file modified except main.py which is permitted)
```

## §6 Acceptance Criteria for Remediation Closure

```yaml
remediation_acceptance:
  - all R-1 acceptance criteria (AC-R1-1..5) satisfied
  - all R-2 acceptance criteria (AC-R2-1..3) satisfied
  - REMEDIATION sprint summary artifact authored at .ledge/reviews/REMEDIATION-pipeline-export-phase1.md
  - case-reporter's CASE §4 verdict block updated (or annotated) with COND-01 + COND-04 marked RESOLVED
  - cross-rite handoff envelope authored to next rite (release for Sprint 4.5 live-smoke + Vince elicitation, OR direct user prompt if user wants to elicit Vince before release)
exit_signal: REMEDIATION artifact + git diff confirming AC-R1-1 + PRD diff confirming AC-R2-1
```

## §7 Anti-Pattern Guards (specific to this remediation)

```yaml
anti_patterns:
  - id: AP-RM-1
    pattern: scope creep into other CONDITIONAL-GO conditions
    detection: principal-engineer attempts to land Sprint 4.5 live-smoke OR Vince elicitation OR .know/ corrections
    action: STOP — those are out-of-scope per §4; route via separate handoff
  - id: AP-RM-2
    pattern: behavioral fix on R-2 instead of documentation
    detection: code change to _exports_helpers.py activity-state default injection
    action: WARN — case-reporter accepted documentation; behavioral change adds risk during remediation; require explicit justification
  - id: AP-RM-3
    pattern: skip the regression test on R-1
    detection: AC-R1-3 left unsatisfied
    action: REMEDIATE — without the test, the next regression of this exact pattern (new PAT route forgetting exclude_paths) goes undetected
  - id: AP-RM-4
    pattern: P1-C-04 forbidden file violation
    detection: git diff shows modifications to query/engine.py, query/join.py, query/compiler.py, cascade_resolver.py, cascade_validator.py, reconciliation/section_registry.py
    action: REMEDIATE — main.py is permitted (it's not in P1-C-04); other files remain forbidden
  - id: AP-RM-5
    pattern: DEF-08 patch broadens auth surface beyond minimum
    detection: principal-engineer adds entries beyond `/api/v1/exports` OR refactors exclude_paths logic
    action: WARN — minimum-viable patch is the goal; broader changes invite new bugs
```

## §8 Pending-Critic Chain (post-remediation)

```yaml
critic_chain:
  immediate: 10x-dev qa-adversary (Sprint 2 — re-runs DEF-08 + DEF-05 attack vectors against the patch)
    OR streamlined: principal-engineer self-attestation with CKP gate (acceptable for remediation of small surface)
  next: release rite (consumes REMEDIATION artifact + original CASE verdict; addresses COND-02 + COND-03)
  ultimate_strong_lift:
    event: Vince user-report verification
    deadline: 2026-05-11
    attester: theoros@know per frame.telos.verified_realized_definition.rite_disjoint_attester
```

## §9 Telos Pulse Carrier (workflow §4 schema)

```yaml
telos_pulse_carrier:
  outgoing_rite: review
  incoming_rite: 10x-dev
  initiative_slug: project-asana-pipeline-extraction
  phase: 1.1-remediation
  throughline_one_liner: |
    Vince and every future caller can produce a parameterized account-grain export
    via dual-mount endpoint without custom scripting; Phase 1 verifies against the
    original Reactivation+Outreach CSV ask by 2026-05-11. Phase 1.1 remediation
    closes the rite-disjoint critique findings (DEF-08 PAT auth + DEF-05 OR/NOT
    semantic doc) without expanding scope.
  verification_deadline: "2026-05-11"
  pulse_carrier_authoring_specialist: review_rite_case_reporter (via this handoff artifact authored by main thread)
  pulse_reroot_ritual_for_incoming_potnia: |
    Before dispatching principal-engineer, the 10x-dev Potnia MUST:
    1. Read this telos_pulse_carrier block in full
    2. Restate the throughline in the dispatch prompt opening (verbatim, not paraphrased)
    3. Cite this handoff artifact path:line as the inception anchor for remediation
    4. Cite CASE §4 verdict + §5 gap-routing for the upstream rationale
    5. Stamp acknowledgement in opening response
```

## §10 Closing Note

This is a **small-scope remediation handoff** — two clean items (R-1 code patch + R-2 PRD doc), each with explicit acceptance criteria. It does NOT re-open Phase 1's full sprint topology. After this remediation closes, the next cross-rite handoff goes to release rite (or direct user for Vince elicitation), per case-reporter's routing.

The rite-disjoint critique discipline that surfaced DEF-08 is the load-bearing legitimacy of this remediation — without the review rite's AP-R-1 anti-rubber-stamp guard catching it, this gap would have shipped silent into release and broken Vince's primary user path. Honor the discipline by closing the remediation cleanly.
