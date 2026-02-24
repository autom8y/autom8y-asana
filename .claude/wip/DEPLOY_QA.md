# Deploy QA Workflow

Repeatable post-deploy validation workflow for autom8y-asana.

## Prerequisites

- Commits on `main`, CI green, ready to push (or already pushed)
- Env vars: `ASANA_BOT_PAT`, `ASANA_SERVICE_KEY`, `ASANA_WORKSPACE_GID`
- AWS CLI configured with ECS/CloudWatch/S3 access

## Phase 1: Push & CI

```bash
git push origin main
# Monitor CI
gh run list --repo autom8y/autom8y-asana --limit 3
gh api repos/autom8y/autom8y-asana/actions/runs/<RUN_ID>/jobs \
  --jq '.jobs[] | "\(.name): \(.status) \(.conclusion)"'
```

Wait for all 4 jobs: lint-check, unit-tests, full-regression, integration-tests.

## Phase 2: Satellite Deploy

```bash
# Satellite dispatch triggers automatically on Test workflow success
gh run list --repo autom8y/autom8y --limit 3
gh api repos/autom8y/autom8y/actions/runs/<RUN_ID>/jobs \
  --jq '.jobs[] | "\(.name): \(.status) \(.conclusion)"'
```

Wait for: Validate Payload → Build and Push → Deploy to ECS → Deploy Lambda.

## Phase 3: ECS Stabilization

```bash
# Check rollout status
aws ecs describe-services --cluster autom8y-cluster --services autom8y-asana-service \
  --query 'services[0].{status:status,desired:desiredCount,running:runningCount,deployments:deployments[*].{status:status,rollout:rolloutState}}'

# Check task health
aws ecs describe-tasks --cluster autom8y-cluster \
  --tasks $(aws ecs list-tasks --cluster autom8y-cluster --service-name autom8y-asana-service --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{lastStatus:lastStatus,healthStatus:healthStatus,startedAt:startedAt}'
```

Wait for: rollout=COMPLETED, healthStatus=HEALTHY.

## Phase 4: Smoke Test

```bash
.venv/bin/python scripts/smoke_test_api.py
```

Self-discovering — uses APIs to find test fixtures. 18 tests across 4 tiers.
Expected: 15 passed, 3 skipped, 0 failed.

Override fixtures if needed:
```bash
SMOKE_OFFER_GID=... SMOKE_UNIT_PHONE=... SMOKE_UNIT_VERTICAL=... \
  .venv/bin/python scripts/smoke_test_api.py
```

## Phase 5: Freshness Audit

```bash
# Check freshness metadata on all entity types
python3 -c "
import httpx, os, json, pathlib
service_key = os.environ.get('ASANA_SERVICE_KEY')
if not service_key:
    for line in pathlib.Path('.env/production').read_text().splitlines():
        if line.startswith('export ASANA_SERVICE_KEY='):
            service_key = line.split('=', 1)[1].strip().strip('\"')
            break
jwt = httpx.post('https://auth.api.autom8y.io/internal/service-token',
    json={'service_name': 'autom8y-asana'},
    headers={'X-API-Key': service_key}, timeout=15).json()['access_token']
hdrs = {'Authorization': f'Bearer {jwt}', 'Content-Type': 'application/json'}
for entity in ['unit', 'business', 'offer', 'contact', 'asset_edit', 'asset_edit_holder']:
    meta = httpx.post(f'https://asana.api.autom8y.io/v1/query/{entity}/rows',
        headers=hdrs, json={'select': ['gid'], 'limit': 1}, timeout=30).json().get('meta', {})
    print(f'{entity:20s} freshness={meta.get(\"freshness\"):20s} age={meta.get(\"data_age_seconds\",0):6.0f}s  ratio={meta.get(\"staleness_ratio\",0):5.1f}x')
"
```

**Healthy**: freshness=fresh or approaching_stale, ratio < 2x.
**Degraded**: freshness=stale, ratio > 5x — SWR not promoting to memory (see GAP below).

## Phase 6: Log Audit (if freshness degraded)

```bash
# SWR triggers
aws logs filter-log-events --log-group-name /ecs/autom8y-asana-service \
  --start-time $(date -v-2H +%s)000 --filter-pattern 'swr_refresh' \
  --query 'events[*].message' --output text | tr '\t' '\n'

# Build results (check total_rows)
aws logs filter-log-events --log-group-name /ecs/autom8y-asana-service \
  --start-time $(date -v-2H +%s)000 --filter-pattern 'build_result_classified' \
  --query 'events[*].message' --output text | tr '\t' '\n'

# S3 watermarks (compare with memory age)
for gid in 1201081073731555 1200653012566782 1143843662099250 1200775689604552; do
  echo "=== $gid ==="
  aws s3 cp s3://autom8-s3/dataframes/$gid/watermark.json - 2>/dev/null | python3 -m json.tool
done
```

**Key signal**: If `build_result_classified` shows `total_rows: 0` with `sections_delta_updated > 0`, the SWR memory promotion bug is active. Fix: `BuildResult.total_rows` must use `len(self.dataframe)`.

## Known Issues

| Issue | Impact | Fix |
|-------|--------|-----|
| `/health/deps` returns 404 via gateway | Low (internal-only endpoint) | Not exposed through ALB, no action needed |
| SWR `total_rows=0` prevents memory promotion | HIGH — all entities serve stale data indefinitely | Fixed in `build_result.py` — deploy pending |
