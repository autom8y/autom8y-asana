---
name: claude-md-architecture
description: "First principles for CLAUDE.md architecture. Use when: modifying CLAUDE.md content, deciding CEM sync behavior, determining content placement, validating CLAUDE.md changes. Triggers: CLAUDE.md, sync behavior, content placement, section ownership, behavioral contract, session state boundaries."
---

# CLAUDE.md Architecture

> First principles for what belongs in CLAUDE.md and why.

## When to Use This Skill

Activate this skill when:

- Modifying any CLAUDE.md content (skeleton or satellite)
- Making CEM sync decisions (SYNC vs PRESERVE vs REGENERATE)
- Determining where content belongs (CLAUDE.md vs SESSION_CONTEXT vs hooks)
- Validating proposed CLAUDE.md changes
- Resolving content placement disputes

---

## The Core Question

> "Is this a behavioral contract (what Claude can do and how) or transient state (what's happening now)?"

CLAUDE.md is a **behavioral contract**, not a knowledge base, session log, or scratchpad.

---

## Quick Reference

### The Stability Rule

```
CLAUDE.md contains: STABLE content (changes weeks/months)
CLAUDE.md excludes: DYNAMIC + EPHEMERAL content (changes daily/hourly)
```

### The Decay Test

> "If I don't update this for a month, is CLAUDE.md incorrect?"

- **No** (still accurate) -> Belongs in CLAUDE.md
- **Yes** (becomes stale) -> Does not belong

### Section Ownership Quick Reference

| Owner | Sync Behavior | Examples |
|-------|---------------|----------|
| Skeleton | SYNC | Skills docs, hooks docs, workflow patterns |
| Satellite | PRESERVE | Project extensions, custom sections |
| Roster | REGENERATE | Quick Start, Agent Configurations |
| Session | NOT IN CLAUDE.md | Current task, git state, handoff context |

---

## Progressive Disclosure

**Core Concepts**:

- [first-principles.md](first-principles.md) - The 6 foundational principles
- [ownership-model.md](ownership-model.md) - Section ownership and sync behaviors
- [boundary-test.md](boundary-test.md) - 5-question validation checklist
- [anti-patterns.md](anti-patterns.md) - What NOT to put in CLAUDE.md

**Source Documents** (comprehensive reference):

- `/docs/architecture/FIRST-PRINCIPLES-CLAUDE-MD.md` - Complete principles documentation
- `/docs/architecture/CONCERN-SEPARATION-MATRIX.md` - Quick reference matrix
- `/docs/architecture/CLAUDE-MD-BOUNDARY-TEST.md` - Full validation checklist

**Related Skills**:

- [ecosystem-ref](../ecosystem-ref/SKILL.md) - CEM implementation and sync mechanics
- [documentation](../documentation/SKILL.md) - General documentation standards
- [standards](../standards/SKILL.md) - Repository conventions

---

## Decision Flowchart

```
New content to add to CLAUDE.md?
           |
           v
  Stable for 1 month? ----NO----> NOT in CLAUDE.md
           |                      (Use SESSION_CONTEXT or hooks)
          YES
           |
           v
  Project-wide scope? ----NO----> SESSION_CONTEXT
           |
          YES
           |
           v
  Who owns this content?
     /        |        \
 SKELETON   ROSTER   SATELLITE
    |         |          |
    v         v          v
  SYNC    REGENERATE  PRESERVE
 section   from state  section
```

---

## Validation Checklist (Quick)

Before modifying CLAUDE.md:

- [ ] Content passes Stability Test (accurate in 1 month)
- [ ] Content passes Source of Truth Test (CLAUDE.md is authoritative)
- [ ] Content passes Scope Test (project-wide, not session-specific)
- [ ] No dates, timestamps, or "currently" language
- [ ] No git state or file status references
- [ ] Correct owner identified (skeleton/satellite/roster)
- [ ] Correct sync behavior specified (SYNC/PRESERVE/REGENERATE)

See [boundary-test.md](boundary-test.md) for the complete 5-question validation.
