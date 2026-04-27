---
type: review
status: draft
station: P7
procession_id: cache-freshness-procession-2026-04-27
parent_telos: verify-active-mrr-provenance
parent_telos_field: verified_realized
parent_telos_deadline: 2026-05-27
authored_on: 2026-04-27
authored_by: thermia.potnia (P7 procession plan dispatch)
verification_mode: BOTH (Track A design-review + Track B in-anger-probe)
pythia_pt_a4_verdict: PROCEED
pythia_carry_forward_flags: [FLAG-1, FLAG-2, FLAG-3, FLAG-4, FLAG-5]
inbound_dossier: .ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md
acceptance_commit: 2253ebc1
sequencing: A — launch P7.A immediately; P7.B parallel-blocked on PRE-1..PRE-5
cross_check_seam_lens3: heat-mapper (rite-disjoint critic per Axiom 1 inner seam)
---

# P7 Procession Plan — `cache-freshness-procession-2026-04-27`

This plan is the Potnia-dispatched procession structure for P7 thermal-monitor
attestation, discharging parent telos `verify-active-mrr-provenance` D8
`verified_realized` by 2026-05-27.

Authored by `thermia.potnia` after Pythia PT-A4 (`before_attestation`)
returned PROCEED with 5 carry-forward FLAGs (FLAG-1 self-review surface,
FLAG-2 Track B precondition pinning, FLAG-3 11-lens discipline, FLAG-4
DEFER tagging, FLAG-5 worktree agent-dir drift recordable).

## §1 Phase Decomposition

### Track A (Design-Review) — primary thermal-monitor; cross-check seam heat-mapper

| Sub-phase | Agent | Artifact | Handoff predicate |
|---|---|---|---|
| P7.A.0 (entry) | thermal-monitor | `.ledge/reviews/P7A-lens-disposition-2026-04-27.md` | 11-row lens table; each row LOAD-BEARING / MERGED-INTO-{X} / SKIPPED-WITH-RATIONALE |
| P7.A.1 | thermal-monitor | `.ledge/reviews/P7A-design-review-2026-04-27.md` | LOAD-BEARING lenses 1, 2, 4, 5, 6, 10 applied to P2/P3/P4 with file:line citations; lens-3 marked `SUSPENDED-PENDING-CROSS-CHECK` |
| P7.A.1-CROSS | heat-mapper | `.ledge/reviews/P7A-cross-check-lens3-observability-2026-04-27.md` | Independent lens-3 disposition (CONCUR / DIVERGE-WITH-REASON) on P4 observability spec |
| P7.A.2 | thermal-monitor | `.ledge/reviews/P7A-adr-receipt-audit-2026-04-27.md` | ADR-001..006 each cited; §2 commit ledger SHAs cross-validated against `git log` |
| P7.A.3 | thermal-monitor | `.ledge/reviews/P7A-alert-predicates-2026-04-27.md` | ALERT-3 predicate stdout captured (operator-runnable); ALERT-5 disposition reason |
| P7.A.4 | thermal-monitor | `.ledge/reviews/P7A-probe4-rerun-2026-04-27.md` | Probe-4 test-pass receipts; comparison vs P5 baseline |
| P7.A.5 | thermal-monitor | `.ledge/reviews/P7A-defer-adjudication-2026-04-27.md` | 6 DEFERs tagged `{telos-adjacent\|telos-orthogonal}` + 1-sentence rationale per item |

### Track B (In-Anger-Probe) — primary thermal-monitor (no cross-check seam)

| Sub-phase | Agent | Artifact | Gating |
|---|---|---|---|
| P7.B.0 (gating) | thermal-monitor | (no artifact; predicate-only) | All of PRE-1..PRE-5 (§5) PASS |
| P7.B.1 | thermal-monitor | `.ledge/reviews/P7B-post-deploy-probe-{merge_sha}.md` | Probes 1, 3, 5 against deployed system |
| P7.B.2 | thermal-monitor | `.ledge/reviews/P7B-post-batchD-probe-{batchD_sha}.md` | Probe 2 against alarm topology |
| P7.B.3 | thermal-monitor | `.ledge/reviews/P7B-alarm-unsuppression-2026-05-{NN}.md` | `actions_enabled=true` un-suppression observation window clean |
| P7.B.FINAL | thermal-monitor | `## Verification Attestation` h2 in dossier | Verdict ∈ {ATTESTED, ATTESTED-WITH-FLAGS, REJECTED-REOPEN} per §6 predicate |

