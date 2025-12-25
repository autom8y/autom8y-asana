# Command Decision Tree

## Metadata
- **Document Type**: Reference
- **Status**: Active
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Purpose**: Canonical reference for choosing the right command for each workflow scenario

## Overview

The autom8_asana project provides 21+ commands for different workflow scenarios. This decision tree helps you choose the right command based on your task type, urgency, and scope.

## Decision Tree

```
What are you trying to do?
│
├─ Switch teams?
│  ├─ Feature development → /10x
│  ├─ Documentation work → /docs
│  ├─ Code cleanup → /hygiene
│  ├─ Debt assessment → /debt
│  └─ Infrastructure/ops → /sre
│
├─ Execute work?
│  ├─ Single well-defined task → /task
│  ├─ Multiple related tasks → /sprint
│  ├─ Production emergency → /hotfix
│  └─ Technical investigation → /spike
│
├─ Manage session?
│  ├─ Start new work → /start
│  ├─ Finish and handoff → /wrap
│  ├─ Pause temporarily → /park
│  └─ Resume paused work → /continue
│
├─ Quality assurance?
│  ├─ Deep adversarial testing → /qa
│  ├─ Code review → /code-review
│  ├─ Create pull request → /pr
│  └─ Build and verify → /build
│
└─ Other?
   ├─ Architecture design → /architect
   ├─ Handoff between agents → /handoff
   └─ View sessions → /sessions
```

---

## Development Workflow Commands

### /task - Single Task Execution

**Use when**: Implementing a well-defined, single-phase task.

**Team**: 10x-dev-pack

**Phases**: Requirements → Design → Implementation → Validation

**Output**: PRD, TDD, Code, Tests, Validation Report

**Example scenarios**:
- "Implement cache invalidation hook"
- "Add custom field descriptor for Status field"
- "Fix bug in dependency graph algorithm"

**Command**:
```
/task "Implement progressive TTL extension for cache"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/task.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/task-ref/skill.md`

---

### /sprint - Multi-Task Sprint Planning

**Use when**: Planning multiple related tasks in a sprint or epic.

**Team**: 10x-dev-pack

**Phases**: Sprint planning → Task decomposition → Execution

**Output**: Sprint plan, task breakdown, prioritization, estimates

**Example scenarios**:
- "Plan Sprint 3: Detection system implementation"
- "Break down Cache Performance Epic into tasks"
- "Organize Q1 roadmap into sprints"

**Command**:
```
/sprint "Sprint 5: Business Model Implementation"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/sprint.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/sprint-ref/skill.md`

---

### /hotfix - Emergency Fix

**Use when**: Critical production bug requiring immediate fix.

**Team**: 10x-dev-pack (fast-track)

**Phases**: Requirements → Implementation → Validation → Deployment (no TDD)

**Output**: Minimal PRD, Code, Tests, Hotfix log

**Example scenarios**:
- "Fix production cache corruption bug"
- "Patch security vulnerability in authentication"
- "Resolve data loss issue in SaveSession"

**Command**:
```
/hotfix "Fix cache corruption in batch operations"
```

**Quality Gate Adjustments**:
- PRD minimal (problem + fix approach)
- TDD may be created retrospectively
- Focus on regression + fix validation

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/hotfix.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/hotfix-ref/skill.md`

---

### /spike - Technical Spike

**Use when**: Technical unknowns require investigation before implementation.

**Team**: 10x-dev-pack

**Phases**: Requirements → Investigation → Report (no implementation)

**Output**: Spike report, findings, recommendations

**Example scenarios**:
- "Investigate caching strategies for batch operations"
- "Evaluate Redis vs S3 for cache backend"
- "Research entity detection algorithms"

**Command**:
```
/spike "Investigate progressive TTL algorithms"
```

**Deliverable**: Spike report that can inform future PRD/TDD.

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/spike.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/spike-ref/skill.md`

---

## Team Management Commands

### /10x - Switch to 10x Development Pack

**Use when**: Full-cycle feature development.

**Team**:
- orchestrator
- requirements-analyst
- architect
- principal-engineer
- qa-adversary

**Workflow**: Requirements → Design → Implementation → Validation → Deployment

**Command**:
```
/10x
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/10x.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/10x-ref/skill.md`

---

### /docs - Switch to Documentation Team

**Use when**: Documentation-focused work (audits, writing, reviews).

**Team**:
- doc-auditor
- information-architect
- tech-writer
- doc-reviewer

**Workflow**: Audit → Architecture → Writing → Review

**Command**:
```
/docs
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/docs.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/docs-ref/skill.md`

---

### /hygiene - Switch to Hygiene Team

**Use when**: Code quality improvements, refactoring, test coverage.

**Team**: hygiene-focused agents

**Focus**: Code cleanup, technical debt reduction, test improvements

**Command**:
```
/hygiene
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/hygiene.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/hygiene-ref/skill.md`

---

### /debt - Switch to Debt Triage Team

**Use when**: Technical debt assessment and prioritization.

**Team**: debt-triage-focused agents

**Focus**: Identify, categorize, and prioritize technical debt

**Command**:
```
/debt
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/debt.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/debt-ref/skill.md`

---

### /sre - Switch to SRE Team

**Use when**: Operational reliability, monitoring, incident response.

**Team**: sre-focused agents

**Focus**: Infrastructure, runbooks, monitoring, deployments

**Command**:
```
/sre
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/sre.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/sre-ref/skill.md`

---

## Session Management Commands

### /start - Start New Session

**Use when**: Beginning work on an initiative.

**Output**: SESSION_CONTEXT created, work tracking initialized

