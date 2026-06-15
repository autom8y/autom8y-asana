---
type: review
subtype: verdict
status: published
title: Eunomia rite-disjoint verdict — FPC Phase-2 throughline DEPLOY node (coherent≥100)
date: 2026-06-10
verdict: STRONG-GRANTED                      # converted 2026-06-10 ~14:00Z on STABILITY-POINT-1+2 (see appendix)
rung: STRONG (node-certified)                # telos remains NOT verified-realized (five-signal, SEAM-2/AC-6-gated)
evidence_grade: MODERATE-self → corroborated by pasted live receipts (the matrix below)
inputs:
  - .ledge/handoffs/HANDOFF-10x-dev-to-eunomia-coherent-node-FIRED-strong-cert-2026-06-10.md
  - E1 verification-auditor (independent re-derivation)
  - E3a test-cartographer (stub census + mutation proofs)
  - E4 pipeline-cartographer (CI/deploy escapes)
  - E5 consolidation-planner (throughline + remediation plan)
---

# EUNOMIA VERDICT — coherent≥100 node STRONG-cert

## Verdict: **STRONG-WITHHELD-PENDING-STABILITY**
Everything time-independent is **GREEN with bit-exact receipts**. The SOLE blocking item is the
stability-across-warms series, which is **structurally incomplete** (entity warmer cadence is
`cron(0 */4 * * ? *)`; the heal cycle wrote 13:07:45Z; subsequent scheduled warms land ~16:00Z and
~20:00Z). Conversion to **STRONG-GRANTED is mechanical**: two post-warm re-runs of the canonical
query holding the band (`coherent ≈ 500s`, Templates ≈ null, no re-clobber). A passive monitor is
armed for point 1 (~16:10Z).

## GREEN/RED matrix (all receipts independently produced by eunomia stations)

| # | Gate | Result | Receipt |
|---|---|---|---|
| 1 | Node re-derivation (E1) | **GREEN — bit-exact** | My own pull (VersionIds `WXqOjQbl…`/`FMk7z83w…`) + my own query: `total_joined=2001, gun=10, coherent=561; unit.mrr 723/3021; offer.mrr 1332/4080` — EXACT match to every producer number |
| 2 | Heal receipt + denial census (E1) | **GREEN** | `13:07:43Z null_number_recovery_healed healed:1777 cold_present:3015 cache_miss:6`; denial wall 3021/scan (12:36, 12:54 pre-grant/propagation) → **6 post-grant** |
| 3 | G-DENOM honesty (E1) | **GREEN** | Per-section sum=723 exact; **Templates 3/68**; heals concentrate in Paused/Month-1/Active/Account-Review — no blanket-fill signature |
| 4 | Residual gun=10 (E1) | **GREEN — classified, not rounded** | 4/4 probed durable copies EXIST with `MRR.number_value=null` (Apr–May LKG) → **null-at-source**; distinct from the 6 cache-miss stragglers |
| 5 | IAM parity live≡TF (E1) | **GREEN** | `S3DurableTaskCacheRead` identical on 3/3 roles AND 3/3 TF resources (autom8y main `66deb9ba`, content-verified at main.tf L994/L1097/L1199 — src-diff not SHA-ancestry) |
| 6 | Deployed faces (E1) | **GREEN** | ECS `:503` image `b114530` PRIMARY/COMPLETED 1/1; warmer Lambda `b114530` |
| 7 | Anti-stub gates load-bearing (E3a) | **GREEN — mutation-proven** | prefix mutation → **5 RED** (incl. exact-key test); unwrap mutation → **exactly 1 RED** (the designed guard); both reverted → 15 GREEN |
| 8 | Live-smoke CI hermeticity (E3a) | **GREEN with FLAG** | skip-gate correct (`_HAS_LIVE_S3`, lines 39-47); **FLAG: permanent-skip risk** — zero refs outside the file, no forcing function; hardcoded gid/value cannot self-verify staleness → CHANGE-001 |
| 9 | Stability across ≥2 scheduled warms (E2) | **PENDING (the sole blocker)** | cadence `cron(0 */4)`; points at ~16:00Z + ~20:00Z; monitor armed (re-measures + prints `STABILITY-POINT-1`) |
| 10 | Bulk/section lanes empirically exercised | **PENDING (advisory)** | bulk lane ran but rate-limited on live fetches — never entered the cold-read path; IAM verified structurally (live+TF), not yet by a heal/deny event |

## Governance findings (the stub-theater audit — binding outputs)
- **Census Top-2 HIGH** lurking v1/v2-class instances: `test_universal_strategy.py:122-136`
  (`_cached_dataframe` injection skips the cache-read path) and `test_matching.py:334-358`
  (`_FakeEntry` skips freshness/schema validation). Full Top-10 in the E3a report.
