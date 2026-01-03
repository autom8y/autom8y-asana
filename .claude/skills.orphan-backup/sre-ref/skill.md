---
name: sre-ref
description: "Quick switch to sre-pack (reliability workflow). Shows team roster after switch. Triggers: /sre, reliability team, SRE workflow, observability, chaos engineering."
---

# /sre - Quick Switch to Reliability Team

> **Category**: Team Management | **Phase**: Team Switching

## Purpose

Instantly switch to the sre-pack, a Site Reliability Engineering team focused on system reliability, observability, incident response, and chaos engineering.

This is a convenience wrapper around `/team sre-pack` that also displays the team roster after switching.

---

## Usage

```bash
/sre
```

No parameters required. This command:
1. Switches to sre-pack
2. Displays team roster with agent descriptions

---

## Behavior

### 1. Invoke Team Switch

Execute via Bash tool:

```bash
~/Code/roster/swap-team.sh sre-pack
```

### 2. Display Team Roster

After successful switch, show the active team roster:

```
Switched to sre-pack (4 agents loaded)

Team Roster:
┌─────────────────────────┬──────────────────────────────────────────────┐
│ Agent                   │ Role                                         │
├─────────────────────────┼──────────────────────────────────────────────┤
│ observability-engineer  │ Metrics, logs, traces, dashboards, alerts    │
│ incident-commander      │ War room coordination, postmortems           │
│ platform-engineer       │ CI/CD, IaC, deployment automation            │
│ chaos-engineer          │ Fault injection, resilience testing          │
└─────────────────────────┴──────────────────────────────────────────────┘

Use /handoff <agent> to delegate work.
```

### 3. Update SESSION_CONTEXT (if active)

If a session is active:
- Update `active_team` field to `sre-pack`
- Add handoff note documenting team switch

---

## Team Details

**Team Name**: sre-pack
**Agent Count**: 4
**Workflow**: Observation → Coordination → Implementation → Resilience

### Workflow Diagram

```
┌──────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    ┌────────────────┐
│   Observation    │───▶│    Coordination     │───▶│   Implementation    │───▶│   Resilience   │
│ (Observability   │    │    (Incident        │    │    (Platform        │    │   (Chaos       │
│   Engineer)      │    │     Commander)      │    │     Engineer)       │    │    Engineer)   │
└──────────────────┘    └─────────────────────┘    └─────────────────────┘    └────────────────┘
        │                        │                          │                        │
        ▼                        ▼                          ▼                        ▼
  observability-          reliability-             infrastructure-           resilience-
     report                  plan                    changes                   report
```

### Complexity Levels

| Level | Scope | Phases |
|-------|-------|--------|
| ALERT | Single alert/dashboard fix | implementation, resilience |
| SERVICE | Single service reliability | observation, coordination, implementation, resilience |
| SYSTEM | Multi-service SLOs/SLIs | observation, coordination, implementation, resilience |
| PLATFORM | Full platform reliability | observation, coordination, implementation, resilience |

---

## Agents

### observability-engineer.md
**Role**: Metrics, logs, traces, dashboards, alerts
**Invocation**: `Act as **Observability Engineer**`
**Purpose**: Makes the invisible visible—catches degradation before customers do

**Color**: Orange | **Model**: Claude Sonnet

**When to use**:
- Evaluating monitoring coverage and gaps
- Designing dashboards and alerting
- Defining SLIs and SLOs
- Instrumenting applications for observability

**Produces**:
- Observability reports
- Dashboard specifications
- Alert configurations
- SLI/SLO definitions

---

### incident-commander.md
**Role**: War room coordination, postmortems
**Invocation**: `Act as **Incident Commander**`
**Purpose**: Runs the war room when systems are on fire; prevents repeat incidents through blameless postmortems

**Color**: Purple | **Model**: Claude Opus

**When to use**:
- Active incident requiring coordination
- Post-incident analysis and postmortems
- Reliability planning and prioritization
- Stakeholder communication during outages

**Produces**:
- Reliability plans
- Postmortem documents
- Incident timelines
- Action item tracking

---

### platform-engineer.md
**Role**: CI/CD, IaC, deployment automation
**Invocation**: `Act as **Platform Engineer**`
**Purpose**: Builds the roads developers drive on—makes deploying to production boring

**Color**: Cyan | **Model**: Claude Sonnet

**When to use**:
- CI/CD pipeline improvements
- Infrastructure as code changes
- Developer environment optimization
- Deployment reliability work

**Produces**:
- Pipeline configurations
- Infrastructure code
- Developer tools and scripts
- Runbooks

---

### chaos-engineer.md
**Role**: Fault injection, resilience testing
**Invocation**: `Act as **Chaos Engineer**`
**Purpose**: Breaks production on purpose—finds cracks in resilience before real outages do

**Color**: Red | **Model**: Claude Opus

**When to use**:
- Verifying resilience claims
- Testing failure scenarios
- Validating rollback procedures
- Pre-release resilience certification

**Produces**:
- Chaos experiments
- Resilience reports
- Failure mode catalogs
- Runbook updates

---

## Command Mapping

When sre-pack is active, commands route to these agents:

| Command | Routes To | Purpose |
|---------|-----------|---------|
| `/start` | observability-engineer | Begin with observability assessment |
| `/architect` | platform-engineer | Design infrastructure/platform changes |
| `/build` | platform-engineer | Implement infrastructure changes |
| `/qa` | chaos-engineer | Validate resilience through chaos testing |
| `/hotfix` | incident-commander | Fast incident response path |
| `/code-review` | chaos-engineer | Review for reliability patterns |

---

## When to Use This Team

**Use sre-pack for**:
- Observability improvements (dashboards, alerts, SLOs)
- Incident response preparation
- Platform and infrastructure work
- Chaos engineering and resilience testing
- Post-incident analysis and prevention

**Don't use for**:
- Feature development (use 10x-dev-pack)
- Documentation cleanup (use doc-team-pack)
- Code quality/refactoring (use hygiene-pack)
- Technical debt triage (use debt-triage-pack)

---

## Integration with Other Teams

The SRE pack often collaborates with other teams:

| Situation | Integration |
|-----------|-------------|
| Reliability issues in code | Hand off to 10x-dev-pack for fixes |
| Documentation gaps in runbooks | Hand off to doc-team-pack |
| Technical debt causing incidents | Hand off to debt-triage-pack |
| Code quality affecting reliability | Hand off to hygiene-pack |

---

## Example Workflows

### Observability Improvement
```
/sre
/start "Improve monitoring coverage for payment service"
→ Observability Engineer assesses gaps
→ Incident Commander prioritizes improvements
→ Platform Engineer implements dashboards/alerts
→ Chaos Engineer validates detection works
```

### Incident Post-Mortem
```
/sre
/hotfix "Database outage caused 30-minute downtime"
→ Incident Commander runs postmortem
→ Produces action items
→ Platform Engineer implements fixes
→ Chaos Engineer validates resilience
```

### Pre-Launch Resilience
```
/sre
/task "Certify checkout service for Black Friday traffic"
→ Observability Engineer baselines metrics
→ Chaos Engineer runs stress tests
→ Documents breaking points and mitigations
```
