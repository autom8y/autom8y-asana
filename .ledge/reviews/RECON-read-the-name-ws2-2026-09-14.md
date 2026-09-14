# RECON — WS-2 (Offer-grain activation observer) · READ-ONLY · 2026-09-14

**Charge:** `read-the-name` wave 1, sprint T5 (per sitting XI R-170, and the F8 J3 REC).
**Station:** architect (10x-dev, co-seated in `autom8y-asana`). **Class:** READ-ONLY recon.
**Built:** nothing. **Applied:** nothing. **Merged:** nothing. **AWS calls:** none.
**Self-cap:** MODERATE (`self-ref-evidence-grade-rule` — single agent, no rite-disjoint
corroboration; every code claim is `origin/main`-anchored and first-hand).

## §0 REFS NAMED (every file:line below is read at one of these two refs)

| ref | repo | sha | how read |
|---|---|---|---|
| **R-ASANA** | `autom8y-asana` `origin/main` | `49506a21b173c2dd6af5686cc9a0dbfc7c85ea1f` | `git show origin/main:<path>` |
| **R-A8** | `autom8y` `origin/main` | `a1f3ecf3a10dd678d520318f3e16a454366452c0` | `git show origin/main:<path>` |

The `autom8y` working checkout is on `fix/wss-wildcard-scope-bypass-closure`, **not** main;
every `autom8y` read below went through the explicit `origin/main:` ref, never the checkout
(the standing checkout-is-not-origin/main hazard).

Working-tree-only artifacts consulted (labelled as such, never as `origin/main`):
`.sos/wip/PYTHIA-forks-read-the-name-wave1-2026-09-14.md` (§F8 J/K slate, V-28/V-29),
`.ledge/decisions/ADR-ws-join-office-naming-path-2026-09-08.md` (Option C). Both are
UNTRACKED at R-ASANA — `git show origin/main:.sos/wip/PYTHIA-...` → path does not exist.

**Label key:** VERIFIED = re-derived first-hand at a named ref this session ·
INHERITED = taken from a prior artifact, not re-derived · UV-P = deferred, method stated.

---

## §1 Q1 — V-29 RE-DERIVED: **VERIFIED** (with a two-part reading and one correction)

> **Claim under test (V-29, previously INHERITED):** *"the executor's live path
> (`dry_run=False` → `task_service.move_to_section`) bypasses `write_authz`."*

### 1.1 Verdict

**VERIFIED as a code-path fact. The bypass is reachable by construction and is
UNREACHED today — there is no caller anywhere in `src/` that passes `dry_run=False`.**

Both halves are load-bearing. "Bypasses" is true of the path; "is bypassing" is false of
production. A WS-2 charge that reads only the first half will over-scope; one that reads
only the second will build an observer whose enforcement leg walks into an ungated write
the first time someone flips a flag.

### 1.2 The call chain, traced (all R-ASANA)

| # | site | what it does |
|---|---|---|
| 1 | `src/autom8_asana/reconciliation/executor.py:47-55` | `execute_actions(actions, *, dry_run=True, task_service=None, client=None, project_gid=None, section_name_to_gid=None)` |
| 2 | `executor.py:97-110` | `dry_run=True` branch: logs `reconciliation_executor_dry_run`, `result.skipped += 1`, **returns before any call** |
| 3 | `executor.py:113-128` | live branch pre-flight: raises `RuntimeError` if any of the four deps is `None`. This is a *completeness* check, **not an authorization check** |
| 4 | `executor.py:159-164` | `await task_service.move_to_section(client, gid=action.unit_gid, section_gid=target_section_gid, project_gid=project_gid)` |
| 5 | `src/autom8_asana/services/task_service.py:463-495` | `move_to_section(...)`; **:481** `task = await client.tasks.move_to_section_async(gid, section_gid, project_gid)` then fires a cache-invalidation `MutationEvent` (:485-493). No principal, no claims, no gate |
| 6 | `src/autom8_asana/clients/tasks.py:816-830` → `src/autom8_asana/clients/task_operations.py:151` | SDK delegation. No gate |

