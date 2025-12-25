# Agent Completeness Evaluation

> Checklist for verifying agent .md files are complete and valid

## Frontmatter Validation

### Required Fields

```yaml
---
name: {kebab-case identifier}           # REQUIRED
description: |                          # REQUIRED, multi-line
  {Role summary}
  {Triggers}
  {Produces}
  {Examples}
tools: {comma-separated list}           # REQUIRED
model: claude-{opus|sonnet|haiku}-4-5   # REQUIRED
color: {color name}                     # REQUIRED
---
```

### Frontmatter Checks

| Check | Pass Condition |
|-------|----------------|
| `name` exists | Non-empty string, kebab-case |
| `description` exists | Multi-line, >50 characters |
| Description has triggers | Contains "Invoke when" or "When to use" |
| Description has examples | Contains `<example>` tag |
| `tools` exists | Non-empty comma-separated list |
| `model` valid | One of: opus, sonnet, haiku (with version) |
| `color` exists | Non-empty string |

## Section Validation

### The 11 Required Sections

| # | Section | Key Content |
|---|---------|-------------|
| 1 | Title + Overview | 2-3 sentence identity statement |
| 2 | Core Responsibilities | 4-6 bullet points with bold labels |
| 3 | Position in Workflow | ASCII diagram with upstream/downstream |
| 4 | Domain Authority | You decide / You escalate / You route |
| 5 | How You Work | 3-4 phases with numbered steps |
| 6 | What You Produce | Artifact table + template |
| 7 | Handoff Criteria | Checklist for next phase |
| 8 | The Acid Test | Single pivotal question |
| 9 | Skills Reference | Cross-references to skills |
| 10 | Cross-Team Notes | When to flag for other teams |
| 11 | Anti-Patterns | 3-5 common mistakes |

### Section Detection Regex

```bash
# Check all sections present
grep -c "^## Core Responsibilities" agent.md      # Should be 1
grep -c "^## Position in Workflow" agent.md       # Should be 1
grep -c "^## Domain Authority" agent.md           # Should be 1
grep -c "^## How You Work" agent.md               # Should be 1
grep -c "^## What You Produce" agent.md           # Should be 1
grep -c "^## Handoff Criteria" agent.md           # Should be 1
grep -c "^## The Acid Test" agent.md              # Should be 1
grep -c "^## Skills Reference" agent.md           # Should be 1
grep -c "^## Cross-Team Notes" agent.md           # Should be 1
grep -c "^## Anti-Patterns" agent.md              # Should be 1
```

## Content Quality Checks

### Core Responsibilities
- [ ] Has 4-6 bullet points
- [ ] Each bullet has bold label followed by description
- [ ] Labels are action-oriented (verbs)

### Position in Workflow
- [ ] Contains ASCII diagram with boxes and arrows
- [ ] Shows upstream agent
- [ ] Shows downstream agent
- [ ] Lists artifacts produced

### Domain Authority
- [ ] Has "You decide:" section with 3-5 items
- [ ] Has "You escalate to" section with 2-3 items
- [ ] Has "You route to" section with 2-3 items

### How You Work
- [ ] Has 3-4 phases with `### Phase N:` headers
- [ ] Each phase has numbered steps
- [ ] Steps are actionable

### What You Produce
- [ ] Has artifact table with columns
- [ ] Has at least one artifact template
- [ ] Templates show expected structure

### Handoff Criteria
- [ ] Has checklist format `- [ ]`
- [ ] Has 5-8 criteria
- [ ] Criteria are verifiable (not subjective)

### The Acid Test
- [ ] Contains a single question in italics
- [ ] Question is answerable yes/no
- [ ] Includes guidance for uncertain cases

### Anti-Patterns
- [ ] Has 3-5 items
- [ ] Each has bold label and explanation
- [ ] Explains why it's problematic

## Token Budget Check

```bash
# Approximate token count (1 token ≈ 4 chars)
wc -c agent.md | awk '{print $1/4}'
```

| Model | Max Tokens | Warning Threshold |
|-------|------------|-------------------|
| opus | 4000 | 3500 |
| sonnet | 3500 | 3000 |
| haiku | 2500 | 2000 |

## Scoring

| Category | Weight | Pass Threshold |
|----------|--------|----------------|
| Frontmatter | 20% | All required fields |
| Sections | 40% | All 11 present |
| Content Quality | 30% | 80% of checks pass |
| Token Budget | 10% | Under warning threshold |

**Overall Pass**: 80% weighted score
