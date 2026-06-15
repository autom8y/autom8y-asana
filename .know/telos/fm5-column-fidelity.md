---
type: telos
initiative_slug: fm5-column-fidelity
authored_at: 2026-06-11T00:00:00Z
authored_by: hygiene station K3 (architect-enforcer) — Gate-A pre-position during the frozen soak window
rite: hygiene
schema_version: 1
code_truth_anchor: origin/main fa265ce1bde8be1d003f39501877d17fe600b0c0
---

# Telos Declaration — fm5-column-fidelity

> Pre-positioned 2026-06-11 per GLINT L5-1 so RULING 3's post-clear
> `/frame g2-column-fidelity-contract` does not stall at telos-integrity Gate A.
> Binding inputs inherited VERBATIM per the ruling's own binding clause:
> `.ledge/decisions/OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md` (RULINGS 1–3) +
> `.ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md` (the two-layer shape).
> Ordering pin: `.ledge/decisions/ORDERING-PIN-114-before-fm5-design-lock-2026-06-11.md`.

```yaml
telos:
  initiative_slug: fm5-column-fidelity

  inception_anchor:
    framed_at: "2026-06-11"  # pre-frame Gate-A authoring date; the post-clear /frame updates to its own date + artifact
    frame_artifact: ".ledge/decisions/OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md:25-39"  # RULINGS 1–3 — the inception record until /frame exists
    why_this_initiative_exists: >
      /v1/query is column-blind by documented shortcut, not defect: the S-07/PG-02
      minimal-schema deferral is inscribed in code at
      src/autom8_asana/core/entity_registry.py:881 ("T1.3 — Shortcut S-07 invoked:
      minimal schema (3 columns beyond base)" — re-verified at fa265ce1; the ruling
      cited :885, the comment sits at :881 at this sha) with PG-02 deferral markers
      at :901 and :939. The deferred bill arrives on fleet re-enable: a consumer
      indexing a never-selected column (the offer_id Utf8↔Int64 class) gets a silent
      null or a prod KeyError instead of a typed refusal. FM-5 converts consumer
      column requirements into a DECLARED two-layer contract so a missing or
      never-selected column is a TYPED REFUSAL, never a silent narrow frame.

  shipped_definition:
    code_or_artifact_landed: []  # MISSING — src/autom8_asana/dataframes/contracts/ does not exist at fa265ce1 (probe receipt in the ordering pin); the home arrives with #114
    user_visible_surface: >
      [OPERATOR-RATIFIED 2026-06-12 — interview R3-Q1: draft blessed as-is; amendable
      at /frame.] A consumer whose declared required column cannot be served receives a loud,
      typed contract-incomplete signal (the column analogue of
      honest_contract_complete=False) instead of silently-null economics; consumers
      that declare nothing keep today's behavior (additive, two-way door per
      SPEC-fm5 §Layer-2).

  verified_realized_definition:
    user_visible_evidence:
      - "The 3 consumers' manifests enforced: the vendored consumer_column_requirements manifest (SPEC-fm5 §Layer-1; monolith-owned, vendored with a freshness guard per the reversed SNC gen.json pattern) drives FieldContract-SSOT derivation, and a consumer entry whose column the shape cannot serve is a build-time RED, not a prod KeyError (SPEC-fm5 §Layer-1 Derivation (iii))."
      - "honest_contract_complete carries column-completeness — the One-Gate graft, NOT a sibling signal path (GLINT L1-2): the derivation site re-verified at fa265ce1 lives at src/autom8_asana/query/engine.py:247-278 (comment block :247-252 'S-01 (unconditional True) is REFUSED'; derive call :253; honest_empty :266; result field :278) with canonical derivation at :527 _derive_honest_contract_complete and the manifest-side derivation at src/autom8_asana/dataframes/section_persistence.py:252. NOTE: the GLINT's 'query/engine.py' resolves to src/autom8_asana/query/engine.py — NOT dataframes/query/ (that path does not exist at fa265ce1)."
      - "Wire layer live: /v1/query/*/rows accepts optional required_columns; all-present serves with response-metadata column_manifest; any missing/unservable yields the typed contract-incomplete signal (SPEC-fm5 §Layer-2), producer-first sequencing so the wire field never hard-fails a live consumer."
      - "offer_id + project_gid land as the contract's first two INSTANCES, never orphan point-fixes (operator ruling, ratified blend item c)."
    verification_method: in-anger-dogfood
    verification_deadline: "2026-07-31"  # OPERATOR-RATIFIED 2026-06-12 (interview R3-Q2: realization-bound RULE = design-lock+21d, binding; 07-31 is the nominal outer bound, recalculated when design-lock lands post-clear per RULING 3)
    rite_disjoint_attester: "eunomia (rite-disjoint per telos-integrity-ref §2 R1 binding)"

  attestation_status:
    inception: INSCRIBED
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null

  receipt_grammar:
    per_item_file_line_anchors:
      - "src/autom8_asana/core/entity_registry.py:881"
      - "src/autom8_asana/core/entity_registry.py:901"
      - "src/autom8_asana/core/entity_registry.py:939"
      - "src/autom8_asana/query/engine.py:247"
      - "src/autom8_asana/query/engine.py:253"
      - "src/autom8_asana/query/engine.py:278"
      - "src/autom8_asana/query/engine.py:527"
      - "src/autom8_asana/dataframes/section_persistence.py:252"
      - ".ledge/decisions/OPERATOR-RULING-fm5-scope-and-sequencing-2026-06-11.md:25-39"
      - ".ledge/specs/SPEC-fm5-consumer-column-declaration-shape-2026-06-11.md:21-98"
    cross_stream_concurrence: false
    code_verbatim_match: true  # every src anchor re-fired via git grep/show against origin/main fa265ce1 by the authoring station this pass
```

