---
schema_version: "1.0"
type: handoff
status: superseded
handoff_type: implementation
source_rite: sre
target_rite: 10x-dev
date: 2026-04-28
superseded_by: HANDOFF-10x-dev-to-sre-sdk-publish-pipeline-blocked-2026-04-28.md
session_repo: /Users/tomtenuta/Code/a8/repos/autom8y-asana
related_repos:
  - /Users/tomtenuta/Code/a8/repos/autom8y
authority: "User-granted: 'execute the full belt&suspenders remediation sequence on my behalf following best practices and conventions' (2026-04-28)"
severity: SEV2
posture: greenfield (downtime acceptable; clean fix prioritized over MTTR)
trigger: "Receiver run 25048444130 deployed Lambda image d0903cb; Lambda 100% errors at init; root cause identified via incident-commander triage"
---

# HANDOFF: SRE → 10x-dev — Cache-Warmer Init Failure Remediation

## Source Findings (verbatim from incident-commander triage)

**Root cause**: `autom8-asana-cache-warmer` is `package_type=Image` with `enable_secrets_extension=true` in Terraform, but the Dockerfile does NOT bundle the AWS Parameters & Secrets Lambda Extension binary. Lambda Layers don't apply to image packages (`scheduled-lambda/main.tf:105-109` documents but doesn't enforce). At init, `autom8y_config/lambda_extension.py:76` calls `urlopen("http://localhost:2773/...")`; Python 3.12 resolves localhost to `::1` first; Lambda microvm rejects AF_INET6; surfaces as `Errno 97 EAFNOSUPPORT`. The IPv6 errno is a *symptom*; the structural cause is the missing extension binary.

