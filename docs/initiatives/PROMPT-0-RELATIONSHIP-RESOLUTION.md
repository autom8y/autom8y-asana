# Orchestrator Initialization: Cross-Holder Relationship Resolution

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources, async-first, batch operations
  - Activates when: Working with SDK implementation, Asana API, business models

- **`autom8-asana-business-relationships`** - Holder patterns, lazy loading, bidirectional navigation
  - Activates when: Designing hierarchy traversal, cache management, parent/child relationships

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
  - Activates when: Creating/reviewing PRD, TDD, ADR, or Test Plan

- **`standards`** - Tech stack decisions, code conventions, repository structure
  - Activates when: Writing code, choosing patterns, organizing files

- **`10x-workflow`** - Agent coordination, session protocol, quality gates
  - Activates when: Planning phases, coordinating handoffs, checking quality criteria

**How Skills Work**: Skills load automatically based on your current task. When you need SDK patterns, the `autom8-asana-domain` skill activates. When you need hierarchy navigation patterns, `autom8-asana-business-relationships` activates.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, algorithm design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, edge case discovery |

## The Mission: Enable Cross-Holder Relationship Resolution

Enable the SDK to resolve relationships that span across holders (e.g., finding which Unit and Offer an AssetEdit belongs to) without requiring users to implement domain-specific lookup logic.

### Why This Initiative?

- **Domain logic encapsulation**: Resolution rules (dependent tasks, field mapping, explicit IDs) belong in the SDK, not in every consumer
- **Consistency**: All consumers resolve relationships the same way
- **Transparency**: Callers can see which resolution strategy succeeded
- **Extensibility**: Pattern can be reused for other process types

### Current State

**What Works Well (Out of Scope)**:
- Hierarchical "fast-paths" work: `offer.unit`, `unit.business`, `contact.business`
- Holders contain their children; navigation within holders is solved
- Hydration initiative (if completed) provides upward/downward traversal

**The Gap**:
- AssetEdit is not a typed entity (plain Task under AssetEditHolder)
- Resolving "which Unit does this AssetEdit belong to?" requires domain logic
- Multiple resolution strategies exist with priority ordering:
  1. Dependent tasks (process tasks have dependents pointing to Unit)
  2. Custom field mapping (vertical field matches)
  3. Explicit offer_id field
- Users currently must implement this logic themselves

**Available Infrastructure**:
- CustomFieldAccessor for reading typed fields
- Task.dependents (if available - Discovery to confirm)
- Existing entity types (Unit, Offer, Business) as resolution targets
- Holder patterns for entity containment

### Target State

From an AssetEdit (or similar process entity), the SDK can:
1. **Resolve to Unit** - Find the Unit this process relates to
2. **Resolve to Offer** - Find the Offer this process relates to (via Unit or directly)
3. **Report strategy used** - Tell the caller which resolution path succeeded
4. **Handle ambiguity** - Clear behavior when multiple matches are found

### Key Constraints

- **Async-first**: Resolution involves API calls; async is appropriate
- **Non-prescriptive**: Discovery should validate whether architect's suggested approach is correct
- **Minimal API calls**: Resolution should not be excessively expensive
- **Clear error handling**: Ambiguity and failures should be explicit, not silent
- **Backward compatibility**: Existing code should continue working

### Requirements Summary (Draft)

| Requirement | Priority | Status |
|-------------|----------|--------|
| Resolve AssetEdit to Unit | Must (if validated) | Discovery to validate |
| Resolve AssetEdit to Offer | Must (if validated) | Discovery to validate |
| Strategy transparency | Should | Architecture to design |
| Ambiguity handling | Must | Architecture to design |
| Batch resolution | Could | Defer to future phase |
| AssetEdit entity typing | TBD | Discovery to assess if prerequisite |

### Success Criteria (Draft)

1. Resolution capability exists and works for AssetEdit use case
2. Strategy used is visible to caller
3. Ambiguity behavior is defined and consistent
4. Performance is acceptable for typical use cases
5. Pattern is generalizable to other process types (if needed)
6. Existing tests continue passing

**Note**: These criteria are drafts. Discovery phase should validate and refine.

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Use case validation, infrastructure audit, Go/No-Go refinement |
| **2: Requirements** | Requirements Analyst | PRD-RESOLUTION with acceptance criteria (if Discovery validates) |
| **3: Architecture** | Architect | TDD-RESOLUTION + ADRs for strategy pattern, ambiguity handling |
| **4: Implementation P1** | Principal Engineer | Core resolution framework (if typed entity needed, that first) |
| **5: Implementation P2** | Principal Engineer | Strategy implementations, SaveSession integration |
| **6: Validation** | QA/Adversary | Validation report, edge cases, ambiguity scenarios |

**Note**: Session count may change based on Discovery findings. If scope is smaller than expected, sessions can be combined.

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

## Discovery Phase: The Critical Gate

