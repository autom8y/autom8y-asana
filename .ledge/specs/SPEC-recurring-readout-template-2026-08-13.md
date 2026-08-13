---
type: spec
status: draft
artifact_id: SPEC-recurring-readout-template-2026-08-13
initiative: exec-insight-delivery (asana-native-insight-delivery)
sprint: EX-5 (WS-2 — DESIGN limb; EXIT HELD pending Q-2)
rite: 10x-dev
author_seat: requirements-analyst
disjoint_critic: eunomia / verification-auditor (NR-5, §A mandate)
date: 2026-08-13
impact: low
impact_categories: []
evidence_grade: MODERATE (self-attestation cap; DESIGN limb — no live render, no build)
decision_owner_cadence: OPERATOR (C-9 — Q-2 UNRULED)
binding_inheritance:
  - PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:41-48 (the say-able set — item 1a only)
  - PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:804-808 (G4′ — branch-enumerating sign gate)
  - PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:1214-1232 (1a's own G4′ sign enumeration, both branches)
  - RULING-operator-morning-set-2026-08-13.md:101-108 (R-8 / D-6 — a k-of-n denominator is NOT a third number)
  - RULING-operator-morning-set-2026-08-13.md:162-176 (R-16 — orientation register, not steering)
  - CONTRACT-offers-freshness-axis-frozen-2026-08-11.md:227-228 (content watermark axes; last_modified nullable=False)
  - .sos/wip/frames/exec-insight-delivery.shape.md:375-405 (EX-5 entry / exit / must-not)
scope: DESIGN ONLY — this spec defines the template, the denominator surface, the
  per-number G4′ enumeration slot, the declared-empty extension point, and the
  generation-path DESIGN. The live worked render (a real figure from a real call)
  and the generation BUILD are Phase-2 (principal-engineer). No authenticated
  call is fired at this limb.
---

# SPEC — the recurring exec readout: template + denominator surface

> **DESIGN LIMB.** This spec is authored so a Phase-2 builder can produce the live
> render and the generation mechanism against a clear target. It **specifies** the
> render; it does not contain a live figure (that is exit criterion 1, a Phase-2
> BUILD). It does not rule cadence (operator's Q-2, C-9) — see the companion
> `PROPOSAL-readout-cadence-2026-08-13.md`.

## §1 The one say-able number (frozen input)

The readout carries **exactly one say-able number**: **item 1a**.

- **Sentence form** (the render must reproduce this shape, no other number
  claim): *"As of {t}, the most recent observed offer edit across {N} in-scope
  sections was {t_s}."*
- **Source**: `max(last_modified)` grouped by section, read via
  `POST /v1/query/offer/rows`.
- **DR-2 (as-of law)**: the reported `{t_s}` is the **`min` floor over
  constituents** — the *oldest* per-section `max(last_modified)`, so the readout
  can never read fresher than its stalest constituent section.
- **Provenance of the column**: `last_modified` is declared **non-nullable**
  (`base.py:76-82`, `source="modified_at"`), copied from Asana's own
  `modified_at`. It cannot lead the source it is copied from — the structural
  fact that makes item 1a single-signed (§3).

### §1.1 DF-1 — the independence that is the easiest thing here to get wrong

Item 1a reads `max(last_modified)` via `POST /v1/query/offer/rows` on a declared
non-nullable column. **It touches NEITHER the story cache, NOR `section-timelines`,
NOR `TemporalFilter`.** The substrate feeding those three is broken (EX-3), and
item 1a is *the one thing we can honestly say that does not depend on it*.

**Binding design constraints preserving DF-1** (a Phase-2 builder MUST hold all
four):
1. The generation path reads **only** `POST /v1/query/offer/rows`. It does not
   call `section-timelines`, does not read the story cache, does not import or
   invoke `TemporalFilter` (`query/temporal.py`).
2. The rendered figure is `max(last_modified)` per section, then the `min` over
   sections (DR-2). No move-class, occurrence-class, or dwell-class derivation
   enters the path.
3. No field carrying edit-history or movement semantics (item 1b, 2, 2′, 5a, 5b)
   is read or rendered — those are WITHHELD (`PREDICATE…:47`).
4. The template's data binding is a **pure function of the `/rows` response
   bytes** — same discipline as Lane-G co-sourcing (`CONTRACT…:519-524`): if the
   figure is a pure function of the served bytes, no cross-surface contamination
   is expressible.

## §2 Template design

The template is a fixed skeleton with named slots. Every slot is either the one
number, its mandatory disclosures, or non-number orientation text. **No slot may
introduce a second number claim** without the §5 extension-point discipline.

```
┌─ RECURRING OFFERS FRESHNESS READOUT ─────────────────────────────────┐
│ {cadence_label} · generated {t} · occurrence #{seq}                   │  ← header (mechanism/provenance)
│                                                                       │
│  As of {t}, the most recent observed offer edit across                │  ← THE ONE SAY-ABLE NUMBER (item 1a)
│  {k} of {n} in-scope sections was {t_s}.                              │      {t_s} = min-floor as-of (DR-2)
│                                                                       │      {k} of {n} = DENOMINATOR ONLY (C-6, §4)
│                                                                       │
│  ▸ Direction of this figure: {g4_prime_bound}                        │  ← PER-NUMBER G4′ enumeration (C-5, §3)
│  ▸ Reads via POST /v1/query/offer/rows; as-of is the oldest of the    │  ← disclosure: what it is / is not
│    {k} constituents. This is a recency statement, not a completeness  │
│    guarantee and not a movement count.                               │
│                                                                       │
│  ── extension point (declared, EMPTY) ──────────────────────────────  │  ← §5; empty unless EX-2 promotes
│                                                                       │
│  {orientation_footer}                                                 │  ← non-steering context (R-16, §6)
└───────────────────────────────────────────────────────────────────────┘
```

### §2.1 Slot inventory

| slot | content | constraint |
|------|---------|------------|
| `cadence_label` | human label of the ruled cadence (e.g. "Weekly") | filled from Q-2; until ruled, render is not generated (EXIT HELD) |
| `t` | generation timestamp, ISO-8601 UTC | the observation instant |
| `seq` | occurrence ordinal | the join key the generation receipt binds (§7) |
| `t_s` | the `min`-floor as-of (DR-2) | **the one say-able number** |
| `k` / `n` | denominator (§4) | **DENOMINATOR ONLY** — C-6; never rendered as an age or a rate |
| `g4_prime_bound` | the per-number sign statement (§3) | **required companion of the number** — DR-6 duty |
| `orientation_footer` | non-steering context | R-16 / F-E3 — no recommendation, no ranking, no CTA (§6) |

## §3 Per-number G4′ sign enumeration (C-5 — per-number and per-render)

**C-5 requirement**: G4′ sign enumeration is published **alongside the figure,
per-number and per-render — not once per artifact.** The template makes this
structural: the `g4_prime_bound` slot rides *on* the number and is regenerated
*with* it every occurrence. A render that carries the figure without its bound
statement is malformed.

**Item 1a's enumeration (frozen from `PREDICATE…:819-823, 1214-1232`)** — every
imputation, default, filter, and clipping branch on the path from source event to
rendered figure, with the sign on each:

| branch on the path | present? | sign of error |
|--------------------|----------|---------------|
| imputation | none | — (neutral) |
| default substitution | none — `last_modified` is `nullable=False` (`base.py:76-82`) | — (neutral) |
| row filters | narrow *which rows*, not the value | — (neutral) |
| clipping / truncation | none on the value | — (neutral) |
| **frame staleness** | pipeline stalls → `max(last_modified)` freezes → `now − max` grows | **OVERSTATE the age** (reads OLDER than truth) |
| understatement path | would need served `last_modified` newer than Asana's `modified_at` — structurally impossible (copy relationship, `source="modified_at"`) | **absent** |

**Result: single-signed (PASS).** The only non-neutral branch fails toward
**stale** — the alarm-safe direction. **`g4_prime_bound` renders as:** *"This
figure can only read as older than the truth, never fresher (it fails toward
stale). Its as-of is the oldest of the {k} constituents."*

> **Why per-render and not per-artifact.** The sign statement is only true of *the
> figure that was actually generated on this occurrence*. Publishing it once in a
> static footer would let a future template change silently break the coupling
> between the number and its bound. The per-render binding is the structural
> defense C-5 asks for. It is also the seam where a future *second* number (§5)
> would be forced to carry its OWN enumeration before it could render — the sign
> gate is per-number by construction.

## §4 Denominator surface under C-6

**R-8 / D-6 ruling**: a `k of n` denominator is a **completeness statement, not an
age** — it is **NOT a third number** (`RULING…:101-108`). The readout MAY carry
it. Precedent already ships: `{N} in-scope sections`.

**Design of the denominator slot:**
- Renders as `{k} of {n} in-scope sections` — a **count of sections**, riding
  **inside** the one say-able sentence as its scope qualifier.
- `n` = the count of in-scope sections for the request. `k` = the count that
  contributed a non-null `max(last_modified)` to the `min` floor.
- It is **DENOMINATOR ONLY**: it is never rendered as an age, a rate, a
  percentage-as-headline, or a delta. It qualifies *how many sections the one
  number is computed over*; it is not itself a number-claim about the business.

> **The fence is the interesting part.** R-8 is fenced to **denominators
> specifically**: *"it is a different kind of claim"* is *"exactly the argument a
> future seat would reuse for a fourth number — no further exceptions without a
> new ruling"* (`RULING…:105-108`). This spec therefore records the fence as a
> **binding design rule, not a convenience**:
>
> **DENOM-FENCE (binding).** The only non-age quantity the template may render
> without a new operator ruling is a **section-completeness denominator** in the
> `k of n` shape. Any future proposal to render another "different kind of claim"
> (a rate, a ratio-as-headline, a movement count, a second freshness axis) is a
> **new number class** and MUST route through §5 (extension point) + a new ruling
> — it may NOT be admitted by analogy to D-6. The template makes this refusable
> rather than debatable by giving the denominator a *typed* slot (`k`,`n`
> integers, "sections" unit) that cannot carry an age or a rate.

## §5 The extension point — DECLARED and EMPTY

The template designs for **one** number class (item 1a) with a **declared
extension point**. The extension point is a **named, empty region** of the
template (§2 skeleton, the `── extension point (declared, EMPTY) ──` band).

**Its disposition is bound to EX-2 (which runs in parallel):**

| EX-2 returns | extension point | template action |
|--------------|-----------------|-----------------|
| **"still one"** (item 1b stays withheld on the event-class mismatch) | stays **EMPTY** | **A legitimate, passing outcome (DF-5).** Record EX-2's disposition against the point; render nothing there. |
| **1b promotes** (a completed G4′ branch table clears it) | **fills** with the second number class | The new number: (a) carries its **own** per-number G4′ enumeration (§3, per-number by construction); (b) is bound by **C-5 per-render**; (c) requires **EX-2's re-derivation** (C-4) — it may NOT be published by analogy to the first. The template revisits (`shape.md:522-523`). |

**Binding constraints on the extension point:**
- **C-4** — no second number class is published without EX-2's re-derivation. The
  extension point is a *seam*, not a licence; it stays empty until EX-2 exits with
  a promotion.
- **DF-4** — **no movement-class number** is ever admitted here. A movement-class
  number is gated on RE-1 **and** EX-3 limb (iii), neither of which is complete.
  The extension point's typed contract forbids movement/occurrence semantics
  entering the template at all (preserves DF-1, §1.1).
- **EX-2 disposition slot** — the template metadata carries a recorded field for
  EX-2's disposition ("still one" / "1b promoted") so the empty state is
  *attested empty*, not merely *blank*.

## §6 Orientation register — R-16 / F-E3 (rung-level, silent in success signals)

The readout is an **orientation document, not a decision document**. It MUST NOT
recommend, rank, or lead with a call to action. This is **rung-level** and
failing it is **silent in every success signal** — a readout that steers still
posts, still delivers, still gets a receipt; the failure only shows when a reader
is nudged toward a pre-selected decision.

**Binding template rules (R-16 / F-E3):**
1. The one number is stated; it is **not** followed by "so you should…", a
   ranking of sections by concern, a trend arrow implying action, or a
   red/green health verdict.
2. `orientation_footer` may state *what the figure is and is not* (recency, not
   completeness; oldest-of-constituents) and *where the alarm lives* (freshness
   *alerting* is the PROV-family alarm's job, not this readout's). It may **not**
   tell the reader what to do about the figure.
3. No slot ranks, sorts-by-severity, or highlights a "worst" section as a
   call-out. `k of n` is a scope qualifier, never a leaderboard.
4. The three questions R-16 keeps open for the reader — whether to keep
   investing, whether to trust the numbers, what is broken and what it costs —
   are the *reader's*, and the template pre-selects none of them.

## §7 Generation-path DESIGN (whose receipt WOULD satisfy rung 2 limb (a))

**This is the DESIGN; the BUILD is Phase-2 (principal-engineer).** The design
target: a receipt from a **real generated occurrence** showing **two consecutive
occurrences with NO human assembly** (`shape.md:388-392`; RUNG 2,
`.know/telos/…:145-149`). **A hand-assembled brief does not clear this — this
initiative's own founding artifact is the proof of how easily that happens.**

**Design requirements for the generation mechanism:**
1. **Data-driven, not hand-assembled.** Every rendered value (`t`, `t_s`, `k`,
   `n`, `g4_prime_bound`) is derived by the mechanism from a real
   `POST /v1/query/offer/rows` response at generation time. No slot is typed by a
   human. The template is a pure function `render(response, cadence_label, seq)`.
2. **No-human-assembly is the load-bearing claim.** The generation receipt is a
   *did-a-human-touch-this* claim — a dual-altitude validation, which is why the
   disjoint critic is Bash-bearing `verification-auditor` (`shape.md:357`). The
   mechanism must emit a receipt that a machine can check: generator identity,
   the `/rows` request+response digest, the render digest, and the occurrence
   `seq`, with **no manual-edit step** between response and delivery.
3. **Two consecutive occurrences, joinable.** Each occurrence emits a *generation*
   receipt joined to its *delivery* receipt by `seq`. Rung 2 limb (a) consumes the
   join (`shape.md:324-325, 458`). The receipt **schema** is EX-4's (principal-
   engineer); this spec's requirement is only that the template's `seq`/`t`/
   digest slots supply the join keys that schema consumes.
4. **DF-1 preserved in the mechanism** (§1.1) — the generator reads only `/rows`;
   it never reaches the story cache, `section-timelines`, or `TemporalFilter`.
5. **CR-1 honoured** — the mechanism **reads** offer rows and **posts to Slack**
   (autonomous delivery, R-7). It performs **no Asana write** (the three Asana
   write classes are operator-reserved). Delivery is Slack-only.

> **What this spec does NOT author.** It does not author the generation source
> (Phase-2 BUILD) and it does not author the limb-(a) receipt schema (EX-4,
> principal-engineer). It specifies the render and the join keys the mechanism
> must supply.

## §8 Success criteria (testable by verification-auditor / QA downstream)

| # | criterion | testable check |
|---|-----------|----------------|
| SC-1 | The render carries **exactly one** say-able number (item 1a), in the §1 sentence form | count number-claims in a rendered occurrence == 1 (denominator, as-of, and G4′ bound are not number-claims) |
| SC-2 | DR-2 holds: `{t_s}` is the `min` floor over constituents | recompute `min` over per-section `max(last_modified)` from the `/rows` response; equals rendered `{t_s}` |
| SC-3 | DF-1 independence: no read of story cache / `section-timelines` / `TemporalFilter` | trace the generation path's calls; only `POST /v1/query/offer/rows` present |
| SC-4 | Per-number G4′ bound is rendered **per occurrence**, matching §3 (single-signed, fails-toward-stale) | `g4_prime_bound` present and non-empty in every occurrence; text asserts overstate-only |
| SC-5 | Denominator rides as `k of n` **only** — never as an age/rate/headline (DENOM-FENCE) | denominator slot is typed (ints + "sections"); no age/rate expressible in it |
| SC-6 | Extension point is **declared and EMPTY**, with EX-2 disposition recorded | the band is present; EX-2 disposition field is populated ("still one" / "1b promoted"); if empty, attested-empty |
| SC-7 | Orientation register: no recommendation, ranking, or CTA (R-16 / F-E3) | adversarial read of a rendered occurrence surfaces no steering language, no leaderboard, no health verdict |
| SC-8 | Generation receipt shows two consecutive occurrences, no human assembly (rung 2 limb (a)) | **Phase-2** — the join of two generation+delivery receipts by `seq`, machine-checked for no manual-edit step |

> SC-1..SC-7 are DESIGN-limb testable against the template + a Phase-2 render.
> SC-8 is the Phase-2 BUILD receipt; it is listed so the design target is
> complete, and the rite-disjoint attestation of limb (a) is
> `eunomia`/`verification-auditor`'s to give, not this seat's.

## §9 Impact assessment

`impact: low` · `impact_categories: []`.

- **No architectural boundary crossed** by the design: it reads a **shipped**
  response field via `POST /v1/query/offer/rows` (read-only; "reading is not
  touching", R-4) and specifies a Slack-delivered render.
- **No schema, API-contract, or auth change** — item 1a consumes existing fields;
  no field is added, no endpoint altered, no permission model touched.
- **No security-sensitive path, no data-model change, no Asana write** (CR-1
  preserved; delivery is Slack-only).
- **Cross-service note (named, not swallowed):** the generation *build* (Phase-2)
  coordinates an asana read and a Slack post. That chain **already exists**
  (`shape.md:1023`, NR-4: `slack_post_entered → report_posted`), so this is
  *consumption of an existing coordination*, not new cross-service coordination.
  The Phase-2 principal-engineer should re-confirm this determination when the
  mechanism is built; the DESIGN limb crosses no boundary and is `low`.

## §10 Fences honoured

- **DF-1** (§1.1) · **C-4 / DF-4 / EX-2 disposition** (§5) · **C-5 per-render**
  (§3) · **C-6 / DENOM-FENCE** (§4) · **R-16 / F-E3 orientation** (§6) ·
  **CR-1 Slack-only** (§7.5) · **C-9** — cadence not ruled here (companion
  PROPOSAL).
- No authenticated/credential-bearing call fired; no live figure rendered; no
  infra mutation; no git. Author-files-only.
