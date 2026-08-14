---
type: review
artifact_id: PROBE-re2-blast-radius-2026-08-13
schema_version: "1.0"
rite: security
agent: penetration-tester
wave: chain-of-custody-closure
station: CC-3
initiative: exec-insight-delivery
created_at: "2026-08-13"
upstream: .ledge/handoffs/HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13.md
resolves: [SEC-002, SEC-003]
state: AUTHORED-UNMERGED
status: complete
self_assessment_cap: MODERATE
evidence_grade: STRONG (infrastructure legs, own-hands AWS + code reads)
ncsr_second_reader: platform-engineer (sre) — rite-disjoint, NR-3 second-read PENDING
---

# PROBE — RE-2 blast radius: UV-P-C-1 and UV-P-C-2 dispositions

**Terminal state this wave (F-A / Q-4 HALT):** this artifact rests
authored-unmerged. It is not written as though merge follows.

**Self-assessment capped MODERATE (F-C)** on the *judgement* layer (severity
calls, remediation shape). The *infrastructure* layer below is STRONG: every
AWS and code claim carries an own-hands command + exit code, re-runnable by the
NR-3 second reader.

**CR-5 compliance statement.** No credential was minted, extracted, copied,
decoded, or logged. No secret value was read. Where a credential is named it is
named by **env key** or **Secrets Manager path** only. The one probe that could
have required handling credential material (minting a service JWT) was
**deliberately not executed** — see §1.4. Reachability was established instead by
`iam simulate-principal-policy`, which returns an authorization decision and
**no material**.

---

## §0 Bottom line

Both UV-Ps are **CLOSED WITH RECEIPT**. Both close in the **adverse** direction.

| UV-P | Question | Disposition | Direction |
|---|---|---|---|
| UV-P-C-1 | Can an agent seat obtain a fleet service JWT clearing `require_service_claims`? | **CLOSED — YES** | adverse |
| UV-P-C-1 | Is any agent-seat runtime env injected with such a credential today? | **CLOSED — NO** (service-JWT creds), **but YES for the target credential itself** | adverse, by a shorter path |
| UV-P-C-2 | Is the ALB internal-only? | **CLOSED — NO. Internet-facing.** | adverse |
| UV-P-C-2 | What SG/WAF sits in front of priority 120? | **CLOSED — SG `0.0.0.0/0` on 443; WAF: none exists in the account.** | adverse |

**The code-side finding's blast radius is NOT bounded. It is wider than the
handoff's framing.** The handoff scoped the question to "can a fleet service
token be obtained." The receipts below show the S2S gap is not the narrowest
path to the impact: the interactive agent seat is handed the **shared bot Asana
credential directly**, and the write surface sits on a **public internet
endpoint with no WAF**.

---

## §1 UV-P-C-1 — CLOSED WITH RECEIPT

> Original: `RAILS-insight-delivery-verified-2026-08-12.md:944`

### 1.1 Q1 — "can an agent seat obtain a service JWT that clears `require_service_claims`?" → **YES**

The affirmative rests on three independently-receipted conjuncts. No conjunct is
inferred.

**Conjunct A — the audience check cannot discriminate between services.**

`FLEET_AUDIENCE` is a single fleet-wide constant. The audience `require_service_claims`
enforces is the audience *every* fleet service token carries.

```
verification_method: file-read
source: .venv/lib/python3.12/site-packages/autom8y_auth/constants.py
line_range: L12
marker_token: 'FLEET_AUDIENCE: str = "https://api.autom8y.io"'
claim: the audience asserted at the asana S2S boundary is a fleet-wide constant,
       so audience verification partitions fleet-vs-non-fleet and performs zero
       service-vs-service discrimination
```
Command: `grep -rn "FLEET_AUDIENCE" .venv/.../autom8y_auth/constants.py` — exit 0.

Call site pinned at `src/autom8_asana/auth/jwt_validator.py:83`:
`client.validate_service_token(token, audience="https://api.autom8y.io")`.

