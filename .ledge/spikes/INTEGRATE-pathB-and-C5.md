---
type: spike
status: accepted
initiative: project-asana-pipeline-extraction
station: S2b
specialist: integration-researcher
related_spike: cascade-vs-join
paths: [B-join-pushdown, C5-lazyframe-delegation]
session_id: session-20260427-232025-634f0913
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
created: 2026-04-27
phase: 0
verdict_authority: S5 (tech-transfer)
this_artifact_authority: integration-cartography (NOT verdict)
upstream_artifact: .ledge/spikes/SCOUT-cascade-vs-join.md
parallel_artifact: .ledge/spikes/INTEGRATE-pathA.md (S2a, Path A)
frame: .sos/wip/frames/project-asana-pipeline-extraction.md
---

# INTEGRATE — Path B (join-engine pushdown) + Path C5 (Polars LazyFrame delegation) Dependency Map (Station S2b)

## §1 Telos Echo

Pulse rerooted. Vince and every future caller can produce a parameterized account-grain export via dual-mount endpoint without custom scripting; Phase 1 verifies against the original Reactivation+Outreach CSV ask by 2026-05-11. This artifact is integration cartography for Paths B and C5; verdict authority is S5. Phase 2 non-foreclosure invariant respected — no design lock proposed; this is dependency cost mapping, not recommendation.

---

## §2 Path B — Files-Touched Map

```yaml
path_b_files_touched:
  - file: src/autom8_asana/query/join.py
    lines: "70"
    change_type: constant_lift
    description: "MAX_JOIN_DEPTH=1 must lift to >=2 to permit traversal of join-target predicates across hops"
    blast_radius: localized
    confidence: high
  - file: src/autom8_asana/query/compiler.py
    lines: "53-63, 192-241"
    change_type: extension
    description: "OPERATOR_MATRIX dtype-keys today; must extend predicate-classifier to recognize join-target fields (fields not in primary schema). _compile_comparison line 218-225 raises UnknownFieldError when field absent — must be augmented to defer resolution to join-target schema rather than reject"
    blast_radius: localized_to_compiler
    confidence: medium
    assumption: "Predicate-classifier can be added without restructuring AST; if AST must change to carry target-entity tag per node, blast radius doubles"
  - file: src/autom8_asana/query/engine.py
    lines: "139-178"
    change_type: composition_reorder
    description: "Lines 159-161 (df.filter(filter_expr)) + 163-178 (join enrichment) currently FILTER-then-JOIN. Path B requires conditional reorder to JOIN-then-FILTER when filter targets join-target columns, OR introduce two filter passes with the second post-join. Filter expression also must be split into primary-only and target-only halves prior to dispatch"
    blast_radius: load_bearing_on_engine
    confidence: medium
    assumption: "Reorder preserves correctness for OR-groups spanning primary+target fields; if not, query rewrite logic required (Substrait-like)"
  - file: src/autom8_asana/query/models.py
    lines: "27-123"
    change_type: untouched_or_minor
    description: "PredicateNode DSL stays as-is per SCOUT §3.2. Comparison.field at L47 is a free-form string today; no entity-prefix convention. May need optional entity-prefix syntax (e.g., 'business.booking_type') if compiler cannot infer target from context"
    blast_radius: contract_surface_risk
    confidence: low
    assumption: "If entity-prefix syntax introduced, this is a contract change visible to all PAT/S2S callers — Phase 1 contract spec must coordinate"
  - file: src/autom8_asana/query/hierarchy.py
    lines: "104-149"
    change_type: extension
    description: "find_relationship + get_join_key serve depth-1 lookups. Depth-N requires graph traversal (BFS/DFS) over ENTITY_RELATIONSHIPS at L101; cycle detection needed"
    blast_radius: localized
    confidence: medium
  - file: src/autom8_asana/query/guards.py
    lines: "45-65"
    change_type: extension
    description: "QueryLimits has max_predicate_depth=5 but no max_join_depth or max_predicate_target_breadth guard. Path B introduces multi-target predicates; new limit field needed to prevent fan-out"
    blast_radius: localized
    confidence: high
  - file: src/autom8_asana/query/errors.py
    lines: "(unverified)"
    change_type: extension
    description: "JoinError exists; new error class needed for predicate-target-not-resolvable (field exists in no joinable schema)"
    blast_radius: trivial
    confidence: high
```

