---
type: review
status: draft
---
# Storage/Config Topology Census — autom8-s3 × Writer × Readers × Env × IAM

> **Station**: arch topology-cartographer A1 (STORAGE/CONFIG TOPOLOGY CENSUS)
> **Date**: 2026-06-10 | **Code HEAD**: `origin/main` 8f9051b1 (working HEAD 3bbb9bc8)
> **Mode**: DESIGN-ONLY. Read-only aws/gh/git. No target mutated.
> **Grandeur anchor**: contract the storage/config topology so the wrong-prefix read becomes STRUCTURALLY UNADDRESSABLE. The triple-defect saga (hot-store phantom tier → `ASANA_CACHE_S3_PREFIX` overload → IAM/namespace drift) was ONE architecture defect wearing three masks. This census is the territory map.
> **G-PROVE**: every row carries a receipt (file:line on `origin/main` via `git show`, or pasted live AWS output captured this session). A row without a receipt is rejected.
> **G-DENOM**: denominator is the FULL namespace × principal matrix. Namespaces enumerated LIVE (not from briefing). Exclusions stated loudly at end.

---

## Live namespace denominator (the territory)

`aws s3api list-objects-v2 --bucket autom8-s3 --delimiter / --prefix asana-cache/` (live this session):
```
asana-cache/dataframes/   asana-cache/insights-frames/   asana-cache/name-gid-mappings/
asana-cache/project-frames/   asana-cache/task-cache/   asana-cache/task-data-cache-v3/
asana-cache/tasks/
```
Bucket root `aws s3api list-objects-v2 --bucket autom8-s3 --delimiter /` (live):
```
asana-cache/  asset-packages/  cache-warmer/  dataframes/  e2e-test-dataframes/
openai-cache/  serp-cache/  slack-cache/  sql-cache/  stripe-cache/  zipcode-cache/
```

**Briefing named 4 asana namespaces; live discovery found 11 autom8-s3 prefixes touching the asana subsystem (7 under `asana-cache/` + top-level `dataframes/` + `cache-warmer/` + `e2e-test-dataframes/`). The 5 undocumented `asana-cache/*` namespaces (`dataframes`, `insights-frames`, `name-gid-mappings`, `task-cache`, `task-data-cache-v3`) are the namespace-drift surface — mask #3.**

---

## THE CENSUS

Legend — Writer/Reader confidence: **High** = explicit code key-construction or live IAM grant; **Med** = directory/naming corroboration; **Low** = grep-only. "Monolith-owned" = NO writer in this repo's `src/` (grep returned empty — see receipt R-MONO).

