---
type: decision
decision_subtype: decision-packet
artifact_id: DP-3-consumer-contracts
id: DP-3
title: "DP-3 — consumer contracts (F5): cross-process refuse-loud + the stale-200 retirement"
created_at: "2026-07-29T08:52:09Z"
author: architect
status: accepted                       # recognized lifecycle value
lifecycle_status: RATIFIED-BY-OPERATOR
ratified: "2026-07-29 — operator in-channel one word ('ratified'), house one-word precedent = recommendations as staged: status class 424+refusal-SLI · F5-5 ratified as P11 law · ADR-serve-stale-within-bound SUPERSEDED (executed in that ADR's frontmatter same day). See §Ratification record."
schema_version: "1.0"
rite: 10x-dev
initiative: substrate-v2-epoch
sprint: S1
door: "#3 (charter one-way-door register) — cross-service consumer contracts (CLI/service/MCP/delegated-fleet)"
blocked_until_ratified: "S5 (serving build)"
supersedes_disposition: "ADR-serve-stale-within-bound (2026-06-03) — EXPLICIT SUPERSEDED (not silent); see §Supersession"
evidence_grade: MODERATE
context: >
  Door #3: the cross-service consumer contract for the refuse-loud serving seam. In-process
  refuse-loud is settled by construction (F5-2 typed choke-point + Provable|Refused). The
  operator-facing decisions are cross-process: (1) the HTTP status class for STALE/CORRUPT/
  DIVERGENT refusals — contested two-sided between the PE (5xx-class) and the adversary
  (424 + dedicated refusal-SLI); (2) whether to mandate a typed client SDK as constitutional
  law (F5-5); (3) the EXPLICIT supersession of the ratified ADR-serve-stale-within-bound
  (2026-06-03), which serves STALE on a 200 with a flag — the exact confidence-labelled stale
  number RC-B forbids.
decision: >
  RECOMMENDATION (operator rules): STALE/CORRUPT/DIVERGENT → 424-class (Failed Dependency) +
  Retry-After bound to the rebuild schedule + a dedicated substrate_refusal_count SLI + RC-F
  alarms — NOT 5xx-class (refusal is a feature, not an outage; P2). Ratify F5-5 (mandated typed
  client SDK) as P11 constitutional law. Explicitly SUPERSEDE ADR-serve-stale-within-bound.
  Refusal bodies are shape-hostile (no data-shaped fields). Both status-class positions are
  presented verbatim below; the operator rules.
consequences:
  - type: positive
    description: "Refuse-loud becomes unbypassable in-process (type) AND cross-process (non-2xx the remote consumer raises on) AND inside the remote process (F5-5 SDK). The MCP island already raises on every non-200 (PE G10)."
  - type: negative
    description: "Live consumers relying on SWR/LKG availability (stale-served-200) lose that availability — STALE now refuses. This IS the one-way door."
    mitigation: "Consumer-side classification (don't-hot-retry-on-refused) MUST land WITH or BEFORE the server flip; Retry-After bounds retries to the rebuild schedule."
related_artifacts:
  - TDD-substrate-v2
  - ADR-substrate-v2-fork-register
  - ADVERSARY-substrate-v2-design-s1
  - FEASIBILITY-substrate-v2-seams-s1
  - CHARTER-substrate-v2-epoch-2026-07-27
tags: [substrate-v2, one-way-door, consumer-contract, refuse-loud, mcp, operator-packet]
---

# DP-3 — consumer contracts (F5)

> **Operator decision-packet. Door #3. RATIFIED-BY-OPERATOR 2026-07-29** (in-channel one-word
> precedent — recommendations as staged; §Ratification record). **Door SATISFIED — S5 ignites once
> {S2, S3} land (build dependency only), with consumer-side classification landing WITH-OR-BEFORE
> the server flip (hard sequencing).**

## The question

The serving seam returns `Provable | Refused`. In-process, refuse-loud is unbypassable by
construction (one typed choke-point; a bare value is unobtainable without handling `Refused`). The
CROSS-SERVICE contract — how a `Refused` crosses the wire to the CLI, the service, and the
MCP/delegated-fleet consumer — is a one-way door (external consumers depend on it). Four sub-decisions.

