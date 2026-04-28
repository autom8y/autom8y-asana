---
type: review
status: draft
procession_id: cache-freshness-procession-2026-04-27
station: P7.A.5
author_agent: thermia.thermal-monitor
parent_telos: verify-active-mrr-provenance
parent_telos_field: verified_realized
verification_deadline: 2026-05-27
authored_on: 2026-04-27
commit_sha_at_authoring: 2253ebc1
potnia_preclassification_source: .ledge/reviews/P7-procession-plan-2026-04-27.md#§4
---

# P7.A.5 — DEFER-FOLLOWUP Adjudication
## cache-freshness-procession-2026-04-27

I validate Potnia's §4 pre-classification from the procession plan, adjudicating
each item as CONCUR or REVISE with rationale. For telos-adjacent items, I produce
promotion verdicts with named owners and evidence requirements. For telos-orthogonal
items, I provide brief rationale confirming orthogonality.

---

## Part 1: Telos-Orthogonal Items (3 items — remain DEFER)

These items are pre-classified by Potnia as orthogonal to the parent telos
`verify-active-mrr-provenance` / D8 `verified_realized`.

---

### LD-P2-4 — XFetch Beta Calibration

**Potnia pre-class**: telos-orthogonal
**thermal-monitor verdict**: **CONCUR**

**Rationale**: XFetch (CACHE:SRC-001, Vattani et al. 2015) is the probabilistic
early-refresh mechanism at the MemoryTier boundary. Its beta parameter calibration
(`beta=1.0` starting value per architecture TDD §6) is a performance-tuning concern,
not a freshness-correctness concern. The parent telos `verify-active-mrr-provenance`
requires verifying that the freshness signal is accurate and the staleness gate
functions correctly. XFetch controls *when* L1 refreshes from L2 — it does not
control whether the staleness signal reaches the CLI consumer. Even with un-tuned
beta, the freshness probe independently reads S3 `LastModified` timestamps and the
`--strict` gate enforces the SLO. XFetch beta miscalibration produces suboptimal
cache hit rates, not incorrect freshness readings. Telos-orthogonal is correct.

---

### LD-P3-3 — max_entries=100 Raise to 150

**Potnia pre-class**: telos-orthogonal
**thermal-monitor verdict**: **CONCUR**

**Rationale**: At 14/100 entries (14% utilization), the MemoryTier capacity limit
has no operational impact on freshness. Lens 2 (cardinality) at P7.A.1 verifies
that the current working set is 84x smaller than available capacity. The `max_entries`
raise only becomes load-bearing at ~100 sections (~10x current section count per
capacity-spec §3.2). The parent telos requires verifying the freshness signal and
SLO-1 compliance — neither of which depends on MemoryTier capacity at current scale.
Telos-orthogonal is correct.

---

### ForceWarmLatency no-alarm-today

**Potnia pre-class**: telos-orthogonal
**thermal-monitor verdict**: **CONCUR**

