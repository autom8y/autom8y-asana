---
type: handoff
status: accepted
handoff_type: validation
source_rite: 10x-dev
target_rite: release
created: 2026-04-28
initiative: project-asana-pipeline-extraction
phase: Sprint-4.5-live-smoke
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
incoming_session_inception_anchor: .ledge/reviews/CASE-pipeline-export-phase1.md#§9 + .ledge/reviews/REMEDIATION-pipeline-export-phase1.md
release_mandate: Sprint 4.5 live-smoke + production deploy + Vince user-report verification path
verdict_authority_upstream: review_rite_case_reporter (CONDITIONAL-GO, 2 of 5 conditions RESOLVED in Phase 1.1)
ultimate_lift_event: Vince user-report verification at 2026-05-11 (attester theoros@know per frame.telos)
---

# HANDOFF — 10x-dev → release (Sprint 4.5 Live-Smoke + Production Deploy)

## §1 Telos Pulse Reroot (verbatim from frame.md:15)

> "A coworker's ad-hoc request to extract actionable account lists from Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana service: there is no first-class BI export surface, and any response today would be a one-off script with zero reusability. This initiative transitions from observation (Iris snapshot) to repeatable, account-grain, CSV-capable data extraction codified in the service's dataframe layer."

**Phase status at handoff**: Phase 1 BUILD COMPLETE + Phase 1.1 REMEDIATION COMPLETE. Code shipped. Tests green (12,331+ passed). Two of five CONDITIONAL-GO conditions RESOLVED. Three remaining route through release rite (live-smoke + deploy) or in parallel (Vince elicitation, hygiene). The release rite's mandate: validate live behavior, deploy, and stand watch on Vince's user-report verification path.

## §2 Inception Context for Incoming Release Potnia

| Tier | Path | Why |
|------|------|-----|
| 1 | `.ledge/reviews/CASE-pipeline-export-phase1.md` | Verdict carrier — §4 binding CONDITIONAL-GO, §5 gap-routing, §9 cross-rite handoff envelope |
| 2 | `.ledge/reviews/REMEDIATION-pipeline-export-phase1.md` | Phase 1.1 remediation closure evidence — COND-01 + COND-04 RESOLVED |
| 3 | `.ledge/handoffs/HANDOFF-review-to-10xdev-2026-04-28.md` | Outgoing review → 10x-dev handoff (context — what was remediated) |
| 4 | `.ledge/reviews/QA-pipeline-export-phase1.md` | qa-adversary baseline + 7 original defects |
| 5 | `.ledge/reviews/SCAN-pipeline-export-phase1.md` | signal-sifter scan + DEF-08 origin |
| 6 | `.ledge/reviews/ASSESS-pipeline-export-phase1.md` | DEF-08 grade rationale (HIGH) |
| 7 | `.ledge/specs/PRD-pipeline-export-phase1.md` | Phase 1 contract (with §4.4 OR/NOT update + AC-8b from R-2) |
| 8 | `.ledge/specs/TDD-pipeline-export-phase1.md` | Component design |
| 9 | `.ledge/decisions/ADR-engine-left-preservation-guard.md` | HYBRID mechanism a+b |
| 10 | `.sos/wip/frames/project-asana-pipeline-extraction.md` | Telos block |

## §3 Validation Scope (REQUIRED PER ITEM)

### Item V-1 — Sprint 4.5 Live-Smoke (COND-02)

```yaml
validation_item:
  id: V-1
  origin_condition: COND-02
  blocker_for_release: yes (P0)
  source_finding:
    artifact: .ledge/reviews/CASE-pipeline-export-phase1.md §4 conditions
    description: |
      Synthetic fixture validated 78 rows / 7,159 bytes against (office_phone, vertical)
      dedupe with identity_complete column. Live-smoke against canonical Reactivation +
      Outreach project pair was deferred (qa-adversary unable to execute live during QA
      session). Release rite must execute live-smoke before deploy to verify the
      synthetic-to-live behavioral parity.
  validation_scope:
    - Warm Asana cache (or trigger cache warming)
    - Invoke /api/v1/exports/process with payload:
        entity_type: process
        project_gids: [1201265144487549, 1201753128450029]  # Reactivation + Outreach
        predicate: section IN ACTIVE-states (or omit for default)
        format: csv
        options.include_incomplete_identity: true
    - Verify response: account-grain CSV with identity_complete column
    - Capture row_count + serialized_bytes for ESC-3 live measurement (DEFER-WATCH-7 disposition)
    - Cross-mount: invoke same payload via /v1/exports/process with ServiceJWT to confirm dual-mount
  acceptance_criteria:
    - id: AC-V1-1
      criterion: "Live PAT request to /api/v1/exports/process returns 200 (NOT 401 — verifies R-1 patch in production)"
      verification: HTTP_response_inspection
      blocking: yes
    - id: AC-V1-2
      criterion: "Live S2S request to /v1/exports/process returns 200 with valid ServiceJWT"
      verification: HTTP_response_inspection
      blocking: yes
    - id: AC-V1-3
      criterion: "CSV body contains identity_complete column on every row; null-key rows surface (NOT silently dropped)"
      verification: CSV_inspection
      blocking: yes
    - id: AC-V1-4
      criterion: "Account-grain dedupe by (office_phone, vertical) produces row count consistent with prior Iris analytical pull"
      verification: row_count_comparison
      blocking: yes
    - id: AC-V1-5
      criterion: "ESC-3 live measurement captured: row_count + serialized_bytes; if >50k rows OR >10MB → trigger Phase 1.5 streaming ADR"
      verification: log_inspection (export_format_serialized event)
      blocking: no (informational; threshold trigger)
  estimated_effort: ~30-60 minutes (cache warm + curl invocations + CSV diff)
```

