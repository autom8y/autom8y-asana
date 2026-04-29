---
type: review
status: draft
---

# INCIDENT: autom8-asana-cache-warmer Lambda init failure — `autom8y_config` localhost IPv6 EAFNOSUPPORT

**Severity**: SEV2
**Status**: ACTIVE — hotfix forward in progress
**Detected**: 2026-04-28T11:01Z (CloudWatch alarm `autom8-asana-cache-warmer-lambda-errors` ALARM at 10:58Z UTC)
**Declared**: 2026-04-28T11:18Z (incident commander)
**Greenfield**: yes (downtime tolerated per user authority)

## Roles

- **Incident Commander**: Claude (Opus 4.7) acting as Incident Commander
- **Decision authority**: user (tenuta.tommy@gmail.com) — granted explicit authority for hotfix-forward path
- **Technical Lead**: Incident Commander (sole responder; greenfield + tolerated downtime)
- **Comms**: not required — greenfield, no external customers

## Scope

- **Affected**: 100% of `autom8-asana-cache-warmer` Lambda invocations fail at module-import init.
- **Unaffected**: ECS FastAPI service (`autom8-asana` task-def 382) — separate execution path; same image, but ECS does not invoke the cache-warmer handler entry-point and Pydantic Settings build at the failing site is exercised under different env-var conditions there. ECS env presumably does not set `*_ARN` keys.
- **Blast radius**: cache-freshness procession is non-functional; cron schedule `cron(0 * * * ? *)` produces 3 errored invocations every hour; no successful warming has occurred since first deploy.

## Verified Facts (SVR receipts)

- Current Lambda image: `696318035277.dkr.ecr.us-east-1.amazonaws.com/autom8y/asana:d0903cb` (`aws lambda get-function`, exit 0). Verified at 2026-04-28T11:16Z.
- `d0903cb2` resolves to commit `chore(sre): Batch-D observation-window manifest + T0 baseline anchor (#32)` on autom8y-asana main.
- Diff `9110e80..d0903cb` on autom8y-asana = ONE file (markdown manifest); NO code change. The previous tagged image `9110e80` should have failed identically — and CloudWatch metrics confirm: invocations=errors=3 every cron hour going back to 2026-04-23T04:00:00+02 (`aws cloudwatch get-metric-statistics`, exit 0).
- **The Lambda has never successfully warmed a cache** since first scheduled invocation. This reframes the incident: `SEV2-greenfield-never-shipped`, NOT regression-on-deploy. The receiver-run-25048444130 deploy correlation was incidental, not causal.
- CloudWatch alarm `autom8-asana-cache-warmer-lambda-errors` state: ALARM, ActionsEnabled=true, Threshold=1.0 (`aws cloudwatch describe-alarms`, exit 0).
- Verbatim error: `[ERROR] RuntimeError: Failed to resolve secret via Lambda extension at http://localhost:2773: <urlopen error [Errno 97] Address family not supported by protocol>` (`aws logs get-log-events` on `2026/04/28/[$LATEST]65e93f3d12a1487d9f0ee559d16b5dfd`, exit 0).
- `Errno 97` = `EAFNOSUPPORT`.
- Stack trace anchors confirmed verbatim: `autom8y_config/lambda_extension.py:76` (`resolve_secret_arn`), `:113` (`resolve_secret_from_env`), `base_settings.py:307`, `:249`, `autom8_asana/settings.py:904`, `models/business/detection/facade.py:68` (init-time call to `get_settings()`).

## Contributing Factors (NOT root cause — per Cook 1998, Reason 1997)

