---
type: spec
artifact_subtype: tdd
title: Token-Safe ASANA_PAT Read-Route + W-REG 19-Constant Replacement
initiative: asana-cutover-readiness-credential-topology
slug: asana-pat-read-route-and-wreg
station: architect (10x-dev, Potnia-gated)
created: 2026-07-02
status: proposed
design_state: DESIGN-LOCKED (both fork branches) — construction AWAITING-OPERATOR-RATIFICATION
impact: high
impact_categories: [security, breaking-change]
consumes:
  - .ledge/handoffs/HANDOFF-security-to-operator-asana-pat-read-route-2026-07-02.md
  - .sos/wip/frames/asana-cutover-readiness-sequencing.shape.md
  - src/autom8_asana/reconciliation/section_registry.py
  - /Users/tomtenuta/code/autom8/apis/asana_api/objects/project/models/business_units/main.py
companion_adr: .ledge/decisions/ADR-asana-pat-read-route-forkR-2026-07-02.md
evidence_grade: MODERATE   # self-ref ceiling; STRONG requires rite-disjoint attester + construction evidence
---

# TDD — Token-Safe ASANA_PAT Read-Route + W-REG 19-Constant Replacement

## GRANDEUR ANCHOR (restated verbatim at head)

> "Finish the ORIGINAL cutover charge's LAST POLE — drive SCAR-REG-001's 19
> placeholder section-GIDs OPEN → proven, via a SAFE token-safe read-route →
> W-IRIS live receipt → W-REG replacement. Proven ONLY by a live `GET /sections`
> receipt joined with the monolith name→bucket taxonomy + a RED-first misroute
> fixture. CONSTRUCT what security designed+gated — no shortcuts, no new-token
> crusade."

This TDD design-locks BOTH the token-safe read-route (a) and the W-REG 19-constant
replacement (b) in one pass. It is **design-only**: no code is written, no route is
deployed, no plaintext PAT appears anywhere (ARN / secret-name / sha256-prefix only).
The FORK-R route-option decision is **surfaced, not selected** — see companion ADR.

---

## 1. System Context

### 1.1 The credential seam (why this exists)

`section_registry.py` freezes 19 sequential **placeholder** section-GIDs behind a
`VERIFY-BEFORE-PROD (SCAR-REG-001)` annotation. Replacing them correctly requires
the raw GIDs, which live ONLY in live Asana (project `1201081073731555`) — reachable
ONLY through the Asana PAT. Security **designed + gated** (teeth-proven, MODERATE) a
token-safe READ route so an interactive caller can obtain those GIDs **without ever
touching the plaintext PAT**. That route is the single seam gating W-IRIS → W-REG →
SCAR-REG-001 closure.

The forbidden path already exists in-code and must NOT be used: `get_auth_context`
PAT-mode (`dependencies.py:139-148`) passes the **caller's plaintext token** straight
through to Asana. The safe path also already exists: JWT/S2S-mode
(`dependencies.py:150-244`) validates a service JWT, then resolves the **bot PAT**
server-side via `get_bot_pat()` (`bot_pat.py:70`) — the caller never sees the secret.

> **SVR (file-read)** — claim: *the section-list route exists and is dual-mode*.
> anchor: `src/autom8_asana/api/routes/projects.py:319-320` marker_token:
> `@router.get("/{gid}/sections"` + `:328` `client: AsanaClientDualMode`. The route
> accepts BOTH auth modes; `AsanaClientDualMode` resolves through
> `get_asana_client_from_context` → `get_auth_context` (`dependencies.py:247-280`).
> Verified by direct read this session.

> **SVR (file-read)** — claim: *JWT-mode brokers the bot PAT; PAT-mode passes caller
> plaintext*. anchor: `src/autom8_asana/api/dependencies.py:139-148` marker_token:
> `return AuthContext(mode=auth_mode, asana_pat=token)` (PAT-mode, plaintext caller
> token) vs `:216` `bot_pat = get_bot_pat()` (JWT-mode, brokered). Verified this session.

> **SVR (file-read)** — claim: *`get_bot_pat` resolves via `resolve_secret_from_env`*.
> anchor: `src/autom8_asana/auth/bot_pat.py:70` marker_token:
> `pat = resolve_secret_from_env("ASANA_PAT")`. Verified this session.

