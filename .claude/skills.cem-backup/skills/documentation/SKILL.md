---
name: documentation
description: "PRD, TDD, ADR, and Test Plan templates with artifact protocols. Use when: writing requirements documents, creating technical designs, recording architecture decisions, planning tests, understanding artifact formats. Triggers: PRD, TDD, ADR, test plan, documentation template, artifact format, requirements document, technical design, architecture decision record."
---

# Documentation Standards & Templates

> **Status**: Complete (Session 2)

## Core Principles

### Single Source of Truth
Each piece of knowledge has exactly one canonical location. Reference, don't duplicate. If information exists elsewhere, link to it.

### Document Decisions, Not Just Outcomes
Capture the "why" alongside the "what." Future team members (and future you) need context to understand, maintain, and evolve decisions.

### DRY for Documentation
Before creating a new document:
1. Check if a relevant document already exists
2. If yes: reference it, extend it, or propose amendments
3. If no: create it in the canonical location with proper indexing

### Living Documents
Documentation is never "done." Review and refactor during development. Update when requirements change. Deprecate when obsolete. Version significant changes.

---

## Artifact Types & When to Use

### PRD - Product Requirements Document

**Owner**: Requirements Analyst | **Location**: `/docs/requirements/PRD-{feature-slug}.md`

Defines WHAT we're building and WHY, from a product/user perspective. Create when starting a new feature, formalizing user requirements, or establishing scope and success criteria.

**Template**: [templates/prd.md](templates/prd.md)

### TDD - Technical Design Document

**Owner**: Architect | **Location**: `/docs/design/TDD-{feature-slug}.md`

Defines HOW we're building it - system design, components, interfaces, data flow. Create when an approved PRD needs technical design or complex implementations require upfront planning.

**Template**: [templates/tdd.md](templates/tdd.md)

### ADR - Architecture Decision Record

**Owner**: Architect (primary), Engineer (implementation-level) | **Location**: `/docs/decisions/ADR-{NNNN}-{slug}.md`

Captures WHY a specific architectural decision was made. Create when choosing between approaches, adopting new patterns/technologies, deviating from established patterns, or making trade-offs with long-term implications.

**Template**: [templates/adr.md](templates/adr.md)

### Test Plan

**Owner**: QA/Adversary | **Location**: `/docs/testing/TP-{feature-slug}.md`

Defines HOW we validate the implementation meets requirements. Create when a feature is ready for QA validation after code complete handoff.

**Template**: [templates/test-plan.md](templates/test-plan.md)

### Prompt 0 - Initiative Kickoff

For multi-session initiatives, complex systems requiring discovery, or large migrations with significant unknowns. See the **initiative-scoping** skill for Prompt -1 and Prompt 0 templates.

---

## Quality Gates Summary

**PRD**: Problem clear, scope defined, requirements testable, acceptance criteria present, no blocking questions

**TDD**: Traces to PRD, decisions have ADRs, interfaces defined, complexity justified, risks mitigated

**ADR**: Context explained, decision unambiguous, alternatives considered, consequences honest

**Test Plan**: Requirements traced, edge/error cases covered, performance tested, exit criteria clear

See each template file for complete quality gate checklists.

---

## Related Resources

- [Workflow & Lifecycle](workflow.md) - Pipeline flow, document lifecycle, indexing
- [Templates](templates/) - All artifact templates
- [Document Index](/docs/INDEX.md) - Registry of all project documentation
