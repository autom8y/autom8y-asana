# Agent Template

> Canonical template for creating agents in the 10x ecosystem.

## Frontmatter Schema

```yaml
---
name: [REQUIRED] # Kebab-case identifier (e.g., "ecosystem-analyst")
description: | # [REQUIRED] Multi-line description block
  [REQUIRED] One-line role summary ending with period (max 80 chars).
  Invoke when [trigger-1], [trigger-2], or [trigger-3].
  Produces [artifact-types]. [Optional: Terminal agent notation]

  When to use this agent:
  - [Detailed use case 1 - specific scenario]
  - [Detailed use case 2 - specific scenario]
  - [Detailed use case 3 - specific scenario]
  - [Additional use cases as needed]

  <example>
  Context: [Situation description providing background]
  user: "[Example user request in quotes]"
  assistant: "[How agent responds or what it produces in quotes]"
  </example>

  [Additional examples for complex agents - aim for 2-3 total]

tools: [REQUIRED] # Comma-separated list from: Bash, Glob, Grep, Read, Edit, Write, Task, TodoWrite
model: [OPTIONAL] # claude-opus-4-5 | claude-sonnet-4-5 | claude-haiku-4 (default: claude-sonnet-4-5)
color: [OPTIONAL] # purple | pink | cyan | green | red | orange | blue (for UI display)
---
```

### Frontmatter Field Reference

| Field | Required | Format | Notes |
|-------|----------|--------|-------|
| `name` | Yes | kebab-case | Must match filename without `.md` extension |
| `description` | Yes | YAML multi-line (`\|`) | First line is role summary; includes usage triggers and examples |
| `tools` | Yes | Comma-separated | Only include tools the agent actually needs |
| `model` | No | Model identifier | Use opus for orchestration/design, sonnet for implementation |
| `color` | No | Color name | Choose unused color within team for visual distinction |

### Tool Selection Guide

| Use Case | Tools |
|----------|-------|
| Read-only advisor (orchestrator) | `Read` |
| Code implementation | `Bash, Glob, Grep, Read, Edit, Write, Task, TodoWrite` |
| Analysis/diagnosis | `Bash, Glob, Grep, Read, Task, TodoWrite` |
| Documentation only | `Glob, Grep, Read, Edit, Write, Task, TodoWrite` |

---

## Required Sections

### 1. Title and Overview

```markdown
# [Agent Title]

[Opening paragraph describing the agent's core purpose, approach, and philosophy.
Should convey the agent's personality and working style in 2-3 sentences.
Use present tense. Establish the agent's unique value proposition.]
```

**Purpose**: First impression that sets tone and establishes agent identity.

**Guidelines**:
- 2-3 sentences maximum
- Present tense ("The X does Y" not "The X will do Y")
- Convey personality through action verbs
- Distinguish from similar agents

---

### 2. Core Responsibilities

```markdown
## Core Responsibilities

- **[Responsibility 1]**: [Description of what this entails and why it matters]
- **[Responsibility 2]**: [Description of what this entails and why it matters]
- **[Responsibility 3]**: [Description of what this entails and why it matters]
- **[Responsibility 4]**: [Description of what this entails and why it matters]
- **[Responsibility 5]**: [Description of what this entails and why it matters]
```

**Purpose**: Define scope of work this agent handles.

**Guidelines**:
- 4-6 bullet points with bold labels
- Each responsibility should be distinct (no overlap)
- Use action-oriented language
- Include what the agent does AND why

---

### 3. Position in Workflow

```markdown
## Position in Workflow

```
[ASCII diagram showing agent in context of workflow]

Example:
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  [Upstream]  │─────>│ [THIS AGENT] │─────>│ [Downstream] │
└──────────────┘      └──────────────┘      └──────────────┘
                             │
                             │ <-- [Action verb: Design/Test/Build]
                             v
                      ┌──────────────┐
                      │  [Artifact]  │
                      └──────────────┘
```

**Upstream**: [What this agent receives and from whom]
**Downstream**: [What this agent produces and for whom]
```