| # | S3 namespace (live key) | WRITER (code path file:line / principal) | READERS (file:line) | Env var(s) feeding each side | IAM principal + grant | Receipts |
|---|---|---|---|---|---|---|
| 1 | `s3://autom8-s3/asana-cache/tasks/<gid>/{task,stories,subtasks,dependencies,attachments,modified_at,struc}.json` — per-task durable cache. **384,992 keys live.** | `S3CacheProvider.set_versioned` via `autom8_adapter.py:300` (`cache.set_versioned(gid, entry)`, `EntryType.TASK`), key built `s3.py:271` `{prefix}/tasks/{key}/{entry_type}.json`. **Prefix resolves to UNADORNED `asana-cache`** because the writer process runs as IAM user `autom8` (monolith warmer) constructing `S3CacheProvider` at default `S3Config.prefix="asana-cache"` (`s3.py:56`) — NOT via the env-overloaded ECS/Lambda settings. The writer does NOT read the polluted `ASANA_CACHE_S3_PREFIX`; default-prefix decoupling is the mechanism. **Confidence: High** (key construction + live object layout + bucket-policy super-principal). | (a) **The #120/#121 cure**: `null_number_recovery.py:495` `f"{_DURABLE_TASK_CACHE_PREFIX}/tasks/{gid}/task.json"` — RAW boto3 `get_object` (NOT `S3CacheProvider`), pinned prefix. (b) warmer-lane Lambdas (read-only grant, see IAM). | WRITE side: `S3CacheProvider` prefix = `s3_settings.prefix` IF env-constructed (`s3.py:137`) but monolith uses default `asana-cache`. READ side (cure): **pinned constant** `_DURABLE_TASK_CACHE_PREFIX="asana-cache"` (`null_number_recovery.py:148`), decoupled from `ASANA_CACHE_S3_PREFIX`. | Writers: IAM user `arn:aws:iam::696318035277:user/autom8` (bucket policy `s3:*` on whole bucket). Readers: warmer roles `S3DurableTaskCacheRead` Sid → `s3:GetObject` on `autom8-s3/asana-cache/tasks/*` (the #481 grant). | R-TASKS-LIVE, R-S3KEY-271, R-S3CFG-56, R-ADAPTER-300, R-CURE-148, R-CURE-495, R-IAM-WARMER, R-BUCKETPOL |
| 2 | `s3://autom8-s3/asana-cache/project-frames/...` — what the prod env var POINTS at. **2,243 keys live.** Subdirs are project-NAME segments (`business_offers/`, `units/`, `commission_💰/` …) NOT `<project_gid>`; plus a degenerate double-slash `project-frames//dataframes/<entity>:<gid>.parquet`. | **No writer in this repo's src targets `project-frames/`.** The env points ECS/Lambda `S3Settings.prefix` here, but the two code writers that read `s3.prefix` (`S3CacheProvider` task path; nothing else) do not write project-frames in practice — the live content is monolith-written name-keyed frames + a stray double-slash artifact. **Confidence: Med** (live layout + absence of repo writer). | Anything constructing `S3CacheProvider`/`S3DataFrameStorage` from `get_settings().s3.prefix` would READ here (the inert #120 cure DID: `{s3.prefix}/tasks/...` → `asana-cache/project-frames/tasks/...` = EMPTY namespace). | `ASANA_CACHE_S3_PREFIX = "asana-cache/project-frames/"` set in prod TF (3 warmer lanes + ECS). Read by `S3Settings` (`settings.py:420` env_prefix `ASANA_CACHE_S3_`, `prefix` field `settings.py:430` default `asana-cache`). | Warmer roles: `S3CacheAccess` Sid → GET/PUT/DELETE/Head on `autom8-s3/asana-cache/project-frames/*`. ECS task: full bucket. | R-PF-LIVE, R-TF-213, R-SETTINGS-420, R-SETTINGS-430, R-CURE-141 |
| 3 | `s3://autom8-s3/dataframes/<project_gid>/<entity>/...` — TOP-LEVEL v2 entity-keyed frames. **1,025 keys live.** Layout `dataframes/<gid>/{dataframe.parquet,manifest.json,gid_lookup_index.json}` + `dataframes/<gid>/<entity>/...`. | `S3DataFrameStorage` (`storage.py:303`), key prefix **default `"dataframes/"`** (`storage.py:342`), keys `_df_key`/`_watermark_key` `storage.py:~410`. Constructed by `section_persistence.py:1045` `S3DataFrameStorage(location=...)` WITHOUT prefix arg → inherits `"dataframes/"`. Bucket from `s3_settings.bucket` (NOT overloaded). The warmer `dataframe_cache.put_async`→`progressive_tier.put_async` (`dataframe_cache.py:691`) lands here. **Confidence: High** (explicit default-prefix constructor arg). | (a) receiver preload (`api/preload/legacy.py:125`, `progressive.py:291` construct `S3LocationConfig`). (b) **offline CLI** `dataframes/offline.py` — HARDCODED `f"dataframes/{project_gid}/.../sections/"` (`offline.py:49/53/59`), bucket from `ASANA_CACHE_S3_BUCKET` (`offline.py:~102`). (c) canary, eunomia freshness probes. | WRITE: prefix is a **constructor default `"dataframes/"`**, env-independent (the cure-by-construction). Bucket: `ASANA_CACHE_S3_BUCKET`. READ (offline): bucket env only; prefix hardcoded. | Warmer roles: `S3CacheAccess` → GET/PUT/DELETE on `autom8-s3/dataframes/*`. ECS task: full bucket. | R-DF-LIVE, R-STORAGE-342, R-SECPERS-1045, R-DFCACHE-691, R-OFFLINE-49, R-OFFLINE-102, R-PRELOAD-125, R-IAM-WARMER |
| 4 | `s3://autom8-s3/cache-warmer/checkpoints/{,bulk/,section-fast/}latest.json` — CheckpointManager. | `CheckpointManager` (`checkpoint.py:152`), prefix resolved `checkpoint.py:_default_prefix` (`checkpoint.py:50`), default `DEFAULT_PREFIX="cache-warmer/checkpoints/"` (`checkpoint.py:31`); bucket `_default_bucket` from `s3_settings.bucket` (`checkpoint.py:42`). **Confidence: High.** | CheckpointManager (same class read path); warmer self-continuation. | `CACHE_WARMER_CHECKPOINT_PREFIX` (env `checkpoint.py:39`) — per-lane DISJOINT prefix set in TF: bulk=`cache-warmer/checkpoints/bulk/` (TF:438), section=`cache-warmer/checkpoints/section-fast/` (TF:592); default lane unset→`cache-warmer/checkpoints/`. Bucket: `ASANA_CACHE_S3_BUCKET`. | Warmer roles: `S3CacheAccess` → GET/PUT/DELETE on `autom8-s3/cache-warmer/checkpoints/*`. | R-CKPT-LIVE, R-CKPT-31, R-CKPT-39, R-CKPT-50, R-TF-438, R-TF-592, R-IAM-WARMER |
| 5 | **Redis (the REAL hot tier)** — no S3 namespace; the actual production hot store. | `RedisCacheProvider` via `CacheProviderFactory._create_redis_provider` (`factory.py:185`), env `REDIS_HOST/PORT/PASSWORD/SSL` (`factory.py:188`). Selected when `settings.is_production` AND `settings.redis_available` (`factory.py:152-160`). `UnifiedTaskStore` wraps it (`factory.py:250`). **Confidence: High.** | `UnifiedTaskStore.get_versioned`/`get_batch`; webhooks read path (`webhooks.py:310`); hierarchy_warmer (`hierarchy_warmer.py:184`). | `ASANA_CACHE_PROVIDER` (memory/redis/tiered/none, `factory.py:83`); `REDIS_HOST` gate (`factory.py:118/128`). | (Redis = ElastiCache/VPC; not an S3 IAM principal — excluded from S3 grant matrix, noted loudly.) | R-FACT-185, R-FACT-152, R-FACT-250, R-WEBHOOK-310, R-HIER-184 |
| 5p | **PHANTOM TIER** — `TieredCacheProvider` S3 cold tier that config implies but does not exist. | `TieredConfig.s3_enabled` default **`False`** (`tiered.py:57`); cold path gated `if self.s3_enabled and self._cold is not None` (`tiered.py:168/211/264/302`). Factory comment: **"For Phase 1, tiered maps to Redis (S3 cold tier is Phase 3)"** (`factory.py:209`, again `:217`) → `_create_tiered_provider` returns `_create_redis_provider` (`factory.py:219`). So tiered NEVER instantiates an S3 cold tier in prod. **Confidence: High.** | Phantom — no production reader. The `null_number_recovery` docstring notes the cure path is "behind the global `ASANA_CACHE_S3_ENABLED` flag (unset on the warmer Lambda…)" (`null_number_recovery.py:35`). | `ASANA_CACHE_S3_ENABLED` → `TieredConfig.s3_enabled` (`tiered.py:49`). **Read ONLY inside `tiered.py`. Set NOWHERE** (not in TF, not in `.env/defaults`, not in secretspec defaults default-True). Config implies a read tier that does not exist = **mask #1**. | n/a (phantom). | R-TIERED-57, R-TIERED-49, R-TIERED-168, R-FACT-209, R-FACT-219, R-CURE-35, R-ENABLED-GREP |
| 6 | `s3://autom8-s3/asana-cache/task-cache/{tasks/<gid>/data.pkl, meta/deleted_tasks.pkl}` — legacy pickle task cache. **128,583 keys live.** | **Monolith-owned** — NO writer in this repo's src (grep empty, R-MONO). Pickle format + `task-cache/` prefix are not produced by any `origin/main` code path. **Confidence: Med** (live layout + repo-writer absence). | None in this repo (no reader references `task-cache/`). | none in this repo. | IAM user `autom8` (bucket `s3:*`). Warmer roles do NOT grant `task-cache/*` (only `project-frames/`, `dataframes/`, `checkpoints/`, `tasks/` read). | R-TASKCACHE-LIVE, R-MONO, R-IAM-WARMER, R-BUCKETPOL |
| 7 | `s3://autom8-s3/asana-cache/task-data-cache-v3/expensive_attrs/<m>/<yyyy>/<mm>/<gid>/{attachments,dependencies,dependents}.pkl` — v3 expensive-attr cache. **342 keys live.** | **Monolith-owned** — NO writer in this repo's src (grep empty, R-MONO). **Confidence: Med.** | None in this repo. | none in this repo. | IAM user `autom8`. NOT in any warmer role grant. | R-V3-LIVE, R-MONO, R-BUCKETPOL |
| 8 | `s3://autom8-s3/asana-cache/insights-frames/<index>/<report>/<window>/<date>/*.parquet` — insights export frames. **13,448 keys live.** | **Monolith / insights-export Lambda-owned** — NO writer in this repo's src (grep empty, R-MONO). Likely `autom8-asana-insights-export-lambda-role`. **Confidence: Med.** | None in this repo. | none in this repo. | `autom8-asana-insights-export-lambda-role` (separate principal; policy not dumped — see EXCLUSIONS). IAM user `autom8` (bucket). | R-INSIGHTS-LIVE, R-MONO, R-ROLES-LIST |
| 9 | `s3://autom8-s3/asana-cache/name-gid-mappings/{custom_field,project,section/<gid>}/mappings.pkl` — name↔gid resolution. **6 keys live.** | **Monolith-owned** — NO writer in this repo's src (grep empty, R-MONO). **Confidence: Med.** | None in this repo. | none in this repo. | IAM user `autom8`. | R-NAMEGID-LIVE, R-MONO, R-BUCKETPOL |
| 10 | `s3://autom8-s3/asana-cache/dataframes/<entity>:<gid>.parquet` — flat entity:gid frames UNDER asana-cache (distinct from top-level `dataframes/`). **6 keys live.** | **Monolith-owned / legacy** — NO writer in this repo's src writes `asana-cache/dataframes/` (repo writer targets top-level `dataframes/`, row 3). **Confidence: Low** (grep-only + layout). | None confirmed in this repo. | none. | IAM user `autom8`. | R-ACDF-LIVE, R-STORAGE-342 (repo writer targets top-level, not this), R-BUCKETPOL |
| 11 | `s3://autom8-s3/e2e-test-dataframes/...` — e2e test frames (root-level). | Test harness (not prod). **Confidence: Low.** | e2e tests. | likely test-scoped bucket/prefix override. | (test) | R-ROOT-LIVE |

