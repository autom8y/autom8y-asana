---
user-invocable: false
---

# /spike Behavior Specification

> Full step-by-step sequence for time-boxed research.

## Behavior Sequence

### 1. Spike Planning

Define the research scope by prompting user for:

**Question to answer**: What are we trying to learn?

**Success criteria**: What would make this spike successful?

**Time budget**: How much time to invest?

**Deliverable type**:
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

Apply Agent Invocation Pattern:
- Agent: Architect (design/architecture) or Principal Engineer (feasibility)
- Mode: "SPIKE MODE (Time-boxed research)"

See [templates.md](templates.md) for full agent invocation templates:
- Architecture/Design Questions
- Implementation Feasibility
- Technology Comparison

### 3. Time-Boxing Enforcement

Apply Time-Boxing Pattern:
- Checkpoints: 25%, 50%, 75%, 100%
- Hard stop at limit
- Incomplete is acceptable

**Progress checkpoints**:
- 25% timebox: Initial findings
- 50% timebox: Preliminary conclusions
- 75% timebox: Start wrapping up
- 100% timebox: STOP and document

### 4. Spike Report Generation

Every spike produces a report at `/docs/research/SPIKE-{slug}.md`.

See [templates.md](templates.md) for full spike report template.

### 5. Completion Summary

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

## Workflow Diagram

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
- Production code (POC is throwaway)
- Production tests
- PRD
- TDD
- Deployed artifacts

---

## Error Cases

| Error | Condition | Resolution |
|-------|-----------|------------|
| Question too vague | Can't define success criteria | Clarify question with user |
| Timebox too short | Can't complete research | Document partial findings, recommend follow-up spike |
| Timebox too long | Research taking > 8h | Break into multiple spikes or convert to `/task` |
| Scope creep | Spike turning into implementation | Stop, remind spike is research only |

---

## Design Notes

### Why No Production Code?

- Spikes are for learning, not building
- Code quality standards relaxed
- Time-boxed → may be incomplete
- Findings inform real `/task` later

### Deliverable Types Explained

| Type | Purpose | Example |
|------|---------|---------|
| `report` | Written findings document | "Can we use GraphQL?" |
| `poc` | Proof of concept (throwaway code) | "How would real-time sync work?" |
| `comparison` | Technology/approach comparison | "Jest vs Vitest vs Playwright" |
| `decision` | Recommendation with pros/cons | "Should we migrate to Vue 3?" |
