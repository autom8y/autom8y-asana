---
type: handoff
artifact_id: HANDOFF-ads-actioning-f1a-headroom-2026-07-20
status: proposed
source_rite: sre (observability seat — ads-actioning wave-1, S6 ARTERIES)
addressed_to: F1a potnia — CHARTER-f1a-budget-allocator-2026-07-20
date: 2026-07-20
initiative: ads-actioning bridge — action-writer budget-headroom requirement
frame: COORDINATE-NEVER-ANNEX (one charter informing another; #242 lineage sovereign; the 1500/60s budget seam is the only shared surface)
evidence_grade: MODERATE (read-only static reads + live gh/worktree probes; every number file:line-cited, command-output-cited, or marked UNMEASURED)
realization_rung: FILED / BUILT (authored + filed; NOT yet acknowledged or accepted by F1a)
telos_touch: TELOS-asana-substrate-freshness-2026-07-13 (F1a's ratified telos — this filing RIDES C1's measurement; it does not amend the telos)
---

# HANDOFF — ads-actioning → F1a: reserve an action-writer headroom line at C1

**To:** the F1a potnia holding `CHARTER-f1a-budget-allocator-2026-07-20.md`.
**From:** the ads-actioning wave-1 sre seat (S6 ARTERIES).
**Ask (single, bounded):** the C1 attribution keystone must carry an explicit, **named
action-writer headroom row** in its who-burns receipt **before** the Phase-2a/2b sizing
fork consumes it. This is a REQUEST from a sibling charter — not a fact about F1a's
internal state, and not a claim on F1a's design authority (see §4, §5).

**Why now (time-urgency, receipt-backed):** two F1a build worktrees are observably live
— `feat/f1a-budget-allocator` and `wt.qa.f1a-canary` (Receipt R6, `git worktree list`)
— so the C1 → sizing window is near. If the allocator is sized across only the two
*currently-visible* writers, a later ads-actioning arm that rides Asana has no reserved
slack, and re-sizing means re-litigating the whole cross-consumer arbitration. Filing
before/at C1 is cheap; filing after sizing is not. **F1a's internal C1 progress is
UNPROBED — see UV-P-3 (§5).**

---

## §1 The requirement

The C1 attribution keystone is DAG node 1 — "**blocks ALL downstream — no allocator
design exists before the heat-map**" (`CHARTER-f1a-budget-allocator-2026-07-20.md:45`),
and its charge is to "MEASURE who burns the budget" under fence **F-d — measure, never
assume** (`CHARTER…:41-43`, node row `CHARTER…:65`). This filing rides F-d; it does not
fight it.

**REQUIREMENT:** C1's who-burns heat-map must add one explicit, **named action-writer
row** before the model/sizing fork (nodes 2a/2b) consumes the receipt.

- The row is a **RESERVED slot, not a current draw.** Season-1 ads-actioning writes are
  modern-direct and do **NOT** ride the shared Asana 1500/60s budget (decision D-5 —
  provenance UV-P'd below). So the season-1-**measured** value of this row may legitimately
  be **zero**.
- The load-bearing point is that the row **EXISTS and is NAMED** in the allocation model,
  so the allocator is not sized to consume 100% of 1500/60s across the two *current*
  writers and leave the known-future third writer to **fold invisibly into the shared ECS
  log line** (`receipts.py:160`, `GLINT-CORPUS-ads-actioning-2026-07-20.md:85`).
- **The number is C1's to measure; the SLOT is what this filing requires.** This is a
  visibility ask (name the third writer in the model), not a sizing prescription. Sizing —
  how much headroom, on which fork, whose quota yields — stays entirely F1a's ruling under
  its own adversary gate (`CHARTER…:72`).

This maps to the ads-actioning pre-work registry item **P-10** (three-writer budget
arbitration; co-sequence F1a + asana-mcp + action-writer) at
`GLINT-CORPUS-ads-actioning-2026-07-20.md:230`.

---

## §2 The three-writer budget census

One budget (**1500/60s**, `CHARTER…:24`; token bucket `config.py:322`,
`GLINT…:80`), one project GID (**`1143843662099250`**, `CHARTER…:24`, `GLINT…:80`), three
writers. F1a's C1 heat-map today has a forward slot for **one** of them.

| # | Writer | Liveness (receipt) | Same GID `1143843662099250` / draws 1500/60s? | Budget draw | Forward C1 slot today |
|---|--------|--------------------|-----------------------------------------------|-------------|------------------------|
| **(a)** | legacy always-on webhook / `asana_handler` consumer | LIVE, always-on (`GLINT…:80,125`; the storm producer the F1a telos exists to protect) | YES — `offer.py:87` == legacy `section/main.py:1004`; token bucket `config.py:322`; writes `x-fleet-idempotency:False` (`entity_write.py:191`) — `GLINT…:80` | **UNMEASURED** — cross-consumer arbitration CONFIRMED ABSENT (`ATTRIBUTION-RECEIPT-asana-429-storm-2026-07-13.md`, `GLINT…:83-85`) | in-storm but un-attributed |
| **(b)** | **asana-mcp-v1** | **MERGED 2026-07-20T13:35:45Z** (Receipt R1, live gh-probe) — the glint corpus recorded it **DRAFT** (`GLINT…:82`); **the drift is the point** | YES — same project GID; ships `field_write_service` + composite `add_tag→push→mark_complete` (`a46c2efd`, `GLINT…:82-83`) | **UNMEASURED** — new writers "fold invisibly into the shared ECS log line" `receipts.py:160` (`GLINT…:85`) | **NONE** (Receipt R4) |
| **(c)** | ads-actioning **future action-writer** | NOT BUILT. Season-1 = modern-direct; does **NOT** ride Asana (D-5, UV-P below) | **NO for season-1** (zero Asana draw); later arms MAY ride the seam | **ZERO** season-1 / **UNMEASURED** for later arms | **NONE** — this is the requested RESERVED row |

**Reading of the census (systems view):** three writers now contend for one budget
(legacy webhook, asana-mcp, future action-writer); **F1a is currently sizing visible to
one and blind to two** (`GLINT…:87`). (b) is the sharp one — it is **LIVE-merged today**,
un-inventoried in the C1 receipt, and its per-writer draw is UNMEASURED. This filing does
not ask F1a to measure (b) as a favor to ads-actioning — measuring **all** current writers
is already C1's own charge (F-d). This filing adds only the **forward (c) row** so the
sizing does not foreclose it.

---

## §3 Receipts (SVR — direct-inspection at claim-assertion time; grade MODERATE)

Every platform-behavior claim above resolves to one of these. Live probes are
re-runnable; file:line anchors are verbatim slices.

**R1 — asana-mcp-v1 (#242) is MERGED, not DRAFT.** `verification_method: bash-probe`

```
$ gh pr view 242 --repo autom8y/autom8y-asana --json state,mergedAt,number,title
{"mergedAt":"2026-07-20T13:35:45Z","number":242,"state":"MERGED",
 "title":"feat(asana-mcp-v1): s6 assembly — stacked on #238/#239/#240 (rebases after merge)"}
exit 0
```
Claim: the third writer is LIVE-merged into `autom8y-asana`; the corpus's DRAFT record
(`GLINT…:82`) is stale — the write surface is in main now, not pending.

**R2 — verification MUST pin `--repo`; a bare `gh pr view 242` is a trap.**
`verification_method: bash-probe`

```
$ gh pr view 242            # NO --repo — resolves against a different repo
{"number":242,"state":"MERGED",
 "title":"BI-integrity crusade: wave-1 G1-G7 guards + census"}   # ← autom8y-DATA PR, unrelated
```
Claim: PR number 242 collides across repos. **F1a, to re-verify (b), run exactly:**
`gh pr view 242 --repo autom8y/autom8y-asana --json state,mergedAt` — **never** a bare
`gh pr view 242`, which returns autom8y-data's unrelated BI-integrity PR.

**R3 — shared budget + GID (file-read).** `CHARTER-f1a-budget-allocator-2026-07-20.md:24`
— "the LIVE shared Asana **1500/60s** budget … GID `1143843662099250`". Corroborated
`GLINT…:80` (token bucket `config.py:322`).

**R4 — C1 has no forward action-writer slot (file-read).** `GLINT…:84-86` — "F1a's C1
heat-map … has **no forward slot for an action-writer** — new writers fold invisibly into
the shared ECS log line (`receipts.py:160`)."

**R5 — three-writer contention + F1a sizing blind to two (file-read).** `GLINT…:87` —
"three writers now contend for one budget (legacy webhook, asana-mcp, future
action-writer); F1a is sizing blind to two."

**R6 — F1a build is live now (bash-probe, urgency basis).**
`git -C …/autom8y-asana worktree list` returns branches `feat/f1a-budget-allocator`
(`wt.10x.f1a-allocator.20260720T153911`) and `wt.qa.f1a-canary.20260720T170231`. Claim:
the allocator + canary worktrees exist → C1→sizing is imminent. **Scope of claim:
existence only. Internal C1 progress is NOT inferred from this — UV-P-3.**

**R7 — f-1 pacing manifest (file-read).**
`data/offline/current/_asr_verdicts_manifest.json` (re-read 2026-07-20): `schema_version:
2` (L22); `degraded_sources: ["billing"]` (L10-12); `run_id:
bec80758-13cc-4fe5-a038-7506068d944d` (L20); `verdict_at: 2026-07-19T16:34:11Z` (L25);
`row_count: 147` (L16). See §6 f-1 note.

---

## §4 Frame — COORDINATE-NEVER-ANNEX

This is **one charter informing another.** Explicitly:

- **#242 lineage is sovereign.** asana-mcp-v1 is its own program; this filing neither
  claims nor re-litigates it. It is named here only as a *census fact* about the shared
  budget.
- **The 1500/60s budget seam is the only shared surface.** ads-actioning does not reach
  into F1a's allocation design, its adversary gate, or its GO-LIVE carve-out (`CHARTER…:33`,
  `…:77` — operator-only). Those remain wholly F1a's.
- **This filing prescribes a SLOT, never a number.** How much headroom, which fork
  (insufficient vs maldistributed, `CHARTER…:54-59`), and which consumer yields are F1a's
  measurements and rulings. If C1 measures the (c) row at zero for season-1 and elects to
  reserve nothing, that is a legitimate F1a outcome — the requirement is satisfied by the
  row being *named and considered*, not by any particular reservation.

---

## §5 UV-P disclosures

**UV-P-3 (the load-bearing disclosure):**
`[UV-P-3: the F1a C1 keystone's execution state and its receptivity to this headroom row
is UNPROBED | METHOD: deferred-to-F1a-potnia-acknowledgment | REASON: this is a
cross-charter REQUEST, not an assertion about F1a's internal progress; the sre seat
observed only that F1a build worktrees exist (R6) and did NOT read into the f1a-allocator
session state, per the COORDINATE-NEVER-ANNEX fence]`

**UV-P-D5 (provenance of the season-1 routing premise):**
`[UV-P: season-1 ads-actioning writes are modern-direct and do NOT ride the Asana
1500/60s budget (decision D-5) | METHOD: deferred-to-ads-actioning-decision-record |
REASON: D-5 is carried from the S6 ARTERIES dispatch brief; its decision artifact was not
resolved to a live file:line within this filing session. F1a may treat the (c) row as
zero-draw-for-season-1 on this basis and reconcile against the ads-actioning /frame
decision record if it wishes independent confirmation]`

---

## §6 Companion notes (for F1a's situational awareness; not part of the ask)

**P-12 live-PR reconciliation** (the three PRs the ads-actioning frame reconciles against;
none merged by the ads-actioning program):

- **asana #242** — MERGED 2026-07-20T13:35:45Z (R1). The (b) writer. Drift vs corpus's
  DRAFT record is the census point.
- **data #319** — OPEN / INERT, title `⛔DO-NOT-MERGE feat(fleet-write): fleet-grain write
  authorization (INERT, staging-only)` (live gh-probe, `--repo autom8y/autom8y-data`). The
  fleet-write admission substrate any nhc-db-side action-writer would ride; the P-3/F-6
  ruling locus. **DO-NOT-MERGE.** Named for awareness only — orthogonal to the Asana
  budget seam.
- **data #83** — OPEN / DRAFT / HELD, title `feat(analytics): convs ads-attribution
  priority [HELD — do not merge]` (live gh-probe). Dormant ads-attribution analytics.

**f-1 watch** (the ads-actioning pacing clock; **not** an F1a dependency — recorded so
the two charters share one artery reading): manifest re-read 2026-07-20 = `schema_version
2` / `degraded_sources ['billing']` / run `bec80758` (R7) → **HALF-FIRABLE** (schema
conjunct met; `degraded_sources==[]` conjunct blocked by the live, uncured get_insight-503,
`GLINT…:24-31`). **Watch-trigger:** `degraded_sources==[]` on any **post-`bec80758`** run.
Billing-class action cards stay gated; season-1 creative/targeting is **delivery-invariant
and NOT gated** (`GLINT…:91-96`). The 503 cure is upstream / out of ads-actioning scope.

---

## §7 Realization rung + acknowledgment criteria

**Rung (honest, never rounded up):** `FILED / BUILT`. This filing is authored and staged
to PR; it is **not** yet ACKNOWLEDGED or ACCEPTED by F1a, and the (c) row is **not** yet
in any C1 receipt. Filing ladder: `FILED < ACKNOWLEDGED < ACCEPTED-INTO-C1 < MEASURED`.
We stand at FILED.

**Acknowledged when** the F1a potnia records a disposition of the (c) row — accept
(carry the named row into the C1 who-burns receipt before 2a/2b), decline-with-reason, or
defer-with-trigger. Any of the three discharges this filing; silent drop does not.

**Grade:** MODERATE (read-only static + live probe; self-graded, sre-seat authorship —
no rite-disjoint corroboration sought for a coordination filing).

— sre seat, ads-actioning wave-1 / S6 ARTERIES, 2026-07-20. COORDINATE-NEVER-ANNEX.
