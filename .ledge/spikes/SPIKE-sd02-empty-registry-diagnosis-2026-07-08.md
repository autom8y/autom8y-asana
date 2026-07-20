---
type: spike
subtype: defect-diagnosis
initiative: north-star-per-offer-economics
status: draft
phase: evidence-gathering
self_assessment_cap: MODERATE
date: 2026-07-08
defect: "prod dtenuta.account_status EMPTY (0 rows, MAX(synced_at)=NULL) despite push machinery present + flag default-ON"
repos:
  - autom8y-asana (push side, read-only)
  - autom8y-data (receive side, read-only)
live_probes: "read-only SELECTs via autom8y-data QueryConnection.from_settings() (direnv DB_*), 2026-07-08"
discipline: "G-DENOM honored: repo evidence cannot prove absence of a live EventBridge rule — that residual is routed to the operator runbook (§5). Self-assessment capped MODERATE (self-referential evidence grade rule)."
---

# SPIKE — SD-02 active-only registry EMPTY: root-cause diagnosis

## §0. Defect restated + live re-confirmation (2026-07-08)

Read-only probe via `QueryConnection.from_settings()` (DuckDB→MySQL attach, schema `dtenuta`):

| Probe | Result |
|---|---|
| `SELECT COUNT(*), MAX(synced_at) FROM account_status` | **`(0, NULL)`** — defect re-confirmed live |
| `SELECT COUNT(*) FROM chiropractors` | `1402` (FK target populated) |
| `information_schema.table_constraints` on `account_status` | **`PRIMARY KEY` + `uq_phone_vertical_pipeline` (UNIQUE) ONLY — NO FOREIGN KEY** |

