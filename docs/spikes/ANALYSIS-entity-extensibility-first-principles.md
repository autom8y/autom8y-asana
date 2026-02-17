# First-Principles Analysis: Entity Extensibility Architecture

**Date:** 2026-02-17
**Status:** Complete
**Predecessor:** [SPIKE-entity-extensibility-architecture](./SPIKE-entity-extensibility-architecture.md), [SPIKE-offer-query-canary-bugs](./SPIKE-offer-query-canary-bugs.md)
**Purpose:** Challenge the proposed auto-wiring architecture by examining what this specific system actually needs given its constraints and trajectory

---

## 1. System Characteristics That Constrain the Design

### 1.1 Entity Count and Growth Rate

**Today: 18 entity descriptors in `ENTITY_DESCRIPTORS`.**

| Category | Count | Entities |
|----------|-------|----------|
| Root | 1 | Business |
| Composite | 1 | Unit |
| Leaf | 6 | Contact, Offer, AssetEdit, Process, Location, Hours |
| Holder | 10 | ContactHolder, UnitHolder, LocationHolder, DNAHolder, ReconciliationHolder, AssetEditHolder, VideographyHolder, OfferHolder, ProcessHolder (+ implicitly LocationHolder) |

**Growth projection: Near-zero.** These entities mirror Asana project types in a specific company's workspace. The domain is a CRM/operations system built on top of Asana. New entity types appear when the company creates a fundamentally new kind of tracked work in Asana. Based on the commit history and the maturity of the domain model (18 descriptors with detailed hierarchy, cascading fields, and section classifiers), this system is in a maintenance-and-refinement phase, not a rapid-entity-addition phase.

Realistic 2-year forecast: 0-2 new entity types. Perhaps a "Campaign" or "Report" type. The holders grow only when new leaf entities need nesting, which is proportional to leaf growth.

### 1.2 Entities with Full DataFrame Support vs Model-Only

**7 schemas registered** in SchemaRegistry: Unit, Contact, Offer, Business, AssetEdit, AssetEditHolder, plus the wildcard `*` (BASE_SCHEMA).

**3 extractors exist**: UnitExtractor, ContactExtractor, DefaultExtractor. That is it.

**3 Row models exist**: TaskRow (base), UnitRow, ContactRow. No OfferRow, BusinessRow, AssetEditRow, or AssetEditHolderRow.

| Entity | Schema | Extractor | Row Model | Full Stack? |
|--------|--------|-----------|-----------|-------------|
| Unit | UNIT_SCHEMA | UnitExtractor | UnitRow | Yes |
| Contact | CONTACT_SCHEMA | ContactExtractor | ContactRow | Yes |
| Offer | OFFER_SCHEMA | DefaultExtractor (crash) | TaskRow (crash) | NO |
| Business | BUSINESS_SCHEMA | DefaultExtractor (crash) | TaskRow (crash) | NO |
| AssetEdit | ASSET_EDIT_SCHEMA | DefaultExtractor (crash) | TaskRow (crash) | NO |
| AssetEditHolder | ASSET_EDIT_HOLDER_SCHEMA | DefaultExtractor (crash) | TaskRow (crash) | NO |

**The ratio: 2 out of 7 schema-bearing entities have a complete extraction stack.** The other 5 will crash on `to_dataframe()` because `TaskRow` uses `extra="forbid"` and the schemas define columns beyond the 12 base fields.

This is the central observation. The problem is not "we keep adding entities and forgetting to wire them." The problem is "we added schemas for 5 entities and never built the extraction layer for any of them."

### 1.3 How Different Are Extractors From Each Other?

Comparing UnitExtractor (the most complex) vs ContactExtractor vs DefaultExtractor:

