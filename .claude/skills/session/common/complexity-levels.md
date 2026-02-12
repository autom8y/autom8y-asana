# Complexity Levels Guide

> Detailed classification guide for initiative complexity.

## Overview

Complexity levels determine:
1. **Which agents are invoked** (Analyst only vs. Analyst → Architect)
2. **Which artifacts are produced** (PRD only vs. PRD + TDD + ADRs)
3. **Expected session duration** (hours vs. days/weeks)
4. **Whether multi-session work is expected**

## Classification Decision Tree

```
How much code will this produce?

< 200 LOC, single file?
├─ Yes → SCRIPT

< 2000 LOC, multiple files, no persistence?
├─ Yes → MODULE

APIs, data persistence, integration points?
├─ Yes → SERVICE

Multiple services, infrastructure, complex integration?
├─ Yes → PLATFORM
```

## SCRIPT

### Characteristics

- **Single file** or very few files (< 3)
- **< 200 lines of code**
- **No external dependencies** beyond standard library
- **No data persistence**
- **No API contracts**
- **Narrow, well-defined scope**

### Examples

- Add retry logic to API client
- Create CLI utility for log parsing
- Add validation function to existing module
- Write shell script for environment setup
- Fix bug in single function

### Workflow

```
/start → Requirements Analyst → PRD
  ↓
/handoff engineer → Implementation
  ↓
/wrap (optional: /handoff qa for validation)
```

**Design Phase**: SKIPPED (no TDD or ADRs)

**Typical Duration**: 1-4 hours

### Artifacts Produced

- ✓ PRD (minimal, 1-2 pages)
- ✗ TDD (skip)
- ✗ ADRs (skip)
- ✓ Code (1 file)
- ~ Tests (simple unit tests)

### When to Upgrade to MODULE

If during implementation you discover:
- Need multiple files with clear interfaces
- External dependencies required
- More than 200 LOC needed
- Data structures need careful design

**Action**: Surface to user, suggest `/handoff architect` to add design phase.

---

## MODULE

### Characteristics

- **Multiple files** with clear interfaces (3-10 files)
- **< 2000 lines of code**
- **External dependencies** (libraries, frameworks)
- **Well-defined interfaces** between components
- **No network APIs** or persistence (or minimal, file-based)
- **Testable in isolation**

### Examples

- Add authentication middleware
- Create reusable UI component library
- Implement caching layer
- Build data validation framework
- Add feature to existing service (not the whole service)

### Workflow

```
/start → Requirements Analyst → PRD
  ↓
/handoff architect → TDD + ADRs
  ↓
/handoff engineer → Implementation
  ↓
/handoff qa → Validation
  ↓
/wrap
```

**Design Phase**: REQUIRED

**Typical Duration**: 1-3 days (may park/resume)

### Artifacts Produced

- ✓ PRD (standard, 3-5 pages)
- ✓ TDD (detailed design)
- ✓ ADRs (2-5 decisions)
- ✓ Code (multiple files)
- ✓ Tests (comprehensive unit tests)

### When to Upgrade to SERVICE

If during design you discover:
- Need REST/GraphQL APIs
- Data persistence required (database)
- Multiple integration points
- Service-level concerns (auth, logging, monitoring)

**Action**: Surface to user, consider re-scoping or breaking into phases.

---

## SERVICE

### Characteristics

- **Multiple modules** with API contracts
- **Data persistence** (database, cache, queues)
- **Network APIs** (REST, GraphQL, gRPC)
- **Integration points** with other services
- **Service-level concerns** (auth, logging, monitoring, deployment)
- **Testable via integration tests**

### Examples

- Build user management service
- Create payment processing API
- Implement notification service
- Add service to microservices architecture
- Build data aggregation pipeline

### Workflow

```
/start → Requirements Analyst → PRD
  ↓
/handoff architect → TDD + ADRs (extended design)
  ↓
/handoff engineer → Implementation (multiple park/resume cycles)
  ↓
/handoff qa → Validation + Integration Tests
  ↓
/wrap
```

**Design Phase**: EXTENDED (may require architect handoff multiple times)

**Typical Duration**: 1-2 weeks (definitely multi-session)

### Artifacts Produced

- ✓ PRD (comprehensive, 5-10 pages)
- ✓ TDD (detailed, API specs, data models, deployment)
- ✓ ADRs (5-15 decisions)
- ✓ Code (service implementation)
- ✓ Tests (unit + integration + API tests)
- ✓ Test Plan (QA validation scenarios)

### When to Upgrade to PLATFORM

If during design you discover:
- Need multiple services working together
- Infrastructure changes required (networking, deployment, monitoring)
- Complex orchestration or data flows
- Affects multiple teams or systems

**Action**: Break into multiple SERVICE-level sessions, or escalate to PLATFORM.

