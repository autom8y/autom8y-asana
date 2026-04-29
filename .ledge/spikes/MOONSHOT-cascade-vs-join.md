---
type: spike
status: accepted
initiative: project-asana-pipeline-extraction
station: S4
specialist: moonshot-architect
related_spike: cascade-vs-join
dual_role: [long-horizon-stress, critic-substitution-on-S3]
session_id: session-20260427-232025-634f0913
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
created: 2026-04-27
verdict_authority: S5 (tech-transfer)
this_artifact_authority: long-horizon-stress + critic-substitution (NOT verdict)
upstream_artifacts:
  - .ledge/spikes/SCOUT-cascade-vs-join.md
  - .ledge/spikes/INTEGRATE-cascade-pathA.md
  - .ledge/spikes/INTEGRATE-pathB-and-C5.md
  - .ledge/spikes/PROTO-cascade-vs-join.md
critic_substitution_rule_invoked: true
critic_substitution_subject: S3 prototype-engineer
polars_version_under_test: "1.38.1"
---

# MOONSHOT — Cascade-vs-Join Long-Horizon Stress + Critic-Substitution on S3 (Station S4)

## §1 Telos Echo

Vince and every future caller produce a parameterized account-grain export via
dual-mount endpoint without custom scripting; Phase 1 verifies against the
original Reactivation+Outreach CSV ask by 2026-05-11. This station's dual
contribution: (a) ensure the spike's eventual S5 verdict survives 2-3 year
scenario pressure, (b) cross-check S3's empirical evidence as rite-disjoint
critic per `critic-substitution-rule` (S3 cannot self-grade STRONG). Phase 2
non-foreclosure invariant respected — no design lock proposed.

---

## §2 Long-Horizon Stress Matrix

