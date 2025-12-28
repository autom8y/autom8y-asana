---
name: forge-ref
description: "The Forge meta-team for creating agent teams. Global singleton. Triggers: /forge, new team, create agents, agent factory, team creation."
---

# The Forge - Agent Factory Team

> **Category**: Meta-Team | **Scope**: Global Singleton

## Purpose

The Forge is the meta-team that creates and maintains all other agent teams. It's a specialized 6-agent pipeline that takes team concepts from initial requirements through design, implementation, testing, and deployment to the roster.

**Key characteristics:**
- **Global singleton**: Always available, never swapped out
- **Self-contained**: Agents coordinate without external dependencies
- **Quality-gated**: Every team passes validation before roster entry
- **Standardized**: Enforces consistent agent and workflow patterns

The Forge produces teams as roster packs: directories containing agent .md files and workflow.yaml, ready to be loaded via `swap-team.sh`.

---

## Usage

### Display Forge Overview

```bash
/forge
```

Shows: Team purpose, agent list, commands, complexity levels

### Show Detailed Agent Information

```bash
/forge --agents
```

Shows: Full agent table with models, responsibilities, handoffs

### Show Workflow Pipeline

```bash
/forge --workflow
```

Shows: ASCII diagram of agent flow and artifacts produced

### Show Available Commands

```bash
/forge --commands
```

Shows: Team creation, validation, and testing commands

---

## Agents

The Forge operates as a 6-stage pipeline. Each agent has clear inputs, outputs, and handoff criteria.

| Agent | Color | Model | Produces | Upstream From | Downstream To |
|-------|-------|-------|----------|---------------|---------------|
| **Agent Designer** | purple | opus-4-5 | TEAM-SPEC | User requirements | Prompt Architect |
| **Prompt Architect** | cyan | opus-4-5 | Agent .md files | TEAM-SPEC | Workflow Engineer |
| **Workflow Engineer** | green | opus-4-5 | workflow.yaml | Agent .md files | Platform Engineer |
| **Platform Engineer** | orange | sonnet-4-5 | roster/teams/ files | workflow.yaml | Eval Specialist |
| **Eval Specialist** | red | opus-4-5 | eval-report | Deployed team | Agent Curator |
| **Agent Curator** | blue | sonnet-4-5 | Roster entry | eval-report | (terminal) |

### Agent Designer (purple)

**Purpose**: Translate user requirements into concrete agent specifications

**Inputs**:
- User's team concept description
- Complexity level (PATCH/TEAM/ECOSYSTEM)
- Domain requirements

**Process**:
1. Ask clarifying questions about team scope
2. Define agent roles and responsibilities
3. Establish contracts between agents
4. Map workflow phases to agents
5. Produce TEAM-SPEC document

**Outputs**:
- `TEAM-SPEC.md` with agent roster, contracts, workflow outline

**Handoff to Prompt Architect when**:
- All agent roles clearly defined
- Contracts established between agents
- Workflow phases mapped to roles
- User approves agent roster

---

### Prompt Architect (cyan)

**Purpose**: Transform TEAM-SPEC into working agent .md files

**Inputs**:
- TEAM-SPEC.md from Agent Designer
- Agent schema (frontmatter format)
- System prompt template (11 sections)

**Process**:
1. For each agent in TEAM-SPEC:
   - Write frontmatter (name, description, tools, model, color)
   - Write 11-section system prompt
   - Define handoff criteria
   - Specify success criteria
2. Ensure consistent tone and terminology
3. Validate schema compliance

**Outputs**:
- N x `{agent-name}.md` files (one per agent)
- Agent files follow standard 11-section structure

**Handoff to Workflow Engineer when**:
- All agents have complete .md files
- Schema validation passes
- Handoff chains are consistent
- Tone and terminology unified

---

### Workflow Engineer (green)

**Purpose**: Orchestrate agents via workflow.yaml

