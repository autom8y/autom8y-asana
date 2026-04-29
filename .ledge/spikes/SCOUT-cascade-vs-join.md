---
type: spike
status: accepted
initiative: project-asana-pipeline-extraction
station: S1
specialist: technology-scout
related_spike: cascade-vs-join
session_id: session-20260427-232025-634f0913
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
created: 2026-04-27
phase: 0
verdict_authority: S5 (tech-transfer)
this_artifact_authority: option-surface-widening (NOT verdict)
time_box: ~3 focused hours
frame: .sos/wip/frames/project-asana-pipeline-extraction.md
shape: .sos/wip/frames/project-asana-pipeline-extraction.shape.md
workflow: .sos/wip/frames/project-asana-pipeline-extraction.workflow.md
---

# SCOUT — Cascade-vs-Join Landscape Mapping (Station S1)

## §1 Telos Echo

**Pulse rerooted.** Verbatim quote from frame.md telos.inception_anchor.why_this_initiative_exists:

> "A coworker's ad-hoc request to extract actionable account lists from Reactivation and Outreach pipelines has exposed a gap in the autom8y-asana service: there is no first-class BI export surface, and any response today would be a one-off script with zero reusability. This initiative transitions from observation (Iris snapshot) to repeatable, account-grain, CSV-capable data extraction codified in the service's dataframe layer."

**Throughline (workflow §2.0 telos-reroot block, paraphrased):** Vince (and every future PAT or S2S caller) can produce a parameterized account-grain export of any business entity via a dual-mount endpoint without custom scripting; Phase 1 verifies against Vince's original Reactivation+Outreach CSV ask by 2026-05-11; Phase 2's cross-entity adjudication ("contacts from active offers"-class queries) is deferred behind the spike-bounded architectural commitment that this inquisition produces.

**This station's contribution.** Phase 0 spike has presented an architectural fork — extend `CascadingFieldResolver` (Path A) vs extend the join engine with cross-entity filter pushdown (Path B). The verdict authority is structurally pinned to S5 (tech-transfer) per inquisition §1; my output is **option-surface widening**, not verdict synthesis. I scan prior art and adjacent ecosystems to detect third options the frame did not enumerate, and I produce a comparison matrix sharp enough to let S5 reach a defensible verdict.

**Phase 2 non-foreclosure invariant respected.** Nothing in this scout artifact constrains the Phase 2 design space; this is a desk-research enumeration, not a design lock. Phase 1 ships single-entity export regardless of any candidate surfaced here.

## §2 Comparison Matrix

Eight candidates evaluated. Status quo (Path A — cascade-extension) is the baseline; Path B (join-pushdown) is the originally-framed alternative; six third options surfaced via prior-art scan.