**What UnitExtractor does beyond BaseExtractor:**
1. `_create_row()` -- Sets `type = "Unit"`, converts None lists to `[]`, calls `UnitRow.model_validate(data)`
2. `_extract_office()` -- Sync stub returning None
3. `_extract_office_async()` -- 60-line parent chain traversal to find Business ancestor name
4. `_extract_vertical_id()` -- Stub returning None
5. `_extract_max_pipeline_stage()` -- Stub returning None
6. `_extract_type()` -- Returns `"Unit"` always

**What ContactExtractor does beyond BaseExtractor:**
1. `_create_row()` -- Sets `type = "Contact"`, converts None lists to `[]`, calls `ContactRow.model_validate(data)`
2. `_extract_type()` -- Returns `"Contact"` always

**What DefaultExtractor does beyond BaseExtractor:**
1. `_create_row()` -- Converts None lists to `[]`, calls `TaskRow.model_validate(data)`

**The pattern:** The `_create_row()` method is the only mandatory override, and it is boilerplate: set the type, handle None lists, call `model_validate`. The only non-trivial extractor logic is UnitExtractor's `_extract_office_async()` parent chain traversal. ContactExtractor is pure boilerplate. An OfferExtractor would be nearly identical to ContactExtractor (boilerplate `_create_row` + type override), because Offer's fields are all `cf:` or `cascade:` sources that BaseExtractor already handles via the resolver and cascading resolver.

**Critical insight: The extraction logic is almost entirely generic.** The schema already declares the source annotations (`cf:`, `cascade:`, `gid:`, direct attribute, `None` for derived). `BaseExtractor.extract()` and `extract_async()` already dispatch on these prefixes. The only reason type-specific extractors exist is:
1. To call `TypeRow.model_validate()` instead of `TaskRow.model_validate()`
2. To implement derived field methods (source=None columns that need custom logic)