> **[UV-P: `resolve_secret_from_env` is `_ARN`-first — it resolves `ASANA_PAT_ARN`
> (Secrets Manager fetch) before falling back to bare `ASANA_PAT` plaintext env |
> METHOD: deferred-to-operator-ratification | REASON: `resolve_secret_from_env`
> lives in the external `autom8y_config.lambda_extension` package, not inspected in
> this repo; the ARN-first behavior is attested by the security HANDOFF §1 Residence
> leg ("Lambda reads by `ASANA_PAT_ARN` ref"), a non-SVR-canonical citation, not
> re-derived here].**

### 1.2 Reachability blocker (the fork trigger)

iris preflight resolved the design magnitude: the (b) proxy is a **THIN assembly, not
from-scratch** — the read-only list AND the brokered auth already exist. The blocker
is deployment reachability:

> **[UV-P: the prod Lambda handler `autom8y_asana_handler_prod` is a stub (Inactive,
> CodeSize=0, no Function URL); the live API runs on ECS whose deploy/reachability
> config is NOT in this repo | METHOD: deferred-to-operator-ratification | REASON:
> Lambda/ECS runtime state is an AWS-control-plane fact requiring an `aws lambda
> get-function` / ECS-service probe; it is an iris-preflight finding, not
> repo-inspectable. This is the load-bearing operator-ratification input — see §4].**

Because the safe machinery exists but its live reachability is unconfirmed, the design
**forks** (§3). Both branches are locked so the parent proceeds the instant the
reachability probe + FORK-R resolve.

---

## 2. Requirements Coverage

| Req (from shape §5 sprint-4-reg + handoff §3/§4) | Design element |
|---|---|
| Token-safe READ route (caller never touches plaintext PAT) | §3 both branches; brokered `get_bot_pat` server-side |
| ONLY `GET /sections` exposed (read-only surface) | §3 pinned single-route capability |
| Pin to project `1201081073731555` / 19-GID allowlist | §3 H2 build-deliverable |
| 7 hard-gates ride with construction | §5 gate→build→qa table |
| W-REG join: live-GID × monolith name→bucket → corrected frozensets | §6 join semantics |
| Join-disposition (i) dual-GID names ruled | §6.2 Disposition (i) |
| Join-disposition (ii) live-name-absent-from-monolith ruled | §6.3 Disposition (ii) |
| RED-first misroute fixture as wrong-BUCKET (two-sided) | §7 fixture spec |
| Honest-rung ceiling (no rounding) | §8 |
| No new scoped token; no cutover; no DEFER items | §9 constraints |

---

## 3. Read-Route Design — BOTH Fork Branches

Both branches converge on the same invariant: **the caller holds a short-lived AWS/S2S
identity, NEVER the plaintext PAT; a broker resolves the PAT server-side via
`ASANA_PAT_ARN`; only `GET /sections` (pinned to project `1201081073731555`) is
reachable.** They differ ONLY in whether new infrastructure is built.

### 3.1 REUSE-EXISTING branch — collapse to grant + conformance-audit

**Precondition (operator-ratified):** the ECS API is deployed **AND** reachable **AND**
brokered (JWT-mode resolves the bot PAT via `ASANA_PAT_ARN`) **AND** the interactive
caller can mint a brokered **S2S JWT** via `SERVICE_CLIENT_SECRET_ARN` token-exchange
(the mechanism `insights-export` already carries).

**If all hold:** the existing `GET /api/v1/projects/1201081073731555/sections` in
**JWT mode** IS the safe read path. No new proxy. The design shrinks to two deliverables:

1. **Caller-access grant** — provision the interactive caller (iris) to mint a
   short-lived S2S JWT via `SERVICE_CLIENT_SECRET_ARN` token-exchange. No PAT ever
   materializes in the caller.