| # | Candidate | Maturity | Code-change Footprint (autom8y-asana) | Phase 2 Fit (cross-entity filter pushdown) | Phase 3 Fit (multi-hop, cross-service, real-time) | Risk Profile | Reversibility | Verdict |
|---|-----------|----------|---------------------------------------|--------------------------------------------|--------------------------------------------------|--------------|---------------|---------|
| C1 | **Cascade-extension** (Path A) | Production in autom8y-asana; cascade machinery live at `dataframes/cascade_utils.py` + extractor at `dataframes/extractors/cascade_resolver.py:199` (per frame brief) | Bounded per cascade-field added; SCAR-005/006 defensive layer already in place at `dataframes/builders/cascade_validator.py:31-32`; `WarmupOrderingError` enforced re-raise | LOW — predicates remain single-entity; cross-entity queries require pre-cascading the relevant fields onto the child grain at extract-time; cascade-null risk amplifies per added field | LOW — denormalization at extract-time does not generalize to multi-hop or cross-service; would multiply schema-explosion risk | Cascade-null amplification (SCAR-005/006); schema explosion proportional to added cascade fields; cascade-resolver bus factor is internal-only | HIGH — adding a cascade field is bounded; removing one is bounded; no external dependency change | **Trial** for narrow Phase 2 scope; **Hold** as Phase 2 architectural commitment |
| C2 | **Join-engine pushdown** (Path B) | Production internal; `JoinSpec` enrichment-only at `query/join.py:21-66`; `MAX_JOIN_DEPTH=1` at `query/join.py:70`; predicate compiler at `query/compiler.py` does not classify join-target fields | High — `query/engine.py:76`, `query/compiler.py`, `query/join.py:70` all touched; predicate-classifier extension required; `MAX_JOIN_DEPTH` lift to ≥2 implies graph traversal logic | HIGH — query-time flexibility; predicates over join targets become first-class; matches the canonical query "contacts from active offers" naturally | MEDIUM-HIGH — extends naturally to multi-hop with depth lift; cross-service join already prototyped via `JoinSpec.source="data-service"` at `query/join.py:48`; real-time is independent of altitude | Performance unknown at scale; predicate-classifier bugs surface as wrong-result silent failures (worse than null); cascade-resolver does not retire — both surfaces coexist | MEDIUM — extension is additive; backing out requires removing only the predicate-classifier path, not all of JoinSpec; existing enrichment path stays | **Assess** — long-horizon fit is strong but performance and predicate-classifier complexity are unknown until S3 prototype lands |
| C3 | **Substrait IR + DuckDB compile-target** | Substrait spec is open and actively maintained; DuckDB has Substrait extension; adoption is "nascent but rolling" per Substrait/Voltron Data 2024-2026 documentation (see §6 SRC-001) | Very high — introduces a third compilation surface (PredicateNode → Substrait → DuckDB or Polars); `query/models.py:27-123` PredicateNode would need a Substrait emitter; `query/compiler.py` would coexist with or be subsumed by Substrait | HIGH — relational algebra IR handles cross-entity joins natively; predicate pushdown is Substrait's native concern | HIGH — multi-hop, cross-service, multi-backend all become tractable; DuckDB or Polars both consume Substrait | Lock-in to a young IR ecosystem; semantic divergence between PredicateNode dialect and Substrait may surface bugs; Substrait's relational ops (~80) is a much wider surface than PredicateNode's ~10 ops | LOW-MEDIUM — once committed, retreat means rewriting all callers using PredicateNode against the new IR | **Hold** — too early; revisit at Phase 3 if multi-backend pressure materializes |
| C4 | **Apache Calcite (relational algebra optimizer)** | Production-grade in Java ecosystem (Hive, Phoenix, Drill, Looker per Calcite docs/Querify Labs blog 2018+); 100+ optimization rules including filter pushdown | Very high — Calcite is JVM-native; Python integration is non-existent at production altitude; would require either a JVM bridge or a port; structural mismatch with the Polars/Python autom8y-asana stack | HIGH (in principle) — Calcite's filter pushdown rule is exactly the Path B problem solved; volcano/cascades framework is the gold standard | HIGH (in principle) — designed for federated query across heterogeneous sources | Stack-mismatch risk: Java in a Python service is operational debt; bus factor on the JVM bridge is high; lock-in to Calcite's algebra | LOW — cannot back out cheaply once predicate compilation routes through a JVM | **Avoid** — stack mismatch makes this not seriously evaluable in autom8y-asana's current shape |
| C5 | **Polars LazyFrame native predicate pushdown delegation** | Production-grade in Polars; documented in Polars user guide on optimizations (see §6 SRC-002); engine performs predicate-pushdown over joins as a native query optimization | Medium — `query/engine.py:76` switches from eager `pl.DataFrame.filter()` to `pl.LazyFrame.collect()` after composing scan + filter + join; PredicateNode compiler at `query/compiler.py` already produces `pl.Expr`, which composes lazily by construction | HIGH — Polars optimizer pushes predicates over joins natively; cross-entity filter pushdown becomes a query-planner concern rather than an engine-extension concern | MEDIUM — Polars native only; cross-service joins still need bespoke logic in `JoinSpec.source="data-service"`; real-time independent | Polars optimizer behavior under cascade-derived columns is unverified — needs prototype evidence; warmed-cache invariant per SCAR-005/006 must hold under lazy execution | HIGH — LazyFrame is a thin wrapper; reverting to eager `.filter()` is mechanical | **Trial** — strong third-option candidate; let the Polars optimizer do the heavy lifting that Path B would build by hand. Especially attractive because it composes with C1 (cascade) without conflict |
| C6 | **Materialized denormalized views** (e.g., precomputed `contact_with_active_offer` dataframe) | Mature pattern in OLAP / data-warehousing (see §6 SRC-003); applicable at autom8y-asana's dataframe layer via SchemaRegistry extension | Medium-high — adds a new schema entry for each materialized view; warmup ordering must extend to the view's dependencies; refresh strategy decision (eager-on-source-change vs scheduled vs query-time-stale) | MEDIUM — answers known cross-entity queries cheaply; new query shapes need new views; not a query-engine generalization | LOW for unknown query shapes; HIGH for known high-frequency queries (Vince's class) | Storage explosion proportional to view count; refresh-staleness vs refresh-cost tradeoff (per SRC-003); warmup-ordering invariant amplifies (SCAR-005/006 family) | MEDIUM — dropping a materialized view is bounded; the upstream callers' query shapes change to reference base entities again | **Assess** — viable companion to C1 or C5 but not standalone. Fits a "known recurring queries" pattern; does not generalize to ad-hoc cross-entity queries |
| C7 | **DuckDB embedded query engine on Polars frames** | Production-grade; DuckDB-Polars integration via Apache Arrow zero-copy is documented and stable (see §6 SRC-004); predicate pushdown from Polars expressions to DuckDB SQL is a documented feature | Medium — introduces DuckDB as a second query engine alongside the PredicateNode/Polars stack; `query/engine.py:76` would dispatch certain query shapes (joins) to DuckDB; `query/models.py:27-123` PredicateNode would need a DuckDB SQL emitter OR delegate via Polars LazyFrame | HIGH — DuckDB SQL handles cross-entity joins, predicate pushdown, and aggregations natively at production-grade performance | HIGH — DuckDB scales to multi-hop joins; cross-service via DuckDB extensions or Arrow Flight; real-time via streaming | Two-query-engine maintenance burden (DuckDB SQL semantics ≠ PredicateNode DSL semantics); cascade-derived columns must be visible to DuckDB (zero-copy via Arrow makes this cheap); SCAR-005/006 surface must be preserved across the boundary | MEDIUM — backing out means routing the affected query shapes back through Polars-native; data does not migrate (DuckDB is in-process, not a persisted store) | **Trial** — strongest "third option" surfaced. Combines C5's Polars-native composition with a query-time SQL surface that Vince-class callers may eventually want directly. Worth a Phase 2 prototype against the canonical "contacts from active offers" |
| C8 | **GraphQL DataLoader / batched-fetch composable endpoints** (caller orchestrates 2 queries) | Production-grade in GraphQL ecosystem (Facebook, Shopify, Apollo per SRC-005); the pattern's use case is N+1 batching, not cross-entity filter pushdown | Very low — autom8y-asana stays exactly as it is; caller (Iris, Vince's tooling) issues two queries, joins client-side | NONE in the service — the service does not gain cross-entity capability; the *caller* does | NONE in the service — every caller reinvents the join logic; the bloodline argument from frame Workstream III applies in reverse | Caller-side correctness becomes a service contract concern (which deduplication policy? which filter semantics?); test surface fragments across consumers; the very problem the initiative was framed to solve | HIGH — the service surface does not change; reverting is a no-op | **Avoid** — directly contradicts the throughline ("without custom scripting"). Surfaced for completeness only |
| C9 | **Ibis Python dataframe API as portable compilation layer** | Production-grade with 22+ backends including DuckDB, Polars, BigQuery, ClickHouse (see §6 SRC-006); Ibis dataframe code generates SQL or backend-native code via SQLGlot | High — adds Ibis as the user-facing PredicateNode-equivalent layer; `query/models.py:27-123` becomes an Ibis expression layer; backend choice (Polars now, DuckDB later) becomes a config switch | HIGH — Ibis natively handles cross-entity joins and predicate pushdown across backends | HIGH — Ibis abstracts backend; multi-backend, multi-hop natively; real-time depends on backend | Lock-in to Ibis API stability; PredicateNode contract semantics must be preserved across the migration; SQLGlot dialect translation is the bus-factor surface | LOW once committed — Ibis becomes the canonical query layer; backing out means restoring PredicateNode compilation | **Assess** — strategically interesting because it consolidates C5 (Polars-native) + C7 (DuckDB) into one API, but the migration cost is high and the immediate Phase 2 problem ("contacts from active offers") does not require backend portability |