```yaml
stress_matrix:
  scope: "Five 2-3 year scenarios x three live paths (A, B, C5). Verdicts: SURVIVES | DEGRADES | BREAKS."
  paths_evaluated:
    A: "Cascade-extension (denormalize at warmup)"
    B: "Join-engine pushdown (build cross-entity classifier in PredicateCompiler + lift MAX_JOIN_DEPTH)"
    C5: "Polars LazyFrame native predicate pushdown delegation (composition-mode flip at engine.py:140-178)"

  scenarios:

    - id: SC-1
      name: "100x scale (10K accounts/pipeline x 50 pipelines x 1M rows)"
      paths:
        A:
          verdict: DEGRADES
          rationale: |
            Cascade is paid at warmup, not per-query — latency stays good. BUT
            schema-explosion is N x M (per cross-entity field x per consumer
            entity), and HC-02 cascade-null thresholds (5%/20%) calibrated at
            today's row count may shift under 100x distribution. SCAR-005's
            30% calibration anchor is at current scale; null-distribution
            per added column at 1M rows is unmeasured.
          migration_trigger: |
            Warmup time exceeds preload SLO (today: lifespan-bound) OR
            cascade null rate on any added field crosses 20% in production
            telemetry on a live cascade column.
        B:
          verdict: DEGRADES
          rationale: |
            JOIN-then-FILTER reorder loads target eagerly per query (S2b
            HC-04 at engine.py:130-133). At 100x rows, target load cost
            multiplies; cache-warming pressure on dataframe provider grows
            proportionally. Predicate-classifier complexity (S2b B-2,
            3-5d effort) adds debugging surface that scales poorly.
          migration_trigger: |
            DataServiceClient/provider cache hit-rate drops below 90% on
            cross-entity queries OR p95 latency on /rows exceeds SLO.
        C5:
          verdict: SURVIVES
          rationale: |
            Polars optimizer is designed for 1M+ row lazy execution (the
            optimizer's whole reason to exist). Predicate pushdown reduces
            materialized intermediate state. NO additional schema columns,
            so cascade-null amplification (HC-02) stays bounded to today's
            5 cascade fields. Optimizer wins (36% reduction at S3 §9
            benchmark) likely scale with row count.
          migration_trigger: |
            Polars optimizer fails to push predicate on a measured
            production query shape (verifiable via .explain() in observability).

    - id: SC-2
      name: "Multi-hop joins (3-hop: contacts from active offers from accounts in expansion pipelines)"
      paths:
        A:
          verdict: DEGRADES
          rationale: |
            Each hop requires a new cascade column on the leaf entity
            (contact). 3-hop = 3 new cascade columns minimum, each carrying
            HC-01 _CASCADE_SOURCE_MAP coupling, HC-02 threshold risk, HC-03
            warmup-ordering coordination, HC-04 ROOT-fallback (BUSINESS-only)
            constraint. Per-query-shape recurring cost (S3 §9: 26-31 LOC)
            multiplies by hop count.
          migration_trigger: |
            Phase 2 ships a 2-hop query AND product backlog adds 3-hop
            within 6 months — at that signal, cascade-extension becomes
            net-debt vs alternatives.
        B:
          verdict: DEGRADES
          rationale: |
            S2b B-2 / hierarchy.py:104-149 requires graph traversal
            (BFS/DFS) for depth>1; cycle detection (B-R5). Predicate-
            classifier becomes hop-aware. Effort jumps from B's stated
            8.5-13.5d to multi-week scope creep at depth>=3.
          migration_trigger: |
            Product confirms a depth>=3 query lands in next quarter's
            roadmap.
        C5:
          verdict: DEGRADES
          rationale: |
            Polars LazyFrame supports chained joins, BUT S3 confirms only
            single-join EXPLAIN evidence. Multi-hop optimizer behavior
            unverified. C5-SC-04 (data-service exclusion) compounds: any
            hop touching data-service breaks the lazy chain. PredicateNode
            DSL gap (no entity-prefix) becomes acute at 3-hop because
            disambiguation surface widens.
          migration_trigger: |
            First production attempt at a 3-hop in-process query; Polars
            .explain() output should be captured and verified.

    - id: SC-3
      name: "Cross-service joins (autom8y-data enrichment routine via JoinSpec.source=data-service)"
      paths:
        A:
          verdict: BREAKS
          rationale: |
            Cascade lives entirely inside the autom8y-asana entity graph.
            Cross-service enrichment from autom8y-data has no cascade
            machinery — Path A is structurally inapplicable. S2b HC-04
            confirms data-service joins fetch AFTER primary filter; cascade
            pre-materialization cannot include data-service columns.
          migration_trigger: |
            ANY product requirement to filter by an autom8y-data field
            triggers Path A insufficiency. Already a known constraint.
        B:
          verdict: SURVIVES
          rationale: |
            Path B's predicate-classifier extends naturally to JoinSpec.
            source="data-service" by routing the data-service-bound
            predicates into the DataServiceClient request shape (B-4 phase).
            This is the scenario where Path B uniquely earns its complexity.
          migration_trigger: |
            Cross-service filter pushdown surfaces as a roadmap item
            beyond Phase 2. (Note: this is the primary B-keep-alive
            scenario.)
        C5:
          verdict: BREAKS
          rationale: |
            S3 C5-SC-04 explicitly excludes data-service from the prototype.
            Polars optimizer cannot push predicates across network
            boundaries — DataServiceClient is a remote fetch, not an
            in-process join. C5 covers in-process entity joins only. THIS
            IS THE LIMITING FACTOR for C5 as a sole architectural commitment.
          migration_trigger: |
            First production data-service join with predicate on
            data-service column. Already foreseeable per S2b.

    - id: SC-4
      name: "Real-time export (sub-second freshness, not warmed-cache reads)"
      paths:
        A:
          verdict: BREAKS
          rationale: |
            Cascade is paid at WARMUP TIME (cascade_validator.py:46-176;
            verified). Sub-second freshness requires per-request resolution,
            which dismantles the warmed-cache contract. SCAR-005/006
            defense-in-depth assumes warmup-time validation.
          migration_trigger: |
            Product confirms sub-second freshness SLA.
        B:
          verdict: DEGRADES
          rationale: |
            Path B inherits the warmed-cache invariant (engine.py:130-133
            DataFrameProvider). Sub-second freshness requires bypassing
            the provider, which Path B does not address. Path B is
            orthogonal to freshness, not antagonistic — but does not solve.
          migration_trigger: |
            Same as A. Both A and B require a separate freshness-tier
            architecture; B's filter-pushdown contributions remain valid
            beneath that architecture.
        C5:
          verdict: DEGRADES
          rationale: |
            C5 inherits the warmed-cache invariant equally. LazyFrame
            execution is purely query-time; the underlying df.lazy() still
            wraps the warmed (eagerly-validated) DataFrame. C5 is
            freshness-neutral. Sub-second SLA needs an upstream change.
          migration_trigger: |
            Same as A and B. Freshness-tier is a separate architectural
            axis from the cascade-vs-join question.

    - id: SC-5
      name: "Regulatory inversion (per-row provenance: which entity contributed which column, when, by whom)"
      paths:
        A:
          verdict: DEGRADES
          rationale: |
            Path A denormalizes at warmup-time, COLLAPSING provenance
            (the cascaded value loses its "originated from offer.gid=X
            at timestamp Y by user Z" trail unless explicit metadata
            columns are added per cascade field). Per-cascade metadata
            triples the LOC cost (value + source_gid + source_timestamp).
          migration_trigger: |
            Compliance/audit ask for "show me where this column came
            from for row N." Today's HC-01 _CASCADE_SOURCE_MAP gives
            entity-type-level provenance only, not row-level.
        B:
          verdict: SURVIVES
          rationale: |
            Path B keeps target rows queryable at query-time. JOIN
            preserves source row identity (target.gid is in scope),
            making per-row provenance derivable from the join output.
            Telemetry decorator (engine.py:76 trace_computation) can
            log provenance at span level.
          migration_trigger: |
            Audit requirement materializes; B's query-time composition
            advantage becomes load-bearing.
        C5:
          verdict: SURVIVES
          rationale: |
            Same as B — query-time composition preserves source row
            identity; LazyFrame chain output includes target columns
            with source-side gids. .explain() output is itself a
            machine-readable provenance trail.
          migration_trigger: |
            Same as B.

  worst_break_summary: |
    SC-3 x C5 = BREAKS (data-service joins). This is the critical limiting
    factor for any S5 verdict that elevates C5 as sole architectural
    commitment for Phase 2+. C5's subsumption thesis is partial precisely
    here. SC-4 produces BREAKS for A as well, but freshness is a separate
    axis the spike does not adjudicate.
```

