---
type: review
subtype: fixture-recapture-receipt
status: accepted
artifact_id: RECEIPT-s8-0-fixture-recapture-2026-07-30
initiative: substrate-v2-epoch — S8-0 pre-gate hardening (P5 gate preconditions)
region: us-east-1
account: "696318035277"
date: 2026-07-30
operator: principal-engineer (10x-dev, S8-0 pre-gate hardening)
consumes: tests/harness/substrate_gate/exemplars.py exemplar_two_*
---

# RECEIPT — S8-0 exemplar #2 fixture recapture (offer plane, current state)

> Pythia ruling O4 (additive). Wound offer plane ONLY (project 1143843662099250,
> EntityType.OFFER). `+unit` / `+siblings` EXCLUDED (UV-P-3 / S10 scope — a surfaced
> boundary, not a silent omission).

## AFFIRMATION (verbatim)

**0 Asana API calls; AWS control-plane + S3 GET/LIST only; NO warm trigger, NO write,
NO terraform.**

Derivation path: `aws sts get-caller-identity` (control plane) → `aws s3 ls` /
`aws s3api list-objects-v2` / `aws s3api head-object` (LIST + metadata) →
`aws s3api get-object` (READ-ONLY GET of `dataframe.parquet` + `watermark.json`) →
`polars.read_parquet` + group-by-sum LOCALLY. No Asana SDK/HTTP was imported or invoked
at any point; the only in-repo import touching Asana was the entity registry
(`sla_seconds_for(OFFER)` — in-memory config, no network).

## AWS identity

```
$ aws sts get-caller-identity
{ "Account": "696318035277", "Arn": "arn:aws:iam::696318035277:user/tom.tenuta", ... }
```

## Probe commands (read-only)

```
aws s3 ls   s3://autom8-s3/dataframes/1143843662099250/offer/
aws s3 ls   s3://autom8-s3/dataframes/1143843662099250/offer/sections/
aws s3api head-object --bucket autom8-s3 --key dataframes/1143843662099250/offer/watermark.json
aws s3api head-object --bucket autom8-s3 --key dataframes/1143843662099250/offer/dataframe.parquet
aws s3api get-object  --bucket autom8-s3 --key dataframes/1143843662099250/offer/watermark.json  watermark.json
aws s3api get-object  --bucket autom8-s3 --key dataframes/1143843662099250/offer/dataframe.parquet dataframe.parquet
aws s3api list-objects-v2 --bucket autom8-s3 --prefix dataframes/1143843662099250/offer/sections/  # 33 section artifacts
```

## Snapshot instant + artifact provenance

- **Snapshot instant (UTC):** 2026-07-30T12:24:15Z (the co-temporal write of the
  assembled frame + its watermark).
- **Watermark BUILD instant (live-pull moment):** 2026-07-30T12:23:09.371507+00:00
  (`watermark.json` field `watermark`) — this is exemplar #2's `built_from_live_at`.
- **Watermark saved_at:** 2026-07-30T12:24:14.403378+00:00. **row_count:** 4180.

| artifact | ETag | VersionId | LastModified (UTC) | size | digest |
|----------|------|-----------|--------------------|------|--------|
| `offer/dataframe.parquet` | `de911e6885a587e09e653ec2d697211d` | `2xx28zUzbkL4G__9FqxupefTaRfPp4LJ` | 2026-07-30T12:24:15Z | 242447 | sha256 `da97751365f1a4c07d508732b5465b72babb975a2dd17ca4a80d43ef357c3e7d` |
| `offer/watermark.json` | `22dfe7576e7ac5bd2da3e0749c85ad21` | `05lifJ79aLT_n0so4Epn7BWJCo5aBzt8` | 2026-07-30T12:24:15Z | 669 | (json, verbatim retained in fixtures) |

## TORN-READ GUARD — PASSED

Accept a snapshot only if `watermark.json` is internally consistent with (post-dates)
the section artifacts. Authoritative UTC ordering:

```
newest of 33 section artifacts : 2026-07-30T11:09:04Z
watermark BUILD instant        : 2026-07-30T12:23:09.371507Z   (> sections ✓)
watermark saved_at             : 2026-07-30T12:24:14.403378Z   (> build ✓)
watermark.json + dataframe write: 2026-07-30T12:24:15Z         (co-temporal ✓)
```

The watermark post-dates every section artifact, and the assembled `dataframe.parquet`
shares the watermark's write instant (12:24:15Z) with a matching `row_count` (4180) and
column set — an internally-consistent, non-torn set. No re-probe was required.

## Derived composition + served_value (polars, local)

Group `dataframe.parquet` by `section`, sum `mrr`, over the THREE offer-lifecycle
sections exemplar #1 tracked (the "three DEFECT sections"). NOTE: the section name is a
plain HYPHEN (U+002D) in prod — exemplar #1's synthetic fixture used an en-dash (U+2013).

| section (verbatim S3 bytes) | rows | Σ mrr |
|-----------------------------|------|-------|
| `ACTIVE` | 47 | $60,085 |
| `OPTIMIZE - Human Review` | 7 | $10,900 |
| `STAGED` | 7 | $10,000 |
| **served_value** | **61** | **$80,985** |

