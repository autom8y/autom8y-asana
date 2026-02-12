---
name: consult-ref
description: "Ecosystem guidance and navigation that matches user intent to appropriate rites and workflows. Use when: unsure which rite to use, need workflow recommendations, or routing guidance. Triggers: /consult, guidance, what rite, which workflow, how do I."
user-invocable: false
---

# /consult - Ecosystem Guidance & Navigation

> **Category**: Meta/Navigation | **Phase**: Decision Support

## Purpose

The `/consult` command provides ecosystem guidance, matches user intent to appropriate rites and workflows, and delivers actionable command-flows. It serves as the meta-navigator for the entire Claude Code ecosystem.

This command acts as an intelligent routing layer that:
- Understands user goals and translates them into concrete workflows
- Recommends the right rite for the job
- Provides step-by-step command sequences
- Offers alternative approaches when multiple valid paths exist
- Surfaces pre-built playbooks for common scenarios

## Cognitive Load Absorber Role

`/consult` is the designated entry point for users who are confused, overwhelmed, or unsure where to start. When users don't know which rite, workflow, or command to use, `/consult` absorbs that cognitive load by:

1. **Parsing natural language intent** - Understanding what the user wants to accomplish
2. **Matching to ecosystem capabilities** - Identifying the right rite, workflow, and complexity
3. **Providing actionable patterns** - Referencing `prompting` skill for exact invocation commands
4. **Explaining the journey** - Referencing `10x-workflow` for phase transitions and quality gates

**Key principle**: Users describe outcomes; `/consult` handles routing complexity.

**Positioning in CLAUDE.md**: "Unsure? Route to `/consult` for guidance."

---

## Mode-Aware Response

When invoked, `/consult` first detects the current execution mode and adapts its response:

### Cross-Cutting Mode Response Template

```
Current Mode: Cross-Cutting

You're in a session without rite orchestration. In this mode:
- Direct execution is valid (Edit/Write allowed)
- Session tracking is active (artifacts, blockers recorded)
- No delegation required

Options:
1. Continue directly - You can implement this yourself
2. Switch to orchestrated mode: /rite <rite-name>
3. Get routing advice - Describe your task and I'll suggest an approach
```

### Native Mode Response Template

```
Current Mode: Native

No session is active. Options:
1. Execute directly - For quick tasks, just do it
2. Start a tracked session: /start "<initiative>"
3. Start with a rite: /start "<initiative>" --rite <pack>
```

### Orchestrated Mode Response

In orchestrated mode, `/consult` provides full rite/workflow routing as described below.

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

# Display rites reference
/consult --rite

