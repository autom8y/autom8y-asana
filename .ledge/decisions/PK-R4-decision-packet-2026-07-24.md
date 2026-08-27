---
# Schema of record: doc-artifact-schemas#prd-schema (folded PRD required fields carried
# via the PK-1 spec; this artifact is the PK-2 ASSEMBLY that folds a PRD (PK-1 mint),
# a contract-spec (SP trust) and a review grid (RD land) into ONE operator-ruling packet.
# PK- prefix = phase-2 packet namespace (shape §2 exit artifact) — a documented divergence
# from PRD-*; this is a decision INPUT that ARMS a ruling, not a standalone PRD.
type: decision
artifact_id: PK-R4-decision-packet
title: "R4 DECISION PACKET — mint + trust + land as ONE coherent whole (fleet-delegation-phase2 WAVE-2)"
created_at: "2026-07-24T00:00:00Z"
author: "PK-2 lane lead (10x-dev / requirements-analyst), fleet-delegation-phase2 WAVE-2"
status: proposed              # SURFACED into the operator's hand; awaiting the R4 ruling.
                              # NOT "accepted" (would presume R4; R33 presumes nothing).
landing_mode: "SURFACE (ALWAYS)"  # R29 — FLIPS NOTHING. Arms the ruling; merges/builds/decides nothing.

# Packet metadata
phase: fleet-delegation-phase2
wave: WAVE-2
sprint: PK-2 (R4 decision-packet assembly)
folds:
  - ".ledge/specs/PK-consent-journey-spec-2026-07-24.md (PK-1 — the MINT leg)"
  - ".ledge/decisions/SP-species-leg-contract-2026-07-24.md (SP — the TRUST leg)"
  - ".ledge/reviews/RD-audit-line-landing-grid-2026-07-24.md (RD — the LAND leg)"
cp_state: "CP-2 CLOSED — RD ∧ SP ∧ PK-1 complete; all three rite-disjoint critics CONCUR'd"

# Impact assessment (requirements-analyst mandate) — classifies the WORK the packet ARMS,
# driving post-ruling routing to Architect. The packet ITSELF flips nothing (SURFACE).
impact: high
impact_categories: [security, auth, api_contract, cross_service, data_model]
# Rationale: the ruled-upon work changes an authN/authZ flow (consent gate + species
# consumption), a cross-service token contract (SDK claims model + auth-endpoint gate),
# and a schema (the authorization_codes migration / claims-model field). High-impact
# routes to Architect regardless of LOC.

# Source discipline
source_of_record:
  autom8y_asana_origin_main: "601a7d22826ab3ab9411e7b5ce36cec03635a407"  # 601a7d22 — ADVANCED from dfdb84a3 via FL-3 floor merges (docs/CI only). src/+pyproject+terraform diff dfdb84a3..601a7d22 = EMPTY (verified §9). All folded asana anchors re-verified stable.
  autom8y_monorepo_origin_main: "790465e01adcb76380f2621df8f622cf42827895"  # 790465e0 — unmoved since SP/PK-1 authorship; all cross-repo anchors re-probed own-hands at assembly (§9).
source_note: "Committed truth read via `git show origin/main:<path>` ONLY. The three folded artifacts anchor to asana dfdb84a3; origin/main advanced to 601a7d22 on FL-3 — re-verified byte-stable for src/, pyproject.toml, terraform/ (§9). PK-1 mandated PK-2 re-probe of the cross-repo anchors at assembly; DONE (§9)."

# Critic errata carried (so the operator rules on CORRECTED anchors — verified §8/§9)
errata_carried:
  - "SP §9 row-10 FORK-C pin anchor = pyproject.toml:68 (NOT :23); marker `autom8y-auth[observability]>=3.3.0`"
  - "PK-1 P4 migration count = 38 real versions (+ migrations/versions/__init__.py = 39 files total), NOT 39 versions; ZERO create authorization_codes"
  - "PK-1 P5 vendor-ceiling anchor = dependencies.py:265 `asana_pat=bot_pat` (NOT :242 — :242 is the `bot_pat_unavailable` log string)"
  - "RD §3 census-seam note DROPS `exports` from the caller_service-logger list (exports.py logs 0 caller_service)"
  - "[assembly-discovered, minor/non-load-bearing] RD A5 client-construction anchor = workflows.py:357 (RD cited :359)"

governing_rulings: "R4 (RESERVED — species migration; operator-only), R20 caveat i (vendor ceiling), R24 (re-derivation in THIS packet), R25 (effect-not-repo), R28 (audit-landing bar), R29 (identity gate — FLIP NOTHING), R33 (spec-only; rule mint+trust+land as one), R34 (phase-2 frame)"
acceptance_bar: "leg (a) — sufficient-to-rule WITHOUT a single follow-up question (falsified by a bounce). Self-contained, coherent, honest about unknowns (log retention is out-of-repo — U-1)."
self_grade: "MODERATE (self-ref ceiling per self-ref-evidence-grade-rule; three-evidence-leg §6 — this is an ASSEMBLY/spec, not a realization attestation; external corroboration was the CP-1/CP-2 rite-disjoint security + eunomia critics on the folded artifacts)"
schema_version: "1.0"
---

# R4 DECISION PACKET — mint + trust + land as ONE coherent whole

> **PACKET-ARMING BANNER (carry on the face — do not strip).**
> This packet **ARMS** the operator's R4 ruling and does **NOTHING** else. It is
> **SURFACE (ALWAYS)**: a working-tree file placed in the operator's hand, **NOT
> merged**. Per **R29 it FLIPS NOTHING** — no token species, claims model,
> validator, `isinstance` gate, consent gate, audit semantics, migration, UI, or
> ui-rite lane is built, merged, deployed, staged-for-flip, or scheduled by this
> artifact, wherever the code lives. It **RULES NOTHING** and **presumes no
> outcome**: **R4 is UNTOUCHED**; the species migration stays **R4-reserved**. The
> packet reports the search space and binds the three legs so the operator rules
> **minting + trusting + landing as ONE coherent whole** (R33). Nothing here takes,
> schedules, ranks-into-a-recommendation, or forecloses that ruling.

---

## §0. Executive read (said first)

**What the operator is ruling (R4).** One north star — *an internal AI agent acts
in a real business workflow carrying the invoking **human's own** delegated
identity, never a shared machine credential, so a real person is provably
accountable for every action a machine takes* — realized by **three legs the
operator now rules as one whole**:

| Leg | Question | Owner sprint | What R4 rules |
|---|---|---|---|
| **MINT** | How does a human *grant* an agent their delegated identity? | PK-1 | the consent journey + which mint path (M-1/M-2/M-3) |
| **TRUST** | How does the satellite come to *know* the human (species consumption)? | SP | the FORK-α locus (O1–O7) — where the actor-claim contract lands |
| **LAND** | How does the audit line *name* "&lt;human&gt; via &lt;agent&gt;"? | RD | which surface(s) (of 13 landable) carry the line |

**The one-sentence chain that binds them.** Consent **MINTS** a token carrying
`act` (`sub`=human, `act.sub`=agent) → the satellite must **TRUST/consume** that
species to bring the human into request context → the audit line **LANDS** naming
the human *from* that context. **Break any leg and the chain is dead:** no mint =
no `act` on the wire; no consumption = `act` erased at the door (today's live
defect); no landing = the human is in context but never written where a rep can
see it.

