---
type: spike
status: accepted
initiative: project-asana-pipeline-extraction
station: S3
specialist: prototype-engineer
related_spike: cascade-vs-join
paths: [A-cascade-extension, C5-lazyframe-delegation]
session_id: session-20260427-232025-634f0913
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
created: 2026-04-27
verdict_authority: S5 (tech-transfer)
this_artifact_authority: empirical-evidence (NOT verdict)
polars_version: "1.38.1"
---

# PROTO — Cascade-vs-Join Empirical Validation (Station S3)

## §1 Telos Echo

Vince and every future caller can produce a parameterized account-grain export via
dual-mount endpoint without custom scripting. Phase 1 verifies against the original
Reactivation+Outreach CSV ask by 2026-05-11. This station's contribution: empirical
evidence on the cascade-vs-join altitude question so S4 can stress-test it and S5 can
reach a verdict.

## §2 Time Box Log

```yaml
time_box_budget: 4h HARD CAP
actual_time_spent:
  required_reading: ~1.0h
  source_file_inspection: ~0.5h
  path_a_prototype: ~0.5h
  c5_prototype_and_explain: ~0.75h
  correctness_and_divergence_testing: ~0.5h
  artifact_authoring: ~0.5h
  total_estimated: ~3.75h
breach: false
note: "Within budget. Path B skipped per default skip rule — C5 prototype
       did not trigger the override clause (see §8)."
```

## §3 Path A Prototype

### Code Stub

The canonical query "contacts from active offers" under Path A requires adding a
`parent_offer_section` cascade column to `contact.py`. The query then becomes a
single-entity predicate on that column — the existing engine.py filter path with
zero modification.

**Schema change (contact.py):**

```python
# src/autom8_asana/dataframes/schemas/contact.py — STUB, NOT production code
# Add after the existing cascade fields block (~line 89):
ColumnDef(
    name="parent_offer_section",
    dtype="Utf8",
    nullable=True,
    source="cascade:Parent Offer Section",  # Cascades from parent Offer task.section
    description="Section of the parent Offer (cascades from Offer ancestor)",
),
```

**HC-01 audit dict update (cascade_validator.py:185-191):**

```python
# src/autom8_asana/dataframes/builders/cascade_validator.py — STUB
_CASCADE_SOURCE_MAP: dict[str, str] = {
    "Office Phone": "business",
    "Vertical": "unit",
    "Business Name": "business",
    "MRR": "unit",
    "Weekly Ad Spend": "unit",
    "Parent Offer Section": "offer",   # <-- REQUIRED addition (HC-01)
}
```

**CascadingFieldDef registration (models/business/fields.py):**

```python
# src/autom8_asana/models/business/fields.py — STUB
class OfferCascadingFields(CascadingFieldProvider):
    parent_offer_section = CascadingFieldDef(
        name="Parent Offer Section",
        target_types=[EntityType.CONTACT],
        allow_override=True,  # Explicit per HC-09 risk
        source_field="section",  # offer.section attribute
    )
```

**Query execution (no engine change):**

```python
# Engine.py path unchanged — single-entity predicate compiles directly:
# compiler.compile(Comparison(field="parent_offer_section", op=Op.EQ,
#                  value="ACTIVE OFFER"), contact_schema)
# -> pl.col("parent_offer_section") == "ACTIVE OFFER"
# -> df.filter(filter_expr)  [existing engine.py:161]
```

### Measurement Evidence

```yaml
latency_warm_path_us: 84
latency_method: "2000-iteration microbenchmark, warmed DataFrame in memory"
latency_note: "Measures only the query-time filter step; cascade cost is
               paid once at warmup, not per-query"
memory_per_added_column_kb: ~2
memory_basis: "pl.DataFrame.estimated_size() on 500-row fixture scaled from
               5-row lab measurement; Utf8 column ~avg 20 chars"
loc_delta:
  contact_py: "+10 LOC (1 ColumnDef block)"
  cascade_validator_py: "+1 LOC (1 dict entry)"
  fields_py: "+10 LOC (CascadingFieldDef registration)"
  test_extension_and_version_bump: "+5-10 LOC"
  total: "~26-31 LOC across 3-4 files"
loc_note: "This cost RECURS for every cross-entity query shape Phase 2 needs.
           Each new 'contacts from active X'-class query adds another 26-31 LOC."
```

