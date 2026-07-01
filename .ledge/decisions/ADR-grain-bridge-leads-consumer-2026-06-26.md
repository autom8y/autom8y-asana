---
type: decision
status: accepted
initiative: grain-bridge-resolver
node: WS-CONSUMER + WS-SKIP + WS-CANARY design-lock
date: 2026-06-26
author: architect (10x-dev)
self_grade: MODERATE   # G-CRITIC cap
companion_tdd: ".ledge/specs/TDD-grain-bridge-leads-consumer-2026-06-26.md"
consumes:
  auth: "autom8y origin/main 1ad88e87 (PR #779)"
  data: "autom8y-data origin/main dd4566e5 (PR #206; supersedes frame-cited 9555bff4)"
  base: "autom8y-asana origin/main b9648de4"
supersedes_premise: "frame data SHA 9555bff4 -> dd4566e5 (re-verified live); grandeur 'get_insights_async' -> get_leads_async; THREAT 'office_phone->normalize(guid)' -> normalize(company_id==guid)"
---

# ADR — grain-bridge-resolver thin asana leads consumer

Five load-bearing decisions for the per-business single-tenant LEADS read.
Every platform-behavior claim carries a `git show <sha>:<path>` file:line anchor;
the full receipt table is in the companion TDD §0 (R1–R19). Grade MODERATE
(G-CRITIC cap; STRONG is the rite-disjoint `review` critic's after re-running the
two-sided canary). This reaches BUILT, not merged (G-RUNG).

---

## D1 — The ebid is derived LOCALLY from `company_id` (bootstrap intact; ambiguity resolved)

**Status:** accepted (one-way door for the consumer's identity model — see Reversibility)

**Context.** The dispatch flagged a load-bearing ambiguity: the THREAT model says
`normalize(office_phone)` (E.164), the SA-ADR says `normalize(guid)`. This decides
whether the consumer derives the ebid LOCALLY (no fetch — bootstrap intact) or must
FETCH a guid (bootstrap break). I resolved it against the merged CODE, not the prose:

- `normalize_chiropractor_guid(guid)` takes a *guid* (UUID passthrough lowercased, or
  numeric -> `uuid5(GUID_NAMESPACE,...)`), NOT a phone (`_converter.py:80` @ 1ad88e87).
- the auth resolver docstring states the export "holds an office_phone-derived
  `external_business_id` (`normalize(guid)`)" (`identity_resolver.py:1-13` @ 1ad88e87).
- the asana `Business` carries `company_id = TextField()` cascading to all
  descendants (`business.py:263,304` @ b9648de4), and `company_id ==
  chiropractors.guid` (`gfr/truth_source.py:52` @ b9648de4).

**Decision.** `external_business_id = normalize_chiropractor_guid(business.company_id)`,
computed caller-side. `company_id` is already on the resolved `Business` entity (after
the existing Offer->Business hierarchy walk) — the consumer derives the ebid with **no
guid fetch**. The SA-ADR's `normalize(guid)` is authoritative; the THREAT diagram's
`office_phone -> normalize(guid)` is loose shorthand (office_phone is the LEADS read
key + report label, `company_id`==guid is the ebid input).

**Why this is the decisive bootstrap fact.** The data self-read
`GET /businesses/{office_phone}` is tenant-scoped (foreign office_phone -> uniform
404) BEHIND the very per-business token being minted. A fetch-the-guid design would be
genuine chicken-and-egg. Because `company_id` is held locally, there is no bootstrap
gap and **no HALT**.

**Alternatives considered.**
- *`normalize(office_phone)`* — REJECTED: the converter consumes a guid, not a phone;
  feeding an E.164 would (a) mismatch what auth-mysql-sync stored in
  `businesses.external_business_id`, producing uniform 404s for the whole fleet, and
  (b) misread the merged contract.
- *Fetch the guid from data before mint* — REJECTED: bootstrap break (tenant-scoped
  read behind the token), and it would add a data-plane resolver dependency the frame
  C2 oracle-locality constraint forbids.

**Consequences.** The consumer extends the Offer->Business resolution to surface
`company_id`. Businesses with absent/null `company_id` become `resolution_miss`
(input_absent/input_null). The "116 numeric cohort" is the `uuid5` branch of the
transform — handled by the same path; a 404 for any such ebid is `resolution_miss(server_404)`.

**Reversibility.** Two-way at the field level (which field feeds normalize is a code
change), but ONE-WAY in identity semantics: the chosen ebid value space MUST equal
auth-mysql-sync's stored image. Mitigated by D2 (pin the same transform). Flagged for
stakeholder awareness: the consumer's ebid is only correct so long as
`company_id == chiropractors.guid` holds (R4) and auth-mysql-sync keeps minting
`external_business_id` via the same `autom8y-guid` transform (R5).

---

## D2 — Add `autom8y-guid` as a pinned dependency; do NOT re-derive the transform

**Status:** accepted

**Context.** `normalize_chiropractor_guid` lives in the publishable `autom8y-guid`
package (v0.1.0, `pyproject.toml:6` @ 1ad88e87). Its own contract states it is
"consumed by both the producer (auth-mysql-sync ... mints the normalized
external_business_id) and the data plane ... re-derivation would risk silent drift"
(`__init__.py:5-8` @ 1ad88e87). asana does NOT currently depend on it.

