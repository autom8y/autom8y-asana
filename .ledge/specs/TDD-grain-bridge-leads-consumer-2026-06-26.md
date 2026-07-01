---
type: spec
subtype: tdd
status: accepted
lifecycle_note: "design-lock (architect) — accepted as the build contract; build = principal-engineer"
initiative: grain-bridge-resolver
node: WS-CONSUMER + WS-SKIP + WS-CANARY (thin asana consumer)
date: 2026-06-26
author: architect (10x-dev)
rung: DESIGN-LOCK-READY (build = principal-engineer; built != verified_realized)
self_grade: MODERATE   # G-CRITIC cap; STRONG = rite-disjoint review critic re-runs the two-sided canary
impact: high
impact_categories: [security, auth, api_contract, cross_service]
consumes_contract:
  auth: "autom8y origin/main = 1ad88e87 (PR #779, S1 AUTH-BRIDGE v2)"
  data: "autom8y-data origin/main = dd4566e5 (PR #206; supersedes frame-cited 9555bff4 — re-verified live, all depended-on elements present)"
  consumer_base: "autom8y-asana origin/main = b9648de4"
supersedes_premise:
  - "frame data SHA 9555bff4 -> RE-VERIFIED live as dd4566e5 (G-PREMISE: mains move)"
  - "grandeur-anchor 'get_insights_async leads read' -> CORRECTED to get_leads_async (the actual LEADS dispatch; get_insights_async serves the other INSIGHTS-factory tables)"
  - "THREAT diagram 'office_phone -> normalize(guid)' -> CORRECTED: ebid = normalize_chiropractor_guid(company_id); office_phone is the read key + report label, company_id(==guid) is the ebid input"
telos_ref: ".sos/wip/frames/grain-bridge-resolver.md (telos block) — verified_realized is eunomia's + the review critic's, rite-disjoint, post-C1, LIVE"
---

# TDD — grain-bridge-resolver thin asana leads consumer

> Design-lock for the per-business single-tenant LEADS read + the 4-class
> emitted skip-signal + the two-sided discriminating canary. Bound to the
> P-3 VERIFIED chain on the live mains (G-PREMISE re-verified at authoring).
> The resolver halves (auth S1 ebid reverse-resolver; data S2 collision-guard)
> are MERGED grounding — this TDD CONSUMES them; it authors NO new resolver
> (G-PROPAGATE). Reaches BUILT (PR opened, not merged); merge / fleet-retire /
> Lever C1 / prod deploy / verified_realized stay the operator's (G-RUNG).

## 0. Resolved-Chain Receipts (SVR — direct inspection at design-lock, 2026-06-26)

Every platform-behavior claim below carries a `git show <sha>:<path>` file:line
anchor. Truth is `origin/main` ONLY; phantom working trees (auth 3149f5d7, data
92d3606d) are never cited.

