# TDD Amendment: WS1-S4 Schema Generation Assessment

**Date:** 2026-02-17
**Author:** Architect Agent
**Status:** DECIDED
**Predecessor:** [ARCH-descriptor-driven-auto-wiring](./ARCH-descriptor-driven-auto-wiring.md)
**Scope:** WS1-S4 scope redefinition -- schema generation vs. validation hardening
**Decision:** Option A (SKIP schema generation)

---

## 1. Decision Context

### 1.1 What S1-S3 Delivered

Sprints 1-3 implemented the full scope of the ARCH descriptor-driven auto-wiring
document:

| Sprint | Deliverable | Verified |
|--------|-------------|----------|
| S1 | EntityDescriptor +4 fields, `_resolve_dotted_path()`, validation checks 6a-7 | 87 tests, QA PASS |
| S2 | `SchemaRegistry._ensure_initialized()` + `_create_extractor()` descriptor-driven | 13 tests, QA PASS |
| S3 | `ENTITY_RELATIONSHIPS` + `_build_cascading_field_registry()` descriptor-driven | 48 tests, QA PASS |

All 4 consumers are auto-wired. 10,550 tests pass, 0 failures. The QA Gate G2
report confirms behavioral equivalence, triad consistency, circular import safety,
contract preservation, validation integrity, cascade equivalence, and zero
regressions.

### 1.2 What S4 Was Originally Envisioned As

The original initiative plan flagged S4 as "HIGHEST RISK" because early user
interviews discussed schemas becoming "derived artifacts" -- meaning the hand-written
`OFFER_SCHEMA`, `BUSINESS_SCHEMA`, etc. would be eliminated entirely by generating
`ColumnDef` lists from metadata stored in `EntityDescriptor`.

### 1.3 The Question

Given the completed auto-wiring, does schema generation still provide enough
value to justify its cost?

---

## 2. Tradeoff Analysis

### 2.1 Option A: Skip Schema Generation

**What changes:** S4 is eliminated as a feature sprint. The hand-written schema
files (`schemas/offer.py`, `schemas/business.py`, etc.) remain as-is. S4 time
is either absorbed into S5 (legacy cleanup / merge prep) or used for validation
hardening.

**What already works:**
- `schema_module_path` on EntityDescriptor provides auto-discovery -- schemas are
  found via descriptor, not hardcoded imports in `_ensure_initialized()`
- `SchemaExtractor` handles entities without hand-coded extractors by dynamically
  generating Pydantic row models from schema `ColumnDef` lists
- Validation checks 6a-6f catch triad inconsistencies at import time
- The B1-class bug (schema registered without extractor) is structurally prevented

**What remains hand-written:**
- 7 schema files containing ~79 total `ColumnDef` entries
  - `base.py`: 12 columns (universal, never changes)
  - `unit.py`: 11 extra columns
  - `offer.py`: 12 extra columns
  - `business.py`: 5 extra columns (after dedup)
  - `contact.py`: 0 extra columns (BASE_COLUMNS only)
  - `asset_edit.py`: 21 extra columns
  - `asset_edit_holder.py`: 1 extra column

**Risk:** LOW. Schemas are stable, validated at import time, and already
auto-discovered.

### 2.2 Option B: Generate Schemas from Descriptor Metadata

**What changes:** EntityDescriptor gains per-entity column definitions. Each
entity with a `schema_module_path` would instead have an inline column
specification. Schema files become generated artifacts (or are eliminated).

**New descriptor fields required (per entity):**

```python
@dataclass(frozen=True, slots=True)
class EntityDescriptor:
    # ... existing 25 fields ...

    # --- Column Definitions (NEW for Option B) ---
    column_defs: tuple[ColumnDefSpec, ...] = ()
    schema_version: str = "1.0.0"
```

Where `ColumnDefSpec` is a lightweight frozen dataclass:

```python
@dataclass(frozen=True, slots=True)
class ColumnDefSpec:
    name: str
    dtype: str
    nullable: bool = True
    source: str | None = None
    description: str | None = None
```

**Estimated metadata additions:**
- `business`: 5 column specs
- `unit`: 11 column specs
- `offer`: 12 column specs
- `contact`: 0 column specs (BASE_COLUMNS only)
- `asset_edit`: 21 column specs
- `asset_edit_holder`: 1 column spec
- **Total:** ~50 column spec entries across 6 entities

