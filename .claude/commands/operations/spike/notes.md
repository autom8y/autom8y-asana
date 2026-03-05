---
user-invocable: false
---

# /spike Design Notes

> Philosophy and guidelines for effective spikes.

## Time-Boxing Philosophy

### Why Time-Box Spikes?

- **Prevents analysis paralysis**: Forces prioritization of research
- **Ensures spikes don't become full tasks**: Clear stopping point
- **Focuses on high-value questions**: Limited time means prioritizing
- **Enables iterative research**: Can always do follow-up spikes

### What If Time Runs Out?

**Document partial findings**:
- List what was learned so far
- Document open questions
- Provide preliminary assessment

**Recommend next steps**:
- Follow-up spike needed? (with specific focus)
- Escalate to `/task`? (if ready for implementation)
- Need stakeholder decision?

**Acceptable outcomes**:
- Partial answer is better than no answer
- "We need more research" is a valid finding
- Unknowns are documented, not ignored

---

## POC Code Guidelines

### POC Code is Throwaway

**Don't worry about**:
- Code quality standards
- Comprehensive tests
- Production-ready error handling
- Documentation
- Performance optimization

**Do prioritize**:
- Proving/disproving hypothesis
- Learning how technology works
- Validating feasibility
- Measuring key metrics

### Saving POC Code

**Save to `/tmp/spike-{slug}/`**:
- Clearly labeled as throwaway
- Can reference in spike report
- Helps future developers
- Delete after spike (optional)

**Never commit POC to production**:
- Quality standards relaxed
- May have security issues
- Likely incomplete
- Use findings to inform `/task` instead

---

## Spike to Task Handoff

### After Spike Completes

**Review spike findings**:
```bash
cat /docs/research/SPIKE-{slug}.md
```

**If approved for implementation**:
```bash
/task "Implement {feature} based on spike findings" --complexity=MODULE
```

**In task PRD, reference spike**:
```markdown
## Background

See SPIKE-{slug}.md for research findings and POC.

Key findings:
- {finding 1}
- {finding 2}

Recommended approach: {approach from spike}
```

### What Changes from Spike to Task

| Aspect | Spike | Task |
|--------|-------|------|
| Code quality | Relaxed | Production standards |
| Tests | Optional | Required |
| Error handling | Minimal | Comprehensive |
| Documentation | Spike report | Code comments, docs |
| Performance | Quick checks | Optimized |
| Security | Basic validation | Full audit |

---

## Multi-Phase Spikes

### When to Break into Phases

- Complex research taking > 8h
- Multiple distinct questions
- Sequential dependencies (answer A before B)
- Uncertain scope (start small, expand if needed)

### Phased Approach

**Phase 1: Quick spike (30m-1h)**
- Answer: "Is this even possible?"
- Outcome: YES/NO + rough effort

**Phase 2: Deep spike (4-8h)**
- Answer: "How would we do it?"
- Build comprehensive POC
- Outcome: Detailed approach + effort estimate

**Phase 3: Production task**
- Build real implementation
- Use findings from Phase 1 & 2

### Example

```bash
# Phase 1: Feasibility
/spike "Can we use WebAssembly for image processing?" --timebox=1h

# If Phase 1 says YES:
/spike "How to integrate WebAssembly with our React app?" --timebox=4h

# If Phase 2 looks good:
/task "Implement WebAssembly image processor" --complexity=MODULE
```

---

## Spike Report Retention

### Keep Spike Reports

**Why retain**:
- Historical record of decisions
- Reference for future similar questions
- Document what was considered
- Explain why certain paths not taken
- Prevent re-researching same questions

### Organization by Category

```
/docs/research/
  architecture/
    SPIKE-graphql-vs-rest.md
    SPIKE-microservices-feasibility.md
  performance/
    SPIKE-websocket-scaling.md
    SPIKE-database-benchmarks.md
  technology/
    SPIKE-test-framework-comparison.md
    SPIKE-state-management-libraries.md
  feasibility/
    SPIKE-realtime-collaboration.md
    SPIKE-webassembly-integration.md
```

---

## Collaborative Spikes

### When to Use Multiple Agents

**High-stakes decisions**:
- Architecture changes affecting multiple systems
- Technology migrations
- Complex integrations

**Complementary expertise**:
- Architect: Design implications
- Engineer: Implementation feasibility

### Multi-Agent Template

```markdown
Act as **Architect** AND **Principal Engineer**.

COLLABORATIVE SPIKE
Question: {complex-question}
Time budget: 4 hours

Architect: Research design implications
- Architecture patterns
- Integration points
- Long-term maintainability

Engineer: Research implementation feasibility
- Technical constraints
- Effort estimation
- Risk assessment

Collaborate on recommendation.
```

---

## Quality vs Speed

### Spikes Prioritize Thoroughness (Within Timebox)

Unlike `/hotfix`, spikes focus on **complete research**:
- Research all viable options
- Build POCs to validate assumptions
- Document findings comprehensively
- Provide clear recommendation

### But Still Time-Boxed

**Don't pursue perfection**:
- Accept incomplete research
- Document unknowns
- Recommend follow-up if needed
- Stop at timebox regardless

**Balance**:
- Thorough enough to make informed decision
- Fast enough to respect timebox
- Honest about limitations and unknowns

---

## Common Spike Patterns

### Technology Selection

**Question**: "Which library/framework should we use?"

**Research**:
- Compare 2-4 options
- Build minimal POC for each
- Evaluate on key criteria
- Make recommendation

**Deliverable**: Comparison matrix

### Performance Validation

**Question**: "Can we handle {scale}?"

**Research**:
- Build representative POC
- Run benchmarks
- Identify bottlenecks
- Estimate capacity

**Deliverable**: Performance report

### Integration Research

**Question**: "How do we integrate {service}?"

**Research**:
- Review API documentation
- Build minimal integration
- Test key workflows
- Estimate effort

**Deliverable**: Integration report

### Risk Assessment

**Question**: "What are risks of {change}?"

**Research**:
- Identify breaking changes
- Estimate migration effort
- Document risks
- Plan mitigation

**Deliverable**: Risk report