**Conjunct B — no scope, no service allowlist, no revocation check downstream of it.**

`require_service_claims` (`api/routes/internal.py:83-162`) — read own-hands, full
body — validates token-type then delegates to `validate_service_token`, then
**returns** `ServiceClaims(...)`. There is no `has_scope`, no `has_permission`, no
`service_name` allowlist between validation and return. This **CONFIRMS** the
handoff §1b finding.

Additionally, and **not** noted in the handoff: the SDK signature is
`validate_service_token(self, token, *, audience=FLEET_AUDIENCE, check_revocation: bool = False)`
(`autom8y_auth/client.py:288-294`). The asana call site passes **only** `audience`.
Therefore `check_revocation=False` — **a revoked service token still authorizes an
Asana write at this boundary.** See F-004.

**Conjunct C — the minting credential is reachable from this agent seat.**

The documented issuance pattern is `client_id` + `client_secret` → HTTP Basic →
`POST {auth_url}/tokens/exchange-business`
(`autom8y_auth/token_manager.py:340-390`, `client_config.py:57-115`;
`auth_url` default `https://auth.api.autom8y.io`).

The fleet's client secrets live in Secrets Manager under one prefix. **30**
service-api-key secrets exist, including the two AI-agent seats:

```
autom8y/auth/service-api-keys/ace-service
autom8y/auth/service-api-keys/iris-service
autom8y/auth/service-api-keys/asana-service
… (27 more)
```
Command: `aws secretsmanager list-secrets --query 'SecretList[].Name'` — exit 0
(188 secrets in account; 30 matched `service-api-key`).

This agent seat's AWS principal is **ALLOWED** to read them:

```
verification_method: bash-probe
source: aws iam simulate-principal-policy
        --policy-source-arn arn:aws:iam::696318035277:role/AWSReservedSSO_AdministratorAccess_072d916d21d2219c
        --action-names secretsmanager:GetSecretValue
        --resource-arns <ace-service> <iris-service> <asana-pat>
command_output_verbatim: "action: secretsmanager:GetSecretValue | decision: allowed"
exit_code: 0
claim: the AWS principal under which this agent seat executes is authorized to
       retrieve the fleet's token-minting client secrets; no operator step
       stands between the seat and the minting credential
```

The seat inherits the operator's SSO **AdministratorAccess** role — receipted at
`aws sts get-caller-identity` (exit 0), ARN
`…assumed-role/AWSReservedSSO_AdministratorAccess_072d916d21d2219c/tomtenuta`.

**A ∧ B ∧ C ⇒ YES.** An agent seat can read any fleet service's client secret,
exchange it by the documented pattern for a token bearing the fleet audience,
and that token clears `require_service_claims` — which then lends it the shared
bot Asana credential for any write class.

### 1.2 The sharpest formulation — read-only agent scoping is nullified here

`ace` and `iris` are declared **AI agent** service accounts whose scopes are
**entirely read-only**:

- `ace` (`service-accounts.yaml:42-56`): `data:read, analytics:read, scheduling:read, sms:read, ads:read`
- `iris` (`:310-323`): `scheduling:read, data:read, analytics:read, sms:read, ads:read`
  — *"All scopes are read-only."*

Because `require_service_claims` never inspects scope, **a token whose every
declared scope is read-only authorizes every Asana write class.** The fleet's
deliberate read-only posture for AI agent seats — with a named approver and a
documented exemption rationale — is **void at this boundary**.

The fleet scope vocabulary has **no Asana write scope to check even if the check
were added**. Distinct scope tokens across the entire registry:

```
ads:read  analytics:read  data:read  data:write  query:read
read:pii  scheduling:read scheduling:write  sms:read  sms:send
```
Command: `grep -cE "asana:(write|create|update|delete)" service-accounts.yaml` →
**0**, exit 1. This **CONFIRMS** the handoff §1b two-layer remediation claim,
own-hands.

### 1.3 Q2 — "is any agent-seat runtime env injected with one TODAY?"

