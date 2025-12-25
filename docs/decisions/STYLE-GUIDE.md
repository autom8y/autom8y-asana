# ADR Style Guide

Version: 1.0
Last Updated: 2025-12-24
Status: Canonical Reference

## Purpose

This guide codifies the quality standards for Architecture Decision Records (ADRs) in autom8_asana. Use this as the authoritative reference when creating or reviewing ADRs.

---

## Quick Reference

- **Next ADR Number**: ADR-0145
- **Naming Format**: `ADR-{NNNN}-{kebab-case-title}.md`
- **Location**: `/docs/decisions/`
- **Template**: `.claude/skills/documentation/templates/adr.md`
- **Quality Benchmark**: 90/100 for exemplary, 70/100 minimum for acceptance

---

## Canonical Template

All ADRs must follow this structure:

```markdown
# ADR-{NNNN}: {Decision Title}

## Metadata
- **Status**: Proposed | Accepted | Deprecated | Superseded by ADR-{NNNN}
- **Author**: {name}
- **Date**: {YYYY-MM-DD}
- **Deciders**: {who was involved}
- **Related**: PRD-{NNNN}, TDD-{NNNN}, ADR-{NNNN}

## Context
{situation and forces}

## Decision
{clear statement}

## Rationale
{why this over alternatives}

## Alternatives Considered
### {Alternative 1}
- **Description**: {what this option entails}
- **Pros**: {benefits}
- **Cons**: {drawbacks}
- **Why not chosen**: {specific reason}

## Consequences
### Positive
- {good outcomes}

### Negative
- {costs, risks, limitations}

### Neutral
- {other effects}

## Compliance
- {enforcement mechanisms}
```

---

## Section Requirements

### Title (5 points)

**Format**: `# ADR-{NNNN}: {Decision Title}`

**Requirements**:
- Use four-digit number with leading zeros (ADR-0035, not ADR-35)
- Title describes the decision, not the problem
- Use title case for the decision phrase
- Be specific and action-oriented

**Good**:
- `ADR-0035: Unit of Work Pattern for Save Orchestration`
- `ADR-0130: Cache Population Location Strategy`

**Bad**:
- `ADR-35: Save Session` (wrong number format)
- `ADR-0035: How to Handle Saves` (question, not decision)
- `ADR-0092: CRUD` (too vague)

---

### Metadata (10 points)

**Format**: Bullet list (not table)

**Required Fields** (all must be present):
1. **Status**: One of:
   - `Proposed` - decision documented, not yet implemented
   - `Accepted` - decision implemented and current
   - `Deprecated` - decision no longer recommended
   - `Superseded by ADR-{NNNN}` - replaced by another decision
   - `Rejected` - decision explicitly rejected (kept for history)
   - `Partially Superseded` - some portions replaced, others still valid
   - `Completed` - implementation finished (for migration ADRs)

2. **Author**: Name or role (Architect, Engineer, etc.)

3. **Date**: ISO format `YYYY-MM-DD`

4. **Deciders**: Who participated in the decision

5. **Related**: Cross-references to PRD/TDD/ADR documents

**Example**:
```markdown
## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
- **Deciders**: Architect, Principal Engineer
- **Related**: PRD-0005 (FR-UOW-001 through FR-UOW-008), TDD-0010
```

**Note**: If you see table-based metadata in older ADRs, convert to bullet list format.

---

### Context (20 points)

**Purpose**: Explain the situation, forces at play, and the problem/question that triggered the decision.

**What to Include**:
1. **Situation**: What is the current state? Why are we making this decision now?
2. **Forces**: What constraints or requirements are in tension?
3. **Problem/Question**: What specific issue needs resolution?

**Structure Options**:
- Prose paragraphs for narrative context
- **Forces at play** as bulleted list for clarity
- Tables for comparing constraints (see ADR-0130)

