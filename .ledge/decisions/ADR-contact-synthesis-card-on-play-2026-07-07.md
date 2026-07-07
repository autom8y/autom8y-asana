---
type: decision
status: accepted
date: 2026-07-07
ratified: 2026-07-07 by operator (verbatim "I ratify the ADR"), post arch-adversary CHALLENGED-2 PASS
initiative: client-onboarding-delivery
slug: contact-synthesis-card-on-play
rung: authored (design altitude only)
forks_ruled: [F-1, F-2, F-3, F-4]
upstream_artifacts:
  - /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/arch-contact-synthesis/A0-pv-probes-report-2026-07-07.md
  - /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/arch-contact-synthesis/A2-dependency-map.md
  - /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/arch-contact-synthesis/A3-architecture-assessment.md
  - /Users/tomtenuta/Code/a8/a8/repos/autom8y/.sos/wip/frames/HANDOFF-10x-dev-to-arch-contact-synthesis-2026-07-07.md
supersedes: RECIPIENT leg of SPIKE-email-defaults-from-asana-entity-data.md §4 R-a/R-b fork
amends: rep-onboarding-deck-email-template-2026-07-06.md (v2 issued as rep-onboarding-deck-email-template-v2-2026-07-07.md per P-NOVA)
operator_ratification: required (status: proposed)
---

# ADR — Contact Synthesis: Ranked Contact Card on PLAY

## 1. Context

The first-client-send arc is realized: deck live + render-proven; link comment
`1216328952729447` + template comment `1216331184470862` live on Sand Lake PLAY
`1215823342887129`; `link_on_play.py` #201 @ 5604789f merged. The next trust-first
telos capability: a ranked-relevance contact card posted to the PLAY comment so the
human operating **Nova** can pick the receiver without leaving Asana. This ADR
consolidates four ruled forks from arch stations A2 (dependency-analyst) and A3
(structure-evaluator) into the design of record for a two-phase build.

G-RUNG: everything in this artifact is `authored` (design altitude only). The build
returns to 10x-dev after A5 adversary gating. No production code authored; target
repos unmodified.

---

## 2. P-NOVA: Sender-Constant Premise (operator ruling, 2026-07-07)

The assigned rep is NOT the sender. Sender = **Nova persona / `support@contenteapp.com`
/ Intercom, human sign-in, manual sends.** Receiver selection is where the value
concentrates; the sender is a constant.

Consequence for design:
- `[REP-NAME]` and `[SEND-FROM]` brackets in the email template collapse to constants
  (Nova / support@contenteapp.com). The template v2 is issued separately
  (`rep-onboarding-deck-email-template-v2-2026-07-07.md`).
- The contact card serves the human in Asana. No Intercom integration is in scope
  (`intercom_link` = storage-only field `dna.py:64`; LB-6 confirmed).
- The card's sole job: surface ranked candidates with `rank_reason` so the human picks
  the RECEIVER. The system never picks.

---

## 3. Seam Invariant

All data flows in this design are **unidirectional: autom8y-asana → autom8y-data**.
autom8y-data holds zero back-dependency on autom8y-asana.

Evidence: A2 §0 coupling three-check:
- Bounded context: autom8y-data is SoR for BusinessRecord/employees; autom8y-asana is
  the workflow/presentation plane. `workflow.py:566-568` (B1 join key already resolved).
- Intentionality: DESIGNED. Mediated by typed `autom8y-core` SDK contract
  (`data_service.py:154-158,193-207`). Methods `verify_office_phone_guid_binding:523`,
  `get_business_by_guid:631` are explicit contract methods.
- Directionality: UNIDIRECTIONAL. **This is the load-bearing invariant F-3 must not break.**

No design decision in this ADR inverts or thickens this directionality.
[DP:SRC-002 Martin DIP, MODERATE | 0.70] [DP:SRC-005 Evans bounded context, MODERATE | 0.70]

---

## 4. Fork Rulings

### F-1: PLAY Pull Read Path — LIVE TARGETED TRAVERSAL selected

Source: A2 §FORK F-1. Confidence: High.

**Ruling**: Option (a) — live targeted traversal, ~3 calls:
1. `get_gid_map(office_phone, vertical)` → `BusinessRecord.task_gid`
   (`data_service.py:264,283-311`)
