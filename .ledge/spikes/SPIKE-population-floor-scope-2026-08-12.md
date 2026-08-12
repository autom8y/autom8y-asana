---
type: spike
artifact_type: SPIKE
status: accepted
ratification: interview ratifies → status flips to accepted with the digest
initiative: substrate-v2-epoch
wave: S8-2
date: 2026-08-12
session: interview-ratification via AskUserQuestion (operator constraints: neutral framing, phased, assumptions surfaced, litigated, labeled recommendations, ratification digest)
consumes:
  - .sos/wip/parity/fetch-diagnostics/refusal-2026-08-12-073019945445.json (67 active rows, 1 offer_id null)
  - src/autom8_asana/substrate/freshness.py:154 (_VALUE_COLUMNS — double-duty pin)
  - src/autom8_asana/metrics/compute.py:116 (dedup unique(subset, keep="first"))
  - RULING-pythia-s8-2-adjudication-rubric-2026-08-03.md §1 W2 (over-refusal class)
---

# SPIKE — Population-floor scope: what should block serving active_mrr?

## The tension (both poles defensible)

Three provisioning-lag offers in three days each halted the parity window on a null
`offer_id` — a column the served number does not consume (active_mrr = Σ mrr over
classifier-active, deduped (office_phone, vertical) rows). One pole: this is the W2
over-refusal shape — v2 refusing a provably-correct number v1 serves, alarm-fatigue in
reverse, the founding wound's mirror. Other pole: the halts are a FEATURE — refuse>wrong
extends to frame integrity, and the window forced three real data fixes in three days
that would otherwise have rotted silently.

## Load-bearing facts (verified today)

