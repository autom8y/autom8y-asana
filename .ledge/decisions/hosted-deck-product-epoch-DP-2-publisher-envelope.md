---
type: decision
status: ratified                  # PARTIAL — RATIFIED by the OPERATOR 2026-09-05 (word typed in hosted-deck-wave-3, wave 4 Phase 0): P-10 + P-13 as composable, account-independent; T7 reading (i); account (UV-P-5) HELD; Q3 + mechanism UNRULED; was: proposed
ratification: { by: "OPERATOR (typed word, 2026-09-05T20:56:34Z, session hosted-deck-wave-3)", scope: "PARTIAL — modifiers P-10 + P-13; Q1 account HELD; Q2 T7 reading (i); Q3 + mechanism UNRULED", transcribed_sha256: "4a1b5d69da5b12b937503b1ccf388824846380017c41e80e21b8dbbc68cae564", scribe: "dispatcher (wave 4 Phase 0)", session: "session-20260905-014608-787b7977" }
initiative: hosted-deck-product-epoch
session_id: session-20260905-014608-787b7977
door: DP-2
owner: OPERATOR
ships_after: PT-03
evidence_grade: moderate
legs_completed: [architect, requirements-analyst, principal-engineer, architect-addendum, architect-addendum-2, requirements-analyst-RC1, architect-remediation-1, architect-staging-1, requirements-analyst-D2R3]
changelog:
  - "2026-09-05 requirements-analyst-D2R3 (PRE-SHIP confirmation owed per DELTA-2 §D.7 item 3): §12.10 appended — P-14's PROVISIONAL C1-C8 face CONFIRMED with two corrections (C6 open question closed; C7 row narrowed) and its FINAL mark issued NON-VIABLE on C3; the ninth clause is RULED OWED and C9 RESPONSE-SHAPING-ONLY is written in C1-C8 form with fixture F-9 and the INV-08 AND NOT INV-09 discriminator; §12.8 w1 CONFIRMED NARROWED-NOT-REVERSED with the pre-surface test named; Posture A CONFIRMED VIABLE-WITH-CONDITIONS and Posture B CONFIRMED VIABLE-WITH-CONDITIONS; the --config sub-form (CH-02) MOVES NO MARK; the wipe-then-stage forward claim BOUND. Two anchor drifts in §4 P-14 corrected (INV-08 is run.js:274 not :248; served-arm list is :235 not :221). No other section edited; §13 byte-identical (sha re-asserted); F-PUBLISH unanswered; T7 unruled."
  - "2026-09-05 architect-staging-1 (DELTA-2 PASS-WITH-CONDITIONS; PRE-STAGING conditions + two cheap PRE-SHIP items): D2-R1 §5.2 T7 table gains a P-14 row + ordering note; D2-R2 §0 retires the now-false 'predates RC-1' sentence and the P-9 NON-VIABLE bullet gains its second (C8/G-18) ground; D2-R6 §9.1 registers the two new UV-P labels (P-14 runtime behaviour; --config composition) so Gate C carries them; D2-R7 cell counts reconciled (§3.2 P-14 row; §11 13→14; §0 line/leg count). D2-R3/R4/R5 are RA/PE/security PRE-SHIP confirmations and are LISTED, NOT PERFORMED (§0). §12/§13 byte-identical. HASH SLICING CONVENTION (per DELTA-2 D.2 advisory): each slice runs from the newline immediately preceding its ## heading to the start of the next ## heading (§13 runs to EOF); §12 = a2ac8373, §13 = 0249d746. No mark ruled; F-PUBLISH unanswered; T7 unpicked."
  - "2026-09-05 architect-remediation-1 (arch-adversary iter-1 BLOCK): CH-01 P-14 serve-time routing predicate enumerated at equal depth (§4) with PROVISIONAL §12/§13-style marks; CH-02 wrangler --config sub-form named (§0 c4, §4 P-6); CH-03 §0 option cells refreshed (+C8 x6, P-7 per §12.9, P-2/P-3 unconditioned-NON-VIABLE, P-9 second ground, P-14 row); CH-04 sixth Q3 term revocability/CC-1 (§0 Q3, §5.3); CH-05 TL-A predictions PR-1..PR-4 (§0; adversary-drafted, attributed); CH-06 two postures graded (§4.1); §3 mechanism-time axis named. §12/§13 byte-identical; no mark ruled; F-PUBLISH unanswered; T7 unpicked."
  - "2026-09-05 requirements-analyst-RC1 (BLOCKING remediation of SECURITY-REVIEW-S5 REQUEST-CHANGES): RC-1(a) §5.3 audience row corrected — the claim that no audience classifier exists on the a8t side was FALSE; RC-1(b) §12.1 gains clause C8 AUDIENCE-EGRESS quantified over dirs(R_P) + fixture F-8; RC-1(c) §12.4 G-18 column corrected to YES for P-1/P-2/P-5/P-6/P-8/P-12 (P-0 PRE-EXISTING-UNGATED, P-9 YES) with C8 added to each conditioning clause, the parenthetical (no option does) struck, and a SEVENTH front-page input constraint added; §12.9 records the review rulings on the three §13 hand-offs. NO viability MARK displaced. §6 and §13 byte-identical (sha re-asserted)."
  - "2026-09-05 architect-addendum-2 (evidence floor R6): §4 P-7 case-for corrected IN PLACE — the 'three of four dimensions are already done' claim now states the wrangler-surface asymmetry (§13.5, S5-E-3). Nothing else in §4 changed; §12/§13 byte-identical."
---

# DP-2 — F-PUBLISH: the per-profile publisher envelope

## §0 — OPERATOR PACKET (read this page; everything below is appendix)

> **R4 compliance** — `…shape.md:1375` requires each door packet be kept *"COMPACT with the
> dissent attached"*. This file is ~3,200 lines across seven legs. **This page is the door; §1
> down is appendix.** No new options, no answers, no ruling appear on this page.

### The door

| | |
|---|---|
| **Door** | **DP-2 — F-PUBLISH**, `type: one-way-door` (`…shape.md:779`) |
| **Owner / gate / status** | **OPERATOR** (`:781`), gate `hard`, `status: proposed`. **SHIPS ONLY AFTER PT-03** — Potnia stages; PT-03 gates. `on_fail` verbatim: *"S8 is BLOCKED. Do not build a per-profile publisher against an unknown account topology."* (`:793`) |
| **Ratifying DOES commit** | the mechanism + modifiers named in the ruling; the scope of S7/S8 (via Q2); which contract terms are COMMON (via Q3) |
| **Ratifying does NOT commit** | **any build.** LEG-3 is **REFUSED** at S1 — no build branch opens on this lineage until the operator rules on the two ancestor VERDICTs (`…eunomia-handoff.md:106`) |

### The three questions

**Q1 — UV-P-5. FIRST; every option depends on it. WHICH Cloudflare account owns Pages project
`deck-host` and `decks.cntently.com`?** Candidate `a245df42893c85a8d96c71cfa46eec76` appears
as a comment-annotated literal in a sibling `publish.sh` (S5-P-5) — **a file-read CLAIM,
unverified**, uncheckable from this machine (the credential here lists only `tenuta-decks`,
G-35 / S5-P-2); the DNS zone was not probed at all. **METHOD:** `wrangler whoami` + `wrangler
pages project list` under the owning credential, or the dashboard.

**Q2 — T7: does "by the existing rail" bind?** Both readings scoped verbatim at
`…shape.md:1355-1366`; **neither is picked** anywhere in this packet. **(i) rail-agnostic** →
**LEG-1 is LANDED**, S7/S8 are **MEASURE + contract**. **(ii) "existing rail" binds** → the
profile seam is **ported into the Contente rail**, S7/S8 **keep a build branch**. Under (ii)
**Q1 must be answered first** — the ported seam lands in a rail whose account is unknown, which
is the mechanical reason DP-2's `on_fail` blocks S8.

**Q3 — the contract.** Of `{header bytes, slug alphabet, parity receipt shape, audience
DEFAULT-DENY, root-404, revocability (CC-1)}`, which are **COMMON** (both rails must satisfy them;
a conformance fixture per side proves it) and which are **CONTRACT-LOCAL**? **Slug alphabet is
already ruled contract-local** (SG-1, DEFER-3 — §6); the other **five** are open. §5.3 is the
evidence table. **Sixth term added at architect-remediation-1 per CH-04** — found independently by
the companion and security seats, carried by neither the addendum nor RC-1: WS-GUARD calls CC-1
*"the decisive control"*; the Contente rail implements a three-part revocation the fence enumerates
at **INV-12** (`src/fence/run.js:128`, `:292`); **the a8t lane has no ledger (S5-P-3) and so no
revocation path but a re-deploy that omits the slug**. A term absent from the list cannot be sorted
COMMON — its absence sorts it CONTRACT-LOCAL **by default**, the same bias RC-1 corrected one term
over.

### Input constraints — know these seven before answering

1. **A-arm-2 REFUTED (S1).** Served bytes ≠ the producer-frozen Asana attachment: **N=2** of 7
   hashable, **+1,711 B** served carrying an `R1(b)` runtime fix; **Foundation Spine & Posture
   has no HTML attachment at all**. Meanwhile deck-host's own ledger `frozen_sha256` == served
   **9/9** (`VERDICT-cloudflare-pages-host-decks-2026-09-05.md:368` — *labelled DISTINCT; does
   NOT satisfy arm-2*). **Which artifact is the record is CANDIDATE DEFER-5**, routed to the
   ancestor PT-04 remit — **not ruled here**; any COMMON parity clause is blocked on it (§7).
2. **UV-P-6 — the tenuta deploy is not reproducible from any durable artifact.** Its staging root
   is a session-scoped `/private/tmp` scratchpad the environment retires
   (`RESUME-AFTER-RESTART.md:32`); no repo-tracked root, ledger, `wrangler.toml` or committed
   publish script exists under `~/Code` (S5-P-3).
3. **The login asymmetry.** From `tom@tenuta.io` / `974c47a3…`, on a token carrying `pages
   (write)` (G-34, S5-P-1), `wrangler pages deploy … --project-name=deck-host` **CANNOT**
   publish the Contente rail (G-35, S5-P-2) — **yet every floodgates wave surfaces exactly that
   command** (`office_runner.py:152`), and nothing records which credential it is for (S5-P-8).
4. **`wrangler` has no `--account-id` flag** (S5-E-3; §13.5): account resolves **only** from
   config `account_id` or `CLOUDFLARE_ACCOUNT_ID`. **P-7's case-for — "three of four are
   already parameters" — does not hold at the wrangler surface**: three are CLI flags, the
   fourth is not a flag at all. **CORRECTED per CH-02:** the earlier "env prefix or pre-flight
   assertion **only**" is **incomplete**. wrangler 4.107.0 carries a **global `--config`**
   (*"Path to Wrangler configuration file"*, in the bundle) and S5-E-3 already records that the
   account resolves from that file's `account_id`. A **third** surfaced shape therefore exists —
   `wrangler pages deploy <root> --project-name=X --config <profile>/wrangler.toml` — in which the
   account enters as a **flag-selected file wrangler alone parses**. That is an
   **existing-substrate carrier for P-6's tuple**, named as a P-6 sub-form (§4 P-6). It moves **no
   mark**: there is still no `--account-id`, and a wrangler config carries account/project/root but
   **not the ledger**, so **C2 still needs a seam**. §13.5 carries the same "only" and is
   principal-engineer text — **not edited**; the correction rides here and in §4 P-6.
5. **The a8 guard's converse-containment gap** (§12, fixture F-3). `assert_root_hygiene` **never
   consults the ledger**: a **foreign, well-shaped directory absent from the ledger passes the
   FULL gate and the deploy command is surfaced** (S5-Q-1). Today's isolation is an **accident of
   alphabet divergence**, not a designed property — it evaporates under rot-trigger **R-4**.
   **C7 has no implementation anywhere.**
6. **LEG-3 REFUSED (S1).** Both ancestor telos read `UNATTESTED`; 1 of 5 arms ATTESTED; two arms
   were measured **FALSE**. `…shape.md:724`: *"the epoch does NOT proceed to build on an
   unattested lineage… Do NOT quietly downgrade L3."*
7. **EGRESS-DENY-1 has no reach at the deploy gate, on either rail.** *(added per
   SECURITY-REVIEW-S5 RC-1(c).)* The audience gate fires only inside `stage_deck_bundle`
   (`host_bundle.py:141`); `deploy_root_guard.py` has **zero** audience awareness (SR-P-3);
   and deck-host's deny law — **including S3's in-flight fence** — is keyed on **active
   ledger entries**, not on staged directories (`bin/verify.js:193`; `src/fence/run.js:112`
   → `:217`, SR-P-6/SR-P-14), so an artifact with no ledger row is **never classified on
   either rail**. **Any option that mints a second write-into-a-capability-root path
   publishes with EGRESS-DENY-1 never evaluated — and DK-004, the sketch P-5/P-6/P-12 rest
   on, carries no audience clause** (its two acceptance criteria at
   `HANDOFF-strategy-to-10x-dev-2026-09-04.md:84-86` are dry-run/`--confirm` and
   account/project-with-no-cross-org-default; SR-P-8). This bears directly on **Q3**. The
   corrected per-option G-18 column is **§12.4**, which governs. The `clause / condition` column
   in the table below **was refreshed at architect-remediation-1 (CH-03)** and now carries `+C8` on
   the six flagged rows; an earlier note here said that column predated RC-1 — **that is no longer
   true and is retired (D2-R2)**. Where the door page and §12.4 could still differ, **§12.4
   governs.**

### The options

**Mark** = §12 (against C1..**C8**). **Band** = §13. **V-W-C** = VIABLE-WITH-CONDITIONS. Full case-for, dissent, G-29 and G-7 exposure per option: **§4**.

| id | one line | mark | band | one-line dissent | clause / condition |
|---|---|---|---|---|---|
| **P-0** | NULL — no envelope; keep ad-hoc scratchpad publishing | V-W-C | XS (a) / S-M (b) | the status quo is not reproducible; that lane has no ledger at all | **C1**, non-Contente side |
| **P-1** | One root / one ledger — absorb every profile into the Contente root | V-W-C | S | collapses the account **and** the domain boundary; governance, not engineering | **C5** `shape_P` — unsatisfiable for a live divergent-alphabet slug; **+ C8** |
| **P-2** | Per-project root + ledger — N independent ⟨root, ledger, project, domain⟩ tuples | V-W-C · **unconditioned form NON-VIABLE** | M-L | the ledger default derives from the root, so a cross-paired tuple passes **vacuously** | **C2** binding (F-5 fails today); **+ C8** |
| **P-3** | Per-project predicate — one ledger, profile-scoped superset check | V-W-C · **both `null` readings NON-VIABLE unconditioned** | M-L | weakens a fail-closed predicate; all 10 existing rows are profile-`null` | **C3** totality; `null⇒omit` and `null⇒default` are **NON-VIABLE**; 10-row backfill is a HARD PRECONDITION |
| **P-4** | Shared contract without shared code + per-side conformance fixtures | **VIABLE** | S | a contract with no enforcement seam is documentation | none — the natural carrier of **C6** |
| **P-5** | DK-004 as the a8t publisher, floodgates untouched | V-W-C | M (→ L) | DK-004 is a **sketch**; `bin/publish.mjs` does not exist (S5-P-9, G-30) | **C4** at \|live(L)\| ≥ 2 — wipe-then-stage is a mass-orphan event above one deck; **+ C8** (the sharpest G-18 face on the slate) |
| **P-6** | Dual publisher + contract-only declarative bridge | V-W-C | L | mints a config format — **but see the `--config` sub-form (CH-02), which uses an existing carrier**; envelope **placement** is itself directional | **C2** closed by atomicity; **C3 and C5 are not**; **+ C8** |
| **P-7** | Finish the parameterization in the a8 publisher only | V-W-C · **unconditioned form NON-VIABLE** | S · **UNBANDABLE** for the `DECK_HOST` half | widening `DECK_HOST` widens an **egress refusal predicate** (`contact_synthesis.py:309-313`) | **RULED (§12.9)**: the revert asymmetry is a **NON-VIABILITY GROUND**, not an advisory; clause **(iii) slug→host ownership assertion is MANDATORY**; allowlist ships **singleton-by-default** |
| **P-8** | Delegate publish to deck-host (third, profile-neutral substrate) | V-W-C | M-L, **not narrowable until S2 lands** | relocates the root question rather than resolving it; deck-host is mid-S2 and personally owned (G-17) | inherited clause + **SEQUENCED-BEHIND S2** + contract-only, or it is P-11; **+ C8** |
| **P-9** | Domain-only separation — one project, N custom domains | **NON-VIABLE ×2 grounds** | not estimated | every slug becomes reachable from every host | **C7** false by construction **AND** an **independent C8/G-18 ground** — under one project behind N hosts *"which audience"* is unanswerable (§12.4) |
| **P-10** | Account-as-boundary — formalize the observed split | **VIABLE** | XS-S | hard-codes today's co-occurrence as tomorrow's ontology (rot-trigger **R-1**) | none — adds a refusal, removes no check |
| **P-11** | Import / vendor the a8 publisher into a8t | **NON-VIABLE (G-29)** | n/a | clean-room re-derivation duplicates risk — an honest case, **overruled by the prescription** | refused **before** the predicate is reached |
| **P-12** | Data-driven derivation from `brand-tokens/profiles/` | V-W-C | M | couples publishing to branding; the coordinate file must carry a **pointer, never the literal account id** (§12.9(iii)) | **C1/C2** — the Contente publisher is **not derivable** (G-4); **+ C8** |
| **P-13** | No-account-mechanism — fail-closed listability check only | **VIABLE** | XS per side | necessary but not sufficient: two accounts could each hold a project named `deck-host` | none — adds a refusal; satisfies no clause; **composes only**. Pin **identity** via an ENVIRONMENT-supplied `(account_id, project)` pair, **never committed** (§12.9(iii)) |
| **P-14** | **Serve-time routing predicate** — one project + N custom domains + a per-host router at the edge (Pages Function / `_routes.json`) | **PROVISIONAL — RA to confirm** | **PROVISIONAL M-L — PE to confirm** | it is **non-resolution, not containment** — the snapshot still CONTAINS every publisher's bytes; and it opens **R1-by-routing**: a 404 at serve time with the pre-surface gate GREEN | **C3** inverted (the router needs the same non-existent scope field); **the only candidate pre-serve path to C7**; a ninth clause may be owed (*response-shaping only, never body-shaping*, witnessed by INV-08) |

**Several compose.** P-4 / P-6 / P-10 / P-12 / P-13 are **modifiers** riding a **mechanism**
(P-0 / P-1 / P-2 / P-3 / P-7 / P-8 / **P-14**); naming the **combination** is part of the ruling.
**Two postures are now written out and GRADED at §4.1** (PROVISIONAL — RA to confirm).
**Cost is not a tiebreaker between an answer and a modifier** (§13.1).

