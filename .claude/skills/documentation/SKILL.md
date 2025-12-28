---
name: documentation
description: "Documentation standards and template routing. Points to category-specific skills for actual templates."
---

# Documentation Standards & Templates

Quick routing hub for documentation templates and standards. Category-specific skills contain the actual templates.

## Quick Reference

| Need | Skill | Templates |
|------|-------|-----------|
| Development artifacts | `doc-artifacts` | PRD, TDD, ADR, Test Plan |
| Doc team workflows | `doc-reviews` | Audit, Info Arch, Content Brief, Review |
| Ecosystem/hygiene | `doc-ecosystem` | Gap Analysis, Migration, Compatibility, Smells |
| SRE/Debt/Analytics | `doc-sre` | Observability, Postmortem, Chaos, Debt, Tracking |
| Strategy workflows | `doc-strategy` | Strategic Roadmap, Competitive Intel, Market Analysis, Financial Model |
| Security workflows | `doc-security` | Threat Model, Compliance Requirements, Pentest Report, Security Signoff |
| R&D workflows | `doc-rnd` | Tech Assessment, Integration Map, Prototype Doc, Moonshot Plan |
| Intelligence workflows | `doc-intelligence` | Research Findings, Experiment Design, Insights Report |

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

## Artifact Types Overview

### Development Artifacts (`doc-artifacts`)
Core development workflow documentation:
- **PRD** - Product Requirements Document (WHAT and WHY)
- **TDD** - Technical Design Document (HOW)
- **ADR** - Architecture Decision Record (WHY this way)
- **Test Plan** - Validation strategy (HOW we verify)

### Documentation Team Templates (`doc-reviews`)
Documentation quality and governance:
- **Documentation Audit Report** - Health assessment of existing docs
- **Information Architecture Specification** - Documentation structure design
- **Content Brief** - Instructions for new documentation
- **Documentation Review Report** - Quality validation reports

### Ecosystem & Hygiene Templates (`doc-ecosystem`)
Project health and maintenance:
- **Gap Analysis** - Identifying missing or broken functionality
- **Migration Plan** - Documentation reorganization plans
- **Compatibility Report** - Cross-version testing results
- **Smell Report** - Code quality and cleanup opportunities

### SRE, Debt & Analytics Templates (`doc-sre`)
Operations, reliability, and metrics:
- **Observability Report** - Monitoring and instrumentation status
- **Postmortem** - Incident analysis and lessons
- **Chaos Experiment** - Resilience testing plans
- **Debt Ledger** - Technical debt inventory
- **Risk Matrix** - Debt prioritization
- **Sprint Debt Packages** - Remediation planning
- **Tracking Plan** - Analytics instrumentation specs

### Strategy Team Templates (`doc-strategy`)
Strategic planning and business analysis:
- **Strategic Roadmap** - Prioritized initiatives with OKRs
- **Competitive Intel** - Competitor analysis and positioning
- **Market Analysis** - TAM/SAM/SOM and segment profiles
- **Financial Model** - Unit economics and scenario analysis

### Security Team Templates (`doc-security`)
Security assessment and compliance:
- **Threat Model** - STRIDE/DREAD attack surface analysis
- **Compliance Requirements** - Regulatory control mapping
- **Pentest Report** - Vulnerability findings and remediation
- **Security Signoff** - Code review security approval

### R&D Team Templates (`doc-rnd`)
Innovation and technology exploration:
- **Tech Assessment** - Technology evaluation and recommendations
- **Integration Map** - System integration analysis
- **Prototype Documentation** - POC learnings and production path
- **Moonshot Plan** - Long-term architecture scenarios

### Intelligence Team Templates (`doc-intelligence`)
Product analytics and research:
- **Research Findings** - Qualitative research synthesis
- **Experiment Design** - A/B test specifications
- **Insights Report** - Data-driven recommendations

---

## Quality Gates Summary

**PRD**: Problem clear, scope defined, requirements testable, acceptance criteria present, no blocking questions

**TDD**: Traces to PRD, decisions have ADRs, interfaces defined, complexity justified, risks mitigated

**ADR**: Context explained, decision unambiguous, alternatives considered, consequences honest

**Test Plan**: Requirements traced, edge/error cases covered, performance tested, exit criteria clear

See category-specific skills for complete quality gate checklists.

---

## Related Resources

- `doc-artifacts` - 10x workflow templates (PRD, TDD, ADR, Test Plan)
- `doc-reviews` - Documentation team templates
- `doc-ecosystem` - Ecosystem and hygiene templates
- `doc-sre` - SRE, debt, and analytics templates
- `doc-strategy` - Strategy team templates
- `doc-security` - Security team templates
- `doc-rnd` - R&D team templates
- `doc-intelligence` - Intelligence team templates
- [Workflow & Lifecycle](workflow.md) - Pipeline flow, document lifecycle, indexing
- [Document Index](/docs/INDEX.md) - Registry of all project documentation
