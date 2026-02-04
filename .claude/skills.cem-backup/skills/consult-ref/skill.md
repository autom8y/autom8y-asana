---
name: consult-ref
description: "Ecosystem guidance and navigation. Matches intent to teams/workflows. Triggers: /consult, guidance, what team, which workflow, how do I."
---

# /consult - Ecosystem Guidance & Navigation

> **Category**: Meta/Navigation | **Phase**: Decision Support

## Purpose

The `/consult` command provides ecosystem guidance, matches user intent to appropriate teams and workflows, and delivers actionable command-flows. It serves as the meta-navigator for the entire Claude Code ecosystem.

This command acts as an intelligent routing layer that:
- Understands user goals and translates them into concrete workflows
- Recommends the right team for the job
- Provides step-by-step command sequences
- Offers alternative approaches when multiple valid paths exist
- Surfaces pre-built playbooks for common scenarios

---

## Usage

```bash
# General ecosystem help
/consult

# Intent-based guidance
/consult "I need to add user authentication"
/consult "improve code quality"
/consult "my app is slow"

# Load curated playbook
/consult --playbook=new-feature
/consult --playbook=bug-fix
/consult --playbook=security-review

# Display teams reference
/consult --team

# Display commands reference
/consult --commands
```

---

## Behavior

### Mode 1: No Arguments (General Help)

When invoked without arguments, `/consult` provides ecosystem overview:

1. **Summarize Current State**
   - Active team (from `.claude/ACTIVE_TEAM`)
   - Active session (from `.claude/sessions/`)
   - Git branch and status
   - Current complexity level (if in session)

2. **Display Team Roster**
   - Show all 9 teams with brief descriptions
   - Highlight quick-switch commands
   - Indicate which team is currently active

3. **List Common Starting Points**
   Based on typical user goals:
   - Feature development → `/10x` + `/start`
   - Documentation → `/docs` + `/task`
   - Code quality → `/hygiene` + `/task`
   - Bug fixes → `/hotfix`
   - Research/exploration → `/rnd` + `/spike`

4. **Point to Playbook Library**
   - Mention available curated playbooks
   - Show how to list playbooks: `/consult --playbook=`
   - Encourage exploration for complex workflows

**Example Output:**

```
=== Ecosystem Status ===
Active Team: 10x-dev-pack (5 agents)
Session: ACTIVE - "Add authentication" (MODULE complexity)
Git: feature/auth-system (clean)

=== Available Teams ===
  10x-dev-pack       /10x          Full feature development
  doc-team-pack      /docs         Documentation workflows
  hygiene-pack       /hygiene      Code quality & refactoring
  debt-triage-pack   /debt         Technical debt management
  sre-pack           /sre          Operations & reliability
  security-pack      /security     Security assessment
  intelligence-pack  /intelligence Analytics & research
  rnd-pack           /rnd          Exploration & prototyping
  strategy-pack      /strategy     Business analysis

=== Common Starting Points ===
  Build a feature:     /10x && /start "Feature name"
  Fix a bug:           /hotfix
  Improve quality:     /hygiene && /task "Audit scope"
  Write docs:          /docs && /task "Documentation goal"
  Research something:  /rnd && /spike "Investigation"

Need specific guidance? Try: /consult "describe your goal"
```

---

### Mode 2: Query Provided (Intent Matching)

When given a natural language query, `/consult` acts as intelligent router:

1. **Parse User Intent**
   - Extract goal, scope, constraints
   - Identify key verbs (add, fix, improve, deploy, etc.)
   - Recognize domain keywords (auth, performance, tests, docs)

2. **Match to Team + Workflow**
   - Consult `~/.claude/knowledge/consultant/routing/intent-patterns.md`
   - Determine appropriate team pack
   - Select workflow type (task, sprint, hotfix, spike)
   - Estimate complexity level

3. **Generate Command-Flow**
   - Provide step-by-step commands
   - Include decision points and checkpoints
   - Note expected artifacts at each phase
   - Highlight handoff patterns if multi-agent

4. **Offer Alternatives**
   - Present other valid approaches if they exist
   - Explain tradeoffs between options
   - Suggest when to escalate complexity

**Example Interaction:**

```bash
/consult "I need to add user authentication"
```

**Output:**

