---
type: telos
initiative_slug: gfr-dynvocab
authored_at: 2026-06-25T00:00:00Z
authored_by: main-thread (Claude) at OPERATOR DIRECTION — drafted for ratification; user-sovereign per telos-integrity-ref §3 Gate-A
ratified_by: operator (Tom Tenuta) — countersigned 2026-06-25
rite: 10x-dev
schema_version: 1
code_truth_anchor: feat/gfr-engine 2092f771 atop origin/main 376e1edd
ratification_status: RATIFIED 2026-06-25 (operator countersign; both [OPERATOR-SET] fields approved as-drafted)
---

# Telos Declaration — gfr-dynvocab (Dynamic Field Vocabulary & Coherence)

> **RATIFIED 2026-06-25** — operator (Tom Tenuta) countersigned. Drafted at operator direction; user-sovereign per telos-integrity-ref §3 Gate-A and now ratified. The two **[OPERATOR-SET]** fields (`verification_deadline` = 2026-07-23, `rite_disjoint_attester` = review-rite external critic) were **approved as-drafted**. Gate-A is CLOSED for `/frame gfr-dynvocab`. Amendable at any `/frame`.

```yaml
telos:
  initiative_slug: gfr-dynvocab

  inception_anchor:
    framed_at: "2026-06-25"
    frame_artifact: ".ledge/specs/gfr-dynvocab-alignment-brief.md"  # accepted; + rnd inquisition .ledge/spikes/gfr-dynvocab-{recon,integration,prototype-findings,moonshot}.md + handoff gfr-dynvocab-rnd-to-10x-handoff.md
    why_this_initiative_exists: >
      GFR's "open-by-declaration / dynamic" promise is silently bounded by a hand-curated
      dataframe-schema SUBSET of each entity's real fields — the asset_id smell (asset_id is on
      the Offer task model at offer.py:144 but absent from the Offer dataframe schema, so GFR
      cannot resolve it). Drift is systemic across every entity. This sibling initiative makes the
      vocabulary reflect what the entity ACTUALLY carries — a typed certified core + a
      heuristically-typed dynamic tail — and governs model<->schema coherence so the gap cannot
      silently recur, all strictly-additive to (never regressing) the STRONG-certified identity spine.

  shipped_definition:
    code_or_artifact_landed:  # LANDED 2026-06-25 — feat/gfr-engine squash-merged to main e49c30d7 (PR #158)
      - "resolution/gfr/{engine,guard,posture,models,entry,errors,truth_source}.py + dynvocab.py + dynvocab_overrides.py + planner.py (the NAME-keyed dynamic tail + Option-A entry-scoped partition + asset_id→SET override)"
      - "dataframes/models/registry.py (model↔schema drift gate, warn-first, UNANALYZABLE/UNPAIRED states)"
      - "models/business/fields.py (STANDARD_TASK_OPT_FIELDS += custom_fields.date_value — live date hole closed)"
    user_visible_surface: >
      [OPERATOR-SET — draft] resolve(gid, fields) resolves ANY field the entity's task carries —
      not just the hand-curated schema columns — heuristically typed from Asana cf-type metadata,
      with a per-field typing-origin provenance tag; asset_id resolves as a SET; a genuinely-absent
      field returns a truthful unknown.

  verified_realized_definition:
    user_visible_evidence:
      - "LIVE: resolve(<real entity gid>, [asset_id]) returns a SET via the whitespace-agnostic comma-split override, off the already-hydrated entry task (HYP-1 free-tail confirmed LIVE against real Asana — the GAP-1 build probe), asserted on a positively-selected real entity (e.g. canary b167331c-...)."
      - "GENERIC: the same heuristic-tail mechanism resolves arbitrary custom fields across >=2 EntityTypes (e.g. Offer + Business) with NO entity-special-casing; cf-type coercion table (text/number/enum/multi_enum/date/people) + per-field override registry keyed by canonical field NAME (NameNormalizer.normalize — operator NAME-keying correction 2026-06-25; cf gid is a runtime intra-task value handle only, never a key)."
      - "GOVERNED-STRICT: a requested-but-absent field returns a truthful UnresolvedError(unknown-field) backed by the manifest (the task's cf keys); UNKNOWN is distinguishable from present-but-null."
      - "TYPING-PROVENANCE: every field carries typing-origin {schema|heuristic|override|absent|fallback} + cf_type alongside {value,status,source,as_of}."
      - "COHERENCE: a model<->schema drift gate FAILS (RED) when an entity's task-model field set diverges from its schema/vocabulary coverage without an explicit exclusion (the asset_id class of gap cannot silently recur)."
      - "SPINE UNREGRESSED: the 105 certified GFR tests stay GREEN; company_id stays on the certified gid-exact frame path; the GAP-1 assert_rows_tenant_identity guard still fires RED-on-bypass. Strictly-additive proven by the regression gate."
    verification_method: in-anger-dogfood
    verification_deadline: "2026-07-23"  # [OPERATOR-SET] proposed placeholder; drives Naxos TELOS_OVERDUE — set the real bound
    rite_disjoint_attester: "review-rite external critic (rite-disjoint from the 10x-dev author; binding attester for the moonshot Future-4 fleet-coherence dissent — mirrors the parent GFR R1 binding). [OPERATOR-SET] — confirm."

  attestation_status:
    inception: RATIFIED       # operator countersigned 2026-06-25
    shipped: LANDED           # merged to main e49c30d7 (PR #158), 2026-06-25; CI all-required GREEN
    verified_realized: ATTESTED   # rite-disjoint review critic (disjoint from 10x-dev author AND iris), 2026-06-25 — own live re-resolve of OFFER gid 1209877818531716 → SET; deadline 2026-07-23 met early. Verdict: .ledge/reviews/gfr-dynvocab-verified-realized-verdict.md
    last_eunomia_advisory: null

  receipt_grammar:
    per_item_file_line_anchors:
      - "src/autom8_asana/models/business/offer.py:144"                 # asset_id on the task model (the smell)
      - "src/autom8_asana/dataframes/resolver/default.py:234-287"       # _extract_raw_value cf-type match-table (~80% in-tree)
      - "src/autom8_asana/models/business/fields.py:232-251"            # STANDARD_TASK_OPT_FIELDS pulls all cf + value subfields (HYP-1)
      - "src/autom8_asana/models/business/hydration.py:283"             # entry fetch uses the full opt-fields
      - "src/autom8_asana/resolution/gfr/engine.py:230-235"            # the no-identity-path stub the tail branch replaces
      - "src/autom8_asana/core/entity_registry.py:136"                  # custom_field_resolver_class_path seam
    cross_stream_concurrence: true    # verified_realized=ATTESTED; review-rite disjoint critic concurred 2026-06-25 (own live re-resolve + mutation re-fire + transform re-derivation)
    code_verbatim_match: false        # anchors carried from the rnd inquisition; 10x-dev re-verifies at build
```

## Carried (from the rnd inquisition)

- **Feasibility PROVEN @ MODERATE** (prototype: asset_id→set, HYP-1/HYP-2, ≥2-EntityType generality, governed-strict). STRONG paradigm-lock + this telos's verified_realized require the **rite-disjoint review-rite critic**.
- **Scoped dissent (moonshot Future-4):** fleet-scale coherence wants a cf-gid **contract registry**, not per-repo drift-gate alone — DEFER-registered, escalate when a 2nd service binds the drift class.
- **HARD constraint:** schema **codegen-from-model reverses ADR-S4-001** (one-way door) — the drift **gate** (warn-first) is the recommended mechanism, NOT codegen.
- **Strictly-additive:** the certified spine (CERT-1 guard, CERT-3 round-trip, 105 tests) is the inviolable regression gate; this initiative must never re-open it.

## Evidence Grade

`[STRUCTURAL | MODERATE]` — pre-build declaration; `self_ref_cap: MODERATE`. Feasibility evidence is first-party (prototype runs); realization attestation belongs to the rite-disjoint review-rite critic at close, not the author.
