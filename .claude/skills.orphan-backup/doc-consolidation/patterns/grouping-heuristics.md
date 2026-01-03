# Grouping Heuristics

> **Purpose**: Rules for categorizing documentation files into topic clusters during the Discovery phase (Phase 0).

## Design Principles

1. **Signal Over Content**: Classification from filename patterns and first 50 lines, not full reads
2. **Explicit Over Implicit**: When uncertain, flag as ambiguous rather than guess
3. **Cluster Affinity**: Prefer grouping related files together over fragmentation
4. **Human Escalation**: Surface ambiguous mappings for resolution

---

## Heuristic Categories

### 1. Naming Pattern Analysis

File and directory names are the strongest signal for topic clustering.

| Pattern | Topic Signal | Confidence |
|---------|--------------|------------|
| `auth-*.md`, `*-auth.md` | authentication | High |
| `*-merge*.md`, `merge-*.md` | settings-merge | High |
| `hook-*.md`, `*-hooks.md` | hook-lifecycle | High |
| `agent-*.md`, `*-agent.md` | agent-routing | High |
| `migration-*.md`, `*-migrate*.md` | migration-runbooks | High |
| `TDD-*.md` | Technical design (check content for topic) | Medium |
| `ADR-*.md` | Architecture decision (check content for topic) | Medium |
| `PRD-*.md` | Requirements (check content for topic) | Medium |
| `README.md` | Parent directory topic | Low |
| `CHANGELOG.md` | Release/versioning | Medium |

**Pattern Matching Rules:**

```yaml
# Strong signals (assign directly)
strong_patterns:
  - regex: "^(auth|authentication|login|session)-"
    topic: "authentication"
    confidence: 0.9
  - regex: "-(auth|authentication|login|session)\\.md$"
    topic: "authentication"
    confidence: 0.9
  - regex: "(settings|config).*merge"
    topic: "settings-merge"
    confidence: 0.85
  - regex: "hook[s]?[-_]?(lifecycle|events|triggers)?"
    topic: "hook-lifecycle"
    confidence: 0.85

# Weak signals (flag for review)
weak_patterns:
  - regex: "^(TDD|ADR|PRD)-\\d+"
    action: "inspect_content"
    confidence: 0.3
  - regex: "README"
    action: "inherit_from_directory"
    confidence: 0.4
```

### 2. Content Similarity Detection

When naming patterns are insufficient, analyze first 50 lines for topic signals.

**Keyword Extraction:**

```yaml
topic_keywords:
  settings-merge:
    primary: ["merge", "precedence", "tier", "override", "cascade"]
    secondary: ["skeleton", "satellite", "sync", "settings.json"]
  hook-lifecycle:
    primary: ["hook", "event", "trigger", "pre-", "post-"]
    secondary: ["SessionStart", "PreToolUse", "PostToolUse", "Stop"]
  agent-routing:
    primary: ["agent", "route", "invoke", "delegate", "Task tool"]
    secondary: ["orchestrator", "specialist", "handoff"]
  migration-runbooks:
    primary: ["migration", "upgrade", "breaking change", "runbook"]
    secondary: ["satellite", "compatibility", "before/after"]
```

**Scoring Algorithm:**

```python
def compute_topic_score(first_50_lines, topic_keywords):
    text = " ".join(first_50_lines).lower()
    primary_matches = sum(1 for kw in topic_keywords["primary"] if kw.lower() in text)
    secondary_matches = sum(1 for kw in topic_keywords["secondary"] if kw.lower() in text)

    score = (primary_matches * 2.0) + (secondary_matches * 0.5)
    max_score = (len(topic_keywords["primary"]) * 2.0) + (len(topic_keywords["secondary"]) * 0.5)

    return score / max_score if max_score > 0 else 0.0
```

**Confidence Thresholds:**

| Score Range | Action |
|-------------|--------|
| >= 0.6 | Assign to topic (high confidence) |
| 0.3 - 0.6 | Assign as supplementary + flag for review |
| < 0.3 | Mark as ambiguous |

### 3. Cross-Reference Clustering

Files that reference each other likely belong to the same topic cluster.

**Reference Detection:**

```yaml
reference_patterns:
  - markdown_link: "\\[.*\\]\\(([^)]+\\.md)\\)"
  - relative_import: "^@import\\s+['\"]([^'\"]+)['\"]"
  - see_also: "See (also )?\\[?([A-Za-z0-9-]+\\.md)\\]?"
  - skill_ref: "@([a-z0-9-]+)\\s"  # Skill references like @doc-ecosystem
```

**Clustering Rules:**

1. If file A references file B, they share at least one topic
2. If A -> B -> C (transitive reference), cluster A, B, C together
3. Maximum cluster depth: 3 hops (prevent runaway clustering)
4. Self-references are ignored