---

## §3 Reversibility Analysis

```yaml
reversibility:
  path_a:
    classification: "two-way per cascade field; one-way once registered"
    rationale: |
      Adding a cascade field is bounded (S2a phase 1c); REMOVING is
      bounded but accumulates: HC-07 (S3 cache key drift) means schema
      version downgrade requires cache flush. Per-field LOC cost is
      additive over time; rollback cost grows with adoption count.
    cheap_back_out: "single field within first sprint of adoption"
    expensive_back_out: "10+ cascade fields accumulated over Phases 2-3"
    one_way_door_threshold: "first cross-entity field that gates a paying-customer report"

  path_b:
    classification: "two-way during build (feature-flagged); one-way once contract surface lifts"
    rationale: |
      B-1 through B-4 are flag-gated (S2b §4 explicitly notes
      rollback_point per phase). B-5 (entity-prefix syntax in PredicateNode
      models.py:47) is contract-breaking — once a public PAT/S2S caller
      adopts entity-prefixed field names, deprecation cycle required.
    cheap_back_out: "B-1 (depth lift) and B-4 (data-service) revertible"
    expensive_back_out: "B-2/B-3 split-filter logic embedded in production"
    one_way_door_threshold: "B-5 (entity-prefix DSL change shipped to a non-internal caller)"

  path_c5:
    classification: "two-way (weak form); two-way with friction (strong form)"
    rationale: |
      C5 weak (S3 §5 stub): single-line revert (df.lazy().filter(...)
      .collect() back to df.filter(...)). C5 strong: execute_join
      signature change is internal-package contract; adapter wrapper
      preserves backward compat per S2b C5-2 phase.
    cheap_back_out: "weak form is mechanical revert"
    expensive_back_out: "strong form requires unwinding lazy join signature; ~3-5d work"
    one_way_door_threshold: "NONE within autom8y-asana boundary (no caller-visible contract change)"

  reversibility_ranking:
    1: C5 (highest reversibility)
    2: B (medium; feature-flag-gated)
    3: A (lowest; per-field one-way after registration)
```

