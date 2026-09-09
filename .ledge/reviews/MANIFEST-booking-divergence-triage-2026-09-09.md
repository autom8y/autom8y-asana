---
id: MANIFEST-booking-divergence-triage
title: Booking-corroboration divergences, triaged BY OFFICE
status: COMPLETE — read-only; nothing mutated, nothing deployed
date: 2026-09-09
generated_at: 2026-09-09T15:51:45Z
seat: calendar-integration-locus (d5861864), rite `sre`
authority: operator, 2026-09-09 — "GO triage the 21 post-recovery divergences by office"
consumer: the operator (R-88 named-consumer rule); and the name-the-client seat closing clause (b)
---

# MANIFEST — booking-corroboration divergences BY OFFICE

## §0 REDACTION NOTICE — OPERATOR RULING, 2026-09-09
**Client office NAMES are withheld from this record by operator ruling.** Offices appear as stable
`office-<8hex>` tokens keyed to their GUID prefix.

**Nothing is lost and nothing is unfalsifiable.** The join is fully reproducible: each token's 8-hex
prefix resolves against `.ledge/reviews/commission-clawback-2026-08/registry/chiropractors.json`
(1,420 rows, `guid` -> `office`). Anyone with repo access can re-derive every name in one lookup; the
names simply are not written here.

**This seat argued against the redaction** — naming the office IS the finding, and a token-only record
is adjacent to the very discriminator-destruction this document criticises in §6. **The operator ruled
otherwise with that tradeoff stated, and the ruling governs.** Recorded so the disagreement is visible
rather than silently resolved.


**A divergence is a SILENT LOSS**: a terminal ledger row (`posted` or `dead_letter`) in the
`booking|live` keyspace that EBI believed was handled, which the canonical data service reports is
**ABSENT from `nhc_production.appointments` ground truth.** `reconcile_handler.py:339-343` logs it
`CRITICAL` and stamps the row `diverged`.

## §1 ★ THE HEADLINE — THE EVIDENCE IS BEING REAPED

**The charge said 21. The ledger holds 6.** Both are true.

`EBI_BOOKING_DIVERGED` counts **events**; the ledger holds **current state**, and the table has
**TTL ENABLED on attribute `ttl`** (`describe-time-to-live` → `ENABLED`) with a **~7-day horizon**.
**≈15 of 21 divergences have already been deleted.** Nothing else recorded them: the divergence log
line carries **only `ledger_status`** — deliberately *"Never PII"*, so it never named an office.

> **The only artifact that ever named WHICH OFFICE lost a booking is the ledger row, and it is on a
> 7-day self-destruct.** This manifest is the first thing that names them, and it exists ~4 hours
> before the next one disappears.

**⏳ Row 1 (`office-4416989f`) reaps at 2026-09-09 19:21:31Z — 3.5 hours from generation.**

## §2 THE SIX, BY OFFICE

| # | office | guid | ledger status | created (UTC) | **REAPS (UTC)** | redrive attempts | last_error | allowlist |
|---|---|---|---|---|---|---|---|---|
| 1 | `office-4416989f` | `4416989f-***` | `posted` | 2026-09-02 19:21:31Z | **2026-09-09 19:21:31Z** | 0 | no | on |
| 2 | `office-ca70baa8` | `ca70baa8-***` | `posted` | 2026-09-03 01:34:30Z | **2026-09-10 01:34:30Z** | 0 | no | on |
| 3 | `office-8e56f6e1` | `8e56f6e1-***` | `dead_letter` | 2026-09-03 05:28:46Z | **2026-09-10 05:28:46Z** | 5 | yes | on |
| 4 | `office-d167d635` | `d167d635-***` | `posted` | 2026-09-04 00:30:39Z | **2026-09-11 00:30:39Z** | 0 | no | on |
| 5 | `office-4416989f` | `4416989f-***` | `posted` | 2026-09-04 11:44:23Z | **2026-09-11 11:44:23Z** | 0 | no | on |
| 6 | `office-d167d635` | `d167d635-***` | `posted` | 2026-09-08 01:18:01Z | **2026-09-15 01:18:01Z** | 0 | no | on |
**4 distinct offices · 6 rows · all 6 ON the live allowlist · 5 `posted`, 1 `dead_letter`.**

