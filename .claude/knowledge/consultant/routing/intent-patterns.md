# Intent Pattern Matching

> Natural language → team/command mapping

---

## Development Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "build a feature" | Full development | `/10x` → `/task` |
| "add functionality" | Development | `/10x` → `/task` |
| "implement X" | Implementation | `/10x` → `/build` |
| "create a new..." | Development | `/10x` → `/task` |
| "develop" | Development | `/10x` → `/task` |

---

## Bug/Fix Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "fix a bug" | Hotfix | `/hotfix` |
| "something's broken" | Hotfix | `/hotfix` |
| "debug" | Investigation | `/hotfix` |
| "not working" | Hotfix | `/hotfix` |
| "urgent fix" | Fast path | `/hotfix` |
| "production issue" | Incident | `/sre` → `/task` |

---

## Documentation Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "document" | Documentation | `/docs` → `/task` |
| "write docs" | Documentation | `/docs` → `/task` |
| "API documentation" | Documentation | `/docs` → `/task` |
| "README" | Documentation | `/docs` → `/task` |
| "explain the code" | Documentation | `/docs` → `/task` |
| "update docs" | Documentation refresh | `/docs` → `/task` |

---

## Quality Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "code quality" | Hygiene | `/hygiene` → `/task` |
| "code review" | Review | `/code-review` |
| "clean up" | Hygiene | `/hygiene` → `/task` |
| "refactor" | Hygiene | `/hygiene` → `/task` |
| "improve code" | Hygiene | `/hygiene` → `/task` |
| "code smells" | Hygiene | `/hygiene` → `/task` |
| "linting" | Hygiene | `/hygiene` → `/task` |

---

## Technical Debt Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "technical debt" | Debt triage | `/debt` → `/task` |
| "tech debt" | Debt triage | `/debt` → `/task` |
| "pay down debt" | Debt paydown | `/debt` → `/task` |
| "legacy code" | Debt/Hygiene | `/debt` or `/hygiene` |
| "outdated dependencies" | Debt | `/debt` → `/task` |

---

## Security Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "security" | Security review | `/security` → `/task` |
| "vulnerability" | Security | `/security` → `/task` |
| "penetration test" | Security | `/security` → `/task` |
| "compliance" | Security | `/security` → `/task` |
| "audit" | Security/Hygiene | Context-dependent |
| "OWASP" | Security | `/security` → `/task` |
| "authentication" | Security + Dev | `/security` then `/10x` |

---

## Research/Exploration Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "explore" | Spike/R&D | `/spike` or `/rnd` |
| "investigate" | Research | `/spike` |
| "research" | Depends on type | See below |
| "prototype" | R&D | `/rnd` → `/task` |
| "proof of concept" | R&D | `/rnd` → `/task` |
| "feasibility" | Spike | `/spike` |
| "can we do X?" | Spike | `/spike` |
| "evaluate technology" | R&D | `/rnd` → `/task` |

### Research Type Disambiguation

| Research Type | Recommended |
|---------------|-------------|
| Technical feasibility | `/spike` |
| Technology evaluation | `/rnd` → `/task` |
| User research | `/intelligence` → `/task` |
| Market research | `/strategy` → `/task` |
| Competitive research | `/strategy` → `/task` |

---

## Analytics/Data Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "A/B test" | Experimentation | `/intelligence` → `/task` |
| "analytics" | Intelligence | `/intelligence` → `/task` |
| "tracking" | Instrumentation | `/intelligence` → `/task` |
| "metrics" | Intelligence | `/intelligence` → `/task` |
| "user research" | Intelligence | `/intelligence` → `/task` |
| "experiment" | Intelligence | `/intelligence` → `/task` |

---

## Strategy/Business Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "market analysis" | Strategy | `/strategy` → `/task` |
| "competitive analysis" | Strategy | `/strategy` → `/task` |
| "business model" | Strategy | `/strategy` → `/task` |
| "roadmap" | Strategy | `/strategy` → `/task` |
| "pricing" | Strategy | `/strategy` → `/task` |
| "go-to-market" | Strategy | `/strategy` → `/task` |

---

## Operations Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "incident" | SRE | `/sre` → `/task` |
| "outage" | SRE | `/sre` → `/task` |
| "performance" | SRE/Hygiene | Context-dependent |
| "reliability" | SRE | `/sre` → `/task` |
| "monitoring" | SRE | `/sre` → `/task` |
| "postmortem" | SRE | `/sre` → `/task` |
| "capacity planning" | SRE | `/sre` → `/task` |

---

## Session Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "start working on" | New session | `/start` |
| "pause" | Park session | `/park` |
| "continue" | Resume session | `/continue` |
| "finish up" | Wrap session | `/wrap` |
| "create PR" | Pull request | `/pr` |
| "ship it" | PR | `/pr` |

---

## Parallel/Isolation Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "work on multiple things" | Worktree | `/worktree create` |
| "parallel work" | Worktree | `/worktree create` |
| "concurrent sessions" | Worktree | `/worktree create` |
| "different team at same time" | Worktree | `/worktree create --team=X` |
| "multiple sprints" | Worktree | `/worktree create` per sprint |
| "isolated environment" | Worktree | `/worktree create` |
| "side-by-side work" | Worktree | `/worktree create` |
| "without affecting main" | Worktree | `/worktree create` |
| "separate workspace" | Worktree | `/worktree create` |
| "already have a session" | Check options | `/park` or `/worktree` |
| "list worktrees" | Worktree list | `/worktree list` |
| "clean up worktrees" | Worktree cleanup | `/worktree cleanup` |

### Parallel vs Park Decision

| Situation | Recommended |
|-----------|-------------|
| Need to switch focus temporarily | `/park` → `/start` |
| Need different team simultaneously | `/worktree create --team=X` |
| Want to isolate experimental work | `/worktree create` |
| Multiple terminals, same project | `/worktree create` per terminal |
| Quick context switch, same team | `/park` → `/continue` |

---

## Confusion/Help Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "I don't know where to start" | Guidance | `/consult` |
| "help" | Guidance | `/consult` |
| "what should I use" | Guidance | `/consult` |
| "which team" | Guidance | `/consult --team` |
| "what commands" | Guidance | `/consult --commands` |
| "how do I" | Guidance | `/consult` |

---

## Team Creation/Management Intents

| User Says | Likely Need | Recommended |
|-----------|-------------|-------------|
| "create a team" | The Forge | `/forge` → `/new-team` |
| "build a team" | The Forge | `/new-team` |
| "new agent team" | The Forge | `/new-team` |
| "add agents" | The Forge | `/new-team --complexity=PATCH` |
| "validate team" | Validation | `/validate-team` |
| "test agent" | Evaluation | `/eval-agent` |
| "check team" | Validation | `/validate-team` |
| "team creation" | The Forge | `/forge` |
| "agent factory" | The Forge | `/forge` |
| "modify team" | The Forge | `/new-team --complexity=PATCH` |

---

## Multi-Intent Patterns

| User Says | Likely Need | Recommended Sequence |
|-----------|-------------|----------------------|
| "build and document" | Dev + Docs | `/10x` → `/task` → `/docs` → `/task` |
| "fix and test" | Hotfix + QA | `/hotfix` |
| "audit and clean" | Hygiene full | `/hygiene` → `/task` |
| "research and prototype" | R&D full | `/rnd` → `/task` |
| "design and implement" | Dev phases | `/10x` → `/architect` → `/build` |
| "create and validate team" | Forge + Eval | `/new-team` → `/validate-team` |
