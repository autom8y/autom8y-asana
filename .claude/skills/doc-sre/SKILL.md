---
name: doc-sre
description: "SRE, reliability, debt triage, and analytics templates for observability, incidents, chaos engineering, and technical debt workflows. Use when: planning reliability improvements, documenting incidents, conducting chaos experiments, tracking technical debt, analyzing observability gaps, planning analytics tracking. Triggers: observability, reliability, postmortem, incident, chaos experiment, chaos engineering, technical debt, debt ledger, debt triage, risk matrix, sprint debt, tracking plan, analytics, SLO, SLI, MTTR."
---

# SRE & Analytics Documentation Templates

> **Status**: Complete (Session 2)

## Template Index

This skill provides templates for:

- **Observability & Monitoring**: [Observability Report](#observability-report-template)
- **Reliability Planning**: [Reliability Plan](#reliability-plan-template)
- **Incident Management**: [Postmortem](#postmortem-template)
- **Chaos Engineering**: [Chaos Experiment](#chaos-experiment-template), [Resilience Report](#resilience-report-template)
- **Technical Debt**: [Debt Ledger](#debt-ledger-template), [Risk Matrix](#risk-matrix-template), [Sprint Debt Packages](#sprint-debt-packages-template)
- **Analytics**: [Tracking Plan](#tracking-plan-template)

---

## Observability Report Template {#observability-report-template}

```markdown
# Observability Report: [System/Service]

## Executive Summary
[One paragraph: Current state, critical gaps, top recommendations]

## Scope
- Services analyzed: [list]
- Time period: [dates]
- Data sources: [metrics/logs/traces systems]

## Current State

### Metrics
| Service | Golden Signals | Custom Metrics | Gaps |
|---------|----------------|----------------|------|
| [name]  | [coverage %]   | [count]        | [list] |

### Logging
| Service | Structured | Correlation IDs | Retention |
|---------|------------|-----------------|-----------|
| [name]  | [yes/no]   | [yes/no]        | [days]    |

### Tracing
| Service | Instrumented | Sample Rate | Coverage |
|---------|--------------|-------------|----------|
| [name]  | [yes/no]     | [%]         | [%]      |

### Alerting
| Alert Category | Count | False Positive Rate | Actions |
|----------------|-------|---------------------|---------|
| Critical       | [n]   | [%]                 | [types] |

## Gap Analysis

### Critical Gaps (Must Fix)
1. [Gap]: [Impact] → [Recommendation]

### Important Gaps (Should Fix)
1. [Gap]: [Impact] → [Recommendation]

### Nice-to-Have Improvements
1. [Improvement]: [Benefit]

## Recommendations

### Quick Wins (< 1 week)
1. [Action]: [Expected outcome]

### Medium-Term (1-4 weeks)
1. [Action]: [Expected outcome]

### Long-Term (> 1 month)
1. [Action]: [Expected outcome]

## SLI/SLO Proposals

| Service | SLI | Current | Proposed SLO | Error Budget |
|---------|-----|---------|--------------|--------------|
| [name]  | [availability] | [%] | [%] | [hours/month] |

## Next Steps
1. [Immediate action]
2. [Follow-up]
```

---

## Reliability Plan Template {#reliability-plan-template}

```markdown
# Reliability Plan: [Period/Focus]

## Summary
[One paragraph: Current reliability state, key priorities, expected outcomes]

## Incident Analysis

### Recent Incidents
| Date | Severity | Duration | Impact | Postmortem |
|------|----------|----------|--------|------------|
| [date] | [SEV] | [time] | [description] | [link] |

### Pattern Analysis
[What patterns emerge from recent incidents?]

## Priorities

### Critical (This Sprint)
| Item | Owner | Due Date | Status | Incident(s) |
|------|-------|----------|--------|-------------|
| [action] | [name] | [date] | [status] | [refs] |

### Important (This Quarter)
| Item | Owner | Due Date | Status | Incident(s) |
|------|-------|----------|--------|-------------|
| [action] | [name] | [date] | [status] | [refs] |

### Backlog (Future)
1. [Item]: [Brief description]

## Metrics
- MTTR (Mean Time to Recovery): [current] → [target]
- Incident Rate: [current] → [target]
- Action Item Completion Rate: [%]

## Next Review
[Date for next reliability review]
```

---

## Postmortem Template {#postmortem-template}

```markdown
# Postmortem: [Incident Title]

**Date**: [incident date]
**Duration**: [start time] - [end time] ([total hours])
**Severity**: [SEV level]
**Authors**: [postmortem participants]
**Status**: [Draft / Final]

## Summary
[2-3 sentences: What happened, what was the impact, how was it resolved]

## Impact
- Users affected: [count or percentage]
- Revenue impact: [if applicable]
- Duration of impact: [time]
- Services affected: [list]

## Timeline
| Time (UTC) | Event |
|------------|-------|
| [time] | [what happened] |

## Contributing Factors
1. **[Factor category]**: [Description of how this contributed]
2. **[Factor category]**: [Description of how this contributed]

## What Went Well
- [Thing that helped during incident]
- [Thing that worked as designed]

## What Went Poorly
- [Thing that made incident worse or longer]
- [Gap that was exposed]

## Where We Got Lucky
- [Thing that could have made it worse but didn't]

## Action Items
| Action | Owner | Due Date | Priority | Status |
|--------|-------|----------|----------|--------|
| [specific action] | [name] | [date] | [P1/P2/P3] | [status] |

## Lessons Learned
[What should we remember from this incident?]

## References
- [Link to incident Slack channel]
- [Link to relevant dashboards]
- [Link to deploy logs]
```

---

## Chaos Experiment Template {#chaos-experiment-template}

```markdown
# Chaos Experiment: [Name]

## Metadata
- **Date**: [execution date]
- **Target**: [service/system]
- **Environment**: [dev/staging/prod]
- **Engineer**: [name]

## Hypothesis
**Given**: [steady state description]
**When**: [failure condition]
**Then**: [expected behavior]

## Steady State Definition
| Metric | Normal Range | Measurement |
|--------|--------------|-------------|
| Request rate | [range] | [source] |
| Error rate | [range] | [source] |
| Latency p99 | [range] | [source] |

## Experiment Design

### Failure Type
[Network / Process / Resource / Dependency]

### Injection Method
```
[How failure will be introduced - e.g., toxiproxy, tc, kill -9]
```

### Blast Radius
- **Scope**: [% of traffic / # of instances]
- **Duration**: [time]
- **Affected Users**: [estimate]

### Abort Criteria
- Error rate > [threshold]
- Latency p99 > [threshold]
- [Other conditions]

### Rollback Plan
```
[How to remove the failure condition]
```

## Execution Log
| Time | Action | Observation |
|------|--------|-------------|
| [time] | [action] | [what happened] |

## Results

### Outcome
**[PASS / PARTIAL / FAIL / ABORT]**

### Observations
[What actually happened vs. hypothesis]

### Gaps Discovered
1. [Gap]: [Impact] → [Recommendation]

### Evidence
[Links to dashboards, logs, screenshots]

## Action Items
| Action | Owner | Priority | Due |
|--------|-------|----------|-----|
| [action] | [name] | [P1/P2/P3] | [date] |

## Lessons Learned
[What did we learn that applies beyond this experiment?]
```

---

## Resilience Report Template {#resilience-report-template}

```markdown
# Resilience Report: [System/Service]

## Executive Summary
[One paragraph: Overall resilience posture, critical findings, top recommendations]

## Scope
- Services tested: [list]
- Time period: [dates]
- Environments: [dev/staging/prod]
- Experiment count: [number]

## Experiments Summary
| Experiment | Target | Result | Critical Findings |
|------------|--------|--------|-------------------|
| [name] | [service] | [PASS/FAIL] | [findings] |

## Resilience Scorecard
| Capability | Status | Evidence |
|------------|--------|----------|
| Database failover | [PASS/FAIL] | [experiment ref] |
| Circuit breakers | [PASS/FAIL] | [experiment ref] |
| Graceful degradation | [PASS/FAIL] | [experiment ref] |
| Auto-recovery | [PASS/FAIL] | [experiment ref] |
| Rollback procedures | [PASS/FAIL] | [experiment ref] |

## Critical Gaps
| Gap | Impact | Priority | Remediation |
|-----|--------|----------|-------------|
| [gap] | [impact] | [P1/P2/P3] | [fix] |

## Recommendations

### Immediate (This Week)
1. [Action]: [Expected improvement]

### Short-Term (This Month)
1. [Action]: [Expected improvement]

### Long-Term (This Quarter)
1. [Action]: [Expected improvement]

## Failure Mode Catalog
| Mode | Detection | Impact | Mitigation |
|------|-----------|--------|------------|
| [failure] | [how detected] | [blast radius] | [how to mitigate] |

## Next Steps
1. [Immediate action]
2. [Follow-up experiments]
3. [Remediation tracking]
```

---

## Debt Ledger Template {#debt-ledger-template}

```markdown
# Technical Debt Ledger
Generated: [date]
Scope: [what was audited]
Audit Type: [full | incremental | targeted]

## Summary
| Category    | Count | New Since Last | Notes           |
|-------------|-------|----------------|-----------------|
| Code Debt   | XX    | +X             |                 |
| Doc Debt    | XX    | +X             |                 |
| Test Debt   | XX    | +X             |                 |
| Infra Debt  | XX    | +X             |                 |
| Design Debt | XX    | +X             |                 |

## Code Debt

### Shortcuts and TODOs
| ID   | Location           | Description              | Age    | Owner   |
|------|-------------------|--------------------------|--------|---------|
| C001 | src/auth/login.js | TODO: Add rate limiting  | 6 mo   | @team-a |

### Complexity Issues
[Similar table format]

### Deprecated Usage
[Similar table format]

## Doc Debt
[Category sections continue...]

## Test Debt
[Category sections continue...]

## Infra Debt
[Category sections continue...]

## Design Debt
[Category sections continue...]

## Audit Notes
- Areas not covered: [list]
- Items requiring clarification: [list]
- Recommended follow-up: [list]
```

---

## Risk Matrix Template {#risk-matrix-template}

```markdown
# Debt Risk Assessment
Generated: [date]
Ledger Version: [ref]
Items Assessed: [count]

## Executive Summary
- Critical items requiring immediate attention: [count]
- High priority items for near-term planning: [count]
- Total estimated remediation effort: [range]
- Top recommendation: [brief statement]

## Risk Matrix

### Critical Priority (Address Immediately)
| ID   | Description          | Blast | Likelihood | Effort | Score | Recommendation    |
|------|---------------------|-------|------------|--------|-------|-------------------|
| C003 | Auth rate limiting  | 5     | 4          | 2      | 10.0  | Sprint 1, P0      |

### High Priority (This Sprint/Next Sprint)
[Similar table format]

### Medium Priority (This Quarter)
[Similar table format]

### Low Priority (Opportunistic)
[Similar table format]

## Quick Wins
Items with high value (Blast * Likelihood >= 6) and low effort (Effort <= 2):
| ID   | Description          | Impact | Effort | Why Quick Win           |
|------|---------------------|--------|--------|-------------------------|
| T012 | Flaky test in CI    | 4      | 1      | 30-min fix, blocks PRs  |

## Risk Clusters
Related items that should be addressed together:
1. Authentication cluster: C003, C007, C012 (shared security surface)
2. Database cluster: I004, I005 (related connection issues)

## Deferred Items (Rationale)
Items intentionally not prioritized and why:
- D001: Legacy module scheduled for deprecation in Q3
- C042: Covered by upcoming feature rewrite

## Assessment Notes
- Items requiring additional context: [list]
- External dependencies affecting priority: [list]
- Assumptions made: [list]
```

---

## Sprint Debt Packages Template {#sprint-debt-packages-template}

```markdown
# Debt Sprint Plan
Generated: [date]
Risk Matrix Version: [ref]
Planning Horizon: [X sprints]
Capacity Assumption: [X points/hours per sprint for debt]

## Sprint [N] Debt Allocation

### Package: [Title]
**Summary**: [What this package accomplishes]
**Effort**: [T-shirt size] ([X-Y hours/points])
**Confidence**: [High/Medium/Low]

**Items Included:**
| ID   | Description          | Individual Effort | Priority |
|------|---------------------|-------------------|----------|
| C003 | Auth rate limiting  | M (4-6h)          | Critical |
| C007 | Session timeout fix | S (2-3h)          | High     |

**Dependencies:**
- Requires: None
- Blocks: Package "API Security Hardening" in Sprint N+1

**Skills Required:** Backend security, auth system familiarity

**Acceptance Criteria:**
- [ ] Rate limiting implemented with configurable thresholds
- [ ] Session timeout correctly enforced across all auth paths
- [ ] Tests added covering new security behaviors
- [ ] Security review completed

**Remediation Risk:** Medium - Auth changes require careful testing

---

### Package: [Quick Wins Bundle]
[Similar format for additional packages]

---

## Sprint [N+1] Debt Allocation
[Continue for each sprint in horizon]

## Capacity Summary
| Sprint | Available | Allocated | Buffer | Remaining |
|--------|-----------|-----------|--------|-----------|
| N      | 40h       | 32h       | 6h     | 2h        |
| N+1    | 40h       | 28h       | 6h     | 6h        |

## Deferred to Future Sprints
| ID   | Description          | Reason for Deferral          |
|------|---------------------|------------------------------|
| I004 | DB connection pool  | Needs architect input first  |

## Assumptions & Constraints
- Sprint length: 2 weeks
- Debt allocation: 20% of capacity
- Team composition: [description]
- External dependencies: [list]
```

---

## Tracking Plan Template {#tracking-plan-template}

```markdown
# TRACK-{slug}

## Overview
{What user journey or feature this tracks}

## Business Questions
- {Question 1 this data answers}
- {Question 2}

## Naming Convention
{event_category_action, e.g., onboarding_step_completed}

## Events

### {event_name}
- **Trigger**: {When this event fires}
- **Category**: {Funnel step, engagement, error, etc.}
- **Platform**: {Web, iOS, Android, Server}

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| {property} | {string/int/bool} | {Yes/No} | {What it represents} |

### Validation Rules
- {Rule 1, e.g., "step_number must be 1-5"}
- {Rule 2}

## Implementation Notes
{Code examples, edge cases, gotchas}

## QA Checklist
- [ ] Events fire on expected triggers
- [ ] All required properties present
- [ ] Property values within expected ranges
- [ ] No duplicate events
- [ ] Works across platforms
```

---

## Usage Guidelines

### When to Use Which Template

**Observability Report**: Auditing current monitoring/logging/tracing coverage
**Reliability Plan**: Quarterly/sprint planning for reliability work
**Postmortem**: After any production incident (severity 2+)
**Chaos Experiment**: Before running any chaos engineering test
**Resilience Report**: After series of chaos experiments to assess overall posture
**Debt Ledger**: Regular audits (quarterly or on-demand) of technical debt
**Risk Matrix**: After debt ledger to prioritize remediation
**Sprint Debt Packages**: Planning sprints with debt allocation
**Tracking Plan**: Before implementing new analytics events

### Integration with Development Workflow

These templates complement the core development workflow (PRD/TDD/ADR/Test Plan):

- **Observability Reports** → inform TDD non-functional requirements
- **Postmortems** → generate ADRs for architectural changes
- **Chaos Experiments** → validate TDD reliability assumptions
- **Debt Ledgers** → inform refactoring PRDs
- **Tracking Plans** → become requirements in feature PRDs

### Related Skills

- **documentation** - Core PRD/TDD/ADR/Test Plan templates
- **10x-workflow** - Agent coordination for multi-phase work
- **standards** - Code quality and architectural conventions
