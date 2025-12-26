# ADR-0002: Demo Scope Boundaries

## Metadata
- **Status**: Accepted
- **Date**: 2025-12-25
- **Consolidated From**: ADR-0058
- **Related**: reference/DEMO.md, PRD-SDKDEMO

## Context

During the SDK Demo Bug Fix Sprint, BUG-4 was identified: the demo script displays GIDs instead of human-readable names in some output contexts.

Example output showing the issue:
```
# Current behavior
Custom Field: 1234567890123456 = High  # Shows GID, not field name
Tag added: 9876543210987654           # Shows GID, not tag name

# Desired behavior
Custom Field: Priority = High
Tag added: optimize
```

### Bug Assessment

| Aspect | Evaluation |
|--------|------------|
| **Impact** | Cosmetic - demo output readability only |
| **Severity** | Low - does not affect SDK functionality |
| **Scope** | Demo script only - not SDK code |
| **Implementation** | ~20-30 lines, demo script only, zero SDK changes |
| **Risk** | None - no SDK changes required |
| **Priority** | P3 (lowest in sprint) |

### Sprint Context

The SDK Demo Bug Fix Sprint targeted "SDK bugs blocking demo execution." The sprint had limited sessions for implementation and QA of core SDK bugs (BUG-1, BUG-2, BUG-3). BUG-4 represented a scope boundary decision: include cosmetic demo improvements or maintain focus on SDK-blocking bugs.

### Forces at Play

1. **Sprint focus**: Sprint charter targets SDK bugs, not demo polish
2. **Time budget**: Limited sessions remaining for implementation and QA
3. **Value delivery**: Fixing SDK bugs has higher ROI than cosmetic improvements
4. **Demo purpose**: Validates SDK functionality; cosmetic output is secondary
5. **Localization**: Fix entirely within demo script, not SDK
6. **Success criteria**: Demo runs successfully with current output

## Decision

**BUG-4 (Demo GID Display) is out of scope for the SDK Demo Bug Fix Sprint.**

The issue is a cosmetic enhancement to demo output formatting, not an SDK bug. The demo script successfully demonstrates SDK functionality with current GID display. This work can be addressed in a future "Demo Polish" initiative.

## Rationale

1. **Not an SDK bug**: The SDK returns correct data; the demo chooses what to display. This is a presentation layer choice, not functionality defect.

2. **Sprint charter alignment**: Sprint fixes "SDK bugs blocking demo execution." The demo runs successfully—no execution blocking occurs.

3. **Resource allocation**: Better to allocate implementation and QA time to validating BUG-1, BUG-2, and BUG-3 fixes that actually impact SDK functionality.

4. **Incremental improvement philosophy**: Cosmetic enhancements can be bundled in future demo improvement initiatives without urgency pressure.

5. **Clear scope boundary**: Fix would be demo script only (~20-30 lines, zero SDK changes). If it doesn't touch SDK code, it doesn't belong in SDK bug sprint.

### What Would Be Required (Future Reference)

If addressed in future "Demo Polish" initiative:

1. **Demo script changes only**: Modify output formatting in demo_sdk_operations.py
2. **Name lookups**: Use existing client.custom_fields.get_async() or cache names
3. **Scope**: ~20-30 lines of demo code, zero SDK changes
4. **Approach**: Leverage NameResolver pattern from ADR-0001 for consistency

## Alternatives Considered

### Alternative A: Include in Sprint

**Description**: Design and implement GID-to-name resolution in demo output during SDK bug sprint

**Pros**:
- Complete all identified issues
- Better demo output readability
- Addresses all items on bug list

**Cons**:
- Scope creep - not an SDK bug per charter
- Consumes implementation/QA time better spent on SDK fixes
- Demo already functional for validation purposes
- Sets precedent for including non-SDK work in SDK sprints

**Why not chosen**: Does not align with sprint charter targeting SDK-blocking bugs

### Alternative B: Quick Fix Without ADR

**Description**: Just fix the demo without formal documentation

**Pros**:
- Fast implementation
- No ceremony overhead
- Issue resolved immediately

**Cons**:
- Sets precedent for undocumented scope additions
- May mask larger design questions about demo output strategy
- No audit trail for why work was added mid-sprint
- Violates 10x-workflow standard of documenting significant decisions

**Why not chosen**: Even exclusions should be documented for audit trail and preventing scope creep

## Consequences

### Positive

1. **Focus maintained**: Sprint stays focused on SDK-blocking bugs, avoiding scope creep
2. **Clear scope boundary**: Documented decision prevents future confusion about what belongs in SDK work vs. demo polish
3. **Time preserved**: QA can thoroughly validate BUG-1, BUG-2, BUG-3 fixes without distraction
4. **Charter integrity**: Demonstrates discipline in adhering to sprint goals
5. **Audit trail**: Future teams understand why cosmetic demo work was deferred

### Negative

1. **Demo output unchanged**: GIDs still display in some contexts, reducing readability
2. **Polish deferred**: Will need separate initiative to address cosmetic improvements
3. **Incomplete bug list**: Not all identified issues resolved in sprint

### Neutral

1. **Backlog item created**: Can be tracked as enhancement for future "Demo Polish" sprint
2. **No SDK impact**: SDK code unaffected by this decision
3. **Future scope clarity**: Sets precedent for distinguishing SDK bugs from demo enhancements

## Compliance

This ADR documents scope exclusion per the 10x-workflow standard of capturing all significant decisions, including what NOT to do.

### Tracking

- **Backlog**: Consider adding "Demo Polish" initiative to project backlog
- **Future scope**: If demo is used for customer presentations, revisit priority
- **Related work**: Any future demo output improvements should reference this ADR for context

### Scope Boundary Principle

Use this decision as reference for future scope questions:

**In scope for SDK work**: Bugs affecting SDK functionality, API correctness, SaveSession behavior, data integrity

**Out of scope for SDK work**: Demo cosmetics, example script polish, output formatting preferences

When unclear, ask: "Does this require changing SDK code, or only demo/example code?"