### Item V-2 — Production Deploy

```yaml
validation_item:
  id: V-2
  origin_condition: deploy_phase
  blocker_for_release: yes (P0)
  validation_scope:
    - PR creation (full diff includes Phase 1 build + Phase 1.1 remediation)
    - CI pipeline green (pytest + linting + type-check)
    - Code review approval (rite-disjoint reviewer if available)
    - Deploy to production
  acceptance_criteria:
    - id: AC-V2-1
      criterion: "PR opened with full Phase 1 + Phase 1.1 diff; description cites CASE verdict + REMEDIATION closure"
      verification: PR_URL
      blocking: yes
    - id: AC-V2-2
      criterion: "CI pipeline green (all checks pass)"
      verification: gh_pr_status
      blocking: yes
    - id: AC-V2-3
      criterion: "Production deploy completes successfully"
      verification: deploy_log
      blocking: yes
    - id: AC-V2-4
      criterion: "Post-deploy /api/v1/exports/process smoke against production endpoint returns 200"
      verification: HTTP_response_inspection
      blocking: yes
  estimated_effort: ~1-2 hours (depends on CI cycle time + deploy gate processes)
```

### Item V-3 — Vince User-Report Verification Path (ultimate STRONG-lift)

```yaml
validation_item:
  id: V-3
  origin_condition: telos.verified_realized_definition
  blocker_for_release: no (post-deploy gate; ultimate STRONG-lift event)
  validation_scope:
    - Notify Vince that endpoint is live and ready
    - Provide curl/example invocation for Reactivation + Outreach CSV
    - Vince invokes endpoint, retrieves CSV, reports satisfaction
    - theoros@know (rite-disjoint attester per frame.telos) confirms verified_realized
  acceptance_criteria:
    - id: AC-V3-1
      criterion: "Vince retrieves CSV via the new /api/v1/exports/process endpoint with no custom scripting"
      verification: user_report
      blocking: yes (telos verification)
    - id: AC-V3-2
      criterion: "CSV contents satisfy Vince's outreach use case (account-grain, contact info present)"
      verification: user_report
      blocking: yes
    - id: AC-V3-3
      criterion: "theoros@know attests verified_realized status in frame.telos.attestation_status"
      verification: theoros_invocation
      blocking: yes (closes telos loop)
  deadline: 2026-05-11
  attester: theoros@know per frame.telos.verified_realized_definition.rite_disjoint_attester
```

## §4 Out-of-Scope for Release Rite (route to other rites)

```yaml
out_of_release_scope:
  - id: COND-03
    item: Vince elicitation for DEFER-WATCH-1 (dedupe winner), DEFER-WATCH-2 (column projection), DEFER-WATCH-3 (ACTIVATING default)
    owner: direct_user_elicitation (parallel track; can land before OR after V-1 live-smoke)
    rationale: |
      Stakeholder decision, not engineering remediation. CASE §6 + handoff §4 routed
      to direct user. Recommend eliciting BEFORE V-1 live-smoke if Vince has strong
      opinions; otherwise document as "pending elicitation; flagged defaults will be
      adjusted post-Vince-feedback if needed".
  - id: COND-05
    item: DEF-03 cross-auth runtime probe test-add OR inheritance citation
    owner: hygiene_rite (P1 non-blocking)
    rationale: Not blocking deploy; can run in parallel hygiene cycle.
  - id: PRC-1
    item: .know/api.md FleetQuery dual-AUTH correction
    owner: hygiene_rite OR theoros (/know skill)
    rationale: Knowledge persistence, not deploy gate.
  - id: SCAR-WS8
    item: .know/scar-tissue.md SCAR-WS8 extension (exclude_paths sync requirement post-R-1)
    owner: hygiene_rite OR theoros
    rationale: |
      Knowledge persistence. Now that R-1 has landed, the SCAR-WS8 entry can be
      authored with the live remediation event as its primary anchor — exactly the
      class of bug the scar would have caught at PRD-time.
  - id: parked_sessions
    item: 2 stale PARKED sessions from March 2026
    owner: naxos triage when convenient
    rationale: cross-session isolation maintained throughout this initiative.
```

## §5 Sprint Topology for Release