2. **Hard-gate conformance audit** of the *existing* route against H1–H6 / GATE-GAP-1
   (§5). The audit verdict is NOT assumed-pass — the existing route was built for
   general S2S consumers, not this scoped read-capability. Per-gate audit disposition:

   | Gate | Existing-route conformance | Hardening needed? |
   |---|---|---|
   | H1 | ECS route sits behind gateway/ALB, not a Lambda function-URL — H1's literal `AuthType: AWS_IAM` does not apply; re-express as "route requires authenticated caller identity; unauthenticated reach fails closed". | **AUDIT** (operator-ratified reachability config, not in repo) |
   | H2 | `GidStr` already enforces `^\d{1,64}$` in production (`models.py:47-54`) — integer-validation SATISFIED. But the route accepts **any** project GID → BOLA/IDOR surface wider than the single cutover project. | **HARDEN** — pin to `1201081073731555` via an allowlist wrapper OR document the wider S2S surface as accepted risk |
   | H3 | GET-only; outbound URL built server-side (`f"/projects/{gid}/sections"`, `projects.py:362`). | **AUDIT** — confirm no method-override middleware upstream |
   | H4 | `bot_pat.py` never logs the value (`:85-89` logs length only); `get_auth_context` logs `caller_service`/`scope`, not token. | **AUDIT** — confirm trace-header capture disabled at ECS/gateway |
   | H5/V6 | Caller-side, not route-side. The route ships the `bot_pat.py:69-74` fail-closed resolver (absent → `BotPATError`). The caller-image guard `assert_no_plaintext_pat_in_caller()` is re-exported from `autom8_asana.auth` (N2b); the out-of-repo iris/hermes read-route caller MUST invoke it at container startup **before** minting the S2S JWT / calling `GET /sections`. | **RIDES REGARDLESS** (caller image guard) |
   | H6 | S2S JWT is short-lived by construction. | **CONFORMANT** iff JWT-mode + bounded TTL |
   | GATE-GAP-1 | Repo-level `.gitleaks.toml` gap. | **RIDES REGARDLESS** (repo, both branches) |

   **Structural hardening lever (recommended within REUSE):** the existing route uses
   `AsanaClientDualMode`, which STILL accepts PAT-plaintext mode. For the scoped
   read-capability, swap the dependency for the JWT-only S2S guard
   `require_service_claims` (already used by `intake_create.py:77`) so PAT-plaintext
   mode is **structurally impossible** on this capability — H1/H5 hardened by
   construction, not by convention.

   > **SVR (file-read)** — claim: *a JWT-only S2S guard exists and is already in use*.
   > anchor: `src/autom8_asana/api/routes/intake_create.py:77` marker_token:
   > `claims: Annotated[ServiceClaims, Depends(require_service_claims)]`. Verified this
   > session; definition at `routes/internal.py`.

### 3.2 BUILD branch — thin read-only proxy

**Precondition:** the REUSE precondition does NOT hold (ECS unreachable/unbrokered, or
S2S-JWT mint unavailable to the caller).

**Design:** a single-route read-only proxy, assembled THIN from existing parts:

- **Surface:** exposes ONLY `GET /sections` for the pinned project `1201081073731555`.
  No other verb, no other path, no other project.
- **Reuse:** the section-fetch reuses the same server call the existing route uses —
  `client._http.get_paginated(f"/projects/{gid}/sections")` (`projects.py:361`) /
  `clients/sections.py:301-380 list_for_project_async`. The PAT resolution reuses the
  brokered `get_bot_pat()` (`bot_pat.py:70`, `ASANA_PAT_ARN`-first). **No new fetch or
  auth code is authored** — the proxy is glue over existing functions.
- **Deployment shape:** Lambda function-URL single-route (canonical, because H1's
  `AuthType: AWS_IAM` applies directly to a function-URL). The stub
  `autom8y_asana_handler_prod` is the natural landing site once activated (deployment
  is user-sovereign — NOT designed here).
- **Caller flow:** iris signs the request with a **short-lived assumed-role identity**
  (SigV4) → function-URL enforces `AuthType: AWS_IAM` (H1) → handler resolves bot PAT
  via `ASANA_PAT_ARN` (H4) → server-side calls `GET /projects/1201081073731555/sections`
  (H2/H3) → returns `{gid, name}` list. The caller never sees the PAT.

### 3.3 Branch-selection input (operator-ratification)

The branch is selected by ONE operator-ratified fact (see ADR §Operator-Ratification
Input): **is the live ECS API deployed + reachable + brokered, and can the caller mint
a brokered S2S JWT?** YES → REUSE (grant + audit). NO → BUILD (thin function-URL proxy).
The design does NOT assume either — the reachability + S2S-JWT-mint confirmation is an
explicit operator input.

---

## 4. Operator-Ratification Inputs (design does NOT assume)

