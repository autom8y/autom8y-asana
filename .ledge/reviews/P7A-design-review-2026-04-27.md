---
type: review
status: draft
procession_id: cache-freshness-procession-2026-04-27
station: P7.A.1
author_agent: thermia.thermal-monitor
parent_telos: verify-active-mrr-provenance
parent_telos_field: verified_realized
verification_deadline: 2026-05-27
authored_on: 2026-04-27
commit_sha_at_authoring: 2253ebc1
lens_3_status: SUSPENDED-PENDING-CROSS-CHECK
---

# P7.A.1 — 5-Lens Design Review (Lens-3 Suspended)
## cache-freshness-procession-2026-04-27

Substrate reviewed:
- `.ledge/specs/cache-freshness-architecture.tdd.md` (P2)
- `.ledge/specs/cache-freshness-capacity-spec.md` (P3)
- `.ledge/specs/cache-freshness-observability.md` (P4, lens-3 territory skipped)
- `.ledge/specs/cache-freshness-runbook.md`
- `.ledge/decisions/ADR-001..ADR-006`
- `.ledge/handoffs/HANDOFF-10x-dev-to-thermia-2026-04-27.md`

Lens-3 (observability-completeness) is SUSPENDED-PENDING-CROSS-CHECK by
`heat-mapper` at `.ledge/reviews/P7A-cross-check-lens3-observability-2026-04-27.md`.

---

## Lens 1 — Freshness-Bound

**Verdict**: PASS

**Evidence**:
- `cache-freshness-architecture.tdd.md:79-89` — AP-consistency model with explicit 6h staleness budget for ACTIVE-classifier sections, grounded in PRD G2 and CACHE:SRC-003 (Brewer CAP, STRONG).
- `cache-freshness-observability.md:107-119` — SLO-1 (ParquetMaxAgeSLO) targets 95% of invocations below 21600s over a rolling 7-day window. Derivation traced to PRD G2 (`prd.md:70-71`).
- `cache-freshness-observability.md:159-181` — ALERT-1 threshold = 21600 (6h exactly, not an arbitrary percentage). Evaluation period 300s. Single-invocation breach triggers P2 WARNING.
- HANDOFF §3.1 SLI table — `MaxParquetAgeSeconds` wired at `cloudwatch_emit.py:1-233` with computation at `freshness.py:202`. `[LANDED]`.

**Reasoning**: The freshness bound is consistently defined across P2, P3, P4, and the implementation. The 6h / 21600s threshold derives from a named PRD constraint (G2) and is realized as both a CLI enforcement gate (`--strict` at `__main__.py:341`) and a CloudWatch alarm threshold. The SLO-1 95% error budget is derived arithmetic, not an arbitrary percentage. The staleness signal is in-band (additive freshness line in default mode per ADR-001) rather than siloed to a side channel.

**Carry-forward concerns**: SLO-1 starts in deficit — 9/14 sections exceed 6h staleness at handoff (capacity-spec §1.2). This is documented and expected pre-Batch-D. The deficit is a deployment-state fact, not a design flaw.

---

## Lens 2 — Hit-Rate / Cardinality (Eviction-Policy MERGED-IN)

**Verdict**: PASS

**Evidence**:
- `cache-freshness-capacity-spec.md:148-162` — MemoryTier working-set sizing: 14 sections at ~0.91 MB vs 76.8 MB available at 256 MB container. `max_entries=100` at 14% utilization. Headroom 84x.
- `cache-freshness-capacity-spec.md:303-323` — Eviction policy: LRU for MemoryTier (OrderedDict at `memory.py:85`), N/A for S3 cold tier (object storage, no eviction). Rationale: non-Zipfian access pattern at 14 entries vs 100-entry capacity; W-TinyLFU scan resistance not warranted.
- `cache-freshness-capacity-spec.md:165-175` — Growth projection: 10x scenario (140 sections) remains within capacity; `max_entries=100` becomes the binding constraint at ~100 sections. Flagged as a minor config change, not a redesign.
- `cache-freshness-architecture.tdd.md:229-248` — Multi-level hierarchy: L1 (MemoryTier) bounded by active project_gid keys; L2 (S3 parquet) bounded by section count (14 at handoff). L2 >= L1 by design.

