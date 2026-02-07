---
artifact_id: PRD-GAP-01-hierarchical-save
title: "Hierarchical Save -- Holder Auto-Creation"
created_at: "2026-02-07T15:30:00Z"
author: requirements-analyst
status: approved
complexity: MODULE
impact: high
impact_categories: [data_model, api_contract]
source: docs/GAPS/Q1/GAP-01-hierarchical-save.md
related_gaps:
  - GAP-06 (LIS-Based Subtask Reordering -- depends on this)
  - GAP-07 (Adapter Expansion -- depends on this)
success_criteria:
  - id: SC-001
    description: "Saving a Business with unpopulated holders creates the missing holder subtasks in Asana"
    testable: true
    priority: must-have
    verification: "Business with 0 holders in Asana -> commit_async() -> re-fetch subtasks -> 7 holder subtasks exist"
  - id: SC-002
    description: "Pre-existing holders are detected and reused, not duplicated"
    testable: true
    priority: must-have
    verification: "Business with 3/7 holders -> commit_async() -> re-fetch -> still 7 total (4 created, 3 reused)"
  - id: SC-003
    description: "Children tracked beneath a newly-created holder are saved as subtasks of that holder"
    testable: true
    priority: must-have
    verification: "Track Business + new Contact -> commit_async() -> Contact.parent.gid == ContactHolder.gid"
  - id: SC-004
    description: "Concurrent in-process saves for the same Business do not create duplicate holders"
    testable: true
    priority: must-have
    verification: "Two concurrent coroutine commit_async() calls on same Business -> 7 holders total, not 14 (in-process only; cross-process deferred)"
  - id: SC-005
    description: "Holder auto-creation can be disabled by the caller"
    testable: true
    priority: should-have
    verification: "commit_async() with opt-out flag -> no holder creation, children with missing holders skipped"
  - id: SC-006
    description: "Unit nested holders (OfferHolder, ProcessHolder) are also auto-created when saving a Unit with children"
    testable: true
    priority: must-have
    verification: "Track Unit + new Offer -> commit_async() -> Offer.parent.gid == OfferHolder.gid"
  - id: SC-007
    description: "Full tree from scratch: all-new Business + holders + children saved in a single commit"
    testable: true
    priority: must-have
    verification: "New Business + new Contact + new Unit + new Offer -> commit_async() -> 5-level hierarchy materialized (Business -> UnitHolder -> Unit -> OfferHolder -> Offer)"
stakeholders:
  - architect
  - principal-engineer
  - qa-adversary
schema_version: "1.0"
---

# PRD: Hierarchical Save -- Holder Auto-Creation

## Overview

When a consumer saves a Business entity, the children beneath it (Contacts, Units, Offers, etc.) are organized through intermediate "holder" subtasks (ContactHolder, UnitHolder, etc.). Today, if a holder does not already exist in Asana, the save silently drops the children that would belong under it. Consumers must manually create holders and wire parent-child relationships before saving -- something the legacy monolith handled transparently.

This gap blocks the adapter expansion strategy (GAP-07) because any consumer migrating from the monolith expects to save a Business tree and have the full hierarchy materialize, including holder creation.

## Problem Statement

### Business Impact

- **Silent data loss**: Children added to a Business without existing holders are never saved. There is no error, no warning -- the save succeeds and the children vanish.
- **Migration blocker**: The monolith's `_get_or_create_subtasks()` makes holder creation invisible to callers. Any consumer ported to autom8_asana must add manual holder management code, increasing migration effort and risk.
- **Onboarding friction**: New consumers must understand the holder subtask pattern (a pure implementation detail of the Asana data model) before they can save hierarchical data. This leaks internal complexity.

### Current Behavior

1. `SaveSession.track(business, recursive=True)` calls `_track_recursive()`, which walks `HOLDER_KEY_MAP` but **only tracks holders that are already populated** (i.e., `_contact_holder is not None`). Unpopulated holders are silently skipped.
2. The dependency graph, batch executor, and temp GID resolution all function correctly for entities that ARE tracked. The gap is upstream: entities that should exist but don't are never constructed.
3. `_populate_holders()` on Business is a **read-path** method that hydrates holders from API-fetched subtasks. There is no corresponding write-path construction.

### Legacy Behavior (Target State)