**Inputs**:
- Agent .md files from Prompt Architect
- TEAM-SPEC workflow outline
- Workflow schema

**Process**:
1. Design workflow.yaml structure
2. Define entry points and phases
3. Map complexity levels to agent sequences
4. Create user-facing commands
5. Validate workflow schema

**Outputs**:
- `workflow.yaml` with phases, commands, complexity levels
- Command files (if custom commands needed)

**Handoff to Platform Engineer when**:
- workflow.yaml schema valid
- Entry points defined
- Commands documented
- Complexity levels mapped

---

### Platform Engineer (orange)

**Purpose**: Deploy team to roster infrastructure

**Inputs**:
- Agent .md files from Prompt Architect
- workflow.yaml from Workflow Engineer
- Team name from TEAM-SPEC

**Process**:
1. Create roster directory structure
2. Deploy agent files to agents/ subdirectory
3. Deploy workflow.yaml to team root
4. Set correct permissions
5. Test swap-team.sh integration

**Outputs**:
- `~/Code/roster/teams/{team-name}/` directory
- Agents and workflow properly deployed
- Integration test passing

**Handoff to Eval Specialist when**:
- Team directory exists in roster
- swap-team.sh loads team successfully
- .claude/ACTIVE_TEAM shows correct name
- .claude/agents/ populated correctly

---

### Eval Specialist (red)

**Purpose**: Validate team quality before roster entry

**Inputs**:
- Deployed team from Platform Engineer
- Team name
- TEAM-SPEC success criteria

**Process**:
1. Schema validation (frontmatter, workflow)
2. Functional testing (swap, agent invocation)
3. Contract verification (handoff chains)
4. Documentation completeness
5. Edge case testing

**Outputs**:
- `eval-report.md` with pass/fail status
- Defect list (if any failures)
- Recommendation (approve/reject/fix)

**Handoff to Agent Curator when**:
- All validation tests pass
- No critical defects found
- Documentation complete
- Team ready for production use

---

### Agent Curator (blue)

**Purpose**: Integrate team into roster and documentation

**Inputs**:
- eval-report from Eval Specialist
- Deployed team pack
- Team metadata

**Process**:
1. Verify team pack integrity
2. Update roster documentation
3. Create team quick-switch command (if requested)
4. Document usage examples
5. Version team pack

**Outputs**:
- Roster entry documented
- Optional quick-switch command
- Usage examples
- Version tag

**Terminal agent**: No further handoffs after completion

---

## Workflow

