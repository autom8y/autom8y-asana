---
type: review
status: draft
rite: 10x-dev
date: 2026-06-08
initiative: cr3-clean-break-cutover
phase: cr3-cutover-closure-procession / R3 GATE-2 (receiver/producer side) — PROBE RECEIPT
evidence_ceiling: MODERATE   # main-thread live prod probe + receiver CloudWatch logs + ALB metrics; STRONG-lift = a rite-disjoint critic (G-CRITIC) before the IRREVERSIBLE bundle
disciplines: [G-PROVE, G-RUNG, G-THEATER, G-HALT, G-CREDENTIAL, default-to-REFUTED]
supersedes_contamination: first 10-min run (bg bgxriewdd) was instrument-contaminated (JWT TTL expiry)
predecessor: .ledge/reviews/cr3-r3-gate2-producer-pickup-map-2026-06-07.md
---

# CR-3 R3 GATE-2 — Receiver Probe Receipt (2026-06-08)

> **VERDICT: GATE-2 MET** on the current receiver substrate (cpu=2048/mem=8192, image `29ee052`,
> section warmer reserved=0). Both arms ≥99% sustained over a clean 10-min @ 100rpm/arm bulk fan-out,
> 100% project content-binding, zero SA-429, zero app-side 5xx. §2A capacity DURABLE; §2B section
> 400/422 STALE-IMAGE CONFIRMED (zero 400/422 observed). Evidence MODERATE — a rite-disjoint critic
> is the remaining STRONG-lift before the irreversible (R5/R6) bundle.

## A. The contamination + instrument fix (why the first run did not count)
- **First run (bg bgxriewdd, exit 0, STATUS:PASS):** project 496/995 2xx + 499 4xx; section 496/996 2xx + 500 4xx. The gate's `success_rate = 2xx/(2xx+5xx)` (probe `:172-183`) EXCLUDES 4xx, so it read 1.0000 while **~50% of valid requests failed**.
- **Root cause = the PROBE, not the receiver.** Receiver access log: the 999 "4xx" were `401 Unauthorized`, time-clustered with a deterministic break at ~07:17 (all 200 before, 401 after) — a JWT TTL expiry signature, NOT load-induced auth flake. The probe minted ONE token at start (`_acquire_token` called once at `_main_async`) and reused it; SA JWT TTL = **~299s** (measured: `[auth] ... auto-refresh armed (skew=60s, exp in ~299s)`). Past TTL every call 401s.
- **Fix (landed, this repo):** `scripts/canary/receiver_bulk_fanout_deploy_gate.py` — replaced the one-shot `_acquire_token()` with an exp-aware self-refreshing `_TokenProvider` (`_jwt_exp` decodes `exp` without verifying signature; re-mints `_TOKEN_REFRESH_SKEW_S=60s` before expiry; `get()` is await-free → atomic across the two arm coroutines). Threaded through `_one_call`/`_run_arm`/`_main_async`. Static env-token path never refreshes. **+5 regression tests** in `tests/unit/canary/test_deploy_gate_content_binding.py` (24/24 pass; `ruff check`/`format --check` clean on the test file; the probe is ruff-excluded via `pyproject.toml:202` `extend-exclude=["scripts/"]`).

## B. The clean run (bg bkbavvoqv, exit 0) — the GATE-2 receipt
| Arm | total | 2xx | 4xx | 5xx | 429 | success_rate | p50 | p99 | content |
|---|---|---|---|---|---|---|---|---|---|
| project | 973 | 973 | 0 | 0 | 0 | **1.0000** | 266ms | 958ms | content_ok=973 / honest_empty=0 / **violations=0** |
| section | 979 | 978 | 0 | 1 | 0 | **0.9990** | 264ms | 860ms | EXEMPT (PQ-5/OQ-3) |

