# First Principles: CLAUDE.md Architecture

> "Session-specific knowledge should NOT be in CLAUDE.md. CLAUDE.md should just maintain alignment with the active team to ensure standardized workflows are followed."

These six principles govern all CLAUDE.md architecture decisions across the skeleton/satellite ecosystem.

---

## Principle 1: CLAUDE.md is a Behavioral Contract

CLAUDE.md tells Claude **what it can do** and **how to work**, not what it is currently doing.

### What CLAUDE.md Answers

1. **What can Claude do here?** (Capabilities: skills, agents, hooks)
2. **How should Claude work here?** (Workflow: routing patterns, handoff protocols)
3. **Who is Claude working as?** (Identity: active team, available agents)

### What CLAUDE.md Is NOT

| Not This | Use This Instead |
|----------|------------------|
| Knowledge base | Skills for domain knowledge |
| Session log | SESSION_CONTEXT for work in progress |
| Task tracker | Todo tools, session files |
| Scratchpad | Conversation context for transient state |

### The Minimal Viable CLAUDE.md

```markdown
# CLAUDE.md

This project uses a {N}-agent workflow ({team-name}).

## Available Agents
{list of agents with one-line descriptions}

## Skills
{list of skills Claude can invoke}

## Workflow
{routing guidance: when to invoke which agent}
```

Everything else is either infrastructure documentation (synced from skeleton) or project extensions (satellite-owned).

---

## Principle 2: Stable Content Only

If content changes more than once per session, it does not belong in CLAUDE.md.

### Stability Tiers

| Tier | Change Frequency | In CLAUDE.md? | Examples |
|------|------------------|---------------|----------|
| **STATIC** | Once (at init) | Rarely needed | Skeleton source reference |
| **STABLE** | Weeks/months | **Yes** | Team, skills, workflow |
| **DYNAMIC** | Days/weekly | **No** | Current initiative |
| **EPHEMERAL** | Minutes/hourly | **No** | Git state, current task |

### The Stability Boundary

```
CLAUDE.md contains: STATIC + STABLE
CLAUDE.md excludes: DYNAMIC + EPHEMERAL
```

### Applying the Classification

| Content | Stability | In CLAUDE.md? | Alternative |
|---------|-----------|---------------|-------------|
| Skill documentation | STABLE | Yes | - |
| Agent roster | STABLE | Yes (regenerated) | - |
| Workflow patterns | STABLE | Yes (synced) | - |
| Active team name | STABLE | Yes (regenerated) | ACTIVE_TEAM file |
| Current initiative | DYNAMIC | No | SESSION_CONTEXT |
| Sprint goals | DYNAMIC | No | PRD, project docs |
| Git branch | EPHEMERAL | No | Hook output |
| Current task | EPHEMERAL | No | Conversation context |

---

## Principle 3: Separation by Source of Truth

Each concern has exactly one owner. Content placement follows ownership.

### The Five Concerns

| Concern | Owner | In CLAUDE.md? | Sync Behavior |
|---------|-------|---------------|---------------|
| **Ecosystem Infrastructure** | Skeleton | Yes | SYNC |
| **Project Identity** | Satellite | Yes | PRESERVE |
| **Team Configuration** | Roster | Yes | REGENERATE |
| **Session State** | Session | **No** | N/A |
| **Workflow Guidance** | Skeleton | Yes | SYNC |

### The Critical Distinction

```
CLAUDE.md = Ecosystem Infrastructure + Project Identity + Team Configuration

CLAUDE.md != Session State
```

Session state is injected by hooks at session start. It appears in Claude's context but never writes back to CLAUDE.md.

### Source of Truth Tests

| Test | Answer | Result |
|------|--------|--------|
| Skeleton | SYNC |
| Satellite | PRESERVE or PROJECT |
| ACTIVE_TEAM + agents/ | REGENERATE |
| Session files | NOT IN CLAUDE.md |

---

## Principle 4: Injection for Transient State

