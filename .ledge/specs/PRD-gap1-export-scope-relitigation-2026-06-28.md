---
type: spec
status: draft
author: requirements-analyst (10x-dev rite)
date: 2026-06-28
impact: high
impact_categories: [security, auth, api_contract, cross_service]
supersedes_scope_of: TDD-gap1-asana-operator-rewire-2026-06-28.md §7.2 (GAP-1b escalation matrix — refined, not replaced)
pinned_trees:
  autom8y-asana: origin/main e7d71fa8
  autom8y-data: origin/main 3169fa96
  autom8y (auth @ services/auth): origin/main 3df3298a
---

# PRD — GAP-1 export-scope re-litigation: the cross-tenant agency-BI subset

> **Status:** DRAFT — requirements/scope artifact, NO code mutation. Reads pinned to `origin/main` for all three repos (local trees stale).
> **Owner:** requirements-analyst (10x-dev rite) · **Date:** 2026-06-28
> **Upstream:** architect TDD `TDD-gap1-asana-operator-rewire-2026-06-28.md` (Option M3 split → GAP-1b escalation to requirements/operator). This PRD discharges the GAP-1b **scope decision** for the de-identified subset and litigates the PII-wall exclusion.
> **Downstream:** architect (GAP-1b data-plane extension TDD), security (ADR-0040 gate), operator (the genuine product calls in §7).

---

## Telos anchor (the frame this scope is litigated against)

> Internal agency BI — The Natural Health Company aggregating across its ~75+ offices — as a **reusable agency-model primitive**: *"authorized aggregation, NEVER a master key."* Isolation by per-office token scope (the bounded owned set `O`); the whitelabel/multi-agency future as a reference seam. The litigation question: does per-patient / financial data flowing **cross-tenant through a single agency view** serve that telos, or contradict it?

---

## 0. Executive verdict (read this first)

Three findings, in order of load-bearing weight:

1. **The triage lands 8 admissible / 4 PII-wall.** Of the export's 12 tables, **8 are de-identified office-grain aggregates** (admissible to the operator plane) and **4 are per-patient (2) or financial (2) PII** (the wall — excluded from the cross-tenant agency view). See §2.

2. **The founding premise (Option-1) is CONFIRMED — earned, not assumed.** The agency-BI telos ("which office / offer / asset / campaign performs best across the fleet?") is an **aggregate-analytical** question, fully served by the 8 de-identified tables. The 4 PII tables answer **operational-workflow** questions (call this patient, reconcile this invoice) that (a) are not agency-BI-analytics, (b) already have a per-office-scoped path, and (c) carry a single-token blast-radius + multi-agency-generalization cost that is the precise antithesis of "authorized aggregation, never a master key." Option-1 is the correct **default**. It is conditional on ONE product fact (§7 OQ-1); if that fact is false, the verdict refutes to Option-4. See §3.

3. **★ The operator-plane extension is MUCH smaller than the TDD implied — the registered insights ALREADY EXIST, and 2 of the 4 needed are ALREADY allowlisted.** The TDD's "intersection = ∅" is true at the **wire-route / response-shape** level but FALSE at the **registered-insight-computation** level: the factory-frame route the export uses **delegates to the same `InsightRegistry`** via `FrameTypeMapper`. Six of the 8 admissible tables map to insights **already on the C-1 allowlist** (`account_level_stats` ×4, `asset_level_stats` ×2); only 2 (`offer_level_stats`, `question_level_stats`) need allowlist **additions**, and **no new insight needs to be built**. The extension is: **+2 allowlist names + a product-equivalence sign-off + the asana rewire onto the GAP-1a substrate.** See §1.3 and §4.

The counter stays RED until the operator FLIP; this PRD does not move it. It converts the GAP-1b escalation from "build matching insights for 8 tables + rule the PII tables" into a bounded, two-name allowlist extension plus an explicit, litigated PII-exclusion ruling.

---

## 1. The premise break (inherited, then refined)

### 1.1 What the export fetches (asana `e7d71fa8`)

`InsightsExportWorkflow._fetch_table` dispatches on `spec.dispatch_type` across **four** `DispatchType` values — `APPOINTMENTS`, `LEADS`, `RECONCILIATION`, `INSIGHTS` (`workflow.py:617-667`, `match spec.dispatch_type`). The 12 `TableSpec` rows live in `tables.py:124-266` (`TABLE_SPECS`). Eight rows are `INSIGHTS` (factory ∈ {`base`, `ad_questions`, `assets`, `business_offers`}); the other four are the three PII shapes.