| Input | Consumer | Resolves |
|---|---|---|
| **ECS reachability + broker** — is the live ECS `/api/v1/projects/{gid}/sections` deployed, reachable, and JWT-brokered? | branch selection | REUSE vs BUILD |
| **S2S-JWT mint** — can the interactive caller mint a short-lived S2S JWT via `SERVICE_CLIENT_SECRET_ARN` token-exchange? | REUSE precondition | collapses (b) → grant+audit |
| **FORK-R route-option** — (b)/REUSE-collapse [default rec], (a) scoped-assume-role [runner-up], (c2) SSO+proxy [higher-infra peer] | route custody | see ADR (AWAITING-OPERATOR-RATIFICATION) |

---

## 5. The 7 Hard-Gates as TDD Constraints (gate → build-deliverable → qa-hook)

Each gate is a **binding constraint** on construction. In the REUSE branch each row
becomes a conformance-audit item on the existing route (§3.1); in the BUILD branch each
row is a build-deliverable on the proxy.

| Gate | Build-deliverable | QA-verification hook (RED-first, two-sided) |
|---|---|---|
| **H1** (auth) | Function-URL `AuthType: AWS_IAM` (BUILD) / authenticated-caller-required (REUSE). Build-fail assertion if the route resolves unauthenticated. | Unauthenticated request → `403` (RED if `200` = anonymous PAT oracle). IaC/test asserts `AuthType != NONE`. Two-sided: signed request → `200`. |
| **H2** (BOLA/IDOR) | Pin route to project `1201081073731555`; reject any `{gid}` not in the allowlist; `{gid}` integer-validated (`^\d{1,64}$` already enforced by `GidStr` in prod). | `gid ∉ allowlist` → `403/404` (RED if it returns another project's sections); non-numeric `gid` → `422`. Two-sided: pinned gid → `200`. |
| **H3** (path/verb) | Ignore `X-HTTP-Method-Override`; exact-match normalized path; build outbound URL server-side from the pinned gid. | `POST` + `X-HTTP-Method-Override: GET` → rejected; encoded-traversal path variant → `404`; assert outbound URL is server-constructed (no caller-supplied URL). |
| **H4** (log hygiene) | Never log `Authorization`/PAT; disable trace-header capture; inject via `ASANA_PAT_ARN`, never bare `ASANA_PAT`. | Log-scrape fixture over a full request asserts **zero** PAT / `Authorization` tokens in emitted logs; static assert bare `ASANA_PAT` is not read on the route path. |
| **H5/V6** (caller guard) | Caller-startup guard asserts bare `ASANA_PAT` **unset**; resolver fail-closed for absent-ARN interactive context. **Contract (N2b):** the caller image MUST call `assert_no_plaintext_pat_in_caller()` (re-exported from `autom8_asana.auth`) at container startup, **before** minting the S2S JWT / calling `GET /sections`. It is intentionally NOT wired into the ECS server lifespan/S2S client (server legitimately brokers `ASANA_PAT`) nor dev/CLI paths. | RED-first: guard absent → caller boots with bare `ASANA_PAT` set; guard present → startup **halts** (`TestCallerPlaintextGuard`, two-sided). Absent-ARN interactive context → `BotPATError` (fail-closed, no plaintext fallback). |
| **GATE-GAP-1** (teeth soundness) | Add a native Asana-PAT rule to `.gitleaks.toml` matching `1/{gid}:{hex}` and `2/…:{hex}` native token forms. | Plant a native-format PAT decoy (sha256-prefix only, never a real value) in a non-allowlisted sink → `gitleaks` RED exit `1`; clean tree → GREEN exit `0`. Extends the S3 teeth (which covered only `asana-client-secret`) to native leaks. |
| **H6** (identity TTL) | Short-lived caller identity (assumed-role session / S2S JWT), bounded TTL. | Assert credential/token TTL ≤ bound; an expired identity → route rejects (`403`). |

**Gate-soundness note:** GATE-GAP-1 is a *gating* obligation — until the native-PAT
rule lands, the GREEN teeth are **not sound** for native `1/gid:hex` leaks (the current
`.gitleaks.toml` is blind to them). It must land with, or before, construction.

---

## 6. W-REG Design — Dual-Anchor Join (live-GID × monolith name→bucket)

### 6.1 The join contract (per shape §3 dual-anchor ruling + §5)

W-REG replaces the 19 frozen placeholders by JOINING two sources on **NAME**, never on
GID value:

- **live-GID source** = the W-IRIS receipt's `name → live GID` map (the ONLY real GID
  source; user-sovereign READ).
