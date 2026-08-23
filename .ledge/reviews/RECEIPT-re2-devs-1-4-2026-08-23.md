---
type: review
artifact_type: RECEIPT
artifact_id: RECEIPT-re2-devs-1-4-2026-08-23
title: "RECEIPT — RE-2 DEV-1..4: the write door checks permission (SEC-001 layer 1, built)"
status: accepted
initiative: provably-landed
sprint: S-14 custody-tail-build (WS-F)
seat: security-reviewer@security (co-seated, inv-20260823-a35f74103374)
date: 2026-08-23
design_of_record: ".ledge/decisions/DESIGN-re2-two-layer-authz-2026-08-13.md"
ratified_by: ".ledge/decisions/RULINGS-coc-phase2-operator-sitting-2026-08-14.md:38-48 (R-7)"
substrate_of_record: "autom8y-asana origin/main = 927cea8b8927a1b3cf4c05fba0d661e37a7fc5ec"
rung_claimed: rung-ENFORCED-IN-PROCESS
rung_not_claimed: rung-ENFORCED-ON-THE-WIRE
self_assessment_cap: MODERATE
evidence_grade_ceiling: MODERATE
critic: verification-auditor@eunomia (rite-disjoint, NOT YET SEATED at authorship)
---

# RECEIPT — RE-2 DEV-1..4

> **Predicate carry (verbatim from the S-14 shape):** *"Exit is asserted on
> realized build output, never on merge state."* Everything below is asserted on
> code that exists and tests that ran. Nothing is asserted on the PR being merged.

## §0 The rung, named precisely

| Rung | Asserts | Status |
|---|---|---|
| `rung-DESIGN` | finding re-derived, options priced, owners named, no code | **SUPERSEDED** — carried by DESIGN-re2 (2026-08-13) |
| **`rung-ENFORCED-IN-PROCESS`** | the control exists, is attached to every declared write route, and **bites in both polarities** against the real app object under test — denied caller 403s and never reaches the handler; authorized caller passes | **CLAIMED** |
| `rung-ENFORCED-ON-THE-WIRE` | a caller lacking authorization receives 403 from the **deployed** service, proved with two live-minted service tokens | **NOT CLAIMED** |

The design (§0) said `rung-ENFORCED` was "unreachable this wave" because a
two-sided harness "requires minting two service tokens" (CR-5) and "exercising a
write route" (CR-1). **That was over-stated, and correcting it is the main
methodological finding of S-14.** A *denied* request never reaches Asana — the gate
raises before the handler body runs. So the deny side is provable in-process with
zero Asana contact and zero credentials, and the allow side is provable by observing
the handler entered. What genuinely remains out of reach is the **wire**: a deployed
service, real JWTs, real network. Hence the split above. `ON-THE-WIRE` stays
unclaimed and is the honest residual (UV-P-S14-3).

## §1 DEV-1..4 — status and named owner of record

Owner derivation is now **mechanical, not imputed**: DEV-4b adds `CODEOWNERS`,
closing the design's own §6 named-owner gap ("autom8y-asana has **no CODEOWNERS
file at origin/main**… the layer-1 owner is therefore imputed").

| ID | Design ref | Deliverable | Anchor | Owner of record | Status |
|---|---|---|---|---|---|
| **DEV-1** | §5.1 L1-1 | Un-loss the claims model — carry `client_id` across the local narrowing | `src/autom8_asana/api/routes/internal.py:84`, `:202`, `:208` | `@autom8y/platform-team` (`CODEOWNERS:28`) | **LANDED** |
| **DEV-2** | §5.1 L1-2 | Deny-by-default write-class gate, applied at every declared write route | `src/autom8_asana/api/write_authz.py:1-445`; 26 call sites | `@autom8y/platform-team` (`CODEOWNERS:26`) | **LANDED** |
| **DEV-3** | §5.1 L1-3 | Plumb identity into the dual-mode family without breaking the PAT branch | `src/autom8_asana/api/dependencies.py:80`, `:295` | `@autom8y/platform-team` (`CODEOWNERS:27`) | **LANDED** |
| **DEV-4** | §5.1 L1-4 | Close the `/v1/receipts` vocabulary hole | `src/autom8_asana/api/main.py:170`, `:198` | `@autom8y/platform-team` (`CODEOWNERS:21` — the `*` default rule; `main.py` has no specific rule) | **LANDED** |
| **DEV-4b** | §6 L1-0 | `CODEOWNERS` — make ownership a mechanical fact | `CODEOWNERS:1-40` | `@autom8y/platform-team` (self-referential by construction) | **LANDED** |

