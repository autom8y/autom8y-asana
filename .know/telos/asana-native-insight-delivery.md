---
type: telos
initiative: asana-native-insight-delivery
status: PROPOSED
created: 2026-08-12
author: >
  architect, standing in for the myron seat (unresolved in this channel
  2026-08-12 — no .claude/agents/myron.md, absent from `ari rite pantheon`;
  myron is a summonable hero requiring an operator `ari agent summon`). Authored
  under the /frame dispatch of 2026-08-12 per the ratified predecessor pattern
  (.know/telos/asana-mcp-postfelt-hardening.md:6 — PROPOSED at framing,
  operator-ratified after). This file DERIVES the mission and predicate from the
  substrate; unlike the mcp precedent it does NOT transcribe an operator's own
  words, because the dispatch instructed derive-don't-ask. Every line here is
  therefore amendable by the operator, and the mission itself is HELD.
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
frame: .sos/wip/frames/asana-native-insight-delivery.md
mission_status: >
  HELD — two defensible missions are present in the substrate (frame §3) and the
  frame refuses to pick. Mission A = new insight class (board behaviour,
  ungated). Mission B = better channel for the existing verdict record
  (gate-starved). The fork is the OPERATOR'S: "is this a NEW insight class, or a
  BETTER CHANNEL for the existing one?" Nothing downstream is well-posed until
  it is ruled.
amendable: >
  the Mission-A verification_deadline (PROPOSED 2026-09-30); the
  rite_disjoint_attester binding; the four-rung ladder and its receipts. The
  rung-4 OPERATOR reservation is proposed as structural (a felt observation about
  a teammate cannot be agent-closed) but is likewise the operator's to amend.
non_amendable_by_agents: >
  Mission-B carries NO deadline. Attaching one would smuggle back the clock that
  P-3 deliberately refused (RULING-operator-option4-interview-2026-08-12.md:21;
  ADR-007 §7.0 :1110-1117, §8 O-5 :1270). Only the operator may attach a clock to
  the dark period or anything gated on it.
---

# Telos — asana-native-insight-delivery (PROPOSED 2026-08-12)

**Gate A (telos-integrity-ref §3) — inception fields present and non-stub.**
**Gate A.1 (provenance-root) — every founding origin-signal is internal and was
live-read at frame time; the frame's grounding table plus SVR-0..8 are the
resolution receipts. No external origin-signal is asserted.**

## Declaration (telos-integrity-ref §2)

