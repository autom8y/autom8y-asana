---
type: handoff
artifact_type: HANDOFF
from_rite: 10x-dev (S8 corridor, session session-20260730-141905-058c4fd7)
to: operator (two levers) → then S8-2 session (same corridor)
initiative: substrate-v2-epoch
wave: S8 — phases S8-0 + S8-1 COMPLETE; S8-2 ARMED-PENDING-OPERATOR
date: 2026-07-30
status: draft
main_sha: 6ba2a04fc0c0e2ff764d549bb497183a33f615ae
charter: .ledge/specs/CHARTER-substrate-v2-epoch-2026-07-27.md
telos: .know/telos/substrate-v2-epoch.md
predecessor_handoff: .ledge/handoffs/HANDOFF-wave2-to-s8-cutover-gate-2026-07-29.md
---

# HANDOFF — S8-0 + S8-1 COMPLETE · S8-2 awaits two operator levers

## 1. Mission + Realization Predicate (operator verbatim — the exit-anchor)

**MISSION:** "every business number the asana dataframe substrate serves is provably
current or loudly refused — delivered by a substrate-v2 designed whole and small enough
that its correctness is legible, with v1 deleted and the doctrine packaged so any
autom8y-* repo can reconstruct the same guarantees as a template application, not a
research project."

**PREDICATE (NOT "PRs merged"):** "Verified-realized" = P5 cutover-gate receipts clean
(adversarial fixture replay + bounded live-parity window, every divergence explained)
AND a rite-disjoint attester re-derives active_mrr by their own hands matching live Asana
within freshness-SLA across >=2 warm cycles AND v1 planes/bridges/flags enumerate to zero
AND doctrine landed at fleet-constitution level.

**LEG status:** LEG-1 = **HALF-DISCHARGED** (fixture-replay receipt PASS; live-parity
pending). LEG-2/3/4 unchanged (S12/S11/S9+S10).

## 2. What landed this session (all on main 6ba2a04f)

| Item | Receipt |
|---|---|
| S8-0 pre-gate hardening (PR #292, squash 6ba2a04f): AIMD `slot.reject()` on 429 (mutation-proven) · per-day P10 budget counter (`ParityBudgetExhausted`, wired through `fetch_all_paced`, live leg still dark) · process-singleton fetcher · exemplar #2 current-state anchor ($80,985, S3-derived, 0 Asana) · bytes-vs-constant tripwire · UV-P-6 minted · DEFER-2026-052..055 promoted · docstring truth-fixes | qa-adversary **GO**; 285 green; 24 CI checks; ZERO src/substrate changes |
| S8-1 fixture-replay gate receipt — **PASS** (22/22 predicates + both exemplars; self-discrimination 5/5; unexplained divergences 0) | `.ledge/reviews/GATE-substrate-v2-s8-1-fixture-replay-2026-07-30.md` |
| Recapture receipt + measured dark-drift **−$3,400/−4.03%** (explained per-section) | `.ledge/reviews/RECEIPT-s8-0-fixture-recapture-2026-07-30.md` |
| Operator packets authored | DP-4a-READY + C8 (below) |
| Rulings of record | potnia S8 orchestration ruling (GO; gate-of-record = post-S8-0 corpus ✓ honored) · pythia recapture ruling (O4; executed verbatim) |

## 3. THE TWO OPERATOR LEVERS (S8-2 arms on BOTH)

1. **DP-4a — apply PROV-1..6** → `.ledge/decisions/DP-4a-READY-provability-alarms-apply-2026-07-30.md`
   (exact terraform lever; D6b already in the suite as PROV-6; **expect PROV-2 dead-man
   to fire post-apply** until the window drives sweeps — that is it working, and C10
   evidence). Ruling: `applied` | `hold`.
2. **C8 — govern the SLA** → `.ledge/decisions/C8-sla-governance-packet-2026-07-30.md`
   (offer SLA currently inherits 180s cache-TTL vs ~17–25min warm cadence → v2 would
   refuse ~85–90% of offer serves → **the parity window starves**; recommended:
   option-c governed `freshness_sla_seconds`, offer=3600s, architect-DELTA + small PR).
   Ruling: mechanism + values + semantic-delta `ack`.

## 4. S8-2 ignite sequence (next session; multi-day window discipline)

1. Verify: DP-4a `applied` + C8 ruled (if option-c: land the architect-DELTA PR first,
   P7 bar). Re-run preflight (rite, main, telos, PR #279 still draft-held).
2. O4 leg-2: window-open re-snapshot of the offer plane (S3-only, receipted; append
   drift verdict to the recapture receipt). Discharge UV-P-6 (real section counts →
   budget-cap calibration) from the same probe.
3. Budget-ledger hardening (carried LOWs, pre-arming): corrupt-JSON → refuse loudly;
   cross-process lock; multi-unit overshoot check. Small PR, P7 bar.
4. ARM live parity: rides the S4 rebuild primitive EXCLUSIVELY; per-day budget enforced;
   off-peak preference; receipt per touch; v2 beside v1 against live prod; EVERY
   divergence → ledger → pythia classifies {explained-benign | wound}; wound → DELTA to
   build, window clock restarts per pythia.
5. Park-per-day: `HANDOFF-s8-parity-<date>.md` carrying ledger + receipts. Never
   fake-complete a window.
6. Window closed → **PT-03** (fresh-instance potnia, Q1-Q6 per the dispatch; supersets
   shape :490-492) → on PASS: rollback drill → PT-CUTOVER → PT-04 (≥2 warm cycles,
   MODERATE cap) → un-hold S9 PR #279. S11 (DP-1/DP-4b) + S12 (`ari sync --rite=eunomia`)
   are the NEXT waves — not this mandate.

## 5. Fresh SVR / UV-P deltas

- UV-P-6 MINTED (real section counts; discharge at S8-2 window-open probe).
- Eunomia co-seat discrepancy carried (potnia's ruling said not-co-seated; live pantheon
  shows co-seated `inv-20260730-746d385f5f3c`) — dormancy law HELD either way (zero
  eunomia agents used); resolve the roster-read gap at next potnia dispatch.
- The commit-message PreToolUse hook blocks the ENTIRE bash chain on rejection (ate a
  `ruff format` step this session → one red CI round; cured `8027229a`). Operational
  note for future chains: commit separately from verification steps.
- Exemplar #1 vs #2 section-name nuance: prod bytes carry HYPHEN (U+002D); exemplar #1's
  synthetic fixture used EN-DASH (U+2013). The real bytes win at parity time.

## 6. Discipline carried (binding on S8-2)

P5 (every divergence explained before flip) · P7 (rigor at the gate + doors only) ·
P8 (doors = operator packets w/ dissent) · P10 (paced primitives only; per-day budget
now EXISTS and is enforced; ad-hoc pulls banned) · T2/dormancy (no eunomia agent
pre-S12) · seams FROZEN (a seam-change is an architect finding) · self-assessment caps
MODERATE (S12 re-derives).