---

## §4 Critic-Substitution Attestation on S3

Per `critic-substitution-rule` (dispatcher S3 = prototype-engineer; rite-disjoint
critic = S4 moonshot-architect). Five load-bearing claims attested below.
Self-ref MODERATE ceiling enforced for this critic's STRONG verdicts —
external/source citations required.

### Claim 1 — Polars 1.38.1 pushes equality predicates over joins

**S3 evidence**: §5 `.explain()` strong form output shows
`FILTER [(col("section")) == ("ACTIVE OFFER")]` inside the RIGHT PLAN before
the join.

**Attestation: CONCUR (with grade qualification)**

**Rationale**: The `.explain()` output as quoted in S3 §5 is the canonical
Polars optimizer artifact and shows the predicate inside RIGHT PLAN's FROM
clause. This is the documented behavior of Polars predicate pushdown per the
official user guide on optimizations (SCOUT SRC-002). External sanity-check
2026-04-27 confirms predicate pushdown is a documented LazyFrame
optimization, though the specific LEFT→INNER rewrite is not surfaced in
user-facing docs. S3's reading of EXPLAIN is correct on the predicate-pushdown
claim itself.

**Grade**: [PLATFORM-EMPIRICAL | MODERATE] for the autom8y-asana-specific
claim (S3 ran the benchmark; not independently re-run by S4). [STRONG | external]
inheritable for the general Polars optimizer behavior per Polars docs and
DeepWiki LazyFrame module. The grade is bounded by the fact that S4 did NOT
re-run the prototype; verbatim re-execution would lift to STRONG.

**Evidence anchor**: `.ledge/spikes/PROTO-cascade-vs-join.md:212-247`
(EXPLAIN output verbatim, both weak and strong form); SCOUT SRC-002 (Polars
user guide); Polars LazyFrame DeepWiki module (deepwiki.com/pola-rs/polars/2.3-lazyframe).

### Claim 2 — LEFT JOIN → INNER JOIN rewrite is semantically equivalent for non-null equality filters

**S3 framing**: §7 states "this is semantically correct for equality
predicates (unmatched contacts where section_right IS NULL cannot satisfy
== 'ACTIVE OFFER' anyway), but it is a semantic contract change callers must
be aware of."

**Attestation: DIVERGE**

**Rationale**: S3 acknowledges the rewrite as a "semantic contract change"
but UNDERWEIGHTS its impact for the export use case. Vince's canonical query
is "contacts from accounts in Reactivation+Outreach pipelines." If a future
analogous query is "contacts from accounts that may or may not have an
active offer" (the LEFT-OUTER intent: include contacts with NO offer as a
distinct rowset), the optimizer's LEFT→INNER rewrite SILENTLY REMOVES those
contacts when the caller filters by an offer column.

This is not a "callers must be aware" issue — it is a wrong-result silent
failure pattern equivalent to S2b's B-R1 "OR-spanning-tables silent failure."
S3 categorizes B-R1 as critical for Path B but treats the analogous C5 risk
as merely semantic. The asymmetry is unjustified.

The export use case specifically may surface this: an account-grain CSV
that filters by `offer.status == 'cancelled'` would, under LEFT→INNER
rewrite, exclude accounts that have no offer at all — and the report's
denominator silently shifts. This is exactly the F-HYG-CF-A "wave-level
CLOSED without per-item receipts" failure mode the platform has burned on
before, only at query-result altitude.

**Grade**: [PLATFORM-INTERNAL | STRONG] for the divergence — the
asymmetric severity treatment is verifiable by side-by-side reading of
S3 §5 (B-R1 framing) vs S3 §7 (LEFT→INNER framing). The wrong-result
risk is structural, not opinion.

**Evidence anchor**: `.ledge/spikes/PROTO-cascade-vs-join.md:378-388`
(LEFT→INNER framing); `.ledge/spikes/INTEGRATE-pathB-and-C5.md:168-173`
(B-R1 wrong-result silent failure framing); the asymmetry is the divergence.

**Required S5 resolution**: §5 below specifies what S5 must address.

### Claim 3 — PredicateNode DSL classifier problem is design question, not empirical unknown

