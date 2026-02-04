---
name: spike-ref
description: "Time-boxed research and exploration. NO production code. Answer: 'Can we do X? How?' Triggers: /spike, research, explore, investigate, feasibility, proof of concept."
---

# /spike - Time-Boxed Research

> **Category**: Development | **Phase**: Research | **Complexity**: Variable

## Purpose

Execute time-boxed research to answer technical questions, explore feasibility, or investigate approaches WITHOUT producing production code.

Spikes are used when you need to answer "Can we do X?" or "What's the best way to do Y?" before committing to a full `/task` workflow.

---

## Usage

```bash
/spike "research-question" [--timebox=DURATION] [--deliverable=TYPE]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `research-question` | Yes | - | What you're trying to learn or validate |
| `--timebox` | No | 2h | Time limit: 30m, 1h, 2h, 4h, 8h |
| `--deliverable` | No | report | report \| poc \| comparison \| decision |

---

## Behavior

### 1. Spike Planning

Define the research scope:

**Prompt user for**:
- **Question to answer**: What are we trying to learn?
- **Success criteria**: What would make this spike successful?
- **Time budget**: How much time to invest?
- **Deliverable type**:
  - `report`: Written findings document
  - `poc`: Proof of concept (throwaway code)
  - `comparison`: Technology/approach comparison
  - `decision`: Recommendation with pros/cons

**Create spike context**:

```yaml
---
spike_id: "spike-20251224-HHMMSS"
created_at: "2025-12-24THH:MM:SSZ"
question: "{research-question}"
timebox: "{duration}"
deliverable_type: "{type}"
status: "in_progress"
findings: []
---
```

### 2. Research Execution

**Invoke appropriate agent(s)** based on research type:

#### For Architecture/Design Questions

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

#### For Implementation Feasibility

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

#### For Technology Comparison

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

### 3. Time-Boxing Enforcement

**Hard stop at timebox limit**:
- Set timer for specified duration
- Agent must stop and summarize findings when time expires
- Incomplete research is acceptable (capture what's unknown)

**Progress checkpoints**:
- 25% timebox: Initial findings
- 50% timebox: Preliminary conclusions
- 75% timebox: Start wrapping up
- 100% timebox: STOP and document

### 4. Spike Report

Every spike produces a report:

**Template**: `/docs/research/SPIKE-{slug}.md`

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

### 5. Spike Completion

Display summary:

```
Spike Complete: {research-question}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time: {actual} / {budget}
Deliverable: {type}

Key Findings:
- {finding 1}
- {finding 2}
- {finding 3}

Recommendation: {recommendation or "More research needed"}

Artifacts:
✓ Spike report: /docs/research/SPIKE-{slug}.md
✓ POC code: /tmp/spike-{slug}/ (throwaway - not for production)

Next steps:
- Review findings
- If approved: Create /task "{implementation}" to build production version
- If needs more research: Create follow-up /spike
```

---

## Workflow

```mermaid
graph TD
    A[/spike invoked] --> B[Define research question]
    B --> C[Set timebox]
    C --> D{Research type?}
    D -->|Architecture| E[Architect researches]
    D -->|Feasibility| F[Engineer researches]
    D -->|Comparison| E
    E --> G[Build POC if needed]
    F --> G
    G --> H{Timebox expired?}
    H -->|No| I[Continue research]
    I --> H
    H -->|Yes| J[Stop and document]
    J --> K[Generate report]
    K --> L[Spike complete]
```

---

## Deliverables

Every spike produces:

1. **Spike report**: Research findings document
2. **POC code** (optional): Throwaway proof of concept
3. **Comparison matrix** (if applicable): Technology comparison
4. **Recommendation** (if applicable): Suggested approach

**NEVER produces**:
- ❌ Production code
- ❌ Production tests
- ❌ PRD (use `/task` instead)
- ❌ TDD (use `/task` instead)

**Why no production code?**
- Spikes are for learning, not building
- Code quality standards relaxed
- Time-boxed → may be incomplete
- Findings inform real `/task` later

---

## Examples

### Example 1: Architecture Spike

```bash
/spike "Can we use GraphQL instead of REST for our API?" --timebox=4h
```

Output:
```
SPIKE MODE: Architecture Research
Question: Can we use GraphQL instead of REST for our API?
Time budget: 4 hours