| office | rows |
|---|---|
| `office-4416989f` | 2 |
| `office-d167d635` | 2 |
| `office-ca70baa8` | 1 |
| `office-8e56f6e1` | 1 (the `dead_letter`) |

### ★ ROW 3 IS C-13
`8e56f6e1-***`, pk `bd875254…`, reap **2026-09-10 05:28:46Z** — matching the C-13 reap instant in the
record exactly. **C-13's dead-letter row is a corroboration divergence, and the office is
``office-8e56f6e1``.** The record has carried it as *"the dead-letter row bd875254…"* for
days. **It now has a name.** It is also the only row with `redrive_attempts = 5` and a `last_error` —
i.e. the redrive was tried five times and could not recover it.

### ★★ WHY ROW 3 IS MORE THAN "C-13 GOT A NAME"
`8e56f6e1-ed00-4a66-b349-7340948cad20` is **on the live 42-entry allowlist at `origin/main`** — verified.
So **`office-8e56f6e1` is an ACTIVATED, ALLOWLISTED, live-POSTing client.** This is **not** a
routing exclusion, **not** an un-enabled office, and **not** a dry-run artifact. **It is a delivery
failure to an enabled paying-plane customer — five redrive attempts, unrecoverable, and nobody was ever
alerted by name.** *(Framing owed to the `autom8y-asana-8f` seat.)*

### WHAT THE SPLIT MEANS
- **`posted` (5)** — *we believed it landed.* EBI POSTed, got a success, stamped terminal. Ground truth
  disagrees. **This is the worse class**: nobody was ever alerted.
- **`dead_letter` (1)** — *we knew it failed and the redrive could not recover it.* Already visible.

## §3 CLAUSE (b), TWO-SIDED, ON DATA THAT ALREADY EXISTS
Clause (b) wants a kind-named loss count plus a past-dated row re-driven to a TYPED terminal. **This
manifest supplies the naming half from existing production state — no deploy, no code, no R-35
dependency.** Contrast clause (a), which this seat verified is currently **unsatisfiable**: 0 of 798
`booking_completed` events in 30 days carry an office, guid, or client token (controls: 798/798 on
`status` and `booking`).

**So the two clauses are in opposite states: (a) needs #2073 to deploy; (b) can be named today.**

## §4 METHOD, AND A NEAR-MISS WORTH RECORDING
- **Join, not shape.** GUIDs resolved by **set-membership against the 1,420-row chiropractor registry**
  (`.ledge/reviews/commission-clawback-2026-08/registry/chiropractors.json`). **6/6 resolved.**
- **★ A VACUOUS RESULT WAS CAUGHT BEFORE IT REACHED THIS TABLE.** The first allowlist check regexed
  `allowlist = [...]`. The value is a **comma-separated STRING**, not a list, so the match failed, the
  set was **empty**, and every row scored `on_allowlist=False`. **An empty reference set makes
  everything False.** Caught only because the parse asserted. Redone against the parsed value with
  **two-sided controls** — a known member returns `True`, a fabricated GUID returns `False` — after
  which all six read `True`. *An earlier, looser grep over the whole tfvars returned `True` for the
  wrong reason (it swept unrelated GUID lists). **Both readings were void; only the third is cited.***
- **Scan completeness:** `ScannedCount 543`, **no `LastEvaluatedKey`** — the table was fully traversed.
- **PII posture:** payloads carry `phone`, `email`, `appt_time`, `office_phone`. **None appears here.**
  GUIDs are truncated to the 8-hex `redact_uuid` safe form; pks to 8 chars. Office names are business
  identifiers, not personal data.