- **name→bucket taxonomy** = the monolith `BusinessUnits.SECTIONS` dict
  (`business_units/main.py:17-38`) — the behavioral source-of-truth for bucketing
  (`active` / `activating` / `inactive` / `ignore`). The monolith holds **no GIDs**.

The join is `join_section_registry(name_to_gid, name_to_bucket, monolith_ignore_names)`
(`section_registry.py:249`), producing corrected `unit_section_gids` /
`excluded_section_gids` frozensets + surfaced `findings`. Matching on NAME (not GID)
means a GID-value divergence between the frozen placeholders and the live receipt
**cannot** misroute a section — that was the SCAR-REG-001 defect class.

> **SVR (file-read)** — claim: *the monolith buckets only `Templates` as `ignore`;
> autom8y `EXCLUDED_SECTION_NAMES` carries 4*. anchor:
> `business_units/main.py:37` marker_token: `"ignore": {"Templates"},` vs
> `section_registry.py:118-125` marker_token: `"Templates", "Next Steps", "Account
> Review", "Account Error",`. Verified this session — the divergence is real and
> load-bearing for Disposition (ii).

### 6.2 Consumption model (verified — determines the fail-closed posture)

The live registry is a **DENYLIST**, not an allowlist. The processor excludes on
`section_gid ∈ EXCLUDED_SECTION_GIDS`, then name-fallback on
`EXCLUDED_SECTION_NAMES`, then no-section; **everything else is PROCESSED-by-default**.
`UNIT_SECTION_GIDS` is **not consumed as a gate** anywhere in the processor.

> **SVR (file-read)** — claim: *the processor is denylist / processes-by-default*.
> anchor: `src/autom8_asana/reconciliation/processor.py:450` marker_token:
> `if section_gid and section_gid in self._excluded_section_gids:` — exclusion fires;
> the fall-through past `:474` no-section check reaches reconciliation matching
> (processed). Verified this session.

> **SVR (bash-probe)** — claim: *`UNIT_SECTION_GIDS` is unused as a processor gate*.
> source: `rg -n "UNIT_SECTION_GIDS" src/ --type py` → hits only in
> `section_registry.py` (definition) and `reconciliation/__init__.py` (re-export);
> zero hits in `processor.py`. Verified this session (exit 0).

**Consequence:** an omitted (route-to-neither) section is **processed**, not excluded.
Therefore fail-closed for W-REG means *fail-closed toward exclusion*, and an
undispositioned unknown section must **block live-wiring**, not silently pass.

### 6.3 Disposition (i) — names in BOTH `EXCLUDED` and `UNIT` with different placeholder GIDs

**RULED.** `"Account Review"` and `"Account Error"` appear in BOTH the frozen
`EXCLUDED_SECTION_GIDS` (`…602`, `…603` @ `section_registry.py:109-110`) AND
`UNIT_SECTION_GIDS` (`…623`, `…624` @ `:152-153`) — the same name mapped to two
different placeholder GIDs.

- This double-GID artifact is an **artifact of the sequential-placeholder fabrication**,
  NOT a live condition. A section name is unique in Asana → the W-IRIS receipt yields
  exactly **one** live GID per name. The dual-GID collapses at join time.
- **Disposition:** exclusion WINS. Both names are in `EXCLUDED_SECTION_NAMES`, so their
  single live GID lands in `excluded_section_gids`, never in `unit_section_gids`. This
  matches the scaffold's `double_membership` → exclusion-wins rule (`section_registry.py:328-340`,
  rationale LBC-004: a section wrongly excluded under-counts; a section wrongly
  processed as a unit pollutes account classification — exclusion is the safety-preserving
  assertion).

> **SVR (file-read)** — claim: *the two names are dual-listed with distinct placeholder
> GIDs*. anchor: `section_registry.py:109-110` marker_token:
> `"1201081073731602",  # Account Review` + `"1201081073731603",  # Account Error`
> vs `:152-153` `"1201081073731623",  # Account Review` + `"1201081073731624",  #
> Account Error`. Verified this session.

