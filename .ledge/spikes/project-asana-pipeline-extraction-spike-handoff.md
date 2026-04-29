---
type: handoff
status: accepted
initiative: project-asana-pipeline-extraction
station: S5
specialist: tech-transfer
related_spike: cascade-vs-join
role: verdict-carrier
outgoing_rite: rnd
incoming_rite: 10x-dev
session_id: session-20260427-232025-634f0913
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
created: 2026-04-27
phase: 0
verdict_authority: S5 (tech-transfer) — pinned by inquisition orchestration §1
upstream_artifacts:
  - .ledge/spikes/SCOUT-cascade-vs-join.md
  - .ledge/spikes/INTEGRATE-cascade-pathA.md
  - .ledge/spikes/INTEGRATE-pathB-and-C5.md
  - .ledge/spikes/PROTO-cascade-vs-join.md
  - .ledge/spikes/MOONSHOT-cascade-vs-join.md
frame: .sos/wip/frames/project-asana-pipeline-extraction.md
shape: .sos/wip/frames/project-asana-pipeline-extraction.shape.md
workflow: .sos/wip/frames/project-asana-pipeline-extraction.workflow.md
inquisition_plan: .sos/wip/inquisitions/cascade-vs-join-spike-orchestration.md
polars_version_tested: "1.38.1"
---

# HANDOFF — Cascade-vs-Join Spike Verdict Carrier (Station S5)

## §1 Telos Echo

This artifact is the binding spike-to-Phase-1 verdict carrier. The throughline (verbatim, workflow §1.1):

> **Vince (and every future PAT or S2S caller) can produce a parameterized account-grain export of any business entity via a dual-mount endpoint without custom scripting; Phase 1 verifies against Vince's original Reactivation+Outreach CSV ask by 2026-05-11; Phase 2 cross-entity adjudication is deferred behind a spike-bounded architectural commitment.**

Phase 1 ships single-entity export. This artifact adjudicates the Phase 2 cascade-vs-join altitude and stamps the constraints Phase 1 must respect to preserve that adjudication.

## §2 telos_pulse_carrier (workflow §4.2)

```yaml
telos_pulse_carrier:
  outgoing_rite: rnd
  incoming_rite: 10x-dev
  initiative_slug: project-asana-pipeline-extraction
  inception_anchor:
    why_this_initiative_exists: |
      A coworker's ad-hoc request to extract actionable account lists from
      Reactivation and Outreach pipelines has exposed a gap in the
      autom8y-asana service: there is no first-class BI export surface, and
      any response today would be a one-off script with zero reusability.
      This initiative transitions from observation (Iris snapshot) to
      repeatable, account-grain, CSV-capable data extraction codified in
      the service's dataframe layer.
    framed_at: "2026-04-27"
    frame_artifact: ".sos/wip/frames/project-asana-pipeline-extraction.md:1"
  throughline_one_liner: |
    Vince (and every future PAT or S2S caller) can produce a parameterized
    account-grain export of any business entity via a dual-mount endpoint
    without custom scripting; Phase 1 verifies against Vince's original
    Reactivation+Outreach CSV ask by 2026-05-11.
  verification_deadline: "2026-05-11"
  pulse_carrier_authoring_specialist: tech-transfer (S5)
  shipped_definition_at_handoff:
    code_or_artifact_landed:
      - ".ledge/spikes/SCOUT-cascade-vs-join.md (S1, 9-candidate matrix)"
      - ".ledge/spikes/INTEGRATE-cascade-pathA.md (S2a, Path A cartography)"
      - ".ledge/spikes/INTEGRATE-pathB-and-C5.md (S2b, B+C5 cartography)"
      - ".ledge/spikes/PROTO-cascade-vs-join.md (S3, empirical .explain() evidence)"
      - ".ledge/spikes/MOONSHOT-cascade-vs-join.md (S4, stress + S3 critic-substitution)"
      - ".ledge/spikes/project-asana-pipeline-extraction-spike-handoff.md (S5, this artifact)"
    user_visible_surface: |
      No production code shipped (spike rite). The shipped surface is the
      verdict carrier (§3 below) that binds Phase 1 architecture choices
      and Phase 2 design space.
  outstanding_invariants:
    - "Phase 2 non-foreclosure: Phase 1 implementation MUST NOT touch query/join.py, query/compiler.py filter-pushdown logic, or query/engine.py join execution paths."
    - "SCAR-005/006 null-flag transparency: identity_complete column on every output row with null component of canonical (office_phone, vertical) key."
    - "Dual-mount auth pattern preservation per FleetQuery precedent at main.py:414-415."
    - "Single-entity scope for Phase 1: ExportRequest contract MUST NOT include cross-entity join semantics."
    - "LEFT-OUTER semantic preservation: any future Phase 2 C5 path MUST defend against silent LEFT-to-INNER rewrite (see §3 verdict and §6 phase_1_constraints)."
  outgoing_potnia_attestation:
    pulse_intact: true
    pulse_intact_evidence: |
      Telos restated verbatim at S1 §1, S2a §1, S2b §1, S3 §1, S4 §1, and
      S5 §1 (this artifact). Critic-substitution chain executed: S3 cross-
      checked by S4 with explicit CONCUR/DIVERGE attestation per
      MOONSHOT-cascade-vs-join.md §4. All five station artifacts cite
      file:line evidence anchors per authoritative-source-integrity.
    cassandra_filings_open: []
  pulse_reroot_ritual_for_incoming_potnia: |
    Before dispatching any Phase 1 specialist, the 10x-dev Potnia MUST:
    1. Read this telos_pulse_carrier block in full (do not skim)
    2. Read §3 verdict block in full
    3. Read §6 phase_1_constraints in full (these bind Sprint 1 and Sprint 2)
    4. Restate the throughline_one_liner verbatim in Sprint 1 dispatch opening
    5. Cite this handoff artifact path:line as the inception anchor for
       requirements-analyst (Sprint 1) and architect (Sprint 2)
    6. Stamp incoming_potnia_acknowledgement (workflow §4.2) before opening Sprint 1
  incoming_potnia_acknowledgement:
    loaded_at: null  # incoming Potnia stamps on read
    pulse_restated: null  # incoming Potnia paraphrases inception_anchor here
    blocking_questions_for_incoming_rite: []
```

## §3 verdict (machine-parseable; orchestration §5.2 schema)

