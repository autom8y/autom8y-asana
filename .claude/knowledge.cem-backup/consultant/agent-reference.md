# Agent Reference

> Quick reference for all agents across teams

---

## Global Agents (7 total)

### Consultant

| Agent | Model | Purpose |
|-------|-------|---------|
| **consultant** | opus | Ecosystem navigation, command-flows |

### The Forge (6 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **agent-designer** | opus | design | TEAM-SPEC, role definitions |
| **prompt-architect** | opus | prompting | Agent .md files |
| **workflow-engineer** | opus | orchestration | workflow.yaml, commands |
| **platform-engineer** | sonnet | infrastructure | Roster files |
| **eval-specialist** | opus | validation | eval-report.md |
| **agent-curator** | sonnet | integration | Roster entry, Consultant sync |

**Workflow**: design → prompting → orchestration → infrastructure → validation → integration

**Complexity Levels**: PATCH, TEAM, ECOSYSTEM

---

## 10x-dev-pack (5 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **orchestrator** | opus | coordination | Work breakdown, routing |
| **requirements-analyst** | opus | requirements | PRD |
| **architect** | opus | design | TDD, ADRs |
| **principal-engineer** | sonnet | implementation | Code, tests |
| **qa-adversary** | opus | validation | Test report, defects |

**Workflow**: requirements → design → implementation → validation

---

## doc-team-pack (4 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **documentation-analyst** | opus | scoping | Doc plan |
| **technical-writer** | opus | drafting | Draft content |
| **editor** | opus | editing | Polished content |
| **publisher** | sonnet | publishing | Published docs |

**Workflow**: scoping → drafting → editing → publishing

---

## hygiene-pack (4 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **audit-lead** | opus | assessment | Audit report |
| **code-smeller** | sonnet | detection | Smell inventory |
| **janitor** | sonnet | remediation | Clean code |
| **architect-enforcer** | opus | validation | Compliance report |

**Workflow**: assessment → detection → remediation → validation

---

## debt-triage-pack (3 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **debt-detective** | opus | discovery | Debt inventory |
| **prioritizer** | opus | prioritization | Priority matrix |
| **paydown-planner** | opus | planning | Paydown roadmap |

**Workflow**: discovery → prioritization → planning

---

## sre-pack (4 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **incident-commander** | opus | response | Incident timeline |
| **postmortem-author** | opus | analysis | Postmortem doc |
| **reliability-engineer** | sonnet | remediation | Fixes, alerts |
| **capacity-planner** | opus | planning | Capacity plan |

**Workflow**: response → analysis → remediation → planning

---

## security-pack (4 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **threat-modeler** | opus | threat-modeling | Threat model |
| **compliance-architect** | opus | compliance-design | Compliance reqs |
| **penetration-tester** | sonnet | penetration-testing | Pentest report |
| **security-reviewer** | opus | security-review | Security signoff |

**Workflow**: threat-modeling → compliance-design → penetration-testing → security-review

---

## intelligence-pack (4 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **analytics-engineer** | sonnet | instrumentation | Tracking plan |
| **user-researcher** | opus | research | Research findings |
| **experimentation-lead** | opus | experimentation | Experiment design |
| **insights-analyst** | opus | synthesis | Insights report |

**Workflow**: instrumentation → research → experimentation → synthesis

---

## rnd-pack (4 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **technology-scout** | sonnet | scouting | Tech assessment |
| **integration-researcher** | sonnet | integration-analysis | Integration map |
| **prototype-engineer** | sonnet | prototyping | Prototype |
| **moonshot-architect** | opus | future-architecture | Moonshot plan |

**Workflow**: scouting → integration-analysis → prototyping → future-architecture

---

## strategy-pack (4 agents)

| Agent | Model | Phase | Produces |
|-------|-------|-------|----------|
| **market-researcher** | sonnet | market-research | Market analysis |
| **competitive-analyst** | opus | competitive-analysis | Competitive intel |
| **business-model-analyst** | opus | business-modeling | Financial model |
| **roadmap-strategist** | opus | strategic-planning | Strategic roadmap |

**Workflow**: market-research → competitive-analysis → business-modeling → strategic-planning

---

## Agent by Purpose

### Analysis/Planning

| Need | Agent | Team |
|------|-------|------|
| Requirements gathering | requirements-analyst | 10x-dev-pack |
| System design | architect | 10x-dev-pack |
| Threat analysis | threat-modeler | security-pack |
| Market research | market-researcher | strategy-pack |
| User research | user-researcher | intelligence-pack |
| Debt discovery | debt-detective | debt-triage-pack |
| Tech exploration | technology-scout | rnd-pack |

### Implementation

| Need | Agent | Team |
|------|-------|------|
| Feature coding | principal-engineer | 10x-dev-pack |
| Code cleanup | janitor | hygiene-pack |
| Prototype building | prototype-engineer | rnd-pack |
| Analytics setup | analytics-engineer | intelligence-pack |
| Reliability fixes | reliability-engineer | sre-pack |

### Validation/Review

| Need | Agent | Team |
|------|-------|------|
| Testing | qa-adversary | 10x-dev-pack |
| Security review | security-reviewer | security-pack |
| Architecture compliance | architect-enforcer | hygiene-pack |
| Experiment analysis | insights-analyst | intelligence-pack |

### Documentation/Communication

| Need | Agent | Team |
|------|-------|------|
| Technical writing | technical-writer | doc-team-pack |
| Editing | editor | doc-team-pack |
| Postmortem authoring | postmortem-author | sre-pack |
| Strategic roadmap | roadmap-strategist | strategy-pack |

---

## Model Usage

### Opus (Deep Reasoning)
- Complex analysis
- Design decisions
- Strategic planning
- Thorough review

### Sonnet (Execution Focus)
- Implementation tasks
- Routine operations
- Fast iteration
- Breadth scanning