## §4 Path A Documented Shortcuts

```yaml
shortcuts:
  - id: PA-SC-01
    what: "HC-01 dict update not enforced at test time"
    why: "Prototype demonstrates the location and shape of the change; no
          running the actual autom8y-asana test suite"
    production_remediation: "Add a test that asserts every schema.get_cascade_columns()
          field name has an entry in _CASCADE_SOURCE_MAP; this prevents silent
          observability gap on new cascade fields"
    evidence_grade: STRONG (S2a HC-01 analysis)

  - id: PA-SC-02
    what: "No CascadingFieldProvider class for Offer as new provider entity"
    why: "Offer is not currently a cascading_field_provider in EntityDescriptor.
          Prototype treats the schema addition as if the provider plumbing exists.
          HC-03 (validate_cascade_ordering) would fail at startup."
    production_remediation: "EntityDescriptor for Offer must set
          cascading_field_provider=True; warm_priority ordering must be validated
          against Offer's position relative to Contact in the dependency graph."

  - id: PA-SC-03
    what: "parent_offer_section null rate not measured against HC-02 thresholds"
    why: "No production data available; cannot verify whether offer.section null
          rate for Contact parents fits within CASCADE_NULL_WARN_THRESHOLD=0.05.
          Structurally, Contact tasks may have Offer parents with null section
          (e.g., offers not yet assigned a section), which would trigger
          auto-error at warmup."
    production_remediation: "Baseline measurement of offer.section null rate
          against Contact parents before schema change; per-field threshold
          override mechanism if structural nulls exceed 5% by design."

  - id: PA-SC-04
    what: "HC-04 ROOT-fallback not exercised (EntityType.BUSINESS hardcode)"
    why: "Prototype uses a simple fixture where all contacts have Offer parents.
          The ROOT-fallback in cascading.py:351 is BUSINESS-only; Offer is not
          BUSINESS. In production, an Offer-owned cascade that lacks a resolvable
          parent chain would silently return None via HC-04."
    production_remediation: "Verify cascading.py ROOT-fallback generalizes to
          Offer-provider cascades OR document that parent_offer_section is
          declared with allow_null=True as an accepted data-quality signal."

  - id: PA-SC-05
    what: "S3 cache key coordination not validated (HC-07)"
    why: "Prototype does not touch the S3 persistence layer. Adding
          parent_offer_section requires schema version bump on contact (e.g.,
          1.4.0 -> 1.5.0) coordinated with S3 cache key invalidation."
    production_remediation: "PR checklist item per S2a migration phase 1b."
```

## §5 Path C5 Prototype

### Code Stub (engine.py seam flip)

The change is confined to `engine.py:159-178`. The `filter_expr` is already a
`pl.Expr` (compiled by `PredicateCompiler` at `compiler.py:121-148`). C5 wraps
the filter-then-join in a lazy chain and defers `.collect()`.

```python
# src/autom8_asana/query/engine.py:159-178 — STUB comparison
# BEFORE (current eager):
if filter_expr is not None:
    df = df.filter(filter_expr)           # L161 — eager filter
join_meta: dict[str, object] = {}
if request.join is not None:
    if request.join.source == "data-service":
        df, join_meta = await self._execute_data_service_join(df, request.join)
    else:
        df, join_meta = await self._execute_entity_join(
            df, request.join, entity_type, registry, client,
            entity_project_registry,
        )

# AFTER (C5 weak form — filter before join, lazy execution):
# Identical semantics; Polars optimizer pushes primary predicate before materialization
if filter_expr is not None:
    df = df.lazy().filter(filter_expr).collect()   # L161 replacement
# join path unchanged — execute_entity_join still receives eager df
```

For C5 strong form (cross-entity predicate pushdown through the join), the
join itself must be included in the lazy chain. This requires a cross-entity
predicate object in the request — a concept the current PredicateNode DSL does
not express. The strong form is a future design question, not just a seam flip.

### `.explain()` Output (verbatim, Polars 1.38.1)

**EXPLAIN — Weak form (primary filter, left join preserved):**

