# Command Reference

> Quick reference for all 30 slash commands

---

## Session Lifecycle

### /start
**Initialize new work session**

```bash
/start "initiative name" [--complexity=LEVEL] [--team=PACK]
```

- Creates SESSION_CONTEXT.md
- Switches team if specified
- Invokes entry point agent

### /park
**Pause session, preserve state**

```bash
/park
```

- Saves current progress to SESSION_CONTEXT
- Marks session as PARKED
- Safe to close terminal

### /continue
**Resume parked session**

```bash
/continue [session-id]
```

- Restores context from SESSION_CONTEXT
- Resumes from last phase
- Picks up where you left off

### /handoff
**Transfer work between agents**

```bash
/handoff <agent-name> ["context message"]
```

- Generates handoff note
- Updates session context
- Invokes target agent

### /wrap
**Finalize session**

```bash
/wrap
```

- Runs quality gates
- Generates session summary
- Archives SESSION_CONTEXT

---

## Team Management

### /team
**Switch team or list available**

```bash
/team                    # List all teams
/team <pack-name>        # Switch to team
```

### Quick Switches

| Command | Switches To |
|---------|-------------|
| `/10x` | 10x-dev-pack |
| `/docs` | doc-team-pack |
| `/hygiene` | hygiene-pack |
| `/debt` | debt-triage-pack |
| `/sre` | sre-pack |
| `/security` | security-pack |
| `/intelligence` | intelligence-pack |
| `/rnd` | rnd-pack |
| `/strategy` | strategy-pack |

All quick switches:
- Invoke `~/Code/roster/swap-team.sh`
- Show team roster after switch
- Ready for workflow commands

---

## Development Workflows

### /task
**Single task full lifecycle**

```bash
/task "task description" [--complexity=LEVEL]
```

Most common workflow. Progresses through all team phases.

### /sprint
**Multi-task sprint orchestration**

```bash
/sprint "sprint goal"
```

- Breaks goal into multiple tasks
- Coordinates across tasks
- Tracks sprint progress

### /hotfix
**Rapid fix for urgent issues**

```bash
/hotfix "issue description"
```

- Skip PRD (unless complex)
- Minimal TDD
- Focus: diagnose → fix → test → ship

### /spike
**Time-boxed research**

```bash
/spike "research question" [--timebox=DURATION]
```

- NO production code
- Answer: "Can we do X? How?"
- Produces feasibility report

---

## Operations

### /architect
**Design phase only**

```bash
/architect
```

- Produces TDD and ADRs
- No implementation
- For design approval before coding

### /build
**Implementation phase only**

```bash
/build
```

- Assumes design exists
- Produces code and tests
- For coding after design approval

### /qa
**Validation phase only**

```bash
/qa
```

- Runs QA adversary
- Tests completed work
- Produces test report

### /pr
**Create pull request**

```bash
/pr [--draft]
```

- Analyzes commit history
- Generates PR description
- Creates via `gh pr create`

### /code-review
**Structured code review**

```bash
/code-review [PR-number or files]
```

- Categorized feedback
- Security considerations
- Actionable suggestions

---

## Meta/Navigation

### /consult
**Ecosystem guidance**

```bash
/consult                           # General help
/consult "goal description"        # Get recommendations
/consult --playbook=NAME           # Load curated playbook
/consult --team                    # List all teams
/consult --commands                # List all commands
```

### /sync
**Sync with skeleton_claude ecosystem**

```bash
/sync                    # Pull latest updates
/sync init               # Initialize project (first time)
/sync status             # Show sync state and version
/sync diff               # Show differences with skeleton
/sync --force            # Force overwrite local changes
/sync --dry-run          # Preview without applying
```

- Manages ecosystem synchronization
- Physical copy with intelligent merge
- Tracks versions via git commits
- Preserves project-specific settings

---

## Meta/Factory (The Forge)

### /forge
**The Forge overview and help**

```bash
/forge                    # Display Forge overview
/forge --agents           # List all Forge agents
/forge --workflow         # Show Forge workflow
/forge --commands         # List Forge commands
```

### /new-team
**Create new team pack**

```bash
/new-team <name>                           # Create new team (TEAM complexity)
/new-team <name> --complexity=PATCH        # Single agent modification
/new-team <name> --complexity=ECOSYSTEM    # Multi-team initiative
```

Invokes Agent Designer → full Forge workflow.

### /validate-team
**Validate existing team**

```bash
/validate-team <name>           # Run full validation
/validate-team <name> --verbose # Detailed output
```

Invokes Eval Specialist for validation.

### /eval-agent
**Test single agent**

```bash
/eval-agent <name>                     # Test in active team
/eval-agent <name> --team=<pack>       # Test in specific team
/eval-agent <name> --adversarial       # Include adversarial prompts
```

Invokes Eval Specialist for agent testing.

---

## Command Cheat Sheet

| Goal | Commands |
|------|----------|
| Build feature | `/10x` → `/start` → (workflow) → `/wrap` → `/pr` |
| Fix bug | `/hotfix` |
| Improve quality | `/hygiene` → `/task` |
| Write docs | `/docs` → `/task` |
| Pay tech debt | `/debt` → `/task` |
| Security review | `/security` → `/task` |
| Research | `/spike` or `/rnd` → `/task` |
| A/B test | `/intelligence` → `/task` |
| Strategy planning | `/strategy` → `/task` |
| Get help | `/consult` |
| Create new team | `/forge` → `/new-team` |
| Validate team | `/validate-team` |
| Test agent | `/eval-agent` |
| Sync ecosystem | `/sync` or `/sync status` |