## §2 Receipt-Grammar Requirements

Per-sub-phase evidence types specified in Potnia output §2. All artifacts
require frontmatter: `procession_id`, `station: P7.{A.N|B.N}`, `author_agent`,
`commit_sha_at_authoring`, `parent_telos`.

## §3 Lens-Disposition Table (FLAG-3)

| # | Lens | Disposition | Rationale |
|---|------|-------------|-----------|
| 1 | freshness-bound | LOAD-BEARING | Core to parent telos `verified_realized`; staleness directly observable |
| 2 | hit-rate / cardinality | LOAD-BEARING (eviction-policy MERGED-IN) | Cardinality drives eviction-policy choice; one lens governs both |
| 3 | observability-completeness | LOAD-BEARING (cross-checked, FLAG-1) | thermal-monitor authored P4; cross-check by heat-mapper required |
| 4 | failure-mode | LOAD-BEARING (stampede MERGED-IN) | Stampede is failure-mode subspecies (CACHE:SRC-002 lease-tokens); one lens covers both |
| 5 | consistency-model | LOAD-BEARING | CAP-positioning (CACHE:SRC-003) is contract-shape evidence |
| 6 | staleness-bound (TTL-strategy MERGED-IN) | LOAD-BEARING | TTL is realization-mechanism of staleness-bound; one lens |
| 7 | stampede protection | MERGED-INTO-failure-mode | Lens 4 absorbs |
| 8 | TTL strategy | MERGED-INTO-staleness-bound | Lens 6 absorbs |
| 9 | eviction policy | MERGED-INTO-cardinality | Lens 2 absorbs |
| 10 | capacity sizing | LOAD-BEARING | P5 capacity-spec verifiable against observed load |
| 11 | rollback / blast-radius | SKIPPED-WITH-RATIONALE | Read-path-cache; no write-path blast radius beyond cache invalidation, which is covered by failure-mode lens 4 |

Net: **6 LOAD-BEARING** (1, 2+9, 3, 4+7, 5, 6+8, 10), **1 SKIPPED** (11).

## §4 DEFER-FOLLOWUP Pre-Classification (FLAG-4)

| ID | Item | Pre-class | Rationale |
|----|------|-----------|-----------|
| LD-P2-4 | XFetch beta tuning | telos-orthogonal | XFetch is stampede-mitigation; telos is MRR-provenance, not stampede-resistance |
| LD-P3-3 | max_entries raise | telos-orthogonal | Capacity-headroom; cardinality lens 2 verifies sufficiency at P3 spec |
| LD-P5A-1 | INDEX ordering | **telos-adjacent (PROMOTE)** | Affects observability-completeness lens 3 |
| LD-P5A-2 | status vocabulary | **telos-adjacent (PROMOTE)** | Vocabulary divergence affects rite-disjoint attester verification |
| (named) | ForceWarmLatency no-alarm | telos-orthogonal | Latency is performance-lens, not freshness-verification |
| (named) | SectionAgeP95 low-N | **telos-adjacent (PROMOTE)** | SectionAge IS the freshness-bound lens 1 metric; low-N undermines verification confidence |
| AP-3 | parquet-not-invalidated | **telos-adjacent (PROMOTE)** | Invalidation-correctness is failure-mode lens 4; if parquet stale, MRR-provenance unverifiable |

Pre-classification: **4 telos-adjacent (PROMOTE)**, **3 telos-orthogonal (remain DEFER)**. thermal-monitor validates and may revise during P7.A.5.

## §5 Track B Precondition Pinning (FLAG-2)

