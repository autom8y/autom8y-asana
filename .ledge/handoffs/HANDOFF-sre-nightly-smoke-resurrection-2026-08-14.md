# HANDOFF H-1 — nightly-smoke-resurrection (sre lane) — 2026-08-14

**Session**: session-20260814-164401-9e5da9d5 · complexity MODULE · main thread sole dispatcher
**Stop line**: both cures merged + deployed + two-sided-proven → H-1 → park. **ALL MET.**

## CURE 1 — Nightly Live Smoke (PR #372, MERGED 2026-08-14T15:27:16Z)

**Root cause (superseded both prior theories).** Not the OIDC exchange; not the header-predicted
IAM AccessDenied. The `autom8y-config` (2.1.0) pytest11 plugin's AUTOUSE fixture
`config_clean_env` (`autom8y_config/testing/fixtures.py:33-48`, `_ENV_PREFIXES` includes `"AWS_"`)
deletes every `AWS_*` env var at EVERY test's setup. The OIDC step exported valid credentials
(run 31788902866 log: `Authenticated as assumedRoleId AROA2EH6KAVGS6WN3ULFE:GitHubActions`;
`AWS_ACCESS_KEY_ID: ***` present in every subsequent step env); the smokes' import-time skip
gate saw them and RAN; the fixture then deleted them before the first boto3 call →
`botocore.auth.py:429 NoCredentialsError`, every night since 2026-06-11 inception.
**Workstation mask**: the same deletion falls through to `~/.aws` SSO (chain: env removed →
sso found) — proven live with fake env creds signing as `ASIA…` SSO creds under pytest, and as
the fake key outside pytest. The detector never worked anywhere; local greens were phantom.

**Fix** (one file, `.github/workflows/nightly-live-smoke.yml`):
1. `-p no:autom8y_config` (nightly = designated non-hermetic run; `Test` keeps the plugin);
2. cred-bridge (operator-ruled): OIDC role's sole S3 grant is
   `autom8y-terraform/duckdb-extensions/*` (read live 2026-08-14, policy
   `github-actions-deploy-policy` Sid `S3MysqlScannerVendorFetch`) → smoke step runs with the
   bridged pair from Secrets Manager `autom8_env` (role inline grant Sid `CIReadAutom8EnvSecret`),
   masked, step-scoped, `AWS_SESSION_TOKEN` unset. Bridged principal HEAD-read the live smoke
   object (12,932 B, LastModified 2026-08-10T09:58:26Z) pre-flight.
3. page-on-red (see meta-gap).

**Two-sided proof**:
- RED history: 60/60 scheduled failures 2026-06-11 → 2026-08-14 (inception-red side).
- GREEN: branch dispatch run **31813754242** → `5 passed in 1.11s`, `0 skipped`,
  "forcing function satisfied". First green in the workflow's life.
- Broken-input RED (discriminating canary — input, never an injected defect): repo var
  `ASANA_CACHE_S3_BUCKET=autom8-smoke-broken-input-proof` → dispatch run **31814393336** →
  `4 failed, 1 passed` (the 4 live reads correctly failed; registry test needs no S3) → job RED
  → page fired. Var deleted immediately after (verified 0 remaining).
- Deployed-path GREEN on main post-merge: run **31814673368** → completed SUCCESS — `5 passed in 1.33s`, 0 skipped, forcing function satisfied.
- Durable check: first scheduled run of the cured workflow ≈ **2026-08-15T09:15Z** — worth an eye.

## Meta-gap — why 60 red nights paged nobody (CURED, proven live)

Scheduled-run failures notify only Actions-tab watchers; the fleet's live alert route
(`autom8y-platform-alerts` → Slack lambda + email) never knew this workflow existed. Cure:
`if: failure()` step publishes there via the cred-bridge — **proven on the broken-input RED**:
SNS `MessageId 99e8d676-169c-5440-8b12-b48f2326e88d`, "published to autom8y-platform-alerts".
**Honest limit (pegged, owner = /sre lane)**: failures BEFORE the cred-bridge step (checkout,
OIDC exchange) cannot page; if that recurs, the durable fix is a CloudWatch-side dead-man on the
workflow's green heartbeat, not more in-job wiring.

## CURE 2 — StoryWarm SEV-1 paging leg (PR #373, MERGED 2026-08-14T15:39:12Z, squash 04e5cb24)