```yaml
telos:
  initiative_slug: asana-native-insight-delivery
  inception_anchor:
    framed_at: "2026-08-12"
    frame_artifact: ".sos/wip/frames/asana-native-insight-delivery.md:1"
    why_this_initiative_exists: >
      The measurement machinery built to litigate the offers freshness gate
      produced its first team-facing artifact
      (.ledge/reviews/REPORT-asr-team-brief-2026-08-12.md) plus a list of seven
      things it measured and could not fit. Three substrate facts define the
      envelope: (1) the #account-health rail is WARM, not dark — the ASR posts an
      abort alert every four hours (autom8y origin/main 6d555c07,
      services/account-status-recon/src/account_status_recon/orchestrator.py:212,223
      on config.py:177-180); only the verdict PAYLOAD is withheld under P-3.
      (2) A durable full-roster per-account verdict surface already exists and is
      armed in production (verdict_surface.py:1-20 SCHEMA_VERSION=2;
      terraform/services/account-status-recon/environments/production.tfvars:27
      verdict_surface_bucket = "autom8y-asr-verdicts"), and the Slack report
      points at it three times (report.py:76-83,133,171-190) — at a surface no
      offers-team member can open. (3) That surface DIES WITH THE GATE:
      _emit_verdict_surface at orchestrator.py:440 sits 198 lines after the
      readiness-FAIL abort return at orchestrator.py:242 inside the same
      function (run_reconciliation, orchestrator.py:65), so no rows are written
      during the pause. Fact (3) splits the work along the line that is this
      envelope's design spine: COMPLETENESS and FRESHNESS are different
      properties and only one is in doubt — completeness is receipted on every
      tick of the pause (68/68 active, 48/48 activating,
      REPORT-asr-team-brief-2026-08-12.md:138) while recency is refused.
      Board-behaviour readouts need completeness only and take staleness as their
      SUBJECT; verdict readouts need recency and are correctly withheld.
      ###
      ### ⚠ CORRECTED 2026-08-12 — the paragraph above is the initiative's stated
      ### design spine and its middle clause is FALSIFIED. The 68/68 and 48/48
      ### pair is total_count vs returned_count, taken post-filter/pre-pagination
      ### (query/engine.py:190, after df.filter() :170, before df.slice() :196)
      ### against post-slice (:243 → :286). It is a TRUNCATION PREDICATE OVER THE
      ### SERVED FRAME — pagination hygiene — NOT a correspondence receipt against
      ### the Asana board. A frame that silently lost thirty active offers reports
      ### 38/38 and passes every guard. The engine indicts itself at
      ### engine.py:136-141 ("the post-filter total_count CONFLATES the two"); the
      ### sole production consumer agrees at autom8y origin/main
      ### readiness.py:96-97 ("a watermark over a truncated result is a watermark
      ### over an arbitrary window"). Established by S1, verified under BLOCK by
      ### the rite-disjoint hygiene critic, corroborated by pythia at PT-02 which
      ### had authored the original claim and withdrew it.
      ###
      ### WHAT SURVIVES: the pair IS receipted every tick, including throughout
      ### the P-3 dark period, and the completeness/freshness DISTINCTION is real
      ### and remains the design spine. WHAT DOES NOT: calling this pair
      ### completeness, or resting class-B say-ability on it.
      ###
      ### ⚠ FURTHER (PT-02 §6 item 7, unresolved): honest_contract_complete — the
      ### receipt S1 rev-3 chose /rows to obtain — MAY CARRY THE SAME DEFECT.
      ### is_honest_complete() (dataframes/section_persistence.py:251-270) returns
      ### True iff no section is FAILED, and returns True VACUOUSLY for an empty
      ### manifest (:268-269). A section never ATTEMPTED is not FAILED — it is
      ### absent, and therefore invisible. That is a FAILURE-ABSENCE receipt, not
      ### a correspondence receipt. Engine boundary handling is fail-closed
      ### (engine.py:576-596) but the vacuous-true branch survives inside the
      ### manifest. Neither S1 nor its critic flagged this. NOT RULED — routed.
      ###
      ### THE SAME SUPERSEDED CLAIM IS STILL LIVE, UNCORRECTED, IN:
      ###   .sos/wip/frames/asana-native-insight-delivery.md:73, :166, :391
      ###   .ledge/reviews/REPORT-asr-team-brief-2026-08-12.md:205
      ###   .sos/wip/DESIGN-option4-verification-axis-annex-2026-08-12.md:1188
      ### Its GATE/ATTESTATION uses are CORRECT and must NOT be changed
      ### (ATTEST-rel6:537 labels it T-GUARD; ADR-007:1057) — there the pair is
      ### used as a non-truncation receipt, which is exactly what it is.
      ###
      ### THIS TELOS REMAINS status: PROPOSED. The correction is inscribed so
      ### ratification cannot absorb a falsified premise. It rules nothing.
  shipped_definition:
    code_or_artifact_landed:
      # PLANNED at inception — replace with real {path}:{line} anchors as items
      # land. Gate B refuses wave-level tokens without them (F-HYG-CF-A).
      - "(planned) WS-A demand-truth: UV-P-1 and UV-P-2 closed — a recorded set of asks attributable to named team members, OR a recorded null result"
      - "(planned) WS-B say-able set: a written completeness-vs-freshness predicate a downstream author can apply without re-litigating P-3, with the five REPORT §6 candidates classified against it"
      - "(planned) WS-C reachability [MISSION-B LIMB, UNCLOCKED]: a named non-engineer opens a complete run record without an engineer fetching it"
      - "(planned) WS-D residue triage: seven written dispositions; the four already-answered items (FP-1..FP-4) CLOSED rather than carried"
      - "(planned) WS-E delivery rails: a rail named with a live receipt, or an honest UV-P on one that is not"
      - "(planned) WS-F recurrence mechanism: two consecutive deliveries whose generation receipts show no human assembling them"
    user_visible_surface: >
      A member of the offers/account team — a person who lives in Asana, not in
      code — receives or opens a recurring readout about the offers board on its
      own cadence, and can reach the complete record behind any number in it.
      WHICH readout is the HELD mission fork: Mission A (how the board is
      actually worked — dwell, quiet corners, weekend gaps, section shape) or
      Mission B (the complete per-account health record, every account rather
      than the ~37 blocks that survive Slack's 50-block ceiling).
  verified_realized_definition:
    # THE LADDER. This arc's lesson is the bar: capability != realization;
    # merged != deployed != consumed. A reporting initiative adds rungs to that
    # same ladder: AUTHORED != DELIVERED != READ != ACTED ON. The bar is rung 4.
    user_visible_evidence:
      - >
        RUNG 1 authored (NOT the bar) — the readout exists as an artifact. Brief
        #1 already clears this and its own status is `draft`.
      - >
        RUNG 2 delivered (NOT the bar) — it landed in a channel on its own
        cadence, TWO consecutive occurrences, WITHOUT a human assembling it.
        Receipt: the two delivery receipts plus the generation receipt for each.
        A hand-assembled brief is a habit, not a mechanism.
      - >
        RUNG 3 read (NOT the bar) — a named team member's response cites a
        SPECIFIC FIGURE from it. Receipt: the reply, quoted. Generic
        acknowledgement is receipt-of-email, not reading.
      - >
        RUNG 4 ACTED ON — **THIS IS THE BAR**: a member of the offers/account
        team, unprompted by this initiative's authors, (a) receives or opens the
        readout on its own cadence at least TWICE, (b) names a specific figure
        from it back to us, and (c) makes a board change they attribute to it,
        the change independently observable in the Asana task record
        (modified_at / story record showing the section move or field edit,
        cross-checked against the attribution) — NOT "the report was posted" and
        NOT "the pipeline is green".
    verification_method: in-anger-dogfood
    verification_deadline: "2026-09-30"
    # ^ MISSION-A LIMB ONLY. PROPOSED: ~7 weeks — demand-truth, then two delivery
    # cycles, then room for an acted-on observation. Drives Naxos TELOS_OVERDUE.
    # MISSION-B LIMB CARRIES NO DEADLINE: gated on ADR-007 K-4-live, inheriting
    # P-3's no-clock. Recorded so a later seat does not read the absence of a
    # clock as an oversight — the same discipline ADR-007 §8 O-5 (:1270) records
    # for the pause itself. Only the operator may attach a clock here.
    rite_disjoint_attester: >
      SPLIT, because the top rung is felt.
      RUNGS 1-3 (receipt integrity): eunomia `verification-auditor`,
      rite-disjoint. The active rite for this working directory is 10x-dev
      (`ari rite current`, frame SVR-2 — note the repo CLAUDE.md's Quick Start
      block declares a `releaser` roster and the CLI, which that same CLAUDE.md
      names authoritative, returns 10x-dev). eunomia is a distinct home rite,
      co-seated here via the repo's borrowed-agents block; disjointness holds
      under co-seating.
      RUNG 4 (acted-on): OPERATOR-ONLY. It is a felt observation about a
      teammate. Precedent is explicit — eunomia "attests receipt integrity, never
      a felt outcome" (.know/telos/asana-mcp-postfelt-hardening.md:107-110). No
      agent closes rung 4, including the seat that authored this file.
  attestation_status:
    inception: INSCRIBED
    shipped: MISSING          # nothing built; envelope only
    verified_realized: UNATTESTED
    last_eunomia_advisory: null
  receipt_grammar:
    per_item_file_line_anchors:
      - ".ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md:54 (§4 priority domains — the real-world-check bar this initiative was ADJUDICATED inside; frame §2)"
      - ".ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md:59 (ratified inference: priority domains = money / customers / data-people-act-on)"
      - ".ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md:55 (§5 gate (b) — anything a customer sees, regardless of reversibility)"
      - ".ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md:57 (§7 never silently widen mandate — the basis for WS-D's disposition-not-absorption rule)"
      - ".ledge/decisions/RULING-operator-option4-interview-2026-08-12.md:21 (P-3 accept-until-replaced, NO clock — the standing tension this envelope is framed around)"
      - ".ledge/decisions/RULING-operator-option4-interview-2026-08-12.md:19,22,30 (P-1 both-disclosed-separately; P-4 observability-truthful-first; P-12 naming fence — inherited verbatim by any human-facing readout)"
      - ".ledge/decisions/ADR-007-verification-axis-gate-2026-08-12.md:1172-1186 (K-lane K-1..K-5; never bundle K-4) and :1228-1239 (the ONE-WAY DOOR on RowsMeta/AggregateMeta this initiative acquires NO dependency on)"
      - ".ledge/reviews/REPORT-asr-team-brief-2026-08-12.md:138 (⚠ CORRECTED 2026-08-12 — this anchor previously read 'completeness receipted on every tick — the fact that makes the class-B readout say-able under P-3'. That characterization is FALSIFIED. The 68/68 and 48/48 pair is total_count vs returned_count, taken post-filter/pre-pagination (query/engine.py:189-190, after df.filter() :168-170, before df.slice() :196) against post-slice (:243 → :286). It is a TRUNCATION PREDICATE OVER THE SERVED FRAME — pagination hygiene — NOT a correspondence receipt against the Asana board. A frame that silently lost thirty active offers reports 38/38 and passes every guard. The engine says so itself at engine.py:136-141; the sole production consumer agrees at autom8y origin/main readiness.py:96-97 ('a watermark over a truncated result is a watermark over an arbitrary window'). Established by S1 (PREDICATE-sayable-set… R-1) and independently verified under BLOCK by the rite-disjoint hygiene critic (CRITIQUE-s1-sayable-predicate-2026-08-12 §A). What survives: the pair IS receipted on every tick, including throughout the P-3 dark period. What does NOT survive: calling it completeness, or resting class-B say-ability on it. THIS TELOS IS STILL status: PROPOSED — the correction is inscribed so ratification cannot absorb a falsified premise; it rules nothing.)"
      - ".ledge/reviews/REPORT-asr-team-brief-2026-08-12.md:185-189,183,191,3 (five CANDIDATE asks; the ask channel; zero recorded asks; status draft)"
      - ".sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md:128,135 (34 sections, 21 zero-row, one at 2802, INACTIVE at 1066 — the board-shape fact no consumer has seen)"
      - ".sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md:55-58,279,477 (cadence 92 vs 26 advances; spread median 10.6h / p90 48.4h / max 88.3h; Monday-maximum mechanism)"
      - ".sos/wip/frames/asana-native-insight-delivery.md §4 (SVR ledger SVR-0..8 + UV-P-1..4: myron seat unresolved, iris unresolved, MCP write surface OFF, MCP stdio-only under promotion fence, comment-CREATE client-layer only, verdict surface armed, surface dies with the gate, rail is warm)"
      - ".sos/wip/frames/asana-native-insight-delivery.md §10 (falsification accounting: 7 premise events — 4 falsified, 3 refined — none papered)"
    cross_stream_concurrence: false
    code_verbatim_match: false
```