---

## §3 Path B — Hidden Coupling Map

```yaml
path_b_hidden_coupling:
  - coupling_site: "engine.py:163-178 join branching on join.source"
    discovery_method: "Read query/engine.py L163-178; engine dispatches to _execute_entity_join vs _execute_data_service_join based on JoinSpec.source"
    coupling_strength: high
    why_hidden: "Path B's filter-pushdown logic must mirror the same source dispatch; cross-service joins (data-service) load target via DataServiceJoinFetcher AFTER primary filter today (engine.py:589 fetcher.fetch_for_join(primary_df=df,...)). Pushing filter onto data-service target means ordering filter resolution before fetch — fundamentally different control flow"
    risk_to_path_b: "Data-service join cannot use the same in-process pushdown mechanism; Path B must either (a) limit filter pushdown to entity joins only, or (b) extend DataServiceClient request shape"
  - coupling_site: "join.py:142-160 target deduplication + null-key filter"
    discovery_method: "Read query/join.py L142-160; execute_join calls target.unique(subset=[join_key], keep='first') and target.filter(pl.col(join_key).is_not_null())"
    coupling_strength: high
    why_hidden: "Filter pushdown that targets join-target columns must execute against the deduped+null-filtered subset, not the raw target_df. Pushdown that runs before deduplication may produce wrong-result silent failures (worst-case per SCOUT §3.2)"
    risk_to_path_b: "Predicate semantics over join target depends on dedup ordering; documented dedup is keep='first' which is order-sensitive — pushed predicates against unsorted source could yield non-deterministic results"
  - coupling_site: "engine.py:140-157 classification + section filter composition"
    discovery_method: "Read query/engine.py L140-157; filter_expr is composed of (where) AND (classification IN sections) AND (section==filter)"
    coupling_strength: medium
    why_hidden: "Path B must split filter_expr into primary-only and target-only at compile time, BUT classification + section are always primary-entity columns. If split logic naively partitions by 'field-not-in-primary-schema', it works; if it partitions by syntactic position, classification may be misrouted"
    risk_to_path_b: "Section/classification filter must explicitly route to primary; new compiler must know about these columns or operate on AST after section/classification expressions are appended"
  - coupling_site: "engine.py:130-133 DataFrameProvider.get_dataframe load order"
    discovery_method: "Read query/engine.py L130-133; primary df loaded BEFORE join target in execute_rows; target loaded at L515-519 inside _execute_entity_join only after filter applied"
    coupling_strength: high
    why_hidden: "Path B with JOIN-then-FILTER requires loading target BEFORE filter — change inverts current load ordering. Cache warming and warmed-cache invariant (cascade defense layer 2 per scar-tissue.md:80-86) assume target is loaded only when needed; eager target load on every query has cache-pressure implications"
    risk_to_path_b: "Worst case: all queries with where-clauses but no join_spec still trigger target loads if predicate-classifier guesses wrong"
  - coupling_site: "models.py:24 imports JoinSpec from join.py"
    discovery_method: "Read query/models.py L24"
    coupling_strength: low
    why_hidden: "Circular-import risk if Path B introduces JoinSpec.predicate_pushdown bool or similar — JoinSpec is currently in query/join.py, models.py imports from it. Inverse dependency would create cycle"
    risk_to_path_b: "Module restructure may be required if JoinSpec gains predicate-aware fields"
  - coupling_site: "trace_computation decorator at engine.py:76 + join.py:90"
    discovery_method: "Read query/engine.py L76, query/join.py L90"
    coupling_strength: medium
    why_hidden: "Telemetry spans currently bracket execute_rows wholesale and execute_join separately. Path B's filter-pushdown changes the span topology — pushed filter executes inside join span, breaking the existing 'computation.duration_ms' attribution at engine.py:221"
    risk_to_path_b: "SLO/observability dashboards keyed on 'entity.query_rows' vs 'entity.join' span names will misattribute time after pushdown"
```

---

## §4 Path B — Migration Phases

