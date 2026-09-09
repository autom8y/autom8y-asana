---
type: telos
initiative: name-the-client
status: INSCRIBED (inception) — verification_deadline NULL, LAWFUL under the R-17 BAR-NOT-DATE carve-out; see the Amendment section, which is part of this declaration
created: 2026-09-08
inscribed_by: >
  main thread of session autom8y-asana-f3, PT-00 pre-flight item B-2, transplant
  performed by moirai under main-thread dispatch. The telos block below is
  transplanted VERBATIM from the frame's §2 (authored by myron). At transplant
  time the asana label was re-resolved own-hands to 389c59bc and the autom8y
  origin/main label to a4bc0e39 — BOTH had moved since the frame was authored:
  the frame's own source_hash reads d75bfe1a and its code_repo_svr cites
  origin/main 57e21107 (itself already a move from the charge's cc88b75e).
source: .sos/wip/frames/name-the-client.md §2 (transplanted verbatim, lines 99-171 + the 173-198 Amendment)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
code_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y @ origin/main a4bc0e39
frame: .sos/wip/frames/name-the-client.md
shape: .sos/wip/frames/name-the-client.shape.md
decision_space_of_record: .ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md
parent_initiative: name-the-zero (PARKED per C-6; its containment work continues INSIDE this envelope per C-1)
self_cap: MODERATE
---

# Telos — name-the-client (inscribed 2026-09-08)

**Gate A closed by inscription.** Mission (end state): every active client's bookings
arrive, are attributed to that client BY NAME on the plane, and are countable — and no
account activates without an end-to-end proof that its pipe works. Verified-realized =
the operator's ratified receipt (C-7), carried VERBATIM into every sprint's exit
criteria: a LIVE attributed booking naming that office, TWO-SIDED — a failure for the
SAME office also names it, with its kind, never blank — held across the C-3 denominator
(ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.

```yaml
telos:
  initiative_slug: name-the-client
  inception_anchor:
    framed_at: 2026-09-08
    frame_artifact: .sos/wip/frames/name-the-client.md:57
    why_this_initiative_exists: >-
      Client success escalated two accounts (Dr. David Salkin `6f22301a`, Sand Lake Dental
      `1b271a63`) as booking failures. The measurement found something worse and older: their
      mail has NEVER arrived — zero `guid_extracted` across the full 89-day retention on two
      disjoint instruments, with 60,830 events of in-query control and 76 other offices
      arriving daily through the same catch-all Inbound Parse route on the same hostname
      (DIAGNOSIS §3, §13). Four MORE offices sit in the identical condition and have never
      been escalated by anyone (REPORT §3). The condition is already NAMED and already
      RATIFIED in committed code — `scripts/ebi_witness_ledger.py:463` splits offices H/S on
      `posted_count > 0 or distinct_dispositions > 0`, and `.know/telos/EBI-automation-crusades.md:74,113`
      records `verified != enabled` OBSERVED LIVE on 2026-07-09 — yet it reached us through a
      human, not an instrument, because the instrument writes to orphan branches nobody reads
      (REPORT §2, §0). Meanwhile the plane cannot name WHICH client a booking belongs to: it
      emits an 8-hex GUID prefix, the account model keys on `office_phone`, and nobody holds
      the join (C-15; RATIFICATION §3:44). The operator ratified the response on 2026-09-08:
      the organizing job is THE CLIENT CLASS (C-1), the done-bar is a client outcome for ALL
      active clients (C-3), and no account may activate without an end-to-end proof (C-17).
  shipped_definition:
    code_or_artifact_landed:
      - "WS-JOIN: a GUID <-> office_phone resolution seam that lets a plane line name its own office, transiting the PII ruling rather than routing around it — `scripts/ebi_witness_ledger.py:21,:394` state verbatim that `office_phone in the payload are DROPPED (not hashed, not truncated`, and DIAGNOSIS §6 names the cost<->integrity coupling that makes this a ruling, not a lookup"
      - "WS-DENOM: an EXTENSIBLE denominator seam (C-16) whose CURRENT adapter is Asana section membership and whose boundary is designed for a DB-status-read successor — an architecture decision, not a source choice; must refuse ASR's `activity` token by construction (different quantity) and must not read `account_status` as a corroborator (same-lineage echo)"
      - "WS-SMOKE: an onboarding smoke bound to the LIFECYCLE TRANSITION on a hook WE own (C-17), such that an account cannot activate without an end-to-end proof that its pipe works"
      - "WS-RECEIPT: the two-sided per-client receipt itself (C-7) — a live attributed booking naming the office AND a same-office failure that also names it with its kind, never blank — evaluated across the C-3 denominator"
      - "WS-CONTAIN: the containment landing (C-10/C-11) — the next image the intake serves carries S-14's cure; executes as a DISPOSITION OF RECORD when R-35 lifts, never by this envelope's motion"
      - "WS-DARK: disposition of the six-office dark class, gated on the untaken outbound signal (Q-C), NOT on pipeline engineering — DIAGNOSIS GO/PARK explicitly PARKS pipeline work for these accounts"
      - "WS-CARGO: a NAMED HOLDER for PR #1941 @ b9bbfadc (C-9) and the carried gate registry (C-12) with owner/trigger/watcher per row and `NO WATCHER` written where true"
    user_visible_surface: >-
      When a booking lands, the plane line NAMES the office it belongs to — readable directly,
      with no cross-service join and no human lookup. When a booking for that same office
      FAILS, the line names the office too, and names the kind of failure; it is never blank.
      Every active client is on that surface, not one exemplar. And a new account cannot be
      switched on until an end-to-end proof has run through its own pipe. Product form:
      "we can tell you, by name, whether YOUR bookings are arriving — and if they are not, we
      can tell you why, before you have to ask us."
  verified_realized_definition:
    user_visible_evidence:
      - "(a) A LIVE attributed booking line on the plane NAMING the office it belongs to — resolved to a client identity, not an 8-hex prefix, and readable without a cross-service trace join"
      - "(b) TWO-SIDED (C-7): a FAILURE for the SAME office also names it, carrying its kind, never blank — the negative pole is a required half of the receipt, not a nice-to-have"
      - "(c) Held across the C-3 denominator: ALL ACTIVE CLIENTS, not one. A green receipt for a single office is a DIFFERENT CLAIM, not a partial pass"
      - "(d) An account that attempts activation without a passing end-to-end pipe proof is REFUSED activation (C-17), demonstrated two-sided: a healthy pipe activates, a broken pipe does not"
      - "NOT 'PRs merged'. NOT a served image. NOT a projection — the parent's S-14 AFTER figure (41.6% -> 21.2%) is a PROJECTION and is named as one (RATIFICATION §4.2)"
    verification_method: telemetry
    verification_deadline: null   # LAWFUL under the R-17 BAR-NOT-DATE carve-out; see the `## Amendment` section below, which is part of this declaration and travels with it
    rite_disjoint_attester: >-
      integrity-architect (dre, co-seated) — rite-disjoint from the active 10x-dev rite per R1.
      BINDING: any dre seat that BUILDS a workstream in this envelope MAY NOT attest it
      (critic-never-author). change-warden (dre) already holds the premise-correction ledger
      for this lane (DIAGNOSIS §12) and is therefore a REVIEW seat here, not an attest seat,
      unless Pythia re-seats explicitly. Pythia may re-seat at /shape within R1.
  attestation_status:
    inception: INSCRIBED   # on transplant to .know/telos/name-the-client.md; MISSING until then
    shipped: MISSING
    verified_realized: UNATTESTED
    last_eunomia_advisory: null
  receipt_grammar:
    per_item_file_line_anchors:
      - ".ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md:10-27 (C-1..C-18), :29-40 (§2 defers, incl. the starred G-FL1 omission and the R-35 no-forcing-function risk), :42-48 (§3 substrate refutation), :50-56 (§4 six unconfirmed assumptions)"
      - ".sos/wip/TRIAGE-client-booking-blockers-2026-09-08.md §10 (the match_lead.py:725-728 defect; 77 modelled vs 76 measured 5xx), §12.1 (74-office control, 585,935 records), §12.2 (CORRECTION 1: b167331c is Oak Springs, NOT Sand Lake), §12.3 (CORRECTION 2: ratified-silent in committed code), §12.4 (an untaken zero caught by its own dead control)"
      - ".sos/wip/DIAGNOSIS-verified-not-enabled-2026-09-08.md §3 (89-day zero on a disjoint instrument), §6 (cost<->integrity coupling; the 1,252 office-blind residual IS the PII control), §7.0 (the charge's SendGrid premise REFUTED AS STATED), §7.1-7.4 (Q-A/Q-B/Q-C/Q-D), §9 (the 15,084-event 2026-08-23->08-27 outage in no record), §12 PR-2 (the load-bearing correction), GO/PARK"
      - ".sos/wip/REPORT-tier-split-consumer-2026-09-08.md §0 + §2 (a green nightly job writing to five orphan branches nobody reads; the missing primitive is a READER), §3 (the six never-arriving GUIDs; three TIER-S drifts incl. BETTER LIFE at 299 arrivals), §4 (the positive control FIRED), §5.1 + §5.2 (two structural false-S generators), §7.5 (the named trigger), §10 (what was not verified)"
      - ".ledge/decisions/PROPOSAL-fast-lane-blast-radius-predicate-2026-09-08.md:43 (FL-1..FL-4 verbatim), :54 (why FL-3 is load-bearing), :111-120 (H2 refused three independent ways), :268 (the G-FL1 UV-P: AUTHORED AND UNRATIFIED)"
      - ".sos/wip/CUSTODY-name-the-zero-wave2-register-2026-09-08.md:12-23 (PT-07 fence-check + verdict), :26-34 (findings at entry, incl. M-4 RED and the stale-tree trap), :38-59 (PT-08 containment gate), :61-66 (findings at PT-08)"
      - ".sos/wip/EXTRACTION-observer-law-and-untaken-zero-2026-09-08.md:159-393 (the seven faces across two registers), :241-299 (face 4 built-and-unconsumed), :322-346 (face 6 wired-fired-unanswered); .sos/wip/PACKET-observer-law-extraction-2026-09-08.md:126-254 (both disciplines), :592-681 (discipline C)"
      - "autom8y @ origin/main 57e21107: .github/workflows/service-deploy-dispatch.yml (push:[main] paths services/**) -> .github/workflows/service-deploy-lambda.yml:4 (workflow_call), :304 (`terraform apply -input=false -auto-approve tfplan`) — the C-11 apply chain, re-verified own-hands 2026-09-08; scripts/ebi_witness_ledger.py:21,:394 (office_phone DROPPED), :463 (the ratified H/S predicate); services/account-status-recon/src/account_status_recon/readiness.py:41-43 (OFFER_CONSTITUENTS and its conditional-index fragility), rules.py:81, verdict_surface.py:101"
    cross_stream_concurrence: false  # earned at close
    code_verbatim_match: false       # earned at close
```

### Amendment — 2026-09-08 (R-17 BAR-NOT-DATE; part of the declaration, transplants with it)

`verification_deadline` is **`null`** and this is **LAWFUL**, not a stub. It is set under the
R-17 bar-not-date carve-out (`telos-integrity-ref` §3 Gate A), which requires this amendment to
state (a) the BAR and (b) the operator ruling that chose bar-not-date.

**(a) THE BAR.**
- **The rung:** a LIVE attributed booking line naming its office, plus a same-office FAILURE
  line that also names it with its kind and is never blank, **held across ALL ACTIVE CLIENTS**
  — plus a demonstrated activation REFUSAL for an account whose pipe proof does not pass.
- **The rite-disjoint attester:** integrity-architect (dre, co-seated), under critic-never-author.
- **The two-sided receipt that discharges it:** the positive pole (a real booking, named) AND
  the negative pole (a real failure for the same office, named and kinded). Either pole alone
  discharges nothing. Per `three-evidence-leg-attestation`, the attester re-derives all legs
  and inherits none of the builder's proofs.

**(b) THE OPERATOR RULING.** The operator's own words in the mission carried into this frame:
**"DONE IS A BAR, NOT A DATE."** Ratified basis: C-3 (`RATIFICATION-client-outcome-decision-space-2026-09-08.md:12`)
sets the done-bar as a CLIENT OUTCOME for all active clients, and C-7 (`:16`) fixes the receipt
as two-sided and log-plane-checkable with no human in the loop. Neither ruling names an instant.

**Why a date would bind nothing here anyway.** `TELOS_OVERDUE` is referenced by `charon` and by
the telos docs but is **EMITTED BY NOTHING** — this is precisely face 3 of the observer law
(`EXTRACTION-observer-law-and-untaken-zero-2026-09-08.md:185-240`: BUILT, TESTED, UNWIRED and
GUARD-BLIND). A date set here would lapse silently and the initiative that just extracted that
law would have shipped an instance of it. When an emitter exists, re-examine this amendment.
