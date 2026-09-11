---
type: telos
initiative: read-the-name
status: DRAFT — UNRATIFIED. Drafted under sitting IX R-146 (2026-09-11); becomes the bar only when a decision-space sitting (X or later) ratifies it. Until then it binds nothing and is cited only as "the draft".
created: 2026-09-11
inscribed_by: >
  seat calendar-integration-locus, main thread, the afternoon after sitting IX.
  Drafted from pythia's CONSULT-morning-after-north-2026-09-11 (§3 amendment,
  §6 successor epoch) and the sitting IX rulings R-135, R-141, R-142, R-145.
  Nothing here is transplanted from a frame; there is no frame yet. self_cap
  MODERATE, single seat, no rite-disjoint attestation.
source: .ledge/decisions/RATIFICATION-decision-space-sitting-IX-2026-09-11.md (R-135 · R-141 · R-145 · R-146) and .sos/wip/CONSULT-morning-after-north-2026-09-11.md
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
code_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y (EBI, terraform) · /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana (lifecycle, clause (d))
decision_space_of_record: .ledge/decisions/RATIFICATION-decision-space-sitting-IX-2026-09-11.md
parent_initiative: name-the-client (wave 1 closing on (d) + R3; clause (c2) carried INTO this epoch as item 3, per R-141)
self_cap: MODERATE
---

# Telos — read-the-name (DRAFT, 2026-09-11)

**Why a new verb.** `name-the-client` answered *can the plane name the client on both
poles?* — on live traffic, every completed booking names its office and every failure
line carries a kind. What it did not and cannot answer is the promise's second clause,
*"before you have to ask us"*: that is a property of a **consumer** of the name, and
none exists. The arc produced its own largest instance of its own law: one office sent
406 mails in eight days, booked 2, and every line correctly named the office and the
reason — and nothing paged, because nothing reads the name. Naming was the prerequisite.
Reading is the product.

## Mission (end state)

Every active client whose mail arrives and does not book is **named to a human before
the client has to ask** — and no account activates without an end-to-end proof that
its pipe works.

## Realization predicate — UNRATIFIED draft; four clauses, in the order their controls arrive

Each clause is two-sided: a positive pole that fires on the real thing and a negative
pole that stays quiet on its absence, both measured on live traffic, never on a
synthetic alone. A clause with only one pole is not realized.

- **(R1) The per-office booking floor (S-1) is live and reads the name.** For any
  office with sustained arrivals and zero completed bookings across the ruled window,
  a page names that office within the window. Positive control is **historical and
  free**: replayed on LOGS over the 2026-09-04..09-11 window it fires on the 406-mail
  office. Negative control: offices with arrivals *and* bookings in the same window do
  not fire. **The instrument carries its own silence deadman** — an evaluator that
  stops running is itself paged; a floor that never evaluates is silence wearing a
  green light. **Shape is decided in the S-1 charge (R-145):** logs-native evaluator
  (operator's disclosed lean) or per-office CloudWatch alarms; sitting X rules.
  Charge caveat, proven 2026-09-11: **metric filters are not retroactive** — the
  positive control runs on logs, and any metric soaks before it arms.
- **(R2) Clause (d) enforces.** The activation smoke is wired on the Offer-grain
  referent (`OFFER_CLASSIFIER`, aggregation `max_offer_activity`) in dry-run first;
  it flips to enforce only on a count of **N = 3 verdicts of each kind** (R-130,
  R-133), and the two sides are demonstrated in production: a healthy pipe activates,
  a broken pipe is refused with a named kind. **Dependency, stated:** the permit pole
  cannot reach N until the facts a proof needs — the office's name and a dated pipe
  proof — are readable from the activating subject, which is (R3)'s join.
- **(R3) Coverage over a ruled population — clause (c2), carried in from wave 1.**
  A ruled population of active offices exists (WS-DENOM successor), a two-stage join
  port resolves an office on the plane to that population without the phone
  (ADR-ws-join-office-naming-path Option C), and coverage — the share of the
  population whose bookings are attributable by name — is measured with the
  office-phone exclusion declared up front. Waits on the identity one-page sitting
  (R-110).
- **(R4) The dark column is consumed or removed.** `Lead.ghl_contact_id` (declared
  2026-04, never read) is either wired to a consumer with a two-sided receipt or
  deleted; the GHL contactId scaffolding is un-scaffolded on the operator's word
  (RATIF-VIII-CONTACTID). Last, because its positive control is produced by (R1)–(R3).

**Bar, not date.** No `verification_deadline` (R-17 BAR-NOT-DATE carve-out, inherited
from the parent telos). Verified-realized is the operator's ratified receipt, carried
verbatim into every sprint's exit.

## Standing laws this epoch inherits, verbatim in effect

1. **A control proves the PROBE ran. It cannot prove the SUBJECT runs.** Every
   instrument needs (i) PROBE LIVE and (ii) SUBJECT LIVE, with an in-query control.
2. **A declared instrument with no enforcement on the thing it protects is the
   organizing defect** — twelve carriers named across the parent arc; this epoch may
   not add one. Every new instrument states its consumer before it is built.
3. **Silence deadman:** every instrument declares an expected-occurrence floor.
4. **Never blank:** a refusal, a failure, a decision names its kind or cannot be
   constructed.
5. **The apply is not the word** (R-136): a `services/<svc>/**` merge applies that
   stack's pending terraform unattended. Governance-relevant terraform is announced on
   the PR that will carry it (R-143 charge), and no terraform-only apply is ever fired
   on a stack with a durable image pin.
6. **No phone digits on any face; no raw client names in the record**; offices are
   named by guid prefix in artifacts and by name only on the plane.

## Explicitly not in this epoch

- Re-litigating the naming clauses (a), (b), (c1): attested, and re-measuring them is
  re-confirming a settled fact.
- The freshness-deadman module re-pin, C6, the apply-visibility builds: READ-epoch
  **charges** (R-143, R-144), not clauses of this bar.
- `nhc-db` exposure: KNOWN AND ACCEPTED (R-124).

## What sitting X must rule before this draft binds

1. The four clauses as written, or amended.
2. S-1's shape (R-145 fork) and its window.
3. Whether (R4) belongs here or to the placeholder-phone cross-arc.
4. Whether `read-the-name` is a successor initiative with its own frame, or an
   amendment of `name-the-client` (the seat drafted it as a successor; pythia's
   consult treats it as the same north with the verb amended).
