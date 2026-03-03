# Pass 5: Tribal Knowledge Interview

> Interactive interview with the domain expert to extract knowledge not encoded in code: priorities, fears, unwritten rules, judgment calls. This pass generates questions -- it does not answer them.

## Purpose

Tribal knowledge is the **Exousia Calibration** mechanism. It reveals:
- What the domain expert actually worries about (vs. what the code suggests)
- Jurisdiction boundaries that should be non-negotiable
- Hidden priorities (e.g., "wrong data is worse than no data")
- Missing context the other passes cannot detect (operational concerns, business constraints)

## Method

Generate 3-5 targeted questions per agent role, informed by Passes 1-4 findings. Present questions to the domain expert. Record raw answers and extract rules.

## Question Templates

For each agent role defined in the RITE-SPEC, generate questions from these categories:

### Category 1: Most Common Mistakes
> "What is the single most common mistake when [agent's primary task]?"

Informed by: Pass 1 scar categories. If scars cluster in one category, ask about that category specifically.

### Category 2: Most Feared Failure Mode
> "What is the scariest failure mode in [agent's domain]?"

Informed by: Pass 2 risk zones. Reference specific unguarded areas.

### Category 3: Unwritten Rules
> "Are there unwritten rules about [specific concern from Pass 3 tensions]?"

Informed by: Pass 3 tensions. Ask about load-bearing jank specifically.

### Category 4: PR Review Priorities
> "When you review a PR touching [critical file], what do you check first?"

Informed by: Pass 4 golden paths. Ask about the difference between gold and anti-exemplar patterns.

### Category 5: Autonomy Boundaries
> "What would you NEVER want an AI agent to modify without human review?"

This question directly produces Exousia boundaries. Always include it for every role.

## Question Generation Process

1. Read the RITE-SPEC agent definitions
2. For each agent, select the 2-3 most relevant question categories
3. Parameterize questions with findings from Passes 1-4
4. Present questions to the domain expert
5. Record raw answers verbatim before extracting rules

## Output Schema

Write each nugget using the [tribal-entry.md](schemas/tribal-entry.md) schema. Number sequentially: `[TRIBAL-001]`, etc.

## Confidence Scoring

- **HIGH**: Domain expert gave a clear, specific answer that adds information beyond what code analysis found
- **MEDIUM**: Answer aligns with codebase evidence but adds no new information, OR expert gave a partial answer
- **LOW**: Expert deferred ("don't know / skip") and the rule is synthesized from codebase evidence alone

## Quality Indicators

- **Minimum yield**: 8+ nuggets across all agent domains
- **Hit rate**: At least 40% HIGH confidence. Lower suggests wrong expert or generic questions
- **Exousia coverage**: At least 1 autonomy boundary per critical agent role
- **Backfill rate**: LOW-confidence entries should reference the specific pass that provided backfill evidence

## Example Question Set

For a **query-specialist** agent after Pass 1 revealed 6 data inflation scars:

```markdown
1. "What is the hardest-to-debug failure in the query pipeline?"
   (Informed by: SCAR-001 through SCAR-006, all data inflation)

2. "When you review a PR touching the SQL generator, what do you check first?"
   (Informed by: TENSION-002, SQL string surgery pattern)

3. "What would you NEVER want an AI to modify in the query layer?"
   (Autonomy boundary question)
```

## After This Pass

Proceed to Pass 6 (Synthesis). Tribal knowledge provides Exousia overrides and priority calibration that the automated passes cannot produce.
