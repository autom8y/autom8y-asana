---
type: handoff
status: proposed
handoff_type: execution
from: ASR arc (account-status-recon session, monorepo)
to: dedicated asana-substrate session (this repo)
date: 2026-07-13
authority: RULINGS-asr-operator-interview-2026-07-13 (RATIFIED) — rulings P3, R1, R5
---

# HANDOFF — ASR arc → dedicated asana-substrate session (2026-07-13)

> **Charter (operator-ratified P3/R1):** this session owns the **429-storm substrate incident**
> — attribution FIRST — and the **substrate-freshness CLASS ownership** (an owned surface with a
> standing owner + SLO, homed in this repo). The storm is that owner's first ticket. The ASR arc
> is parked on ASR-local rungs and resumes on this session's receipts.
>
> **Grandeur anchor:** land the PRODUCTION-READY, PROVEN, REALIZABLE ASR composition (the
> cross-tenant three-axis reconciliation; schedule DISABLED, node-4 deferred). The offer
> substrate this session cures is the composition's binding constraint (G2) — nothing downstream
> (canary → supervised first egress → operator firehose ruling → enable) can move until the ASR
> offer frame is fresh again.

## Inherited rulings (R5: these BIND this session — no re-interview)

Ledger: `services/account-status-recon/.ledge/decisions/RULINGS-asr-operator-interview-2026-07-13.md`
(monorepo local canonical; the origin/main-visible copy lands via
`services/account-status-recon/.ledge/shelf/` — PR #1019, the fleet's blessed .ledge landing
zone since service .gitignore tracks only shelf/). Operative here:
- **Lanes (P4, in-lane, receipts + ledger mandatory):** canary-class env mutations with proven
  byte-verbatim revert (internal, schedule-disabled surfaces); alarm-hygiene mutations that do
  NOT page off-hours and do NOT touch client-visible surfaces; docs/artifact landings to
  origin/main; scoped-fix merge + routine production apply on green.
- **Carve-outs (confirm-first, unchanged):** anything that pages a human / NEW paging wiring,
  secrets/rotation, client-visible risk, spending, data deletion, node-4.
- **Non-ruling #2 (cross-session concurrency):** if you collide with another session on a
  repo/infra surface, ESCALATE — do not infer a collision posture.
- **Non-ruling #3 (throttle-a-client):** if attribution shows the storm's consumer IS a
  live-client-serving flow, the cure trade-off is a fresh operator escalation. Do NOT throttle a
  client-felt path on your own authority.

## Work items

### W1 — Attribution (FIRST): the WHO-is-consuming receipt
The fleet shares Asana's 1500 req/60s ceiling. Produce a dated receipt of consumption by
consumer/initiative across the storm window.
- Onset arithmetic: last successful ASR-GID warm ≈ **2026-07-10T15:50Z** — the same day the EBI
  Phase-A flip went live (nudge sweep activated 07-13). **This correlation is an UNVERIFIED
  HYPOTHESIS** — attribute, don't assume.
- Known: this repo made **zero** warmer/concurrency changes 07-08→07-13 (cure is likely not
  warmer-local); 429 rate observed 1,422–2,344 hits/30min fleet-wide (2026-07-13 receipts).
- **Acceptance:** a dated per-consumer breakdown of Asana API consumption for the onset window +
  today; a named owner for the dominant consumer; escalation filed if it is client-serving.

### W2 — Freshness-class ownership charter (P3)
Author the substrate-freshness ownership artifact: the owned surface (entity frames this repo
serves), its owner, its SLO, and its detection. Third eruption of this class:
CACHE_NOT_WARMED P0 (2026-06-08) → warmer stall (2026-07-07) → this storm.
- **Include the granularity gap found today:** the offer dead-man keys on
  `entity_type="offer"` — `offer:warm_complete:age_seconds` read **8,396s (~2.3h, healthy)** at
  2026-07-13T18:32Z while the ASR frame (project_gid `1143843662099250`) sat **86,848s (~24.1h)
  stale**. Per-GID starvation is INVISIBLE to entity-level absence. Any re-designed detection
  must see the GID axis.