**Decision.** Add `autom8y-guid>=0.1.0` to `[project.dependencies]` and import
`normalize_chiropractor_guid`. asana becomes the THIRD pinned consumer of the SAME
transform — producer, data plane, and now the leads consumer apply byte-identical
normalization.

**Alternatives considered.**
- *Re-implement the ~10-line transform locally* — REJECTED: violates the package's
  explicit anti-drift contract; a future change to the namespace or numeric handling
  would silently desync the consumer's ebid from auth's stored value (canonical-source
  -integrity). The blast radius is fleet-wide 404s with no obvious cause.

**Tension surfaced + resolved (frame C2).** The frame constraint reads "Asana stays
THIN — NO autom8y_guid data-plane dependency, NO orphan resolver". This prohibition
targets the data-plane RESOLVER (the ebid->business_id reverse seek, which stays
SERVER-SIDE in auth, single-owned). It does NOT prohibit the pure `normalize` transform
— the same frame sentence says "Asana computes `normalize(guid)` caller-side". Importing
`autom8y-guid` for the pure transform (and nothing else) honors C2 oracle-locality while
satisfying the no-drift discipline. The resolver remains server-side; asana adds no
collision check and no second oracle.

**Consequences.** One new dependency. CI must resolve `autom8y-guid` from the same
CodeArtifact index as the other `autom8y-*` pins. Watch-register: if `autom8y-guid` is
not yet published to asana's index, the operator publishes/whitelists it (lead-time
NOTIFY) — same provisioning class as the other internal SDKs asana already pins.

---

## D3 — Build a thin `BusinessTokenMinter`; the SDK exchange path is the fleet path

**Status:** accepted

**Context.** The pinned `autom8y-auth` SDK TokenManager's exchange sends an EMPTY body
(`"json": {}`) — explicitly "the default ... does not request a business_id or
requested_scopes ... callers ... can layer those on via a future API"
(`token_manager.py:355-368` @ 1ad88e87). An empty body is the exempt/FLEET path. The
business-scoped exchange API is NOT present at the pin.

**Decision.** Build a thin consumer-side `BusinessTokenMinter` (autom8y-http) that
POSTs `/tokens/exchange-business` with Basic auth + body
`{external_business_id, requested_scopes:["data:read"]}` (R6), returning the
single-tenant token and classifying the response by status (404/429/401/403/409/5xx ->
§4 taxonomy). Credentials per SC-BUILD-4: `SERVICE_CLIENT_ID` +
`resolve_secret_from_env("SERVICE_CLIENT_SECRET")`, mirroring `service_token.py:38-78`
(R15) — process-env only, no client_secret on disk, no re-mint.

**Alternatives considered.**
- *Use TokenManager's empty-body exchange* — REJECTED: that mints the FLEET token
  (violates AC-M2 "never the fleet token" + SC-BUILD-1 scope pin); it is the exact
  posture this initiative retires.
- *Wait for the SDK's "future" business-scoped API* — REJECTED: absent at the pin;
  blocks the build. Watch-register: when a future `autom8y-auth` ships the
  business-scoped exchange, the minter can be reduced to an SDK call (DRY follow-on).

