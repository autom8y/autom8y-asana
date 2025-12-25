# Command Registry

> **Purpose**: Global namespace registry for all slash commands
> **Status**: Migration Complete - All commands in `.claude/commands/`
> **Updated**: 2025-12-24

## Overview

This registry maps all slash commands to their implementation files. Commands are now proper Claude Code slash commands in `.claude/commands/` (not skills).

**Naming Conflicts Resolved**:
- `/resume` → `/continue` (avoid built-in conflict)
- `/review` → `/code-review` (avoid built-in conflict)

---

## Registered Commands (32 Total)

### Session Lifecycle (7 commands)

| Command | File | Status | Description |
|---------|------|--------|-------------|
| `/start` | [commands/start.md](commands/start.md) | Active | Begin new work session |
| `/park` | [commands/park.md](commands/park.md) | Active | Pause session, save state |
| `/continue` | [commands/continue.md](commands/continue.md) | Active | Resume parked session |
| `/handoff` | [commands/handoff.md](commands/handoff.md) | Active | Transfer work between agents |
| `/wrap` | [commands/wrap.md](commands/wrap.md) | Active | Finalize session, validate gates |
| `/sessions` | [commands/sessions.md](commands/sessions.md) | Active | List and manage active sessions |
| `/worktree` | [commands/worktree.md](commands/worktree.md) | Active | Manage isolated worktrees for parallel sessions |

### Team Management (10 commands)

| Command | File | Status | Description |
|---------|------|--------|-------------|
| `/team` | [commands/team.md](commands/team.md) | Active | Switch team pack or list |
| `/10x` | [commands/10x.md](commands/10x.md) | Active | Quick switch to 10x-dev-pack |
| `/docs` | [commands/docs.md](commands/docs.md) | Active | Quick switch to doc-team-pack |
| `/hygiene` | [commands/hygiene.md](commands/hygiene.md) | Active | Quick switch to hygiene-pack |
| `/debt` | [commands/debt.md](commands/debt.md) | Active | Quick switch to debt-triage-pack |
| `/sre` | [commands/sre.md](commands/sre.md) | Active | Quick switch to sre-pack |
| `/security` | [commands/security.md](commands/security.md) | Active | Quick switch to security-pack |
| `/intelligence` | [commands/intelligence.md](commands/intelligence.md) | Active | Quick switch to intelligence-pack |
| `/rnd` | [commands/rnd.md](commands/rnd.md) | Active | Quick switch to rnd-pack |
| `/strategy` | [commands/strategy.md](commands/strategy.md) | Active | Quick switch to strategy-pack |

### Development Workflows (4 commands)

| Command | File | Status | Description |
|---------|------|--------|-------------|
| `/sprint` | [commands/sprint.md](commands/sprint.md) | Active | Multi-task sprint orchestration |
| `/task` | [commands/task.md](commands/task.md) | Active | Single task full lifecycle |
| `/hotfix` | [commands/hotfix.md](commands/hotfix.md) | Active | Rapid fix for urgent issues |
| `/spike` | [commands/spike.md](commands/spike.md) | Active | Time-boxed research |

### Operations (5 commands)

| Command | File | Status | Description |
|---------|------|--------|-------------|
| `/architect` | [commands/architect.md](commands/architect.md) | Active | Design-only (TDD + ADRs) |
| `/build` | [commands/build.md](commands/build.md) | Active | Implementation-only |
| `/qa` | [commands/qa.md](commands/qa.md) | Active | Validation-only |
| `/pr` | [commands/pr.md](commands/pr.md) | Active | Create pull request |
| `/code-review` | [commands/code-review.md](commands/code-review.md) | Active | Structured code review |

### Meta/Navigation (2 commands)

| Command | File | Status | Description |
|---------|------|--------|-------------|
| `/consult` | [commands/consult.md](commands/consult.md) | Active | Ecosystem guidance and command-flows |
| `/sync` | [commands/sync.md](commands/sync.md) | Active | Sync project with skeleton_claude ecosystem |

### Meta/Factory (4 commands)

| Command | File | Status | Description |
|---------|------|--------|-------------|
| `/forge` | [commands/forge.md](commands/forge.md) | Active | The Forge overview and help |
| `/new-team` | [commands/new-team.md](commands/new-team.md) | Active | Create new team pack |
| `/validate-team` | [commands/validate-team.md](commands/validate-team.md) | Active | Validate existing team |
| `/eval-agent` | [commands/eval-agent.md](commands/eval-agent.md) | Active | Test single agent |

---

## Architecture

### Command Location
```
.claude/commands/{name}.md    # Invocable slash commands (20-80 lines)
.claude/skills/{name}-ref/skill.md # Reference documentation (200-800 lines)
```