Most derived fields are stubs returning None. The only real logic is `_extract_office_async`, which is shared across Unit, Offer, Contact, and AssetEdit (all need the Business ancestor's name).

---

## 2. The Real Problem Decomposition

### 2.1 Is the Problem Extensibility or Integrity?

**The problem is integrity, not extensibility.**

The system does not need to be extended frequently. The evidence:
- 18 entity types exist; maybe 1-2 more in 2 years
- Schemas were added without corresponding extractors and row models -- this is a completeness gap, not a scalability gap
- The `_create_extractor()` match statement has 2 cases + default. This is not a 50-case match statement crying for a plugin system

The spike document frames the problem as "shotgun surgery across 5 disconnected subsystems." But shotgun surgery is painful in proportion to frequency. With near-zero new entity additions per year, the cost of touching 10 files once every 6-12 months is negligible.

What actually hurts is the **silent failure mode**: you can register a schema and believe you have DataFrame support, but the extraction path crashes at runtime because no one enforced that the schema-extractor-row triad is complete.

### 2.2 Reframing: What Guard Would Have Prevented the Offer Crash?

A single test:

```python
def test_schema_extractor_row_triad_completeness():
    """Every schema in SchemaRegistry must have a matching extractor and row model."""
    from autom8_asana.dataframes.models.registry import SchemaRegistry
    from autom8_asana.dataframes.builders.base import DataFrameBuilder

    registry = SchemaRegistry.get_instance()

    for task_type in registry.list_task_types():
        schema = registry.get_schema(task_type)

        # Build a minimal fake task with all schema columns as None
        # and verify that _create_extractor doesn't fall through to
        # DefaultExtractor when a type-specific schema exists
        builder = DataFrameBuilder(schema=schema, task_type=task_type)
        extractor = builder._create_extractor(task_type)

        # If schema has columns beyond BASE, extractor must not be DefaultExtractor
        base_columns = {"gid", "name", "type", "date", "created", "due_on",
                       "is_completed", "completed_at", "url", "last_modified",
                       "section", "tags"}
        schema_columns = set(schema.column_names())
        extra_columns = schema_columns - base_columns

        if extra_columns:
            assert type(extractor).__name__ != "DefaultExtractor", (
                f"{task_type} has {len(extra_columns)} extra columns "
                f"({', '.join(sorted(extra_columns))}) but falls through "
                f"to DefaultExtractor, which will crash on TaskRow(extra='forbid')"
            )
```

This test costs about 20 lines. It would have caught the Offer crash, the Business crash, the AssetEdit crash, and the AssetEditHolder crash. It requires zero architectural changes. It can be written and merged today.

### 2.3 What About the Auto-Wiring?

The spike proposes adding 3-4 new fields to EntityDescriptor (`schema_module_path`, `extractor_class_path`, `row_model_class_path`, `cascading_field_provider`), then rewiring SchemaRegistry, `_create_extractor()`, `hierarchy.py`, and `_build_cascading_field_registry()` to read from descriptors instead of hardcoded registrations.

This is architecturally clean. But it solves a problem that does not exist at the current scale: "how do I add entity types without touching multiple files." At 18 entities with near-zero growth rate, the answer is: you touch the files, and a test catches you if you miss one.

---

## 3. Schema-Driven Extraction: The Road Not Taken

### 3.1 Could the Extractor Be Generated from the Schema?

**Yes, for the vast majority of cases.**

Look at what `BaseExtractor._extract_column()` and `_extract_column_async()` already do:

| Source Annotation | Extraction Logic | Already Generic? |
|-------------------|-----------------|------------------|
| `source="gid"` | `getattr(task, "gid")` | Yes |
| `source="name"` | `getattr(task, "name")` | Yes |
| `source="completed"` | `bool(getattr(task, "completed"))` | Yes |
| `source="cf:MRR"` | `resolver.get_value(task, "cf:MRR")` | Yes |
| `source="gid:1234"` | `resolver.get_value(task, "gid:1234")` | Yes |
| `source="cascade:Office Phone"` | `cascading_resolver.resolve_async(task, "Office Phone")` | Yes |
| `source=None` | `self._extract_{name}(task)` | Delegates to subclass |

Every source type except `None` (derived) is already handled generically by `BaseExtractor`. The only reason subclasses exist is:
1. `_create_row()` must call the right Pydantic model
2. Derived fields (source=None) need custom logic

### 3.2 What If DefaultExtractor Could Handle Any Schema?

The crash happens because `TaskRow` has `extra="forbid"`. If we create a **generic row factory** that dynamically generates a Pydantic model matching the schema, DefaultExtractor could handle any entity type without a type-specific extractor:

```python
# Conceptual approach
def _create_row_model_for_schema(schema: DataFrameSchema) -> type[TaskRow]:
    """Dynamically create a Pydantic model matching the schema."""
    extra_fields = {}
    for col in schema.columns:
        if col.name not in TaskRow.model_fields:
            python_type = _dtype_to_python_type(col.dtype)
            if col.nullable:
                extra_fields[col.name] = (python_type | None, None)
            else:
                extra_fields[col.name] = (python_type, ...)

    if not extra_fields:
        return TaskRow

    return create_model(
        f"{schema.task_type}Row",
        __base__=TaskRow,
        **extra_fields,
    )
```

**This approach eliminates the need for OfferRow, BusinessRow, AssetEditRow, and AssetEditHolderRow entirely.** The schema already declares all column names and dtypes. Creating a Pydantic model from that metadata is a straightforward mapping.

**However**, there is a meaningful tradeoff: hand-coded row models provide IDE autocompletion, static type checking, and serve as documentation of the contract. Dynamically generated models sacrifice these. For a team that values `frozen=True` and `extra="forbid"` on their Pydantic models, this loss matters.

### 3.3 The Middle Path: GenericExtractor with Schema-Derived Row

Instead of full dynamic generation, a more practical approach:

1. Keep hand-coded Row models for entities with complex derived fields (Unit, Contact)
2. Add a `SchemaExtractor` that generates a permissive row model from the schema for entities that only have `cf:`, `cascade:`, and direct-attribute sources
3. The `_create_extractor()` factory first looks for a registered type-specific extractor, then falls back to SchemaExtractor

This means: OfferExtractor becomes unnecessary. BusinessExtractor, AssetEditExtractor, AssetEditHolderExtractor become unnecessary. You only write a custom extractor when you have derived fields that need custom logic.

**How many of the 7 schema entities need custom extraction logic?**

| Entity | Derived Fields (source=None) | Custom Logic Needed? |
|--------|------------------------------|---------------------|
| Unit | office, vertical_id, max_pipeline_stage | Yes (office_async parent traversal) |
| Contact | vertical_id | Maybe (stub returns None) |
| Offer | office, vertical_id, name (overridden) | Same as Unit (office_async) |
| Business | name (overridden from base) | Minimal |
| AssetEdit | None -- all fields are cf: or cascade: | No |
| AssetEditHolder | None -- only office_phone cascade | No |

**4 out of 7 entities need zero custom extraction logic.** Their schemas consist entirely of `cf:` and `cascade:` sources, which `BaseExtractor` already handles generically.

---

## 4. Minimum Viable Fix vs Architectural Investment

### 4.1 Absolute Minimum Change to Fix the Offer Crash

**Option MVF-1: Single-entity fix (2-3 hours)**
1. Create `OfferRow(TaskRow)` with 12 offer-specific fields in `task_row.py`
2. Create `OfferExtractor(BaseExtractor)` as boilerplate (identical structure to ContactExtractor)
3. Add `case "Offer":` to `_create_extractor()` match
4. Export OfferExtractor from `extractors/__init__.py`

This fixes the crash. It does not prevent the same class of bug from recurring.

**Option MVF-2: Fix + integrity test (3-4 hours)**
Everything in MVF-1, plus:
5. Add the schema-extractor-row triad test (see Section 2.2)
6. Fix or skip the Business, AssetEdit, AssetEditHolder crash paths (either create their Row+Extractor or add `# xfail: no extractor yet` to test)

This fixes the crash AND prevents recurrence.

**Option MVF-3: SchemaExtractor eliminates boilerplate (1-2 days)**
Everything in MVF-2, plus:
7. Create `SchemaExtractor(BaseExtractor)` that dynamically generates a row model from the schema at construction time
8. Change `_create_extractor()` default case to use `SchemaExtractor` instead of `DefaultExtractor`
9. This means OfferExtractor, BusinessExtractor, AssetEditExtractor, AssetEditHolderExtractor are all unnecessary -- `SchemaExtractor` handles them via the schema

### 4.2 ROI of Full Auto-Wiring Architecture

The extensibility spike proposes 5 phases of work to achieve full descriptor-driven auto-wiring. Let us estimate the cost and benefit.

**Cost estimate:**
- Phase 1 (Descriptor extension + Offer fix): 1-2 days
- Phase 2 (Auto-wire SchemaRegistry): 0.5 day
- Phase 3 (Auto-wire extractor factory): 0.5 day
- Phase 4 (Auto-wire query hierarchy): 0.5 day
- Phase 5 (Auto-wire cascading fields): 0.5 day
- Testing and migration validation: 1-2 days
- **Total: 4-6 days**

**Benefit at current scale:**
- Saves 10 minutes per new entity type (touching ~10 files vs 1)
- At 0-2 new entities over 2 years, total time saved: 0-20 minutes
- Provides validation that all pieces are wired (but a test does this too)

**Benefit at speculative future scale:**
- If entity count triples to 50+, the auto-wiring pays for itself
- But this system mirrors a specific company's Asana workspace -- 50 entity types is not realistic

**Verdict: The auto-wiring architecture has negative ROI at the current scale.** The 4-6 days of investment saves 0-20 minutes of future manual wiring. Its only real benefit -- integrity enforcement -- is achievable with a test.

### 4.3 Is the Shotgun Surgery Actually Painful?

At 18 entities with ~0 additions per year, no.

The spike correctly identifies 14 registration points for a fully-wired entity. But:
- Points 1-4 (descriptor, enum, schema, schema registration) are already done for Offer
- Points 9, 11, 12, 14 (hierarchy, classifier, model, cache) are also already done for Offer
- Only points 5-8, 10 (row model, extractor, factory, init, cascading fields) are missing
- These 5 points are all in the `dataframes/` package -- it is not cross-cutting shotgun surgery, it is one package that was not completed

**The "shotgun surgery" framing overstates the problem.** The registration points fall into two categories:
1. Domain model wiring (entity_registry, entity_types, Asana model, classifier, hierarchy) -- done once when the entity concept is introduced
2. DataFrame layer wiring (schema, row model, extractor, factory) -- done when DataFrame support is added for that entity

These are two separate concerns, and they should be done at two separate times. The fact that Offer has complete domain wiring but incomplete DataFrame wiring is normal -- it means DataFrame support was not prioritized. The bug is that SchemaRegistry accepted the OFFER_SCHEMA without an extractor to back it, and no test caught this.

---

## 5. Ranked Pain Points from Canary Bugs

### Rank 1: Missing OfferExtractor (crash) -- B1

**Impact: High. Severity: Bug.**

`to_dataframe(task_type="Offer")` crashes with a `ValidationError`. This is a functional failure that blocks any consumer requesting Offer DataFrames. The same crash affects Business, AssetEdit, and AssetEditHolder schemas.

**Fix: MVF-2 (fix + integrity test).** Create the missing OfferRow/OfferExtractor, add the triad completeness test. Consider MVF-3 (SchemaExtractor) if Business/AssetEdit/AssetEditHolder also need DataFrame support soon.

### Rank 2: cascade:MRR vs cf:MRR (correctness) -- B2

**Impact: High. Severity: Correctness.**

OFFER_SCHEMA declares `mrr` with `source="cascade:MRR"` and `dtype="Utf8"`. UNIT_SCHEMA declares it with `source="cf:MRR"` and `dtype="Decimal"`. Two problems:
1. If MRR is directly available on Offer tasks (as the spike observed), using `cascade:` forces unnecessary parent chain API calls and async-only extraction
2. The dtype mismatch (`Utf8` vs `Decimal`) means MRR values require string-to-number conversion for any aggregation query at the Offer level

This is a data correctness issue. Fix requires investigation: check whether MRR is a project-level custom field on the Business Offers project (available directly) or truly cascaded from the Unit parent. If direct, change `source` to `cf:MRR` and `dtype` to `Decimal`.

### Rank 3: MRR deduplication (data quality) -- B3

**Impact: Medium. Severity: Design gap.**

Multiple offers under the same Unit share the Unit's MRR, so naive summation at Offer level overcounts. This is a semantic issue, not a bug -- the data is correct (each Offer correctly reports its Unit's MRR), but naive aggregation produces wrong results.