**Nothing at steps 4-6 consults `write_authz`.** VERIFIED by exhaustive grep of `src/**.py`
at R-ASANA for `write_authz|require_write_authz|is_authorized|WriteClass`: every hit is in
`api/routes/*`, `api/write_authz.py` itself, or a *comment* (`api/main.py:199-200`,
`api/routes/forwarding_stage_census.py:6-10`, `api/routes/internal.py:47,69`). **Zero hits
under `clients/`, `services/`, `reconciliation/`, `lifecycle/`, `lambda_handlers/`.**

### 1.3 Why the gate cannot reach an in-process caller

`api/write_authz.py:385-428`: `require_write_authz(write_class)` returns
`_write_authz_gate(request: Request, auth_context: Annotated[AuthContext, Depends(get_auth_context)])`
— a **FastAPI route dependency**. Its own docstring (:403-406) states the property:
*"Route dependencies are resolved BEFORE the handler body runs."* A caller that never
enters a route never resolves a dependency. The gate is structurally unreachable from a
Lambda/in-process caller; it is not a check someone forgot to add on a path, it is a check
that lives on a different plane from that path.

Complete enumeration of enforcement sites at R-ASANA (all `dependencies=[...]` on routes):

| write class | sites |
|---|---|
| `INTAKE` | `entity_write.py:195`, `intake_create.py:73,210`, `intake_custom_fields.py:57` |
| `PROJECTS` | `projects.py:227,277,341,471,518` |
| `RECEIPTS` | `receipts.py:99` |
| `SECTIONS` | `sections.py:103,153,204,255,308` |
| `TASKS` | `tasks.py:197,259,324,490,545,595,648,702,751,801` |
| `WORKFLOWS` | `workflows.py:280` |

### 1.4 CORRECTION to F8's K-slate framing — the class is `TASKS`, not `INTAKE`

F8's "Write-authz bypass routing" preamble names *"the live `WriteClass.INTAKE` gate"* as
what K2 would restore. That is the wrong class for this call.

The HTTP twin of `executor.py:159` is `POST /tasks/{gid}/section` at `tasks.py:636-686`:
gated at **`tasks.py:648`** by `Depends(require_write_authz(WriteClass.TASKS))`, and its
handler calls **the same** `task_service.move_to_section` at `tasks.py:681`. `INTAKE` gates
the three intake/entity-write routes and no section move. **VERIFIED.** This correction
materially changes K2's cost — see §3.

### 1.6 The bypass is a CLASS, not an instance — a second in-process write plane

While enumerating the above, a second ungated in-process Asana write surfaced at R-ASANA:
`src/autom8_asana/persistence/healing.py:351` `await client.tasks.add_to_project_async(...)`
(the self-healing path; `HealingManager` is imported by `persistence/session.py:26` and
re-exported at `persistence/__init__.py:105`, and `client.py:35` imports `SaveSession`).
It is OPT-IN (`healing.py:11-13`) and likewise never touches `write_authz` — **VERIFIED**,
same exhaustive grep as §1.2.

This matters for the K-slate: the reconciliation executor is **an instance of a class**, not
a singular hole. Any "fix the executor" framing leaves `healing.py` exactly where it is.
K1's "closes the whole class" claim is therefore *substantively true* — and so is its price
(§3.1). Recorded, not adjudicated: `healing.py` is outside WS-2's scope and belongs to the
SID-26 / security limb that sitting X §6 already flagged.

### 1.5 The live-ness half: no caller, today

- Only in-repo caller of `execute_actions` is `lambda_handlers/reconciliation_runner.py:138`
  — `await execute_actions(result.processor_result.actions, dry_run=True)`; its config is
  `ReconciliationConfig(dry_run=True)` at **:125** with the inline comment
  `# SHADOW MODE: always dry_run`, behind an env gate at **:61**
  (`ASANA_RECONCILIATION_SHADOW_ENABLED`). VERIFIED.