**S3 reasoning**: §8 declares override clause NOT triggered because "the
gaps above are design questions for S4/S5, not empirical gaps that require
a Path B prototype to resolve."

**Attestation: CONCUR (with caveat)**

**Rationale**: The classifier problem (PredicateNode `Comparison.field` is
free-form string per `query/models.py:47` verified — STRONG file:line) is
indeed a DSL design question. No PredicateCompiler caller in the live
codebase that I could verify uses an entity-prefix convention; the
referenced `query/fleet_query_adapter.py` does NOT exist (file absent at
verification time 2026-04-27). The dispatch's reference to that file as
"existing PredicateNode caller" is itself stale — backwards-compat surface
is narrower than the dispatch implies, which actually STRENGTHENS S3's
reasoning that the classifier problem is design-altitude.

**Caveat**: S3 assumes that "design question" means "no prototype needed,"
but the DSL change has ripple effects on the public schema visible to
PAT/S2S callers. A semantic prototype (e.g., draft a PredicateNode with
`Comparison.field` = "offer.section" and confirm the compiler raises
UnknownFieldError per `query/compiler.py:220-225`) would take 30 minutes
and would empirically validate the migration cost. S3 declined to do this;
it remains open. This is a "could have been cheap to validate, was not"
gap, not an attestation refutation.

**Grade**: [PLATFORM-INTERNAL | STRONG] for the file-absence finding
(`fleet_query_adapter.py` not present, verified by Read tool error
2026-04-27). [MODERATE] for the general concurrence with S3's reasoning.

**Evidence anchor**: `src/autom8_asana/query/models.py:47`
(`field: str = Field(description="Column name to compare against.")`);
`src/autom8_asana/query/compiler.py:220-225` (UnknownFieldError raise);
absence of `src/autom8_asana/query/fleet_query_adapter.py` (Read error
2026-04-27).

### Claim 4 — C5-SC-04 cross-service join exclusion is not Phase 1 blocker

**S3 reasoning**: implicit in §8 override-clause NO recommendation; C5-SC-04
acknowledges data-service exclusion but treats it as Phase 2 scope question.

**Attestation: CONCUR**

**Rationale**: Phase 1's telos (Reactivation+Outreach single-entity export
by 2026-05-11) does not require cross-service joins. Vince's original ask
is account-grain export, not enrichment from autom8y-data. Phase 1 ships
single-entity export regardless of which path S5 selects per inquisition
§1. The data-service question is correctly Phase 2+ scope per the
non-foreclosure invariant.

**Caveat for S5**: my §2 stress matrix (SC-3) shows this exclusion is the
WORST BREAKS verdict for C5 across all five scenarios. It is not a Phase 1
blocker but it IS the limiting factor on C5 as a long-horizon sole
commitment. S5's verdict carrier should explicitly address whether the
Phase 2+ data-service trajectory makes a B-coexistence path mandatory.

**Grade**: [PLATFORM-INTERNAL | STRONG] for the Phase 1 scope claim
(verified against frame.md telos.verified_realized_definition.deadline =
2026-05-11). [MODERATE] for the long-horizon caveat.

**Evidence anchor**: `.sos/wip/frames/project-asana-pipeline-extraction.md`
telos block; `.ledge/spikes/PROTO-cascade-vs-join.md:323-330` (C5-SC-04
documented shortcut); §2 SC-3 above.

### Claim 5 — C5 inherits warmed cache as eager-validated; LazyFrame composition is purely query-time

**S2b claim, S3 implicitly accepted**: S2b §7 coupling table line 270-274:
"Cascade validation runs on merged_df at WARMUP TIME (cascade_validator.py:54
takes merged_df as input from progressive builder, not query-time df).
LazyFrame execution at QUERY TIME does not affect the null-audit denominator
because validation has already completed before df reaches engine.py."

**Attestation: CONCUR**

**Rationale**: Independent verification of `cascade_validator.py:46-176`
confirms `validate_cascade_fields_async` accepts `merged_df: pl.DataFrame`
(eager) at line 47, runs at warmup time (called from
`api/preload/progressive.py` per S2a §2), produces a corrected eager
DataFrame, and returns it. Line 91's `null_mask = merged_df[col_name].is_null()`
operates on eager DataFrame; corrections applied at line 142-159 with
`.with_columns()` produce eager output. No LazyFrame paths in the
validator.

