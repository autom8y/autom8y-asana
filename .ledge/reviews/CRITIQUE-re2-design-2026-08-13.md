---
type: review
artifact_type: CRITIQUE
artifact_id: CRITIQUE-re2-design-2026-08-13
title: "NR-2 NCSR second-read receipt — rite-disjoint adversarial sweep of DESIGN-re2-two-layer-authz"
status: draft
lifecycle_state: AUTHORED-UNMERGED (terminal state this wave; main thread owns git; no verb fired by this seat)
rung: rung-CRITIQUE (rite-disjoint second-read receipt; no ratification, no merge)
phase: review
authored_by: dependency-analyst
rite: arch (co-seated borrow; rite-disjoint from CC-2 author security-reviewer)
sprint: CC-2 (chain-of-custody-closure wave) — NCSR second reader
second_reads: DESIGN-re2-two-layer-authz-2026-08-13.md (author: security-reviewer, security)
charge: "attack the NEGATIVE, do not confirm the design; one hop past the author; own-hands via origin/main only"
producer_code_basis: "autom8y-asana @ origin/main = d7560153 (local HEAD 4129ae7e lags by 12 commits — stale-tree hazard REAL)"
consumer_code_basis: "autom8y @ origin/main = 07819b39 (local monorepo tree 158-behind/70-ahead — divergent; every read via git show origin/main:)"
evidence_ceiling: MODERATE (rite-disjoint reader; legs re-derived own-hands are external corroboration, but the NEGATIVE's survival is graded, NOT the design's correctness)
verdict_headline: "NR-2 STANDS, with N-1 NARROWED. 'CR-1 is the only control' SURVIVES (narrowed to app/gateway layer). (f)+(a)+owners HOLD; (a) repriced. UV-P-3 structural half CONFIRMED own-hands."
fences_honored: [CR-1-no-write-path-exercised, CR-5-no-credential-read, CR-2-verdicts-bucket-untouched, no-AWS-call, no-git-verb, origin-main-refs-only]
---

# NR-2 NCSR SECOND-READ — the negative's survival under adversarial own-hands re-derivation

> **Charge discharged as adversarial.** I did not confirm CC-2's design. I attacked
> its strongest negative (NR-2 = N-1 + N-2 + N-3) one hop past where the author
> stopped, re-ran every load-bearing grep own-hands against `origin/main` (never the
> divergent local tree), and report each return including nulls. The negative
> **survives**, but N-1 narrows materially and I surface three refuters the author
> did not name. The `(f)+(a)` recommendation and the named owners **hold**; `(a)` is
> **repriced** by a finding the author's slate did not carry.

## 0. Stale-tree hazard was real — the fence earned its keep

`autom8y-asana` local HEAD `4129ae7e` lags `origin/main = d7560153` by 12 commits;
the `autom8y` monorepo local tree is 158-behind / 70-ahead of `origin/main = 07819b39`.
Both cited bases match the design's frontmatter exactly. A local-tree `find` for
`authz.py` returned nothing (the file lives at a divergent path locally). **Every
finding below is `git show origin/main:` / `git grep origin/main`.** A stale-tree
"absence" would have been worthless; I did not rely on one.

## 1. Refuter (a) — was EVERY load-bearing grep run against origin/main?

**Disposition: MOSTLY YES; one receipt used the installed venv, re-grounded here.**

| Design claim | Design's ref | My own-hands re-run @ origin/main | Result |
|---|---|---|---|
| N-1 taxonomy | `authz.py:22-35` | `git show origin/main:services/auth/autom8y_auth_server/schemas/authz.py` | 14-entry `SCOPE_TO_RELATION`, **no `asana:` key** — reproduced |
| N-2 zero-hit | `git grep origin/main -- src/ tests/` | re-ran verbatim | **exit 1, zero hits** — reproduced |
| §1.2 two-hit | `git grep '.permissions' origin/main -- src/` | re-ran | exactly `admin.py:456` (decision) + `internal.py:161` (populate); `has_*` only `admin.py:36` (comment) — reproduced |
| N-5 gateway | grep spec | `git show origin/main:services/api-gateway/specs/asana.openapi.json` | `x-fleet-scope-required` count **0** (data=12, scheduling=7, sms=1) — reproduced |
| N-6 consumers | monorepo grep | re-ran | all hits are SDK/client **definitions + docstrings**, zero production call sites — reproduced |
| §2.2 `extra=ignore` | `grep .venv/.../claims.py` **(NOT origin/main)** | re-grounded → `origin/main:sdks/python/autom8y-auth/src/autom8y_auth/claims.py:162` | `model_config = {"extra": "ignore"}` present — **matches; venv ≈ origin/main** |