**Good Example** (ADR-0035):
```markdown
## Context

The autom8_asana SDK currently uses immediate persistence where every API call
executes immediately. PRD-0005 requires a Save Orchestration Layer that enables
Django-ORM-style deferred saves where multiple model changes are collected and
executed in optimized batches.

**Forces at play:**

1. **Developer Familiarity**: Django ORM's session.add() / session.commit()
   pattern is well-known
2. **Explicit Scope**: Developers need clear boundaries for which entities
   participate in a batch
3. **Resource Management**: HTTP connections, state tracking, and cleanup
   need proper lifecycle
4. **Error Handling**: Partial failures need to be captured and reported
   within a defined scope
5. **Async/Sync Duality**: SDK uses async-first with sync wrappers per ADR-0002

**Problem**: How should we structure the API for collecting and committing
multiple entity changes?
```

**What to Avoid**:
- Jumping straight to solution without explaining the problem
- Omitting constraints or forces
- Assuming reader knows project context

---

### Decision (15 points)

**Purpose**: State clearly and unambiguously what was decided.

**Requirements**:
1. **Clear Statement**: One sentence summarizing the decision
2. **Code Examples**: Show concrete implementation where applicable
3. **Specificity**: Avoid vague language; be precise

**Good Example** (ADR-0035):
```markdown
## Decision

Implement the Unit of Work pattern via a **SaveSession class that acts as
a context manager**.

```python
# Async usage (primary)
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = await session.commit_async()

# Sync usage (wrapper)
with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = session.commit()
```

The SaveSession:
- Enters via `__aenter__` / `__enter__` (returns session for use)
- Tracks entities explicitly via `session.track(entity)`
- Commits changes via `session.commit_async()` / `session.commit()`
- Exits via `__aexit__` / `__exit__` (marks session closed)
```

**What to Avoid**:
- Explaining why instead of what (that belongs in Rationale)
- Multiple competing options (pick one)
- Ambiguous statements like "we'll probably use X"

---

### Rationale (15 points)

**Purpose**: Explain WHY this decision over alternatives. Address key trade-offs.

**What to Include**:
1. **Primary Justification**: Why is this the right choice?
2. **Trade-offs**: What did we gain vs. what did we sacrifice?
3. **Context-Specific Factors**: What made this fit our situation?

**Structure Options**:
- Numbered list of reasons (see ADR-0035)
- Comparison tables (see ADR-0130)
- Subsections for complex rationale

**Good Example** (ADR-0035):
```markdown
## Rationale

### Why Unit of Work Pattern

1. **Familiar Pattern**: Mirrors SQLAlchemy, Django ORM, and Entity Framework -
   developers understand the semantics immediately
2. **Explicit Scope**: Context manager provides clear "this is where batched
   operations happen" boundary
3. **State Isolation**: Each session tracks its own entities, preventing
   cross-session confusion
4. **Resource Cleanup**: Context manager guarantees cleanup even on exceptions
5. **Composable**: Multiple sessions can exist (though we don't encourage
   concurrent access to same entities)
```

**Table Example** (ADR-0130):
```markdown
### Why Builder Level (Not Client Level)?

| Factor | Client Level | Builder Level |
|--------|-------------|---------------|
| **PRD Compliance** | Violates constraint | Compliant |
| **Change Scope** | Global (all list_async() callers) | Local (DataFrame path only) |
| **Opt_fields Control** | Unknown which fields to cache | Builder knows exact requirements |
```

**What to Avoid**:
- Restating the decision without explaining why
- Ignoring trade-offs (be honest about costs)
- Vague statements like "seems better"

---

### Alternatives Considered (20 points)

**Purpose**: Show that multiple approaches were genuinely evaluated, not just strawmen.

**Minimum**: 2 alternatives (excluding the chosen decision)
**Recommended**: 3-4 alternatives for complex decisions

**Required Structure for EACH Alternative**:
```markdown
### {Alternative Name}

- **Description**: {What this option entails}
- **Pros**: {Benefits}
- **Cons**: {Drawbacks}
- **Why not chosen**: {Specific reason for rejection}
```