> The export uses **4 of the 14** factories the client exposes (`client.py:659-674` `FACTORY_TO_FRAME_TYPE`); the other 10 (`account`, `ads`, `adsets`, `campaigns`, `spend`, `leads`, `appts`, `targeting`, `payments`, `ad_tests`) are not referenced by `TABLE_SPECS`.

### 1.2 What the operator plane serves (data `3169fa96`)

The sole operator route is `POST /api/v1/insights/operator/execute-batch` (`operator_insights.py:223-452`), gated by the **C-1 default-deny allowlist** `_OPERATOR_INSIGHT_ALLOWLIST = {business_summary, account_level_stats, asset_level_stats}` (`operator_insights.py:172-178`). Any other `insight_name` → bare 404-as-oracle **before DB resolution** (`operator_insights.py:353-354`). `reconciliation` is **deliberately C-1 EXCLUDED** pending OD-5 (`operator_insights.py:165-171`).

### 1.3 ★ The refinement the TDD missed: factory-frame DELEGATES to the registered insights

The asana `get_insights_async(factory=…)` POSTs to `/api/v1/data-service/insights` with `frame_type = FACTORY_TO_FRAME_TYPE[factory]` (`_endpoints/insights.py:182,189`). On the data side, `FrameTypeMapper._FRAME_TYPE_TO_INSIGHT` routes each frame_type to a **registered insight name** and **derives its dimensions/metrics from the same `InsightRegistry`** (`frame_type_mapper.py:78-105`). Resolving the full chain:

| Export factory | →frame_type (`client.py:659-674`) | →registered insight (`frame_type_mapper.py:79-83`) | On C-1 allowlist today? |
|---|---|---|---|
| `base` | `unit` | **`account_level_stats`** | **YES** (`operator_insights.py:175`) |
| `assets` | `asset` | **`asset_level_stats`** | **YES** (`operator_insights.py:176`) |
| `business_offers` | `offer` | `offer_level_stats` | NO — needs add |
| `ad_questions` | `question` | `question_level_stats` | NO — needs add |

So the export's `base`/`assets` tables **are** `account_level_stats` / `asset_level_stats` — the very insights already allowlisted. The "intersection = ∅" holds only at the **route + response-envelope** level (`/data-service/insights`→`InsightsResponse` vs `/insights/operator/execute-batch`→`BatchInsightResponse`); at the **insight-computation** level the intersection is large. This is the load-bearing correction that shrinks GAP-1b. (`business_summary` — the third allowlisted name, `library.py:367` — is the `dimensions=[date]` time-series insight; it is the natural candidate for the BY-period tables — see §4.3 equivalence question.)

---

## 2. The 12-table triage

PII classes: **DE-ID AGG** = de-identified office-grain aggregate (admissible cross-tenant); **PER-PATIENT** = row-level patient/lead grain (PII wall); **FINANCIAL** = customer/invoice grain (PII wall). All `INSIGHTS`-dispatch insights carry `office_phone` as a dimension — this is the **OFFICE business phone (the tenant key the operator owns)**, not patient PII; the data owner already cleared it by allowlisting `account_level_stats` + `asset_level_stats`, both of which carry it.