**Minor SVR-hygiene flag (non-material):** the §2.2 receipt cited the installed
`.venv` SDK, not an `origin/main` ref. I re-derived the equivalent against the
monorepo SDK source at `origin/main` and it agrees, so no substance moves — but per
the NR-2 fence the receipt itself should have been an `origin/main` read. Flag, not
a fall.

## 2. Refuter (b) — does an asana scope vocabulary exist under a different spelling? **YES — and it drives the N-1 NARROWS**

This is the productive refuter. The asana scope namespace is **not absent from the
minting layer** — it is present-but-unmapped, and one arm of it is **live-provisioned**.

```yaml
structural_verification_receipt:
  claim: >-
    the fleet already provisions a live OAuth-client identity (autom8y-hermes)
    carrying an asana:read scope via terraform, so the asana scope namespace is
    partially live at the minting layer despite being absent from SCOPE_TO_RELATION
  verification_method: file-read
  verification_anchor:
    source: "git show origin/main:terraform/services/auth/main.tf"
    line_range: "L1576-L1584"
    marker_token: "service_name = \"autom8y-hermes\""
    claim: >-
      the module block oauth_clients_hermes is live IaC (not a dead script) that
      registers autom8y-hermes with scopes "data:read asana:read"
```

Own-hands returns (all `origin/main`):
- `terraform/services/auth/main.tf:1581` → `scopes = "data:read asana:read"` inside a live `module "oauth_clients_hermes"` block. **`asana:read` is a provisioned fleet scope.**
- `services/auth/scripts/register_autom8y_hermes.sh:53` → `readonly SCOPES="data:read asana:read"`.
- `services/auth/tests/test_token_service_exchange_business.py:745` → `scopes=("asana:read", "asana:write")`. **`asana:write` already circulates in the token-exchange surface.**
- OAuth scope validation is `validate_scopes(client, requested)` = intersection with **`client.allowed_scopes`** (`services/auth/autom8y_auth_server/services/authorization_code_service.py:51`), **NOT** an intersection with `CANONICAL_SCOPES`. So an asana scope is grantable to a client without ever appearing in `SCOPE_TO_RELATION`.
- **OpenFGA relation for asana write: NULL.** `git grep -i asana origin/main -- '*model.fga' '*authz*' '*scope*'` returns only `.ledge/` document hits — no `model.fga` relation, no tuple. The write capability is **not** expressed as an OpenFGA relation under any spelling.

**What this does to N-1.** N-1's *precise* falsifier ("any `asana:`-prefixed key in
`SCOPE_TO_RELATION`") **STANDS** — no such key exists. But NR-2 as the author stated
it to me — *"no `asana:*` write scope exists at the minting layer"* — **NARROWS**:
the asana scope *namespace* is nascent-and-unmapped (asana:read provisioned live;
asana:write in the exchange-test vocabulary), not absent. **Corrected scope:** *"No
asana scope is mapped to an OpenFGA relation, and no identity is granted `asana:write`
today; but `asana:read` is already provisioned on a live OAuth-client identity and
`asana:write` already circulates in the exchange surface — the vocabulary is partial
and unmapped, not greenfield."*

## 3. Refuter (c) — is there authorization by ANOTHER existing mechanism? **NO existing partial gate found in the two repos; network layer remains unresolved**

The claim most likely to be too strong is N-3. I attacked it three ways:
- **App middleware (asana):** `git grep add_middleware|BaseHTTPMiddleware|authorizer|cognito|waf origin/main -- src/ terraform/` → only `SecurityHeadersMiddleware`, `RequestIDMiddleware`, `RequestLoggingMiddleware`, `IdempotencyMiddleware`, `MetricsMiddleware`. **None authorize.** No authorizer / WAF / cognito in `src/` or the in-repo `terraform/`.
- **Gateway (monorepo):** N-5 held own-hands — 0 asana gated ops, and 4 of the 5 write classes (`receipts`, `intake/business`, `custom-fields`, `entity/`) are **absent from the asana openapi spec entirely** (0 hits each). The live fail-closed `AuthzMiddleware` fabric CORRECTION-1 describes provides **zero** authz over the asana write surface.
- **OpenFGA:** no asana relation/tuple (refuter b).

The **network layer** (ALB listener rule / WAF / SG fronting `asana.api.autom8y.io`)
is NOT readable in either repo — it lives in the external `a8 stacks/service-stateless`
module the design flags as un-checked-out. The design correctly carries this as
**UV-P-2 / UV-P-4 (SEC-003, CC-3)**.

