# hygiene-pack

> Code quality, refactoring, and cleanup workflows

## Overview

The code hygiene team for improving code quality through systematic assessment, detection of issues, remediation, and architectural compliance validation.

## Switch Command

```bash
/hygiene
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **audit-lead** | opus | Assesses codebase health |
| **code-smeller** | sonnet | Detects code smells |
| **janitor** | sonnet | Remediates issues |
| **architect-enforcer** | opus | Validates compliance |

## Workflow

```
assessment → detection → remediation → validation
     │            │           │            │
     ▼            ▼           ▼            ▼
  Audit       Smell       Clean       Compliance
  Report     Inventory     Code        Report
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **SPOT** | Single file cleanup | 1-2 files |
| **MODULE** | Component refactor | Directory |
| **CODEBASE** | Full audit | Entire repo |

## Best For

- Code quality audits
- Refactoring initiatives
- Pattern standardization
- Cleaning up legacy code
- Pre-release quality gates

## Not For

- Adding new features → use 10x-dev-pack
- Technical debt analysis → use debt-triage-pack
- Security issues → use security-pack

## Quick Start

```bash
/hygiene                       # Switch to team
/task "Audit authentication module"
```

## Common Patterns

### Code Audit

```bash
/hygiene
/task "Full codebase audit" --complexity=CODEBASE
```

### Targeted Cleanup

```bash
/hygiene
/task "Clean up utils/ directory" --complexity=MODULE
```

### Pattern Enforcement

```bash
/hygiene
/task "Enforce error handling patterns"
```

## Related Commands

- `/task` - Full hygiene lifecycle
- `/code-review` - Can be used for review perspective
