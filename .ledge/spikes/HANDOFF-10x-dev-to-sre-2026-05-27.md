---
type: handoff
artifact_id: HANDOFF-10x-dev-to-sre-2026-05-27
schema_version: "1.0"
source_rite: 10x-dev
target_rite: sre
handoff_type: validation
priority: high
blocking: true
initiative: freshness-verification-recency
created_at: 2026-05-27T19:45:00Z
status: draft
handoff_status: pending
authoring_context: >
  Authored at the hygiene station of the freshness-verification-recency procession
  (10x-dev build → hygiene CI-gate fix → SRE ops-validation). Content provenance is
  the 10x-dev build + QA gates + live prod re-probe (cited below). Surfaced now
  because PR #67 reached mergeState CLEAN and the merge is GATED on the SRE briefing.
source_artifacts:
  - .ledge/decisions/ADR-006-freshness-equals-verification-recency.md
  - .ledge/specs/freshness-verification-recency.tdd.md
  - .ledge/reviews/QA-freshness-verification-recency-gate.md
  - .sos/wip/SPIKE-freshness-last-verified-at.md
items:
  - id: SRE-001
    summary: >
      Configure the CloudWatch alarm for `section_name_contract_violation` to
      page ONLY on true contract violations, NOT on the expected first-deploy
      re-seed window.
    priority: critical
    validation_scope:
      - "Alarm MUST filter on `reseed_window=false` OR `LEVEL=ERROR` — NOT on the event name alone. [VERDICT: QA-gate-2 §merge-conditions #2, .ledge/reviews/QA-freshness-verification-recency-gate.md]"
      - "Rationale (code-anchored): the alarm tier is keyed on `last_verified_at is not None`. WARN/`reseed_window=true` = never-warmed (expected pre-first-warm); ERROR/`reseed_window=false` = a section stamped-but-still-null-named (true violation). [ADR-006 §Decision-7a]"
      - "Expected first-deploy behavior (live-measured): ~10 of 11 fleet projects emit ONE WARN-tier `section_name_contract_violation` each on first post-deploy warm, then self-clear on the warm cadence. [prod fleet probe 2026-05-27, QA-gate-2 §C-R1: 10/11 projects ≥2 sections all name=null pre-deploy]"
    notes: >
      If the alarm is wired on event-name-presence alone, first deploy pages ~10
      times for expected behavior. This is the load-bearing SRE config item.
    estimated_effort: 30-60 min
    dependencies: []

  - id: SRE-002
    summary: >
      Own the post-merge prod re-probe that discharges the evidence ceiling from
      MODERATE to STRONG (confirms the signal computes on the live fleet, not just
      the pre-merge spike).
    priority: high
    validation_scope:
      - "After PR #67 merges and one full provider-first warm runs (scheduled Lambda OR manual), confirm on the offer + unit manifests: `name_present == total` (re-seed populated), `last_verified_at` populated on all sections, `verification_age` computes (NOT the 62d mutation fallback). [VERDICT: QA-gate-2 §merge-conditions #3]"
      - "Confirm NO ERROR-tier `section_name_contract_violation` fires for ≥1h post-warm (the re-seed-window WARN should have cleared)."
      - "Pre-merge spike already demonstrated this on offer/1143843662099250: name_present 34/34, last_verified 34/34, verification_age=9m on 22 in-scope sections. [.sos/wip/SPIKE-freshness-last-verified-at.md §Empirical discharge] — SRE confirms it holds on a NON-spike scheduled warm across the fleet."
    notes: >
      The deployed warmer Lambda has reserved concurrency = 1; manual `force_warm`
      can throttle (TooManyRequestsException) if the scheduled run holds the slot.
      The EventBridge schedule is the reliable path. [observed 2026-05-27]
    estimated_effort: 1h (mostly wait-for-warm)
    dependencies: [SRE-001]

  - id: SRE-003
    summary: >
      Register the new observability surface (one new alarmable SLI + two new
      metrics) in the ops catalog / runbooks.
    priority: medium
    validation_scope:
      - "`verification_age` — new alarmable SLI under `--strict`. Semantics: now − min(last_verified_at) over active-classified sections. Replaces the mutation-age 62d false-signal as the trustworthy freshness gauge. [ADR-006 §Decision-4]"
      - "`section_name_contract_violation` — WARN (reseed window) / ERROR (true violation). Filter per SRE-001."
      - "`section_last_verified_stamp_failed` — emitted if the stamp-phase fails under the warm broad-catch (silent-degradation guard). [TDD §Decision-9; freshness/progressive stamp block]"
      - "`mutation_age` — retained as CONTEXT-ONLY, non-alarmable (the old write-age signal; do NOT alarm on it)."
    notes: >
      Null-watermark residual: ~21/34 offer + ~4/17 unit sections have watermark=null
      and retain hash-only change detection (pre-existing, not a regression). Their
      verification_age stamp is no stronger than the old signal was for them.
      [QA-gate rev-2 D8, documented]
    estimated_effort: 30 min
    dependencies: []