**N-3 verdict: STANDS, NARROWED.** "CR-1 is the only control" survives as *"the only
authorization control over the asana write surface VISIBLE at the application and
gateway layers of the two repos read own-hands."* It is **not** a proof that the
network layer is clear — and the design does not claim it is. No existing partial
gate falsifies it.

## 4. Refuter (d) — is the gap a call-site OMISSION of a mechanism already applicable? **YES — this CORROBORATES (f), does not refute**

`admin.py:456` gates via `if SUPER_ADMIN_PERMISSION not in claims.permissions` — a
**direct in-process membership test on the claims object**, NOT an SDK `has_permission`
call. That exact mechanism is trivially applicable to the write routes
(`if caller ∉ allowlist → 403`). Own-hands confirms **zero** production
`has_scope`/`has_permission`/`require_*` call sites in asana `src/` (the sole hit is
the `admin.py:36` comment). So the gap is a **call-site omission of an in-process
check the codebase already performs one line away**, not an absent capability. This
**inverts toward option (f)** and corroborates the design's own recommendation. Not
a refutation.

## 5. Nulls re-derived own-hands — N-4 and N-6

**N-4 — no SA carries wildcard `*`. HELD own-hands (load-bearing).**
```yaml
structural_verification_receipt:
  claim: >-
    no service account or OAuth client is granted a wildcard * scope, and the SDK
    has_scope() short-circuits to True on scope == "*", so the null is the only
    thing standing between option (a) and a silent universal bypass
  verification_method: bash-probe
  verification_anchor:
    source: "git show origin/main:services/auth/service-accounts.yaml | grep -E '^\\s*-\\s*[\"\\x27]?\\*[\"\\x27]?\\s*$'"
    command_output_verbatim: "exit=1 (no match)"
    exit_code: 1
    claim: >-
      zero wildcard scope grants exist in the registry today; combined with the SDK
      shortcut this is a standing assertion option (a) must convert into a test
```
- Wildcard grant: **exit 1, none** (re-run at `origin/main`).
- SDK behavior confirmed own-hands: `origin/main:sdks/python/autom8y-auth/src/autom8y_auth/claims.py:227` `has_scope` → `if self.scope == "*": return True`. The null's load-bearing rationale is CONFIRMED — one wildcard edit would silently defeat (a). **N-4 holds; the hazard it guards is real.**
- **Added observation:** `_dev_bypass_service_claims()` returns `ServiceClaims(scope="*")` under `dev_mode` (`client.py:583`). Dev-only, production-guarded — but if `dev_mode` ever leaks to a deployed environment, every `has_scope` returns True. Note for CC-3, not a production defect.

**N-6 — no fleet service consumes scopes at any production call site. HELD own-hands.**
Every `has_scope(`/`require_scope(`/`require_permission(` hit across the monorepo at
`origin/main` is an SDK/client **definition** (`sdks/python/autom8y-auth/.../dependencies.py`,
`.../claims.py`, `services/auth/client/.../middleware.py:240`) or a **docstring
example** — **zero production consumer call sites.** The gateway path enforces via
OpenFGA, not via in-service `has_scope`. So option (a)'s in-service half would indeed
be the fleet's **first** production scope-check call site. **N-6 holds; the repricing
it implies for (a) is correct.**

## 6. Added refuters the author did not name

**AR-1 — the "granted scopes ⊆ 14 canonical" sub-claim is FALSE own-hands.**
N-1 asserts *"the 10 scope values actually granted across all 18 SAs ... are a subset
of these [14 canonical]."* Own-hands, the distinct granted scopes in
`origin/main:services/auth/service-accounts.yaml` include **`query:read`** and
**`read:pii`** — neither is in `SCOPE_TO_RELATION`, and `read:pii` even inverts the
declared `<domain>:<verb>` convention. The registry grants scopes outside the
canonical dict. This is collateral to NR-2's core but **corroborates the N-1 NARROWS**:
`SCOPE_TO_RELATION` is not the minting layer's actual granted vocabulary.