**For a service JWT / its client credentials: NO — receipted, not inferred.**

Explicit presence test on this seat (key names and booleans only; no value read):

```
AUTOM8Y_DATA_SERVICE_CLIENT_ID     = ABSENT
AUTOM8Y_DATA_SERVICE_CLIENT_SECRET = ABSENT
CLIENT_ID                          = ABSENT
CLIENT_SECRET                      = ABSENT
AUTOM8Y_AUTH_URL                   = ABSENT
```
Command: `for K in …; do printenv "$K" >/dev/null 2>&1 && echo PRESENT || echo ABSENT; done` — exit 0.
Key-name set derived own-hands from `autom8y_auth/client_config.py:87-92` (the
canonical/legacy dual-lookup), not guessed.

**But the seat holds the target credential directly — the JWT is unnecessary.**

```
ASANA_PAT      = PRESENT
TF_VAR_asana_pat = PRESENT   (bridged form)
ASANA_USER_PAT = PRESENT
```
Command: `printenv ASANA_PAT >/dev/null 2>&1` — **PRESENT**. Value **not read**
(CR-5). 138 env vars in seat; the credential-shaped key names also include
`AUTOM8Y_META_*`, `*_SLACK_BOT_TOKEN`, `CLOUDFLARE_API_TOKEN`, `GRAFANA_AUTH`,
`UV_INDEX_AUTOM8Y_PASSWORD`.

`ASANA_PAT` is **exactly the key the service reads for the shared bot
credential** — `src/autom8_asana/auth/bot_pat.py:75`
(`resolve_secret_from_env("ASANA_PAT")`). Same key name, own-hands.

**Injection path (checked-in, no operator step at probe time):**
`/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.envrc` (git-TRACKED), final two lines:
`use autom8y --no-tf` then
`autom8y_tf_bridge_all "ASANA_PAT:asana_pat" "ASANA_WORKSPACE_GID:asana_workspace_gid"`.
Any seat whose cwd is inside this repo with direnv allowed receives it automatically.

**This directly contradicts the codebase's own guard.** `bot_pat.py:108-136`
implements a caller-startup guard (H5/V6) that **halts** a caller context holding
a bare `ASANA_PAT`, with the verbatim rationale that callers must
*"resolve the secret via ASANA_PAT_ARN brokerage and use a short-lived S2S"*
token and *"NEVER carry the plaintext PAT in its own environment."* The Lambda
plane obeys this (§3 positive P-2). The interactive agent seat does not.

[UV-P: whether the `ASANA_PAT` value in this seat's env is byte-identical to the
production bot credential at `autom8y/asana/asana-pat` | METHOD: compare secret
values | REASON: comparison requires reading credential material — CR-5 refuses
it. Key-name identity and injection path are receipted; value identity is NOT.
This UV-P does not weaken any finding: the seat holds *an* Asana PAT with write
reach either way.]

### 1.4 What was deliberately NOT executed

- **No service JWT was minted.** Executing `/tokens/exchange-business` would
  produce credential material in this seat — CR-5 refuses it. Conjuncts A/B/C are
  independently receipted, so the conjunction stands without the terminal mint.
- **No Asana write path was exercised** — CR-1. No POST/PUT/PATCH/DELETE was sent
  to any route, authenticated or not. Only `GET` on `/health`, `/redoc`,
  `/docs`, `/openapi.json`.
- **`s3://autom8y-asr-verdicts` was neither read nor listed** — CR-2.
- **Nothing in AWS or terraform was mutated** — L4. Every AWS call was
  `describe-*`, `list-*`, `get-*-configuration`, or `simulate-*`.

---

## §2 UV-P-C-2 — CLOSED WITH RECEIPT

> Original: `RAILS-insight-delivery-verified-2026-08-12.md:945`

### 2.1 The listener is INTERNET-FACING. Not internal.

The handoff correctly refused to infer from private-subnet placement. The direct
read disposes of it:

```
verification_method: bash-probe
source: aws elbv2 describe-load-balancers --names autom8-prod-alb
        --query 'LoadBalancers[0].[LoadBalancerName,Scheme,Type,DNSName,SecurityGroups]'
command_output_verbatim: ["autom8-prod-alb","internet-facing","application",
                          "autom8-prod-alb-1056534770.us-east-1.elb.amazonaws.com",
                          ["sg-0c189d96413dca1c1"]]
exit_code: 0
claim: the shared platform ALB carrying the asana listener rule is scheme
       internet-facing; the private-subnet placement of the ECS tasks does not
       make the ingress internal
```

**All 6 ALBs in the account are `internet-facing`.** There is no internal ALB.
Command: `aws elbv2 describe-load-balancers` — exit 0.

### 2.2 Priority 120 confirmed as the asana rule — matched, not assumed

```
verification_method: bash-probe
source: aws elbv2 describe-rules --listener-arn <autom8-prod-alb :443>
command_output_verbatim: Priority "120" | Conditions: host-header =
  ["asana.api.autom8y.io"] | Actions: forward -> targetgroup/autom8y-asana-service
  (weight 100), targetgroup/a8-asana-green (weight 0)
exit_code: 0
claim: listener_rule_priority 120 on the prod ALB's HTTPS listener is the asana
       service rule, forwarding to the autom8y-asana-service target group
```

**Load-bearing detail:** the rule's **only** condition is `host-header`. There is
**no path-pattern condition**. Every path on that host — including the
`include_in_schema=False` S2S write routes — is reachable through this rule.
There is no route-level segmentation at the ALB, matching the handoff's
"one FastAPI app / one target group" observation.

### 2.3 SG: open to the entire internet on 443

```
verification_method: bash-probe
source: aws ec2 describe-security-groups --group-ids sg-0c189d96413dca1c1
command_output_verbatim: name=autom8-prod-alb-sg
  ingress tcp 80-80   cidr 0.0.0.0/0 "HTTP access for prod environment"
  ingress tcp 443-443 cidr 0.0.0.0/0 "HTTPS access for prod environment"
exit_code: 0
claim: the security group in front of listener_rule_priority 120 permits ingress
       from any source address on 443; it applies no network-origin restriction
```

### 2.4 WAF: none. Not "not found" — none exists.

```
verification_method: bash-probe
source: aws wafv2 get-web-acl-for-resource --resource-arn <autom8-prod-alb>
command_output_verbatim: "" (empty body — no WebACL associated)
exit_code: 0

source: aws wafv2 list-web-acls --scope REGIONAL --region us-east-1
command_output_verbatim: {"WebACLs": []}
exit_code: 0

source: aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1
command_output_verbatim: {"WebACLs": []}
exit_code: 0
claim: no WAF sits in front of priority 120, and the absence is not local to
       this ALB — zero WAFv2 web ACLs exist in the account at either scope
```

This is a **stated absence backed by an executed probe**, not an unattempted one.

### 2.5 Reachability corroborated end-to-end

```
dig +short asana.api.autom8y.io
  -> autom8-prod-alb-1056534770.us-east-1.elb.amazonaws.com. / 52.72.135.15 / 107.20.73.158   (exit 0)

curl -sS -o /dev/null -w '%{http_code}' https://asana.api.autom8y.io/health
  -> http_code=200  remote_ip=107.20.73.158  ssl_verify=0                                      (exit 0)
```
Public DNS, public IPs, unauthenticated 200 from an arbitrary host. No credential
was sent on this request.

---

## §3 Findings

Severity per `severity-taxonomy.lego.md §Bug Bar`; CWE/OWASP binding per
`coverage-matrix.lego.md`. Exploitability is noted separately from severity per
the exploitability≠severity rule.

### F-001 — Read-only agent-seat tokens authorize all Asana write classes

