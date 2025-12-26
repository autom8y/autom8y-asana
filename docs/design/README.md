# Technical Design Documents

> Consolidated TDDs for the Autom8 Asana SDK.

This directory contains 12 consolidated Technical Design Documents that define the complete SDK architecture. Each TDD synthesizes multiple related original documents into a single authoritative source.

## Quick Navigation

| TDD | Title | Scope |
|-----|-------|-------|
| [TDD-01](TDD-01-foundation-architecture.md) | Foundation & SDK Architecture | SDK extraction, backward compatibility, protocol design |
| [TDD-02](TDD-02-data-layer.md) | Data Layer Architecture | Pydantic models, Polars dataframes, schema design |
| [TDD-03](TDD-03-resource-clients.md) | Resource Client Architecture | Tier 1 and Tier 2 clients for all Asana resource types |
| [TDD-04](TDD-04-batch-save-operations.md) | Batch & Save Operations | Batch API chunking, SaveSession unit of work pattern |
| [TDD-05](TDD-05-observability.md) | Observability & Telemetry | Logging, metrics, correlation IDs, event hooks |
| [TDD-06](TDD-06-custom-fields.md) | Custom Fields Architecture | Resolution, tracking, descriptors, remediation |
| [TDD-07](TDD-07-navigation-hydration.md) | Navigation & Hydration | Entity relationships, lazy loading, navigation descriptors |
| [TDD-08](TDD-08-business-domain.md) | Business Domain Architecture | Process pipelines, automation, entity detection, self-healing |
| [TDD-09](TDD-09-registry-seeding.md) | Registry & Field Seeding | Workspace project registry, field seeding configuration |
| [TDD-10](TDD-10-operations-usability.md) | Operations & SDK Usability | Action endpoints, subtask operations, async method patterns |
| [TDD-11](TDD-11-resolution-hardening.md) | Resolution & Foundation Hardening | Cross-holder resolution, cascade fixes, SDK hardening |
| [TDD-12](TDD-12-debt-migration.md) | Technical Debt & Migration | Debt remediation, documentation reset, legacy cleanup |

## About the Consolidation

In December 2025, the TDD collection was consolidated from 38 original documents into 12 cohesive TDDs. This consolidation:

- **Reduces duplication**: Related designs now live in a single document
- **Improves navigation**: Engineers can find relevant architecture in one place
- **Preserves history**: All original documents remain accessible in the archive
- **Maintains traceability**: Each consolidated TDD lists its source documents in the Metadata section

### Consolidation Mapping

Each TDD-NN document consolidates multiple original TDDs. For example:

- **TDD-01** consolidates TDD-SDK-FAMILY and TDD-0006 (backward compatibility)
- **TDD-04** consolidates TDD-0005, TDD-0010, and TDD-0022 (batch and save operations)
- **TDD-08** consolidates TDD-PROCESS-PIPELINE, TDD-AUTOMATION-LAYER, TDD-DETECTION, and several business model TDDs

Check each document's Metadata section for the complete list of consolidated sources.

## Archive

Original TDDs are preserved in [`docs/.archive/2025-12-tdds/`](../.archive/2025-12-tdds/) for historical reference. The archive contains:

- 38 original TDD documents
- Complete git history preserved
- Useful for understanding design evolution and decision context

## Document Structure

Each consolidated TDD follows a consistent structure:

1. **Title and Overview** - What the document covers
2. **Metadata** - Status, date, consolidated sources, related ADRs
3. **Design Goals** - Objectives and principles
4. **Architecture** - System structure and component relationships
5. **Implementation Details** - Specific patterns and approaches
6. **Testing Strategy** - Verification approach
7. **Related Documents** - Links to ADRs, PRDs, and other TDDs

## Creating New TDDs

For new features or architectural changes:

1. Check if the work fits an existing consolidated TDD
2. If extending existing architecture: update the relevant TDD-NN document
3. If entirely new domain: create `TDD-NN-descriptive-name.md` using next available number
4. Always link related ADRs and PRDs in the Metadata section

## Status Values

All consolidated TDDs use the **Accepted** status, indicating the designs are approved and active. For status lifecycle details, see [CONVENTIONS.md](../CONVENTIONS.md).

## See Also

- [ADR Index](../decisions/INDEX.md) - Architecture Decision Records
- [PRD Directory](../requirements/) - Product Requirements Documents
- [Documentation Conventions](../CONVENTIONS.md) - Status lifecycle and formatting standards