```yaml
verdict:
  decision: hybrid
  rationale_summary: |
    C5 (Polars LazyFrame predicate-pushdown delegation) is the Phase 2
    primary path for in-process entity joins: S3 .explain() empirically
    confirms predicate pushdown over equality joins (PROTO §5
    LL.230-247); S2b cartography puts effort at 5-9d med-high vs Path B's
    8.5-13.5d med-low (INTEGRATE-pathB-and-C5 §4 vs §8); the warmed-cache
    invariant is preserved (S4 Claim 5 CONCUR, MOONSHOT §4 LL.431-468);
    reversibility is the highest of the three live paths (MOONSHOT §3
    LL.273-282). Path B (join-engine pushdown) is reserved for the
    cross-service trajectory: SC-3 (data-service joins) is the unique
    SURVIVES verdict for B and the BREAKS verdict for C5 (MOONSHOT §2
    LL.130-165). Path A (cascade-extension) is NOT selected as the Phase 2
    primary because per-shape recurring cost (~26-31 LOC per cross-entity
    query shape per S3 §9) becomes net-debt at >=2 cross-entity shapes,
    and SC-2/SC-3 stress shows DEGRADES/BREAKS verdicts. The boundary
    predicate that classifies a query as cascade vs C5 vs B is given
    below; the LEFT-to-INNER divergence (S4 Claim 2 DIVERGE) is resolved
    via an engine-side how-preservation guard.

  hybrid_split:
    cascade_queries:
      shape: |
        Single-entity predicates over fields ALREADY cascaded onto the
        primary entity at warmup (e.g., contact.office_phone,
        contact.vertical, process.{cascade fields}). NO new cascade
        fields are added in Phase 1 or Phase 2 unless explicitly
        triggered by the boundary_predicate below.
      example: |
        See §5 worked-example #1 (Vince's Reactivation+Outreach CSV ask).
        Predicate: section IN {ACTIVE_SECTIONS}; primary entity: process;
        all relevant columns already present on warmed process schema.
        Engine path: existing eager engine.py:159-161 filter, unchanged.
    join_queries:
      shape: |
        Cross-entity predicates over IN-PROCESS entity joins
        (JoinSpec.source != "data-service") with EQUALITY operators
        and either (a) how="inner" explicitly OR (b) how="left" with
        LEFT-preservation guard active (see boundary_predicate below).
        These dispatch through C5 (Polars LazyFrame chain at engine.py:140-178
        with predicate pushdown delegated to the optimizer).
      example: |
        See §5 worked-example #2 ("contacts whose parent offer is in an
        ACTIVE OFFER section"). Predicate spans contact + offer schemas;
        engine constructs LazyFrame chain; Polars optimizer pushes
        offer.section predicate onto RIGHT PLAN before join.
    boundary_predicate: |
      A query is classified as follows (this rule lives in the Phase 2
      engine dispatch, NOT in Phase 1):

      1. IF every field in the predicate AST is resolvable against the
         primary entity's warmed schema (PredicateCompiler does not raise
         UnknownFieldError per compiler.py:220-225):
           --> CASCADE-PATH (existing eager engine, no change)

      2. ELIF the predicate references a field resolvable against an
         entity reachable via JoinSpec with source="entity"
         (in-process), AND the predicate's operator is in
         {EQ, NE, IN, NOT_IN, GT, GTE, LT, LTE, BETWEEN}, AND
         (request.join.how == "inner" OR LEFT-preservation guard active):
           --> C5-PATH (Polars LazyFrame chain; optimizer pushdown)

      3. ELIF the predicate references a field on a JoinSpec target with
         source="data-service" (cross-service), OR the operator is
         IS_NULL / IS_NOT_NULL on a join-target column with how="left"
         (anti-join semantics):
           --> PATH-B (Phase 2+; deferred to a separate ADR if/when
               cross-service filter pushdown is product-prioritized)

      4. ELSE: raise UnsupportedPredicateError; caller refines query.

      Phase 2 implements branches 1 and 2. Branch 3 (Path B) is gated on
      a separate cross-service-roadmap signal (CONSTRAINT-1 in MOONSHOT §6).

  station_evidence:
    s1_scout: ".ledge/spikes/SCOUT-cascade-vs-join.md"
    s2_integrate_a: ".ledge/spikes/INTEGRATE-cascade-pathA.md"
    s2_integrate_b_c5: ".ledge/spikes/INTEGRATE-pathB-and-C5.md"
    s3_prototype: ".ledge/spikes/PROTO-cascade-vs-join.md"
    s4_moonshot: ".ledge/spikes/MOONSHOT-cascade-vs-join.md"

  critic_substitution_chain:
    s3_cross_checked_by_s4: DIVERGE
    s3_s4_divergence_resolution:
      divergent_claim: |
        "LEFT JOIN to INNER JOIN rewrite is semantically equivalent for
        non-null equality filters" (S3 PROTO §7 LL.378-388 framing as
        "semantic contract change callers must be aware of"; S4 MOONSHOT
        §4 Claim 2 LL.326-364 framing as "wrong-result silent failure
        equivalent to B-R1; underweighted").
      resolution_mechanism: |
        ENGINE-SIDE LEFT-PRESERVATION GUARD (Phase 2 design requirement,
        Phase 1 must not foreclose). When the C5 dispatch branch is taken
        AND request.join.how == "left", the engine MUST execute one of
        the following before returning results:

        (a) PRIMARY DEFENSE — POST-EXPLAIN ASSERTION: invoke
            lazy_frame.explain() before .collect(); parse the resulting
            plan; assert the top-level join node header matches
            request.join.how. If the optimizer rewrote LEFT-to-INNER,
            either (i) raise LeftJoinRewrittenError, OR (ii) re-execute
            with a defensive coalesce/anti-join post-step that restores
            the LEFT-OUTER row set.

        (b) EXPLICIT CALLER OPT-IN: if the ExportRequest contract
            (Phase 1 Sprint 1) admits a `predicate_join_semantics` field
            with values {"preserve-outer", "allow-inner-rewrite"}, then
            "allow-inner-rewrite" disables defense (a) for the request.
            Default MUST be "preserve-outer" — fail-loud, not silent.

        (c) DOCUMENTATION-ONLY (REJECTED as sole defense): the platform
            has burned on the F-HYG-CF-A "documentation without
            mechanism" pattern (RETROSPECTIVE-VD3-2026-04-18.md:145).
            Documentation alone is INSUFFICIENT per telos-integrity-ref
            §3 Gate B precedent.

      escalation_to_phase_1_architect: |
        ENGINE-DESIGN-Q1: the Phase 1 architect (Sprint 2) MUST decide
        between (a) and (b) above when designing the dual-mount router
        and format-negotiation surface. Phase 1 ships single-entity
        export so the LEFT-rewrite question does not fire in Phase 1
        proper, BUT the Sprint 1 ExportRequest contract MUST NOT
        foreclose either (a) or (b). Specifically: the contract MUST
        leave room for an optional `predicate_join_semantics` field
        even if Phase 1 does not populate it. See §6 phase_1_constraints
        constraint P1-C-04.

      rationale_for_required_resolution: |
        S4 MOONSHOT §5 LL.479-499 cites F-HYG-CF-A precedent: silent
        denominator shifts at query-result altitude are the same anti-
        pattern as wave-level CLOSED claims without per-item receipts.
        This verdict closes the divergence by selecting mechanism (a)
        as primary defense and (b) as the escape valve, AND by
        escalating the design choice between them to the Phase 1
        architect with an explicit phase_1_constraint that prevents
        contract foreclosure. Silent omission would violate
        option-enumeration-discipline.

    s4_synthesized_by_s5: true
    s5_pending_critic: "Phase 1 architect at Sprint 2 (rite-disjoint per critic-substitution-rule). Ultimate STRONG-lift: Vince's user-report verification at Phase 1 close per frame.telos.verified_realized_definition.verification_method = user-report, verification_deadline = 2026-05-11, rite_disjoint_attester = theoros@know."
```

