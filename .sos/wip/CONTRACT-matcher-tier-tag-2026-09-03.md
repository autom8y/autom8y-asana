---
type: spec
title: "CONTRACT — matcher tier/tag seam freeze (S-01)"
initiative: matcher-recalibration
sprint: S-01
date: 2026-09-03
revision: 8
revision_8_nature: "MECHANISM — the READ-COMPLETENESS axis (DF-40) lands on V-5, V-6 and V-8; V-1 stays CLOSED at eight and no ninth outcome is minted. name-the-zero S-04 moves; matcher-lane S-04/S-05/S-06 unaffected; matcher-lane S-08 tolerates two new row attributes."
revision_8_scope: "MECHANISM at a NEW ORTHOGONAL AXIS only. V-1, V-2, V-3, V-4, V-7 UNCHANGED. No new outcome, no new tier, no new metric label, no threshold VALUE chosen in this document, no terraform, no config field, no field on the 6-field attribution-verdict gate request."
revision_8_authority: ".sos/wip/frames/name-the-zero.shape.md:184-256 (S-01 exit criteria) + .sos/wip/CONTRACT-name-the-zero-kind-vocabulary-2026-09-05.md §4 K-8, §6 N-1..N-3"
revision_7_nature: "text-only — V-5/V-6 null-condition conformance + R-4a disposition; NOT a seam change; S-04/S-05/S-06/S-08 unaffected"
revision_7_scope: "TEXT-ONLY. Three cells: the V-5 and V-6 `winner_is_collider` null condition (moved to the mechanism the head already implements) and V-1's `matched_weak` disposition gloss (RS-12 wording). No mechanism, no threshold value, no seam limb, no new binder, no new field, no vocabulary change."
revision_7_authority: ".sos/wip/CHECKPOINT-matcher-recalibration-PT-04-DELTA-2026-09-05.md §D DC-2 (BLOCKING, owner architect) + §A Q4 ★ NEW + §C.2 R-4a; evidence qa VERDICT §13.9(b) and §13.5"
revision_6_nature: "MECHANISM — the plurality refusal is SCOPED TO THE COLLIDER (RS-19 amending RS-8; SEAM-RULING-plurality-scope-2026-09-04); S-04 and S-05 move; S-06 unaffected, S-08 tolerates one new row field"
revision_6_scope: "MECHANISM at the plurality lever's SCOPE and its per-candidate carrier. V-8.4's count chain UNTOUCHED. V-1, V-2, V-3, V-4, V-7, V-8 UNCHANGED. No new outcome, no new tier, no new metric label, no threshold VALUE chosen in this document."
revision_6_authority: ".sos/wip/SEAM-RULING-plurality-scope-2026-09-04.md §3, on the operator word RS-19; evidence qa VERDICT §12.9 N2-4 + RECEIPT ITER-4 §I4.4.1"
revision_5_nature: "MECHANISM — blank (2) forgiveness bar becomes shape-keyed (Option A, SEAM-RULING-forgiveness-bar-per-shape-2026-09-04); S-05 moves; S-04/S-06/S-08 unaffected"
revision_5_scope: "MECHANISM at the bar's ARITY only. V-1, V-2, V-4, V-5, V-6, V-7, V-8 UNCHANGED. No new outcome, no new tier, no new metric label, no threshold VALUE chosen in this document, no terraform, no config field."
revision_5_authority: ".sos/wip/SEAM-RULING-forgiveness-bar-per-shape-2026-09-04.md §3, discharging the RS-17 escalation at RECEIPT-matcher-recalibration-s09b-2026-09-04.md I2.8"
revision_4_nature: "text-only — predicate wording + conformance note; NOT a seam change; S-04/S-05/S-06/S-08 unaffected"
revision_3_nature: "text-conformance correction — NOT a seam change; S-04/S-05/S-06/S-08 unaffected"
revision_3_scope: "TEXT-ONLY. V-8.4 prose + a V-5 documentation note + §R. No mechanism, no threshold value, no seam limb, no new binder."
revision_3_authority: ".sos/wip/CHECKPOINT-matcher-recalibration-PT-04-2026-09-03.md — PT04-C2 (BLOCKING), discharging §F B-3"
rite: 10x-dev
agent: architect
status: FROZEN
binds: [S-04, S-05, S-06, S-08, name-the-zero-S-04]
consumes: [.sos/wip/PACKET-contradiction-flag-write-class-2026-09-03.md, .sos/wip/THREAT-contradiction-flag-reversal-surface-2026-09-03.md]
artifact_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana
build_target_repo: /Users/tomtenuta/Code/a8/a8/repos/autom8y
build_target_hash: b80a968762dcaf0a3dfaafac5d0092ccec5f2fcb
build_target_hash_rev8: 52995b267a773f9b91b1c8992bcf8acba543b222
reads_taken_at: origin/main
ruling_of_record: .ledge/decisions/RULING-matcher-recalibration-and-landed-definition-2026-09-03.md
frame: .sos/wip/frames/matcher-recalibration.md
shape: .sos/wip/frames/matcher-recalibration.shape.md
self_attestation_cap: MODERATE
resolves: [F-M2, F-M3, F-M4, F-M5, name-the-zero-F-M1, name-the-zero-F-M3]
flags_not_resolves: [F-P1, F-P2, F-P3, F-P4, F-A1, F-A2, F-M6]
---

# CONTRACT — Matcher tier/tag seam freeze

## §0 Realization predicate — CARRIED VERBATIM

> **Every ad-driven booking that arrives with minimal patient info is attributed
> to its originating lead — tiered by evidence, flagged when wrong; restated
> with provenance once the record-correction primitive lands, and never
> silently dropped. Verified-realized = the change is adversarially certified by
> a rite-disjoint critic AND at least one organic minimal-info booking has been
> attributed by the new tiers and spot-confirmed correct — NOT PRs merged, NOT
> self-attested green.**

Every sprint that binds to this contract carries the predicate verbatim into its
own exit criteria and into its PR body (shape §7 prescribed 1,
`matcher-recalibration.shape.md:1075-1077`). Never paraphrased, never compressed.

---

## §1 What this contract is, and is not

**IS.** The frozen seam that S-04 (W-ROUTE), S-05 (W-TIER + W-RECENCY), S-06
(W-FLAG limb a) and S-08 (W-COUNT) bind to. Four MECHANISM forks resolved with
reasons and receipts; one outcome vocabulary minted, closed, and shared across
three surfaces (the enum, the metric label, the persisted attribute).

**IS NOT.** No threshold VALUE is chosen here — every number in this document is
either a *name* awaiting G-4's word or an *existing* live value read at
`origin/main`. The contradiction-flag write's AUTHORITY class is not ruled here
(G-5 / S-07). No production code is written here.

**Authority of the ruling.** `R-M1..R-M9` / `R-L1..R-L6` are consumed verbatim
and never re-litigated. Where the frame and the ruling differ, the ruling wins
(shape §7 prescribed 2, `:1078-1081`).

**Revision 2 — the two S-07 inputs are CONSUMED, not merely acknowledged.**

