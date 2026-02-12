---
user-invocable: false
---

# Handoff Note Templates

> Transition-specific context for agent handoffs.

## Note Structure

```markdown
## Handoff: {current_agent} → {target_agent}

**Timestamp**: {ISO 8601}
**Handoff reason**: {auto-generated or user-provided}

### Current Phase
{phase}

### Work Completed
Artifacts produced since last handoff:
- ✓ {artifact} - {status}

Decisions made:
- {list recent ADRs or key decisions}

### Current State
Progress: {phase completion status}
Blockers: {count} active

Open questions:
{list questions if any}

### Handoff Context
{user-provided or auto-generated context}

Key points for {target_agent}:
1. {item}
2. {item}

### Next Steps for {target_agent}
1. {action}
2. {action}
```

---

## Transition-Specific Context

### Analyst → Architect

```markdown
PRD approved and ready for technical design. Focus on:
- System architecture and component design
- Technology selection and justification (ADRs)
- Interface definitions and data flow
- Risk identification and mitigation strategies
```

### Architect → Engineer

```markdown
TDD and ADRs complete and approved. Focus on:
- Implementation following TDD specifications
- Code structure matching architectural decisions
- Test coverage for all requirements
- Type safety and error handling
```

### Engineer → QA

```markdown
Implementation complete, code committed. Focus on:
- Validation against PRD acceptance criteria
- Edge case and error condition testing
- Performance and scalability verification
- Production readiness assessment
```

### QA → Engineer (Issues Found)

```markdown
QA validation identified {count} issues. Focus on:
- Addressing defects listed in test plan
- Re-validation after fixes
- Root cause analysis for critical issues
```

### QA → Any (All Pass)

```markdown
QA validation complete, all tests passing. Focus on:
- Final review before /wrap
- Documentation completeness check
- Deployment readiness confirmation
```

---

## Status Icons

| Icon | Meaning |
|------|---------|
| ✓ | Completed |
| ⧗ | In progress |
| ✗ | Blocked |
| ⚠ | Warning/needs attention |
