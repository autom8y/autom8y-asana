---
type: review
status: draft
---
# Storage-Config Consumer Graph (Station A2 — Dependency Analyst)

> **Initiative**: arch / storage-config-contraction
> **Grandeur anchor**: CONTRACT the storage/config topology so the wrong-prefix read becomes STRUCTURALLY UNADDRESSABLE.
> **Author**: arch dependency-analyst (DESIGN-ONLY, read-only)
> **Date**: 2026-06-10
> **autom8y-asana HEAD**: `8f9051b1` (origin/main)
> **autom8y (TF) origin/main**: `49972967`
> **autom8 (monolith)**: bare repo ABSENT at `/Users/tomtenuta/Code/a8/repos/autom8`. The Go monolith IS `/Users/tomtenuta/Code/a8` itself (`git@github.com:autom8y/a8.git`); Go-side edges probed directly (see Monolith Edge §). All asana-cache refs in `repos/` are nested python checkouts, not Go code.
> **Inherits**: A1 census (11 live namespaces under autom8-s3; writer = unadorned-default-prefix S3CacheProvider; #121 cure pins constant; TF sets ASANA_CACHE_S3_PREFIX="asana-cache/project-frames/").

---

## §0 The Overload, Restated (the contraction target)

ONE env var `ASANA_CACHE_S3_PREFIX` is consumed by TWO unrelated planes that are then read by THREE divergent code paths:

```
                          ASANA_CACHE_S3_PREFIX (TF = "asana-cache/project-frames/")
                                       │
              ┌────────────────────────┴───────────────────────────┐
              ▼                                                      ▼
   S3Settings.prefix  (settings.py:430, env_prefix ASANA_CACHE_S3_)  │  (env never reaches DF plane)
              │                                                      │
   ┌──────────┴───────────┐                              the DATAFRAME plane
   ▼                      ▼                               IGNORES the env entirely
 S3CacheProvider      [NO live runtime                    (S3DataFrameStorage prefix
 cold-tier prefix      reads s3.prefix —                   HARDCODED "dataframes/")
 (s3.py:151)           all 4 grep hits are                       │
   │                   #121 cure comments]                       ▼
   ▼                                                     dataframes/{gid}/... (LIVE,
 asana-cache/project-frames/{...}                        written 2026-06-10)
 (cold tier — but s3_enabled=False →
  STRUCTURALLY DEAD, never written)         null_number_recovery PINS "asana-cache" (line 148),
                                            decoupled from the polluted env → reads
                                            asana-cache/tasks/{gid}/task.json (LIVE, #121 cure)
```

Net: the env's nominal value (`asana-cache/project-frames/`) is consumed by NO live writer and NO live reader. The dataframe writers hardcode `dataframes/`; the task-cache reader hardcodes `asana-cache`; the cold-tier path that WOULD honour the env is dead. The env is a **decorative fossil pointing at a fossil namespace**.

---

## §1 Consumer Graph Table (every edge file:line-anchored)

Repos: **AS** = autom8y-asana (`8f9051b1`) · **TF** = autom8y terraform (`49972967`) · **M** = autom8 Go monolith (`/Users/tomtenuta/Code/a8`).

### 1A — `ASANA_CACHE_S3_PREFIX` / `S3Settings.prefix` edges

| # | Edge (config surface → reader) | file:line | Runtime | Classification | Break-on-split note |
|---|---|---|---|---|---|
| P1 | env → `S3Settings.prefix` field (`default="asana-cache"`) | AS `settings.py:430` (class `S3Settings` :404, env_prefix :421) | shared (any get_settings caller) | **TRUSTS-ENV** | The single env→setting binding. A split renames this field or adds siblings; every consumer below inherits the change. **HIGH** |
| P2 | `S3CacheProvider` prefix resolution `resolved_prefix = prefix if prefix is not None else s3_settings.prefix` | AS `cache/backends/s3.py:151` (resolves), `:140` (reads `get_settings().s3`) | ECS + warmer (whoever builds the cold tier) | **TRUSTS-ENV** (fallback) | Only reads env when NO `prefix=` kwarg passed. **But cold tier is never live** (see T-flag). **HIGH** confidence the code reads env; **HIGH** confidence it's dead at runtime. |
| P3 | bare `S3CacheProvider()` (no prefix arg) → default `asana-cache` writer of `asana-cache/tasks/` | AS `cache/providers/tiered.py:16` (docstring exemplar); **NO prod `S3CacheProvider(` instantiation in src/ or scripts/** (only s3.py:63 class def, backends/__init__.py:13 + tiered.py:16 docstrings) | ECS receiver (would be cold tier) | **DEFAULT-ONLY** | The A1 "MONOLITH writer at autom8_adapter.py:300, unadorned default prefix" is **REFUTED as a monolith edge**: the only unadorned `S3CacheProvider()` is the asana-repo cold-tier exemplar, and it is gated behind dead `s3_enabled` (see T-flag). No prod construction site found. **MEDIUM** (absence-of-evidence: grep-negative for `S3CacheProvider(` in src/scripts). |
| P4 | `get_settings().s3.prefix` direct read | AS `null_number_recovery.py:44, 135, 141, 493` | warmer-lane | **PINNED (not a read)** | **All 4 hits are COMMENTS/docstrings** explaining why the cure does NOT use `s3.prefix`. Zero live reads. The cure pins `_DURABLE_TASK_CACHE_PREFIX = "asana-cache"` at `:148`. **HIGH**. |
| P5 | TF env → ECS receiver/api container | TF `terraform/services/asana/main.tf:222` (owning `module "service"` :88), bucket :221 | ECS (receiver) | **TRUSTS-ENV (sets, unused by DF plane)** | The receiver's S3DataFrameStorage ignores it; only the (dead) cold tier would honour it. Splitting can DROP this env from the receiver with no behavioral change. **HIGH**. |
| P6 | TF env → `cache_warmer` Lambda | TF `main.tf:330` (owning `module "cache_warmer"` :292), bucket :329 | warmer-lane (main) | **TRUSTS-ENV (sets, unused by DF plane)** | Warmer persists via `dataframes/` default; env unread by DF path. **HIGH**. |
| P7 | TF env → `cache_warmer_bulk` Lambda | TF `main.tf:445` (owning `module "cache_warmer_bulk"` :398), bucket :444 | warmer-lane (bulk) | **TRUSTS-ENV (sets, unused by DF plane)** | Same. **HIGH**. |
| P8 | TF env → `cache_warmer_section` Lambda | TF `main.tf:601` (owning `module "cache_warmer_section"` :522), bucket :600 | warmer-lane (section, PAUSED reserved_conc=0) | **TRUSTS-ENV (sets, unused by DF plane)** | Same. **HIGH**. |

> **Key structural fact**: the `ASANA_CACHE_S3_PREFIX` env is set at **4 sites** (P5–P8) but read by **only the dead cold-tier path** (P2/P3). **No live reader consumes it.** A1's "4 env sites" is confirmed (the 5th bucket env at `main.tf:1515`/`unit_reconciliation` carries NO prefix).

### 1B — `S3CacheProvider` prefix-arg provenance

| Site | Where prefix comes from | file:line | Note |
|---|---|---|---|
| `__init__(prefix=None)` → resolves `s3_settings.prefix` | env via S3Settings | AS `s3.py:127` (sig), `:151` (resolve) | Only path that touches env |
| `S3Config(bucket="my-cache-bucket")` | no prefix → S3Config default | AS `backends/__init__.py:13` (docstring) | exemplar only |
| `cold_tier=S3CacheProvider()` | bare → env-default `asana-cache` | AS `tiered.py:16` (docstring) | exemplar only; **no prod call** |

### 1C — `ASANA_CACHE_S3_BUCKET` edges (assert NOT overloaded)

| # | Reader | file:line | Runtime | Classification |
|---|---|---|---|---|
| B1 | `S3Settings.bucket` (`default="autom8-s3"`) | AS `settings.py:426` | shared | TRUSTS-ENV |
| B2 | `get_settings().s3.bucket` readers | AS `legacy.py:126`, `progressive.py:292`, `cache/dataframe/factory.py:191,252`, `cache_warmer.py:380,682`, `checkpoint.py:46`, `null_number_recovery.py:522,622` | ECS + warmer | TRUSTS-ENV |
| B3 | `os.environ.get("ASANA_CACHE_S3_BUCKET")` direct | AS `scripts/warm_cache.py:69`, `dataframes/offline.py:102` | CLI / warmer | TRUSTS-ENV |
| B4 | TF bucket env (all = `"autom8-s3"`) | TF `main.tf:221, 329, 444, 600, 1515` + `modules/asana-cache-warmer/main.tf:45` | ECS + 4 lambdas | TRUSTS-ENV |

> **BUCKET NOT-OVERLOADED — ASSERTED.** Every site resolves to the single value `autom8-s3`; the bucket selects ONE bucket, the prefix selects the namespace within it. The overload is **prefix-only**. The #121 cure relies on this (`null_number_recovery.py:147` comment: "the BUCKET env is NOT [overloaded]"). **HIGH** confidence.

### 1D — Dataframe-side prefix plumbing (`dataframes/`, storage.py:342 default)

| # | Edge | file:line | Runtime | Classification | Break-on-split note |
|---|---|---|---|---|---|
| D1 | `S3DataFrameStorage.__init__(prefix="dataframes/")` DEFAULT | AS `dataframes/storage.py:342` | all DF consumers | **DEFAULT-ONLY (hardcoded, ignores env)** | The DF plane's prefix is a Python default literal, NOT env-bound. The env override never reaches it. **HIGH**. |
| D2 | `S3DataFrameStorage(location=..., retry_orchestrator=...)` — **no prefix arg** | AS `api/preload/legacy.py:130` | ECS (preload) | DEFAULT-ONLY | inherits `dataframes/`. **HIGH**. |
| D3 | `S3DataFrameStorage(location=..., retry_orchestrator=...)` — **no prefix arg** | AS `api/preload/progressive.py:298` | ECS (preload) | DEFAULT-ONLY | inherits `dataframes/`. **HIGH**. |
| D4 | `S3DataFrameStorage(location=location)` — **no prefix arg** | AS `dataframes/section_persistence.py:1050` | ECS + warmer | DEFAULT-ONLY | inherits `dataframes/`. **HIGH**. |
| D5 | `S3DataFrameStorage(location=location, retry=...)` — **no prefix arg** | AS `scripts/warm_cache.py:82` | CLI / warmer | DEFAULT-ONLY | inherits `dataframes/`; reads BUCKET (`:69`) + REGION (`:80`) from env but **never reads PREFIX env**. **HIGH**. |
| D6 | `SectionPersistence.__init__(prefix="dataframes/")` DEFAULT | AS `section_persistence.py:295` (also factory `:1023`, returns `:1052`) | ECS + warmer | DEFAULT-ONLY | Second hardcoded `dataframes/`. **HIGH**. |
| D7 | offline reader scans `dataframes/{gid}/...` (v2 + legacy) | AS `dataframes/offline.py:7-14, 83-87` (paths), `:102` (bucket from env) | CLI (`metrics`) / offline | DEFAULT-ONLY (path hardcoded) | Reads `dataframes/`; bucket from BUCKET env. **HIGH**. |
| D8 | S3LocationConfig (bucket/region/endpoint ONLY — no prefix field) | AS `config.py:419` (class), `:433` (bucket), `:438` (from_env) | all | n/a | **S3LocationConfig carries NO prefix** — prefix lives only on the storage/persistence objects. Confirms the env→DF disconnect is structural, not incidental. **HIGH**. |

> **Dataframe plane verdict**: the live `dataframes/` namespace is governed by **two hardcoded Python defaults** (`storage.py:342`, `section_persistence.py:295`) and is **completely disconnected from `ASANA_CACHE_S3_PREFIX`**. Eight DF consumers, zero env reads of prefix. The env can be deleted from every DF-running lane with no effect.

### 1E — `ASANA_CACHE_S3_ENABLED` (the phantom flag)

| # | Edge | file:line | Classification |
|---|---|---|---|
| E1 | docstring names env `ASANA_CACHE_S3_ENABLED` | AS `tiered.py:49` | **PHANTOM (doc only)** |
| E2 | `s3_enabled: bool = False` on `@dataclass TieredConfig` | AS `tiered.py:42` (`@dataclass`), `:57` (field) | **NOT env-bound** — plain dataclass, NOT BaseSettings; no env_prefix, no getenv. The docstring "Environment variable: ASANA_CACHE_S3_ENABLED" is **FALSE**. |
| E3 | all gating reads of `s3_enabled` | AS `tiered.py:120,126,168,211,264,302,364,430,492` | reads dataclass field, never env |
| E4 | `TieredConfig(s3_enabled=True)` constructions | AS `tiered.py:13,90` (docstrings), `tests/unit/cache/test_tiered.py:104,111,118,191,219,248,278`; **ZERO in src/ or scripts/** | **No prod setter.** Prod path is `self._config = config or TieredConfig()` (`tiered.py:116`) → always `s3_enabled=False`. |
| E5 | #121 comment treats it as global flag "unset on the warmer" | AS `null_number_recovery.py:35, 385` | the cure ASSUMES the flag is effectively-off everywhere |
| E6 | docs imply it works | AS `docs/guides/cache-system.md:140` (`s3_enabled=True`) | stale doc |

> **PHANTOM-FLAG VERDICT (HIGH)**: `ASANA_CACHE_S3_ENABLED` is never read from the environment by any code. `TieredConfig` is a plain `@dataclass` (`tiered.py:42`), `s3_enabled` defaults `False` (`:57`), and **no production site constructs `TieredConfig(s3_enabled=True)`** — only tests and docstrings. The S3 cold tier (P2/P3 → `asana-cache/...`) is therefore **structurally dead**: even if the env were set, no pydantic-settings binding would consume it, and the prod path always uses `TieredConfig()`. Setting `ASANA_CACHE_S3_ENABLED=true` in TF would be inert. This is why A1 saw the cold-tier writer as the source of `asana-cache/tasks/` keys yet the env never matters — the live `asana-cache/tasks/` writer is the **ECS receiver's durable-first path** (per #121 IAM comment `main.tf:1218`), NOT the tiered cold-tier.

---

## §2 Blast Radius per Split Option

Counts are of **distinct edges in this graph** (file:line sites), grouped by repo and runtime.

### O-A — Env split: `ASANA_TASK_CACHE_S3_PREFIX` + `ASANA_DATAFRAME_S3_PREFIX` (back-compat defaults)

| Repo | Sites touched | Files | Runtimes |
|---|---|---|---|
| AS (settings) | `settings.py:404-431` add 2 fields (task-prefix default `asana-cache`, df-prefix default `dataframes/`) | 1 | shared |
| AS (cold tier) | `s3.py:151` repoint to task-prefix field (P2) | 1 | ECS |
| AS (DF plane) | `storage.py:342` + `section_persistence.py:295,1023` repoint default to df-prefix field (D1/D6) | 1 (2 sites) | ECS + warmer + CLI |
| AS (#121 cure) | `null_number_recovery.py:148` — CAN now read `task-prefix` field instead of pinned constant (the overload it was decoupling-from disappears) | 1 | warmer |
| TF | rename env at `main.tf:222,330,445,601` → both new vars (or set df var; drop task var on lanes that don't write tasks) | 1 | ECS + 3 lambdas |
| **TOTAL O-A** | **~9 edge sites** | **~5 files** (4 AS + 1 TF) | ECS, warmer×3, CLI |

- **Import-time vs call-time**: All AS env reads are **call-time** (`get_settings()` is lazily resolved; `S3DataFrameStorage` defaults bind at call-time on each construction). No import-time env read on the prefix path → **no deploy-order hazard for code**. TF env changes are deploy-time; back-compat default (df-prefix defaults to `dataframes/`) means **a TF apply that drops the old var still leaves the DF plane correct** (it never read it). **The hazard is the cold-tier task-prefix**: if O-A repoints `s3.py:151` to a new `ASANA_TASK_CACHE_S3_PREFIX` whose back-compat default is `asana-cache`, the dead cold tier stays dead (fine) and the #121 pin can be retired safely. **Lowest-risk option for the live planes.**

### O-B — `StorageNamespaceContract` SSOT module (settings + TF + IAM + alignment-test derive from it)

| Repo | Sites touched | Files | Runtimes |
|---|---|---|---|
| AS (new module) | new `storage_namespace.py` declaring TASK_CACHE=`asana-cache`, DATAFRAME=`dataframes/`, PROJECT_FRAMES_FOSSIL=`asana-cache/project-frames/` (quarantined), CHECKPOINTS=`cache-warmer/checkpoints/` | 1 (new) | n/a |
| AS (settings) | `settings.py:430` derive `S3Settings.prefix` default from contract (or deprecate) | 1 | shared |
| AS (cold tier) | `s3.py:151` derive from contract.TASK_CACHE (P2) | 1 | ECS |
| AS (DF plane) | `storage.py:342`, `section_persistence.py:295,1023` derive from contract.DATAFRAME (D1/D6) | 1 (2 sites) | ECS + warmer + CLI |
| AS (#121 cure) | `null_number_recovery.py:148` `_DURABLE_TASK_CACHE_PREFIX` = contract.TASK_CACHE (retires the hand-pinned literal) | 1 | warmer |
| AS (offline) | `offline.py:7-14,83-87` derive `dataframes/` from contract.DATAFRAME (D7) | 1 | CLI |
| TF | `main.tf:222,330,445,601` (prefix) + `:221,329,444,600,1515` (bucket) + IAM `:1197,1210,1227` derive from a shared TF local / generated var | 1 | ECS + 4 lambdas + IAM |
| AS (alignment test) | new test asserts settings/TF/IAM all agree with the contract (closes the divergence class structurally) | 1 (new) | CI |
| **TOTAL O-B** | **~14 edge sites** | **~8 files** (6 AS + 1 TF + 1 test) | ECS, warmer×3, CLI, IAM, CI |

- **Import-time hazard**: the SSOT module would be imported at module-load by settings + storage + recovery. As long as it's pure constants (no env at import) there's **no deploy-order hazard**. The cross-repo derivation (TF deriving from a Python contract) is the **hard edge** — TF can't import Python at plan-time; requires either a generated `.tf`/`.tfvars` from the contract (a build step) or a duplicated-but-test-asserted literal. The alignment-test is what makes the overload **structurally unaddressable** (the Grandeur anchor): a future drift fails CI. **Highest contraction value, highest cross-repo coordination cost.**

### O-D — Status-quo + lint

| Repo | Sites touched | Files | Runtimes |
|---|---|---|---|
| AS (lint) | a grep-lint forbidding `get_settings().s3.prefix` as a live read (only the #121 comment refs exist today; lint pins that) + forbidding new `S3DataFrameStorage(prefix=...)` overrides | 1 (CI rule) | CI |
| TF | none (leave the 4 fossil env sites) | 0 | n/a |
| **TOTAL O-D** | **~1 edge site** | **1 file** | CI |

- **Import-time vs call-time**: N/A (no runtime change). Leaves the env overload live but documented + lint-guarded. The fossil env (`project-frames/`) and phantom flag persist; the #121 pin stays load-bearing. **Lowest cost, zero contraction** — the wrong-prefix read remains *addressable* (a future caller could still pass `prefix=get_settings().s3.prefix` and re-pollute), only discouraged.

> **Cross-option note for remediation-planner**: O-A and O-B both make the DF plane's prefix env-derived (today it's a hardcoded literal divorced from env). That is a behavior CHANGE on the live `dataframes/` plane — back-compat defaults must equal `dataframes/` exactly or the live v2 namespace moves. The safest contraction touches the cold-tier/task-prefix side (dead + #121-pinned) FIRST and leaves `dataframes/` literal until an alignment test exists.

---

## §3 The Monolith Edge

**Does SEAM-2 / the monolith read ANY of these envs or namespaces beyond writing `tasks/`?**

- **Go monolith (`/Users/tomtenuta/Code/a8`, `autom8y/a8`)**: probed `cmd/ internal/ pkg/ terraform/ compose/ config/` for `asana-cache` / `ASANA_CACHE_S3` — **ZERO hits** except `pkg/manifest/testdata/manifest.yaml:210` (`asana-cache-warmer`, an infra resource name, not a namespace read). **The Go monolith reads NONE of these envs and accesses NONE of these S3 namespaces.** **HIGH** (grep-negative across the proper monolith tree, excluding nested python `repos/`).
- **A1's "MONOLITH writer at autom8_adapter.py:300"**: **REFUTED.** `cache/integration/autom8_adapter.py` is a **Python module inside autom8y-asana**, not the Go monolith. Its line-300 region is `warm_project_tasks` / `create_autom8_cache_provider` (`:89`), which builds a **Redis** provider (`create_autom8_cache_provider` → `RedisCacheProvider`, `:136-170`), not the S3 task-cache writer. The actual `asana-cache/tasks/` writer is the **ECS receiver's durable-first path** under its full-bucket S3 grant (per TF IAM comment `main.tf:1218`: "written by the ECS receiver under its full-bucket grant").
- **SEAM-2 monolith consumers (offer/unit frame reads, receiver_query path)**: **UV-P** — these live in the Go monolith's runtime consumers of the `dataframes/` parquet plane. No Go-side code reads `ASANA_CACHE_S3_*` or constructs S3 keys for these namespaces (grep-negative). If SEAM-2 consumers read `dataframes/` they do so via the **asana service's HTTP API** (the ECS receiver), not by reading S3 directly — so they are **transitively** coupled to the `dataframes/` prefix through the receiver, NOT directly to the env.

`[UV-P: Go-monolith SEAM-2 consumers (offer/unit) read the dataframes/ plane only via the asana receiver HTTP API, not via direct S3 access | METHOD: bash-probe (grep-negative for asana-cache/ASANA_CACHE_S3/dataframes-key-construction across a8 cmd/internal/pkg) | REASON: confirming the receiver-mediated coupling requires reading the Go HTTP-client call sites, out of A2 scope; structure-evaluator/remediation-planner should confirm the receiver is the sole S3 boundary]`

> **Monolith-edge verdict (HIGH)**: The Go monolith has **NO direct edge** to any storage-config surface in scope. Every cross-repo coupling to these namespaces is **mediated by the asana ECS receiver**. A split is **monolith-invisible**: changing `ASANA_CACHE_S3_PREFIX` semantics breaks nothing in `a8` directly. Blast radius for the monolith = **0 direct sites** (transitive only, via the receiver API contract, which does not expose prefixes).

---

## §4 Fossil-or-Live Verdict: `asana-cache/project-frames/`

**VERDICT: WRITE-ORPHANED FOSSIL (HIGH confidence).**

Evidence:
1. **No code path writes it.** `git grep "project-frames"` across `src/` + `scripts/` returns **only comments** in `null_number_recovery.py:46,47,138,140,141` (the #121 cure documenting why the env is overloaded). Zero writers, zero readers. **HIGH** (grep-negative for live code).
2. **The env that names it reaches no live writer.** Edges P5–P8 set `ASANA_CACHE_S3_PREFIX="asana-cache/project-frames/"`, but the only consumer (P2 cold-tier `s3.py:151`) is dead (E-flag: `s3_enabled=False`, no prod setter). The DF plane that *could* have written it ignores the env (D1–D6, hardcoded `dataframes/`).
3. **Live-object probe (read-only `aws s3 ls`)**: newest key under `asana-cache/project-frames/` is dated **`2025-10-02 17:14:16`** (e.g. `videography_services/section_group/all/1759418055.52324.parquet`). **~8 months stale** as of 2026-06-10. The namespace is keyed by **entity-name segments** (`videography_services/section_group/...`) — a **v1/legacy schema**, distinct from the live `dataframes/` plane which is keyed by **project GID** (`dataframes/{gid}/sections/...`, newest `2026-06-10 17:03:46` — written today).
4. **Schema divergence confirms it's a different (abandoned) layout**, not a staging area for the live plane: project-frames = `{entity_name}/{section_type}/...`; dataframes = `{project_gid}/sections/{section_gid}.parquet` (storage.py:330-342). They are not two views of the same writer.

> The 2,243 live keys in `asana-cache/project-frames/` (A1) are **stranded v1 artifacts** from a pre-SEAM storage layout, kept alive only by the IAM grants (TF `main.tf:1197,1210`) and the decorative env (P5–P8). Nothing reads or refreshes them. They are safe to quarantine; the contraction's job is to ensure no future code can be pointed at them via the overloaded env.

---

## §5 Unknowns

### Unknown: Live `asana-cache/tasks/` writer identity (cold-tier vs receiver durable-first)
- **Question**: Which exact code path writes the 385k live `asana-cache/tasks/{gid}/task.json` keys — the (apparently dead) tiered cold tier, or a receiver durable-first write distinct from `S3CacheProvider`?
- **Why it matters**: The #121 cure reads this namespace (`null_number_recovery.py:148`). If the writer is also env-decoupled, O-A/O-B must preserve `asana-cache` exactly or break the cure.
- **Evidence**: `tiered.py` cold tier is dead (E-flag); yet TF IAM `main.tf:1218` comment says tasks are "written by the ECS receiver under its full-bucket grant" — implying a writer OUTSIDE the tiered/S3CacheProvider path that this A2 census did not locate in src/ (no `S3CacheProvider(` prod site, no other `asana-cache/tasks` write found).
- **Suggested source**: receiver request-handler / durable-first write path (likely `cache/dataframe/warmer.py` or a receiver endpoint); structure-evaluator or a follow-up grep for `tasks/{` / `task.json` writers.

### Unknown: TF↔Python prefix derivation under O-B
- **Question**: Can TF derive the namespace contract from the Python SSOT without a build-step (codegen), or must O-B accept a duplicated-but-test-asserted literal?
- **Why it matters**: Determines whether O-B's "structurally unaddressable" claim holds across the repo boundary or degrades to "test-guarded duplication."
- **Evidence**: TF has no plan-time Python import; the 4 prefix env sites + IAM are literals today.
- **Suggested source**: remediation-planner (cross-repo SSOT mechanics); not an A2 decision.

### Unknown: `S3Settings.prefix` deprecation safety
- **Question**: If O-A/O-B deprecates the env-bound `S3Settings.prefix` (P1) entirely, does anything outside this repo's src/scripts/tests read it (e.g., a sibling python service importing `autom8_asana.settings`)?
- **Why it matters**: A cross-repo importer of `get_settings().s3.prefix` would be a hidden edge.
- **Evidence**: In-repo, the only live consumer is the dead cold tier (P2); SEAM-2 unit-econ worktree (`repos/seam2-unit-econ`) has its own checkout of settings — unverified whether it reads `.s3.prefix` live.
- **Suggested source**: cross-repo grep of sibling python services importing `autom8_asana.settings`; routed to remediation-planner.

---

## §6 Confidence Summary

| Finding | Confidence | Basis |
|---|---|---|
| Prefix env consumed by NO live reader | HIGH | manifest+grep: all 4 `s3.prefix` hits are comments; DF plane hardcodes |
| `dataframes/` plane env-disconnected (hardcoded) | HIGH | `storage.py:342`, `section_persistence.py:295` defaults; no prefix arg at any of 5 construction sites |
| `ASANA_CACHE_S3_ENABLED` is a phantom flag | HIGH | `TieredConfig` is `@dataclass` (`:42`), not BaseSettings; no prod `s3_enabled=True` |
| Cold tier structurally dead | HIGH | prod path `TieredConfig()` → `s3_enabled=False`; gates at `:120,126,168...` |
| Bucket NOT overloaded | HIGH | all sites = `autom8-s3`; #121 comment corroborates |
| `project-frames/` is fossil | HIGH | grep-negative for writers + live `aws s3 ls` (newest 2025-10-02, 8mo stale) |
| Monolith has zero direct edge | HIGH | grep-negative across a8 Go tree |
| A1 "monolith writer autom8_adapter.py:300" | REFUTED→MEDIUM | that module is in-repo Python + Redis-only; live tasks writer = ECS receiver (Unknown §5) |
| Live `asana-cache/tasks/` writer path | MEDIUM (UNKNOWN) | IAM comment attributes to ECS receiver; no src/ writer located |

---

*Artifact: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/storage-config-consumer-graph-2026-06-10.md`. Read-only census; no target repo modified. Handoff → structure-evaluator + remediation-planner.*