```
=== Assessment ===
Goal: Implement authentication system
Domain: Security + Backend
Estimated Complexity: MODULE to SERVICE level

=== Recommendation ===
Team: 10x-dev-pack
Workflow: /task (sequential phases)
Complexity: MODULE

Rationale: Authentication is a well-scoped feature requiring
requirements, design, implementation, and security validation.

=== Command-Flow ===
1. Switch to development team:
   /10x

2. Start session with appropriate complexity:
   /start "Add user authentication" --complexity=MODULE

3. Requirements phase (auto-starts):
   Requirements Analyst will create PRD covering:
   - Authentication methods (password, OAuth, etc.)
   - Session management approach
   - Security requirements

4. Design phase:
   /handoff architect
   Architect produces TDD with:
   - Database schema for users/sessions
   - API endpoint designs
   - Security controls (hashing, tokens)

5. Implementation phase:
   /handoff engineer
   Principal Engineer implements:
   - User model and migrations
   - Auth endpoints and middleware
   - Session handling

6. Validation phase:
   /handoff qa
   QA tests:
   - Authentication flows
   - Security edge cases
   - Token expiry, logout, etc.

7. Finalize:
   /wrap
   Creates summary and runs quality gates

8. Create PR:
   /pr

=== Alternatives ===
- If urgent/hotfix context: Use /hotfix instead (skips full workflow)
- If security-focused review needed: Start with /security team
- If this is part of larger initiative: Consider /sprint for multi-task coordination

Next step: Run `/10x` to switch teams
```

---

### Mode 3: Playbook Loading (`--playbook=NAME`)

Curated playbooks provide pre-built workflows for common scenarios:

1. **Check Playbook Exists**
   - Look in `~/.claude/knowledge/consultant/playbooks/curated/{NAME}.md`
   - If not found, list available playbooks

2. **Load and Present Playbook**
   - Show full workflow with phases
   - Inject current context (team, session, git state)
   - Highlight where user is in the workflow (if applicable)

3. **Provide Entry Point**
   - Suggest first command to execute
   - Note prerequisites or setup needed

**Available Playbooks:**

| Playbook | Use Case |
|----------|----------|
| `new-feature` | Full feature development (requirements through deployment) |
| `bug-fix` | Rapid bug diagnosis and fix |
| `code-audit` | Comprehensive code quality assessment |
| `documentation-refresh` | Update or create documentation |
| `performance-optimization` | Profile, analyze, and optimize performance |
| `security-review` | Security audit and remediation |
| `tech-debt-sprint` | Planned technical debt reduction |
| `incident-response` | Production incident handling |

**Example:**

```bash
/consult --playbook=new-feature
```

**Output:**

```
=== Playbook: New Feature Development ===

This workflow guides you through full feature lifecycle:
Requirements → Design → Implementation → Testing → Deployment

Current Context:
  Team: none (will switch to 10x-dev-pack)
  Session: none (will start new)
  Branch: main

--- Phase 1: Requirements ---
Command: /10x && /start "Feature name" --complexity=MODULE
Agent: Requirements Analyst
Output: PRD.md with acceptance criteria

--- Phase 2: Design ---
Command: /handoff architect
Agent: Architect
Output: TDD.md, ADRs for key decisions

--- Phase 3: Implementation ---
Command: /handoff engineer
Agent: Principal Engineer
Output: Production code, tests

--- Phase 4: Validation ---
Command: /handoff qa
Agent: QA/Adversary
Output: Test results, edge case validation

--- Phase 5: Finalize ---
Command: /wrap
Output: Session summary

--- Phase 6: Deploy ---
Command: /pr
Output: Pull request with full context

Next step: /10x && /start "Your feature name"
```

---

### Mode 4: Team Reference (`--team`)

Display complete team reference table:

```
=== All Teams (9 Total) ===

| Team              | Command       | Agents | Best For                           |
|-------------------|---------------|--------|------------------------------------|
| 10x-dev-pack      | /10x          | 5      | Full feature development lifecycle |
| doc-team-pack     | /docs         | 4      | Documentation, technical writing   |
| hygiene-pack      | /hygiene      | 4      | Code quality, refactoring          |
| debt-triage-pack  | /debt         | 3      | Technical debt prioritization      |
| sre-pack          | /sre          | 4      | Operations, reliability            |
| security-pack     | /security     | 4      | Security assessment, compliance    |
| intelligence-pack | /intelligence | 4      | Analytics, A/B testing, research   |
| rnd-pack          | /rnd          | 4      | Exploration, prototyping           |
| strategy-pack     | /strategy     | 4      | Market research, business analysis |

Total: 41 agents across all teams

Use /team <name> or quick-switch commands (e.g., /10x) to activate.
```

