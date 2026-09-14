# READ — Offer-grain activity of `ccb52f4c` and the 26 gate-refused offices (sizing S-1)

**Seat:** calendar-integration-locus subagent · **Date:** 2026-09-11 · **Mode:** READ-ONLY (no repo file touched, no commit, no push)
**Charge:** R-142 of sitting IX + its §6 addendum (INHERITED from the charge; the sitting-IX text is not on disk in `.ledge/` or `.sos/wip/` — `grep -rln 'R-142'` → 0 files).
**Question:** at the OFFER grain in Asana, is each of these offices live, activating, or dark? `is_paying` NOT used (autom8y-data `origin/main 005bb231` `.know/business-context.md:363` "is_paying Is NOT a Clean Fallback", `:454` "is_paying Empirical Inversion (100% Mislabel Confirmed)").

Labels: **VERIFIED** = taken with own hands this session at a named ref/live call · **INHERITED** = carried from a named artifact, not re-taken · **NOT TAKEN** = not done, with the reason.

---

## 0. BLUF

- **`ccb52f4c` is a live, served-set client at the offer grain.** Its Business task holds 6 Offer tasks; one sits in section `ACTIVE` (class `active`), one in `AWAITING REP UPDATE`, four in `INACTIVE`. `max_offer_activity` = **active**. The `ACTIVE` offer carries MRR 600 (the served definition is section-gated `ACTIVE` ∧ `mrr>0`; note MRR is populated on its INACTIVE rows too, so MRR alone discriminates nothing — the section does). **406 mails / 2 bookings is happening to a paying-class client.** VERIFIED.
- **Of the 26 class-C refused offices (all offer rows `disabled IS NULL` pre-flip): 11 `active` + 1 `activating` = 12 live/activating (46%); 12 `inactive` (dark); 2 `ignored` (Business in `OPPORTUNITY`, Offer in `Sales Process` — prospects that never launched).** VERIFIED via the cascade-phone path (see §3 on what the ADR rules).
- The single largest refused offender (rank 1, `c2ab6637`, 508 declines) is **dark** (`INACTIVE` ×2). The second largest (rank 2, `d167d635`, 448 declines, 300 booked anyway) is **active** and is itself one of the CONSULT's "arrivals AND bookings today" offices.
- Positive controls fired on the identical call shape: `4ec260bf` → active, `d167d635` → active, census Tier-H `8e56f6e1` / `ca70baa8` → active; negative `00000000` → absent. **One CONSULT-named positive did NOT fire: `15caa02c` → `inactive`** (its only Offer is in `INACTIVE`); I report it, I do not adjudicate it (§5).
- **The independent parent-chain cross-check landed after first writing (21:30Z, 6,353 GET calls):** walking Business → Unit subtasks → holder → Offer subtasks (`unit.py:317`) gives the **same class for every one of the 5 targets, all 3 auto-picked positive controls, and all 25 single-hit SPLIT rows (25/25)**. Where the two paths differ at all (7 rows + `ccb52f4c`), the hierarchy sees extra `Sales Process` (ignored) offers that carry no cascaded phone — never a class change. VERIFIED.
- `Business.max_offer_activity` is **not on origin/main** (PR #431 OPEN, `mergedAt: null`); the class per office below is a local analogue: highest-priority class across the office's Offer tasks under `ACTIVITY_PRIORITY` (ACTIVE > ACTIVATING > INACTIVE > IGNORED), the ordering `max_unit_activity` documents at `activity.py:20-27`. INHERITED semantics, VERIFIED computation.

---

## 1. Vocabulary and refs (VERIFIED)

| Item | Value | Ref |
|---|---|---|
| autom8y-asana `origin/main` | `6430cec5` (fetched; `git ls-remote` agrees) | own hands |
| `OFFER_CLASSIFIER` | `src/autom8_asana/models/business/activity.py:181-210`, project `1143843662099250`; active = {OPTIMIZE - Human Review, STAGING, STAGED, ACTIVE, MANUAL}; activating = {ACTIVATING, IMPLEMENTING, NEW LAUNCH REVIEW}; inactive = {ACCOUNT ERROR, AWAITING REP UPDATE, INACTIVE}; ignored = {Sales Process, Complete, Plays/PLAYS, Performance Concerns} | `git show origin/main:…/activity.py` |
| Working-tree classifier == origin/main | `git diff --stat origin/main -- …/activity.py` → empty | own hands |
| `max_offer_activity` on origin/main | **absent** (`grep` finds only `max_unit_activity` at `business.py:448`); PR #431 `state: OPEN` | `gh pr view 431` |
| Join of record (guid ↔ Asana) | `Company ID` field on the **Business** task == `chiropractor_guid` — `forwarding_stage_backfill/config.py:118` "chiropractor_guid == the Company-ID field value (T-B6 join precondition)"; `business.py:311` `COMPANY_ID = CascadingFieldDef(name="Company ID")` | origin/main |
| Business project | `1200653012566782` (`business.py:144`, class `Business`) — **not** `1167650840134033` (`business.py:58`, `DNAHolder`; see §5 trap) | origin/main |
| Unit / Offer projects | `1201081073731555` / `1143843662099250` | `unit.py:85`, `offer.py:87` |
| Credential convention | `ASANA_PAT` from env (`_defaults/auth.py:27-60` `EnvAuthProvider`); `secretspec.toml:45` declares it | origin/main |
| autom8y `origin/main` (census) | `2ce7515c`; `scripts/ebi_witness_ledger.py:150-176` `_TIER_H`/`_TIER_S`/`_TW_EXCLUDED` prefixes | own hands |

---

## 2. The table

Columns: **guid8** · **class** = local `max_offer_activity` analogue over the office's Offer tasks · **source+ref** · **refusal history pre-flip** (INHERITED from `.sos/wip/SPLIT-not-enrolled-and-null-shadow-2026-09-10.md` §2.2/§4/§5: declines over 90d EBI window, DB offer-row class, "booked anyway") · **note**. Every Offer task listed has `completed=false`. "Biz §" = the Business task's own section in `1200653012566782`.

Source key: **[P]** = resolved by `Company ID` prefix (the ADR's key of record) · **[Φ]** = reached through the Business task's own cascaded `Office Phone` field (ADR ws-join §1.2 **J1** second leg, `get_business_by_phone_async`) and then the prefix read off its `Company ID` — SUPPLEMENTARY under the ADR, see §3. All reads: live Asana REST GET, 2026-09-11 ~20:5x–21:0xZ, classified with the repo classifier.

### 2.1 The subject

| guid8 | class | source + ref | refusal history pre-flip | note |
|---|---|---|---|---|
| `ccb52f4c` | **active** | [P] Biz § `BUSINESSES`; 6 offers: `AWAITING REP UPDATE`, **`ACTIVE`**, `INACTIVE`×4 → classes inactive, **active**, inactive×4 | **not in the SPLIT's 29** (never gate-refused in the 90d window on the SPLIT's evidence); CONSULT-morning-after-north §4 L251-276: 406 mails / 329 no_appt_dt / 2 bookings over 8 days (INHERITED) | ACTIVE offer MRR = 600 (served-set: ACTIVE ∧ mrr>0). In the seat's allowlist (scratchpad `allowlist.txt`); not in the census tiers. Hierarchy walk: 8 offers (the 6 above + 2 `Sales Process`/ignored without a cascaded phone) → still **active**; Units: `Month 1` (active), `Unengaged` ×2. |

### 2.2 The 26 class-C refused offices (all offer rows `disabled IS NULL` pre-flip)

| # | guid8 | class | source + ref | refusal history pre-flip (declines · DB rows · booked anyway) | note |
|---|---|---|---|---|---|
| 1 | `c2ab6637` | **inactive** | [P] (SPLIT names the guid) Biz § `BUSINESSES`; `INACTIVE`×2 | 508 (rank 1) · 3 rows all NULL · 75 booked, 186 wrote-nowhere | Largest offender is **dark**. guid8 agrees SPLIT↔Company ID. |
| 2 | `d167d635` | **active** | [Φ] Biz § `BUSINESSES`; `AWAITING REP UPDATE`, **`ACTIVE`** | 448 (rank 2, "unnamed" in SPLIT) · 2 rows NULL · 300 booked | Census Tier-H. Also a CONSULT positive control — fired. |
| 3 | `8e56f6e1` | **active** | [P] Biz § `BUSINESSES`; `AWAITING REP UPDATE`, **`ACTIVE`** | 181 (rank 3) · 2 NULL · 102 booked | Census Tier-H. guid8 agrees. |
| 4 | `87bd31d7` | **inactive** | [P] Biz § `BUSINESSES`; `INACTIVE`×3 | 136 (rank 4) · 6 NULL · 15 booked | Dark. guid8 agrees. |
| 5 | `6b93fb76` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE`×2 | 123 (rank 5) · 2 NULL · 10 booked | Dark. |
| 6 | `933a026c` | **ignored** | [Φ] Biz § `OPPORTUNITY`; offer in `Sales Process` | 110 (rank 6) · 3 NULL · 13 booked | Prospect never launched; not a client under the offer vocabulary. |
| 7 | `53295a22` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE`×2 | 109 (rank 7) · 5 NULL · 11 booked | Dark. |
| 8 | `ca70baa8` | **active** | [P] Biz § `BUSINESSES`; **`ACTIVE`** | 109 (rank 8) · 1 NULL · 75 booked | Census Tier-H. guid8 agrees. |
| 9 | `ed88a4a9` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE`×3 | 69 (rank 9) · 3 NULL · 11 booked | Dark. |
| 10 | `783b40aa` | **active** | [Φ] Biz § `BUSINESSES`; **`ACTIVE`** | 58 (rank 10) · 3 NULL · 40 booked | Census Tier-H. |
| 12 | `06a9afb0` | **active** | [Φ] Biz § `IMPLEMENTING`; offer **`ACTIVE`** | 52 (rank 12) · 2 NULL · **0 booked** | Live client that never recovered a booking. |
| 13 | `4ad24874` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 45 (rank 13) · 1 NULL · 5 booked | Dark. |
| 14 | `7363c7ea` | **active** | [Φ] TWO Business tasks share the phone and the same `Company ID` (§ `OPPORTUNITY` + § `BUSINESSES`); offers **`ACTIVE`** + `Sales Process` | 41 (rank 14) · 1 NULL · 24 booked | Census `_TW_EXCLUDED`. Duplicate Business task, same guid — not a collision. |
| 15 | `4416989f` | **active** | [Φ] Biz § `BUSINESSES`; **`ACTIVE`** | 40 (rank 15) · 2 NULL · 29 booked | Census Tier-H, H-fragile. |
| 16 | `800f9fe1` | **active** | [Φ] Biz § `BUSINESSES`; **`ACTIVE`** | 34 (rank 16) · 1 NULL · 23 booked | Census Tier-H. |
| 17 | `cf6ae0f2` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 34 (rank 17) · 1 NULL · 7 booked | Dark. |
| 19 | `b167331c` | **active** | [Φ] Biz § `IMPLEMENTING`; offer **`ACTIVE`** | 25 (rank 19) · 1 NULL · 17 booked | Census Tier-H, H-fragile. |
| 20 | `9fcf1507` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 19 (rank 20) · 1 NULL · 0 booked | Dark. |
| 21 | `949bc690` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 19 (rank 21) · 2 NULL · 3 booked | Dark. |
| 22 | `e715d36c` | **active** | [Φ] TWO Business tasks, same `Company ID`; offers **`ACTIVE`** + `Sales Process` | 15 (rank 22) · 1 NULL · 10 booked | Census Tier-S. Duplicate task, not a collision. |
| 23 | `a146f353` | **activating** | [Φ] Biz § `IMPLEMENTING`; offer `NEW LAUNCH REVIEW` | 12 (rank 23) · 1 NULL · 0 booked | The one activating office. |
| 24 | `1c20d27c` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 9 (rank 24) · 3 NULL · 0 booked | Dark. |
| 25 | `51144b61` | **ignored** | [Φ] Biz § `OPPORTUNITY`; offer `Sales Process` | 9 (rank 25) · 1 NULL · 0 booked | Prospect never launched. |
| 26 | `e3267756` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 7 (rank 26) · 1 NULL · 0 booked | Dark. |
| 27 | `7beec6b3` | **active** | [Φ] Biz § `BUSINESSES`; **`ACTIVE`** + `INACTIVE` | 2 (rank 27) · 2 rows (1 NULL / 1 disabled) · 2 booked | Census Tier-S. |
| 28 | `a60abc74` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 2 (rank 28) · 1 NULL · 0 booked | Dark. |

### 2.3 The 3 refused offices outside class C (for completeness; not part of "the 26")

| # | guid8 | class | source + ref | refusal history pre-flip | note |
|---|---|---|---|---|---|
| 11 | `40f86e73` | **inactive** | [Φ] Biz § `BUSINESSES`; `INACTIVE` | 54 · class **D** (1 row `disabled=1`, the fallback's own defect) · 40 booked | Census **Tier-H** yet offer-dark and deliberately disabled — worth a look by whoever owns the census. |
| 18 | — | **unjoinable under the ADR** | no guid on record; no Business task in `1200653012566782` carries this Office Phone | 33 · class **A** (0 offer rows) · 0 booked | Absent from Asana by both keys. |
| 29 | — | **unjoinable under the ADR** | as above | 2 · class **A** · 0 booked | Absent from Asana by both keys. |

### 2.4 Tallies

| Population | active | activating | inactive (dark) | ignored (never launched) | unjoinable |
|---|---|---|---|---|---|
| `ccb52f4c` | **1** | 0 | 0 | 0 | 0 |
| 26 class-C refused | **11** | **1** | **12** | **2** | 0 |
| 3 non-C refused | 0 | 0 | 1 | 0 | 2 |
| **All 27 in the charge (ccb52f4c + 26)** | **12** | **1** | **12** | **2** | 0 |

So **13 of 27 are live-or-activating at the offer grain**; 12 are dark; 2 are prospects. Declines are NOT concentrated on the dark side: the 12 live/activating class-C offices absorbed 448+181+109+58+52+41+40+34+25+15+12+2 = **1,017** of the 2,216 class-C declines (46%); the dark 12 absorbed 508+136+123+109+69+45+34+19+19+9+7+2 = **1,080** (49%); the 2 prospects 119 (5%). Census offices (Tier-H/S/TW) account for **10 of the 29** refused clinics.

**Cross-check (landed 21:30Z):** the subtask-hierarchy walk reproduces the class in every row it could resolve — 5/5 targets, 25/25 single-hit SPLIT rows (rows 14 and 22 are two-task duplicates the walk script skipped by its `exactly-one-hit` rule; their phone-path class stands), 3/3 positive controls. Offer sets were identical in 18/25 rows; in the other 7 (ranks 2, 12, 15, 16, 19, 20, 27) the walk found 2 additional `Sales Process` offers each, all `ignored`, none altering the max class.

---

## 3. What the ADR rules, and how each row was reached

`.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md` at asana `origin/main 6430cec5` (VERIFIED): §0 — the join "exists in three places already"; §1.2 J1 = data service `get_business_by_guid_async(guid)` **and** `get_business_by_phone_async(office_phone)`; §1.3/§7.1 — the ruled seam is **prefix → full guid through an injectivity-asserted registry derived from the denominator, then guid → name**; §9 — the `redact_uuid` 8-hex prefix is "ratified as the join key of record"; §4 Option H **REFUSED** = "put `office_phone` on the plane as the join key".

- **[P] rows** (`ccb52f4c`, `c2ab6637`, `8e56f6e1`, `87bd31d7`, `ca70baa8`, controls): the ADR's key. Registry = every uuid-shaped `Company ID` in the Business project (931 of 999 non-empty; 898 distinct prefixes; **0 prefix collisions** → injectivity holds on this superset, hence on any denominator subset). Each prefix resolved to exactly one Business task (or two tasks carrying the identical full guid — a duplicate task, not a collision; flagged in rows 14, 22).
- **[Φ] rows** (the 21 "unnamed" SPLIT rows): the SPLIT carries **no guid** for them, only a phone, so the ADR's key cannot be applied to the record as it stands — strictly, **they are unjoinable under the ADR's key of record from the SPLIT alone**. What I did instead is the ADR's own J1 second leg (phone → Business) executed against Asana's `Office Phone` cascading field (`business.py:305` `OFFICE_PHONE = CascadingFieldDef(name="Office Phone")`, FR-CASCADE-002), then read the guid8 off that Business's `Company ID` — after which the prefix key applies. This carries no phone onto any plane, widens no log line, and touches nothing the ADR fences; it is a read-only lookup, not a join written anywhere. **It is nevertheless not the ruled key, and the seat should treat those 21 rows as SUPPLEMENTARY** until the prefix→guid registry (WS-DENOM / RegistryPort) names them. Control on the hop: for the 4 SPLIT rows that DO name a guid, the phone-resolved Business's `Company ID` prefix **agreed with the SPLIT's guid 4/4**.
- Offer ↔ Business linkage used for classification: Offer tasks carry the cascaded `Office Phone` (2,901 of 4,193 Offer tasks have one; `Company ID` is **empty on all 4,193 Offer tasks**, so the guid lives only on the Business task). Offers were attached to their Business by equality of the cascaded phone. Shared phones: 66 phone values are held by >1 Business task in the project (rows 14 and 22 are two of them and resolve to the same guid). The parent-chain (subtask hierarchy, `unit.py:317 _populate_holders`) cross-check **TAKEN** (landed 21:30Z): it agrees on class for every resolved row; the only differences are extra phone-less `Sales Process` offers visible to the walk (§2.4, §5).

---

## 4. Is `ccb52f4c` a paying-class client under the offer vocabulary?

**Yes, on the offer vocabulary's own terms.** The vocabulary's billable set is `classify(section) ∈ {active, activating}` (`lambda_handlers/traffic_offer_divergence_tripwire.py:452-458`, `OFFER_CLASSIFIER.billable_sections()`), and the served number (`active_mrr`, per the seat's memory of pythia's referent ruling) is ACTIVE-section offers with `mrr>0`. `ccb52f4c` has an Offer task in `ACTIVE` with MRR 600. Two honest caveats: (i) MRR is populated on its `INACTIVE` and `AWAITING REP UPDATE` rows too (600 each), and on **every** offer of every office I resolved, dark ones included — so MRR>0 is a price tag, not a payment receipt; only the section carries the live/dark signal; (ii) Asana sections are human-moved and I did not test their freshness (§6). Under the naive `is_paying` this office would have read as not-paying; that field is a documented 100% mislabel and was not consulted.

---

## 5. Controls (VERIFIED) — the zeros were never taken bare

| Control | Call shape | Result |
|---|---|---|
| Positive, CONSULT-named ("arrivals AND bookings today") | identical `by_prefix()` resolver | `4ec260bf` → **active** (7 offers: ACTIVE×2, INACTIVE×5) ✔ · `d167d635` → **active** ✔ · **`15caa02c` → `inactive`** (1 offer, `INACTIVE`) ✘ — resolved fine, classified dark. Either its bookings ride a path the Offer project doesn't reflect, or its section is stale. Reported, not adjudicated. |
| Positive, census Tier-H "activated" | same | `8e56f6e1` → active ✔ · `ca70baa8` → active ✔ |
| Positive, join-hop agreement | phone-resolved `Company ID` prefix vs SPLIT's own guid | 4/4 agree (`c2ab6637`, `8e56f6e1`, `87bd31d7`, `ca70baa8`) |
| Negative | same resolver, prefix `00000000` | `absent-in-asana` ✔ |
| Classifier, population level | every Offer task in `1143843662099250` (4,193) | sections: ACTIVE 50 · OPTIMIZE-Human Review 3 · ACTIVATING 22 · IMPLEMENTING 21 · NEW LAUNCH REVIEW 6 · AWAITING REP UPDATE 8 · INACTIVE 1,075 · Sales Process 2,801 · COMPLETE 169 · PLAYS 38 → classes active 53 · activating 49 · inactive 1,083 · ignored 3,008 · **unclassified 0** (every live section name is in the vocabulary) |
| Classifier, unit level | `OFFER_CLASSIFIER.classify(...)` | `'ACTIVATING'`→activating, `'ACTIVE'`→active, `'nonsense-section'`→`None` |
| MRR field populated on actives | 50 ACTIVE-section offers | 50/50 `mrr>0`, 0 blank |
| Independent join path (subtask hierarchy vs cascade-phone) | `offer_activity_read2.py`: Business → subtasks depth 3, Offer-project members classified; 6,353 GETs | 5/5 targets same class; 3/3 auto-picked positives (an `ACTIVE`-, an `ACTIVATING`-, an `ACTIVE`-section offer's Business) → active / activating / active on **both** paths; negative `00000000` absent; 25/25 SPLIT rows same class (18/25 identical offer sets; 7 differ only by 2 phone-less `Sales Process` offers each) |
| Token / project reachability | `curl … /users/me` and `/projects/1143843662099250` (status only) | http=200, http=200 |
| **Trap that fired on me** | pass-1 fetched `1167650840134033` as "the Business project" (it is `DNAHolder`'s, `business.py:58`): 31,216 tasks, **0** `Company ID` values, all 5 targets "absent" | The zero was NOT taken: known-active census offices also came back absent, so the call shape was wrong, not the offices. Re-read `business.py` class-by-class → `1200653012566782` (`business.py:144`). Recorded here so the next reader does not repeat it. |

---

## 6. NOT TAKEN / INHERITED — and why

| Item | Status | Reason |
|---|---|---|
| Parent-chain hierarchy cross-check (Business → Unit subtasks → holder → Offer subtasks) agreeing with the cascade-phone attachment | **TAKEN (landed 21:30Z, after first writing)** | `offer_activity_read2.py` (task `bmoqp7n3a`) completed exit 0 after 6,353 GETs; results in `offer_activity_results.json`. Class agreement 100% on every resolved row (§5). Residual: the walk script skipped the two duplicate-task rows (14, 22) by its exactly-one-hit rule and, by construction, the two class-A rows; those four keep their §2 readings. |
| Pre-flip refusal history, DB row classes (A/C/D), "booked anyway" | **INHERITED** | `.sos/wip/SPLIT-not-enrolled-and-null-shadow-2026-09-10.md` §2.2, §4, §5 (self-graded MODERATE, single seat). Not re-queried: no DB access attempted. |
| 406 mails / 2 bookings / 8 days for `ccb52f4c` | **INHERITED** | `.sos/wip/CONSULT-morning-after-north-2026-09-11.md` L251-276, L433. |
| R-142 wording | **INHERITED from the charge** | not on disk in `.ledge/` or `.sos/wip/`. |
| `max_offer_activity` | **INHERITED semantics, local computation** | PR #431 OPEN; computed as max over `ACTIVITY_PRIORITY`. |
| SDK hydration path (`Offer.account_activity` on a hydrated `Business`) | **NOT TAKEN** | Used REST GET + the repo's `OFFER_CLASSIFIER`/`extract_section_name` directly (same primitives `Offer.account_activity` calls, `offer.py:264-280`). |
| Freshness of Asana sections vs reality | **NOT TAKEN** | Not adjudicable from Asana alone; `15caa02c` is the live example of a possible lag. |
| Rows 18 and 29 | **unjoinable under the ADR** | no guid on record and no Business task with that Office Phone. |
| Phone-keyed rows (21 of the 26) | **SUPPLEMENTARY** | §3: J1 second leg, not the ruled prefix key; treat as provisional until the denominator registry names them. |

---

## 7. Exact commands (all read-only; scratchpad = `/private/tmp/claude-501/-Users-tomtenuta-Code-a8-a8-repos-autom8y-asana/d5861864-ca42-4b96-84df-0a4323c797aa/scratchpad`)

```bash
# refs
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana && git fetch origin main && git rev-parse origin/main     # 6430cec5
gh pr view 431 --json state,mergedAt                                                                        # OPEN, null
git show "origin/main:src/autom8_asana/models/business/activity.py" | sed -n '181,210p'
git show "origin/main:src/autom8_asana/models/business/business.py" | grep -n 'max_offer_activity\|max_unit_activity'   # only :448 max_unit_activity
git diff --stat origin/main -- src/autom8_asana/models/business/activity.py                                 # empty
git show "origin/main:.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md" | sed -n '39,58p;92,120p;478,503p'
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-data && git show origin/main:.know/business-context.md | grep -n is_paying   # :363, :454

# credential + reachability (status only)
curl -s -o /dev/null -w 'http=%{http_code}\n' -H "Authorization: Bearer ${ASANA_PAT}" 'https://app.asana.com/api/1.0/users/me?opt_fields=gid'
curl -s -o /dev/null -w 'http=%{http_code}\n' -H "Authorization: Bearer ${ASANA_PAT}" 'https://app.asana.com/api/1.0/projects/1143843662099250?opt_fields=gid,name'

# pass 1 (Offer + Unit project dumps; WRONG Business project — the trap in §5)
cd /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana && AUTOM8Y_DATA_URL=http://offline-cli.local ASANA_WORKSPACE_GID=offline LOG_LEVEL=ERROR \
  uv run --quiet python "$SP/offer_activity_read.py" --refresh ccb52f4c c2ab6637 8e56f6e1 87bd31d7 ca70baa8 00000000
# pass 2 (correct Business project 1200653012566782 -> biz_dump.json; hierarchy walk landed 21:30Z, 6,353 GETs -> offer_activity_results.json)
AUTOM8Y_DATA_URL=http://offline-cli.local ASANA_WORKSPACE_GID=offline LOG_LEVEL=ERROR uv run --quiet python "$SP/offer_activity_read2.py"
# the table + ALL controls, zero API calls, from the two dumps (this is what §2 and §5 report)
AUTOM8Y_DATA_URL=http://offline-cli.local ASANA_WORKSPACE_GID=offline LOG_LEVEL=ERROR uv run --quiet python "$SP/cascade_join_local.py"
#   -> targets ccb52f4c c2ab6637 8e56f6e1 87bd31d7 ca70baa8 ; controls 4ec260bf d167d635 15caa02c 00000000 ; SPLIT §4 rows 1-29
#   -> outputs $SP/cascade_join_local.json (contains no names/phones)
```

Evidence grade: **MODERATE** (self-cap: single seat, own hands, no rite-disjoint corroboration). The [P] rows and every control are STRONG-eligible on re-run; the [Φ] rows are capped by §3.
