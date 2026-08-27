---
# Schema of record: doc-artifact-schemas#prd-schema (structure + required fields).
# Namespace note: the PK- prefix is the phase-2 packet namespace (shape §2 exit
# artifact), a DELIBERATE, documented divergence from the PRD-* filesystem pattern —
# this is a packet-staged decision INPUT that ARMS an operator ruling, not a
# standalone PRD in the draft->approved lifecycle. All PRD required fields are present.
type: spec
artifact_id: PK-consent-journey-spec
title: "G-CONSENT-HUMAN — The Human Consent / Grant Journey (Delegated-Identity Minting Surface)"
created_at: "2026-07-24T00:00:00Z"
author: requirements-analyst
status: proposed        # .ledge/ shelf lifecycle: PROPOSED into the R4 packet, awaiting
                        # operator disposition. Deliberately NOT "accepted" (that would
                        # presume the R4 ruling; R33 presumes nothing) and NOT "draft" (the
                        # spec is complete + staged for the security/threat-modeler critic at
                        # CP-2). In PRD-schema terms (draft|review|approved|superseded) this
                        # maps to "review": complete, staged, not yet ruled on.
complexity: SERVICE     # the specified journey (if ruled buildable) spans a human web
                        # surface + auth-server consent/exchange endpoints + a cross-service
                        # token mint. Impact (below) routes to Architect regardless.

# Impact assessment (requirements-analyst mandate) — drives workflow routing.
impact: high
impact_categories: [security, auth, api_contract, cross_service]
# Rationale: the journey mints delegated authorization (authN/authZ flow change);
# it is a security-sensitive consent path; it names an auth-endpoint contract change
# (the G-CONSENT-HUMAN gate); and it spans the auth-server (mint) + satellite (consume).

# Packet metadata
phase: fleet-delegation-phase2
sprint: PK-1
lane: "10x-dev / requirements-analyst"
landing_mode: SURFACE                      # into the R4 packet; nothing auto-lands
feeds: PK-2 (R4 packet assembly)
parallel_to: [RD (re-derivation grid), SP (species-leg contract)]
external_critic: "security / threat-modeler (rite-disjoint) at CP-2"
governing_rulings: "R24-R34 constitution @origin/main dfdb84a3 (PR #270); R33 consent-lane spec-only; R4 reserved; R20 caveat i vendor ceiling; R22 transport hold 2026-07-28"
telos_binding: ".know/telos/fleet-delegation-portfolio.md (RATIFIED; BOUND not minted)"

# Source discipline
source_anchors:
  autom8y_asana_origin_main: dfdb84a3      # satellite (this repo); local main FROZEN pre-epic
  autom8y_monorepo_origin_main: 790465e0   # auth-server (cross-repo READ-ONLY via git show)
source_note: "Committed records read via `git show origin/main:<path>` after fresh fetch ONLY. .sos/wip scratch + stranded ledger artifacts read from the working tree by design. Auth-server line anchors were re-probed LIVE this dispatch @ 790465e0; they MOVE on release (frame UV-P #3) — PK-2/SP re-probe at assembly."

self_grade: "MODERATE (self-ref ceiling per self-ref-evidence-grade-rule; external corroboration = the CP-2 security/threat-modeler critic)"

success_criteria:
  - id: SC-001
    description: "The consent journey is specified end-to-end (authenticate -> present -> decide -> mint hand-off -> audit) such that an engineer not in the room could design the build from this document alone (the acid test)."
    testable: true
    priority: must-have
  - id: SC-002
    description: "The consenting principal is gated on HUMAN identity (require_human_token equivalent): an agent token cannot exercise grant/deny. The live G-CONSENT-HUMAN gate defect is named with its fix."
    testable: true
    priority: must-have
  - id: SC-003
    description: "Consent is INFORMED: the human is shown the requesting agent, the requested scopes, the delegated-token bounds (single-hop, ~30-min TTL), and the honest reach (fleet-plane; Asana-still-bot vendor ceiling) BEFORE deciding."
    testable: true
    priority: must-have
  - id: SC-004
    description: "Consent is SCOPED: requested scope is a subset of the delegator's actual OpenFGA permissions; excess is fully rejected (no silent scope reduction)."
    testable: true
    priority: must-have
  - id: SC-005
    description: "The DENY path is first-class; BOTH grant and deny are audited with delegating_user_id + acting_agent_id."
    testable: true
    priority: must-have
  - id: SC-006
    description: "The mint hand-off is specified: the consented decision deterministically yields the RFC-8693 delegated token (sub=human, act.sub=agent). Candidate mint paths are enumerated (option-enumeration-discipline); none is silently presumed."
    testable: true
    priority: must-have
  - id: SC-007
    description: "The spec carries the vendor ceiling (R20 caveat i) on its face and states unambiguously that it ARMS the R4 ruling, builds nothing (R33), and presumes no outcome."
    testable: true
    priority: must-have
  - id: SC-008
    description: "The G-CLIENT-REDIR/R22 transport dependency and the G-MIGRATION landing dependency are named as DEPENDENCIES (not built), appearing only in option/landing analysis where a landing depends on them."
    testable: true
    priority: should-have
  - id: SC-009
    description: "The inaugural Q3 ui-lane switch is recorded as MOOT-until-operator-rules; no ui-rite lane is presumed or switched this phase."
    testable: true
    priority: must-have

schema_version: "1.0"
---

# PK-1 — The Human Consent / Grant Journey (G-CONSENT-HUMAN)

