---
type: review
status: draft
artifact_id: CRITIQUE-s3-delivery-rails-2026-08-12
initiative: asana-native-insight-delivery
sprint: S3-critique
rite: arch
critic_of: RAILS-insight-delivery-verified-2026-08-12
date: 2026-08-12
verdict: PASS-WITH-CONDITIONS
critic_seat: structure-evaluator (arch) — rite-disjoint from the authoring architect (10x-dev)
read_surface_discipline: >-
  autom8y read EXCLUSIVELY via `git show origin/main:<path>` (SVR-S3-11 hazard
  re-confirmed live: worktree report.py = 182 lines, origin/main = 510).
  autom8y-asana read from the working tree ONLY after proving it byte-identical
  to origin/main for src/ and mcp/ (`git diff --stat origin/main -- src/ mcp/`
  → empty; HEAD == origin/main == 4129ae7e).
live_world_discipline: >-
  Zero writes of any class. No Asana call, no Slack post, no Lambda invoke, no
  AWS mutation, no terraform action, no git mutation. Every probe is a file
  read, a grep, or a read-only git plumbing command.
---

# CRITIQUE — S3 delivery-rail inventory, adversarially tested

## 1. VERDICT

**PASS-WITH-CONDITIONS.**

The artifact's method (§2 four-test AVAILABLE bar), its fence discipline (§1, §4),
its 50-block analysis (§6), its 404 re-derivation (§6.2 item 5), and every
receipt I re-ran on the Slack rail reproduce **exactly** at the read surface of
record — but its own headline falsification claim is wrong in the same direction
it was written to correct: **R-04 "independently UNBUILT" is REFUTED** — Asana
comment-CREATE is built, mounted and reachable at `POST /v1/receipts` — so the
count in §3.1 is **three of three** write classes built, not two of three, and
the declared Asana-write surface is **26 endpoints across 8 route modules**, of
which S3 named two.

I attempted to break the artifact on eight fronts. It held on five. The three it
did not hold on are conditions, not a BLOCK, because **every failure moves in the
safe direction**: the CR-1 fence turns out to be *more* load-bearing than S3
said, never less. No rail S3 graded NOT AVAILABLE or RESERVED becomes available
under my findings, and no disposition in §9 flips.

---

## 2. The R-05/R-06 security adjudication

S3 says task-CREATE is "BUILT and reachable" with "Auth: `AsanaClientDualMode`",
and entity-field write is "BUILT", "gated `Depends(require_service_claims)`
(S2S-only)". Both are true. Both are **under-called**. Here is the chain S3 did
not walk.

### 2.1 The decorator is not the gate — `pat_router` performs no runtime auth

`tasks.py:64` builds the router via `pat_router(prefix="/api/v1/tasks", ...)`.
That factory is documented as metadata-only:

> `src/autom8_asana/api/routes/_security.py:9-12` — *"The `auto_error=False`
> setting ensures SecureRouters only inject OpenAPI metadata without performing
> runtime auth checks -- runtime auth is handled by the existing auth
> dependencies (`get_current_user`, `verify_service_jwt`)."*

So the security scheme on R-05 is an OpenAPI annotation. The runtime gate is
whatever the handler's dependencies enforce.

### 2.2 R-05's real gate: possession of *any* Asana PAT — the service validates nothing

`create_task` (`tasks.py:197-199`) depends on `AsanaClientDualMode`
(`dependencies.py:385`) → `get_asana_client_from_context` → `get_auth_context`
(`dependencies.py:109`). That function branches on `detect_token_type`
(`auth/dual_mode.py:55-58`), which **counts dots**: 2 dots → JWT, otherwise PAT.

On the PAT limb (`dependencies.py:140-149`):

```
    if auth_mode == AuthMode.PAT:
        # PAT pass-through: user's token goes directly to Asana
        ...
        return AuthContext(mode=auth_mode, asana_pat=token)
```

The only checks applied to a PAT are structural, at `_extract_bearer_token`
(`dependencies.py:88-107`): header present, `Bearer ` prefix, non-empty,
`len(token) >= 10`. **The service does not validate the PAT at all** — it
forwards it to Asana, which enforces.

**Adjudication (a):** in PAT mode, R-05 confers *no privilege the caller did not
already hold*. Anyone with a workspace-write PAT could create the same task via
Asana's own API. The route is a proxy. Exposure here is **not material** — and I
tried to make it material and failed.

### 2.3 R-05 and R-06's real gate: a fleet service JWT lends the caller the **bot PAT**

The JWT limb is the material one. `get_auth_context` validates the token and then
substitutes a service-held credential. `auth/bot_pat.py:56-58` states the
consequence in its own words:

> *"The bot PAT is used for S2S requests when the incoming auth is a JWT. It's
> the single credential that autom8_asana uses to call the Asana API **on behalf
> of all S2S callers**."*

`entity_write.py:271` then does exactly that: `async with
AsanaClient(token=auth_context.asana_pat) as client:`.

**So a caller holding a service JWT needs no Asana credential whatsoever.** It
borrows the bot's board privileges. That is the real exposure, and it is not what
"dual-mode auth" or "S2S-gated" conveys.

### 2.4 The sharp finding: `require_service_claims` is **authentication-only**. There is zero authorization.

`require_service_claims` (`internal.py:83-161`) rejects PATs
(`SERVICE_TOKEN_REQUIRED`, `:114-118`), validates the JWT via
`validate_service_token`, and returns `ServiceClaims(sub, service_name, scope,
permissions)` (`:155-160`). Validation enforces signature/expiry/issuer plus a
fleet audience (`jwt_validator.py:83`, `audience="https://api.autom8y.io"`).

