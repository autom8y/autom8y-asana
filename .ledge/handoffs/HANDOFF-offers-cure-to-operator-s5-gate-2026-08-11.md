---
type: handoff
status: draft
artifact_id: HANDOFF-offers-cure-to-operator-s5-gate-2026-08-11
crusade: offers-false-staleness-cure (rename pending — card #4)
session: session-20260811-115247-a1ccd942
sprint: sprint-20260811-offers-false-staleness-cure-wave1
date: 2026-08-11
from: 10x-dev wave (S0-S4 complete, C-2 discharged)
to: OPERATOR (S5 gate stack)
borrow_state_live: "10x-dev native (potnia, requirements-analyst, architect, principal-engineer, qa-adversary) + sre co-seats (inv-20260811-7dc640ec7e0d) + dre co-seats (inv-20260811-712099ca4841, first-invoked at S4); verified via `ari rite current` at authoring"
evidence_posture: grade-split carried verbatim from DESIGN §5 + S3-AUDIT lifts — AUDITED where externally corroborated, MODERATE where not (K-dominates-J explicitly NEVER lifted)
---

# HANDOFF — offers-false-staleness-cure → OPERATOR (S5 gate)

Every station receipt is inline-cited; every falsified premise is named as
falsified in `.sos/wip/RECEIPT-s0-s05-premise-refinement-2026-08-11.md`
(refinements #0-#8, the crusade's epistemic ledger). Nothing below is asserted
above its evidence grade.

## 1. What stands built (nothing merged, nothing deployed, control arm intact)

| Leg | Head | State | Tests |
|---|---|---|---|
| K-SDK (content-axis derivation, autom8y-core → 4.14.0) | `7ca58a81` | PR autom8y#1506 OPEN | 819 passed; QA delta GO-CONFIRMED-AT-HEAD |
| K-ASR (gate on content axis; 4 guards + attribution fix) | `7d634c1a` | branch pushed; PR drawn post-S5 by design | 652 passed; QA delta GO-CONFIRMED-AT-HEAD |
| FIX-N-B (null→decay micro-packet, replaced-ground inscription) | `f9e60593` | asana PR #338 OPEN, MERGE-HELD | 1387 passed; teeth 6R/4G |
| FIX-N-C1 (preload stamp honesty, default-preserving) | `79c0078c` | asana PR #339 OPEN, MERGE-HELD | 2831 passed; teeth 7R/1G |
| F (alarm legs) | `0f9a802a` | staged; apply card ready | validated offline two-sided |

Verification chain: QA GO×4 (`.sos/wip/QA-s3-offers-cure-2026-08-11.md`, +§D
delta pass) → S3-AUDIT lifts (tooth, T-GUARD → AUDITED) → S4
**CERTIFIED-WITH-CONDITIONS**, GO-for-activation withheld under GATE-1
(`.sos/wip/CERT-offers-cure-s4-2026-08-11.md`). The frozen contract
(`.sos/wip/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md`) is
byte-verified at every mutation (§B fence: empty diff, re-run by five parties).

## 2. YOUR GATE STACK (the change-warden's ranked seven, annotated)

1. **Publish-vs-Lane-J** — fire `.ledge/handoffs/HANDOFF-10x-dev-to-releaser-2026-08-11.md`
   (repair fleet CI; recommended, clocks run parallel) OR invoke the ratified
   Lane-J fallback (ASR-local derivation, pays P11). The whole delivery path
   hangs on this choice.
2. **Enforce the forced S5 order**: SDK-merge → 4.14.0 publish → ASR-merge.
   The ASR image build fails loud (deliberately) until 4.14.0 serves.
3. ~~Green receipts at exact merge heads~~ — **DISCHARGED** (C-2 QA delta pass,
   GO-CONFIRMED-AT-HEADS). If any head moves again, re-run the delta pass.
4. **FIX-N merge admits** (operator-admit per ratified S5 posture; asana merge =
   auto-deploy ~13min into money-adjacent numbers): strictly post-window
   (≥2026-08-12T09:19:45Z) AND C-NULL landed under the **strict deployed-image
   reading** (merged is not landed). #338 additionally carries the Lane-B
   replaced-ground release conditions (all inscribed in its body).
5. **Ratify the honest REALIZE predicate** (warden-minted): the organic tick's
   PASS counts ONLY via `disposition=GATE` on the content axis with same-trace
   producer-watermark corroboration, no synthetic warm, no threshold moved —
   DORMANT-fallback or deploy-adjacent PASSes carry zero weight (two such
   PASSes already occurred today and prove the bare predicate non-discriminating).
   The REALIZE attester is rite-disjoint (eunomia verification-auditor or dre),
   invoked at that gate only.
6. **Inscribe the image-rollback story before merge** (Lambdas float on
   CodeArtifact — rollback is image rollback, not pin rollback).
7. **Sequencing ratification-delta** (potnia, consultation #3): the 4.14.0
   floor raise converted ratified-ungated step 3 into gated-on-fleet-CI —
   flagged-with-rationale, no HAP-4, but the re-gating is yours to ratify.

## 3. Standing operator cards (accrued, none absorbed)

- **#1 Alarm apply** — `.sos/wip/CARD-l6-alarm-apply-2026-08-11.md`: bind AL-5
  to `autom8y-platform-alerts`, `-target`ed sequence; post-apply green ≠ cure;
  AL-5's semantics demoted in writing (a read counter carrying an age field);
  its honest successor is frame-scoped PROV-family (never
  `content_watermark_returned` — S3-AUDIT boundary).
- **#4 Rename** — the slug asserts the falsified title premise;
  `offers-freshness-axis-contract` suggested (D-9).
- **#5 SLA authority (D-5b)** — producer governed 3600s vs consumer override
  [UV-P: deployed location]; decide post-K; the F-GUARD 60s provisional
  allowance and the HELD-2 token choice are BOUND to this card.
- **#7 Separate initiatives** — resolver cadence-ABSENCE alert (collapse
  02:41:59Z, caller-side, silent-by-construction; acid test: 2 of 4
  reconciliations skipped today, nothing paged) · ABORT-path `fetch_timestamp`
  field · `max_total>700` headroom trend field (T-GUARD's only leading
  indicator, nothing computes it) · ECS turnover triggers [UV-P] ·
  `dataframe_cache_put` consumer sweep [UV-P] · TF snowflake commit-or-delete ·
  contested unit-recon read · #312 named debt · reconcile-ads T-GUARD opt-in
  choice (fail-closed conversion, deliberate per consumer).
- **Tripwire tally** — 1 confirmed (Lane-B ground) + 1 candidate (title
  PV-FALSE) of the 3-firing escalation criterion; your tally to keep.

## 4. Platform friction (receipted, not editorial)

The moirai-autopark loop forced **7 main-thread session restorations** in one
day (cadence degraded to ~12s — structurally faster than a coordinator round
trip). Complaints: `COMPLAINT-20260811-095320-moirai.yaml` +
`COMPLAINT-20260811-100250-moirai.yaml` (escalated HIGH, corroborated 7th
cycle). Working workaround, proven: `ari session resume -s <id>` from the MAIN
thread, with lifecycle mutations bundled atomically under the moirai lock
protocol (resume → lock → mutate → unlock in minimal turns); the deviation is
surfaced in the session Timeline each time it was used.

## 4b. POST-INTERVIEW ADDENDUM (2026-08-11, after RULING-operator-s5-gate-interview)

Rulings executing: R-9 alarm apply **EXECUTED + verified** (AL-5 bound to
autom8y-platform-alerts; the §4.4-predicted spurious ALARM→OK fired 28s
post-apply — a reconfiguration artifact, zero cure evidence; card §10 records
it; end-to-end channel delivery unconfirmed). R-6 honest-quiet amendment
**BUILT** @`fdef8bd6` (QA delta running). R-7 runbook **DISCHARGED**
(`.sos/wip/RUNBOOK-image-rollback-offers-cure-2026-08-11.md`) — the merge
precondition is now SATISFIED; R-5's gate set reduces to: window close +
C-NULL deployed + #338's inscribed conditions. PUB-001 diagnosis running.

New facts from the runbook: (a) **rollback no-op trap** — task-def revisions
748/749/750 share one image; roll back by image-tag difference and verify the
RUNNING task, never `current−1`; (b) **D-5b deployed-threshold UV-P CLOSED**
— `OFFER_STALENESS_THRESHOLD_SECONDS=3600` is an explicit ASR Lambda env var
(matches code default; the 7200 abort is derived ×2.0) — a code-default
change alone cannot move the deployed gate; (c) **SECURITY FLAG (route to
security lane, not this crusade)**: a Grafana OTLP basic-auth credential sits
in plaintext ASR Lambda env config, unlike its Secrets-Manager siblings —
not reproduced in any artifact; (d) **merge-batching**: merging asana #338 +
#339 close together collapses them into ONE rollback unit — space them or
accept the joint unit; (e) the ECS deployment alarms already automate
R-8-shaped rollback but ONLY within the in-flight deploy window — the
4-hourly-tick blind spot is why the runbook exists. Also on the stack:
the alarm-staging branch merge (closes the state-vs-tree TF drift) and the
binding-report CONFIGURED-vs-LIVE relabel.

## 5. Artifact index (the record, one place)

`.sos/wip/`: RECEIPT-s0-s05-premise-refinement (epistemic ledger #0-#8) ·
DESIGN-s1-arch-watermark-contract (v2, A-K, §5 grade-split) ·
CONTRACT-offers-freshness-axis-frozen (497-line fence + §F signatures) ·
SURFACE-k-sdk (+§9 deltas) · QA-s3-offers-cure (+§D delta pass) ·
CERT-offers-cure-s4 · DIAG-S1-cadence · CENSUS-sdk-consumers (+A, +A.8
correction) · LEDGER-asr-ticks (+B) · UVP-null-watermark-frequency ·
GATE-G-CUT-limb-b (+rebase+expansion addenda) · GATE-G-CUT-k-sdk ·
CARD-l6-alarm-apply. `.ledge/handoffs/`: HANDOFF-10x-dev-to-releaser (staged).
`.know/scar-tissue.md`: SCAR-ALARM-BINDING-001 (satellite-local, N=3).
Monorepo custody markers: ASR subtree + root `.sos/wip/`. Worktrees:
offers-limb-b (bf57) · offers-k-sdk (2384) · offers-fixn (f350) ·
offers-alarm-legs (0315).
