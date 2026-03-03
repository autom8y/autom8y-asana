# Schema: Thematic Synthesis

## Template

```
## Theme {N}: {Theme Title}

**Consensus**: {What the literature broadly agrees on, with evidence tier}
**Sources**: [SRC-NNN], [SRC-NNN], ...

**Controversy** (if any): {Where sources disagree, with the nature of the disagreement}
**Dissenting sources**: [SRC-NNN] argues {position}, while [SRC-NNN] argues {counter-position}

**Practical Implications**:
- {Implication 1 for the target domain}
- {Implication 2 for the target domain}

**Evidence Strength**: {STRONG|MODERATE|WEAK|MIXED}
```

## Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| Theme Title | Yes | Descriptive name for the thematic cluster. Should be actionable, not academic (e.g., "Write-ahead logging is the consensus durability mechanism" not "Durability approaches"). |
| Consensus | Yes | The majority view, stated as a claim. Include the evidence tier of the consensus claim. |
| Sources | Yes | SRC-NNN references to all sources contributing to this theme. |
| Controversy | Conditional | Required if sources disagree on any aspect of the theme. Omit if consensus is clear. |
| Dissenting sources | Conditional | Required if Controversy is present. Identify which sources hold which positions. |
| Practical Implications | Yes | At least 1 implication. What does this theme mean for someone working in the target domain? |
| Evidence Strength | Yes | Overall strength of evidence for this theme. MIXED if consensus and controversy coexist. |

## Synthesis Rules

1. **Group by insight, not by source.** Themes emerge from cross-source patterns, not from individual papers.
2. **Minimum 3 themes.** If fewer than 3 themes emerge, the source catalog is likely too narrow. Return to source discovery.
3. **Acknowledge gaps.** If a theme has weak evidence, say so. If an important sub-topic has no coverage, note it as a knowledge gap.
4. **Controversy is valuable.** Do not suppress disagreement to present clean consensus. Consumers need to know where the field is unsettled.
5. **Practical over academic.** Implications should be actionable ("use X pattern when Y condition holds") not observational ("the field is moving toward X").

## Example

```
## Theme 1: Raft Has Displaced Paxos as the Practical Consensus Default

**Consensus**: For new distributed systems, Raft is the recommended consensus algorithm due to its understandability advantage over Paxos, with equivalent correctness guarantees. [**STRONG**]
**Sources**: [SRC-001], [SRC-003], [SRC-007], [SRC-012]

**Controversy**: Whether Raft's performance matches Paxos variants in high-throughput scenarios. Multi-Paxos implementations in production (e.g., Google's Chubby) report lower latency at scale than Raft implementations.
**Dissenting sources**: [SRC-005] argues Multi-Paxos outperforms Raft at >10K ops/sec, while [SRC-007] argues the gap is implementation-dependent, not algorithmic.

**Practical Implications**:
- Default to Raft for new consensus implementations unless benchmarks demonstrate a specific performance bottleneck
- If adopting a Paxos variant, budget for significant implementation complexity and testing effort
- Consider CRDTs for workloads that can tolerate eventual consistency (avoids consensus entirely)

**Evidence Strength**: STRONG (consensus on Raft preference) / MIXED (performance comparison)
```

## Aggregation to .know/ Output

The synthesis section of the final `.know/literature-{domain}.md` file contains all themes in sequence. The theme numbering is continuous (Theme 1, Theme 2, ...). After all themes, a "Knowledge Gaps" section lists domains or sub-topics where evidence was insufficient.
