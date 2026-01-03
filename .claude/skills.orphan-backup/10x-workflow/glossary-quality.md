# Glossary: Quality & Principles

> Quality concepts, anti-patterns, workflow principles

**Other Domains**: [Agents & Artifacts](glossary-agents.md) | [Process & Workflow](glossary-process.md) | [Index](glossary-index.md)

---

## Quality Concepts

### Fresh-Machine Test
**Definition**: Validation that code/documentation works on a clean environment without implicit dependencies on the author's setup.

**Application**: Examples must run, procedures must execute, from a fresh starting point.

---

### Acid Test
**Definition**: A specific, measurable validation that proves an initiative achieved its goals. Often used for documentation initiatives.

**Characteristics**:
- Concrete scenario (not abstract)
- Measurable outcome (time, success rate)
- Tests the real goal, not proxies

**Example**: "New developer completes first successful API call in under 5 minutes using only the documentation."

---

### Backward Compatibility
**Definition**: Constraint that existing interfaces, behaviors, or contracts must continue to work after changes.

**Application**: New parameters must be optional with sensible defaults. Existing method signatures must not change.

---

## Anti-Patterns

### Rubber-Stamp Approval
**Definition**: Approving artifacts without genuine validation. Passing quality gates without checking criteria.

**Impact**: Low-quality work propagates downstream, causing expensive rework.

---

### Analysis Paralysis
**Definition**: Endless scoping and planning without reaching a Go/No-Go decision.

**Mitigation**: Timebox Prompt -1, accept uncertainty, use spikes for high-risk unknowns.

---

### Premature Implementation
**Definition**: Writing code before requirements and design are understood.

**Impact**: Building the wrong thing, rework, scope creep.

---

### Documentation Theater
**Definition**: Creating documents to satisfy process rather than to enable success.

**Detection**: Documents that no one reads or references.

**Mitigation**: Every document should have a clear consumer and purpose.

---

### Footgun Framing
**Definition**: Documentation that emphasizes what NOT to do rather than what TO do.

**Impact**: Makes users feel stupid, doesn't teach the right patterns.

**Better Approach**: Lead with the correct pattern, explain why it's correct.

---

## Workflow Principles

### The 10x Principle
**Definition**: Well-structured agentic workflows can achieve 10x productivity by:
- Preventing rework through clear requirements
- Right-sizing effort to complexity
- Parallelizing where possible
- Catching issues early through quality gates

---

### Specialist Sovereignty
**Definition**: Each specialist agent has authority over their domain. The orchestrator delegates decisions within scope, not just tasks.

**Application**: Architect decides architecture, Engineer decides implementation details, QA decides test strategy.

---

### Explicit Over Implicit
**Definition**: State assumptions, boundaries, and decisions explicitly rather than relying on shared understanding.

**Application**: Define scope IN and OUT, document decisions in ADRs, surface open questions.

---

### Reference, Don't Duplicate
**Definition**: Information should exist in exactly one canonical location. Other documents should link to it.

**Application**: PRD defines requirements (reference from TDD). TDD defines design (reference from implementation). ADR explains decision (reference from everywhere).
