# Schema: HANDOFF-PROMPT-FUEL Document

## Document Structure

```markdown
# HANDOFF: {Domain} Domain Knowledge -> forge/Prompt Architect

### Target: {rite-name} rite agent prompts
### Source: {N}-pass forensic archaeology of {target} codebase
### Upstream Artifacts:
- PASS1-SCAR-TISSUE.md ({N} scars)
- PASS2-DEFENSIVE-PATTERNS.md ({N} guards, {N} risk zones)
- PASS3-DESIGN-TENSIONS.md ({N} tensions)
- PASS4-GOLDEN-PATHS.md ({N} exemplars, {N} rules)
- PASS5-TRIBAL-KNOWLEDGE.md ({N} nuggets) [if DEEP mode]
### Date: {YYYY-MM-DD}

---

## Prompt Fuel: {agent-name}

### CRITICAL (must be in system prompt)
1. **[source-IDs] Rule title.** Narrative with file locations and references.

### IMPORTANT (skill reference)
8. **[source-IDs] Rule title.** Narrative.

### NICE-TO-HAVE (tool-discoverable)
13. **[source-IDs] Rule title.** Narrative.

---
[Repeat per agent]
---

## Prompt Anti-Pattern Catalog

### AP-01: {Anti-pattern title}
**Source**: {SCAR-NNN or GOLD-NNN anti-exemplar}
**Anti-Pattern**: {concrete wrong behavior}
**Rule**: {correct behavior}

[Repeat per anti-pattern]

---

## Cross-Agent Knowledge

### CK-01: {Shared knowledge title}
{1-3 sentence description of knowledge shared across all agents}

[Repeat per cross-cutting concern]

---

## Exousia Overrides from Tribal Knowledge

### EX-01: {Override title} [{TRIBAL-NNN}]
**Applies to**: {agent-name}
**Boundary**: {what the agent must/must not do}
**Rationale**: {domain expert quote or justification}

[Repeat per override]

---

## GO/NO-GO: Readiness for Prompt Authoring

### Assessment: {GO | NO-GO}

### Rationale
{2-3 paragraph assessment of coverage, prioritization, and gaps}

### Known Gaps (acceptable for prompt authoring)
1. {Gap description and mitigation}

### Recommendation
{1-2 sentence final recommendation}
```

## Section Descriptions

| Section | Purpose | Target Size |
|---------|---------|-------------|
| Per-agent Prompt Fuel | CRITICAL/IMPORTANT/NICE-TO-HAVE tiered knowledge | 40-70 lines per agent |
| Anti-Pattern Catalog | Concrete "never do this" behaviors from scars | 40-60 lines total |
| Cross-Agent Knowledge | Domain rules shared by all agents | 30-50 lines total |
| Exousia Overrides | Jurisdiction boundaries from tribal knowledge | 15-30 lines total |
| GO/NO-GO | Honest assessment of coverage and gaps | 15-25 lines total |

## Tiering Rules

| Tier | Include When | Token Priority |
|------|-------------|---------------|
| CRITICAL | Failure mode agent could re-introduce; Exousia boundary; load-bearing constraint | Always in system prompt |
| IMPORTANT | Navigation guide for tension; golden path rule; decision table | Skill reference (loaded on demand) |
| NICE-TO-HAVE | Historical context; low-risk awareness; infrequently relevant | Discoverable via tools |

## Numbering

- Per-agent items numbered continuously (1-N) across all tiers
- Anti-patterns: AP-01, AP-02, ...
- Cross-agent: CK-01, CK-02, ...
- Exousia: EX-01, EX-02, ...

## Quality Checklist

- [ ] Every CRITICAL item references specific artifact IDs
- [ ] Every agent has 5-9 CRITICAL items (fewer = simple domain; more = scope too broad)
- [ ] Anti-patterns derived from real scars, not hypothetical concerns
- [ ] Cross-agent knowledge covers architecture, primary threat, and key file map
- [ ] GO/NO-GO honestly documents known gaps
- [ ] Total HANDOFF is 250-400 lines (compress further if exceeding)
