---
type: review
report_kind: resilience-report
status: draft
slug: b1-distribution-canary-2026-06-29
title: "B-1 Per-Office Distribution Canary — Controlled Fault Injection on the Asana Insights Distributor"
author: chaos-engineer (sre rite, rite-disjoint from the GAP-1 PR-A build lineage)
date: 2026-06-29
rite: sre
phase: resilience
anchor: "autom8y-asana origin/main 6551aee0 · branch chaos/b1-distribution-canary"
upstream: "COMPLIANCE-c1-pii-deidentification-2026-06-29 (B-1 blocker, security rite)"
downstream: "Platform Engineer (B-2 office_phone uniqueness fix) · Incident Commander (activation go/no-go) · operator (export re-enable, PT-02 terminal)"
halt_above: "PT-02 (export re-enable + operator-plane un-darking are operator-terminal — NOT crossed here)"
verdict: "FAIL — the per-office distribution invariant is NOT enforced; a shared-office_phone collision silently merges office B's rows into office A's partner deck. B-1 canary LANDED; B-2 (data-side uniqueness fix) REQUIRED before re-enable."
---

# Resilience Report: Asana Insights Per-Office Distributor (B-1)

## Executive Summary

The C-1 PII safety of the partner-facing insights deck rests **entirely** on one
unproven invariant: that the Asana distributor hands each office only its **own**
de-identified rows. The compliance facet (`COMPLIANCE-c1-pii-deidentification-2026-06-29.md`
(b)/(c) R-2, (e) **B-1**) found this invariant has **no guard and no test** — the
data-plane ownership canaries stop at the authorization boundary; nothing tests the
distributor. This chaos experiment built that missing proof: a two-sided, blast-radius-
bounded distribution canary driven by controlled fault injection.

**Verdict: FAIL.** Under the known `office_phone` uniqueness hazard (two distinct offices
sharing one phone — emergent, not enforced), the distributor at `workflow.py:806`
**silently merges** both offices' rows into one bucket that **both** decks read. Office
B's office-attributable, unmasked-`office` row leaks into office A's partner report. The
canary catches it (RED arms PASS by detecting the leak) and a strict-xfail invariant
beacon names the defect machine-readably. The distributor is **resilient under unique
keys (GREEN) but fragile under a key collision (RED)** — a single latent data condition
breaches per-office isolation. **B-1 (this canary) is landed and merge-ready; B-2 (the
`office_phone` uniqueness fix, data-side / operator-terminal) is REQUIRED before any
export re-enable.**

## Scope

- **Service tested**: `autom8_asana` insights-export per-office distributor (the cross-tenant agency-BI partner deck).
- **Surfaces (real, no reimplementation)**: `distribute_per_office` (`src/autom8_asana/clients/data/_endpoints/operator.py:44`, fold site `:78`) + `InsightsExportWorkflow._fetch_all_tables` → `_fetch_table` (`src/autom8_asana/automation/workflows/insights/workflow.py:806`).
- **Environment**: test-harness only (dev). **NO prod calls, NO live export, NO operator-plane mint.** Pure fault injection.
- **Commit**: `origin/main 6551aee0` (matches the compliance review anchor exactly).
- **Experiment count**: 1 experiment, 6 arms (1 GREEN, 2 RED, 1 TEETH, 1 INVARIANT beacon, 1 SCOPE) + 1 transient teeth-proof.

## Hypothesis (Given / When / Then)

- **Given** a steady state where the operator batch has been folded into the per-office cache `self._operator_batch[table][office_phone]` (`workflow.py:140`, shape `{table_name: {office_phone: rows}}`),
- **When** office A's deck is rendered (the per-office slice read at `workflow.py:806`: `rows = self._operator_batch.get(spec.table_name, {}).get(office_phone, [])`),
- **Then** that deck contains rows belonging to office A **only** — zero rows belonging to any other office (the per-office isolation invariant; `COMPLIANCE-c1` (b) "NHC sees only its own data").

## Steady State Definition