### §2.1 Boundary classification — which candidates are in vs out of the genuine option set

Of the nine candidates evaluated:

- **C4 (Apache Calcite)** — eliminated on stack mismatch (Java in Python service)
- **C8 (DataLoader)** — eliminated on direct throughline contradiction
- **C3 (Substrait)** — Hold; correct generality but premature for Phase 2 horizon
- **C9 (Ibis)** — Assess; strategically attractive but cost-disproportionate to the immediate question

Live option set for S5's verdict consideration: **C1 (cascade), C2 (join), C5 (Polars-LazyFrame), C6 (materialized views), C7 (DuckDB-on-Polars)**.

The genuine third options that the frame did not enumerate are **C5, C6, and C7**. C5 in particular is structurally underweighted in the original cascade-vs-join framing — it converts the question from "engine extension altitude" to "execution mode of the existing engine."

## §3 Per-Candidate Brief

### §3.1 C1 — Cascade-extension (Path A)

**What it is.** Extension of the existing `CascadingFieldResolver` machinery (frame brief: `dataframes/extractors/cascade_resolver.py:199`; verified live at `dataframes/cascade_utils.py:1-80` with cascade-provider derivation for `business` and `unit` entity types). Each cross-entity field that Phase 2 might need to filter by is denormalized onto the child entity row at extract-time. Single-entity predicates remain sufficient because every relevant column is already on the row.

