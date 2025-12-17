# Orchestrator Initialization: Architecture Hardening - Initiative D (Resolution Framework)

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
- **`standards`** - Tech stack decisions, code conventions, repository structure
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources
- **`autom8-asana-business-fields`** - Field resolver patterns

**How Skills Work**: Skills load automatically based on your current task.

## Your Role: Orchestrator

You coordinate a 4-agent development workflow. You plan, delegate, coordinate, and verify - you do not implement directly.

## Your Specialist Agents

| Agent | Invocation | Responsibility |
|-------|------------|----------------|
| **Requirements Analyst** | `@requirements-analyst` | Requirements definition, acceptance criteria, scope boundaries |
| **Architect** | `@architect` | TDDs, ADRs, system design, trade-off analysis |
| **Principal Engineer** | `@principal-engineer` | Implementation, code quality, technical execution |
| **QA/Adversary** | `@qa-adversary` | Validation, failure mode testing, security/quality review |

---

## The Mission: Extract Resolution Logic into a Reusable Framework

This initiative addresses the **resolution coupling issue**: name-to-GID resolution logic is embedded in a 600+ line AssetEdit class, making it impossible to reuse for other entity types. Extraction enables consistent resolution across the SDK.

### Why This Initiative?

- **Reusability**: Resolution logic can't be used outside AssetEdit
- **Maintainability**: 600+ line class is hard to understand and modify
- **Consistency**: Different entity types need similar resolution patterns
- **Testability**: Resolution logic is hard to test in isolation
- **Extensibility**: New resolution types require editing monolithic class

### Issues Addressed

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 5 | Resolution coupled to AssetEdit | 600+ lines, can't reuse for other entity types | Medium |

### Current State

**AssetEdit Resolution**:
- 600+ line class handling multiple concerns
- Name-to-GID resolution embedded inline
- Custom field name resolution mixed with edit logic
- User/assignee resolution embedded
- Project/portfolio resolution embedded
- No clear separation of resolution concerns

**Problems**:
- Cannot resolve names without going through AssetEdit
- Resolution logic duplicated when needed elsewhere
- Testing requires full AssetEdit context
- Adding new resolution types requires editing large class
- Different resolution patterns for different entity types

### Target State

```
Resolution Framework:
  - Independent resolution service/registry
  - Pluggable resolvers for different entity types
  - Consistent resolution API across SDK
  - Cacheable resolution results
  - Batch resolution support

AssetEdit Simplified:
  - Delegates to resolution framework
  - Focused on edit orchestration only
  - Much smaller, focused class
```

### Key Constraints

- **Backward compatibility**: AssetEdit behavior must remain unchanged
- **Performance**: No regression in resolution performance
- **Caching**: Resolution results must be cacheable
- **Batch support**: Must support resolving multiple names efficiently
- **Type safety**: Resolvers must be type-safe

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Extract resolution into separate module | Must |
| Create resolver protocol/interface | Must |
| Implement entity-type resolvers (user, project, etc.) | Must |
| Support batch resolution | Must |
| Integrate with caching layer | Should |
| Refactor AssetEdit to use framework | Must |
| Maintain AssetEdit backward compatibility | Must |
| Document resolution framework | Must |

### Success Criteria

1. Resolution logic in dedicated module (`src/autom8_asana/resolution/`)
2. `Resolver` protocol defining standard interface
3. Entity-specific resolvers (UserResolver, ProjectResolver, etc.)
4. Batch resolution API for efficiency
5. AssetEdit refactored to <200 lines, delegates resolution
6. Zero behavioral changes to AssetEdit
7. Resolution usable from any SDK context
8. Documentation for adding custom resolvers

### Dependencies

**Depends On:**
- Initiative A (Foundation) - For logging/exception patterns
- Initiative C (Navigation) - For stable relationship patterns

**Blocks:**
- None (end of dependency chain before F)

**Can Run Parallel With:**
- Initiative E (Hydration) - Different code areas

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | AssetEdit decomposition analysis, resolution pattern inventory |
| **2: Requirements** | Requirements Analyst | PRD-HARDENING-D with acceptance criteria |
| **3: Architecture** | Architect | TDD-HARDENING-D + ADR for resolver pattern |
| **4: Implementation** | Principal Engineer | Resolution framework, resolvers, AssetEdit refactor |
| **5: Validation** | QA/Adversary | Resolution testing, AssetEdit regression testing |

---

## Workflow Protocol

For each session:

1. **PLAN**: Create detailed plan with relevant agent
2. **CLARIFY**: Surface ambiguities, get user confirmation
3. **EXECUTE**: Only after "Proceed with the plan"
4. **HANDOFF**: Summarize outputs, update `/docs/INDEX.md`

**Critical Rule**: Never execute without explicit confirmation.

---

## Discovery Phase: What Must Be Explored

Before requirements can be finalized, the **Requirements Analyst** must explore:

### AssetEdit Decomposition

| Section | Questions to Answer |
|---------|---------------------|
| Resolution code | What resolution logic exists? Line counts? |
| Edit orchestration | What's core edit logic vs resolution? |
| State management | What state does resolution require? |
| Dependencies | What does resolution depend on? |

### Resolution Pattern Analysis

| Resolution Type | Questions to Answer |
|-----------------|---------------------|
| User/assignee | How are users resolved? By name? Email? |
| Project | How are projects resolved? |
| Portfolio | How are portfolios resolved? |
| Custom field | How are custom field names resolved? |
| Section | How are sections resolved? |
| Tag | How are tags resolved? |

### Existing Patterns

| Pattern | Questions to Answer |
|---------|---------------------|
| `NameResolver` class | Does it exist? What does it do? |
| Caching | Is resolution cached? How? |
| Batch resolution | Is batch supported? How? |
| Error handling | What happens on resolution failure? |

