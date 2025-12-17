# Reference: Entity Type Table

> Extracted from: DISCOVERY-HYDRATION-001.md (Section 1.1, 1.2)
> Date: 2025-12-17
> Related: PRD-HYDRATION.md, TDD-HYDRATION.md

---

## Entity Hierarchy

| Entity Type | Parent Type | Holder Type | Navigation Properties | Population Methods | Custom Fields |
|-------------|-------------|-------------|----------------------|-------------------|---------------|
| **Business** | (root) | - | `contact_holder`, `unit_holder`, `location_holder`, `dna_holder`, `reconciliations_holder`, `asset_edit_holder`, `videography_holder` | `_populate_holders()`, `_fetch_holders_async()` (stub) | 19 fields |
| **ContactHolder** | Business | HolderMixin[Contact] | `business`, `contacts`, `owner` | `_populate_children()` | - |
| **Contact** | ContactHolder | - | `business`, `contact_holder` | - | 19 fields |
| **UnitHolder** | Business | HolderMixin[Unit] | `business`, `units` | `_populate_children()` | - |
| **Unit** | UnitHolder | - | `business`, `unit_holder`, `offer_holder`, `process_holder`, `offers`, `processes` | `_populate_holders()`, `_fetch_holders_async()` (stub) | 31 fields |
| **OfferHolder** | Unit | HolderMixin[Offer] | `unit`, `business`, `offers`, `active_offers` | `_populate_children()` | - |
| **Offer** | OfferHolder | - | `unit`, `business`, `offer_holder` | - | 39 fields |
| **ProcessHolder** | Unit | HolderMixin[Process] | `unit`, `business`, `processes` | `_populate_children()` | - |
| **Process** | ProcessHolder | - | `unit`, `business`, `process_holder` | - | 9 fields |
| **LocationHolder** | Business | HolderMixin[Location] | `business`, `locations`, `hours`, `primary_location` | `_populate_children()` | - |
| **Location** | LocationHolder | - | `business`, `location_holder` | - | 8 fields |
| **Hours** | LocationHolder | - | `business`, `location_holder` | - | 9 fields |

**Stub Holders** (Business-level, typed as plain Task children):
- `DNAHolder`, `ReconciliationsHolder`, `AssetEditHolder`, `VideographyHolder`

---

## Hierarchy Depth Analysis

```
Business (Level 0)
  +-- ContactHolder (Level 1)
  |     +-- Contact (Level 2)
  +-- UnitHolder (Level 1)
  |     +-- Unit (Level 2)
  |           +-- OfferHolder (Level 3)
  |           |     +-- Offer (Level 4)
  |           +-- ProcessHolder (Level 3)
  |                 +-- Process (Level 4)
  +-- LocationHolder (Level 1)
  |     +-- Location (Level 2)
  |     +-- Hours (Level 2)
  +-- DNAHolder (Level 1)
  |     +-- Task (Level 2)
  ...
```

**Maximum downward depth from Business**: 4 levels (Business -> UnitHolder -> Unit -> OfferHolder -> Offer)
**Maximum upward depth to Business**: 4 levels (Offer -> OfferHolder -> Unit -> UnitHolder -> Business)
**Total traversal may span**: 8-9 levels (4 up + 4 down + root)

---

## Entity Counts by Custom Field

| Entity | Custom Fields |
|--------|---------------|
| Business | 19 |
| Contact | 19 |
| Unit | 31 |
| Offer | 39 |
| Process | 9 |
| Location | 8 |
| Hours | 9 |
| **Total** | **134** |

---

*Reference document. Source: .archive/discovery/DISCOVERY-HYDRATION-001.md*
