---
type: review
subtype: pre-registered-activation-watch
artifact_id: WATCH-f1a-warmers-first-activation-2026-07-21
status: accepted
initiative: F1a — asana cross-consumer rate-limit budget allocator
node: "NODE 8 — GO-LIVE (warmers-first stage-1). This is the PRE-REGISTERED watch that makes the activation lawful under PW-7."
authority: "ADR-post-wave-halt-rulings-interview-2026-07-21 §PW-7 (watched activation clears the bar); unleashed item (1)"
operator_role: sre platform-engineer (activation is MINE under PW-7; the watch IS the reality-proof)
rite_disjoint_critic_of_the_wiring: eunomia verification-auditor @ autom8y-asana (per dispatch: disjoint cert PASS)
date: 2026-07-21
code_ref: "origin/main @ d11ae5747b4a6d25231aae3f6b91198e50ee121a (PR #256; wiring read directly from git, never the working tree)"
region: us-east-1
account: "696318035277"
targets_flipped:
  - autom8-asana-cache-warmer
  - autom8-asana-cache-warmer-bulk
targets_NOT_flipped:
  - autom8-asana-cache-warmer-section   # third warmer-lane Lambda; held INERT per the two-Lambda fence (see §9 SURPRISE-1)
watched_project_gid: "1143843662099250"
fences: "env-only mutation on exactly the two warmer Lambdas; ECS NOT flipped (stays governed by §3.5 tripwire); nothing else."
---

# WATCH — F1a warmer-floor cure, warmers-first activation (stage-1)

## 0. What this is

The pre-registered watch for the FIRST WATCHED ACTIVATION of the F1a warmer-floor
cure, fired under PW-7. PW-7 bar (all met before this watch was authored): the
mechanism is disjoint-certified (eunomia @ autom8y-asana), tested (two-sided
wiring suite), byte-identical-off (verified §2 below), and instantly revertible
(env-only, §6). PW-7 requires a watch PRE-REGISTERED with named success + abort
criteria, and a tripped abort that reverts and reports. This file IS that watch;
it was authored and committed-to BEFORE the flip.

The flip sets `ASANA_BUDGET_ALLOCATOR_ENABLED=true` on the two warmer Lambdas
ONLY. ECS is NOT flipped (stage-2 stays gated on the §5 ABORT tripwire NOT
firing during this window).

## 1. STEP-1 provenance receipts — the wiring is deployed (UV-P-2 gate DISCHARGED)

The custody analysis (`CUSTODY-f1a-flip-ac4-ac5-2026-07-21.md`) analyzed
`origin/main @ 2362cd37` (the commit BEFORE the wiring) and raised F-C3-01: the
flip was registration-only — no production path routed the gap-warm sweep
through the floor gate. It gave an explicit falsification pathway: a commit that
wires the gap-warm loop into `WarmerFloorGate.admit()` collapses F-C3-01 to
RESOLVED.

**F-C3-01 is RESOLVED by `d11ae574`** (read directly from git, not the commit
message):

