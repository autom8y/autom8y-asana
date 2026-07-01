---
type: handoff
handoff_type: implementation
status: accepted
from: 10x-dev (W-AUTH-2 procession)
to: auth (auth-side session / platform-team)
created: 2026-06-24
initiative: asana-cutover-readiness
session: session-20260624-122743-279749db
---

# Cross-Rite HANDOFF — 10x-dev W-AUTH-2 → auth-side session

> **Grandeur anchor:** Close the live BI insights-export outage at its SECOND layer. #151 deployed-live and its auth-provider WIRING is proven (error advanced `AUTH-TEB-001` → `TokenAcquisitionError 400`), but the S2S token MINT still fails → every table `succeeded:0`. Root cause is now PINNED and it is AUTH-DOMAIN governance, not asana code — the operator's auth-side-session hypothesis was substantially right. Proven-closed ONLY by a live `succeeded>0` `insights_export_completed` run after the governance change, NEVER by a merge or a green plan.

## ROOT CAUSE (corroborated — evidence-graded STRONG via independent verification)

The insights-export Lambda authenticates with `SERVICE_CLIENT_ID = sa_2018…` — an **`sa_*` ServiceAccount** (VERIFIED live; len 35). autom8y-core **4.6.0** `TokenManager` routes by client-id prefix (`token_manager.py:481-484`):
- `client_*` → `POST /oauth/token` (RFC 6749, service-level / tenant-unbound)
- `sa_*` → `POST /tokens/exchange-business` (legacy **TEB**, business-scoped)

`_build_teb_kwargs` (`token_manager.py:526-549`) sends an **empty body** unless `config.business_id` is set **or the SA is provisioned `bypass_scope_enforcement` (`business_scoped:false`)**. `auth/service_token.py` (asana, origin/main) builds `Config(client_id=sa_*, client_secret=<scalar len 48, resolves FINE>, auth_url, service_name)` with no `business_id`. The insights SA is **not enrolled as an exempt `business_scoped:false` SA**, so it has no bypass tuple → empty TEB body → **`AUTH-TEB-002` → 400** on every table.

**REFUTED (do not re-chase):** secret value/resolution (scalar, resolves correctly), IAM `GetSecretValue` (role allowed on the exact ARN), R4 `PutMetricData` (allowed), the cache-warmer "control" (invalid — cache-warmer mints no S2S).

