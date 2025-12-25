# Prompt -1 Template

> **Purpose**: Validate initiative readiness before committing to the full 4-agent workflow. Prompt -1 answers: "Do we know enough to write Prompt 0?"

---

## What Is Prompt -1?

Prompt -1 is the **pre-initialization scoping phase** that occurs before Prompt 0 (Orchestrator Initialization). It serves as a meta-prompt that:

1. **Validates** the initiative is ready for structured execution
2. **Identifies** blockers, dependencies, and open questions
3. **Assesses** complexity to right-size the workflow
4. **Surfaces** risks before resources are committed
5. **Recommends** Go/No-Go with clear rationale

### When to Use Prompt -1

| Situation | Use Prompt -1? | Rationale |
|-----------|----------------|-----------|
| New feature development | Yes | Validate scope, dependencies, complexity |
| Major refactoring | Yes | Assess risk, identify blockers |
| Sprint planning | Yes | Right-size workflow, surface questions |
| Bug fix | Usually No | Unless cross-cutting or high-risk |
| Documentation sprint | Yes | Define deliverables, validate gaps |
| Simple task | No | Over-engineering; proceed directly |

### Prompt -1 → Prompt 0 Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Initiative Lifecycle                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Prompt -1 (Scoping)                                            │
│  ─────────────────                                              │
│  • Validate problem                                             │
│  • Assess complexity                                            │
│  • Identify blockers                                            │
│  • Surface open questions                                       │
│  • Go/No-Go decision                                            │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │  GO / NO-GO  │                                               │
│  └──────────────┘                                               │
│         │                                                        │
│    ┌────┴────┐                                                  │
│    ▼         ▼                                                  │
│  [GO]     [NO-GO]                                               │
│    │         │                                                  │
│    ▼         ▼                                                  │
│  Prompt 0   Resolve blockers, gather context,                   │
│  (Init)    or descope → retry Prompt -1                         │
│    │                                                            │
│    ▼                                                            │
│  Sessions 1-N (Execution)                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Template Structure

### Prompt -1: Initiative Scoping — {INITIATIVE_NAME}

> **Purpose**: Validate readiness for the 4-agent workflow. Answer: "Do we know enough to write Prompt 0?"

---

## Initiative Summary

**One-liner**: {Single sentence describing what this initiative accomplishes}

**Sponsor**: {Owner/requester of this initiative}

**Triggered by**: {What event, feedback, or need triggered this initiative?}

---

## Pre-Flight Checklist

### 1. Problem Validation

| Question | Answer | Confidence |
|----------|--------|------------|
| Is there a real problem? | {Yes/No + evidence} | {High/Medium/Low} |
| Who experiences it? | {Affected users/systems} | {High/Medium/Low} |
| What's the cost of not solving? | {Impact description} | {High/Medium/Low} |
| Is this the right time? | {Yes/No + rationale} | {High/Medium/Low} |

**Problem Statement Draft**:
> {2-3 sentence problem statement that will seed the PRD}

### 2. Scope Boundaries

| Dimension | In Scope | Out of Scope | Decision Rationale |
|-----------|----------|--------------|-------------------|
| {Dimension 1} | {What's included} | {What's excluded} | {Why this boundary} |
| {Dimension 2} | {What's included} | {What's excluded} | {Why this boundary} |
| {Dimension 3} | {What's included} | {What's excluded} | {Why this boundary} |
| {Dimension 4} | {What's included} | {What's excluded} | {Why this boundary} |

### 3. Complexity Assessment

