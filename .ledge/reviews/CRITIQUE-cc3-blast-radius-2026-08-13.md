---
type: review
artifact_id: CRITIQUE-cc3-blast-radius-2026-08-13
schema_version: "1.0"
rite: sre
agent: platform-engineer
role: NCSR second reader (rite-disjoint) for CC-3
wave: chain-of-custody-closure
station: CC-3
initiative: exec-insight-delivery
created_at: "2026-08-13"
second_reads: .ledge/reviews/PROBE-re2-blast-radius-2026-08-13.md
negative_read: NR-3
state: AUTHORED-UNMERGED
status: proposed
self_assessment_cap: MODERATE
evidence_grade: STRONG (only on legs re-run own-hands; see per-leg table)
---

# CRITIQUE — CC-3 blast-radius NCSR second read (NR-3)

**Charge**: adversarial. Attack the ADVERSE closure, do not confirm it. A false
Critical is as much an over-claim as a false all-clear. One hop past the author.

**Terminal state (Q-4 HALT)**: this artifact rests authored-unmerged. Main thread
owns git. No git verb was run. No AWS mutation. No Asana write path. No credential
VALUE read (CR-5) — env presence tested by boolean `printenv >/dev/null` only;
`list-secrets` returns metadata; `simulate` returns a decision, not material.

---

## §0 Bottom line

The author's two negatives are genuinely FALSE — I re-derived both falsifications
own-hands. The **infrastructure legs (F-002) STAND without qualification.** The
**authz-gap defect (F-001) is REAL and confirmed own-hands** — but its **Critical
severity NARROWS to High**, because the end-to-end "read-only agent token → write
executes" chain traverses a control the author read but did not trace: the
`require_business_scope=True` fleet middleware, which sits on the S2S write routes
and rejects tokens carrying neither `bypass_scope_enforcement` nor `business_id`
(both of which DEFAULT off in the claims model). The author dismissed it as
"tenant isolation, not write-class"; that is directionally right about its
PURPOSE but wrong to treat as a no-op on the reachability chain.

| Finding | Verdict | Severity |
|---|---|---|
| NR-3 (both negatives) | **STANDS** (negatives genuinely FALSE) — but consequent severity framing NARROWS | — |
| F-001 | **STANDS as CWE-862 defect / NARROWS on severity + on the read-only-agent end-to-end framing** | **Critical → High** |
| F-002 | **STANDS** (own-hands) | Important |
| F-003 | **STANDS** (own-hands) | Important |
| F-004 | **STANDS** (own-hands) | Moderate |
| F-005 | **STANDS** (own-hands) | Moderate |

---

## §1 Own-hands re-derivation — command + exit-code table

Every row re-run by me (sre/platform-engineer), rite-disjoint from the author
(security/penetration-tester). STRONG is claimed ONLY on these legs.

