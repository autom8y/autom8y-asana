---
name: docs-ref
description: "Quick switch to doc-team-pack (documentation workflow). Shows team roster after switch. Triggers: /docs, documentation team, doc workflow."
---

# /docs - Quick Switch to Documentation Team

> **Category**: Team Management | **Phase**: Team Switching

## Purpose

Instantly switch to the doc-team-pack, a specialized team focused on technical writing, API documentation, information architecture, and documentation quality audits.

This is a convenience wrapper around `/team doc-team-pack` that also displays the team roster after switching.

---

## Usage

```bash
/docs
```

No parameters required. This command:
1. Switches to doc-team-pack
2. Displays team roster with agent descriptions

---

## Behavior

### 1. Invoke Team Switch

Execute via Bash tool:

```bash
~/Code/roster/swap-team.sh doc-team-pack
```

### 2. Display Team Roster

After successful switch, show the active team roster:

```
Switched to doc-team-pack (4 agents loaded)

Team Roster:
┌─────────────────────────┬──────────────────────────────────────────────┐
│ Agent                   │ Role                                         │
├─────────────────────────┼──────────────────────────────────────────────┤
│ doc-auditor             │ Reviews docs for accuracy and completeness   │
│ information-architect   │ Structures documentation for discoverability │
│ tech-writer             │ Creates clear, concise technical content     │
│ doc-reviewer            │ Validates quality, consistency, standards    │
└─────────────────────────┴──────────────────────────────────────────────┘

Use /handoff <agent> to delegate work.
```

### 3. Update SESSION_CONTEXT (if active)

If a session is active:
- Update `active_team` field to `doc-team-pack`
- Add handoff note documenting team switch

---

## Team Details

**Team Name**: doc-team-pack
**Agent Count**: 4
**Workflow**: Audit → Architecture → Writing → Review

### Agents

#### doc-auditor.md
**Role**: Documentation audit and gap analysis
**Invocation**: `Act as **Doc Auditor**`
**Purpose**: Identifies missing, outdated, or incomplete documentation

**When to use**:
- Beginning documentation initiatives
- Assessing current doc coverage
- Finding documentation gaps in codebases
- Planning documentation roadmaps

#### information-architect.md
**Role**: Documentation structure and organization
**Invocation**: `Act as **Information Architect**`
**Purpose**: Designs navigation, taxonomy, and information hierarchy

**When to use**:
- Structuring large documentation sets
- Creating documentation site architecture
- Organizing API references
- Designing user guides and tutorials
- Planning progressive disclosure strategies

#### tech-writer.md
**Role**: Technical content creation
**Invocation**: `Act as **Tech Writer**`
**Purpose**: Writes clear, accurate technical documentation

**When to use**:
- Creating README files
- Writing API documentation
- Producing user guides
- Drafting tutorials and how-tos
- Documenting architecture and design decisions
- Creating runbooks and operational docs

#### doc-reviewer.md
**Role**: Documentation quality validation
**Invocation**: `Act as **Doc Reviewer**`
**Purpose**: Ensures accuracy, consistency, and adherence to style guides

**When to use**:
- Final review before publishing
- Consistency checks across docs
- Style guide compliance validation
- Technical accuracy verification
- Readability and clarity assessment

---

## Examples

### Example 1: Basic Switch

```bash
/docs
```

Output:
```
[Roster] Switched to doc-team-pack (4 agents loaded)

Team Roster:
  - doc-auditor: Reviews docs for accuracy and completeness
  - information-architect: Structures documentation for discoverability
  - tech-writer: Creates clear, concise technical content
  - doc-reviewer: Validates quality, consistency, standards

Ready for documentation workflow.
```

### Example 2: Documentation Initiative

```bash
/docs
/start "Document REST API" --complexity=MODULE
```

Output:
```
[Roster] Switched to doc-team-pack (4 agents loaded)
Session started: Document REST API
Complexity: MODULE

Next: Doc Auditor will assess current API documentation state.
```

### Example 3: Mid-Session Switch

After implementing a feature with `/10x`, switch to document it:

```bash
/docs
/handoff writer
```

Output:
```
[Roster] Switched to doc-team-pack (4 agents loaded)
Handing off to: tech-writer

Tech Writer reviewing implementation artifacts...
```

---

## Typical Workflow with Docs Team

### Phase 1: Audit
```bash
/docs
/start "Document authentication system" --complexity=MODULE
# Doc Auditor assesses current state, identifies gaps
```

### Phase 2: Architecture
```bash
/handoff information-architect
# Information Architect designs doc structure
# - Getting Started
# - API Reference
# - Integration Guide
# - Troubleshooting
```

### Phase 3: Writing
```bash
/handoff tech-writer
# Tech Writer creates documentation content
# Following structure from Information Architect
```

### Phase 4: Review
```bash
/handoff doc-reviewer
# Doc Reviewer validates quality and consistency
# Checks against style guides
# Ensures technical accuracy
```

### Phase 5: Completion
```bash
/wrap
```

---

## When to Use Docs Team

Use this team for:

- **API documentation**: REST/GraphQL/gRPC endpoint documentation
- **README creation**: Project onboarding, quickstart guides
- **Architecture documentation**: System design docs, diagrams
- **User guides**: Feature usage, integration instructions
- **Runbooks**: Operational procedures, troubleshooting
- **ADR review**: Polishing architecture decision records
- **Tutorial creation**: Step-by-step learning content

**Don't use for**:
- Feature implementation → Use `/10x` instead
- Code refactoring → Use `/hygiene` instead
- Debt assessment → Use `/debt` instead

---

## State Changes

### Files Modified

| File | Change | Description |
|------|--------|-------------|
| `.claude/ACTIVE_TEAM` | Set to `doc-team-pack` | Active team state |
| `.claude/agents/` | Populated | 4 agent files loaded |
| `.claude/SESSION_CONTEXT` | `active_team` updated | If session active |

---

## Success Criteria

- Team switched to doc-team-pack
- 4 agent files present in `.claude/agents/`
- Team roster displayed to user
- If session active, SESSION_CONTEXT updated

---

## Error Handling

If swap fails:

```
[Roster] Error: Team pack 'doc-team-pack' not found
[Roster] Use '/team --list' to see available packs
```

**Resolution**: Verify roster installation at `~/Code/roster/`

---

## Integration with Documentation Skill

This team complements the `documentation` skill:

```bash
/docs
# Use documentation skill to access templates
Act as **Tech Writer**.

Create API documentation for user authentication endpoints.
Use template at `.claude/skills/documentation/templates/api-doc.md`.
```

The documentation skill provides templates, this team provides specialized agents.

---

## Related Commands

- `/team` - General team switching with options
- `/10x` - Quick switch to development team
- `/hygiene` - Quick switch to code hygiene team
- `/debt` - Quick switch to technical debt team
- `/handoff` - Delegate to specific agent in current team

---

## Related Skills

- [documentation](../documentation/SKILL.md) - Templates for PRD/TDD/ADR/Test Plans
- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns

---

## Related Documentation

- [COMMAND_REGISTRY.md](../../COMMAND_REGISTRY.md) - All registered commands
- [swap-team.sh](~/Code/roster/swap-team.sh) - Roster swap implementation

---

## Notes

### Documentation-First Projects

Some projects prioritize documentation:
- Open source libraries (README, API docs critical)
- Internal tools (runbooks, user guides essential)
- Platform migrations (documentation before code changes)

For these, start with `/docs` instead of `/10x`.

### Difference from /team

| Command | Behavior |
|---------|----------|
| `/team doc-team-pack` | Switches team, shows swap confirmation |
| `/docs` | Switches team, shows roster with agent descriptions |

Use `/docs` when you want to see available agents after switching.

### Cross-Team Handoffs

Common pattern: Implement with `/10x`, document with `/docs`:

```bash
/10x
/start "Add OAuth2 support" --complexity=MODULE
# ... implementation ...
/docs
/handoff tech-writer
# Tech Writer documents new OAuth2 endpoints
```

This leverages specialized teams for each phase.
