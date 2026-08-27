---
artifact_id: SP-species-leg-contract
title: "SP species-leg contract: how the satellite comes to KNOW the human (delegated-token consumption locus)"
created_at: "2026-07-24T00:00:00Z"
author: SP lane lead (security · threat-modeler), fleet-delegation-phase2 WAVE-1
status: proposed
type: spec  # contract-specification (SURFACE-mode): the FORK-alpha locus enumeration into the operator's R4 packet
consumption_predicate: SURFACE
landing_mode: SURFACE  # R29 — FLIP NOTHING. This artifact SPECIFIES; it merges/deploys/stages nothing.
phase: "design-only — input to the operator's R4 packet (PK). The species MIGRATION itself is R4, untouched here."
evidence_ceiling: MODERATE  # self-authored option slate over self-probed facts; self-ref-evidence-grade-rule + three-evidence-leg §6 (spec, not a realization attestation)
source_of_record:
  autom8y_asana_origin_main: "dfdb84a38e71496e3b3a577935aa72039f37b5df"   # brief: dfdb84a3 — MATCHES
  autom8y_monorepo_origin_main: "790465e01adcb76380f2621df8f622cf42827895" # brief stated 2dce25cc — SUPERSEDED on release; all cross-repo anchors re-derived LIVE at 790465e0 and confirmed unmoved (see §2)
upstream:
  - ".ledge/decisions/ADR-ws7-actor-attribution-seam.md (ADR #266 → 2c91a724): the D1 schema constraint (C-1/C-5, PRECONDITION-1). This contract is the downstream enumeration of PRECONDITION-1's 'SDK actor-claim contract that MUST exist before K3 locks.'"
related_artifacts:
  - "autom8y: services/auth/autom8y_auth_server/services/token_service.py:403 (create_agent_token — the CORRECT RFC-8693 mint)"
  - "autom8y: services/auth/autom8y_auth_server/models/audit_log.py:45-46 (acting_agent_id + delegating_user_id — the audit already indexes both legs)"
  - "autom8y: sdks/python/autom8y-auth/src/autom8y_auth/claims.py:133/165/295/401/162 (four-class topology; extra=ignore; ZERO act field)"
  - "autom8y: sdks/python/autom8y-auth/src/autom8y_auth/_detection.py:12 (detect_token_type — the SERVICE-downgrade fate of agent_access)"
  - "autom8y: sdks/python/autom8y-auth/src/autom8y_auth/client.py:336 (isinstance(claims, ServiceClaims) — the SDK's OWN gate)"
  - "autom8y-asana: src/autom8_asana/auth/jwt_validator.py:24/83 (ServiceClaims-only inbound, audience-gated)"
tags: [security, auth, delegation, rfc-8693, threat-model, species-leg, phase-2, R4-packet, SURFACE]
---

# SP species-leg contract — how the satellite comes to KNOW the human

- **Date**: 2026-07-24
- **Lane / seat**: SP (security · threat-modeler), fleet-delegation-phase2 WAVE-1
- **Landing mode**: **SURFACE**. This artifact authors a SPECIFIED contract into the operator's R4 packet. Per **R29 it FLIPS NOTHING** — no token species, claims model, validator contract, isinstance gate, or audit semantics is merged, deployed, or staged-for-flip, wherever the code lives. That boundary is the critical risk R-SP-2; the attestation is in §8.
- **What this is**: the enumeration of the **FORK-α locus** — the structurally distinct ways the delegated token *species* becomes **consumable** (the satellite comes to know that an agent is acting **on behalf of a human**). It discharges ADR #266 (WS-7) PRECONDITION-1: *"an actor-modeling claims contract MUST exist SDK-side before the K3 schema locks."*
- **What this is NOT**: the migration. The R4 species migration (the flip that makes consumption LIVE) is **out of scope** and **untouched**. The operator rules the locus in PK; **this lane enumerates, it does not pre-rank**.
- **Evidence ceiling**: **MODERATE** per `self-ref-evidence-grade-rule`. The file:line facts in §2/§9 are directly probed (SVR, own-hands, LIVE). The option slate is argued design over a self-authored slate; the two discovered options (§5 O6/O7) came from a forced `option-enumeration-discipline` §4 Step-1 self-audit, not empirical outcome. No claim here reaches STRONG.

