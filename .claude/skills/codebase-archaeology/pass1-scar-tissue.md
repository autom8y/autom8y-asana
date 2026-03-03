# Pass 1: Scar Tissue Catalog

> Extract past bugs, regressions, and defensive patterns born from production failures. Scar tissue is the highest-value prompt content because it encodes failure modes an AI cannot derive from reading current code alone.

## Purpose

Scar tissue tells agents what HAS gone wrong. A model reading `sorted(keys())` sees a sorted call; only the scar explains that without it, the same query produces different results across runs. The git history and regression tests contain this knowledge -- current code only shows the fix, not the failure.

## Sources

| Source | What to Extract |
|--------|----------------|
| Git commit messages | Fixes, regressions, reverts, hotfixes |
| Code comments | CRITICAL, HACK, FIXME, BUG-, SCAR-, DEF- markers |
| Regression test names | Tests named after specific bugs or failure modes |
| Revert commits | The original change AND the fix after revert |

## Search Queries

Parameterized for the target codebase root `$ROOT`:

```bash
# Git log: fix/bug/regression commits
git log --oneline --all --grep='fix' --grep='bug' --grep='regression' --grep='revert' --grep='hotfix' --since='2 years ago'

# Code comments with scar markers
Grep pattern: "CRITICAL|HACK|FIXME|BUG-|SCAR-|DEF-|WORKAROUND|XXX"

# Regression test names
Grep pattern: "test.*regression|test.*prevention|test.*guard|test.*fix"
Glob pattern: "**/test_*regression*" or "**/test_*prevention*"
```

### Project-Type Variants

| Language | Additional Comment Markers | Test Patterns |
|----------|---------------------------|---------------|
| Python | `# type: ignore`, `noqa:`, `pragma: no cover` | `test_*_regression`, `@pytest.mark.parametrize` with bug IDs |
| Go | `//nolint:`, `// BUG(`, `// TODO(ticket-` | `Test*Regression`, `Test*Fix`, `Test*Guard` |
| TypeScript | `// @ts-expect-error`, `eslint-disable`, `istanbul ignore` | `it.skip`, `describe('regression:` |
| Infrastructure | `lifecycle { prevent_destroy }`, `# DANGER:` | Plan validation tests, rollback scripts |

## Categorization

Classify each scar into one of these categories (extend as needed):

- **Data corruption**: Silent wrong results, inflation, incorrect aggregation
- **Race condition**: Non-determinism, ordering bugs, concurrency issues
- **Integration failure**: Cross-component contract violations, API mismatches
- **Configuration drift**: Environment-specific failures, missing config
- **Security**: Injection, bypass, privilege escalation
- **Performance cliff**: Sudden degradation under specific conditions
- **Schema evolution**: Breaking changes, migration failures, type mismatches

## Output Schema

Write each scar using the [scar-entry.md](schemas/scar-entry.md) schema. Number sequentially: `[SCAR-001]`, `[SCAR-002]`, etc.

## Quality Indicators

- **Minimum yield**: 10+ scars for a mature codebase (500+ commits). Fewer than 5 suggests insufficient git history or missed sources.
- **Category coverage**: At least 3 distinct categories represented.
- **Agent relevance**: Every scar must map to at least one agent role.

## Example Entry

```markdown
### [SCAR-002] Non-Deterministic Query Merge (Variable Row Counts)
- **Category**: Race condition
- **What Went Wrong**: Running the same analysis 10 times produced different row counts
  due to non-deterministic dict/set iteration during query plan generation and merge.
- **Root Cause**: Python dict and set iteration order is non-deterministic across runs.
  Three code sites iterated over unsorted collections in the query planning path.
- **Fix Location**: `src/core/query/resolver.py:308`, `resolver.py:359`,
  `src/core/optimizer.py:158`, `optimizer.py:576`
- **Defensive Pattern Added**: Every dict/set iteration in query planning now uses
  `sorted()`. Comments marked `# CRITICAL: Sort for deterministic iteration`.
  Integration test runs the query 10x and asserts identical row counts.
- **Agent Relevance**: **query-specialist** (any new dict/set iteration in query paths
  MUST be sorted), **qa-agent** (determinism tests must run multi-iteration)
```

## After This Pass

Proceed to Pass 2 (Defensive Patterns) or run Passes 2-3 in parallel. The scar catalog informs Pass 4 (Golden Paths) by identifying what "correct" means in the context of past failures.
