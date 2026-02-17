# SPIKE: Deferred TODO Item Triage

**Date**: 2026-02-17
**Source**: `.claude/wip/TODO.md` (from TDD-ENTITY-EXT-001 Task 8)
**Status**: Complete

---

## Question

What is the current state, blast radius, and recommended priority for each of the
5 deferred work items from the entity extensibility sprint?

## Items Investigated

1. cascade:MRR source annotation
2. Traversal unification initiative
3. MRR dedup documentation
4. SM-003 business task_type naming normalization
5. Query CLI utility

---

## 1. cascade:MRR Source Annotation

### Current State

| Schema | Source | dtype | Resolution |
|--------|--------|-------|------------|
| UNIT_SCHEMA | `cf:MRR` | Decimal (Float64) | Direct custom field lookup |
| OFFER_SCHEMA | `cascade:MRR` | Utf8 (String) | Async parent-chain traversal to Unit |

**How cascade works**: `BaseExtractor._extract_column_async()` detects `cascade:` prefix,
calls `CascadingFieldResolver.resolve_async(task, "MRR")`, which walks the parent chain
to find the owning Unit and extracts its MRR custom field value.

**How cf: works**: `DefaultCustomFieldResolver.get_value()` looks up the custom field by
normalized name in the task's `custom_fields` list, then `TypeCoercer.coerce()` converts
to the target dtype.

### Key Finding

The `cascade:MRR` annotation is **semantically correct** -- MRR is defined at the Unit
level and propagates downward to Offers via `CascadingFieldDef(name="MRR",
target_types={"Offer"}, allow_override=False)`.

However, the **dtype mismatch is a real bug**:
- Unit MRR resolves to `Decimal` (native numeric)
- Offer MRR resolves to `Utf8` (string representation of the same number)
- Aggregation requires explicit `cast_dtype=pl.Float64` in MetricExpr to work correctly

### Other cascade: sources for reference

- `cascade:Office Phone` -- Unit, Offer, Contact, AssetEdit, AssetEditHolder (owner: Business)
- `cascade:Vertical` -- Offer, Contact (owner: Unit)
- `cascade:MRR` -- Offer (owner: Unit)
- `cascade:Weekly Ad Spend` -- Offer (owner: Unit)

### Recommendation

**Fix: Change OFFER_SCHEMA mrr dtype from Utf8 to Decimal.**

- Source stays `cascade:MRR` (correct semantics)
- dtype changes to `Decimal` to match Unit and enable native numeric aggregation
- Eliminates need for `cast_dtype=pl.Float64` workaround in MetricExpr
- Blast radius: 1 file (`schemas/offer.py`), plus any tests that assert Utf8 type
- Risk: Low -- TypeCoercer already handles Decimal coercion

**Effort**: S (< 1 hour)
**Priority**: P2 (data correctness, but mitigated by cast workaround)

---

## 2. Traversal Unification Initiative

### Current State: Three Parallel Traversal Systems

#### System A: UpwardTraversalMixin (Model Layer)
- **Location**: `models/business/mixins.py` + `models/business/hydration.py`
- **Purpose**: Full entity hydration with cached references
- **Used by**: Contact, Unit, Offer, Process via `to_business_async()`
- **Pattern**: `_traverse_upward_async()` returns `(Business, path)`

#### System B: CascadingFieldResolver (DataFrame Extraction Layer)
- **Location**: `dataframes/resolver/cascading.py`
- **Purpose**: Lightweight field-value resolution during extraction
- **Used by**: BaseExtractor for `cascade:` sources
- **Pattern**: `_traverse_parent_chain()` with cycle/depth guards

#### System C: CascadeViewPlugin (Unified Cache Integration)
- **Location**: `dataframes/views/cascade_view.py`
- **Purpose**: Cache-backed field resolution via UnifiedTaskStore
- **Used by**: BaseExtractor when unified_store is available
- **Pattern**: `store.get_parent_chain_async()` replaces per-instance API calls

#### Additional: UnitExtractor._extract_office_async()
- **Location**: `dataframes/extractors/unit.py:89-199`
- **Purpose**: Manual traversal to find Business ancestor name
- **Pattern**: Bespoke while-loop duplicating System B logic

### Key Finding

