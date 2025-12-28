# Playbook Authoring Guide

> How to create custom playbooks for the Consultant

## When to Create a Playbook

Create a custom playbook when:
- You have a repeated workflow
- Existing playbooks don't fit your scenario
- Your team has specific patterns
- You want to document a complex process

## Playbook Location

Save playbooks to:
```
.claude/knowledge/consultant/playbooks/curated/{name}.md
```

## Required Structure

Every playbook must have:

```markdown
# Playbook: [Name]

> [One-line description]

## When to Use
- [Trigger condition 1]
- [Trigger condition 2]

## Prerequisites
- [Prerequisite 1]
- [Prerequisite 2]

## Command Sequence

### Phase 1: [Phase Name]
```bash
/[command] [args]
```
**Expected output**: [What user will see]
**Decision point**: [If X, proceed. If Y, adjust.]

### Phase 2: [Phase Name]
[Continue pattern...]

## Variations
- **[Variant name]**: [When and how to adjust]

## Success Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
```

## Optional Sections

Add as needed:

```markdown
## Rollback
If things go wrong: [Recovery steps]

## Quick Path
For simple cases: [Abbreviated workflow]

## Integration
How this works with other workflows: [Details]

## Team Coordination
When multiple teams involved: [Details]
```

## Writing Guidelines

### Be Specific

Bad:
```bash
/start "something"
```

Good:
```bash
/start "Feature name" --complexity=MODULE
```

### Include Decision Points

Every phase should have:
- Expected output
- When to proceed
- When to adjust

### Document Variations

Common variations:
- Quick path for simple cases
- Complex path for edge cases
- Team-specific adjustments

### Keep It Actionable

Focus on what to do, not why.
Save explanations for skill docs.

## Example Playbook

```markdown
# Playbook: API Endpoint Addition

> Add a new REST API endpoint with full lifecycle

## When to Use
- Adding new API endpoint
- Extending existing API
- New integration point

## Prerequisites
- API design decision made
- Authentication requirements known

## Command Sequence

### Phase 1: Initialize

```bash
/10x
/start "Add /users/{id}/preferences endpoint" --complexity=MODULE
```
**Expected output**: Session created, Requirements Analyst invoked
**Decision point**: If endpoint is simple CRUD, consider SCRIPT complexity.

### Phase 2: Design

```bash
/architect
```
**Expected output**: TDD with endpoint specification
**Decision point**: Review API contract before proceeding.

### Phase 3: Implement

```bash
/build
```
**Expected output**: Endpoint code, tests, documentation

### Phase 4: Validate

```bash
/qa
```
**Expected output**: Test report, API contract validation

### Phase 5: Ship

```bash
/wrap
/pr
```

## Variations
- **Simple endpoint**: Skip /architect, use SCRIPT complexity
- **External API**: Add /security review phase
- **Breaking change**: Add migration planning

## Success Criteria
- [ ] Endpoint responds correctly
- [ ] Tests cover happy path and errors
- [ ] Documentation updated
- [ ] PR created
```

## Testing Your Playbook

1. Run through the workflow manually
2. Verify each command works
3. Check decision points are clear
4. Ensure success criteria are measurable

## Naming Convention

Use lowercase, hyphen-separated names:
- `new-feature.md`
- `api-endpoint.md`
- `database-migration.md`

## Submitting for Curation

To add to curated collection:
1. Create the playbook
2. Test it thoroughly
3. Place in `playbooks/curated/`
4. Update references if needed