**Reasoning**: The cardinality analysis is grounded in empirical data (14 sections observed, 292 KB total parquet data). The LRU eviction policy selection is justified against the actual access pattern (not assumed Zipfian). The growth analysis correctly identifies `max_entries=100` as the binding constraint at 10x scale and explicitly names the corrective action (raise to 150-175). This is not a hidden trap.

**Carry-forward concerns**: `max_entries=100` raise is flagged as LD-P3-3 (DEFER-FOLLOWUP). At 14/100 current utilization this is correctly deferred. Becomes load-bearing at ~100 sections.

---

## Lens 3 — Observability-Completeness

**Verdict**: SUSPENDED-PENDING-CROSS-CHECK

This lens is not evaluated in this artifact. `thermia.thermal-monitor` authored
the P4 observability spec (`cache-freshness-observability.md`); applying this
lens to its own authored work violates Axiom 1 (critic-rite-disjointness, per
`external-critique-gate-cross-rite-residency` skill). `heat-mapper` applies
lens 3 independently at `.ledge/reviews/P7A-cross-check-lens3-observability-2026-04-27.md`.

---

## Lens 4 — Failure-Mode (Stampede MERGED-IN)

**Verdict**: PASS-WITH-NOTE

**Evidence**:
- `cache-freshness-architecture.tdd.md:112-117` (Layer 1 failure mode table) — S3 unavailability: fail-open with `FreshnessError` at `freshness.py:158-182`; origin unavailability: fail-open stale with `WarmFailure` metric at `cache_warmer.py:501-504`; network partition: fail-closed for freshness probe (`FreshnessError.KIND_NETWORK`), exit 1 per AC-4.3/4.4.
- `cache-freshness-architecture.tdd.md:179-184` (Layer 2 failure mode table) — MemoryTier OOM/eviction: fail-open bypass to ProgressiveTier; Asana API unavailable during SWR: fail-open stale (exception caught at `factory.py:118`).
- `cache-freshness-capacity-spec.md:248-256` — Stampede: `DataFrameCacheCoalescer` at `coalescer.py` wired at `DataFrameCache` level (`dataframe_cache.py:191`). Force-warm CLI must route through `DataFrameCache`, not direct Lambda invoke. HANDOFF confirms coalescer-routing per LD-P3-2 structural enforcement (`grep -n "boto3" __main__.py` returns only 3 docstring mentions at lines 252, 258, 314).
- `cache-freshness-architecture.tdd.md:587-638` — AP-3 named risk: `MutationInvalidator._TASK_ENTRY_TYPES` excludes DataFrame parquet tier (`mutation_invalidator.py:36`). Task mutation does not trigger parquet re-write. Documented as known architectural gap.

**Reasoning**: All four non-transient failure modes from the architecture have detection paths: S3 cache miss maps to ALERT-5 (kind=not-found), stale cache maps to ALERT-1/ALERT-2, Lambda warmer failure maps to ALERT-3, S3 unavailability maps to ALERT-5 (kind=network). Warmer timeout with self-continuation is correctly excluded (checkpoint resume at `cache_warmer.py:399-425` is designed behavior, not a failure). The stampede protection via coalescer + idempotency key (P3 §5.2 PDR-4) is structurally enforced via LD-P3-2 at implementation.

**Note (not a FAIL)**: AP-3 (parquet not invalidated on task mutation) is the one failure mode that has no automatic detection path — it surfaces only through freshness staleness readings, not through a mutation-triggered alert. This is explicitly accepted per DEF-3 (eventual consistency is tolerable for internal/operational use). The force-warm CLI provides operator-accessible remediation. The risk is named, not hidden. The note is carried forward so Track B in-anger probes confirm the AP-3 docstring is in place at `force_warm.py:28-30`.