```yaml
path_b_phases:
  - phase: B-1
    name: "MAX_JOIN_DEPTH lift + guard"
    files: ["query/join.py:70", "query/guards.py:45-65"]
    effort: 0.5d
    confidence: high
    rollback_point: "Revert depth to 1; QueryLimits guard ensures no caller can exploit"
  - phase: B-2
    name: "Predicate-classifier in compiler (target-field resolution)"
    files: ["query/compiler.py:53-63,192-241", "query/hierarchy.py:104-149"]
    effort: 3-5d
    confidence: medium
    rollback_point: "Compiler default = current behavior (UnknownFieldError); flag-gated extension; revert flag"
    assumption: "AST shape unchanged; if AST extension required, +2d"
  - phase: B-3
    name: "Engine filter-split + JOIN-then-FILTER reorder"
    files: ["query/engine.py:139-178"]
    effort: 4-6d
    confidence: low
    rollback_point: "Behind feature flag; OR-spanning-tables case may force HARD rollback if rewrite is unsound"
    assumption: "Reorder is sound for AND-only and OR-only-on-one-side; mixed-table OR not validated"
  - phase: B-4
    name: "Data-service-join exclusion + telemetry span fix"
    files: ["query/engine.py:539-627"]
    effort: 1-2d
    confidence: medium
    rollback_point: "Limit pushdown to source==entity; data-service path bypasses pushdown — no rollback needed"
  - phase: B-5
    name: "Contract surface decision (entity-prefix syntax in PredicateNode)"
    files: ["query/models.py:27-123 (potentially)", "Phase 1 contract spec"]
    effort: TBD-by-architect
    confidence: low
    rollback_point: "Contract change is MOSTLY one-way; deprecation cycle if reverted"
    assumption: "If avoided via context-inference in compiler, B-5 collapses to zero work"
total_effort: 8.5-13.5d
total_confidence: medium-low
critical_path: B-2 -> B-3 (B-3 cannot start without classifier)
```

---

## §5 Path B — Risk Surface

```yaml
path_b_risks:
  - id: B-R1
    name: "Wrong-result silent failure on OR-spanning-tables"
    severity: critical
    surface: "engine.py:139-178 filter-split logic"
    detection: "Adversarial QA fixture with OR(primary.f1=x, target.f2=y); compare to JOIN-then-FILTER on full unioned df"
  - id: B-R2
    name: "Predicate over deduped+null-filtered target diverges from raw target semantics"
    severity: high
    surface: "join.py:154-160 dedup + null filter"
    detection: "Fixture with target rows that have duplicate join_keys + non-null filter values on duplicates"
  - id: B-R3
    name: "Cache-warming load ordering inversion increases cold-start latency"
    severity: medium
    surface: "engine.py:130-133, 515-519 + lifespan warmup"
    detection: "Cold-start metric on /rows with no join_spec but predicate naming target-only field"
  - id: B-R4
    name: "Telemetry attribution breaks SLO dashboards"
    severity: medium
    surface: "engine.py:76,221 + join.py:90,183"
    detection: "Span-name audit on production telemetry post-deployment"
  - id: B-R5
    name: "Hierarchy graph traversal cycle on N>1 hops"
    severity: medium
    surface: "query/hierarchy.py:104-149"
    detection: "Test with cyclic join graph (A->B, B->A discoverable via descriptor join_keys)"
  - id: B-R6
    name: "Contract surface change forecloses Phase 2 design space (entity-prefix syntax)"
    severity: high (Phase 2 non-foreclosure invariant)
    surface: "query/models.py:47 Comparison.field"
    detection: "Phase 1 contract review at PT-02"
poc_scope_for_path_b:
  must_validate: [B-R1, B-R2]
  success_criteria: "Adversarial fixture with OR-spanning-tables produces same result via Path B as via current FILTER-then-JOIN-then-FILTER baseline"
```

---

## §6 Path C5 — Files-Touched Map (validating SCOUT seam-claim)

**SCOUT seam-claim validation**: SCOUT §3.5 asserted C5 lands at `query/engine.py:140-180`. Read of the file (lines 139-178 inclusive) **confirms** the claim with one refinement: the load-bearing change site is L139-161 (filter expression composition + apply), with L163-178 (join enrichment) being the secondary site that switches from eager to lazy participation. SCOUT's range 140-180 is accurate within ±2 lines.

