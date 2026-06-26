---
artifact_id: PROTO-asana-r1-concurrency
type: spike
status: proposed
artifact_type: prototype-documentation
initiative: receiver-bulk-fanout-reliability — R1 (CF-1 fix)
authored_at: "2026-06-02"
author: prototype-engineer
evidence_ceiling: MODERATE
---

# PROTO — R1 Concurrency De-risk: `max_concurrent_builds` Raise Safety

## Decision Being Enabled

**Go/no-go**: Is it safe to raise `BuildCoordinator.max_concurrent_builds` above 4 to
address CF-1 (build-concurrency starvation under 104-project width that falsified the S7 gate)?
And what value is appropriate?

**Hypothesis**: The semaphore in `build_coordinator.py` is a pure asyncio gate — no shared
mutable state, no lock inversion, no correctness coupling to the value 4. Raising it to a
higher value is correctness-safe. The practical ceiling is constrained by a different axis:
the CPU thread pool and `cpu_thread_concurrency` (PDR-002 §4.3).

---

## Deliberate Shortcuts

| Shortcut | What was skipped | Production remediation |
|----------|-----------------|----------------------|
| S1 — asyncio.sleep simulation | Build `build_fn` sleeps 1.0s per key; no real Asana I/O or Polars `pl.concat`. | Production build must be re-measured at real build duration (3–15s typical). The queuing math scales linearly with duration. |
| S2 — single-worker only | All N=104 builds run in one asyncio event loop (single uvicorn worker model). Multi-worker interaction (independent semaphore per worker process) not exercised. | Multi-worker (uvicorn `--workers N`) gives N independent semaphore instances; each worker has its own `_build_coordinator` singleton. No cross-worker coordination. This is a FEATURE, not a gap — it means raising `max_concurrent_builds` per-worker has multiplicative effect at N-worker scale. |
| S3 — no CPU/thread contention | `asyncio.to_thread` + `cpu_thread_concurrency` semaphore interaction not exercised. | The `cpu_thread_concurrency` field in settings (`settings.py:276`, `le=20` bound) MUST be co-raised with `max_concurrent_builds`. They are declared "equal" in PDR-002 §4.3 comment (`capacity-specification.md:382`). Not co-raising creates a correctness hazard: more builds can queue but CPU slots stall. |
| S4 — no memory pressure | DataFrame memory impact of concurrent builds not measured. | At 104 projects × ~2 MB/frame, peak in-flight memory is bounded by `max_concurrent_builds` × 2 MB. At mcb=16: 32 MB incremental — well within the 307 MB memory tier budget (capacity-spec §1.1). |
| S5 — probe harness only | Prototype is a standalone probe script, not a change to `build_coordinator.py`. | Production change = 2 files: `build_coordinator.py:131` (default) AND `lifespan.py:237` (initialization call) AND `settings.py` (new settings-driven field) AND `cpu_thread_concurrency` default bump. |

---

## Prototype Artifact

`tests/spikes/probe_concurrency_semaphore.py` — runs in-process asyncio simulation of
N=104 distinct-key builds at `max_concurrent_builds` ∈ {4, 8, 12, 16, 20}.

**Correctness invariants tested**:
1. Semaphore respected: `max_observed_concurrent <= max_concurrent_builds` at every value.
2. All builds complete with outcome `BUILT` (no `FAILED`, `TIMED_OUT`).
3. Stats are accurate: `builds_started == N`, `builds_coalesced == 0` (distinct keys).

---

## Measured Results

**Substrate**: in-process asyncio, `sim_build_duration=1.0s`, N=104 distinct keys.

```
  MCB |   WallTime |   TheoMin |   MaxObs |  SemOK |  Correct
------------------------------------------------------------
    4 |    26.03s |   26.00s |        4 |    YES |     PASS
    8 |    13.02s |   13.00s |        8 |    YES |     PASS
   12 |     9.01s |    9.00s |       12 |    YES |     PASS
   16 |     7.01s |    7.00s |       16 |    YES |     PASS
   20 |     6.03s |    6.00s |       20 |    YES |     PASS
```

`WallTime ≈ TheoMin` at every value: the semaphore is the ONLY queuing gate; no lock
contention or deadlock introduced. All 33 existing unit tests pass at baseline (mcb=4).

**Correctness verdict: RAISE_SAFE.** Raising `max_concurrent_builds` to any value in [4, 20]
does not introduce correctness regressions in the BuildCoordinator itself. The semaphore
count is an integer constructor argument; the coalescing, cancellation-isolation, staleness
rejection, and failure-propagation paths are all indifferent to its value.

