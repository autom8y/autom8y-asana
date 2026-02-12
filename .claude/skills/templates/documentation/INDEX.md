---
name: documentation
description: "Doc standards routing hub. Use when: choosing which documentation template to use, understanding doc standards, routing to domain-specific doc skills. Triggers: documentation, doc standards, which template, documentation routing."
---

# Documentation Standards & Templates

Quick routing hub for documentation templates and standards. Category-specific skills contain the actual templates.

## When to Use This Skill

1. **Choosing which template skill**: Consult Quick Reference table
2. **Understanding doc standards**: Read Core Principles
3. **Checking workflow**: See [Workflow & Lifecycle](workflow.md)
4. **Getting actual templates**: Go to the domain skill (e.g., `doc-artifacts`)

Do NOT use this skill to get templates directly—it's a routing hub.

## Quick Reference

| Need | Skill | Templates |
|------|-------|-----------|
| Development artifacts | `doc-artifacts` | PRD, TDD, ADR, Test Plan |
| Docs rite workflows | `doc-reviews` | Audit, Info Arch, Content Brief, Review |
| Ecosystem/hygiene | `doc-ecosystem` | Gap Analysis, Migration, Compatibility, Smells |
| SRE/Debt/Analytics | `doc-sre` | Observability, Postmortem, Chaos, Debt, Tracking |
| Strategy workflows | `doc-strategy` | Strategic Roadmap, Competitive Intel, Market Analysis, Financial Model |
| Security workflows | `doc-security` | Threat Model, Compliance Requirements, Pentest Report, Security Signoff |
| R&D workflows | `doc-rnd` | Tech Assessment, Integration Map, Prototype Doc, Moonshot Plan |
| Intelligence workflows | `doc-intelligence` | Research Findings, Experiment Design, Insights Report |

## Template Ownership

This skill **routes** to template skills—it does not contain templates itself.

For actual templates, use the appropriate domain skill:
- Development artifacts (PRD, TDD, ADR, Test Plan) → `doc-artifacts`
- Other domains → see Quick Reference table above

## Core Principles

- **Single Source of Truth**: Each knowledge piece has one canonical location. Reference, don't duplicate.
- **Document Decisions**: Capture "why" alongside "what." Future readers need context.
- **DRY**: Before creating, check if it exists. Reference, extend, or amend—don't duplicate.
- **Living Documents**: Review, update, deprecate. Version significant changes.

## Anti-Patterns

- Creating new doc when existing doc needs update
- Duplicating content between skills or docs
- Templates without clear ownership boundary
- Quality gates using subjective language ("clear", "appropriate")

## Quality Gates Summary

**PRD**: Problem statement names specific user and pain point, In/Out scope lists are exhaustive, each requirement has measurable acceptance criteria, no blocking questions

**TDD**: Traces to PRD, decisions have ADRs, interfaces defined, complexity justified, risks mitigated

**ADR**: Context explained, decision unambiguous, alternatives considered, consequences honest

**Test Plan**: Requirements traced, edge/error cases covered, performance tested, exit criteria clear

See category-specific skills for complete quality gate checklists.

## Related Resources

- [Workflow & Lifecycle](workflow.md) - Pipeline flow, document lifecycle, indexing
- [Document Index](/docs/INDEX.md) - Registry of all project documentation
