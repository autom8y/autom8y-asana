---
type: review
status: draft
---

# READ — Office `15caa02c` books while its only Offer is INACTIVE (T2)

**Seat:** observability-engineer · **Date:** 2026-09-14 · **Mode:** READ-ONLY (no repo file changed outside this artifact, no Asana write, no comment, no alarm armed, nothing merged)
**Charge:** `read-the-name` wave 1, charge-DAG node **T2**; `HANDOFF-name-the-client` row SIZING-`15caa02c` "NO WATCHER".
**Refs of record:** autom8y-asana `origin/main` = `2ef49ff60e55a54e760c6b49dc522fe4a079c593` (fetched this session; the worktree for this artifact is branched off that exact ref). Region **us-east-1**. AWS account id withheld → `<ACCOUNT>`.
**Fence honoured:** guid8 only (`15caa02c`, `4ec260bf`, …) — no full GUID, no task name (Asana task names ARE client names), no phone digit, no account id.

**The class ruling is pythia's. This node measures both hypotheses and reports. No verdict line is spoken here.**

---

## 0. BLUF — the two evidence lines, first

**H1 (a non-Offer booking path) — NOT SUPPORTED.** On the terminal-outcome unit U-3, subject `15caa02c` and the active control `4ec260bf` are **identical in kind**: the same five events, the same `office_identity_kind=resolved`, the same `status=scheduled` on every `booking_completed`, the same `park_key` discipline on declines, the same day-by-day cadence across the 30-day window, and the same booking-onset date. The booking lines carry **no** `intake_source`, **no** `product`, **no** `offer`, **no** stage field — the key set is identical between subject and control (12 keys on `booking_completed`, 10 on `contente_booking_booked`, both offices). The only kind-level difference is 3 `booking_intake_fault` (`loss_kind=intake_fault`) on the subject and 0 on the control — a fault, not a different product path. There is no second path to find on this log plane.

**H2 (the Asana section is stale) — STRONGLY SUPPORTED, and the provenance is worse than "stale".** The subject's only Offer task sits in `INACTIVE` today, but across a **complete** 354-story pagination (2024-07-15 → 2026-05-29) it carries **only four `section_changed` stories, and the last one moved it INTO an active-class section**: `IMPLEMENTING -> OPTIMIZE - Human Review` at `2024-08-19T17:30:07.172Z`. **No story records a move into `INACTIVE` at all.** The current membership and the recorded history disagree. The control proves the mechanism works and is current: `ca70baa8`'s chain is well-formed and ends `OPTIMIZE - Human Review -> ACTIVE` on `2026-08-26T15:39:22.972Z`.

**The bridging fact:** `OPTIMIZE - Human Review` is in the **active** group of `OFFER_CLASSIFIER` (`src/autom8_asana/models/business/activity.py:181-210` at `origin/main`). So the last thing Asana's own history says happened to this Offer is that a human moved it to an **active** section — and the office has been producing terminal outcomes on the live wire ever since.

**Named observability gap found in passing (owner: platform-engineer):** `chiropractor_guid` is **not stamped on booking lines before 2026-09-09**. Fleet-wide there are 1,443 booking events across all 31 days of the window, but `count_distinct(guid)` on those lines is **0 every day through 2026-09-08** and only becomes non-zero on 09-09. Every guid-attributed booking number in this report therefore covers **6 days (09-09..09-14), not 30** — and is labelled as such. The decline arm of U-3 is guid-stamped across the whole window; the booking arm is not. This asymmetry is the reason "NO WATCHER" could persist.

---

## 1. Method, credentials, and reachability (all taken this session)

| Item | Value | Command |
|---|---|---|
| autom8y-asana `origin/main` | `2ef49ff60e55a54e760c6b49dc522fe4a079c593` | `git fetch origin main && git rev-parse origin/main` |
| AWS identity | `arn:aws:sts::<ACCOUNT>:assumed-role/AWSReservedSSO_AdministratorAccess_…/tomtenuta`, rc=0 | `aws sts get-caller-identity --region us-east-1 --query Arn --output text` |
| `ASANA_PAT` | present in env, live (both live passes below returned 200-class bodies) | `printf 'PAT_SET=%s\n' "${ASANA_PAT:+yes}"` |
| Log group | `/aws/lambda/autom8-email-booking-intake`, `retentionInDays=90`, `storedBytes=82,749,916` | `aws logs describe-log-groups --region us-east-1 --log-group-name-prefix /aws/lambda/autom8-email-booking-intake` |
| Window | `2026-08-15T00:00:00Z` .. `2026-09-14T23:59:59Z` | every Insights call below |
| Insights driver | `$SP/t2_ins.sh <label> <query-file>` — `aws logs start-query` + poll `get-query-results`, prints `recordsScanned` from the response `statistics` block | scratchpad |