| # | Leg | Command | Result | Exit | Verdict vs author |
|---|---|---|---|---|---|
| 1 | Seat identity | `aws sts get-caller-identity` | `assumed-role/AWSReservedSSO_AdministratorAccess_072d916d21d2219c/tomtenuta`, acct 696318035277 | 0 | CONFIRMED |
| 2 | ALB scheme | `aws elbv2 describe-load-balancers` | `autom8-prod-alb` = `internet-facing`; **all 6** ALBs internet-facing; SG `sg-0c189d96413dca1c1` | 0 | CONFIRMED |
| 3 | Rule 120 | `aws elbv2 describe-rules --listener-arn <:443>` | priority 120, **only** condition `host-header=asana.api.autom8y.io`, **no path-pattern** | 0 | CONFIRMED |
| 4 | SG ingress | `aws ec2 describe-security-groups --group-ids sg-0c189d96413dca1c1` | `autom8-prod-alb-sg`, ingress `0.0.0.0/0` on 80 and 443 | 0 | CONFIRMED |
| 5 | WAF REGIONAL | `aws wafv2 list-web-acls --scope REGIONAL` | `{"WebACLs": []}` | 0 | CONFIRMED |
| 6 | WAF CLOUDFRONT | `aws wafv2 list-web-acls --scope CLOUDFRONT` | `{"WebACLs": []}` | 0 | CONFIRMED (zero, both scopes) |
| 7 | Secrets inventory | `aws secretsmanager list-secrets` | 188 total; **29** match `autom8y/auth/service-api-keys/` (author said 30) | 0 | CONFIRMED w/ minor count delta |
| 8 | IAM reachability | `aws iam simulate-principal-policy --action secretsmanager:GetSecretValue` | `decision: allowed` — **via admin `*/*`**, resource returned as `${SecretId}` template | 0 | CONFIRMED, with reframe (see §3) |
| 9 | authz gap | `git show origin/main:…/routes/internal.py` (full `require_service_claims`) | validates token-type + JWT, logs `scope`/`caller_service`, `return ServiceClaims(...)`; **no `has_scope`/`has_permission`/allowlist** | 0 | CONFIRMED |
| 10 | sibling gate exists | `git show origin/main:…/routes/admin.py:452-460` | admin route **DOES** gate: `if SUPER_ADMIN_PERMISSION not in claims.permissions: raise 403` | 0 | CONFIRMED — proves omission on write routes |
| 11 | **missed control** | `.venv/…/autom8y_auth/middleware.py:246-300` | `require_business_scope` precedence: `bypass_scope_enforcement is True → allow`; `business_id truthy → allow`; **else → reject 400 AUTH-TEB-004** | 0 | **NEW — author did not trace** |
| 12 | claims defaults | `.venv/…/autom8y_auth/claims.py:134,175` | `bypass_scope_enforcement` default `False`; `ServiceClaims.business_id` default `None` | 0 | **NEW — the gate is not a no-op** |
| 13 | call site | `git show origin/main:…/auth/jwt_validator.py` | `validate_service_token(token, audience="https://api.autom8y.io")` — omits `check_revocation` | 0 | CONFIRMED (F-004) |
| 14 | SDK signature | `.venv/…/autom8y_auth/client.py:288-293` | `async def validate_service_token(self, token, *, audience=FLEET_AUDIENCE, check_revocation: bool = False)` | 0 | CONFIRMED (F-004) |
| 15 | audience constant | `.venv/…/autom8y_auth/constants.py:12` | `FLEET_AUDIENCE: str = "https://api.autom8y.io"` | 0 | CONFIRMED (Conjunct A) |
| 16 | injection path | `git ls-files --error-unmatch .envrc` + `git show origin/main:.envrc` | git-TRACKED; final line `autom8y_tf_bridge_all "ASANA_PAT:asana_pat" …` | 0 | CONFIRMED (F-003) |
| 17 | repo's own guard | `git show origin/main:…/auth/bot_pat.py:107-140` | `assert_no_plaintext_pat_in_caller` raises if bare `ASANA_PAT` in caller env — but is a **function that must be invoked**, "intentionally NOT wired into ECS server startup" | 0 | CONFIRMED, with nuance |
| 18 | seat env presence | `printenv ASANA_PAT >/dev/null; printenv AUTOM8Y_DATA_SERVICE_CLIENT_SECRET >/dev/null` (BOOLEAN, CR-5) | `ASANA_PAT` PRESENT, `TF_VAR_asana_pat` PRESENT; service-JWT client creds ABSENT | 0/1 | CONFIRMED (§1.3) |
| 19 | live exposure | `curl -sS -o /dev/null -w '%{http_code}' https://asana.api.autom8y.io/health` and `/openapi.json` | `health=200 ip=107.20.73.158`, `openapi=200`, unauthenticated | 0 | CONFIRMED (F-002/F-005) |

**Substrate caveat.** Infra legs (2-8, 19) are LIVE production state. Code legs
(9,10,13,16,17) are read from `origin/main` (d7560153); the local branch is ahead
(4129ae7e) and the deployed ECS image is a third point — my code reads are the same
`origin/main` proxy the author used, not a read of the running artifact. The SDK
legs (11,12,14,15) are the installed `.venv` package (the author's established
method). This does not weaken the infra legs; it bounds the code legs to
"origin/main, not proven byte-identical to deployed."

---

## §2 NR-3 sweep — refuters, returns including nulls

