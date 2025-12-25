# Claude Code Ecosystem Map

> Complete overview of the agentic development system

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                                           ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│  /consult (Consultant)  │           │  /forge (The Forge)     │
│     Meta-Navigator      │           │    Agent Factory        │
└─────────────────────────┘           └─────────────────────────┘
        │                                           │
        │                                           ▼
        │                              ┌─────────────────────────┐
        │                              │   Creates & Maintains   │
        │                              │         Teams           │
        │                              └─────────────────────────┘
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
 ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
 │   Commands  │   │    Teams    │   │  Playbooks  │
 │    (29)     │   │     (9)     │   │  (curated)  │
 └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Teams (9 Total)

| Team | Switch | Agents | Domain |
|------|--------|--------|--------|
| **10x-dev-pack** | `/10x` | 5 | Full feature development lifecycle |
| **doc-team-pack** | `/docs` | 4 | Documentation workflows |
| **hygiene-pack** | `/hygiene` | 4 | Code quality, refactoring |
| **debt-triage-pack** | `/debt` | 3 | Technical debt management |
| **sre-pack** | `/sre` | 4 | Operations, reliability |
| **security-pack** | `/security` | 4 | Security assessment, compliance |
| **intelligence-pack** | `/intelligence` | 4 | Analytics, A/B testing, research |
| **rnd-pack** | `/rnd` | 4 | Exploration, prototyping |
| **strategy-pack** | `/strategy` | 4 | Business analysis, planning |

**Total Agents**: 36 across all teams

---

## Commands (30 Total)

### Session Lifecycle (5)

| Command | Purpose |
|---------|---------|
| `/start` | Initialize new work session with context |
| `/park` | Pause session, preserve state for later |
| `/continue` | Resume a parked session |
| `/handoff` | Transfer work between agents |
| `/wrap` | Finalize session, run quality gates |

### Team Management (10)

| Command | Purpose |
|---------|---------|
| `/team` | Switch team or list available |
| `/10x` | Quick switch to 10x-dev-pack |
| `/docs` | Quick switch to doc-team-pack |
| `/hygiene` | Quick switch to hygiene-pack |
| `/debt` | Quick switch to debt-triage-pack |
| `/sre` | Quick switch to sre-pack |
| `/security` | Quick switch to security-pack |
| `/intelligence` | Quick switch to intelligence-pack |
| `/rnd` | Quick switch to rnd-pack |
| `/strategy` | Quick switch to strategy-pack |

### Development Workflows (4)

| Command | Purpose |
|---------|---------|
| `/task` | Single task through full lifecycle |
| `/sprint` | Multi-task sprint orchestration |
| `/hotfix` | Rapid fix for urgent issues |
| `/spike` | Time-boxed research (no production code) |

### Operations (5)

| Command | Purpose |
|---------|---------|
| `/architect` | Design phase only (TDD + ADRs) |
| `/build` | Implementation phase only |
| `/qa` | Validation phase only |
| `/pr` | Create pull request |
| `/code-review` | Structured code review |

### Meta/Navigation (2)

| Command | Purpose |
|---------|---------|
| `/consult` | Ecosystem guidance and command-flows |
| `/sync` | Sync project with skeleton_claude ecosystem |

### Meta/Factory (4)

| Command | Purpose |
|---------|---------|
| `/forge` | The Forge overview and help |
| `/new-team` | Create new team pack |
| `/validate-team` | Validate existing team |
| `/eval-agent` | Test single agent |

---

## Workflows

All teams use **sequential workflows** with complexity gating.

### Workflow Pattern

```
phase-1 → phase-2 → phase-3 → phase-4
   │          │          │          │
   ▼          ▼          ▼          ▼
artifact  artifact  artifact  artifact
```

### Complexity Levels

Each team defines its own complexity levels:

| Team | Levels | Determines |
|------|--------|------------|
| 10x-dev-pack | SCRIPT, MODULE, SERVICE, PLATFORM | Which phases to include |
| doc-team-pack | PAGE, SECTION, SITE | Depth of documentation |
| hygiene-pack | SPOT, MODULE, CODEBASE | Scope of audit |
| debt-triage-pack | QUICK, AUDIT | Extent of analysis |
| sre-pack | TASK, PROJECT, PLATFORM | Operational scope |
| security-pack | PATCH, FEATURE, SYSTEM | Security depth |
| intelligence-pack | METRIC, FEATURE, INITIATIVE | Research scope |
| rnd-pack | SPIKE, EVALUATION, MOONSHOT | Exploration depth |
| strategy-pack | TACTICAL, STRATEGIC, TRANSFORMATION | Planning horizon |