### Command Format
```markdown
---
description: Brief description for /help
argument-hint: [args]
allowed-tools: Bash, Read, Write, Task, ...
---

## Context
- Dynamic state via !`shell commands`

## Your Task
$ARGUMENTS

## Behavior
[Core logic]

## Reference
Full documentation: `.claude/skills/{name}-ref/skill.md`
```

---

## Consultant Synchronization

> **IMPORTANT**: When adding or modifying commands, update the Consultant knowledge base.

The `/consult` command provides ecosystem navigation. If its knowledge is stale, users get wrong guidance.

### Files to Update

| Change | Update These Files |
|--------|-------------------|
| New command | `knowledge/consultant/command-reference.md`, `ecosystem-map.md` |
| New team | `command-reference.md`, `agent-reference.md`, `team-profiles/{team}.md`, routing files |
| Workflow change | `team-profiles/{team}.md`, `agent-reference.md` |

### Knowledge Base Location

```
.claude/knowledge/consultant/
├── ecosystem-map.md       # Team/command overview
├── command-reference.md   # All commands
├── agent-reference.md     # All agents
├── routing/               # Intent patterns
├── team-profiles/         # Team details
└── playbooks/curated/     # Workflow playbooks
```

### Validation

```bash
# Verify command count matches
grep "Total" .claude/knowledge/consultant/command-reference.md
grep "32 Total" .claude/COMMAND_REGISTRY.md
```

See `.claude/skills/team-development/patterns/consultant-sync.md` for detailed sync patterns.

---

## Reserved Built-in Commands

These are Claude Code built-in commands - DO NOT create custom commands with these names:

```
/add-dir    /agents     /bashes     /bug        /clear
/compact    /config     /context    /cost       /doctor
/exit       /export     /help       /hooks      /ide
/init       /install-github-app     /login      /logout
/mcp        /memory     /model      /output-style /permissions
/plugin     /pr-comments /privacy-settings /release-notes
/rename     /resume     /review     /rewind     /sandbox
/security-review /stats /status     /statusline /terminal-setup
/todos      /usage      /vim
```

---

## Hooks Architecture

Commands receive context automatically via hooks instead of redundant `!` shell commands.

### Registered Hooks

| Hook | Event | Script | Purpose |
|------|-------|--------|---------|
| session-context | SessionStart | `hooks/session-context.sh` | Inject project, team, session, git context |
| auto-park | Stop | `hooks/auto-park.sh` | Auto-save session state on exit |
| artifact-tracker | PostToolUse (Write) | `hooks/artifact-tracker.sh` | Track PRD/TDD/ADR creation |
| team-validator | PreToolUse (Bash) | `hooks/team-validator.sh` | Validate team switch operations |

### Hook Configuration

Hooks are configured in `.claude/settings.local.json`:
```json
{
  "hooks": {
    "SessionStart": [{ "matcher": "startup|resume", "hooks": [{ "type": "command", "command": ".claude/hooks/session-context.sh" }] }],
    "Stop": [{ "hooks": [{ "type": "command", "command": ".claude/hooks/auto-park.sh" }] }],
    "PostToolUse": [{ "matcher": "Write", "hooks": [{ "type": "command", "command": ".claude/hooks/artifact-tracker.sh" }] }],
    "PreToolUse": [{ "matcher": "Bash", "hooks": [{ "type": "command", "command": ".claude/hooks/team-validator.sh" }] }]
  }
}
```

### Context Injection

SessionStart hook outputs markdown context that Claude sees on every session:
```
## Project Context (auto-loaded)
- **Project**: /path/to/project
- **Active Team**: 10x-dev-pack
- **Session**: feature-auth (ACTIVE, implementation phase)
- **Git**: main (clean)
- **PRDs**: PRD-auth.md
- **TDDs**: TDD-auth.md
```

Commands no longer need redundant `!` commands - context is auto-injected.

---

## Migration Notes

### 2025-12-24: Skills → Commands Migration

**Changed**:
- All 19 commands moved from `.claude/skills/*/skill.md` to `.claude/commands/*.md`
- Commands now use Claude Code slash command format (YAML frontmatter + `!` context)
- Skills remain as detailed reference documentation

**Renamed**:
- `/resume` → `/continue` (built-in conflict)
- `/review` → `/code-review` (built-in conflict)

**Format Change**:
- Commands are now 20-80 lines (actionable prompts)
- Skills remain 200-800 lines (reference docs)
- Commands reference skills via "Full documentation" link

### 2025-12-24: Hooks Architecture

**Added**:
- SessionStart hook for automatic context injection
- Stop hook for session auto-parking
- PostToolUse hook for artifact tracking
- PreToolUse hook for team validation