---

### Mode 5: Commands Reference (`--commands`)

Display all commands categorized by domain:

```
=== Command Registry (31 Total) ===

--- Session Lifecycle (6) ---
/start              Initialize new work session
/park               Pause session, preserve state
/continue           Resume parked session
/handoff            Transfer work between agents
/wrap               Finalize session, run quality gates
/worktree           Manage isolated worktrees

--- Team Management (10) ---
/team               Switch team or list available
/10x                Quick switch to 10x-dev-pack
/docs               Quick switch to doc-team-pack
/hygiene            Quick switch to hygiene-pack
/debt               Quick switch to debt-triage-pack
/sre                Quick switch to sre-pack
/security           Quick switch to security-pack
/intelligence       Quick switch to intelligence-pack
/rnd                Quick switch to rnd-pack
/strategy           Quick switch to strategy-pack

--- Development Workflows (4) ---
/task               Single task through full lifecycle
/sprint             Multi-task sprint orchestration
/hotfix             Rapid fix for urgent issues
/spike              Time-boxed research (no production code)

--- Operations (5) ---
/architect          Design phase only (TDD + ADRs)
/build              Implementation phase only
/qa                 Validation phase only
/pr                 Create pull request
/code-review        Structured code review

--- Meta/Navigation (2) ---
/consult            Ecosystem guidance (you are here)
/sync               Sync project with skeleton_claude

--- Meta/Factory (4) ---
/forge              The Forge overview
/new-team           Create new team pack
/validate-team      Validate existing team
/eval-agent         Test single agent
```

---

## Knowledge Sources

The Consultant draws from structured knowledge base:

| Source | Purpose |
|--------|---------|
| `ecosystem-map.md` | Complete system overview (teams, commands, workflows) |
| `agent-reference.md` | All 41+ agents with roles and capabilities |
| `command-reference.md` | Complete command catalog with examples |
| `routing/intent-patterns.md` | Natural language → team/workflow mapping |
| `team-profiles/*.md` | Deep knowledge of each team's strengths |
| `playbooks/curated/*.md` | Pre-built workflows for common scenarios |

These sources are maintained in `~/.claude/knowledge/consultant/` and kept in sync with the ecosystem.

---

## Response Format

All `/consult` responses follow this 4-part structure:

### 1. Assessment
What you understand the user needs:
- Goal extraction
- Domain identification
- Scope estimation
- Constraint recognition

### 2. Recommendation
Which team/workflow fits best:
- Team name and quick-switch command
- Workflow type (task/sprint/hotfix/spike)
- Complexity level recommendation
- Rationale for the choice

### 3. Command-Flow
Step-by-step commands to execute:
- Numbered sequence of commands
- Expected artifacts at each step
- Decision points and checkpoints
- Agent handoff patterns

### 4. Alternatives
Other valid approaches (if applicable):
- Alternative teams or workflows
- Tradeoffs between options
- When to escalate or simplify
- Edge cases or special considerations

---

## Teams Quick Reference

| Team | Command | Complexity Levels | Use When |
|------|---------|-------------------|----------|
| **10x-dev-pack** | `/10x` | SCRIPT, MODULE, SERVICE, PLATFORM | Building features, fixing complex bugs |
| **doc-team-pack** | `/docs` | PAGE, SECTION, SITE | Writing or updating documentation |
| **hygiene-pack** | `/hygiene` | SPOT, MODULE, CODEBASE | Refactoring, code quality improvements |
| **debt-triage-pack** | `/debt` | QUICK, AUDIT | Assessing and prioritizing technical debt |
| **sre-pack** | `/sre` | TASK, PROJECT, PLATFORM | Operational work, reliability, monitoring |
| **security-pack** | `/security` | PATCH, FEATURE, SYSTEM | Security reviews, vulnerability fixes |
| **intelligence-pack** | `/intelligence` | METRIC, FEATURE, INITIATIVE | Analytics, A/B tests, data research |
| **rnd-pack** | `/rnd` | SPIKE, EVALUATION, MOONSHOT | Exploration, prototyping, research |
| **strategy-pack** | `/strategy` | TACTICAL, STRATEGIC, TRANSFORMATION | Business planning, market research |

---

## Example Use Cases

### Example 1: Feature Development

```bash
/consult "add shopping cart to ecommerce site"
```