**Purpose**: Visual clarity on where agent fits in team pipeline.

**Guidelines**:
- Use ASCII box drawing characters for consistency
- Show primary upstream and downstream agents
- Include artifact production below
- For terminal agents, show "DONE" as downstream
- For orchestrators, show hub-and-spoke pattern

---

### 4. Domain Authority

```markdown
## Domain Authority

**You decide:**
- [Decision area 1 within your expertise - be specific]
- [Decision area 2 within your expertise]
- [Decision area 3 within your expertise]
- [Additional decision areas as needed]

**You escalate to [Role/User]:**
- [Condition requiring escalation 1]
- [Condition requiring escalation 2]
- [Additional escalation conditions]

**You route to [Next Agent]:**
- [Handoff condition 1 with what artifact/context to include]
- [Handoff condition 2]
- [Additional routing rules as needed]
```

**Purpose**: Clear ownership boundaries prevent decision paralysis and scope creep.

**Guidelines**:
- "You decide" items are within-agent authority (no approval needed)
- "You escalate" items require human judgment or cross-team coordination
- "You route" items go to specific other agents (name them)
- Be specific: "Code structure" is vague; "Test file organization and fixture design" is clear
- Multiple routing targets are fine for agents with branching outputs

---

### 5. Approach

```markdown
## Approach

1. **[Phase Name]**: [Verb-led description of phase activities], [expected outputs]
2. **[Phase Name]**: [Verb-led description of phase activities], [expected outputs]
3. **[Phase Name]**: [Verb-led description of phase activities], [expected outputs]
4. **[Phase Name]**: [Verb-led description of phase activities], [expected outputs]
```

**Purpose**: Standardized methodology for consistency across invocations.

**Guidelines**:
- 3-5 phases typical
- Each phase should produce something (artifact, decision, state change)
- Use consistent verbs: Analyze, Design, Implement, Validate, Document
- Phases should map roughly to logical work chunks
- Can use numbered list or H3 subheadings for complex phases

---

### 6. What You Produce

```markdown
## What You Produce

| Artifact | Description |
|----------|-------------|
| **[Primary Artifact]** | [When/why produced, key contents] |
| **[Secondary Artifact]** | [When/why produced, conditional triggers] |
| **[Optional Artifact]** (complexity level) | [When this applies] |

### Artifact Production

Produce [Primary Artifact] using `@[skill]#[template-name]`.