Retention is **not** a confound: a bare `stats count() by bin(1d)` over the window returns **31 rows, one per day**, min 1,738 / max 116,835 records (`recordsScanned=606,883`, `recordsMatched=606,883`). The window is fully covered by data.

**Fence note on raw reads.** One query pulled raw `@message` (60-line cap) to discover the field vocabulary. Those lines carry an `office_name` key — a client name. The raw bodies stayed in the session scratchpad; **only key *names* and non-PII key *values* are reproduced here.** No name, no phone, no appointment identifier value appears in this artifact.

---

## 2. H1 — the log plane

### 2.1 Field vocabulary discovered first (not assumed)

```
fields @message | filter ispresent(event) | stats count() as n by event | sort n desc | limit 200
```
→ `recordsScanned=606,883` · `recordsMatched=449,844` · **68 distinct `event` values**. All six U-3 members are present fleet-wide in the window: `terminal_decline` 3,565 · `booking_gate_declined` 1,169 · `booking_completed` 818 · `contente_booking_booked` 625 · `ad_lead_gate_refused` 623 · `booking_intake_fault` 241. (`terminal_decline_parked` 2,284 is the park arm.)

### 2.2 U-3 for subject and control — the same run, the same resolver shape

```
fields coalesce(chiropractor_guid, office.chiropractor_guid) as guid
| filter ispresent(guid) | filter guid like /^(15caa02c|4ec260bf)/
| filter event in ["terminal_decline","ad_lead_gate_refused","booking_gate_declined","booking_completed","contente_booking_booked","booking_intake_fault"]
| fields substr(guid,0,8) as guid8 | stats count() as n by guid8, event | sort guid8 asc, n desc
```
→ `recordsScanned=190,071` · `recordsMatched=227` · 9 rows.

| event | `15caa02c` (SUBJECT) | `4ec260bf` (POS-CONTROL, Asana-active) |
|---|---|---|
| `terminal_decline` | **91** | 100 |
| `booking_completed` | **7** | 10 |
| `ad_lead_gate_refused` | **6** | 5 |
| `contente_booking_booked` | **1** | 4 |
| `booking_intake_fault` | **3** | 0 |
| `booking_gate_declined` | 0 | 0 |
| **total U-3** | **108** | 119 |

The subject is not a marginal case: it is **91% of the control's U-3 volume** while carrying the opposite Asana label.

### 2.3 PATH fields — the discriminator that does not exist

```
… same filter …
| stats count() as n by guid8, event, office_identity_kind, status, loss_kind, park_key
```
→ `recordsScanned=190,075` · `recordsMatched=227` · 79 rows, re-aggregated locally:

| guid8 | event | n | `office_identity_kind` | `status` | `loss_kind` | distinct `park_key` |
|---|---|---|---|---|---|---|
| `15caa02c` | `terminal_decline` | 91 | resolved 9 / absent 82 | absent | absent | **29** |
| `15caa02c` | `booking_completed` | 7 | **resolved 7** | **scheduled 7** | absent | 0 |
| `15caa02c` | `ad_lead_gate_refused` | 6 | resolved 6 | absent | absent | 0 |
| `15caa02c` | `booking_intake_fault` | 3 | resolved 3 | absent | **intake_fault 3** | 0 |
| `15caa02c` | `contente_booking_booked` | 1 | resolved 1 | absent | absent | 0 |
| `4ec260bf` | `terminal_decline` | 100 | resolved 9 / absent 91 | absent | absent | **39** |
| `4ec260bf` | `booking_completed` | 10 | **resolved 10** | **scheduled 10** | absent | 0 |
| `4ec260bf` | `ad_lead_gate_refused` | 5 | resolved 5 | absent | absent | 0 |
| `4ec260bf` | `contente_booking_booked` | 4 | resolved 4 | absent | absent | 0 |