[Hour 1 - 25% checkpoint]
✓ Researched GraphQL fundamentals
✓ Reviewed existing REST API structure
✓ Initial assessment: Feasible but significant migration

[Hour 2 - 50% checkpoint]
✓ Built minimal GraphQL POC with 2 endpoints
✓ Compared query complexity vs REST
✓ Researched Apollo Server vs graphql-yoga

[Hour 3 - 75% checkpoint]
✓ Performance benchmarks: GraphQL comparable to REST
✓ Identified migration challenges: Authentication, caching
✓ Estimated effort: 3-4 weeks for full migration

[Hour 4 - TIMEBOX COMPLETE]
✓ Documented findings

Spike Complete: Can we use GraphQL instead of REST?

Recommendation: YES, but phased approach recommended
- Phase 1: Add GraphQL alongside REST (2 weeks)
- Phase 2: Migrate clients gradually (2 weeks)
- Phase 3: Deprecate REST (if desired)

Effort estimate: 4-6 weeks total
Risk level: MEDIUM (mature technology, well-supported)

Report: /docs/research/SPIKE-graphql-vs-rest.md
POC: /tmp/spike-graphql/ (throwaway)

Next step: Create /task "Implement GraphQL API (Phase 1)" if approved
```

### Example 2: Feasibility Spike

```bash
/spike "Can we integrate real-time collaboration like Google Docs?" --timebox=2h
```

Output:
```
SPIKE MODE: Feasibility Research
Question: Can we integrate real-time collaboration?
Time budget: 2 hours

[30 min - 25% checkpoint]
✓ Researched collaboration algorithms (OT vs CRDT)
✓ Reviewed libraries: Yjs, automerge, ShareDB

[1h - 50% checkpoint]
✓ Built POC with Yjs (simple text editor)
✓ Tested with 2 concurrent users
✓ Real-time sync working

[1h 30m - 75% checkpoint]
✓ Researched scaling: WebSocket vs WebRTC
✓ Identified backend requirements: Redis for pub/sub
✓ Estimated effort: 2-3 weeks

[2h - TIMEBOX COMPLETE]

Spike Complete: Real-time collaboration feasibility

Recommendation: FEASIBLE with Yjs + Redis

Pros:
- Mature library (Yjs)
- Good browser support
- Scales with Redis

Cons:
- Requires backend infrastructure (Redis)
- WebSocket connection management
- Conflict resolution complexity

Effort estimate: 2-3 weeks
Risk level: MEDIUM-HIGH (new technology for team)

Report: /docs/research/SPIKE-realtime-collaboration.md

Next steps:
- If approved: Create /task "Implement real-time collaboration (MVP)"
- Consider: Additional spike for scaling/performance testing
```

### Example 3: Technology Comparison

```bash
/spike "Compare test frameworks: Jest vs Vitest vs Playwright" --timebox=3h --deliverable=comparison
```

Output:
```
SPIKE MODE: Technology Comparison
Question: Jest vs Vitest vs Playwright
Time budget: 3 hours

[Researching - 1h]
✓ Reviewed documentation for all 3
✓ Checked compatibility with our stack (TypeScript, React)
✓ Researched community adoption

[POC - 1.5h]
✓ Converted 3 existing tests to each framework
✓ Measured performance
✓ Evaluated DX (developer experience)

[Documentation - 30m]
✓ Created comparison matrix

Spike Complete: Test Framework Comparison

