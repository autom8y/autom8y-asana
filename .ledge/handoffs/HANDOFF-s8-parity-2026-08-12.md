---
type: handoff
artifact_type: HANDOFF
subtype: daily-parity-digest (window day 2 of the extended count)
initiative: substrate-v2-epoch
wave: S8-2 (P5 live-parity window)
date: 2026-08-12
window_clock_start: 2026-08-11T10:57:51Z (extended count, per RULING-operator-extend-s8-2-window-2026-08-11)
hard_ceiling: 2026-08-18T10:36:46Z
status: accepted
---

# S8-2 PARITY DIGEST — 2026-08-12: CYCLE 2 SERVED PENNY-EXACT · ≥2-CYCLE CONJUNCT SATISFIED

**MISSION (verbatim):** "every business number the asana dataframe substrate serves is provably
current or loudly refused — delivered by a substrate-v2 designed whole and small enough that its
correctness is legible, with v1 deleted and the doctrine packaged so any autom8y-* repo can
reconstruct the same guarantees as a template application, not a research project."
**PREDICATE (verbatim, NOT "PRs merged"):** "Verified-realized" = P5 cutover-gate receipts clean
(adversarial fixture replay + bounded live-parity window, every divergence explained) AND a
rite-disjoint attester re-derives active_mrr by their own hands matching live Asana within
freshness-SLA across >=2 warm cycles AND v1 planes/bridges/flags enumerate to zero AND doctrine
landed at fleet-constitution level.

## ⭐ CYCLE 2 (of ≥2) — 2026-08-12T09:56:03Z, exit 0 SERVED, ~2 minutes

| Leg | v1 | v2 | Digest |
|---|---|---|---|
| **A — served active_mrr (gate anchor)** | **$78,285.00** | **$78,285.00** | `cd62f88b…` (identical) |
| B — exemplar aggregate (tripwire) | $74,885.00 | $74,885.00 | `378adcd3…` (identical) |

- **Cycle distinctness**: `built_from_live_at 2026-08-12T09:57:00Z` vs cycle 1's
  2026-08-11T10:58Z — two distinct warm generations ~23h apart. Zero divergence both
  cycles; per rubric §6 #9 an identical-instant match requires no pythia classification.
- Receipt `offer-1143843662099250-095659127513-6f054b99.json`; artifact `version_id
  9b5271f0…` published. Telemetry: 73 requests, **0×429, 0 retries**, 34/34 sections.
- Boundary accounting **reconciled exactly**: 73 page + 297 cascade + 70 pre-warm = 440
  = ledger delta. Day total 1,292/11,200 (11.5%) incl. the two morning refusals below.
- **data_quality_warnings: []** — the tiered floor's warning channel present (bridge
  fd7263fc live in the sweep tree) and EMPTY: zero active-row economic nulls.

**Window position: the ≥2-distinct-warm-cycles conjunct is SATISFIED.** The ~3-day floor
runs to ~2026-08-14T10:58Z; ceiling 2026-08-18T10:36:46Z. Remaining to evidence-close:
floor elapse + all-divergences-explained (trivially: there are none) + zero open wounds
(none) + budget honored (11.5% worst day). Cadence-diverse sweeps continue daily.

## Mixed-floor ledger note (the PT-03 Q1 disclosure, owed since the ratification)

Cycle 1 served under the STRICT economic floor; cycle 2 under the TIERED floor
(`OFFER_PUBLISH_FLOOR`, bridge #347 merged fd7263fc between them, per
SPIKE-population-floor-scope-2026-08-12 operator ratification). **The tier distinction
was never exercised**: cycle 2's active set carried zero demoted-column nulls, so strict
and tiered would have served byte-identically. No contradiction; both receipts stand.

## Morning refusals (both explained, zero wounds)

1. **07:28Z refused `['offer_id']`** — the third provisioning-lag offer (task
   1217390596823323); operator re-ran the offer update → Offer ID 1608 flowed. Under
   the now-live tiered floor this class serves-with-warning instead of halting.
2. **08:18Z refused C16 (1/34 sections)** — Asana cost-limiter ("exceptionally
   expensive") 50min after the prior sweep. Schedule cure proven: the 09:56Z sweep,
   ~100min later, took 0×429s.

## ⛔ FINDING → DEFECT → cure in flight: PROV evaluator was blind to the published artifact

The 2026-08-11 watch item (PROV completeness 0.0 / evaluated 0) CONVERTED to a finding on
cycle 2 (second consecutive publish, first-publish-ordering hypothesis falsified) and was
root-caused same-hour: `digest_of_canonical_frame_bytes` used bare `pl.DataFrame(rows)`
inference, which dies on the live artifact's sparse late-typed `trackstat_id` column
(4,181/4,191 null → Null-dtype prefix → ComputeError on `"BETTER25CTWA"`) — the exact
#313 construction class, missed in the evaluator path. [H20] held (loud skip, never
false-green) and **PROV-3 fired truthfully** on the emitted 0.0 (period 900s). Serve path
and parity legs unaffected (leg digest equality is verified in-leg, not by the evaluator).
Full record: `DEFECT-prov-digest-bare-inference-2026-08-12.md`. Cure **PR #351**
(value-columns-only reconstruction; two-sided offline proof vs the live artifact —
re-derived digest == `proof.content_digest` byte-exact, PROVABLE; discriminating tests
verified failing on pre-fix code) — qa-adversary gate in flight at authoring. The next
sweep's PROV block must read completeness 100 / evaluated 1 (live clear receipt).

## Floor-scope decision arc (same day, operator-ratified → landed)

Spike + 2-round interview ratified (#345) → tiered-floor bridge MERGED (#347 fd7263fc)
→ locus adjudication H1 "declare once, project twice" (#346) → adversary
PASS-WITH-CONDITIONS + metrics select-before-filter DEFECT (#348) → Gate-A telos (#350)
→ myron frame + pythia shape in `.sos/wip/frames/floor-locus-endstate.{md,shape.md}`
(gitignored per convention; 7 sprints, all-but-S0 post-window, PT-03 interlock §11:
FLE artifacts are POINTERS in the PT-03 packet, never gate conditions).

## Carried to PT-03

Mixed-floor Q1 note (above) · qa LOW F-1 (CW put-swallow) + F-2 (alarm cannot HOLD
between sparse sweeps; notBreaching releases PROV-3 between emissions — EventBridge
schedule G2 option-b is the cure) · C10 two-sided PROV-2 evidence (banked; heartbeat
re-confirmed OK 2026-08-12 09:31 local) · PROV blind-window disclosure (cycles 1-2
evaluator-blind; cured pre-gate if #351 lands green) · shape path + S0 ruling as
pointers only.