```yaml
path_c5_files_touched:
  - file: src/autom8_asana/query/engine.py
    lines: "140-178"
    change_type: composition_mode_flip
    description: "Lines 140-142 build filter_expr (pl.Expr — already lazy by construction). Line 161 calls df.filter(filter_expr) on eager pl.DataFrame. C5 switches to df.lazy().filter(filter_expr).<join>.collect() so Polars optimizer can push predicates over joins natively. Specifically: replace L161 + L163-178 with a single LazyFrame chain that defers .collect() until after join enrichment"
    blast_radius: load_bearing_on_engine
    confidence: high
    assumption: "Polars optimizer pushes predicates over LEFT joins (the dedup'd target join shape at join.py:168-172). Polars docs (SCOUT SRC-002) confirm this for inner+left joins"
  - file: src/autom8_asana/query/join.py
    lines: "96-192 (execute_join)"
    change_type: signature_extension
    description: "execute_join takes pl.DataFrame today (L97-98). C5 minimal version keeps eager join via .collect() after lazy compose, then re-applies join. RICHER C5 changes execute_join signature to accept pl.LazyFrame and return pl.LazyFrame, deferring .collect() to engine.py L181 (total_count line)"
    blast_radius: contract_surface_risk
    confidence: medium
    assumption: "Eager-collect-before-join preserves match-stat counts (matched_count, unmatched_count at L177-181); lazy version requires .collect() before stat computation OR computing stats lazily via .filter(pl.col(...).is_not_null()).select(pl.len()).collect()"
  - file: src/autom8_asana/query/compiler.py
    lines: "121-148 (_build_expr)"
    change_type: untouched
    description: "Compiler already produces pl.Expr (verified at L121-148, e.g., col == value at L127). pl.Expr composes lazily by construction — no compiler change needed"
    blast_radius: zero
    confidence: high
  - file: src/autom8_asana/query/models.py
    lines: "27-123"
    change_type: untouched
    description: "PredicateNode DSL fully unchanged. C5 is composition-mode flip, not contract change"
    blast_radius: zero
    confidence: high
  - file: src/autom8_asana/query/guards.py
    lines: "45-65"
    change_type: untouched
    description: "Depth/limit guards unaffected — they operate on AST, not execution mode"
    blast_radius: zero
    confidence: high
  - file: src/autom8_asana/query/temporal.py
    lines: "1-119"
    change_type: untouched
    description: "TemporalFilter is an isolated dataclass-based filter for SectionTimeline (not PredicateNode). Does not interact with engine.py:140-178 path. No coupling to C5"
    blast_radius: zero
    confidence: high
  - file: src/autom8_asana/query/hierarchy.py
    lines: "65-149"
    change_type: untouched
    description: "Relationship registry serves join-key resolution; unaffected by composition mode"
    blast_radius: zero
    confidence: high
```

**SCOUT seam-claim verdict**: CONFIRMED. SCOUT §3.5 framing — "the cost is changing the execution mode from eager to lazy at the call site" — accurately describes the engine.py:140-178 change. The dominant additional finding from this cartography is that join.py:96-192 has a SIGNATURE-EXTENSION choice point (eager-collect-then-join vs lazy-pass-through) that SCOUT did not enumerate; the signature choice gates whether Polars optimizer can push predicates THROUGH the join (C5 strong form) vs only OVER the pre-join filter (C5 weak form).

---

## §7 Path C5 — Hidden Coupling Map

