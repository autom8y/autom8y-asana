---
type: telos
initiative_slug: seam2-consumer-realization
authored_at: 2026-06-11T00:00:00Z
authored_by: hygiene station K3 (architect-enforcer) — Gate-A pre-position during the frozen soak window
rite: hygiene
schema_version: 1
code_truth_anchor: origin/main fa265ce1bde8be1d003f39501877d17fe600b0c0
---

# Telos Declaration — seam2-consumer-realization

> Pre-positioned 2026-06-11 per GLINT L5-1 (`.sos/wip/glints/GLINT-path-forward-post-keystone-2026-06-11.md:67`)
> so the 06-18 unlock chain (`CLEAR-READINESS-BUNDLE-telos-soak-2026-06-18-2026-06-11.md` §B.4.a)
> does not stall at telos-integrity Gate A. The `/frame` artifact supersedes the
> `frame_artifact` anchor below at dispatch time. NOTHING here rolls a task-def or touches the clock.

```yaml
telos:
  initiative_slug: seam2-consumer-realization

  inception_anchor:
    framed_at: "2026-06-11"  # pre-frame Gate-A authoring date; /frame (post-soak-clear) updates to its own date + artifact
    frame_artifact: ".ledge/decisions/CLEAR-READINESS-BUNDLE-telos-soak-2026-06-18-2026-06-11.md:56-58"  # §B.4.a SEAM-2 rebind — the inception record until /frame exists
    why_this_initiative_exists: >
      The receiver-side substrate is healed and (pending the 06-18 clock) STRONG-eligible,
      but the autom8 monolith's three consumers still bind entity=project and read
      $0/fossil economics. The eunomia ratified dispatch spec pre-commits the scope split
      (EUNOMIA-RATIFIED-STRONG-DISPATCH-SPEC-soak-clear-2026-06-18-2026-06-11.md §3):
      S2 (ad_reporting offer-entity) and S3 (payments/mrr congruence) are
      deferred-not-observed BY DESIGN, and "rounding the receiver-side STRONG up to
      telos-realized is the named failure mode." This initiative IS the un-deferral:
      rebind C1/C2/C3 so the dataframe-resolution-coherence five-signal can flip S2/S3
      from deferred-not-observed to OBSERVED-LIVE.

  shipped_definition:
    code_or_artifact_landed: []  # MISSING — nothing landed; populated by the post-clear rebind PRs (monolith-side edits + any receiver widen/rebind rulings)
    user_visible_surface: >
      [OPERATOR-RATIFIED 2026-06-12 — stakeholder interview R3-Q1: drafts blessed as-is;
      amendable at any /frame; user-sovereign per telos-integrity-ref Gate A.] The
      monolith's three consumers (C1 ad_reporting, C2 payments/mrr, C3 OfferHolders)
      surface entity-correct economics — offer 62/$79,485-class and unit sold-band —
      where they today surface project-entity $0/fossil values; dashboards and reports
      reading those consumers show real money, not zeros.

  verified_realized_definition:
    user_visible_evidence:
      # Per-consumer realization signals; sequencing C3 ≺ C1 ≺ C2 (cheapest-receiver-ready first).
      - "C3 (OfferHolders): monolith reads offer-holder economics through the receiver's already-served descriptor — receiver-side requires ZERO work: OfferHolder EntityDescriptor primary_project_gid='1210679066066870' at src/autom8_asana/core/entity_registry.py:836; OFFER_HOLDER_PROJECT at src/autom8_asana/core/project_registry.py:29 and :250; PRIMARY_PROJECT_GID at src/autom8_asana/models/business/offer.py:296 (ALL re-verified at fa265ce1 by this station). Realization = C3 monolith call site rebound + live read returns offer-holder rows, not project-entity fossil."
      - "C1 (ad_reporting): five-signal S2 flips deferred-not-observed → OBSERVED-LIVE — ad_reporting returns offer-entity economics (62/$79,485-class over the ACTIVE subset), never project-entity zero-fill (scope split per EUNOMIA-RATIFIED-STRONG-DISPATCH-SPEC §3)."
      - "C2 (payments/mrr): five-signal S3 flips deferred-not-observed → OBSERVED-LIVE — payments/mrr congruent with the warmed denominator (62-row offer class) and the unit sold-band; HARD-GATED on the unit-economics population work (existing substrate: worktree seam2-unit-econ, GLINT L1-1 — rebase onto fa265ce1 is the freeze-week prerequisite)."
      - "fallback-flip retired: legacy_fallback_enabled is a CODE default (src/autom8_asana/dataframes/storage.py:352, `legacy_fallback_enabled: bool = True`, re-verified at fa265ce1) — retirement is a code change + deploy, sequenced post-clear per CLEAR bundle §B.4.a; realized when the flag default flips and dual-read is retired without consumer regression."
    verification_method: in-anger-dogfood
    verification_deadline: "2026-07-03"  # OPERATOR-RATIFIED 2026-06-12 (interview R3-Q2: realization-bound = clear+14d; clear co-signed 2026-06-19T09:02:05Z → 07-03). DEADLINE-MISSED: as of 2026-07-07 (A1 reconcile) this date is 4 days past with nothing landed on main. Disposition = PENDING-B1-redundancy-probe (crusade Track B, data-analyst rite, operator-gated). DO NOT silently re-date. Redundancy signal: operator-plane offer_level_stats buildout (2026-06-29 reorientation) may obviate the monolith rebind — the B1 probe decides retire-vs-build. No retire/build ruling authored here (that is B1's leg).
    rite_disjoint_attester: "eunomia (rite-disjoint per telos-integrity-ref §2 R1 binding; same attester pre-cast for the parent telos five-signal)"

  attestation_status:
    inception: INSCRIBED
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null  # the S2/S3-deferred pre-commitment lives in EUNOMIA-RATIFIED-STRONG-DISPATCH-SPEC §3 — context, not a VERDICT on THIS initiative

  receipt_grammar:
    per_item_file_line_anchors:
      - "src/autom8_asana/core/entity_registry.py:836"
      - "src/autom8_asana/core/project_registry.py:29"
      - "src/autom8_asana/core/project_registry.py:250"
      - "src/autom8_asana/models/business/offer.py:296"
      - "src/autom8_asana/dataframes/storage.py:352"
      - ".ledge/decisions/EUNOMIA-RATIFIED-STRONG-DISPATCH-SPEC-soak-clear-2026-06-18-2026-06-11.md:58-66"
      - ".sos/wip/glints/GLINT-path-forward-post-keystone-2026-06-11.md:31-34"
    cross_stream_concurrence: false
    code_verbatim_match: true  # every src anchor above re-fired via git grep/show against origin/main fa265ce1 by the authoring station this pass
```

