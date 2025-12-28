---
name: team-development
description: |
  Design and implement agent team packs for the roster ecosystem.
  Use when: creating new teams, designing workflows, writing agent prompts,
  integrating with slash commands. Triggers: new team, team pack, workflow design,
  agent creation, roster integration.
---

# Team Development

> Design agent teams that work. Build workflows that flow.

This skill codifies the patterns discovered from building 5 teams (10x-dev-pack, doc-team-pack, hygiene-pack, debt-triage-pack, sre-pack) into reusable templates and decision frameworks.

---

## Quick Reference

| Component | Location | Key Decisions |
|-----------|----------|---------------|
| Team Pack | `~/Code/roster/teams/{name}-pack/` | Name, agent count, domain |
| Workflow | `workflow.yaml` | Phases, complexity levels, entry point |
| Agents | `agents/*.md` | Role, model, color, tools |
| Command | `.claude/commands/{name}.md` | Quick-switch integration |
| Skill | `.claude/skills/{name}-ref/` | Reference documentation |

---

## Team Creation Checklist

```
1. [ ] Define team domain and purpose
2. [ ] Design workflow phases (3-4 typical)
3. [ ] Identify agent roles (3-5 agents)
4. [ ] Create workflow.yaml
5. [ ] Write agent prompts (use template)
6. [ ] Create quick-switch command
7. [ ] Create reference skill
8. [ ] Update COMMAND_REGISTRY.md
9. [ ] Validate with swap-team.sh
10. [ ] **Update Consultant knowledge base** (REQUIRED)
```

> **CRITICAL**: Step 10 ensures the Consultant agent stays canonical. The Consultant is the ecosystem's navigation system - if it has stale data, users will get wrong guidance.

---

## Decision Frameworks

### How Many Agents?

| Count | Team Type | Examples |
|-------|-----------|----------|
| 3 | Focused/specialized | debt-triage-pack |
| 4 | Standard teams | doc-team, hygiene, sre |
| 5 | Full lifecycle | 10x-dev-pack |

### Model Assignment

| Role Type | Model | Examples |
|-----------|-------|----------|
| Orchestration/Senior | opus | architect, qa-adversary, incident-commander |
| Mid-level Specialist | sonnet | tech-writer, platform-engineer, janitor |
| Assessment/Analysis | haiku | code-smeller, debt-collector |

### Color Assignment

| Role Type | Color | Examples |
|-----------|-------|----------|
| Coordination | purple | orchestrator, incident-commander |
| Requirements/Entry | pink/orange | requirements-analyst, observability-engineer |
| Design/Architecture | cyan | architect, platform-engineer |
| Execution/Implementation | green | principal-engineer, janitor, tech-writer |
| Validation/Testing | red | qa-adversary, chaos-engineer |

### Workflow Phases

| Phase Position | Role | Produces |
|----------------|------|----------|
| Entry | Assessment/Discovery | Report, Audit, Requirements |
| Design | Planning/Architecture | Plan, Design, TDD |
| Execute | Implementation | Code, Content, Changes |
| Validate | Testing/Review | Signoff, Report |

---

## Progressive Disclosure

### Glossary
Shared vocabulary for team development:
- [glossary/index.md](glossary/index.md) - Navigation
- [glossary/agents.md](glossary/agents.md) - Agent role types
- [glossary/workflows.md](glossary/workflows.md) - Workflow concepts
- [glossary/artifacts.md](glossary/artifacts.md) - Artifact patterns

### Patterns
Codified design patterns:
- [patterns/team-composition.md](patterns/team-composition.md) - 3/4/5-agent patterns
- [patterns/phase-sequencing.md](patterns/phase-sequencing.md) - Sequential workflow design
- [patterns/complexity-gating.md](patterns/complexity-gating.md) - Complexity levels
- [patterns/command-mapping.md](patterns/command-mapping.md) - Slash command integration

### Templates
Copy-and-fill templates:
- [templates/workflow.yaml.template](templates/workflow.yaml.template) - Workflow config
- [templates/agent.md.template](templates/agent.md.template) - Agent prompt (11 sections)
- [templates/quick-switch.md.template](templates/quick-switch.md.template) - Team command
- [templates/skill-ref.md.template](templates/skill-ref.md.template) - Reference skill

### Validation
Pre-flight checks:
- [validation/checklist.md](validation/checklist.md) - Validation checklist
- [validation/common-issues.md](validation/common-issues.md) - Troubleshooting

### Examples
Complete team implementations:
- [examples/minimal-team.md](examples/minimal-team.md) - 3-agent team
- [examples/full-team.md](examples/full-team.md) - 5-agent team