The FK declared in migration 013 (`autom8y-data/alembic/versions/013_add_account_status_table.py:67-72`)
did **not** land in prod — consistent with `autom8y-data/.know/db.md:240` ("Deploy entrypoint strips
`FOREIGN KEY` clauses and sets `FOREIGN_KEY_CHECKS=0` before Alembic runs").

A zero-row table is itself diagnostic: the receiver's snapshot-replace only DELETEs when a new POST
arrives (`account_status_store.py:82-143`, transactional, rollback preserves prior rows), and the
sender **skips the POST entirely when entries are empty** (`gid_push.py:605-610`, returns True without
HTTP). So a table that was EVER populated would still hold rows. **Zero rows ⇒ no successful non-empty
push has EVER reached prod** since the table was created (migration 013, dated 2026-03-28 — the same
day the push seam was authored, commit `c5c0e156`).

## §1. Verdict table

| # | Hypothesis | Verdict | Evidence (file:line) |
|---|---|---|---|
| **H1** | Push never invoked in prod (push-bearing lane not on the warm cadence) | **SUPPORTED — primary root cause** | Sole call chain: `cache_warmer.handler` (`lambda_handlers/cache_warmer.py:1222`) → `_warm_cache_async` (`:706`) → `_push_account_status_for_completed_entities` (`:1086-1092`) → `push_status_to_data_service` (`push_orchestrator.py:186`). Grep proves NO other caller. The lanes that actually warm prod frames contain ZERO push calls: ECS in-process progressive preload (`api/lifespan.py:338-346` → `api/preload/progressive.py`, grep "push" = 0 hits), SWR serve-stale refresh (`cache/dataframe/dataframe_cache.py` `_trigger_swr_refresh`, PR #156 `376e1edd`), and BOTH Lambda prematerialization lanes (`cache_warmer.py:310-705`, grep "push" = 0 hits). The entity-type warm Lambda lane — the ONLY push-bearing lane — is paused/not scheduled: Trap-4 "warm lane paused — section warmer reserved=0 + schedule DISABLED" (`.ledge/handoffs/HANDOFF-releaser-to-sre-10xdev-cr3-gate2-release-sequencing-2026-06-08.md:32`); "The receiver has no `0 */4` warm lane" + prior "4h cron warm_all lane" comment ruled **FACTUALLY-FALSE** (`config.py:265-271`, PR #156 2026-06-25); observed offer-frame age drift ~70min (June) → **~4h50m stale on 2026-07-07** — impossible under any live scheduled warm cron. |
| H2 | Push fires but FAILS (auth / URL / payload / swallowed error) | **RULED OUT as proximate; latent risks named (§4)** | Receiver exists + is mounted: `autom8y-data/api/main.py:81,1705`; auth = S2S JWT dependency (`api/routes/account_status.py:41`). Payload matches field-by-field, both `extra="forbid"`-safe: sender envelope `source/entries/source_timestamp/entry_count` (`gid_push.py:612-617`) = `AccountStatusSyncRequest` (`_account_status_sync.py:70-102`); entry keys `phone/vertical/pipeline_type/account_activity/pipeline_section/stage_entered_at` (`gid_push.py:543-552`) = `AccountStatusEntry` (`:25-67`); sender pre-filters to active/activating (`gid_push.py:540`) = `AccountActivityEnum`. Failures are NOT swallowed silently at code level: `status_push_failed/timeout/error` logs (`gid_push.py:281-309`) + `StatusPushFailure` metric (`push_orchestrator.py:198`) + `StatusPushSkipped{skip_reason}` (`gid_push.py:54-65,584,593,602`). BUT no alarm is live: alarm IaC is "AUTHORED / UN-DEPLOYED / UN-ARMED" (`terraform/services/asana/observability_alarms.tf:8-21`) — so IF the lane ran and failed, nothing would page. Moot as proximate cause because the lane never runs (H1). |
| H3 | Enumeration legitimately yields zero | **RULED OUT as stated; zero-YIELD variant UNDETERMINED-but-not-the-cause** | `enumerate_active_offers` (`automation/workflows/active_offer_enumeration.py:34`) is NOT in the SD-02 path — it serves insights-export + grain-bridge leads (docstring `:1-13`). The SD-02 classifier is `extract_status_from_dataframe` (`gid_push.py:446-554`) via `SectionClassifier` registry (`models/business/activity.py:317-343`). The canonical `section` column exists in BASE_SCHEMA (`dataframes/schemas/base.py:83-89`) and `office_phone`/`vertical` in unit/offer/process schemas (`dataframes/schemas/unit.py:54,61`, `offer.py:19,28`, `process.py:18,27`). Real narrowing found: the Lambda's default warm set is the ENTITY list (unit, business, offer, contact, asset_edit…, `cache_warmer.py:719-721,795`), but `PIPELINE_TYPE_BY_PROJECT_GID` (`gid_push.py:413-424`) keys 10 PROJECT GIDs of which only unit's project `1201081073731555` corresponds to a default-warmed entity; the offer project `1143843662099250` is absent from the map (contributes nothing by design), and the 9 process-pipeline projects are not entity types in the default warm order. A unit-only push would still insert rows — so zero-yield does not explain 0 rows; it caps what the registry would contain once live. |
| H4 | Data-side write rejected/rolled back (FK, upsert bug, wrong table) | **RULED OUT (live evidence)** | Live probe: NO FK constraint on `account_status` (PRIMARY + UNIQUE only) — migration 013's declared FK (`013_add_account_status_table.py:67-72`) was stripped at deploy (`.know/db.md:240-242`); `chiropractors` populated (1402) anyway. Write path targets literal `INSERT INTO account_status` (`api/services/account_status_store.py:130-142`) in schema `dtenuta` (probe: `DATABASE()`=dtenuta, catalog `dtenuta_raw`) — same table measured empty. Transaction failure would raise → HTTP 500 → sender-visible `status_push_failed`, and rollback keeps prior rows (no wipe path). Latent: intra-snapshot duplicate grain vs `uq_phone_vertical_pipeline` would roll back the whole INSERT (§4-L3). |
| H5 | `STATUS_PUSH_ENABLED` explicitly OFF in prod deploy config | **UNDETERMINED (no in-repo evidence of OFF; moot while H1 holds)** | `_is_status_push_enabled()` default-ON confirmed (`gid_push.py:439-443`). No deploy config in EITHER repo sets it (only `docker-compose.override.yml:36` sets local `AUTOM8Y_DATA_URL`). autom8y-asana carries no service IaC — "IaC lands in the monorepo… `autom8y/autom8y` `terraform/services/asana/`" (`HANDOFF-account-status-recon-…-2026-06-08.md` §6), which is out of this spike's read scope → operator check (§5-R2). Even if set OFF, that path only executes when the Lambda lane runs — which it does not. |

## §2. Most probable root cause + causal chain

**The SD-02 status push is structurally dead code in prod: it is wired ONLY into the entity-type warm
flow of the cache-warmer Lambda, and prod cache warming does not run through that lane.**

Causal chain:

1. **2026-03-28**: seam authored (`c5c0e156` "feat(cache-warmer): push account status snapshots to
   autom8y-data") into `_warm_cache_async`'s post-warm tail (`cache_warmer.py:1086-1092`); table
   created the same day (migration 013). The push runs only after ALL entities complete
   (`cache_warmer.py:1064`); strict-mode early-returns (`:1008-1015`) exit before it.
2. Prod warming is served by lanes that never call the push: the ECS receiver's in-process
   progressive preload at startup (`lifespan.py:338`), SWR/hierarchy-gap refresh during serving, and
   the Lambda **prematerialization** lanes (bulk 30-min sweep + SECTION ≤10-min lane,
   `cache_warmer.py:310-705` — zero push references; each "runs on its own EventBridge schedule",
   `:1304-1312`).
3. The entity-type warm lane was paused during the CR-3 GATE-2 soak (Trap-4, 2026-06-08:
   "warm lane paused… schedule DISABLED") and never re-armed; by 2026-06-25 the corrected premise is
   on record — "the receiver has no `0 */4` warm lane" (`config.py:270`). The believed "~every 4h"
   push cadence is a documented conflation with `autom8y-account-status-recon-schedule` — the
   **ASR consumer-READ** cron (DISABLED, postmortem Symptom 1 = EXPECTED,
   `sre-dark-subsystem-postmortem.md:70-86`) — NOT an asana push lane. The receiver route's own
   docstring still carries the stale premise ("pushes snapshots every 4 hours",
   `autom8y-data/api/routes/account_status.py:7`).
4. Therefore `push_status_to_data_service` never executes → no POST ever reaches
   `/api/v1/account-status/sync` → 0 rows, `synced_at` NULL — for the table's entire ~3.5-month life.
5. Nothing surfaced it: every skip/failure path is non-blocking log+metric only; the AL-1..AL-4 alarm
   suite is AUTHORED/UN-DEPLOYED/UN-ARMED (`observability_alarms.tf:8`); and the one consumer that
   would have screamed (ASR three-way recon) has its schedule DISABLED (node-4 DEFERRED) — a
   dark-seam × dark-consumer × unarmed-alarm alignment (postmortem CF-4/CF-5/CF-6 pattern, same
   class as the 06-18 dark-subsystem).

Evidence grade: repo-forensic + live-DB probes = MODERATE (self-assessment cap). The single
unfalsified residual — "no EventBridge rule currently targets the entity-type warm lane" — is a
monorepo/console fact, discharged by §5-R1/R3.

## §3. Minimal repair shape (for the fix sprint — NOT implemented here)

1. **Give the push an execution home that actually runs.** Two honest options (pick one, don't do both):
   - **(a) Re-arm the Lambda lane**: EventBridge rule (monorepo IaC `terraform/services/asana/`)
     invoking `cache_warmer.handler` with the plain entity-type event (NOT
     `prematerialize_*`), on the ratified cadence; Lambda env must carry `AUTOM8Y_DATA_URL` +
     `AUTOM8Y_DATA_API_KEY` (+ leave `STATUS_PUSH_ENABLED` default-ON). Respect Trap-4/CR-3
     sequencing — the pause was deliberate; re-arming is an operator/IC decision.
   - **(b) Move the seam to the warm path prod actually uses**: invoke
     `_push_account_status_for_completed_entities` (or an equivalent post-warm hook) from the ECS
     progressive-preload/SWR completion seam. Smaller blast radius; no new cron; keeps FLAG-1
     layering in mind (`push_orchestrator.py:7-9`).
2. **Fix the denominator**: reconcile the warm entity set vs `PIPELINE_TYPE_BY_PROJECT_GID`
   (`gid_push.py:413-424`) — as wired, only `unit` rows can ever land; decide whether the 9
   process-pipeline projects are in-scope for SD-02 and warm/classify them accordingly.
3. **Prove it lands** (canary-signal-contract): deploy-gate on prod `StatusPushSuccess ≥ 1` within one
   cadence + a `SELECT COUNT(*) FROM account_status > 0` floor probe; deploy + arm AL-1
   (`StatusPushSkipped{url_absent,invalid_key}` graduate to PAGE post-baseline per
   `observability_alarms.SURFACED.md` L-1/L-2).
4. **Pre-enable latent checks** (from H2/H4 latents): (L1) E.164-conformance sweep of the office_phone
   population vs `OfficePhoneField` (one non-conforming phone 422s the WHOLE snapshot — entry_count
   integrity + `extra=forbid`); (L2) confirm Lambda-env secret resolution path for
   `AUTOM8Y_DATA_API_KEY` (`resolve_secret_from_env`, `gid_push.py:155-168`); (L3) dedup identical
   `(phone, vertical, pipeline_type)` grains within one snapshot before INSERT or the UNIQUE
   constraint rolls back the entire batch (`account_status_store.py:114-143`).
5. **Kill the stale premise in prose**: correct `autom8y-data/api/routes/account_status.py:7`
   ("every 4 hours") to the ratified cadence chosen in (1).

## §4. What only a prod log/console check can confirm — operator runbook (read-only)

The repo cannot prove a negative about live AWS state (G-DENOM). These discriminate the residuals:

- **R1 — Is ANY rule invoking the entity-type warm lane?**
  `aws events list-rules --region us-east-1 | grep -i -E 'warm|asana'` then for each candidate:
  `aws events list-targets-by-rule --rule <name>` (which Lambda + input payload — a payload with
  `prematerialize_bulk_set`/`prematerialize_section_set` is NOT the push lane) and
  `aws events describe-rule --name <name> --query State`.
  *Expected under H1: no ENABLED rule whose target input is the plain entity-type event.*
- **R2 — Lambda env (H5/H2 discharge):**
  `aws lambda get-function-configuration --function-name <cache-warmer fn>` → check presence of
  `AUTOM8Y_DATA_URL`, `AUTOM8Y_DATA_API_KEY` (ARN ref ok), `STATUS_PUSH_ENABLED` (values are
  secret-adjacent — inspect presence, do not paste; redact as [redacted]).
- **R3 — The teeth: has the push seam EVER executed?** Logs Insights, warmer log group(s), 30d+:
  `filter @message like /status_push_/` (matches `status_push_starting|success|failed|skipped`).
  *Expected under H1: ZERO matches (over a non-silent group — verify recordsScanned > 0 first).
  ANY match REFUTES H1 → pivot to H2/H3 with the matched event's reason/status_code.*
- **R4 — Metric side:** `aws cloudwatch list-metrics --namespace Autom8y/AsanaBridgeFleet` →
  does `StatusPushSkipped`/`StatusPushSuccess`/`StatusPushFailure` exist as a prod series at all?
  (Alarm tf comment says fixtures-only until the instrumented Lambda deploys, `observability_alarms.tf:19-20`.)
- **R5 — Receiver side (independent leg):** autom8y-data service logs, 30d:
  `filter @message like /account_status_sync_received/`. *Expected under H1: ZERO (no POST ever
  arrives). Any hit with a 4xx/5xx pairing refutes H1 in favor of H2/H4.*
- **R6 — Which lanes DO fire:** CloudWatch `AWS/Lambda Invocations` per warmer function name +
  `cache_warmer_handler_invoked` log events (the `event` field distinguishes lane per
  `cache_warmer.py:1293-1298`).

## §5. Live-probe appendix (read-only, 2026-07-08)

Method: `autom8y-data` venv, `direnv exec . python`, `QueryConnection.from_settings()` (env=local →
real MySQL attach as `dtenuta_raw`, schema `dtenuta`). SELECT-only. Results in §0. No .env files
opened; no credentials echoed.
