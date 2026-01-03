# CLAUDE.md Boundary Test

A practical checklist for determining if content belongs in CLAUDE.md. Before adding ANY content, run through these five questions.

---

## The Five-Question Test

### Question 1: Stability Test

> "Will this content be accurate in one month without updates?"

| Answer | Verdict |
|--------|---------|
| Yes | Proceed to Question 2 |
| No | **STOP. Does not belong in CLAUDE.md.** |

**Examples that fail**:
- Current task or initiative
- Sprint goals
- Git branch name
- Recent decisions
- "Last updated" timestamps

**Where it should go**: SESSION_CONTEXT, session files, hook output

---

### Question 2: Source of Truth Test

> "Is CLAUDE.md the authoritative source for this content?"

| Answer | Verdict |
|--------|---------|
| Yes, CLAUDE.md is THE source | Proceed to Question 3 |
| No, derived from elsewhere | **Consider regeneration or hook injection instead** |

**Examples that fail**:
- Git state (derived from repository)
- Session state (derived from SESSION_CONTEXT)
- Team roster (derived from ACTIVE_TEAM + agents/)
- Build status (derived from CI)

**Correct approach**: Inject via hooks or regenerate from authoritative source

---

### Question 3: Scope Test

> "Does this content apply to ALL sessions in this project?"

| Answer | Verdict |
|--------|---------|
| Yes, project-wide | Proceed to Question 4 |
| No, session-specific | **STOP. Belongs in SESSION_CONTEXT or hook output.** |

**Examples that fail**:
- Current initiative
- Handoff context
- Parked session info
- "Currently working on..."
- Phase-specific decisions

**Where it should go**: SESSION_CONTEXT for persistent session state, hook output for transient context

---

### Question 4: Propagation Test

> "Should changes to this content flow between skeleton and satellites?"

| Answer | Sync Behavior | Section Type |
|--------|---------------|--------------|
| Yes, skeleton -> satellites | SYNC | Infrastructure section |
| No, satellite-only | PRESERVE | Identity/Extension section |
| Regenerated from roster | REGENERATE | Team configuration |

**Use this to determine section ownership**:
- Infrastructure docs (skills, hooks, routing) = SYNC
- Project-specific content = PRESERVE or `## Project:*`
- Agent roster = REGENERATE from ACTIVE_TEAM

---

### Question 5: Noise Test

> "If this content disappeared, would Claude work less effectively?"

| Answer | Verdict |
|--------|---------|
| Yes, Claude needs this | Essential content, include it |
| No, nice-to-have | Consider removing or relocating |

**Essential content examples**:
- Skills activation table
- Agent routing guidance
- Workflow patterns
- Hook documentation

**Noise examples**:
- Historical context
- Informational notes
- "FYI" content
- Redundant references

---

## Quick Decision Flowchart

```
                    +---------------------+
                    | New content to add  |
                    +----------+----------+
                               |
                    +----------v----------+
                    | Stable for 1 month? |
                    +----------+----------+
                               |
              +----------------+----------------+
              | NO                              | YES
              v                                 v
    +------------------+             +---------------------+
    | NOT in CLAUDE.md |             | Project-wide scope? |
    | Use SESSION_     |             +----------+----------+
    | CONTEXT or hooks |                        |
    +------------------+            +-----------+-----------+
                                    | NO                    | YES
                                    v                       v
                              +------------+     +------------------+
                              | SESSION_   |     | Who owns this?   |
                              | CONTEXT    |     +--------+---------+
                              +------------+              |
                                               +----------+----------+
                                               |          |          |
                                            SKELETON   ROSTER   SATELLITE
                                               |          |          |
                                               v          v          v
                                             SYNC     REGENERATE  PRESERVE
                                            section   from state   section
```

---

## Red Flags Checklist

If your content contains any of these, reconsider:

| Red Flag | Why Problematic | Correct Approach |
|----------|-----------------|------------------|
| Dates or timestamps | Immediately stale | Use git history |
| "Currently..." | Session state | SESSION_CONTEXT |
| "Last updated..." | Maintenance burden | Git history |
| "Working on..." | Task state | Session files |
| Git branch names | Changes every checkout | Hook injection |
| Commit hashes | Changes every commit | Hook injection |
| File paths that change | Fragile references | Relative or regenerated |
| Personal preferences | User-specific | ~/.claude/CLAUDE.md |
| Specific version numbers | Unless truly stable | Keep minimal |
| "Today" or "yesterday" | Time-relative | Never use |

---

## Correct Placement Guide

| Content Type | Correct Location | Why |
|--------------|------------------|-----|
| Skills documentation | CLAUDE.md (SYNC) | Stable, project-wide |
| Agent roster | CLAUDE.md (REGENERATE) | Derived from roster |
| Workflow patterns | CLAUDE.md (SYNC) | Stable infrastructure |
| Project extensions | CLAUDE.md (`## Project:*`) | Satellite-owned |
| Current task | SESSION_CONTEXT | Session-specific |
| Session phase | SESSION_CONTEXT | Changes during session |
| Parked session info | SESSION_CONTEXT | Ephemeral |
| Git status | Hook output | Changes constantly |
| Worktree context | Hook output | Ephemeral |
| Personal preferences | ~/.claude/CLAUDE.md | User-scoped |
| Sprint details | PRD or session files | Dynamic |
| Historical decisions | Session summaries | Archival |

---

## The Ultimate Test

Before committing any CLAUDE.md change:

> "Is this a behavioral contract (what Claude can do and how) or transient state (what's happening now)?"

| Answer | Result |
|--------|--------|
| **Behavioral contract** | Belongs in CLAUDE.md |
| **Transient state** | Belongs elsewhere |

---

## Validation Checklist

Copy this checklist before any CLAUDE.md modification:

```markdown
## Pre-Modification Validation

- [ ] Content passes Stability Test (accurate in 1 month)
- [ ] Content passes Source of Truth Test (CLAUDE.md is authoritative)
- [ ] Content passes Scope Test (project-wide, not session-specific)
- [ ] Content passes Propagation Test (correct sync behavior identified)
- [ ] Content passes Noise Test (Claude needs this to work effectively)
- [ ] No dates, timestamps, or "currently" language
- [ ] No git state or file status references
- [ ] No session-specific information
- [ ] Owner correctly identified (skeleton/satellite/roster)
- [ ] Correct sync behavior specified (SYNC/PRESERVE/REGENERATE/PROJECT)
```

---

## Related Files

- [first-principles.md](first-principles.md) - Core architectural principles
- [ownership-model.md](ownership-model.md) - Section ownership details
- [anti-patterns.md](anti-patterns.md) - What NOT to put in CLAUDE.md