The monolith's save path:
1. Detects which holder subtasks exist in Asana for the given Business.
2. Creates missing holders as subtasks with conventional names (e.g., `"{BusinessName} Contacts"`).
3. Wires new holders as subtasks of the Business via `setParent`.
4. Prevents duplicate creation under concurrency via per-holder-type locking.
5. This all happens transparently -- the consumer calls `business.save()` and the hierarchy materializes.

---

## Goals

1. **Transparent hierarchy materialization**: When a consumer saves a Business (or Unit) with children, any missing holder subtasks are automatically created and wired as parents of those children.
2. **Idempotent creation**: Running the same save twice, or running concurrent saves for the same Business, must not create duplicate holders.
3. **Existing holder reuse**: If a holder already exists in Asana, it must be detected and used -- never recreated.
4. **Caller opt-out**: Consumers who want to manage holders manually can disable auto-creation.

## Non-Goals

1. **Holder deletion**: Removing holders when they become empty is out of scope. Holders persist even with zero children.
2. **Holder re-ordering**: Sorting holders into a canonical order after creation is deferred to GAP-06 (LIS Reordering).
3. **Holder field population**: Setting custom fields on newly created holders (beyond name) is out of scope. Holders are structural containers, not data-carrying entities.
4. **Cross-Business holder sharing**: Each Business owns its own holder hierarchy. Sharing holders between Businesses is not supported.
5. **Holder migration**: Detecting holders in the wrong project or with incorrect names and fixing them is out of scope (that is the healing system's concern).
6. **Read-path changes**: The existing `_populate_holders()` / `_fetch_holders_async()` hydration flow is not modified.
7. ~~**Full tree construction from scratch**~~: **MOVED TO SCOPE** per stakeholder decision. Full tree from scratch (Business + all holders + all children, all new) is a MUST for v1. The system must handle 5-level temp GID chains with fan-outs: Business -> UnitHolder -> Unit -> OfferHolder/ProcessHolder -> Offer/Process.

---

## User Stories

### US-001: Save Business with New Contacts

**As a** consumer creating Contact entities for an existing Business
**I want** the ContactHolder subtask to be created automatically if it doesn't exist
**So that** I can save Contacts without managing holder lifecycle manually

**Acceptance Criteria:**
- [ ] Saving a Business with tracked Contacts creates a ContactHolder subtask in Asana
- [ ] The ContactHolder becomes the parent of the new Contacts
- [ ] If the ContactHolder already exists, it is reused
- [ ] The ContactHolder name follows the established naming convention

### US-002: Save Unit with New Offers

**As a** consumer adding Offers to a Unit
**I want** the OfferHolder subtask to be created automatically under the Unit
**So that** I don't need to know about the holder layer to save Offers

**Acceptance Criteria:**
- [ ] Saving a Unit with tracked Offers creates an OfferHolder subtask
- [ ] The OfferHolder is a subtask of the Unit
- [ ] Offers are saved as subtasks of the OfferHolder

### US-003: Concurrent Business Saves

**As a** system with multiple processes saving to the same Business
**I want** holder creation to be idempotent
**So that** concurrent operations don't corrupt the hierarchy

**Acceptance Criteria:**
- [ ] Two concurrent saves create exactly one set of holders, not two
- [ ] The second save detects holders created by the first and reuses them
- [ ] No 409 Conflict errors or orphaned subtasks

### US-004: Opt Out of Holder Auto-Creation

**As a** power user who manages holders manually
**I want** to disable auto-creation
**So that** SaveSession does not make unintended API calls

**Acceptance Criteria:**
- [ ] An explicit opt-out mechanism exists (flag, config, or parameter)
- [ ] When disabled, save behavior matches today's behavior (unpopulated holders are skipped)
- [ ] The opt-out is per-session, not global

---

## Functional Requirements

### Must Have

#### FR-001: Holder Existence Detection

Before creating holders, the system must determine which holders already exist as subtasks of the target parent entity.

- Detection must work for both Business holders (7 types) and Unit holders (2 types).
- Detection must use the same identification logic as the read path (name/emoji matching or project membership detection) to ensure consistency.
- A holder that exists in Asana but is not hydrated locally counts as "existing" and must not be recreated.

#### FR-002: Missing Holder Construction

When a parent entity has children that require a holder, and that holder does not exist, the system must construct the holder subtask.

- The holder must be created as a subtask of its parent entity (Business or Unit).
- The holder name must follow the naming convention established in `HOLDER_KEY_MAP` (e.g., the ContactHolder for "Acme Corp" should include the conventional name and emoji).
- The holder must be created before any of its children are saved (dependency ordering).
- Creation must integrate with the existing temp GID system so that children can reference the holder's GID before it is assigned by the API.

#### FR-003: Dependency Graph Integration

Newly constructed holders must participate in the existing dependency graph so that the save pipeline processes them in the correct order.

- Holders must be saved before their children.
- Children must reference the holder as their parent.
- The temp GID resolution chain must handle up to 5 levels with fan-outs: Business -> UnitHolder -> Unit -> OfferHolder/ProcessHolder -> Offer/Process.

#### FR-004: SetParent Wiring

After a holder is created, it must be wired as a subtask of its parent entity via the Asana `setParent` API.

- Newly created holders must have `setParent` called to establish the parent-child relationship.
- `setParent` for multiple holders of the same Business should be batched where possible.

#### FR-005: Idempotent Creation Under Concurrency

Concurrent saves targeting the same parent entity must not create duplicate holders.

- If two processes attempt to create the same holder type for the same parent simultaneously, only one holder should result.
- The system must handle the race condition where a holder is created between detection and creation (time-of-check to time-of-use).
- The idempotency mechanism must work correctly for in-process concurrency (multiple coroutines) via `asyncio.Lock` per holder type. Cross-process concurrency (multiple service instances) is explicitly deferred.

#### FR-006: Opt-Out Mechanism

Consumers must be able to disable holder auto-creation.

- When disabled, the save pipeline behaves as it does today: unpopulated holders are silently skipped.
- **Resolved**: Separate `auto_create_holders` flag on `SaveSession`, defaulting to `True` (opt-out). Independent of the `recursive` flag.

#### FR-007: Unit Nested Holder Support (**Promoted from SHOULD to MUST** per stakeholder decision)

Holder auto-creation must work recursively for Unit-level holders (OfferHolder, ProcessHolder), not just Business-level holders.

- When saving a Business tree that includes Units with children, the full hierarchy must materialize: Business -> UnitHolder -> Unit -> OfferHolder -> Offer.
- This requires multi-level holder creation in a single commit.
- The temp GID resolution chain must handle 5 levels with fan-outs: Business (L1) -> UnitHolder (L2) -> Unit (L3) -> OfferHolder/ProcessHolder (L4) -> Offer/Process (L5).

### Should Have

#### FR-008: Holder Project Assignment

Newly created holders should be added to the correct Asana project(s) so that the detection system can identify them via Tier 1 (project membership) in the future.

- The project assignment must align with whatever detection metadata is available for each holder type.
- Not all holder types have `PRIMARY_PROJECT_GID` defined (e.g., LocationHolder has `None`). The system must handle this gracefully.

### Could Have

#### FR-009: Holder Ordering After Creation

After all holders are created for a parent, they should be ordered to match the canonical order in `HOLDER_KEY_MAP`.

- This aligns with GAP-06 (LIS Reordering) and may be deferred entirely to that work item.

---

## Non-Functional Requirements

### NFR-001: Performance

| Metric | Target |
|--------|--------|
| Holder detection latency (per parent) | < 500ms (one `subtasks` API call) |
| Holder creation latency (per holder) | < 1s (one `create` + one `setParent` call) |
| Full Business hierarchy save (7 holders + children) | < 15s including all holder creation |
| No regression for saves where all holders exist | < 5% overhead from detection check |

### NFR-002: Reliability

- Partial holder creation failure must not corrupt the hierarchy. If 5/7 holders are created and the 6th fails, the 5 that succeeded must remain valid.
- Failed holder creation must be reported in the `SaveResult`, not silently swallowed.
- The system must tolerate Asana API eventual consistency (e.g., a newly created holder may not appear immediately in a `subtasks` listing).

### NFR-003: Observability

- Structured log events for: holder detection started, holder detected (existing), holder creation started, holder creation succeeded, holder creation failed, duplicate holder detected (idempotency).
- Each event must include: `business_gid`, `holder_type`, `holder_gid` (when available).

### NFR-004: Backward Compatibility

- Existing save workflows that do not use holders must not be affected.
- The public API of `SaveSession` must remain backward compatible. New parameters (if any) must have defaults that preserve current behavior.

---

## Edge Cases

| Case | Expected Behavior |
|------|------------------|
| All 7 holders already exist | No creation; detection finds all, proceeds to save children |
| 0 of 7 holders exist | Creates all 7, then saves children under them |
| Holder exists but has wrong name | Detected via project membership (Tier 1) or emoji (Tier 2), not recreated |
| Holder exists but is not in expected project | Used as-is; project correction is the healing system's job, not this feature's |
| Business has no children to save | No holder detection or creation needed; no-op for this feature |
| Business itself is new (no GID yet) | Business must be created first (existing dependency graph handles this); then holders are created referencing Business's resolved GID |
| Holder type has no PRIMARY_PROJECT_GID | Holder created without project assignment; detection will fall back to Tier 2/3 |
| API rate limit during holder creation | Existing transport retry/backoff handles this; partial success reported |
| Asana returns 403 on holder creation | Holder creation fails; children under that holder are cascading failures in SaveResult |
| Holder created by concurrent process between detection and creation | Duplicate detection at API level (Asana allows duplicate subtask names); idempotency mechanism must handle |
| SaveSession with recursive=False but children need holders | No holder creation; recursive=False means "only save what I explicitly tracked" |
| Unit holder creation when UnitHolder itself doesn't exist yet | Multi-level: Business -> UnitHolder (created) -> Unit -> OfferHolder (created) -> Offer; dependency graph must handle 4-level chain |

---

## Success Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| SC-001 | Missing holders are created during save | Integration test: Business with 0 holders -> save -> 7 holders exist |
| SC-002 | Existing holders are reused | Test: Business with 3/7 holders -> save -> 7 total, 3 unchanged |
| SC-003 | Children are parented under created holders | Test: new Contact's parent GID == new ContactHolder's GID |
| SC-004 | Concurrent saves don't duplicate | Concurrency test: 2 parallel saves -> 7 holders, not 14 |
| SC-005 | Opt-out disables creation | Test: opt-out flag -> save succeeds, no holders created |
| SC-006 | Unit nested holders auto-created | Test: Unit + Offer -> OfferHolder created under Unit |

---

## Open Questions (RESOLVED)

All open questions resolved via stakeholder interview on 2026-02-07.

| ID | Question | Resolution |
|----|----------|------------|
| OQ-1 | Should auto-creation be opt-in or opt-out by default? | **Separate `auto_create_holders` flag on SaveSession, defaults to `True` (opt-out).** Independent of `recursive` flag. Matches legacy behavior while giving explicit control. |
| OQ-2 | Where should the auto-creation logic live? | **Architect chooses between new SavePipeline phase or standalone HolderManager service.** Options of extending `_track_recursive` or pre-commit hook are off the table. |
| OQ-3 | How should holder naming be specified? | **Derive from existing `HOLDER_KEY_MAP`.** No new data structures or abstractions. Naming stays consistent with read-path detection logic. |
| OQ-4 | What concurrency mechanism handles cross-process idempotency? | **`asyncio.Lock` per holder type, in-process only.** Cross-process idempotency is explicitly deferred. No distributed locking infrastructure needed for v1. |
| OQ-5 | Should holder project assignment use `PRIMARY_PROJECT_GID` or a separate mapping? | **Use `PRIMARY_PROJECT_GID` where available.** Skip project assignment for holder types where it's `None`. Detection falls back to Tier 2/3 for those. |
| OQ-6 | How does auto-creation interact with the healing system? | **No healing integration for v1.** Healing system picks up holders in its normal sweep. No coupling between auto-creation and healing. |
| OQ-7 | What is the error strategy for partial holder creation failure? | **Retry failed holders with backoff, then partial-success semantics.** Save what succeeds, report failures in `SaveResult`. No rollback of successfully created holders. |

---

## Dependencies

| Dependency | Type | Status | Notes |
|------------|------|--------|-------|
| SaveSession + SavePipeline | Internal | Exists | Core save infrastructure; this feature extends it |
| DependencyGraph (Kahn's algorithm) | Internal | Exists | Must handle additional levels for auto-created holders |
| Temp GID resolution | Internal | Exists | Must handle multi-level chains (Business -> Holder -> Child) |
| `set_parent` action support | Internal | Exists | Used to wire holders as subtasks |
| HolderFactory / HOLDER_KEY_MAP | Internal | Exists | Provides holder type definitions |
| Business._populate_holders / detection | Internal | Exists | Read-path detection reused for write-path existence check |
| Asana Tasks API (create, subtasks, setParent) | External | Available | Standard Asana API operations |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Asana API eventual consistency | Medium | Holder created but not visible in immediate subtasks listing | Retry detection with backoff; or skip detection after known creation |
| Duplicate holders from race conditions | Medium | Data corruption, confusing UI | Idempotency mechanism (OQ-4); detection before creation |
| Multi-level temp GID chain breaks | Low | Children fail to save | Existing temp GID system handles 2 levels; verify 3+ levels work |
| Holder name mismatch with detection | Low | Created holder not found by read path | Use same naming source as detection logic |
| Performance regression for simple saves | Low | Slower saves for consumers who don't use holders | Detection step adds one API call per parent; opt-out avoids entirely |

---

## Out of Scope / Deferred

| Item | Rationale | Deferred To |
|------|-----------|-------------|
| LIS-based subtask reordering after creation | Separate concern with different complexity | GAP-06 |
| Adapter expansion consuming this feature | Depends on this + GAP-02 | GAP-07 |
| Holder deletion when empty | Low priority; holders are lightweight structural tasks | Backlog |
| Holder custom field population | Holders don't carry business data | Not planned |
| ~~Full tree creation from scratch~~ | **MOVED TO SCOPE** -- now a MUST per stakeholder decision (SC-007) | N/A |
| Distributed locking infrastructure | Not needed for v1 per OQ-4 resolution (in-process asyncio.Lock only) | Future if cross-process needed |
| Cross-process idempotency | Deferred per OQ-4 resolution; in-process only for v1 | Future |

---

## Stakeholder Decisions (2026-02-07)

Captured via structured stakeholder interview before design/implementation.

### Scope Changes

- **Full-tree-from-scratch**: Promoted from non-goal to **MUST**. 5-level temp GID chains with fan-outs required.
- **FR-007 (Unit nested holders)**: Promoted from SHOULD to **MUST**.
- **SC-004 (Concurrency)**: Scoped to **in-process only** (asyncio coroutines). Cross-process deferred.

### Design Constraints for Architect

- Architecture: Choose between **new SavePipeline phase** or **standalone HolderManager service** (no other options).
- Naming: Derive from **HOLDER_KEY_MAP** (no new abstractions).
- Concurrency: **asyncio.Lock** per holder type, in-process only.
- Project assignment: **PRIMARY_PROJECT_GID** where available, skip for `None`.
- Healing: No integration for v1.
- Errors: Retry with backoff, then partial-success semantics.
- Interface: Evolution allowed (new params with defaults, new fields). Greenfield mindset.

### Quality Bar

- **Testing**: Unit + integration tests for all success criteria (SC-001 through SC-007). Edge cases from PRD table covered.
- **Performance**: NFR-001 targets are aspirational. No benchmark tests for v1.
- **Documentation**: TDD + ADR + updated PRD (this document).

### Execution

- **Workflow**: Orchestrator determines phasing and agent routing.
- **Git**: Atomic commits directly to main via `/commit`. No feature branch.

---

## Artifact Attestation

| Artifact | Absolute Path | Verified |
|----------|---------------|----------|
| This PRD | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-GAP-01-hierarchical-save.md` | Read |
| Gap Analysis Brief | `/Users/tomtenuta/Code/autom8_asana/docs/GAPS/Q1/GAP-01-hierarchical-save.md` | Read |
| Gap Analysis Index | `/Users/tomtenuta/Code/autom8_asana/docs/GAPS/Q1/INDEX.md` | Read |
| SaveSession | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/session.py` | Read |
| SavePipeline | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/pipeline.py` | Read |
| DependencyGraph | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/graph.py` | Read |
| HealingManager | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/persistence/healing.py` | Read |
| HolderFactory | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/holder_factory.py` | Read |
| Business Model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/business.py` | Read |
| Unit Model | `/Users/tomtenuta/Code/autom8_asana/src/autom8_asana/models/business/unit.py` | Read |
| Style Reference (cascade PRD) | `/Users/tomtenuta/Code/autom8_asana/docs/requirements/PRD-cascade-field-resolution-generalized.md` | Read |
