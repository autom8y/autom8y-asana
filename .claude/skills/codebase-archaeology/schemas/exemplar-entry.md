# Schema: Exemplar Entry [GOLD-NNN]

## Template

```markdown
## [GOLD-NNN] Best {Type}: `{name}`
- **Location**: {file:line range}
- **Why It's Gold**: {narrative explaining completeness, 3-6 bullet points
  of specific qualities that make this exemplary}
- **Pattern Rule**: {extracted generalized rule, 1-2 sentences}
- **Code Snippet**: {the actual code, 15-25 lines}
- **Anti-Exemplar**: {name and location of worst example of same type}
- **Anti-Exemplar Location**: {file:line range}
```

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| NNN | Yes | Sequential number (001, 002, ...). |
| Type | Yes | The concept type: Model Definition, Composite, Test, Handler, Config, etc. |
| name | Yes | The specific instance name (e.g., `n_distinct`, `TestDivisionByZero`). |
| Location | Yes | File:line range of the gold exemplar. |
| Why It's Gold | Yes | Bulleted list of specific qualities. Reference field names, constraint types, and documentation patterns. Do not use vague praise. |
| Pattern Rule | Yes | A generalized rule extracted from the contrast. Must be actionable for the agent. |
| Code Snippet | Yes | The actual code (15-25 lines). This is the "show, don't tell" component. |
| Anti-Exemplar | Yes | Name of the worst instance of the same type, with specific deficiencies listed. |
| Anti-Exemplar Location | Yes | File:line range. |

## Extracted Rules Format

After all exemplars, extract rules using this convention:

```markdown
**R-{AGENT}-{NNN}** Rule text. Reference specific field names, constraints,
or patterns that the agent must follow.
```

Where `{AGENT}` is a 2-3 letter abbreviation of the agent role (e.g., MA for metric-architect, QS for query-strategist).

## Example

```markdown
## [GOLD-004] Best Test: `TestDivisionByZeroGuardRegression`
- **Location**: `tests/test_composite.py:642-809`
- **Why It's Gold**:
  - Explicit purpose in docstring tracing back to audit finding
  - `@pytest.mark.parametrize` covers every formula family
  - Tests BOTH row-wise and vectorized execution paths
  - Sanity tests confirm valid inputs return non-None
  - `ids=["cpc", "cpl", "cps"]` for readable test names
  - Assertion messages include the metric name for debugging
- **Pattern Rule**: For every formula class, write a parametrized regression
  test covering: zero denominator returns None, valid inputs return a value,
  both execution paths work, test names are readable.
- **Code Snippet**:
  [15-25 lines of the actual parametrized test]
- **Anti-Exemplar**: `test_analytics.py:1-8` -- single assertion
  `assert Builder is not None`. No docstring, no failure message,
  no business intent, zero edge cases.
- **Anti-Exemplar Location**: `tests/test_analytics.py:1-8`
```

## Notes

- Include code snippets for gold exemplars. This is the highest-value content for agent prompt engineering -- concrete examples beat abstract rules.
- Anti-exemplars should be specific, not strawmen. Cite real code in the codebase.
- The Pattern Rule is what becomes an `R-XX-NNN` rule in the agent prompt. Write it as a direct instruction.