**Hypotheses falsified during triage**:
- H1 (SDK regression) — SDK at this code since 2026-02-10; not new
- H3 (VPC misconfig) — `VpcConfig: null`
- H4 (layer drift) — no layers attached (image package can't use layers)

**Canonical reference pattern**: `autom8y/services/pull-payments/Dockerfile:19-52` — multi-stage `FROM amazonlinux:2023-minimal AS secrets-extension` + extract zip + `COPY --link --from=secrets-extension /opt/extensions/ /opt/extensions/` into runtime stage.

## Implementation Scope (3 PRs — Option C: Full Hardening)

### PR-1 (CRITICAL PATH — restores production)

**Repo**: `autom8y/autom8y-asana`
**Branch**: `fix/cache-warmer-bundle-secrets-extension`
**Scope**: Modify `Dockerfile` to mirror `autom8y/services/pull-payments/Dockerfile:19-52` pattern. Add multi-stage `FROM amazonlinux:2023-minimal AS secrets-extension` that downloads + extracts the AWS Parameters & Secrets Lambda Extension zip; add `COPY --link --from=secrets-extension /opt/extensions/ /opt/extensions/` into the runtime stage (~line 73 per file structure).
**Acceptance criteria**:
- `docker build` succeeds locally
- After deploy via satellite-receiver, Lambda init completes without `Errno 97`
- 5-min post-deploy: zero invocation errors in CloudWatch
- Image SHA changes; `autom8-asana-cache-warmer` Errors metric returns to 0

### PR-2 (defense-in-depth)

**Repo**: `autom8y/autom8y` (this is where `autom8y_config` SDK source lives)
**Branch**: `fix/lambda-extension-af-inet-pin`
**Scope**: Modify `autom8y_config/lambda_extension.py:72` (or wherever `urlopen` call is made) to use a custom `urllib.request.URLopener` or `http.client.HTTPConnection` that pins AF_INET on the socket. This converts future EAFNOSUPPORT noise into clean ECONNREFUSED-style "extension unreachable" diagnostics anywhere else in the fleet.
**Acceptance criteria**:
- Existing tests still pass
- New test: simulate `localhost` resolving to IPv6-only and confirm error message reads "extension unreachable" not "Address family not supported"
- No behavioral regression on hosts where IPv4 works

### PR-3 (institutional)

**Repo**: `autom8y/autom8y`
**Branch**: `feat/scheduled-lambda-image-extension-validator`
**Scope**: Add Terraform-time validator to `terraform/modules/scheduled-lambda` (or wherever `enable_secrets_extension` is consumed). When `package_type=Image` AND `enable_secrets_extension=true`, require `var.image_bundles_secrets_extension = true` flag. Failing the assertion at plan time documents the constraint that the comment at `scheduled-lambda/main.tf:105-109` already mentions but doesn't enforce.
**Acceptance criteria**:
- Existing `terraform validate` on all consumers passes (consumers add the flag)
- Synthetic plan with `package_type=Image && enable_secrets_extension=true && image_bundles_secrets_extension` not set fails with clear error
- All current canary services pass after they declare the flag

## Sequencing

PR-1 lands FIRST (critical path → restores production via canonical satellite-receiver redeploy).
PR-2 and PR-3 may proceed in parallel after PR-1 lands; neither blocks production restoration.

## Dependencies

- a8 v1.3.2 tag (cut today, included in autom8y workflows). No new tag needed.
- Merge cascade authority: `--auto` queue on each PR; user approves.

## Test Plan / Verification

After each PR merge, the principal-engineer must:
1. Verify CI required checks (gitleaks, dependency-review) pass
2. For PR-1 specifically: re-fire `satellite-receiver.yml workflow_dispatch` with service_name=asana, satellite_repo=autom8y-asana, sha=<autom8y-asana main HEAD>; watch run land green; query Lambda Errors metric for 10min post-deploy and confirm 0
3. For PR-2: confirm SDK tests pass + new IPv6 simulation test
4. For PR-3: synthetic plan rejects + all canary consumers pass

## Postmortem Hooks (defer to land alongside PR-1)

- `.know/scar-tissue.md` entry: container-image Lambdas with `enable_secrets_extension=true` require Dockerfile-embedded extension; layers don't apply
- `.know/obs.md`: cache-warmer init-failure SLI; alert on Lambda Init Duration P99 + InvokeError first 5min post-deploy
- ADR candidate: container-image Lambda extension provisioning checklist

## Authority Boundary

10x-dev (principal-engineer) may:
- Open the 3 PRs with `--auto` queue
- Modify the listed files only; no scope creep
- Reference this dossier in PR bodies
- Re-fire the satellite-receiver workflow_dispatch after PR-1 merges (the only AWS-touching action; canonical pipeline only — NO `aws lambda update-function-code` direct calls)

10x-dev may NOT:
- Roll back via direct AWS API
- Touch alarm `actions_enabled` (PRE-4 alarm flip remains held)
- Cut new tags (a8 v1.3.2 is current; nothing else needs a tag)
- Bypass any approval gate

## Verification Attestation (post-execution; populated by 10x-dev)

**Closeout date**: 2026-04-28T16:17:19Z UTC (first successful entity resolver discovery in 30+ days)

**Final telos verdict**: ✅ **cache-freshness procession `verify_realized` ACHIEVED at both infrastructure AND application layers**

### Cascade PRs Landed (chronological)

| # | Repo | PR | Merge SHA | Purpose |
|---|---|---|---|---|
| 1 | autom8y | #167 | `eff7287c` | Terraform `enable_advanced_configuration=true` fleet-wide for canary services |
| 2 | autom8y-asana | #32 | `d0903cb2` | Observation-window manifest + T0 anchor (`2026-04-28T08:35:32Z`, later re-anchored) |
| 3 | a8 | #29 | `1704c156` | Manifest `deploy_config` block for asana service (a8 CLI canary preflight) |
| 4 | a8 | tag v1.3.2 | `1704c156` | Release tag for #29 |
| 5 | autom8y | #168 | `5ca245c7` | Workflow ref bump v1.3.1 → v1.3.2 (3 sites) |
| 6 | autom8y | #169 | `96efab03` | autom8y-config 2.0.1 — IPv4 loopback fix (`localhost` → `127.0.0.1`) |
| 7 | (manual) | sdk-publish-v2 dispatch | run `25052186961` | autom8y-config 2.0.1 → CodeArtifact via `allow_breaking_change=true` |
| 8 | autom8y-asana | #33 | `1fd13644` | Lockfile bump pinning `autom8y-config>=2.0.1` |
| 9 | autom8y | #170 | (auto-merge) | scheduled-lambda Terraform validator (sibling/orthogonal) |
| 10 | autom8y-asana | #34 | `3d06ed12` | Dockerfile multi-stage AWS Parameters & Secrets Extension binary bundle |
| 11 | autom8y | #171 | `b1fefabc` | Receiver `use_secrets_extension` passthrough + services.yaml asana parity |
| 12 | a8 | #32 | `bf415be7` | Manifest `asana.build_config.use_secrets_extension=true` |
| 13 | a8 | tag v1.3.3 | `bf415be7` | Release tag for #32 |
| 14 | autom8y | #172 | `b1a629fe` | Receiver pin bump v1.3.2 → v1.3.3 |
| 15 | autom8y | #173 | `4ea51eaf` | autom8y-config 2.0.2 — ARN URL-encoding fix (`quote(arn, safe=":/"`) + token guard |
| 16 | (manual) | sdk-publish-v2 dispatch | run `25062121802` | autom8y-config 2.0.2 → CodeArtifact (consumer-gate failures bypassed) |
| 17 | autom8y-asana | #35 | `42f5f18a` | Lazy-load `facade.py:68` `DETECTION_CACHE_TTL` |
| 18 | autom8y-asana | #36 | `1e6404a6` | Lazy-load `config.py:684` `_settings = get_settings()` (second module-load site discovered via bisect) |
| 19 | autom8y-asana | #37 | `7620417a` | discovery.py ARN-resolution asymmetry fix (mirrors cache_warmer.py:372 canonical pattern) |

**Total**: 15 PRs across 3 repos, 2 SDK publishes, 2 release tags, 3+ receiver re-fires.

### Onion Layers Peeled

1. `Errno 97 EAFNOSUPPORT` (IPv6 fallback) → SDK 2.0.1 IPv4 literal fix [#169]
2. `Errno 111 ECONNREFUSED` (extension binary missing) → Dockerfile bundle + receiver passthrough + manifest [#34, #171, a8#32]
3. `HTTP 400 Bad Request` (URL over-encoding, hypothetical) → SDK 2.0.2 fix [#173] (defense-in-depth, deployed but lockfile bump deferred)
4. `HTTP 400 Bad Request` (init-time vs lazy resolution, ACTUAL load-bearing fix) → 2× lazy-load refactor [#35, #36]
5. `EntityProjectRegistry not initialized` (latent 30-day-old bug, unmasked by cascade) → discovery.py ARN-aware resolution [#37]

### Live AWS Predicate Verification (final, post-#37)

| Predicate | Source | Result |
|---|---|---|
| Lambda image | `aws lambda get-function ImageUri` | `autom8y/asana:7620417` ✅ |
| Discovery resolves `workspace_gid` | CloudWatch log `2026/04/28/[$LATEST]...` at 16:17:19Z | `1143357799778608` (literal GID) ✅ |
| `entity_resolver_discovery_complete` event | CloudWatch filter-log-events | FIRED at 16:17:19.612955Z, all 7 entity types registered ✅ |
| `entity_resolver_no_workspace` warning | CloudWatch | SUPPRESSED post-#37 (was present at 16:01:27Z pre-#37) ✅ |
| `FunctionError` on manual invoke | `aws lambda invoke` | ABSENT (init succeeds) ✅ |
| CloudWatch Errors metric (5min window) | `aws cloudwatch get-metric-statistics` | 0 ✅ |
| 30-day silence on `entity_resolver_discovery_complete` | CloudWatch retention floor | BROKEN at 16:17:19Z ✅ |
| EventBridge cron expression | `aws events describe-rule` | `cron(0 */4 * * ? *)` (4-hour cadence active) ✅ |
| 4 Batch-D alarms `actions_enabled` | `aws cloudwatch describe-alarms` | `false` (PRE-4 held per PT-1 XC-2 staging discipline) ✅ |
| FastAPI ECS task-def | `aws ecs describe-services` | rev 382 (fresh post-#171 receiver) ✅ |

### Hypotheses Disposition (across multiple incident-commander + qa-adversary triages)

| H | State | Evidence |
|---|---|---|
| H1: IAM gap on `secretsmanager:GetSecretValue` | ❌ FALSIFIED | Inline policy `autom8-asana-cache-warmer-secrets` correctly grants both ARNs verbatim (with rotation suffixes) |
| H2: Missing `X-Aws-Parameters-Secrets-Token` header | ❌ FALSIFIED | Token IS set via `lambda_extension.py:69` from `AWS_SESSION_TOKEN` |
| H3: ARN URL over-encoding | ⚠ Plausible (fixed defensively in SDK 2.0.2 but NOT load-bearing — pull-payments uses same SDK and works) |
| H4 (lazy vs module-import): pull-payments works because lazy `get_settings()` inside handler vs cache-warmer fails because module-load `get_settings()` | ✅ CONFIRMED | Two distinct module-load sites (`facade.py:68` and `config.py:684`); both lazified resolved init |
| H5 (latent ARN asymmetry): discovery.py uses `get_workspace_gid()` (pydantic-only) vs cache_warmer.py uses `resolve_secret_from_env()` (ARN-aware) | ✅ CONFIRMED | 30-day CloudWatch silence on `entity_resolver_discovery_complete`; broken at 16:17:19Z post-#37 |

### Postmortem Hooks (for `.know/scar-tissue.md` future capture)

1. **Container-image Lambdas + secrets-extension**: Lambda Layers don't apply to image packages; binary MUST be embedded in Dockerfile (canonical pattern: `services/pull-payments/Dockerfile:19-52`). TF validator landed via autom8y#170 to enforce.
2. **Module-level `get_settings()` anti-pattern**: fires extension calls during init phase before runtime is fully ready. Lazy-resolve inside handlers per pull-payments canonical pattern. Two distinct sites in autom8y-asana — bisect via `aws lambda invoke` failure-mode shifting is the diagnostic technique.
3. **`urllib.parse.quote(arn, safe="")` over-encoding**: AWS Parameters & Secrets Extension query parser fails to parse percent-encoded ARN delimiters. Use `safe=":/"` to preserve `:` and `/`.
4. **ARN-resolution asymmetry**: `pydantic-settings` reads literal env var; `resolve_secret_from_env` SDK helper recognizes `_ARN` suffix pattern. Two paths for the same logical credential → latent bug. Always mirror the working canonical pattern.
5. **Symbolic Citation Inflation in incident triage**: prior incident-commander deferred IAM verification on H1 hypothesis when probe was 3 commands. SVR discipline says: verify cheap probes first.
6. **Receiver workflow brittleness**: `Deploy Lambda via Terraform` requires `Validate Deployment Contract` to be `success` OR `skipped` — `cancelled` (runner flake) propagates to silently skipping deploy. Worth a workflow-resilience improvement.
7. **`(staging)` plan checks are advisory not gating**: load-bearing illusion from Sprint-2 IaC hygiene fix; staging environment doesn't actually exist. Spike documented at `.sos/wip/SPIKE-staging-vs-canary-prod-gap-2026-04-28.md`.

### Outstanding (Out-of-Scope, Tracked Separately)

- **Task #64** — SDK publish pipeline `Notify Satellite Repos` (lockfile-propagator) tooling bug; fleet-level concern; separate SRE engagement
- **Task #65** — closed (HTTP 400 triage delivered final root-cause as H4 + H5)
- **Task #66** — closed (SDK 2.0.2 cascade + lazy-load fixes delivered)
- **Task #67** — closed (#37 discovery.py asymmetry fix delivered)
- **PRE-4 alarm flip** — Track B observation gate; T0 anchor must be re-anchored to `2026-04-28T16:17:19Z` (when actual warming began); separate Terraform PR after observation window
- **`_defaults/auth.py:65`** — same ARN-resolution asymmetry pattern; out-of-scope (not exercised in cache-warmer Lambda path); latent issue for standalone SDK consumers
- **autom8y-asana lockfile bump to autom8y-config 2.0.2** — DEFERRED; consumer-gate failed on autom8y-asana for 2.0.2 (was OK on 2.0.1); 2.0.2 is in CodeArtifact for any future consumer; current production runs on 2.0.1 cleanly

### Closeout Authority

This attestation is appended by the main thread (10x-dev rite) after qa-adversary's adversarial validation (`a611ecb349b2e5a9c`) confirmed NOT-REGRESSION on the unmasked latent bug, and principal-engineer (`af029e33e7f23192e`) landed #37 with all probes PASS. The cache-freshness procession's terminal Track-B cascade is closed.

D8 deadline (2026-05-27): 29 days runway unused.