**Severity**: Bug Bar level 1 (Critical) per severity-taxonomy §Bug Bar.
**CWE**: CWE-862 (Missing Authorization) — `owasp_category: A01` per coverage-matrix §A01.
**Affected**: `src/autom8_asana/api/routes/internal.py:83-162`;
`src/autom8_asana/auth/jwt_validator.py:83`.

**Repro (non-weaponized).**
1. Read `constants.py:12` — confirm `FLEET_AUDIENCE` is one shared fleet value.
2. Read `internal.py:83-162` — confirm no `has_scope`/`has_permission`/service
   allowlist between validation and `return ServiceClaims(...)`.
3. Read `service-accounts.yaml` `ace`/`iris` — confirm scopes are all `*:read`.
4. Observe: a token minted for a read-only agent seat satisfies every check the
   write routes perform. No write need be issued to establish this.

**Impact.** Any holder of any fleet service credential — including the two
cross-tenant AI agent seats whose approved posture is read-only — can create,
update and delete Asana objects using the shared bot credential. `caller_service`
is captured but log-only, so post-hoc attribution exists while prevention does not.

**Remediation** (two-layer; layer 1 is upstream and must land first):
1. **`autom8y-auth`** — mint an Asana write vocabulary in `service-accounts.yaml`
   (e.g. `asana:write`, or per-class `asana:comment:write` / `asana:task:write` /
   `asana:field:write`). Grant to no seat by default. `ace` and `iris` MUST NOT
   receive it — their exemption rationale explicitly claims read-only.
2. **`autom8y-asana`** — enforce at each write route. The pattern already exists
   in-repo at `api/routes/admin.py:456`; apply it to writes:
   ```python
   # after require_service_claims returns
   if "asana:write" not in claims.scope:
       raise ApiAuthError("INSUFFICIENT_SCOPE", "asana:write required")
   ```
3. Pass `check_revocation=True` at `jwt_validator.py:83` (see F-004).
4. Until (1)+(2) land, CR-1 remains the only control — and CR-1 is a process
   fence that binds agents, not network callers. See F-002.

### F-002 — The gated surface is internet-facing with no WAF

**Severity**: Bug Bar level 2 (Important) per severity-taxonomy §Bug Bar —
raised in real-world urgency by F-001 (per §SSVC, a working authorization bypass
on an internet-exposed asset elevates urgency above its base score).
**CWE**: CWE-668 (Exposure of Resource to Wrong Sphere) — `owasp_category: A05`.
**Affected**: `autom8-prod-alb` rule priority 120; `sg-0c189d96413dca1c1`.

**Impact.** F-001's precondition is "hold a fleet credential." F-002 removes
every *network* barrier to using one: no IP allowlist, no WAF, no internal-only
boundary, no path segmentation at the rule. A leaked service credential is
exploitable from anywhere on the internet, with no rate-based or signature-based
control in path.

**Remediation.**
1. Attach a WAFv2 web ACL to `autom8-prod-alb` (none exists in the account —
   this is greenfield, not a tuning change). Minimum: AWS managed common rule
   set + a rate-based rule on the write paths.
2. Narrow `autom8y-asana-service`'s ingress: if the service is
   service-to-service only, add a path-pattern condition to rule 120 restricting
   internal route trees, or move S2S routes behind an internal ALB / VPC
   endpoint / PrivateLink and leave only genuinely public routes on 120.
3. Do **not** rely on `include_in_schema=False` as a control (see F-005).

### F-003 — Interactive agent seat carries the bare bot PAT, contradicting the repo's own guard

**Severity**: Bug Bar level 2 (Important) per severity-taxonomy §Bug Bar.
**CWE**: CWE-522 (Insufficiently Protected Credentials) — `owasp_category: A07`.
**Affected**: `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.envrc` (git-tracked,
final line); contrast `src/autom8_asana/auth/bot_pat.py:108-136`.

**Impact.** The S2S authorization gap is not the shortest path from an agent seat
to an Asana write — the seat is handed the write credential directly by a
checked-in file. Any process in that shell (including any tool an agent invokes)
inherits it. CR-1 is a *process* fence; it does not remove the capability.