---

## Existing Teams Reference

| Team | Agents | Workflow | Entry Agent |
|------|--------|----------|-------------|
| 10x-dev-pack | 5 | Requirements → Design → Implementation → Validation | requirements-analyst |
| doc-team-pack | 4 | Audit → Architecture → Writing → Review | doc-auditor |
| hygiene-pack | 4 | Assessment → Planning → Execution → Audit | code-smeller |
| debt-triage-pack | 3 | Collection → Assessment → Planning | debt-collector |
| sre-pack | 4 | Observation → Coordination → Implementation → Resilience | observability-engineer |
| security-pack | 4 | Threat Modeling → Compliance → Testing → Review | threat-modeler |
| intelligence-pack | 4 | Instrumentation → Research → Experimentation → Synthesis | analytics-engineer |
| rnd-pack | 4 | Scouting → Integration → Prototyping → Future Architecture | technology-scout |
| strategy-pack | 4 | Market Research → Competitive Analysis → Business Modeling → Planning | market-researcher |

**Total**: 9 teams, 36 agents

---

## Cross-Skill Integration

- @10x-workflow for workflow mechanics and phase transitions
- @documentation for artifact templates (PRD, TDD, ADR)
- @standards for naming conventions and code patterns
- @prompting for agent invocation patterns
- **@consult-ref for ecosystem navigation** (MUST update when adding teams)

---

## Consultant Synchronization (REQUIRED)

The Consultant agent is the ecosystem's meta-navigator. When you create or modify teams, you **MUST** update the Consultant's knowledge base to keep it canonical.

### Files to Update

| Change | Files to Update |
|--------|-----------------|
| New team created | `ecosystem-map.md`, `agent-reference.md`, new `team-profiles/{team}.md` |
| New command added | `command-reference.md`, `ecosystem-map.md` |
| Workflow changed | `team-profiles/{team}.md`, `agent-reference.md` |
| Agent added/removed | `agent-reference.md`, `team-profiles/{team}.md` |
| New playbook needed | `playbooks/curated/{playbook}.md` |

### Knowledge Base Location

```
.claude/knowledge/consultant/
├── ecosystem-map.md          # Update team count, add new team
├── command-reference.md      # Add new commands
├── agent-reference.md        # Add new agents
├── routing/
│   ├── intent-patterns.md    # Add routing patterns for new team
│   ├── decision-trees.md     # Update routing logic
│   └── complexity-matrix.md  # Add complexity levels
├── team-profiles/
│   └── {team-name}.md        # CREATE new team profile
└── playbooks/curated/
    └── {playbook}.md         # Add relevant playbooks
```

### Team Profile Template

When creating a new team, add a profile at `.claude/knowledge/consultant/team-profiles/{team}-pack.md`:

```markdown
# {team}-pack

> [One-line description]

## Overview
[2-3 sentence description]

## Switch Command
`/{team}`

## Agents
| Agent | Model | Role |
|-------|-------|------|
| ... | ... | ... |

## Workflow
[ASCII workflow diagram]

## Complexity Levels
| Level | When to Use | Phases |
|-------|-------------|--------|
| ... | ... | ... |

## Best For
- [Use case 1]
- [Use case 2]

## Not For
- [Anti-pattern 1]
- [Anti-pattern 2]

## Quick Start
/{team}
/task "description"

## Related Commands
- /task, /architect, /build, /qa (as applicable)
```

### Validation

After updating Consultant knowledge:
```bash
# Verify team appears in ecosystem map
grep "{team-name}" .claude/knowledge/consultant/ecosystem-map.md

# Verify agents listed
grep "{agent-name}" .claude/knowledge/consultant/agent-reference.md

# Verify profile exists
ls .claude/knowledge/consultant/team-profiles/{team-name}.md
```

See [patterns/consultant-sync.md](patterns/consultant-sync.md) for detailed synchronization patterns.

---

## Quick Start

To create a new team:

```bash
# 1. Create directory structure
mkdir -p ~/Code/roster/teams/{name}-pack/agents

# 2. Copy and fill templates
# - workflow.yaml from templates/workflow.yaml.template
# - agent files from templates/agent.md.template

# 3. Create command and skill
# - .claude/commands/{name}.md
# - .claude/skills/{name}-ref/skill.md

# 4. Update registry
# - Add to COMMAND_REGISTRY.md

# 5. Validate
~/Code/roster/swap-team.sh {name}-pack
```

See [validation/checklist.md](validation/checklist.md) for full pre-flight checks.
