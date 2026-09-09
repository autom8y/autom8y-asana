---
id: ADR-ws-join-office-naming-path
date: 2026-09-08
status: PROPOSED — the recommendation is ARCHITECTURAL and is NOT a grant to build
initiative: name-the-client
wave: 0
sprint: S-04a (WS-JOIN-DESIGN)
rite: 10x-dev
seat: architect
deploy_class: C-INERT
ruling_served: C-15
adjacent_rulings: C-3, C-7, C-11, C-16, R-35, O-4
pii_limb: .ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.PII-LIMB.md
evidence_cap: MODERATE (self-ref per `self-ref-evidence-grade-rule`; every platform-behavior
  claim below carries an SVR receipt taken by THIS seat's own hands at an explicit ref)
---

# ADR — WS-JOIN: the office naming path

> **This ADR is one of TWO limbs.** The **PII disposition limb** is authored separately and
> concurrently by `compliance-architect` (security rite) at
> `.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.PII-LIMB.md`.
> That limb is **GOVERNING on every PII disposition named here.** This limb states, for each
> option, *what data crosses which plane*; it does **not** rule on whether that crossing is
> permissible. Where this document says "the PII limb governs," it means exactly that: the
> statement here is a **factual description of data movement**, never an adjudication.
> The main thread consolidates both limbs at PT-01.

---

## Status

**PROPOSED.** Nothing here authorizes a merge, a deploy, an apply, or a build.
The recommendation identifies **which option S-06 should be shaped around**; S-06 itself is
gated by PT-01 and, for the options that land in DEPLOY-CLASS A, by **R-35**.

---

## 0. The one-paragraph answer

WS-JOIN was framed as *"build a join that does not exist, without reintroducing a
deliberately-dropped identifier."* **Direct inspection at an explicit ref falsifies both halves
of that framing.** The join **exists in three places already** — authoritatively in the data
service (`get_business_by_guid_async`, called on *every* booking), durably in DynamoDB
(`ebi-forwarding-idempotency` obligation rows), and incidentally on the CloudWatch plane
(`resolve_office.py:259-265` emits the redacted guid, the raw phone and the business name on
**one line**). And `office_phone` is **not absent from the log plane**: it is emitted
**unredacted from five sites** in `resolve_office.py` at `origin/main` today. So the real
question is not *"how do we build the join"* but **"which locus do we resolve at, and what does
that locus cost us in deploy class."** The recommendation is
**Option C — read-time resolution through a two-stage port: an injectivity-asserted
prefix→guid registry derived from the denominator, then guid→name through the existing
data-service reader.** It touches the log surface **not at all**, carries the phone
**nowhere**, lands **C-INERT**, and **routes around O-4 for its own construction** — while
**surfacing** a live, unadjudicated exposure that belongs to the PII limb and the warden.

---

## 1. Context — what C-15 assigned, and what re-verification found

**C-15 (RATIFICATION, `:24`):** *"The bar is keyed on OFFICE GUID, and building the GUID ↔
`office_phone` join is OURS."* Right-hand column: *"Rejected: putting a phone number into
structured logs."*
**RATIFICATION `§3:44`:** *"the account model keys on `office_phone` at grain
`(office_phone, vertical, pipeline_type)`; one phone holds many rows. **Nobody holds the join.**"*
**RATIFICATION `§4:55`:** *"The GUID ↔ office_phone join does not exist. C-15 assigns it to us;
nothing has been built or verified."*

The bar clause WS-JOIN serves is *"attributed to them **by name**."* Note what that clause
actually demands: a **NAME**, not a phone. The phone entered this problem only as the *account
model's* key — it was never the thing the bar asks for. That distinction turns out to be the
whole design.

### 1.1 The three planes that were being read as one

The sprint charge cites `ebi_witness_ledger.py:21/:394` as *"THE PII control"* and attributes it
to DIAGNOSIS §6. Read at explicit refs, **these are three distinct controls on three distinct
planes**, and collapsing them is what made WS-JOIN look impossible:

| # | Plane | Control | Verbatim, read at an explicit ref | What it actually protects |
|---|---|---|---|---|
| **P1** | **CloudWatch, UPSTREAM of `resolve_office`** | `parser.py:125-126` (via DIAGNOSIS §6) | *"patient names and recipient addresses -- keep them out of structured logs (autom8y-log does not redact arbitrary fields)."* | **Patient identity.** This is the control DIAGNOSIS §6 names, and it is why the **1,252** are office-blind. |
| **P2** | **DynamoDB payload → git-tracked witness JSON** | `ebi_witness_ledger.py:21`, `:394` | `:21` *"office_phone in the payload are DROPPED (not hashed, not truncated —"* · `:394` *"office_phone are DROPPED (not hashed). The raw payload string is"* | **The rendered artifact.** A renderer-side refusal to carry email/phone/office_phone out of the store and into `.ledge/reviews/witness-ledger/*.json`. |
| **P3** | **CloudWatch, INSIDE `resolve_office`** | **NO CONTROL — five raw emissions** | `resolve_office.py:204`, `:214`, `:233`, `:248`, `:262` all pass `office_phone=` **unredacted** to `log.info`/`log.warning` | **Nothing.** The clinic's phone is already on the plane. |

**Consequence for the charge's framing.** DIAGNOSIS §6's control (P1) is about **patients**, and
WS-JOIN never touches it — closing the 1,252 is explicitly **out of scope** (frame §10 row 6).
`ebi_witness_ledger`'s drop (P2) is an **artifact-side** discipline that WS-JOIN's output should
**inherit and strengthen**, not trade. And P3 means the "rejected act" is **not a trade WS-JOIN
would make — it is a standing condition WS-JOIN discovers.**

### 1.2 "Nobody holds the join" — falsified three ways, at an explicit ref

| # | Holder | Evidence (own hands, `origin/main e292b616`) | Grain / limits |
|---|---|---|---|
| **J1** | **The data service** | `resolve_office.py:170` — `business = await data_read_client.get_business_by_guid_async(guid)`, then `:229` `get_business_by_phone_async(office_phone)` → `full_business.business_name`. **A first-class API, called on every single booking.** | Keyed on the **FULL** guid. Authoritative for the name. |
| **J2** | **DynamoDB `ebi-forwarding-idempotency`** | `book_contente.py:279` — `_obligation_attributes` writes `"office_phone": payload.get("office_phone")` as a top-level attribute **alongside** `"payload": json.dumps(payload)` (`:282`), and the payload carries `guid` (`ewl.py` Leg A keys on `payload["guid"]`). | `posture == "live"` **only** (`:250-256`: dry_run rows carry ZERO payload). Rows are **reapable** (`:267`). |
| **J3** | **The CloudWatch plane itself** | `resolve_office.py:259-265` — a **single** `log.info("office_resolved", guid=redact_uuid(guid), office_phone=full_business.office_phone, office_name=full_business.business_name, resolve_source=...)`. Prefix, phone and name on **one line**. | 90-day retention (measured). Only for offices that produced an event. |

**The join is not missing. It was never looked for at the right altitude.** What *is* genuinely
missing is a **prefix→full-guid** step: the plane carries only `redact_uuid`'s first-8-hex form
(`utils/redact.py:52-71`), and `get_business_by_guid_async` needs the full guid. That single
missing hop — **not a phone mapping** — is the actual content of WS-JOIN.

### 1.3 The mechanism that already solves the missing hop

`scripts/ebi_witness_ledger.py` **already builds a prefix→full-guid registry**, and already
guards it: `build_census_map` (`:244-302`) raises `RuntimeError` on a first-8-hex collision —
verbatim *"census prefix-injectivity VIOLATION"* — because *"a redacted disposition guid cannot
be attributed."* `resolve_disposition_guid` (`:305-328`) is the resolver, with a four-way
disposition (`activated` / `monolith_served` / `non_census` / `unresolved`) and the standing rule
*"NEVER guessed."*

**But the census has no name column.** `CensusOffice` (`:189-196`) is
`{prefix, full_guid, membership, engine, tier_ratified, h_fragile}`. Office names appear in that
file only as **code comments** (e.g. *"office-64803da3"* at `:171`). So the registry gets us
prefix→**guid**; the **name** must still come from J1.

---

## 2. ★ REFUTATION — "treat writing a mapping as the whole job" (HARD GATE 3)

The frame states any decomposition that treats WS-JOIN as *"write a mapping"* has missed the
constraint that makes it hard. **It is refuted here, in-artifact, on four independent grounds.**
Each ground is a property a mapping-writer never asks about, and each one alone changes the
answer.

**R1 — A mapping is not injective, and the non-injectivity is silent.**
The plane's key is 8 hex characters, not a guid. Two offices sharing a first-8-hex prefix would
**mis-attribute a booking to the wrong clinic** — a two-sided failure (one office falsely named,
another falsely silent) that produces a *plausible-looking* answer. `build_census_map:255-265`
already fails LOUD on this; a hand-written mapping has no such guard. **The injectivity assert is
a load-bearing part of the deliverable, not a nicety** — and its collision probability is a
function of the **denominator size**, so it must be re-asserted every time the denominator grows,
not once at authoring.

**R2 — ★ A mapping built from observations names only the offices that already worked. This
inverts the bar.**
This is the deepest reason and it is decisive. Any join derived from what the plane emitted
(J3, or a scrape of `office_resolved`) can only ever name an office **that produced an event**.
The realization predicate demands the opposite:

> *held across the C-3 denominator (**ALL active clients**, not one)*
> *TWO-SIDED — a failure for the SAME office also names it, with its kind, **never blank***

A **dark** office — the entire class WS-DARK exists for — emits **nothing**, so an
observation-derived mapping renders it **absent**, which is indistinguishable from *"not a
client."* **An absent row and a zero row are different claims, and the bar is built on the
difference.** Therefore the naming path must be **denominator-first**: the population comes from
WS-DENOM (S-05), and observations are *joined onto* it — never the reverse. A mapping-writer
builds the arrow backwards and the defect is invisible until a dark client is the one you were
asked about.

**R3 — The mapping is a PORT, not a table (C-16).**
C-16 binds the *integration point*, not just the source. A literal mapping welds today's source
into the call site. The naming path must be a **port** whose current adapter is the data-service
reader and whose successor is the DB status read — and, per frame §4.3, it must make three
specific mis-wirings **unrepresentable**, not merely discouraged. A table cannot refuse anything.

**R4 — ★ The locus decision sets the DEPLOY CLASS, and the class — not the engineering —
decides whether S-06 can start at all.**
A mapping-writer never asks *where* the resolution happens. But emit-time resolution touches
`services/**`, and a `services/**` push to `main` fires
`terraform apply -input=false -auto-approve` (SVR-2, inherited; SVR-6 own-hands). That places the
work behind **R-35**, whose own subject is **serving production right now** (SVR-7). Read-time
resolution touches `services/**` **not at all** and lands **C-INERT**. **The same feature is
either frozen behind an unadjudicated gate or shippable today, purely as a function of where a
function call lives.** That is an architecture decision, and it is the highest-leverage thing
this ADR produces.

---

## 3. The option space — enumerated by construction, not by listing

Per `option-enumeration-discipline`, the slate is generated from the problem's two independent
axes rather than assembled ad hoc, so that omission is **visible as an empty cell** rather than
invisible as an unwritten paragraph.

- **Axis 1 — LOCUS (where resolution happens):** EMIT-TIME (inside EBI) · INGEST-TIME (between)
  · READ-TIME (in a reader).
- **Axis 2 — REFERENT (what supplies the name):** the log line itself · the DDB store · the
  data-service business record · a static registry · an onboarding-minted token.

| | **log line** | **DDB store** | **data service** | **static registry** | **minted token** |
|---|---|---|---|---|---|
| **EMIT-TIME** | *(degenerate — the line naming itself)* | — | **A** (= live PR #2073) | — | **F** (mint side) |
| **INGEST-TIME** | **E** | **E** | **E** | **E** | — |
| **READ-TIME** | **B** | **D** | **★ C** (via registry) | **G** | **F** (read side) |

Cell **H** sits outside the matrix: it is the **rejected act** itself, enumerated so that it is
*refused on the record* rather than omitted.

### Legend for the four questions (asked of every option)

- **Q1 — Reintroduces `office_phone` onto the log plane?** (the rejected act)
- **Q2 — Deploy class** (§12: **A-APPLY** / **B-ECS** / **C-INERT**)
- **Q3 — Needs the O-4 operator ruling, or routes around it?**
- **Q4 — Survives C-16 extensibility** (adaptable to a DB-status-read successor, not welded)?

---

## 4. Options considered

### Option A — EMIT-TIME resolution inside EBI *(the charge's option 1)*

The pipeline resolves the office and the plane line **carries the name**. This is not
hypothetical: **PR #2073 (`autom8y`, OPEN, `8c9aa11f`, 6 files, +699/−7, all
`services/email-booking-intake/**`) implements exactly this**, adding `office_name`,
`chiropractor_guid` and `office_identity_kind` to five booking events, with a
`resolved`/`absent` KIND so the failure pole is never blank.

- **Q1 — Reintroduces the phone?** **NO.** It carries the **business name**, which is a
  different data class from the phone. (Its own body: the name is *"already logged unredacted
  one stage earlier on `office_resolved`"* — which this ADR corroborates at `:262`.) **But**: it
  operates on the plane where **P3's five raw `office_phone=` emissions already live**, so it
  *inherits* an exposure it does not create. **The PII limb governs.**
- **Q2 — Deploy class: `A-APPLY`.** All six files are `services/email-booking-intake/**`;
  `service-deploy-dispatch.yml:26-31` is an **allow**-list `paths: ['services/**']` (SVR-6),
  and the chain ends in `terraform apply -auto-approve` (SVR-2).
- **Q3 — O-4?** **Needs it** — not for the name, but because merging it is a `services/**`
  apply while **R-35 stands**, and R-35's own subject is **live in production** (SVR-7). So it
  needs **O-1** (what lifts R-35) *before* O-4 is even reachable. **Two operator words deep.**
- **Q4 — C-16?** **PARTIAL.** The naming is resolved by the pipeline's own data-service client,
  which is already not-Asana — but the resolution is **welded into stage code**, so a successor
  source means editing `services/**` again, i.e. another A-APPLY.
- **Strongest argument FOR (it is real):** it is the **only** option that puts the name on the
  **same line** as the event, so no reader, no retention window and no registry can ever
  desynchronise from it. It is also **already written, tested (468 lines) and reviewed** — the
  cheapest engineering on the board.
- **Decisive against:** it is **frozen behind two unspoken operator words** and cannot start.

### Option B — READ-TIME resolution from the log line *(the NULL option)*

Change nothing. `resolve_office.py:259-265` already emits prefix + phone + name on one line;
one Logs Insights query over `event="office_resolved"` grouped by
`guid, office_name` yields the table today.

- **Q1 — Reintroduces the phone?** **NO — but it READS it.** The `office_resolved` line the
  query targets carries `office_phone` unredacted (`:262`), so any operator or artifact touching
  this path handles the phone. **This is the reason Option B loses to Option C.** **The PII limb
  governs.**
- **Q2 — Deploy class: `C-INERT`** (zero code) — or **nothing at all**, since it is a query.
- **Q3 — O-4?** **Routes around it** for construction; **surfaces** it for the P3 exposure.
- **Q4 — C-16?** **FAILS.** It is welded to a **log line's key set** — the most brittle
  contract in the system, changeable by any `services/**` PR without a schema gate. There is no
  port here to plug a successor into.
- **Why it must still be enumerated:** it is the **true baseline**, and it is what falsifies
  *"nobody holds the join."* Any option must beat *doing nothing*, and several of the four
  mandated options do not obviously beat it.
- **Decisive against:** **R2.** It names only offices that emitted. A dark client is **absent**,
  not zero. It cannot carry the bar.

### Option C — ★ READ-TIME resolution through a two-stage port *(RECOMMENDED)*

The plane keeps the 8-hex prefix, untouched. A reader resolves:

```
  prefix(8hex)  --[ RegistryPort: injectivity-asserted, DERIVED FROM THE DENOMINATOR ]-->  full guid
  full guid     --[ NamePort:     current adapter = data-service business reader     ]-->  office name
```

The **denominator** (WS-DENOM / S-05, Asana-now behind a DB-status-read successor per C-16)
supplies the **population**; the registry is that population's **prefix index**; the name comes
from J1. **The phone appears at no step.** The prefix-injectivity assert of
`build_census_map:255-265` is carried forward as a **required property of `RegistryPort`**, and
re-asserted whenever the denominator changes.

- **Q1 — Reintroduces the phone?** **NO — and it never touches it.** It does not read
  `office_resolved`, does not read the DDB payload, and emits nothing. Its output artifact
  **inherits P2's drop discipline** (carry the name, drop the phone), which **strengthens** the
  existing control rather than trading it. **The PII limb governs the disposition; this limb
  asserts only the data-movement fact.**
- **Q2 — Deploy class: `C-INERT`,** by either landing:
  - **`autom8y-asana`:** `.ledge/**` is in the `paths-ignore` deny-list (**verified LIVE**,
    SVR-5) → deploy-inert. Reader **code** in `src/` would be **`B-ECS`** (asana's default), and
    that needs its own operator gate, which the shape already surfaces.
  - **`autom8y` repo-root `scripts/`:** **not** `services/**`, so `service-deploy-dispatch.yml`
    does **not** fire (SVR-6, two-sided). This is where `ebi_witness_ledger.py` already lives.
    **This is the cheapest landing and the one that reuses the injectivity assert in place.**
- **Q3 — O-4?** **★ ROUTES AROUND IT for its own construction.** O-4 exists because the frame
  believed WS-JOIN must trade the drop. It need not: this path carries no phone, widens no log
  line, and weakens no control. **It does not, however, dissolve O-4** — O-4 still owns the
  **P3 finding** this ADR surfaces (§6).
- **Q4 — C-16?** **★ PASSES, and is the only option that passes structurally.** Two named
  ports with the denominator injected, not assumed. The DB-status-read successor swaps
  `NamePort`'s adapter; nothing at the call site changes. The three §4.3 mis-wirings
  (ASR `activity`, `account_status`, `active_section_days`) are **unrepresentable** because
  `RegistryPort` is typed on `(prefix, full_guid)` and `NamePort` on `(full_guid) -> name` —
  none of the three can typecheck into either.
- **Decisive against (stated honestly):** it is a **second reader** of a fact the emitter
  already knows, so it can desynchronise (a renamed business shows the new name on old events).
  And it is bounded by the **90-day** retention measured at SVR-8 — it can name an office's
  events only inside that window.

### Option D — READ-TIME resolution off the DDB obligation rows

Read `ebi-forwarding-idempotency` directly: the `obligation|live` row holds `office_phone`
top-level **and** the guid inside the payload string — the join, materialized.

- **Q1 — Reintroduces the phone onto the LOG plane?** **NO.** But it **reads the phone from the
  store**, which is precisely what `ebi_witness_ledger.py:21/:394` **already refuses to carry
  forward**. Building on it would be **re-opening, from the other side, the exact drop P2
  exists to enforce.** **The PII limb governs — and this is the option most likely to be
  refused there.**
- **Q2 — Deploy class: `C-INERT`** (a script, same locus as the existing renderer).
- **Q3 — O-4?** **★ NEEDS IT, squarely.** This is the closest thing on the slate to the trade
  the frame feared.
- **Q4 — C-16?** **FAILS.** Welded to a DynamoDB item shape that is explicitly an
  idempotency-store implementation detail, whose payload attr is documented as **reapable**.
- **Decisive against:** `posture == "live"` **only** (`book_contente.py:250-256`: dry_run rows
  carry ZERO payload) — so it is blind to the entire suppressed/dry-run population, **and** the
  rows are reapable. **It cannot carry C-3, and it needs the ruling C routes around.**

### Option E — INGEST-TIME resolution (subscription filter → resolver → derived store)

A CloudWatch subscription filter on the intake log group feeds a resolver that writes a derived,
named store; readers query that.

- **Q1 — Reintroduces the phone?** **NO** onto the log plane; but the subscription **consumes**
  the P3 lines wholesale, so raw phones flow into a **new** durable store. **A materially larger
  PII surface than any other option. The PII limb governs.**
- **Q2 — Deploy class: `A-APPLY`.** A subscription filter, a resolver Lambda, an IAM role and a
  target store are **terraform** — the applying chain, and new standing infrastructure.
- **Q3 — O-4?** **Needs it,** and **O-1** first (it is A-APPLY under R-35).
- **Q4 — C-16?** **PARTIAL** — a resolver *could* be a port, but the seam would then be pinned
  by infrastructure rather than by a type.
- **Decisive against:** it buys **latency** (near-real-time naming) at the price of **new
  always-on infrastructure, a new PII-bearing store, and both operator words.** Nothing in the
  realization predicate asks for latency; it asks for a **bar**. Wrong currency.

### Option F — A derived, non-reversible office token minted at onboarding *(the charge's option 4)*

Mint a stable opaque token per office at onboarding; the plane carries the token; readers map
token→name out of band.

- **Q1 — Reintroduces the phone?** **NO** — by construction it is the *most* phone-free design
  on the slate. This is its genuine merit and it should be recorded as such.
- **Q2 — Deploy class: `A-APPLY` **and worse**.** It requires (i) an emit-side change in
  `services/**` to carry the token, (ii) an onboarding-side mint, and (iii) a **backfill** for
  every existing office. It is **A-APPLY plus a data migration**.
- **Q3 — O-4?** **Needs O-1 first,** and it additionally collides with the **R-A4 floor**:
  minting a durable business-of-record identifier is adjacent to *"business-of-record identity
  mints"*, on which frame §7 constraint 10 states *"No grant phrasing, however explicit, lifts
  it."* **This is the only option on the slate that touches the never-grantable floor.**
- **Q4 — C-16?** **PASSES in principle** — a token is the cleanest possible seam.
- **Decisive against:** **it solves a problem we do not have.** The identifier problem was never
  *"the office identifier is reversible"* — the plane already carries a **redacted**,
  non-reversible 8-hex prefix (`redact_uuid`), and that prefix is **already the join key** every
  existing instrument uses (`ebi_witness_ledger` Leg A and Leg B both). Minting a *second*
  non-reversible identifier alongside the one we have adds a migration, a floor collision and a
  dual-key era, and buys **nothing the prefix does not already buy**. **A token is the right
  answer to a question that was answered in 2026 by `redact_uuid`.**

### Option G — CENSUS-ONLY registry extension *(the charge's option 3, standalone)*

Add a **name** column to the census — i.e. extend `production.tfvars`'s allowlist entries (or a
sibling map) so `CensusOffice` gains `business_name`, and resolve prefix→name entirely from the
pinned file.

- **Q1 — Reintroduces the phone?** **NO.**
- **Q2 — Deploy class: `A-APPLY`.** `terraform/services/email-booking-intake/environments/
  production.tfvars` is **terraform under the applying path**, and that file is the *"ONE policy
  flip"* file (frame §10 row 4, `:154`). Editing it is emphatically not inert.
- **Q3 — O-4?** Routes around the PII ruling; **needs O-1** on deploy-class grounds.
- **Q4 — C-16?** **FAILS.** A hand-maintained name column in a tfvars file **is** the literal
  "write a mapping" that R1–R4 refute: it has no injectivity guarantee beyond the one assert, it
  drifts silently the moment a business renames, and it welds the name source to a
  **terraform variable** — the single least pluggable place in the system.
- **Decisive against:** it converts a **derived** fact into a **hand-maintained** one, and the
  census's own history proves the failure mode — the allowlist **outgrew its ratified spec** and
  only a **drift-guard test** caught it (`ewl.py:143-149`, OW-11 lineage). **Do not add a second
  hand-maintained column to a file that has already drifted once.**
  *(Note: option C **uses** the census mechanism — the injectivity assert and the four-way
  `resolve_disposition_guid` disposition — while **refusing** to make it the name source. That
  is the "extended rather than invented" reading the charge asked for, taken at the mechanism
  and not at the data.)*

### Option H — REFUSED: put `office_phone` on the plane as the join key

Enumerated so it is **refused on the record**, not silently omitted.

- **Q1 — Reintroduces the phone?** **YES. This is the rejected act, named by C-15.**
- **Q2 — `A-APPLY`. Q3 — needs O-4 and O-1. Q4 — fails C-16** (welds the join to PII).
- **REFUSED.** Per **HARD GATE 1**, no option requiring this trade may be recommended. It is
  recorded here **only** as the fixed point against which the other options are measured — and
  because §6 shows the trade has **partially already been made without a ruling**, which is a
  finding, not a licence.

---

## 5. ★ The comparison table — HARD GATE 2 discharged

**The deploy class is stated explicitly for every option, because the class — not the
engineering — determines whether S-06 can start.**

| Opt | Locus | Q1 phone → log plane? | **Q2 DEPLOY CLASS** | Q3 needs O-4? | Q4 C-16? | Can S-06 start today? |
|---|---|---|---|---|---|---|
| **A** | emit | NO (carries name) — *inherits P3* | **A-APPLY** | needs **O-1 then O-4** | PARTIAL | **NO — R-35** |
| **B** | read | NO — but **reads** it | **C-INERT** / none | routes around | **FAIL** | yes, but cannot carry the bar (R2) |
| **★ C** | read | **NO — touches it nowhere** | **C-INERT** (autom8y `scripts/`) · **B-ECS** if asana `src/` | **★ routes around** | **★ PASS** | **★ YES** |
| **D** | read | NO to log; **reads store** | **C-INERT** | **needs O-4** | FAIL | blocked on the ruling |
| **E** | ingest | NO to log; **new PII store** | **A-APPLY** | needs **O-1 then O-4** | PARTIAL | **NO — R-35** |
| **F** | emit+mint | **NO (strongest)** | **A-APPLY + migration** | **R-A4 floor** | PASS | **NO — R-35 + floor** |
| **G** | read | NO | **A-APPLY** (tfvars) | needs **O-1** | FAIL | **NO — R-35** |
| **H** | emit | **YES — REJECTED ACT** | A-APPLY | — | FAIL | **REFUSED** |

**The operative reading.** Four of eight options (A, E, F, G) are **A-APPLY and therefore frozen
behind R-35** — and R-35 is not a paperwork obstacle: its own subject image
`sha256:76c21a00…`, sole tag `salkin-safe-routing-20260905-90e0aa5a4937`, **is serving
production right now** (SVR-7, re-verified own-hands). One (H) is refused outright. Of the three
that can start today, **B fails the bar (R2)** and **D needs the very ruling the sprint was
sent to route around**. **Exactly one option is both startable and bar-carrying: C.**

---

## 6. ★ SURFACED, NOT ADJUDICATED — the P3 finding

**This is a finding, not a recommendation, and it is not this seat's to rule.**

At `origin/main e292b616`, `services/email-booking-intake/src/email_booking_intake/pipeline/
stages/resolve_office.py` passes `office_phone` **unredacted** to a structured-log call at
**five** sites:

| Line | Call | Event |
|---|---|---|
| `:200-206` | `log.info(...)` | `guid_resolved_via_data_service` |
| `:209-215` | `log.info(...)` | `guid_resolved_via_override` |
| `:229-234` | `log.warning(...)` | `business_lookup_failed` |
| `:248` | `log.warning("business_not_found", office_phone=office_phone)` | `business_not_found` |
| `:259-265` | `log.info(...)` | `office_resolved` — **and this line also carries `office_name` and the redacted guid** |

All five land in `/aws/lambda/autom8-email-booking-intake`, retention **90 days** (SVR-8).

**Why this is decision-relevant and cannot be left unsaid.** HARD GATE 1 asks whether the
recommendation *reintroduces* the phone onto the log plane. That question **presupposes the
phone is not there.** It is. Asserting "gate satisfied" without disclosing this would satisfy
the gate for the wrong reason, and would leave the next seat to inherit the same false premise
that made WS-JOIN look impossible. It also **changes the ranking**: it is the specific reason
Option B loses to Option C.

**Three things this is NOT:**

1. **It is NOT the 1,252 office-blind residual** (frame §10 row 6). That residual is
   *patient*-data-driven (P1, `parser.py:125-126`) and lives **upstream** of `resolve_office`.
   This finding is about the *clinic's* phone **inside** `resolve_office`. Different plane,
   different data class, different owner. **Adjacency is not inclusion, and this ADR does not
   annex it.**
2. **It is NOT an adjudication.** Whether a chiropractic clinic's published business line is
   personal data, whether `office_phone` in a business record is the same data class as
   `office_phone` in a lead payload, and what disposition follows — **all of that is the PII
   limb's**, at `.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.PII-LIMB.md`.
3. **It is NOT a cure proposal.** Curing it is `services/**` ⇒ **A-APPLY** ⇒ R-35, and folding
   a cure into this envelope would be **bundling** (frame §7 constraint 7: *"bundling =
   REFUSAL"*).

**Two corroborating signals that this is a real divergence and not a design intent:**
- The **same service** hashes the same field elsewhere: `book_appointment.py:151`
  `office_phone_hash=_redact_phone(ctx.office_phone)`; `forwarding_confirm/source_writeback.py:208,268`
  emit `office_phone_digits=len(...)` — a **count**, never the value.
- `utils/redact.py:1-18` states verbatim that *"Every log-emission site in a path that touches a
  UUID mailbox, capability-URL, client Gmail, or sender-auth token MUST route through these
  helpers"* — and the module **has no `redact_phone`** (recorded as live drift TENSION-010 /
  ABSTRACTION-005 in the service's own `.know/design-constraints.md:60-62`, and as
  *"semgrep-invisible"* in `.know/feat/pii-redaction.md:200-212`). **The gap is documented; the
  five call sites are not.**

**ROUTED TO:** the **PII limb** (governing) → **change-warden** (dre) + the **security seat**,
per DIAGNOSIS §12 PR-8's own assignment (*"change-warden + security seat"*). **Operator fork:
this is new matter for O-4's owner**, distinct from O-4 as framed. **This ADR takes no position
on it beyond naming it.**

---

## 7. Decision

**RECOMMEND Option C — read-time resolution through a two-stage port.**

### 7.1 The seam

```
                    ┌─────────────────────────────────────────────┐
   WS-DENOM (S-05)  │  DenominatorPort   -> Set[OfficeIdentity]   │   Asana-now / DB-later (C-16)
                    └───────────────────────┬─────────────────────┘
                                            │  supplies the POPULATION (C-3: ALL active clients)
                                            v
                    ┌─────────────────────────────────────────────┐
                    │  RegistryPort                               │
                    │    build(population) -> {prefix -> guid}    │
                    │    INVARIANT: prefix-injective, FAILS LOUD  │   (ewl.py:255-265 carried fwd)
                    │    resolve(prefix) -> Resolved | NonCensus  │
                    │                     | Unresolved            │   (ewl.py:305-328 disposition)
                    └───────────────────────┬─────────────────────┘
                                            v
                    ┌─────────────────────────────────────────────┐
                    │  NamePort                                   │
                    │    name(guid) -> OfficeName                 │
                    │    adapter NOW: data-service business reader │
                    │    adapter LATER: DB status read (C-16)     │
                    └─────────────────────────────────────────────┘
                                            ^
   OBSERVATIONS (log plane, UNTOUCHED) -----┘  join prefix -> row; NEVER the reverse (R2)
```

### 7.2 The contract — five properties, each falsifiable

| # | Property | Why it is required | How it fails loud |
|---|---|---|---|
| **P-1** | **Denominator-first.** The population is an **input**; observations are joined **onto** it. | **R2** — an observation-derived join renders a dark client *absent*, and the bar's whole point is that absent ≠ zero. | A client in the denominator with no observation renders **`0`**, never a missing row. |
| **P-2** | **Prefix-injectivity is asserted at build, over the denominator.** | 8 hex is not a guid; collision mis-attributes a booking **plausibly**. | `RuntimeError` at registry build — the `ewl.py:255-265` behaviour, carried forward verbatim in spirit. |
| **P-3** | **Unresolvable is a VALUE, never a guess.** `Unresolved` and `NonCensus` are distinct from `Resolved`. | `ewl.py:305-328`: *"NEVER guessed."* The `***` residual must stay visibly unnamed. | An unresolvable prefix renders its own kind; it never lands in an office bucket. |
| **P-4** | **Two-sided by construction (C-7).** The failure pole resolves through the **same** port on the **same** key. | Both poles carry the prefix — `terminal_decline` groups by `chiropractor_guid` (`ewl.py:26-30`); success will too if A ever lands. **One resolver, both poles, never blank.** | A failure with no name is a **defect**, not an empty cell. |
| **P-5** | **The phone appears at no step, and the output artifact inherits P2's drop.** | Strengthens the existing control instead of trading it. | An output artifact containing a phone fails its own schema. |

### 7.3 Landing (a recommendation to PT-01, not a decision this seat owns)

**Land the reader in `autom8y` repo-root `scripts/`, beside `ebi_witness_ledger.py`.**
`scripts/**` at the repo root is **not** `services/**`, so `service-deploy-dispatch.yml` does
not fire (SVR-6, two-sided) → **C-INERT**. It also puts the new ports **next to the injectivity
assert they inherit**, which is where the drift-guard discipline already lives.
The alternative — asana `src/` — is **B-ECS** (asana's `paths-ignore` is a **deny**-list; code
paths deploy) and would need its own operator gate, which the shape has already surfaced and
which this ADR does not attempt to grant. **D-1 in the shape reserves the repo choice for
PT-01; this is input to that, not a pre-emption of it.**

---

## 8. Rationale — why C over each of the others

- **over A:** A is better *engineering* and is already written. It is **not startable**: two
  operator words deep, behind a gate whose subject is live. C ships the same user-visible
  capability **today** at the cost of a second reader. **If O-1 lifts R-35, A and C are
  complements, not rivals** — A puts the name on the line; C holds the denominator. Recommending
  C **does not** argue against A, and §10 records that explicitly.
- **over B:** B cannot carry the bar (**R2**) and reads a raw phone. C is the same locus with a
  denominator and no phone.
- **over D:** D needs the ruling the sprint was dispatched to route around, is live-posture-only,
  and reads a reapable store.
- **over E:** buys latency nobody asked for; costs A-APPLY, standing infra, and a new PII store.
- **over F:** solves a problem `redact_uuid` solved already; adds a migration and collides with
  the **R-A4 never-grantable floor**.
- **over G:** it *is* the refuted "write a mapping," in the least pluggable file in the system,
  in a file whose census has already drifted once.
- **over H:** refused by HARD GATE 1.

**The acid test.** *Will this look obviously right in 18 months?* The thing that dates fastest
here is **Asana**, and C-16 says so out loud. C's answer is a `NamePort` whose adapter is
swapped and whose call sites do not move. The thing that would look worst in 18 months is a
hand-maintained name column in a terraform variable (**G**) or a second opaque identifier
running alongside the first (**F**). C is the only option whose **failure mode is a swap** and
whose **wrong answer is loud**.

---

## 9. Consequences

### Positive
- **S-06 is NOT R-35-blocked.** This is the sprint's highest-leverage output: PT-01 can shape
  S-06 as a **C-INERT** sprint that starts in Wave 0/1 rather than queueing behind an
  unadjudicated, unwatched gate with no forcing function (RATIFICATION §3, *"the single largest
  open risk"*).
- **O-4 is not on WS-JOIN's critical path.** The construction carries no phone. O-4 remains
  live — for the P3 finding (§6) — but it no longer blocks the build.
- The **prefix-injectivity assert** and the **four-way never-guessed disposition** are
  **reused**, not reinvented — the "extended rather than invented" reading, taken at the
  mechanism.
- **C-7 two-sidedness is structural**, not bolted on: one resolver, one key, both poles.
- WS-JOIN's output **strengthens** the existing PII posture rather than trading it.

### Negative
- **A second reader of a fact the emitter knows.** A renamed business shows its new name against
  old events. Acceptable for a naming bar; **not** acceptable if a future requirement needs the
  name *as of* the event — record that as the boundary.
- **Bounded by 90-day retention** (SVR-8, own-hands). Anything the bar needs beyond 90 days must
  come from the denominator side, not the plane.
- **A live dependency on the data service.** `NamePort`'s current adapter can be unavailable;
  `resolve_office.py:191-194` shows the pipeline treats that as terminal. The reader must
  degrade to `Unresolved` (P-3), **never** to a blank.
- **It does not name the `***` residual** and must not try — the cure is emission-side, which is
  the annexation frame §10 row 6 forbids.

### Neutral
- PR **#2073** is neither blessed nor blocked by this ADR. Its disposition is PT-01's + O-1's.
- The `redact_uuid` 8-hex prefix is **ratified as the join key of record** by this
  recommendation. If that ever changes, both C and every existing instrument change together.

---

## 10. ★ WHOSE RULING THE RECOMMENDATION NEEDS

The sprint asked for this by name. The answer has **three tiers**, and the distinction between
them is the point.

### Tier 1 — Rulings the recommendation does **NOT** need (it routes around them)

| Ruling | Why C routes around it |
|---|---|
| **O-4** — the PII ruling WS-JOIN transits | **For its own construction only.** C carries no phone at any step, widens no log line, weakens no control. O-4 was framed on the premise that WS-JOIN must trade the drop; C does not. **O-4 stays open for §6.** |
| **O-1** — what lifts R-35 | C is **C-INERT**. Options A, E, F, G all need O-1 first. This is precisely what choosing C **buys**. |

### Tier 2 — The ruling this ADR **transits and does not own**

| Ruling | Owner | What is owed |
|---|---|---|
| **The PII disposition of every option** | **`compliance-architect`**, at `.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.PII-LIMB.md` — **GOVERNING** | This limb states *what data crosses which plane*. It does **not** rule that any crossing is permissible. If the PII limb refuses C's artifact shape, **C changes and this limb defers.** |
| **★ The P3 finding (§6)** | **change-warden (dre) + the security seat**, per DIAGNOSIS §12 PR-8's own assignment; **operator fork — new matter for O-4's owner** | Five unredacted `office_phone` log emissions at `resolve_office.py`, live at `origin/main`. **Surfaced, not adjudicated, not cured** (curing = `services/**` = A-APPLY = R-35 = bundling). |

### Tier 3 — Rulings this recommendation **DEPENDS ON** but does not ask for

| Ruling | Why C depends on it |
|---|---|
| **O-2** — does "client" mean a CONTRACT or a BILLING state? | **P-1 makes the denominator an INPUT.** C is therefore *correct under either answer* and does not force O-2 — but the **bar** cannot close until O-2 is spoken, because the denominator's membership is undefined without it. C **isolates** the dependency; it does not remove it. |
| **C-16 / S-05** — the DenominatorPort | C consumes it. If S-05 lands a different shape, `RegistryPort.build()`'s input type changes and nothing else does. |
| **PT-01 / D-1** — which repo the reader lands in | Sets **C-INERT** (autom8y `scripts/`) vs **B-ECS** (asana `src/`). §7.3 is **input to** that decision, not a pre-emption of it. |

### The honest statement of what is NOT recommended

Per **HARD GATE 1**: **no recommended option reintroduces `office_phone` onto the log plane**,
and the recommendation therefore does **not** exit on a surfacing. **Option H is refused**, and
**Option D is not recommended precisely because it needs the trade**.
**However** — the gate's *premise* is falsified by §6, and that falsification is
**surfaced as operator fork matter** in Tier 2. The sprint does **not** exit on it, because the
finding does not change the recommendation; it **reinforces** it (it is why B loses to C).

---

## 11. Reversibility assessment (one-way doors)

| Decision | Door | Signoff required before S-06 |
|---|---|---|
| Read-time locus (C over A) | **TWO-WAY.** A reader can be deleted; A remains available if O-1 lifts R-35. **They compose.** | No |
| `redact_uuid` 8-hex prefix as the join key of record | **TWO-WAY but WIDE.** Already the de facto key of every instrument; C ratifies it. Changing it later changes C **and** `ebi_witness_ledger` **and** every operator query, together. | No — but **record the coupling** |
| Landing repo (`autom8y scripts/` vs asana `src/`) | **TWO-WAY**, different deploy class each way | **PT-01 (D-1)** |
| Adding a name column to `production.tfvars` (**G**) | **★ ONE-WAY.** A hand-maintained column in the *"ONE policy flip"* file becomes load-bearing and cannot be un-depended-on. **NOT RECOMMENDED.** | n/a — refused |
| Minting an onboarding office token (**F**) | **★ ONE-WAY.** A durable business-of-record identifier + a backfill. Collides with the **R-A4 never-grantable floor**. **NOT RECOMMENDED.** | n/a — refused |

---

## 12. Risks

| # | Risk | Sev | Mitigation |
|---|---|---|---|
| **RK-1** | The denominator (S-05) is not ready, and C is shaped against a guess | MED | **P-1 makes it an input.** Build `RegistryPort` against an explicit population type; the census is a **test fixture**, never the denominator. |
| **RK-2** | Prefix collision as the denominator grows | LOW→MED | **P-2.** The assert is not optional and is re-run per build, not once. |
| **RK-3** | A reader is built with no consumer — the live *"instrument-without-reader"* failure (frame M-4, five orphan branches) | **HIGH** | C **is** a reader. Its exit must name **who runs it and when**, or it joins the orphans. **Flag to PT-01: WS-JOIN and M-4 are the same question and should be shaped together.** |
| **RK-4** | The PII limb refuses C's artifact shape | LOW | The limb is **governing**; C's artifact schema is authored **after** it, not before. |
| **RK-5** | §6 is read as a cure proposal and someone opens a `services/**` PR | MED | §6 states three times that it is not. **Bundling = REFUSAL** (frame §7 c.7). |
| **RK-6** | C is read as an argument against PR #2073 | MED | §9 Neutral + §8: **they compose.** C is chosen on **startability**, not on merit. |

---

## 13. SVR receipts — taken by THIS seat, own hands, 2026-09-08

Per `structural-verification-receipt`. Grades per `evidence-grade-vocabulary`; **self-cap
MODERATE** per `self-ref-evidence-grade-rule`. **Refs re-resolved at MY start, not inherited.**

**★ SUBSTRATE RE-RESOLUTION (T-1, the stale-tree trap).** The charge states autom8y `origin/main`
was re-resolved to `a4bc0e39` at 2026-09-08T20:33Z. **At my start it is
`e292b61652a935c0f35e27c18c6075c2bb19ff3c`.** That is the **FIFTH move this arc**, not the
fourth. Working tree confirmed still `fix/wss-wildcard-scope-bypass-closure` @ `29e59e81`,
**352 dirty files**, not an ancestor of origin/main. **Every autom8y read below is
`git show e292b616:<path>`.** asana session repo: branch `main`, HEAD `d75bfe1a`,
`origin/main` `389c59bc`.

| # | Claim | Method | Anchor / result | Grade |
|---|---|---|---|---|
| **SVR-1** | The `:21`/`:394` DROP comments say what the charge says they say | `file-read` @ `e292b616` | 942 lines. `:21` — *"office_phone in the payload are DROPPED (not hashed, not truncated —"* · `:394` — *"office_phone are DROPPED (not hashed). The raw payload string is"*. **Both in comments.** Positive control: `grep -n "DROPPED"` → 1 hit; negative control `zzzz_no_such_token` **rc=1** | **[STRONG]** two-sided |
| **SVR-2** | The census holds **no name column** | `file-read` @ `e292b616` | `ewl.py:189-196` `CensusOffice = {prefix, full_guid, membership, engine, tier_ratified, h_fragile}`. Office names appear **only** in comments (`:171` *"office-64803da3"*). **This is why option G must invent data and option C must not.** | **[STRONG]** |
| **SVR-3** | ★ `office_phone` is **already emitted unredacted** onto the log plane | `file-read` @ `e292b616` | `resolve_office.py` **five sites**: `:204`, `:214`, `:233`, `:248`, `:262` — all `office_phone=` into `log.info`/`log.warning`. `:259-265` also carries `guid=redact_uuid(guid)` **and** `office_name=`. Positive control: `git grep -q "_redact_phone"` **rc=0** (the service *does* hash the field elsewhere — `book_appointment.py:151`); negative control `zzzz_no_such_token` **rc=1** | **[STRONG]** two-sided |
| **SVR-4** | ★ The join **already exists** in three holders | `file-read` @ `e292b616` | **J1** `resolve_office.py:170` `get_business_by_guid_async(guid)` + `:229` `get_business_by_phone_async(...)` → `full_business.business_name` · **J2** `book_contente.py:279` `"office_phone": payload.get("office_phone")` + `:282` `"payload": json.dumps(payload)` · **J3** `resolve_office.py:259-265` one line, three fields | **[STRONG]** |
| **SVR-5** | **asana** deploy fence (**O-3**), read **LIVE** | `file-read` @ asana `origin/main 389c59bc` | `test.yml:29-35` `paths-ignore: ['.ledge/**','.sos/**','.claude/**','.gemini/**','.knossos/**','.know/**.md']`; own comment `:20-22` *"Deny-list, not an allowlist, on purpose: an unlisted or newly-added path still triggers."* Positive control `.ledge` → **rc=0** at `:30`; negative control `zzz-nonexistent-path` → **rc=1** | **[STRONG]** two-sided |
| **SVR-6** | **autom8y** deploy trigger is an **allow**-list on `services/**`, and repo-root `scripts/**` is outside it | `file-read` @ `e292b616` | `service-deploy-dispatch.yml:26-31` — `on: push: branches:[main] paths: ['services/**']`, 457 lines. Enumeration of every `scripts/**` path-filter in `.github/workflows/*`: **only** `services/auth/scripts/**` and `terraform/services/otlp-collector/scripts/**` — **neither is repo-root `scripts/`**. Positive control `services/**` present **rc=0**; negative control `zzz-no-such-path/**` **rc=1** | **[STRONG]** two-sided |
| **SVR-7** | ★ R-35's own subject **is serving production** (PT-00's fact, **re-verified**) | `api-probe` (AWS, 2026-09-08) | `lambda get-function-configuration` → `CodeSha256 = 76c21a00bcb122b264e8623d181f70a081198f86faf5d1e75d4964df77600dfe`, `LastModified 2026-09-05T16:31:56Z` · `get-function` → `ImageUri …/autom8y/email-booking-intake@sha256:76c21a00…` · `ecr describe-images` → `"tags": ["salkin-safe-routing-20260905-90e0aa5a4937"]`, **sole tag**, pushed `2026-09-05T12:31:05-04:00`. **PT-00 fully corroborated own-hands, including the tag.** | **[STRONG]** |
| **SVR-8** | Log retention bounds any read-time option | `api-probe` (AWS, 2026-09-08) | `logs describe-log-groups` → `/aws/lambda/autom8-email-booking-intake` **retentionInDays = 90** (and 90 on all three siblings) | **[STRONG]** |
| **SVR-9** | PR **#2073** is live prior art for Option A | `api-probe` `gh pr view 2073` | OPEN, not draft, `8c9aa11f`, base `main`, mergeable **UNKNOWN**, **6 files all `services/email-booking-intake/**`**, +699/−7. Body: *"MERGE IS HELD"*, *"already logged unredacted one stage earlier on `office_resolved`"* | **[STRONG]** for state; **the `UNKNOWN` is reported as unknown** |
| **SVR-10** | The three PII planes are **distinct** | `file-read` | **P1** DIAGNOSIS `§6:194-196` quoting `parser.py:125-126` — *"patient names and recipient addresses -- keep them out of structured logs"* · **P2** `ewl.py:21,:394` · **P3** SVR-3. **DIAGNOSIS §6's control is patient data, NOT `office_phone` in `resolve_office`.** | **[STRONG]** |

### Controls that fired ON ME, recorded

**T-4 FIRED — a pipe laundered an exit code.** My first negative control was
`git grep ... | head -3; echo rc=$?`, which reported **rc=0** for a token that does not exist —
`head`'s status, not `git grep`'s. **Caught by re-running without the pipe: rc=1.** Every
control in the table above was subsequently taken **pipe-free** with `git grep -q`. Consistent
with the frame's T-4 (*"the strongest-evidenced trap on the board"*) and with the fence's
*"11/11 were caught by RE-RUNNING, 0 by inspection."*

**A control that MISSED, recorded.** My first ECR probe used repository name
`autom8-email-booking-intake` → `RepositoryNotFoundException`. **The AWS CLI returned rc=0 on an
error.** Resolved by reading `Code.ImageUri` off the Lambda itself rather than guessing the repo
name — the correct name is `autom8y/email-booking-intake`. **A zero from the first probe would
have been UNTAKEN.**

### O-3 per-PR fence — discharged for this sprint

**Changed paths, this sprint:** exactly one —
`.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md`.
**Asserted against the LIVE deny-list** (SVR-5, read at asana `origin/main 389c59bc`, not
assumed): `.ledge/**` is present at `test.yml:30`. **Positive control fired (rc=0); negative
control rc=1.** ⇒ **`Test` is suppressed ⇒ `satellite-dispatch` does not fire ⇒ no ECS roll.**
**DEPLOY-CLASS C-INERT, verified live, not inherited.**

### UV-P ledger

```
[UV-P: whether the clinic's `office_phone` in a BusinessRecord is the same data class as the
 `office_phone` inside a lead booking payload | METHOD: deferred-to-PII-limb |
 REASON: a data-classification question owned by compliance-architect at
 ADR-ws-join-office-naming-path-2026-09-08.PII-LIMB.md; this limb states only the data-movement
 fact, never the disposition]

[UV-P: whether the five `resolve_office.py` raw emissions are a deliberate accepted posture or
 undocumented drift | METHOD: deferred-to-change-warden + security seat |
 REASON: the service's OWN `.know/design-constraints.md:60-62` records the redact-module phone
 gap as TENSION-010 drift, but names `book_appointment.py:33-42` and NOT these five sites. I did
 not locate a ruling either way and I will not infer one]

[UV-P: whether `office_resolved` is emitted on the DECLINE/park poles as well as the success
 pole | METHOD: deferred-to-S-06-build | REASON: I read the stage source, not a live log sample.
 `terminal_decline` provably carries `chiropractor_guid` (ewl.py:26-30), so the PREFIX is
 two-sided — which is what P-4 actually requires. The stronger claim that the NAME is two-sided
 pre-diff is NOT taken here]

[UV-P: the live membership of the C-3 denominator | METHOD: deferred-to-S-05 + operator O-2 |
 REASON: "client" as contract-state vs billing-state is unanswered (RATIFICATION §4.3). P-1 makes
 the denominator an input precisely so this ADR is correct under either answer]

[UV-P: whether any consumer will actually run the reader | METHOD: deferred-to-PT-01 |
 REASON: RK-3 — frame M-4 records five orphan branches proving instrument-without-reader is a
 LIVE failure in this codebase. C is a reader; naming its consumer is PT-01's shaping call]
```

---

## 14. Exit criteria

### Realization predicate — VERBATIM

> "Verified-realized" = the operator's ratified receipt (C-7), carried VERBATIM into every
> sprint's exit criteria: a LIVE attributed booking naming that office, TWO-SIDED — a failure
> for the SAME office also names it, with its kind, never blank — held across the C-3
> denominator (ALL active clients, not one). NOT "PRs merged". DONE IS A BAR, NOT A DATE.

**ADVANCES:** clauses **(a)** and **(b)**. Both poles require the office to be NAMEABLE; this
ADR decides **how**, and its answer is that **S-06 is NOT R-35-blocked**.
**DOES NOT DISCHARGE:** all four clauses. **An ADR names no office and produces no booking.**

### Hard gates

| Gate | Status |
|---|---|
| **1** — no recommended option reintroduces `office_phone` onto the log plane | **PASS.** C touches it nowhere. **H refused**, **D not recommended** for needing the trade. The gate's *premise* is falsified by §6 and that is **surfaced** as Tier-2 operator matter; the sprint does **not** exit on it, because it does not change the recommendation. |
| **2** — deploy class stated explicitly per option | **PASS.** §5, all eight. **Four of eight are A-APPLY and frozen behind R-35; C is C-INERT.** |
| **3** — "treat writing a mapping as the whole job" refuted in-artifact | **PASS.** §2, four independent grounds (R1 injectivity · **R2 denominator inversion** · R3 port-not-table · R4 locus-sets-class). |

### Entry criteria

| Criterion | Status |
|---|---|
| `:21`/`:394` read at an explicit ref, quoted from what was actually read | **MET.** SVR-1, `git show e292b616:scripts/ebi_witness_ledger.py`, two-sided control. **Refs re-resolved at my start — `origin/main` had moved a FIFTH time.** |
| The 1,252 residual is ADJACENT and NOT ANNEXED | **MET.** §6 point 1 names the boundary explicitly. DIAGNOSIS §6's own *"cheaper, non-coupled alternative"* (`redact_uuid(ctx.to)` on `intake_classified`) is **explicitly handed to "the design lane"** — **this seat records it and REFUSES it**: it is emission-side, `services/**`, A-APPLY, and out of scope by frame §10 row 6. **Routed, not taken.** |

### Handoff

| To | What |
|---|---|
| **PT-01** (main thread) | Consolidate with the PII limb. Decide **D-1** (landing repo → deploy class). **Shape S-06 as C-INERT** if C survives the limb. **RK-3: shape WS-JOIN's reader together with M-4.** |
| **`compliance-architect`** | This limb defers to yours on every disposition. **§6 is the live matter.** |
| **`change-warden` (dre)** — this sprint's critic | The P3 finding (§6) is yours by DIAGNOSIS §12 PR-8's own assignment. **It is surfaced, not cured.** |
| **Operator** | **New matter for O-4's owner** (§6) — distinct from O-4 as framed. **O-1 remains the gate on options A/E/F/G.** **O-2 remains the gate on the denominator, which C isolates but does not remove.** |

---

*Evidence cap **MODERATE** per `self-ref-evidence-grade-rule` (a design seat attesting its own
design). Every platform-behavior claim carries an SVR receipt taken at an explicit ref by this
seat; the two-sided controls are recorded, **including the two that fired on me**.
Nothing here authorizes a merge, deploy, or apply.*
