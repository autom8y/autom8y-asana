---
type: review
slug: STATE-OF-PLAY
status: accepted            # recognized lifecycle status (ratified binding surface)
content_status: measured-ground-truth   # brief-specified content semantic (not a lifecycle value)
rite: sre
date: 2026-07-13
aws_account: 696318035277
aws_region: us-east-1
baseline: origin/main f713dd30
re-verify-by: 2026-07-14
self_assessment_ceiling: MODERATE  # self-ref-evidence-grade-rule: SRE-authored measured-facts surface
skills:
  - "@structural-verification-receipt"   # every platform-behavior row carries a receipt or is UV-P
  - "@telos-integrity-ref"               # per-item file:line receipt-grammar; no wave-level tokens
  - "@throughlines:index:denominator-integrity"  # G-DENOM: the log-group axis cannot separate EBI-driven service calls
---

# STATE-OF-PLAY — Measured Ground-Truth Surface (autom8y-asana substrate attribution)

## Purpose

This is the **measured ground-truth surface**. `/sprint` charge-authors **BIND
premises to the §2 table** — no charge asserts a fact about the substrate that
this table does not carry with a dated live receipt. **If `re-verify-by`
(2026-07-14) has passed, re-run §1 before authoring** — freshness receipts decay
fast (the ASR frame age oscillates on a ~sub-hour cadence; the 429 envelope is
burst-driven). **No claim here without a dated live receipt.** A green dashboard
is not a receipt; a pasted live value with its command is.

Baseline: `origin/main f713dd30` (worktree
`wt.10x-dev.substrate-attribution.20260713T212750.5b7f85`). AWS account
`696318035277`, region `us-east-1`.

> **Grade ceiling — MODERATE.** This surface is SRE-authored (same-rite as the
> attribution it records) per `self-ref-evidence-grade-rule`. The §2 rungs are
> reported at the honest rung reached (G-RUNG: never round up). A row's rung is
> the LOWEST altitude its receipt proves, not the altitude it aspires to.

---

## §1 — RE-VERIFY COMMAND BLOCK

Copy-paste. Each stanza re-measures one or more §2 rows. Run all of it, then
diff the output against §2. If any row moves, update §2 with the new value + a
fresh dated receipt and reset `re-verify-by`.

