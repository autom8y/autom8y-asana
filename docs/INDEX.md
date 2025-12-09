# Documentation Index

> Central registry of all project documentation. Update this file when creating new documents.

## PRDs

| ID | Title | Status | Date |
|----|-------|--------|------|
| [PRD-0001](requirements/PRD-0001-sdk-extraction.md) | autom8_asana SDK Extraction | Approved | 2025-12-08 |
| [PRD-0002](requirements/PRD-0002-intelligent-caching.md) | Intelligent Caching Layer | Draft | 2025-12-09 |

## TDDs

| ID | Title | PRD | Status | Date |
|----|-------|-----|--------|------|
| [TDD-0001](design/TDD-0001-sdk-architecture.md) | autom8_asana SDK Architecture | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0002](design/TDD-0002-models-pagination.md) | Core Models and Pagination Infrastructure | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0003](design/TDD-0003-tier1-clients.md) | Tier 1 Resource Clients | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0004](design/TDD-0004-tier2-clients.md) | Tier 2 Resource Clients | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0005](design/TDD-0005-batch-api.md) | Batch API for Bulk Operations | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0006](design/TDD-0006-backward-compatibility.md) | Backward Compatibility Layer | PRD-0001 | Draft | 2025-12-08 |
| [TDD-0007](design/TDD-0007-observability.md) | Observability Enhancements | PRD-0001 | Draft | 2025-12-08 |

## ADRs

| ID | Title | Status | Date |
|----|-------|--------|------|
| [ADR-0001](decisions/ADR-0001-protocol-extensibility.md) | Protocol-Based Extensibility for Dependency Injection | Accepted | 2025-12-08 |
| [ADR-0002](decisions/ADR-0002-sync-wrapper-strategy.md) | Fail-Fast Strategy for Sync Wrappers in Async Contexts | Accepted | 2025-12-08 |
| [ADR-0003](decisions/ADR-0003-asana-sdk-integration.md) | Replace Asana SDK HTTP Layer, Retain Types and Error Parsing | Accepted | 2025-12-08 |
| [ADR-0004](decisions/ADR-0004-item-class-boundary.md) | Minimal AsanaResource in SDK, Full Item Stays in Monolith | Accepted | 2025-12-08 |
| [ADR-0005](decisions/ADR-0005-pydantic-model-config.md) | Pydantic v2 with extra="ignore" for Forward Compatibility | Accepted | 2025-12-08 |
| [ADR-0006](decisions/ADR-0006-namegid-standalone-model.md) | NameGid as Standalone Frozen Model | Proposed | 2025-12-08 |
| [ADR-0007](decisions/ADR-0007-consistent-client-pattern.md) | Consistent Client Pattern Across Resource Types | Accepted | 2025-12-08 |
| [ADR-0008](decisions/ADR-0008-webhook-signature-verification.md) | Webhook Signature Verification Strategy | Accepted | 2025-12-08 |
| [ADR-0009](decisions/ADR-0009-attachment-multipart-handling.md) | Attachment Multipart/Form-Data Handling | Accepted | 2025-12-08 |
| [ADR-0010](decisions/ADR-0010-batch-chunking-strategy.md) | Sequential Chunk Execution for Batch Operations | Accepted | 2025-12-08 |
| [ADR-0011](decisions/ADR-0011-deprecation-warning-strategy.md) | Deprecation Warning Strategy for Compatibility Layer | Proposed | 2025-12-08 |
| [ADR-0012](decisions/ADR-0012-public-api-surface.md) | Public API Surface Definition | Proposed | 2025-12-08 |
| [ADR-0013](decisions/ADR-0013-correlation-id-strategy.md) | Correlation ID Strategy for SDK Observability | Proposed | 2025-12-08 |
| [ADR-0014](decisions/ADR-0014-example-scripts-env-config.md) | Environment Variable Configuration for Example Scripts | Accepted | 2025-12-09 |
| [ADR-0015](decisions/ADR-0015-batch-api-request-format.md) | Batch API Request Format Fix | Accepted | 2025-12-09 |

## Test Plans

| ID | Title | PRD | TDD | Status |
|----|-------|-----|-----|--------|
| [TP-0001](testing/TEST-PLAN-0001.md) | autom8_asana SDK Phase 1 Parity Validation | PRD-0001 | TDD-0001 | Draft |
| [TP-batch-api-adversarial](testing/TP-batch-api-adversarial.md) | Batch API Adversarial Testing | PRD-0001 | TDD-0005 | Completed |
