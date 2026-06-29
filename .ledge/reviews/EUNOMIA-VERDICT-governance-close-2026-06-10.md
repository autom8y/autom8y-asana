---
type: review
subtype: verdict
status: accepted
title: Eunomia governance close — SNC Phase-α STRONG-cert · N=2 custodian ruling · FPC Phase-1 retro-cert · remediation executed
date: 2026-06-10
verdicts:
  snc_phase_alpha: STRONG-GRANTED
  fpc_phase1_floor: STRONG-GRANTED
  n2_promotion: HELD-AT-N1 (O-2 — same-satellite corroboration recorded, non-promoting)
  remediation_e3: EXECUTED-MERGED (MODERATE self-cap — eunomia executing eunomia's plan)
---

# EUNOMIA VERDICT — Governance Close (2026-06-10)

## 1. SNC Phase-α (#123, deployed :506/2f0e7dc) — **STRONG-GRANTED**
Independently re-derived (E1, fresh worktree off `2f0e7dc0`, producer receipts treated as hypotheses):
- tests/arch **20/20 green by MY run**; **two mutation-REDs re-fired by me**: registry prefix mutation →
  gen diff-test + t2 RED (diff pasted); rogue literal `asana-cache/project-frames/` injected at
  `client.py:31` → **t3 RED naming the exact file:line** → reverted → GREEN. The wrong-prefix read is
  structurally unaddressable at the Python boundary: a loose literal in src fails CI.
- gen-sha **byte-parity** with the vendored autom8y #490 copy: `03a6201c…b50292` both sides.
- FP-3 live smoke **5/5 under MY invocation** (MRR=1500; live object independently re-read).
- Band: `unit.mrr 723/3021` EXACT; `gun=11` in-band. HONEST PARTIAL: the reader-derived
  `coherent`/Templates figures are not reconstructible from raw parquet alone (ACTIVE classification is
  reader-layer; offer `status` null in the persisted frame) — the substrate-grounded signals + the live
  smoke through the real reader path carry the certification. Scope note: STRONG covers the Python
  boundary; TF/IAM stays DETECTION-grade until the β applies (operator).

## 2. FPC Phase-1 floor (#115) — **STRONG-GRANTED (retro-cert on the in-anger receipt)**
- The WARN **re-pulled from CloudWatch**: `2026-06-10T12:37:02Z population_receipt_below_floor
  entity_type=unit active_rows=764 mrr=0.0 warn_threshold=0.8` — fired while the cure was inert: the
  floor was the system's honest voice during the triple-defect saga. The strongest possible receipt.
- Green-path exercised live: offer `population_receipt_ok` (mrr 0.967→0.984) at 14:05Z/16:47Z.
- Substrate on main verified file:line (threshold L54, unit entry L69, both event emits L240/L242);
  the #115 test file present, **6/6 green by MY run**.
- **Calibration finding (watch-register, NOT a defect):** the unit floor still WARNs at mrr≈0.237 —
  correct behavior, but the sold band IS ~24%, so unit:mrr at threshold 0.8 over `active_rows=764`
  will WARN indefinitely. Per the FPC G-DENOM per-cell policy, the unit:mrr floor wants either a
  per-cell ratio or an ACTIVE-subset re-scoping → route to the FPC Phase-3/UK-2 context.

## 3. The N=2 promotion — **HELD AT N=1 (ruling O-2)**
Criteria quoted (§7): *"The second anchor MUST be a DISTINCT incident at a DISTINCT satellite."*
The SNC instance is genuine config-altitude generalization but shares satellite + session + saga
parentage — all three self-reference vectors at once. Promoting would leave the gate unable to refuse
any future same-satellite claim. **Recorded in the candidate spec as same-satellite corroboration,
non-promoting** (`n_applied: 1 (+1 corroboration)`); gate text preserved verbatim; promotion awaits a
genuinely distinct satellite. O-1/O-3 enumerated and rejected (O-3 = self-serving gate amendment).

## 4. Remediation E3 — **EXECUTED-MERGED** (MODERATE self-cap: eunomia executing eunomia's plan)
PR **#124** → main **`b48452d5`** (CI all green; scope = 3 test files + README + justfile only):
- CHANGE-002 `9412e814` — universal-strategy tests route through a real `DataFrameCacheEntry` +
  provider boundary stub (the Rank-1 census HIGH); 41/41 green.
- CHANGE-003 `73e2be61` — `_FakeEntry` deleted; real entry shape in matching tests; 20/20 green.
- CHANGE-004 `fc3c6f77` — §1+§2 merged, parameterized; **assertion-union GUARD pasted** (10/10 preserved); 15 collected.
- CHANGE-005 `a85ae830` — README `pre-commit install` + justfile lint→fmt pointer.
Residuals (honest): 30+ out-of-scope `_cached_dataframe` injections remain (follow-on plan needed);
the matching route itself still reads only `.dataframe` (route hardening = future src work).

## Telos ADVISORY (non-blocking)
The telos `dataframe-resolution-coherence` remains **NOT verified-realized** — five-signal gated on
SEAM-2 (C1/C2/C3), AC-6 (`receiver_query_outcome_total` absent), the valid soak (IC P1–P8), and the
`legacy_fallback` flip. The governance ledger is closed; the realization tail is operational.

## Operator levers (unchanged, surfaced)
CHANGE-001 (nightly OIDC live-smoke job) · #490/#491 approvals+applies · #486 apply+arm · β-3 canary ·
AC-6 · soak co-sign · CR-3 Stage-B · UK-2 (now also carrying the unit-floor calibration question) · γ-0 monolith anchor.