**Good Example** (ADR-0035):
```markdown
### Alternative 1: Repository Pattern with Automatic Tracking

- **Description**: All entities fetched through repository are automatically tracked
- **Pros**: More "magical", less boilerplate
- **Cons**: Hidden behavior, performance surprises, requires model modification
- **Why not chosen**: Violates explicit tracking decision in PRD; would require
  model changes
```

**Quality Criteria**:
- **Genuine Alternatives**: Real options that could work, not obviously bad choices
- **Honest Evaluation**: Acknowledge pros even for rejected alternatives
- **Specific Rejection**: Explain exactly why not chosen (not just "worse")

**What to Avoid**:
- Strawman alternatives designed to make chosen option look good
- Missing "Why not chosen" explanation
- Alternatives missing description or pros/cons

---

### Consequences (10 points)

**Purpose**: Honestly assess the implications of the decision.

**Required Structure**:
```markdown
## Consequences

### Positive
- {good outcome 1}
- {good outcome 2}

### Negative
- {cost, risk, or limitation 1}
- {cost, risk, or limitation 2}

### Neutral
- {other effect 1}
- {other effect 2}
```

**Requirements**:
1. **Positive**: List benefits and good outcomes
2. **Negative**: Honestly acknowledge costs, risks, limitations (required!)
3. **Neutral**: Other effects that are neither good nor bad

**Good Example** (ADR-0130):
```markdown
### Negative

1. **Not Universal**: Only DataFrame fetch path benefits; other list_async()
   callers do not
2. **Opt_fields Coupling**: Cached tasks must include _BASE_OPT_FIELDS to be useful
3. **Population Latency**: Adds ~50-100ms to cold fetch (batch write overhead)
```

**What to Avoid**:
- Omitting negative consequences (dishonesty)
- Repeating rationale instead of stating implications
- Vague statements like "might cause issues"

---

### Compliance (5 points)

**Purpose**: Specify HOW the decision will be enforced.

**What to Include**:
- Code review guidelines
- Automated checks (linting, tests, CI)
- Documentation requirements
- Architectural tests
- Code location references

**Good Example** (ADR-0035):
```markdown
## Compliance

How do we ensure this decision is followed?

1. **API Design**: SaveSession is the only public entry point for batched saves
2. **Documentation**: Examples show context manager usage exclusively
3. **Type Hints**: Methods return SaveSession enabling IDE guidance
4. **Linting**: Could add custom lint rule for SaveSession usage outside
   context manager
5. **Tests**: All tests use context manager pattern
```

**Advanced Example** (ADR-0130):
```markdown
### Code Location

```python
# /src/autom8_asana/dataframes/builders/project.py
# build_with_parallel_fetch_async(), after line 369

# Per ADR-0130: Cache population occurs at builder level
await task_cache_coordinator.populate_tasks_async(fetched_tasks)
```

### Test Coverage

```python
# Required tests per ADR-0130
def test_cache_populated_after_fetch(self):
    """Verify tasks are cached after fetch_all()."""
```
```

**What to Avoid**:
- Generic "code review will catch it" without specifics
- No enforcement mechanisms
- Omitting this section entirely

---

## Formatting Standards

### Metadata Format

**Correct** (bullet list):
```markdown
## Metadata
- **Status**: Accepted
- **Author**: Architect
- **Date**: 2025-12-10
```

**Incorrect** (table - convert to bullet list):
```markdown
| Field | Value |
|-------|-------|
| Status | Accepted |
```

### Alternatives Structure

**Correct** (subsections with all fields):
```markdown
### Alternative 1: Repository Pattern

- **Description**: All entities fetched through repository are automatically tracked
- **Pros**: More "magical", less boilerplate
- **Cons**: Hidden behavior, performance surprises
- **Why not chosen**: Violates explicit tracking decision in PRD
```

**Incorrect** (missing structure):
```markdown
We considered a repository pattern but it seemed too magical.
```

### Consequences Structure

