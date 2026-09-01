---
type: spec
artifact_subtype: landing-receipt-schema
initiative: close-the-activation-loop
sprint: S-9
workstream: P5a
repo: autom8y-asana
rite: 10x-dev
author: architect (10x-dev)
in_sprint_critic: qa-adversary (10x-dev)
disjoint_critic: verification-auditor (eunomia)
consumer: S-10 change-warden (dre) via edge E-11 / handoff H-3
date: 2026-09-01
evidence_grade: MODERATE
status: draft-for-disjoint-certification
---

# SCHEMA — Landing Receipt (GATE-1)

> The instrument S-10's disjoint certifier holds. This document defines
> **mechanically** what *"three ATTRIBUTED routed bookings observed clean"* means
> per clinic — and, at least as importantly, what **"clean" EXCLUDES**.
>
> Implementation: `scripts/certification/landing_receipt.py`
> Parameter surface: `scripts/certification/predicate.toml`
> How to run it without talking to anyone: `scripts/certification/RUNBOOK.md`

---

## §0 The one thing to read if you read nothing else

A clinic's `LANDED` verdict under the shipped default configuration is an
**AD-FUNNEL** reading, not a **FORWARDING-INTEGRATION** reading. The predicate of
record has no booking-source leg, so the harness faithfully counts bookings
written by any stack — including the legacy monolith, which runs whether or not a
clinic's email forwarding has ever worked.

Measured live 2026-09-01 over the window `2026-08-02 →`:

| reading | clinics reaching 3 |
|---|---|
| `eligible` (any writer — the ad funnel) | **41** of 90 |
| `eligible_via_email_booking_intake` (the forwarding integration) | **3** of 90 |

Both numbers are true. They answer different questions. Every receipt carries
both, on its face, and names which one supports which claim. See §6.

---

## §1 Predicate of record and its parameterisation (CE-4)

**Entry state.** G-3 — the operator's predicate re-ratification word — is
**UNSPOKEN** as of 2026-09-01. Per `close-the-activation-loop.shape.md` CE-4
(SOFT edge), this schema is built against **ATTRIBUTED**, the verified-in-substance
reading (`.sos/wip/CONSULT-silence-is-a-defect-north-2026-09-01.md:167-177`,
ADDENDUM A Collision 2).

**The CE-4 contract.** The predicate wording is carried as an *explicit
parameter*, never as a hard-coded assumption. A ratification landing on different
words is a **config change**, not a rebuild:

| If G-3 lands on… | Do this in `predicate.toml` | Code change |
|---|---|---|
| the same words | `wording_status = "RATIFIED"`, set `ratification_anchor` | none |
| different wording, same meaning | replace `wording_of_record` verbatim | none |
| ROUTED (drops "ATTRIBUTED") | `legs.attributed.enabled = false` | none |
| a count other than three | `predicate.required_count = N` | none |
| a forwarding-only reading | `scope.booking_source.mode = "include"` | none |

Every receipt stamps `predicate.fingerprint` = `sha256(predicate.toml)[:16]`, so a
receipt is never legible against a predicate other than the one that produced it.
A receipt produced under a non-default config also prints its
`disabled_switches` list in the header. **The predicate cannot be quietly
widened.**

