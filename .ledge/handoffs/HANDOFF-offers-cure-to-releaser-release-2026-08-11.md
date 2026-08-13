---
artifact_id: HANDOFF-offers-cure-to-releaser-release-2026-08-11
schema_version: "1.0"
type: handoff
status: in_progress  # HANDOFF-schema enum (HANDOFF-009); FIRED at authoring — operator cross-rite grant
shelf_status: draft  # .ledge lifecycle companion field (the two schemas' status enums are disjoint)
source_rite: 10x-dev
target_rite: releaser
handoff_type: execution
priority: critical
blocking: false
initiative: offers-freshness-axis-contract (formerly offers-false-staleness-cure) — S5 LAND + REALIZE
created_at: "2026-08-11T16:45:00Z"
session_id: session-20260811-115247-a1ccd942
sprint_id: sprint-20260811-offers-false-staleness-cure-wave1
source_artifacts:
  - .ledge/handoffs/HANDOFF-offers-cure-to-operator-s5-gate-2026-08-11.md
  - .ledge/decisions/RULING-operator-s5-gate-interview-2026-08-11.md
  - .sos/wip/CERT-offers-cure-s4-2026-08-11.md
  - .sos/wip/QA-s3-offers-cure-2026-08-11.md
  - .sos/wip/RUNBOOK-image-rollback-offers-cure-2026-08-11.md
evidence_grade: strong
authority: >-
  Operator cross-rite grant 2026-08-11 (/cross-rite-handoff --to=releaser):
  user-grade execution authority to pantheon + borrowed seats, all repos.
  BOUNDED BY the operator's own inscribed rulings, which this grant does NOT
  override: R-5/D-6 (FIX-N merges ≥2026-08-12T09:19:45Z AND C-NULL deployed) ·
  R-2 strict REALIZE bar · R-4/R-8 trigger regimes · L4 keep-warm REFUSED
  (the control arm is never synthetically warmed) · rollback per the runbook.
items:
  - id: REL-1
    summary: Merge autom8y#1516 (consumer-gate cancelled-supersede retry guard) — removes the publish race from 4.14.0's path.
    priority: critical
    acceptance_criteria:
      - "#1516 merged; its CI green"
  - id: REL-2
    summary: Merge autom8y#1506 (K-SDK content-axis, autom8y-core 4.14.0) — merge auto-triggers the publish.
    priority: critical
    dependencies: [REL-1]
    acceptance_criteria:
      - "#1506 merged; publish run green end-to-end"
      - "CodeArtifact serves autom8y-core 4.14.0 (describe-package-version receipt)"
  - id: REL-3
    summary: >-
      K-ASR leg lands: re-merge origin/main into fix/asr-offers-watermark-repoint
      (clean diff post-#1506), draw the PR (body per the seat's prepared text incl.
      the R-6 note), complete the contract §F K-ASR signature with the PR link,
      merge (ratified autonomous), and verify the ASR deploy: image build resolves
      >=4.6.0 with 4.14.0 actually installed, deploy completes, and the
      C-NULL-DEPLOYED receipt is inscribed (running image digest + SDK version).
    priority: critical
    dependencies: [REL-2]
    acceptance_criteria:
      - "PR drawn with clean diff (services/** only) and merged"
      - "ASR image rebuilt + deployed; installed autom8y-core version receipted at 4.14.0"
      - "C-NULL-DEPLOYED receipt inscribed (gates FIX-N admits)"
  - id: REL-4
    summary: >-
      Merge asana fix/al5-alarm-actions-staging (@0f9a802a) — closes the TF
      state-vs-tree drift from the executed alarm apply. NOTE asana merge
      auto-deploys the service (~13-30min); TF-only diff, deploy is a no-op
      rebuild; verify the deploy completes green and the artifact-contains-
      new-modules check is N/A (no src change).
    priority: high
    acceptance_criteria:
      - "Branch merged; satellite deploy green; terraform plan from main tree shows NO drift on AL-5"
  - id: REL-5
    summary: >-
      FIX-N admits at gate-clear (asana #338 null→decay, #339 preload stamp
      honesty). ★TIME-GATED: operator ruling R-5/D-6 — merge ONLY when BOTH
      (a) ≥2026-08-12T09:19:45Z and (b) REL-3's C-NULL-DEPLOYED receipt exists.
      This grant does not override the gate. Runbook precondition SATISFIED.
      Consider the runbook's merge-batching note (#338+#339 close-merge = one
      rollback unit) — space them or accept the joint unit. If this session
      ends before the window, this item CARRIES to the next seam.
    priority: critical
    dependencies: [REL-3]
    acceptance_criteria:
      - "Both merged strictly post-window with C-NULL-DEPLOYED receipted"
      - "Each deploy verified green; rollback levers from the runbook confirmed reachable"
  - id: REL-6
    summary: >-
      REALIZE attestation: after REL-3 (and ideally REL-5) deploys, the next
      ORGANIC ASR tick (4h cron: 20:00Z / 00:00Z / …) is judged by the
      rite-disjoint verification-auditor (eunomia, aboard) under the STRICT
      R-2 bar: PASS counts ONLY via disposition=GATE on the content axis
      (offer_freshness_axis evidence present, NOT the DORMANT fallback),
      content age corroborated against the same-trace producer watermark, no
      synthetic warm, no threshold moved; DORMANT-fallback or deploy-adjacent
      PASSes carry ZERO weight. L4 keep-warm remains REFUSED throughout.
    priority: critical
    dependencies: [REL-3]
    acceptance_criteria:
      - "Attester verdict inscribed with the predicate receipts (trace-linked both sides)"
      - "R-4 review-prompts and R-8 rollback triggers quoted in the attestation"
---

# HANDOFF — offers-freshness-axis-contract → releaser: LAND + REALIZE

The producing wave's full record rides in `source_artifacts`. The release
spine is pre-adjudicated (S4 CERTIFIED-WITH-CONDITIONS; every condition
either discharged or inscribed above as a gate). Orchestration: releaser
potnia coordinates; pythia adjudicates at dynamic forks (premises falsified
mid-release are surfaced per §10.5, never papered — any fork touching an
operator-ruled gate escalates rather than re-rules).
