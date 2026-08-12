---
type: decision
status: accepted
artifact_id: CARDS-follow-up-initiatives-2026-08-11
opened_by: operator ruling R-12 (RULING-operator-s5-gate-interview-2026-08-11.md)
crusade_of_origin: offers-freshness-axis-contract (formerly offers-false-staleness-cure)
session: session-20260811-115247-a1ccd942
date: 2026-08-11
---

# FOLLOW-UP INITIATIVE CARDS — opened by operator ruling R-12

Three standalone initiatives, deliberately OUT of the origin crusade's scope
(charter §7: surfaced, never absorbed). Each is self-contained for routing.

> **Two PROPOSED cards await the operator at the bottom of this file (§PROPOSED).**
> They are recorded, not opened. This register was opened by operator ruling R-12
> and only the operator adds to it — a sprint (S2) declined to open one of these
> on exactly that ground, and that restraint is correct and is preserved here.
> They are written down because the alternative is that two real findings from
> the 2026-08-12 overnight campaign evaporate at session end. **Nothing below
> §PROPOSED is decided, scheduled, or routed.**

## CARD-FU-1 · Cadence-absence alerting for scheduled internal consumers
**The gap**: a stopped scheduled consumer produces no failing call, so no
error-rate alarm can see it. Two live instances on 2026-08-11: the
`asana-dataframe-resolver` project-query cadence collapsed at 02:41:59.112Z
(caller-side, auth plane clean, silent 7.8h+ at last check —
DIAG-S1 F2.1-F2.3, .sos/wip/DIAG-S1-cadence-2026-08-11.md); and ASR skipped
2 of 4 daily reconciliations with nothing paging (tick ledger acid test).
**The work**: cadence-ABSENCE alerts (expected-invocation heartbeat) for the
resolver and the ASR cron; pattern generalizable to any scheduled consumer.
**Routing**: sre/observability. Non-blocking on the origin crusade.