> **PACKET-ARMING BANNER (carry on the face — do not strip).**
> This is a **SPECIFICATION ONLY** (R33). It **builds nothing**: no code, no UI, no
> migration, no endpoint change, no ui-rite switch. It **ARMS** the operator's R4
> ruling by specifying the *minting* leg of "minting + trusting + landing as ONE
> coherent whole" (R33). It **presumes no outcome**: R4 is untouched; the operator
> rules whether the consent journey is minted, trusted, and landed. Nothing here
> schedules, decides, or forecloses that ruling.

## 0. Where this sits (one paragraph)

The fleet north star is that internal AI agents act in real business workflows
carrying the invoking **human's own delegated identity** — never a shared machine
credential — so a real person is provably accountable for every action a machine
takes (telos `.know/telos/fleet-delegation-portfolio.md`). Three legs realize it, and
the phase-2 packet folds all three so the operator rules them as one whole:

| Leg | Question | Owner sprint | This spec |
|---|---|---|---|
| **Minting** | How does a human *grant* an agent their delegated identity? | **PK-1 (this)** | **IN** |
| **Trusting** | How does the satellite come to *know* the human (species consumption)? | SP | OUT (SP owns) |
| **Landing** | How does the audit line *name* "&lt;human&gt; via &lt;agent&gt;"? | RD | OUT (RD owns) |

The delegated-token **protocol** already exists auth-server-side (RFC-8693 exchange
mints `sub`=human, `act.sub`=agent). The **missing product piece** is the human
consent JOURNEY — the login-then-consent surface where a person authorizes the
agent. That absence is glint **G-04** and the crux of the remote-access spike. This
spec specifies that journey and its hand-off into the existing mint.

---

## 1. Executive Summary

**The problem.** A protocol-complete delegation surface has **no reachable human
grant moment.** The auth-server can mint a delegated token, and it *has* a consent
*contract* (`routers/authorize.py`), but "**consent machinery exists; a reachable
consent journey does not**" (spike §11.1, corrected finding). Worse, the one consent
endpoint that exists gates on the *wrong* identity tier: it accepts an **agent**
token where it must require a **human** — which means, as shipped, an agent could
approve its own delegation. That defect is precisely what this sprint's glint is
named for: **G-CONSENT-HUMAN**.

**The specification.** A human (a rep, or the operator) authenticates as a human,
is shown *which* agent is asking for *what* scope for *how long* and with *what real
reach*, and makes an **explicit, informed, human-only** grant-or-deny decision. On
grant, the consented decision hands off to the existing RFC-8693 exchange, which
mints a **single-hop, ~30-minute, scope-bounded** delegated token (`sub`=human,
`act.sub`=agent). Both grant and deny are audited. The human can revoke.

**What it deliberately does NOT do.** It does not provision OAuth client redirect
URIs (that is transport — **G-CLIENT-REDIR**, held behind **R22** until 2026-07-28).
It does not grant per-user *Asana* authority (the **vendor ceiling** — Asana still
sees the bot user until a separate, unscoped decision — **R20 caveat i**). It does
not build the species/validator consumption (SP) or the audit-line grammar (RD). And
it does not switch on a ui-rite lane — that is **moot until the operator rules**.

**Why now / why in the packet.** R24 terminated the re-derivation "**in exactly this
packet**"; R33 folds the consent journey into it "so the operator rules on minting +
trusting + landing as ONE coherent whole." Sequencing consent *after* the keystone
wiring would idle the keystone — agents wait on consent regardless (SL-2 rationale).

---

## 2. Scope Boundaries (explicit, scope-creep-resistant)

### 2.1 IN scope — the human grant journey (G-CONSENT-HUMAN)

- **The grant surface**: what a human sees and touches to authorize an agent.
- **Consent semantics**: informed, explicit, human-gated, scoped, bounded,
  attributable, revocable (§6 — the heart of this spec).
- **The mint hand-off**: how a consented decision becomes the delegated token the
  auth-server issues (§7), including the G-CONSENT-HUMAN gate correction.
- **The deny path, the audit of both outcomes, and revocation.**
- **The honest-reach disclosure** the consent screen must carry (the vendor ceiling,
  stated to the human so consent is not misinformed).

### 2.2 OUT of build scope — MAY appear only in option/landing analysis

- **G-CLIENT-REDIR / `redirect_uris` provisioning** — the transport by which an
  external client (claude.ai, Claude Code, Desktop) redirects a human's browser to
  the consent surface. This stays with the **transport stream behind R22** (WS-6).
  It appears in this spec **only** as a named *dependency* where a *production*
  (external-client) landing of the journey depends on it (§8), per the frame's
  explicit allowance — never as something this spec builds or specifies to build.
- **Per-user Asana OAuth** — the vendor-ceiling remedy (R20 caveat i). Carried on the
  face (§6.7) as a boundary the human must be told about; **not** in scope to design.

### 2.3 OUT — owned by a sibling sprint (named to prevent conflation)

- **Species / validator consumption** — how the satellite *validates and consumes*
  the delegated token (SDK actor-claim modeling, validator widening). **SP owns this.**
  This spec stops at the mint; where the token is *consumed* is SP's boundary.
- **Audit-line landing grammar** — how "&lt;human&gt; via &lt;agent&gt;" is written into
  the business record or structured logs. **RD owns this.** This spec produces the
  *identity* RD's landings name; it does not choose the landing.

### 2.4 OUT — by ruling / posture

- **Any BUILD** (R33) — spec only; zero build artifacts.
- **The ui-rite lane switch** — the inaugural Q3 ui-lane switch (`ari sync --rite=ui`
  in the a8 repo) is **MOOT until the operator rules** (R33; frame §6). Recorded as
  such in §10; **not presumed, not requested, not scheduled** by this spec.
- **The action-time confirm gate (RB-1 / R5)** — already shipped
  (`mcp/asana_mcp/tools/confirm_gate.py`), a *distinct* trust surface (§6.8). Named
  only to prevent conflation with grant-time consent.