| # | Table | dispatch_type | Resolved insight / endpoint | PII class | Admissible? | Cite |
|---|-------|---------------|-----------------------------|-----------|-------------|------|
| 1 | SUMMARY | INSIGHTS (base) | `account_level_stats` (period=lifetime) | DE-ID AGG | **YES** | `tables.py:126-131`; `library.py:407` |
| 6 | BY QUARTER | INSIGHTS (base) | `account_level_stats` (period=quarter) † | DE-ID AGG | **YES** | `tables.py:159-178` |
| 7 | BY MONTH | INSIGHTS (base) | `account_level_stats` (period=month) † | DE-ID AGG | **YES** | `tables.py:180-199` |
| 8 | BY WEEK | INSIGHTS (base) | `account_level_stats` (period=week) † | DE-ID AGG | **YES** | `tables.py:201-220` |
| 9 | AD QUESTIONS | INSIGHTS (ad_questions) | `question_level_stats` (grain: question_key × office) | DE-ID AGG | **YES** (needs allowlist add) | `tables.py:222-227`; `library.py:1483` |
| 10 | ASSET TABLE | INSIGHTS (assets) | `asset_level_stats` (period=t30) | DE-ID AGG | **YES** | `tables.py:229-249`; `library.py:522` |
| 11 | OFFER TABLE | INSIGHTS (business_offers) | `offer_level_stats` (grain: offer_id × office) | DE-ID AGG | **YES** (needs allowlist add) | `tables.py:251-256`; `library.py:1295` |
| 12 | UNUSED ASSETS | INSIGHTS (assets) | `asset_level_stats` (include_unused=True) ‡ | DE-ID AGG | **YES** | `tables.py:258-265` |
| 2 | APPOINTMENTS | APPOINTMENTS | `GET /api/v1/appointments` (row-level, filter by lead phone) | PER-PATIENT | **NO — PII wall** | `tables.py:133-138`; `simple.py:143`; `appointments_read.py:71` |
| 3 | LEADS | LEADS | `GET /api/v1/leads` (row-level, lead phone) | PER-PATIENT | **NO — PII wall** | `tables.py:140-146`; `simple.py:248`; `leads_read.py:6,83` |
| 4 | LIFETIME RECONCILIATIONS | RECONCILIATION | `POST /insights/reconciliation/execute` (customer_id + hosted_invoice_url + invoice_number + SUM(amount)) | FINANCIAL | **NO — C-1 EXCLUDED (OD-5)** | `tables.py:148-151`; `reconciliation.py:156`; `operator_insights.py:165-171` |
| 5 | T14 RECONCILIATIONS | RECONCILIATION | same (window_days=14) | FINANCIAL | **NO — C-1 EXCLUDED (OD-5)** | `tables.py:153-157` |

**Verdict: 8 admissible (de-identified aggregate) / 4 PII-wall (2 per-patient + 2 financial).**

† The BY-period tables select `account_level_stats` via factory=base; `account_level_stats` has `dimensions=[office_phone, office, vertical]` (no time dimension), so a per-period **time series** may instead require `business_summary` (`dimensions=[date]`) or a period-breakdown capability — a product-equivalence question, not an admissibility question (§4.3, OQ-3). Admissibility (de-identified) is unaffected.
‡ `asset_level_stats` is admissible/allowlisted; whether the operator route honors the `include_unused` filter is an equivalence item (§4.3, OQ-4), not an admissibility item.

### 2.1 Why the 4 are the wall (grain evidence)

- **APPOINTMENTS / LEADS** are **row-level** fetches (`days`, `limit=100` — `tables.py:135-137,142-145`), returning per-appointment / per-lead rows filterable by **lead phone in E.164** (`appointments_read.py:71`, `leads_read.py:83`). This is patient/lead-grain PHI — exactly what the C-1 allowlist exists to refuse (the comment names `lead_phone` as the reason it is an allowlist and not the `_pii_dimension_names` dim-gate, `operator_insights.py:151-157`).
- **RECONCILIATION** exposes `customer_id` + a **bearer-accessible `hosted_invoice_url`** + `invoice_number` alongside `SUM(p.amount)` (`operator_insights.py:165-171`; `reconciliation.py:65`) — cross-agency financial PII, deliberately excluded pending OD-5.

---

## 3. The founding-premise litigation (both sides + verdict)

**Question:** Does the cross-tenant agency-BI export genuinely NEED per-patient (APPOINTMENTS, LEADS) + financial (RECONCILIATION) data, or is the agency value entirely in the de-identified aggregates?

### 3.1 Steelman for KEEPING the PII tables cross-tenant (→ Option-4, re-open the wall)

- **S-1 — feature parity / loss-aversion.** The export produces all 12 tables today. If TNHC's agency staff already consume per-patient appointment/lead lists and reconciliation **across offices**, dropping them removes a capability they have. "We had it" is a real cost.
- **S-2 — concrete cross-office operational use-cases exist.** No-show recovery (an agency team calling no-shows across all offices needs per-patient appointments + phone); lead-quality auditing (per-lead conversion across offices to flag bad lead sources); agency-level billing reconciliation (amounts/invoices across offices).
- **S-3 — bounded ownership ≠ "blending strangers."** The operator route is bounded to the agency's **owned set `O`** (`operator_insights.py:384-408`). The agency reading per-patient data for **its own offices** is arguably authorized access to data it already has rights to under its office relationships — not a cross-tenant leak. Under this framing, the PII never blends across unrelated tenants; the agency just sees its own offices.