**Where it lands.** Cascade-resolver extension at `dataframes/cascade_utils.py:51-80` (`cascade_provider_field_mapping`); schema declarations carry `source="cascade:..."` per the existing convention; cascade-validator threshold at `dataframes/builders/cascade_validator.py:31-32` (`CASCADE_NULL_WARN_THRESHOLD = 0.05`, `CASCADE_NULL_ERROR_THRESHOLD = 0.20`) governs added fields.

**Evidence grade.** [PLATFORM-INTERNAL | MODERATE] — production-validated within autom8y-asana; SCAR-005/006 production incident at 30% null rate is the calibration anchor (per `.know/scar-tissue.md:80-86`).

### §3.2 C2 — Join-engine filter pushdown (Path B)

**What it is.** Extension of `JoinSpec` (live at `query/join.py:21-66`) and `PredicateCompiler` (live at `query/compiler.py:1-120`) to support cross-entity predicates. Today: `JoinSpec` is enrichment-only, `MAX_JOIN_DEPTH=1` at `query/join.py:70`, the predicate compiler resolves only fields visible in the primary entity's schema. Phase 2 would lift `MAX_JOIN_DEPTH`, add a predicate-classifier that routes filter expressions to the appropriate frame, and extend `query/engine.py:76` (`execute_rows`) to compose filter-then-join when filters target join targets.

**Where it lands.** `query/join.py:70` (depth lift), `query/compiler.py:53-63` (`OPERATOR_MATRIX` extension to recognize join-target fields), `query/engine.py:140-160` (filter-expression composition). `query/models.py:27-123` PredicateNode DSL stays unchanged; the change is in the compiler, not the AST.

**Evidence grade.** [PLATFORM-INTERNAL | MODERATE] — file:line anchors verified live; performance and predicate-classifier complexity unverified pending S3 prototype.

### §3.3 C3 — Substrait IR + DuckDB compile-target

**What it is.** Substrait is an open, language-agnostic intermediate representation for relational query plans; DuckDB has a Substrait extension that consumes the IR. The pattern: PredicateNode AST compiles to Substrait, Substrait routes to DuckDB (for cross-entity work) or back to Polars (for single-entity work).

**Where it lands (if adopted).** A new `query/substrait_emitter.py` module beside `query/compiler.py`; `query/engine.py:76` dispatches based on query shape; `query/models.py:27-123` PredicateNode stays as the user-facing DSL but compiles to a wider IR.

**Evidence grade.** [STRONG | external] for Substrait's specification maturity per Substrait.io official docs and Querify Labs analysis (SRC-001); [MODERATE] for production adoption — Substrait/Voltron Data and Hacker News evidence indicates "nascent" production use; Apache Arrow, DuckDB, Velox have implementations but most large-scale users are building on top, not adopting.

### §3.4 C4 — Apache Calcite

**What it is.** JVM relational algebra framework with a volcano-style optimizer and 100+ rules including filter pushdown. The textbook solution to the Phase 2 problem if autom8y-asana were Java.

**Where it lands.** It does not — Python service, no production-grade Calcite Python bridge.