```
┌─────────────────┐
│ User: /new-team │
│   "auth-pack"   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT DESIGNER (purple)                                         │
│ • Clarify requirements                                          │
│ • Define agent roles                                            │
│ • Establish contracts                                           │
│ Produces: TEAM-SPEC.md                                          │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PROMPT ARCHITECT (cyan)                                         │
│ • Create agent .md files                                        │
│ • Write 11-section prompts                                      │
│ • Validate schema                                               │
│ Produces: N x {agent-name}.md                                   │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ WORKFLOW ENGINEER (green)                                       │
│ • Design workflow.yaml                                          │
│ • Define entry points                                           │
│ • Create commands                                               │
│ Produces: workflow.yaml                                         │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ PLATFORM ENGINEER (orange)                                      │
│ • Create roster directories                                     │
│ • Deploy files                                                  │
│ • Test integration                                              │
│ Produces: ~/Code/roster/teams/{name}/                           │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ EVAL SPECIALIST (red)                                           │
│ • Schema validation                                             │
│ • Functional testing                                            │
│ • Contract verification                                         │
│ Produces: eval-report.md                                        │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENT CURATOR (blue)                                            │
│ • Verify integrity                                              │
│ • Update roster docs                                            │
│ • Create quick-switch                                           │
│ Produces: Roster entry, versioned team pack                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Commands

### /new-team

**Purpose**: Create a complete new team pack from concept to roster

**Usage**:
```bash
/new-team auth-pack
```

**Behavior**:
1. Invokes Agent Designer with team name
2. Follows pipeline through all 6 agents
3. Produces ready-to-use roster pack
4. Reports completion with usage instructions

**Entry Agent**: Agent Designer (purple)

**Complexity**: TEAM (default) or ECOSYSTEM for platform-wide initiatives

**Outputs**:
- Team pack at `~/Code/roster/teams/{name}/`
- eval-report documenting validation
- Usage documentation

---

### /validate-team

**Purpose**: Run validation suite on existing team

**Usage**:
```bash
/validate-team auth-pack
```

**Behavior**:
1. Invokes Eval Specialist directly
2. Runs schema, functional, contract tests
3. Produces eval-report with findings
4. No modifications made to team

**Entry Agent**: Eval Specialist (red)

**Use when**:
- Verifying team after manual edits
- Troubleshooting swap-team.sh issues
- Pre-deployment quality gate
- Periodic health checks

**Outputs**:
- eval-report.md with pass/fail status
- Defect list if issues found

---

### /eval-agent

**Purpose**: Test single agent in isolation

**Usage**:
```bash
/eval-agent requirements-analyst
```

**Behavior**:
1. Invokes Eval Specialist with agent scope
2. Tests schema, invocation, tool usage
3. Validates handoff criteria
4. No team-level workflow testing

**Entry Agent**: Eval Specialist (red)

**Use when**:
- Debugging specific agent issues
- Testing agent modifications
- Verifying new agent before team integration

**Outputs**:
- Agent-specific eval report
- Invocation test results

---

## Complexity Levels

The Forge operates at three complexity tiers:

### PATCH

**Scope**: Single agent modification

**Typical work**:
- Fix agent prompt bugs
- Update tool permissions
- Refine handoff criteria
- Adjust model selection

**Agents involved**: Typically 2-3 (Prompt Architect, Platform Engineer, Eval Specialist)

**Timeline**: Minutes to hours

---

### TEAM

**Scope**: New team with 3-5 agents

**Typical work**:
- Create domain-specific team (auth, docs, testing)
- Full 6-agent pipeline
- Roster integration
- Documentation

**Agents involved**: All 6 agents

**Timeline**: Hours to days

---

### ECOSYSTEM

**Scope**: Multi-team initiative or platform changes

**Typical work**:
- Create team suites (e.g., full microservice lifecycle)
- Update roster infrastructure
- New workflow patterns
- Schema evolution

**Agents involved**: All 6 agents, possibly multiple iterations

**Timeline**: Days to weeks

---

## When to Use

Use The Forge when you need to:

### Create New Teams
- Domain-specific workflows (documentation, testing, deployment)
- Project-specific agent sets
- Experimental agent configurations
- Specialized skill combinations

### Maintain Existing Teams
- Fix broken handoffs
- Update to new agent schema
- Add/remove agents from team
- Refactor workflow.yaml

### Quality Assurance
- Validate team packs before deployment
- Test agent modifications
- Verify roster integrity
- Troubleshoot swap-team.sh issues

### Infrastructure
- Update agent schema
- Evolve workflow patterns
- Improve swap mechanisms
- Standardize team structures

---

## Examples

### Example 1: Create Authentication Team

```bash
/new-team auth-pack
```

**User provides**:
- Team concept: "Authentication and authorization workflows"
- Desired agents: OAuth specialist, Session manager, Security auditor

**Forge pipeline**:
1. Agent Designer produces TEAM-SPEC with 4 agents
2. Prompt Architect creates agent .md files
3. Workflow Engineer designs auth workflow
4. Platform Engineer deploys to roster
5. Eval Specialist validates OAuth flows
6. Agent Curator documents and versions

**Output**:
```
Team 'auth-pack' created successfully!

Location: ~/Code/roster/teams/auth-pack/
Agents: 4 (oauth-specialist, session-manager, security-auditor, integration-tester)
Commands: /auth-flow, /session-debug, /security-scan