**Example:**

```
TDD-0042-settings.md -> references -> doc-ecosystem/SKILL.md
doc-ecosystem/SKILL.md -> references -> cem-sync.md

Result: All three files cluster into "settings-merge" topic
```

### 4. Directory Structure Heuristics

Directory location provides topic context.

| Directory Pattern | Default Topic | Confidence |
|-------------------|---------------|------------|
| `.claude/skills/{skill-name}/` | `{skill-name}` | High |
| `.claude/agents/` | agent-routing | Medium |
| `.claude/hooks/` | hook-lifecycle | High |
| `docs/design/` | Inspect content | Low |
| `docs/guides/` | Inspect content | Low |
| `docs/api/` | API reference (new topic) | Medium |

**Inheritance Rules:**

```yaml
# Directory-level defaults
directory_topics:
  ".claude/skills/doc-consolidation": "doc-consolidation"
  ".claude/skills/doc-ecosystem": "ecosystem-sync"
  ".claude/hooks": "hook-lifecycle"
  ".claude/agents": "agent-routing"

# Files inherit directory topic unless content strongly suggests otherwise
inheritance_threshold: 0.4  # Override only if content score > 0.4 for different topic
```

---

## Decision Tree

```
START: New file discovered
  |
  v
[1] Check filename patterns
  |-- Strong match? --> Assign topic (confidence: high)
  |-- Weak match? --> Continue to [2]
  |-- No match? --> Continue to [2]
  |
  v
[2] Analyze first 50 lines for keywords
  |-- Score >= 0.6? --> Assign topic (confidence: high)
  |-- Score 0.3-0.6? --> Assign as supplementary, flag ambiguous
  |-- Score < 0.3? --> Continue to [3]
  |
  v
[3] Check cross-references
  |-- References file with assigned topic? --> Inherit topic (confidence: medium)
  |-- No useful references? --> Continue to [4]
  |
  v
[4] Apply directory inheritance
  |-- Directory has default topic? --> Assign topic (confidence: low)
  |-- No default? --> Mark as ambiguous
  |
  v
END: File mapped or flagged for human review
```

---

## Split vs. Combine Decisions

### When to Split a Topic

| Signal | Action |
|--------|--------|
| Topic has > 10 source files | Consider subtopics |
| Estimated tokens > 15K | Split into logical subsections |
| Sources span > 3 directories | May be multiple concerns |
| Significant conflicts between sources | May need separate treatment |

**Split Criteria:**

```yaml
split_thresholds:
  max_sources_per_topic: 10
  max_tokens_per_topic: 15000
  max_directory_span: 3
  min_conflict_count_for_split: 3

split_strategy:
  - Identify natural subsection boundaries in primary source
  - Create child topics: "{parent-topic}-{subsection}"
  - Maintain parent topic as summary/overview
```

### When to Combine Topics

| Signal | Action |
|--------|--------|
| Topics have < 3 sources each | Consider merging |
| Topics share > 50% of sources | Strong merge candidate |
| Topics have "extends" relationship | Child into parent |
| Combined tokens < 5K | Merge for efficiency |

**Combine Criteria:**

```yaml
combine_thresholds:
  min_sources_per_topic: 3
  source_overlap_threshold: 0.5  # 50% shared files
  max_combined_tokens: 5000

combine_strategy:
  - Use more specific topic name as primary
  - Broader topic becomes a section within it
  - Preserve all source mappings
```

---

## Ambiguity Resolution

When automatic heuristics fail, surface for human input.

**Ambiguous Entry Format:**

```yaml
ambiguous:
  - path: "docs/guides/getting-started.md"
    candidate_topics:
      - topic_id: "agent-routing"
        confidence: 0.45
        rationale: "Contains agent invocation examples (lines 23-35)"
      - topic_id: "workflow-overview"
        confidence: 0.38
        rationale: "Covers end-to-end workflow (lines 5-15)"
    signals_found:
      - "agent" (3 occurrences)
      - "route" (1 occurrence)
      - "workflow" (5 occurrences)
    recommendation: "Assign to agent-routing as supplementary"
    resolution_needed: true
```

**Resolution Priority:**

1. **Blocking ambiguity**: File is primary source candidate for multiple topics
2. **Standard ambiguity**: File could belong to multiple topics as secondary
3. **Low-priority ambiguity**: File has weak signals for any topic

---

## Validation Checklist

Before finalizing manifest:

- [ ] Every file has at least one topic assignment
- [ ] Every topic has exactly one primary source
- [ ] No circular dependencies between topics
- [ ] Ambiguous entries have clear recommendations
- [ ] High-token topics (>10K) reviewed for split opportunities
- [ ] Small topics (<2K) reviewed for combine opportunities
- [ ] Cross-references validate topic clustering