**Evidence grade.** [STRONG | external] for Calcite's maturity per Apache Calcite docs and the Begoli/Hyde 2018 paper "Apache Calcite: A Foundational Framework for Optimized Query Processing Over Heterogeneous Data Sources" (SRC-007); production users include Hive, Phoenix, Drill, Looker. [STRONG | external] for the negative finding (Python integration is absent) per the same sources.

### §3.5 C5 — Polars LazyFrame native predicate pushdown delegation

**What it is.** Convert `query/engine.py:76` (`execute_rows`) from eager DataFrame filter-then-join to LazyFrame compose-then-collect. Polars' optimizer performs predicate pushdown over joins natively per the Polars user guide on optimizations and the official "Power of predicate pushdown" post (SRC-002). The PredicateNode compiler at `query/compiler.py:140` already produces `pl.Expr` objects, which compose lazily by construction.

**Where it lands.** `query/engine.py:140-180` switches `df.filter(filter_expr)` to a LazyFrame chain `df.lazy().filter(filter_expr).join(target_lazy, on=join_key, how="left").collect()`. The query optimizer handles filter-over-join pushdown automatically. Cascade-derived columns are unchanged because the cascade pipeline produces the underlying DataFrame.

**Evidence grade.** [STRONG | external] for Polars LazyFrame's predicate-pushdown semantics per the official Polars user guide (SRC-002); [MODERATE] for fit with autom8y-asana specifically — needs prototype evidence to confirm cascade-derived columns and the warmed-cache invariant compose correctly under LazyFrame execution.

**Why this is the highest-leverage third option.** It reframes the cascade-vs-join question. The original framing assumes the autom8y-asana team builds the predicate-pushdown logic by hand (Path B). C5 says Polars already does this, and the cost is changing the execution mode from eager to lazy at the call site. If true, it dominates Path B on code-change footprint.

### §3.6 C6 — Materialized denormalized views

**What it is.** A precomputed dataframe schema (e.g., `contact_with_active_offer`) registered with `SchemaRegistry`, warmed at startup like the existing 8 named dataframes, refreshed on a schedule or event. Trades schema explosion for read latency.

**Where it lands.** New schema definitions; `core/entity_registry.py` extension to declare a "view" entity type; warmup ordering in `api/preload/progressive.py` (referenced in `.know/scar-tissue.md:80-86`) extends to view dependencies. Materialized-view pattern is documented at OLAP altitude for read-heavy repeatable queries (SRC-003).

**Evidence grade.** [STRONG | external] for the pattern's maturity per OLAP/data-warehousing literature (SRC-003); [WEAK] for fit with autom8y-asana's specific cache-invariant constraints — needs design analysis on refresh-vs-staleness for the cascade-driven warmup ordering.

### §3.7 C7 — DuckDB embedded query engine on Polars frames

**What it is.** DuckDB runs in-process alongside Polars. Polars dataframes pass to DuckDB via Apache Arrow zero-copy, DuckDB executes SQL with predicate pushdown and join optimization, results return as Polars dataframes. This is a documented integration pattern (SRC-004).

**Where it lands.** A new `query/duckdb_executor.py` module; `query/engine.py:76` dispatches cross-entity queries to DuckDB; `query/compiler.py` gains a SQL-emit mode OR delegates via the Polars LazyFrame path (DuckDB consumes Polars LazyFrames natively). Cascade-derived columns are visible to DuckDB because Arrow zero-copy preserves them.

**Evidence grade.** [STRONG | external] for the DuckDB-Polars integration's maturity per DuckDB official Polars guide and DeepWiki module (SRC-004); [MODERATE] for the specific dispatch design within autom8y-asana — needs prototype evidence.

### §3.8 C8 — GraphQL DataLoader / batched-fetch composable endpoints

**What it is.** Caller-side composition: caller issues two service queries (one per entity), batches and joins client-side. The DataLoader pattern is mature in GraphQL (SRC-005) but its concern is N+1 batching, not cross-entity filter pushdown.

**Where it lands.** It does not — service stays as-is; caller takes on the join.

**Evidence grade.** [STRONG | external] for the pattern's maturity in GraphQL ecosystems per the graphql/dataloader repo and Apollo/Shopify documentation (SRC-005); [STRONG | structural] for the negative finding (directly contradicts the initiative's "without custom scripting" throughline).