# Display commands reference
/consult --commands
```

---

## Behavior

### Mode 1: No Arguments (General Help)

When invoked without arguments, `/consult` provides ecosystem overview:

1. **Summarize Current State**
   - Active rite (from `.claude/ACTIVE_RITE`)
   - Active session (from `.claude/sessions/`)
   - Current complexity level (if in session)

2. **Display Rite Catalog**
   - Show all rites with brief descriptions (dynamic count from rite-discovery)
   - Highlight quick-switch commands
   - Indicate which rite is currently active

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
Active Rite: 10x-dev (5 agents)
Session: ACTIVE - "Add authentication" (MODULE complexity)

=== Available Rites ===
  10x-dev       /10x          Full feature development
  docs      /docs         Documentation workflows
  hygiene       /hygiene      Code quality & refactoring
  debt-triage   /debt         Technical debt management
  sre           /sre          Operations & reliability
  security      /security     Security assessment
  intelligence  /intelligence Analytics & research
  rnd           /rnd          Exploration & prototyping
  strategy      /strategy     Business analysis

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

2. **Match to Rite + Workflow**
   - Consult `~/.claude/knowledge/consultant/routing/intent-patterns.md`
   - Determine appropriate rite
   - Select workflow type (task, sprint, hotfix, spike)
   - Estimate complexity level

3. **Generate Command-Flow**
   - Provide step-by-step commands
   - Include decision points and checkpoints
   - Note expected artifacts at each phase
   - Highlight handoff patterns if multi-agent

3b. **Reference Invocation Patterns**
   - Invoke `prompting` skill mentally to retrieve exact copy-paste patterns
   - Include patterns from `prompting/patterns/*.md` appropriate to workflow type
   - For orchestrator-coordinated workflows, reference `prompting/patterns/discovery.md`
   - For implementation phases, reference `prompting/patterns/implementation.md`

3c. **Reference Workflow Context**
   - Invoke `10x-workflow` skill mentally for phase/gate information
   - Include quality gate expectations from `10x-workflow/quality-gates.md`
   - Reference lifecycle phases from `10x-workflow/lifecycle.md` when explaining journey

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
Rite: 10x-dev
Workflow: /task (sequential phases)
Complexity: MODULE

Rationale: Authentication is a well-scoped feature requiring
requirements, design, implementation, and security validation.

=== Command-Flow ===
1. Switch to development rite:
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
- If security-focused review needed: Start with /security rite
- If this is part of larger initiative: Consider /sprint for multi-task coordination

Next step: Run `/10x` to switch rites
```

---

### Mode 3: Playbook Loading (`--playbook=NAME`)

Curated playbooks provide pre-built workflows for common scenarios:

1. **Check Playbook Exists**
   - Look in `~/.claude/knowledge/consultant/playbooks/curated/{NAME}.md`
   - If not found, list available playbooks

2. **Load and Present Playbook**
   - Show full workflow with phases
   - Inject current context (rite, session, git state)
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
  Rite: none (will sync to 10x-dev)
  Session: none (will start new)

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

### Mode 4: Rite Reference (`--rite`)

Display complete rite reference table:

```
=== All Rites (Dynamic Count from rite-discovery) ===

| Rite              | Command       | Agents | Best For                           |
|-------------------|---------------|--------|------------------------------------|
| 10x-dev      | /10x          | 5      | Full feature development lifecycle |
| docs     | /docs         | 4      | Documentation, technical writing   |
| hygiene      | /hygiene      | 4      | Code quality, refactoring          |
| debt-triage  | /debt         | 3      | Technical debt prioritization      |
| sre          | /sre          | 4      | Operations, reliability            |
| security     | /security     | 4      | Security assessment, compliance    |
| intelligence | /intelligence | 4      | Analytics, A/B testing, research   |
| rnd          | /rnd          | 4      | Exploration, prototyping           |
| strategy     | /strategy     | 4      | Market research, business analysis |

Total: 41 agents across all rites

Use /rite <name> or quick-switch commands (e.g., /10x) to activate.
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

--- Rite Management (10) ---
/rite               Switch rite or list available
/10x                Quick switch to 10x-dev
/docs               Quick switch to docs
/hygiene            Quick switch to hygiene
/debt               Quick switch to debt-triage
/sre                Quick switch to sre
/security           Quick switch to security
/intelligence       Quick switch to intelligence
/rnd                Quick switch to rnd
/strategy           Quick switch to strategy

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
/sync               Sync project with knossos

--- Meta/Factory (4) ---
/forge              The Forge overview
/new-rite           Create new rite
/validate-rite      Validate existing rite
/eval-agent         Test single agent
```

---

## Knowledge Sources

The Consultant draws from structured knowledge base:

| Source | Purpose |
|--------|---------|
| `ecosystem-map.md` | Complete system overview (rites, commands, workflows) |
| `agent-reference.md` | All 41+ agents with roles and capabilities |
| `command-reference.md` | Complete command catalog with examples |
| `routing/intent-patterns.md` | Natural language → rite/workflow mapping |
| `rite-profiles/*.md` | Deep knowledge of each rite's strengths |
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
Which rite/workflow fits best:
- Rite name and quick-switch command
- Workflow type (task/sprint/hotfix/spike)
- Complexity level recommendation
- Rationale for the choice

### 3. Command-Flow
Step-by-step commands to execute:
- Numbered sequence of commands
- Expected artifacts at each step
- Decision points and checkpoints
- Agent handoff patterns
- **Invocation patterns** from `prompting` skill (copy-paste ready)
- **Quality gates** from `10x-workflow` at phase transitions

### 4. Alternatives
Other valid approaches (if applicable):
- Alternative rites or workflows
- Tradeoffs between options
- When to escalate or simplify
- Edge cases or special considerations

---

## Skill Reference Patterns

`/consult` references other skills to provide accurate, current information:

### Referencing prompting Skill

When providing invocation patterns, `/consult` retrieves patterns from:
- `prompting/INDEX.lego.md` - Agent invocation quick reference
- `prompting/patterns/discovery.md` - PRD creation, session initialization
- `prompting/patterns/implementation.md` - TDD, coding, testing
- `prompting/patterns/validation.md` - QA, review gates

**Pattern**: Instead of generating ad-hoc commands, extract from `prompting` skill.

Example transformation:
- WITHOUT skill reference: "Start a session with `/start 'Add auth'`"
- WITH skill reference: "Per `prompting` skill, invoke: `Act as Requirements Analyst. Create PRD for: Add auth`"

### Referencing 10x-workflow Skill

When explaining workflow journeys, `/consult` retrieves context from:
- `10x-workflow/INDEX.lego.md` - Agent routing, complexity calibration
- `10x-workflow/lifecycle.md` - Phase protocol (PLAN -> CLARIFY -> EXECUTE -> VERIFY -> HANDOFF)
- `10x-workflow/quality-gates.md` - Gate criteria per phase

**Pattern**: Include quality gate expectations when describing phase transitions.

Example enhancement:
- WITHOUT: "After PRD, handoff to Architect"
- WITH: "After PRD, quality gate requires: problem clear, scope defined, requirements testable. Then handoff to Architect per `10x-workflow` lifecycle."

### Referencing rite-discovery Skill

When recommending rites, `/consult` retrieves current rite inventory from:
- `rite-discovery` skill for dynamic rite list
- `rite-discovery/schemas/rite-profile.yaml` for profile structure

**Pattern**: Never hardcode rite counts or capabilities; always read from `rite-discovery`.

---

## Rites Quick Reference

| Rite | Command | Complexity Levels | Use When |
|------|---------|-------------------|----------|
| **10x-dev** | `/10x` | SCRIPT, MODULE, SERVICE, PLATFORM | Building features, fixing complex bugs |
| **docs** | `/docs` | PAGE, SECTION, SITE | Writing or updating documentation |
| **hygiene** | `/hygiene` | SPOT, MODULE, CODEBASE | Refactoring, code quality improvements |
| **debt-triage** | `/debt` | QUICK, AUDIT | Assessing and prioritizing technical debt |
| **sre** | `/sre` | TASK, PROJECT, PLATFORM | Operational work, reliability, monitoring |
| **security** | `/security` | PATCH, FEATURE, SYSTEM | Security reviews, vulnerability fixes |
| **intelligence** | `/intelligence` | METRIC, FEATURE, INITIATIVE | Analytics, A/B tests, data research |
| **rnd** | `/rnd` | SPIKE, EVALUATION, MOONSHOT | Exploration, prototyping, research |
| **strategy** | `/strategy` | TACTICAL, STRATEGIC, TRANSFORMATION | Business planning, market research |

---

## Example Use Cases

### Example 1: Feature Development

```bash
/consult "add shopping cart to ecommerce site"
```

**Response:**
- Assessment: New feature, ecommerce domain, MODULE/SERVICE complexity
- Recommendation: 10x-dev, /task workflow, MODULE complexity
- Command-Flow: `/10x` → `/start "Shopping cart" --complexity=MODULE` → agent handoffs
- Alternatives: Consider `/intelligence` rite if A/B testing cart UX needed

---

### Example 2: Performance Issue

```bash
/consult "my API responses are too slow"
```

**Response:**
- Assessment: Performance optimization, backend focus, existing system
- Recommendation: 10x-dev for implementation OR intelligence for profiling first
- Command-Flow: Option A (immediate fix) vs Option B (data-driven)
- Alternatives: `/sre` rite if operational/infrastructure issue

---

### Example 3: Documentation Needed

```bash
/consult "need to document the API endpoints"
```

**Response:**
- Assessment: Documentation task, API domain, SECTION complexity
- Recommendation: docs, /task workflow
- Command-Flow: `/docs` → `/task "API documentation" --complexity=SECTION`
- Alternatives: None, straightforward doc work

---

### Example 4: Code Smells

```bash
/consult "this module has too many code smells"
```

**Response:**
- Assessment: Code quality, refactoring need, MODULE complexity
- Recommendation: hygiene, /task workflow
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
- Alternatives: If security breach suspected, involve `/security` rite

---

## Integration with Workflows

The `/consult` command is workflow-aware:

- **Before session**: Recommends which rite + workflow to start
- **During session**: Suggests next phase or agent handoff
- **After session**: Points to follow-up work (PR, deployment, monitoring)
- **Blocked**: Offers alternative approaches or rite escalation

---

## Success Criteria

A good `/consult` response:
- Clearly understands user intent (Assessment)
- Recommends appropriate rite and workflow (Recommendation)
- Provides actionable, copy-pasteable commands (Command-Flow)
- Explains why this approach fits (Rationale)
- Offers alternatives when multiple valid paths exist

---

## Related Commands

| Command | Relationship |
|---------|--------------|
| `/rite` | Executes rite syncs recommended by /consult |
| `/start` | Begins sessions recommended by /consult |
| `/task`, `/sprint`, `/hotfix`, `/spike` | Executes workflows recommended by /consult |
| `/forge` | Meta-level rite creation (vs /consult for navigation) |

---

## Notes

### Consultant Agent

The `/consult` command is powered by the **Consultant** agent, a global singleton at `~/.claude/agents/consultant.md`. This agent:
- Persists across rite swaps
- Has deep knowledge of all rites and workflows
- Uses Claude Opus 4.5 for complex reasoning
- Accesses comprehensive knowledge base

### When to Use /consult

Use `/consult` when:
- Starting work and unsure which rite to use
- Stuck and need alternative approaches
- Want to see all options before committing
- Learning the ecosystem and its capabilities
- Need a quick reference for rites or commands

**Don't use** for:
- Executing work (use workflow commands instead)
- Creating new rites (use `/forge` commands)
- Switching rites (use `/rite` or quick-switch commands)

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
- Rite catalog changes (new rites, rite updates)
- Command registry updates (new commands, deprecations)
- Playbook library (new curated workflows)
- Intent patterns (improved routing heuristics)

When ecosystem changes, update:
1. This skill reference (INDEX.lego.md)
2. Consultant knowledge base (`~/.claude/knowledge/consultant/`)
3. Consultant agent prompt (`~/.claude/agents/consultant.md`)
