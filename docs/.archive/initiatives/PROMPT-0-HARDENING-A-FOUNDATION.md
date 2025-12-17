# Orchestrator Initialization: Architecture Hardening - Initiative A (Foundation)

## Context & Available Skills

Read project documentation to understand context before starting.

### Progressive Context Loading

You have access to the following skills for on-demand context:

- **`documentation`** - PRD/TDD/ADR templates, workflow pipeline, quality gates
- **`standards`** - Tech stack decisions, code conventions, repository structure
- **`10x-workflow`** - Agent coordination, session protocol, quality gates
- **`prompting`** - Agent invocation patterns, workflow examples
- **`autom8-asana-domain`** - SDK patterns, SaveSession, Asana resources

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

## The Mission: Establish a Clean Foundation for SDK Architecture Hardening

This initiative addresses **6 low-severity issues** to create a clean, consistent foundation before tackling higher-risk changes. These are quick wins that improve DX, debuggability, and code hygiene.

### Why This Initiative?

- **Enables debugging**: Structured logging helps diagnose issues in subsequent initiatives
- **Improves DX**: Consistent exceptions and naming reduce developer confusion
- **API hygiene**: Clean `__all__` exports prevent accidental internal API usage
- **Operational readiness**: Observability hooks prepare SDK for production monitoring
- **Low risk**: Changes are isolated and unlikely to cause regressions

### Issues Addressed

| # | Issue | Description | Severity |
|---|-------|-------------|----------|
| 9 | Exception hierarchy inconsistent | Different attribute patterns across exceptions | Low |
| 10 | Naming inconsistencies | `get_custom_fields()` sounds like fetch, `Fields` vs `CascadingFields` | Low |
| 11 | Private functions in `__all__` | API hygiene - internal functions exposed | Low |
| 12 | Stub holders incomplete | May cause runtime errors on access | Low |
| 13 | Logging is minimal | Most modules don't use logging | Low |
| 14 | No observability hooks | No telemetry/metrics integration points | Low |

### Current State

**Exceptions**:
- Inconsistent attribute patterns (some have `message`, others `detail`, etc.)
- No common base class with standard attributes
- Stack traces sometimes missing context

**Naming**:
- `get_custom_fields()` implies API fetch, actually returns local data
- `Fields` vs `CascadingFields` distinction unclear
- Some method names violate SDK conventions

**API Surface**:
- Private helper functions (`_helper()`) in some `__all__` exports
- No clear public/private boundary in some modules

**Logging**:
- Only ~10% of modules have logging
- No consistent format or levels
- Debug information printed directly instead of logged

**Observability**:
- No hooks for metrics (request counts, latencies)
- No structured event emission
- No trace context propagation

### Target State

```
Exceptions:     Standardized hierarchy with consistent attributes
Naming:         Clear, consistent naming following conventions
API Surface:    Clean __all__ with only public functions
Logging:        Structured logging in all modules
Observability:  Hook points ready for metrics/tracing integration
```

### Key Constraints

- **Backward compatibility**: Existing exception handling code must continue to work
- **No external dependencies**: Observability hooks should not require new dependencies
- **Opt-out by default**: Logging/observability should not impact performance unless enabled
- **Documentation**: All changes must be documented in code and migration guide

### Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Standardize exception base class with common attributes | Must |
| Ensure all exceptions inherit from common base | Must |
| Audit and fix naming inconsistencies | Must |
| Remove private functions from all `__all__` exports | Must |
| Complete stub holder implementations | Must |
| Add structured logging to all modules | Should |
| Create observability hook protocol | Should |
| Document changes in migration guide | Must |
| Maintain backward compatibility | Must |

### Success Criteria

1. All exceptions inherit from a common `AsanaSDKError` base class
2. Common base has standardized attributes: `message`, `code`, `context`, `cause`
3. No private functions (leading `_`) in any `__all__` export
4. All stub holders raise meaningful `NotImplementedError` with guidance
5. Logging present in all client modules with consistent format
6. `ObservabilityProtocol` defined for optional metrics/tracing hooks
7. No breaking changes to existing exception handling code
8. Migration guide updated with any behavioral changes