This initiative has a **CONDITIONAL GO** from Prompt -1. Discovery must validate before proceeding.

### Discovery Goals

The **Requirements Analyst** must answer:

| Question | Why It Matters |
|----------|----------------|
| **How often is cross-holder resolution needed?** | Justifies investment |
| **What TasksClient capabilities exist for dependents?** | Affects strategy feasibility |
| **Is AssetEdit typing a prerequisite?** | Affects phasing |
| **What resolution strategies are actually needed?** | Confirms or refutes architect suggestions |
| **What are the edge cases for ambiguity?** | Informs requirements |

### Infrastructure to Audit

| Area | Questions to Answer |
|------|---------------------|
| `src/autom8_asana/clients/tasks.py` | Does `dependents_async()` exist? What methods are available? |
| `src/autom8_asana/models/business/` | Is AssetEdit typed? What holder contains it? |
| AssetEditHolder implementation | How are AssetEdits currently structured? |
| Custom field accessor | Can we read offer_id, vertical fields reliably? |

### Use Cases to Validate

| Scenario | Questions |
|----------|-----------|
| Processing AssetEdits from a webhook | How common? What resolution is needed? |
| Generating Unit-level reports | Does this require AssetEdit -> Unit resolution? |
| Workflow automation | What relationships need resolving? |

### Discovery Deliverable

A document (DISCOVERY-RESOLUTION-001.md) with:
- Use case frequency assessment
- Infrastructure capability summary
- Recommended scope (confirm, reduce, or defer initiative)
- Blocking dependencies identified
- Go/No-Go recommendation with rationale

## Open Questions Requiring Resolution

### Questions for Discovery Phase

1. **How frequently is cross-holder resolution needed?** - Validate the problem is worth solving
2. **What TasksClient methods exist for dependents?** - DEPENDENT_TASKS strategy feasibility
3. **Is AssetEdit currently typed?** - May need typing first
4. **What custom fields exist for resolution?** - CUSTOM_FIELD_MAPPING strategy feasibility
5. **What ambiguity scenarios exist in practice?** - Informs handling requirements

### Questions for Architecture Phase (if Discovery validates)

6. **Where should resolution API live?** - Instance method? Standalone resolver? SaveSession?
7. **How should strategy priority work?** - Fixed order? Configurable? Per-call?
8. **What should ambiguity return?** - Error? All matches? First match? Configurable?
9. **Should resolution be cached?** - Different semantics than hierarchical cache
10. **How to prevent circular resolution?** - If A resolves via B which resolves via A

## Prompt -1 Reference

This initiative was validated (conditionally) in [PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION.md](./PROMPT-MINUS-1-RELATIONSHIP-RESOLUTION.md).

**Key findings from Prompt -1**:
- Problem appears valid but needs Discovery confirmation
- Multiple resolution strategies identified by architect
- AssetEdit typing status unknown - may be prerequisite
- TasksClient capabilities need audit
- Conditional GO with Discovery as validation gate

## Your First Task

Confirm understanding by:

1. Summarizing the relationship resolution initiative goal in 2-3 sentences
2. Noting that this is a **CONDITIONAL GO** - Discovery must validate
3. Listing the key Discovery questions that determine whether to proceed
4. Identifying what must be audited in the codebase
5. Confirming the handoff criteria from Discovery to Requirements

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery (Validation Gate)

```markdown
Begin Session 1: Cross-Holder Resolution Discovery

Work with the @requirements-analyst agent to validate this initiative and audit infrastructure.

**Context**: This is a CONDITIONAL GO from Prompt -1. Discovery determines whether to proceed.

**Goals:**
1. Validate how frequently cross-holder resolution is actually needed
2. Audit TasksClient for dependents-related methods
3. Assess whether AssetEdit is typed or needs typing first
4. Identify what resolution strategies are feasible with current infrastructure
5. Surface any additional blockers or dependencies
6. Recommend Go/No-Go/Descope based on findings

**Codebase to Audit:**
- `src/autom8_asana/clients/tasks.py` - Available methods, especially dependents
- `src/autom8_asana/models/business/` - AssetEdit typing status, holder structure
- `src/autom8_asana/models/custom_field_accessor.py` - Field access capabilities
- Existing integration code (if any) - Current resolution patterns

**External Assessment:**
- Asana API documentation for dependents endpoint
- Existing use cases that would benefit from resolution

**Deliverable:**
A discovery document (DISCOVERY-RESOLUTION-001.md) with:
- Use case frequency assessment
- Infrastructure capability summary
- Feasibility of each proposed resolution strategy
- Recommended scope (proceed, reduce, or defer)
- Go/No-Go recommendation with clear rationale

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements (If Discovery Validates)

```markdown
Begin Session 2: Resolution Requirements Definition

Work with the @requirements-analyst agent to create PRD-RESOLUTION.

