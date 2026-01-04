---
name: hygiene-ref
description: "Quick switch to hygiene-pack (code quality workflow). Use when: detecting code smells, enforcing architecture compliance, executing refactoring, running quality audits. Triggers: /hygiene, code quality, refactoring team, quality audit, code cleanup."
---

# /hygiene - Quick Switch to Code Hygiene Team

> **Category**: Team Management | **Phase**: Team Switching

## Purpose

Instantly switch to the hygiene-pack, a specialized team focused on code quality, architectural compliance, refactoring, and technical cleanliness. This team detects code smells, enforces standards, and cleans up technical messes.

This is a convenience wrapper around `/team hygiene-pack` that also displays the team roster after switching.

---

## Usage

```bash
/hygiene
```

No parameters required. This command:
1. Switches to hygiene-pack
2. Displays team roster with agent descriptions

---

## Behavior

### 1. Invoke Team Switch

Execute via Bash tool:

```bash
$ROSTER_HOME/swap-team.sh hygiene-pack
```

### 2. Display Team Roster

After successful switch, show the active team roster:

```
Switched to hygiene-pack (4 agents loaded)

Team Roster:
┌─────────────────────────┬──────────────────────────────────────────────┐
│ Agent                   │ Role                                         │
├─────────────────────────┼──────────────────────────────────────────────┤
│ code-smeller            │ Detects code smells and anti-patterns        │
│ architect-enforcer      │ Validates architectural compliance           │
│ janitor                 │ Cleans up code, refactors for quality        │
│ audit-lead              │ Conducts comprehensive quality audits        │
└─────────────────────────┴──────────────────────────────────────────────┘

Use /handoff <agent> to delegate work.
```

### 3. Update SESSION_CONTEXT (if active)

If a session is active:
- Update `active_team` field to `hygiene-pack`
- Add handoff note documenting team switch

---

## Team Details

**Team Name**: hygiene-pack
**Agent Count**: 4
**Workflow**: Detect → Audit → Enforce → Clean

### Agents

#### code-smeller.md
**Role**: Code smell detection and anti-pattern identification
**Invocation**: `Act as **Code Smeller**`
**Purpose**: Identifies problematic code patterns, smells, and quality issues

**When to use**:
- Initial codebase assessment
- Finding refactoring candidates
- Identifying technical debt hotspots
- Pre-refactoring analysis
- Code review quality checks

**Detects**:
- Long methods/functions (> 50 LOC)
- God classes (too many responsibilities)
- Duplicate code
- Poor naming conventions
- Deep nesting (> 4 levels)
- Large parameter lists
- Feature envy, inappropriate intimacy
- Dead code

#### architect-enforcer.md
**Role**: Architectural compliance validation
**Invocation**: `Act as **Architect Enforcer**`
**Purpose**: Ensures code adheres to documented architecture and ADRs

**When to use**:
- Validating implementations against TDDs
- Checking ADR compliance
- Architecture drift detection
- Design pattern enforcement
- Dependency rule validation

**Validates**:
- Layer boundaries (presentation, business, data)
- Dependency direction (no circular deps)
- Interface contracts
- Design pattern implementations
- ADR-documented decisions
- Module coupling/cohesion

#### janitor.md
**Role**: Code cleanup and refactoring execution
**Invocation**: `Act as **Janitor**`
**Purpose**: Performs safe refactoring to improve code quality

**When to use**:
- Executing refactoring plans
- Cleaning up after initial implementation
- Improving code readability
- Reducing complexity
- Removing duplication

**Performs**:
- Extract method/class refactorings
- Rename for clarity
- Reduce nesting
- Simplify conditionals
- Remove dead code
- Consolidate duplicate logic
- Improve naming

#### audit-lead.md
**Role**: Comprehensive quality audit coordination
**Invocation**: `Act as **Audit Lead**`
**Purpose**: Orchestrates full quality audits, produces reports

**When to use**:
- Quarterly quality reviews
- Pre-release quality gates
- Technical health assessments
- Refactoring initiative planning
- Quality metric collection

**Produces**:
- Quality audit reports
- Refactoring recommendations (prioritized)
- Code health metrics
- Trend analysis
- Remediation roadmaps

---

## Examples

### Example 1: Basic Switch

```bash
/hygiene
```

Output:
```
[Roster] Switched to hygiene-pack (4 agents loaded)

Team Roster:
  - code-smeller: Detects code smells and anti-patterns
  - architect-enforcer: Validates architectural compliance
  - janitor: Cleans up code, refactors for quality
  - audit-lead: Conducts comprehensive quality audits

Ready for code quality workflow.
```

### Example 2: Quality Audit Session

```bash
/hygiene
/start "Q4 Codebase Quality Audit" --complexity=PLATFORM
```

Output:
```
[Roster] Switched to hygiene-pack (4 agents loaded)
Session started: Q4 Codebase Quality Audit
Complexity: PLATFORM

Next: Audit Lead will coordinate comprehensive quality review.
```

### Example 3: Refactoring After Implementation

After completing feature with `/10x`:

```bash
/hygiene
/handoff smeller
```

Output:
```
[Roster] Switched to hygiene-pack (4 agents loaded)
Handing off to: code-smeller

Code Smeller analyzing recent implementation...
Detecting code smells and refactoring opportunities...
```

---

## Typical Workflow with Hygiene Team

### Phase 1: Detection
```bash
/hygiene
/start "Refactor authentication module" --complexity=MODULE
# Code Smeller identifies issues in auth module
# Produces: List of code smells with severity
```

### Phase 2: Audit
```bash
/handoff audit-lead
# Audit Lead reviews smells, prioritizes by impact
# Produces: Refactoring roadmap with effort estimates
```

### Phase 3: Enforcement Check
```bash
/handoff architect-enforcer
# Architect Enforcer validates current state vs ADRs
# Identifies: Architecture violations needing correction
```

### Phase 4: Cleanup
```bash
/handoff janitor
# Janitor executes refactoring plan
# Performs: Safe refactorings with tests passing
```

### Phase 5: Validation
```bash
/handoff audit-lead
# Audit Lead validates improvements
# Produces: Before/after metrics, completion report
```

### Phase 6: Completion
```bash
/wrap
```

---

## When to Use Hygiene Team

Use this team for:

- **Code quality audits**: Regular health checks
- **Refactoring initiatives**: Cleaning up technical mess
- **Architecture compliance**: Enforcing design decisions
- **Pre-release cleanup**: Quality gates before shipping
- **Onboarding prep**: Making codebase cleaner for new devs
- **Post-implementation cleanup**: After rapid prototyping
- **Complexity reduction**: Simplifying overgrown code

**Don't use for**:
- New feature implementation → Use `/10x` instead
- Documentation → Use `/docs` instead
- Debt assessment (use `/debt` for planning, hygiene for execution)

---

## Hygiene vs Debt Teams

| Hygiene Team | Debt Team |
|--------------|-----------|
| **Focus**: Code quality and cleanliness | **Focus**: Technical debt prioritization |
| **Action**: Detect and fix issues | **Action**: Assess and plan remediation |
| **Scope**: Code-level refactoring | **Scope**: Project/portfolio-level debt |
| **Agents**: Smeller, Enforcer, Janitor, Audit Lead | **Agents**: Collector, Assessor, Planner |
| **Output**: Clean code, refactorings | **Output**: Debt inventory, roadmaps |

**Workflow**: Use `/debt` to plan, `/hygiene` to execute.

---

## State Changes

### Files Modified

| File | Change | Description |
|------|--------|-------------|
| `.claude/ACTIVE_TEAM` | Set to `hygiene-pack` | Active team state |
| `.claude/agents/` | Populated | 4 agent files loaded |
| `.claude/sessions/{session_id}/SESSION_CONTEXT.md` | `active_team` updated | If session active |

---

## Success Criteria

- Team switched to hygiene-pack
- 4 agent files present in `.claude/agents/`
- Team roster displayed to user
- If session active, SESSION_CONTEXT updated

---

## Error Handling

If swap fails:

```
[Roster] Error: Team pack 'hygiene-pack' not found
[Roster] Use '/team --list' to see available packs
```

**Resolution**: Verify roster installation at `$ROSTER_HOME/`

---

## Integration with Standards Skill

This team complements the `standards` skill:

```bash
/hygiene
Act as **Architect Enforcer**.

Validate implementation against standards documented in:
.claude/skills/standards/SKILL.md

Check for violations of:
- Directory structure conventions
- Naming conventions
- Error handling patterns
```

Standards skill defines rules, hygiene team enforces them.

---

## Related Commands

- `/team` - General team switching with options
- `/10x` - Quick switch to development team
- `/docs` - Quick switch to documentation team
- `/debt` - Quick switch to technical debt team
- `/handoff` - Delegate to specific agent in current team

---

## Related Skills

- [standards](../standards/SKILL.md) - Code conventions and quality rules
- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns

---

## Related Documentation

- [COMMAND_REGISTRY.md](../../COMMAND_REGISTRY.md) - All registered commands
- [swap-team.sh]($ROSTER_HOME/swap-team.sh) - Roster swap implementation

---

## Notes

### Continuous vs Project-Based Hygiene

**Continuous hygiene** (recommended):
- Run Code Smeller on each PR
- Monthly Audit Lead reviews
- Janitor cleanups after feature completion

**Project-based hygiene**:
- Quarterly quality initiatives
- Pre-release cleanup sprints
- Major refactoring projects

Both valid, continuous prevents accumulation.

### Difference from /team

| Command | Behavior |
|---------|----------|
| `/team hygiene-pack` | Switches team, shows swap confirmation |
| `/hygiene` | Switches team, shows roster with agent descriptions |

Use `/hygiene` when you want to see available agents after switching.

### Quality Metrics

Hygiene team can track:
- Cyclomatic complexity trends
- Code duplication percentage
- Test coverage
- Linter violation counts
- Architecture compliance score

Store metrics in session artifacts for historical comparison.
