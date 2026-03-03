# Spike: Asana Offer ↔ Meta Ads Cross-Check

**Date:** 2026-03-02
**Objective:** Design a reconciliation model that joins Asana offer status (source-of-truth contract) with Meta ad account status (actual execution) to detect misalignment in both directions.

---

## 1. Data Model Summary

### Meta Side (autom8y-ads / e2e_full_tree.json)

| Level | Key Fields | Join Key Encoded In Name |
|-------|-----------|--------------------------|
| **Campaign** | id, status, daily_budget_cents, raw_name | `office_phone•business_name•vertical_key•objective•optimized_for•algo_version•controls_budget` |
| **Ad Group** | id, status, campaign_id, raw_name | `offer_id•office_phone•targeting•opt_goal•gender•age•lang•dynamic•assets•questions` |
| **Ad** | id, status, ad_group_id, raw_name | `asset_id•form_questions•creative_id` |

Ad group names encode `offer_id` as field[0] — a short numeric ID (e.g., `1548`, `1536`) matching the Asana `cf:Offer ID` custom field.

### Asana Side (autom8y-asana / offer entity)

All join keys are DataFrame columns on the offer entity:

| Field | Source | In DataFrame | Notes |
|-------|--------|:---:|-------|
| `office_phone` | `cascade:Office Phone` | Yes | Primary join key to both campaign and ad group names |
| `vertical` | `cascade:Vertical` | Yes | Maps to `vertical_key` in campaign names |
| `offer_id` | `cf:Offer ID` | Yes | Short numeric ID (e.g., `1548`), maps to ad group name field[0] |
| `weekly_ad_spend` | `cascade:Weekly Ad Spend` | Yes | Dollars, cascaded from Unit level |
| `section` | Native | Yes | Current workflow state (20 active sections) |
| `gid` | Native | Yes | Asana task GID (NOT the same as offer_id) |
| `campaign_id` | `cf:Campaign ID` | No | Exists on model but not in DataFrame schema |
| `ad_set_id` | `cf:Ad Set ID` | No | Exists on model but not in DataFrame schema |

---

## 2. Join Strategy

The join is driven from the **Asana offer side** outward, using offer DataFrame columns as the left side of each join.

### Join A — Campaign level: `(office_phone, vertical)`

