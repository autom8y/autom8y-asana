---
user-invocable: false
---

# /spike Templates

> Agent prompts and report templates.

## Agent Invocation Templates

### Architecture/Design Questions

```markdown
Act as **Architect**.

SPIKE MODE (Time-boxed research)
Question: {research-question}
Time budget: {timebox}
Deliverable: {type}

Research and document findings:

1. Understand the question/problem
2. Research options (libraries, patterns, approaches)
3. Build proof of concept if needed (throwaway code)
4. Document findings with:
   - Options considered
   - Pros/cons of each
   - Recommendation (if applicable)
   - Open questions

Time limit: {timebox} - Stop at deadline regardless of completeness

Save findings to: /docs/research/SPIKE-{slug}.md
```

### Implementation Feasibility

```markdown
Act as **Principal Engineer**.

SPIKE MODE (Time-boxed research)
Question: {research-question}
Time budget: {timebox}

Investigate feasibility:

1. Review existing codebase
2. Research implementation approaches
3. Build minimal proof of concept (throwaway)
4. Estimate effort for production implementation
5. Document risks and unknowns

Deliverable: Feasibility report with effort estimate

Save to: /docs/research/SPIKE-{slug}.md
```

### Technology Comparison

```markdown
Act as **Architect**.

SPIKE MODE (Technology comparison)
Question: {research-question}
Options to compare: {option1, option2, option3}
Time budget: {timebox}

Compare technologies:

1. Research each option
2. Build simple POC for each (if time permits)
3. Compare on criteria:
   - Performance
   - Developer experience
   - Community/support
   - License/cost
   - Integration complexity
   - Long-term viability
4. Make recommendation

Deliverable: Comparison matrix + recommendation

Save to: /docs/research/SPIKE-{slug}.md
```

---

## Spike Report Template

```markdown
# Spike: {research-question}

> **Status**: Complete
> **Date**: 2025-12-24
> **Researcher**: {agent-name}
> **Time Invested**: {actual-time} / {timebox}

## Question

{Original research question}

## Success Criteria

{What we wanted to learn}

## Findings

{Summary of what was learned}

### Options Considered

1. **Option 1**: {name}
   - Pros: ...
   - Cons: ...
   - Effort: ...

2. **Option 2**: {name}
   - Pros: ...
   - Cons: ...
   - Effort: ...

### Proof of Concept

{Description of POC built, if any}
{Link to throwaway code, if saved}

### Performance/Benchmarks

{Any measurements taken}

## Recommendation

{Suggested approach, if applicable}

## Open Questions

{What remains unknown}

## Next Steps

- [ ] Create /task for implementation (if approved)
- [ ] Additional spikes needed (if more research required)
- [ ] Decision needed from stakeholder

## Artifacts

- Spike report: /docs/research/SPIKE-{slug}.md
- POC code: /tmp/spike-{slug}/ (throwaway)
- Benchmarks: {if applicable}
```

---

## Quick-Start Templates

### Technology Selection Spike

```bash
/spike "Choose database: PostgreSQL vs MongoDB vs Redis" \
  --timebox=3h \
  --deliverable=comparison
```

**Focus**: Compare options on performance, DX, ecosystem, integration complexity.

### Performance Spike

```bash
/spike "Can we handle 10k concurrent WebSocket connections?" \
  --timebox=4h \
  --deliverable=poc
```

**Focus**: Build POC, measure performance, identify bottlenecks.

### Integration Spike

```bash
/spike "How to integrate Stripe payment processing?" \
  --timebox=2h \
  --deliverable=report
```

**Focus**: Research API, build minimal integration, estimate effort.

### Risk Assessment Spike

```bash
/spike "What are the risks of migrating from Vue 2 to Vue 3?" \
  --timebox=4h \
  --deliverable=report
```

**Focus**: Identify breaking changes, estimate migration effort, document risks.

---

## Comparison Matrix Template

Use this table format for technology comparisons:

```markdown
## Comparison Matrix

| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Performance | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Developer Experience | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Community/Support | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| License/Cost | Free | Paid | Free |
| Integration | Easy | Moderate | Complex |
| Maturity | Stable | Beta | Experimental |

## Recommendation

**Winner**: Option A

**Rationale**: {explain decision}

**Runner-up**: Option B (use if {condition})
```

---

## POC Code Template

Save POC code to `/tmp/spike-{slug}/README.md`:

```markdown
# Spike POC: {research-question}

> **WARNING**: This is throwaway code for research only. NOT production-ready.

## Purpose

Proof of concept to validate {research-question}

## Setup

{How to run the POC}

## Key Learnings

- {finding 1}
- {finding 2}
- {finding 3}

## Next Steps

If implementing for production:
1. {what needs to change}
2. {what needs to be added}
3. {what needs testing}

## Do NOT Use This Code

This POC has relaxed quality standards:
- No tests
- Hardcoded values
- Quick-and-dirty approaches
- Missing error handling

Create a /task for production implementation.
```