S-3 is the strongest and must be met head-on, not dismissed.

### 3.2 The telos / compliance case for EXCLUDING them (→ Option-1)

- **T-1 — the design invariant is the load-bearing safety property.** C-1 default-deny is "the load-bearing non-PHI control" (`operator_insights.py:141-149`); the plane's stated guarantee is it "can NEVER serve a patient-grain or PII-bearing operand, by default." Re-opening it for PHI is not a tweak — it inverts the plane's defining property.
- **T-2 — single-token blast radius is the named anti-telos.** "Authorized aggregation, NEVER a master key." Even bounded to `O`, a SINGLE agency token spanning ~75 offices' **patient PHI** is a master-key-shaped blast radius: one compromised token → patient PHI across 75 offices. Per-office tokens bound that radius to one office; the agency aggregate token deliberately does not. PHI is exactly the payload where that difference is decisive.
- **T-3 — the multi-agency/whitelabel generalization raises the bar to a wall.** As a **reusable agency-model primitive**, "operators may read cross-office per-patient PHI" becomes a capability granted to EVERY future agency. De-identified aggregates generalize safely; cross-office PHI generalization demands per-agency HIPAA BAAs, patient-consent posture, and per-agency audit — a compliance program, not a code change.
- **T-4 — the use-cases are operational, not BI-analytical.** The agency-BI telos is **aggregate comparison** (best office / offer / asset / campaign). S-2's use-cases (call this patient, reconcile this invoice) are **per-record operational actions** — a different product, with a different rightful surface.
- **T-5 — the operational path already exists, per-office-scoped.** No-show recovery and reconciliation are per-office workflows the office's own staff (or the agency acting **per-office with per-office scope**) already perform. Pulling them into a single cross-tenant agency view does not unlock a NEW agency-BI need; it widens the blast radius of an EXISTING per-office capability — the literal T-2 anti-pattern.

### 3.3 Verdict — Option-1 CONFIRMED (conditional on OQ-1)

The decisive axis is **BI-analytics (aggregate, cross-office comparison) vs operational-workflow (per-record action)**. The agency-BI telos lands entirely on the de-identified aggregates (the 8 tables). The 4 PII tables serve operational workflows that are (a) not agency-BI-analytics [T-4], (b) already served per-office-scoped [T-5], and (c) impose a blast-radius + generalization cost antithetical to the telos [T-2, T-3]. S-3's "bounded ownership" rebuts "stranger-blending" but does **not** rebut T-2/T-3 — bounding to `O` still concentrates 75 offices' PHI behind one token and still becomes a fleet-wide grant in the multi-agency future.

**Therefore Option-1 is the correct default scope: the de-identified aggregate subset (8 tables) IS the cross-tenant agency-BI export; the 4 PII tables are EXCLUDED from the cross-tenant agency view.**

**The single condition that would refute** (→ Option-4): if the operator affirms that TNHC agency staff run **cross-office per-patient / financial OPERATIONAL workflows from this export today as a core agency function** (S-1+S-2 are live, not hypothetical), then the per-patient/financial tables have a genuine cross-office need and the wall must be re-litigated — but under a materially higher bar (OD-5 ratification + per-agency BAA/consent posture + narrowed token scope + audit), NOT by simply seeding them into C-1. That is OQ-1, the sharpest open question.

**Hard line (carried from the architect, re-affirmed):** Option-1 exclusion does **NOT** mean "silently produce fewer tables." It means the 4 PII tables are explicitly routed to a per-tenant disposition (§4.4) — and explicitly NOT kept on the SA fleet-read path, which would re-assert DATA-VAL-003 and defeat the GAP-1 telos.

---

## 4. The Option-1-aligned scope + operator-plane extension spec

### 4.1 Scope statement

The **cross-tenant agency-BI export** = the **8 de-identified aggregate tables**, served via the operator plane (minted `OperatorClaims` → `execute-batch`, bounded to owned set `O`), retiring the SA fleet-read path **for those 8 tables**. The **4 PII tables** are removed from the cross-tenant agency view and dispositioned per §4.4.

### 4.2 The operator-plane extension (data-side) — what GAP-1b must concretely add