```yaml
path_c5_hidden_coupling:
  - coupling_site: "engine.py:181 total_count = len(df) materializes df"
    discovery_method: "Read query/engine.py L181"
    coupling_strength: high
    why_hidden: "len(df) requires .collect() on a LazyFrame. C5 must either (a) call .collect() at L181 — defeating the optimizer's late-materialization benefit for downstream pagination, or (b) use .height after explicit collect, or (c) restructure to call .collect() once at L222 (df.to_dicts) and compute total_count via the collected schema. Option (c) requires moving pagination logic"
    risk_to_c5: "Naive C5 still calls .collect() at L181, losing optimizer wins. Strong C5 requires reordering of L180-187 (pagination + total count)"
  - coupling_site: "cascade_validator.py:31-32 null-audit denominator"
    discovery_method: "Read dataframes/builders/cascade_validator.py L25-103"
    coupling_strength: zero (NOT coupled — validates SCOUT C5 claim)
    why_hidden: "Cascade validation runs on merged_df at WARMUP TIME (cascade_validator.py:54 takes merged_df as input from progressive builder, not query-time df). LazyFrame execution at QUERY TIME does not affect the null-audit denominator because validation has already completed before df reaches engine.py. CASCADE_NULL_WARN_THRESHOLD=0.05 / CASCADE_NULL_ERROR_THRESHOLD=0.20 are computed against the warmed cache, not lazy execution"
    risk_to_c5: "NONE. C5 inherits the warmed cache as eager-validated; LazyFrame composition is purely query-time"
  - coupling_site: "DataFrameProvider.get_dataframe at engine.py:129-133 returns pl.DataFrame (eager)"
    discovery_method: "Read query/engine.py L129-133"
    coupling_strength: high
    why_hidden: "Provider returns eager pl.DataFrame. C5 calls .lazy() on it. Polars LazyFrame.lazy() on already-warmed DataFrame is cheap (wraps in-memory) — but the cache layer at provider returns a SHARED reference; .lazy() does not clone. If multiple concurrent requests call .lazy().filter() on the same warmed DataFrame, Polars internal handling must be thread-safe"
    risk_to_c5: "Polars LazyFrame is documented thread-safe for read paths (per Polars architecture); needs prototype confirmation. SCAR-005/006 cache-coherence layer is unaffected because cache layer never mutates"
  - coupling_site: "trace_computation decorator + record_dataframe_shape at engine.py:76, join.py:90"
    discovery_method: "Read query/engine.py L76, query/join.py L90; record_dataframe_shape=True"
    coupling_strength: medium
    why_hidden: "record_dataframe_shape inspects df shape via .height/.width. On a LazyFrame, .width is cheap (schema-resident) but .height requires .collect() — or counts via .select(pl.len()). Telemetry decorator may inadvertently trigger materialization, defeating optimizer benefit"
    risk_to_c5: "Telemetry-induced materialization is silent perf loss; surfaces only under load test"
  - coupling_site: "join.py:177-181 matched_count/unmatched_count via .filter(...).height"
    discovery_method: "Read query/join.py L175-181"
    coupling_strength: high
    why_hidden: "matched_count = enriched.filter(pl.col(first_join_col).is_not_null()).height. .height on a LazyFrame requires .collect(). Strong C5 (lazy execute_join) must restructure stat computation OR perform .collect() inside execute_join — losing pushdown benefit if stats run before final filter"
    risk_to_c5: "JoinResult contract (frozen dataclass at join.py:74-87) carries int counts; lazy version requires either (a) eager .collect() at stat point, (b) returning a LazyFrame with deferred stats, or (c) counts as Polars Expr resolved later"
  - coupling_site: "engine.py:215-217 select(valid_columns) on df"
    discovery_method: "Read query/engine.py L215-217"
    coupling_strength: low
    why_hidden: "Final .select() on LazyFrame is cheap; .to_dicts() at L222 forces collect. Single materialization point if pagination + select are deferred until L222"
    risk_to_c5: "Composable; this is the natural .collect() boundary"
```

---

## §8 Path C5 — Migration Phases

```yaml
path_c5_phases:
  - phase: C5-1
    name: "Naive lazy filter (weak form)"
    files: ["query/engine.py:140-161"]
    effort: 0.5-1d
    confidence: high
    rollback_point: "Single-line revert: df.lazy().filter(filter_expr).collect() back to df.filter(filter_expr)"
    delivers: "Predicate pushdown OVER pre-join filter only; no pushdown THROUGH join"
  - phase: C5-2
    name: "Lazy join pass-through (strong form)"
    files: ["query/engine.py:163-178", "query/join.py:96-192"]
    effort: 3-5d
    confidence: medium
    rollback_point: "execute_join signature change is contract-breaking inside the package; wrap with adapter for backward compat"
    delivers: "Predicate pushdown THROUGH join; Polars optimizer composes filter+join"
    assumption: "Polars LEFT join pushdown over filtered primary preserves match-stat semantics"
  - phase: C5-3
    name: "Restructure pagination + total_count for single .collect()"
    files: ["query/engine.py:180-187, 215-222"]
    effort: 1-2d
    confidence: medium
    rollback_point: "Re-introduce eager .collect() at L181"
    delivers: "Single materialization at L222; full optimizer benefit"
  - phase: C5-4
    name: "Telemetry decorator audit (record_dataframe_shape on lazy)"
    files: ["engine.py:76, join.py:90; autom8y_telemetry contract"]
    effort: 0.5-1d
    confidence: medium
    rollback_point: "Disable record_dataframe_shape on lazy paths"
    delivers: "Avoid silent materialization via telemetry"
total_effort: 5-9d
total_confidence: medium-high (weak form HIGH; strong form MEDIUM)
critical_path: C5-1 standalone validates pushdown wins; C5-2 unlocks Phase 2 fit
```