| Factor | Assessment | Notes |
|--------|------------|-------|
| **Scope** | {Script / Module / Service / Platform} | {Justification} |
| **Technical Risk** | {Low / Medium / High} | {Key risk factors} |
| **Integration Points** | {Low / Medium / High} | {What systems touched} |
| **Team Familiarity** | {Low / Medium / High} | {Prior experience} |
| **Unknowns** | {Low / Medium / High} | {What we don't know} |

**Recommended Complexity Level**: {Script / Module / Service / Platform}

**Workflow Recommendation**: {Full 4-agent / Reduced workflow / Direct implementation}

**Rationale**: {Why this workflow is appropriate}

### 4. Dependencies & Blockers

| Dependency | Status | Owner | Blocking? |
|------------|--------|-------|-----------|
| {Dependency 1} | {Done / In Progress / Not Started / Unknown} | {Owner} | {Yes / No} |
| {Dependency 2} | {Done / In Progress / Not Started / Unknown} | {Owner} | {Yes / No} |
| {Dependency 3} | {Done / In Progress / Not Started / Unknown} | {Owner} | {Yes / No} |

**Blockers**: {List any blocking issues or "None identified"}

### 5. Success Definition (Draft)

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| {Metric 1} | {Baseline} | {Goal} | {How measured} |
| {Metric 2} | {Baseline} | {Goal} | {How measured} |
| {Metric 3} | {Baseline} | {Goal} | {How measured} |

### 6. Rough Effort Estimate

| Phase | Effort | Confidence |
|-------|--------|------------|
| Discovery / Requirements | {Time estimate} | {High / Medium / Low} |
| Architecture / Design | {Time estimate} | {High / Medium / Low} |
| Implementation | {Time estimate} | {High / Medium / Low} |
| Validation / QA | {Time estimate} | {High / Medium / Low} |
| **Total** | {Total time} | {Overall confidence} |

### 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| {Risk 1} | {Low / Medium / High} | {Low / Medium / High} | {Mitigation strategy} |
| {Risk 2} | {Low / Medium / High} | {Low / Medium / High} | {Mitigation strategy} |
| {Risk 3} | {Low / Medium / High} | {Low / Medium / High} | {Mitigation strategy} |

---

## Open Questions to Resolve Before Prompt 0

### Must Answer (Blocking)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 1 | {Critical question} | {Options available} | {Your recommendation} | ? |
| 2 | {Critical question} | {Options available} | {Your recommendation} | ? |
| 3 | {Critical question} | {Options available} | {Your recommendation} | ? |

### Should Answer (Informing)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 4 | {Important question} | {Options available} | {Your recommendation} | ? |
| 5 | {Important question} | {Options available} | {Your recommendation} | ? |
| 6 | {Important question} | {Options available} | {Your recommendation} | ? |

### Nice to Answer (Context)

| # | Question | Options | Recommendation | Status |
|---|----------|---------|----------------|--------|
| 7 | {Contextual question} | {Options available} | {Your recommendation} | ? |
| 8 | {Contextual question} | {Options available} | {Your recommendation} | ? |

---

## Spike Recommendations (If Applicable)

Before committing to Prompt 0, consider these targeted investigations:

### Spike 1: {Spike Name} ({Estimated Time})

**Goal**: {What uncertainty does this reduce?}

**Tasks**:
1. {Investigation task}
2. {Investigation task}
3. {Investigation task}

**Output**: {What artifact or knowledge is produced?}

### Spike 2: {Spike Name} ({Estimated Time})

**Goal**: {What uncertainty does this reduce?}

**Tasks**:
1. {Investigation task}
2. {Investigation task}

**Output**: {What artifact or knowledge is produced?}

---

## Go/No-Go Decision

### Criteria for "Go"

- [ ] Problem is validated and worth solving
- [ ] Scope is bounded and achievable
- [ ] No blocking dependencies
- [ ] Complexity level appropriate for chosen workflow
- [ ] Success metrics are measurable
- [ ] Rough effort estimate acceptable
- [ ] High-risk items have mitigation plans

### Recommendation

**{GO / CONDITIONAL GO / NO-GO}** — {Brief recommendation}

**Rationale**:
- {Key point 1}
- {Key point 2}
- {Key point 3}

**Conditions (if CONDITIONAL GO)**:
- {Condition that must be met}
- {Condition that must be met}

---

## Next Steps

1. **{Action 1}** ({Time estimate})
   - {Detail}

2. **{Action 2}** ({Time estimate})
   - {Detail}

3. **{Action 3}** ({Time estimate})
   - {Detail}

---

## Appendix: Quick Reference

### {Reference Section 1}

{Relevant context, diagrams, or reference material}

### {Reference Section 2}

{Relevant context, diagrams, or reference material}

### Related Documentation

| Document | Location | Relevance |
|----------|----------|-----------|
| {Doc 1} | {Path/Link} | {Why relevant} |
| {Doc 2} | {Path/Link} | {Why relevant} |
| {Doc 3} | {Path/Link} | {Why relevant} |

---

*This Prompt -1 {validated/did not validate} that the initiative is ready for the full 4-agent workflow. {Proceed to Prompt 0 / Resolve blockers first}.*

---

# Prompt -1 Quality Criteria

## What Makes a Good Prompt -1?

### Completeness
- [ ] Problem statement is clear and evidence-based
- [ ] Scope boundaries are explicit (in AND out)
- [ ] Complexity is assessed with rationale
- [ ] Dependencies are identified with status
- [ ] Success metrics are measurable
- [ ] Effort estimate exists with confidence level
- [ ] Risks are identified with mitigations
- [ ] Open questions are categorized by priority

### Honesty
- [ ] Unknowns are acknowledged, not hidden
- [ ] Confidence levels are realistic
- [ ] Risks include likelihood AND impact
- [ ] "No-Go" is a valid recommendation when warranted

### Actionability
- [ ] Go/No-Go criteria are checkable
- [ ] Next steps are concrete
- [ ] Open questions have owners implied
- [ ] Spikes (if needed) are scoped and timeboxed

### Efficiency
- [ ] Doesn't over-analyze simple initiatives
- [ ] Doesn't under-analyze risky initiatives
- [ ] Focuses on decisions, not documentation theater
- [ ] Produces just enough to decide Go/No-Go

---

# Common Patterns

## Pattern 1: Clear Go

```
Problem: Validated
Scope: Bounded
Dependencies: None blocking
Complexity: Matches workflow
Risks: Manageable

-> Recommendation: GO
-> Action: Generate Prompt 0
```

## Pattern 2: Conditional Go

```
Problem: Validated
Scope: Bounded
Dependencies: 1 blocking
Complexity: Matches workflow
Risks: One high-risk item

-> Recommendation: CONDITIONAL GO
-> Action: Resolve dependency, spike high-risk item, then Prompt 0
```

## Pattern 3: No-Go (Scope)

```
Problem: Validated
Scope: Unbounded (keeps growing)
Dependencies: Unknown
Complexity: Cannot assess

-> Recommendation: NO-GO
-> Action: Bound scope, return to Prompt -1
```

## Pattern 4: No-Go (Blockers)

```
Problem: Validated
Scope: Bounded
Dependencies: 3 blocking
Complexity: High

-> Recommendation: NO-GO
-> Action: Resolve blockers, reassess, return to Prompt -1
```

## Pattern 5: Descope to Direct Implementation

```
Problem: Validated
Scope: Very small
Dependencies: None
Complexity: Script-level

-> Recommendation: SKIP PROMPT 0
-> Action: Proceed directly with implementation (no orchestrator needed)
```

---

# Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | Better Approach |
|--------------|--------------|-----------------|
| **Rubber-stamp Go** | Skips validation, surprises later | Honest assessment of blockers |
| **Analysis paralysis** | Never reaches Go/No-Go | Timebox scoping, accept uncertainty |
| **Hidden unknowns** | False confidence in estimates | Explicit "Unknown" with spike recommendation |
| **Scope without boundaries** | "Everything" is in scope | Explicit Out of Scope section |
| **Success without metrics** | Can't tell if we succeeded | Measurable targets with baseline |
| **Risks without mitigations** | Worry without action | Every risk has a mitigation strategy |
| **Questions without priority** | All questions seem equal | Must/Should/Nice categorization |

---

# Orchestrator's Role with Prompt -1

The **Orchestrator** uses Prompt -1 as an input artifact, not as something it creates. The typical flow:

1. **User** (or main thread) creates Prompt -1 through conversation
2. **Prompt -1** produces Go/No-Go recommendation
3. **If Go**: User provides Prompt -1 context to Orchestrator alongside Prompt 0
4. **Orchestrator** references Prompt -1 for:
   - Validated problem statement
   - Scope boundaries
   - Known dependencies
   - Risk mitigations
   - Open questions to resolve in Discovery

The Orchestrator should **not re-validate** what Prompt -1 already validated. It should **build on** the scoping work to create an efficient execution plan.