**Remediation.**
1. Change `.envrc` to bridge `ASANA_PAT_ARN` rather than `ASANA_PAT`, matching
   the Lambda plane (§3 P-2) and the stated intent of the `bot_pat.py:108-136`
   guard. Local tooling resolves through the ARN at point of use.
2. Extend the H5/V6 caller-startup guard to fire in developer/agent contexts, not
   only the service caller image — today the guard's own invariant is violated in
   the one context it cannot see.
3. Treat the currently-injected PAT as exposed-by-breadth and rotate on the same
   ticket as the known history exposure (`.know/defer-watch.yaml:382-403`).

### F-004 — Revoked service tokens still authorize writes

**Severity**: Bug Bar level 3 (Moderate) per severity-taxonomy §Bug Bar.
**CWE**: CWE-613 (Insufficient Session Expiration) — `owasp_category: A07`.
**Affected**: `src/autom8_asana/auth/jwt_validator.py:83`.

**Detail.** `validate_service_token(..., check_revocation: bool = False)`
(`autom8y_auth/client.py:293`). The asana call site omits it. The SDK documents
the service-token arm as **fail-CLOSED** when enabled (ADR-0034 FORK-2), so
turning it on is the intended posture. Until then, revoking a compromised fleet
credential does **not** stop Asana writes until natural token expiry.

**Remediation.** Pass `check_revocation=True` at `jwt_validator.py:83`. Confirm
the fail-closed arm's availability posture against the asana service's SLO before
enabling, since an unreachable introspection endpoint will then reject writes.

### F-005 — Unauthenticated OpenAPI publishes the mutation surface

**Severity**: Bug Bar level 3 (Moderate) per severity-taxonomy §Bug Bar.
**CWE**: CWE-200 (Information Exposure) — `owasp_category: A05`.
**Affected**: `src/autom8_asana/api/main.py:421-440` (`/redoc` in
`exclude_paths`), `:454`.

**Detail.** `/redoc`, `/docs`, `/openapi.json` all return 200 unauthenticated
from the internet (201 KB schema, 47 paths). The four newer S2S write routes are
`include_in_schema=False` and correctly absent — but that is obscurity, not a
control: rule 120 has no path condition, so they remain reachable. The published
schema **does** enumerate a broad mutation surface on the JWT-excluded PAT trees,
including `DELETE /api/v1/tasks/{gid}`, `DELETE /api/v1/projects/{gid}`,
`POST /api/v1/tasks/{gid}/duplicate`, `PUT /api/v1/tasks/{gid}/assignee`.

**Note for the security-reviewer:** this mutation surface is **wider than the
three write classes the handoff enumerated**. `/api/v1/tasks/*` and
`/api/v1/projects/*` are JWT-**excluded** at the middleware (`main.py:428-429`)
and rely on dual-mode `get_auth_context` DI. Their authorization posture was not
in this probe's scope and is **UNKNOWN** — flagged, not assessed. See §5 R-2.

**Remediation.** Gate `/redoc`, `/docs`, `/openapi.json` behind auth in
production, or serve them only on an internal listener. Do not treat
`include_in_schema=False` as access control.

### Positive findings — controls that work

- **P-1 — dev-mode bypass fails closed.** `AUTH_DEV_MODE=false` and
  `AUTOM8Y_ENV=production` on task def `autom8y-asana-service:770`, and the SDK
  raises at construction if `dev_mode and autom8y_env != LOCAL`
  (`autom8y_auth/config.py:182-186`). The `_dev_bypass_service_claims()` wildcard
  path (`client.py:554-563`) is unreachable in prod. Receipted, both halves.
- **P-2 — the Lambda plane is clean, exhaustively.** All **249** Lambda functions
  in the account were swept for bare credential env keys
  (`ASANA_PAT`, `SERVICE_CLIENT_SECRET`, `CLIENT_SECRET`,
  `AUTOM8Y_DATA_SERVICE_CLIENT_SECRET`, `REDIS_PASSWORD`): **0 hits**. Every
  asana Lambda uses `*_ARN` brokerage. `aws lambda list-functions` — exit 0.
