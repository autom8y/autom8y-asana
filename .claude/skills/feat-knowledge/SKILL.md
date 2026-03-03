---
name: feat-knowledge
description: "Feature knowledge discovery index for .know/feat/ files. Use when: understanding a product feature before modifying its code, finding which packages implement a feature, understanding why a feature was designed a certain way, looking up feature boundaries and failure modes. Triggers: feature knowledge, feature purpose, feature design, feature implementation map, .know/feat/, feature boundaries, product feature, feature rationale."
---

# Feature Knowledge

> Discovery index for per-feature knowledge references in `.know/feat/`. Each feature file captures purpose, conceptual model, implementation map, and boundaries -- everything an agent needs to modify a feature safely.

## Quick Reference

| Resource | Path | Contents |
|----------|------|----------|
| Feature census (index) | `.know/feat/INDEX.md` | All features with slugs, categories, complexity ratings |
| Per-feature knowledge | `.know/feat/{slug}.md` | Deep reference for a single feature |
| Generate feature knowledge | `/know --scope=feature` | Runs census then per-feature knowledge capture |

## When to Use Feature Knowledge

Read feature knowledge **before** modifying feature-related code. The decision tree:

```
Am I about to modify code that implements a product feature?
+-- No  -> Continue without feature knowledge
+-- Yes -> Continue below

Do I know which feature this code belongs to?
+-- No  -> Read(".know/feat/INDEX.md") to find the feature slug
+-- Yes -> Read(".know/feat/{slug}.md") for the feature reference

Does .know/feat/ exist?
+-- No  -> Suggest: "Run /know --scope=feature to generate feature knowledge"
+-- Yes -> Proceed with reads above
```

## How to Use

### Step 1: Find the Right Feature

Read the census index to identify which feature your target code belongs to:

```
Read(".know/feat/INDEX.md")
```

The census lists every feature with its slug, category, source evidence, and complexity rating. Use the source evidence column to match packages to features.

### Step 2: Load the Feature Reference

Once you have the slug, read the per-feature knowledge file:

```
Read(".know/feat/{slug}.md")
```

Each file contains four sections (described below). Read the entire file before making changes -- boundaries and failure modes are as important as implementation details.

### Step 3: Apply the Knowledge

- **Purpose and Design Rationale**: Understand *why* before changing *how*. Check if your change aligns with the original design intent and accepted tradeoffs.
- **Conceptual Model**: Use the feature's terminology and mental model in your code, commit messages, and comments.
- **Implementation Map**: Find the right packages and entry points. Follow established data flow patterns.
- **Boundaries and Failure Modes**: Avoid violating scope boundaries. Check known edge cases before introducing new code paths.

## Feature Knowledge Schema

Each `.know/feat/{slug}.md` file follows this structure:

| Section | What It Contains | Why It Matters |
|---------|-----------------|----------------|
| **Purpose and Design Rationale** | Problem statement, design decisions, rejected alternatives, tradeoffs, ADR references | Prevents changes that contradict design intent |
| **Conceptual Model** | Key terminology, mental model, state machines or lifecycles, inter-feature relationships | Gives agents the vocabulary to reason about the feature |
| **Implementation Map** | Packages, key types, entry points, data flow, public API surface, test locations | Tells agents exactly where to look and what to expect |
| **Boundaries and Failure Modes** | Scope limitations, known edge cases, error paths, interaction points, configuration boundaries | Protects agents from violating implicit assumptions |

## If Feature Knowledge Does Not Exist

When `.know/feat/` is absent or empty:

1. **Do not block on it.** Feature knowledge is supplementary -- agents can still work using `.know/architecture.md` and source code exploration.
2. **Suggest generation.** Tell the user: "Feature knowledge files do not exist yet. Run `/know --scope=feature` to generate them."
3. **Fall back to architecture knowledge.** `Read(".know/architecture.md")` provides package structure and layer boundaries that partially cover what feature knowledge offers.

## Census Expiry

Feature knowledge files include frontmatter with `generated` timestamps. The census (`INDEX.md`) expires after 30 days by default. Individual feature files expire after 14 days. Stale files are still useful but may not reflect recent changes -- the `/know` command regenerates them.

## Related

- `.know/architecture.md` -- Package structure and layers (complementary to feature implementation maps)
- `.know/scar-tissue.md` -- Past bugs and defensive patterns (evidence source for feature boundaries)
- `.know/design-constraints.md` -- Structural tensions and frozen areas (evidence source for feature tradeoffs)
- `pinakes/domains/feature-census.lego.md` -- Census audit criteria (how the census is graded)
- `pinakes/domains/feature-knowledge.lego.md` -- Per-feature knowledge audit criteria (how feature files are graded)