---

## Sessions

### TTY-Based Isolation

Each terminal gets its own session:
- Sessions are mapped by TTY hash
- Multiple terminals = multiple concurrent sessions
- No interference between sessions

### Session Artifacts

```
.claude/sessions/{session-id}/
  SESSION_CONTEXT.md    # Current state, blockers, artifacts
  PRD-{slug}.md         # Requirements (if created)
  TDD-{slug}.md         # Design (if created)
```

### Session States

| State | Meaning |
|-------|---------|
| ACTIVE | Work in progress |
| PARKED | Paused, preserves context |
| COMPLETED | Wrapped and finalized |

---

## Hooks

Hooks auto-inject context and automate operations.

| Hook | Event | Purpose |
|------|-------|---------|
| session-context | SessionStart | Load project, team, session, git info |
| auto-park | Stop | Save session state on exit |
| artifact-tracker | PostToolUse | Track PRD/TDD/ADR creation |
| team-validator | PreToolUse | Validate team switch commands |

---

## Skills

Skills provide domain knowledge on-demand.

| Skill | Domain |
|-------|--------|
| 10x-workflow | Agent coordination, handoffs |
| documentation | PRD/TDD/ADR templates |
| standards | Code conventions, tech stack |
| prompting | Copy-paste invocation patterns |
| justfile | Task automation recipes |
| atuin-desktop | Runbook file format |
| initiative-scoping | Session -1/0 protocols |

---

## Global Agents (Singletons)

Some agents persist across team swaps:

```
.claude/global-agents/
  consultant.md           # Ecosystem navigator
  agent-designer.md       # The Forge: role specs
  prompt-architect.md     # The Forge: system prompts
  workflow-engineer.md    # The Forge: orchestration
  platform-engineer.md    # The Forge: infrastructure
  eval-specialist.md      # The Forge: validation
  agent-curator.md        # The Forge: integration
```

**Total Global Agents**: 7 (1 Consultant + 6 Forge)

These are copied into `.claude/agents/` after every team swap.

### The Forge

The Forge is a 6-agent meta-team for creating and maintaining other teams:

| Agent | Purpose |
|-------|---------|
| Agent Designer | Creates team specs and role definitions |
| Prompt Architect | Writes agent system prompts |
| Workflow Engineer | Designs orchestration and commands |
| Platform Engineer | Implements roster infrastructure |
| Eval Specialist | Validates teams before shipment |
| Agent Curator | Integrates and syncs Consultant |

**Workflow**: Designer → Prompt Architect → Workflow Engineer → Platform → Eval → Curator

---

## File Locations

| Component | Location |
|-----------|----------|
| Team packs | `~/Code/roster/teams/{pack}/` |
| Active agents | `.claude/agents/` |
| Global agents | `.claude/global-agents/` |
| Commands | `.claude/commands/` |
| Skills | `.claude/skills/` |
| Sessions | `.claude/sessions/` |
| Knowledge | `.claude/knowledge/` |
| Hooks | `.claude/hooks/` |

---

## Quick Start Patterns

### "I want to build a feature"

```bash
/10x                    # Switch to development team
/start "Feature name"   # Initialize session
# Follow the workflow: requirements → design → build → test
/wrap                   # Finalize session
/pr                     # Create pull request
```

### "I want to fix a bug"

```bash
/hotfix                 # Fast-track bug fix workflow
```

### "I want to improve code quality"

```bash
/hygiene                # Switch to hygiene team
/task "Code audit"      # Start quality assessment
```

### "I need documentation"

```bash
/docs                   # Switch to doc team
/task "Document API"    # Start documentation
```

### "I'm not sure what to do"

```bash
/consult                # Get guidance
/consult "describe your goal"  # Get recommendations
```

### "I want to create a new team"

```bash
/forge                  # See The Forge overview
/new-team my-team       # Start team creation workflow
```

### "I want to validate a team"

```bash
/validate-team security-pack   # Run full validation
/eval-agent architect          # Test single agent
```

### "I want to sync this project with skeleton_claude"

```bash
/sync status                   # Check if updates available
/sync                          # Pull latest updates
/sync diff                     # See what changed
```

### "I want to set up a new project with the ecosystem"

```bash
# From terminal (not in Claude)
cd ~/Code/my-new-project
~/Code/skeleton_claude/cem init
```