- **Live-signal cross-check (G-THEATER — not the instrument's own word):** receiver CloudWatch `/ecs/autom8y-asana-service` per-minute status for the run window (07:33–07:48) = **status 200 only, ZERO 401**. Refresh fix confirmed end-to-end.
- **GATE-2 criteria:** project ≥0.99 ✓ · section ≥0.99 ✓ · SA-429 == 0 ✓ · project content-binding 0 violations ✓ (S7-GATE-FIDELITY office_phone/vertical/gid on all 973).

## C. The single section 5xx — attributed, sub-budget, NOT the receiver
- App access log: **no `HTTP/1.1" 5xx` line** for the run (the app never returned a 5xx).
- ALB metrics (window): `HTTPCode_Target_5XX_Count` (asana TG `targetgroup/autom8y-asana-service/75206e89d0fd529e`) = **0**; `HTTPCode_ELB_5XX_Count` (autom8-prod-alb, shared) = **1**.
- → The probe's 1 section 5xx was an **ELB-level transient** (load balancer returned one 5xx with no target/app error). 0.05% of 1952 calls; within the ≥99% bar; correctly excluded from receiver health.

## D. Rung-honest dispositions
- **§2A receiver capacity — DURABLE.** Clean sustained ~200/min (both arms) bulk fan-out, **zero app 5xx**, p99 ≤958ms (well under the §D 2.2s target) on the cpu=2048 substrate. The 86.8%-FAIL / 70%-18% era was the stale cpu=256 fleet; gone.
- **§2B section 400/422 — STALE-IMAGE CONFIRMED.** Zero 400/422 across smoke + both full runs. Every section non-2xx was the 401 token-expiry (now fixed), never a schema fault. The inbound handoff's 18.1% was the dead fleet. HC-7 blame REFUTED.

## E. NEW DEFECT (does NOT block GATE-2) — section read-path logs expected-absence as `level:error`
- An **unfiltered** section query (probe sends NO `section_gid` — the PQ-5 degenerate case) fans out to ~20+ per-section parquet S3 reads, **all `NoSuchKey`** (warm-lane durably PAUSED → parquets never materialized), each logged `event:retry_exhausted, level:error` (e.g. `s3_get:dataframes/1143843662099250/sections/<gid>.parquet`). The request still returns **2xx** (handled — honest_empty/on-demand).
- **Impact:** at 100rpm section × 10min this is thousands of `level:error` lines for an EXPECTED, accepted state. It would (a) inflate any error-log-based SLI / error budget, (b) **falsely trip the VG-005 / error-rate alarms** (P2-b), (c) bury real errors.
- **Routing:** feed into P2-a (self-measure must not count expected-NoSuchKey as failure) and P2-b (VG-005 alarm MUST exclude `error_type=NoSuchKey` on the paused section path). Candidate fix: downgrade expected-absent-parquet under warm-lane-paused from `error` → `info/debug`, or emit a dedicated `section_parquet_absent_expected` counter. NOT a frozen-boundary change. Recorded for the sprint; not a GATE-2 blocker (section is content-EXEMPT and returns 2xx).
- **Honesty note:** "section 2xx 99.9%" is HTTP-true, but under warm-lane-paused + unfiltered the section bodies are honest_empty/on-demand, not warm parquet reads. That is the deliberate FROZEN state, not a regression — stated so the soak does not over-read section health.

## F. What remains before the IRREVERSIBLE bundle
1. **Rite-disjoint critic (G-CRITIC)** of this receipt — the STRONG-lift (this is a same-thread synthesis = MODERATE).
2. In-repo durability + self-measure diff (workflow wf_4ea9cef0: P0-b guard, P2-a export) CI-green + PR.
3. Cross-repo handoffs applied by operator (P0-a cpu/mem floor, P2-b VG-005 alarm — the alarm must heed §E).
4. **Operator levers:** S7 composite apply / soak clock-start; 7-day soak; then R4 durable-debt (monolith→Secret-2, retire Secret-1) → R5/R6.

*Probe receipt MODERATE (self-ref). Secrets by name/metadata only (SSM param NAMES only; JWT exp read, never logged). Deployed ≠ done ≠ GATE-2-proven-clean. The first run's PASS was instrument-contaminated; this run is the honest receipt.*
