---
type: handoff
artifact_id: HANDOFF-sre-to-fleet-potnia-staging-infra-clarification-2026-04-22
schema_version: "1.0"
source_rite: sre
target_rite: fleet-potnia
handoff_type: assessment
priority: low
blocking: false
initiative: autom8y-core-aliaschoices-platformization-phase-a
created_at: "2026-04-22T11:45Z"
status: proposed
source_artifacts:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-PR131-POSTMERGE-REREVIEW-2026-04-22.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SRE-F2-migration-024-staging-replay-design-2026-04-22.md
evidence_grade: strong
items:
  - id: STAGING-INFRA-001
    summary: Clarify whether a staging environment (separate from production + CI-ephemeral) exists or is intended to exist for services/auth — F2 staging alembic replay is BLOCKED-ON-STAGING-INFRA pending this decision.
    priority: low
    assessment_questions:
      - "Does staging RDS exist outside the repo (AWS console only, not IaC-tracked) for services/auth? If yes, provide: RDS instance identifier, Secrets Manager path for DB password, ECS cluster/service names for auth in staging."
      - "If staging RDS does not exist, is it intended to exist (imminent IaC authorship) or permanently-not-planned? If permanent-not-planned, SRE F2 verdict collapses to REPLAY-READY-MANUAL-V1 (ephemeral CI Postgres) which is acceptable."
      - "Are there other services (asana, scheduling, data, val01b) that DO have staging and would benefit from the same replay pattern? This would promote STAGING-INFRA-001 from a services/auth concern to a fleet-level pattern."
    notes: |
      F2 of PR #131 post-merge re-review identified that terraform/environments/ has only production/ — no staging workspace materialized. variables.tf accepts `staging` as legal value but no tfvars/RDS/backend exists.

      Priority LOW because migration 024 round-trip was proven locally (dev Postgres) at merge and staging replay was explicitly scope-deferred per SRE-CONCURRENCE §7.2. This handoff does not unblock anything that is currently blocking.

      Preferred resolution path: (a) confirm staging permanently-not-planned → SRE accepts REPLAY-READY-MANUAL-V1 ephemeral-CI verdict; F2 closes. OR (b) confirm staging exists-but-undocumented → fleet-potnia produces staging-infra inventory note, SRE upgrades F2 to REPLAY-READY-CI-V2 against real staging. OR (c) confirm staging imminent-IaC → fleet-potnia owns authorship, SRE F2 stays OPEN pending that authorship.
    dependencies: []
    estimated_effort: "30 min to 2 hours depending on resolution path chosen"
---

# HANDOFF — SRE → fleet-potnia (Staging Infra Clarification)

## 1. The question

Does staging exist? If yes, where? If no, is it intended to?

## 2. Why SRE is asking

F2 migration 024 staging alembic replay design (SRE-F2-migration-024-staging-replay-design-2026-04-22.md) produced a complete procedure but cannot bind to a real staging target because the target is not repo-discoverable.

## 3. Deliverable requested

A short answer (paragraph or Slack thread is fine, no formal artifact required) covering the three assessment questions. Routing the answer back into the F2 artifact as an appended §9 staging-disposition closes the loop.

## 4. Priority posture

LOW. Phase A retirement-baseline is signed regardless of this answer.

---

*Emitted 2026-04-22T11:45Z by SRE rite.*
