# Schema: Tribal Knowledge Entry [TRIBAL-NNN]

## Template

```markdown
### [TRIBAL-NNN] Title
- **Question**: {the question asked}
- **Raw Answer**: {exact domain expert response, verbatim}
- **Extracted Rule**: {formalized rule for agent prompt, 1-2 sentences}
- **Confidence**: {HIGH | MEDIUM | LOW}
```

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| NNN | Yes | Sequential number (001, 002, ...). |
| Title | Yes | Short descriptive title summarizing the knowledge nugget. |
| Question | Yes | The exact question asked. Include what pass findings informed it. |
| Raw Answer | Yes | Verbatim response from domain expert. If they deferred, record "Don't know / skip". |
| Extracted Rule | Yes | Formalized rule suitable for embedding in an agent prompt. Must be actionable. For deferred answers, backfill from codebase evidence and note the source. |
| Confidence | Yes | HIGH (expert gave clear answer adding new info), MEDIUM (aligns with code evidence, no new info), LOW (expert deferred, rule synthesized from code). |

## Example

```markdown
### [TRIBAL-003] All Composites Require Human Review
- **Question**: What would you NEVER want an AI to modify without human review?
- **Raw Answer**: "All composites"
- **Extracted Rule**: The agent MUST escalate all composite modifications
  (creation, formula changes, dependency changes) to the user for review.
  This is an Exousia boundary -- composites are never autonomous.
- **Confidence**: HIGH -- explicit user preference. Non-negotiable.
```

```markdown
### [TRIBAL-007] Fragile Definitions Unknown
- **Question**: What is the most fragile definition in the registry?
- **Raw Answer**: "Don't know / skip"
- **Extracted Rule**: Fall back to Pass 4 evidence. Definitions with
  commented-out required fields, missing constraints, or arbitrary defaults
  should be treated as fragile. See GOLD-003 anti-exemplar.
- **Confidence**: MEDIUM -- inferred from codebase, not confirmed by expert.
```

## Notes

- Always record the raw answer verbatim, even for "don't know" responses. Absence of knowledge is itself informative.
- HIGH confidence answers that define autonomy boundaries become Exousia Overrides in the HANDOFF.
- When backfilling LOW confidence entries, always cite the specific pass and entry ID that provided the evidence.