Comparison Matrix:
┌─────────────┬──────┬────────┬────────────┐
│ Criteria    │ Jest │ Vitest │ Playwright │
├─────────────┼──────┼────────┼────────────┤
│ Performance │ ⭐⭐  │ ⭐⭐⭐⭐ │ ⭐⭐⭐      │
│ DX          │ ⭐⭐⭐ │ ⭐⭐⭐⭐ │ ⭐⭐⭐      │
│ Ecosystem   │ ⭐⭐⭐⭐│ ⭐⭐⭐  │ ⭐⭐⭐      │
│ E2E support │ ❌   │ ❌     │ ✅         │
└─────────────┴──────┴────────┴────────────┘

Recommendation:
- Unit/Integration: **Vitest** (fast, great DX, Vite-native)
- E2E: **Playwright** (only option for real browser testing)

Migration effort:
- Jest → Vitest: 1-2 days (similar API)
- Adding Playwright: 3-5 days (new E2E suite)

Report: /docs/research/SPIKE-test-framework-comparison.md

Next step: Create /task "Migrate to Vitest" if approved
```

### Example 4: Quick 30-Minute Spike

```bash
/spike "Is there a library for parsing YAML frontmatter?" --timebox=30m
```

Output:
```
SPIKE MODE: Quick Research
Question: Library for parsing YAML frontmatter?
Time budget: 30 minutes

[15 min]
✓ Researched npm packages
✓ Found: gray-matter, front-matter, remark-frontmatter

[15 min]
✓ Tested gray-matter with our use case
✓ Works perfectly, well-maintained

Spike Complete (Quick)

Recommendation: **gray-matter**

Why:
- Most popular (1.3M weekly downloads)
- Supports YAML, TOML, JSON
- Simple API
- Well-maintained

Example:
```javascript
const matter = require('gray-matter');
const file = matter(fileContents);
// file.data = frontmatter object
// file.content = markdown content
```

Effort to integrate: < 1 hour

Report: /docs/research/SPIKE-yaml-frontmatter.md

Next step: Just use it (too simple for /task)
```

---

## When to Use vs Alternatives

| Use /spike when... | Use alternative when... |
|---------------------|-------------------------|
| Need to answer "Can we...?" | Know how, just need to build → Use `/task` |
| Evaluating options | Already chose approach → Use `/task` |
| Feasibility unclear | Requirements unclear → Use `/start` |
| Time-boxed exploration | Open-ended development → Use `/task` or `/sprint` |

### /spike vs /task

- `/spike`: RESEARCH, throwaway code, answer questions
- `/task`: PRODUCTION, real code, build features

### /spike vs /start

- `/spike`: No production deliverable
- `/start`: Begins production session

### When NOT to use /spike

**Don't use /spike if**:
- You already know the answer (just do it)
- You need production code (use `/task`)
- Research is open-ended (time-box or use `/task` with exploratory PRD)

---

## Complexity Level

**VARIABLE** - Complexity depends on research question:

- **Simple spike**: 30m-1h, answer quick question
- **Standard spike**: 2-4h, evaluate options, build POC
- **Deep spike**: 8h, comprehensive research, multiple POCs

**Recommended for**:
- Technology selection
- Feasibility validation
- Performance testing
- Approach exploration
- Risk assessment

**Not recommended for**:
- Building production features (use `/task`)
- Fixing bugs (use `/task` or `/hotfix`)
- Implementing known solutions (use `/task`)

---

## State Changes

### Files Created

| File Type | Location | Always Created? |
|-----------|----------|-----------------|
| Spike report | `/docs/research/SPIKE-{slug}.md` | Yes |
| POC code | `/tmp/spike-{slug}/` | Optional |
| Benchmarks | `/docs/research/benchmarks/` | If applicable |
| Comparison matrix | Embedded in report | If deliverable=comparison |

### No Production Artifacts

Intentionally NOT created:
- ❌ Production code (POC is throwaway)
- ❌ Production tests
- ❌ PRD
- ❌ TDD
- ❌ Deployed artifacts

---

## Prerequisites

- Clear research question
- Defined success criteria
- Realistic timebox

**No session required**: Spikes can run standalone.

---

## Success Criteria

- Research question answered (or documented as unanswerable)
- Findings documented in spike report
- Recommendation provided (if applicable)
- Time budget respected
- Next steps clear

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Question too vague | Can't define success criteria | Clarify question with user |
| Timebox too short | Can't complete research | Document partial findings, recommend follow-up spike |
| Timebox too long | Research taking > 8h | Break into multiple spikes or convert to `/task` |
| Scope creep | Spike turning into implementation | Stop, remind spike is research only |

---

## Related Commands

- `/task` - Implement production version after spike
- `/start` - Begin session (can incorporate spike findings)
- `/sprint` - Multiple tasks (can include spikes)

---

## Related Skills

- [10x-workflow](../10x-workflow/SKILL.md) - Workflow patterns
- [documentation](../documentation/SKILL.md) - Spike report template

---

## Notes

### Time-Boxing Philosophy

**Why time-box spikes?**
- Prevents analysis paralysis
- Forces prioritization of research
- Ensures spikes don't become full tasks
- Clear stopping point

**What if time runs out?**
- Document partial findings
- List open questions
- Recommend follow-up spike or escalate to `/task`

### POC Code Guidelines

**POC code is throwaway**:
- Don't worry about code quality
- Skip tests (unless testing is the research)
- Hardcode values
- Use quick-and-dirty approaches
- **NEVER** commit to production codebase

**Save POC to `/tmp/spike-{slug}/`**:
- Clearly labeled as throwaway
- Can reference in spike report
- Delete after spike complete (optional)

### Spike to Task Handoff

After spike completes:

```bash
# Review spike findings
cat /docs/research/SPIKE-{slug}.md