**Prerequisites:**
- Session 1 discovery document complete
- Discovery recommended GO or PROCEED WITH REDUCED SCOPE

**Goals:**
1. Define functional requirements for resolution capability
2. Define which entity types support resolution (AssetEdit confirmed, others TBD)
3. Define resolution strategies in scope
4. Define ambiguity handling requirements
5. Define API surface requirements
6. Define acceptance criteria for each requirement

**Key Questions to Address:**
- What resolution scenarios are in scope for this initiative?
- What behavior is expected for ambiguous matches?
- What should happen on resolution failure?
- What caller controls are needed (if any)?

**PRD Organization:**
- FR-RESOLVE-*: Core resolution requirements
- FR-STRATEGY-*: Strategy-specific requirements
- FR-AMBIG-*: Ambiguity handling requirements
- FR-API-*: API surface requirements
- NFR-*: Performance, reliability requirements

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture (After Requirements)

```markdown
Begin Session 3: Resolution Architecture Design

Work with the @architect agent to create TDD-RESOLUTION and foundational ADRs.

**Prerequisites:**
- PRD-RESOLUTION approved

**Goals:**
1. Design resolution framework pattern
2. Design strategy definition and registration
3. Design priority ordering mechanism
4. Design ambiguity handling approach
5. Design API surface (method signatures, return types)
6. Assess caching strategy (if applicable)
7. Create ADRs for key decisions

**Potential ADRs:**
- ADR-XXXX: Relationship Resolution Strategy Pattern
- ADR-XXXX: Resolution Ambiguity Handling
- ADR-XXXX: AssetEdit Entity Typing (if needed)
- (Others as needed based on decisions)

**Considerations from Architect Analysis:**
- Strategy enum pattern (DEPENDENT_TASKS, CUSTOM_FIELD_MAPPING, EXPLICIT_OFFER_ID, AUTO)
- Isolated, testable strategies
- Transparency about which strategy succeeded
- Different cache semantics than hierarchical navigation

Create the plan first. I'll review before you execute.
```

### Sessions 4-5: Implementation

```markdown
Begin Session {N}: Implementation Phase {M}

Work with the @principal-engineer agent to implement resolution.

**Prerequisites:**
- PRD-RESOLUTION approved
- TDD-RESOLUTION approved
- ADRs documented

Phase-specific scope defined in TDD-RESOLUTION.

Create the plan first. I'll review before you execute.
```

### Session 6: Validation

```markdown
Begin Session 6: Resolution Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation phases complete
- All tests passing

**Goals:**

**Part 1: Functional Validation**
- Verify resolution works for each supported entity type
- Verify each strategy works in isolation
- Verify AUTO mode tries strategies in correct order
- Verify result includes which strategy succeeded

**Part 2: Ambiguity Testing**
- No matches found - expected behavior
- Single match - happy path
- Multiple matches - ambiguity handling
- Strategy conflicts - priority ordering

**Part 3: Edge Cases**
- Missing required fields for strategy
- API failures during resolution
- Circular resolution attempts (if possible)
- Resolution of already-resolved entity

**Part 4: Integration Validation**
- SaveSession integration (if applicable)
- Existing tests still pass
- No regressions in hierarchical navigation

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, the Discovery phase should gather:

**Resolution Infrastructure:**
- [ ] TasksClient methods for dependents
- [ ] AssetEdit entity typing status
- [ ] AssetEditHolder structure
- [ ] Custom field accessor capabilities

**Use Case Assessment:**
- [ ] Frequency of cross-holder resolution need
- [ ] Current workarounds or manual resolution code
- [ ] Priority of resolution scenarios

**Strategy Feasibility:**
- [ ] DEPENDENT_TASKS - Can we fetch task dependents?
- [ ] CUSTOM_FIELD_MAPPING - What fields are available?
- [ ] EXPLICIT_OFFER_ID - Does this field exist on relevant tasks?

**Related Documentation:**
- [ ] Hydration initiative artifacts (prior art)
- [ ] Existing relationship pattern documentation
- [ ] Asana API documentation for relevant endpoints

---

## Key Difference from Hydration Initiative

The Hydration initiative focused on **hierarchical traversal** - navigating up and down the holder tree. This initiative focuses on **cross-holder relationships** - finding related entities that are not in a direct parent/child relationship.

| Hydration | Relationship Resolution |
|-----------|------------------------|
| Contact -> Business (upward) | AssetEdit -> Unit (cross-holder) |
| Business -> Units (downward) | Process -> Offer (cross-holder) |
| Follows containment hierarchy | Requires domain-specific logic |
| Cache-friendly (stable relationships) | May need different cache semantics |

This distinction is important: the existing hierarchical navigation (including hydration) does not solve this problem.

---

*This Prompt 0 initializes an initiative with CONDITIONAL GO status. Session 1 (Discovery) is the validation gate that determines whether to proceed with full implementation.*