---

## §9 Path C5 — Risk Surface

```yaml
path_c5_risks:
  - id: C5-R1
    name: "Polars optimizer behavior under cascade-derived columns unverified (SCOUT-flagged)"
    severity: high
    surface: "engine.py:140-178 + cascade-derived columns in warmed schema"
    detection: "POC fixture: filter on cascade-derived column (e.g., business.booking_type) with primary entity = process; verify EXPLAIN plan shows predicate pushdown; verify result rows match eager baseline"
    file_line_entry_point: "src/autom8_asana/query/engine.py:140-178 (LazyFrame chain construction); cross-validate via .explain() or pl.DataFrame.lazy().filter(...).explain() output"
  - id: C5-R2
    name: "Match-stat semantics divergence (matched/unmatched count) under lazy join"
    severity: critical
    surface: "join.py:175-181"
    detection: "POC compares JoinResult.matched_count between eager baseline and lazy form on fixture with known match topology"
  - id: C5-R3
    name: "Telemetry decorator triggers silent materialization"
    severity: medium
    surface: "engine.py:76, join.py:90 (record_dataframe_shape=True)"
    detection: "Profile lazy path; assert no .collect() before final L222"
  - id: C5-R4
    name: "Concurrent .lazy() on shared warmed DataFrame thread-safety"
    severity: medium
    surface: "engine.py:129-133 + provider cache layer"
    detection: "Concurrent /rows requests against same project_gid; Polars docs assert thread-safe reads but autom8y-asana cache layer is bespoke"
  - id: C5-R5
    name: "Phase 2 forecloser: weak-form C5 (engine.py only) does NOT deliver cross-entity pushdown"
    severity: high (Phase 2 non-foreclosure invariant)
    surface: "C5-1 alone produces single-entity pushdown; cross-entity requires C5-2 (lazy join)"
    detection: "Phase 2 design review against C5-2 vs C5-1 capability boundary"
poc_scope_for_path_c5:
  must_validate: [C5-R1, C5-R2]
  success_criteria: ".explain() output for filter+join LazyFrame chain shows predicate pushdown over join AND matched/unmatched counts match eager baseline on canonical 'contacts from active offers'-class fixture"
```

---

## §10 B-vs-C5 Compatibility Surface

```yaml
b_c5_compatibility:
  can_coexist: "yes-with-tension — both touch query/engine.py:139-178 as load-bearing seam; sequencing matters"
  shared_seams:
    - "src/autom8_asana/query/engine.py:139-178 (filter expression composition + join branching)"
    - "src/autom8_asana/query/join.py:96-192 (execute_join — Path B reorders, Path C5 may make signature lazy)"
    - "src/autom8_asana/query/compiler.py (Path B extends classifier; Path C5 leaves untouched but inherits any classifier output)"
  conflict_sites:
    - "engine.py:163-178: Path B reorders to JOIN-then-FILTER; Path C5 wants to defer collect through both filter+join. If both adopted, C5 lazy chain must compose with B's split-filter logic — composable in principle but doubles complexity at this seam"
    - "join.py execute_join signature: Path B keeps eager (passes split filters); Path C5 strong-form makes lazy. Adopting both requires execute_join to accept lazy + split-predicate args"
  if_both_adopted: "C5 should land first (lower risk, validates Polars optimizer behavior); Path B then layers ON the lazy infrastructure rather than building parallel split-filter eager logic. If B lands first, C5 retrofit requires reworking B's split-filter dispatch into the lazy chain. Reverse order doubles rework cost"
  composition_thesis: "C5 is largely a SUBSET of what Polars-optimizer-driven Path B would do automatically. If C5-2 (strong form) confirms Polars handles cross-entity filter pushdown over the dedup'd left join correctly, Path B may be SUBSUMED — i.e., C5 strong-form delivers Path B's promised capability without engine.py:139-178 split-filter complexity. This would be S5's verdict-relevant finding. POC required to confirm or refute"
```

