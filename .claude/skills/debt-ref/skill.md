---
name: debt-ref
description: "Quick switch to debt-triage-pack (technical debt management). Shows team roster after switch. Triggers: /debt, debt team, debt triage, debt planning."
---

# /debt - Quick Switch to Technical Debt Team

> **Category**: Team Management | **Phase**: Team Switching

## Purpose

Instantly switch to the debt-triage-pack, a specialized team focused on identifying, assessing, and planning remediation of technical debt across codebases and projects.

This is a convenience wrapper around `/team debt-triage-pack` that also displays the team roster after switching.

---

## Usage

```bash
/debt
```

No parameters required. This command:
1. Switches to debt-triage-pack
2. Displays team roster with agent descriptions

---

## Behavior

### 1. Invoke Team Switch

Execute via Bash tool:

```bash
~/Code/roster/swap-team.sh debt-triage-pack
```

### 2. Display Team Roster

After successful switch, show the active team roster:

```
Switched to debt-triage-pack (3 agents loaded)

Team Roster:
┌─────────────────────────┬──────────────────────────────────────────────┐
│ Agent                   │ Role                                         │
├─────────────────────────┼──────────────────────────────────────────────┤
│ debt-collector          │ Identifies and catalogs technical debt       │
│ risk-assessor           │ Evaluates impact and urgency of debt         │
│ sprint-planner          │ Creates remediation plans and roadmaps       │
└─────────────────────────┴──────────────────────────────────────────────┘

Use /handoff <agent> to delegate work.
```

### 3. Update SESSION_CONTEXT (if active)

If a session is active:
- Update `active_team` field to `debt-triage-pack`
- Add handoff note documenting team switch

---

## Team Details

**Team Name**: debt-triage-pack
**Agent Count**: 3
**Workflow**: Collect → Assess → Plan

### Agents

#### debt-collector.md
**Role**: Technical debt identification and cataloging
**Invocation**: `Act as **Debt Collector**`
**Purpose**: Systematically finds and documents technical debt across codebase

**When to use**:
- Initial debt inventory creation
- Quarterly debt scans
- New codebase assessment
- Pre-acquisition due diligence
- Portfolio health checks

**Identifies**:
- Outdated dependencies
- Deprecated API usage
- TODO/FIXME comments
- Workarounds and hacks
- Test coverage gaps
- Documentation debt
- Architectural drift
- Performance bottlenecks
- Security vulnerabilities
- Code duplication

**Produces**:
- Debt inventory (structured catalog)
- Debt categories and tags
- Initial severity estimates
- Source locations and context

#### risk-assessor.md
**Role**: Debt impact and urgency evaluation
**Invocation**: `Act as **Risk Assessor**`
**Purpose**: Prioritizes technical debt by risk, impact, and business value

**When to use**:
- After debt collection
- Before planning remediation
- When prioritizing backlog
- Risk-based decision making
- ROI analysis for debt paydown

**Assesses**:
- **Impact**: How much does this hurt? (High/Medium/Low)
- **Probability**: How likely to cause problems? (%)
- **Urgency**: When must this be fixed? (Critical/Soon/Eventually)
- **Cost**: Effort to remediate (days/weeks)
- **Value**: Benefit of fixing (velocity, quality, security)

**Produces**:
- Debt priority matrix
- Risk scores (impact × probability)
- ROI estimates (value / cost)
- Remediation urgency timeline
- Risk mitigation recommendations

#### sprint-planner.md
**Role**: Remediation planning and roadmap creation
**Invocation**: `Act as **Sprint Planner**`
**Purpose**: Creates actionable plans to pay down technical debt

**When to use**:
- After risk assessment
- Planning debt paydown sprints
- Creating quarterly roadmaps
- Balancing features vs debt work
- Estimating cleanup initiatives

**Produces**:
- Sprint-sized debt paydown tasks
- Remediation roadmaps (quarterly/annual)
- Effort estimates (story points/days)
- Dependency graphs (what to fix first)
- Success criteria and validation plans
- Progress tracking metrics