1. Floor mechanics: `_value_columns_with_nulls(active)` refuses on ANY null among
   `_VALUE_COLUMNS = ("cost","mrr","offer_id","weekly_ad_spend")` on classifier-active
   rows (rebuild.py:379 path; active predicate per #318).
2. **Double duty**: `_VALUE_COLUMNS` is ALSO the FROZEN content-digest value set
   (`sv2-canonical-digest-1`, freshness.py:148-158 — "stable for the life of the frozen
   v1.0 seam"). Any floor rescope must introduce a SEPARATE floor-set definition; the
   digest set is untouchable without a digest-scheme version event.
3. The served metric consumes exactly: `section` (scope), `mrr` (sum),
   `office_phone`+`vertical` (dedup keys). Note polars `unique(subset, keep="first")`
   treats nulls as equal — a null dedup key on active rows would silently COLLAPSE
   distinct offers into one, corrupting the sum. So dedup keys are correctness-bearing
   for the number, not just metadata.
4. Today's active set (67 rows): zero nulls in mrr/office_phone/vertical/cost/was;
   exactly one in offer_id (since provisioned, ID 1608). A metric-consumed floor would
   have served all three incident days; the strict floor refused all three.
5. Provisioning reality: Offer IDs are set by the Business-Offers completion trigger —
   lag between an offer entering an active section and provisioning is structural.
6. The floor as-built was P7-gated twice (#305 iter-2, #318). A rescope is a corridor
   DELTA (P7: discriminating tests + qa gate). Mechanics fork (not operator-decided,
   disclosed): if the floor set is hardcoded inside the frozen seam, the change routes
   as an architect finding; if injectable via AcceptancePredicates, it is seam-use.
7. OUT OF SCOPE here: the PROV evaluated_count=0 finding (separate diagnosis, parallel).

## Decision space

**D1 — Purpose of the floor (the pillar).** (a) Protect the served NUMBER only →
floor = consumed columns. (b) Enforce frame-wide economic-data integrity → floor =
economic set (status quo). (c) TIERED: block on number-bearing columns, loudly surface
the rest. (d) Reject the frame ("wrong question").

**D2 — Serve-blocking set (concretely).** (a) `{cost,mrr,offer_id,weekly_ad_spend}`
status quo. (b) `{mrr,office_phone,vertical}` metric-consumed (sum + dedup
correctness). (c) `{mrr}` minimal. (d) Registry-governed per-entity set (C17 pattern —
operator-ratifiable config).

**D3 — Demoted columns' fate.** (i) Receipt warning + daily-digest line. (ii) Emitted
data-quality metric + ticket-class alarm (PROV pattern). (iii) Escalating: warn N
cycles then block. (iv) Nothing.

**D4 — Source of truth for the floor set.** (i) New hardcoded constant. (ii) DERIVED
at runtime from the metric definition's Scope (anti-RC-C: cannot drift from what the
metric consumes). (iii) Registry-governed (=D2d).

**D5 — Timing.** (i) Land now mid-window (P7 DELTA + qa gate; mixed-floor cycles noted
in the PT-03 Q1 ledger — cycle 1 served under the strict floor, no contradiction).
(ii) After window close (window remains lag-haltable; ceiling risk). (iii) Now, plus a
recorded pythia/PT-03 note on the mid-window floor change.

## Recommendation (labeled; one view among peers)

D1(c) tiered · D2(b) consumed · D3(ii) metric+alarm · D4(ii) derived · D5(iii).
Rationale: protects everything the number depends on (incl. the null-collapse dedup
hazard), kills the lag-interruption class, keeps every data wound loud. Main tradeoff:
the window stops FORCING data fixes — the three catches this week happened because
serving halted; a warning channel is easier to ignore than a halted window.

## Ratification digest (operator interview, 2026-08-12, two rounds via AskUserQuestion)

**DECIDED (operator-direct):**
1. **Floor purpose = TIERED** — serving blocks only on number-bearing columns; other
   economic nulls surface loudly without halting. BINDING QUALIFIER (operator verbatim
   intent): the mechanism must be future-proof/extensible — the dataframes substrate
   serves an insights pipeline with MANY consumers; ASR/active_mrr is one consumer
   implementation, and the floor must not pigeonhole the pipeline to it.
2. **Enforcement channel = PROV-7 data-quality alarm + digest**: emitted active-row
   economic-null metric (SubstrateProvability namespace), ticket-class alarm (in-repo
   tf, DP-4a apply pattern, paging unarmed), per-offer named lines in the daily digest.
3. **Timing = now, mid-window, + PT-03 ledger note** (mixed-floor cycles disclosed;
   cycle 1 served under the strict floor — no contradiction).
4. **The BRIDGE ships now** (common to both surviving Q3 options): publish-time floor
   rescoped to `{mrr, office_phone, vertical}` — sum inputs + dedup-collapse guards for
   the live consumer — decoupled from the FROZEN digest set; `offer_id/cost/
   weekly_ad_spend` demoted to the warning/alarm channel.

**DELEGATED (operator's words, verbatim intent):**
5. **Floor-locus ENDSTATE** — among {serve-time per-consumer derived, registry-governed
   per-entity, schema-tagged columns} — "to be litigated and triangulated through
   adjudication by rigorous architecturally principled evaluation by our pantheon
   subagent specialists": architect-led option-enumeration with arch-adversary
   challenge (P8 pattern), rendered as an option slate + recommendation for operator
   ratification.
6. **Bridge→endstate landing path** (post-window DELTA vs S9/S10 doctrine/kit form) —
   "to be advised by myron /frame and pythia /shape", consuming #5's slate.

**Sequencing:** cycle-2 sweep first (data fix 1608 already unblocks it under the
current floor) → bridge DELTA (P7: tests + qa gate) → locus adjudication (parallel,
background) → myron/pythia framing consumes the adjudication.

**EXPLICITLY DEFERRED:** the endstate locus choice itself; the landing path.
**ASSUMPTIONS UNCONFIRMED:** A6 (serve-time seam extension is cheap — the adjudication
verifies); A4 stands unobjected (floor rescope = P7 corridor DELTA, not a door);
upstream provisioning root-cure (trigger on section-entry) noted as adjacent
opportunity for the intake workstream, not decided here.
