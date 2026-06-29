---
type: handoff
status: draft
handoff_status: pending
source_rite: releaser
target_rite: operator/IC (deploy authority)
initiative: cr3-clean-break-cutover
created: 2026-06-05
evidence_ceiling: STRONG  # 3-repo state read AT SOURCE (SVR) + rite-disjoint re-verify; self-authored synthesis MODERATE
discipline: RELEASE PROCESSION readiness cert. Reversible/read-only authorship. PR-only; all prod gates HELD. Secrets names/scope only. Verify-at-source; default-to-REFUTED.
---

# CR-3 RELEASE PROCESSION — Gate-2 (DEPLOY) readiness cert (releaser rite, Sprint 1)

**Telos:** cutover *done* = both arms LIVE on the receiver (VERIFICATION-REALIZED), NOT #60-merged. **Current: `cutover_state = MERGED_NOT_DEPLOYED`** (rite-disjoint-verified). Gate-1 (#60 merge) DONE; Gate-2 (deploy) READY-HELD for operator/IC env-approval.

## §1. Verified platform-state-map (SVR receipts; 3 repos at source)
**CONSUMER (autom8y/autom8) — the gating arm:**
- #55 (`merged 2026-06-04T12:25:08Z`), #58 (`2026-06-05T11:47:27Z`), #60 (`2026-06-05T13:15:23Z`) ALL merged → origin/main HEAD **`86bf029d`**.
- #60 SPOF fix LIVE + sound on main (`config/satellite_config.py:420-440`): SM-first by default; env override only behind fail-secure `_resolver_env_secret_override_allowed() = (not is_running_on_cloud()) and (not is_production_func())` — any single prod signal denies it; deliberately avoids `AWS_EXECUTION_ENV` (AST-locked).
- **NOT DEPLOYED:** `monolith-prod` runs task-def **`:382`** / ECR `autom8_monolith:prod` pushed **2026-05-31** (predates all 3 merges by ~4 days), rollout COMPLETED 1/1. **The cutover code is not running.**
- `ASANA_RESOLVER_CLIENT_SECRET` ABSENT from `:382` (secrets=null) → the SM-first gate will be effective on deploy (no inert env override in the running env).

**RECEIVER (autom8y/autom8y-asana) — deployed + healthy:** task-def **`:481`**, image `asana:28ae50b` (== origin/main HEAD `28ae50b8`), cpu2048/mem8192 (§D substrate), rollout COMPLETED, AMP `up{job=asana}=1`. Section warm lane DURABLY PAUSED (Lambda `reserved_concurrency=0` + EventBridge `DISABLED`); `FRESHNESS_CONTRACT_MAX_AGE_SECONDS["section"]=3000` live.

