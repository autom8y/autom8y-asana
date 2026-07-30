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