**Plans**:
- Incremental remediation (safe, testable steps)
- Dependency upgrades (with migration plans)
- Refactoring initiatives (broken into sprints)
- Test coverage improvements (module by module)
- Documentation debt paydown (by priority)

---

## Examples

### Example 1: Basic Switch

```bash
/debt
```

Output:
```
[Roster] Switched to debt-triage-pack (3 agents loaded)

Team Roster:
  - debt-collector: Identifies and catalogs technical debt
  - risk-assessor: Evaluates impact and urgency of debt
  - sprint-planner: Creates remediation plans and roadmaps

Ready for debt triage workflow.
```

### Example 2: Debt Assessment Session

```bash
/debt
/start "Q1 Technical Debt Assessment" --complexity=PLATFORM
```

Output:
```
[Roster] Switched to debt-triage-pack (3 agents loaded)
Session started: Q1 Technical Debt Assessment
Complexity: PLATFORM

Next: Debt Collector will scan codebase for technical debt.
```

### Example 3: Portfolio-Wide Debt Analysis

```bash
/debt
/handoff debt-collector
```

Output:
```
[Roster] Switched to debt-triage-pack (3 agents loaded)
Handing off to: debt-collector

Debt Collector scanning repositories...
Cataloging technical debt items...
```

---

## Typical Workflow with Debt Team

### Phase 1: Collection
```bash
/debt
/start "Annual Debt Inventory" --complexity=PLATFORM
# Debt Collector scans codebase(s)
# Produces: Debt inventory with 100+ items cataloged
```

### Phase 2: Assessment
```bash
/handoff risk-assessor
# Risk Assessor evaluates each debt item
# Produces: Priority matrix with risk scores
#
# Example output:
# - CRITICAL (6 items): Security vulnerabilities, deprecated APIs in prod
# - HIGH (15 items): Performance bottlenecks, missing tests
# - MEDIUM (42 items): Code duplication, outdated deps
# - LOW (38 items): TODOs, documentation gaps
```

### Phase 3: Planning
```bash
/handoff sprint-planner
# Sprint Planner creates remediation roadmap
# Produces:
# - Q1: Address all CRITICAL items (2 sprints)
# - Q2: Top 10 HIGH items (3 sprints)
# - Q3-Q4: MEDIUM items by ROI (ongoing)
```

### Phase 4: Execution (Hand off to other teams)
```bash
/10x
# Switch to dev team to implement debt fixes
# Or:
/hygiene
# Switch to hygiene team for refactoring work
```

### Phase 5: Tracking
```bash
/debt
/handoff sprint-planner
# Sprint Planner tracks progress
# Updates debt inventory as items are resolved
```

---

## When to Use Debt Team

Use this team for:

- **Debt inventories**: Comprehensive scans of technical debt
- **Risk assessment**: Prioritizing what debt to pay down
- **Roadmap planning**: Multi-quarter debt remediation plans
- **Portfolio management**: Tracking debt across multiple projects
- **Due diligence**: Assessing acquired or inherited codebases
- **Budget justification**: Quantifying debt impact for leadership
- **Velocity improvements**: Finding debt slowing development

**Don't use for**:
- Executing refactoring → Use `/hygiene` instead
- New feature work → Use `/10x` instead
- Documentation → Use `/docs` instead

---

## Debt vs Hygiene Teams

| Debt Team | Hygiene Team |
|-----------|--------------|
| **Focus**: Strategic debt management | **Focus**: Tactical code cleanup |
| **Scope**: Portfolio/project-level | **Scope**: Module/file-level |
| **Output**: Inventories, roadmaps, plans | **Output**: Refactored code, cleanliness |
| **Horizon**: Quarterly/annual planning | **Horizon**: Sprint/week execution |
| **Agents**: Collector, Assessor, Planner | **Agents**: Smeller, Enforcer, Janitor, Audit Lead |

**Workflow**: Use `/debt` to plan, `/hygiene` to execute.

```bash
# Strategic planning
/debt
/start "Q1 Debt Paydown Plan"
# Produces roadmap

# Tactical execution
/hygiene
/start "Refactor authentication module"
# Executes item from roadmap
```

