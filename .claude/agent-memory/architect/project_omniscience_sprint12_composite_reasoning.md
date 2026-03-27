---
name: Omniscience Sprint 12 Composite Reasoning Surface
description: Architecture design for cross-domain query composition across matching, lifecycle, and semantic APIs -- composition over monolith pattern
type: project
---

Sprint 12 spike produced at `.ledge/spikes/omniscience-composite-reasoning-patterns.md`.

**Why:** AI agents need to reason about business health by combining matching (duplicate detection), lifecycle (stage transitions/stall detection), and semantic (field metadata/enum values) capabilities. No single endpoint answers cross-domain questions.

**How to apply:** Three key design decisions:
- D1: Sequential fan-out with client-side join -- agents compose existing endpoints rather than calling new monolithic composite endpoints. GID-set passing via IN predicates is the composition joint.
- D2: GID-set passing pattern -- output of domain A becomes an IN predicate for domain B. Bounded by 1000 per page; paginate for larger sets.
- D3: Schema-first discovery protocol -- agents MUST execute discovery (GET /entities, /fields, /sections, /schema) before constructing composite queries to prevent hallucinated field names.

Three patterns specified with concrete JSON payloads:
1. Sales-stage businesses + high-aggression offers + duplicate detection (lifecycle + semantic + matching)
2. Stalled businesses + cascade health degradation (lifecycle + cascade monitoring)
3. Pipeline conversion funnel by semantic field completeness (lifecycle + semantic)

Performance: Patterns 2 and 3 complete in <700ms at 10K scale. Pattern 1 bottleneck is per-entity matching calls -- requires parallelism at >10 candidates, batch endpoint deferred until measured need.

Scale wall at 50K entities: IN-predicate lists become expensive. Mitigation path: batch matching endpoint, then server-side ephemeral result sets.