## Sequencing (load-bearing, carried into the /frame)

**C3 ≺ C1 ≺ C2.** C3 is receiver-ready at fa265ce1 (all three anchors above re-verified —
monolith-side rebind only, cheapest-first per GLINT L1-4). C1 follows (offer substrate READY:
62/$79,485 per CLEAR bundle §B.4.a). C2 lands LAST — gated on the seam2 unit-economics
population work (dirty worktree `seam2-unit-econ`, base `e686ba06`, 8+ PRs behind; GLINT L1-1
routes the rebase NOW, freeze-safe).

Cross-cutting dependency: a rebound consumer missing `offer_id` exit-1s exactly as
`business_offers` does today — **FM-5 (`.know/telos/fm5-column-fidelity.md`) is a precondition
rider** per OPERATOR-RULING-fm5 §TELOS-riders. The widen-vs-rebind ruling per consumer is
FM-5 design-lock territory intersecting this initiative (SPEC-fm5 §Layer-1 field semantics).

## DEFER / pending

| Item | Status |
|---|---|
| user_visible_surface final wording | RATIFIED 2026-06-12 (interview R3-Q1: draft blessed; amendable at /frame) |
| verification_deadline real date | RATIFIED 2026-06-12: 2026-07-03 (clear+14d; clear = 06-19T09:02:05Z) |
| seam2-unit-econ worktree rebase onto fa265ce1 | OPEN — freeze-week prerequisite (GLINT L1-1) |
| /frame + /shape | post-soak-clear per CLEAR bundle §B.4; this declaration satisfies Gate A |

## Evidence Grade

`[STRUCTURAL | MODERATE]` — pre-frame declaration authored by the hygiene station
(self-ref ceiling per `self-ref-evidence-grade-rule`); code anchors are first-party re-verified
at fa265ce1; realization attestation belongs to eunomia (rite-disjoint) at close.