**Carry-forward concerns**: `CoalescerDedupCount` metric (stampede activation monitoring) is wired at `coalescer.py:34-67` per HANDOFF WI-4 `[LANDED]`. AP-3 acceptance recorded at `force_warm.py:28-30` — Track B should verify the docstring is present and accurate.

---

## Lens 5 — Consistency-Model

**Verdict**: PASS

**Evidence**:
- `cache-freshness-architecture.tdd.md:79-89` — AP-positioning selected per CACHE:SRC-003 (Brewer CAP, STRONG grade). Rationale: internal/operational metric (DEF-3); serving 6h-old figure with visible freshness signal is preferable to refusing to answer during partition.
- `cache-freshness-architecture.tdd.md:155-163` — MemoryTier inherits eventual consistency from ProgressiveTier; no linearizability requirement.
- `cache-freshness-architecture.tdd.md:206-212` — Freshness probe (Layer 3) reads S3 `LastModified` directly; S3 provides strong read-after-write consistency for new objects (since 2020). No coordination needed with MemoryTier.
- `cache-freshness-architecture.tdd.md:707-730` — ADR-004 embedded in TDD: AP alternative (CP positioning) explicitly considered and rejected — CP would require Lambda warm to complete before CLI returns, impossible under cache-aside with CLI/Lambda separation, unacceptable UX.
- `cache-freshness-architecture.tdd.md:91-108` — Consumer observations per state: (a) cache hit exits 0; (b) cache miss exits 1; (c) stale data served with WARNING, `--strict` exits 1; (d) post-write-during-warm: accepted eventual consistency window with dedup via coalescer.

**Reasoning**: The AP consistency model is correctly applied across all three layers. The consistency-model selection is documented with the correct CAP-literature grounding (CACHE:SRC-003, STRONG). The `FreshnessReport` serves as the explicit compensation mechanism — it makes the consistency window visible. The `--strict` flag is the enforcement gate for consumers who require freshness before acting. If DEF-3 changes (investor-grade scenario), the USER-ADJUDICATION-REQUIRED heat-mapper flag is the documented trigger for a consistency-model revisit.

**Carry-forward concerns**: None. The consistency model is coherent across all three layers and the compensation mechanism is instrumented.

---

## Lens 6 — Staleness-Bound (TTL-Strategy MERGED-IN)

**Verdict**: PASS-WITH-NOTE

**Evidence**:
- `cache-freshness-capacity-spec.md:84-115` — Tiered TTL: ACTIVE 6h (21600s), WARM 12h (43200s), COLD 24h (86400s), near-empty 7d (604800s). Derivation math present: ACTIVE = PRD G2 anchor; WARM = heat-mapper freshness budget table; COLD = aligned with DMS 24h window; near-empty = coincides with `S3Config.default_ttl = 604800` at `cache/backends/s3.py` line 46.
- `cache-freshness-capacity-spec.md:84-90` — Force-warm cadence: every 4h for ACTIVE class (0.67 × TTL), providing one full warm cycle headroom before 6h threshold. Derivation: 4h cadence at 2-minute max execution leaves 4h 2min elapsed before TTL breach.
- `cache-freshness-observability.md:159-205` — ALERT-1 (single breach at 21600s) and ALERT-2 (sustained 30 minutes at 21600s) both derive threshold from ACTIVE-class TTL. No arbitrary percentage.
- `cache-freshness-capacity-spec.md:344-362` — PDR-2: tiered TTL vs flat TTL decision. Anti-pattern register item "Flat TTL" cited. Rationale: near-empty 32-day sections should not be warmed at 6h cadence.
- ADR-005 (`ADR-005-ttl-manifest-schema-and-sidecar.md`) — TTL persistence via YAML manifest + JSON S3 sidecar with V-1..V-6 validators. `sla_profile.py:1-652` implements full schema.