- **Composition canonical form** (sorted `{section: [rows, value]}`):
  `{"ACTIVE":[47,60085.0],"OPTIMIZE - Human Review":[7,10900.0],"STAGED":[7,10000.0]}`
- **Composition digest:** sha256 `4e711a7a8b8a7f4b18d4beb7ef9f7dc28286d682d3e339c9a407c63de84bce65`
  → exemplar #2 `content_digest` / `frame_digest` (drift tripwire: same bytes → same digest).
- **Offer SLA:** 180s (registry `default_ttl_seconds` for OFFER; `sla_seconds_for(OFFER)` — in-memory, no network).

## exemplar-#2-value ↔ source-artifact mapping

`exemplar_two_materialization().served_value == $80,985` is the Σ-mrr over
{ACTIVE, OPTIMIZE - Human Review, STAGED} in `offer/dataframe.parquet`
(ETag `de911e68…`, sha256 `da977513…`) at snapshot 2026-07-30T12:24:15Z. Its
`built_from_live_at` is the watermark build instant 2026-07-30T12:23:09.371507Z.

## Measured dark-build drift-delta (vs exemplar #1's frozen $84,385)

```
$80,985 (current #2) − $84,385 (frozen #1 fresh) = −$3,400  (−4.03%)
```

Decomposition (RC-A-2 ledger idiom; exemplar #1 FRESH → exemplar #2 CURRENT):

```
ACTIVE                  48r·$61,585 → 47r·$60,085 = −$1,500
OPTIMIZE Human Review    5r·$7,900  →  7r·$10,900  = +$3,000   (en-dash → hyphen in prod)
STAGED                   7r·$10,000 →  7r·$10,000  =     $0
OTHER (unchanged)        6r·$4,900  →   (dropped)  = −$4,900   (exemplar #1 synthetic bucket; no S3 analogue)
                                                net  = −$3,400
```

The +$1,500 real shift across the three shared sections, minus exemplar #1's $4,900
synthetic OTHER bucket (unreproducible from S3), composes the −$3,400 headline delta.

## Retained snapshot bytes (serialization-determinism synergy)

Retained under `tests/harness/substrate_gate/fixtures/offer_1143843662099250/`:

- `offer_plane_section_mrr.parquet` — a **PII-SAFE column projection** `(section, mrr)`
  of the real frame (sha256 `614c9ab89f40e7d9cdf44597720a088ec00c504f62df47f4bc0b3eeaa292c986`).
  ALL identifier/PII columns (`name`, `office`, `office_phone`, `company_id`, `offer_id`,
  the `*_url` / `*_id` fields, etc.) were DROPPED — retained only the two columns the
  offer-plane aggregate derives from. The projection re-derives $80,985 on its own
  (round-trip determinism input). **Judgment call:** the full 242 KB `dataframe.parquet`
  carries customer PII (phone numbers, company ids, booking URLs) and is deliberately NOT
  committed; its ETag + sha256 above preserve full provenance for a re-fetch if a future
  determinism test needs more value columns.
- `watermark.json` — the real watermark verbatim (no PII: project_gid, column names,
  counts, timestamps only).

## DuckDB MCP synergy — SKIPPED (non-blocking)

No DuckDB MCP tooling was available in this dispatch. Parquet sums were derived with
`polars` locally, as instructed. This skip is non-blocking.

## Amendment — 2026-07-30 (C17): proof-metadata SLA 180→3600

Per the C8 operator ruling (option-c, C8-sla-governance-packet-2026-07-30
§Ratification) and architect build-note C17: exemplar #2's `FreshnessProof.
sla_seconds` changes 180→3600 (the governed `freshness_sla_seconds`, decoupled
from the cache-role `default_ttl_seconds` which stays 180). **The S3-derived
VALUE ($80,985), composition, and content digest are byte-unchanged** —
`sla_seconds` is proof-metadata, not a composition/digest input (proven
mechanically by `test_fixture_parquet_bytes_rederive_the_pinned_constants`,
which re-derives all three from raw bytes with zero reference to sla_seconds).
No re-snapshot performed; **0 Asana calls, 0 S3 calls** in this amendment.

---

## O4 leg-2 — window-open re-snapshot (2026-08-03, S8-2 WU-1)

> Mirrors leg-1's capture method verbatim (offer plane ONLY; project 1143843662099250,
> EntityType.OFFER). `+unit` / `+siblings` frames are read for UV-P-6 section counts
> (LIST only) but the served-value recompute is offer-only, per UV-P-3 / S10 scope.
> Probe by principal-engineer, session session-20260803-220334-f2a75514, main @ 5d62d0b8.
> **pythia (the standing adjudicator) rules the drift verdict, NOT this probe.**

### AFFIRMATION (verbatim)

**0 Asana API calls; AWS control-plane identity check (`sts get-caller-identity`) + S3
LIST/GET via `aws s3 ls` / `aws s3 cp` ONLY; NO warm trigger, NO write to the bucket,
NO terraform.** All parquet recompute ran on LOCAL scratchpad copies with `polars`; the
only in-repo imports were `entity_registry.py` / `project_registry.py` (in-memory config,
no network). System `aws` CLI (aws-cli/2.36.8), region us-east-1.

### Probe window + identity

- **Probe window (UTC):** 2026-08-03 16:53Z → 16:57Z.
- **Identity:** `arn:aws:iam::696318035277:user/tom.tenuta` (same principal as leg-1).

### Offer-plane snapshot (current state, 2026-08-03)

Probe: `aws s3 ls s3://autom8-s3/dataframes/1143843662099250/offer/` and `.../offer/sections/`;
`aws s3 cp .../offer/ ./ --recursive` (38 objects).

| artifact | mtime (UTC) | size | notes |
|----------|-------------|------|-------|
| `offer/dataframe.parquet` | 2026-08-03 16:12:42 | 244813 | sha256 `cb79eaf500501c4aeec3b7446af7be9ead44b36e4150e6efc15b8f036b75c261` |
| `offer/watermark.json` | 2026-08-03 16:12:42 | 684 | build `2026-08-03T16:12:41.349255Z`; saved `…41.501623Z`; row_count 4191 |
| `offer/manifest.json` | 2026-08-03 16:06:49 | 15209 | `total_sections: 34`, `completed_sections: 34`, all `status: complete` |
| `offer/gid_lookup_index.json` | 2026-08-03 16:12:42 | 56222 | — |
| `offer/sections/*.parquet` | newest 16:01:06 / oldest 2026-06-18 22:04:35 | — | **33 S3 parquets** |

**Watermark schema note (non-load-bearing):** the 08-03 watermark adds two fields absent
in leg-1's — `population_degraded: false`, `population_min_rate: 0.8205128…`. Value/composition
unaffected (they are not aggregate inputs).

**Section-count reconciliation:** manifest `total_sections = 34` vs **33 S3 parquets**. The
one section with no parquet is `1201990715810462` ("REVIEW OPTIMIZATION", rows 0, empty). This
is the FIX-1 / `DEFECT-delta-path-empty-poison` surface (an empty section that carries a manifest
entry but no object). 17 of the 33 present parquets are the *identical* 2358-byte empty stamp
(sha256 `bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2`, gid_hash
`e3b0c44298fc1c14`) — strong corroboration the FIX-1 deterministic empty-section stamp holds
(same empty bytes → same hash).

### TORN-READ GUARD — PASSED

```
newest of 33 section artifacts : 2026-08-03T16:01:06Z
watermark BUILD instant        : 2026-08-03T16:12:41.349255Z   (> sections ✓)
watermark saved_at             : 2026-08-03T16:12:41.501623Z   (> build ✓)
watermark.json + dataframe write: 2026-08-03T16:12:42Z         (co-temporal ✓)
```

Internally consistent, non-torn set. Manifest shows 34/34 complete, no in-progress section.

### Recompute (polars, LOCAL) — served value

Group `dataframe.parquet` by `section`, sum `mrr`, over the three in-scope statuses
{ACTIVE, "OPTIMIZE - Human Review", STAGED}. Section names verified plain-HYPHEN (U+002D)
in prod — codepoints for "OPTIMIZE - Human Review" = `… 0x20 0x2d 0x20 …` (matches leg-1).

| section (verbatim S3 bytes) | rows | Σ mrr |
|-----------------------------|------|-------|
| `ACTIVE` | 45 | $57,085 |
| `OPTIMIZE - Human Review` | 7 | $10,900 |
| `STAGED` | 6 | $8,000 |
| **served_value (active_mrr)** | **58** | **$75,985** |

- **Total frame row count:** 4191 (watermark `row_count` matches).
- **Composition canonical form:** `{"ACTIVE":[45,57085.0],"OPTIMIZE - Human Review":[7,10900.0],"STAGED":[6,8000.0]}`
- **Composition digest:** sha256 `4a3aca962e1b656a47a74c2d57c19d1353b024b11c98c54fee267666e5285b65`
  (leg-1 baseline digest was `4e711a7a…`; digest changed → drift tripwire fired correctly).

### DRIFT vs the pinned S8-0 baseline (exemplar #2)

| metric | S8-0 baseline (2026-07-30) | O4 leg-2 (2026-08-03) | Δ |
|--------|----------------------------|------------------------|---|
| served_value (active_mrr) | $80,985 | **$75,985** | **−$5,000 (−6.17%)** |
| in-scope rows | 61 | 58 | −3 |
| total frame rows | 4180 | 4191 | +11 |
| composition digest | `4e711a7a…` | `4a3aca96…` | changed |

**Per-section decomposition (baseline → current):**

```
ACTIVE                  47r·$60,085 → 45r·$57,085 = −2 rows, −$3,000
OPTIMIZE - Human Review  7r·$10,900 →  7r·$10,900 =  0 rows,     $0   (held EXACTLY)
STAGED                   7r·$10,000 →  6r·$8,000  = −1 row,  −$2,000
                                                net = −3 rows, −$5,000
```

**Probe reading (data only; verdict is pythia's):** the delta is fully accounted by three
offers leaving the in-scope lifecycle sections over 4 days (−2 from ACTIVE, −1 from STAGED),
net −$5,000 MRR; "OPTIMIZE - Human Review" is byte-stable. The total frame GREW (+11 rows,
driven by INACTIVE/Sales Process churn), so this is not a truncation/torn read — it reads as
benign business motion. **pythia adjudicates {no-drift | delta+explanation}.**

### UV-P-6 discharge data — real per-entity section counts (S3 LIST, own hands)

Method: `aws s3 ls s3://autom8-s3/dataframes/{primary_project_gid}/{entity}/sections/` per
governed entity; GIDs resolved from `entity_registry.py` / `project_registry.py`.

| governed entity | primary_project_gid | S3 section parquets | frame.parquet mtime (UTC) | oldest→newest section mtime |
|-----------------|---------------------|--------------------:|---------------------------|-----------------------------|
| business | 1200653012566782 | 5 | 2026-08-03 16:04:55 | 2026-07-27 16:13:23 → 2026-07-31 20:22:35 |
| unit | 1201081073731555 | 13 | 2026-08-03 16:05:37 | 2026-08-03 16:04:56 → 16:05:33 |
| offer | 1143843662099250 | 33 (manifest 34) | 2026-08-03 16:12:42 | 2026-06-18 → 2026-08-03 16:01:06 |
| contact | 1200775689604552 | 4 | 2026-08-03 16:14:15 | 2026-06-09 → 2026-07-31 16:14:50 |
| asset_edit | 1202204184560785 | 18 | 2026-08-03 16:20:12 | 2026-07-27 18:26:08 → 2026-08-03 16:06:52 |
| **process** (dynamic; 9 pipelines) | **None** (per-pipeline GIDs) | **25** (sum) | 16:27:23 → 16:31:04 | see breakdown |

**`process` fan-out breakdown** (`primary_project_gid=None` in the registry — process is served
across 9 pipeline projects; each pipeline is its own rebuild):

| pipeline | project_gid | section parquets | frame mtime (UTC) |
|----------|-------------|-----------------:|-------------------|
| process_sales | 1200944186565610 | 4 | 16:27:23 |
| process_outreach | 1201753128450029 | **0*** (monolithic, 100545 B) | 16:27:48 |
| process_onboarding | 1201319387632570 | 4 | 16:29:15 |
| process_implementation | 1201476141989746 | 5 | 16:29:46 |
| process_retention | 1201346565918814 | 4 | 16:30:12 |
| process_reactivation | 1201265144487549 | 6 | 16:30:52 |
| process_account_error | 1201684018234520 | **0*** (monolithic, 8934 B) | 16:30:57 |
| process_expansion | 1201265144487557 | **0*** (monolithic, 12355 B) | 16:31:04 |
| process_month1 | 1209247943184021 | 2 | 16:29:49 |

`*` **ANOMALY (surfaced for WU-2):** three pipelines write their frame *monolithically* with NO
`sections/` subdir at all — a non-empty frame (outreach = 100 KB, ~2800 rows) served as one
object. **"0 section files" ≠ "0 upstream fetch attempts"** — a monolithic project is ≥1 paginated
fetch. The section-count proxy under-counts the true fetch fan-out for these pipelines. WU-2's
budget model MUST NOT equate `section_count == 0` with `attempts == 0`.

### Warm-cadence evidence (vs the C8 17–25 min baseline)

- **Full-substrate warm sweep:** every governed frame in THIS snapshot was (re)assembled inside a
  single sweep running **16:04:55 → 16:31:04 UTC (≈26.2 min span)**, in exact `warm_priority` order
  (business 1 → unit 2 → offer 3 → contact 4 → asset_edit 5/6 → process pipelines 10–18). This is
  consistent with the C8 baseline of ~17–25 min offer-rebuild cadence being the sweep interval.
- **Offer content-change cadence (2026-08-03, FIX-1 hash-CLEAN gated writes):** the churning offer
  sections re-wrote at 14:05:10, 15:05:40, 16:01:06 UTC → ~56–60 min *between content changes*. This
  is SLOWER than the frame-reassembly cadence because FIX-1 skips hash-CLEAN sections (unchanged
  section → no re-write → old S3 mtime). Manifest `last_verified_at` = 16:06:47 for offer sections
  (verified every sweep; written only on change).
- **Freshness at probe time:** offer frame built 16:12:41, probed 16:53 → **≈40 min old, GREEN**
  under the governed 3600 s (1 h) SLA (40 min < 60 min).
- **Independent cadence limit (honest):** a precise frame-to-frame interval cannot be derived from a
  single `aws s3 ls` (prior versions require `s3api list-object-versions`, out of the `ls`/`cp`
  constraint). The continuous WU-4 window is the authoritative frame-cadence measurement.
- **Cache-warmer bulk checkpoint** (`aws s3 cp s3://autom8-s3/cache-warmer/checkpoints/bulk/latest.json -`,
  streamed, not saved): `invocation_id f21b13bb-…`, `created_at 2026-08-03T16:57:12Z`,
  `expires_at …17:57:12Z` (1 h dead-man TTL); 1 entity complete (`1167650840134033` DNA-holder
  project arm 227 s / section arm 271 s, 31 091 rows), **66 arms pending** (the 34-GID `project`+`section`
  bulk pre-materialization lane — distinct from the entity-frame lane above). Confirms an active,
  in-flight warm sweep at probe time.

### Budget-cap calibration arithmetic (feeds WU-2 `PerDayBudgetLedger.cap`)

Model (UV-P-6): 1 unit charged per upstream fetch ATTEMPT; per-day hard REFUSE at cap.
attempts-per-sweep ≈ sections fetched per rebuild.

**Per-governed-sweep fan-out (every-section-verified upper bound):**

```
offer 34 (manifest) + asset_edit 18 + unit 13 + business 5 + contact 4
  + process 28 (25 section files + 3 monolithic pipelines floored at ≥1)   = 102 attempts/sweep
(strict S3-parquet count, no monolithic floor: 33+18+13+5+4+25            =  98 attempts/sweep)
```

- **Single-rebuild MAX fan-out = offer @ 34** (cap sanity floor: one offer rebuild must complete).
- **Sweep interval:** ≈26 min observed (span) / ~17–25 min C8 baseline → **sweeps/day = 48 (@30min) · 55 (@26min) · 72 (@20min)**.
- **Per-day governed attempts (upper bound):** `102 × {48, 55, 72} = {4 896; 5 610; 7 344}/day`.

**Cap options (headroom on the ~5 600/day midpoint):**

| headroom | cap/day | rationale |
|----------|--------:|-----------|
| 1.0× | ~5 600 | too tight — no room for WU-4 paced-parity double-reads or retry jitter |
| 1.5× | ~8 400 | modest headroom |
| **2.0×** | **~11 200** | **RECOMMENDED start** — absorbs warm sweep + WU-4 paced live-parity + retry jitter, still bites a runaway loop; well below the Asana PAT hard limit (1500 req/min ≈ 2.16 M/day). The per-day cap is a P10 runaway guard (the 2026-07-27 429-storm), not the API ceiling. |

**Key input WU-2 MUST pin (do NOT assume):** whether an "attempt" = every-sweep freshness *verify*
(→ ~102/sweep upper bound) or only an actual upstream *GET* on a hash-DIRTY section (→ far fewer;
offer re-fetched only 4 sections across 2 h on 2026-08-03). Plus the monolithic-pipeline nuance above.
UV-P-6's whole point: derive the cap from real fan-out, not a guess — both bounds are now on record.

### asset_edit / process SLA re-ratification data (C8 §Ratification: "re-ratify at UV-P-6 discharge")

C8 stamped asset_edit/process at **3600 s provisional** (no measured cadence at ratification).
Observed here:

- **asset_edit:** frame rebuilt once per sweep (16:20:12), sweep interval ≈26 min → 2× cadence ≈ 52 min
  < 3600 s. **3600 s CONFIRMED adequate** (frame is always < 1 h old at this cadence).
- **process (all 9 pipelines):** frames rebuilt once per sweep (16:27–16:31), same ≈26 min interval →
  2× cadence ≈ 52 min < 3600 s. **3600 s CONFIRMED adequate.** Monolithic pipelines rebuild *faster*
  (single object), so 3600 s is comfortably conservative for them.

**Re-ratification reading (operator's call):** the provisional 3600 s for asset_edit and process may be
lifted to RATIFIED — observed cadence (≈26 min sweep) sits at/under the C8 "SLA ≥ 2× cadence" bar for
both. No value change required; only the `provisional` qualifier is dischargeable.

### sha256 of every downloaded parquet (34 objects)

```
dataframe.parquet  cb79eaf500501c4aeec3b7446af7be9ead44b36e4150e6efc15b8f036b75c261
sections/1143843662099256.parquet (ACTIVE)   7145e13231eacd440d58bd5ccae7a2e939675c83ce8776bd82da1853d64f783a
sections/1143843662099257.parquet (INACTIVE) 6473fb07afdc03057112ed42600f3dc8f4d2319adbafac76490d035414332ece
sections/1155403608336729.parquet  a0941160048d7f4cd82fe44f85ffafbd7fd890007df52ecc8f1af94cae443948
sections/1199511476245249.parquet  76d0518056b2ba64da8e0961b005aefe4695372da298d2c054880b7aed8899e1
sections/1201105736066893.parquet  75b01092c3cb42c95a6cbaddc36a8382a486fd8505f782df3c95920b88bdd8a5
sections/1201131323536610.parquet  d5e2817a48df1f08bffe804c0aff8bdb05f37217cfc7f16666a405bf6922034c
sections/1201147432407818.parquet  2d2be1d11816e81ea015aa4358e74488b36f5fcae375c7349511d3a744b784a0
sections/1201488931621745.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1201903612408022.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1201930502275849.parquet  bb48c4367bb73b628c4095e384d3c3b5b0652402b8212c38c99bad2bd02c70de
sections/1201990715810461.parquet (OPTIMIZE - Human Review) d2a154523b3c251bc40cf94359cd7afb32db1a47aac90fd4604e443f9842b0fc
sections/1202005604742382.parquet  5ecd3acf12e38526f3635b102ec408a4597d98e83c28afa465a2c155733de36c
sections/1202496785025459.parquet  54ff549fd9a2c6786f890eb0ad92e9ed5a6be769a6f95e5246abbc856945283e
sections/1202885704349471.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1203363090117434.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1203713548624886.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1204000038008371.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1204152425074369.parquet  e48241603688af8fcc9afc3b32ba55ef33efa5702b0851f31bbc37a27f4bfc32
sections/1204152425074370.parquet  1a3bb177ca23e4e85495a9cd6502da9f545b18f33ef362c9591a8e1133c473c5
sections/1204152425074371.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1204157499197063.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1204313987569696.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1205398175267472.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1205478010922161.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1205807787419514.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1206021313912651.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1206486569501969.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1206900809285302.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1206942147371947.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1207396100287952.parquet (NEW LAUNCH REVIEW) 0709b864fb175c3d3b54e002bd97614fa0f3264252ad319cd61f71a6f1c0577f
sections/1208667647433692.parquet  2cb9279c24763f0f4eec7b75a9f9b7a1fc56d7ed3ae88c57e2e8838a30c38288
sections/1209233681691557.parquet  bd406b89f01ce172e7d5a82d495fbf4517408eecbd9020aea2715e1616e525c2  [empty stamp]
sections/1209233681691558.parquet (STAGED) 54780e58f9e8ba88513064561cc7e3ecff2aa6be1b94cd71ab48394e9a8fdd13
```

### PROBE RECEIPT

- **S3 LIST ops (`aws s3 ls`):** 1 offer parent + 1 offer sections + 5 governed-entity parents +
  5 governed-entity sections + 9 process-pipeline parents + 9 process-pipeline sections +
  1 cache-warmer checkpoints prefix = **31 LIST calls**.
- **S3 GET ops (`aws s3 cp`):** 1 recursive copy of the offer prefix = **38 objects downloaded**
  (33 section parquets + `dataframe.parquet` + `gid_lookup_index.json` + `manifest.json` +
  `manifest.json.bak-2026-07-27` + `watermark.json`); + 1 checkpoint `latest.json` streamed to stdout.
- **Total bytes downloaded to scratchpad:** **732 357 bytes** (offer prefix) + ~3.5 KB checkpoint (streamed).
- **Control-plane:** 1 `aws sts get-caller-identity` (identity check).
- **ZERO-ASANA ATTESTATION:** 0 Asana API calls; 0 warm triggers; 0 bucket writes; 0 terraform.
  No Asana SDK/HTTP imported or invoked. Downloads landed only in the session scratchpad
  (`/private/tmp/.../scratchpad/wu1/`), never the repo.

## pythia drift verdict: **{delta+explanation}** — EXPLAINED-BENIGN, RE-PIN GRANTED, PROMINENT-FLAGGED

> Inscribed verbatim by the main thread 2026-08-03 (Pythia non-authoring doctrine, DR-2
> Option A). Independent arithmetic re-verification performed by the adjudicator own-hands
> before ruling: leg-2 in-scope sum $57,085 + $10,900 + $8,000 = $75,985 (58 rows: 45+7+6);
> leg-1 baseline $60,085 + $10,900 + $10,000 = $80,985 (61 rows: 47+7+7); net −$5,000 / −3
> rows; −$5,000 / $80,985 = −6.174%. The decomposition closes exactly, to the penny and the row.

**Scope of this verdict.** O4 leg-2 is a **DRIFT** verdict (the pinned S8-0 exemplar baseline vs current substrate state, same substrate at two time-points), NOT a v1-vs-v2 **parity** divergence (that is the WU-4 continuous window). The rubric's §3 recapture-drift protocol governs; the §1 wound classes are applied here only as exclusion tests on the drift.

### 1. Evidence-gate results (all cleared, on positive evidence)

- **Snapshot-validity / torn-read guard — PASS.** newest section `16:01:06Z` < build `16:12:41.349255Z` < saved `16:12:41.501623Z` < write `16:12:42Z`; watermark `row_count` 4191 matches; manifest 34/34 complete, no in-progress section (this receipt, leg-2 section). A valid pin candidate; **W6 excluded.**
- **Determinism intact — W1 excluded on positive evidence.** The composition-digest change `4e711a7a…` → `4a3aca96…` is CORRECT tripwire behavior: **different bytes** (rows genuinely departed) → different digest, not same-bytes→different-digest. Independently corroborated by the 17 byte-identical 2358-B empty stamps (all sha256 `bd406b89…`): same empty bytes → same hash, proving the FIX-1 deterministic-stamp serialization holds. This is quiet-side RC-F determinism evidence, banked.
- **Not a data-loss / silent-drop — W4 excluded on positive evidence.** The total frame **GREW** +11 rows (4180 → 4191) while the in-scope set shrank −3. A truncation/torn/partial-rebuild wound would SHRINK the frame; growth is the structural signature of rows **moving** (offers departing in-scope lifecycle sections into INACTIVE/Sales-Process), not rows lost. The "OPTIMIZE - Human Review" section held **byte-exact** (7r/$10,900) — an untouched section's byte-stability under a live rebuild is a determinism-intact tell inconsistent with corruption.
- **Decomposition closes exactly — W3 excluded.** ACTIVE −2r/−$3,000 + OPTIMIZE 0/$0 + STAGED −1r/−$2,000 = −3r/−$5,000, matching the headline to the penny and the row (arithmetic re-verified by the adjudicator own-hands).
- **Pacing/budget — W5 excluded.** The probe was S3-only, 0 Asana calls, 0 warm triggers, 0 writes, 0 terraform; it is itself a model of P10 discipline (it refused to chase per-offer attribution via an ad-hoc Asana pull).

### 2. Ruling on attribution granularity — per-section decomposition satisfies the B2 "individually-attributable" bar here; per-offer attribution is NOT required

**Per-section decomposition suffices for {delta+explanation} / explained-benign in this case.** Three grounds:

1. **Precedent parity.** B2's load-bearing property is inscribed as "per-section decomposability with every line attributable, *not the magnitude*." The O4 leg-1 precedent (−$3,400/−4.03%, this receipt L106-123) was ruled benign at **section** granularity — it did not chase per-offer identity. To now demand per-offer attribution would raise the bar above the pre-registered rubric and above the leg-1 precedent — the precise post-hoc bar-raising that pre-registration exists to forbid.
2. **The attribution here is not bare plausibility — it carries an S3-derivable wound-exclusion.** The benign classification rests on a structural check derivable entirely from the S3 bytes in hand: **(frame grew +11) AND (in-scope shrank −3) AND (one in-scope section byte-stable) AND (determinism intact via the 17 empty stamps)**. The only hypothesis consistent with all four is real business motion out of the in-scope sections; every wound class is excluded by that conjunction (§1 above). That conjunction IS the "every line attributable" substance at section granularity.
3. **P10 constraint + obtainability.** Per-offer attribution cannot be obtained now without an ad-hoc Asana pull, which P10 bans (Charter L122-126). It is not needed: the wound classes per-offer attribution would guard against are already excluded. **Minimal-additional-evidence note (for the record, not required):** a per-offer gid-set diff of the ACTIVE/STAGED section parquets is obtainable *from S3 bytes alone* (the section parquets + `gid_lookup_index.json` are retained) with **zero** Asana touch — but it is **retro-unavailable against leg-1** because leg-1 deliberately dropped all gid/PII columns, retaining only the `(section, mrr)` projection (this receipt L127-137). It is **prospectively available** for WU-4. This asymmetry is a further reason section-level is the correct bar for THIS verdict.

**Boundary named, not assumed:** this verdict certifies **substrate parity** (v2 faithfully computes what the source frame contains), NOT **business truth** (whether those 3 offers *should* have departed). If the departures were themselves an upstream Asana-side anomaly, that is a business-data question outside the drift verdict's scope and outside the substrate's fault surface — the substrate correctly reflects its source. The boundary is flagged rather than silently folded in.

### 3. Prominence disposition (both thresholds tripped)

The drift trips **both** §3 prominence thresholds: −6.17% ≥ 5% **and** |−$5,000| ≥ $4,800. Per §3 the disposition is: **classified {delta+explanation}/explained-benign AND flagged PROMINENT** in the dated daily parity handoff. Because it is benign (fully decomposed, wound-excluded), it does **NOT** restart the P5 clock and does **NOT** trigger the operator-visibility interrupt — Charter L81 interrupts fire on {wound-class, budget exhaustion, alarm anomaly} only, and this is none. Explicit note carried in the flag: **the magnitude meets-and-exceeds the original wound** ($5,000/6.17% vs the founding $4,800/~6%, Charter L23) — which is exactly why the prominence threshold was calibrated to $4,800 and why this rides the digest with emphasis for the operator's eye, benign classification notwithstanding. The prominence flag firing here is the rubric working as designed, not a wound.

### 4. Re-pin ruling (§3 re-pin rule) — GRANTED, as a coherent leg-2 generation

Both §3 re-pin preconditions are met (torn-read PASS + decomposition closes fully), and the snapshot is EXPLAINED — so re-pinning launders no wound (the §3 forbidden case does not apply). **RE-PIN GRANTED**, with this discipline:

- The exemplar **advances to a leg-2 generation as a coherent set**: served value **$75,985**, composition digest **`4a3aca96…`**, source frame `dataframe.parquet` sha256 **`cb79eaf5…`**, torn-read-clean provenance (build `16:12:41.349255Z` / saved `…501623Z` / write `16:12:42Z` / `row_count` 4191). Value, digest, and retained bytes advance **together** so the byte-rederivation determinism property (`test_fixture_parquet_bytes_rederive_the_pinned_constants`) holds at the new generation — never the constant without its bytes.
- **PII discipline (mirrors leg-1, this receipt L127-137):** the retained fixture bytes are the **PII-safe `(section, mrr)` projection** of the leg-2 frame, committed as the new determinism anchor; the full `cb79eaf5…` frame carries customer PII and is **not** committed (its sha + provenance preserve re-fetch capability only). The re-pin is contingent on that projection being committed and re-deriving $75,985 from its own bytes.
- The **S8-0 generation** ($80,985 / projection `614c9ab8…` / digest `4e711a7a…`) is **retained** in this receipt as the historical baseline, with the drift ledger ($80,985 →[−$5,000, decomposed]→ $75,985) connecting the two generations. The re-pin keeps the PT-03 fixture-replay gate testing against *current* prod reality rather than a stale baseline.
- The re-pin does **not** touch the WU-4 live-parity comparison (which references live v1 at each observation, not the fixture) — no laundering risk to the live leg.

### 5. UV-P-6 "attempt" semantics — advisory counsel to WU-2 (NOT a binding ruling)

**Budget unit = the Asana HTTP request at the client boundary. Count every request that crosses the Asana boundary — successes AND 429s/retries. Do NOT count S3 GET/LIST ops, and do NOT count hash-CLEAN freshness verifies that resolve without an Asana fetch.** Reasoning, anchored to P10:

- **P10's budget guards the 429-storm failure mode on record** (Charter L124-126, the 2026-07-27 storm). 429s are an **Asana-API** phenomenon; S3 GETs cannot produce the storm the budget exists to prevent. So the guarded surface — and thus the budget unit — is the Asana touch, not the S3 verify.
- **Count attempts, not successes — the load-bearing correction.** A 429-storm is composed of FAILED attempts (many requests, few/no successes). A success-only counter is **blind to the exact failure mode** the budget was built to catch. Therefore a 429 MUST charge the budget. The unit is *attempt at the HTTP boundary*, inclusive of retries.
- **Hash-CLEAN verifies are not prod touches.** FIX-1 hash-CLEAN gating means unchanged sections are not re-fetched (offer re-fetched only 4 sections across 2h). A verify that resolves by content-hash comparison without crossing the Asana boundary is not a PROD touch and must not charge the budget — else the guard is calibrated against phantom load and false-refuses legitimate fetches (violating the servable-provable direction of the north star).
- **Reject the S3-section-file proxy as the counter (critical).** Three monolithic pipelines write 0 section files yet each is ≥1 paginated Asana fetch: `section_count == 0 ≠ attempts == 0`. Instrument the **actual Asana client call site** (count at the HTTP boundary, pagination pages counted individually), never infer attempts from S3 artifact counts — the proxy under-counts precisely where a runaway could hide.
- **Cap sizing:** the numeric cap is a WU-2 build decision, but the probe's 2.0× ≈ 11,200/day recommendation is consistent with P10's runaway-guard-not-API-ceiling purpose; it should be pinned from the instrumented HTTP-boundary count, not the ~5,600 section-proxy upper bound.

### 6. Anomaly dispositions (awareness — bearing on future classifications)

1. **Manifest 34 vs 33 parquets** (empty `1201990715810462` "REVIEW OPTIMIZATION"): KNOWN, contained — the FIX-1 / `DEFECT-delta-path-empty-poison` surface. rows=0 → hash-CLEAN on an empty section IS complete verification and stamps (Charter L101-103, P6 floor-integrity). Contributes $0 to the served value; the 34-vs-33 is expected, **not a wound.**
2. **17 identical empty stamps** (`bd406b89…`): folded into this verdict as **positive determinism evidence** (W1 exclusion), per §1.
3. **Watermark schema +2 fields** (`population_degraded: false`, `population_min_rate: 0.8205…`): SCHEMA-SURFACE change, non-load-bearing for value → **benign per §1 B3** (proof-metadata that touches neither composition nor digest). **Registered for future classification:** these are new provability/completeness signals — if `population_degraded` ever flips TRUE or `population_min_rate` drops materially, that becomes W4-relevant (a provability signal that may require refusal). For THIS verdict `population_degraded: false` reads GREEN, consistent with benign. No leg-1 baseline exists to trend the rate; not over-read now.
4. **asset_edit/process cadence ≈52min < 3600s SLA:** UV-P-6 discharge data confirming 3600s adequacy (2×≈52min < 3600s clears the C8 "SLA ≥ 2× cadence" bar). This is C8-class governance data. Under P13 the adjudicator *may* stage a provisional→ratified lift as a non-door ruling, but it was not delegated in this dispatch and is **not staged unbidden** — available for a P13 staged re-ratification on the coordinator's/operator's word; the cadence evidence is sufficient.

### Provenance block

```
Ruling:        drift-verdict (O4 leg-2 recapture-drift) — {delta+explanation}, RE-PIN GRANTED
Adjudicator:   pythia-adjudicator (standing seat, substrate-v2-epoch S8-2 parity window)
Session:       session-20260803-220334-f2a75514
Main @:        5d62d0b8   Date: 2026-08-03
Ruling class:  P13 staged-auto (NON-DOOR) — auto-ratifies on inscription;
               standing 24h operator amend window (one word reverts);
               this provenance disclosed in-record (Charter L152-158).
Rubric:        RULING-pythia-s8-2-adjudication-rubric-2026-08-03.md (P13, 16:53:17Z), §3 + §1
Anchors:       Charter L70-85 (P5 + window law); L93-103 (P6 floor-integrity/FIX-1);
               L122-126 (P10 prod-touch/budget); L23 (founding wound magnitude);
               RECEIPT L160-415 (leg-2 evidence, own-hands read + arithmetic re-verified);
               RECEIPT L106-137 (leg-1 precedent + PII-projection discipline).
Door note:     Doors DP-1 / DP-4b remain operator-halting and outside this seat; no ruling
               here closes a door. Re-pin, prominence, and attempt-semantics counsel are
               all non-door. asset_edit/process SLA re-ratification available but not staged.
```

**pythia drift verdict: {delta+explanation} — explained-benign; clock NOT restarted; exemplar re-pins to the leg-2 generation under the PII-safe-projection discipline; prominent daily-handoff flag (no operator interrupt).**