| # | Claim (verified) | Anchor (file:line @ SHA) |
|---|------------------|--------------------------|
| R1 | ebid = `normalize_chiropractor_guid(guid)`: UUID passthrough lowercased, OR numeric -> `uuid5(GUID_NAMESPACE, guid)`; namespace frozen `a1b2c3d4-e5f6-7890-abcd-ef1234567890` | `autom8y` `sdks/python/autom8y-guid/src/autom8y_guid/_converter.py:80` (+ namespace `:18`) @ 1ad88e87 |
| R2 | the cross-service insights export "holds an `office_phone`-derived `external_business_id` (`normalize(guid)`)"; reverse seek is a STORED-COLUMN equality match (uuid5 non-reversibility irrelevant); `business_id` never crosses the wire | `autom8y` `services/auth/.../services/identity_resolver.py:1-13,37-65` @ 1ad88e87 |
| R3 | the asana `Business` entity carries `company_id = TextField()`, a cascading field (COMPANY_ID, target_types=None = all descendants) | `autom8y-asana` `src/autom8_asana/models/business/business.py:263,304` @ b9648de4 |
| R4 | `company_id == chiropractors.guid` (the UUID before `@` in the appointments address) | `autom8y-asana` `src/autom8_asana/resolution/gfr/truth_source.py:52` @ b9648de4 |
| R5 | `autom8y-guid` is a publishable package (name `autom8y-guid`, v0.1.0, uv_build); the SAME transform is pinned by the producer (auth-mysql-sync) AND the data plane — "re-derivation would risk silent drift" | `autom8y` `sdks/python/autom8y-guid/pyproject.toml:6` + `.../__init__.py:5-8` @ 1ad88e87 |
| R6 | `ExchangeBusinessRequest{client_id, client_secret, business_id, requested_scopes:list[str]|None, external_business_id:str|None}`; all optional; Basic-auth ingress preferred | `autom8y` `services/auth/.../routers/tokens.py:524-530` @ 1ad88e87 |
| R7 | ebid fold fires ONLY when `external_business_id is not None AND business_id is None` -> `resolve_business_id_by_external_id(ebid, db)` | `autom8y` `services/auth/.../routers/tokens.py:808-814` @ 1ad88e87 |
| R8 | oracle seal: `resolved is None OR str(resolved) not in authorized_organizations` -> uniform **404 AUTH-TEB-005**, mint NOT reached; 404 echoes ONLY the caller's own `external_business_id`; miss ≡ out-of-set byte/status/header-identical | `autom8y` `services/auth/.../routers/tokens.py:825-857` @ 1ad88e87 |
| R9 | per-credential SA rate-limit (`rl:tokens_exchange_business:sa:{client_id}`, `OAUTH_TOKEN_RATE_LIMIT`) -> **429 AUTH-TEB-006** + Retry-After; per-IP limit precedes it | `autom8y` `services/auth/.../routers/tokens.py:762-779` @ 1ad88e87 |
| R10 | AUTH-TEB status map: 001=**401** (bad creds), 003=**403** (scope-exceeds-grant / unauthorized), 005=**404** (unknown/out-of-set), 006=**429** (rate-limit) | `autom8y` `services/auth/.../services/tokens_exchange_errors.py:88-108` + `tokens_exchange_errors_extended.py:145-205` @ 1ad88e87 |
| R11 | the pinned `autom8y-auth` SDK TokenManager exchange sends an **EMPTY body** (`"json": {}`) = the fleet/exempt path; business-scoped `{external_business_id, requested_scopes}` is "a future API" NOT present | `autom8y` `sdks/python/autom8y-auth/src/autom8y_auth/token_manager.py:355-368` @ 1ad88e87 |
| R12 | the asana LEADS read is `get_leads_async(office_phone, *, days, exclude_appointments, limit) -> InsightsResponse`, "Maps to GET /leads ... same auth as get_insights_async" | `autom8y-asana` `src/autom8_asana/clients/data/client.py:1245-1281` @ b9648de4 |
| R13 | the LEADS table dispatch in the existing 12-table workflow is `DispatchType.LEADS -> get_leads_async` (NOT get_insights_async) | `autom8y-asana` `src/autom8_asana/automation/workflows/insights/tables.py:40` + `.../workflow.py` `_fetch_table` LEADS case @ b9648de4 |
| R14 | DataServiceClient injects auth via `_get_auth_token() -> auth_provider.get_secret(token_key)` set as `Authorization: Bearer {token}` per request; `auth_provider: AuthProvider | None` is a ctor arg | `autom8y-asana` `src/autom8_asana/clients/data/client.py:104-132,415-472` @ b9648de4 |
| R15 | the AuthProvider the consumer mirrors reads `SERVICE_CLIENT_ID` + `resolve_secret_from_env("SERVICE_CLIENT_SECRET")` (`_ARN` on Lambda, bare on ECS/local); RuntimeError propagates honestly (no silent no-cred path) | `autom8y-asana` `src/autom8_asana/auth/service_token.py:38-78` @ b9648de4 |
| R16 | data anti-IDOR: `detail_office_phone = None if is_fleet_read(request) else tenant_office_phone` — the JWT-resolved tenant key OVERRIDES the client `office_phone` query param; client value validated for shape but NEVER trusted as tenant selector | `autom8y-data` `src/autom8_data/analytics/routes/data_service.py:1009` (region 996-1011) @ dd4566e5 |
| R17 | `OfficePhoneCollisionError -> 409 DATA-CONFLICT-002` handler present; office_phone -> >1-distinct-guid collision | `autom8y-data` `src/autom8_data/api/errors.py:1009,1030,1045` @ dd4566e5 |
| R18 | `is_fleet_read(request)` carrier present; DATA-VAL-003 control present | `autom8y-data` `src/autom8_data/api/auth/fleet_read_admission.py:48` + DATA-VAL-003 refs @ dd4566e5 |
| R19 | seal canary to mirror: GREEN in-set ebid -> 200 + `create_mock.assert_awaited_once()` (business_id==resolved); RED None/out-of-set -> 404 AUTH-TEB-005 + `create_mock.assert_not_called()`; miss ≡ out-of-set identical error block | `autom8y` `services/auth/tests/test_identity_resolver_and_ebid_seal.py:219-300` @ 1ad88e87 |

