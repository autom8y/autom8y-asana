---
type: telos
initiative: matcher-recalibration
status: INSCRIBED (inception) — verification_deadline ESTIMATIVE (frame Trigger Table row 6; operator spoke no date; adjustable at /shape)
created: 2026-09-03
inscribed_by: >
  main thread, WAVE-2 dispatch session. The telos block below is transplanted
  VERBATIM from the frame's §2 (authored by myron under the operator's /frame
  charge; mission and predicate in the operator's own words from the 2026-09-03
  ruling sitting). Policy of record: .ledge/decisions/RULING-matcher-recalibration-and-landed-definition-2026-09-03.md (merged autom8y-asana#403, 29bc55ed).
source: .sos/wip/frames/matcher-recalibration.md §2 (transplanted verbatim)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
frame: .sos/wip/frames/matcher-recalibration.md
shape: .sos/wip/frames/matcher-recalibration.shape.md (authoring in flight at inscription time)
parent_wave: close-the-activation-loop (S-4b successor initiative)
---

# Telos — matcher-recalibration (inscribed 2026-09-03)

**Gate A closed by inscription.** Realization predicate (operator's words, ruling
sitting 2026-09-03): every ad-driven booking that arrives with minimal patient
info is attributed to its originating lead — tiered by evidence, flagged when wrong; restated with provenance once the record-correction primitive lands, and never silently dropped. Verified-realized = the change is adversarially
certified by a rite-disjoint critic AND at least one organic minimal-info booking
has been attributed by the new tiers and spot-confirmed correct — NOT "PRs
merged", NOT self-attested green. DONE IS A BAR, NOT A DATE.

```yaml
telos:
  initiative_slug: matcher-recalibration
  inception_anchor:
    framed_at: 2026-09-03
    frame_artifact: .sos/wip/frames/matcher-recalibration.md:31
    why_this_initiative_exists: >-
      The shipped S-4 matcher (autom8y #1845 ba7def24, live 2026-09-02T15:03Z)
      was calibrated precision-first by a dispatcher/critic choice (F-B1 cure
      (a)) that the operator never ratified and that inverts the operator's
      stated priority: a missed attributable booking is costlier than a
      correctable mis-attribution. The 2026-09-03 sitting (ruling R-M1..R-M9)
      re-based the policy; this initiative realizes it.
  shipped_definition:
    code_or_artifact_landed:
      - "W-CAL calibration artifact (replay of phone-matched bookings, per shape x window; sets every threshold BEFORE landing, R-M8)"
      - "W-ROUTE: FULL_NAME-no-phone routed to the matcher (today excluded at services/email-booking-intake/src/email_booking_intake/pipeline/stages/match_lead.py:338-347 @ origin/main b80a9687); per-shape window (today single-valued at activation_read_client.py:483 / config.py:164)"
      - "W-TIER: HIGH silent / WEAK tagged+counted+flagged-when-wrong bind (matched_weak label absent from metrics.py:325 outcome enum today) / thin-evidence park; floor at name_evidence.py:295 relaxed per R-M3"
      - "W-RECENCY: decisive-recency binds, close-recency parks (today structurally impossible: name_evidence.py:178-183 RECENCY_MAX_BONUS 0.5 < AMBIGUITY_EPSILON 1.0)"
      - "W-FLAG: contradiction flag on a WEAK bind, never auto-undo (no surface exists today; R-15)"
      - "W-COUNT: exposable per-shape x tier outcome counts as a data surface (no consumer in ~/code/a8/contente/dashboard_ui today; R-19)"
      - "W-CERT: rite-disjoint critic verdict at the ASSEMBLED head (.sos/wip/dre/VERDICT-matcher-recalibration-*.md)"
      - "W-LAND: one EBI image event on all THREE lambdas (intake / contente-reconcile / forwarding-nudge), pinged to the peer socket pre-merge"
    user_visible_surface: >-
      An ad-driven booking that arrives with only a name or initials is
      attributed to its lead: strong evidence binds silently (HIGH), weaker
      evidence binds tagged, counted and flagged when wrong; restated with provenance once the record-correction primitive lands (WEAK),
      thin evidence parks to a human — and per-office match outcomes per shape
      and tier are readable by the agency view as a data surface.
  verified_realized_definition:
    user_visible_evidence:
      - "Rite-disjoint critic VERDICT at the assembled head: DELTA-CONCUR or PASS, own-hands mutants, the S-4 mutant corpus re-fired (three-evidence-leg: uncached re-run + own teeth + live surface)"
      - "At least ONE organic (not synthetic, not replayed) minimal-info booking attributed by the new tiers with a receipt {booking, lead_id, shape, tier, score, window} — spot-confirmed correct by a human (operator or ops), the confirmation itself receipted"
      - "The per-shape x tier outcome counts read back (read-after-write) from the exposable surface with that booking in the count — N>=1, not a served zero"
      - "No silent drop: every minimal-info booking in the post-landing window resolves to exactly one of {HIGH, WEAK, PARK} with a typed receipt (conservation check per WATCH §1.1 re-run at the new head)"
    verification_method: cross-stream-corroboration
    verification_deadline: 2026-10-15  # ESTIMATIVE (Trigger Table row 6; operator spoke NO date; DONE IS A BAR) — adjusted at /shape D-2: ~09-09 earliest landing + ~2wk for a qualifying organic arrival at ~0.5/day
    rite_disjoint_attester: integrity-architect (dre, co-seated) — the seat that certified S-4 (VERDICT-close-the-activation-loop-s4.md:20-21); change-warden stays RESERVED for the parent's S-10 per handoff H-7 (:53-56); Pythia may re-seat at /shape within R1 (rite-disjoint from 10x-dev)
  attestation_status:
    inception: INSCRIBED
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null
  receipt_grammar:
    per_item_file_line_anchors:
      - ".ledge/decisions/RULING-matcher-recalibration-and-landed-definition-2026-09-03.md:36-72 (R-M1..R-M9)"
      - ".ledge/decisions/RULING-matcher-recalibration-and-landed-definition-2026-09-03.md:76-91 (R-L1..R-L6)"
      - ".sos/wip/SPIKE-legacy-initials-lead-matching.md:90-131 (matcher design of record + refusal doctrine)"
      - ".sos/wip/dre/VERDICT-close-the-activation-loop-s4.md:315-394 (F-B1, superseded by R-M3) and :673-776 (§8.1 floor mechanics, R-1 residue)"
      - ".sos/wip/WATCH-ebi-activation-train-2026-09-02.md:426-464 (§3 arming events, inherited by citation)"
    cross_stream_concurrence: false  # earned at close
    code_verbatim_match: false       # earned at close
```