**Rationale**: `ForceWarmLatencySeconds` is an informational metric (HANDOFF §3.1,
ADR-006 alarm-vs-metric matrix: `NO` alarm for `ForceWarmLatencySeconds`). The
latency of a force-warm invocation is a performance metric, not a freshness-correctness
metric. SLO-1 is the freshness-correctness SLO; `MaxParquetAgeSeconds` is its
enforcement signal. A slow force-warm that eventually completes still satisfies
SLO-1. A no-alarm decision on latency does not affect the parent telos evidence
chain. Telos-orthogonal is correct. The DEF-2 seam note ("derive SLO post-P3 cadence
resolution") is a future-procession concern.

---

## Part 2: Telos-Adjacent Items (4 items — PROMOTE)

These items are pre-classified by Potnia as adjacent to the parent telos and
requiring in-procession resolution or close tracking.

---

### LD-P5A-1 — INDEX Ordering

**Potnia pre-class**: telos-adjacent (PROMOTE)
**thermal-monitor verdict**: **CONCUR-PROMOTE**

**Promoted verdict**: PROMOTE to in-procession resolution — named to hygiene rite.

**Reasoning**: The HANDOFF §6.2 description of LD-P5A-1 ("entries appended chronologically
per schema `.ledge/specs/handoff-dossier-schema.tdd.md:223-234`; no canonical ordering
policy beyond append") touches observability-completeness lens 3: if INDEX entries
are chronological-only, a rite-disjoint attester scanning `INDEX.md` for
"status=ATTESTED-PENDING" entries cannot rely on consistent sort order for triage.
Potnia's rationale (affects lens 3) is correct. However, the INDEX ordering question
is structural catalog hygiene, not freshness-signal correctness.

**Evidence the verification attestation needs to record**: Confirmation that
`.ledge/handoffs/INDEX.md` contains the HANDOFF-10x-dev-to-thermia entry and is
discoverable by grep (i.e., the by-append behavior does not break discoverability
in practice for this procession's dossier count).

**Named owner**: hygiene rite (`naxos` or `janitor` agent). Ordering policy is
a `.ledge/` schema concern, not a thermia-procession correctness concern.

**Resolution target**: Post-attestation, via hygiene rite secondary handoff (already
referenced at `.ledge/handoffs/HANDOFF-thermia-to-hygiene-2026-04-27.md`).

**Owner+date**: hygiene rite, post-P7-close (no hard deadline; not a blocker for
attestation). If not resolved by 2026-05-27, record as open item in the verification
attestation with the hygiene handoff as the discharge path.

---

### LD-P5A-2 — Status Vocabulary Divergence

**Potnia pre-class**: telos-adjacent (PROMOTE)
**thermal-monitor verdict**: **CONCUR-PROMOTE**

**Promoted verdict**: PROMOTE to in-procession awareness — adjudicated here, no
further owner escalation required.

**Reasoning**: The divergence between `status: draft` (lifecycle vocabulary, used
in predecessor HANDOFF frontmatter) and `status: PENDING-THERMIA-P7` (state-machine
vocabulary per schema §1.2, used in the 10x-dev→thermia HANDOFF) creates potential
scanning ambiguity for rite-disjoint attesters who grep `INDEX.md` or filter by
`status:`. Potnia's characterization (affects rite-disjoint attester verification)
is sound.

**Evidence the verification attestation needs to record**: This P7.A.5 document
itself uses `status: draft` per the `.ledge/` hook advisory (valid statuses:
`accepted, proposed, superseded, rejected, stale, deprecated, draft`). The 10x-dev
HANDOFF's `PENDING-THERMIA-P7` is not in the canonical vocabulary. This is a
concrete vocabulary drift that thermia.thermal-monitor observes in this dispatch.

**Resolution**: The thermia procession artifacts authored in this dispatch use
`status: draft` (lifecycle-correct). The HANDOFF `status: draft` field in the
dossier frontmatter is also lifecycle-correct. The `PENDING-THERMIA-P7` variant
in the 10x-dev→thermia HANDOFF's `status` field is the non-canonical form.

**Owner+date**: LD-P5A-2 should be raised to ADR post-P6 if the divergence recurs
across more than 3 handoffs. At current count (1 instance observed), the HANDOFF
§6.2 characterization ("Raise to ADR post-P6 if it becomes load-bearing") is the
correct disposition. No additional owner escalation needed at this procession
level. Record in verification attestation as: vocabulary drift observed, 1 instance,
monitoring for recurrence.

---

### SectionAgeP95 Low-N Degeneracy

**Potnia pre-class**: telos-adjacent (PROMOTE)
**thermal-monitor verdict**: **CONCUR-PROMOTE**

**Promoted verdict**: PROMOTE to explicit Track A carry-forward — named concern
for Track B observation.

**Reasoning**: At N=14 sections, P95 = the 95th percentile of 14 values. The
nearest-rank P95 index = ceil(0.95 × 14) = 14, which is the maximum value in the
sorted list. `SectionAgeP95Seconds` is therefore structurally equivalent to
`MaxParquetAgeSeconds` at N=14. The metric does not provide the "distribution-aware
staleness" signal it is designed to provide until N >= ~20 sections (where P95
begins to differentiate from the max).

This is telos-adjacent because `SectionAgeP95Seconds` is cited in the
observability spec as a lens for lens 3 coverage. If the metric is degenerate at
current N, its observability contribution for freshness-bound verification is
reduced. It does not affect SLO-1 (which uses `MaxParquetAgeSeconds`) but it
affects the richness of the dashboard and the completeness assessment lens 3 applies.

**Evidence the verification attestation needs to record**: Record that at N=14,
`SectionAgeP95Seconds = MaxParquetAgeSeconds` (structurally). This is not a defect
— the metric is correctly computed. The degeneracy is a statistical property of
low-N percentile computation that will self-resolve as section count grows. Track B
in-anger Probe-5 (if executed post-deploy) should note the P95 value and confirm
it equals or approximates the max.

**Named owner**: No escalation needed. The implementation is correct; the metric
will become more informative at N >= ~20. Record in attestation as: SectionAgeP95
is statistically degenerate at N=14 (P95 = max); self-resolves with section count
growth; not a freshness-correctness gap.

**Owner+date**: Self-resolving via organic section count growth. If section count
does not grow to N >= 20 by 2026-11-27 (6 months post-telos deadline), raise as a
metrics-design follow-up in the next thermia procession touching the observability
spec.

---

### AP-3 — Parquet Not Invalidated on Task Mutation

**Potnia pre-class**: telos-adjacent (PROMOTE)
**thermal-monitor verdict**: **CONCUR-PROMOTE**

**Promoted verdict**: PROMOTE to attestation record — explicit risk-acceptance
confirmation required.

**Reasoning**: AP-3 (`MutationInvalidator._TASK_ENTRY_TYPES` excludes DataFrame
parquet tier at `mutation_invalidator.py:36`) is the most material telos-adjacent
item. It directly affects MRR-provenance correctness: an Asana task moving between
sections is not reflected in the parquet (and thus the `active_mrr` aggregate)
until the next scheduled Lambda warm or operator-triggered force-warm. The parent
telos is `verify-active-mrr-provenance`; AP-3 is a case where the provenance can
be temporarily wrong without any automated detection signal.

Potnia's characterization is correct: "Invalidation-correctness is failure-mode
lens 4; if parquet stale, MRR-provenance unverifiable." However, the risk has been
explicitly named, bounded, and accepted per:
- `cache-freshness-architecture.tdd.md:587-645` (full AP-3 documentation in §7)
- `force_warm.py:28-30` (docstring recording the risk acceptance)
- DEF-3 (internal/operational eventual consistency accepted)
- The `--force-warm` CLI as operator-accessible remediation

**Evidence the verification attestation needs to record**:
1. The AP-3 docstring at `force_warm.py:28-30` is present in the implementation (Track B Probe-3 or independent code read should confirm).
2. The gap is bounded by the Lambda warm cadence (4h for ACTIVE class post-Batch-D apply) — at worst, the provenance is ~4h stale after a task mutation.
3. The staleness is visible to any operator who runs the freshness CLI — it is not silent.
4. The `--force-warm` CLI provides sub-minute remediation on demand.

**Named owner**: thermia rite (this procession). Record as explicit risk-acceptance
in the verification attestation body. Future procession targeting event-driven
re-warm (DEF-5, heat-mapper deferred decisions) would close AP-3 architecturally.

**Owner+date**: AP-3 risk-acceptance is complete at this procession. The DEF-5
follow-up procession has no committed date — surface to user if investor-grade
usage of `active_mrr` is ever declared (USER-ADJUDICATION-REQUIRED flag from
heat-mapper G5 is the trigger). At that point AP-3 becomes a blocker and the
DEF-5 procession must be scheduled.

---

## Summary

| ID | Potnia Pre-Class | thermal-monitor Verdict | Owner | Resolution |
|----|-----------------|------------------------|-------|-----------|
| LD-P2-4 (XFetch beta) | telos-orthogonal | CONCUR | N/A | Remain DEFER |
| LD-P3-3 (max_entries raise) | telos-orthogonal | CONCUR | N/A | Remain DEFER |
| ForceWarmLatency no-alarm | telos-orthogonal | CONCUR | N/A | Remain DEFER |
| LD-P5A-1 (INDEX ordering) | telos-adjacent (PROMOTE) | CONCUR-PROMOTE | hygiene rite | Post-attestation via hygiene handoff |
| LD-P5A-2 (status vocabulary) | telos-adjacent (PROMOTE) | CONCUR-PROMOTE | thermia (this dispatch) | Resolved here; monitor for recurrence; raise to ADR if > 3 instances |
| SectionAgeP95 low-N | telos-adjacent (PROMOTE) | CONCUR-PROMOTE | self-resolving | Record in attestation; no owner escalation |
| AP-3 (parquet not invalidated) | telos-adjacent (PROMOTE) | CONCUR-PROMOTE | thermia (this procession) | Explicit risk-acceptance in verification attestation; DEF-5 for future architectural close |

All 7 items are adjudicated. No REVISE verdicts (all CONCUR with Potnia's pre-classification).
The 4 telos-adjacent items are promoted per §6 predicate requirements; their
disposition is recorded for the verification attestation `## Verification Attestation`
section. Per §6 predicate, all 4 telos-adjacent DEFERs have named owners and
resolution paths — consistent with ATTESTED-WITH-FLAGS predicate if needed.
