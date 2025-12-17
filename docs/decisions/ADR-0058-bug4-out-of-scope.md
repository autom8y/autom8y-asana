# ADR-0058: BUG-4 Demo GID Display Out of Scope

## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-12
- **Deciders**: Architect, Requirements Analyst
- **Related**: PRD-SDKDEMO, SDK Demo Bug Fix Sprint Session 1 Analysis

## Context

BUG-4 identified that the demo script displays GIDs instead of human-readable names in some output contexts:

```
# Example from demo output
Custom Field: 1234567890123456 = High  # Shows GID, not field name
Tag added: 9876543210987654           # Shows GID, not tag name
```

### Bug Classification

| Aspect | Assessment |
|--------|------------|
| **Impact** | Cosmetic - demo output readability only |
| **Severity** | Low - does not affect SDK functionality |
| **Scope** | Demo script only - not SDK code |
| **Risk** | None - no SDK changes required |
| **Priority** | P3 (lowest in sprint) |

### Analysis from Session 1

The Requirements Analyst categorized BUG-4 as:

> "4. **BUG-4: Demo displays GIDs instead of names** (P3 - Demo cosmetic)
>    - **Root Cause**: Demo output formatting, not SDK
>    - **Decision needed**: In-scope (design fix) or out-of-scope (demo-only)?
>    - **Analyst recommends: Out of scope**"

### Forces at Play

1. **Sprint focus**: Sprint targets SDK bugs blocking demo, not demo polish
2. **Time budget**: Limited sessions remaining for implementation and QA
3. **Value delivery**: Fixing SDK bugs (BUG-1, BUG-2, BUG-3) has higher ROI
4. **Demo purpose**: Demo validates SDK functionality, cosmetic output is secondary
5. **Localization**: Fix would be entirely within demo script, not SDK

## Decision

**BUG-4 is out of scope for the SDK Demo Bug Fix Sprint.**

The issue is a cosmetic enhancement to demo output formatting, not an SDK bug. The demo script successfully demonstrates SDK functionality even with GID display.

## Rationale

### Why Out of Scope

1. **Not an SDK bug**: The SDK returns correct data; the demo chooses what to display
2. **Sprint charter**: Sprint fixes "SDK bugs blocking demo execution" - demo runs successfully
3. **Resource allocation**: Better to allocate QA time to BUG-1, BUG-2, BUG-3 validation
4. **Incremental improvement**: Can be addressed in a future "Demo Polish" initiative

### What Would Be Required (Future Reference)

If addressed later, the fix would involve:

1. **Demo script changes only**: Modify output formatting in `demo_sdk_operations.py`
2. **Name lookups**: Use existing `client.custom_fields.get_async()` or cache names
3. **Scope**: ~20-30 lines of demo code, zero SDK changes

## Alternatives Considered

### Alternative A: Include in Sprint

**Description**: Design and implement GID-to-name resolution in demo

**Pros**:
- Complete all identified issues
- Better demo output

**Cons**:
- Scope creep - not an SDK bug
- Consumes implementation/QA time better spent on SDK fixes
- Demo already functional

**Why not chosen**: Does not align with sprint charter

### Alternative B: Quick Fix Without ADR

**Description**: Just fix the demo without formal documentation

**Pros**:
- Fast
- No ceremony

**Cons**:
- Sets precedent for undocumented scope additions
- May mask larger design questions

**Why not chosen**: Even exclusions should be documented for audit trail

## Consequences

### Positive

1. **Focus maintained**: Sprint stays focused on SDK-blocking bugs
2. **Clear scope**: Documented decision prevents future confusion
3. **Time preserved**: QA can thoroughly validate BUG-1, BUG-2, BUG-3 fixes

### Negative

1. **Demo output unchanged**: GIDs still display in some contexts
2. **Polish deferred**: Will need separate initiative to address

### Neutral

1. **Backlog item**: Can be tracked as enhancement for future sprint
2. **No SDK impact**: SDK code unaffected by this decision

## Tracking

- **Backlog**: Consider adding "Demo Polish" initiative to project backlog
- **Future scope**: If demo is used for customer presentations, revisit priority

## Compliance

This ADR documents scope exclusion per the 10x-workflow standard of capturing all significant decisions, including what NOT to do.
