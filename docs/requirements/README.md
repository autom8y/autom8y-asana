# Product Requirements Documents

> Consolidated PRDs for the Autom8 Asana SDK.

## Quick Navigation

| PRD | Title | Description | Related TDD |
|-----|-------|-------------|-------------|
| [PRD-01](PRD-01-foundation-architecture.md) | Foundation & SDK Architecture | SDK extraction, architecture hardening, and operational stability | [TDD-01](../design/TDD-01-foundation-architecture.md) |
| [PRD-02](PRD-02-data-layer.md) | Data Layer Architecture | Polars dataframes, schema design, and custom field resolution | [TDD-02](../design/TDD-02-data-layer.md) |
| [PRD-03](PRD-03-batch-save-operations.md) | Batch & Save Operations | Batch API and SaveSession orchestration with Unit of Work pattern | [TDD-04](../design/TDD-04-batch-save-operations.md) |
| [PRD-04](PRD-04-custom-fields.md) | Custom Fields Architecture | Custom field tracking, descriptors, and type remediation | [TDD-06](../design/TDD-06-custom-fields.md) |
| [PRD-05](PRD-05-navigation-hydration.md) | Navigation & Hydration | Entity relationships, hierarchy hydration, and holder factories | [TDD-07](../design/TDD-07-navigation-hydration.md) |
| [PRD-06](PRD-06-business-domain.md) | Business Domain Architecture | Business models, process pipelines, and automation layer | [TDD-08](../design/TDD-08-business-domain.md) |
| [PRD-07](PRD-07-detection-resolution.md) | Detection & Resolution | Entity detection, cross-holder resolution, and workspace registry | [TDD-09](../design/TDD-09-registry-seeding.md), [TDD-11](../design/TDD-11-resolution-hardening.md) |
| [PRD-08](PRD-08-field-seeding.md) | Field Seeding Configuration | Field seeding configuration and gap analysis | [TDD-09](../design/TDD-09-registry-seeding.md) |
| [PRD-09](PRD-09-sdk-usability.md) | SDK Usability | Developer experience and API usability improvements | [TDD-10](../design/TDD-10-operations-usability.md) |
| [PRD-10](PRD-10-quality-triage.md) | Quality & Triage | QA findings and critical bug remediation | N/A |
| [PRD-11](PRD-11-debt-migration.md) | Technical Debt & Migration | Debt remediation and documentation reset | [TDD-12](../design/TDD-12-debt-migration.md) |

---

## Document Structure

Each consolidated PRD follows a consistent structure:

1. **Metadata** - Status, date, consolidation sources, related TDDs
2. **Executive Summary** - Key capabilities and outcomes
3. **Problem Statement** - Current state issues and pain points
4. **Requirements** - Functional and non-functional specifications
5. **Success Criteria** - Measurable outcomes for validation

---

## PRD-TDD Alignment

PRDs define **what** and **why**; TDDs define **how**. The consolidation effort aligned PRD and TDD numbering where possible:

| Domain | PRD | TDD |
|--------|-----|-----|
| Foundation | PRD-01 | TDD-01 |
| Data Layer | PRD-02 | TDD-02 |
| Batch/Save | PRD-03 | TDD-04 |
| Custom Fields | PRD-04 | TDD-06 |
| Navigation | PRD-05 | TDD-07 |
| Business Domain | PRD-06 | TDD-08 |
| Detection | PRD-07 | TDD-09, TDD-11 |
| Field Seeding | PRD-08 | TDD-09 |
| Usability | PRD-09 | TDD-10 |
| Quality | PRD-10 | N/A |
| Debt/Migration | PRD-11 | TDD-12 |

Note: TDD-03 (Resource Clients) and TDD-05 (Observability) exist as standalone technical designs without dedicated PRDs.

---

## Archive

Original PRDs are preserved for historical reference:

**Location**: [`docs/.archive/2025-12-prds/`](../.archive/2025-12-prds/)

The archive contains 25+ original PRDs that were consolidated into the 11 documents above. Each consolidated PRD lists its source documents in the Metadata section under "Consolidated From".

**Archive manifest**: [`docs/.archive/2025-12-prds/CONSOLIDATION-MANIFEST.yaml`](../.archive/2025-12-prds/CONSOLIDATION-MANIFEST.yaml)

---

## Creating New PRDs

For new feature requirements:

1. Determine if the requirement fits an existing consolidated PRD
2. If extending existing functionality, update the relevant PRD
3. If net-new capability, create `PRD-NN-descriptive-name.md`
4. Use numbered format (PRD-12, PRD-13, etc.) for consistency with consolidation
5. Create corresponding TDD in `/docs/design/`
6. Update this README and [INDEX.md](../INDEX.md)

---

## See Also

- [TDD README](../design/README.md) - Technical design documents
- [ADR INDEX](../decisions/INDEX.md) - Architectural decisions
- [INDEX.md](../INDEX.md) - Full documentation registry