### Live receipts
- Incident OPEN on live image `:e0b5360` (= #152, warmer-telemetry-deps; insights mint code unchanged from #151/a30d55a): `insights_export_completed` traces `94b6cf6e…` / `d77a7e6d…`, 2026-06-24 19:29-19:39Z — every table `TokenAcquisitionError "Token exchange failed with status 400"`, `succeeded:0`.
- SDK routing: `autom8y_core/token_manager.py:481-484` (prefix route), `:517-549` (`_build_teb_kwargs` empty-body → AUTH-TEB-002 docstring).
- asana call-site: `src/autom8_asana/auth/service_token.py` `Config(...)` (origin/main) — no `business_id`, `sa_*` client_id.

## WHY THE CONVENTION SAYS `sa_*` + `business_scoped:false` (NOT `client_*`)

`services/auth/service-accounts.yaml` is the governance source-of-truth (→ OpenFGA `can_issue_service_token` / `bypass_scope_enforcement` via `modules/service-accounts/`). **All 14 cross-tenant services are `sa_*` + `business_scoped:false` + an `exemption` block; none use `client_*`.** Smoking gun — `data-canary-monitor` (`service-accounts.yaml:442-469`): *"mints a fleet-read token (`bypass_scope_enforcement=True`, no business_id) … via the exempt `/tokens/exchange-business` leg (bypass=True, no business_id)."* That is exactly insights-export's need. Peers: `reconcile-ads`, `reconcile-spend`, `sms-reminder-lambda`, `account-status-recon`, `meta-lead-service`, `email-booking-intake-service`.

**The gap:** asana has `asana-dataframe-resolver` registered (the `/v1/query` consumer, `query:read`) — but the **insights-export SA (`sa_2018…` / secret `autom8y/auth/service-api-keys/asana-service`) is NOT enrolled.** It was simply never added to the exempt registry alongside its cross-tenant peers.

## PROPOSED FIX (auth-side; asana needs NO code change)

Enroll the insights-export SA in `service-accounts.yaml` as a `business_scoped:false` exemption. Draft entry (auth-domain to verify scopes + the `id`↔`sa_2018…`↔secret mapping + the migration round-trip):

```yaml
  - id: asana-insights-export
    name: asana-insights-export-service
    business_scoped: false
    authorized_organizations: []
    secret_path: autom8y/auth/service-api-keys/asana-service   # VERIFY: shared with ECS asana — may need its own SA/secret
    scopes:
      - data:write     # exports BI insight tables to autom8y-data
      - data:read      # VERIFY: if it reads reconciliation inputs first
    description: >-
      Asana insights-export Lambda — nightly fleet-wide BI export of
      per-offer insight tables (reconciliations, leads, appointments, …)
      to autom8y-data across all business tenants.
    exemption:
      reason: >-
        Fleet-wide nightly BI export — writes insight tables for every
        tenant; tenant is the iteration unit, so per-business token
        issuance would require N exchanges per run with no observable win.
      approved_by: <OPERATOR>            # user-sovereign approval
      approved_date: "2026-06-24"
      tension_inherited: "TENSION-005"
      category: cross_tenant_rollup       # peer-consistent w/ sms-performance-report
      owner: platform-team
      justification: |
        insights-export iterates all offers across all businesses and
        writes their BI tables to autom8y-data as its core function.
        Shape-identical to reconcile-* / account-status-recon (single
        Lambda, single cron, fleet-wide). Per-business scoping breaks the
        export. Currently UN-enrolled → empty-body TEB → AUTH-TEB-002 400.
```

Then: migration (021-style — **the `id` MUST match the migration BUCKET dict or AUTH-TEB-002 fires at startup**, per `service-accounts.yaml:18-23`) + `terraform/services/auth` apply emits the bypass tuple. No asana code/IaC change; the `sa_*`+empty-body path becomes valid once the SA is exempt.

## OPEN QUESTIONS (auth-domain — I could not resolve these; AWS creds expired mid-session)
1. Does `sa_2018…` map to an existing (non-exempt) auth-DB SA under the `asana-service` secret, or does insights need its OWN SA/secret distinct from the ECS asana identity? (The secret is shared with ECS today.)
2. Exact `scopes` for the export (data:write vs data:read+write vs an analytics:* scope).
3. **ECS asana is likely ALSO broken, differently:** manifest `SERVICE_CLIENT_ID="asana"` is UN-prefixed → SDK 4.6.0 `_resolve_token_endpoint` raises `ValueError`→500. UNVERIFIED against the live ECS task-def env (AWS expired before I could read `autom8y-asana-service:550`). Reconcile both asana identities (Lambda `sa_2018…` + ECS `asana`) against the prefix contract.
4. The exact 400 sub-reason (AUTH-TEB-002 "business_id required" vs allow_multi_tenant-reject) is un-fired — would need a credentialed probe to `/tokens/exchange-business` (body `{}` vs `{business_id}`); both collapse to this fix.

## Realization rungs (honest; never round up)
- #151 (layer 1, auth-provider wiring): **live** (image deployed, wiring proven) — necessary-but-not-sufficient.
- W-AUTH-2 root cause: **proven** (corroborated, STRONG).
- W-AUTH-2 fix: **authored-as-recommendation** only (draft entry) — the governance change is auth-side, UNSTARTED.
- BI incident: **STILL OPEN** — `succeeded:0` live (19:39Z). NOT `protecting-prod`. Closes only on a live `succeeded>0` run after the governance change + a token refresh/redeploy.

## Blocked legs
- **AWS creds expired** (`ExpiredTokenException`) — all live verification / re-invoke / deploy blocked until operator re-auth (`aws sso login` or equivalent).
- Live verify-close: a schedule-faithful async invoke → `succeeded>0` + a live `Autom8y/AsanaInsights` `PutMetricData` datapoint (IAM already allows it).

## Watch-registered DEFER (not scope-crept)
- ECS `SERVICE_CLIENT_ID` prefix reconciliation (folds into the SA-identity work above).
- `api/routes/workflows.py:361` bare-`DataServiceClient` sibling — SEPARATE static-key path (`AUTOM8Y_DATA_API_KEY`), NOT closed by this fix; 10x-dev follow-up.
- Stale `tests/unit/api/test_fleet_query_adapter.py:370`; D-2 coverage.
- FORK-2 interop substrate (2026-09-29); H-4 cache_warmer decomposition; W-REG/SCAR-REG-001 dual-anchor (until W-IRIS).

## Production-mutating levers — UNTOUCHED, user-sovereign
The `service-accounts.yaml` change + migration + `terraform/services/auth` apply + any token/secret rotation are **auth-side and user-sovereign** — no agent executed them. The `approved_by` in the exemption block is the operator's to set.

## Inherited receipts / context
`@.ledge/reviews/handoffs/cross-rite-handoff-releaser-land151-to-operator-2026-06-24.md`; operator auto-memory `autom8y-asana-scar-tissue.md` (full corroborated diagnosis + receipts). Diagnostic agent (resumable): architect `aa4060560fe5c6b20`.
