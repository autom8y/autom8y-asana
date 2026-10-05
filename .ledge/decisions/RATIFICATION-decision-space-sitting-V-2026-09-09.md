# RATIFICATION — decision-space sitting V, 2026-09-09 (residuals)

**Form:** `/interview`, two adaptive rounds, seven questions. **Rulings R-105 … R-111.**
**Selection: 5 of 5 recommendation-bearing questions took this seat's recommendation.**
**Recorded as a caution, not a result** — the same signal sitting II logged, returning after two
sittings where it broke. Never-grantable floor **UNTOUCHED**.

---

## §1 DECIDED

### R-105 — N = 10, on the CORRECTED basis · BINDING
Arm the gate when **fewer than 10 open PRs predate it**.
**★ This seat's R-103 priced N against the wrong denominator.** It said *"PRs touching `services/**`"*
(33). **The gate has NO paths filter, so it runs on every PR and EVERY PR predating it lacks a run** —
the real basis is **all open PRs, ~58-60 of 63.** N=10 against the right denominator is a **materially
longer wait** than against the wrong one, and was chosen with that stated.

### R-106 — ★★ C-13 IS DISCHARGED · BINDING
The cofounder exchange **was** C-13's conversation. `R-65` said *read the handler*; `INTEROP:116`
established the handler is unreadable by us, so the condition could only mean **ask the owner** —
which happened, and was answered: **the endpoint returns a 2xx and nothing else**, which IS the answer
to what it does with an unconfirmable write.
**Declared cost:** it discharges by **reinterpretation**, not by the literal handler read R-65 named.
> **CONSEQUENCE: R-87's dominance is satisfied. R-99's narrow lift is OPERATIVE. #2073 MAY MERGE.**

### R-107 — The PII class is cured in ONE PR, PARKED · BINDING
Four raw `office_phone` emissions (`resolve_office.py:204,214,233,248`) **and** the
`phone_hash` at `book_appointment.py:45-54,151` are **one class**: an identifier either logged raw or
hashed in a way that does not anonymise (anonymity set of 1 against a published clinic corpus).
**#2073's `office_log_fields` is the non-reversible replacement**, so the cure lands on top of it.
**Accepted cost:** it bundles two findings the record holds under separate owners.

### R-108 — SAMPLE and verify the ad-lead-gate refusals · BINDING
`[OWN-HANDS]` 7-day measurement: **386 refused / 38 passed = 91% refusal**, with `terminal_decline`
matching refusals **exactly** at 386. **Nobody has verified a single refusal is correct.**
**At a 5% error rate that is ~19 wrongly-dropped leads per week.** Read-only.
**Declared risk, accepted:** it may return *"working as intended"* and cost a cycle.

### R-109 — The gap is covered by the DO NOT MERGE title convention, RESTATED · BINDING
**★ The interaction none of the questions exposed, surfaced before ruling:** R-99's lift makes merges
resume **while N=10 keeps the gate unarmed for months** — **the recurrence control is inert during
exactly the window it was built for.**
**The operator ruled the convention covers it, with the objection printed in the option and chosen
anyway:** *"a convention a tired seat must read has already failed by design"* — **this seat's own
words, about this exact convention, on this exact surface, which failed on #2087 twenty-nine minutes
after being honoured on #2085.**

### R-110 — F-1…F-7 get ONE PREPARED SITTING · BINDING
This seat prepares a single page — **the one question, its seven consequences, what each unblocks, and
the default if unruled** — and the operator rules it in one sitting rather than seven.
**Only clause (c2) strictly waits on it.**

### R-111 — ALL FOUR residuals are to be ruled, none left deferred · BINDING
1. **`is_paying = 0`** on all four divergence offices — **semantics and snapshot currency unverified.**
2. **`calendly-intake-recon`**, disabled since 09-04, no feature gate found in source ⇒ looks like
   **real behaviour switched off**, not a dark no-op.
3. **The onboarding walkthrough's disabled schedule** — R-95 established the pilot ran and reps get
   real value, so **a working tool is off.** Re-enable order is **flag → declaration → schedule
   (schedule LAST)**, because the disabled state is declared in terraform.
4. **O-2 §A · O-4(a) · O-4(c) · O-7** — **★ this seat flagged that it has NOT re-verified these are
   still live**, and the operator selected them anyway. **So the order is: this seat measures, THEN
   the operator rules.** Ruling on unmeasured forks is the thing this arc exists to refuse.

---

## §2 THE SEQUENCE R-106 UNBLOCKS (per R-104)
1. **#2073 → main** — apply #1 — verify live
2. **retarget #2105 → main**, merge — apply #2 — verify live
3. **reassess #2071**
4. **then** author the R-107 PII cure on top of #2073's `office_log_fields`, and park it
**C-1 holds: each merge is a separate image event and they are NOT bundled.**

## §3 ASSUMPTIONS UNCONFIRMED
1. **★ 5 of 5.** The recommendation-selection pattern returned after breaking in two sittings.
   **Any of R-105…R-111 is re-openable on that ground alone.**
2. **★ The C-13 ↔ R-35 linkage reached this seat SECOND-HAND.** A peer relayed that the operator
   confirmed *"one wait"*; **the landed registry had STRUCK that claim** before it was re-established
   on other grounds. This seat never witnessed the confirmation. **R-106 rests on it.**
3. **R-107 may rest on an unexamined premise.** `ad_lead_gate/observe.py:33-37` states
   *"office_phone is a BUSINESS phone and is permitted"* — which **contradicts C-15** and was offered
   as an option and not taken. **Whether clinic phone numbers are PII at all has never been tested by
   this arc.**
4. **N=10 may be months away** on a 63-PR board.
5. **O-2 §A / O-4(a) / O-4(c) / O-7 are unmeasured.**

## §4 WHAT SITTING V DOES NOT DO
It does not arm the gate, cure the PII, close clause (a) or (c2), or rule the identity fork.
**It discharges no clause — all four remain WAITING.** **But R-106 removes the last gate in front of
#2073, and #2073 is clause (a)'s cure.**

> **`Verified-realized` = a LIVE attributed booking naming that office, TWO-SIDED — a failure for the
> SAME office also names it, WITH ITS KIND, never blank — held across ALL active clients, not one.
> NOT "PRs merged". DONE IS A BAR, NOT A DATE.**