- `reconciliation/engine.py:131` records `"executor not invoked from engine -- use
  executor.execute_actions()"` — the engine does not call it either. VERIFIED.
- Its host (`autom8-asana-cache-warmer`) is `schedule_enabled = false`
  (R-A8 `terraform/services/asana/main.tf:501`). VERIFIED.
- **No call site anywhere in `src/` passes `dry_run=False` to `execute_actions`.** VERIFIED
  by enumerating all 13 `dry_run=False` occurrences in `src/**.py` at R-ASANA: nine are
  docstring / error-message text inside `executor.py` itself (`:5,60,73,75,77,80,86,125`
  plus the module header), one is a docstring example (`persistence/healing.py:25`), and
  three are `dataclass` **field values** on result objects, not arguments
  (`persistence/healing.py:368,388` `HealingResult(..., dry_run=False, ...)`;
  `services/scheduling_stratum_push.py:222,234` `StratumPushResult(..., dry_run=False, ...)`).
  **Zero are calls.** (A bare `grep -c` returns 13 and would read as a live-path count —
  it is not one.)

**Consequence for the K-slate:** F8 §11 says *"F8's whole K-slate is moot if false."* It is
not false — the slate stands. But the slate is a **design-debt** question, not an incident:
nothing is writing around the gate right now, and nothing can start to without a code change
that passes a reviewer.

---

## §2 Q2 — WHAT THE OFFER-GRAIN OBSERVER NEEDS

The observer's job, stated once: **hold prior Offer→section membership for project
`1143843662099250`, re-read it on a cadence, and emit a dated `ActivationTransition` for
every offer that CROSSED INTO the activating bucket since the last read.**

### 2.1 The read — where membership comes from (options)

| # | option | receipts | disposition |
|---|---|---|---|
| **R-A** | **Live Asana read.** `clients/sections.py:319` `list_for_project_async` for the section roster; tasks fetched with `memberships.section.name` in `opt_fields` — the idiom already exists at `services/dataframe_service.py:110`, `services/section_timeline_service.py:99`, `automation/workflows/active_offer_enumeration.py:154` | VERIFIED (all R-ASANA) | **Fallback / verification leg.** Spends Asana rate budget on a project with a 429 history, and needs a credential the observer would otherwise not need |
| **R-B** | **The warmed Offer frame already in S3.** `lambda_handlers/traffic_offer_divergence_tripwire.py:208-212` pins `OFFER_FRAME_KEY = f"{DATAFRAMES_V2.prefix}{OFFER_PROJECT_GID}/offer/dataframe.parquet"`; **:217** `REQUIRED_OFFER_COLUMNS = ("office_phone", "section", "is_completed")` — **the frame already carries a per-offer `section` column** | VERIFIED (R-ASANA) | **★ REC (primary).** Zero Asana calls, zero Asana credential, and an IAM precedent that is already written (§2.2) |
| **R-C** | **The service's own HTTP surface** (`/v1/offers/section-timelines`, query router) | INHERITED (prior-wave finding; not re-read tonight) | **REJECT for v1.** Adds an auth hop and a live-service dependency to an instrument whose whole value is being independent of the thing it watches |