## §4 phase_2_boundary (orchestration §5.3 schema)

```yaml
phase_2_boundary:
  files_phase_2_will_modify:
    - path: "src/autom8_asana/query/engine.py:139-178"
      modification_type: refactor
      rationale: |
        Replace eager filter-then-join (current L161 df.filter +
        L163-178 join dispatch) with lazy chain when boundary_predicate
        classifies query as C5-PATH. SCOUT/PROTO/MOONSHOT all converge
        on this seam (PROTO §5 LL.184-204 stub; INTEGRATE-pathB-and-C5
        §6 LL.211-217 confirms; MOONSHOT Evidence Trail #1).
    - path: "src/autom8_asana/query/engine.py:181"
      modification_type: refactor
      rationale: |
        total_count = len(df) currently materializes; lazy chain must
        either (a) move materialization to L222 single-collect point,
        or (b) compute count via .select(pl.len()).collect() expression.
        S2b §7 coupling site #1; phase C5-3 in INTEGRATE §8.
    - path: "src/autom8_asana/query/join.py:96-192"
      modification_type: extension
      rationale: |
        execute_join signature extension for C5 strong form (lazy
        in/out). S2b §6 LL.218-224 documents this as the strong-form
        gating decision; PROTO §6 C5-SC-03 documents match-stat
        restructuring requirement. Phase 2 weak-form keeps eager
        signature; strong-form requires this extension.
    - path: "src/autom8_asana/query/engine.py:76 + join.py:90 (telemetry decorators)"
      modification_type: refactor
      rationale: |
        record_dataframe_shape=True triggers .height on LazyFrame —
        defeats optimizer. S2b C5-R3; PROTO C5-SC-05; MOONSHOT
        Evidence Trail #4.
    - path: "src/autom8_asana/query/engine.py (NEW: post-EXPLAIN guard module)"
      modification_type: new
      rationale: |
        LEFT-preservation guard implementing the s3_s4_divergence_resolution
        mechanism (§3 above). Either inline in execute_rows or extracted to
        a helper (e.g., query/join_semantics_guard.py). Phase 2 architect
        decides module shape.
    - path: "src/autom8_asana/query/models.py:24-123 (NO change planned for hybrid C5+B-deferred)"
      modification_type: extension
      rationale: |
        Phase 2's C5 path does NOT require PredicateNode DSL change
        (free-form Comparison.field at L47 stays; predicate-classifier
        operates at engine dispatch time, not at AST). If Phase 2 ever
        promotes to Path B branch (cross-service), entity-prefix syntax
        becomes a one-way-door decision per MOONSHOT §3 reversibility
        ranking and CONSTRAINT-5. Phase 2 Sprint 1 ADR required at
        that promotion point.

  phase_2_DSL_extensions:
    - "Engine-level boundary_predicate classifier (NEW): in-process classifier that routes query to CASCADE-PATH | C5-PATH | PATH-B branch per §3 hybrid_split.boundary_predicate. Lives in engine.py dispatch, NOT in PredicateNode AST."
    - "Optional ExportRequest.predicate_join_semantics field (NEW, Phase 1 contract MUST leave room): values {preserve-outer, allow-inner-rewrite}; default preserve-outer; controls LEFT-preservation guard."
    - "JoinResult.lazy_match_counts capability (NEW for C5 strong form): match-stat semantics under lazy execution per PROTO C5-SC-03 / S2b §7 coupling site #5."
    - "Path B dispatch (DEFERRED to separate ADR): MAX_JOIN_DEPTH lift at query/join.py:70; predicate-classifier at query/compiler.py:53-63,192-241; entity-prefix syntax decision. Triggered only if cross-service filter pushdown lands as a roadmap item per MOONSHOT CONSTRAINT-1."

  phase_1_must_not_touch:
    - "src/autom8_asana/query/join.py (any line — no JoinSpec changes, no MAX_JOIN_DEPTH lift, no execute_join signature change)"
    - "src/autom8_asana/query/compiler.py:53-63 (OPERATOR_MATRIX — Path B classifier territory)"
    - "src/autom8_asana/query/compiler.py:192-241 (_compile_comparison and UnknownFieldError raise at L220-225 — Phase 2 territory)"
    - "src/autom8_asana/query/engine.py:139-178 (filter+join composition — Phase 2 C5 seam)"
    - "src/autom8_asana/query/engine.py:181 (total_count materialization — Phase 2 lazy-chain dependency)"
    - "src/autom8_asana/query/models.py:27-123 (PredicateNode AST — DSL stability through Phase 2 per CONSTRAINT-5)"
    - "src/autom8_asana/dataframes/builders/cascade_validator.py:185-191 (HC-01 _CASCADE_SOURCE_MAP — only edit if a Phase 1 cascade field is added, which is OUT of Phase 1 scope)"
    - "src/autom8_asana/dataframes/extractors/cascade_resolver.py:199-275 (cascade resolver — Phase 2 if Path A branch ever invoked, NOT Phase 1)"
    - "src/autom8_asana/reconciliation/section_registry.py (SCAR-REG-001 out-of-scope per shape §7)"
    - "Any file under src/autom8_asana/dataframes/extractors/ touching CascadingFieldResolver root cause (parked SPIKE — keep parked per shape §7)"

  phase_1_may_touch:
    - "src/autom8_asana/api/routes/dataframes.py:111 (_format_dataframe_response — format negotiation extension per shape §2 Sprint 2)"
    - "src/autom8_asana/api/routes/_security.py:37,45 (pat_router/s2s_router factories — dual-mount per shape §2)"
    - "main.py:414-415 (FleetQuery dual-mount precedent — new /exports route mounts here)"
    - "src/autom8_asana/query/temporal.py (date operators source — LIFT into PredicateNode date-op extension per shape §2 Sprint 2; PredicateNode AST stays unchanged in shape but new operator types may be admitted per architect ADR)"
    - "src/autom8_asana/query/formatters.py:122 (CSV serializer — format negotiation)"
```

## §5 worked_examples (orchestration §5.4 — TWO required)

### §5.1 Worked Example #1 — CASCADE-PATH (Vince's inception-anchor query)