---

## 3. Grounding — SVR Premise Ledger (receipted this dispatch)

Source discipline: satellite anchors @ `git show origin/main:` (dfdb84a3); auth-server
anchors @ the autom8y monorepo `git show origin/main:` (790465e0), **re-probed live
this dispatch**. Auth-server lines move on release (frame UV-P #3) — carried, and
flagged for PK-2/SP re-probe at assembly.

**P1 — The consent MACHINERY exists (a consent CONTRACT), but gates on the wrong tier.**

```yaml
structural_verification_receipt:
  claim: "the auth-server /authorize consent endpoints exist and already model a grant/deny consent contract, but they gate the consenting principal on get_current_user (which accepts agent tokens), NOT on require_human_token"
  verification_method: file-read
  verification_anchor:
    source: "git -C .../autom8y show origin/main:services/auth/autom8y_auth_server/routers/authorize.py (origin/main = 790465e0)"
    line_range: "L22 + L105 + L117 + L207 + L209 + L227 + L232 + L268 + L280 + L320"
    marker_token: "from autom8y_auth_server.app.dependencies import get_current_user, get_db, get_redis"
    claim: "authorize.py imports get_current_user at L22 (NOT require_human_token); authorize_get (L105) and authorize_post (L227) both Depends(get_current_user) (L117, L232); GET returns client_name (L207) + requested_scopes (L209) for a UI; POST reads body.authorize with a deny branch (if not body.authorize:, L268 -> return L280) and an approve return (L320). The consent contract is present; the human-gating is not."
```

**P2 — The human gate EXISTS one import away; the mint already uses it, the consent surface does not.**

```yaml
structural_verification_receipt:
  claim: "require_human_token rejects agent tokens and is the correct tier for a human-only decision; the RFC-8693 mint already gates on it, revealing an asymmetry with the /authorize consent surface"
  verification_method: file-read
  verification_anchor:
    source: "git -C .../autom8y show origin/main:services/auth/autom8y_auth_server/app/dependencies.py (790465e0)"
    line_range: "L84 + L98 + L174 + L183-L186"
    marker_token: "Both user_access and agent_access tokens are accepted."
    claim: "get_current_user (L84) accepts BOTH user_access and agent_access (docstring L98); require_human_token (L174) permits ONLY user_access ('any new token_type is automatically rejected (fail-closed)', enforced L183-186). The exchange endpoint gates on require_human_token; /authorize does not — the G-CONSENT-HUMAN defect."
```

**P3 — The mint hand-off is real: sub=human, act.sub=agent, single-hop, 30-min TTL, scope-bounded.**

```yaml
structural_verification_receipt:
  claim: "the RFC-8693 agent-token exchange, gated on a human token, mints a delegated token carrying an act claim (sub=delegating human, act.sub=agent), TTL 30 minutes, with requested scope fully rejected if it exceeds the delegator's OpenFGA permissions"
  verification_method: file-read
  verification_anchor:
    source: "git -C .../autom8y show origin/main:services/auth/autom8y_auth_server/routers/tokens.py + services/token_service.py (790465e0)"
    line_range: "tokens.py L405 + L409 + L466 + L480 ; token_service.py L403 + L414-L416 + L422 + L425-L426 + L434"
    marker_token: "sub = delegating user, act.sub = agent identity."
    claim: "agent_token_exchange (tokens.py L405) Depends(require_human_token) (L409), validate_delegator_scope full-reject on excess (L466; AUTH-TEB-003 scope_exceeds_granted 403), then create_agent_token (L480). token_service.create_agent_token (L403) sets sub=user_id (L422), act.sub=agent:{session} (L425-426), ttl=AGENT_TOKEN_TTL_SECONDS (L434), docstring 'TTL: 30 minutes (BIND #18)' (L414-416). NOTE: earlier probes cited tokens.py:157-258 for this endpoint; it now resolves at :405 — drift confirms frame UV-P #3."
```

**P4 — G-MIGRATION: the table written on consent-approval has no migration (a landing dependency).**

```yaml
structural_verification_receipt:
  claim: "the authorization_codes table (written when a human approves at /authorize) has no Alembic migration among the auth-server migration versions, so a clean-bootstrap environment would 500 the moment consent is granted"
  verification_method: bash-probe
  verification_anchor:
    source: "for f in $(git ls-tree -r origin/main --name-only | grep -E 'services/auth/.*migrations/versions/.*\\.py$'); do git show origin/main:$f | grep -il 'authorization_codes' && echo MATCH; done ; (count) ... | wc -l"
    command_output_verbatim: "(zero MATCH lines)\n39"
    exit_code: 0
    claim: "39 auth migration version files exist; ZERO contain 'authorization_codes'. The approval write-target has no schema migration — same DB-contract-drift class as the external_business_id/FW-A3 case. This is a LANDING dependency the packet must surface (the fix is auth-server migration work — mechanical, R25 effect-not-repo)."
```

**P5 — The vendor ceiling (R20 caveat i): even perfect in-fleet consent leaves Asana acting as the bot.**

```yaml
structural_verification_receipt:
  claim: "the satellite substitutes a single shared bot PAT for every downstream Asana call; a fleet-plane delegated grant does not confer per-user Asana authority — Asana's own API, object permissions, 'created by', and comment authorship still read as the bot"
  verification_method: file-read
  verification_anchor:
    source: "git show origin/main:src/autom8_asana/api/dependencies.py (asana dfdb84a3) + research §6"
    line_range: "L242 + L247-L280 ; research :113-121"
    marker_token: "asana_pat=bot_pat"
    claim: "in JWT mode the identity is replaced by the shared bot PAT at dependencies.py:242 and the bot-PAT client is handed to routes (:247-280). Closing this requires per-user Asana OAuth, which no artifact in either repo scopes (R20 caveat i) — a vendor/product decision above the code. The consent screen MUST disclose this so consent is not misinformed."
```

**Anchor drift / re-probe note (carry to PK-2).** All auth-server anchors above are
live @ 790465e0 this dispatch. The frame's cross-repo UV-P (`tokens.py:405`,
`audit_log.py:45-46`, `client.py:336`) and the `:157-258 -> :405` drift both attest
that **these lines move on release**. PK-2/SP MUST re-run these probes at packet
assembly; the *findings* (a consent contract exists; it gates on the wrong tier; the
mint requires a human; G-MIGRATION; the vendor ceiling) are structural and stable
even as the exact line numbers drift.