provenance:
  - source: .ledge/reviews/QA-freshness-verification-recency-gate.md
    type: artifact
    grade: strong
  - source: .ledge/decisions/ADR-006-freshness-equals-verification-recency.md
    type: adr
    grade: moderate
  - source: ".sos/wip/SPIKE-freshness-last-verified-at.md (live prod re-probe 2026-05-27 19:00 UTC)"
    type: artifact
    grade: strong
evidence_grade: strong
tradeoff_points:
  - attribute: deployability
    tradeoff: First-deploy WARN-tier alarm noise across ~10 fleet projects until first warm.
    rationale: >
      Accepted in exchange for self-healing re-seed (no separate backfill job). The
      warm cadence IS the backfill. SRE-001 alarm filter is the mitigation; without
      it, first deploy pages for expected behavior. [ADR-006 §Decision-7a]
  - attribute: observability-vs-correctness
    tradeoff: verification_age trustworthy enough to alarm only because the prober blind spot was fixed in-scope.
    rationale: >
      The D3 watermark-task-identity prober fix (shipped in PR #67, commit 34df2d44)
      closed the false-CLEAN channel for watermark-bearing sections, so a stamped
      section reflects a real verification. Null-watermark sections remain a named
      residual (SRE-003 note). [QA-gate rev-2/rev-3 D3/D8]
---

# HANDOFF — 10x-dev → SRE: freshness=verification-recency ops validation

## Why this is the rite-switch point

PR #67 is **mergeState: CLEAN** (all required checks green incl. the just-fixed lint
gate). The feature is built, multi-gate-QA'd, and pre-merge prod-re-probed to STRONG
evidence. The remaining work is **operational** — alarm configuration, post-merge
re-probe ownership, and observability-catalog registration — which lives in the SRE
rite. Per the procession, this requires a **rite switch (restart CC into SRE)**.

## MERGE GATING

**PR #67 SHOULD NOT merge until SRE-001 (alarm filter) is configured** — otherwise
the first post-deploy warm fires ~10 WARN-tier `section_name_contract_violation`
events fleet-wide against an unfiltered alarm, paging on expected behavior. Sequence:
SRE-001 alarm filter → merge PR #67 → SRE-002 post-merge re-probe.

## Receipt grammar (telos-integrity Gate C)

Every "verified/shipped" claim above carries a `[VERDICT: ...]` citation, a
`[file:line / artifact]` anchor, or a live-measurement timestamp. The one
forward-looking claim (SRE-002 "holds on a non-spike warm across the fleet") is
explicitly the SRE validation deliverable, not a pre-asserted fact — it is the
STRONG-discharge that SRE owns.

## Open follow-ups (non-blocking, tracked)

- HYG-002 durable fix: `chore(justfile): make verify CI-congruent` — separate hygiene PR. [.ledge/decisions/ADR-007-verify-denominator-congruence.md]
- `.know/defer-watch.yaml` entry `verify-denominator-resync` (cross-repo CI single-source) — to be written with the HYG-002 follow-up PR.
- D10/D12 (LOW): CLI integration test for the broad-catch degrade path.

## Response

On completion, append `## Response (sre)`: alarm-filter config reference (SRE-001),
post-merge re-probe results (SRE-002), catalog entries (SRE-003). Set
`handoff_status: completed`.

## Response (sre) — in progress

**SRE-001 — determination made; execution routed cross-repo (intra-rite).**
- observability-engineer determined the alarm surface is **Terraform-managed in the `autom8y` repo** (`terraform/services/asana/main.tf`), not CLI/ad-hoc — every live alarm maps to a committed TF resource. No infra mutated (would be drift).
- **Schema correction (load-bearing):** `section_name_contract_violation` is a structured **log event** (`logger.error`/`.warning`, `progressive.py:489-535`), NOT a CloudWatch metric. SRE-001 is therefore a **CloudWatch Logs metric filter + alarm**, not a bare metric alarm. The handoff's "configure the alarm" framing is corrected here.
- Full TF spec authored + routed: `.ledge/spikes/HANDOFF-sre-to-sre-crossrepo-2026-05-27.md` (copied to `autom8y/.ledge/spikes/`).
- **Routing per Pythia ruling (2026-05-27):** rite ⊥ repo — execution stays in the **sre** rite (the `autom8y` repo is already `ACTIVE_RITE=sre`; platform-engineer is the sre executor agent, not a rite). One CC-restart (repo-root → `autom8y`), then a single `/task` → platform-engineer. ("platform" is not a rite; my earlier `target_rite: platform` was an error.)

**SRE-002 — pending** (blocked on SRE-001 TF apply → PR #67 merge → deploy → first EventBridge-scheduled warm). Owns the MODERATE→STRONG discharge.

**SRE-003 — pending** (ops-catalog registration; do alongside/after SRE-002; must record the null-watermark residual caveat).

**Procession state:** SRE station's in-repo determination complete; execution demands a **repo switch to `autom8y` (same sre rite)** — the next CC-restart boundary. PR #67 merge remains gated on SRE-001.