2. `subtasks_async(business_gid)` → locate "Contacts 🧑" holder
   (`business.py:609`)
3. `subtasks_async(holder_gid, include_detection_fields=True)` → Contact children
   (`business.py:698-707`)

Entry state: at PLAY-comment build time the workflow already holds `office_phone`
(E.164) + `BusinessRecord.guid` from B1 (`workflow.py:566-568`). `get_gid_map`
bridges the data-plane row to the Asana traversal root in one POST.

> **⚠️ AMENDED-AT-BUILD (B5, 2026-07-07) — Call-1 only. Status: amended-at-build
> (orchestrator α-ruling, operator-vetoable). The ratified ruling text above is
> preserved.**
> B5's fail-closed dry-run FALSIFIED the Call-1 premise live: `get_gid_map_async`
> returns `None` for Sand Lake under EVERY vertical candidate (`BusinessRecord.
> default_vertical_key='none'`, `default_vertical_id=None`); the gid-map dataset does
> not cover these offices. **Call-1 (`get_gid_map`) is replaced with the N0-proven
> Asana-native bridge**: search the workspace by the Office Phone custom field, keep only
> members of the "Businesses" project (`1200653012566782`), refuse loudly on >1 match.
> Calls 2-3 (subtasks → holder → children) are UNCHANGED. Consequence: Phase-1 is
> **pure-Asana** — the `DataServiceClient` dependency and the `vertical` requirement are
> removed, and the §3 seam invariant (autom8y-asana → autom8y-data unidirectional) is
> STRENGTHENED to zero autom8y-data dependency at Phase-1. Evidence + implementation:
> the B5 live receipts + `contact_synthesis._business_gid_by_phone` + `TestBusinessBridge`
> two-sided tests; TDD Build-errata appendix "F-1 Call-1 AMENDED at B5". Rejected options
> below are unaffected (they concerned the read path, not the identity bridge).

Rejected options:
- **(a-naive) `hydrate_async`**: 10-20+ calls fetching all 7 holders + recursive
  Unit/Offer/Process holders (`business.py:588-682`). Efferent over-fetch for a card
  that reads only the Contacts holder.
- **(b) CONTACT_SCHEMA parquet (standalone)**: three flow-fit defects — mixed plane
  (230/300 rows are non-contact: `base.py:98`); FIND-005 silent NOT_FOUND ambiguity
  (`contact.py:75`); no freshness win on a human-gated low-freq flow. NOTE: the cascade
  viability doubt from the handoff is NOT the blocker — `resolver/cascading.py:277-343`
  `_traverse_parent_chain` walks Contact → parent → parent until the BUSINESS ancestor
  and reads that Business's Office Phone field, bypassing the empty holder field entirely.
  (b) is rejected on mixed-plane + FIND-005 + no-freshness grounds.
- **(c) Hybrid (dataframe + live read-back)**: registered as the documented scale path
  if post-rate rises. Not needed at Phase-1 volume; adds mixed-plane/FIND-005 complexity
  for no present benefit.

---

### F-2: Synthesis Home — SPLIT selected (entity method + workflow module)

Source: A3 §F-2. Confidence: High.

**Ruling (c)**: Two-part split:
- `ContactHolder.ranked_contacts()` — pure deterministic ordering over `self.children`;
  no I/O, no external data, no rendering. Extends the `owner` precedent
  (`contact.py:223-236`).
- `contact_synthesis.py` workflow module (beside `link_on_play.py`) — owns: residual
  garbage filter, dedup, Phase-2 cross-plane merge, ContactCard assembly, escaped
  render, egress.

Grounds:
1. **Repo idiom** — policy in workflow modules; pure derivations on entities. Entity
   precedent: `ContactHolder.owner` (`contact.py:223-236`) is a pure scan over
   `self.children`. Policy precedent: `link_on_play.py:138-143` (composition),
   `tenant_binding.py:29-34,66-69` (egress oracle sits off the producer with in-repo
   rationale).
2. **DDD bounded context** [DP:SRC-005, MODERATE | 0.70] — Phase-2 employees merge
   crosses into autom8y-data's context (`LB-4`: no employees method in
   `data_service.py:264,343,438,523,631,815,871`). That cross-context data belongs
   behind the anti-corruption seam = the service. The entity must never import the
   employees client.