- **Acceptance:** charter artifact in this repo's `.ledge/`; detection design names the per-GID
  blind spot.

### W3 — Cure the ASR-GID starvation (the arc's blocking receipt)
Restore the ASR offer frame (project_gid `1143843662099250`) to sustained freshness.
Mechanism is yours (per-GID warm prioritization, concurrency/backoff, cross-consumer
arbitration extending ADR-ASANA-003's per-client AIMD — a fleet cross-CONSUMER budget allocator
does not exist today); the interview deliberately did NOT prescribe the HOW.
- **Acceptance (the receipt the ASR arc resumes on):** `frame age < 3600s` for the ASR GID,
  sustained across ≥2 consecutive warm cycles, with dated serve-path receipts
  (`/ecs/autom8y-asana-service` log events for the GID, or the equivalent live query).

### W4 — Warmer dead-man hygiene
`autom8-asana-cache-warmer-DMS-24h` (CloudWatch, monorepo asana terraform) has been in ALARM
since **2026-06-04** with `ActionsEnabled: False` — dark for 5+ weeks. Reconcile it
(re-arm / re-key / retire) under the alarm-hygiene lane. NEW paging wiring = confirm-first.
Related, already handled by the ASR arc: the AMP offer-freshness SLO alerts were DISARMED
to their ship-dark spec today (monorepo PR #1018 → `e7024c9c`); re-arm is a registered rung
gated on that spec's (a)/(b)/(c)+soak — coordinate rather than re-arm ad hoc.

## State snapshot (ALL receipts dated 2026-07-13 — STALE at your session open; PV pre-flight re-verify)

| Receipt | Value | Source |
|---|---|---|
| ASR offer frame age | 86,848s (~24.1h) @13:00Z, climbing daily (74.1→84.7→86.8ks over 07-11→13) | asana service logs |
| Entity-level warm age | 8,396s (~2.3h) @18:32Z — warms succeed for SOME offer project | AMP ruler query |
| OfferWarmCompleteDeadMan | ALERTS = empty (NOT firing; granularity-blind) | AMP ruler query |
| 429 storm | 1,422–2,344 rate-limit hits/30min, fleet-wide, + 900s warmer timeouts | asana service logs |
| platform-alerts channel | 70–170 msgs/day (trained-ignore risk context) | SNS CloudWatch metrics |
| asana origin/main | `249f00c3` (#230/#231 insights-lane landed TODAY — another session is ACTIVE in this repo; coordinate, see non-ruling #2) | git |
| monorepo origin/main | `e7024c9c` (the SLO-disarm merge) | git |

**Corrected premise (do not inherit the stale one):** earlier artifacts said "zero successful
warms ≥48h" — that was GID-scoped truth mis-scoped to the entity class. True state: entity-level
offer warms succeed at least intermittently (2.3h-old write at 18:32Z); the ASR GID specifically
starves. See PR #1018's correction comment.

## Disciplines (carried verbatim from the arc)
- ★Stale-tree scar (fired 6×): read origin/main, NEVER the local working tree.
- Staleness is a finding, not a footnote — every inherited receipt above must be re-proven live
  at session open before it is load-bearing.
- Every claim carries a dated receipt (file:line at origin/main, or live aws/gh output).
- Self-assessment caps MODERATE; STRONG requires rite-disjoint corroboration.
- Secrets by sha256 prefix only; never a raw value in shell or logs.
- Commits: one paren-scope subject, no attribution trailers.

## Receipt contract back to the ASR arc
1. **W1 attribution receipt** (dated, per-consumer) — unblocks the storm's ownership decision.
2. **W3 freshness receipt** (ASR GID frame <3600s sustained ×2 cycles) — the ASR arc resumes at
   the dry-run canary (its step 3) on this receipt.
3. **W4 disposition** (re-armed / re-keyed / retired, with receipts) — feeds the ASR arc's
   step-6 alarm-reconciliation (three dead-men total: warmer DMS, AMP SLO set, ASR liveness).