Every booking on both offices is `office_identity_kind=resolved` and `status=scheduled`. The park discipline matches (29 vs 39 distinct `park_key`, ~1 decline per park key on both).

**The field vocabulary on the booking lines themselves** (60 raw lines, `recordsScanned=69,693`, `recordsMatched=25`; key names only):

`appointment_id` · `chiropractor_guid` · `event` · `failed_stage` · `hold_lever` · `http_status` · `idempotency_key` · `level` · `loss_kind` · `office_identity_kind` · `office_name` · `pipeline_status` · `service` · `span_id` · `status` · `status_code` · `timestamp` · `trace_id`

Key-set cardinality is **identical across the two offices**: `booking_completed` 12 keys for both, `contente_booking_booked` 10 keys for both, and the subject-only `booking_intake_fault` carries 14 (the extra three being `failed_stage`, `hold_lever`, `pipeline_status`). **There is no `intake_source`, no `product`, no `offer`, no `stage` field on any booking line for either office.** A confirmatory query filtering `intake_classified`/`office_resolved`/`booking_attempt`/`lead_created`/`guid_resolved_via_data_service` on `intake_kind`, `intake_source`, `resolution_source` returned `recordsScanned=575,228` · **`recordsMatched=0`** — those field names do not exist. The log plane carries **no product/stage/intake discriminator at all**, so H1's "which product/stage/intake produced them?" has no answer *because the question has no field*, not because the two offices answer it differently.

[UV-P: that no booking path outside `/aws/lambda/autom8-email-booking-intake` produced these bookings | METHOD: cross-log-group sweep of the other five `autom8-email-booking-intake-*` groups plus any non-EBI booking producer | REASON: charge scoped this node to the one named log group; three of the five sibling groups show `storedBytes: 0` and `-contente-reconcile` shows 6,910,235 — unswept here]

### 2.4 Temporal cadence — and the guid-stamping gap

```
… U-3 filter … | stats count() as n, sum(event="booking_completed" or event="contente_booking_booked") as bookings by bin(1d) as day, guid8
```
→ `recordsScanned=184,312` · `recordsMatched=227` · 45 rows.

Both offices produce U-3 traffic on **essentially the same days** across the whole window (subject active on 21 of 31 days; control on 23). Bookings, however, are **zero for both offices every day through 2026-09-09** and then appear together:

| day | `15caa02c` U-3 / bookings | `4ec260bf` U-3 / bookings |
|---|---|---|
| 2026-09-10 | 9 / **3** | 11 / 5 |
| 2026-09-11 | 12 / **4** | 10 / 6 |
| 2026-09-13 | 3 / **1** | 4 / 1 |
| 2026-09-14 | 2 / 0 | 3 / 2 |

**Firing control for that onset — it is a stamping gap, not a behaviour change:**

```
filter event in ["booking_completed","contente_booking_booked"]
| stats count() as n_fleet, count_distinct(coalesce(chiropractor_guid, office.chiropractor_guid)) as n_offices by bin(1d) as day
```
→ `recordsScanned=62,439` · `recordsMatched=1,443` · 28 rows. Fleet booking volume is non-zero on **every** day of the window (14 – 272/day; e.g. 2026-08-27 = 272, 2026-09-01 = 102), yet `n_offices` is **0 on every day through 2026-09-08**, becomes 2 on 09-09, then 20 / 20 / 12 / 15 / 12. The guid simply is not on the booking line before 09-09.

**Consequence, stated plainly:** the subject's "8 bookings" and the control's "14" are **6-day** figures (09-09..09-14). The 91 vs 100 decline figures are **30-day**. Both hypotheses are measured on the same asymmetry, so the subject-vs-control comparison stands; the absolute booking counts must not be read as 30-day rates.

---

## 3. H2 — Asana

### 3.1 The resolver control — identical `by_prefix()`, one run, zero API calls

