---
type: review
status: draft
rite: 10x-dev
date: 2026-06-07
initiative: cr3-clean-break-cutover
phase: cr3-cutover-closure-procession / R3 GATE-2 (receiver/producer side)
evidence_ceiling: MODERATE   # explore-swarm + main-thread live AWS re-verify; STRONG-lift = the redeploy-probe receipt + a rite-disjoint critic (G-CRITIC)
source: explore-swarm wf_b6224aa2-aad (6 Explore dives + adversarial synthesis) + main-thread live AWS re-verification 2026-06-07
disciplines: [G-PROVE, G-RUNG, G-THEATER, G-HALT, G-CREDENTIAL, default-to-REFUTED]
inbound_handoff: /Users/tomtenuta/Code/autom8/.ledge/handoffs/HANDOFF-autom8-sre-to-asana-receiver-cr3-r3-gate2-2026-06-07.md
---

# CR-3 R3 GATE-2 — Receiver (Producer) Pick-Up State Map (2026-06-07)

> **R2 GREEN (consumer-proven). R3 soak BLOCKED on GATE-2 (≥99% both-arms fleet mint).** The inbound
> handoff measured **70.2% project / 18.1% section on a STALE fleet image**. Live re-verify shows the
> RECEIVER is current + provisioned — so the §2A capacity fix is LIVE and §2B is a stale-image artifact.
> The work is to **mechanically prove GATE-2 on the current receiver**, not to build capacity from scratch.