**The keystone that physically embodies the gap.** `AuthContext` is a **3-slot**
carrier — `("mode", "asana_pat", "caller_service")` — with **no human slot**
(`dependencies.py:58`). Every landing RD enumerates can only *name* an identity
present in that context; today none is. MINT puts the human on the wire; TRUST
must put it in the empty slot; LAND writes it down. **RD's every landable verdict
is conditioned on TRUST first delivering the human into that slot** — this is the
load-bearing cross-leg dependency (§2).

**On the packet's face — the present-state risks the operator must rule against
(not buried):**

1. **VENDOR CEILING (R20 caveat i)** — even with all three legs green, **Asana's
   own product API still acts as the bot**. Every downstream Asana call
   substitutes the shared bot PAT (`dependencies.py:265` `asana_pat=bot_pat`);
   `created_by`, comment authorship, and object permissions read as the bot until
   a **separate, unscoped per-user-Asana-OAuth decision** above the code. The
   fleet-plane audit line names the human; the Asana plane does not. This **bounds
   what R4 can deliver**: fleet-plane accountability, not Asana-native attribution.
2. **TWO LIVE FAIL-OPEN DEFECTS — at the two ends of the SAME chain** (critics
   confirmed against live code):
   - **MINT end** — `/authorize` gates the consenting principal on
     `get_current_user`, which **accepts agent tokens** → *an agent can drive its
     own consent approval* (`authorize.py:117/:232` vs `require_human_token`,
     `dependencies.py:174`). **G-CONSENT-HUMAN.**
   - **TRUST end** — a delegated `agent_access` token is **silently admitted as a
     plain SERVICE call** with the human/agent pair erased (`_detection.py:43`
     fall-through + `extra="ignore"` drop + `client.py:336` admit). **Silent
     admission, not rejection — fail-OPEN.**
   Both are the **same defect class** (fail-open on identity tier) at the mint end
   and the consume end. The fixes — `require_human_token` on the consent surface
   (PK-1) and fail-closed on the consume surface (SP O6) — are the **same
   discipline**; the operator can rule the posture at both ends as one stance.
3. **G-MIGRATION** — the `authorization_codes` table written when a human approves
   at `/authorize` has **no Alembic migration** (38 migration versions; zero create
   it) → a clean-bootstrap env **500s the moment consent is granted**. This is a
   **landing dependency of mint-path M-2** (OAuth-code); mint-path **M-1** (direct
   RFC-8693 exchange) avoids it entirely.