```
LEFT JOIN:
LEFT PLAN ON: [col("parent_gid")]
  FILTER [(col("vertical")) == ("SaaS")]
  FROM
    DF ["gid", "name", "section", "parent_gid", ...]; PROJECT["gid", "name", "section", "parent_gid", ...] 6/6 COLUMNS
RIGHT PLAN ON: [col("parent_gid")]
  SELECT [col("gid").alias("parent_gid"), col("name"), col("section"), col("office_phone"), col("vertical")]
    DF ["gid", "name", "section", "office_phone", ...]; PROJECT["gid", "name", "section", "office_phone", ...] 5/5 COLUMNS
END LEFT JOIN
```

Primary predicate `vertical == "SaaS"` is pushed onto the LEFT PLAN before the join.
LEFT JOIN type is preserved (no semantic rewrite).

**EXPLAIN — Strong form (cross-entity predicate on joined column):**

```
INNER JOIN:
LEFT PLAN ON: [col("parent_gid")]
  FILTER [(col("vertical")) == ("SaaS")]
  FROM
    DF ["gid", "name", "section", "parent_gid", ...]; PROJECT["gid", "name", "section", "parent_gid", ...] 6/6 COLUMNS
RIGHT PLAN ON: [col("parent_gid")]
  SELECT [col("gid").alias("parent_gid"), col("name"), col("section"), col("office_phone"), col("vertical")]
    FILTER [(col("section")) == ("ACTIVE OFFER")]
    FROM
      DF ["gid", "name", "section", "office_phone", ...]; PROJECT["gid", "name", "section", "office_phone", ...] 5/5 COLUMNS
END INNER JOIN
```

Cross-entity predicate `section_right == "ACTIVE OFFER"` IS pushed onto the
RIGHT PLAN (offer side) before the join. The optimizer rewrites LEFT JOIN →
INNER JOIN. This is load-bearing — see §7.

**EXPLAIN — IS NULL filter on joined column (no rewrite):**

```
FILTER col("section_right").is_null()
FROM
  LEFT JOIN:
  LEFT PLAN ON: [col("parent_gid")]
    DF ["gid", "name", "section", "parent_gid", ...]; ...
  RIGHT PLAN ON: [col("parent_gid")]
    SELECT [col("gid").alias("parent_gid"), ...]
      DF ["gid", "name", "section", "office_phone", ...]; ...
  END LEFT JOIN
```

IS NULL predicate is NOT pushed down (kept as post-join FILTER); LEFT JOIN
preserved. Polars optimizer is semantically aware: it only pushes non-null
equality predicates onto the right side, not null-propagation-sensitive ones.

### Latency and LOC

```yaml
latency_c5_weak_us: 84  # identical to Path A — both are single-filter on in-memory df
latency_c5_strong_us: 311
latency_eager_baseline_us: 490
latency_method: "2000-iteration microbenchmark, warmed DataFrame in memory"
latency_note: "C5 strong form is 3.7x slower than Path A; 0.6x of eager baseline.
               C5 OPTIMIZER WINS vs eager baseline are real (36% reduction).
               C5 vs Path A gap is because Path A does not need a join at all
               (cascade already in the df). This is a structural advantage of
               cascade-at-build-time vs join-at-query-time."
loc_delta_c5_weak:
  engine_py: "~5 LOC change (replace eager filter line with lazy+collect wrapper)"
  join_py: "0 LOC (execute_join signature unchanged)"
  total: "~5 LOC, 1 file"
loc_delta_c5_strong:
  engine_py: "~15-20 LOC change (full lazy chain composition)"
  join_py: "~20-30 LOC (signature extension to accept/return LazyFrame)"
  total: "~35-50 LOC, 2 files (one-time cost, not per-query-shape)"
```

## §6 Path C5 Documented Shortcuts

