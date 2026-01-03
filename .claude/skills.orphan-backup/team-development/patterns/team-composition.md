# Team Composition Patterns

How to size and structure agent teams.

---

## Decision Framework

```
How complex is the domain?
├─ Simple/focused (single concern) → 3 agents
├─ Standard (multiple concerns) → 4 agents
└─ Full lifecycle (many concerns) → 5 agents
```

---

## The 3-Role Model (Focused)

For specialized, single-concern domains.

### Structure
```
Entry → Analyze → Plan
```

### Example: debt-triage-pack
| Agent | Role | Produces |
|-------|------|----------|
| debt-collector | Inventory debt | debt-ledger |
| risk-assessor | Evaluate risk | risk-report |
| sprint-planner | Plan paydown | sprint-plan |

### When to Use
- Domain has clear, linear flow
- No implementation phase (planning only)
- Single type of output
- Teams that plan but don't execute

### Characteristics
- Model mix: haiku → sonnet → sonnet
- Colors: orange → cyan → pink
- No validation phase (output is the plan)

---

## The 4-Role Model (Standard)

Most common pattern for balanced teams.

### Structure
```
Entry → Design → Execute → Validate
```

### Example: sre-pack
| Agent | Role | Produces |
|-------|------|----------|
| observability-engineer | Assess monitoring | observability-report |
| incident-commander | Plan reliability | reliability-plan |
| platform-engineer | Build infrastructure | infrastructure-changes |
| chaos-engineer | Verify resilience | resilience-report |

### When to Use
- Domain requires discovery, planning, execution, and validation
- Full lifecycle from assessment to verification
- Multiple types of output
- Teams that both plan and execute

### Characteristics
- Model mix: sonnet → opus → sonnet → opus
- Colors: orange → purple → cyan → red
- Validation phase closes the loop

### Variations

**doc-team-pack:**
```
Audit → Architecture → Writing → Review
```

**hygiene-pack:**
```
Assessment → Planning → Execution → Audit
```

---

## The 5-Role Model (Full Lifecycle)

For complex domains requiring orchestration.

### Structure
```
                    ┌─ Coordinator ─┐
                    │               │
Entry → Design → Execute → Validate
```

### Example: 10x-dev-pack
| Agent | Role | Produces |
|-------|------|----------|
| orchestrator | Coordinate phases | (coordination) |
| requirements-analyst | Capture intent | prd |
| architect | Design solution | tdd, adr |
| principal-engineer | Implement code | code |
| qa-adversary | Validate quality | test-plan |

### When to Use
- Complex multi-phase initiatives
- Long-running projects (PLATFORM complexity)
- Multiple handoffs requiring coordination
- Need for explicit orchestration

### Characteristics
- Model mix: opus (coordinator) + standard 4-role
- Colors: purple (coordinator) + standard colors
- Orchestrator manages cross-phase concerns

---

## Role Mapping

### Universal Roles

| Position | Purpose | Examples |
|----------|---------|----------|
| Entry | Start workflow, gather info | requirements-analyst, doc-auditor, observability-engineer |
| Design | Plan approach | architect, information-architect, incident-commander |
| Execute | Do the work | principal-engineer, tech-writer, platform-engineer |
| Validate | Verify quality | qa-adversary, doc-reviewer, chaos-engineer |
| Coordinate | Orchestrate phases | orchestrator |

### Role Naming Conventions

| Pattern | Examples | When to Use |
|---------|----------|-------------|
| `{noun}-{role}` | requirements-analyst, debt-collector | Clear domain + function |
| `{adjective}-{role}` | principal-engineer, tech-writer | Seniority + function |
| `{domain}-{action}` | code-smeller, audit-lead | Domain + what they do |
| `{single-word}` | orchestrator, architect, janitor | Well-known roles |

---

## Agent Count Guidelines

| Count | Phases | Complexity | Example Teams |
|-------|--------|------------|---------------|
| 3 | 3 | Planning-focused | debt-triage |
| 4 | 4 | Balanced lifecycle | doc, hygiene, sre |
| 5 | 4 + coordinator | Full lifecycle | 10x-dev |

### Warning Signs

**Too few agents:**
- Single agent doing unrelated tasks
- No clear handoff points
- Missing validation

**Too many agents:**
- Agents with overlapping responsibilities
- Trivial handoffs between agents
- Single-task agents

---

## Team Specialization

### Domain Alignment
Each team should have a clear domain:

| Team | Domain | What They Don't Do |
|------|--------|-------------------|
| 10x-dev | Feature development | Documentation cleanup |
| doc-team | Documentation | Code changes |
| hygiene | Code quality | New features |
| debt-triage | Debt management | Debt paydown (plans only) |
| sre | System reliability | Feature development |

### Cross-Team Handoffs
Teams note when work belongs elsewhere:

```markdown
## Cross-Team Notes

When {finding} reveals:
- Documentation gaps → Note for doc-team-pack
- Code quality issues → Note for hygiene-pack
- Technical debt → Note for debt-triage-pack
```