---

## Session-Phased Approach

| Session | Agent | Deliverable |
|---------|-------|-------------|
| **1: Discovery** | Requirements Analyst | Exception hierarchy audit, naming audit, `__all__` audit |
| **2: Requirements** | Requirements Analyst | PRD-HARDENING-A with acceptance criteria |
| **3: Architecture** | Architect | TDD-HARDENING-A + ADRs for exception hierarchy, observability protocol |
| **4: Implementation** | Principal Engineer | Exception standardization, naming fixes, `__all__` cleanup, logging |
| **5: Validation** | QA/Adversary | Validation report, backward compatibility verification |

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

### Exception Hierarchy Analysis

| File/Area | Questions to Answer |
|-----------|---------------------|
| `src/autom8_asana/exceptions.py` | What exceptions exist? What are their attributes? |
| All client modules | How are exceptions raised? What context is included? |
| Tests | How are exceptions caught? What attributes are accessed? |
| Error handling patterns | What's the current convention? What needs standardization? |

### Naming Audit

| Area | Questions to Answer |
|------|---------------------|
| `get_*` methods | Which ones fetch vs return local data? |
| `Fields` vs `CascadingFields` | What's the distinction? Is it clear? |
| Method naming conventions | What patterns exist? What's inconsistent? |
| Class naming | Are names self-explanatory? |

### API Surface Audit

| Area | Questions to Answer |
|------|---------------------|
| All `__all__` exports | What private functions are exposed? |
| Module boundaries | What should be public vs private? |
| Import patterns | How do consumers import SDK components? |

### Logging & Observability Audit

| Area | Questions to Answer |
|------|---------------------|
| Current logging usage | Which modules log? What format? |
| Structured logging patterns | What fields should be standard? |
| Observability integration points | Where should hooks be placed? |
| Performance impact | How to make logging zero-cost when disabled? |

---

## Open Questions Requiring Resolution

Before Session 2 (Requirements) begins:

### Exception Questions

1. **Common base class name**: `AsanaSDKError` vs `AsanaError` vs `SDKError`?
2. **Attribute standardization**: What attributes should all exceptions have?
3. **Error codes**: Should we have an error code enum?
4. **Cause chaining**: How to handle exception cause/original error?

### Naming Questions

5. **`get_custom_fields()` rename**: `custom_fields` property? `local_custom_fields()`?
6. **Fields terminology**: Should we rename `Fields` to be clearer?

### Observability Questions

7. **Protocol vs ABC**: Use Protocol for observability hooks or ABC?
8. **Default implementation**: Should there be a no-op default?
9. **Metric categories**: What metrics should be hookable (requests, latency, errors)?

---

## Your First Task

Confirm understanding by:

1. Summarizing the Foundation initiative goal in 2-3 sentences
2. Listing the 5 sessions and their deliverables
3. Identifying the **Discovery Phase** as the critical first step
4. Confirming which files/areas must be analyzed before PRD-HARDENING-A
5. Listing which open questions you need answered before Session 2

**Do NOT begin Session 1 yet. Wait for my confirmation.**

---

## Session Trigger Prompts

### Session 1: Discovery