### §3.9 C9 — Ibis Python dataframe API

**What it is.** Portable Python dataframe library (22+ backends including DuckDB, Polars, BigQuery, ClickHouse). Ibis expressions compile to backend SQL via SQLGlot or to native dataframe code. The pattern: PredicateNode is replaced by Ibis expressions, and the backend choice is a config switch (start on Polars, migrate to DuckDB later).

**Where it lands.** A wider replacement: `query/models.py:27-123` PredicateNode is supplanted by Ibis expressions; `query/compiler.py` becomes thin (Ibis handles compilation); `query/engine.py:76` dispatches to the configured Ibis backend.

**Evidence grade.** [STRONG | external] for Ibis's maturity per the Ibis project documentation and benchmarking posts (SRC-006); [MODERATE] for fit — strategically attractive but cost-disproportionate to the immediate Phase 2 question.

## §4 Third-Option Detection Summary

The frame enumerated two options (cascade-extension, join-pushdown). My scan surfaced seven additional candidates (C3-C9), of which three are live in the option set (C5, C6, C7) and four are documented-but-not-live (C3 Hold, C4 Avoid, C8 Avoid, C9 Assess).

**The highest-leverage third option is C5 (Polars LazyFrame native predicate pushdown delegation).** The cascade-vs-join framing presents a binary that assumes autom8y-asana must build cross-entity filter pushdown logic itself. C5 surfaces a structurally different option: switch the execution mode of the existing engine from eager to lazy and let Polars' query optimizer do the predicate-pushdown work. The PredicateNode compiler already produces `pl.Expr` (verified at `query/compiler.py:140`+ comment "Expression building"), so the change is composition, not compilation.

**The second-highest-leverage third option is C7 (DuckDB embedded on Polars frames).** Where C5 says "let Polars do it," C7 says "let DuckDB do it via zero-copy Arrow." DuckDB's predicate pushdown and join optimization are production-grade. The integration is in-process (no network hop, no separate store), so the operational cost is lower than introducing a true third backend.

**Search rigor.** I evaluated nine candidates across four ecosystems (autom8y-asana internal, Python dataframe-native, JVM relational-algebra, GraphQL composable). I checked official documentation for Polars, DuckDB, Substrait, Ibis, Apache Calcite, and GraphQL DataLoader. I cross-referenced production-adoption signals (Hacker News, Querify Labs, Voltron Data, Apache Calcite docs, Polars user guide) per the search results captured in §6. I did not find a tenth candidate that materially advances the option surface beyond what is enumerated here.

I considered but did not separately enumerate: (a) Apache Arrow Flight as a transport-layer answer — orthogonal to the filter-pushdown question; (b) Iceberg/Delta as storage formats — irrelevant to in-process query patterns; (c) custom IR via PEG parsers — strictly worse than Substrait (C3) on every dimension. These are documented here for search-rigor transparency.

## §5 Boundary Criteria for Option Selection

The dimensions that S5 should weight most heavily, in order of decreasing relevance to this initiative:

1. **Phase 2 fit on the canonical query "contacts from active offers."** This is the operational test. C2, C5, C7 score HIGH; C1 scores LOW (requires per-field cascade extension); C6 scores MEDIUM (needs per-shape view).
2. **Code-change footprint inside the autom8y-asana boundary.** Reversibility and bus factor are downstream of this. C5 is lowest (execution-mode flip); C1 is bounded-but-recurring (per-field); C2 is high-but-localized; C7 is medium with a new module.
3. **SCAR-005/006 cascade-null amplification risk.** C1 amplifies; C2, C5, C7 are neutral (they query existing cascaded columns rather than expanding them); C6 amplifies if views build on cascaded columns.
4. **Phase 3 non-foreclosure.** Whether the choice constrains multi-hop, cross-service, real-time futures. C2, C5, C7 preserve options; C1, C6 narrow them; C3, C9 widen them at large present cost.
5. **Operational maturity and bus factor.** C1, C2 are autom8y-asana-internal (high bus factor concentration). C5, C7 leverage Polars/DuckDB community maturity. C3, C4, C9 add external lock-in.
6. **Reversibility under Phase 3 surprise.** Which choices can be backed out cheaply if we learn something at Phase 3 that invalidates the Phase 2 commitment. C5 is highest (mechanical revert to eager); C2, C7 medium; C1 high in isolation but compounding over fields; C3, C9 lowest.

