---
type: spec
status: draft
---

# TDD — GAP-1: asana insights-export operator-plane consumer rewire

> **Status:** DRAFT — design-only, NO code mutation. Rung ceiling = merged + deployed-INERT.
> **Author:** architect (10x-dev rite) · **Date:** 2026-06-28
> **Pinned trees (all reads via `git show origin/main:<path>`):**
> - autom8y-asana origin/main `e7d71fa8`
> - autom8y-data origin/main `3169fa96`
> - autom8y (auth lives at `services/auth/`) origin/main `3df3298a`
> **Cross-refs:** `autom8y-data/.ledge/specs/TDD-machine-operator-mint-capability-2026-06-28.md` (the auth+data BUILD this consumes), `autom8y-data/.ledge/specs/TDD-gap1-gap2-lean-realization-2026-06-27.md` (GAP-2 route design), `services/auth/.ledge/decisions/ADR-AUTH-MULTI-TARGET-OPERATOR-PLANE-004.md`, ADR-0040 (security gate).

---

## Grandeur Anchor

> "We are 10x-dev, building GAP-1 — the asana insights-export consumer rewire — to mint an OperatorClaims token via the deployed C-6 sts:GetCallerIdentity endpoint and consume the deployed operator-plane route (analytics:aggregate), retiring the OLD fleet-read SA path — toward merged + deployed-INERT, NO FURTHER. Proven ONLY by a REAL round-trip + import-cleanliness under the deployed-image condition. NEVER weaken DATA-VAL-003 / c1b / REC-3. The counter moves only at the operator FLIP."

---

## 0. Executive verdict (read this first)

The PRIORITY FORK resolves **NOT 1:1**, and not even partially. **The intersection of {what the operator route serves} and {what the export consumes} is EMPTY (∅).** GAP-1, framed as a *pure asana consumer rewire that retires the OLD fleet-read SA path*, is **INFEASIBLE at origin/main** — there is nothing to rewire, because no export table is served by the operator route's allowlist, and the export's PII tables are structurally **inadmissible** to the de-identified-aggregate operator plane by design (C-1 default-deny).

GAP-1 therefore **splits**:

- **GAP-1a — BUILDABLE INERT NOW (keystone-free, this TDD's primary deliverable):** the asana-side **operator-mint client** (SigV4 → `/operator/token`) + a NEW operator-batch **data-client method** that consumes `POST /api/v1/insights/operator/execute-batch`. Mergeable INERT (empty allowlist 403s the mint; no production call-site consumes it). Round-trip-provable against an off-prod synthetic-ARN-allowlisted auth + the REAL operator route. **Does NOT retire the SA path** — it is the reusable substrate the eventual cutover needs.
- **GAP-1b — BLOCKED / ESCALATED (scope expansion, NOT a pure asana rewire):** the actual call-site rewire of the 12 export tables. Requires (i) data-plane EXTENSION (new registered de-identified aggregate insights + C-1 allowlist additions, each under ADR-0040 security review) for the aggregate-eligible subset, AND (ii) a **product-scope decision** (requirements-analyst / operator domain) for the per-patient (APPOINTMENTS, LEADS) and financial (RECONCILIATION) tables, which the operator plane refuses by construction. **This is escalated to Potnia — it is not the architect's call to silently drop or down-scope client data.**

The rest of this document rules the fork in full, specifies GAP-1a's design (mint client, deploy-INERT, round-trip harness, deployed-image discipline) to a buildable bar, and enumerates the GAP-1b options for the escalation.

---

## 1. ★ The mapping verdict — THE load-bearing ruling

### 1.1 What the OLD export actually fetches (origin/main, asana `e7d71fa8`)

The export is `InsightsExportWorkflow` (`src/autom8_asana/automation/workflows/insights/workflow.py`). It fetches **12 tables** declared in `TABLE_SPECS` (`src/autom8_asana/automation/workflows/insights/tables.py`), dispatched in `_fetch_table` via a `match` on `spec.dispatch_type` across **four** `DispatchType` values (workflow.py:619/625/632/660):

| # | Table | DispatchType | Client method | Data-plane route hit | Param |
|---|-------|--------------|---------------|----------------------|-------|
| 1 | SUMMARY | INSIGHTS | `get_insights_async` | `POST /api/v1/data-service/insights` (`_endpoints/insights.py:182`) | factory=`base`, period=lifetime |
| 6 | BY QUARTER | INSIGHTS | `get_insights_async` | same | factory=`base`, period=quarter |
| 7 | BY MONTH | INSIGHTS | `get_insights_async` | same | factory=`base`, period=month |
| 8 | BY WEEK | INSIGHTS | `get_insights_async` | same | factory=`base`, period=week |
| 9 | AD QUESTIONS | INSIGHTS | `get_insights_async` | same | factory=`ad_questions` |
| 10 | ASSET TABLE | INSIGHTS | `get_insights_async` | same | factory=`assets`, period=t30 |
| 11 | OFFER TABLE | INSIGHTS | `get_insights_async` | same | factory=`business_offers`, period=t30 |
| 12 | UNUSED ASSETS | INSIGHTS | `get_insights_async` | same | factory=`assets`, include_unused |
| 2 | APPOINTMENTS | APPOINTMENTS | `get_appointments_async` | `GET /api/v1/appointments` (`_endpoints/simple.py:143`) | days=90, limit |
| 3 | LEADS | LEADS | `get_leads_async` | `GET /api/v1/leads` (`_endpoints/simple.py:248`) | days=30, exclude_appointments |
| 4 | LIFETIME RECONCILIATIONS | RECONCILIATION | `get_reconciliation_async` | `POST /api/v1/insights/reconciliation/execute` (`_endpoints/reconciliation.py:156`) | period |
| 5 | T14 RECONCILIATIONS | RECONCILIATION | `get_reconciliation_async` | same | window_days=14 |

So the export consumes **four distinct data-plane surfaces**: the **factory/frame** insights subsystem (`/data-service/insights`, 8 tables, factory ∈ {`base`, `ad_questions`, `assets`, `business_offers`}), `GET /appointments`, `GET /leads`, and the **registered-insight** `reconciliation` execute path.

> SVR — claim: *the export dispatches on 4 DispatchType values and 8 of 12 tables use the factory-frame `/data-service/insights` route, not a registered-insight-by-name route.*
> verification_method: file-read · source: `git show e7d71fa8:src/autom8_asana/automation/workflows/insights/tables.py` · marker_token: `dispatch_type=DispatchType.INSIGHTS,\n        factory="base",` · line_range: TABLE_SPECS SUMMARY entry · claim attested: the INSIGHTS dispatch is parameterized by `factory`, and `_endpoints/insights.py:182` sets `path = "/api/v1/data-service/insights"`.

### 1.2 What the operator route serves (data `3169fa96`)

The **only** operator route on the data plane is `execute_operator_batch` → `POST /api/v1/insights/operator/execute-batch` (`src/autom8_data/analytics/routes/operator_insights.py`). It serves a **single registered `insight_name`** across a batch of offices, gated by a **default-deny C-1 allowlist**:

```
_OPERATOR_INSIGHT_ALLOWLIST = frozenset({"business_summary", "account_level_stats", "asset_level_stats"})
```
(`operator_insights.py`, the `_OPERATOR_INSIGHT_ALLOWLIST` definition). Any `insight_name` not in this set is refused with the bare 404-as-oracle **before any DB resolution**.

Grep of the data plane confirms **no operator variant exists for appointments, leads, or `/data-service/insights`** — `operator_insights.py` is the sole operator route (the only `routes/*` module gated by `MultiTargetOperatorDep`; `comparison.py` is the human-operator *compare* route, a different shape).

> SVR — claim: *the operator allowlist is exactly {business_summary, account_level_stats, asset_level_stats} and reconciliation is deliberately excluded.*
> verification_method: file-read · source: `git show 3169fa96:src/autom8_data/analytics/routes/operator_insights.py` · marker_token: `# C-1 EXCLUSION — \`reconciliation\` is DELIBERATELY NOT seeded.` · claim attested: financial-PII `reconciliation` is excluded pending OD-5; the seed family is the three de-identified aggregates.

### 1.3 The intersection

| Operator allowlist (served) | In the export's call set? |
|---|---|
| `business_summary` | **NO** — export uses factory=`base` via `/data-service/insights`, a different subsystem/route/shape. |
| `account_level_stats` | **NO** — not requested anywhere by the export. |
| `asset_level_stats` | **NO** — export uses factory=`assets` via `/data-service/insights`, not the `asset_level_stats` registered insight. |

**Intersection = ∅.** The operator route covers **zero** of the 12 export tables today.

### 1.4 Why this is structural, not a build oversight

The data-plane operator route docstring asserts business_summary is "the per-office aggregate the asana export consumes / the route's documented example." **This premise is FALSIFIED by the export source:** the export consumes the *factory/frame* subsystem (factory=`base`/`assets`/…), not the *registered-insight-by-name* subsystem. The operator route was built against an **imagined** consumer, not the real one. Two distinct insight subsystems exist on the data plane:

1. **factory/frame** (`POST /data-service/insights`, request carries `factory`→`frame_type`, returns `InsightsResponse`) — what the export uses for 8 tables.
2. **registered-insight-by-name** (`/insights/{name}/execute[/batch]` + the operator variant, returns `BatchInsightResponse`) — where the allowlisted names live.

These are different routes, different response shapes (`InsightsResponse.data` vs `BatchInsightResponse.data`, models.py:384), and different computations. Even the *semantically adjacent* candidates (SUMMARY↔business_summary, ASSET TABLE↔asset_level_stats) are **NOT transparent rewires** — they are data-source migrations that change report content and require product sign-off that the registered-insight output is an acceptable substitute. That is a requirements decision, not an architecture decision.

### 1.5 The PII wall (why the gap can never be fully closed on the operator plane)

The operator plane is **de-identified-aggregate-only by design** (C-1 default-deny is the load-bearing non-PHI control: `operator_insights.py` Step 2a-bis). Three of the export's tables are **structurally inadmissible**:

- **APPOINTMENTS, LEADS** — per-patient / per-lead grain (PII). The operator plane refuses any non-allowlisted, non-de-identified operand on purpose; `lead_phone` is specifically why C-1 is an allowlist and not the `_pii_dimension_names` dim-gate.
- **RECONCILIATION** — financial PII (customer_id + bearer-accessible hosted_invoice_url + invoice_number). **Explicitly C-1 EXCLUDED pending OD-5** ratification + data-owner sign-off.

Retiring the SA fleet-read for these three tables therefore cannot mean "move them to the operator plane." It can only mean **(a)** keep a fleet-read path for them (defeats the GAP-1 telos and re-asserts the DATA-VAL-003 problem), or **(b)** a product decision to **drop them from the cross-tenant export**. Either is a scope/product call.

### 1.6 The fork ruling (explicit, per option-enumeration discipline)

**Question posed by the fork:** does GAP-1 rewire ONLY the covered shapes (and what of the uncovered ones — stay on old SA path [DATA-VAL-003 conflict] or out-of-scope?), OR does the data plane need extension (scope expansion beyond a pure asana rewire)?

**Options for resolving the scope gap:**

- **Option M1 — "rewire only the covered shapes."** Covered set = ∅ → rewires nothing → SA path stays for all 12 tables → **no retirement, telos not advanced, DATA-VAL-003 unresolved.** *Vacuous.* **REJECTED** (delivers no value; the SA path survives in full).
- **Option M2 — full data-plane extension to reproduce all 12 tables on the operator plane.** Requires: new registered de-identified aggregate insights reproducing the 8 factory tables; NEW operator routes for appointments/leads (no registered-insight or aggregate shape exists); C-1 allowlist additions per insight under ADR-0040 review. The appointments/leads/reconciliation members are **PII-inadmissible** → cannot be satisfied without violating the operator plane's non-PHI invariant. **REJECTED as stated** (asks the operator plane to do the thing it exists to forbid).
- **Option M3 — split: build GAP-1a INERT now; escalate GAP-1b scope decision.** Build the reusable mint+consume substrate (keystone-free, mergeable INERT, round-trip-provable). Escalate the GAP-1b product-scope decision to Potnia/requirements: for the aggregate-eligible subset, data-plane extension under security review; for the PII tables, an explicit accept/drop/keep-SA ruling by the operator. **RECOMMENDED.** It advances the buildable substrate to its honest rung without silently dropping data or pretending the SA path is retired.
- **Option M4 — abandon GAP-1, leave the export on the SA path.** Honest if the operator plane is judged the wrong tool for this export. But it forfeits the substrate that the eventual cutover will need anyway, and leaves DATA-VAL-003 unaddressed. **REJECTED** (M3 dominates — it builds the substrate INERT at near-zero risk and surfaces the real decision).

**RULING: Option M3.** GAP-1 ≠ a pure asana rewire. The architect builds GAP-1a (this TDD §2–§6) and **escalates GAP-1b** (the 12-table scope decision + data-plane extension) to Potnia (§7). The counter stays RED; that is correct — GAP-1a does not move it, and GAP-1b is gated on the escalation.

---

## 2. The SigV4 mint-client design (GAP-1a, asana-side)

### 2.1 The mint contract (verified, auth `3df3298a`)

`POST /operator/token` (mounted at `app/main.py:296` `prefix="/operator"` + `routers/operator.py` `@router.post("/token")`). Request body `OperatorTokenRequest`:

```
iam_request_method:  str  = "POST"
iam_request_body:    str  # MUST be exactly "Action=GetCallerIdentity&Version=2011-06-15"
iam_request_headers: dict[str,str]  # SigV4-signed: Authorization + X-Amz-Date (+ Host)
nonce:               str | None     # optional single-use replay nonce
```
Response: `SuccessResponse[TokenResponse]` → `data.access_token` (the Bearer string), `data.token_type="bearer"`, `data.expires_in` (≈300).

Auth-side enforcement the client must satisfy (`services/operator_identity.py`):
- body **must equal** `Action=GetCallerIdentity&Version=2011-06-15` (`_GET_CALLER_IDENTITY_BODY`; any other action → 403).
- `X-Amz-Date` freshness within `OPERATOR_STS_MAX_SKEW_SECONDS=60` (`app/config.py:113`) → **sign immediately before POST**, do not cache the signed request.
- signed `Host` (if present) must equal the pinned STS host. Auth pins `OPERATOR_STS_ENDPOINT="https://sts.amazonaws.com"` (`app/config.py:106`) → **the asana signer must sign for host `sts.amazonaws.com`** (the global endpoint, not a regional `sts.us-east-1.amazonaws.com`).
- empty `OPERATOR_ARN_ALLOWLIST` (`app/config.py:110`, default `[]`) → every mint 403s (the INERT gate). Multi-agency allowlist → fail-closed tripwire 403.

> SVR — claim: *auth pins the STS host to the global `https://sts.amazonaws.com` and enforces a 60s X-Amz-Date skew window.*
> verification_method: file-read · source: `git show 3df3298a:services/auth/autom8y_auth_server/app/config.py` · marker_token: `OPERATOR_STS_ENDPOINT: str = "https://sts.amazonaws.com"` · line_range: L106 · claim attested: the asana signer must produce a SigV4 signature whose credential scope/Host targets `sts.amazonaws.com`, signed within 60s of the POST.

### 2.2 Does asana need the autom8y-auth SDK floor? — NO

The asana side **mints + sends a token STRING** (Bearer). It does **NOT** deserialize `OperatorClaims` — the data plane does that (REC-3 recognizer, `operator_plane.extract_operator_plane_claim`). Therefore asana needs **no `autom8y-auth` SDK floor bump**. It needs only:
- **boto3/botocore** for ambient credentials + SigV4 signing — **already a runtime dependency** (`pyproject.toml:41` `boto3>=1.42.19` in `[project.dependencies]`, not a dev extra; botocore ships with boto3).
- an HTTP client to POST the signed components — already present (the data client uses `autom8y_http`; `httpx` is available).

> SVR — claim: *boto3 (hence botocore/SigV4Auth) is in the asana DEPLOYED runtime image, not a dev-only dep.*
> verification_method: file-read · source: `git show e7d71fa8:pyproject.toml` · marker_token: `boto3>=1.42.19", # S3 for progressive cache warming` · line_range: L41 (`[project.dependencies]`) · claim attested: SigV4 signing is available at runtime without a new dependency; `[dependency-groups]/dev` is not involved.

### 2.3 Mint-client mechanics

New module `src/autom8_asana/clients/data/_operator_mint.py` (private, sibling of the other `_endpoints`/`_*` helpers):

1. `creds = boto3.Session().get_credentials().get_frozen_credentials()` (ambient execution-role creds — the `autom8-asana-insights-export-lambda-role`; AWS-managed, rotated by AWS; no secret at rest, satisfies CG-6).
2. Build `botocore.awsrequest.AWSRequest(method="POST", url="https://sts.amazonaws.com/", data="Action=GetCallerIdentity&Version=2011-06-15", headers={"Content-Type":"application/x-www-form-urlencoded"})`.
3. `botocore.auth.SigV4Auth(creds, "sts", "us-east-1").add_auth(request)` — signs in place, sets `Authorization` + `X-Amz-Date` (+ `Host`).
4. POST `{Authorization, X-Amz-Date, Host, Content-Type}` + body + a fresh `uuid4` nonce to `${AUTOM8Y_AUTH_OPERATOR_TOKEN_URL}` (NEW env var; see §4).
5. Parse `SuccessResponse[TokenResponse]` → return `access_token` (+ `expires_in` for the cache).

**Signer options enumerated:**
- **S-A — botocore `SigV4Auth` (RECOMMENDED).** Already in-image; canonical; matches auth's GetCallerIdentity-replay expectation exactly. **CHOSEN.**
- **S-B — hand-rolled SigV4.** Re-implements a security-critical algorithm; high defect surface; no upside. **REJECTED.**
- **S-C — `aws-requests-auth` / extra lib.** New dependency for what botocore already does. **REJECTED.**

---

## 3. The call-site rewire + token-reuse (GAP-1a substrate; GAP-1b is escalated)

### 3.1 What GAP-1a actually wires

Because the covered set is ∅ (§1), GAP-1a does **NOT** rewrite the 12 `_fetch_table` dispatch arms. It delivers a **NEW, uncalled-in-production** consumer method on `DataServiceClient`:

`get_operator_insights_batch_async(insight_name: str, phones: list[str], *, period, start_date, end_date, filters, limit) -> InsightsResponse-compatible`

- mints (or reuses, §3.2) an operator token via §2,
- POSTs `OperatorBatchInsightRequest` (`{phones | phone_vertical_pairs, period, …, insight_name}`) to `POST /api/v1/insights/operator/execute-batch` with `Authorization: Bearer {operator_token}`,
- parses `SuccessResponse[BatchInsightResponse]`; exposes `.data` (a `list[dict]`, models.py:384) behind the same minimal surface the export reads (`response.data`, workflow.py:673) via a thin adapter.

This method is the substrate a future GAP-1b cutover calls. **No production call-site invokes it in GAP-1a** → INERT (and 403-INERT even if invoked, because the allowlist is empty pre-FLIP).

> The auth-injection seam for the OLD SA path is `DataServiceClient._get_auth_token()` (`client.py:450`) → injected as `Authorization: Bearer` at `client.py:439`. GAP-1a does **NOT** touch this seam (the SA path must keep working for the 12 live tables). The operator method carries its OWN Authorization header per request; it does not route through `_get_auth_token`.

### 3.2 Token-reuse strategy

The operator token TTL is **300s** (`OPERATOR_TOKEN_TTL_SECONDS=300`). The export runs over many offices per run.

- **T-A — mint per office.** N offices → N mints. Hammers the auth mint (rate-limited 30/min/IP, `OPERATOR_TOKEN_RATE_LIMIT`), pointless STS load. **REJECTED.**
- **T-B — mint once per run, reuse across the batch (RECOMMENDED).** The operator route is itself a **batch over `phones`** — a single `execute-batch` call serves many offices with one token. Mint once, hold in memory, send one (or few) batch requests. **CHOSEN.**
- **T-C — mint once, refresh-on-401/near-expiry.** T-B plus a guard: if `expires_in` is within a skew margin of elapsed, or a 401 returns, re-mint once and retry. **CHOSEN as the hardening of T-B** (a long run can exceed 300s). Bounded single retry; no infinite loop.

Token is held **in process memory only**, never written to disk/SM/log (CG-6). The mint client is constructed per-run (Lambda invocation), so the token dies with the invocation.

---

## 4. The deploy-INERT ruling + graceful-INERT behavior

### 4.1 The INERT gate ruling (option-enumerated)

- **I-A — rely on the empty `OPERATOR_ARN_ALLOWLIST` 403 as the natural INERT gate (RECOMMENDED, cleanest).** Pre-FLIP the allowlist is `[]`, so the mint 403s for everyone including the asana role. GAP-1a's operator method handles the 403 gracefully (§4.2). No new flag needed; the gate is the same one the auth/data build already documents as the INERT mechanism. **CHOSEN.**
- **I-B — a new asana feature flag (e.g. `AUTOM8Y_DATA_OPERATOR_ENABLED`).** Redundant with I-A AND with the two existing kill-switches (`AUTOM8_EXPORT_ENABLED` workflow-level, workflow.py `EXPORT_ENABLED_ENV_VAR`; `AUTOM8Y_DATA_INSIGHTS_ENABLED` client-level, `client.py:102`). YAGNI for an uncalled method. **REJECTED as the primary gate** — but see I-C.
- **I-C — reuse the existing `AUTOM8Y_DATA_INSIGHTS_ENABLED` kill-switch for the operator method too.** When GAP-1b eventually wires call-sites, the operator method should honor the SAME emergency kill-switch the rest of the data client honors, so an operator can dark the whole data integration with one lever. **CHOSEN as a defense-in-depth addition to I-A** (not the INERT gate; a kill-switch for the live era).

**Net:** INERT is enforced by the empty allowlist (I-A); the operator method additionally respects `AUTOM8Y_DATA_INSIGHTS_ENABLED` (I-C). No new flag (I-B rejected).

### 4.2 Graceful-INERT behavior (precise)

The operator method MUST fail **closed and quiet** and MUST NEVER fall back to the SA fleet-read:

1. mint 403 (empty/again-tripwire allowlist) → raise a typed `OperatorMintRefusedError` (new, repo-local, in the asana errors module), logged at WARNING with `reason="mint_refused"`. **No crash, no retry-storm, no SA fallback.**
2. operator route 404-as-oracle (non-owned / non-operator / non-allowlisted insight) → typed `OperatorAccessDeniedError`, WARNING. No SA fallback.
3. Because **no production call-site invokes the method in GAP-1a**, neither error reaches the live export → **the counter stays RED with zero regression** (the 12 tables continue on the SA path untouched).
4. **NO fall-back-to-fleet-read anywhere.** A fleet-read fallback would re-assert DATA-VAL-003 and defeat the telos. This is a named invariant (G-NO-FALLBACK), enforced by a test (§7 AT-INERT-3).

---

## 5. The round-trip proof harness (the G-THEATER bar — NOT a green CI)

A green unit suite with mocked HTTP proves nothing about the real mint + real operator route. The proof bar is a **REAL round-trip** under the deployed-image condition, achievable WITHOUT the operator FLIP.

### 5.1 Harness options

- **H-A — off-prod real round-trip against a synthetic-ARN-allowlisted auth (RECOMMENDED, DECISIVE).** Stand up auth (or a staging auth) with `OPERATOR_ARN_ALLOWLIST=[<the test caller's role ARN>]` and the real STS pin. The harness, running under an IAM role on that allowlist, executes the FULL chain: ambient creds → SigV4 GetCallerIdentity → `/operator/token` → real Bearer → `POST /insights/operator/execute-batch` with an **allowlisted** `insight_name` (`business_summary`) for a seeded synthetic owned office → assert a real `BatchInsightResponse`. This exercises every real boundary (STS signature validity, host-pin, freshness, REC-3 admission, C-1 allowlist, owned-set authorize, executor) with only a synthetic allowlist entry — the production FLIP is untouched. **CHOSEN as the discharge artifact.**
- **H-B — definitive integration test in CI with a containerized auth+data+STS.** Same chain, hermetic, repeatable. Strong, but STS cannot be faithfully containerized (the SigV4 signature is validated by *real* AWS STS). A moto/stub STS proves the wiring but not the signature semantics. **CHOSEN as the CI-resident complement** to H-A (wiring regression), explicitly NOT a substitute for H-A's real-STS leg.
- **H-C — mocked-HTTP unit tests only.** Proves serialization, not the round-trip. **REJECTED as the proof bar** (it is the floor, not the bar).

### 5.2 Discriminating (two-sided) canaries

Per discriminating-canary doctrine, each canary bites only on the defect:
- **RT-1 (mint, two-sided):** allowlisted role → token minted (GREEN); a deliberately **stale** X-Amz-Date (skew > 60s) → 403 `stale_x_amz_date` (RED-correctly-rejected). Proves freshness is real, not theater.
- **RT-2 (consume, two-sided):** allowlisted `insight_name=business_summary` for an **owned** office → 200 `BatchInsightResponse` (GREEN); a **non-allowlisted** name (e.g. `reconciliation`) → bare 404-as-oracle (RED-correctly-rejected). Proves C-1 is enforced end-to-end.
- **RT-3 (ownership, two-sided):** an **owned** office → authorized; a **non-owned** office → bare 404 (no oracle). Proves DATA-VAL-003 sidestep (bounded O, not master key).

---

## 6. The deployed-image discipline (the scar)

The auth deploy crash-looped TWICE on a test/dev-only dep on the startup/import path. The rewire MUST be **import-clean under the deployed-image condition.**

- All GAP-1a imports (`boto3`, `botocore.auth`, `botocore.awsrequest`, the HTTP client, repo-local error types) MUST be runtime deps — **boto3 is already runtime (§2.2)**; no test/dev-only module may appear on any import path reachable from the Lambda handler `src/autom8_asana/lambda_handlers/insights_export.py` → `workflow_handler` → `DataServiceClient`.
- **Verification (named):** build the asana runtime image (or `uv sync` with the **prod/non-dev** resolution the Dockerfile uses) and import the handler module + construct `DataServiceClient` with the operator method present. The asana equivalent of `uv sync --no-dev`: run the import-clean probe **inside the built image / prod dependency set**, not the dev venv. (Asana ships `Dockerfile`; the probe runs against that image's interpreter.)
- **G-IMPORT acceptance:** `python -c "import autom8_asana.lambda_handlers.insights_export"` succeeds in the prod image with zero dev deps installed (AT-IMG-1).

---

## 7. Contracts → named acceptance tests, and the GAP-1b escalation

### 7.1 GAP-1a acceptance tests (one per contract)

| ID | Contract | Test |
|----|----------|------|
| AT-MINT-1 | SigV4 GetCallerIdentity body is exactly the allowed action | mint client emits `iam_request_body == "Action=GetCallerIdentity&Version=2011-06-15"`; mutate one byte → auth 403 `disallowed_sts_action`. |
| AT-MINT-2 | Host signed for the pinned STS host | signed `Host`/credential-scope targets `sts.amazonaws.com`; a regional host → auth 403 `host_pin_mismatch`. |
| AT-MINT-3 | Freshness | sign-then-POST within 60s GREEN; injected stale `X-Amz-Date` → 403 `stale_x_amz_date` (RT-1). |
| AT-MINT-4 | No SDK floor / no secret at rest | mint uses ambient `boto3` creds only; grep-zero for any operator-token persisted to SM/disk/log. |
| AT-CONSUME-1 | Bearer carries the minted operator token, not the SA token | operator method's Authorization == minted token; `_get_auth_token` (client.py:450) NOT called on the operator path. |
| AT-CONSUME-2 | Request shape matches `OperatorBatchInsightRequest` | body validates against `{phones XOR phone_vertical_pairs, period…, insight_name}`; round-trips to a real `BatchInsightResponse` (RT-2). |
| AT-CONSUME-3 | Response adapter exposes `.data` (list[dict]) | adapter surfaces `BatchInsightResponse.data` (models.py:384) as the export's `response.data` shape. |
| AT-INERT-1 | Empty allowlist → graceful 403 | against an empty-allowlist auth, mint → `OperatorMintRefusedError`, WARNING, no crash. |
| AT-INERT-2 | No production call-site | grep-zero: no `_fetch_table` arm / no workflow path invokes `get_operator_insights_batch_async` in GAP-1a. |
| AT-INERT-3 | G-NO-FALLBACK | on mint-403 or 404, the operator method NEVER calls the SA fleet-read path; assert no `/data-service/insights` / `/appointments` / `/leads` request is emitted as a fallback. |
| AT-IMG-1 | Deployed-image import-cleanliness | handler imports in the prod image with zero dev deps (§6). |
| RT-1/2/3 | Real round-trip canaries | §5.2, discharged by the H-A off-prod run (the G-THEATER bar). |

### 7.2 GAP-1b — the escalation package (NOT decided here)

Escalate to Potnia → requirements-analyst + operator, with the security gate (ADR-0040) in the loop. The decision matrix per table family:

| Family | Operator-plane admissible? | Decision needed |
|--------|----------------------------|-----------------|
| 8 factory aggregates (base/assets/business_offers/ad_questions) | Only after data-plane builds matching **de-identified registered aggregate insights** + C-1 allowlist additions (each ADR-0040-reviewed) AND product accepts the registered-insight output as a substitute for the factory-frame output | data-plane extension scope + product equivalence sign-off |
| APPOINTMENTS, LEADS (per-patient PII) | **NO — inadmissible by design** | product: drop from cross-tenant export, OR keep on a fleet-read path (DATA-VAL-003 conflict — security must rule) |
| RECONCILIATION ×2 (financial PII) | **NO — C-1 EXCLUDED pending OD-5** | operator OD-5 ratification + data-owner sign-off, OR drop/keep-SA |

**Architect's hard line:** do NOT silently drop or down-scope client data. The export currently produces 12 tables for the agency; any path that produces fewer (or moves PII tables off-tenancy-bounded auth) is a stakeholder decision, surfaced explicitly. The security gate (ADR-0040, FEATURE+ — auth/PII/external-integration) is **INVOKED** for GAP-1b's data-plane extension; the architect hands off the verdict, does not consume it.

---

## 8. Build DAG

```
GAP-1a (this TDD, buildable INERT now, keystone-free):
  A1  _operator_mint.py (SigV4 → /operator/token)            [no SDK floor]
       │
  A2  DataServiceClient.get_operator_insights_batch_async    [consumes operator route]
       │     ├─ response adapter (.data surface)
       │     └─ token-reuse (T-B + T-C single-retry)
       │
  A3  graceful-INERT errors + G-NO-FALLBACK                  [OperatorMintRefusedError / OperatorAccessDenied]
       │
  A4  unit suite (AT-*) + H-B CI integration (stub STS)
       │
  A5  H-A off-prod REAL round-trip (RT-1/2/3)                ← the G-THEATER discharge artifact
       │
  A6  AT-IMG-1 deployed-image import probe                   ← the deployed-image scar discharge
       │
  ▶  merged + deployed-INERT  (RUNG CEILING — STOP)

GAP-1b (ESCALATED — gated, NOT in this build):
  B0  Potnia → requirements/operator scope ruling (12-table matrix §7.2)
  B1  data-plane extension (registered aggregate insights + C-1 additions)  ── ADR-0040 security gate INVOKED
  B2  per-table call-site rewire of the aggregate-eligible subset
  B3  PII-table disposition (drop / keep-SA-under-security-ruling / OD-5)
  ▶  ONLY THEN can the SA fleet-read path be retired → counter moves at operator FLIP
```

---

## 9. ADR-delta

- **ADR-Δ1 (mint transport):** asana mints the operator token via botocore `SigV4Auth` on `sts:GetCallerIdentity`, forwarding signed components to `/operator/token`. No `autom8y-auth` SDK floor on the asana side (asana sends a token string; it never deserializes `OperatorClaims`). Supersedes any assumption that the consumer needs the SDK.
- **ADR-Δ2 (mapping):** the operator route and the export consume DISJOINT data-plane subsystems (registered-insight-by-name vs factory/frame); intersection = ∅. GAP-1 is NOT a 1:1 rewire. Recorded as the load-bearing finding; falsifies the operator-route docstring premise that business_summary is "the per-office aggregate the asana export consumes."
- **ADR-Δ3 (split + escalation):** GAP-1 splits into GAP-1a (buildable INERT substrate) and GAP-1b (escalated scope expansion). The SA fleet-read path is **NOT retired by GAP-1a**; retirement is gated on GAP-1b's product+security rulings.
- **ADR-Δ4 (INERT gate):** the empty `OPERATOR_ARN_ALLOWLIST` is the INERT gate (I-A); the operator method additionally honors `AUTOM8Y_DATA_INSIGHTS_ENABLED` (I-C). No new asana feature flag.
- **ADR-Δ5 (no-fallback invariant):** G-NO-FALLBACK — the operator path NEVER falls back to a fleet-read on refusal/denial. Test-enforced (AT-INERT-3). Preserves DATA-VAL-003 / c1b / REC-3.
- **ADR-Δ6 (security gate):** GAP-1b data-plane extension triggers ADR-0040 (FEATURE+, PII/auth/external-integration). Architect INVOKES + HANDS OFF the `security-verdict`; does not consume it.

---

## 10. Open UV-Ps (unverified premises carried forward)

- [UV-P: the C-6 mint + operator route are not merely merged but DEPLOYED and reachable from the asana Lambda's network/identity at FLIP time | METHOD: deferred-to-flip-integration | REASON: this TDD verified source presence on origin/main for all three repos; live reachability + the asana role's eventual allowlist entry are operator-FLIP-time facts, not buildable here]
- [UV-P: a registered de-identified aggregate insight can reproduce each factory-frame export table acceptably (product equivalence) | METHOD: deferred-to-gap1b-requirements | REASON: SUMMARY↔business_summary / ASSET TABLE↔asset_level_stats adjacency is semantic, not proven-equivalent; needs data-owner + product sign-off in GAP-1b]
- [UV-P: STS region for SigV4 credential scope (`us-east-1`) matches what the global `sts.amazonaws.com` endpoint accepts for the asana role | METHOD: deferred-to-H-A-round-trip | REASON: global STS accepts us-east-1-scoped SigV4; confirm in the real round-trip (RT-1), not in unit mocks]
- [UV-P: the asana role ARN that the operator allowlists at FLIP equals `arn:aws:iam::696318035277:role/autom8-asana-insights-export-lambda-role` after `normalize_arn` collapses the assumed-role session | METHOD: deferred-to-flip | REASON: the Lambda presents an `assumed-role` ARN at runtime; auth `normalize_arn` collapses it to the `role/` form — the allowlist must hold the collapsed form; verify in H-A]
- [UV-P: GAP-1b PII-table disposition (drop vs keep-SA vs OD-5) | METHOD: deferred-to-potnia-escalation | REASON: product/operator/security decision, explicitly out of architect scope]

---

*End TDD. Reads pinned: asana `e7d71fa8`, data `3169fa96`, auth `3df3298a`. No code mutated.*
