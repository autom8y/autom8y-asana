---
type: decision
adr_id: CR3-COORDINATED-LAND-RUNBOOK-2026-06-03
title: "CR-3 coordinated irreversible-land runbook (the IC-executed artifact)"
status: draft
decision_state: STAGED — nothing executed
rite: sre
author: platform-engineer
date: 2026-06-03
initiative: cr3-fleet-data-plane-foundation-cutover
reversible_only: true
evidence_grade: moderate   # self-ref sre rite; MODERATE ceiling. STRONG claims = consumer-corroborated (OQ-1 width, OQ-4 cred) + V1 rite-disjoint #55 re-verify, cited inline.
reconciles:
  - .ledge/decisions/ADR-section-10min-x-502-headroom-2026-06-03.md   # §C is the parent ordering; this runbook is its executable form
  - Verify LANE V1 (consumer #55 rite-disjoint re-verify)
  - Verify LANE V2 (PR topology, REST GET)
  - Verify LANE V3 (land mechanisms at source)
  - Verify LANE V4 (Trap-4/Trap-5 dry-run for #343)
  - /Users/tomtenuta/Code/autom8/.sos/wip/handoffs/HANDOFF-autom8-to-asana-sre-cr3-consumer-return-2-2026-06-03.md
grounding_receipts:
  - "origin/main HEAD = 3c1dca57 (git ls-remote origin refs/heads/main, this session)"
  - "FROZEN=4 anchor: build_coordinator.py:131 'max_concurrent_builds: int = 4' (grep, this session)"
  - "A8_VERSION repo var = v1.3.8 (gh api repos/autom8y/autom8y/actions/variables/A8_VERSION → updated 2026-06-02T18:56:05Z)"
  - "current applied baseline cpu=1024/mem=2048 (a8 manifest @v1.3.8; memory asana-deploy-ci-writer-race.md)"
---

# CR-3 COORDINATED IRREVERSIBLE-LAND RUNBOOK

> **STAGED — nothing executed. reversible_only: true.** This is the artifact the human/IC executes
> in a SEPARATE land pass. The authoring of this runbook ran read-only (REST GET, git ls-remote, grep,
> file reads). No merge, no `terraform apply`, no deploy, no `a8 deploy` / version cut, no push, no
> secret op, no `max_concurrent_builds` value change (FROZEN=4 holds), no prod flag flip.
>
> **IC-GATE legend:** each `🔒 IC-GATE` line marks a point where human/IC sign-off is REQUIRED before the
> next irreversible step. `[IRREVERSIBLE]` = one-way door (merge/apply/deploy/version-cut). `[reversible]`
> = branch/read/measure op that can be undone or re-run.

---

## §0. Pre-flight invariants (assert ALL before step 1)

| # | Invariant | Receipt to re-assert at land time |
|---|-----------|-----------------------------------|
| P1 | origin/main HEAD == `3c1dca57` (all receiver PR `base_sha` pin to this) | `git ls-remote origin refs/heads/main` |
| P2 | `max_concurrent_builds` FROZEN=4 | `build_coordinator.py:131` + `settings.py:305` (PR #100 only *parameterizes*; no value change until step (f)/(g)) |
| P3 | A8_VERSION repo var == `v1.3.8`; current applied baseline cpu=1024/mem=2048 | `gh api repos/autom8y/autom8y/actions/variables/A8_VERSION` |
| P4 | All receiver PRs OPEN, `merged=false` | V2 table; re-GET `gh api repos/autom8y/autom8y-asana/pulls/{N}` |
| P5 | #343 plan shows **0 destroy on the cred surface** (Trap-4) | V4: `+3 import, +1 add, +3 change, +0 DESTROY`; re-plan at land time |
| P6 | Consumer #55 commit == `09e0f64b` (≡ `ae41170c` by patch-id), 3 files | V1 patch-id `a04ac55e…`; V2 #55 head |

---

## §1. ORDERED LAND STEPS

The order is load-bearing: the **CPU/mem lever lands FIRST among the capacity steps** (step f precedes
the §B lane deploy and any knob→576s), the **knob calibration is LAST among receiver config** (after the
lane is live), and the **consumer #55 merge + the FINAL ≥99% re-gate are DOWNSTREAM of the whole receiver
land** (consumer return-2: Stage-B is gated behind the re-gate on the headroom-APPLIED substrate).

> **NOTE on step lettering:** the prompt's lettered list (a)–(j) is the canonical step set. The order
> below sequences them per ADR §C so the lever is never inert-and-dangerous. Mapping is annotated per step.

---

### STEP a — Rebase the bundled receiver PRs off origin/main  `[reversible prep]`

Prompt-(a). **No IC gate** (branch op, fully reversible).

**#99, #100, #101** transitively carry the fast-lane bundling delta (`25d466ca` + `873653e7`, V2
"bundling delta — load-bearing finding"). Rebase each onto current origin/main so its diff shrinks to its
logical change:

```
git fetch origin
git rebase --onto origin/main 25d466ca^ sre/serve-stale-adr-stale-served-knob          # #99
git rebase --onto origin/main 25d466ca^ sre/cr3-c2-namespace-pq1-headroom-prep          # #100
git rebase --onto origin/main 25d466ca^ sre/canary-project-arm-content-binding          # #101
# #102 is STACKED on #99 (base = sre/serve-stale-adr-stale-served-knob) — rebase it AFTER #99 lands its rebase:
git rebase --onto sre/serve-stale-adr-stale-served-knob <old-99-head> sre/calibrate-freshness-knob-oq2   # #102
```

**Per-step verify:** each rebased branch diff against origin/main contains ONLY its logical change — NO
fast-lane handler files (`*fast_lane*`, the 15-min `section_only`/`fast` key source). Confirm `git diff
origin/main...<branch> --stat` for #100 = src + tests only.
**Abort:** if a rebase surfaces a conflict in the fast-lane files, STOP — the delta separation is wrong;
re-derive the bundling root before continuing.
**#98 and #103 are already clean** (V2: base main, not carrying the delta) — no rebase.

---

### STEP b — Merge the OQ-free receiver PRs in dependency order  `[IRREVERSIBLE]`

Prompt-(b). 🔒 **IC-GATE before this step** (first one-way door into main).

Merge order (V2 dep topology + ADR §C step 2):

1. **#98** — EMF 3-cause disaggregation. No deps.
2. **#100** — C2 namespace + `max_concurrent_builds` **parameterization** (FROZEN=4, no behavior change; adds `dataframe_max_concurrent_builds: int = Field(default=4, …)` per V3 §2). 
3. **#99** — serve-stale attestation + **inert `{}` knob** (`FRESHNESS_CONTRACT_MAX_AGE_SECONDS` ships empty).
4. **#101** — Project-arm canary content-binding.
5. **#102** — freshness-knob calibration scaffold. **STACKED on #99** — merge ONLY after #99 is in main and #102's base is retargeted to main (or #102 auto-retargets on #99 merge).

**Per-step verify after each merge:** `gh api repos/autom8y/autom8y-asana/pulls/{N}` → `merged=true`;
re-GET origin/main HEAD; confirm CI Test conclusion green on main BEFORE the next merge.
**DEPLOY-TRAP guard (memory `asana-deploy-ci-writer-race`):** each merge to main fires a main-branch Test →
`satellite-dispatch.yml` → `satellite-deploy` repository_dispatch → an `a8 deploy` that re-overlays cpu/mem
from the A8_VERSION-pinned manifest. **At v1.3.8 that manifest reads cpu=1024/mem=2048**, so these merges
re-assert the CURRENT baseline (not a regression). The cpu=256 re-revert hazard is RESOLVED. PR #94's
`concurrency` group on `satellite-dispatch.yml` serializes stacked dispatches — confirm it is merged or
quiesce in-flight dispatches between merges.
**Abort:** any merge that turns main-Test red → STOP, do not merge the next PR.

> **TF-only PR note (memory `autom8y-tf-only-pr-defense3-blocked`):** if any receiver PR sits at
> `mergeStateStatus=BLOCKED` solely because "Defense 3 — migration-pairing gate" never reports (path-filtered
> to `services/auth`), that is benign and admin-mergeable (precedent #335). Does NOT apply to #98–#103
> (they are receiver src/test PRs, not TF-only) — flagged only if a blocked-state surprise appears.

---

### STEP c — `terraform apply` #343 (autom8y infra-TF cred-IaC)  `[IRREVERSIBLE]`

Prompt-(d). 🔒 **IC-GATE before this step.**

Repo = **`autom8y/autom8y`** (V2/V4 confirmed `.base.repo.full_name`), workspace `terraform/services/asana`,
branch `sre/pq3-asana-dataframe-resolver-cred-iac`, head `255f25ae`.

**Trap-5 guard — pass the DEPLOYED short-SHA, NOT the var defaults (V4):**
```
terraform plan/apply \
  -var 'image_tag=3c1dca5' \          # live from lambda get-function (NOT default 'latest')
  -var 'image_ref=:3c1dca5' \         # live from running ECS TD (NOT the stale @sha256:21a701… digest)
  -var 'environment=production'
```
Both resolve to deployed short-SHA `3c1dca5` (== HEAD `3c1dca57`).

**Trap-4 GATE EVIDENCE — the apply is authorized ONLY if the plan shows 0 destroy on the cred surface:**
- Required plan signature (V4): `Plan: 3 to import, 2 to add, 8 to change, 1 to destroy` where the **#343
  DELTA over baseline = `+3 import, +1 add, +3 change, +0 DESTROY`**. The single standalone destroy is NOT
  on the cred surface (V4: `grep -c "will be destroyed"` on cred resources = 0). The `import{}` adopt-blocks
  make Secret 1 + both SSM pointers main-resident (Trap-4 remedy).
- **STOP-AND-REPORT if the re-plan shows ANY destroy on `aws_secretsmanager_secret.*resolver*` or
  `aws_ssm_parameter.*resolver*`** — that is a Trap-4 trip; do not apply.

**Scope fence:** #343 declares Secret 1 + both SSM pointers + a client_id-drift alarm. **Secret 2 STAYS**
(drift alarm, NOT delete — it is actively consumed: monolith reads it at `autom8 config/satellite_config.py`,
`LastAccessedDate=2026-06-03`; cred-topology memory). No `aws_secretsmanager_secret_version` declared (value
stays out-of-band). **Secret-2 decommission is NOT a land step** (see §2).

**Per-step verify:** post-apply `terraform plan` → `0 to add, 0 to change, 0 to destroy` (clean re-plan).
**Abort:** non-zero destroy on cred surface, or image_tag resolving to `latest`/stale digest (phantom churn).

> **TF-land mechanics (memory `autom8y-service-terraform-concurrency-gate`):** the prod-env approval on
> `service-terraform.yml` is self-approvable via REST, but a parked apply gate holds the shared `main`
> concurrency slot and blocks UNRELATED services' applies — coordinate the #343 apply window so it does not
> starve other satellite applies. A `-target` local apply on the cred resources is the in-authority bypass
> if the shared slot is contended.

---

### STEP d — C1 5-lambda OTLP convergence deploy  `[IRREVERSIBLE]`

Prompt-(e). 🔒 **IC-GATE before this step.**

Re-bake the 5 asana lambdas' `OTEL_EXPORTER_OTLP_HEADERS` from SSM v10 (currently divergent: SSM v10
@12:59Z vs lambda env @09:06Z, sprint ledger A3(i); #339 removed the oscillating var-chain; single-source
SSM writer `observability/main.tf:164`).

**Per-step verify (the literal gate):** AFTER convergence, re-plan asserts literal **`0 to add, 0 to change,
0 to destroy`** (0/0/0) on the observability/lambda-env surface. If the re-plan shows ANY OTLP-header churn,
the convergence did not take — re-run, do not proceed.
**Abort:** non-zero re-plan on the OTLP surface.

---

### STEP e — CPU/mem bump to 2048/8192 — THE LEVER, LANDED FIRST  `[IRREVERSIBLE]`

Prompt-(f). 🔒 **IC-GATE before this step** — this is the load-bearing capacity gate; everything capacity-
dependent (the §B lane, the knob→576s, the re-gate) is downstream of it.

**MECHANISM (V3-confirmed — this is a releaser-shaped a8-version-cut path, NOT an autom8y `terraform apply`):**
The runtime cpu/mem comes from the **a8 manifest `services.asana.resources`**, overlaid by `a8 deploy`
(`cmd/a8/deploy.go:845-847`). The autom8y TF taskdef is INERT (`ignore_changes=[task_definition]`; TD-002
was inert). Editing `terraform/services/asana/main.tf` alone silently no-ops at runtime. The lever is:

1. Edit a8 `manifest.yaml` `services.asana.resources` → **cpu: 2048, memory: 8192** (§A.2 RECOMMENDED).
   - Source-of-truth: current v1.3.8 manifest = cpu:1024/mem:2048 (V3 §1; `manifest.yaml:659-660`).
2. **Cut a new a8 release tag** (e.g. `v1.3.9`) containing that manifest edit (binary byte-identical to
   v1.3.8 since manifest is a data file).
3. **Bump the autom8y `A8_VERSION` repo var** v1.3.8 → v1.3.9 (`gh api ... actions/variables/A8_VERSION`).
4. **Trigger a satellite deploy** (main-branch Test-success dispatch or `workflow_dispatch`) so the
   `deploy-ecs-a8` job checks out the manifest at the new A8_VERSION ref and `a8 deploy` overlays 2048/8192.

**`cpu_thread_concurrency` co-binding:** `settings.py:273` comment binds `cpu_thread_concurrency` to
`max_concurrent_builds` ("Sizing = max_concurrent_builds"). Since the value stays 4 (step g), no change.

**Per-step verify (RUNTIME, not the TF plan — memory `asana-runtime-taskdef-cpu-mem-source-of-truth`):**
`aws ecs describe-task-definition autom8y-asana-service:<latest>` → cpu=2048/mem=8192 AND
`aws ecs describe-tasks` on the RUNNING task → cpu=2048, healthStatus=HEALTHY. Do NOT trust the TF plan.
**Abort:** running task still at 1024/2048 after deploy drains → the A8_VERSION bump or tag-cut did not take
(re-check the manifest ref CI checked out); do not proceed to step f/g.

> **Reconcile ADR §C step 5 wording:** the ADR says "task-def apply" generically. Per V3, the correct
> mechanism is **a8-manifest-edit + tag-cut + A8_VERSION-bump + satellite deploy** — NOT an autom8y
> `terraform apply` (which is `ignore_changes=[task_definition]` inert).

---

### STEP f — `max_concurrent_builds`: KEEP 4 (made honest by mem=8192)  `[no value change]`

Prompt-(g). **No IC gate for a value change — because there is NO value change.**

Per L4 §A.2 / §E: the RECOMMENDATION is **KEEP `max_concurrent_builds`=4**, paired with cpu=2048/mem=8192
(step e). The mem=8192 bump makes the existing semaphore value *truthful* against RAM (~3 safe ~2GB builds
+ Retry-After backpressure beyond ~3), rather than a latent OOM trap. **The operator's earlier "raise" is
RECONCILED to "keep 4."** A raise (to 6–8) is a **re-gate-contingent lever only** (L4 §A.2 4096/16384
option), NOT a land step — it fires ONLY if the §D re-gate shows the warm-miss tail is wide at unthrottled
width AND the consumer refuses the OQ-1 `max_workers→4` throttle.

**FROZEN=4 release point:** FROZEN=4 is released into "parameterized but unchanged" by PR #100 (step b) and
stays at value 4. No `.tf`/settings value edit. `build_coordinator.py:131` remains `= 4`.
**Verify:** `build_coordinator.py:131` and the deployed `dataframe_max_concurrent_builds` env both resolve
to 4 post-deploy.

> **If the consumer applies the OQ-1 throttle (max_workers→4):** L4 §A.2 alt is `max_concurrent_builds=2` +
> cpu=2048/mem=4096 (cheaper). That is ALSO not a land-now step — it is a post-re-gate optimization. Land
> the RECOMMENDED 4 / 2048-8192 baseline; tune down only with re-gate evidence.

---

### STEP g — Deploy the §B SECTION warm lane  `[IRREVERSIBLE]`

Prompt-(h). 🔒 **IC-GATE before this step** — MUST be downstream of step e (the lane's warm-miss tail relies
on the headroom) and MUST precede the knob→576s (step h).

Deploy the new SECTION-arm-only lane (ADR §B.2): `section_only_prematerialization_keys()` (34 keys,
`[(gid,"section") for gid in consumer_warm_set_gids()]`) + `prematerialize_section_set` event flag +
**disjoint `CACHE_WARMER_CHECKPOINT_PREFIX`** (e.g. `section-fast/`, isolated from `bulk/` per #96) +
**dedicated `reserved_concurrency` pool** + ≤10-min EventBridge schedule.

**Concurrency-pool gate (V3 §2 + ADR B.3 UV-P):** the section lane MUST have a reserved-concurrency pool
**disjoint from the bulk warmer's `ReservedConcurrentExecutions=1`** — checkpoint-prefix isolation (#96)
does NOT cover concurrency-slot contention. Recommended shape **B.3.a**: section pool ≥2–3 + heaviest-first
ordering + ≤10-min tick. **The account-level Lambda concurrency budget for the disjoint pool is a value the
land MUST verify, not assume:**
```
aws lambda get-account-settings   # confirm unreserved headroom to carve a 2–3 section pool
```
[Carry-forward UV-P from ADR B.3: account-concurrency headroom verified at THIS plan time, not the design
time.] **Fallback B.3.b** (if no account headroom): heaviest-subset section lane (2–4 heaviest GIDs) at
≤10-min on `reserved_concurrency=1`, bulk 30-min covering the cheap-section tail.

**Per-step verify:** lane Lambda exists with its OWN reserved-concurrency (not sharing bulk's pool);
EventBridge schedule ≤10-min; first invocation writes to its disjoint checkpoint prefix.
**Abort:** if carving the section pool would push the bulk warmer below its `ReservedConcurrentExecutions=1`
or starve the offer warmer → recede to B.3.b heaviest-subset on a non-contending slot.

> **Warmer collision guard (memory `warmer-bulk-warm-concurrency-collisions`):** verify the new lane's
> checkpoint key is disjoint AND its schedule does not let a 4-hourly offer/scheduled-warm hijack the section
> checkpoint via an entity-type path. CW metrics ns `autom8y/cache-warmer`, dim `environment`.

---

### STEP h — Calibrate `FRESHNESS_CONTRACT_MAX_AGE_SECONDS`  `[IRREVERSIBLE]`

Prompt-(c). 🔒 **IC-GATE before this step** — MUST follow step g (calibrating SECTION→576s before the lane
is live produces a section hard-reject / 503 build-storm, ADR §B.4 / §0).

Calibrate via PR #102's map to **EXACTLY `{"project":86400, "section":576}`** — **NOT the four-tier dead-key
list.** Per sprint-ledger Gate 2/6 + cred-topology corrections: only `project` and `section` bind to a
receiver `entity_type` (`entity_registry.py:885,925`); `analytics`/`backfill`/`vertical-summary` have NO
matching entity and are **DEAD KEYS** — including them is inert at best, misleading at worst.
- `section`=576s is the literal `caching.py:39 SECTION_DF_REFRESH_HOURS=0.16 (×3600)`; the `~10min`/`600s`
  shorthand is the comment gloss, NOT the calibrated value.
- Ratify PR #99's serve-stale ADR in the same step.

**Per-step verify:** deployed `FRESHNESS_CONTRACT_MAX_AGE_SECONDS` == `{"project":86400,"section":576}`
(no extra keys); a section read finds a frame <576s old and serves FRESH/SWR (does NOT enter
`BuildCoordinator`).
**Abort:** section reads hard-reject + build-storm post-calibration → the lane (step g) is not meeting the
576s cadence; recede, do not continue to the re-gate.

---

### STEP i — ≥2 clean SECTION sweeps  `[reversible verify]`

Prompt-(j). **No IC gate** (read/measure). Precondition for the §D re-gate.

Confirm via `WarmerKeysCovered`/`WarmerEnumerated` + `WarmerCheckpointCleared` (`cache_warmer.py:410-414`)
that the section lane reaches coverage=1.0 inside the ≤10-min cadence on **≥2 consecutive cycles**.
**Verify:** 2 consecutive sweeps at coverage=1.0, each completing inside the ≤10-min tick.
**Abort/iterate:** coverage <1.0 or sweep > 10min → tune pool size / ordering (step g), re-measure. Do NOT
run the re-gate on a lane that has not proven 2 clean sweeps.

---

### STEP j — Merge consumer #55 (cross-repo, autom8)  `[IRREVERSIBLE]`

Prompt-(i). 🔒 **IC-GATE before this step.** **CROSS-REPO ORDERING (load-bearing):** per consumer return-2
§0, Stage-B (the consumer cutover) is **gated behind the FINAL ≥99% re-gate on the headroom-APPLIED
substrate** (steps e–i complete + §D PASS). So #55 merges **AFTER the receiver land AND after the §D re-gate
PASS** — NOT before. The receiver substrate must be certified before the consumer repoints to it.

Repo = `autom8y/autom8` (V1 `git remote -v`), PR #55, base main, head **`09e0f64b`** (≡ local `ae41170c`
by patch-id `a04ac55e…`, V1 STRONG rite-disjoint). 3 files: `apis/asana_api/objects/section/main.py`,
`config/satellite_config.py`, `tests/apis/asana_api/satellite/test_resolver_auth_config.py`.

**Pre-merge gate (consumer-side, per return-2 §QA-RETURN):** #55 is HELD behind a **QA-adversary re-gate**
(`safe_to_commit` was false; principal-engineer remediated the orphaned credential-topology tests to 12/12
+ 128/128 green but did NOT self-flip). The QA re-gate must turn green BEFORE merge.
**Per-step verify:** `gh api repos/autom8y/autom8/pulls/55` → `merged=true`; consumer resolver-auth suite
green on main; live monolith auth path now fetches Secret 1 (authoritative, HTTP 200), not Secret 2.
**Abort:** §D re-gate not PASS, or QA re-gate not green → do NOT merge #55 (the consumer would repoint to an
uncertified receiver substrate).

> **Consumer corrections folded (do NOT carry the stale references):**
> - **SCAR-031 is a no-op** — it is "not grounded anywhere in the repo" (return-2 §land notes); the protective
>   intent is the credential-topology-integrity throughline + **SCAR-029** (`.know/scar-tissue.md:313`).
>   Grep-zero confirmed receiver-side. Drop "SCAR-031" wherever carried.
> - **CQ-3 S0 reconciliation is gitignored** (`.gitignore:448 **/.sos/*`) → consumer working-tree only, NOT
>   in commit `ae41170c`/`09e0f64b`. Not an omission; not a merge artifact. The deployed call is name-based
>   (`fetch_project_rows(project_gid, section_names, …)`, `consumer.py:409-413`); receiver predicate filters
>   `pl.col('section') == section_name_filter` (`engine.py:163-164`). Section arm is **column-contract-EXEMPT**
>   (`ENABLE_SECTION_PROBE=False`, fail-closed, no fabricated `section_gid`).

---

### STEP k — §D FINAL ≥99% re-gate  `[reversible verify — chaos-engineer-authored]`

The §D re-gate (ADR §D) runs **between step i and step j** — it is the precondition for the consumer merge.
It is **rite-disjoint (chaos-engineer-authored, NOT the receiver author)** and measured on the
headroom-APPLIED substrate (steps e–i). It MUST NOT run on the current substrate (repeats the INTERIM
82%/stale-datum error). Success criteria: ≥99% satellite-serve on BOTH project AND section arms, 3-cause-EMF
disaggregated, SECTION-576s held (zero serves >576s), CPU_STARVATION=0, singleflight proven under bulk,
≥2 concurrent streams at confirmed live width (~20 unthrottled / ~8 throttled), canary content-bound.
**This re-gate PASS is the gate on step j.** Failure → recede per §D abort criteria; do NOT merge #55.

---

## §2. NOT land steps (explicitly out-of-scope; STAGED for separate IC sequencing)

| Item | Disposition | Why NOT here |
|------|-------------|--------------|
| **Secret 2 decommission** | **IC-gated, sequenced with task #73** (baked-`.env` SPOF, `ASANA_RESOLVER_CLIENT_SECRET`, `Dockerfile:294`) | Secret 2 is actively consumed (`LastAccessedDate=2026-06-03`); decommission only AFTER #55 repoint is live-verified. #343 declares the drift alarm, NOT the decommission. |
| **`max_concurrent_builds` raise (4→6–8)** | re-gate-contingent lever (L4 §A.2 4096/16384) | Inert without wide-tail evidence at the §D re-gate; NOT a land-now value change. |
| **uvicorn worker bump** | KEEP 1 | Multi-worker multiplies the semaphore → defeats the cap (ADR §A.2 / §E). |
| **SCAR-031** | drop the reference | Not grounded in repo (return-2); use SCAR-029 + credential-topology-integrity throughline. |

---

## §3. IC-GATE checkpoint summary (ordered)

```
[a] rebase #99/#100/#101 --onto origin/main; #102 onto #99        reversible    (no gate)
🔒 IC-GATE 1 ─────────────────────────────────────────────────────────────────
[b] merge #98 → #100 → #99 → #101 → #102 (stacked)                IRREVERSIBLE
🔒 IC-GATE 2 ─────────────────────────────────────────────────────────────────
[c] terraform apply #343  (Trap-5 image_tag=3c1dca5; Trap-4 0-destroy gate)   IRREVERSIBLE
🔒 IC-GATE 3 ─────────────────────────────────────────────────────────────────
[d] C1 OTLP convergence deploy → assert 0/0/0 re-plan            IRREVERSIBLE
🔒 IC-GATE 4 ─────────────────────────────────────────────────────────────────
[e] CPU/mem → 2048/8192  (a8 manifest + tag-cut + A8_VERSION bump + satellite deploy)  IRREVERSIBLE  ← LEVER FIRST
[f] max_concurrent_builds: KEEP 4 (no value change)              (no gate — no change)
🔒 IC-GATE 5 ─────────────────────────────────────────────────────────────────
[g] deploy §B SECTION warm lane (disjoint reserved-concurrency pool; verify acct budget)  IRREVERSIBLE
🔒 IC-GATE 6 ─────────────────────────────────────────────────────────────────
[h] calibrate knob → {"project":86400,"section":576}  (after lane live)        IRREVERSIBLE
[i] ≥2 clean SECTION sweeps (coverage=1.0)                       reversible verify
[k] §D ≥99% re-gate (chaos-engineer, rite-disjoint, headroom-applied substrate)  reversible verify
🔒 IC-GATE 7 (cross-repo) ─── §D PASS + consumer QA re-gate green ─────────────
[j] merge consumer #55 (autom8)                                  IRREVERSIBLE
```

---

## §4. Trap guards carried on every TF/deploy step

- **Trap-4 (0-destroy):** the #343 apply (step c) is authorized ONLY on a re-plan showing `+0 DESTROY` on
  the cred surface (V4: import-adopt makes cred resources main-resident). Any cred-surface destroy → STOP.
  The satellite deploy (step e) runs a full TF apply from main — confirm no out-of-band resource is absent
  from main before any satellite deploy (the import-adopt of #343 is the remedy; land #343 BEFORE step e
  relies on cred resources, which it does — #343 is step c, step e is downstream).
- **Trap-5 (image_tag):** every local TF plan/apply (step c) passes the DEPLOYED short-SHA `image_tag=3c1dca5`
  + `image_ref=:3c1dca5` (V4 live-derived), NOT the stale `latest`/digest var defaults → no phantom churn.
- **CPU/mem mechanism trap (V3):** step e is a8-manifest + A8_VERSION cut, NOT an autom8y TF apply; verify
  at RUNTIME (`describe-tasks` cpu), not the TF plan.
- **CI-writer race (memory):** at A8_VERSION=v1.3.9 (post step e) the manifest reads 2048/8192, so post-step-e
  merges/dispatches re-assert 2048/8192 (not a regression). Quiesce in-flight dispatches between irreversible
  steps; PR #94 serializes stacked dispatches.

---

**STAGED — nothing executed. reversible_only: true.** Every `[IRREVERSIBLE]` step is enumerated for the
separate human/IC-gated land pass with its precise command, per-step verification, and abort criterion.
FROZEN=4 holds until step e/f (and is KEPT at 4). Secret values never printed. Self-ref MODERATE ceiling;
STRONG claims = OQ-1 width (`refresh_frames.py:115`), OQ-4 cred (cred-topology memory), V1 rite-disjoint #55
re-verify (patch-id `a04ac55e…`).