- `.sos/wip/PACKET-contradiction-flag-write-class-2026-09-03.md` (§2 residence
  table; §9 "FOR S-01"). Its §9 **Reading 2** is **ADOPTED**: the tier tag is
  served content, not metadata, and frame `:649` ("the mark inherits F-A1's
  answer") is refused as admission-by-analogy. §5 below is rewritten on the
  packet's terms; the *residence* ruling of revision 1 is unchanged and is now
  the packet's own "cheapest" branch (§9 finding 1).
- `.sos/wip/THREAT-contradiction-flag-reversal-surface-2026-09-03.md` (T-01,
  T-02, T-10, T-13, T-15; §4.3; M-d, M-g). Five findings are folded into the
  frozen vocabulary, §4's window seam, §6's listener and §8's PII clause. T-02 in
  particular changes what `LeadCandidateSet` must carry, which is *this
  contract's own dataclass amendment* — so it rides §4 rather than becoming a
  separate change.

Every code claim either packet makes that this contract relies on was
**re-derived at `origin/main` by this seat's own reads** (§2, SVR-13..SVR-18).
Nothing is inherited on assertion (shape §7 prescribed 3, "Re-derive, never
inherit").

**Self-attestation cap: MODERATE.** This contract is authored by the same rite
that will implement against it. S-10's rite-disjoint critic is the attester;
S-09 re-derives composition at the assembled head (C-5).

---

## §2 Substrate and SVR ledger

All code reads taken at `autom8y` `origin/main` = `b80a9687` via
`git show origin/main:<path>` after `git fetch origin`. The working tree was
never read. Paths are relative to
`services/email-booking-intake/src/email_booking_intake/` unless prefixed.

| id | claim | method | anchor | marker (verbatim slice) |
|---|---|---|---|---|
| SVR-1 | EBI's prometheus counters do not reach CloudWatch; every live signal rides a structured log line | file-read | `pipeline/stages/extract_fields.py:247-249` | `The prometheus counter above does NOT reach CloudWatch -- this service's own terraform says so` |
| SVR-1b | the same constraint stated terraform-side, transport distinction named | file-read | `terraform/.../semantic_alarms.tf:22-26` | `TRANSPORT CONSTRAINT: the service's prometheus_client counters ... do NOT reach CloudWatch — the EMF bridge is a separate unmerged PR (#1123)` |
| SVR-2 | `record_intent` rows carry a 7-day TTL and are reaped | file-read | `forwarding_confirm/idempotency_ddb.py:108-116, :143-146` | `ttl_seconds: epoch-offset written to the ``ttl`` attribute so DynamoDB TTL reaps rows (R-A3)` |
| SVR-3 | `record_witness` is a TTL-FREE sibling with the same additive-attribute contract, minted to cure "an ephemeral-lifetime mechanism silently imported into an of-record duty" | file-read | `forwarding_confirm/idempotency_ddb.py:238-291` | `diverging from ``record_intent`` on exactly ONE axis: the written ``Item`` NEVER carries a ``ttl`` key, at any value` |
| SVR-4 | the intake role already holds PutItem/GetItem/UpdateItem on the shared table, and holds NO Scan and NO control-plane | file-read | `terraform/.../forwarding_idempotency.tf:59-78` | `Same-table, data-plane-only, single-item verb: no Scan, no control-plane (CreateTable/UpdateTable remain absent by design)` |
| SVR-5 | the contente-reconcile role already holds Scan/UpdateItem/GetItem on the same table | file-read | `terraform/.../contente_booking_reconcile.tf:194-196` | `"dynamodb:Scan",` / `"dynamodb:UpdateItem",` / `"dynamodb:GetItem",` (3-line literal slice) |
| SVR-6 | no new table and no GSI is available to this repo's CI role at any price | file-read | `terraform/.../forwarding_idempotency.tf:8-13` + `contente_booking_reconcile.tf:12` | `CI role is deliberately scoped to DATA-PLANE-only DynamoDB ... with NO dynamodb:CreateTable` |
| SVR-7 | the contente-reconcile sweep is LIVE in production on a 15-minute schedule, running a decoupled observe-only phase on it | file-read | `terraform/.../environments/production.tfvars:138, :146` + `variables.tf:316-320` | `contente_booking_reconcile_enabled = true` / `default     = "rate(15 minutes)"` |
| SVR-8 | a terraform change to EBI is a SECOND, environment-gated deploy path — never the merge-to-image path | file-read | `.github/workflows/service-terraform.yml:293-322` + `terraform-apply-reusable.yml:110` | `it requires ``workflow_dispatch`` with ``environment=production``. The GHA ``production`` environment binding ... additionally enforces the environment's required-reviewers rule` |
| SVR-9 | `WEAK_EVIDENCE` today REFUSES to the OPS park — the string whose referent R-M3 flips | file-read | `name_evidence.py:211-216` + `pipeline/stages/match_lead.py:132-155` | `The winner cleared the FIELD but not the FLOOR (S-4 FIX-1 / F-B1).` |
| SVR-10 | the metric module declares a low-cardinality-only label contract with a ~500-series ceiling and a no-PII rule | file-read | `metrics.py:18-20, :40, :42-45` | `All labels are low-cardinality enumerations` / `Total series count stays well within Prometheus health limits (~500 series).` |
| SVR-11 | `LeadCandidateSet` carries BOTH `window_days` and the literal `window_start`, and the client derives one from the other — the fetch anchor is exactly reconstructible from the set alone | file-read | `activation_read_client.py:284-298, :570-571, :617-621` | `window_start = anchor - timedelta(days=self._lead_window_days)` |
| SVR-12 | an undated candidate (`created_at is None`) is NOT rejected by the 90-day window today | file-read | `activation_read_client.py:706-713` | `if created_at is not None and created_at < window_start:` |
| **SVR-13** | **the same service formally refuses pick-semantics on `leads.phone` in one module while performing exactly that pick in another** — THREAT T-01, re-derived here | file-read | `ad_lead_gate/predicate.py:35-41` vs `pipeline/stages/match_lead.py:198` | `P3 IS A SET PREDICATE, NOT A LOOKUP (§3.3). ``leads.phone`` is not unique (4,977 distinct values carry >1 row).` — against `existing = await data_message_client.get_lead(winner.candidate.phone)` |
| **SVR-14** | **candidates are deduped by phone, and `rows_before_dedupe` is LOGGED but NOT carried onto `LeadCandidateSet`** — THREAT T-02, re-derived here | file-read | `activation_read_client.py:595-608` (dedupe), `:610-616` (log), `:617-621` (set construction, field absent) | `seen: set[str] = set()` … `if candidate.phone in seen:` … `rows_before_dedupe=len(records),` |
| **SVR-15** | **the tier cannot ride the contente booking POST: the client refuses any drift from the frozen 6-field contract at the wire** — PACKET §9.3 | file-read | `contente_booking_client.py:19-24` | `by REFUSING any payload that drifts from the frozen 6-field contract at the wire` |
| **SVR-16** | **`phone_hash` is an unsalted, 32-bit-truncated sha256 of a direct identifier; the module itself calls it a correlation token, not a de-identifier** — THREAT §4 / T-10 | file-read | `name_evidence.py:265-269` | `"""Opaque correlation token -- the ``book_appointment._redact_phone`` shape."""` with `hashlib.sha256(...).hexdigest()[:8]` |
| **SVR-17** | **the phone path resolves and RETURNS before name evidence is ever consulted, so predicate (ii) exists nowhere today and is only buildable against a persisted mark** — THREAT T-15 | file-read | `pipeline/stages/match_lead.py:305-323` | `existing = await data_message_client.get_lead(ctx.contact_phone)` … `return StageResult(` … `message=f"Matched existing lead {ctx.lead_id}",` |
| **SVR-18** | **one ServiceAccount is the runtime identity of the whole EBI service, and it is ALREADY on two fail-closed `*_ALLOWED_CALLERS` planes in autom8y-data** — PACKET §2 residence A, corroborated own-hands | bash-probe / file-read | `git grep sa_e92a293f22b9f7aed2650ba0d3866b94 origin/main` → `services/email-booking-intake/RUNBOOK.md:132`, `terraform/services/data/main.tf:465, :479` | `"BOOKING_CORROBORATION_ALLOWED_CALLERS" = "sa_e92a293f22b9f7aed2650ba0d3866b94"` / `"ATTRIBUTION_VERDICT_ALLOWED_CALLERS" = "sa_e92a293f22b9f7aed2650ba0d3866b94"` |

Supporting anchors cited inline (not repeated): `name_evidence.py:167-186`,
`:202-225`, `:295-330`, `:489-495`, `:567-622`;
`match_lead.py:105-108, :110-188, :215-233, :338-348, :456-471`;
`metrics.py:302-331`; `park.py:51-89, :163-180, :276-311`;
`pipeline/stages/book_contente.py:221-283`;
`forwarding_confirm/idempotency_ddb.py:452-500, :597-645`;
`receipts/sink.py:1-8`; `reconcile_handler.py:620-745`; `utils/redact.py:52-71`;
`handler.py:764-775, :795-797, :940-952`;
`terraform/services/email-booking-intake/main.tf:278, :424-436`;
`.../semantic_alarms.tf:64-101`; `.../variables.tf:61-65, :341`.

---

## §3 THE FROZEN OUTCOME VOCABULARY

One vocabulary, three surfaces. A sprint may refactor freely inside the matcher
plane (shape §7 emergent, `:1117-1119`) **provided this vocabulary is honored
byte-for-byte.**

### V-1 — `NameMatchOutcome` (CLOSED enum)

| value | tier | binds? | disposition | status vs `origin/main` |
|---|---|---|---|---|
| `matched` | `high` | YES | silent bind | **UNCHANGED** |
| `matched_weak` | `weak` | YES | bind + tag + count + **flagged when wrong** (the REMEDY is §0's, per RS-12: restated with provenance once the record-correction primitive lands — corrected at rev 7, residue R-4a) | **MINTED** (R-M3, R-M4) |
| `below_bar` | `none` | no | OPS park | **MINTED** — takes over the park limb `weak_evidence` used to serve |
| `ambiguous` | `none` | no | OPS park | **UNCHANGED** |
| `no_match` | `none` | no | OPS park, ORGANIC | **UNCHANGED** |
| `no_candidates` | `none` | no | OPS park, ORGANIC | **UNCHANGED** |
| `read_failed` | `none` | n/a | stage-level degradation | **UNCHANGED** (`match_lead.py:473-475`) |
| `lead_id_unresolved` | `none` | no | stage-level refusal | **UNCHANGED** (`match_lead.py:208`) |
| ~~`weak_evidence`~~ | — | — | — | **RETIRED at the landing instant. Never re-pointed.** |

CLOSED. A sprint that needs a ninth value has found a seam defect: surface it at
its checkpoint, do not add it (shape §7 emergent, `:1126-1128`).

### V-2 — the `tier` field (CLOSED enum)

`tier ∈ {high, weak, none}`, a **first-class field on `NameEvidenceMatch`**, not
derived at each call site.

1. **R-L3 becomes structural.** The certificate's exclusion predicate is the
   single-field test `tier != "weak"` (ruling `:81-83`, C-7). As a string-set
   over `outcome` it would silently widen the moment a ninth outcome appeared.
2. **W-FLAG's scan predicate is one attribute** (`tier = "weak"`) — what makes
   §6's server-side `FilterExpression` cheap.
3. **W-COUNT's four classes are a TIER axis crossed with an OUTCOME axis**, not
   one axis (R-M7).

★ **Consequence carried from PACKET §9 Reading 2, and it is load-bearing for
§5:** because a served count and a certificate both READ this field, `tier` is
**record content**, not metadata. That is not a footnote — it is the fact that
decides the tag's authority class.

### V-3 — the two-directional delta, and the migration of `weak_evidence`

R-M3 does two opposite things at once (shape S-01 exit `:145-150`; frame R-14 /
PC-4):

- **Direction A (park → bind) — SEQUENCED AT rev 5; DOES NOT LAND IN EVENT ONE.**
  A lone prefix-first FNLI candidate today PARKS via `clears_evidence_floor` →
  `WEAK_EVIDENCE` → `TerminalDecline("name_evidence_weak", OPS)`
  (`name_evidence.py:328-329`, `:588-598`; `match_lead.py:132-155`). R-M3 makes
  it BIND — **and that bind is realised at the LOOSENING SITTING, not in event
  one** (RS-17 amending RS-9; R-25). Event one REPRODUCES today's park through
  the FNLI key of the per-shape forgiveness bar, so Direction A is **DEFERRED,
  never REVERSED**: R-M3 stands ratified and its BIND limb is scheduled. The
  two-directional delta therefore lands **ONE-DIRECTIONAL in event one —
  Direction B only**. Mechanism, receipts and the per-shape keys: **§R rev 5
  Clause 1**.
- **Direction B (silent-high → tagged-weak).** A lone INITIALS candidate today
  binds SILENTLY as `matched` — the floor is inert for that shape by
  construction (`name_evidence.py:309-317`; frame PC-4). R-M4 makes it
  `matched_weak`: same disposition, different tier.

**Migration rule: RETIRE, never re-point.**

| surface | today | after landing |
|---|---|---|
| enum value | `WEAK_EVIDENCE = "weak_evidence"` (refuses) | value **removed**; `MATCHED_WEAK`, `BELOW_BAR` added |
| metric label value | `outcome="weak_evidence"` | stops forever; `matched_weak` / `below_bar` begin |
| TerminalDecline class | `name_evidence_weak` | **retired**; `name_evidence_below_bar` begins — and at rev 5 it begins **NON-MUTE**: the FNLI bar routes exactly the population `name_evidence_weak` serves today, so the successor is a **1:1 handover**, not a born-silent class |
| CloudWatch dimension `class` | `name_evidence_weak` populated | goes flat at the landing instant, **with `class=name_evidence_below_bar` picking up in the same instant** (rev 5; under the rev-4 shape-agnostic strike BOTH read flat) |

A label string whose referent silently changes is a denominator-integrity breach:
every historical query over the 90-day window would compare two populations under
one name. Retiring makes the regime change VISIBLE at a known instant.

**Naming note (`below_bar`, not `thin_evidence`).** Maximum lexical distance from
a just-flipped referent is the point.

**LANDING-DAY CROSS-LANE CONSEQUENCE — S-11 carries this.** `class=name_evidence_weak`
going flat is a *correct* consequence and will read as signal loss to the sre
lane (frame §13). S-11's landing note states the retirement, the instant, and the
successor dimension by name.

**AMENDED AT rev 5 — the note is now a HANDOVER note, and its honest scale is
stated with it.** Because the FNLI bar takes the population the retiring class
serves, S-11 states predecessor, instant **and a successor that fires**, rather
than two flat lines. The volume is small and must be said so: VERDICT §3.3
measured that population at **1 in 12,660 replayed cells** (an ORGANIC booking
where the park was correct; ZERO on the ad population). The handover is
**correct by construction and near-silent by volume** — both halves, or the sre
lane re-reads a working instrument as a broken one (CT-10 / DF-16).

### V-4 — the metric-label shape (FROZEN — and its transport truth)

```
NAME_EVIDENCE_MATCH = Counter(
    "autom8y_ebi_name_evidence_match_total",
    "Name-evidence matcher outcomes, by name shape and outcome.",
    ["shape", "outcome"],          # <- UNCHANGED: exactly two labels
)
```

- Labels UNCHANGED at two. Only the `outcome` VALUE DOMAIN changes (V-1).
- **`tier` MUST NOT be added** — functionally determined by `outcome`, so zero
  information for multiplied series against the module's own ceiling (SVR-10).
- **`office` MUST NOT be added** — 42 clinics × 3 shapes × 8 outcomes breaches
  both the low-cardinality contract and the ceiling (SVR-10). Per-office counts
  live on the persisted plane (§7).
- ★ **TRANSPORT TRUTH (SVR-1/1b).** This counter **does not reach CloudWatch**;
  the EMF bridge is unmerged (#1123). It is a unit-test/local surface only. **It
  is not the count surface and no sprint may report it as one.**

### V-5 — the log-event shape (FROZEN — THIS IS THE LIVE SURFACE)

> "ONE event name, emitted on ALL FOUR outcomes, carrying the outcome as a field
> -> `stats count() by evidence` is the rate." — `extract_fields.py:261-262`

**MINT one INFO event, `name_evidence_outcome`, emitted on EVERY outcome
including `read_failed`.** Frozen field set:

| field | type | notes |
|---|---|---|
| `shape` | enum | `full_name` \| `first_name_last_initial` \| `initials` |
| `outcome` | enum | V-1, all eight |
| `tier` | enum | V-2 |
| `office` | str | `redact_uuid(ctx.chiropractor_guid)` (`utils/redact.py:52-71`) |
| `candidates_considered` | int | pool size at the 90-d ceiling |
| `candidates_gated` | int | passed the comparator |
| `candidates_in_effective_window` | int | after §4's narrowing — I-5's positive control |
| `rows_before_dedupe` | int | **T-02** — plurality erased upstream (SVR-14) |
| `plurality_suppressed` | bool | `rows_before_dedupe > candidates_considered` — a POOL-level FACT. **Definition UNCHANGED at rev 6; its CONSEQUENCE is now conditional** (RS-19): it no longer predicts any particular outcome, so it must be read beside `winner_is_collider` |
| `winner_is_collider` | bool\|null | **NEW at rev 6 (RS-19); null-condition corrected at rev 7.** Did the CHOSEN candidate carry a phone key the fetch saw twice? **Three deliberately-distinct states:** `false` = a candidate WAS chosen and is not a collider (asked and answered) · `true` = a candidate was chosen and IS a collider · `null` = **no candidate was chosen, or provenance is unknown** (could not be asked). A `false` on an UNBOUND outcome is therefore correct, not a divergence — on `lead_id_unresolved` a candidate was chosen and the STAGE refused the id, so both planes read `false`. **Two-sided by construction** — emitted on binds AND refusals, so `plurality_suppressed=true` with `outcome=matched` is readable as "scoping fired" rather than "the lever stopped firing". A BOOLEAN: never the key, never a phone, never a hash (C-9) |
| `read_completeness` | enum | **NEW at rev 8 (DF-40).** The READ-COMPLETENESS axis, orthogonal to `outcome` and to `tier`. **CLOSED at three:** `complete` = every read leg answered · `partial` = ≥1 leg FAILED and ≥1 leg ANSWERED · `none` = every leg failed, the read did not happen. **ALWAYS present on every emission.** `unknown` is deliberately NOT a member: the discriminator is computed inside the loop that ran the legs (`activation_read_client.py:799-819`), which cannot fail to know what it ran; a member only a defect could emit is not a member. A call site that cannot know its own completeness has found **a seam defect to SURFACE, not an `unknown` to emit** |
| `read_legs_failed` | int | **NEW at rev 8.** How many legs raised. **ALWAYS present.** `0` ⟺ `complete`; `== legs attempted` ⟺ `none`; strictly between ⟺ `partial` |
| `read_failed_leg_status` | str | **NEW at rev 8.** **THE STATUS CARRIED** — this is the field that retires the cross-service trace join. The `code` ClassVar of the raised `ActivationReadError` subclass, verbatim (`ACTIVATION_READ_UNAVAILABLE` \| `ACTIVATION_READ_CONTRACT_ERROR` \| `ACTIVATION_READ_REQUEST_ERROR` \| `ACTIVATION_READ_ERROR` \| the auth/scope subclasses' codes — `activation_read_client.py:206-245`), or the literal `unknown` when a non-`ActivationReadError` escaped the leg. **ABSENT — omitted from the line, never `null`** — when `read_completeness = "complete"`. Companion field `read_failed_leg` (`status_open` \| `status_null`, the two legs at `activation_read_client.py:177-182`) rides beside it under the same presence rule |
| `window_days_pool` | int | the fetched window (90) |
| `window_days_effective` | int | the shape's window after narrowing |
| `undated_retained` | int | §4's honesty field |
| `top_gap` | float\|null | `top.score - runner_up.score`; null when <2 gated |
| `attribution_key` | str | sha256, §5 — joins the log plane to the row plane |
| `dedup_basis` | enum | `identity` \| `message_id` \| `nonce` — denominator quality |
| `persisted` | bool | did the §5 row write succeed |

> **★ THE NULL DISCIPLINE, STATED SO THE TWO PLANES CANNOT COLLIDE (rev 8).**
> `winner_is_collider` and `top_gap` use `null` to mean **could not be asked**
> (rev 6/rev 7). The rev-8 fields therefore use **OMISSION**, never `null`, for
> their "nothing to describe" state, and their DISCRIMINATOR
> (`read_completeness`) is what says so. A `read_failed_leg_status: null` meaning
> "no leg failed" would invert the line's own established null-semantics inside
> one JSON object — one reader's `null` would be the other reader's opposite, at
> the plane, with nothing to tell them apart. Refused by construction. The full
> convention is frozen at
> `CONTRACT-name-the-zero-kind-vocabulary-2026-09-05.md §3 (KNC)`.

**The five existing per-outcome lines are RETAINED UNCHANGED** —
`name_evidence_matched` (`:219`), `name_evidence_below_floor` (`:140`),
`name_evidence_ambiguous` (`:115`), `name_evidence_organic` (`:175`),
`name_evidence_read_failed` (`:476`). They are the human/ops layer; the new line
is the countable layer. This is the S-4 FIX-1 F-A1 pattern applied a second time.

> **A SIXTH ops line is MINTED at rev 8: `name_evidence_read_partial`** (WARNING),
> carrying `shape`, `read_failed_leg`, `read_failed_leg_status`, `error_type` and
> the survivors' count. It is minted **because F-M1 landed the mark as a FIELD**
> and not as a ninth outcome — the frame's WS-A item (4) conditions the sibling on
> exactly that answer. It is the human/ops layer; **the countable layer stays ONE
> line.** Third application of the S-4 FIX-1 pattern (a shared denominator line
> beside the detail lines), not a replacement of them.
>
> **NEW-1's cost note extends by one row, stated rather than discovered:** the six
> ops lines do **not** carry `read_completeness`. An operator reading only the ops
> layer cannot compute the partial rate; that is the countable line's job and it
> is the reason the countable line exists. No code change to any retained line.

**NEW-1 — what "RETAINED UNCHANGED" costs, stated rather than discovered (added
at rev 3; the five lines are NOT changed).** Two of the five —
`name_evidence_matched` and `name_evidence_organic` — carry a field named
`candidates_considered` whose value is `NameMatchResult.candidates_considered`,
i.e. **the count the matcher SCORED**, which is this table's
`candidates_in_effective_window`, **not** this table's `candidates_considered`.
The other three (`below_floor`, `ambiguous`, `read_failed`) do not carry the
field at all. Under a biting window the ops line and the countable line
therefore publish two different numbers under one field name. This is the
pre-contract vocabulary (one window, so the two counts were one number)
surviving into a post-contract world that MINTED the distinction.

**RULED: DOCUMENT. The five lines stay RETAINED UNCHANGED and no code changes.**
The reasons are recorded so a later seat does not read the silence as oversight:

1. **No machine consumer reads it.** Every counting surface takes the pool value
   from a different plane: the counts reader reads the **row**
   (`name_evidence_counts.py:299`, over `scan_attribution_rows`); I-3 counts
   `name_evidence_outcome` events; `plurality_suppressed` is computed against
   `pool.pool_size` on the set itself. The two ops lines feed a human and
   nothing else.
2. **The countable line already carries both counts on every request**
   (`match_lead.py:285-289`) — pool and narrowed, side by side, by construction.
   An ops reader who needs the distinction has it there, always. The human layer
   does not owe it a second time.
3. **"RETAINED UNCHANGED" is the load-bearing half of the S-4 FIX-1 F-A1
   pattern, not a convenience:** mint a new countable surface, leave the human
   surface alone, so saved queries and ops muscle memory survive the change.
   Renaming a field on the human layer to satisfy a vocabulary that layer does
   not participate in inverts the pattern and makes ops pay for the countable
   layer's precision.
4. **Changing the VALUE under the unchanged name is refused outright.** A label
   whose referent silently changes is the denominator-integrity breach V-3
   exists to prevent — and it is the specific thing this clause was written to
   forbid.

**The residual hazard is the AUTHORING one, and it already bit once** (D-2,
BLOCKING at S-09 limb (a)): a seat wiring the narrowed value into a pool-named
V-5 field. It is guarded in three places on the head — `match_lead.py:267-276`,
`:440-441`, and `attribution_witness.py:262-266`, which names the collision in
the code's own words. **DEFER DF-36:** rename the INTERNAL
`NameMatchResult.candidates_considered` attribute to name its true referent,
leaving **both wire keywords untouched** (read-sites are exactly two:
`match_lead.py:538`, `:623`). **Trigger: the next sprint that edits either ops
line's log call, or any change adding a THIRD reader of that attribute.** DF-36
is **not** an S-09 limb (b) item; nothing on this train builds it.

**PII:** `office` redacted at the log site. No names. No raw phones. See §8 C-9
for what `phone_hash` does and does not buy.

### V-6 — the persisted row schema (FROZEN)

| attribute | type | value |
|---|---|---|
| `pk` | S | the attribution key, §5 |
| `ns` | S | **`attribution\|name_evidence`** — unhashed, server-side filterable |
| `created_at` | N | epoch seconds |
| `shape` | S | V-1 shape |
| `outcome` | S | V-1 outcome |
| `tier` | S | V-2 tier |
| `chiropractor_guid` | S | **full** guid — opaque office selector (§8 C-9a) |
| `lead_id` | N | present **iff** `tier ∈ {high, weak}`. **THE lead reference. Never `phone`.** (T-01) |
| `bound_phone_hash` | S | present iff bound — the CAS partner for `lead_id` (M-d / T-01, T-08) |
| `phone_row_arity` | N\|null | rows the point read saw for that phone; `null` when unknown (T-01's arming event) |
| `candidates_considered` | N | |
| `candidates_gated` | N | |
| `candidates_in_effective_window` | N | |
| `rows_before_dedupe` | N | T-02 |
| `winner_is_collider` | BOOL\|null | **NEW at rev 6 (RS-19); null-condition corrected at rev 7.** Mirrors the V-5 field on the row plane, on T-02's own precedent (the dedupe pair was ruled onto the line AND the row together) — which is what keeps CT-8's row-vs-log two-sided check able to compare them. **The states are carried here IDENTICALLY, not by reference, so the row schema is readable alone:** **Three deliberately-distinct states:** `false` = a candidate WAS chosen and is not a collider (asked and answered) · `true` = a candidate was chosen and IS a collider · `null` = **no candidate was chosen, or provenance is unknown** (could not be asked). A `false` on an UNBOUND outcome is therefore correct, not a divergence — on `lead_id_unresolved` a candidate was chosen and the STAGE refused the id, so both planes read `false`. Row **==** line on `(outcome, tier, winner_is_collider)` in every case |
| `read_completeness` | S | **NEW at rev 8 (DF-40).** Mirrors the V-5 field on the row plane, on T-02's own precedent (the dedupe pair was ruled onto the line AND the row together) — which is what keeps CT-8's row-vs-log two-sided check able to compare them. **The states are carried here IDENTICALLY, not by reference:** `complete` = every read leg answered · `partial` = ≥1 leg failed and ≥1 answered · `none` = every leg failed. **The `none` state never appears on a row**, because `outcome = read_failed` writes no row at all and must keep writing none (`match_lead.py:174-181`) — see V-8.11. Row **==** line on `read_completeness` in every case where a row exists |
| `read_failed_leg_status` | S | **NEW at rev 8.** The failed leg's typed error code, carried identically to V-5. **ABSENT when `read_completeness = "complete"`** — omitted, never null |
| `window_days_pool` | N | |
| `window_days_effective` | N | |
| `undated_retained` | N | |
| `dedup_basis` | S | `identity` \| `message_id` \| `nonce` |
| `contradiction_status` | S | **ABSENT at write.** Reserved for W-FLAG limb (b); disjoint state attribute mirroring `corroboration_status` (`idempotency_ddb.py:452-500`) |
| `ttl` | — | **MUST BE ABSENT.** TTL-FREE by construction (SVR-3) |

**No `phone`, no `email`, no `contact_name`, no `office_phone`, no raw name of
any kind** on this row.

### V-7 — the contradiction-evidence vocabulary (FROZEN — new in rev 2)

Folded from THREAT §4.3 / M-g. R-M6 predicate (i)'s natural payload is **two
patient names**; serializing them would put a stronger identifier into a flag
than the flag's own subject carries. The comparison is therefore performed
**inside** the listener and only its CLASS is emitted:

| field | domain | notes |
|---|---|---|
| `name_agreement` | `none` \| `prefix` \| `exact` | the class, never the strings |
| `contradicting_lead` | `lead_id` when resolvable, else `phone_hash` | prefer the unique key (T-01); the hash is the fallback, with §8 C-9's caveat |
| `contradiction_kind` | `lead_booked_separately` \| `phone_resolves_elsewhere` \| `duplicate_appeared` | R-M6's three predicates (ruling `:56-59`) |
| `flag_key` | sha256 | §6, the distinctness token |
| `source_trust` | `gated` \| `ungated` | T-13 — see §6 |

**No name, no partial name, no initials string** may be serialized into a flag,
a count, a receipt or a row. (T-11 additionally records that
`initials_detected` already logs raw initials today and R-M4 is about to raise
its volume — pre-existing, out of this contract's scope, routed in §12 R-7.)

### V-8 — invariants (checkable; the qa-adversary's pins)

1. `winner is not None` **⟺** `tier ∈ {high, weak}`. (Today `WEAK_EVIDENCE` sets
   `winner=None, contenders=(top,)` — `name_evidence.py:588-598`.)
2. `outcome == "matched"` ⟺ `tier == "high"`; `outcome == "matched_weak"` ⟺
   `tier == "weak"`; every other outcome ⟹ `tier == "none"`.
3. The persisted `outcome`/`tier`/`shape` triple **equals** the emitted
   `name_evidence_outcome` triple for the same `attribution_key`. A divergence is
   the I-3 false-green detector (§7).
4. `candidates_gated <= candidates_in_effective_window <= candidates_considered
   <= rows_before_dedupe`. The order is V-5's own field definitions read in
   sequence: the comparator gates the **narrowed** set, so gating can only
   REMOVE from `candidates_in_effective_window`; §4's narrowing can only REMOVE
   from the 90-day pool; the dedupe can only REMOVE rows. `candidates_gated <=
   candidates_considered` is unchanged **as an assertion** — at rev 3 it holds
   by transitivity rather than as a written leg. **Corrected at rev 3 (D-2b);
   the rev-2 text and the receipt are in §R.**
5. `match_name_evidence` remains **pure — no I/O, no clock, no logging**
   (`name_evidence.py:495`). The persistence port is called by the STAGE.
6. `AMBIGUITY_EPSILON > RECENCY_MAX_BONUS` is a live structural invariant
   (`:178-186`) that **R-M5 deliberately breaks**. S-05 replaces it explicitly
   and pins the replacement; it does not weaken it silently.
7. **A bound row always carries BOTH `lead_id` and `bound_phone_hash`.** Neither
   alone identifies the record the matcher actually scored (T-01).

8. `read_legs_failed == 0` ⟺ `read_completeness == "complete"`.
9. `read_legs_failed == <legs attempted>` ⟺ `read_completeness == "none"`.
10. `read_completeness == "complete"` ⟹ `read_failed_leg` and
    `read_failed_leg_status` are **ABSENT** from both planes. Not null — absent.
11. `read_completeness == "none"` ⟺ `outcome == "read_failed"` ⟺
    `persisted == false` ⟺ **no V-6 row is written.** This extends V-8.3's
    three-plane agreement to the new axis rather than weakening it.
12. Where a V-6 row exists, `row.read_completeness == line.read_completeness` for
    the same `attribution_key`. A divergence is the I-3 false-green detector.

**And the two-sidedness leg, stated as an invariant because the predicate
requires it two-sided:**

13. The three cells are mutually exclusive and jointly exhaustive over every
    read: `(no_candidates, complete)` = a genuinely empty pool ·
    `(no_candidates, partial)` = one leg failed with zero survivors ·
    `(read_failed, none)` = both legs failed. **`stats count() by outcome,
    read_completeness` separates all three with no trace join.**

---

## §4 F-M2 — RESOLVED: the per-shape window

> **RULING: option (e) — ONE fetch at the 90-day pool ceiling, then a PURE
> per-shape narrowing on `LeadCandidateSet` at the STAGE layer.**
> `ActivationReadClient` is UNCHANGED. No second HTTP call. No config field.
> No terraform.

### Full option slate (enumerated before the recommendation)

| # | option | verdict | reason |
|---|---|---|---|
| a | second constructor parameter / per-call `window_days` override on `ActivationReadClient` | REJECTED | I-5's positive control needs BOTH the 90-d and tight counts on the same request; with (a) that costs a SECOND HTTP round-trip per INITIALS mail — the instrument's own arming evidence becomes a recurring production cost and doubles the 429 surface this service has been burned by. |
| b | post-filter inside `match_name_evidence` | REJECTED | Windowing is the READ layer's job — the set is documented as "the office-scoped, **window-bounded** candidate set" (`activation_read_client.py:503-504`). Moving it in requires a `now` argument, eroding the purity contract at `:495` that makes W-CAL's fixture replay exact (frame R-20). |
| c | a new config field | REJECTED | PC-5 proved `activation_lead_window_days` is **not plumbed to terraform**. A config-shaped lever nothing sets is a born-mute lever — instrument I-8's exact class. |
| d | a second `ActivationReadClient` instance | REJECTED | (a)'s cost plus a second cold-start construction and token consumer, for no gain. |
| **e** | **a pure `LeadCandidateSet.narrowed(window_days)` at the stage** | **SELECTED** | below |

### Why (e)

1. **The set reconstructs its own fetch anchor — so the narrowing needs NO
   clock.** `window_start = anchor - timedelta(days=lead_window_days)`
   (`:571`) and BOTH `window_days` and `window_start` ride the frozen set
   (`:284-298, :617-621`, SVR-11), so `anchor == window_start +
   timedelta(days=window_days)` exactly. `narrowed()` is a pure function of the
   set alone. This is the mechanical fact that makes (e) strictly dominate (a),
   (b) and (d).
2. **C-2 guarantees one fetch is sufficient by RULING, not by luck** — "the
   INITIALS window narrows inside it, never widens" (R-M9 / frame C-2).
3. **I-5's positive control becomes free and always-available.** Both counts are
   in hand on EVERY request; the instrument is proven on the first request where
   they differ, and until then the pair is visibly identical — the honest reading
   of "unproven".
4. **W-CAL's grid gets N windows from ONE fetched set** (frame R-20).
5. **Zero terraform** (SVR-8; shape `:1146`).

### The frozen mechanism

- `LeadCandidateSet.narrowed(window_days: int) -> LeadCandidateSet` — pure;
  returns a new frozen set with `window_days`/`window_start` recomputed and
  `candidates` filtered on `created_at`. Identity when
  `window_days >= self.window_days`. **`rows_before_dedupe` is carried through
  unchanged** (below).
- `SHAPE_WINDOW_DAYS: dict[NameShape, int]` — a **module constant in
  `name_evidence.py`** beside the scoring constants (`:167-186`). **Not a config
  field** (rejected option (c)).
- The stage applies it between fetch and match. **VALUES are G-4's**, set at
  S-09 off W-CAL's measured cells.

### T-02 — `LeadCandidateSet` MUST carry `rows_before_dedupe` (new in rev 2)

`fetch_lead_candidates` dedupes candidates by phone across its two status legs
(`activation_read_client.py:595-608`), `rows_before_dedupe` is **logged** at
`:614` but is **not a field on `LeadCandidateSet`** (`:617-621`) — SVR-14,
re-derived here. Consequences, in the order they bite:

1. **Two distinct leads sharing a phone collapse into ONE candidate**, so
   `len(scored_all) == 1` routes to `_floored(1, "single_gated_candidate")`
   (`name_evidence.py:600-601`) and **the AMBIGUOUS branch at `:608-620` cannot
   execute for that population.**
2. **R-M3 makes this bite harder, not softer.** Today that construction PARKS;
   post-landing it BINDS. The `matched_weak` safety net is applied to a candidate
   whose plurality was erased before the matcher ever saw it.
3. **It biases the evidence G-4's word is read off.** Collision rates measured
   over a phone-deduped candidate set **under-report collisions by
   construction**, biasing the forgiveness bar toward permissiveness. This is a
   first-order finding for S-02, not a footnote — see §12 R-8.

**FROZEN AT THE SEAM (this contract's part):** `rows_before_dedupe` becomes a
field on `LeadCandidateSet`, is preserved by `narrowed()`, and is carried onto
the V-5 log line and the V-6 row together with the derived
`plurality_suppressed` boolean. This is a one-field change to the very dataclass
§4 already amends, so it costs this wave nothing.

**AMENDED AT rev 6 (RS-19) — the seam gains a second carrier, `collided_keys`.**
`LeadCandidateSet` ALSO carries `collided_keys` — the phone keys the fetch saw
**≥2** times — computed in the same dedupe loop, beside `rows_before_dedupe` and
`pool_size`, and **preserved by `narrowed()` unchanged**, exactly as those two
are. It describes the FETCH, not the view, so the narrowing-invariance the whole
T-02 argument rests on is preserved rather than punctured. Three coherence legs
bind the two representations together: the set is non-empty **iff**
`rows_before_dedupe > pool_size`; `len(collided_keys) <= rows_before_dedupe -
pool_size` (one key seen three times drops two rows and collides one key, so the
bound is an inequality); and `collided_keys` is a subset of the fetched
candidates' keys **AS FETCHED ONLY** — a narrowing may filter a collided
survivor out, and that leg is therefore not re-asserted on the narrowed view.

★ **`collided_keys` IS AN IN-PROCESS JOIN KEY AND NOTHING ELSE.** It holds raw
phones and is never logged, emitted, persisted or counted; only the derived
BOOLEAN `winner_is_collider` crosses a serialization boundary (V-5, V-6, C-9).

★ **CONSEQUENCE, STATED NOT ABSORBED.** Because collision identity is
fetch-level, a survivor whose twin lies OUTSIDE the narrowed window is still a
collider and is still refused. That is conservative — the cost is RECALL, never
a mis-attribution — and it is the price of the invariance. Window-aware
collision detection is the alternative; it is RECORDED as residue R-6a, not
built.

**NOT FROZEN HERE — routed, and SPOKEN at rev 6:** whether a plurality-suppressed
candidate should **refuse**, **force-WEAK**, or **bind as scored** is a
mis-attribution-risk disposition of F-P2's shape. **G-4 answered it: RS-8 =
`refuse`, amended by RS-19 to `refuse` SCOPED TO THE COLLIDING CANDIDATES.** The
limb and the SCOPE are orthogonal — all three limbs remain expressible and all
three are now scoped, so a later sitting can change the limb as a VALUE. The mechanism makes all three expressible and makes
the population *countable* either way; the disposition is S-05's proposal and
G-4's word. **What is NOT permitted is binding a plurality-suppressed candidate
while the suppression is invisible** — that is the state today, and shipping
R-M3 on top of it without the field would deepen it.

### The undated-candidate sub-fork — RULED at mechanism, FLAGGED at policy

`created_at` is nullable and an undated candidate is **NOT** rejected by the
90-day window today (SVR-12, `:712`); the recency bonus already declines to
impute a date ("candidates with no `created_at` receive zero, which is stated
rather than imputed", `name_evidence.py:471-472`).

- **MECHANISM (ruled): `narrowed()` RETAINS undated candidates and emits
  `undated_retained`.** (i) a narrowing must not become a silent pool CHANGE,
  which C-2 forbids; (ii) recall-first (R-M1) biases toward retention; (iii)
  retention keeps both behaviours measurable against each other, whereas
  dropping erases the population from the measurement.
- **POLICY (flagged to G-4): retain vs drop.** One named constant flips it; no
  rework either way. W-CAL should report the undated sub-population per cell.

---

## §5 F-M3 — RESOLVED: where the WEAK tag persists (+ the authority answer)

> **RULING: option (c) — a NEW, TTL-FREE attribution-witness row on the shared
> `ebi-forwarding-idempotency` DynamoDB table, namespace
> `attribution|name_evidence`, written from the `match_lead` stage through an
> injected Protocol port. This is PACKET §2 Residence C.**
>
> **AUTHORITY ANSWER (stated on the tag's OWN terms, per PACKET §9):** the tier
> tag is **served record CONTENT, not metadata**, so R-A3's ADMIN-GRADE metadata
> limb *never covered it in the first place*; and at Residence C it crosses no
> service boundary, so **no S2S write class is minted and no mechanical
> authorization control exists at all**. **W-TIER's tag persistence is therefore
> NOT gated on G-5** — and the honest converse: **the operator's word at G-2 is
> the only control on it.**

### Full option slate

| # | option | verdict | reason |
|---|---|---|---|
| 0 | log-only | **REFUSED — TWICE** | frame §5: a WEAK bind that is "not counted" is one of three doctrine falsifiers; shape S-01 exit `:151-155`: "log-only fails the doctrine. A record mark is required." **And now a second, independent refusal: THREAT T-15.** The phone path resolves and RETURNS before name evidence is ever consulted (SVR-17, `match_lead.py:305-323`), so R-M6 predicate (ii) — "a phone lands on the weakly-bound record and resolves to a different lead" — can only be detected against a **persisted** mark. Log-only does not merely weaken the doctrine; it makes one of R-M6's three predicates **unimplementable**. |
| a | additive attribute on the existing `booking\|{posture}` intent row (`book_contente._intent_attributes`, `:221-260`) | REJECTED | **7-day TTL** (SVR-2) against a 1–2-week lead→booking lag (R-M4, U-2): the reaper deletes the tag before the contradiction it enables can arrive. This is the exact defect `record_witness` was minted to cure — "an ephemeral-lifetime mechanism silently imported into an of-record duty" (`idempotency_ddb.py:256-258`). Also created only for allowlisted offices, only after the ad-lead gate passes (`book_contente.py:509`) and after `book_appointment` succeeds — so parks, gate-refusals and scheduling failures carry no tag, losing W-COUNT's denominator. |
| b | additive attribute on the TTL-FREE `obligation\|{posture}` row (`:263-283`) | REJECTED | TTL-free but minted for **live-effective bookings only** (`:269-275`) — the same denominator loss; and it overloads a row with a different owner-duty (INV-2 recovery). |
| **c** | **a new TTL-FREE `record_witness` row in a disjoint `ns`, written at the matcher-outcome instant (Residence C)** | **SELECTED** | below |
| d | a metadata mark on the LEAD/BOOKING record in autom8y-data via S2S (Residence A) | REJECTED FOR THIS WAVE | The residence the frame assumed. PACKET §2 shows SEC-001 has **no jurisdiction** there — the real control is the data service's own fail-closed `*_ALLOWED_CALLERS` plane (`booking_corroboration_plane.py:57-78`), which EBI's identity is already on twice (SVR-18). And PACKET §9 finding 2: the tier is a **served field**, so at Residence A it would be a cross-service write of record content — a *stronger* claim than the flag's, which R-A3's METADATA limb may be unable to carry at all. Kept as the successor form (§12 R-3). |
| e | the contente booking POST payload | **REFUSED — MECHANICALLY IMPOSSIBLE** | SVR-15: the client refuses any payload that drifts from the frozen 6-field contract **at the wire** (`contente_booking_client.py:19-24`). It is also a clinic-visible surface, i.e. F-P1 / R-A4(2) territory. |
| f | a new DynamoDB table, or a GSI | **REFUSED — IMPOSSIBLE** | SVR-6: no `CreateTable`, and a GSI needs `UpdateTable`; both "absent by design". |
| g | a new route on `autom8y-asana` (Residence B) | REJECTED | The only residence SEC-001 governs — but PACKET §2 records that SEC-001 is in **OBSERVE** mode (dispatcher-asserted; packet UV-P-2), where the gate logs `write_authz_would_deny` and **proceeds anyway**. So the allowlist entry would not be a control today. It is also a second repo, a second deploy path, and a new public surface for a tag nothing outside EBI reads. |

### Why (c)

1. **TTL-FREE by construction, not by a large value** (SVR-3). The reversal
   horizon R-M6 needs is structural, not a fuse someone chose well.
2. **Predicate (ii) becomes buildable** (T-15 / SVR-17) — see option 0 above.
3. **Zero IAM change, zero terraform.** The intake role already holds `PutItem`
   on this exact table (SVR-4); the table name is wired unconditionally from a
   `data` source on all three lambdas (`main.tf:278`). One image event.
4. **Complete denominator.** Written at the MATCHER-outcome instant inside
   `match_lead`, upstream of every later stage, so it covers all eight outcomes.
   R-M7 asks for *match* outcomes, not booking outcomes (`ruling:60-62`).
5. **The additive-attributes contract already exists with two callers**
   (`book_contente`, `park.py:282-297`) — a third instance of an established
   idiom, not a new mechanism.
6. **It composes with §6 and §7 for free** — the same unhashed `ns` the reconcile
   sweep already knows how to filter server-side (`idempotency_ddb.py:597-645`).

### The frozen mechanism

**The port (DIP).** `match_lead` MUST NOT import `DdbIdempotencyStore`. It
depends on a Protocol — the precedent is explicit: "The pipeline stages … depend
on the `ReceiptSink` Protocol, NOT on Slack/Asana/DDB concretes (DIP). This is
the seam FORK-A selected" (`receipts/sink.py:3-8`). The concrete is wired in
`handler.py` from the store already constructed at `:940-952`. Absent-is-no-op.

**The key.** `pk = sha256(netstring-preimage)` over the length-prefixed tuple

```
("name-evidence-attribution", shape, subject, to, appt_dt, identity)
```

using the SAME `<len>:<value>` composition and the SAME `_identity_discriminator`
chain both existing keyspaces use (`park.py:51-89`, `book_contente.py:106-135`).
The leading literal differs in both length AND value from `"terminal-decline"`
and `"bookingv2"`, so no cross-keyspace collision is possible (`park.py:56-62`).

**`dedup_basis`.** On this path `contact_phone` is absent by construction
(`match_lead.py:344-348`) and `contact_email` typically is too, so the chain
usually resolves to `message_id`; absent that it falls to `uuid4` and the row is
NOT re-delivery-idempotent. The row records which basis was used so any count can
state its own quality instead of asserting distinctness it does not have.

**`lead_id` + `bound_phone_hash` together (T-01).** The candidates carry no
`lead_id` — `phone` is the only identity on that wire
(`activation_read_client.py:266-273`) — so the bind resolves the integer id by a
point read on a column the same service formally refuses to pick on (SVR-13). The
row therefore records **both** the resolved `lead_id` and the
`bound_phone_hash` of the candidate that was actually scored, plus
`phone_row_arity` when the point read can report it. **This is the seam's part
of T-01's mitigation and the enabler of §6's CAS.** Whether a bind should
*refuse* when the point read is ambiguous is S-05's proposal and G-4's word
(§12 R-8); what this contract forbids is binding without recording which record
was scored.

**Failure posture.** Best-effort-LOUD, never fail-closed onto the booking —
mirrors `park.py:298-311`. A write failure MUST emit
`name_evidence_attribution_write_failed` and set `persisted: false` on the V-5
line, because a silently failing writer is precisely I-3's false green.

**Ordering.** ONE write, at the stage's terminal disposition for this mail.
Never two writes, never write-then-update.

### The authority answer, in full (shape S-01 exit `:151-155`; PT-01 `:644`)

**PACKET §9 Reading 1 is REFUSED; Reading 2 is ADOPTED.**

1. **The tag is CONTENT, not metadata.** W-COUNT's exposable counts are keyed on
   tier (frame `:551-552`), the landed certificate's arithmetic reads it (R-L3,
   `:81-83`), and F-P4 exists precisely because its product meaning is served.
   R-A3's ADMIN-GRADE limb covers "reversible business-ledger METADATA writes …
   **never record content**" (`RULING-decision-space-amendments-2026-08-26.md:73-76`).
   A field a served count and a certificate both read fails that test — so the
   metadata limb **never reached the tag**, in either direction.
2. **Frame `:649` is REFUSED as inheritance.** "the persisted mark rides
   W-FLAG/W-TIER's F-M3 answer … the mark inherits F-A1's answer" transfers
   authority across two acts that fail the same test differently — admission by
   analogy in the precise sense R-A3 `:77-79` forbids. This contract does not
   inherit it and no downstream sprint may.
3. **At Residence C the question dissolves rather than being answered
   permissively.** The write is a DynamoDB `PutItem` by the intake Lambda's own
   execution role against EBI's own operational store (SVR-4). No service
   boundary is crossed; no S2S write class is minted; SEC-001's gate is on
   `autom8y-asana`'s 26 Asana-write routes and is not on this path;
   autom8y-data's `*_ALLOWED_CALLERS` plane is not on this path either. PACKET §2
   row C states the consequence plainly and this contract adopts it verbatim in
   substance: **"No cross-service authority is created, so there is nothing to
   allowlist."**
4. **THE HONEST CONVERSE, STATED RATHER THAN ENJOYED.** Residence C is the
   cheapest branch *because* it has no mechanical control. There is no allowlist
   to fail, no gate to deny, no fail-closed plane to refuse it. **The only
   control on this write is the operator's word at G-2 (the deploy word /
   F-A2).** That is a real reduction in defence-in-depth relative to Residence A,
   and it is on the record here so the operator is choosing it rather than
   inheriting it. The compensating controls this contract does impose are:
   V-6's field fence (no PII on the row), C-9's evidence fence, §7's two-sided
   count check, and the fact that the write is *additive and reversible by
   deletion* — none of which is an authorization control.
5. **The act the SPRINT performs is code authorship**, which R-A3 `:71-73` places
   at USER-GRADE. The runtime write is performed by the deployed service. The
   landing remains W-LAND's ADMIN-GRADE-by-effect merge (frame §8, F-A2).

**What this does NOT rule.** The contradiction FLAG write (W-FLAG limb (b)) is
NOT ruled here — G-5 and S-07's packet own it. See §6 for the single thing the
F-M4 ruling hands S-07.

---

## §6 F-M4 — RESOLVED: where the contradiction listener lives

> **RULING: option (b) — the existing `contente-reconcile` Lambda's live
> 15-minute schedule.**
> **Residence of limb (a): C (EBI's own state) — an emit, no write, no
> cross-service authority, therefore no allowlist and, again, the operator's
> word as the only control. The residence of limb (b)'s STAMP is S-07's and
> G-5's, not this contract's.**

### Full option slate

| # | option | verdict | reason |
|---|---|---|---|
| a | synchronous in `match_lead` at the next same-office booking | REJECTED | (i) **I-2's only positive control is structurally unavailable** — the `contradiction_listener_ran` denominator heartbeat, "a count of weak binds EXAMINED, emitted even when zero are flagged" (shape S-06 `:363-367`), cannot be emitted by a listener that runs only when traffic arrives. (ii) Two-candidate contests at one office are ~0–1/month (frame I-6), so the listener would be near-permanently unrun while reading identical to "nothing to say" — I-2's named false-green verbatim. (iii) It adds a read to the hot path inside the ~29 s API-GW budget (`activation_read_client.py:494-495`). |
| **b** | **the `contente-reconcile` schedule** | **SELECTED** | below |
| c | data-service side (autom8y-data) | REJECTED | Second repo, second deploy path, second soak interaction (shape D-5), for a detector that needs EBI's tier — which autom8y-data does not hold. |
| d | a new dedicated scheduled Lambda | REJECTED | A new terraform module (schedule, role, log group, deadman) — the fenced surface (SVR-8; shape `:1146`) — for zero capability (b) lacks. |
| e | EventBridge rule on `BookingEmailReceived` | REJECTED | New rule + target (terraform), and re-creates (a)'s traffic dependence: event-driven means no denominator heartbeat. |

### Why (b)

1. **It is LIVE** — `contente_booking_reconcile_enabled = true` on
   `rate(15 minutes)` (SVR-7). A surface to extend, not to build.
2. **The heartbeat is free.** Only a scheduled locus can emit
   `weak_binds_examined` every sweep regardless of findings. That IS I-2's
   positive control.
3. **Zero IAM, zero terraform** — the reconcile role already holds
   `Scan`/`UpdateItem`/`GetItem` on this table (SVR-5).
4. **The exact pattern already exists on this Lambda.** The OR-4 corroboration
   pass is a decoupled observe-only phase on the same schedule, "DECOUPLED from
   the redrive gates … observe-only, so it may run while the write/redrive phase
   stays inert" (`variables.tf:341`). Limb (a) emit-only / limb (b) write-gated
   is the same shape, already deployed.
5. **The scan idiom already exists** (`idempotency_ddb.py:597-645`).
6. **The S2S read client for the predicates already lives there**
   (`booking_corroboration_client.py`, same ServiceAccount token provider).

### The frozen mechanism

- **Scan predicate:** `ns = "attribution|name_evidence"` **AND**
  `created_at >= now - CONTRADICTION_HORIZON_DAYS`, server-side. Never a
  client-side filter over a full-table page stream. **No GSI** (SVR-6).
- `CONTRADICTION_HORIZON_DAYS` is a named module constant; VALUE from W-CAL's
  lag distribution (U-2) at S-09 under G-4. Emitted on the heartbeat so the bound
  is never invisible.
- **Limb (a) is EMIT-ONLY** (shape S-06 `:349-350`): a typed event and a counter.
  **No record write.** `contradiction_status` stays ABSENT.
- **Evidence is V-7's vocabulary.** `{name_agreement, contradicting_lead,
  contradiction_kind, flag_key, source_trust}`. **Never a name.** The two-name
  comparison predicate (i) is made of happens *inside* the listener; only its
  class leaves (THREAT §4.3 / M-g).
- **Predicate (ii)'s mechanism, stated because it exists nowhere today
  (SVR-17 / T-15):** the phone branch returns at `lead_found_by_phone`
  (`match_lead.py:305-323`) without ever consulting name evidence, so the
  comparison must be performed by the *listener* — joining the persisted
  attribution row (`lead_id`, `bound_phone_hash`, `chiropractor_guid`,
  `created_at`) against later phone-matched bookings. This is precisely why §5
  had to be record-resident.
- **Every emission carries `phone_row_arity`** for the flagged lead (T-01's
  arming event: the guard cannot fire once, honestly, without it).
- **T-13 — mail-derived contradictions are not trusted on their face.** A forged
  booking mail (plaintext `From`; no SPF/DKIM on the booking path) can
  manufacture a contradiction. Every emission carries `source_trust ∈ {gated,
  ungated}` reflecting whether the contradicting signal itself cleared the
  ad-lead gate discipline. A listener that flags an `ungated` contradiction
  without saying so is an attacker-steerable ops action; an `ungated` flag is
  emitted but MUST be labelled, and ops-facing consumers treat `ungated` as
  advisory only.

**The at-most-once problem an emit-only listener creates — and its cure.**
Without a stamp, a 15-minute sweep re-emits the same flag forever, yielding a
retry-inflated LEVEL rather than a distinct count — the identical pathology the
codebase already solved for parks (`terminal_decline` on every delivery vs
`terminal_decline_parked` carrying `newly_recorded`, `semantic_alarms.tf:89-101`).
Cure: **every emission carries a stable `flag_key`**

```
flag_key = sha256(netstring("name-evidence-contradiction",
                            attribution_key, lead_id, bound_phone_hash,
                            contradiction_kind))
```

so `count_distinct(flag_key)` is the distinct count and the raw count is the
sweep level, both labelled. Note the key binds **`lead_id` AND
`bound_phone_hash`** — this is M-d's CAS tuple, minted at limb (a) so limb (b)
inherits it rather than re-deriving it.

**Forward-compatibility with limb (b), stated now:** when G-5 lands, limb (b)
stamps `contradiction_status` **under the same `flag_key`, as a CAS on
`(lead_id, bound_phone_hash, bound_at)`** (M-d / T-01, T-08); a CAS miss is a
no-op plus `contradiction_flag_superseded`, never a blind overwrite. That makes
the emission at-most-once and removes the row from the candidate scan via
`attribute_not_exists(contradiction_status)`. Limb (b) is then strictly additive
and changes no vocabulary. **The emit-only limb's `flag_key` IS limb (b)'s
idempotency token.**

**Heartbeat (frozen):** event `contradiction_listener_ran`, INFO, **every sweep
including zero-flag sweeps**, fields `weak_binds_examined`, `flags_emitted`,
`distinct_flag_keys`, `ungated_flags`, `horizon_days`, `scan_pages`.

### What this hands S-07 (surfaced, NOT resolved)

The F-M4 ruling gives S-07 a **second, narrower candidate residence** for the
flag STAMP alongside the one the frame assumed:

- **(i) as framed — Residence A:** a mark on a LEAD/BOOKING record in
  autom8y-data. PACKET §2: SEC-001 has no jurisdiction; the real instrument is
  the fail-closed `*_ALLOWED_CALLERS` plane, on which EBI's identity already
  appears twice (SVR-18) — a real gate on day one.
- **(ii) newly available — Residence C:** a disjoint `contradiction_status`
  attribute on **EBI's own** attribution row, written by the reconcile Lambda's
  own IAM role — structurally the same act as the `corroboration_status` stamp
  already shipped and running (`idempotency_ddb.py:452-500`;
  `production.tfvars:146`). **And, per §5.4, structurally the same absence of a
  mechanical control.**

**Which residence the operator is asked to authorize, and at what tier, is
S-07's packet question and G-5's word.** This contract does not rule it, does not
prefer one, and explicitly does not admit (ii) by analogy to the corroboration
stamp — R-A3 `:77-79` forbids exactly that move, and PACKET §2 names the
one-decorator theater path as the cheap wrong turn. It records only that the
slate has two members, that (ii) may make the word cheaper, and that **cheaper
here means less controlled, not more safe.**

**Identity note the packet supplies and this seat corroborated (SVR-18):** one
ServiceAccount `sa_e92a293f22b9f7aed2650ba0d3866b94` is the runtime identity of
the whole EBI service (`RUNBOOK.md:132`). **A grant scoped to "the reconcile
lambda" is not expressible at the identity layer** — any allowlist entry widens
all three lambdas (intake · contente-reconcile · forwarding-nudge, C-11). S-07's
blast-radius section must say so; S-01 does not rule it.

---

## §7 F-M5 — RESOLVED: the exposable count surface

> **RULING: EBI-RESIDENT. Repo residence = `autom8y`, single train, ONE image
> event, ZERO terraform, ZERO second deploy path.** The persisted attribution
> rows of §5 **are** the count surface. The read is (i) a versioned READ CONTRACT
> and (ii) a scheduled aggregate emitted by the reconcile Lambda — a process that
> is not the writer. The `name_evidence_outcome` log line is the cross-check
> plane.

### Full option slate

| # | option | repo | 2nd deploy path? | verdict |
|---|---|---|---|---|
| a | new API-GW route on the intake HTTP API | autom8y | **YES** — a new `aws_apigatewayv2_route` is terraform, applied only by `workflow_dispatch` + `environment=production` with required reviewers (SVR-8) | REJECTED. Both existing routes carry **no authorizer** (`main.tf:424-436`), so a data-read route would additionally mint an authn question this wave has no mandate for. |
| b | CloudWatch log metric filters | autom8y | **YES** (terraform) | REJECTED, and directly refused by the ruling: "No CloudWatch dashboard/alarm work is commissioned by this ruling" (`:63-64`); shape fences it out (`:1141`). |
| c | Prometheus metrics API read | — | — | **REFUSED — TRANSPORT-DEAD.** SVR-1/1b: the counters do not reach CloudWatch. Believing otherwise is the born-mute class `observe.py:215-222` names. |
| d | a read endpoint in autom8y-data over a tier persisted there | autom8y-data | **YES** — second repo, second deploy, second soak interaction (shape D-5) | REJECTED; rides §5 option (d) and its stronger content-write claim. |
| e | `dashboard_ui` reads the DDB table directly | contente | yes (credential + network path) | REJECTED — consumer access path unresolved (U-4); agency-view presentation is out of scope. |
| **f** | **persisted rows + a versioned read contract + a scheduled non-writer aggregate, all in EBI** | **autom8y** | **NO** | **SELECTED** |

### Why (f)

1. **R-M7's bar is EXPOSABLE, not EXPOSED** (`ruling:60-63`). A durable,
   structured, documented store IS a data surface; an endpoint is a consumer
   convenience R-M7 does not commission and that costs the wave its single-train
   property.
2. **I-3's positive control is satisfiable with no new surface.** The **intake**
   Lambda writes; the **contente-reconcile** Lambda reads — different function,
   different IAM role, different process, different schedule. A genuine
   non-writer read, available today at zero cost. (See §12 R-2: the intake role
   has no `Scan`, which is *why* this separation is structural rather than
   conventional.)
3. **One scan serves both §6 and §7** — the listener already pages this namespace
   every 15 minutes; the aggregate rides the same page stream.
4. **Zero terraform is a fence, not a preference** (SVR-8; shape `:1146`).
5. **Two-sided by construction.** Row plane and log plane are written by one code
   path but read through entirely different transports; their counts MUST agree,
   and a divergence is a live detector for a silently failing writer — I-3's
   false green made *detectable* rather than merely warned about.
6. **It keeps served content out of the business ledger.** Because the counts key
   on `tier` (V-2), the tier is content (§5). Siting the count surface on EBI's
   own store is what keeps this wave from writing a served field into the ledger
   of record — the consequence PACKET §9 finding 2 warns about.

### The frozen mechanism

- **The store:** the §5 rows. Per-office × shape × tier is a group-by over
  `chiropractor_guid × shape × tier` — exactly R-M7's cut.
- **The aggregate:** the reconcile sweep emits ONE event,
  `name_evidence_outcome_counts`, per sweep, carrying `{window_days, per_office:
  [{office, shape, tier, outcome, n}], totals, plurality_suppressed_n}` with
  `office = redact_uuid(chiropractor_guid)` at the log site.
- **Count window** `created_at >= now - COUNT_WINDOW_DAYS`, **default 90** —
  aligned to `log_retention_days = 90` (`variables.tf:61-65`) so the row plane
  and the log cross-check plane share one horizon and (5) is valid over its whole
  domain.
- **The read contract** is an artifact in `autom8y-asana` (S-08's exit): the V-6
  schema, the namespace, the group-by, the window semantics, the `dedup_basis`
  and `plurality_suppressed` caveats, and a worked query. Versioned, because U-4
  is unspecified.
- **A non-writer read helper** ships in EBI: one module, two callers (the sweep,
  and an operator-invocable script), so the documented query is proven executable
  rather than asserted.

### What this is NOT

- **BUILT-UNCONSUMED, and that label travels with the artifact** (shape S-08
  `:435-439`). No consumer exists (R-19). I-3 must not be read as healthy on a
  surface nobody reads.
- **Not cumulative-since-activation.** R-L5's cumulative window belongs to the
  CERTIFICATE (S-10) over a different substrate. Conflating them would let a WEAK
  count leak toward the certificate, which C-7 / R-L3 forbids.
- **Growth clause.** Rows are TTL-FREE, accruing at ~17/day (~6 k/year, frame
  R-4). **Review trigger: when the `attribution|name_evidence` namespace exceeds
  50 000 items, the sweep's aggregate must move to a rolled-up aggregate row.**

---

## §8 Contract clauses — binding on S-04, S-05, S-06, S-08

- **C-9 (PII, restated as a contract clause — CORRECTED in rev 2).** Tags, flags,
  counts and receipts carry `phone_hash` / opaque ids, **never names, never raw
  phones**. No `contact_name`, `resolved_name`, `phone`, `email` or
  `office_phone` on any row, event or count minted by this wave.
  ★ **`phone_hash` is a PSEUDONYMOUS CORRELATION TOKEN, NEVER a
  de-identification primitive.** It is `sha256(phone).hexdigest()[:8]` —
  unsalted, unkeyed, truncated to 32 bits over a ~10^10 NANP preimage space
  (SVR-16); the module's own word is "Opaque correlation token"
  (`name_evidence.py:267`), which is the honest one. **No artifact of this wave
  may argue "it carries only hashes, therefore no personal data."** The honest
  formulation is: *the hash bounds casual disclosure in a log or a Slack line; it
  does not bound re-identification.* At 32 bits it also **collides**, so it is
  not an identity either: **prefer `lead_id` wherever a lead reference is needed**
  (V-6, V-7), and use `phone_hash` only as the fallback and as the CAS partner.
- **C-9b (evidence fence — new in rev 2).** A contradiction's own evidence is
  more sensitive than its subject: predicate (i)'s natural payload is two patient
  names. **No name, partial name, or initials string may be serialized into a
  flag, evidence field, count, row or receipt.** The comparison happens inside
  the listener; only V-7's `name_agreement` class leaves (THREAT §4.3 / M-g).
- **C-9a (the one place row and log diverge, stated deliberately).** The DDB row
  carries the **full** `chiropractor_guid`; the log line carries
  `redact_uuid(...)`. The redaction discipline is stated for **log-emission
  sites** (`redact.py:4-6`) and the guid is an opaque business identifier, not
  personal data. Consequence: row plane and log plane join on an 8-hex prefix;
  with ~42 activated clinics collision risk is negligible but is **stated, not
  assumed**.
- **C-I (identity — new in rev 2).** One ServiceAccount is the runtime identity
  of all three EBI lambdas (SVR-18). No control, allowlist entry or grant in this
  wave can be scoped to one lambda; any such entry widens all three (C-11).
- **C-T (no terraform).** No clause may be implemented by a terraform change. A
  sprint needing one has left the seam: surface it (SVR-8; shape `:1146`).
- **C-S (no new store).** No new table, no GSI (SVR-6) — a design assuming one is
  void on arrival.
- **C-P (purity).** `match_name_evidence` stays pure. Persistence, logging and
  windowing are the STAGE's (V-8.5).
- **C-D (DIP).** Stages depend on Protocols, not on DDB/Slack/Asana concretes
  (`receipts/sink.py:3-8`). The attribution port is `None`-able, absent-is-no-op.
- **C-A (atomic per-repo PR).** Code → `autom8y`; artifacts → `autom8y-asana`. No
  mixed commits. **Sprints author; S-11 merges** (shape §7 prescribed 16).
- **C-V (vocabulary).** §3 is frozen. Internal refactors granted; vocabulary
  changes are not. A ninth outcome, a fourth tier or a third metric label is a
  seam defect to surface.
- **C-R (retirement, not re-pointing).** No live label string, metric label value
  or CloudWatch dimension value may be re-pointed at a new referent (V-3).
- **C-L (loudness).** Every new write and emitter is best-effort-LOUD: failures
  counted and surfaced, never swallowed, never escalated into a 5xx on the
  booking path (`park.py:298-311`).
- **C-X (no silent plurality) — AMENDED AT rev 6.** No bind may be recorded
  without `rows_before_dedupe`, `plurality_suppressed` **and
  `winner_is_collider`** (T-02) and without both `lead_id` and
  `bound_phone_hash` (T-01). The *disposition* of a plurality-suppressed or
  arity-ambiguous bind is G-4's; its **visibility** is not negotiable.
  ★ **Why the third field is not optional.** Before RS-19 a bind at a
  suppressed pool was IMPOSSIBLE; after it, that is the COMMON case. Recording
  such a bind carrying only the pool-level flag would leave a reader unable to
  distinguish "the scoping fired correctly" from "the lever silently stopped
  firing" — CT-12's exact shape, one lever over.
  ★ **And the key never leaves the process.** `collided_keys` is an in-process
  join key: never logged, emitted, persisted or counted. Only the derived
  boolean crosses the boundary (C-9, C-9b).

---

## §9 Contract traps (CT-n) — silent failures converted to pre-flight gates

> Numbered `CT-n` to keep a clean namespace against the threat model's `T-nn`.
> The right-hand column names the threat-model entry where one exists.

| # | trap | tell | gate | THREAT |
|---|---|---|---|---|
| CT-1 | **Transport trap.** A sprint reports "the counter shows N" as live evidence. | any exit claim citing `autom8y_ebi_name_evidence_match_total` from a live environment | SVR-1: it does not reach CloudWatch. Live claims cite the LOG or ROW plane. | — |
| CT-2 | **TTL trap.** The tag is written with `record_intent` because it is the familiar method. | the Item carries a `ttl` key at any value | V-6 requires `ttl` ABSENT; `record_witness`, never `record_intent` (SVR-2/3). | — |
| CT-3 | **Re-pointed-label trap.** `weak_evidence` is kept and made to mean "bound". | the string survives the landing anywhere | V-3: RETIRE on all three surfaces. | — |
| CT-4 | **Born-mute `below_bar` trap.** G-4 sets the bar so nothing can fall under it. **At rev 5 the bar is PER SHAPE, so the trap is per shape too**: one shape's declared-unreachable bar must not be read as the outcome being mute. | `below_bar == 0` with `matched_weak > 0` and no bar-adjacent W-CAL cell — **and, at rev 5, read PER SHAPE**: for a shape whose bar is STRUCK the tell is a NON-SIGNAL by declaration, not evidence of a born-mute bar | S-09 states the bar's *reachability* alongside its value **for EVERY key, plus the aggregate**; UNREACHABLE is not 0, and a shape with no score axis is a THIRD state (N/A) that is neither. ★ **rev 6: the per-shape row states BAR-reachability, NOT OUTCOME-reachability.** `below_bar` is reachable for FULL_NAME and for exact-FNLI HIGH by a different route — the plurality lever — and at rev 6 that route fires only when the winner is itself a collider. A reader taking the N/A row as "this shape can never take this outcome" is wrong. | — |
| CT-5 | **Vacuous tight-window trap.** Both windows return the same set because no office has an ad candidate in either. | `candidates_in_effective_window == candidates_gated` on 100 % of requests | both counts on EVERY line (V-5); the guard is UNPROVEN until one differs. | I-5 |
| CT-6 | **`uuid4` dedup trap.** No `message_id` ⇒ nonce key ⇒ a re-delivery double-counts. | `dedup_basis == "nonce"` on a non-trivial share | `dedup_basis` required (V-6); S-08 states its distinctness quality rather than claiming it. | — |
| CT-7 | **Re-emitting listener trap.** Emit-only ⇒ the same contradiction every 15 min forever. | `flags_emitted` grows monotonically with sweeps at constant rate | stable `flag_key`; `count_distinct(flag_key)` is the distinct count; both reported. | T-07 |
| CT-8 | **Silent-writer trap.** Counts read zero for every office because the writer never persisted. | row-plane count ≠ log-plane count for the same window | §7(5) two-sided check; `persisted: false`; `name_evidence_attribution_write_failed`. | I-3 |
| CT-9 | **Gate-refused blind spot.** A bind the ad-lead gate later refuses leaves no `booking\|*` row. | — | moot *because* §5 writes upstream of the gate — named so no sprint "optimizes" the write down into `book_contente` and re-opens it. | — |
| CT-10 | **Dimension-goes-flat trap.** `class=name_evidence_weak` flatlines at landing and reads as an outage. **Rev-5 addition — the second half of the same trap:** a retirement whose named successor ALSO never fires is indistinguishable from a broken instrument, which is the state the rev-4 shape-agnostic strike would have shipped. | both `name_evidence_weak` and `name_evidence_below_bar` reading zero after the landing instant | S-11's landing note names retirement, instant, successor (V-3) **and asserts the successor is REACHABLE for at least one shape** — mechanically, via the per-shape reachability statement CT-4 now requires. | — |
| **CT-11** | **Pick-on-a-dirty-column trap.** The bind's `lead_id` is the output of an unadjudicated point read on a column the same service formally refuses to pick on. | a bound row carrying `lead_id` with no `bound_phone_hash`, or `phone_row_arity` absent where obtainable | V-6 + V-8.7 require both identities together; §6's `flag_key` binds both; disposition of an ambiguous arity → G-4. | **T-01** (SVR-13) |
| **CT-12** | **Deduped-plurality trap.** Two distinct leads sharing a phone collapse to one candidate, `_floored(1, "single_gated_candidate")` fires, and the AMBIGUOUS branch cannot execute — while `ambiguous == 0` reads as "no ambiguity in the corpus". **Rev-6 second face (RS-19): the SCOPING itself can fail in either direction** — silently not firing (regression to the office-wide refusal, which parks every bind at an office for every shape) or firing too widely (a collider binding). | `candidates_gated == 1` with `rows_before_dedupe > candidates_considered` — **and, at rev 6, two-sided on the scope**: `plurality_suppressed=true` with EVERY outcome at an office `below_bar` (scoping not firing), or `winner_is_collider=true` with `outcome ∈ {matched, matched_weak}` (firing too widely) | §4: `rows_before_dedupe` + `collided_keys` on the set, `plurality_suppressed` + `winner_is_collider` on the line and the row. **S-02 must report it per cell or its collision rates are biased low.** **And the arming rule TA-1 applies** — a suite that arms a non-ratified limb cannot see this trap at all (§R rev 6 Clause 6). | **T-02** (SVR-14) |
| **CT-13** | **"Hashes ⇒ non-PII" trap.** A compliance or PR claim leans on `phone_hash` as de-identification. | any artifact asserting the flag/count carries no personal data because it carries hashes | §8 C-9: unsalted 32-bit truncation of a direct identifier; pseudonymous, not de-identified (SVR-16). | **T-10** |
| **CT-14** | **Forged-contradiction trap.** A forged booking mail manufactures a contradiction and the flag becomes the audit justification for a wrong ops re-point. | a flag emitted with no `source_trust` field, or an `ungated` flag consumed as authoritative | §6: `source_trust ∈ {gated, ungated}` on every emission; `ungated` is advisory only. | **T-13 / T-14** |
| **CT-16** | **ABSENCE OF THE MARK IS NOT `complete`** (NEW at rev 8; matcher-lane namespace). Pre-DF-40 rows and lines carry none of the rev-8 fields, so a filter on `read_completeness = "complete"` over a window spanning the landing instant silently drops the entire pre-landing population. | any count, dashboard or W-COUNT class filtering `read_completeness` across the DF-40 landing instant | State the landing instant and report the pre-landing population separately, or restrict the window to post-landing. **A count that cannot say which side of the landing it is on reads "measured zero, meter under repair".** | **name-the-zero S-04 / S-09** |
| **CT-15** | **Log-only regression trap.** A later sprint "simplifies" the row away because the log line already carries everything. | any proposal to drop the §5 write on the grounds that V-5 duplicates it | R-M6 predicate (ii) is only detectable against a persisted mark (SVR-17); log-only makes it unimplementable *and* fails frame §5. | **T-15** |

> **CT-16 — ABSENCE OF THE MARK IS NOT `complete`.** Rows and lines emitted before
> DF-40 lands carry none of the rev-8 fields. A query, dashboard, W-COUNT class or
> W-3-style count that filters `read_completeness = "complete"` over a window
> spanning the landing instant **silently drops the entire pre-landing
> population** — a denominator defect wearing a filter's name, and the same class
> as the one PT04-C14 cured on the other side.
> **Pre-flight gate:** any count over a window containing the DF-40 landing
> instant MUST state that instant and report the pre-landing population
> separately, or restrict its window to post-landing. **A count that cannot say
> which side of the landing it is on reads "measured zero, meter under repair".**

---

## §10 FLAGGED — not resolved here

**PRODUCT / POLICY — the operator's alone.** The last wave's floor calibration
went wrong by resolving one of these as if it were mechanism (shape §A
`:1252-1257`).

| fork | gate | what this contract adds |
|---|---|---|
| **F-P1** — is a wrong bind that is FLAGGED (not reversed) acceptable on a clinic-visible surface? | G-3 | Nothing. The mechanism half is S-05's read (UV-P-2). This contract does not touch `ctx.resolved_phone`'s propagation. THREAT T-18 is S-05's input, not this seam's. **Wording corrected at rev 4 (RS-12); the rev-3 text is in §R. G-3 was spoken 2026-09-04 = `propagate` (R-24) — the gate is closed; the product question this row names is not re-opened, answered or dissolved here.** |
| **F-P2 / F-P3** — the acceptable mis-attribution / collision rate; the thin-evidence forgiveness bar | G-4 | The bar's *name* (`below_bar`), its reachability tell (CT-4), and — **new at rev 5** — its **ARITY**: the bar is **PER SHAPE**, one key per shape that has a score axis, as PT-02 §I blank (2)'s own title (*"**FNLI** thin-evidence forgiveness bar (R-M3)"*) has read since 2026-09-03. **Still no value.** **Plus a correction to the evidence the word will be read off: CT-12 biases measured collision rates LOW.** |
| **F-P4** — what a WEAK count MEANS to the agency | G-4-adjacent | The count is emitted per tier; the meaning is product semantics, unresolved (U-4). Its existence is also what makes the tier *content* (§5). |
| **new — undated-candidate eligibility in a narrowed window** | G-4 | §4 rules the MECHANISM (retain + count), flags the POLICY. One constant flips it. |
| **new — disposition of a plurality-suppressed or arity-ambiguous bind** | G-4 | §4 / §5 make it VISIBLE and expressible three ways (refuse / force-WEAK / bind-as-scored). The choice is S-05's proposal and the operator's word. **Visibility is frozen; disposition is not.** **SPOKEN 2026-09-04: RS-8 = `refuse`, amended by RS-19 to `refuse` SCOPED TO THE COLLIDING CANDIDATES — the gate is closed and the SCOPE is frozen at rev 6 (§4 T-02); the LIMB remains a value a later sitting may change.** Recorded on the rev-4 F-P1/G-3 precedent so a certifier does not read an open gate that has closed; the product question this row names is not re-opened or answered here. |

**AUTHORITY — words, not work.**

| fork | gate | status |
|---|---|---|
| **F-A1** — the contradiction-flag write class | G-5 | **NOT ruled here.** §6 hands S-07 a two-member residence slate with the control that actually governs each, and the identity note (C-I). Explicitly NOT admitted by analogy (R-A3 `:77-79`). |
| **F-A2** — within-wave vs successor initiative | G-2 | Untouched. The frame's Reading-B posture stands. **Newly load-bearing:** §5.4 makes G-2 the *only* control on the tag write. |

**MECHANISM — deferred by the shape, not by this contract.**

| fork | status |
|---|---|
| **F-M6** — kill-switch terraform plumbing | A named DEFER (shape §B; `:1146`). §4 rejected config-shaped levers for the same reason F-M6 exists: an unplumbed lever is a born-mute lever (I-8). If the operator later wants `SHAPE_WINDOW_DAYS` as a real lever, the constants become plumbed variables in ONE PR — recorded, not built. |

---

## §11 UV-P ledger

**Minted by this contract:**

- `[UV-P: the agency-view backend (contente/dashboard_ui) can reach the attribution rows through some credentialed path | METHOD: deferred-to-U-4-data-contract-negotiation | REASON: F-M5 ships a durable store, a versioned read contract and a non-writer read helper; the CONSUMER's access path from a Heroku-resident app to a DynamoDB table in this AWS account is unspecified and is not this wave's to invent (R-19, U-4). The surface is EXPOSABLE per R-M7; it is not yet reachable BY THAT CONSUMER.]`
- `[UV-P: ctx.message_id is present on the JaneApp / no-phone booking mails at a rate high enough for the attribution key to be re-delivery-idempotent | METHOD: deferred-to-S-08-measurement-of-dedup_basis-distribution | REASON: the identity chain on this path skips resolved_phone and contact_email by construction (match_lead.py:344-348), so message_id is load-bearing for distinctness and its live presence rate is unmeasured (CT-6).]`
- `[UV-P: the three R-M6 contradiction predicates are computable from read surfaces the contente-reconcile Lambda already holds | METHOD: deferred-to-S-06-surface-inventory at the F-M4 locus | REASON: the Lambda holds an S2S ServiceAccount read client and DDB Scan, but whether predicates (i)/(ii)/(iii) are answerable WITHOUT a new autom8y-data read endpoint was not derived here. If a new endpoint is needed that is a second repo, and S-06 must surface it, never absorb it.]`
- `[UV-P: no other consumer reads the TerminalDecline class value name_evidence_weak | METHOD: deferred-to-S-11-landing-note cross-lane check | REASON: the ebi-terminal-decline-by-class metric filter is the one consumer found at origin/main (semantic_alarms.tf:71-87); dashboards, runbooks and sre artifacts outside this repo were not swept (CT-10).]`
- `[UV-P: the data_message_client.get_lead point read can report the row arity it saw | METHOD: deferred-to-S-05-client-surface-read | REASON: V-6 specifies phone_row_arity as nullable precisely because the client's ability to surface it was NOT derived here; if it cannot, T-01's arming event needs a different construction and S-05 must say so rather than emit a null forever.]`

**Inherited from the two S-07 artifacts, carried NOT discharged:** the packet's
UV-P-2 (**SEC-001 is in OBSERVE mode — dispatcher-asserted, not verified by this
seat**; §5 option (g) rests on it and would need re-derivation if the residence
ever changed to B) and the threat model's own ledger (§11 there).

**Inherited from the frame, NOT discharged here:** UV-P-1 (W-CAL substrate),
UV-P-2 (weak-bind clinic visibility → G-3), UV-P-3 (ops re-point queue exists),
UV-P-4 (peer socket listener), UV-P-5 (F-A2 grant reach), UV-P-6 (the R-M3
population arrives), UV-P-7 (estimative deadline), UV-P-8 (WATCH volume table).

---

## §12 Residues

- **R-1 — `weak_evidence`'s historical population is not backfilled.** Rows and
  counts begin at the landing instant; the pre-landing park population lives only
  in 90-day log retention. Backfilling would require imputing a tier for
  decisions made under a superseded floor.
- **R-2 — the intake Lambda cannot read what it writes.** Its role is
  `PutItem`/`GetItem`/`UpdateItem` with no `Scan` (SVR-4). This is *why* §7's
  non-writer read is structural, and it also means no intake-side
  self-verification is possible: read-after-write proofs run from the reconcile
  role or from operator credentials.
- **R-3 — the tier is not resident in the business ledger of record.** If a
  consumer ever needs `tier` on the lead or booking row, that is §5 option (d):
  a second repo, a schema change, the `*_ALLOWED_CALLERS` plane, and a word that
  R-A3's metadata limb may be unable to carry because the tier is served content
  (PACKET §9 finding 2). Recorded as the successor form, deliberately not built.
- **R-4 — `AMBIGUITY_EPSILON > RECENCY_MAX_BONUS` is a live invariant this wave
  breaks.** S-05 owns the replacement and the test that pins it (the F-A5 gap).
  This contract fixes only that the replacement must be stated and pinned.
- **R-5 — the count window (90 d) and the certificate window (cumulative since
  activation, R-L5) are deliberately different.** Anyone reading both must not
  reconcile them.
- **R-6 — the kill switch still moves two subsystems.**
  `name_evidence_match_enabled` unwires S-6's trust ground as well
  (`handler.py:764-775`). Unchanged here; restated because W-LAND's rollback
  story depends on it.
- **R-7 — `initials_detected` logs raw initials today** (`match_lead.py:449-454`;
  THREAT T-11) and R-M4 is about to raise that path's volume. Pre-existing, out
  of this contract's scope, and it sits in tension with C-9b. **Routed to S-04**
  (which owns the initials routing) as a surface-don't-absorb item.
- **R-8 — ★ ESCALATION TO S-02: the calibration evidence is biased LOW before it
  is measured.** CT-12/T-02: collision rates replayed over a phone-deduped
  candidate set under-report collisions by construction, and CT-11/T-01: the
  ground-truth "which lead did this booking bind" is itself the output of a
  pick on a column the service refuses to pick on. **W-CAL must report
  `rows_before_dedupe` and the duplicate-phone sub-population per cell, or the
  bar G-4 sets will be read off a permissive measurement.** This is a
  denominator-integrity finding on the evidence base, not a code defect in the
  matcher, and it is the single most consequential thing rev 2 adds.

---

## §13 Consumption map — who binds to what

| sprint | binds to |
|---|---|
| **S-02** (W-CAL) | **§12 R-8 (escalation)** · §4's `rows_before_dedupe` semantics · CT-11, CT-12. Not a binder of the seam, but the seam changes what its denominators must carry. |
| **S-04** (W-ROUTE) | §4 in full (narrowing, `SHAPE_WINDOW_DAYS`, undated rule, `rows_before_dedupe` **and `collided_keys`** carriage with their coherence legs (rev 6), both logged counts) · V-1 shapes · V-5 window/dedupe fields · CT-5, CT-12 · C-T, C-P · **R-7** (raw initials, surface don't absorb) |
| **S-05** (W-TIER + W-RECENCY) | §3 in full (V-1…V-8) · §5 in full (port, key, `dedup_basis`, `lead_id`+`bound_phone_hash`, failure posture, ordering) · **the authority answer: S-05 is NOT gated on G-5, and G-2 is the only control** · CT-2, CT-3, CT-4, CT-6, CT-8, CT-11, CT-12, CT-15 · C-9, C-9a, C-9b, C-P, C-D, C-V, C-R, C-L, C-X · R-4 |
| **S-06** (W-FLAG limb a) | §6 in full (locus, scan predicate, horizon, emit-only, V-7 evidence vocabulary, `flag_key`/CAS tuple, `source_trust`, heartbeat) · V-6 `contradiction_status` reserved-absent · predicate (ii)'s mechanism (SVR-17) · CT-7, CT-14 · C-9b, C-I |
| **S-07** (packet) | §5's authority answer as the *boundary* of what is already outside the class (and the refusal of frame `:649`) · §6's two-member residence slate with each residence's real control · C-I. S-07 specifies; it inherits no preference. |
| **S-08** (W-COUNT) | §7 in full (residence, aggregate event, window, read contract, non-writer read) · V-6 schema · V-5 fields · CT-1, CT-6, CT-8, CT-12 · C-9's pseudonymity correction · C-9a's prefix-join caveat · the BUILT-UNCONSUMED label |
| **S-09** (assembly) | Sets every VALUE this contract only NAMED: `SHAPE_WINDOW_DAYS`, the **per-shape forgiveness bar map** (one value per shape carrying a score axis; rev 5), the recency thresholds, `CONTRADICTION_HORIZON_DAYS`, `COUNT_WINDOW_DAYS`, and the two new G-4 dispositions (undated candidates; plurality-suppressed binds) — each from a measured W-CAL cell plus G-4's word. Re-derives composition at the assembled head (C-5). |
| **S-11** (landing) | The V-3 retirement note (CT-10): dimension, instant, successor. |
| **name-the-zero S-04** (WS-A read-kind) | V-5's three rev-8 fields · V-6's two rev-8 attributes · V-8.8–V-8.13 · Clause 5's ops sibling · Clause 6's no-new-label rule · **CT-16** · and, as its own frozen seam, `CONTRACT-name-the-zero-kind-vocabulary-2026-09-05.md` in full |
| **name-the-zero S-09** (assembly) | Applies this delta as its own atomic asana PR · asserts V-8.8–V-8.13 by test at the assembled head · asserts the CONSTRAINT-1 six-field clause by test |

---

## §R Revision log

### rev 8 — 2026-09-05 — **MECHANISM** (the read-completeness axis, DF-40)

**Applied at name-the-zero S-09** from
`.sos/wip/CONTRACT-matcher-tier-tag-rev8-DELTA-2026-09-05.md` (authored S-01,
`architect`, 2026-09-05T03:55:42Z), as its own **atomic asana PR** per frame C-9.
Reads taken at autom8y `origin/main` `52995b26`.

**Authority:** `.sos/wip/frames/name-the-zero.shape.md:184-256` (S-01 exit:
*"F-M1 is answered against a CLOSED vocabulary … So the answer is a rev-8
contract act either way and the contract says which and why"*) +
`.sos/wip/CONTRACT-name-the-zero-kind-vocabulary-2026-09-05.md` §4 K-8.

**★ NAMESPACE NOTE (PT-01 C-5), because two contracts now carry a `CT-16`.**
Unprefixed identifiers in THIS document — `V-1`…`V-8`, `CT-1`…`CT-16`, `F-M1`…`F-M6`,
`S-04`…`S-11` — are the **matcher-recalibration** lane's. Identifiers belonging to
the `name-the-zero` wave are written with their initiative prefix
(`name-the-zero S-04`, `name-the-zero-F-M1`). The `CT-16` minted by Clause 7 is
**this document's** — the DF-40 landing-instant denominator gate. The `CT-16` in
`CONTRACT-name-the-zero-kind-vocabulary-2026-09-05.md` is a DIFFERENT trap in a
DIFFERENT namespace, and neither supersedes the other.

## §C Nature — **MECHANISM**, and the standing test answered honestly

Rev 7's standing test is *"Would any bound sprint (S-04/S-05/S-06/S-08) have built
differently under the corrected text?"* — asked of the **matcher lane's** four
binders. Rev 8 answers it in two parts, because rev 8 is not a correction:

**Part 1 — is it MECHANISM or TEXT?** **MECHANISM.** Rev 8 changes what a builder
must EMIT: three new fields on the V-5 line, two on the V-6 row, five new V-8
invariants, one new ops line, one new contract trap. The class-follows-the-edit
rule admits no other answer, and calling it TEXT to avoid the ceremony would be
the exact defect rev 7's DC-2 was raised to stop.

**Part 2 — which sprint MOVES?** Exactly one: **name-the-zero's S-04 (WS-A)**. It
is the sprint that emits the axis. No other sprint's build changes.

---

## §D Compatibility posture for the matcher lane's four binders

Written to hold under BOTH answers to UV-P-N4 (whether the matcher lane's S-08 has
landed at the instant rev 8 applies), so nothing here depends on knowing.

| binder | posture | grounds |
|---|---|---|
| **S-04** (W-ROUTE) | **UNAFFECTED.** Binds §4's narrowing, `SHAPE_WINDOW_DAYS`, `rows_before_dedupe`/`collided_keys` carriage. Rev 8 touches none of them | the new fields are on a different axis and are computed at a different layer (the read client's leg loop, not the narrowing) |
| **S-05** (W-TIER + W-RECENCY) | **UNAFFECTED.** Binds §3 V-1…V-8 and §5's persistence port | V-1 is **not touched** (Clause 1). V-8's additions are new legs, not edits to legs 1–7 (Clause 4). The persistence port gains two attributes it writes through unchanged |
| **S-06** (W-FLAG limb a) | **UNAFFECTED.** Binds §6 and V-6's `contradiction_status` reserved-absent | rev 8 adds two V-6 attributes that are neither `contradiction_status` nor a state attribute |
| **S-08** (W-COUNT) | **TOLERATES two new row attributes** — the rev-6 posture, verbatim and unchanged (`revision_6_nature`: *"S-08 tolerates one new row field"*) | S-08's aggregate must not enumerate row attributes exhaustively. If S-08 has already landed, rev 8 changes nothing it built and the attributes are simply present-and-unread. If it has not, this row is its instruction |

**One live consequence, named rather than discovered.** Rows and lines emitted
**before** DF-40 lands carry none of the new fields. **ABSENCE IS NOT `complete`.**
A W-COUNT class or a Logs-Insights query that filters on `read_completeness` over
a window spanning the landing instant silently drops the entire pre-landing
population. That is CT-16 (Clause 7).

---

## §F What rev 8 does **NOT** touch

Recorded by name so a successor cannot read the silence as an oversight, and so
the atomic PR's diff can be audited against this list:

- **V-1** — CLOSED at eight. No ninth outcome. The `read_failed` row unchanged.
- **V-2** — the `tier` enum and its three grounds.
- **V-3** — the two-directional delta and the `weak_evidence` migration/retirement.
- **V-4** — the metric-label shape and the TRANSPORT TRUTH paragraph.
- **V-5's existing rows** — every field from `shape` through `persisted` is
  byte-identical, including `winner_is_collider`'s rev-7 null condition and
  `plurality_suppressed`'s rev-6 conditional consequence.
- **V-6's existing attributes** — including `ttl` **MUST BE ABSENT** and
  `contradiction_status` reserved-absent.
- **V-7** — the contradiction-evidence vocabulary.
- **V-8.1–V-8.7** — unchanged as written, including V-8.4's rev-3 correction.
- **§4, §5, §6, §7** — the four resolved matcher forks, their option slates, their
  frozen mechanisms and their authority answers.
- **§8's clauses, §9's CT-1…CT-15, §10, §11, §12's residues** — untouched;
  **R-4a's rev-7 disposition stands** and is not re-opened.
- **§0's realization predicate** — the matcher lane's predicate stays verbatim as
  its own §0. Rev 8 does **not** overwrite it with name-the-zero's; the two
  predicates are carried in their own artifacts and this delta's §A is
  name-the-zero's, appearing here as the delta's header, **not** as a replacement
  of §0.
- **The 6-field attribution-verdict gate request** — `_REQUEST_FIELDS` is exactly
  `("lead_id","office_phone","phone","email","guid","appt_time")`
  (`ad_lead_gate/verdict_client.py:128-135`). **No rev-8 field rides it.** A 7th
  field client-first is a 422 → `p0_attribution_read_failed` → **every booking
  refuses.** If one ever must ride: **server-first**, nullable on the
  autom8y-data `extra="forbid"` model, THEN client.

---

---
### rev 7 — 2026-09-05 — **TEXT-ONLY** (V-5/V-6 null-condition conformance · R-4a discharged)

**Authority.** `.sos/wip/CHECKPOINT-matcher-recalibration-PT-04-DELTA-2026-09-05.md`
**§D DC-2** — *"the CONTRACT must not carry a leg the head provably fails"*,
BLOCKING, **owner `architect`** — together with §A Q4 (`★ NEW`) and §C.2 residue
**R-4a**. Evidence: qa **VERDICT §13.9(b)** (the contract-text precision note) and
**§13.5** (the three-state / two-plane table, constructed own-hands at the stage
at base `84ae4094`).

**Why the text must be right, stated as DC-2 states it.** DC-2 is a
**pre-briefing** condition: PT-04 ruled the class BLOCKING because *"leaving it is
a manufactured DIVERGE at the certificate."* A document that a reader takes as
authority must not assert a behaviour its head does not have — the defect is in
the CONTRACT, not in the code. rev 7 moves the text to the mechanism; it does
not move the mechanism to the text.

**Nature — TEXT-ONLY, and the standing test answers NO.** *"Would any bound
sprint (S-04/S-05/S-06/S-08) have built differently under the corrected text?"* —
**NO**, on three grounds:

1. **The head already implements the corrected sentence.** VERDICT §13.5
   constructed the field's three states at the real stage and recorded row **==**
   line on `(outcome, tier, winner_is_collider)` in every case. S-05 built this
   semantics; rev 7 writes it down. A correction that describes what was already
   built cannot have changed what was built.
2. **No consumer reads the field yet** (VERDICT §13.9(b), verbatim: `no consumer
   reads it yet`). There is no query, aggregate or gate whose behaviour turns on
   the sentence at this landing.
3. **R-4a's word is not a build instruction** — see Clause 3. It names a
   capability that does not exist on this train and has no owner, so no sprint
   could have built it.

No mechanism, no threshold value, no seam limb, no new field, no new binder, and
**no change to any V-clause's mechanical content**. `revision_7_nature` states it
in the frontmatter's own words.

**Quotation convention.** rev 4's convention is inherited verbatim and not
restated. **Provenance:** `reads_taken_at` and `build_target_hash` are
**UNCHANGED** and still describe the contract body; rev 7 takes **no new code
reads** — its two sources are the PT-04 DELTA and the qa VERDICT, read at their
paths. The rev-5 (`e90650b4`) and rev-6 (`f5c40dd2`) provenance notes stand.

#### Clause 1 — V-5, before and after

**rev 6, verbatim:**

> | `winner_is_collider` | bool\|null | **NEW at rev 6 (RS-19).** Did the BOUND-OR-REFUSED winner carry a phone key the fetch saw twice? `null` when there is no bind or no provenance. **Two-sided by construction** — emitted on binds AND refusals, so `plurality_suppressed=true` with `outcome=matched` is readable as "scoping fired" rather than "the lever stopped firing". A BOOLEAN: never the key, never a phone, never a hash (C-9) |

**rev 7, verbatim:**

> | `winner_is_collider` | bool\|null | **NEW at rev 6 (RS-19); null-condition corrected at rev 7.** Did the CHOSEN candidate carry a phone key the fetch saw twice? **Three deliberately-distinct states:** `false` = a candidate WAS chosen and is not a collider (asked and answered) · `true` = a candidate was chosen and IS a collider · `null` = **no candidate was chosen, or provenance is unknown** (could not be asked). A `false` on an UNBOUND outcome is therefore correct, not a divergence — on `lead_id_unresolved` a candidate was chosen and the STAGE refused the id, so both planes read `false`. **Two-sided by construction** — emitted on binds AND refusals, so `plurality_suppressed=true` with `outcome=matched` is readable as "scoping fired" rather than "the lever stopped firing". A BOOLEAN: never the key, never a phone, never a hash (C-9) |

**Two defects in the rev-6 sentence, both now closed.** *"there is no bind"* was
the wrong predicate — the field reports the **CHOSEN candidate's** status, and a
candidate can be chosen without a bind resulting (`below_bar` via the bar; the
lever's refusal; `lead_id_unresolved`). And the sentence collapsed a **three-state**
field into a two-state gloss. The corrected form states the discriminator
explicitly: **`false` = asked and answered · `null` = could not be asked · `true`**.
Without that distinction a reader meeting `false` on an unbound row would read a
divergence where the mechanism is correct — which is exactly the misreading DC-2
exists to prevent.

#### Clause 2 — V-6, before and after (carried IDENTICALLY, not by reference)

**rev 6, verbatim:**

> | `winner_is_collider` | BOOL\|null | **NEW at rev 6 (RS-19).** Mirrors the V-5 field on the row plane, on T-02's own precedent (the dedupe pair was ruled onto the line AND the row together) — which is what keeps CT-8's row-vs-log two-sided check able to compare them |

**rev 7, verbatim:**

> | `winner_is_collider` | BOOL\|null | **NEW at rev 6 (RS-19); null-condition corrected at rev 7.** Mirrors the V-5 field on the row plane, on T-02's own precedent (the dedupe pair was ruled onto the line AND the row together) — which is what keeps CT-8's row-vs-log two-sided check able to compare them. **The states are carried here IDENTICALLY, not by reference, so the row schema is readable alone:** **Three deliberately-distinct states:** `false` = a candidate WAS chosen and is not a collider (asked and answered) · `true` = a candidate was chosen and IS a collider · `null` = **no candidate was chosen, or provenance is unknown** (could not be asked). A `false` on an UNBOUND outcome is therefore correct, not a divergence — on `lead_id_unresolved` a candidate was chosen and the STAGE refused the id, so both planes read `false`. Row **==** line on `(outcome, tier, winner_is_collider)` in every case |

**Why identical text rather than "mirrors V-5".** rev 6's row cell deferred the
definition to V-5 and stated only the pairing rationale, so a reader consulting
the ROW schema alone never met the null condition at all. DC-2's standard is that
the document must not carry a leg the head fails; a plane that carries **no** leg
is the adjacent defect. Carrying the triad verbatim on both planes also makes
`row == line` provable **from the text**, which is the property CT-8's two-sided
check rests on — and which VERDICT §13.5 confirms empirically in every constructed
case. **`read_failed` remains the one asymmetry, and it is pre-existing:** there is
no row at all on that outcome, so the row plane is ABSENT rather than `null`.

#### Clause 3 — R-4a: **RULED A TEXT-CONFORMANCE CORRECTION, and APPLIED**

DC-2 required this seat to rule whether correcting V-1's `matched_weak`
disposition cell is a **text-conformance correction** (rev-3's class) or a **V-1
charge** (which would move bound sprints and STOP as a fork). **Ruled:
TEXT-CONFORMANCE CORRECTION. It does not stop; it is applied here.**

**rev 6, verbatim:**

> | `matched_weak` | `weak` | YES | bind + tag + count + reversible | **MINTED** (R-M3, R-M4) |

**rev 7, verbatim:**

> | `matched_weak` | `weak` | YES | bind + tag + count + **flagged when wrong** (the REMEDY is §0's, per RS-12: restated with provenance once the record-correction primitive lands — corrected at rev 7, residue R-4a) | **MINTED** (R-M3, R-M4) |

**The ruling, with the reason it is not a V-1 charge — four legs:**

1. **What a V-1 charge IS, by this contract's own definition.** §8 **C-V** names
   it exactly: *"A ninth outcome, a fourth tier or a third metric label is a seam
   defect to surface."* A V-1 charge moves the enum's **values**, its **tier
   mapping** or its **binds?** column. rev 7 moves **none** of the three. The
   `disposition` column is a descriptive gloss on each value, not the vocabulary
   the sprints honour byte-for-byte — §3's preamble scopes that phrase to *the
   vocabulary*, and the vocabulary is the value set.
2. **The corrected word was never a build instruction, and this seat already
   found so at rev 4.** rev 4 Clause 4 recorded, of this exact cell:
   `matched_weak's three mechanical dispositions (bind, tag, count) are unchanged
   and are what the sprints build; the fourth word is a promise, and the promise
   now lives at §0.` rev 7 changes only the fourth word. A word that no sprint
   builds cannot be a charge that moves a sprint.
3. **The stronger form of leg 2 — nothing could have been built.** rev 4 Clause 1
   established that *"reversible" asserted a capability that **does not exist at
   this landing and has no owner on this train**.* The reversal act is R3's, on
   the **dre** lane. A word naming a non-existent capability with no owner is not
   a specification any sprint could have satisfied — which is precisely why it is
   the leg the head provably fails, and precisely why DC-2 wants it gone.
4. **Class consistency — the same word, twice already ruled TEXT-ONLY.** rev 4
   corrected `reversible` at **§0** (the realization predicate) and at **§10**
   (F-P1's question) and classified both as TEXT-ONLY. Ruling the third occurrence
   of the same word, correcting it to the same RS-12 wording, a *charge* would
   make the class depend on the cell's neighbourhood rather than on the edit.

**The steelman for STOPPING, weighed and rejected.** V-1 is declared CLOSED and
honoured byte-for-byte, so a maximalist reading makes ANY edit to the table a
charge. Rejected because that reading proves too much: under it §3 would be
unamendable, yet rev 5 amended **V-3** and rev 6 amended **V-5** and **V-6** —
both correctly classed MECHANISM *because they moved mechanism*, not because they
sat inside §3. The class follows the EDIT, not the section. Had the edit touched
the value string, the tier, or `binds?`, this seat would have STOPPED and returned
it to PT-04 as a fork under the PT04-C2 construction.

**Form of the replacement.** The four-item shape is kept and the promise is
**pointed at §0 rather than duplicated**. Duplicating the RS-12 sentence in a
vocabulary cell would re-create R-4a's own defect one revision later — two
independently-editable copies of one promise, which is how the cell fell out of
step with §0 in the first place.

**R-4a is DISCHARGED.** Its carriage chain closes here: registered at rev 4
Clause 4 → re-routed at rev 5 Clause 6 → re-routed at rev 6 Clause 8 → **corrected
at rev 7 Clause 3**. Owner and trigger retire with it.

#### Clause 4 — the other three "reversib" occurrences: still NOT EDITED

rev 4 identified five occurrences, edited two, and refused three with named
reasons. rev 7 edits the third (Clause 3) and **leaves the remaining two exactly
as rev 4 left them**, for rev 4's own reasons, restated so a reader does not read
rev 7's silence as a sweep:

| site | text | rev 7 |
|---|---|---|
| §5.1 | verbatim quotation of `RULING-decision-space-amendments-2026-08-26.md:73-76` — *"reversible business-ledger METADATA writes … never record content"* | **NOT EDITED.** A verbatim external quotation, used there to REFUSE the metadata limb; altering a quoted charter would break the refusal's own citation. It is also not said of the weak tier — it is said of a **write class**. |
| §5.4 | *"the write is additive and reversible by deletion"* | **NOT EDITED.** A **mechanism clause** about the §5 DynamoDB `PutItem`. A row is deletable; that is orthogonal to whether a wrong ATTRIBUTION can be un-said to the clinic, which is what RS-12 governs. Editing it would be a mechanism edit, which rev 7 may not be. |

#### Clause 5 — CT-12's two-sided tell, re-checked under the new sentence

DC-2's charge requires confirming the trap still reads correctly. **It does, and
CT-12 is NOT edited.** Checked leg by leg against the corrected states:

* **Leg 1** — *"`plurality_suppressed=true` with EVERY outcome at an office
  `below_bar`"* (scoping not firing): does not reference `winner_is_collider` at
  all. **Unaffected.**
* **Leg 2** — *"`winner_is_collider=true` with `outcome ∈ {matched,
  matched_weak}`"* (firing too widely): keyed on `true`, and the correction moves
  only the `null`/`false` boundary. VERDICT §13.5 confirms the `true` condition
  independently: *a collider winner is* `True` *under every limb; a non-collider
  is always* `False`. **Unaffected.**
* **No new false positive.** The corrected sentence makes `lead_id_unresolved`
  read `false` rather than `null`. Neither leg fires on `false`, so the state that
  moved cannot trip the trap. **CT-8** is likewise strengthened, not weakened:
  row **==** line on that outcome, which is the comparison CT-8 performs.

#### What rev 7 did NOT touch

§0 · **V-1 apart from the fourth word of ONE disposition cell — the value set,
every tier mapping, every `binds?` cell and the `status vs origin/main` column are
byte-identical, and `weak_evidence` stays RETIRED** · **V-2 · V-3 · V-4 · V-7 ·
V-8 (all seven items, including 8.1, 8.4's count chain and 8.6)** · **V-5 and V-6
apart from ONE cell each — every other field row on both planes is
byte-identical** · §1 · §2 (SVR-1..SVR-18) · §4 (including T-02 as amended at
rev 6) · §5 · §6 · §7 · **§8 (every clause, C-V and C-X included)** · **§9 (every
CT row, CT-4 and CT-12 included)** · §10 · §11 · §12 · §13. `binds`, `consumes`,
`resolves`, `flags_not_resolves`, `build_target_hash`, `reads_taken_at` and
`self_attestation_cap` are unchanged. `status` remains **FROZEN**. The rev-6,
rev-5, rev-4 and rev-3 sections of this log are unaltered, including every
verbatim quotation they carry.

**Evidence grade: `[STRUCTURAL | MODERATE]`.** Self-ref ceiling per
`self-ref-evidence-grade-rule`: this seat authored the rev-6 sentence it is now
correcting. **The finding is not self-attested** — the divergence was constructed
own-hands at the real stage by the rite-disjoint qa seat (VERDICT §13.9(b),
§13.5) and ruled BLOCKING by PT-04 (§D DC-2); this seat's contribution is the
wording and the R-4a class ruling. **No claim here is corroborated by a
rite-disjoint seat on the RULING itself, and none addresses one (H-7 unchanged —
this artifact is written for the record and the build seat, not for any
certifying seat, and none was consulted).**

---

### rev 6 — 2026-09-04 — **MECHANISM** (the plurality refusal is SCOPED TO THE COLLIDER)

**Authority.** `.sos/wip/SEAM-RULING-plurality-scope-2026-09-04.md`, on the
operator word **RS-19** (amends RS-8): *the plurality-suppressed disposition
`refuse` is SCOPED TO THE COLLIDING CANDIDATES — only the candidates that share
the duplicated phone are refused; unrelated candidates at the same office
(exact-FNLI HIGH, FULL_NAME/RS-18, lone INITIALS weak) still bind as scored.*
Evidence consumed: **qa VERDICT §12.9 N2-4**
(`.sos/wip/qa/VERDICT-matcher-recalibration-s09a-capped-pass-2026-09-03.md`,
constructed at the real stage at head `b7660a80`) and **RECEIPT ITER-4 §I4.4.1**
(`.sos/wip/RECEIPT-matcher-recalibration-s09b-2026-09-04.md`, head `f5c40dd2`).

**Nature — MECHANISM.** The standing test (*"would any bound sprint have built
differently?"*) answers **YES**. This is the second mechanism revision. It
changes the plurality lever's **SCOPE** and adds its per-candidate carrier;
it changes no count, no outcome, no tier and no metric label.

| | |
|---|---|
| **What changes** | the lever fires only when the **WINNER** is a collider; `LeadCandidateSet` gains a fetch-level `collided_keys`; the line and the row gain a boolean `winner_is_collider` |
| **S-04 (W-ROUTE)** | **MOVES.** the dedupe loop computes `collided_keys`; the set carries it with three coherence legs; `narrowed()` carries it through unchanged |
| **S-05 (W-TIER)** | **MOVES.** `apply_plurality_disposition` gains an explicit `winner_is_collider`; the emission carries the new field |
| **S-08 (W-COUNT)** | **no logic change.** The row's field set grows by one; §7's read contract is versioned, so the aggregate must TOLERATE it — confirm, do not assume |
| **S-06 (W-FLAG)** | **UNAFFECTED.** It scans on `tier = "weak"`; a population moving between outcomes changes volume, not the predicate |
| **Still true of §1** | **No threshold VALUE is chosen in this document.** rev 6 rules the lever's SCOPE; the LIMB (`refuse`) is G-4's word, recorded in §10, not authored here |

**Quotation convention.** rev 4's convention is inherited verbatim and not
restated. **Provenance:** the frontmatter's `reads_taken_at: origin/main` and
`build_target_hash` are **UNCHANGED** and still describe the contract body;
rev 6's mechanism reads were taken own-hands at `f5c40dd2` via `git show` — no
checkout switch, no worktree. rev 5's own `e90650b4` provenance note stands.

#### Clause 1 — the defect, and why it is worse than the census reads

`plurality_suppressed` is **narrowing-invariant by design**: `narrowed()`
carries `rows_before_dedupe` and `pool_size` through unchanged and the property
compares those two fetch-level numbers. That invariance is CORRECT — it is what
stops the flag reading `False` merely because a window filtered the survivor
out, which would be a denominator breach of the class V-3 guards.

Composed with an **office-wide** `refuse`, the invariance became an amplifier.
qa VERDICT §12.9 N2-4 constructed it at the real stage: an office pool
`[Priya Sharma, Nathan Wu, Zed Quill]` with `rows_before_dedupe=4` — ONE
duplicate-phone pair anywhere in the office's 90-day fetch — parks
`Priya S.` (exact FNLI, HIGH), `Priya Sharma` (FULL_NAME, RS-18's new surface)
**and** `P.S.` at `below_bar` / `plurality_refused_*`; the positive control
without the duplicate returns `matched`.

**And it reaches shapes whose own window contains no collision.** The census
reads ZERO suppressing cells at 14/21/30/45d and TWELVE at 90d, all at one
office — the naive reading is that INITIALS, ratified at 14 days, is untouched.
It is not: INITIALS reads the same **fetch-level** flag. The live traffic is
**4 of 4 matcher-reaching mails INITIALS**, so the office-wide behaviour was
maximally wrong exactly where the only observed traffic is. **Scoping does not
touch the invariance** — it keeps the flag fetch-level and adds a second,
per-candidate question beside it.

#### Clause 2 — the option that was refused, and why (the widening trap)

The obvious implementation — exclude colliders from the contest — was
**REJECTED**. Construction: collider **C** and non-collider **N** both score
8.0 at the same office.

* today, and under the ruled form: C and N tie inside `AMBIGUITY_EPSILON` →
  **`ambiguous` park**; nothing binds.
* under exclude-at-scoring: C is removed → N wins alone → **`matched` HIGH**.

That turns a refusal into a bind — a new binding population authored by an
implementation choice rather than a word, the same class rev 5 spent a whole
revision refusing at V-3 Direction A. **RS-19 narrows which candidates are
REFUSED; it says nothing about widening which candidates BIND, and a seat may
not infer the second from the first.**

**So colliders still COMPETE and the ambiguity net still sees them.** That is
the property being bought, not a residual cost: `classify_tier`'s FULL_NAME limb
states the residual risk in its own words — two different patients sharing a
name, which the ambiguity refusal is what catches — and a collided phone group
is the strongest available signal that two distinct people are in the pool. A
candidate that parks ambiguous is not "bound as scored", but it is not refused
by the PLURALITY lever either: it is refused by the AMBIGUITY lever, separately
ratified (V-8.6). RS-19 governs the first and does not reach the second.

**One structural fact makes the refusal set small and exact.** The dedupe keeps
the FIRST row per phone and skips the rest, so non-survivors are not in
`candidates` and can never be scored. "The candidates that share the duplicated
phone" therefore resolves to **exactly one survivor per collided key**.

#### Clause 3 — §4 T-02, before and after

**rev 5, verbatim — the frozen-at-the-seam paragraph:**

> **FROZEN AT THE SEAM (this contract's part):** `rows_before_dedupe` becomes a
> field on `LeadCandidateSet`, is preserved by `narrowed()`, and is carried onto
> the V-5 log line and the V-6 row together with the derived
> `plurality_suppressed` boolean. This is a one-field change to the very dataclass
> §4 already amends, so it costs this wave nothing.

**rev 6** leaves that paragraph **BYTE-IDENTICAL** and APPENDS the second
carrier — `collided_keys`, fetch-level, preserved by `narrowed()` unchanged,
with three coherence legs (set non-empty **iff** `rows_before_dedupe >
pool_size`; `len(collided_keys) <= rows_before_dedupe - pool_size`; subset of
the fetched keys **as fetched only**), the in-process-join-key PII fence, and
the stated consequence that a survivor whose twin is outside the narrowed window
is still refused (conservative; recall-only cost). Appending rather than
rewriting is deliberate: the original sentence is what four sprints built to.

**The routed paragraph, rev 5 verbatim:**

> **NOT FROZEN HERE — routed:** whether a plurality-suppressed candidate should
> **refuse**, **force-WEAK**, or **bind as scored** is a mis-attribution-risk
> disposition of F-P2's shape.

**rev 6, verbatim:**

> **NOT FROZEN HERE — routed, and SPOKEN at rev 6:** whether a plurality-suppressed
> candidate should **refuse**, **force-WEAK**, or **bind as scored** is a
> mis-attribution-risk disposition of F-P2's shape. **G-4 answered it: RS-8 =
> `refuse`, amended by RS-19 to `refuse` SCOPED TO THE COLLIDING CANDIDATES.** The
> limb and the SCOPE are orthogonal — all three limbs remain expressible and all
> three are now scoped, so a later sitting can change the limb as a VALUE.

#### Clause 4 — V-5 and V-6, before and after (the observability decision)

**The question rev 6 had to answer:** is the per-candidate mark a V-5 FIELD or a
reason-code suffix on the outcome? **A field — and the existing suffix stays.**

`plurality_suppressed` remains a POOL-level FACT and its DEFINITION does not
change. Its **consequence** does: before RS-19 it implied every bind at that
office was refused; after it, it implies nothing about any particular outcome.
A field whose consequence silently becomes conditional is CT-12's shape — an
existing query keeps parsing and quietly answers a different question.

A reason suffix alone is **one-sided**: it appears only on refusals. The new and
previously-impossible combination is `plurality_suppressed=true` **with**
`outcome=matched`, and under a suffix-only design nothing distinguishes
"scoping fired correctly" from "the lever silently stopped firing".

**rev 5, verbatim — the V-5 row:**

> | `plurality_suppressed` | bool | `rows_before_dedupe > candidates_considered` |

**rev 6, verbatim — that row plus one:**

> | `plurality_suppressed` | bool | `rows_before_dedupe > candidates_considered` — a POOL-level FACT. **Definition UNCHANGED at rev 6; its CONSEQUENCE is now conditional** (RS-19): it no longer predicts any particular outcome, so it must be read beside `winner_is_collider` |
> | `winner_is_collider` | bool\|null | **NEW at rev 6 (RS-19).** Did the BOUND-OR-REFUSED winner carry a phone key the fetch saw twice? `null` when there is no bind or no provenance. **Two-sided by construction** — emitted on binds AND refusals, so `plurality_suppressed=true` with `outcome=matched` is readable as "scoping fired" rather than "the lever stopped firing". A BOOLEAN: never the key, never a phone, never a hash (C-9) |

V-6 gains the same field on T-02's own precedent — the dedupe pair was ruled
onto the line AND the row together, and that pairing is what keeps CT-8's
row-vs-log two-sided check able to compare them. **Recorded alternative:** V-5
only, leaving the row plane to infer. Rejected for CT-8; a reader could
reasonably have chosen it.

**V-4 is UNTOUCHED — the metric labels stay at exactly two.** The new field
rides the LOG and ROW planes only, so there is no cardinality cost and SVR-10's
ceiling is not approached. `_tiered`'s existing two-cause `reason` split
(`plurality_refused_*` vs the below-bar reason) is likewise untouched and still
names the CAUSE on the refusal side.

#### Clause 5 — §8 C-X and §9 CT-12 / CT-4

**C-X, rev 5 verbatim:**

> - **C-X (no silent plurality).** No bind may be recorded without
>   `rows_before_dedupe` and `plurality_suppressed` (T-02) and without both
>   `lead_id` and `bound_phone_hash` (T-01). The *disposition* of a
>   plurality-suppressed or arity-ambiguous bind is G-4's; its **visibility** is
>   not negotiable.

**rev 6** adds `winner_is_collider` to the required triple and states two
reasons in the clause itself: that a bind at a suppressed pool was IMPOSSIBLE
before RS-19 and is the COMMON case after it, so the pool flag alone
under-specifies exactly the new case; and that `collided_keys` is an in-process
join key that never crosses a serialization boundary (C-9, C-9b).

**CT-12** gains a **second face and a two-sided tell**: the scoping can fail by
not firing (regression to the office-wide refusal) or by firing too widely (a
collider binding). Tells: `plurality_suppressed=true` with every outcome at an
office `below_bar`; or `winner_is_collider=true` with `outcome ∈ {matched,
matched_weak}`. The row also now names **TA-1** — a suite arming a non-ratified
limb cannot see this trap at all (Clause 6).

**CT-4** gains one sentence discharging N2-4's second correction: the per-shape
row states **BAR-reachability, not OUTCOME-reachability**. `below_bar` is
reachable for FULL_NAME and for exact-FNLI HIGH by the plurality route, and at
rev 6 that route fires only when the winner is itself a collider. A reader
taking the `N/A` row as "this shape can never take this outcome" is wrong.
**The rev-5 text of the row is otherwise byte-identical**, and the rev-5 §R
quotation of the original CT-4 row is untouched.

#### Clause 6 — TA-1, the ratified-arming rule (named, and why rev 6 carries it)

> **TA-1.** Every autouse arming fixture that arms a G-4 lever MUST arm the
> **RATIFIED** value. A test needing a different limb arms it **LOCALLY** and
> names which limb and why. A global fixture arming a non-ratified limb makes
> the shipped behaviour invisible to the entire suite by construction.

RECEIPT ITER-4 §I4.4.1 found `conftest.S05_TEST_THRESHOLDS` arming
`PLURALITY_SUPPRESSED_DISPOSITION` at **`bind_as_scored`** — the most permissive
limb, not the ratified `refuse`. **This is the class PT04-C9 closed one lever
over** (windows), re-created at the disposition lever, and it is why a fully
green suite could not see the office-wide effect. Mechanical guard:
`test_the_arming_fixture_arms_the_ratified_value` asserts fixture-equals-module
for every armed lever, with an explicit allowlist of deliberate divergences,
two-sided (an un-listed divergence fails; an allowlist entry that no longer
diverges also fails, so the list cannot rot into decoration).

**Sequencing, and it is load-bearing: SCOPE FIRST, THEN FLIP THE ARMING.**
Flipping the fixture to `refuse` while the disposition is still office-wide
would cascade across the suite. Under the scoped form the flip is near-neutral —
only constructions with an actual collided winner change. The arming fix is
safely takeable *because* RS-19 scopes the lever; the other order produces a red
wall that says nothing about the ruling.

#### Clause 7 — §13, the S-04 row

The S-04 row's `rows_before_dedupe` carriage clause gains **`collided_keys`**
and its coherence legs. **Every other row of §13 — S-02, S-05, S-06, S-07,
S-08, S-09, S-11 — is byte-identical.** S-05's row already binds *"§3 in full
(V-1…V-8)"* and CT-12, so it inherits rev 6 without a text change; S-08's row
already binds *"§7 in full … V-6 schema · V-5 fields"*, so the new field arrives
through the existing binder and needs no new obligation beyond tolerating it.

#### Clause 8 — residue **R-6a**, and residue **R-4a** re-routed again

**R-6a (new, registered here).** Collision identity is fetch-level, so a
survivor whose twin lies outside the narrowed window is still refused.
Window-aware detection would require re-running the dedupe per narrowed view — a
departure from the fetch-level design T-02's denominator argument rests on.
**Owner:** the loosening sitting, or the successor that re-keys the dedupe on
`(phone, lead_id)` so distinct leads both survive and the AMBIGUOUS branch
executes naturally (the stronger fix, which subsumes R-6a). **Refused now**
because it is a **silent pool change (C-2)**, it moves `pool_size` /
`candidates_considered`, and **every collision and recall cell was measured on a
phone-deduped corpus** — it is a re-pricing, not a re-scoping. **Trigger:** a
measured false refusal at a narrowed window.

**R-4a (carried).** rev 6 carries **no V-1 charge**, so R-4a's trigger (*"any
rev-5+ with a V-1 charge, or a certifier finding on the §0/V-1 wording delta"*)
again does not fire. Owner and trigger unchanged. One note for its owner: rev 6
makes the `matched_weak` population LARGER than rev 5 implied at suppressed
offices — the binds RS-19 restores are mostly weak ones — which moves the
residue's blast radius back up, without touching its substance.

#### What rev 6 did NOT touch

§0 · **V-1 · V-2 · V-3 · V-4 · V-7 · V-8 (all seven items)** — and specifically
**V-8.4's chain `candidates_gated <= candidates_in_effective_window <=
candidates_considered <= rows_before_dedupe` is UNTOUCHED**: `collided_keys`
adds no count and moves no count, it is a set of keys and not a cardinality in
the chain, so the rev-3 correction stands exactly as written. **V-8.1** holds
via `_tiered`'s existing NONE→`BELOW_BAR` construction without a text change;
8.2, 8.3, 8.5, 8.6, 8.7 untouched. §1 · §2 (SVR-1..SVR-18) · §4 apart from
T-02's appended paragraph and its routed paragraph · §5 · §6 · §7 · §8 apart
from C-X · §9 apart from CT-4 and CT-12 (the other thirteen rows byte-identical)
· §11 · §12. In §10 exactly **one** row changed; in §13 exactly **one** clause
of one row. `binds`, `consumes`, `resolves`, `flags_not_resolves`,
`build_target_hash`, `reads_taken_at` and `self_attestation_cap` are unchanged.
`status` remains **FROZEN**. The rev-5, rev-4 and rev-3 sections of this log are
unaltered, including rev 5's verbatim quotation of the original CT-4 row.

**Evidence grade: `[STRUCTURAL | MODERATE]`.** Self-ref ceiling per
`self-ref-evidence-grade-rule`: the architect seat authored both the seam ruling
and this amendment to its own frozen contract. The defect itself is **not**
self-attested — it was constructed at the real stage by the rite-disjoint qa
seat (VERDICT §12.9 N2-4) and the arming gap by the build seat (ITER-4
§I4.4.1); this seat's contribution is the scope, not the finding. Mechanism
reads own-hands at `f5c40dd2`. **No claim here is corroborated by a rite-disjoint
seat on the RULING itself, and none addresses one (H-7 unchanged).**

---

### rev 5 — 2026-09-04 — **MECHANISM** (blank (2)'s forgiveness bar becomes SHAPE-KEYED)

**Authority.** `.sos/wip/SEAM-RULING-forgiveness-bar-per-shape-2026-09-04.md` —
the architect seam ruling that discharges the escalation the build seat raised at
`.sos/wip/RECEIPT-matcher-recalibration-s09b-2026-09-04.md` **I2.8** (*"RS-17
cannot be executed as a constant SET"*, three-way word requested; limb 3 was
*"something else — but not a value of this constant"*, and this is it). Operator
words consumed: **RS-17** (`RATIFICATION-matcher-recalibration-sitting-2026-09-04.md`
§6), **RS-5** (§2), **RS-9 as amended by RS-17**, **RS-10** (recency NOT SET),
**R-25** (loosening bound behind the gate's tier predicate).

**Nature — the rev-3/rev-4 test, answered honestly and in the other direction.**
The standing test is *"would any bound sprint (S-04/S-05/S-06/S-08) have built
differently under the corrected text?"* — **YES.** This is a **MECHANISM**
revision, the first on this contract. It changes the **ARITY** of one lever and
nothing else:

| | |
|---|---|
| **What changes** | `WEAK_FORGIVENESS_MIN_SCORE` ceases to be a single scalar shared across shapes and becomes a **map keyed by shape**, in the form §4's `SHAPE_WINDOW_DAYS` already established for the window axis |
| **Which sprint's code moves** | **S-05 (W-TIER + W-RECENCY) — the only one.** S-05 owns `classify_tier`, the tier thresholds and the guard legs over them |
| **S-04 (W-ROUTE)** | **UNAFFECTED.** `SHAPE_WINDOW_DAYS`, `narrowed()`, the routing gate, the undated rule and `rows_before_dedupe` carriage are untouched. §4 is **cited as precedent, not amended** |
| **S-06 (W-FLAG limb a)** | **UNAFFECTED.** The listener scans on `tier = "weak"`; a population leaving that set changes its VOLUME, not its predicate |
| **S-08 (W-COUNT)** | **UNAFFECTED.** The four classes are a TIER axis crossed with an OUTCOME axis (R-M7); both axes are unchanged. Population moves BETWEEN existing classes, and no class is added or removed |
| **Still true of §1** | **No threshold VALUE is chosen in this document.** rev 5 rules the bar's SHAPE; the numbers remain S-09's, off G-4's words |

**Quotation convention.** rev 4's convention is inherited verbatim and is not
restated: block quotes of this contract's own prose are byte-exact including line
breaks; inline quotations of OTHER artifacts are set in `code spans`, verbatim in
wording and punctuation, normalised only in emphasis markup; elisions marked
`[...]`.

**Provenance of rev 5's own reads — stated because it differs from the body's.**
The frontmatter's `reads_taken_at: origin/main` and `build_target_hash` are
**UNCHANGED** and still describe the contract body. rev 5's *new* mechanism reads
were taken **own-hands at `e90650b49fb3bda54ad890dbe019bc2cbc5f27fa`** via
`git show` in the `autom8y` repo — no checkout switch, no worktree. The two
provenances are different and are not merged.

#### Clause 1 — the mechanism, and why the scalar could not carry it

**The build seat's finding is ACCEPTED and is correctly scoped.** ITER-2 swept
thirteen candidate values — STRUCK, 2.0, 2.001, 2.5, 3.0, 4.0, 4.001, 4.5, 5.0,
6.0, 7.0, 8.0, 8.5 — and returned `BARS SATISFYING BOTH RULINGS: NONE`. The
cause is a **score collision**: lone prefix-first FNLI scores **4.0** and lone
INITIALS scores **4.0**, and `classify_tier` tests `scored.score <
WEAK_FORGIVENESS_MIN_SCORE` **before** it dispatches on shape, so a scalar bar is
shape-agnostic by construction and cannot send one 4.0 to `below_bar` and the
other to `matched_weak`. RS-17 requires `bar > 4.0`; RS-5's INITIALS limb
requires `bar <= 2.0`; the interval is empty. **That conclusion is true of every
SHAPE-AGNOSTIC bar and is false per shape**, which is the whole of this revision.

**Per shape the interval is a clean gap, and it is coextensive with the predicate
`origin/main` actually uses.** Derived from the head's own enumeration
(`achievable_base_scores()`, `first_name_last_initial` = `{2.0, 4.0, 6.0, 8.0}`):

| FNLI base score | composition | `first_name_exact` | `origin/main` | FNLI bar 5.0 |
|---|---|---|---|---|
| 2.0 | prefix first (2.0) + hyphenated-surname gate branch (0.0) | False | PARK | park |
| 4.0 | prefix first (2.0) + surname initial (2.0) | False | PARK | park |
| 6.0 | first exact (6.0) + hyphenated-surname branch (0.0) | True | bind | bind HIGH |
| 8.0 | first exact (6.0) + surname initial (2.0) | True | bind | bind HIGH |

`first_name_exact` is set **iff** `FULL_FIRST_NAME_EXACT_BONUS` (6.0) is awarded
— `name_evidence.py:1217-1219` at `e90650b4`, the partition receipt. So on FNLI
the score partition `{2.0, 4.0}` / `{6.0, 8.0}` **is** `¬first_name_exact` /
`first_name_exact`: the score expresses `§6a`'s boolean predicate exactly, once
the bar stops being shared with a shape whose 4.0 means something else.

**And the value is comparand-invariant.** `scored.score` carries
`RECENCY_MAX_BONUS = 0.5`, so the ¬-exact band tops out at **4.5** and the exact
band opens at **6.0**; `5.0 ∈ (4.5, 6.0]` separates under PT-04 D-5's (α)
recency-inclusive comparand **and** under (β) base-score. RS-9's α/β deferral
therefore stays genuinely moot for event one — as RS-17 asserted — for a reason
stronger than RS-10's zero bonus. **The comparand fork is NOT decided here** and
remains the loosening sitting's.

**The keys, and the STRIKE form of each:**

| key | value | form | word |
|---|---|---|---|
| `FIRST_NAME_LAST_INITIAL` | **5.0** | a SET value, **DERIVED** by RS-17's own rule (lowest enumeration value strictly above the parked score 4.0; neighbours 4.0 / 6.0) | **RS-17** |
| `INITIALS` | **STRUCK** | the EXISTING `WEAK_FORGIVENESS_STRUCK` marker, re-scoped to this key — no new marker is minted | **RS-5** (INITIALS limb) + RS-9's strike |
| `FULL_NAME` | **ABSENT from the map** | absence, pinned by a derived two-sided keyset guard | **PT-02 §D blank (1)** (FULL_NAME slot = N/A with reason) + **R-M2** |

`FULL_NAME` is absent because `achievable_base_scores()` carries **no
`full_name` key**: the shape has no score axis, so a bar there is not *struck*,
it is **unpriceable**. This is the mechanical form of blank (1)'s ruling that a
number in that slot *"commissions an unauthorized non-exact mechanism"*.

**RS-17 is satisfied as written, and R-M3 is not reversed.** RS-17's operative
clause is *"FNLI lone prefix-first PARKS in event one, as today"*; *"the constant
is SET (not struck)"* is its derivation rule, and the constant IS set — on the
FNLI key. RS-17 supplies the sequencing itself: *"R-M3's bind is realised at the
loosening sitting, not before (R-25)."* **Deferral, not reversal.** Corroborating
and cutting the same way: blank (2)'s STRUCK form as OFFERED reads
`STRUCK: clears_evidence_floor stands as shipped and R-M3's bar is not set in this wave`
(PT-02 §I) — *stands as shipped*, i.e. the shipped park preserved. RS-17 is the
operator restating blank (2)'s own STRUCK semantics on the corrected premise.

**What this revision does NOT assert.** It does not describe, prescribe or
attest any code at any head. The per-shape keys, guards and reachability
predicates are S-05's to build under the seam ruling's §5 charge; this contract
asserts only the seam: **the bar has one key per shape carrying a score axis, and
its reachability is stated per key.**

#### Clause 2 — V-3, before and after

**rev 4, verbatim — Direction A:**

> - **Direction A (park → bind).** A lone prefix-first FNLI candidate today PARKS
>   via `clears_evidence_floor` → `WEAK_EVIDENCE` →
>   `TerminalDecline("name_evidence_weak", OPS)` (`name_evidence.py:328-329`,
>   `:588-598`; `match_lead.py:132-155`). R-M3 makes it BIND.

**rev 5, verbatim:**

> - **Direction A (park → bind) — SEQUENCED AT rev 5; DOES NOT LAND IN EVENT ONE.**
>   A lone prefix-first FNLI candidate today PARKS via `clears_evidence_floor` →
>   `WEAK_EVIDENCE` → `TerminalDecline("name_evidence_weak", OPS)`
>   (`name_evidence.py:328-329`, `:588-598`; `match_lead.py:132-155`). R-M3 makes
>   it BIND — **and that bind is realised at the LOOSENING SITTING, not in event
>   one** (RS-17 amending RS-9; R-25). Event one REPRODUCES today's park through
>   the FNLI key of the per-shape forgiveness bar, so Direction A is **DEFERRED,
>   never REVERSED**: R-M3 stands ratified and its BIND limb is scheduled. The
>   two-directional delta therefore lands **ONE-DIRECTIONAL in event one —
>   Direction B only**. Mechanism, receipts and the per-shape keys: **§R rev 5
>   Clause 1**.

**Direction B is BYTE-IDENTICAL.** RS-5's INITIALS limb ships exactly as ratified
(silent-high → tagged-weak), and the trace's fourteen-construction replay
confirmed it (constructions B, F, G: bind today, bind `matched_weak` at the head).

**rev 4, verbatim — two migration-table rows:**

> | TerminalDecline class | `name_evidence_weak` | **retired**; `name_evidence_below_bar` begins |
> | CloudWatch dimension `class` | `name_evidence_weak` populated | goes flat at the landing instant |

**rev 5, verbatim:**

> | TerminalDecline class | `name_evidence_weak` | **retired**; `name_evidence_below_bar` begins — and at rev 5 it begins **NON-MUTE**: the FNLI bar routes exactly the population `name_evidence_weak` serves today, so the successor is a **1:1 handover**, not a born-silent class |
> | CloudWatch dimension `class` | `name_evidence_weak` populated | goes flat at the landing instant, **with `class=name_evidence_below_bar` picking up in the same instant** (rev 5; under the rev-4 shape-agnostic strike BOTH read flat) |

The other two rows (enum value, metric label value) are **byte-identical**, as is
the migration rule, the denominator-integrity paragraph and the `below_bar`
naming note. The landing-day paragraph gains an appended rev-5 block stating the
handover **and its honest scale** (1 in 12,660 replayed cells, VERDICT §3.3) —
recorded because a correct-and-near-silent successor is exactly what a reader
mistakes for a dead one.

#### Clause 3 — §9 CT-4 and CT-10, before and after

**rev 4, verbatim:**

> | CT-4 | **Born-mute `below_bar` trap.** G-4 sets the bar so nothing can fall under it. | `below_bar == 0` with `matched_weak > 0` and no bar-adjacent W-CAL cell | S-09 states the bar's *reachability* alongside its value; UNREACHABLE is not 0. | — |

> | CT-10 | **Dimension-goes-flat trap.** `class=name_evidence_weak` flatlines at landing and reads as an outage. | — | S-11's landing note names retirement, instant, successor (V-3). | — |

**rev 5, verbatim:**

> | CT-4 | **Born-mute `below_bar` trap.** G-4 sets the bar so nothing can fall under it. **At rev 5 the bar is PER SHAPE, so the trap is per shape too**: one shape's declared-unreachable bar must not be read as the outcome being mute. | `below_bar == 0` with `matched_weak > 0` and no bar-adjacent W-CAL cell — **and, at rev 5, read PER SHAPE**: for a shape whose bar is STRUCK the tell is a NON-SIGNAL by declaration, not evidence of a born-mute bar | S-09 states the bar's *reachability* alongside its value **for EVERY key, plus the aggregate**; UNREACHABLE is not 0, and a shape with no score axis is a THIRD state (N/A) that is neither. | — |

> | CT-10 | **Dimension-goes-flat trap.** `class=name_evidence_weak` flatlines at landing and reads as an outage. **Rev-5 addition — the second half of the same trap:** a retirement whose named successor ALSO never fires is indistinguishable from a broken instrument, which is the state the rev-4 shape-agnostic strike would have shipped. | both `name_evidence_weak` and `name_evidence_below_bar` reading zero after the landing instant | S-11's landing note names retirement, instant, successor (V-3) **and asserts the successor is REACHABLE for at least one shape** — mechanically, via the per-shape reachability statement CT-4 now requires. | — |

CT-10 gains a `tell` where it previously had none (`—`). That is deliberate:
the trap as written at rev 4 was one-sided — it caught the predecessor going
flat and had no tell for the successor never arriving. The rev-4 shape-agnostic
strike would have shipped exactly that second state, and it was the build seat's
ITER-2 that surfaced it (I2.5: *"Both correct; together they still look exactly
like a broken instrument"*). **The other thirteen CT rows are byte-identical.**

#### Clause 4 — §10, the F-P2 / F-P3 row, before and after

**rev 4, verbatim:**

> | **F-P2 / F-P3** — the acceptable mis-attribution / collision rate; the thin-evidence forgiveness bar | G-4 | The bar's *name* (`below_bar`) and its reachability tell (CT-4). No value. **Plus a correction to the evidence the word will be read off: CT-12 biases measured collision rates LOW.** |

**rev 5, verbatim:**

> | **F-P2 / F-P3** — the acceptable mis-attribution / collision rate; the thin-evidence forgiveness bar | G-4 | The bar's *name* (`below_bar`), its reachability tell (CT-4), and — **new at rev 5** — its **ARITY**: the bar is **PER SHAPE**, one key per shape that has a score axis, as PT-02 §I blank (2)'s own title (*"**FNLI** thin-evidence forgiveness bar (R-M3)"*) has read since 2026-09-03. **Still no value.** **Plus a correction to the evidence the word will be read off: CT-12 biases measured collision rates LOW.** |

**§10 remains the operator's table and rev 5 answers nothing in it.** The gate
(G-4) is unchanged, the question is unchanged, and no value is supplied. What is
added is the shape of the answer the gate may receive — which was already the
shape blank (2) asked in, and which the scalar implementation had narrowed.
**Every other §10 row — F-P1, F-P4, both `new` policy rows, F-A1, F-A2, F-M6 —
is byte-identical.**

#### Clause 5 — §13, the S-09 row, before and after

**rev 4, verbatim (opening clause of the row):**

> | **S-09** (assembly) | Sets every VALUE this contract only NAMED: `SHAPE_WINDOW_DAYS`, the forgiveness bar, the recency thresholds,

**rev 5, verbatim:**

> | **S-09** (assembly) | Sets every VALUE this contract only NAMED: `SHAPE_WINDOW_DAYS`, the **per-shape forgiveness bar map** (one value per shape carrying a score axis; rev 5), the recency thresholds,

The remainder of the S-09 row and **every other row of §13 — S-02, S-04, S-05,
S-06, S-07, S-08, S-11 — is byte-identical.** S-05's row already binds *"§3 in
full (V-1…V-8)"* and *"CT-4"*, so it inherits this revision without a text
change; naming S-05 twice would imply two obligations where there is one.

#### Clause 6 — residue **R-4a**: RE-ROUTED, not discharged

R-4a (registered in rev 4 Clause 4) records that **V-1's `matched_weak`
disposition cell still reads `bind + tag + count + reversible`** while §0 now
reads *"flagged when wrong; restated with provenance once the record-correction
primitive lands"*. Its stated trigger is *"any rev-5+ with a V-1 charge, or a
certifier finding on the §0/V-1 wording delta."*

**rev 5 carries NO V-1 charge**, so the trigger does not fire and the residue is
**carried forward unchanged**. Stated explicitly because rev 5 is the first
rev-5+ and a reader could reasonably expect the trigger to have fired here: it
did not, because this revision's charge is blank (2)'s ARITY, and touching V-1's
disposition cell would falsify `revision_5_nature`'s *"S-04/S-06/S-08
unaffected"* — V-1 is the CLOSED vocabulary all four sprints bind to
byte-for-byte. **Owner and trigger are unchanged**: the next revision carrying a
V-1 charge, or the S-10 certifier, whichever reaches it first.

**One rev-5 note the residue's owner will want.** rev 5 makes the `matched_weak`
population in event one **smaller than rev 4 implied** — the FNLI limb does not
join it — which changes the residue's blast radius, not its substance. The
mechanical dispositions (bind, tag, count) are still unchanged and are still what
the sprints build; the fourth word is still a promise, and it still lives at §0.

#### What rev 5 did NOT touch

§0 (both paragraphs, including the RS-12 predicate as landed at rev 4) ·
**V-1 · V-2 · V-4 · V-5 · V-6 · V-7 · V-8 (all seven items, including 8.4 as
corrected at rev 3 and 8.6's `AMBIGUITY_EPSILON > RECENCY_MAX_BONUS` replacement
pin — RS-10 leaves recency STRUCK and this revision touches no recency lever)** ·
§1 · §2 (SVR-1..SVR-18) · **§4 in full** (F-M2's option slate, the `narrowed()`
mechanism, `SHAPE_WINDOW_DAYS`, T-02, the undated sub-fork — cited as precedent,
amended nowhere) · §5 · §6 · §7 · **§8 (every clause: C-9, C-9a, C-9b, C-I, C-T,
C-S, C-P, C-D, C-A, C-V, C-R, C-L, C-X — C-V holds, no ninth outcome / fourth
tier / third metric label; C-R holds and is IMPROVED, the retirement gains a live
successor)** · §11 · §12. In V-3 exactly **three** places changed (Direction A,
two migration-table rows, and an appended landing-day block); in §9 exactly
**two** rows; in §10 exactly **one** row; in §13 exactly **one** clause of one row.
`binds`, `consumes`, `resolves`, `flags_not_resolves`, `build_target_hash`,
`reads_taken_at` and `self_attestation_cap` are unchanged. `status` remains
**FROZEN**. The rev-4 and rev-3 sections of this log are unaltered.

**Evidence grade: `[STRUCTURAL | MODERATE]`.** Self-ref ceiling per
`self-ref-evidence-grade-rule`: the architect seat authored both the seam ruling
and this amendment to its own frozen contract. Mechanism claims in Clause 1 are
derived own-hands at `e90650b4`; the operator words and the ITER-2 receipt are
read at their paths. **No claim in this revision is corroborated by a
rite-disjoint seat, and none addresses one (H-7 unchanged).**

---

### rev 4 — 2026-09-04 — TEXT-ONLY (RS-12 sentence · C14 conformance note · the dissolutions)

**Authority.** `.ledge/decisions/RATIFICATION-matcher-recalibration-sitting-2026-09-04.md`
— **RS-12** (`:55-57`), the derived paragraph (`:64-66`), and teed act **#2**
(`:89`), whose row reads verbatim:
`| 2 | CONTRACT rev 4 (text-only): RS-12 sentence in §0; note read_failed emission fix | architect | before S-10 |`.

**Nature — the question rev 3 was required to answer, answered again.**
**TEXT-ONLY. NOT A SEAM CHANGE.** The test is unchanged: *"would any bound
sprint (S-04/S-05/S-06/S-08) have built differently under the corrected text?"*
— **NO**, on three grounds:

1. **§0 is a realization predicate, not a mechanism clause.** No sprint reads it
   to decide a field, a value or a limb; every sprint carries it verbatim into
   its exit criteria and its PR body (§0's own second paragraph). RS-12 changes
   what the sentence PROMISES, not what any sprint BUILDS.
2. **V-5's text is UNCHANGED** (Clause 2). The `read_failed` conformance gap is
   closed CODE-side at S-09 limb (b) — the contract is not weakened to meet the
   head.
3. **The dissolutions remove CONDITIONAL items that were never built** (Clause
   3). D-12/D-13 were conditional on `G-3 = park`, which did not occur; G-5's
   question already dissolved at Residence C (§5.3); blank (2) is a VALUE this
   contract never carried (§1: *"No threshold VALUE is chosen here"*).

No mechanism, no threshold value, no seam limb, no binder in §13, and **no
clause of V-1..V-8** changes.

**Quotation convention in this section.** Block quotes of this contract's own
prose are byte-exact including line breaks. Inline quotations of OTHER artifacts
are set in `code spans`, are verbatim in wording and punctuation, and are
normalised only in emphasis markup (`**bold**` / `*italic*` dropped) so a
markdown quote cannot silently re-emphasise its source; any elision is marked
`[...]`.

#### Clause 1 — §0, the realization predicate (RS-12)

**rev 3, verbatim — the sentence the operator replaced:**

> **Every ad-driven booking that arrives with minimal patient info is attributed
> to its originating lead — tiered by evidence, reversible when wrong, and never
> silently dropped. Verified-realized = the change is adversarially certified by
> a rite-disjoint critic AND at least one organic minimal-info booking has been
> attributed by the new tiers and spot-confirmed correct — NOT PRs merged, NOT
> self-attested green.**

**rev 4, verbatim:**

> **Every ad-driven booking that arrives with minimal patient info is attributed
> to its originating lead — tiered by evidence, flagged when wrong; restated
> with provenance once the record-correction primitive lands, and never
> silently dropped. Verified-realized = the change is adversarially certified by
> a rite-disjoint critic AND at least one organic minimal-info booking has been
> attributed by the new tiers and spot-confirmed correct — NOT PRs merged, NOT
> self-attested green.**

**The substitution is exactly the ratified one, and it is a SUBSTRING swap.**
RS-12 (`:55-57`) reads, verbatim but for its bold markup:
`"reversible when wrong" becomes "flagged when wrong; restated with provenance once the record-correction primitive lands"`.
**Only those three words are replaced.** Every other word — including the heading's **CARRIED
VERBATIM** — is byte-identical; the two line-wraps that move do so because the
replacement is longer, not because any word changed. **The swap is deliberately
mechanical** so the RULING §8 errata, the TELOS (`:23`, `:46`, `:54-55`) and the
four PR bodies can perform the IDENTICAL substring replacement and still
byte-match this contract. A re-punctuated or re-flowed predicate would silently
fork the verbatim-carry discipline §0's second paragraph binds every sprint to —
which is the one discipline a predicate labelled CARRIED VERBATIM cannot afford
to lose while being edited.

**Why the sentence changed — the premise, not the wording.** The external effect
of a mis-attribution is **irreversible by construction**; what is correctable is
OUR RECORD on the terminal planes, and the ONE primitive that corrects it is
**R3 restate-with-provenance, never delete** — commissioned on the **dre lane**,
registered as **DF-5**, and **not built by this wave**
(`RATIFICATION-shared-front-sitting-2026-09-03.md` §2 **R-23**, per the 09-04
ratification's `governed_by` field `:9`; corroborated in-repo at
`.sos/wip/HANDOFF-10x-dev-wave2-close-activation-loop-2026-09-01.md:1335` —
verbatim but for its bold markup, `ONE primitive = R3
restate-with-provenance, never delete; no "undo" artifact. Built by the DRE
LANE, not ours. Register = DF-5.` — and at
`.sos/wip/CARD-dead-letter-disposition-2026-09-04.md:39`). "Reversible"
therefore asserted a capability that **does not exist at this landing and has no
owner on this train**. R-25 permits the tier to ship before the reversal act
exists; RS-12 is the price of that permission — the promise is downgraded to
what the wave actually delivers (a flag), plus a dated, owned second phase (R3's
restatement).

`[UV-P: RATIFICATION-shared-front-sitting-2026-09-03.md exists as a landed artifact under the name the 09-04 ratification's governed_by field uses | METHOD: deferred-to-dispatcher-cross-repo-locate | REASON: the file does not resolve in this session repo or in autom8y (find over both trees plus git log --all --name-only, zero hits at 2026-09-04). R-23's CONTENT is corroborated by the two resolvable in-repo anchors cited above, so this clause's reasoning does not rest on the unresolved pointer — only the pointer's own resolvability is deferred.]`

**Two things RS-12 does NOT do, stated so a certifier does not infer them:**

1. **It does not make the weak bind correct.** `matched_weak` still binds; a
   wrong weak bind still reaches the clinic-visible surface (F-P1, §10). RS-12
   changes the REMEDY the predicate promises, not the exposure it creates.
2. **It does not create, name or schedule the flag's write-back.** FLAG-5's
   write-back default remains deferred (ratification §4). The flag is
   **emit-only** on this train — the same fact that dissolves G-5 (Clause 3).

#### Clause 2 — V-5's conformance at `6c44cec7`: the TEXT is UNCHANGED, the HEAD moves

**V-5, verbatim — UNCHANGED at rev 4, quoted to fix what rev 4 did not touch:**

> **MINT one INFO event, `name_evidence_outcome`, emitted on EVERY outcome
> including `read_failed`.**

**Receipt — own-hands, this seat, at `6c44cec7cd07b9b9c7871b61bee54159e1de4310`**
(repo `/Users/tomtenuta/Code/a8/a8/repos/autom8y`, branch
`integration/matcher-recalibration`, via `git show 6c44cec7:<path>`):
`_emit_outcome` (`pipeline/stages/match_lead.py:248`, publishing `OUTCOME_EVENT`
at `:280`) has a **single** call site, inside `_terminate` (`:452`). The
`read_failed` path never reaches it: it runs through `_count_tier_declined`
(`:117-156`), called at `:817` and `:947`, which increments the prometheus
`read_failed` label and logs the **retained ops line**
`name_evidence_read_failed` — and returns. No V-5 line, no V-6 row.
**The countable line is emitted on SEVEN of V-1's eight outcomes, not eight.**

Cross-anchors, both dispatcher-appended 2026-09-04T17:35Z from the peer
change-warden's Arm A cert, both leaving the authoring seats' text unedited:
the **qa VERDICT ERRATUM**
(`.sos/wip/qa/VERDICT-matcher-recalibration-s09a-capped-pass-2026-09-03.md:554-555`)
and the **PT-04 ERRATUM**
(`.sos/wip/CHECKPOINT-matcher-recalibration-PT-04-2026-09-03.md:358-359`) —
verbatim but for its bold markup, with one elision marked:
`is WRONG by one: it is emitted on SEVEN. [...] V-5's "including read_failed" is
therefore unmet at this head → S-09 limb (b) mandatory item PT04-C14.`

**DISPOSITION: the CONTRACT does not move; the HEAD does.** S-09 limb (b) is
landing **PT04-C14** concurrently (ratification §5 teed act 1). Three reasons
V-5 is not weakened to match the defect:

1. **A contract edited toward the head it exists to judge stops being
   authority.** Rev 3's test (PT-04 §F **B-3**) asks whether the CONTRACT
   contains a leg the head provably fails. At rev 2 the answer was yes *because
   the CONTRACT was wrong* (V-8.4's inverted leg) and the contract was
   corrected. Here the answer is yes *and the contract is right*: the head fails
   V-5, and the cure is code. Closing this divergence from the prose end would
   make B-3 unanswerable forever — every divergence can be closed from either
   end, and the prose end is always the cheaper one.
2. **The gap is exactly the denominator this contract exists to protect.** V-5
   is the countable layer and V-8.3's I-3 false-green detector reads it. A
   `read_failed` that never emits the countable line is invisible to
   `stats count() by outcome` — an upstream outage silently SHRINKS the
   denominator instead of appearing in it. That is the `weak_evidence` / V-3
   denominator-integrity fault wearing a different costume, and V-3 retired an
   enum value to prevent it.
3. **The cure is owned and dated.** PT04-C14 is a mandatory limb (b) item with a
   named seat; nothing about it is speculative at rev-4 authorship time.

**Conformance state, stated plainly for the S-10 certifier:** V-5 is **UNMET at
`6c44cec7` on the `read_failed` limb**, deliberately, and **conformance is
restored at limb (b)'s head**. A certifier reading rev 4 against `6c44cec7`
*should* find this divergence — it is named here so the finding is a
**confirmation, not a discovery**. B-3's answer for rev 4 is therefore: *yes,
with the cure dispatched, dated and pointed at.*

#### Clause 3 — the dissolutions, recorded (one line each)

Per the ratification's derived paragraph (`:64-66`) — *"Derived, recorded not
asked"*:

1. **G-3 = `propagate` (R-24).** The laundering hazard closes **at the gate, not
   at the matcher**; the seam is set to `propagate` at limb (b). This contract
   never held a G-3 value (§1), so nothing here changes but the record: the gate
   is **SPOKEN**, and §10's F-P1 row now carries that fact.
2. **D-12 DISSOLVES** (PT04-C4). It was conditional on `G-3 = park` — a policy
   park sharing the `name_evidence_below_bar` decline class. No park, no new
   decline class, no `TerminalDecline` dimension; **V-1 stays CLOSED at eight
   with nothing pressing on it.**
3. **D-13 DISSOLVES** (PT04-C5; **DF-30 closes with it**). A bound-then-parked
   row cannot arise under `propagate`. `.sos/wip/RULING-PRERENDER-d13-bound-then-parked-2026-09-03.md`
   is **VOID by its own `voids_on` clause** (*"WEAK_BIND_RESOLVED_PHONE_PROPAGATION
   in {'propagate', 'gate_the_phone'}"*) and has been marked so by **one appended
   status line**; nothing else in that artifact is altered. **V-6 is untouched by
   rev 4** — which was the point of pre-rendering: the one artifact that could
   have changed a frozen schema's *meaning without changing its fields* expired
   unused. *(Filename note: the rev-4 charge and PT-04's ERRATA both refer to
   this pre-render; the artifact on disk is dated `2026-09-03`.)*
4. **G-5 DISSOLVES.** The contradiction flag is **emit-only** on this train;
   record correction is R3 on the dre lane (Clause 1). §5's closing line —
   *"The contradiction FLAG write (W-FLAG limb (b)) is NOT ruled here — G-5 and
   S-07's packet own it"* — is **UNCHANGED** and now reads as history: there is
   no write class to rule because there is no record-mutating write. This also
   **answers DF-27 rather than merely carrying it**: PT-04 `:241` recorded the
   hazard as *"a reversal that changes no served number reverses nothing"* — but
   under RS-12 the flag was never the reversal (R3 is), so a clause forbidding
   the flag from touching a served number is **coherent, not self-defeating**.
5. **Blank (2) `WEAK_FORGIVENESS_MIN_SCORE` is STRUCK for event one** (RS-9),
   with the **comparand fork (α)/(β) DEFERRED to the loosening sitting** (D-5 /
   PT04-C3). **V-8.6's replacement pin is UNAFFECTED**: V-8.6 pins
   `AMBIGUITY_EPSILON > RECENCY_MAX_BONUS` and obliges S-05 to *replace it
   explicitly and pin the replacement* when R-M5 breaks it — a different pair of
   constants, on a different blank (blank (4), also struck this wave by RS-10),
   and an obligation about **how** a live invariant may be broken, not about
   which forgiveness value is typed. Striking blank (2) touches neither the
   invariant nor the pinning duty. **Also unaffected: CT-4** (`below_bar`'s
   reachability tell) and **NEW-2 / D-4c (PT04-C7)** — the float-leg validity
   guard remains a MANDATORY limb (b) item even though no value arrives at event
   one, because *the guard that must refuse a bad number has to exist before the
   number is asked for*. RS-9 postpones the number, not the guard.

#### Clause 4 — the five "reversible" occurrences: two edited, three deliberately not

`grep -n -i "reversib"` over rev 3 returns **five** hits. Two are edited; three
are not, and each refusal is named so a later reader does not read the silence
as oversight (`named-trap-discipline`).

| line (rev 3) | text | rev 4 |
|---|---|---|
| `:33` — §0 predicate | *"tiered by evidence, **reversible when wrong**, and never silently dropped"* | **EDITED** — Clause 1 (RS-12). |
| `:917` — §10 F-P1 | *"is a **reversible** wrong bind acceptable on a clinic-visible surface?"* | **EDITED** — below. |
| `:140` — **V-1**, `matched_weak` disposition cell | *"bind + tag + count + **reversible**"* | **NOT EDITED.** V-1..V-8 are outside rev 4's charge, and V-1 is the CLOSED vocabulary four sprints bind to byte-for-byte; editing a disposition cell would falsify `revision_4_nature`'s *"S-04/S-05/S-06/S-08 unaffected"*. **This is now the one surviving place this contract says "reversible" of the weak tier, and its referent is two-phase** (flagged now; restated at R3). Carried as residue **R-4a** below — routed, not buried. |
| `:578` — §5.1 | verbatim quotation of `RULING-decision-space-amendments-2026-08-26.md:73-76` — *"**reversible** business-ledger METADATA writes … never record content"* | **NOT EDITED.** A verbatim external quotation, used there to **refuse** the metadata limb; altering a quoted charter would break the refusal's own citation. It is also not said of the weak tier — it is said of a **write class**. |
| `:604` — §5.4 | *"the write is additive and **reversible** by deletion"* | **NOT EDITED.** A **mechanism clause** about the §5 DynamoDB `PutItem`, listed there among compensating controls that the same paragraph says are *"none of which is an authorization control"*. A row is deletable; that is orthogonal to whether a wrong ATTRIBUTION can be un-said to the clinic, which is what RS-12 governs. Editing it would be a mechanism edit, which rev 4 may not be. |

**Residue R-4a (registered here, not in §12 — rev 4 does not touch §12).** V-1's
`matched_weak` disposition cell still reads "reversible" while §0 now reads
"flagged … restated with provenance once the record-correction primitive lands".
**Owner:** the next revision carrying a V-clause charge, or the S-10 certifier,
whichever reaches it first. **Trigger:** any rev-5+ with a V-1 charge, or a
certifier finding on the §0/V-1 wording delta. **Not a defect in the seam** —
`matched_weak`'s three mechanical dispositions (bind, tag, count) are unchanged
and are what the sprints build; the fourth word is a promise, and the promise now
lives at §0.

**F-P1, before and after.**

rev 3, verbatim:

> | **F-P1** — is a reversible wrong bind acceptable on a clinic-visible surface? | G-3 | Nothing. The mechanism half is S-05's read (UV-P-2). This contract does not touch `ctx.resolved_phone`'s propagation. THREAT T-18 is S-05's input, not this seam's. |

rev 4, verbatim:

> | **F-P1** — is a wrong bind that is FLAGGED (not reversed) acceptable on a clinic-visible surface? | G-3 | Nothing. The mechanism half is S-05's read (UV-P-2). This contract does not touch `ctx.resolved_phone`'s propagation. THREAT T-18 is S-05's input, not this seam's. **Wording corrected at rev 4 (RS-12); the rev-3 text is in §R. G-3 was spoken 2026-09-04 = `propagate` (R-24) — the gate is closed; the product question this row names is not re-opened, answered or dissolved here.** |

The contribution column is unchanged. Two facts are appended: the RS-12 wording
correction, and that **G-3 has been spoken** — recorded because a certifier
reading an OPEN gate on a row whose gate has closed would mis-price the flag.
**§10 remains the operator's table; rev 4 answers nothing in it.**

#### What rev 4 did NOT touch

§0's second paragraph · **V-1 · V-2 · V-3 · V-4 · V-5 · V-6 · V-7 · V-8 (all
seven items, including 8.4 as corrected at rev 3, and 8.6)** · §1 · §2
(SVR-1..SVR-18) · §3's vocabulary · §4 · §5 · §6 · §7 · §8 · §9 · §11 · §12 ·
§13. In §10 exactly **one cell** changed (F-P1's question text + an appended
note, Clause 4); the rest of §10 — F-P2/F-P3, F-P4, both `new` policy rows,
F-A1, F-A2, F-M6 — is byte-identical. `binds`, `consumes`, `resolves`,
`flags_not_resolves`, `build_target_hash` and `reads_taken_at` are unchanged.
`status` remains **FROZEN**. The rev-3 section of this log is unaltered.

---

### rev 3 — 2026-09-03 — TEXT-ONLY (D-2b + NEW-1)

**Authority.** PT-04 §C rows D-2b and NEW-1, condition **PT04-C2 (BLOCKING)**,
discharging PT-04 §F **B-3** — *"Does the CONTRACT the certifier will read as
authority contain a leg the head provably fails?"* Answer at rev 2: **YES**.
Answer at rev 3: **no**.

**Nature — the question PT-04 required be answered before any edit.**
**TEXT-CONFORMANCE CORRECTION, NOT A SEAM CHANGE.** The test PT-04 set is
*"would any bound sprint (S-04/S-05/S-06/S-08) have built differently under the
corrected text?"* — **NO**, on three own-hands grounds at `6c44cec7`:

1. **The only mechanism that pins V-8.4 enforces the CORRECTED chain already.**
   `LeadCandidateSet.__post_init__` (`activation_read_client.py:319-347`) quotes
   rev-2's chain in its docstring and then enforces exactly two legs:
   `pool_size >= len(candidates)` (= `in_effective <= considered`) and
   `rows_before_dedupe >= pool_size` (= `considered <= rbd`). **Both are legs of
   the corrected chain. Neither is the false leg.** The type does not carry
   `candidates_gated` as a field at all, so the inverted leg was never buildable
   at that seam — S-04 could not have built it differently because S-04 could
   not have built it.
2. **Nothing rev 2 truly asserted is withdrawn.** rev-2's chain has three legs;
   leg 1 (`in_effective <= gated`) is false, leg 2 (`gated <= considered`) and
   leg 3 (`considered <= rbd`) are true. rev 3 keeps leg 3 verbatim and keeps
   leg 2 **as an assertion** by transitivity. The correction removes only the
   false leg and adds the true one it displaced. The rev-3 chain is strictly
   stronger than rev-2's-chain-minus-its-false-leg.
3. **The head's own test already asserts the corrected order, non-vacuously.**
   `tests/test_s05_attribution_witness.py:738-771`
   (`test_the_V8_4_chain_holds_on_the_true_values`) asserts
   `gated <= in_effective <= considered <= rbd` on the V-5 line **and** asserts
   the three counts genuinely differ, so the chain is not satisfied by every
   number being equal.

No mechanism, no threshold value, no seam limb, and no binder in §13 changes.

#### Clause 1 — V-8.4 (`§3 V-8`, item 4)

**rev 2, verbatim:**

> 4. `candidates_in_effective_window <= candidates_gated <= candidates_considered
>    <= rows_before_dedupe`.

**rev 3, verbatim:**

> 4. `candidates_gated <= candidates_in_effective_window <= candidates_considered
>    <= rows_before_dedupe`. The order is V-5's own field definitions read in
>    sequence: the comparator gates the **narrowed** set, so gating can only
>    REMOVE from `candidates_in_effective_window`; §4's narrowing can only REMOVE
>    from the 90-day pool; the dedupe can only REMOVE rows. `candidates_gated <=
>    candidates_considered` is unchanged **as an assertion** — at rev 3 it holds
>    by transitivity rather than as a written leg. **Corrected at rev 3 (D-2b);
>    the rev-2 text and the receipt are in §R.**

**Receipt — the head implements V-5 and provably fails the rev-2 prose.** All
reads at `6c44cec7cd07b9b9c7871b61bee54159e1de4310`, branch
`integration/matcher-recalibration`, repo
`/Users/tomtenuta/Code/a8/a8/repos/autom8y`, via `git show 6c44cec7:<path>`.

| V-5 field (frozen definition) | derivation at the head | SVR anchor |
|---|---|---|
| `candidates_considered` — *pool size at the 90-d ceiling* | `pool.pool_size` | `pipeline/stages/match_lead.py:285` (V-5 line); `:442` (V-6 row) |
| `candidates_gated` — *passed the comparator* | `result.candidates_gated`, computed over the **narrowed** set | `match_lead.py:286`; gate input `:352` `pool.narrowed(...)` → `:394` `match_name_evidence(evidence, candidate_set)` |
| `candidates_in_effective_window` — *after §4's narrowing* | `len(candidate_set.candidates)` | `match_lead.py:287-289` (line); `:443` (row) |
| `rows_before_dedupe` — *T-02* | `provenance.rows_before_dedupe` | `match_lead.py:290` (line); `:444` (row) |

Because the comparator is applied to `candidate_set` (`:394`) and never to
`pool`, `candidates_gated` is drawn from `candidates_in_effective_window` and can
only be `<=` it. The rev-2 first leg asserts the reverse.

**Falsification, on measured values.** qa VERDICT §11.4 `:510` and FIXRECEIPT §3:
true values `gated=1, in_effective=2, considered=4, rows_before_dedupe=6` on a
FNLI-45 request over a 90-d pool of 4 — V-5-ordered chain `1 <= 2 <= 4 <= 6`
**True**; literal rev-2 first leg `2 <= 1` **False**. VERDICT §11.4 records the
same falsification on its own fixture as `2 <= 3 <= 4 <= 6` True / `3 <= 2`
False. **Two independently-constructed fixtures, same verdict.**

**The head said so first, and declined to fix it.**
`name_evidence.py:1240-1248` (annotated at `76a933b9`, folded into `6c44cec7`):

> ★ THAT CHAIN IS QUOTED FROM CONTRACT V-8.4 VERBATIM AND ITS FIRST LEG IS
> INVERTED relative to V-5's own field definitions […] the true order is
> ``gated <= in_effective_window <= considered <= rows_before_dedupe`` and the
> literal text is unsatisfiable. This code implements V-5. The contract is
> FROZEN, so the prose is a PT-04 amendment item and is NOT edited here --
> recorded so the next reader does not "correct" the code toward the text.

Rev 3 discharges that amendment item. **The build seat's refusal to edit a frozen
contract, and its decision to annotate instead, was correct and is recorded as
such.**

#### Clause 2 — V-5, the retained-lines note (`§3 V-5`)

**rev 2, verbatim — UNCHANGED at rev 3, quoted to fix what rev 3 did not touch:**

> **The five existing per-outcome lines are RETAINED UNCHANGED** —
> `name_evidence_matched` (`:219`), `name_evidence_below_floor` (`:140`),
> `name_evidence_ambiguous` (`:115`), `name_evidence_organic` (`:175`),
> `name_evidence_read_failed` (`:476`). They are the human/ops layer; the new line
> is the countable layer. This is the S-4 FIX-1 F-A1 pattern applied a second time.

**rev 3 ADDS** the block beginning *"**NEW-1 — what "RETAINED UNCHANGED" costs,
stated rather than discovered**"* and ending *"…nothing on this train builds
it."* — reproduced in §3 V-5 above and not duplicated here. **No sentence of the
rev-2 paragraph is altered, reordered or deleted.**

**Disposition: (β) DOCUMENT. No code change. No S-09 limb (b) item created.**

**Option slate — PT-04 enumerated three; this seat adds three and rejects five**
(`option-enumeration-discipline` §4 Step 1, §5):

| # | option | mechanism | disposition |
|---|---|---|---|
| **α** | RENAME the field on the ops lines to `candidates_in_effective_window` | code, wire | **REFUSED.** Truthful, but it is a wire-visible rename on the layer whose whole purpose is to survive the change (reason 3 in V-5). It also only half-helps: the ops line gains a correct name and still carries no pool count. |
| **β** | DOCUMENT in the contract (+ S-11 runbook), change no code | text | **CHOSEN.** See the four reasons at V-5. |
| **γ** | change the ops lines' VALUE to the pool count | code, wire | **REFUSED outright.** A value change under an unchanged name is V-3's denominator-integrity breach and is the exact thing the clause forbids. |
| **δ** *(added)* | DROP `candidates_considered` from the two ops lines entirely | code, wire | **REFUSED.** The null-mechanism option, and it must be named: it removes the contested referent at a stroke. But it deletes a receipt an ops reader has today, to cure a hazard with no machine consumer, and "RETAINED UNCHANGED" forbids a deletion as much as a rename. |
| **ε** *(added)* | rename the field on the **V-5 line** instead (the symmetric option) | code, wire, **seam** | **REFUSED, and named so the asymmetry is shown to be principled.** `candidates_considered` on the countable plane is what `plurality_suppressed` is defined against and what the I-5 positive control keys on; V-5 binds four sprints. Renaming there is a seam change by definition, which is what rev 3 may not be. |
| **η** *(added)* | rename the **INTERNAL** `NameMatchResult.candidates_considered` attribute only; both wire keywords untouched | code, **no wire** | **DEFERRED as DF-36.** The only option that fixes the hazard that actually bit (D-2, the authoring hazard) without touching the wire at all, so "RETAINED UNCHANGED" holds literally *and* in spirit. Blast radius is two read-sites (`match_lead.py:538`, `:623`). It is still a code change and must not ride a TEXT-ONLY rev. |

**Receipt — NEW-1's shape is narrower than PT-04 and the FIXRECEIPT state it.**
Both say *"the five retained ops lines carry `candidates_considered`"*
(PT-04 §C row NEW-1; FIXRECEIPT §4 item 9, which then names only two in its own
parenthesis). Own-hands at `6c44cec7`, `git grep -n` over
`pipeline/stages/match_lead.py`: the field appears on **two** of the five —
`name_evidence_organic` (`:538`) and `name_evidence_matched` (`:623`).
`name_evidence_below_floor` (`:514-521`) carries `candidates_gated` only;
`name_evidence_ambiguous` (`:488-494`) and `name_evidence_read_failed`
(`:151-156`) carry neither. The qa VERDICT `:516` anchors the correct pair. **The
blast radius is 2-of-5, not 5-of-5** — recorded because a certifier reading
"five" against a head showing two would find a divergence that is not there.

**Receipt — the value on the ops lines.** `result.candidates_considered` is
`len(candidate_set.candidates)` (`name_evidence.py:1411`), assigned from the
**narrowed** set (`match_lead.py:352` → `:394`) — arithmetically identical to
what the V-5 line publishes as `candidates_in_effective_window`
(`match_lead.py:287-289`). The `NameMatchResult` field is honestly documented for
what it holds — *"candidates_considered: how many candidates were in the window"*
(`name_evidence.py:647`). **The collision is between the dataclass vocabulary and
the contract vocabulary, not between the code and itself.**

**Receipt — no machine consumer.** `name_evidence_counts.py:299` reads
`candidates_considered` off the **row** plane, not a log line; the row's value is
`pool.pool_size` (`match_lead.py:442`). The three machine-read planes (V-5 line
`:285`, V-6 row `:442`, S-04 `name_evidence_window` line `:385`) all carry the
pool. Only the two human lines carry the narrowed value under that name.

#### What rev 3 did NOT touch

§0 predicate · V-1 · V-2 · V-3 · V-4 · V-5's field table · V-6 · V-7 ·
V-8.1/2/3/5/6/7 · §4 · §5 · §6 · §7 · §8 · §9 · §10 · §11 · §12 · §13. `binds`,
`consumes`, `resolves`, `flags_not_resolves`, `build_target_hash` and
`reads_taken_at` are unchanged. `status` remains **FROZEN**.

#### §R note — D-9 / DF-33, for a successor sitting, NOT this rev

I-3's denominator (`row_plane_n` vs `countable_n`) is a ruling on the frozen §7
read contract and is **not settled here**. Recorded so the successor inherits a
shaped question rather than a raw one: `row_plane_n` counts rows **seen**;
`countable_n` counts rows **read**. I-3 is a silent-writer detector, so existence
is the right comparand — but `countable_n == 0 AND row_plane_n > 0` is rows
present and unreadable, which is neither agreement nor divergence and must not
render as AGREE. The likely shape is a third token (rows-present-unreadable),
not a denominator swap; a two-valued detector with a reachable vacuous-green is
the I-3 class turned on itself. **S-11's landing note must name the vacuous-AGREE
state so the first post-deploy AGREE is not read as evidence** (PT-04 §C row
D-9). Trigger: DF-33.

---

*Revision 4, TEXT-ONLY, 2026-09-04, same seat (10x-dev `architect`) that
authored revs 2 and 3. Authority: RATIFICATION 2026-09-04 RS-12 + derived +
teed act #2. Head read for the Clause-2 receipt:
`6c44cec7cd07b9b9c7871b61bee54159e1de4310`. Scope: **TEXT-ONLY** — §0's
predicate (a ratified substring swap), one §10 cell, and this log. No
mechanism, no threshold value, no seam limb, no V-clause. Self-attestation cap
**MODERATE** per `self-ref-evidence-grade-rule` — this seat is amending its own
contract; the rite-disjoint certifier at S-10 remains the attester and rev 4 is
not a certificate. Classification: **[TACTICAL | MODERATE]** — a wording
correction carrying a ratified premise change, plus a conformance note whose
falsification is mechanically checkable at the cited head.*

---

*Revision 3, TEXT-ONLY, 2026-09-03, same seat (10x-dev `architect`) that authored
rev 2. Head read for every rev-3 receipt:
`6c44cec7cd07b9b9c7871b61bee54159e1de4310`. Self-attestation cap **MODERATE** per
`self-ref-evidence-grade-rule` — this seat is amending its own contract against a
head it did not build; the rite-disjoint certifier remains the attester and rev 3
is not a certificate. Classification: **[TACTICAL | MODERATE]** — a text-
conformance correction with a mechanically checkable falsification, not an
architectural change.*

---

*Revision 2, authored at S-01, 2026-09-03. Reads at `autom8y origin/main
b80a9687`. Consumes PACKET §2/§9 and THREAT T-01/T-02/T-10/T-13/T-15 + §4.3 +
M-d/M-g, each code claim re-derived by this seat's own reads (SVR-13..SVR-18).
Self-attestation cap MODERATE — S-10's rite-disjoint critic is the attester.*
