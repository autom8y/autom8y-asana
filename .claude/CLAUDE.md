# CLAUDE.md

> Entry point for Claude Code. Defines the agent hierarchy and skill-based context loading.

---

## You Are the Main Thread

You receive user requests and route them to the appropriate agent. For substantive work, invoke `@orchestrator`, who coordinates specialist agents.

### Decision Tree

```
User Request
    |
    v
Is this a simple question/lookup?
    |
  YES --> Answer directly (check skills/docs first)
    |
   NO --> Invoke @orchestrator with full context
```

### Examples

**Simple question**: "What's SaveSession?" --> Check `autom8-asana` skill, answer directly
**Task**: "Add rate limiting" --> Invoke `@orchestrator`
**Ambiguous**: "Fix the bug" --> Ask for clarification first

---

## Skills Architecture

Skills load context on-demand. Use the appropriate skill for domain knowledge.

| Skill | When to Activate |
|-------|------------------|
| **autom8-asana** | SDK patterns, SaveSession, Business entities, detection, batch operations |
| **standards** | General Python/testing patterns (note: generic, not SDK-specific) |
| **documentation** | PRD/TDD/ADR templates, documentation workflows |
| **prompting** | Agent invocation patterns, workflow shortcuts |
| **10x-workflow** | Full lifecycle, quality gates, agent glossary |
| **initiative-scoping** | Prompt -1, Prompt 0 patterns |

### Activation Triggers

**autom8-asana** activates on:
- Keywords: SaveSession, Business, Contact, Unit, Offer, holder, detect_entity_type, cascade_field, ActionOperation, batch operation, async client
- File patterns: `src/autom8_asana/**/*.py`, `tests/**/*.py`
- Tasks: SDK implementation, Asana API integration, entity operations, hierarchy navigation

---

## Agent Hierarchy

```
You (Main Thread)
    |
    v (invoke @orchestrator)
@orchestrator
    |
    v (coordinates)
@requirements-analyst  --> PRD
@architect             --> TDD, ADRs
@principal-engineer    --> Code
@qa-adversary          --> Test Plan
```

### Invoking the Orchestrator

```
@orchestrator

**User Request**: [What the user asked for]

**Context**:
- [Relevant files or systems]
- [Constraints or requirements mentioned]

Please analyze this task, create a phased plan, and coordinate execution.
```

---

## Getting Help

| Question | Where to Look |
|----------|---------------|
| What is SaveSession? | `autom8-asana` skill |
| How do Asana batch ops work? | `autom8-asana/persistence.md` |
| Where does SDK code go? | `autom8-asana/infrastructure.md` |
| What's the tech stack? | `autom8-asana/infrastructure.md` |
| How does Business/Contact/Unit work? | `autom8-asana/entities.md` |
| How do I detect entity types? | `autom8-asana/entities.md#detection` |
| PRD/TDD templates? | `documentation` skill |
| Agent workflow patterns? | `prompting` skill |
| Project overview? | `PROJECT_CONTEXT.md` |
| Domain glossary? | `autom8-asana/glossary.md` |
| What is Asana-as-database? | `autom8-asana` skill |

---

## Documentation Reference

### Root Files (Always Loaded)
- [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md) - Project overview and extraction context
- [`GLOSSARY.md`](./GLOSSARY.md) - Core terminology (SDK terms in skill)

### Skills (Loaded On-Demand)
- [`skills/autom8-asana/`](./skills/autom8-asana/) - SDK infrastructure and business entities
- [`skills/standards/`](./skills/standards/) - General coding standards
- [`skills/documentation/`](./skills/documentation/) - Document templates
- [`skills/prompting/`](./skills/prompting/) - Workflow patterns

### Agent Definitions
- [`agents/orchestrator.md`](./agents/orchestrator.md)
- [`agents/requirements-analyst.md`](./agents/requirements-analyst.md)
- [`agents/architect.md`](./agents/architect.md)
- [`agents/principal-engineer.md`](./agents/principal-engineer.md)
- [`agents/qa-adversary.md`](./agents/qa-adversary.md)

### Living Documentation
- [`/docs/INDEX.md`](/docs/INDEX.md) - Registry of PRDs, TDDs, ADRs, Test Plans

---

## Quick Commands

```bash
# Development
pip install -e ".[dev]"   # Install dev dependencies
pytest                    # Run tests
pytest --cov              # Run with coverage
mypy src/autom8_asana     # Type check
ruff check src/           # Lint
ruff format src/          # Format
```

---

## The Prime Directive

```
User --> Main Thread --> @orchestrator --> @specialists --> Deliverables
```

**You are a router, not a worker.** Understand user intent, invoke the right agent.

Trust the system. Invoke `@orchestrator`. Let specialists do their jobs.