Approver-of-record for all five: **the operator (tomtenuta)**, per
`RULING-cc8-item2-owner-2026-08-14.md:12-14`. Layer 2 (cross-repo scope minting)
remains unbuilt and unowned-in-this-repo by design — it is the `autom8y` monorepo's
`services/auth/` surface.

## §2 The finding the build corrected — the write surface is 4× larger than designed

The design enumerated **five write classes across six routes** and registered
UV-P-5 against exactly this risk (*"no route outside the five enumerated write
classes reaches an Asana write through a path this review did not trace"*).

**UV-P-5 returned NOT NULL.** A derived sweep of `x-fleet-side-effects` over all 70
routes found **26** routes declaring `{"type": "asana_api"}`:

| File | Gated routes | Class |
|---|---|---|
| `tasks.py` | 10 | `tasks:write` |
| `projects.py` | 5 | `projects:write` |
| `sections.py` | 5 | `sections:write` |
| `intake_create.py` | 2 | `intake:write` |
| `entity_write.py` | 1 | `intake:write` |
| `intake_custom_fields.py` | 1 | `intake:write` |
| `receipts.py` | 1 | `receipts:write` |
| `workflows.py` | 1 | `workflows:execute` |
| **TOTAL** | **26** | |

Two routes the design missed entirely are worth naming, because they are not
rounding error: `intake_create.py:209` `route_intake_process` (creates an Asana
process task — a *sixth* write class in a file the design had already read), and
`workflows.py:272` `invoke_workflow` (drives arbitrary registered workflows against
entity GIDs). **Hand-enumeration was the wrong instrument.** GUARD-1 (§4) replaces
it with derivation, so the enumeration cannot silently fall behind again.

## §3 CORRECTION-3 — the axis ruling (threat-modeler lens, disclosed)

**Lens disclosure.** This item was ruled while carrying `threat-modeler` discipline
per the S-14 charge (`.claude/agents/threat-modeler.md`), not security-reviewer's
default review lens. The distinction matters: the question is not *"is this line
buggy?"* but *"which axis, chosen now, is structurally sound against an adversary
who controls token contents?"* Recorded per the out-of-distribution guidance —
this is a STRIDE **Elevation-of-Privilege / Spoofing** class on a documented
primitive, so Bug Bar categorisation applies normally and no escalation was needed.

### The ruling

> **Authorization is keyed on issuer-asserted principal identity, deny-by-default.
> The `scope`/`scopes` axis is REFUSED at every layer, permanently.**

`ServiceClaims.has_scope` (`autom8y_auth/claims.py:221`) opens with:

```python
# Wildcard shortcut (legacy sentinel — grants everything).
if self.scope == "*":
    return True
```

Any token with `scope == "*"` satisfies `has_scope("asana:write")` unconditionally.

**Why the axis, not the call site, is the defect.** The tempting remediation is
"call `has_scope` but also check for `*`". That is a patch on a primitive whose
*contract* is permissive, and it decays: the next call site will not remember. The
ruling therefore refuses the axis itself and makes the refusal machine-checked
(GUARD-2), so the fail-open cannot be reintroduced by a contributor who has not
read this document.

**Admissible axes, in preference order:**
1. **Issuer-asserted principal identity** (built, layer 1) — `service_account_id` →
   `client_id` → `sub`. Signature-covered; **no wildcard sentinel exists in any of
   them**. Fleet precedent: `SCHEDULING_ENROLLMENT_WRITER_CLIENT_IDS`.
2. **The `permissions` axis** (layer 2, ready) — plain membership, no wildcard;
   already the idiom at `admin.py:456`. Shipped as `has_permission_no_wildcard`
   (`write_authz.py:278`), which additionally refuses a `"*"` *permission* entry —
   defence in depth against a future issuer adopting that convention.

**Independent corroboration (rite-disjoint, authored without reference to this
review):** `services/auth/service-accounts.yaml:682-683` — *"The guard resolves
through `ServiceClaims.has_permission` (plain membership), NOT `has_scope`, which
short-circuits True on `scope == '*'`."* The fleet's own auth maintainers reached
the same conclusion independently.

**The carrier is not hypothetical — this is the sharpest evidence S-14 found.**
`AuthClient._dev_bypass_service_claims` (`autom8y_auth/client.py:554-570`) **mints**
`ServiceClaims(sub="dev-bypass-service", scope="*", …)` whenever `dev_mode` is set.
Had RE-2 shipped option (a) as originally posed, **every dev-mode token would have
satisfied every write gate** — a fail-open reachable by an env toggle, not by a
legacy accident. Pinned as a test (`test_the_wildcard_carrier_is_not_hypothetical`)
so that if a future SDK removes the wildcard, the ruling is revisited deliberately
rather than drifting.

**Design consequence, restated:** option (a) is not merely "dominated by (f)" as the
design put it. On this evidence it is **inadmissible**.

## §4 Two-sided teeth — every control shown to BITE in both polarities (D-5)

**59 tests, 59 passed.** Suite: `tests/unit/api/test_write_authz.py` (50) +
`test_write_authz_coverage.py` (9).

Per D-5, an unearned RED counts against us as much as an unearned GREEN, so every
denial below is paired with the **minimal-delta case that must be allowed**. A gate
that denies everything is indistinguishable from a broken gate.

### 4.1 deny-RED — observed

| # | Case | Observed |
|---|---|---|
| R1 | Unauthorized principal, allowlist populated | **403 `INSUFFICIENT_PRIVILEGE`**, `handler_calls == []` — handler never entered, no Asana call reachable |
| R2 | `scope="*"` wildcard carrier | **403** — the carrier that defeats `has_scope` gets nothing |
| R3 | Principal authorized for `tasks:write` hitting `receipts:write` | **403** — classes do not confer each other |
| R4 | Lower-tier `client_id` allowlisted but higher-tier `service_account_id` not | **denied** — a caller cannot demote itself into a permissive tier |

**R1 observed live on a REAL route in the REAL app**, before any fixture existed —
`/v1/receipts` under the pre-existing receipts suite:

```
{"write_class": "receipts:write", "principal": "email_booking_intake",
 "principal_tier": "service_name", "mode": "enforce", "allowlist_size": 0,
 "would_deny": true}   →   HTTP/1.1 403 Forbidden
```

### 4.2 allow-GREEN — observed

| # | Case | Observed |
|---|---|---|
| G1 | Allowlisted principal | **200**, `handler_calls == ["entered"]` |
| G2 | Allowlisted principal **carrying `scope="*"`** | **200** — proves R2 denies on the *allowlist*, not on `scope`; the gate is indifferent to `scope` entirely |
| G3 | **PAT-branch caller, allowlist unset** | **200** — DEV-3's highest-regression-risk case. An over-broad gate would 403 here |
| G4 | Tier-1 `service_account_id` allowlisted | **200** — canonical identity is the one that authorizes |
| G5 | `OBSERVE` mode, unauthorized caller | **200** — proves OBSERVE is reachable, which is what makes R5 below discriminate |

### 4.3 malformed-config RED — observed

| # | Misconfiguration | Resolved | Observed |
|---|---|---|---|
| M1 | Allowlist **unset** | `frozenset()` | **403** |
| M2 | Allowlist `""`, `"   "`, `","`, `",,,"`, `" , , "` | `frozenset()` | **403** |
| M3 | Mode **unset** | `ENFORCE` | control active |
| M4 | Mode `"observ"`, `"OBSERVE!"`, `"off"`, `"disabled"`, `"true"`, `"0"`, `""` | `ENFORCE` | **403** — a typo one character short of a bypass does **not** bypass |
| M5 | Non-`str` identity (object with `__eq__` returning True) | skipped, falls through | **not admitted as a principal** |

M4 is paired with G5: OBSERVE *is* reachable by the exact literal, so M4 proves
fail-closed discrimination rather than a constant.

### 4.4 Drift guards — themselves two-sided

| Guard | GREEN (real substrate) | RED (synthetic broken fixture) |
|---|---|---|
| **GUARD-1** coverage — every declared Asana-write route carries the gate | 26/26 gated in the real `create_app()`; anti-vacuity assertion `>= 26` declared routes | guard returns `["POST /forgotten"]` for a synthetic ungated write route; returns `[]` for reads (does not over-fire) |
| **GUARD-2** axis ban — `has_scope`/`require_scope` absent from `src/` | 0 hits across all scanned sources | trips on synthetic `claims.has_scope(...)` and on `from autom8y_auth import require_scope`; does **not** trip on `has_permission`; **does not shelter a real call hiding behind a docstring** |

Per the discriminating-canary doctrine, **no defect was injected into production
code**. Both RED sides run against deliberately-broken *synthetic input* that the
guard must correctly reject — the guard is the thing under test, not the codebase.

GUARD-2 bit during development on a true positive: it flagged `internal.py:67`,
prose in a DEV-1 docstring. The instrument was sharpened (AST-precise docstring
exemption) rather than the code reworded around it — and a further test was added
proving the exemption is not a bypass.

### 4.5 Regression evidence — baseline-differenced

| Run | Result |
|---|---|
| `tests/unit/api` @ `origin/main` (clean baseline worktree) | **0 failed** |
| `tests/unit/api` @ this branch, first pass | **272 failed** — all attributable to this change |
| `tests/unit/api` @ this branch, final | **1570 passed, 0 failed** |

The 272 are recorded rather than hidden, because they are the **strongest single
piece of evidence that the gate is real**: with no allowlist configured, the
deny-by-default control refused every S2S write in the suite. Two distinct causes,
both genuine:

1. **75 denials** (`autom8_data`, `email_booking_intake`) — the gate working as
   designed against an unconfigured allowlist. Resolved by declaring those
   principals in `tests/conftest.py:241-250`, which mirrors deployment-time config.
   It is **not** a bypass: mode stays `ENFORCE`, and the dedicated teeth suite
   strips the fixture back off so its RED cases test the gate, not the fixture.
2. **A real defect in DEV-1, found by the suite.** `getattr(claims, "client_id",
   None)` returns a `MagicMock` under test doubles, which pydantic rejected. Fixed
   at `internal.py:202-208` with an `isinstance(str)` narrowing that is *also* the
   safer production behaviour: an authorization key must be a genuine string or
   absent, never a duck-typed object that gets to define its own `__eq__`.

## §5 Fail-closed posture — the complete table

| Condition | Resolution | Anchor |
|---|---|---|
| mode unset | `ENFORCE` | `write_authz.py:153` |
| mode malformed | `ENFORCE` (+ warning) | `write_authz.py:153` |
| allowlist unset / empty / garbage | `frozenset()` → deny-all | `write_authz.py:175` |
| principal unresolvable | deny | `write_authz.py:264` |
| non-`str` identity | tier skipped | `write_authz.py:204` |
| `"*"` in allowlist | authorizes a principal *named* `"*"`, nothing else | `write_authz.py:264` |
| PAT branch | **skipped by design** (Asana ACL authorizes) | `write_authz.py:385` |

There is deliberately no allow-on-error branch anywhere in the module.

## §6 Deployment hazard — LOUD, and not resolved by this PR

**This PR is safe to merge and NOT safe to deploy unconfigured.** The gate defaults
to `ENFORCE` with an empty allowlist, which means **every S2S Asana write 403s until
allowlists are provisioned**. That default is deliberate — a control that defaults to
inert is precisely the failure CORRECTION-1 documented (a drafted, route-mapped,
published-and-unenforced scope vocabulary already sat in this repo). Shipping
another one would be theatre.

The operator has two safe paths, and this seat does **not** choose between them:

- **Shadow-first:** set `ASANA_WRITE_AUTHZ_MODE=observe`, deploy, harvest
  `write_authz_would_deny` receipts for a soak window, populate the six allowlists
  from observed traffic, then remove the var (unset ⇒ `ENFORCE`). While OBSERVE is
  set the service is in exactly its pre-RE-2 state and **CR-1 remains the only
  control** — this is disclosed in the module docstring, not buried.
- **Configure-first:** populate the six `ASANA_WRITERS_*` vars in the ECS task
  definition from the known caller set, deploy straight to `ENFORCE`.

Env vars: `ASANA_WRITERS_{TASKS,PROJECTS,SECTIONS,INTAKE,RECEIPTS}_WRITE`,
`ASANA_WRITERS_WORKFLOWS_EXECUTE`, and `ASANA_WRITE_AUTHZ_MODE`.

## §7 Non-claims (binding — carried forward from DESIGN §5.3)

1. **CR-1 is NOT retired.** This closes *service-level* authorization. CR-1 is an
   operator/agent-authority control that no service-level mechanism can answer.
   Reading "the write door checks permission" as "CR-1 can be lifted" is a category
   error.
2. **Exploitability is NOT bounded.** SEC-002 / SEC-003 are untouched. Severity
   stays **High**, with the design's escalation condition intact: if SEC-002 returns
   that an agent seat can obtain a qualifying JWT by documented patterns, SEC-001
   escalates to **Critical**.
3. **`rung-ENFORCED-ON-THE-WIRE` is NOT claimed** (§0).
4. **No "history clean" claim is made anywhere in S-14.** F-2 is staged, not fired
   (`RUNBOOK-f2-cred-t21-rotation-2026-08-23.md` §4). Own-hands live probe confirms
   the leaked PAT is **still un-rotated** (`LastChangedDate` 2026-04-08, earlier than
   the 2026-07-07 leak filing).
5. **No Asana write of any class was executed** (CR-1) and **no credential value was
   read** (CR-5).

## §8 Fences honored

| Fence | Status |
|---|---|
| **CR-1** — no Asana write path exercised | **HONORED.** No Asana API call. Denials are proved *before* the handler; allows are proved against a stub handler or mocked clients. |
| **CR-5** — no credential material | **HONORED.** `describe-secret` (metadata) only; `get-secret-value` **never invoked**. No token read, reconstructed, or written. |
| Secrets never to disk / argv | **HONORED.** No credential temp file was created, so none needed shredding. Runbook §3 specifies `fileb://` + `shred` for the operator. |
| PII fence | **HONORED.** Only service identifiers, ARNs, GIDs. No personal data. |
| No `\|\| true` | **HONORED.** No swallowing added; the suite's exit codes are load-bearing throughout. |
| Foreground, bounded polls | **HONORED.** |
| Do NOT merge | **HONORED.** PR opened, not merged. |
| MODERATE self-cap | **HONORED.** No STRONG self-grade; rite-disjoint critic not yet seated. |

## §9 UV-P register

[UV-P: no route reaches an Asana write WITHOUT declaring an `x-fleet-side-effects` `asana_api` entry | METHOD: exhaustive outbound call-graph trace from every route handler to the `clients/` HTTP call sites | REASON: GUARD-1 derives the write surface from the routes' own declaration, which is a large improvement on the design's hand-enumeration (6 → 26) but inherits its trust boundary — an undeclared write is invisible to it. Narrower than what it replaces, not zero. Carried as UV-P-S14-1.]

[UV-P: the `service_account_id` tier is reachable in production for the dual-mode write family | METHOD: inspect `request.state.claims_dict` on a live `/api/v1/tasks` request | REASON: `JWTAuthConfig.exclude_paths` lists `/api/v1/tasks/*`, `/api/v1/projects/*`, `/api/v1/sections/*`, so `JWTAuthMiddleware` may not populate `claims_dict` on those paths — in which case that family authorizes on `client_id`/`sub` (tiers 2-3), never tier 1. Fail-closed either way and the allowlist simply must name the tier actually presented, but operators MUST verify which identity their callers present before populating allowlists. Carried as UV-P-S14-2.]

[UV-P: the gate returns 403 to an unauthorized caller on the DEPLOYED service | METHOD: two live-minted service tokens with different authorization states against the deployed write surface | REASON: this is the `rung-ENFORCED-ON-THE-WIRE` predicate. It requires credential minting (CR-5) and a deploy, neither of which is this seat's. All evidence in §4 is in-process against the real app object. Carried as UV-P-S14-3.]

[UV-P: the suite-wide allowlist in `tests/conftest.py` does not mask a future write-route regression | METHOD: rite-disjoint review of the fixture's blast radius | REASON: authorizing three principals for all six classes suite-wide is a pragmatic fix for 75 denials. It is bounded by GUARD-1 (a new ungated route still fails CI) and by the teeth suite (which strips the env), but a new test asserting an unauthorized caller is allowed would pass spuriously. Carried as UV-P-S14-4.]

[UV-P: `has_permission_no_wildcard` behaves correctly against REAL issuer-emitted permissions | METHOD: layer-2 integration once per-write-class scopes are minted at `services/auth/service-accounts.yaml` | REASON: the predicate is layer-2-ready and unit-tested, but has no production caller yet — layer 2 is unbuilt and cross-repo. It is shipped ready, not shipped live, and this receipt does not claim otherwise.]

## §10 Attestation

**Substrate:** `origin/main = 927cea8b8927a1b3cf4c05fba0d661e37a7fc5ec`. Branch
`security/re2-s14-write-authz`, built in an isolated worktree; baseline differenced
against a second clean `origin/main` worktree.

| Claim | Method | Result |
|---|---|---|
| 26 declared Asana-write routes exist | AST sweep of `openapi_extra` over all route modules | 26 of 70 routes |
| 26/26 carry the gate in the real app | `create_app()` + route-dependency introspection | 26/26 |
| `has_scope` wildcard fail-open present in SDK 4.1.0 | file-read + executed assertion | `claims.py:221`, CONFIRMED |
| Dev-bypass mints `scope="*"` | file-read + executed assertion | `client.py:554-570`, CONFIRMED |
| Auth service independently refuses the axis | file-read (monorepo `origin/main`) | `service-accounts.yaml:682-683`, CONFIRMED |
| Gate denies unauthorized on a real route | live TestClient against real app | 403 + structured receipt, OBSERVED |
| Baseline is clean | full `tests/unit/api` at `origin/main` | 0 failed |
| Post-change suite is clean | full `tests/unit/api` at branch | 1570 passed, 0 failed |
| Teeth suite | `test_write_authz*.py` | 59 passed |
| Lint/format | `ruff check src/ tests/`, `ruff format --check` | clean |
| F-2 not executed; PAT un-rotated | `describe-secret` (metadata only) | `LastChangedDate` 2026-04-08 < leak-filed 2026-07-07 |
| PAT consumer topology | ECS describe-services/task-definition + Lambda list-functions | 1 ECS service + 8 Lambdas |

**Self-assessment: MODERATE** per `self-ref-evidence-grade-rule` / F-C. The
rite-disjoint critic (`verification-auditor@eunomia`) was **NOT seated** at
authorship; completeness of the sweeps is a single-seat assertion. The strongest
claim here — the `has_scope` wildcard fail-open and the axis ruling that follows —
carries **independent rite-disjoint corroboration** from the auth service's own
maintainers at `service-accounts.yaml:682-683`, authored without reference to this
review, and is additionally pinned by an executed assertion against the installed
SDK.