```yaml
worked_example_1:
  name: "Vince's Reactivation+Outreach actionable-account CSV"
  classification: CASCADE-PATH
  boundary_predicate_branch: "Branch 1 (every field resolvable against primary entity's warmed schema)"
  user_intent: |
    Export deduped account-grain rows from the Reactivation
    (GID 1201265144487549) and Outreach (GID 1201753128450029) pipelines,
    scoped to ACTIVE activity-state sections, with hygiene exclusions
    (IGNORED states + message fragments), keyed by (office_phone, vertical).

  export_request_pseudo:
    entity_type: process
    project_gids: [1201265144487549, 1201753128450029]
    predicate:
      kind: AND
      children:
        - kind: Comparison
          field: section
          op: IN
          value: ["{ACTIVE_SECTIONS_FROM_activity.py:282}"]
        - kind: Comparison
          field: completed
          op: EQ
          value: false
    join: null  # NO join in Phase 1 inception-anchor
    format: csv
    options:
      include_incomplete_identity: true  # surface SCAR-005/006 nulls
      dedupe_key: ["office_phone", "vertical"]

  engine_dispatch_pseudo: |
    # Phase 2 engine.py classifier (NOT in Phase 1):
    if all_fields_in_primary_schema(predicate, process_schema):
        # Branch 1: CASCADE-PATH (existing eager engine — no change)
        df = provider.get_dataframe(entity_type=process, project_gids=...)
        filter_expr = compiler.compile(predicate, process_schema)
        df = df.filter(filter_expr)        # engine.py:161 unchanged
        # No join needed — predicates resolve against process columns
        # (section, completed, office_phone, vertical all on warmed schema)
        return format_response(df, format=csv, identity_flag=true)

  identity_complete_handling: |
    For each row: identity_complete = (office_phone IS NOT NULL) AND
    (vertical IS NOT NULL). Rows with identity_complete=false are NOT
    silently dropped per SCAR-005/006 invariant — they appear in the CSV
    with the flag column set, allowing downstream consumers to triage.

  why_this_classification: |
    All predicate fields (section, completed) are resolved against the
    process schema directly. Identity columns (office_phone, vertical)
    are warmed cascade columns already present (cascade_validator.py:185-191
    _CASCADE_SOURCE_MAP entries). NO cross-entity predicate. Boundary_predicate
    Branch 1 fires. Engine path is the existing eager filter — Phase 2's C5
    seam change does not apply because no join is requested.

  phase_1_relevance: |
    THIS IS THE PHASE 1 INCEPTION-ANCHOR FIXTURE. Sprint 3 PT-04 hard gate
    binds to this exact query reproducing end-to-end with --format=csv per
    workflow §1.4. The verdict explicitly does NOT change Phase 1's eager
    engine path for this query — Phase 1 ships the query against the
    existing engine.py:159-161 filter, with the new dual-mount /exports
    route, format negotiation, and identity_complete column wired in.

  evidence_anchors:
    - "Frame Workstream I activity-state predicate definition (frame.md L108-171)"
    - "activity.py:282 PROCESS_PIPELINE_SECTIONS canonical vocabulary (frame.md L84)"
    - "Process schema cascade columns confirmed (PROTO Evidence Trail #8)"
    - "Existing eager engine path at engine.py:159-161 (PROTO Evidence Trail #1)"
```

### §5.2 Worked Example #2 — C5-PATH (Phase 2 cross-entity)

```yaml
worked_example_2:
  name: "Contacts whose parent offer is in an ACTIVE OFFER section"
  classification: C5-PATH
  boundary_predicate_branch: "Branch 2 (predicate references join-target field; in-process; equality op; how=inner OR LEFT-guard active)"
  user_intent: |
    Phase 2-class query (NOT Phase 1): export account-grain rows for
    contacts whose parent offer is currently in an ACTIVE OFFER section.
    This is the cross-entity query that the spike adjudicated.

  export_request_pseudo:
    entity_type: contact
    predicate:
      kind: AND
      children:
        - kind: Comparison
          field: vertical          # primary entity (contact) field
          op: EQ
          value: SaaS
        - kind: Comparison
          field: offer.section     # join-target field
          op: EQ
          value: "ACTIVE OFFER"
    join:
      target_entity: offer
      source: entity               # in-process (NOT data-service)
      how: left                    # caller wants outer semantics
      join_key: parent_gid
    format: csv
    options:
      predicate_join_semantics: preserve-outer  # default; activates LEFT-guard
      include_incomplete_identity: true

  engine_dispatch_pseudo: |
    # Phase 2 engine.py classifier (NOT in Phase 1):
    if predicate_references_target_field(predicate, request.join):
        if request.join.source == "data-service":
            raise UnsupportedPredicateError("PATH-B deferred")  # Branch 3
        if not is_equality_or_range_op(predicate):
            raise UnsupportedPredicateError("PATH-B deferred")  # Branch 3
        # Branch 2: C5-PATH
        primary_lazy = provider.get_dataframe(contact, ...).lazy()
        target_lazy = provider.get_dataframe(offer, ...).lazy()
        filter_expr = compiler.compile(predicate, joined_schema)
        chain = primary_lazy.join(target_lazy,
                                  left_on="parent_gid",
                                  right_on="gid",
                                  how=request.join.how) \
                            .filter(filter_expr)
        # === LEFT-PRESERVATION GUARD (s3_s4_divergence_resolution) ===
        if request.join.how == "left" and \
           request.options.predicate_join_semantics == "preserve-outer":
            plan = chain.explain()
            if "INNER JOIN" in plan_top_node(plan):
                # Optimizer rewrote LEFT->INNER (S3 PROTO §5 LL.232-244).
                # Re-execute with anti-join restoration:
                chain = restore_left_outer_via_anticoalesce(
                    primary_lazy, target_lazy, filter_expr, request.join
                )
        df = chain.collect()
        return format_response(df, format=csv, identity_flag=true)

  why_this_classification: |
    Predicate references offer.section, which is NOT on the contact
    primary schema (compiler.py:220-225 would raise UnknownFieldError
    today). Branch 2 fires: in-process join, equality op, how=left with
    LEFT-guard. C5 lazy chain composes; Polars optimizer pushes
    offer.section predicate onto RIGHT PLAN (PROTO §5 EXPLAIN strong
    form, LL.230-247). LEFT-preservation guard activates because
    optimizer rewrote LEFT->INNER (PROTO LL.232 INNER JOIN header) —
    guard re-executes via anti-join restoration so accounts-without-offer
    are not silently dropped.

  why_NOT_path_b: |
    Path B's predicate-classifier + MAX_JOIN_DEPTH lift + filter-split
    logic (S2b §4 LL.124-160; 8.5-13.5d effort) is unnecessary for this
    query. Polars optimizer empirically performs the equivalent
    pushdown (PROTO Subsumption Thesis §7 CONFIRMED row 1). C5 wins on
    LOC (~5-50 vs Path B's full multi-file refactor) and on reversibility
    (MOONSHOT §3).

  why_NOT_cascade: |
    Path A would require adding parent_offer_section as a new cascade
    column on contact.py (PROTO §3 stub LL.59-79), incurring 26-31 LOC
    per query shape (PROTO §9), HC-01/HC-02/HC-03/HC-04 coupling
    (S2a §3), and SC-2 multi-hop DEGRADES verdict (MOONSHOT §2 LL.94-106).
    Per-shape cost dominates at >=2 cross-entity shapes (PROTO §9
    break-even).

  phase_2_relevance: |
    This query lives in Phase 2 (post-spike). The verdict ensures Phase 2
    can implement this WITHOUT being foreclosed by Phase 1 contract
    decisions (CONSTRAINT-1 below). Phase 1 must leave room for the
    predicate_join_semantics field in the ExportRequest contract.

  evidence_anchors:
    - "PROTO §5 EXPLAIN strong form (PROTO L230-247)"
    - "PROTO §7 Subsumption Thesis CONFIRMED rows 1+3"
    - "MOONSHOT §4 Claim 2 DIVERGE (LEFT->INNER divergence resolution)"
    - "S2b §10 composition_thesis (C5 SUBSUMES B for in-process equality)"
```