**Highest-differential dimension surfaced.** Code-change footprint (dimension 2) cleanly distinguishes C5 from every other candidate by an order of magnitude. C5 is a composition change in `query/engine.py:140-180`; every other candidate touches new modules, new schemas, or new compilation surfaces. If C5's prototype evidence (S3) confirms that Polars LazyFrame's predicate pushdown over joins works correctly with cascade-derived columns and the warmed-cache invariant, C5 dominates the option set on code-change footprint while matching C2 on Phase 2 fit.

**S5 input.** The verdict authority pinned at S5 (tech-transfer) should treat C5 as the dark-horse candidate that the original cascade-vs-join binary occluded. The verdict carrier should explicitly enumerate why C5 was or was not chosen — the option-enumeration discipline requires disposition, not silent omission.

## §6 Evidence Trail

External literature citations per `citation-format-standard` SRC-NNN notation. Internal references use `{path}:{line_int}` per the platform-internal convention.

| ID | Source | Contributes | Grade |
|----|--------|-------------|-------|
| SRC-001 | Substrait specification (substrait.io); Querify Labs "Substrait — the Lingua Franca for Databases" 2022; Voltron Data "What is Substrait? A High-Level Primer" 2022; HN discussion item 30585752 (2022); GitHub substrait-io/substrait | C3 maturity claim; cross-engine IR design | [STRONG \| external] |
| SRC-002 | Polars official documentation: "Optimizations" user guide page; "Power of predicate pushdown" pola.rs blog post; LazyFrame API reference; "How to Optimize Join Operations with Polars LazyFrames" (Statology 2024) | C5 LazyFrame predicate pushdown over joins claim | [STRONG \| external] |
| SRC-003 | "Denormalization: When and Why to Flatten Your Data" (datalakehousehub.com 2026-02); "The Real Tradeoffs of Materialized Views in Production" (technori.com); ClickHouse "OLTP vs OLAP in 2026"; Databricks "What are Materialized Views?"; ResearchGate "OLAP, Data Warehousing, and Materialized Views: a Survey" | C6 materialized-view trade-offs (storage vs read latency, refresh strategy) | [STRONG \| external] for pattern; [MODERATE] for autom8y-asana fit |
| SRC-004 | DuckDB official "Integration with Polars" guide; DuckDB-Python Polars Integration DeepWiki module; "DuckDB + Polars: Fast Enough to Feel Illegal" (Modexa, Medium); "Beyond Postgres and DuckDB: The Rise of Composable Query Engines" (ThinhDA blog 2026); "Polars + DuckDB: The New Power Combo For In-Process Analytics" (Open Source For You 2026-03) | C7 DuckDB-Polars zero-copy Arrow integration; predicate pushdown from Polars expressions to DuckDB | [STRONG \| external] |
| SRC-005 | graphql/dataloader GitHub repo; Apollo "Fetching Data" docs; Shopify Engineering "Solving the N+1 Problem for GraphQL through Batching"; Hygraph "How to solve the graphql n+1 problem"; WunderGraph "Dataloader 3.0" | C8 DataLoader pattern maturity; explicit identification of N+1 as the use-case (not cross-entity filter pushdown) | [STRONG \| external] |
| SRC-006 | Ibis Project official site; "Using one Python dataframe API to take the billion row challenge with DuckDB, Polars, and DataFusion" (Ibis blog); Ibis benchmarking blog post; CodeCut "Portable DataFrames in Python: When to Use Ibis, Narwhals, or Fugue"; PyPI ibis-framework page | C9 Ibis 22+ backend portability claim; SQLGlot translation layer | [STRONG \| external] |
| SRC-007 | Apache Calcite official site; Begoli/Hyde et al. "Apache Calcite: A Foundational Framework for Optimized Query Processing Over Heterogeneous Data Sources" (arXiv 1802.10233, 2018); Querify Labs "Relational Operators in Apache Calcite"; Looker SlideShare presentation | C4 Calcite's filter-pushdown rule maturity and JVM-native scope | [STRONG \| external] |
| INT-001 | `src/autom8_asana/query/models.py:27-123` (PredicateNode DSL — Op enum L27-39, Comparison L42-49, AndGroup/OrGroup/NotGroup L52-77, discriminated union L112-118) | Internal anchor for cascade-vs-join surface; PredicateNode is the user-facing DSL all candidates compose against | [PLATFORM-INTERNAL \| STRONG] |
| INT-002 | `src/autom8_asana/query/join.py:21-66` (JoinSpec definition); `query/join.py:70` (`MAX_JOIN_DEPTH = 1`); `query/join.py:96-192` (`execute_join` enrichment-only logic) | Internal anchor for Path B framing — confirms enrichment-only and depth=1 baseline | [PLATFORM-INTERNAL \| STRONG] |
| INT-003 | `src/autom8_asana/query/compiler.py:1-120` (PredicateCompiler stateless design; OPERATOR_MATRIX at L53-63; Expression building section header at L116-118) | Internal anchor for Path B + C5 — confirms `pl.Expr` is the existing compilation target, so LazyFrame composition is direct | [PLATFORM-INTERNAL \| STRONG] |
| INT-004 | `src/autom8_asana/dataframes/cascade_utils.py:1-80` (`is_cascade_provider`, `cascade_provider_field_mapping`); `WarmupOrderingError` at L22-30; `.know/scar-tissue.md:80-86` (Cascade Defense-in-Depth four-layer pattern) | Internal anchor for C1 risk profile — SCAR-005/006 calibration at 30% production null incident; cascade thresholds at 5% WARN / 20% ERROR | [PLATFORM-INTERNAL \| STRONG] |
| INT-005 | `src/autom8_asana/query/engine.py:76` (`execute_rows`); L140-160 (filter expression composition); QueryEngine dataclass at L60-74 | Internal anchor for the Path B and C5 dispatch site | [PLATFORM-INTERNAL \| STRONG] |
| INT-006 | `.sos/wip/frames/project-asana-pipeline-extraction.md:10-35` (telos block) and `.sos/wip/frames/project-asana-pipeline-extraction.shape.md:26-35` (throughline + success criteria) | Telos echo evidence — verbatim quote in §1 | [PLATFORM-INTERNAL \| STRONG] |
| INT-007 | `.sos/wip/inquisitions/cascade-vs-join-spike-orchestration.md:25-31` (S1-S5 station table; S5 verdict authority); §5.2 verdict envelope schema | Verdict-authority pin and handoff-envelope contract that this artifact feeds into | [PLATFORM-INTERNAL \| STRONG] |

