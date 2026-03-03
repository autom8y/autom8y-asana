---
name: research
description: "Run a structured literature review for a domain, producing .know/literature-{domain}.md with evidence-graded findings."
argument-hint: "{domain} [--depth=SURVEY|REVIEW]"
allowed-tools: Bash, Read, Write, Glob, Grep, Skill, WebSearch, WebFetch
model: opus
context: fork
---

# /research -- Literature Review Generator

Runs a structured literature review for a given domain, producing a `.know/literature-{domain}.md` file with evidence-graded findings. Single-agent execution -- no orchestration.

## Context

This command operates in forked context (transient session). It generates `.know/` files at the project root. The output complements codebase-facing `.know/` files (architecture, conventions, etc.) with external scholarship.

## Pre-flight

1. **Parse arguments**:
   - `domain`: Required. Free-form topic string (e.g., "cache-consistency", "distributed-consensus", "event-sourcing"). Will be normalized to kebab-case for the filename.
   - `--depth`: Optional. `SURVEY` or `REVIEW` (default: `REVIEW`).
     - `SURVEY`: Source discovery + basic evidence grading. 5-8 sources. Quick landscape scan.
     - `REVIEW`: Full multi-pass review. 10-15 sources. Thematic synthesis. Comprehensive output.

2. **Normalize domain**:
   - Convert to kebab-case: spaces to hyphens, lowercase, strip non-alphanumeric except hyphens.
   - The output filename will be: `.know/literature-{normalized-domain}.md`

3. **Load literature review skill**:
   ```
   Skill("literature-review")
   ```
   This loads the evidence grading scale, source taxonomy, review protocol, and schemas into context. Source: `rites/shared/mena/literature-review/`.

4. **Check for existing output**:
   - If `.know/literature-{domain}.md` exists:
     - Read its YAML frontmatter
     - Parse `generated_at` and `expires_after`
     - If not expired: report "Literature review for '{domain}' is current (generated {date}, expires {date}). Use --force to regenerate." and STOP.
     - If expired: proceed with regeneration.
   - If file does not exist: proceed.

5. **Check tool availability**:
   - Verify WebSearch and WebFetch are available.
   - If unavailable: WARN "WebSearch/WebFetch not available. Review will use model training knowledge only. All source claims will be UNVERIFIED. Proceed? (y/n)"
   - If user declines: STOP.

6. **Ensure .know/ directory exists**:
   ```
   mkdir -p .know
   ```

## Phase 1: Source Discovery

Search for sources relevant to the domain using WebSearch. Execute multiple search queries to maximize coverage:

### Search Strategy

```
Query 1: "{domain} survey paper" OR "{domain} overview"
Query 2: "{domain} RFC" OR "{domain} specification" (if domain is protocol/standard-related)
Query 3: "{domain} best practices" OR "{domain} architecture patterns"
Query 4: "{domain} comparison" OR "{domain} trade-offs"
```

For SURVEY depth: execute queries 1-2. For REVIEW depth: execute all 4.

### Source Collection

For each search result:
1. Assess relevance to the domain question (skip obviously irrelevant results)
2. Fetch the source via WebFetch if URL is accessible
3. Extract metadata: title, author(s), year, type, URL
4. Record a 2-4 sentence summary of what the source contributes
5. Catalog using the [review-entry schema](../literature-review/schemas/review-entry.md)

### Source Targets

| Depth | Minimum Sources | Minimum Primary Sources | Source Type Diversity |
|-------|----------------|------------------------|---------------------|
| SURVEY | 5 | 2 | At least 2 types |
| REVIEW | 10 | 4 | At least 3 types |

If source targets are not met after all search queries, note this in the output as a knowledge gap. Do not fabricate sources to meet targets.

## Phase 2: Evidence Grading

For each source in the catalog:

1. **Read companion reference**: Load the evidence grading framework via `Skill("literature-review")` for tier definitions.

2. **Extract key claims**: Identify the 2-5 most relevant claims from the source for the domain question.