### 6.4 Disposition (ii) — live name present in Asana but ABSENT from the monolith map

**RULED — fail-closed toward exclusion, with a scaffold precedence correction.**

The monolith buckets only `Templates` as `ignore`; autom8y's `EXCLUDED_SECTION_NAMES`
additionally carries `Next Steps`, `Account Review`, `Account Error` — **local-only
exclusions the monolith never knew**. Under the *current* scaffold these names hit the
`bucket is None` branch and route to NEITHER set (EC-REG-1), because the
`name in EXCLUDED_SECTION_NAMES` check sits INSIDE the `bucket is not None` branch and
is therefore **unreachable** for local-only exclusions.

> **SVR (file-read)** — claim: *the scaffold checks EXCLUDED_SECTION_NAMES only after
> the bucket-None route-to-neither, making it unreachable for monolith-absent names*.
> anchor: `section_registry.py:309-325` marker_token: `if bucket is None:` … `continue`
> precedes `is_excluded = (bucket == "ignore") or (name in EXCLUDED_SECTION_NAMES)`.
> Verified this session.

Under the verified DENYLIST (§6.2), route-to-neither = **processed** — so the current
scaffold would silently PROCESS units sitting in `Next Steps` / `Account Review` /
`Account Error`. That is exactly the SCAR-REG-001 silent-misroute class the fix must
kill. **Disposition ruling (build-deliverable for W-REG):**

1. **Precedence correction (three-tier):**
   - **Tier 1 — local authoritative exclusion:** check `name ∈ EXCLUDED_SECTION_NAMES`
     **FIRST**, independent of monolith presence → route the live GID to
     `excluded_section_gids`. (Covers `Templates`, `Next Steps`, `Account Review`,
     `Account Error`.) This moves the `EXCLUDED_SECTION_NAMES` check *above* the
     bucket-None route-to-neither.
   - **Tier 2 — monolith bucket:** for names not excluded in Tier 1: `ignore` →
     excluded; a unit bucket (`active`/`activating`/`inactive`) → `unit_section_gids`.
   - **Tier 3 — genuine unknown (neither source):** a live name in NEITHER
     `EXCLUDED_SECTION_NAMES` NOR the monolith taxonomy → EC-REG-1 `live_name_no_bucket`
     finding, routed to NEITHER set.