The TDD assumed "build matching de-identified registered aggregate insights." **Refuted (§1.3): the insights already exist.** The actual data-plane delta is:

- **MUST add 2 names to `_OPERATOR_INSIGHT_ALLOWLIST`** (`operator_insights.py:172-178`): `offer_level_stats` and `question_level_stats`. Post-add allowlist = `{business_summary, account_level_stats, asset_level_stats, offer_level_stats, question_level_stats}`.
  - `offer_level_stats` (`library.py:1295`): de-identified aggregate, grain `offer_id × office_phone × vertical`; metrics are spend/leads/scheds/convs/ltv/cost-efficiency. No patient grain.
  - `question_level_stats` (`library.py:1483`): de-identified aggregate, grain `question_key × office_phone × vertical`; per-screening-question performance. No patient grain.
  - Both carry `office_phone` (the tenant key) on the SAME footing as the already-allowlisted `account_level_stats`/`asset_level_stats` — i.e., they clear the existing C-1 admission criterion.
- **MUST route each addition through ADR-0040 (FEATURE+, PII/auth)** — the data owner confirms "no patient-grain / PII dimension" per the allowlist's own admission rule (`operator_insights.py:159-163`); security reviews. This PRD asserts the de-identified classification from source; the data owner **ratifies**.
- **MUST NOT add `reconciliation`** (financial, C-1 EXCLUDED, OQ-5/OD-5).
- **No new InsightDefinition, no new route, no schema change.** The existing `BatchInsightExecutor` serves all five names (`operator_insights.py:430-432`).

### 4.3 Operator-plane vocabulary the route must serve (beyond the current 3-name allowlist)

The operator route must serve these `insight_name` values for the 8 admissible tables:

| Insight name | Tables served | Status | Equivalence question |
|---|---|---|---|
| `account_level_stats` | SUMMARY, BY QUARTER, BY MONTH, BY WEEK | allowlisted | **OQ-3:** account_level_stats has no time dimension; BY-period time series may need `business_summary` (dimensions=[date], already allowlisted) or a period-breakdown mode |
| `asset_level_stats` | ASSET TABLE, UNUSED ASSETS | allowlisted | **OQ-4:** does the operator `execute-batch` honor the `include_unused` filter (UNUSED ASSETS) via its `filters` field? |
| `offer_level_stats` | OFFER TABLE | **add** | data-owner PII confirm (§4.2) |
| `question_level_stats` | AD QUESTIONS | **add** | data-owner PII confirm (§4.2) |

