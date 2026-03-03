---
name: radar-opportunity-schema
description: "Opportunity entry format for /radar output. Use when: formatting radar opportunities, understanding OPP-NNN structure, producing radar signal findings. Triggers: radar opportunity, OPP-NNN format, radar signal entry, opportunity schema."
user-invocable: false
---

# Schema: Radar Opportunity [OPP-NNN]

## Template

```markdown
### [OPP-NNN] Title (short description of the opportunity)

- **Signal**: {radar-confidence-gaps | radar-staleness | radar-unguarded-scars | radar-constraint-violations | radar-convention-drift | radar-architecture-decay | radar-recurring-scars}
- **Severity**: HIGH | MEDIUM | LOW
- **Confidence**: {0.00–1.00} (source confidence × evidence strength — see Confidence Derivation below)
- **Evidence**:
  - `{file path}:{line}` — {specific finding}
  - `{file path}:{line}` — {specific finding}
- **Suggested Action**: {consultant-style prose describing what to do and why — NOT a machine enum}
```

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| NNN | Yes | Sequential number within this radar run (001, 002, ...). Reset per run. |
| Title | Yes | Short phrase naming the opportunity. Focus on the actionable gap, not the symptom. |
| Signal | Yes | The signal type that detected this opportunity. One of the 7 defined signal domains. |
| Severity | Yes | HIGH, MEDIUM, or LOW. See Severity Scale below. |
| Confidence | Yes | Derived value 0.00–1.00. Never omit — consumers use this for prioritization. |
| Evidence | Yes | File paths with line numbers and specific findings. Use at least one concrete reference. |
| Suggested Action | Yes | Prose recommendation. Read like a consultant note: explain the issue, name the rite or command to invoke, and state the expected outcome. |

## Confidence Derivation

Opportunity confidence is derived from two factors:

```
opportunity_confidence = source_confidence × evidence_strength
```

**Source confidence**: The `confidence` value from the `.know/` file that produced the signal.
If a signal reads from multiple `.know/` files, use the minimum confidence across them.

**Evidence strength**: Qualitative assessment of how strongly the evidence supports the finding.

| Evidence Strength | Multiplier | Description |
|-------------------|------------|-------------|
| Strong | 1.00 | Multiple concrete file:line references, unambiguous pattern |
| Moderate | 0.80 | At least one concrete reference, pattern is plausible |
| Weak | 0.60 | Indirect indicators only, no specific file:line |

**Example**: Source `.know/scar-tissue.md` has `confidence: 0.85`. The evidence is strong (3 specific file references). Result: `0.85 × 1.00 = 0.85`.

**Minimum floor**: Never report an opportunity with `confidence < 0.40`. Below that threshold, omit the finding and note in the report summary that low-confidence signals were suppressed.

## Severity Scale

| Severity | Criteria |
|----------|----------|
| HIGH | Active regression risk OR documented constraint violated OR 3+ scars in same category |
| MEDIUM | Knowledge gap that affects day-to-day decisions OR convention drift in active packages |
| LOW | Documentation staleness OR confidence gap without immediate code impact |

## Example

```markdown
### [OPP-003] Unguarded Scar in internal/sync (No Test Coverage)

- **Signal**: radar-unguarded-scars
- **Severity**: HIGH
- **Confidence**: 0.72 (scar-tissue confidence 0.90 × moderate evidence 0.80)
- **Evidence**:
  - `internal/sync/engine.go:142` — SCAR-004 defensive pattern (nil check added after production panic)
  - `.know/test-coverage.md:31` — internal/sync listed as untested package
- **Suggested Action**: The nil guard at `internal/sync/engine.go:142` was added after a production
  panic (SCAR-004), but `internal/sync` has no test coverage. A regression could silently remove
  this guard. Consider a hygiene session targeting `internal/sync` to add at least one regression
  test that exercises the nil path. Run `/theoria scar-tissue` after to confirm coverage alignment.
```

## Deduplication Rule

When multiple signals flag the same package or file:

1. Create one opportunity entry per unique (package, severity) pair.
2. List all contributing signals in the **Signal** field, comma-separated.
3. Combine evidence from all signals into a single Evidence list.
4. The Suggested Action addresses all signals together.

This prevents the report from listing the same package 4 times with 4 identical recommendations.

## Related

- [report.lego.md](report.lego.md) — Full report format and output structure
- [../INDEX.dro.md](../INDEX.dro.md) — /radar dromenon (produces these entries)
