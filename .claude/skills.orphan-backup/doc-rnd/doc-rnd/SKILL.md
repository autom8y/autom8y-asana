---
name: doc-rnd
description: "R&D-pack templates for technology assessment, integration research, prototyping, and moonshot planning. Use when: evaluating new technologies, mapping integration requirements, documenting prototypes, planning long-term architecture. Triggers: tech assessment, technology scout, integration map, prototype documentation, moonshot plan, future architecture, migration path."
---

# R&D Documentation Templates

Templates for research and development workflow artifacts from the rnd-pack team.

## Template Index

- [Tech Assessment Template](#tech-assessment-template) - Technology evaluation and recommendation (SCOUT-{slug})
- [Integration Map Template](#integration-map-template) - Integration analysis and effort estimation (INTEGRATE-{slug})
- [Prototype Documentation Template](#prototype-documentation-template) - Prototype results and learnings (PROTO-{slug})
- [Moonshot Plan Template](#moonshot-plan-template) - Long-term architectural vision (MOONSHOT-{slug})

---

## Tech Assessment Template {#tech-assessment-template}

```markdown
# SCOUT-{slug}

## Executive Summary
{One paragraph: what it is, verdict, and key insight}

## Technology Overview
- **Category**: {Database, Framework, Protocol, Tool, etc.}
- **Maturity**: {Experimental, Early Adopter, Mainstream, Declining}
- **License**: {MIT, Apache, Commercial, etc.}
- **Backing**: {Company, Foundation, Community}

## Capabilities
{What it does well}

## Limitations
{What it doesn't do or does poorly}

## Ecosystem Assessment
- **Community**: {Size, activity, responsiveness}
- **Documentation**: {Quality, completeness}
- **Tooling**: {IDE support, debugging, monitoring}
- **Adoption**: {Who's using it, at what scale}

## Risk Analysis
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {risk} | {H/M/L} | {H/M/L} | {strategy} |

## Fit Assessment
- **Philosophy Alignment**: {How well it fits our approach}
- **Stack Compatibility**: {Integration complexity}
- **Team Readiness**: {Learning curve, existing expertise}

## Recommendation
**Verdict**: {Adopt / Trial / Assess / Hold / Avoid}

**Rationale**: {Why this verdict}

**Next Steps**:
1. {If proceeding, what's next}

## Comparison Matrix
| Criteria | This Tech | Alternative 1 | Alternative 2 |
|----------|-----------|---------------|---------------|
| {criterion} | {rating} | {rating} | {rating} |
```

---

## Integration Map Template {#integration-map-template}

```markdown
# INTEGRATE-{slug}

## Overview
{What we're integrating and why}

## Current State

### Architecture
{Description or diagram of current system}

### Integration Points
| System | Interface | Data | Frequency |
|--------|-----------|------|-----------|
| {system} | {REST/gRPC/etc.} | {what flows} | {calls/day} |

### Dependencies
- {Dependency 1}: {How it's used}
- {Dependency 2}: {How it's used}

## Target State

### New Architecture
{Description or diagram of target system}

### New Integration Points
| System | Interface | Data | Changes |
|--------|-----------|------|---------|
| {system} | {new interface} | {what flows} | {what changes} |

## Gap Analysis

### API Compatibility
| Feature | Current | New | Compatibility | Notes |
|---------|---------|-----|---------------|-------|
| {feature} | {current API} | {new API} | {Full/Partial/None} | {details} |

### Breaking Changes
1. {Breaking change 1}: {Impact and mitigation}
2. {Breaking change 2}: {Impact and mitigation}

### Hidden Dependencies
| Dependency | Impact | Discovery |
|------------|--------|-----------|
| {dep} | {what breaks} | {how we found it} |

## Effort Estimate

| Component | Effort | Confidence | Notes |
|-----------|--------|------------|-------|
| {component} | {days/weeks} | {High/Medium/Low} | {assumptions} |

**Total Estimated Effort**: {X} person-weeks

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {risk} | {H/M/L} | {H/M/L} | {strategy} |

## Integration Approach

### Option A: {Approach Name}
- **Pros**: {benefits}
- **Cons**: {drawbacks}
- **Effort**: {estimate}

### Option B: {Approach Name}
...

### Recommendation
{Which approach and why}

## Migration Plan
1. **Phase 1**: {What and duration}
2. **Phase 2**: {What and duration}
3. **Phase 3**: {What and duration}

## Success Criteria
- [ ] {Criterion 1}
- [ ] {Criterion 2}
```

---

## Prototype Documentation Template {#prototype-documentation-template}

```markdown
# PROTO-{slug}

## Executive Summary
{What was built and what it proves in 2-3 sentences}

## Decision Enabled
{What decision can now be made with this prototype}

## Prototype Scope

### What It Does
- {Capability 1}
- {Capability 2}

### What It Doesn't Do
- {Limitation 1}
- {Limitation 2}

### Deliberate Shortcuts
| Shortcut | Production Alternative |
|----------|----------------------|
| {hardcoded thing} | {what it should be} |
| {simulated thing} | {real implementation} |

## Technical Approach

### Architecture
{Diagram or description}

### Key Technologies
- {Tech 1}: {Why chosen}
- {Tech 2}: {Why chosen}

### Integration Points
- {How it connects to our systems}

## Results

### What Worked
- {Success 1}
- {Success 2}

### What Didn't Work
- {Failure 1}: {Why and implications}
- {Failure 2}: {Why and implications}

### Performance
| Metric | Result | Target | Notes |
|--------|--------|--------|-------|
| {metric} | {value} | {goal} | {context} |

### Discovered Constraints
- {Constraint 1}: {Impact on production}
- {Constraint 2}: {Impact}

## Feasibility Assessment

### Verdict
{Feasible / Feasible with caveats / Not feasible}

### Confidence
{High / Medium / Low}

### Key Risks for Production
1. {Risk 1}
2. {Risk 2}

## Production Path

### Required Changes
| Prototype | Production |
|-----------|------------|
| {what we did} | {what we'd need} |

### Effort Estimate
{Rough estimate for production implementation}

### Recommended Next Steps
1. {Step 1}
2. {Step 2}

## Demo Guide

### Prerequisites
{What needs to be set up}

### Demo Script
1. {Step 1: Show X}
2. {Step 2: Demonstrate Y}
3. {Step 3: Highlight Z}

### FAQ
- Q: {Common question}
- A: {Answer}

## Repository
{Link to prototype code}

## Appendix
- Setup instructions
- Known issues
- Future ideas
```

---

## Moonshot Plan Template {#moonshot-plan-template}

```markdown
# MOONSHOT-{slug}

## Executive Summary
{The future we're planning for and why it matters}

## Time Horizon
{X} years

## Scenario Definition

### Scenario: {Name}
**Probability**: {High/Medium/Low}
**Impact if True**: {Critical/High/Medium}

**Assumptions**:
- {Key assumption 1}
- {Key assumption 2}

**Triggers/Signals**:
- {Signal that this scenario is materializing}
- {Another signal}

## Current State

### Architecture Overview
{Diagram or description of current system}

### Key Constraints
- {Constraint 1}
- {Constraint 2}

### Technical Debt Affecting Future
- {Debt item and impact}
- {Debt item and impact}

## Future Architecture

### Vision
{What the system looks like in this future}

### Architecture Diagram
{Visual representation}

### Key Changes

| Area | Current | Future | Rationale |
|------|---------|--------|-----------|
| {area} | {now} | {then} | {why} |

### New Capabilities Required
1. {Capability 1}: {Why needed}
2. {Capability 2}: {Why needed}

### Technology Dependencies
| Technology | Purpose | Maturity | Risk |
|------------|---------|----------|------|
| {tech} | {purpose} | {stage} | {risk} |

### Scaling Implications
{How architecture handles 10x, 100x scale}

## Migration Path

### Phase 1: {Name} ({timeframe})
**Goal**: {What this phase achieves}
**Deliverables**:
- {Deliverable 1}
- {Deliverable 2}
**Investment**: {Rough estimate}
**Reversibility**: {Can we undo this?}

### Phase 2: {Name} ({timeframe})
...

### Decision Points
| Decision | When | Options | Implications |
|----------|------|---------|--------------|
| {decision} | {trigger} | {A/B/C} | {what changes} |

## Risk Analysis

### Scenario Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| {risk} | {H/M/L} | {H/M/L} | {strategy} |

### Execution Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| {risk} | {H/M/L} | {H/M/L} | {strategy} |

## Investment Summary

| Phase | Duration | Team Size | Key Investments |
|-------|----------|-----------|-----------------|
| {phase} | {months} | {FTEs} | {major items} |

**Total Estimated Investment**: {range}

## Strategic Implications
{How this connects to business strategy}

## Recommendations

### Immediate Actions
1. {What to do now}
2. {What to do now}

### Decisions Needed
1. {Decision required}: {By when}
2. {Decision required}: {By when}

### What to Watch
1. {Signal to monitor}
2. {Signal to monitor}

## Open Questions
- {Question 1}
- {Question 2}
```

---

## Related Resources

For comprehensive guidance on all documentation types, see the `documentation` hub skill which links to:
- `doc-artifacts` - Core development templates (PRD, TDD, ADR, Test)
- `doc-reviews` - Review and critique templates
- `doc-sre` - SRE and operations templates
- `doc-ecosystem` - Build and ecosystem templates
- `doc-rnd` - This skill (R&D templates)