3. **Phase-2-without-reshape** — acceptance criterion from handoff: "Phase-2 slots
   behind the same contract." Only (c) satisfies this with no entity reshaping.
4. **God-model guard** [AQ:SRC-004 Mo 2019, STRONG | 0.75] — `contact.py` is 243
   lines; `ContactHolder` is ~30 lines (`:206-236`). Option (a) would load the holder
   with html rendering + external-client I/O + escaping + egress = the god-component
   accumulation the anti-pattern taxonomy flags. Option (c) adds ONE pure ordering
   method.

Rejected options:
- **(a)** entity absorbs I/O + cross-context policy → god-model; Phase-2 reshapes entity.
- **(b)** acceptable but leaves aggregate anemic for a concern structurally internal
  to it (child-ordering is the aggregate's own invariant per `owner` precedent)
  [DP:SRC-002, MODERATE].

---

### F-3: Phase-2 Employees Endpoint — SEPARATE PROVENANCE TIER selected

Source: A2 §FORK F-3. Confidence: High for contract shape.

**Premise reset**: `Contact.employee_id` (`contact.py:87`) is populated on 4% of
contacts (A0). The force-join premise is dead. Employees are a separate provenance
tier corroborated deterministically — never force-joined.

**Ruling (a)**: `GET /api/v1/employees/by-company/{company_guid}` — autom8y-data builds
it; autom8y-asana consumes it via autom8y-core SDK. Full contract: see
`SPEC-employees-by-company-endpoint-2026-07-07.md`.

Rejected options:
- **(b) server-side reconciliation hints**: requires autom8y-asana to push contact PII to
  autom8y-data → inverts seam thickness. Reconciliation belongs where both datasets
  co-reside (asana plane).
- **(c) synthesis endpoint on autom8y-data**: forces autom8y-data to read Asana contacts
  → inverts/circularizes S-B directionality. Violates DIP [DP:SRC-002] and Acyclic
  Dependencies Principle [AQ:SRC-006 Martin 2002, STRONG | 0.75]. The card synthesis
  is autom8y-asana's domain.

**Dedup / corroboration rule (autom8y-asana side — deterministic):**
1. Normalize every email: `email.strip().casefold()`.
2. Corroboration keys (in priority order):
   a. `Contact.employee_id` == `EmployeeRecord.employee_id` — exact match (available
      on the 4% that carry it). Highest confidence.
   b. Casefolded-email exact match: `Contact.contact_email` (`contact.py:82`) vs
      `EmployeeRecord.email`.
3. Matched pair → ONE card entry, `provenance=corroborated` (Asana row is display
   base; `employee_id`/role enriched from the employee row).
4. Unmatched employee row → `provenance=employees`. Unmatched Asana contact →
   `provenance=asana`.
5. NEVER fuzzy/name-only merge — operator ruling (ranking must be
   deterministic-over-recorded-facts; model inference barred).

---

### F-4: Card Contract + Hardening — L1 real-`<table>` + fallback + plain-text

Source: A3 §F-4. Confidence: High.

**Premise correction (A0 supersedes LB-3):** `<table><tr><td>` round-trips (Asana
augments cells with width attrs). `<br>` in any form → silent 201 that entity-escapes
the ENTIRE payload into rendered tag soup. Line breaks inside cells = literal `\n`,
never `<br>`. `stories.py:307` `html_text: str | None = None` is the live seam.
A0 probe receipts (durable): A0-pv-probes-report-2026-07-07.md §UV-P-html — T4 story
`1216333984133231` confirms `<table>` survival; T1/T1d/e/f confirm `<br>` POISON
failure mode = silent 201 entity-escape (never a 400). [CH-03]

---

## 5. ContactCard Contract

| Field | Type | Source (file:line) | Notes |
|-------|------|--------------------|-------|
| `full_name` | str | `Contact.full_name` `contact.py:134-141` | escaped at render |
| `nickname` | str\|None | `Contact.nickname` `contact.py:89`; fallback `Contact.preferred_name` `:196-203` | |
| `contact_email` | str\|None | `Contact.contact_email` `contact.py:82` | 99% coverage where contact exists (A0) |
| `role` | str\|None | `Contact.position` `contact.py:97` | 43% present (A0); nullable; never a ranking hard-dep |
| `provenance` | enum{asana, employees, corroborated} | asana=holder child; employees=P2 endpoint; corroborated=`employee_id` join `contact.py:87` | 4% join population (A0); corroborated rare-by-design |
| `rank` | int | assigned by ranker | 1-based |
| `rank_reason` | str | assigned by ranker | MANDATORY per card; rendered as `<em>`; required even at n=1 |

---

## 6. Deterministic Tier Ranker

Tuple sort, all terms derived from recorded facts. No model inference (operator ruling).

| Tier | Key | Direction | Source (file:line) | rank_reason string |
|------|-----|-----------|--------------------|--------------------|
| 1 | `is_owner` | DESC | `contact.py:103-115`; `OWNER_POSITIONS:55-61` | "owner/{position}" |
| 2 | position-weight (static map over position enum) | DESC | `contact.py:97`; null position → weight 0 | "{position}" |
| 3 | has-email (`contact_email is not None`) | DESC | `contact.py:82` | "has email on file" |
| 4 | corroborated (`provenance == corroborated`) | DESC | join hook `contact.py:87` | "corroborated w/ employees" |
| 5 | alpha (`full_name`) | ASC | `contact.py:134-141` | deterministic tie-break |

Assessment grounding: same input → same output regardless of invocation count
[assessment-methodology P-03: inter-rater reliability sets the ceiling, MODERATE —
analogical transfer; functional ceiling per evidence-grade-vocabulary]. [CH-07]

---

## 7. Card Layouts

**L1 — Primary (real `<table>`; only A0-proven tags):**

```html
<body>
<table>
<tr><td><strong>#</strong></td><td><strong>Name</strong></td><td><strong>Nickname</strong></td><td><strong>Email</strong></td><td><strong>Role</strong></td></tr>
<tr><td>1</td><td>{esc full_name}</td><td>{esc nickname}</td><td>{esc contact_email}</td><td>{esc role}</td></tr>
<tr><td></td><td colspan="4"><em>{esc rank_reason}</em></td></tr>
</table>
[autom8y:contact-card deck={slug}]
</body>
```

Tags used: `<body><table><tr><td><strong><em>` — A0-proven-intact subset. No `<br>`.
Intra-cell line separators = `\n` only.

Note on `colspan="4"`: A0 probed TAGS not attributes; `colspan` was not independently
probed. TDD §6 carries `UV-P-colspan` discharged by the build-time G-ii read-back assert
at N5. See A0-pv-probes-report-2026-07-07.md ★orchestrator-addendum.

**L3 — Fallback (`<ul><li>`; used if future Asana change breaks `<table>`):**

```html
<body><ul>
<li><strong>1.</strong> {esc full_name} ({esc nickname}) — {esc contact_email} — {esc role} — <em>{esc rank_reason}</em></li>
</ul>
[autom8y:contact-card deck={slug}]
</body>
```

**Plain-text (ALWAYS populated):** `\n`-delimited numbered list of the same fields.
Mirrors `link_on_play.py:94` `LinkOnPlayResult.comment_text` always-populated convention.

---

## 8. Named Guards

**G-i — HTML-escape every contact-sourced string.**
Escape `< > & " '` BEFORE composition for every ContactCard field. A contact named
`A<br>B` escapes to `A&lt;br&gt;B` — simultaneously an injection guard AND the
`<br>`-poison guard (the escaped form cannot trip the silent-201 entity-escape).
- RED: `Dr <br> Smith` → composed html contains `&lt;br&gt;`; zero raw `<br>` in html_text.
- GREEN: `José O'Neil` → `José O&#39;Neil`; renders correctly; no over-escaping.

**G-ii — Read-back render assert (load-bearing loudness primitive).**
After post: GET the story back; assert `html_text` is NOT entity-escaped (contains live
`<table`, NOT `&lt;table`) AND idempotency marker is present. This makes the
silent-201-escape LOUD. Without G-ii, a `<br>` or future-unproven tag silently escapes
the whole payload → garbled card → wrong receiver picked = the exact silent-wrong-outcome
failure class (telos-integrity-ref anchor-return question; A3 AP-A).
- RED: inject unescaped poison tag → post → read-back shows `&lt;table` → raises LOUD.
- GREEN: valid L1 card → read-back shows `<table` live + marker present → pass.
Note: G-ii re-verifies A0's `<table>` survival claim at runtime on every post; design
does not rest on a one-time probe that could drift. [AQ:SRC-003 ATAM STRONG | 0.75]

**G-iii — Egress chain over composed text.**
Reuse `CANONICAL_ROUTING_ADDR_RE` (`tenant_binding.py:66-69`) + full-domain-literal
refusal + DECK_HOST https pin (`link_on_play.py:62`, `deck_slug_from_url:109`) over
FINAL composed text (card + any link). A `contact_email` that is a
`{uuid}@appointments.contenteapp.com` routing address must refuse BEFORE posting,
exactly as `link_on_play.py:219-223` does.
- RED: `ContactCard.contact_email = <uuid>@appointments.contenteapp.com` → compose →
  egress guard matches → refuse (raise, no `create_comment`).
- GREEN: `jane@clinic.com` → guard finds no routing address → posts.

**G-iv — Length cap (UV-P; build-probe discharges).**
`git grep` for MAX_COMMENT/COMMENT_MAX/65536 over `src/**/*.py` at origin/main returned
zero; `persistence/session.py:1392` is logging only. Length constant unknown.

[UV-P: Asana comment html_text max length | METHOD: deferred-to-build-probe (post a
length-N sandbox comment, bisect the reject boundary) | REASON: no length constant
exists in repo at 5604789f; needed to size the truncate/refuse policy]

Design: cap on composed length; overflow → truncate candidate LIST by dropping
lowest-ranked rows + "+N more" line (never mid-tag truncation; mid-tag could birth
unclosed tag → escape trip).
- RED: N contacts exceeding cap → composed html ≤ cap AND ends on closed `</table>`
  AND carries "+N more".
- GREEN: within-cap card → composed unchanged, no truncation notice.

**G-v — Slug-scoped idempotency marker.**
Marker: `[autom8y:contact-card deck={slug}]`. Extend #201 marker convention
(`link_on_play.py:56` `POSTER_MARKER_PREFIX`, `compose_marker:121-123`, scan
`:225-230`) with a DISTINCT prefix so contact-card comment and link-on-play comment
never collide on the same PLAY task. Slug-scoped: new deck re-posts; re-run skips.
- RED: story list already contains `[autom8y:contact-card deck=sand-lake]` → re-run
  for same slug → outcome `skipped_existing`, no second `create_comment`.
- GREEN: `deck=new-office` → marker absent → posts fresh.

**G-vi — Mixed-plane filter (person-shaped heuristic; lives in ContactSynthesis).**
A0: the Contacts plane is 77% non-contact rows; structural filter is free (holder
scope `contact.py:232`). Residual heuristic: person-shaped = has `contact_email` OR
non-null `position`. Dedup on `(full_name, contact_email)`. Lives in `ContactSynthesis`,
NOT in the entity's pure `ranked_contacts()`.
- RED: child with null email AND null position AND template-looking name → excluded.
- GREEN: child with `contact_email` set → included even if position null.

Named residuals for G-vi (carried to TDD §12 G-vi supplement and HANDOFF Named Residuals):
- False-inclusion: garbage row WITH email passes filter → tier-3 boosted; human reads
  rank_reason to recognize non-person row.
- False-exclusion: real sole contact with null email AND null position → must return
  `no_usable_contacts` (LOUD), not `no_contacts` (silent).

---

## 9. Two-Phase Plan

### Phase-1 (Asana-only — ships alone; no employees endpoint dependency)

- `ContactHolder.ranked_contacts()` pure method on the entity (tiers 1-5 over
  `self.children`)
- `contact_synthesis.py` workflow module (beside `link_on_play.py`) owns:
  G-vi mixed-plane filter, dedup `(full_name, contact_email)`, ContactCard assembly,
  G-i escaping, L1/L3/plain-text render, G-ii read-back assert, G-iii egress chain,
  G-iv length cap, G-v idempotency
- All ContactCard entries: `provenance=asana`
- CLI: dry-run-default + `--execute`; retry-429-only-never-POST-5xx
- 0-contact / no-holder paths: deterministic graceful-degrade; `no_contacts` (zero
  holder subtasks) and `no_usable_contacts` (≥1 subtasks, none pass G-vi — LOUD) are
  distinct outcomes

### Phase-2 (employees tier — slots behind the same contract; no entity reshape)

- Trigger: `GET /employees/by-company/{guid}` live on autom8y-data + autom8y-core
  SDK minor bump published + autom8y-asana consumer floor pin bumped + lockfile regenned
- `ContactSynthesis` adds `employees`/`corroborated` provenance tiers via dedup rule
  (§F-3)
- `ContactHolder.ranked_contacts()` is NOT reshaped; Phase-2 is purely additive in the
  service layer
- SPOF fallback (AP-B): if employees endpoint fails → degrade to `provenance=asana`;
  do NOT hard-fail the PLAY comment

---

## 10. Anti-Pattern Notes (for build sprint)

From A3 sweep; leverage scores inherited from structure-evaluator.

| ID | Finding | Class | Leverage | Build implication |
|----|---------|-------|----------|-------------------|
| AP-A | Silent-wrong-outcome dominant risk; G-ii read-back is sole load-bearing mitigation | [STRUCTURAL \| STRONG] | 5/1 | G-ii MUST NOT be dropped; raise on entity-escaped read-back |
| AP-B | Phase-2 SPOF at employees endpoint; hard-fail MUST become graceful degrade | [STRUCTURAL \| MODERATE] | 4/2 | Encode fallback in ContactSynthesis at Phase-1 design time |
| AP-C | Cascade risk: card + link are separate comments with separate markers | [STRUCTURAL \| MODERATE] | 4/2 | G-v separate marker; each fails independently |
| AP-D | Boundary honesty on provenance; 4% corroboration is rare-by-design | [STRUCTURAL \| MODERATE] | 3/1 | provenance enum in ContactCard contract |
| AP-E | Tier dormancy for 94% single-contact modal case | [TACTICAL \| MODERATE] | n/a | rank_reason MANDATORY even at n=1 |
| AP-F | God-model line: hold ranked_contacts() pure at all times | [STRUCTURAL \| STRONG] | 5/1 | Refuse any build drift moving dedup/merge/render onto ContactHolder |

---

## 11. Supersedes / Amends

**Supersedes RECIPIENT leg** of `SPIKE-email-defaults-from-asana-entity-data.md §4`
R-a/R-b fork. The spike proposed surface-as-candidates (R-a recommended) or
operator-re-ratification of auto-fill (R-b). This ADR supersedes both: the contact
card IS the surface-as-candidates mechanism — ranked, provenance-annotated, posted to
the PLAY comment. No separate bracket infill is required. The CLINIC and DECK LINK
infill legs (spike §5 emission items 1-2) are unaffected and stand as-is.

**Amends** `rep-onboarding-deck-email-template-2026-07-06.md` via separate v2 artifact
per P-NOVA ruling: sender brackets replaced by constants (Nova /
support@contenteapp.com). See `rep-onboarding-deck-email-template-v2-2026-07-07.md`.

---

## 12. Open Questions and Unknowns (carry to build sprint)

- **UV-P-1** — Contacts live coverage fraction (ACTIVE-section offices with ≥1 contact
  carrying non-null `contact_email`). Pre-flight probe at build time via CONTACT_SCHEMA
  dataframe or live read.
- **UV-P (G-iv)** — Asana comment html_text max length. Discharge at build via sandbox
  bisect post.
- **UV-P-colspan** — `colspan="4"` attribute survival in Asana html_text. A0 probed
  TAGS not attributes. Discharge: G-ii read-back at N5 (if colspan triggers silent-201
  escape, G-ii raises LOUD; if G-ii passes, colspan confirmed safe). No pre-build probe
  required.
- **Parquet cadence** — watermark/extraction schedule for `Contact/dataframe.parquet`
  is not determinable from source files (A2 Unknown 1). Matters only if hybrid (c)
  scale-path is ever promoted. Suggested source: autom8y-asana batch/lambda infra owner.
- **employees-table fields** — `preferred_name`, `active`, `role` vocabulary existence
  on autom8y-data's employees table (A2 Unknown 2). autom8y-data's to confirm at Phase-2.

---

## 13. Amendment — v3 Carrier Ratification (additive; operator-ruled 2026-07-07)

> **Additive.** This section is appended; §§1–12 above are preserved verbatim,
> including the P-NOVA ruling (§2) and the F-1..F-4 rulings. It amends only the
> carrier-email doctrine that §2/§11 handed to the email template.

### 13.1 What the operator ruled

The first client send (Nova → Dr. Ziyad, 2026-07-07) deliberately **included** the
client's own routing address `1b271a63-…@appointments.contenteapp.com` in the outbound
email — which the v1/v2 carrier checklist explicitly FORBADE
(`rep-onboarding-deck-email-template-v2-2026-07-07.md:78-80`: *"Nothing in your email
mentions an `@appointments.contenteapp.com` address"*). The operator ruled the inclusion
**correct**: Dr. Ziyad needs the address to complete the forwarding step the walkthrough
teaches. The blanket no-address rule is REVERSED — **conditional on a tenant-match
hardening.**

### 13.2 The tenant-match invariant (load-bearing)

The routing address that appears in the carrier email MUST be provably THIS office's
own — never another tenant's (the leak-by-containment crown-jewel). This is proven by a
**two-sided guard**, never by a checklist line alone:

> `assert_template_tenant_match(composed_text, office_guid)` — harvest every
> `{uuid}@appointments.contenteapp.com` via `CANONICAL_ROUTING_ADDR_RE`
> (`tenant_binding.py:66`); refuse fail-closed if any ≠ `format_routing_address(office_guid)`
> (`routing.py:75`). Predicate: `harvested − {own} == ∅` (no-foreign; **subset, not
> equality** — presence is a SHOULD, absence is permitted, a foreign address is REFUSED).

This is the same tenant-binding discipline `assert_exclusive_tenant_binding`
(`tenant_binding.py:115`) already applies to the frozen deck bytes, now applied to the
email-composition surface — minus the presence half (a valid re-send may omit the
address; the deck never may). Full guard + two-sided teeth:
`TDD-rep-template-v3-tenant-match-2026-07-07.md`.

### 13.3 System-provides-the-address (anti-fat-finger)

The routing address is SYSTEM-COMPOSED from the office guid, never hand-typed by the
rep. The guid is the office's **Company ID** custom field
(`business.py:263`, `dataframes/schemas/business.py:13` `source="cf:Company ID"`;
≡ office guid per `offer.py:123-130`) — the same guid the deck and contact card use.
`format_routing_address` raises `ValueError` on a malformed guid (`routing.py:98-108`),
so a bad anchor can never yield a plausible-but-wrong address.

### 13.4 Surface enumeration (which rule where)

The v1/v2 blanket no-address refusal is **preserved** on the two surfaces that
legitimately carry no routing address; the tenant-match guard REPLACES it on **only**
the template surface:

| Surface | v3 rule | Anchor |
|---------|---------|--------|
| LINK comment (`link_on_play.py` `_BODY_TEMPLATE:133`, egress `:225`) | blanket no-address STAYS | unchanged |
| CARD comment (`contact_synthesis.py` `_egress_guard:291,299`) | blanket no-address STAYS | unchanged |
| TEMPLATE comment (NEW `template_comment.py`) | tenant-match guard | §13.2 |

Net build surface: **1 new guard + 1 new module + 1 new exception**; zero edits to any
existing surface's invariant, and zero edits to §2 P-NOVA (Nova / support@contenteapp.com
remain the sender constants).

### 13.5 Fork carried to build (Pythia to ratify)

**FORK-GUID-SOURCE** — office_guid provenance for the routing-address composition:
- **Option A (recommended, lean):** the Business task's **Company ID** custom field,
  pure-Asana (mirrors `contact_synthesis._office_phone_from_task:356` /
  `_business_gid_by_phone:374`); keeps the template surface in the Phase-1 pure-Asana
  seam. Premise: Company ID ≡ `BusinessRecord.guid`.
- **Option B:** `get_business_by_phone_async(office_phone).guid` (`workflow.py:568`) —
  the same authority the deck's frozen address uses; re-adds the autom8y-data dependency
  contact_synthesis dropped.

The guard contract is identical under either; only the anchor provenance differs.

### 13.6 Supersession note

§13 amends the carrier-doctrine leg of `rep-onboarding-deck-email-template-v2-2026-07-07.md`
(v2 checklist item at `:78-80`). The template is re-issued as
`rep-onboarding-deck-email-template-v3-2026-07-07.md` (supersedes v2). All non-carrier
v2 rules (link-not-attachment, contact-card receiver selection, P-NOVA sender constants)
are preserved verbatim in v3.
