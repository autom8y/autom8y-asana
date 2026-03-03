# Schema: Scar Entry [SCAR-NNN]

## Template

```markdown
### [SCAR-NNN] Title (short description of failure)
- **Category**: {data_corruption | race_condition | integration_failure |
  configuration_drift | security | performance_cliff | schema_evolution}
- **What Went Wrong**: {1-2 sentence narrative of the user-visible failure}
- **Root Cause**: {technical root cause explaining WHY it happened}
- **Fix Location**: {file:line references to the fix, comma-separated}
- **Defensive Pattern Added**: {what guard/check/test was put in place,
  with comment markers if applicable}
- **Agent Relevance**: {agent-name} (what this agent must know),
  {agent-name} (what this agent must know)
```

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| NNN | Yes | Sequential number (001, 002, ...). Do not skip or reuse. |
| Title | Yes | Short phrase describing the failure mode. Include the impact if measurable (e.g., "17k -> 3.5M rows"). |
| Category | Yes | One of the defined categories. Extend the list if none fit, but prefer existing categories. |
| What Went Wrong | Yes | User-visible symptom. What would someone observe? Focus on the EFFECT, not the cause. |
| Root Cause | Yes | Technical explanation of WHY. This is what the code alone cannot tell you. |
| Fix Location | Yes | Absolute file:line references. Multiple locations comma-separated. |
| Defensive Pattern Added | Yes | What was put in place to prevent recurrence. Include test names and comment markers. |
| Agent Relevance | Yes | Map to at least one agent role. Explain WHAT each agent needs to know, not just that they need to know it. |

## Example

```markdown
### [SCAR-002] Non-Deterministic Query Merge (Variable Row Counts)
- **Category**: race_condition
- **What Went Wrong**: Running the same analysis 10 times produced different
  row counts (900, 1389, 1488) due to non-deterministic iteration during
  query plan generation.
- **Root Cause**: Python dict and set iteration order is non-deterministic
  across runs. Three sites iterated unsorted collections in the query path.
- **Fix Location**: `src/core/query/resolver.py:308`, `resolver.py:359`,
  `src/core/optimizer.py:158`, `optimizer.py:576`
- **Defensive Pattern Added**: Every dict/set iteration in query planning
  now uses `sorted()`. Comments: `# CRITICAL: Sort for deterministic iteration`.
  Test: `test_determinism` runs query 10x asserting identical row counts.
- **Agent Relevance**: **query-specialist** (any new dict/set iteration
  MUST be sorted), **qa-agent** (determinism tests must be multi-iteration)
```

## Notes

- Scars from "intentional" design decisions (e.g., deliberate fan-out for attribution) should still be cataloged but noted as intentional. They prevent agents from "fixing" correct behavior.
- When multiple scars share a root cause, catalog them separately but cross-reference. Each scar represents a distinct user-visible failure.