**AR-2 — two minting substrates for the same logical identity, with divergent asana
posture.** The `iris` SA (`service-accounts.yaml`, "Deployed as hermes-agent
(autom8y-hermes)") carries **no** asana scope; the OAuth-client terraform
(`module oauth_clients_hermes`) grants the **same** logical identity `asana:read`.
The design's blast-radius analysis (§1.5, "18 service accounts") examined **only** the
SA-registry path. OAuth-client identities are a **second, uncounted population** that
also carries asana scope. This does not refute NR-2, but it **widens the reachable
surface beyond the design's 18** and is a cross-repo coupling the (a) remediation must
reconcile (see §8).

**AR-3 — UV-P-3 is not merely an open question; its structural half is CONFIRMED
own-hands, and it further widens blast radius.** See §7.

## 7. UV-P-3 disposition — PARTIALLY DISCHARGED own-hands (author deferred the whole question)

The author flagged UV-P-3 (could an `agent_access` token be parsed as `ServiceClaims`,
which declares no `token_type` discriminator?) and deferred it **entirely** to CC-3 as
needing a live token. Reading the `origin/main` SDK, **the structural half is
confirmable statically, and it confirms the hazard:**

```yaml
structural_verification_receipt:
  claim: >-
    the SDK selects the claims species by structural shape, and the SERVICE species
    is an unguarded catch-all else with no token_type allowlist, so a token that is
    neither operator-shaped nor user-shaped is parsed as a ServiceClaims regardless
    of its token_type value
  verification_method: file-read
  verification_anchor:
    source: "git show origin/main:sdks/python/autom8y-auth/src/autom8y_auth/client.py"
    line_range: "L476-L489"
    marker_token: "else:\n            return ServiceClaims.model_validate(claims_dict)"
    claim: >-
      the require_access_token_type gate that asserts token_type == user_access lives
      ONLY inside the TokenType.USER branch; the SERVICE branch has no equivalent
      assertion, so agent_access is not rejected — it is silently reclassified
```

Trace: `detect_token_type` (`origin/main:sdks/python/autom8y-auth/src/autom8y_auth/_detection.py`)
returns OPERATOR only if `token_type == "operator_access"`, USER only if
`business_id AND roles AND token_type` are all present, and **falls through to
`return TokenType.SERVICE`** otherwise. An `agent_access` token carries `scope` (not
`roles`), so `has_roles` is False → it is classified SERVICE → parsed as
`ServiceClaims` via the catch-all `else`. `extra="ignore"` (`claims.py:162`) then
drops `act.sub` and the `token_type` marker silently. The asana door adds nothing
here — its local `validate_service_token` (`src/autom8_asana/auth/jwt_validator.py:62`,
`origin/main`) delegates entirely to the SDK per ADR-S2S-001.

**Disposition: UV-P-3 structural half CONFIRMED (species dispatch is an unguarded
catch-all; no `token_type == "service"` assertion on the service branch;
`extra=ignore` erases the delegation marker). The remaining half — whether an
`agent_access` token carries `aud = https://api.autom8y.io` and whether an agent seat
can mint one — is CR-5/SEC-002 and I did not touch a credential.** HAND OFF to CC-3's
penetration-tester with a **sharpened** target: the parse behavior no longer needs
confirming; only audience + mintability remain.

**Consequence for the design:** AR-3 widens §1.5's blast radius — the reachable
identity set is potentially **broader than the 18 SAs** (any fleet principal whose
token is neither operator- nor user-shaped and carries the fleet audience). Beneficial
interaction: option **(f)'s `caller_service` allowlist fail-closes on a confused agent
token** — a mis-parsed `agent_access` token's `sub` is a `user_id`, which is not in a
service allowlist → 403. So (f) partially mitigates AR-3 as a side effect; (a) with a
widened claim model that carries `token_type` would close it directly.

## 8. Do the recommendation and the named owners survive?

**(f) in-repo `caller_service` allowlist — SURVIVES, STRENGTHENED.** Refuter (d)
corroborates it (the mechanism is already in the codebase at `admin.py:456`); AR-3
shows it also fail-closes token-species confusion. One PR, one repo, no upstream
dependency — the design's pricing holds own-hands (no CODEOWNERS gate in this repo;
see below).

**(a) scope-vocab + `has_scope` — SURVIVES, but REPRICED.** The design frames (a) as
inventing a vocabulary and prices its hidden cost as "widen the local claim model to
carry `scopes`; refuse the `*` wildcard." Own-hands, that pricing is **necessary but
incomplete**: (i) the asana vocabulary is **already partially live** (asana:read
provisioned, asana:write in exchange tests) — so (a) is a *formalize + map* job, not a
greenfield mint; (ii) (a) must **reconcile two minting substrates** (SA-registry +
OAuth-clients, AR-2) or the grant will be inconsistent across identity paths; (iii)
`asana:write` must be added to `SCOPE_TO_RELATION` **and** the OpenFGA model for the
gateway/delegation halves to enforce it — the design's own §3(a) "OpenFGA model change
is the expensive part" is right, but the reconciliation surface is larger than one
migration. This is a **NARROWS/amend on (a)**, not a rejection.