## §5 OPEN — NOT RESOLVED HERE
1. **★ 15 reaped divergences are unrecoverable from the ledger — and reconstruction is CONSTRAINED.**
   The reconcile lambda's CloudWatch logs run 90 days, **but `reconcile_handler.py:339-343` emits the
   diverged event carrying ONLY `ledger_status`** — deliberately *"Never PII"*. **The office name is not
   in that event.** Reconstruction must come from a DIFFERENT event that carries the guid; **if none
   does, the 15 are gone, and that absence is itself the finding rather than a failed attempt.**
   Not tested. *(Constraint identified by the `autom8y-asana-8f` seat from this manifest's own §1.)*
2. **~~Allowlist 18 vs 42.~~ RESOLVED — and the error was mine.** The live allowlist is **42**, and
   there is no discrepancy to explain. **I read a stale checkout.** Blob discriminator applied:
   my working copy of `production.tfvars` is `5cc6d931…` (variable at `:153`, **18** GUIDs);
   `origin/main` is `01889354…` (variable at `:160`, **42** GUIDs). **The blobs DIFFER ⇒ genuine
   head-drift, and both line anchors are correct at their own ref.** My autom8y checkout is behind
   `origin/main` by several commits touching that file. **42 is current; 18 was never a live value
   at HEAD.** Caught by the `autom8y-asana-8f` seat cross-checking; I verified it own-hands rather
   than accepting the correction, which is how the drift (rather than a mis-citation) was identified.

   **Re-verified against `origin/main`:** all four diverged GUIDs — `4416989f`, `ca70baa8`,
   `d167d635`, `8e56f6e1` — are present in the **42-entry** list. The `allowlist: on` column stands,
   now cited against the correct ref.
3. **`is_paying = 0` on all four offices** in the registry snapshot (dated 2026-09-07, built for a
   clawback review). **Deliberately NOT asserted as a business fact** — the field's semantics and the
   snapshot's currency are both unverified. **If it is accurate, all four losing offices are non-paying,
   which changes the commercial reading entirely. Operator question, not a finding.**
4. **Whether these six SHOULD have landed.** A booking correctly refused upstream would look identical
   here. This manifest names divergences; it does **not** claim a booking was lost.
5. **No cure is proposed.** Re-driving a past-dated row is never automatic (RETRO), and any
   customer-visible outbound act sits on the never-grantable floor.


## §6 ★ THE STRUCTURAL FINDING THIS TRIAGE SURFACED
**"Never PII" on the alert line is correct in isolation.** Its *consequence* is that the **only durable
place an office name could live was a row carrying a deletion clock.** The privacy rule and the retention
rule are each defensible alone; **together they guarantee that the identity of a lost booking survives
exactly seven days and then is not recoverable from anywhere.**

This is the **discriminator-destruction class** the substrate lane named — *absent*, *unknown* and *not
applicable* collapsing to one symbol — **except the write that destroys the distinction here is a
DELETION CLOCK rather than a literal.** No single component is wrong. The composition loses the fact.

## §7 METHOD ERRORS IN THIS TRIAGE — THREE, ALL THE SAME SHAPE
Recorded because the shape repeated within one task and only one instance self-caught.
1. **Empty set from a failed parse.** Regexed `allowlist = [...]`; the value is a comma-separated
   **string**. Match failed → empty set → every row scored `False`. **Caught by an assert.**
2. **Over-inclusive grep.** A looser sweep over the whole tfvars returned `True` for the wrong reason
   (it swept unrelated GUID lists). **Caught by re-doing it precisely.**
3. **Right object, WRONG REF.** Read `production.tfvars` from a **stale local checkout** and reported
   18 as a live value. **Caught only by a peer cross-check**, then confirmed by the blob discriminator.

> **All three are "the parse succeeded against the wrong object."** Two were caught by my own controls;
> **the third needed a second seat.** An assert defends against a failed parse. **Nothing internal
> defends against reading the wrong ref — only a disjoint reader does.**