## §6 phase_1_constraints (orchestration §5.5)

Constraints Phase 1 (10x-dev rite, Sprints 1-4) MUST respect to avoid foreclosing the §3 hybrid verdict's Phase 2 design space.

```yaml
phase_1_constraints:

  - id: P1-C-01
    name: "Single-entity scope hard-lock"
    binding_on: "Sprint 1 (requirements-analyst), Sprint 2 (architect), Sprint 3 (principal-engineer)"
    constraint: |
      The Phase 1 ExportRequest contract MUST NOT include any field that
      expresses cross-entity joins. Specifically: NO `join` field, NO
      `target_entity` field, NO `predicate_target_resolution` field. The
      contract is single-entity per shape §2 Sprint 1 exit criteria.
    rationale: |
      Cross-entity joins are Phase 2 (§4 phase_2_DSL_extensions). Adding
      them to Phase 1 contract forecloses the boundary_predicate
      classifier design (§3 hybrid_split.boundary_predicate) and risks
      shipping a contract that constrains the Phase 2 dispatch.
    derived_from: "shape §2 Sprint 1; verdict §3 hybrid_split"
    foreclosure_risk_if_violated: HIGH

  - id: P1-C-02
    name: "predicate_join_semantics contract reservation"
    binding_on: "Sprint 1 (requirements-analyst)"
    constraint: |
      The Phase 1 ExportRequest contract MUST leave room for an OPTIONAL
      future field named `predicate_join_semantics` (or
      semantically-equivalent) with values {preserve-outer,
      allow-inner-rewrite}. Phase 1 does NOT populate this field; Phase 2
      may populate it. The contract MUST NOT use a closed enum in the
      `options` substructure that would block additive extension.
    rationale: |
      The s3_s4_divergence_resolution mechanism (§3) requires this field
      for Phase 2 C5 path. Closing the contract enum here forecloses the
      LEFT-preservation guard escape valve (mechanism (b) in the
      resolution).
    derived_from: "verdict §3 critic_substitution_chain.s3_s4_divergence_resolution; MOONSHOT CONSTRAINT-2"
    foreclosure_risk_if_violated: HIGH

  - id: P1-C-03
    name: "PredicateNode AST stability"
    binding_on: "Sprint 2 (architect), Sprint 3 (principal-engineer)"
    constraint: |
      The PredicateNode DSL at src/autom8_asana/query/models.py:27-123
      MUST NOT change in Phase 1. Specifically: Comparison.field stays
      free-form string at L47 (no entity-prefix syntax introduced); no
      new node types added beyond what the date-operator extension
      requires per shape §2 Sprint 2.
    rationale: |
      MOONSHOT CONSTRAINT-5 + §3 reversibility ranking: entity-prefix
      syntax in PredicateNode is a one-way door. Any DSL contract change
      visible to PAT/S2S callers requires explicit ADR with deprecation
      cycle. Phase 1 ships date-operator additions only (BETWEEN,
      DATE_GTE, DATE_LTE) per shape §2; no entity-prefix.
    derived_from: "MOONSHOT §6 CONSTRAINT-5; shape §2 Sprint 2 emergent_behavior.prescribed"
    foreclosure_risk_if_violated: CRITICAL (one-way door)

  - id: P1-C-04
    name: "Engine seam isolation"
    binding_on: "Sprint 3 (principal-engineer W1, W2, W3)"
    constraint: |
      No Phase 1 implementation may modify
      src/autom8_asana/query/engine.py:139-178 OR
      src/autom8_asana/query/engine.py:181 (total_count line) OR
      src/autom8_asana/query/join.py (any line). The Phase 1 export
      route calls into the existing engine via the existing /rows-style
      path; format negotiation and identity_complete column live in the
      route handler / formatter layer, NOT in the engine.
    rationale: |
      §4 phase_1_must_not_touch list. These seams are the Phase 2 C5
      load-bearing change sites (§4 files_phase_2_will_modify). Phase 1
      modifications here would conflict with Phase 2 implementation.
    derived_from: "verdict §4 phase_1_must_not_touch; PROTO §5 seam location"
    foreclosure_risk_if_violated: HIGH

  - id: P1-C-05
    name: "identity_complete column source-of-truth wiring"
    binding_on: "Sprint 2 (architect), Sprint 3 (principal-engineer W3)"
    constraint: |
      The identity_complete flag column MUST be computed at extraction
      time (in the export route handler or its formatter helper), NOT
      inside the cascade resolver and NOT inside the cascade validator.
      Cascade validator at cascade_validator.py:46-176 stays warmup-time
      only (PROTO Evidence Trail #7; MOONSHOT Claim 5 CONCUR).
    rationale: |
      Adding identity_complete as a cascade column would touch
      cascade_validator.py:185-191 _CASCADE_SOURCE_MAP (HC-01) and
      could destabilize the warmed-cache invariant. Computing it at
      extraction time keeps the cascade defense layer intact and
      satisfies the SCAR-005/006 transparency promise.
    derived_from: "S2a HC-01; MOONSHOT Claim 5 CONCUR; shape §3 PT-03 Q4"
    foreclosure_risk_if_violated: MEDIUM (operational, not architectural)

  - id: P1-C-06
    name: "format negotiation extension shape"
    binding_on: "Sprint 2 (architect), Sprint 3 (principal-engineer W3)"
    constraint: |
      Format negotiation (CSV / Parquet / JSON) MUST extend
      _format_dataframe_response at api/routes/dataframes.py:111 (3-line
      branch addition shape acceptable per shape §2 Sprint 2). Format
      branches MUST work on the eager pl.DataFrame returned by the
      existing engine path. NO call into the engine to request a lazy
      output — Phase 1 does not introduce LazyFrame outputs to consumers.
    rationale: |
      Phase 2 C5 lazy chain materializes inside the engine (single
      .collect() at engine.py:222 per S2b C5-3). Consumer-facing API
      sees only eager DataFrames in Phase 1 AND Phase 2. Introducing a
      LazyFrame consumer surface in Phase 1 would be both a contract
      change and a Phase 2 forecloser.
    derived_from: "S2b §8 phase C5-3; shape §2 Sprint 2"
    foreclosure_risk_if_violated: MEDIUM

  - id: P1-C-07
    name: "Dual-mount auth pattern fidelity"
    binding_on: "Sprint 2 (architect), Sprint 3 (principal-engineer W2)"
    constraint: |
      The /exports route MUST mount under BOTH PAT and S2S routers via
      the FleetQuery precedent at main.py:414-415 + factories at
      api/routes/_security.py:37,45. Asymmetric mounting (PAT-only or
      S2S-only) violates the throughline.
    rationale: |
      The throughline names "every future PAT or S2S caller" explicitly.
      Iris (S2S) and Vince's tooling (PAT) are both first-class.
    derived_from: "throughline; shape §1 success criteria; shape §2 Sprint 2"
    foreclosure_risk_if_violated: HIGH (throughline-violating)
```

