# Role Definition Pattern

> How to define clear, non-overlapping agent roles

## Purpose

This pattern guides the Agent Designer in creating role definitions that:
- Have clear boundaries
- Don't overlap with other agents
- Cover all necessary responsibilities
- Enable smooth handoffs

## Pattern Structure

### 1. Role Statement

```markdown
The {Role Name} is responsible for {primary function}.
This agent {action verb} when {trigger condition}.
```

**Example**:
```markdown
The Architect is responsible for system design decisions.
This agent engages when requirements are approved and technical design is needed.
```

### 2. Responsibility Clusters

Group related responsibilities into 4-6 clusters:

```markdown
- **{Cluster Label}**: {What this covers}
```

**Rules**:
- Each cluster should be distinct (no overlap)
- Responsibilities within a cluster should be related
- Use action verbs (defines, creates, validates)

**Example**:
```markdown
- **System Design**: Component architecture, data flow, integration points
- **Technology Selection**: Framework choices, library decisions, infrastructure
- **Risk Assessment**: Technical risks, mitigation strategies, trade-offs
- **Documentation**: TDD creation, ADR authoring, decision rationale
```

### 3. Boundary Markers

Explicitly state what the agent does NOT do:

```markdown
**This agent does NOT:**
- {Thing that belongs to another agent}
- {Thing that requires escalation}
```

**Example**:
```markdown
**This agent does NOT:**
- Write implementation code (Principal Engineer)
- Define business requirements (Requirements Analyst)
- Validate implementation correctness (QA Adversary)
```

### 4. Input/Output Contract

Specify what the agent receives and produces:

```markdown
**Inputs:**
- {Artifact from upstream agent}
- {Context information}

**Outputs:**
- {Primary artifact}
- {Secondary artifacts}
```

## Anti-Patterns

- **Vague Responsibilities**: "Handles technical stuff" - too broad
- **Overlapping Domains**: Two agents both "decide architecture" - conflict
- **Missing Boundaries**: No clear statement of what agent doesn't do
- **Implicit Contracts**: Assuming agents know what to pass without specifying

## Checklist

- [ ] Role statement is one clear sentence
- [ ] 4-6 responsibility clusters defined
- [ ] Each cluster is distinct from others
- [ ] Boundary markers state what agent doesn't do
- [ ] Input artifacts explicitly listed
- [ ] Output artifacts explicitly listed
- [ ] No overlap with other agents in team
