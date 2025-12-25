# Routing Decision Trees

> Structured routing logic for the Consultant

---

## Primary Router

```
User Intent
│
├─ BUILD/CREATE something?
│   │
│   ├─ New feature/functionality
│   │   └─ → /10x → /task
│   │
│   ├─ Documentation
│   │   └─ → /docs → /task
│   │
│   ├─ Prototype/exploration
│   │   └─ → /rnd → /task
│   │
│   └─ Unknown scope
│       └─ → Ask: "What are you building?"
│
├─ FIX/IMPROVE something?
│   │
│   ├─ Bug/broken behavior
│   │   ├─ Urgent → /hotfix
│   │   └─ Not urgent → /10x → /task
│   │
│   ├─ Performance issue
│   │   ├─ Reliability concern → /sre → /task
│   │   └─ Code optimization → /hygiene → /task
│   │
│   ├─ Security vulnerability
│   │   └─ → /security → /task
│   │
│   ├─ Code quality
│   │   └─ → /hygiene → /task
│   │
│   └─ Technical debt
│       └─ → /debt → /task
│
├─ REVIEW/VALIDATE something?
│   │
│   ├─ Code review
│   │   └─ → /code-review
│   │
│   ├─ QA/testing
│   │   └─ → /qa
│   │
│   ├─ Security review
│   │   └─ → /security → /task
│   │
│   └─ Architecture review
│       └─ → /architect
│
├─ RESEARCH/ANALYZE something?
│   │
│   ├─ Technical feasibility
│   │   └─ → /spike
│   │
│   ├─ Technology evaluation
│   │   └─ → /rnd → /task
│   │
│   ├─ Market/competitors
│   │   └─ → /strategy → /task
│   │
│   ├─ User behavior
│   │   └─ → /intelligence → /task
│   │
│   └─ Unknown type
│       └─ → Ask: "What kind of research?"
│
└─ MANAGE/COORDINATE something?
    │
    ├─ Multiple tasks
    │   └─ → /sprint
    │
    ├─ Session management
    │   ├─ Start → /start
    │   ├─ Pause → /park
    │   ├─ Resume → /continue
    │   └─ Finish → /wrap
    │
    └─ Team switching
        └─ → /team or quick-switch
```

---

## Team Selection Tree

```
What domain?
│
├─ Feature Development
│   └─ → 10x-dev-pack (/10x)
│
├─ Documentation
│   └─ → doc-team-pack (/docs)
│
├─ Code Quality/Refactoring
│   └─ → hygiene-pack (/hygiene)
│
├─ Technical Debt
│   └─ → debt-triage-pack (/debt)
│
├─ Operations/Reliability
│   └─ → sre-pack (/sre)
│
├─ Security/Compliance
│   └─ → security-pack (/security)
│
├─ Analytics/Experiments
│   └─ → intelligence-pack (/intelligence)
│
├─ R&D/Exploration
│   └─ → rnd-pack (/rnd)
│
└─ Strategy/Business
    └─ → strategy-pack (/strategy)
```

---

## Complexity Selection Tree

```
What scope?
│
├─ Single file/function
│   └─ → Lowest level (SCRIPT, SPOT, PAGE, QUICK, etc.)
│
├─ Module/component
│   └─ → Middle level (MODULE)
│
├─ Service/subsystem
│   └─ → High level (SERVICE)
│
└─ Entire system/platform
    └─ → Highest level (PLATFORM, CODEBASE, SYSTEM)
```

---

## Urgency Tree

```
How urgent?
│
├─ Production is down
│   └─ → /sre → incident response
│
├─ Critical security issue
│   └─ → /security → immediate review
│
├─ Bug blocking users
│   └─ → /hotfix
│
├─ Important but not urgent
│   └─ → Normal workflow (/task)
│
└─ Nice to have
    └─ → Backlog or /spike for exploration
```

---

## Cross-Team Scenarios

### Security + Development

```
Feature touches auth/crypto?
│
├─ Yes
│   ├─ 1. /security → threat modeling
│   ├─ 2. /10x → implementation
│   └─ 3. /security → security review
│
└─ No
    └─ → Standard /10x workflow
```

### R&D → Production

```
Prototype successful?
│
├─ Yes, ready for production
│   ├─ 1. /10x → productionize
│   └─ 2. Full development workflow
│
└─ No, needs more exploration
    └─ → Continue /rnd
```

### Debt → Feature

```
Tech debt blocking feature?
│
├─ Yes
│   ├─ 1. /debt → identify scope
│   ├─ 2. /hygiene → remediate
│   └─ 3. /10x → build feature
│
└─ No
    └─ → Direct to /10x
```

---

## Playbook Selection Tree

```
Common scenario?
│
├─ New feature development
│   └─ → playbook: new-feature
│
├─ Bug fix
│   └─ → playbook: bug-fix
│
├─ Code quality audit
│   └─ → playbook: code-audit
│
├─ Documentation update
│   └─ → playbook: documentation-refresh
│
├─ Security assessment
│   └─ → playbook: security-review
│
├─ Performance optimization
│   └─ → playbook: performance-optimization
│
├─ Tech debt sprint
│   └─ → playbook: tech-debt-sprint
│
├─ Production incident
│   └─ → playbook: incident-response
│
└─ Novel scenario
    └─ → Generate custom playbook
```

---

## Fallback Logic

```
Can't determine intent?
│
├─ Ask clarifying question
│   └─ "What are you trying to accomplish?"
│
├─ Suggest exploration
│   └─ /consult --team to see options
│
└─ Default recommendation
    └─ Start with /10x for general development
```