---

## PLATFORM

### Characteristics

- **Multiple services** with complex interactions
- **Infrastructure changes** (networking, security, deployment)
- **Cross-cutting concerns** (observability, disaster recovery)
- **Multi-rite coordination**
- **Phased rollout** required
- **Too large for single session**

### Examples

- Migrate monolith to microservices
- Implement multi-region deployment
- Build developer platform (CI/CD, tooling, standards)
- Add multi-tenancy to SaaS product
- Implement zero-trust security architecture

### Workflow

```
/start → Requirements Analyst → PRD (initiative-level)
  ↓
/handoff architect → TDD (high-level architecture + phase breakdown)
  ↓
/park (session too large, break into phases)

For each phase:
  /start → MODULE or SERVICE session
  /wrap

After all phases:
  /start validation-session → Integration validation
  /wrap
```

**Design Phase**: CRITICAL (architecture decisions guide all phases)

**Typical Duration**: Weeks to months (always multi-session)

### Artifacts Produced

- ✓ PRD (comprehensive, 10-30 pages, initiative-level)
- ✓ TDD (high-level architecture, phase breakdown)
- ✓ ADRs (15-50 decisions across all phases)
- ✓ Migration Plan or Deployment Strategy
- ✓ Per-phase artifacts (MODULE/SERVICE sessions)
- ✓ Integration Test Plan

### Handling PLATFORM Complexity

**Initial Session**:
1. Create initiative-level PRD and TDD
2. Break work into MODULE/SERVICE-sized phases
3. /wrap initial planning session

**Subsequent Sessions**:
- Each phase gets its own session (MODULE or SERVICE complexity)
- Reference original PLATFORM TDD for alignment
- Final session for integration validation

---

## Complexity Re-classification

### Upgrading During Session

If complexity increases during the session:

1. **Surface to user**: "This is more complex than initially scoped"
2. **Recommend action**:
   - Invoke missing phase (e.g., /handoff architect for SCRIPT → MODULE)
   - Re-scope and break into multiple sessions (MODULE → SERVICE)
   - Park and re-plan (SERVICE → PLATFORM)

### Downgrading During Session

If complexity decreases (rare):

1. **Continue with current plan** (extra rigor doesn't hurt)
2. **Skip optional artifacts** (e.g., fewer ADRs)
3. **Note in wrap summary**: "Initially MODULE, implemented as SCRIPT"

## Complexity vs. Rite

Some rites specialize in complexity levels:

| Rite | Best For |
|------|----------|
| 10x-dev | MODULE, SERVICE (general development) |
| rnd | SCRIPT, MODULE (experimentation, prototyping) |
| sre | SERVICE, PLATFORM (infrastructure, reliability) |
| ecosystem | PLATFORM (knossos sync infrastructure) |

**Note**: Rite doesn't dictate complexity; complexity dictates which agents are invoked.

## Estimation Guidelines

### Lines of Code (LOC)

| Complexity | Typical LOC | Max LOC |
|------------|-------------|---------|
| SCRIPT | 50-150 | 200 |
| MODULE | 500-1500 | 2000 |
| SERVICE | 2000-10000 | 15000 |
| PLATFORM | 10000+ | No limit |

**Note**: LOC is a rough guide. Interface complexity matters more than line count.

### File Count

| Complexity | Typical Files | Max Files |
|------------|---------------|-----------|
| SCRIPT | 1-2 | 3 |
| MODULE | 3-8 | 10 |
| SERVICE | 10-30 | 50 |
| PLATFORM | 50+ | No limit |

### Session Count

| Complexity | Typical Sessions | Reason |
|------------|------------------|--------|
| SCRIPT | 1 | Complete in one sitting |
| MODULE | 1-2 | May park once for extended implementation |
| SERVICE | 2-5 | Multiple park/resume cycles, extended QA |
| PLATFORM | 5-20+ | Phased approach, multiple sub-sessions |

## Anti-Patterns

### Under-classifying Complexity

**Symptom**: Started as SCRIPT, now need database and API

**Problem**: Skipped design phase, rework needed

**Fix**: /handoff architect, create TDD retroactively

### Over-classifying Complexity

**Symptom**: Started as SERVICE, only wrote 100 LOC

**Problem**: Wasted time on unnecessary artifacts

**Fix**: Note in wrap summary, skip optional ADRs

### Starting PLATFORM as Single Session

**Symptom**: Initiative too broad, context overflow, confusion

**Problem**: Session scope exceeds manageable size

**Fix**: /park, break into phases, create MODULE/SERVICE sessions

## Cross-References

- [Session Context Schema](session-context-schema.md) - complexity field definition
- [Session Phases](session-phases.md) - Phase requirements per complexity
- [Start Examples](../start-ref/examples.md) - Classification examples
