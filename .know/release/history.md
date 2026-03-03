---
domain: release/history
generated_at: "2026-03-03T19:01:00Z"
source_scope:
  - "./.know/release/"
generator: pipeline-monitor
source_hash: "394d61c"
confidence: 0.90
format_version: "1.0"
update_mode: "full"
incremental_cycle: 0
max_incremental_cycles: 0
---

# Release History

## Log

### 2026-03-03 (4) — autom8y-asana HOTFIX release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS (after 1 retry)
- **Duration**: ~20 min (including retry)
- **Commit released**: 394d61c — fix(cascade): add parent_gid case to DataFrameViewPlugin derived field extraction
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **Chain timing**: test 3m 50s, dispatch 13s, receiver attempt 1 failed (2m 31s), receiver attempt 2 green (~9m)
- **ECS deploy**: Rolling deployment, smoke test passed (attempt 2)
- **Run IDs**: test=22637797551, dispatch=22637942164, receiver=22637949056 (attempt 2)
- **Retry**: satellite-receiver.yml failed on transient Sigstore attestation 401 (attempt 1). Rerun via `gh run rerun --failed` succeeded on attempt 2.
- **Notable**: 4th release of the day. Sigstore flakiness flagged as SRE-scope concern. Recon skipped via cached platform profile.

### 2026-03-03 (3) — autom8y-asana P0 HOTFIX release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS
- **Duration**: 12m 21s (chain only)
- **Commit released**: a24311a — fix(cascade): use put_batch_async for gap warming instead of warm_ancestors
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **Chain timing**: test 3m 54s, dispatch 7s, receiver 8m 17s
- **ECS deploy**: Rolling deployment, smoke test passed
- **Run IDs**: test=22636195393, dispatch=22636346659, receiver=22636350887
- **Notable**: P0 hotfix for production hierarchy warmup (Step 5.3 warm_hierarchy_gaps broken). Recon skipped via cached platform profile. Third release of the day.

### 2026-03-03 (2) — autom8y-asana PATCH release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS
- **Duration**: 11.9 min (chain only)
- **Commit released**: 9606712 — fix(cascade): persist parent_gid to repair hierarchy on S3 resume
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **Chain timing**: test 4m 0s, dispatch 11s, receiver 7m 39s
- **ECS deploy**: Rolling deployment, smoke test passed
- **Run IDs**: test=22634870350, dispatch=22635032893, receiver=22635039337
- **Notable**: Clean PATCH, no blocking issues. Second release of the day.

### 2026-03-03 — autom8y-asana PATCH release

- **Repos**: autom8y-asana
- **Complexity**: PATCH (no dependents)
- **Outcome**: PASS
- **Duration**: ~2.5 hours (including CI infra fix cross-session)
- **Commits released**: 12 on origin/main (9 feature + 2 CI retry + 1 lint fix)
- **Key commit**: c141e1b (lint fix that unblocked CI)
- **Pipeline chain**: test.yml → satellite-dispatch.yml → satellite-receiver.yml
- **ECS deploy**: Rolling deployment, smoke test passed
- **Blocking issues resolved**:
  - INFRA: Reusable workflow resolution failure (fixed via autom8y-workflows extraction)
  - LINT-001: 22 ruff UP042 StrEnum violations (15 files)
  - TEST-001: 3 entity registry ordering assertions
  - DISPATCH-001: Org secrets visibility (private → all for public repo)
- **Run IDs**: test=22630104172, dispatch=22630885109, receiver=22630902492
- **Notable**: First release after CI migration from autom8y/autom8y to autom8y/autom8y-workflows
