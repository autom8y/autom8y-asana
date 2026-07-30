---
type: review
artifact_type: GATE-RECEIPT
gate: S8-1 (fixture replay — the deterministic leg of the P5 gate)
initiative: substrate-v2-epoch
date: 2026-07-30
status: proposed
session: session-20260730-141905-058c4fd7
main_sha: 6ba2a04fc0c0e2ff764d549bb497183a33f615ae
executed_at: "content verified identical to merged main (git diff origin/main HEAD --stat = empty) — receipts bind to 6ba2a04f"
ruling_lineage: "potnia S8 orchestration ruling Q1 (2026-07-30): the gate-of-record replay is the POST-S8-0-corpus run; pre-S8-0 CI greens were signal-only"
---

# S8-1 GATE RECEIPT — adversarial fixture replay (deterministic leg): **PASS**

**PREDICATE anchor (LEG-1, partial):** "P5 cutover-gate receipts clean (adversarial
fixture replay + bounded live-parity window, every divergence explained)" — this
receipt discharges the FIXTURE-REPLAY half. The live-parity half (S8-2) remains
gated on DP-4a (alarms applied) + C8 (SLA governed) — operator levers.

## Run of record

| Fact | Value |
|---|---|
| Corpus | 22/22 RC acceptance predicates (RC-A:4 B:4 C:3 D:3 E:4 F:4) + exemplar #1 (frozen wound archetype, $84,385/$79,585 divergence) + exemplar #2 (current-state anchor, $80,985, S8-0 recapture) |
| Command | `uv run python -m pytest tests/harness/substrate_gate tests/unit/substrate -q` |
| Result | **285 passed, 0 failed** (73 harness + 212 substrate-unit) in 70.13s |
| Self-discrimination (teeth-of-the-teeth) | `test_self_discrimination.py` **5/5** — the harness FAILS a silent-serving substrate and FAILS an over-refusing substrate (two-sided) |
| Content binding | working tree == merged main `6ba2a04f` (diff empty); prior green on the identical tree at PR #292 CI (24 checks) |

## Divergence ledger (fixture leg)

**Unexplained divergences: 0.**
- Exemplar #1 emits its EXPECTED divergence (the wound archetype: $84,385-vs-$79,585,
  digest-consistent DIVERGENT → RefusePayload with per-section explanation) — asserted
  BY the corpus as the RC-A-2 explained-divergence exemplar; this is the tripwire
  functioning, not a finding.
- Exemplar #2 emits NO divergence (coherent current-state anchor; v1==v2) and its
  constants are re-derived FROM THE COMMITTED BYTES (`test_fixture_parquet_bytes_
  rederive_the_pinned_constants` — value $80,985, composition, sha256 digest) — the
  bytes-vs-constant tripwire added at qa-adversary's S8-0 review.
- Measured dark-build drift (recapture receipt): exemplar #2 vs #1 = **−$3,400
  (−4.03%)**, per-section decomposed and EXPLAINED (RECEIPT-s8-0-fixture-recapture-
  2026-07-30.md) — an explained divergence, entered here for the PT-03 Q1 ledger.

## Two-sided teeth evidence

1. **Mutation probe (qa-adversary, S8-0 review):** removing the AIMD `slot.reject()`
   line flipped both 429-side tests RED while 200/500-side stayed GREEN; restored and
   verified clean vs HEAD. (Discrimination proven by live mutation, not assertion.)
2. **Saboteur trip:** the S7 corpus's deliberately-broken variants trip at 100%
   (carried receipt, QA-s7-harness-pr283); re-executed green in this run.
3. **Self-discrimination suite:** 5/5 — silent-serve of a broken input FAILS the
   harness; over-refusal of a good input FAILS the harness.

## What this receipt does NOT claim

- NOT the live-parity leg (S8-2; arms only after S8-0-merged ✓ + DP-4a applied ✗).
- NOT PT-03 (requires: parity ledger closed, rite-disjoint security critics rendered,
  capacity sign-off, P10 receipts, C8+D6b+C10 discharged).
- NOT LEG-2/3/4 of the predicate. Self-assessment altitude: **MODERATE** (self-ref cap;
  the S12 eunomia attester re-derives independently).

## Carries into S8-2 arming (ledgered)

- Budget-ledger hardening before the cap becomes a real allowance guard: corrupt-JSON
  fail-OPEN → should refuse loudly; cross-process lock; multi-unit overshoot check
  (qa-adversary LOW/INFO findings, PR #292 review).
- `_is_rate_limit_signal` coverage note for the real outbound impl injection.
- UV-P-6 discharge (real section counts → cap calibration) at window-open re-snapshot.
- O4 leg-2: window-open re-snapshot + drift verdict appended to the recapture receipt.
