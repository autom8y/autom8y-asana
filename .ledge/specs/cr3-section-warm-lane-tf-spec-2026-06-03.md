---
type: spec
spec_id: cr3-section-warm-lane-tf-spec-2026-06-03
title: "TF spec — cache_warmer_section Lambda (SECTION ≤10-min warm lane)"
status: draft
decision_state: authored-not-ratified
rite: sre
date: 2026-06-03
initiative: cr3-fleet-data-plane-foundation-cutover
evidence_grade: moderate   # self-ref sre rite; live aws receipts are STRONG and cited inline.
reversible_only: true      # SPEC ONLY — no terraform apply, no deploy. Paired autom8y PR authored at §C/gate-5 land time.
grounding:
  - .ledge/decisions/ADR-section-10min-x-502-headroom-2026-06-03.md   # §B.2, §B.3.a, §B.4, §C step 6
  - src/autom8_asana/lambda_handlers/cache_warmer.py                  # prematerialize_section_set wiring
  - src/autom8_asana/core/project_registry.py                        # section_only_prematerialization_keys
  - src/autom8_asana/lambda_handlers/checkpoint.py                    # CACHE_WARMER_CHECKPOINT_PREFIX (:39)
land_dependency: "GATE-5 — paired autom8y (infra-TF) PR, authored at land time; this receiver PR is its prerequisite."
---

# TF spec — `cache_warmer_section` Lambda module (SECTION ≤10-min warm lane)

> **SPEC ONLY.** No `terraform apply`, no deploy, no value bump. The autom8y infra-TF repo
> (`gh slug autom8y/autom8y`) is NOT checked out in this worktree; this spec is the precise hand-off
> for the paired infra-TF PR authored at the §C gated-land pass (ADR §C step 6). This receiver PR
> (`sre/cr3-section-warm-lane`) is its **prerequisite** — the `prematerialize_section_set` flag and
> `section_only_prematerialization_keys` key source must merge to receiver `main` and bake into the
> shared image before the Lambda can route to the section branch.

## 0. Why a third Lambda (not an extended bulk/fast lane)