**Changed**:
- All 19 commands updated to use hook-injected context
- Removed redundant `!` shell commands (50+ eliminated)
- Commands now say "Auto-injected by SessionStart hook"

**Files Created**:
- `.claude/hooks/session-context.sh`
- `.claude/hooks/auto-park.sh`
- `.claude/hooks/artifact-tracker.sh`
- `.claude/hooks/team-validator.sh`

### 2025-12-24: Skill Directory Renaming

**Issue**: Claude Code bug #14945 - commands blocked when skill shares same name.

**Fix**: Renamed 17 skill directories from `{name}/` to `{name}-ref/`:
- `skills/team/` → `skills/team-ref/`
- `skills/10x/` → `skills/10x-ref/`
- (and 15 others)

**Result**: All 19 commands now user-invocable via `/{name}`.

### 2025-12-24: Consultant Agent Addition

**Added**:
- `/consult` command for ecosystem navigation and guidance
- Consultant agent as global singleton (persists across team swaps)
- Knowledge base at `.claude/knowledge/consultant/`
- 8 curated playbooks for common workflows
- consult-ref skill for reference documentation

**Architecture**:
- Global agents directory: `~/.claude/agents/`
- Modified `swap-team.sh` to preserve global agents after team swaps
- Knowledge base includes routing logic, team profiles, and playbooks

**Files Created**:
- `~/.claude/agents/consultant.md`
- `.claude/commands/consult.md`
- `.claude/skills/consult-ref/skill.md` (+ 3 support files)
- `.claude/knowledge/consultant/` (ecosystem-map, routing, team-profiles, playbooks)

### 2025-12-24: The Forge (Agent Factory Team)

**Added**:
- 6 global agents for team creation: agent-designer, prompt-architect, workflow-engineer, platform-engineer, eval-specialist, agent-curator
- 4 commands: `/forge`, `/new-team`, `/validate-team`, `/eval-agent`
- Forge knowledge base at `.claude/knowledge/forge/`
- forge-ref skill for reference documentation

**Architecture**:
- The Forge is a global singleton team (persists across team swaps)
- Has its own workflow at `.claude/forge-workflow.yaml`
- Complexity levels: PATCH, TEAM, ECOSYSTEM
- Workflow: Designer → Prompt Architect → Workflow Engineer → Platform Engineer → Eval Specialist → Curator

**Files Created**:
- `~/.claude/agents/{agent-designer,prompt-architect,workflow-engineer,platform-engineer,eval-specialist,agent-curator}.md`
- `.claude/commands/{forge,new-team,validate-team,eval-agent}.md`
- `.claude/forge-workflow.yaml`
- `.claude/knowledge/forge/` (patterns, evals, templates)
- `.claude/skills/forge-ref/skill.md`

### 2025-12-24: Claude Ecosystem Manager (CEM)

**Added**:
- `cem` script for syncing skeleton_claude ecosystem to satellite projects
- `/sync` command for in-Claude synchronization
- Physical copy with intelligent merge (not symlinks)

**Architecture**:
- Copy-based sync: files physically copied to each project's `.claude/`
- State tracking via `.claude/.cem/manifest.json`
- Git-based versioning (commit hash tracking)
- Three sync strategies: COPY-REPLACE, MERGE-SETTINGS, MERGE-DOCS

**Commands**:
- `cem init` - Initialize project with ecosystem
- `cem sync` - Pull updates from skeleton
- `cem status` - Show sync state and version
- `cem diff` - Show differences with skeleton

**Files Created**:
- `skeleton_claude/cem` - Main CLI tool (~800 lines)
- `.claude/commands/sync.md` - Slash command wrapper

### 2025-12-24: Worktree Isolation

**Added**:
- `/worktree` command for managing isolated git worktrees
- True filesystem isolation for parallel Claude sessions
- Each worktree gets independent `.claude/` ecosystem

**Architecture**:
- Uses git worktrees with detached HEAD (no branch pollution)
- Worktrees stored in `project/worktrees/wt-{id}/`
- Each worktree auto-initialized via CEM
- Session, team, and sprint state fully isolated

**Commands**:
- `/worktree create [name] [--team=PACK]` - Create isolated worktree
- `/worktree list` - List all worktrees with status
- `/worktree remove <id>` - Remove specific worktree
- `/worktree cleanup` - Remove stale worktrees (7+ days)
- `/worktree status` - Detailed worktree info

**Files Created**:
- `.claude/commands/worktree.md` - Slash command
- `.claude/hooks/lib/worktree-manager.sh` - Core worktree operations
- `.claude/skills/worktree-ref/skill.md` - Reference documentation

**Integration**:
- `/start` now suggests worktrees when session exists
- `/wrap` offers worktree cleanup when in worktree
- `/sessions --all` shows sessions across all worktrees
- `cem status` detects and displays worktree info