| Signal | Steady-state value | Measurement |
|--------|--------------------|-------------|
| Cross-office rows in office A's rendered deck | **0** | `cross_office_rows(deck_a, OFFICE_A)` detector (rows whose unmasked `office` ≠ A) |
| Office A's own rows present | ≥ 1 | `[r["office"] for r in deck_a["SUMMARY"].data] == ["NHC North Wellness"]` |
| SA fleet-read invocations on the distribution path | **0** | `get_leads/insights/appointments/reconciliation_async.assert_not_called()` |

Baseline measured by **TC-GREEN** (distinct phones): both decks isolated, zero contamination — steady state holds when the distribution key is unique.

## Experiment Design

### Failure Type
**Dependency / data-integrity fault** — a key-collision on the per-office distribution key (`office_phone`), modeling the known latent hazard that `office_phone` uniqueness is **emergent, not enforced**: autom8y-data `repositories/business.py:192` `.first()` with no `ORDER BY` and no `UNIQUE` constraint (fleet memory `ebi-forwarding-confirm-golive-nogo`; `COMPLIANCE-c1` R-2 latent).

### Injection Method (the discriminating fixture — break the INPUT, never the SURFACE)
Per `discriminating-canary-doctrine` (G-THEATER forbidden): **no production file is edited.** The only thing that differs between GREEN and RED is the data-plane response **envelope** handed to the *real* `distribute_per_office`. Two faithful collision modes:

- **MERGE mode** — one phone entry carrying two office-attributed rows (faithful to the `office_phone × office × vertical` grain; `COMPLIANCE-c1` (a), `library.py:455`): `results: [{phone: SHARED, data: [A_row, B_row]}]` → `distribute_per_office` → `{SHARED: [A_row, B_row]}`.
- **OVERWRITE mode** — two same-phone entries: `results: [{phone: SHARED, data: [A_row]}, {phone: SHARED, data: [B_row]}]` → `distribute_per_office` last-write-wins (`operator.py:78` `per_office[phone] = rows`) → `{SHARED: [B_row]}` (A's own data dropped).

### Blast Radius
- **Scope**: test-harness only. MagicMock clients; `_fetch_table` makes **no** wire call (it reads only `self._operator_batch`). Zero production traffic, zero offices affected.
- **Duration**: < 1s per run (`5 passed, 1 xfailed in 0.80s`).
- **Affected users**: none. The operator plane is INERT at HEAD (`operator_insights.py:179` empty `OPERATOR_ARN_ALLOWLIST` darks the plane; `AUTOM8_EXPORT_ENABLED` unset).

### Abort Criteria (pre-registered)
- Any arm makes a real wire call or touches an SA fleet-read method → **ABORT** (would breach the no-prod-call constraint). *Result: not triggered — TC-SCOPE proves zero SA calls.*
- The fixture cannot be made to both pass (clean) and fail (collision) → **ABORT** (no teeth / vacuous canary). *Result: not triggered — TC-TEETH proves two-sidedness.*
- The collision requires editing production code to manifest → **ABORT** (G-THEATER). *Result: not triggered — only the input envelope differs.*

### Rollback Plan
Additive test-only artifact; nothing to roll back. Removing the file restores the prior state byte-for-byte. The canary alters **no** production code (`git diff` touches only the new test file + this report).

## Execution Log & Two-Sided Transcript

Run: `pytest tests/unit/canary/test_canary_b1_peroffice_distribution.py -v -rxX` @ `6551aee0`

```
tests/unit/canary/test_canary_b1_peroffice_distribution.py::...::test_tc_green_distinct_phones_zero_cross_contamination PASSED   [ 16%]
tests/unit/canary/test_canary_b1_peroffice_distribution.py::...::test_tc_red_merge_collision_leaks_office_b_into_office_a       PASSED   [ 33%]
tests/unit/canary/test_canary_b1_peroffice_distribution.py::...::test_tc_red_overwrite_collision_replaces_office_a_with_office_b PASSED  [ 50%]
tests/unit/canary/test_canary_b1_peroffice_distribution.py::...::test_tc_teeth_detector_is_two_sided_non_vacuous               PASSED   [ 66%]
tests/unit/canary/test_canary_b1_peroffice_distribution.py::...::test_tc_invariant_b1_isolation_holds_under_collision          XFAIL    [ 83%]
tests/unit/canary/test_canary_b1_peroffice_distribution.py::...::test_tc_scope_no_wire_call_no_sa_fleet_read                   PASSED   [100%]

XFAIL ...::test_tc_invariant_b1_isolation_holds_under_collision - B-2 UNFIXED: office_phone is the per-office distribution
  key but its uniqueness is EMERGENT not enforced (autom8y-data repositories/business.py:192 .first(), no ORDER BY, no
  UNIQUE constraint). The Asana distributor at insights/workflow.py:806 has NO per-row office-identity guard, so a
  shared-phone collision silently merges office B's rows into office A's partner deck...
========================= 5 passed, 1 xfailed in 0.80s =========================
```

### GREEN arm (steady state holds — distinct phones)
`TC-GREEN`: office A (`+17705551111`) and B (`+17705552222`) have **distinct** phones. After the real `distribute_per_office` fold and the real `_fetch_all_tables` read: `cross_office_rows(deck_a, "NHC North Wellness") == []` **and** `cross_office_rows(deck_b, "Rival Spine & Joint") == []`. Each deck rendered exactly its own row. **PASS — zero cross-contamination.** The distributor IS correct when the key is unique.

### RED arm (fault injection — the TEETH)
`TC-RED-MERGE`: A and B share `+17705559999`; the office-grain aggregate returns both rows under that one phone. Office A's deck renders `{"NHC North Wellness", "Rival Spine & Joint"}`; the detector returns office B's row. **The canary CATCHES the leak.** The current distributor has **no** per-row office-identity guard — it silently merges.

`TC-RED-OVERWRITE`: same shared phone, two same-phone envelope entries → last-write-wins → office A's deck renders `{"Rival Spine & Joint"}` **only** — A's own data is silently **replaced** by B's. **The canary CATCHES it.**

Transient teeth-proof (not committed) confirming the beacon is two-sided:
```
[CURRENT  workflow.py:806] office A deck offices=['NHC North Wellness', 'Rival Spine & Joint']  foreign_leak=['Rival Spine & Joint']  -> RED (leak)
[FIXED   post-B-2 guard ] office A deck offices=['NHC North Wellness']                          foreign_leak=[]                       -> GREEN
[TEETH-PROOF OK] xfail(strict) beacon is two-sided: RED today, reachable-GREEN post-B-2 -> it WILL flip XPASS->SUITE-FAIL when B-2 lands.
```

### Invariant beacon
`TC-INVARIANT-B1` (`xfail(strict=True)`): asserts the isolation invariant as a **fixed** distributor would satisfy it. **XFAILs today** (the loud, machine-readable "B-2 unfixed" signal). When B-2 lands it flips to XPASS → **strict suite-fail** → forces removal of the marker → the canary becomes a permanent live guard.

## Results

### Outcome: **FAIL** (the per-office distribution invariant is NOT enforced)

This is a *true* FAIL, not a wasted experiment: the chaos run made a **latent failure visible** (Cook 1998 [II:SRC-001 STRONG] — the failure was always present; the experiment surfaced it). The distributor passes under a unique key and fails under a key collision; per the SRE boundary-case calibration this is **"resilient under single-fault but fragile under compound-fault"** — here the compounding fault is the data-side `office_phone` non-uniqueness, which is a *live latent condition*, not a hypothetical.

### Observations vs hypothesis
The hypothesis predicted office A's deck contains A's rows **only**. Actual: under a shared-phone collision, office A's deck contains A's **and** B's rows (MERGE) or B's rows alone (OVERWRITE). The distributor distributes purely by `office_phone` with no office-identity check at the read site (`workflow.py:806`) and no de-dup at the fold site (`operator.py:78`). Hypothesis **falsified** under fault injection.

## Resilience Scorecard

| Capability | Status | Evidence |
|------------|--------|----------|
| Per-office isolation under **unique** key | **PASS** | TC-GREEN — `cross_office_rows == []` both directions |
| Per-office isolation under **key collision** | **FAIL** | TC-RED-MERGE / TC-RED-OVERWRITE — office B's row renders in office A's deck |
| Fail-closed on ambiguous distribution key | **FAIL** | No guard at `workflow.py:806` / `operator.py:78`; silently merges (no refusal, no warning) |
| No SA fleet-read fallback on the cross-tenant path | **PASS** | TC-SCOPE — `get_leads/insights/appointments/reconciliation_async.assert_not_called()` |
| Canary teeth (two-sided, non-vacuous) | **PASS** | TC-TEETH + transient proof — clean → `[]`, collision → non-empty; reachable-GREEN post-fix |

## Critical Gaps

| Gap | Impact | Priority | Remediation (owner) |
|-----|--------|----------|---------------------|
| **B-2** — `office_phone` distribution key is not uniqueness-enforced | A shared phone silently merges two offices' decks → cross-tenant PII disclosure (office B's office-attributable row in office A's partner report; `office` renders **unmasked** per `COMPLIANCE-c1` Rs-3, so the leak is immediately re-identifying). Bug Bar: **Important** (`COMPLIANCE-c1` R-2). | **P1 (blocks activation)** | Data-side: add a `UNIQUE` constraint / dedup proof on `office_phone`, **or** re-key distribution to `chiropractors.guid` (which IS unique; `COMPLIANCE-c1` (d) evidence-mechanism #2). Owner: **Platform Engineer + data owner**; ratification operator-terminal. |
| Distributor has no defense-in-depth office-identity guard at the read site | Even with B-2, the Asana distributor would silently trust the key. A per-row guard at `workflow.py:806` (drop/refuse rows whose identity ≠ the office) would make isolation enforced **at the distributor**, not merely emergent from upstream uniqueness. | P2 (defense-in-depth) | Asana-side: filter the per-office slice to the office's own identity, or fail-closed on a multi-office bucket. Owner: **Platform Engineer** (route via SEAM). |

## Failure Mode Catalog

| Mode | Detection | Impact (blast radius) | Mitigation |
|------|-----------|-----------------------|------------|
| Shared-phone MERGE | `cross_office_rows` finds a foreign-`office` row in the deck | Office A's partner deck shows office B's de-identified-but-office-attributable rows (cross-tenant disclosure) | B-2 unique key / guid re-key; + asana per-row guard |
| Shared-phone OVERWRITE (last-write-wins, `operator.py:78`) | Deck renders **only** the foreign office; the office's own data absent | Office A receives **B's** numbers and loses its own — disclosure **and** data-integrity loss | Same as above; de-dup at the fold with a collision alarm |
| Silent (no abort) | No log, no refusal at HEAD | The merge is invisible operationally — exactly the "degraded-mode-as-normal" trap (Cook 1998) | The xfail beacon + canary make it visible in CI |

## Recommendations

### Immediate (this week)
1. **Land B-1 (this canary)** as the permanent evidence artifact for the per-office isolation invariant. (Done — merge-ready on `chaos/b1-distribution-canary`.)
2. **Route B-2 to Platform Engineer + data owner**: the `office_phone` uniqueness fix is the activation-blocking remediation. The canary's xfail beacon is the acceptance test — it flips GREEN (and the strict marker must be removed) when B-2 lands.

### Short-term (this month)
1. Add the **asana-side defense-in-depth guard** at `workflow.py:806` (filter the per-office slice to the office's own identity / fail-closed on a multi-office bucket), so isolation is *enforced at the distributor*, not merely inherited from upstream key uniqueness.
2. Extend the canary to the other office-grain tables (`offer_level_stats`, `question_level_stats`) once B-3 (ADR-0040 data-owner sign-off) clears, since they too carry `× office_phone`.

### Long-term (this quarter)
1. **Compound-fault testing** (resilience-theater avoidance): pair the distribution collision with an ownership-drift fault (a churned guid + a shared phone) to test the EC-4 drift-sweep (`operator.py:144`) under collision — a failure mode neither this canary nor the data-plane canaries cover.

## Action Items

| Action | Owner | Priority | Acceptance |
|--------|-------|----------|------------|
| Fix `office_phone` distribution-key uniqueness (B-2) | Platform Engineer + data owner | P1 | `test_tc_invariant_b1_isolation_holds_under_collision` flips XFAIL→XPASS; remove the `xfail` marker |
| Asana-side per-row office-identity guard at `workflow.py:806` | Platform Engineer | P2 | A new GREEN arm asserting the distributor itself rejects/filters a foreign-office row |
| Activation go/no-go incorporating B-1 evidence + B-2 status | Incident Commander | P1 | B-2 landed + B-1 GREEN before export re-enable recommendation |
| Export re-enable / operator-plane un-darking | **operator (terminal)** | — | PT-02 — NOT crossed here |

## Handoff / Merge-Ready Rung

- **Rung**: **merge-ready** (additive test + report on `chaos/b1-distribution-canary` off `origin/main 6551aee0`; ruff check + ruff format --check GREEN; `120 passed, 1 xfailed` across the canary dir + the two related surface modules; zero production-code change). **NOT pushed, NOT PR'd, NOT merged** — per dispatch constraints.
- **Operator-terminal (NOT crossed)**: export re-enable (`AUTOM8_EXPORT_ENABLED`), operator-plane un-darking (`OPERATOR_ARN_ALLOWLIST`). PT-02 HALT stands.
- **The B-2 fix is data-side / operator-terminal** — this experiment does **not** weaken anything and does **not** paper over the defect; it names B-2 as the activation blocker the operator must clear, with the canary as the machine-checkable acceptance gate.

## Lessons Learned

The de-identification posture was *provably sufficient against patient re-identification* (grain-level, default-deny) but *unproven against office re-identification under a distribution defect* — because nothing tested the distribution boundary. "NHC sees only its own data" was **intended**, not **proven**. The single most valuable chaos artifact here is not a new failure we created, but the **visibility** we gave an always-present latent one: a shared `office_phone` was already capable of silently merging two partners' decks; now CI says so loudly, and will say so until B-2 lands.

## Attestation

| Claim | Source (origin/main `6551aee0`) | Method |
|---|---|---|
| Per-office read distributes by `office_phone`, no identity guard | `src/autom8_asana/automation/workflows/insights/workflow.py:806` | file-read |
| Batch cache shape `{table_name: {office_phone: rows}}` | `.../insights/workflow.py:135, :140` | file-read |
| Fold site last-write-wins on duplicate phone key | `src/autom8_asana/clients/data/_endpoints/operator.py:78` (`per_office[phone] = rows`) | file-read |
| `_fetch_table` makes no client call (reads only `_operator_batch`) | `.../insights/workflow.py:806-816` | file-read |
| Activity filter keeps `spend>0 OR leads>0` (fixtures survive untouched) | `.../insights/workflow.py:856-871` | file-read |
| `office`/`vertical` render unmasked → foreign `office` IS re-identifying | `COMPLIANCE-c1` (a) lines 110-114, Rs-3 | file-read |
| `office_phone` uniqueness emergent, not enforced (the B-2 root) | autom8y-data `repositories/business.py:192` `.first()` (cited by `COMPLIANCE-c1` R-2 line 213-217; fleet memory `ebi-forwarding-confirm-golive-nogo`) | citation |
| Two-sided transcript: GREEN isolates, RED catches, INVARIANT xfails | `tests/unit/canary/test_canary_b1_peroffice_distribution.py` — `5 passed, 1 xfailed` | test-run |
| No regression | canary dir + `test_operator_batch.py` + `test_insights_export.py` — `120 passed, 1 xfailed` | test-run |

**PT-02 HALT STANDS.** This is rite-disjoint sre input to the activation go/no-go. B-1 landed; B-2 required before re-enable.