Systems A, B, and C serve **different purposes** and operate at **different abstraction
levels**. Unifying them into a single traversal mechanism would conflate model hydration
(full object graph) with field extraction (single value lookup).

However, there IS legitimate duplication:
- `UnitExtractor._extract_office_async()` duplicates `CascadingFieldResolver` logic
- Systems B and C have overlapping `_traverse_parent_chain()` implementations
- All three use `detect_entity_type()` + `max_depth` + `visited` cycle detection

### Entity Traversal Needs Audit

| Entity | Derived Fields | Current Mechanism | Needs Dedicated Extractor? |
|--------|---------------|-------------------|---------------------------|
| Unit | office (Business.name) | UnitExtractor._extract_office_async() | Already has one |
| Offer | office_phone, vertical, mrr, weekly_ad_spend | cascade: via BaseExtractor | No (cascade handles it) |
| Contact | office_phone, vertical | cascade: via BaseExtractor | No |
| Business | (none derived) | SchemaExtractor | No |
| AssetEdit | office_phone | cascade: via BaseExtractor | No |
| AssetEditHolder | office_phone | cascade: via BaseExtractor | No |

### Recommendation

**Do NOT unify Systems A/B/C** -- they serve different architectural layers.

**DO eliminate the duplication within the DataFrame layer:**
1. Remove `UnitExtractor._extract_office_async()` and replace with
   `cascade:Office Phone` source in UNIT_SCHEMA (already partially done -- Unit has
   `cascade:Office Phone` for office_phone, but `office` is a separate derived field)
2. Consolidate Systems B and C by making CascadeViewPlugin the primary path and
   CascadingFieldResolver the fallback

**Effort**: M (2-4 hours for B/C consolidation, needs tests)
**Priority**: P3 (tech debt, no user-facing impact)

---

## 3. MRR Dedup Documentation

### Current State

**Dedup is already implemented** in the metrics layer:

```python
# metrics/definitions/offer.py
ACTIVE_MRR = Metric(
    name="active_mrr",
    expr=MetricExpr(column="mrr", cast_dtype=pl.Float64, agg="sum",
                    filter_expr=pl.col("mrr").is_not_null() & (pl.col("mrr") > 0)),
    scope=_ACTIVE_OFFER_SCOPE,  # dedup_keys=["office_phone", "vertical"]
)

# metrics/compute.py
if metric.scope.dedup_keys:
    df = df.unique(subset=dedup_keys, keep="first")
```

**Why dedup matters**: Multiple Offers under one Unit share the same MRR. Without dedup
by `(office_phone, vertical)` -- the PVP that uniquely identifies a Unit -- MRR sums
are inflated proportional to offer count per unit.

**Existing documentation**:
- `scripts/demo_query_layer.py` has aggregation examples but doesn't call out dedup
- `scripts/calc_metric.py` correctly deduplicates
- `docs/spikes/SPIKE-offer-query-canary-bugs.md` mentions the issue as B3

### Correct Aggregation Patterns

| Approach | Correct? | Notes |
|----------|----------|-------|
| `Metric("active_mrr")` via compute_metric() | Yes | Auto-dedup via scope |
| Unit-level DataFrame (1 row per unit) | Yes | Native dedup |
| `AggregateRequest(group_by=["office_phone","vertical"])` | Yes | Manual dedup |
| Raw `df["mrr"].sum()` on offer DataFrame | **NO** | Overcounts |

### Recommendation

**Add a docstring to ACTIVE_MRR explaining the dedup rationale**, and add a "Data
Correctness" section to `scripts/demo_query_layer.py` showing correct vs incorrect
aggregation.

**Effort**: XS (< 30 minutes)
**Priority**: P3 (knowledge preservation, low urgency)

---

## 4. SM-003: business task_type Naming Normalization

### Current State

| Schema | task_type | Convention |
|--------|-----------|-----------|
| UNIT_SCHEMA | `"Unit"` | PascalCase |
| CONTACT_SCHEMA | `"Contact"` | PascalCase |
| OFFER_SCHEMA | `"Offer"` | PascalCase |
| ASSET_EDIT_SCHEMA | `"AssetEdit"` | PascalCase |
| ASSET_EDIT_HOLDER_SCHEMA | `"AssetEditHolder"` | PascalCase |
| **BUSINESS_SCHEMA** | **`"business"`** | **lowercase (inconsistent)** |

