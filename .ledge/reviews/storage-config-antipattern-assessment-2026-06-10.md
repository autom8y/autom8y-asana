---
type: review
status: draft
---
# Storage/Config Anti-Pattern Assessment — autom8-s3 × Env × IAM × Namespace

> **Station**: arch structure-evaluator A3 (ANTI-PATTERN ASSESSMENT). DESIGN-ONLY, read-only.
> **Date**: 2026-06-10 | **Code HEAD**: `origin/main` 8f9051b1
> **Inputs**: A1 census (`storage-topology-census-2026-06-10.md`), A2 consumer graph (`storage-config-consumer-graph-2026-06-10.md`).
> **Spot-checks (this session, `git show origin/main:<path>`)**: `tiered.py:49/57` (docstring claims env, field is `@dataclass` default `False`), `factory.py:209/219` ("S3 cold tier is Phase 3" → returns `_create_redis_provider`), `null_number_recovery.py:148` (`_DURABLE_TASK_CACHE_PREFIX = "asana-cache"`), `storage.py:342` (`prefix: str = "dataframes/"`), `settings.py:420/430` (`env_prefix="ASANA_CACHE_S3_"`, `prefix` default `"asana-cache"`), and `git grep` confirming `ASANA_CACHE_S3_ENABLED` is read-only (3 hits, all docstring/comment) + zero prod `s3_enabled=True` + zero prod `S3CacheProvider(` call-site. **All verified.**
> **Calibration anchor**: the triple-defect saga (hot-store phantom tier → `ASANA_CACHE_S3_PREFIX` overload → IAM/namespace drift) was ONE architecture defect wearing three masks — each mask cost a full deploy cycle of an inert production cure (#119, #120, #121, then #481). Severity is graded against THAT real cost, not inflated.

---

## Calibration scale (saga-anchored)

| Severity | Meaning, anchored to the saga's real cost |
|---|---|
| **CRITICAL** | Latent or live defect that already cost ≥1 inert-cure deploy cycle AND remains structurally re-triggerable — any new consumer/grant re-pays the cost. The saga's recurring root. |
| **HIGH** | Cost a deploy cycle once OR is the live blast-radius surface; addressable but not self-healing; a plausible next-consumer inherits the defect. |
| **MED** | Standing confusion/attack surface or doc-falsehood that has not yet cost a cycle but mis-leads the next reader; would have masked a real defect if it had. |
| **LOW** | Cosmetic / test-only / fully-quarantined; no path to a cure cycle without first crossing a higher-severity gate. |

Three-check false-positive gate applied to every finding before grading: (1) intentional trade-off? (2) dependency-analyst already flagged as context-aware? (3) evidence sufficient to distinguish from false positive? Findings that passed as **intentional/accepted trade-offs** are recorded as such, not as anti-patterns (see §Accepted Trade-Offs).

---

## GRADED ANTI-PATTERN TABLE

| # | Anti-pattern | Severity | Evidence (A1/A2 receipts) | Saga mask | Structural-cure direction (what A4 contract must make UNREPRESENTABLE) | Cheapest detection |
|---|---|---|---|---|---|---|
| **AP-1** | **Env-var overload** — one name (`ASANA_CACHE_S3_PREFIX`), two ontologies (task-cache prefix vs project-frames value). INERT (zero live readers) but LATENT. | **HIGH** | A1 env-table row 1 + 3-mask row #2: env = `"asana-cache/project-frames/"` set at TF `:213/:321/:436/:590`; read by `S3Settings.prefix` (`settings.py:430`, semantic = task-cache prefix). A2 §0 + P1–P8: **no live reader consumes it** (all 4 `s3.prefix` reads are #121 comments; DF plane hardcodes `dataframes/`; cold-tier reader P2/P3 dead). The #120 cure read `{s3.prefix}/tasks/` → `asana-cache/project-frames/tasks/` = EMPTY (R-CURE-141). | **#2** | A4 must make it impossible to express ONE env/setting that two semantic planes read. Per-namespace prefix bindings (`ASANA_TASK_CACHE_S3_PREFIX`, `ASANA_DATAFRAME_S3_PREFIX`) OR a `StorageNamespaceContract` SSOT where `S3Settings.prefix` cannot be the source for a task-cache key. The cure-by-pin (`_DURABLE_TASK_CACHE_PREFIX`) becomes derivable, not hand-pinned. | Alignment test asserting `settings.S3Settings.prefix` is never the prefix arg on a task-cache key-builder; grep-lint forbidding new `prefix=get_settings().s3.prefix` live reads (A2 O-D). |
| **AP-2** | **Phantom cold tier** — config (`TieredConfig.s3_enabled`, env `ASANA_CACHE_S3_ENABLED`, tiered cold path) advertises an S3 read tier that production never wires. | **HIGH** | A1 row 5p + env-table: `s3_enabled` default `False` (`tiered.py:57`), gated cold path `tiered.py:168/211/264/302`, `factory.py:209` "S3 cold tier is Phase 3" → `_create_tiered_provider` returns `_create_redis_provider` (`factory.py:219`). A2 §1E (HIGH): `TieredConfig` is a plain `@dataclass` (`tiered.py:42`), NOT `BaseSettings` — **the `tiered.py:49` docstring "Environment variable: ASANA_CACHE_S3_ENABLED" is FALSE**; no env binding exists. Prod path `TieredConfig()` (`tiered.py:116`) → always `s3_enabled=False`; zero prod `s3_enabled=True`. **Verified this session.** | **#1** | A4 must make a config tier UNREPRESENTABLE unless a wired backend exists: tier-config presence ⇒ a liveness-asserted backend. Delete the `s3_enabled` field + cold path OR bind it to a real, test-asserted provider. The FALSE docstring env claim must be impossible (settings fields self-document their binding). | Liveness test: for every cache-tier config field, assert a constructed provider actually instantiates that tier; assert any docstring naming an env var corresponds to a real `BaseSettings` binding (catches the false `@dataclass` docstring). |
| **AP-3** | **IAM ↔ namespace drift** — grants evolve per-incident; no binding contract derives grant from namespace map. | **CRITICAL** | A1 IAM column + 3-mask row #3: 11 live namespaces vs **4 scoped warmer grants** (`project-frames/`, `dataframes/`, `checkpoints/`, + `tasks/` read-only via the **reactive #481 `S3DurableTaskCacheRead` grant**) + **2 full-bucket super-principals** (ECS task role `autom8-s3/*` R-IAM-ECS; IAM user `autom8` `s3:*` R-BUCKETPOL). 5 live namespaces (`task-cache`, `task-data-cache-v3`, `insights-frames`, `name-gid-mappings`, `asana-cache/dataframes`) have NO repo writer + NO warmer grant. **Asymmetry**: least-privilege warmer (scoped) vs full-bucket ECS — same cure code GETs `tasks/*` on ECS (full bucket) but died on the warmer until #481 added the scoped read. | **#3** | A4 must make a grant that points at an un-mapped prefix UNREPRESENTABLE, and a writer landing in an un-granted namespace UNREPRESENTABLE: IAM Resource ARNs projected from the canonical namespace registry (TF local / generated). Full-bucket `autom8-s3/*` on ECS must narrow to the namespace set. A new namespace cannot exist without a co-generated grant. | Alignment test asserting (a) every IAM `Resource` prefix ∈ namespace registry, (b) every registry namespace with a declared writer-principal has a matching grant, (c) no principal holds `autom8-s3/*` unscoped. (A2 O-B alignment test.) |
| **AP-4** | **Writer-ignores-env vs reader-trusts-env asymmetry + WRITER-UNKNOWN** — the live `asana-cache/tasks/` writer is not pinnable from this repo. | **CRITICAL** | A1 row 1 (384,992 keys; writer attributed to monolith/ECS via default-prefix + bucket super-grant, Confidence Med) vs reader pin (`null_number_recovery.py:148`). A2 §1 P3 **REFUTES** the A1 "monolith writer at `autom8_adapter.py:300`" attribution (that module is in-repo Python building a **Redis** provider); **no prod `S3CacheProvider(` construction exists** (verified); TF IAM comment `main.tf:1218` attributes `tasks/` writes to the **ECS receiver durable-first path** under full-bucket grant — a writer A2 could not locate in `src/` (A2 §5 Unknown). Reader TRUSTS pinned `asana-cache`; writer cannot be pinned. | **NEW** (compounds #2+#3) | A4 must make a namespace whose WRITER cannot be named UNREPRESENTABLE: a **namespace-owner registry** binding every namespace to a {writer-principal, writer-code-anchor, key-schema} tuple. No namespace may be live without a named, locatable owner. Forces the cross-repo writer to surface or the namespace to be quarantined. | Registry-completeness test: every live S3 namespace (from `list-objects` denominator) maps to a registry row with a non-empty writer anchor; a namespace with keys but no registry owner fails CI as an orphan. |
| **AP-5** | **(SWEEP) Fossil namespaces with live IAM grants + live decorative env** — `asana-cache/project-frames/` (2,243 keys, newest 2025-10-02, ~8mo stale) is write-orphaned yet kept reachable by `S3CacheAccess` GET/PUT/DELETE (`main.tf:1197/1210`) and the env at 4 sites. | **HIGH** | A2 §4 (HIGH, WRITE-ORPHANED FOSSIL): grep-negative for writers/readers (only #121 comments); live newest key 2025-10-02 vs `dataframes/` newest 2026-06-10; v1 name-keyed schema vs v2 gid-keyed. A1 row 2. **Standing confusion/attack surface**: a future caller pointed at the overloaded env (AP-1) lands writes into a fossil with full GET/PUT/DELETE — exactly the #120 failure path, now write-capable. | **NEW** (intersection #2 ∩ #3) | A4 must make a writable grant on a quarantined namespace UNREPRESENTABLE: the registry marks `PROJECT_FRAMES_FOSSIL` read-only-or-none; grant projection refuses PUT/DELETE on a fossil-classified namespace. | Test: any namespace classified `fossil/quarantined` in the registry must have no PUT/DELETE grant; stale-detector flags a granted namespace whose newest object age > threshold with no writer anchor. |
| **AP-6** | **(SWEEP) Hardcoded prefix literals scattered across ≥3 sites** — `"dataframes/"` and `"asana-cache"` repeated as Python defaults divorced from any single source. | **MED** | A1: `storage.py:342` `"dataframes/"`, `settings.py:430` `"asana-cache"`, `null_number_recovery.py:148` `"asana-cache"`, `checkpoint.py:31` `"cache-warmer/checkpoints/"`. A2: `section_persistence.py:295` + `:1023` second `"dataframes/"`; `offline.py:7-14/83-87` hardcoded `dataframes/{gid}/.../sections/` path; doc-drift `cache_warmer.py:18` default `"cache/"` ≠ `"asana-cache"` (R-DOC-DRIFT). | **NEW** (the substrate of #2's overload) | A4 must make a second literal declaration of a known namespace UNREPRESENTABLE: all prefixes derive from the namespace registry; a string literal `"dataframes/"`/`"asana-cache"` in a key-builder is a lint failure. | Grep-lint forbidding namespace string literals outside the registry module; doc-vs-default consistency test (catches the `"cache/"` doc-drift). |
| **AP-7** | **(SWEEP) 128k-key legacy task-cache (`asana-cache/task-cache/`) — owner-unknown, format-divergent.** | **LOW** | A1 row 6: 128,583 keys, **pickle** format (`tasks/<gid>/data.pkl`, `meta/deleted_tasks.pkl`); NO repo writer (R-MONO grep-empty), NO repo reader, NOT in any warmer grant (only the `autom8` super-user bucket policy reaches it). | **NEW** (a third namespace-owner unknown, but inert) | Same as AP-4: namespace-owner registry must claim or quarantine it. Distinct from AP-4 only in that it has **no** live reader/cure depending on it — so its severity floor is LOW until something reads it. | Same registry-completeness test as AP-4; this row is the test's canary (a 128k-key namespace with no owner anchor should fail loudly). |

---

## Accepted Trade-Offs (passed the false-positive gate — NOT anti-patterns)

These surfaced as candidate anti-patterns but the three-check gate classifies them as intentional/sound. Recording so the remediation-planner does not re-litigate them.

- **`_DURABLE_TASK_CACHE_PREFIX` pinned constant (`null_number_recovery.py:148`)** — looks like a magic literal (AP-6 family) but is a **deliberate decoupling** from the overloaded env (the #121 cure). It is the *correct local mitigation* of AP-1; it should be **retired into the contract** (derived from registry), not flagged as a smell. Accepted as a sound interim trade-off.
- **`CACHE_WARMER_CHECKPOINT_PREFIX` per-lane disjoint values** (A1 env-table; bulk vs section vs default) — looks like prefix proliferation but is **intentional per-lane isolation (#96)**, single-purpose, single-reader (`CheckpointManager`). Bounded-context-aligned (A2 confirms not overloaded). NOT an anti-pattern.
- **`ASANA_CACHE_S3_BUCKET` single value at 5+ sites** — repetition, but A2 §1C asserts NOT overloaded (one value `autom8-s3`, single semantic). The #121 cure *depends* on the bucket NOT being overloaded. Accepted; the repetition is AP-6 territory only if it ever diverges (the consistency test covers it).
- **Redis as the real hot tier with `s3_enabled=False`** — this is the *intended* Phase-1 architecture (`factory.py:209` ADR-tracked "Phase 3"). The anti-pattern (AP-2) is NOT "Redis-only is wrong"; it is "config/docstring advertises a tier that isn't wired and lies about an env binding." The Redis-first decision itself is an accepted trade-off.

---

## Severity rationale (against the saga's real cost)

- **CRITICAL (AP-3, AP-4)**: These are the saga's *recurring root*. #481 was a **reactive** grant added post-AccessDenied (A1 IAM column) — a deploy cycle spent because the grant map did not track the namespace the cure needed (`tasks/` read). The writer-unknown (AP-4) means the team **cannot pin the writer of 385k live keys from the consuming repo** — the exact condition under which #120 shipped an inert cure against the wrong namespace. Both remain structurally re-triggerable: a new grant or a new reader re-pays the cost. They sit at CRITICAL because they are the masks that *generate* the other masks.
- **HIGH (AP-1, AP-2, AP-5)**: Each cost exactly one cure cycle (AP-1 → #120; AP-2 → the phantom-tier confusion that made #119/#120 look live) but is **inert today** (AP-1: zero live readers; AP-2: cold tier dead; AP-5: fossil unread). Graded HIGH not CRITICAL because the live blast radius is currently zero — the danger is the *next* consumer inheriting the wrong ontology. AP-5 is HIGH (not MED) specifically because the fossil retains **PUT/DELETE** grants, making the next-consumer failure *write-capable*, not just empty-read.
- **MED (AP-6)**: Scattered literals have not themselves cost a cycle, but they are the **substrate** that let AP-1's overload exist (no SSOT → two planes each hardcode their own prefix). The `"cache/"` doc-drift would mislead the next reader. Below HIGH because no live path currently breaks on it.
- **LOW (AP-7)**: 128k orphan keys, but **nothing reads them and no cure depends on them**. It is the canary for AP-4's registry test, not an independent hazard. Cannot cause a cure cycle without first crossing AP-4.

---

## Cross-rite observations (for remediation-planner → cross-rite referrals)

- **Security/IAM (note, not an audit)**: two full-bucket super-principals (ECS `autom8-s3/*`, IAM user `autom8` `s3:*`) are a least-privilege blast-radius beyond storage-config concerns. AP-3's cure narrows them; flag for security-rite confirmation of the ECS narrowing's safety.
- **The pickle namespaces (AP-7, task-cache; A1 row 7 task-data-cache-v3)**: pickle deserialization of monolith-written objects in any future reader is a deserialization-trust concern — out of A3 scope, noted for cross-rite.

---

## Unknowns (structural decisions requiring human/cross-repo context)

### Unknown: Live `asana-cache/tasks/` writer identity (the AP-4 root)
- **Question**: Which exact code path writes the 384,992 live `asana-cache/tasks/{gid}/task.json` keys — the dead tiered cold tier, or an ECS-receiver durable-first write distinct from `S3CacheProvider`?
- **Why it matters**: AP-4's cure (namespace-owner registry) and AP-1's cure (env split) both require pinning this writer. If it is also env-decoupled, the contract must preserve `asana-cache` exactly or break the #121 cure. The writer is the linchpin that distinguishes "quarantine safe" from "live-critical."
- **Evidence**: A2 §5 + §1 P3 — no prod `S3CacheProvider(` site (verified this session); TF IAM comment `main.tf:1218` attributes writes to "the ECS receiver under its full-bucket grant"; A2 REFUTES the A1 `autom8_adapter.py:300` attribution (Redis, not S3).
- **Suggested source**: receiver request-handler / durable-first write path (cross-repo or a follow-up grep for `task.json` / `tasks/{` writers); the monolith repo `autom8/a8` Go tree was probed grep-negative (A2 §3) so the writer is the ECS receiver Python path or a non-obvious key-builder.

### Unknown: TF↔Python prefix derivation feasibility (governs whether AP-1/AP-3 cures are "structurally unaddressable" or "test-guarded duplication")
- **Question**: Can TF derive the namespace registry from a Python SSOT without a codegen build-step, or must the contract accept duplicated-but-test-asserted literals across the repo boundary?
- **Why it matters**: Determines whether A4's "make it unrepresentable" claim holds across repos (AP-1, AP-3, AP-5 cures all cross the AS↔TF boundary). If only test-guarded duplication is feasible, the cure is detection-grade, not prevention-grade.
- **Evidence**: A2 §5 + O-B note — TF has no plan-time Python import; the 4 prefix env sites + IAM ARNs are literals today.
- **Suggested source**: remediation-planner (cross-repo SSOT mechanics).

### Unknown: `S3Settings.prefix` cross-repo importers
- **Question**: Does any sibling python service (e.g. the `repos/seam2-unit-econ` worktree) import `autom8_asana.settings` and read `.s3.prefix` live?
- **Why it matters**: A hidden cross-repo reader would invert AP-1's "zero live readers" premise and reclassify it CRITICAL.
- **Evidence**: A2 §5 — in-repo the only live consumer is the dead cold tier; sibling checkouts unverified.
- **Suggested source**: cross-repo grep of services importing `autom8_asana.settings`.

---

## Confidence ratings

| Finding | Confidence | Basis |
|---|---|---|
| AP-1 env-var overload (latent) | **HIGH** | A1 env-table + A2 P1–P8 corroboration; multi-artifact + structural. "Zero live readers" is HIGH conditional on the cross-repo-importer Unknown. |
| AP-2 phantom cold tier | **HIGH** | A1 row 5p + A2 §1E + **own spot-check** (`@dataclass`, docstring-FALSE, zero prod `s3_enabled=True`). Triple-corroborated. |
| AP-3 IAM↔namespace drift | **HIGH** | A1 IAM column (live `get-role-policy`/`get-bucket-policy` dumps) + namespace denominator; live AWS + structural. |
| AP-4 writer-ignores/reader-trusts + writer-unknown | **HIGH** (defect) / the *writer identity* is **MEDIUM-UNKNOWN** | A2 REFUTATION of A1's writer attribution + verified absence of prod `S3CacheProvider(`. The anti-pattern (un-pinnable writer) is HIGH; the resolution of WHO writes is the open Unknown. |
| AP-5 fossil + live grant | **HIGH** | A2 §4 grep-negative + live `aws s3 ls` 8mo-stale + schema divergence + A1 IAM grant. |
| AP-6 scattered literals | **HIGH** (existence) | direct file:line enumeration across A1/A2; spot-checked `storage.py:342` + `settings.py:430`. Severity MED is the judgment, not the evidence. |
| AP-7 128k orphan task-cache | **MEDIUM** | A1 R-MONO grep-negative (repo-writer absence) + live key count; writer is cross-repo inference, not a receipt. |

---

## Handoff readiness (→ remediation-planner)

- [x] All 7 findings carry severity, evidence (A1/A2 receipts + 6 own spot-checks), saga-mask mapping, structural-cure direction, and cheapest-detection.
- [x] False-positive three-check gate applied; 4 candidates reclassified as Accepted Trade-Offs.
- [x] Confidence ratings assigned to every finding.
- [x] Cure directions stated as "what A4 must make UNREPRESENTABLE" (prevention-grade) with a detection-grade fallback each — leverage/effort ranking is remediation-planner's call.
- [x] Three structural Unknowns documented (the writer-identity Unknown is load-bearing for AP-4 and AP-1 cure scope).
- [x] Cross-rite observations noted (security IAM blast-radius; pickle deserialization-trust) for remediation-planner to convert into referrals.

**Artifact**: `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/storage-config-antipattern-assessment-2026-06-10.md`