### Reusability Assessment

| Context | Questions to Answer |
|---------|---------------------|
| Outside AssetEdit | Where else is resolution needed? |
| Business layer | How does business layer resolve names? |
| SaveSession | Does SaveSession need resolution? |
| Import/export | Do data operations need resolution? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Framework Design Questions

1. **Resolver pattern**: Protocol-based? ABC? Registry pattern?
2. **Resolver discovery**: Explicit registration? Auto-discovery? Both?
3. **Scope**: Global singleton? Per-client? Per-session?
4. **Configuration**: How to configure resolver behavior?

### API Design Questions

5. **Batch API**: `resolve_batch(names)` vs `resolve(name, batch=True)`?
6. **Return type**: GID string? NameGid object? Entity object?
7. **Ambiguity handling**: What if name matches multiple entities?
8. **Not found handling**: Raise? Return None? Return sentinel?

### Integration Questions

9. **Cache integration**: Use existing cache? Separate resolver cache?
10. **Async support**: Resolvers async? Sync? Both?
11. **AssetEdit migration**: Big-bang or incremental?

---

## Your First Task

Confirm understanding by:

1. Summarizing the Resolution Framework goal in 2-3 sentences
2. Listing the 5 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which code areas must be analyzed before PRD-HARDENING-D
5. Listing which open questions you need answered before Session 2
6. Acknowledging this initiative depends on A and C

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery

```markdown
Begin Session 1: Resolution Framework Discovery

Work with the @requirements-analyst agent to analyze AssetEdit and resolution patterns.

**Goals:**
1. Decompose AssetEdit into resolution vs orchestration concerns
2. Inventory all resolution types in AssetEdit
3. Document existing resolution patterns elsewhere
4. Identify resolution reuse opportunities
5. Assess current caching and batching

**Files to Analyze:**
- AssetEdit implementation (find location)
- `src/autom8_asana/clients/name_resolver.py` (if exists)
- Business layer resolution patterns
- Custom field resolution code

**Deliverable:**
A discovery document with:
- AssetEdit decomposition (resolution vs orchestration)
- Resolution type inventory
- Existing pattern analysis
- Reusability opportunities
- Recommended framework design

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements

```markdown
Begin Session 2: Resolution Framework Requirements

Work with the @requirements-analyst agent to create PRD-HARDENING-D.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define resolver protocol requirements
2. Define entity-specific resolver requirements
3. Define batch resolution requirements
4. Define AssetEdit refactoring requirements
5. Define acceptance criteria for each

**Key Questions to Address:**
- What resolver pattern to use?
- What resolvers are needed?
- How to handle batch resolution?
- What's the migration strategy?

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture

```markdown
Begin Session 3: Resolution Framework Architecture

Work with the @architect agent to create TDD-HARDENING-D and required ADRs.

**Prerequisites:**
- PRD-HARDENING-D approved

**Goals:**
1. Design resolver protocol
2. Design resolver registry
3. Design batch resolution API
4. Design AssetEdit refactoring approach

**Required ADRs:**
- ADR: Resolution Framework Design
- ADR: Resolver Registry Pattern

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation

```markdown
Begin Session 4: Resolution Framework Implementation

Work with the @principal-engineer agent to implement framework and refactor.

**Prerequisites:**
- PRD-HARDENING-D approved
- TDD-HARDENING-D approved
- ADRs documented

**Scope:**
1. Create resolution module structure
2. Implement Resolver protocol
3. Implement resolver registry
4. Implement entity-specific resolvers
5. Implement batch resolution
6. Refactor AssetEdit to delegate
7. Tests for all components

**Hard Constraints:**
- AssetEdit behavior unchanged
- No performance regression
- Full test coverage

Create the plan first. I'll review before you execute.
```

### Session 5: Validation

```markdown
Begin Session 5: Resolution Framework Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation complete

**Goals:**

**Part 1: Framework Validation**
- Verify resolver protocol works correctly
- Verify all entity resolvers function
- Verify batch resolution works
- Verify caching integration

**Part 2: AssetEdit Regression**
- Verify AssetEdit behavior unchanged
- Verify all existing tests pass
- Verify no performance regression

**Part 3: Reusability Validation**
- Verify resolution usable outside AssetEdit
- Verify custom resolver extension works
- Verify documentation accuracy

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Codebase:**
- [ ] AssetEdit implementation
- [ ] `src/autom8_asana/clients/name_resolver.py` (if exists)
- [ ] Business layer resolution patterns
- [ ] Custom field resolution code
- [ ] Existing cache integration

**Documentation:**
- [ ] ADR-0071 (Resolution Ambiguity Handling)
- [ ] ADR-0072 (Resolution Caching Decision)
- [ ] ADR-0073 (Batch Resolution API Design)
- [ ] Field resolver skill documentation

**Related PRDs:**
- [ ] PRD-RESOLUTION (Cross-Holder Relationship Resolution)

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Meta Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md` | Parent initiative |
| ADR-0071 | `/docs/decisions/ADR-0071-resolution-ambiguity-handling.md` | Ambiguity handling |
| ADR-0072 | `/docs/decisions/ADR-0072-resolution-caching-decision.md` | Caching decision |
| ADR-0073 | `/docs/decisions/ADR-0073-batch-resolution-api-design.md` | Batch API |
| Field Resolver Skill | `.claude/skills/autom8-asana-business-fields/field-resolver.md` | Resolver patterns |
| Initiative C | `/docs/initiatives/PROMPT-0-HARDENING-C-NAVIGATION.md` | Dependency |

---

*This is Initiative D of the Architecture Hardening Sprint. It depends on Initiatives A and C. Can run in parallel with Initiative E.*
