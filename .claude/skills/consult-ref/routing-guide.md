# Routing Guide

> Deep dive on how the Consultant routes user requests

## Overview

The Consultant uses a multi-layer routing system:

```
User Request
     │
     ▼
┌─────────────────┐
│ Intent Patterns │ ← Natural language matching
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Decision Trees  │ ← Structured routing logic
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Complexity      │ ← Scope-based selection
│ Matrix          │
└────────┬────────┘
         │
         ▼
   Team/Command
   Recommendation
```

---

## Intent Pattern Matching

### How It Works

1. Extract keywords from user request
2. Match against known patterns
3. Identify likely intent category
4. Suggest appropriate team/command

### Pattern Categories

| Category | Keywords |
|----------|----------|
| Development | build, create, implement, add, feature |
| Bug Fix | fix, bug, broken, debug, not working |
| Documentation | document, docs, readme, explain |
| Quality | quality, clean, refactor, improve code |
| Debt | debt, legacy, outdated, technical debt |
| Security | security, vulnerability, auth, compliance |
| Research | explore, investigate, research, spike |
| Analytics | analytics, metrics, A/B, experiment |
| Strategy | market, competitive, business, roadmap |
| Operations | incident, outage, performance, reliability |

### Disambiguation

When patterns overlap:
- "Improve performance" → Could be /sre or /hygiene
- "Research" → Could be /spike, /rnd, /intelligence, or /strategy

The Consultant asks clarifying questions or considers context.

---

## Decision Tree Logic

### Primary Router

```
What is the primary action?

BUILD/CREATE
├─ Feature/functionality → /10x
├─ Documentation → /docs
├─ Prototype → /rnd
└─ Unknown → Ask "What are you building?"

FIX/IMPROVE
├─ Bug → /hotfix (urgent) or /10x (complex)
├─ Performance → /sre or /hygiene
├─ Security → /security
├─ Quality → /hygiene
└─ Tech debt → /debt

REVIEW/VALIDATE
├─ Code review → /code-review
├─ QA → /qa
├─ Security → /security
└─ Architecture → /architect

RESEARCH/ANALYZE
├─ Technical feasibility → /spike
├─ Technology evaluation → /rnd
├─ Market/competitors → /strategy
├─ User behavior → /intelligence
└─ Unknown → Ask "What kind of research?"

MANAGE/COORDINATE
├─ Multiple tasks → /sprint
├─ Session → /start, /park, /continue, /wrap
└─ Team → /team
```

### Team Selection

Each team has clear domain boundaries:

| Domain | Primary Team | Secondary |
|--------|--------------|-----------|
| Features | 10x-dev-pack | - |
| Docs | doc-team-pack | - |
| Quality | hygiene-pack | - |
| Debt | debt-triage-pack | hygiene-pack |
| Operations | sre-pack | - |
| Security | security-pack | - |
| Analytics | intelligence-pack | - |
| R&D | rnd-pack | - |
| Strategy | strategy-pack | - |

### Cross-Domain Routing

Some tasks span multiple teams:

```
Security + Development:
/security (threat model) → /10x (implement) → /security (review)

Debt + Quality:
/debt (prioritize) → /hygiene (remediate)

R&D + Development:
/rnd (prototype) → /10x (productionize)
```

---

## Complexity Matrix

### Determining Complexity

| Signal | Lower | Higher |
|--------|-------|--------|
| Files affected | 1-2 | 5+ |
| Dependencies | None | Many |
| Risk | Low | High |
| Reversibility | Easy | Hard |
| Stakeholders | Just me | Multiple teams |

### Team-Specific Levels

Each team defines its own:

**10x-dev-pack**: SCRIPT → MODULE → SERVICE → PLATFORM

**hygiene-pack**: SPOT → MODULE → CODEBASE

**security-pack**: PATCH → FEATURE → SYSTEM

### Escalation Rules

Always escalate when:
- Security implications
- Breaking changes
- External API changes
- Data model changes
- Multiple teams affected

---

## Playbook Selection

### When to Use Curated

Match user scenario to playbook:

| Scenario | Playbook |
|----------|----------|
| New feature | new-feature.md |
| Bug to fix | bug-fix.md |
| Code quality | code-audit.md |
| Update docs | documentation-refresh.md |
| Security check | security-review.md |
| Speed up app | performance-optimization.md |
| Pay down debt | tech-debt-sprint.md |
| Production down | incident-response.md |

### When to Generate

Generate custom playbook when:
- No curated match
- Multiple teams involved
- Unique constraints
- Custom workflow needed

### Generation Process

1. Parse user intent
2. Select primary team
3. Determine phases needed
4. Add decision points
5. Format as playbook

---

## Fallback Logic

When routing is unclear:

1. **Ask clarifying question**
   - "What are you trying to accomplish?"
   - "Can you describe the scope?"

2. **Suggest exploration**
   - `/consult --team` to see options
   - `/consult --commands` for available commands

3. **Default recommendation**
   - Development: /10x
   - Unknown: Ask first

---

## Context Awareness

The Consultant considers:

- **Current team**: May influence recommendations
- **Active session**: State and phase matter
- **Recent work**: Pattern recognition
- **Git state**: Branch, uncommitted changes

This context is auto-injected via hooks.
