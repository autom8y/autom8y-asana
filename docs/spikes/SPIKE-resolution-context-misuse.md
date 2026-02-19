# SPIKE: ResolutionContext business_gid Misuse Audit

**Date:** 2026-02-19
**Timebox:** 1 hour
**Status:** COMPLETE

## Question

Where in the codebase is `ResolutionContext(business_gid=...)` called with a GID that is NOT actually a Business entity? What is the full surface area of this entity model violation?

## Context

During E2E validation of the insights_export workflow against offer `1205925604226368`, we discovered that `_resolve_offer()` passes an **OfferHolder GID** as `business_gid` to `ResolutionContext`. The fast-path in `ResolutionContext` trusts this GID and loads it directly via `Business.from_gid_async()`, bypassing the `HierarchyTraversalStrategy` that correctly walks the parent chain.

**Entity Hierarchy (Offer path):**
```
Business
  └── UnitHolder
        └── Unit
              └── OfferHolder    ← Offer.parent (NOT Business!)
                    └── Offer
```

**Entity Hierarchy (Contact path):**
```
Business
  └── ContactHolder    ← ContactHolder.parent IS Business
        └── Contact
```

## Methodology

Two parallel exploration agents audited the entire codebase:
1. **Agent 1**: All `ResolutionContext(business_gid=...)` instantiation sites — verified what each GID actually points to
2. **Agent 2**: All `parent_gid` / `parent.gid` extraction patterns in automation code — verified hierarchy assumptions

## Findings

### All ResolutionContext Instantiation Sites

| File | Lines | Source of business_gid | Actual Entity Type | Status |
|------|-------|----------------------|-------------------|--------|
| `insights_export.py` | 664-668 | `offer_task.parent.gid` | **OfferHolder** | **BUG** |
| `conversation_audit.py` | 588-593 | `holder_task.parent.gid` | Business | CORRECT |
| `pipeline.py` | 562-567 | `source_process.business.gid` | Business | CORRECT |
| `lifecycle/engine.py` | 354, 577, 610 | `trigger_entity=source_process` | (uses resolution chain) | CORRECT |

### BUG: insights_export.py — CRITICAL

**3 call sites, 1 root cause:**

```python
# Line 399 (_enumerate_offers_section_targeted): extracts OfferHolder GID
"parent_gid": t.parent.gid if t.parent else None,  # ← OfferHolder GID

# Line 447 (_enumerate_offers_fallback): same extraction
"parent_gid": t.parent.gid if t.parent else None,  # ← OfferHolder GID

# Line 664-668 (_resolve_offer): passes OfferHolder GID as business_gid
async with ResolutionContext(
    self._asana_client,
    business_gid=parent_gid,  # ← BUG: OfferHolder GID, not Business
) as ctx:
    business = await ctx.business_async()  # Fast-path loads OfferHolder as Business
    office_phone = business.office_phone   # None (OfferHolder has no phone)
    vertical = business.vertical            # None (OfferHolder has no vertical)
```

**Impact:** The fast-path at `context.py:191-200` calls `Business.from_gid_async(client, offerHolder_gid)`, which fetches the OfferHolder task and attempts to construct a `Business` from it. Custom field descriptors (`office_phone`, `vertical`) return `None` because those fields don't exist on OfferHolder tasks.

### CORRECT: conversation_audit.py

```python
# ContactHolder.parent IS Business — this works correctly
business_gid = holder_task.parent.gid  # ← Business GID (correct)
```

The Contact hierarchy has ContactHolder as a direct child of Business, so `parent.gid` is valid here. However, the code works **by structural coincidence** — a variable named `parent_gid` without type validation is fragile.

### CORRECT: pipeline.py

```python
# Navigates via resolved object property, not raw parent chain
business_gid = source_process.business.gid  # ← Pre-resolved Business reference
```

### CORRECT: lifecycle/engine.py

```python
# Uses trigger_entity, which invokes the resolution strategy chain
async with ResolutionContext(client, trigger_entity=source_process) as ctx:
```

This is the **correct pattern** — passes an entity and lets the `HierarchyTraversalStrategy` traverse to Business.

### Additional Patterns Audited (No Bugs)

| File | Pattern | Status |
|------|---------|--------|
| `asset_edit.py:659-669` | Traverses `offer.parent.parent` (OfferHolder → Unit) | CORRECT |
| `strategies.py:265-276` | Generic parent traversal with `try/except` Business validation | DEFENSIVE (correct) |

## Root Cause Analysis

1. **Inconsistent hierarchy depths**: Some entities (ContactHolder) are direct Business children; others (Offer) are 4 levels deep. Code authors assumed `entity.parent = Business` universally.

2. **No type safety on GIDs**: `parent_gid` is an untyped string — nothing prevents passing an OfferHolder GID where a Business GID is expected.

3. **Fast-path trusts the caller**: `ResolutionContext(business_gid=X)` assumes X is truly a Business GID and skips traversal entirely. There's no validation.

## Fix Strategy

### Option A: Fix the caller (minimal, recommended)

Change `_resolve_offer()` to use `trigger_entity` instead of `business_gid`, letting the resolution chain traverse correctly:

```python
# Instead of: ResolutionContext(client, business_gid=parent_gid)
# Use:        ResolutionContext(client, trigger_entity=offer_entity)
```

Also stop caching `parent_gid` in enumeration dicts (lines 399, 447) since it's the wrong entity.

### Option B: Add fast-path validation (defense-in-depth)

Add a type check in `ResolutionContext._resolve_business_async()` to verify the loaded entity is actually a Business before returning it. Fall back to traversal if validation fails.

### Recommendation

**Option A + B**: Fix the caller (immediate) AND add fast-path validation (defense-in-depth). The fast-path optimization is valuable for cases where the caller truly has the Business GID, but it should fail safely rather than silently returning wrong data.

## Follow-up Actions

- [ ] Fix `_resolve_offer()` to use `trigger_entity` or traverse to Business correctly
- [ ] Remove or rename `parent_gid` from offer enumeration dicts (it's OfferHolder GID, not Business)
- [ ] Add fast-path validation in `ResolutionContext` to detect non-Business entities
- [ ] Re-run E2E validation against offer `1205925604226368` after fix
- [ ] Consider adding `EntityType` enum to GID references for type safety