**SECRETS:** Secret-1 `autom8y/asana-dataframe-resolver` provisioned (not deleted, changed 2026-06-03); Secret-2 `autom8y/auth/service-api-keys/asana-dataframe-resolver` still live. BOTH last-accessed 2026-06-05 (day-granularity — does NOT prove the cutover path exercises Secret-1; the deployed May-31 image can't run the SM-first code, so live auth most plausibly still rides Secret-2).

## §2. Pre-deploy gate (Phase 1) — CLEARED
- **PF-1 #60 security/threat-model:** GO_WITH_CONDITIONS, `closes_spof=true` — fail-secure gate, no fail-open path; fail-safe-to-legacy preserved; secrets not logged.
- **PF-2 Secret-1 provisioned:** ✅ PASS (the cartographer's flagged forward-risk — RESOLVED).
- **PF-3 IAM:** ✅ PASS — task role `autom8_EcsTaskRole` → `autom8_EcsTaskPolicy` grants `secretsmanager:GetSecretValue` + `DescribeSecret`. The runtime boto3 SM-fetch will have access; absent ECS secrets-block is the CORRECT topology for #60.
- **PF-4 .env-bake:** MINOR/non-blocking for the RUNTIME SPOF (final-layer scrub + baked `WORKDIR /var/task` makes the override fail-secure regardless of BRANCH). Residual = secret recoverable from the earlier `COPY .env` image layer (supply-chain) + tautological build assertion → **fast-follow** (rotate Secret-1 + BuildKit `--mount=type=secret`), NOT a deploy blocker.
- **Pytest receipt** (the no-CI gap): autom8 has NO `.github/workflows`; the satellite AC-1..AC-7 suite never runs in CI. Receipt EXISTS from the SPOF sprint (`f217e585` == merged content: 27/27 resolver + 199 regression, ruff clean). **Pre-deploy condition: run the suite in the deploy build OR accept this local receipt; durable fix = wire CI.**

## §3. Gate-2 (DEPLOY) — the decision, HELD for operator/IC
**Deploy = the cutover goes live ONLY here. PROD GATE: env approval.** Build a post-#60 monolith image (MUST be downstream of `86bf029d` — H-3) and roll `monolith-prod` to it via the satellite chain (test.yml push → Satellite Dispatch → autom8y/autom8y Satellite Receiver).
**Post-deploy load-bearing gate before soak entry (PDG / AC-6 — a FUNCTIONAL-PATH canary, not a 2xx-liveness probe):**
- **PDG-3:** the prod monolith mints a real token via Secret-1 SM-fetch → satellite returns **HTTP 200**; AMP `receiver_query_outcome_total{...,success}` increments.
- **PDG-2:** confirm NO `ASANA_RESOLVER_CLIENT_SECRET` in the running container env (name-only).
- both arms (`project` + `section`) route `/v1/query`.
If PDG-3 fails, the SM-first code fails safe to legacy SDK (no env secret present) → **satellite auth would silently fall to legacy — the cutover would NOT be live**. AC-6 is what proves it real.

## §4. Hazards (from dependency-resolver)
- **H-1 CRITICAL:** deploy before Secret-1 SM-fetch live-verified → silent fallback to legacy. *Mitigation: AC-6/PDG-3 before soak.*
- **H-2 CRITICAL:** Secret-2 decommission before live-verify+soak strands the auth fallback. *Secret-2 stays live until AC-6 PASS + soak + IC.*
- **H-3 CRITICAL:** deploying a pre-`86bf029d` image re-arms the SPOF. *Verify the built image SHA is downstream of the #60 merge.*
- **H-4 MEDIUM:** section warm-lane reactivation before stability → 503 bursts (serve-stale 3000s is the backstop; keep paused until CQ-RETURN-3).
- **H-5 ADVISORY:** autom8 declares `autom8y-core>=4.1.0` vs receiver `>=4.2.0` — no runtime impact; follow-up floor bump.

## §5. Rollback boundaries
- **RB-1 PRE-SB-1 flag-OFF** (`satellite_get_df_enabled`→False; tested 2/2 @ `14586df8`): both arms → legacy SDK, ~30s ECS rolling, no redeploy. *Caveat: flag defaults True on main — a re-deploy without explicit override re-enables satellite.*
- **RB-2** section warm lane paused (both knobs set). **RB-3** receiver serve-stale net (3000s). **RB-4** Secret-2 retained for re-injection until decommission gate. **ECS:** `update-service --task-definition monolith-prod:382` (prior rev), pre-authorized.

## §6. Remaining procession (HELD — human/IC deliberate)
P2 **Deploy** [env approval] → P2 **AC-6 live-verify** → P3 **7-day soak** (long-pole 10080 min; per-arm ≥99%, capacity_502=0, ell-lag under real load) → P4 **Stage-B** [IRREVERSIBLE, IC sign-off; gated on clean soak + Platform §9.3 ell-lag headroom review] → P5 **Secret-2 decommission** [IRREVERSIBLE, LAST; gated on PDG-2/3 + task-#73 SPOF closed + Secret-2 access stopped].

## §7. Fast-follows (non-blocking)
Rotate Secret-1 + move build off `COPY .env` to BuildKit secret (supply-chain; with #73) · wire the satellite AC suite into autom8 CI · bump autom8 `autom8y-core` floor to `>=4.2.0` · correct #60 docstring (cwd not BRANCH is the baked prod-authority).

*Releaser rite, Sprint 1, 2026-06-05. SVR-disciplined, rite-disjoint-verified. Reversible/read-only; deploy + Stage-B + Secret-2 decommission stay the operator/IC's deliberate action. The cutover is NOT live until AC-6/PDG-3 passes.*
