---
id: ADR-ws-denom-seam
title: WS-DENOM — the extensible denominator seam (C-16), and the consumption-shape ruling that fixes S-06's deploy class
status: PROPOSED — design only; nothing merged, deployed, or applied
date: 2026-09-09
initiative: name-the-client
wave: 1
sprint: S-05 (WS-DENOM-SEAM)
rite: 10x-dev
author: architect (10x-dev, co-seated)
session_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
refs_resolved_own_hands_at_start:
  autom8y-asana origin/main: 389c59bc9c95234df668d817a894014dd0b79a1
  autom8y      origin/main: 4e0b41f9d872a9d256c5a6b617b7ab2af4fe55ac
self_cap: MODERATE
supersedes: nothing
consumes:
  - .sos/wip/CUSTODY-name-the-client-wave0-register-2026-09-08.md A9 (PT-02), A10 (PT-01), A11 (O-8/O-9)
  - .ledge/decisions/RATIFICATION-client-outcome-decision-space-2026-09-08.md (C-1..C-18)
  - .know/telos/name-the-client.md (the bar)
---

# ADR — WS-DENOM: the extensible denominator seam

> **Scope fence.** DESIGN ONLY. No code, no merge, no deploy, no apply. This ADR
> writes one file, in `.ledge/decisions/`, which is verified deploy-inert in §1.4
> against the live fence text rather than assumed.

---

## §0 READ THIS FIRST — the two things that changed the design

**(0a) The predicate is not merely undefined — TWO INDEPENDENT LANES REACHED IT AND BOTH
DECLINED TO INVENT IT.** This is the ADR's framing, not a footnote.

- This initiative's PT-02 found that clause (c) quantifies over *"ALL ACTIVE CLIENTS"* and
  **no artifact contains that set, its cardinality, or the predicate that would generate it.**
- Independently, the `identity-activity-substrate` lane ships its scheduled roster walk with
  **`walk_enabled=False`**. `autom8y-data :: src/autom8_data/core/config.py:204-206` gives the
  reason, and **the reason is a CONJUNCTION**:
  **"FALSE by default: the roster is an un-ruled population AND the ledger is append-only.
  Enabling is a separate operator lever."**
  *[**`[OWN-HANDS]`** — read to its end at `autom8y-data` origin/main by this seat. An earlier
  draft of this ADR carried the fragment `"…an un-ruled population…"` anchored at `:203-205`.
  **That anchor was CORRECT for the truncated quote** — the sentence continues onto `:206`,
  outside the cited range — **so the line-anchor discrepancy is the FINGERPRINT of the
  truncation, not a second defect.** The peer lane caught and disclosed its own ellipsis.]*

> **★ THE TWO LANES DECLINED FOR DIFFERENT REASONS, AND THIS ADR MUST NOT MERGE THEM.**
> **This lane's ground is UNFALSIFIABILITY:** no artifact holds the set, its cardinality, or the
> predicate that would generate it, so no answer can be checked.
> **The substrate lane's ground is IRREVERSIBILITY:** its ledger is append-only, so **a wrong
> population cannot be un-written.**
> Same action, **independent cost functions, disjoint corpora.** That is **two observations, not
> one reason echoed twice** — and merging them into "same wall, same refusal" would count a single
> observation twice and inflate the corroboration grade.

> **★ AND THE CONJUNCTION RELEASES THIS SEAM RATHER THAN BINDING IT.** Append-only is what makes an
> un-ruled roster *disqualifying* rather than merely uncomfortable. **S-06's store is not
> append-only:** it writes a dated artifact under `scripts/` (§1), nothing acts on it, and a wrong
> snapshot is supersedable by a later one plus an erratum. **So S-06 has an option the substrate
> lane does not have, and takes it knowingly rather than inheriting the caution by analogy** — an
> approximate denominator here is a **v1 that refines**, not a permanent record of a wrong
> population.
>
> **The discipline that survives the release:** mutability makes a wrong population safe to
> **WRITE**, not safe to **MISREAD**. Therefore the artifact carries `grain`,
> `membership_predicate` and `quantifier` as explicit **`UNRULED`** fields, and every member
> carries **GREEN · RED · UNOBSERVED(reason)** — never mere absence. **A seam that silently picked
> a population would be the first seat to fail the test both lanes passed.**

**(0b) The seam is not greenfield.** A structurally identical program already lives at the exact
locus this ADR recommends — `autom8y` repo-root `scripts/ebi_witness_ledger.py` — reading ONE of
the two live booking-enablement authorities, already carrying a named-exclusion field and a binding
PII posture. WS-DENOM is **a second adapter plus the missing reconciler**, not a new system. §1.2.

---

## §1 ★ THE CONSUMPTION-SHAPE ANSWER, AND S-06'S DEPLOY CLASS

### §1.1 The answer, stated plainly

> ## **(i) — AN ARTIFACT THE DENOMINATOR EMITS.**
>
> **The reader consumes a dated, persisted, named-exclusion-carrying denominator artifact.
> It does NOT make a live call into asana, and it does NOT import asana in-process.**
>
> ## **⇒ S-06's reader lands in `autom8y` repo-root `scripts/` = C-INERT.**

**A live call into asana DOES occur — inside the Asana adapter, one layer below the reader's
boundary.** PT-01(c)'s trichotomy conflates two different questions:

| question | answer |
|---|---|
| Does *anything* in WS-DENOM make a live call into asana? | **YES** — the Asana adapter does. |
| Does **THE READER** consume the denominator *via* a live call? | **NO** — it consumes the emitted artifact. |

The fork is scoped to the reader's consumption boundary, and at that boundary the answer is (i).
Nothing about the adapter's internals reaches S-06's locus, because the artifact is the interface
between them. **This is the whole point of having a seam.**

### §1.2 Why (i) — derived on the SUBSTRATE axis, three independent reasons