1. **`autom8y_config/lambda_extension.py:40` hardcodes `f"http://localhost:{port}"`** (file-read at `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-config/src/autom8y_config/lambda_extension.py:40`, verbatim: `return f"http://localhost:{port}"`). Python 3.12 + Lambda runtime resolves `localhost` to IPv6 `::1` first via `getaddrinfo`. AWS Parameters & Secrets Lambda Extension binds IPv4 only on `127.0.0.1:2773`. `urlopen` attempts AF_INET6, kernel returns EAFNOSUPPORT, no fallback to IPv4 occurs.
2. **No Lambda-runtime integration test on the secret-extension code path**. SDK tests at `/Users/tomtenuta/Code/a8/repos/autom8y/sdks/python/autom8y-config/tests/test_lambda_extension.py` mock `urlopen` directly, never exercising the `localhost` resolution behavior. Unit tests pass green; the IPv6/IPv4 resolution mismatch only surfaces under real Lambda runtime.
3. **No deploy-time smoke invocation gate in the receiver workflow**. The satellite-receiver workflow that deployed image `d0903cb` (`autom8y/autom8y` run 25048444130) did not test-invoke the Lambda after pushing the image. Init-time failures of this class would surface the moment a smoke invocation runs.
4. **CI test discipline does not cover Lambda-runtime context**. `pytest` runs on a developer/CI host where `localhost` resolves consistently; the IPv6-first behavior only manifests in the AWS Lambda execution environment.
5. **Cron-driven invocation pattern delays detection**. The Lambda is invoked once per hour; the CloudWatch alarm requires 1 datapoint above threshold over 5-minute period; alarm fires only when error datapoints land in alarm window. Detection latency for this defect class is hours, not minutes.
6. **No canary post-deploy invocation**. A single synthetic invocation triggered immediately after deploy (per `canary-signal-contract` discipline) would have surfaced this before the first cron-fire.

## Decision Tree (war-room reasoning)

**Option A — rollback to image `9110e80`**: rejected. Metrics show `9110e80` had identical 100% failure rate; rollback is not a fix. Earlier image `latest`-tag drift was incidental.

**Option B — hotfix forward in `autom8y-config` SDK**: SELECTED.
- Patch `lambda_extension.py:40` `localhost` → `127.0.0.1`.
- Add regression test asserting URL uses literal IPv4.
- Bump SDK version `2.0.0` → `2.0.1`.
- Publish to CodeArtifact via `sdk-publish-v2.yml`.
- Bump pin in `autom8y-asana/pyproject.toml` to `>=2.0.1`.
- Refresh `uv.lock`.
- Merge & deploy via satellite-receiver dispatch.

**Option C — Lambda environment variable workaround** (e.g., set `localhost` resolution in `/etc/hosts` via Dockerfile): rejected. Higher surface area than the SDK fix; no tests; doesn't fix other satellites that import `autom8y-config`.

## Timeline (UTC)

- **2026-04-23T04:00Z** (approx): first scheduled cron invocation. 3 errors. (Inferred from CloudWatch retention.)
- **2026-04-23 → 2026-04-28**: ~5 days of silent 100% failures. CloudWatch alarm not yet active (presumably enabled later or in lower-actions state).
- **2026-04-28T08:57Z**: Lambda image updated to `d0903cb` (no-op code change; only markdown manifest added). LastModified per `aws lambda get-function`.
- **2026-04-28T10:58Z**: CloudWatch alarm `autom8-asana-cache-warmer-lambda-errors` transitioned to ALARM (Threshold=1.0, ActionsEnabled=true).
- **2026-04-28T11:01Z**: incident detection event.
- **2026-04-28T11:18Z**: incident declared SEV2; user authorized hotfix-forward (Option B).
- **2026-04-28T11:30Z**: contributing-factor analysis complete; SDK fix authored.
- **2026-04-28T11:30Z** → **resolution**: SDK PR + asana PR sequence in flight (see Action Items).

## Action Items

(Owners and dates assigned per blameless framing — fixes are systemic, not individual; Dekker 2006.)

| ID | Action | Owner | Due | Status |
|----|--------|-------|-----|--------|
| AI-1 | Add Lambda-runtime smoke-invocation test on `autom8y-config` SDK that exercises real `urlopen` against a local IPv4-only HTTP server (and verifies it does NOT use `localhost`). | Platform Engineer (autom8y-config maintainer) | 2026-05-05 | OPEN |
| AI-2 | Add post-deploy synthetic invocation to satellite-receiver workflow as a deploy-time gate per `canary-signal-contract` discipline. Must run a single synthetic invocation against the deployed Lambda and require success before marking deploy `success`. | Platform Engineer (autom8y receiver workflow owner) | 2026-05-12 | OPEN |
| AI-3 | Audit other satellites that import `autom8y-config>=2.0.0` and verify no other Lambdas are silently failing the same way. Search candidates: `autom8y-ads`, `autom8y-sms`, `autom8y-scheduling`, `autom8y-hermes`, `autom8y-data`. | Incident Commander | 2026-04-29 | OPEN |
| AI-4 | Tighten `autom8y-config` pin in `autom8y-asana/pyproject.toml` from `>=2.0.1` to `>=2.0.1,<3.0.0` to prevent inadvertent major-version drift; same for all sibling satellites. | Platform Engineer | 2026-05-05 | OPEN |
| AI-5 | Document IPv4-vs-IPv6 loopback gotcha in `autom8y-config` README and add to platform `scar-tissue.md`. | Documentation rite | 2026-05-12 | OPEN |
| AI-6 | Verify CloudWatch alarm action enablement matches deployment readiness — `autom8-asana-cache-warmer-lambda-errors` had `ActionsEnabled=true` but the Lambda never worked; confirm no false-positive on prior batches. | Observability Engineer | 2026-05-05 | OPEN |
| AI-7 | Open complaint (`/reflect` zone) for the receiver-deploy correlation framing in the original incident dispatch; the deploy was incidental, not causal. The dispatch reasoning attributed regression to a deploy that diff'd 1 markdown file — receiver-correlation heuristic needs a `git diff --stat` sanity check before assuming regression. | Process / Knossos rite | 2026-05-19 | OPEN |

