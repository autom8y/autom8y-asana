---
type: telos
initiative: name-the-zero
status: INSCRIBED (inception) — verification_deadline ESTIMATIVE (frame Trigger Table row 6; operator spoke no date; R-17 "NO DATE, BAR ONLY" available as an operator word; adjustable at /shape)
created: 2026-09-05
inscribed_by: >
  main thread, WAVE-2 dispatch session (d5861864). The telos block below is
  transplanted VERBATIM from the frame's §2 (authored by myron under the
  operator's word of 2026-09-05 "request what's needed from the peer locus then
  fire it"; peer pointers cited by file:line, peer gaps carried as UV-P).
  North of record: .sos/wip/CONSULT-north-iii-2026-09-05.md §1 — "a reading
  that cannot name its own kind is still silence". Policy of record inherited:
  .ledge/decisions/RATIFICATION-matcher-recalibration-sitting-2026-09-04.md
  (RS-3 RETRO requirement :36-38; RS-4 first-successor ordering STANDS — this
  frame names workstreams, it does not order them).
source: .sos/wip/frames/name-the-zero.md §2 (transplanted verbatim)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
code_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y @ origin/main 52995b26
frame: .sos/wip/frames/name-the-zero.md
shape: .sos/wip/frames/name-the-zero.shape.md (not yet authored at inscription time)
parent_wave: close-the-activation-loop (successor of matcher-recalibration; DF-40 + RESIDUAL-5 + RETRO)
---

# Telos — name-the-zero (inscribed 2026-09-05)

**Gate A closed by inscription.** Mission (end state): every zero the
booking-attribution plane shows NAMES ITS OWN KIND (nothing-happened vs
could-not-look), and every booking the intake fails to deliver is COUNTED at a
floor and RECOVERABLE by a walled, operator-worded retroactive act — never
dropped silently. Verified-realized = predicate legs (a) and (b) below, observed
LIVE and certified by a rite-disjoint critic — NOT "PRs merged", NOT
self-attested green. DONE IS A BAR, NOT A DATE. Say "measured zero, meter under
repair", never just "zero".