```
PRE-1: gh pr view 28 --json state --jq '.state' == "MERGED"
PRE-2: gh pr view 28 --json mergedAt --jq '.mergedAt' parsed; (now() - mergedAt).days <= 7
PRE-3: gh pr list --search "Batch-D xrepo" --state all --json number,state --jq '.[0].state' == "MERGED"
       (NOTE: §A.7 of dossier does not enumerate Batch-D PR — main agent must locate and append PR# to dossier before P7.B can proceed)
PRE-4: aws cloudwatch describe-alarms --alarm-names ALERT-1 ALERT-2 ALERT-3 ALERT-4 ALERT-5 \
         --query 'MetricAlarms[*].ActionsEnabled' --output text | tr -d '\t' == "TrueTrueTrueTrueTrue"
PRE-5: deploy-pipeline status — last-deploy SHA matches PR #28 merge SHA
```

## §6 Verdict-Shape Spec

```yaml
verification_attestation:
  attester_agent: thermal-monitor
  attester_rite: thermia
  rite_disjoint_from_authoring: true   # 10x-dev built, thermia verifies
  attested_at: {ISO-8601}
  parent_telos: verify-active-mrr-provenance
  parent_telos_field: verified_realized
  tracks_executed: [A, B]
  track_a_artifacts: [list of P7.A.* paths]
  track_b_artifacts: [list of P7.B.* paths]
  lens_disposition_ref: .ledge/reviews/P7A-lens-disposition-2026-04-27.md
  defer_adjudication_ref: .ledge/reviews/P7A-defer-adjudication-2026-04-27.md
  cross_check_ref: .ledge/reviews/P7A-cross-check-lens3-observability-2026-04-27.md
  carry_forward_flags_dispositioned: [FLAG-1, FLAG-2, FLAG-3, FLAG-4, FLAG-5]
  verdict: {ATTESTED | ATTESTED-WITH-FLAGS | REJECTED-REOPEN}
  verdict_predicate:
    ATTESTED: "all 6 LOAD-BEARING lenses PASS AND all 4 telos-adjacent DEFERs promoted-and-resolved AND Track B observation window clean"
    ATTESTED-WITH-FLAGS: "all 6 LOAD-BEARING lenses PASS AND ≤2 telos-adjacent DEFERs remain open with named owner+date AND Track B observation window clean OR has named non-blocking anomaly"
    REJECTED-REOPEN: "any LOAD-BEARING lens FAIL OR ≥1 telos-adjacent DEFER unresolved without owner OR Track B firing on freshness-bound or failure-mode alarm"
```

## §7 Sequencing Decision

**A — launch P7.A immediately; Track B parallel-blocked on PRE-1..PRE-5.**

Rationale: Track A is design-review of artifacts that already exist (no deploy
dependency). Telos deadline 2026-05-27 leaves ~30 days; PR #28 + 7d deploy lag
could consume 10-14d. Sequencing A in parallel preserves 16-20d for B. Track A
DEFER-adjudication (P7.A.5) may surface telos-adjacent items requiring code
changes — better discovered now than after merge.

## §8 Cross-Check Seam for FLAG-1

**heat-mapper** (over capacity-engineer) for P7.A.1-CROSS lens-3.

Rationale: heat-mapper has no authorship surface in P4 (whereas
capacity-engineer authored P3 which feeds into observability metrics).
Per Axiom 1 intra-rite inheritance: critic-rite-disjointness applies
even at intra-rite cross-checks when self-review surface exists.
heat-mapper is the disjoint critic.

## §9 Execution dispatch sequence

Main agent dispatch order:

1. PARALLEL — thermal-monitor (P7.A.0 entry: lens disposition table) + heat-mapper (P7.A.1-CROSS lens-3 cross-check). Both reference §3 lens table from this plan.
2. PARALLEL — thermal-monitor (P7.A.1: 5 of 6 load-bearing lenses, suspend lens-3) + thermal-monitor (P7.A.2: ADR receipt audit) + thermal-monitor (P7.A.4: Probe-4 re-run) + thermal-monitor (P7.A.5: DEFER adjudication). Note: A.1, A.2, A.4, A.5 are parallel-safe since they don't depend on each other's outputs.
3. SERIAL — thermal-monitor (P7.A.3: ALERT predicates, captures operator-runnable predicates as request to user).
4. SERIAL — Track A synthesis: stitch P7.A.{0,1,1-CROSS,2,3,4,5} into Track A close artifact.
5. PAUSE — Track B awaits PRE-1..PRE-5 clearing; main agent informs user of preconditions.