**Gap**: CC-5 (#369) built the receipt surface; **zero alarms** watched any StoryWarm metric
(describe-alarms by MetricName, live 2026-08-14: 0) — the binding-blind shape
(`observability_alarms.tf:104-116`) one lane over.

**Shape — dead-man, deliberately NOT failure-count**: `StoryWarmFailure` 7d baseline =
89/152 hours nonzero, p50 19/h, max 100/h → a `failure>0` alarm ≈60% alarm duty (AL-5 flap
class reborn). Alarm `autom8y-asana-story-warm-dead` (fleet SEV-1 naming
`autom8y-<service>-<class>`): `Sum(StoryWarmSuccess) <= 0`, period 7200 (2× the hourly :19-:21
emission slot — AL-5 anchor-drift scar honoured), 2-of-2, `treat_missing_data=breaching`.
7-day replay: **0 false fires, 1 true would-have-paged** (real 10h lane silence
2026-08-12T10:21Z–20:21Z).

**Dimension drift, documented not hidden**: production warmer
(`autom8-asana-cache-warmer`, `AUTOM8Y_ENV=production`) leaves `ASANA_CW_ENVIRONMENT` unset →
`ObservabilitySettings.environment` defaults `"staging"` (`settings.py:793-795`) → the alarm
watches `autom8y/cache-warmer` / `environment=staging`, the series the production lane
ACTUALLY writes. NO production-labeled StoryWarm series exists anywhere.

**Routing**: dual-route per fleet doctrine (`autom8y` repo
`scheduling_stratum_producer_alarms.tf:174-181` — both topics on both action lists):
`autom8y-platform-alerts` + `autom8y-platform-sre-sev1` (subscribers verified live 2026-08-14:
SMS +1248****32 + email — the sre_paging.tf "0 subscribers" comment is STALE; the
production.tfvars "LIVE SMS" comment is the true one).

**Deploy**: F-1 pattern (code-of-record tf + CLI apply; this tf tree has no apply pipeline; the
sitting AL-5 re-point diff in `observability_alarms.tf` untouched by construction —
`put-metric-alarm`, zero terraform-state interaction). Applied 15:25:08Z actions-disabled →
first evaluation OK on real data 15:26:48Z ("2 of 2 datapoints [599.0, 981.0] not <= 0") →
actions enabled 15:27:19Z (fires nothing).

**Synthetic paging proof (operator-ordered), full cycle receipts** (alarm history, UTC):
- 15:27:21.247 StateUpdate OK → ALARM (synthetic, reason marked SYNTHETIC)
- 15:27:21.303 Action **Successfully executed** → `autom8y-platform-alerts`
- 15:27:21.372 Action **Successfully executed** → `autom8y-platform-sre-sev1` ← **the page**
- 15:27:59.383 StateUpdate ALARM → OK (auto re-evaluation = the reset)
- 15:27:59.416/.439 Action Successfully executed → both topics (recovery notices)
- SNS corroboration: `NumberOfMessagesPublished` ≥1 on the sev1 topic in the 15:23–15:28Z bucket.
- MODERATE-cap honesty: "Successfully executed action" proves CloudWatch→topic delivery; the
  SMS/email last hop rides the topic's live subscriptions (operator's own endpoints — the two
  buzzes at ≈17:27:21/17:27:59 local are the operator-side corroboration).

## Evidence discipline

Every load-bearing claim above carries a mechanical anchor (run id, policy Sid, file:line,
alarm-history timestamp) read own-hands this session; self-attestation capped MODERATE
throughout. UV-P (deferred): the 2026-08-15T09:15Z scheduled run's conclusion.

## Walls audit

FLAG-1 lever (`ASANA_STORY_WARM_PRIORITY_ENTITIES`) untouched · Tier-2 untouched (no IAM
mutation, no fleet-stack writes; alarm applied via the era's CLI pattern) · atomic per-cure
PRs #372/#373, both merged manually on green under the biting secrets gate (#373 after a
strict-mode branch update and one gate RED investigated to ground — finding 6) · client-facing
behavior: none.

## Findings routed (surfaced, not absorbed — charter §7)

1. **FLEET CLASS — `config_clean_env` kills live-credential tests fleet-wide**: any repo using
   `autom8y-config`'s pytest11 plugin + live smokes inherits this exact silent-kill; the SSO
   fallback masks it on every workstation. Route: scar-tissue entry + upstream SDK improvement
   (marker-based opt-out, e.g. `@pytest.mark.live_credentials`). Owner: fleet SDK lane.
2. **Env-label drift**: production warmer emits `environment=staging`
   (`ASANA_CW_ENVIRONMENT` unset). Fixing = Lambda env change + redeploy
   (workflows-env-tag-drift class). When fixed, re-point the alarm dimension in the same PR.
3. **Stale fleet comment**: `autom8y/terraform/shared/sre_paging.tf:25-32` claims 0 sev1
   subscribers; live topic has SMS+email. One-line doc fix in the autom8y repo.
4. **Durable successor for the cred-bridge**: read-only `autom8-s3/asana-cache/tasks/*` grant
   on `github-actions-deploy` (autom8y#481). When landed: delete the bridge step;
   `-p no:autom8y_config` stays.
5. **"SEV-1 cornerstone patterns" has no doc referent** (thorough sweep). The real authority:
   `PAGING-SIGNAL-CONTRACT-fleet-sre-sev1-2026-07-01.md` + `terraform/shared/sre_paging.tf`
   (autom8y repo). Future briefs should cite those.

6. **Enforcing secrets gate can RED transiently on ref churn, leaving no forensic artifact**:
   #373's post-update-branch gate run REDDED with "leaks found: 3" (run 31814981590,
   1625 commits scanned); a rerun on the byte-identical headSha passed clean (1624
   commits), and local 8.24.3 scans (same config, same baseline, single-ref AND
   --all) found zero — the 3 findings attributed to a ref that existed only during
   the #372 branch-deletion window. NOT a secret in the tree. Route: consider a
   redacted-FINGERPRINT log line in gitleaks-enforcing.yml (fingerprints are not
   secrets) so a transient RED stays attributable post-hoc. Owner: /sre lane.

## State for the next session

- Nightly Live Smoke: cured on main; watch 2026-08-15T09:15Z scheduled run.
- `autom8y-asana-story-warm-dead`: LIVE, actions enabled, state OK, dual-routed. Import into
  terraform state when an apply path lands (command in the file header).
- Worktree `wt.sre.nightly-smoke-resurrection.20260814T151308.d81533cc` — reap after close.