Fix is documentation and query guidance, not code change. The correct MRR aggregation queries at Unit level with `group_by=["office_phone", "vertical"]`. The QueryEngine already supports this.

### Rank 4: Query infrastructure discoverability (usability) -- B4

**Impact: Low. Severity: Developer experience.**

The full query stack (QueryEngine, aggregation compiler, HTTP endpoints) exists but is not ergonomically accessible from scripts. Fix is a convenience wrapper. Nice-to-have, not blocking.

### Rank 5: Shotgun surgery (developer experience) -- F2

**Impact: Low at current scale. Severity: Code smell.**

At near-zero entity additions per year, the manual wiring cost is negligible. The auto-wiring architecture is a solution looking for a problem at this scale. If entity growth accelerates (unlikely given the domain), revisit.

---

## 6. Recommendation

### Do This Now (1-2 days)

**A. Fix the crash with SchemaExtractor (MVF-3).**

Instead of creating boilerplate OfferExtractor, BusinessExtractor, AssetEditExtractor, and AssetEditHolderExtractor classes that are all identical to ContactExtractor, create a single `SchemaExtractor(BaseExtractor)` that:

1. Accepts any `DataFrameSchema` at construction
2. Dynamically creates a Pydantic row model from the schema (using `pydantic.create_model()` with base=TaskRow)
3. Handles `_create_row()` generically
4. Falls through to `_extract_{name}()` methods on the instance for derived fields (source=None columns)