The downstream `DataFrameProvider.get_dataframe` at `engine.py:129-133`
returns the warmed (validator-corrected) eager DataFrame. C5's
`df.lazy()` wraps this validated output — Polars `.lazy()` on an in-memory
DataFrame is documented as a thread-safe read-only view per Polars
architecture (SCOUT SRC-002 ecosystem). LazyFrame composition cannot
re-trigger the validator because the validator is not in the call path —
it executed at warmup, before query routing.

The contract is preserved.

**Grade**: [PLATFORM-INTERNAL | STRONG] (verified independently by S4 via
Read tool of `cascade_validator.py:46-176` against S2b/S3 claims).

**Evidence anchor**: `src/autom8_asana/dataframes/builders/cascade_validator.py:46-54`
(signature: `merged_df: pl.DataFrame` — eager); `src/autom8_asana/dataframes/builders/cascade_validator.py:91`
(`null_mask = merged_df[col_name].is_null()` — eager operation);
`src/autom8_asana/dataframes/builders/cascade_validator.py:142-159` (corrections
via `.with_columns()` — eager output); `src/autom8_asana/query/engine.py:129-133`
(DataFrameProvider returns warmed eager df).

---

## §5 Required Resolution for S5 Verdict Carrier

**Single DIVERGE recorded: Claim 2 (LEFT→INNER rewrite semantic risk).**

The S5 verdict carrier MUST address the following resolution requirement
in `verdict.critic_substitution_chain.s3_s4_divergence_resolution`:

```yaml
s3_s4_divergence_resolution:
  divergent_claim: "LEFT JOIN to INNER JOIN rewrite is semantically equivalent for non-null equality filters"
  s3_position: "semantic contract change callers must be aware of"
  s4_position: "wrong-result silent failure equivalent to B-R1; underweighted"

  required_in_verdict:
    - "Explicit policy on whether C5 (any form) is acceptable WITHOUT a guard against LEFT→INNER rewrite for queries where the LEFT-OUTER semantics are user-facing"
    - "If C5 is selected, specify the engine-side defense (e.g., assert post-EXPLAIN that JOIN type matches request.join.how, or document at API layer that equality predicates on join-target columns produce INNER semantics)"
    - "If A or B is selected, explicitly note that the LEFT→INNER risk is C5-only and not a constraint on the chosen path"
    - "Cite the export use case where this matters: account-grain CSV with filter on offer column may silently drop accounts-without-offer"

  rationale_for_required_resolution: |
    F-HYG-CF-A precedent (RETROSPECTIVE-VD3-2026-04-18.md:145) burned the
    platform on wave-level claims without per-item receipts. The LEFT→INNER
    rewrite is the same anti-pattern at query-result altitude: the
    optimizer silently changes the denominator. S5 verdict authority
    cannot leave this implicit. Telos-integrity gate at /sos wrap
    requires per-item receipts; the verdict carrier requires per-claim
    resolution.
```

---

## §6 Phase 2 Architectural Commitment Constraint Set

**NOT a verdict — these are constraints S5's verdict MUST respect**, derived
from §2 stress matrix worst-cases and §4 attestation findings. S5 selects
the path; these constraints bound the selection.