Per ADR §B.2: the SECTION freshness contract is **576s** (`caching.py:39 SECTION_DF_REFRESH_HOURS=0.16 × 3600`,
the `~10min`/`600s` gloss), binding for **all 34** warm-set GIDs' section arm — not just the 2 heaviest.
The live bulk warmer (`autom8-asana-cache-warmer-bulk`, `cron(0,30 * * * ? *)`, ~46-min inter-warm for the
heaviest GID) and the held 2-GID fast lane (#97, never deployed — `aws lambda get-function-configuration
autom8-asana-cache-warmer-fast` → ResourceNotFound, this session) both **miss** 576s. A dedicated
SECTION-arm-only lane over all 34 GIDs at a ≤10-min tick is the only shape that meets the contract at full
width (ADR §B.2 decision). It reuses the existing `_prematerialize_bulk_set_async` coroutine verbatim via a
third `key_source` + the `prematerialize_section_set` event flag — **no new build/merge/coverage code in the
Lambda**; the TF delta is one new function module mirroring `cache_warmer_bulk`.

## 1. Module: `cache_warmer_section` (mirror `cache_warmer_bulk`, PR #331 precedent)

Author a new TF module/instance `cache_warmer_section` mirroring the existing `cache_warmer_bulk` module
(PR #331 precedent — the bulk-warmer module that produced `autom8-asana-cache-warmer-bulk`). Same shared
container image, same handler entrypoint `autom8_asana.lambda_handlers.cache_warmer.handler`. Deltas only
where the section lane diverges:

| Knob | `cache_warmer_bulk` (LIVE — receipts below) | `cache_warmer_section` (THIS spec) | Rationale |
|------|---------------------------------------------|-------------------------------------|-----------|
| function name | `autom8-asana-cache-warmer-bulk` | `autom8-asana-cache-warmer-section` | distinct fn so concurrency/checkpoint are disjoint |
| `memory_size` | 2048 | **2048** | each Polars section build ≈ ~2GB resident (`cache_warmer.py:88-89`, `lifespan.py:232-234`); per-key frame released after `put_async`, so peak ≈ one frame — 2048 matches bulk |
| `timeout` | 900 | **900** | max Lambda; per-link wall-clock bounded by `ASANA_WARMER_KEY_BUDGET` chunking + self-invoke |
| `reserved_concurrent_executions` | 1 | **2** | **DEDICATED, DISJOINT pool** (ADR §B.3.a). ≥2 parallel links let the 34-key serial-≫10min sweep finish inside a 10-min tick. MUST NOT share bulk's `=1` — sharing would let section links starve the bulk self-continuation chain (disjoint-checkpoint-prefix #96 does NOT cover slot contention) |
| EventBridge schedule | `cron(0,30 * * * ? *)` (30-min) | **`cron(0/10 * * * ? *)`** (every 10 min) | meets the ≤576s/600s SECTION contract; the `/10` step fires at :00,:10,:20,:30,:40,:50 |
| `schedule_input` (EventBridge target `input`) | `{"prematerialize_bulk_set": true}` | **`{"prematerialize_section_set": true}`** | routes to the section branch in `handler` (`cache_warmer.py` — `prematerialize_section_set` evaluated FIRST in the if/elif, takes precedence over bulk) |
| env `CACHE_WARMER_CHECKPOINT_PREFIX` | `bulk/` (disjoint, #96) | **`section-fast/`** | disjoint `latest.json` so the section lane never reads/writes the bulk checkpoint (`checkpoint.py:39` `CHECKPOINT_PREFIX_ENV`; `:49-60` normalizes to one trailing slash). Single-writer safety per object holds because `reserved_concurrent_executions` is set AND the prefix is distinct |
| env `ASANA_WARMER_KEY_BUDGET` | (default 16) | (default 16, or tune at re-gate) | per-link key cap; `0`/negative disables chunking (`cache_warmer.py:92-111`) |

All OTHER env (ASANA_PAT/secret extension, ASANA_CACHE_S3_BUCKET, ASANA_CACHE_S3_PREFIX, ENVIRONMENT,
CLOUDWATCH_NAMESPACE, ASANA_WORKSPACE_GID, OTEL_* observability headers) mirror `cache_warmer_bulk` exactly.

### Live receipts for the bulk mirror (this session, STRONG)
- `aws lambda get-function-concurrency autom8-asana-cache-warmer-bulk` → `ReservedConcurrentExecutions=1`
- bulk `mem=2048`, `timeout=900`, rule `cron(0,30 * * * ? *)` ENABLED, LastMod `2026-06-03T09:06:11Z`
  (`describe-rule` / `get-function-configuration`, ADR §B.1 live-receipts block, lines 146-152)
- fast warmer `autom8-asana-cache-warmer-fast` → **ResourceNotFound** (#97/#338 NOT deployed)

## 2. Reserved-concurrency budget (the §C land MUST set, not assume)

ADR §B.3.a UV-P: the section pool of **2** must be carved from account unreserved-concurrency headroom,
disjoint from bulk's `=1` and the offer warmer's reservation. Account budget confirmed **971 unreserved**
(task brief; re-verify at land via `aws lambda get-account-settings` `AccountLimit.UnreservedConcurrentExecutions`
≥ 100 floor + 2 for this pool). Three-lane reservation at land: offer (existing) + bulk (`=1`) + section (`=2`).

## 3. IAM trio (mirror PR #335)

Mirror the three IAM policy attachments PR #335 wired for `cache_warmer_bulk`, scoped to the new
`autom8-asana-cache-warmer-section` execution role:
1. **s3-cache** — read/write on the cache bucket + `section-fast/` checkpoint prefix (`s3:GetObject`,
   `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` scoped to bucket/prefix).
2. **self-invoke** — `lambda:InvokeFunction` on its OWN function ARN (the `_self_invoke_continuation`
   continuation path, `timeout.py:107-113`, `InvocationType=Event`).
3. **cloudwatch-metrics** — `cloudwatch:PutMetricData` for the coverage/DMS namespaces
   (`WarmerKeysCovered/Enumerated`, `WarmerCheckpointCleared`, `Autom8y/AsanaCacheWarmer` DMS).

## 4. Coverage / observability (no new code; emitted over the section denominator)

The section lane reuses `_finish` (`cache_warmer.py`) and `emit_warmer_coverage_rate` over its OWN 34-key
denominator (NOT the bulk 68). Re-gate (ADR §C step 8) confirms `WarmerKeysCovered/Enumerated = (34,34)` and
`WarmerCheckpointCleared=1` on ≥2 consecutive ≤10-min cycles. The DMS success-timestamp
(`DMS_NAMESPACE="Autom8y/AsanaCacheWarmer"`) is shared; add a section-scoped Grafana panel if per-lane DMS
isolation is wanted (optional, not blocking).

## 5. Gate-5 land dependency + ordering (ADR §C)

This TF is a **gate-5 (§C step 6) land dependency** — a **paired autom8y (infra-TF) PR authored at land time**.
Ordering invariants (ADR §C):
- **Receiver PR first.** `sre/cr3-section-warm-lane` (this branch) must merge to receiver `main` and bake into
  the shared image BEFORE the Lambda routes to the section branch (the flag is a no-op until the image carries it).
- **Lane before knob.** Deploy the section Lambda (§C step 6) BEFORE calibrating
  `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` SECTION→576s (§C step 7) — calibrating first produces a section
  hard-reject/503 storm (ADR §B.4).
- **Headroom before lane.** The cpu/mem + `max_concurrent_builds` apply (§C step 5) precedes the lane deploy so
  the warm-miss/cold tail has build headroom.
- **IRREVERSIBLE (deploy).** Per ADR §C step 6; verify the section pool is disjoint from bulk's `=1` at plan time.

## 6. Acceptance for the paired TF PR (land-time checklist)

- [ ] `cache_warmer_section` module added, mirroring `cache_warmer_bulk` with the §1 deltas only.
- [ ] `reserved_concurrent_executions = 2`, disjoint from bulk `=1` (verified `get-account-settings` headroom).
- [ ] EventBridge rule `cron(0/10 * * * ? *)`, target `input = {"prematerialize_section_set": true}`.
- [ ] env `CACHE_WARMER_CHECKPOINT_PREFIX = "section-fast/"` (disjoint from bulk `bulk/`).
- [ ] IAM trio (s3-cache / self-invoke / cloudwatch-metrics) attached to the new role (PR #335 mirror).
- [ ] `terraform plan` shows ONE new function + rule + target + role/policies; NO change to the bulk module.
- [ ] Receiver `sre/cr3-section-warm-lane` already merged + image baked (prerequisite).