2. **Tier-3 is BLOCKING, not advisory.** Because the denylist processes-by-default,
   any `live_name_no_bucket` finding is a **hard-stop**: the join result MUST NOT be
   wired into the live registry until the operator dispositions the unknown section.
   Surfacing alone (the scaffold's current behavior) is insufficient — surface AND halt.
3. **Divergence stays surfaced (unchanged):** the R-REG-4 `taxonomy_divergence` check
   (`section_registry.py:349-365`) already surfaces `monolith_ignore_names ^
   EXCLUDED_SECTION_NAMES` = `{Next Steps, Account Review, Account Error}` as
   present-only-in-`EXCLUDED_SECTION_NAMES`. Keep it — it is the informational record
   of *why* Tier-1 routed those names. Routing is fail-closed; the divergence is never
   auto-reconciled.

**Net:** local-only exclusions fail-closed toward exclusion (safe under denylist); only
a section unknown to BOTH sources blocks — never silently processes and never silently
excludes.

### 6.5 Expected join outcome (from the two verified name-sets)

| Live section name | Tier hit | Routed to | Finding |
|---|---|---|---|
| Templates | 1 (excluded-name; also monolith `ignore`) | excluded | R-REG-4? no (in monolith ignore) |
| Next Steps | 1 (excluded-name; monolith-absent) | excluded | taxonomy_divergence (informational) |
| Account Review | 1 (excluded-name; monolith-absent; dual-GID artifact) | excluded | taxonomy_divergence |
| Account Error | 1 (excluded-name; monolith-absent; dual-GID artifact) | excluded | taxonomy_divergence |
| Month 1, Consulting, Active | 2 (monolith `active`) | unit | — |
| Onboarding, Implementing, Delayed, Preview | 2 (monolith `activating`) | unit | — |
| Unengaged, Engaged, Scheduled, Paused, Cancelled, No Start | 2 (monolith `inactive`) | unit | — |
| *any brand-new live section* | 3 (unknown) | NEITHER | live_name_no_bucket → **BLOCK live-wiring** |

W-REG exit: 13 names → `unit_section_gids`; 4 names → `excluded_section_gids`; the 19
sequential placeholders and the `VERIFY-BEFORE-PROD (SCAR-REG-001)` annotations removed;
any Tier-3 finding blocks until operator-dispositioned.

---

## 7. RED-First Misroute Fixture — as a wrong-BUCKET assignment (two-sided)

Per shape §5 + the task's upgrade: the RED-first fixture proves a **wrong-BUCKET**
misroute (a section landing in the WRONG classification set), not merely a wrong-GID
mismatch. It is two-sided: the no-defect variant passes GREEN.

### 7.1 Primary teeth — join-level wrong-bucket (centered on the Disposition-(ii) defect)

- **Fixture input:** `name_to_gid = {"Account Review": "<live-gid-AR>", "Month 1":
  "<live-gid-M1>", …}` (synthetic live GIDs — NEVER real placeholders); `name_to_bucket`
  = the monolith map (which has NO `Account Review`).
- **DEFECT variant (RED):** the join WITHOUT the §6.4 Tier-1 precedence correction (the
  scaffold as-is) routes `"Account Review"` to NEITHER set (EC-REG-1) → its live GID is
  **absent from `excluded_section_gids`**. Assertion: `"<live-gid-AR>" ∉
  result.excluded_section_gids` → the section that MUST be excluded is not → **RED**
  (wrong bucket: belongs in `excluded`, landed in neither = processed downstream).
- **NO-DEFECT variant (GREEN):** the join WITH the Tier-1 correction routes
  `"Account Review"` → `excluded_section_gids`. Assertion: `"<live-gid-AR>" ∈
  result.excluded_section_gids` AND `∉ result.unit_section_gids` → **GREEN**.
- **Teeth property:** the fixture bites ONLY on the mis-bucketing (Tier-1 precedence)
  defect; a correct join passes. Two-sided, non-theatrical (not green-run-alone).

### 7.2 Consequence teeth — processor-level (proves the downstream harm)

- Drive the processor (`processor.process()`) with a unit row whose `section` =
  `"Account Review"` (name-fallback path, `section_gid` empty) against the join's
  `excluded_section_gids`.
- **DEFECT variant (RED):** with `"Account Review"` mis-bucketed out of the excluded
  set, the unit falls through to reconciliation matching → `result.excluded_count`
  does NOT increment for it → the excluded unit is **processed** → **RED**.
- **NO-DEFECT variant (GREEN):** with `"Account Review"` correctly excluded, the unit
  is skipped (`excluded_count` increments) → **GREEN**.
- This closes the loop from join-routing to the actual SCAR-REG-001 harm (a
  wrongly-processed unit polluting account classification).

### 7.3 Fixture hygiene

- FRESH construction per construction-exhaustion-ledger (no reused fixture).
- Synthetic GIDs only; the real placeholders stay untouched until the live W-IRIS
  receipt lands (R-REG-6 stays OUT until then).
- Rite-disjoint critic-clean per shape §10 Prescribed (RED-first + two-sided teeth +
  external critic).

---

## 8. Honest-Rung Ceiling (no rounding — G-RUNG)

Rung ladder (handoff §2, verbatim):
`authored < emitting < alerting < proven < merged < live < protecting-prod`.

**This design's ceiling line:** *This TDD/ADR is DESIGN-LOCKED. It enables a pipeline
that tops at **route-constructed + qa-proven (pre-deploy)**. W-REG reaches `proven`
ONLY post-deploy + live W-IRIS receipt; SCAR-REG-001 closes at `proven`; the traffic
cutover (`protecting-prod`) is a LATER user-sovereign decision, NOT this cycle.*

| Stage | Rung | Owner |
|---|---|---|
| This TDD + ADR | design-locked (pre-construction) | architect (this station) |
| Route constructed + qa-proven (RED-first teeth vs the constructed route, gates H1–H6/GATE-GAP-1) | route-constructed + qa-proven | principal-engineer + qa-adversary **(ceiling of this design's authority)** |
| Deploy the route/proxy | live | **USER-SOVEREIGN** |
| Live `GET /sections` receipt (W-IRIS) | receipt-present | iris (user-sovereign READ) |
| W-REG join wired + fixture GREEN vs receipt | proven | 10x-dev — **closes SCAR-REG-001** |
| Traffic cutover | protecting-prod | **USER-SOVEREIGN — NOT this cycle** |

`verified_realized` stays **HELD** — cutover value is unrealized until the live receipt
+ merge + deploy occur, all downstream of this design and (merge/deploy/cutover)
user-sovereign. This design does not, and must not, round any rung up.

---

## 9. Hard Constraints (binding on downstream construction)

- **No new scoped Asana token.** All FORK-R options route the EXISTING PAT. Minting a
  new scoped token is the forbidden crusade and is OUT for every branch.
- **No plaintext PAT anywhere** — ARN / secret-name / sha256-prefix only, in code,
  tests, fixtures, logs, and these artifacts.
- **No cutover / no traffic move** this cycle (shape north-star). `protecting-prod` is
  a later user-sovereign decision, not designed here.
- **No DEFER items** — rotation (`asana-pat-rotation-disabled-indefinite-validity`) and
  the `-thnc` sibling secret stay fenced (shape §10, handoff §5). Do not expand.
- **Monolith is READ-only** — `business_units/main.py` informs W-REG; never mutated.
- **FORK-R is surfaced, not selected** — the ADR is stamped AWAITING-OPERATOR-RATIFICATION.
- **Agent never merges/deploys/rotates/arms/WRITEs** — shape §10 user-sovereign levers.

---

## 10. Risk Assessment

| Risk | Prob | Impact | Mitigation |
|---|---|---|---|
| REUSE branch selected but existing route accepts PAT-plaintext (dual-mode) | MED | HIGH (forbidden path reachable) | §3.1 structural lever: swap `AsanaClientDualMode` → `require_service_claims` (JWT-only) so PAT-plaintext is impossible by construction |
| H2 allowlist skipped → route reads arbitrary projects | MED | MED (BOLA/IDOR widening) | H2 build-deliverable pins to `1201081073731555`; qa-hook proves `gid ∉ allowlist → 403/404` |
| W-REG wired with the scaffold's unreachable EXCLUDED_SECTION_NAMES branch | MED | HIGH (silent-process of Next Steps/Account Review/Account Error) | §6.4 Tier-1 precedence correction is a mandatory build-deliverable; §7.1 RED fixture bites exactly this defect |
| Unknown live section silently processed | LOW | HIGH (new SCAR-REG-001 instance) | §6.4 Tier-3 BLOCKING: any `live_name_no_bucket` finding halts live-wiring |
| GATE-GAP-1 not landed → native-PAT leak undetected | MED | MED (teeth unsound for native format) | GATE-GAP-1 must land with/before construction; qa-hook two-sided native decoy |
| Rung rounded up (design treated as proven) | LOW | HIGH (false closure of SCAR-REG-001) | §8 ceiling line; PT-04 hard gate; receipt-present strictly gates W-REG |
| Operator-ratification input assumed instead of confirmed | MED | HIGH (wrong branch built) | §4 makes reachability + S2S-JWT-mint an explicit operator input; ADR stamped AWAITING-OPERATOR-RATIFICATION |

---

## 11. Handoff Criteria (to principal-engineer / qa-adversary — post ratification)

- [ ] FORK-R ratified + branch selected (operator) — ADR un-stamped from AWAITING.
- [ ] Selected branch's §5 gate table bound as acceptance criteria (build OR audit).
- [ ] §6.4 Tier-1 precedence correction + Tier-3 BLOCKING implemented in the join
      wiring (W-REG), gated on the live W-IRIS receipt.
- [ ] §7 two-sided wrong-BUCKET fixture RED-first, then GREEN; rite-disjoint critic-clean.
- [ ] GATE-GAP-1 `.gitleaks.toml` native rule landed with two-sided teeth.
- [ ] Honest-rung ceiling (§8) preserved — no rung rounded up; W-REG gated on receipt.

---

*Architect station. DESIGN-LOCKED (both branches); construction AWAITING-OPERATOR-RATIFICATION.
Evidence grade MODERATE (self-ref ceiling; STRONG requires a rite-disjoint attester +
construction evidence). No code, no deploy, no plaintext PAT. FORK-R surfaced, not selected.
Companion: `.ledge/decisions/ADR-asana-pat-read-route-forkR-2026-07-02.md`.*