```bash
# ── ENV ────────────────────────────────────────────────────────────────────
export AWS_ACCOUNT=696318035277 AWS_REGION=us-east-1
GID=1143843662099250
WT=/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.knossos/worktrees/wt.10x-dev.substrate-attribution.20260713T212750.5b7f85
APS_WS=ws-26b271ef-afd6-4158-82cc-74dbcb273976   # AMP workspace (entity ruler)

# ── ROW: baseline HEAD ───────────────────────────────────────────────────────
git -C "$WT" rev-parse origin/main                       # expect f713dd30...

# ── ROW: C2 AL-5 alarm state (offer-frame-stale) ────────────────────────────
aws cloudwatch describe-alarms --region "$AWS_REGION" \
  --alarm-names "asana-AL5-offer-frame-stale-${GID}" \
  --query 'MetricAlarms[0].{State:StateValue,Updated:StateUpdatedTimestamp,Actions:AlarmActions}'
#   expect StateValue=OK while GID <3600s (live-emitting; INSUFFICIENT_DATA only if no recent serve;
#   ALARM if starved >3600s ×2 periods), Actions=[] (NON-PAGING)

# ── ROW: ASR offer GID frame age (serve-path event) ─────────────────────────
aws logs filter-log-events --region "$AWS_REGION" \
  --log-group-name /ecs/autom8y-asana-service \
  --filter-pattern '"'"$GID"'" "age_seconds"' \
  --start-time $(( ($(date +%s) - 1800) * 1000 )) \
  --query 'events[-5:].message'
#   read age_seconds + freshness off dataframe_cache_*_lkg_serve; expect ~3.1-3.4ks, "stale"

# ── ROW: C4 warmer DMS alarm + its EMPTY namespace ──────────────────────────
aws cloudwatch describe-alarms --region "$AWS_REGION" \
  --alarm-names "autom8-asana-cache-warmer-DMS-24h" \
  --query 'MetricAlarms[0].{State:StateValue,Enabled:ActionsEnabled,NS:Namespace,Metric:MetricName,Actions:AlarmActions}'
aws cloudwatch list-metrics --region "$AWS_REGION" \
  --namespace "Autom8y/AsanaCacheWarmer" --query 'Metrics'
#   expect alarm State=ALARM, Enabled=false; list-metrics=[] (ORPHANED — namespace empty)

# ── ROW: entity-level offer freshness metric + ALERTS (AMP ruler) ───────────
#   the SCAR-015 blind-spot ruler: entity metric reads "healthy" while the GID sits ks-stale
uvx --from awscurl awscurl --region "$AWS_REGION" --service aps \
  "https://aps-workspaces.${AWS_REGION}.amazonaws.com/workspaces/${APS_WS}/api/v1/query" \
  --data-urlencode 'query=offer:warm_complete:age_seconds'
uvx --from awscurl awscurl --region "$AWS_REGION" --service aps \
  "https://aps-workspaces.${AWS_REGION}.amazonaws.com/workspaces/${APS_WS}/api/v1/query" \
  --data-urlencode 'query=ALERTS{alertstate="firing"}'
#   expect offer:warm_complete:age_seconds ~O(1e4)s tagged "healthy"; cross-check vs the
#   ks-stale GID age from the logs stanza above => the blind spot, LIVE.

# ── ROW: 429 storm envelope (Logs Insights, 6h) ─────────────────────────────
for LG in /ecs/autom8y-asana-service /ecs/autom8y-asana-cache-warmer-bulk /ecs/autom8y-asana-cache-warmer; do
  QID=$(aws logs start-query --region "$AWS_REGION" \
    --log-group-name "$LG" \
    --start-time $(( $(date +%s) - 21600 )) --end-time $(date +%s) \
    --query-string 'filter @message like /429|rate_limit_429/ | stats count() as n by bin(6h)' \
    --query 'queryId' --output text)
  sleep 4
  echo "== $LG =="; aws logs get-query-results --region "$AWS_REGION" --query-id "$QID" --query 'results'
done
#   G-DENOM: /ecs/autom8y-asana-service folds EBI-driven calls into the same line as warm
#   calls — this axis CANNOT separate them. See §2 note + @throughlines:index:denominator-integrity.

# ── ROW: open PRs (insights-lane coordination surface) ──────────────────────
env -u GITHUB_TOKEN gh pr list --state open --limit 50

# ── ROW: TF codification of AL-5 (validate — does NOT apply) ─────────────────
( cd "$WT/terraform/services/asana" && terraform validate )   # expect: Success
grep -nE 'asana-AL5-offer-frame-(age|stale)|OfferFrameAgeSeconds|AsanaSubstrateFreshness' \
  "$WT/terraform/services/asana/observability_alarms.tf"
```

---

## §2 — MEASURED GROUND-TRUTH TABLE

Columns: **Fact** | **Live value (2026-07-13)** | **Receipt / source** | **Rung**
(see §3 ladder). Every platform-behavior row carries a receipt per
`@structural-verification-receipt`; live-telemetry rows carry the command +
observed value; code rows carry `{path}:{line}`. Rungs are honest-floor
(G-RUNG).