## Why this is a one-way door

Once external MCP/delegated-fleet consumers depend on the wire contract (status class, refusal-body
shape, SDK), changing it breaks them. And this packet RETIRES a ratified behavior (stale-served-200)
that live consumers rely on for availability. Charter Door #3.

## Option slate (F5 consumer-contract mechanisms)

| Option | Mechanism | Verdict |
|--------|-----------|---------|
| F5-1 | guard at each call-site | REJECTED — v1's documented failure (the guard drifted, missed a layer) |
| **F5-2** | single typed choke-point → `Provable\|Refused` | **RATIFIED (in-process construction; the frozen seam)** |
| F5-3 | refuse at the storage layer | REJECTED — DIP violation; blocks the rebuilder + parity harness (they need raw stale bytes) |
| F5-4 | HTTP middleware only | REJECTED as sole — covers only HTTP, not CLI/in-process consumers |
| **F5-5** | **mandated typed client SDK (constitution-homed, P11)** | **NEW (adversary-added) — the ONLY option reaching INSIDE the remote process; composes with F5-2. RECOMMEND RATIFY.** |

**F5-5 (C5):** F5-2 + non-2xx makes refusal maximally loud AT the boundary, but cannot construct
correctness into a process the substrate does not own. F5-5 — delegated-fleet consumers consume ONLY
through a sanctioned client library that raises on `Refused` in the CONSUMER's process — is the sole
mechanism that does. The MCP island's raising client (PE G10) is a de-facto instance for ONE consumer;
F5-5 generalizes it as constitutional law (P11 doctrine home) rather than an accident of the island's
implementation.

## Sub-decision A — STALE/CORRUPT/DIVERGENT status class (CONTESTED — two-sided, operator rules)

The in-process seam is fixed: **no `Refused` is ever a 200** (that would be the confidence-labelled
stale number RC-B forbids); every `Refused` is a non-2xx with a machine-readable `code`. The open
question is WHICH non-2xx class. The PE and the adversary disagree; both positions verbatim.

### Position 1 — PE: 5xx-class (verbatim, FEASIBILITY §4c)

> **Status partition + SLI accounting (grounded subtlety):** the query route's receiver SLI counts
> 5xx as `server_error` but **does NOT count 4xx** ("4xx are NOT counted (client error, not receiver
> health)", route body). So STALE→**409** would HIDE substrate-staleness from the receiver health
> metric (re-creating a query-gated blind spot), while STALE→**503-class** makes the SLI and RC-F both
> see unprovability as a health signal. **My recommendation to the DP-3 packet: STALE/CORRUPT/DIVERGENT
> map to a 5xx-class refuse, not 4xx** — so substrate-unprovability is visible to receiver health,
> consistent with RC-F. (Recommendation, not ruling.)

### Position 2 — adversary: 424 + dedicated refusal-SLI (verbatim, ADVERSARY §4a)