### §6.1 Self-attestation grade

Per `self-ref-evidence-grade-rule`: this scout artifact carries a MODERATE ceiling on its own claims. STRONG appears only for external citations (SRC-NNN with peer-reviewed or production-documented basis) or for platform-internal references verified at file:line. The verdict-authority structural pin at S5 means this artifact's recommendation framing in §5 ("S5 should treat C5 as the dark-horse candidate") is option-surface input, not a verdict statement.

### §6.2 Anti-pattern guard self-check

- **Theater detection.** §2 matrix surfaces specific decision-relevant differentials per candidate; §5 highest-differential dimension is named (code-change footprint, dimension 2). No "all options have merit, you decide" formulation appears.
- **Pre-decision bias.** Cascade-vs-join is treated as the baseline binary; six third options are evaluated against it. C5 emerges as the highest-leverage third option, and the framing explicitly notes that the original binary occluded it.
- **Self-ref MODERATE ceiling.** STRONG claims (e.g., "Polars LazyFrame's predicate-pushdown semantics") cite external SRC-NNN. Internal claims about autom8y-asana state cite INT-NNN with file:line. No internal self-attestation appears at STRONG.

### §6.3 Time-box note

This artifact was authored within the ~3-hour focused budget. Search rigor in §4 is bounded by the budget; an extended scan (4-6h) would investigate (a) Apache DataFusion as a Polars-adjacent SQL engine and (b) Trino/Presto pushdown patterns as a long-horizon scaling reference. Neither is expected to materially change the live option set (C1, C2, C5, C6, C7) for Phase 2's horizon. The time-box is honored without breach.

---

*Authored by technology-scout (Station S1) under `project-asana-pipeline-extraction` Phase 0 spike, session-20260427-232025-634f0913. MODERATE grade on self-attestations. Verdict authority pinned at S5 per inquisition §1. Phase 2 non-foreclosure invariant respected — no design lock proposed.*