---

## 4. Actors & Stakeholders

| Actor | Role in the journey | Notes |
|---|---|---|
| **Delegating human** (rep / operator) | The principal who grants authority. Authenticates as a human; makes the grant/deny decision. | Must be a *human* token holder (P2). The operator is the first delegator (dogfood witness). |
| **Agent (client)** | The party requesting to act *as* the human. Identified on the consent screen. | Named `act.sub = agent:{session}` in the minted token (P3). MUST NOT be able to self-consent. |
| **Auth-server** | Authenticates the human, presents the consent contract, records the decision, mints the delegated token. | Owns `/authorize` + the RFC-8693 exchange. Cross-repo (autom8y monorepo). |
| **Satellite (autom8y-asana)** | Later *consumes* the minted token. | **SP's boundary** — out of this spec. |
| **Operator** | Rules R4 (mint/trust/land). Sole approver of the identity gate (R29) and who-may-use (R4). | This spec ARMS the ruling; the operator takes it. |
| **QA / threat-modeler** | Verifies the consent semantics adversarially. | The CP-2 rite-disjoint critic of this spec. |

---

## 5. User Stories

**US-001 — A rep grants an agent their delegated identity.**
> As a rep, I want to authorize a named agent to act on my behalf with a specific,
> time-bounded scope, so that the agent can do real work in my name and I remain
> provably accountable — without handing over a shared machine credential.
- **AC-1**: I authenticate as *myself* (a human) before any consent is possible.
- **AC-2**: I see *which* agent is asking, *what* scopes it wants, *how long* the
  grant lasts (~30 min), that it is *single-hop* (the agent cannot re-delegate), and
  the *honest reach* (fleet-plane; Asana actions still appear as the bot — §6.7).
- **AC-3**: I make an explicit **Grant** or **Deny** choice; neither is pre-selected.
- **AC-4**: On Grant, a delegated token (`sub`=me, `act.sub`=agent) is minted and the
  agent can act; on Deny, nothing is minted and the attempt is recorded.

**US-002 — A rep denies (or later revokes) a grant.**
> As a rep, I want to deny a request I do not recognize, and revoke a grant I made,
> so that I stay in control of what acts in my name.
- **AC-1**: Deny is a first-class, one-click path; it mints nothing.
- **AC-2**: I can revoke an active grant before its TTL expires (§6.6); after
  revocation the delegated token no longer authorizes action.
- **AC-3**: Both deny and revoke are audited (who, which agent, when).

**US-003 — The operator dogfoods the grant (the live-witness leg).**
> As the operator, I want a minimal path to grant my own delegated identity, so that
> I can be the live witness that "an agent bearing my OWN delegated identity" acts —
> the moment the realized bar witnesses (telos predicate).
- **AC-1**: A minimal grant path exists that does not require the full external-client
  transport (G-CLIENT-REDIR/R22) — an internal/direct sign-in to my own auth server
  (§8.1, dogfool posture).
- **AC-2**: The dogfood grant produces the *same* token shape as the production path
  (`sub`=human, `act.sub`=agent) so the witness is valid.

**US-004 — A security reviewer verifies consent cannot be forged.**
> As a threat-modeler, I want to confirm that only a human can consent, that scope
> cannot exceed the delegator's, and that an agent cannot self-authorize, so that the
> delegation is trustworthy.
- **AC-1**: An agent token presented to the consent surface is rejected (not accepted
  as the consenter) — the G-CONSENT-HUMAN fix.
- **AC-2**: A requested scope exceeding the delegator's OpenFGA permissions is fully
  rejected (no silent narrowing).
- **AC-3**: The minted token is single-hop; a re-delegation attempt fails.

---

## 6. Consent Semantics (the heart of the spec)

Six properties an authorization must satisfy to be a *valid delegated-identity grant*.
Each has a testable condition and a live evidence anchor.

### 6.1 INFORMED
The human is presented, **before** deciding: the requesting **agent** (client name),
the **requested scopes** (in human-readable terms), the **bounds** (single-hop,
~30-min TTL), and the **honest reach** (§6.7). The consent *contract* already returns
`client_name` + `requested_scopes` (P1, `authorize.py:207/:209`); this spec requires
the presentation to additionally carry bounds + reach. *Untested claim to avoid:
"the human knows what they're granting" — the screen must SHOW it, not assume it.*

### 6.2 EXPLICIT
An affirmative act (`authorize: true`), never implied or defaulted. **Deny is a
first-class path** with its own audited outcome (P1, `authorize.py:268/:280`). No
"silence = consent."

### 6.3 HUMAN-GATED  *(the G-CONSENT-HUMAN correction — MUST)*
The consenting principal **must be a human** (`require_human_token`), not an agent.
Today `/authorize` gates on `get_current_user`, which **accepts agent tokens** (P1,
P2) — so an agent could exercise approve/deny on a delegation. **This must switch to
`require_human_token` before consent is trustworthy.** The mint endpoint already does
this (P3, `tokens.py:409`); the asymmetry is the defect. *This is the single most
load-bearing consent requirement.*

