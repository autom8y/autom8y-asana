---
type: review
status: accepted
---

# DOSSIER — SEC-002: RE-2 grant-chain trace + CF-1 widening

```yaml
artifact: DOSSIER-sec002-re2-grant-chain-2026-08-14
sprint: SEC-002
initiative: chain-of-custody-closure
phase: Phase 2
session: coc-phase-2
authored: 2026-08-14
status: COMPLETE-AS-SCOPED
rung: STRUCTURALLY-VERIFIED (static own-hands file:line; NO runtime probe)
rung_ceiling_rationale: >-
  Every hop in LEG A/B/C/D is anchored to a read file:line in a working tree
  this agent read directly. NO hop was confirmed against running infrastructure:
  no OpenFGA tuple was queried, no token was minted or decoded, no deployed
  image digest was checked, no terraform state was read. The chain is proven
  AS DECLARED IN CODE, not AS RUNNING IN PRODUCTION. REALIZED-MECHANISM is
  therefore NOT claimed and MUST NOT be inferred from this artifact.
self_assessment_cap: MODERATE
seat: >-
  dependency-analyst (arch rite), substituted for the phantom security bench
  per pythia seating ruling. threat-modeler STRIDE-lite duty FOLDED into this
  charge (see §6). penetration-tester DROPPED-BY-SCOPE — this sprint is
  read-only static tracing; an active-exploitation seat would breach its own
  fence.
fences_observed:
  - READ-ONLY across all repos; zero writes outside this file; zero git verbs
  - CR-5 honoured — no credential values, no secret files, no token mint/decode,
    no AWS/Asana/OpenFGA API calls
  - R-2 honoured — F-001 severity NOT re-graded here; §7 carries a labelled
    RECOMMENDATION only
  - CF-7 NOT widened into
```

---

## §0 — Staleness receipts (read BEFORE any claim below)

| Repo | Local HEAD | Local branch | Dirty files | origin/main SHA (gh api) | Divergence |
|---|---|---|---|---|---|
| `/Users/tomtenuta/Code/a8/a8/repos/autom8y` | `2159f967f9b18cddf2eea88f7eb7e7acc804ec85` | **`fix/wss-wildcard-scope-bypass-closure`** | 11 | `868ead943bf4cf44b9f44458e7bf4d9574672fb5` | **NOT main** |
| `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana` | `b76424cca02a67d02cc90744ddbe7bc88a01cd6d` | `main` | 129 | `d75601531edd220e693ce279f10b2a9b1d171f20` | behind/ahead of origin |
| `/Users/tomtenuta/Code/a8/a8/repos/autom8y-hermes` | `ccdcb9a88c38366f1f6753973af65286fa849858` | `autom8y` | 7 | not queried (out of charge) | — |

**STALENESS HAZARD SH-1 (load-bearing).** Every `autom8y`-repo anchor in this
dossier was read from a working tree checked out on
`fix/wss-wildcard-scope-bypass-closure`, **not** `main`, and **not** at
`origin/main` (`868ead94`). The branch name itself references a *scope-bypass
closure* — i.e. the surface under trace may be mid-remediation on this branch
in a shape that differs from what is deployed. No diff was taken (git verbs are
fenced). **Every LEG A/B/D anchor below carries this hazard.** Discharge method:
re-run this trace against `origin/main` at `868ead94` and diff the anchor set.

**STALENESS HAZARD SH-2 (SDK version split).** Two different `autom8y-auth` SDK
copies exist and they do **not** share line numbers:

- monorepo source: `sdks/python/autom8y-auth/pyproject.toml:7` → `version = "4.2.0"`
- asana's installed runtime: `.venv/.../autom8y_auth-4.1.0.dist-info` → **4.1.0**
- asana's declared floor: `autom8y-asana/pyproject.toml:68` → `autom8y-auth[observability]>=3.3.0` (no upper pin)

Phase-1's SDK anchors (`claims.py:134,175`; `middleware.py:246-300`;
`client.py:288` F-004; `client.py:L476-489` CF-6) resolve against the **installed
4.1.0**. This dossier gives BOTH coordinate systems where they diverge, marked
`[4.1.0-installed]` and `[4.2.0-source]`. Consumers must not mix them.

---

## §1 — Determinant re-confirmed own-hands (not inherited)

Not re-litigated, but re-read at this session rather than carried on trust.

| Fact | Anchor | Confidence |
|---|---|---|
| `ace` is registry-declared, `business_scoped: false` | `autom8y/services/auth/service-accounts.yaml:42-44` | HIGH (explicit declaration) |
| `ace` exemption block: `category: ai_agent`, `approved_by: tomtenuta`, `approved_date: "2026-04-11"`, `tension_inherited: "TENSION-005 (mitigated via D5 — 5-min TTL)"` | `service-accounts.yaml:56-64` | HIGH |
| `ace` scopes read-only: `data:read analytics:read scheduling:read sms:read ads:read` | `service-accounts.yaml:46-51` | HIGH |
| `iris` is registry-declared, `business_scoped: false` | `service-accounts.yaml:249-251` | HIGH |
| `iris` exemption block: `category: ai_agent`, `approved_by: tomtenuta`, `approved_date: "2026-04-13"`, same TENSION-005/D5 line | `service-accounts.yaml:264-272` | HIGH |
| `iris` scopes read-only: `scheduling:read data:read analytics:read sms:read ads:read` — **NO asana scope** | `service-accounts.yaml:253-258` | HIGH |

**NEW COUNTED FACT NF-1 (not in Phase 1).** The registry contains **18** service
accounts, of which **18** are `business_scoped: false` and **0** are
`business_scoped: true`.

```
grep -c '^  - id:'                 services/auth/service-accounts.yaml  -> 18
grep -c 'business_scoped: false'   services/auth/service-accounts.yaml  -> 18
grep -c 'business_scoped: true'    services/auth/service-accounts.yaml  -> 0
```

The exemption is **100% of the registry population**, not an exception carved
out of a business-scoped norm. The root module's own header comment still
describes the land-time state — `terraform/services/service-accounts/main.tf:18-20`
reads "12 entries, all business_scoped:false at land-time → 12 bypass tuples,
0 can_issue_service_token tuples" — the population has since grown 12 → 18
without the comment being updated. `ace` and `iris` are 2 of 18 identically
situated identities. This is recorded as a counted fact for the severity
question in §7; it is **not** a severity judgement.