| # | Fact | Live value (2026-07-13) | Receipt / source | Rung |
|---|------|-------------------------|------------------|------|
| 1 | **origin/main HEAD** | `f713dd30` (#232 nsr band render). Insights-lane session ACTIVE (landed #228–#232 on 07-13). This is a **coordinate, non-ruling #2** — do not re-open its lane; bind to it. | `git -C {wt} rev-parse origin/main` → `f713dd30f6702dde33db63a2c98d89d8037a0020` (bash-probe, this dispatch) | measured |
| 2 | **ASR offer frame age** (GID 1143843662099250) | age = **3278s @20:04Z**, `freshness="stale"`; **oscillating 3.1–3.4ks** (partial self-heal — **NOT cured**: hierarchy-warm still 429-failing gaps → `gaps_warmed:0`). Serve-path event = `dataframe_cache_*_lkg_serve`. | Logs Insights `/ecs/autom8y-asana-service` (age_seconds + freshness fields). Serve-path event confirmed in code: `src/autom8_asana/cache/integration/dataframe_cache.py:767-776` (`dataframe_cache_{tier}_lkg_serve`, emits `age_seconds`, `freshness:"stale"`). | **attributed, NOT cured** |
| 3 | **Entity-metric blind spot (SCAR-015)** | `offer:warm_complete:age_seconds ≈ 11,336s` tagged **"healthy"** while the SAME GID sat **74–87ks stale** the same day. The entity aggregate does NOT see the per-GID frame age. | AMP ruler query (workspace `ws-26b271ef-afd6-4158-82cc-74dbcb273976`); cross-referenced against per-GID log age (row 2). TF comment records the same class: `terraform/services/asana/observability_alarms.tf:265` ("healthy … while the ASR project frame 1143843662099250 sat …"). | **LIVE-proven blind spot** |
| 4 | **429 storm envelope (6h)** | log-lines: `service=79,881` / `warmer-bulk=25,669` / `warmer=3,095`. Service→Asana calls `17,449/1h` (~19% avg of the 1500/60s budget). **BURST-driven**, not steady saturation. Onset **07-08/09**; **07-10 EBI-flip onset FALSIFIED**. | Logs Insights per-log-group count (see §1 429 stanza). **G-DENOM**: the `/ecs/autom8y-asana-service` line **folds EBI-driven calls into the same count as warm calls** — this axis cannot separate them (see §2 note). | **attributed (discharged)** |
| 5 | **Token architecture** | **Single bot PAT** `ASANA_PAT` serves ALL S2S callers. **Per-client AIMD only**; **cross-consumer arbitration ABSENT**. Code-default rate = **1500 req / 60s** (Asana's limit; no env override set). | `src/autom8_asana/auth/bot_pat.py:57-75` ("single credential that autom8_asana uses to call the Asana API on behalf of all S2S callers"). AIMD: `src/autom8_asana/client.py:158-163` (`_shared_rate_limiter = TokenBucketRateLimiter`, per ADR-0062) + `src/autom8_asana/config.py:392-413` (AIMD floor/decrease/start-window). Rate default: `config.py:322-326` ("Default: 1500 requests per 60 seconds (Asana's limit)"). | code @ f713dd30 |
| 6 | **Felt-line = NO** (internal-only) | insights render reads **external** `autom8_data` via `AUTOM8Y_DATA_URL`; the starved LKG path reads **only** cache `/query`. The two are **disjoint** — a stale ASR frame does NOT starve the insights render. Operator plane is **deploy-INERT**. | Insights→external: `src/autom8_asana/automation/workflows/insights/workflow.py:783-790` (`_data_client.get_operator_insights_batch_with_meta_async`) → `src/autom8_asana/clients/data/_endpoints/operator.py:432`. `AUTOM8Y_DATA_URL` canonical Tier-3 env: `src/autom8_asana/settings.py:35,661`. Starved LKG path: `dataframe_cache.py:767-776` (/query serve only). | **internal-only (NOT Pillar-9)** |
| 7 | **C2 AL-5 detection** | metric filter `asana-AL5-offer-frame-age-1143843662099250` → `Autom8y/AsanaSubstrateFreshness / OfferFrameAgeSeconds{project_gid}`. Alarm `asana-AL5-offer-frame-stale-1143843662099250` (**Max > 3600 / 2×300s**, actions **[] NON-PAGING**, **LIVE-EMITTING** — first real serve datapoint 3,277.9s @20:02Z → `OK`; full filter→metric→alarm pipeline proven on prod traffic). **Teeth proven**: RED 7200s → ALARM @19:45Z; GREEN 300s → OK @19:48Z; real-log backtest breach 07-11→07-13. **TF-codified** (`terraform validate` PASS). | `describe-alarms --alarm-names asana-AL5-offer-frame-stale-1143843662099250`. TF: `observability_alarms.tf:335` (metric filter `asana-AL5-offer-frame-age-${each.key}`), `:321` (namespace `Autom8y/AsanaSubstrateFreshness`), `:340` (`OfferFrameAgeSeconds`), `:353,356` (alarm), `:302` (GID default `["1143843662099250"]`). CI apply **wedged** (validate passes; apply not run). | **detecting-via-canary + teeth-proven + TF-merged-pending; NOT protecting-prod** |
| 8 | **C4 warmer DMS alarm** | `autom8-asana-cache-warmer-DMS-24h` = **ALARM**, `ActionsEnabled:false` since **2026-06-04**. Watches `LastSuccessTimestamp` in namespace `Autom8y/AsanaCacheWarmer` — which is **EMPTY** (`list-metrics=[]`) → **ORPHANED**. Actions wired to **paging** SNS `autom8y-platform-alerts`. | `describe-alarms --alarm-names autom8-asana-cache-warmer-DMS-24h` (State=ALARM, Enabled=false) + `list-metrics --namespace Autom8y/AsanaCacheWarmer` → `[]`. | **diagnosed-orphaned → disposition = retire-and-supersede (USER lever)** |
| 9 | **Freshness semantics** | code-FRESH ≤ TTL (offer **180s** / default 300s); STALE beyond the SWR grace window (**grace = TTL × 3.0**; so default STALE > 900s, **offer STALE > 540s**); LKG serve ceiling for offer = the **freshness contract 16,200s** (`FRESHNESS_CONTRACT_MAX_AGE_SECONDS["offer"]`), applied at `dataframe_cache.py:684-686` (`ceiling_source="freshness_contract"`), OVERRIDING the 1,800s multiplier fallback (`10.0 × 180`, reached only when NO contract). The `config.py:299-303` "GATED on OQ-2" wording is a process-ratification note, NOT a runtime gate — the `:304` entry is live and applied. **The <3600s cure bar is LOOSER than code-fresh.** | `dataframe_cache.py:1248-1258` (FRESH ≤ entity_ttl; APPROACHING_STALE ≤ grace_ttl = entity_ttl × SWR_GRACE_MULTIPLIER; else STALE). `config.py:137` (`SWR_GRACE_MULTIPLIER = 3.0`), `:156` (`LKG_MAX_STALENESS_MULTIPLIER = 10.0`), `:294-305` (`"offer": 16200.0` — comment: "GATED on operator land-gate / OQ-2 … NOT load-bearing"). Offer ttl 180s: `config.py:259-262` (comment: multiplier ceiling = 10.0 × 180 = 1800s). | code @ f713dd30 |
| 10 | **DEFER-watch** (out of scope, registered) | Not measured this pass; carried so charges do NOT accidentally scope them in: `sms EcsServiceDenominatorAbsent` page-severity **FIRING** (out-of-lane → surface to operator); AMP `slo_offer_freshness` re-arm (ASR arc — needs (a)/(b)/(c) + soak); node-4 read-schedule (operator); `get_insight-503` (data rite); AL-6 warm-liveness candidate; EBI per-route attribution; AL-5 threshold tightening **post-cure**; per-GID pattern **satellite-promotion candidate**. | Registered here as scope-fence, per `@telos-integrity-ref` DEFER discipline; each item owned by the noted rite/lever, not this surface. | registered-DEFER (unmeasured) |

### G-DENOM note (row 4) — the log-group axis limit

`@throughlines:index:denominator-integrity`. The `/ecs/autom8y-asana-service`
log group carries **both** EBI-driven (event-based-ingestion) Asana calls **and**
warm-path calls under the same emitter. A `filter … like /429/ | stats count()`
over that group therefore **cannot separate** EBI-driven service calls from
warm calls — EBI-driven calls are **folded into the service line** (row 4's
`79,881`). Any charge that needs per-route (EBI vs warm) 429 attribution **must
add a route dimension at emission time** (registered as DEFER-watch "EBI
per-route attribution", row 10) — it cannot be recovered from this axis
post-hoc. Stating a per-route 429 split off row 4 would be a denominator error.

---

## §3 — RUNG LADDER (reference)

Read left→right; each rung strictly dominates the one before. A row's rung is
the **rightmost** rung its receipt actually proves (G-RUNG: never round up).

```
authored  <  emitting  <  detecting-via-canary  <  teeth-proven  <  merged  <  imported/applied  <  protecting-prod
```

| Rung | Meaning | This surface's exemplar |
|------|---------|--------------------------|
| **authored** | Artifact/alarm exists in a file; no runtime yet. | — |
| **emitting** | The metric/event is being emitted to a live sink. | — |
| **detecting-via-canary** | A canary has driven the detector and it responded. | AL-5 (row 7) |
| **teeth-proven** | Two-sided: fires on the defect, passes on the no-defect variant. | AL-5 RED 7200s→ALARM / GREEN 300s→OK (row 7) |
| **merged** | Codified in TF/code and merged (validate passes). | AL-5 TF (row 7 — CI apply wedged, so stops here) |
| **imported/applied** | Applied to the live account (`terraform apply` ran). | — (AL-5 blocked at merged; apply pending) |
| **protecting-prod** | Live, paging, gating real serve traffic. | **NONE** — AL-5 is live-emitting but NON-PAGING (actions `[]`); DMS (row 8) is orphaned/disabled. |

**Standing truth for the next charge-author**: nothing in this substrate is at
`protecting-prod`. The freshness storm stands **attributed** (rows 2, 4, 5); the
per-GID detector stands **teeth-proven + merged-pending** (row 7); the legacy
DMS alarm stands **orphaned** (row 8). Bind premises to the rung shown, not to
the aspiration.

---

## Receipt-grammar & scope notes

- **Skills bound as named pointers** (frontmatter): `@structural-verification-receipt`
  (every platform-behavior row carries a `{path}:{line}` or command receipt, or is
  labelled a registered DEFER), `@telos-integrity-ref` (per-item file:line
  receipt-grammar — no wave-level "CLOSED/verified" tokens appear in §2),
  `@throughlines:index:denominator-integrity` (G-DENOM, row 4 note).
- **G-RUNG** honored: rows 2 and 7 are the two most-likely-to-be-rounded-up; both
  are pinned at their honest floor (`attributed, NOT cured`; `teeth-proven +
  merged-pending, NOT protecting-prod`).
- **Grounding corrections** (do not re-propagate the pre-correction figures): (i)
  STALE is **grace-window relative** (`TTL × 3.0`), so the "> 900s" figure is
  default-TTL-specific and the **offer STALE boundary is 540s** (row 9); (ii) the
  operative offer LKG serve ceiling is the **16,200s freshness contract**, applied at
  `dataframe_cache.py:684-686` (`contract_max_age is not None` → `max_age = 16200`,
  `ceiling_source="freshness_contract"`), which OVERRIDES the 1,800s multiplier
  fallback. The `config.py:299-303` "GATED on OQ-2" wording is a process-ratification
  note, NOT a runtime gate — the `:304` dict entry is live and the code reads it. An
  earlier same-rite draft had this inverted; corrected here against the ground-truth
  code path (row 9).
- **Self-assessment ceiling: MODERATE** (`self-ref-evidence-grade-rule`) — this is
  an SRE-authored, same-rite measured surface; a rite-disjoint attester (eunomia)
  is required to lift any row above MODERATE self-grade.
- **Decay**: `re-verify-by 2026-07-14`. The telemetry rows (2, 3, 4) decay within
  hours; the code rows (5, 6, 9) decay only on a new merge to `origin/main`; the
  alarm-topology rows (7, 8) decay on the next `terraform apply` or alarm edit.
