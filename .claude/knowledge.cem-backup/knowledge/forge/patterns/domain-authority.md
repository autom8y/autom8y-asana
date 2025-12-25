# Domain Authority Pattern

> Defining what agents decide, escalate, and route

## Purpose

This pattern ensures every agent knows:
- What decisions are within their authority
- When to escalate to humans
- When to route to other agents

## The Three-Part Structure

Every agent's Domain Authority section should have exactly three parts:

### 1. "You decide:"

List 3-5 decisions the agent makes autonomously:

```markdown
**You decide:**
- {Decision type 1 within expertise}
- {Decision type 2 within expertise}
- {Decision type 3 within expertise}
```

**Criteria for inclusion**:
- Agent has the expertise to make this decision
- Decision doesn't require human judgment on values/priorities
- Decision scope is within the agent's phase

**Example (Architect)**:
```markdown
**You decide:**
- Component boundaries and interfaces
- Technology stack selections with clear trade-offs
- Data model structure and relationships
- API contract specifications
- Integration patterns between components
```

### 2. "You escalate to User/Senior Role:"

List 2-3 conditions requiring human input:

```markdown
**You escalate to {Role}:**
- {Condition requiring escalation 1}
- {Condition requiring escalation 2}
```

**Criteria for inclusion**:
- Decisions involving business priorities
- Trade-offs between competing values
- Irreversible decisions with significant impact
- Ambiguous requirements needing clarification

**Example (Architect)**:
```markdown
**You escalate to User:**
- Trade-offs between speed, cost, and quality
- Decisions that constrain future options significantly
- Ambiguous requirements that affect architecture
- Security vs. usability trade-offs
```

### 3. "You route to {Next Agent}:"

List 2-3 conditions triggering handoff:

```markdown
**You route to {Next Agent}:**
- {Handoff condition 1}
- {Handoff condition 2}
```

**Criteria for inclusion**:
- Work that belongs to the next phase
- Issues discovered that require different expertise
- Completion of this agent's deliverables

**Example (Architect)**:
```markdown
**You route to Principal Engineer:**
- When TDD and ADRs are complete and approved
- When all technical decisions are documented
- When implementation scope is clear
```

## Complete Example

```markdown
## Domain Authority

**You decide:**
- System component architecture
- Database schema design
- API contract specifications
- Integration patterns
- Technology selections within approved stack

**You escalate to User:**
- Trade-offs affecting timeline or budget
- Decisions constraining future product direction
- Ambiguous requirements needing business input

**You route to Principal Engineer:**
- When TDD is complete with all sections
- When ADRs document key decisions
- When no blocking technical questions remain
```

## Anti-Patterns

- **Decision Vacuum**: "You decide everything" - no boundaries
- **Escalation Overload**: Escalating trivial decisions - slows progress
- **Route Confusion**: Unclear when to hand off - work stalls
- **Authority Creep**: Deciding things outside expertise - quality suffers

## Checklist

- [ ] 3-5 autonomous decision areas listed
- [ ] Decisions are within agent's expertise
- [ ] 2-3 escalation conditions specified
- [ ] Escalations involve human judgment needs
- [ ] 2-3 routing conditions specified
- [ ] Routing conditions are specific and testable
- [ ] No overlap with other agents' decision areas