### 6.4 SCOPED
The requested scope MUST be a subset of the delegator's **actual OpenFGA
permissions**; excess is **fully rejected**, not silently reduced (P3,
`validate_delegator_scope`, `tokens.py:466`; AUTH-TEB-003 403). A human cannot grant
authority they do not themselves hold.

### 6.5 BOUNDED
The minted delegation is **single-hop** (the agent cannot re-delegate — enforced
because only a *human* token can trigger the exchange, P2/P3) and **TTL-bound**
(~30 min, P3, `token_service.py:414-416/:434`). Bounded blast radius by construction.

### 6.6 ATTRIBUTABLE & REVOCABLE
Every grant records **who** authorized **whom** (`delegating_user_id` +
`acting_agent_id` — the attribution spine, glint G-08). Both grant and deny are
audited (`log_event`, `authorize.py:26`). The human can **revoke** an active grant
before TTL; revocation invalidates the delegated token (the auth-server already
carries a revocation surface — `routers/tokens.py` revoke path, `:160`).

### 6.7 HONEST REACH — the vendor ceiling on the consent screen  *(MUST)*
The consent screen MUST state, in terms the human understands, that this grant is a
**fleet-plane delegation**: the agent acts as the human *inside the fleet*, and the
**audit line names the human** — but **Asana's own product API still acts as the
bot** (created-by, comment authorship, object permissions read as the bot) until a
separate, unscoped **per-user Asana OAuth** decision (R20 caveat i, P5). Omitting
this makes the consent *misinformed*: the human might believe they are granting
Asana-level authority they are not. **Carrying the ceiling is a consent-integrity
requirement, not a footnote.**

