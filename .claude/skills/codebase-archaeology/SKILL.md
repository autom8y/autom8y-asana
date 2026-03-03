---
name: codebase-archaeology
description: "Structured 6-pass forensic codebase analysis extracting scar tissue, defensive patterns, design tensions, golden paths, and tribal knowledge. Compresses findings into Prompt Fuel for expert-level agent prompts. Use when: creating domain-expert agents, investigating codebase quality, performing deep code archaeology, generating prompt fuel for agent prompts. Triggers: archaeology, forensic, scar tissue, domain knowledge extraction, prompt fuel."
---

# codebase-archaeology

> 6-pass forensic analysis framework that extracts domain expertise from codebases and compresses it into Prompt Fuel for agent prompts.

## Pass Overview

| # | Pass | Purpose | Automatable? | Typical Yield |
|---|------|---------|-------------|---------------|
| 1 | [Scar Tissue](pass1-scar-tissue.md) | Past bugs, regressions, defensive patterns born from production failures | Largely yes | 15-30 scars |
| 2 | [Defensive Patterns](pass2-defensive-patterns.md) | Guards, assertions, constraints, safety checks | Partially | 50-80 guards, 3-8 risks |
| 3 | [Design Tensions](pass3-design-tensions.md) | Structural conflicts, load-bearing jank, missing/premature abstractions | Partially | 10-20 tensions |
| 4 | [Golden Paths](pass4-golden-paths.md) | Best-in-class exemplars paired with anti-exemplars | Partially | 3-7 exemplars, 15-25 rules |
| 5 | [Tribal Knowledge](pass5-tribal-knowledge.md) | Domain expert interview: fears, priorities, unwritten rules | No (interactive) | 10-15 nuggets |
| 6 | [Synthesis](pass6-synthesis.md) | Compress passes 1-5 into per-agent Prompt Fuel | LLM-assisted | HANDOFF doc |

## Dependency Graph

```
Pass 1 (Scar Tissue) ---+
                         |
Pass 2 (Defensive) -----+--> Pass 4 (Golden Paths) --+
                         |                             |
Pass 3 (Tensions) ------+                             +--> Pass 6 (Synthesis)
                                                       |
Pass 5 (Tribal Knowledge) ----------------------------+
                                                       |
RITE-SPEC (agent definitions) -------------------------+
```

- Passes 1-3 are independent and run in parallel
- Pass 4 benefits from Passes 1-3 (knows what "gold" means in context of known failures)
- Pass 5 is optional but generates targeted questions from Passes 1-4
- Pass 6 requires all previous passes plus the RITE-SPEC agent definitions

## Quick Start

**STANDARD mode** (recommended): Execute Passes 1-4, then Pass 6.
**DEEP mode**: Execute Passes 1-5 (including domain expert interview), then Pass 6.

For each pass: read the pass reference file, execute the search queries against the target codebase, categorize findings using the schema, and write output to `.sos/wip/ARCHAEOLOGY/`.

## Token Budget

| Pass | Output Lines | Estimated Tokens | Notes |
|------|-------------|-----------------|-------|
| Pass 1 | 150-260 | ~2,500-3,500 | Scales with commit history depth |
| Pass 2 | 400-730 | ~5,000-8,500 | Scales with codebase LOC |
| Pass 3 | 150-240 | ~2,000-3,200 | Fewer entries but longer narratives |
| Pass 4 | 250-400 | ~3,500-5,200 | Includes code snippets |
| Pass 5 | 80-120 | ~1,000-1,500 | Interview transcript |
| Pass 6 | 250-400 | ~3,500-5,100 | Compression of all passes |
| **Total** | **1,280-2,150** | **~17,500-27,000** | |

## Output Convention

All archaeology artifacts are written to `.sos/wip/ARCHAEOLOGY/`:

```
.sos/wip/ARCHAEOLOGY/
    PASS1-SCAR-TISSUE.md
    PASS2-DEFENSIVE-PATTERNS.md
    PASS3-DESIGN-TENSIONS.md
    PASS4-GOLDEN-PATHS.md
    PASS5-TRIBAL-KNOWLEDGE.md          (only in DEEP mode)
    HANDOFF-PROMPT-FUEL.md             (Pass 6 output)
```

After rite creation, archive raw passes and commit only the HANDOFF as `domain-knowledge.md` in the rite's mena directory.

## Execution Modes

| Mode | Passes | Duration | Use Case |
|------|--------|----------|----------|
| QUICK | Skip all | 0 | Rapid prototyping, familiar domains |
| STANDARD | 1-4 + 6 | 15-30 min | New rites with good codebase coverage |
| DEEP | 1-6 | 30-60 min | Critical domains, production-facing agents |

## Quality Indicators

1. **Scar coverage**: At least 3 scars per agent role
2. **Guard-to-risk ratio**: At least 10:1 guards to risk zones
3. **Tension resolution cost**: Most tensions Low or Medium cost
4. **Tribal knowledge hit rate**: At least 40% HIGH confidence answers
5. **CRITICAL tier saturation**: 5-9 CRITICAL items per agent in HANDOFF

## Schemas

- [scar-entry.md](schemas/scar-entry.md) -- `[SCAR-NNN]` entry format
- [guard-entry.md](schemas/guard-entry.md) -- `[GUARD-NNN]` entry format
- [tension-entry.md](schemas/tension-entry.md) -- `[TENSION-NNN]` entry format
- [exemplar-entry.md](schemas/exemplar-entry.md) -- `[GOLD-NNN]` entry format
- [tribal-entry.md](schemas/tribal-entry.md) -- `[TRIBAL-NNN]` entry format
- [handoff.md](schemas/handoff.md) -- HANDOFF-PROMPT-FUEL document structure

## Consumers

- **domain-forensics** (forge rite): Executes all passes against target codebase
- **prompt-architect** (forge rite): Consumes HANDOFF to write agent prompts
- Any agent performing structured codebase investigation