**Impact on EntityDescriptor:**
- Field count grows from 25 to 27 (column_defs + schema_version)
- ARCH doc section 7.1 warned about the 25-field complexity threshold
- The `entity_registry.py` file grows by ~250 lines of column metadata
- The column metadata is highly repetitive (name/dtype/source/description
  for each column) and is harder to scan than the current schema files

**Impact on schema files:**
- 7 schema files become either:
  - (a) Generated at import time from descriptor metadata, or
  - (b) Eliminated entirely (schemas created inline in SchemaRegistry)
- Either approach requires `DataFrameSchema` construction logic to move
  from declarative module-level constants to runtime generation

**Risk:** HIGH.

1. **Complexity tax.** The 50 column specs in `entity_registry.py` would
   make the file significantly harder to read. Schema files are currently
   self-documenting modules with clear names and focused scope. Moving
   that metadata into a 900-line registry file trades readability for
   centralization.

2. **Extractor coupling.** ColumnDef `source` values drive extraction
   behavior (`cf:` for custom fields, `cascade:` for parent traversal,
   `None` for derived). These are DataFrame-layer concerns. Embedding
   them in `core/entity_registry.py` crosses the package boundary that
   the deferred-import architecture was designed to preserve.

3. **Custom extractors.** ColumnDef supports a `extractor: Callable`
   field for custom extraction functions. This cannot be represented as
   a dotted path string in a frozen descriptor without also adding
   callable resolution logic. The current schema files can reference
   inline lambdas or module-level functions naturally.

4. **Version coordination.** Schema versions (`version: "1.3.0"`)
   control cache invalidation. Moving version metadata to descriptors
   creates a coupling between entity lifecycle (descriptor changes) and
   cache lifecycle (schema version bumps). Today these are independent
   concerns.

5. **Migration scope.** All 50 column definitions must be migrated
   atomically (cannot have half the schemas generated and half
   hand-written without introducing two code paths). This violates the
   ARCH doc's Phase-by-Phase independence guarantee.

---

## 3. Assessment: Value-to-Risk Ratio

### 3.1 Value Delivered by Each Option

| Value Dimension | Status Quo (pre-S1) | Option A (S1-S3 done) | Option B (S4 gen) |
|----------------|--------------------|-----------------------|-------------------|
| Auto-discovery of schemas | Manual (7 hardcoded imports) | Automatic (descriptor-driven) | Automatic (inline) |
| B1 prevention | None | Import-time validation | Import-time validation |
| Adding new entity schema | Edit 4 files | Edit 2 files (schema + descriptor) | Edit 1 file (descriptor) |
| Schema readability | HIGH (dedicated files) | HIGH (dedicated files) | LOW (embedded in 900-line registry) |
| Schema stability validation | None | check 6a-6c at import | N/A (no separate files) |
| Column-level documentation | Inline in schema file | Inline in schema file | Inline in descriptor |

The marginal value of Option B over Option A is: when adding a new entity schema,
you edit 1 file instead of 2. Given that new entity types arrive approximately
2-3 times per year, this saves ~3 file edits per year. The cost is a permanent
reduction in readability and a one-time migration risk.

### 3.2 Schema Change Frequency

Git history confirms 19 commits touching `src/autom8_asana/dataframes/schemas/`
since August 2025. However, the majority are:
- Initial creation of schema files (one-time)
- Bug fixes (dtype corrections, dedup fixes)
- Version bumps for cache invalidation
- The S0 quick wins from this initiative

Structural changes to column definitions (adding/removing/renaming columns)
occurred approximately 2 times in the last 6 months. This is consistent with the
Asana domain model being driven by Asana custom fields, which change infrequently.

### 3.3 The "2 files vs 1 file" Argument

The argument for Option B reduces to: "when adding entity X, editing
`entity_registry.py` AND `schemas/x.py` is worse than editing only
`entity_registry.py`."

This argument is weakened by three observations:

1. **Validation check 6d already catches the gap.** If a developer adds
   a descriptor with `schema_module_path` but forgets to create the
   schema file, validation check 6a fails at import time with a clear
   error. The "forgot to edit the second file" failure mode is already
   prevented.