PT-01(c) refused to fix S-06's class because *"deciding the landing on the deploy axis while the
substrate axis is unmeasured is the exact error S-04b self-corrected on."* Accordingly **every
reason below is substrate-side. The deploy class is a CONSEQUENCE, derived last, in §1.3.**

**REASON 1 — FALSIFIABILITY. The mission's own bar forces persistence.**
Clause (c) is *"held across the C-3 denominator: ALL ACTIVE CLIENTS."* To check that a receipt
held across a set, **the set must still exist when the receipt is checked.** A live call returns a
population as of instant T which is gone at T+1; a receipt evaluated against it can never be
re-derived, and a disagreement can never be adjudicated. PT-02's finding — *"no green receipt can
be shown to cover it; no red one can be shown to fall outside it"* — **is not cured by making the
call live. It is cured by DATING AND PERSISTING THE SET.** An ephemeral denominator reproduces the
exact defect this sprint exists to close.

This is also what the peer lane's record grammar demands: the placement must be carried
*"inseparably with … the instant the placement was OBSERVED at the source of record, and the
ruleset version"* (ADR §4.1:1389-1392, attributed). **An instant and a ruleset version are
properties of a RECORD, not of a function call.**

**REASON 2 — SEAM SURVIVAL. The successor adapter reads a database asana does not own.**
C-16's operator text: *"eventually we're likely to phase out the heavy reliance on Asana… plug in
direct communication to status reads from our database."* **Our** database — not asana's.

Apply the Dependency Rule [DP:SRC-003 Martin 2017] [MODERATE | 0.70 @ 2026-03-31]: source
dependencies point inward toward policy; infrastructure satisfies interfaces the policy declares.

| seam locus | Asana adapter | DB-status adapter | what happens at phase-out |
|---|---|---|---|
| inside `autom8y-asana src/` | local | **asana must read a DB it does not own — a new cross-service dependency pointing the wrong way** | the seam must be **migrated out of the service being retired, at the moment of maximum change** |
| in the consumer (`autom8y`) | HTTP call (the proven pattern, §1.2/R3) | local read | **delete one adapter. The seam is untouched.** |

> **A denominator seam that lives inside Asana dies with its first adapter.** That is the
> definition of a seam built wrong, and it is the 18-month acid test this design must pass.

**REASON 3 — RATIFIED DOCTRINE + LIVE PRECEDENT, both already in production.**
`autom8y` @ `4e0b41f9`, `services/email-booking-intake/src/email_booking_intake/receipts/asana_leg.py:3-9`,
verbatim:

> *"the Asana comment-threading capability is a FLEET-GENERIC primitive that ALREADY lives in the
> shared substrate (the autom8y-asana satellite …). EBI is a **CONSUMER**: it passes the clinic
> `company_id` + the receipt body over a **narrow HTTP port**; autom8y-asana resolves the task and
> threads the comment. EBI does **NOT** duplicate the gid map or build an Asana SDK here
> (**G-PROPAGATE — no per-service Asana orphan**)."*

