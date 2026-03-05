---
user-invocable: false
---

# /spike Examples

> Usage scenarios with sample outputs.

## Example 1: Architecture Spike

```bash
/spike "Can we use GraphQL instead of REST for our API?" --timebox=4h
```

**Output**:
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

---

## Example 2: Feasibility Spike

```bash
/spike "Can we integrate real-time collaboration like Google Docs?" --timebox=2h
```

**Output**:
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

---

## Example 3: Technology Comparison

```bash
/spike "Compare test frameworks: Jest vs Vitest vs Playwright" --timebox=3h --deliverable=comparison
```

**Output**:
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

---

## Example 4: Quick 30-Minute Spike

```bash
/spike "Is there a library for parsing YAML frontmatter?" --timebox=30m
```

**Output**:
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

## Edge Case Examples

### Edge Case: Timebox Exceeded

**Scenario**: Research taking longer than expected

**Behavior**: Stop at timebox, document partial findings

**Example**:
```
[2h - TIMEBOX COMPLETE]
⚠️ Research incomplete - time budget reached

Partial findings documented:
- Option A: Researched, looks promising
- Option B: Not enough time to investigate

Recommendation: Follow-up spike needed
- Focus: Deep dive on Option B
- Duration: 2h

Report: /docs/research/SPIKE-partial-findings.md (incomplete)
```

### Edge Case: Question Too Vague

**Scenario**: Can't define success criteria

**Behavior**: Clarify with user before starting

**Example**:
```
Question: "Research authentication"

⚠️ Question too vague. Please clarify:
- What aspect? (OAuth, JWT, session-based, passwordless)
- Current state? (Adding new, replacing existing, evaluating options)
- Success criteria? (What would make this spike successful?)

Refined question: "Can we add OAuth2 to our existing JWT authentication?"
```

### Edge Case: Scope Creep

**Scenario**: Spike becoming implementation

**Behavior**: Stop and redirect

**Example**:
```
[75% checkpoint]
⚠️ Scope creep detected

Current activity:
- Building production-ready authentication module
- Writing comprehensive tests
- Planning deployment

⚠️ This is implementation, not research!

STOPPING spike. Converting to /task:

Findings so far:
- Authentication is feasible
- Recommended library: Passport.js

Next step: Create /task "Implement OAuth2 authentication" with proper PRD/TDD
```