# If approved for implementation:
/task "Implement {feature} based on spike findings" --complexity=MODULE

# In task PRD, reference spike:
# "See SPIKE-{slug}.md for research findings and POC"
```

### Multi-Phase Spikes

For complex research:

**Phase 1**: Quick spike (30m-1h)
- Answer: "Is this even possible?"

**Phase 2**: Deep spike (4-8h)
- Answer: "How would we do it?"
- Build comprehensive POC

**Phase 3**: Production task
- Build real implementation

Example:
```bash
# Phase 1
/spike "Can we use WebAssembly for image processing?" --timebox=1h

# If Phase 1 says YES:
/spike "How to integrate WebAssembly with our React app?" --timebox=4h

# If Phase 2 looks good:
/task "Implement WebAssembly image processor" --complexity=MODULE
```

### Spike Report Retention

**Keep spike reports**:
- Historical record of decisions
- Reference for future similar questions
- Document what was considered
- Explain why certain paths not taken

**Organize by category**:
- `/docs/research/architecture/`
- `/docs/research/performance/`
- `/docs/research/technology/`
- `/docs/research/feasibility/`

### Collaborative Spikes

For high-stakes decisions:

**Multi-agent spikes**:
```markdown
Act as **Architect** AND **Principal Engineer**.

COLLABORATIVE SPIKE
Question: {complex-question}
Time budget: 4 hours

Architect: Research design implications
Engineer: Research implementation feasibility

Collaborate on recommendation.
```

---

## Quality Over Speed

Unlike `/hotfix`, spikes prioritize **thoroughness within timebox**:

- Research all viable options
- Build POCs to validate assumptions
- Document findings comprehensively
- Provide clear recommendation

**But still time-boxed**:
- Don't pursue perfection
- Accept incomplete research
- Document unknowns
- Recommend follow-up if needed

---

## Spike Templates

Common spike patterns:

### Technology Selection Spike
```bash
/spike "Choose database: PostgreSQL vs MongoDB vs Redis" \
  --timebox=3h \
  --deliverable=comparison
```

### Performance Spike
```bash
/spike "Can we handle 10k concurrent WebSocket connections?" \
  --timebox=4h \
  --deliverable=poc
```

### Integration Spike
```bash
/spike "How to integrate Stripe payment processing?" \
  --timebox=2h \
  --deliverable=report
```

### Risk Assessment Spike
```bash
/spike "What are the risks of migrating from Vue 2 to Vue 3?" \
  --timebox=4h \
  --deliverable=report
```

All follow same pattern: question → research → document → recommend.
