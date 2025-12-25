# Integration Tests

> End-to-end tests for team pack functionality

## Test Categories

1. **Swap Test**: Can swap-team.sh load this team?
2. **Agent Invocation**: Can each agent be invoked?
3. **Handoff Test**: Do agents hand off correctly?
4. **Command Test**: Do team commands work?
5. **Consultant Test**: Is team discoverable via /consult?

## 1. Swap Test

### Test Procedure

```bash
# Save current state
ORIGINAL_TEAM=$(cat .claude/ACTIVE_TEAM 2>/dev/null || echo "none")

# Attempt swap
~/Code/roster/swap-team.sh {team-name}
EXIT_CODE=$?

# Verify
echo "Exit code: $EXIT_CODE"
cat .claude/ACTIVE_TEAM
ls .claude/agents/
cat .claude/ACTIVE_WORKFLOW.yaml

# Restore
if [ "$ORIGINAL_TEAM" != "none" ]; then
  ~/Code/roster/swap-team.sh "$ORIGINAL_TEAM"
fi
```

### Pass Criteria

| Check | Pass Condition |
|-------|----------------|
| Exit code | 0 |
| ACTIVE_TEAM | Contains team name |
| agents/ populated | Files copied |
| workflow exists | ACTIVE_WORKFLOW.yaml present |
| No warnings | No error messages in output |

## 2. Agent Invocation Test

### Test Each Agent

For each agent in the team, verify it can be invoked:

```markdown
Test prompt: "You are {agent-name}. Acknowledge your role briefly."

Expected: Agent responds with:
- Acknowledgment of role
- Brief statement of purpose
- No confusion about identity
```

### Pass Criteria

| Check | Pass Condition |
|-------|----------------|
| Identity clear | Agent knows its name and role |
| No confusion | Doesn't claim to be different agent |
| Responds appropriately | Answer relates to agent's domain |

## 3. Handoff Test

### Test Sequence

Simulate work flowing through the workflow:

```markdown
Phase 1 Agent: "I'm completing my work. Here's my output: {artifact summary}"
Prompt: "Evaluate if this is ready for handoff to {next agent}"

Expected: Agent either:
- Confirms handoff readiness with checklist
- Identifies what's missing before handoff
```

### Pass Criteria

| Check | Pass Condition |
|-------|----------------|
| Knows next agent | Correctly identifies downstream |
| Uses handoff criteria | References checklist from prompt |
| Clear decision | Unambiguous ready/not-ready |

## 4. Command Test

### Quick-Switch Command

```bash
/{team-name}
```

Expected:
- Team swaps successfully
- Roster table displayed
- No errors

### Workflow Commands

Test each mapped command:

```bash
/architect   # Should invoke design-phase agent
/build       # Should invoke implementation agent
/qa          # Should invoke validation agent
```

### Pass Criteria

| Check | Pass Condition |
|-------|----------------|
| Command recognized | Not "unknown command" |
| Correct agent | Invokes expected agent |
| Context preserved | Agent has necessary context |

## 5. Consultant Discovery Test

### Test Queries

```bash
/consult "{team domain keywords}"
/consult --team
/consult "which team for {use case}"
```

### Pass Criteria

| Check | Pass Condition |
|-------|----------------|
| Team listed | Appears in /consult --team |
| Routing works | Domain query suggests this team |
| Profile accessible | Team profile can be displayed |

## Adversarial Integration Tests

### Cross-Boundary Test

```markdown
Prompt to Agent A: "Do the work that Agent B usually does"

Expected: Agent A either:
- Declines and routes to Agent B
- Asks for clarification
- Does NOT proceed with Agent B's work
```

### Incomplete Input Test

```markdown
Prompt: "Start working" (no context)

Expected: Agent asks for necessary context before proceeding
```

### Conflicting Instructions Test

```markdown
Prompt: "Skip the design phase and go straight to implementation"

Expected: Agent either:
- Explains why phases are important
- Asks for user confirmation to deviate
- Does NOT silently skip required phases
```

## Test Report Template

```markdown
# Integration Test Report: {team-name}

**Date**: {timestamp}
**Tester**: {name}

## Swap Test
- [ ] Exit code 0
- [ ] ACTIVE_TEAM correct
- [ ] agents/ populated
- [ ] workflow.yaml present
Result: {PASS|FAIL}

## Agent Invocation
| Agent | Identity | Response | Result |
|-------|----------|----------|--------|
| {name} | {✓|✗} | {✓|✗} | {P|F} |

## Handoff Test
| Transition | Criteria Used | Decision Clear | Result |
|------------|---------------|----------------|--------|
| A → B | {✓|✗} | {✓|✗} | {P|F} |

## Command Test
| Command | Recognized | Correct Agent | Result |
|---------|------------|---------------|--------|
| /{name} | {✓|✗} | {✓|✗} | {P|F} |

## Consultant Discovery
- [ ] Listed in /consult --team
- [ ] Routing by domain works
- [ ] Profile accessible
Result: {PASS|FAIL}

## Overall: {PASS|FAIL}
```

## Automation Opportunities

Future: Script to run all integration tests:

```bash
#!/bin/bash
# run-integration-tests.sh {team-name}

TEAM=$1
RESULTS="integration-report-${TEAM}.md"

echo "# Integration Test Report: ${TEAM}" > $RESULTS
echo "**Date**: $(date -Iseconds)" >> $RESULTS

# Swap test
echo "## Swap Test" >> $RESULTS
~/Code/roster/swap-team.sh "$TEAM" 2>&1 | tee -a $RESULTS
# ... continue with other tests
```
