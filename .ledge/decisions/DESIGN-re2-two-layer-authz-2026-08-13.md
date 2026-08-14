---
type: decision
artifact_type: DESIGN
artifact_id: DESIGN-re2-two-layer-authz-2026-08-13
title: "RE-2 — the write door checks permission: two-layer authorization design for the Asana write surface (SEC-001)"
status: proposed
lifecycle_note: "AUTHORED-UNMERGED (F-A) — rests unmerged in the working tree; that is its terminal state this wave (Q-4 HALT). No inscription or merge follows."
phase: design
authored_by: security-reviewer
rite: security (co-seated via inv-20260813-41bc318aeb4c)
authored_on: 2026-08-13
initiative: chain-of-custody-closure
sprint: CC-2
answers: SEC-001 (Q1/Q2/Q3) per HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13.md §3
upstream_handoff: .ledge/handoffs/HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13.md
rung: rung-DESIGN
rung_not_claimed: rung-ENFORCED
producer_code_basis: "autom8y-asana @ origin/main = d75601531edd220e693ce279f10b2a9b1d171f20 (ALL reads via `git show origin/main:<path>`)"
consumer_code_basis: "autom8y @ origin/main (ALL monorepo reads via `git show origin/main:<path>` — local checkout is divergent, MONOREPO TRAP per handoff §4.4)"
sdk_basis: "autom8y-auth 4.1.0 as installed at .venv/lib/python3.12/site-packages/autom8y_auth"
evidence_ceiling: MODERATE (self-assessment cap per F-C / self-ref-evidence-grade-rule; STRONG requires the rite-disjoint critic's own-hands re-derivation)
scope: DESIGN ONLY — no production code authored, no infra mutation, no deploy, no Asana call of any class, no credential material read or transcribed.
verdict: Request-Changes
blocking_findings: [SEC-001]
---

# DESIGN — RE-2: the write door checks permission

> **How to read this.** §0 names the rung. §1 answers SEC-001 Q1 (confirm/refute).
> §2 is the NR-2 first-sweep with every return including nulls — **two sweeps came
> back NOT NULL and they change the design**. §3 answers Q3 (the hinge) *before*
> §4's option slate, because the hinge determines which options are admissible.
> §4 enumerates the slate, then prices it, then recommends. §5 is the recommended
> design with named owners. §6 is the owner table. §7 is the UV-P register.
>
> **Three corrections to inherited premises, surfaced rather than absorbed**, all
> found by direct read at authoring time and all material to the remediation:
>
> - **[CORRECTION-1]** A per-operation write-scope vocabulary **already exists in
>   this repo** (`api/main.py:150-192`), is already mapped to write routes, and is
>   published in the OpenAPI spec. It is documentation-only and has exactly one
>   caller. The taxonomy work of layer 1 is therefore **drafted, not greenfield** —
>   but it does **not** cover the comment-create class. §2 sweep (b).
> - **[CORRECTION-2]** The SDK ships `require_scope()` / `require_permission()` /
>   `has_scope()` / `has_permission()` as first-class primitives (4.1.0). The
>   enforcement gap here is a **call-site omission, not an absent capability** —
>   which inverts the cost of the in-repo layer. §2 sweep (d).
> - **[CORRECTION-3]** `has_scope()` carries a **wildcard fail-open**
>   (`scope == "*"` → True, `claims.py:220-222`). The monorepo's own auth service
>   documents this hazard and routes around it (`service-accounts.yaml:682-683`).
>   **The obvious remediation — `has_scope("asana:write")` — is the wrong axis.**
>   This is the single most consequential finding in this artifact. §3.3.

---

## §0 — The rung

This artifact rests at **`rung-DESIGN`**.

**`rung-ENFORCED` is NOT claimed.** The formulation is borrowed deliberately from
ADR-007 §1.2, which closed its wave at `REALIZED-MECHANISM` and recorded that
"**`PASS-REALIZED` was not claimed**" while the substrate-stale finding stood.
The same discipline applies here, and the distinction is the wave's defining
failure mode if collapsed:

| Rung | What it asserts | Status here |
|---|---|---|
| **`rung-DESIGN`** | The finding is re-derived own-hands against a pinned substrate; the remediation option space is exhaustively enumerated, priced, and recommended; each layer has a named accountable owner. No code exists. | **CLAIMED** |
| **`rung-ENFORCED`** | The control is on the wire and biting: a caller lacking authorization receives 403 on a live write route, proved by a two-sided harness (denied-caller RED, authorized-caller GREEN). | **NOT CLAIMED — unreachable this wave** |

`rung-ENFORCED` is unreachable here for a structural reason, not a scheduling one:
the two-sided harness requires minting two service tokens with *different*
authorization states and exercising a write route with each. Minting tokens is
credential handling (**CR-5**) and exercising an Asana write path of any class is
**CR-1**-forbidden. No amount of effort inside this seat's fences reaches the
higher rung. Claiming it would be theater.

**What this artifact is FOR:** it is the input to an operator-review→land
sequence (handoff §5), and — under the wave's recede semantics — the typed
`blocking_findings` payload that a 10x-dev seat can consume as concrete
remediation input.

**Verdict: `Request-Changes`** (blocking). Severity **High**. Blocking finding:
**SEC-001**. Rationale at §5.4.

---

## §1 — SEC-001 Q1: confirm or refute

> *"Is `require_service_claims` (`internal.py:83-162`) authenticate-and-pass-through
> with NO write-class authorization, and is `admin.py:456` the ONLY permission gate
> on the surface?"*

### 1.1 — CONFIRMED, on both limbs, own-hands

**Limb 1 — `require_service_claims` is authenticate-and-pass-through. CONFIRMED.**

The function occupies exactly `internal.py:83-162` (line numbers verified, no
drift). Its complete control flow is: extract bearer → reject PAT-shaped tokens
(`:106-119`) → `validate_service_token(token)` (`:122`) → log → construct and
return a claims object (`:157-162`). There is no branch on any authorization
predicate. It never calls `has_scope`, `has_permission`, `require_scope`, or
`require_permission`. Every caller that clears signature/issuer/expiry/audience
receives claims and proceeds.

**Limb 2 — `admin.py:456` is the only permission gate. CONFIRMED, mechanically.**

A grep for every permission-check idiom across **all** `src/**/*.py` at
`origin/main` returns exactly six lines. Five are non-enforcing:

| Hit | Character |
|---|---|
| `admin.py:36` | comment |
| `admin.py:39` | constant definition `SUPER_ADMIN_PERMISSION = "admin:access"` |
| `admin.py:463` | log field |
| `admin.py:472` | error-message f-string |
| `internal.py:161` | claims propagation (`permissions=list(claims.permissions)`) |

The sixth — `admin.py:456`, `if SUPER_ADMIN_PERMISSION not in claims.permissions`
→ 403 `INSUFFICIENT_PRIVILEGE` — is the **only** site in the service where an
authorization decision is taken. It guards `POST /v1/admin/cache/refresh`. It is
not an Asana write.

**All five write classes re-verified at the cited anchors.** No line drift:

| Write class | Route anchor | Auth dependency | Claims in scope? |
|---|---|---|---|
| Comment create | `receipts.py:99` (`post_receipt`) | `require_service_claims` (`:103`) | yes |
| Task create (intake) | `intake_create.py:73` (`create_intake_business`) | `require_service_claims` (`:77`) | yes |
| Task create (generic) | `tasks.py:197` (`create_task`) | dual-mode `get_auth_context` | **no** |
| Task update (generic) | `tasks.py:258` (`update_task`) | dual-mode `get_auth_context` | **no** |
| Custom-field write | `entity_write.py:195` (`write_entity_fields`) | `require_service_claims` (`:200`) | yes |
| Custom-field write | `intake_custom_fields.py:57` (`write_custom_fields`) | `require_service_claims` (`:62`) | yes |

Not one of them consults `claims.permissions`, `claims.scope`, or `service_name`
for an authorization decision. **The finding holds. CR-1 is the only control.**

### 1.2 — Three refinements that sharpen the finding

These are **not** refutations of the finding. They are corrections to the
*remediation premise*, and each moves the design.

**[R-1] `tasks.py` is not the same defect as the other four — it is a worse one
and a cheaper one simultaneously.**

`create_task` (`:197-202`) and `update_task` (`:258-264`) take **no claims
parameter at all**. They receive `AsanaClientDualMode`. There is no
`ServiceClaims` object in scope to check. So:

- *Worse*: adding a permission check to these two routes requires first plumbing
  an identity into the handler. It is not a one-line addition.
- *Cheaper*: `get_auth_context` (`dependencies.py:109-135`) is **dual-mode** — for
  PAT callers it "passes through the user's PAT unchanged" (`:123-124`), so an
  Asana-side ACL **already authorizes** that path (the user's own PAT carries the
  user's own Asana permissions). The unauthorized path on `tasks.py` is
  specifically the **JWT→shared-bot-PAT** branch (`:239` `bot_pat = get_bot_pat()`,
  `:263-267` returns `AuthContext(asana_pat=bot_pat, ...)`).

**Design consequence:** the write surface is not uniformly unauthorized. The
defect is precisely *"a JWT caller is lent the shared bot credential"*. Any
remediation must gate the JWT branch and must not break the PAT branch.

**[R-2] The scope vocabulary is not absent in this repo — it is present and
inert.** See §2 sweep (b). This halves the taxonomy design cost and supplies a
ready-made draft.

**[R-3] `admin.py:456` may be gating on a permission no service account is
provisioned with.** The minted scope set at `services/auth/service-accounts.yaml`
contains no `admin:access` (§2 sweep (b) return). If `permissions` derives from
ServiceAccount scopes — as `internal.py:40-43` states — then `admin.py:456`
currently denies **every** caller. That is fail-closed and therefore not a
vulnerability, but it means the fleet's one working permission gate has likely
**never been exercised green in production**, so it is not evidence that the
mechanism works end-to-end. Carried as **UV-P-1**.

---

## §2 — NR-2 first-sweep (the wave's strongest negative)

### 2.0 — The negative, stated

> **"No `asana:*` write scope exists at the minting layer."**
> **"No `acting_agent`/`delegating_user` claim exists anywhere."**
> **"CR-1 is the ONLY control."**

I state this negative and first-sweep it below. Rite-disjoint second-read by
`dependency-analyst` is the wave's designated corroboration; this artifact's
self-assessment is capped at **MODERATE** per F-C.

### 2.1 — Sweep (a): was every grep run against `git show origin/main:`?

**RETURN: YES — with one declared exception.**

Every claim about `autom8y-asana` source and every claim about the `autom8y`
monorepo was derived via `git show origin/main:<path>` or
`git grep <pat> origin/main -- <path>`. `origin/main` for autom8y-asana is pinned
at `d75601531edd220e693ce279f10b2a9b1d171f20`. The monorepo local checkout was
**never read** (MONOREPO TRAP, handoff §4.4).

**Declared exception:** the `autom8y_auth` SDK (4.1.0) was read from the
**installed venv** at `.venv/lib/python3.12/site-packages/autom8y_auth`, not from
git. This is correct and deliberate — the installed artifact is what the running
service imports, and the SDK source is not vendored in either repo at
`origin/main`. Version pin corroborated: 4.1.0, consistent with the FORK-C
`uv.lock` pin. Carried as **UV-P-2** (the installed wheel is not proved
byte-identical to the published 4.1.0 artifact).

### 2.2 — Sweep (b): does a scope vocabulary exist under a DIFFERENT spelling?

**RETURN: NOT NULL — and this is the sweep's most consequential result.**

**(b.i) At the consuming service (autom8y-asana): a vocabulary EXISTS.**

`api/main.py:150-168` defines `_OAUTH2_SCOPE_DEFINITIONS` — 17 scopes on an
`{entity}:{action}` convention, including `tasks:write`, `intake:write`,
`sections:write`, `projects:write`, `admin:manage`.

`api/main.py:173-192` defines `_SCOPE_RULES` — a path-prefix → required-scope map
that **already maps four of the five write classes**:

| Prefix (`_SCOPE_RULES`) | Write scope | Covers |
|---|---|---|
| `/api/v1/tasks` (`:174`) | `tasks:write` | `tasks.py:197`, `tasks.py:258` |
| `/v1/intake` (`:187`) | `intake:write` | `intake_create.py:73`, `intake_custom_fields.py:57` |
| `/v1/entity-write` (`:191`) | `intake:write` | `entity_write.py:195` |

**But it is inert, and it has a hole:**

- `main.py:142-143` states verbatim: *"Scopes are DOCUMENTATION-ONLY — they
  describe intended authorization requirements per-operation. Runtime enforcement
  remains unchanged."*
- `main.py:712-717` states the OAuth2 scheme is for discovery *"until OAuth2
  enforcement is live."*
- A whole-repo call-graph sweep proves inertness mechanically:
  `_resolve_scopes_for_operation` has **exactly one caller**, `main.py:732`,
  inside `custom_openapi()`. No route, no dependency, no middleware, no test
  consumes it.
- **The hole:** `/v1/receipts` appears **nowhere** in `_SCOPE_RULES` (grep count
  0 over `:173-192`). The comment-create write class has no scope even in the
  documentation vocabulary — `_resolve_scopes_for_operation("/v1/receipts",
  "post")` returns `[]`.

**(b.ii) At the minting layer (autom8y-auth): the negative HOLDS.**

The complete set of scope values minted across every service account at
`services/auth/service-accounts.yaml` @ `origin/main` is **exactly ten**:

```
ads:read  analytics:read  data:read  data:write  query:read
read:pii  scheduling:read  scheduling:write  sms:read  sms:send
```

Grep for any scope containing `asana`: **NULL**. There is no `asana:write`,
no `asana.write`, no `write:asana`, no numeric id, no role, no group.
The `asana-onboarding-walkthrough` SA (`:585-600`) carries `data:read` only and
self-documents least-privilege.

**Note the vocabulary mismatch:** asana's inert doc-vocabulary uses `admin:manage`
(`main.py:166`); its live enforcement constant uses `admin:access`
(`admin.py:39`); the minting layer mints **neither**. Only `query:read` overlaps
between the two vocabularies.

**Net:** the negative *"no `asana:*` write scope exists at the minting layer"*
**HOLDS**. The broader negative *"no scope vocabulary exists"* is **REFUTED for
the consuming service** — a drafted, route-mapped, published-but-unenforced
vocabulary is already in the repo, missing only the receipts class.

### 2.3 — Sweep (c): is there authorization by ANOTHER mechanism?

**RETURN: NULL for every inbound authorization mechanism probed. The "CR-1 is
the only control" claim SURVIVES.**

| Probe | Return |
|---|---|
| Router-level runtime gate (`_security.py`) | **NULL.** `_security.py:10-12` states `auto_error=False` ensures `SecureRouter`s *"only inject OpenAPI metadata without performing runtime auth checks"*. Metadata only. |
| WAF anywhere in monorepo terraform | **NULL.** `git grep -l 'wafv2\|aws_waf' origin/main -- terraform/*` → no matches. |
| ALB `internal` flag in the platform module | **NULL** in `terraform/modules/platform/*`. The flag lives in the external `a8` `service-stateless` module, not checked out. Consistent with handoff §2. |
| Security groups as caller authorization | **NULL as authz.** `terraform/services/asana/main.tf:119-124` consumes `alb_security_group_id` from platform remote state — a shared, network-tier SG for all services on the shared ALB (priority 10=auth, 110=data, 120=asana, `:126-129`). A shared SG cannot distinguish caller services. |
| mTLS / client-cert allowlist | **NULL.** No mTLS configuration found in either repo at `origin/main`. |
| Route decorator carrying authz | **NULL.** The five write routes' decorators carry only `openapi_extra` metadata (side-effects, idempotency, rate-limit tier). |
| Tenant-scope middleware as write-class authz | **NOT NULL, but orthogonal.** `main.py:445` `require_business_scope=True` opts into ADR-07 §7.1 precedence (`bypass_scope_enforcement` → `business_id` → reject). This is real, live **tenant isolation** — but it authorizes *which tenant's data*, never *which write class*. Several fleet SAs carry `bypass_scope_enforcement=True` by design (`claims.py:119-126`). Orthogonal axis; does not falsify the finding. |
| Rate limiting as a control | **NOT NULL, but not authz.** `rate_limit.py` applies SA-namespace token buckets. Throttles volume, not permission. |

**Conclusion of sweep (c): the negative HOLDS.** No inbound mechanism at any
layer — network, middleware, router, or decorator — distinguishes which service
may invoke which Asana write class. CR-1 is the only control.

*(SEC-003's ALB-internal question remains genuinely open and is NOT absorbed
here — it bounds exploitability, not the finding.)*

### 2.4 — Sweep (d): is the gap a call-site omission rather than an absent capability?

**RETURN: NOT NULL — the gap IS a call-site omission at the enforcement layer.
This inverts the remediation cost.**

The `autom8y-auth` SDK at 4.1.0 already ships every primitive required:

| Primitive | Anchor | Character |
|---|---|---|
| `ServiceClaims.has_scope(scope)` | `claims.py:204-236` | predicate — **carries a wildcard fail-open**, see §3.3 |
| `ServiceClaims.has_permission(perm)` | `claims.py:238-247` | predicate — plain list membership, **no wildcard** |
| `require_scope(scope)` | `dependencies.py:117-153` | FastAPI dependency factory → `PermissionDeniedError` |
| `require_service_permission(perm)` | `dependencies.py:156+` | FastAPI dependency factory, `ServiceClaims.permissions`-based |
| `require_permission(perm)` | `dependencies.py:255` | FastAPI dependency factory (UserClaims) |

And the enforcement idiom is already proven in-repo at `admin.py:456`.

**So the enforcement layer needs no new capability — it needs call sites.** But
two concrete obstacles make it more than a one-line change, and both are design
inputs:

1. **This repo re-declares its own narrow `ServiceClaims`.** `internal.py:33-49`
   is a *local Pydantic model*, not the SDK's. It has **zero methods**
   (`has_scope`/`has_permission` are unavailable on it), and its construction at
   `internal.py:157-162` copies only `sub`, `service_name`, `scope`,
   `permissions` — **dropping `scopes`, `client_id`, `business_id`, `key_id`,
   `bypass_scope_enforcement`**. The lossiness is load-bearing: `client_id` — the
   key the fleet precedent authorizes on (§4.1 option (e)) — is discarded before
   any route sees it.
2. **`tasks.py` has no claims in scope at all** (per [R-1]).

**Net:** the capability exists; the vocabulary is drafted here and absent
upstream; the claims model is lossy; two routes lack identity entirely. The gap
is a call-site omission **plus** a claims-plumbing omission — not an absent
capability.

### 2.5 — Sweep return: delegation identity

**RETURN: NULL in `src/` — the corrected premise is CONFIRMED and strengthened.**

A sweep for `acting_agent|delegating_user|on_behalf_of|impersonat` across every
`.py` at `origin/main` returns **zero hits in `src/`**. (Apparent hits on
`extract_async` are regex noise from the `act_as` substring.)

The only true hits are **disclosure text** at `mcp/asana_mcp/tools/workflows.py:25-26`
and `:61-62`, which state that writes ride the *"shared bot PAT (S2S-JWT → bot
PAT) until the identity keystone (acting_agent + delegating_user) lands in a
cross-repo Phase-2."*

This is stronger than the handoff's framing: the absence is not merely true, it
is **known, documented, and deferred to a cross-repo Phase-2** in the service's
own MCP surface disclosure.

---

## §3 — SEC-001 Q3: the hinge, answered explicitly

> *"Is `caller_service` (captured, log-only at `entity_write.py:231,:362`) a
> SUFFICIENT authorization key, or is a delegation identity required FIRST?"*

*Answered before the option slate because the answer determines which options are
admissible.*

### 3.1 — What `caller_service` actually is

`caller_service` is `claims.service_name`. The critical fact, corroborated in
this repo's own cross-repo anchor at `rate_limit.py:25-46` and verified directly
against the SDK:

- `ServiceClaims.service_name` is a Python **`@property` that returns `self.sub`**
  (`claims.py:183-185`). It is **not a JWT claim**.
- The auth service emits `service_account_id` (= `sa.yaml_id`, the canonical SA
  short-name, e.g. `"asana-dataframe-resolver"`) **and** `client_id`
  (= `sa.client_id`) as the real claims (`rate_limit.py:26-31, :34-37`).
- `rate_limit.py:42-46` records a **prior defect of exactly this class**:
  Sprint-1 read `payload.get("service_name")`, which does not exist, so every SA
  request silently fell through to the PAT namespace. Corrected to read
  `service_account_id` (canonical), accepting `client_id` as secondary.

So `caller_service` today resolves to the **SA UUID** (`sub`). It is
signature-covered, issuer-asserted, and unforgeable by the caller. It is also
opaque — the logs at `entity_write.py:231,:362` are recording UUIDs.

**Confirmed log-only:** a whole-`src/` sweep shows `service_name` never branches
control flow for authorization. Its non-log uses are the idempotency partition
key (`idempotency.py:602-629, :818`), a telemetry span attribute
(`resolver.py:359`), and propagation into `AuthContext` (`dependencies.py:266`).

### 3.2 — The answer

**`caller_service` IS a sufficient authorization key for the question SEC-001
actually asks — and a delegation identity is NOT required first.**

SEC-001 asks: *which service may invoke which write class?* That is a
service-authorization question, and its correct key is the issuer-asserted
service identity, which is present, signed, and unforgeable today. Requiring a
delegation identity before enforcing service authorization would gate a
**closeable single-repo control** behind an **unstarted cross-repo Phase-2** —
leaving CR-1 as the only control for that entire interval. That trade is not
defensible.

**But the sufficiency is bounded, and the bound is the honest part:**

| Question | Key required | Available today? |
|---|---|---|
| Which *service* may invoke this write class? | issuer-asserted service identity (`sub` / `service_account_id` / `client_id`) | **YES** |
| On whose *behalf* is this write performed? | `delegating_user` | **NO** |
| Which *agent seat* performed it? | `acting_agent` | **NO** |

**Therefore:** enforcement keyed on `caller_service` **closes SEC-001** and does
**not** retire CR-1. CR-1 exists because Asana writes are operator-reserved —
that is a statement about *human/agent* authority, and no service-level control
can answer it. Anyone reading a future "the write door checks permission" claim
as "CR-1 can be lifted" would be making a category error. **§5.3 carries this as
an explicit non-claim.**

### 3.3 — The axis correction (the most consequential finding here)

**Do not key enforcement on `has_scope()`.**

`has_scope()` (`claims.py:204-236`) resolves in four modes, and mode 1 is:

```python
# Wildcard shortcut (legacy sentinel — grants everything).
if self.scope == "*":
    return True
```

Any token carrying `scope == "*"` satisfies `has_scope("asana:write")`
unconditionally. A write-class gate built on `has_scope` is **fail-open** against
that carrier.

This is not my inference — **the monorepo's own auth service documents the hazard
and routes around it.** `services/auth/service-accounts.yaml:682-683`, describing
the scheduling service's enrollment-writer guard, states verbatim:

> *"The guard resolves through `ServiceClaims.has_permission` (plain membership),
> **NOT `has_scope`, which short-circuits True on `scope == "*"`**."*

`has_permission()` (`claims.py:238-247`) is plain list membership with no
wildcard. **The `permissions` axis is the safe axis.** This is also the axis
`admin.py:456` already uses.

**Design consequence:** option (a) as posed in the handoff — *"`has_scope`
enforcement on the write routes"* — is **the wrong primitive**, and the slate
must carry a permissions-axis variant. §4.1 (f).

---

## §4 — SEC-001 Q2: the remediation shape

Per `option-enumeration-discipline`: **enumerated first (§4.1), priced second
(§4.2), recommended only third (§4.3).**

### 4.1 — The slate (enumeration — no preference expressed)

**(a) Minted scope vocabulary + `has_scope` enforcement.** Mint per-service →
write-class scopes (`asana:tasks:write`, `asana:receipts:write`,
`asana:fields:write`) at `services/auth/service-accounts.yaml`; enforce with
`has_scope`/`require_scope` on the five write routes.

**(b) mTLS / service allowlist at the transport layer.** Terminate client certs
or an SG/listener allowlist in front of the write routes so only named services
reach them.

**(c) Per-write-class bot-credential partition.** Replace the single shared
`ASANA_PAT` with N bot credentials, one per write class, each held in a distinct
secret path, each with Asana-side permissions narrowed to that class.

**(d) Do nothing — ratify CR-1 as the control, with a named owner.** No code
change. CR-1 is elevated from an informal fence to a ratified, owned,
periodically-attested process control.

**(e) Per-write-class writer allowlist keyed on issuer-asserted identity,
enforced in-service, deny-by-default.** Config-driven set of authorized
`service_account_id`/`client_id` values per write class; empty set == deny-all,
loudly. **This is a fleet-ratified precedent, not a novel invention** —
`SCHEDULING_ENROLLMENT_WRITER_CLIENT_IDS` (`services/auth/service-accounts.yaml:680-683`;
code-side at `services/auth/migrations/versions/036_provision_asana_enrollment_bridge_sa.py:53`;
`services/auth/tests/_canonical_sa_constants.py:78`; terraform-asserted at
`tests/test_enrollment_intent_bridge_terraform.py:288`). **Single-layer: requires
no minting-layer change.**

**(f) Permissions-axis enforcement.** Mint write scopes upstream (as in (a)) but
enforce via `has_permission` / `require_service_permission` — the axis with **no
wildcard fail-open** (§3.3), matching `admin.py:456`'s existing idiom.

**(g) Network segmentation of the write surface.** Split the five write routes
onto a distinct ALB listener rule / target group / internal-only surface, so
write reachability is a network property.

**(h) Delegation-identity-first.** Land the `acting_agent` + `delegating_user`
keystone (the cross-repo Phase-2 named at `mcp/asana_mcp/tools/workflows.py:25-26`)
before building any write-class authorization.

### 4.2 — The pricing

Every option priced on: layers touched, owner locus, whether it closes SEC-001,
residual risk, and the blocking dependency.

| # | Layers | Owner locus | Closes SEC-001? | Residual risk | Blocking dependency |
|---|---|---|---|---|---|
| **(a)** | 2 (mint + enforce) | cross-repo | Partially | **HIGH — `has_scope` wildcard fail-open (§3.3), explicitly warned against by the auth service itself.** Also needs `scopes` re-added to the lossy local claims model (`internal.py:157-162`). | minting-layer change lands first |
| **(b)** | 1 (infra) + external | `a8` module repo (not checked out) | Yes, coarsely | Cannot express per-**write-class** granularity — only per-caller reachability. Shared ALB (priority 120 on a listener shared with auth/data) makes per-service cert termination invasive. Blast radius touches every service on the listener. | UV-P-C-2 (SEC-003) must resolve first |
| **(c)** | 1 (secrets + Asana admin) | asana service + Asana workspace admin | Yes, and **uniquely also narrows blast radius at the Asana side** | Highest operational cost: N credentials to provision, rotate, monitor. Multiplies the live `ASANA_PAT`-in-history hazard (handoff §4.3) by N. Asana-side per-credential ACLs must actually exist and be maintainable. | Asana workspace admin capability (unverified — **UV-P-3**) |
| **(d)** | 0 | operator | **No** — it *is* the status quo | The control is a human fence over a surface reachable by any fleet JWT. Its failure mode is silent: nothing detects or refuses an unauthorized write. Depends entirely on UV-P-C-1 (SEC-002) for its risk profile. | none |
| **(e)** | **1 (enforce only)** | **autom8y-asana** | **Yes** | Allowlist is config, so it drifts unless owned; must key on `service_account_id`/`client_id` (**requires un-lossing `internal.py:157-162`**); `tasks.py` needs identity plumbed ([R-1]). **No wildcard exposure.** | none — shippable independently |
| **(f)** | 2 (mint + enforce) | cross-repo | Yes | Correct axis, no wildcard. Same lossy-model and `tasks.py` work as (e). Strictly better than (a). | minting-layer change lands first |
| **(g)** | 1 (infra) + external | `a8` module repo | Partially | Same shared-ALB constraint as (b); does not distinguish *which* authorized service may perform *which* class. | UV-P-C-2 (SEC-003) |
| **(h)** | 3+ (mint + SDK + enforce, cross-repo) | fleet | Not by itself | **Leaves CR-1 as the only control for the entire duration of an unstarted cross-repo Phase-2.** Answers a different, larger question (§3.2). | the entire Phase-2 |

**Two structural observations from the pricing:**

1. **(e) is the only option that closes SEC-001 at a single layer with no
   blocking dependency.** Every other closing option waits on a minting-layer
   change, an external module repo, or Asana workspace administration.
2. **(a) is dominated by (f).** Same two layers, same cost, but (a) carries a
   documented fail-open that (f) does not. **(a) should not be selected.**

### 4.3 — The recommendation

**Recommended: (e) now, (f) next — a two-layer design in which layer 1 ships
independently and layer 2 upgrades it in place.**

Explicitly **not** recommended: (a) (dominated by (f), fail-open axis); (b)/(g)
(cannot express write-class granularity; blocked on SEC-003); (h) (leaves CR-1
sole control indefinitely); (d) (is the status quo the finding indicts).

**(c) is not rejected — it is deferred with a trigger.** It is the only option
that narrows blast radius *at the Asana side*, which is a property (e)+(f)
cannot provide: under (e)/(f) an authorized-but-compromised caller still holds
full bot authority. Its trigger is stated at §5.2.

---

## §5 — The recommended design

### 5.1 — Layer 1 — enforcement, in `autom8y-asana` (ships independently)

**L1-1. Un-loss the claims model.** Extend the local `ServiceClaims`
(`internal.py:33-49`) and its construction (`:157-162`) to carry
`service_account_id` and `client_id`. **Rationale:** these are the real,
issuer-emitted JWT claims (§3.1); `service_name` is a Python property over `sub`.
`rate_limit.py:42-46` records the exact defect that follows from reading the
wrong field. Prefer `service_account_id` (canonical), accept `client_id` as
secondary — mirroring the correction already made in `rate_limit.py`.

**L1-2. Add a deny-by-default write-class authorization gate.** One dependency
per write class, keyed on the identity from L1-1, resolved against a
config-supplied allowlist. **Empty allowlist == deny-all, loudly** — following
`SCHEDULING_ENROLLMENT_WRITER_CLIENT_IDS` (§4.1 (e)). Deny emits 403
`INSUFFICIENT_PRIVILEGE`, matching `admin.py:466-473`'s existing shape.

Apply at all five sites: `receipts.py:99`, `intake_create.py:73`,
`entity_write.py:195`, `intake_custom_fields.py:57`, and — after L1-3 —
`tasks.py:197`/`:258`.

**L1-3. Plumb identity into `tasks.py` without breaking the PAT branch.** Per
[R-1], `get_auth_context` is dual-mode. The gate must fire **only on the JWT
branch**; the PAT branch is already authorized by Asana's own ACL on the user's
PAT and must pass through unchanged. This is the single highest-regression-risk
item in the design and warrants a two-sided test (JWT-denied RED / PAT-allowed
GREEN).

**L1-4. Close the `/v1/receipts` vocabulary hole.** Add the missing prefix to
`_SCOPE_RULES` (`main.py:173-192`) so the comment-create class is *documented*
consistently with the other four (§2.2). Documentation-only, but it is the
class most likely to be forgotten again precisely because it is absent today.

**Deliberately excluded from layer 1:** any change to `has_scope` usage (§3.3),
any minting-layer change, any Asana-side credential change.

### 5.2 — Layer 2 — vocabulary, at `autom8y-auth` (upgrades layer 1 in place)

**L2-1. Mint per-write-class scopes** in `services/auth/service-accounts.yaml`
on the established `<domain>:<verb>` convention (`:25`). The drafted taxonomy at
`main.py:150-192` is the input; the receipts class must be added.

**L2-2. Provision least-privilege per SA**, with the `exemption`/`justification`
discipline the file already enforces for cross-tenant grants.

**L2-3. Migrate the L1-2 gate from allowlist to `has_permission`** — option (f).
The gate's *shape* is unchanged; only its predicate swaps. This is why layer 1 is
not throwaway: it is the same door, re-keyed.

**Binding constraint on L2-3: use the `permissions` axis, never `has_scope`**
(§3.3, corroborated at `service-accounts.yaml:682-683`).

**Deferred option (c) trigger.** Revisit per-write-class bot-credential
partition if **either**: (i) SEC-002/UV-P-C-1 resolves to "an agent seat can
obtain a valid service JWT by documented patterns", making an authorized-caller
compromise materially likely; **or** (ii) the count of SAs authorized for any
write class exceeds a small number, at which point shared-credential blast radius
dominates.

### 5.3 — Non-claims (binding)

1. **This design does NOT retire CR-1.** It closes service-level authorization;
   CR-1 is an operator/agent-authority control that no service-level mechanism
   can answer (§3.2). CR-1 remains in force until an operator rules otherwise.
2. **This design does NOT bound exploitability.** SEC-002 (UV-P-C-1) and SEC-003
   (UV-P-C-2) are untouched here and are not absorbed.
3. **This design does not decide the locus (F-3), the execution timing, or
   whether remediation ever lands.** Those are operator-reserved (handoff §5).
4. **Scope fence honored:** the D-4 modal fires on Asana writes only. Slack
   delivery is untouched and stays autonomous (R-7).

### 5.4 — Verdict rationale

**`Request-Changes` (blocking), severity High.** Under the Decision Matrix,
High/Critical → Request Changes (blocking). Severity is High, not Critical, on
the Bug Bar's exploitation-context criterion: the defect is an authorization
bypass on a write surface (Critical-shaped), but exploitation requires a valid
fleet service JWT — i.e. it is **authenticated**, not anonymous — and the
reachability of that credential from an unprivileged seat is **UNESTABLISHED**
(UV-P-C-1 / SEC-002, deliberately unprobed). Severity is therefore held at High
with an explicit escalation condition: **if SEC-002 returns that an agent seat
can obtain a qualifying JWT by documented patterns, this finding escalates to
Critical**, because the write surface would then be reachable without an
operator and CR-1's sole-control status would be actively load-bearing against a
reachable adversary.

`blocking_findings: [SEC-001]` is populated per the SI-5 recede binding — the
verdict carries typed remediation input a 10x-dev seat can consume.

---

## §6 — Named owners

`rung-DESIGN` without a named owner is not `rung-DESIGN`. Owners are named by
concrete role/team, derived mechanically where a CODEOWNERS rule exists.

| Layer | Deliverable | **Named owner** | Basis |
|---|---|---|---|
| **Layer 1** — enforcement (L1-1..L1-4) | `autom8y-asana` write routes + claims model | **`@autom8y/platform-team`**, executing through the **autom8y-asana service maintainer seat (10x-dev rite, principal-engineer)** | No CODEOWNERS in autom8y-asana (**see gap below**); ownership imputed from the `owner: platform-team` stamp carried by asana-related SA entries in `services/auth/service-accounts.yaml` |
| **Layer 2** — vocabulary (L2-1..L2-3) | `services/auth/service-accounts.yaml` scope taxonomy + SA provisioning | **`@autom8y/platform-team`** — mechanically derived: `CODEOWNERS:1` `* @autom8y/platform-team` covers `/services/auth/` (no more specific rule exists) | own-hands read of monorepo `CODEOWNERS` @ `origin/main` |
| **Governance** — CR-1 until layer 1 lands | keeping CR-1 in force; ruling on execution locus and landing | **the operator** (handoff §5, operator-reserved) | handoff §5; kit C-9 |
| **Escalation** — severity re-grade | re-grading SEC-001 High→Critical on SEC-002's return | **security rite** (this seat's successor) | §5.4 |