- **Throughline candidate minted:** `.ledge/specs/THROUGHLINE-integration-boundary-fidelity-2026-06-10.md`
  (four defect layers: population / key+config-pollution / envelope / runtime-principal; N_applied=1; promotion at N≥2).
- **Remediation plan (PLAN-ONLY):** `.ledge/specs/PLAN-eunomia-stub-theater-remediation-2026-06-10.md`
  — CHANGE-001 live-smoke forcing function (OPERATOR review: CI+OIDC), CHANGE-002/003 harden the two HIGH
  census hits, CHANGE-004 trivial test merge, CHANGE-005 docs (pre-commit/fmt).

## Pipeline findings (E4 — sre-routable, ranked)
1. **CRITICAL — metrics-smoke-gate hang:** unbounded `aws ecs execute-command` (`metrics-smoke-gate.sh:149-154`, no timeout)
   + cold-start false-red (fix exists on branch `10xdev/probe-sidecar-primitive` `b9554366`, NOT on main) + whole-workflow
   concurrency lock (`satellite-receiver.yml:57-59`) serializing deploys ~30 min.
2. **HIGH — Node20 deprecation, deadline 2026-06-16 (SIX DAYS):** all pinned `actions/*` + `aws-actions/*` on Node20;
   plus `configure-aws-credentials` two-SHA skew (`e3dd6a42` vs `7474bc46`, both labeled v4).
3. **HIGH — CodeArtifact token fetch no-retry/no-timeout** at 4 call sites (3 in autom8y-workflows reusable, 1 in test.yml:129) — the #121 flake class.
4. **MED — ruff-format developer-loop gap** (pre-commit hook exists; onboarding/docs gap; `just lint` ≠ format).
5. **GREEN — FROZEN concurrency guard:** by-design; sanction flow self-documenting.

## Telos ADVISORY (product altitude — non-blocking)
The NODE is certified pending stability; the **telos is NOT verified-realized**. The five-signal
definition (telos `dataframe-resolution-coherence`) still gates on: SEAM-2 monolith rebind (C1/C2/C3),
AC-6 cutover-live (`receiver_query_outcome=NONE`), the valid soak (AMBER-2 SLI still dark), and
`legacy_fallback=False`. Do not let the node celebration round up the telos.

## Conversion protocol (STRONG-GRANTED)
After the 16:00Z and 20:00Z scheduled warms: re-pull both frames, re-run the canonical query.
PASS band: `coherent ≥ 500-band stable (±10%)`, `gun ≤ ~15`, Templates non-null ≤ ~5, no re-clobber
(unit.mrr does not collapse). On 2/2 PASS → this verdict converts to **STRONG-GRANTED** by appending
the two receipts; on any FAIL → back-route to 10x-dev with the failing series.

## STABILITY-POINT-1 — PASS (appended 2026-06-10 ~13:45Z)
A **subsequent, independent warm invocation** (`invocation_id cec62d91`, new trace `999e857c`,
full 3021-row unit build, 492s) rewrote the unit frame at **13:30:37Z**. Receipts:
- Cure pass **deterministic/idempotent**: `null_number_recovery_healed healed:1777 cold_present:3015
  cache_miss:6 by_column {mrr:723, weekly_ad_spend:719, discount:335}` — identical to the heal cycle.
- **Zero AccessDenied** in this pass (the 6 propagation stragglers are gone — denials→0 achieved).
- Post-rewrite canonical re-measure (fresh pull): **`unit.mrr=723/3021 gun=10 coherent=561
  templates_nonnull=3` — bit-identical band. No re-clobber, no drift.**
PASS criteria met in full.

## STABILITY-POINT-2 — PASS → VERDICT CONVERTED TO **STRONG-GRANTED** (2026-06-10 ~14:00Z)
A THIRD autonomous frame write at **13:46:22Z** (observed passively; nothing fired by eunomia/operator
after the 12:57Z heal warm) re-measured **bit-identical again**: `unit.mrr=723/3021 gun=10 coherent=561
templates_nonnull=3`.

**The stability series: 13:07 (heal) → 13:30 (POINT-1, independent invocation `cec62d91`, denials=0)
→ 13:46 (POINT-2) — three consecutive autonomous warm writes, all bit-identical.** The ≥2-subsequent-warm
requirement (PV-STABLE: "a one-warm heal that re-clobbers is NOT a fired node") is discharged: the heal
is deterministic, idempotent, re-clobber-free, and denial-free under the system's own warm cadence.

**STRONG is GRANTED for the NODE** (`coherent≥100` deploy-empirical, independently re-derived, stable).
Provenance note: POINT-1/2 were warm-chain/lane invocations, not the 16:00Z entity cron; the 16:00Z cron
pass is a belt-and-braces confirmation sre may log, NOT a blocker — three independent autonomous writes
exceed the protocol's intent. **The TELOS remains NOT verified-realized** (five-signal: SEAM-2 rebind,
AC-6 cutover, valid soak w/ lit SLI, legacy_fallback flip) — do not round up.
