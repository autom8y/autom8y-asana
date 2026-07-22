---
type: decision
artifact: operator-rulings-record
initiative: fleet-mcp-substrate (asana seat) — the fleet-halt interview
date: 2026-07-22
method: >-
  Structured operator interview (/interview, AskUserQuestion), five adaptive
  phases under the operator's two-tier discipline: standing rulings (R1-R12 of
  2026-07-20 + the fleet-era commitments) received confirm-only treatment; the
  five OPEN items were litigated fresh with the strongest honest case AGAINST
  presented before each ruling. All four convergence blocks confirmed as
  drafted — zero amendments, zero strikes. Selections quoted verbatim.
operator: Tom Tenuta
scribed_by: dispatcher session b3f74f84 (scribe-at-direction; content is the operator's)
supersedes: nothing — R1-R12 (2026-07-20) stand; this record adds R13-R23
evidence_note: >-
  The R16 live probe was EXECUTED at inscription time (2026-07-22, read-only
  GETs against https://auth.api.autom8y.io) — verdict PASS, receipts in §R16
  below. This lifts the chain's largest unverified premise (deployed-surface
  identity, spike §9-item-1/§11.7-item-7).
---

# OPERATOR RULINGS R13–R23 — the fleet-halt decision space (2026-07-22)

## Block A — Delta (what changed since R1–R12)

**R13 · Value bar — AMENDED.** A third clause joins the standing two: success now
also requires *"demonstrating that an automated action visibly carried a real
person's identity"* (verbatim option: "Identity joins the bar"). Standing
clauses (capability proven + nothing bad happened) persist unamended.

**R14 · Pace — RATIFIED · EXECUTES-NOW (posture).** "Sustain the compounding."

**R15 · Energy — RATIFIED · EXECUTES-NOW (posture).** "Both in parallel" — the
company identity spine and this workspace's local lanes advance together.

## Block B — The signature and its riders

**R16 · Serving-path signature — SIGNED, GATED ON A LIVE PROBE (AMENDED-signature).**
The operator's word is given on serving the remote surface via the
company-owned edge directly; the build opens only on a live, read-only probe
confirming the deployed auth service serves the code the design assumes; a
contradicting probe returns the signature to the operator. The adversarial
case was presented in full before the ruling (static-read ceiling; six-day
spec gate unpassed; un-re-scored bundled-deployment decision; first-consumer
coupling; consent journey untouched by any signature).
**PROBE EXECUTED 2026-07-22 — VERDICT: PASS.** Receipts (read-only GETs,
https://auth.api.autom8y.io): `/health` 200; OIDC discovery advertises
`authorization_endpoint=/authorize` and `token_endpoint=/oauth/token/exchange`
(the user-plane pair, exactly per jwks_service.py expectations),
`grant_types_supported=["authorization_code","urn:autom8y:grant-type:business-exchange"]`,
`code_challenge_methods_supported=["S256"]` only,
`token_endpoint_auth_methods_supported` includes `"none"` (public-client PKCE),
NO `registration_endpoint` (only-advertise-what-exists, consistent with no-DCR);
`/.well-known/jwks.json` serves 1 live key (kid `2024-12-v1`);
`/.well-known/oauth-protected-resource` 404 (the PRM must-build confirmed
still absent, as designed). HONEST SCOPE: discovery/read surface only; POST
behaviors (consent, exchange) not exercised — outside the read-only class.
**EFFECT: the serving-path build lane is OPEN. The transport-specific build
remains held by R22 — the two gates are separate and compose.**

**R17 · Domain pin — RATIFIED (with named amendment) · QUEUED (rides the serving
build).** "Confirm + exception path": the surface pins to org-domain accounts,
with a per-person exception list namable later, granted only by the operator;
the exception mechanism is acknowledged as future surface someone must build
and audit.

**R18 · Telemetry-allowlist flag — RATIFIED · QUEUED (hygiene queue).** The
pre-existing gmail-in-otel-gateway-allowlist entry routes to the hygiene lane
with its own review, decoupled from this arc ("Route to hygiene lane").

## Block C — The open pillars

**R19 · Daily-tool cutover — RATIFIED · QUEUED (open-ended).** "Organic, no
forcing function" — the shared machine credential retires when convenient.
Recorded with the tension the operator chose in full view: *this is the exact
debt pattern the identity vision was declared against, and it carries no
retirement date by deliberate choice.* Not papered; named.

**R20 · The proof — AMENDED (structures the felt bar) · QUEUED.** "Two moments,
staged": **Moment one (gate-proof)** — the identity is accepted at the gate and
the action succeeds on the person's authority, with ALL THREE boundary caveats
spoken verbatim in the record: (i) the workspace-vendor side still acts as the
shared bot — attribution is real inside the fleet, not inside the vendor's
product; (ii) whether the carried identity is USED downstream (data selection,
audit lines) is unmapped at ruling time; (iii) absent the live probe the
mechanism was design-proven only (caveat iii is now PARTIALLY lifted by R16's
probe for the auth surface specifically). **Moment two (consumption-proof)** —
the audit trail names the human and what they can touch reflects their
authority — a named ceremony that MUST receive its own date when the spine
lands; per the operator's chosen option, "the second one must actually happen
or the asterisk becomes permanent."

**R21 · Lane ordering — RATIFIED · EXECUTES-NOW (dispatches authorized).** "All
three concurrent": (1) protect-the-driver (durable mount re-point, credential
rotation motion, the R5-mandated confirm-before-firing gate, the 401-fail-clean
fix); (2) delegation-landing readiness (the R16 probe — now discharged; the
downstream identity-consumption mapping; the R10-mandated startup proposal);
(3) the evidence engine (team daily workflows, trigger-confirmation loop).
Confirming Block C authorized dispatches to begin at inscription.

## Block D — Held doors (still-standing confirms only, per the operator's rule)

**R22 · The dated spec gate — RATIFIED (re-confirmed) · auto-resolves at the
date.** "Stands as held": the remote-transport build waits for the 2026-07-28
spec clarity regardless of the probe outcome.

**R23 · External access — RATIFIED (re-confirmed).** "Stands closed": access
beyond the internal team remains closed, reopenable only by the operator's
word. No exploration invited or opened.

## Deliberately left undecided (named so silence is never consent)

1. The cutover date (R19 — open-ended by choice).
2. Moment-two's date (R20 — minted when the spine lands; a standing debt marker
   until then).