## Postmortem (Blameless)

### What happened
The `autom8-asana-cache-warmer` Lambda has been failing 100% on init since first scheduled invocation on 2026-04-23. CloudWatch metrics confirm 3 errors per cron-hour every hour for the entire 5-day observation window. The CloudWatch alarm transitioned to ALARM at 10:58Z UTC on 2026-04-28, triggering incident detection at 11:01Z — five days late.

### Why it happened (contributing factors, not "root cause")
The five contributing factors documented above. The trigger was Python 3.12 + AWS Lambda runtime IPv6-first `localhost` resolution intersecting with an IPv4-only Parameters & Secrets Lambda Extension binding. The latent conditions were: (1) no Lambda-runtime integration test in SDK CI, (2) no deploy-time smoke invocation gate, (3) cron-driven invocation pattern delays detection, and (4) CloudWatch alarm only fires when a 5-min datapoint window contains errors — a 1-error-per-hour cron pattern often misses windows entirely. Cook 1998 (II:SRC-001 [STRONG]) is the relevant frame: the trigger was the IPv6 resolution change, but the system was already running in degraded mode (a cache-warmer that has never warmed). Reason 1997 (II:SRC-003 [STRONG]) Swiss-cheese model: each defense layer (unit tests, CI, alarm) had a hole — the holes aligned and the failure went undetected for 5 days.

### What we did
1. Bisected the SDK version (no regression — bug present since `lambda_extension.py` introduction in commit `019ac8cf`, Feb 2026).
2. Reframed from "regression on deploy" to "never-worked-since-deploy".
3. Authored 1-character-class fix in `autom8y-config/src/autom8y_config/lambda_extension.py:40` (`localhost` → `127.0.0.1`).
4. Added regression test asserting URL uses IPv4 and explicitly does NOT contain `localhost`.
5. Bumped SDK version `2.0.0` → `2.0.1`.
6. PR autom8y/autom8y#169 opened, auto-merge enabled, merged at 2026-04-28T11:21:57Z. SDK publish workflow triggered.
7. Asana hotfix branch `hotfix/autom8y-config-2.0.1-pin` prepared with pin bump; awaiting SDK publish completion before lock refresh.

### What went well
- Direct verification of actual Lambda image SHA, image diff, and CloudWatch metrics caught the framing error early ("regression on deploy" was incorrect; the Lambda was already broken).
- 1-character-class fix kept change surface minimal.
- Worktree-isolated branches kept the working tree of both repos clean throughout.
- Auto-merge with required-checks passing avoided force-merge.

### Where we got lucky
- This is greenfield. No customer impact.
- The receiver-run-correlation framing in the dispatch led to an early bisect step that surfaced the metrics-history reframe quickly.
- The Lambda extension uses HTTP not HTTPS — no certificate trust to navigate.
- The defect is in stdlib `urllib`, fully isolatable; no third-party HTTP client involved.

### What we'd change
- Add Lambda-runtime smoke testing to SDK CI (AI-1).
- Add post-deploy synthetic invocation as a deploy gate (AI-2).
- Audit fleet for similar latent bugs (AI-3).

## Resolution

Pending — awaiting SDK publish to CodeArtifact, then asana pin-bump PR + uv.lock refresh + receiver-dispatch deploy + post-deploy CloudWatch verification. Updates appended below as they land.