**Cross-cutting equivalence (OQ-2):** the operator route returns `BatchInsightResponse` (`models.py:384`); the export currently reads `InsightsResponse.data`. The GAP-1a substrate already specifies a thin response adapter (`get_operator_insights_batch_async`, TDD §3.1). Product must confirm the registered-insight output (at the export's default parameterization — no custom metrics/dimensions) is an acceptable substitute for the current factory-frame output for each of the 8 tables. Because `FrameTypeMapper` derives the factory-frame dimensions/metrics from the **same** `InsightRegistry` entry (`frame_type_mapper.py:99-105`), the computations are the same engine modulo (period-breakdown OQ-3, include_unused OQ-4, response envelope OQ-2).

### 4.4 What the asana rewire then consumes (asana-side)

- **Rewire the 8 `INSIGHTS` `_fetch_table` arms** (`workflow.py:659-667`) to call the GAP-1a substrate `DataServiceClient.get_operator_insights_batch_async(insight_name=<mapped name>, …)` via the adapter, instead of `get_insights_async(factory=…)`. Mapping per §4.3.
- **Remove the 4 PII arms** (`workflow.py:618-631`: APPOINTMENTS/LEADS/RECONCILIATION) from the cross-tenant export path.
- **PII-table disposition (Option-1):** the 4 tables are NOT produced on the cross-tenant agency deck. Their operational data, IF needed, is served by a **per-office-scoped** mechanism (the office's own report path / a per-office token), **NOT** the agency operator token and **NOT** the SA fleet-read (which would re-assert DATA-VAL-003). The concrete per-tenant mechanism is OQ-6 (deferred; only built if OQ-1 confirms a real per-office operational need that the existing per-office reports do not already cover).
- **G-NO-FALLBACK preserved** (TDD ADR-Δ5): the operator path never falls back to a fleet-read on refusal/denial.

---

## 5. Acceptance criteria (SMART) + MoSCoW

### 5.1 MoSCoW

- **MUST:** (M1) operator allowlist extended with `offer_level_stats` + `question_level_stats` under ADR-0040, data-owner-ratified de-identified. (M2) the 8 admissible tables produced via the operator plane (minted token → execute-batch, bounded to `O`). (M3) the SA fleet-read path retired **for the 8 tables**. (M4) the 4 PII tables removed from the cross-tenant export; NOT kept on the SA path. (M5) G-NO-FALLBACK enforced.
- **SHOULD:** (S1) product-equivalence sign-off on OQ-2/OQ-3/OQ-4 before the FLIP. (S2) BY-period tables resolved to a concrete insight (`account_level_stats` vs `business_summary`).
- **COULD:** (C1) a per-office-scoped mechanism for the excluded PII tables (only if OQ-1/OQ-6 establish the need).
- **WON'T (this scope):** (W1) `reconciliation` on the operator plane (OD-5 reserved). (W2) any cross-tenant per-patient/financial surface absent an Option-4 re-litigation. (W3) moving the counter (operator FLIP is operator-terminal).

### 5.2 SMART acceptance criteria (testable by QA Adversary)

- **AC-1 (allowlist):** `_OPERATOR_INSIGHT_ALLOWLIST` contains exactly the 5 de-identified names; `reconciliation` absent. A `reconciliation` operator request → bare 404-as-oracle (two-sided: an allowlisted name → 200). Measurable: assertion on the frozenset + the RT-2 canary.
- **AC-2 ("the counter moves on the admissible subset"):** for the agency's owned offices, the export produces all **8** admissible tables with non-empty rows sourced from `execute-batch`, AND the operator audit sink records `honored` events for those offices (`operator_insights.py:414-422`), AND telemetry shows **zero `/data-service/insights` SA-path calls for the 8 rewired tables** (grep-zero + metric). The "counter" = count of tables served via the operator plane reaching 8/8 for owned offices at FLIP.
- **AC-3 (PII exclusion is clean):** grep-zero — the cross-tenant/operator export path invokes none of `get_appointments_async` / `get_leads_async` / `get_reconciliation_async` (`workflow.py:618-631` arms removed from that path). No SA fleet-read survives for any of the 12 tables on the cross-tenant path (M4 + M3 together → DATA-VAL-003 not re-asserted).
- **AC-4 (round-trip, deployed-image):** the GAP-1a RT-1/RT-2/RT-3 two-sided canaries pass against a synthetic-ARN-allowlisted auth + the real operator route, for at least one of the **newly added** insight names (`offer_level_stats` or `question_level_stats`) — proving the extension, not just the seed.
- **AC-5 (equivalence gate):** for each of the 8 tables, a recorded product sign-off that the operator-route output is an acceptable substitute (discharges OQ-2/3/4) before `dry_run=false`.

---

## 6. Edge cases

- **EC-1 — BY-period time series from a non-time-dimensioned insight.** `account_level_stats` groups by office, not period; `business_summary` is the date-grained insight. If neither yields the BY QUARTER/MONTH/WEEK shape via one call, the rewire may need N period-scoped calls or a period-breakdown mode. Expected behavior: resolved by OQ-3 sign-off before rewiring those 3 arms; until then they stay un-rewired (still on SA path) and the FLIP is partial — which violates M3 unless explicitly accepted.
- **EC-2 — `include_unused` for UNUSED ASSETS.** If the operator `execute-batch` `filters` field cannot express `include_unused`, UNUSED ASSETS cannot be served on the operator plane as-is. Expected: OQ-4; fallback is dropping UNUSED ASSETS from the agency deck (it is the lowest-value table) or a small data-plane filter addition.
- **EC-3 — empty owned set `O`.** Agency owns zero resolvable offices → all-or-nothing denies → bare 404 (`operator_insights.py:375-408`). Expected: export produces an empty agency deck gracefully (WARNING, no crash, no SA fallback).
- **EC-4 — partial ownership.** One requested office not in `O` → the WHOLE batch 404s (all-or-nothing, `operator_insights.py:393-408`). Expected: the asana rewire must call per owned office or pre-scope the batch to `O`; a single non-owned office must not blank the entire agency run.
- **EC-5 — token expiry mid-run (TTL 300s).** Long agency runs exceed the token TTL. Expected: GAP-1a T-C single-retry re-mint (TDD §3.2).
- **EC-6 — office_phone as tenant key vs PII.** All 5 allowlisted insights carry `office_phone`. Expected: this is the OFFICE business phone (tenant key the agency owns), NOT patient PII; the data owner re-confirms this holds for `offer_level_stats`/`question_level_stats` at ADR-0040 (consistent with the existing `account_level_stats`/`asset_level_stats` precedent).
- **EC-7 — asset_level_stats `transcript` / `asset_link` dimensions.** `asset_level_stats` carries `transcript` + `asset_link` (`library.py:565-583`); these are **ad-creative** attributes (the insight is "creative performance"), not patient transcripts; already cleared by the existing allowlist entry. The asana ASSET TABLE additionally strips `transcript` at display (`tables.py:237-248`). No new PII exposure from the rewire.

---

## 7. Open operator questions (the genuine product calls)

- **★ OQ-1 (the verdict's hinge — sharpest):** Do TNHC agency staff today run **cross-office per-patient or financial OPERATIONAL workflows** off this export (e.g., agency-wide no-show recovery from APPOINTMENTS, lead-source auditing from LEADS, agency billing from RECONCILIATION) as a **core agency function** — or is the agency's use of this export **aggregate-analytical** (comparing office/offer/asset/campaign performance)? **If aggregate-analytical → Option-1 confirmed (this PRD stands). If a live cross-office operational function → refute to Option-4** (re-open the PII wall under OD-5 + per-agency BAA/consent + narrowed scope + audit — a separate, heavier initiative).
- **OQ-2 (equivalence — envelope):** Is the operator route's `BatchInsightResponse` output an acceptable substitute for the current factory-frame `InsightsResponse` output for each of the 8 tables? (The underlying computation is the same registry/engine; this confirms the report content is acceptable.)
- **OQ-3 (equivalence — BY-period):** Should BY QUARTER/MONTH/WEEK be served by `account_level_stats` (period filter), `business_summary` (date dimension, already allowlisted), or a period-breakdown mode? This determines whether 3 of the 8 tables are trivially rewired or need a data-plane affordance.
- **OQ-4 (equivalence — include_unused):** Does/should the operator `execute-batch` honor `include_unused` so UNUSED ASSETS is servable? If not, drop UNUSED ASSETS from the agency deck or add the filter.
- **OQ-5 / OD-5 (financial):** Is the `hosted_invoice_url`/`customer_id`/`invoice_number` exposure of `reconciliation` ever acceptable on a cross-tenant plane? Until OD-5 ratifies + data owner signs off, reconciliation stays excluded (W1).
- **OQ-6 (PII disposition mechanism):** For any excluded PII table with a confirmed per-office operational need (gated on OQ-1), what is the per-office-scoped mechanism — keep the office's existing per-office report, or build a per-office-token path? (Explicitly NOT the SA fleet-read; that re-asserts DATA-VAL-003.)

---

## 8. Structural-Verification-Receipt (SVR) ledger

All receipts are `file-read` against the pinned trees (asana `e7d71fa8`, data `3169fa96`). Verified at authorship.

| # | Claim | source (`git show <tree>:<path>`) | line | marker_token (verbatim) |
|---|-------|-----------------------------------|------|--------------------------|
| R1 | 12 TableSpecs across 4 dispatch types | asana `e7d71fa8`:tables.py | 124-266 | `TABLE_SPECS: list[TableSpec] = [` |
| R2 | dispatcher matches 4 dispatch types | asana:workflow.py | 617-667 | `match spec.dispatch_type:` |
| R3 | factory→frame_type map (base→unit, assets→asset, business_offers→offer, ad_questions→question) | asana:client.py | 659-674 | `"base": "unit",` |
| R4 | export INSIGHTS path resolves frame_type from the map | asana:_endpoints/insights.py | 182,189 | `frame_type = client.FACTORY_TO_FRAME_TYPE[factory]` |
| R5 | frame_type→registered insight, derived from InsightRegistry | data `3169fa96`:frame_type_mapper.py | 78-105 | `"unit": "account_level_stats",` |
| R6 | C-1 allowlist = exactly the 3 de-identified names | data:operator_insights.py | 172-178 | `_OPERATOR_INSIGHT_ALLOWLIST: frozenset[str] = frozenset(` |
| R7 | reconciliation deliberately C-1 EXCLUDED (financial PII) | data:operator_insights.py | 165-171 | `# C-1 EXCLUSION — `reconciliation` is DELIBERATELY NOT seeded.` |
| R8 | non-allowlisted insight → bare 404 before DB resolution | data:operator_insights.py | 353-354 | `if body.insight_name not in _OPERATOR_INSIGHT_ALLOWLIST:` |
| R9 | account_level_stats is a registered de-id insight (office grain) | data:library.py | 407,455 | `dimensions=["office_phone", "office", "vertical"],` |
| R10 | asset_level_stats registered; transcript/asset_link are creative dims | data:library.py | 522,565-583 | `name="asset_level_stats",` |
| R11 | offer_level_stats registered de-id aggregate (offer grain) | data:library.py | 1295,1317-1328 | `name="offer_level_stats",` |
| R12 | question_level_stats registered de-id aggregate (question grain) | data:library.py | 1483,1508-1520 | `name="question_level_stats",` |
| R13 | business_summary is the date-grained (time-series) insight | data:library.py | 367-371 | `dimensions=["date"],` |
| R14 | APPOINTMENTS is row-level, filtered by lead phone (per-patient) | asana:simple.py:143 / data:appointments_read.py:71 | — | `description="Filter by lead phone (E.164 format)",` |
| R15 | LEADS is per-lead by phone | asana:simple.py:248 / data:leads_read.py:6,83 | — | `GET /api/v1/leads/{phone} - Get a lead by phone` |
| R16 | RECONCILIATION sums financial amounts | data:processors/reconciliation.py | 65 | `COALESCE(SUM(p.amount) / 100.0, 0) AS total_dollars,` |
| R17 | operator route serves via BatchInsightExecutor (no new insight needed) | data:operator_insights.py | 430-432 | `executor = BatchInsightExecutor(engine=engine)` |
| R18 | owned-set bounded, all-or-nothing (not a fleet-read) | data:operator_insights.py | 384-408 | `if not result.all_authorized:` |

---

## 9. Requirements traceability

| Requirement | Source | Type |
|---|---|---|
| 8/4 triage | source-read (R1-R16) | constraint (PII design) |
| Option-1 default scope | telos + C-1 design invariant (R6,R7,T-1..T-5) | stakeholder telos |
| +2 allowlist names | factory→insight refinement (R3,R5,R6,R11,R12) | derived (shrinks GAP-1b) |
| PII exclusion ≠ keep-SA | DATA-VAL-003 + GAP-1 telos | constraint |
| Equivalence sign-offs (OQ-2/3/4) | InsightsResponse vs BatchInsightResponse (R5,R17) | product decision |
| OD-5 reconciliation hold | R7 | operator-reserved |

---

## 10. Handoff, impact, attestation

**Impact: high** — categories `security` (C-1 PII wall, allowlist additions), `auth` (operator token / OperatorClaims path), `api_contract` (operator route allowlist surface + asana client rewire), `cross_service` (asana ↔ data ↔ auth). Routes to Architect (GAP-1b data-plane extension TDD) + Security (ADR-0040) even though no schema change.

**Handoff state:**
- Architect: the operator-plane extension is bounded to **+2 allowlist names + equivalence resolution (OQ-2/3/4) + the 8-arm asana rewire onto the GAP-1a substrate** — NOT a build-new-insights effort. The BY-period and include_unused affordances (OQ-3/OQ-4) are the only candidate data-plane code beyond the allowlist edit.
- Security: ADR-0040 gate INVOKED for the 2 allowlist additions (de-identified-classification ratification). Reconciliation stays excluded (OD-5).
- Operator: **OQ-1 is decision-blocking for the verdict** (confirms Option-1 or refutes to Option-4); OQ-2..OQ-6 are FLIP-gating, not merge-gating.
- Counter unaffected (RED until operator FLIP). This PRD mutated no code.

**Attestation:**

| Artifact | Absolute path | Verified |
|---|---|---|
| This PRD | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PRD-gap1-export-scope-relitigation-2026-06-28.md` | Write + Read-back |
| Upstream TDD | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/TDD-gap1-asana-operator-rewire-2026-06-28.md` | Read (on-disk) |

*Reads pinned: asana `e7d71fa8`, data `3169fa96`, auth `3df3298a`. No code mutated; `.claude` / `.gemini` / `.know` not staged.*