## §7 new_risks (orchestration §5.6 — spike-discovered)

Risks the spike surfaced that are NOT in shape §9 risk_map; Phase 1 must not foreclose mitigation paths.

```yaml
new_risks:

  - id: SR-01
    name: "HC-01 silent observability degradation on cascade additions"
    severity: HIGH
    surface: "src/autom8_asana/dataframes/builders/cascade_validator.py:185-191"
    description: |
      _CASCADE_SOURCE_MAP at cascade_validator.py:185-191 is a hand-
      maintained dict mapping cascade field name -> source entity. Any
      new cascade field (Path A trajectory) silently misses SCAR-005
      audit unless this dict is updated in lockstep. Phase 1's
      identity_complete flag depends on cascade audit firing correctly
      per added cascade column; if Phase 2 ever invokes Path A branch,
      this hidden coupling fires.
    discovered_in: "S2a INTEGRATE-cascade-pathA.md §3 HC-01"
    phase_1_impact: |
      Phase 1 adds NO new cascade fields per P1-C-05; risk dormant for
      Phase 1. Documented here so Phase 2 architect inherits awareness.
    mitigation_for_phase_2: |
      Add a startup assertion that every schema.get_cascade_columns()
      field name has an entry in _CASCADE_SOURCE_MAP (per PROTO §4
      PA-SC-01 production_remediation). Phase 1 may introduce this
      assertion as a defensive backstop (no behavior change for
      existing fields, fail-fast for any future addition).
    phase_1_foreclosure_risk: NONE (Phase 1 does not foreclose)

  - id: SR-02
    name: "C5 LEFT-to-INNER silent denominator shift"
    severity: CRITICAL
    surface: "Polars 1.38.1 optimizer (LazyFrame.collect() over join+filter chain)"
    description: |
      When Phase 2 C5 path is invoked with how='left' and a non-IS-NULL
      equality predicate targets a join-target column, Polars optimizer
      rewrites LEFT JOIN -> INNER JOIN (PROTO §5 strong form EXPLAIN).
      Rows where the join target is null are silently excluded from the
      result, shifting the denominator. F-HYG-CF-A-class failure at
      query-result altitude (RETROSPECTIVE-VD3-2026-04-18.md:145
      precedent).
    discovered_in: "PROTO §5 LL.230-244; MOONSHOT §4 Claim 2 DIVERGE"
    phase_1_impact: |
      Phase 1 ships single-entity export only (P1-C-01); no cross-entity
      join in Phase 1 contract. Risk does not fire in Phase 1. BUT
      Phase 1 contract MUST leave room for the LEFT-preservation guard
      mechanism per P1-C-02.
    mitigation_for_phase_2: |
      Implement LEFT-preservation guard per §3 s3_s4_divergence_resolution.
      Default mechanism (a) post-EXPLAIN assertion + anti-join
      restoration; mechanism (b) caller opt-in via
      predicate_join_semantics='allow-inner-rewrite'. Documentation-only
      defense REJECTED per F-HYG-CF-A precedent.
    phase_1_foreclosure_risk: HIGH if P1-C-02 violated (closed enum in options blocks future field)

  - id: SR-03
    name: "Cross-service join coverage gap (data-service exclusion)"
    severity: HIGH (Phase 2+ scope; CRITICAL if cross-service surfaces in roadmap)
    surface: "src/autom8_asana/query/engine.py:587-594 + JoinSpec.source='data-service'"
    description: |
      C5's Polars optimizer cannot push predicates across network
      boundaries. JoinSpec with source='data-service' uses
      DataServiceJoinFetcher (engine.py:589) which fetches AFTER primary
      filter today. Phase 2 hybrid verdict explicitly defers cross-
      service filter pushdown to a separate Path B ADR (boundary_predicate
      Branch 3). If product roadmap surfaces a cross-service-with-pushdown
      requirement before that ADR lands, the verdict's hybrid scope
      shifts.
    discovered_in: "PROTO §6 C5-SC-04; MOONSHOT §2 SC-3 (BREAKS for C5, SURVIVES for B)"
    phase_1_impact: |
      Phase 1 ships single-entity; risk does not fire. Documented for
      Phase 2 architect awareness.
    mitigation_for_phase_2: |
      Path B dispatch (boundary_predicate Branch 3) is the documented
      mitigation. Triggered only if cross-service filter pushdown
      becomes a roadmap item per MOONSHOT CONSTRAINT-1.
    phase_1_foreclosure_risk: NONE (Phase 1 does not touch JoinSpec or compiler)

  - id: SR-04
    name: "Telemetry decorator forces silent LazyFrame materialization"
    severity: MEDIUM
    surface: "src/autom8_asana/query/engine.py:76 + query/join.py:90 (record_dataframe_shape=True)"
    description: |
      trace_computation decorator with record_dataframe_shape=True calls
      .height on df. On a LazyFrame, .height triggers .collect() — silent
      perf loss negating C5 optimizer wins. Surfaces only under load test.
    discovered_in: "PROTO §6 C5-SC-05; S2b §7 coupling site #4"
    phase_1_impact: NONE (Phase 1 path is eager; decorator behavior unchanged)
    mitigation_for_phase_2: |
      Disable record_dataframe_shape on lazy paths, or restructure to
      use schema-level shape (LazyFrame.schema is cheap). S2b §8 phase
      C5-4 (0.5-1d effort).
    phase_1_foreclosure_risk: NONE

  - id: SR-05
    name: "match-stat semantics divergence under lazy join"
    severity: HIGH (C5 strong form only)
    surface: "src/autom8_asana/query/join.py:175-181 (matched_count/unmatched_count via .height)"
    description: |
      JoinResult.matched_count is computed via .filter(...).height on
      enriched df. Under C5 strong form (lazy execute_join signature),
      .height triggers .collect() — either eager-collect-before-stats
      (defeating optimizer) or restructure stat computation (1-2d work).
    discovered_in: "PROTO §6 C5-SC-03; S2b C5-R2"
    phase_1_impact: NONE (Phase 1 does not touch join.py)
    mitigation_for_phase_2: |
      S2b §8 phase C5-3 restructures pagination + total_count for
      single .collect(). JoinResult contract may need lazy_match_counts
      capability per §4 phase_2_DSL_extensions.
    phase_1_foreclosure_risk: NONE
```

## §8 evidence_trail (orchestration §5.7)

Every load-bearing claim in this verdict carrier traced to a station artifact path:line OR external Polars/source evidence. Self-ref MODERATE ceiling enforced per self-ref-evidence-grade-rule.

