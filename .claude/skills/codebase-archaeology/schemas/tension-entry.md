# Schema: Tension Entry [TENSION-NNN]

## Template

```markdown
### [TENSION-NNN] Title
- **Type**: {naming_mismatch | layering_violation | under_engineering |
  over_engineering | missing_abstraction | premature_abstraction}
- **Location**: {file(s):line(s)}
- **The Tension**: {narrative explaining the structural conflict, 2-4 sentences}
- **Historical Reason**: {why it is the way it is -- what decision or evolution led here}
- **Ideal Resolution**: {what the "correct" fix would be, technically}
- **Resolution Cost**: {Low | Medium | High}
- **Agent Navigation Guide**: {how agents should work WITH this tension, not against it}
```

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| NNN | Yes | Sequential number (001, 002, ...). |
| Title | Yes | Short phrase capturing the conflict. Prefer noun phrases: "Identity Crisis", "Dual Systems", "Megafunction". |
| Type | Yes | One or two of the defined types. Use "/" for tensions spanning two types. |
| Location | Yes | All files involved. Tensions often span multiple files or modules. |
| The Tension | Yes | The core narrative. Explain what the conflict IS, not just where it is. Include why a naive agent would make the wrong decision. |
| Historical Reason | Yes | Why the tension exists. Reference ADRs, commits, or business decisions if known. |
| Ideal Resolution | Yes | The technically correct fix. This helps agents understand the direction of travel. |
| Resolution Cost | Yes | Low (< 1 day), Medium (1-3 days), High (1+ weeks or cross-cutting). |
| Agent Navigation Guide | Yes | Concrete instructions for how agents should work within the constraint. This is the most actionable field for prompt content. |

## Example

```markdown
### [TENSION-002] SQL Generation: String Surgery vs. Structured AST
- **Type**: under_engineering
- **Location**: `src/core/query/sql_generator.py` (entire file, ~1200 lines)
- **The Tension**: The SQL generator builds queries via string concatenation and
  regex-based table reference substitution. The regex `(?<!prefix_)(?<![a-zA-Z_])table\.`
  is a heuristic that breaks with new table names that are substrings of others.
  Six different subquery-building methods all produce raw SQL strings, making
  composition error-prone.
- **Historical Reason**: The design explicitly states "KISS: Simple string
  concatenation, no complex SQL AST." Correct for initial scope but exceeded
  by actual complexity of temporal joins and pre-aggregation subqueries.
- **Ideal Resolution**: Lightweight query IR (intermediate representation) for
  FROM/JOIN/WHERE/GROUP BY that handles aliasing correctly. Keep string-based
  column methods but wrap them in composable query structure.
- **Resolution Cost**: High -- load-bearing infrastructure, every query flows
  through this class.
- **Agent Navigation Guide**: Table reference substitution is order-dependent
  (alphabetical) and uses negative lookbehinds. New table names must not be
  substrings of existing names. Verify substitution patterns when adding tables.
```

## Notes

- After cataloging all tensions, identify **load-bearing jank**: tensions that MUST NOT be resolved without extreme care because other systems depend on their current behavior.
- The Agent Navigation Guide is the most valuable field for prompt content. It should be specific enough to prevent the wrong decision without explaining the entire fix.
- Resolution Cost helps the synthesis pass tier tensions: Low-cost tensions often become NICE-TO-HAVE, while High-cost load-bearing tensions become CRITICAL navigation guides.