2. **Schema files are copy-paste-modify.** Every schema file follows the
   same 20-line template: import BASE_COLUMNS, define entity-specific
   columns, compose with dedup, instantiate DataFrameSchema. A developer
   adding a new entity copies an existing schema file and changes the
   column list. This takes approximately 5 minutes.

3. **Separation of concerns.** `entity_registry.py` describes entity
   identity, hierarchy, cache behavior, and discovery metadata.
   Schema files describe DataFrame column definitions, dtypes, and
   extraction sources. These are different concerns owned by different
   subsystems.

---

## 4. Decision

**Option A: Skip schema generation. S4 is eliminated as a feature sprint.**

### 4.1 Rationale

1. **The high-value deliverable is complete.** The ARCH doc's stated goal
   was "EntityDescriptor as single source of truth for DataFrame layer
   auto-wiring." All 4 consumers (SchemaRegistry, extractor factory,
   ENTITY_RELATIONSHIPS, cascading field registry) are now auto-wired.
   The B1-class bug is structurally prevented. The module docstring's
   promise ("Adding a new entity type means adding one entry here") is
   now true for wiring; schema content is a separate, lower-stakes
   concern.

2. **Schema generation crosses the complexity/value threshold.** Adding
   ~50 column specs to EntityDescriptor delivers marginal value (save
   editing 1 file, ~3 times per year) at significant cost (readability
   degradation, package boundary violation, migration risk, custom
   extractor callable limitation).