**Both layers land with the same accountable team, but in two different repos**
— so at least one owner sits outside this repo, exactly as the charge anticipated.
The split is real: layer 2 changes a fleet-shared registry governing every
service account, and its change-control (`exemption`, `approved_by`,
`tension_inherited`) is heavier than layer 1's.

**Named-owner gap found (and it is this design's own):** `autom8y-asana` has
**no CODEOWNERS file at `origin/main`** (verified NULL at both `CODEOWNERS` and
`.github/CODEOWNERS`). The layer-1 owner is therefore imputed, not mechanically
derived. **Recommended L1-0: add a CODEOWNERS to autom8y-asana** so the owner of
the write surface is a mechanical fact rather than an inference. This is the
cheapest item in the design and the one that makes every other item auditable.

---

## §7 — UV-P register

Per the frozen `structural-verification-receipt` syntax.

[UV-P: `admin.py:456`'s permission gate has ever passed green in production — i.e. that some ServiceAccount is actually provisioned with `admin:access` and that `ServiceClaims.permissions` is populated from ServiceAccount scopes end-to-end | METHOD: read the auth service's token-issuance path (`token_service.py` scope→permissions mapping) at `origin/main`, plus a live claims inspection | REASON: the minted scope set at `service-accounts.yaml` contains no `admin:access` (§2.2), so the fleet's one working permission gate may be denying every caller. Live claims inspection is credential handling (CR-5). Bears on §5.2 L2-3, which reuses that mechanism. Route: SEC-002's credential-distribution audit.]

[UV-P: the installed `autom8y_auth` 4.1.0 wheel at `.venv/lib/python3.12/site-packages/autom8y_auth` is byte-identical to the published 4.1.0 artifact in CodeArtifact | METHOD: hash-compare the installed dist-info RECORD against the CodeArtifact-published artifact | REASON: SDK claims in §2.4/§3.3 were read from the installed venv, not from git (declared exception, §2.1). A tampered or locally-modified wheel would falsify the `has_scope` wildcard finding. Low likelihood; stated for completeness.]

[UV-P: Asana-side per-credential ACLs can express per-write-class narrowing, making option (c) mechanically realizable | METHOD: Asana workspace admin console / API inspection of bot-account permission granularity | REASON: option (c)'s pricing at §4.2 assumes Asana can narrow a PAT's authority per write class. Verifying requires Asana workspace administration, outside this seat. Bears only on the deferred option, not on the recommendation.]

[UV-P: the deny-by-default allowlist of §5.1 L1-2 fails closed under every misconfiguration mode (unset env var, empty string, malformed value) | METHOD: two-sided test harness at implementation time — denied-caller RED / authorized-caller GREEN, plus a malformed-config RED | REASON: this is a `rung-ENFORCED` predicate. It cannot be proved at `rung-DESIGN` because it requires running code that does not exist. It is the primary acceptance criterion for the layer-1 build.]

[UV-P: no route outside the five enumerated write classes reaches an Asana write through a path this review did not trace | METHOD: exhaustive outbound-call-graph trace from every route handler to `clients/tasks.py` / `clients/stories.py` HTTP call sites | REASON: this review verified the five classes named in the handoff and swept for authorization mechanisms, but did not independently re-derive the *completeness* of the write-class enumeration from the call graph up. The handoff grades that enumeration STRONG. Route: the rite-disjoint critic's second-read is the natural discharge.]

---

## §8 — Fences honored

| Fence | Status |
|---|---|
| **CR-1** — never exercise an Asana write path of any class | **HONORED.** No Asana API call of any kind was made. The finding was re-derived entirely by static read. |
| **CR-5** — no credential material | **HONORED.** `ASANA_PAT` is referenced as a key name and a path only. No credential value was read, transcribed, or logged. `auth/bot_pat.py` was not dumped. |
| **MONOREPO TRAP** | **HONORED.** Every monorepo read via `git show origin/main:` / `git grep origin/main`. Local checkout never read. Declared exception for the installed SDK at §2.1. |
| **Do not land any fix** | **HONORED.** Design only. No code authored, no infra touched. |
| **Do not absorb F-3 (locus) / landing decision** | **HONORED.** §5.3.3. |
| **Do not widen past R-7** | **HONORED.** §5.3.4 — Asana writes only; Slack delivery untouched. |
| **AUTHORED-UNMERGED (F-A)** | **HONORED.** This artifact rests authored-unmerged in the working tree; that is its terminal state this wave. Nothing here presumes inscription or merge. |
| **Self-assessment cap MODERATE (F-C)** | **HONORED.** `evidence_ceiling: MODERATE`. No STRONG self-grade. |
| **Author files only** | **HONORED.** No git verb executed. |

---

## §9 — Attestation

**Substrate pinned:** autom8y-asana `origin/main` =
`d75601531edd220e693ce279f10b2a9b1d171f20`. Monorepo reads via
`git show origin/main:`. SDK read from the installed 4.1.0 wheel (§2.1 declared
exception).

| Claim | Method | Anchor | Result |
|---|---|---|---|
| `require_service_claims` spans `internal.py:83-162`, no authz branch | file-read | `git show origin/main:src/autom8_asana/api/routes/internal.py` | CONFIRMED, no drift |
| `admin.py:456` is the only permission gate | bash-probe (exhaustive grep over all `src/**/*.py`) | 6 hits, 5 non-enforcing | CONFIRMED |
| Five write classes at cited anchors | file-read ×6 | `receipts.py:99`, `intake_create.py:73`, `tasks.py:197`/`:258`, `entity_write.py:195`, `intake_custom_fields.py:57` | CONFIRMED, no drift |
| `tasks.py` routes carry no claims | file-read | `tasks.py:197-202`, `:258-264` | CONFIRMED — [R-1] |
| Inert scope vocabulary exists in-repo | file-read + call-graph sweep | `main.py:142-143,150-192,197-205`; sole caller `:732` | **NOT NULL** — CORRECTION-1 |
| `/v1/receipts` absent from `_SCOPE_RULES` | bash-probe (grep count) | `main.py:173-192` → 0 | CONFIRMED absent |
| Minted scopes = exactly 10, no `asana:*` | bash-probe (awk extraction) | `git show origin/main:services/auth/service-accounts.yaml` | **NULL for asana** — negative HOLDS |
| SDK ships `require_scope`/`require_permission`/`has_*` | bash-probe (grep) | `claims.py:204,238`; `dependencies.py:117,255` | **NOT NULL** — CORRECTION-2 |
| `has_scope` wildcard fail-open | file-read | `claims.py:220-222` | CONFIRMED — CORRECTION-3 |
| Auth service documents the wildcard hazard | file-read | `service-accounts.yaml:682-683` | CONFIRMED (independent corroboration) |
| `client_id` allowlist is a fleet precedent | bash-probe (git grep) | `service-accounts.yaml:680-683`; migration `036…:53`; `_canonical_sa_constants.py:78`; `test_enrollment_intent_bridge_terraform.py:288` | CONFIRMED in code |
| `service_name` is a property over `sub`, not a JWT claim | file-read ×2 | `claims.py:183-185`; `rate_limit.py:25-46` | CONFIRMED |
| Local `ServiceClaims` lossy (drops `client_id`,`scopes`) | file-read | `internal.py:33-49`, `:157-162`; 0 methods | CONFIRMED |
| `caller_service` never branches for authz | bash-probe (whole-`src` sweep) | non-log uses: `idempotency.py`, `resolver.py:359`, `dependencies.py:266` | CONFIRMED log-only |
| No delegation identity in `src/` | bash-probe | only `mcp/…/workflows.py:25-26,:61-62` disclosure text | **NULL in src** — premise confirmed |
| Router-level gate is metadata-only | file-read | `_security.py:10-12` | CONFIRMED NULL |
| No WAF in monorepo terraform | bash-probe (git grep -l) | `terraform/*` | **NULL** |
| ALB `internal` flag not in platform module | bash-probe | `terraform/modules/platform/*` | **NULL** — SEC-003 stays open |
| Layer-2 owner mechanically derived | file-read | monorepo `CODEOWNERS:1` `* @autom8y/platform-team` | CONFIRMED |
| autom8y-asana has no CODEOWNERS | git-ls-files probe | `CODEOWNERS`, `.github/CODEOWNERS` | **NULL** — named-owner gap, §6 |

**Self-assessment: MODERATE** (F-C cap). STRONG on any claim here requires the
rite-disjoint critic's own-hands re-derivation. The strongest single claim —
the `has_scope` wildcard fail-open — already carries **independent, rite-disjoint
corroboration** from the auth service's own maintainers at
`service-accounts.yaml:682-683`, authored without reference to this review.