## CARD-FU-2 · Failure-forensics parity for ASR aborts
**The gap**: `fetch_timestamp` is emitted only on the PASS path, so ABORT
anchors are reconstructed from log-emission time — over-estimating by a
measured 11-27s and leaving the FAILING case with the weaker forensics
(LEDGER-asr-ticks §Mission-B finding #2).
**The work**: one field on the `readiness_check_fail` payload carrying the
same fetch-timing evidence the PASS path already emits.
**Routing**: ASR service (monorepo); one-field change + test.

## CARD-FU-3 · Capacity early-warning for the 1000-row query cap
**The gap**: T-GUARD (the new completeness guard) fails closed the day a
per-classification offer count exceeds the 1000-row cap; current headroom is
~15x (67/1000 active, 49/1000 activating — LEDGER §SUPPLEMENT B), but
NOTHING computes or trends the margin; erosion is invisible until the day it
refuses (the census §B.9 standing-watch note: `max_total > 700` is the only
leading indicator and nothing emits it).
**The work**: emit the per-classification `total_available` (or the margin)
as a metric from ASR or reconcile-ads; one alarm at the 700 line.
**Routing**: sre/observability + ASR.

## DEFERRED (on the stack, unopened — operator ruling R-12, explicitly NOT declined)
Infra hygiene trio: (a) untracked live alarm definition
`terraform/services/asana/warmer_cache_degraded_alarm.tf` commit-or-delete;
(b) the contested `autom8-asana-unit-reconciliation` binding-blind reading
(now ALARM-with-action; confirm what changed before closing occurrence #2);
(c) #312 P6-adjacency named debt. Resurface at the next review point.

## CARD-FU-4 · Enforce the ASR image_tag pin invariant (opened 2026-08-12 by hotfix)
**The gap**: `terraform/services/account-status-recon/environments/production.tfvars`
carries the invariant *"Refresh this pin whenever CD rolls a new sha; it MUST
equal the resident image at merge time"* — and **nothing enforces it**. The
refresh is manual. It went unrefreshed for **19 days** (ce96477 @2026-07-23 vs
CD-rolled c21cab9 @2026-08-11), during which any `workflow_dispatch` apply or
local `just tf-apply` would have rolled the production ASR lambda back past
PR #1539 — un-deploying the offers content-axis gate attested at
REALIZED-MECHANISM. Fixed for now by PR autom8y#1555; the CLASS is untouched.
**The work**: either (a) automate the refresh in CD (the deploy that rolls the
sha also updates the var-file pin), or (b) fail the plan when
`pin != resident image` — a guard in the plan workflow comparing the var-file
value against `aws lambda get-function`. (b) is the smaller, two-sided one.
**Why it recurs by construction**: the pin exists to stop a wiring-only apply
re-pinning to mutable `:latest`, so it can never be deleted — only kept true.
Every future CD roll re-arms it.
**Routing**: sre/platform-engineer + the monorepo CD owner. Non-blocking on any
current initiative; the acute instance is closed.
**Acute-instance receipt (2026-08-12T20:32:05Z)**: autom8y#1555 **MERGED** as
`7bbb418e`; all required contexts SUCCESS, including
`Plan (account-status-recon, production)`. The pin now reads `c21cab9`, equal to
the resident image — so a `workflow_dispatch` apply is no longer a rollback.
**Second-order finding, worth its own line** (see also §PROPOSED below): auto-merge was armed at 20:16:44Z
and **did not fire** for ~15 min against `mergeStateStatus: CLEAN`,
`mergeable: MERGEABLE`, `required_approving_review_count: 0`, every required
context green. It landed only on a manual `gh pr merge`. Candidate cause:
`required_linear_history: true` on `main` versus the armed `mergeMethod: MERGE`
(main does carry two-parent merges — `0e60e0f5`, `c21cab9d` — so the convention
survives by admin bypass, which auto-merge does not inherit). **Not verified.**
Consequence if real: *arming* auto-merge on this repo is not *landing*, and any
unattended flow that treats it as landing will stall silently. Worth a probe
before anything depends on it.
**Corroborated 2026-08-12T21:1xZ by the sibling repo's configuration** (still
not a direct proof for the monorepo, but the hypothesis now has a control):

| | `autom8y` (monorepo) | `autom8y-asana` |
|---|---|---|
| `required_linear_history` | **true** | **true** |
| `enforce_admins` | **false** | **true** |
| merge commits on `main`? | **yes** — `0e60e0f5`, `c21cab9d` are two-parent | **no** — `#350/#339/#351/#352` all single-parent, squash |

The two repos declare the *same* linear-history rule and behave oppositely,
and the variable that differs is `enforce_admins`. On the monorepo, admin bypass
is what lets two-parent merges land at all — and **auto-merge does not inherit
an admin's bypass**, so an armed `mergeMethod: MERGE` there is unlandable by the
bot while being landable by hand. That is exactly what was observed. On
`autom8y-asana`, admins are enforced, so nothing bypasses and everything is
squashed — auto-merge with `--squash` should behave normally here.
**Practical rule until proven otherwise: on the monorepo, arm auto-merge with
`--squash`, or do not treat arming as landing.**

---

# §PROPOSED — recorded for the operator, NOT opened

Surfaced by the 2026-08-12 overnight campaign. Only the operator opens a card in
this register (ruling R-12). Each below states its own evidence and its own
uncertainty. **Neither is decided, scheduled, or routed.**

## PROPOSED CARD-FU-5 · The 100-campaign cap has six coincident surfaces and no leading indicator
**Proposed by**: S2 (`DISPOSITION-asr-brief-residues-2026-08-12.md`, OP-2).
**S2 explicitly declined to open it**, on the ground that the register is opened
by operator ruling and not by a sprint. That restraint is why this sits here
rather than above.

**The gap**: the ADS 100-campaign server cap is *handled* — S2 falsified the
"unhandled" charge and found **six** operator surfaces, not the two claimed:
banner `orchestrator.py:633-637`, keyable log `:317-323`, metrics
`metrics.py:85-86`, a live Grafana rule `alerting.tf:1949-1972`, and the runbook.
But **all six are coincident** — they fire when the cap is already being hit.
`CampaignsFleetTotal` emits `0` on healthy runs, because `campaigns_fleet_total`
defaults to 0 (`models.py:387`) and is assigned **only inside the truncation
branch** (`orchestrator.py:310-312`). So the metric that would show the fleet
approaching the cap reads zero right up until the cap bites.

**Why it is worth a card**: this is the same defect class as CARD-FU-3 — a
different cap, a different repo, a different entity, the identical shape. Two
instances make a class.

**Do not conflate the two caps.** S2 holds them apart in an 11-row table:
**100** = ADS server cap, monorepo, drop-and-warn. **1000** = offers query row
limit, autom8y-asana, T-GUARD fails closed. *(Related: a rite-disjoint critic
established on 2026-08-12 that the 1,000 is the ASR's own request at
`fetcher.py:504-514`, not a platform invariant — `guards.py:50` sets
`max_result_rows = 10_000`.)*

**Routing if opened**: sre/observability + the monorepo ADS owner.

## PROPOSED CARD-FU-6 · S2S write endpoints are authenticated but not authorized
**Proposed by**: the rite-disjoint arch critic on S3
(`CRITIQUE-s3-delivery-rails-2026-08-12.md` §A). **Defensive-security finding on
our own surface.** Not an incident; no exploitation is claimed or implied.

**The finding**: `require_service_claims` is **authentication-only**. It returns
`ServiceClaims(..., permissions=[...])`, but `entity_write.py` references
`claims` at exactly `:231` and `:362` — **both are logging**. One file away,
`admin.py:456` reads `if SUPER_ADMIN_PERMISSION not in claims.permissions:`. So
**a cache-refresh is permission-gated and an Asana board write is not.** In
JWT-mode the caller is lent the bot PAT — `bot_pat.py:56-58`, *"the single
credential that autom8_asana uses to call the Asana API on behalf of all S2S
callers."* The effective gate is **fleet membership, not authorization**. The
declared write surface is **26 endpoints across 8 modules** (`x-fleet-side-effects`).

**What was tried and failed** (recorded so the finding is not overstated): the
critic attempted to make PAT-mode into an exposure and could not —
`dependencies.py:140-149` passes the user's own token through, conferring
nothing the caller did not already have. It is a proxy. The finding is about
the S2S/JWT path only.

**The open question, deliberately unprobed**: whether an agent seat in this
fleet can actually obtain such a JWT. Carried as **UV-P-C-1**. Probing it needs
live credentials and was correctly not attempted.

**Why it matters now**: `CR-1` reserves all three Asana write classes to the
operator. This finding establishes that CR-1 is a **process fence standing where
a technical one does not**. A later seat reading "Asana writes are gated" could
reasonably infer the gate is technical and treat the fence as redundant. It is
not redundant; for the S2S path it is the only control. *(Note: the same critic
also refuted S3's claim that comment-CREATE is unbuilt — the route reaches the
verb through `services/` at `main.py:491` → `receipts.py:85` → `:169` →
`receipts_service.py:346`. **Three of three** write classes are built.)*

**Routing if opened**: security rite, with the autom8y-asana API owner.