---

## §2 — LEG A: registry → OpenFGA tuples

### VERDICT: CHAIN CONFIRMED. **NO filter, no condition, no allowlist** stands between Bucket-1 membership and the bypass tuple. Confidence HIGH (explicit declaration, two independent emitters).

### A.1 — The terraform emitter

`terraform/modules/service-accounts/main.tf` is the module the registry header
names. Registry header, `service-accounts.yaml:11-12`:

> `#   2. Consumed by the 'modules/service-accounts/' terraform module to`
> `#      emit OpenFGA tuples (can_issue_service_token / bypass_scope_enforcement).`

The tuple set is computed at `main.tf:32-36`:

```hcl
  # One bypass tuple per exempt SA.
  bypass_tuples = [
    for sa in local.service_accounts : {
      sa_id = sa.id
    } if !sa.business_scoped
  ]
```

**The predicate is `if !sa.business_scoped` and nothing else.** There is no
inspection of the `exemption` block, no check of `category`, no check of
`approved_by`, no check of `approved_date` freshness, no environment gate, no
scope-shape gate, no allowlist. A registry entry with `business_scoped: false`
and a *missing or malformed* exemption block would still produce a bypass tuple
at this layer (schema enforcement is upstream and out-of-band — pre-commit +
a terraform-plan CI job per `service-accounts.yaml:14-16` — not a condition in
the emitter).

Emission resource, `main.tf:80-95`:

```hcl
resource "openfga_relationship_tuple" "bypass_scope_enforcement" {
  for_each = { for sa in local.bypass_tuples : sa.sa_id => sa }
  ...
  user     = "service_account:${each.value.sa_id}"
  relation = "bypass_scope_enforcement"
  object   = "organization:__bypass__"
```

The only precondition in the module is a duplicate-id check
(`main.tf:45-52`), which is a hygiene assertion, not an authorization filter.

Caller: `terraform/services/service-accounts/main.tf:31-48` — exactly one
instantiation, passing `var.yaml_path` (validated only to *end in*
`service-accounts.yaml`, `modules/service-accounts/variables.tf:14-17`).

**Answer to the charge question:** `ace`/`iris` membership in Bucket 1
**mechanically produces** the bypass tuple. There is nothing between.

### A.2 — The SECOND emitter (not identified in Phase 1)

The terraform module is **not** the only writer of this tuple. The auth service
writes the same tuple itself, at boot.

- `services/auth/autom8y_auth_server/services/sa_reconciler.py:794-796`:

```python
    for entry in entries:
        if not entry.business_scoped:
            bypass_tuples.append(_build_bypass_tuple(entry.yaml_id))
```

- `sa_reconciler.py:723-739` (`_build_bypass_tuple`) states the shape is
  "byte-identical to `terraform/modules/service-accounts/main.tf:80-95`" and
  emits `user=service_account:{yaml_id}`, `relation=bypass_scope_enforcement`,
  `object=_BYPASS_SENTINEL_OBJECT`.
- Invocation: `services/auth/autom8y_auth_server/boot_reconciler.py:89-91` imports
  `reconcile_service_account_fga_tuples`; `boot_reconciler.py:139` gates the
  OpenFGA leg on `settings.OPENFGA_STORE_ID` being set.

**Same single predicate (`if not entry.business_scoped`), same absence of any
filter.** This matters for chain robustness: the LEG-A hop does **not** depend
on terraform having been applied. Even where the terraform plan cannot run —
and `.github/workflows/terraform-plan-reusable.yml:84-86` explicitly warns
"until then the plan will fail with 'No value for required variable'" pending
per-environment `TF_VAR_openfga_*` / `OPENFGA_API_TOKEN` population — the auth
service re-asserts the bypass tuples on every boot. **The chain has a redundant
emitter; removing the terraform tuple does not remove the grant.**

### A.3 — LEG A residual

- **UV-P-A1**: whether the bypass tuples are *presently resident* in the live
  OpenFGA store for `ace` and `iris`.
  `[UV-P: organization:__bypass__#bypass_scope_enforcement@service_account:{ace,iris} tuples exist in the production OpenFGA store | METHOD: deferred-to-security-rite OpenFGA read probe or terraform state read | REASON: CR-5 fence forbids API calls from this seat; both emitters are declarative-only evidence]`
- **UV-P-A2**: whether the terraform root module has ever been successfully
  applied in production (the plan-workflow comment implies prerequisites may be
  unmet). Does **not** break the chain — A.2 is the load-bearing emitter — but
  bears on drift-detection posture.

---

## §3 — LEG B: tuples → issuance-time behaviour

### VERDICT: CHAIN CONFIRMED. `bypass_scope_enforcement=True` lands in the issued claims. D5 300s TTL CONFIRMED at the issuance layer. Confidence HIGH.

### B.1 — Eligibility derives directly from the registry field

`services/auth/autom8y_auth_server/services/token_service_resolution.py:133-140`:

```python
        return TokenIssuanceResolution(
            effective_scopes=list(entry.scopes),
            business_scoped=entry.business_scoped,
            bypass_eligible=(entry.business_scoped is False),
            resolution_source=SAResolutionSource.YAML_REGISTRY,
        )
```

`bypass_eligible` is a direct restatement of the registry boolean —
`token_service_resolution.py:137`. The module docstring at
`token_service_resolution.py:38-40` states the invariant: "`bypass_eligible` is
`True` ONLY on the YAML path AND ONLY [when business_scoped is false] … no
other code path that can produce `bypass_eligible=True`".