**G-PREMISE note (data main moved).** The frame cited data `9555bff4`; live `origin/main` is `dd4566e5` (#206 added a *read-only office_phone<->guid binding-verify* endpoint). All depended-on data elements (R16/R17/R18) re-verified PRESENT at dd4566e5. The new binding-verify endpoint is adjacent and OOS for this build (the consumer derives the ebid locally; see §3.1) — watch-register only.

## 1. System Context

```
   ┌──────────────────────── autom8y-asana (THIS BUILD: the thin consumer) ─────────────────────────┐
   │                                                                                                  │
   │  ACTIVE Offer enumeration ──▶ ResolutionContext.business_async()                                 │
   │   (section-targeted, G-DENOM)      │  yields {gid, office_phone, vertical, name, company_id}      │
   │                                    ▼                                                              │
   │                          ebid = normalize_chiropractor_guid(company_id)   [autom8y-guid, R1/R5]   │
   │                                    │  (LOCAL — no guid fetch; bootstrap intact)                    │
   │                                    ▼                                                              │
   │   BusinessTokenMinter ── POST /tokens/exchange-business ───────────────────────────┐             │
   │     Basic auth(SERVICE_CLIENT_ID:SECRET)   {external_business_id, requested_scopes:[data:read]}   │
   │                                    │                                               │             │
   │   PerBusinessTokenProvider(token) ◀┘ (200)                                          │             │
   │                                    │                                               ▼             │
   │   DataServiceClient(auth_provider=PerBusinessTokenProvider)                    ┌─────────┐        │
   │     get_leads_async(office_phone) ── Authorization: Bearer <per-business JWT> ─▶│  auth   │        │
   │                                    │                                           │ exchange│        │
   │                                    ▼                                           │-business│        │
   │   GrainBridgeLeadsConsumer: success(succeeded+1) | EMIT skip(class,+1)         └─────────┘        │
   │     reconciliation invariant: attempted == succeeded + Σ skip-class counts                        │
   └──────────────────────────────────────────────────────────────────────────────────────────────┘
                                          │ Bearer <per-business JWT>
                                          ▼
   ┌──────────── autom8y-data (MERGED, CONSUME) ────────────┐     ┌──── autom8y auth (MERGED, CONSUME) ────┐
   │ GET /leads = get_lead_details                          │     │ exchange-business ebid fold + oracle    │
   │   detail_office_phone = None if is_fleet_read           │     │ seal: ebid -> business_id, membership   │
   │     else tenant_office_phone   [R16 anti-IDOR]          │     │ pre-check -> 404 AUTH-TEB-005 | 200 mint │
   │ OfficePhoneCollisionError -> 409 DATA-CONFLICT-002 [R17] │     │   [R6-R10] ; [data:read] only [SC-BUILD-1]│
   └────────────────────────────────────────────────────────┘     └─────────────────────────────────────────┘
```

**Trust boundary.** The minted per-business token binds `business_id` (auth's UUID,
reverse-resolved from the ebid behind the oracle seal). It carries NO
`external_business_id` claim (c1b; R6 docstring) and NO `bypass_scope` -> it does
NOT trip `is_fleet_read` (R18) -> DATA-VAL-003 satisfied positively. The fleet
token is never minted nor used on the LEADS path (AC-M2). The full fleet-token
retirement (all tables) is the predecessor envelope + Lever C1 (OOS-2/OOS-4).

## 2. Components (build surface for principal-engineer)

All NEW unless marked. Module locations follow `repository-map.md` (auth in
`auth/`, data-client surface in `clients/data/`, orchestration in
`automation/workflows/`).

### 2.1 `auth/business_token.py` — `BusinessTokenMinter` (NEW)
Thin exchange-business client. **Built (not the SDK)** because the pinned
`autom8y-auth` TokenManager sends an empty body = the fleet path (R11); the
business-scoped exchange API is absent. See ADR §D3.

```python
class BusinessTokenMinter:
    SCOPE_DATA_READ: ClassVar[list[str]] = ["data:read"]   # SC-BUILD-1, FROZEN; never read:pii

    def __init__(self, client_id: str | None = None, client_secret: str | None = None,
                 auth_url: str = "https://auth.api.autom8y.io") -> None: ...
        # SC-BUILD-4: cid = SERVICE_CLIENT_ID; csecret = resolve_secret_from_env("SERVICE_CLIENT_SECRET")
        # mirror service_token.py:38-78 EXACTLY (delivery-convention-agnostic; RuntimeError propagates).
        # No client_secret persisted; process-env only.

    async def mint(self, external_business_id: str) -> str:
        # POST {auth_url}/tokens/exchange-business
        #   headers: Authorization: Basic b64(client_id:client_secret)        [R6 preferred ingress]
        #   json:    {"external_business_id": ebid, "requested_scopes": ["data:read"]}
        # returns: the per-business access_token (single-tenant JWT)
        # raises (classified — see §4):
        #   404 AUTH-TEB-005 -> MintResolutionMiss          (no token; the RED arm)
        #   429 AUTH-TEB-006 -> MintRateLimited(retry_after) (transient)
        #   401 AUTH-TEB-001 -> MintCredentialError          (FATAL delegator misconfig — not a per-business skip)
        #   403 AUTH-TEB-003 -> MintScopeError               (FATAL — delegator lacks data:read; misconfig)
        #   409 DATA-CONFLICT-002 -> MintCollision           (defensive; fail-closed)
        #   5xx / network / timeout -> MintUnavailable        (transient)
```
- HTTP via `autom8y-http` (the platform client; same stack as DataServiceClient).
- `requested_scopes` is the FROZEN constant `["data:read"]` — assert at the call
  site and in the canary that the request body's `requested_scopes == ["data:read"]`
  on EVERY mint (SC-BUILD-1 / AC-M3 / EC-10 / TC-GREEN scope assertion).
- The ebid is consumed as a request INPUT only; the minter NEVER folds it into any
  token payload it constructs (c1b; AC-M6). The minter constructs no token payload
  at all — it receives one.

### 2.2 `auth/per_business_provider.py` — `PerBusinessTokenProvider` (NEW)
Implements `protocols.auth.AuthProvider` (R14). Wraps ONE minted per-business token.
```python
class PerBusinessTokenProvider:
    def __init__(self, token: str) -> None: self._token = token
    def get_secret(self, key: str) -> str: return self._token   # key ignored — single token
    def close(self) -> None: ...
```
- Per-business isolation (EC-6 / AC-M5): one provider per business; never reused
  across tenants. The leads `DataServiceClient` is constructed with this provider
  so the JWT business_id == the tenant whose company_id minted it
  (mismatch is unreachable-by-construction; see §6 EC-9).

### 2.3 `automation/workflows/leads_consumer.py` — `GrainBridgeLeadsConsumer` (NEW)
The orchestrator. Owns the per-business iteration + skip taxonomy + reconciliation.
Does NOT entangle the existing 12-table `InsightsExportWorkflow` (OOS-4 — that
envelope owns the non-leads tables).
```python
class GrainBridgeLeadsConsumer:
    def __init__(self, asana_client, minter: BusinessTokenMinter,
                 data_client_factory: Callable[[AuthProvider], DataServiceClient],
                 *, max_concurrency: int = 5) -> None: ...

    async def run(self, scope: EntityScope) -> LeadsRunResult:
        # 1. enumerate ACTIVE offers (G-DENOM) — REUSE the section-targeted
        #    enumeration from InsightsExportWorkflow (extract to a shared helper:
        #    automation/workflows/active_offer_enumeration.py) so both consumers
        #    share ONE ACTIVE-set definition (DRY; no second classifier).
        # 2. resolve each Offer -> Business -> (office_phone, vertical, company_id)
        #    via ResolutionContext.business_async()  [reuse workflow.py:_resolve_offer
        #    shape; EXTEND the returned tuple to include business.company_id].
        # 3. ebid = compute_ebid(company_id)        [§2.4]
        # 4. token = await minter.mint(ebid)
        # 5. client = data_client_factory(PerBusinessTokenProvider(token))
        # 6. resp = await client.get_leads_async(office_phone, days=..., limit=...)
        # 7. classify: succeeded (resp.data non-empty AND not is_stale) | inactive_or_empty
        # On any classified exception -> EMIT skip (log + metric + count); NEVER
        # silent-drop; NEVER fall back to the fleet token.
        # Returns LeadsRunResult{attempted, succeeded, skipped_by_class: dict[SkipClass,int]}
        # ASSERT (close-of-run): attempted == succeeded + sum(skipped_by_class.values())  [AC-S3]
```

### 2.4 `automation/workflows/leads_ebid.py` — `compute_ebid` (NEW, thin)
```python
from autom8y_guid import normalize_chiropractor_guid   # ADR §D2 (pinned transform; no re-derivation)

def compute_ebid(company_id: str | None) -> str:
    # company_id absent (None) or null/whitespace -> raise EbidInputAbsent / EbidInputNull
    #   (distinct sub-reasons; EC-1 discriminability). normalize raises ValueError on empty;
    #   wrap it into the typed sub-reason so resolution_miss(input_absent|input_null) is
    #   observably distinct from a server 404(server_404).
    normalized, _was_converted = normalize_chiropractor_guid(company_id)
    return normalized
```

### 2.5 `automation/workflows/leads_skip.py` — skip taxonomy (NEW)
```python
class SkipClass(str, Enum):
    RESOLUTION_MISS = "resolution_miss"
    COLLISION_CONFLICT = "collision_conflict"
    INACTIVE_OR_EMPTY = "inactive_or_empty"
    MINT_UNAVAILABLE = "mint_unavailable"

def emit_skip(log, metric, *, klass: SkipClass, office_phone: str, sub_reason: str | None = None) -> None:
    # log.warning(event=klass.value, office_phone=mask_phone_number(office_phone), sub_reason=...)
    #   PII masking via mask_phone_number (SCAR-028 / AC-S4) — never raw E.164.
    # metric: counter "grain_bridge_leads_skipped_total", labels {"class": klass.value}
    # caller increments skipped_by_class[klass] += 1   (the count observable)
```

### 2.5 `lambda_handlers/leads_consumer.py` — entrypoint (NEW, thin)
Mirror `insights_export.py`: `bootstrap()` + a `workflow_handler` wiring
`GrainBridgeLeadsConsumer`. DMS namespace `Autom8y/AsanaLeadsBridge`. Feature-flag
env var (e.g., `AUTOM8_LEADS_BRIDGE_ENABLED`). NOT wired into prod scheduling by
this build (operator deploy, OOS-2).

### 2.6 `pyproject.toml` — add `autom8y-guid>=0.1.0` (dependency add; ADR §D2)
One line in `[project.dependencies]`. The same package the producer + data plane
pin (R5) — third pinned consumer of the canonical transform; no re-derivation.

## 3. Key Design Decisions (full rationale in the companion ADR)

### 3.1 The ebid is derived LOCALLY from `company_id` — the bootstrap is intact
`external_business_id = normalize_chiropractor_guid(business.company_id)` (R1+R3+R4).
`company_id` is a cascading field already carried on the resolved `Business` entity
(R3) and equals the chiropractor guid (R4). The consumer holds it after the
existing Offer->Business resolution — **no guid fetch**. This is load-bearing: the
data self-read `GET /businesses/{office_phone}` is tenant-scoped behind the very
token being minted, so a fetch-the-guid design would be a genuine chicken-and-egg
bootstrap break. Resolving the dispatch's `normalize(office_phone)` vs
`normalize(guid)` ambiguity against the CODE (R1: the converter takes a *guid*, not
a phone; R2: the resolver docstring says `normalize(guid)`): **the SA-ADR's
`normalize(guid)` is authoritative; the THREAT diagram's `office_phone ->
normalize(guid)` is loose shorthand** — office_phone is the LEADS read key + report
label (R12/R16), `company_id`(==guid) is the ebid input. **No false premise; no HALT.**

### 3.2 Per-business token isolation (anti-IDOR, EC-6 / SC-BUILD-3)
One mint + one `PerBusinessTokenProvider` + one leads `DataServiceClient` per
business. The served tenant is the JWT's `business_id`, which DOMINATES the client
`office_phone` param (R16) — the consumer MUST NOT assume its office_phone controls
the tenant. Token reuse across tenants is forbidden (IDOR). Mismatch is
unreachable-by-construction because the SAME `Business` supplies both the
`company_id` (-> ebid -> token business_id) and the `office_phone` (-> read).

### 3.3 [data:read]-only scope pin (SC-BUILD-1)
`requested_scopes` is the frozen `["data:read"]` on EVERY mint. Never `read:pii`,
even if the delegator holds it — the `meta-lead-service` adjacency unmasks PII on
the leads surface. Asserted at the call site AND in the canary (EC-10).

## 4. Error Handling — the 4-class skip taxonomy (WS-SKIP)

Every refusal EMITs `log + metric + skipped-count`. NEVER a silent drop; NEVER a
fleet fallback. The denominator is the ACTIVE-offer set (G-DENOM).

| Skip class | Trigger (verified locus) | Sub-reason | Negative assertion (MUST-NOT) |
|---|---|---|---|
| `resolution_miss` | exchange-business **404 AUTH-TEB-005** (ebid unresolved OR out-of-`authorized_organizations`) [R8]; OR `company_id` absent/null pre-mint [§2.4] | `server_404` \| `input_absent` \| `input_null` (EC-1 discriminability) | no `minter.mint` success; no `get_leads_async` call; no fleet token |
| `collision_conflict` | **409 DATA-CONFLICT-002** (`OfficePhoneCollisionError`) [R17] | — | fail CLOSED — no arbitrary-tenant pick; no leads read with ambiguous binding |
| `inactive_or_empty` | business not in ACTIVE-offer set (pre-filter) OR resolves but `resp.data` empty | `pre_filtered` \| `empty_leads` | not counted as `succeeded`; no mint wasted on a pre-filterable inactive |
| `mint_unavailable` | exchange-business **429 AUTH-TEB-006** [R9] OR 5xx/network, AFTER retry exhaustion (honor Retry-After) | `rate_limited` \| `upstream_5xx` | no fleet fallback; not `succeeded`; not conflated with `resolution_miss` (retryable vs permanent) |

**Non-skip FATAL (distinct from per-business skip).** `401 AUTH-TEB-001` (bad
delegator creds) and `403 AUTH-TEB-003` (delegator lacks `data:read`) are
delegator-level MISCONFIGURATIONS — they manifest identically for EVERY business.
They MUST raise-and-halt the run (mirror `service_token.py`'s honest-propagation
posture, R15) rather than be silently swallowed as 75 `resolution_miss` skips. This
prevents a misconfigured delegator from masquerading as a fleet-wide resolution
miss.

**409 reachability note (honest design surface).** In the merged contract the
forward office_phone->guid collision guard (`resolve_guid_or_raise` ->
`OfficePhoneCollisionError`, R17) is NOT on the JWT-tenant-scoped leads read path
(`get_lead_details` uses `tenant_office_phone` from the JWT, R16 — it never resolves
the client office_phone to a guid), and exchange-business returns 404 (not 409) on
the reverse path. So `collision_conflict` is **defensively handled** — the consumer
maps ANY observed `409 DATA-CONFLICT-002` (from mint or read) to `collision_conflict`,
fail-closed — but it is not primary-path-reachable in the current contract. Retained
per the binding WS-SKIP taxonomy and for contract-fidelity (the data-side
binding-verify endpoint #206 CAN emit it; R17 is live). This is a refinement, not a
contradiction.

**Read-side vs mint-side disambiguation (EC-7).** A data circuit-breaker OPEN or a
read-path 5xx is classified distinctly from a mint-side 5xx — both EMIT, neither is
mislabeled. **Stale-cache (EC-8, ADR-INS-004):** a `get_leads_async` stale-cache hit
(`metadata.is_stale=True`) is NOT counted as a fresh `succeeded` for the
verified-realized signal — it surfaces as `inactive_or_empty(stale)` or a distinct
`stale` observable, never as a live success.

## 5. Security (consumes the merged seal; adds no new oracle)

- **SC-BUILD-1** scope pin `[data:read]` — §3.3, asserted per mint + in the canary.
- **SC-BUILD-3** resolved-key anti-IDOR — §3.2; JWT business_id dominates (R16).
- **SC-BUILD-4** secrets process-env-only — `BusinessTokenMinter` mirrors
  `service_token.py:38-78` (R15): `SERVICE_CLIENT_ID` + `resolve_secret_from_env`,
  Basic-auth exchange, no client_secret on disk/logs, no re-mint.
- **c1b (AC-M6)** the consumer reintroduces NO `external_business_id` into any
  payload it constructs; the ebid is a request input only (R6).
- **Enumeration honesty (AC-S1)** the consumer's `resolution_miss` mirrors the auth
  oracle seal (R8): unknown ≡ unauthorized, uniform handling, no
  existence/timing tell that turns the skip into an enumeration oracle. The
  consumer does NOT log the resolved business_id on a miss (there is none — it
  receives a 404, not a resolution).
- **PII masking (AC-S4)** every skip emission masks office_phone via
  `mask_phone_number` (SCAR-028).
- **Threat-modeler consult**: already discharged at the G-SEC gate (APPROVE
  conditional, MODERATE; HANDOFF §1). This TDD adds no new auth/crypto/PII surface
  beyond consuming the attested contract — no re-consult required.

## 6. Edge-Case Inventory (binding shapes; exact keys are the engineer's)

- **EC-1 three-state company_id**: present+valid -> mint; present-but-null/empty ->
  `resolution_miss(input_null)`, NO exchange-business call with empty ebid;
  absent -> `resolution_miss(input_absent)`. `input_null`/`input_absent` observably
  distinct from `server_404`.
- **EC-2 empty ACTIVE set**: `attempted=0, succeeded=0`, no exception, no mint, no
  fleet fallback; explicit "empty active set" observable distinct from "all skipped".
- **EC-3 transient mint failure**: 429 (either bucket — credential-agnostic, AC-S2)
  or 5xx -> retry per existing backoff (honor Retry-After) -> on exhaustion
  `mint_unavailable`; never conflated with the permanent 404.
- **EC-4 409 collision**: `collision_conflict`, fail-closed (see §4 note).
- **EC-5 partial-batch mix**: all businesses processed; reconciliation invariant
  holds (AC-S3); no business unaccounted.
- **EC-6 per-business token isolation / TTL**: own token per business; mid-iteration
  expiry re-mints for the correct business; never reused across tenants.
- **EC-7 read-side vs mint-side**: classified distinctly; both EMIT.
- **EC-8 stale-cache**: not counted as fresh `succeeded`.
- **EC-9 phone/token tenant mismatch**: unreachable-by-construction (§3.2); the
  consumer asserts the leads `DataServiceClient` is the one bound to the
  per-business provider for the SAME business (no cross-wiring).
- **EC-10 scope-leak boundary**: assert `requested_scopes == ["data:read"]` on every
  mint, even if the delegator holds `read:pii`.

## 7. Test Plan (strictly additive; the existing asana suite + any GFR spine stay GREEN)

Tests via `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.venv/bin/python -m pytest`
(NEVER `uv run` — CodeArtifact 401). Format `uvx ruff@0.15.4 format . --check`.
Full local gate before push: `mypy --strict` + `tests/` + `arch/`.

### 7.1 Unit (the spine)
- `compute_ebid`: UUID passthrough (lowercase/hyphenate), numeric->uuid5 (the 116
  cohort), empty/null/whitespace -> typed sub-reason. Pin one fixture against a
  KNOWN `(company_id -> ebid)` pair computed by `autom8y_guid` directly (proves the
  consumer's transform == the producer's; no drift — R5).
- `BusinessTokenMinter.mint`: status->exception mapping (404/429/401/403/409/5xx)
  against a mocked exchange-business; assert `requested_scopes == ["data:read"]` and
  Basic-auth header shape on the request; assert NO client_secret in logs.
- `GrainBridgeLeadsConsumer.run`: reconciliation invariant
  (`attempted == succeeded + Σ skips`) across a partial-batch fixture (EC-5);
  per-class emission (log+metric+count); never-silent-drop; never-fleet-fallback
  (assert the fleet `ServiceTokenAuthProvider` is never instantiated on the leads
  path).
- `emit_skip`: PII masking (no raw E.164 in log/metric labels).

### 7.2 WS-CANARY — the two-sided discriminating canary (SC-BUILD-2; mirrors R19)
`tests/.../test_grain_bridge_canary.py`. SAME harness; only the INPUT differs
(TC-DISJOINT) — NO production code altered to manufacture RED (G-THEATER).

- **TC-GREEN** — owned (`authorized_organizations`-member) office_phone/company_id:
  mock exchange-business returns 200 + a single-tenant token; assert
  `minter.mint` called once, request `requested_scopes == ["data:read"]`;
  `get_leads_async` returns non-empty -> `succeeded == 1` (and `is_stale is False`).
- **TC-RED (= DATA-VAL-003 non-regression)** — cross-tenant/un-owned company_id:
  mock exchange-business mirrors the oracle seal -> uniform **404 AUTH-TEB-005**;
  assert the minter raised `MintResolutionMiss`, `resolution_miss` EMITted, and
  **`get_leads_async.assert_not_called()`** (the consumer-altitude mirror of
  `create_service_token.assert_not_called()` — no per-business token minted, no
  leads read, no fleet fallback).
- **TC-TEETH (non-vacuity)** — a fixture flag disables the mock seal's membership
  gate; the RED input then flips to a 200 mint (canary bit **404 -> 200**, leads
  read now occurs); restore is byte-identical (sha256 BEFORE==AFTER; the fixture is
  a toggled parameter, NOT an edited production file; worktree clean). Proves the
  canary bites ONLY on the gate.
- **TC-SCOPE** — assert NO arm ever sends `read:pii` (EC-10).

**Attestation.** Self-grade caps **MODERATE** (G-CRITIC). STRONG = the rite-disjoint
`review` critic RE-RUNS RED+GREEN+TEETH and concurs (parallel; not a seam-blocker).
This build reaches **BUILT** (PR opened) — not merged, not verified_realized.

## 8. mypy / ruff / arch implications

- `--strict` clean: `BusinessTokenMinter.mint -> str`; typed mint-exception
  hierarchy; `AuthProvider` protocol conformance for `PerBusinessTokenProvider`
  (R14); `LeadsRunResult` dataclass; `SkipClass(str, Enum)`.
- arch: new modules live in `auth/` (token mint), `automation/workflows/`
  (orchestration), `clients/data/` untouched except as a constructed consumer. No
  layering violation (orchestration depends on auth + clients; not the reverse) —
  Dependency Rule holds (high-level orchestration -> stable client/auth ports).
- ruff: `autom8y_log.get_logger`, no stdlib logging (pyproject bans).
- Atomic per-repo PR boundary; the PR `--json files` must be scoped to the consumer
  surface (no `.claude/ .gemini/ .know/ .mcp.json .knossos/ .sos/` stowaways).

## 9. Build Surface Summary (for principal-engineer)

| File | Action | Key contract |
|------|--------|--------------|
| `pyproject.toml` | EDIT (+1 dep) | `autom8y-guid>=0.1.0` (R5) |
| `auth/business_token.py` | NEW | `BusinessTokenMinter.mint(ebid)->str`; scope=[data:read]; classified exceptions (§4) |
| `auth/per_business_provider.py` | NEW | `PerBusinessTokenProvider(token)` impl AuthProvider (R14) |
| `automation/workflows/leads_ebid.py` | NEW | `compute_ebid(company_id)->str` (autom8y-guid) |
| `automation/workflows/leads_skip.py` | NEW | `SkipClass` + `emit_skip` (mask PII) |
| `automation/workflows/active_offer_enumeration.py` | NEW (extract) | shared ACTIVE-offer enumeration (DRY with InsightsExportWorkflow) |
| `automation/workflows/leads_consumer.py` | NEW | `GrainBridgeLeadsConsumer.run(scope)`; reconciliation invariant |
| `lambda_handlers/leads_consumer.py` | NEW | thin entrypoint (not prod-scheduled this build) |
| `tests/.../test_grain_bridge_canary.py` | NEW | two-sided discriminating canary (§7.2) |
| `tests/.../test_business_token_minter.py` | NEW | status->exception map; scope assertion |
| `tests/.../test_leads_consumer.py` | NEW | reconciliation + skip emission |
| `tests/.../test_compute_ebid.py` | NEW | transform parity + 3-state input |

## 10. Out of Scope (watch-register — surface, don't walk)
Lever C1 apply / SA `business_scoped` flip (operator); fleet-token retirement;
prod deploy / merge (G-RUNG: BUILT only); dedicated `leads-resolver` SA provisioning
(lead-time NOTIFY); DATA-VAL-003 live re-probe (UV-P-DBCLEAN, operator deploy-time);
non-leads insights tables (predecessor envelope, OOS-4); the data binding-verify
endpoint #206; `verified_realized` (eunomia, live, post-C1).

## 11. Handoff Readiness
- [x] Chain resolved LIVE (file:line @ SHA; §0) — no false premise, no HALT.
- [x] Components + signatures specified (§2, §9).
- [x] 4-class skip taxonomy mapped to verified loci (§4).
- [x] Two-sided discriminating canary designed, mirrors the seal (§7.2).
- [x] Security constraints SC-BUILD-1..4 bound (§5).
- [x] Edge cases enumerated (§6).
- [x] Strictly-additive proof plan + local gate (§7, §8).
- Principal-engineer can implement without architectural questions.