**Command**:
```
/start "Implement cache optimization P2"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/start.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/start-ref/skill.md`

---

### /wrap - Complete Session

**Use when**: Finishing work, creating handoff.

**Output**: Summary, artifacts list, handoff notes

**Command**:
```
/wrap
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/wrap.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/wrap-ref/skill.md`

---

### /park - Pause Session

**Use when**: Temporarily pausing work.

**Output**: Current state saved, resumption notes

**Command**:
```
/park "Blocked on external dependency"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/park.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/park-ref/skill.md`

---

### /continue - Resume Session

**Use when**: Resuming paused work.

**Input**: Previous SESSION_CONTEXT

**Command**:
```
/continue
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/continue.md`

---

## Quality Assurance Commands

### /qa - Quality Adversarial Testing

**Use when**: Deep testing, edge case validation, finding bugs.

**Team**: qa-adversary

**Output**: Test Plan, Validation Report, bug reports

**Command**:
```
/qa "Validate cache invalidation edge cases"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/qa.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/qa-ref/skill.md`

---

### /code-review - Code Review

**Use when**: Reviewing pull request or code changes.

**Output**: Review comments, approval/rejection, improvement suggestions

**Command**:
```
/code-review "Review PR #42"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/code-review.md`

---

### /pr - Create Pull Request

**Use when**: Ready to merge code to main branch.

**Output**: GitHub PR with description, test plan, full commit history analysis

**Command**:
```
/pr "Cache optimization P2 implementation"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/pr.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/pr-ref/skill.md`

---

### /build - Build and Verify

**Use when**: Running full build, tests, and verification.

**Output**: Build status, test results, lint/type check results

**Command**:
```
/build
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/build.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/build-ref/skill.md`

---

## Specialized Commands

### /architect - Architecture Design Session

**Use when**: Designing system architecture, creating ADRs.

**Team**: architect

**Output**: TDD, ADRs, architecture diagrams

**Command**:
```
/architect "Design cache provider protocol"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/architect.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/architect-ref/skill.md`

---

### /handoff - Handoff Between Agents

**Use when**: Transitioning work between workflow phases.

**Output**: Handoff document with context, artifacts, next steps

**Command**:
```
/handoff "From design to implementation"
```

**References**:
- Command: `/Users/tomtenuta/Code/autom8_asana/.claude/commands/handoff.md`
- Skill: `/Users/tomtenuta/Code/autom8_asana/.claude/skills/handoff-ref/skill.md`

---

## Decision Matrix

| Scenario | Command | Team | Output |
|----------|---------|------|--------|
| New feature (well-scoped) | `/task` | 10x | PRD, TDD, Code, Tests |
| Sprint planning | `/sprint` | 10x | Sprint plan, task breakdown |
| Production bug | `/hotfix` | 10x | Minimal PRD, Code, Tests |
| Technical investigation | `/spike` | 10x | Spike report, findings |
| Documentation work | `/docs` | docs | Docs, audits, reviews |
| Code cleanup | `/hygiene` | hygiene | Refactored code, improved tests |
| Debt assessment | `/debt` | debt | Debt inventory, priorities |
| Infrastructure work | `/sre` | sre | Runbooks, monitoring, deployment |
| Deep testing | `/qa` | 10x (qa-adversary) | Test plan, validation report |
| Code review | `/code-review` | 10x | Review comments |
| Create PR | `/pr` | 10x | GitHub PR |
| Architecture design | `/architect` | 10x (architect) | TDD, ADRs |

---

## Examples

### "I need to add a new feature"

**Well-defined feature**:
```
/task "Add rate limiting to Asana API client"
```

**Undefined/exploratory feature**:
```
/spike "Investigate rate limiting strategies for Asana API"
```

**Epic with multiple features**:
```
/sprint "Q1 Epic: Cache Performance Optimization"
```

---

### "We have a production issue"

**Critical bug**:
```
/hotfix "Fix cache corruption causing data loss"
```

**Non-urgent bug**:
```
/task "Fix off-by-one error in pagination logic"
```

---

### "Planning next sprint"

```
/sprint "Sprint 6: SaveSession Reliability Improvements"
```

---

### "Documentation is out of date"

```
/docs
# Then describe documentation work to doc-team
```

---

### "Code is messy, needs cleanup"

```
/hygiene
# Then describe cleanup scope
```

---

### "Need to design a complex system"

```
/architect "Design entity detection tier system"
```

---

## Common Mistakes

### Mistake: Using /task for investigations

❌ **Wrong**:
```
/task "Figure out why cache is slow"
```

✓ **Correct**:
```
/spike "Investigate cache performance bottlenecks"
```

**Why**: `/task` assumes you know WHAT to build. Use `/spike` for unknowns.

---

### Mistake: Using /hotfix for non-urgent bugs

❌ **Wrong**:
```
/hotfix "Fix typo in error message"
```

✓ **Correct**:
```
/task "Fix typo in error message"
```

**Why**: `/hotfix` bypasses design phase and should only be used for critical production issues.

---

### Mistake: Using /sprint for single tasks

❌ **Wrong**:
```
/sprint "Implement one function"
```

✓ **Correct**:
```
/task "Implement progressive TTL function"
```

**Why**: `/sprint` is for planning MULTIPLE related tasks. Use `/task` for single-task execution.

---

## See Also

- [REF-workflow-phases.md](./REF-workflow-phases.md) - Workflow phase details
- [COMMAND_REGISTRY.md](../../.claude/COMMAND_REGISTRY.md) - Complete command list
- [10x-workflow/lifecycle.md](../../.claude/skills/10x-workflow/lifecycle.md) - Workflow lifecycle