```
offer.(office_phone, vertical)  →  campaign.(office_phone, vertical_key)
```
- Both fields extracted from campaign `raw_name` via `CAMPAIGN_NAME.decode()`
- One offer may match 1-2 campaigns (VOLUME + QUALITY optimization variants)
- Budget reconciliation: SUM daily budgets across matched campaigns
- This is the **status alignment** join (is this offer's campaign running?)

### Join B — Ad Set level: `(office_phone, offer_id)`

```
offer.(office_phone, offer_id)  →  ad_group.(office_phone, offer_id)
```
- Both fields extracted from ad group `raw_name` via `AD_GROUP_NAME.decode()`
- `offer_id` is field[0], `office_phone` is field[1] in ad group names
- More precise than campaign join — links directly to the ad sets serving this specific offer
- This is the **delivery health** join (are there ad sets and ads actually running for this offer?)

### Relationship

```
Asana Offer ──(phone,vertical)──► Meta Campaign(s)    [1:N, N=1-2 via VOLUME/QUALITY]
             ──(phone,offer_id)──► Meta Ad Set(s)      [1:N, N=1-15 per offer]
                                      └──► Meta Ad(s)  [1:1 with ad set currently]
```

One offer fans out to campaigns (via vertical) and drills into ad sets (via offer_id). The phone anchors both joins.

---

## 3. Cross-Check Dimensions

### A. Status Alignment (2-way street)

| Asana Classification | Meta Campaign Status | Verdict | Action |
|---------------------|---------------------|---------|--------|
| `active` | Active + has ad sets | **ALIGNED** | None |
| `active` | Active + 0 ad sets (hollow) | **DELIVERY_GAP** | Campaign spending budget but not delivering ads |
| `active` | Inactive or missing | **MISSING_CAMPAIGN** | Contracted service not running |
| `activating` | Any | **TRANSITIONAL** | Expected gap, no action |
| `inactive`/`ignored` | Active | **GHOST_CAMPAIGN** | Spending money without active contract |
| `inactive`/`ignored` | Inactive | **ALIGNED** | None |

### B. Budget Alignment

**Formula:**
```
meta_weekly = SUM(daily_budget_cents for campaigns matching (phone, vertical)) * 7 / 100
asana_weekly = offer.weekly_ad_spend
variance_pct = abs(meta_weekly - asana_weekly) / asana_weekly * 100
```

**Tolerance bands:**
- `MATCHED`: variance < 5%
- `DRIFT`: 5% ≤ variance < 20%
- `MISMATCH`: variance ≥ 20%

**Complication:** `weekly_ad_spend` cascades from the Unit level, shared across sibling offers. Dedup by `(office_phone, vertical)` pair is needed (same pattern as `calc_weekly_ad_spend.py`).

### C. Delivery Health

| Condition | Flag |
|-----------|------|
| Campaign active, 0 ad sets | `HOLLOW` — budget allocated, no delivery |
| Campaign active, ad sets active, 0 ads | `BARREN` — ad sets exist but no creative |
| All levels active and populated | `HEALTHY` |

---

## 4. Vertical Mapping

Campaign names use `vertical_key` (e.g., `chiropractic`, `spinal_decomp`, `integ_therapy`).
Asana offers use the `Vertical` enum field.

**Need to verify:** Are these the same string values, or is there a mapping layer? The existing `CampaignSearchService` in autom8y-ads uses `vertical_key` directly from `CampaignNameFields` and matches it against the offer vertical — suggesting they use the same vocabulary.

---

## 5. Implementation Sketch

### Phase 1: Join Script (spike/PoC)

A standalone Python script that:
1. Reads `e2e_full_tree.json` (Meta side)
2. Queries Asana offers via CLI: `python -m autom8_asana.query rows offer --classification active --select gid,name,office_phone,vertical,offer_id,weekly_ad_spend,section --format json`
3. Builds two-level reconciliation report

```python
# Pseudocode — build Meta indexes keyed the same way offers are

# Campaign index: (phone, vertical) → aggregated campaign data
meta_campaigns = defaultdict(lambda: {"campaigns": [], "total_daily_cents": 0})
for campaign in active_campaigns:
    fields = CAMPAIGN_NAME.decode(campaign.raw_name)
    key = (fields.office_phone, fields.vertical_key)
    meta_campaigns[key]["campaigns"].append(campaign)
    meta_campaigns[key]["total_daily_cents"] += campaign.daily_budget_cents or 0

# Ad set index: (phone, offer_id) → ad sets and their ads
meta_adsets = defaultdict(lambda: {"adsets": [], "ad_count": 0})
for tree_entry in active_tree:
    for child in tree_entry.get("children", []):
        ag_fields = AD_GROUP_NAME.decode(child["ad_group"]["raw_name"])
        key = (ag_fields.office_phone, ag_fields.offer_id)
        meta_adsets[key]["adsets"].append(child["ad_group"])
        meta_adsets[key]["ad_count"] += len(child.get("ads", []))

# Reconcile from Asana offer outward
for offer in active_offers:
    campaign_key = (offer["office_phone"], offer["vertical"])
    adset_key = (offer["office_phone"], offer["offer_id"])

    camp = meta_campaigns.get(campaign_key)
    adset = meta_adsets.get(adset_key)

    # Status check
    if not camp:
        verdict = "MISSING_CAMPAIGN"
    elif not adset or adset["ad_count"] == 0:
        verdict = "DELIVERY_GAP"
    else:
        verdict = "ALIGNED"

    # Budget check (campaign level)
    if camp:
        meta_weekly = camp["total_daily_cents"] * 7 / 100
        asana_weekly = offer["weekly_ad_spend"] or 0
        budget_verdict = check_budget_variance(meta_weekly, asana_weekly)

# Also check for ghost campaigns (Meta active, no matching Asana offer)
for key, camp in meta_campaigns.items():
    if key not in asana_by_phone_vert:
        verdict = "GHOST_CAMPAIGN"  # spending without contract
```

### Phase 2: Productionize

Options (increasing investment):
1. **Script in autom8y-asana** — `scripts/ads_crosscheck.py`, reads both data sources, outputs report
2. **Cross-service query** — New `data-service` factory that fetches Meta tree via autom8y-ads API, joins at query time
3. **Scheduled reconciliation** — Cron job producing alerts for GHOST/MISSING/MISMATCH verdicts

---

## 6. Data Access Paths

### Getting Meta data
- **File:** `e2e_full_tree.json` (snapshot, from `scripts/e2e_tree_fetch.py`)
- **API:** `GET /api/v1/accounts/{account_id}/campaigns/active/tree` (live)
- **Key:** All campaigns in flat list (`all_campaigns`), tree with ad groups/ads (`active_tree`)

### Getting Asana data
- **CLI:** `python -m autom8_asana.query rows offer --classification active --select gid,name,office_phone,vertical,weekly_ad_spend,section --format json`
- **Saved query:** Could create `queries/active_offers_for_ads_crosscheck.yaml`
- **Programmatic:** `OfflineDataFrameProvider` + `QueryEngine`

### Vertical string validation needed
Before building the join, verify that `vertical_key` in campaign names matches the Asana `Vertical` enum values exactly. Quick check:
- Meta verticals seen: `chiropractic, spinal_decomp, integ_therapy, phys_therapy, knee_pain, weight_loss, mens_health, neurodiversity, softwave, naturopathy, 8ww, neuropathy, iv_therapy`
- Asana verticals: need to query `python -m autom8_asana.query rows offer --select vertical --classification active` and compare

---

## 7. Open Questions

1. **Vertical mapping**: Are Meta campaign `vertical_key` values identical to Asana `Vertical` enum values?
2. **Multi-campaign offers**: Some offers have both VOLUME + QUALITY campaigns. Should budget reconciliation sum both or treat them separately?
3. **Cascade dedup**: `weekly_ad_spend` cascades from Unit. Multiple offers under the same Unit share the same value. How do we handle? (Answer: dedup by `(office_phone, vertical)` — same as existing `calc_weekly_ad_spend.py` pattern)
4. **Inactive campaign with budget**: Should we flag campaigns that are inactive but still have non-zero budget configured?
5. **Where does the script live?** `autom8y-asana` (has query engine) or `autom8y-ads` (has tree data), or a new cross-service script?
6. **Hollow campaign root cause**: The 36 hollow campaigns ($2,269.40/day at risk) — are these intentionally paused ad sets, or a system bug in the launch pipeline?

---

## 8. Quick Win: Immediate Value

Even before building the full reconciliation, the data from the user's report already reveals:

- **36 hollow campaigns** = $2,269.40/day of budget allocated but zero delivery
- **110 active campaigns** across **13 verticals** vs however many active Asana offers exist
- Phone numbers in campaign names are the canonical join key

A quick script joining these two datasets would immediately surface:
- Ghost campaigns (Meta active, Asana inactive) — money being spent without contract
- Missing campaigns (Asana active, Meta inactive) — contracted service not being delivered
- Budget drift — actual Meta spend ≠ contracted Asana weekly_ad_spend / 7
