# Complete Workflow: Exploratory Spike

> Minimal process for exploring technical options before committing

---

## Context

Exploring whether to use GraphQL instead of REST for a new feature.

## Session (Spike Mode)

**Prompt:**
```
This is exploratory—skip full workflow.

I want to explore: GraphQL vs REST for our analytics queries

Build two quick prototypes:
1. REST endpoint: GET /analytics/dashboard?date_from=X&date_to=Y
2. GraphQL query: dashboard(dateFrom, dateTo) { metrics { ... } }

Use real query logic from /src/domain/services/analytics_service.py

After building both, compare:
- Code complexity
- Query flexibility
- Performance characteristics
- Client experience

Help me decide which to use for the full implementation.
```

**Expected Output:**
- Two prototype implementations
- Comparison analysis
- Recommendation with rationale
- If GraphQL chosen: Draft ADR for the decision

---

## When to Use Spike Mode

- Evaluating competing technologies
- Proving feasibility before commitment
- Learning a new library/framework
- Performance benchmarking

## What Comes After a Spike

If the spike succeeds and you want to productionize:
1. Create a proper PRD capturing what you learned
2. Create TDD based on spike learnings
3. Create ADR documenting the choice
4. Re-implement with production quality