The report under challenge (`.ledge/reviews/READ-offer-activity-sizing-2026-09-11.md` at `origin/main`) resolved via `by_prefix()` over the Business project `1200653012566782`, `Company ID` custom field. That resolver was re-run **verbatim** from the 2026-09-11 dumps (`biz_dump.json`, `asana_dump.json`) — **zero API calls** — with the subject, **all four** positives, and the negative **in the same run**:

```bash
AUTOM8Y_DATA_URL=http://offline-cli.local ASANA_WORKSPACE_GID=offline LOG_LEVEL=ERROR \
  uv run --quiet python "$SP/t2_resolver.py"     # from the autom8y-asana checkout
```

Registry integrity printed by the same run: `businesses=2574` · `CompanyID_nonempty=999` · `uuid_shaped=931` · `distinct_8hex_prefixes=898` · **`TRUE_collisions=0`** · `offers_total=4193`. Injectivity holds; no prefix is ambiguous.

| role | guid8 | status | Business § | n offers | offer sections | `max_offer_activity` |
|---|---|---|---|---|---|---|
| **SUBJECT** | `15caa02c` | Resolved | `BUSINESSES` | **1** | `['INACTIVE']` | **inactive** |
| POS-CONTROL | `4ec260bf` | Resolved | `BUSINESSES` | 7 | `['ACTIVE','ACTIVE','INACTIVE'×5]` | **active** ✔ |
| POS-CONTROL | `d167d635` | Resolved | `BUSINESSES` | 2 | `['AWAITING REP UPDATE','ACTIVE']` | **active** ✔ |
| POS-CONTROL | `8e56f6e1` | Resolved | `BUSINESSES` | 2 | `['AWAITING REP UPDATE','ACTIVE']` | **active** ✔ |
| POS-CONTROL | `ca70baa8` | Resolved | `BUSINESSES` | 1 | `['ACTIVE']` | **active** ✔ |
| NEG-CONTROL | `00000000` | **absent-in-asana** ✔ | — | — | — | — |

**4/4 positives → active. Negative → absent. Subject → inactive.** The 2026-09-11 reading reproduces exactly; the subject's classification is not a resolver artefact.

A **live refreshed pass** (PAT live, 2026-09-14) confirms the dump is still current for the subject: Offer `1207818294474681` memberships = `[('1143843662099250', 'INACTIVE')]`. Both passes are printed.

### 3.2 The Offer task's own record and its section-move history