```yaml
telos:
  initiative_slug: name-the-zero
  inception_anchor:
    framed_at: 2026-09-05
    frame_artifact: .sos/wip/frames/name-the-zero.md:45
    why_this_initiative_exists: >-
      The first live mail after the matcher-recalibration deploy
      (2026-09-05T00:14:58Z) read leg A = 17 real candidates at HTTP 200 and
      leg B = HTTP 400; the client's union-or-raise discarded all 17 and the
      plane recorded `read_failed / candidates_considered=0` — a line
      indistinguishable AT THE PLANE from a genuinely empty pool, found only by
      a cross-service trace_id join (RECEIPT-matcher-recalibration-s11-landing
      §3.2). Concurrently the intake's only durable-loss floor (the dead-letter
      ledger) holds one live booking that ten receiver POSTs refused with 503,
      reaping 2026-09-10T05:28:46Z with no kind-named count and no walled
      retroactive path, while a retry-exhausted inbound mail runs to SendGrid's
      72h cliff with no floor at all (HANDOFF :1311-1318). CONSULT III named
      the law both violate: a reading that cannot name its own kind is still
      silence.
  shipped_definition:
    code_or_artifact_landed:
      - "WS-A-READ-KIND: partial-read degradation in fetch_lead_candidates (union-or-raise loop, services/email-booking-intake/src/email_booking_intake/activation_read_client.py:800-817 @ origin/main 52995b26) with the failed leg's identity + status kind carried on the V-5 `name_evidence_outcome` line (pipeline/stages/match_lead.py:212; read_failed branch :150-200) as a three-state field, INV-BASIS shape-compatible; two-sided tests partial != empty != failed; CONTRACT rev-8 text for the new field(s) (architect-owned — V-5 is FROZEN at rev 7); the W-3 historical read_failed measurement as a read-only artifact WITH denominator"
      - "WS-B-LOSS-FLOOR: a kind-named loss surface for undelivered bookings — receiver-refused / intake-fault / TTL-reaped (three-state; unknown != none) — replacing the kind-blind two-number level observation (ledger_level_observation.py:22-24) with a count a TTL-reap cannot silently leave; a durable floor for the inbound FAILED->502->72h path (handler.py:850-870); an alarm whose resting state is EARNED by a positive control, not vacuous"
      - "WS-C-RETRO: a walled, operator-worded, one-row-at-a-time retroactive re-drive of a PAST-DATED dead-letter row producing a TYPED terminal outcome {landed, refused-with-reason, held} stamped on the row and emitted countable — never automatic (terraform/services/email-booking-intake/dead_letter_level_surface.tf:201), never a silent drop; first fixture the live `bd875254…` row IF it survives to a build (EXTEND-TTL is the operator's word), else a synthetic row in a non-live ns"
      - "WS-D-ONE-TRAIN: ONE EBI image event carrying everything above onto all THREE functions (autom8-email-booking-intake / -contente-reconcile / -forwarding-nudge), peer-socket ping before merge, served==pinned==merge x3 read-back, rite-disjoint critic VERDICT at the assembled head, and the event-triggered arming watch for predicate legs (a) and (b)"
    user_visible_surface: >-
      When the booking-attribution plane shows a zero, it says WHICH zero:
      `no_candidates` (nothing there — both legs answered), a partial-read mark
      (one leg failed, its status named, the survivors were scored), or
      `read_failed` (nobody could look) — readable on the CloudWatch line with no
      trace join. When a booking the intake accepted never reaches its receiver,
      it is counted under its kind — receiver-refused / intake-fault /
      TTL-reaped — on a surface an operator reads directly, and one operator
      word can re-drive one past-dated row to a typed end. Product form:
      "when we show you a zero, we tell you whether it means nothing happened
      or we could not look."
  verified_realized_definition:
    user_visible_evidence:
      - "(a) A LIVE `name_evidence_outcome` line in which one read leg failed WITH its status carried and the surviving leg's candidates were scored — distinguishable AT THE PLANE without a cross-service trace join; two-sided: a genuinely empty pool with both legs OK still reads `no_candidates`, and a both-legs-failed read still reads `read_failed`"
      - "(b) A dead-lettered booking appears in a kind-named loss count (receiver-refused vs intake-fault vs TTL-reaped) that a resting-green alarm cannot mask, and ONE past-dated row re-driven on an operator word produces a TYPED terminal outcome (landed / refused-with-reason / held), never a silent drop"
      - "Rite-disjoint critic VERDICT at the assembled head: own-hands mutants for the three-way discrimination (partial/empty/failed) and for the loss kinds; three-evidence-leg (uncached re-run + own teeth + live surface observed directly)"
      - "NOT 'PRs merged' — merge events alone attest nothing; a served image is not a landed predicate"
    verification_method: telemetry
    verification_deadline: 2026-10-15  # ESTIMATIVE (Trigger Table row 6); operator spoke NO date; leg (a) waits on a LIVE leg failure recurring (W-1/W-3 unmeasured — UV-P-10); R-17 precedent "NO DATE, BAR ONLY" available as an operator word; Pythia adjusts at /shape; DONE IS A BAR
    rite_disjoint_attester: integrity-architect (dre, co-seated) — the seat that certified S-4 and authored the S-11 landing receipt whose §3.2 is this frame's origin signal (it has already read the plane cold); change-warden (dre) stays RESERVED for the parent's S-10 per HANDOFF H-7; ANY dre seat that BUILDS a workstream here may not attest it (critic-never-author); Pythia may re-seat at /shape within R1 (rite-disjoint from 10x-dev)
  attestation_status:
    inception: INSCRIBED   # on transplant to .know/telos/name-the-zero.md; MISSING until then (R-44)
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null
  receipt_grammar:
    per_item_file_line_anchors:
      - ".sos/wip/CONSULT-north-iii-2026-09-05.md:74-95 (Δ-3), :189-231 (north), :543-576 (§4.3 one frame), :634 and :638 (§5 rows 1 and 5), :798-811 (W-1/W-2/W-3 WEAK)"
      - ".sos/wip/dre/RECEIPT-matcher-recalibration-s11-landing.md:160-181 (the countable read_failed line), :348-428 (§3.2 the first live mail)"
      - ".sos/wip/HANDOFF-10x-dev-wave2-close-activation-loop-2026-09-01.md:1311-1318 (RESIDUAL-5 routed), :2268-2283 (PC-54 server half), :2312-2363 (PC-56 boundary, PC-57 dispatch)"
      - ".sos/wip/CARD-dead-letter-disposition-2026-09-04.md:13-30 (facts), :114-153 (final re-drive outcome; receiver identified)"
      - ".ledge/decisions/RATIFICATION-matcher-recalibration-sitting-2026-09-04.md:36-40 (RS-3 RETRO verbatim, RS-4), :55-62 (RS-12, RS-14, RS-16)"
      - ".sos/wip/CONTRACT-matcher-tier-tag-2026-09-03.md:156 (read_failed row), :252-271 (V-5 frozen set; winner_is_collider three-state)"
      - "autom8y origin/main 52995b26: .ledge/decisions/ADR-r3-record-restatement-primitive-2026-09-03.md:195-198, :242-248, :306, :712, :813, :1073; .ledge/reviews/CRIT-R3-delta-2026-09-04.md:398, :458, :741-747; .ledge/decisions/RATIFICATION-cutover-front-sitting-2026-09-02.md:97-100; .ledge/reviews/CRIT-S05-form-c-adversarial-2026-09-04.md:41-62; .ledge/reviews/RECEIPT-S05-organic-window-2026-09-04.md:90; .ledge/runbooks/RUNBOOK-ebi-op1-rollback-readiness-2026-07-17.md:48, :145-151; .know/telos/cutover-front.md:46-51"
    cross_stream_concurrence: false  # earned at close
    code_verbatim_match: false       # earned at close
```