**Response:**
- Assessment: New feature, ecommerce domain, MODULE/SERVICE complexity
- Recommendation: 10x-dev-pack, /task workflow, MODULE complexity
- Command-Flow: `/10x` → `/start "Shopping cart" --complexity=MODULE` → agent handoffs
- Alternatives: Consider `/intelligence` team if A/B testing cart UX needed

---

### Example 2: Performance Issue

```bash
/consult "my API responses are too slow"
```

**Response:**
- Assessment: Performance optimization, backend focus, existing system
- Recommendation: 10x-dev-pack for implementation OR intelligence-pack for profiling first
- Command-Flow: Option A (immediate fix) vs Option B (data-driven)
- Alternatives: `/sre` team if operational/infrastructure issue

---

### Example 3: Documentation Needed

```bash
/consult "need to document the API endpoints"
```

**Response:**
- Assessment: Documentation task, API domain, SECTION complexity
- Recommendation: doc-team-pack, /task workflow
- Command-Flow: `/docs` → `/task "API documentation" --complexity=SECTION`
- Alternatives: None, straightforward doc work

---

### Example 4: Code Smells

```bash
/consult "this module has too many code smells"
```

**Response:**
- Assessment: Code quality, refactoring need, MODULE complexity
- Recommendation: hygiene-pack, /task workflow
- Command-Flow: `/hygiene` → `/task "Refactor module X" --complexity=MODULE`
- Alternatives: If technical debt assessment needed first, start with `/debt`

---

### Example 5: Production Incident

```bash
/consult "production is down, users can't login"
```

**Response:**
- Assessment: Urgent production issue, security/availability concern
- Recommendation: /hotfix for immediate fix, then /sre for root cause
- Command-Flow: `/hotfix` → diagnose → fix → deploy → `/sre` for postmortem
- Alternatives: If security breach suspected, involve `/security` team

---

## Integration with Workflows

The `/consult` command is workflow-aware:

- **Before session**: Recommends which team + workflow to start
- **During session**: Suggests next phase or agent handoff
- **After session**: Points to follow-up work (PR, deployment, monitoring)
- **Blocked**: Offers alternative approaches or team escalation

---

## Success Criteria

A good `/consult` response:
- Clearly understands user intent (Assessment)
- Recommends appropriate team and workflow (Recommendation)
- Provides actionable, copy-pasteable commands (Command-Flow)
- Explains why this approach fits (Rationale)
- Offers alternatives when multiple valid paths exist

---

## Related Commands

| Command | Relationship |
|---------|--------------|
| `/team` | Executes team switches recommended by /consult |
| `/start` | Begins sessions recommended by /consult |
| `/task`, `/sprint`, `/hotfix`, `/spike` | Executes workflows recommended by /consult |
| `/forge` | Meta-level team creation (vs /consult for navigation) |

---

## Notes

### Consultant Agent

The `/consult` command is powered by the **Consultant** agent, a global singleton at `~/.claude/agents/consultant.md`. This agent:
- Persists across team swaps
- Has deep knowledge of all teams and workflows
- Uses Claude Opus 4.5 for complex reasoning
- Accesses comprehensive knowledge base

### When to Use /consult

Use `/consult` when:
- Starting work and unsure which team to use
- Stuck and need alternative approaches
- Want to see all options before committing
- Learning the ecosystem and its capabilities
- Need a quick reference for teams or commands

**Don't use** for:
- Executing work (use workflow commands instead)
- Creating new teams (use `/forge` commands)
- Switching teams (use `/team` or quick-switch commands)

---

## Implementation Notes

The `/consult` command:
1. Loads context via SessionStart hook (automatic)
2. Reads user arguments via `$ARGUMENTS` variable
3. Uses Task tool with Consultant agent for reasoning
4. Returns structured guidance following 4-part format
5. Does not modify state (read-only navigation)

**Model**: Claude Opus 4.5 (for superior reasoning and planning)
**Tools**: Bash, Read, Grep, Glob, Task (exploration only)

---

## Maintenance

This skill is kept in sync with:
- Team roster changes (new teams, team updates)
- Command registry updates (new commands, deprecations)
- Playbook library (new curated workflows)
- Intent patterns (improved routing heuristics)

When ecosystem changes, update:
1. This skill reference (SKILL.md)
2. Consultant knowledge base (`~/.claude/knowledge/consultant/`)
3. Consultant agent prompt (`~/.claude/agents/consultant.md`)
