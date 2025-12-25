# Consultant Synchronization Pattern

> Keep the Consultant agent canonical with all ecosystem changes

## Why This Matters

The Consultant agent (`/consult`) is the ecosystem's meta-navigator. Users rely on it for:
- Team recommendations
- Command guidance
- Workflow playbooks
- Ecosystem navigation

**If the Consultant has stale data, users get wrong guidance.**

---

## Knowledge Base Structure

```
.claude/knowledge/consultant/
├── ecosystem-map.md          # Complete ecosystem overview
├── command-reference.md      # All 25+ commands
├── agent-reference.md        # All 36+ agents
├── routing/
│   ├── intent-patterns.md    # Natural language → team/command
│   ├── decision-trees.md     # Structured routing logic
│   └── complexity-matrix.md  # Scope-based selection
├── team-profiles/
│   └── {team}-pack.md        # One per team (9 files)
└── playbooks/curated/
    └── {scenario}.md         # Common workflow playbooks
```

---

## Synchronization Matrix

| Change Type | Files to Update |
|-------------|-----------------|
| **New team** | ecosystem-map, agent-reference, team-profile (new), intent-patterns, decision-trees, complexity-matrix, command-reference |
| **New agent to existing team** | agent-reference, team-profile |
| **New command** | command-reference, ecosystem-map |
| **Workflow change** | team-profile, agent-reference (if phases change) |
| **Rename team** | All files referencing old name |
| **Remove team** | Remove from all files, delete team-profile |
| **New playbook** | Create in playbooks/curated/ |

---

## Step-by-Step: Adding a New Team

### 1. Update ecosystem-map.md

Add to Teams table:
```markdown
| **{team}-pack** | `/{team}` | {N} | {Brief description} |
```

Update counts:
```markdown
**Total Agents**: {new count} across all teams
```

### 2. Update agent-reference.md

Add new section:
```markdown
## {team}-pack ({N} agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **{agent-1}** | {model} | {phase} | {artifact} |
| **{agent-2}** | {model} | {phase} | {artifact} |
...

**Workflow**: {phase-1} → {phase-2} → {phase-3} → {phase-4}
```

### 3. Create team-profiles/{team}-pack.md

Use template from SKILL.md. Include:
- Overview
- Switch Command
- Agents table
- Workflow diagram
- Complexity Levels
- Best For / Not For
- Quick Start
- Related Commands

### 4. Update routing/intent-patterns.md

Add intent patterns for new team domain:
```markdown
## {Domain} Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "{keyword 1}" | {description} | `/{team}` → `/task` |
| "{keyword 2}" | {description} | `/{team}` → `/task` |
```

### 5. Update routing/decision-trees.md

Add to Primary Router:
```markdown
├─ {DOMAIN} something?
│   └─ → {team}-pack (/{team})
```

Add to Team Selection Tree:
```markdown
├─ {Domain}
│   └─ → {team}-pack (/{team})
```

### 6. Update routing/complexity-matrix.md

Add team's complexity levels:
```markdown
## {team}-pack Complexity

| Level | When to Use | Scope |
|-------|-------------|-------|
| **{LEVEL1}** | {description} | {scope} |
| **{LEVEL2}** | {description} | {scope} |
```

### 7. Update command-reference.md

Add to Team Management section:
```markdown
| `/{team}` | {team}-pack |
```

---

## Step-by-Step: Modifying Existing Team

### Agent Added

1. **agent-reference.md**: Add agent to team section
2. **team-profiles/{team}.md**: Update Agents table

### Agent Removed

1. **agent-reference.md**: Remove agent from team section
2. **team-profiles/{team}.md**: Update Agents table

### Workflow Changed

1. **team-profiles/{team}.md**: Update Workflow diagram
2. **agent-reference.md**: Update workflow summary if needed

### Complexity Levels Changed

1. **team-profiles/{team}.md**: Update Complexity Levels table
2. **routing/complexity-matrix.md**: Update team section

---

## Step-by-Step: Adding Playbook

### 1. Identify the scenario

Common playbooks cover:
- Feature development
- Bug fixes
- Code quality
- Documentation
- Security
- Performance
- Tech debt
- Incidents

### 2. Create playbook file

Location: `.claude/knowledge/consultant/playbooks/curated/{scenario}.md`

Use format:
```markdown
# Playbook: {Name}

> {One-line description}

## When to Use
- {Trigger 1}
- {Trigger 2}

## Prerequisites
- {Prereq 1}

## Command Sequence

### Phase 1: {Name}
```bash
/{command} {args}
```
**Expected output**: {Description}
**Decision point**: {When to proceed vs adjust}

### Phase 2: {Name}
...

## Variations
- **{Variant}**: {Adjustment}

## Success Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}
```

### 3. Update consult-ref skill

Add playbook to the list in `.claude/skills/consult-ref/skill.md`:
```markdown
**Curated Playbooks**: Pre-authored sequences for common scenarios
- `{playbook}.md`
```

---

## Verification Commands

After any sync:

```bash
# Verify ecosystem-map has correct team count
grep "teams" .claude/knowledge/consultant/ecosystem-map.md

# Verify agent-reference has all teams
grep "## .*-pack" .claude/knowledge/consultant/agent-reference.md

# Verify all team profiles exist
ls .claude/knowledge/consultant/team-profiles/

# Verify routing includes team
grep "{team-name}" .claude/knowledge/consultant/routing/intent-patterns.md

# Verify command reference
grep "/{team}" .claude/knowledge/consultant/command-reference.md
```

---

## Common Issues

### Forgot to update ecosystem-map

**Symptom**: `/consult --team` shows wrong count
**Fix**: Update team count and add missing team to table

### Missing team profile

**Symptom**: `/consult` can't give detailed team guidance
**Fix**: Create team-profiles/{team}-pack.md

### Stale routing patterns

**Symptom**: `/consult "query"` doesn't route to new team
**Fix**: Add keywords to intent-patterns.md and decision-trees.md

### Wrong agent count

**Symptom**: Consultant says team has N agents, but it has M
**Fix**: Update agent-reference.md and ecosystem-map.md

---

## Automation Opportunity

Future enhancement: Create a validation script that:
1. Scans roster for all teams
2. Compares against Consultant knowledge
3. Reports discrepancies
4. Suggests updates

```bash
# Future: ~/Code/roster/validate-consultant.sh
# Would check all teams are reflected in knowledge base
```

---

## Related

- [SKILL.md](../SKILL.md) - Team development overview
- [validation/checklist.md](../validation/checklist.md) - Full validation checklist
- [consult-ref skill](../../consult-ref/skill.md) - Consultant reference