3. **The ARCH doc itself anticipated this.** Section 7.1 ("The descriptor
   becomes a god object") acknowledged the 25-field threshold. Going to
   27 fields plus 50 inline column specs would push EntityDescriptor
   firmly into god-object territory.

4. **Reversibility.** Option A is fully reversible. If column-level
   generation becomes valuable in the future (e.g., Asana custom field
   metadata API becomes available as a source-of-truth for column defs),
   the descriptor infrastructure is already in place to support it. No
   doors are closed.

### 4.2 ADR: Schema Generation Deferred

| Field | Value |
|-------|-------|
| **ID** | ADR-S4-001 |
| **Title** | Defer schema generation from EntityDescriptor |
| **Status** | Accepted |
| **Context** | S1-S3 delivered descriptor-driven auto-wiring for all 4 DataFrame consumers. S4 was originally envisioned as schema generation (deriving ColumnDef lists from descriptor metadata). Reassessment shows the auto-discovery via `schema_module_path` captures the high-value portion. Full schema generation adds ~50 column specs to descriptors for marginal benefit. |
| **Decision** | Keep schemas as hand-written, auto-discovered files. Do not add column metadata to EntityDescriptor. |
| **Consequences** | Adding a new entity schema requires editing 2 files (descriptor + schema file) instead of 1. This is mitigated by import-time validation that catches mismatches. EntityDescriptor stays at 25 fields. Schema files remain readable, self-documenting modules. The option to add schema generation later remains open. |
| **Alternatives Rejected** | Option B (inline column specs in descriptor): Higher complexity, god-object risk, package boundary violation, custom extractor callable limitation. |

---

## 5. What "S4" Becomes

With schema generation eliminated, the S4 time allocation is redistributed.
Two options, both low-risk:

### 5.1 Option S4a: Validation Hardening (Recommended)

Use S4 time to tighten the validation safety net:

1. **Promote check 6d to configurable severity.** Add a
   `strict_triad_validation: bool = False` flag to EntityRegistry. When
   flipped to `True` (after all existing schemas have matching extractors),
   check 6d ("schema without extractor") becomes an ERROR instead of a
   WARNING. This is the "future tightening" mentioned in ARCH doc section
   4.3.

2. **Add import-resolution test coverage.** The current validation checks
   6a-6c only verify path syntax at import time (to avoid circular imports).
   Add a dedicated test that calls `_resolve_dotted_path()` for every
   populated path in every descriptor, ensuring actual import resolution
   succeeds. (This test may already exist as `TestDataFramePathResolution`
   per the QA report -- verify and extend if needed.)

3. **Add schema-column-count smoke test.** For each entity with a schema,
   verify that the schema's column count matches expectations. This catches
   accidental column removal or duplication without requiring full
   integration tests.

**Estimated effort:** 0.5 sprints (half a sprint). Can be combined with
S5 merge prep.

### 5.2 Option S4b: Absorb into S5

Skip S4 entirely. Proceed directly to S5 (legacy cleanup + merge prep for
`feature/ssot-convergence` into `main`). The validation improvements from
S4a become part of S5's cleanup scope.

**Recommended:** S4a. The validation hardening is low-effort, low-risk, and
provides concrete defensive value for the merge.

---

## 6. Impact on Remaining Sprints

### 6.1 Revised Sprint Plan

| Sprint | Scope | Status |
|--------|-------|--------|
| S0 | Quick wins (BUSINESS_SCHEMA task_type fix, Offer dtype fixes) | COMPLETE |
| S1 | EntityDescriptor +4 fields, `_resolve_dotted_path()`, validation 6a-7 | COMPLETE |
| S2 | SchemaRegistry + extractor factory auto-wired | COMPLETE |
| S3 | ENTITY_RELATIONSHIPS + cascading field registry auto-wired | COMPLETE |
| ~~S4~~ | ~~Schema generation~~ | **ELIMINATED** |
| S4 (revised) | Validation hardening (optional, combinable with S5) | READY |
| S5 | Legacy cleanup, dead code removal, merge prep | READY |

### 6.2 Timeline Impact

Eliminating schema generation removes the HIGHEST RISK sprint from the plan.
The remaining work (S4-revised + S5) is low-risk mechanical cleanup. Estimated
total remaining effort: 1-1.5 sprints.

### 6.3 ARCH Doc Completeness

The ARCH doc (`ARCH-descriptor-driven-auto-wiring.md`) defined 6 phases:

| Phase | ARCH Section | Status |
|-------|-------------|--------|
| Phase 1: Foundation | 5.1 | COMPLETE (S1) |
| Phase 2: Fix B1 | 5.1 | N/A (SchemaExtractor handles this generically) |
| Phase 3: Auto-Wire SchemaRegistry | 3.2 / 5.1 | COMPLETE (S2) |
| Phase 4: Auto-Wire _create_extractor() | 3.3 / 5.1 | COMPLETE (S2) |
| Phase 5: Auto-Wire ENTITY_RELATIONSHIPS | 3.4 / 5.1 | COMPLETE (S3) |
| Phase 6: Auto-Wire _build_cascading_field_registry() | 3.5 / 5.1 | COMPLETE (S3) |

All 6 ARCH-defined phases are complete. The "schema generation" concept was
discussed in user interviews but was never specified as a phase in the ARCH doc.
This amendment formalizes the decision not to pursue it.

---

## 7. Risk Assessment

### 7.1 Risk of Proceeding with Option A

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| New entity added without schema file | LOW | LOW | Check 6a catches at import time |
| Schema file drifts from descriptor | LOW | LOW | Schema is auto-discovered via descriptor; no manual sync needed beyond the path |
| Developer confusion about where to edit | LOW | MEDIUM | Document the 2-file pattern in entity_registry.py docstring |
| Schema generation needed later | LOW | LOW | Descriptor infrastructure supports adding it; no doors closed |

### 7.2 Risk Avoided by Skipping Option B

| Risk | Severity | Likelihood | Note |
|------|----------|------------|------|
| EntityDescriptor god-object | MEDIUM | HIGH | 27 fields + 50 column specs |
| core/ to dataframes/ package boundary violation | MEDIUM | HIGH | Column sources (cf:, cascade:) are DataFrame-layer concerns |
| Atomic migration of 50 column defs | MEDIUM | MEDIUM | Cannot partial-migrate |
| Custom extractor callable limitation | LOW | MEDIUM | ColumnDef.extractor cannot be a dotted path |
| Readability degradation of entity_registry.py | MEDIUM | HIGH | File grows from ~820 to ~1100 lines |

---

## 8. Verification Checklist

- [x] ARCH doc all 6 phases complete
- [x] QA Gate G2 passed (10,550 tests, 0 failures)
- [x] All 4 consumers auto-wired from descriptors
- [x] B1-class bug structurally prevented (validation checks 6a-6f)
- [x] Option A vs B tradeoff analysis documented
- [x] ADR recorded (ADR-S4-001)
- [x] Sprint plan updated
- [x] Risk assessment for chosen option
- [x] No implementation changes required (design-only amendment)