---

## 1. Position — this contract is the downstream of ADR #266 PRECONDITION-1

ADR #266 (WS-7 actor-attribution seam) fixed the **schema constraint** (normative, SHAPE-level):

- **C-1**: the Phase-2 K3/WS-4 consumption+audit schema MUST carry BOTH `sub`=human (delegating_user) AND `act`=agent (acting_agent) for **every** authorized action — request- OR event-triggered.
- **C-5 / PRECONDITION-1**: the schema **MUST NOT be locked** until an actor-modeling claims contract exists **SDK-side**. Locking `(sub)`-only today would foreclose `(sub, act)` tomorrow.

ADR #266 said **WHAT must hold**. This SP contract enumerates **HOW the SDK/satellite comes to model and consume `act`** — the species-leg made consumable. It is the missing half of PRECONDITION-1: the locus slate the operator's R4 packet needs in order to choose where the actor-claim contract lands.

**The asymmetry, stated once:** the *producer* is already correct. The mint emits the delegated species per RFC-8693; the audit substrate already indexes both identities. The gap is entirely on the **consumer** side — the satellite cannot read the human off the token because the SDK claims model has no `act` field and silently drops it. This contract is about closing the consumer gap **without** flipping the species.

---

## 2. Entry re-probe (LIVE, own-hands) — third UV-P discharge

SDK/auth lines move on release, so the entry premises are re-asserted **LIVE** against the current `origin/main`, not inherited. This is the receipts-exist leg (`three-evidence-leg-attestation` §2.1) at spec altitude — a fresh uncached re-derivation; there is **no** teeth-leg or live-CLI-leg because **nothing is being realized** (SURFACE mode: the species migration is R4, untouched — §6 self-ref note applies).

**Source-discipline correction (recorded, not propagated — per SVR provenance-correction discipline):** the brief stated monorepo `origin/main = 2dce25cc`. The LIVE probe resolves `origin/main = 790465e0` (the monorepo advanced on release). Every cross-repo anchor below was re-derived at `790465e0`; the load-bearing claims.py line numbers (`133/165/295/401/162`) are **identical** to ADR #266's read at the earlier `a53288db` — claims.py itself did not drift even though the repo SHA did. asana `origin/main = dfdb84a3` matches the brief exactly.

| # | Premise (brief) | LIVE finding @ origin/main | Anchor | Verdict |
|---|---|---|---|---|
| P2 | ServiceClaims-only inbound, audience-gated | `from autom8y_auth import AuthClient, ServiceClaims` (:24); `validate_service_token(token, audience="https://api.autom8y.io")` (:83) | asana `jwt_validator.py:24,:83` | CONFIRMED |
| P4a | Four claim classes, ZERO act/actor field | `BaseClaims:133`, `ServiceClaims:165`, `UserClaims:295`, `OperatorClaims:401`; module grep-negative for a modeled `act`/`actor` field on any class | monorepo `claims.py:133/165/295/401` | CONFIRMED |
| P4b | `extra="ignore"` silently drops `act` at parse | `model_config = {"extra": "ignore"}` on `BaseClaims` — inherited by all four classes | monorepo `claims.py:162` | CONFIRMED |
| A1 | Mint is CORRECT (sub=human + act.sub=agent) | `create_agent_token`: `"sub": str(user_id)` + `"act": {"sub": f"agent:{agent_session_id}", "agent_type": …}`; docstring "carries an 'act' claim per RFC 8693 Section 4.1. sub = delegating user, act.sub = agent identity"; `token_type="agent_access"` | monorepo `token_service.py:403-440` | CONFIRMED |
| A2 | Audit already models BOTH legs | `acting_agent_id: Mapped[str \| None] … String(255)` (:45); `delegating_user_id: Mapped[uuid.UUID \| None]` (:46); partial indexes :73-79 | monorepo `audit_log.py:45-46` | CONFIRMED |
| A3 | Gate is the SDK's OWN client.py; services/auth/client/ is a dead alley | `if not isinstance(claims, ServiceClaims):` (:336, inside `validate_service_token`); `services/auth/client/autom8y_auth_client/client.py` isinstance-count = **0** | monorepo `client.py:336` + dead-alley grep | CONFIRMED |