### 6.8 NOT the action-time confirm gate  *(anti-conflation)*
Grant-time consent (this spec) — a one-time, TTL-bounded authorization that mints the
delegated identity — is **distinct** from the **action-time confirm gate** (RB-1 /
R5, already shipped, `mcp/asana_mcp/tools/confirm_gate.py`), which pauses each
automation-triggering *write* for a per-action "human yes." They compose (a granted
agent's trigger-writes still hit the confirm gate) but are different moments. The
packet reader should see both without conflating them.

---

## 7. The Mint Hand-off (consent -> delegated token)

**What "mint hand-off" means here:** the deterministic path from a human's *consented
decision* to the *issued* RFC-8693 delegated token. The token protocol exists (P3);
this section specifies *how consent triggers it* and enumerates the candidate wirings
**without presuming one** (option-enumeration-discipline — the architect/operator
choose; this spec surfaces).

### 7.1 The invariant (all options must satisfy)
On grant, a delegated token is issued with: `sub` = the delegating human; `act.sub` =
the agent; `scope` subset of the delegator's OpenFGA perms (full-reject on excess);
single-hop; ~30-min TTL. On deny, nothing is minted. Both outcomes audited.

### 7.2 Candidate mint paths (enumerated; none presumed)

| # | Path | How consent triggers the mint | Cost / gate | Note |
|---|---|---|---|---|
| **M-1** | **Direct RFC-8693 exchange.** The consent decision authenticates the human, whose human token is exchanged at `agent_token_exchange` for the delegated token. | Human consents -> human `user_access` token -> `POST` exchange (`tokens.py:405`, `require_human_token`) -> `create_agent_token`. | Mint already human-gated (P3). Consent UX front is the build. | Cleanest identity story; the exchange is the delegation-native path. |
| **M-2** | **OAuth authorization-code + consent.** The `/authorize` consent issues an authorization_code the client redeems for the delegated token. | Human consents at `/authorize` (approve, `:320`) -> authorization_code -> redeemed at token endpoint. | Requires the **G-CONSENT-HUMAN** gate fix (P1/P2) AND hits the **G-MIGRATION** blocker (P4). | Standard OAuth; but the consent endpoint currently under-gates and the code table has no migration. |
| **M-3** | **Composed.** OAuth `/authorize` for *client* consent, then RFC-8693 exchange for the *delegation* (act-claim). | Human consents to the client at `/authorize`; the agent then exchanges the human's session token for the act-claim token. | Both fixes above; two moments to reconcile. | Most faithful to how the two surfaces exist today, but the most wiring to specify. |

**Requirements-analyst finding (surfaced, not decided):** M-1 and M-2/M-3 differ in
*which* surface carries the human gate. The **exchange already requires a human**
(P3); the **`/authorize` consent does not** (P1/P2). Therefore any path that routes
consent through `/authorize` (M-2, M-3) **inherits the G-CONSENT-HUMAN fix as a
precondition**, and M-2's approval write inherits **G-MIGRATION** as a landing
blocker. The architect/operator choose the path in PK-2/at-ruling; this spec fixes
only that **the human gate must sit on whichever surface carries the consent
decision.**

### 7.3 The gate-fix, precisely
Wherever the human's consent decision is taken, that endpoint MUST gate on
`require_human_token` (or equivalent human-only tier), not `get_current_user`. This
is an **auth-endpoint contract change** (hence `impact_categories: [... api_contract]`).
It is **specified here, executed nowhere** (R33; R29 — the identity gate; the change
merges only on the operator's word).

---

## 8. Dependencies (named; not built)

Per the frame's allowance, transport/landing dependencies appear here **only** where a
consent-journey landing depends on them.

### 8.1 Reachability has two postures
- **Dogfood / internal (US-003):** a human signs into their own auth server directly
  (minimal grant path). This may **not** require the full external-client transport —
  it is the live-witness leg (SL-2: "dogfood may use a minimal grant path"). This
  posture depends on: the G-CONSENT-HUMAN gate fix (§7.3) and, for M-2, G-MIGRATION.
- **Production / external client (claude.ai, Claude Code, Desktop):** an external
  agent redirects the human's browser to the consent surface. This posture depends on
  **G-CLIENT-REDIR / R22** (redirect-capable client provisioning, PRM, port-agnostic
  loopback matching) — **out of build scope**, held behind the transport gate
  (2026-07-28). The consent journey does not build this; it *waits on* it for the
  external posture.

### 8.2 Dependency register

| Dep | On what | Blocks | Owner / gate | This spec |
|---|---|---|---|---|
| **G-CLIENT-REDIR** | redirect_uris provisioning, PRM, loopback matching | the *production/external* posture only | transport stream / R22 (2026-07-28) | Named as dependency; **not built** |
| **G-MIGRATION** | `authorization_codes` Alembic migration (P4) | M-2 (OAuth-code) mint landing in a clean env | auth-server (mechanical; R25 effect-not-repo) | Named; fix is auth-server work, surfaced |
| **G-CONSENT-HUMAN gate fix** | `require_human_token` on the consent surface (§7.3) | trustworthy consent on any `/authorize`-routed path | auth-server; R29 identity gate (operator word) | Specified; **not merged/flipped** |
| **SP species contract** | satellite consuming `act`=agent | *downstream* trust (not the mint) | SP sprint | Boundary — out |
| **RD landing grid** | audit-line grammar | *downstream* landing (not the mint) | RD sprint | Boundary — out |

---

## 9. Functional Requirements (MoSCoW)

Prioritized by "what happens if we ship without this?" (anti-inflation: only items
whose absence makes the delegation *untrustworthy or broken* are Must).

### MUST (delegation is untrustworthy/broken without)
- **FR-M1** — The consenting principal is gated on **human** identity; an agent token
  cannot grant/deny (G-CONSENT-HUMAN fix). *Without: an agent self-authorizes; the grant is meaningless.*
- **FR-M2** — The consent presentation shows **agent + scopes + bounds (single-hop,
  ~30-min TTL) + honest reach** before the decision. *Without: consent is not informed, thus not valid.*
- **FR-M3** — The decision is **explicit** (affirmative grant), with **deny** as a
  first-class audited path. *Without: silence-as-consent; no clean refusal.*
- **FR-M4** — Requested **scope ⊆ delegator's OpenFGA perms**, full-reject on excess.
  *Without: privilege escalation via delegation.*
- **FR-M5** — On grant, the **mint hand-off** yields `sub`=human, `act.sub`=agent,
  single-hop, TTL-bounded (§7). *Without: no delegated identity is produced.*
- **FR-M6** — **Both grant and deny are audited** with `delegating_user_id` +
  `acting_agent_id`. *Without: the accountability the whole north star exists for is absent.*
- **FR-M7** — The consent surface carries the **vendor ceiling** disclosure (§6.7).
  *Without: consent is misinformed about real reach.*

### SHOULD (strongly wanted; documented workaround exists)
- **FR-S1** — A **revocation surface**: the human revokes an active grant before TTL.
  *Workaround: wait out the ~30-min TTL.*
- **FR-S2** — An **active-grants view**: which agents currently hold my delegation.
  *Workaround: infer from audit log.*
- **FR-S3** — **WCAG 2.2 AA** for the consent surface (a consent screen a human
  cannot perceive/operate cannot yield informed consent). *Elevates to MUST if built as the production human UX.*
- **FR-S4** — A **scope step-up** re-consent flow when an agent needs broader scope
  mid-session. *Workaround: deny + new grant.*

### COULD (nice; deferrable)
- **FR-C1** — A consent **receipt** (what I granted, to whom, when) surfaced to the human.
- **FR-C2** — **Remember-this-agent** within a bounded trust window (reduces re-prompt;
  trades against explicit-consent — design with care).
- **FR-C3** — Branded/themed consent screen.
- **FR-C4** — Localization / multi-language.

### WON'T (this scope / this phase — explicit)
- **FR-W1** — G-CLIENT-REDIR / redirect_uris provisioning (R22/WS-6 transport).
- **FR-W2** — Per-user Asana OAuth (vendor ceiling; separate unscoped decision).
- **FR-W3** — Species/validator consumption (SP).
- **FR-W4** — Audit-line landing grammar (RD).
- **FR-W5** — The action-time confirm gate (RB-1 — already shipped; distinct surface).
- **FR-W6** — Any BUILD (R33).
- **FR-W7** — The ui-rite lane switch (moot until operator rules).

---

## 10. Non-Functional Requirements (measurable)

| ID | Requirement | Target (testable) |
|---|---|---|
| **NFR-1 (security)** | The consent decision is human-only. | An `agent_access` token presented to the consent surface receives an authZ rejection (403/401), never an approve/deny capability. |
| **NFR-2 (security)** | No scope escalation. | A requested scope not held by the delegator yields full rejection (AUTH-TEB-003 / 403); zero partial grants. |
| **NFR-3 (security)** | Bounded blast radius. | Minted token TTL ≤ 30 min; single-hop verified (a re-delegation / agent-initiated exchange fails). |
| **NFR-4 (auditability)** | Every outcome is attributable. | 100% of grant AND deny events emit a log carrying `delegating_user_id` + `acting_agent_id` + timestamp. |
| **NFR-5 (integrity)** | Informed-consent completeness. | The consent presentation contains all of {agent, scopes, TTL, single-hop, vendor-ceiling reach}; a missing element fails review. |
| **NFR-6 (accessibility)** | Perceivable/operable consent (if built as production UX). | WCAG 2.2 AA on the consent surface (a11y-engineer zero-tolerance gate, if the ui-rite lane is later ruled on). |
| **NFR-7 (resilience)** | Consent-grant does not 500 on a clean env. | The approval write-path has a schema migration (G-MIGRATION resolved) OR the mint path chosen (M-1) does not depend on `authorization_codes`. |
| **NFR-8 (latency)** | Grant is not a friction wall. | Consent presentation renders and the mint completes within an interactive budget (target < 2 s end-to-end for the decision->token step), transport excluded. |

---

## 11. Edge Case Inventory (systematic)

Boundaries, empty/error states, concurrency, permissions, reversibility.

| # | Edge case | Expected behavior |
|---|---|---|
| **E-1** | **Agent token presented as the consenter** (the G-CONSENT-HUMAN attack). | Rejected — only a human token may consent (FR-M1). This is the defect the fix closes. |
| **E-2** | **Requested scope exceeds delegator's perms.** | Full rejection, no partial grant (FR-M4; AUTH-TEB-003 403). |
| **E-3** | **Clean-bootstrap env, first consent granted (G-MIGRATION).** | Must not 500. Either the migration exists (NFR-7) or the chosen mint path (M-1) avoids `authorization_codes`. Surfaced as a landing dependency. |
| **E-4** | **TTL expires mid-action.** | The delegated token stops authorizing; the agent must re-obtain consent (or a refresh path, if specified). No silent extension. |
| **E-5** | **Human denies.** | Nothing minted; deny audited; the agent receives an unambiguous refusal (not an error that looks like a bug). |
| **E-6** | **Human revokes before TTL.** | The delegated token no longer authorizes; revocation audited (FR-S1). |
| **E-7** | **Re-delegation attempt** (agent tries to delegate onward). | Fails — single-hop by construction (only a human token triggers the exchange). |
| **E-8** | **Concurrent grants** (two agents, or two sessions of one agent). | Each grant is independently scoped/TTL'd/attributable; one does not widen another. |
| **E-9** | **Consent screen reached without a human session** (no login-redirect chaining today; ADR-0018 no-cookie design). | The journey must define how the human is authenticated *first* (a login step precedes consent); it cannot assume a pre-existing Bearer token (spike §11.1 structural blocker). |
| **E-10** | **External client with no provisioned redirect (G-CLIENT-REDIR absent).** | The *production* posture is unreachable until R22; the *dogfood* posture (direct sign-in) still works (§8.1). Not a bug — a named transport dependency. |
| **E-11** | **Vendor-ceiling confusion** (human believes they granted Asana authority). | Prevented by the FR-M7 disclosure; absence of the disclosure is a review failure, not a runtime error. |
| **E-12** | **Scope presented in opaque terms** (raw scope strings). | Requested scopes must be rendered human-readable; raw `resource:verb` strings alone fail informed-consent (NFR-5). |

---

## 12. Contradictions & Tensions (surfaced early)

- **T-1 — Human gate asymmetry.** The mint requires a human (`require_human_token`);
  the consent surface does not (`get_current_user`). Any consent routed through
  `/authorize` inherits the fix (§7.3). *Resolved by specifying the gate on the
  decision-carrying surface.*
- **T-2 — No-session design vs a browser consent journey.** ADR-0018 ratified a
  no-cookie/no-session posture (zero `set_cookie` repo-wide; spike §11.1); a reachable
  human consent journey needs the human authenticated *then* consenting. The journey
  must specify how login precedes consent **without** presuming a session layer the
  architecture disallows — or surface the tension to the architect if a session is
  genuinely required. *Surfaced; the resolution is architect/auth-server design, not
  this spec's to decide.*
- **T-3 — Dogfood-minimal vs production-grade.** The operator's live-witness leg wants
  the *smallest* grant path; the product wants a production-grade UX. Both are valid;
  §8.1 separates the postures so neither blocks the other.
- **T-4 — Explicit consent vs remember-this-agent (FR-C2).** Convenience trades
  against the explicit-consent property (§6.2). If pursued, bound the trust window and
  keep revocation cheap. *Flagged, not resolved.*

---

## 13. Success Criteria (SMART; testable by the CP-2 critic)

Mirrors the frontmatter. Each is verifiable by the security/threat-modeler critic or
by an engineer reading for buildability.

- **SC-001** — End-to-end journey specified (authN -> present -> decide -> mint -> audit).
  *Verify:* the acid test — an Architect/PE reads this and can design the build with **zero** clarifying questions.
- **SC-002** — Human-gated consent named with fix (G-CONSENT-HUMAN). *Verify:* §6.3 + P1/P2 + FR-M1 + E-1.
- **SC-003** — Informed consent (agent+scopes+bounds+reach). *Verify:* §6.1/§6.7 + FR-M2/M7 + NFR-5.
- **SC-004** — Scope ⊆ delegator, full-reject. *Verify:* §6.4 + FR-M4 + NFR-2 + E-2.
- **SC-005** — Deny first-class; both outcomes audited. *Verify:* §6.2/§6.6 + FR-M3/M6 + NFR-4 + E-5.
- **SC-006** — Mint hand-off specified; paths enumerated, none presumed. *Verify:* §7 (M-1/M-2/M-3) + the §7.2 finding.
- **SC-007** — Vendor ceiling on the face; arms-not-takes stated. *Verify:* the banner (§top) + §6.7 + §14.
- **SC-008** — G-CLIENT-REDIR/R22 + G-MIGRATION named as dependencies only. *Verify:* §8 register.
- **SC-009** — ui-lane switch recorded moot-until-ruled. *Verify:* §2.4 + §15.

---

## 14. Out of Scope (explicit, scope-creep-resistant)

Scope-creep toward any of these is a spec violation, not a judgment call.

- **The R4 ruling itself** — operator-only. This spec arms it; nothing here takes,
  schedules, or presumes it.
- **Any BUILD** (R33) — no code, UI, migration, or endpoint change is produced.
- **G-CLIENT-REDIR / redirect_uris provisioning** — transport (R22/WS-6).
- **Per-user Asana OAuth** — the vendor-ceiling remedy (R20 caveat i); a separate,
  unscoped decision above the code.
- **Species / validator consumption** — SP owns it (this spec stops at the mint).
- **Audit-line landing grammar** — RD owns it.
- **The ui-rite lane switch** — moot until the operator rules (§15).
- **The action-time confirm gate (RB-1/R5)** — already shipped; distinct surface.

---

## 15. Open Questions — For the Operator's Ruling (the packet surfaces, does not decide)

1. **Mint path** — M-1 (direct RFC-8693 exchange), M-2 (OAuth-code), or M-3
   (composed)? Each carries different preconditions (§7.2). *Surfaced; architect/operator choose.*
2. **Dogfood vs production first** — minimal internal grant path (live-witness leg)
   before, or alongside, the production UX? (§8.1)
3. **The ui-rite lane** — the inaugural Q3 ui-lane switch (`ari sync --rite=ui` in the
   a8 repo; prior-shape U1 named a ui-rite lane with copy-strategist,
   design-system-steward, rendering-architect, component-engineer, a11y-engineer) is
   **MOOT until the operator rules** (R33; frame §6). **This spec does not presume,
   request, or schedule it.** If the operator rules to build, *then* the lane question
   is live; until then it is recorded here as pending-the-ruling, nothing more.
4. **The G-CONSENT-HUMAN gate fix + G-MIGRATION** are auth-server changes behind the
   R29 identity gate — do they land as part of the consent build, or as a pre-cleared
   floor item? *Operator's call; both are named, neither is flipped here.*

---

## 16. Handoff & Attestation

### 16.1 The acid test
> *"Could an engineer who was not in the room design exactly the consent journey the
> operator wants, using only this document?"*

This spec is built to pass it: the journey stages (§5, §7), the semantics (§6), the
requirements (§9-§10), the edges (§11), the tensions (§12), and the named dependencies
(§8) are all present. The **one** thing it deliberately leaves open — the mint-path
choice (§15 Q1) — is enumerated with its trade-offs so the *decision* is teed up, not
missing. If the CP-2 critic or PK-2's architect has a *clarifying* question (vs a
*decision* question), the spec is incomplete and bounces at DELTA scope.

### 16.2 Handoff to PK-2
PK-2 folds this spec (the *minting* leg) with the RD grid (*landing*) and the SP
contract (*trusting*) into the one R4 packet. PK-2 binds to the **stable artifact id**
`PK-consent-journey-spec` (shape §6), never to sprint numbering. Carry-forward for
PK-2: re-probe the §3 auth-server anchors at assembly (lines move on release); keep
the vendor ceiling and the arms-not-takes banner on the packet's face.

### 16.3 Discipline attestation
- **Spec-only (R33):** zero build artifacts — no code, UI, migration, endpoint change,
  or ui-rite switch was produced. This document is the sole output.
- **Arms, presumes nothing:** the banner (§top), §14, and §15 keep R4 untouched.
- **Option-enumeration-discipline:** the mint paths (M-1/M-2/M-3) and reachability
  postures (§8.1) are enumerated with costs; none is silently presumed.
- **Vendor ceiling carried (R20 caveat i):** §6.7 + P5, on the face.
- **Anti-inflation MoSCoW:** 7 Must (each with a "broken/untrustworthy without"
  rationale), 4 Should (with workarounds), 4 Could, 7 Won't — a negotiated distribution.
- **Source discipline:** satellite @ dfdb84a3; auth-server @ 790465e0, re-probed live;
  drift flagged (§3 note).
- **Self-grade: MODERATE** (self-ref ceiling per self-ref-evidence-grade-rule).
  External corroboration = the CP-2 security/threat-modeler rite-disjoint critic.

### 16.4 Attestation table (absolute paths)

| Artifact | Absolute path | State |
|---|---|---|
| **This spec** | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/PK-consent-journey-spec-2026-07-24.md` | authored, working-tree, SURFACED (uncommitted — operator disposition) |
| Frame (PK envelope) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/frames/fleet-delegation-phase2.md` | read (§4-PK) |
| Shape (PK-1 sprint) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/frames/fleet-delegation-phase2.shape.md` | read (PK-1 §2) |
| Telos (bound) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.know/telos/fleet-delegation-portfolio.md` | read (BOUND) |
| Glint G-04 | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/glints/GLINT-asana-automation-value-expansion-2026-07-22.md` | read (:49) |
| Prior-shape U1 (mined) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/frames/fleet-delegation-portfolio.shape.md` | read (:175-188, MINED) |
| Research (vendor ceiling) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/RESEARCH-identity-consumption-mapping-2026-07-22.md` | read (§6 :113-121) |
| Remote-access spike (§11.1) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.sos/wip/SPIKE-asana-mcp-remote-access.md` | read (§11.1) |
| Auth-server consent + mint | autom8y monorepo `git show origin/main:services/auth/autom8y_auth_server/routers/{authorize,tokens}.py`, `app/dependencies.py`, `services/token_service.py` @ 790465e0 | READ-ONLY (cross-repo) |

*Authored by requirements-analyst (10x-dev), PK-1 lane, fleet-delegation-phase2 WAVE-1,
2026-07-24. SURFACE landing into the R4 packet. Spec-only (R33). Self-grade MODERATE.
This consent journey ARMS the R4 ruling; it builds nothing and presumes no outcome.*