**(d) ratify CR-1 and (e) gateway defense-in-depth — untouched by my sweep;** N-5
holds, so (e)'s "structurally blind to 4 of 5 classes" blocker is confirmed own-hands.

**Named owners — HOLD own-hands.**
- Monorepo L1/L3: `git show origin/main:CODEOWNERS` (autom8y) → `* @autom8y/platform-team` (L9) + `/terraform/ @autom8y/platform-team` (L12). **Confirmed.** The OAuth-client asana grant (AR-2) lives under `terraform/services/auth/` → also platform-team, consistent with the design's L1 owner.
- asana L2: **no CODEOWNERS anywhere in `autom8y-asana` at `origin/main`** (`git cat-file -e` → ABSENT for `CODEOWNERS`, `.github/CODEOWNERS`, `docs/CODEOWNERS`; tree scan → none). Merge authority operator-only under F-4. **Confirmed.**
- The design's "no single owner spans both layers — that is itself a finding" **holds**, and AR-2 sharpens it: the asana scope namespace is already split across two platform-team-owned substrates with no asana reconciliation, so the coordination gap is wider than the design states.

## 9. Verdicts (grammar: STANDS / FALLS / NARROWS)

| Claim | Verdict | Concrete hop |
|---|---|---|
| **NR-2 (composite)** | **STANDS, with N-1 NARROWED** | The write door performs no write-class authorization and no technical control gates it in-code — survives intact own-hands; the narrowing sharpens rather than rescues |
| N-1 (no asana:* write scope at minting layer) | **NARROWS** | Literal `SCOPE_TO_RELATION` falsifier STANDS; broad framing narrows — `asana:read` live-provisioned (`main.tf:1581`), `asana:write` in exchange tests (`test_token_service_exchange_business.py:745`), `validate_scopes` intersects `client.allowed_scopes` not `CANONICAL_SCOPES` |
| N-2 (no acting_agent/delegating_user on service claim surface) | **STANDS** | `git grep -w origin/main -- src/ tests/` → exit 1, zero hits (re-run own-hands) |
| N-3 (CR-1 is the ONLY control) | **STANDS, NARROWED** | Confirmed at app + gateway layer (no auth middleware; 0 asana gated ops; two-hit `.permissions`); network layer unresolved (UV-P-2), not proven — scope narrowed to controls visible in the two repos |
| N-4 (no wildcard `*` scope) | **HELD** | exit 1 own-hands; SDK `has_scope` wildcard shortcut confirmed (`claims.py:227`) — hazard real |
| N-6 (no production scope consumer) | **HELD** | all `has_scope`/`require_*` hits are SDK/client defs + docstrings; zero call sites |
| UV-P-3 | **PARTIALLY DISCHARGED → CC-3** | structural half CONFIRMED own-hands (`client.py:476-489` catch-all `else`; `_detection.py` SERVICE fall-through; `extra=ignore`); audience+mintability → penetration-tester |
| (f) recommendation | **SURVIVES, strengthened** | refuter (d) corroborates; AR-3 fail-close side effect |
| (a) recommendation | **SURVIVES, repriced** | refuter (b)/AR-1/AR-2 → formalize-not-mint + two-substrate reconciliation |
| Named owners (§5) | **HOLD** | monorepo `* @autom8y/platform-team`; asana no CODEOWNERS (F-4) — both own-hands |

**Does "CR-1 is the only control" survive?** **Yes**, narrowed to the application and
gateway layers visible in the two repos. No existing partial gate falsifies it; the
network-layer question is genuinely open (the design carries it). **Do (f)+(a) and the
named owners survive my attack?** **Yes** — (f) strengthened, (a) repriced (not
rejected), owners confirmed.

## 10. Fences honored
- **CR-1** — no Asana write path exercised; every conclusion is static read of `origin/main`.
- **CR-5** — no credential material read; `ASANA_PAT`/`ASANA_PAT_ARN` and the admin-token SSM parameter referenced as names only. UV-P-3's remaining half deliberately NOT probed (would require a live token).
- **CR-2** — verdicts bucket untouched.
- **origin/main only** — the divergent local `autom8y` monorepo tree was never read; every monorepo citation is `git show origin/main:` / `git grep origin/main`.
- **No AWS call, no git verb** — none fired. This receipt rests AUTHORED-UNMERGED; the main thread owns git.
- **Evidence ceiling MODERATE** — legs I re-derived own-hands are external corroboration for those legs, but I grade the **negative's survival**, not CC-2's design correctness.
