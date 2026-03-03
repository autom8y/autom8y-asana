# Pass 4: Golden Path Exemplars

> Identify best-in-class patterns for each major concept type, paired with anti-exemplars from the same codebase. Golden Path Contrast is one of the most effective prompt engineering techniques for code generation.

## Purpose

Instead of listing rules abstractly, show the best example and the worst example side by side. The agent learns what "good" looks like in THIS specific codebase rather than from generic best practices. Each exemplar produces extracted rules that become agent prompt content.

## Sources

| Source | What to Extract |
|--------|----------------|
| Concept instances | Find all instances of each major concept type (models, handlers, tests, configs) |
| Completeness analysis | Which instance has all fields set, all constraints applied, documentation present? |
| Test quality | Parametrized coverage, both paths tested, assertion messages, edge cases |
| Anti-exemplars | The worst or most incomplete instance of the same type |

## Search Queries

Parameterized for the target codebase:

```bash
# Find all instances of the primary concept type
# (Adapt pattern to match the project's domain objects)
Grep pattern: "class \\w+.*Model|def register_|def create_"

# Completeness signals
Grep pattern: "description=|precision=|contract=|metadata=|tags="

# Test parametrization (indicates thorough testing)
Grep pattern: "@pytest.mark.parametrize|t.Run\\(|describe\\("

# Documentation completeness
Grep pattern: '""".*"""' (multiline) or "// [A-Z].*\\." (Go doc comments)
```

### Project-Type Variants

| Language | Gold Signals | Anti-Exemplar Signals |
|----------|-------------|----------------------|
| Python | Full type hints, docstrings, `@dataclass` with all fields, parametrized tests | Missing types, bare `dict`, `# TODO`, commented-out code |
| Go | Interface compliance, table-driven tests, error wrapping, doc comments | `interface{}`, ignored errors, no table tests, panic |
| TypeScript | Strict types, Zod schemas, React Testing Library, accessibility | `any`, `as` casts, no tests, inline styles |
| Infrastructure | Lifecycle hooks, tags, outputs, documentation | Missing tags, hardcoded values, no outputs, no README |

## Categorization

For each major concept type in the codebase, identify:

1. **The gold exemplar**: The most complete, well-documented, correctly-constrained instance
2. **The anti-exemplar**: The least complete instance of the same type
3. **Extracted rules**: Generalized rules derived from the contrast

Common concept types (adapt per project):
- Model/entity definitions
- Composite/computed definitions
- Configuration/registration entries
- Test patterns
- Integration/join definitions
- API endpoint handlers

## Output Schema

Write each exemplar using the [exemplar-entry.md](schemas/exemplar-entry.md) schema. Number sequentially: `[GOLD-001]`, etc.

## Rule Extraction

After identifying exemplars, extract rules using this naming convention:

```
R-{AGENT-ABBREV}-{NNN}: Rule text
```

Rules should be:
- Concrete and actionable (not "write good code")
- Specific to this codebase (not generic best practices)
- Derived from the contrast between gold and anti-exemplar
- Mappable to a specific agent role

## Quality Indicators

- **Minimum yield**: 3+ exemplars covering the project's primary concept types
- **Rule extraction**: 15-25 extracted rules across all exemplars
- **Agent coverage**: Rules should map to at least 3 distinct agent roles
- **Anti-exemplar specificity**: Anti-exemplars should cite specific files and lines, not generic complaints

## Example Entry

```markdown
## [GOLD-001] Best Model Definition: `n_distinct`
- **Location**: `src/core/library.py:257-280`
- **Why It's Gold**: Most complete definition in the library. Has:
  - Aggregation type correctly paired with raw-grain flag
  - Precision and type both set explicitly
  - Constraint contract enforcing grain safety
  - Extensive block comment explaining WHY the constraint exists
  - AI metadata with natural language names and semantic notes
- **Pattern Rule**: Every COUNT_DISTINCT model must answer three questions
  explicitly: (1) What grain am I counting? (2) Can I be aggregated from
  pre-aggregated data? (3) What dimensions inflate my count?
- **Code Snippet**: [include 15-25 lines of the actual code]
- **Anti-Exemplar**: `first_ran` / `last_ran` (`library.py:307-343`)
  Missing precision, missing type, no contract, no semantic metadata.
- **Anti-Exemplar Location**: `src/core/library.py:307-343`
```

## Decision Tables

When exemplars reveal pattern choices (e.g., which formula class to use, which test pattern to apply), extract a decision table:

```markdown
| Situation | Correct Pattern | Wrong Pattern | Rule |
|-----------|----------------|---------------|------|
| Numerator is cost | CostDivisionFormula | DivisionFormula | R-MA-001 |
| Value is a list | ComputedFieldSpec | Metric | R-QS-003 |
| Test verifies formula | Parametrized class | Single assertion | R-AQ-001 |
```

## After This Pass

If running DEEP mode, proceed to Pass 5 (Tribal Knowledge Interview). Otherwise, skip to Pass 6 (Synthesis). Golden path rules feed directly into Pass 6's per-agent CRITICAL/IMPORTANT/NICE-TO-HAVE tiering.
