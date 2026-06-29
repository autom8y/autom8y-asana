---
type: decision
subtype: ratified-dispatch-spec
status: accepted
title: "RATIFIED — the 2026-06-18 eunomia STRONG dispatch spec (bundle §B.3, amended from the attester's seat)"
date: 2026-06-11
ratifies: .ledge/decisions/CLEAR-READINESS-BUNDLE-telos-soak-2026-06-18-2026-06-11.md §B.3
authored_by: eunomia (Pre-Clear External Corroboration procession, E5) — the SAME rite that will execute the at-clear STRONG; this ratification is the attester pre-committing to its own evidence bar
evidence_grade: MODERATE   # a spec, not a verdict. THE STRONG ITSELF IS CLOCK-GATED: it cannot be issued before 2026-06-18T15:24:21Z by anyone, including eunomia. Ceiling today: clear-readiness-RATIFIED.
clock:
  anchor_utc: 2026-06-11T15:24:21Z
  target_clear_utc: 2026-06-18T15:24:21Z
inputs_standing:
  - .ledge/reviews/EUNOMIA-INTERIM-CORROBORATION-keystone-day1-2026-06-11.md   # day-1-CORROBORATED, method-SOUND-with-findings (MF-1/2/3)
  - .ledge/reviews/EUNOMIA-E3-grades-and-custody-2026-06-11.md                  # grades + the three custody candidates
  - .ledge/decisions/SOAK-SENTINEL-PROTOCOL-telos-soak-2026-06-11.md            # the ritual under corroboration
---

# RATIFIED STRONG DISPATCH SPEC — what eunomia will demand of itself on 2026-06-18

> The bundle §B.3 sketched the dispatch; this ratification AMENDS it with the evidence bar the
> attester pre-commits to, informed by the E1 interim corroboration. **The STRONG cannot fire
> before the clock clears. All-GREEN interim findings change nothing about that.**

## 1. Standing evidence (corroborated — carries to clear, no re-derivation needed)
- **Day-1 attestation: CORROBORATED rite-disjoint** (E1, zero disputes) — at clear, only days 2–7
  + window-integrity remain to corroborate.
- **The One-Gate convergence: structurally re-derived + 2 mutation-REDs fired by eunomia's own hand**
  (write-side + serve-side, RED→revert→GREEN). At clear: re-fire **≥1** mutation-RED as a spot-check
  (substrate may have moved only if the operator authorized a deploy — then src-identity proof or
  full re-fire per the law).
- **The game-day content claims: byte-diff corroborated** (priorgood≡underfault md5-identical;
  enforce-log + 3021-gid-fails + zero-final-writes re-pulled from logs).

## 2. The at-clear re-derivation list (eunomia's own hand, never the producers' numbers)
1. **Attestation-chain audit**: all 7 day-N records exist; re-pull spot receipts for ≥3 days
   including day-7; every RESET-vs-LOG ruling re-judged against the codified law.
2. **Band, first-party**: fresh parquet pulls; unit ratio ≥0.20, offer 1332-class, gun ≤15,
   coherent ≥561 — **including gun/coherent via the canonical office_phone join** (MF-2 rider:
   the 2-frame coherence counts ARE first-party; no UV-P deferral permitted at clear).
3. **AC-6 7-day cadence**: AMP query_range over the full window (PREFIXED
   `autom8y_asana_receiver_query_outcome_total`, step ≤1800, runtime epochs, POST form-urlencoded);
   judge the BURST CADENCE; any synthetic traffic (canary/iris) LABELED and excluded from
   organic-cadence claims; any dark stretch cross-checked against the day-N pipe-smoke rulings.
4. **Alarm-state history**: rules present the whole window; any `firing` interval mapped to its
   day-N ruling; the dead-man's continuity affirmed.
5. **Window-integrity (MF-1 rider — the amendment that closes the deploy+self-revert blindspot)**:
   not just main-sha-now == 49099b12 — read the ECS service `deployments[]` + `events[]` history
   over the FULL window for ANY task-def registration beyond `:511`; any motion = either
   operator-authorized + src-identity-proven (then the rung carries) or RESET-recommended. The
   point-in-time freeze check alone is INADMISSIBLE at clear.
6. **Operational hygiene (MF-3 rider)**: the at-clear run executes from a fresh worktree at
   origin/main — never the operator's local checkout state.

## 3. The verdict, pre-committed
- **Vocabulary**: `soak-CLEARED(STRONG)` / `soak-CLEARED-WITH-CONDITIONS(items)` /
  `RESET-recommended(receipts)` — no adjectives.
- **The S2/S3-deferred ruling (pre-commitment, binding on the at-clear attester)**: S2
  (ad_reporting offer-entity) and S3 (payments/mrr congruence) are SEAM-2-gated and
  deferred-not-observed BY DESIGN — the consumer rebind is sequenced post-soak. Therefore the
  at-clear verdict scope is precisely: **the receiver-side four signals (S1, S4-exception, AC-6
  pipe+cadence, substrate stability) over a 7-day window**. A clean window earns
  `soak-CLEARED(STRONG)` **scoped to the receiver-side substrate**, which unlocks SEAM-2/Stage-B/FM-5
  per the bundle; the **full telos five-signal stays NOT-verified-realized until SEAM-2 lands and
  S2/S3 are observed live**. The verdict artifact MUST state this scope split in its header —
  rounding the receiver-side STRONG up to telos-realized is the named failure mode.
- A DISPUTE against any day-N record = RESET-adjacent → operator, both derivations side-by-side.

## 4. Binding riders for the daily ritual (days 2–7) — surfaced to the operator/sre
The E1 method findings become riders the at-clear audit will EXPECT to see adopted (their absence
is a LOG-class finding per day, not a reset):
- **a3 (MF-1)**: each day's §2(a) adds the ECS `deployments[]`/`events[]` diff vs the prior day.
- **first-party coherence (MF-2)**: each day's §2(b) derives gun/coherent via the canonical join
  from the two pulled parquets (no cross-repo UV-P).
- **worktree preflight (MF-3)**: any code-adjacent command runs from a worktree at origin/main.
(The sentinel protocol doc itself is sre's accepted record; amending it is recommended to the
operator rather than done unilaterally by eunomia — this spec is the binding instrument either way.)

## 5. Custody linkage
The three throughline candidates (One-Gate Invariant · iris pipe-smoke · soak-sentinel schema,
registered 2026-06-11, N=1 same-satellite non-promoting) each receive an N-event ONLY from
genuinely distinct applications. The at-clear STRONG, executed per this spec, is the natural
second application of the sentinel schema and the pipe-smoke method **at the same satellite** —
corroborating, still non-promoting. Promotion awaits a DISTINCT satellite, per the registry gate.
