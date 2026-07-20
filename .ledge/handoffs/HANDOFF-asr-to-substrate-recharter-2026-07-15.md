---
type: handoff
status: proposed
handoff_type: charter
from: ASR arc (asr-terminal-realization session) — FORK-1 escalation
to: RE-CHARTERED asana-substrate session (fresh conversation, this repo)
date: 2026-07-15
re: >
  FORK-1 operator ruling (RE-CHARTER) on the stalled F1a keystone. Supersedes nothing;
  continues HANDOFF-asr-to-substrate-session-2026-07-13.md and
  HANDOFF-asr-to-substrate-durability-finding-2026-07-14.md (both land with this commit).
---

# HANDOFF — ASR arc → RE-CHARTERED substrate session: the F1a keystone

## The ruling (FORK-1, operator, 2026-07-15)

The ASR terminal-realization wave's FORK-1 fired ("F1a stalled >1 operator-day → escalate
routing") and the **operator ruled RE-CHARTER**: fire/resume the dedicated asana-substrate
session with the R-2 protected-floor mandate and this handoff chain. Pythia's adjudication
(recommended RE-CHARTER over ABSORB/HYBRID/HOLD): it honors the ratified 07-13
dedicated-session ruling and P-B commons ownership, and homes the F1a *measurement* — the
true long pole — with the session that owns both the commons and the AL-5 instrument it
must also fix. **Fold the floor-sizing / cross-initiative-attribution call into the same
operator turn if it arises** — one operator touch, not two.

## Stall receipts (why FORK-1 fired)

- `origin/main` frozen at `78edc63c` since 2026-07-13T23:08:46+02:00 (verified live
  2026-07-15 ~14:20Z). Both `substrate-*` branches predate the 07-14 mandate. Zero
  mandate-era commits, branches, or PRs. The prior substrate session appears dead/parked.

## Fresh sawtooth receipts (live CloudWatch, 26h to 2026-07-15T13:21Z)

`Autom8y/AsanaSubstrateFreshness OfferFrameAgeSeconds{project_gid=1143843662099250}`,
Maximum/300s (sparse emission — read METRIC datapoints, never AL-5 alarm state):

| Local (+02) | Age (s) | | Local (+02) | Age (s) |
|---|---|---|---|---|
| 07-14 14:21 | 8710 | | 07-15 03:01 | 14297 |
| 07-14 15:01 | 3480 | | 07-15 04:01 | **30765** |
| 07-14 15:31 | 5236 | | 07-15 04:31 | 1388 |
| 07-14 18:21 | 9017 | | 07-15 07:01 | 14313 |
| 07-14 19:01 | 14264 | | 07-15 11:01 | 14298 |
| 07-14 19:11 | 1610 | | 07-15 14:56 | 2029 |
| 07-14 23:01 | 14096 | | 07-15 15:21 | 1054 |

Pattern unchanged from the durability finding: warm cycles bite (dips to ~1–2ks) then
re-stale to ~4h plateaus; one 8.5h spike. A transient dip is a self-heal, not a cure.

## What the ASR arc consumes (the W3 receipt — UNCHANGED)

Two consecutive `OfferFrameAgeSeconds{1143843662099250}` datapoints **<3600s** PLUS a
`hierarchy_gap_warming_partial|complete` event with `fetched>0` — **SUSTAINED, not a dip**.
Canary #2 (the formal GATE-OP-5 baseline) fires on this receipt. Nothing else is owed to
the ASR arc.

## The mandate (R-2, RATIFIED 2026-07-14 — binding in-arc per R5 portability)

1. The shared Asana API budget is the arc's first registered commons, **owned by THIS
   session** (P-B: owned surface + owner + SLO; internal yields to client-felt; operator
   adjudicates ties).
2. The substrate warmer gets a **PROTECTED-MINIMUM quota** — blanket-yield is overruled;
   substrate freshness is commons-serving.
3. The floor's **SIZE comes from your F1a measurement** ("measured sizing"); genuine
   trade-offs against client-felt consumers escalate to the operator.