Then change `_create_extractor()`:
```python
match task_type:
    case "Unit":     return UnitExtractor(...)
    case "Contact":  return ContactExtractor(...)
    case _:          return SchemaExtractor(self._schema, self._resolver, client=self._client)
```

This fixes Offer, Business, AssetEdit, AssetEditHolder, and any future entity type simultaneously. No boilerplate per-entity extractors needed unless the entity has custom derived field logic.

**B. Add the triad completeness test.**

Write the test from Section 2.2 that iterates SchemaRegistry and verifies every registered schema can produce a DataFrame without crashing. This is the integrity guard that prevents B1 from recurring.

**C. Fix cascade:MRR vs cf:MRR.**

Investigate and correct the source annotation and dtype for MRR in OFFER_SCHEMA. This is a correctness fix independent of architecture.

### Do Not Do Now

**D. Do NOT build the descriptor-driven auto-wiring architecture.**

The ROI is negative at the current entity count and growth rate. The integrity benefit is achieved by the triad test. The "single source of truth" benefit is a readability improvement that does not justify 4-6 days of migration work and ongoing maintenance of dotted-path strings in EntityDescriptor.

If the entity count ever approaches 30+, or if the team finds itself adding entities more than twice a year, revisit the auto-wiring decision. Until then, the test is sufficient.