To use:
  ~/Code/roster/swap-team.sh auth-pack
```

---

### Example 2: Validate Documentation Team

```bash
/validate-team docs-pack
```

**Eval Specialist tests**:
- Schema compliance for all 5 doc agents
- workflow.yaml structure
- Command invocation (/prd, /tdd, /adr)
- Handoff chains (Writer → Reviewer → Publisher)

**Output**:
```
Validation Report: docs-pack
============================

Schema Validation: PASS
Functional Tests: PASS
Contract Verification: PASS
Documentation: PASS

Status: APPROVED for production use
Defects: 0 critical, 0 major, 2 minor

Minor issues:
  - reviewer-agent.md: Missing example in handoff section
  - workflow.yaml: Typo in phase description

Recommendation: Deploy as-is, address minor issues in next revision
```

---

### Example 3: Test Single Agent

```bash
/eval-agent principal-engineer
```

**Eval Specialist tests**:
- Frontmatter schema
- Tool permissions (Read, Write, Edit, Bash, Grep, Glob)
- Model specification (opus-4-5)
- Handoff criteria to qa-adversary

**Output**:
```
Agent Evaluation: principal-engineer
====================================

Schema: PASS
Invocation Test: PASS
Tool Usage: PASS
Handoff Criteria: PASS

Tested scenarios:
  - Feature implementation from TDD
  - Refactoring with architectural changes
  - Handoff to QA with test plan

Status: READY
```

---

### Example 4: Update Existing Team (PATCH)

```bash
# User discovers bug in handoff criteria
/eval-agent architect
# -> Reveals contract mismatch with principal-engineer

# Invoke Prompt Architect to fix
"Fix handoff contract between architect and principal-engineer in 10x-dev-pack"

# Prompt Architect edits architect.md
# Platform Engineer re-deploys
# Eval Specialist validates fix

/validate-team 10x-dev-pack
# -> PASS
```

---

## Team Integration

### How Forge Agents Coordinate

Unlike regular teams that require user-driven handoffs, Forge agents coordinate automatically:

1. **Entry point**: User invokes command (/new-team, /validate-team)
2. **Pipeline execution**: Each agent completes its phase and hands off to next
3. **Quality gates**: Eval Specialist blocks bad teams from roster
4. **Terminal state**: Agent Curator completes with no further handoffs

### Forge vs Regular Teams

| Aspect | Regular Teams | Forge Team |
|--------|---------------|------------|
| **Scope** | Project/domain work | Team creation/maintenance |
| **Handoffs** | User-driven (`/handoff`) | Automatic pipeline |
| **Availability** | Swapped via roster | Always available (singleton) |
| **Invocation** | Via active team | Via `/forge` commands |
| **Output** | Code, docs, artifacts | Team packs (agents + workflow) |

---

## Forge Agent Schemas

### Agent Frontmatter

All Forge-produced agents include:

```yaml
---
name: agent-name
description: "Brief description (triggers, keywords)"
tools: [Read, Write, Edit, Bash, Grep, Glob, Task, TodoWrite]
model: claude-opus-4-5 | claude-sonnet-4-5
color: purple | cyan | green | orange | red | blue | yellow | magenta
---
```

### Agent System Prompt (11 Sections)

1. **Role Definition**: Agent identity and purpose
2. **Core Responsibilities**: Primary duties and scope
3. **Position in Workflow**: Upstream/downstream context
4. **Domain Authority**: Decision rights and escalation rules
5. **How You Work**: Step-by-step process, phases
6. **What You Produce**: Artifacts table
7. **Handoff Criteria**: When to pass to next agent
8. **The Acid Test**: Single question to validate readiness
9. **Skills Reference**: Related skills to activate
10. **Cross-Team Notes**: Edge cases and learnings
11. **Anti-Patterns to Avoid**: Common mistakes and warnings

### Workflow Schema

```yaml
name: team-name
workflow_type: linear | branching | cyclic
entry_point: agent-name
phases:
  - name: phase-name
    agent: agent-name
    produces: artifact-type
    handoff_to: next-agent-name