## The /goal charge (paste into a fresh session in `~/Code/a8/a8/repos/autom8y-asana`)

```
Proceed as the RE-CHARTERED asana-substrate session on the F1a keystone: the durable
offer-axis cure under the ratified R-2 PROTECTED-FLOOR-MEASURED mandate (FORK-1
operator ruling 2026-07-15, RE-CHARTER).

READ FIRST (all in this repo unless noted):
.ledge/handoffs/HANDOFF-asr-to-substrate-recharter-2026-07-15.md (this charter)
.ledge/handoffs/HANDOFF-asr-to-substrate-durability-finding-2026-07-14.md (W3 bar + AL-5 defect)
.ledge/handoffs/HANDOFF-asr-to-substrate-session-2026-07-13.md (original chartering)
.ledge/decisions/TELOS-asana-substrate-freshness-2026-07-13.md
monorepo services/account-status-recon/.ledge/decisions/RULINGS-asr-operator-interview-2026-07-{13,14}.md

PV PRE-FLIGHT (staleness is a finding — re-prove live before any mutation):
sawtooth state (OfferFrameAgeSeconds{1143843662099250} datapoints, NOT AL-5 state);
hierarchy_gap_warming parent_gids_count trajectory; 429 storm rate (rate-limit hits/30min);
C1 attribution currency (who consumes the shared 1500/60s ceiling NOW — the EBI Phase-A
hypothesis is UNCONFIRMED; attribution FIRST, a warmer patch under an unresolved storm
burns the session).

THE WORK (keystone order):
1. C1 attribution REFRESH → name the storm's consumer(s) with receipts.
2. F1a MEASURED SIZING → the protected floor's size, from measurement not assumption.
   If attribution is cross-initiative or any trade-off is client-felt → OPERATOR, same turn.
3. F1a BUILD → cross-consumer budget partition honoring the protected floor (per-client
   AIMD exists per ADR-ASANA-003 rate_limit.py/client_pool.py; there is NO cross-consumer
   allocator for the shared 1500/60s ceiling — that absence is the defect).
4. AL-5 SPARSITY FIX (your instrument): OfferFrameAgeSeconds emission is ~hourly-sparse vs
   Period=300/EvaluationPeriods=2/notBreaching → OK ≠ fresh. Match period to emission,
   M-of-N over a wider window, or emit continuously. Until fixed: read datapoints.
5. PROVE the W3 receipt SUSTAINED (2 consecutive <3600s + gap-warm fetched>0, held across
   cycles, not a dip) → hand the receipt to the ASR arc (canary #2 consumes it).

CONSTRAINTS: commons owned per P-B; monorepo Service-Terraform apply lane is SHARED with
the ASR session (single-writer, announce before applying, never blind-collide); do not
double-drive ASR-owned surfaces (ASR env/schedule/alarms). Scars: watcher-kills ×7 (embed
receipts IN watcher output); stale-tree (read origin/main, never local trees); macOS shell
init-flake (simple inline-arg commands, retry once); hyphen-token false-zeros (CloudWatch
tokenizes hyphens); commit = one paren-scope subject, no attribution trailers.

DONE-BAR: W3 receipt SUSTAINED + AL-5 no longer blind (or a documented interim read
protocol) + receipts handed back. The ASR arc's canary #2 → GATE-OP-5 → node-4 enable
chain resumes on your receipt.
```

## Coordination notes for the re-chartered session

- The ASR session is concurrently discharging warden conditions in autom8y-data + monorepo
  terraform (alarm re-key + materialization image repin). The monorepo Service-Terraform
  apply lane is the ONLY shared surface — announce, single-writer, escalate on collision
  (ratified non-ruling #2: ESCALATE, never infer).
- `HANDOFF-substrate-to-asr-receipts-2026-07-13.md` (already tracked) is the prior
  session's receipt artifact — consume for C1/C2/C3 state; C3's cure was proven TRANSIENT
  (the durability finding), which is exactly why F1a is the keystone.