**The one hazard R-B carries, stated:** the frame is only as fresh as whatever warms it, and
**every** warmer module in the asana stack is `schedule_enabled = false`
(R-A8 `main.tf:501` offer warmer, `:723` bulk, `:899` section — VERIFIED). The frame is
presumably refreshed by the ECS service's on-demand warm path; *how stale it actually is
right now was not measured.*
`[UV-P: the S3 Offer frame's current LastModified / staleness | METHOD: s3 head-object on the OFFER_FRAME_KEY under the asana role | REASON: this charge is read-only with no AWS calls]`
Mitigation, not deferral: the observer must **refuse** on a stale input rather than emit a
false crossing — the exact posture the tripwire already ships
(`traffic_offer_divergence_alarm.tf:270`, R-A8: *"the emitter refuses rather than reading
403 as a first run and re-seeding, which would false-page"*).

### 2.2 The prior-state store (options, with rejected reasons)

| # | option | receipts | disposition |
|---|---|---|---|
| **S-1** | **An S3 state object in `autom8-s3`.** Bucket declared at R-A8 `terraform/services/asana/s3.tf:13-14`, **versioned** `:21-22`, SSE `:28-29`. IAM precedent is exact and already written: R-A8 `traffic_offer_divergence_lambda.tf:232` `["s3:GetObject","s3:PutObject"]` on **one exact key**, plus **:262** `s3:ListBucket` on the bucket — with the reason spelled out at **:237-247**: without `ListBucket`, S3 answers a MISSING key with **403, not 404**, and an emitter that reads 403 as "first run" re-seeds silently | VERIFIED (R-A8) | **★ REC.** One new key, one IAM statement copied from a sibling in the same stack, versioning already on (so two successive versions ARE the receipt) |
| **S-2** | **DynamoDB.** `api/middleware/idempotency.py:265` constructs `boto3.client("dynamodb")` | VERIFIED (R-ASANA); and VERIFIED-ABSENT in IaC: the **only** `dynamodb` string in the whole asana stack is `backend.tf:10 dynamodb_table = "autom8y-terraform-locks"` (the state-lock table) | **REJECT.** The table this stack would need is not this stack's IaC. A new table + new IAM = a resource-creating apply on a stack whose apply path is itself an open hazard (§4.3) |
| **S-3** | **SSM Parameter Store.** | **VERIFIED-ABSENT**: exhaustive grep of `src/**.py` at R-ASANA for `"ssm"` / `ssm_client` / `get_parameter` returns **zero** hits | **REJECT.** No precedent in this service at all, plus a 4KB/parameter ceiling against a per-offer membership map |
| **S-4** | **Local parquet**, reusing `lifecycle/observation_store.py` (`:40` `_DEFAULT_BASE_DIR = Path.home()/".autom8"/"stage_transitions"`, `:43` `StageTransitionStore`, append-only) | VERIFIED (R-ASANA) | **REJECT as the store** (Lambda-ephemeral; dies on cold start, and a store that silently empties makes every offer look like a first-time crossing). **Keep its *schema* as prior art** for the in-run record shape |
| **S-5** | **CloudWatch metrics as the state** | — | **REJECT.** A metric is not readable as prior membership; you cannot diff last tick's roster out of a counter |

### 2.3 The crossing emission

The seam is already built and landed; the observer supplies inputs, nothing more.

- `lifecycle/activation_referent.py:112-127` `offer_grain_hook(*, checks=None, clock=None)` →
  `ActivationSmokeHook(offer_grain_referent(), default_pipe_checks() if checks is None else checks)`. VERIFIED.
- `activation_referent.py:92-109` `offer_grain_referent()`: grain `"offer"`,
  `project_gid=OFFER_CLASSIFIER.project_gid`, `activating_buckets={ACTIVATING}`, matcher
  derived from `OFFER_CLASSIFIER` (**by reference, not by copy** — `:77-80`), aggregation
  rule `max_offer_activity` (`:105-108`) mirroring `models/business/business.py:465`. VERIFIED.
- The project and the bucket names: `models/business/activity.py:183` `project_gid="1143843662099250"`;
  the activating group at `:193-195` = `ACTIVATING`, `IMPLEMENTING`, `NEW LAUNCH REVIEW`. VERIFIED.
- `lifecycle/activation_smoke.py:577-609` `observe(subject_gid, to_section, from_section)`:
  returns `None` unless the move crosses **into** the activating set; **:598-599** an
  already-activating `from_bucket` returns `None` (within-bucket moves are not activations).
  `:608` stamps `observed_at=self._clock()` — **the dated asset** (`:16-19`: *"THE INSTANT
  THIS HOOK RECORDS IS THE ASSET"*). VERIFIED.
- `guard(...)` at `:668-...` is the two-sided gate; `run(...)` at `:613-623` produces the
  report without the permit semantics.

**Design consequence:** the observer is a *differ*, and `observe()` is a *classifier* —
`observe()` needs `from_section`, which only the prior-state store can supply. This is
precisely why S-1 is not optional plumbing: without it the hook can never be given a
`from_section`, and every read looks like a cold start.

### 2.4 The N=3-of-each-kind counter and the flip

R-133 (`.ledge/decisions/RATIFICATION-decision-space-sitting-VIII-2026-09-10.md:54`):
*"N = 3 verdicts of each kind before the dry-run flips to enforce"*, confirming R-130 (`:24`).
VERIFIED (working-tree read; this file IS tracked at R-ASANA).

| # | where the counter lives | disposition |
|---|---|---|
| **C-1** | **In the same S3 state object** as the membership snapshot — one JSON document, one writer, one version history | **★ REC.** Survives cold start; human-readable before the flip; versioned, so the tally's own history is auditable |
| **C-2** | A CloudWatch metric dimensioned by `kind` | **REJECT as the flip predicate** (metrics age out; and dimensioning a live metric blinds the alarm written against its undimensioned form — a scar this fleet already owns). **KEEP as the visibility surface**, alongside C-1 |
| **C-3** | Derived at read time from Logs Insights | **REJECT.** Makes the flip predicate depend on log retention and on a query grant the observer otherwise does not need |

**The flip itself must not be automatic.** R-133 sets a *precondition* for a flip; it does
not authorize code to flip itself. REC: the counter emits `activation_observer_flip_ready`
when all kinds reach 3 and **stops there**; the flip is an operator word. Rationale in §3.4.

### 2.5 The facts provider — and what the observer can prove BEFORE the office join exists

**The honest finding, stated first:** an exhaustive grep of `src/**.py` at R-ASANA for
`office_name` returns **exactly one file** — `lifecycle/activation_smoke.py:804-818`, the
probe that **consumes** it. **There is no producer of `office_name` in this repo.** VERIFIED.

The ADR-ws-join recommendation (Option C, working-tree artifact §7.1/§7.3) lands the
resolver in the **`autom8y` repo root `scripts/`**, beside `ebi_witness_ledger.py` —
deliberately *not* in asana `src/`. So the join will not become importable here by default.

What `default_pipe_checks()` (`activation_smoke.py:879-906`) asks for, and what a v1
observer can supply today:

| check | probe | fact it needs | can v1 supply it? |
|---|---|---|---|
| `subject_identified` | `:798-801` | `transition.subject_gid` | **YES** — the crossing itself carries it |
| `office_named` | `:804-818` | `facts["office_name"]` | **NO** — no producer exists (above). Fails `office_unresolved` |
| `failure_path_names_office` | `:821-849` | `facts["failure_probe"] = {office_name, kind}` | **NO** — same root. Fails `failure_probe_absent` |
| `pipe_proof_fresh` | `:852-876` | `facts["pipe_proof_at"]` (tz-aware, `≤ 1h` old) | **NO** — nothing mints a pipe proof. Fails `pipe_proof_absent` |

**Therefore: with `default_pipe_checks()`, `guard()` refuses 100% of activations today**,
with `refused_check="office_named"`. That is the hook behaving exactly as designed — and it
is also why **WS-2 v1 must not call `guard()` for a permit decision**.

**What v1 CAN prove, honestly:**
1. That a named offer GID crossed INTO the activating bucket **at a recorded instant** —
   the one dated placement-transition fact either lane holds (`activation_smoke.py:16-19`).
2. That a within-bucket move (`ACTIVATING`→`IMPLEMENTING`) was **correctly not** emitted —
   the negative pole, mechanical at `:598-599`.
3. That the three office-dependent checks **fail with named kinds** — the built-unconsumed
   debt rendered VISIBLE per-crossing instead of hidden. A report where the office checks
   are *absent* is indistinguishable from one where they passed; `_run_one` (`:625-664`)
   was written for exactly that distinction.

REC shape for v1: call `observe()` then `run(transition, facts={})` and **log the
`SmokeReport`**; do not call `guard()`. Note the smoke refuses an empty check set
(`DECISION_KIND_NO_CHECKS`, `:73-76`) — narrowing to `checks=()` is not a legal escape, and
narrowing to `(subject_identified,)` would *hide* the office debt. Keep all four; report all four.

---

## §3 Q3 — ENFORCEMENT ROUTING (the K-slate)

### 3.1 The options

| # | option | what it actually costs, given §1.4 | disposition |
|---|---|---|---|
| **K2** | Route the executor through the HTTP write path | The route is `POST /tasks/{gid}/section` gated by **`WriteClass.TASKS`** (`tasks.py:648`), **not `INTAKE`**. The observer's principal would have to appear in `ASANA_WRITERS_TASKS_WRITE` (`write_authz.py:136`) — which grants it **all ten** `TASKS` routes (`tasks.py:197..801`): create, update, delete, complete, assignee, dependencies. **A section-move grant becomes a blanket task-write grant.** Transport itself is constructible: `auth/service_token.py:19` `ServiceTokenAuthProvider` (client_credentials) is already used by three Lambdas (`scheduling_stratum_snapshot.py:1110`, `enrollment_intent_bridge.py:678`, `workflow_handler.py:186`) | **Good transport, wrong grant** |
| **K3** | Mint `WriteClass.ACTIVATION` | One enum member (`write_authz.py:100-108`), one `ALLOWLIST_ENV` row (`:135-142`), one route. Separately grantable, separately revocable, separately auditable — the allowlist env var names the class in every deny log (`:360`) | **★ REC** |
| **K1** | Move the check into the service layer | Closes the class, not the instance — but `authorize_write(write_class, claims, request, ...)` (`:312-318`) is built on a `Request` and issuer-asserted claims (`resolve_principal`, `:204-256`). A Lambda has neither. Service-layer enforcement therefore requires **inventing a non-HTTP principal carrier** — a new identity surface, which sits against the charter's never-grantable identity-mint floor | **REJECT for now; record as design debt.** The right K1 is a *later* consequence of K3, not its alternative |
| **K4** | Leave the bypass, gate at the observer | An advisory gate in front of an ungated enforcement point is a declared instrument with no enforcement on the thing it protects | **REJECT** (F8's own reasoning, upheld) |

### 3.2 Recommendation

**K3, carried on K2's transport.** One sentence: *the observer, if it ever enforces, calls
the HTTP write plane (so the single enforcement point stays the route dependency — no new
enforcement surface, the `test_write_authz_coverage.py` guard keeps covering it), through a
NEW route gated by a NEW `WriteClass.ACTIVATION`, so the grant is scoped to the activation
move and never widens to the whole `TASKS` class.*

If only one may be taken: **K3**. K2 alone buys enforcement at the price of an over-grant
that is invisible in the allowlist (the env var would say `TASKS_WRITE` while the intent
says "move one offer's unit into Onboarding").

### 3.3 The never-grantable floor, stated plainly

An Asana section move is **not** a business-of-record identity mint: `task_service.py:481`
calls `move_to_section_async` on an **existing** task GID; no identity is created, no
external record is minted. So it is grantable in principle.

But it **is** customer-visible — the move lands on a board the client sees — which is
adjacent to the floor's customer-visible-outbound limb. Two consequences: (a) WS-2 v1 is
observe-only, which sidesteps the question entirely; (b) the enforce flip, when proposed,
is an **operator word in the operator's own room**, not a consequence of the N=3 counter
reaching 3 (§2.4).

### 3.4 Risk-map carriers (confirming §6 of sitting X, re-derived)

- **#16 — a live write path around the authz gate.** CONFIRMED as a *construction*
  (§1.2-1.3), **downgraded in liveness** (no caller, §1.5) and **widened in scope**
  (at least two such paths, §1.6). Recommend re-wording the carrier to *"a CLASS of
  in-process Asana write paths that the route-level gate cannot reach by construction —
  `reconciliation/executor.py:159` (uncalled) and `persistence/healing.py:351` (opt-in);
  the class, not the instance, is the carrier."*
- **#15 — terraform declaring a Lambda whose handler never existed** (`module
  "unit_reconciliation"`, R-A8 `main.tf:1904`, `handler_command` `:1930`,
  `schedule_enabled = false` `:1921`). Re-derived at R-A8: the module block is present as
  described. INHERITED for the never-existed-in-history half (not re-run tonight).

---

## §4 Q4 — THE SMALLEST WS-2 BUILD, AND A DATED CONSUMER COMMITMENT

### 4.1 Scope of the smallest honest build (observer in dry-run only; **no enforcement**)

1. `src/autom8_asana/lifecycle/activation_observer.py` — read membership (R-B), load prior
   state (S-1), diff, `offer_grain_hook().observe(...)` per changed offer, `run(...)` with
   empty facts, log the report two-sidedly, write new state + tallies.
2. The S3 state object: one key in `autom8-s3`, one document `{schema_version, read_at,
   frame_etag, membership:{offer_gid: section}, tallies:{kind: n}}`.
3. A `service-lambda-scheduled` module + three IAM statements in R-A8
   `terraform/services/asana/`, copied from `traffic_offer_divergence_lambda.tf:217-263`
   (including the `s3:ListBucket` 403-vs-404 guard — its absence is a *silent* defect).
4. Tests, two-sided and day-one-broken:
   - a crossing that MUST be emitted (INACTIVE→`ACTIVATING`);
   - a within-bucket move that MUST NOT be (`ACTIVATING`→`IMPLEMENTING`);
   - **the cold-start case**: first run, no prior state → **seed and emit zero**, loudly.
     (Emitting every currently-activating offer as a "crossing" on day one is this
     instrument's vacuous-pass failure mode, and it looks like success.);
   - stale/unreadable input → **refuse**, never a fabricated empty diff.
5. No `guard()` permit path, no write class, no Asana write, no `dry_run=False` anywhere.

**Explicitly out of scope for v1:** the office join, the facts provider, enforcement,
`WriteClass.ACTIVATION`, and the flip.

### 4.2 Seats and days

| leg | seat | estimate |
|---|---|---|
| Observer + store + tests | one build seat (seam/principal) | **~2 days** |
| Terraform module + IAM (plan-only) | same seat or a platform seat | **~0.5 day** of work |
| Rite-disjoint critic (two-sided teeth, cold-start fixture) | a disjoint seat | **~0.5 day** |
| **Total** | | **~3 seat-days** |

### 4.3 The two things days cannot buy — operator words

1. **Scheduling anything in this stack.** All ten scheduled modules in the asana stack carry
   a literal `schedule_enabled = false` (R-A8 `main.tf:501,723,899,1921,2152,2250,2373,2464`,
   `substrate_prov_sweep.tf:86`, `traffic_offer_divergence_lambda.tf:141`) while
   `var.schedules_enabled` **defaults `true`** (`variables.tf:209-213`) — the pause is a
   per-module literal, written to be durable against a bare apply (`main.tf:715-722`, and
   *"RELEASED BY: the enable act that re-opens this job... Never by a date."*). A new
   observer that schedules itself is a **new exception to a standing decommission**, not a
   default. VERIFIED.
2. **The apply path.** `environments/production.tfvars:265` pins `image_tag = "5047cc6"`
   (VERIFIED, R-A8). The asana stack's apply path for its re-pin is a sitting-X §2 deferred
   item carrying **NO WATCHER**. No manual Service Terraform apply on a pinned stack.

### 4.4 Proposed exit receipt for the WS-2 build charge (five items, dated, two-sided)

| # | receipt | why it is not satisfiable by a green test |
|---|---|---|
| **(i)** | One dated `ActivationTransition` for a **real** offer GID, in the log plane, stamped `referent_name=offers-1143843662099250`, at a named instant | The instant is the asset; a fixture cannot produce a real one |
| **(ii)** | The **negative control from the same run**: a within-bucket move present in the input rows and **absent** from the emitted crossings, cited by row | Proves the differ discriminates, not merely that it fires |
| **(iii)** | The `SmokeReport` for (i) showing `office_named`, `failure_path_names_office`, `pipe_proof_fresh` **failed with their named kinds** | Renders the office debt visible; a report missing these is indistinguishable from one where they passed |
| **(iv)** | The **cold-start run** emitting **zero** crossings with its own log line | The single most likely way this instrument fakes success |
| **(v)** | Two successive **versions** of the state object at the named S3 key (versioning already on, `s3.tf:21`) | Proves prior state actually persisted across invocations |

### 4.5 The dated consumer commitment (the price of J3)

F8's J3 REC is explicitly conditioned: *"the recon charge must carry a **dated consumer
commitment**, not an open defer."* Paying it:

> **PROPOSED (operator rules):** the WS-2 build charge is cut **at the READ epoch's wave-2
> sitting**. If it has not been cut by **2026-10-05**, `#439` / `#441` are re-classified
> from *built-unconsumed-by-design* to **DEBT**, and the epoch's own Law-2 refusal
> ("every new instrument states its consumer before it is built") fires **on the epoch
> itself** — recorded in the next sitting's record, with no watcher needed because the date
> is the watcher.

The modules are already landed: `7ea3e055` (#439) and `088a5f48` (#441) are on R-ASANA, and
**zero production callers** import them — grep of `src/**.py` for
`activation_smoke|activation_referent|offer_grain_hook|ActivationSmokeHook` returns only
the two modules themselves plus `tests/unit/lifecycle/test_activation_{smoke,referent}.py`.
VERIFIED. The clock on the debt started when they merged, not when WS-2 is charged.

---

## §5 WHAT THIS RECON DID NOT DO

| item | class |
|---|---|
| Any AWS call (no `s3 head-object`, no `logs`, no `lambda get-function-configuration`) | **NOT TAKEN** — read-only charge |
| The Offer frame's actual staleness | **UV-P** (§2.1) |
| Re-derivation of "`unit_reconciliation.py` never existed in history" | **INHERITED** (sitting X §6); the module block itself re-derived at R-A8 |
| Whether a human reads `platform_alerts` in business hours | **NOT TAKEN** — the charge's own standing assumption, operator's to confirm |
| `processor.py`'s third-site Engaged/Scheduled disagreement (`:67-74`, re-read this session) | **VERIFIED-PRESENT**, not adjudicated here — it is the UNIT vocabulary, and WS-2 does not consume it |
| Reading `.terraform/` or any other worktree | **REFUSED** by fence |

## §6 EVIDENCE GRADE

**MODERATE**, self-capped. Single agent, no rite-disjoint corroboration. Every code claim
is anchored at R-ASANA or R-A8 with file:line and was read first-hand this session; the
remainder is labelled INHERITED, UV-P, or NOT TAKEN. The three findings most worth an
independent re-derivation by the critic are **§1.4** (the gated class is `TASKS`, not
`INTAKE` — it changes K2's price), **§2.5** (`office_name` has no producer in this repo —
it changes what a v1 observer can honestly claim), and **§1.6** (the bypass is a class with
at least two members — it changes what "fixing it" means).
