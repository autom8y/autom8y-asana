# SPIKE: INDEX_UNAVAILABLE Error - Missing S3 Configuration in ECS

**Date**: 2026-01-10
**Status**: Complete
**Timebox**: 30 minutes

## Question

Why is the Dynamic Resolution API returning `INDEX_UNAVAILABLE` errors for all entity types (unit, business, contact, offer) when it was working previously?

## Decision This Informs

Whether the issue is:
1. A code regression
2. An infrastructure configuration issue
3. A transient S3/cache failure

## Context

The demo script `scripts/demo_dynamic_api.sh` returns `INDEX_UNAVAILABLE` for all resolution requests:

```json
{
  "results": [
    {
      "gid": null,
      "gids": null,
      "match_count": 0,
      "error": "INDEX_UNAVAILABLE"
    }
  ]
}
```

The schema discovery endpoint still works correctly, indicating the API itself is healthy.

## Research Approach

1. Traced `INDEX_UNAVAILABLE` error origin in codebase
2. Analyzed DataFrame cache initialization path
3. Reviewed Terraform configuration for ECS and Lambda deployments
4. Compared environment variable configuration between services

## Findings

### 1. Error Origin

`INDEX_UNAVAILABLE` is generated in `src/autom8_asana/services/universal_strategy.py:145` when `_get_or_build_index()` returns `None`.

```python
if index is None:
    results.append(
        ResolutionResult.error_result("INDEX_UNAVAILABLE")
    )
```

### 2. Failure Chain

The index becomes unavailable when:
1. `DynamicIndexCache` has no cached index for the entity/column combination
2. `DataFrameCache.get_async()` returns `None`
3. Legacy strategy build also fails

### 3. Root Cause: Missing S3 Environment Variable in ECS

**The ECS task definition is missing `ASANA_CACHE_S3_BUCKET` environment variable.**

| Component | `ASANA_CACHE_S3_BUCKET` | `ASANA_CACHE_S3_PREFIX` |
|-----------|------------------------|------------------------|
| **Lambda (cache_warmer)** | ✅ `autom8-s3` | ✅ `asana-cache/project-frames/` |
| **ECS (asana service)** | ❌ **MISSING** | ❌ **MISSING** |

Evidence from Terraform:

**Lambda (`autom8-cache-lambda/main.tf:66-79`):**
```hcl
environment {
  variables = {
    ASANA_CACHE_S3_BUCKET = var.s3_bucket      # ✅ Configured
    ASANA_CACHE_S3_PREFIX = var.s3_prefix      # ✅ Configured
    ...
  }
}
```

**ECS (`services/asana/main.tf:102-115`):**
```hcl
additional_environment = {
  "SERVICE_ENV" = var.environment
  "APP_ENV"     = var.environment
  "LOG_LEVEL"   = "INFO"
  "API_HOST"    = "0.0.0.0"
  "API_PORT"    = "8000"
  "AUTH_JWKS_URL" = "..."
  "AUTH_ISSUER"   = "..."
  "AUTH_DEV_MODE" = "false"
  # ❌ ASANA_CACHE_S3_BUCKET is NOT configured
  # ❌ ASANA_CACHE_S3_PREFIX is NOT configured
}
```

### 4. Cache Initialization Behavior

Without `ASANA_CACHE_S3_BUCKET`, the cache factory returns `None`:

```python
# src/autom8_asana/cache/dataframe/factory.py:75-86
if not settings.s3.bucket:
    logger.warning(
        "dataframe_cache_s3_not_configured",
        extra={
            "detail": (
                "ASANA_CACHE_S3_BUCKET not set. "
                "DataFrameCache will not be available. "
                "Resolution strategies will build DataFrames on every request."
            ),
        },
    )
    return None
```

### 5. Why This Started Failing

The system **likely worked before** because:
1. There was a code path that built DataFrames on-demand without cache
2. A deployment or code change removed or broke that fallback
3. The cache warmer Lambda populated S3, but ECS can't read it

The Lambda warmer writes to S3, but the ECS service cannot read from S3 because it doesn't know the bucket name.

## Recommendation

**Fix Required**: Add S3 cache configuration to ECS service Terraform.

**File**: `autom8y/terraform/services/asana/main.tf`

**Change**:
```hcl
additional_environment = {
  # ... existing vars ...

  # S3 Cache Configuration (matches Lambda cache_warmer)
  "ASANA_CACHE_S3_BUCKET" = "autom8-s3"
  "ASANA_CACHE_S3_PREFIX" = "asana-cache/project-frames/"
}
```

## Verification

After deploying the fix:

```bash
# 1. Deploy Terraform changes
cd terraform/services/asana
terraform apply

# 2. Force ECS service deployment
aws ecs update-service --cluster autom8y-production --service asana \
  --force-new-deployment

# 3. Wait for stable deployment
aws ecs wait services-stable --cluster autom8y-production --services asana

# 4. Run demo script
./scripts/demo_dynamic_api.sh
```

Expected result: Resolution requests return actual GIDs instead of `INDEX_UNAVAILABLE`.

## Follow-Up Actions

| Action | Owner | Priority |
|--------|-------|----------|
| Add S3 env vars to ECS Terraform | Platform | **Critical** |
| Add startup health check for cache availability | Satellite | Medium |
| Document cache architecture requirements | Satellite | Low |

## Related Files

- `src/autom8_asana/services/universal_strategy.py:145` - Error origin
- `src/autom8_asana/cache/dataframe/factory.py:75-86` - Cache init check
- `src/autom8_asana/settings.py:237-266` - S3Settings class
- `terraform/services/asana/main.tf:102-115` - Missing env vars
- `terraform/modules/autom8-cache-lambda/main.tf:66-79` - Working Lambda config

## Conclusion

The root cause is a **missing infrastructure configuration**, not a code bug. The ECS service Terraform is missing `ASANA_CACHE_S3_BUCKET` and `ASANA_CACHE_S3_PREFIX` environment variables. Without these, the DataFrameCache cannot initialize, and all resolution requests return `INDEX_UNAVAILABLE`.

The fix is straightforward: add the missing environment variables to match the Lambda cache warmer configuration.
