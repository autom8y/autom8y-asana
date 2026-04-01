---
domain: feat/business-domain-model
generated_at: "2026-04-01T15:30:00Z"
expires_after: "14d"
source_scope:
  - "./src/autom8_asana/models/business/**/*.py"
  - "./.know/architecture.md"
generator: theoros
source_hash: "c213958"
confidence: 0.87
format_version: "1.0"
---

# Business Domain Entity Model

## Purpose and Design Rationale

The Business Domain Entity Model maps real-world business client data stored in Asana tasks into a typed Python object hierarchy. It transforms Asana's project/task/subtask tree into domain-meaningful entities with bidirectional navigation, typed custom field access, and full upward/downward hydration.

### Entity Hierarchy

```
Business (root)
  +-- ContactHolder -> Contact (0..N)
  +-- UnitHolder -> Unit (0..N)
  |     +-- OfferHolder -> Offer (0..N)
  |     +-- ProcessHolder -> Process (0..N)
  +-- LocationHolder -> Location, Hours
  +-- DNAHolder, ReconciliationHolder, AssetEditHolder, VideographyHolder
```

### Five Structural Concepts

1. **Entity types**: Business, Unit, Contact, Offer, Process, Location, Hours, AssetEdit, DNA, Reconciliation, Videography
2. **Holder types**: 9 holder classes generated via `HolderFactory.__init_subclass__`
3. **Custom field descriptors**: 9 typed descriptors (TextField, EnumField, NumberField, PhoneTextField, etc.)
4. **Cascading fields**: `CascadingFieldDef` for downward field propagation
5. **Navigation descriptors**: `ParentRef[T]` and `HolderRef[T]` for upward navigation

## Conceptual Model

### Hydration

`hydrate_from_gid_async(client, gid)`: Fetches entry task, detects type, routes to downward-only (if Business) or upward traversal + downward hydration. Max traversal depth: 10.

### Bootstrap

`_bootstrap.py:register_all_models()` -- explicit startup registration with `ProjectTypeRegistry`. Per TDD-registry-consolidation: replaces `__init_subclass__` auto-registration. Called from `entrypoint.py` and `api/lifespan.py` step 1.

### ProcessType

Process entities have no static `PRIMARY_PROJECT_GID`. They belong to dynamic pipeline projects discovered via `WorkspaceProjectRegistry`. 10 process types: SALES, OUTREACH, ONBOARDING, IMPLEMENTATION, RETENTION, REACTIVATION, MONTH1, ACCOUNT_ERROR, EXPANSION, UNKNOWN.

## Implementation Map

60+ files: base.py (HolderMixin, BusinessEntity), business.py (Business + 4 stub holders), holder_factory.py, descriptors.py (ParentRef, HolderRef, 9 CustomFieldDescriptor subclasses), hydration.py, _bootstrap.py, registry.py (ProjectTypeRegistry, WorkspaceProjectRegistry), unit.py, contact.py, offer.py, process.py, mixins.py, fields.py (CascadingFieldDef), activity.py (SectionClassifier), plus location.py, hours.py, dna.py, reconciliation.py, asset_edit.py, videography.py, sections.py, patterns.py, seeder.py, section_timeline.py.

## Boundaries and Failure Modes

### Critical Constraints

- Every holder class requires `PRIMARY_PROJECT_GID` to prevent entity collision (SCAR-001)
- Phone fields must use `PhoneTextField` not `TextField` (SCAR-024)
- Registration only in `_bootstrap.py`, never in `__init_subclass__` (TDD-registry-consolidation)
- Descriptors declared WITHOUT type annotations (ADR-0077, Pydantic constraint)
- `allow_override=False` default in CascadingFieldDef -- parent always wins
- `Process.PRIMARY_PROJECT_GID=None` is intentional (WorkspaceProjectRegistry)
- `extra="allow"` on BusinessEntity is load-bearing for descriptor `__set__`

## Knowledge Gaps

1. Secondary entity files (dna, reconciliation, videography, location, hours) field inventories not read.
2. `AssetEdit` relationship to Process not confirmed.
3. `seeder.py`, `patterns.py` purpose not read.
4. CONSULTATION process type missing from ProcessType enum.