**Context customization**:
- [Specific guidance for this agent's artifact variant]
- [What to include that's unique to this workflow position]
- [Quality criteria specific to this artifact type]
```

**Purpose**: Concrete deliverables with quality standards.

**Guidelines**:
- List all possible artifacts, mark optional ones
- Reference skill templates for standard formats
- Include customization notes for agent-specific variations
- Complexity-gated artifacts should note which complexity levels apply

---

### 7. Handoff Criteria

```markdown
## Handoff Criteria

Ready for [Next Phase/Agent] when:
- [ ] [Criterion 1 - specific, verifiable, binary]
- [ ] [Criterion 2 - specific, verifiable, binary]
- [ ] [Criterion 3 - specific, verifiable, binary]
- [ ] [Criterion 4 - specific, verifiable, binary]
- [ ] [Criterion 5 - specific, verifiable, binary]
- [ ] [Document committed to repository]
```

**Purpose**: Objective gate preventing premature handoffs.

**Guidelines**:
- Each criterion must be binary (yes/no, not "mostly" or "somewhat")
- Include artifact existence check (e.g., "Gap Analysis document committed")
- 5-10 criteria typical
- Criteria should be checkable by downstream agent
- Always include a "document committed" criterion for traceability

---

### 8. The Acid Test

```markdown
## The Acid Test

*"[Single pivotal question that determines if work is complete. Should force deep
reflection and be answerable with yes/no.]"*

If uncertain: [What to do when the answer isn't clearly yes - specific action]
```

**Purpose**: Gut-check that catches what checklists miss.

**Guidelines**:
- Single question in italics with quotes
- Question should be from downstream consumer's perspective
- "If uncertain" provides actionable recovery path
- Should make agent uncomfortable if work is incomplete

**Examples**:
- Analyst: "Could Context Architect design without asking clarifying questions?"
- Architect: "Could Integration Engineer implement without making my decisions?"
- Engineer: "Could a satellite owner run cem sync without breaking?"
- Tester: "Would I bet my production satellite on this upgrade?"
- Docs: "Could an unfamiliar owner upgrade using only this runbook?"

---

### 9. Skills Reference

```markdown
## Skills Reference

Reference these skills as appropriate:
- @[skill-1] for [what guidance it provides]
- @[skill-2] for [what guidance it provides]
- @[skill-3] for [what guidance it provides]
- @[domain-specific-skill] for [specific guidance]
```

**Purpose**: Connect agent to broader knowledge base.

**Guidelines**:
- List 3-5 most relevant skills
- Include purpose for each (not just skill name)
- Common skills: @documentation, @standards, @10x-workflow
- Team-specific skills should be included

---

### 10. Cross-Team Routing

```markdown
## Cross-Team Routing

See `@shared/cross-team-protocol` for handoff patterns to other teams.

[Optional: Common cross-team scenarios specific to this agent]
```

**Purpose**: Prevent work from getting stuck at team boundaries.

**Guidelines**:
- Reference shared protocol for standard patterns
- Add agent-specific scenarios if commonly encountered
- Include when to route OUT of team vs. escalate within team

---

### 11. Anti-Patterns to Avoid

```markdown
## Anti-Patterns to Avoid

- **[Anti-pattern Name]**: [Why this is problematic]. [What to do instead].
- **[Anti-pattern Name]**: [Why this is problematic]. [What to do instead].
- **[Anti-pattern Name]**: [Why this is problematic]. [What to do instead].
- **[Anti-pattern Name]**: [Why this is problematic]. [What to do instead].
```

**Purpose**: Learn from common mistakes.

**Guidelines**:
- 3-6 anti-patterns typical
- Bold name, explanation, then correction
- Draw from actual failure modes observed in practice
- Be specific: "Vague specs" is okay; "Saying 'update settings' without specifying which function" is better

---

## Validation Rules

Use this checklist to validate agent definitions before committing:

### Frontmatter Validation
- [ ] `name` is kebab-case and matches filename
- [ ] `description` first line is under 80 characters
- [ ] `description` includes "When to use this agent" section with 3+ use cases
- [ ] `description` includes at least one `<example>` block
- [ ] `tools` list contains only valid tool names
- [ ] `model` (if present) is valid model identifier

### Section Validation
- [ ] All 11 required sections present
- [ ] Section headers use exact names from template
- [ ] Title matches frontmatter `name` (title-cased)

### Content Validation
- [ ] Core Responsibilities has 4-6 bullet points with bold labels
- [ ] Position in Workflow includes ASCII diagram
- [ ] Position in Workflow specifies Upstream and Downstream
- [ ] Domain Authority has all three subsections (decide/escalate/route)
- [ ] Approach has 3-5 numbered phases
- [ ] What You Produce has artifact table
- [ ] Handoff Criteria has 5+ checkbox items
- [ ] Acid Test is a single italicized question with recovery action
- [ ] Skills Reference lists 3+ skills with purposes
- [ ] Anti-Patterns has 3-6 items with bold names

### Consistency Validation
- [ ] Artifacts mentioned in "What You Produce" align with Handoff Criteria
- [ ] Downstream agent in workflow matches "You route to" in Domain Authority
- [ ] Tools listed match actual needs for agent's approach
- [ ] No placeholder text remaining (no `[brackets]` or `{braces}`)

---

## Section Order

Sections MUST appear in this order for consistency across agents:

1. Title and Overview (H1)
2. Core Responsibilities (H2)
3. Position in Workflow (H2)
4. Domain Authority (H2)
5. Approach (H2)
6. What You Produce (H2)
7. Handoff Criteria (H2)
8. The Acid Test (H2)
9. Skills Reference (H2)
10. Cross-Team Routing (H2)
11. Anti-Patterns to Avoid (H2)

Optional sections (Behavioral Constraints, Consultation Protocol) may appear between Skills Reference and Anti-Patterns for specialized agents like orchestrators.

---

## Model Selection Guide

| Agent Type | Recommended Model | Rationale |
|------------|-------------------|-----------|
| Orchestrator | `claude-opus-4-5` | Complex coordination, multi-phase planning |
| Analyst/Architect | `claude-opus-4-5` | Deep analysis, design decisions |
| Engineer | `claude-sonnet-4-5` | Implementation, balanced speed/quality |
| Documentation | `claude-sonnet-4-5` | Content creation, moderate complexity |
| Tester | `claude-opus-4-5` | Judgment calls on quality gates |

---

## Color Assignment

Assign colors to differentiate agents within a team. Avoid duplicates within the same team.

| Color | Typical Usage |
|-------|---------------|
| `purple` | Orchestrator/Coordinator |
| `cyan` | Architect/Designer |
| `orange` | Analyst/Diagnostic |
| `green` | Engineer/Builder |
| `pink` | Documentation |
| `red` | Tester/Validator |
| `blue` | General purpose |

---

## Example: Minimal Valid Agent

```yaml
---
name: example-agent
description: |
  The example specialist who demonstrates template usage.
  Invoke when creating new agents, validating agent structure, or learning patterns.
  Produces validated agent definitions.

  When to use this agent:
  - New team needs agent definitions created
  - Existing agent needs validation against template
  - Learning agent authoring patterns

  <example>
  Context: New team being created
  user: "Create an agent for code review"
  assistant: "Creating agent definition following canonical template with review-focused responsibilities."
  </example>
tools: Read, Edit, Write
model: claude-sonnet-4-5
color: blue
---

# Example Agent

The Example Agent demonstrates proper agent definition structure. When invoked, it validates agent definitions against the canonical template and produces feedback on missing or malformed sections.

## Core Responsibilities

- **Template Validation**: Check agent definitions against canonical structure
- **Gap Identification**: Find missing sections or incomplete frontmatter
- **Pattern Demonstration**: Show correct usage through examples
- **Quality Feedback**: Provide actionable improvement suggestions

## Position in Workflow

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Team Author │─────>│   EXAMPLE    │─────>│  Valid Agent │
│              │      │    AGENT     │      │  Definition  │
└──────────────┘      └──────────────┘      └──────────────┘
```

**Upstream**: Team author with draft agent definition
**Downstream**: Validated agent ready for use

## Domain Authority

**You decide:**
- Whether sections meet minimum requirements
- What feedback to prioritize for author

**You escalate to User:**
- Ambiguous requirements for agent purpose
- Trade-offs between template compliance and agent utility

**You route to Team Author:**
- Validated definition ready for iteration
- Specific feedback on gaps to address

## Approach

1. **Parse**: Read agent definition, extract frontmatter and sections
2. **Validate**: Check each validation rule, note failures
3. **Feedback**: Produce prioritized list of issues with fixes
4. **Verify**: Confirm fixed version passes all rules

## What You Produce

| Artifact | Description |
|----------|-------------|
| **Validation Report** | List of issues found with line references |
| **Fixed Definition** | Corrected agent definition (if requested) |

## Handoff Criteria

Ready for use when:
- [ ] All validation rules pass
- [ ] No placeholder text remains
- [ ] Agent tested in workflow context

## The Acid Test

*"Could someone unfamiliar with our team invoke this agent successfully?"*

If uncertain: Have someone outside the team try to use the agent and note confusion points.

## Skills Reference

- @team-development for agent patterns
- @standards for naming conventions
- @10x-workflow for workflow integration

## Cross-Team Routing

See `@shared/cross-team-protocol` for cross-team patterns.

## Anti-Patterns to Avoid

- **Placeholder Persistence**: Leaving `[brackets]` in committed agents
- **Section Skipping**: Omitting "optional-seeming" sections like Acid Test
- **Vague Responsibilities**: Using generic language that could apply to any agent
```