3. The exception-list mechanism's design (R17).
4. Staffing/budget of any lane (proposals carry real numbers to R4's gates).
5. The outer-ring per-user vendor sign-in (unscoped; held outside the proof bar
   deliberately via caveat i).

## Questions deliberately NOT asked (and why)

1. Reopening either held door — the operator's rule: reopening is theirs to
   initiate, not the interviewer's to invite.
2. The fleet-level fork votes already ratified at the fleet gate — standing,
   not re-litigable here.
3. Re-asking the cutover trigger given its named tension — the operator ruled
   with the tension visible in the option text; asking again is re-litigation.
4. Lane staffing details — proposals will surface real numbers for real
   approvals.
5. The second integration's sequencing — already committed and queued by the
   operator's standing fleet ruling.

## Work set in motion at inscription (the EXECUTES-NOW ledger)

- R16 probe: EXECUTED, PASS (receipts above) — serving-path build lane OPEN.
- Lane 1 dispatch: durable mount worktree + config re-point (with backup;
  effective at the operator's next session restart), rotation MOTION drafted
  (operator-mediated execution), confirm-gate + 401-fix PRs authored under the
  R7 review path (no self-merge).
- Lane 2 dispatch: read-only identity-consumption mapping + species-widening
  design doc (feeds the now-open spine build and R20's moment two).
- Lane 3: dispatch follows the first two waves' receipts (same authorization).