complexity_levels:
  - level: PATCH | MODULE | SERVICE | PLATFORM
    entry: agent-name
    phases: [phase-list]
```

---

## State and Artifacts

### Forge Working Directory

Forge operations create temporary artifacts:

```
.forge/
├── TEAM-SPEC.md           # Agent Designer output
├── agents/                # Prompt Architect output
│   ├── agent-1.md
│   ├── agent-2.md
│   └── agent-3.md
├── workflow.yaml          # Workflow Engineer output
└── eval-report.md         # Eval Specialist output
```

### Roster Output

Final team pack location:

```
~/Code/roster/teams/{team-name}/
├── agents/
│   ├── agent-1.md
│   ├── agent-2.md
│   └── agent-3.md
└── workflow.yaml
```

---

## Quality Standards

### Schema Validation

Every team must pass:
- Frontmatter structure (YAML valid, required fields present)
- Workflow structure (entry point exists, phases reference valid agents)
- File naming (kebab-case, .md extension)
- Tool permissions (only allowed tools listed)

### Functional Testing

Every team must demonstrate:
- swap-team.sh loads without errors
- .claude/ACTIVE_TEAM updates correctly
- .claude/agents/ populated with correct files
- Commands invoke correct agents

### Contract Verification

Every team must show:
- Handoff chains are complete (no dangling agents)
- Handoff criteria are testable
- Success criteria are clear
- Artifacts are documented

---

## Troubleshooting

### Team Won't Load (swap-team.sh fails)

**Check**:
1. Team directory exists: `ls ~/Code/roster/teams/{name}`
2. agents/ subdirectory exists
3. At least one .md file in agents/
4. workflow.yaml present

**Fix**: Run `/validate-team {name}` to diagnose

### Agent Invocation Fails

**Check**:
1. Agent name matches filename (without .md)
2. Frontmatter name field matches filename
3. Agent in .claude/agents/ after swap

**Fix**: Run `/eval-agent {name}` for detailed report

### Handoff Chain Broken

**Check**:
1. Each agent's handoff_to references valid agent
2. Entry point defined in workflow.yaml
3. Circular dependencies avoided

**Fix**: Review eval-report, update handoff criteria

---

## Related Documentation

- `10x-workflow` skill - Regular team coordination patterns
- `team-development` skill - Team pack creation standards
- `standards` skill - File naming and schema conventions
- `~/Code/roster/swap-team.sh` - Team loader implementation
- `.claude/agents/` - Active agent directory

---

## Notes

### Why a Meta-Team?

Creating quality agent teams requires:
- Consistent schema enforcement
- Multi-phase quality gates
- Infrastructure integration
- Documentation standards

A dedicated meta-team ensures:
- Repeatability (same process every time)
- Quality (validation gates prevent bad teams)
- Maintainability (centralized team creation logic)
- Scalability (easy to create many teams)

### Forge as Singleton

Unlike regular teams (swapped via roster), Forge is always available because:
- Team creation can't require an active team
- Validation must work regardless of current team
- Infrastructure must be accessible at all times

### Self-Hosting

The Forge team itself was created by The Forge (bootstrapped manually, then self-hosted). Changes to Forge agents follow the same pipeline as any other team.

---

## Quick Reference

| Task | Command | Entry Agent |
|------|---------|-------------|
| Create new team | `/new-team <name>` | Agent Designer |
| Validate team | `/validate-team <name>` | Eval Specialist |
| Test agent | `/eval-agent <name>` | Eval Specialist |
| Show Forge info | `/forge` | (display only) |
| Show agents | `/forge --agents` | (display only) |
| Show workflow | `/forge --workflow` | (display only) |

---

**Last updated**: 2025-12-25
**Forge version**: 1.0.0
**Schema version**: 1.0.0
