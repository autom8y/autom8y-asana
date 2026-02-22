---
user-invocable: false
---

# Question Patterns

> Templates for structured interview questions by category.

## Constraint Discovery

Questions that surface hard limits early.

```yaml
pattern: "constraint_probe"
phase: UNDERSTAND
example:
  question: "What's the deployment target?"
  options:
    - label: "Single server"
      description: "Simplest ops, vertical scaling only"
    - label: "Container orchestration"
      description: "K8s/ECS, horizontal scaling, more infra complexity"
    - label: "Serverless"
      description: "Zero idle cost, cold start latency, vendor lock-in"
    - label: "Edge/CDN"
      description: "Low latency globally, limited compute model"
signals:
  - User mentions "budget" or "timeline"
  - User mentions existing infrastructure
  - Compliance or regulatory context detected
```

## Tradeoff Navigation

Questions that make implicit tradeoffs explicit.

```yaml
pattern: "tradeoff_fork"
phase: DESIGN
example:
  question: "How should we handle consistency vs. availability for this data?"
  options:
    - label: "Strong consistency"
      description: "Every read sees the latest write. Higher latency, simpler mental model."
    - label: "Eventual consistency"
      description: "Reads may lag. Lower latency, requires conflict resolution strategy."
    - label: "Tunable per-operation"
      description: "Caller decides per request. Most flexible, most complex API surface."
signals:
  - Multiple valid architectures exist
  - User hasn't mentioned a preference
  - Performance vs. correctness tension detected
```

## Failure Mode Probing

Questions the user hasn't thought to ask themselves.

```yaml
pattern: "failure_probe"
phase: DESIGN
example:
  question: "What happens when the upstream dependency is unavailable?"
  options:
    - label: "Fail fast"
      description: "Return error immediately. Simple, honest, but user sees failures."
    - label: "Degrade gracefully"
      description: "Serve stale/cached data. Better UX, risk of stale reads."
    - label: "Queue and retry"
      description: "Accept the request, process when available. Best UX, most complex."
signals:
  - External service integration
  - Network boundary crossing
  - Data pipeline with multiple stages
```

## Scope Boundary

Questions that prevent scope creep by making exclusions explicit.

```yaml
pattern: "scope_boundary"
phase: UNDERSTAND
example:
  question: "Should this handle multi-tenancy?"
  options:
    - label: "Yes, from day one"
      description: "Tenant isolation in data model, auth, and config. Higher upfront cost."
    - label: "Not now, but design for it"
      description: "Single tenant, but avoid patterns that make multi-tenancy hard later."
    - label: "No, single tenant only"
      description: "Simplest path. Accept that adding tenancy later may require significant rework."
signals:
  - Feature could plausibly serve multiple users/orgs
  - User hasn't mentioned scale expectations
  - Data isolation is architecturally significant
```

## Edge Case Surfacing

Questions that probe boundaries of stated requirements.

```yaml
pattern: "edge_case"
phase: DESIGN
example:
  question: "What's the expected payload size range?"
  options:
    - label: "Small (< 1MB)"
      description: "Standard HTTP, in-memory processing, no streaming needed"
    - label: "Medium (1-100MB)"
      description: "May need chunked upload, streaming processing, progress tracking"
    - label: "Large (100MB+)"
      description: "Requires multipart upload, background processing, resumable transfers"
signals:
  - User describes input/output but not volume
  - API design decisions depend on data size
  - Performance characteristics change with scale
```

## Confirmation Synthesis

Questions that verify understanding before committing to the spec.

```yaml
pattern: "confirmation"
phase: REVIEW
example:
  question: "Here's what I understand — does this match your intent?"
  options:
    - label: "Yes, that's right"
      description: "Proceed to writing the spec"
    - label: "Mostly, but..."
      description: "I'll note what needs adjusting"
    - label: "No, let me clarify"
      description: "We need to revisit some decisions"
signals:
  - All design phases complete
  - Ready to transition to artifact production
  - Major decisions are made
```
