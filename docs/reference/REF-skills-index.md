# REF-skills-index

> Skills architecture and activation triggers

**Category**: Reference
**Status**: Living Document
**Last Updated**: 2025-12-24

---

## Overview

Skills load context on-demand when Claude Code detects relevant keywords, file patterns, or task types. This document catalogs available skills and their activation criteria.

---

## Skills Directory

| Skill | When to Activate |
|-------|------------------|
| **autom8-asana** | SDK patterns, SaveSession, Business entities, detection, batch operations |
| **standards** | General Python/testing patterns (note: generic, not SDK-specific) |
| **documentation** | PRD/TDD/ADR templates, documentation workflows |
| **prompting** | Agent invocation patterns, workflow shortcuts |
| **10x-workflow** | Full lifecycle, quality gates, agent glossary |
| **initiative-scoping** | Prompt -1, Prompt 0 patterns |

---

## Activation Triggers

### autom8-asana

**Location**: `.claude/skills/autom8-asana/`

**Keywords**:
- SaveSession, Business, Contact, Unit, Offer, holder
- detect_entity_type, cascade_field, ActionOperation
- batch operation, async client

**File patterns**:
- `src/autom8_asana/**/*.py`
- `tests/**/*.py`

**Tasks**:
- SDK implementation
- Asana API integration
- Entity operations
- Hierarchy navigation

**Key files**:
- `SKILL.md` - Skill overview
- `entities.md` - Business model entities (Business, Contact, Unit, Offer)
- `persistence.md` - SaveSession, batch operations
- `automation.md` - Post-commit hooks, automation rules
- `glossary.md` - SDK-specific terminology
- `infrastructure.md` - Tech stack, project structure

### standards

**Location**: `.claude/skills/standards/`

**Keywords**:
- Python conventions, PEP 8
- Testing patterns, pytest
- Code quality, linting

**Tasks**:
- General Python patterns (not SDK-specific)
- Test structure
- Code style

### documentation

**Location**: `.claude/skills/documentation/`

**Keywords**:
- PRD, TDD, ADR, Test Plan
- Documentation templates
- Doc workflows

**Tasks**:
- Creating PRDs, TDDs, ADRs
- Documentation standards

### prompting

**Location**: `.claude/skills/prompting/`

**Keywords**:
- Agent invocation
- Workflow patterns
- Prompt templates

**Tasks**:
- Multi-agent coordination
- Workflow shortcuts

### 10x-workflow

**Location**: `.claude/skills/10x-workflow/`

**Keywords**:
- Full lifecycle
- Quality gates
- Agent workflows

**Tasks**:
- End-to-end development workflows
- Quality standards

### initiative-scoping

**Location**: `.claude/skills/initiative-scoping/`

**Keywords**:
- Prompt -1, Prompt 0
- Initiative planning
- Session protocols

**Tasks**:
- Large initiative scoping
- Multi-phase planning

---

## Skill Loading

Skills are loaded **on-demand** based on:
1. **Keyword detection** in user requests
2. **File pattern matching** in current work
3. **Task type inference** from context
4. **Explicit skill references** (e.g., "check autom8-asana skill")

Skills are **NOT loaded by default**—they activate only when relevant.

---

## Related

- [GLOSSARY.md](GLOSSARY.md) - Core terminology
- [/docs/INDEX.md](/docs/INDEX.md) - Documentation index
- [.claude/agents/README.md](../../.claude/agents/README.md) - Agent hierarchy
