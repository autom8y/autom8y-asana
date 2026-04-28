---
type: review
status: draft
procession_id: cache-freshness-procession-2026-04-27
station: P7.A.0
author_agent: thermia.thermal-monitor
parent_telos: verify-active-mrr-provenance
parent_telos_field: verified_realized
verification_deadline: 2026-05-27
authored_on: 2026-04-27
commit_sha_at_authoring: 2253ebc1
---

# P7.A.0 — Lens Disposition (Entry)
## cache-freshness-procession-2026-04-27

This artifact is authored by `thermia.thermal-monitor` as verifier-of-record for
the 11-lens rubric scope decision. I have read the Potnia-authored §3 lens table
from `.ledge/reviews/P7-procession-plan-2026-04-27.md` and reproduce it below as
my own disposition, marking each row with my CONCUR or DIVERGE verdict.

---

## Lens Disposition Table

| # | Lens | Potnia Preliminary Disposition | thermal-monitor Verdict | Rationale |
|---|------|-------------------------------|------------------------|-----------|
| 1 | freshness-bound | LOAD-BEARING | **CONCUR** | Core telos signal. `MaxParquetAgeSeconds` is the direct `verified_realized` evidence surface. Observable without deploy. |
| 2 | hit-rate / cardinality (eviction-policy MERGED-IN) | LOAD-BEARING | **CONCUR** | Cardinality is the load-bearing fact driving eviction selection. LRU-vs-alternatives is correctly resolved at P3 capacity-spec §6.2. Merged lens scope is appropriate. |
| 3 | observability-completeness | LOAD-BEARING (cross-checked, FLAG-1) | **CONCUR — SUSPENDED-PENDING-CROSS-CHECK** | Lens 3 is load-bearing. I authored P4; heat-mapper is the disjoint critic per Axiom 1. This dispatch leaves lens 3 with SUSPENDED-PENDING-CROSS-CHECK status until `.ledge/reviews/P7A-cross-check-lens3-observability-2026-04-27.md` is produced. |
| 4 | failure-mode (stampede MERGED-IN) | LOAD-BEARING | **CONCUR** | Stampede is correctly classified as a failure-mode subspecies. Lease-token analysis lives at P3 §5.2 (`capacity-spec.md:265-285`); coalescer + idempotency key selection is the architecture answer. One lens covers both. |
| 5 | consistency-model | LOAD-BEARING | **CONCUR** | AP-positioning is the contract-shape evidence for the telos. CAP decision at architecture TDD §Layer 1 (`cache-freshness-architecture.tdd.md:79-89`) is the structural anchor. |
| 6 | staleness-bound (TTL-strategy MERGED-IN) | LOAD-BEARING | **CONCUR** | TTL is the realization mechanism of the staleness bound. ACTIVE-class 6h / 21600s is the P3-derived threshold that ALERT-1 and ALERT-2 enforce. |
| 7 | stampede protection | MERGED-INTO-failure-mode | **CONCUR** | Lens 4 absorbs. No independent coverage needed. |
| 8 | TTL strategy | MERGED-INTO-staleness-bound | **CONCUR** | Lens 6 absorbs. TTL derivation math at P3 §2.2 is the same evidence base. |
| 9 | eviction policy | MERGED-INTO-cardinality | **CONCUR** | Lens 2 absorbs. At 14/100 entries the eviction question is academically resolved. |
| 10 | capacity sizing | LOAD-BEARING | **CONCUR** | P3 capacity-spec is independently verifiable against observed mtime histogram and working-set math. Direct evidence chain to telos. |
| 11 | rollback / blast-radius | SKIPPED-WITH-RATIONALE | **CONCUR** | Read-path-only cache. No write-path blast radius beyond cache invalidation, which lens 4 covers. AP-3 (parquet not invalidated on task mutation) is the closest analog; it is documented in architecture TDD §7 and in failure-mode lens 4 coverage. No independent lens warranted. |

---

## Net Disposition

- **LOAD-BEARING**: Lenses 1, 2+9, 3 (SUSPENDED), 4+7, 5, 6+8, 10 — 6 LOAD-BEARING (lens 3 suspended pending cross-check)
- **MERGED**: Lenses 7, 8, 9 (absorbed into 4, 6, 2 respectively)
- **SKIPPED-WITH-RATIONALE**: Lens 11

---

## Divergence Register

**No divergences.** I CONCUR with all 11 rows of Potnia's preliminary table.

The only substantive note is that lens 3 (observability-completeness)
carries an inner FLAG-1 seam: I authored P4 (`cache-freshness-observability.md`),
making self-review problematic. The cross-check assignment to heat-mapper is
correct and I endorse it. My P7.A.1 design-review artifact marks lens 3
`SUSPENDED-PENDING-CROSS-CHECK` accordingly.

---

## Verifier-of-Record Commitment

As `thermia.thermal-monitor`, I own the lens-rubric scope decision for this
procession. The 6 LOAD-BEARING lenses (1, 2, 4, 5, 6, 10) are applied in
P7.A.1. Lens 3 is applied by heat-mapper in P7.A.1-CROSS. Lens 11 is
formally skipped with rationale recorded here.