| Fact | Anchor (origin/main @ d11ae574) |
|---|---|
| Gap-warm loop now resolves a floor-paced fetch once per sweep | `src/autom8_asana/dataframes/builders/hierarchy_warmer.py` — `fetch_one, cure_active = self._floor_paced(_fetch_gap_parent)` |
| `_floor_paced` gates on `running_in_warmer_lane()` AND `allocator.enabled`, then routes every gap GET through `gate.admit()` + records `observe_admission(Lane.WARMER)` | `hierarchy_warmer.py` `_floor_paced` / `_floor_paced_fetch` |
| Per-chunk banking (AC-4 (b') fix) folded in: `_bank_gap_chunk(chunk_dicts)` inside the chunk loop when `cure_active` | `hierarchy_warmer.py` chunk loop + `_bank_gap_chunk` |
| Byte-identical when inert: `if not cure_active` → single end-of-sweep banking; `fetch_one IS` the bare closure, no per-GET branch | `hierarchy_warmer.py` |
| Warmer lane gate keys on `AWS_LAMBDA_FUNCTION_NAME` containing `"cache-warmer"` | `budget_allocator.py` `_WARMER_LANE_FUNCTION_MARKER = "cache-warmer"`, `running_in_warmer_lane()` |
| Fail-open throughout (never fail-closed on the gate); emits `budget_lane_failopen` | `hierarchy_warmer.py` `_floor_paced` except-arms + `_note_floor_failopen` |

**Deployed-image provenance (own-hands, `aws` @ 2026-07-21T16:38Z):**

| Item | Value |
|---|---|
| Deploy mechanism | merge-to-main auto-deploy: `Test` (success on main) → `Satellite Dispatch` workflow → `repository_dispatch: satellite-deploy` to `autom8y/autom8y` (builds+pushes+deploys the asana image). No manual deploy needed; it fired on the merge. |
| CI timeline | Test run on `d11ae574` started 13:39Z; Satellite Dispatch 13:45Z; ECR image `d11ae57` pushed 13:47:21Z; warmer Lambdas updated 13:51:30Z. |
| ECR image (all 3 cache-warmers) | `696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/asana:d11ae57` |
| ECR digest for tag `d11ae57` | `sha256:dcd96528c36f023d9bf488915c4772f0eb5cd6cd1c5ca596814e6473e106a048` |
| Lambda `CodeSha256` (all 3) | `dcd96528c36f023d9bf488915c4772f0eb5cd6cd1c5ca596814e6473e106a048` — **EXACT match** to the ECR digest (for container Lambdas CodeSha256 == image manifest digest → the Lambda runs exactly this image) |
| Tag → commit binding | `d11ae57` = 7-char short SHA of merge commit `d11ae574`; corroborated by the immediately-prior deploy tag `2362cd3` (= parent/custody-ref commit). CI tags images with the merged commit's git short SHA. |
| LastModified | `2026-07-21T13:51:30Z` — advanced from the `2362cd3` era (not deploy-success-alone; the rebuild-cache scar is satisfied by the CodeSha + LastModified change). |

Residual (bounded, honest): the image config carries NO OCI `revision` label
(`imagetools inspect` → labels null), so the image→git-tree binding rests on the
CI short-SHA tag convention (strong; two-deploy precedent `2362cd3`→`d11ae57`),
not an embedded label. The digest chain is definitive that the Lambda runs the
image CI tagged `d11ae57`; the tag convention is what binds `d11ae57` to the
`d11ae574` source tree. Logged as UV-P-A (§10).

## 2. Before-state (own-hands, pre-flip)

| Function | env key count | `ASANA_BUDGET_ALLOCATOR_ENABLED` (before) | `allocator_boot` live state |
|---|---|---|---|
| autom8-asana-cache-warmer | 24 | **ABSENT** → INERT | (shares image; inert) |
| autom8-asana-cache-warmer-bulk | 20 | **ABSENT** → INERT | `state=inert, enabled=false, floor=110/60, fair_share=1390` at 15:57Z / 16:21Z / 16:37Z |
| autom8-asana-cache-warmer-section | 20 | **ABSENT** → INERT | dormant (0 log bytes) |

`enabled` defaults FALSE when the key is absent (`settings.py` `BudgetAllocatorSettings.enabled: bool = Field(default=False)`;
`config.py` `from_env` builds a FRESH settings instance per-process → the knob binds
per-process-fresh, so `update-function-configuration` (new execution env) arms it
on the next cold start). Absent ≡ false ≡ INERT byte-identical passthrough. This
discharges the custody UV-P "zero deployed processes currently set the knob."

## 3. The mechanism being armed

With the knob true AND the process in the warmer lane (`"cache-warmer"` in the
function name — both targets qualify), each gap-warm sweep routes every gap GET
through the process-singleton `WarmerFloorGate` at the static floor (110 req /
60 s) on the real clock, records `observe_admission(Lane.WARMER)`, and banks each
~200-GET chunk durably (no-expiry) instead of once at end-of-sweep. Fail-open: any
allocator fault proceeds un-paced and emits `budget_lane_failopen`. ECS is
untouched (fair-share lane; its knob stays absent).

## 4. SUCCESS criteria (claimable only through ≥1 diurnal peak, 09:00–12:00Z 2026-07-22)

ALL of:
1. `OfferFrameAgeSeconds{project_gid=1143843662099250}` RAW datapoints sustained
   **< 3600 s** through ≥1 diurnal-peak window (09:00–12:00Z) — the pre-flip
   sawtooth (Max 1304↔11589 s, §8) collapses and stays under threshold.
2. Warmer sweeps completing at floor pace: `allocator_boot` shows
   `state=active/enabled=true` on post-flip invokes; gap-warm admission paced at
   ~110/60 s; AIMD behavior sane (no new error class; `aimd_at_minimum` not worse).
3. `uncached_count` for GID 1143843662099250 **stable or converging**
   (monotone-ish shrink across ticks from the 3191 pre-flip baseline; §8).
   OBSERVATION-METHOD AMENDED (see §12, per QA-1): read `uncached_count` from
   `hierarchy_gap_fetch_starting` (emitted on BOTH the success and failure paths),
   NOT the failure-arm-only `parent_gids_count`. Both are the SAME quantity
   (`len(uncached)`), so the 3191 baseline and the convergence semantics stand —
   only the field/event read is corrected.

## 5. ABORT criteria → auto-revert + report (the §3.5 promote-to-blocker tripwire)

Fire the REVERT (§6) and report the honest record if ANY of:
- **Regrowth tripwire (§3.5):** `uncached_count` for GID 1143843662099250
  regrows to **≥ 90% of the prior full set** (prior full ≈ 3291; 90% ≈ **2962**)
  across **≥ 2 consecutive 30-min ticks** WHILE floored sweep attempts are present
  (`allocator_boot` active; `hierarchy_gap_warming_failed` /
  `hierarchy_gap_chain_warm_rate_limited` continuing).
  OBSERVATION-METHOD AMENDED (see §12, per QA-1): read `uncached_count` from
  `hierarchy_gap_fetch_starting` (success + failure paths); it equals the
  failure-arm `parent_gids_count` (both are `len(uncached)`), so the **2962**
  threshold and every condition above are UNCHANGED. If the probe returns EMPTY the
  reading is AMBIGUOUS (converged-to-zero vs GID-not-swept-this-tick) — disambiguate
  via the §7 P2b checkpoint probe; NEVER read an empty probe as health.
- **Staleness tripwire:** `OfferFrameAgeSeconds{1143843662099250}` RAW datapoints
  sustain **> 3600 s** through a storm-equivalent window WITH the floor engaged
  (allocator active).
- **Client-felt regression (any):** a new error class in the warmer logs, a
  `budget_lane_failopen` storm (fail-open should be rare; a sustained stream = the
  gate is faulting), a spike in `hierarchy_gap_warming_failed` beyond the pre-flip
  baseline, or any inbound 5xx / hard-starvation signal attributable to the flip.

NON-EVIDENCE (do NOT treat as a signal for the warmer lane): `budget_floor_overage`
is floor-protected for `Lane.WARMER` (PC-4 warmer-insulation) — `observe_admission`
telemeters NO overage for a warmer admission by design; its absence is NOT health
and its presence is not expected. Valid signals are OfferFrameAgeSeconds /
parent_gids_count / aimd_at_minimum only.

## 6. REVERT procedure (env-only; byte-identity proven; seconds)

For each of the two flipped Lambdas, set the knob false (behaviorally byte-identical
to the absent baseline: `enabled=false` → INERT passthrough). GET current env,
merge the single key, apply — never clobber:

```bash
FN=autom8-asana-cache-warmer   # then repeat for autom8-asana-cache-warmer-bulk
aws lambda get-function-configuration --function-name "$FN" --region us-east-1 \
  --query 'Environment.Variables' --output json > /tmp/env-$FN.json
jq '{Variables: (. + {ASANA_BUDGET_ALLOCATOR_ENABLED: "false"})}' /tmp/env-$FN.json > /tmp/rev-$FN.json
aws lambda update-function-configuration --function-name "$FN" --region us-east-1 \
  --environment "file:///tmp/rev-$FN.json" \
  --query '{Fn:FunctionName,LastMod:LastModified}' --output json
# Confirm next-invoke allocator_boot returns to state=inert.
```

## 7. Probe commands + cadence (each 30-min tick through the 2026-07-22 09:00–12:00Z peak)

All verified runnable @ 2026-07-21 (macOS `date`; epoch math is portable).

```bash
# --- P1: OfferFrameAgeSeconds RAW, watched GID, last 90 min, 5-min Max/Avg ---
aws cloudwatch get-metric-statistics --namespace "Autom8y/AsanaSubstrateFreshness" \
  --metric-name OfferFrameAgeSeconds \
  --dimensions Name=project_gid,Value=1143843662099250 --region us-east-1 \
  --start-time "$(date -u -v-90M +%Y-%m-%dT%H:%M:%SZ)" \
  --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --period 300 --statistics Maximum Average \
  --query "sort_by(Datapoints,&Timestamp)[].{T:Timestamp,Max:Maximum,Avg:Average}" --output table
# SUCCESS: Max < 3600 sustained through the peak. ABORT: Max > 3600 sustained w/ floor engaged.

# --- P2a (AMENDED §12, per QA-1): uncached_count from hierarchy_gap_fetch_starting ---
# Emitted at the START of every sweep with >=1 uncached parent, on BOTH the success
# AND failure paths. The OLD probe read parent_gids_count, which emits ONLY in the
# failure arm (hierarchy_warmer.py:337-341) -> it went half-blind on healthy/timeout
# ticks. uncached_count (hierarchy_gap_fetch_starting :194-201) == len(uncached) ==
# the failure-arm parent_gids_count, so the 2962 / 3191 thresholds transfer unchanged.
# (uncached_count is unique to gap_fetch_starting, so filtering on it selects that event.)
aws logs filter-log-events --log-group-name "/aws/lambda/autom8-asana-cache-warmer-bulk" \
  --region us-east-1 --start-time $(( ($(date +%s) - 1800) * 1000 )) \
  --filter-pattern '{ $.extra.project_gid = "1143843662099250" && $.extra.uncached_count = * }' \
  --query "events[].message" --output text | grep -oE '"(total_parent_gids|uncached_count)": [0-9]*'
# ABORT: uncached_count >= 2962 across >= 2 consecutive ticks while floored sweeps present.
# SUCCESS-3: uncached_count monotone-ish shrink from the 3191 baseline.

# --- P2b (AMENDED §12, per QA-1): empty-set blind-spot disambiguation ---
# The empty-set/complete case early-returns (hierarchy_warmer.py:190 `if not uncached`)
# and logs NOTHING, so an EMPTY P2a is AMBIGUOUS: converged-to-zero (GOOD) vs the GID
# never swept this tick (starvation, BAD). The -bulk warmer drains a queue of
# ~68 {gid:entity_type} entities and completes few per 900s invocation; the checkpoint
# carries per-entity status (verified own-hands 2026-07-21T18:11Z):
aws s3 cp s3://autom8-s3/cache-warmer/checkpoints/bulk/latest.json - --region us-east-1 | jq '{
  completed: [.completed_entities[]? | select(test("1143843662099250"))],
  pending:   [.pending_entities[]?   | select(test("1143843662099250"))],
  result:    [.entity_results[]?     | select(.project_gid=="1143843662099250")] }'
# READ: watched GID in `completed` / `result[].result=="success"` => converged/handled
#       (an empty P2a is then GOOD). In `pending` AND absent from gap_fetch_starting
#       => NOT REACHED / starved (actionable — the sweep never got to it; NOT health).

# --- P3: allocator_boot state (arming/realization) ---
aws logs filter-log-events --log-group-name "/aws/lambda/autom8-asana-cache-warmer-bulk" \
  --region us-east-1 --start-time $(( ($(date +%s) - 1800) * 1000 )) \
  --filter-pattern '"allocator_boot"' --query "events[-3:].message" --output text
# EXPECT post-flip: state=active, enabled=true.

# --- P4: aimd_at_minimum frequency + fail-open (health) ---
aws logs filter-log-events --log-group-name "/aws/lambda/autom8-asana-cache-warmer-bulk" \
  --region us-east-1 --start-time $(( ($(date +%s) - 1800) * 1000 )) \
  --filter-pattern '"aimd_at_minimum"' --query "length(events)" --output text
aws logs filter-log-events --log-group-name "/aws/lambda/autom8-asana-cache-warmer-bulk" \
  --region us-east-1 --start-time $(( ($(date +%s) - 1800) * 1000 )) \
  --filter-pattern '"budget_lane_failopen"' --query "length(events)" --output text
# ABORT signal: a sustained budget_lane_failopen stream (gate faulting).
```

Repeat P1–P4 each 30 min. The `-bulk` warmer is the heavy gap-warm workhorse
(3.5 GB logs) and owns the watched GID's section hierarchy; also spot-check
`/aws/lambda/autom8-asana-cache-warmer` (P3 for allocator_boot=active). Watch is
HUMAN-PULL (no SNS topic exists; AL-5 Actions=[]); a tripped ABORT maps to the
single §6 revert command.

## 8. Pre-flip baseline (own-hands, 2026-07-21)

- `OfferFrameAgeSeconds{1143843662099250}` last 6h Max (UTC): 10:38Z=3031 · 11:08Z=**11589** · 11:38Z=2632 · 12:08Z=1304 · 12:38Z=2141 · 13:08Z=2814 · 15:38Z=**6571**. Sawtooth crossing 3600 repeatedly; metric emits sparsely.
- `parent_gids_count{1143843662099250}` = **3191** (entity_type section), near the worst-case full set (~3291); `hierarchy_gap_warming_failed` with HTTP 404 "Not a recognized ID" — the diseased near-full state.
- `aimd_at_minimum` firing (16:04Z, 16:38Z) — AIMD pinned at floor (the suppression the cure relieves).

## 9. Surprises / scope flags

- **SURPRISE-1 — three warmer-lane Lambdas, not two (but the third is dormant).**
  Production has `autom8-asana-cache-warmer`, `-bulk`, AND `-section`. The code
  lane gate keys on substring `"cache-warmer"`, so ALL THREE are `Lane.WARMER` and
  all three run the wired image `d11ae57`. The dispatch + custody §5.1 name only
  the first two. Per the two-Lambda fence I flip ONLY the first two; `-section`
  stays INERT (its knob stays absent). `-section` is **genuinely dormant**: its
  EventBridge rule `autom8-asana-cache-warmer-section-schedule` (`cron(0/10 …)`)
  is **DISABLED**, and its log group has 0 stored bytes — it never fires. Holding
  it inert is therefore fully benign for THIS watch. OPEN QUESTION for the
  operator (UV-P-B): if `-section` is later ENABLED, its gap-sweeps would need the
  flip too — is it in the F1a warmed-hierarchy path?
- **Warmer schedules (own-hands):** `-bulk` = `cron(0,30 * * * ? *)` ENABLED
  (every :00/:30 — the heavy workhorse, owns the watched GID's section gap-warm;
  first post-flip cycle at 17:00Z); `cache-warmer` = `cron(0 */4 * * ? *)` ENABLED
  (next fire 20:00Z — its realization confirms then); `-section` DISABLED.
- **SURPRISE-2 — OfferFrameAgeSeconds is sparse.** Not continuously emitted
  (multi-hour gaps in the baseline). "Sustained < 3600 s" must be read over
  available datapoints across the peak, not as a dense series.
- **budget_floor_overage is NON-EVIDENCE for warmers** (§5) — carried from the
  cert; the warmer lane is floor-protected so it never self-reports overage.

## 10. UV-P register (residuals — structural-verification-receipt frozen syntax)

- [UV-P-A: the ECR image `autom8y/asana:d11ae57` was built from git tree `d11ae574` | METHOD: CI short-SHA tag convention (no OCI revision label present) corroborated by the prior deploy tag `2362cd3`=parent commit | REASON: `imagetools inspect` returned null labels; the digest chain proves the Lambda runs image `d11ae57`, the tag convention binds `d11ae57`→`d11ae574` source]
- [UV-P-B: `-section` warmer's role in the F1a warmed-hierarchy path | METHOD: operator/topology confirmation | REASON: it is warmer-lane per the code gate and shares the wired image, but is dormant and outside the dispatch's two-Lambda scope]

---
*sre platform-engineer, PW-7 watched activation, 2026-07-21. Pre-registered
BEFORE the flip. Post-flip receipts + initial observation appended below.*

## 11. POST-FLIP RECEIPTS + INITIAL OBSERVATION

### 11.1 Flip receipts (own-hands, applied 2026-07-21 ~16:42Z)

Method: fresh `get-function-configuration` → `jq '. + {ASANA_BUDGET_ALLOCATOR_ENABLED:"true"}'`
→ `update-function-configuration --environment` (full map re-supplied; single key added).

| Function | env keys before→after | knob before→after | RevisionId (after) | UpdateStatus | CodeSha256 |
|---|---|---|---|---|---|
| autom8-asana-cache-warmer | 24 → 25 | `<ABSENT>` → `true` | aba4a8f2-f30b-44ac-97c6-f5312eb90339 | Successful | dcd96528…e106a048 (unchanged) |
| autom8-asana-cache-warmer-bulk | 20 → 21 | `<ABSENT>` → `true` | 67dd7ef1-e77d-4a4a-aad1-67ae1634e94f | Successful | dcd96528…e106a048 (unchanged) |

- **No-clobber proof:** for each function, `(after.keys) − (before.keys)` = exactly
  `{ASANA_BUDGET_ALLOCATOR_ENABLED}` and `(before.keys) − (after.keys)` = `∅`. The
  rest of the env map (incl. secret-bearing keys, never printed) is byte-preserved.
- **CodeSha256 unchanged** = the env update did not touch code; both Lambdas still run
  the wired image `d11ae57`.
- **LastModified:** cache-warmer 16:41:58Z · bulk 16:42:00Z.
- **ECS NOT flipped** (fence); `-section` NOT flipped (dormant, DISABLED schedule).

### 11.2 Initial observation (bulk warmer, first post-flip cycle)

The `-bulk` warmer's next scheduled cold start is 17:00Z (`cron(0,30 …)`); the
`update-function-configuration` invalidated the execution environment, so that
invocation binds `enabled=true` fresh and emits `allocator_boot state=active`.
Capture recorded below.

## 12. AMENDMENT 2026-07-21 ~18:00Z — P2 observation-method repair (per QA-1)

**Author:** sre observability-engineer (D-6 watch-maintenance). **Trigger:** QA-1's
material finding on the LIVE watch — probe P2 was reading a field that emits only in
the failure arm, so the watch was HALF-BLIND on the exact signal it governs.

**The defect (verified own-hands against the deployed tree `d11ae574`):**
- `parent_gids_count` is logged ONLY in the broad-catch failure arm
  (`hierarchy_warmer.py:337-341`, event `hierarchy_gap_warming_failed`). A healthy
  sweep, and a sweep KILLED by the 900s Lambda wall (SIGKILL, no catchable
  exception), emit it NEVER. Live proof: for the watched GID over the post-flip
  window `filter-pattern … parent_gids_count = *` returned **0 events**.
- The healthy-path convergence signal is `uncached_count` in
  `hierarchy_gap_fetch_starting` (`hierarchy_warmer.py:194-201`), emitted at the
  START of every sweep that has ≥1 uncached parent — success AND failure paths.
- The empty-set/complete case early-returns (`hierarchy_warmer.py:190
  `if not uncached: return 0``) and logs NOTHING — a genuine blind spot.

**The repair (observation method ONLY — no threshold or criterion changed):**
- §4 SUCCESS-3, §5 Regrowth tripwire, and §7 P2 now read `uncached_count` from
  `hierarchy_gap_fetch_starting`. The failure-arm `parent_gids_count` is literally
  `len(uncached)` (`:341`), and `uncached_count` is literally `len(uncached)`
  (`:199`) — the **SAME quantity**. Therefore the **2962** abort line, the 3291
  full-set / 3191 baseline, the ≥2-consecutive-tick and floored-sweeps-present
  conditions, and the < 3600 s staleness line ALL STAND UNCHANGED. Only the
  field/event read is corrected. The armed abort (§5→§6) is unchanged and remains
  armed.
- §7 gains **P2b**: an empty P2a is AMBIGUOUS (converged-to-zero vs GID-never-swept).
  Disambiguate via the `-bulk` checkpoint `s3://autom8-s3/cache-warmer/checkpoints/
  bulk/latest.json` (entities keyed `{gid}:{entity_type}`; per-entity status in
  `completed_entities` / `pending_entities` / `entity_results`). Never read an empty
  probe as health.

**INTERPRETATION NOTE (carried so the instrument is not misread during the peak —
does NOT alter any threshold).** Rite-disjoint forensics this session found the
live large-set NON-CONVERGENCE root cause is a **pre-flip, pre-existing image
defect**, not flip-harm: the deployed image `d11ae57` is missing the optional
`redis` package (`redis` is an extra in `pyproject.toml`/`uv.lock`), so
`RedisCacheProvider` catches `ImportError` and enters **degraded mode**
(`cache/backends/redis.py:154-159`, event `redis_package_not_installed` /
`fallback: degraded_mode`, observed firing at **15:25Z — BEFORE the 16:42Z flip**).
In degraded mode every `get_versioned`→None and every `set_batch`→no-op, so
per-chunk banking writes nothing durable: `autom8y-asana-redis-001` shows
**CurrItems=0, Evictions=0** across 24h while ~1400-1786 parents are "banked" per
tick and the next tick's `uncached_count` re-reads the full set. **Consequence for
this watch: a `uncached_count` stuck ≥ 2962 is GUARANTEED by the degraded cache and
is NOT evidence that the env-flip harmed production.** A §3.5 fire on the
stuck-high signal ALONE should be read as confirmation of the degraded-cache defect,
NOT as flip regression; auto-revert on that signal alone would remove floor pacing
without curing anything. Genuine flip-attributable abort signals remain: a new error
class, a `budget_lane_failopen` storm (observed **0**), a `hierarchy_gap_warming_failed`
spike beyond baseline, or inbound 5xx/hard-starvation. The durable fix (ship the
`redis` extra in the warmer image) is a CODE/BUILD change → next build+cert cycle,
out of this watch's env-only scope.

## 13. DEPLOY-WATCH 2026-07-21 ~19:20–19:37Z — warmer redis fix (PR #257 / b3da9d8c)

**Author:** sre platform-engineer (DEPLOY-WATCH, act-and-report PW-4/PW-7). Full
six-field receipt: `.ledge/reviews/RECEIPT-warmer-redis-fix-deploy-2026-07-21.md`.
The §12 durable fix (ship the `redis` extra) LANDED as PR #257 and auto-deployed.

### 13.1 Deploy + provenance (clean)
- Merge b3da9d8c @ 19:07:22Z → Test SUCCESS 19:14Z → Satellite Dispatch 19:13:48Z
  → autom8y/autom8y `Satellite Receiver — asana` build 29860632298 → ECR `b3da9d8`
  pushed 19:16:03Z → warmer Lambdas updated **19:20:15Z** (~13 min end-to-end).
- All 3 warmers now run `autom8y/asana:b3da9d8`, CodeSha256 **`3533b7a8…8657b3f6`**
  == the ECR digest for tag `b3da9d8` (exact match; changed from the redis-less
  `dcd96528…`). UpdateStatus Successful on all 3.

### 13.2 ⚠ STOP CONDITION — the deploy CLOBBERED the flip env
- `ASANA_BUDGET_ALLOCATOR_ENABLED`: **`true` → ABSENT** on BOTH cache-warmer (25→24
  keys) and -bulk (21→20 keys). The app's own `allocator_boot` reverted
  `active/enabled=true` → **`inert/enabled=false`** (@ 19:25:56Z). The F1a
  floor-gate is now INERT on both warmers.
- **Root cause (recurs every deploy):** the `Deploy Lambda via Terraform` build
  step terraform-applies the warmer env from the autom8y monorepo
  `terraform/services/asana/main.tf` `module.cache_warmer` (:336-344) +
  `module.cache_warmer_bulk`. That block does NOT contain the flip key (it is
  nowhere in monorepo IaC), so `terraform apply` reverts the §11.1 manual env
  mutation. Classic manual-drift-clobbered-by-IaC.
- **Consequence for THIS watch:** the 2026-07-22 09:00–12:00Z peak will observe an
  **INERT allocator** (not the cure) unless the flip is restored first. Durable
  fix = add `ASANA_BUDGET_ALLOCATOR_ENABLED = "true"` to those two module env
  blocks (cross-repo, autom8y monorepo), then re-apply §11.1 for the interim.

### 13.3 Realization probes — PARTIAL (honest read)
- **(a) PASS — the import-level cure realized.** `cache_degraded_mode` = 0 AND
  `redis_package_not_installed` = 0 across **35,158** post-deploy `-bulk` events.
  Live corroboration: `Production environment with Redis configured, using
  RedisCacheProvider`. → `import redis` resolves in prod; the §12 defect is cured
  at the import layer. This is the PR's core deliverable and it is REAL.
- **(b) NOT realized in-window — the peak does NOT yet read a real cache.**
  `autom8y-asana-redis-001` CurrItems **still 0.0**, SetTypeCmds empty (no writes),
  CurrConnections 5 (connected). Two confounds: (i) the clobbered flip → F1a
  per-chunk banking OFF (allocator inert); (ii) ⚠ a NEW unmasked transient
  `backend_entering_degraded_mode` reason **"Too many connections"** (x2,
  19:26:11–14Z, cold-start only, self-healed) — at 5 cluster connections on a
  t4g.micro this is a **client pool** limit, not the server ceiling. Whether (b)
  realizes with the flip ON is UNPROVEN (the clobber destroyed the clean test).
- **(c) no post-deploy datapoint.** Project 1203404998225231 (pre-deploy FLAT at
  `uncached_count`=2466 across 4 ticks) was not swept post-deploy in-window;
  absent a cache fill it would not shrink regardless. Deferred to the peak.

### 13.4 F-1 listener (the cert LOW advisory, TS-1 watch-only) — APPLIED LIVE
- 3 metric filters `{ $.event = "cache_degraded_mode" }` → `Autom8y/AsanaWarmerCache/CacheDegradedMode`
  on all 3 warmer log groups + alarm `asana-F1-warmer-cache-degraded-mode` (Sum>0,
  notBreaching, → `autom8y-platform-alerts`). Verified state INSUFFICIENT_DATA →
  **OK** (quiet-when-healthy). Applied via CLI (asana tf = no wired apply path);
  byte-matched code-of-record at `terraform/services/asana/warmer_cache_degraded_alarm.tf`.
- COVERAGE NOTE: F-1 catches the boot/import degrade (`cache_degraded_mode`,
  ERROR — the PR#257 companion). It does NOT catch the runtime
  `backend_entering_degraded_mode` (WARNING, base class) seen in 13.3(b). A
  sustained-threshold runtime-degrade listener is recommended (not built — a
  threshold-0 alarm on the self-healing blips would be noisy).

### 13.5 UV-P additions
- [UV-P-C: whether cache-fill (probe b/c) realizes with the flip RESTORED | METHOD: restore flip per §11.1 + durable-IaC it, then re-observe CurrItems/uncached_count | REASON: the deploy clobbered the flip before a clean post-fix+flip-on cache-fill could be observed; the transient "Too many connections" is a second, separable factor]
- [UV-P-D: the "Too many connections" client-pool limit on autom8y-asana-redis-001 | METHOD: inspect RedisCacheProvider connection-pool max vs Lambda concurrency | REASON: server maxclients (t4g.micro ~65k) is not the limit at 5 live connections; the fix unmasked it]

## 14. FLIP RESTORED DURABLY-IN-IaC 2026-07-21 ~20:15Z — clobber-proof (discharges §13.5 UV-P-C)

The §13.2 STOP condition is **RESOLVED**. The flip key is now encoded in the
monorepo IaC that the `Deploy Lambda via Terraform` step applies, so it is
clobber-proof: every future deploy PRESERVES it (no more true→ABSENT reversion).
Restored via the sanctioned service-terraform dispatch, not a manual env mutation
— so it survives the next merge.

### 14.1 The durable-IaC change (2 atomic PRs, autom8y monorepo)
- **PR #1189 (the flip)** `fix(asana-warmers): durable-in-IaC F1a budget-allocator
  flip` — adds `ASANA_BUDGET_ALLOCATOR_ENABLED = "true"` to the `environment_variables`
  of `module.cache_warmer` and `module.cache_warmer_bulk` (`terraform/services/asana/main.tf`).
  Warmers-only: `cache_warmer_section` (dormant) + all ECS untouched. Env-only,
  `terraform fmt` clean. Merged as 9db54cad. This executes the §13.2 prescribed durable fix.
- **PR #1188 (apply-safety prerequisite)** `chore(asana-tf): refresh scheduled-lambda
  image pin 2ee3391 -> b3da9d8 (live resident)` (`environments/production.tfvars`).
  REQUIRED: the dispatch apply path (`just tf-apply`, passes NO `-var image_tag`)
  reads this pin, which was stale at `2ee3391` while live is `b3da9d8` (today's redis
  fix) — so an unmodified apply would have ROLLED BACK all 6 scheduled lambdas off
  b3da9d8, undoing the redis remediation. Same drift-repair the fleet applied today
  for ASR (#1185) / EBI (#1184): pin to the live resident. Merged as 6da06311. This
  is asana "put through today's drift-repair discipline."

### 14.2 Sanctioned apply + plan-gate corroboration (own-hands)
- Dispatch `service-terraform.yml -f service_name=asana -f environment=production`
  → run **29864540858**. Stalled at the `production` env gate (required_reviewers:
  tomtenuta). Plan corroborated line-by-line BEFORE approval:
  - **`Plan: 0 to add, 3 to change, 0 to destroy`**
  - `module.cache_warmer…aws_lambda_function.main` — `environment { variables }`
    ONLY (no image_uri / layers / memory / timeout / runtime / handler) = the flip
  - `module.cache_warmer_bulk…aws_lambda_function.main` — same, env-only = the flip
  - `module.service…aws_lb_target_group.service` — benign provider-default
    materialization (`+ enable_unhealthy_connection_termination = false`,
    `+ unhealthy_draining_interval = 300`; behaviorally inert — `false` is the legacy
    no-op, the interval is dead while termination is off; in-place, no service cycle)
    = the "benign drift at most" the watch permits.
  - **ZERO image_uri lines** — warmers STAY on :b3da9d8 / CodeSha 3533b7a8.
  - Differential proof the warmer change IS the flip (env map is `(sensitive value)`
    so redacted): the #1188-only plan showed the warmers ABSENT (env == state); the
    #1189 key is the sole delta that makes the warmers appear.
  - Gate **APPROVED** by tomtenuta; apply completed **SUCCESS**.

### 14.3 Config realization (confirmed own-hands, post-apply 20:15:03Z)

| warmer | ALLOCATOR_ENABLED | keys | CodeSha256 | ImageUri |
|---|---|---|---|---|
| autom8-asana-cache-warmer | **true** | 24→**25** | 3533b7a8… (unchanged) | asana:b3da9d8 (unchanged) |
| autom8-asana-cache-warmer-bulk | **true** | 20→**21** | 3533b7a8… (unchanged) | asana:b3da9d8 (unchanged) |

Env-only realization (+1 key each, exactly reversing the §13.2 clobber); no image
roll; CodeSha unchanged. The key now lives in the tf env blocks the deploy applies.

### 14.4 Runtime realization probes (b)/(c) — [PENDING next -bulk cycle]
Baselines pinned pre-cycle (own-hands 20:16Z):
- allocator_boot: **inert/enabled=false** since the 19:25:56Z clobber (last: 20:00:12Z inert).
- **(b)** CurrItems `autom8y-asana-redis-001` = **0** across the last hour (never nonzero).
- **(c)** project 1203404998225231 (section) uncached_count = **2466** (== total_parent_gids).

Awaiting the first post-flip -bulk cold start (cron 0,30 → next tick ~20:30Z) to
observe: allocator_boot → **active/true**, CurrItems → **>0** (first nonzero in the
cluster's history), and uncached_count → **<2466** (tick-over-tick shrink, ~cycle 2
as redis persistence compounds). Results appended below when observed; if outside a
~2–3-cycle window, the 09:00–12:00Z peak reads the rest. [TO BE APPENDED]

### 14.5 SURPRISE-2 carried to the peak (not chased now)
The §13.3(b) transient `backend_entering_degraded_mode` reason **"Too many
connections"** (client-pool limit at ~5 live connections on the t4g.micro, cold-start
only, self-healed) is a SEPARATE factor from the flip. With the flip now ON, the
-bulk will bank + write under the 09:00–12:00Z peak load — so this pool limit (UV-P-D)
is the **top watch item for the peak**. NOT chased tonight; the F-1 listener (§13.4)
does NOT catch this WARNING-class runtime degrade.

### 14.6 Discharges
- §13.5 **UV-P-C** — flip RESTORED durably-in-IaC (the METHOD is executed); the
  cache-fill re-observation (b/c) is in-flight per §14.4. **UV-P-D** remains OPEN
  (peak watch item).

## 15. OVERNIGHT READ 2026-07-22 08:12–08:25Z (own-hands, ~23 post-flip -bulk cycles) — flip REALIZED, fill NOT; UV-P-D promoted to ROOT CAUSE

**Author:** sre platform-engineer (watch cadence, pre-peak). Credentials re-authed 08:12Z.

**(a) Flip runtime realization — CONFIRMED.** `allocator_boot state=active, enabled=true`
on all -bulk boots observed in the last 2h (4 events). The durable-IaC key (§14.1)
binds in production. `budget_lane_failopen` = 0 across 13h — the allocator gate is
healthy. Boot-class `cache_degraded_mode` = 0 (F-1 alarm stays quiet-correct for its
class).

**(b) Cache fill — NOT REALIZED; §13.5 UV-P-D is the CONFIRMED root cause, and it is
NOT a cold-start transient:**
- `backend_entering_degraded_mode` reason **"Too many connections"** (WARNING,
  RedisCacheProvider): **34 events over 13h**, latest 08:00:13.938Z + 08:00:14.245Z
  (two entries 300 ms apart ⇒ ≥2 provider instances or rapid re-entry; the mixin logs
  only on fresh entry, so 34 entries = the pool exhausts on essentially every cycle,
  cycling degrade→reconnect→re-exhaust).
- **`SetTypeCmds` on `autom8y-asana-redis-001` has NO datapoints in the window — zero
  write commands have EVER reached the server.** `CurrConnections` FLAT at 5.0;
  `CurrItems` = 0.0 every 30-min sample (unchanged, never nonzero).
- -bulk checkpoint: **1 of 68 entities completed**; watched GID 1143843662099250 and
  1203404998225231 both still `pending` (the sweep thrashes: fetch → bank-to-void →
  900s wall → restart). Watched-GID `uncached_count` read 158 → 3191 overnight
  (in-memory degraded fallback in a warm container, then full set on cold).
- `OfferFrameAgeSeconds{1143843662099250}` overnight Max: repeatedly >3600 — 11,933
  (23:13Z) · 11,942 (03:13Z) · **14,583 (05:43Z)** · 11,945 (07:13Z). The sawtooth is
  uncured, as it must be while banking writes nothing.

**Interpretation (extends §12, same law):** a stuck-high `uncached_count` / staleness
through today's 09:00–12:00Z peak is the UV-P-D pool defect, NOT flip-harm — **do NOT
revert on it**. Genuine flip-attributable abort signals (§5) remain armed and none
have fired.

**Alarm-surface note (promotes §13.4 coverage gap to load-bearing):** this kill runs
entirely in the WARNING-class runtime event; the F-1 boot-class alarm cannot see it.
The fix must carry a LOUD companion for sustained runtime degrade.

**Action (act-and-report):** fix lane DISPATCHED 08:26Z — root-cause the exact pool
mechanics on the deployed tree (RedisConfig max 10 @ redis.py:61 vs adapter 20 @
autom8_adapter.py:179 vs dead setting settings.py:216 vs COLD_CONCURRENCY 24; observed
ceiling ~5), build the durable fix + two-sided proofs, stop at PR-ready. Merge/deploy
follows the established cert chain (deploys are flip-proof per §14.1). Peak reads
continue on cadence; today's peak documents the defect unless the fix lands in-window.

## 16. GATE-1 LANDING 2026-07-22 09:55–10:05Z — FIRST-EVER BANKING; §15 root cause CURED-LIVE

**The §15 hypothesis was refined by the builder and the cure LANDED same-morning.**
Root cause (falsifies the fan-out theory; change-warden reproduced by execution
against locked redis-py 7.2.1): `_initialize_pool` passed `ssl`/`ssl_cert_reqs`
kwargs that `Connection.__init__` rejects at checkout while `make_connection`
increments `_created_connections` BEFORE constructing — each TypeError permanently
leaks a slot; at cap 20 → `MaxConnectionsError("Too many connections")` → sticky
degraded mode. **Zero TCP connections were ever established in this service's
production life** (flat CurrConnections 5 = ElastiCache engine baseline).

**Chain (all 2026-07-22):** fix built + two-sided-proven (RED reproduces the live
signature against a real RESP server; GREEN banks under 24-way fan-out) → PR #259 →
rite-disjoint change-warden cert **PASS** (own-hands repro; CA-default-load proven by
execution — `ssl.create_default_context()`, 128 CAs; deployed `REDIS_SSL=true`
matches cluster `TransitEncryptionMode=required`) → merged @ origin/main **10d7c559**
(09:21Z) → satellite deploy → all 3 warmers on `asana:10d7c55` / CodeSha `a56a628c`
@ 09:34:57Z. **★#1189 clobber-proofing passed its first live deploy: the flip
SURVIVED** (`=true` on both warmers; `-section` fence held, knob absent).

**Landing receipt (own-hands, server-side ground truth):**
1. **`SetTypeCmds` posted its FIRST datapoints in cluster history** — from 09:55Z,
   steady ~440/~3,200 per minute alternation.
2. **`CurrItems` 0 → 8,020 (09:58Z) → 8,918 (10:00Z), climbing** — first items ever.
3. `backend_entering_degraded_mode` ("Too many connections") on -bulk: **0** post-fix.
4. `redis_connection_kwargs_invalid` boot tripwire: **0** (negative control clean).
5. Watched-GID collapse: PENDING queue rotation — the 10:00Z -bulk sweep is banking
   project 1200944186565610 (`uncached_count=788`) with durable writes for the first
   time; watched GID 1143843662099250 still `pending` in the checkpoint.

Writes began at 09:55Z, BEFORE the 10:00Z warmer cron — the early writer is almost
certainly the asana **ECS service** rolled onto `10d7c55` by the same deploy (its
read-through/hydration path shares the fixed constructor; exact task-revision
corroboration not yet pinned — inference, marked honestly). The fix un-broke the
cache for EVERY provider consumer, not only the warmer lane.

**Honest rung:** cure = **LIVE and banking**. §4 SUCCESS (sawtooth <3600s through a
diurnal peak + uncached convergence) is NOT yet claimable — it needs the compounding
window (today's peak tail reads + tomorrow's 09:00–12:00Z peak). §5 abort criteria
remain armed; nothing has fired. F1a mask ledger: unwired (#256) → unpackaged
(#257) → unconstructible (#259) → **banking**.