**E. Do NOT build a query CLI utility.**

This is a nice-to-have convenience for ad-hoc scripts. It is not blocking any production use case. The existing HTTP API and QueryEngine serve production needs.

### Summary Decision Matrix

| Action | Cost | Impact | Verdict |
|--------|------|--------|---------|
| SchemaExtractor (generic fallback) | 1 day | Fixes 5 broken schemas, eliminates future boilerplate | DO NOW |
| Triad completeness test | 2 hours | Prevents recurrence of B1-class bugs forever | DO NOW |
| Fix cascade:MRR annotation | 0.5 day | Correctness fix for Offer MRR queries | DO NOW |
| Descriptor-driven auto-wiring (5 phases) | 4-6 days | Eliminates manual wiring for ~0 new entities/year | DEFER |
| Per-entity extractors (OfferExtractor etc.) | 3-4 days | Boilerplate code that SchemaExtractor renders unnecessary | SKIP |
| Query CLI utility | 1 day | Developer convenience for ad-hoc scripts | DEFER |
| MRR aggregation best practice doc | 2 hours | Prevents naive summation errors | DO LATER |

---

## 7. The 18-Month Test

*"Will this design look obviously right in 18 months?"*

**SchemaExtractor + triad test:** Yes. A generic extractor that handles any schema is obviously right because the schema already contains all the information needed for extraction. The triad test is obviously right because it catches an entire class of wiring bugs with 20 lines of test code.

**Descriptor-driven auto-wiring (if built):** In 18 months, with still ~18 entity types and 0-1 additions, the team would look at 4-6 days of migration work and ask "what were they thinking?" The EntityDescriptor would have 25+ fields including 4 dotted-path strings that are only read at initialization time by 4 different subsystems, adding cognitive overhead to a dataclass that is already at 21 fields. The auto-wiring would work correctly but provide no observable benefit.

**The architecture this system actually needs is not extensibility machinery. It is extraction generality (SchemaExtractor) and integrity enforcement (the test).** These are small, targeted interventions that address the actual failure modes without building infrastructure for a growth trajectory that does not exist.