**Negatives under second-read**: (i) "an agent seat cannot obtain a fleet service
JWT"; (ii) "the ALB is internal-only." The author CLOSED both ADVERSELY (seat CAN
reach; ALB IS internet-facing). My charge was to try to REFUTE the adverse closure.

**(a) Is every "yes, exploitable" receipted own-hands, or inferred?**
Re-ran legs 2-8 (the load-bearing AWS reads) myself. ALB scheme, rule-120 absence
of path condition, SG `0.0.0.0/0`, WAF-zero-at-both-scopes, and the IAM `allowed`
decision all reproduce at exit 0. The ADVERSE closure of both negatives **STANDS**:
the negatives are genuinely FALSE, receipted, not inferred.

**(b) UNKNOWN vs FALSE discipline — did any UNKNOWN get silently upgraded?**
Swept the three the author named. **All three stayed UNKNOWN; none upgraded to
FALSE or "exploitable."** Confirmed:
- `ASANA_PAT` value-identity vs prod bot secret → UV-P at §1.3, labelled, not asserted. I did NOT read the value either (CR-5).
- `/api/v1/tasks/*` + `/api/v1/projects/*` authz posture → flagged §5 R-2, UNKNOWN. I independently confirm these route trees are **JWT-EXCLUDED** at `main.py:428-437` (dual-mode `get_auth_context` DI), so their posture genuinely differs from the S2S routes and is correctly left UNKNOWN — NOT covered by F-001 either way.
- Executed end-to-end mint → §1.4, not run (CR-5). Stayed UNKNOWN.
PASS: the author did not launder any UNKNOWN into a positive.

**(c) Is the exploit chain reachable end-to-end, or does a control the author
missed break it? — THE HOP.**
This is where the attack lands. The write routes (`entity_write`, `intake_create`,
`intake_custom_fields`, `matching`, `projects` POST/PUT/DELETE, `resolver`,
`receipts`, `fleet_query`) all `Depends(require_service_claims)` — confirmed
tree-wide. But those routes are **NOT** in `main.py` `exclude_paths` (only the PAT
trees `/api/v1/tasks|projects|sections|users|workspaces|dataframes|offers|exports|tags/*`
are excluded). Therefore every S2S write request first transits the fleet
`JWTAuthMiddleware`, configured `require_business_scope=True` (`main.py:445`).

`_check_business_scope_precedence` (`middleware.py:246-300`), own-hands:
1. `bypass_scope_enforcement is True` → allow
2. truthy `business_id` → allow
3. **else → reject 400 AUTH-TEB-004** ("token missing both …")

And the claims model defaults (`claims.py:134,175`): `bypass_scope_enforcement =
False`, `ServiceClaims.business_id = None`. So this is a REAL gate, not the no-op
the author's "tenant isolation, not write-class" framing implies. For the chain to
reach the (un-scope-checked) handler, a minted read-only agent token MUST carry
`bypass_scope_enforcement=True` (an exempt-SA grant, W3.5b-2 / ADR-04 §4.2, NOT the
default) OR a `business_id` (which the `exchange-business` endpoint name suggests it
issues, bounding the write to a business scope). **Which branch a minted `ace`/`iris`
token takes is UNKNOWN** — the author did not mint (correctly) and did not read the
auth-server SA provisioning. The author asserted PAST this gate.