---

## State Changes

### Files Modified

| File | Change | Description |
|------|--------|-------------|
| `.claude/ACTIVE_TEAM` | Set to `debt-triage-pack` | Active team state |
| `.claude/agents/` | Populated | 3 agent files loaded |
| `.claude/sessions/{session_id}/SESSION_CONTEXT.md` | `active_team` updated | If session active |

---

## Success Criteria

- Team switched to debt-triage-pack
- 3 agent files present in `.claude/agents/`
- Team roster displayed to user
- If session active, SESSION_CONTEXT updated

---

## Error Handling

If swap fails:

```
[Roster] Error: Team pack 'debt-triage-pack' not found
[Roster] Use '/team --list' to see available packs
```

**Resolution**: Verify roster installation at `~/Code/roster/`

---

## Debt Tracking Artifacts

Debt team produces structured artifacts:

### debt-inventory.yaml
```yaml
---
scan_date: "2025-12-24"
scope: "platform-wide"
items:
  - id: DEBT-001
    category: security
    severity: critical
    title: "Deprecated bcrypt version with known CVE"
    location: "auth-service/package.json"
    impact: "Remote code execution risk"
    effort_estimate: "2 hours"
    priority: 1
  - id: DEBT-002
    category: performance
    severity: high
    title: "N+1 query in user dashboard"
    location: "api/controllers/dashboard.js:45"
    impact: "2s load time for 1000+ users"
    effort_estimate: "1 day"
    priority: 2
```

### remediation-roadmap.md
```markdown
# Q1 2025 Technical Debt Remediation Roadmap

## Critical (Complete by Jan 31)
- [ ] DEBT-001: Upgrade bcrypt to 5.1.1
- [ ] DEBT-005: Fix SQL injection in search endpoint

## High Priority (Complete by Mar 31)
- [ ] DEBT-002: Resolve N+1 queries in dashboard
- [ ] DEBT-008: Add integration tests for payment flow
```

---

## Related Commands

- `/team` - General team switching with options
- `/10x` - Quick switch to development team
- `/docs` - Quick switch to documentation team
- `/hygiene` - Quick switch to code hygiene team
- `/handoff` - Delegate to specific agent in current team

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Agent coordination patterns
- [standards](../standards/SKILL.md) - Quality standards to compare against

---

## Related Documentation

- [COMMAND_REGISTRY.md](../../COMMAND_REGISTRY.md) - All registered commands
- [swap-team.sh](~/Code/roster/swap-team.sh) - Roster swap implementation

---

## Notes

### Debt vs Feature Tradeoffs

Leadership often asks: "Should we build features or pay down debt?"

Debt team provides data for this decision:
- **Velocity impact**: "Debt costs us 20% velocity (2 days/sprint)"
- **Risk quantification**: "CRITICAL items have 30% probability of production incident"
- **ROI analysis**: "Fixing top 10 items yields 15% velocity gain for 1 sprint investment"

This enables evidence-based prioritization.

### Difference from /team

| Command | Behavior |
|---------|----------|
| `/team debt-triage-pack` | Switches team, shows swap confirmation |
| `/debt` | Switches team, shows roster with agent descriptions |

Use `/debt` when you want to see available agents after switching.

### Debt Categories

Common debt categories tracked:
- **Code quality**: Duplication, complexity, smells
- **Testing**: Coverage gaps, flaky tests
- **Security**: Vulnerabilities, outdated auth
- **Performance**: Bottlenecks, inefficiencies
- **Dependencies**: Outdated libraries, deprecated APIs
- **Documentation**: Missing/outdated docs
- **Architecture**: Violations of ADRs, drift
- **Infrastructure**: Manual processes, missing automation

Debt Collector tags items by category for filtering.

### Continuous Debt Tracking

Recommended cadence:
- **Weekly**: Debt Collector scans (automated)
- **Monthly**: Risk Assessor re-prioritizes
- **Quarterly**: Sprint Planner updates roadmap
- **Annual**: Comprehensive portfolio debt review

Prevents debt from growing out of control.
