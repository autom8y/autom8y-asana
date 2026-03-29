---
name: hygiene-catalog
description: "Hygiene rite agent profiles and capabilities. Use when: choosing between hygiene agents, understanding code-smeller vs janitor vs audit-lead roles, hygiene vs debt distinction. Triggers: code-smeller, architect-enforcer, janitor, audit-lead, hygiene agents."
---

# Hygiene Rite Catalog

## Agent Profiles

### code-smeller
**Model**: Opus | **Invocation**: `Act as **Code Smeller**`

Identifies problematic code patterns, smells, and quality issues. Use for initial codebase assessment, finding refactoring candidates, and pre-refactoring analysis.

**Detects**: Long methods (>50 LOC), god classes, duplicate code, deep nesting (>4 levels), large parameter lists, feature envy, dead code, poor naming.

### architect-enforcer
**Model**: Opus | **Invocation**: `Act as **Architect Enforcer**`

Ensures code adheres to documented architecture and ADRs. Use for validating implementations against TDDs, checking ADR compliance, and architecture drift detection.

**Validates**: Layer boundaries, dependency direction, interface contracts, design pattern implementations, module coupling/cohesion.

### janitor
**Model**: Sonnet | **Invocation**: `Act as **Janitor**`

Performs safe refactoring to improve code quality. Use for executing refactoring plans, cleaning up after implementation, reducing complexity, and removing duplication.

**Performs**: Extract method/class, rename for clarity, reduce nesting, simplify conditionals, remove dead code, consolidate duplicates.

### audit-lead
**Model**: Opus | **Invocation**: `Act as **Audit Lead**`

Orchestrates full quality audits and produces reports. Use for quarterly quality reviews, pre-release quality gates, and technical health assessments.

**Produces**: Quality audit reports, prioritized refactoring recommendations, code health metrics, trend analysis, remediation roadmaps.

## Hygiene vs Debt

| Hygiene Rite | Debt Rite |
|--------------|-----------|
| **Focus**: Code quality and cleanliness | **Focus**: Technical debt prioritization |
| **Action**: Detect and fix issues | **Action**: Assess and plan remediation |
| **Scope**: Module/file-level refactoring | **Scope**: Project/portfolio-level debt |
| **Horizon**: Sprint/week execution | **Horizon**: Quarterly/annual planning |

**Workflow**: Use `/debt` to plan, `/hygiene` to execute.

## Integration

Standards skill defines rules, hygiene agents enforce them. Reference: `standards` legomenon for code conventions and quality rules.