| # | Claim | Source / file:line | Grade |
|---|---|---|---|
| 1 | C5 seam at engine.py:140-178 (filter+join composition) | `src/autom8_asana/query/engine.py:139-178` (S2b §6 verified; S3 §5 stub; MOONSHOT Evidence Trail #1) | [PLATFORM-INTERNAL \| STRONG] |
| 2 | Eager filter at engine.py:161 (current behavior) | `src/autom8_asana/query/engine.py:159-161` (S3 §5; MOONSHOT Evidence Trail #2) | [PLATFORM-INTERNAL \| STRONG] |
| 3 | Polars 1.38.1 pushes equality predicates onto right side before join | `.ledge/spikes/PROTO-cascade-vs-join.md:230-247` (verbatim .explain() strong form); MOONSHOT §4 Claim 1 CONCUR | [PLATFORM-EMPIRICAL \| MODERATE] (S3-attested; S4 did not re-run; STRONG inheritable for general Polars optimizer behavior per Polars docs SCOUT SRC-002) |
| 4 | Polars optimizer rewrites LEFT JOIN to INNER JOIN on equality predicate | `.ledge/spikes/PROTO-cascade-vs-join.md:232-244` (verbatim INNER JOIN header); MOONSHOT §4 Claim 2 DIVERGE | [PLATFORM-EMPIRICAL \| MODERATE] |
| 5 | LEFT JOIN preserved for IS NULL predicate (no rewrite) | `.ledge/spikes/PROTO-cascade-vs-join.md:250-262` (verbatim EXPLAIN null-filter form) | [PLATFORM-EMPIRICAL \| MODERATE] |
| 6 | Eager and lazy results equal for equality predicates (correctness) | `.ledge/spikes/PROTO-cascade-vs-join.md:507-510` (Evidence Trail row "Eager and lazy results equal") | [PLATFORM-EMPIRICAL \| MODERATE] (2000-iter benchmark) |
| 7 | Path A per-shape recurring cost ~26-31 LOC | `.ledge/spikes/PROTO-cascade-vs-join.md:107-123` (latency + LOC matrix); §9 break-even | [PLATFORM-EMPIRICAL \| MODERATE] |
| 8 | C5 weak form 5 LOC; C5 strong form 35-50 LOC | `.ledge/spikes/PROTO-cascade-vs-join.md:280-288` | [PLATFORM-EMPIRICAL \| MODERATE] |
| 9 | Path B effort 8.5-13.5d med-low confidence | `.ledge/spikes/INTEGRATE-pathB-and-C5.md:157-159` (total_effort, total_confidence) | [PLATFORM-INTERNAL \| MODERATE] |
| 10 | Path C5 effort 5-9d med-high confidence | `.ledge/spikes/INTEGRATE-pathB-and-C5.md:332-334` (total_effort, total_confidence) | [PLATFORM-INTERNAL \| MODERATE] |
| 11 | Cascade null-audit denominator NOT coupled to C5 | `.ledge/spikes/INTEGRATE-pathB-and-C5.md:270-274` (S2b §7 zero-coupling); MOONSHOT §4 Claim 5 CONCUR (verified independently) | [PLATFORM-INTERNAL \| STRONG] |
| 12 | _CASCADE_SOURCE_MAP hardcoded 5-entry dict at cascade_validator.py:185-191 | `src/autom8_asana/dataframes/builders/cascade_validator.py:185-191` (S2a §3 HC-01; PROTO Evidence Trail row 6) | [PLATFORM-INTERNAL \| STRONG] |
| 13 | SC-3 (cross-service) BREAKS for C5; SURVIVES for B | `.ledge/spikes/MOONSHOT-cascade-vs-join.md:130-165` (§2 stress matrix SC-3) | [PLATFORM-INTERNAL \| MODERATE] (scenario reasoning) |
| 14 | C5-SC-04 prototype excluded JoinSpec.source='data-service' | `.ledge/spikes/PROTO-cascade-vs-join.md:323-330` (§6 documented shortcut) | [PLATFORM-INTERNAL \| STRONG] |
| 15 | DataServiceJoinFetcher fetches AFTER primary filter | `src/autom8_asana/query/engine.py:587-594` (S2b §3 + Evidence Trail) | [PLATFORM-INTERNAL \| STRONG] |
| 16 | PredicateNode Comparison.field is free-form string (no entity-prefix) | `src/autom8_asana/query/models.py:47` (S2b Evidence Trail; MOONSHOT Evidence Trail #6) | [PLATFORM-INTERNAL \| STRONG] |
| 17 | UnknownFieldError raised at compiler.py:220-225 | `src/autom8_asana/query/compiler.py:220-225` (S2b Evidence Trail; MOONSHOT Evidence Trail #7) | [PLATFORM-INTERNAL \| STRONG] |
| 18 | C5 reversibility highest (single-line revert weak form) | `.ledge/spikes/MOONSHOT-cascade-vs-join.md:273-282` (§3 reversibility ranking) | [PLATFORM-INTERNAL \| MODERATE] |
| 19 | Subsumption thesis PARTIAL (C5 subsumes B for in-process equality; not for data-service or anti-join) | `.ledge/spikes/PROTO-cascade-vs-join.md:357-411` (§7 verdict + summary table) | [PLATFORM-EMPIRICAL \| MODERATE] |
| 20 | warmed-cache invariant preserved under C5 | `.ledge/spikes/MOONSHOT-cascade-vs-join.md:431-468` (§4 Claim 5 CONCUR; verified by S4 via Read of cascade_validator.py:46-176) | [PLATFORM-INTERNAL \| STRONG] |
| 21 | Polars LazyFrame predicate pushdown is documented optimization | docs.pola.rs/user-guide/lazy/optimizations/ (SCOUT SRC-002; MOONSHOT Evidence Trail #14) | [STRONG \| external] |
| 22 | LEFT->INNER rewrite NOT explicitly documented in user-facing Polars docs | Web search 2026-04-27 returned no canonical doc reference (MOONSHOT Evidence Trail #15) | [MODERATE \| external negative] |
| 23 | F-HYG-CF-A canonical precedent (per-item receipts; silent denominator shift anti-pattern) | `RETROSPECTIVE-VD3-2026-04-18.md:145` (cited in telos-integrity-ref skill body and MOONSHOT Evidence Trail #21) | [PLATFORM-INTERNAL \| STRONG] |
| 24 | FleetQuery dual-mount precedent at main.py:414-415 | `main.py:414-415` (shape §2 Sprint 2 emergent_behavior.prescribed; SVR not run by S5) | [PLATFORM-INTERNAL \| MODERATE] |
| 25 | Phase 1 deadline 2026-05-11 (telos.verified_realized_definition.verification_deadline) | `.sos/wip/frames/project-asana-pipeline-extraction.md:25` | [PLATFORM-INTERNAL \| STRONG] |
| 26 | rite_disjoint_attester = theoros@know | `.sos/wip/frames/project-asana-pipeline-extraction.md:26` | [PLATFORM-INTERNAL \| STRONG] |

### §8.1 Self-attestation grade ceiling

This S5 verdict carrier is authored by tech-transfer (rnd rite). Self-ref MODERATE ceiling per self-ref-evidence-grade-rule applies to all claims marked [PLATFORM-INTERNAL] or [PLATFORM-EMPIRICAL]. STRONG-lift requires external corroboration:
- Phase 1 architect at Sprint 2 entry (rite-disjoint critic per critic-substitution-rule)
- Vince's user-report verification at Phase 1 close per frame.telos.verified_realized_definition.verification_method = user-report

Until both corroboration events occur, all PLATFORM-INTERNAL/PLATFORM-EMPIRICAL claims in this artifact remain MODERATE-ceilinged.

## §9 GO/NO-GO Recommendation for Phase 1 Entry

**Verdict: CONDITIONAL GO**

The 10x-dev rite SHOULD proceed to Phase 1 (Sprint 1: requirements lock) under the following entry conditions:

```yaml
entry_conditions:
  - id: EC-01
    name: "Telos pulse arrival check"
    requirement: |
      Incoming 10x-dev Potnia stamps the
      telos_pulse_carrier.incoming_potnia_acknowledgement block per
      workflow §4.4. pulse_restated MUST paraphrase the inception_anchor
      AND quote it verbatim. If Potnia cannot paraphrase without re-reading,
      the pulse did not arrive — escalate to user.
    blocking: true

  - id: EC-02
    name: "Phase 2 boundary internalization"
    requirement: |
      Sprint 1 (requirements-analyst) and Sprint 2 (architect) dispatch
      prompts MUST cite this handoff artifact path:line as inception
      context per workflow §2.1 step 2 and §2.2 step 2. Sprint 2 ADR
      MUST cite §4 phase_2_boundary explicitly.
    blocking: true

  - id: EC-03
    name: "phase_1_constraints registration"
    requirement: |
      Sprint 1 contract spec MUST satisfy P1-C-01 (single-entity scope)
      AND P1-C-02 (predicate_join_semantics contract reservation). PT-02
      hard gate (shape §3) verifies these explicitly. PT-02 MUST NOT
      pass with a closed enum in ExportRequest.options that blocks
      future predicate_join_semantics field addition.
    blocking: true

  - id: EC-04
    name: "DIVERGE resolution acknowledged at Sprint 2"
    requirement: |
      Sprint 2 ADR MUST explicitly acknowledge the s3_s4_divergence_resolution
      mechanism (§3) as a Phase 2 design requirement. ADR MAY defer
      mechanism-(a)-vs-(b) selection to Phase 2, BUT MUST NOT silently
      omit the constraint. ENGINE-DESIGN-Q1 MUST appear in the ADR's
      "Phase 2 forward-binding constraints" section.
    blocking: true

  - id: EC-05
    name: "Engine seam isolation enforcement at PT-04"
    requirement: |
      Sprint 3 PT-04 hard gate MUST verify that no Phase 1 commit
      modifies the files in §4 phase_1_must_not_touch. Automated check
      via `git diff` against the phase_1_must_not_touch path list at
      Sprint 3 close.
    blocking: true

recovery_criteria_if_phase_1_falters:
  - "If PT-04 inception-anchor fixture fails: targeted fix sprint per shape §3 PT-04 on_fail; re-evaluate hybrid verdict only if the fixture failure traces to a verdict-level decision (not a Phase 1 implementation defect)."
  - "If Vince's user-report verification on 2026-05-11 surfaces an unmet outcome: telos-integrity Gate B refusal (per telos-integrity-ref §3); residual-work ledger entry; Phase 2 design opens only after remediation per shape §3 PT-06."

j_curve_timeline_expectation:
  brief: |
    Phase 1 has 14 days slack to deadline 2026-05-11 (per inquisition
    plan §7). The hybrid verdict imposes ZERO additional Phase 1
    implementation cost — all Phase 2 burden is in §4 phase_2_boundary.
    No J-curve dip expected at Phase 1 close because Phase 1 ships the
    same single-entity export per shape §2 regardless of which path
    Phase 2 ultimately implements. The hybrid verdict's value is realized
    at Phase 2 entry (when the boundary_predicate classifier and
    LEFT-preservation guard land).
  recovery_signal: |
    If Phase 2 entry takes >4 weeks after Phase 1 close, MOONSHOT
    CONSTRAINT-3 (per-shape vs per-engine recurring cost discipline)
    re-evaluates: a documented count of cross-entity query shapes
    in the Phase 2-3 roadmap should anchor the C5-vs-A re-litigation.

verdict_status: |
  CONDITIONAL GO. Phase 1 may begin Sprint 1 immediately after the
  five entry conditions above are satisfied. The hybrid verdict is
  binding on Phase 2 design; no narrative escape hatch.
```

## §10 Pending-Critic Acknowledgment

Per critic-substitution-rule and the inquisition orchestration plan §4 critic-substitution map:

```yaml
pending_critic_acknowledgment:
  s5_verdict_authored_by: "tech-transfer (rnd rite, this artifact)"

  immediate_pending_critic:
    role: "Phase 1 architect at Sprint 2 entry"
    rite: "10x-dev"
    rite_disjoint_from: "rnd (this artifact's authoring rite)"
    critique_substitution_basis: |
      Per critic-substitution-rule: dispatcher (S5 tech-transfer) MUST NOT
      self-attest STRONG. The Phase 1 architect at Sprint 2 entry is the
      first rite-disjoint reader of this verdict carrier. Their ADR
      authoring is the immediate cross-rite critique event. If the
      architect identifies a foreclosure risk or boundary violation in
      §4 or §6, this verdict carrier must be revised via critique-iteration-protocol
      DELTA-scope (NOT cosmetic revision).

  ultimate_strong_lift_critic:
    role: "Vince (or equivalent caller)"
    rite: "user-report (frame.telos.verified_realized_definition.verification_method)"
    deadline: "2026-05-11"
    rite_disjoint_attester_named_in_frame: "theoros@know"
    strong_lift_basis: |
      Per frame.telos.verified_realized_definition: the ultimate
      verification is Vince's user-report attestation that the original
      Reactivation+Outreach actionable-account CSV reproduces against
      the new endpoint. Until this attestation lands at deadline
      2026-05-11, this verdict carrier and all Phase 1 sprint artifacts
      remain MODERATE-ceilinged per self-ref-evidence-grade-rule. The
      user-report attestation is the cross-stream-concurrence event that
      lifts the throughline to STRONG.

  silent_omission_guard: |
    This acknowledgment is REQUIRED per inquisition orchestration plan
    §4 critic-substitution map. Silent omission of s5_pending_critic
    would violate critic-substitution-rule. Both critics named above
    are explicit and time-anchored.
```

---

**End of verdict carrier.** Phase 1 entry begins when the five entry conditions in §9 are satisfied. Phase 2 design opens after Phase 1 close + PT-06 telos-integrity gate (per shape §2 Sprint 5 + frame.telos.verified_realized_definition).
