# MEASURE: Reverse-Orphan Count Per Grain — 2026-09-09

Read-only pathologist evidence collection. Dispatched by session autom8y-asana-f3,
initiative `name-the-client`, overnight autonomous push.

**Asserted dimension (fence #2, named before probing)**: whether there exists an
office/business-unit that Asana currently classifies ACTIVE or ACTIVATING (under
one or more of the code-defined section-classification vocabularies below) but
that is ABSENT from the 42-entry `contente_booking_live_allowlist` UUID set.

**HEADLINE RESULT: MEASUREMENT COULD NOT BE COMPLETED FOR ANY GRAIN.** A
necessary join key between Asana task/section-membership identity and the
42-entry allowlist's UUID identifier space does not exist anywhere in this
repo's code, and no live Asana probing was performed as a result (see §5). This
is reported as a complete, honest result per the dispatch's own admonition — an
un-joinable pair of sets is not a zero, it is an unmeasured comparison, and
asserting either direction would be exactly the UNTAKEN-ZERO / T-17 failure mode
the dispatch warns against.

## 0. The 42-office allowlist (re-extracted own-hands)

Source: `autom8y` repo, commit `4e0b41f9`,
`terraform/services/email-booking-intake/environments/production.tfvars:160`,
key `contente_booking_live_allowlist`, read via `git show 4e0b41f9:<path>`
(no working-tree checkout of the flagged 352-dirty tree — fence #6 honored).

```
git show 4e0b41f9:terraform/services/email-booking-intake/environments/production.tfvars \
  | grep '^contente_booking_live_allowlist' | sed 's/.*= "//;s/"//' | tr ',' '\n' \
  | wc -l                    # -> 42
  | sort -u | wc -l          # -> 42 (42 distinct)
```

All 42 values are well-formed UUIDv4-shaped strings (e.g.
`7363c7ea-66f8-487f-9f6e-c7a12a63d33f`). **Re-verified: 42 entries, 42 distinct,
42 well-formed — confirms the paragraph's claim independently.**

**Format note (load-bearing for §5)**: these are UUID identifiers, not Asana
GIDs (16-digit numeric strings) and not phone numbers. Whatever entity space
this allowlist keys into, it is not Asana's own GID space.

## 0b. CORRECTION (mid-sprint, verified own-hands) — the enablement plane is 46, not 42

A coordinator relay flagged that `contente_booking_live_allowlist` (42 entries)
is only ONE of two disjoint EBI-enablement lists in the same tfvars file.
**Independently re-verified before incorporating** (never trust a relayed
claim without own-hands confirmation — SVR discipline):

```
git show 4e0b41f9:terraform/services/email-booking-intake/environments/production.tfvars   | sed -n '100,125p'
```

confirms `contente_booking_monolith_served_set` at line 124:

```
contente_booking_monolith_served_set = "056ea6e6-0036-4e85-b38f-e5a68603ccce:reviewwave,161:reviewwave,4a2f351c-6829-4032-9226-2efe71e22a60:reviewwave,2b73d481-a777-4ea7-a070-ea1ce806762f:custom_ghl_id"
```

**4 entries, own-hands count confirmed.** Entry format is `{key}:{provider}`,
NOT a bare identifier — extraction MUST split on `:` and take the key
(confirmed by re-running the split myself; a naive whole-token compare against
Asana GUIDs would silently never match, per the relayed warning).

**`161` is NOT a UUID.** A UUID-shape filter would silently drop this key from
the served-set. **No UUID-shape filter was applied anywhere in this artifact's
allowlist/served-set extraction** — the 42-entry list happens to be
all-UUID-shaped (independently verified in §0), but the served-set is
mixed-shape and is carried through unfiltered.

**Served-set members, individually, `{key}:{provider}`:**

| Key | Provider |
|---|---|
| `056ea6e6-0036-4e85-b38f-e5a68603ccce` | reviewwave |
| `161` | reviewwave |
| `4a2f351c-6829-4032-9226-2efe71e22a60` | reviewwave |
| `2b73d481-a777-4ea7-a070-ea1ce806762f` | custom_ghl_id |

**Intersection with the 42-entry allowlist**: 0 (confirmed via `comm -12` on
sorted key lists) — the tfvars comment's disjointness claim ("Each office is
EITHER EBI-allowlisted OR monolith-served, never both") holds under direct
re-check.

**Union (the real enablement plane)**: 42 + 4 − 0 = **46 distinct keys**
(confirmed by `sort -u` over the concatenated key lists → 46 lines).

**`2b73d481-a777-4ea7-a070-ea1ce806762f:custom_ghl_id`** is flagged by the
correction as directly relevant to open fork F-4 (a `CustomGHLId` class
apparently has at least one live enablement-plane member). Per the
coordinator's own instruction, this office's Asana active/activating section
membership (if any) should be reported as its own row and NOT ruled on for
denominator membership — that ruling is reserved for the operator. **This
report cannot supply that row**, because (per §5 below, unchanged by this
correction) no join key exists in this repo's code between ANY of these 46
keys and Asana task/section identity. The gap is upstream of the 42-vs-46
distinction: **whether the comparison set has 42 or 46 members, it still
cannot be joined against Asana without a join key that this repo does not
contain.**

**Effect on §§2-4 below**: every occurrence of "42" in the per-grain
set-difference sections is superseded by "the 46-member union, and the two
46-member components (42-allowlist / 4-served-set) reported separately per
the coordinator's instruction" — but since §§2-4 were already NOT MEASURED
for the join-key reason, the 42-vs-46 correction does not change the
measured/not-measured verdict for any grain. It changes what the comparison
SET would have been, had a join key existed. This is recorded so that when
the join key is found, the next attempt starts from 46 (two-component), not 42.

## 1. Grain enumeration from code (`autom8y-asana`)

Per `models/business/activity.py:181-195` (`OFFER_CLASSIFIER`) and
`:213-235` (`UNIT_CLASSIFIER`), plus the process-pipeline block at `:263-306`,
and a THIRD independently-authored vocabulary discovered at
`reconciliation/section_registry.py:329-366` — there are candidate grains
across (at minimum) 4 distinct classification vocabularies, 2 of which govern
the SAME project (`1201081073731555`) and disagree.

### Grain A — Offer grain

- **Project GID**: `1143843662099250`
- **Classifier**: `OFFER_CLASSIFIER`, `src/autom8_asana/models/business/activity.py:181-206`
- **Section names classified `active`**: `OPTIMIZE - Human Review`, `STAGING`, `STAGED`, `ACTIVE`, `MANUAL`
- **Section names classified `activating`**: `ACTIVATING`, `IMPLEMENTING`, `NEW LAUNCH REVIEW`
- **Section GIDs for this project**: NOT present anywhere in this repo's code
  (no `_RECEIPT_NAME_TO_GID`-equivalent exists for the offer project; the
  offer-side section registry work — W-REG — is scoped to the unit project
  only per `section_registry.py:7-15`). A live `GET
  /projects/1143843662099250/sections` call would be required to resolve
  names to GIDs; NOT performed (see §5 — no join key existed downstream
  regardless).

### Grain B1 — Unit grain, `UNIT_CLASSIFIER` vocabulary (activity.py)

- **Project GID**: `1201081073731555`
- **Classifier**: `UNIT_CLASSIFIER`, `src/autom8_asana/models/business/activity.py:213-235`
- **Section names classified `active`**: `Month 1`, `Consulting`, `Active`
- **Section names classified `activating`**: `Onboarding`, `Implementing`, `Delayed`, `Preview`, `Engaged`, `Scheduled`
  (comment at `:224-225`: "Per truth audit: forward momentum, not inactive" /
  "scheduled interaction = activating")
- **Section GIDs** (from `reconciliation/section_registry.py:329-346`,
  `_RECEIPT_NAME_TO_GID`, sourced per that file's docstring from a "W-IRIS
  live `GET /sections` receipt" against this same project GID):
  - Onboarding `1201081073731565`, Implementing `1201081073731566`,
    Delayed `1201081073731567`, Preview `1201081073731569`,
    Engaged `1201081073731561`, Scheduled `1201081073731562`,
    Month 1 `1201081073731570`, Consulting `1201081073731568`,
    Active `1201081073731571`

### Grain B2 — Unit grain, vendored-monolith vocabulary (section_registry.py) — **F-2, same project, opposite classification**

- **Project GID**: `1201081073731555` (identical to Grain B1)
- **Classifier source**: `_VENDORED_MONOLITH_SECTIONS`,
  `src/autom8_asana/reconciliation/section_registry.py:359-364`, itself a
  vendored copy of `autom8/apis/asana_api/objects/project/models/business_units/main.py:17-38`
  (a DIFFERENT repo — not independently re-verified; vendoring is per this
  file's own docstring at `:349-357`)
- **Section names classified `active`**: `Month 1`, `Consulting`, `Active` (agrees with B1)
- **Section names classified `activating`**: `Onboarding`, `Implementing`, `Delayed`, `Preview` — **`Engaged` and `Scheduled` are EXCLUDED from `activating` here**
- **Section names classified `inactive`**: `Unengaged`, `Engaged`, `Scheduled`, `Paused`, `Cancelled`, `No Start`
  (`section_registry.py:361`) — **`Engaged` and `Scheduled` are classified
  `inactive` in this vocabulary**, directly opposite Grain B1's `activating`
  classification of the same two section names on the same project GID.
- This is F-2, confirmed IN THIS REPO — the "TWO OF THEM GOVERN THE SAME
  PROJECT WHILE CLASSIFYING Engaged AND Scheduled OPPOSITELY" claim in the
  dispatch is TRUE and locatable at these two exact file:line anchors. It does
  not require the `autom8y-data` cross-repo evidence to establish — this
  repo alone contains both halves of the contradiction.
- **Which vocabulary is live-wired?** `get_classifier("unit")` (consumed by
  `gid_push.py:491` for the account-status push) resolves to `CLASSIFIERS["unit"]
  = UNIT_CLASSIFIER` (Grain B1) per `activity.py:298`. The vendored-monolith
  taxonomy (Grain B2) at `section_registry.py` is consumed by
  `reconciliation/processor` for **exclusion-set** purposes (which sections'
  members are dropped from reconciliation), a DIFFERENT downstream consumer
  than the account-status/activity classification path. The two vocabularies
  are NOT dead code vs. live code — both are live, on two different
  consumption paths, over the same project. **This is exactly F-2 as
  described: an open fork, not resolved by this measurement.**
- Section GIDs: identical set as B1 (`_RECEIPT_NAME_TO_GID` is shared).

### Grain C — Nine process pipelines

- **Project GIDs**, `src/autom8_asana/services/gid_push.py:421-430`
  (`PIPELINE_TYPE_BY_PROJECT_GID`):
  - unit `1201081073731555` (already covered as Grain B — same project GID
    reused here, mapped to pipeline_type `"unit"`, which resolves back to
    `UNIT_CLASSIFIER` per `get_classifier`, i.e. NOT a distinct 10th grain)
  - sales `1200944186565610`, onboarding `1201319387632570`,
    outreach `1201753128450029`, retention `1201346565918814`,
    reactivation `1201265144487549`, expansion `1201265144487557`,
    implementation `1201476141989746`, account_error `1201684018234520`,
    month1 `1209247943184021`
- **Classifier**: all eight non-unit pipeline types share
  `_DEFAULT_PROCESS_SECTIONS`, `src/autom8_asana/models/business/activity.py:258-278`
- **Section names classified `active`**: `ACTIVE`, `EXECUTING`, `BUILDING`, `PROCESSING`, `OPPORTUNITY`, `CONTACTED`
- **Section names classified `activating`**: `SCHEDULED`, `REQUESTED`, `DELAYED`
- **Section GIDs**: NOT present anywhere in this repo's code for any of these
  8 project GIDs — no `_RECEIPT_NAME_TO_GID`-equivalent exists for them.
  Comment at `activity.py:252-256` self-flags: "PROVISIONAL: Section names are
  educated guesses... MUST be verified against live Asana project data... A
  later comment claims "Verified against live Asana API (2026-03-29)" for the
  section NAMES, but no corresponding GID table was ever added to this file.

## 2. The office set in ACTIVE/ACTIVATING sections — per grain

**NOT MEASURED for any grain.** No live Asana query was executed. Rationale:

1. For Grain A (offer) and Grain C (8 of the 9 process pipelines), the section
   GIDs are not resolvable from code at all — a live `GET /sections` call per
   project would be required first, and even then:
2. For ALL grains (A, B1, B2, C), there is no code-resolvable join key that
   maps an Asana task/section member to one of the 42 UUID-format allowlist
   entries (see §0 format note and §5). Enumerating office membership in
   ACTIVE/ACTIVATING sections without a confirmed join key would produce a
   listing that LOOKS like the requested comparison set but cannot actually
   be diffed against the allowlist — exactly the T-17 pre-written-caption
   trap ("write labels after output, never before"): fetching Asana members
   and captioning them "the office set for this grain" before confirming they
   share an identity space with the allowlist would be premise-fabrication,
   not measurement.

Per fence #1 (UNTAKEN-ZERO), no live-Asana call was made at all for this
measurement, because a query executed without a resolvable join key produces
neither a valid zero nor a valid non-zero over THE ASSERTED DIMENSION
(allowlist-membership) — it would only produce a listing over a DIFFERENT,
unlinked dimension (raw section membership), which is not what was asked.

## 3. Set difference (Asana-active-but-not-in-the-46-member-enablement-plane) — per grain

**NOT MEASURED**, for the same reason as §2. No office set could be honestly
constructed to diff, against either the 42-member allowlist, the 4-member
served-set, or their 46-member union.

## 4. Forward difference (46-member enablement-plane members absent from Asana-active) — per grain, incl. `70316996` and `2b73d481…:custom_ghl_id`

**NOT MEASURED**, for the same reason. Note for the record: `70316996-f9ee-4e54-
ac0a-790d2439ae71` IS present in the re-extracted 42-entry allowlist (confirmed
in the raw list captured in §0) — the dispatch's claim that this UUID is
allowlist-present is corroborated by this sprint's independent extraction.
`2b73d481-a777-4ea7-a070-ea1ce806762f` (key `custom_ghl_id`) IS present in the
served-set, own-hands confirmed in §0b — flagged per the correction as F-4-relevant
and reported here as its own row per instruction, with NO ruling on its
denominator membership. Neither office's Asana-side visibility (or invisibility)
could be confirmed or refuted per grain, because no join key exists to locate
either identifier on the Asana side.

## 5. What could NOT be measured (named)

1. **The join key itself.** Grepped this repo (`autom8y-asana`) exhaustively
   for `office_id`, `business_unit_id`, `external_id`, `source_id`,
   `monolith_id`, `business_unit_uuid`, `office_uuid`, `contente_booking_live_allowlist`
   — zero hits. The repo's own office-identifying field for Asana-side
   entities is `office_phone` (used throughout `gid_push.py`, e.g. the
   `CANARY_SENTINEL_PHONE` exclusion), which is NOT the same identifier space
   as the allowlist's UUIDs. No code path in this repo converts between a
   phone-keyed Asana office and a UUID-keyed allowlist entry.
2. **Section GIDs for Grain A (offer, project `1143843662099250`)** — no
   registry equivalent to `_RECEIPT_NAME_TO_GID` exists for this project.
3. **Section GIDs for 8 of 9 process-pipeline projects (Grain C)** — same gap;
   only names are code-documented, GIDs are not.
4. **Any live Asana API call** — `ASANA_PAT` was available and verified
   reachable per the dispatch, but was NOT invoked, because doing so without
   a resolvable join key would not have advanced the measurement and risked
   manufacturing a same-looking-different-dimension listing (§2).
5. **Resolution of F-2** (Grain B1 vs B2 disagreement over `Engaged`/`Scheduled`)
   — confirmed as an open, live, two-consumer-path contradiction within THIS
   repo (§1 Grain B2), but which vocabulary should govern the reverse-orphan
   question, or whether they should be reconciled, is explicitly NOT decided
   here per the dispatch's hard limit ("Do not decide F-2").
6. **The `autom8y-data` two-member `SBM_FETCH_POOLS` vocabulary** and its
   "two more grains" — out of this repo, not inspected (would require a
   separate session against that repo).

## 6. Grains identified vs. grains measured

**4 of 4 identifiable grains found in code (offer, unit-B1, unit-B2,
process-pipelines-C); 0 of 4 measured end-to-end** — the blocking gap is
identical and upstream of all four: no code-resolvable join key exists in
`autom8y-asana` between Asana task identity and either the 42-entry allowlist,
the 4-entry served-set, or their 46-member union (§0b). This is reported as
the complete result: **an honest "0 of 4 grains measured, join-key absent,
comparison-set corrected from 42 to a 46-member two-component union mid-sprint
and independently re-verified" rather than a fabricated per-grain office
listing.**
