---
name: forge-ref
description: |
  Reference documentation for The Forge - the meta-team for creating and maintaining
  agent teams. Use when: learning about team creation, understanding the Forge workflow,
  invoking Forge commands. Triggers: /forge, /new-team, team creation, agent factory,
  build team, create agents.
---

# The Forge Reference

> The team that builds teams. Meta-level agent factory for the Claude Code ecosystem.

## Quick Reference

### Commands

| Command | Purpose | Entry Agent |
|---------|---------|-------------|
| `/forge` | Display Forge overview and help | (info only) |
| `/new-team <name>` | Create a new team pack | Agent Designer |
| `/validate-team <name>` | Run validation on team | Eval Specialist |
| `/eval-agent <name>` | Test single agent | Eval Specialist |

### Agents

| Agent | Model | Color | Produces |
|-------|-------|-------|----------|
| **Agent Designer** | opus | purple | TEAM-SPEC, role definitions |
| **Prompt Architect** | opus | cyan | Agent .md files (11 sections) |
| **Workflow Engineer** | opus | green | workflow.yaml, commands |
| **Platform Engineer** | sonnet | orange | Roster files, directory structure |
| **Eval Specialist** | opus | red | eval-report.md, test results |
| **Agent Curator** | sonnet | blue | Roster entry, Consultant sync |

### Workflow

```
Agent Designer → Prompt Architect → Workflow Engineer → Platform Engineer → Eval Specialist → Agent Curator
     │               │                   │                    │                  │               │
     ▼               ▼                   ▼                    ▼                  ▼               ▼
 TEAM-SPEC      Agent .md files    workflow.yaml      roster/teams/       eval-report      roster entry
                                                         {team}/                           + Consultant
```

---

## Complexity Levels

| Level | Scope | Phases |
|-------|-------|--------|
| **PATCH** | Single agent modification | design, prompting, validation |
| **TEAM** | New team with 3-5 agents | All 6 phases |
| **ECOSYSTEM** | Multi-team initiative | All 6 phases |

---

## Using The Forge

### Creating a New Team

```bash
# Start team creation workflow
/new-team api-development

# With specific complexity
/new-team security-auditor --complexity=PATCH
```

**What happens**:
1. Agent Designer asks about team purpose and scope
2. You collaborate to define 3-5 agent roles
3. Prompt Architect creates agent files
4. Workflow Engineer creates workflow.yaml
5. Platform Engineer deploys to roster
6. Eval Specialist validates
7. Agent Curator integrates and syncs Consultant

### Validating Existing Teams

```bash
# Full validation
/validate-team security-pack

# With verbose output
/validate-team 10x-dev-pack --verbose
```

**What's checked**:
- Structure: All files exist
- Schema: Frontmatter and workflow valid
- Logic: Phase chain coherent
- Adversarial: Edge cases handled

### Testing Individual Agents

```bash
# Test agent in active team
/eval-agent principal-engineer

# Test agent in specific team
/eval-agent threat-modeler --team=security-pack

# Include adversarial prompts
/eval-agent architect --adversarial
```

---

## The Six Agents

### Agent Designer (Entry Point)

**Purpose**: Creates team specifications and role definitions.

**Domain**:
- Team purpose and scope
- Agent role boundaries
- Input/output contracts
- Complexity level design

**Produces**: TEAM-SPEC.md with all roles defined

**Handoff**: When TEAM-SPEC is complete and approved

### Prompt Architect

**Purpose**: Crafts system prompts for agents.

**Domain**:
- Agent identity and personality
- Instruction clarity and constraints
- Token efficiency
- Example creation

**Produces**: Complete agent .md files with 11 sections

**Handoff**: When all agents have complete prompts

### Workflow Engineer

**Purpose**: Designs orchestration and commands.

**Domain**:
- Phase sequencing
- workflow.yaml configuration
- Slash command creation
- Complexity gating

**Produces**: workflow.yaml and command files

**Handoff**: When workflow is complete and validates

### Platform Engineer

**Purpose**: Implements roster infrastructure.

**Domain**:
- Directory structure creation
- File deployment
- swap-team.sh integration
- Structure validation

**Produces**: Team pack deployed to roster

**Handoff**: When swap-team.sh loads successfully

### Eval Specialist