**NEW keystone finding (own-hands, not in the brief) — the failure mode is silent ADMISSION, not rejection.** `detect_token_type` (`_detection.py:12-49`) branches: OPERATOR iff `token_type=="operator_access"`; USER iff `business_id ∧ roles ∧ token_type`; else **SERVICE**. The agent token carries `token_type="agent_access"` and **no `roles`** (payload keys: sub, business_id, email, act, scope, delegation_session_id). Walking the detector: not OPERATOR (marker mismatch), not USER (no `roles`), therefore **falls through to `TokenType.SERVICE`**. So today, a delegated `agent_access` token arriving at the asana boundary:

1. `jwt_validator.py:83` → `validate_service_token(...)`;
2. SDK `client.py:333` → `validate_token` → `detect_token_type` → **SERVICE** → parses `ServiceClaims`;
3. `extra="ignore"` **drops `act`** at parse (the agent identity is erased);
4. `client.py:336` `isinstance(claims, ServiceClaims)` → **TRUE** → the token is **ADMITTED**.

The gate does **not** reject the delegated token — it **admits it as a plain service call with the human/agent pair erased**. `sub` survives as a raw UUID mislabeled service-principal; `act.sub` is gone. This is the concrete shape of "the satellite cannot know the human," and it is the fact every consuming option in §5 must defeat.

---

## 3. Threat lens — why the silent downgrade is a security gap (not just a missing feature)

Naming the gap in STRIDE terms (threat-modeler seat), then binding severity to the substrate (SI-1) — **citing, not redefining**:

- **Repudiation (primary).** An agent action taken on behalf of a human is admitted with the `(human, agent)` pair erased at the satellite. The satellite cannot attribute, authorize on, or enrich its own logs with the delegated pair. The audit-of-record is mitigated cross-repo (ADR #266 C-4: the auth-server `audit_log` holds both columns) — **but only if that row is written**; the satellite-plane view is human-less.
- **Spoofing / scope-confusion (secondary).** A delegated principal is routed with **SERVICE-tier** semantics (service permissions from scopes) rather than delegated-human semantics. Framed by `credential-scope-assertion-discipline`: `agent_access` and `service` are distinct `(protocol × scope × auth_routing_field)` rows — the `act` claim **is** the auth_routing_field that distinguishes the delegated species. Collapsing `agent_access` into `service` scope and admitting it is a **fail-OPEN on a credential-topology mismatch**; the discipline mandates **fail-CLOSED** on mismatch (Step 4). Today's path violates that posture silently.
- **Reactive-axis foreclosure (systemic).** Per ADR #266 §1, event-woken actions have no inbound JWT at all; if K3 locks against the request-axis-only model while this consumer gap stands, audit stops naming the human the moment an action is reactive.

**Bug Bar severity of the current silent-admit state: Important** — per `severity-taxonomy.lego.md §Bug Bar` (SI-1 single source of truth; semantics owned there, cited here, NOT restated). Rationale for the read: repudiation/attribution-integrity of a delegated principal plus scope-confusion admission, partially mitigated by the cross-repo audit row. The option chosen at the FORK-α locus **modulates the residual**: options that model or standard-anchor the read (O1/O5/O7) or fail-closed (O6) reduce the residual; leaving status-quo (silent admit) or accreting an unbounded local contract (O3) hold it at Important. No known CVE is in scope, so CVSS/EPSS/KEV/SSVC are not attached; if a specific SDK/CVE later applies, run the substrate signals and its `§Conflict Resolution` rule.

> This is a compact threat lens proportionate to a contract-spec, not a full STRIDE model of the satellite. A downstream security-reviewer / compliance-architect consumes the `bug_bar_severity` binding above.

---

## 4. The wire contract the satellite must come to consume (KNOWN, produced today)

The mint has already caught an RFC-8693 delegation contract onto the wire. This is the fixed target every consuming option reads toward (verbatim from `create_agent_token`, `token_service.py:403-440`):

```
token_type        = "agent_access"            # a DISTINCT discriminator (not operator_access, not user_access)
sub               = str(user_id)              # the DELEGATING HUMAN
act               = { "sub": "agent:{agent_session_id}",   # RFC-8693 §4.1 actor claim
                      "agent_type": agent_type }
business_id       = str(business_id)
email             = email
scope             = requested_scope
delegation_session_id = agent_session_id
aud               = "https://api.autom8y.io"  # fleet audience (F-002 Phase C.1)
ttl               = AGENT_TOKEN_TTL_SECONDS   # 30 min (BIND #18)
```

The contract to be specified is not "invent a delegated identity" — it is **"model/consume what the mint already emits (`act`) and the audit already indexes (`acting_agent_id`/`delegating_user_id`)."** The `act` claim is present on the raw wire; the only reason the satellite cannot see it is the SDK's lossy Pydantic model.

---

## 5. FORK-α locus — the option slate (structurally distinct; NOT pre-ranked)

Five options were sharpened by pythia; two more were surfaced by the mandatory `option-enumeration-discipline` §4 Step-1 self-audit (the brief's five are **all consume-mechanisms** — the required **null** and **delegation** options were the enumeration gap, §5 items 2 & 4). Each primary mechanism is categorically different (model-mint / gate-widen / local-bespoke-parse / paper-spec / raw-read-bridge / refuse / network-delegate), satisfying the structural-distinctness bar. Gating legend: **R4** = the consumption/migration flip (the actual "satellite now knows the human"); **R29** = must-not-flip this wave (species/model/validator/gate/audit surfaces); **R27** = divergence-ratchet watch.

### O1 — New SDK claims class modeling `act` (+ AGENT detection branch)  *[canonical / terminal state]*
- **Mechanism**: mint `AgentClaims(BaseClaims)` with a typed `act` field (`{sub, agent_type}`); add an AGENT branch to `_detection.py` keyed on `token_type=="agent_access"` (following the OPERATOR-branch-first precedent — additive marker, downgrade-safe); the data plane reads `act.sub`. "Model what the mint already emits + the audit already indexes."
- **Locus**: monorepo `claims.py` (new class) + `_detection.py:12` (new branch before USER) + `client.py:336` gate admittance for the new class.
- **Landability**: cross-repo **autom8y-auth SDK release** (v4.2.0 → next) + **FORK-C pin-bump** (asana `pyproject.toml` `autom8y-auth>=3.3.0` → `>=next`). Highest ceremony; fleet-wide blast radius (the SDK is consumed by every satellite).
- **Cost**: SDK release + fleet re-pin; detection-order care; **directly follows the existing declare-or-drop precedent** at `claims.py:312-321` (see §6.A). This is the durable contract everything else converges to or retires into.
- **Gating**: **R29-gated** (touches shared claims model + detection + gate — specify only, do not flip); **R4-gated** to consume; **R27-CLEAN** (it IS the shared contract — zero divergence).

### O2 — Widen the shared validator at `client.py:336`
- **Mechanism**: widen `isinstance(claims, ServiceClaims)` to admit the delegated species (e.g. `isinstance(claims, (ServiceClaims, AgentClaims))`) so `validate_service_token` accepts it.
- **Locus**: monorepo `client.py:336` (and symmetrically the `UserClaims` gate at `:297` if the delegated species should reach the human plane).
- **Landability**: a **rider on O1**, not standalone — you cannot widen to admit a class that isn't modeled. Widened alone (to admit the current ServiceClaims-downgraded token "as-is") it changes nothing about `act` (still dropped) → **vacuous for consumption**. Its real form is "widen after O1."
- **Cost**: **breaks `test_contract_auth`** — the shared validator contract test; gate semantics change fleet-wide.
- **Gating**: **R29-gated** (the isinstance gate is a named R29 surface); **R4-gated**; entangled with O1. (Dead-alley note: `services/auth/client/` has **0** isinstance gates — NOT the locus; the locus is the SDK's own `client.py:336`.)

### O3 — Satellite-local bespoke claim parse
- **Mechanism**: asana defines its **own** model of the `act` contract locally (e.g. in `jwt_validator.py`, after `ServiceClaims`, parse a satellite-owned model for `act`) — a contract nobody else models.
- **Locus**: asana `src/autom8_asana/auth/jwt_validator.py` (satellite-local).
- **Landability**: satellite-only; **lowest ceremony to land** (no cross-repo release, no pin-bump). But asana-only — every other satellite re-invents.
- **Cost**: **UNBOUNDED DIVERGENCE** — the local model of `act` can drift from the mint's / RFC's with no shared anchor and no retirement clause; N satellites → N bespoke contracts.
- **Gating**: **R29** — does not touch the SHARED validator/model, but **establishes a competing local contract** → **R27-ratchet-watch fires** (the divergence this discipline exists to catch); **R4-locus**. This is the anti-option; enumerated, not endorsed.

### O4 — Contract-level RFC-8693 mapping the SDK adopts later  *(spec-only now)*
- **Mechanism**: define the canonical RFC-8693 `act` → claims mapping as a written CONTRACT (ADR/schema) the SDK adopts in a future release.
- **Locus**: a document (this artifact's §4 is a partial down-payment; a follow-on schema/ADR completes it).
- **Landability**: trivial now (prose/schema); delivers **zero consumption** until the SDK adopts it (i.e. until O1 implements it).
- **Cost**: no code, no consumption; risk = spec rots if never adopted. It is the **specification O1 implements** (O4 = the paper contract, O1 = its realization).
- **Gating**: **R29-safe + R4-safe** (nothing flipped — spec only).

### O5 — Transitional standard-anchored consumption (raw `act` read)  *(convergence-gated BRIDGE, retirement-bound)*
- **Mechanism**: the satellite reads `act` **directly off the RAW jwt payload** (the `jwt.decode()` dict, which carries `act` because the mint emits it and `extra="ignore"` only affects the Pydantic MODEL, never the raw dict) — bypassing the SDK's lossy `ServiceClaims` parse. A BRIDGE that **RETIRES when O1 lands**.
- **Sub-split**:
  - **O5a — raw-JWT-act parse**: after `validate_service_token` succeeds, separately `jwt.decode` the same token and read `act` off the raw dict (double-decode; simplest).
  - **O5b — pre-validation intercept**: capture `act` at the decode boundary (`client.py:372 _decode_unverified` → `RawTokenPayload`) before Pydantic parse (single-decode; needs an SDK seam or a satellite decode helper). `RawTokenPayload` (`claims.py:28-58`) does **not** declare `act` today → O5b may **additively add `act` to `RawTokenPayload`** (typing-only, R29-safe since it is a `total=False` TypedDict, not the validated model).
- **Locus**: asana `jwt_validator.py` (O5a); asana + typing-only SDK addition (O5b).
- **Landability**: satellite-local (O5a) or satellite-local + typing-only SDK addition (O5b); **no** shared validator/gate/model semantic change.
- **Cost**: double-decode (O5a) or small typing addition + intercept (O5b); **MUST read RAW** (not the SDK-parsed `ServiceClaims`, which already dropped `act`); carries a **retirement clause** (retire when O1 lands) → **bounded** drift.
- **Gating**: **R27-CLEAN** (reads identity, mints no writer; drift bounded by RFC-8693 + a defined retirement); **R29-gated** (a read-beside — flips no species/model/validator/gate/audit); **R4-locus**.
- **Distinct from O3**: O5 consumes an **existing correct producer's STANDARD wire-format** (RFC-8693 `act`) with bounded drift + retirement; O3 invents a satellite contract with unbounded drift + no retirement. The RFC anchor + the retirement clause are the separation.

### O6 — [DISCOVERED · NULL] Fail-closed refusal of `agent_access` until modeled  *(no new consumption mechanism)*
- **Mechanism**: the satellite **detects** `token_type=="agent_access"` (read off the raw payload — same substrate as O5) and **fail-closed REFUSES** it until an actor-modeling contract lands — converting today's **silent-admit-with-human-erased** into an **explicit reject**. Solves the gap by **not adding consumption mechanism**.
- **Locus**: asana `jwt_validator.py` (a guard before/around `validate_service_token`).
- **Landability**: satellite-local, minimal — the lowest-mechanism option that closes the erasure.
- **Cost**: **blocks delegated tokens entirely** (no consumption) — trades delegation-availability for erasure-safety; a bridge that stops the bleeding but delivers no "know the human." Shares O5's raw-read substrate; diverges on the ACTION (refuse vs consume).
- **Gating**: **R29-gated** (satellite-local refuse — flips no shared surface); **R4-locus**; **R27-CLEAN** (mints nothing).
- **Why on the slate**: `option-enumeration-discipline` §5 item-2 **requires** a no-new-mechanism/null option; the brief's five are all consume-options. O6 is also the **credential-scope-conformant** posture: the discipline mandates fail-CLOSED on a `(protocol × scope × auth_routing_field)` mismatch (§3) — the honest response to the `act`/service scope collapse is refusal, exactly O6. Today's silent-admit is the fail-OPEN violation O6 corrects. Enumerated, **not ranked above** the consume options — the operator rules the locus.

### O7 — [DISCOVERED · DELEGATION] Auth-server introspection / grant-dereference (resolve `act` at the producer)
- **Mechanism**: instead of the satellite parsing `act` locally, **delegate** act-resolution to the already-capable producer — the auth-server holds the mint + both audit columns; the satellite calls an introspection surface (RFC-7662 token introspection, or the ADR #266 Option-A grant-dereference) that returns the resolved `(delegating_user, acting_agent)`.
- **Locus**: cross-repo — an auth-server introspection endpoint (`services/auth`) + an asana client call. **Composes** with ADR #266's reactive-axis grant-dereference (which the event axis needs at action time anyway — O7 reuses that substrate for the request axis, unifying request + reactive attribution through one producer of record).
- **Landability**: requires an auth-server endpoint (mint + audit exist; introspection may need building) + a satellite network call.
- **Cost**: per-request **network round-trip + availability coupling** on the auth-server at validation time (the same SPOF / fail-open-vs-fail-closed trade-off ADR #266 §6/§9 surfaces for the reactive axis) + latency. No local parse → **no `extra="ignore"` concern and no satellite divergence**.
- **Gating**: **R29-gated** (out-of-band resolution — flips no token species/model/validator/gate); **R4-locus**; **R27-CLEAN** (delegates to the producer of record — zero satellite divergence).
- **Why on the slate**: `option-enumeration-discipline` §5 item-4 **requires** a delegation option when the problem is surfacing information from an already-capable entity; the auth-server ALREADY holds both identities (`audit_log.py:45-46`) and the mint — delegating resolution to it is the canonical delegation option the brief's slate omitted.

### Slate audit (option-enumeration-discipline §6 mechanical check)
- **Option avoiding the SDK claims model entirely?** O5 (raw read), O6 (refuse), O7 (introspection). ✔
- **Delegation option?** O7. ✔ · **Null / no-new-mechanism option?** O6. ✔
- **Existing substrate not otherwise mentioned?** O5 (raw `jwt.decode` dict + `RawTokenPayload`); O7 (auth-server audit/mint/introspection). ✔
- **Hardest open questions surfaced (not softballs)?** §7. ✔

---

## 6. Folded constraints (bind EVERY option — these are not themselves options)

**A. `extra="ignore"` — the declare-or-drop law (grounded in an in-code precedent).** `BaseClaims.model_config = {"extra": "ignore"}` (`claims.py:162`, inherited by all four classes) **silently drops** any undeclared claim at parse — including `act`. This is not hypothetical: the SDK **already documents this exact law** at `claims.py:312-321`, where `external_business_id` is declared with the note that it *"MUST be declared here for the data plane to read the claim — an undeclared claim is silently dropped at parse,"* explicitly referencing a *"delegated-agent path (CONDITION-1, SEC-RULING C1b GATE-1)."* Consequence per option: **O1** declares `act` on the new class (follows the precedent exactly); **O2** is inert without O1's declaration; **O5** MUST read the **RAW** payload (the SDK-parsed object has already dropped `act`); **O6** reads raw only to detect+refuse; **O7** sidesteps it (no local parse). Any option that tries to read `act` off the SDK's parsed `ServiceClaims` is defeated by this law.

**B. D1 schema (ADR #266 C-1 / C-5).** The contract must serve `sub`=human + `act`=agent for **BOTH** request- and event-triggered actions, and **MUST NOT be locked** until the SDK models the actor claim. Therefore this slate is deliberately a **locus enumeration, not a lock**: it specifies where the actor-claim contract *can* land (O1/O4 canonical; O5/O7 bridge; O6 null; O3 anti); the K3 schema lock waits on the chosen locus landing. The reactive axis (event-woken, no inbound JWT) is served natively only by O7's producer-side resolution or by O1's model paired with ADR #266's grant-dereference — O3/O5/O6, being inbound-token-shaped, address the **request axis** and leave the reactive axis to ADR #266's grant seam.

**C. OperatorClaims/4.2.0 is PRE-KILLED-AS-VEHICLE (FORK-D) — recorded, never silently omitted.** `OperatorClaims` (`claims.py:401`) reads `operator_sub` from `BaseClaims.sub` — the **subject IS the machine-operator principal**, not the delegating human — and carries **no `act` field**. Structurally it cannot hold `sub`=human + `act`=agent: it would put the non-human principal in `sub` and erase the human. Its detection is keyed on `token_type=="operator_access"` with a load-bearing **absence of `roles`** (CB-ORD-1) guaranteeing old-SDK-downgrade to ServiceClaims, never UserClaims. **OperatorClaims survives on this slate ONLY as the shape O1's new class must NOT be** — a distinct NEW actor-modeling class (sub=human + act=agent), never a reuse or subclass of OperatorClaims. ADR #266 PRECONDITION-1 warns the same: an `act` contract designed against a stale three-class model risks colliding with the operator-plane detection invariants.

**D. Detection downgrade-safety (the §2 keystone).** Today `agent_access` → SERVICE (§2). Any O1 detection branch MUST be **additive and marker-keyed** (like OPERATOR-branch-first) so it neither collides with the USER/SERVICE branches nor breaks old-SDK downgrade safety: a pre-AGENT SDK must continue to downgrade `agent_access` predictably (to SERVICE, never UserClaims), and O6's fail-closed refusal is the safe posture in exactly that pre-AGENT window.

**E. Credential-scope conformance (`credential-scope-assertion-discipline`).** `act` is the **auth_routing_field** distinguishing the `agent_access` species from `service`; the two must not be collapsed into one scope row. The conformant posture on a decoded-vs-declared mismatch is **fail-CLOSED** (Step 4). Today's silent SERVICE-admission is a fail-OPEN violation; O6 is the fail-closed correction; O1/O5/O7 resolve the field correctly rather than dropping it.

---

## 7. Open questions carried to the operator's R4 packet (escalate to human — do not silently answer)

1. **Who owns/releases the SDK `act` contract, on what cadence?** (ADR #266 Unknown-3). O1/O2 gate the K3 lock on a cross-repo `autom8y-auth` release; this is a fleet sequencing dependency, not an asana-local choice.
2. **Attribution-unavailable policy: fail-open vs fail-closed?** (ADR #266 Unknown-1). Bears directly on O6 (refuse) and O7 (producer availability at validation time). The credential-scope discipline argues fail-closed; ADR #266 leaves it a Phase-2 policy decision.
3. **Type asymmetry `act.sub` (String) vs `sub` (UUID).** `audit_log.py` mirrors it: `acting_agent_id String(255)` vs `delegating_user_id uuid.UUID` (ADR #266 §8 FW-A3). Whatever locus is chosen, the consumption schema must not silently coerce/truncate `agent:{session_id}` (string) against a UUID column.
4. **Bridge → terminal retirement enforcement.** If O5 (or O6) is chosen as a bridge, the retirement trigger (O1 lands → bridge removed) needs a watch entry so the bridge does not calcify into a permanent second contract (the O3 failure mode by drift).

---

## 8. FLIP-NOTHING attestation (R29 — the critical boundary, risk R-SP-2)

- **Nothing merged.** No commit, branch, PR, or push authored by this lane. This artifact is a **working-tree file only**.
- **Nothing deployed / staged-for-flip.** No token species, claims model (`claims.py`), validator contract, detection logic (`_detection.py`), isinstance gate (`client.py:336`), or audit semantics was changed, wherever the code lives (asana or monorepo). All monorepo/asana reads were `git show origin/main:…` against a **FROZEN local main**; zero writes to any source file.
- **R25 honored, R29 held.** Per R25 a file edit is a file edit and this lane *may* read/author anywhere — but the ONLY authorship performed is this specification. The species **migration is R4**, reserved to the operator, and is **untouched**.
- **Scope of authorship**: exactly one file — `.ledge/decisions/SP-species-leg-contract-2026-07-24.md`. No `git add`/`commit`/`branch`/`push`/`merge` performed.

---

## 9. Evidence anchors (SVR) — own-hands, LIVE at origin/main

Method: `git show origin/main:<path>` (asana `dfdb84a3`) and `git -C …/autom8y show origin/main:<path>` (monorepo `790465e0`). Every anchor re-derived at authoring time; none inherited.

| Claim | Anchor | marker_token (verbatim slice) | Method |
|---|---|---|---|
| ServiceClaims-only, audience-gated inbound | asana `jwt_validator.py:24,:83` | `validate_service_token(token, audience="https://api.autom8y.io")` | file-read |
| Four claim classes, no `act` field | monorepo `claims.py:133/165/295/401` | `class BaseClaims(BaseModel)` … `class OperatorClaims(BaseClaims)` (grep-negative for a modeled `act` field) | file-read + bash-probe |
| `extra="ignore"` silent-drop law | monorepo `claims.py:162` | `model_config = {"extra": "ignore"}` | file-read |
| Declare-or-drop precedent (delegated-agent path) | monorepo `claims.py:312-321` | `an undeclared claim is silently dropped at parse` | file-read |
| Mint is correct (RFC-8693 act) | monorepo `token_service.py:414-426` | `act": { "sub": f"agent:{agent_session_id}"` ; `sub = delegating user, act.sub = agent identity` | file-read |
| Agent token discriminator + roles-absence | monorepo `token_service.py:421-431` | `token_type="agent_access"` ; payload has no `roles` key | file-read |
| Detector falls agent_access → SERVICE | monorepo `_detection.py:38-49` | `if claims.get("token_type") == "operator_access"` … `return TokenType.SERVICE` | file-read |
| Audit indexes both legs | monorepo `audit_log.py:45-46` | `acting_agent_id: Mapped[str \| None]` ; `delegating_user_id: Mapped[uuid.UUID \| None]` | file-read |
| SDK's OWN gate; services/auth/client dead alley | monorepo `client.py:336`; `services/auth/client/…/client.py` | `if not isinstance(claims, ServiceClaims):` ; isinstance-count **0** in the dead alley | file-read + bash-probe |
| SDK version + FORK-C pin locus | monorepo `sdks/…/autom8y-auth/pyproject.toml:7`; asana `pyproject.toml:23` | `version = "4.2.0"` ; `"autom8y-auth>=3.3.0"` | file-read |

**Provenance corrections (recorded, not propagated):** (1) brief monorepo SHA `2dce25cc` → LIVE `790465e0` (repo advanced on release; claims.py anchors unmoved vs ADR #266's `a53288db` read). (2) The mint has two correct anchor layers: the router endpoint `routers/tokens.py:405 agent_token_exchange` (ADR #266's cite) calls the service function `token_service.py:403 create_agent_token` (this brief's cite, verified as the emit site). Both correct; the emit is `token_service.py:403`.

---

## 10. Handoff — into the operator's R4 packet (PK)

- **Consumers**: the operator (rules the FORK-α locus in PK); compliance-architect / security-reviewer (bind to §3 `bug_bar_severity`); the R4 species-migration owner (consumes the chosen locus).
- **This lane's terminal state**: the slate is **SURFACED, not selected**. The operator picks the locus; the R4 migration executes it. Per the fold in §6.B the K3 schema stays **unlocked** until the chosen actor-claim contract lands.
- **Recursive-dogfood note**: this artifact makes platform-behavior claims; every one carries an SVR receipt (§9) or is a design argument explicitly graded MODERATE (§1). No claim is asserted STRONG; the two discovered options (O6/O7) are labelled as enumeration-discipline discoveries, not author instinct.

END SP species-leg contract. SURFACE-landed 2026-07-24. FLIP NOTHING held (§8). Self-grade ceiling MODERATE.