```markdown
Begin Session 1: Foundation Initiative Discovery

Work with the @requirements-analyst agent to audit the current state of exceptions, naming, API surface, and logging.

**Goals:**
1. Document all exception classes and their attributes
2. Identify naming inconsistencies (methods, classes)
3. Audit all `__all__` exports for private function leakage
4. Document current logging patterns
5. Identify observability hook placement opportunities
6. Catalog stub holders needing completion

**Files to Analyze:**
- `src/autom8_asana/exceptions.py` - Exception definitions
- `src/autom8_asana/**/__init__.py` - All `__all__` exports
- `src/autom8_asana/clients/*.py` - Logging patterns, naming
- `src/autom8_asana/models/*.py` - Holder implementations

**Deliverable:**
A discovery document with:
- Exception hierarchy diagram
- Naming inconsistency inventory
- `__all__` audit results
- Logging coverage map
- Observability hook recommendations

Create the analysis plan first. I'll review before you execute.
```

### Session 2: Requirements

```markdown
Begin Session 2: Foundation Requirements Definition

Work with the @requirements-analyst agent to create PRD-HARDENING-A.

**Prerequisites:**
- Session 1 discovery document complete

**Goals:**
1. Define exception standardization requirements
2. Define naming convention requirements
3. Define API hygiene requirements
4. Define logging requirements
5. Define observability hook requirements
6. Define acceptance criteria for each

**Key Questions to Address:**
- What attributes must all exceptions have?
- What naming patterns should be enforced?
- What logging format should be standard?
- What observability hooks are needed?

Create the plan first. I'll review before you execute.
```

### Session 3: Architecture

```markdown
Begin Session 3: Foundation Architecture Design

Work with the @architect agent to create TDD-HARDENING-A and required ADRs.

**Prerequisites:**
- PRD-HARDENING-A approved

**Goals:**
1. Design exception hierarchy
2. Design observability protocol
3. Design logging configuration
4. Document module-level changes

**Required ADRs:**
- ADR: Exception Hierarchy Standardization
- ADR: Observability Hook Protocol Design
- ADR: Logging Strategy

Create the plan first. I'll review before you execute.
```

### Session 4: Implementation

```markdown
Begin Session 4: Foundation Implementation

Work with the @principal-engineer agent to implement all Foundation changes.

**Prerequisites:**
- PRD-HARDENING-A approved
- TDD-HARDENING-A approved
- ADRs documented

**Scope:**
1. Implement standardized exception base class
2. Migrate all exceptions to new hierarchy
3. Fix all naming inconsistencies
4. Clean up all `__all__` exports
5. Complete stub holder implementations
6. Add structured logging to all modules
7. Implement observability protocol

**Hard Constraints:**
- No breaking changes to exception handling
- Logging must be zero-cost when disabled
- All changes documented

Create the plan first. I'll review before you execute.
```

### Session 5: Validation

```markdown
Begin Session 5: Foundation Validation

Work with the @qa-adversary agent to validate the implementation.

**Prerequisites:**
- All implementation complete

**Goals:**

**Part 1: Functional Validation**
- Verify all exceptions inherit from common base
- Verify common attributes present on all exceptions
- Verify no private functions in `__all__`
- Verify stub holders raise meaningful errors
- Verify logging in all modules

**Part 2: Backward Compatibility**
- Verify existing exception handling code still works
- Verify exception attribute access unchanged
- Verify no import breakages

**Part 3: Quality Validation**
- Verify logging format consistency
- Verify observability protocol documented
- Verify migration guide complete

Create the plan first. I'll review before you execute.
```

---

## Context Gathering Checklist

Before starting, gather:

**Codebase:**
- [ ] `src/autom8_asana/exceptions.py` - Current exceptions
- [ ] All `__init__.py` files - `__all__` exports
- [ ] Client modules - Logging, naming patterns
- [ ] Model modules - Holder implementations

**Documentation:**
- [ ] Existing ADRs on error handling
- [ ] Code conventions document
- [ ] SDK patterns documentation

**Tests:**
- [ ] Exception handling test patterns
- [ ] Current test coverage for exceptions

---

## Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| Meta Prompt -1 | `/docs/initiatives/PROMPT-MINUS-1-ARCHITECTURE-HARDENING.md` | Parent initiative |
| SDK Conventions | `.claude/skills/autom8-asana-domain/code-conventions.md` | Naming conventions |
| Exception Patterns | `.claude/skills/standards/code-conventions.md` | Error handling |
| Current Exceptions | `src/autom8_asana/exceptions.py` | Starting point |

---

*This is Initiative A of the Architecture Hardening Sprint. Upon completion, Initiatives B and E can proceed in parallel.*