**P-14 is new at architect-remediation-1** (arch-adversary CH-01, BLOCKING). It is the slate's
**only serve-time mechanism**; P-0..P-13 all act at stage-, deploy- or config-time. **Two appendix
claims it narrows — flagged, not edited:** §12.8 weakness 1 (*"C7 is the only clause with no
mechanical implementation path named"*) and §13.2 (*"no C7 line item to price"*) were true of the
slate as it stood and **predate P-14**; P-14 is the candidate pre-serve path, **pending
requirements-analyst and principal-engineer confirmation at DELTA**. Those sections are RA and PE
text and are byte-identical.

### NON-VIABLE — two, with reasons

- **P-9 — NON-VIABLE on TWO INDEPENDENT GROUNDS.**
  **(1) C7.** One project behind N custom domains makes cross-host containment **false by
  construction**; it deletes the two-sided isolation G-36 verified (Contente slugs → 404 on
  `tenuta-decks.pages.dev`; control → 200 on `decks.cntently.com`). No condition inside the option
  closes it. Its seam is *minutes and no PR* (§13.2) — which is why the refusal needs writing down.
  **(2) C8 / G-18 — an independent ground, surfaced here per D2-R2 from the §12.4 row.** Under one
  project behind N hosts, ***"which audience"* becomes unanswerable**: `classify(deck_template)`
  answers "customer" against the **Contente** producer taxonomy, so a non-Contente deck served from
  the same project would be adjudicated by a classifier that was never about it. **Either ground
  alone is sufficient**; the door page previously showed only the first.
- **P-11, on G-29 (prescribed).** *"a8 → a8t imports are FORBIDDEN"* (`deck-kit/GOAL.md:21`;
  shape §7 Prescribed: *"NON-VIABLE, not merely expensive"*). Refused before the acceptance
  predicate is reached.

### Operator-only — no agent, no exception

The **Q1** answer · the **UV-P-6** statement · **T7** · ratification of **this door** and of the
**two S1 ancestor VERDICTs** · `wrangler deploy` · Cloudflare account/project **create** · **DNS**
· **slug mint** · client **SEND** · deadline re-bind · **RA-1 from S2**. (`…shape.md` §7
Prescribed — reserved levers. The publisher **surfaces** the wrangler command; never runs it.)

### TL-A — structured predictions (added at architect-remediation-1 per CH-05)

Three load-bearing facts in this packet are receipted today and sit on surfaces that **can move
inside the epoch's horizon**, with no re-probe bound to any of them. **Drafted by the
rite-disjoint arch-adversary** (`ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md` §2, "Drafted
entries the remediation may adopt verbatim"); **adopted here substantively unchanged and
attributed.** Horizon is the epoch telos deadline `2026-10-03`
(`.know/telos/hosted-deck-product-epoch.md:60`; attester eunomia `:61`), which was previously
unbound.

| id | claim | what falsifies it | who can observe it | horizon |
|---|---|---|---|---|
| **PR-1** | `assert_deploy_root_ready` (`deploy_root_guard.py:246-258`) **surfaces** a deploy for a root holding a well-shaped 32-hex dir **absent from the ledger** (the F-3 guard gap, S5-Q-1) | the F-3 fixture **REFUSES** at the a8 gate, in either landing shape of §13.3 | **requirements-analyst** (curator) — re-run F-3 | **2026-10-03** |
| **PR-2** | the `wrangler` pinned as deck-host's devDependency exposes **no `--account-id`** on `pages deploy` (S5-E-3) | `grep -c '"account-id"' node_modules/wrangler/wrangler-dist/cli.js` returns **> 0** at the pinned version, **or the pin moves** | **principal-engineer** (curator) | **2026-10-03** |
| **PR-3** | **no** repo-tracked root, ledger, `wrangler.toml` or publish script for `tenuta-decks` exists under `~/Code` (UV-P-6, S5-P-3) | a tracked file matching `publish-tenuta*` or a tenuta ledger appears in any `~/Code` repo — **an operator commit** | **architect** (curator) | **2026-10-03** |
| **PR-4** *(adversary-optional, adopted)* | `decks.tenuta.io` is **not attached** to `tenuta-decks` (`SHIP-RECEIPT-advantage-rc.md`) | `wrangler pages project list` shows a **second domain** on the project | **operator** (curator) | **2026-10-03** |

**PR-4 is rot-trigger R-5 (§3.3) with a horizon attached** — the trigger existed; the clock did
not. **None of these is a sprint completion gate**; each is observable at expiry by the stated
probe. F-1..F-8 remain acceptance criteria and are deliberately **not** listed here.

---

### PRE-SHIP CONFIRMATIONS OWED — listed here, NOT performed

DELTA-2 (`ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md` §D.7) cleared the gate
**PASS-WITH-CONDITIONS**. The two PRE-STAGING conditions (**D2-R1**, **D2-R2**) and the two cheap
PRE-SHIP registrations (**D2-R6**, **D2-R7**) are **applied at architect-staging-1**. The three
below are **other seats' work and are deliberately NOT performed here** — the architect may not
confirm on the RA's, PE's or security seat's behalf. **PT-03 gates the ship; these are what PT-03
is waiting on.**

| id | Owed by | What is owed |
|---|---|---|
| **D2-R3** | **requirements-analyst** | Confirm or reject **P-14's C1–C8 reading** (§4 P-14) → a §12.4 row + §12.5 paragraph; dispose the **"ninth clause"** question (*response-shaping only, never body-shaping*); amend **§12.8 w1** (*"C7 is the only clause with no mechanical implementation path"*) or record why not; confirm the **Posture A / B** clause unions (§4.1); bind or mark-illustrative the §12 forward claim on wipe-then-stage |
| **D2-R4** | **principal-engineer** | Confirm or reject **P-14's band** (§4 P-14) → a §13.1 row + §13.4 lever row; amend **§13.2** (*"no C7 line item to price"*) and **§13.5** (the `--config` "only", CH-02) or record why not; bind or mark the §13 forward claim on P-5's band |
| **D2-R5** | **security co-seat** | **DELTA on P-14 dissent 3** — whether a per-host router re-deriving *"may this be served"* is the **per-Pages orphan gate C-3 forbids** (`url-capability-contract-cloudflare-host-decks-2026-07-04.md:145-146`). The packet routes it there; the security review on record **predates P-14**, so the routing is unfulfilled until that seat reads the option |

**Why these are not performed here.** §12 and §13 are requirements-analyst and principal-engineer
text and are **byte-identical** across every architect leg (hash convention in the changelog).
Where P-14 narrows a claim in either section, the architect **flagged it in P-14 and on this page
and did not edit the section** — that is the whole point of the split. **Nothing on this page or in
§4 P-14 is a mark**; both PROVISIONAL blocks say so in their own first line.

### Where to look

| Need | Section |
|---|---|
| the probes behind every claim here | **§0 ENTRY GATE** (S5-P-1..11; cited elsewhere as §0.2 / §0.3) · **§12.0** (S5-Q) · **§13.0** (S5-E) |
| asymmetry · seam map · rot-triggers R-1..R-5 · full option cases · the three questions | **§1** · **§2** · **§3.3** · **§4** · **§5** |
| slug clause + DEFER-SG1-REANCHOR · A-arm-2 / DEFER-5 · DK-004 · carried UV-P + ownership facts | **§6** · **§7** · **§8** · **§9** |
| **P-14 in full** (the serve-time option) · the **T7 row** that places it · the **UV-P register** (now incl. UV-P-7 / UV-P-8) | **§4 P-14** · **§5.2** · **§9.1** |
| predicate C1..**C8** · fixtures F-1..**F-8** · marks in full · bands · seam cost · C5 closure estimate | **§12.1** · **§12.3** · **§12.4-12.5** · **§13.1** · **§13.2** · **§13.3** |

**Self-assessment: MODERATE** (`self-ref-evidence-grade-rule`). **This page restates; it adds no claim.** Every platform-behavior sentence on it carries a **G-NN** anchor, an **S5-P/Q/E** receipt id, or a **UV-P** label. **It contains no answer and no ruling.**

---

**OPERATOR DECISION PACKET (one-way door #2).** Authored at S5 (WS-B, DESIGN half),
rite 10x-dev, architect lead. **RUNG = authored** — this advances no leg. It
ENUMERATES; the OPERATOR rules.

This packet does **not** answer F-PUBLISH and does **not** rule T7. It carries an
exhaustive option slate, per-option dissent, the a8→a8t contract-vs-code disposition,
a PROVISIONAL G-7 SUPERSET exposure statement per option, and three ordered questions.

> **THROUGHLINE (verbatim, binding).** "A non-Contente-profile deck is served at a
> capability URL by the existing rail with zero regression on what already works, and
> both ancestor telos are closed by a rite-disjoint attester — nothing counts as done
> because a PR merged."

**Evidence discipline.** Every platform-behavior sentence carries a **G-NN** frame
anchor, an **SG-/SV-** shape anchor, an **S5-P-NN** probe receipt minted in §0, or a
**UV-P** label in the frozen `structural-verification-receipt` syntax. A sentence
with none of those does not appear here. Self-assessment caps **MODERATE**
(`self-ref-evidence-grade-rule`); nothing in this packet is self-attested as
realized.

---

### RULINGS TRANSCRIBED — 2026-09-05 sitting (scribal act; STAGED, NOT STAMPED)

> **OPERATOR, /interview sitting 2026-09-05; transcribed by the dispatcher (wave 4, Phase 0); source**
> `/Users/tomtenuta/Code/a8t/deck-host/.ledge/handoffs/HANDOFF-wave2-hosted-deck-product-epoch-2026-09-05.md` **§8 :297**, verbatim:
> "DP-2 = account HOLD (UV-P-5 unresolvable from this machine: credential tom@tenuta.io / 974c47a3… sees only tenuta-decks;
> `deck-host` absent; decks.cntently.com live on a zone it cannot enumerate — resolve out-of-band) + **P-10 account-as-boundary
> and P-13 fail-closed listability RATIFIED** as composable, account-independent, on the principle that the a8t and a8 worlds
> are siloed by entity separation (bottom-line online LLC-owned a8/contente vs sovereign projects); the rest of F-PUBLISH stays STAGED."
>
> Rendered into this packet's three questions: **Q1 (UV-P-5)** = HOLD, out-of-band · **Q2 (T7)** = reading (i), RULED at the same sitting
> (telos :142-144; PT-05 recorded PT-01-style 2026-09-05T18:42:43Z) · **Q3 (the contract)** = UNRULED · **mechanism** = UNRULED ·
> **modifiers P-10 + P-13** = RATIFIED as composable, account-independent. No other option is ruled; P-9/P-11 keep their NON-VIABLE marks;
> P-14's later NON-VIABLE (D2-R3) stands as registered. This packet carried no `RULING:` slot at authoring; this block is the slot.
> The dispatcher authored no ruling. Ratification STAMP pending the operator's word; `status: proposed` unchanged.
> Packet sha256 BEFORE this transcription: `c16fcca6913b192842b51d9d2078ebf38528f3ef94c8568732aa9995f4989683` (3441 lines).
> Cross-reference (hosted-deck-conductor, 2026-09-05; not a ruling): the packet's options speak of "a deck" without distinguishing the SERVED
> assessment (the render.mjs product at nogqfo3…; the object publish-tenuta.sh actually staged) from the deck-kit-built exhibits deck
> (unshipped); only P-5 and P-12 are engine-bound. The remaining slate is to be re-read against the SERVED artifact before S8 is framed.

> **RATIFICATION STAMP (PARTIAL).** RATIFIED by the OPERATOR on 2026-09-05 (typed word in session hosted-deck-wave-3 / session-20260905-014608-787b7977, wave 4 Phase 0): the rulings transcribed above are the operator's and are BINDING as far as they go — P-10 + P-13 ratified as composable, account-independent modifiers; T7 reading (i); the account (UV-P-5) HELD out-of-band; **Q3 (the contract) and the mechanism remain UNRULED** and no option beyond P-10/P-13 is ratified by this stamp.
> Binds to the transcribed packet sha256 `4a1b5d69da5b12b937503b1ccf388824846380017c41e80e21b8dbbc68cae564` (3460 lines). Written by the dispatcher on the operator's word; the dispatcher authored no ruling. Consequence recorded elsewhere: S8 entry :587 is satisfied ONLY as far as the partial ratification reaches — the account clause stays a carried UV-P unless the operator waives it; the operator chose 'Freeze first, then S8' at the same sitting, and RA-1 is HELD, so S8 stays BLOCKED on :588.

## §0 — ENTRY GATE (STEP 0): re-probed, never inherited

UV-P-6 was **re-probed at S5 entry**, not inherited from the frame or the shape. The
probes below are read-only. **No `wrangler` write, no project create, no deploy, no
DNS, no mint, no SEND was performed.** Reserved levers are operator-only (shape §7).

### 0.1 Numbering correction (verified; carried)

The shape is internally inconsistent about UV-P ids in the WS-B region:

| Location | Label used | For |
|---|---|---|
| `hosted-deck-product-epoch.shape.md:788` (DP-2 `first_questions`) | "UV-P-4" | account ownership of `deck-host` |
| `…shape.md:449` (S5 `entry_criteria`) | "UV-P-5" | the tenuta-decks staging root + deploy command |
| `…shape.md:711` (PT-03 region) | "UV-P-5" | the staging root |
| `…shape.md:457` (S5 `exit_criteria`) | "UV-P-4" | account ownership |
| `…shape.md:890` (Phase-0 operator-input list) | **"UV-P-7"** | `publish-tenuta.sh` — a **third** distinct slip; already flagged in the PT-00 checkpoint rationale (`.sos/sessions/session-20260905-014608-787b7977/events.jsonl`, PT-00 record: *"shape :890 says UV-P-7 — a numbering slip vs the §10.3 register"*) |

**The §10.3 register at `…shape.md:1453-1460` is AUTHORITATIVE.** It reads:

- **UV-P-4** = `publish-tenuta.sh` and the whole `scratchpad/` tree — home **S5**
- **UV-P-5** = which Cloudflare account owns Pages project `deck-host` +
  `decks.cntently.com` — home **S5 / DP-2, the packet's FIRST question**
- **UV-P-6** = which staging root and ledger produced the `tenuta-decks` deployment
  — home **Phase-0 operator input**, re-cited as an S5 entry criterion

**This packet uses the register numbering throughout.** The prose labels at `:449`,
`:711`, `:788` and `:890` disagree with the register and should be read as register
ids. The correction is recorded here and not silently applied. Note there is **no
`UV-P-7`** in the register — the id at `:890` refers to register **UV-P-4**.

### 0.2 S5-local probe register (minted here)

Precedent for minting sprint-local anchor ids: the shape mints `SG-1`, `SG-2`, `SV-1`
at `…shape.md:1390-1397` for observations the frame does not carry. These `S5-P-NN`
ids are **S5-local receipts, not frame anchors** — they corroborate or extend G-NN,
they never replace it.

| id | Claim | Method | Receipt (verbatim / anchored) |
|---|---|---|---|
| **S5-P-1** | The operator's wrangler login is `tom@tenuta.io`, account `974c47a3be9b85d1b4986b85c1c3ede3`, token carrying **28 scopes** including `pages (write)`, `account (read)`, `zone (read)`. **Corroborates G-34** by a second pair of hands. | bash-probe | `CI=1 npx --no-install wrangler whoami` in `/Users/tomtenuta/Code/a8t/deck-host` → `👋 You are logged in with an OAuth Token, associated with the email tom@tenuta.io.` / `│ Tom@tenuta.io's Account │ 974c47a3be9b85d1b4986b85c1c3ede3 │` / scope list of 28 rows incl. `- pages (write)`, `- account (read)`, `- zone (read)`. Wrangler `4.107.0`. |
| **S5-P-2** | Exactly **one** Pages project is visible from that credential: `tenuta-decks`. `deck-host` is **absent**. **Corroborates G-35.** | bash-probe | `CI=1 npx --no-install wrangler pages project list` → single row `│ tenuta-decks │ tenuta-decks.pages.dev │ No │ 5 hours ago │`. No `deck-host` row. |
| **S5-P-3** | **UV-P-6 — the tenuta staging root is an EPHEMERAL session scratchpad, not a durable repo path.** | bash-probe + file-read | `find /Users/tomtenuta/Code -maxdepth 8 … -iname '*tenuta*deck*'` → **zero hits**; `find … -name 'publish-tenuta*'` under `~/Code` → **zero hits**. `/Users/tomtenuta/Code/external/advantage-rc` contains **no** `package.json`, **no** `bin/`, **no** `wrangler.toml`. The root resolves to `/private/tmp/claude-501/-Users-tomtenuta-Code-external-advantage-rc/{session-uuid}/scratchpad/`, named verbatim in a tracked ledger artifact: `advantage-rc/.ledge/decisions/RESUME-AFTER-RESTART.md:32` — *"Scratchpad moved: working assets now at `/private/tmp/claude-501/-Users-tomtenuta-Code-external-advantage-rc/75ee569d-51ee-4c3f-b39d-5138ae32c941/scratchpad` (… `publish-tenuta.sh`, …). **The previous scratchpad path is retired by the environment.**"* |
| **S5-P-4** | **UV-P-4 — `publish-tenuta.sh` LOCATED and READ.** Its deploy command is verbatim `wrangler pages deploy "$DIST" --project-name "$PROJECT"`, `PROJECT="${PROJECT:-tenuta-decks}"`, `CLOUDFLARE_ACCOUNT_ID="${…:-974c47a3be9b85d1b4986b85c1c3ede3}"`, `DIST="$(dirname "$0")/dist-tenuta"`. | file-read | `/private/tmp/claude-501/-Users-tomtenuta-Code-external-advantage-rc/75ee569d-51ee-4c3f-b39d-5138ae32c941/scratchpad/publish-tenuta.sh` (3.1 KB, mode 755, mtime 2026-09-04 21:56). Staged output confirmed at `…/fda5697d-…/scratchpad/dist-tenuta/` → `_headers` + `nogqfo3pizvjhbdbxvvsvhdgt/index.html`, **two entries only**. |
| **S5-P-5** | **UV-P-5, PARTIAL — a candidate account id for the Contente rail exists as a literal in the sibling script.** `publish.sh` (the Contente-rail variant, same scratchpad family) carries `export CLOUDFLARE_ACCOUNT_ID=a245df42893c85a8d96c71cfa46eec76   # the account that owns Pages project deck-host (Aug-27 deploy receipt)`. **This is a file-read of a CLAIM, not a verified ownership fact** — it cannot be checked from this machine (S5-P-2). | file-read | `…/fda5697d-07f8-4768-a4c4-09347e8316f7/scratchpad/publish.sh` (2.5 KB, mode 755, mtime 2026-09-04 19:48), line beginning `export CLOUDFLARE_ACCOUNT_ID=`. |
| **S5-P-6** | **The deck-host ledger has NO account, project, domain or profile dimension.** Entry fields are exactly `deck_file, office, deck_template, frozen_sha256, minted_at, status`. 10 entries: 9 `active`, 1 `revoked`. | bash-probe | `node -e` over `config/deck-manifest.json` → `top-level keys: [ 'version', '_comment', 'decks', '_backfill_2026-07-09' ]`; `entry fields: [ 'deck_file','office','deck_template','frozen_sha256','minted_at','status' ]`; `status histogram: { revoked: 1, active: 9 }`. |
| **S5-P-7** | The Contente publish root holds exactly **9 32-hex slug dirs + `_headers`**. | bash-probe | `ls /Users/tomtenuta/Code/a8t/deck-host/public/` → the nine 32-hex names + `_headers`; `ls -d public/*/ \| wc -l` → `9`. |
| **S5-P-8** | **Three of the four envelope dimensions are ALREADY parameters in the a8 publisher; ACCOUNT is absent entirely and DOMAIN is a pinned constant behind an egress guard.** | file-read | `batch.py:335` `--deploy-base`; `:345` `--deck-manifest`; `:355` `--project-name` (help: *"Cloudflare Pages project name (surfaced into the wrangler command; operator-domain)"*). `office_runner.py:204` and `:404` take `project_name: str \| None`; `:152` `project = project_name or DECK_HOST_PAGES_PROJECT`. Recursive grep for `CLOUDFLARE_ACCOUNT\|account_id\|account-id` across `onboarding_walkthrough/` → **zero matches**. `link_on_play.py:62` `DECK_HOST: str = "decks.cntently.com"`, consumed at `office_runner.py:268` `deck_url = f"https://{DECK_HOST}/{slug}/"` and **enforced** at `contact_synthesis.py:310-313` (`if host.lower() != DECK_HOST: raise ContactCardEgressRefused`). |
| **S5-P-9** | **G-30 freshness: the load-bearing half HOLDS; the inventory has drifted.** `deck-kit/bin/publish.mjs` still does-not-exist. `bin/check-render.mjs` now EXISTS (DK-001 landed). | git-ls-files + bash-probe | `git -C ~/Code/a8t/deck-kit ls-files --error-unmatch bin/publish.mjs` → `error: pathspec 'bin/publish.mjs' did not match any file(s) known to git`, exit 1; `ls bin/publish.mjs` → `No such file or directory`. `ls deck-kit/bin/` → `build.mjs check-render.mjs prep-fonts.mjs prep-images.mjs verify.mjs`. Branch `feat/dk-001-dk-005-render-check-and-negative-fixtures` @ `d8c7794`. |
| **S5-P-10** | `wrangler 4.107.0` is a **deck-host** devDependency, not an advantage-rc one. | file-read | `deck-host/package.json` → `"devDependencies": { "wrangler": "4.107.0" }`; `advantage-rc/package.json` → `No such file or directory`. Consistent with `publish-tenuta.sh`'s `MISE_DIR=/Users/tomtenuta/Code/a8t/deck-host   # only for the node-22 pin so wrangler runs; nothing there is read or written`. |
| **S5-P-11** | The five declared brand profiles are `a8t fixture lotusun-brand lotusun-cream tenuta`. **Corroborates G-5.** | bash-probe | `ls /Users/tomtenuta/Code/a8t/brand-tokens/profiles` → `a8t fixture lotusun-brand lotusun-cream tenuta`. |

### 0.3 UV-P dispositions at S5 entry

**UV-P-4 — `publish-tenuta.sh`: DISCHARGED at S5 by direct probe (S5-P-4).** The file
is on disk and was read. The register recorded it OPEN because it was sought at
`scratchpad/publish-tenuta.sh` relative to the advantage-rc checkout
(`…shape.md:1458`, G-41); it lives at the session-scoped tmp scratchpad the
`RESUME-AFTER-RESTART.md:32` note names. **Consumed per SVR §1 RULE-1** (a subsequent
artifact in the same initiative attaches a non-vacuous receipt for the same claim).
The `scratchpad/` *tree* half remains partially open — it is ephemeral by
construction and is **not** a durable substrate (S5-P-3).

**UV-P-6 — staging root + deploy command: DISCHARGED-WITH-A-FINDING.** Both halves
are now receipted (S5-P-3, S5-P-4). The finding the operator should see:

> The tenuta lane's staging root is a **session-scoped `/private/tmp` scratchpad that
> the environment retires** (`RESUME-AFTER-RESTART.md:32`). There is no repo-tracked
> root, no `wrangler.toml`, no ledger, and no committed publish script anywhere under
> `~/Code` (S5-P-3). The live `tenuta-decks` deployment (G-33, G-37) is therefore
> **not reproducible from any durable artifact today**. This is a finding about
> reproducibility, not about correctness — the deploy happened and the bytes verify
> (G-37). It is stated, not ruled.

**UV-P-5 — account ownership: STILL OPEN, but NARROWED.** A candidate account id
`a245df42893c85a8d96c71cfa46eec76` is on disk as a comment-annotated literal
(S5-P-5). It is **not verified** — S5-P-2 shows the credential on this machine cannot
list any project in that account, so the claim cannot be checked from here, and the
`decks.cntently.com` **zone** ownership was not probed at all. Carried forward as:

```
[UV-P: Pages project `deck-host` and the DNS zone for decks.cntently.com are owned by
Cloudflare account a245df42893c85a8d96c71cfa46eec76 | METHOD: `wrangler whoami` +
`wrangler pages project list` under the Contente-owning credential, or the Cloudflare
dashboard account switcher; the zone half additionally needs `zone (read)` on that
account | REASON: the id is a file-read of a comment in an ephemeral publish script
(S5-P-5), not a verified ownership fact; the credential present on this machine lists
only `tenuta-decks` (S5-P-2, G-35), so no probe available here can confirm or refute
it, and the zone was not probed at all]
```

---

## §1 — THE ASYMMETRY, STATED PLAINLY

This is the fact the packet exists to put in front of the operator.

**From the operator's own login — `tom@tenuta.io`, account
`974c47a3be9b85d1b4986b85c1c3ede3`, a token carrying 28 scopes *including*
`pages (write)` (G-34, S5-P-1) — the command**

```
wrangler pages deploy <root> --project-name=deck-host
```

**CANNOT publish the Contente rail.** `deck-host` is not a project in that account
(G-35, S5-P-2). The refusal is not a permissions shortfall — the token holds
`pages (write)`; the project is simply **elsewhere**.

**Yet every floodgates wave surfaces exactly that command.**
`office_runner.py:145-153`:

```python
def _surface_wrangler_command(deploy_root: Path, project_name: str | None) -> str:
    """The exact reserved-lever command to SURFACE (never execute)."""
    project = project_name or DECK_HOST_PAGES_PROJECT
    return f"wrangler pages deploy {deploy_root} --project-name={project}"
```

with `DECK_HOST_PAGES_PROJECT = "deck-host"` at `:142` (G-6), surfaced once per wave
at `batch.py:257` after the fail-closed guard passes.

**Three consequences the operator should weigh at DP-2:**

1. **The surfaced command is credential-relative.** It is correct for whoever holds
   the Contente credential and inert for the operator's own login. Nothing in the
   publisher records **which** credential it is correct for — the account is not a
   parameter, not a constant, not a log line, not a check (S5-P-8: zero matches for
   any account identifier across `onboarding_walkthrough/`).
2. **The tenuta lane already solved this, ad hoc, and outside the repo.**
   `publish-tenuta.sh` pins `CLOUDFLARE_ACCOUNT_ID` explicitly, gates on
   `wrangler whoami | grep -q 'tom@tenuta.io'` (exit 4) and on
   `wrangler pages project list | grep -q "$PROJECT"` (exit 5) **before** deploying
   (S5-P-4). That is precisely DK-004's "refuse if wrangler cannot list the project"
   acceptance criterion, already implemented once — in an ephemeral file (S5-P-3).
3. **From this machine the operator can publish tenuta and cannot publish contente.**
   The frame states this as correct isolation, not a defect (frame §9.9, "Consequence
   for T3"). It is nonetheless the hinge of every option below.

---

## §2 — SEAM MAP: where account / project / domain / ledger enter TODAY

The DP-2 question is *where the per-profile parameter enters*. Before enumerating
options, here is the honest current state — **three of four dimensions are already
parameters** (S5-P-8). This materially narrows the design space and is the single
most important input to the slate.

| Dimension | Today | Named seam | Already a parameter? |
|---|---|---|---|
| **Project** | `DECK_HOST_PAGES_PROJECT = "deck-host"` module constant used as a **default**, overridable end-to-end | `office_runner.py:142` (constant), `:152` (`project_name or …`), `:204`/`:404` (signature), `:226`/`:297` (call sites), `batch.py:355` (`--project-name`, help: *"operator-domain"*) | **YES** — CLI → runner → surfaced command |
| **Root** | wave-shared accumulating deploy root | `batch.py:335` (`--deploy-base`, default `.sos/floodgates/deploy`), `office_runner.py:~208` `deploy_root = deploy_base` | **YES** |
| **Ledger** | committed deck-host ledger; default derived **from the root** | `batch.py:345` (`--deck-manifest`), `deploy_root_guard.py:67-74` `default_manifest_path()` → `<deploy_root>/../config/deck-manifest.json`, consumed at `:179` | **YES**, with a **root-derived default** — this coupling is load-bearing below |
| **Account** | **absent** | — (zero occurrences of any account identifier in `onboarding_walkthrough/`, S5-P-8) | **NO** — implicit in the operator's authenticated shell |
| **Domain** | `DECK_HOST: str = "decks.cntently.com"` | `link_on_play.py:62` (constant), `office_runner.py:268` (URL construction), **`contact_synthesis.py:310-313` (EGRESS GUARD: any non-`DECK_HOST` URL host raises `ContactCardEgressRefused`)** | **NO** — and it is not merely a constant, it is a **refusal predicate** |

**Reading of the map.** The a8 publisher was built with project/root/ledger as
operator-supplied knobs and with domain and account as **invariants**. The domain
invariant is enforced at egress (`contact_synthesis.py:310-313`); the account
invariant is enforced nowhere at all. Any option that makes **domain** per-profile
touches an egress guard; any option that makes **account** per-profile is adding a
dimension the publisher has never had.

### 2.1 The no-orphan machinery the envelope must not weaken

- **`deploy_root_guard.py:162` `assert_manifest_superset`** — *"every non-revoked
  ledger slug MUST be staged in the root… `status=="revoked"` entries are exempt;
  every OTHER status is treated as live (fail-closed: not-explicitly-revoked means
  the deploy must carry it). A missing or unreadable ledger REFUSES — absence of the
  ledger is not permission."* (G-7)
- **`deploy_root_guard.py:8-14` root hygiene** — allowlist is `_headers` + non-symlink
  dirs matching `^[0-9a-f]{32}$`, each holding **exactly** `index.html`. *"The dead
  legacy base32 slug shape is refused by design."* A **25-char base32 tenuta slug dir
  in this root is refused by shape.**
- **`deploy_root_guard.py:142-158`** — the root's `_headers` must be **byte-identical**
  to `host_bundle.HEADERS_FILE_CONTENT` (`host_bundle.py:56`), *"cross-repo drift
  would regress the guard headers on ALL decks"*.
- **`host_bundle.py:68` `_SLUG_RE = re.compile(r"^[0-9a-f]{32}$")`** and **`:79-101`
  `mint_slug()`** (`secrets.token_hex(16)`, G-16) — *"The minted slug MUST be pinned
  in the office manifest and REUSED on any re-run: a re-mint would orphan the
  already-deployed deck (SLUG-1 hazard)."*
- **`host_bundle.py:41` `import secrets`** — the CSPRNG draw is the capability
  guarantee; **N-1** (mailbox never in the URL) is structural (`host_bundle.py:22-28`).
- **`constants.py:14-42`** — the universal-deck ruling: provider-agnostic selection,
  audience **DEFAULT-DENY**, *"absence of a manifest IS denial"* (G-18).

**The failure mode Pages imposes** (`deploy_root_guard.py:2-5`): *"Cloudflare Pages
custom domains serve the LATEST deployment only, and `wrangler pages deploy <root>`
publishes the WHOLE tree as an immutable snapshot."* Everything below turns on that.

---

## §3 — F-PUBLISH OPTION SLATE — spanning FOUR mechanism-times

Authored under `option-enumeration-discipline`. **The numbering is not the
completeness claim** (skill §5: *"Minimum viable slate is NOT a sequential list (A, B,
C…) where the numbering implies completeness"*). Completeness is argued structurally
in §3.1 below and re-tested per option.

**The heading previously read "(exhaustive)". It was falsified** by the rite-disjoint
arch-adversary at CH-01 (BLOCKING): every option then on the slate acted at **stage-, deploy- or
config-time**, and **no option acted at serve-time** — a mechanism-category blind spot the skill
names as a HIGH-confidence truncation signal (§3, "all enumerated options share the same primary
mechanism category"). **P-14 is added at architect-remediation-1** and the heading now names the
axis the slate spans rather than asserting exhaustiveness:

| mechanism-time | options |
|---|---|
| **(none — the null)** | P-0 |
| **stage-time** (root-and-ledger topology, evaluated before a command is surfaced) | P-1 · P-2 · P-3 · P-5 · P-8 · P-12 |
| **deploy-time** (what the publisher surfaces / asserts at the moment of deploy) | P-7 · P-10 · P-13 |
| **config-time** (contract, envelope data, DNS posture — no runtime component) | P-4 · P-6 · P-9 |
| **serve-time** (a predicate evaluated per request, after the snapshot is published) | **P-14** |
| **refused class** | P-11 (G-29, prescribed) |

**The axis is now named, and naming it is a stronger claim than "exhaustive" was** — a future
reader can test the slate against the axis rather than against a word. **If a sixth
mechanism-time is found, this heading is falsified again and the slate is truncated again.**

Each option carries: **mechanism** — **dissent** (the explicit case against, authored
at equal depth to the case for) — **G-29 contract-vs-code** — **PROVISIONAL G-7
SUPERSET exposure**.

**On the G-7 marks.** This packet states each option's SUPERSET exposure and **does
not issue final NON-VIABLE marks on R1 grounds.** The acceptance predicate — the
restatement of no-orphan for N roots as a testable predicate — is
**requirements-analyst's next artifact** (shape `:426` S5 roles). Marks below read
`PROVISIONAL`. The only NON-VIABLE marks issued here are on **G-29**, which is a
prescribed constraint (shape §7 Prescribed: *"An option that imports a8 code into a8t
is NON-VIABLE, not merely expensive"*) and therefore rulable at design time.

### 3.1 Author self-audit (option-enumeration-discipline §4 Step 1)

| Forced question | Answer | Option that covers it |
|---|---|---|
| What existing substrate did I NOT consider as a carrier? | Cloudflare's own multi-custom-domain support; the `brand-tokens/profiles/` envelope (G-5, S5-P-11); deck-host's own `wrangler.toml` + `bin/verify.js` | **P-9**, **P-12**, **P-8** |
| Is there an option where the problem is solved by NOT adding mechanism? | Two: do nothing; and refuse to model the account at all | **P-0**, **P-13** |
| Is there a delegation option? | Two: delegate to the a8t side (DK-004); delegate to a third profile-neutral substrate (deck-host) | **P-5**, **P-8** |
| Is there a hybrid I evaluated as a subset rather than standalone? | Yes — "contract + declarative envelope" was initially folded into the contract option; split out | **P-6** split from **P-4** |
| This design MINTS A CLASSIFICATION ("profile"). What ENDURING PREDICATE does each class encode? | See §3.3 — the predicate is *"the organisation whose Cloudflare account holds the serving project and whose brand tokens the deck is built from."* Today that co-occurs with brand profile, account, project, domain and slug alphabet **all at once**. A name that encodes a co-occurrence is a packaging accident. | §3.3 |
| What are the ROT-TRIGGERS? | See §3.3 | §3.3 |
| Is a data-driven derivation enumerable NOW, even if rejected-for-now? | Yes | **P-12** |

### 3.2 Slate at a glance

| id | Option | G-29 | PROVISIONAL G-7 exposure |
|---|---|---|---|
| **P-0** | NULL — no envelope; keep one rail + ad-hoc scratchpad publishing | viable | **NONE-NEW** (Contente rail untouched) |
| **P-1** | ONE ROOT / ONE LEDGER — absorb every profile into the Contente accumulating root | viable | **LOUD-REFUSAL, not silent** |
| **P-2** | PER-PROJECT ROOT + LEDGER — N independent (root, ledger, project, domain) tuples | viable | **PROVISIONAL-EXPOSED** (root↔ledger default coupling) |
| **P-3** | PER-PROJECT PREDICATE — one ledger, profile-scoped superset check | viable | **PROVISIONAL-EXPOSED (sharpest)** |
| **P-4** | SHARED CONTRACT WITHOUT SHARED CODE — versioned contract + per-side conformance fixtures | viable | **NONE-NEW** |
| **P-5** | DK-004 AS THE a8t PUBLISHER, FLOODGATES UNTOUCHED | viable | **NONE-NEW** (exposure-minimal) |
| **P-6** | DUAL PUBLISHER + CONTRACT-ONLY BRIDGE — declarative profile envelope, parsed independently by each side | viable | **PROVISIONAL-EXPOSED, mitigable by tuple-atomicity** |
| **P-7** | FINISH THE PARAMETERIZATION IN THE a8 PUBLISHER ONLY ("why not just…") | viable — **but see the egress-guard flag** | **PROVISIONAL-EXPOSED** (inherits P-3) |
| **P-8** | DELEGATE PUBLISH TO deck-host (third, profile-neutral substrate) | viable **only** in the contract-only shape | **PROVISIONAL-EXPOSED** (collapses to P-1 or P-2) |
| **P-9** | DOMAIN-ONLY SEPARATION — one project, N custom domains | viable | **NONE-NEW for orphaning; OVER-SERVE risk instead** |
| **P-10** | ACCOUNT-AS-BOUNDARY — formalize the observed split | viable | **NONE-NEW** |
| **P-11** | IMPORT / VENDOR THE a8 PUBLISHER INTO a8t | **NON-VIABLE (G-29)** | n/a — refused before exposure is reached |
| **P-12** | DATA-DRIVEN DERIVATION from `brand-tokens/profiles/` | viable | **NONE-NEW if fail-closed; PROVISIONAL-EXPOSED if it defaults** |
| **P-13** | NO-ACCOUNT-MECHANISM — account is a property of the authenticated env; the only duty is a fail-closed listability check | viable | **NONE-NEW** |
| **P-14** | SERVE-TIME ROUTING PREDICATE — one project + N custom domains + a per-host router at the edge (Pages Function / `_routes.json`) | viable — **a8t-side code; the a8 publisher untouched**. NON-VIABLE variant: a router that imports/vendors a8 ownership logic (= P-11) | **PROVISIONAL-EXPOSED — AT A NEW TIME.** R1-by-routing: a 404 at **serve time** with every pre-surface predicate GREEN. Not the deploy-time exposure this column was built for |

### 3.3 The classification this design would mint — enduring predicate and rot-triggers

`option-enumeration-discipline` §5(5) requires this block whenever a design mints a
class token, **because operator-facing surfaces calcify first**. If DP-2 rules for any
option that externalizes a `--profile` flag or a `profile:` config key, the following
must ride the ADR.

**Candidate enduring predicate**: *"a **profile** is the organisation whose Cloudflare
account holds the serving Pages project and whose brand tokens the deck is built
from."*

**Why the name is at risk today**: for the two live instances, profile co-occurs with
**five** things simultaneously — brand profile (G-5/S5-P-11), Cloudflare account
(G-34/G-35), Pages project (G-6/G-33), serving domain (`link_on_play.py:62` vs
`tenuta-decks.pages.dev`) and slug alphabet (SG-1). **N=2 is not enough to tell an
ontology from a packaging accident.**

**Named ROT-TRIGGERS** (observable events that would falsify the classification):

| # | Trigger | What it falsifies |
|---|---|---|
| R-1 | A second **project** appears inside **one** account (e.g. `tenuta-decks-staging`) | account ≡ profile |
| R-2 | One project acquires a **second custom domain** serving a different brand | domain ≡ profile |
| R-3 | A deck for brand profile X is published to the account associated with profile Y (an agency arrangement) | brand ≡ profile |
| R-4 | A third slug alphabet consumer appears, or two profiles agree on one alphabet | alphabet ≡ profile |
| R-5 | `decks.tenuta.io` is attached to `tenuta-decks` (already anticipated: `SHIP-RECEIPT-advantage-rc.md` — *"Custom domain: decks.tenuta.io NOT attached at 2026-09-05T00:31Z… The same slug resolves there once attached; no redeploy needed"*) | one-domain-per-project |

**Consequence for the operator**: if DP-2 rules for an option with an operator-facing
`profile` token, that token needs a **deprecation-tolerant parse plan** now, because
R-1..R-5 are all plausible within the epoch's horizon. **P-12** is the option in which
the classification is derived rather than named, and is the one that survives R-1..R-4
without a token migration.

---

## §4 — THE OPTIONS, IN FULL

### P-0 — NULL: no envelope

**Mechanism.** Nothing changes. The a8 publisher keeps `deck-host` as its project
default (G-6) and `decks.cntently.com` as its domain invariant
(`link_on_play.py:62`). Non-Contente decks continue to be published the way the live
one actually was: by hand, from an ephemeral scratchpad script, under the operator's
own credential (S5-P-3, S5-P-4).

**Case for.** It is the only option with a **live, verified 200** behind it (G-33,
G-37). It touches no guard, no ledger, no egress predicate. It costs nothing and
forecloses nothing.

**Dissent (explicit).** The observed status quo is **not reproducible**: the staging
root is a `/private/tmp` path the environment retires
(`RESUME-AFTER-RESTART.md:32`, S5-P-3), the script is untracked, and no ledger records
the tenuta slug anywhere in a repo. If the operator must re-publish
`nogqfo3pizvjhbdbxvvsvhdgt` — or revoke it — there is no durable artifact to do it
from. P-0 also leaves the §1 asymmetry permanently unrecorded in code: the publisher
keeps surfacing a command that is inert under the operator's own login, with nothing
in the repo saying so.

**G-29.** Viable — no code crosses.
**PROVISIONAL G-7 exposure: NONE-NEW.** The Contente rail is untouched, so no live
Contente slug can be 404'd by anything P-0 does.

---

### P-1 — ONE ROOT / ONE LEDGER: absorb every profile into the Contente accumulating root

**Mechanism.** The frame §9.6 table's "one root" leg. Every profile stages into the
same wave-shared accumulating root; the same `config/deck-manifest.json` is the single
ledger of record; profile becomes a **field on a ledger entry**, never a channel. One
project, one domain, one superset predicate — exactly as today, with more rows.

**Case for.** The no-orphan predicate stays literally unchanged
(`deploy_root_guard.py:162`): one root, one ledger, superset-or-refuse. There is
exactly one place where a live deck can be orphaned, and it is already guarded and
already tested. The ledger gains one column (S5-P-6 shows it has none today), which
is the smallest possible schema delta.

**Dissent (explicit).** It fails on **three** independent structural facts, any one of
which is disqualifying:
1. **Root hygiene refuses the slug shape.** `deploy_root_guard.py:8-14` allowlists
   `_headers` + `^[0-9a-f]{32}$` dirs only, and explicitly refuses base32 by design.
   The live tenuta slug is 25-char base32 (G-33, SG-1). A tenuta deck cannot be
   staged into this root without either re-minting it (orphaning the live 200 — the
   SLUG-1 hazard named at `host_bundle.py:79-101`) or **unifying the alphabets**,
   which shape §7 puts **out of scope** (SG-1, DEFER-3).
2. **It collapses the account boundary.** One root serves one project in one account.
   P-1 requires the Contente decks and the tenuta decks to share a Cloudflare account
   — the exact thing DK-004's acceptance criterion forbids (*"no default that points
   at another organisation's project"*) and the exact thing the current topology has
   (correctly, per frame §9.9) kept separate.
3. **It collapses the domain boundary.** All slugs would resolve under one host. A
   Contente client deck and a Tenuta client deck would be siblings on one hostname.

**G-29.** Viable — no code crosses; this is an a8-side change only.
**PROVISIONAL G-7 exposure: LOUD-REFUSAL, NOT SILENT.** This is the important nuance.
If a base32 profile slug is staged into the Contente root, `assert_root_hygiene`
raises `DeployRootRefused`, `batch.py:249-253` clears every `wrangler_command`, and
**no command is surfaced**. Nothing is deployed, so nothing is orphaned — Pages keeps
serving the previous snapshot (`deploy_root_guard.py:2-5`). The exposure is to
**publishing availability** (the wave halts), not to silent 404. Loud is the correct
behaviour; it is still an exposure the operator should price.

---

### P-2 — PER-PROJECT ROOT + LEDGER: N independent tuples

**Mechanism.** Each profile gets its own `(root, ledger, project, domain)` tuple. The
G-7 predicate is applied **N times independently**, once per root, unmodified. The
publisher is invoked once per profile with `--deploy-base`, `--deck-manifest` and
`--project-name` already-existing flags (S5-P-8); only **account** and **domain** need
new seams.

**Case for.** The superset predicate itself is **never weakened** — this is the option
in which `assert_manifest_superset` keeps its exact current semantics and is simply
instantiated more than once. Blast radius is per-profile by construction: a mistake in
the tenuta tuple cannot reach a Contente slug, because they share no root and no
ledger. It matches the observed topology (two accounts, two projects, two roots)
rather than fighting it.

**Dissent (explicit).** The **ledger default is derived from the root**:
`deploy_root_guard.py:67-74` returns `<deploy_root>/../config/deck-manifest.json`. With
one tuple that coupling is invisible and safe. With N tuples it becomes the primary
hazard: point `--deploy-base` at root A while the derived (or explicitly passed)
ledger is B's, and `assert_manifest_superset` passes **vacuously** — it checks A
against B's short list, finds no orphans, and surfaces a deploy command for a root
that is missing every one of A's live slugs. Pages then publishes the whole tree
(`deploy_root_guard.py:2-5`) and A's live decks 404. **That is a silent-404 path and
it is the one the operator most needs the acceptance predicate to close.** P-2 also
multiplies operator surface: N roots, N ledgers, N accounts to keep straight, with
`--project-name` help text (`batch.py:355-359`) currently saying only
"operator-domain".

**G-29.** Viable — no code crosses.
**PROVISIONAL G-7 exposure: EXPOSED.** The root↔ledger pairing is the exposed joint.
A mitigation exists and should be named for requirements-analyst: **make the tuple
atomic** — refuse to accept a root and a ledger that do not declare each other, so a
mismatched pair is a refusal rather than a vacuous pass. Not ruled here.

---

### P-3 — PER-PROJECT PREDICATE: one ledger, profile-scoped superset check

**Mechanism.** One ledger of record keeps every slug across every profile.
`assert_manifest_superset` (`deploy_root_guard.py:162`) gains a profile filter: when
staging profile X's root, only X's non-revoked slugs must be present.

**Case for.** One ledger means one place to look for "what is live anywhere", which is
genuinely valuable for revocation and for audit. It avoids P-2's root↔ledger pairing
hazard entirely — there is only one ledger, so it cannot be the wrong one.

**Dissent (explicit).** **This is the option that weakens the guarantee itself, and
the packet says so plainly.** The current predicate is fail-closed by construction:
*"`status=="revoked"` entries are exempt; every OTHER status is treated as live
(fail-closed: not-explicitly-revoked means the deploy must carry it)"*
(`deploy_root_guard.py:162-172`). A profile filter converts an **exemption whitelist of
one value** into an **inclusion predicate over a new field** — and the ledger has **no
profile field today** (S5-P-6: entries are `deck_file, office, deck_template,
frozen_sha256, minted_at, status`). Every one of the 10 existing rows would be
profile-`null`. The filter must then decide what `null` means, and **every** answer is
bad:
- `null` ⇒ "belongs to no profile" ⇒ silently omitted from every root ⇒ **9 live
  client decks 404 on the next deploy**;
- `null` ⇒ "belongs to the default profile" ⇒ the fail-closed property is restored
  only for as long as the default is right, and it re-breaks the moment a second
  Contente-shaped profile exists;
- `null` ⇒ REFUSE ⇒ the ledger must be backfilled before any deploy — safe, but it is
  a hard precondition of the same class as the Option-B backfill
  (`ADR-taskcache-projection-coverage-2026-07-08.md:63` §(f): *"HARD PRECONDITION:
  operator backfill of deck-host's STALE `public/`… PV the live deployment, never a
  local manifest (standing scar)"*).

**G-29.** Viable — no code crosses.
**PROVISIONAL G-7 exposure: EXPOSED — SHARPEST OF THE SLATE.** This is the only option
in which a mislabelled or unlabelled ledger row silently drops a live client deck out
of the predicate's scope. Flagged for the requirements-analyst acceptance predicate
and for the security critic as the highest-attention option.

---

### P-4 — SHARED CONTRACT WITHOUT SHARED CODE

**Mechanism.** Neither publisher changes shape. What is written down is a **versioned
contract artifact** naming the terms both rails must satisfy, plus **conformance
fixtures on each side independently**. The frame already asserts the two publishers
are *"different shapes by design, not by drift"* (frame §9.6); P-4 makes that a
checkable claim rather than a prose one.

**Case for.** It is the only option that directly answers DP-2's third question
without touching either publisher. It respects G-29 by construction — a contract is
prose plus fixtures, and fixtures live on each side of the boundary. It is reversible:
a contract can be amended; a root split cannot be un-split without a re-mint.

**Dissent (explicit).** A contract with no enforcement seam is documentation. The
`_headers` term is the cautionary case: it **is** already enforced cross-repo
(`deploy_root_guard.py:142-158` byte-compares the root's `_headers` against
`host_bundle.py:56` `HEADERS_FILE_CONTENT`) — and the tenuta side reproduces those
exact four header lines **by hand-copied heredoc** in `publish-tenuta.sh` (S5-P-4).
Two hand-copies of the same four lines with no comparison between them is drift
waiting to happen, and the drift would be invisible until a served-header probe caught
it. P-4 also does not answer §1: it records the asymmetry without changing anything
about it.

**G-29.** **Viable and specifically well-formed.** Shape §7 Prescribed:
*"**Contracts may be shared; code may not.**"* P-4 is the shape of option that clause
contemplates.
**PROVISIONAL G-7 exposure: NONE-NEW.** No publisher behaviour changes.

---

### P-5 — DK-004 AS THE a8t PUBLISHER, FLOODGATES UNTOUCHED

**Mechanism.** The non-Contente profile is served by an **a8t-side** publish lever
(the `bin/publish.mjs` DK-004 sketches). The a8 publisher is not modified at all: no
new parameters, no predicate change, no ledger change. The two rails are permanently
separate programs.

**Case for.** **Zero exposure to the Contente rail, by construction** — this is the
exposure-minimal option in the slate. It is also the option the world already
half-ran: `publish-tenuta.sh` is a working instance of this shape (S5-P-4) whose live
output verifies (G-33, G-37). It sits cleanly inside the a8t clean-room posture
(G-29).

**Dissent (explicit).** **DK-004 is a SKETCH.** `deck-kit/bin/publish.mjs`
does-not-exist — re-probed at S5 entry, still absent (S5-P-9, G-30). Ruling for P-5
would be ruling for a thing that must then be built, and **this packet may not
schedule it** (shape §7 out-of-scope: *"Scheduling any DK-001..DK-005 item as an epoch
sprint"*). P-5 also does nothing for the §1 asymmetry on the a8 side and gives up the
one-ledger audit view: two publishers, two ledgers, no single answer to "what is live
anywhere". And under T7 reading (ii) it is **the wrong answer by construction** — see
§5.2.

**G-29.** Viable **provided** DK-004 is built clean-room, as deck-kit's own posture
demands (`GOAL.md:15-24`: *"Not a port of the Contente deck-stage.js producer… The
fleet rule is absolute: a8 → a8t imports are FORBIDDEN… ZERO code was copied"*).
Note that P-5's dissent and P-11's refusal are the same boundary seen from two sides.
**PROVISIONAL G-7 exposure: NONE-NEW.**

---

### P-6 — DUAL PUBLISHER + CONTRACT-ONLY BRIDGE

**Mechanism.** P-4's contract, made **machine-readable**. A declarative per-profile
envelope — an object naming `{account_id, project, domain, root, ledger, slug_shape,
headers_bytes}` as **one atomic tuple** — is published as data. Each publisher parses
it **independently, in its own language**, with no shared code. The a8 side reads it
to populate `--deploy-base` / `--deck-manifest` / `--project-name` (S5-P-8) and to
gate on the account; the a8t side reads it to populate DK-004's pinned account and
project.

**Case for.** It is the option that makes P-2's exposed joint **structurally closed**:
if root and ledger are fields of one tuple that is read atomically, a mismatched pair
is not expressible. It answers DP-2's first question mechanically — the account
becomes a declared, checkable value instead of an invisible property of a shell — and
it is the natural carrier for the fail-closed listability check (P-13, DK-004). It
satisfies G-29 exactly: **data crosses, code does not.**

**Dissent (explicit).** It mints a new configuration format, and configuration formats
calcify (see §3.3 R-1..R-5). Two independent parsers of one schema is two places for
the schema to be misread, and the misreads are asymmetric across languages. It also
requires deciding **where the envelope lives** — an a8 path, an a8t path, or a third
place — and that placement decision is itself directional across the boundary the
epoch is trying not to cross. Nothing in the envelope is enforced unless each side
also carries conformance fixtures, so P-6 is strictly **P-4 plus a schema**, not a
replacement for it.

**UN-NAMED SUB-FORM, added at architect-remediation-1 per CH-02 — and it dissolves the principal
dissent above.** The "mints a new configuration format … two independent parsers" objection assumes
the envelope must be a **new** format. It need not be. wrangler 4.107.0 carries a **global
`--config`** (*"Path to Wrangler configuration file"*, in the bundle) and resolves `account_id`
from the file it names (S5-E-3). So **P-6-via-wrangler-config** is available: a per-profile
`wrangler.toml` carrying `account_id` + `name`, selected at deploy by
`wrangler pages deploy <root> --project-name=X --config <profile>/wrangler.toml`. The envelope is
then an **existing format with exactly one parser — wrangler's own** — which is the
"existing substrate not mentioned" and "delegate to an already-capable CLI" check the
`option-enumeration-discipline` mechanical scan fires on. **What it does NOT carry: the ledger.**
A wrangler config binds account + project + root; it has no field for `L_P`, so **C2's binding half
still needs a seam** and the sub-form narrows the dissent without closing the clause. **Marks
unmoved.** Flagged for the RA at DELTA.
`[UV-P: pages deploy honors a --config-supplied account_id at runtime | METHOD: wrangler pages project list --config <tmp.toml carrying account_id> under the operator's credential, read-only | REASON: adopted from the arch-adversary's own UV-P (ADVERSARY-REPORT §3.2); this seat fires no wrangler write and the config path was not exercised — the flag and the account_id resolution are each receipted separately, their COMPOSITION is not]`

**G-29.** Viable — data crossing is explicitly permitted (*"Contracts may be shared;
code may not"*). **Non-viable variant to avoid:** shipping a shared **parser library**
consumed by both sides — that is code crossing, and if it originates a8-side it is
P-11.
**PROVISIONAL G-7 exposure: EXPOSED, MITIGABLE.** Exposure is P-2's, and tuple
atomicity is the named mitigation. Whether atomicity is sufficient is exactly the
question for the requirements-analyst acceptance predicate.

---

### P-7 — FINISH THE PARAMETERIZATION IN THE a8 PUBLISHER ONLY ("why not just…")

**Mechanism.** The a8 publisher already parameterizes project, root and ledger
(S5-P-8). Complete the set: add an account parameter and make `DECK_HOST` a
parameter. One publisher then serves every profile, including non-Contente ones. No
a8t publisher is built.

**Case for — corrected in place (evidence floor R6).** P-7's appeal is that it looks
like the smallest delta to "where does the parameter enter." **That appeal is weaker
than it first reads, and the correction belongs here, not only in the appendix.**
Three of the four dimensions are **CLI flags** on the a8 publisher today, but they do
not all reach the same place: `--project-name` (`batch.py:355`) reaches the surfaced
command **end-to-end** (→ `run_office(project_name=…)` at `office_runner.py:204` →
`:152` `project = project_name or DECK_HOST_PAGES_PROJECT`, **G-6**); `--deploy-base`
(`batch.py:335`) reaches the runner (`office_runner.py:201`, `:210`
`deploy_root = deploy_base`); and `--deck-manifest` (`batch.py:345`) reaches **the
guard ONLY, never the runner** (→ `_gate_wave_deploy_command` at `batch.py:216`/`:221`
→ `assert_deploy_root_ready(manifest_path=…)` at `:247`; the `run_office` call site at
`batch.py:196-206` is never passed it). **The fourth dimension — account — is not a
`wrangler` flag at all.** `wrangler` 4.107.0 resolves the account **only** from the
config-file `account_id` key or the `CLOUDFLARE_ACCOUNT_ID` environment variable;
there is **no `--account-id` flag** on that surface (**§13.5**, **S5-E-3**). It can
therefore enter only as an **env prefix** on the surfaced command — the shape
`publish-tenuta.sh` already uses (S5-P-4) — or as a **pre-flight assertion** (P-10 /
P-13), which is a different program. **P-7's "the rest is additive" case-for does not
hold at the wrangler surface**: the three that are done are done *as flags*, and the
fourth is a different mechanism, producing a different operator-instruction shape than
`_wave_halt_banner` prints today. What survives of the case-for is real but narrower —
P-7 still preserves one predicate, one guard implementation and one test suite, and
there is no second program to keep in sync, so P-4/P-6's drift problem never arises.

**Dissent (explicit). Two objections, the second serious.**
1. **It inherits P-3's exposure wholesale.** One publisher over N profiles needs
   either N roots+ledgers (then it *is* P-2) or a profile-scoped predicate (then it
   *is* P-3, with P-3's `null`-profile hazard over 10 existing rows, S5-P-6).
2. **Making `DECK_HOST` a parameter weakens an egress guard.** `DECK_HOST` is not a
   formatting constant. `contact_synthesis.py:305-313` raises
   `ContactCardEgressRefused` for **any** URL host that is not `DECK_HOST` exactly,
   and `link_on_play.py:58-62` records why: *"The ONLY host a deck URL may point at
   (N3 QA pre-merge condition)… an exact netloc match refuses userinfo (user@host), an
   explicit port (host:port), and any foreign host in one predicate, so an
   attacker-supplied URL can never be composed into a posted comment."* Turning a
   single-value equality check into a set-membership check over operator-supplied
   values is a change to a **posted-comment egress predicate**. Shape §7 out-of-scope
   forbids *"Weakening any WS-GUARD invariant to make per-profile publishing easier."*
   Whether a widened allowlist is a *weakening* or a correct *generalization* is
   **not ruled here** — it is flagged as the single item on this slate most in need of
   the **security rite's** dissent (S5's `rite_disjoint_exit_critic`).

**G-29.** **Viable — and this is the subtle one, so state it precisely.** G-29 forbids
**a8 → a8t imports**: *"a8 → a8t imports are FORBIDDEN"* (`deck-kit/GOAL.md:21`,
G-29). P-7 adds parameters to a8 code that a8 continues to own and run. **No a8 code
is imported into a8t.** P-7 is therefore **NOT** disqualified on G-29. What it does is
place a8t-profile publishing under **a8 governance** — a different objection, made on
posture rather than on the prescribed rule, and one the operator must weigh separately.
**PROVISIONAL G-7 exposure: EXPOSED (inherited from P-2 or P-3, per which shape it
takes).**

---

### P-8 — DELEGATE PUBLISH TO deck-host (a third, profile-neutral substrate)

**Mechanism.** Neither floodgates nor deck-kit owns the envelope. `deck-host` — which
already carries `wrangler.toml` (`name = "deck-host"`,
`pages_build_output_dir = "public"`), a `bin/` with `verify` and `mint-slug`
entrypoints, and the ledger itself — grows the publish lever. Both producers hand it a
staged root; it owns account/project/domain/ledger for everyone.

**Case for.** It is the genuine **delegation** option (`option-enumeration-discipline`
§5(4)). deck-host is already the ruled durable accumulation substrate
(`ADR-taskcache-projection-coverage-2026-07-08.md:63` §(f): *"deck-host IS the durable
accumulation substrate"*, G-20) and already holds the ledger and the verifier. It is
also **a8t-side by location** (`/Users/tomtenuta/Code/a8t/deck-host`), so a lever built
there is on the permitted side of the boundary. The tenuta lane already borrows
deck-host as a toolchain host: `publish-tenuta.sh` sets
`MISE_DIR=/Users/tomtenuta/Code/a8t/deck-host   # only for the node-22 pin so wrangler
runs; nothing there is read or written` (S5-P-4) — a runtime-toolchain coupling that
already exists and is explicitly non-reading.

**Dissent (explicit).** It does not actually resolve the root question; it relocates
it. deck-host's `public/` **is** the Contente root (S5-P-7: 9 32-hex dirs +
`_headers`), so a deck-host publish lever that stages non-Contente slugs into `public/`
is **P-1** wearing a different hat and hits the same shape refusal; one that stages
elsewhere is **P-2**. deck-host's repo remote is **personal**
(`git@github.com:tomtenuta/deck-host.git`, G-17) while the Contente rail's account is
disjoint from the operator's login (G-34, G-35) — so P-8 concentrates the whole
publishing surface into a personally-owned repo that publishes into an account nobody
on this machine can reach. That is a governance question, not an engineering one.
deck-host is also mid-reconciliation: `bin/verify.js:77` enforces a 26-char base32
shape matching neither live surface (G-12, frame §9.7) and **S2 is reconciling it right
now** — building on it while it moves is a sequencing hazard.

**G-29.** Viable **only** in the contract-only shape. If the deck-host lever were
implemented by copying `host_bundle.py` / `deploy_root_guard.py` logic across, that is
**P-11** and is NON-VIABLE. Re-deriving equivalent behaviour clean-room from a written
contract is permitted (*"Contracts may be shared; code may not"*).
**PROVISIONAL G-7 exposure: EXPOSED — collapses to P-1's or P-2's exposure.**

---

### P-9 — DOMAIN-ONLY SEPARATION: one project, N custom domains

**Mechanism.** Profiles are separated purely at the DNS/custom-domain layer. One
account, one Pages project, one root, one ledger; each profile gets its own custom
domain pointed at the same project.

**Case for.** It uses an **existing platform substrate** rather than adding mechanism,
and the epoch already anticipates the move: `SHIP-RECEIPT-advantage-rc.md` records
*"Custom domain: decks.tenuta.io NOT attached… The same slug resolves there once
attached; no redeploy needed."* Cheapest possible profile surface: attach a domain,
done. The no-orphan predicate is untouched — one root, one ledger, exactly as G-7
was written.

**Dissent (explicit). This option inverts the risk rather than removing it.** With one
project behind N domains, **every slug is reachable from every domain**. A Contente
client deck would be fetchable at `decks.tenuta.io/{contente-slug}/` and vice versa.
That is not an orphan risk — it is a **containment** risk, and it runs directly at the
capability-URL contract and the audience DEFAULT-DENY posture (`constants.py:14-42`,
G-18; WS-GUARD, G-19). The current isolation is **verified two-sided**: G-36 records
Contente slugs `207688021de8…` and `761ebfd8a7e1…` returning **404** on
`tenuta-decks.pages.dev` while the control on `decks.cntently.com` returns **200**.
P-9 would delete exactly that property. It is enumerated here for completeness and
because a domain attach is a low-friction operator action that could arrive by
accident; the operator should see the consequence written down before it does.

**G-29.** Viable — no code crosses; this is a Cloudflare configuration posture.
**PROVISIONAL G-7 exposure: NONE-NEW for orphaning; OVER-SERVE risk instead.**
Routed to the security critic as a leak-by-containment path (S5's
`rite_disjoint_exit_critic` remit, verbatim: *"does any option create a
leak-by-containment path or weaken audience DEFAULT-DENY at egress?"*).

---

### P-10 — ACCOUNT-AS-BOUNDARY: formalize the observed split

**Mechanism.** The Cloudflare **account** is declared the profile boundary. One
account ⇒ one profile ⇒ one project ⇒ one root ⇒ one ledger ⇒ one domain. The
publisher's only new duty is to **pin** the account it expects and refuse if the
authenticated credential is a different one.

**Case for.** It is the topology that **already exists and already works**: Contente in
one account (G-35 — `deck-host` absent from `974c47a3…`), tenuta in the operator's
own (G-33, G-34, S5-P-2), with verified two-sided isolation between them (G-36). It
makes the §1 asymmetry **explicit and checkable** rather than silent: a publisher that
pins its account would refuse loudly under the wrong credential instead of surfacing an
inert command. `publish-tenuta.sh` already implements exactly this — `whoami | grep -q
'tom@tenuta.io'` → exit 4; `pages project list | grep -q "$PROJECT"` → exit 5 (S5-P-4)
— and DK-004 states it as an acceptance criterion.

**Dissent (explicit).** It hard-codes today's **co-occurrence** as tomorrow's
**ontology** — precisely the packaging accident §3.3 warns about, falsified by
rot-trigger **R-1** (a second project inside one account) the first time a staging
project appears. It also makes account creation a prerequisite for every new profile,
and account create is an operator-reserved lever (shape §7). And it does not by itself
say anything about root, ledger or predicate — P-10 is a **boundary declaration**, not
a mechanism, so it must be combined with P-2, P-5 or P-6 to be a complete answer.

**G-29.** Viable — no code crosses.
**PROVISIONAL G-7 exposure: NONE-NEW.** Account pinning adds a refusal; it removes no
check.

---

### P-11 — IMPORT / VENDOR THE a8 PUBLISHER INTO a8t — **NON-VIABLE (G-29)**

**Mechanism (stated so the class is refused explicitly, per the enumeration
discipline's requirement that a rejected mechanism be named rather than omitted).**
Any option in which a8-side publisher code reaches a8t: deck-kit or deck-host
importing, vendoring, porting or pasting `host_bundle.py`, `deploy_root_guard.py` or
`office_runner.py`; a shared parser/validator library originating a8-side and consumed
a8t-side; a git submodule or copied module carrying floodgates logic into `~/Code/a8t`.

**Disposition: NON-VIABLE — refused on a PRESCRIBED constraint, not on cost.** Shape
§7 Prescribed: *"**The a8 → a8t import boundary is DIRECTIONAL and absolute.** 'a8 →
a8t imports are FORBIDDEN' (deck-kit `GOAL.md:21`, `README.md:254`; zero code copied,
`README:253-255`; G-29). **Contracts may be shared; code may not.** An option that
imports a8 code into a8t is NON-VIABLE, not merely expensive."* The constraint is
self-declared by the a8t side: *"Not a port of the Contente `deck-stage.js` producer
(`~/Code/a8`). The fleet rule is absolute: a8 → a8t imports are FORBIDDEN. Conventions
were read for orientation…; ZERO code was copied"* (`deck-kit/GOAL.md:19-23`).

**Dissent (recorded, and overruled by the prescription).** The honest case for P-11 is
that `deploy_root_guard.py` encodes hard-won no-orphan semantics that a clean-room
re-derivation may get subtly wrong, and re-deriving it is duplicated risk. **That
argument does not survive the prescription** and is recorded only so the slate is not
accused of strawmanning the refused class. The permitted discharge of that concern is
**P-4/P-6**: share the *semantics* as a written contract plus per-side conformance
fixtures, so the a8t re-derivation is checkable without any code crossing.

**G-29: NON-VIABLE.**
**G-7 exposure: n/a** — refused before exposure is reached.

---

### P-12 — DATA-DRIVEN DERIVATION from `brand-tokens/profiles/`

**Mechanism.** The classification is **derived**, not declared. A profile already
exists as a first-class directory: `brand-tokens/profiles/` holds `a8t`, `fixture`,
`lotusun-brand`, `lotusun-cream`, `tenuta` (G-5, S5-P-11), and deck-kit already
defaults its profile root there (`deck-kit/bin/build.mjs:30` `DEFAULT_PROFILE_ROOT`,
G-27). Publish coordinates become a declared file **inside the profile the deck was
built from**, so `--profile tenuta` yields account/project/domain/ledger/slug-shape
without any new taxonomy.

**Case for.** This is the `option-enumeration-discipline` §5(5) data-driven option, and
it is the one that **survives rot-triggers R-1..R-4** (§3.3) without an operator-facing
token migration: if account and project decouple, the profile file simply carries both
fields. It reuses an envelope that already exists and is already the thing that
determines what the deck looks like — so "which profile" is already answered upstream
of publishing, and the publisher stops guessing.

**Dissent (explicit).** It couples **publishing** to **branding**, and those may not
stay coupled (rot-trigger **R-3**: brand X published under account Y). It puts
Cloudflare account ids into `brand-tokens`, a repo whose purpose is design tokens —
that is a scope creep with a security dimension (account ids in a repo that may have
wider read access than the publisher does). `DEFAULT_PROFILE_ROOT` is currently
hardcoded to an **absolute path** (`deck-kit/bin/build.mjs:30`, G-27; the DK-004
addendum in `HANDOFF-strategy-to-10x-dev-2026-09-04.md` records *"hardcoded to
`~/code/a8t/brand-tokens/profiles` (clean-checkout green only with that sibling
present)"*), so derivation today rests on a machine-local assumption. And the Contente
rail has **no** entry under `profiles/` — Contente brand binding lives in
`@autom8y/contente-tokens` on the a8 side (G-4) — so the derivation covers the a8t
profiles and **not** the profile that actually matters for G-7.

**Must-be-fail-closed.** If P-12 is ruled, the derivation must **REFUSE** when a
profile directory carries no publish coordinates. A default — of account, project,
domain or ledger — reintroduces exactly the class DK-004's acceptance criterion names:
*"Account and project are parameters with no default that points at another
organisation's project."*

**G-29.** Viable — the derivation is a8t-side data; nothing is imported from a8.
**PROVISIONAL G-7 exposure: NONE-NEW if fail-closed; EXPOSED if it defaults.** The
exposure is entirely a function of the missing-coordinates behaviour.

---

### P-13 — NO-ACCOUNT-MECHANISM: the account is a property of the environment

**Mechanism.** The publisher **never models the account**. It takes no account
parameter, stores no account id, and reads no account config. Its entire
account-related duty is a **fail-closed listability check**: *can the authenticated
credential list the named project?* If not, refuse before staging anything. Account
correctness is delegated to the operator's shell, and the check catches every case
where the shell is wrong.

**Case for.** It is the second "solve by NOT adding mechanism" option, and it is the
one **already proven twice**. `publish-tenuta.sh` gates on
`wrangler pages project list … | grep -q "$PROJECT"` → exit 5 *"PROJECT $PROJECT not
visible in account $CLOUDFLARE_ACCOUNT_ID — refusing"* (S5-P-4), and the Contente-side
`publish.sh` gates on `wrangler pages deployment list --project-name deck-host` → exit
5 *"PROJECT NOT REACHABLE — the credential cannot see Pages project deck-host…;
refusing to deploy so nothing is created elsewhere"* (S5-P-5). DK-004 states the same
rule as an acceptance criterion. It keeps account ids **out of repos entirely** —
which, given S5-P-5 found one sitting in a script comment, is not a hypothetical
benefit. And it is robust to every rot-trigger in §3.3, because it asserts nothing
about what an account *means*.

**Dissent (explicit).** A listability check is **necessary but not sufficient**: it
proves the credential can see *a* project of that name, not that it is *the right*
project. Two accounts could each hold a project named `deck-host`, and the check would
pass in both. It gives the operator no **declared** record of intended topology, so
UV-P-5-shaped questions ("which account owns this?") stay unanswerable from the repo
forever — the check is a runtime guard, not documentation. And it is orthogonal rather
than alternative: P-13 composes with P-2/P-5/P-6/P-10 and answers none of their root,
ledger or predicate questions.

**G-29.** Viable — no code crosses.
**PROVISIONAL G-7 exposure: NONE-NEW.** It only ever adds a refusal.

---

### P-14 — SERVE-TIME ROUTING PREDICATE: one project + N custom domains + a per-host router at the edge

> **Added at architect-remediation-1 in response to `ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md`
> CH-01 (BLOCKING).** The adversary's finding is accepted without argument: P-0..P-13 all act at
> **stage-, deploy- or config-time**; **none acts at serve-time**, and the substrate has no
> serve-time component today (S5-Q-7). That is a mechanism-category blind spot under
> `option-enumeration-discipline` §3 ("all enumerated options share the same primary mechanism
> category" — HIGH-confidence detection signal), and it is load-bearing rather than cosmetic
> because two of the packet's own C7 statements rest on the truncated slate. **The slate is
> corrected here; the option is enumerated at equal depth and is NOT recommended.**

**Mechanism.** ONE Cloudflare Pages project, ONE deploy root, ONE ledger, **N custom domains** —
plus a **per-host routing predicate evaluated at the edge**: a Pages Function (or `_worker.js`)
with `_routes.json`, mapping each host in `H_P` to exactly the slug set its publisher owns, and
**404-ing everything else**. Where P-9 attaches N domains and lets every host resolve every slug,
P-14 adds the predicate P-9 lacks. It is the **first and only** option on the slate whose
mechanism runs **after** the snapshot is published and **before** the bytes reach a requester.

**Case for.** Three things no other option offers.
1. **It is the only candidate pre-serve path to C7.** Every other option leaves C7 a post-deploy
   live probe (§12.8 w1; §13.2). A router evaluates the containment predicate *on every request*,
   which is strictly earlier than an N×M curl sweep and strictly later than a pre-surface gate —
   a third position the packet did not have.
2. **It leverages an existing substrate the slate never named.** `_routes.json` and Pages
   Functions are first-class in the pinned toolchain, not a bespoke build (S5-R-3).
3. **One root, one ledger, one predicate.** C1–C6 and C8 keep their N=1 shape exactly — P-14 adds
   no second tuple to bind (P-2's C2 hazard) and no scope field to backfill (P-3's C3 hazard).
   It is the only option that gets multi-host serving **without** touching the no-orphan machinery.

**Dissent (explicit) — four objections, and the second is the one that may kill it.**
1. **Containment or only non-resolution? — the question the operator must actually answer.**
   A routing predicate refuses a slug on the wrong host **at serve time**. It does **not** remove
   the bytes: `wrangler pages deploy` publishes the WHOLE tree as an immutable snapshot
   (`deploy_root_guard.py:2-5`), so **the snapshot still CONTAINS every publisher's bytes**, and
   every host is backed by that one artifact. **That is non-resolution, not containment.** G-36's
   two-sided isolation is containment *by construction* — the tenuta project does not hold the
   Contente bytes at all (Contente slugs 404 there because they are absent, not because a rule
   declined to serve them). P-14 replaces an **absence** guarantee with a **code-path** guarantee.
   Every failure mode of the router — a mis-deployed Function, a `_routes.json` that excludes the
   path so the Function never runs, a rollback to a snapshot whose Function predates a host — is
   a containment failure that an absence guarantee cannot have. **Naming this precisely is the
   point of the option; the packet does not rule which of the two the epoch requires.**
2. **R1-by-routing — a NEW silent-404 surface, at a NEW time.** Every other option's R1 risk is
   at stage/deploy time, where a fail-closed gate can refuse before a command is surfaced. P-14
   moves R1 to **serve time, after the gate has passed and the deploy has succeeded**: a router
   keyed on a field the ledger does not have (**the scope field does not exist** — S5-P-6, and
   C3's totality clause exists precisely because of it) resolves every unscoped row to "owned by
   nobody" and **404s all nine live Contente decks on every host** — with a GREEN pre-surface
   gate and a successful deploy. It is the only option on the slate that can produce an R1 event
   **with every enumerated pre-deploy predicate satisfied**. This is not a reason to refuse it; it
   is the reason its acceptance predicate cannot be C1–C8 alone.
3. **It creates a second site where the audience verdict is evaluated — or bypassed.** A router
   deciding what may be served is, functionally, a second gate on the same question
   `classify(deck_template)` answers. C-3 forbids exactly this shape: *"egress MUST CONSUME the
   producer `assert_customer_deck` classification… MUST NOT mint a per-Pages orphan gate"*
   (`url-capability-contract-cloudflare-host-decks-2026-07-04.md:145-146`). A host router that
   re-derives "may this be served" is a per-Pages orphan gate by another name. **Routed to the
   rite-disjoint security seat, unruled here** — this is the same G-18/C8 face the six flagged
   options carry (§12.4), arriving by a different road.
4. **It concentrates rather than separates.** P-10's whole case-for is that account/project
   separation is *already* the live topology, verified two-sided (G-36). P-14 deliberately
   un-separates and buys the separation back in code. An operator who values the current
   isolation should read P-14 as spending a structural guarantee to purchase a flexibility.

**CONTRACT-vs-code across the a8→a8t boundary (G-29) — VIABLE.** The router is **a8t-side code**:
it lives in the `deck-host` project (a `functions/` directory or `public/_worker.js` plus
`_routes.json`), in a repo whose remote is personal (G-17), on the a8t side of the boundary.
**No a8 code is imported into a8t** — the prohibition G-29 states (*"a8 → a8t imports are
FORBIDDEN"*, `deck-kit/GOAL.md:21`). The a8 publisher is **untouched**: no floodgates file changes,
no new flag, no predicate edit. **Non-viable variant to avoid** (same shape as P-6's and P-8's):
a router that *imports or vendors* `host_bundle.py` / `deploy_root_guard.py` logic to decide
ownership is **P-11** and is NON-VIABLE on the prescribed constraint. The ownership map must be
**data** the router reads — which is the same "contracts may be shared; code may not" seam P-4/P-6
already describe.

**Seam points it touches.**

| Surface | Touched? | Anchor |
|---|---|---|
| **deck-host project config** | **YES** — a `functions/` dir or `public/_worker.js`, plus `_routes.json`; `wrangler.toml` currently declares only `name = "deck-host"` / `pages_build_output_dir = "public"` and neither file exists (**S5-R-4**) | `deck-host/wrangler.toml`; S5-R-4 |
| **the a8 publisher** | **NO — untouched.** `office_runner.py`, `deploy_root_guard.py`, `host_bundle.py`, `batch.py`: zero edits | §2 seam map |
| **the ledger** | **read by the router**, not restructured — but see dissent 2: the router needs an ownership field the ledger does not have (S5-P-6) | `config/deck-manifest.json` |
| **DNS / custom-domain attach** | **OPERATOR LEVER** — reserved, never scheduled (`…shape.md` §7 Prescribed: DNS is operator-only) | §0 "Operator-only" |
| **the fence** | the router is a new serve-path the fence's served-arm must cover; INV-08 hash-parity already sits on the served bytes | `src/fence/run.js:248` |

**Does the D-02 ruling prescribe it away? — NO. D-02 CONSTRAINS the shape; it does not forbid it,
and it DATES the slate rather than the option.** The ancestor fork resolved
**D-01 = Pages / D-02 = direct-upload** (`host_bundle.py:3-4`, crossed at PT-01 on the Contente
account 2026-07-06). Direct-upload names *how the artifact reaches Pages* (no git provider, no
build command — `deck-host/wrangler.toml`: *"direct-upload (no build command)"*), **not whether
the project may carry a Function**. The pinned toolchain uploads both from the same
`pages deploy` path (**S5-R-3**: `✨ Uploading _routes.json` and *"Compile a folder of Pages
Functions into a single Worker"* are both in the wrangler 4.107.0 bundle, and the Functions error
string names `wrangler pages de[ploy]` as the command that carries them). **What D-02 does
constrain:** the router must not become a *build* step — it may not re-render, and it may not
introduce a build command, or D-02 is reopened rather than consumed.

**The byte-parity / DW-7 implication — a Function does not rewrite deck bytes UNLESS IT DOES.**
The serving model is *"the host MOVES bytes, it never re-renders"* (`host_bundle.py:8-9`), and
G-PROPAGATE arm-2 requires served-sha == frozen-sha. A router that only **decides whether to
respond** preserves that. A router that rewrites, injects, templates or wraps the response
**breaks byte-parity** — and would do so *invisibly to every pre-deploy predicate*, because the
staged bytes on disk would still hash correctly. **The fence catches it:** INV-08 evaluates hash
parity **on the served bytes** (`src/fence/run.js:248` `guard.evaluateHashParity(p.bodySha, entry.frozen_sha256)`,
in the served-arm list at `:221`), so a rewriting Function shows up as an INV-08 failure on the
live surface. **Consequence for any P-14 acceptance predicate: "the Function is response-shaping
only, never body-shaping" must be a named clause with INV-08 as its standing two-sided witness.**

**PROVISIONAL §12-style mark — P-14 against C1–C8.**
**PROVISIONAL — requirements-analyst to confirm at DELTA or pre-ship. This is the architect's
reading of clauses the RA owns; it is not a mark.**

| | reading | basis |
|---|---|---|
| **R1 silent-404?** | **YES — and by a mechanism no other option has**: at serve time, with the pre-surface gate GREEN (dissent 2) | S5-P-6; §12.1 C3 |
| **R2 leak?** | **NO if the router is correct; the exposure is that correctness is now a code property** (dissent 1) | G-36; `deploy_root_guard.py:2-5` |
| **G-18 / C8?** | **YES — routed to security** (dissent 3) | C-3 `…2026-07-04.md:145-146` |
| **C1 legibility** | unchanged — one ledger | §12.1 |
| **C2 binding** | **not engaged** — one root, one ledger; nothing to cross-pair | §12.1 |
| **C3 partition** | **ENGAGED AND INVERTED.** P-3 needs `scope` to *filter a deploy*; P-14 needs the same non-existent field to *route a request*. C3's totality clause is the router's ownership map | S5-P-6 |
| **C4 no-orphan** | unchanged — the superset predicate keeps its N=1 shape | `deploy_root_guard.py:162` |
| **C5 hygiene** | unchanged — one root, one `shape_P` | §12.1 |
| **C6 headers** | unchanged — one `_headers`. **Open:** whether a Function may set headers, and whether that is a C6 event | `host_bundle.py:56` |
| **C7 containment** | **THE CANDIDATE PRE-SURFACE PATH — and only partially.** It moves C7 from post-deploy probe to serve-time predicate, which is earlier but still not pre-surface: the *predicate's presence* is checkable before surfacing; its *correctness against live hosts* is not | §12.8 w1 |
| **C8** | unchanged in quantifier; **a ninth clause may be owed** — "response-shaping only, never body-shaping", witnessed by INV-08 | `src/fence/run.js:248` |

**Two claims in the appendix that P-14 revises — flagged, NOT edited.**
- **§12.8 weakness 1** (*"C7 is the only clause with no mechanical implementation path named …
  a pre-surface gate cannot run it"*) and **§13.2** (*"No option below carries a C7 line item,
  because there is no pre-surface work to price"*) were **true of the slate as it stood** and are
  **narrowed by P-14's arrival**. **Both are requirements-analyst and principal-engineer text
  respectively; neither is edited here.** The correction rides in this option and on the front
  page (§0). **RA and PE confirm or reject at DELTA.** Note the narrowing is partial, not a
  reversal: per the C7 row above, a routing predicate is *serve-time*, not *pre-surface*.

**PROVISIONAL §13-style band + seam touch list.**
**PROVISIONAL — principal-engineer to confirm. The architect does not band; this is a placeholder
with its uncertainty named, offered so the door is not blank in that column.**

| | |
|---|---|
| **Side** | **a8t code** (deck-host `functions/` or `public/_worker.js` + `_routes.json`) · **operator config** (custom-domain attach) · **a8 code: ZERO** |
| **Provisional band** | **M–L**, with a wide interval |
| **Dominant uncertainty** | **not the router — the ownership map.** The routing code is small; the field it keys on does not exist (S5-P-6) and its backfill is P-3's 10-row HARD PRECONDITION arriving by a different road. **A band that prices the Function and not the backfill would be wrong by the larger term.** |
| **Second uncertainty** | whether the security seat rules dissent 3 a C-3 violation — if so the band is moot, not large |
| **Test cost** | a new two-sided fixture class the slate has none of: a **live-surface** router fixture (correct host → 200; wrong host → 404) **plus** an INV-08 body-shaping negative control. F-1..F-8 are all pre-deploy or served-hash; none of them bites a router |

**PROVISIONAL G-7 exposure: EXPOSED — at a NEW TIME.** Not the deploy-time exposure the column
was built for. Stated here rather than shoehorned into the existing vocabulary, and routed to the
RA as the reason P-14's acceptance predicate cannot be C1–C8 alone.

**Platform-behaviour claims in this option — receipts and one UV-P.**

| id | Claim | Method | Receipt |
|---|---|---|---|
| **S5-R-3** | The pinned toolchain carries Pages-Functions and `_routes.json` support on the `pages deploy` (direct-upload) path. | file-read (bundled CLI) | `node_modules/wrangler/wrangler-dist/cli.js` (wrangler `4.107.0`, S5-P-10): `_routes.json` × 32, `_worker.js` × 18, `"Pages Functions"` × 5. Verbatim: `✨ Uploading _routes.json`; `Compile a folder of Pages Functions into a single Worker`; `Consolidate and optimize route paths declared in _routes.json`; `Ignoring provided _routes.json file, and falling back to the following default routes configuration`; and the Functions guidance string naming `wrangler pages de…` as the carrying command. |
| **S5-R-4** | deck-host has **no** serve-time component today. | git-ls-files + bash-probe | `git ls-files \| grep -iE "functions/\|_worker\|_routes"` → **zero tracked matches**; `ls functions public/_worker.js public/_routes.json _routes.json` → all four `No such file or directory`. Corroborates **S5-Q-7**. |

```
[UV-P: a Pages Function deployed via direct-upload to the deck-host project actually
evaluates a per-host routing predicate at request time, returning 404 for a slug whose
host is not its owner while the same slug returns 200 on its owner host | METHOD: attach a
second custom domain to a Pages project under the operator's own credential, deploy a
minimal Function + _routes.json, and probe both hosts read-only (HEAD both, two-sided) |
REASON: this is RUNTIME behaviour of a not-yet-existing component (S5-R-4) on a project the
credential on this machine cannot reach (G-35, S5-P-2). S5-R-3 receipts that the TOOLCHAIN
ships and uploads the mechanism; it does NOT receipt that the deployed predicate behaves as
designed. Per SVR §1 trigger-table row 7 this is design-choice-masquerading-as-platform-
behaviour unless labelled, and a domain attach + deploy are OPERATOR-RESERVED levers this
packet may not fire]
```

---

### 4.1 Composability — and the two postures, GRADED (CH-06)

Several of these are **not mutually exclusive**, and the operator should not read the
slate as fourteen alternatives. The structurally distinct **mechanism choices** are
P-0 / P-1 / P-2 / P-3 / P-7 / P-8 / P-9 / **P-14**. **P-4, P-6, P-10, P-12 and P-13 are
composable modifiers** that can ride most of them. **P-11 is refused.** Naming which
combination is intended is part of the DP-2 ruling, not a detail below it.

**The union rule is a convention, not an evaluated result** (§13.1) — and it already misses one
recorded interaction (P-13-by-identity re-imports P-12's git-history one-way, §12.9(iii)). The
adversary's CH-06 asks that the two postures the packet names be written out and graded rather
than left implicit. **Both graded below as PROVISIONAL — requirements-analyst to confirm; the
clause readings are the RA's, not mine.**

#### Posture A — **P-2 + P-6 + P-13** (per-project tuple + declarative bridge + assert-never-surface)

| | |
|---|---|
| **Clause union (PROVISIONAL)** | **C2** closed by tuple atomicity **with the sole-source proviso** (§12.5 P-6; fixture **F-5**) · **C3** owed (**F-6**; the envelope set must be **closed and enumerable**) · **C5** owed per publisher (**F-3/F-4**) · **C8** owed per rail (**F-8**) · **C1/C4/C6** unchanged |
| **G-18 / C8** | **YES ×2** — both P-2 and P-6 carry the flagged face (§12.4). The union does **not** cancel it |
| **Account handling** | P-13 supplies the `(account_id, project)` pair **from the ENVIRONMENT and asserts it at runtime; never committed** (§12.9(iii)) — which is also what closes the interaction the union rule misses |
| **One-way** | **two-repo ordered rollback** (§13.2); any deploy fired under a new tuple is not revertible by reverting code |
| **Reserved levers** | the widest on the slate (§13.4) |
| **Hazard the union does NOT surface** | P-13-by-identity vs P-12's git-history one-way — **closed here only because the pair is environment-supplied** (§12.9(iii)). Had P-12 ridden this posture instead of P-13, the union would have read clean and been wrong |

#### Posture B — **P-5 + P-4 + P-13** (a8t publisher + shared contract + assert-never-surface)

| | |
|---|---|
| **Clause union (PROVISIONAL)** | **C4-above-one-deck** (§12.5 P-5 — wipe-then-stage is a mass-orphan event at `|live(L)| ≥ 2`) · **C8** on the a8t rail (**F-8** — *unsatisfiable by either rail's current wiring*, §12.3) · one **C6** fixture per side (§13.2 P-4) · the **P-13** listability assertion |
| **G-18 / C8** | **YES ×1** (P-5 — "the sharpest on the slate", §12.4) |
| **Contente-rail exposure** | **NONE-NEW** — floodgates untouched. This is the exposure-minimal posture |
| **One-way** | **none in code**; but the live slug **must be REUSED**, never re-minted (§13.2; SLUG-1, `host_bundle.py:79-101`) |
| **Reserved levers** | deploy · a second project · the `decks.tenuta.io` attach (**PR-4**) |
| **Hazards** | **nothing exists** (`bin/publish.mjs` does-not-exist, G-30, S5-P-9) and **the precedent is ephemeral** (S5-P-3) · **revocability is absent on the a8t side** (CC-1 — the sixth Q3 term, §5.3) |

**No ranking is implied and none is made.** Two postures are written out because the packet
already named them; **a third posture built on P-14 is NOT graded here** — P-14's own clause face
is PROVISIONAL (§4 P-14) and grading a composition on top of an unconfirmed member would compound
the provisionality rather than reduce it. **The composition space remains larger than two, and
that is a standing property of this packet** (§13.6).

---

## §5 — THE THREE QUESTIONS, IN ORDER

### 5.1 FIRST QUESTION — UV-P-5: which Cloudflare account owns Pages project `deck-host` and `decks.cntently.com`?

**Every option above depends on this answer.** P-1 needs to know whether one account
can hold both. P-2/P-6/P-10 need it as a declared field. P-9 needs it to know whether a
custom-domain attach is even possible. P-13 needs it to know what "the right project"
means. P-0 and P-5 are the only options that survive the question going unanswered —
and only by declining to touch the Contente rail at all.

**METHOD:** `wrangler whoami` + `wrangler pages project list` **under the
Contente-owning credential**, or the Cloudflare dashboard account switcher. The zone
half (`decks.cntently.com`) additionally needs `zone (read)` on that account.

**What S5 could establish:**
- The credential on this machine lists exactly one project, `tenuta-decks`; `deck-host`
  is absent (S5-P-2, G-35) — so the answer is **not obtainable from here**.
- A **candidate** answer exists on disk: `a245df42893c85a8d96c71cfa46eec76`, annotated
  *"the account that owns Pages project deck-host (Aug-27 deploy receipt)"* in
  `publish.sh` (S5-P-5). **This is a file-read of a claim, not a verified fact,** and
  the packet does not promote it.
- The zone ownership was **not probed at all**.

**What the operator is asked for:** confirm or correct the candidate account id, and
state the zone owner. A one-line statement discharges the UV-P; a dashboard screenshot
or a `whoami` under the other credential discharges it with a receipt.

### 5.2 SECOND QUESTION — T7: does "by the existing rail" bind?

**NOT RULED HERE.** T7 is operator-sovereign and its home is **PT-05**
(`…shape.md:1355`, *"PLACED at PT-05, carried as DP-2's second question, and it SCOPES
S7 and S8"*). Both readings are scoped **verbatim** from `…shape.md:1355-1366`:

> **T7 [MINTED THIS SHAPE] — "by the existing rail". PLACED at PT-05, carried as
> DP-2's second question, and it SCOPES S7 and S8.** The operator's THROUGHLINE says
> the deck is served *"by the existing rail"*; telos LEG-1's own text is
> **rail-agnostic**. The 2026-09-04 deck was served by the **a8t** rail (deck-kit +
> the engagement's publish lever, G-24/G-33), not the **a8** rail (floodgates →
> deck-host `public/` → `deck-host` project, G-6/G-7). Reading (i) rail-agnostic →
> **LEG-1 is LANDED** and S7/S8 are MEASURE + contract. Reading (ii) "existing rail"
> binds → the profile seam is ported into the Contente rail and S7/S8 keep a build
> branch. **Both branches are scoped in §2; this shape picks neither.** The reason it
> is a tension and not a defect: had it gone unnamed, S7/S8 would have defaulted to
> build and manufactured work that is already on disk — the exact verify-not-build
> failure the orientation's freshness discipline exists to catch.

**How T7 interacts with the slate** (stated as scoping, not as a recommendation):

| | Reading (i) — rail-agnostic → **LEG-1 LANDED**, S7/S8 MEASURE + contract | Reading (ii) — "existing rail" binds → seam ported into the Contente rail, S7/S8 keep a build branch |
|---|---|---|
| Options that fit | P-0, P-4, P-5, P-6, P-10, P-13 | P-1, P-2, P-3, P-7, P-8 |
| Options that become inert | P-1/P-2/P-3/P-7 (nothing needs porting) | P-5 (an a8t publisher is the wrong rail by construction) |
| **P-14** *(row added per D2-R1)* | **FITS — and needs no port.** P-14 is **a8t-side by construction**: the router lives in the `deck-host` project (S5-R-4) and the a8 publisher is untouched (§4 P-14 seam table). Under a rail-agnostic reading LEG-1 is LANDED and S7/S8 are MEASURE + contract; P-14 has nothing to port because the mechanism is **new, not moved** | **FITS, BUT IS UNADDRESSABLE BEFORE Q1.** "Existing rail" binding does **not** make P-14 inert — a serve-time predicate is precisely the sort of thing that would be ported *into* the Contente rail. But a Pages Function deploys to a **named project in a named account**, and which account owns that project **is UV-P-5** (§5.1) |
| Consequence for §1 asymmetry | stays as recorded, unresolved in code | must be resolved — the seam cannot be ported into a rail the operator cannot publish to without first answering §5.1 |

**P-14's ordering dependency is the sharpest on the slate, and it is why that row is asymmetric.**
Every other option's dependency on Q1 is about *whether the surfaced command works*. P-14's is about
*where a piece of code physically lives*: under reading (ii) an unanswered UV-P-5 does not delay
P-14 — it leaves the Function **nowhere to land**. Under reading (i) the same option is buildable
immediately on the a8t side. **The two readings therefore do not merely re-scope P-14's cost; they
change whether it can be started at all.** Stated as scoping — **T7 is not picked here or anywhere
in this packet, and P-14 is not recommended under either reading.**

**Note the ordering dependency the table makes visible:** under reading (ii), **UV-P-5
must be answered before any build begins**, because the ported seam lands in a rail
whose account is unknown. This is the mechanical reason DP-2's `on_fail` reads *"S8 is
BLOCKED. Do not build a per-profile publisher against an unknown account topology."*
(`…shape.md:793`).

### 5.3 THIRD QUESTION — the shared contract: which terms are COMMON and which are CONTRACT-LOCAL?

**Six** candidate terms — the sixth added at architect-remediation-1 per CH-04. The packet
states each term's current evidence and asks the operator to sort it; it **does not sort them**.

| Term | Contente rail today | a8t / tenuta rail today | Current evidence of common-ness |
|---|---|---|---|
| **Header bytes** | `host_bundle.py:56` `HEADERS_FILE_CONTENT` — four rules under `/*`; enforced byte-identical at the root by `deploy_root_guard.py:142-158` | the **same four lines**, hand-written as a heredoc in `publish-tenuta.sh` (S5-P-4) | **Strongest COMMON candidate.** Two independent implementations already agree byte-for-byte, and both live surfaces serve them (G-36 for tenuta; the S1 nine-deck probe for Contente). The risk is that agreement is currently maintained by hand-copy, with no cross-check. |
| **Slug alphabet** | 32-hex, `secrets.token_hex(16)` — `host_bundle.py:68` `_SLUG_RE`, `:79-101` `mint_slug` (G-16, G-13) | 25-char base32 (G-33); deck-host's verifier enforces a third shape, 26-char base32 (G-12) | **CONTRACT-LOCAL — already ruled.** SG-1: *"slug shape is contract-local per publisher"*; unifying alphabets is **out of scope** (shape §7, DEFER-3). See §6. |
| **Parity receipt shape** | `verify_bundle_parity` / served-sha == frozen-sha, refuse on drift (`host_bundle.py:7-11`) | `SHIP-RECEIPT-advantage-rc.md` table form: channel, live URL, slug, frozen file, sha256, live verification, external requests, deployed-at | **Structurally similar, semantically UNSETTLED** — because *which artifact is the record* is itself open. See §7. |
| **Audience DEFAULT-DENY** | `constants.py:14-42` + the 2b attach-gate; *"absence of a manifest IS denial"* (G-18); `host_bundle.py:12-19` EGRESS-DENY-1, enforced at `host_bundle.py:141` inside `stage_deck_bundle` | **CORRECTED per SECURITY-REVIEW-S5 RC-1(a) — the previous text ("no audience classifier exists on the a8t side") was FALSE.** deck-host ships a **C-3-compliant deny law**: `src/audience/classify.js:41-49` applies `guard.evaluateAudience` over the **pinned producer map** `config/producer-audience-map.json` (provenance `autom8y-asana:…/deck_manifests`, `pinned_commit f3d8eec1…`), wired at `bin/verify.js:154` with `refuse(aud, 'audience')` at `:156`; **zero template→audience literals on the a8t side**. Enumerated by S3 at **INV-11** with three RED arms + a GREEN twin (`ws-guard-fence-invariants-enumeration-2026-09-05.md:279-297`). | **NOT the asymmetry this row previously asserted.** (1) **The cost of ruling DEFAULT-DENY COMMON is far LOWER than this row represented** — the a8t pattern already exists, and it is precisely the shape that reconciles **C-3** (*"egress MUST CONSUME the producer `assert_customer_deck` classification… MUST NOT mint a per-Pages orphan gate"*, `url-capability-contract-cloudflare-host-decks-2026-07-04.md:145-146`) with **G-29** (*code may not cross*): **the producer classification crosses as pinned DATA; no code crosses.** (2) **But as currently wired that gate is LEDGER-KEYED** — `bin/verify.js:193` iterates `manifest.activeEntries()`, and **so does S3's in-flight fence** (`src/fence/run.js:112` → `:217`) — so it has **no reach over a staged artifact with no ledger row**. **The pattern exists and is C-3-correct; its QUANTIFIER is the thing clause C8 (§12.1) changes.** Q3 remains the operator's to sort. |
| **Root 404** | root hygiene + capability-URL contract (G-19) | verified live: `HEAD https://tenuta-decks.pages.dev/` → **404** with the full guard header set (G-36); `publish-tenuta.sh` asserts it post-deploy (`echo "root must 404:"`, S5-P-4) | **Strong COMMON candidate.** Both rails already assert it and both live surfaces exhibit it. |
| **Revocability (CC-1)** — *added per CH-04* | a **three-part** revocation: ledger `status` flip → re-stage → re-deploy. The ledger carries `status` (S5-P-6; 9 `active` + 1 `revoked`), the superset predicate exempts `revoked` (`deploy_root_guard.py:162-172`), and the fence enumerates the negative control at **INV-12** (`src/fence/run.js:128`, `:292`). The revoked base32 slug `od67…` is **404, 0 bytes** on the live surface (S1 §3.2) | **NO LEDGER, THEREFORE NO REVOCATION PATH.** `publish-tenuta.sh` stages exactly one slug into a wiped `$DIST` (S5-P-4) — revoking means **re-deploying without the slug**, with no record that it ever existed and no negative control. There is nothing to flip | **THE ASYMMETRY IS REAL, AND WS-GUARD CALLS THIS ONE DECISIVE.** Ruling CC-1 COMMON obliges the a8t lane to grow a ledger — which is **P-0's C1 condition and P-5's C4 condition arriving by a third road**. Ruling it CONTRACT-LOCAL leaves a live client artifact with **no revocation primitive**. Found by the companion and security seats independently; **absent from this list until now, which sorted it CONTRACT-LOCAL by default** |

**The question put to the operator:** of `{header bytes, slug alphabet, parity receipt
shape, audience DEFAULT-DENY, root-404, **revocability (CC-1)**}`, which are **COMMON contract
terms** (both rails must satisfy them, and a conformance fixture on each side proves it), and which
are **CONTRACT-LOCAL** (each publisher's own business)? Slug alphabet is already ruled
contract-local (SG-1). **The other five are open** — and the sixth, revocability, is the one whose
absence from this list was itself a silent CONTRACT-LOCAL vote (CH-04).

---

## §6 — CONTRACT-CLAUSE-SLUG — SEQUENCED-BEHIND-S2-SG-1 → **FILLED (naming only)**

**Status change at the architect addendum leg.** This section was authored as a NAMED
PLACEHOLDER because S2 (`s2/ws-f-ch01-reconciliation`) was naming the three alphabets
**concurrently** with this packet. **The SG-1 naming has now LANDED, YES-QUALIFIED** per the
10x-dev potnia. The clause below is therefore **filled** — and filled with the **naming ONLY**.
Everything the placeholder deferred that is *not* naming stays deferred.

### 6.0 Addendum probe register (S5-R; minted here; read-only, no lever fired)

| id | Claim | Method | Receipt |
|---|---|---|---|
| **S5-R-1** | The SG-1 naming is on disk at `src/slug/shape.js:6-15`, carrying all three alphabets with their G-anchors and the contract-local rule. | file-read (`git show`) | `git -C deck-host show 828cea5:src/slug/shape.js \| sed -n '6,15p'` → *"THREE slug alphabets coexist across the a8 → a8t boundary. None is wrong and none is canonical for the others (SG-1)"* … *"Contente rail (RULED live)   32 lowercase hex   `secrets.token_hex(16)`   G-16 / G-13"* / *"a8t rail                     25-char base32     125-bit draw              G-33"* / *"deck-host legacy             26-char base32     `mintSlug()`, SUPERSEDED  G-12"* … *"Slug shape is CONTRACT-LOCAL PER PUBLISHER. This file does NOT unify the three alphabets — imposing one shape across the boundary is out of scope."* |
| **S5-R-2** | **The file is BRANCH-RESIDENT and UNMERGED.** It exists on `s2/ws-f-ch01-reconciliation` only; `main` does **not** contain it, and `828cea5` is **not** an ancestor of `main`. | bash-probe | `git rev-parse --short main` → `f9f0af2`. `git cat-file -e main:src/slug/shape.js` → `fatal: path 'src/slug/shape.js' exists on disk, but not in 'main'`, exit **128**. `git merge-base --is-ancestor 828cea5 main` → exit **1**. `git branch --contains 828cea5` → `* s2/ws-f-ch01-reconciliation` (that branch only). |

> **CITATION DISCIPLINE — binding for every downstream consumer.** The clause below is anchored
> to `src/slug/shape.js:6-15` **@ branch `s2/ws-f-ch01-reconciliation`, commit `828cea5`**.
> **It is BRANCH-RESIDENT and UNMERGED (S5-R-2).** It MUST NOT be cited as main-resident, as
> merged, or as `deck-host` canon. `main` is at `f9f0af2` and does not contain the file.

### 6.1 THE CLAUSE — naming only

> **CONTRACT-CLAUSE-SLUG (naming).** Three capability-slug alphabets coexist across the
> a8 → a8t boundary. **None is wrong and none is canonical for the others.**
>
> | rail | shape | anchor |
> |---|---|---|
> | **Contente rail** (RULED live) | **32 lowercase hex**, `secrets.token_hex(16)` | **G-16** (`host_bundle.py:68` `_SLUG_RE`, `:79-101` `mint_slug`) / **G-13** (CH-01) |
> | **a8t rail** | **25-char base32**, 125-bit draw | **G-33** (slug `nogqfo3pizvjhbdbxvvsvhdgt`) |
> | **deck-host legacy** | **26-char base32**, `mintSlug()` — **SUPERSEDED-DEAD** | **G-12** (`bin/verify.js:77`) / **G-13** |
>
> **Slug shape is CONTRACT-LOCAL PER PUBLISHER. The three alphabets are NOT unified**, and
> imposing one shape across the boundary is **out of scope** (**SG-1**; shape §7 out-of-scope:
> *"Naming the divergence is in scope; imposing one alphabet across the boundary is not"*;
> **DEFER-3**).
>
> *Anchor: `src/slug/shape.js:6-15` @ `s2/ws-f-ch01-reconciliation` `828cea5` — BRANCH-RESIDENT,
> UNMERGED (S5-R-1, S5-R-2).*

### 6.2 What this clause DOES NOT carry — stated so the boundary is not read by omission

The clause is **naming only**. It explicitly does **not** carry, imply, or depend on:

- **the S2 SEAM RULING** — how deck-host reconciles its verifier/mint to 32-hex, where the seam
  sits, and what it refuses. That is **S2's chartered work** (shape §7: the only permitted
  `verify.js` change ahead of F-PUBLISH), and it is **not** a DP-2 term.
- **RA-1** — an S2 output reserved to the **OPERATOR** (§0 "Operator-only"). Nothing here
  consumes it, restates it, or anticipates it.
- **any WS-GUARD semantic** — the capability-URL contract is **SEALED-CONDITIONAL** with C-1..C-5
  reserved to operator/PT-01 (**G-19**). This epoch *consumes* that contract; it does not arm it.
  The clause asserts a *shape vocabulary*, never an *enforcement*.
- **any entropy floor, opacity or identity-free assertion.** The N-1 property
  (`host_bundle.py:22-28`: *"never the guid, never the mailbox local-part, never the client
  name"*) and the Contente-128-bit / tenuta-125-bit entropy difference are **still open** as
  candidate COMMON terms and belong to **Q3** (§5.3), not to this clause.
- **`shape_P` in the acceptance predicate.** §12.1 C5 treats `shape_P` as a **parameter** and
  proves containment by *membership* (`d ∈ slugs(live(L_P))`), which is shape-agnostic and
  strictly stronger. **Nothing in this clause requires or implies DEFER-3's discharge**, and
  nothing in C5 requires this clause.

### 6.3 DEFER-WATCH ENTRY — **DRAFT** (frozen `defer-watch-manifest` grammar)

**DRAFT, not minted.** Per `hosted-deck-product-epoch-eunomia-handoff.md:363` — *"A
`defer-watch-manifest` entry should be minted **only** by the sprint that disposes it."* This
leg names the entry and does not open it.

```yaml
- id: DEFER-SG1-REANCHOR
  title: "Re-anchor CONTRACT-CLAUSE-SLUG once the S2 PR is merged or rejected"
  status: DRAFT              # NOT MINTED — minted by the sprint that disposes it
  rationale: >
    CONTRACT-CLAUSE-SLUG (§6.1) is anchored to src/slug/shape.js:6-15 @ branch
    s2/ws-f-ch01-reconciliation commit 828cea5. That anchor is BRANCH-RESIDENT and
    UNMERGED (S5-R-2: `git cat-file -e main:src/slug/shape.js` -> exit 128;
    `git merge-base --is-ancestor 828cea5 main` -> exit 1; main is f9f0af2). A
    branch anchor is not durable: the branch may be rebased, squashed, force-pushed
    or abandoned, and the SHA would then resolve to nothing. The clause TEXT is
    settled (SG-1, DEFER-3); only its CITATION is provisional.
  watch_trigger: "the OPERATOR merges or rejects the S2 PR (s2/ws-f-ch01-reconciliation)"
  escalation:
    on_merge: >
      re-anchor §6.1 to the main-merge SHA and path (git rev-parse the merge commit;
      re-derive the line range, which may move). The clause text does not change.
    on_reject: >
      RE-OPEN the clause. Its naming is corroborated independently by G-12/G-13/G-16/G-33
      and SG-1, so the NAMING survives a rejection; but the citation must fall back to
      those anchors and §6.1's shape.js reference must be struck, not silently retained.
    on_branch_rewrite: >
      if 828cea5 becomes unresolvable before either outcome, treat as on_reject and
      fall back to the G-anchors; never cite a SHA that does not resolve.
  owner: "S5 author (architect) — re-anchoring is editorial; the RULING is not reopened"
  blocks: "nothing. DP-2 may be ruled on every other term without waiting (see §6.4)."
```

### 6.4 The PARITY-RECEIPT half of the clause

The placeholder deferred the slug half. The **parity-receipt** half can be stated as fact now,
and its **unresolved** half named precisely. **What each publisher's receipt hashes against
TODAY:**

| publisher | the receipt's referent today | anchor |
|---|---|---|
| **Contente rail** | **deck-host's own ledger `frozen_sha256` == served bytes**, **9/9 MATCH** | `VERDICT-cloudflare-pages-host-decks-2026-09-05.md:368` — *"Served-vs-**deck-host-ledger** byte parity — **DERIVED** (9/9 MATCH) — labelled DISTINCT; does NOT satisfy arm-2"* |
| **a8t rail** | **the SHIP-RECEIPT's frozen-file sha256 == served bytes** — `080768a3…c918`, re-derived independently | **G-37** (`GET https://tenuta-decks.pages.dev/nogqfo3…/` → `status=200 bytes=63336`; `shasum -a256` identical to the SHIP-RECEIPT frozen sha) |

**Both rails already assert served == frozen. They do not agree on what "frozen" NAMES.** The
Contente rail's referent is a **ledger row**; the a8t rail's is a **file on disk at freeze
time**; and **A-arm-2's** referent — the **producer-frozen Asana attachment** — is a **third
artifact that demonstrably disagrees with the first** (§7: N=2 mismatch, `+1,711 B`,
`R1(b)` fix; Foundation has no attachment at all).

> **CONSEQUENCE — carried, not ruled.** A COMMON parity clause of the form *"served == frozen"*
> is **not writable** until "frozen" is named. **The record-of-truth question is routed to
> CANDIDATE DEFER-5** (§7.1), homed at the **ancestor PT-04 hash-parity remit**
> (`cloudflare-pages-host-decks.shape.md:251-253`). **It is NOT ruled here, and this leg does
> not mint its defer-watch entry either.** What *is* writable today, and is offered to **Q3**
> as the shape of a COMMON term, is the weaker, referent-explicit form: *"each publisher names
> its record artifact, and asserts served-bytes sha256 == that named record's sha256."*
> Naming which artifact is the record remains DEFER-5's.

**Sequencing, updated.** The clause is filled; the **CITATION** is provisional pending
DEFER-SG1-REANCHOR. **DP-2 may be ruled on every term in §5.3 without waiting for the S2 PR** —
the slug term is contract-local and settled (SG-1/DEFER-3), and the parity term is blocked on
DEFER-5, not on S2.

---

## §7 — A-arm-2 REFUTED: an INPUT CONSTRAINT on any parity clause

**This is an input to the packet, not a finding of it.** It is carried because §5.3
asks whether "parity receipt shape" is a shared contract term, and **the refutation
makes that question unanswerable without first naming the record.**

**The S1 finding** (`VERDICT-cloudflare-pages-host-decks-2026-09-05.md:172-283`;
carried at `hosted-deck-product-epoch-eunomia-handoff.md:193-240`):

A-arm-2 — *"served artifact HASH-MATCHES the producer-frozen Asana attachment"* — is
**REFUSED / REFUTED (derived FALSE)**. Fetched read-only via `ASANA_PAT` →
`/attachments/{gid}` → signed `download_url` → `shasum -a 256`:

| office | producer-frozen ASANA attachment sha256 | SERVED-BYTES sha256 | result |
|---|---|---|---|
| nation-of-wellness (att `1216264246897515`, 1 047 702 B) | `5250179a717f556726d4e64248b56f36922b1b35a0998590c0763c0e40deddbb` | `083cf351cc9eb59e8cd59dafd421fe800cb1282528a4c0382be1f4cf11741c22` | **MISMATCH** (+1 711 B served) |
| wholebody-systems (att `1216252578292835`, 1 047 701 B) | `2c5d3078f248ed1a4006fe6f942be14b6e6b80f95e5dbe307402df3ca611b572` | `839f6813c1627cefabd1e89ce4923347441f770c790dc8bd622c1305c1dcda9c` | **MISMATCH** |

**Foundation Spine & Posture has NO producer-frozen HTML attachment at all** — task
`1217867773183924`, `attachments=1, asana-hosted-HTML=0`, a Loom link only. For that
office A-arm-2 is not unmatched, it is **structurally unsatisfiable**.

**The divergence is characterized, not speculative.** The routing address is
**identical** in both copies; the difference is in the deck runtime JavaScript. The
**served** surface is **ahead** of the producer-frozen record by an `R1(b)` fix
(handoff §5(b) carries the verbatim diff hunk).

**N-bounding, carried exactly as H1 states it.** `hosted-deck-product-epoch-eunomia-handoff.md:230`:
*"N=2 of the 7 hashable attachments ⇒ **ILLUSTRATIVE, N-bounded.** Drift is present in
both offices hashed; 'systematic' is NOT asserted beyond N=2."* **Discrepancy noted
for the record:** the underlying VERDICT prose at
`VERDICT-cloudflare-pages-host-decks-2026-09-05.md:216` reads *"N=2 — the drift is
**systematic**, not a one-off."* The handoff's later, narrower framing is the one this
packet carries; the stronger word in the VERDICT is flagged, not adopted.

**The NAMED SUBSTITUTION TRAP, not taken here either.** deck-host's own
`config/deck-manifest.json` `frozen_sha256` matches served bytes **9/9**
(`VERDICT…:273-274`, `:368`). That is parity against **deck-host's own ledger** and
**does NOT satisfy A-arm-2**, whose referent is the producer-frozen Asana attachment.
This packet records it as a distinct, clearly-labelled observation and does not
substitute it.

### 7.1 The binding consequence for any contract clause

> **Any clause asserting byte-parity as a shared contract term MUST name WHICH
> ARTIFACT IS THE RECORD.** There are three candidates and they demonstrably disagree:
>
> 1. **deck-host's ledger `frozen_sha256`** — matches served **9/9**;
> 2. **the Asana attachment** — mismatches served, **N=2 of 7 hashable**, and is
>    **absent entirely** for the most recent mint (foundation, 2026-08-27);
> 3. **the producer's frozen file at freeze time** — the artifact
>    `host_bundle.py:7-11` actually means by *"the host MOVES bytes, it never
>    re-renders"*, and the one no probe in this epoch has yet hashed directly.
>
> A parity clause that says "served == frozen" without naming which of these is
> "frozen" is **already falsified by the evidence on record**. Two of the three cannot
> both be the record.

**ROUTING — not ruled here.** The record-of-truth question is **not S5's to answer**
and not DP-2's to rule. It belongs to the **ancestor PT-04 hash-parity remit**
(`cloudflare-pages-host-decks.shape.md:251-253`, cited as arm-2's declared home at
`hosted-deck-product-epoch-eunomia-handoff.md:117`). Raised here as:

**CANDIDATE DEFER-5 — "record-of-truth for byte-parity".**
*Which artifact is the parity record: the deck-host ledger `frozen_sha256`, the Asana
attachment, or the producer-frozen file?* **Route: ancestor PT-04 hash-parity remit.**
**Status: CANDIDATE.** Per `hosted-deck-product-epoch-eunomia-handoff.md:363` — *"A
`defer-watch-manifest` entry should be minted **only** by the sprint that disposes
it."* — this packet **names the candidate and does not mint the entry.**

**Adjacent, deliberately not merged:** handoff §5(b) already routes the `R1(b)`
divergence itself as a **candidate DEFER to the producer lane (DW-7 lineage)**, homed
at **S3**, explicitly *"NOT RULED HERE"* and explicitly not asserted to *be* the DW-7
fix. DEFER-5 is the **record-of-truth** question, which is distinct from and upstream
of the `R1(b)` disposition. Keeping them separate is deliberate.

---

## §8 — DK-004: a CONTRACT CANDIDATE ONLY, never scheduled

**DK-004 is a SKETCH.** `deck-kit/bin/publish.mjs` **does-not-exist** — re-probed at
S5 entry and still absent (S5-P-9; G-30). Its acceptance criteria are cited here as
**candidate contract clauses**, not adopted as code, and **nothing about DK-004 is
scheduled by this packet** (shape §7 out-of-scope: *"Scheduling any DK-001..DK-005 item
as an epoch sprint. Cross-reference ids; consume outputs as contracts (G-39)."*).

**Verbatim summary** (`HANDOFF-strategy-to-10x-dev-2026-09-04.md`, DK-004,
`priority: medium`):

> *"A publish lever: `bin/publish.mjs` that stages one frozen deck (slug + `_headers`)
> into a named Cloudflare Pages project under a pinned account id, refuses if wrangler
> cannot list that project, deploys, verifies served bytes == frozen sha256 and the
> noindex/no-store/no-referrer headers plus a 404 root, and writes a ship receipt;
> generalizing the engagement's `publish-tenuta.sh`."*

**Acceptance criteria, verbatim:**

> - *"Dry-run mode prints every step without network; live mode requires an explicit
>   `--confirm` and never uploads more than the one slug."*
> - *"Account and project are parameters with no default that points at another
>   organisation's project."*

**As candidate contract clauses, mapped to the slate:**

| Candidate clause | Slate option it belongs to | Live precedent |
|---|---|---|
| **pinned account id** | P-6 (declared tuple field), P-10 (account-as-boundary) | `publish-tenuta.sh`: `export CLOUDFLARE_ACCOUNT_ID="${…:-974c47a3…}"` (S5-P-4) |
| **one slug only / never uploads more than the one slug** | P-5, P-2 — and note this is the **inverse** of the Contente rail's accumulating-SUPERSET model (frame §9.6 table) | `publish-tenuta.sh` step [2/5] **wipes and re-creates** its `$DIST` before staging, then copies exactly one deck to `$DIST/$SLUG/index.html`; the staged dir was observed holding exactly `_headers` + one slug dir (S5-P-4) |
| **refuse if wrangler cannot list the project** | **P-13** — this clause *is* P-13 | both scripts implement it: exit 5 on each side (S5-P-4, S5-P-5) |
| **served == frozen sha + guard headers + 404 root** | §5.3 rows *parity receipt shape*, *header bytes*, *root-404*. **Blocked on §7** — "frozen" is not yet named. | `publish-tenuta.sh` step [5/5]; G-36/G-37 |
| **ship receipt** | §5.3 *parity receipt shape* | `SHIP-RECEIPT-advantage-rc.md` table form |
| **no default pointing at another organisation's project** | the direct counterweight to `DECK_HOST_PAGES_PROJECT = "deck-host"` as a **default** (G-6, `office_runner.py:152`) | — |

**One structural observation worth the operator's attention.** DK-004's "one slug
only" and G-7's "accumulating SUPERSET" are **opposite failure-mode defenses**, exactly
as the frame's §9.6 table records: the Contente root prevents *silent-404 orphaning of
live client decks*; the tenuta lane prevents *uploading more than the one slug*. The
tenuta lane's wipe-then-stage step is safe **only because its root holds exactly one
deck** — applied to an accumulating root it would be a mass-orphan event. A contract
term that tried to be both defenses would be incoherent. **Any COMMON parity clause
must therefore be written at the level of "served bytes == the named record" and leave
root-model contract-local** — the same shape of answer SG-1 already reached for slug
alphabet.

**Also never scheduled** (shape §7 out-of-scope): the `tenuta-decks` project's creation
and its first deploy. Both are **operator-done facts** (G-33, G-35) and appear in this
packet only as receipts.

**Not absorbed** (SG-2): the `advantage-rc-engagement` telos. Its legs 2–3 are
UNATTESTED with deadline **2026-10-16**, a different initiative in a different repo
under the strategy rite. Cross-reference only.

---

## §9 — CARRIED FORWARD

### 9.1 UV-P register at S5 exit

| id | Status at S5 exit | Basis |
|---|---|---|
| **UV-P-1** (DW-7 closure) | **OPEN — untouched by S5.** Home S3; hard gate on any send-bearing action. | `…shape.md:1455`; S5 neither probed nor disposed it |
| **UV-P-4** (`publish-tenuta.sh` + `scratchpad/` tree) | **DISCHARGED (script half) by S5-P-4**, consumed per SVR §1 RULE-1. **Tree half: ephemeral by construction** (S5-P-3) — not a durable substrate; recorded as a finding rather than a gap. | S5-P-3, S5-P-4 |
| **UV-P-5** (account ownership of `deck-host` + `decks.cntently.com`) | **OPEN — NARROWED.** Candidate id `a245df42893c85a8d96c71cfa46eec76` is a file-read of a claim (S5-P-5), unverifiable from this machine (S5-P-2). Zone unprobed. **DP-2's FIRST question.** Re-labelled at §0.3. | S5-P-2, S5-P-5, G-35 |
| **UV-P-6** (tenuta staging root + deploy command) | **DISCHARGED-WITH-A-FINDING** — both halves receipted; the finding is non-reproducibility (§0.3). | S5-P-3, S5-P-4, `RESUME-AFTER-RESTART.md:32` |
| **CANDIDATE DEFER-5** (record-of-truth for byte-parity) | **NAMED, NOT MINTED.** Routed to the ancestor PT-04 hash-parity remit. | §7.1 |
| **UV-P-7** (P-14 serve-time router runtime behaviour) — *registered per D2-R6* | **OPEN — MINTED at architect-remediation-1.** A Pages Function deployed via direct-upload actually 404-ing a slug on a non-owner host while its owner host returns 200. **The TOOLCHAIN half is receipted (S5-R-3); the DEPLOYED-PREDICATE half is not.** METHOD requires a **custom-domain attach + a deploy** — both **operator-reserved levers** — against a project this machine's credential cannot reach (G-35, S5-P-2). Label in frozen syntax at **§4 P-14**. | §4 P-14; S5-R-3, S5-R-4, G-35 |
| **UV-P-8** (`--config`-supplied `account_id` honoured by `pages deploy`) — *registered per D2-R6* | **OPEN — adopted verbatim from the arch-adversary** (`ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md` §3.2). The `--config` **flag** and the `account_id` **resolution** are each receipted separately; their **COMPOSITION on the `pages deploy` path is not**. Discharged read-only by `wrangler pages project list --config <tmp.toml carrying account_id>` under the owning credential. Label at **§4 P-6** (sub-form) and referenced at **§0 constraint 4**. | §4 P-6; §0 c4; S5-E-3 |

**Both new labels were minted by the CH-01/CH-02 remediation and were unregistered until
architect-staging-1** — which is exactly the condition Gate C cannot see (DELTA-2 N-2). Registering
them here does **not** discharge them; it makes them ride.

**Gate C** (`…shape.md:1462-1464`): every UV-P still open at a cross-rite handoff rides
that handoff under the DEFER-tag pattern with a `defer-watch-manifest` entry. **UV-P-1, UV-P-5,
UV-P-7 and UV-P-8 ride.** S10 will not attest over an unrecorded UV-P.

### 9.2 The three ownership facts, carried

1. **The `deck-host` repo remote is a PERSONAL account** — `git remote -v` →
   `git@github.com:tomtenuta/deck-host.git (fetch/push)` (**G-17**).
2. **The `deck-host` Pages project is in an account the operator's login cannot
   reach** — `wrangler pages project list` under `974c47a3…` returns exactly one row,
   `tenuta-decks`; `deck-host` is absent (**G-35**, re-derived at S5-P-2).
3. **`tenuta-decks` is in the operator's personal account** — account
   `974c47a3be9b85d1b4986b85c1c3ede3`, `tom@tenuta.io` (**G-33**, **G-35**; re-derived
   at S5-P-1, S5-P-2).

**Together:** the repo, the Contente serving account, and the tenuta serving account
are **three different ownership domains**, and no credential on this machine spans
them. That is the substrate every F-PUBLISH option is built on.

### 9.3 Freshness note on G-30

**G-30's load-bearing half HOLDS** (`bin/publish.mjs` does-not-exist, S5-P-9), but its
**file inventory has drifted**: `deck-kit/bin/` now also contains `check-render.mjs`
(DK-001 landed at branch `feat/dk-001-dk-005-render-check-and-negative-fixtures` @
`d8c7794`; `main` remains at `bfc2f41`). Recorded so a downstream consumer does not
read the drift as a contradiction of G-30.

---

## §10 — WHAT THIS PACKET DID NOT DO

Recorded explicitly so the absences are read as discipline, not as gaps.

- **Did NOT answer F-PUBLISH.** The slate is enumerated; no option is recommended,
  ranked or preferred. DP-2 is an **operator** decision (`…shape.md:777`,
  `owner: OPERATOR`).
- **Did NOT rule T7.** Both readings are carried verbatim (§5.2). T7's home is PT-05
  and it is operator-sovereign.
- **Did NOT issue final NON-VIABLE marks on R1 / G-7 grounds.** All G-7 marks read
  PROVISIONAL. The acceptance predicate — no-orphan restated for N roots as a testable
  predicate — is **requirements-analyst's** next artifact (`…shape.md:426`).
- **Did NOT re-litigate Option B** (G-20). F-PUBLISH asks whether a **second**
  publisher exists for a non-Contente profile — not whether Contente's rail should
  change shape. Option B is cited as settled substrate throughout.
- **Did NOT weaken any WS-GUARD invariant.** Where an option would touch one (P-7's
  `DECK_HOST` egress predicate; P-3's fail-closed superset semantics; P-9's
  containment), the packet **flags it for the security critic** rather than proposing
  the weakening.
- **Did NOT unify the slug alphabets.** §6 is a named visible-deferred placeholder
  sequenced behind S2's SG-1 output.
- **Did NOT schedule** any DK-001..DK-005 item, nor `tenuta-decks` creation or its
  first deploy (operator-done facts, G-33/G-35).
- **Did NOT run any reserved lever.** No `wrangler` write, no `pages project create`,
  no deploy, no DNS, no slug mint, no SEND. Every wrangler invocation in §0 was
  read-only (`whoami`, `pages project list`).
- **Did NOT change code anywhere**, in any repo.
- **Did NOT write outside its two permitted paths.** This artifact is the only file
  written in any a8 repo.
- **Did NOT touch S2's files or git state.** S2 holds `deck-host` at branch
  `s2/ws-f-ch01-reconciliation`; every deck-host read in this packet was read-only and
  no stash, checkout, reset or write was performed there.
- **Did NOT absorb the advantage-rc-engagement telos** (SG-2). Cross-reference only.
- **Did NOT ship this packet.** Potnia stages it; **PT-03 gates it**.

---

## §11 — SELF-ASSESSMENT

**Evidence grade: MODERATE (ceiling, not floor).** Per `self-ref-evidence-grade-rule`,
an artifact authored inside 10x-dev about 10x-dev's own design surface caps at
MODERATE. **Nothing here is self-attested as realized.** RUNG = **authored**; this
packet advances no leg of the telos. Only the rite-disjoint attestation at S10 may
reach STRONG, and only on LEG-1/LEG-2 (`…shape.md` §7 Prescribed).

**What is STRONG-grade underneath this packet, and is not mine:** the live-surface
receipts (G-33, G-36, G-37, G-38, G-38b) and the S1 eunomia VERDICTs. I re-derived
two of them by my own hands (S5-P-1, S5-P-2) as corroboration, which is *additional
hands, not rite-disjoint attestation* — the frame makes exactly that distinction at
§9.8 and it applies to me.

**Where this packet is weakest, stated plainly:**

1. **UV-P-5 is still open**, and it is the FIRST question. Every option's evaluation
   is conditional on an answer I could not obtain (S5-P-2). The candidate id at
   S5-P-5 is a comment in an ephemeral script — I did not promote it and the operator
   should not read it as an answer.
2. **The G-7 exposure marks are PROVISIONAL by construction.** I state exposure; I do
   not close it. If the requirements-analyst's acceptance predicate finds a
   silent-404 path I did not name, the slate's exposure column is wrong, not merely
   incomplete.
3. **Composability (§4.1) means the slate is larger than 14.** I enumerated
   mechanisms and modifiers; I did not evaluate every mechanism×modifier pairing at
   equal depth. `option-enumeration-discipline` §6 asks for evaluation-depth symmetry
   and I met it **per option**, not per combination.
4. **N=2 on the drift, and N=2 on the profile classification.** §7 carries the
   handoff's bounding verbatim rather than the VERDICT's stronger word. §3.3's
   rot-triggers exist precisely because two live instances cannot distinguish an
   ontology from a packaging accident.

**Rite-disjoint critic for this artifact** (`…shape.md:464`): **security**
(security-reviewer, co-seated) — *"does any option create a leak-by-containment path
or weaken audience DEFAULT-DENY at egress?"* The three options I have flagged for that
review, in priority order: **P-9** (one project behind N domains deletes the verified
two-sided isolation of G-36), **P-7** (widening the `DECK_HOST` egress predicate at
`contact_synthesis.py:305-313`), **P-3** (the `null`-profile hazard against a
fail-closed predicate).

**Anti-pattern self-check** (architect register):

| Anti-pattern | Check |
|---|---|
| First Solution Syndrome | **14** viable options + 1 refused class (P-11, excluded as prescribed); no recommendation issued. **Count updated at architect-staging-1 (D2-R7)** — P-14 was added at architect-remediation-1 and the tally had not followed it |
| Strawman Options | P-11 carries its own honest case-for before the prescribed refusal; P-9 and P-1 are enumerated with their real advantages, not as foils; dissent authored at equal depth to the case-for throughout |
| Handwavy NFRs | the operative predicate (G-7 no-orphan) is quoted from source, not paraphrased; where a predicate is not yet testable, it is routed to requirements-analyst rather than asserted |
| Missing ADRs | this **is** the decision artifact; it stages a door rather than embedding a decision in prose |
| One-Way Doors Without Signoff | DP-2 is declared one-way at `…shape.md:779` (`type: one-way-door`); `owner: OPERATOR`; `gate: hard`; `on_fail` carried verbatim at §5.2 |

---

**END — DP-2 packet.** Staged for the operator. Gated at PT-03. Not shipped by this
artifact.

---

## §12 — Acceptance predicate for N roots + viability marks (requirements-analyst, leg 2)

**Leg 2 of S5's DESIGN half.** The architect ENUMERATED and left every G-7 mark
`PROVISIONAL` (§3.2, §10). This section **GRADES that slate against a testable
acceptance predicate** and issues the FINAL viability marks. It does **not**
re-enumerate the slate, does **not** answer F-PUBLISH, does **not** rule T7, and does
**not** ship the packet (`status: proposed`; PT-03 gates).

**Evidence discipline (inherited, extended).** Every platform-behavior sentence
carries a **G-NN** frame anchor, an **S5-P-NN** receipt from §0.2, an **S5-Q-NN**
receipt minted in §12.0 below, or a **UV-P** label in the frozen
`structural-verification-receipt` syntax. S5-Q ids are **S5-local receipts, not frame
anchors** — same standing as the architect's S5-P register, same precedent
(`…shape.md:1390-1397` mints `SG-1`/`SG-2`/`SV-1`). A claim carrying a direct-inspection
receipt takes the receipt, **not** a UV-P label: UV-P is the frozen syntax for
*deferred* verification (SVR §1), and labelling a receipted claim UV-P would be a
false deferral. Self-assessment caps **MODERATE**.

### 12.0 S5-Q probe register (minted here; read-only; no lever fired)

| id | Claim | Method | Receipt (verbatim) |
|---|---|---|---|
| **S5-Q-1** | **The full gate PASSES a root holding a well-shaped slug dir that is ABSENT from the ledger.** The negative twin does **not** bite today. | bash-probe (real `assert_deploy_root_ready`, tmp fixture, `.venv/bin/python`) | root = `{aaaa…(32) , ffff…(32)}`, ledger = `{aaaa…(32): active}` → `{"deploy_root": "…/tmp…/deck-host/public", "event": "floodgates_deploy_root_ready", "level": "info"}` and **no raise**. The wrangler command WOULD be surfaced. |
| **S5-Q-2** | **The no-orphan predicate bites two-sided at N=1.** | bash-probe (same harness) | GREEN root=`{A}` ledger=`{A}` → `floodgates_deploy_root_ready`, no raise. RED root=`{A}` ledger=`{A,B}` → `DeployRootRefused`: *"no-orphan REFUSED: ledger slug(s) ['bbbb…'] (status != revoked) absent from deploy root … — deploying would 404 LIVE client deck(s)"*, `reason: manifest_orphans`. |
| **S5-Q-3** | **deck-host's live workspace satisfies BOTH containment directions today.** `dirs(public/)` and the ledger's non-revoked slug set are **set-equal**, 9 = 9. | bash-probe | `node -e` over `config/deck-manifest.json` + `public/` → `live-ledger-slugs n=9`; `public dirs n=9`; `SET EQUAL: true`; `dirs NOT in live ledger: []`; `live ledger NOT in dirs: []`; `all slug dirs hold exactly index.html: true`; `_headers bytes=128`. |
| **S5-Q-4** | **`public/_headers` is byte-identical to `host_bundle.HEADERS_FILE_CONTENT`** — 128 bytes both sides. Corroborates the cross-repo term **G-16** (`host_bundle.py:56` — the publisher owns the `_headers` bytes) and its enforcement at `deploy_root_guard.py:142-158`, by a second pair of hands. | bash-probe | `host_bundle HEADERS_FILE_CONTENT bytes: 128` / `deck-host public/_headers bytes: 128` / `BYTE-IDENTICAL: True`. |
| **S5-Q-5** | **Shape census over all 10 ledger rows**: 9 × 32-hex `active`, 1 × 26-char base32 `revoked` (`od67utt5a5gdbidn6b5dszjjoi`). The revoked row is the **only** row matching `main`'s verifier shape `/^[a-z2-7]{26}$/`. Corroborates G-1, G-13. | bash-probe | per-row table: `26 b32-26:Y hex-32:n status=revoked od67utt5a5gdbidn6b5dszjjoi`; nine rows `32 b32-26:n hex-32:Y status=active`. |
| **S5-Q-6** | **G-12 FRESHNESS — HOLDS on `main`, SUPERSEDED on the S2 branch.** `main:bin/verify.js:77` is `const structuralOk = /^[a-z2-7]{26}$/.test(slug);`. On `s2/ws-f-ch01-reconciliation` @ `cbcd180` it is `const structuralOk = SLUG_RE.test(slug);` with `src/slug/shape.js:31` `const SLUG_RE = /^[0-9a-f]{32}$/` (file **absent on `main`**). **S2's chartered CH-01 work, in flight, not merged.** Recorded, not ruled, not touched. | git-show + file-read | `git show main:bin/verify.js \| sed -n '75,79p'` → the base32 line; `sed -n '110,114p' bin/verify.js` → the `SLUG_RE` line; `git cat-file -e main:src/slug/shape.js` → `fatal: path 'src/slug/shape.js' exists on disk, but not in 'main'`. |
| **S5-Q-7** | **Revocation is TWO-STEP, and the deploy gate enforces only the exemption half.** A `status` flip alone does not 404 a live URL; deck-host serves a static snapshot with **no** Pages Function. | file-read + bash-probe | `bin/mint-slug.js:66` — *"revoked slug ${slug} (status=revoked). **Re-stage + re-deploy to 404 the old URL.**"*; `src/slug/manifest.js:81` resolve() *"null for unknown/revoked (fail-closed)"* — a **tooling**-layer predicate; `wrangler.toml` → `pages_build_output_dir = "public"`, no build command; `functions/`, `public/_worker.js`, `public/_routes.json` → **all absent**. |
| **S5-Q-8** | **`deck_file` type census**: 8 of 10 rows GID-shaped (`\d+\.html`); **2 of 10 rows** carry a bare filename — **both** `sand-lake-dental` rows (the `revoked` od67 and the `active` `207688021de8…`). Sharpens H1 §5(a)'s *"One entry"*: one **office**, two **rows**. | bash-probe | `BARE-FILE revoked sand-lake-dental walkthrough-gmail-forwarding-setup-sand-lake-dental.html` / `BARE-FILE active sand-lake-dental walkthrough-gmail-forwarding-setup-sand-lake-dental.html`; eight `GID-SHAPED active` rows. |

**No `wrangler` write, no project create, no deploy, no DNS, no mint, no SEND.** The
S5-Q-1/S5-Q-2 probes ran the **existing** guard against **temporary fixtures** under
`tempfile.TemporaryDirectory()`; **no code was changed in any repo** and **nothing was
written into `deck-host`'s working tree** (branch `s2/ws-f-ch01-reconciliation`, read-only
throughout — no stash, checkout, reset or write).

---

### 12.1 THE ACCEPTANCE PREDICATE — no-orphan restated for N roots

The G-7 predicate as written is **N=1**: one root, one ledger, one direction of
containment (`deploy_root_guard.py:162` `assert_manifest_superset`, composed at `:246`
`assert_deploy_root_ready` behind `assert_root_hygiene` and `assert_headers_parity`).
Restated for N publishers it is **seven clauses**, of which **three do not exist today
in any form** (C2, C3, C7) and **one exists in a weaker shape-based form** (C5).

> **GIVEN** a finite publisher set `𝑷 = {P₁ … P_N}`, `N ≥ 1`, where each publisher `P`
> declares a **triple** `⟨L_P, R_P, H_P⟩` — a ledger, a staged deploy root, and the set
> of hostnames its Pages project serves —
> **AND** the deploy of `P` publishes `R_P` as a **whole-tree immutable snapshot** that
> becomes the **only** thing every `h ∈ H_P` serves (`deploy_root_guard.py:2-5`: *"Cloudflare
> Pages custom domains serve the LATEST deployment only, and `wrangler pages deploy <root>`
> publishes the WHOLE tree as an immutable snapshot"*),
>
> **WHEN** a `wrangler pages deploy` command for any `P ∈ 𝑷` is about to be **SURFACED**,
>
> **THEN** the command is surfaced **if and only if all seven clauses hold**; on any
> refusal **NO command is surfaced for any publisher** (`batch.py:249-253` clears every
> `wrangler_command`), and the refusal names the failing clause and the failing slug.
>
> ```
> notation:  live(L)  = { e ∈ entries(L) : e.status ≠ "revoked" }
>            slugs(S) = { e.slug : e ∈ S }
>            dirs(R)  = { immediate child names of R }
>            scope(P) = the set of ledger entries the deploy of P is required to carry
>
> C1 LEGIBILITY — fail-closed
>    ∀ P ∈ 𝑷 : readable(L_P) ∧ decks(L_P) is an object ∧ ∀ e ∈ entries(L_P): e is an object.
>    ¬readable(L_P) ⇒ REFUSE.  Absence of a ledger is NOT permission.
>
> C2 BINDING — non-vacuity of C4
>    ∀ P ∈ 𝑷 : bind(R_P) = L_P  ∧  bind(L_P) = R_P.
>    The ⟨root, ledger⟩ pair is ATOMIC and MUTUALLY declared. An unpaired, cross-paired,
>    or independently-overridden pair ⇒ REFUSE.
>
> C3 PARTITION — totality ∧ uniqueness
>    ∀ e ∈ ⋃_{P∈𝑷} live(L_P) : | { P ∈ 𝑷 : e ∈ scope(P) } | = 1.
>    ZERO  ⇒ REFUSE  (the silent-404 clause: a live entry no root is required to carry).
>    TWO+  ⇒ REFUSE  (the ambiguity clause: a live entry two roots claim).
>
> C4 NO-ORPHAN — superset, per root  [G-7 verbatim, instantiated N times]
>    ∀ P ∈ 𝑷, ∀ e ∈ live(L_P) :
>        e.slug ∈ dirs(R_P) ∧ isfile(R_P/e.slug/index.html)
>        ∧ ¬islink(R_P/e.slug) ∧ ¬islink(R_P/e.slug/index.html).
>    status == "revoked" is the ONLY exemption; every other status is treated as LIVE.
>
> C5 HYGIENE — converse containment, per root
>    ∀ P ∈ 𝑷, ∀ d ∈ entries(R_P) :
>        d = "_headers" ∧ isfile(d)
>      ∨ ( isdir(d) ∧ ¬islink(d) ∧ shape_P(d) ∧ contents(d) = ["index.html"]
>          ∧ ¬islink(d/index.html) ∧ d ∈ slugs(live(L_P)) ).
>    A directory in R_P that is not a LIVE slug of L_P is a STRAY and REFUSES —
>    including a well-shaped directory belonging to another publisher, and including a
>    REVOKED slug of this publisher.
>
> C6 HEADERS PARITY
>    ∀ P ∈ 𝑷 : bytes(R_P/"_headers") == HEADERS_FILE_CONTENT, byte-for-byte.
>
> C7 CONTAINMENT — two-sided, at the live surface  [G-36 generalized]
>    ∀ P ≠ P′ ∈ 𝑷, ∀ e ∈ live(L_P), ∀ h ∈ H_{P′} :  GET https://h/{e.slug}/ → 404
>    AND ∃ h ∈ H_P :                                  GET https://h/{e.slug}/ → 200.
>    One-sided evidence does NOT satisfy C7 (shape §7 Emergent floor, :1224-1225 —
>    "evidence quality may never REGRESS below what is already on record").
>
> C8 AUDIENCE-EGRESS DEFAULT-DENY — per publisher, per staged artifact
>    [ADDED per SECURITY-REVIEW-S5 RC-1(b); EGRESS-DENY-1 / WS-GUARD C-3 / G-18]
>    ∀ P ∈ 𝑷, ∀ d ∈ dirs(R_P) \ {"_headers"} :
>        ∃ e : e ∈ entries(L_P) ∧ e.slug = d
>        ∧ audience_source_P(e.deck_template) = "customer".
>    The classification MUST be CONSUMED from a producer-pinned source, never minted
>    locally (WS-GUARD C-3, :145-146). Absence, unreadability, or an unmapped template
>    ⇒ REFUSE (":92-93" — absence of a valid customer manifest IS denial).
>    Quantified over dirs(R_P), NOT over entries(L_P): a staged artifact with no ledger
>    row must REFUSE, not be skipped. (C8 subsumes nothing in C5; C5 is membership,
>    C8 is classification, and today NEITHER is implemented.)
> ```

**Why C8 quantifies over the ROOT, not over the LEDGER — the load-bearing choice.** The
security review found that **the F-3 converse-containment gap is ALSO an audience-gate
gap: they are one hole seen from two angles.** An un-ledgered directory has no `entry`,
hence no `deck_template`, hence **no audience verdict at all** — it is invisible to the
superset predicate *and* to the classifier, **on both rails**. On the a8 side the deploy
gate has zero audience awareness (SR-P-3: `deploy_root_guard.py` contains no occurrence of
`deck_manifests`, `assert_customer_deck`, `audience` or `deck_template`), and
`assert_customer_deck` fires on exactly **one** write path — inside `stage_deck_bundle`
(`host_bundle.py:141`; SR-P-4). On the a8t side the deny law exists and is C-3-correct, but
`verifyLocal` iterates `manifest.activeEntries()` (`bin/verify.js:193`) and looks **up**
each slug's staged file (`:83`) — there is **no** `readdir(public/)` anywhere in the
verifier (SR-P-6). **S3's in-flight fence closes the containment half and not this one:**
`src/fence/evaluators.js:98` genuinely walks the root with both converse arms, but
`src/fence/run.js:112` keys INV-11 on `manifest.activeEntries()` and `:217` calls
`classify.classify(entry.deck_template, …)` **inside that loop** (SR-P-14 — which cites
`:215`; re-probed here, the call is at **`:217`**, and the two-line drift changes nothing
about the finding) — so a foreign
dir the converse arm correctly flags as a *hygiene* violation is **never classified**.
**The converse-containment quantifier and the audience quantifier are different, and only
the first is being closed anywhere in the fleet today.** Had C8 been written over
`entries(L_P)` it would have reproduced exactly the gap it exists to close. *(Recorded per
SECURITY-REVIEW-S5 RC-1(b); the in-flight fence is recorded as IN FLIGHT — untracked and
uncommitted — and is NOT credited as landed.)*

**Fixture F-8, in §12.3's form — four arms.** **RED-a:** a staged dir whose entry's
`deck_template` classifies `internal` (`ghl-calendar-setup` in the pinned map) → **REFUSED
naming C8**. **RED-b:** a template **absent** from the pinned map — the default-deny arm,
*"the one that most often silently passes in naive implementations"* (S3 INV-11) →
**REFUSED naming C8**. **RED-c:** an unreadable/empty classification source → **REFUSED
fail-closed**. **GREEN twin:** the customer-classified template (`email-forwarding-setup`)
→ **surfaced**. All three RED arms are **fixture-only by construction**, since injecting a
non-customer template into the live ledger would be a production mutation (S3 INV-11's own
constraint). **F-8 cannot be satisfied by either rail's current wiring** — which is the
point of stating it.

**Four properties of this statement that are load-bearing:**

1. **It never says "profile" and never says "account."** The quantifier ranges over
   `⟨L, R, H⟩` triples. This is the direct answer to §3.3's classification-rot worry:
   rot-triggers **R-1** (a second project inside one account), **R-2** (a second custom
   domain), **R-3** (brand X published under account Y) and **R-5** (`decks.tenuta.io`
   attached) **do not falsify any clause**, because none of them changes the shape of a
   ⟨ledger, root, hostset⟩ triple. Two projects in one account are simply two publishers;
   a second custom domain is simply a larger `H_P`. **R-4** (two publishers agreeing on
   one alphabet) is the only trigger with predicate consequence, and it lands on C5 —
   see §12.2 (5).
2. **`shape_P` is a parameter, not a constant.** Slug shape is contract-local per
   publisher (SG-1, DEFER-3, shape §7 out-of-scope). The **membership** test
   `d ∈ slugs(live(L_P))` is shape-agnostic and strictly stronger, so C5 achieves
   containment **without unifying alphabets**. Nothing in this predicate requires or
   implies DEFER-3's discharge.
3. **C5 quantifies over `live(L_P)`, not `slugs(L_P)`.** A revoked-but-still-staged slug
   dir therefore REFUSES. This UPGRADES revocation from a two-step operator convention
   (S5-Q-7: *"Re-stage + re-deploy to 404 the old URL"*) into a **gate-enforced**
   property. It is satisfied by the live workspace as it stands today (S5-Q-3, S5-Q-5:
   od67 is `revoked` and absent from `public/`).
4. **C3 is the clause the N=1 statement has no room for.** With one publisher, "every
   live entry is in exactly one scope" is a tautology. With N publishers it is the
   entire silent-404 surface, and it is where P-3 lives or dies.

---

### 12.2 Clause provenance — what exists today, and what does not

| Clause | Exists today? | Anchor / gap |
|---|---|---|
| **C1** | **YES, verbatim** | `deploy_root_guard.py:162-190` — *"A missing or unreadable ledger REFUSES — absence of the ledger is not permission"* (G-7). Fixture: `test_absent_manifest_refused_fail_closed`, `test_unreadable_manifest_refused_fail_closed`, `test_manifest_without_decks_object_refused`. |
| **C2** | **NO — and the default is the hazard** | `deploy_root_guard.py:67-74` `default_manifest_path()` DERIVES the ledger from the root (`<root>/../config/deck-manifest.json`), which at N=1 is a convenience. `batch.py:345` `--deck-manifest` can override it **independently** of `batch.py:335` `--deploy-base`. Nothing anywhere requires the pair to declare each other. `test_explicit_manifest_path_overrides_default` is the fixture that shows an arbitrary ledger may be paired with an arbitrary root and PASS. |
| **C3** | **NO — inexpressible** | The ledger has **no** account/project/domain/profile dimension (S5-P-6, re-derived S5-Q-5/S5-Q-8: entry fields are exactly `deck_file, office, deck_template, frozen_sha256, minted_at, status`). There is no field over which `scope(P)` could be computed, so at N≥2 `scope` must be minted before C3 can be evaluated at all. |
| **C4** | **YES, verbatim (this IS G-7)** | `deploy_root_guard.py:162` `assert_manifest_superset`. Two-sided at N=1, re-proven by my own hands at **S5-Q-2**. `test_unknown_status_treated_as_live_fail_closed` proves the fail-closed direction; `test_revoked_slug_missing_is_exempt` proves the exemption. |
| **C5** | **PARTIAL — shape-based, not membership-based** | `assert_root_hygiene` (`:76-140`) allowlists `_headers` + non-symlink dirs matching `^[0-9a-f]{32}$` holding **exactly** `index.html`, and refuses symlinked dirs and symlinked `index.html` leaves. It **never consults the ledger**. **S5-Q-1 proves the consequence empirically: a well-shaped 32-hex dir absent from the ledger passes the FULL gate and the deploy command is surfaced.** |
| **C6** | **YES, verbatim** | `deploy_root_guard.py:141-158` byte-compares `R/_headers` against `host_bundle.py:56` `HEADERS_FILE_CONTENT`; re-derived by my own hands at **S5-Q-4** (128 bytes, byte-identical). Fixture: `test_trailing_byte_drift_refused`. |
| **C7** | **NO — verified once, enforced never** | G-36 records the two-sided isolation as an **api-probe observation** (Contente slugs `207688021de8…` and `761ebfd8a7e1…` → 404 on `tenuta-decks.pages.dev`; control on `decks.cntently.com` → 200). No predicate in any repo asserts it. The nearest enforcement is the **egress** guard `contact_synthesis.py:309-313` — `if host.lower() != DECK_HOST: raise ContactCardEgressRefused` — which is a **URL-composition** predicate, not a **serving** predicate. |

**(5) The R-4 consequence, stated precisely.** Today C5's shape test *incidentally*
doubles as an isolation test, because the two live publishers use disjoint alphabets
(32-hex vs 25-char base32, SG-1/G-33). **That isolation is an accident of alphabet
divergence, not a designed property**, and it evaporates under rot-trigger **R-4** ("a
third alphabet consumer appears, or two profiles agree on one alphabet", §3.3). S5-Q-1
is the demonstration: with shapes coinciding, a foreign slug staged into the wrong root
is **published**, not refused. C5's membership half is what survives R-4. **This is the
single most consequential gap I found and it is not in the architect's exposure column.**

---

### 12.3 THE TWO-SIDED FIXTURES THAT PROVE IT BITES

The predicate is only worth its ink if a fixture set exists that **fails when the
predicate is violated and passes when it is not**. Three fixtures per clause, stated as
acceptance criteria a QA leg can execute. The first three are **re-runs of fixtures that
already exist**; the fourth is the **negative twin the architect's slate did not carry**.

| # | Fixture | Expected | Status today |
|---|---|---|---|
| **F-1 (RED)** | For some `P`, build `R_P` omitting exactly one entry of `live(L_P)`; run the gate. | **REFUSED**, `reason=manifest_orphans`, message NAMES the omitted slug. | **PASSES — proven by my own hands (S5-Q-2)**, and by `test_active_slug_missing_from_root_refused`. |
| **F-2 (GREEN)** | For the same `P`, complete `R_P` so `slugs(live(L_P)) ⊆ dirs(R_P)`; run the gate. | **SURFACED** — `floodgates_deploy_root_ready`, one wrangler command. | **PASSES (S5-Q-2)**, and `test_green_all_active_slugs_staged_passes`; the live workspace leg `test_real_workspace_passes_full_gate` is the in-anger form. |
| **F-3 (NEGATIVE TWIN — foreign slug present)** | Stage a directory that is a **live slug of `P′`**, well-shaped under `shape_P`, holding exactly `index.html`, into `R_P`; run the gate. | **REFUSED as a stray** — C5 membership. | **FAILS TODAY. The gate PASSES it and surfaces the deploy (S5-Q-1).** This is the fixture that must be authored before any N≥2 option ships. |
| **F-4 (NEGATIVE TWIN — revoked slug still staged)** | Stage a directory for an entry whose `status == "revoked"`; run the gate. | **REFUSED** — C5 quantifies over `live(L_P)`. | **FAILS TODAY** by the same mechanism as F-3 (hygiene is shape-only). The live workspace happens to satisfy it (S5-Q-3/S5-Q-5: od67 revoked AND absent), so the fixture would go green on the real root — which is exactly why a synthetic RED is required for teeth. |
| **F-5 (C2 — cross-paired tuple)** | Run the gate with `R_A` and `L_B` where `bind(R_A) = L_A ≠ L_B`. | **REFUSED** — binding, before C4 is evaluated. | **FAILS TODAY.** `test_explicit_manifest_path_overrides_default` demonstrates the opposite behaviour is the *supported* one: an arbitrary ledger paired with an arbitrary root **passes**. At N=1 that is harmless; at N≥2 it is the vacuous-pass silent-404 path the architect named at P-2. |
| **F-6 (C3 — unscoped live entry)** | Give one entry of `⋃ live(L_P)` a `scope` that resolves to **no** publisher; run the gate for **every** publisher. | **REFUSED for every publisher**, naming the unscoped entry. | **INEXPRESSIBLE TODAY** — no scoping field exists (S5-Q-5/S5-Q-8). |
| **F-7 (C7 — two-sided live probe)** | For each ordered pair `(P, P′)`, `P ≠ P′`: `GET https://h/{slug}/` for every `h ∈ H_{P′}` and every `slug ∈ slugs(live(L_P))` → **404**; and the control on some `h ∈ H_P` → **200**. | Both sides asserted. A 404-only run is **not** a pass. | **PARTIALLY ON RECORD** — G-36 is exactly this shape for the (Contente, tenuta) pair at N=2 slugs. It is an observation, not a gate. |

**Teeth discipline.** F-3, F-4 and F-5 are **deliberately-broken INPUTS that a correct
gate REJECTS**, paired with a no-defect variant that passes — not defects injected into
working production code. That is the discriminating-canary shape and it is two-sided by
construction: the fixture bites ONLY on the violation. **Nothing in this leg proposes
changing `deploy_root_guard.py`**; F-3..F-7 are acceptance criteria for whatever DP-2
rules, authored so that S8's build branch (if T7 reading (ii) opens one) has a
falsifiable target and S9/S10 have something to re-fire.

---

### 12.4 VIABILITY MARKS — the slate graded against C1..C8

**Reading key.** **R1** = *can a live **Contente** slug **silently** 404?* (silently =
the gate does not refuse; a LOUD refusal that surfaces no command is **not** an R1
event). **R2** = *can a Contente slug resolve on a non-Contente host, or vice versa?*
**G-18** = *does the option weaken audience DEFAULT-DENY at egress?* — `constants.py:14-42`,
*"absence of a manifest IS denial"*.

| id | R1 silent-404? | R2 leak? | G-18 weakened? | **FINAL MARK** | Failing / conditioning clause |
|---|---|---|---|---|---|
| **P-0** | NO for Contente; **YES for the non-Contente lane** | no | **PRE-EXISTING-UNGATED** | **VIABLE-WITH-CONDITIONS** | **C1** for `P_tenuta` — that publisher has no ledger at all |
| **P-1** | no (LOUD refusal) | no (collapses the boundary rather than crossing it) | **YES** | **VIABLE-WITH-CONDITIONS** | **C5** `shape_P` — unsatisfiable for any already-live slug of a divergent alphabet; **+ C8** |
| **P-2** | **YES, unconditioned** | no | **YES** | **VIABLE-WITH-CONDITIONS** | **C2** — without binding, C4 passes vacuously (F-5); **+ C8** |
| **P-3** | **YES, unconditioned** | no | no | **VIABLE-WITH-CONDITIONS** | **C3 totality** — `null ⇒ omit` and `null ⇒ default` variants are **NON-VIABLE** |
| **P-4** | no | no | no | **VIABLE** | none — changes no publisher; the natural carrier of **C6** across the boundary |
| **P-5** | no for Contente | no | **YES — the sharpest on the slate** | **VIABLE-WITH-CONDITIONS** | **C4** at `|live(L_P)| ≥ 2` — wipe-then-stage is a mass-orphan event above one deck; **+ C8** |
| **P-6** | no, IF the conditions hold | no | **YES** | **VIABLE-WITH-CONDITIONS** | **C2 closed by atomicity; C3 and C5 are NOT**; **+ C8** |
| **P-7** | inherits P-2 or P-3 | no, IF the egress condition holds | no — but it touches a **different** guard | **VIABLE-WITH-CONDITIONS** | inherited **C2**/**C3** + a **C7-at-egress** condition; the security ruling is **not mine** |
| **P-8** | inherits P-1 or P-2 | no | **YES — uniquely mitigable** | **VIABLE-WITH-CONDITIONS** | inherited clause + **SEQUENCED-BEHIND S2** (S5-Q-6) + contract-only or it is P-11; **+ C8** |
| **P-9** | no | **YES — by construction** | **YES — an independent NON-VIABILITY ground** | **NON-VIABLE** | **C7** — false by construction; no condition inside the option closes it |
| **P-10** | no | no | no | **VIABLE** | none — adds a refusal, removes no check; rot-trigger R-1 does not falsify the predicate |
| **P-11** | n/a | n/a | n/a | **NON-VIABLE (G-29, prescribed)** | refused **before** the predicate is reached |
| **P-12** | no if fail-closed; **YES if it defaults** | no | **YES** | **VIABLE-WITH-CONDITIONS** | **C1/C2** — the Contente publisher is **not derivable** from `brand-tokens/profiles/` (G-4); **+ C8** |
| **P-13** | no | no | no | **VIABLE** | none — adds a refusal; satisfies no clause; composes only |

**On G-18 across the whole slate — CORRECTED per SECURITY-REVIEW-S5 RC-1(c).** The
previous text here read *"No option on this slate touches the audience classifier"* and
answered the G-18 question with the parenthetical *"(no option does)"*. **That
parenthetical is struck, and the correction is mine to own:** it was true on a narrow
test and false on the one that matters. Literally, no option **edits** the classifier.
**Operationally, six options mint a second write-into-a-capability-root path that
`stage_deck_bundle`'s EGRESS-DENY-1 does not sit on** — and publishing with the audience
gate never evaluated **is** weakening DEFAULT-DENY at egress, in the only sense that
matters. The G-18 column above now reads **YES** for **P-1, P-2, P-5, P-6, P-8, P-12** on
that one-line reason; **P-0** takes **PRE-EXISTING-UNGATED** (the tenuta lane already
publishes to a capability URL with no audience gate, SR-P-7 — P-0 makes that permanent and
unrecorded); **P-9** takes **YES** on the independent ground that under one project behind
N hosts *"which audience"* becomes unanswerable, since `classify(deck_template)` answers
"customer" against the **Contente** producer taxonomy.

**The narrower finding still stands and is not displaced.** **P-7 remains the only option
that touches the URL-**host** egress predicate** (`contact_synthesis.py:309-313`), which is
a *different* guard from the audience classifier and governs what may be composed into a
posted comment. Both findings are live: **P-7 widens a composition guard; six options
bypass a publication guard.** The G-18 column measures the second.

**Why my original framing was wrong, stated plainly** (`critique-iteration-protocol`
DELTA-scope, not cosmetic revision): I narrowed a question the architect had correctly
left open at §5.3 and routed to the security seat, answered it on a classifier-edit test,
and printed the answer as a blanket parenthetical. **A blanket negative pre-empted the
rite-disjoint critic's own question**, and it did so on a `type: one-way-door` packet where
**Q3** asks the operator to sort DEFAULT-DENY as COMMON or CONTRACT-LOCAL. The corrected
column, clause **C8** (§12.1) and front-page input constraint **7** are the remediation.
**No viability MARK is displaced by RC-1** — the review displaces none, and every dissent
it raised was against an exposure column, never a mark.

---

### 12.5 THE MARKS, IN FULL

**P-0 — VIABLE-WITH-CONDITIONS (C1, non-Contente side).** The Contente rail is untouched,
so the answer to "can a live Contente slug silently 404?" is **no** and the architect's
`NONE-NEW` mark stands. But `𝑷` under P-0 contains a publisher with **no ledger**: the
tenuta lane's staging root is a session-scoped `/private/tmp` scratchpad the environment
retires (S5-P-3, `RESUME-AFTER-RESTART.md:32`), with no repo-tracked root, no ledger and
no committed publish script. C1 REFUSES that publisher fail-closed. The exposure is
**symmetric to R1 but on the other side of the boundary**: if a fresh scratchpad is
staged that omits `nogqfo3pizvjhbdbxvvsvhdgt`, the live deck goes dark and **nothing
refuses**, because there is no ledger against which a superset could be checked.
**Condition (testable):** either (a) `P_tenuta ∉ 𝑷` — declared not-a-publisher,
hand-operated, and the predicate makes **no** claim about it, which the operator must
accept in writing; or (b) `P_tenuta ∈ 𝑷` and it acquires a durable `⟨L, R⟩` before its
next deploy, verified by F-1/F-2 against that pair. There is no third branch.

**P-1 — VIABLE-WITH-CONDITIONS (C5 shape).** I **concur with the architect's
LOUD-REFUSAL reading**: staging a base32 slug into the Contente root raises
`DeployRootRefused`, `batch.py:249-253` clears every command, nothing is deployed, and
Pages keeps serving the previous snapshot. That is an availability exposure, not an R1
event. My addition is the reachability analysis: P-1 can satisfy C5 **only** for slugs
minted under `shape_contente`. The live tenuta slug is 25-char base32 (G-33) and both
repairs are **prescribed out of scope** — re-minting it orphans a live 200 (SLUG-1,
`host_bundle.py:79-101`; and re-minting the live fleet is shape §7 out-of-scope), and
unifying alphabets is SG-1/DEFER-3 out-of-scope. **Condition (testable):** P-1 may absorb
only slugs `s` with `shape_contente(s)` true **at mint time**; F-3 must show that a slug
of the other alphabet REFUSES rather than being re-minted. P-1 therefore **cannot be a
complete answer to F-PUBLISH for the deck that already exists** — it is an answer for
future non-Contente decks only, served from Contente's account and domain. Whether that
is acceptable is an operator/governance ruling (DK-004's *"no default that points at
another organisation's project"* runs directly at it) and is **not** a predicate question.

**P-2 — VIABLE-WITH-CONDITIONS (C2).** The architect named the hazard precisely and
named the mitigation ("make the tuple atomic"). **I confirm the hazard is reachable
today and is not hypothetical**: `--deploy-base` (`batch.py:335`) and `--deck-manifest`
(`batch.py:345`) are independent flags, and `test_explicit_manifest_path_overrides_default`
demonstrates that an arbitrary ⟨root, ledger⟩ pairing **passes**. At N=1 this is inert;
at N≥2 it means `assert_manifest_superset` checks root A against ledger B's short list,
finds no orphans, and surfaces a deploy for a root missing **every one of A's live
slugs** — the whole-tree snapshot then 404s them. **Condition (testable):** C2 must be
implemented as mutual declaration and covered by **F-5**; a cross-paired tuple REFUSES
before C4 is evaluated, and a correctly-paired one surfaces. **Unconditioned, P-2 is
NON-VIABLE on R1.** With F-5 green, P-2 is the option in which C4 keeps its **exact
current semantics** and is simply instantiated N times — which is the strongest thing
that can be said for any option on this slate.

**P-3 — VIABLE-WITH-CONDITIONS (C3 totality), and the two obvious variants are
NON-VIABLE.** The architect called this the sharpest exposure and I concur, and can now
say why in one clause: P-3 replaces C4's **exemption whitelist of one value** with an
**inclusion predicate over a field that does not exist** (S5-Q-5/S5-Q-8). Every one of
the 10 existing rows would be `scope = null`, so `|{P : e ∈ scope(P)}| = 0` for **all nine
live Contente decks** — C3 totality fails for the entire live fleet on day one. Of the
three `null` readings the architect enumerated:
- `null ⇒ "belongs to no profile"` — **NON-VIABLE**: nine live client decks are silently
  dropped from every root's required set while every root's superset check passes. This
  is the canonical R1 event and it is the reason R1's NON-VIABLE rule exists.
- `null ⇒ "belongs to the default profile"` — **NON-VIABLE**: it restores fail-closure
  only while the default is right, and re-breaks **silently** the first time a second
  Contente-shaped publisher exists. A predicate whose correctness depends on a default
  is not fail-closed; it is fail-closed-for-now.
- `null ⇒ REFUSE` — **the only viable branch.** **Condition (testable):** (i) the scoping
  field is **mandatory** and absent/unknown ⇒ REFUSE, never omit — fixture **F-6**;
  (ii) all 10 rows are backfilled **before** any deploy, a HARD PRECONDITION of the same
  class as the 2026-07-09 Option-B backfill the ledger records in its own
  `_backfill_2026-07-09` key; (iii) F-1/F-2 re-fire per scope after the backfill.

**P-4 — VIABLE.** No publisher behaviour changes, so R1/R2/G-18 are all "no" and the
architect's `NONE-NEW` stands unqualified. My addition: P-4 satisfies **zero** clauses by
itself — it is a modifier, not a member of `𝑷` — but it is the **natural carrier of C6
across the boundary**. C6 is enforced today only *inside* the Contente gate
(`deploy_root_guard.py:142-158` byte-comparing against `host_bundle.py:56`); the
non-Contente side reproduces the same four lines by **hand-copied heredoc** (S5-P-4) with
no comparison between the copies. S5-Q-4 shows the two copies presently agree at 128
bytes byte-for-byte — which is a receipt that the term is **currently** COMMON, and
equally a receipt that its agreement is maintained by hand.

**P-5 — VIABLE-WITH-CONDITIONS (C4 above one deck).** Zero exposure to the Contente rail
by construction; the architect's `NONE-NEW` stands. The condition is one the slate states
only obliquely (§8, as contract-incoherence) and which I raise to a **viability
condition with a named trigger**: DK-004's *"never uploads more than the one slug"*
posture, implemented as `publish-tenuta.sh`'s **wipe-then-stage** of `$DIST` (S5-P-4),
satisfies C4 **only while `|live(L_P)| = 1`**. The moment a **second** non-Contente deck
is minted, wipe-then-stage is a **mass-orphan event** for the first — the exact R1
failure mode, on the a8t side, produced by the a8t side's own safety posture.
**Condition (testable):** before a second non-Contente deck exists, `P_a8t` must acquire
either (a) an accumulating root + ledger and pass **F-1/F-2**, or (b) a distinct project
per deck so that `N` grows instead of `|live(L_P)|` — in which case **F-7** must be
re-fired across the enlarged pair set. Fixture: staging deck #2 into a wiped root
REFUSES. **Sequencing note, not a condition:** `deck-kit/bin/publish.mjs`
does-not-exist (G-30, S5-P-9) and **this leg schedules nothing** (shape §7 out-of-scope).

**P-6 — VIABLE-WITH-CONDITIONS. This is the direct answer to the architect's open
question** (*"Whether atomicity is sufficient is exactly the question for the
requirements-analyst acceptance predicate"*). **Atomicity is necessary and sufficient
for C2, and insufficient for C3 and C5.**
- **C2 — CLOSED by atomicity, with one proviso.** If `⟨R_P, L_P, H_P⟩` is read as one
  tuple, a mismatched pair is *not expressible*. **Proviso (testable):** the envelope
  must be the **SOLE** source of those three fields. An envelope that merely *populates*
  `--deploy-base`/`--deck-manifest` leaves the mispairing reachable at the call site,
  because those flags remain independently overridable (`batch.py:335`, `:345`).
  Independent per-field override must **REFUSE**, not merely be discouraged — F-5.
- **C3 — NOT closed.** Atomicity makes each publisher internally consistent; it says
  nothing about whether the union of the envelopes **covers** every live entry exactly
  once. **Condition:** the envelope set is **closed and enumerable**, and C3 is evaluated
  across it — F-6.
- **C5 — NOT closed.** Membership is a per-root property the envelope does not assert.
  **Condition:** F-3 and F-4 authored per publisher.
- The architect's own dissent — two parsers, two ways to misread one schema — is
  discharged only by **per-side conformance fixtures**, i.e. P-6 is strictly **P-4 plus a
  schema**, exactly as the architect states. I concur and add: the fixtures are the part
  that carries the predicate; the schema alone carries none of it.

**P-7 — VIABLE-WITH-CONDITIONS (inherited + a C7-at-egress condition). I do not rule the
security question.** P-7 takes P-2's shape (then condition C2/F-5) or P-3's shape (then
condition C3/F-6); naming which is part of the DP-2 ruling, not of this grading. On the
`DECK_HOST` half, the predicate has something precise to contribute **without** ruling:
`contact_synthesis.py:309-313` refuses any URL host `!= DECK_HOST` exactly, and
`link_on_play.py:58-62` records why — *"an exact netloc match refuses userinfo
(user@host), an explicit port (host:port), and any foreign host in one predicate"*. The
**condition under which widening it would not be a weakening** is statable and testable:
(i) the allowlist is a **closed set of exact netlocs** derived from the **same atomic
envelope** as `⟨R_P, L_P⟩` — never a pattern, suffix or wildcard match; (ii) the check
remains **per-host exact equality**, preserving the userinfo/port refusals verbatim;
(iii) the composed URL's host must belong to `H_P` **for the publisher that owns that
slug** — so a Contente slug composed into a URL on a tenuta host still REFUSES. Under
(iii) the egress guard becomes the **only implementation of C7 anywhere in the fleet**,
at comment-post time rather than at serve time. Whether that widening is a *weakening* or
a correct *generalization* is the **security rite's ruling** (S5's
`rite_disjoint_exit_critic`), and shape §7 out-of-scope forbids me to weaken a WS-GUARD
invariant to make per-profile publishing easier. **I state the condition; I do not rule
it, and I do not propose the change.**

**P-8 — VIABLE-WITH-CONDITIONS (inherited + sequencing).** P-8 relocates the root
question rather than resolving it, as the architect says: staging non-Contente slugs into
deck-host's `public/` **is** P-1 (inherit P-1's C5 condition); staging elsewhere **is**
P-2 (inherit P-2's C2 condition). Two conditions are P-8's own: (i) **SEQUENCED-BEHIND
S2.** A predicate implemented in deck-host needs a `shape_P` function, and deck-host's
own slug gate is **mid-reconciliation right now** — `/^[a-z2-7]{26}$/` on `main`,
`/^[0-9a-f]{32}$/` on `s2/ws-f-ch01-reconciliation` @ `cbcd180` (S5-Q-6). On the `main`
shape, `shape_P` is false for **every live slug** and C5 would refuse everything (loud,
not silent). (ii) **contract-only implementation**; copying `host_bundle.py` /
`deploy_root_guard.py` logic across is **P-11** and NON-VIABLE (G-29). The governance
observation — a personally-owned repo (G-17) holding the publishing surface for an
account no credential on this machine can reach (G-35) — is carried, not ruled.

**P-9 — NON-VIABLE on C7. This is my one substantive disagreement with the architect's
exposure column.** The architect marked P-9 `NONE-NEW for orphaning; OVER-SERVE risk
instead` and routed it to the security critic. **I concur on the orphaning half and
escalate the containment half from a risk to a clause failure.** One Cloudflare Pages
project serves **one snapshot** to **every** host attached to it
(`deploy_root_guard.py:2-5`). Under P-9, `H_P = H_{P′}` for every pair, so
`∀ e ∈ live(L_P), ∀ h ∈ H_{P′}: GET → 404` is **false for every e and every h** — C7 is
not merely unverified, it is **false by construction**. The two escape attempts both
close:
- *Declare `N = 1` so C7 has no pairs.* Then P-9 **deletes** the isolation property that
  G-36 verified two-sided, which the shape's §7 Emergent floor forbids in terms:
  *"the floor that evidence quality may never REGRESS below what is already on record
  (G-38b's two-sidedness is a floor)"* (`…shape.md:1224-1225`). Refused by the floor.
- *Add a routing layer to scope paths per host.* That is a **different mechanism** and
  therefore a different option; P-9's entire case-for is that it adds **no** mechanism.
  Naming it is not mine to do — the slate belongs to the architect — so I record it as a
  **residual for DP-2**: *if the operator wants domain separation, the option that would
  have to be enumerated and evaluated is domain separation **plus** a per-host routing
  predicate, and it is not on this slate.*
**No condition inside the option closes the exposure ⇒ NON-VIABLE**, per the rule this
leg was charged with.
**The distinction from P-1, stated so the two marks are not read as arbitrary: P-9
DELETES an isolation that exists; P-1 DECLINES TO EXTEND it to new decks.** A recorded
property regressed is a floor violation; a new deck given no isolation is a governance
choice.
**One consequence the operator needs before a low-friction action arrives by accident**
(the architect's own worry, sharpened into a rule): attaching `decks.tenuta.io` to the
`tenuta-decks` project — the attach the `SHIP-RECEIPT-advantage-rc.md` already
anticipates — is **NOT P-9 and is NOT an R2 event**. It enlarges `H_P` for one publisher,
and C7 quantifies over publishers with `H` as a **set**. **The R2 event is attaching a
host to a project on behalf of a DIFFERENT publisher's audience.** That is the testable
line: *safe attach — the new host serves only slugs of the publisher that owns the
project; unsafe attach — the new host serves a snapshot containing another publisher's
live slugs.*

**P-10 — VIABLE.** Account pinning adds a refusal and removes no check; the architect's
`NONE-NEW` stands. My addition: the architect's own §3.3 dissent against P-10 (it
hard-codes today's co-occurrence as tomorrow's ontology, falsified by **R-1**) is a real
objection to P-10 **as a classification**, and it is **not** an objection to P-10 under
this predicate — because the predicate never mentions accounts. Under C1..C7, two
projects inside one account are simply two publishers with two triples. **P-10 is safe
to rule for and unsafe to name a taxonomy after**, and those are separable decisions.

**P-11 — NON-VIABLE (G-29), preserved verbatim from the architect's disposition.** Refused
on a prescribed constraint before the predicate is reached; no clause mark applies. The
architect's recorded-and-overruled dissent (that `deploy_root_guard.py` encodes hard-won
semantics a clean-room re-derivation may get subtly wrong) is **exactly what §12.1 exists
to discharge**: the semantics are now written as seven clauses with seven fixtures, which
is the permitted form of sharing them.

**P-12 — VIABLE-WITH-CONDITIONS (C1/C2).** The architect's `NONE-NEW if fail-closed;
EXPOSED if it defaults` is correct and I sharpen both halves. If it **defaults**, the
default names some `⟨R, L⟩`; if that default is the Contente tuple, a deck built from a
coordinate-less profile is staged into the Contente root — **P-1 reached by accident**,
which is worse than P-1 chosen. If it is **fail-closed**, the residual is structural:
Contente has **no** entry under `brand-tokens/profiles/` (G-4 — its brand binding lives
in `@autom8y/contente-tokens` on the a8 side), so `P_contente`'s triple is **not
derivable from this substrate at all** and P-12 is a **partial** envelope. A partial
envelope is precisely where C3 totality breaks. **Conditions (testable):** (i) missing
coordinates ⇒ **REFUSE**, never default — fixture: a profile dir without publish
coordinates REFUSES, one with them surfaces; (ii) `P_contente`'s triple is declared
somewhere the derivation can reach, or P-12 must compose with another option and C3 is
evaluated across the union — F-6; (iii) `DEFAULT_PROFILE_ROOT` is a hardcoded **absolute**
path (G-27) so derivation currently rests on a machine-local assumption, which cannot
carry C2's binding half until resolved. The account-ids-in-a-design-tokens-repo dimension
the architect raised is a security question, **routed, not ruled**.

**P-13 — VIABLE.** Only ever adds a refusal; `NONE-NEW` stands. Two sharpenings, neither
of which changes the mark. (a) A listability check is the natural implementation of the
**reachability precondition on `H_P`** — you cannot bind a root to a hostset you cannot
see — so P-13 is C2-adjacent even though it satisfies no clause. (b) The architect's
"necessary but not sufficient" dissent (two accounts could each hold a project named
`deck-host`) has a one-line closure: **pin the project's identity, not its name** — the
`(account_id, project)` pair or the project id — and the check becomes an identity
assertion rather than a visibility assertion. Recorded as an observation for whoever
implements it; not a condition on viability, because P-13 removes no check either way.

---

### 12.6 Dissent register for this leg

**Where I disagree with the architect:**

1. **P-9: `OVER-SERVE risk` → `NON-VIABLE on C7`.** Stated in full above. The
   disagreement is about whether a **verified, on-record** property that an option
   deletes is a *risk to price* or a *clause to fail*. The shape's §7 Emergent floor
   (`:1224-1225`) makes it the latter. The architect's routing of P-9 to the security
   critic stands and is **not** displaced by my mark — the security rite rules the
   security question; the predicate mark is the requirements question.
2. **The C5 membership gap is missing from the exposure column entirely.** §3.2 marks
   P-1's exposure as loud, P-2/P-3/P-6/P-7/P-8 as `PROVISIONAL-EXPOSED` on
   root↔ledger and profile-scoping grounds, and no option carries an exposure for
   *root→ledger* containment. **S5-Q-1 shows the gate publishes a foreign well-shaped
   slug today**, and §3.3's own rot-trigger **R-4** is the event that makes it reachable
   between two live publishers. This is a gap in the exposure analysis, not in the option
   slate — the architect's §11 weakness #2 anticipated exactly this outcome
   (*"If the requirements-analyst's acceptance predicate finds a silent-404 path I did
   not name, the slate's exposure column is wrong, not merely incomplete"*), and the
   honest reading is that the column is **incomplete on a different axis than R1**: the
   path S5-Q-1 opens is a **leak** (R2), not an orphan (R1).
3. **P-0's exposure is understated as "not reproducible."** Non-reproducibility is a
   finding about artifacts; **C1 makes it a fail-closed refusal about a live capability
   URL.** The tenuta lane has no ledger, so nothing can ever check that a re-deploy
   carries `nogqfo3pizvjhbdbxvvsvhdgt`. That is the same failure class as R1, on the
   other side of the boundary, and the epoch's risk map does not carry it.

**Where I concur and add nothing:** P-1's LOUD-REFUSAL reading; P-3 as the sharpest
option; P-11's prescribed refusal; P-4's and P-13's `NONE-NEW`; the composability note at
§4.1 (my marks are **per option** and a composition inherits the **union** of its
members' conditions — e.g. `P-2 + P-6 + P-13` inherits C2-by-atomicity plus C3 and C5
still open).

---

### 12.7 What this leg did NOT do

- **Did NOT answer F-PUBLISH.** No option is recommended, ranked or preferred. The marks
  grade **admissibility**, not desirability: three options are VIABLE, nine are
  VIABLE-WITH-CONDITIONS, two are NON-VIABLE. That is not a shortlist.
- **Did NOT rule T7.** Both readings stand exactly as §5.2 carries them. Note only that
  the marks are **T7-invariant**: no mark changes under either reading, because C1..C7 are
  stated over publishers, not over rails.
- **Did NOT re-enumerate the slate.** Where the predicate implied an option that is not
  present (domain separation **plus** a routing predicate, at P-9), I recorded it as a
  **residual for DP-2** rather than adding an option to the architect's slate.
- **Did NOT re-litigate Option B** (G-20), **did NOT weaken any WS-GUARD invariant**
  (P-7's condition is stated as the shape a non-weakening would take, and routed to the
  security critic), **did NOT unify the slug alphabets** (C5's membership half is
  shape-agnostic precisely so DEFER-3 stays closed), **did NOT schedule any DK item**.
- **Did NOT propose a code change.** F-3..F-7 are acceptance criteria for whatever DP-2
  rules. `deploy_root_guard.py` is not edited, patched or proposed-for-patch by this leg.
- **Did NOT run a reserved lever.** The S5-Q probes are read-only or tmp-fixture-only; no
  `wrangler` write, no project create, no deploy, no DNS, no mint, no SEND.
- **Did NOT touch S2's files or git state.** Every `deck-host` read was read-only on
  branch `s2/ws-f-ch01-reconciliation`; no stash, checkout, reset or write. S5-Q-6 records
  S2's in-flight reconciliation as a freshness fact and rules nothing about it.
- **Did NOT ship the packet.** `status: proposed`. PT-03 gates. RUNG = **authored**.

---

### 12.8 Self-assessment (leg 2)

**Evidence grade: MODERATE (ceiling, not floor)** per `self-ref-evidence-grade-rule` —
authored inside 10x-dev about 10x-dev's own design surface. **Nothing here is
self-attested as realized.** The predicate is a **design artifact**: it is not
implemented anywhere, and saying so is the point of §12.2's "exists today?" column.

**What is STRONG underneath this leg and is not mine:** G-36, G-33, G-37, G-38/G-38b and
the S1 eunomia VERDICTs. **What I derived by my own hands:** S5-Q-1..S5-Q-8 — additional
hands, **not** rite-disjoint attestation (frame §9.8; the same distinction the architect
draws at §11 applies to me).

**Where this leg is weakest, stated plainly:**

1. **C7 is the only clause with no mechanical implementation path named.** C1..C6 are
   file-and-directory predicates a gate can evaluate before surfacing a command. C7 is a
   **live-surface** predicate: it requires N×M HTTP probes against deployed hosts, which
   is a post-deploy check, and a pre-surface gate cannot run it. **The predicate is
   therefore honest about a split it does not resolve: C1-C6 are pre-surface; C7 is
   post-deploy.** An option that satisfies C1-C6 can still produce an R2 event that is
   only detectable after the snapshot is live. P-7's egress condition is the closest thing
   to a pre-emptive C7 and it acts at comment-post time, not at deploy time.
2. **`scope(P)` is left abstract in C3.** I deliberately did not specify whether scope is
   a ledger field, an envelope membership, or a root-derived fact — that choice **is**
   the F-PUBLISH ruling and specifying it would be answering the door. The cost is that
   C3's fixture F-6 cannot be written until DP-2 rules.
3. **The marks are per-option; compositions are not graded.** §4.1's mechanism×modifier
   space is larger than 14, and I inherited the architect's §11 weakness #3 rather than
   closing it. The union rule at §12.6 is a stated convention, not an evaluated result.
4. **`N` is treated as given.** The predicate assumes the publisher set is declared and
   enumerable. Nothing in it forces `𝑷` to be *complete* — a publisher that exists in the
   world but is not in `𝑷` (exactly P-0's tenuta lane) is invisible to every clause. C1
   catches it only once it is declared. **A publisher nobody declares is the residual
   silent-404 surface no predicate can close**, and the operator should read that as the
   reason P-0's condition (a) requires a written acceptance rather than a code change.

**Rite-disjoint critic for this leg, unchanged** (`…shape.md:464`): **security**
(security-reviewer, co-seated). The three options I hand that critic, in priority order:
**P-9** (NON-VIABLE on C7 here — I ask the critic to test whether that mark is too strong
or not strong enough), **P-7** (the egress-widening condition at
`contact_synthesis.py:309-313` — I state a condition and explicitly do not rule it), and
**the C5 membership gap** (S5-Q-1 — a leak vector reachable by staging error alone, with
no option-dependence at all).

---

### 12.9 The security seat's rulings on the three §13 hand-offs (recorded per SECURITY-REVIEW-S5 RC-1)

Leg 3 handed three items to the rite-disjoint security seat; **all three are now ruled and
none remains "flagged".** (i) **Env-prefix account shape — ADVISORY, upgrading to a
CONDITION on any option that surfaces the account into a command string**: the env-prefixed
string **must not be persisted into a committed report artifact**, and it must be paired
with the **P-13 listability assertion** so a wrong-account paste **refuses** rather than
deploying elsewhere — confirming on security grounds that *assert-never-surface* (P-10/P-13)
is the cleaner answer to the account dimension than *parameterize* (P-7). (ii) **P-7's
revert asymmetry — NOT an advisory: a NON-VIABILITY GROUND for the unconditioned form.**
The `DECK_HOST` half may not be ruled as *"make it a parameter"*; it may be ruled only as
*"make the composition publisher-aware and the guard a slug→host **ownership** assertion,
default-singleton."* Condition **(iii) — the slug→host ownership assertion — is MANDATORY,
not one of three**: a set-membership guard **without** the pairing check is *strictly weaker*
than today's equality guard, because it would permit composing a Contente slug onto a
non-Contente host (R2 at the comment-post surface). **My §12.5 offered (iii) as one of three
conditions; the security seat raises it to load-bearing and I record the correction.** The
seat adds a fourth of its own: ship the allowlist **singleton-by-default** (`{DECK_HOST}`),
widened only by an explicit reviewable **data** edit, so the code change lands with zero
behavioural delta and the one-way step requires a separate deliberate act. (iii) **P-12's
git-history one-way — ADVISORY with a condition**: an account id is an *identifier, not a
credential* (standalone **Low**); the profile coordinate file must carry a **pointer** (env
var name or secret reference), **never the literal id**. The seat also reconciled my P-13
sharpening (*pin identity, not name*) with leg 3's objection: **supply the
`(account_id, project)` pair via the ENVIRONMENT and assert it at runtime; never commit it.**
**None of these is ruled by me** — they are recorded here so the operator reads them on the
packet rather than only in the review.

---

### 12.10 P-14 confirmation (D2-R3)

**The PRE-SHIP confirmation owed by this seat** (`ADVERSARY-REPORT-S5-dp2-slate-2026-09-05.md`
§D.7 item 3; §0 PRE-SHIP CONFIRMATIONS OWED). The architect enumerated **P-14** at
`§4 P-14 :1046-1216` with a **PROVISIONAL** C1–C8 face and said in its own first line that it is
**not a mark**. It is mine to confirm or correct, and mine to mark. **I do not answer F-PUBLISH
and I do not rule T7.**

**Standing constraint on everything below.** P-14's *runtime* behaviour is **UV-P-7**
(`§9.1`; label in frozen syntax at `§4 P-14`). **I may not assert it.** Every clause reading here
is about **what the predicate requires of a router**, never about what a deployed router does.
`S5-R-3` receipts that the **toolchain** ships and uploads Functions/`_routes.json`; it does not
receipt that a deployed predicate behaves as designed — and `S5-R-4`, which I re-probed by my own
hands, receipts that **no serve-time component exists**: `git ls-files | grep -iE "functions/|_worker|_routes"`
→ **zero tracked matches**, and `functions`, `public/_worker.js`, `public/_routes.json`,
`_routes.json` are all `No such file or directory`. That corroborates **S5-Q-7**.

#### 12.10.1 P-14's C1–C8 face — CONFIRMED, with two corrections

| clause | architect's PROVISIONAL reading | my disposition |
|---|---|---|
| **C1** legibility | unchanged — one ledger | **CONFIRM** |
| **C2** binding | not engaged — one root, one ledger | **CONFIRM.** P-14 is the only multi-host option that never creates a pair to cross-pair. **F-5 is not owed by P-14.** |
| **C3** partition | ENGAGED AND INVERTED — the router needs the field P-3 needs, to route rather than to filter | **CONFIRM, and this is the failing clause.** See 12.10.2. |
| **C4** no-orphan | unchanged — superset keeps its N=1 shape | **CONFIRM — and name the consequence the row does not.** C4 is not weakened, it is **out-scoped**: the predicate goes on passing while the router 404s the decks C4 exists to protect. **A clause that cannot see the failure it was written for is not satisfied by passing.** |
| **C5** hygiene | unchanged — one root, one `shape_P` | **CONFIRM.** F-3/F-4 remain owed on the same ground as every other option, not on P-14's. |
| **C6** headers | unchanged; **"Open:** whether a Function may set headers, and whether that is a C6 event*" | **CORRECTION — the open question closes, and it closes NEGATIVE.** C6 quantifies over `bytes(R_P/"_headers")` — a **file on disk**, byte-compared against `HEADERS_FILE_CONTENT` (`deploy_root_guard.py:141-158`; **S5-Q-4**, 128 bytes both sides, `BYTE-IDENTICAL: True`). A Function that sets or overrides a response header **does not change that file and therefore cannot fail C6** — which is exactly the problem: **the guard-header set could be altered at serve time with C6 GREEN.** The header question is real and C6 is the wrong clause for it; it belongs to **C9** below (a header rewrite is response-shaping) and to the fence's served header arms **INV-02..INV-05** (`src/fence/invariants.js:74-77`, `needs: 'served'`), which are the only header checks anywhere that look at what was actually served. |
| **C7** containment | "THE CANDIDATE PRE-SURFACE PATH — and only partially" | **CORRECTION — narrower than "partially".** See 12.10.4: **no part of C7 becomes pre-surface.** What P-14 adds is a *third* evaluation time between the two the predicate already had. |
| **C8** audience-egress | unchanged in quantifier; a ninth clause may be owed | **CONFIRM on the quantifier** — C8 ranges over `dirs(R_P)` and P-14 changes no root, so C8's reading is untouched. **Dissent 3's C-3 orphan-gate face is a SEPARATE question and is NOT mine** — it is **D2-R5**, owed by the security co-seat, whose review on record predates P-14. I do not pre-empt it; I record that **C8 is satisfied or not independently of how D2-R5 rules**, because C8 asks whether staged artifacts are classified, not whether a router may re-derive the verdict. |

**Anchor drift corrected (two, both in §4 P-14; the finding is unaffected).** The option cites
`src/fence/run.js:248` for INV-08 and `:221` for the served-arm list. **Re-probed: INV-08 is at
`src/fence/run.js:274`** — `receipts.push(fromGuard(slug, 'INV-08', guard.evaluateHashParity(p.bodySha, entry.frozen_sha256), {` —
and **the served-arm id list is at `:235`**; `:248` is INV-01's served-status cell. The registry row
is `src/fence/invariants.js:80`. **Recorded, not silently adopted; §4 is the architect's text and is
not edited here.**

#### 12.10.2 FINAL MARK — **P-14 is NON-VIABLE, failing C3**

**The R1-by-routing face is NOT closable by C1–C8, and it is not closable by C9 either.** This is
the question D2-R3 puts to me and it deserves the direct answer.

**Why C1–C8 cannot close it.** C1–C8 are, without exception, **pre-surface** predicates over a
ledger and a directory tree: every one of them is evaluated before a `wrangler` command is
surfaced, and every one of them can be GREEN on a root and ledger that are internally perfect.
P-14's failure mode is **a correct root, a correct ledger, a passing gate, a successful deploy, and
a router that resolves all nine live rows to "owned by nobody"** — because the ownership key **does
not exist in `config/deck-manifest.json`** (**S5-P-6**, re-derived at **S5-Q-5**/**S5-Q-8**: the six
per-row fields carry no scope dimension). **C3 is the clause that names this and C3 is the clause it
fails**: `∀ e ∈ ⋃ live(L_P) : |{P : e ∈ scope(P)}| = 1`, and **ZERO ⇒ REFUSE**. Under P-14 every
live entry resolves to zero owners the moment the router keys on the absent field.

**So why is that a NON-VIABLE mark rather than a condition?** Because of **where the clause can be
evaluated**. For **P-3** the identical C3 defect is a **condition**: P-3's scope filter runs inside
the pre-surface gate, so `null ⇒ REFUSE` is expressible *at the point of failure* and the backfill
is a checkable precondition (§12.5 P-3). For **P-14** the scope resolution runs **at request time,
in a different process, after the gate has already returned GREEN**. A pre-surface clause cannot
refuse a serve-time resolution; **the gate has no jurisdiction over the router.** To close P-14's
R1 face you would need a predicate that verifies *the deployed router's resolution table against the
live ledger* — which is (a) not C1–C8, (b) not C9, and (c) **UV-P-7 by construction**: it requires
an attach and a deploy, both **operator-reserved levers**, against a project this machine's
credential cannot reach (**G-35**, S5-P-2). **No condition available to this predicate closes the
exposure, so the rule this leg was charged with applies: NON-VIABLE.**

**This is a mark on the option as enumerated, and I say plainly what would change it.** If the
ownership map were **not the ledger** — if the router keyed on a closed, enumerable, deploy-time-
verifiable artifact whose correspondence to `live(L_P)` is checkable *before* the deploy is surfaced
— then C3 becomes evaluable pre-surface and the mark is reconsiderable. **That artifact does not
exist and P-14 as enumerated does not propose one.** I am not inventing it: naming an option is the
architect's remit, not mine (§12.7), and I record it as a **residual for DP-2** in the same form as
P-9's.

**Relation to P-9, so the three marks are legible together.** P-9 is NON-VIABLE on **C7** — it
deletes an isolation that exists. P-14 is NON-VIABLE on **C3** — it *rebuilds* that isolation in
code, and pays for it with a new silent-404 surface at a time no clause can reach. **The architect
is right that P-14 is the option P-9 lacked; it does not follow that P-14 is viable.** Both marks
rest on the same structural fact: **one project serving one snapshot to N hosts cannot get
containment from an absence guarantee, and a code-path guarantee costs a clause elsewhere.**

**Preserved from the architect, and I concur:** dissent 1's distinction — **P-14 replaces an
ABSENCE guarantee with a CODE-PATH guarantee**, which is *non-resolution*, not containment
(`deploy_root_guard.py:2-5`; the snapshot still contains every publisher's bytes). That framing is
correct, it is the operator's to weigh, and my C3 mark does not rest on it.

#### 12.10.3 The ninth clause — **RULED OWED. C9, in C1–C8 form.**

The architect asked whether a ninth clause is owed and did not mint it — correctly; the predicate is
mine (adversary §D.5 N-6). **It is owed, and not only for P-14.** A response-shaping component is a
new class of actor over the served surface that C1–C8 never contemplated, because until P-14 the
slate had no serve-time member at all. **C9 is written to bind ANY publisher that acquires one**,
not P-14 specifically — a clause minted for one option is a packaging accident (§3.3).

> ```
> C9 RESPONSE-SHAPING-ONLY — per publisher, per served artifact
>    [MINTED at D2-R3; witnessed by fence INV-08 ∧ INV-09; G-PROPAGATE / host_bundle.py:8-9]
>    ∀ P ∈ 𝑷 : if P's project carries a serve-time component S (Pages Function,
>              _worker.js, or _routes.json-selected handler), then
>        ∀ d ∈ dirs(R_P) \ {"_headers"} :
>            sha256( bytes served at https://h/{d}/ , ∀ h ∈ H_P )
>          = sha256( bytes at R_P/d/index.html )
>          = e.frozen_sha256   where e ∈ entries(L_P) ∧ e.slug = d.
>    S MAY decide WHETHER to respond (200 / 404 / 403). S MAY NOT rewrite, inject,
>    template, wrap, or re-render the response body. Absence of a served probe is
>    NOT satisfaction — a served clause is NEVER GREEN by omission.
>    (C9 subsumes nothing in C6: C6 is a FILE on disk, C9 is the BYTES on the wire,
>    and a serve-time component can pass C6 while failing C9.)
> ```

**Why C9 is not covered by any existing clause.** C4/C5 quantify over the staged tree; C6 over a
file; C8 over classification. **None of them looks at what was served.** The serving model this
protects is `host_bundle.py:8-9` — *"the host MOVES bytes, it never re-renders"* — and a rewriting
Function breaks it **invisibly to every pre-deploy predicate**, because the staged bytes on disk
still hash correctly. This is the one place where the architect's INV-08 observation is exactly
right and I adopt it.

**The discriminator, sharpened — and this is my addition.** The architect names INV-08 as the
witness. **INV-08 alone is not discriminating**: it fails for a rewriting Function *and* for a
plain staging error. The signature that isolates body-shaping is the **conjunction**:

> **INV-08 FAIL ∧ INV-09 PASS** — served sha ≠ ledger sha **while** staged sha == ledger sha.

`src/fence/invariants.js:80` INV-08 — *"byte-parity: SERVED sha == deck-host ledger frozen_sha256"*,
`needs: 'served'`; `:81` INV-09 — *"staged parity: `public/<slug>/index.html` sha == ledger
frozen_sha256"*, `needs: 'local'`. Both carry `recommended: false`, i.e. **their exit mappings are
RULED, not unruled recommendations** (`src/fence/run.js:409`, `:418`). A staging error fails **both**;
a body-shaping serve-time component fails **only INV-08**. **That conjunction is the two-sided witness
C9 needs, and the fence already computes both halves** (`run.js:224` INV-09, `run.js:274` INV-08).

**Fixture F-9, in §12.3's form — three arms.** **RED-a (body-shaping):** a serve-time component
that injects, wraps or templates the response → **INV-08 FAIL ∧ INV-09 PASS** → **REFUSED naming
C9**. **RED-b (header-shaping):** a component that alters the guard headers at serve time → caught
by **INV-02..INV-05** (`invariants.js:74-77`, `needs: 'served'`), **not** by C6 — this is the arm
that closes the C6 open question negatively (12.10.1). **GREEN twin (response-shaping only):** a
component that returns 404 for a non-owned host and passes the untouched artifact through for the
owner host → **INV-08 PASS ∧ INV-09 PASS**, C9 satisfied.
**Two honest limits.** (1) **F-9 is a SERVED fixture** — it needs a live probe, so it inherits
C7's evaluation-time problem and cannot be run pre-surface; `src/fence/probe.js:7` records why the
probe must be a GET (*"HEAD returns no body, so INV-08 byte-parity"* cannot be computed). (2)
**INV-08's datum is deck-host's own ledger sha, not the producer-frozen artifact** — the registry
says so in its own note at `invariants.js:80` (*"RECORD-OF-TRUTH CAVEAT … NOT the producer-frozen
Asana attachment"*), which is **LF-2 / candidate DEFER-5** arriving inside the witness. **This does
not weaken C9**: C9 asks whether the served bytes equal a *fixed recorded value*, and any rewrite
moves them off it regardless of which artifact the record ought to be. **Which artifact the record
ought to be remains DEFER-5's, unruled here.**

#### 12.10.4 §12.8 weakness 1 — **CONFIRMED NARROWED, NOT REVERSED**

w1 says *"C7 is the only clause with no mechanical implementation path named … C1-C6 are
pre-surface; C7 is post-deploy."* **P-14 narrows it and I record the narrowing precisely, because
the architect's own C7 row already flags that the narrowing is partial.**

**What changes:** the two-position model in w1 (pre-surface / post-deploy) was **complete for the
slate as it stood** and is **incomplete now**. There are **three** positions, and P-14 occupies the
new middle one: **pre-surface** (a gate reads files before surfacing a command) · **serve-time** (a
router evaluates on every request) · **post-deploy** (an N×M probe sweep after the fact).

**What does NOT change — and the coordinator asked me to say which:** **no part of C7 becomes
pre-surface.** The test that *would* be pre-surface is precisely statable, and it is the test that
does not exist: *"a predicate, evaluable before the `wrangler pages deploy` command is surfaced,
that verifies the routing artifact's host→slug-set resolution equals `{(h, slugs(live(L_P))) : h ∈ H_P}`
for every publisher, against the ledger, without a network probe."* **Two things must both hold for
that test to exist, and neither holds:** (a) the routing artifact must be **static and readable at
gate time** — a `_routes.json` path list is, but a Function's resolution is **code**, and the
architect's own mechanism describes a Function; and (b) the ownership map must be **derivable from
the ledger** — it is not (**S5-P-6**). **What IS pre-surface-checkable is only the PRESENCE of the
artifact, not its CORRECTNESS** — exactly what the architect's C7 row says, and I confirm it.

**Amended w1, for the record** (the §12.8 text itself is left as authored; this is the amendment,
per D2-R3's "amend or record why not" — I record it here rather than editing 12.8 so the leg-2 text
stays the leg-2 text): *C7 has no **pre-surface** implementation path. P-14 introduces a
**serve-time** path, which is strictly earlier than the post-deploy probe w1 named and strictly
later than the gate. C1–C6 remain pre-surface; **C9 joins C7 as served**; the honest split is now
three positions, not two.*

#### 12.10.5 The two postures — CONFIRMED, with marks

The architect graded both PROVISIONAL and asked me to confirm the clause unions (CH-06). **Both
unions are correct as written. Neither posture contains P-14, so neither inherits its NON-VIABLE
mark** — and the architect was right not to grade a P-14 posture on an unconfirmed member.

**Posture A — P-2 + P-6 + P-13 — CONFIRMED **VIABLE-WITH-CONDITIONS**.** Union confirmed:
**C2** closed by tuple atomicity **with the sole-source proviso** (F-5) · **C3 owed** (F-6; the
envelope set must be closed and enumerable) · **C5 owed** per publisher (F-3/F-4) · **C8 owed** per
rail (F-8) · C1/C4/C6 unchanged. **C9: not engaged** — no member introduces a serve-time component.
Two confirmations the architect flagged to me: the **G-18 ×2 does not cancel in the union** (correct
— C8 is per-publisher, and two members each minting a write path mint two), and the **hazard the
union misses** is correctly identified (P-13-by-identity vs P-12's git-history one-way, closed only
because the pair is environment-supplied per §12.9(iii)). **Conditioning clauses: C2 (proviso) + C3
+ C5 + C8.** This posture is the widest condition set on the slate and the architect says so.

**Posture B — P-5 + P-4 + P-13 — CONFIRMED **VIABLE-WITH-CONDITIONS**.** Union confirmed:
**C4-above-one-deck** (§12.5 P-5) · **C8 on the a8t rail** (F-8) · one **C6** fixture per side ·
the P-13 listability assertion. **C9: not engaged.** **G-18 ×1** is correct. **Conditioning clauses:
C4-above-one-deck + C8.** I add one clause the union table does not carry and that belongs to it:
**C1 is owed on the a8t side** — P-5's publisher has no ledger (§12.5 P-0/P-5), and "revocability is
absent on the a8t side" (the hazard row, CC-1, the sixth Q3 term) **is C1's consequence, not a
separate hazard**. **Posture B remains the exposure-minimal posture** — Contente-rail exposure
NONE-NEW — and that is unchanged by the addition.

**Neither posture is recommended.** Confirming a union is not ranking it; **F-PUBLISH is unanswered.**

#### 12.10.6 The `--config` sub-form (CH-02) — **MOVES NO MARK. CONFIRMED.**

The architect narrowed P-6's principal dissent by naming `wrangler --config` as an **existing**
carrier with **exactly one parser — wrangler's own** — dissolving the "two independent parsers"
objection, and flagged it to me with *"Marks unmoved."* **I confirm: no mark moves, and the reason
is clause-level.** P-6's conditioning clause is **C2**, and C2 requires **mutual** binding of
`⟨R_P, L_P⟩`. A wrangler config binds **account + project + root**; it carries **no field for the
ledger**. So the sub-form closes the *format-proliferation* half of the dissent and leaves **C2's
binding half exactly where it was** — the architect's own sentence (*"it has no field for `L_P`, so
C2's binding half still needs a seam"*) is correct and is the whole answer. **P-6 stays
VIABLE-WITH-CONDITIONS on C2 + C3 + C5 + C8.** The sub-form also does not touch C3, C5 or C8.
The composition claim carries its own UV-P at `§4 P-6` (adopted from the adversary), and I inherit
it rather than re-deriving: **the flag and the `account_id` resolution are receipted separately;
their composition is not.**

#### 12.10.7 The §12 forward claim on wipe-then-stage — **BOUND**

D2-R3 asks me to bind or mark-illustrative the §12.5 P-5 claim that *"the moment a **second**
non-Contente deck is minted, wipe-then-stage is a **mass-orphan event** for the first."* **BOUND, as
a falsifiable prediction with a named falsifier and horizon**, in the form CH-05 uses for PR-1..PR-4:

| field | value |
|---|---|
| **id** | **PR-RA-1** (requirements-analyst forward claim, bound at D2-R3) |
| **claim** | If a **second** non-Contente deck is published by the `publish-tenuta.sh`-shaped lane **without** that lane first acquiring a durable ledger + accumulating root, the first deck's capability URL **404s** — because the lane wipes `$DIST` before staging (S5-P-4) and its root then holds only the newest slug. |
| **falsifier** | A second non-Contente deck published by that lane while `https://tenuta-decks.pages.dev/nogqfo3pizvjhbdbxvvsvhdgt/` still returns **200**. Either the lane acquired an accumulating root (claim's precondition removed) or wipe-then-stage did not behave as read — **either outcome falsifies the claim as stated.** |
| **curator** | requirements-analyst (this seat) |
| **horizon** | **2026-10-03** (the epoch telos deadline) |
| **status** | **UNBOUND-BY-EVIDENCE, BOUND-BY-FORM.** No second non-Contente deck exists; the claim is a **prediction from a file-read of the script** (S5-P-4), not an observation. It is **not** a receipt and nothing downstream may consume it as one. |

**The §12.5 text stands as authored**; PR-RA-1 is the binding, recorded here.

#### 12.10.8 Self-assessment (D2-R3)

**MODERATE** (ceiling, not floor) per `self-ref-evidence-grade-rule` — same rite, same packet.
**RUNG = authored.** What I derived by my own hands at this leg: the re-probe of **S5-R-4** (zero
tracked serve-path matches; four absent paths), the **INV-08 / INV-09 registry and call-site
reads** (`invariants.js:80-81`; `run.js:224`, `:235`, `:274`, `:409`, `:418`), the `recommended`
semantics, and `probe.js:7`. **Additional hands, not rite-disjoint attestation.**

**Where this leg is weakest, stated plainly.** (1) **The NON-VIABLE mark on P-14 rests on a
structural argument, not on a probe** — I cannot probe a router that does not exist (**UV-P-7**),
and I have been careful to mark P-14 on *what the predicate can reach*, never on *what a deployed
router would do*. A reader who disagrees should attack the jurisdiction argument at 12.10.2, which
is where the mark actually lives. (2) **C9 is minted by the same seat that owns the predicate it
extends** — there is no independent check on whether C9 is the right ninth clause, and its RED-b arm
delegates to fence invariants this leg did not run. (3) **F-9 cannot be run pre-surface**, so C9
inherits C7's evaluation-time problem the moment it is written; I state that rather than presenting
C9 as a closure. (4) **Dissent 3 is not mine and I have not pre-empted it** — if the security
co-seat rules at **D2-R5** that a per-host router IS the per-Pages orphan gate C-3 forbids, that is
an **independent** NON-VIABILITY ground arriving on top of mine, and my C3 mark neither anticipates
nor depends on it.

---

**END — §12, requirements-analyst leg 2** (RC-1 applied 2026-09-05 per SECURITY-REVIEW-S5;
§12.10 appended 2026-09-05 per DELTA-2 D2-R3).
The slate is graded; F-PUBLISH is unanswered; T7 is unruled; the packet is unshipped and
gated at PT-03.

---

## §13 — Feasibility bands + seam cost (principal-engineer, leg 3)

**Leg 3 of S5's DESIGN half — the COMPRESSIBLE leg.** The architect ENUMERATED
(§1-§11); the requirements-analyst GRADED admissibility against a seven-clause
predicate (§12). This leg prices **what each admissible option costs to build**, in
bands. It does **not** answer F-PUBLISH, does **not** rule T7, does **not**
re-litigate Option B, does **not** schedule any DK item or tenuta-decks work, and
**writes no code and no branch**. Its output is a **feasibility band per option**, not
a build. **RUNG = authored.**

**On imprecision.** These are concept-altitude estimates. Initial concept-phase
estimates carry 4x-16x uncertainty that narrows only as an initiative moves through
requirements, design and implementation [EST:SRC-002 McConnell 2006]
[STRONG | 0.68 @ 2026-03-31]. Presenting a single-point number here would be a false
precision, so every entry is a **band with its dominant uncertainty named**. Structured
decomposition outperforms unstructured judgment [EST:SRC-007 Jorgensen & Shepperd 2007]
[STRONG | 0.68 @ 2026-03-31], and the decomposition used is the same five axes for every
option: **seam touch list → size band → test cost → migration → rollback → reserved
levers**.

**Which bands have a historical analogue and which do not** (the honest calibration
split, stated once):

- **Has an analogue ⇒ narrower band.** Account threading (§13.5) is a copy of a
  parameter chain that is already threaded end-to-end and already covered by a test
  asserting the exact surfaced string (S5-E-1). That is the canonical case: a familiar
  seam with a working precedent in the same file.
- **No analogue ⇒ widest band.** Everything that requires an N≥2 publisher set — C2
  binding, C3 scoping, C5 membership, the whole P-2/P-3/P-6/P-8 family — has **no prior
  instance anywhere in either repo**. The predicate at §12.1 was authored yesterday and
  is implemented nowhere (§12.2's "exists today?" column). Those bands are the boundary
  case and I decline to narrow them.

**Band vocabulary** (fixed for this section): **XS** <1 day · **S** 1-2 days ·
**M** 3-5 days · **L** >1 week. A band prices **engineering time to a landable,
tested change**. It does **not** price operator steps, credential acquisition,
governance rulings or security rulings — those are called out separately and are the
reason several options carry an unbandable half.

**Evidence discipline (inherited).** Every platform-behavior sentence carries a
**G-NN** frame anchor, an **S5-P-NN** receipt (§0.2), an **S5-Q-NN** receipt (§12.0),
an **S5-E-NN** receipt minted in §13.0 below, or a **UV-P** label in the frozen
`structural-verification-receipt` syntax. S5-E ids are **S5-local, leg-3 receipts, not
frame anchors** — same standing and same precedent as S5-P and S5-Q
(`…shape.md:1390-1397`). Self-assessment caps **MODERATE**.

### 13.0 S5-E probe register (minted here; read-only; no lever fired; no file written outside this append)

| id | Claim | Method | Receipt (verbatim / anchored) |
|---|---|---|---|
| **S5-E-1** | **`--project-name` is REACHABLE END-TO-END today** — CLI flag → `run_batch` → `run_office` → `_run_produce` → the surfaced command — **and the full chain is covered by a test that asserts the exact surfaced string.** | bash-probe (grep) + file-read | Chain: `batch.py:387` `project_name=args.project_name` → `:158` `project_name: str \| None = None` → `:205` `project_name=project_name` → `office_runner.py:404` → `:423` → `:204` → `:226`/`:297` `_surface_wrangler_command(deploy_root, project_name)` → `:152` `project = project_name or DECK_HOST_PAGES_PROJECT`. Test: `test_office_runner.py:178` passes `project_name="contente-decks"` and `:186-188` asserts `result.wrangler_command == f"wrangler pages deploy {tmp_path / 'deploy'} --project-name=contente-decks"`. |
| **S5-E-2** | **`--deck-manifest` reaches the GUARD ONLY; `--deploy-base` reaches BOTH the guard and the runner. The two halves of the ⟨root, ledger⟩ tuple are consumed on DIFFERENT call paths.** | bash-probe (grep) | `deck_manifest`: `batch.py:388` → `:159` → `:216` `_gate_wave_deploy_command(report, deploy_base=…, deck_manifest=…)` → `:221` → `:247` `assert_deploy_root_ready(Path(deploy_base), manifest_path=deck_manifest)`. **Zero occurrences of `deck_manifest` in `office_runner.py`.** `deploy_base` appears in both `:205` (→`run_office`) and `:216` (→ the gate). |
| **S5-E-3** | **`wrangler` 4.107.0 resolves the Cloudflare account from the config-file `account_id` key or the `CLOUDFLARE_ACCOUNT_ID` environment variable. There is no `--account-id` flag on the bundled CLI surface.** Consequence: an account cannot be surfaced INTO a `wrangler pages deploy` command the way `--project-name` is. | file-read (bundled CLI) | `node_modules/wrangler/wrangler-dist/cli.js` (wrangler `4.107.0`, S5-P-1/S5-P-10): 7 occurrences of `CLOUDFLARE_ACCOUNT_ID`, incl. `variableName: "CLOUDFLARE_ACCOUNT_ID"` and *"it is mandatory to specify an account ID, either by assigning its value to CLOUDFLARE_ACCOUNT_ID, or as \`account_id\` in your …file."* Grep for the literal `"account-id"` → **zero matches**. |
| **S5-E-4** | **Floodgates test inventory: 6 files, 74 tests.** The guard file holds **32** tests in 6 classes; **`TestLiveDeckHostWorkspace` (2 tests) runs the REAL deck-host workspace through the full gate** — an a8-side test whose fixture is the a8t-side live tree. | bash-probe | `test_deploy_root_guard.py` 32 tests / 379 lines; `test_batch.py` 16 / 533; `test_office_runner.py` 15 / 574; `test_state.py` 7 / 97; `test_mint_slug.py` 3 / 55; `test_accumulation_proof.py` 1 / 72. Classes at `test_deploy_root_guard.py:68,188,218,302,333,359`; `:368` `def test_real_workspace_passes_full_gate` → `assert_deploy_root_ready(_DECK_HOST_WORKSPACE / "public")`. |
| **S5-E-5** | **Zero account identifiers anywhere in `onboarding_walkthrough/`.** Corroborates **S5-P-8** by a third pair of hands. | bash-probe | recursive case-insensitive grep for `cloudflare_account\|account_id\|account-id` across `onboarding_walkthrough/` (excluding `__pycache__`) → **0 lines**. |
| **S5-E-6** | **`assert_root_hygiene` takes ONLY `deploy_root`; the ledger is parsed INSIDE `assert_manifest_superset` and is not in hygiene's scope. Both are exported public symbols.** This is the mechanical reason the C5 closure is not a one-line edit in place. | file-read | `deploy_root_guard.py:76` `def assert_root_hygiene(deploy_root: Path) -> None:`; `:162` `def assert_manifest_superset(deploy_root: Path, *, manifest_path: Path \| None = None) -> None:` with the ledger read at `:181`; `:45-53` `__all__` exports both names; `:246-258` `assert_deploy_root_ready` composes hygiene → headers → superset in that order. |

**No `wrangler` write, no project create, no deploy, no DNS, no mint, no SEND.** Every
probe above is a grep, a file read, or a line count. **No code was changed in any
repo.** `deck-host` was read-only on branch `s2/ws-f-ch01-reconciliation` — no stash,
checkout, reset or write; `bin/`, `src/` and `test/` were not opened there (the S5-E-3
read is of `node_modules/`, a build artifact, not a source tree).

---

### 13.1 THE BAND TABLE

**Side** = which side of the a8→a8t boundary the change lands on.
**P-11 is omitted: NON-VIABLE (G-29), prescribed — a refused class is not estimated.**
**P-9 is marked NOT-ESTIMATED: NON-VIABLE on C7 (§12.4/§12.5)** — but its seam is
recorded below because its seam is the finding.

| id | Side | Band | Dominant uncertainty |
|---|---|---|---|
| **P-0** | operator config (branch a) **or** a8t code (branch b) | **XS** (a) / **S-M** (b) | Which branch of §12.5's P-0 condition the operator takes — (a) a written not-a-publisher acceptance is hours; (b) giving the tenuta lane a durable ⟨L, R⟩ is days. The two differ by ~5 days and **the packet cannot pick** |
| **P-1** | a8t data (deck-host ledger + root) · a8 code **unchanged** | **S** | Not engineering. The band is small and the **governance ruling is the whole cost** — serving a non-Contente client deck from Contente's account and domain. A band cannot price that |
| **P-2** | **a8 code** (guard + CLI) · a8t data (per-tuple declaration) · operator config | **M-L** | **No analogue.** Where the ⟨root, ledger⟩ mutual declaration lives, and whether the binding must also cover `assert_wave_slugs_staged` (`deploy_root_guard.py:213`), which today takes the root but never the ledger |
| **P-3** | **a8 code** (predicate) · **a8t data** (all 10 ledger rows) · a8t code (mint lever) | **M-L** | **The backfill, not the filter.** The filter is a handful of lines; the 10-row mandatory backfill is a HARD PRECONDITION of the same class as the ledger's own `_backfill_2026-07-09` (§12.5), operator-gated and PV-against-live |
| **P-4** | contract-only (+ one conformance fixture per side) | **S** | How many of §5.3's five terms the operator sorts as COMMON. DP-2 has not sorted them, so the band scales with an unanswered question. The C6 fixture alone is XS |
| **P-5** | **a8t code only** (`deck-kit/bin/publish.mjs`) · zero a8 files | **M** (→ **L** if C4 is in scope) | Whether §12.5's C4 condition (wipe-then-stage is a mass-orphan event at \|live(L)\| ≥ 2) is in the first build or explicitly deferred with a written trigger. **NOT SCHEDULED — this is a price tag, not a plan** |
| **P-6** | **a8 code + a8t code + contract-only + operator config** | **L** | Envelope **placement** (a8 path / a8t path / third), which is directional across the boundary the epoch exists not to cross — an operator/governance call, not an engineering one. P-6 = P-4 + a schema + two independent parsers + P-2's guard work |
| **P-7** | **a8 code only** (4 files, one of which is an egress guard) | **S** for the account/project half · **UNBANDABLE** for the `DECK_HOST` half | Not size — **a security ruling this leg may not make and §12.5 explicitly declined to make.** Reporting a composite "M" would launder a blocked half into a schedulable number, so I do not |
| **P-8** | **a8t code** (deck-host `bin/`) · inherits P-1's or P-2's data cost | **M-L**, **not narrowable until S2 lands** | S2's landing date. `shape_P`'s source of truth is the file S2 is rewriting right now: `/^[a-z2-7]{26}$/` on `main`, `/^[0-9a-f]{32}$/` on the S2 branch (S5-Q-6). That is a calendar variable, not an engineering one |
| **P-9** | **operator config + DNS ONLY — zero code, either side** | **NOT ESTIMATED** (NON-VIABLE on C7) | n/a. See the hazard note at §13.2 P-9: its seam is *minutes and no PR*, which is exactly why it needs a written line |
| **P-10** | a8 code (a pin + a refusal) **or** contract-only | **XS-S** | Whether the pin is checked **pre-surface** (the publisher's first-ever `wrangler` invocation — a posture crossing, see §13.2 P-10) or merely surfaced as an operator instruction. Those are different programs and only the first is testable |
| **P-12** | **a8t data** (`brand-tokens/profiles/`) · a8t code (deck-kit reader) | **M** | Whether account ids in a design-tokens repo is acceptable (security question, routed not ruled at §12.5). If not, the coordinate file moves and **P-12 becomes P-6** — a band change of M → L driven by a non-engineering answer |
| **P-13** | a8 code and/or a8t code (both scripts already implement it) | **XS** per side | The same posture crossing as P-10. Plus §12.5's sharpening — pinning **identity** rather than **name** re-introduces an account id into a repo, which is the thing P-13's case-for was that it avoids (§13.2 P-13) |

**Read of the table.** The three cheapest admissible options (**P-4**, **P-13**,
**P-10**) are also the three the requirements-analyst marked **VIABLE** unconditioned
(§12.4). The most expensive (**P-6**, **P-3**, **P-2**) are the three carrying the
open C2/C3/C5 clauses. **That correlation is not a coincidence and it is not an
argument**: cheap-and-unconditioned options are cheap precisely because they add a
refusal and satisfy no clause (§12.5 P-13, P-4), so they answer F-PUBLISH's *mechanism*
question not at all. **Cost is not a tiebreaker between an answer and a modifier.**

---

### 13.2 PER-OPTION SEAM COST

Six fixed axes per option: **SEAM TOUCH** (files/lines, and which side of the a8→a8t
boundary) · **BAND** · **TEST COST** · **MIGRATION** (against the **10 ledger rows**,
S5-P-6/S5-Q-5, and the **9 live `public/` dirs**, S5-P-7/S5-Q-3) · **ROLLBACK** ·
**RESERVED LEVERS** (wrangler deploy, account/project create, DNS, slug mint —
**OPERATOR ONLY, never scheduled by this leg**).

**One statement that applies to every option and is made once.** The seven-clause
predicate at §12.1 **cannot be implemented as a pre-surface file predicate in full.**
C1-C6 are file-and-directory predicates a gate evaluates before surfacing a command.
**C7 is a post-deploy live probe with no pre-surface implementation path** (§12.8
weakness 1): it requires N×M HTTP GETs against hosts that only exist after the
snapshot is published. No option below carries a C7 line item, because there is no
pre-surface work to price. Where an option's exposure is a C7 exposure (P-9), the
answer is not a fixture — it is the mark the requirements-analyst already issued.

---

**P-0 — NULL.**
**SEAM TOUCH:** branch (a) **operator config only** — a written acceptance that
`P_tenuta ∉ 𝑷` (§12.5's condition (a)); **zero files, either side**. Branch (b) **a8t
code + a8t data** — a durable ⟨L, R⟩ for the tenuta lane, i.e. a committed root, a
committed ledger and a committed publish script to replace the `/private/tmp`
scratchpad the environment retires (S5-P-3, `RESUME-AFTER-RESTART.md:32`). **Zero a8
files in either branch.**
**BAND:** **XS** (a) · **S-M** (b). Dominant uncertainty: the branch choice, which is
the operator's.
**TEST COST:** (a) zero. (b) a8t-side only; zero a8 tests break, zero added. Under (a),
**C1 is unsatisfiable for `P_tenuta` by construction** — there is no ledger to be
fail-closed about — so F-1/F-2 are not merely unwritten, they are inexpressible for
that publisher.
**MIGRATION:** **zero.** 10 rows and 9 dirs untouched; the set-equality S5-Q-3 records
(9 = 9, both directions) is preserved.
**ROLLBACK:** (a) nothing to revert. (b) `git revert` in the a8t engagement repo.
**One-way step: none — PROVIDED the live slug `nogqfo3pizvjhbdbxvvsvhdgt` is REUSED,
never re-minted.** A re-mint orphans the live 200 (SLUG-1, `host_bundle.py:79-101`) and
no revert recovers it.
**RESERVED LEVERS:** none scheduled. Any re-publish of the tenuta lane is a `wrangler
pages deploy` — **operator only**.

---

**P-1 — ONE ROOT / ONE LEDGER.**
**SEAM TOUCH:** **a8t data** — `deck-host/config/deck-manifest.json` gains a passive
profile column; `deck-host/public/` accumulates. **a8t code** — `deck-host/bin/mint-slug.js`
if the publisher must write the column. **a8 code: UNCHANGED** — the column is passive
and `deploy_root_guard.py` never reads it. **operator config** — `--project-name` is
already a flag (S5-E-1), so no CLI work.
**BAND:** **S**. The mechanism is small. **The governance ruling is the cost and it is
not bandable**: P-1 serves a non-Contente client deck from Contente's account and
domain, which runs directly at DK-004's *"no default that points at another
organisation's project"*.
**TEST COST:** **F-3 becomes MANDATORY** and it **FAILS TODAY** (S5-Q-1). P-1 is
precisely the configuration in which two publishers share one root and one alphabet —
rot-trigger **R-4** realized *by design* rather than by accident — so the C5 membership
half is not optional under P-1, it is load-bearing. Existing tests that break: **none.**
`test_non_capability_dir_refused` (`test_deploy_root_guard.py:104`) already refuses the
base32 shape, which is the LOUD behaviour the architect and §12.5 both read correctly.
`test_real_workspace_passes_full_gate` (`:368`) stays green while set-equality holds.
**MIGRATION:** **zero if the column is passive** — this is P-1's genuine and
under-stated advantage. The moment the column is *read* by a predicate, P-1 is P-3 and
inherits P-3's full 10-row backfill. 9 `public/` dirs untouched.
**ROLLBACK:** `git revert` in **deck-host (a8t)**. **One-way step: any slug minted under
P-1 and deployed.** Reverting the ledger does not un-serve the snapshot; only a
re-stage + re-deploy does, and that is an operator lever.
**RESERVED LEVERS:** `wrangler pages deploy` (operator); slug mint (operator). No
account create, no project create, no DNS.

---

**P-2 — PER-PROJECT ROOT + LEDGER.**
**SEAM TOUCH:** **a8 code**, three sites. (1) `deploy_root_guard.py` — a **new** C2
binding predicate composed into `assert_deploy_root_ready` (`:246-258`) **before** the
superset check, so a cross-paired tuple refuses before C4 is evaluated (§12.5). (2)
`batch.py:335` (`--deploy-base`) and `:345` (`--deck-manifest`) stop being independently
overridable. (3) **the assertion has to live where BOTH halves are in scope** — and
S5-E-2 shows they are not: `--deck-manifest` reaches the guard only and never reaches
`office_runner`. So the binding site is `_gate_wave_deploy_command` (`batch.py:220-259`)
or `assert_deploy_root_ready` (`:246`), **never the runner**. Plus **a8t data** (a
per-tuple mutual declaration) and **operator config** (N tuples).
**BAND:** **M-L**. **No analogue anywhere in either repo.** Dominant uncertainty: where
the declaration lives, and whether `assert_wave_slugs_staged` (`:213-243`) — which today
takes the root but never the ledger — must also be bound.
**TEST COST:** **F-5 must be authored** (cross-paired tuple ⇒ REFUSE) and **two existing
tests break by design**: `test_explicit_manifest_path_overrides_default`
(`test_deploy_root_guard.py:285`) and `test_explicit_deck_manifest_param_overrides_default`
(`test_batch.py:326`) **both assert the current behaviour C2 forbids** — an arbitrary
ledger paired with an arbitrary root passes. They are not deleted; they are re-authored
as *"an override is permitted only when the pair mutually declares."* That re-authoring
is the concrete, countable test cost of C2 and it is **two tests in two files**.
F-1/F-2 are then parametrized over N tuples (the existing `:219`/`:230` bodies are the
template). **C7/F-7 stays post-deploy — not priced.**
**MIGRATION:** **zero row changes.** P-2 partitions by ledger **file**, not by row
**field** — this is its migration advantage over P-3 and it is worth the operator's eye.
The Contente tuple is already self-declaring: `deploy_root_guard.py:67-74` derives
`<root>/../config/deck-manifest.json`, which for `deck-host/public/` **is** the committed
ledger. Migration is writing that pairing down, not changing it. 9 dirs untouched.
**ROLLBACK:** `git revert` in **a8 (autom8y-asana)**, one repo, clean. **One-way step:
none in code.** Any deploy fired under a new tuple is a Pages snapshot and is operator-
reversible only by another deploy.
**RESERVED LEVERS:** `wrangler pages deploy` per tuple (operator); **project create** per
new tuple (operator); **account create** if a tuple crosses accounts (operator); **DNS**
if a tuple carries a custom domain (operator); slug mint per deck (operator). P-2 is the
option with the **widest reserved-lever surface** on the slate.

---

**P-3 — PER-PROJECT PREDICATE.**
**SEAM TOUCH:** **a8 code** — `deploy_root_guard.py:162-210` `assert_manifest_superset`
gains the scope filter (the `:201-202` revoked-exemption is where the new inclusion
predicate lands). **a8t data** — **all 10 rows** of `deck-host/config/deck-manifest.json`
gain a mandatory scope field. **a8t code** — `deck-host/bin/mint-slug.js` must write it.
**a8 CLI** — `batch.py` gains a scope selector.
**BAND:** **M-L**, and **the code is not the cost**. The filter is a handful of lines.
The cost is the **10-row mandatory backfill**, which §12.5 places in the same class as
the 2026-07-09 Option-B backfill the ledger records in its own `_backfill_2026-07-09`
key — operator-gated, PV-against-the-live-deployment (standing scar), and not
compressible by engineering.
**TEST COST:** **F-6 must be authored** (`null`/absent scope ⇒ REFUSE, never omit);
`test_unknown_status_treated_as_live_fail_closed` (`test_deploy_root_guard.py:277`) is
the exact shape precedent and its scope analogue is the fixture to copy. **The test that
goes red first, and for the right reason, is `TestLiveDeckHostWorkspace::test_real_workspace_passes_full_gate`
(`:368`)** — it runs the REAL ledger through the real gate (S5-E-4), so the instant the
filter lands against an un-backfilled ledger, the a8 suite fails on the a8t workspace.
**That is a feature: the suite already holds a live tripwire for exactly this migration.**
Also touched: `:219` `test_green_all_active_slugs_staged_passes` and `:244`
`test_revoked_slug_missing_is_exempt` need scoped fixtures.
**MIGRATION:** **10 of 10 rows, mandatory, before any deploy. Highest migration cost on
the slate.** 9 `public/` dirs unchanged (the dirs carry no metadata).
**ROLLBACK:** `git revert` in **a8** for the filter **and** in **deck-host (a8t)** for the
backfill — two repos. **One-way step: not the backfill (revertible) but a deploy fired
against a wrongly-scoped ledger.** That publishes a snapshot omitting live decks; it is
an R1 event, and the recovery is another operator deploy, not a revert.
**RESERVED LEVERS:** `wrangler pages deploy` (operator); slug mint per new deck
(operator). No account create, no project create, no DNS.

---

**P-4 — SHARED CONTRACT WITHOUT SHARED CODE.**
**SEAM TOUCH:** **contract-only.** A versioned contract artifact (placement is itself
open) plus **one conformance fixture per side, authored independently** — a8 side under
`tests/unit/automation/workflows/onboarding_walkthrough/floodgates/`, a8t side in
deck-kit/deck-host. **No publisher source file changes on either side.**
**BAND:** **S** for the contract text plus the a8-side fixture; the a8t-side fixture is
comparable a8t work. Dominant uncertainty: **how many of §5.3's five terms are COMMON**,
which DP-2 has not sorted. The **C6 fixture alone is XS** and is the obvious first move:
`deploy_root_guard.py:141-158` already byte-compares against `host_bundle.py:56`
in-repo, and S5-Q-4 shows both live copies at **128 bytes, byte-identical** — a contract
fixture makes that same comparison performable from the a8t side **with nothing
imported**.
**TEST COST:** **pure addition. Zero existing tests break.** Lowest test cost of any
option carrying mechanism.
**MIGRATION:** **zero.** 10 rows, 9 dirs untouched.
**ROLLBACK:** `git revert` on whichever repo holds the contract and the fixture.
**No one-way step. Lowest rollback risk on the slate.**
**RESERVED LEVERS:** **NONE.** P-4 is the only option here that touches no reserved
lever at all.

---

**P-5 — DK-004 AS THE a8t PUBLISHER.**
**SEAM TOUCH:** **a8t code ONLY** — `deck-kit/bin/publish.mjs`, which
**does-not-exist** (G-30, re-probed S5-P-9), plus a8t tests. **ZERO a8 files.**
**BAND:** **M** to DK-004's stated acceptance criteria (dry-run without network;
`--confirm` for live; never more than the one slug; account and project as parameters
with no cross-org default; served-bytes == frozen sha; the four guard headers; a 404
root; a ship receipt). The band is **compressed** by a working precedent —
`publish-tenuta.sh` implements most of it (S5-P-4) — and **widened** by that precedent
being ephemeral (S5-P-3), so "generalizing" starts from a re-read, not a port.
**→ L if §12.5's C4 condition is in scope**: wipe-then-stage satisfies C4 only while
`|live(L_P)| = 1`, and deck #2 makes it a mass-orphan event.
**NOT SCHEDULED.** Shape §7 forbids scheduling any DK-001..DK-005 item. **This band is
a price tag, not a plan.**
**TEST COST:** a8t-side, all new. **Zero a8 tests break; zero a8 tests added.**
**MIGRATION:** **zero** — P-5 never touches the Contente ledger or root.
**ROLLBACK:** `git revert` in **deck-kit (a8t)**. **One-way step: none in code**; the
live slug must be REUSED, never re-minted (SLUG-1 by analogy).
**RESERVED LEVERS:** `wrangler pages deploy` (operator — and DK-004's `--confirm` is
precisely the surfaced form of that lever); **project create** for a second non-Contente
project (operator); **DNS** for `decks.tenuta.io` (operator — and §12.5's P-9 analysis
marks that attach **SAFE**, because it enlarges one publisher's `H_P` rather than
serving another publisher's slugs).

---

**P-6 — DUAL PUBLISHER + CONTRACT-ONLY BRIDGE.**
**SEAM TOUCH:** **all four categories at once.** **a8 code** — an envelope reader plus a
**REFUSAL** on independent per-field override at `batch.py:335`/`:345` (§12.6's proviso:
an envelope that merely *populates* the flags leaves the mispairing reachable at the call
site). **a8t code** — DK-004's reader. **contract-only** — the envelope schema. **operator
config** — the envelope instances.
**BAND:** **L.** P-6 is strictly P-4 **plus** a schema **plus** two independent parsers
**plus** per-side conformance fixtures **plus** P-2's guard work. Dominant uncertainty:
**placement** — an a8 path, an a8t path or a third place — which is directional across
the boundary the epoch exists not to cross, and is a governance call.
**TEST COST:** everything P-2 costs (F-5 plus the two override tests re-authored) **plus**
per-side conformance fixtures **plus** the proviso fixture (independent per-field override
must **REFUSE**, not merely be discouraged). **C3 and C5 remain open under P-6** (§12.6),
so **F-3, F-4 and F-6 are still owed on top.** Highest test cost on the slate.
**MIGRATION:** **zero row changes** (P-6 partitions by envelope, not row field) —
**unless** it composes with P-3, in which case it inherits P-3's full 10-row backfill.
**ROLLBACK:** `git revert` in **a8 AND a8t**, and **the reverts must be ordered** so that
neither side is left reading a schema the other no longer writes. **P-6 is the only option
with a two-repo rollback ordering constraint**, and that constraint is itself a
cross-boundary coupling worth naming.
**RESERVED LEVERS:** as P-2 — the widest surface, plus the envelope's own placement.

---

**P-7 — FINISH THE PARAMETERIZATION IN a8 ONLY.**
**SEAM TOUCH:** **a8 code, four files.** (1) `office_runner.py:142`-adjacent — an account
seam beside `DECK_HOST_PAGES_PROJECT`. (2) `office_runner.py:145-153`
`_surface_wrangler_command` — signature and returned string. (3) `batch.py:355`-adjacent —
an `--account` flag threaded exactly as `--project-name` is. (4) **`link_on_play.py:58-62`
`DECK_HOST` from constant to parameter — which makes `contact_synthesis.py:305-313` a
set-membership check instead of an equality check.** The fourth is the one that matters
and it is **not the same kind of edit** as the first three.
**BAND:** **S** for the account/project half — see §13.5, it is a copy of a proven chain.
**UNBANDABLE** for the `DECK_HOST` half: that is a **security ruling** this leg may not
make and §12.5 explicitly declined to make. **I report S + a hard gate rather than a
composite M**, because a composite number would launder a blocked half into a schedulable
one.
**TEST COST:** account half is **additive** — `test_office_runner.py:164-193` already
asserts the exact surfaced string with `project_name="contente-decks"` (S5-E-1) and is the
template to extend. `DECK_HOST` half: the egress tests for `contact_synthesis` **were not
read this leg** (not on the READ list — see §13.6), so I name the cost and do **not** count
it. §12.5's three-part non-weakening condition (closed exact-netloc set; exact equality
preserved so userinfo/port refusals survive; per-publisher slug ownership) is **three
fixtures**, and the third is the one that would make the egress guard the fleet's **only**
implementation of C7 — at comment-post time, not serve time.
**MIGRATION:** inherits P-2's (zero rows) or P-3's (10 rows) per which shape it takes.
**ROLLBACK:** `git revert` in **a8 only** — single repo, clean. **But the `DECK_HOST` half
carries a REVERT ASYMMETRY that is not a git-level one: a widened egress allowlist that has
already permitted a post cannot be un-posted. The code reverts; the posted comment does
not.** That is P-7's genuine one-way step and it is not in the packet.
**RESERVED LEVERS:** `wrangler pages deploy` (operator). No create, no DNS.

---

**P-8 — DELEGATE PUBLISH TO deck-host.**
**SEAM TOUCH:** **a8t code** — `deck-host/bin/` gains a publish lever; deck-host already
carries `wrangler.toml` and `bin/`. **Inherits P-1's data cost** if it stages into
`public/`, **P-2's** if it stages elsewhere.
**BAND:** **M-L**, and **not narrowable until S2 lands.** A `shape_P` implemented in
deck-host needs a slug shape, and that file is being rewritten right now: `/^[a-z2-7]{26}$/`
on `main`, `/^[0-9a-f]{32}$/` via `src/slug/shape.js` on `s2/ws-f-ch01-reconciliation`
(S5-Q-6, `src/slug/shape.js` absent on `main`). Dominant uncertainty is a **calendar**
variable, not an engineering one.
**TEST COST:** a8t-side; inherits P-1's F-3 or P-2's F-5. Zero a8 tests break — **with one
exception worth naming, because it is the only place on this slate where an a8t-side change
breaks an a8-side test.** `TestLiveDeckHostWorkspace` (`test_deploy_root_guard.py:359-379`,
S5-E-4) reads the **live a8t workspace** as its fixture: if a deck-host publish lever
changes the shape of `public/` or `config/deck-manifest.json`, the **a8** suite goes red.
That coupling exists today and P-8 puts weight on it.
**MIGRATION:** none if it stages elsewhere; P-1's if it stages into `public/`.
**ROLLBACK:** `git revert` in **deck-host (a8t)**. **One-way step: none.** The governance
observation stands unchanged (a personally-owned remote, G-17, holding a publishing surface
for an account no credential on this machine can reach, G-35) — carried, not ruled.
**RESERVED LEVERS:** `wrangler pages deploy` (operator).

---

**P-9 — DOMAIN-ONLY SEPARATION. NOT ESTIMATED — NON-VIABLE on C7 (§12.4/§12.5).**
A refused option is not priced as work. **Its seam is recorded because its seam IS the
finding.**
**SEAM TOUCH:** **operator config + DNS ONLY. Zero code, either side.**
**HAZARD NOTE — the reason this belongs in a cost section at all.** Every other option on
this slate costs a PR, a review, a test and a rollback artifact. **P-9 costs a single
operator action in a dashboard.** Its realization time is minutes; it produces no diff, no
test and no revertible commit; and a DNS detach does not un-serve bytes already fetched.
**It is the only option on the slate that can arrive by accident**, which is exactly the
architect's stated worry and exactly why §12.5's testable line needs to be in front of the
operator **before** a low-friction attach happens: *safe attach — the new host serves only
slugs of the publisher that owns the project; unsafe attach — the new host serves a
snapshot containing another publisher's live slugs.*
**RESERVED LEVERS:** **DNS attach — operator only, never scheduled.**

---

**P-10 — ACCOUNT-AS-BOUNDARY.**
**SEAM TOUCH:** **a8 code** — a declared expected account plus a refusal; **or
contract-only** if the pin rides P-6's envelope.
**BAND:** **XS-S.** Dominant uncertainty is not size — it is **which program this is**.
**A POSTURE FINDING, stated because it is a real seam cost the packet does not carry:**
the floodgates publisher's entire discipline is *surface, never execute*
(`office_runner.py:146` — *"The exact reserved-lever command to SURFACE (never execute)"*;
`batch.py` module docstring — *"The CF `wrangler` deploy and the client SEND are RESERVED
operator levers — surfaced, never fired"*). **A pre-surface account check would be the
first `wrangler` invocation the publisher ever makes.** It is read-only (`whoami`), so it
is **not** a reserved-lever fire and it is precedented at §0 (S5-P-1) — but it crosses a
stated posture line and **should be ruled, not assumed**. Surfacing the pin as an operator
instruction instead is XS and crosses nothing; checking it pre-surface is S and crosses the
line. **Only the second is testable pre-surface, and that is the whole trade.**
**TEST COST:** additive; zero breaks. The subprocess-faking pattern already exists — the
suite fakes `curl` in `_fetch_served_bytes` (`office_runner.py:157`), and the office_runner
tests already assert `m["curl"].assert_not_awaited()` (`test_office_runner.py:192`). A
faked `wrangler whoami` is the same shape.
**MIGRATION:** **zero.**
**ROLLBACK:** `git revert` in **a8**. **No one-way step.**
**RESERVED LEVERS:** **account create** for a new profile (operator). `wrangler whoami`
is read-only and precedented; it is **not** a reserved lever.

---

**P-12 — DATA-DRIVEN DERIVATION from `brand-tokens/profiles/`.**
**SEAM TOUCH:** **a8t data** — `brand-tokens/profiles/{name}/` gains publish coordinates
(five dirs exist: `a8t fixture lotusun-brand lotusun-cream tenuta`, S5-P-11). **a8t code** —
a deck-kit reader; and `deck-kit/bin/build.mjs:30` `DEFAULT_PROFILE_ROOT` is a hardcoded
**absolute** path (G-27), which must be resolved before derivation can carry C2's binding
half. **a8 code: NOT REACHABLE** — Contente has no entry under `profiles/` (G-4), so
`P_contente`'s triple is not derivable from this substrate at all and P-12 is a **partial**
envelope by construction.
**BAND:** **M.** Dominant uncertainty: **whether account ids in a design-tokens repo is
acceptable** — a security question, routed not ruled (§12.5). If not, the coordinate file
moves and **P-12 becomes P-6**: a band change of **M → L** driven entirely by a
non-engineering answer.
**TEST COST:** a8t-side. The mandatory one is fail-closure: a profile dir **without**
coordinates REFUSES, one **with** them surfaces. Zero a8 tests break. `DEFAULT_PROFILE_ROOT`'s
absolute path means clean-checkout green requires the sibling present — a **pre-existing**
test-environment cost P-12 **inherits, not creates**.
**MIGRATION:** **zero against the 10 rows and 9 dirs.** The migration surface is instead the
**five profile dirs**, each of which needs coordinates or must REFUSE.
**ROLLBACK:** `git revert` in **brand-tokens AND deck-kit** (a8t, two repos). **ONE-WAY
STEP — and it is the sharpest one on the slate: committing a Cloudflare account id into a
repo is not undone by a revert. The id remains in git history.** That is the strongest
engineering argument for P-13's "keep account ids out of repos entirely" and it is a cost
no band captures.
**RESERVED LEVERS:** as P-5.

---

**P-13 — NO-ACCOUNT-MECHANISM.**
**SEAM TOUCH:** **a8 code** (a listability check before staging) and/or **a8t code**
(DK-004 already states it as an acceptance criterion). **Both existing scripts already
implement it** — `publish-tenuta.sh` exit 5 (S5-P-4), `publish.sh` exit 5 (S5-P-5). This is
a **re-derivation of a proven check, not an invention**, which is why the band is the
smallest on the slate.
**BAND:** **XS per side.** Dominant uncertainty: the **same posture crossing as P-10** —
`wrangler pages project list` would be the publisher's first wrangler invocation. Read-only,
precedented at §0 (S5-P-2), not a reserved lever, but a stated-posture crossing.
**TEST COST:** additive — one RED (project not listable ⇒ REFUSE, zero bytes staged) and one
GREEN. Same subprocess-faking pattern as P-10. **Zero breaks.**
**MIGRATION:** **zero.**
**ROLLBACK:** `git revert`, one repo. **No one-way step.**
**RESERVED LEVERS:** **none.**
**One cost the packet does not carry, surfaced here.** §12.5's P-13(b) sharpening — *"pin
the project's identity, not its name"* — is correct and it **does not change the band**
(still XS). **But it changes the seam**: an identity pin means an `(account_id, project)`
pair or a project id **in a repo**, which is precisely the thing P-13's own case-for is
that it avoids (S5-P-5 found one already sitting in a script comment). **P-13-by-name is
free and weaker; P-13-by-identity is equally cheap and re-imports P-12's one-way
git-history cost.** That trade is an operator call and it is priced nowhere in the packet.

---

### 13.3 THE C5-CONVERSE-CONTAINMENT GAP — closure estimate (ESTIMATE ONLY; NOT wave-1 work)

**Scope statement first, because it governs everything below.** The gap
(§12.2 finding 1 / §12.6 dissent 2) is in **a8 publisher code**. Closing it is a
**finding for the operator packet and the producer lane. It is NOT this epoch's wave-1
work, it is not proposed, it is not scheduled, and no branch or patch exists.** What
follows is a price tag with its shape named, nothing more.

**The gap, restated mechanically.** `assert_root_hygiene` (`deploy_root_guard.py:76-140`)
**never consults the ledger** — it tests shape, symlink-freedom and exact contents.
`assert_manifest_superset` (`:162-210`) checks **ledger → root only**. The composition at
`:246-258` runs hygiene → headers → superset and nothing tests **root → ledger**. S5-Q-1
proves the consequence: a well-shaped 32-hex dir **absent from the ledger passes the FULL
gate and the deploy command is surfaced.**

**Is it a one-line membership check against `live(L_P)`?** **The predicate is; the landing
is not — and the difference is the whole estimate.** The test itself is one condition
(`name in live_slugs`). But S5-E-6 records the obstruction: `assert_root_hygiene` takes
**only** `deploy_root` (`:76`), the ledger is parsed **inside** `assert_manifest_superset`
(`:181`), and **both names are exported in `__all__` (`:45-53`)**. So there are two landing
shapes and they cost differently:

| Shape | What it does | Cost | API break? |
|---|---|---|---|
| **(a) hoist** | Parse the ledger once in `assert_deploy_root_ready` (`:246`) and pass the live-slug set into **both** predicates | ~5-line check, but a **new signature on an exported symbol** | **YES.** `assert_root_hygiene(deploy_root)` becomes `assert_root_hygiene(deploy_root, live_slugs)`. Every ledger-free caller breaks — including `test_green_headers_plus_hex_slug_dirs_pass` (`test_deploy_root_guard.py:69`) and `test_slug_dirs_holding_exactly_index_html_pass` (`:155`), which call hygiene alone with no ledger at all |
| **(b) add a fourth predicate** | A new `assert_no_stray_live_dirs(deploy_root, manifest_path=…)` composed **after** the superset check at `:257` | ~30 lines including its own ledger read, plus fixtures | **NO.** Purely additive; every existing hygiene test keeps its signature and stays green |

**(b) is the cheaper shape and is the one I would build.** It duplicates the ledger parse
(the honest cost of not breaking an exported API), and that duplication is itself the thing
to weigh, not hand-wave.

**BAND: S (1-2 days).** Dominated **not** by the code but by two decisions: the ledger-parse
duplication in shape (b), and the **F-4 interaction** — C5 quantifies over `live(L_P)`, so a
**revoked-but-still-staged** dir must also refuse. That **upgrades revocation from a two-step
operator convention** (S5-Q-7: `bin/mint-slug.js:66` — *"Re-stage + re-deploy to 404 the old
URL"*) **into a gate-enforced property**. That is a behaviour change with an operator-visible
consequence and it is the reason this is S and not XS.

**TEST COST — two synthetic REDs, each with a no-defect GREEN twin (the discriminating-canary
shape, two-sided by construction, no defect injected into working code):**
- **F-3** — a directory that is a live slug of `P′`, well-shaped under `shape_P`, holding
  exactly `index.html`, staged into `R_P` ⇒ **REFUSE**. Fails today (S5-Q-1).
- **F-4** — a directory for an entry whose `status == "revoked"` ⇒ **REFUSE**. Fails today by
  the same mechanism.
- **Existing tests: zero break under shape (b); two break under shape (a)** (`:69`, `:155`).
- **`TestLiveDeckHostWorkspace::test_real_workspace_passes_full_gate` (`:368`) STAYS GREEN
  either way** — the live workspace is set-equal in both directions today (S5-Q-3: 9 = 9,
  `dirs NOT in live ledger: []`). **The fix therefore ships with a live positive control
  already on record**, which is unusually favourable and is worth the operator knowing.
- TDD's cost/benefit applies to the fixture work directly: authoring the negative twins costs
  15-35% additional development time and buys a 40-90% pre-release defect reduction
  [EST:SRC-005 Nagappan et al. 2008] [STRONG | 0.68 @ 2026-03-31]. For a fail-closed guard
  whose failure mode is a live client deck going dark, that trade is not close.

**MIGRATION:** **zero.** 10 rows and 9 dirs unchanged; the live workspace already satisfies
the stricter predicate.
**ROLLBACK:** `git revert` in **a8**, one repo, one commit. **No one-way step.**
**RESERVED LEVERS:** **none** — the change adds a refusal and surfaces nothing new.

**THE INDEPENDENT deck-host ROUTE — stated clearly, because it does not wait on the a8 lane.**
**S3's deck-host fence can check `dirs(public/) ⊆ slugs(live(config/deck-manifest.json))` —
converse containment — at the deck-host level, with ZERO a8 code touched.** deck-host holds
**both sides of that comparison in one repo**, and S5-Q-3 already computed exactly this
comparison by hand (`dirs NOT in live ledger: []`). That is an **a8t-side, import-free,
contract-free** realization of C5's membership half. **BAND: XS-S.**
**What it does and does not close, stated honestly:** it closes converse containment **for the
substrate of record** — the thing that actually holds the bytes. It does **not** close it for
the **a8 gate**, which would still surface a `wrangler` command for a root carrying a stray
live-shaped dir. **Two different fences at two different altitudes; neither substitutes for the
other; and the deck-host one is available now without touching a8 code.** That split is the
finding.

---

### 13.4 RESERVED-LEVER LEDGER — OPERATOR ONLY, NEVER SCHEDULED

Consolidated so the operator can read the whole slate's lever surface in one place.
**Nothing in this column is scheduled, proposed or fired by this leg.** Every `wrangler`
invocation made during S5 was read-only (`whoami`, `pages project list`) — §0, §12.0, §13.0.

| id | wrangler deploy | project create | account create | DNS | slug mint |
|---|---|---|---|---|---|
| **P-0** | yes (re-publish) | no | no | no | **no — REUSE the live slug; a re-mint orphans it (SLUG-1)** |
| **P-1** | yes | no | no | no | yes (per new deck) |
| **P-2** | yes (per tuple) | **yes (per tuple)** | **yes (if a tuple crosses accounts)** | **yes (if a tuple carries a custom domain)** | yes |
| **P-3** | yes | no | no | no | yes |
| **P-4** | **none** | none | none | none | none |
| **P-5** | yes (DK-004's `--confirm` is its surfaced form) | yes (2nd non-Contente project) | no | yes (`decks.tenuta.io` — SAFE attach per §12.5) | yes |
| **P-6** | as P-2 | as P-2 | as P-2 | as P-2 | yes |
| **P-7** | yes | no | no | no | yes |
| **P-8** | yes | no | no | no | yes |
| **P-9** | no | no | no | **YES — and DNS is the ENTIRE mechanism** | no |
| **P-10** | yes | no | **yes (per new profile)** | no | yes |
| **P-12** | as P-5 | as P-5 | no | as P-5 | yes |
| **P-13** | yes | no | no | no | yes |

**Two readings of this table.** (1) **P-4 is the only option with an empty row** — it is
the only mechanism-bearing option that cannot be realized by an operator action at all,
which is both its safety and its limitation. (2) **P-9's row is the inverse**: DNS is not
one lever among several, it is the **entire mechanism**, with no code, no PR and no revert
artifact anywhere in it (§13.2 P-9 hazard note).

---

### 13.5 THREE OF FOUR DIMENSIONS — end-to-end reachability, and the cost of the fourth

The architect's §2 seam map states three of four dimensions are already parameters
(S5-P-8). **Leg 3's job is to say whether "already a parameter" means "reachable
end-to-end today", and to price the fourth.** All three were traced by my own hands.

| Dimension | Reachable end-to-end **today**? | Chain (verified, S5-E-1 / S5-E-2) | Cost to use as-is |
|---|---|---|---|
| **`--project-name`** | **YES — fully, CLI to surfaced string, AND covered by a test asserting the exact string** | `batch.py:355` (flag) → `:387` → `run_batch:158` → `:205` → `run_office:404` → `:423` → `_run_produce:204` → `:226`/`:297` → `_surface_wrangler_command:145-153` → `:152` `project_name or DECK_HOST_PAGES_PROJECT`. Test: `test_office_runner.py:178` + `:186-188` | **ZERO** |
| **`--deploy-base`** | **YES — to BOTH the runner and the guard** | `batch.py:335` (flag) → `run_batch` → `:205` (runner) **and** `:216` `_gate_wave_deploy_command` → `:247` `assert_deploy_root_ready` | **ZERO** |
| **`--deck-manifest`** | **YES — but to the GUARD ONLY. It never reaches `office_runner` (zero occurrences).** | `batch.py:345` (flag) → `:388` → `run_batch:159` → `:216` → `:221` → `:247` `manifest_path=deck_manifest` | **ZERO to use.** But see the C2 note below — this asymmetry is the seam finding |
| **Account** | **NO — absent entirely.** Zero account identifiers anywhere in `onboarding_walkthrough/` (S5-E-5, corroborating S5-P-8) | — | see below |

**The C2 seam finding that falls out of the reachability trace.** `--deploy-base` and
`--deck-manifest` — the two halves of the ⟨root, ledger⟩ tuple C2 must bind — are **consumed
on different call paths** (S5-E-2). A binding assertion therefore has to be made where **both**
are in scope, and there are exactly two such places: `_gate_wave_deploy_command`
(`batch.py:220-259`) and `assert_deploy_root_ready` (`deploy_root_guard.py:246`). **It cannot
be made in the runner**, which never sees the ledger. That is a small fact with a real
consequence: any C2 implementation lands in the **guard/gate layer**, not the staging layer,
and inherits that layer's test file (`test_deploy_root_guard.py`, 32 tests) rather than the
runner's.

**COST TO THREAD THE FOURTH (account): S (1-2 days) for the surfaced-string half.**
The seam is **three edits**, and — uniquely on this slate — **it has a working analogue in the
same files**: `--project-name` is already threaded through the identical chain and is covered
by a test that asserts the exact resulting string (S5-E-1). This is the canonical-case
estimating situation, not the boundary case: a familiar seam with a proven precedent, so the
band is narrow and I am willing to commit to it [EST:SRC-002 McConnell 2006]
[STRONG | 0.68 @ 2026-03-31].
1. `office_runner.py:142`-adjacent — an account seam beside `DECK_HOST_PAGES_PROJECT`.
2. `office_runner.py:145-153` — `_surface_wrangler_command` signature and returned string.
3. `batch.py` — an `--account` flag threaded exactly as `--project-name` is at
   `:355`→`:387`→`:158`→`:205`→`:404`→`:423`.

**BUT — and this is the finding the packet does not carry — `wrangler` DOES NOT TAKE AN
ACCOUNT ON THE COMMAND LINE.** S5-E-3: wrangler 4.107.0 resolves the account from the
config-file `account_id` key **or** the `CLOUDFLARE_ACCOUNT_ID` environment variable, and the
bundled CLI surface carries **no `--account-id` flag** on this path. **Consequence: an account
parameter in floodgates cannot be surfaced INTO the `wrangler pages deploy` command the way
`--project-name` is** (`:153` returns
`f"wrangler pages deploy {deploy_root} --project-name={project}"`). It can only be surfaced as
an **env prefix** — `CLOUDFLARE_ACCOUNT_ID=… wrangler pages deploy … --project-name=…` —
which is exactly the shape `publish-tenuta.sh` already uses (S5-P-4: `CLOUDFLARE_ACCOUNT_ID="${…:-974c47a3…}"`
exported before the deploy) — **or** as a **pre-flight assertion** (P-10 / P-13), which is a
different program.

**Why that matters to DP-2 and not just to an implementer.** P-7's whole case-for is *"three
of four are already done; the remaining work is additive."* **The symmetry that case-for
implies does not hold at the wrangler surface: three of the four dimensions are CLI flags on
wrangler; the fourth is not a flag at all.** Threading it is still cheap (S), but the cheap
version produces an **env-prefixed surfaced string**, which is a different operator-instruction
shape than what `_wave_halt_banner` prints today. Whether that shape is acceptable is an
operator-surface question, and it is the reason P-10/P-13 (assert the account, never surface
it) are structurally cleaner answers to the account dimension than P-7 (parameterize it) —
**a structural observation, not a recommendation. This leg recommends nothing.**

---

### 13.6 WHAT I COULD **NOT** ESTIMATE, AND WHY

Four things, and the fourth is the largest.

**UV-P-5 (unknown account owner).** Every option that pins, declares or checks an account —
P-6, P-7, P-10, P-12, P-13 — has a code estimate I can give and an **operator estimate I
cannot**. I can price the edits; I cannot price the step of obtaining the credential that owns
`deck-host` and `decks.cntently.com`, because no probe available from this machine can confirm
or refute the candidate id (S5-P-2, S5-P-5, G-35). Under T7 reading (ii) that step is **on the
critical path before any build begins** (§5.2's ordering dependency, `…shape.md:793`), which
means the bands for that whole family are conditional on an unanswered first question. **A
band on the code is not a band on the work.**

**UV-P-6 (non-reproducible tenuta deploy).** P-0 branch (b) and P-5 both begin from
*"generalize `publish-tenuta.sh`"*, and that script lives in a `/private/tmp` scratchpad the
environment **retires** (S5-P-3, `RESUME-AFTER-RESTART.md:32`). It was read at S5 entry
(S5-P-4), so the estimate is grounded **today** — but I cannot estimate against an artifact
that may not exist when the work starts. **P-5's M assumes the script is re-readable or
cleanly re-derivable; if it is neither, P-5 moves toward L and I have no way from here to know
which.** That is the honest shape of the uncertainty and I decline to average it away.

**The T7 reading (which scopes S8 build vs contract).** T7 is operator-sovereign, homed at
PT-05, and **scopes S7/S8** (`…shape.md:1355-1366`). Under reading (i) the entire **a8-side
column** of §13.1 prices work nobody does; under reading (ii) the **a8t-side column** is the
wrong rail by construction. **I have banded both columns because I may not rule T7 — which
means roughly half of these estimates will turn out to have priced work that is never
performed.** That is not a defect in the estimate; **it is what a pre-ruling band costs, and
saying so is the only honest form it can take.** Presenting a single blended number across both
readings would hide the branch rather than price it.

**Two things I did not read, and therefore did not count.** (1) The `contact_synthesis` egress
test suite — it was not on this leg's READ list, so **P-7's `DECK_HOST` half carries a test cost
I have named and not counted**, and its S/UNBANDABLE split should be read with that hole in it.
(2) **Composition bands.** §12.6's union rule is a stated convention; §4.1's mechanism×modifier
space is larger than 13. **I banded per option and graded no pairing** — the same weakness the
architect declared at §11(3) and the requirements-analyst at §12.8(3), inherited a third time
rather than closed. Three legs have now named it and none has closed it; the operator should
read that as a standing property of this packet, not as an oversight repeated.

---

### 13.7 WHAT THIS LEG DID **NOT** DO

- **Did NOT write code, tests, or a branch.** Not one line, in any repo. Every artifact of this
  leg is this append.
- **Did NOT change any file other than this DP-2 append** (plus the single frontmatter field
  `legs_completed`).
- **Did NOT answer F-PUBLISH**, did **NOT** recommend, rank or prefer an option. Cost is not a
  ranking (§13.1, closing paragraph).
- **Did NOT rule T7.** Both readings stand; both columns are banded (§13.6).
- **Did NOT re-litigate Option B** (G-20), **did NOT re-enumerate the slate**, **did NOT issue
  or revise a viability mark** — §12.4's marks are the requirements-analyst's and are untouched
  here. Where I decline to price P-9 and P-11, it is **because of** their marks, not a
  re-derivation of them.
- **Did NOT schedule any DK-001..DK-005 item** (P-5's band is a price tag, stated as such twice)
  and **did NOT schedule tenuta-decks work**.
- **Did NOT propose the C5 closure as wave-1 work.** §13.3 is an estimate, explicitly routed to
  the operator packet and the producer lane.
- **Did NOT weaken any WS-GUARD invariant**, and did not propose weakening one. P-7's egress
  half is priced as UNBANDABLE-pending-security rather than given a number.
- **Did NOT run a reserved lever.** No `wrangler` write, no project create, no deploy, no DNS,
  no mint, no SEND. Every S5-E probe is a grep, a file read or a line count.
- **Did NOT touch S2's files or git state.** `deck-host` was read-only on branch
  `s2/ws-f-ch01-reconciliation`; no stash, checkout, reset or write; `bin/`, `src/` and `test/`
  were not opened there.
- **Did NOT ship the packet.** `status: proposed`. PT-03 gates. **RUNG = authored.**

---

### 13.8 SELF-ASSESSMENT (leg 3)

**Evidence grade: MODERATE (ceiling, not floor)** per `self-ref-evidence-grade-rule` — authored
inside 10x-dev about 10x-dev's own design surface. **Nothing here is self-attested as realized.**
An estimate is by construction an **estimative claim** and therefore **not SVR-bearing**
(`structural-verification-receipt` §1 trigger table row 6: *"Forecast, not platform fact; truth-value
determined by future events"*). The **bands carry no receipts and cannot**. What carries receipts is
the **substrate** the bands rest on — the S5-E register at §13.0 — and every platform-behavior
sentence in this section is anchored to one of those, to an S5-P/S5-Q receipt, or to a G-NN frame
anchor.

**What is STRONG underneath this leg and is not mine:** G-33, G-36, G-37, G-38/G-38b and the S1
eunomia VERDICTs. **What I derived by my own hands:** S5-E-1..S5-E-6 — **additional hands, NOT
rite-disjoint attestation** (frame §9.8; the same distinction the architect draws at §11 and the
requirements-analyst at §12.8 applies unchanged to me).

**Where this leg is weakest, stated plainly:**

1. **The bands are concept-altitude and I have not narrowed them beyond what the evidence supports.**
   Only **one** estimate on this page has a genuine historical analogue — account threading, which
   copies a chain that is already threaded and already tested (S5-E-1). **Every N≥2 band has no
   analogue at all**, because the predicate they implement was authored yesterday and exists nowhere
   (§12.2). Those are boundary-case estimates carrying the widest honest spread
   [EST:SRC-002 McConnell 2006] [STRONG | 0.68 @ 2026-03-31], and narrowing them here would be
   fabrication, not diligence.
2. **I priced engineering time only.** Governance rulings (P-1), security rulings (P-7), operator
   credential acquisition (UV-P-5) and S2's landing date (P-8) are each the **dominant** cost of the
   option they sit on, and **none of them is in a band**. For four of thirteen options the number I
   give is not the number that matters.
3. **Two costs named and not counted** — the `contact_synthesis` egress tests, and every
   mechanism×modifier composition (§13.6).
4. **The reserved-lever ledger at §13.4 is derived from option mechanics, not from an operator
   walkthrough.** If an option's realization needs a lever I did not infer from its mechanism, my row
   is incomplete rather than wrong. The rows I am most confident in are P-4's (empty) and P-9's (DNS
   is the whole mechanism); the rows I am least confident in are P-2's and P-6's, which are the
   widest and the most conditional.

**Rite-disjoint critic for this artifact, unchanged** (`…shape.md:464`): **security**
(security-reviewer, co-seated). **What I hand that critic from leg 3**, in priority order:
(1) **§13.5's wrangler finding** — the account is not a CLI flag, so any "parameterize the account"
option surfaces an **env-prefixed command or a pre-flight assertion**, and the security posture of
those two is not the same; (2) **§13.2 P-7's revert asymmetry** — a widened egress allowlist that has
already permitted a post **cannot be un-posted**, which makes the `DECK_HOST` half a one-way step in
a way `git revert` does not capture; (3) **§13.2 P-12's git-history one-way step** — an account id
committed to a repo survives its own revert, which is a concrete cost on the option the architect
flagged for scope creep with a security dimension.

---

**END — §13, principal-engineer leg 3.** Bands issued; F-PUBLISH unanswered; T7 unruled; no code
written; the packet unshipped and gated at PT-03.