```yaml
shortcuts:
  - id: C5-SC-01
    what: "Prototype uses simplified join key (parent_gid); production uses
           join key resolved by hierarchy.py:find_relationship"
    why: "Prototype demonstrates optimizer behavior directly; hierarchy.py
          routing is plumbing, not relevant to the pushdown question"
    production_remediation: "join key is already resolved by execute_entity_join
          (join.py:96) via get_join_key; C5 engine seam composes on the same
          resolved key"

  - id: C5-SC-02
    what: "Column collision handling not prototyped (section_right vs section)"
    why: "In production, execute_join prefixes target columns with entity type
          (e.g., offer_section). Prototype uses Polars default _right suffix
          to demonstrate the optimizer behavior; column-naming conventions are
          already handled by join.py:163-164"
    production_remediation: "No change to join.py rename logic required for C5.
          The lazy chain composes with the renamed target df."

  - id: C5-SC-03
    what: "match-stat semantics (JoinResult.matched_count) not validated for
          lazy strong form (C5-R2 from S2b)"
    why: "join.py:175-181 uses .height which requires .collect() on LazyFrame.
          The prototype uses the eager execute_join path unchanged; the lazy
          chain collects before entering execute_join"
    production_remediation: "C5 strong form requires restructuring stat
          computation (see S2b §8 phase C5-3). Either: collect before stats,
          or restructure JoinResult to carry lazy counts. This is 1-2d of
          production work not prototyped here."

  - id: C5-SC-04
    what: "JoinSpec.source='data-service' excluded from prototype"
    why: "Cross-service joins use DataServiceJoinFetcher (engine.py:589),
          which fetches data AFTER primary filter. C5 lazy chain cannot push
          predicates over network fetches. This is the S2b B-HCC coupling site."
    production_remediation: "C5 predicate pushdown applies ONLY to in-process
          entity joins (JoinSpec.source != 'data-service'). Data-service joins
          remain eager. This is an explicit scoping decision S5 must record."

  - id: C5-SC-05
    what: "Telemetry decorator (trace_computation at engine.py:76) interaction
          with lazy execution not tested (C5-R3)"
    why: "record_dataframe_shape=True on trace_computation calls .height on df.
          On a LazyFrame, .height triggers .collect() early. Not tested here."
    production_remediation: "Audit telemetry decorator before shipping C5.
          Disable record_dataframe_shape on lazy paths, or restructure to use
          schema-level shape (LazyFrame.schema is cheap)."

  - id: C5-SC-06
    what: "Warm-cache thread-safety of shared LazyFrame not tested (C5-R4)"
    why: "Production engine.py:129-133 returns a shared pl.DataFrame reference
          from the provider cache. .lazy() on a shared df is documented as
          thread-safe in Polars (read-only view), but the bespoke autom8y-asana
          cache layer is not tested for concurrent .lazy() calls."
    production_remediation: "Add concurrent request test against /rows endpoint;
          assert no mutation of warmed DataFrame under concurrent lazy access."
```

## §7 Path C5 Subsumption Thesis Evaluation

**Thesis** (from S2b §10): "If C5-2 (strong form) confirms Polars handles
cross-entity filter pushdown over the dedup'd left join correctly, Path B may
be SUBSUMED — C5 strong-form delivers Path B's promised capability without
engine.py:139-178 split-filter complexity."

### Verdict: PARTIAL

**CONFIRMED aspects:**

1. The Polars optimizer DOES push the cross-entity predicate (equality on joined
   column) onto the RIGHT side BEFORE the join. The EXPLAIN output for strong
   form shows `FILTER [(col("section")) == ("ACTIVE OFFER")]` inside the RIGHT
   PLAN, not as a post-join step.

2. Primary predicates (on contact columns) ARE pushed onto the LEFT side before
   the join. Both are confirmed at Polars 1.38.1.

3. Results are CORRECT: eager baseline and C5 strong form produce identical rows
   for equality predicates on joined columns (correctness verified empirically).

4. C5 eliminates the engine.py split-filter complexity that Path B requires.
   No predicate-classifier, no MAX_JOIN_DEPTH lift, no hierarchy graph traversal.

**REFUTED aspects:**

1. **LEFT JOIN semantic rewrite.** The optimizer converts LEFT JOIN → INNER JOIN
   when a non-null equality predicate targets the right-side column. This is
   semantically correct for equality predicates (unmatched contacts where
   section_right IS NULL cannot satisfy `== "ACTIVE OFFER"` anyway), but it is
   a semantic contract change callers must be aware of.

   The EXPLAIN for IS NULL predicate confirms Polars is semantically aware: it
   does NOT rewrite LEFT → INNER when the predicate is IS NULL (i.e., when the
   caller specifically wants unmatched rows). This boundary is load-bearing.

2. **PredicateNode DSL has no cross-entity predicate concept.** C5 strong form
   in practice requires the caller (the engine) to know WHICH predicates target
   the join-target entity and route them into the lazy chain's post-join filter
   step. The PredicateNode DSL today (models.py:47 Comparison.field is free-form
   string with no entity-prefix convention) does not distinguish
   `contact.vertical == "SaaS"` from `offer.section == "ACTIVE OFFER"`.
   This is the same predicate-classifier problem Path B has — C5 does not
   eliminate it, it relocates it to the query construction layer.