## Gates (load-bearing, carried into the /frame)

1. **Design-lock is OPERATOR-HELD**: RULING 1 (contract-driven subset, NOT eager 30-column
   parity) must be RE-CONFIRMED at design-lock against the actual declared union — the frame
   must surface it explicitly (ruling's own words).
2. **Derivation GATES on #114**: the FieldContract SSOT home
   (`src/autom8_asana/dataframes/contracts/field_contract_maps.py`) does not exist at
   fa265ce1 — it is carried by open PR #114 (`fpc/phase1-dtype-parity`; files verified via
   `gh pr view 114 --json files`). Full pin + probe receipts:
   `.ledge/decisions/ORDERING-PIN-114-before-fm5-design-lock-2026-06-11.md`.
3. **Deploy waits for soak-clear** (RULING 3): any schema-selection deploy resets the clock.
   Sequence: #127 release seam + EXP-1 + re-anchor landed FIRST, then post-clear
   `/10x` → `/frame g2-column-fidelity-contract` → PV before design-lock (PV re-pulls live
   with SVR receipts, never inherits) → `/shape`.

## Telos riders (inherited verbatim from the operator ruling)

FM-5 is a PRECONDITION for: (1) honest S7 — retiring the monolith's legacy get_df fallback
on a column-blind contract converts silent-degrade into a HARD outage for 3 consumers
(monolith S7 DEPENDS-ON our FM-5); (2) SEAM-2 rebind (`.know/telos/seam2-consumer-realization.md`)
— a rebound consumer missing `offer_id` exit-1s exactly as `business_offers` does today.
The five-signal GROWS: a representative consumer frame must carry its full declared
required-column set, populated.

## DEFER / pending

| Item | Status |
|---|---|
| user_visible_surface final wording | RATIFIED 2026-06-12 (interview R3-Q1: draft blessed; amendable at /frame) |
| verification_deadline real date | RATIFIED 2026-06-12: rule = design-lock+21d (outer bound 07-31) |
| widen-vs-rebind ruling per consumer | design-lock; intersects SEAM-2 (SPEC-fm5 §Out-of-scope) |
| monolith manifest hand-back (file path + sha) | cross-repo round-trip step 1 (SPEC-fm5 §Round-trip) |

## Evidence Grade

`[STRUCTURAL | MODERATE]` — pre-frame declaration, hygiene-station self-ref ceiling;
code anchors first-party re-verified at fa265ce1; realization attestation is eunomia's at close.