**Consequences.** ~1 small new auth module + a typed mint-exception hierarchy. The
minter is the single site that constructs the exchange request, so SC-BUILD-1 (scope)
and SC-BUILD-4 (creds) are enforced in one place and asserted by the canary.

---

## D4 — Per-business token isolation via a per-business `AuthProvider` (anti-IDOR)

**Status:** accepted

**Context.** `DataServiceClient` injects auth via
`_get_auth_token() -> auth_provider.get_secret()` set as `Authorization: Bearer` per
request (`client.py:104-132,415-472` @ b9648de4). The data leads endpoint's tenant is
the JWT `business_id`, which DOMINATES the client `office_phone` param
(`data_service.py:1009` @ dd4566e5, SC-BUILD-3).

**Decision.** One mint -> one `PerBusinessTokenProvider(token)` (impl `AuthProvider`)
-> one leads `DataServiceClient` per business. Tokens are never reused across tenants.
The consumer MUST NOT assume its `office_phone` controls the served tenant; correctness
is by construction because the SAME `Business` supplies both `company_id` (-> token
business_id) and `office_phone` (-> read).

**Alternatives considered.**
- *Mutate the shared client's `Authorization` header per business* — REJECTED:
  concurrency race under the parallel offer loop (`max_concurrency=5`) and an IDOR
  hazard (a stale header could read tenant B with tenant A's token).

**Consequences.** A per-business `DataServiceClient` is heavier (circuit breaker, cache)
but isolation is the security-correct choice (EC-6). A `data_client_factory` injection
seam keeps the orchestrator testable and lets the canary substitute a mock client.

---

## D5 — 4-class emitted skip taxonomy + a FATAL-misconfig carve-out

**Status:** accepted

**Context.** WS-SKIP binds four classes that must EMIT (log+metric+count), never
silent-drop, never fleet-fallback. The verified loci: 404 AUTH-TEB-005 (R8), 429
AUTH-TEB-006 (R9), 409 DATA-CONFLICT-002 (R17), inactive/empty.

**Decision.** Map exactly: `resolution_miss` (404 + company_id absent/null, with
distinct sub-reasons per EC-1), `collision_conflict` (409, fail-closed),
`inactive_or_empty`, `mint_unavailable` (429/5xx after retry, honor Retry-After).
ADD a carve-out: `401 AUTH-TEB-001` (bad delegator creds) and `403 AUTH-TEB-003`
(delegator lacks data:read) are delegator-level MISCONFIGURATIONS that manifest
identically for every business — they raise-and-halt the run rather than masquerade as
75 `resolution_miss` skips (honest-propagation, mirroring R15).

**Alternatives considered.**
- *Treat 401/403 as `resolution_miss`* — REJECTED: would hide a total
  delegator-credential failure as a fleet-wide "miss", defeating the skip-signal's
  purpose (a misconfigured run would look like "every business legitimately refused").

**Consequences (honest design surface).** In the merged contract the 409 forward
collision guard (`resolve_guid_or_raise`, R17) is NOT on the JWT-scoped leads read path
(`get_lead_details` uses `tenant_office_phone`, R16) and exchange-business returns 404
(not 409). So `collision_conflict` is **defensively handled** but not primary-path-
reachable; retained per the binding WS-SKIP taxonomy and for contract-fidelity (the
data binding-verify endpoint #206 can emit it). This is a refinement, not a
contradiction with the contract.

---

## Acid Test

In 18 months: the consumer derives a stable, locally-held identity (`company_id`==guid)
through the SAME pinned transform the producer uses, mints a single-tenant token bound
to `business_id` behind the merged oracle seal, and reads leads on a JWT-dominated
tenant key — with every refusal emitted, never silently dropped, never falling back to
the fleet token it exists to retire. The two-sided discriminating canary (RED
cross-tenant input correctly refused + no mint; GREEN owned passes; TEETH proves
non-vacuity) makes the claim falsifiable. The one structural risk — the ebid value-space
coupling to auth-mysql-sync — is contained by the pinned transform (D2), not by
re-derivation. This will look obviously right.