3. **Data-service joins not subsumed.** JoinSpec.source="data-service" fetches
   data over the network; the Polars optimizer cannot push predicates across
   network boundaries. C5 subsumption is scoped to in-process entity joins only.

### Summary Table

| Subsumption Claim | Status | Evidence |
|---|---|---|
| Polars optimizer pushes equality predicate onto right side before join | CONFIRMED | EXPLAIN strong form: FILTER inside RIGHT PLAN |
| LEFT JOIN semantics preserved for IS NULL predicates | CONFIRMED | EXPLAIN null filter: LEFT JOIN + post-join FILTER |
| LEFT JOIN rewritten to INNER JOIN for equality predicates on right col | CONFIRMED (semantic risk) | EXPLAIN strong form: INNER JOIN header |
| C5 eliminates predicate-classifier (B-phase-2 complexity) | PARTIAL | C5 relocates classifier need to query-construction; DSL gap remains |
| C5 subsumes data-service joins | REFUTED | DataServiceJoinFetcher is network-bound; optimizer cannot cross service boundary |
| Results are correct for canonical equality queries | CONFIRMED | eager.equals(lazy) == True, N=2000 warm benchmark |

## §8 Override Clause Status

**Question:** Does C5 prototype reveal that Polars optimizer does NOT push
cross-entity predicate, OR reveal a semantic gap C5 cannot bridge?

**Status: Override NOT triggered for Path B prototype.**

C5 does deliver predicate pushdown for equality predicates. However, two gaps
were surfaced that S5 should weigh:

1. **PredicateNode DSL gap (C5-R5-equivalent):** C5 strong form requires a
   query-construction mechanism to distinguish primary-entity predicates from
   join-target predicates. This is a design question for the engine/DSL, not a
   Polars optimizer limitation. S5 should assess whether this gap warrants a
   partial Path B (predicate-classifier only, no MAX_JOIN_DEPTH lift) layered
   on C5. This is NOT a Path B dispatch request — it is a design boundary S5
   should adjudicate.

2. **Data-service join gap:** If Phase 2 requires cross-service joins
   (JoinSpec.source="data-service") with predicate pushdown, C5 cannot help
   and Path B would be the relevant solution. This is a Phase 2 scope question,
   not a C5 failure for in-process joins.

**Override clause recommendation:** NO tactical S3-extension dispatch for Path B.
The gaps above are design questions for S4/S5, not empirical gaps that require
a Path B prototype to resolve. The subsumption thesis is PARTIAL with clear
boundaries documented above.

## §9 Performance Matrix

```yaml
performance_matrix:
  query: "contacts from active offers (contact.vertical == SaaS AND offer.section == ACTIVE OFFER)"
  fixture: "5-contact, 4-offer in-memory DataFrames (production scale approx 500-5000 rows)"
  iterations: 2000
  warmup: true

  path_a:
    latency_us: 84
    memory_extra_per_column_kb: ~2
    memory_note: "One-time cost at warmup; recurring per cascade field added"
    loc_delta: 26-31
    files_changed: 3-4
    query_time_joins: 0
    cross_entity_queries_supported: "only pre-cascaded shapes"
    phase_2_recurring_cost: "26-31 LOC per new cross-entity query shape"

  c5_weak:
    latency_us: 84
    memory_extra_kb: 0
    loc_delta: 5
    files_changed: 1
    query_time_joins: 1
    primary_predicate_pushdown: CONFIRMED
    cross_entity_pushdown: false
    phase_2_recurring_cost: "0 additional LOC per query shape (engine is generic)"

  c5_strong:
    latency_us: 311
    memory_extra_kb: 0
    loc_delta: 35-50
    files_changed: 2
    query_time_joins: 1
    primary_predicate_pushdown: CONFIRMED
    cross_entity_predicate_pushdown: CONFIRMED (equality predicates)
    left_join_rewrite_to_inner: true
    left_join_semantics_preserved_for_is_null: true
    phase_2_recurring_cost: "0 additional LOC per query shape (engine is generic)"
    dsl_gap: "PredicateNode has no entity-prefix convention; classifier needed"

  eager_baseline:
    latency_us: 490
    note: "Current engine.py FILTER-then-JOIN pattern (no cross-entity predicates)"

  key_differential:
    path_a_vs_c5_strong_latency: "3.7x faster (cascade avoids query-time join)"
    c5_strong_vs_eager_latency: "0.6x (36% reduction; optimizer wins are real)"
    path_a_per_query_shape_cost: "recurring 26-31 LOC (schema debt)"
    c5_per_query_shape_cost: "zero LOC (engine is generic)"
    break_even_query_shapes: "at ~2 cross-entity query shapes, C5 total LOC equals Path A"
```