**Correct** (headings with bullets):
```markdown
## Consequences

### Positive
- Familiar pattern for Python developers
- Clear scope boundaries

### Negative
- Additional API surface to learn
- Requires explicit track() calls
```

**Incorrect** (flat list):
```markdown
## Consequences
- Good: familiar pattern
- Bad: more API surface
```

### Code Examples

**Requirements**:
- Use proper markdown code fences with language hint
- Include necessary imports (or note them as omitted)
- Show complete, runnable examples
- Add comments for clarity

**Good**:
```markdown
```python
# Async usage (primary)
async with SaveSession(client) as session:
    session.track(task)
    task.name = "Updated"
    result = await session.commit_async()
```
```

**Bad**:
```markdown
```
SaveSession(client)
task.name = "Updated"
session.commit()
```
```

### Tables

**When to Use**:
- Comparison of options (see Rationale in ADR-0130)
- Forces at play with multiple dimensions (see Context in ADR-0130)
- Constraint matrices

**Format**:
```markdown
| Factor | Option A | Option B |
|--------|----------|----------|
| **Performance** | Fast | Slow |
| **Complexity** | High | Low |
```

**Requirements**:
- Header row with descriptive column names
- Alignment for readability (pipes line up)
- Bold key terms in first column

---

## Naming Convention

**Format**: `ADR-{NNNN}-{kebab-case-title}.md`

**Rules**:
1. **Number**: Four digits with leading zeros (0001, 0035, 0145)
2. **Separator**: Single hyphen between number and title
3. **Title**: Lowercase, words separated by hyphens (kebab-case)
4. **Extension**: `.md`

**Examples**:
- `ADR-0001-protocol-extensibility.md`
- `ADR-0035-unit-of-work-pattern.md`
- `ADR-0130-cache-population-location.md`

**Next Available Number**: ADR-0145

**Non-Standard**: `ADR-SDK-005` exists but should not be replicated. Use numeric sequence.

---

## Quality Benchmarks

### Scoring Rubric (100 points)

| Section | Points | Criteria |
|---------|--------|----------|
| Title | 5 | Format correct? Specific and action-oriented? |
| Metadata | 10 | All 5 fields present? |
| Context | 20 | Problem clear? Forces listed? Situation explained? |
| Decision | 15 | Unambiguous? Code examples? |
| Rationale | 15 | Explains WHY? Addresses trade-offs? |
| Alternatives | 20 | 2+ alternatives? All 4 fields per alternative? |
| Consequences | 10 | Positive/Negative/Neutral all present? Honest? |
| Compliance | 5 | Enforcement mechanisms specified? |

### Quality Tiers

- **90-100 points**: Exemplary (reference quality)
- **70-89 points**: Good (acceptable with minor issues)
- **50-69 points**: Adequate (needs improvement)
- **Below 50**: Needs work (significant gaps)

**Minimum Acceptable Score**: 70/100

### Exemplary ADRs (Reference Models)

Study these ADRs as models of quality:

1. **ADR-0001**: Protocol-Based Extensibility (Score: 98/100)
   - 5 alternatives with full structure
   - Honest consequences (acknowledges runtime error risk)
   - Actionable compliance mechanisms

2. **ADR-0035**: Unit of Work Pattern (Score: 100/100)
   - Forces clearly enumerated
   - Two-part rationale (why UoW, why context manager)
   - Balanced consequences (positive/negative/neutral)

3. **ADR-0130**: Cache Population Location (Score: 100/100)
   - Uses comparison tables effectively
   - PRD constraint tracking in context
   - Detailed compliance with code locations and tests

---

## Common Pitfalls

### 1. Solution in Search of a Problem

**Bad**:
```markdown
## Context
We should use Protocol for extensibility.

## Decision
Use Protocol for dependency injection.
```

**Why**: No explanation of WHY this decision was needed. What problem does it solve?

**Fix**: Explain the situation, forces, and problem that triggered the decision.

---

### 2. Strawman Alternatives

