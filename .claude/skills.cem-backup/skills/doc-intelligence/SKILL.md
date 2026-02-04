---
name: doc-intelligence
description: "Intelligence-pack templates for user research, experimentation, and insights synthesis. Use when: conducting user research, designing experiments, synthesizing product insights. Triggers: research findings, user interview, usability test, experiment design, A/B test, sample size, insights report, product analytics."
---

# Intelligence Templates

Templates for the intelligence-pack workflow artifacts.

## Template Index

- [Research Findings Template](#research-findings-template) - User research synthesis (RESEARCH-{slug})
- [Experiment Design Template](#experiment-design-template) - A/B test specifications (EXPERIMENT-{slug})
- [Insights Report Template](#insights-report-template) - Data-driven recommendations (INSIGHT-{slug})

## Research Findings Template {#research-findings-template}

```markdown
# RESEARCH-{slug}

## Executive Summary
{Key findings in 2-3 sentences}

## Research Questions
1. {Question this research answers}
2. {Additional question}

## Methodology
- **Method**: {Interviews, Usability Testing, Survey, etc.}
- **Participants**: {N participants, criteria}
- **Duration**: {Session length, study duration}

## Participant Profile
| ID | Segment | Key Characteristics |
|----|---------|---------------------|
| P1 | {segment} | {relevant attributes} |

## Key Findings

### Finding 1: {Headline}
**Confidence**: {High/Medium/Low}

**Evidence**:
> "{Direct quote from participant}" - P3

> "{Another quote}" - P7

**Observation**: {What we saw/heard}

**Implication**: {What this means for product}

### Finding 2: {Headline}
...

## Themes
| Theme | Frequency | Sentiment | Evidence |
|-------|-----------|-----------|----------|
| {theme} | {X/N participants} | {Positive/Negative/Mixed} | {summary} |

## Connection to Quantitative Data
{How these findings explain or contextualize analytics}

## Recommendations
1. {Actionable recommendation}
2. {Another recommendation}

## Open Questions
{What we still don't know}

## Appendix
- Interview guide
- Session recordings (links)
- Raw notes
```

---

## Experiment Design Template {#experiment-design-template}

```markdown
# EXPERIMENT-{slug}

## Executive Summary
{What we're testing and why in 2-3 sentences}

## Hypothesis

### Belief
{The intuition or assumption we're testing}

### Null Hypothesis (H0)
{What we assume is true if treatment has no effect}

### Alternative Hypothesis (H1)
{What we expect if treatment works}

### Expected Effect Size
{Minimum detectable effect we care about}

## Experiment Design

### Type
{A/B test, multivariate, bandit, etc.}

### Variants
| Variant | Description | Traffic |
|---------|-------------|---------|
| Control | {Current experience} | {50%} |
| Treatment | {New experience} | {50%} |

### Randomization
- **Unit**: {User, session, device, etc.}
- **Stratification**: {Any stratification variables}

### Sample Size
- **MDE**: {X%} change in primary metric
- **Power**: {80/90}%
- **Significance**: {α = 0.05}
- **Required N per variant**: {calculated sample size}

### Duration
- **Minimum**: {X days based on sample size}
- **Recommended**: {X days including weekly cycles}
- **Maximum**: {X days before novelty effects concern}

## Metrics

### Primary Metric
- **Metric**: {Conversion rate, revenue, etc.}
- **Baseline**: {Current value}
- **Target**: {Expected improvement}
- **Success Threshold**: {Minimum to ship}

### Secondary Metrics
| Metric | Baseline | Expected Direction |
|--------|----------|-------------------|
| {metric} | {value} | {↑/↓/→} |

### Guardrail Metrics
| Metric | Threshold | Action if Crossed |
|--------|-----------|-------------------|
| {metric} | {limit} | {stop/investigate} |

## Segments
{Key segments to analyze}
- {Segment 1}
- {Segment 2}

## Risks and Mitigations
| Risk | Mitigation |
|------|------------|
| {risk} | {mitigation} |

## Early Stopping Rules
- Stop for harm: {conditions}
- Stop for success: {conditions}
- Continue regardless: {conditions}

## Pre-Registration
This document serves as pre-registration. Analysis will follow this plan.

## Timeline
- **Design Complete**: {date}
- **Launch**: {date}
- **Minimum Run Time**: {date}
- **Analysis**: {date}

## Success Criteria
{When do we ship the treatment?}

## Post-Experiment
- [ ] Results document
- [ ] Decision recorded
- [ ] Learnings documented
```

---

## Insights Report Template {#insights-report-template}

```markdown
# INSIGHT-{slug}

## Executive Summary
{2-3 sentence summary: what we learned and what to do}

## Decision Recommendation
**Recommendation**: {Ship / Don't Ship / Iterate / More Testing}
**Confidence**: {High / Medium / Low}

## Background
{Context for this analysis}

## Key Findings

### Finding 1: {Headline}
**Impact**: {High/Medium/Low}
**Confidence**: {High/Medium/Low}

{Detailed explanation with data}

| Metric | Control | Treatment | Change | Significance |
|--------|---------|-----------|--------|--------------|
| {metric} | {value} | {value} | {+/-X%} | {p-value} |

**Interpretation**: {What this means}

### Finding 2: {Headline}
...

## Segment Analysis

### {Segment 1}
| Metric | Effect | vs Overall |
|--------|--------|------------|
| {metric} | {+/-X%} | {better/worse/same} |

**Interpretation**: {Why this segment differs}

### {Segment 2}
...

## Supporting Evidence

### Quantitative
{Data points supporting conclusions}

### Qualitative
{User research supporting conclusions}

## Alternative Explanations
{Hypotheses we considered and ruled out}

## Limitations
- {Limitation 1}
- {Limitation 2}

## Recommendations

### Primary Recommendation
{What to do, with rationale}

### If We Ship
1. {Follow-up action}
2. {Monitoring plan}

### If We Don't Ship
1. {Alternative approach}
2. {What to test next}

## Open Questions
{What we still don't know}

## Appendix
- Raw data
- Methodology details
- Statistical analysis
```

---

## Related Resources

See `@documentation` hub for other template collections:
- `@doc-artifacts` - PRD, TDD, ADR, Test templates
- `@doc-sre` - Runbook, incident, postmortem templates