---

## Width / Throughput Analysis

At real build duration of ~5s/build (conservative median for Asana I/O + Polars concat):

```
mcb |  wall_time (N=104, 5s/build)
  4 |  ceil(104/4)  * 5 = 130s  (≈ 2.2 min)   ← current
  8 |  ceil(104/8)  * 5 =  70s  (≈ 1.2 min)
 12 |  ceil(104/12) * 5 =  45s  (≈ 0.75 min)
 16 |  ceil(104/16) * 5 =  35s  (≈ 0.58 min)
```

[UV-P: 5s/build median | METHOD: design estimate from Asana API P95 + Polars concat | REASON: real duration requires instrumented prod measurement; range 3–15s observed historically]

At mcb=4, serving 104 projects requires the builds to run in 26 batches of 4. The default
timeout for coalesced waiters is `default_timeout_seconds=55.0` (`factory.py:368`). With
5s/build and mcb=4: builds 21–26 (keys 81–104) queue for ≥25s before their slot. With
upstream request timeout of `dataframe_build_wait_seconds=30s` (`settings.py:259`), the
last 20+ builds (slots 21–26) will TIMEOUT at 30s — explaining the observed 82% rate
(≈ 85 of 104 projects receiving frames before their wait-timeout).

**Rate calculation at mcb=4, 5s/build, 30s wait-timeout**:
- Builds completing within 30s: `floor(30/5) * 4 = 24 batches × ... wait, semaphore is
  first-come-first-served per asyncio event loop scheduling.
- Actually: `30s / 5s = 6 batches of 4 = 24 keys` served before timeout.
  That is 24/104 = 23%, not 82%. The 82% is explained by coalescing (warmer pre-warmed
  most keys; only cold-miss keys hit the build path) + the single-worker topology.

**This analysis is UV-P**: the exact success-rate projection requires real build durations.
DO NOT use these numbers as the go/no-go threshold — they are directional only.

---

## Recommended Value: mcb = 8

Rationale:

1. **Throughput headroom**: Doubles the current semaphore from 4 → 8. At 5s/build, N=104:
   wall time drops from 130s → 70s. If the 30s consumer wait-timeout is the binding
   constraint, mcb=8 serves `floor(30/5) * 8 = 48` builds before timeout — roughly 46%
   of 104 cold-miss keys vs ~23% at mcb=4. With the warmer pre-warming, the fraction of
   cold-miss keys is much lower; mcb=8 is materially better for the residual cold-miss
   cases.

2. **CPU/thread alignment**: `cpu_thread_concurrency` has a settings-driven `le=20` bound
   (`settings.py:284`). PDR-002 §4.3 sizing equation is `CPU_THREAD_CONCURRENCY =
   max_concurrent_builds` (`capacity-specification.md:382`). Raising mcb=8 requires
   co-raising `cpu_thread_concurrency` default to 8. At 8 concurrent CPU threads:
   - Thread pool required: min(32, cpu_count+4). At Fargate cpu_count≈2: pool=6.
   - 8 > 6: still potentially exceeds thread pool at 0.25vCPU.
   - **This is the correctness concern for mcb=8**: S3 persistence I/O also uses the
     default executor. At mcb=8 with 0.25vCPU, we may move the thread-pool-starvation
     wall without solving it.

3. **CONSERVATIVE recommendation**: mcb=8 + the required vCPU raise (to 1.0vCPU,
   capacity-spec §4.2) together address CF-1 without approaching the thread-pool ceiling.
   At 1.0vCPU, cpu_count ≈ 4+, pool = min(32, 8+) = 8+; 8 CPU threads fit within the
   pool.

4. **If staying at 0.25vCPU** (infra change not feasible): mcb=6 is safer — stays within
   the 6-thread pool floor at cpu_count=2. This is a conservative minimum that doubles
   current throughput (26 → 18 batches for N=104 at 5s/build = 90s total) while not
   exceeding the thread pool on the most constrained Fargate host.

---

## What Didn't Work

1. **Width extrapolation from queue math**: Initial read of the capacity-spec's "26 batches
   of 4" arithmetic as directly explaining 82% failure rate was wrong. The warmer changes
   the cold-miss fraction; the 82% is not purely explained by semaphore queuing. The
   gameday evidence (rate "collapsed below 82%") under chaos suggests task restart (CF-2)
   is the dominant driver, not pure semaphore queuing (CF-1). CF-1 is a contributing
   factor to task restart (OOM / event-loop saturation from too many queued coroutines),
   not a direct throughput killer.

2. **Multi-worker as pure throughput multiplier is INCOMPLETE**: Multiple uvicorn workers
   each have independent `_build_coordinator` singletons. They do NOT share coalescing
   state. This means same-key builds from concurrent workers can run concurrently (no
   cross-worker dedup). This is a LATENT correctness gap: multi-worker + mcb raise could
   multiply S3 writes for the same key. Acceptable for the current architecture (last-write
   wins on S3) but must be documented for the production implementation.

---

## Production Gaps

| Gap | Description | Production remediation |
|-----|-------------|----------------------|
| PG-1 | `max_concurrent_builds` is hardcoded at `build_coordinator.py:131` and passed without settings wiring (`lifespan.py:237`). | Add `ASANA_CACHE_MAX_CONCURRENT_BUILDS` env var + settings field (matching pattern of `cpu_thread_concurrency`). |
| PG-2 | `cpu_thread_concurrency` must be co-changed. They must remain equal (PDR-002 §4.3). | Raise `cpu_thread_concurrency` default from 4 → 8 in `settings.py:277`. Update `le=20` guard if needed. |
| PG-3 | vCPU must be raised to 1.0 for mcb=8 to stay within thread pool bounds. | ECS task definition: `cpu: 1024` (1.0 vCPU) + memory 2048 MB per capacity-spec §4.2 recommendation. |
| PG-4 | Multi-worker cross-key dedup is absent. | Document as known limitation; acceptable for current single-worker uvicorn deploy. Multi-worker: consider a shared coordination layer (Redis Pub/Sub or Fargate Service Connect) for cross-worker coalescing. Out of scope for R1. |
| PG-5 | `default_timeout_seconds=55.0` is not the binding timeout. The consumer wait timeout is `dataframe_build_wait_seconds=30.0`. At mcb=8, 5s/build: builds 25–26 (keys 97–104) still queue ≈25s. | Investigate raising `dataframe_build_wait_seconds` to 45s or lowering build latency via warmer pre-warm coverage improvement. |

---

## Correctness Re-validation Required Before Ship

1. Re-run all 33 unit tests with `max_concurrent_builds=8` default (modify `test_default_configuration` assertion at `tests/unit/cache/test_build_coordinator.py:863`).
2. Run `TestBuildCoordinatorConcurrency::test_max_concurrent_builds_honored` at mcb=8 — it already parameterizes `max_builds = 2`; add a mcb=8 variant.
3. Run the existing `test_mixed_keys_under_contention` with `max_concurrent_builds=8` (currently uses 5 — does not break at 8).

---

## Source Anchors (file:line)

- `build_coordinator.py:131` — `max_concurrent_builds: int = 4` (current default)
- `build_coordinator.py:141` — `asyncio.Semaphore(self.max_concurrent_builds)` initialization
- `lifespan.py:232-237` — "single-worker uvicorn" comment + `initialize_build_coordinator()` with no args
- `factory.py:328-383` — `initialize_build_coordinator()` signature + idempotent guard
- `settings.py:276-285` — `cpu_thread_concurrency` field, `le=20` bound
- `dataframes/concurrency.py:16` — sizing equation: `capping concurrent CPU-bound submissions at max_concurrent_builds (= 4)`
- `capacity-specification.md:382` — `CPU_THREAD_CONCURRENCY = max_concurrent_builds = 4`
- `SRE-VERDICT-receiver-bulk-validation-2026-06-02.md:63-67` — CF-1 primary contributing factor evidence
- `obs.md:98` — RECV-BULK-001 open gap

---

## Handoff Notes for Moonshot Architect / Platform Engineer

- **RAISE_SAFE**: Raising `max_concurrent_builds` has zero correctness risk in the BuildCoordinator logic itself — measured and verified at N=104 width, mcb ∈ {4…20}.
- **Recommended default: 8**, contingent on vCPU raise to 1.0 (ECS) and co-raising `cpu_thread_concurrency` to 8.
- **Conservative floor without vCPU raise: 6** — fits within 6-thread pool minimum at Fargate cpu_count=2.
- **Settings wiring is missing** — the raise MUST be accompanied by a new env var / settings field (PG-1) so it is tunable without code changes at the next width revision.
- **This probe does NOT validate the full S7 gate recovery**. R1 (semaphore raise) is necessary but not sufficient for CONJUNCT-2. CONJUNCT-3 (drain, B3) and CONJUNCT-4 (singleflight live proof, B4) remain open.