`wording_status` is itself on every receipt. Until G-3 is spoken it reads
`UNRATIFIED-VERIFIED-IN-SUBSTANCE`, which is the honest state and which S-10's
`entry_criteria` treat as HARD (unlike S-9's SOFT).

---

## §2 The unit of counting: a BOOKING, not a row

**A row is not a booking.** The dual-write path records one booking as two
`appointments` rows — the `email-booking-intake` row (naive local start) and the
`reviewwave` row (the same instant rendered `...Z`).

Measured 2026-09-01: **367** near-simultaneous same-`(clinic, contact)` row pairs
exist in the window. Counting raw rows inflates a clinic's soak by roughly 2x on
this path alone. Nation of Wellness's single booking is present as **two** rows
(18229605 / 18229606) — a row-counting harness would report Nation at 2-of-3 on
one booking.

**Dedup rule.** Two rows collapse into one booking when ALL hold:

1. same `appointments.office_phone`
2. same `appointments.phone` (the contact)
3. `|Δ created| ≤ created_tolerance_seconds` (default **300**)
4. `|Δ resolved start instant| ≤ start_tolerance_hours` (default **24**)

Conditions 3 and 4 are **both** required, and each is load-bearing:

- Without (4), appts `18194750` (start 2026-08-04) and `18194751` (start
  2026-08-19), created 56 s apart, would wrongly merge — a blanket collapse.
- Without (3), a patient's genuine repeat visit would merge.

Verified against every known pair: `18229605/18229606` (4 h apart in
representation) collapse; `18231179/18231180` (7 h) collapse; `18235669/18235670`
(7 h) collapse; `18195228/18195229` (identical) collapse; `18194750/18194751`
(15 days) do **not**. Teeth T5 and T6 assert both directions.

The surviving row keeps `cluster_booking_sources` — the set of `source` values
across the whole cluster — so collapsing never destroys the evidence of which
stack wrote the booking.

---

## §3 Legs. A booking is countable when every enabled leg passes.

Refusals are **reason-coded** (the R-4 grammar): a refusal always names the first
failing leg and lists all of them. There is no bare "no".

### ROUTED — it is a real booking whose contact is in our funnel

| code | check | maps to |
|---|---|---|
| `R1-appt-type` | `appointments.type = 'appt'` | — |
| `R2-contact-present` | phone non-empty OR lead email non-empty | ad-lead gate **P2** |
| `R3-lead-resolves` | contact resolves to a `leads` row | ad-lead gate **P3** |
| `R4-start-parseable-and-future` | `start_datetime` parses in one of the three stored dialects AND `start > created` | ad-lead gate **P1** |

### ATTRIBUTED — PATH-A ONLY

| code | check | maps to |
|---|---|---|
| `A1-source-id-present` | `leads.source_id` is not null/empty | gate **P4a** |
| `A2-ad-join` | `source_id ∈ ads.ad_id` | gate **P4b** |
| `A3-path-a-chain-complete` | `ads → adsets → campaigns → chiropractors` all resolve | — |
| `A4-path-a-office-congruent` | campaign-side `chiropractors.office_phone` **==** `leads.office_phone`, exact string | gate **P5** (path-a) |

The chain, verbatim from `predicate.toml`:

```
leads.source_id -> ads.ad_id -> adsets.adset_id -> campaigns.campaign_id
                -> campaigns.chiropractor_id -> chiropractors.guid
                -> chiropractors.office_phone
```

**Exact equality, not normalised.** Measured 2026-09-01: 1066/1066 attributed
window rows match exactly; **0** match only after digit normalisation. Loosening
to normalised comparison would widen the gate with no observed population to
justify it. (Corroborates the ad-lead-gate sitting §3: "path-a equality exact
1,060/1,060, zero format drift".)

### CLEAN — what "observed clean" EXCLUDES

| code | excludes | why, with its evidence |
|---|---|---|
| `C1-status-real` | status ∈ {`cancelled`, `no_show`, `system`} | A cancelled or no-show booking is not an observed-clean landing event. **Statuses are normalised** (lowercase, `-`→`_`): the live vocabulary carries BOTH `no-show` (130) and `no_show` (26); a verbatim comparison leaks 26 rows. |
| `C2-not-duplicate` | rows absorbed by an earlier cluster member | §2. 367 near-simultaneous pairs in the window. |
| `C3-clinic-identity-coherent` | `appointments.office_phone ≠ leads.office_phone` | **5** attributed window rows violate this — the booking is filed at one clinic while its lead is owned by another. A receipt for clinic X cannot rest on a row whose own two identity fields disagree about X. |
| `C4-clinic-not-internal` | clinic office phone ∈ {`+12488025832`} | The internal/agency phone is not a client integration. |
| `C5-clinic-resolves` | office phone that does not resolve to exactly one `chiropractors` row | An ambiguous clinic identity is an ambiguous receipt. |
| `C6-within-window` | `created < window.since` | A receipt is always scoped to a window. C6 has no off-switch: a window-less receipt is an unbounded claim. |

### SCOPE — which booking PATH is being counted

| code | check |
|---|---|
| `S1-booking-source-in-scope` | under `mode="all"`: always true. Under `mode="include"`: the booking's **cluster** source set intersects `include`. |

Scope is deliberately **not** a "clean" leg. A scope refusal is not a defect in
the booking; it is the certifier having chosen a narrower claim. Keeping it
separate stops a scope refusal from ever reading as a data-quality finding.

---

## §4 Declared NON-exclusions

As load-bearing as §3. These are things a reader might assume are filtered and
which deliberately are **not**. Each surfaces as a provenance **flag**, never as a
refusal. Converting one into a refusal is a predicate change requiring an operator
word — not an edit.

| what | refuses? | why not |
|---|---|---|
| far-future start (the 2027 rows) | **no** | **R-3, ratified**: no horizon cap. The client's own calendar settings govern how far out booking is allowed; our duty is to READ ACCURATELY. The 2027 dates are a parser defect to be cured at the parser, never masked by a filter. The Mansour 2027 rows refuse here on **attribution** — and that is the correct reason. Tooth T3 asserts it: if that row ever refuses on a date leg, the harness has grown the filter R-3 prohibits. |
| inactive campaign (`status=0`, adset `TESTING`) | **no** | The ratified gate (R-2) has no campaign-status leg. Watch-flag carried from CONSULT:177 — if the gate ever grows one, soak booking #1 stops passing. |
| synthetic lead (`leads.platform='test'`) | **no**, flag `F-SYNTHETIC-LEAD` | The activation apparatus mints attributed test leads **by design**. Soak booking #1 (lead 329753) is one. Refusing it would refuse the very booking the predicate names as good. Counted **and** flagged; the count appears in every receipt's boundary block, and the renderer shouts when *all* members are synthetic. A synthetic-free claim is a NARROWER claim — the certifier subtracts and narrows explicitly; the harness never narrows silently. |
| booking `source` | **no** | See §6 — it is a proxy for provider dialect, not the dialect. |
| naive timestamp representation | **no**, flag `F-TZ-AMBIGUOUS-START` | See §5. |

---

## §5 Known representational conflations, implemented verbatim and flagged

`start_datetime` is stored in **three** dialects. Measured over the window
(2,731 `type='appt'` rows):

| dialect | example | count |
|---|---|---|
| UTC-Z | `2026-08-31T14:00:00Z` | 1672 |
| naive local | `2026-08-31T10:00:00` | 1018 |
| explicit offset | `...+00:00` | 41 |

The ratified `P1` leg compares the parsed start against `created` (a UTC
timestamp) **regardless of dialect**. For naive rows this conflates local and UTC.
The harness implements the ratified semantics exactly and **flags** the
conflation (`F-TZ-AMBIGUOUS-START`) rather than silently correcting it — there is
no clinic timezone table to correct it with, and inventing one inside a
certification instrument would be a silent predicate change.

Practical consequence: a naive-form booking scheduled within ~8 h *after*
`created` could pass or fail `R4` depending on the clinic's offset. Every affected
member is enumerated by `appt_id` in the receipt's boundary block.

---

## §6 What a landing receipt does NOT certify

Printed on every receipt. Reproduced here because it is the schema's substance,
not its footer.

1. **That these bookings arrived via the FORWARDING INTEGRATION** — unless
   `scope.booking_source.mode='include'` was set. This is the most likely
   over-certification in the instrument (§0). Under the shipped default, `LANDED`
   is an ad-funnel reading.
2. **That the booking was KEPT.** Status is read at query time; a later
   cancellation is not retro-applied to an issued receipt.
3. **That the clinic's integration was ACTIVE for the whole window.** `window.since`
   is an *operator-supplied parameter*; the database carries no per-clinic
   activation date. A receipt is only as tight as the window it was given, and it
   says so.
4. **That the EBI witness ledger ran.** This harness reads the booking substrate
   only. Witness evidence is S-1's and is a separate evidence leg (H-4).
5. **That the provider-format rule library parsed these mails correctly.** Parser
   correctness is not observable from these rows.
6. **`>=3 distinct PROVIDER DIALECTS`** (S-10 exit criterion 2) **cannot be
   discharged from this harness.** `appointments.source` (`reviewwave` /
   `email-booking-intake` / `ghl` / `dashboard` / `calendar`) distinguishes the
   *writing stack*, not the *provider dialect*. The dialect lives in the source
   email's format and is not represented in this database — the same structural
   limit the ad-lead-gate sitting recorded for EDD typing ("EDD typing is NOT
   representable in the DB", §3). **S-10 must source dialect evidence elsewhere.**
7. **Any refused row's real-world truth.** A refusal means "not usable as landing
   evidence", NOT "not a real appointment".

---

## §7 Receipt shape

```
receipt_kind        landing-receipt
schema              SCHEMA-landing-receipt-2026-09-01
generated_at_utc
predicate           { id, wording_of_record, wording_status, ratification_anchor,
                      required_count, fingerprint, config_source, disabled_switches[] }
attribution         { path: "path-a", chain, retired_substrate[],
                      guard: ARMED|NOT-ARMED, guard_checks[] }
clinic              { office_phone, guid, office, account_status, resolves_to_n_rows }
window              { since, since_provenance }
scope               { booking_source_mode, booking_source_include[], note }
verdict             LANDED | NOT-LANDED
counts              { rows_scanned, eligible, required, shortfall, refused,
                      refused_by_first_failing_leg{}, 
                      eligible_via_email_booking_intake, ..._appt_ids[] }
members[]           per booking: appt_id, created, start_verbatim, start_dialect,
                    status, booking_source, cluster_booking_sources[],
                    clinic_office_phone, contact(masked), lead_id, lead_initials,
                    lead_email(masked), lead_platform, ad_id, adset_id, campaign_id,
                    chiropractor_guid, campaign_office_phone, legs{}, flags[],
                    absorbed_duplicate_appt_ids[]
refusals[]          per row: appt_id, created, first_failing_leg, all_failing_legs[],
                    status, booking_source, lead_id, lead_initials
boundary            { synthetic_lead_members, timezone_ambiguous_members,
                      booking_sources_observed, forwarding_integration_subset,
                      not_certified[] }
```

**Exit codes**: `0` ok · `1` preflight/selftest failed · `3` clinic NOT-LANDED ·
`4` no rows.

---

## §8 Structural guarantees (all self-tested, all fired on purpose)

### 8.1 Path-b is IMPOSSIBLE, not discouraged

Exit criterion 3 asks for impossibility. Four layers:

1. `attribution.path` accepts only `"path-a"`; any other value aborts the harness
   at config load.
2. The resolver reads `ads`, `adsets`, `campaigns`, `chiropractors` only.
   `ad_accounts` is never referenced.
3. **Every statement passes a gate** before reaching the server: it must begin
   `SELECT`, must contain no DML/DDL token, and must not mention any retired
   table. A word-boundary match on `ad_accounts` raises `RetiredSubstrateError`.
   A future edit that reintroduces path-b fails **loudly at runtime**, not
   silently in results.
4. The guard is **fired once on purpose** at every `preflight` and `selftest` —
   an ad_accounts query is attempted and the raise is asserted, and a path-a
   query is attempted and the acceptance is asserted. An unfired guard does not
   count as armed. (Adopted cross-arc from the 33/33 never-authenticated witness
   lesson and the ad-lead-gate sitting's "the burst alarm must be FIRED ONCE ON
   PURPOSE before it counts as armed".)

Every receipt stamps `attribution.guard` and the individual guard-check results.

R-2's grounds, restated: `ad_account_id` is non-unique — one agency master
carries 857 office phones including the internal `+12488025832`; there is a
malformed `act_act_890095768862663` row and 91 empty-string phones. A receipt
walking it is vacuous.

### 8.2 The staged-lookup pattern is a CORRECTNESS device

`campaigns.chiropractor_id` is `latin1_swedish_ci`; `chiropractors.guid` is
`utf8mb3_general_ci` (verified by `information_schema.COLUMNS`, 2026-09-01). The
naive 7-table join asks MySQL's collation resolver to reconcile those, which is
what grinds.

The harness **never joins across that boundary**. It walks the chain in five
staged `WHERE … IN (…)` lookups, carrying identifiers back into Python between
each stage, where the comparison is plain byte equality. Batches of 500. Pattern
inherited from the ad-lead-gate sitting's `audit3.py` / `audit2.py`.

### 8.3 Read-only and PII-fenced

Session opened `SET SESSION TRANSACTION READ ONLY` + `START TRANSACTION READ
ONLY`; every statement additionally gated in-process. Patient names reduce to
initials, phones to a masked tail, emails to a masked local part. **There is no
unmask flag** — certifiers re-derive from `appt_id` / `lead_id`, which every
receipt carries. Credentials are read from a `.env` and never printed, including
in error paths (connection errors are redacted before display).

---

## §9 Teeth — two-sided, on real rows

Per `discriminating-canary-doctrine`: the RED is a **deliberately-broken INPUT**
that the live harness correctly rejects — never a defect injected into working
code. All fixtures are real production rows.

| # | fixture | must | on leg |
|---|---|---|---|
| T1 | appt 18231179 — U.E. attorney-referral (lead 336056) | REFUSE | `A1-source-id-present` |
| T2 | appt 18231180 — its reviewwave twin | REFUSE | `A1-source-id-present` |
| T3 | appt 18197931 — Mansour 2027 (`→ 2027-01-04`) | REFUSE | `A1-source-id-present` **(never a date leg — R-3)** |
| T4 | appt 18229605 — soak booking #1 (lead 329753, Nation) | **CERTIFY** + carry `F-SYNTHETIC-LEAD` | — |
| T5 | 18229605 + 18229606 | CERTIFY, absorbing `[18229606]` | dedup |
| T6 | 18194750 + 18194751 | absorb **nothing** | dedup negative control |
| T7 | 18229605 under `include=["email-booking-intake"]` | CERTIFY | scope positive |
| T8 | 18229605 under `include=["ghl"]` | REFUSE | `S1-booking-source-in-scope` — scope negative |

A refusal test asserts the **specific** failing leg, not merely that a refusal
occurred: a harness that refuses everything for the wrong reason **fails** the
teeth. That is what makes the refusals discriminating rather than blanket.

Plus 4 guard checks (§8.1). **Total 12; all PASS live on prod, 2026-09-01.**

---

## §10 SVR / UV-P ledger

Platform-behaviour claims in this schema, each receipted by direct inspection at
assertion time or labelled UV-P.

| # | claim | method | anchor |
|---|---|---|---|
| SVR-1 | `campaigns.chiropractor_id` is `latin1_swedish_ci` while `chiropractors.guid` is `utf8mb3_general_ci` — the charset clash is real | bash-probe | `SELECT COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS …` → `('chiropractor_id','latin1','latin1_swedish_ci')`, `('guid','utf8mb3','utf8mb3_general_ci')`; exit 0, 2026-09-01 |
| SVR-2 | three `start_datetime` dialects exist in the window | bash-probe | census over 2,731 `type='appt'` rows: `{'...Z': 1672, '...+00:00': 41, 'naive-T': 1018}` |
| SVR-3 | path-a office equality is EXACT for the whole attributed window | bash-probe | staged walk: `exact=1066 norm-only=0 diverge=0 dangling-chiro=0` |
| SVR-4 | the dual-write path doubles rows per booking | bash-probe | 367 near-simultaneous same-`(clinic,contact)` pairs; Nation's single booking present as 18229605 + 18229606 |
| SVR-5 | 5 attributed rows have `appointments.office_phone ≠ leads.office_phone` | bash-probe | same staged walk, `office_mismatch=5` |
| SVR-6 | both `no-show` and `no_show` exist as statuses | bash-probe | `GROUP BY status`: `no-show`=130, `no_show`=26 |
| SVR-7 | lead 329753 is `platform='test'` | bash-probe | `SELECT … FROM leads WHERE id=329753` → `(…, 'scheduled', …, 'chat', 'test')` |
| SVR-8 | leads 336056 and 332849 carry `source_id IS NULL` | bash-probe | `SELECT id, source_id … WHERE id=336056` → `source_id=None`; `… WHERE phone='+16194468090'` → `(332849, None, …)` |
| SVR-9 | the retired-substrate guard raises on an `ad_accounts` query, live | bash-probe | `selftest` → `[PASS] live reader refuses path-b: RetiredSubstrateError raised` |
| SVR-10 | 41 clinics reach 3 on `eligible`; 3 on `eligible_via_email_booking_intake` | bash-probe | `survey --json` over `2026-08-02 →`, 90 clinics: `elig>=3: 41`, `ebi>=3: 3` |
| SVR-11 | Nation of Wellness stands at 1 of 3, sole member synthetic | bash-probe | `clinic --office-phone +14079068111` → `ELIGIBLE 1 of 3 … shortfall 2`, exit 3 |

| # | UV-P |
|---|---|
| UV-P-1 | `[UV-P: the Asana stage-of-record card (REVIEW gid 1209442727608201) agrees with this harness that Nation stands at 1 of 3 \| METHOD: deferred-to-S-10-or-B2-sweeper \| REASON: the harness reads the booking substrate; the Asana card is a separate surface and reconciling them is B2's sweeper work, not S-9's. The DB reading is the one asserted here.]` |
| UV-P-2 | `[UV-P: change-warden can execute this harness without interviewing this session's lineage \| METHOD: deferred-to-S-10-first-run \| REASON: H-3's acceptance test is discharged by the certifier's own hands at S-10 and cannot be self-attested here. RUNBOOK.md + preflight + selftest are the affordances offered; whether they suffice is the certifier's finding, not the author's.]` |
| UV-P-3 | `[UV-P: `.ledge/spikes/audit-ad-lead-gate-2026-09-01/audit3.py` is present on `autom8y` origin/main \| METHOD: deferred \| REASON: the cited path resolves ONLY inside monorepo worktrees (`wt.10x-dev.adlead-s2a.…`, `wt.10x-dev.s5-f0-f3.…`); it is absent from the monorepo checkout root. This is the worktree-unbacked-substrate scar the CONSULT names. The pattern was read from the worktree copy.]` |

Evidence grade **MODERATE** per `self-ref-evidence-grade-rule`: the schema, the
harness and the teeth are all authored by the same seat. STRONG requires the
rite-disjoint re-derivation that S-10 exists to perform.

---

## §11 Findings this instrument produced on its first real execution

### R-5 (shape.md) — **Nation of Wellness soak has STALLED at 1 of 3**

Queried 2026-09-01 (unqueried since 08-27, per `CONSULT:140`):

```
verdict   NOT-LANDED
ELIGIBLE  1 of 3 required   (shortfall 2)
!! ALL of them rest on a SYNTHETIC (platform='test') lead
scanned   2 rows; refused 1  (C2-not-duplicate)
member    appt 18229605  created 2026-08-27 16:45:15  start 2026-08-31T10:00:00
          status=rescheduled  src=email-booking-intake  lead 329753 (M.D.)
          platform=test  ad 120218567929080275 -> campaign 120218567918190275
          -> chiro +14079068111    absorbed [18229606]
```

**Five days, zero new bookings.** The one member is the 08-27 machine-driven E2E
validation booking itself, on a synthetic lead. Nation's *real-customer* count is
**zero**. This is R-5's finding, reported not buried; F3's tripwire is the cure.

### New — the ad-funnel / forwarding-integration divergence

§0. `41` vs `3`. Not in the frame's risk register. This is the mechanism by which
a well-intentioned certifier could certify the whole fleet on evidence that says
nothing about forwarding integrations. Surfaced structurally: the `ebi` column on
`survey`, the `of which via email-booking-intake` line and the shouting
`!! THIS CLINIC IS 'LANDED' ONLY BECAUSE NON-FORWARDING WRITERS ARE COUNTED` on
`clinic`, and `boundary.forwarding_integration_subset` on every receipt.

### For S-10's R-7 watch

Under the forwarding reading the qualifying population is **exactly three**:
Inver Grove `+16514511012` (7), Mansour `+19093934545` (5), Cornerstone
`+16055404004` (3). Cornerstone sits **on** the boundary. Next tier: Watts,
Active 4 Life, Ashburn (2 each). If any of the three is disqualified for a reason
outside this harness, the `>=3 pilot clinics` criterion fails on population, not
on machine quality — which is R-7 firing, and the honest move is to narrow the
certified claim, never to loosen the predicate.

---

## §12 Handoff

**H-3 · edge E-11 · S-9 → S-10.**

Delivered: this schema + `scripts/certification/landing_receipt.py` +
`scripts/certification/predicate.toml` + `scripts/certification/RUNBOOK.md`.

Acceptance test (shape.md H-3): *change-warden runs it WITHOUT interviewing this
lineage.* An interview reintroduces the degeneracy through tooling. The author
cannot mark this discharged — see UV-P-2. The affordances offered are: a
zero-argument `preflight`, a zero-argument `selftest` that returns PASS/FAIL
rather than a table needing interpretation, a `RUNBOOK.md` written for a stranger,
and per-leg explanations printed inline with every refusal.

Not delivered, and named so it is not assumed: **provider-dialect evidence**
(§6.6). S-10's second exit criterion needs a different instrument.