### Key Finding: Blast Radius Is Much Smaller Than Expected

The original estimate was "100+ locations across 30+ files." After investigation:

- **Actual code change**: **1 line** in `schemas/business.py:56`
- **Why so small**: The mapping indirection in `dataframe_service.py` and `resolver.py`
  isolates the task_type value from downstream consumers
- `to_pascal_case("business")` returns `"Business"` -- the registry lookup already uses
  PascalCase keys, so changing task_type to `"Business"` aligns the value with its lookup
- No test changes expected (tests use SchemaRegistry which already normalizes)
- `FACTORY_TO_FRAME_TYPE` uses lowercase `"business"` per the external autom8_data
  service API contract -- this is a **different field** and unaffected

### Recommendation

**Fix: Change `task_type="business"` to `task_type="Business"` in BUSINESS_SCHEMA.**

This is a 1-line fix with no downstream breakage due to mapping indirection. The
original "blast radius 100+" estimate was based on string occurrence counting, not
actual code path analysis.

**Effort**: XS (< 15 minutes including test run)
**Priority**: P2 (convention violation, easy win)

---

## 5. Query CLI Utility

### Current State

**The infrastructure is complete and production-ready:**

- `QueryEngine` with `execute_rows()` and `execute_aggregate()`
- Full predicate compilation (10 operators, nested AND/OR/NOT)
- Aggregation with GROUP BY, HAVING, and Utf8-to-Float64 casting
- Cross-entity joins
- Guard rails (depth limits, result limits)
- Schema registry, entity resolution, cache integration

**Existing entry points:**
- `scripts/demo_query_layer.py` -- comprehensive demo with argparse
- `scripts/calc_metric.py` -- metric-driven aggregation
- `automation/polling/cli.py` -- example argparse CLI pattern
- No `[project.scripts]` entry points in pyproject.toml

**Gap**: No general-purpose `autom8-query` CLI. Users must write Python scripts or use
the demo scripts.

### What a CLI Would Look Like

```bash
# Row query
autom8-query rows offer --where '{"field":"section","op":"eq","value":"Active"}' --limit 10

# Aggregation
autom8-query agg offer --group-by section,vertical --agg 'mrr:sum,gid:count'

# Metric
autom8-query metric active_mrr --project <gid>
```

### Recommendation

**Defer. The existing scripts are sufficient for current usage patterns.**

The demo scripts already provide ad-hoc query capability. A proper CLI would need:
- Authentication (PAT handling)
- Project GID resolution
- Output formatting (table, CSV, JSON)
- Cache warm/cold behavior
- Error handling for network failures

This is feature work, not debt. It should be driven by actual user demand.

**Effort**: L (1-2 days for a polished CLI)
**Priority**: P4 (nice-to-have, no blocker)

---

## Priority Matrix

| # | Item | Effort | Priority | Risk | Recommendation |
|---|------|--------|----------|------|---------------|
| 4 | SM-003 task_type naming | XS | P2 | Very Low | Fix now (1 line) |
| 1 | cascade:MRR dtype | S | P2 | Low | Fix soon (dtype Utf8 -> Decimal) |
| 3 | MRR dedup docs | XS | P3 | None | Add docstrings when convenient |
| 2 | Traversal consolidation | M | P3 | Medium | Consolidate B/C, skip A |
| 5 | Query CLI | L | P4 | None | Defer until user demand |

### Suggested Execution Order

1. **SM-003** (XS, P2) -- 1-line fix, validates immediately
2. **cascade:MRR dtype** (S, P2) -- small schema change + test updates
3. **MRR dedup docs** (XS, P3) -- docstring additions
4. **Traversal consolidation** (M, P3) -- plan as separate sprint work item
5. **Query CLI** (L, P4) -- defer to backlog

---

## Follow-Up Actions

- [ ] SM-003: Change `task_type="business"` to `task_type="Business"` in `schemas/business.py`
- [ ] cascade:MRR: Change `dtype="Utf8"` to `dtype="Decimal"` in `schemas/offer.py`
- [ ] MRR dedup: Add docstring to `ACTIVE_MRR` metric definition
- [ ] Traversal: Create backlog item for B/C consolidation
- [ ] Query CLI: Backlog only -- await user demand
