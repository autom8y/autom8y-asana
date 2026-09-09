---
type: shape
initiative: name-the-client
frame: .sos/wip/frames/name-the-client.md
created: 2026-09-08
rite: cross-rite
complexity: INITIATIVE
generator: pythia
evidence_grade: MODERATE
self_cap: MODERATE
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
source_hash: "d75bfe1a"
asana_origin_main_at_shaping: "389c59bc"
code_repo: "/Users/tomtenuta/Code/a8/a8/repos/autom8y @ origin/main b2b4ae98"
code_repo_svr: >-
  ls-remote + fetch own-hands 2026-09-08. The FRAME cited autom8y origin/main 57e21107;
  it HAS MOVED AGAIN to b2b4ae9835d757e84bf80b6c5fb514b743b2da58 (third move in the arc:
  cc88b75e -> 57e21107 -> b2b4ae98). Local autom8y checkout remains STALE — branch
  fix/wss-wildcard-scope-bypass-closure @ 29e59e81, 351 porcelain entries. Every autom8y
  read in this shape came from the object DB at an explicit ref. The asana repo ALSO moved:
  frame source_hash d75bfe1a -> origin/main 389c59bc (+1 commit, #413), d75bfe1a IS an
  ancestor (rc=0).
decision_space_of_record: .ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md
governing_charter: .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md
scope:
  rites: ["10x-dev", "dre", "eunomia", "security", "sre", "clinic"]
  sprints: 12
cross_rite_consultations: []
workstreams: ["WS-JOIN", "WS-DENOM", "WS-SMOKE", "WS-RECEIPT", "WS-CONTAIN", "WS-DARK", "WS-CARGO"]
ordering_authority: pythia
---

# Shape — Name the Client

> Pythia decomposition of `.sos/wip/frames/name-the-client.md` (**826L**, myron,
> 2026-09-08T19:41:02Z), reconciled against
> `.ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md` **C-1..C-18**
> and its **§4 six unconfirmed assumptions**. Authored at asana `d75bfe1a`
> (origin/main `389c59bc`) / autom8y `origin/main **b2b4ae98**`.
> **SEQUENCING ONLY.** This shape orders, sizes, and task-decomposes what the frame named.
> It re-litigates no ruling. Every platform-behavior claim carries an SVR receipt (§13) or a
> UV-P label (§13). Self-assessment capped **MODERATE** per `self-ref-evidence-grade-rule`.

**Authoring channel.** Progressive-write-heredoc via the existing `Bash` grant
(`Skill('progressive-write-heredoc')`, Option 3). No `Write`/`Edit` tool was used and no
tool frontmatter was widened. The section filler was **self-tested two-sided before use**:
a metacharacter fragment (`` ` ``, `**`, `$VAR`, `${VAR}`, `\\`, `&`, `/`, `|`, `★`)
survived **verbatim** (rc=0), and a missing-marker negative control **failed loud (rc=3)
and did not mutate the file**. A first attempt using BSD `sed -e '/m/{r f' -e 'd}'` was
**discarded**: it errored, and its negative control then reported "OK" *because the tool had
broken before `mv`* — a false pass of exactly the untaken-zero shape this envelope exists to
name. Recorded rather than quietly fixed.

### The realization predicate — VERBATIM, carried into every sprint's exit criteria

> **"Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
> sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a failure
> for the SAME office also names it, with its kind, never blank — held across the C-3
> denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.**

**How the carry is enforced without lying.** Every one of the twelve sprints reproduces that
block verbatim in its `exit_criteria` under the key `realization_predicate_verbatim`, and then
states two further things: **`advances`** (which clause of the predicate this sprint moves) and
**`does_not_discharge`** (what the sprint explicitly does *not* settle). A measurement sprint
cannot produce a live attributed booking; pretending otherwise would manufacture the very
one-sided receipt the parent initiative exists to close. **A sprint whose exit criteria cannot
cite the predicate is mis-scoped — and a sprint that claims to DISCHARGE it without the
two-sided receipt across the C-3 denominator is worse than mis-scoped.** Only **S-12**
discharges. Eleven sprints advance.

## 1. Initiative Thread

```yaml
initiative_thread:
  throughline: >-
    Every active client's bookings arrive, are attributed to that client BY NAME on the plane,
    and are countable two-sidedly — and no account activates without an end-to-end proof that
    its own pipe works.
  success_criteria:
    - "(a) A LIVE attributed booking line on the plane NAMING the office it belongs to — resolved to a client identity, not an 8-hex prefix, and readable without a cross-service trace join"
    - "(b) TWO-SIDED (C-7): a FAILURE for the SAME office also names it, carrying its kind, never blank — the negative pole is a required half of the receipt, not a nice-to-have"
    - "(c) Held across the C-3 denominator: ALL ACTIVE CLIENTS, not one. A green receipt for a single office is a DIFFERENT CLAIM, not a partial pass"
    - "(d) An account that attempts activation without a passing end-to-end pipe proof is REFUSED activation (C-17), demonstrated two-sided: a healthy pipe activates, a broken pipe does not"
  failure_signals:
    - "A sprint reports a zero without a firing positive control and visible stderr (the fence is at N=12; 11/11 failed in the safe-looking direction, 11/11 caught by re-running and 0 by inspection)"
    - "The denominator seam is wired to ASR's `activity` token — it measures our own pipeline fetch coverage and LOOKS PLAUSIBLE (91/144 rows `untriangulated`)"
    - "A per-client attribution surface ships that nothing READS — face 4, built-and-unconsumed, shipped by the wave that extracted the law (REPORT §2: five orphan branches, `the missing primitive is not a consumer; it is a READER`)"
    - "The positive pole alone is reported as realization; the failure pole is deferred to `a follow-up`"
    - "A single exemplar office is reported as a partial pass rather than as a different claim"
    - "`PRs merged`, a served image, or S-14's PROJECTED 41.6% -> 21.2% figure is substituted for the bar"
    - "A registry row acquires a fabricated watcher so the board looks green (worse than an empty cell — C-12)"
    - "R-35 quietly acquires a narrowing, a lift, or an overwrite from inside this initiative"
```

**What the throughline is NOT.** It is not "land the seven workstreams." Six of the twelve
sprints can complete with every PR merged and the throughline still unsatisfied, because the
bar is a **client outcome held across a denominator**, not a set of landings. Potnia evaluates
every checkpoint against the four success criteria above, never against sprint completion.

**The one structural fact that governs the whole graph.** The predicate's clause (b) requires a
failure to name **its kind, never blank**. The cure that supplies the kind for the terminal
decline class is autom8y **#2071**, which touches `services/**` and is therefore an **apply**
— frozen behind **R-35**, which **nothing rules the lift of** and which carries **NO WATCHER**.
Therefore **the realization predicate is gated behind an unwatched operator gate**. That is
not a scheduling inconvenience; it is the shape's central finding, and §5 draws it as the
critical path rather than burying it in a risk row.

## 2. Sprint Decomposition

**Sprint internals are NON-PRESCRIPTIVE.** Each sprint below fixes a mission, a roster, entry
and exit criteria, and the constraints it may not violate. It does **not** hand the seats a task
list — Potnia coordinates, agents discover. Twelve sprints. **Only hard dependency edges are
encoded**; everything else runs in parallel (see §5).

**Seat legend.** `10x-dev` is the ACTIVE rite (native seats). `dre`, `eunomia`, `security`,
`sre`, `clinic` are **CO-SEATED live** — verified own-hands via `ari rite current` and by
physical presence of all 28 agent files in `.claude/agents/` (§6). No seat below is invented.

```yaml
sprints:

  - id: S-01
    name: WS-DARK-PROBE — Q-C, the outbound check
    workstream: WS-DARK
    rite: clinic
    agents: [diagnostician, pathologist]
    external_critic: {rite: sre, agent: observability-engineer}   # rite-disjoint from clinic
    deploy_class: C-INERT
    pr_boundary: "autom8y-asana :: .sos/wip/ + .ledge/reviews/ ONLY (deploy-inert path set)"
    depends_on: []
    mission: >-
      Run Q-C — the single highest-value unknown in §4 assumption 1 — and settle whether the
      six dark offices are a real class or a reporting artifact. The question is OUTBOUND:
      `GET /v3/messages` (SendGrid Email Activity) for the six offices — was the onboarding
      deck ever SENT, DELIVERED, OPENED, BOUNCED? This is a MEASUREMENT, not a build.
      DIAGNOSIS GO/PARK explicitly PARKS pipeline engineering for these accounts.
    named_traps:
      - "★ PREMISE CORRECTION, load-bearing: the charge's SendGrid premise was REFUTED AS STATED (DIAGNOSIS §7.0, §12 PR-2: `No per-recipient inbound log exists`). An INBOUND-shaped query returns a VACUOUS ZERO that will read as confirmation. Q-C is OUTBOUND and only outbound."
      - "T-8 `parse/stats` HAS NO RECIPIENT DIMENSION — it can NEVER say whether one office's mail arrived. Anyone reporting a per-office conclusion from Q-B has produced an untaken zero."
      - "T-9 RETENTION IS NOT HISTORY — the log group was created 149 d ago; 2026-04-12 -> 2026-06-10 is UNOBSERVABLE. `never` means `never within retention` and must be written that way."
      - "403 / UNENTITLED: the Email Activity History add-on may not be on the account. If the call 403s, the honest output is INSTRUMENT UNAVAILABLE — it is NOT a zero, and it must not be reported as one."
    entry_criteria:
      - "The six GUIDs are carried verbatim from frame §5 WS-DARK — not re-derived"
      - "A positive control is designed BEFORE the query runs: a known-good office that DID receive a deck, whose non-zero result proves the instrument answers at all"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (c) — the C-3 denominator. Until Q-C answers, it is unknown whether the six dark
        offices belong IN the denominator as broken pipes or OUT of it as never-onboarded
        accounts. The denominator cannot be closed over an undetermined class.
      does_not_discharge: >-
        Every clause. This sprint produces NO booking, NO attribution and NO failure line. It
        cannot discharge the predicate and must not be reported as partial realization.
      hard_gates:
        - "The positive control FIRED (non-zero on the known-good office) and its stderr is visible in the artifact — otherwise the zero is UNTAKEN and UNREPORTABLE"
        - "The outcome is stated in one of exactly three forms: DECKS WERE DELIVERED (the dark class is a pipeline/forwarding problem) · DECKS WERE NEVER SENT (the class relocates wholesale into onboarding delivery) · INSTRUMENT UNAVAILABLE (403/unentitled — no claim either way)"
        - "UV-P-5 in the frame's ledger is either DISCHARGED or re-labelled with the reason"
    exit_artifacts:
      - path: ".sos/wip/PROBE-qc-outbound-deck-delivery-2026-09-08.md"
        description: "Q-C result, its positive control with visible stderr, and the three-way disposition"
    context:
      - ".sos/wip/DIAGNOSIS-verified-not-enabled-2026-09-08.md §7.0, §7.2, §7.3, §12 PR-2, GO/PARK"
      - ".sos/wip/REPORT-tier-split-consumer-2026-09-08.md §3, §4"
      - ".ledge/decisions/VERDICT-client-onboarding-delivery-2026-09-05.md:82 §3.1"

  - id: S-02
    name: WS-CARGO — the named holder and the gate registry
    workstream: WS-CARGO
    rite: eunomia
    agents: [verification-auditor, entropy-assessor]
    external_critic: {rite: 10x-dev, agent: qa-adversary}
    deploy_class: C-INERT
    pr_boundary: "autom8y-asana :: .ledge/decisions/ + .sos/wip/ ONLY"
    depends_on: []
    seat_note: >-
      ★ CAPABILITY SPLIT, verified own-hands: `entropy-assessor` frontmatter is
      `tools: Read, Write, Glob, Grep` — it has NO Bash and CANNOT run `gh pr view` or any live
      probe. `verification-auditor` (`tools: Bash, Glob, Grep, Read, Write`) holds every live
      verification in this sprint; entropy-assessor authors the registry. Assigning the live
      re-verification to entropy-assessor would silently produce an unverifiable registry.
    mission: >-
      Discharge C-9 and C-12. Name a HOLDER for PR #1941 (or surface the naming to the operator
      as fork O-7 if it is not agent-decidable), and inscribe the carried gate registry as a
      registry of record with owner · trigger · watcher per row and `NO WATCHER` written where
      true. This is face 7 of the observer law — a DECISION with no watcher — and the envelope
      that extracted that law shipping an unwatched deferral would be the law's own counterexample.
    entry_criteria:
      - "The §9 registry of this shape is taken as the starting rows — 11 rows, 9 carrying NO WATCHER, 1 self-firing clock — not re-derived from scratch"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        None of (a)-(d) directly. WS-CARGO is what stops the other six workstreams from rotting:
        R-35 (which gates clause (b)'s kinding), G-A1 and G-FL1 all sit unwatched, and an
        unwatched gate is how this initiative fails without anyone observing the failure.
      does_not_discharge: >-
        Every clause. Custodial only. It must never be reported as progress toward the bar.
      hard_gates:
        - "#1941 head re-verified LIVE and reported as frozen-or-moved against `b9bbfadc` — inheritance is not assumed"
        - "Every registry row carries an owner and a trigger, or carries the literal string `NO WATCHER`. A fabricated watcher is worse than an empty cell (C-12)"
        - "The M-4 RED is triaged with its one genuine hit at `test_df40_read_kind_corpus.py:80` named, and its word-time bite stated"
        - "The #1941 disposition is LAND / HOLD / CLOSE — and if the seat cannot decide, it is surfaced as O-7 and NOT decided. Closing #1941 to tidy the board is FORBIDDEN: it spends a rite-disjoint certificate that cost two re-walks"
    exit_artifacts:
      - path: ".ledge/decisions/REGISTRY-name-the-client-carried-gates-2026-09-08.md"
        description: "The C-12 registry of record: owner · trigger · watcher, NO WATCHER written where true"
    context:
      - ".sos/wip/frames/name-the-client.md §6, §9"
      - ".sos/wip/CUSTODY-name-the-zero-wave2-register-2026-09-08.md:12-23, :26-34, :38-59, :61-66"

  - id: S-03
    name: WS-SMOKE-LOCATE — resolve the unlocated observer (UV-P-2)
    workstream: WS-SMOKE
    rite: sre
    agents: [observability-engineer]
    external_critic: {rite: 10x-dev, agent: qa-adversary}
    deploy_class: C-INERT
    pr_boundary: "autom8y-asana :: .sos/wip/ ONLY"
    depends_on: []
    mission: >-
      C-17 asserts `the one existing observer matches a literal section name` and that the new
      hook must be built better than that. The framing seat could not locate that observer — its
      positive control DIED over `services/contente-onboarding/src/*` (rc=1, zero output), so the
      zero was correctly WITHHELD as untaken. Locate the observer by name at an explicit autom8y
      ref, or establish with a FIRING control that it does not exist. Then answer the two
      RATIFICATION §3:48 unknowns: does an ACTIVATING placement exist LIVE, and does anything
      observe the transition today?
    entry_criteria:
      - "Reads come from the object DB at an explicit ref — the local autom8y checkout is on fix/wss-wildcard-scope-bypass-closure @ 29e59e81 with 351 dirty files and is NOT an ancestor of origin/main"
      - "origin/main is re-resolved at sprint start by ls-remote; this shape pinned b2b4ae98 and it has already moved twice during this arc"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (d) — the activation refusal. S-07 cannot bind a hook to a lifecycle transition
        that has not been located; without this sprint, WS-SMOKE would be built on an inferred
        referent.
      does_not_discharge: >-
        All four clauses. No hook is built here and no activation is refused.
      hard_gates:
        - "Every zero reported carries a FIRING positive control with visible stderr. The framing seat's control died on this exact probe and the zero was withheld — repeating the dead control and reporting the zero is the named failure mode"
        - "UV-P-2 and UV-P-3 are each DISCHARGED or re-labelled with the reason"
        - "The `readiness.py:41` positional-index fragility — `built conditionally, so index 0 is active on one call and activating on` another — is confirmed or refuted at the current ref, because S-07 must NOT inherit it as a contract"
    exit_artifacts:
      - path: ".sos/wip/LOCATE-c17-lifecycle-observer-2026-09-08.md"
        description: "The observer located or provably absent; the ACTIVATING live-placement answer; the positional-index disposition"
    context:
      - ".sos/wip/frames/name-the-client.md §3.F, §4.2, §11 UV-P-2/UV-P-3"
      - "autom8y @ explicit ref :: services/account-status-recon/src/account_status_recon/{readiness.py:41-43,rules.py:81,verdict_surface.py:101}"

  - id: S-04
    name: WS-JOIN-DESIGN — the M-2 fork, and the PII ruling it must transit
    workstream: WS-JOIN
    rite: 10x-dev + security (co-authored)
    agents: [architect, compliance-architect]
    external_critic: {rite: dre, agent: change-warden}
    deploy_class: C-INERT
    pr_boundary: "autom8y-asana :: .ledge/decisions/ ONLY (an ADR; no code)"
    depends_on: []
    seat_note: >-
      `compliance-architect` (security) is a NAMED PARTICIPANT IN AUTHORING, not an optional
      reviewer — frame §4.1 is explicit. `security-reviewer` is deliberately held OUT of this
      sprint so it remains available as S-06's rite-disjoint critic. `change-warden` (dre) is
      the critic because the frame designates it a REVIEW seat for this lane (it holds the
      premise-correction ledger, DIAGNOSIS §12) and expressly NOT an attest seat — so using it
      here does not contaminate `integrity-architect`'s S-12 attestation.
    mission: >-
      ★ THE HARDEST DESIGN QUESTION IN THE ENVELOPE, and it is not the one it looks like.
      C-15 says `nobody holds the join`. Re-verification found something stronger and it changes
      the shape of the work: `scripts/ebi_witness_ledger.py:21` and `:394` state verbatim that
      `office_phone in the payload are DROPPED (not hashed, not truncated` — and THAT DROP IS
      THE PII CONTROL (DIAGNOSIS §6; premise PR-8 `Redaction is pure cost with no integrity
      role` REFUTED). C-15 also records that putting a phone number into structured logs was
      REJECTED. So WS-JOIN must produce a naming path that resolves an office identity WITHOUT
      reintroducing the dropped identifier onto the log plane. **It transits a ruling it does
      not own.** Enumerate the options exhaustively per `option-enumeration-discipline`,
      recommend one, and name whose ruling the recommendation needs.
    must_enumerate_at_minimum:
      - "(1) EMIT-TIME resolution inside EBI — the plane line carries the resolved office name. Consequence: touches autom8y `services/**` => DEPLOY-CLASS A => R-35-blocked."
      - "(2) READ-TIME resolution in a READER — the plane keeps the 8-hex prefix; a reader resolves it at query time. Consequence: MAY satisfy WS-JOIN without touching the log surface AT ALL, and moves the work out of DEPLOY-CLASS A. Frame fork M-2 names this explicitly."
      - "(3) CENSUS/REGISTRY lookup keyed on the 8-hex prefix — the mechanism `ebi_witness_ledger` already uses (`resolve_disposition_guid(...)` against a census), extended rather than invented."
      - "(4) A DERIVED NON-REVERSIBLE office token minted at onboarding — names the office without ever carrying the phone."
      - "For EACH: does it reintroduce `office_phone` onto the log plane (the rejected act)? what deploy class does it land in? does it need the O-4 operator ruling, or does it route around the ruling entirely?"
    entry_criteria:
      - "The `:21`/`:394` DROP comments are read at an explicit ref, not inherited from this shape"
      - "The 1,252 office-blind residual is understood as ADJACENT and OUT OF SCOPE — adjacency is not inclusion and WS-JOIN must not annex it (frame §10 row 6)"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clauses (a) and (b) — both poles require the office to be NAMEABLE. This sprint decides
        HOW, and its answer determines whether S-06 is R-35-blocked (option 1) or not
        (options 2/3/4). It is the highest-leverage decision on the board.
      does_not_discharge: >-
        All four clauses. An ADR names no office and produces no booking.
      hard_gates:
        - "No recommended option reintroduces `office_phone` onto the log plane. If the recommendation requires that trade, it is NOT recommended — it is SURFACED as operator fork O-4 and the sprint exits on the surfacing"
        - "The deploy class of each option is stated explicitly (§12), because it is the class — not the engineering — that determines whether S-06 can start"
        - "`treat writing a mapping as the whole job` is refuted in-artifact — the frame states that any decomposition doing so has missed the constraint that makes this hard"
    exit_artifacts:
      - path: ".ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md"
        description: "Enumerated options with PII disposition and deploy class per option; a recommendation; the named ruling it needs"
    context:
      - ".sos/wip/frames/name-the-client.md §4.1, §5 WS-JOIN, §9 M-2, §10 row 6"
      - ".ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md C-15, §3:44"
      - "autom8y @ explicit ref :: scripts/ebi_witness_ledger.py:21,:394 and its census resolver"

  - id: S-05
    name: WS-DENOM-SEAM — the extensible denominator boundary (C-16)
    workstream: WS-DENOM
    rite: 10x-dev
    agents: [architect, principal-engineer]
    external_critic: {rite: eunomia, agent: verification-auditor}
    deploy_class: "B-ECS if it lands asana code; A-APPLY if it lands autom8y services/** — decided at PT-01"
    pr_boundary: "ONE repo, ONE PR. The seam does not straddle repos."
    depends_on: [S-04]
    depends_reason: >-
      HARD. The denominator enumerates CLIENTS; a client is whatever identity WS-JOIN
      establishes. A seam built before the identity is chosen would key on the 8-hex prefix and
      inherit exactly the naming gap this initiative exists to close. (Edge given by the frame's
      sequencing, not re-derived.)
    mission: >-
      Build the C-16 seam: Asana section membership is the CURRENT ADAPTER, behind a boundary
      designed for a DB-status-read successor. **This is an ARCHITECTURE DECISION, NOT A SOURCE
      CHOICE.** The boundary's job is to make the successor pluggable WHILE MAKING THREE
      SPECIFIC MIS-WIRINGS UNREPRESENTABLE — not discouraged, not documented, unrepresentable.
    the_three_refusals:
      - "ASR's `activity` is a DIFFERENT QUANTITY — pipeline fetch coverage, not accounts (91 of 144 rows `untriangulated`). A denominator reading that token measures OUR OWN FETCH COVERAGE AND LOOKS PLAUSIBLE. A seam that CAN be wired to it will eventually be wired to it."
      - "`account_status` is a SAME-LINEAGE ECHO of Asana — H/S agreeing with it is one observation read twice, NEVER corroboration."
      - "`active_section_days` is a NEVER-LIT FIELD — NULL on 144/144 rows, two incompatible implementations that are different measurands. If tenure enters the bar, it will not carry it."
    entry_criteria:
      - "PT-01 has ruled the WS-JOIN identity, so the seam knows what it is enumerating"
      - "O-2 (contract-state vs billing-state) is UNDERSTOOD AS OPEN. It blocks CLOSING the population; it does NOT block building the seam. Do not stall on it and do not decide it."
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (c) — `held across the C-3 denominator (ALL active clients, not one)`. This
        sprint IS the denominator's mechanism. Without it, WS-RECEIPT can only ever produce a
        single-office green, which C-3 defines as A DIFFERENT CLAIM, not a partial pass.
      does_not_discharge: >-
        Clauses (a), (b) and (d) entirely; and clause (c) only partially — the seam can
        ENUMERATE the population but cannot CLOSE it until O-2 is spoken.
      hard_gates:
        - "A test demonstrates each of the three mis-wirings is UNREPRESENTABLE — it does not compile, or it fails closed. `documented as discouraged` FAILS this gate"
        - "The Asana adapter is behind the boundary, not hardened INTO it (`silently harden Asana into the boundary it is supposed to sit behind` is the named anti-goal)"
        - "The H/S tier split is NOT used as the denominator — it is an INSTRUMENT and it carries two structural false-S generators (REPORT §5.1 TTL-bounded `posted_count`; §5.2 `coalesce(park_key, canonical_key)` blind to a decline class), with 3 of 10 TIER-S offices not silent at all (`8a9b1a84` BETTER LIFE took 299 arrivals in 30 days)"
        - "The population is reported WITH its O-2 dependency stated, never as closed"
    exit_artifacts:
      - path: "(repo decided at PT-01) :: the denominator seam + its unrepresentability tests"
        description: "Adapter-behind-boundary implementation with three refusals proven by construction"
    context:
      - ".sos/wip/frames/name-the-client.md §4.3, §5 WS-DENOM, §9 M-1, §11 UV-P-6"
      - ".ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md C-16, §3:45-47"

  - id: S-06
    name: WS-JOIN-BUILD — implement the chosen naming path
    workstream: WS-JOIN
    rite: 10x-dev
    agents: [principal-engineer]
    external_critic: {rite: security, agent: security-reviewer}
    deploy_class: "FORK-DEPENDENT — A-APPLY if PT-01 chose emit-time; B-ECS or C-INERT if PT-01 chose read-time/reader"
    pr_boundary: "ONE repo, ONE PR, and it MUST NOT be folded into #1941 (FORBIDDEN, C-1)"
    depends_on: [S-04]
    mission: >-
      Implement the option PT-01 selected, under whatever PII ruling O-4 returned. The office
      becomes nameable from a plane line without a cross-service trace join and without a human
      lookup.
    entry_criteria:
      - "PT-01 PASSED and named the option"
      - "★ If the chosen option requires trading the redaction, the O-4 operator ruling IS SPOKEN. If O-4 is unspoken and the option needs it, THIS SPRINT DOES NOT START — it is not an agent-decidable trade (frame §9 O-4; R-A4 floor context)"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (a) — `a LIVE attributed booking naming that office ... not an 8-hex prefix`.
        This sprint supplies the naming capability that clause (a) asserts and that clause (b)
        reuses for the failure pole.
      does_not_discharge: >-
        Clause (a) is NOT discharged by a merged PR — the clause requires a LIVE line, which
        requires the code to be SERVED, which is a deploy event this sprint does not perform.
        Clauses (b), (c), (d) untouched.
      hard_gates:
        - "`office_phone` does not appear on the log plane. Verified by a two-sided test: the resolved name IS present AND the dropped identifier is NOT — a one-sided assertion fails this gate"
        - "The negative pole is buildable with the same mechanism — if the naming path works for success lines but cannot name an office on a FAILURE line, clause (b) is unreachable and the sprint is mis-built"
        - "`PRs merged` is NOT claimed as clause (a). The exit is a merged, unserved capability and must be reported as such"
    exit_artifacts:
      - path: "(repo per PT-01) :: the naming resolution path + two-sided presence/absence tests"
        description: "Office nameable from a plane line; dropped identifier provably still dropped"
    context:
      - ".ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md (S-04 output)"
      - "autom8y PR #2073 @ 8c9aa11f — `feat(ebi): name the clinic on booking success lines`, the SUCCESS half already authored"

  - id: S-07
    name: WS-SMOKE-BUILD — the activation gate on a hook we own
    workstream: WS-SMOKE
    rite: sre
    agents: [platform-engineer]
    external_critic: {rite: 10x-dev, agent: qa-adversary}
    deploy_class: A-APPLY
    pr_boundary: "autom8y :: ONE service, ONE PR. Deploy-shaped => R-35."
    depends_on: [S-03]
    depends_reason: "HARD. A hook cannot bind to a lifecycle transition that has not been located (UV-P-2)."
    seat_note: >-
      ★ Deliberately assigned to `sre`, NOT to `dre`, even though C-17 is activation-gating and
      dre owns activation gates. Reason: the frame binds `integrity-architect` (dre) as the
      rite-disjoint ATTESTER under critic-never-author, and `any dre seat that BUILDS a
      workstream in this envelope MAY NOT attest it`. Keeping dre out of every BUILD sprint
      keeps the attestation rite pristine rather than merely seat-clean. This is a Pythia
      re-seat within R1, which frame §2 expressly permits.
    mission: >-
      C-17: an account may not activate without an end-to-end proof that its own pipe works.
      Bind the smoke to the LIFECYCLE TRANSITION on a hook WE own, and build it better than the
      incumbent — which C-17 says matches a LITERAL SECTION NAME.
    entry_criteria:
      - "S-03 located the observer or proved its absence with a firing control"
      - "R-35 disposition for this path is understood: the sprint may BUILD and PLAN; it may not APPLY (R-72: `The plan lane runs read-only; the R-35 EBI freeze forbids applies, not plans`)"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (d) — `an account that attempts activation without a passing end-to-end pipe
        proof is REFUSED activation (C-17), demonstrated two-sided: a healthy pipe activates, a
        broken pipe does not`. This is the ONLY preventive clause and the only sprint that
        serves it.
      does_not_discharge: >-
        Clauses (a), (b), (c). And clause (d) itself is not discharged until the refusal is
        demonstrated on a LIVE activation attempt, which requires a deploy this sprint cannot make.
      hard_gates:
        - "The hook does NOT match on a literal section name (the named anti-goal — it is what C-17 says to be built better than)"
        - "The hook does NOT inherit a positional index as a contract. `readiness.py:41`: constituents are `built conditionally, so index 0 is active on one call and activating on` another — a positional index whose meaning depends on which call built it is EXACTLY the defect class C-17 forbids"
        - "★ The smoke has an ANSWERER, not merely a firing. An observer that is wired, fires, and is unanswered is FACE 6 — which the EXTRACTION calls THE MORE DANGEROUS STATE BECAUSE IT FEELS SOLVED. A smoke whose failure notifies nothing FAILS this gate"
        - "Two-sided: a healthy pipe activates AND a broken pipe is REFUSED. A one-sided pass is not a gate, it is a formality"
    exit_artifacts:
      - path: "autom8y :: the activation smoke hook + two-sided activate/refuse tests"
        description: "Lifecycle-bound pipe proof with a named answerer"
    context:
      - ".sos/wip/LOCATE-c17-lifecycle-observer-2026-09-08.md (S-03 output)"
      - ".sos/wip/EXTRACTION-observer-law-and-untaken-zero-2026-09-08.md:322-346 (face 6)"

  - id: S-08
    name: WS-DARK-DISPOSITION — dispose of the six-office class
    workstream: WS-DARK
    rite: clinic
    agents: [attending, diagnostician]
    external_critic: {rite: eunomia, agent: verification-auditor}
    deploy_class: C-INERT
    pr_boundary: "autom8y-asana :: .ledge/decisions/ ONLY"
    depends_on: [S-01]
    depends_reason: "HARD. The disposition IS the Q-C answer; there is nothing to dispose before the measurement."
    mission: >-
      Turn Q-C's answer into a disposition of record for the six dark offices — two escalated by
      a human, FOUR NEVER ESCALATED BY ANYONE. Per §4.4 this may not be an engineering problem
      at all: the receiving chain is `provably working at every layer we own`, and the one
      unexcluded possibility is P1 — the clinics never switched forwarding on — because
      WE CANNOT SHOW THEY WERE EVER ASKED.
    entry_criteria:
      - "S-01 exited with one of its three stated forms"
      - "O-6 (disposition of the four never-escalated offices) is surfaced to the operator; where the disposition is a customer-facing act it is NOT agent-decidable"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (c). Six offices either enter the C-3 denominator as broken pipes that the bar
        must turn green, or leave it as never-onboarded accounts. Until disposed, the
        denominator has a hole in it and clause (c) cannot be evaluated honestly.
      does_not_discharge: >-
        All four clauses. A disposition is a ruling, not a booking.
      hard_gates:
        - "NO pipeline cure is built for these accounts — DIAGNOSIS explicitly PARKS it: `Engineering effort aimed at the pipeline for these two accounts would be building a cure for a cost that has not been measured to exist`"
        - "★ R-A4 FLOOR: any remedy that is a CUSTOMER-VISIBLE OUTBOUND ACT (re-sending decks, contacting the clinics) is ABOVE EVERY TIER and is the operator's alone. `No grant phrasing, however explicit, lifts it.` The sprint may RECOMMEND; it may not SEND"
        - "The six are stated as zero WITHIN RETENTION, never as `never` (T-9)"
    exit_artifacts:
      - path: ".ledge/decisions/DISPOSITION-dark-client-class-2026-09-08.md"
        description: "In-denominator or out, per office, with the O-6 operator surface stated"
    context:
      - ".sos/wip/PROBE-qc-outbound-deck-delivery-2026-09-08.md (S-01 output)"
      - ".sos/wip/frames/name-the-client.md §4.4, §5 WS-DARK"

  - id: S-09
    name: WS-RECEIPT — the two-sided per-client receipt AND its reader
    workstream: WS-RECEIPT
    rite: 10x-dev
    agents: [principal-engineer, architect]
    external_critic: {rite: sre, agent: observability-engineer}
    deploy_class: A-APPLY (instrument) + the reader per PT-01's repo ruling
    pr_boundary: "The instrument and the reader MAY be separate PRs; neither may be folded into #1941 (FORBIDDEN, C-1)."
    depends_on: [S-05, S-06]
    depends_reason: >-
      HARD on both. The receipt is evaluated ACROSS the denominator (needs S-05) and it NAMES
      the office on both poles (needs S-06). Given by the frame's sequencing — WS-DENOM is
      upstream of WS-RECEIPT; WS-JOIN is upstream of both — not re-derived.
    mission: >-
      Build the bar's instrument: a live attributed booking naming that office, AND a failure
      for the SAME office that also names it, with its kind, never blank — checkable FROM THE
      LOG PLANE WITH NO HUMAN IN THE LOOP, evaluated across ALL ACTIVE CLIENTS.
      ★ AND RESOLVE MECHANISM FORK M-4: whether the READER is a deliverable of this sprint.
      This shape rules that IT IS. REPORT §2 is unambiguous — a green nightly job writes to five
      orphan branches nobody reads, and `the missing primitive is not a consumer; it is a
      READER`. Shipping a per-client attribution surface that nothing reads would be
      built-and-unconsumed (face 4) SHIPPED BY THE WAVE THAT EXTRACTED THE LAW.
    entry_criteria:
      - "S-05's seam exposes the population; S-06's naming path resolves an office"
      - "PT-03 PASSED — the three mis-wirings are proven unrepresentable, so the receipt cannot silently measure our own fetch coverage"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clauses (a), (b) and (c) simultaneously — this workstream IS the bar's instrument. It is
        the only sprint that touches three clauses at once.
      does_not_discharge: >-
        ★ ALL OF THEM, and this is the sprint most likely to be misreported. An instrument that
        CAN produce the receipt is not the receipt. The predicate requires a LIVE attributed
        booking held across the denominator — an ATTESTED OBSERVATION, which is S-12's, not
        this sprint's. Clause (d) is untouched here.
      hard_gates:
        - "★ THE NEGATIVE POLE IS BUILT IN THIS SPRINT, NOT DEFERRED. `The negative pole is not a test; it is half the receipt.` A sprint that exits with the success line naming the office and the failure line still blank has built HALF an instrument and must not report exit"
        - "★ A READER EXISTS AND IS NAMED. Not a consumer — a READER. If nothing reads the surface, this sprint has shipped face 4 and FAILS regardless of test status"
        - "Evaluation is across the C-3 denominator. A single-exemplar green is A DIFFERENT CLAIM and must be reported as one, never as a partial pass"
        - "★ The face-4 hazard does NOT transfer from PT-08: it was tested for S-14 and did not fire there because `semantic_alarms.tf:69-70` is dimensioned generically so new classes ride the existing dimension. THAT RESULT DOES NOT TRANSFER to a per-client attribution surface and must not be cited as if it did"
        - "S-14's AFTER figure (41.6% -> 21.2%) is NOT cited as evidence — it is a PROJECTION with parse-class 30 vs 10 UNRECONCILED (UV-P-4)"
    exit_artifacts:
      - path: "(repos per PT-01) :: the two-sided receipt instrument + the reader"
        description: "Both poles, denominator-wide, with a named reader"
    context:
      - ".sos/wip/REPORT-tier-split-consumer-2026-09-08.md §0, §2"
      - ".sos/wip/EXTRACTION-observer-law-and-untaken-zero-2026-09-08.md:241-299 (face 4)"
      - ".sos/wip/frames/name-the-client.md §5 WS-RECEIPT, §9 M-4"

  - id: S-10
    name: WS-CONTAIN-PLAN — exercise the R-72 plan lane
    workstream: WS-CONTAIN
    rite: sre
    agents: [platform-engineer]
    external_critic: {rite: eunomia, agent: pipeline-cartographer}
    deploy_class: READ-ONLY (no merge, no apply)
    pr_boundary: "NONE — this sprint opens no PR and merges nothing. Its output is an artifact in autom8y-asana .sos/wip/."
    depends_on: []
    mission: >-
      ★ THE PARALLELISM WIN NOBODY HAS TAKEN. R-72 states verbatim: `The plan lane runs
      read-only; the R-35 EBI freeze forbids applies, not plans.` CUSTODY PT-07 finding 3
      records R-72 as `Surfaced, not acted on`, with NO WATCHER, and the frame notes C-10's
      `terraform plan` HAS NEVER BEEN RUN. Run it. Produce the plan diff for the C-10 supersede
      so that when R-35 lifts, S-11 executes against a plan already read rather than discovering
      the blast radius at apply time.
    entry_criteria:
      - "R-72's text is re-read at source and confirmed to permit plans — this sprint's entire licence rests on it and it must not be inherited from this shape"
      - "#2071 @ 6265e378 and #2073 @ 8c9aa11f are re-verified live for head and base"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (b) — `never blank`. The kinding cure lives behind the apply this plan
        de-risks. Running the plan now converts an unbounded wait into a wait with a known
        blast radius, which is the only part of the R-35 problem that is inside our reach.
      does_not_discharge: >-
        All four clauses. A plan is not an apply and an apply is not a booking.
      hard_gates:
        - "★ NOTHING IS APPLIED. NOTHING IS MERGED. R-35 is NOT lifted, narrowed, or overwritten by this sprint or by its output (C-11, binding)"
        - "The plan output records the blast radius of the C-10 supersede explicitly, including whether the two images are separable — because C-1's image-event law makes BUNDLING = REFUSAL"
        - "The pre-existing `alarm_description` 1001-vs-1000 red is identified in the plan and left ALONE — it is PRE-EXISTING ON MAIN, proven four ways, belongs to the SEV-1-delivery-claim lane, and CURING IT HERE WOULD BE BUNDLING (frame §10 row 5)"
    exit_artifacts:
      - path: ".sos/wip/PLAN-c10-supersede-blast-radius-2026-09-08.md"
        description: "The never-run terraform plan for the C-10 supersede, read-only, with blast radius and separability"
    context:
      - ".sos/wip/CUSTODY-name-the-zero-wave2-register-2026-09-08.md:38-59, :61-66"
      - "autom8y @ explicit ref :: .github/workflows/service-deploy-lambda.yml:304"

  - id: S-11
    name: WS-CONTAIN-DISPOSITION — the C-10 supersede executes
    workstream: WS-CONTAIN
    rite: sre
    agents: [platform-engineer, incident-commander]
    external_critic: {rite: eunomia, agent: verification-auditor}
    deploy_class: A-APPLY
    pr_boundary: "ONE image event. ONE PR merge. Bundling two image events = REFUSAL (C-1)."
    depends_on: [S-10]
    blocked_by_gate: "★ R-35 LIFT (operator fork O-1) — UNRULED, NO WATCHER, NO FORCING FUNCTION"
    mission: >-
      Execute C-10: the next image the intake serves is the one carrying S-14's cure. This is a
      DISPOSITION OF RECORD that executes WHEN R-35 LIFTS — never by this envelope's motion.
    entry_criteria:
      - "★ R-35 IS LIFTED BY THE OPERATOR, ON THE RECORD. Nothing in this initiative lifts it. If R-35 is not lifted, THIS SPRINT DOES NOT START — and its not-starting is the correct outcome, not a blocked one"
      - "S-10's plan has been READ, and its blast radius accepted"
      - "PT-04 PASSED"
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: >-
        Clause (b) — specifically `with its kind, never blank`. #2071 marks the terminal decline
        sites so a failure carries a KIND. Until it is SERVED, failures in that class are
        recorded under NO KIND and the negative pole is structurally blank for them.
      does_not_discharge: >-
        Clauses (a), (c), (d). And clause (b) is not discharged by the apply — it is discharged
        when a REAL failure for a REAL office is observed carrying its kind. A served image is
        explicitly excluded by the predicate: `NOT a served image`.
      hard_gates:
        - "ONE image event. Bundling two = REFUSAL (C-1 image-event law)"
        - "NO cure is folded into #1941 — FORBIDDEN"
        - "The AFTER figure is MEASURED post-apply, or it stays a PROJECTION and is labelled one. UV-P-4 discharges here or not at all"
        - "The parse-class 30-vs-10 gap is TRACKED SEPARATELY and binds only citations of the parse class. It does NOT gate the AFTER figure: S-14 RECEIPT LEG 1 :112 marks the parse row 'different stage - out of this file's scope' and :116 states the projected delta is 'exactly -52, entirely from :725'. The parse class contributes ZERO to 41.6%->21.2%. The real precondition for quoting AFTER is the line above: a post-deploy window."
    exit_artifacts:
      - path: ".ledge/decisions/DISPOSITION-c10-supersede-executed-2026-09-08.md"
        description: "The image event of record, with the measured AFTER or an explicit projection label"
    context:
      - ".sos/wip/PLAN-c10-supersede-blast-radius-2026-09-08.md (S-10 output)"

  - id: S-12
    name: ATTEST — the rite-disjoint attestation of the bar
    workstream: "(all seven)"
    rite: dre
    agents: [integrity-architect]
    external_critic: "N/A — this sprint IS the external critic. Its own self-assessment caps MODERATE."
    deploy_class: C-INERT
    pr_boundary: "autom8y-asana :: .sos/wip/dre/ + .ledge/decisions/ ONLY"
    depends_on: [S-06, S-07, S-09, S-11]
    depends_reason: >-
      HARD on all four. (a) needs S-06's naming SERVED; (b) needs S-09's failure pole AND
      S-11's kinding; (c) needs S-05 via S-09; (d) needs S-07's activation refusal. S-11's
      inclusion is what places the ENTIRE ATTESTATION behind R-35.
    seat_note: >-
      `integrity-architect` (dre) is the frame-designated attester, rite-disjoint from the
      active 10x-dev rite per R1. It BUILDS NOTHING in this shape — verified: dre appears only
      as `change-warden` (review, S-04) and `integrity-architect` (attest, S-12). WS-SMOKE was
      deliberately re-seated from dre to sre for exactly this reason. Critic-never-author holds
      at RITE level here, not merely at seat level.
    mission: >-
      Attest — or refuse to attest — that the realization predicate is met. Per
      `three-evidence-leg-attestation` the attester INHERITS NONE of the builders' proofs and
      re-derives every leg with its own hands: (a) the keystone re-run UNCACHED, (b) the
      discriminating teeth re-proved with the attester's OWN fresh construction, (c) the live
      surface observed DIRECTLY.
    exit_criteria:
      realization_predicate_verbatim: |
        "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
        sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a
        failure for the SAME office also names it, with its kind, never blank — held across the
        C-3 denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.
      advances: "All four clauses."
      does_not_discharge: >-
        ★ THIS IS THE ONLY SPRINT THAT DISCHARGES — and only if all four clauses hold
        simultaneously across the denominator. A three-of-four result is UNATTESTED, not
        partially attested.
      hard_gates:
        - "A LIVE attributed booking line naming its office, observed DIRECTLY by the attester — not a test fixture, not a log excerpt supplied by a builder"
        - "A REAL failure for the SAME office, naming it, carrying its kind, NEVER BLANK — constructed by the attester's own hand"
        - "Held across ALL ACTIVE CLIENTS per the S-05 seam and the S-08 disposition. One office is A DIFFERENT CLAIM"
        - "An activation REFUSAL demonstrated two-sided on a real attempt"
        - "NOT `PRs merged`. NOT a served image. NOT a projection"
        - "Every zero in the attestation carries a firing positive control with visible stderr"
    exit_artifacts:
      - path: ".sos/wip/dre/VERDICT-name-the-client-realization.md"
        description: "The four-clause satisfaction table with per-leg re-derivation, or an honest UNATTESTED"
      - path: ".know/telos/name-the-client.md (verified_realized field update)"
        description: "ATTESTED / ATTESTED-WITH-FLAG / UNATTESTED — never silently omitted"
    context:
      - "All prior sprint artifacts; .know/telos/name-the-client.md"
```

## 3. Potnia Consultation Points

**Placement doctrine, and it is a correction.** *A checkpoint that cannot change an act is
ceremony.* The parent wave fired **eight** checkpoints and its own close ruled that the
surfacing loop **had become an instance of the disease it named**. This shape places **five**,
and each one has a named act it can change. Checkpoints that a reader might expect and that are
**deliberately ABSENT** are listed at the end with the reason — an unplaced checkpoint recorded
is a decision; an unplaced checkpoint unrecorded is an omission.

```yaml
checkpoints:

  - id: PT-01
    after: S-04
    blocks: [S-05, S-06]
    evaluates: "Clause (a) reachability, and the deploy class of the entire join path"
    the_act_it_changes: >-
      Whether S-06 is a DEPLOY-CLASS-A sprint frozen behind R-35, or a read-time/reader sprint
      that reaches clause (a) WITHOUT touching the log surface at all. This single ruling moves
      the join path into or out of the freeze. It also fixes S-05's repo and PR boundary.
    questions:
      - "Which option was recommended, and does it reintroduce `office_phone` onto the log plane? If yes -> it is NOT ratifiable by any agent; it is O-4 and the fork exits to the operator"
      - "Was the option set exhaustive? Emit-time, read-time, census-lookup, derived-token — all four dispositioned, per `option-enumeration-discipline`?"
      - "★ Does the recommendation route AROUND the PII ruling or THROUGH it? Routing around it is a legitimate and preferred answer — frame M-2 says read-time `may satisfy WS-JOIN without touching the log surface at all`"
      - "Does the recommended path name an office on a FAILURE line, not only a success line? If it cannot, clause (b) is unreachable and the design is half a design"
    gate: hard
    on_fail: >-
      HALT S-05 and S-06. If the failure is `needs a ruling we do not own`, that is NOT a
      checkpoint failure — it is the correct exit, and the fork routes to the operator as O-4.
      Distinguish the two in the checkpoint record.

  - id: PT-02
    after: S-01
    blocks: [S-08]
    evaluates: "Clause (c) — whether the C-3 denominator has a hole in it"
    the_act_it_changes: >-
      Whether WS-DARK becomes a disposition inside this initiative or RELOCATES WHOLESALE into
      onboarding delivery. Frame §4.4: the outcome `may relocate the entire class`. It also
      determines whether six offices are inside or outside the denominator S-05 is building.
    questions:
      - "★ Did the positive control FIRE, with visible stderr? If it did not, there is no result — only an untaken zero — and the checkpoint evaluates NOTHING. This exact control died on the framing seat"
      - "Which of the three forms did S-01 return: DELIVERED / NEVER SENT / INSTRUMENT UNAVAILABLE?"
      - "If NEVER SENT: does the class leave engineering entirely and become WS-SMOKE's preventive twin? Frame §4.4 says WS-SMOKE (C-17) IS the preventive twin of WS-DARK's diagnosis"
      - "If INSTRUMENT UNAVAILABLE (403/unentitled): is the entitlement an operator act? Then the highest-value unknown in the client lane stays open and MUST be re-flagged, not quietly absorbed"
    gate: hard
    on_fail: "S-08 does not start. An undetermined dark class is carried EXPLICITLY into S-05's population as a named hole, never silently."

  - id: PT-03
    after: S-05
    blocks: [S-09]
    evaluates: "Clause (c) — that the denominator measures CLIENTS and not our own pipeline"
    the_act_it_changes: >-
      Whether S-09 may start building the receipt. A receipt evaluated over a denominator wired
      to ASR's `activity` would measure OUR OWN FETCH COVERAGE, look plausible, and produce a
      green that means nothing. That is the trap the ratification says `WOULD HAVE WRECKED THE
      BAR SILENTLY`.
    questions:
      - "Are all three mis-wirings UNREPRESENTABLE — proven by a test that fails closed — or merely documented as discouraged? Documented FAILS"
      - "Is the Asana adapter BEHIND the boundary, or has Asana been hardened INTO it?"
      - "Is the population reported WITH its O-2 dependency (contract-state vs billing-state) stated, rather than as closed?"
      - "Was the H/S tier split kept OUT of the denominator? It is an instrument with two structural false-S generators and 3 of 10 TIER-S offices are not silent at all"
    gate: hard
    on_fail: "S-09 does not start. A receipt over an unproven denominator is worse than no receipt — it is a plausible-looking green."

  - id: PT-04
    before: S-11
    blocks: [S-11]
    evaluates: "Clause (b)'s `never blank`, and the C-11 wall"
    the_act_it_changes: "Whether a `terraform apply` fires against production. This is the highest-consequence checkpoint on the board."
    questions:
      - "★ Is R-35 LIFTED, by the operator, on the record? Not `assumed lifted`, not `probably fine`, not `nobody objected`. If the answer is anything other than an explicit operator lift, S-11 DOES NOT START"
      - "Has S-10's plan been read, and is the blast radius accepted?"
      - "Is this ONE image event? Two bundled = REFUSAL (C-1)"
      - "Is the pre-existing `alarm_description` red still untouched? Curing it here is BUNDLING and belongs to the SEV-1-delivery-claim lane"
      - "Is anything folded into #1941? FORBIDDEN"
    gate: hard
    on_fail: >-
      S-11 does not start, and — this is the important part — ITS NOT-STARTING IS THE CORRECT
      OUTCOME, not a blocked one. The gate firing correctly is a working gate. Do not escalate a
      correctly-firing guard into a problem to be routed around; the parent wave already
      recorded that exact misreading.

  - id: PT-05
    after: [S-07, S-09, S-11]
    blocks: [S-12]
    evaluates: "All four clauses — attestation readiness"
    the_act_it_changes: "Whether the rite-disjoint attester is dispatched at all. Dispatching S-12 against an incomplete predicate burns the attestation and produces a UNATTESTED that costs a re-walk."
    questions:
      - "Are BOTH poles live? A positive pole alone is HALF the receipt and dispatching on it manufactures the one-sided receipt this initiative exists to close"
      - "Does the receipt hold across ALL ACTIVE CLIENTS, or one exemplar? One exemplar is A DIFFERENT CLAIM"
      - "Does a real failure carry its KIND, never blank — which requires S-11 to have SERVED the cure?"
      - "Is the activation refusal demonstrated two-sided on a real attempt?"
      - "★ Has any dre seat BUILT anything in this initiative? If yes, critic-never-author is breached and the attester must be re-seated BEFORE dispatch, not after the verdict"
    gate: hard
    on_fail: "S-12 is not dispatched. The honest state is UNATTESTED and it is written as UNATTESTED — the telos field is never silently omitted."
```

### Checkpoints deliberately NOT placed, and why

| Not placed | Why it would be ceremony |
|---|---|
| After **S-02** (WS-CARGO) | Custodial. Its output is a registry; no downstream act branches on it. A checkpoint here would surface a registry to a coordinator who cannot change what the registry says. **The registry's own `NO WATCHER` rows ARE the surfacing** — a checkpoint on top of them would be the surfacing-loop disease the parent wave named. |
| After **S-03** (SMOKE locate) | Its result feeds exactly one consumer (S-07) as an input, not as a branch. S-07's design changes with the finding; no *act* forks. The finding travels in the artifact. |
| After **S-06** (JOIN build) | The fork was already taken at PT-01. Post-build there is nothing left to decide — the exit gates (`office_phone` absent, failure-line nameable) are pass/fail conditions the sprint owns, and its rite-disjoint critic is `security-reviewer`. A checkpoint would re-adjudicate a settled fork. |
| After **S-10** (CONTAIN plan) | The plan is an INPUT to PT-04, which already asks whether it was read and accepted. A separate checkpoint would ask the same question twice. |
| After **S-12** (ATTEST) | S-12 IS the terminal evaluation. A checkpoint after the attester would be a coordinator grading the rite-disjoint critic — inverting the critic relationship the whole design rests on. |

## 4. Execution Sequence

**Dispatcher invariant.** The **main thread is the sole dispatcher** — agents cannot spawn
agents. Every `Task(...)` below is a main-thread act. Each dispatch preloads **only its
station's skills**; no dispatch inherits the full mena set.

### 4.0 Pre-flight — main thread, before any sprint

```
# (i) Re-resolve BOTH origin/main labels. They have moved three times in this arc.
git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana rev-parse origin/main
git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y ls-remote origin refs/heads/main

# (ii) Transplant the telos block (closes Gate A on disk).
#     ★ SEAT GAP — see §14: the frame's Next-Command says Task(moirai). There is NO
#     moirai.md in .claude/agents/ (verified own-hands, with a negative control).
#     Do ONE of:
#       (a) main thread performs the transplant directly, OR
#       (b) `ari agent summon moirai` then restart CC, then Task(moirai).
#     Transplant frame §2's YAML block VERBATIM to .know/telos/name-the-client.md,
#     INCLUDING the "## Amendment — 2026-09-08 (R-17 BAR-NOT-DATE)" subsection — that
#     subsection is what makes verification_deadline: null LAWFUL rather than a stub.
#     Then flip the frame frontmatter telos_file_status: INSCRIBED.

# (iii) ★ THE ONLY SELF-FIRING CLOCK ON THE BOARD, and it is not this initiative's.
#     C-13 / R-65 — dead-letter row bd875254…: HARD CUT 2026-09-09T18:00Z, after which it
#     resolves LOST AUTOMATICALLY; reap 2026-09-10T05:28:46Z. OPERATOR'S OWN HAND — he
#     reads the receiver's handler FIRST. At this shape's authoring instant the window is
#     under ~24 h. No sprint below holds it and no sprint below may consume it.
```

**Rite transitions: NONE are required for sprints S-01..S-12.** See §6 — every rite this shape
uses is already co-seated, verified live. No `ari sync`, no CC restart.

### 4.1 Session

```
/sos start --initiative=name-the-client
```

```yaml
execution_sequence:

  - phase: WAVE-0 (five sprints, FULLY PARALLEL, zero hard upstream edges)
    parallel: true
    note: >-
      ★ This is the parallelism that makes decomposition worth doing. All five are
      DEPLOY-INERT or READ-ONLY (§12) and NONE is blocked by R-35. Dispatch them together;
      do not serialize them into a queue.
    dispatches:
      - "Task(diagnostician)  -> S-01 WS-DARK-PROBE   [clinic]   # Q-C, sequenced FIRST on purpose: highest-value unknown in §4 assumption 1"
      - "Task(verification-auditor) -> S-02 WS-CARGO  [eunomia]  # + entropy-assessor for authoring; NOTE entropy-assessor has NO Bash"
      - "Task(observability-engineer) -> S-03 SMOKE-LOCATE [sre]"
      - "Task(architect)      -> S-04 WS-JOIN-DESIGN  [10x-dev + security/compliance-architect co-author]"
      - "Task(platform-engineer) -> S-10 CONTAIN-PLAN [sre]      # R-72 plan lane, surfaced-not-acted-on since PT-07"
    critics_after:
      - "Task(observability-engineer) critiques S-01 · Task(qa-adversary) critiques S-02 and S-03 · Task(change-warden) critiques S-04 · Task(pipeline-cartographer) critiques S-10"

  - phase: CHECKPOINTS PT-01 (after S-04) and PT-02 (after S-01)
    parallel: true
    commands:
      - "Task(potnia, 'PT-01: evaluate S-04 against clause (a) reachability and the deploy class of the join path')"
      - "Task(potnia, 'PT-02: evaluate S-01 against clause (c) — is the denominator holed?')"
    forks_to_operator:
      - "O-4 — the PII ruling WS-JOIN transits, IF PT-01's recommendation needs it"
      - "O-6 — disposition of the four never-escalated dark offices, IF S-01 returned NEVER SENT"
    note: "At a genuine fork, engage Pythia-navigation via `/consult` — ★ NOT `Task(pythia)`; there is no pythia.md seat in this repo (§14)."

  - phase: WAVE-1 (parallel after their own gates clear)
    parallel: true
    dispatches:
      - "Task(architect)         -> S-05 WS-DENOM-SEAM  [10x-dev]  # needs PT-01"
      - "Task(principal-engineer)-> S-06 WS-JOIN-BUILD  [10x-dev]  # needs PT-01 (+ O-4 if the option requires it)"
      - "Task(platform-engineer) -> S-07 WS-SMOKE-BUILD [sre]      # needs S-03"
      - "Task(attending)         -> S-08 DARK-DISPOSITION [clinic] # needs PT-02"
    note: "S-05/S-06 share an upstream (S-04) but NOT each other — they run concurrently. S-07 and S-08 are independent of both."
    critics_after:
      - "Task(verification-auditor) critiques S-05 · Task(security-reviewer) critiques S-06 · Task(qa-adversary) critiques S-07 · Task(verification-auditor) critiques S-08"

  - phase: CHECKPOINT PT-03 (after S-05)
    commands:
      - "Task(potnia, 'PT-03: are the three mis-wirings UNREPRESENTABLE, or merely documented?')"

  - phase: WAVE-2
    dispatches:
      - "Task(principal-engineer) -> S-09 WS-RECEIPT [10x-dev]  # needs S-05 + S-06 + PT-03"
    critics_after:
      - "Task(observability-engineer) critiques S-09"

  - phase: THE R-35 WALL — CHECKPOINT PT-04
    blocking: true
    note: >-
      ★ This phase has NO agent action and NO forcing function. It waits on operator fork O-1.
      RATIFICATION §2: `nothing rules what lifts it ... outstanding since 09-06 with no forcing
      function.` NO WATCHER. Everything downstream — including the entire attestation — sits
      behind it.
    commands:
      - "Task(potnia, 'PT-04: is R-35 lifted by the operator on the record? If not, S-11 does not start and that is CORRECT.')"

  - phase: WAVE-3 (gated on R-35)
    dispatches:
      - "Task(platform-engineer) -> S-11 CONTAIN-DISPOSITION [sre]"
    critics_after:
      - "Task(verification-auditor) critiques S-11"

  - phase: CHECKPOINT PT-05 (after S-07, S-09, S-11)
    commands:
      - "Task(potnia, 'PT-05: are both poles live across the denominator, with kinds, plus a two-sided activation refusal?')"

  - phase: ATTEST
    dispatches:
      - "Task(integrity-architect) -> S-12 ATTEST [dre, rite-disjoint, builds nothing]"

  - phase: close
    commands:
      - "/sos wrap"
```

### 4.2 Every dispatch carries these four fences — VERBATIM, non-negotiable

Paste into **every** `Task(...)` prompt. They are not style notes; each has a live incident behind it.

```
1. THE UNTAKEN-ZERO FENCE. Every zero you report must carry a POSITIVE CONTROL that
   FIRED and VISIBLE STDERR, or the zero is UNTAKEN and UNREPORTABLE. N=12 across 5 tools
   and 6 seats; 11/11 failed in the SAFE-LOOKING direction; 11/11 were caught by RE-RUNNING,
   0 by inspection. It fired TWICE on the framing seat during framing and both zeros were
   correctly WITHHELD. It fired once on THIS shaping seat (a BSD-sed negative control that
   "passed" only because the tool had already errored). If your control dies, you have no
   result — say so.

2. THE STALE-TREE TRAP. Read the object DB at EXPLICIT REFS.
   /Users/tomtenuta/Code/a8/a8/repos/autom8y is on branch
   fix/wss-wildcard-scope-bypass-closure @ 29e59e81 with 351 dirty files, and
   `git merge-base --is-ancestor 29e59e81 origin/main` returns rc=1 — NOT AN ANCESTOR.
   Use `git -C <repo> show <explicit-ref>:<path>`. Re-resolve origin/main at YOUR start:
   it moved cc88b75e -> 57e21107 -> b2b4ae98 during framing and shaping alone.

3. "${VAR}:path" BRACING. Quoting alone does NOT protect against zsh's :s modifier — it
   fires INSIDE double quotes. Only "${R}:services/..." is safe; "$R:services/..." is not.
   Safest of all: pass paths as SEPARATE ARGUMENTS and avoid the construction entirely.

4. rg CORPUS BLINDNESS. `.sos/` is hidden AND gitignored — BOTH `--hidden` AND
   `--no-ignore` are required there. `.ledge/`, `.know/`, `.github/` need only `--hidden`.
   EXPLICIT PATHS ARE ALWAYS SAFE.
```

**Plus, per dispatch:** the realization predicate VERBATIM (frame §1); the sprint's
`advances` / `does_not_discharge` pair; and the sprint's own `named_traps` where present.

## 5. Critical Path

### The DAG — hard edges only

```
WAVE 0  (no upstream — all five dispatch together)
┌──────────────────────────────────────────────────────────────────────────┐
│  S-01 Q-C probe      S-02 CARGO      S-03 SMOKE-LOCATE                   │
│  [clinic]            [eunomia]       [sre]                               │
│                                                                          │
│  S-04 JOIN-DESIGN                    S-10 CONTAIN-PLAN                   │
│  [10x-dev+security]                  [sre, R-72 read-only]               │
└──────────────────────────────────────────────────────────────────────────┘
     │                     │                    │                  │
     │ PT-02               │ PT-01              │                  │
     ▼                     ▼                    ▼                  │
   S-08              ┌────────────┐          S-07                  │
   DARK-DISP         │ S-05 DENOM │          SMOKE-BUILD           │
   [clinic]          │ S-06 JOIN  │          [sre]                 │
                     └────────────┘                                │
                        │     │                 │                  │
                   PT-03│     │                 │                  │
                        ▼     ▼                 │                  │
                     ┌──────────────┐           │                  │
                     │ S-09 RECEIPT │           │                  │
                     │  + READER    │           │                  │
                     └──────────────┘           │                  │
                            │                   │                  │
                            │              ┌────┘                  ▼
                            │              │              ★ PT-04 — R-35 LIFT
                            │              │                 (O-1, UNRULED,
                            │              │                  NO WATCHER,
                            │              │                  NO FORCING FUNCTION)
                            │              │                       │
                            │              │                       ▼
                            │              │                  S-11 CONTAIN-DISP
                            │              │                       │
                            └──────────────┴───────────┬───────────┘
                                                       │
                                                    PT-05
                                                       ▼
                                              S-12 ATTEST  [dre]
                                          (THE ONLY DISCHARGING SPRINT)
```

### Hard edges, and only hard edges

| Edge | Why it is HARD | Source |
|---|---|---|
| S-04 → S-05 | The denominator enumerates CLIENTS; a client is whatever identity WS-JOIN establishes | frame sequencing: *WS-JOIN is upstream of both* |
| S-04 → S-06 | Cannot build the naming path before the mechanism is chosen | PT-01 fork |
| S-05 → S-09 | The receipt is evaluated ACROSS the denominator | frame sequencing: *WS-DENOM is upstream of WS-RECEIPT* |
| S-06 → S-09 | The receipt NAMES the office on both poles | clause (a)+(b) |
| S-03 → S-07 | A hook cannot bind to an unlocated lifecycle transition | UV-P-2 |
| S-01 → S-08 | The disposition IS the measurement's answer | DIAGNOSIS GO/PARK |
| S-10 → S-11 | Do not apply against a plan nobody read | R-72 / C-11 |
| **S-11 → S-12** | **Clause (b) requires the failure to name `its kind, never blank`. #2071 supplies the kind for the terminal decline class. Unserved ⇒ that class is structurally blank ⇒ the negative pole cannot hold across the C-3 denominator** | **C-7 + C-3 + C-10/C-11** |
| S-06, S-07, S-09 → S-12 | The attester re-derives clauses (a), (d), (b)/(c) respectively | `three-evidence-leg-attestation` |

**Edges deliberately NOT drawn** (drawing them would destroy the parallelism):
S-02 → anything (custodial; it gates *touching #1941*, which no sprint does — that is a
**gate**, not an edge) · S-01 → S-05 (the dark class is a named HOLE in the population, carried
explicitly, not a blocker on building the seam) · S-03 → S-04 (independent probes of different
subsystems) · S-10 → anything but S-11 · S-05 ↔ S-06 (they share an upstream, not each other) ·
**O-2 → S-05** (O-2 blocks CLOSING the population, **not building the seam** — treating it as an
edge would stall WS-DENOM on an operator word it does not need yet).

### The critical path is not length-determined. It is gate-determined.

```
S-04 ─ PT-01 ─ S-06 ─┐
                     ├─ S-09 ─┐
S-04 ─ PT-01 ─ S-05 ─┘        │
                              ├─ PT-05 ─ S-12
S-10 ─ ★PT-04 (R-35) ─ S-11 ──┘
                              │
S-03 ─ S-07 ──────────────────┘
```

Counting sprints, the longest chain is four. **That number is meaningless here.** The binding
constraint is **PT-04**, a gate with:

- **no rule for what lifts it** (RATIFICATION §2: *"nothing rules what lifts it"*),
- **no forcing function** (*"outstanding since 09-06 with no forcing function"*),
- **NO WATCHER** (§9 row 1),

and because **S-11 → S-12 is a hard edge**, that unwatched gate sits in front of **the entire
attestation**. Eleven sprints can complete, every PR can merge, every critic can pass — and
`verified_realized` stays **UNATTESTED** until an operator word with no scheduled occasion is
spoken.

**★ The single most actionable consequence of this decomposition:** the initiative's throughput
is not limited by engineering. **Give R-35 a watcher and a forcing function, or accept that the
bar is unreachable by construction.** That is fork **O-1**, and it should be put to the operator
**in Wave 0**, concurrently with the five dispatches — not discovered at PT-04. S-02 (WS-CARGO)
is the sprint that surfaces it, which is why WS-CARGO is Wave 0 rather than a closing tidy-up.

## 6. Cross-Rite Handoff Protocol & Sync-Sequence Verification

### 6.1 Sync-sequence verification — **CONFIRMED, not UV-P**

The charge asked me to *verify the CLI surface live rather than assume, and label UV-P if
unverified.* **It was verified live. The result is CONFIRMED.**

| # | Probe (own hands, 2026-09-08) | Result |
|---|---|---|
| 1 | `ari rite current` | Active rite **10x-dev**. Borrowed with invocation IDs: **dre** `inv-20260903-e2e4acc003e6` · **eunomia** `inv-20260903-15e7b9dd14fd` · **security** `inv-20260903-d726cb32d049` · **sre** `inv-20260903-172beff897f1` · **clinic** `inv-20260908-e9ebababc88b`. rc=0 |
| 2 | `ls -1 .claude/agents/*.md \| wc -l` | **28** files, and the roster matches the borrow list **EXACTLY**: 5 native + 4 dre + 6 eunomia + 4 security + 4 sre + 4 clinic + myron = 28. Every seat this shape assigns is **physically present** |
| 3 | `ari sync --scope=rite --dry-run` | `[DRY RUN] Sync: success · Rite: success (10x-dev)` across all four channels, **no pending changes**. rc=0 |
| 4 | `ari sync --help` | `--rite string` — a **string flag: SINGULAR, one rite per invocation**. Confirmed as the charge states |
| 5 | `ari rite invoke --help` | *"Additively borrows components from another rite **without switching context**"* |

**CONCLUSION — CONFIRMED (not UV-P): for `dre`, `eunomia`, `security`, `sre` and `clinic`,
`ari sync` is a NO-OP and NO CC RESTART IS NEEDED.** Their agents are already projected into
the channel directory. Sprints S-01..S-12 require **zero rite transitions**.

**★ A NAVIGATIONAL CORRECTION the charge's phrasing would have caused.** The charge says to
surface `ari sync --rite=X` for a genuine crossing. Against the live CLI that command is
**the wrong instrument for a co-seat need**: `ari sync --rite=X` **SWITCHES** the rite scope,
which would move this repo **off `10x-dev`** and unseat the native 10x-dev roster this shape
depends on. The additive instrument is `ari rite invoke`. Both are surfaced below; neither is
executed here.

```bash
# CO-SEAT an additional rite (ADDITIVE — does NOT switch the active rite).
# Operator runs this; Pythia does not execute it.
ari rite invoke <rite-name> agents
# then: ONE CC restart per transition.

# SWITCH the active rite (ONLY if a genuine rite change is intended — this
# would take this repo OFF 10x-dev):
ari sync --rite=<rite-name>        # SINGULAR: one rite per invocation
# then: ONE CC restart per transition.
```

**No sprint in this shape requires either command.** If a later sprint genuinely crosses to an
unseated rite (`arch`, `forge`, `docs`, `rnd`, `hygiene`, `debt-triage`, `intelligence`,
`strategy`, `thermia`, `ui`, `rainbow`, `slop-chop`, `releaser`, `review`), the operator runs
**one** invocation and **one** restart per transition. **Pythia surfaces; the operator executes.**

### 6.2 Handoff artifacts

All handoff artifacts land in the **session repo**,
`/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana`, under `.ledge/` (decisions of record) or
`.sos/wip/` (working artifacts). Both are in the **deploy-inert** path set (§12) — an artifact
handoff cannot roll a service.

| From | To | Artifact | Carries |
|---|---|---|---|
| S-01 clinic | S-08 clinic | `.sos/wip/PROBE-qc-outbound-deck-delivery-2026-09-08.md` | the three-way disposition + the firing control |
| S-03 sre | S-07 sre | `.sos/wip/LOCATE-c17-lifecycle-observer-2026-09-08.md` | observer located/absent; positional-index disposition |
| S-04 10x-dev+security | S-05, S-06 | `.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md` | the enumerated options + deploy class per option |
| S-10 sre | S-11 sre | `.sos/wip/PLAN-c10-supersede-blast-radius-2026-09-08.md` | blast radius + image separability |
| S-02 eunomia | **all** | `.ledge/decisions/REGISTRY-name-the-client-carried-gates-2026-09-08.md` | owner · trigger · watcher, `NO WATCHER` where true |
| all | S-12 dre | the above + code refs | the attester **inherits none of them as proof** — it re-derives every leg |

**RULE-2 carry:** every UV-P still open at a cross-rite handoff travels into it under the
Gate-C DEFER-tag mechanism. §13 is the ledger that travels.

## 7. Emergent Behavior Constraints

### PRESCRIBED — every sprint, no discretion

1. **C-11 — the supersede is a DISPOSITION OF RECORD.** R-35 is **NOT** lifted, narrowed, or
   overwritten by this shape or anything downstream of it. Merging `services/**` to `main`
   **IS an apply** — re-verified own-hands at autom8y `b2b4ae98` (§13 SVR-1/SVR-2).
2. **C-1 image-event law.** One image event per envelope; **bundling = REFUSAL**; folding any
   cure into **#1941 is FORBIDDEN**.
3. **C-3 denominator.** ALL ACTIVE CLIENTS. A single-office green is **a different claim**,
   never a partial pass.
4. **C-7 two-sidedness.** The failure pole is a **required half** of the receipt.
5. **C-12 registry discipline.** Owner · trigger · watcher per row, **`NO WATCHER` written
   where true**. A fabricated watcher is worse than an empty cell.
6. **C-4.** *A reading that cannot name its own SUBJECT is still silence* **EXTENDS** the
   north and does **NOT** amend `name-the-zero`'s realization predicate, which stays
   **PARKED, INTACT and UNAMENDED**.
7. **C-18.** CARD-ARCH-2 is **SURFACED, NEVER TAKEN** — external premise, external owner.
8. **★ Every zero needs a firing positive control and visible stderr, or it is UNTAKEN and
   UNREPORTABLE.** A reporting bar, not a style note.
9. **★ The R-A4 floor, unlifted by anything here:** credential-rotation EXECUTION,
   customer-visible OUTBOUND acts, business-of-record identity mints. *"No grant phrasing,
   however explicit, lifts it."* This is why S-08 may recommend but may not send.
10. **`DONE IS A BAR, NOT A DATE.`** No sprint may substitute a date, a merge, a served image,
    or a projection for the bar.
11. **Critic-substitution / rite-disjointness (R1).** Every sprint's external critic is
    **rite-disjoint from its author** (§2, per-sprint `external_critic`).
    **Self-assessment caps MODERATE** — `self-ref-evidence-grade-rule`.
12. **Option-enumeration-discipline at every genuine fork.** Enumerate exhaustively, *then*
    recommend. S-04 is the load-bearing instance.

### EMERGENT — agent discretion inside the sprint

- **HOW** the join resolves, **HOW** the seam makes mis-wirings unrepresentable, **HOW** the
  smoke binds, **WHAT SHAPE** the reader takes. The shape fixes the *refusals* and the *bar*;
  the mechanism is the seat's.
- Which probes, which instruments, which fixtures — subject only to the positive-control fence.
- Whether a sprint's work needs one PR or two, **provided** each PR is atomic and single-repo.
- Re-seating within R1 where a better-fitting co-seated agent exists (this shape already
  exercised that: WS-SMOKE moved dre → sre to keep the attest rite pristine).

### OUT OF SCOPE — must not touch (frame §10, carried by name)

| # | Out | Where it belongs |
|---|---|---|
| 1 | **G-A1** | deferred by R-39 on the cofounder's answer; blocks #1941's landing, does not enter this envelope |
| 2 | **Blocker C(a)** — the actor behind `salkin-safe-routing` | not asked, not ruled |
| 3 | **Blocker C(c)** — train-or-pin | not asked, not ruled |
| 4 | **H2 / the ADIO identity** | refused three independent ways by the fast-lane predicate; fails the **R-A4 floor absolutely** (`production.tfvars:154`) |
| 5 | **The main-branch `alarm_description` red** (1001 vs a 1000 cap) | the SEV-1-delivery-claim lane. Pre-existing, proven four ways. **Curing it here would be bundling** |
| 6 | **The PII-coupled 1,252 office-blind residual** | warden + security call. **Adjacent to WS-JOIN is not inside it** — S-04 must not annex it |
| 7 | **The extraction's preload grade** (BLOCKING vs LAZY) | the promotion packet's own disposition |
| 8 | **The traffic halving** (~381/24h baseline vs 97-255 live) | observed, uninvestigated, not ruled |
| 9 | **The 15,084-event 2026-08-23→08-27 outage** | a bounded, closed, 5-day incident **in no record**. It is *evidence for* why WS-CONTAIN and WS-RECEIPT exist; **it is not a workstream** and the sitting named no owner |
| 10 | **Re-litigating any of C-1..C-18** | the operator's next sitting |

## 8. Risk Map

Ordered by **what they cost the bar**, not by likelihood.

| # | Risk | Sprint(s) | P | Impact | Mitigation (and who holds it) |
|---|---|---|---|---|---|
| **R-1** | **★ R-35 never lifts.** No rule, no forcing function, NO WATCHER. Clause (b)'s kinding sits behind it, and S-11 → S-12 is a hard edge — so **the whole attestation is behind an unwatched gate** | S-11, S-12 | **HIGH** | **FATAL to the bar** | Put **O-1 to the operator in WAVE 0**, not at PT-04. S-02 surfaces it and is Wave-0 for this reason. **NO AGENT CAN MITIGATE THIS** — the honest mitigation is that the initiative names the gate loudly and refuses to pretend the bar is reachable without it |
| **R-2** | **The denominator silently measures our own pipeline.** ASR's `activity` is fetch coverage, not accounts (91/144 `untriangulated`); it **looks plausible** | S-05, S-09 | MED | **Silent false-green — worst class** | PT-03 is a HARD gate demanding **unrepresentability proven by a failing-closed test**, not documentation. `account_status` is a same-lineage echo and is barred as a corroborator |
| **R-3** | **The receipt ships with no READER** — face 4, built-and-unconsumed, shipped by the wave that extracted the law. REPORT §2 shows this is the fleet's **live** condition (five orphan branches) | S-09 | **HIGH** | Instrument exists, bar unreachable | M-4 ruled **in this shape**: the READER is an S-09 deliverable, not a follow-up. Hard gate. **The PT-08 non-firing result does NOT transfer** — it held only because `semantic_alarms.tf:69-70` is generically dimensioned |
| **R-4** | **The negative pole is deferred.** The positive pole is easy and demoable; the failure pole is neither | S-06, S-09, S-12 | **HIGH** | Reproduces the exact defect the parent exists to close, at client altitude | Hard gate in S-06 (failure line must be nameable), S-09 (both poles or no exit), PT-05 and S-12. Four independent places, because this is the most likely failure |
| **R-5** | **Q-C returns a vacuous zero** from an inbound-shaped query. The per-recipient inbound log **does not exist** (PR-2) | S-01 | MED | Six offices wrongly dispositioned; denominator corrupted | Named trap in S-01 + the positive control + PT-02's first question is whether the control fired |
| **R-6** | **WS-JOIN reintroduces `office_phone` onto the log plane** to make naming easy — trading away an integrity control (PR-8 **REFUTED**) that C-15 **explicitly rejected** | S-04, S-06 | MED | Governance breach; PII regression | `compliance-architect` is a **named co-author**, not a reviewer. S-06 has a **two-sided** test: name present AND identifier absent. O-4 exits to the operator if the trade is required |
| **R-7** | **origin/main drifts under a sprint.** It moved **three times** in this arc: `cc88b75e` → `57e21107` → `b2b4ae98` | all | **HIGH** | Citations detach from referents silently | Fence 2 in every dispatch; explicit refs only; re-resolve at sprint start. **This shape caught a live instance** — see §14 |
| **R-8** | **A `services/**` merge fires an apply** while R-35 stands | S-05, S-06, S-07, S-09 | MED | **R-35 breach** | §12 classifies every sprint by deploy class **before** it starts. PT-01 determines whether the join path is even in the blocked class |
| **R-9** | **★ An asana-repo merge rolls production** — a second, distinct deploy path the charge's sequencing facts did not cover | S-05, S-06, S-09 | MED | Unplanned prod deploy | **§12 — this shape's own finding.** The deny-list is only `.ledge/**`, `.sos/**`, `.claude/**`, `.gemini/**`, `.knossos/**`, `.know/**.md`; it is a **DENY**-list, so any unlisted path still triggers |
| **R-10** | **Checkpoint proliferation** — the parent fired 8 and its close ruled the surfacing loop had become the disease it named | all | MED | Coordination theatre; velocity loss | **Five** checkpoints, each with a named act it can change; the five NOT placed are recorded with reasons (§3) |
| **R-11** | **#1941 rots** or is closed to tidy the board, spending a rite-disjoint certificate that cost two re-walks | S-02 | MED | Certificate lost; C-9 breached | **S-02 is WAVE 0** and names a holder before anything touches it. Closing is reserved to O-7 |
| **R-12** | **A correctly-firing gate is misread as a blocker** and routed around | PT-04, S-11 | MED | Governance breach dressed as unblocking | PT-04's `on_fail` states it plainly: **not-starting is the CORRECT outcome**. The parent wave already recorded this exact misreading |
| **R-13** | **Attester contamination** — a dre seat builds and then dre attests | S-07, S-12 | LOW | Attestation void | dre is kept out of **every** build sprint: WS-SMOKE re-seated dre → sre. dre appears only as `change-warden` (review) and `integrity-architect` (attest). PT-05's last question tests it |
| **R-14** | **O-2 stalls WS-DENOM.** `client` = contract state or billing state is unanswered and C-3's denominator turns on it | S-05 | MED | Wave-1 stall | **Deliberately NOT an edge.** O-2 blocks CLOSING the population, not BUILDING the seam. S-05 proceeds and reports the population **with its dependency stated** |
| **R-15** | **The C-13 clock is consumed by this initiative.** Cut `2026-09-09T18:00Z`, ~24 h from framing | pre-flight | LOW | Operator's own act missed | Surfaced in §4.0(iii) as **not this initiative's to hold**. The only self-firing row in the registry |

## 9. Carried Gate Registry (C-12) — owner · trigger · watcher

Carried from frame §6 **as a registry**, not re-derived and not retired (C-12). Each row gains
a **shape column**: which sprint holds it. **`NO WATCHER` is written where true — it is a
finding, not a gap to paper over.** Fabricating a watcher to make the board look green is
explicitly worse than an empty cell.

| gate / deferral | owner | trigger (what ends the wait) | watcher | held by |
|---|---|---|---|---|
| **★ R-35 lift** — the wall in front of WS-CONTAIN | operator (keyed on the cofounder) | **UNRULED.** *"nothing rules what lifts it ... outstanding since 09-06 with no forcing function"* | **NO WATCHER** | **S-02** surfaces (Wave 0); **PT-04** blocks; **O-1** decides |
| **G-A1** — blocks landing #1941 | operator | third-party answer; deferred by R-39, untouched by the 09-08 sitting | **NO WATCHER** | **S-02** (registry row only — G-A1 is OUT OF SCOPE, §7 row 1) |
| **★ G-FL1** — the fast-lane predicate | operator | **NEVER PUT TO THE OPERATOR.** PROPOSAL is **AUTHORED AND UNRATIFIED** (`:268`); the sitting asked about *sequencing*, never *"do you ratify it?"* | **NO WATCHER** — and its disjoint reviewer (`security-reviewer`) is **named in the PROPOSAL but never dispatched** | **S-02** surfaces as **O-3**. ★ Folded as a **GATE, not a workstream** (frame §5) — a registry row plus an operator fork, never a build |
| **G-P3** — answered-and-absent parks | **SPOKEN (C-8)** | discharged at the 09-08 sitting | C-8 **IS** the record — its text existed nowhere in this repo. **Nothing to check it against** | closed; carried as **UV-P-8** |
| **C-13 / R-65** — dead-letter row `bd875254…` | **operator's own hand** | **HARD CLOCK: cut 2026-09-09T18:00Z**, then resolves **LOST automatically**; reap 2026-09-10T05:28:46Z | **the clock itself — the ONLY self-firing row in this table** | **NOBODY IN THIS SHAPE.** §4.0(iii) surfaces it; no sprint holds or consumes it |
| **C-18 / CARD-ARCH-2** | **EXTERNAL** (their code, their wave mid-flight) | **SURFACE IT, DO NOT TAKE IT** | owner named externally; we **carry the dependency knowingly** | **S-02** registry row; §7 prescription 7 |
| **C-10 disposition** (supersede both images) | this initiative, WS-CONTAIN | executes **when R-35 lifts** — inherits R-35's missing forcing function | inherits **NO WATCHER** from R-35 | **S-11**, gated at **PT-04** |
| **G-P6 · G-RS16 · G-P4 · G-M7 · R-41 · G-CIREACH · G-RS4 · G-P2** | carried per C-12 | **none ruled** at the 09-08 sitting | **NO WATCHER** (8 rows) | **S-02** — carried as rows, none actioned |
| **R-72** — *"the plan lane runs read-only; the R-35 freeze forbids applies, not plans"* | unassigned → **assigned by this shape** | narrows R-35; CUSTODY PT-07 finding 3: *"Surfaced, not acted on"* | **NO WATCHER** → **★ NOW WATCHED: S-10** | **S-10.** This shape's one registry improvement: R-72 goes from surfaced-and-inert to **an executing sprint in Wave 0** |
| **R-67 / R-39(i)** — the cofounder snippet, FIRST ACT, six rulings keyed to it | operator | **no ratification through 2026-09-08 records an ANSWER** | **NO WATCHER** | **S-02** registry row |
| **M-4 RED** on `#1941` | **WS-CARGO** | one genuine hit at `test_df40_read_kind_corpus.py:80` + reserved-TLD allowlisting; **will go RED at word-time** if unaddressed | WS-CARGO holder (**to be named**) | **S-02** — naming the holder is the sprint's first act |

**Count: 11 rows · 9 carrying `NO WATCHER` in whole or in part · 1 self-firing clock.**
**That ratio IS the registry's finding and must be read as one.**

**What this shape changed, and what it did not.** It assigned **exactly one** previously
unwatched row a watcher — **R-72 → S-10** — because R-72 is the only row whose trigger was
already satisfied and merely unexercised (*plans are permitted; nobody ran one*). **Every other
`NO WATCHER` remains `NO WATCHER`**, because inventing watchers for operator-keyed gates is the
fabrication C-12 forbids. **8 of the 11 rows are still unwatched after this shape, and R-35 —
the row that gates the entire attestation — is one of them.**

## 10. Defer Registry

Distinct from §9. §9 carries **inherited** gates; this section registers what **this shape
itself defers**, so the deferrals are watched rather than absorbed.

| # | Deferred by this shape | Why deferred (not decided here) | Who decides | Watcher | Lapses to |
|---|---|---|---|---|---|
| **D-1** | **The repo in which S-05's seam lands** | Depends on PT-01's identity ruling; deciding it now would pre-empt the fork and pick a deploy class blind | PT-01 + S-05 architect | **PT-01** | n/a — PT-01 always fires before S-05 |
| **D-2** | **Whether S-09's reader is a separate PR** | Sprint-internal, and sprint internals are non-prescriptive by schema | S-09 seats | S-09's critic (`observability-engineer`) | one PR |
| **D-3** | **Whether the H/S tier split is repaired, replaced, or retired** (frame **M-5**) | Two structural false-S generators and 3 of 10 TIER-S offices not silent; §7.5's alarm has this as a **blocking precondition**. **No sprint in this shape owns it** | operator or a successor initiative | **★ NO WATCHER** | **NOT ASSIGNED — written as NO WATCHER because it is true** |
| **D-4** | **The C-3 population's closure** (O-2: contract vs billing state) | Not agent-decidable; blocks CLOSING, not BUILDING | operator (**O-2**) | S-05 reports it with every population figure | population stays **OPEN**, stated as open |
| **D-5** | **Whether `verified_realized` can be ATTESTED-WITH-FLAG** if 3 of 4 clauses hold | S-12's call under `three-evidence-leg-attestation`; pre-deciding would let a partial pass in through the shape | S-12 (`integrity-architect`) | PT-05 | **UNATTESTED** — the conservative default |
| **D-6** | **Q-C's entitlement** (Email Activity History add-on) | If unentitled, acquiring it is an operator/billing act | operator | **PT-02** | **INSTRUMENT UNAVAILABLE**, and the §4 assumption-1 unknown **stays open and re-flagged** |
| **D-7** | **The initiative's NAME** (frame **O-5**) | RATIFICATION §2 records it as not given. The frame proposed `name-the-client`; this shape uses that slug **on the frame's proposal, not on an operator word** | operator (**O-5**) | **★ NO WATCHER** | slug stays in use **without a word behind it** — recorded, not hidden |
| **D-8** | **Whether the gate architecture should be kept and tuned or dismantled** | Frame UV-P-7: *"smuggled into three questions; C-12 implies yes but it was never tested head-on."* This shape **inherits the registry per C-12 and therefore inherits the untested assumption** | operator | **★ NO WATCHER** | assumption stays untested |

**★ Honest count: 3 of this shape's 8 own deferrals carry `NO WATCHER`** (D-3, D-7, D-8).
Written because they are true. A shape that extracted the observer law and then shipped its own
unwatched deferrals silently would be the law's counterexample — the same reasoning that made
WS-CARGO a workstream rather than a footnote.

## 11. Inherited Cargo — PR #1941 and its Holder

**C-9, verbatim: *"Needs a named holder or it rots."*** This section is the holder assignment.

### Live state — re-verified own-hands 2026-09-08 (`gh pr view`, rc=0)

| PR | state | head | base | mergeable | note |
|---|---|---|---|---|---|
| **#1941** | **OPEN**, not draft | `b9bbfadcbdbc89d23a5f723a9c140acecb0d0728` | `integration/name-the-zero` | **MERGEABLE** | *S-09 assembly — name-the-zero: one train, one re-derivation.* **33 files.** Updated **2026-09-05T14:51:37Z** — **head still FROZEN**, matches CUSTODY PT-07 `:15` exactly. **Base-bound: its base is an integration branch, NOT `main`** |
| **#2071** | **OPEN**, not draft | `6265e378b5ba3bb007ec6966429afc965aec984d` | `main` | **UNKNOWN** | *fix(email-booking-intake): mark 3 terminal decline sites in match_lead (S-14 class audit)* **`[DO NOT MERGE]`** in-band. **2 files, both `services/email-booking-intake/**` ⇒ DEPLOY-CLASS A** |
| **#2073** | **OPEN**, not draft | `8c9aa11f3eba2ec100d4c73be67a4a580d87b15e` | `main` | **UNKNOWN** | *feat(ebi): name the clinic on booking success lines.* **6 files, all `services/email-booking-intake/**` ⇒ DEPLOY-CLASS A** |

**UV-P-10 is NOT upgraded.** `#2071` and `#2073` still read `mergeable: UNKNOWN` at re-probe.
That is **reported as unknown** — not as MERGEABLE, not as CONFLICTED. The frame reported it as
unknown and this shape does the same.

### The holder

| Object | **HOLDER** | Authority | What the holder may NOT do |
|---|---|---|---|
| **PR #1941 @ `b9bbfadc`** | **S-02 — `verification-auditor` (eunomia)**, as the sprint's **named custodian of record** | C-9 (carried as inherited cargo); C-12 (registry) | **May NOT close it.** Closing spends a rite-disjoint certificate that cost **two re-walks**. **May NOT land it** — landing needs **G-A1**, which is deferred on a third party and **OUT OF SCOPE** (§7 row 1). **May NOT fold any cure into it — FORBIDDEN (C-1)** |
| **The M-4 RED on #1941** | **S-02** | frame §6 final row | May not mark it resolved without addressing the genuine hit at `test_df40_read_kind_corpus.py:80` and the reserved-TLD allowlisting. **It will bite at word-time** |
| **The disposition LAND / HOLD / CLOSE** | **★ OPERATOR — fork O-7** | C-9 *"explicitly reserves this"* | **No agent decides this.** S-02 surfaces it with the evidence; the operator words it |

**The holder's standing duty, and it is the whole point of the assignment:** re-verify the head
at each Wave boundary and report **FROZEN or MOVED**. `b9bbfadc` has been frozen since
2026-09-05T14:51:37Z. **Inheritance is never assumed** — an unverified inheritance is how cargo
rots while looking held.

**Why the holder is a Wave-0 sprint and not a closing tidy-up.** C-9's failure mode is not
misconduct; it is **time**. A holder named at the end of the initiative holds nothing, because
the rotting happens during the initiative. This is **face 7 of the observer law** — *a decision
with no watcher* — and the envelope that extracted that law would be its own counterexample if
it deferred custody to the close.

## 12. Deploy-Shape Classification

**Why this section exists.** The charge supplied one deploy-shape fact: *merging `services/**`
to main IS an apply.* **That fact is true and re-verified (§13 SVR-1/SVR-2) — and it is not the
only deploy path this initiative can trip.** Verifying the second one was necessary to assign
PR boundaries honestly, and it materially changes which sprints are safe to run now.

### CLASS-A — `autom8y` `services/**` → **terraform apply** · **R-35-BLOCKED**

```
.github/workflows/service-deploy-dispatch.yml   on: push: branches:[main] paths:['services/**']   (:26-31)
   -> .github/workflows/service-deploy-lambda.yml:4    workflow_call:
   -> .github/workflows/service-deploy-lambda.yml:304  run: terraform apply -input=false -auto-approve tfplan
```
Re-verified own-hands at autom8y `b2b4ae98` with a firing negative control. **R-35 forbids the
APPLY. R-72 permits the PLAN** — which is S-10's entire licence.
**Sprints:** S-07, S-11, and S-06/S-09 if PT-01 chooses emit-time.

### CLASS-B — `autom8y-asana` code → **satellite dispatch → ECS service roll** · ★ **NEW FINDING**

```
.github/workflows/test.yml            on: push: branches:[main]   (with a paths-ignore DENY-list)
   -> .github/workflows/satellite-dispatch.yml:6   workflow_run: workflows:["Test"] branches:[main] types:[completed]
   -> :58  event-type: satellite-deploy   -> repository_dispatch to autom8y/autom8y  -> rolls the asana ECS service
```

**The asana repo has its own deploy trigger, distinct from CLASS-A.** `test.yml`'s own comment
records the incident verbatim: *"a docs-only push to main redeploys production: `b371deed`
(22:06:38Z, four `.ledge/**` markdown files, zero code) drove the 22:18:32-22:34:23Z blue/green
swap and the resulting `Asana Availability Fast Burn` + `High Error Rate` page."* Commit
`6c3ed718` (#411, in this repo's recent history) added the deny-list in response.

**★ It is a DENY-list, not an allowlist — its own comment says so: *"an unlisted or newly-added
path still triggers."*** So CLASS-B is the **default** for asana, and only the listed paths escape.

**I make NO claim that R-35 covers CLASS-B.** R-35 is the EBI freeze; extending it to the asana
ECS roll would be inventing scope, and narrowing it would be worse. **CLASS-B needs its own
operator gate, and this shape surfaces that rather than deciding it.**

### CLASS-C — **DEPLOY-INERT** · the exact asana `paths-ignore` set, verified verbatim

```
.ledge/**   .sos/**   .claude/**   .gemini/**   .knossos/**   .know/**.md
```
**Nothing else.** Note deliberately absent, though "docs" by name: `docs/**`
(`docs/api-reference/openapi.json` is a Test input), `**.md` outside those trees
(`README.md` is `COPY`'d by the Dockerfile), and `.know/**` non-`.md`
(`.know/cache-freshness-ttl-manifest.yaml` is loaded at runtime).

### Per-sprint classification

| Sprint | Class | Blocked by R-35? | May run in Wave 0? |
|---|---|---|---|
| **S-01** Q-C probe | **C-INERT** | no | **YES** |
| **S-02** CARGO | **C-INERT** | no | **YES** |
| **S-03** SMOKE-LOCATE | **C-INERT** | no | **YES** |
| **S-04** JOIN-DESIGN | **C-INERT** (ADR only) | no | **YES** |
| **S-10** CONTAIN-PLAN | **READ-ONLY** (no merge, no PR) | **no — R-72 permits plans** | **YES** |
| **S-05** DENOM-SEAM | **B-ECS** or **A-APPLY** — decided at PT-01 | fork-dependent | no |
| **S-06** JOIN-BUILD | **A-APPLY** (emit-time) or **B/C** (read-time) | **fork-dependent — this is what PT-01 buys** | no |
| **S-07** SMOKE-BUILD | **A-APPLY** | **yes** (build+plan permitted; apply not) | no |
| **S-08** DARK-DISPOSITION | **C-INERT** | no | no (needs S-01) |
| **S-09** RECEIPT | **A-APPLY** (+ reader per PT-01) | **yes** | no |
| **S-11** CONTAIN-DISP | **A-APPLY** | **★ YES — the wall** | no |
| **S-12** ATTEST | **C-INERT** | no (but needs S-11's effect) | no |

**★ The operative consequence: five of twelve sprints are CLASS-C or READ-ONLY and are
therefore completely unblocked by R-35 today.** That is precisely the Wave-0 set. The
decomposition's value is that it finds this parallelism instead of queueing the whole
initiative behind an unwatched gate.

## 13. SVR Receipts & UV-P Ledger

Grades per `evidence-grade-vocabulary`; **self-cap MODERATE** per `self-ref-evidence-grade-rule`.
Every claim below was **re-taken by this seat** — none is inherited from the frame.

### SVR receipts (own hands, 2026-09-08)

| # | Claim | Probe | Result | Grade |
|---|---|---|---|---|
| **SVR-1** | `services/**` push to autom8y `main` triggers the deploy dispatch | `git show b2b4ae98:.github/workflows/service-deploy-dispatch.yml`, `on:` block | `:26-31` — `on: push: branches: [main] paths: ['services/**']`. rc=0 | **[STRONG]** |
| **SVR-2** | that chain ends in a `terraform apply` | same file → `service-deploy-lambda.yml` | `:4` `workflow_call:` · **`:304` `run: terraform apply -input=false -auto-approve tfplan`** · 542 lines · positive control: 3 `terraform apply` hits · **negative control rc=1** | **[STRONG]** — two-sided |
| **SVR-3** | `office_phone` is DROPPED, and that drop IS the PII control | `git show b2b4ae98:scripts/ebi_witness_ledger.py` | 942 lines · **positive control 58** prefix-keyed hits (fires) · `office_phone` = **2 hits, BOTH IN COMMENTS**: `:21` *"office_phone in the payload are DROPPED (not hashed, not truncated —"*, `:394` *"office_phone are DROPPED (not hashed). The raw payload string is"* · **negative control rc=1** | **[STRONG]** — two-sided |
| **SVR-4** | asana merges to main can roll production (CLASS-B) | `test.yml` `on:` + `satellite-dispatch.yml` | `test.yml` push:[main] with a 6-entry `paths-ignore` DENY-list → `satellite-dispatch.yml:6` `workflow_run:["Test"]` → `:58` `event-type: satellite-deploy` → repository_dispatch to autom8y/autom8y. **negative control rc=1** | **[STRONG]** — two-sided |
| **SVR-5** | co-seat state | `ari rite current` · `ls .claude/agents/` · `ari sync --scope=rite --dry-run` | 10x-dev active; dre/eunomia/security/sre/**clinic** borrowed with inv-IDs; **28/28 agent files, exact roster match**; dry-run success, no changes. **negative control: `zzz-nonexistent-seat` ABSENT** | **[STRONG]** — two-sided |
| **SVR-6** | PR live state | `gh pr view` ×3 | #1941 OPEN/MERGEABLE/`b9bbfadc`/`integration/name-the-zero`/33 files · #2071 OPEN/`6265e378`/main/UNKNOWN/2 files · #2073 OPEN/`8c9aa11f`/main/UNKNOWN/6 files. rc=0 | **[STRONG]** for state; **the `UNKNOWN` is reported as unknown** |
| **SVR-7** | grounding line counts | `wc -l` | TRIAGE **186** · CUSTODY **66** · RATIFICATION **56** · frame **826** — **all four match the charge's corrected figures exactly** | **[STRONG]** |
| **SVR-8** | `ari sync --rite` is singular | `ari sync --help` | `--rite string` — one value per invocation. `ari rite invoke` is the additive co-seat instrument | **[STRONG]** |

### ★ Drift and citation corrections caught by this seat

| # | What the charge/frame said | What is true at re-take | Disposition |
|---|---|---|---|
| **DR-1** | autom8y `origin/main` = `57e21107` (charge: *"MOVED AGAIN `cc88b75e` → `57e21107`"*) | **`b2b4ae9835d757e84bf80b6c5fb514b743b2da58`** — a **THIRD** move during shaping | Shape pinned to `b2b4ae98`; every dispatch carries "re-resolve at your start" |
| **DR-2** | asana frame `source_hash: d75bfe1a` | asana `origin/main` = **`389c59bc`** (+1 commit, #413 `ci(sweep)`); `d75bfe1a` **IS** an ancestor (rc=0) | Recorded in frontmatter; immaterial to cited content |
| **DR-3** | **★** `ebi_witness_ledger.py:463` splits offices H/S (frame telos block + `receipt_grammar`, inherited from the ratification) | **WRONG ANCHOR.** `:463` is a `"""` docstring terminator. The predicate is at **`:495`** (`def _tier_observed(...)`) and **`:498`** (`return "H" if (posted_count > 0 or distinct_dispositions > 0) else "S"`) | **NOT head-drift** — the file is **byte-identical** at `57e21107` and `b2b4ae98` (942 lines, `diff` clean), so the anchor was wrong at both refs the frame claims to have read. **Inherited mis-citation. Use `:495`/`:498`.** S-05 and S-12 must cite the corrected anchor |
| **DR-4** | charge lists **dre · eunomia · security · sre** as co-seated | **clinic is ALSO co-seated** (`inv-20260908-e9ebababc88b`, 4 agents present) | Used: S-01 and S-08 are seated on clinic. Not invented — verified |

### UV-P ledger — carried from frame §11, plus this shape's own

Frame **UV-P-1 … UV-P-10** are **carried forward UNCHANGED**; none was discharged by shaping,
and shaping is not the act that discharges them. Their sprint owners:

| frame UV-P | subject | discharged by |
|---|---|---|
| UV-P-1 | the upstream human origin-signal | **none** — origin-of-record is the ratification (Gate A.1(a) satisfied); carried |
| UV-P-2 | C-17's *"observer matches a literal section name"* | **S-03** |
| UV-P-3 | that `account-status-recon`'s vocabulary is C-17's referent | **S-03** |
| UV-P-4 | S-14's projected 41.6% → 21.2% | **S-11** (post-apply measurement) or it stays a projection |
| UV-P-5 | that the six dark offices are real | **S-01** (Q-C) |
| UV-P-6 | *"client"* = contract vs billing state | **operator O-2** — no sprint discharges it |
| UV-P-7 | that the gate architecture should be kept and tuned | **operator** — carried as **D-8**, `NO WATCHER` |
| UV-P-8 | G-P3's correctness as recorded by C-8 | **unfalsifiable by construction** — carried as such |
| UV-P-9 | live runtime state of the served EBI images | **S-10** (plan lane will read it) |
| UV-P-10 | `mergeable` of #2071 / #2073 | **re-probed by this seat: STILL `UNKNOWN`. NOT upgraded.** |

**This shape's own UV-Ps:**

`[UV-P: that R-35's scope does NOT extend to the CLASS-B asana ECS deploy path (§12) | METHOD: operator ruling on whether the EBI freeze covers the asana satellite roll | REASON: R-35 is the EBI freeze; the CLASS-B path is a different mechanism (test.yml -> satellite-dispatch -> repository_dispatch -> ECS roll) verified own-hands at SVR-4. Extending R-35 to cover it would be inventing scope; asserting it is uncovered would be narrowing R-35. NEITHER is done here. Surfaced for a ruling; S-05/S-06/S-09 inherit the ambiguity if they land asana code.]`

`[UV-P: that S-11 -> S-12 is a strictly HARD edge | METHOD: architect ruling at PT-05 on whether WS-RECEIPT can supply failure-kinding independently of #2071 | REASON: clause (b) requires a failure to name its kind, never blank; #2071 supplies the kind for the terminal decline class. If S-09 built its own kinding the edge would soften — but that likely duplicates #2071 and risks the C-1 bundling refusal. Drawn HARD here, which places the whole attestation behind R-35. If an architect softens it, the critical path changes materially and this shape must be amended, not reinterpreted.]`

`[UV-P: that Q-C is entitled | METHOD: attempt the call in S-01 | REASON: the SendGrid Email Activity History add-on may be unentitled, returning 403. Carried as D-6; the honest output would then be INSTRUMENT UNAVAILABLE, never a zero.]`

## 14. Seat Gaps & Reconciliation Notes

### 14.1 ★ Seat gaps — flagged, never invented

The charge said: *map roles to agents that EXIST … flag gaps, never invent a seat.* Verified
own-hands against `.claude/agents/` with a negative control.

| Referenced seat | Present? | Consequence |
|---|---|---|
| `pythia` | **ABSENT** | **★ There is no `Task(pythia)` in this repo.** Pythia is a fleet agent reached by the **`/consult` dromenon** (present at `.claude/commands/consult.md`). Every "engage Pythia-navigation at genuine forks" instruction in §4 therefore reads **`/consult`**, a main-thread/operator act. Dispatching `Task(pythia)` would fail |
| `moirai` | **ABSENT** | **★ The frame's own Next-Command step 1 says `Task(moirai) or main thread` for the telos transplant. The `moirai` half is not executable here.** §4.0(ii) gives the two working paths: main thread performs it, or `ari agent summon moirai` + CC restart first |
| `dionysus`, `theoros`, `naxos`, `charon` | **ABSENT** | Summonable heroes, not currently summoned. Only `myron` is. No sprint depends on them |
| every seat this shape assigns | **PRESENT** | 28/28 roster match; each of `diagnostician`, `pathologist`, `attending`, `observability-engineer`, `platform-engineer`, `incident-commander`, `architect`, `principal-engineer`, `qa-adversary`, `compliance-architect`, `security-reviewer`, `change-warden`, `integrity-architect`, `verification-auditor`, `entropy-assessor`, `pipeline-cartographer` verified individually |

**★ Capability gap inside a present seat.** `entropy-assessor` frontmatter is
`tools: Read, Write, Glob, Grep` — **no Bash**. It cannot run `gh`, `git`, or any live probe.
S-02 therefore pairs it with `verification-auditor` (`tools: Bash, Glob, Grep, Read, Write`),
which holds every live verification. Assigning the live re-verification of #1941 to
`entropy-assessor` would have produced an **unverifiable registry that looked complete** —
precisely the failure class this initiative is named for.

### 14.2 Reconciliation against the ratification (C-1..C-18)

| Ruling | Where it lands in this shape |
|---|---|
| **C-1** the client class is the organizing job; image-event law | §7 prescription 2; the whole decomposition |
| **C-2** words first, then subtract | O-1/O-3/O-4/O-6 surfaced in **Wave 0** (via S-02 and PT-01/PT-02), before any drain |
| **C-3** ALL active clients | clause (c); S-05, S-08; hard gate in S-09 and S-12 |
| **C-4** subject-silence EXTENDS the north, does not amend the parked predicate | §7 prescription 6 — stated as non-amending |
| **C-5** denominator routed to the substrate lane | **EXECUTED at the sitting**; its refutations are S-05's three refusals |
| **C-6** park name-the-zero, open this one | this shape is the successor's decomposition |
| **C-7** two-sided receipt | the verbatim predicate in **all twelve** sprints; **S-09**; PT-05 |
| **C-8** answered-and-absent parks; G-P3 spoken | §9 row 4; carried as UV-P-8 |
| **C-9** #1941 inherited cargo, needs a named holder | **§11 — holder named; S-02 is Wave 0** |
| **C-10** supersede both images | **S-11** |
| **C-11** disposition of record; executes when R-35 lifts; merging `services/**` IS an apply | §7 prescription 1; **PT-04**; SVR-1/SVR-2 |
| **C-12** inherit gates AS A REGISTRY, `NO WATCHER` where true | **§9**, 11 rows, 9 unwatched |
| **C-13** dead-letter row, HARD CLOCK 2026-09-09T18:00Z | **§4.0(iii)** — surfaced, **held by nobody in this shape** |
| **C-14** frame now, denominator open inside it | honored — O-2 is a named open question, not a blocker (D-4, R-14) |
| **C-15** the GUID ↔ `office_phone` join is ours | **S-04 + S-06**, sharpened by DR-3-adjacent §4.1 finding |
| **C-16** Asana for now, seam MUST be extensible | **S-05** + the three refusals + PT-03 |
| **C-17** smoke on the lifecycle transition, own the hook | **S-03 + S-07**; clause (d) |
| **C-18** CARD-ARCH-2 surfaced, never taken | §7 prescription 7; §9 row 6 |

### 14.3 Reconciliation against §4 — the six unconfirmed assumptions

| # | Assumption | Sprint that touches it | Can it be discharged here? |
|---|---|---|---|
| **1** | the six dark offices are real | **S-01 (Q-C)** — sequenced **FIRST** per the charge | **YES** — unless 403 (D-6) |
| **2** | S-14's cure does what it projects | **S-11** post-apply | **Only if R-35 lifts.** Else stays a projection |
| **3** | *"client"* = contract or billing state | **operator O-2** | **NO** — not agent-decidable. S-05 proceeds and reports the dependency |
| **4** | the gate architecture should be kept and tuned | **nobody** | **NO** — carried as **D-8**, `NO WATCHER` |
| **5** | the GUID ↔ `office_phone` join does not exist | **S-04 → S-06** | **YES** — S-06 builds the resolution |
| **6** | G-P3 had no prior text | **nobody** | **NO** — unfalsifiable by construction (UV-P-8) |

**★ Two of six (4 and 6) have no owner in this shape, and one (3) is operator-only.** Written
because it is true. A decomposition that silently assigned owners to unownable assumptions
would be manufacturing watchers, which C-12 forbids.

### 14.4 Folding decisions inherited from the frame — honored, not re-litigated

- **G-FL1 is a GATE, not a workstream.** Honored: §9 registry row + operator fork **O-3**.
  No sprint builds it.
- **The `match_lead` cure is NOT a workstream** — it is **PR #2071**, and its landing is
  **WS-CONTAIN's subject**. Honored: #2071 appears only inside S-10/S-11.
- **WS-CARGO was added by the framing seat** because C-9 + C-12 = **face 7, an unwatched
  decision**. Honored and **strengthened**: WS-CARGO is **S-02, in Wave 0**, because a holder
  named at the close holds nothing.

### 14.5 What this shape decided that the frame explicitly left to Pythia

| Frame fork | This shape's ruling |
|---|---|
| **M-1** shape of the C-16 boundary | Deferred to S-05's architect **by design** — but the **bar** is fixed: unrepresentable-by-construction, proven by a failing-closed test, gated at PT-03 |
| **M-2** where naming resolution happens | **NOT decided — escalated to PT-01 as the highest-leverage fork on the board**, because it determines the deploy class of the whole join path. Option-enumeration is mandatory (four options minimum) |
| **M-3** what hook C-17 hangs on | Sequenced behind **S-03**; the positional-index inheritance is barred by hard gate |
| **M-4** whether WS-RECEIPT needs a READER | **★ RULED: YES.** The reader is an **S-09 deliverable**, not a follow-up. REPORT §2 is decisive: *"the missing primitive is not a consumer; it is a READER"* |
| **M-5** repair / replace / retire the H/S split | **NOT ASSIGNED.** Carried as **D-3** with **`NO WATCHER` written**, because no sprint here owns it and inventing an owner would be fabrication |
| **M-6** rite assignment and the attester seat | **RULED** across §2. **Re-seat exercised within R1:** WS-SMOKE moved **dre → sre** so that dre appears only as `change-warden` (review) and `integrity-architect` (attest), keeping critic-never-author clean at **rite** level, not merely seat level |

### 14.6 Sections deliberately omitted from the schema

- **§8 Context Loading Order** — omitted. The compact `sprint.context` form is used instead;
  the schema says use one or the other, not both.
- **§10 Estimated Duration** — **omitted on principle.** The predicate says **`DONE IS A BAR,
  NOT A DATE`**, and `verification_deadline: null` is lawful only under the R-17 bar-not-date
  carve-out. A duration table would reintroduce the date the operator ruled out. Its absence is
  a decision, recorded here so it is not read as an oversight.

---

*Shape authored by pythia, 2026-09-08, at asana `d75bfe1a` (origin/main `389c59bc`) / autom8y
`origin/main b2b4ae98`. Decomposition and sequencing only — it re-litigates no ruling of
C-1..C-18. Authored via `progressive-write-heredoc` (Option 3, existing Bash grant; no
`Write`/`Edit`, no tool-frontmatter widening) with a filler self-tested two-sided before use.
Self-assessment capped **MODERATE** per `self-ref-evidence-grade-rule`. Three zeros in this
shape fired their own fence on the author: a BSD-`sed` filler whose negative control produced a
FALSE PASS (discarded and recorded), an `origin/main` probe run against the wrong repo (caught
and corrected — `57e21107` is an autom8y ref, not an asana one), and the `:463` H/S anchor,
which proved to be an inherited mis-citation rather than head-drift.*
