# Pass 6: Synthesis and Handoff (Prompt Fuel)

> Compress Passes 1-5 into per-agent Prompt Fuel, tiered by priority. This pass extracts nothing new -- it distills, prioritizes, and formats for prompt consumption.

## Purpose

Raw archaeology output from Passes 1-5 may total 1,500-2,500 lines. Agent prompts have a token budget. The synthesis prioritizes findings into three tiers per agent:
- **CRITICAL** (~7-9 items, ~40 lines per agent): Baked into the agent's system prompt
- **IMPORTANT** (~5-8 items, ~40 lines per agent): Packaged as skill reference, loaded on demand
- **NICE-TO-HAVE** (~3-5 items, ~15 lines per agent): Tool-discoverable when needed

## Inputs Required

| Input | Source | Required? |
|-------|--------|-----------|
| PASS1-SCAR-TISSUE.md | Pass 1 output | Yes |
| PASS2-DEFENSIVE-PATTERNS.md | Pass 2 output | Yes |
| PASS3-DESIGN-TENSIONS.md | Pass 3 output | Yes |
| PASS4-GOLDEN-PATHS.md | Pass 4 output | Yes |
| PASS5-TRIBAL-KNOWLEDGE.md | Pass 5 output | Only in DEEP mode |
| RITE-SPEC (agent definitions) | Agent Designer output | Yes |

## Synthesis Process

### Step 1: Per-Agent Relevance Mapping

For each agent defined in the RITE-SPEC, scan all pass outputs for entries with that agent in their Agent Mapping/Agent Relevance field. Collect:
- Scars mentioning this agent
- Guards this agent must know about
- Tensions this agent navigates
- Rules extracted for this agent
- Tribal knowledge affecting this agent's domain

### Step 2: Priority Tiering

Apply these criteria to tier each finding:

| Tier | Criteria | Token Budget |
|------|----------|-------------|
| CRITICAL | Failure mode the agent could re-introduce; Exousia boundary; load-bearing constraint | ~40 lines per agent |
| IMPORTANT | Pattern the agent should follow; tension navigation guide; decision table | ~40 lines per agent |
| NICE-TO-HAVE | Context that helps but does not prevent errors; nice-to-know history | ~15 lines per agent |

Tiering heuristics:
- Scars with recurrence risk = CRITICAL
- Tribal knowledge with HIGH confidence = CRITICAL
- Guards protecting against silent failures = CRITICAL
- Tensions with load-bearing jank = IMPORTANT
- Golden path rules = IMPORTANT
- Risk zones (unguarded) = IMPORTANT
- Historical context without recurrence risk = NICE-TO-HAVE

### Step 3: Cross-Reference Consolidation

Merge related findings into single entries. A scar, its guard, and its golden path rule often describe the same concern from different angles. Consolidate with cross-references:

```markdown
**[SCAR-004 + GUARD-036 + R-MA-002] COUNT_DISTINCT requires three declarations.**
Every COUNT_DISTINCT metric MUST set: (a) `requires_distinct=True`,
(b) `requires_raw_grain_for_rolling=True` with `raw_grain_column`,
(c) grain constraint via contract. Missing any causes silent overcounting.
```

### Step 4: Write the HANDOFF Document

Use the [handoff.md](schemas/handoff.md) schema for the output structure.

## Output Sections

The HANDOFF-PROMPT-FUEL document contains:

1. **Per-agent Prompt Fuel** (one section per agent with CRITICAL/IMPORTANT/NICE-TO-HAVE tiers)
2. **Prompt Anti-Pattern Catalog** (concrete "never do this" behaviors derived from scars)
3. **Cross-Agent Knowledge** (shared domain rules for all agents)
4. **Exousia Overrides** (jurisdiction boundaries from tribal knowledge)
5. **GO/NO-GO Assessment** (whether domain knowledge is sufficient for prompt authoring)

## Token Budget Targets

| Section | Lines | Tokens |
|---------|-------|--------|
| Per-agent (each) | 40-70 | ~500-900 |
| Anti-Patterns | 40-60 | ~500-750 |
| Cross-Agent | 30-50 | ~400-650 |
| Exousia Overrides | 15-30 | ~200-400 |
| GO/NO-GO | 15-25 | ~200-325 |
| **Total** | **250-400** | **~3,500-5,100** |

## Compression Ratios

- Raw archaeology to HANDOFF: ~5.5x compression
- HANDOFF to per-agent CRITICAL: ~2x further compression
- Raw archaeology to per-agent CRITICAL: ~11x total compression
- Net prompt budget consumed: ~40 lines per agent of domain-specific knowledge

## Quality Indicators

- **CRITICAL tier saturation**: 5-9 items per agent. Fewer than 5 = simple domain. More than 12 = scope too broad
- **Source traceability**: Every CRITICAL item must reference specific artifact IDs (SCAR-NNN, GUARD-NNN, etc.)
- **Anti-pattern coverage**: At least 1 anti-pattern derived from each scar category
- **Exousia presence**: At least 1 Exousia override per agent if tribal knowledge was collected
- **GO/NO-GO honesty**: Document known gaps; do not overstate coverage

## Example CRITICAL Entry

```markdown
### CRITICAL (must be in system prompt)

1. **[TRIBAL-003] All composites require human review.** The agent MUST
   escalate every composite creation, formula change, and dependency
   modification to the user. This is an Exousia boundary -- composites
   are never autonomous.

2. **[SCAR-004 + GUARD-036 + RISK-004] COUNT_DISTINCT requires three
   explicit declarations.** Every COUNT_DISTINCT definition MUST set:
   (a) requires_distinct=True, (b) requires_raw_grain_for_rolling=True
   with raw_grain_column, (c) grain constraint via contract. Missing any
   causes silent overcounting in rolling windows.
```

## After This Pass

The HANDOFF-PROMPT-FUEL.md is the deliverable. It is consumed by the Prompt Architect agent (in forge) to write agent prompts. Archive raw pass outputs; commit only the HANDOFF to the rite's mena directory as `domain-knowledge.md`.