```yaml
constraints_for_s5:

  - id: CONSTRAINT-1
    name: "Cross-service join trajectory must be addressed"
    derived_from: "SC-3 worst-BREAKS for C5; B is the sole SURVIVES for cross-service"
    requirement: |
      Verdict MUST state explicitly whether Phase 2+ data-service
      enrichment is in-scope. If yes, C5 alone is insufficient; either
      Path B coexistence is required OR a documented "data-service
      enrichment uses bespoke path" exception. Silent omission is
      verdict-failure.

  - id: CONSTRAINT-2
    name: "LEFT→INNER rewrite defense"
    derived_from: "Claim 2 DIVERGE attestation (§4)"
    requirement: |
      If C5 is any part of the verdict, the engine MUST defend against
      silent LEFT→INNER rewrite when caller specified how='left'. Either
      runtime EXPLAIN inspection OR API documentation OR query
      construction guard. Per §5 above.

  - id: CONSTRAINT-3
    name: "Per-shape vs per-engine recurring cost discipline"
    derived_from: "S3 §9 break-even analysis (~2 cross-entity query shapes); §3 reversibility"
    requirement: |
      Verdict MUST disclose the projected count of cross-entity query
      shapes for Phases 2-3. If count <2, Path A's per-shape cost wins.
      If count >=2, C5/B's per-engine cost wins. The selection rationale
      must reference an actual product-roadmap-anchored count, not a
      hypothetical.

  - id: CONSTRAINT-4
    name: "Warmed-cache invariant preservation"
    derived_from: "Claim 5 CONCUR; Phase 1 freshness scope"
    requirement: |
      Whichever path is selected, SCAR-005/006 cascade defense layer
      (cascade_validator.py warmup-time validation, WarmupOrderingError
      re-raise barrier at progressive.py:696-699) MUST remain intact.
      Sub-second freshness (SC-4) is OUT of scope for this verdict;
      verdict must explicitly NOT promise freshness improvements.

  - id: CONSTRAINT-5
    name: "PredicateNode DSL contract surface stability through Phase 2"
    derived_from: "Claim 3 CONCUR + caveat; absence of fleet_query_adapter.py"
    requirement: |
      If Path B (B-5) entity-prefix syntax is contemplated, verdict MUST
      treat it as a one-way door per §3 reversibility ranking. Phase 1
      ships without DSL contract change; Phase 2 contract change requires
      explicit ADR with 6-month deprecation cycle.

  - id: CONSTRAINT-6
    name: "Migration-trigger observability before commitment"
    derived_from: "§2 migration_trigger fields per scenario"
    requirement: |
      Whichever path is selected, the verdict MUST identify which
      observable signals (production telemetry, .explain() output,
      cascade null rate, DataServiceClient hit rate) will fire when the
      chosen path begins to BREAK or DEGRADE under any of the five
      scenarios. Without observable signals, the selection is unfalsifiable.
```

---

## §7 Evidence Trail

| # | Claim | Source / file:line | Grade |
|---|---|---|---|
| 1 | engine.py:140-178 is the C5/B load-bearing seam | `src/autom8_asana/query/engine.py:139-178` (verified by Read) | [PLATFORM-INTERNAL \| STRONG] |
| 2 | Filter applied at L161 eager today | `src/autom8_asana/query/engine.py:159-161` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 3 | Join branches on JoinSpec.source data-service vs entity | `src/autom8_asana/query/engine.py:165-178` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 4 | total_count = len(df) materializes (engine.py:181) | `src/autom8_asana/query/engine.py:181` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 5 | _build_expr returns pl.Expr (compiler is lazy-composable) | `src/autom8_asana/query/compiler.py:121-148` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 6 | Comparison.field is free-form string (no entity-prefix) | `src/autom8_asana/query/models.py:47` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 7 | UnknownFieldError raised at compiler.py:220-225 | `src/autom8_asana/query/compiler.py:220-225` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 8 | join.py execute_join returns eager pl.DataFrame; matched_count via .height | `src/autom8_asana/query/join.py:175-181` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 9 | Target dedup + null-key filter at join.py:154-160 | `src/autom8_asana/query/join.py:142-160` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 10 | validate_cascade_fields_async signature: merged_df=pl.DataFrame (eager, warmup-time) | `src/autom8_asana/dataframes/builders/cascade_validator.py:46-54` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 11 | Cascade null thresholds 5%/20% calibrated against SCAR-005 30% incident | `src/autom8_asana/dataframes/builders/cascade_validator.py:31-32` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 12 | _CASCADE_SOURCE_MAP is hardcoded 5-entry dict | `src/autom8_asana/dataframes/builders/cascade_validator.py:185-191` (verified) | [PLATFORM-INTERNAL \| STRONG] |
| 13 | fleet_query_adapter.py absent at verification time (dispatch reference stale) | Read tool error 2026-04-27 on `src/autom8_asana/query/fleet_query_adapter.py` | [PLATFORM-INTERNAL \| STRONG] |
| 14 | Polars predicate pushdown is documented LazyFrame optimization | docs.pola.rs/user-guide/lazy/optimizations/; deepwiki.com/pola-rs/polars/2.3-lazyframe (web search 2026-04-27) | [STRONG \| external] |
| 15 | LEFT→INNER rewrite NOT explicitly documented in user-facing Polars docs | Web search 2026-04-27 returned no canonical doc reference for the rewrite | [MODERATE \| external negative] |
| 16 | S3 .explain() output (verbatim) shows predicate inside RIGHT PLAN before join | `.ledge/spikes/PROTO-cascade-vs-join.md:212-247` | [PLATFORM-EMPIRICAL \| MODERATE] (S3-attested; not S4-re-run) |
| 17 | S3 LEFT→INNER framing as "semantic contract change" (Claim 2 source) | `.ledge/spikes/PROTO-cascade-vs-join.md:378-388` | [PLATFORM-INTERNAL \| STRONG] (verbatim quote) |
| 18 | S2b B-R1 wrong-result silent failure framing | `.ledge/spikes/INTEGRATE-pathB-and-C5.md:168-173` | [PLATFORM-INTERNAL \| STRONG] |
| 19 | S2b coupling site: cascade validation NOT coupled to C5 | `.ledge/spikes/INTEGRATE-pathB-and-C5.md:270-274` | [PLATFORM-INTERNAL \| STRONG] (verified independently by S4) |
| 20 | Phase 1 deadline 2026-05-11 from frame telos | `.sos/wip/frames/project-asana-pipeline-extraction.md` telos block | [PLATFORM-INTERNAL \| STRONG] (per upstream artifact references) |
| 21 | F-HYG-CF-A canonical precedent (per-item receipts) | `RETROSPECTIVE-VD3-2026-04-18.md:145` (per telos-integrity-ref skill) | [PLATFORM-INTERNAL \| STRONG] (cited in skill body) |

