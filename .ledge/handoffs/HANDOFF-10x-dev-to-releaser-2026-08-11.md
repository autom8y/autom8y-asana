---
artifact_id: HANDOFF-10x-dev-to-releaser-2026-08-11
schema_version: "1.0"
type: handoff
lifecycle: draft  # .ledge shelf lifecycle; `status` below is the HANDOFF-schema field (HANDOFF-009 requires its own enum)
source_rite: 10x-dev
target_rite: releaser
handoff_type: execution
priority: critical
blocking: true
initiative: offers-false-staleness-cure (wave 2, K bridge)
created_at: "2026-08-11T13:05:00Z"
status: in_progress  # FIRED by operator ruling R-3 (RULING-operator-s5-gate-interview-2026-08-11.md), 2026-08-11; releaser seats invoked inv-20260811-24155caefbac
session_id: session-20260811-115247-a1ccd942
sprint_id: sprint-20260811-offers-false-staleness-cure-wave1
source_artifacts:
  - .sos/wip/CENSUS-sdk-consumers-2026-08-11.md
  - .sos/wip/GATE-G-CUT-limb-b-2026-08-11.md
  - .sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md
evidence_grade: strong
provenance:
  - source: .sos/wip/CENSUS-sdk-consumers-2026-08-11.md
    type: artifact
    grade: strong
items:
  - id: PUB-001
    summary: >-
      Diagnose and repair the autom8y-core publish pipeline: 8 of the last 12
      publish runs are red; the 4.13.0 publish failed at the consumer gate with
      verbatim reason "satellite run conclusion 'cancelled'" — a false-block
      (satellite CI on main was green at the time). Source sits at 4.13.0+
      while CodeArtifact tops out at 4.12.0 (merged-unpublished six days).
    priority: critical
    acceptance_criteria:
      - A publish run completes green end-to-end and CodeArtifact serves the
        then-current source version of autom8y-core.
      - The false-block cause ("satellite run conclusion 'cancelled'" while the
        gated run was green) is NAMED with a receipt and guarded against
        recurrence (fix or documented override path).
      - The 8/12-red failure modes are triaged — repaired or explicitly carded.
    notes: >-
      Inherited debt, NOT crusade residue — 4.13.0 predates every crusade leg
      (census §5). Ruled cross-rite (releaser competence) by potnia
      consultation #3 under DESIGN §2.9 §7 scope discipline.
  - id: PUB-002
    summary: >-
      Publish autom8y-core 4.14.0 once autom8y/autom8y#1506 (K-SDK content-axis
      surface) merges. This is the middle leg of the FORCED S5 order:
      SDK-merge → 4.14.0 publish → ASR-merge. The ASR image resolves SDKs from
      CodeArtifact (services/account-status-recon Dockerfile:69) and its floor
      is deliberately raised to autom8y-core>=4.14.0 — the image cannot build
      until 4.14.0 is served.
    priority: critical
    dependencies: [PUB-001]
    acceptance_criteria:
      - CodeArtifact lists autom8y-core 4.14.0.
      - An ASR image build resolves the >=4.14.0 floor successfully (build-time
        proof; no deploy required by this item).
---

# HANDOFF — 10x-dev → releaser: autom8y-core publish convergence

## RESULT ADDENDUM (2026-08-11, PUB-001 executed post-fire)

**PUB-001: AC-1 MET (by the fleet, verified live)** — publish run 31498306734
(merge of autom8y#1507, 13:50Z) ran green end-to-end; CodeArtifact serves
**4.13.0** (publishedTime 14:10:12Z). The authorized re-run was correctly
declined (moot + no longer idempotent). **AC-2: cause NAMED with receipts** —
concurrency-group supersession (satellite `test.yml` shares
`test-${{github.ref}}` with push runs, `cancel-in-progress: true` cancels the
gate's dispatched run; `poll.py` maps cancelled→FAIL). Structural class,
transient instances, 6 of 12 reds. **Guard STAGED: PR autom8y#1516**
(bounded re-dispatch on cancelled, fail-closed two-sided, 105 tests; root-cause
complement — satellite concurrency-group isolation, 5-repo change — named in
the PR, not bundled). **AC-3 MET**: three failure classes triaged with run/job
receipts (A cancelled-false-block → guarded; B genuine satellite failures →
carded; C SDK's own test gate → carded). Premise refinements surfaced: the
"satellite CI green at the time" claim is PARTIALLY FALSIFIED (autom8y-data
main predominantly red 08-05→08-10) and the 4.13.0 block was OVER-DETERMINED
(ads leg genuine failure — closes the census ads-leg UV-P).

**PUB-002 path now**: merge #1516 first (removes the race from 4.14.0's
publish), then #1506 merge auto-publishes 4.14.0, then verify CodeArtifact +
one ASR image-build proof. The R-3 timeline-coupling risk is largely
dissolved: the pipeline works today; only the race guard and the two ordered
merges remain.

## Status: STAGED FOR OPERATOR FIRE (superseded — FIRED per R-3; see addendum)

This handoff is authored and ready but **not yet routed** — the routing is an
operator decision because a **ratified alternative exists**: DESIGN §2.9 L1361
retains **Lane J** (ASR-local derivation, zero SDK dependency) "as fallback if
the SDK change is blocked." A permanently red publish pipeline IS "blocked" in
delivery terms. The costed choice, per potnia consultation #3:

| Option | Cost | Effect |
|---|---|---|
| **Fire this handoff** (recommended by potnia's parallel-clocks rationale) | releaser-rite work on inherited CI debt | K lands as ratified (SDK-owned derivation, P11-conformant); S5 order SDK→publish→ASR |
| **Fall back to Lane J** | pays the P11 price (a per-application derivation, DP-3 constitutional law disfavours) | crusade decouples from fleet CI entirely; K-SDK PR still merges whenever publish converges |

**Timing**: S3-QA and S4-CERT have ZERO dependency on publish convergence —
only S5-merge does. Firing this in parallel with S3 runs the two clocks
concurrently instead of serially. Carding ≠ deferring.

**Dispatch mechanics when fired**: the attestation charge is emitted via
`ari procession charge --slots=<file>` (never hand-written); this artifact is
the work-transfer plane only. Full pipeline forensics (run IDs, per-leg gate
conclusions, the three-speed consumer versioning map, seven registered UV-Ps)
are in `.sos/wip/CENSUS-sdk-consumers-2026-08-11.md`.
