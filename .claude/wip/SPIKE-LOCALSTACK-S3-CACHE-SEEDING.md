# SPIKE: LocalStack S3 DataFrame Cache Seeding

**Session**: session-20260302-165404-dfdf5ad1
**Date**: 2026-03-02
**Status**: COMPLETE
**Time-box**: 30 min (actual: ~15 min)

## Problem Statement

The asana service's progressive preloader completes but loads **0 of 7 projects** — all skipped with:
> "no manifest or parquet, no Lambda ARN — skipping"

The auth fix (dev bypass returning ServiceClaims) is verified working. The 503 CACHE_NOT_WARMED is the next layer down.

## Root Cause

**Gap in the progressive preloader's fallback chain** when S3 is available but empty.

The 4-tier resolution in `api/preload/progressive.py:320-399`:

| Tier | Condition | Action | Local Dev? |
|------|-----------|--------|------------|
| 1 | S3 manifest exists | Resume from checkpoint | NO — bucket empty |
| 2 | S3 `dataframe.parquet` exists | Load directly | NO — bucket empty |
| 3 | No manifest/parquet, Lambda ARN set | Delegate to Lambda | NO — no ARN configured |
| 4 | No manifest/parquet, no Lambda ARN | **Skip** | YES — this is what happens |

The legacy preload fallback (ADR-011, `legacy.py`) only triggers when `persistence.is_available == False` (S3 unreachable). But in local dev, LocalStack S3 **is** reachable — the `autom8-s3` bucket exists and is healthy. It's just empty.

**Code path**: `progressive.py:253` checks `persistence.is_available` → `True` (LocalStack up) → enters progressive path → per-project: no manifest, no parquet, no Lambda → skip at line 391.

## Options Evaluated

### Option A: "Cold Start" Fallback in Progressive Preloader (RECOMMENDED)

When manifest=None, parquet=None, Lambda=None — instead of skipping, allow the progressive builder to do a full API fetch.

**Implementation**: ~20 lines in `progressive.py`. When all three tiers fail:
- If `AUTOM8Y_ENV == "local"` or `CACHE_WARM_ALLOW_FULL_FETCH=true`: proceed to `builder.build_progressive_async(resume=False)` (line 401 equivalent)
- Otherwise: skip (preserves production safety)

**The OOM concern** (comment at line 320-325) is valid for production (tens of thousands of tasks per project) but irrelevant for local dev with small datasets. Environment-gating handles this.

**Pros**: Self-healing cold start. No external dependencies. Uses existing progressive builder.
**Cons**: Requires ASANA_PAT + Asana API access. Takes ~60-120s for 7 projects.
**Risk**: Low. The progressive builder already handles full fetches when manifest exists.

### Option B: Seed LocalStack S3 with Production Snapshot

Script to download DataFrame parquets from production S3 and upload to LocalStack.

**Pros**: Instant warm start. No Asana API calls needed.
**Cons**: PII exposure (production data has phone numbers, names). Requires PII scrubbing pipeline. Snapshot staleness. Must be re-run when schema changes.
**Risk**: Medium. PII handling is a liability.

### Option C: Run Lambda Handler Locally

Invoke `lambda_handlers/cache_warmer.py:handler()` directly as a management command.

**Pros**: Uses the same code path as production.
**Cons**: Lambda handler has specific event format, timeout detection, self-invocation logic. Needs adaptation for local execution.
**Risk**: Medium. Lambda handler is complex (1000+ lines).

### Option D: Force Legacy Preload via Env Var

Add `CACHE_PRELOAD_STRATEGY=legacy` override that bypasses progressive → legacy.

**Pros**: Simple. Legacy preload builds from Asana API directly.
**Cons**: Doesn't exercise progressive path. Legacy preload is deprecated (ADR-011). Two code paths to maintain.
**Risk**: Low but backwards.

## Recommendation

**Option A** — cold-start fallback in the progressive preloader, gated by `AUTOM8Y_ENV == "local"`.

This is the minimal, architecturally correct fix:
1. Fills the gap in the fallback chain (empty S3 + no Lambda = should still work)
2. Uses existing progressive builder (no new code paths)
3. Environment-gated (production behavior unchanged)
4. Produces manifests + parquets in LocalStack S3 on first run (subsequent starts resume from Tier 1/2)

### Proposed Change (progressive.py ~line 390)

```python
# Current: skip
else:
    logger.warning(
        "progressive_preload_no_manifest_no_lambda",
        ...
    )
    return False

# Proposed: cold-start fallback for local dev
else:
    env = os.environ.get("AUTOM8Y_ENV", "")
    allow_full_fetch = os.environ.get("CACHE_WARM_ALLOW_FULL_FETCH", "").lower() == "true"
    if env == "local" or allow_full_fetch:
        logger.info(
            "progressive_preload_cold_start_full_fetch",
            extra={
                "project_gid": project_gid,
                "entity_type": entity_type,
                "reason": "no manifest/parquet/Lambda, cold-start full fetch enabled",
            },
        )
        # Fall through to builder.build_progressive_async() below
    else:
        logger.warning(
            "progressive_preload_no_manifest_no_lambda",
            ...
        )
        return False
```

## Prerequisites

- `ASANA_PAT` must be set in the host environment (passed through docker-compose.override.yml)
- `ASANA_WORKSPACE_GID` must be set
- First warm takes ~60-120s (7 projects × Asana API). Subsequent starts resume from S3 in ~5s.

## Dependencies

- This is an **asana service** change (this repo)
- No cross-service changes needed
- LocalStack bucket creation already handled by `init-aws.sh`

## Decision

Spike complete. Option A recommended for implementation via `/build` or `/hotfix`.