So the fleet already has a **ratified cross-repo consumption doctrine**, an S2S token path
(`:35-38` — `autom8y_core.TokenManager.get_token_async`, *"the SAME provider the scheduling client
uses — one ServiceAccount, one in-process cache, two consumers"*), and a live wire
(`production.tfvars:172` `asana_receipt_base_url = "https://asana.api.autom8y.io/v1"`).

And the locus itself is **already occupied by this program's sibling** —
`autom8y` `scripts/ebi_witness_ledger.py` @ `4e0b41f9`:

| what it already does | line |
|---|---|
| parses `production.tfvars` for the booking-enablement population | `:221-228` `parse_census` |
| carries a per-office census record with `membership` and `tier_ratified` | `:190-198` `CensusOffice` |
| binding PII posture: *"office_phone in the payload are DROPPED (not hashed, not truncated — dropped)"* | `:19-22`, `:393-395` |
| a NAMED bucket for the un-attributable residual: *"accumulate into a single office-blind `unresolved` bucket (**NEVER guessed into an office**)"* | `:461-462` |

> **WS-DENOM is a second adapter and the missing reconciler on a census that already exists,
> in the right repo, at the right deploy class, with the right PII posture and the right
> named-exclusion primitive.** Landing it anywhere else would be the novel act.

### §1.3 The deploy consequence — derived last, re-taken at a FRESH ref

Per PT-01(b) condition 1 (*"TRUE AT A REF, NOT A PROPERTY … re-take against a freshly fetched
`origin/main`; never inherit from the ADR"*), re-resolved own-hands at this seat's start:
`autom8y` `origin/main` = **`4e0b41f9`**.

**Asserted dimension, named before the probe: whether a repo-ROOT `scripts/**` path is matched by
any workflow's `push:`-paths filter.**

- `service-deploy-dispatch.yml:26-31` @ `4e0b41f9`, quoted live:
  `on: push: branches: [main] / paths: - 'services/**'` — root-anchored ALLOW-list.
- Full enumeration of every path-filter line mentioning `scripts` across **all** workflows at that
  ref: **every hit is a SPECIFIC FILENAME** (`scripts/manifest-query.sh`,
  `scripts/pin_pullability_check.py`, `scripts/verify-deployed-digest.sh`, …) or is nested under
  `services/auth/scripts/**` / `terraform/services/otlp-collector/scripts/**` (neither repo-root).
  **No workflow carries a bare `scripts/**` glob.**
- **POSITIVE CONTROL, same probe form, same corpus, varying ONLY the asserted dimension** (`scripts`
  → `services`): `services/**` FIRES in 6 workflows including `service-deploy-dispatch.yml:31`.
  The probe can see what it is looking for; the zero is not an untaken zero.

⇒ **A new file at `autom8y` repo-root `scripts/` matches no deploy trigger. S-06 = C-INERT.**

> **★ TWO PRECISIONS, recorded so no successor inherits an imprecision as fact.**
>
> **(1) The absence is NAME-SPECIFIC, not directory-wide.** `scripts/` is heavily referenced by
> per-file gate filters. The instant any sprint adds a `scripts/**` glob to any workflow, this
> property flips. **Re-take at merge time. Never inherit this ADR's finding.**
>
> **(2) C-INERT ON DEPLOY ≠ GATE-FREE ON MERGE.** `merge-surface-sweep.yml:20-22` @ `4e0b41f9` is
> `pull_request: branches:[main]` with **no paths filter**, and it fails a PR whose ADDED lines
> carry *"32-hex runs, 25-char base32 runs, **12-digit runs**, Basic auth, glc_ tokens, AWS key ids,
> real-looking e-mails"* (`:12-13`). **This is a binding constraint on the artifact's schema, not a
> nuisance** — see §4.3.

### §1.4 This ADR's own deploy class — verified live, not assumed

Per the standing per-PR fence. `autom8y-asana` `.github/workflows/test.yml` @ `origin/main`
`389c59bc`, quoted with line numbers, read live at that ref:

```
29:    paths-ignore:
30:      - '.ledge/**'
31:      - '.sos/**'
32:      - '.claude/**'
33:      - '.gemini/**'
34:      - '.knossos/**'
35:      - '.know/**.md'
36:  pull_request:
37:    branches: [main]
```

**Positive membership asserted:** this file's path `.ledge/decisions/ADR-ws-denom-seam-2026-09-09.md`
**IS** matched by the deny-list entry at **`:30`**. ⇒ **C-INERT on push-to-main.**
**Asymmetry acknowledged (assertion 7):** `paths-ignore` sits on `push:` only; `pull_request:` at
`:36-37` carries no filter. **A PR still runs the full suite. "C-INERT" never means "no CI runs."**

### §1.5 What this ruling does NOT decide

- It does **not** rule S-09. O-8 was spoken (**COMPOSE — C now, A booked open**); S-09's locus
  follows the compose disposition and is not this ADR's to fix.
- It does **not** touch R-35, narrow it, or reinterpret it.
- It does **not** consume the O-9 standing B-ECS window. Under this design **WS-DENOM needs no
  asana `src/` change at all** (§2.6), so the window is available but **unspent**.

---

## §2 THE SEAM — grain, membership predicate AND aggregation rule as EXPLICIT PARAMETERS

### §2.1 The refusal that generates the design

> **A seam that hard-codes a grain or a membership predicate reproduces the defect.**
> The record now holds **SIX** `activating` vocabularies across **THREE repos**:

| # | vocabulary | grain / project | `activating` members | repo |
|---|---|---|---|---|
| 1 | `OFFER_CLASSIFIER` `activity.py:181-195` | offer · `1143843662099250` | ACTIVATING, IMPLEMENTING, NEW LAUNCH REVIEW | asana |
| 2 | `UNIT_CLASSIFIER` `activity.py:213-241` | unit · `1201081073731555` | Onboarding, Implementing, Delayed, Preview, **Engaged**, **Scheduled** | asana |
| 3 | `PROCESS_PIPELINE_SECTIONS` `activity.py:~262` | 9 pipelines · gid `""` | SCHEDULED, REQUESTED, DELAYED | asana |
| 4 | `_VENDORED_MONOLITH_SECTIONS` `section_registry.py:361-366` | unit · **`1201081073731555` — SAME PROJECT as #2** | Onboarding, Implementing, Delayed, Preview — and **Engaged/Scheduled → `inactive`** | asana |
| 5 | `SBM_FETCH_POOLS` `sbm.py:48,:55` | business-unit | `{"active","activating"}` | `autom8y-data` |
| 6 | `_account_status_sync.py:22,:55` | business-unit | `{"active","activating"}` | `autom8y-data` |

*Rows 1-4 measured own-hands at `autom8y-asana` `origin/main` `389c59bc`. Rows 5-6 ATTRIBUTED to
the identity-activity-substrate lane exchange @ `autom8y-data` `20c26cb8` — NOT this seat's
measurement. That lane's own characterisation: **"a fourth party, not a referee"** — neither
adjudicates the offers/units/pipeline vocabularies.*

**H-2(ii) confirmed verbatim at origin/main.** `activity.py` annotates
`"Engaged",  # Per truth audit: forward momentum, not inactive` while
`section_registry.py:332-333` annotates `"Engaged": "1201081073731561",  # §2 row 3 -> unit (inactive)`.
**Two authorities, one project, opposite buckets, each with a written rationale, neither aware of
the other.** This is not drift — it is a deliberate override with no reconciler.

**The peer lane's Q-2 rule makes silent selection structurally forbidden**, not merely unwise:
attaching OUT is permitted with a row-count and key-sequence assertion; **collapsing IN is
STRUCTURALLY REJECTED without a declared aggregation rule**; a finer identity may never be minted
from a coarser key (enforced by a landed UNIQUE constraint). *[ATTRIBUTED, `autom8y-data` ADR §4.1
Q-2.]* **Two vocabularies classifying `Engaged`/`Scheduled` oppositely inside one project is a
collapse-in with no declared aggregation rule — the exact shape that rule rejects.**

⇒ **The seam takes THREE explicit parameters, not one.** Grain alone is insufficient; PT-02's H-2
named grain and bucket, and the peer rule adds the third.

### §2.2 ★ A FIFTH HOLE, MEASURED THIS SPRINT — the client grain has no vocabulary at all

**Asserted dimension, named before the probe: presence of a `SectionClassifier` binding for a given
project GID (a `project_gid="<gid>"` line in `activity.py`).**

| project | entity | referenced repo-wide? | classifier in `activity.py`? |
|---|---|---|---|
| `1200653012566782` | **Business — THE CLIENT GRAIN** | **YES, 13 sites** (`entity_registry.py:470`, `project_registry.py:23`, `business.py:144`, …) | **★ NO — ZERO** |
| `1201081073731555` | Unit | yes | **YES** `activity.py:215` ← POSITIVE CONTROL FIRED |
| `1143843662099250` | Offer | yes | **YES** `activity.py:183` ← POSITIVE CONTROL FIRED |

`CLASSIFIERS` @ `origin/main` = `{"offer", "unit"}` + the nine pipeline types. **No `"business"` key.**

> ### **H-5 — C-16 SAYS "ASANA SECTION MEMBERSHIP." AT THE CLIENT GRAIN, THERE IS NO MEMBERSHIP VOCABULARY TO READ.**
> Every one of the six vocabularies is at a **sub-client** grain (offer, unit, pipeline,
> business-unit). **None is at the client grain.** The zero is not an untaken zero: the Business
> project is reachable and heavily referenced, and the identical probe fires on both sibling
> grains. The absence is specifically of an *activity vocabulary*, on the one grain the bar
> quantifies over.

**And the peer lane says this absence is CORRECT, not an oversight.** ADR §4.1:1400-1404: the
placement is *"readable on the **Offer and Unit** entities and **aggregated at Business**, with no
name anywhere in the traversal."* *[ATTRIBUTED.]*

⇒ **The client grain is DERIVED BY AGGREGATION, never natively classified.** Minting a
`BUSINESS_CLASSIFIER` would create a seventh vocabulary and mint a coarser-grain identity from
scratch — the thing the Q-2 rule forbids. **H-5 is therefore resolved by design, not by building:
the seam declares an aggregation rule instead of a new vocabulary.** This is what removes the last
asana `src/` change from WS-DENOM (§2.6).

### §2.3 The port

```
                        ┌──────────────────────────────────────┐
   DenominatorSpec ────▶│         DenominatorResolver          │
   (grain, predicate,   │  (POLICY — owns the port; knows no   │──▶ DenominatorArtifact
    aggregation,        │        source, no transport)         │    (dated · named-exclusion
    as_of, ruleset_ver) └───────────────┬──────────────────────┘     carrying · reproducible)
                                        │  DenominatorSource (PORT)                │
                        ┌───────────────┼───────────────┬──────────────────┐       │
                        ▼               ▼               ▼                  ▼       ▼
              AsanaSectionAdapter  BookingEnablement  DbStatusAdapter   LeadSignal  S-06 READER
              (CURRENT · HTTP to    Adapter           (SUCCESSOR —      Adapter     (autom8y
               asana /v1 · S2S)     (tfvars census)    NOT BUILT)       (ADD-ONLY)   scripts/)
```

**Dependency direction:** every arrow points **into** the resolver. The resolver imports no adapter;
adapters satisfy an interface the policy declares. Retiring Asana deletes one leaf.

### §2.4 `DenominatorSpec` — the three parameters, plus provenance

```yaml
DenominatorSpec:                  # every field REQUIRED; no field has a default
  grain:                          # H-2(i). WHICH population is enumerated.
    entity: business | unit | offer | <pipeline_type>
    project_gid: "<16-digit>"     # explicit; never inferred from `entity`
  membership_predicate:           # H-2(ii). WHICH buckets count as IN.
    vocabulary_id: OFFER_CLASSIFIER | UNIT_CLASSIFIER | VENDORED_MONOLITH
                 | PROCESS_<type> | <external-declared>
    vocabulary_source: asana-api | vendored | declared-inline
    buckets_in: [active] | [active, activating]     # the narrow/wide fork, EXPLICIT
    on_vocabulary_conflict: FAIL_CLOSED             # see §2.5 — the ONLY legal value
  aggregation_rule:               # ★ REQUIRED by the peer Q-2 rule. Absent ⇒ REFUSE.
    from_grain: unit | offer
    to_grain: business
    join_key: office_phone        # resolved INSIDE the adapter; never emitted (§4.3)
    quantifier: ANY | ALL         # ∃ vs ∀ over the child set — an OPERATOR choice
    row_count_assertion: true     # attaching-out demands one
    key_sequence_assertion: true
  provenance:                     # peer record grammar, adopted verbatim
    as_of: <ISO-8601>             # "the instant the placement was OBSERVED at the source"
    ruleset_version: <semver>
    source_refs: [{repo, ref, path, line}]
```

**Every one of the three is a REQUIRED input with NO DEFAULT.** A resolver invoked without a fully
bound spec **REFUSES and emits nothing**. There is no "sensible default" seam through which the
narrow/wide fork, the grain, or the quantifier can be silently chosen. *That refusal is the design.*

**★ The `quantifier` field is where the wave's own hazard lives.** PT-02: *"on the narrow reading
the bar could be reported GREEN while naming none of the dark offices — vacuously satisfied by
excluding the very class it was written for."* `buckets_in: [active]` + `quantifier: ALL` is the
maximally-vacuous binding. **Making it a required, named, recorded field is what stops it being
chosen by accident.** It is still an operator's to choose — F-2/F-6, §5.

### §2.5 `on_vocabulary_conflict: FAIL_CLOSED` — the H-2(ii) treatment

When two vocabularies at the same `project_gid` classify the same section name into different
buckets — the live `Engaged`/`Scheduled` case — the adapter **MUST NOT** pick, merge, or prefer.
It emits the office with `disposition: VOCABULARY_CONFLICT`, both bucket readings, and both source
anchors, and the artifact is marked `complete: false`.

**Precedent, already ratified and in production in this repo:** `section_registry.py:253-262`
routes a Tier-3 unknown to **NEITHER** set and emits a **BLOCKING** `live_name_no_bucket` finding —
*"omitted from both sets and BLOCKS live-wiring (not default-routed)"* — and
`SectionRegistryError` **fails module import** rather than start a service that would misroute.
**This ADR does not invent a posture; it extends the one this codebase already fails closed on.**

### §2.6 Adapters — and why WS-DENOM needs no asana `src/` change

**AsanaSectionAdapter (CURRENT).** Reads over the **already-live** S2S routes; ships **no** asana
code:

| need | live route @ `389c59bc` | verified |
|---|---|---|
| the vocabulary, as data | `GET /v1/query/{entity_type}/sections` → `[{section_name, classification}]` | `query.py:272-303`; `introspection.py:76-108` reads `CLASSIFIERS` |
| the population + placement | `POST /v1/query/{entity_type}/rows` | `query.py:~318`; `BASE_COLUMNS` carries **`section`** (`schemas/base.py:84`) and `parent_gid` (`:98`) |
| the client identity | `business` schema carries **`company_id`** (`schemas/business.py:9-15`) — **the allowlist's own key space** — plus `office_phone`, `name` | `entity_registry.py:460-490`: `business` is `warmable`, `warm_priority=1`, `key_columns=("office_phone",)` |

> **★ The vocabulary is FETCHED, never vendored.** The reader holds no copy of any bucket list.
> This is the seventh-vocabulary refusal made mechanical: **`buckets_in` names a `vocabulary_id`;
> the members come from asana at run time.** G-PROPAGATE honoured — no per-service Asana orphan.

⇒ **All three needs are served by routes that exist today. WS-DENOM ships ZERO asana `src/`
change ⇒ no B-ECS act ⇒ the O-9 window is available but UNSPENT.**

**BookingEnablementAdapter — the reconciler H-1(i) says nothing performs.** PT-02: *"Two live
authorities, receipted, contradicting, with no reconciler."* This adapter is that reconciler, and
it reads the plane `ebi_witness_ledger.py` already parses.

> ### ★★ A CORRECTION TO THE RECORD, MEASURED THIS SPRINT
> **The booking-enablement plane is TWO disjoint sets, not one.** PT-02 correctly cites *"the live
> 42-office allowlist."* That is the allowlist. It is **not** the plane.
>
> Measured own-hands @ `autom8y` `4e0b41f9`, `terraform/services/email-booking-intake/environments/production.tfvars`:
>
> | set | tfvar | n | controls |
> |---|---|---|---|
> | EBI-allowlisted | `contente_booking_live_allowlist` (`:160`) | **42** (42 unique) | `70316996`→1; POS `6f22301a`→1, `1b271a63`→1; NEG `deadbeef`→0 |
> | monolith-served | `contente_booking_monolith_served_set` | **4** | `70316996`→0; `6f22301a`→0 |
> | **intersection** | — | **0** — the tfvars' *"disjoint by construction"* claim CONFIRMED | POS control (allowlist ∩ itself) → **42** |
> | **union = the plane** | — | **★ 46** | |
>
> **A denominator reconciled against 42 alone would silently exclude 4 production-booking-enabled
> offices** — H-1(i)'s own failure mode, one altitude up.
>
> **Two further facts on that plane, both load-bearing:**
> - **★ THE KEY SPACE IS NOT UNIFORMLY UUID.** One served-set member is the legacy short-id
>   **`161`**. Probe: served-set keys failing `^[0-9a-f]{8}-…-[0-9a-f]{12}$` → **1**; POSITIVE
>   CONTROL, same probe, dimension varied to the allowlist → **0**. `ebi_witness_ledger.py:201-207`
>   already handles it (*"or the verbatim lower-cased short-id for a non-UUID legacy guid (e.g.
>   `161`)"*). **Any denominator that assumes UUID shape silently drops a live client** — a silent
>   exclusion, forbidden by §4.
> - **★ F-4 IS NON-EMPTY ON THE BOOKING-ENABLEMENT PLANE.** The served set contains
>   `2b73d481-…:custom_ghl_id`. **`custom_ghl_id` is a live production booking engine on this
>   plane, today.** This does **not** close F-4 — *"not on the `/calendar/reviewwave` route" ≠
>   "cannot reach the EBI plane"*, and EBI is an **email** intake — but it upgrades the class from
>   *hypothetical edge* to **occupied, with at least one named member**. §4.2 gives it a bucket.

**LeadSignalAdapter — ADD-ONLY, and the asymmetry is enforced in the type.** S-01's outbound
lead-notification measurement is the **only lineage-disjoint corroborator** of the Asana plane
(Salkin 75 rows/73 leads/21d; Sand Lake 41/39).

> **★ IT IS ONE-SIDED: IT CAN ADD TO THE DENOMINATOR, NEVER SUBTRACT.** 30-day window; sees only
> offices *receiving* lead notifications. An office absent from it may be perfectly active.

**Enforced structurally, not by comment:** this adapter's return type is `AddOnlyEvidence`, which
the resolver can only union. **There is no code path by which it can remove an office.** A
subtraction is not "discouraged" — it is **unexpressible**.

**DbStatusAdapter (SUCCESSOR — NOT BUILT).** Named to fix the port's shape, not to build. Its
existence at design time is what proves the boundary is real: it needs `grain`,
`membership_predicate`, `aggregation_rule` and `provenance` — the same four — and **nothing
Asana-shaped.** If any Asana concept had leaked into the port, this adapter could not satisfy it.

### §2.7 The artifact — one row per office in the union, always

```yaml
denominator_artifact:
  spec: <the full DenominatorSpec, echoed verbatim — the artifact carries its own predicate>
  as_of: <ISO-8601>
  ruleset_version: <semver>
  complete: <bool>            # false if ANY row is VOCABULARY_CONFLICT or UNRESOLVED
  counts: {in: N, out: M, conflict: C, unresolved: U, total_considered: T}   # T == N+M+C+U, asserted
  offices:
    - key: <company_id | legacy short-id>
      key_shape: uuid | legacy_short_id           # ★ heterogeneity carried, never normalised away
      disposition: IN | OUT | VOCABULARY_CONFLICT | UNRESOLVED
      reason_code: <closed enum — §4.1>
      evidence:
        asana:              {present: <bool>, grain: <…>, section: <name|null>, bucket: <…|null>, source_ref: <…>}
        booking_enablement: {present: <bool>, set: allowlist | monolith_served | null, engine: <…|null>, source_ref: <…>}
        lead_signal:        {present: <bool>, window_days: 30, note: "ADD-ONLY — absence is not evidence of inactivity"}
      aggregated_from: {child_grain: <…>, child_count: <int>, quantifier: ANY|ALL}   # the row-count assertion
```

**`total_considered` is asserted against the union, not against the rows the adapter happened to
return.** A listing is not a count: the artifact carries `total_considered` and the resolver
**fails** if the dispositions do not sum to it. That is the untaken-zero fence, at denominator
altitude, made arithmetic.

---

## §3 THE FOUR FORBIDDEN INPUTS — REFUSED BY CONSTRUCTION, NOT BY CONVENTION

### §3.1 The construction

**A convention is a comment. A construction is a type.** The `DenominatorSource` port's return type
admits exactly:

```
PlacementObservation = { key, key_shape, grain, project_gid, section_name, observed_at,
                         ruleset_version, source_ref }
```

**`section_name` is the ONLY status-bearing field, and it is a raw Asana section name resolved
against a `vocabulary_id` fetched from asana.** None of the four forbidden tokens is a member of
this type. An adapter cannot pass `activity`, `account_status`, `active_section_days` or
`Forwarding Stage` **through the port** — not because it is told not to, but because **there is no
field to put them in.** Bucket assignment is performed by the resolver, from `section_name` + the
fetched vocabulary, and from nothing else.

That is the by-construction refusal. The per-input reasoning below is *why the type is shaped that
way*, and the assertion in §3.3 is the guard against a future widening.

### §3.2 Per input

**(1) ASR's `activity` — A DIFFERENT QUANTITY.** It measures **pipeline fetch coverage, not
accounts**: *"91/144 rows read `untriangulated`, and 91/91 of those lack at least one of ASR's
three fetches — the token tracks pipeline COVERAGE, not accounts."* Producer branch frozen since
**2026-09-05T16:58Z**. *[ATTRIBUTED to the identity-activity-substrate lane; CONFIRMED by that
seat.]*
> **The specific danger: a denominator built on it MEASURES OUR OWN FETCH COVERAGE AND LOOKS
> PLAUSIBLE.** It would report a smaller, healthier population precisely where our own pipeline is
> weakest — construct-irrelevant variance [Messick 1989] [STRONG | 0.72 @ 2026-03-31] that
> correlates with the failure being measured. **Refused: not a placement.**

**(2) `account_status` — A SAME-LINEAGE ECHO THAT ALSO DESTROYS ITS OWN HISTORY.**
**★ UPDATED — worse than the record previously held.** It is refreshed by a **4-hourly snapshot
REPLACE**. *[ATTRIBUTED; CONFIRMED by that seat.]* So it fails **twice**:
- *lineage*: agreement with Asana is **one observation read twice**, not corroboration; and
- *provenance*: the REPLACE **destroys its own history**, so it is **undated** — it cannot supply
  `observed_at`, which the port **requires**.
> **Refused twice over. And the second refusal is structural**: an undated source literally cannot
> satisfy `PlacementObservation`.

**(3) `active_section_days` — NULL 144/144, two incompatible implementations, different measurands.**
> **★ HONESTY DISCLOSURE, carried as given:** this input was **NOT re-measured** by the
> identity-activity-substrate lane — wave 2 touched nothing in that path. It is carried here as
> **unchanged-and-unverified-by-that-seat**, **NOT as confirmed**. The refusal stands on the
> original wave-0 measurement and on the type (it is a derived duration, not a placement).

**(4) `Forwarding Stage` — WRONG IN BOTH DIRECTIONS ON THE SAME MEASUREMENT.** Lazar reads
`Flowing` with **zero arrivals in 90 days** (false-GREEN); Salkin records `Verified → Stalled`.
> **★ The aggravating factor is the CONSUMER, not the error rate: it is the first false-signal
> generator sitting on a surface a HUMAN reads.** A wrong number in a query is caught by the next
> query. A wrong *word* on a human-read surface is believed, repeated, and becomes the record.
> **Refused as a denominator input AND as an exclusion predicate.**

### §3.3 The guard against a future widening

The refusal is only as strong as the type. Two mechanical checks, both belonging to WS-DENOM's own
test surface (no watcher invented, nothing scheduled):

1. **Field-set assertion** — `PlacementObservation` is asserted to have **exactly** its declared
   fields. Adding one fails the test. *(This is the real gate: the four tokens can only re-enter
   through a widened type.)*
2. **Token deny-assertion** — the artifact serialisation is asserted to contain none of
   `activity`, `account_status`, `active_section_days`, `forwarding_stage` as keys.
   **Two-sided, or it asserts nothing:** the test must include a fixture carrying a forbidden key
   that the assertion **FAILS** on, alongside the clean fixture it passes. A one-sided deny-check
   certifies nothing.

---

## §4 THE NAMED-EXCLUSION MECHANISM

> **BINDING SHAPE-CONSTRAINT (PT-02, holds on either branch of F-1):**
> **If an office is OUT of the denominator, it must be OUT BY NAME, with a recorded reason —
> NEVER merely absent. A named exclusion is checkable; an absence is not.**

### §4.1 The construction: absence is not representable

**The artifact has one row for every office in the union of all adapters' populations.**
`disposition: OUT` is a **value**, never a missing row. There is no "filter" step anywhere in the
resolver — filtering is what produces silent exclusions. **The resolver only ever ASSIGNS a
disposition**, and `counts.total_considered` must equal the sum of dispositions or the run fails.

**`reason_code` is a CLOSED enum.** A new exclusion cause cannot be expressed until it is named,
which is exactly the point:

| disposition | reason_code | meaning |
|---|---|---|
| `IN` | `PLACEMENT_IN_BUCKET` | aggregated placement ∈ `buckets_in` |
| `OUT` | `PLACEMENT_OUT_OF_BUCKET` | placement resolved, bucket not in `buckets_in` |
| `OUT` | `NOT_IN_GRAIN_POPULATION` | absent from the declared grain's project entirely |
| `OUT` | `OPERATOR_RULED_OUT` | an operator fork resolved against inclusion — **cites the ruling** |
| `VOCABULARY_CONFLICT` | `H2_BUCKET_DISAGREEMENT` | §2.5 — two vocabularies, one project, opposite buckets |
| `UNRESOLVED` | `ALLOWLIST_ORPHAN` | **H-1(i)** — booking-enabled, invisible to the grain source |
| `UNRESOLVED` | `REVERSE_ORPHAN` | **H-1(ii)** — in the grain source, on NEITHER enablement set |
| `UNRESOLVED` | `KEY_SHAPE_UNJOINABLE` | non-UUID legacy key with no resolved counterpart (`161`) |
| `UNRESOLVED` | `ENGINE_CLASS_OPEN` | **F-4** — `custom_ghl_id`; reachability undetermined |
| `UNRESOLVED` | `CLIENT_UNDEFINED` | **H-3** — placement resolves; *client* does not |

**`UNRESOLVED` is never silently promoted to `OUT`.** It is a third state, it is counted, and any
`UNRESOLVED > 0` sets `complete: false`. **The bar cannot be reported green over an incomplete
denominator** — that is the mechanical form of *"held across ALL."*

**Precedent, in production, in the sibling script:** `ebi_witness_ledger.py:461-462` —
*"Unresolvable (`***`) dispositions accumulate into a single office-blind `unresolved` bucket
(**NEVER guessed into an office**)."* This ADR reuses that primitive; it does not invent one.

### §4.2 The four holes get rows, not footnotes

- **H-1(i) `70316996`** → `UNRESOLVED / ALLOWLIST_ORPHAN`, carrying both receipts (present on
  `production.tfvars:160`; absent from Asana on three query forms) and the note that it is
  **production-enabled to book while invisible to the denominator**. **F-1 is refused as
  agent-decidable; the artifact makes the office VISIBLE, WITH ITS CONTRADICTION, without deciding
  it.** Either branch of F-1 then only changes the row's disposition — never whether it appears.
- **H-1(ii) reverse orphan** → `UNRESOLVED / REVERSE_ORPHAN`. **The bucket exists before the count
  does.** Per the coordinator, this is being measured directly from Asana against the allowlist,
  because the peer registry is **structurally unable to answer it**: *"absence of a row = inactive"*
  cannot distinguish *inactive* from *never present*. **Designed for; the number drops into an
  existing slot. NOT asserted non-empty.**
- **F-4 `CustomGHLId`** → `UNRESOLVED / ENGINE_CLASS_OPEN`. **Designed for as an OPEN class, not
  excluded** — per the charge, and now with a live named member (§2.6).
- **H-3 "client" undefined** → `CLIENT_UNDEFINED`. Narrowed by the peer lane (§5), not closed.

### §4.3 ★ The artifact's schema is constrained by the merge-surface sweep — and it agrees with the PII ruling

`merge-surface-sweep.yml` fails a PR whose ADDED lines carry **12-digit runs** (`:12-13`).
**`office_phone` is phone-shaped and would trip it.** Independently, the binding PII ruling at
`ebi_witness_ledger.py:19-22` is *"office_phone … DROPPED (not hashed, not truncated — dropped)."*

> **Two independent constraints, one conclusion: the artifact keys on `company_id` (hyphenated
> UUID — no 32-hex run) and NEVER carries `office_phone`.**
> `office_phone` is used **inside** the adapter as the aggregation join key (§2.4) and is discarded
> before emission. **A `key_shape` field carries the `161` heterogeneity instead of normalising it
> away** — normalising would be a silent exclusion by another name.

*Note, non-actionable: a green sweep on an integration-base PR asserts nothing (PT-01 assertion 8);
pre-check against the PR's own diff before opening.*

---

## §5 OPERATOR FORKS THAT REMAIN, AND THE EVIDENCE THAT WOULD CLOSE EACH

**None of these blocks S-05's deliverable or S-06's charter.** The seam is designed so that every
fork below is a **binding of a declared parameter** or a **disposition of an already-visible row**.
That is the design's load-bearing property: **the denominator can be BUILT before these are
answered, and cannot be SILENTLY answered by building it.**

| # | fork | owner | status after S-05 | evidence that would close it |
|---|---|---|---|---|
| **F-1** | Is `70316996` a client — and generally, **which authority governs when booking-enablement and Asana membership disagree?** | **OPERATOR** | **UNCHANGED — refused as agent-decidable.** Now carried as a NAMED `ALLOWLIST_ORPHAN` row rather than an absence. | Two read-only probes, both unblocked: (1) `get_business_by_guid_async` on the **FULL** guid — the allowlist supplies all 36 chars, so the prefix→full-guid hop is not needed; distinguishes *real client, no CRM record* from *stale/test allowlist entry*. (2) An independent **name-based** Asana search. **Neither is pipeline engineering; GO/PARK untouched.** Then **one operator word** on the authority question. |
| **F-2** | **Which vocabulary governs, at which grain/project?** (H-2) | ARCHITECT / **OPERATOR** | **RESHAPED, not closed.** Now `grain` + `membership_predicate.vocabulary_id` + `buckets_in` — three required fields. **Scope ENLARGEMENT confirmed: it is C-3's denominator's question, not only S-07's hook-binding, and must not be settled on S-07's needs alone.** | An operator binding of the three fields. **The `Engaged`/`Scheduled` conflict is now adjudicable**: `activity.py` (→activating) vs `section_registry.py:332-333` (→inactive), same project, both anchors quoted. Until bound: `FAIL_CLOSED`. |
| **F-3** | **What is a "client"** — contract vs billing state? | **OPERATOR** | **★ NARROWED, NOT CLOSED.** At substrate altitude the peer lane ruled it is *"the classified lifecycle placement of a named account entity in the account model of record … the instant the placement was OBSERVED … and the ruleset version"* (**contract-side placement**). *[ATTRIBUTED.]* **The BILLING-state question has NO NAMED OWNER and that lane explicitly refused to guess.** | **Naming the owner of the billing-state answer** is the next step, and it is upstream of everything else. This ADR adopts the placement definition as the seam's record grammar; a billing-state ruling would add an adapter, not change the port. |
| **F-4** | `CustomGHLId` membership | **OPERATOR** | **OPEN — and now measurably NON-EMPTY** on the booking-enablement plane (`2b73d481-…:custom_ghl_id`, §2.6). **Designed for as an open class; NOT excluded.** | Whether a `custom_ghl_id` office can reach the **EBI email intake**. *"Not on the `/calendar/reviewwave` route" ≠ "cannot reach the EBI plane"* — EBI is an **email** intake, so the reviewwave-route argument does not settle it. **Not closable by inference.** |
| **F-6** | **★ NEW — the `quantifier`.** With `aggregation_rule.from_grain != to_grain`, does a client count if **ANY** child is in-bucket, or only if **ALL** are? | **OPERATOR** | **NEW, surfaced by making the aggregation rule explicit.** It was previously invisible because no artifact aggregated. | An operator word. **Consequence, stated so it is not chosen by accident:** `buckets_in:[active]` + `quantifier:ALL` is the **maximally vacuous** binding — PT-02's *"reported GREEN while naming none of the dark offices."* |
| **F-7** | **★ NEW — is the denominator's enablement reconciliation drawn against the 42-office allowlist, or the 46-office UNION** (allowlist ∪ monolith_served)? | **OPERATOR** | **NEW, from this sprint's measurement (§2.6).** | A ruling. **Consequence:** drawing against 42 alone silently excludes **4 production-booking-enabled offices** — H-1(i)'s own failure mode. This ADR's adapter reads the union and dispositions all 46; the ruling decides their `disposition`, never their presence. |

### §5.1 Registry hygiene — stated, not invented

**All seven forks above carry `NO WATCHER`.** C-12 forbids inventing one, and this ADR invents
none. Consistent with A6.2's ratio: **looking is what produces them** — this sprint added two
(F-6, F-7) and one structural hole (H-5) by measuring, and every one is unwatched.

**★ And the standing hazard is unchanged and worth restating:** the O-9 Wave-1 B-ECS window is
**human-memory-enforced** — deploy-class vocabulary is absent from `.github/` entirely — and the
cure is itself the disease, since `.github/**` is **not** on asana's deny-list, so a workflow file
adding an automated deploy-class gate **would itself roll prod on merge.** **No cure proposed here;
no watcher invented.** This design's contribution is narrower and real: **it spends none of that
window** (§2.6).

---

## §6 WHAT THIS ADR DOES NOT CLAIM

- **It does not enumerate the denominator.** It makes enumeration *possible and checkable*. Clause
  (c) stays **UNFALSIFIABLE until F-2 and F-3 are bound** — this design's contribution is that the
  binding is now a **named, recorded, three-field act** instead of an implicit consequence of
  whichever import someone reached for.
- **It does not measure the reverse orphan (H-1(ii)).** It gives it a bucket. **NOT asserted
  non-empty.**
- **It does not close F-1, F-3 or F-4**, and it refuses to narrow F-1 by inference.
- **Rows 5-6 of §2.1, and all §3 `activity` / `account_status` confirmations, are ATTRIBUTED** to
  the identity-activity-substrate lane exchange @ `autom8y-data` `20c26cb8`. **This seat did not
  read that repo.** `active_section_days` is explicitly carried as **unverified by that seat**.
- **The peer lane's `identity_observation_ledger` is not a third witness** — 0 rows, walk disabled,
  zero `IDENTITY_*` env keys on the serving task. Their words: **"an empty room."** And their own
  honesty limit, carried as given: the 0-row count is a **2026-09-06** read, and *"still zero"* is
  an **INFERENCE** from the code-side default plus the absent env key — **not tonight's
  measurement.** This design therefore treats that ledger as **absent**, not as a corroborator.
- **UV-P labels — claims this seat could NOT verify at this altitude:**
  - `[UV-P: GET /v1/query/business/rows returns a non-empty live population with a populated `section` column in production | METHOD: deferred-to-S-06-live-probe | REASON: this seat read the route, the schema and BASE_COLUMNS at origin/main 389c59bc by direct inspection, but issued no live authenticated request; the code path is verified, the live return is not]`
  - `[UV-P: an autom8y repo-root script can obtain S2S ServiceClaims accepted by asana's /v1/query router | METHOD: deferred-to-S-06-live-probe | REASON: asana_leg.py:35-38 documents the TokenManager provider and two live consumers, and production.tfvars:172 pins the base URL, but this seat executed nothing; the pattern is receipted for /receipts, not for /v1/query]`
  - `[UV-P: no workflow will carry a bare `scripts/**` glob at S-06's merge instant | METHOD: deferred-to-merge-time-re-take | REASON: §1.3 is TRUE AT REF 4e0b41f9 ONLY; origin/main moved eight times on 2026-09-08 alone. Re-take at merge time; never inherit]`

---

## §7 THE ACID TEST

> *"Will this look obviously right in 18 months, or will we be asking 'what were they thinking?'"*

In 18 months the operator's stated direction has been taken and Asana is being phased out. On that
day:

- the **seam** is untouched — it never knew what Asana was;
- the **Asana adapter** is deleted, and the **DB-status adapter** already satisfies the same
  four-field port;
- the **artifact** is byte-comparable across the switch, because `as_of` and `ruleset_version`
  travel in the record — **so the cutover is auditable rather than asserted**;
- and every office that was ever excluded is **still named, with its reason**, in every dated
  artifact ever emitted.

The alternative — a denominator that reads Asana in-process — would on that same day require
extracting a seam from inside the service being retired, **at the exact moment of maximum change**,
with no dated history to check the migration against. **That is the design we would be asked about.**

**Predicate clauses: (a)(b)(c)(d) ALL WAITING. Nothing merged, deployed, or applied.
S-05 wrote ONE file: this one.**