## A. Live substrate truth (main-thread AWS re-verify — closes the swarm's cert-vs-live gap)
| Fact | Value (live 2026-06-07) |
|---|---|
| Receiver service | `autom8y-asana-service` @ `autom8y-cluster`, running 1/1, rollout COMPLETED |
| Task-def | **`:485`, cpu=2048 / mem=8192** (the §D substrate) |
| Image | `autom8y/asana:29ee052` (= origin/main HEAD — current `{Source}`-emitting + #52) |
| Recent revs | `:480–:485` ALL cpu=2048/8192 — **no cpu=256 CI-race regression in recent history** |
| Section warmer | `reserved_concurrency=0` (durably paused) |

## B. The two GATE-2 asks — rung-honest disposition
### §2A — receiver capacity (GENUINE) → SUBSTRATE FIX IS LIVE; DURABILITY is the residual
- **Bottleneck = single-worker event-loop CPU starvation** (NOT BuildCoordinator semaphore — adversarially refuted with ≥2-stream corroboration: D1 topology + the SRE re-gate before/after holding CPU as the only changed variable: cpu=256→1024 took task-replacements many→0, ELB-5xx 502-cascade→0, p99 30s→2.2s). `uvicorn --workers` defaults to **1** (`scripts/entrypoint.sh:53`; deliberate — singleton CPU-offload semaphore binds to one loop).
- **The lever is VERTICAL (cpu/mem bump), NOT multi-worker.** D1's `--workers N` suggestion is REFUTED: per-loop singleton-semaphore rebinding is a live hazard; thermia refuted horizontal/Redis 3/3; `max_concurrent_builds=4` is FROZEN (4×~2GB=8GB ≫ old 768MB).
- **The fix already landed**: receiver is live on cpu=2048/mem=8192 (rev :485). The 70%/18% in the handoff was the **old cpu=256 / stale-fleet era**.
- **RESIDUAL (the open wound): durability.** A CI-writer race historically re-registered cpu=256 (rev454/455/456); recent revs are clean, but the **manifest cpu/mem floor + a satellite-dispatch concurrency guard** must land or a future clean deploy can silently re-arm RECV-BULK-001.

### §2B — section 400/422 → STALE-IMAGE-ARTIFACT (HIGH), mechanically-closeable
- The receiver **requires `project_gid` in the section body** (`api/routes/query.py:499-506` fail-fast → 400 `InvalidParameterError`; malformed 16-digit GID → 422 via `query/models.py:348-358`). `section_gid` is an optional in-project filter, never a `project_gid` substitute.
- The consumer sends `project_gid` since PR #52; the body-parameterized contract is unbroken since Sprint-2 (`4822eaad`, ancestor of every image). **No receiver-side required field the consumer omits → no schema fault.** HC-7 blame REFUTED; default-to-REFUTED honored.
- **NOT yet mechanically closed**: no re-probe of 400/422 on the current image. The cheap STRONG-lift = the redeploy-probe (§D).

## C. self-measurement
The receiver DOES emit per-arm SLI (`autom8y_asana_receiver_query_outcome_total`, `receiver_query_success_rate(entity_type)`, `api/metrics.py:103-107`, recorded at `query.py:596` for body-parameterized arms) — process-local, zero consumer-log dependency. BUT the deployed gate (`receiver_bulk_fanout_deploy_gate.py:172-183`) reads **canary HTTP** status, not the receiver counter; and export to AMP/CloudWatch is UNCONFIRMED (may be process-local → lost on task replacement). **Wiring gap**: wire the gate/assertion to `receiver_query_success_rate` per arm + export to AMP for a receiver-side GATE-2 self-proof.

## D. Highest-leverage next action — the redeploy-probe (closes §2B + confirms §2A + feeds GATE-2)
Re-run `scripts/canary/receiver_bulk_fanout_deploy_gate.py` against the **current** receiver (`https://asana.api.autom8y.io`), measuring per-arm 400/422 + both-arm honest success_rate (Project content-bound; Section EXEMPT). Outcomes: 400/422 collapse → §2B = stale-image CONFIRMED; success ≥99% + zero 5xx → §2A durable on the current substrate + GATE-2 evidence. **Needs no consumer deploy.** (Operator authority for the prod-load probe.)

## E. FROZEN boundary (remediation must not move)
A1 body-parameterized `project_gid` contract (`query.py:499-506`/`models.py:322-358`) · `require_business_scope=True` (`main.py:403-425`, ADR-07 §7.1) · `honest_contract`/`honest_empty` derivation (never-fabricated-True) · 27-entity offer-domain / 29 EntityDescriptors (`entity_registry.py`) · SA OAuth chain (JWT→middleware→bot-PAT) · Semaphore(4) as the SOLE CPU-offload path (`concurrency.py`) · deploy floor cpu=2048/mem=8192 · section warm-lane durably PAUSED + serve-stale 3000s.

## F. Remediation sprint shape (Potnia-coordinated)
0. **Substrate durability** (platform-engineer): land the manifest cpu/mem floor + satellite-dispatch concurrency guard so cpu=256 cannot creep back.
1. **§2B closure** (platform-engineer + qa-adversary): the redeploy-probe → stamp stale-image CONFIRMED (or escalate to architect if 400/422 persist).
2. **self-measure wiring** (observability-engineer): export `receiver_query_outcome_total` to AMP + wire `receiver_query_success_rate` per arm; close VG-005 (CPU_STARVATION_REPLACEMENT alarm).
3. **GATE-2 verification + soak** (incident-commander): ≥99% both-arms sustained → S7 clock-start → 7-day soak. *(Note: the consumer arm is now R2-GREEN per the inbound receipt; the handoff's "monolith merged-not-deployed" is superseded by the 06-07 monolith deploy.)*
4. **IRREVERSIBLE bundle** (IC sign-off only): Stage-B → Secret-2 NEVER decommissioned; warm-lane reactivation deferred to CQ-RETURN-3.

## G. Open risks
1. §2A durability (CI-writer race) — recent revs clean but the floor+guard are unmerged.
2. §2B HIGH-on-code but not yet probe-closed.
3. GATE-2 self-proof built-but-unconsumed (gate reads canary HTTP); AMP export unconfirmed.
4. Evidence ceiling MODERATE (single-thread synthesis); the redeploy-probe receipt + a rite-disjoint critic are the STRONG-lift.

*Self-grade MODERATE (self-ref). Secrets by name/metadata only. Deployed ≠ done ≠ GATE-2-proven. Live AWS re-verify 2026-06-07 supersedes the 06-01 RESUMPTION-BRIEF.*