---

## §11 Evidence Trail

```yaml
evidence:
  - claim: "Path B touches query/engine.py:139-178 (filter+join composition)"
    citation: "src/autom8_asana/query/engine.py:139-178 (verified via Read)"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "MAX_JOIN_DEPTH=1 baseline at query/join.py:70"
    citation: "src/autom8_asana/query/join.py:70 (verified)"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "PredicateCompiler raises UnknownFieldError at L218-225 when field absent from primary schema"
    citation: "src/autom8_asana/query/compiler.py:220-225"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "JoinSpec source dispatch at engine.py:165-178 (entity vs data-service)"
    citation: "src/autom8_asana/query/engine.py:165-178"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "execute_join dedup + null-key filter at join.py:154-160"
    citation: "src/autom8_asana/query/join.py:154-160"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "DataServiceJoinFetcher.fetch_for_join executes after primary filter (engine.py:589)"
    citation: "src/autom8_asana/query/engine.py:587-594"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "C5 seam at engine.py:140-180 confirmed; refined to 139-178"
    citation: "src/autom8_asana/query/engine.py:139-178 (verified via Read against SCOUT §3.5 claim)"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "Compiler produces pl.Expr already (lazy-composable by construction)"
    citation: "src/autom8_asana/query/compiler.py:121-148 (_build_expr returns pl.Expr)"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "Cascade null-audit denominator NOT coupled to C5 (validates SCOUT C5-R1 framing)"
    citation: "src/autom8_asana/dataframes/builders/cascade_validator.py:54 (validate_cascade_fields_async takes merged_df at warmup, before query-time)"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "Match-stat counts at join.py:175-181 require .height (forces .collect() on LazyFrame)"
    citation: "src/autom8_asana/query/join.py:175-181"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "TemporalFilter at query/temporal.py:24-80 isolated from PredicateNode (no engine coupling)"
    citation: "src/autom8_asana/query/temporal.py:1-119 (no import from query.models or query.engine)"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "QueryLimits has no max_join_depth field (Path B requires extension)"
    citation: "src/autom8_asana/query/guards.py:45-65"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "Hierarchy registry serves depth-1 lookups (find_relationship at L104-125)"
    citation: "src/autom8_asana/query/hierarchy.py:104-149"
    grade: "[PLATFORM-INTERNAL | STRONG]"
  - claim: "Polars LazyFrame predicate pushdown over joins is a documented optimization"
    citation: "SCOUT-cascade-vs-join.md SRC-002 (Polars user guide)"
    grade: "[STRONG | external] (inherited from SCOUT)"
  - claim: "models.py imports JoinSpec from join.py (potential circular-import risk for Path B)"
    citation: "src/autom8_asana/query/models.py:24"
    grade: "[PLATFORM-INTERNAL | STRONG]"

self_attestation_grade: "MODERATE ceiling per self-ref-evidence-grade-rule. STRONG appears only for file:line verifications (PLATFORM-INTERNAL) and inherited external citations (SCOUT SRC-NNN). No verdict synthesis; verdict authority pinned at S5"

anti_pattern_self_check:
  hidden_coupling_count: "Path B = 6 sites; Path C5 = 5 sites + 1 zero-coupling validation. Both above the >=3 threshold"
  scout_seam_claim: "Validated against engine.py:139-178; SCOUT range confirmed within ±2 lines"
  no_verdict_creep: "§4, §5, §8, §9 enumerate costs and risks; no recommendation language. §10 surfaces a composition thesis flagged for S5 adjudication, not asserted as preferred path"
  out_of_scope_observed: "SCAR-REG-001 untouched; CascadingFieldResolver SPIKE untouched; no Path A comparison (S5 owns)"
```

---

*Authored by integration-researcher (Station S2b) under `project-asana-pipeline-extraction` Phase 0 spike, session-20260427-232025-634f0913. MODERATE grade on self-attestations. Verdict authority pinned at S5. Phase 2 non-foreclosure invariant respected — no design lock proposed.*