It performs **no permission check, no scope check, and no per-service allowlist.**

And the route does not add one. In `entity_write.py`, the `claims` object is
referenced at exactly two sites — `:231` and `:362` — and **both are logging**
(`"caller_service": claims.service_name`). I grepped the whole file for
`permission`/`scope`/`claims.`; those two log lines are the entire usage.

This is not a general fleet limitation. The codebase **has** fine-grained
authorization and uses it one file away:

> `src/autom8_asana/api/routes/admin.py:456` —
> `if SUPER_ADMIN_PERMISSION not in claims.permissions:`

`ServiceClaims.permissions` is documented as existing precisely for this
(`internal.py:40-43`: *"Used for fine-grained authorization on privileged routes
(e.g., super-admin gating on `/v1/admin/cache/refresh` per Bedrock W4C-P3 /
SEC-DT-10)"*). A cache-refresh is permission-gated. **An Asana board write is
not.**

### 2.5 Plain statement of exposure

> **R-06 (and every other S2S write route) is reachable by *any* holder of a
> valid, unexpired fleet service JWT bearing audience `https://api.autom8y.io`.
> Not "the entity-writer service" — any fleet service account. The route then
> executes the write with the bot PAT's board privileges. The gate is
> fleet-membership, not authorization.**
>
> **R-05 in JWT mode is identical. R-05 in PAT mode is a proxy that adds no
> privilege.**

Two mitigating facts I checked and will not suppress: the entity and receipts
routers carry `include_in_schema=False` (`entity_write.py:54`,
`receipts.py:82`), so they are absent from the published OpenAPI document — but
this is discoverability, not access control; the routes are mounted
(`main.py:487`, `:491`) and route normally. And I could **not** establish network
reachability (see §6, UV-P-C-2) — `terraform/services/asana/` in this repo
contains only alarm definitions.

### 2.6 Could an agent seat in this fleet reach either endpoint without an operator?

**I could not establish that it could, and I am not going to assert it.** What I
can state with receipts: the *code-side* barrier for R-06 is a fleet service JWT
and nothing more (§2.4). Whether an agent seat can obtain such a JWT by following
documented patterns is a fact about credential distribution, not about this
repo's code, and I did not probe it — doing so would have meant touching live
credentials. Carried as **UV-P-C-1**.

**Net effect on S3's §3.1 argument: it is CORRECT and STRENGTHENED.** S3 wrote
§3.1 to stop a later seat concluding the fence is redundant. My finding makes the
fence *more* load-bearing than S3 claimed: the write classes are not merely built
but sit behind a coarse authentication-only gate, and there are 26 of them.

---

## 3. Tilt audit of §7 — is the two-sided presentation neutral?

I read the operator ruling first (`RULING-operator-gate-b-modal-2026-08-12.md`),
which binds S3 at `:95`: *"It DOES bind S3, whose subject is the rails: S3 must
present both readings and must not assume either."*

**Verdict: structurally neutral, with one asymmetry of *emphasis* and one
material *omission of adverse evidence*.**

### 3.1 What is genuinely, mechanically neutral (and I tried hard to break this)

- **Symmetric table construction.** §7.1 and §7.2 both use in-favour/against
  tables. §7.1 carries 4 rows/4 counters; §7.2 carries 3 rows/3 counters.
- **S3 argues against its own interest, explicitly.** The single most
  self-damaging line in the artifact is in reading (a)'s *against* column:
  *"Practically: it is the only reading under which this initiative has an
  autonomous delivery rail at all"* → *"**That consequence is a cost, not an
  argument. It must not be smuggled in as a reason**"* (`:327`). That is the
  exact tilt vector a partisan author would have exploited, pre-emptively
  disarmed by the author.
- **Reading (a)'s load-bearing premise is flagged as unverified by the author
  himself** (`:325`, UV-P-S3-1) — again, damage to the reading that benefits the
  sprint.
- **§7.5 is a genuine neutrality device**: five things true under both readings,
  which is what lets the sprint complete without the ruling.

I attempted to show that §7.1 receives more favourable detail than §7.2 and
**failed**: the extra row in §7.1 is offset by the fact that two of §7.1's four
counters are ⚠-marked (the artifact's own severity glyph) while only one of
§7.2's is not.

### 3.2 The emphasis asymmetry — §7.3 and §7.4 both cut one way

Both "newly surfaced consequences" are costs assessed **against reading (b)**,
and none against reading (a):

- §7.3 retroactivity: *"A reading that retroactively re-classifies a running
  system is a heavier ruling than it looks"* — filed in §7.2's **against**
  column (`:338`).
- §7.4 rung-2: *"it may make a named success rung structurally unreachable"* —
  also §7.2's **against** column (`:339`).

So the two novel contributions of the section are both anti-(b). S3 mitigates
this honestly — §7.3 splits into (b-i)/(b-ii) and says *"this artifact picks
neither"*; §7.4 gives narrow and broad reads and says *"Not decided here."* The
sub-splits are real neutrality work, not decoration.

**But the closing sentence of §7.4 does editorialise**: *"it means reading (b) is
not merely a friction cost — under the broad read it changes what success can
even mean. **The operator should see that before ruling.**"* No equivalent
"the operator should see this" sentence attaches to any cost of reading (a).

**Grade: MILD TILT toward reading (a), by asymmetric novelty rather than by
argument.** Below the threshold that would make me call the presentation
non-compliant with the ruling — S3 met the letter and most of the spirit — but a
PT-02 briefing that inherits §7 verbatim will inherit that lean. **Condition C-4
below.**

### 3.3 The material omission — in-repo evidence adverse to reading (a) that S3 read past

Reading (a) rests on the channel being *"opted-in, internally-controlled"*
(`:320`, `:325`), with S3 correctly conceding it cannot probe membership
(UV-P-S3-1). Fair. **But there is in-repo evidence bearing on that premise, in a
file S3 demonstrably read, and it is not surfaced anywhere in the artifact:**

> `services/account-status-recon/src/account_status_recon/orchestrator.py:1225-1227`
> (autom8y @ origin/main) — *"the wire-call to `send_blocks` is suppressed so an
> un-ratified shadow baseline cannot post to the **customer-facing channel**."*

The only channel `_safe_slack_post` ever posts to is `settings.slack_channel` =
`#account-health`. The deployed service's own source calls it *the
customer-facing channel*.

**I will not overclaim this, and the honest reading is genuinely ambiguous.** In
ASR's own vocabulary "customer" may mean the internal business stakeholder: the
same feature record says *"The business stakeholders who act on anomalies are
not engineers; they read Slack"* and calls the feature *"the **only user-facing
surface** of the service"*
(`services/account-status-recon/.know/feat/slack-report-delivery.md:30,32`). On
that reading "customer-facing" means "the live audience channel", not
"client-reachable".

The defect is **not** that S3 got the answer wrong. It is that **DEFER-WATCH-2**
— *"any rail proposal whose surface a client could reach → HALT and ESCALATE"* —
is dispositioned in §9 as **"NOT TRIGGERED by any rail this artifact names as
available"**, while the read surface S3 probed contains a string that describes
the one rail it *does* name as available as customer-facing. Whatever it means,
it is a signal on the exact predicate DEFER-WATCH-2 keys on, and it belonged in
§7.1's *against* column beside UV-P-S3-1.

S3 was reading in this precise region — it cites `orchestrator.py:1178-1187`,
`:1248`, `:1330-1359`. Line 1227 sits between them.

**Materiality: MEDIUM-HIGH.** It does not flip DEFER-WATCH-2 (which S3 correctly
keeps **STANDING**), and it does not decide §7. It does mean the operator's
two-sided briefing is missing a piece of in-repo evidence that cuts against the
reading the artifact mildly leans toward. **Condition C-3.**

---

## 4. Findings

Format: claim as written → what I did → receipt → disposition → materiality.

### F-1 — R-04 "independently UNBUILT" — **REFUTED**

**Claim** (`:98`): *"**R-04** Asana comment-CREATE | RESERVED (CR-1) — and
independently UNBUILT | `grep -rn "create_comment" src/autom8_asana/api/ mcp/` →
zero matches (exit 1). `create_comment_async` exists **only** at
`clients/stories.py:249`. **No HTTP route, no MCP tool.**"*

**What I did**: reproduced S3's grep verbatim, then — suspecting the probe was
scoped to the wrong layer — enumerated every route module declaring an Asana side
effect and walked the call chain of the one whose target names a comment.

**Receipts** (autom8y-asana, working tree proven == origin/main):

| step | receipt |
|---|---|
| S3's grep is accurate | `grep -rn "create_comment" src/autom8_asana/api/ mcp/` → no output, exit 1. **Reproduced exactly.** |
| but the write is declared | `src/autom8_asana/api/routes/receipts.py:89-91` — `"x-fleet-side-effects": [{"type": "asana_api", "target": "business_task_comment"}]` |
| the route exists | `receipts.py:85-86` — `@router.post("/receipts", ...)` on `s2s_router(prefix="/v1")` (`:82`) → **`POST /v1/receipts`** |
| it is mounted | `src/autom8_asana/api/main.py:491` — `RouterMount(router=receipts_router)`; exported at `routes/__init__.py:48` |
| it calls the service | `receipts.py:164` `ReceiptsService(`, `:169` `await service.thread_receipt(` |
| the service creates the comment | `src/autom8_asana/services/receipts_service.py:346` — `story = await self._client.stories.create_comment_async(task=business_gid, text=text)` |
| the module says so in line 1 | `receipts.py:3-4` — *"POST /v1/receipts - thread an internal forwarding-lifecycle receipt onto the clinic's Business task **as an Asana comment**."* |

**Disposition: REFUTED.** Comment-CREATE is **built, mounted, and reachable at
the HTTP API**, S2S-gated exactly as R-06 is. The grep was a *true receipt
supporting a false inference*: the literal token `create_comment` does not appear
under `api/` because the route reaches the verb through `services/`. This is
structurally the **identical** error class S3 caught in the inherited SVR-5
("checked only `create_comment`") — an under-scoped symbol probe generalised into
a claim about a whole class.

**Materiality: HIGH.** It falsifies the artifact's own headline falsification.

### F-2 — §3.1 "two of three write classes" — **REFUTED (it is three of three)**

**Claim** (`:120`, `:126-127`): *"Task-CREATE (R-05) and entity-field write
(R-06) are BUILT and reachable at the HTTP API"* … *"for **two of three
classes**, the fence is the only thing standing between this initiative and an
Asana write."*

**What I did**: applied F-1.

**Receipt**: `receipts.py:89-91` + `receipts_service.py:346` (above).

**Disposition: REFUTED.** All **three** CR-1-enumerated write classes — comment,
task, custom-field — are built and reachable. The correct sentence is *"for all
three classes, the fence is the only thing standing between this initiative and
an Asana write."*

**Materiality: HIGH — and it strengthens S3's own argument.** The whole point of
§3.1 is that a later seat must not read "unbuilt" and conclude the fence is
redundant. R-04 is the one row still carrying the word **UNBUILT** in the
inventory, and it is the row most likely to be inherited as a licence.

### F-3 — the declared Asana-write surface is **26 endpoints, not 2** — **REFINED**

**Claim** (§3, §4.2): the inventory names two built write routes; §4.2 lists the
classes CR-1 did not enumerate as *"external attachments, adding a follower,
project status updates."*

**What I did**: enumerated every occurrence of the codebase's own machine-readable
side-effect marker `{"type": "asana_api", ...}` across `src/autom8_asana/api/routes/`
and resolved each to its decorator, path and handler.

**Receipt** — 26 endpoints across 8 modules, all mounted at `main.py:456-492`:

| module | n | endpoints |
|---|---|---|
| `tasks.py` | 10 | `:182` POST `""` create · `:244` PUT `/{gid}` update · `:308` DELETE `/{gid}` · `:472` POST `/duplicate` · `:527` POST `/tags` · `:577` DELETE `/tags/{tag_gid}` · `:629` POST `/section` · `:682` PUT `/assignee` · `:730` POST `/projects` · `:779` DELETE `/projects/{project_gid}` |
| `projects.py` | 5 | `:212` POST `""` · `:262` PUT `/{gid}` · `:325` DELETE `/{gid}` · `:454` POST `/{gid}/members` · `:500` DELETE `/{gid}/members` |
| `sections.py` | 5 | `:88` POST `""` · `:138` PUT `/{gid}` · `:188` DELETE `/{gid}` · `:238` POST `/{gid}/tasks` · `:290` POST `/{gid}/reorder` |
| `intake_create.py` | 2 | `:61` POST `/business` (target `business_task`) · `:198` POST `/route` (target `process_task`) |
| `entity_write.py` | 1 | `:184` PATCH `/{entity_type}/{gid}` — **the R-06 row** |
| `intake_custom_fields.py` | 1 | `:46` POST `/{task_gid}/custom-fields` (target `task_custom_fields`) |
| `receipts.py` | 1 | `:85` POST `/receipts` (target `business_task_comment`) — **F-1** |
| `workflows.py` | 1 | `:250` POST `/{workflow_id}/invoke` (target `task`) |

**Disposition: REFINED.** S3's §4.2 conclusion — *"the boundary is READ-ONLY, not
the enumeration"* — is **correct and I endorse it**; the three grounds it gives
hold. But §4.2's *illustrative list* is materially incomplete and, worse, points
outward (attachments, followers, status updates — mostly unbuilt) while the large
built surface sits inside the same route tree. A second S2S custom-field writer
(`intake_custom_fields.py:46`) is a same-class sibling of R-06 and is unnamed.

**Materiality: MEDIUM-HIGH.** Does not change any verdict — §4.2's categorical
ground catches all 26 — but the enumeration a later seat reads is off by an order
of magnitude in the direction of under-stating the fence's reach.

### F-4 — "S2S-gated" / "dual-mode auth" — **REFINED (under-called)**

**Claim** (`:99`, `:100`): *"Auth: `AsanaClientDualMode`"*; *"gated
`Depends(require_service_claims)` (S2S-only)"*.

**What I did**: walked `pat_router` → `get_auth_context` → `detect_token_type` →
bot-PAT substitution; audited `require_service_claims` for authorization;
contrasted with `admin.py`.

**Receipts**: `_security.py:9-12` (metadata-only); `dual_mode.py:55-58`
(dot-count); `dependencies.py:140-149` (PAT pass-through);
`bot_pat.py:56-58` (*"on behalf of all S2S callers"*); `entity_write.py:271`
(bot PAT used for the write); `internal.py:155-160` (claims returned, unchecked);
`entity_write.py:231,362` (claims used **only** for logging);
`admin.py:456` (`if SUPER_ADMIN_PERMISSION not in claims.permissions:`).

**Disposition: REFINED.** Both statements are true and both understate. "S2S-only"
reads as *a named peer service*; the mechanism is *any fleet JWT, no
authorization*. See §2.5.

**Materiality: HIGH (security posture).** This is the finding a security seat
should receive as a cross-rite observation.

### F-5 — R-08 receipts — **CONFIRMED, every one**

**Claim** (`:102`): channel default, terraform wiring, cadence, three post sites,
`dry_run` default False.

**What I did**: re-read each at `git show origin/main:` in the monorepo.

| S3 citation | my result |
|---|---|
| `config.py:177-180` default `#account-health` | **CONFIRMED** — `slack_channel: str = Field(default="#account-health", ...)` at `:177-180` |
| `main.tf:135` `SLACK_CHANNEL = var.slack_channel` | **CONFIRMED** at `:135` |
| `main.tf:108` `cron(0 */4 * * ? *)` | **CONFIRMED** at `:108`, comment *"Schedule: every 4 hours (per PRD NFR-4)"* at `:107` |
| `orchestrator.py:160/162, 223/225, 501/503` post sites | **CONFIRMED** — `slack_post_attempt` at `:154`/`:217`/`:495`, `_safe_slack_post` at `:160`/`:223`/`:501` |
| `dry_run` default False | **CONFIRMED** — and see F-8: now proven live, not merely by default |
| team-facing per `.know/feat/slack-report-delivery.md:30` | **CONFIRMED** verbatim |

**Disposition: CONFIRMED.** **Materiality: n/a — this is the load-bearing row and
it holds under adversarial re-probe.**

### F-6 — the 404 drill-out — **CONFIRMED, and the routing to S5 is right**

**Claim** (`:291-298`, SVR-S3-12): bare `latest.json` at `report.py:81,167,193`
vs `f"{prefix}/{_LATEST_KEY}"` at `verdict_store.py:28,43-45`.

**What I did**: re-derived independently at `origin/main` — the **only** surface
on which this is checkable (see F-7).

**Receipts**:
- `git show origin/main:…/report.py | grep -n "latest.json"` → **`81`, `167`,
  `193`**. Exactly the three lines S3 cites, in three distinct
  reader-facing strings (`_BODY_CAP_NOTE`, the ghost-campaign clause, the
  stale/not-evaluable advisory).
- `git show origin/main:…/verdict_store.py` → `:28` `_LATEST_KEY = "latest.json"`;
  `:43` `def latest_pointer_key(prefix: str) -> str:`; `:45` `return
  f"{prefix}/{_LATEST_KEY}"`. Exactly as cited.

**Disposition: CONFIRMED.** The mismatch is real: the renderer emits a bare
filename at three reader-facing sites while the object is written prefix-qualified.

**Is the routing to S5 right?** **Yes, and I tested the opposite case.** The
defect lives entirely in `report.py`/`verdict_store.py` in the *autom8y* monorepo
— a different repo, a different service, and NF-1's declared owner. It touches no
rail verdict: R-08's availability does not depend on the pointer resolving, and
R-12 (the S3 verdict surface) is RESERVED under CR-2 regardless of whether its
URL is well-formed. The only place it *does* bear on S3's own output is the
constraint S3 already drew and did not absorb: a readout *"may not rely on
drill-out for completeness"* until S5 lands (`:295-298`). **That is the correct
disposition and I endorse it unchanged.**

**Materiality: n/a — correct as written.**

### F-7 — the monorepo trap — **CONFIRMED LIVE, and S3 navigated it correctly**

**Claim** (SVR-S3-11): the autom8y checkout is on an unrelated branch; everything
was read via `git show origin/main`.

**Receipts**: `git rev-parse --abbrev-ref HEAD` → `fix/wss-wildcard-scope-bypass-closure`;
`HEAD` = `cd24d61f`; `git merge-base --is-ancestor HEAD origin/main` → **NOT an
ancestor**. Working-tree `report.py` = **182 lines**; `origin/main` = **510
lines**.

**Disposition: CONFIRMED.** Note S3 recorded `origin/main` as `0e60e0f5`; it is
now `7bbb418e` — main advanced between S3's dispatch and mine. **Every S3
citation still resolves at today's `origin/main`**, so the drift is benign here,
but a stale SHA in an SVR tuple is a latent re-verification hazard. Minor.

**Materiality: LOW (drift note only).** S3 gets full credit: had it read the
working tree, its `report.py:193` citation would have pointed past EOF.

### F-8 — R-08's rung — **REFINED: UV-P-S3-4 is now DISCHARGED for delivery-mechanism**

Addressed in full at §5 below, including the parts of the gap that remain open.

### F-9 — R-02, R-01, §6 ceiling — **CONFIRMED (spot-checks)**

| claim | receipt | result |
|---|---|---|
| R-02 gated OFF | `mcp/asana_mcp/assembly.py:53-54` — *"EXPOSURE-GATED (W-5 / GATE-BW): register() self-gates on ASANA_MCP_ENABLE_WRITE_SURFACE (default OFF) — attaches nothing while off."* | **CONFIRMED verbatim** |
| R-01 iris unresolvable | `ls .claude/commands/iris.md` → *No such file or directory (os error 2)*; the only match in `.claude/commands/` is `iris-attestation.md` | **CONFIRMED**, including the near-miss |
| §6 silent truncation | `.know/feat/slack-report-delivery.md` — *"The 50-block truncation limit (FR-21) is enforced inside the SDK builder, not in service code. This means the service cannot observe the truncation event directly — the builder silently caps the output."* | **CONFIRMED, independently corroborated** |

---

## 5. UV-P-S3-4 and the tick census — adjudicated independently

The main thread supplied a read-only CloudWatch Logs Insights census
(`.sos/wip/EVIDENCE-tick-terminal-census-2026-08-12.md` — **artifact resolves**;
queryId `bf15fa66-2ea9-4622-ac30-b82fcb8e4dbc`, 35 rows, 7 invocations, window
2026-08-11T20:00Z→2026-08-12T20:36Z) showing every tick emitting `slack_post` and
`report_posted` with `channel: "#account-health"`, `block_count: 3`,
`abort_reason: readiness_gate_abort`. I was asked for independent judgment on
three points. I tested the evidence before accepting it.

### 5.1 Does `report_posted` actually prove delivery? — **Yes. I tried to break it three ways and could not.**

This mattered: the UV-P's own wording offers `slack_post_attempt` as an
acceptable method, and an *attempt* event would prove only egress intent.
`report_posted` is a different and much stronger event. At `origin/main`:

1. **It is inside the `try`, after the wire call returns.**
   `orchestrator.py:1248-1251` — `await slack_client.send_blocks(...)` then
   `log.info("report_posted", channel=channel, block_count=len(blocks), ...)`.
   On exception, control diverts to `slack_post_failed` (`:1268`) and
   `raise ReportError` (`:1294`). `report_posted` **cannot** fire on a failed post.
2. **`dry_run` returns before it.** `:1230-1245` logs
   `slack_post_suppressed_dry_run`, records a `SUPPRESSED` side-effect, and
   `return`s — never reaching `report_posted`. **So the census independently
   proves `dry_run` is False in the deployed configuration**, upgrading S3's
   config-default-plus-absent-tfvar *inference* to a live measurement. That is a
   second, unclaimed discharge.
3. **The SDK raises on Slack's `ok: false`.** This was my sharpest attack —
   Slack returns HTTP 200 with `{"ok": false}` for `channel_not_found`. It fails:
   `sdks/python/autom8y-slack/src/autom8y_slack/client.py:187` — `if not
   data.get("ok", False):` → raises `SlackChannelNotFoundError` (`:192`),
   `SlackRateLimitError` (`:200`), or `SlackAPIError` (`:206`). `send_blocks`
   (`:258`) routes through `_request` (`:135`).

**Conclusion: `report_posted` firing means Slack returned `ok: true` for
`chat.postMessage` to the channel named in the same log record.** That is
genuine observed delivery.

### 5.2 Does it discharge UV-P-S3-4? — **Yes, as written. But the coordinator's caution is right, and the residue needs a new name.**

UV-P-S3-4 asks: *"whether abort alerts are landing in `#account-health` right
now"*, METHOD *"one channel read, or CloudWatch `slack_post_attempt` /
`report_posted` event counts over 24h."* The census executed **precisely the
named method** over **precisely the named window** and answers **precisely the
named question**. Per SVR §1 RULE-1, the UV-P is consumed.

**UV-P-S3-4: DISCHARGED. R-08 rises from `VERIFIED-IN-CODE-AND-TERRAFORM` to
`VERIFIED-LIVE`.** This was the single highest-value zero-risk conversion
available on this sprint and it is correctly taken.

**But I will not let it cover more than it covers**, and the coordinator was
right to press: the census proves the **transport** works for a hand-built
3-block abort. It does not prove a *readout-shaped payload* posts successfully.
Those differ on the exact dimension §6 is about — the abort path **bypasses the
block-budget machinery entirely** (F-9, next). I open:

> **UV-P-C-3** — `[UV-P: whether a readout-class payload (SDK-built, multi-block,
> approaching the 50-block ceiling) posts successfully to #account-health |
> METHOD: first live readout post, observed via the same report_posted /
> block_count telemetry | REASON: the tick census proves the transport for a
> hand-built 3-block abort that bypasses report.py and the SDK budget machinery.
> Payload class differs from the class §6 constrains. Non-blocking: it cannot be
> closed before a readout exists, and closing it is SA-1's natural first receipt.]`

### 5.3 `block_count: 3` — **I do not accept the proposed use. It does not sharpen the budget arithmetic.**

The coordinator proposed this as *"a live measurement of framing overhead against
the 50-block ceiling"*. **It is not, and the codebase says so.**

- The 3 blocks are the abort's **entire** message, not framing around a body:
  `_build_readiness_abort_alert` (`orchestrator.py:1330-1359`) returns exactly
  `header` + `section` + `context`. `block_count: 3` matches — a clean
  corroboration that the census reads the readiness-abort path, consistent with
  `abort_reason: readiness_gate_abort`.
- **The abort path never touches the report builder.**
  `.know/feat/slack-report-delivery.md` states it outright: *"Abort-path alerts
  (`_build_all_failed_alert`, `_build_readiness_abort_alert`) are hand-built
  3-block arrays in `orchestrator.py` and **bypass `report.py` entirely**."*
  So it measures nothing about `DEFAULT_MAX_BLOCKS = 50` or
  `DEFAULT_RESERVED_BLOCKS = 10`, which live in the SDK builder the abort does
  not call.
- The readout's framing overhead is SA-1's own design choice — which is exactly
  why S3 declined to name an item ceiling and instead required SA-1 to **declare**
  its budget (`:280-285`). **That requirement is correct and this datum does not
  relax it.**

**What `block_count: 3` *does* legitimately corroborate**: S3's §6.2 item 1 —
*"the budget is per message, not per channel"* — is now live-confirmed. The
incumbent occupies 3 blocks per message and costs the readout zero. Co-tenancy
(§5) and the ceiling (§6) are confirmed independent. I endorse using it for that
and only that.

One genuine refinement it surfaces: §6 presents the 50-block ceiling as a
property of the channel's traffic, but the incumbent abort messages **do not pass
through the capped builder at all**. Minor, worth a line in SA-1's brief.

### 5.4 Does this evidence tilt §7? — **Yes, and it must be handled explicitly.**

The coordinator flagged the risk correctly and I confirm it is real. §7.3's
factual predicate — *"The ASR service **already** posts to `#account-health`
autonomously, 6×/day, unattended, today"* — was inferred from `cron` + code
(`main.tf:108`, `orchestrator.py:223`). **It is now an observed fact: 7 ticks, 7
posts, `ok: true`, during the pause.**

Retroactivity therefore stops being a hypothetical cost of reading (b) and
becomes a measured one. Since §7.3 is filed in reading (b)'s **against** column,
strengthening its factual base **strengthens the case against (b)** — which is
the tilt vector §3.2 already identified, now amplified by hard data.

**My ruling on this**: the census must go into the PT-02 briefing as a **fact**
(the incumbent is observed posting 6×/day) and **not** as a strengthened argument
in (b)'s against-column. Concretely, it cuts **both** ways and the briefing must
say so:

- **Against (b)**: a uniform modal now demonstrably re-classifies *observed live
  traffic*, not hypothetical traffic.
- **For (b)**: the very same observation shows the surface is **actively
  broadcasting right now**, which is precisely the condition the modal keys on —
  a live, currently-firing autonomous channel is a *stronger* candidate for
  gate-(b) scrutiny than a dormant one, not a weaker one.

S3 could not have written the second bullet — the datum did not exist. Whoever
writes PT-02 must. **Condition C-4.**

---

## 6. Missing rails

I looked, and I found **two genuine missing delivery rails plus one missing rail
*class***. This is not a completeness quibble: both missing rails are, on their
face, **better** fits for a recurring readout to an Asana-frontend team than
several rails S3 did enumerate — precisely because they are *update-in-place*
rather than *broadcast*.

**Where I looked**: (i) every route module declaring `{"type": "asana_api"}`
(F-3, 26 endpoints); (ii) the full `RouterMount` list at `main.py:456-492`
(28 routers, all reconciled); (iii) `src/autom8_asana/clients/` for client-layer
verbs with no route; (iv) the `.claude/commands/` and `ari rite pantheon` surface
(agent rails); (v) the autom8y monorepo's ASR service for producer-side rails.

### MR-1 — Asana **task description update-in-place** (`PUT /api/v1/tasks/{gid}`, `notes`)

**Receipt**: route `tasks.py:244` (`update_task`, target `task`);
`UpdateTaskRequest.notes` at `api/models.py:292-296` (*"New task description"*);
mounted `main.py:461`.

A single standing "Weekly Readout" task whose **description is overwritten** each
cycle. Visible in the frontend where the team already works; naturally
idempotent; no 50-block ceiling (Asana notes, not Slack blocks); no new task
appears in anyone's My Tasks.

**Why its absence matters**: it has a materially **different broadcast profile**
from R-05 task-CREATE. Editing a description does not fan out a new work item; it
generates a story visible to existing followers. That is exactly the *"reversible
**record** vs irretractable **broadcast**"* decomposition S3 invokes as §4.2
ground 2 — and the one write class where the two limbs genuinely come apart is
the class S3 never named. It is still **RESERVED** under CR-1's categorical
READ-ONLY clause (§4.2 ground 1) — I am not proposing it — but the operator
deciding OS-6 deserves to know the fenced set contains an option with a
softer broadcast profile than "create a task."

### MR-2 — Asana **project description update-in-place** (`PUT /api/v1/projects/{gid}`, `notes`)

**Receipt**: route `projects.py:262` (`update_project`, target `project`);
`UpdateProjectRequest.notes` at `api/models.py:506-509` (*"New project
description"*); mounted `main.py:465`.

The project description renders on the project Overview — for a team working a
board daily, the highest-visibility non-task surface in the product. Same
update-in-place properties as MR-1, and weaker notification semantics again.

### MR-3 — the missing rail *class*: **delivery by making existing views show the insight**

Every one of S3's 16 rows is a **push**: a message, a comment, a task, a file, a
link. For a team that lives in the Asana frontend, there is a whole delivery mode
that is not a message at all — **writing values into custom fields the team's
existing board views, sort orders and filters already surface**. The readout is
"delivered" by the board changing, with no new object and no notification.

This is not hypothetical here: R-06 (`entity_write.py:184`) and
`intake_custom_fields.py:46` are exactly the mechanism, both built. It is
**RESERVED** under CR-1's custom-field limb — again, I am not proposing it. But
§2's four-test bar is written entirely around rails that *carry a payload to a
reader*, so a pull-shaped rail cannot even be scored by it. A rail the method
cannot express is invisible in a way a rejected rail is not.

### Rails I checked and found correctly absent or correctly classified

`workflows.py:250` invoke (an execution trigger, not a delivery surface);
`sections.py` create/reorder (board structure, no reader payload);
`projects.py:454` add_members (an access-control act — correctly CR-2/§5(b)
territory, and not a readout carrier); Asana project **status updates** — S3's
claim that no client exists is **CONFIRMED**; outbound e-mail — no fleet rail
found beyond SNS (R-11, correctly classified).

**Net**: the *inventory's dispositions* are sound; its *coverage* has a
systematic gap at update-in-place and pull-shaped surfaces.

---

## 7. What I could not test

Named honestly rather than filled with plausible reasoning.

- **UV-P-C-1** — `[UV-P: whether an agent seat in this fleet can obtain a valid service JWT (audience https://api.autom8y.io) by following existing documented patterns, and therefore reach POST /v1/receipts, PATCH /api/v1/entity/{type}/{gid} or POST /v1/tasks/{gid}/custom-fields without an operator | METHOD: credential-distribution audit across the fleet's service-account issuance path (autom8y-auth), plus a review of agent-seat runtime env injection | REASON: this is a fact about credential distribution, not about this repo's code. Probing it would mean handling live credentials, which this seat will not do. **This is the open half of the R-05/R-06 security question** — §2 establishes the code-side gate is fleet-membership-only; whether fleet membership is reachable from an agent seat is unestablished. Route: security rite.]`
- **UV-P-C-2** — `[UV-P: the network reachability of the autom8y-asana API — whether the ALB/listener is internal-only or internet-facing, and what SG/WAF sits in front | METHOD: read terraform/services/asana/{alb,ecs,service}.tf in the autom8y monorepo at origin/main, or aws elbv2 describe-load-balancers | REASON: terraform/services/asana/ in THIS repo contains only observability alarm definitions; the service's network infra is defined elsewhere and I did not locate it within this dispatch. Bounds the blast radius of §2 but does not change the code-side finding.]`
- **UV-P-C-3** — readout-class payload delivery (§5.2 above).
- **Inherited and untouched by me**: UV-P-S3-1 (channel membership — I add the `orchestrator.py:1227` counter-signal at §3.3 but **cannot resolve it**; the ambiguity is genuine), UV-P-S3-2 (bot channel membership), UV-P-S3-3 (SNS subscribers), UV-P-4 (external surfaces — OPERATOR), UV-P-1/2/3.
- **I did not exercise any rail.** No Asana write, no Slack post, no Lambda
  invoke, no AWS mutation, no git mutation. Every finding above is a file read, a
  grep, or read-only git plumbing. Under CR-1 the three write classes are
  operator-reserved and verifying a rail by using it is the one failure this
  sprint cannot absorb.

### Conditions attached to this PASS

| # | condition | owner |
|---|---|---|
| **C-1** | **Correct R-04.** Strike *"and independently UNBUILT"* and *"No HTTP route, no MCP tool."* Replace with the `POST /v1/receipts` chain (F-1). R-04's verdict stays **RESERVED (CR-1)** — only the buildness ground is removed. | S3 re-author |
| **C-2** | **Correct §3.1 to "three of three"** and restate §9's FP-9/DEFER-S-1 row accordingly (it currently says *"two of three … are built"*). | S3 re-author |
| **C-3** | **Surface `orchestrator.py:1227` ("customer-facing channel")** in §7.1's against-column beside UV-P-S3-1, with its genuine ambiguity stated (§3.3). Do not resolve it. | S3 re-author → PT-02 |
| **C-4** | **PT-02 briefing must carry the tick census two-sidedly** per §5.4 — as a fact that cuts both ways, not as reinforcement of §7.3's anti-(b) column. | PT-02 author |
| **C-5** | **Record F-3 (26 endpoints) and F-4 (authentication-only gate)** in §4.2, replacing the illustrative list. Route F-4 to the **security** rite as a cross-rite observation: an Asana board write is reachable on fleet-membership alone while a cache-refresh is permission-gated (`admin.py:456`). | S3 re-author → security |
| **C-6** | **Add MR-1/MR-2/MR-3** to §3 as RESERVED rows, or state explicitly why update-in-place and pull-shaped surfaces are out of the inventory's scope. | S3 re-author |
| **C-7** | **Discharge UV-P-S3-4**; promote R-08 to `VERIFIED-LIVE`; open UV-P-C-3. Note that the census also independently discharges the `dry_run=False` inference (§5.1 item 2). | S3 re-author |

None of C-1..C-7 changes a rail's verdict. **One rail remains AVAILABLE (R-08),
now at a higher rung. CR-1 stands, over-determined and — on my findings — more
load-bearing than S3 claimed.**

---

## 8. Grade

**Self-attestation: MODERATE.** Ceiling per `self-ref-evidence-grade-rule`.

**Why not higher.** Every finding rests on file-read and grep probes of a static
read surface. I ran no runtime, minted no token, sent no request, and read no
Slack channel. F-1..F-4 and F-9 are STRONG *as code facts* — decorators, call
chains and mount points are deterministic and I walked them end-to-end — but the
claims that matter operationally (§2.6: can a seat actually reach these routes?)
rest on evidence I explicitly do not have (UV-P-C-1, UV-P-C-2). A structural
claim about reachability that cannot see the network layer or the credential
distribution path is capped, and I decline to call it more than MODERATE.

The tick census (§5) is the one strand at **STRONG** — but it is not mine. It is
rite-disjoint from me, produced by the main thread, and I graded it by attacking
its inference chain (§5.1) rather than by producing it. I confirmed it, partially
narrowed its reach (§5.2), and **rejected one of the three uses proposed for it**
(§5.3).

**Why not lower.** The load-bearing findings are two-sided-tested rather than
asserted: I reproduced S3's own grep before contradicting its inference (F-1);
I tried three independent ways to make `report_posted` mean less than delivery
and failed (§5.1); I tried to show §7.1 received asymmetric favourable detail and
failed (§3.1); and I confirmed the artifact's Slack, ceiling, 404 and monorepo
receipts **all** reproduce exactly (F-5, F-6, F-7, F-9).

**What I tried that failed to break the artifact** — recorded because, per the
dispatch, this is what raises the grade rather than lowers it:

1. **§7 tilt by asymmetric detail** — failed. Row counts are near-symmetric and
   the ⚠-weighting runs *against* the reading S3 mildly leans toward. S3 also
   pre-emptively disarms its own strongest partisan argument at `:327`.
2. **`report_posted` as mere egress-attempt** — failed on three checks
   (in-`try` placement, `dry_run` early return, SDK `ok:false` raising).
3. **R-05 PAT-mode as a privilege escalation** — failed. Pass-through confers
   nothing the caller lacked; the route is a proxy.
4. **The 404 defect as secretly S3's to absorb** — failed. It touches no rail
   verdict; S3's constraint-on-SA-1 disposition is exactly right.
5. **S3 having read the working tree instead of `origin/main`** — failed. Its
   `report.py:193` citation resolves only at `origin/main` (worktree is 182
   lines), which proves it honoured the discipline it claimed.
6. **S3's `#account-health` receipts drifting against today's `origin/main`** —
   failed. Main advanced `0e60e0f5` → `7bbb418e` since S3's dispatch; every cited
   line still resolves.

**Where the artifact is genuinely strong**: §2's three-state discrimination
("unbuilt" / "built but fenced" / "built, reachable, reserved") is the right
instrument for this problem and is what made F-1 and F-3 *findable* — S3 built
the frame that exposes its own gap. §4.2's categorical-not-enumerative ground is
correct and is the reason a 24-endpoint enumeration miss changes no verdict.
§6.2's refusal to name an item ceiling, substituting a requirement that SA-1
*declare* its budget, is the correct call and survives the live `block_count`
datum intact.

**Ceiling on the whole S3 record**: MODERATE until C-1 and C-2 land. The
corrections are small in text and large in consequence — R-04 is the one row that
still carries the word **UNBUILT**, and §3.1 exists specifically to stop a later
seat inheriting "unbuilt" as a licence to treat the fence as redundant.