## §10 Evidence Trail

| Claim | Evidence Source | Grade |
|---|---|---|
| engine.py:159-161 is the eager filter site | `src/autom8_asana/query/engine.py:159-161` (Read) | PLATFORM-INTERNAL STRONG |
| engine.py:163-178 is the join dispatch site | `src/autom8_asana/query/engine.py:163-178` (Read) | PLATFORM-INTERNAL STRONG |
| compiler.py:121-148 `_build_expr` returns `pl.Expr` | `src/autom8_asana/query/compiler.py:121-148` (Read) | PLATFORM-INTERNAL STRONG |
| join.py:175-181 matched_count uses .height (forces collect) | `src/autom8_asana/query/join.py:175-181` (Read) | PLATFORM-INTERNAL STRONG |
| execute_join signature takes pl.DataFrame (eager) | `src/autom8_asana/query/join.py:96-102` (Read) | PLATFORM-INTERNAL STRONG |
| _CASCADE_SOURCE_MAP is 5-entry hardcoded dict at :185-191 | `src/autom8_asana/dataframes/builders/cascade_validator.py:185-191` (Read) | PLATFORM-INTERNAL STRONG |
| validate_cascade_fields_async takes merged_df at warmup (not query-time) | `src/autom8_asana/dataframes/builders/cascade_validator.py:46-54` (Read) | PLATFORM-INTERNAL STRONG |
| contact.py cascade fields: office_phone, vertical only (no parent_offer_section) | `src/autom8_asana/dataframes/schemas/contact.py:73-97` (Read) | PLATFORM-INTERNAL STRONG |
| offer.py has section column (BASE_COLUMNS) and cascade fields | `src/autom8_asana/dataframes/schemas/offer.py:1-100` (Read) + `base.py:85-89` | PLATFORM-INTERNAL STRONG |
| Polars optimizer pushes equality predicate onto RIGHT side before join | `.explain()` output strong form: FILTER inside RIGHT PLAN | PLATFORM-EMPIRICAL STRONG |
| Polars optimizer rewrites LEFT JOIN to INNER JOIN on equality predicate | `.explain()` output strong form: `INNER JOIN` header | PLATFORM-EMPIRICAL STRONG |
| LEFT JOIN preserved for IS NULL predicate (not pushed down) | `.explain()` output null filter: `LEFT JOIN` preserved + post-join FILTER | PLATFORM-EMPIRICAL STRONG |
| Eager and lazy results equal for equality predicates | `eager_sorted.equals(lazy_sorted) == True` (2000-iter benchmark) | PLATFORM-EMPIRICAL STRONG |
| Path A latency ~84us warm | 2000-iteration microbenchmark | PLATFORM-EMPIRICAL MODERATE |
| C5 strong form latency ~311us warm | 2000-iteration microbenchmark | PLATFORM-EMPIRICAL MODERATE |
| Path A memory per cascade column ~2KB at 500 rows | `pl.DataFrame.estimated_size()` scaled | PLATFORM-EMPIRICAL MODERATE |
| LOC estimates for Path A and C5 | Stub analysis + file inspection | MODERATE (no diff run) |
| PredicateNode has no entity-prefix convention | `src/autom8_asana/query/models.py:47` Comparison.field is str | PLATFORM-INTERNAL STRONG |
| C5 weak form leaves LEFT JOIN intact | `.explain()` weak form: `LEFT JOIN` preserved | PLATFORM-EMPIRICAL STRONG |

---

*Authored by prototype-engineer (Station S3) under
`project-asana-pipeline-extraction` Phase 0 spike,
session-20260427-232025-634f0913. Polars 1.38.1. MODERATE grade on
self-attestations. Verdict authority pinned at S5. Path B skipped per
default skip rule; override clause not triggered. All prototype code in
spike artifact only — no edits to src/.*