**Purpose**: Validates teams before shipment.

**Domain**:
- Completeness checks
- Schema validation
- Logic validation
- Adversarial testing

**Produces**: eval-report.md with pass/fail

**Handoff**: When all validations pass

### Agent Curator (Terminal)

**Purpose**: Finalizes integration and documentation.

**Domain**:
- Consultant knowledge sync
- Team profile creation
- Version recording
- Documentation

**Produces**: Roster entry + Consultant sync

**Terminal**: Workflow completes here

---

## Knowledge Base

### Patterns

| File | Purpose |
|------|---------|
| `patterns/role-definition.md` | How to define agent roles |
| `patterns/domain-authority.md` | decide/escalate/route structure |
| `patterns/handoff-criteria.md` | Verification checklists |

### Evaluation Harnesses

| File | Purpose |
|------|---------|
| `evals/agent-completeness.md` | Agent file validation |
| `evals/workflow-validity.md` | workflow.yaml checks |
| `evals/integration-tests.md` | End-to-end tests |

### Templates

See: `.claude/knowledge/forge/templates/README.md`

---

## Best Practices

### Team Design

1. **Start with purpose**: What problem does this team solve?
2. **3-5 agents**: Less is more. Consolidate related responsibilities.
3. **Clear boundaries**: No overlap between agent domains.
4. **Linear flow**: Avoid circular dependencies.

### Agent Prompts

1. **Strong identity**: First paragraph establishes who they are.
2. **Actionable instructions**: Not vague guidelines.
3. **Realistic examples**: Show actual expected behavior.
4. **Token awareness**: Keep under 4000 tokens.

### Workflows

1. **One terminal**: Exactly one phase with `next: null`.
2. **Reachable phases**: All phases accessible from entry.
3. **Sensible gating**: Lower complexity = fewer phases.
4. **Clear commands**: Map /architect, /build, /qa appropriately.

---

## Troubleshooting

### "swap-team.sh fails"

Check:
- Team directory exists at `~/Code/roster/teams/{name}/`
- agents/ subdirectory has .md files
- workflow.yaml exists
- File permissions are correct

### "Agent validation fails"

Check:
- All 11 sections present
- Frontmatter has required fields
- No YAML syntax errors
- Token count under budget

### "Consultant can't find team"

Check:
- ecosystem-map.md updated
- team-profiles/{team}.md exists
- intent-patterns.md has keywords
- command-reference.md lists command

### "Handoff doesn't trigger"

Check:
- Handoff criteria are specific
- Next agent is correctly named
- workflow.yaml `next` field is correct

---

## File Locations

| Type | Location |
|------|----------|
| Forge agents | `.claude/global-agents/` |
| Forge commands | `.claude/commands/` |
| Forge workflow | `.claude/forge-workflow.yaml` |
| Knowledge base | `.claude/knowledge/forge/` |
| This skill | `.claude/skills/forge-ref/` |

---

## Related Resources

- [team-development skill](../team-development/SKILL.md) - Manual team creation guidance
- [10x-workflow skill](../10x-workflow/SKILL.md) - Workflow patterns
- [consult-ref skill](../consult-ref/skill.md) - Ecosystem navigation
- [documentation skill](../documentation/SKILL.md) - Artifact templates

---

## Global Singleton Architecture

The Forge is a **global singleton team**—it's always available regardless of which team pack is active.

### How It Works

1. Forge agents live in `.claude/global-agents/`
2. `swap-team.sh` preserves global agents after team swaps
3. You can invoke any Forge agent from any team context
4. Forge has its own workflow config at `.claude/forge-workflow.yaml`

### Why Global?

- Team creation is meta-level work (about teams, not within teams)
- Should be accessible regardless of current work context
- Similar to Consultant—always available for ecosystem operations

---

## Extending The Forge

### Adding New Patterns

1. Create file in `.claude/knowledge/forge/patterns/`
2. Update `templates/README.md`
3. Reference in relevant agent prompts

### Adding New Eval Checks

1. Create file in `.claude/knowledge/forge/evals/`
2. Update `eval-specialist.md` to reference it
3. Add to validation checklist

### Modifying Forge Workflow

1. Edit `.claude/forge-workflow.yaml`
2. Update agent handoff criteria if phases change
3. Update this skill reference
