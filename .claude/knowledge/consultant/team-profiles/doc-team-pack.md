# doc-team-pack

> Technical writing and documentation workflows

## Overview

The documentation team for creating, updating, and maintaining technical documentation. Takes documentation needs through scoping, drafting, editing, and publishing phases.

## Switch Command

```bash
/docs
```

## Agents

| Agent | Model | Role |
|-------|-------|------|
| **documentation-analyst** | opus | Scopes documentation needs |
| **technical-writer** | opus | Creates draft content |
| **editor** | opus | Polishes and refines |
| **publisher** | sonnet | Publishes final docs |

## Workflow

```
scoping → drafting → editing → publishing
    │         │          │          │
    ▼         ▼          ▼          ▼
 Doc Plan   Draft    Polished    Published
```

## Complexity Levels

| Level | When to Use | Scope |
|-------|-------------|-------|
| **PAGE** | Single doc page | One file |
| **SECTION** | Related pages | Directory |
| **SITE** | Full docs refresh | Entire docs |

## Best For

- README creation/updates
- API documentation
- User guides
- Technical specifications
- Architecture documentation

## Not For

- Code implementation → use 10x-dev-pack
- PRD/TDD artifacts → use 10x-dev-pack (documentation skill)
- Code comments → part of implementation

## Quick Start

```bash
/docs                          # Switch to team
/task "Document authentication API"
```

## Common Patterns

### API Documentation

```bash
/docs
/task "API reference for /users endpoint" --complexity=PAGE
```

### README Update

```bash
/docs
/task "Update README with new setup instructions"
```

### Full Documentation Refresh

```bash
/docs
/task "Refresh all documentation" --complexity=SITE
```

## Related Commands

- `/task` - Full documentation lifecycle
- No `/architect` or `/build` variants for this team