Hooks inject ephemeral context at session start. It appears in Claude's view but never writes to CLAUDE.md.

### The Three Layers

```
SESSION CONTEXT (Injected by hooks)
  - Git state, active session, worktree context
          |
          v
PROJECT CLAUDE.md (.claude/CLAUDE.md)
  - Team config, project identity, infrastructure
          |
          v
GLOBAL CLAUDE.md (~/.claude/CLAUDE.md)
  - Personal preferences, global tools
```

### Layer Responsibilities

| Layer | Content Type | Modified By |
|-------|--------------|-------------|
| Global | Personal preferences, global tools | User manually |
| Project | Team + Project + Infrastructure | CEM sync, roster |
| Session | Transient state, current work | Hooks (read-only to CLAUDE.md) |

### Hook Output Example

```markdown
## Project Context (auto-loaded)

| Property | Value |
|----------|-------|
| **Project** | /Users/dev/myproject |
| **Active Team** | doc-team-pack |
| **Git** | feature/add-auth (3 uncommitted) |
```

This content is:
- Generated fresh on each session start
- Never written to CLAUDE.md
- Only exists in Claude's conversation context
- Can change between sessions without file modification

---

## Principle 5: Single Purpose per Content

Each piece of content has one owner, one sync behavior, one location.

### Content Classification

| Content | Owner | Sync | Location |
|---------|-------|------|----------|
| Skills Architecture table | Skeleton | SYNC | CLAUDE.md |
| Project-specific conventions | Satellite | PRESERVE | CLAUDE.md (## Project:*) |
| Quick Start agent table | Roster | REGENERATE | CLAUDE.md |
| Current initiative | Session | N/A | SESSION_CONTEXT |
| Git state | Hooks | N/A | Hook output only |

### The Anti-Duplication Rule

If content exists in multiple places, one becomes stale. Pick the authoritative source and reference it:

- **Derived content**: Regenerate from source (team sections from ACTIVE_TEAM + agents/)
- **Transient content**: Inject via hooks, never persist
- **Project extensions**: Use `## Project:*` namespace

---

## Principle 6: The Decay Test

Content that decays (becomes stale) without active maintenance does not belong in CLAUDE.md.

### The Test

> "If I don't update this for a month, is CLAUDE.md incorrect?"

| Answer | Verdict |
|--------|---------|
| **No** (still accurate) | Belongs in CLAUDE.md (STABLE) |
| **Yes** (becomes stale) | Does not belong (DYNAMIC/EPHEMERAL) |

### Applying the Decay Test

| Content | After 1 Month | Belongs? |
|---------|---------------|----------|
| Skills documentation | Still accurate | Yes |
| Workflow patterns | Still accurate | Yes |
| Agent roster | Still accurate (unless team swapped) | Yes |
| "Currently working on X" | Stale immediately | No |
| Git branch name | Stale within hours | No |
| "Last updated: DATE" | Stale immediately | No |

### The Ultimate Test

> "If this content disappeared, would Claude work less effectively in this project?"

- **YES**: The content describes capabilities, workflow, or identity that Claude needs
- **NO**: The content is informational, historical, or transient

CLAUDE.md should contain only content that passes the YES test.

---

## Summary Table

| Principle | Rule | Test |
|-----------|------|------|
| 1. Behavioral Contract | What Claude can do and how | Does it define capabilities or workflow? |
| 2. Stable Content Only | Changes less than once per session | Will it be accurate in a month? |
| 3. Separation by Source | One owner per content | Where is the authoritative source? |
| 4. Injection for Transient | Hooks inject, CLAUDE.md stores | Does it change per session? |
| 5. Single Purpose | One owner, one location | Is it duplicated anywhere? |
| 6. Decay Test | No maintenance = still accurate | Does it rot without updates? |

---

## Related Files

- [ownership-model.md](ownership-model.md) - Detailed section ownership
- [boundary-test.md](boundary-test.md) - Validation checklist
- [anti-patterns.md](anti-patterns.md) - What NOT to put in CLAUDE.md