### §7.1 Self-attestation grade ceiling

Per `self-ref-evidence-grade-rule`: this artifact's claims about the spike's
long-horizon survivability and S3 attestations cap at MODERATE except where
backed by:
- External literature/docs (web search 2026-04-27, Polars docs)
- Independent file:line Read verification (rows 1-13, 19 above)
- Verbatim quotation of upstream artifact text (rows 16, 17, 18)

The single DIVERGE on Claim 2 carries STRONG grade because it is structural
(side-by-side asymmetric severity treatment in S3's own text), not opinion.

### §7.2 Anti-pattern guard self-check

- **Theater detection**: §2 stress matrix produces specific
  SURVIVES/DEGRADES/BREAKS verdicts with named migration triggers per cell.
  No "all paths viable, you decide" formulation.
- **Pre-decision bias**: §2 evaluates all three live paths (A, B, C5)
  against five distinct scenarios. C5's worst-BREAKS (SC-3) is surfaced
  even though C5 is the S3-favored direction; B's unique SURVIVES (SC-3)
  is surfaced even though B was prototype-skipped.
- **Self-ref MODERATE ceiling**: STRONG appears only for external sources
  or independent file:line reads. The Claim 2 DIVERGE is graded STRONG on
  structural-asymmetry grounds, not self-reasoning.
- **Verdict-synthesis creep guard**: §6 frames as "constraint set S5 must
  respect," not "S5 should choose X." Each constraint cites its derivation
  source; none recommends a path.
- **Scenario discipline**: exactly 5 scenarios per dispatch; no enumeration
  beyond the brief.
- **Single-scenario brittleness guard**: 5 scenarios x 3 paths = 15 verdict
  cells; no path is evaluated in isolation. Migration triggers per cell.
- **Stateless future design guard**: §3 reversibility analysis maps each
  path's back-out cost concretely; no fantasy architectures.

---

*Authored by moonshot-architect (Station S4) under
`project-asana-pipeline-extraction` Phase 0 spike,
session-20260427-232025-634f0913. MODERATE self-attestation ceiling (STRONG
where independently verified or externally cited). Verdict authority pinned
at S5. Phase 2 non-foreclosure invariant respected — no design lock proposed.
Critic-substitution per `critic-substitution-rule` records 4 CONCUR + 1
DIVERGE on S3's load-bearing claims. Required S5 resolution per §5.*