**Reasoning**: The staleness-bound design is principled and fully derived. The 4-class TTL taxonomy is grounded in observed mtime data, not assumed. The manifest/sidecar persistence mechanism (ADR-005) makes TTL configuration auditable (version-controlled in `.know/`) and operator-overridable (S3 sidecar). The warmer cadence (4h for ACTIVE class per ADR-004) satisfies SLO-1 once Batch-D Terraform apply completes.

**Note (not a FAIL)**: GID-to-ACTIVE-name mapping is unresolved ([DEFER] at capacity-spec §2.1). Until the mapping is established, all 14 sections are conservatively treated as ACTIVE-class. This means SLO-1 applies to the full fleet, not just the 3 named ACTIVE sections. Conservative fallback is correct operational posture. The ADR-005 manifest provides the mechanism to encode the mapping once resolved.

**Carry-forward concerns**: GID-to-name mapping (LD-P3-3 forward reference) needed to activate per-class TTL enforcement. Conservative all-ACTIVE treatment is the correct interim state. No FAIL because the mechanism is in place; the data to populate it requires a runtime Asana API call or parquet metadata read.

---

## Lens 10 — Capacity Sizing

**Verdict**: PASS

**Evidence**:
- `cache-freshness-capacity-spec.md:136-162` — Current working set: 14 sections, 292 KB total parquet data, ~0.91 MB in-memory (3x Polars decompression factor). `max_entries=100` at 14% utilization. Headroom 84x at 256 MB container.
- `cache-freshness-capacity-spec.md:165-175` — Growth projection: 10x scenario (140 sections) yields ~9.1 MB in-memory vs 76.8 MB available; `max_entries=100` becomes binding at ~100 sections.
- `cache-freshness-capacity-spec.md:178-190` — Daily write volume: 680.7 KB/day (~34 PUT requests/day). Monthly PUT cost: $0.005. Storage cost: < $0.01/month.
- `cache-freshness-capacity-spec.md:196-213` — Lambda invocation cost: $0.0000003–$0.000017/invocation. Monthly upper bound: $0.30 at 10 operator force-warms/day.
- `cache-freshness-capacity-spec.md:216-226` — Theoretical burst cap: 1 invocation/minute/day = $4.32/month. Not a decision constraint at any realistic volume.
- `cache-freshness-capacity-spec.md:326-338` — Aggregate resource plan table: total incremental monthly cost < $0.10/month (capacity-engineer scope only).

**Reasoning**: The capacity sizing is derived from empirical data (14 sections, 292 KB observed at handoff 2026-04-27). All cost and resource estimates include derivation chains to source data. The sensitivity analysis (§10 of capacity-spec) confirms all estimates are insensitive to 2x variations in parquet size or Lambda execution time. The working set is trivially small relative to container allocations — capacity is not a constraint at current or projected scale.

**Carry-forward concerns**: None. Capacity sizing is grounded, with explicit growth projection and sensitivity analysis.

---

## Summary

| Lens | Verdict |
|------|---------|
| 1 — freshness-bound | PASS |
| 2 — hit-rate / cardinality (eviction MERGED) | PASS |
| 3 — observability-completeness | SUSPENDED-PENDING-CROSS-CHECK |
| 4 — failure-mode (stampede MERGED) | PASS-WITH-NOTE |
| 5 — consistency-model | PASS |
| 6 — staleness-bound (TTL MERGED) | PASS-WITH-NOTE |
| 10 — capacity sizing | PASS |

**PASS**: 5 of 6 load-bearing lenses (lens 3 suspended).
**PASS-WITH-NOTE**: Lenses 4 and 6. Notes are named risks (AP-3, GID mapping) that are documented, accepted, and not blockers.
**FAIL**: None.

Track A disposition pending: lens 3 cross-check result + P7.A.3 ALERT predicate execution.
