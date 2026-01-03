---
name: doc-strategy
description: "Strategy-pack templates for roadmaps, competitive intelligence, market analysis, and financial modeling. Use when: creating strategic roadmaps, analyzing competitors, sizing markets, modeling business economics. Triggers: strategic roadmap, prioritization, OKR, competitive analysis, market sizing, TAM/SAM/SOM, unit economics, financial model, pricing analysis."
---

# Strategy Document Templates

Templates for strategic analysis and planning artifacts from the strategy-pack team.

## Template Index

1. [Strategic Roadmap Template](#strategic-roadmap-template) - STRATEGY-{slug}
2. [Competitive Intel Template](#competitive-intel-template) - COMPETE-{slug}
3. [Market Analysis Template](#market-analysis-template) - MARKET-{slug}
4. [Financial Model Template](#financial-model-template) - FINANCE-{slug}

---

## Strategic Roadmap Template {#strategic-roadmap-template}

```markdown
# STRATEGY-{slug}

## Executive Summary
{Strategic direction in 2-3 sentences}

## Strategic Context

### Vision
{Where we're going}

### Strategic Themes
1. {Theme 1}
2. {Theme 2}
3. {Theme 3}

### Resource Constraints
- Engineering: {X FTEs}
- Budget: ${X}M
- Timeline: {X quarters}

## Initiative Assessment

### Initiatives Under Consideration
| Initiative | Strategic Theme | Owner |
|------------|-----------------|-------|
| {initiative} | {theme} | {team} |

### Evaluation Criteria
| Criterion | Weight | Description |
|-----------|--------|-------------|
| Strategic Fit | {X}% | {How it aligns with strategy} |
| ROI | {X}% | {Financial return} |
| Feasibility | {X}% | {Can we execute} |
| Risk | {X}% | {What could go wrong} |

### Scoring Matrix
| Initiative | Strategic Fit | ROI | Feasibility | Risk | Total |
|------------|--------------|-----|-------------|------|-------|
| {init} | {1-5} | {1-5} | {1-5} | {1-5} | {weighted} |

## Prioritization

### Tier 1: Must Do
| Initiative | Rationale | Resources |
|------------|-----------|-----------|
| {initiative} | {why tier 1} | {allocation} |

### Tier 2: Should Do
| Initiative | Rationale | Resources |
|------------|-----------|-----------|
| {initiative} | {why tier 2} | {allocation} |

### Tier 3: Could Do
| Initiative | Rationale | Condition |
|------------|-----------|-----------|
| {initiative} | {why tier 3} | {when we'd do it} |

### Not Doing
| Initiative | Rationale |
|------------|-----------|
| {initiative} | {why not} |

## Resource Allocation

### By Initiative
| Initiative | Eng FTEs | Budget | Timeline |
|------------|----------|--------|----------|
| {init} | {X} | ${X}K | {Q} |

### By Team
| Team | Q1 | Q2 | Q3 | Q4 |
|------|----|----|----|----|
| {team} | {focus} | {focus} | {focus} | {focus} |

## Roadmap

### Timeline View
```
Q1: {Focus and milestones}
Q2: {Focus and milestones}
Q3: {Focus and milestones}
Q4: {Focus and milestones}
```

### Dependencies
{Initiative A} blocks {Initiative B}

### Milestones
| Date | Milestone | Owner |
|------|-----------|-------|
| {date} | {milestone} | {owner} |

## OKRs

### Objective 1: {Objective}
- KR1: {Measurable key result}
- KR2: {Measurable key result}
- KR3: {Measurable key result}

### Objective 2: {Objective}
...

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| {risk} | {H/M/L} | {H/M/L} | {strategy} |

## Decision Points
| Decision | Timing | Trigger |
|----------|--------|---------|
| {decision} | {when} | {what prompts it} |

## Success Metrics
| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| {metric} | {baseline} | {goal} | {when} |

## Appendix
- Detailed initiative descriptions
- Full scoring rationale
- Alternative scenarios considered
```

---

## Competitive Intel Template {#competitive-intel-template}

```markdown
# COMPETE-{slug}

## Executive Summary
{Key competitive insight in 2-3 sentences}

## Competitor Landscape

### Market Map
| Competitor | Segment | Position | Threat Level |
|------------|---------|----------|--------------|
| {name} | {segment} | {leader/challenger/niche} | {High/Medium/Low} |

## Competitor Profiles

### {Competitor 1}
- **Founded**: {year}
- **Funding**: {amount, stage}
- **Size**: {employees, revenue if known}
- **Target Market**: {who they sell to}

#### Product Analysis
| Capability | Them | Us | Advantage |
|------------|------|-------|-----------|
| {capability} | {rating} | {rating} | {Them/Us/Tie} |

#### Pricing
{Pricing model and tiers}

#### Recent Moves
- {Date}: {What they did}
- {Date}: {What they did}

#### Likely Next Moves
1. {Predicted move}: {Reasoning}
2. {Predicted move}: {Reasoning}

#### Our Vulnerabilities
- {Where they beat us}

#### Our Advantages
- {Where we beat them}

### {Competitor 2}
...

## Competitive Dynamics

### Industry Trends Affecting Competition
- {Trend 1}: {Impact on competitive landscape}
- {Trend 2}: {Impact}

### Competitive Threats
| Threat | Likelihood | Impact | Response |
|--------|------------|--------|----------|
| {threat} | {H/M/L} | {H/M/L} | {strategy} |

### Competitive Opportunities
| Opportunity | Timeline | Effort | Impact |
|-------------|----------|--------|--------|
| {opportunity} | {when} | {H/M/L} | {H/M/L} |

## Strategic Recommendations
1. {Recommendation with rationale}
2. {Recommendation}

## Monitoring Plan
| Competitor | Signals to Watch | Frequency |
|------------|------------------|-----------|
| {name} | {what to track} | {daily/weekly/monthly} |

## Sources
- {Source 1}
- {Source 2}
```

---

## Market Analysis Template {#market-analysis-template}

```markdown
# MARKET-{slug}

## Executive Summary
{One paragraph overview of market opportunity}

## Market Definition
- **Category**: {What market we're analyzing}
- **Geographic Scope**: {Regions included}
- **Time Horizon**: {Current state and projection period}

## Market Size

### TAM (Total Addressable Market)
- **Size**: ${X}B
- **Methodology**: {How calculated}
- **Sources**: {Data sources used}

### SAM (Serviceable Addressable Market)
- **Size**: ${X}M
- **Constraints**: {Why smaller than TAM}

### SOM (Serviceable Obtainable Market)
- **Size**: ${X}M
- **Assumptions**: {Market share assumptions}

## Market Segments

### Segment 1: {Name}
- **Size**: ${X}M ({X}% of TAM)
- **Growth Rate**: {X}% CAGR
- **Characteristics**: {Key attributes}
- **Buyer Persona**: {Who buys}
- **Buying Criteria**: {What they prioritize}

### Segment 2: {Name}
...

## Market Dynamics

### Growth Drivers
- {Driver 1}
- {Driver 2}

### Headwinds
- {Headwind 1}
- {Headwind 2}

### Secular Trends
- {Trend 1}: {Impact assessment}
- {Trend 2}: {Impact assessment}

## Adjacent Markets
{Opportunities for expansion}

## Recommendations
1. {Strategic implication 1}
2. {Strategic implication 2}

## Data Sources
- {Source 1}
- {Source 2}
```

---

## Financial Model Template {#financial-model-template}

```markdown
# FINANCE-{slug}

## Executive Summary
{Key financial insight in 2-3 sentences}

## Strategic Question
{What decision this model informs}

## Current State

### Revenue Structure
| Revenue Stream | Annual Revenue | % of Total | Trend |
|---------------|----------------|------------|-------|
| {stream} | ${X}M | {X}% | {↑/↓/→} |

### Cost Structure
| Cost Category | Annual Cost | % of Revenue | Type |
|--------------|-------------|--------------|------|
| {category} | ${X}M | {X}% | {Fixed/Variable} |

### Unit Economics
| Metric | Current Value | Benchmark | Status |
|--------|--------------|-----------|--------|
| CAC | ${X} | ${Y} | {Good/Concern} |
| LTV | ${X} | ${Y} | |
| LTV:CAC | {X}:1 | >3:1 | |
| Payback (months) | {X} | <12 | |
| Gross Margin | {X}% | {Y}% | |

## Scenarios

### Base Case
{Description and assumptions}

### Bull Case
{Description and assumptions}

### Bear Case
{Description and assumptions}

## Projections

### Revenue Projections
| Year | Base | Bull | Bear |
|------|------|------|------|
| Y1 | ${X}M | ${X}M | ${X}M |
| Y2 | ${X}M | ${X}M | ${X}M |
| Y3 | ${X}M | ${X}M | ${X}M |

### Margin Projections
| Year | Base | Bull | Bear |
|------|------|------|------|
| Y1 | {X}% | {X}% | {X}% |

### Unit Economics Impact
| Metric | Before | After (Base) | Change |
|--------|--------|--------------|--------|
| {metric} | {value} | {value} | {delta} |

## Sensitivity Analysis

### Key Variables
| Variable | Range Tested | Impact on Revenue |
|----------|--------------|-------------------|
| {variable} | {low} to {high} | {sensitivity} |

### Breakeven Analysis
{What needs to be true for this to work}

## Risks and Opportunities

### Financial Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| {risk} | {H/M/L} | ${X}M | {strategy} |

### Upside Opportunities
| Opportunity | Probability | Impact |
|-------------|-------------|--------|
| {opportunity} | {H/M/L} | ${X}M |

## Recommendations
1. {Recommendation with financial rationale}
2. {Recommendation}

## Key Assumptions
- {Assumption 1}: {Rationale}
- {Assumption 2}: {Rationale}

## Data Sources
- {Source 1}
- {Source 2}

## Model Details
{Link to spreadsheet or model files}
```

---

## Related Resources

See the `documentation` skill hub for additional template categories:
- Development artifacts (PRD, TDD, ADR, Test Plans)
- Team formation (TEAM-SPEC templates)
- Other strategic artifacts