```yaml
sprint_topology:
  - sprint: 1
    name: live_smoke_sprint
    specialists: [pipeline-monitor or release-executor]
    scope: [V-1]
    rationale: Live invocation + measurement; small focused work
    exit_artifacts:
      - .ledge/reviews/LIVE-SMOKE-pipeline-export.md (V-1 evidence)
  - sprint: 2
    name: deploy_sprint
    specialists: [release-planner, release-executor, pipeline-monitor]
    scope: [V-2]
    rationale: PR + CI + deploy + post-deploy smoke
    exit_artifacts:
      - PR URL on GitHub
      - Deploy log evidence
  - sprint: 3
    name: vince_verification
    type: customer_engagement (NOT specialist sprint)
    scope: [V-3]
    rationale: User-report verification; release rite stands watch
    exit_artifacts:
      - frame.telos.attestation_status.verified_realized: ATTESTED (via theoros@know)
```

## §6 Anti-Pattern Guards

```yaml
anti_patterns:
  - id: AP-RL-1
    pattern: deploy without live-smoke validation
    detection: V-2 sprint advances without V-1 evidence artifact
    action: HALT — V-1 is hard gate before V-2; validates R-1 patch in production behavior
  - id: AP-RL-2
    pattern: skip Vince elicitation and deploy with flagged defaults
    detection: V-2 closes but COND-03 remains open without "deferred-with-explicit-flag" notation
    action: WARN — DEFER-WATCH-1/-2/-3 are AP-R-4 items per review rite; recommend eliciting before V-3
  - id: AP-RL-3
    pattern: post-deploy regression on dual-mount
    detection: AC-V2-4 production smoke fails OR returns 401 from PAT route
    action: REMEDIATE — back-route to 10x-dev with specific failure mode; do NOT silently retry
  - id: AP-RL-4
    pattern: ESC-3 live measurement skipped
    detection: V-1 closes without log_inspection evidence on row_count + serialized_bytes
    action: REMEDIATE — ESC-3 is the load-bearing measurement that closes DEFER-WATCH-7 disposition; required for Phase 1.5 trigger decision
  - id: AP-RL-5
    pattern: Vince notified before live-smoke validates the endpoint
    detection: V-3 notification fires before V-1 evidence artifact exists
    action: HALT — never advertise an unsmoked endpoint to a stakeholder; user-report verification depends on functional path
```

## §7 Pending-Critic Chain

```yaml
critic_chain:
  immediate: pipeline-monitor (V-1 validation in production via gh CLI / smoke probes)
  next_rite_if_failure: 10x-dev (REMEDIATE specific failure mode with delta-scope sprint)
  parallel_tracks:
    - hygiene_rite (COND-05 + PRC-1 + SCAR-WS8 — knowledge persistence and test hygiene)
    - direct_user (COND-03 — Vince DEFER-WATCH elicitation)
  ultimate_strong_lift:
    event: Vince user-report verification (V-3)
    deadline: 2026-05-11
    attester: theoros@know per frame.telos.verified_realized_definition.rite_disjoint_attester
    verification_method: user-report
```

## §8 Telos Pulse Carrier (workflow §4 schema)

```yaml
telos_pulse_carrier:
  outgoing_rite: 10x-dev
  incoming_rite: release
  initiative_slug: project-asana-pipeline-extraction
  phase: Sprint-4.5-live-smoke + deploy + verification
  throughline_one_liner: |
    Phase 1 BUILD + Phase 1.1 REMEDIATION CLOSED. Code shipped, tests green, two
    rite-disjoint findings RESOLVED. Release rite consumes REMEDIATION evidence
    + CASE verdict, runs live-smoke + deploy, stands watch on Vince's user-report
    verification by 2026-05-11 (theoros@know attests).
  verification_deadline: "2026-05-11"
  pulse_carrier_authoring_specialist: 10x-dev (via this handoff artifact)
  pulse_reroot_ritual_for_incoming_potnia: |
    Before dispatching pipeline-monitor or release-executor, the release rite Potnia MUST:
    1. Read this telos_pulse_carrier block in full
    2. Restate the throughline in dispatch prompt opening (verbatim, not paraphrased)
    3. Cite this handoff artifact path:line + REMEDIATION + CASE as inception anchors
    4. Acknowledge V-1 → V-2 → V-3 sprint dependency (V-1 is hard gate before V-2)
    5. Stamp acknowledgement in opening response
```

## §9 Closing Note

This is a **validation handoff** — Phase 1 + Phase 1.1 engineering work is complete. Release rite's job is to (a) prove the live behavior matches the synthetic, (b) ship to production, (c) stand watch as Vince exercises the endpoint. The rite-disjoint critique that surfaced DEF-08 (PAT auth middleware exclusion) was load-bearing — without it, V-1 would have failed silently and broken the throughline at Vince's first invocation. Honor the discipline by closing live-smoke cleanly before deploy.

The throughline pulse is intact and ready for the release rite Potnia to inherit.