Live `GET /tasks/1207818294474681` (subject's **only** Offer; `parent.gid=1207818295260598`):

| field | value |
|---|---|
| `created_at` | `2024-07-15T22:57:47.670Z` |
| `modified_at` | **`2026-05-29T15:14:33.074Z`** |
| `completed` | `false` (`completed_at: null`) |
| current section (project `1143843662099250`) | **`INACTIVE`** |
| `num_subtasks` | 0 |

Full story pagination (`GET /tasks/{gid}/stories?limit=100` followed to exhaustion via `next_page.offset`): **354 stories**, span `2024-07-15T22:57:48.062Z` .. `2026-05-29T15:14:32.589Z`, of which **4 are `section_changed`**:

| when | move |
|---|---|
| `2024-07-15T22:59:20.969Z` | `PLAYS -> Sales Process` (ignored → ignored) |
| `2024-07-23T22:04:34.805Z` | `Sales Process -> ACTIVATING` (ignored → **activating**) |
| `2024-08-19T16:58:59.217Z` | `ACTIVATING -> IMPLEMENTING` (activating → activating) |
| **`2024-08-19T17:30:07.172Z`** | **`IMPLEMENTING -> OPTIMIZE - Human Review`** (activating → **ACTIVE**) |

**There is no fifth move.** The last recorded act on this Offer's section is a move **into an active-class section**, and nothing in 354 stories records it leaving. The tail of the story stream is ordinary field edits (`number_custom_field_changed` at `2026-05-29T15:14:32.589Z`, `text_custom_field_changed` on 2025-10-22/23) — no section event.

`OPTIMIZE - Human Review` ∈ active group; `INACTIVE` ∈ inactive group — both per `OFFER_CLASSIFIER`, `src/autom8_asana/models/business/activity.py:181-210` at `origin/main`, read verbatim this session.

**Firing control — the story mechanism works and is current.** `ca70baa8` (POS-CONTROL, single Offer, structurally the closest match to the subject): 132 stories, **9** `section_changed`, span `2026-01-08` .. `2026-08-29`, chain `PLAYS -> Sales Process -> ACTIVATING -> IMPLEMENTING -> … -> Sales Process -> ACTIVATING -> IMPLEMENTING -> (NEW LAUNCH REVIEW ->) OPTIMIZE - Human Review -> **ACTIVE**` with the final move at `2026-08-26T15:39:22.972Z`. Asana emits `section_changed` for section moves, it emitted nine for this office, and the most recent is 19 days old. The subject's silence is therefore **informative**, not a limitation of the API. Two further controls (`4ec260bf` ACTIVE offer, `d167d635` ACTIVE offer) also carry `section_changed` stories in 2026 (`2026-08-21T15:08:03.801Z` and a 2025 chain respectively).

### 3.3 Dating the label against the bookings

| event | when |
|---|---|
| Last recorded Offer section move (into an **active** section) | **2024-08-19T17:30:07Z** |
| Offer task last modified at all | **2026-05-29T15:14:33Z** |
| Business task last modified | `2026-08-20T00:48:47Z` |
| Unit last modified | `2025-04-28T13:45:27Z` |
| Subject's U-3 traffic in window | 21 of 31 days, **108 terminal outcomes** |
| Subject's guid-attributed bookings | **8**, all 2026-09-10 .. 2026-09-13 |

The move into `INACTIVE` **cannot be dated** — no story carries it. What can be dated is that the last *recorded* section decision was `active`, made 2024-08-19, and that the Offer record has been untouched for 3.5 months while the office booked.

[UV-P: the exact date and actor of the transition into `INACTIVE` | METHOD: Asana audit-log API (enterprise) or `/v1/offers/section-timelines` served against a warmed story cache | REASON: no `section_changed` story exists for it; the stories API is the only history surface this node could reach read-only]

### 3.4 The Units — does a Unit book while the Offer sleeps? **No.**

Business `1207818294169805` has 7 direct subtasks; **none** is in the Unit project `1201081073731555`. A depth-2 subtask walk finds exactly **one** Unit task: `1207818459866503`, section **`Paused`**.

`Paused` ∈ the **inactive** group of `UNIT_CLASSIFIER` (`activity.py`, unit groups, `project_gid="1201081073731555"`, read verbatim at `origin/main`). Under `max_unit_activity` (`src/autom8_asana/models/business/business.py:448` at `origin/main` — `min(activities, key=ACTIVITY_PRIORITY.index)` over child Units) the office is **inactive at the Unit grain too**.

The Unit's own history: 113 stories, span `2024-07-15` .. **`2025-04-28T13:45:27.859Z`**, 4 `section_changed`, the last being `Month 1 -> Paused` at `2025-04-27T17:38:15.019Z`. Unlike the Offer, the Unit's move into a dark section **is** properly recorded — which sharpens the Offer's anomaly by contrast.

**So both Asana grains say dark, and the office books anyway.** H2 is not "one stale field": the Offer grain is stale *and* its transition is unrecorded, while the Unit grain was deliberately parked 16 months ago and left there.

### 3.5 `/v1/offers/section-timelines` — located, not exercised

Handler found at `src/autom8_asana/api/routes/section_timelines.py:125-132` (`@router.get("/section-timelines")`, `get_offer_section_timelines`), mounted at `src/autom8_asana/api/main.py:521`. It takes `period_start` / `period_end` / optional `classification`, replays Asana section history over the window via `get_or_compute_timelines(..., BUSINESS_OFFERS_PROJECT_GID, classifier_name="offer", ...)`, and returns `active_section_days` / `billable_section_days` / `current_section` / `current_classification` per offer, with an `imputation` block whose `basis` is `"inferred-from-story-cache-warmth"`.

[UV-P: what `/v1/offers/section-timelines` would report for this Offer over 2026-08-15..2026-09-14 | METHOD: authenticated GET against the deployed service with a Bearer token | REASON: this node is READ-ONLY against Asana and CloudWatch; no service base URL or token was in scope, and the endpoint replays the same `section_changed` stories already exhausted directly in §3.2 — it would necessarily report zero section-days movement and fall through to its imputation path]

---

## 4. Reading — which hypothesis the evidence supports, how strongly, and what would falsify each

### H1 — "its bookings ride a path the Offer project does not reflect"

**NOT SUPPORTED. Confidence: high on the plane measured; bounded by the UV-P in §2.3.**

Four independent ways the two offices are the same in kind, each with the active control measured in the same run: identical event membership in U-3; identical `office_identity_kind=resolved` / `status=scheduled` on every booking; identical key sets on the booking lines with **no** product/stage/intake field existing at all; identical daily cadence and identical booking-onset date driven by a fleet-wide stamping change. The subject's 3 `booking_intake_fault` are a *failure* on the same path, not evidence of a second path.

**What would falsify this reading** (i.e. resurrect H1): a booking producer outside `/aws/lambda/autom8-email-booking-intake` — the `-contente-reconcile` group (6.9 MB stored) is the live candidate — showing bookings for `15caa02c` that the subject's lines here do not account for; **or** a path discriminator existing off the log line (in the data service, the lead record, or the Contente write plane) that separates these two offices. Neither was swept here and §2.3 carries the UV-P.

### H2 — "the Asana section is STALE; the office is live, the Offer never moved back / was moved wrongly"

**SUPPORTED, and more specifically than the hypothesis was written. Confidence: high for the Offer grain.**

The hypothesis said "never moved back / was moved wrongly". The evidence says something sharper: **the move into `INACTIVE` was never recorded at all.** Across a complete 354-story pagination the last section decision on this Offer is `IMPLEMENTING -> OPTIMIZE - Human Review` — an **active** section — on 2024-08-19, and the control `ca70baa8` proves `section_changed` stories are emitted, are nine-deep, and are 19 days fresh for a comparable live office. The Offer record has not been touched since 2026-05-29 while the office produced 108 terminal outcomes on 21 of 31 days and 8 bookings in the 6 days its guid has been stamped. The Unit grain is independently dark (`Paused` since 2025-04-27) and its darkening *was* recorded — the contrast isolates the Offer's anomaly.

**What would falsify this reading:** (a) evidence that Asana suppresses `section_changed` stories for some move mechanism (bulk move, CSV import, section deletion/merge, an API `addProject` with `insert_section`) that was applied to this Offer — that would convert "unrecorded" back to plain "stale" without disturbing the staleness conclusion; (b) a story-retention or permission limit truncating this task's stream — argued against by the complete pagination reaching `created_at` and by 354 > 132 stories on the control, but not formally excluded; (c) a ruling that `INACTIVE` is the *correct* present label and the bookings are the anomaly — in which case the finding relocates to "a dark office is being worked by the live wire", which is an equally actionable defect and is exactly what row SIZING-`15caa02c` "NO WATCHER" names.

**The two hypotheses are not symmetric in what they cost.** H1 being false means there is nothing exotic to go find. H2 being true means the Offer section — the field the served-set definition is gated on — can disagree with reality **without leaving a trace**, for at least one office, for a period that cannot be bounded from Asana alone.

### Observability reading (my seat's own altitude)

Three gaps, none of them adjudications:

1. **The booking arm of U-3 was unattributable for most of the window.** Guid stamping on booking lines begins 2026-09-09 fleet-wide; declines carry it throughout. Any SLI built on "bookings per office" silently measured **zero offices** before that date while 1,443 bookings occurred. Owner: platform-engineer (instrumentation).
2. **No signal exists for "Asana says dark AND the wire says live".** The divergence is computable today from data both sides already hold (`max_offer_activity` vs U-3 presence in a trailing window) and nothing computes it. That is the literal content of "NO WATCHER".
3. **Section provenance has no integrity check.** A current section with no `section_changed` story explaining it is a detectable condition on the story cache that already backs `/section-timelines` (§3.5) — its own `imputation.basis` of `"inferred-from-story-cache-warmth"` is an admission that unobserved offers are imputed rather than flagged.

These are observations for pythia and the platform-engineer lane. **No alarm was designed, armed, or proposed as ratified here.**

---

## 5. What was NOT taken, and why

| Item | Status | Reason |
|---|---|---|
| Sibling log groups (`-contente-reconcile` et al.) | **NOT TAKEN** | charge scoped this node to `/aws/lambda/autom8-email-booking-intake`; carried as the §2.3 UV-P |
| `/v1/offers/section-timelines` live call | **NOT TAKEN** | §3.5 UV-P — no service URL/token in scope; the endpoint replays the stories already exhausted directly |
| Asana audit-log API (to date the unrecorded move) | **NOT TAKEN** | §3.3 UV-P — enterprise surface, not in scope for a read-only node |
| DB-side offer rows / `disabled` flags | **NOT TAKEN** | no DB access attempted; the 2026-09-11 report's DB figures are not re-derived or relied on here |
| 2026-09-11 dumps (`biz_dump.json`, `asana_dump.json`) | **INHERITED substrate, re-computed** | the resolver was re-run over them this session; the subject's current section was independently re-confirmed live (§3.1) |
| Any Asana write, comment, or field change | **REFUSED by charge** | Asana reads only |
| Class ruling / verdict | **RESERVED to pythia** | this node measures; it does not adjudicate |

---

## 6. Reproduction

```bash
# refs
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana && git fetch origin main && git rev-parse origin/main   # 2ef49ff6…
git show origin/main:src/autom8_asana/models/business/activity.py | sed -n '181,250p'                      # OFFER_/UNIT_CLASSIFIER
git show origin/main:src/autom8_asana/models/business/business.py | sed -n '440,462p'                       # max_unit_activity :448
git grep -n 'section-timelines' origin/main -- src/                                                         # routes/section_timelines.py:125

# log plane (each prints recordsScanned from the response statistics block)
"$SP/t2_ins.sh" vocab  "$SP/t2_q_vocab.txt"    # 606,883 scanned / 449,844 matched / 68 events
"$SP/t2_ins.sh" u3     "$SP/t2_q_u3.txt"       # 190,071 / 227 / 9 rows      <- §2.2
"$SP/t2_ins.sh" path   "$SP/t2_q_path.txt"     # 190,075 / 227 / 79 rows     <- §2.3
"$SP/t2_ins.sh" raw    "$SP/t2_q_raw.txt"      #  69,693 /  25 / key names   <- §2.3 (bodies stay in scratchpad)
"$SP/t2_ins.sh" intake "$SP/t2_q_intake.txt"   # 575,228 /   0 -> fields absent
"$SP/t2_ins.sh" day    "$SP/t2_q_day.txt"      # 184,312 / 227 / 45 rows     <- §2.4
"$SP/t2_ins.sh" fleet  "$SP/t2_q_fleet.txt"    #  62,439 / 1,443 / 28 rows   <- §2.4 control
"$SP/t2_ins.sh" ret    "$SP/t2_q_ret.txt"      # 606,883 / 606,883 / 31 days <- §1 coverage

# Asana (read-only; ASANA_PAT from env)
AUTOM8Y_DATA_URL=http://offline-cli.local ASANA_WORKSPACE_GID=offline LOG_LEVEL=ERROR \
  uv run --quiet python "$SP/t2_resolver.py"   # §3.1 offline control, ZERO API calls
python3 "$SP/t2_asana_h2c.py"                  # §3.2/§3.4 full story pagination, subject offer + unit
python3 "$SP/t2_moves.py"                      # §3.2 move DIRECTIONS + ca70baa8 control chain
```

Scratchpad: `/private/tmp/claude-501/-Users-tomtenuta-Code-a8-a8-repos-autom8y-asana/d5861864-ca42-4b96-84df-0a4323c797aa/scratchpad`. Outputs: `t2_{vocab,u3,path,raw,intake,day,fleet,ret}.json`, `t2_resolver_offline.json`, `t2_asana_h2.json`.

---

**Evidence grade: MODERATE** (self-ref cap — single seat, own hands, no rite-disjoint corroboration; `self-ref-evidence-grade-rule`). The H1 event/field measurements and every control in §2 and §3.1 are STRONG-eligible on re-run: they are deterministic Insights aggregations and a zero-API-call resolver over frozen dumps. The §3.2 story-exhaustion claim is STRONG-eligible against the live API and is the load-bearing H2 anchor. The three §4 observability readings are `[STRUCTURAL | MODERATE]` and are **advisory to pythia and the platform-engineer lane, not rulings**.