Note also `token_service_resolution.py:133` — `effective_scopes` come from the
**YAML entry**, not the DB row. The registry is the authoritative scope source
for catalogued SAs (corroborated by `service-accounts.yaml:7-9`: "Scopes here
are AUTHORITATIVE for YAML-catalogued SA token issuance"). This is load-bearing
for LEG C.

### B.2 — The runtime FGA probe

`services/auth/autom8y_auth_server/services/token_service.py:614-640`:

```python
    if resolution.bypass_eligible:
        ...
        bypass_granted = await _check_openfga(
            openfga_check,
            user_id=f"service_account:{sa.yaml_id}",
            relation="bypass_scope_enforcement",
            object_type="organization",
            object_id="__bypass__",
        )
        if bypass_granted:
            return _finalise_exempt_issuance(...)
```

The FGA probe (`token_service.py:627-633`) is a **conjunctive second gate**:
registry-eligibility AND tuple-presence are both required. The in-code comment
at `token_service.py:617-622` names this "the runtime enforcement point for
exemption revocation". This is a genuine control and should be credited as
such — it is the one place where removing the tuple actually revokes the
bypass mid-flight. Its force is nonetheless limited by LEG A.2: the auth
service's own boot reconciler re-writes the tuple it would need to be missing.

### B.3 — The claim lands

`token_service.py:776-785` (`_finalise_exempt_issuance`):

```python
    payload: dict[str, Any] = {
        "sub": str(sa.id),
        "client_id": sa.client_id,
        "service_account_id": sa.yaml_id,
        "bypass_scope_enforcement": True,
        "permissions": granted_scopes,
        "scope": scope_string,
        "scopes": list(granted_scopes),
        # business_id deliberately OMITTED per ADR-04 §4.2.
    }
```

- `bypass_scope_enforcement: True` — **`token_service.py:780`**. This is the
  single strongest anchor for LEG B.
- `business_id` **omitted entirely** — `token_service.py:784` (comment), and by
  construction (absent from the dict literal).
- Signed at `token_service.py:789-795`, `ttl_seconds=settings.EXEMPT_SA_TOKEN_TTL_SECONDS`
  (`:791`), `audience="https://api.autom8y.io"` (`:794`).

Contrast the business-scoped sibling `_finalise_business_issuance`, which stamps
`"bypass_scope_enforcement": False` at `token_service.py:843` and carries
`business_id` at `:842`.

### B.4 — D5 5-min TTL: CONFIRMED at the issuance layer

`services/auth/autom8y_auth_server/app/config.py:83`:

```python
    EXEMPT_SA_TOKEN_TTL_SECONDS: int = 300  # 5 min (ADR-04 §4.1 D5)
```

vs. `config.py:76` `SERVICE_TOKEN_TTL_SECONDS: int = 1800  # 30 min (FR-038)`.

**300s confirmed for the exempt path.** The registry's
`tension_inherited: "TENSION-005 (mitigated via D5 — 5-min TTL)"` claim
(`service-accounts.yaml:62`, `:271`) is therefore **substantiated at the
issuance layer** for tokens minted via `_finalise_exempt_issuance`.

Two caveats that bound the mitigation:

1. It is a **pydantic-settings default**, environment-overridable. No code-level
   floor or assertion prevents an env var raising it. `[UV-P: EXEMPT_SA_TOKEN_TTL_SECONDS is 300 in the deployed production task definition | METHOD: deferred-to-security-rite ECS task-definition read | REASON: config.py:83 is a default, not a floor; deployed env not readable from this seat under CR-5]`
2. The 300s TTL applies **only** to the exempt SA species. It does **not** apply
   to the OAuth-client species (§4.2) — that path is 1800s.

### B.5 — `check_revocation` from the auth side (F-004 corroboration)

F-004's claim (SDK `client.py:288` defaults False) is **corroborated** — the
default is `False` in both SDK copies, at different line numbers:

- `[4.1.0-installed]` `.venv/.../autom8y_auth/client.py:185` — `check_revocation: bool = False,` on `validate_token`
- `[4.2.0-source]` `sdks/python/autom8y-auth/src/autom8y_auth/client.py:193, :268, :306` — default `False` on `validate_token`, `validate_user_token`, `validate_service_token`
- `[4.2.0-source]` `client.py:210-213` — "Defaults to `False` — when `False` the behavior is byte-identical to 4.0.0 (JWKS+expiry+audience only; NO introspection HTTP call is made). … The 5.0.0 follow-on flips this default to `True`."

**Consequence for the chain:** a 300s exempt token is, in the default
configuration, **not revocation-checked by consumers**. The auth service *does*
expose the machinery — `routers/tokens.py:260-292` documents an
`/tokens/introspect` endpoint with a fail-CLOSED SA leg
(`tokens.py:282-287`) — but nothing on the asana consuming side opts in. The
300s TTL is therefore the **only** effective revocation bound for an
already-issued exempt token: within its 5-minute window it is unrevokable in
practice. This is the correct reading of D5 — TTL as revocation substitute, not
TTL as defence-in-depth atop revocation.

### B.6 — Mint-time authentication on the exempt path

`routers/tokens.py:673-722` — `POST /tokens/exchange-business`. The route takes
**no auth dependency**. Credentials are `client_id` + `client_secret`, resolved
from either an HTTP Basic header or the JSON body (`tokens.py:716-722`), verified
by SHA-256 comparison (Step 2, `tokens.py:697`). Rate limiting is per-IP and
per-`client_id` (`tokens.py:696`). **Possession of the client secret is the
entire mint-time control.** There is no mTLS, no IP allowlist, no additional
factor at this layer.

---

## §4 — LEG C: CF-1 widening — which substrate governs which token species

### VERDICT: RESOLVED, and the resolution INVERTS the framing of the charge. The two substrates do disagree — but the OAuth-client `asana:read` grant is **INERT** for the token species `iris` actually uses, and the SA-registry exemption **does NOT extend** to the OAuth-client population. Confidence HIGH on the mechanism; MEDIUM on the deployment-reality of which path runs. See C.5.

### C.1 — The two substrates, side by side

| | SA-registry substrate | OAuth-client substrate |
|---|---|---|
| Identity name | `iris` / `iris-service` | `autom8y-hermes` |
| Declaration | `service-accounts.yaml:249-281` | `terraform/services/auth/main.tf:1575-1597` |
| Scopes | `scheduling:read data:read analytics:read sms:read ads:read` (`:253-258`) — **no asana** | `"data:read asana:read"` (`main.tf:1581`) |
| Mint endpoint | `POST /tokens/exchange-business` (`tokens.py:673-684`) | `POST` client_credentials (`oauth.py`, `:1620-1638`) |
| Claim: `bypass_scope_enforcement` | **`True`** (`token_service.py:780`) | **absent** (`oauth.py:1627-1631`) |
| Claim: `business_id` | omitted (`token_service.py:784`) | absent (`oauth.py:1627-1631`) |
| Claim: `permissions` | present (`token_service.py:781`) | **absent** |
| Claim: `service_account_id` | present (`token_service.py:779`) | **absent** |
| TTL | **300s** (`config.py:83`) | **1800s** (`oauth.py:1634`, `config.py:76`) |
| Audience | `https://api.autom8y.io` (`token_service.py:794`) | `https://api.autom8y.io` (`oauth.py:1637`) |

### C.2 — OAuth-client tokens are a genuinely DIFFERENT species

`services/auth/autom8y_auth_server/routers/oauth.py:1620-1638`:

```python
    # ----- Step 8 — Issue JWT via create_access_token() DIRECT -----------
    # D-0 §6.5 / D-1 §9.5 SUPERSESSION ADDENDUM: this is the BYPASS.
    # Payload carries ONLY {sub, client_id, scope}. NO business_id,
    # NO service_account_id, NO bypass_scope_enforcement, NO permissions,
    # NO roles. create_access_token auto-injects iss/iat/exp/jti/token_type;
    # audience is the fleet platform aud "https://api.autom8y.io".
    scope_string = " ".join(granted_scopes)
    payload: dict[str, Any] = {
        "sub": client.client_id,
        "client_id": client.client_id,
        "scope": scope_string,
    }
```

This is corroborated by a *verbatim-binding* constitutional clause reproduced
in the tfvars at `terraform/services/auth/oauth-clients.tfvars:29-32`:

> "JWT claim shape is dichotomous. OAuthClient-minted JWTs MUST NOT carry
> business_id, service_account_id, bypass_scope_enforcement, or permissions
> claims …"

and by the write-side invariant at `routers/admin.py:488-490`.

**Answer to the charge question:** the SA-registry exemption does **NOT** extend
to the OAuth-client population. There is no code path by which an
`oauth_clients` row acquires `bypass_scope_enforcement`. The two substrates are
disjoint at the claim layer. Scope enforcement for the OAuth species is
`requested ∩ client.allowed_scopes` at `oauth.py:1600-1618`.

Corollary, and a genuine gap: an OAuth-client token carries **neither**
`bypass_scope_enforcement` **nor** `business_id`. Under the middleware
precedence (§5) it therefore falls to **Step 3 → reject 400 AUTH-TEB-004**. An
OAuth-client token cannot pass a `require_business_scope=True` middleware at
all. `[UV-P: no OAuth-client-minted token presently transits a require_business_scope=True satellite route in production | METHOD: deferred-to-security-rite log query on AUTH-TEB-004 by client_id | REASON: static reads cannot establish live traffic shape]`

### C.3 — THE DECISIVE FINDING: `iris` does not use the OAuth path

The consumer named by the terraform module's own authority chain
(`terraform/services/auth/main.tf:1563`) is
`autom8y-hermes/plugins/autom8y/auth/service_jwt.py`. That file's declared
protocol, `service_jwt.py:22-23`:

> `  - protocol:           OAuth2 client_credentials grant (RFC 6749 §4.4)`
> `                        wrapped as POST /tokens/exchange-business`

and its actual request, `service_jwt.py:231-235`:

```python
        exchange_url = f"{self._auth_url}/tokens/exchange-business"
        payload = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
```

**`iris`/hermes posts its OAuth client credentials to the SERVICE-ACCOUNT
endpoint, with no `business_id`.** It never calls the OAuth client_credentials
token endpoint. Its own docstring at `service_jwt.py:34-35` states the expected
result: "Returns `{"access_token": "<jwt>", ...}` with a **300s TTL for exempt
service accounts**" — i.e. the consumer *knows* it is on the exempt SA path.

The consequence is precise:

1. The credential pair minted by `module "oauth_clients_hermes"` is used as the
   **credential**, but the **token species** minted is the exempt-SA token.
2. Therefore `iris`'s live token carries `bypass_scope_enforcement: True`, no
   `business_id`, a 300s TTL, and `permissions` = the **SA-registry** scope set
   (`token_service_resolution.py:133`), i.e. `scheduling:read data:read
   analytics:read sms:read ads:read`.
3. **The `asana:read` grant at `main.tf:1581` never reaches a live token.** It
   governs `oauth_clients.allowed_scopes` for an endpoint hermes does not call.
   The provider's own docstring at `service_jwt.py:24-27` advertises scope
   `"data:read asana:read"` — **that advertisement is false for the token it
   actually obtains.**

**Which substrate governs which token species — the answer:**
the **mint endpoint** selects the substrate, not the identity. `/tokens/exchange-business`
→ SA-registry governs (scopes, bypass, 300s TTL). OAuth client_credentials
endpoint → `oauth_clients.allowed_scopes` governs (scopes only; no bypass,
1800s TTL). `iris` is dual-registered and calls the former, so the SA registry
governs it end-to-end and the OAuth registration is credential-material only.

### C.4 — CF-1 widening: the population count

Exhaustive grep for `asana:read|asana:write|asana:*` across `.tf`, `.tfvars`,
`.yaml`, `.yml`, `.py`, `.json` in the `autom8y` repo (excluding `.know/`,
`.ledge/`, `node_modules`) returns **four** hits, of which **one** is a live grant:

| Hit | Anchor | Kind |
|---|---|---|
| `scopes = "data:read asana:read"` | `terraform/services/auth/main.tf:1581` | **LIVE GRANT** (module `oauth_clients_hermes`) |
| comment describing the above | `terraform/services/auth/main.tf:1572` | comment |
| `CANONICAL_SCOPES = "data:read asana:read"` | `services/auth/tests/test_autom8y_hermes_registration.py:72` | test constant |
| `scopes=("asana:read", "asana:write")` | `services/auth/tests/test_token_service_exchange_business.py:745` | test fixture |

**CF-1 widening population:**

- OAuth-client identities carrying any `asana:*` scope: **1** (`autom8y-hermes`)
- SA-registry identities carrying any `asana:*` scope: **0** (of 18)
- Terraform-declared OAuth clients total: **2** (`autom8-legacy-monolith` =
  `data:read sms:write` at `main.tf:1533`; `autom8y-hermes` = `data:read asana:read`
  at `main.tf:1581`)
- Identities appearing in **both** substrates under **different names with
  divergent scope sets**: **1** (`iris` ≡ `autom8y-hermes`)

**So the "second uncounted population" is a population of exactly one — and it
is uncounted in the *opposite* direction from the CF-1 hypothesis.** The
hypothesis was that the OAuth substrate silently widens `iris` with an asana
grant the SA registry does not show. The trace shows the reverse: the asana
grant is real in the OAuth substrate but **inert**, because hermes mints on the
SA path where the SA registry's asana-free scope set is authoritative.

**But — and this is the sting — the inertness does not protect asana.** See §5.
`require_service_claims` performs **no scope check**, so the absence of
`asana:read` from `iris`'s live token has **no effect** on `iris`'s ability to
call asana S2S routes. The scope divergence is a governance-integrity defect
(two substrates disagree about one identity, and a shipped docstring asserts a
scope set the runtime token lacks), not an access-control differential.

### C.5 — LEG C residuals

- **UV-P-C1** (population bound): the terraform count is a **lower bound only**.
  `oauth_clients` rows are DB-resident and the canonical write boundary is the
  admin endpoint (`routers/admin.py:474-486` — "this endpoint is the CANONICAL
  DB-write boundary for `oauth_clients` row creation"), which terraform *wraps*
  rather than owns. Rows created via `provision_oauth_client.py` or the admin
  endpoint directly would not appear in any `.tf` file.
  `[UV-P: the complete set of oauth_clients rows carrying an asana:* allowed_scope | METHOD: deferred-to-security-rite read of the auth Postgres oauth_clients table | REASON: CR-5 forbids DB/API access from this seat; terraform is not the authoritative registry for this population]`
- **UV-P-C2** (deployment reality): whether the deployed hermes/iris runtime is
  the `service_jwt.py` provider traced here, at the `ccdcb9a8` tree state.
  `[UV-P: production iris mints via POST /tokens/exchange-business | METHOD: deferred-to-security-rite auth-service log query on tokens_exchange_business_issued where service_account_id=iris | REASON: static read of a non-main branch tree cannot establish deployed behaviour]`
- **UV-P-C3**: whether any *other* consumer calls the OAuth client_credentials
  endpoint with the hermes credentials (which would produce the 1800s no-bypass
  species). Not found in the hermes tree; not exhaustively searched fleet-wide.

---

## §5 — LEG D: CF-6 remaining half — AUDIENCE + MINTABILITY

### VERDICT: SPLIT. **Audience: CONFIRMED** — `agent_access` tokens are minted with the exact fleet audience asana requires. **Reclassification: CONFIRMED** — the SDK does route them to `ServiceClaims`. **Clearing `require_service_claims`: REFUTED — but by ACCIDENT, not by design.** A type mismatch on the `scope` claim breaks the parse. Confidence HIGH on audience/reclassification (explicit declaration); MEDIUM on the parse-failure (static inference over pydantic coercion semantics — see UV-P-D1).

### D.1 — Audience: CONFIRMED

`services/auth/autom8y_auth_server/services/token_service.py:403-440`
(`create_agent_token`):

```python
    settings = get_settings()
    effective_audience = audience or "https://api.autom8y.io"
    ...
    token = create_access_token(
        payload=payload,
        ttl_seconds=settings.AGENT_TOKEN_TTL_SECONDS,
        token_type="agent_access",
        issuer=settings.TOKEN_ISSUER,
        audience=effective_audience,
    )
```

- Default audience `https://api.autom8y.io` — **`token_service.py:420`**.
- The asana S2S validator demands exactly that string:
  `autom8y-asana/src/autom8_asana/auth/jwt_validator.py:83` —
  `claims = await client.validate_service_token(token, audience="https://api.autom8y.io")`.
- The only caller (`routers/tokens.py:480-487`) passes **no** `audience`
  argument, so the default fires.

**An `agent_access` token is minted with the fleet audience the asana S2S routes
require. The audience is not a barrier.**

### D.2 — Reclassification: CONFIRMED (Phase-1 structural half, extended)

`agent_access` payload shape (`token_service.py:421-431`): `sub`, `business_id`,
`email`, `act`, `scope`, `delegation_session_id`, plus injected `iss/iat/exp/jti/token_type/aud`.
**No `roles` claim.**

`[4.1.0-installed]` `.venv/.../autom8y_auth/_detection.py:25-34`:

```python
    has_business_id = "business_id" in claims
    has_roles = "roles" in claims
    has_token_type = "token_type" in claims

    if has_business_id and has_roles and has_token_type:
        return TokenType.USER

    # Service tokens (both APIKey and ServiceAccount) lack roles
    return TokenType.SERVICE
```

`business_id` ✓, `roles` ✗ → the USER conjunct fails → **falls through to
`TokenType.SERVICE` at `_detection.py:34`** `[4.2.0-source: _detection.py:43]`.

Then `[4.1.0-installed]` `client.py:463-473`:

```python
        if token_type == TokenType.USER:
            if self._settings.require_access_token_type:
                claim_token_type = claims_dict.get("token_type")
                if claim_token_type != "user_access":
                    raise InvalidTokenTypeError(...)
            return UserClaims.model_validate(claims_dict)
        else:
            return ServiceClaims.model_validate(claims_dict)
```

**The USER branch has a `token_type` guard; the SERVICE branch has NONE.** There
is no `claim_token_type != "service"` check on the else-arm. This is the exact
asymmetry CF-6 names, and it is confirmed in the version asana actually runs
(`client.py:473`) `[4.2.0-source: client.py:489-490]`.

### D.3 — Mintability: gated, but the gate is a delegator not a bypass

`routers/tokens.py:397-498` (`agent_token_exchange`):

- Caller must present a **user_access** token — `Depends(require_human_token)`
  at `tokens.py:409`; `tokens.py:413-415` states the single-hop constraint
  ("Agent tokens (token_type: agent_access) are rejected").
- `business_id` is taken from the caller's own JWT, not the request
  (`tokens.py:429`; schema comment `schemas/agent.py:58`).
- PT-007 agent-registration check at `tokens.py:441-452` — **conditional**: it
  fires only `if body.agent_id`. When `agent_id` is absent *and*
  `settings.REQUIRE_AGENT_ID` is off, the else-arm at `tokens.py:453-461`
  merely **audit-logs a warning** and proceeds to mint. So the registration gate
  is feature-flag-dependent, not structural.
- Scope downscoping is enforced: `validate_delegator_scope` at
  `tokens.py:465-475` rejects the whole request if any requested scope exceeds
  the delegator's permissions.

**Mintability verdict:** an `agent_access` token with fleet audience is mintable
by **any authenticated human user**, bounded to that user's own `business_id`
and that user's own scope set. It is not mintable by an unauthenticated party,
and it cannot escalate scope. `[UV-P: REQUIRE_AGENT_ID is enabled in production | METHOD: deferred-to-security-rite ECS task-definition read | REASON: config default not read; CR-5 forbids deployed-env access]`

### D.4 — Would it clear `require_service_claims`? — REFUTED, accidentally

`autom8y-asana/src/autom8_asana/api/routes/internal.py:83-172` is confirmed
logs-only as Phase 1 found: it rejects PATs (`internal.py:106-118`), calls
`validate_service_token` (`internal.py:121`), and then **logs** the caller and
scope (`internal.py:146-153`) before returning. **No business_id check, no
bypass check, no scope/permission assertion.** So the route's own logic imposes
no barrier.

The barrier, such as it is, sits in the pydantic model. `ServiceClaims.scope` is
typed `str | None`:

`[4.1.0-installed]` `.venv/.../autom8y_auth/claims.py:164`
`[4.2.0-source]` `sdks/python/autom8y-auth/src/autom8y_auth/claims.py:187`:

```python
    scope: str | None = Field(default=None, description="RFC 6749 space-delimited scope")
```

But `create_agent_token` stamps `scope` as a **list**:

- `token_service.py:429` — `"scope": requested_scope,`
- `token_service.py:409` — `requested_scope: list[str]`
- `schemas/agent.py:68` — `requested_scope: list[str] = Field(default_factory=list, max_length=14)`

So the claim decodes to a JSON array (possibly `[]`), never a string.
`ServiceClaims.model_validate` on `str | None` with a `list` value raises
`pydantic.ValidationError` under pydantic v2 lax coercion (list is not a `str`
source type). Model config is `{"extra": "ignore"}` only — no strict/lax
override, no custom validator on `scope`
(`[4.2.0-source] claims.py:162`; the only validator, `validate_scope_scopes_invariant`
at `claims.py:210-224`, is opt-in *after* construction and cannot rescue the parse).

Note further that this `ValidationError` is raised **outside** the SDK's
try/except (which covers only `MissingRequiredClaimError` and `PyJWTError`,
`[4.2.0-source] client.py:460-466`), so it propagates un-normalised — but
`internal.py:135-145`'s broad boundary catch converts it to `ApiAuthError` /
401 regardless.

**Verdict: an `agent_access` token would NOT clear `require_service_claims`** —
it fails at claims-model construction, before any authorization logic. **But the
mechanism that saves the boundary is a `list`-vs-`str` type accident in an
unrelated claim, not a designed control.** Nothing asserts `token_type ==
"service"` anywhere on the service arm. Were `create_agent_token` ever changed
to emit `scope` as a space-delimited string (which is the RFC-6749-correct
shape, and the shape both sibling minters already use —
`token_service.py:782`, `oauth.py:1630`), the `agent_access` token would parse
cleanly as `ServiceClaims`, carry `bypass_scope_enforcement=False` by
`BaseClaims` default (`[4.1.0-installed] claims.py:134`), carry a **truthy
`business_id`** from the delegator, clear the middleware at precedence Step 2
(§5.1), and clear `require_service_claims` outright. **CF-6 is one
type-normalisation commit away from live.**

`[UV-P-D1: pydantic v2 raises ValidationError rather than coercing a list into a 'str | None' field under the ServiceClaims model_config | METHOD: deferred-to-security-rite offline ServiceClaims.model_validate on a synthetic claims dict — no crypto, no live token, no network | REASON: static reading of pydantic coercion semantics; the pin is 'pydantic>=2.0.0' (sdks/python/autom8y-auth/pyproject.toml:29) with no upper bound, so behaviour is version-dependent and was not empirically exercised under the CR-5 read-only fence]`

`[UV-P-D2: no SDK test exercises the agent_access → ServiceClaims path | METHOD: deferred — grep of sdks/python/autom8y-auth/ for 'agent_access' returned ZERO matches (result_count: 0) | REASON: absence-of-test is evidence of an unguarded seam, not proof of behaviour; the seam is untested in either direction]`

---

## §6 — STRIDE-lite fold (threat-modeler duty)

Trust boundaries crossed by the traced chain, and the single control present at
each crossing. Anchored claims only; no speculative attack trees.

| # | Boundary crossed | Direction | Control at the crossing | Anchor | STRIDE class |
|---|---|---|---|---|---|
| TB-1 | Human governance → declarative registry | operator commits YAML | Schema gate (pre-commit + terraform-plan CI) requiring an `exemption` block on every `business_scoped: false` entry | `service-accounts.yaml:14-16`, `:28-31` | **Elevation of Privilege** — the gate validates *presence* of an exemption block, not its *merit*; `approved_by` is a free-text YAML string with no cryptographic binding |
| TB-2 | Registry → OpenFGA authz store (terraform arm) | IaC apply | **NONE beyond `if !sa.business_scoped`** + a duplicate-id precondition | `modules/service-accounts/main.tf:32-36`, `:45-52` | **Elevation of Privilege** — no filter between Bucket-1 membership and grant |
| TB-3 | Registry → OpenFGA authz store (runtime arm) | auth-service boot | **NONE beyond `if not entry.business_scoped`**; gated only on `OPENFGA_STORE_ID` being set | `sa_reconciler.py:794-796`, `boot_reconciler.py:139` | **Elevation of Privilege** + **Repudiation** — a service self-granting its own bypass tuples on boot means the IaC audit trail is not the sole grant record |
| TB-4 | Untrusted network → auth mint plane | `POST /tokens/exchange-business` | Client-secret SHA-256 comparison + per-IP/per-client_id rate limit. **No auth dependency on the route** | `tokens.py:684-690` (no `Depends` for authn), `:696-697`, `:716-722` | **Spoofing** — single-factor; secret possession is total |
| TB-5 | Registry classification → issued JWT claims | token issuance | **Conjunctive**: registry eligibility AND live FGA tuple probe. Genuine revocation point | `token_service.py:614`, `:627-633`, `:617-622` | **Elevation of Privilege** (mitigated) — but TB-3 re-writes the tuple this control depends on being absent |
| TB-6 | Issued token → time | token lifetime | **300s TTL** (exempt) vs 1800s (business/OAuth). Env-overridable default, not a floor | `config.py:83`, `:76`, `token_service.py:791` | **Elevation of Privilege** (mitigated) — this is D5, and it is the *only* effective bound given TB-7 |
| TB-7 | Issued token → revocation authority | consumer validation | **NONE by default.** `check_revocation=False`; asana never opts in. Machinery exists (`/tokens/introspect`, fail-CLOSED SA leg) but is unwired | `[4.1.0] client.py:185`; `[4.2.0] client.py:193/268/306`; `tokens.py:282-287`; grep of `autom8y-asana/src/` for `check_revocation` → **0 matches** | **Repudiation / Elevation of Privilege** — an exempt token is unrevokable within its 300s window |
| TB-8 | Fleet token → asana satellite (middleware layer) | HTTP request | `JWTAuthMiddleware(require_business_scope=True)` — JWKS signature + fleet-audience + business-scope precedence | `autom8y-asana/src/autom8_asana/api/main.py:445`; `[4.1.0] middleware.py:278-300` | **Elevation of Privilege** — precedence Step 1 is `bypass → allow`, so this control is *by design* inoperative for exempt tokens |
| TB-9 | Fleet token → asana satellite (route layer) | S2S route DI | `require_service_claims` — rejects PATs, validates JWT shape, **then logs and returns**. No scope check, no tenant check, no caller allowlist | `autom8y-asana/src/autom8_asana/api/routes/internal.py:83-172`, esp. `:146-153` | **Elevation of Privilege / Information Disclosure** — zero authorization at the route boundary |
| TB-10 | Token species → claims model | SDK parse | USER arm has a `token_type` guard; SERVICE arm has **none** | `[4.1.0] client.py:463-473`; `_detection.py:34` | **Spoofing** — species confusion; currently blocked only by the incidental `scope` type mismatch (§5.4) |
| TB-11 | Substrate ↔ substrate (SA registry vs OAuth clients) | governance | **NONE.** No cross-check reconciles the two declarations of the same logical identity | `service-accounts.yaml:253-258` vs `terraform/services/auth/main.tf:1581`; grep for any reconciler across both → none found | **Tampering / Repudiation** — divergent scope truth for one identity, with a shipped docstring (`service_jwt.py:24`) asserting the wrong one |

**Crossings with NO control whatsoever: TB-2, TB-3, TB-7, TB-9, TB-11** (five of
eleven). **Crossings where the control is present but by-design inoperative for
the traced identities: TB-8.**

---

## §7 — Severity input (R-2: report, do not re-grade)

### 7.1 — What the chain PROVES

The question posed: *does the completed chain show the business-scope middleware
gate (`JWTAuthMiddleware require_business_scope=True`, precedence
bypass→business_id→reject) is BYPASSED for ace/iris tokens end-to-end?*

**YES — plainly, and with an unbroken file:line chain at every hop.** Stated as
a closed loop:

1. `ace` and `iris` are `business_scoped: false` in the registry
   (`service-accounts.yaml:44`, `:251`).
2. That boolean alone — with no filter — emits
   `organization:__bypass__#bypass_scope_enforcement@service_account:{ace,iris}`,
   from **two** independent emitters (`modules/service-accounts/main.tf:35`;
   `sa_reconciler.py:795`).
3. That same boolean alone sets `bypass_eligible=True`
   (`token_service_resolution.py:137`).
4. Eligibility + tuple-presence route issuance to the exempt finaliser
   (`token_service.py:614`, `:634-635`).
5. The finaliser stamps `"bypass_scope_enforcement": True`
   (**`token_service.py:780`**) and **omits `business_id`**
   (`token_service.py:784`), at 300s (`config.py:83`) with fleet audience
   (`token_service.py:794`).
6. asana wires `require_business_scope=True` (`main.py:445`); the SDK middleware
   precedence checks bypass **FIRST** and returns `None` (= allow) —
   `[4.1.0] middleware.py:278-281`:
   ```python
        if getattr(claims, "bypass_scope_enforcement", False) is True:
            request.state.bypass_scope = True
            return None
   ```
7. At the route layer, `require_service_claims` adds **no** authorization —
   `internal.py:83-172` validates shape, logs, returns.

**The gate is not "circumvented"; it is *designed* to stand down for exactly
this claim, and the claim is produced unconditionally from a single YAML boolean
that is presently `false` for 18 of 18 registered service accounts (NF-1).**

Two aggravating facts the chain also proves, which were not in the Phase-1
picture:

- **AGG-1 — redundant emitter.** Removing the terraform tuple does not revoke
  the grant; the auth service re-writes it at boot (`sa_reconciler.py:795`,
  `boot_reconciler.py:139`). The one genuine runtime revocation control
  (`token_service.py:627-633`) depends on the absence of a tuple that a
  co-located subsystem restores.
- **AGG-2 — no revocation backstop.** `check_revocation` defaults `False` and
  asana never opts in (grep of `autom8y-asana/src/` → 0 matches). The 300s TTL
  is therefore not defence-in-depth atop revocation; it is the **sole** bound.

One mitigating fact the chain also proves:

- **MIT-1 — D5 is real.** The 5-minute TTL claimed in both exemption blocks is
  substantiated at the issuance layer (`config.py:83`, `token_service.py:791`).
  Both SAs' registry scope sets are read-only (`service-accounts.yaml:46-51`,
  `:253-258`), and both are `authorized_organizations: []`. This is a genuine
  blast-radius bound and should be credited.

### 7.2 — What stays UV-P (must not be reported as proven)

| ID | Open question |
|---|---|
| UV-P-A1 | Bypass tuples presently resident in the live OpenFGA store |
| UV-P-A2 | Whether the service-accounts terraform root has ever applied in prod |
| UV-P-B1 | `EXEMPT_SA_TOKEN_TTL_SECONDS=300` in the deployed task definition (it is a default, not a floor) |
| UV-P-C1 | The full `oauth_clients` population carrying `asana:*` (DB-resident; terraform is a lower bound only) |
| UV-P-C2 | That production iris actually mints via `/tokens/exchange-business` |
| UV-P-C3 | Whether any other consumer calls the OAuth client_credentials endpoint with hermes credentials |
| UV-P-D1 | pydantic v2 list→`str|None` raises rather than coerces (the entire LEG-D refutation rests on this) |
| UV-P-D2 | `agent_access → ServiceClaims` is untested in the SDK (0 grep matches) |
| UV-P-E1 | `REQUIRE_AGENT_ID` enabled in production |
| **SH-1** | **Every autom8y anchor was read on `fix/wss-wildcard-scope-bypass-closure`, not `origin/main` `868ead94`** |
| **SH-2** | SDK line anchors differ between installed 4.1.0 and source 4.2.0 |

### 7.3 — RECOMMENDATION (LABELLED AS SUCH — MODERATE — the re-grade act is the security rite's / operator's, NOT this seat's)

> **RECOMMENDATION (dependency-analyst, substituted seat; MODERATE
> self-assessment cap; ADVISORY ONLY — R-2 binds: RE-2 F-001 stays HIGH until
> the security rite or the operator acts, and this dossier does not re-grade
> it):**
>
> **HIGH STANDS. Re-escalation toward Critical is NOT warranted on this
> evidence — but HIGH should be re-affirmed with two amendments to its
> rationale, and one adjacent finding should be opened.**
>
> **Why not Critical.** Escalation to Critical would require at least one of:
> (a) an unauthenticated or trivially-obtainable path to an exempt token —
> refuted, TB-4 requires the client secret; (b) write capability on the exempt
> scope sets — refuted, both are read-only with `authorized_organizations: []`;
> (c) an unbounded token lifetime — refuted, MIT-1, D5 is substantiated at
> `config.py:83`. The design is a *deliberate, documented, operator-approved*
> cross-tenant read exemption with a real 5-minute bound. That is a HIGH-shaped
> risk, not a Critical-shaped one.
>
> **Amendment 1 to the HIGH rationale — the finding is wider than two SAs.**
> NF-1: 18 of 18 registered service accounts are `business_scoped: false`. The
> chain traced for `ace`/`iris` is *identical* for all 18 — the predicate is a
> single unfiltered boolean at `modules/service-accounts/main.tf:35` and
> `sa_reconciler.py:795`. F-001 should be understood as a population-level
> property of the registry, not a two-identity exception. This does not raise
> severity by itself (all 18 carry approved exemption blocks), but it changes
> the remediation target from "review two SAs" to "the exemption path has no
> filter."
>
> **Amendment 2 to the HIGH rationale — AGG-1 + AGG-2 weaken the stated
> mitigations.** The exemption-revocation story (`token_service.py:617-622`)
> is undercut by the boot reconciler restoring the tuple (AGG-1), and the 300s
> TTL is the *sole* revocation bound rather than a secondary one (AGG-2). If
> F-001's HIGH grade was justified partly by "revocable via tuple removal," that
> justification is materially weaker than it reads.
>
> **Adjacent finding to open (NOT a re-grade, NOT CF-7).** LEG C surfaced a
> governance-integrity defect independent of F-001: `iris`/`autom8y-hermes` is
> declared in two substrates with divergent scope sets
> (`service-accounts.yaml:253-258` has no asana scope;
> `terraform/services/auth/main.tf:1581` grants `asana:read`), no reconciler
> exists between them (TB-11), and a shipped consumer docstring
> (`autom8y-hermes/plugins/autom8y/auth/service_jwt.py:24-27`) advertises the
> scope set the runtime token does **not** carry. Severity of *this* is low on
> access-control grounds (§4.4: scope is not checked at the asana boundary
> anyway) but non-trivial on audit-integrity grounds: the written record of what
> `iris` may do is wrong in a shipped artifact. Recommend filing separately.
>
> **Hardening lever worth naming for the operator (mechanism only, no
> sequencing — remediation ownership is not this seat's).** The single
> highest-leverage structural change surfaced by the trace is at TB-10: add a
> `token_type` assertion to the SERVICE arm at `[4.1.0] client.py:473` /
> `[4.2.0] client.py:489-490`, mirroring the guard the USER arm already has at
> `client.py:464-470`. CF-6 is presently held shut by a `list`-vs-`str` accident
> in an unrelated claim (§5.4); an RFC-6749-correctness commit normalising
> `token_service.py:429` to a space-delimited string would open it. That is a
> latent, one-commit-away exposure and it is not currently guarded by any test
> (UV-P-D2).

---

## §8 — Handoff notes

- **Charge coverage**: LEG A ✅ · LEG B ✅ · LEG C ✅ · LEG D ✅ · STRIDE-lite ✅ · severity input ✅. CF-7 not entered.
- **Fence compliance**: zero writes outside this file; zero git verbs; zero API calls to AWS/Asana/OpenFGA; `gh api` used for two branch-SHA **reads** only; no credential value, secret file, or token was read, minted, or decoded. `oauth-clients.tfvars` was read and contains **no** secret material by construction (`:52-53`); AWS-SM paths were noted as **paths only**, never resolved.
- **Rung discipline (BR-6)**: `STRUCTURALLY-VERIFIED`. Not `REALIZED-MECHANISM` — no runtime observation was made. Consumers must not upgrade this rung without discharging UV-P-A1 and UV-P-C2 at minimum.
- **SH-1 is the highest-priority discharge** before any operator action rests on this dossier: the `autom8y` anchors come from a branch named for a scope-bypass closure, not from `origin/main`.