- **P-3 — CI runners hold no fleet credentials.** `.github/workflows/` references
  only `secrets.APP_ID`, `secrets.APP_PRIVATE_KEY`, `secrets.AWS_OIDC_ROLE_ARN`,
  `secrets.GITHUB_TOKEN` — OIDC federation, no long-lived fleet secret. Explicit
  grep for `AUTOM8Y_DATA_SERVICE_CLIENT_ID|CLIENT_SECRET|ASANA_PAT` → exit 1 (no match).
- **P-4 — the ECS service uses Secrets Manager, not plaintext.** `ASANA_PAT`,
  `SERVICE_CLIENT_SECRET`, `REDIS_PASSWORD`, `ASANA_WORKSPACE_GID` are all in the
  `secrets` block (valueFrom), none in `environment`.
- **P-5 — tracked `.env` is empty.** `keys=0 keys_with_nonempty_value=0`,
  `lines=0`. It is git-tracked and not ignored, which is a latent trap, but it
  holds nothing today.
- **P-6 — `.claude/settings.local.json` at HEAD holds no credential keys.** Parsed
  key names: `hooks.*` only; no `env` block. The known hazard is git **history**
  only, exactly as the handoff stated.

---

## §4 NR-3 first sweep (negative-claim scrutiny), reporting nulls

Negatives under sweep: *"an agent seat cannot obtain a fleet service JWT"* and
*"the ALB is internal-only."* **Both negatives are FALSIFIED.** The sweep below
therefore also scrutinises the negatives I *did* assert.

**(a) Is each "no" RECEIPTED, never inferred? UNKNOWN vs FALSE discipline.**

| Statement | Word used | Basis | Verdict |
|---|---|---|---|
| ALB is internal-only | **FALSE** | `describe-load-balancers` → `internet-facing`, exit 0 | receipted |
| A WAF sits in front of prio 120 | **FALSE** | `get-web-acl-for-resource` empty + `list-web-acls` `[]` at both scopes, exit 0 | receipted |
| Agent seat cannot obtain a fleet JWT | **FALSE** | `simulate-principal-policy` → `allowed`, exit 0, + 2 code conjuncts | receipted |
| Service-JWT client creds in this seat's env | **FALSE (absent)** | explicit `printenv` presence test, all 4 canonical keys ABSENT | receipted |
| Any Lambda carries a bare credential env key | **FALSE (0/249)** | full-population sweep, exit 0 | receipted, exhaustive |
| CI runners carry fleet credentials | **FALSE** | grep exit 1 over `.github/workflows/` | receipted |
| Fleet vocabulary contains an Asana write scope | **FALSE (0)** | `grep -c` → 0, exit 1, + full 10-token vocabulary enumerated | receipted |
| `ASANA_PAT` in this seat == prod bot credential | **UNKNOWN** | value comparison barred by CR-5 | **labelled UV-P §1.3, not asserted** |
| `/api/v1/tasks/*` + `/api/v1/projects/*` authz posture | **UNKNOWN** | out of probe scope; dual-mode DI unread | **flagged §5 R-2, not asserted** |
| Whether an *executed* mint clears the gate end-to-end | **UNKNOWN** | mint deliberately not run (CR-5) | **stated §1.4; conjuncts receipted independently** |

No negative in this artifact rests on an unattempted probe. Where I did not
probe, the word is UNKNOWN and it is named as such.

**(b) Were agent-ADJACENT seats swept, or only interactive seats?** All four
classes swept:

| Seat class | Swept | Method | Result |
|---|---|---|---|
| Interactive agent seat (this one) | YES | `printenv` presence test, 138 vars | no JWT creds; **bare `ASANA_PAT` PRESENT** |
| CI runners | YES | grep over `.github/workflows/` | clean (OIDC only) |
| Lambda execution env | YES — **all 249**, not sampled | `list-functions` full config | clean (ARN brokerage) |
| ECS task definitions | YES | `describe-task-definition` rev 770 | clean (Secrets Manager) |
| AWS principal reach (cross-cutting) | YES | `simulate-principal-policy` | **`allowed` on all 30 minting secrets** |

Gap acknowledged: Lambda **execution roles' IAM policies** were not individually
simulated — I swept their *env* exhaustively and their *role ARNs* are recorded,
but per-role secret reach is **UNKNOWN**. Low materiality: the seat-level reach
(admin) already dominates. Named, not silently dropped.

**(c) Does any checked-in `.env`, secretspec profile, or ECS task def inject a
service JWT?** **No — receipted.** `.env` tracked but 0 keys (P-5).
`secretspec.toml` is git-tracked (spec, not vault; profiles `default`/`cli`).
ECS task def uses Secrets Manager `valueFrom` (P-4). `.claude/settings.local.json`
has no `env` block (P-6). **The one affirmative injection is not a JWT** — it is
the bare `ASANA_PAT` via the git-tracked `.envrc` (F-003).

**(d) Is the audience check satisfiable by a token minted for a DIFFERENT
service?** **YES — this is the load-bearing answer.** `FLEET_AUDIENCE` is a single
constant shared by every fleet service (`constants.py:12`). The audience check
partitions fleet-vs-non-fleet only. A token minted for `iris`, `ace`,
`sms-reminder-lambda`, or any of the 30 accounts carries the identical `aud` and
clears the asana boundary. Combined with the absent scope check (F-001), audience
verification contributes **zero** service-level authorization.

---

## §5 Routing and residuals

- **R-1 → security-reviewer.** F-001 through F-005 with remediation. F-001's
  layer-1 remediation is upstream in `autom8y-auth` and cannot be closed in this
  repo; sequencing is load-bearing.
- **R-2 → NEW SCOPE, un-assessed.** The `/api/v1/tasks/*` and `/api/v1/projects/*`
  mutation surface (JWT-**excluded** at middleware, dual-mode `get_auth_context`
  DI, publicly enumerated per F-005) is **wider than the handoff's three write
  classes** and its authorization posture is **UNKNOWN**. Recommend a follow-on
  probe; do not assume it inherits the §1 finding either way.
- **R-3 → threat-modeler (coverage-matrix §A04).** F-002 + F-003 are
  architectural, not implementation defects: the credential-distribution topology
  hands write capability to seats by default and the network boundary was never
  drawn. Per the design-flaw routing rule, these want threat-model review, not
  only a pentest fix.
- **R-4 → operator (escalation).** F-001 ∧ F-002 is a live authorization bypass
  on an internet-exposed production asset with no compensating network control.
  CR-1 does not bind non-agent callers. Flagged for immediate awareness per the
  critical-vulnerability escalation rule.
- **UV-P carried:** `ASANA_PAT` value-identity (§1.3). Deliberate, CR-5-bound,
  non-load-bearing.

**No evidence of active compromise was sought or observed.** This probe read
configuration and authorization state only; it did not review logs, CloudTrail,
or Asana audit history. Absence of a compromise statement here is **UNKNOWN**,
not a clean bill.

---

## §6 Attestation

| Artifact | Path | Verified |
|---|---|---|
| This probe | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/PROBE-re2-blast-radius-2026-08-13.md` | YES (authored-unmerged) |
| Upstream handoff | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/handoffs/HANDOFF-10x-dev-to-security-s2s-authz-2026-08-13.md` | YES (read own-hands) |

All AWS reads: `describe-*`, `list-*`, `get-*`, `simulate-*` — **no mutation**.
All monorepo reads: `git show origin/main:<path>` / `git ls-tree origin/main`
(monorepo HEAD is `fix/wss-wildcard-scope-bypass-closure`, divergent — the trap
was respected).
No credential minted, read, copied, decoded, or logged.