3. **Assign evidence tiers**: Apply the grading scale from the evidence-grading companion. Each claim gets an independent tier.

4. **Cross-reference**: When multiple sources assert the same claim, note the corroboration. This may upgrade tiers (e.g., MODERATE to STRONG when a second independent primary source is found).

5. **Verify titles**: For every paper or article cited, search for its exact title via WebSearch. If no results found, downgrade the source verification status and any associated claims.

**CRITICAL**: Never fabricate DOIs. If a DOI cannot be retrieved, omit it. A missing DOI with an honest "Not available" is correct. A fabricated DOI is a credibility-destroying error.

## Phase 3: Synthesis (REVIEW Depth Only)

Skip this phase for SURVEY depth.

1. **Read synthesis schema**: Access synthesis schema via `Skill("literature-review")` companion files.

2. **Identify themes**: Group claims across sources into thematic clusters. Minimum 3 themes for REVIEW depth.

3. **Assess consensus vs. controversy**: For each theme, determine whether sources agree (consensus) or disagree (controversy). Document both sides.

4. **Extract practical implications**: For each theme, identify what it means for someone working in the target domain. Actionable over observational.

5. **Identify knowledge gaps**: Note sub-topics within the domain where evidence is insufficient or absent.

## Phase 4: Output Assembly

### Construct the .know/ file

Build YAML frontmatter:
```yaml
---
domain: "literature-{domain}"
generated_at: "{current ISO 8601 UTC timestamp}"
expires_after: "180d"
source_scope:
  - "external-literature"
generator: bibliotheca
confidence: {computed from evidence tier distribution}
format_version: "1.0"
---
```

Confidence computation:
- Weight each claim: STRONG=1.0, MODERATE=0.7, WEAK=0.4, UNVERIFIED=0.2
- Overall confidence = weighted average of all claim tiers, rounded to 2 decimal places
- If >50% of claims are UNVERIFIED, cap confidence at 0.45

### Body Structure

```markdown
# Literature Review: {Domain Title}

> LLM-synthesized literature review. Citations should be independently verified before use in production decisions or published work.

## Executive Summary

{3-5 sentences. What the literature says about this domain. Key consensus, key controversies, overall evidence quality.}

## Source Catalog

{All sources using the review-entry schema, ordered by relevance (highest first)}

### [SRC-001] {Title}
...

### [SRC-NNN] {Title}
...

## Thematic Synthesis

{For REVIEW depth only. All themes using the synthesis schema.}

### Theme 1: {Title}
...

### Theme N: {Title}
...

## Evidence-Graded Findings

{Top findings across all sources, ordered by evidence strength.}

### STRONG Evidence
- {Finding} -- Sources: [SRC-NNN], [SRC-NNN]
- ...

### MODERATE Evidence
- {Finding} -- Sources: [SRC-NNN]
- ...

### WEAK Evidence
- {Finding} -- Sources: [SRC-NNN]
- ...

### UNVERIFIED
- {Finding} -- Basis: model training knowledge
- ...

## Knowledge Gaps

{Sub-topics within the domain where evidence was insufficient, sources were inaccessible, or coverage was incomplete. At least 1 gap must be documented -- no review is exhaustive.}

- {Gap 1}: {Why this gap exists and what would be needed to fill it}
- ...

## Domain Calibration

{If >80% of graded claims are STRONG}: "High confidence distribution reflects a well-studied domain with canonical literature. For less-established domains, expect more MODERATE/UNVERIFIED claims. Evidence grades reflect training data density, not independent verification rigor."

{If >50% of graded claims are UNVERIFIED}: "Low confidence distribution reflects a domain with sparse or paywalled primary literature. Many claims could not be independently corroborated. Treat findings as starting points for manual research, not as settled knowledge."

## Methodology Note

This literature review was generated by an LLM (Claude) using WebSearch for source discovery and WebFetch for source verification. Limitations:

1. **Training data cutoff**: Model knowledge is frozen at the training cutoff date. Recent publications may be missing despite web search augmentation.
2. **Source access**: Paywalled content could not be fully verified. Claims from paywalled sources are graded MODERATE at best.
3. **Citation accuracy**: Paper titles and authors were verified via web search where possible, but some citations may contain inaccuracies. DOIs are included only when confirmed.
4. **No domain expertise**: This review reflects what the literature says, not expert judgment about what the literature gets right. Use as a structured research draft, not as authoritative assessment.

Generated by `/research {domain}` on {date}.
```