**The asymmetry that shrinks the work.** The **producer is already correct**: the
mint emits `act` per RFC-8693 (`token_service.py:425-426`) and the audit already
indexes **both** legs (`audit_log.py:45-46` `acting_agent_id` + `delegating_user_id`).
The **entire gap is consumer-side** — TRUST (satellite can't read `act`) + LAND
(satellite plane names no human). R4 is a *consumption + landing* ruling, not a
*mint-from-scratch* one.

**Critic errata carried** (operator rules on corrected anchors — verified §8/§9):
SP FORK-C pin → `pyproject.toml:68`; PK-1 migrations → **38** versions (+`__init__.py`);
PK-1 vendor-ceiling → `dependencies.py:265`; RD census-seam → **drop `exports`**.

**R4 is untouched.** This packet arms the ruling; §11 attests it takes nothing.

---

## §1. The ruling surface — what R4 decides, and what this packet does NOT

**R4 decides three coupled things, as one whole (R33):**

- **(MINT)** whether the consent journey is *minted*, and **which mint path** carries
  the human's grant into the existing RFC-8693 exchange (M-1 / M-2 / M-3, §3.3);
- **(TRUST)** the **FORK-α locus** — where the actor-claim contract lands so the
  satellite consumes the species (O1–O7, §4). The species **migration itself** (the
  flip that makes consumption LIVE) is **R4-reserved** and executed only on the
  operator's word;
- **(LAND)** which of the **13 landable** audit-line surfaces the packet adopts, at
  what strength, and whether reading (a) in-record and reading (b/c) structured-log
  land **together** (R28 admits *and/or*) (§5).

**This packet does NOT** rank the SP options into a recommendation, choose the RD
landing, pick the mint path, decide the fail-open posture, schedule the migration,
switch a ui-rite lane, or presume the ruling. It **enumerates** (exhaustively,
killed/dead preserved — option-enumeration-discipline) and **binds** (shows how a
choice in one leg constrains the others — §2), so the ruling is coherent. The
**operator rules; the packet arms.**

**Downstream of the ruling** (named, not done): the chosen mint path, trust locus,
and landing set route to **Architect** (high-impact, §frontmatter) for the TDD/ADR
that designs the R4 build; the species migration is the R4-reserved flip.

---

## §2. THE THREE-LEG BINDING (the packet's core — how a choice in one leg constrains the others)

The value of assembling one packet (vs three artifacts) is **this section**: the
ruling is a **tuple** `(mint-path × trust-locus × landing-set)`, and the legs are
**not independent**. Below is the directed constraint map. Every constraint is a
*fact* (anchored), not a preference — the operator still rules the choice.

### 2.1 The causal spine (the chain, drawn once)

```
  HUMAN                          SATELLITE (autom8y-asana)                    REP
  grant                          consume            name
    │                               │                 │
 [MINT / PK-1]  ── act on wire ──▶ [TRUST / SP] ── human in ──▶ [LAND / RD] ──▶ audit line
 sub=human                         reads act into    AuthContext   writes "<human>
 act.sub=agent                     the empty slot    (3 slots →     via <agent>"
 (token_service.py:425-426)        (dependencies.py:58   4)         where work lives
                                    has NO human slot)
        ▲                                                                  │
        └──────────── producer already correct; audit indexes BOTH ───────┘
                      (token_service.py:425-426 + audit_log.py:45-46)
                                                                    ▲
                                          VENDOR CEILING caps the realized meaning:
                                          Asana's own API still acts as the bot
                                          (dependencies.py:265) — fleet-plane only
```

### 2.2 TRUST → LAND (the load-bearing constraint set)

SP **gates** RD: **RD's every landable verdict is explicitly conditioned on
SP-consumption delivering the human into `AuthContext`** (RD §2.1/§2.3 — "today NO
surface names a human"). Therefore the trust-locus choice **directly changes what
LAND can realize**:

| If the operator rules the TRUST locus as… | …then the LAND leg (RD) is constrained to… |
|---|---|
| **O1** (new `AgentClaims` modeling `act`, typed) | the human lands from a **typed, first-class** context field → strongest substrate for **every** structured-log landing (C1/C2/C3/C5/C6) and in-record (A1/A2/C6). Full-strength across the grid. |
| **O5** (raw-`act` bridge, retirement-bound) | landings fire from a **raw-dict read** (bounded drift, retires when O1 lands). All request-axis landings realizable; substrate is a bridge, not the terminal contract. |
| **O6** (fail-closed **REFUSE** `agent_access`) | the delegated token is **rejected** → **NO human enters context** → **ALL 13 landable RD options go DORMANT for the `agent_access` path** until O1/O5/O7 lands. O6 stops the erasure and delivers **zero** landing. *Hard constraint — a "stop-the-bleeding-first" posture.* |
| **O7** (auth-server introspection / grant-dereference) | the human is resolved **at the producer** → uniquely **also serves the REACTIVE/event axis** → **only O7 (or O1 + ADR#266 grant-dereference) unlocks RD's C4** (event-triggered/webhook) landing that inbound-token options (O3/O5/O6) structurally cannot reach (RD §2.2 PRE-D1). |
| **O3** (satellite-local bespoke parse) | landings fire, but on an **unbounded-divergence** substrate (R27 ratchet fires) — the anti-option; RD lands on fragile ground. |

**Corollary the operator must see:** if the ruling wants to **LAND the event path
(RD C4)**, that *forecloses* the inbound-token-only trust options and **forces O7
(or O1 + grant-dereference)** on the trust leg. Choosing a landing constrains the
locus.

### 2.3 MINT → (TRUST, LAND) constraints

- **All three mint paths emit the SAME token shape** (`sub`=human, `act.sub`=agent —
  P3). So the **trust-locus choice is largely independent of the mint-path choice**
  — SP consumes the same `act` regardless of M-1/M-2/M-3. *(No hard MINT→TRUST
  constraint; this is itself load-bearing — the operator can rule mint-path and
  trust-locus on separate axes.)*
- **BUT the mint-path choice determines which live defect sits on the critical
  path:**
  - **M-1 (direct RFC-8693 exchange)** routes consent through the exchange, which
    **already gates on `require_human_token`** (`tokens.py:409`) → **avoids the
    G-CONSENT-HUMAN gate fix and avoids G-MIGRATION**. Cleanest identity story.
  - **M-2 (OAuth authorization-code)** routes consent through `/authorize` → **inherits
    the G-CONSENT-HUMAN fix** (that surface under-gates, §0/§3.2) **AND hits
    G-MIGRATION** (the `authorization_codes` write-target has no migration →
    clean-env 500).
  - **M-3 (composed)** inherits **both** fixes (two moments to reconcile).

### 2.4 The fail-open symmetry (why the two defects are one ruling)

The MINT-end defect (`/authorize` accepts agent tokens) and the TRUST-end defect
(`agent_access` silently admitted as SERVICE) are the **same class — fail-OPEN on
identity tier** — at the two ends of the chain. The remedies are the **same
discipline**: PK-1's `require_human_token` on the consent surface and SP's **O6
fail-closed** on the consume surface. `credential-scope-assertion-discipline`
mandates fail-CLOSED on a `(protocol × scope × auth_routing_field)` mismatch (SP
§3/§6.E); `act` **is** the auth_routing_field distinguishing `agent_access` from
`service`. **The operator can rule the fail-closed posture at both ends as one
coherent stance** — or rule them apart, knowing they are the same defect.

### 2.5 The producer-correct / consumer-blind asymmetry (what R4 does NOT have to build)

- **Mint already emits `act`** (`token_service.py:425-426`), **TTL-bounded 30 min**
  (`:434`), **scope full-reject on excess** (`tokens.py:466`).
- **Audit already indexes both legs** (`audit_log.py:45-46`).
- ⇒ R4 is **consumption + landing**, not minting-from-scratch. The audit-**of-record**
  already holds the truth **cross-repo** (auth-server); RD's job is to bring the human
  into the **satellite plane** where reps see it (reading a) and where the service's
  own structured logs live (reading b/c).

### 2.6 The vendor ceiling caps the realized meaning of the whole ruling (R20 caveat i)

Even a green `(M-x, O-y, {landings})` tuple delivers **fleet-plane** accountability
only. Asana's own API acts as the bot (`dependencies.py:265`); closing that needs
**per-user Asana OAuth**, which **no artifact in either repo scopes** — a
vendor/product decision above the code. **The consent screen MUST disclose this**
(PK-1 FR-M7/§6.7) so consent is not misinformed. This is a boundary on **what the
ruling can mean**, carried on the face — not a leg the operator rules today.

---

## §3. MINT leg — the human consent / grant journey (PK-1, IN)

**Summary.** A protocol-complete delegation surface has **no reachable human grant
moment**. The auth-server can mint a delegated token and *has* a consent *contract*
(`routers/authorize.py`), but the missing product piece is the **consent JOURNEY** —
the login-then-consent surface where a person authorizes the agent. PK-1 specifies
that journey end-to-end (authenticate → present → decide → mint hand-off → audit)
and its hand-off into the existing mint. **Spec-only (R33); builds nothing.**

### 3.1 Consent semantics (the seven properties a valid grant must satisfy)

Informed · Explicit · **Human-gated** · Scoped (⊆ delegator's OpenFGA perms,
full-reject on excess) · Bounded (single-hop, ~30-min TTL) · Attributable &
Revocable · **Honest-reach** (the vendor ceiling on the consent screen). Each has a
testable condition and live anchor (PK-1 §6). MoSCoW: **7 Must** (each with a
"broken/untrustworthy without" rationale), 4 Should (with workarounds), 4 Could,
7 Won't — a negotiated distribution (anti-inflation).

### 3.2 The LIVE defect — G-CONSENT-HUMAN (confirmed against live code, §9)

`/authorize` gates the consenting principal on **`get_current_user`**, which
**"Both user_access and agent_access tokens are accepted"** (auth
`dependencies.py:98`) — so **an agent token can exercise approve/deny on a
delegation** (`authorize.py:117` GET, `:232` POST). The correct human-only tier
**exists one import away**: `require_human_token` (`dependencies.py:174`) permits
**only** `user_access` and "any new token_type is automatically rejected
(fail-closed)" (`:181/:183`). The **mint exchange already uses it**
(`tokens.py:409`); the **asymmetry is the defect**. *Fix: whichever surface carries
the consent decision MUST gate on `require_human_token` — an **auth-endpoint
contract change** (hence `impact: api_contract`), specified here, **executed
nowhere** (R29 identity gate; operator's word).*

### 3.3 The mint hand-off — candidate paths (enumerated; NONE presumed)

On grant, the invariant (all paths satisfy): a delegated token issues with
`sub`=human, `act.sub`=agent, `scope` ⊆ delegator's OpenFGA perms (full-reject on
excess), single-hop, ~30-min TTL; on deny, nothing mints; **both** outcomes audited.

| # | Path | How consent triggers the mint | Gate / cost | Cross-leg note |
|---|---|---|---|---|
| **M-1** | **Direct RFC-8693 exchange** | human consents → human `user_access` token exchanged at `agent_token_exchange` (`tokens.py:405`, `require_human_token` `:409`) → `create_agent_token` (`:480`) | mint **already human-gated** (P3); consent UX is the build | **Avoids** G-CONSENT-HUMAN fix **and** G-MIGRATION. Cleanest identity story. |
| **M-2** | **OAuth authorization-code + consent** | human approves at `/authorize` (`:320`) → `authorization_code` → redeemed for the delegated token | requires the **G-CONSENT-HUMAN** gate fix **AND** hits **G-MIGRATION** (P4) | Standard OAuth, but the consent endpoint under-gates and the code table has no migration. |
| **M-3** | **Composed** — OAuth `/authorize` for *client* consent, then RFC-8693 exchange for the *delegation* | human consents to the client; agent exchanges the human's session token for the act-claim token | **both** fixes above; two moments to reconcile | Most faithful to how the two surfaces exist today; most wiring to specify. |

**Requirements-analyst finding (surfaced, not decided):** M-1 and M-2/M-3 differ in
*which* surface carries the human gate. The exchange already requires a human; the
`/authorize` consent does not. Any path routing consent through `/authorize`
inherits the G-CONSENT-HUMAN fix as a **precondition**, and M-2's approval write
inherits **G-MIGRATION** as a **landing blocker**. The architect/operator choose;
PK-1 fixes only that *the human gate must sit on whichever surface carries the
consent decision.*

### 3.4 G-MIGRATION (a landing dependency of M-2, on the face)

The `authorization_codes` table (written on `/authorize` approval) has **no Alembic
migration**: **38** migration versions exist (+`migrations/versions/__init__.py`);
**ZERO** create it (§9 receipt) → a clean-bootstrap env **500s the moment consent is
granted**. Same DB-contract-drift class as the `external_business_id`/FW-A3 case.
**Fix is auth-server work — mechanical, R25 effect-not-repo.** M-1 avoids it.

### 3.5 Named MINT dependencies (not built)

`G-CLIENT-REDIR / redirect_uris` (the *production/external-client* transport —
claude.ai / Claude Code / Desktop) is **held behind R22 (2026-07-28)** and is
**out of build scope**; the **dogfood/internal** posture (a human signs into their
own auth server directly — the operator's live-witness leg, US-003) does **not**
require it. Per-user Asana OAuth = the vendor-ceiling remedy (out; §2.6). The
**ui-rite lane switch** is **MOOT until the operator rules** (R33) — not presumed,
requested, or scheduled.

---

## §4. TRUST leg — the species-consumption locus (SP FORK-α; the operator RULES the locus)

**The keystone finding (own-hands, SP §2).** Today's failure is **silent ADMISSION,
not rejection**. A delegated `agent_access` token at the asana boundary:
`jwt_validator.py:83` → `validate_service_token` → SDK `detect_token_type` **falls
through to SERVICE** (`_detection.py:43`: not OPERATOR — no marker; not USER — **no
`roles`**) → parses `ServiceClaims` → **`extra="ignore"` drops `act`** at parse
(`claims.py:162`) → `client.py:336` `isinstance(claims, ServiceClaims)` **TRUE** →
**ADMITTED**. The gate does **not reject** the delegated token — it **admits it as a
plain service call with the human/agent pair erased**. This is the concrete shape of
"the satellite cannot know the human," and it is the fact **every** option below must
defeat. **Bug Bar severity of the current state: Important** (repudiation/attribution
of a delegated principal + scope-confusion admission, partially mitigated by the
cross-repo audit row) — SP §3, semantics owned by `severity-taxonomy`.

**The wire target is KNOWN and produced today** (`create_agent_token`,
`token_service.py:403-435`): `token_type="agent_access"`, `sub`=user_id (delegating
human), `act={sub:"agent:{session}", agent_type}`, 30-min TTL. The `act` claim is
**on the raw wire**; the only reason the satellite can't see it is the SDK's lossy
Pydantic model. **The contract to specify is "consume what the mint already emits."**

### 4.1 The FORK-α option slate — 7 structurally-distinct loci (NOT pre-ranked)

Gating legend: **R4** = the consumption/migration flip (the actual "satellite now
knows the human"); **R29** = must-not-flip this wave; **R27** = divergence-ratchet
watch.

| Opt | Mechanism (categorically distinct) | Locus | Landability | Cost / key risk | Gating |
|---|---|---|---|---|---|
| **O1** *(canonical / terminal)* | Mint a new `AgentClaims(BaseClaims)` with typed `act`; add an AGENT detection branch keyed on `token_type=="agent_access"` (OPERATOR-branch-first precedent); data plane reads `act.sub`. "Model what the mint emits + the audit indexes." | monorepo `claims.py` (new class) + `_detection.py:12` (new branch before USER) + `client.py:336` admit the new class | cross-repo **autom8y-auth SDK release** + **FORK-C pin-bump** (asana `pyproject.toml:68`). Highest ceremony; fleet-wide blast radius | follows the in-code declare-or-drop precedent (`claims.py:312-321`); the durable contract everything converges to | **R29**-specify-only; **R4** to consume; **R27-CLEAN** (it IS the shared contract) |
| **O2** | Widen `isinstance(claims, ServiceClaims)` → admit the delegated species | monorepo `client.py:336` (and `UserClaims` gate `:297` if it should reach the human plane) | a **rider on O1**, not standalone — can't widen to admit a class that isn't modeled; widened alone → still drops `act` → **vacuous** | **breaks `test_contract_auth`**; gate semantics change fleet-wide | **R29** (named gate surface); **R4**; entangled with O1 |
| **O3** *(anti-option)* | Satellite defines its **own** local model of `act` (e.g. in `jwt_validator.py`) — a contract nobody else models | asana `jwt_validator.py` (satellite-local) | **lowest ceremony** (no cross-repo release/pin) but asana-only; every other satellite re-invents | **UNBOUNDED DIVERGENCE** — no shared anchor, no retirement clause; N satellites → N contracts | **R29** (no shared surface) but **R27-ratchet FIRES** (the divergence this discipline exists to catch); **R4** |
| **O4** *(spec-only)* | Define the canonical RFC-8693 `act` → claims mapping as a written CONTRACT the SDK adopts later | a document (SP §4 is a partial down-payment) | trivial now (prose/schema); **zero consumption** until the SDK adopts it (i.e., until O1 implements it) | risk = spec rots if never adopted; it **is the specification O1 implements** | **R29-safe + R4-safe** (nothing flipped) |
| **O5** *(bridge, retirement-bound)* | Read `act` **directly off the RAW jwt payload** (the `jwt.decode()` dict carries `act`; `extra="ignore"` only affects the Pydantic MODEL) — bypass the lossy parse. **O5a** double-decode; **O5b** pre-validation intercept (may additively add `act` to `RawTokenPayload`, typing-only, R29-safe) | asana `jwt_validator.py` (O5a); + typing-only SDK addition (O5b) | satellite-local; **no** shared validator/gate/model semantic change | **MUST read RAW** (SDK-parsed object already dropped `act`); carries a **retirement clause** (retire when O1 lands) → **bounded** drift | **R27-CLEAN** (bounded + retirement); **R29** (read-beside); **R4** |
| **O6** *(DISCOVERED · NULL / no-new-mechanism)* | **Detect** `token_type=="agent_access"` (raw read) and **fail-closed REFUSE** it until an actor-contract lands — convert silent-admit-with-human-erased into **explicit reject** | asana `jwt_validator.py` (guard around `validate_service_token`) | satellite-local, minimal — the **lowest-mechanism** option that closes the erasure | **blocks delegated tokens entirely** (no consumption) — trades delegation-availability for erasure-safety; **stops the bleeding, delivers no "know the human"** | **R29**; **R4**; **R27-CLEAN**. The **credential-scope-conformant** posture (fail-closed on mismatch) |
| **O7** *(DISCOVERED · DELEGATION)* | **Delegate** act-resolution to the already-capable producer — the auth-server (holds mint + both audit columns); the satellite calls an introspection surface (RFC-7662 or ADR#266 grant-dereference) returning `(delegating_user, acting_agent)` | cross-repo — auth-server introspection endpoint + an asana client call; **composes** with ADR#266's reactive-axis grant-dereference | requires an auth-server endpoint (may need building) + a satellite network call | per-request **network round-trip + availability coupling** on the auth-server (same SPOF / fail-open-vs-closed trade ADR#266 surfaces) + latency; **no local parse → no `extra=ignore` concern, no satellite divergence** | **R29**; **R4**; **R27-CLEAN** (delegates to producer of record). **Uniquely serves the reactive/event axis** → unlocks RD C4 |

**Slate-completeness receipt** (option-enumeration-discipline §6): option avoiding the
SDK model entirely = O5/O6/O7 ✔; delegation option = O7 ✔; null / no-new-mechanism =
O6 ✔; existing substrate not otherwise mentioned = O5 (raw `jwt.decode` dict +
`RawTokenPayload`), O7 (auth-server audit/mint/introspection) ✔. **Slate complete,
not terminated-by-convention.**

### 4.2 Pre-killed-as-vehicle — recorded, never silently omitted

**OperatorClaims / autom8y-auth 4.2.0 is PRE-KILLED-AS-VEHICLE (FORK-D).**
`OperatorClaims` (`claims.py:401`) reads `operator_sub` from `BaseClaims.sub` — the
**subject IS the machine-operator principal**, not the delegating human — and carries
**no `act` field**. It **cannot** hold `sub`=human + `act`=agent: it would put the
non-human principal in `sub` and erase the human. It survives on the slate **only as
the shape O1's new class must NOT be** — a **distinct NEW** actor-modeling class
(`sub`=human + `act`=agent), never a reuse or subclass of OperatorClaims. (The SDK
**version** 4.2.0 is likewise **not the vehicle**; O1 is a new-class release, not an
OperatorClaims widening.)

### 4.3 Folded constraints (bind EVERY option — not themselves options)

**A. `extra="ignore"` declare-or-drop law** (`claims.py:162`, documented in-code at
`:312-321` for the *"delegated-agent path"*): any option reading `act` off the
SDK-parsed `ServiceClaims` is defeated — O1 declares it on the new class, O5 MUST read
RAW, O6 reads raw to detect+refuse, O7 sidesteps it. **B. D1 schema (ADR#266
C-1/C-5):** the contract serves `sub`=human + `act`=agent for **BOTH** request- and
event-triggered actions and **MUST NOT lock until the SDK models the actor claim** —
so this slate is a **locus enumeration, not a lock** (the K3 schema stays unlocked
until the chosen locus lands). **C. Detection downgrade-safety** (the §4 keystone): any
O1 branch MUST be additive/marker-keyed so a pre-AGENT SDK keeps downgrading
`agent_access` predictably (to SERVICE, never UserClaims); O6 fail-closed is the safe
posture in that pre-AGENT window. **D. Credential-scope conformance:** `act` is the
auth_routing_field; fail-CLOSED on mismatch is conformant (O6); O1/O5/O7 resolve the
field rather than dropping it.

---

## §5. LAND leg — the audit-line landing grid (RD; 18 candidates, dispositions preserved)

**The bar (R28, verbatim).** The audit line may land **(a)** written INTO the
business record (an Asana story/comment/field naming "&lt;human&gt; via &lt;agent&gt;",
visible to reps) **and/or (b)** as durable structured log lines naming the human,
with retention. *Fleet-owned durable store* and *external-auditor grade* are
**EXCLUDED as the bar** (optional hardening only); the *auth-service audit-table
path* is **dead as the bar**.

**The headline archaeological finding.** The real live audit path is a **FAMILY of
per-route structured logs** — the reconciliation {routes emitting a `caller_service`
structured log} ∩ {routes declaring an `asana_api` write side-effect} partitions to
**exactly FIVE** members: **`workflows` (C1), `entity_write` (C2), `intake_create`
(C3), `intake_custom_fields` (C5), `receipts` (C6)** — each records the *service*
with **zero** human field (verified §9). That family is the strongest reading-(b)
landing because the surface **already fires on every write**: naming the human is a
**field addition to a live audit line, not a new mechanism**. The **inverse** seam:
`projects`, `sections`, route-level `tasks` declare `asana_api` writes but emit **no**
structured audit log (verified: 0 caller_service each) — live reading-(a) write
surfaces currently un-audited at the route layer.

**Every landable verdict is conditioned on §2 (SP delivering the human into
`AuthContext`).** "LANDABLE" marks the *surface* admissible **once TRUST lands** —
never "works today." Today **no** surface names a human (RD §2.3 receipt: repo-wide
grep → 0 audit-field matches).

### 5.1 Reading (a) — in-the-business-record

| # | Candidate | Disposition | Anchor (origin/main) | Cause-of-death (two-sided) / landing note |
|---|---|---|---|---|
| **A1** | Story/comment "&lt;human&gt; via &lt;agent&gt;" on the acted-on object | **LANDABLE** `full` | `clients/stories.py:249/262/275/288/301` create_comment | Comment body is **free text**, durable, **rep-visible** — R28(a)'s canonical example. Highest-fidelity reading-(a) home. Lands iff §2 delivers the human. |
| **A2** | Task description/notes grammar (append the line to `notes`) | **LANDABLE** `full` | `clients/tasks.py:436/470-471/528`; PUT full-state `:246-301` | Free-text, durable, rep-visible. Append-grammar must be additive (Asana `notes` is last-write-wins) — an impl constraint, not a kill. |
| **A3** | Custom-field write naming the human | **LANDABLE** `partial` | `clients/custom_fields.py:218/320/398/613` | PASSES IF a dedicated text/enum field is provisioned on the object type. Typed, not free text → heavier; better as a *structured* complement. |
| **A4** | Attachment/artifact record naming the human | **LANDABLE** `weak` | `clients/attachments.py` (`upload:204`…) | Human name sits in file content/metadata, not a first-class field → awkward as the *primary* line; fine as **optional hardening**. |
| **A5** | Rely on Asana's **NATIVE** actor attribution (`created_by`/system stories) | **KILLED** | write cred = **shared bot PAT**: `workflows.py:357` `AsanaClient(token=auth_context.asana_pat)`; `dependencies.py:265` `asana_pat=bot_pat` ← `get_bot_pat()` `:239` | PASSES IF Asana attributes the mutation to the human. It does **not**: every write runs under the **single shared bot PAT**, so Asana's own `created_by`/system stories name the **bot**, never the human — by construction. Dead independent of SP. *(RD cited the client line as :359; verified :357.)* |

### 5.2 Reading (b) — durable structured logs (frame-named surfaces)

| # | Candidate | Disposition | Anchor | Note |
|---|---|---|---|---|
| **B1** | Wire the DORMANT `S2SAuditLogger` with human fields | **LANDABLE** `partial` | `auth/audit.py:99` class; fields `:51-59` (no human field); singleton `:259`; **zero live callers** | Purpose-built audit surface but **presently inert** — needs a human field + live call sites + §2 + retention. Landable, not free (3 build steps + 2 preconditions). |
| **B2** | Extend the inline auth log (`auth_mode_jwt`) with a human field | **LANDABLE** `partial` | `dependencies.py:253-260` `caller_service=claims.service_name` | Fires **once per authentication**, not per business action → records *who authenticated*, not *who acted on which object*. Coarser grain; admissible as a coarse ledger. |
| **B3** | MCP-layer log at the tool boundary (10 tool modules) | **LANDABLE** `weak` | `mcp/asana_mcp/tools/` (self-labeled "REFERENCE / THROWAWAY POSTURE") | Sidecar is reference/throwaway, sits *outside* the production service; weakest "durable with retention" claim. Optional hardening only. |

### 5.3 Reading (c) — discovered surfaces (neither the inaugural wave nor the frame named)

| # | Candidate | Disposition | Anchor | Note |
|---|---|---|---|---|
| **C1** | `workflow_invoke_api` — the LIVE audit log (census-missed real path) | **LANDABLE** `full` | `workflows.py:320` `# Audit log`, `:322` `workflow_invoke_api`, `:327` `caller_service`; completion `:400` | PASSES with the **least new mechanism**: the audit log already fires on every invoke, already structured, already self-labeled "Audit log" — naming the human is a **field addition to a live line**. **The strongest structured-log home.** |
| **C2** | `entity_write` field-write audit log (sibling on a WRITE route) | **LANDABLE** `full` | `entity_write.py:226` request `+ :231 caller_service`, around `write_entity_fields:195` | Same shape as C1, sited **at the mutation point** — arguably the most apt per-action home. Proves C1 is a **pattern, not a one-off**. |
| **C3** | `intake_create` audit log (sibling on a WRITE route) | **LANDABLE** `full` | `intake_create.py:108` + `:176`, both `caller_service=claims.service_name` | Third live instance of the family, on business-hierarchy creation. |
| **C5** | `intake_custom_fields` audit log (4th family member; CP-2 census gap) | **LANDABLE** `full` | `intake_custom_fields.py` side-effect `task_custom_fields:51`; twins `:90`+`:149`; mounted `api/main.py:488` | Distinct from C2/C3 (different path/verb/target/event-names) → **not subsumable**. Same disposition. Added at CP-2 (security-reviewer). |
| **C6** | `receipts`/`forwarding_receipt` audit log (5th family member; CP-2) — **ALSO the live in-production embodiment of A1** | **LANDABLE** `full` | `receipts.py:90` side-effect `business_task_comment`; twins `:131`+`:211`; `caller_service:135/:219`; **`story_gid` recorded `:215`**; mounted `api/main.py:490` | **Doubly material:** `forwarding_receipt_complete` records `story_gid` → this route **already writes a story onto the Business task in production** → the single most concrete LIVE instance of **A1**. Add the human on both the log and the story body. |
| **C4** | Event-triggered dispatch log (webhook path) | **LANDABLE** `weak` | `webhooks.py:173` `logger.info("webhook_…")`; V2 extension point `:6` | PASSES IF the human is nameable on the **event-triggered** path. Per RD §2.2 there is **no human-bearing token** on a webhook trigger → naming depends **wholly on SP's D1 event-triggered mapping (ADR#266)** → **only trust-locus O7 (or O1 + grant-dereference) reaches it** (§2.2 corollary). |

> **Census-seam note (CORRECTED — erratum carried).** The inverse set — `asana_api`
> write routes emitting **no** `caller_service` structured log — names three live
> surfaces audited today only at the client layer: **`projects.py`**,
> **`sections.py`**, route-level **`tasks.py`** (verified: 0 caller_service each; 5/5/10
> `asana_api` refs). Any structured-log (b/c) landing does **not** cover them today.
> The read-routes that log `caller_service` with side-effects `[]` are **{admin,
> fleet_query, intake_resolve, matching, query, resolver, resolver_schema, internal}**
> — **`exports` is DROPPED** (it logs 0 `caller_service`; RD's original list
> over-included it). caller_service-logging route family = **13**; write-family = **5**
> (C1/C2/C3/C5/C6); write-but-no-log = 3 (projects/sections/tasks). Named for
> completeness; **not distinct numbered candidates** (same mechanisms as A1/A2/A3 +
> the C-family) — count stays 18.

### 5.4 KILLED (intrinsic cause) and DEAD-AS-BAR (R28 exclusion) — PRESERVED

| # | Candidate | Disposition | Cause / receipt |
|---|---|---|---|
| **K-MCP** | Armed MCP composite write (`composite_write.py`+`confirm_gate.py`) as the audit-naming surface | **KILLED** | Three independent kills (any one suffices): (i) `composite_write.py:1-6` "**THROWAWAY / REFERENCE-POSTURE. NOT production code**"; (ii) exposure gate `:98/:102/:458` default **OFF** (`ASANA_MCP_ENABLE_WRITE_SURFACE`); (iii) backing write = S2S-JWT → **shared bot PAT**, and the tool docstring declares "**NOT audit-names-the-human**". |
| **D-1** | Fleet-owned durable store **AS THE BAR** | **DEAD-AS-BAR** | R28 :130-133 EXCLUDED as the bar. MAY appear as optional hardening (ship the C-family logs onward to a durable store) — **never** a REALIZED requirement. |
| **D-2** | External-auditor grade **AS THE BAR** | **DEAD-AS-BAR** | R28 :130-133 (same clause). MAY appear as optional hardening (an external attester over the logs). |
| **D-3** | Auth-service audit-table path **AS THE BAR** | **DEAD-AS-BAR** | R28 :146-147 "dead as the bar." The auth-server already models BOTH species (`audit_log.py:45-46`; carried UV-P, cross-repo) → **optional-hardening-ready but DEAD as the bar**. Complementary, not the leg. |

### 5.5 Live-vs-killed accounting (exhaustiveness receipt)

| Bucket | Count | Members |
|---|---|---|
| **LANDABLE** (admissible, §2-conditioned) | **13** | A1, A2, A3, A4, B1, B2, B3, C1, C2, C3, C4, C5, C6 |
| — `full` / `partial` / `weak` | 7 / 3 / 3 | full: A1,A2,C1,C2,C3,C5,C6 · partial: A3,B1,B2 · weak: A4,B3,C4 |
| **KILLED** (intrinsic) | **2** | A5, K-MCP |
| **DEAD-AS-BAR** (R28 exclusion) | **3** | D-1, D-2, D-3 |
| **TOTAL** | **18** | — |

### 5.6 ATAM trade-off surface (for the ruling — not a recommendation)

- **Visibility-to-reps ↔ machine-queryability.** Reading (a) (A1/A2/C6) is rep-visible
  where the work lives but not machine-indexed; reading (c) (C1/C2/C3) is
  machine-queryable but invisible to reps. **R28 admits *and/or*** — complementary,
  not exclusive; the packet may propose both.
- **Least-new-mechanism ↔ purpose-built.** C1 (extend a live audit line) is lowest-effort;
  B1 (`S2SAuditLogger`) is purpose-built but inert (3 build steps).
- **Per-action grain ↔ per-auth grain.** A1/C1/C2 record *who acted on which object*;
  B2 records *who authenticated*. R28 "the audit line names that human" → per-action
  grain is the stronger construct-validity match (but see U-2).
- **Durability posture.** Reading (a) inherits Asana's own durability; reading (b/c)
  inherits the CloudWatch group's retention, which is **out-of-repo (U-1)**. A
  belt-and-suspenders read — (a) rep-visible + (c) structured retention — hedges both.

---

## §6. On the packet's FACE — present-state risks the ruling must account for

*(Pulled up so they are not buried in the leg sections. All confirmed against live
code, §9.)*

1. **VENDOR CEILING (R20 caveat i) — bounds what R4 can deliver.** Fleet-plane
   accountability only; Asana's own API acts as the bot (`dependencies.py:265`).
   Per-user Asana OAuth is **unscoped in either repo** — a vendor/product decision
   above the code. The consent screen MUST disclose it (PK-1 FR-M7). *This is not a
   leg the operator rules today; it is a ceiling the ruling inherits.*
2. **LIVE DEFECT #1 — G-CONSENT-HUMAN (MINT end, fail-open).** `/authorize` accepts
   agent tokens → an agent can drive its own consent approval (§3.2). Present-state
   risk; the fix is an auth-endpoint contract change behind R29.
3. **LIVE DEFECT #2 — silent SERVICE-admission (TRUST end, fail-open).**
   `agent_access` admitted as SERVICE with `act` erased (§4). Present-state risk; SP
   Bug-Bar **Important**. O6 is the fail-closed correction; O1/O5/O7 resolve the field.
4. **G-MIGRATION — clean-env 500 on first consent (M-2 landing dependency).** The
   `authorization_codes` write-target has no migration (§3.4). Mint-path-scoped: bites
   M-2/M-3, not M-1.
5. **Honest unknown — log retention is OUT-OF-REPO (U-1).** Every reading-(b/c)
   landing's "durable … with retention" clause depends on `var.asana_service_log_group`'s
   `retention_in_days`, which **no in-repo terraform declares** (RD §2.4). The packet
   **names** this; it cannot resolve it from the repo.

---

## §7. Unknowns carried to the ruling (surfaced, not assumed; honest about out-of-repo)

| # | Unknown | Why it matters to the ruling | Suggested source |
|---|---|---|---|
| **U-1** | audit-log-group `retention_in_days` (out-of-repo) | gates every reading-(b/c) "durable with retention" verdict (LAND) | shared platform/ECS terraform module (outside `terraform/services/asana/`); operator/SRE |
| **U-2** | per-action vs per-request human grain | decides whether the full C-family (A1/C1/C2 grain) is required or a coarse ledger (B2) suffices (LAND) | operator, at this ruling |
| **U-3** | event-triggered human provenance (C4 / PRE-D1) | C4 landability + the D1 constraint → **forces trust-locus O7/O1+grant-dereference** if the event path must land (TRUST↔LAND) | SP + ADR#266; operator |
| **SP-Q1** | who owns/releases the SDK `act` contract, on what cadence? | O1/O2 gate the K3 lock on a cross-repo `autom8y-auth` release — a fleet sequencing dependency (TRUST) | operator / fleet sequencing |
| **SP-Q2** | attribution-unavailable policy: fail-open vs fail-closed? | bears on O6 (refuse) and O7 (producer availability); credential-scope argues fail-closed (TRUST + the §2.4 posture) | operator |
| **SP-Q3** | type asymmetry `act.sub` (String) vs `sub` (UUID) | consumption schema must not coerce/truncate `agent:{session}` against a UUID column (mirrored in `audit_log.py`) | architect, at design |
| **SP-Q4** | bridge → terminal retirement enforcement | if O5/O6 is a bridge, the retirement trigger (O1 lands → bridge removed) needs a watch entry so it doesn't calcify (the O3 failure mode) | defer-watch, post-ruling |
| **PK-Q1** | mint path M-1 / M-2 / M-3? | determines which live defect is on the critical path (§2.3) (MINT) | architect/operator |
| **PK-Q2** | dogfood vs production first? | minimal internal grant path (live-witness) before/alongside the production UX (MINT) | operator |
| **PK-Q3** | the ui-rite lane switch | **MOOT until the operator rules** (R33) — not presumed/requested/scheduled | operator (only if ruled to build) |
| **PK-Q4** | do the G-CONSENT-HUMAN + G-MIGRATION fixes land in the consent build or as a pre-cleared floor item? | both are auth-server changes behind the R29 identity gate | operator |

---

## §8. Critic errata carried (operator rules on CORRECTED anchors)

The three folded artifacts were CP-2-CONCUR'd; the rite-disjoint critics flagged the
following anchor corrections, **carried here and independently re-verified at assembly
(§9)** so the operator rules on corrected truth:

| # | Source | Original | **Corrected** | Verification |
|---|---|---|---|---|
| **E-1** | SP §9 row-10 FORK-C pin | `pyproject.toml:23` | **`pyproject.toml:68`** — `auth = ["autom8y-auth[observability]>=3.3.0"]` | §9 probe: pin at :68 (also :94/:101 test deps, :371 index) |
| **E-2** | PK-1 P4 migration count | "39 migration version files" | **38 real versions** (+ `migrations/versions/__init__.py` = 39 files total); **ZERO** create `authorization_codes` | §9 probe: 39 `.py` files, 1 is `__init__.py`, 38 migrations, 0 authorization_codes |
| **E-3** | PK-1 P5 vendor-ceiling | `dependencies.py:242` | **`dependencies.py:265`** — `asana_pat=bot_pat` (`:242` is the `bot_pat_unavailable` log string) | §9 probe: `asana_pat=bot_pat` at :265; `:242 "bot_pat_unavailable"` |
| **E-4** | RD §3 census-seam | list includes `exports` | **DROP `exports`** (logs 0 `caller_service`) | §9 probe: `exports.py` caller_service count = 0; not in the 13-route family |
| **E-5** *(assembly-discovered, minor/non-load-bearing)* | RD A5 client-construction | `workflows.py:359` | **`workflows.py:357`** — `AsanaClient(token=auth_context.asana_pat)` | §9 probe: statement at :357. A5's kill is over-determined (shared bot PAT), so this is anchor hygiene only. |

---

## §9. Source discipline + own-hands anchor re-verification (at assembly)

**Asana `origin/main` advanced dfdb84a3 → 601a7d22 (FL-3 floor merges).** Verified the
merges are docs/CI only: `git diff --stat dfdb84a3 601a7d22 -- src/ pyproject.toml
terraform/` → **EMPTY**. Therefore **every folded asana `src/`/`pyproject`/`terraform`
anchor valid at dfdb84a3 is byte-identical at 601a7d22** — RD and PK-1 asana anchors
carry forward without re-derivation, and I re-confirmed the load-bearing ones directly
(C1 `workflows.py:322/:327/:400`; A5 `:357`; C2 `entity_write.py:226/:231`; C6
`receipts.py:90/:135/:215/:219`; inverse set projects/sections/tasks 0-caller_service;
AuthContext `dependencies.py:58`; vendor-ceiling `:265`; FORK-C `pyproject.toml:68`;
exports 0-caller_service).

**Monorepo `origin/main` = 790465e0 (unmoved since SP/PK-1 authorship).** PK-1 mandated
PK-2 re-probe the cross-repo anchors at assembly (auth-server lines move on release);
**DONE, own-hands** via `git -C <monorepo> show origin/main:<path>`:

| Claim | Anchor @ 790465e0 | Verified marker |
|---|---|---|
| ServiceClaims-only inbound, audience-gated | asana `jwt_validator.py:83` (@601a7d22) | `validate_service_token(token, audience=…)` |
| Four claim classes, no `act` field | `claims.py:133/165/295/401` | Base/Service/User/OperatorClaims present; no modeled `act` |
| `extra="ignore"` drop law + in-code precedent | `claims.py:162` + `:315` | `model_config = {"extra": "ignore"}`; "undeclared claim is silently dropped at parse" |
| Detector `agent_access` → SERVICE fall-through | `_detection.py:36/:39/:43` | OPERATOR-first `:36`; USER needs `has_roles` `:39`; `return TokenType.SERVICE` `:43` |
| SDK OWN gate | `client.py:336` | `if not isinstance(claims, ServiceClaims):` |
| Mint correct (RFC-8693 act) + TTL + type | `token_service.py:422/:425-426/:434/:435`; TTL note `:416` | `"sub": str(user_id)`; `"act": {"sub": f"agent:{agent_session_id}"`; `AGENT_TOKEN_TTL_SECONDS`; `token_type="agent_access"`; "TTL: 30 minutes (BIND #18)" |
| Audit indexes both legs | `audit_log.py:45/:46` | `acting_agent_id: Mapped[str \| None]`; `delegating_user_id: Mapped[uuid.UUID \| None]` |
| Mint exchange human-gated | `tokens.py:405/:409/:466/:480` | `agent_token_exchange`; `Depends(require_human_token)`; `validate_delegator_scope`; `create_agent_token` |
| G-CONSENT-HUMAN defect | `authorize.py:22/:117/:232` vs `dependencies.py:98/:174/:181/:183` | `/authorize` `Depends(get_current_user)` (accepts agent) vs `require_human_token` (user_access only, fail-closed) |
| G-MIGRATION | 38 versions + `__init__.py`; 0 `authorization_codes` | `git ls-tree` + per-file grep |

*Method: `git show origin/main:<path>` (asana 601a7d22) and `git -C <monorepo> show
origin/main:<path>` (790465e0). Every anchor re-derived at assembly; none inherited.
This is the receipts-exist leg (`three-evidence-leg-attestation` §2.1) at packet-assembly
altitude — there is **no** teeth-leg or live-CLI-leg because **nothing is realized**
(SURFACE mode; the species migration is R4, untouched). Self-grade ceiling MODERATE
(§12).*

---

## §10. The ruling surface, bound (a coherent decision menu — NOT a recommendation)

The ruling is a tuple `(mint-path, trust-locus, landing-set, fail-open-posture)`. This
menu lays out the **coherent** combinations and the constraints that make some tuples
contradictory — so the operator rules the whole. **It ranks nothing** (SP is not
pre-ranked; RD is not pre-chosen; the mint path is not picked).

- **Axis 1 — MINT path:** {M-1 direct exchange · M-2 OAuth-code · M-3 composed}.
  M-1 avoids the G-CONSENT-HUMAN fix and G-MIGRATION; M-2/M-3 inherit them (§2.3).
- **Axis 2 — TRUST locus:** {O1 · O2(rider on O1) · O3(anti) · O4(spec-only) · O5(bridge) ·
  O6(null/refuse) · O7(delegation)}. OperatorClaims/4.2.0 pre-killed-as-vehicle (§4.2).
- **Axis 3 — LAND set:** any subset of the 13 landable {A1–A4, B1–B3, C1–C6}; R28 admits
  reading (a) **and/or** (b/c).
- **Axis 4 — fail-open posture:** rule the fail-closed fix at the MINT end
  (require_human_token) and the TRUST end (O6-style) together or apart (§2.4).

**Coherence constraints the operator must honor (facts, §2):**

1. **TRUST gates LAND.** No landing is realizable until the chosen locus delivers the
   human into `AuthContext`. **O6 (refuse) ⇒ zero landing for `agent_access`** until
   O1/O5/O7 — a coherent "stop-the-bleeding-first" tuple `(any-M, O6, {} , fail-closed)`.
2. **Event-path landing forces the locus.** Adopting **RD C4** ⇒ **O7 (or O1 +
   grant-dereference)**; O3/O5/O6 cannot reach the reactive axis.
3. **O2 is not standalone.** `(…, O2 alone, …)` is vacuous (still drops `act`); O2 is
   "widen after O1."
4. **O4/O1 are the paper/realization pair.** `(…, O4, …)` delivers zero consumption
   until O1 implements it.
5. **Mint-path picks the defect on the critical path.** `(M-1, …)` clears
   G-CONSENT-HUMAN + G-MIGRATION off the path; `(M-2/M-3, …)` puts them on it.
6. **The vendor ceiling caps every tuple** — fleet-plane accountability only, until a
   separate per-user-Asana-OAuth decision (§2.6).

**Illustrative coherent tuples (NOT recommended — shown to prove the axes compose):**
a durable terminal `(M-1, O1, {C1-family + A1/C6}, fail-closed-both-ends)`; a
minimal-bridge `(M-1, O5, {C1}, fail-closed-both-ends)` with a retirement watch
(SP-Q4); a stop-the-bleeding `(any-M, O6, {}, fail-closed)`; an event-inclusive
`(M-1, O7, {C1-family + C4}, fail-closed-both-ends)`. The operator may compose any
tuple the §2 constraints permit; the packet neither endorses nor excludes among the
permitted set.

---

## §11. R4 UNTOUCHED — reaffirmation + FLIP-NOTHING attestation (R29)

- **R4 is reserved and untouched.** This packet **arms** the ruling on minting +
  trusting + landing; it **takes nothing, schedules nothing, ranks nothing into a
  recommendation, and presumes no outcome.** The **species migration stays
  R4-reserved** (the flip that makes consumption LIVE is the operator's, executed only
  on the ruling).
- **Nothing merged / deployed / staged-for-flip.** No token species, claims model
  (`claims.py`), validator/detection (`_detection.py`), `isinstance` gate
  (`client.py:336`), consent gate (`authorize.py`), audit semantics, `authorization_codes`
  migration, UI, or ui-rite lane was changed, wherever the code lives (asana or
  monorepo). All reads were `git show origin/main:…` against a FROZEN local main; zero
  writes to any source file.
- **R25 honored, R29 held.** A file edit is a file edit (R25); the ONLY authorship
  performed is this one packet file. The identity gate (R29) is un-pre-empted.
- **Scope of authorship:** exactly one working-tree file —
  `.ledge/decisions/PK-R4-decision-packet-2026-07-24.md`. **No `git add` / commit /
  branch / push / merge.** SURFACED into the operator's hand; **committed only at the
  operator's post-ruling disposition.**

---

## §12. Handoff & attestation

### 12.1 The acid test (leg a)
> *"Could the operator rule R4 — minting + trusting + landing as one coherent whole —
> from this packet alone, without a single follow-up question?"*

The packet is built to pass it: the causal chain and cross-leg constraint map (§2),
the mint journey + live defect + mint paths (§3), the un-ranked 7-option trust slate +
pre-kill + folded constraints (§4), the full 18-candidate landing grid with
dispositions and preserved kills (§5), the present-state risks on the face (§0/§6), the
carried errata on corrected anchors (§8), the own-hands re-verification (§9), and the
bound ruling surface (§10) are all present. The unknowns are **named** (§7), including
the honest out-of-repo one (U-1 log retention). If a rite-disjoint reader has a
*clarifying* question (vs a *decision* question the operator answers by ruling), the
packet is incomplete and bounces at DELTA scope.

### 12.2 Discipline attestation
- **SURFACE / FLIP-NOTHING (R29):** §11. One file; nothing merged, built, or flipped.
- **Arms, presumes nothing:** banner + §1 + §10 + §11 keep R4 untouched.
- **Option-enumeration-discipline:** SP 7-option slate and RD 18-candidate grid carried
  in full with killed/dead **preserved** (§4/§5); no truncation; SP **not pre-ranked**;
  RD **not pre-chosen**; mint paths enumerated (§3.3).
- **Vendor ceiling carried (R20 caveat i):** §0 + §2.6 + §6, on the face.
- **Three-leg binding:** §2 (the packet's core value — the cross-leg constraint map).
- **Errata carried + re-verified:** §8 + §9.
- **Source discipline:** asana 601a7d22 (dfdb84a3 anchors re-verified byte-stable);
  monorepo 790465e0 re-probed own-hands (§9).
- **Self-grade: MODERATE** (self-ref ceiling per self-ref-evidence-grade-rule;
  three-evidence-leg §6 — assembly/spec, not a realization attestation; external
  corroboration was the CP-1/CP-2 rite-disjoint security + eunomia critics on the
  folded artifacts).

### 12.3 Attestation table (absolute paths)

| Artifact | Absolute path | State |
|---|---|---|
| **This packet** | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/PK-R4-decision-packet-2026-07-24.md` | authored, working-tree, **SURFACED (uncommitted — operator post-ruling disposition)** |
| PK-1 (MINT — folded) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/specs/PK-consent-journey-spec-2026-07-24.md` | read in full; folded |
| SP (TRUST — folded) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/SP-species-leg-contract-2026-07-24.md` | read in full; folded |
| RD (LAND — folded) | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/reviews/RD-audit-line-landing-grid-2026-07-24.md` | read in full; folded |
| Asana committed truth | `git show origin/main:<path>` @ `601a7d22` (src/ byte-stable vs dfdb84a3) | READ-ONLY |
| Monorepo committed truth | `git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y show origin/main:<path>` @ `790465e0` | READ-ONLY (cross-repo) |

*Assembled by the PK-2 lane lead (10x-dev / requirements-analyst), fleet-delegation-phase2
WAVE-2, 2026-07-24. SURFACE (ALWAYS) into the operator's hand. This packet ARMS the R4
ruling on minting + trusting + landing as one coherent whole; it builds nothing, flips
nothing, ranks nothing into a recommendation, and presumes no outcome. Self-grade MODERATE.*