> The STATUS-CLASS recommendation I CONTEST as presented:
> - *Retry-amplification:* 5xx is retry-coded by default across HTTP clients AND by the island's own
>   classifier (503 → retryable-warming, G10 note). STALE persists for minutes-to-hours (until next
>   rebuild) — not a retry-clearable condition. 5xx without a distinct non-retryable code +
>   `Retry-After` bound to the rebuild schedule, shipped on BOTH sides simultaneously, invites
>   hot-retry storms and tells the remote LLM "retry" when the truth is "wait for rebuild."
>   Sequencing constraint: consumer-side classification must land WITH or BEFORE the server flip.
> - *SLO attribution:* refusal is "a feature, not an outage" (charter P2) — mapping it to 5xx burns
>   receiver availability-SLO for correct behavior and trains operators to read substrate staleness as
>   receiver failure.
> - *The visibility argument is weakened by the design's own RC-F:* PE argues 409 hides staleness from
>   the receiver SLI. But F6-1 exists precisely to make staleness visible WITHOUT queries; the receiver
>   SLI need not carry substrate health. A dedicated refusal-count metric (emitted at the choke-point)
>   + RC-F alarms covers visibility with clean attribution.
> - *Un-enumerated option:* **424 Failed Dependency** — semantically exact (request failed because a
>   dependency's state is unprovable), non-retry-coded by default.
> VERDICT: PE's 5xx-class is DEFENSIBLE (one merged health signal, zero new metrics) but NOT dominant;
> DP-3 must present 5xx-class vs 424/409-class with the retry/SLO/attribution ledger above and the
> sequencing constraint. (Condition C5.)

### My recommendation (operator rules)

**424 Failed Dependency + `Retry-After` (bound to the rebuild schedule) + a dedicated
`substrate_refusal_count` SLI at the choke-point + RC-F alarms** — NOT 5xx-class. The adversary's
argument is decisive on three grounds: (1) **P2 — refusal is a feature, not an outage;** 5xx burns
receiver availability-SLO for CORRECT behavior and mistrains operators. (2) **429-scar-tissue:** STALE
is not retry-clearable in the retry window; a retry-coded 5xx against an hours-persistent condition
invites a hot-retry storm — this fleet has a 2026-07-27 429-storm on record. 424 is non-retry-coded;
`Retry-After` points the consumer at the rebuild schedule. (3) **RC-F already carries the visibility**
the PE's 5xx argument wants — F6-1 emits staleness independent of query, so the receiver SLI need not
carry substrate health; a dedicated refusal-count metric gives cleaner attribution. This is
acceptance-compatible (RC-acceptance names "HTTP 5xx/409 with a machine-readable reason" — 424 is in
the same 4xx-refusal family as the 409 example). **Sequencing (hard):** the consumer-side
classification (MCP island `map_http_error` learning "refused-stale = don't-hot-retry") lands WITH or
BEFORE the server flip.

## Sub-decision B — refusal bodies are shape-hostile (C5, freeze)

A refusal body carries NO data-shaped fields (no `rows: []`, no zero-value aggregate). A sloppy remote
client that ignores the status and parses the body gets a PARSE failure, not an empty success —
refusal is structurally unparseable as a served number. This is the seam; the operator acknowledges
the consumer-facing consequence.

## Sub-decision C — F5-5 mandated typed client SDK

Ratify F5-5 as P11 constitutional law (the doctrine home): delegated-fleet consumers consume through
the sanctioned client, which raises on `Refused` in the consumer's process. Recommend RATIFY (generalize
the MCP island's raising client from an implementation accident to fleet law).

## Supersession — ADR-serve-stale-within-bound (2026-06-03), EXPLICIT (C5, not silent)

A ratified ADR (`ADR-serve-stale-within-bound`, 2026-06-03) serves STALE data on a **200** with
`stale_served=true` (SWR + LKG), surfaced as an honesty flag (`query/models.py:249/:428`; the MCP
island lifts it to the tool top-level). **That 200-with-a-flag IS the "confidence-labelled stale
number" the charter Non-goals and RC-B explicitly forbid.** Substrate-v2's serving seam RETIRES it:
STALE becomes a non-2xx `Refused`. This packet records that as an **EXPLICIT SUPERSEDED disposition** —
a ratified ADR dying as a silent casualty of a seam invariant is exactly the silent-supersession
class the fleet guards against. On DP-3 ratification, `ADR-serve-stale-within-bound` is marked
`superseded_by: DP-3-consumer-contracts`.

## ADVERSARY DISSENT (verbatim — arch-adversary, ADVERSARY-substrate-v2-design-s1 §2 F5)

> **Slate exhaustive?** NO — one structurally distinct option missing, and it is the ONLY one that
> reaches inside the remote process (the exact gap RK5 names):
>
> 1. **Option F5-5 — mandated typed client SDK.** Fleet-constitution law (P11's doctrine home):
>    delegated-fleet consumers consume ONLY through the sanctioned client library, which raises on
>    `Refused` in the CONSUMER's process. Server-side design (F5-2 + non-2xx) can only make refusal
>    maximally loud AT the boundary; it cannot construct correctness into a process it does not own.
>    F5-5 is the sole mechanism that does, and it composes with (does not replace) F5-2. The MCP
>    island's raising client (feasibility G10) is a de-facto instance of it for ONE consumer; the
>    packet should generalize it as constitutional law rather than leave it an accident of the
>    island's implementation.
>
> **Choice defensible?** YES in-process — F5-2 is the RC-C construction applied to serving; F5-1 is
> the documented failure; F5-3 misplaces policy; F5-4 covers one transport. The architect's own
> honesty about the cross-process boundary ("across the wire `Refused` is just bytes") is correct and
> correctly door-routed.
>
> **Packet-grade dissent items for DP-3:**
> 1. **Refusal envelope must be shape-hostile.** "non-2xx or explicit refusal envelope" (TDD RK5)
>    under-specifies: a sloppy remote client that ignores status and parses the body must get a PARSE
>    failure, not an empty list. Freeze: refusal bodies carry NO data-shaped fields (no `rows: []`, no
>    zero-value aggregate) — refusal is structurally unparseable as success. (Condition C5.)
> 2. **The STALE→5xx-class recommendation is contestable — present it two-sided** (full argument in
>    §4a). Un-enumerated middle option: **424 Failed Dependency** + dedicated refusal-count SLI + RC-F
>    alarms.
> 3. **Retiring ADR-serve-stale-within-bound must be an EXPLICIT supersession disposition** in the
>    packet — a ratified ADR (2026-06-03) dying as an implicit casualty of a seam invariant is silent
>    supersession (AC-03 class). (Condition C5.)
> 4. Steel-man of the recommendation, honestly rendered: for every consumer that checks status codes
>    — which includes the entire currently-shipped consumer surface (G9/G10) — F5-2 + non-2xx IS
>    unbypassable today, and no enumerated alternative beats it server-side. The dissent is about the
>    un-owned future consumer and the status-class semantics, not about the choke-point.

## Consequences / reversibility

- The choke-point (F5-2) and shape-hostile bodies are the frozen seam — not reversed by any status
  ruling. The status CLASS, F5-5 mandate, and the supersession are the one-way, operator-ruled items.
- Two-way until external consumers depend on the wire contract; one-way after.

## Requested ruling (one word per sub-decision)

1. **STALE/CORRUPT/DIVERGENT status class:** **`424+refusal-SLI`** (recommended) | `5xx-class` (PE)
2. **F5-5 mandated typed client SDK as P11 law:** **`ratify`** (recommended) | `defer`
3. **Supersede ADR-serve-stale-within-bound (2026-06-03):** **`supersede`** (recommended — the stale-200 is the forbidden confidence-label) | `keep`

Shape-hostile refusal bodies + "no `Refused` is a 200" are the frozen seam (not ruling items).
**On ratification, S5 unblocks.**

## Ratification record — 2026-07-29

**Ruling received:** operator in-channel, one word — "ratified" — per the house one-word precedent
(recommendations as staged, unamended). Recorded by the orchestrator; the operator was invited to
flag if a narrower ruling was intended.

| Sub-decision | Ruling |
|---|---|
| 1 · STALE/CORRUPT/DIVERGENT status class | **424 Failed Dependency + `Retry-After` (bound to the rebuild schedule) + dedicated `substrate_refusal_count` SLI + RC-F alarms.** The PE's 5xx-class position remains preserved verbatim above as the considered-and-NOT-adopted alternative. |
| 2 · F5-5 mandated typed client SDK | **RATIFIED as P11 constitutional law** — S9 carries it into the doctrine; the MCP island's raising client generalizes from implementation accident to fleet law. |
| 3 · ADR-serve-stale-within-bound (2026-06-03) | **SUPERSEDED — EXECUTED**: its frontmatter now carries `superseded_by: DP-3-consumer-contracts` (marked 2026-07-29). It remains the accurate record of the v1 paradigm until cutover; it governs nothing in v2. |
| (frozen seam, not ruled) | Shape-hostile refusal bodies + "no `Refused` is ever a 200" — stand as the seam. |

**Binding sequencing (hard, carried into the S5 brief):** consumer-side classification (the MCP
island's `map_http_error` learning `refused-stale = don't-hot-retry` + the 424/Retry-After
handling) lands WITH or BEFORE the server flip.

**Consequence:** Door #3 is **SATISFIED**. S5 ignites once {S2, S3} land (build dependency only).
The wire contract becomes ONE-WAY once external consumers depend on it.