### Write and verify

```
Write(".know/literature-{domain}.md", frontmatter + body)
Read(".know/literature-{domain}.md", limit=30)
```

Confirm frontmatter fields are present and valid. Confirm body sections exist.

## Phase 5: Report (MANDATORY -- never skip)

**This phase is non-optional.** The review is incomplete until the summary report is displayed to the user. Do not end with "done", "complete", or a bare URL list. Always execute the steps below.

### Step 1: Read back the generated file

```
Read(".know/literature-{domain}.md", limit=30)
```

Extract from the frontmatter: `domain`, `confidence`, `expires_after`, `generated_at`.

### Step 2: Count evidence tiers

Scan the file for evidence tier markers. Count occurrences of each:
```
Grep("[**STRONG**]", path=".know/literature-{domain}.md", output_mode="count")
Grep("[**MODERATE**]", path=".know/literature-{domain}.md", output_mode="count")
Grep("[**WEAK**]", path=".know/literature-{domain}.md", output_mode="count")
Grep("[**UNVERIFIED**]", path=".know/literature-{domain}.md", output_mode="count")
```

### Step 3: Count sources

Count source catalog entries: `Grep("### \\[SRC-", path=".know/literature-{domain}.md", output_mode="count")`

Identify primary sources (peer-reviewed papers): `Grep("peer-reviewed paper", path=".know/literature-{domain}.md", output_mode="count")`

### Step 4: Display summary

Output this exact format (fill values from steps 1-3):

```
## Literature Review Generated: .know/literature-{domain}.md

| Field | Value |
|-------|-------|
| Domain | literature-{domain} |
| Depth | {SURVEY|REVIEW} |
| Sources | {N} cataloged |
| Primary sources | {N} (peer-reviewed papers) |
| Source types | {N} ({list unique types}) |
| Confidence | {confidence} |
| Expires | {computed expiry date} |

### Evidence Distribution
| Tier | Claims |
|------|--------|
| STRONG | {N} |
| MODERATE | {N} |
| WEAK | {N} |
| UNVERIFIED | {N} |

### Key Themes

{List theme titles from Thematic Synthesis section, numbered, with evidence strength}

### Disclaimer
This is an LLM-synthesized literature review. Citations should be
independently verified before use in production decisions or published work.

Consumable by any CC agent via `Read(".know/literature-{domain}.md")`.
Regenerate with: `/research {domain} --force`
```

## Error Handling

| Scenario | Action |
|----------|--------|
| No domain argument | ERROR: "Usage: /research {domain} [--depth=SURVEY\|REVIEW]" |
| WebSearch unavailable | WARN and offer model-knowledge-only mode (all claims UNVERIFIED) |
| WebFetch unavailable | WARN; proceed with WebSearch only; downgrade verification to "partial" at best |
| Source targets not met | WARN in output; document in Knowledge Gaps; do not fabricate sources |
| Existing file not expired | STOP with "current" message unless --force |
| .know/ not writable | ERROR with permission details |

## Anti-Patterns

- **Fabricating DOIs**: Never invent a DOI. Omit with "Not available" if unknown.
- **Inflating evidence tiers**: When in doubt, grade DOWN not up. UNVERIFIED is honest.
- **Skipping verification**: Always attempt to verify paper titles via WebSearch before citing.
- **Suppressing controversy**: If sources disagree, document the disagreement. Do not present false consensus.
- **Ignoring the methodology note**: Every output must include the methodology note. It is not optional.
- **Modifying the literature-review skill**: The protocol lives in the skill. This dromenon consumes it. Do not duplicate or override the skill's grading definitions here.