---

## Env-var column — the OVERLOAD evidence (mask #2)

| Env var | Prod value / set-site | Code reader(s) | Overloaded? |
|---|---|---|---|
| `ASANA_CACHE_S3_PREFIX` | `"asana-cache/project-frames/"` — TF `terraform/services/asana/main.tf:213` (ECS), `:321` + `:436` (bulk lane) + `:590` (section lane). Live-verified this session. | (1) `S3Settings.prefix` field (`settings.py:430`, env_prefix `ASANA_CACHE_S3_` `settings.py:420`), default `"asana-cache"`. (2) `S3CacheProvider` via `s3_settings.prefix` (`s3.py:137`). (3) `scripts/warm_cache.py:78` `S3LocationConfig`. (4) Doc-only defaults disagree: `cache_warmer.py:18` says default `"cache/"`, `cache_invalidate.py:28` + `settings.py` say `"asana-cache"` — **doc-drift**. | **YES — the keystone overload.** One env var feeds BOTH the dataframe-storage prefix (`project-frames/`) AND would feed the task-cache prefix if any task writer read it. The #120 cure read `{s3.prefix}/tasks/` → `asana-cache/project-frames/tasks/` = EMPTY (mask #2). |
| `ASANA_CACHE_S3_BUCKET` | `"autom8-s3"` — TF `:212/:320/:435/:589/:1238`; `.env/defaults:21`; canonical per ADR-0002. | `S3Settings.bucket` (`settings.py:426` default `autom8-s3`); `offline.py:~102` direct `os.environ`; `_default_bucket()` `checkpoint.py:42`. | **NO** — single-purpose, single value. (Cure docstring explicitly relies on this: bucket NOT overloaded, only prefix.) |
| `ASANA_CACHE_S3_ENABLED` | **SET NOWHERE** (not TF, not `.env/defaults`, not secretspec). | ONLY `TieredConfig.s3_enabled` (`tiered.py:49`, default `False`). | **PHANTOM FLAG** — gates a Phase-3 S3 cold tier that does not exist (mask #1). Reader present, writer/setter absent. |
| `CACHE_WARMER_CHECKPOINT_PREFIX` | per-lane: bulk `"cache-warmer/checkpoints/bulk/"` (TF:438), section `"cache-warmer/checkpoints/section-fast/"` (TF:592); default lane unset. | `checkpoint.py:39` (`CHECKPOINT_PREFIX_ENV`), resolver `checkpoint.py:50`, default `"cache-warmer/checkpoints/"` `checkpoint.py:31`. | NO — per-lane disjoint by design (#96), single purpose. |
| `_DURABLE_TASK_CACHE_PREFIX` (the CURE's pin, not an env) | pinned constant `"asana-cache"` (`null_number_recovery.py:148`). | `null_number_recovery.py:495` builds `{const}/tasks/{gid}/task.json`. | N/A — deliberately a CONSTANT precisely to escape the `ASANA_CACHE_S3_PREFIX` overload. This is the existing partial-contract (one reader pinned; writers/other readers still env-coupled). |

---

## IAM column — live `get-role-policy` statements

**Three warmer-lane roles — `autom8-asana-cache-warmer-lambda-role`, `-bulk-lambda-role`, `-section-lambda-role` — carry BYTE-IDENTICAL `*-s3-cache` inline policies** (live-dumped this session, R-IAM-WARMER):
```json
{ "Statement": [
  { "Sid":"S3CacheAccess", "Effect":"Allow",
    "Action":["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:HeadObject"],
    "Resource":[ "arn:aws:s3:::autom8-s3/asana-cache/project-frames/*",
                 "arn:aws:s3:::autom8-s3/dataframes/*",
                 "arn:aws:s3:::autom8-s3/cache-warmer/checkpoints/*" ] },
  { "Sid":"S3BucketList", ... "s3:prefix":["asana-cache/project-frames/*","dataframes/*","cache-warmer/checkpoints/*"] },
  { "Sid":"S3DurableTaskCacheRead", "Effect":"Allow",
    "Action":["s3:GetObject"], "Resource":"arn:aws:s3:::autom8-s3/asana-cache/tasks/*" } ] }
```
The `S3DurableTaskCacheRead` Sid is the **#481 grant** — read-only `tasks/*` so the cure can GET the durable per-task copies. Note: warmer roles can write `project-frames/`, `dataframes/`, `checkpoints/` but ONLY read `tasks/` — they CANNOT write `task-cache/`, `task-data-cache-v3/`, `insights-frames/`, `name-gid-mappings/`.

**ECS task role — `autom8y-asana-service-ecs-task`, policy `autom8y-asana-service-task-s3`** (live-dumped, R-IAM-ECS):
```json
{ "Statement":[{ "Sid":"S3CacheAccess","Effect":"Allow",
  "Action":["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket","s3:HeadObject"],
  "Resource":["arn:aws:s3:::autom8-s3","arn:aws:s3:::autom8-s3/*"] }] }
```
**FULL-BUCKET `autom8-s3/*`** — no prefix scoping. The receiver/ECS can read/write ANY asana namespace (this is the IAM blast-radius the contract must narrow).

**Bucket policy — `autom8-s3`** (live, R-BUCKETPOL): grants `arn:aws:iam::696318035277:user/autom8` `s3:*` on `autom8-s3` + `/*`. **This IAM USER is the monolith super-principal** that writes `tasks/`, `task-cache/`, `task-data-cache-v3/`, `insights-frames/`, `name-gid-mappings/`. It is the writer for every "monolith-owned" row.

**Other discovered asana principals** (R-ROLES-LIST, policies NOT dumped — see EXCLUSIONS): `autom8-asana-insights-export-lambda-role`, `autom8-asana-conversation-audit-lambda-role`, `-conversation-audit-freshness-prober-role`, `autom8-asana-unit-reconciliation-lambda-role`, `autom8y-asana-service-ecs-execution`, `autom8y-asana-service-ecs-elb-canary`.

---

## EXCLUSIONS (stated loudly per G-DENOM)

1. **Non-asana S3 namespaces NOT censused** (out of asana scope): `asset-packages/`, `openai-cache/`, `serp-cache/`, `slack-cache/`, `sql-cache/`, `stripe-cache/`, `zipcode-cache/`. These belong to sibling autom8 subsystems; named here so the denominator is honest.
2. **IAM policy bodies NOT dumped** for: `autom8-asana-insights-export-lambda-role`, `autom8-asana-conversation-audit-lambda-role` (+ freshness-prober), `autom8-asana-unit-reconciliation-lambda-role`, `autom8y-asana-service-ecs-execution`, `-elb-canary`. Existence verified (R-ROLES-LIST); their exact S3 grants are UNCENSUSED. The insights-export role is the probable writer of namespace #8 — UNCONFIRMED. **Low-confidence rows #8/#10/#11 are turn-budget-bounded; a deeper pass should dump these policies.**
3. **Monolith repo source NOT inspected** — writers of rows #1,6,7,8,9,10 are attributed to the `autom8` IAM user / monolith by ABSENCE in THIS repo's src (R-MONO) + bucket-policy super-grant. The actual monolith write code path was not read (cross-repo, out of station scope). The `S3CacheProvider`-with-default-prefix attribution for row #1 is the strongest available repo-side inference, not a monolith-source receipt.
4. **Redis hot-tier internals** (key schema, TTLs, ElastiCache cluster topology) — not an S3 namespace; censused only at the selection/factory boundary.
5. **`scripts/warm_cache.py`** flagged as a 3rd `S3LocationConfig`/prefix reader (`warm_cache.py:54/78`) but its prefix-resolution path not fully traced.

---

## THE 3-MASK MAPPING (one defect, three masks)

| Mask | Saga symptom | Census row(s) exploited | Structural root |
|---|---|---|---|
| **#1 — hot-store phantom tier** | "config implies a read tier that does not exist" | **Row 5p** (`TieredConfig.s3_enabled=False`, `factory.py:209` "S3 cold tier is Phase 3", `ASANA_CACHE_S3_ENABLED` set nowhere). | The cache abstraction advertises an S3 cold tier (config field + env flag + tiered provider) that production never wires. A reader gated on `s3_enabled` is dead code that LOOKS live. |
| **#2 — `ASANA_CACHE_S3_PREFIX` overload** | wrong-prefix read: `{s3.prefix}/tasks/` → `asana-cache/project-frames/tasks/` = EMPTY | **Rows 1+2** (one env var, value `asana-cache/project-frames/`, feeds dataframe-storage prefix BUT the task writer/reader keyspace is `asana-cache/tasks/`). The #120 cure read through the polluted prefix; the #121 cure pinned `_DURABLE_TASK_CACHE_PREFIX` (row 1 reader) to escape it. | ONE env var carries TWO semantic prefixes (dataframe-frames vs task-cache). The decoupling is currently AD-HOC (storage.py default `"dataframes/"`; cure pins `"asana-cache"`) not contractual. |
| **#3 — IAM / namespace drift** | grant scoped to one namespace; data lives in another | **Rows 1,3,6,7,8,9,10** + IAM column. Warmer roles grant `project-frames/`,`dataframes/`,`checkpoints/` write + `tasks/` read — but the durable data the cure needs is at `tasks/` (read-only, late-granted via #481), and 5 live namespaces (`task-cache`, `task-data-cache-v3`, `insights-frames`, `name-gid-mappings`, `asana-cache/dataframes`) have NO repo writer and NO warmer-role grant — written by the `autom8` super-user under a full-bucket bucket policy. ECS task role is full-bucket `autom8-s3/*` (zero prefix scoping). | The namespace map (11 live prefixes) and the IAM grant map (4 scoped prefixes + 2 full-bucket super-grants) are MISALIGNED. The contract must make the namespace×principal matrix the single source of truth so a grant cannot point at a prefix the writer doesn't use, and a writer cannot land data in an ungranted/unmapped namespace.|

**Synthesis**: all three masks are the same root — **the storage prefix and the principal grant are not derived from a single canonical namespace registry.** `ASANA_CACHE_S3_PREFIX` is overloaded (mask #2) because there is no per-namespace prefix contract; the phantom flag survives (mask #1) because there is no liveness check binding config tiers to wired backends; the IAM drift persists (mask #3) because grants are hand-authored per role rather than projected from the namespace map. Contract the namespace × principal matrix → the wrong-prefix read becomes structurally unaddressable.

---

## RECEIPT INDEX (file:line on origin/main 8f9051b1, or LIVE this session)

- **R-TASKS-LIVE**: `aws s3 ls s3://autom8-s3/asana-cache/tasks/ --recursive | wc -l` → `384992`; sample keys `asana-cache/tasks/1143843662099260/{modified_at,stories,struc,task}.json` (live)
- **R-PF-LIVE**: `aws s3 ls .../project-frames/ --recursive | wc -l` → `2243`; CommonPrefixes name-keyed + stray `project-frames//dataframes/<entity>:<gid>.parquet` (live)
- **R-DF-LIVE**: top-level `aws s3 ls s3://autom8-s3/dataframes/ --recursive | wc -l` → `1025`; `dataframes/1143843662099250/{dataframe.parquet,manifest.json,gid_lookup_index.json,offer/...}` (live)
- **R-CKPT-LIVE**: `cache-warmer/checkpoints/{,bulk/,section-fast/}latest.json` (live `list-objects-v2`)
- **R-TASKCACHE-LIVE**: `task-cache/ --recursive | wc -l` → `128583`; `task-cache/tasks/<gid>/data.pkl`, `task-cache/meta/deleted_tasks.pkl` (live)
- **R-V3-LIVE**: `task-data-cache-v3/ | wc -l` → `342`; `expensive_attrs/<m>/<yyyy>/<mm>/<gid>/{attachments,dependencies,dependents}.pkl` (live)
- **R-INSIGHTS-LIVE**: `insights-frames/ | wc -l` → `13448`; `insights-frames/<index>/<report>/<window>/<date>/*.parquet` (live)
- **R-NAMEGID-LIVE**: `name-gid-mappings/{custom_field,project,section/<gid>}/mappings.pkl`, `| wc -l` → `6` (live)
- **R-ACDF-LIVE**: `asana-cache/dataframes/<entity>:<gid>.parquet`, `| wc -l` → `6` (live)
- **R-ROOT-LIVE**: bucket-root delimiter list includes `e2e-test-dataframes/` (live)
- **R-S3KEY-271**: `cache/backends/s3.py:271` `return f"{self._config.prefix}/tasks/{key}/{entry_type.value}.json"`
- **R-S3CFG-56**: `cache/backends/s3.py:56` `prefix: str = "asana-cache"`
- **R-S3-137**: `cache/backends/s3.py:137` `resolved_prefix = prefix if prefix is not None else s3_settings.prefix`
- **R-ADAPTER-300**: `cache/integration/autom8_adapter.py:300` `cache.set_versioned(gid, entry)` (`EntryType.TASK` at :256/:295)
- **R-CURE-148**: `dataframes/builders/null_number_recovery.py:148` `_DURABLE_TASK_CACHE_PREFIX = "asana-cache"`
- **R-CURE-495**: `null_number_recovery.py:495` `return f"{_DURABLE_TASK_CACHE_PREFIX}/tasks/{gid}/task.json"`
- **R-CURE-141**: `null_number_recovery.py:141` comment `{s3.prefix}/tasks/{gid}/task.json => asana-cache/project-frames/tasks/...` EMPTY
- **R-CURE-35**: `null_number_recovery.py:35` "behind the global ASANA_CACHE_S3_ENABLED flag (unset on the warmer Lambda…)"
- **R-STORAGE-342**: `dataframes/storage.py:342` `prefix: str = "dataframes/",`
- **R-SECPERS-1045**: `dataframes/section_persistence.py:1045` `storage = S3DataFrameStorage(location=location)` (no prefix arg)
- **R-DFCACHE-691**: `cache/integration/dataframe_cache.py:691` `durable = await self.progressive_tier.put_async(cache_key, entry)`
- **R-OFFLINE-49**: `dataframes/offline.py:49` `v2_prefix = f"dataframes/{project_gid}/{entity_type}/sections/"` (also :53 legacy, :59 scan-all)
- **R-OFFLINE-102**: `offline.py` `bucket = bucket or os.environ.get("ASANA_CACHE_S3_BUCKET")`
- **R-PRELOAD-125**: `api/preload/legacy.py:125` + `progressive.py:291` `S3LocationConfig(...)`
- **R-SETTINGS-420**: `settings.py:420` `env_prefix="ASANA_CACHE_S3_"`
- **R-SETTINGS-430**: `settings.py:430` `prefix: str = Field(default="asana-cache", ...)`
- **R-TIERED-57**: `cache/providers/tiered.py:57` `s3_enabled: bool = False`
- **R-TIERED-49**: `tiered.py:49` "Environment variable: ASANA_CACHE_S3_ENABLED"
- **R-TIERED-168**: `tiered.py:168/211/264/302` cold-path gated `if self.s3_enabled and self._cold is not None`
- **R-FACT-209**: `cache/integration/factory.py:209` + `:217` "For Phase 1, tiered maps to Redis (S3 cold tier is Phase 3)"
- **R-FACT-219**: `factory.py:219` `_create_tiered_provider` returns `_create_redis_provider(config)`
- **R-FACT-185/152/250**: `factory.py:185` `_create_redis_provider`; `:152-160` prod Redis selection; `:250` `UnifiedTaskStore(cache=cache_provider,...)`
- **R-WEBHOOK-310 / R-HIER-184**: `api/routes/webhooks.py:310` + `cache/integration/hierarchy_warmer.py:184` `get_versioned(gid, EntryType.TASK)`
- **R-ENABLED-GREP**: `git grep -n ASANA_CACHE_S3_ENABLED origin/main -- src/` → only `tiered.py` (reader) + `null_number_recovery.py:35` (comment). NOT in TF / `.env/defaults` / secretspec-default-true.
- **R-CKPT-31/39/50**: `lambda_handlers/checkpoint.py:31` `DEFAULT_PREFIX="cache-warmer/checkpoints/"`; `:39` `CHECKPOINT_PREFIX_ENV`; `:50` resolver
- **R-TF-213/438/592**: `autom8/terraform/services/asana/main.tf:213` `"ASANA_CACHE_S3_PREFIX"="asana-cache/project-frames/"`; `:438` bulk `CACHE_WARMER_CHECKPOINT_PREFIX="cache-warmer/checkpoints/bulk/"`; `:592` section `".../section-fast/"`. (Live-read this session.)
- **R-IAM-WARMER**: live `aws iam get-role-policy` × 3 warmer roles, `*-s3-cache` — byte-identical, incl. `S3DurableTaskCacheRead` Sid (pasted in IAM column)
- **R-IAM-ECS**: live `aws iam get-role-policy --role-name autom8y-asana-service-ecs-task --policy-name autom8y-asana-service-task-s3` → full-bucket `autom8-s3` + `autom8-s3/*` (pasted)
- **R-BUCKETPOL**: live `aws s3api get-bucket-policy --bucket autom8-s3` → `user/autom8` `s3:*` on bucket + `/*`
- **R-ROLES-LIST**: live `aws iam list-roles ... contains(asana)` → 12 roles enumerated (warmer×3, conversation-audit×2, insights-export, unit-reconciliation, ecs×3, model-dev, compile-asana)
- **R-MONO**: `git grep -lc "task-data-cache-v3|task-cache/|name-gid-mappings|insights-frames" origin/main -- src/` (excl. test) → EMPTY ⇒ no repo writer ⇒ monolith-owned
- **R-DOC-DRIFT**: `lambda_handlers/cache_warmer.py:18` doc default `"cache/"` vs `settings.py:430` / `cache_invalidate.py:28` `"asana-cache"`

---

**Artifact**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/storage-topology-census-2026-06-10.md`
**Confidence posture**: Rows 1-5/5p High-Med (explicit code + live IAM). Rows 8/10/11 Low (turn-budget-bounded; IAM bodies undumped per EXCLUSIONS #2). No target unit modified (read-only aws/gh/git).
