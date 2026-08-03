---
type: decision
decision_subtype: floor-integrity-micro-packet
artifact_id: FIX-1-empty-section-stamp
id: FIX-1
title: "FIX-1 — empty (rows=0) null-watermark sections stamp on hash-CLEAN"
created_at: "2026-08-03"
author: main-thread orchestrator (ruling session, operator interview #3)
status: accepted
lifecycle_status: AUTO-RATIFIED-P13 (staged recommendation; 24h operator amend window from inscription — one word reverts)
rite: 10x-dev
initiative: substrate-v2-epoch
law: "charter P6 [A-2026-08-03] floor-integrity exception class — instance #1"
adr_lineage: "ADR-006 §Decision-5b / D8 — scope refinement, not reversal"
---

# FIX-1 — empty-section stamp (floor-integrity class, instance #1)

## The false signal (operator-reported 2026-08-03)

`active_mrr` emitted `WARNING: verification age 6d 21h` while the value rode
fully-verified populated sections. Manifest probe: **18 sections pinned at the
last pre-P3 bulk stamp (2026-07-27T16:01) — every one `rows=0, watermark=NULL`**
(STAGING, PENDING APPROVAL, CALL, …). The floor's own stamp rule (P3, PR #276)
was mislabeling verified facts as unverifiable → false-stale → the alarm-fatigue
direction that buried the original wound for 14 days.

## The epistemic rationale (why this is a refinement, not a loosening)

P3's no-stamp rule guards the D8 false-CLEAN class: *a content edit that
preserves the GID set is invisible to a hash-only probe.* **On a rows=0 section
that class is unconstructable**: any content requires a task; any task changes
the GID set from ∅; the prober compares the LIVE GID fetch against the stored
hash every warm → the change surfaces as STRUCTURE_CHANGED. Therefore
hash-CLEAN on an empty section IS complete verification — "still empty" is
re-proven on every warm. The stamp is truthful.

Non-empty null-watermark sections keep the full P3 no-stamp + watermark-heal
path — the load-bearing D8 guard is untouched, and the fix's test proves both
sides in one warm (empty stamps; populated sibling refuses).

## The change

`progressive.py` stamp pass: the no-stamp condition gains `and stamp_info.rows != 0`.
Two-sided test: `test_fix1_empty_null_watermark_clean_stamps`. Effect in prod:
the next warm stamps the 18 empty sections → the verification floor jumps to the
populated-section minimum → the WARNING clears honestly.

## Provenance (P13 disclosure)

Ruled under the charter P6 **[A-2026-08-03] floor-integrity exception class**
(operator interview #3, Phase-1 Q1: "Floor-integrity exceptions" ratified) and
inscribed under **P13 staged-auto**: this packet AUTO-RATIFIES on inscription
with a **24h operator amend window** — one word reverts. v2 impact: none (v2's
whole-artifact proof design retires the per-section stamp entirely at cutover;
this fix dies with v1 at S11, as all floor fixes do).