Added refuter run: does any write route layer its own scope/permission check after
the dependency (like `admin.py` does)? Tree-wide grep for
`has_scope|INSUFFICIENT_SCOPE|not in claims.(scope|permissions)|has_permission`
across all `origin/main` route files → **only** `admin.py`'s `SUPER_ADMIN_PERMISSION
not in claims.permissions` gate. The write routes have NONE. So: the middleware is
the ONLY interposed control, and it enforces BUSINESS scope, never WRITE-CLASS
scope. The author's CORE claim (no write-class authz) survives this refuter. The
author's SEVERITY claim (weaponizable end-to-end from a read-only agent seat, wide
open) does not — it depends on the un-receipted branch of a gate the author waved off.

**(d) Blast-radius honesty — what does the network exposure add?**
`GET /health → 200` (leg 19) proves the HEALTH route is unauthenticated. It proves
NOTHING about the write routes: those transit `JWTAuthMiddleware`, and an
unauthenticated request has no Bearer → 401 AUTH-TEB-001 at the middleware (I did
NOT send a write to prove this — CR-1 — I read the middleware's `_classify_error`).
So F-002's internet exposure adds **network reach to PRESENT a token from any
source with no WAF / rate-limit / IP-allowlist in path** — it does NOT make writes
unauthenticated. The Critical therefore rests on F-001 (authz gap) **AND**
agent-token reachability **TOGETHER**, never on public exposure alone. Credit where
due: the author states this correctly in F-002's own impact ("F-001's precondition
is 'hold a fleet credential'") — F-002 is not the over-claim.

---

## §3 Per-finding verdicts

### NR-3 — STANDS (negatives genuinely FALSE); consequent framing NARROWS
Both asserted negatives are falsified own-hands (legs 2, 8). The adverse
dispositions are correct: the ALB IS internet-facing and the admin seat CAN read
the minting secrets. What NARROWS is the author's onward escalation to a
"wide-open Critical" — that inference crosses the untraced `require_business_scope`
gate (§2c) and rests on an un-executed mint.

### F-001 — STANDS as a CWE-862 defect; **NARROWS: Critical → High**
**What STANDS, own-hands (legs 9, 10, 15):** `require_service_claims` performs zero
write-class authorization — it validates token-type and fleet audience, captures
`scope`/`caller_service` for LOGGING, and returns `ServiceClaims` with no
`has_scope` / `has_permission` / service allowlist. The sibling `admin.py` route
gates on `claims.permissions` (leg 10), proving the omission on the write routes is
a genuine gap, not an intended design. There is no fleet `asana:write` scope to
check even if one were added. This is a real Missing-Authorization defect.

**Why it NARROWS from Critical to High — the concrete hops:**
1. **Untraced middleware gate** (`middleware.py:246-300`, `claims.py:134/175`, legs
   11-12): the S2S write routes sit behind `require_business_scope=True`, which
   rejects tokens carrying neither `bypass_scope_enforcement` (default `False`) nor
   `business_id` (default `None`). The disposition of a minted read-only `ace`/`iris`
   token at this gate is **UNKNOWN**; the author asserted past it. Absent an
   exempt-SA `bypass_scope_enforcement=True` grant, the resulting authority is
   **business-scoped**, not the unbounded cross-tenant write the Critical framing
   describes.
2. **Reachability is an SSO-admin property, not an agent-token escalation** (leg 8):
   the `simulate → allowed` decision resolves through the operator's
   AdministratorAccess `*/*` policy (resource returned as the `${SecretId}`
   template), i.e. the seat can read the minting secret **because it is admin** —
   which also means it can read the prod bot PAT and write directly (F-003). In the
   admin-seat threat model the S2S authz gap is redundant with F-003; the S2S gap's
   marginal risk is the **leaked non-admin fleet credential** scenario.
3. **Terminal mint not executed** (correctly, CR-5): hops "exchange-business → token
   → write executes" are inferred, not receipted.
4. **Internet exposure ≠ unauthenticated write** (§2d): removes network barriers to
   presenting a token, not the JWT requirement.

**High is the defensible rung**: a real missing-write-class-authorization defect on
an internet-reachable S2S mutation surface, exploitable by any holder of a fleet
credential that clears the business-scope middleware — but NOT proven weaponizable
end-to-end from the specific read-only agent tokens the Critical named, and bounded
(absent an exempt-SA grant) to a business scope.

**Explicit re-escalation trigger (do not minimize):** IF `ace`/`iris` (or any
broadly-held fleet SA) are provisioned as **exempt-SAs** carrying
`bypass_scope_enforcement=True` — verifiable in the `autom8y-auth` SA config /
issuance path, NOT probed here (CR-5, cross-repo) — then the business-scope gate no
longer bounds the finding and F-001 re-escalates toward Critical. This is the single
operator-actionable question that resolves the High/Critical fork.

### F-002 — STANDS (own-hands, legs 2-6, 19)
Internet-facing prod ALB, SG `0.0.0.0/0` on 443/80, zero WAF at both scopes, rule
120 with no path segmentation, `/health` 200 unauthenticated — all reproduce at
exit 0. Severity Important stands. No over-claim: the author correctly scopes its
impact to "removes network barriers to using a held credential."

### F-003 — STANDS (own-hands, legs 16, 17, 18)
`.envrc` is git-tracked and bridges `ASANA_PAT`; `ASANA_PAT`/`TF_VAR_asana_pat`
PRESENT in this seat (value never read); `bot_pat.py`'s `assert_no_plaintext_pat_in_caller`
guard documents this exact posture as forbidden for caller contexts. Nuance worth
recording: the guard is a function that must be **invoked** at caller startup and is
"intentionally NOT wired into ECS server startup" — it is likewise not invoked in
the agent seat, so the "contradiction" is that the guard's stated invariant is
unenforced in the one context it targets. Finding STANDS; `ASANA_PAT` value-identity
correctly stays UNKNOWN (UV-P preserved).

### F-004 — STANDS (own-hands, legs 13, 14)
`validate_service_token(..., check_revocation: bool = False)` and the asana call site
passes only `audience`. Revoked service tokens still authorize writes until natural
expiry. Moderate stands.

### F-005 — STANDS (own-hands, leg 19)
`/openapi.json` 200 unauthenticated (and `/redoc` per the excluded-paths config).
The published schema enumerates a mutation surface. Author correctly labels the
`include_in_schema=False` S2S routes as obscurity-not-control and the
`/api/v1/tasks|projects/*` posture UNKNOWN. Moderate stands.

---

## §4 What survives to the operator (the honest core)

1. **Real defect (High):** the Asana S2S write routes enforce no write-class
   authorization; a fleet service token that clears the business-scope middleware
   authorizes every S2S write class regardless of the account's declared read-only
   scope. The pattern to fix already exists in-repo (`admin.py` permission gate).
   Two-layer remediation (mint `asana:write` vocab upstream in `autom8y-auth`;
   enforce at each write route) is sound and sequencing-correct.
2. **Real hardening gaps (Important):** internet-facing write surface with zero WAF,
   `0.0.0.0/0` SG, no path segmentation (F-002); bare bot PAT in the agent seat via
   git-tracked `.envrc`, against the repo's own guard (F-003).
3. **Real config defects (Moderate):** revocation unchecked (F-004); OpenAPI
   published unauthenticated (F-005).
4. **The one question that moves the severity:** are `ace`/`iris` exempt-SAs
   (`bypass_scope_enforcement=True`)? If yes → F-001 re-escalates toward Critical.
   If no → F-001 is High and the business-scope middleware bounds writes to a
   business scope. Author did not resolve this; it is the load-bearing UNKNOWN.

## §5 What FALLS

Nothing FALLS to zero. The single over-reach is F-001's **Critical severity and its
"read-only agent seats authorize all write classes [cross-tenant], wide open"
end-to-end framing**, which NARROWS to High + business-scoped (absent an exempt-SA
grant) because an interposed, defaulted-off business-scope middleware gate was read
but not traced, and the terminal mint was (correctly) not executed.

---

## §6 Fence compliance

- Read-only AWS only: `get-caller-identity`, `describe-*`, `list-*`,
  `get-web-acl-for-resource`, `simulate-principal-policy`. No mutation (L4 held).
- No Asana write path (CR-1): only `GET /health`, `GET /openapi.json`. No
  POST/PUT/PATCH/DELETE to any route; the 401-on-unauthenticated-write claim was
  read from middleware source, not sent.
- CR-5: no credential VALUE read/transcribed. Env tested by boolean `printenv
  >/dev/null`; `list-secrets` metadata only; `simulate` decision only.
- CR-2: `s3://autom8y-asr-verdicts` untouched.
- Monorepo reads via `git show origin/main:`; installed-SDK reads via `.venv`
  (author's established method). No git verb run; main thread owns git. This
  critique rests authored-unmerged (Q-4 HALT).

| Artifact | Path | Verified |
|---|---|---|
| This critique | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/CRITIQUE-cc3-blast-radius-2026-08-13.md` | YES |
| Probe second-read | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/PROBE-re2-blast-radius-2026-08-13.md` | YES (read own-hands) |