## Standing notes carried with this telos

**The mission is HELD; the ladder is not.** The fork at frame §3 is the
operator's. But whichever mission is ruled, the four-rung ladder and the rung-4
bar apply — the whole point of the predicate is that it does not soften when the
scope changes.

**The initiative's own predicate already bites on its own founding artifact.**
`REPORT-asr-team-brief-2026-08-12.md` is `status: draft` and carries no delivery
receipt (UV-P-1). At inception this initiative stands at **rung 1** on its own
evidence. That is recorded, not papered.

**Demand is unestablished (UV-P-2).** Zero asks are recorded against the report's
§6 invitation. A null result on UV-P-2 is a legitimate and mission-reshaping
finding, and WS-A exists to receive it either way. Building a recurring readout
nobody asked for is the authored ≠ read failure with extra steps.

**Four open UV-Ps ride this telos** (frame §4): UV-P-1 delivery of brief #1;
UV-P-2 demand; UV-P-3 live prod state of the `autom8y-asr-verdicts` bucket
(the cheapest falsifier of WS-C's premise — one `ListObjectsV2` + one
`GET latest.json`); UV-P-4 what non-engineering data surfaces the team already
has. Per SVR §1 RULE-2, any UV-P still unconsumed at a cross-rite HANDOFF gate is
carried into the HANDOFF under the Gate-C DEFER-tag pattern.

**Non-collision is a telos-level constraint, not just a shape concern.** This
initiative is READ-ONLY with respect to the ADR-007 K-lane: no touch on the
offer-axis combiner, the freshness-meta reducer, `RowsMeta`/`AggregateMeta`, the
manifest write path, or `SectionInfo`; nothing rides a K-lane PR. If a readout
wants a number that only exists on the K-lane, it **waits** — it does not widen
the one-way door.