**Bad**:
```markdown
### Alternative 1: Do Nothing
- **Pros**: No work required
- **Cons**: Problem persists
- **Why not chosen**: Obviously won't work
```

**Why**: Not a genuine alternative. Makes chosen option look good without real consideration.

**Fix**: Present alternatives that could realistically work, then explain specific trade-offs.

---

### 3. Missing Negative Consequences

**Bad**:
```markdown
## Consequences

### Positive
- Everything is better now
- No downsides

### Negative
- None
```

**Why**: Every decision has trade-offs. Omitting negatives signals incomplete analysis.

**Fix**: Honestly acknowledge costs, limitations, and risks.

---

### 4. Vague Rationale

**Bad**:
```markdown
## Rationale
This approach seemed like the best option because it's better.
```

**Why**: Doesn't explain WHY it's better or what trade-offs were considered.

**Fix**: Provide specific reasons tied to forces in Context section.

---

### 5. Missing "Why Not Chosen"

**Bad**:
```markdown
### Alternative 1: Repository Pattern
- **Description**: Track entities automatically
- **Pros**: Less boilerplate
- **Cons**: Hidden behavior
```

**Why**: Incomplete. Reader doesn't know WHY this was rejected.

**Fix**: Add "Why not chosen" with specific rejection rationale.

---

### 6. Incomplete Context

**Bad**:
```markdown
## Context
We need to cache things.
```

**Why**: No explanation of situation, forces, or specific problem.

**Fix**: Explain current state, constraints in tension, and triggering problem.

---

### 7. No Compliance Mechanisms

**Bad**:
```markdown
## Compliance
Developers should follow this pattern.
```

**Why**: No actionable enforcement. How will we ensure compliance?

**Fix**: Specify code review guidelines, tests, linting rules, or documentation.

---

## Examples by Type

### Positive Decision (Adopting a Pattern)

See: ADR-0035 (Unit of Work Pattern)
- Clear statement of what's adopted
- Multiple alternatives evaluated
- Honest about learning curve (negative consequence)

### Negative Decision (Rejecting an Approach)

See: ADR-0092 (CRUD Base Class Evaluation)
- States "DO NOT implement"
- Analysis section shows evaluation process
- Alternatives include "current pattern" as chosen option

### Supersession (Evolving a Decision)

See supersession chain documentation in INDEX.md:
- ADR-0098 (Superseded) links to ADR-0101 (Current)
- Old ADR explains what changed
- New ADR references old for context

---

## Process

### Creating a New ADR

1. **Check numbering**: Next available is ADR-0145
2. **Copy template**: `.claude/skills/documentation/templates/adr.md`
3. **Fill all sections**: Don't skip Compliance or Consequences
4. **Add code examples**: Make decision concrete
5. **Self-review**: Use scoring rubric
6. **Update INDEX.md**: Add to thematic and numeric sections

### Reviewing an ADR

Use the checklist in `.claude/skills/documentation/templates/adr-checklist.md`:
- Verify template compliance
- Check alternatives are genuine (not strawmen)
- Confirm consequences include negatives
- Validate cross-references

### Updating an Existing ADR

**When to Update**:
- Status change (Proposed → Accepted)
- Supersession (link to new ADR)
- Related docs added

**What NOT to Change**:
- Original decision (create new ADR instead)
- Historical context

**Process**:
1. Update Status field
2. Add "Superseded by" link if applicable
3. Update Related field if new docs added
4. Update INDEX.md if status changed

---

## Cross-References

- **Template**: `.claude/skills/documentation/templates/adr.md`
- **Contribution Checklist**: `.claude/skills/documentation/templates/adr-checklist.md`
- **Thematic Index**: `/docs/decisions/INDEX.md`
- **Audit Report**: `/docs/audits/AUDIT-adr-quality-standardization.md`

---

## Questions?

For questions about ADR style or standards, reference:
- This style guide for format and structure
- Exemplary ADRs (0001, 0035, 0130) for examples
- Audit report for quality criteria
- Contribution checklist for review process
