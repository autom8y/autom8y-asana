---
type: decision
status: draft
artifact_id: RAILS-insight-delivery-verified-2026-08-12
revision: 2
remediates: CRITIQUE-s3-delivery-rails-2026-08-12
initiative: asana-native-insight-delivery
sprint: S3
workstream: WS-E
date: 2026-08-12
author: architect (10x-dev), under the shared-spine S3 dispatch
external_critic: >-
  structure-evaluator (arch — rite-disjoint) — RUN 2026-08-12.
  Verdict PASS-WITH-CONDITIONS, conditions C-1..C-7.
  Eight attacks pressed; five failed against this artifact, three landed.
  All three landed in the SAFE direction (the CR-1 fence is MORE load-bearing,
  never less). This revision discharges C-1, C-2, C-3, C-5, C-6, C-7;
  C-4 is routed to the PT-02 author with the material staged here at §7.3/§7.6.
repo: autom8y-asana
subject: >-
  The delivery-rail inventory for this initiative, named from LIVE receipts
  only, under the binding CR-1 fence that reserves every Asana-native write
  rail to the operator.
evidence_grade: MODERATE (self-attestation ceiling; self-ref-evidence-grade-rule)
binding_inputs:
  - ".sos/wip/frames/asana-native-insight-delivery.shape.md §3 (CR-1) — BINDING"
  - ".sos/wip/frames/asana-native-insight-delivery.md §5 WS-E, SVR-1/3/4/5/8"
  - ".ledge/decisions/RULING-operator-gate-b-modal-2026-08-12.md — §OPEN BINDS this sprint"
  - ".ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md :48-65"
governing_note: >-
  Nothing in this artifact is a decision the operator has not already made.
  Where two readings are live, BOTH are presented and NEITHER is assumed.
---

# RAILS — delivery rails for asana-native-insight-delivery, verified not assumed

## REVISION 2 — what changed under C-1..C-7

The rite-disjoint critic (`structure-evaluator`, arch) returned
**PASS-WITH-CONDITIONS** at
`.ledge/reviews/CRITIQUE-s3-delivery-rails-2026-08-12.md`. It pressed eight
attacks. **Five failed against this artifact; three landed.** Every one that
landed moves in the safe direction: the CR-1 fence is *more* load-bearing than
revision 1 claimed, never less.

### R2.1 Disposition table

| # | condition | disposition | what moved | rail verdict changed? |
|---|---|---|---|---|
| **C-1** | Correct R-04: strike *"and independently UNBUILT"* / *"No HTTP route, no MCP tool"* | **ACCEPTED** | R-04's receipt cell rewritten to carry the `POST /v1/receipts` chain, re-walked hop-by-hop from this seat (§3 R-04, SVR-S3-13). The verdict cell is untouched | **NO** — R-04 stays **RESERVED (CR-1)**. Only the *buildness ground* is removed; CR-1's gate-(a)/(b) + predicate-integrity + `asana-mcp-v1:209` grounds were always independent of it |
| **C-2** | Correct §3.1 to "three of three"; restate §9 FP-9/DEFER-S-1 | **ACCEPTED** | §3.1 rewritten (headline corrected + a standing caution on directory-scoped symbol probes, §3.1.1). §9 FP-9 row restated | **NO** |
| **C-3** | Surface `orchestrator.py:1227` ("customer-facing channel") in §7.1's against-column, ambiguity stated, **not resolved** | **ACCEPTED** | Added to §7.1's *against* column **and** to §7.2's *in favour* column (see R2.3 — the critic asked for §7.1 only; a signal that bears on the predicate belongs in both readings' columns or it is itself a tilt). §9 DEFER-WATCH-2 row annotated. **Not resolved here** | **NO** — DEFER-WATCH-2 remains **STANDING** |
| **C-4** | PT-02 briefing must carry the tick census two-sidedly | **ACCEPTED — routed, not discharged here.** C-4's owner is the PT-02 author | §7.3 restated on observed fact; **§7.6 added** as the staged two-sided census brief PT-02 inherits verbatim | **NO** |
| **C-5** | Record F-3 (26 endpoints) + F-4 (authentication-only gate) in §4.2, replacing the illustrative list; route F-4 to **security** | **ACCEPTED** | §4.2 rewritten around the machine-readable census (26 endpoints / 8 modules, re-run from this seat) + **§4.3 added** carrying the authorization finding and its security-rite routing. New **O-H** in §10 | **NO** — and see R2.2, where I checked the one verdict this *could* have moved |
| **C-6** | Add MR-1/MR-2/MR-3 or state why out of scope | **ACCEPTED-WITH-NARROWING** | Added as **R-17/R-18/R-19**, all **RESERVED (CR-1)**. §4.2 ground 2's record/broadcast decomposition repaired (§4.2.1). §2 extended to make a pull-shaped rail *expressible* (§2.1). **Narrowing**: the critic's "materially softer broadcast profile" is carried as `[INFERRED — WEAK]` + **UV-P-S3-5**, not as a receipt — see R2.4 | **NO** — three new rows, all RESERVED; no existing row moves |
| **C-7** | Discharge UV-P-S3-4; R-08 → `VERIFIED-LIVE`; open UV-P-C-3; note the `dry_run` bonus | **ACCEPTED** | §8 marks UV-P-S3-4 **DISCHARGED**; §12 raises R-08's rung; UV-P-C-3 opened; the `dry_run=False` live discharge recorded at §12 and §8 | **NO — but the RUNG changed.** See R2.2 |

### R2.2 Did any rail verdict change? — checked independently, not assumed

The critic asserts none should. I verified this rather than inheriting it, by
re-walking every row whose *ground* this revision touches:

- **R-04** — gained buildness, kept **RESERVED**. Under §2 it now passes test 1
  (exists) where it previously failed it, and it passes test 3 (an Asana comment
  on a Business task is read by a non-engineering human). It still fails test 4,
  which is the RESERVED condition. Verdict unchanged; **the number of tests it
  fails dropped from two to one**, which is exactly why §3.1 matters.
- **R-08** — verdict unchanged (**AVAILABLE**); **rung** rises
  `VERIFIED-IN-CODE-AND-TERRAFORM` → **`VERIFIED-LIVE`**. This is the one real
  movement in the artifact and it is a *rung*, not a *verdict*. Recorded
  separately so a later seat does not read "no verdict changed" as "nothing
  changed."
- **R-13** — this is the row the security finding (§4.3) could plausibly have
  moved, so I tested it. F-4 shows the HTTP API's gate is fleet-membership, not
  authorization. Does that make it a *team* rail? **No.** §2 test 3 asks whether
  it reaches a **non-engineering human**; a fleet service-account JWT holder is
  not a teammate. R-13's verdict holds; its *characterisation* ("authenticated
  engineering surface") holds and becomes more precise, not less.
- **R-05/R-06/R-07, R-17/R-18/R-19, and all 26 census endpoints** — every one is
  an Asana write, caught categorically by CR-1's `READ-ONLY` clause (§4.2 ground
  1). None can become available without OS-6.
- **R-01, R-02, R-03, R-09..R-12, R-14..R-16** — untouched by any condition;
  R-01 and R-02 re-probed anyway this revision (SVR-S3-16) and both reproduce.

> **Result: no rail's verdict changes. One rail's rung rises (R-08). Three rows
> are added, all RESERVED.** The critic's assertion is CONFIRMED on independent
> re-derivation.

### R2.3 Where I did more than the condition asked

- **C-3 as written puts `orchestrator.py:1227` in reading (a)'s against-column
  only.** I declined that scoping. A datum that bears on DEFER-WATCH-2's exact
  predicate is *evidence about the surface*, and filing evidence about the
  surface in exactly one reading's adverse column is the same asymmetry the
  critic graded as MILD TILT at its §3.2. It is recorded in **both** columns,
  with the ambiguity stated identically in each.

### R2.4 Where I did not accept the critic's framing — with receipts

**REJECTED-WITH-RECEIPT (one item), and one narrowing:**

1. **The critic's MR-1 claim that description-update has a "materially softer
   broadcast profile than task-CREATE" is NOT receipted, and I will not carry it
   as one.** The critic's own supporting sentence — *"Editing a description does
   not fan out a new work item; it generates a story visible to existing
   followers"* — is a claim about **Asana's product notification semantics**, not
   about this repo, and no in-repo receipt establishes it. Worse, the receipt
   that *does* exist on that exact route cuts the other way:

   > `src/autom8_asana/api/routes/tasks.py:272-273` — *"**CAUTION**: Setting
   > `completed=true` may trigger Asana Rules automations (notifications, section
   > moves, workflow transitions) on FIRST fire."*

   That caution is scoped to the `completed` limb, not the `notes` limb — so it
   does not falsify the critic either. The honest position is that
   `PUT /api/v1/tasks/{gid}` is a route on which the repo **affirmatively warns
   about automation-triggered notifications**, and carries **no** receipt that a
   `notes`-only update is notification-quiet. Carried as `[INFERRED — WEAK]` plus
   **UV-P-S3-5**. The structural point the critic is making — that the
   record/broadcast decomposition comes apart at update-in-place — survives this
   narrowing intact, and I adopt it (§4.2.1).

2. **`block_count: 3` is NOT used as framing-overhead arithmetic.** I agree with
   the critic's rejection and adopt its reasoning verbatim-in-substance: the
   abort path is a hand-built 3-block array that **bypasses `report.py`
   entirely** (`services/account-status-recon/.know/feat/slack-report-delivery.md:40`,
   re-read at `origin/main` this dispatch), so it touches neither
   `DEFAULT_MAX_BLOCKS` nor `DEFAULT_RESERVED_BLOCKS`. It corroborates §6.2
   item 1 (**budget is per-message**) and nothing else. §6.2 item 1 updated;
   §6.2 item 3's refusal to name an item ceiling **stands unrelaxed**.

### R2.5 What the critic tried and could not break — recorded, because this is the load-bearing half

Five of eight attacks failed against revision 1. Naming them is not
self-congratulation; it is what distinguishes a two-sided audit from a
one-sided one, and a later seat inheriting only the three corrections would
mis-weight the artifact.

| attack | outcome | where |
|---|---|---|
| §7 tilt by asymmetric favourable detail | **FAILED** — row counts near-symmetric; the ⚠-weighting runs *against* the reading the artifact mildly leans toward; `:327` pre-emptively disarms the artifact's own strongest partisan argument | critique §3.1 |
| `report_posted` as mere egress-*attempt* | **FAILED** on three independent checks (in-`try` placement, `dry_run` early return, SDK `ok:false` raising) | critique §5.1 |
| R-05 PAT-mode as privilege escalation | **FAILED** — `dependencies.py:140-149` passes the caller's own token through; the route is a proxy conferring nothing the caller lacked | critique §2.2 |
| the NF-1 404 defect as secretly S3's to absorb | **FAILED** — it touches no rail verdict; the constraint-on-SA-1 disposition is correct as written | critique §4 F-6 |
| the artifact having read the working tree instead of `origin/main` | **FAILED** — the `report.py:193` citation resolves *only* at `origin/main` (worktree is 182 lines), which proves the discipline was honoured, not merely claimed | critique §4 F-7 |

### R2.6 Read-surface drift — a live re-confirmation, and a correction to the critic

`SVR-S3-11` recorded the autom8y `origin/main` tip as `0e60e0f5`. The critic
recorded it as `7bbb418e`. **At this dispatch it is `0c2fc6a5`, and the local
checkout has itself advanced to `29724c2b` on the same unrelated branch
(`fix/wss-wildcard-scope-bypass-closure`, still NOT an ancestor of
`origin/main`).** Main has moved twice inside one day. **Every monorepo citation
in this artifact was re-resolved at `0c2fc6a5` in this dispatch and every one
still resolves** (SVR-S3-14). The drift is benign three times running — which is
precisely why it should not be trusted a fourth. The pinned-SHA fields in
SVR-S3-9/10/12 are therefore restated as *"read at `origin/main` on 2026-08-12"*
rather than as a SHA that will be stale before it is re-read.

---

## §0 What this artifact is, and what it is NOT

**IS**: an inventory of every candidate delivery rail for a recurring readout,
each carrying either a receipt I probed myself in this dispatch, or an explicit
UV-P. Plus the design answer for the one rail that is live, the inherited
ceiling that binds its length, and a two-sided presentation of the open scope
question the operator ruled *undecided in both directions* today.

**IS NOT**:
- a rail *build*. Naming a rail is not building one (frame `:457`).
- a recommendation on the fork. GATE-FORK (OS-3) is the operator's.
- a ruling on the §OPEN scope question. That is PT-02 / operator (§7 below).
- any communication to any client or team member. None occurred.

**Nothing was inherited.** Every rail the frame already falsified (SVR-1/3/4/5)
was **re-probed by me, from this seat, in this dispatch**. Several of the frame's
receipts came back **REFINED, not confirmed** — see the falsification note at
§3.1. Surfaced, never papered (shape `:1515`).

✦ **And in revision 2, one of MY OWN receipts came back REFUTED.** The same
discipline applies to this artifact's output as to its input: R-04's
"independently UNBUILT" was **wrong**, caught by the rite-disjoint critic, and is
corrected in place at §3 and §3.1.1 rather than quietly amended. **Read
`REVISION 2` above before anything else** — it is the map of what moved and, more
importantly, of what did not.

---

## §1 Binding fences, restated before anything is named

| fence | source | effect on this artifact |
|---|---|---|
| **CR-1** — all three Asana write classes are OPERATOR-RESERVED; the initiative is **READ-ONLY with respect to the Asana board** | shape `:413-426` | **No Asana-native rail is named as available anywhere below.** §4 restates it and states its reach over the classes CR-1 did not enumerate |
| **K-SW-4** — any sprint proposing an Asana-native write **HALTS** and routes to **OS-6** | shape `:1439` | This sprint proposes none. §4 records the escalation path so no later seat treats an unenumerated class as an open door |
| **DEFER-WATCH-2** — any rail proposal whose surface a client could reach → **HALT and ESCALATE** | shape `:1400` | Verified at §3 per-row and at §7. Disposition recorded in §9 |
| **Charter §5(b)** — "anything a customer sees", **regardless of reversibility** | `CHARTER…:55` | Governs the whole §7 two-sided presentation |
| **No client or team communication of any kind** | S3 dispatch | Honoured. Zero messages sent; zero Slack API calls made |
| **Self-attestation caps MODERATE** | shape `:1512` | Declared in frontmatter and §12. ✦ **REVISION 2**: `structure-evaluator` critique **HAS RUN** — PASS-WITH-CONDITIONS. **The ceiling still holds**: rite-disjoint critique raises confidence, it does not convert file-read evidence into runtime evidence, and the critic capped itself at MODERATE on identical grounds |
| **Read `autom8y` at `origin/main` ONLY** | ADR-007 §8 O-11 | Honoured, and the hazard was **confirmed live** — see SVR-S3-11. ✦ **REVISION 2**: re-confirmed and **worsened** — main advanced twice in one day (`0e60e0f5` → `7bbb418e` → `0c2fc6a5`) while the local checkout sits on `fix/wss-wildcard-scope-bypass-closure` @ `29724c2b`, still **NOT an ancestor**. Every monorepo anchor re-resolved this dispatch (SVR-S3-14) |
| ✦ **READ-ONLY against the live world** | S3 dispatch + CR-1 | **Honoured absolutely, both revisions.** Zero writes of any class: no Asana call, no Slack post, no Lambda invoke, no AWS mutation, no terraform action, no git mutation. The critic completed with the same discipline. **Verifying a rail by exercising it is the one failure this sprint cannot absorb** |

---

## §2 Method — what it takes to be called "available"

A rail is **AVAILABLE** only if all four hold, each with a receipt:

1. **It exists** — code/config that carries a payload, present at the read
   surface of record.
2. **It is not gated OFF** — no flag, fence, or ruling standing between it and
   use.
3. **It reaches a non-engineering human** — an agent-facing or engineer-facing
   surface is not a team rail. (This is the discriminator the frame's SVR-4 drew
   and it does most of the work below.)
4. **Using it is inside this initiative's autonomy** — it does not require an
   operator ruling to fire.

Anything failing (1) or (2) is **NOT AVAILABLE**. Anything failing (3) is
**NOT A TEAM RAIL** — it may still be true and useful, but it cannot discharge
rung 2. Anything failing only (4) is **RESERVED** — real, reachable, and the
operator's to open.

The three states are kept distinct deliberately: "unbuilt", "built but fenced",
and "built, reachable, and reserved" have different costs and different doors,
and collapsing them is how a fence gets mistaken for an absence.

### §2.1 Test 3 restated — the bar was PUSH-ONLY, and that was a real gap

**[ADDED REVISION 2 under C-6.]** As written in revision 1, test 3 —
*"it reaches a non-engineering human"* — silently presumes a rail that **carries
a payload to a reader**. Every one of revision 1's sixteen rows was push-shaped:
a message, a comment, a task, a file, a link. A rail that delivers by **changing
a surface the reader already looks at** could not be scored by the bar at all,
and a rail the method cannot express is invisible in a way a rejected rail is
not. The critic found this and it is correct.

I take the *extend* branch rather than the *declare-push-only* branch, because
push-only is not a defensible restriction for a team that lives inside a
frontend: for such a team the highest-fidelity delivery may be the board itself
changing.

> **Test 3 (restated).** *The rail puts the insight in front of a
> non-engineering human* — by **either**
> **(3-push)** carrying a payload to them, **or**
> **(3-pull)** changing a surface they already consult on their own cadence.

**A pull rail carries an extra burden the push rails do not**, and it must be
stated or the extension smuggles in a weaker bar:

> **Test 3-pull additionally requires a receipt that the surface is one the team
> demonstrably already consults.** For a push rail, delivery is established by
> the transport firing. For a pull rail, transport is trivially satisfied (the
> write lands) and *readership is the entire question*. Without that receipt, a
> pull rail is not a delivery rail — it is a write nobody reads.

**Consequence, and it is not a dodge:** that receipt is exactly what **UV-P-4**
asks for — *"what non-engineering data surfaces the offers/account team already
has"* (§8) — and UV-P-4 is **OPERATOR-OWNED and OPEN**. So the pull-rail class
(R-19) is now *expressible* by the bar and **not yet scoreable** by it, for a
reason this artifact already carries rather than a new one. The extension makes
the gap visible instead of structural. **This is a second, previously-unnoticed
consequence of UV-P-4**: it does not merely soft-block the *external* half of the
inventory (§8), it hard-blocks scoring of an entire *in-repo* rail class.

---

## §3 The rail inventory

Every row: a receipt I ran, or a UV-P. **Zero rows named on inference.**

| # | candidate rail | verdict | receipt (probed this dispatch) |
|---|---|---|---|
| **R-01** | **`iris` harness agent** | **NOT AVAILABLE — does not resolve** | `ls .claude/commands/iris.md` → *No such file or directory (os error 2)*; `ls .claude/agents/iris.md` → same; `ari rite pantheon` → **24 rows, 0 matching `iris`** (`grep -ci iris` → `0`, exit 1). `.claude/commands/` contains `iris-attestation.md` — a **different** command — which is exactly the near-miss that makes this rail look present when it is not |
| **R-02** | **MCP composite write surface** (`asana_complete_tagged_task`) | **NOT AVAILABLE — exposure-gated OFF, and fenced** | `mcp/asana_mcp/assembly.py:53-56` verbatim: *"EXPOSURE-GATED (W-5 / GATE-BW): register() self-gates on / ASANA_MCP_ENABLE_WRITE_SURFACE (default OFF) — attaches nothing while off."*; `mcp/serve_stdio.py:26` verbatim *"…(default OFF); this launcher never sets it."*; flag read at `:60` defaults to `""` → OFF |
| **R-03** | **MCP read surface** (5 read tools, stdio) | **NOT A TEAM RAIL — agent transport, under a promotion fence** | `mcp/serve_stdio.py:75` → `mcp.run(transport="stdio", show_banner=False)`; `mcp/README.md:3-5` verbatim: *"REFERENCE / THROWAWAY POSTURE. This is a proof-of-concept, NOT production code, and NOT to be promoted before the charter §4 probe rules COMMIT"*. stdio is mounted by a Claude Code client: it can deliver to an **agent**, never to a non-engineering human. Naming it a team rail would additionally breach its own promotion fence (shape `:1542`) |
| **R-04** | **Asana comment-CREATE** | **RESERVED (CR-1)** — ⚠ **and BUILT, reachable, and S2S-mounted** — ✦ **CORRECTED REVISION 2 (C-1)** | **The route reaches the verb through `services/`, not `api/`, so a grep scoped to `api/` never sees it.** Chain re-walked hop-by-hop this dispatch: `api/main.py:491` `RouterMount(router=receipts_router)` → `api/routes/receipts.py:82` `router = s2s_router(prefix="/v1", …, include_in_schema=False)` → `:85-86` `@router.post("/receipts", …)` → **`POST /v1/receipts`**; declared write at `:89-91` `x-fleet-side-effects: [{"type": "asana_api", "target": "business_task_comment"}]`; gated `:103` `claims: Annotated[ServiceClaims, Depends(require_service_claims)]`; executes with the bot PAT at `:163` `async with AsanaClient(token=auth_context.asana_pat)`; calls `:169` `await service.thread_receipt(` → `services/receipts_service.py:346` `await self._client.stories.create_comment_async(task=business_gid, text=text)` → `clients/stories.py:249`. The module says so in its own first paragraph: `receipts.py:3-4` *"POST /v1/receipts - thread an internal forwarding-lifecycle receipt onto the clinic's Business task **as an Asana comment**."* **Revision 1's grep is accurate and its inference was false — see §3.1.1.** CR-1 reserves this class on gate (a)/(b) + predicate-integrity grounds (shape `:375-378`, `:381-396`) and the `asana-mcp-v1:209` fence — **none of which ever depended on buildness** |
| **R-05** | **Asana task-CREATE** | **RESERVED (CR-1)** — ⚠ **and BUILT, contrary to the inherited picture** | `src/autom8_asana/api/routes/tasks.py:182-197`: `@router.post("", summary="Create a task", … status_code=HTTP_201_CREATED)` with `x-fleet-side-effects: [{type: asana_api, target: task}]` and `x-fleet-idempotency: {idempotent: false}`. Auth: `AsanaClientDualMode`. **This rail exists and is reachable.** CR-1 reserves it on gate-(a)/(b) + predicate-integrity grounds (shape `:381-396`), all of which stand independently of buildness |
| **R-06** | **Asana custom-field / entity-field write** | **RESERVED (CR-1)** — ⚠ **and BUILT** | `src/autom8_asana/api/routes/entity_write.py:184`: `@router.patch("/{entity_type}/{gid}")` with `x-fleet-side-effects: [{type: asana_api, target: entity_task}]`, gated `Depends(require_service_claims)` (S2S-only), writable types enumerated by an `EntityWriteRegistry` (`:247-262`). CR-1 reserves it on the acquired-dependency limb (shape `:397-411`) |
| **R-07** | **Asana external attachment** (`create_external`) | **RESERVED — the class CR-1 did not enumerate; see §4.2** | `src/autom8_asana/clients/attachments.py:340` `create_external_async`. Client-layer; no route probed as exposing it. Named here so it is not later discovered as an unruled door |
| **R-08** | **Slack `#account-health`** | ✅ **AVAILABLE — the only rail clearing all four §2 tests** | Channel default `#account-health` at autom8y `origin/main` `services/account-status-recon/src/account_status_recon/config.py:177-180`. Wired live: `terraform/…/account-status-recon/main.tf:135` `SLACK_CHANNEL = var.slack_channel`. Cadence `main.tf:108` → `cron(0 */4 * * ? *)` = **6 ticks/day**. Posts fire at `orchestrator.py:160/162`, `:223/225`, `:501/503`. Egress **not** suppressed: `config.py:210-214` `dry_run` default `False`, and `environments/production.tfvars` sets no `ASR_DRY_RUN`/`DRY_RUN` (full file read; absent). Team-facing by its own design record: *"The business stakeholders who act on anomalies are not engineers; they read Slack"* (`services/account-status-recon/.know/feat/slack-report-delivery.md:30`). ✦ **REVISION 2 (C-7): now VERIFIED-LIVE, not merely armed.** `EVIDENCE-tick-terminal-census-2026-08-12.md` — 7/7 ticks over 2026-08-11T20:00Z→2026-08-12T20:36Z emit `event: slack_post` **and** `event: report_posted` naming `#account-health` (queryId `bf15fa66-2ea9-4622-ac30-b82fcb8e4dbc`). I re-derived why `report_posted` means *delivered* rather than *attempted* — SVR-S3-15. **UV-P-S3-4 DISCHARGED**; rung → `VERIFIED-LIVE` (§12) |
| **R-09** | **A NEW Slack channel for the readout** | **NOT AVAILABLE TODAY — a build, plus an operational act outside this seat** | `SLACK_CHANNEL` is a **single** value consumed by **all three** ASR post sites (`orchestrator.py:162, :225, :503` all pass `settings.slack_channel`), corroborated at `services/account-status-recon/.know/feat/observability-invocation-correlation.md:310`: *"Changing this changes the target for all three call sites simultaneously."* So retargeting moves the **aborts** too. A **new producer** with its own channel setting is a different matter — see §5.4. Either way the bot must be a member of the target channel: **UV-P-S3-2** |
| **R-10** | **`slack-alert` → `#platform-alerts`** | **NOT A TEAM RAIL — engineering alarm transport** | `services/slack-alert/README.md:3`: *"SNS-triggered Lambda that posts CloudWatch alarm notifications to Slack."*; `terraform/services/slack-alert/variables.tf:28-32` default `"#platform-alerts"`. Routing a recurring business readout down the oncall alarm path is a category error and would page humans on a report |
| **R-11** | **SNS `autom8y-platform-alerts` e-mail subscription** | **NOT A TEAM RAIL — same category error; and the subscriber claim is uncorroborated** | `terraform/services/asana/observability_alarms.tf:672` asserts the topic *"has live Slack+email subscribers"* — an **in-repo comment**, not a probe. Even if true, this is the oncall alerting topic. **UV-P-S3-3** |
| **R-12** | **S3 verdict surface `s3://autom8y-asr-verdicts` / presigned URL / auth'd view** | **RESERVED — CR-2, charter §5(b) security/credentials** | shape `:432-449`: every mechanism for putting this in front of a non-engineer (IAM principal, presigned bearer URL, or widening an existing auth surface) is an access-control decision, and §5(b) fires *regardless of reversibility*. Operator-reserved at **OS-7** |
| **R-13** | **`autom8y-asana` HTTP API** (`/v1/*`, `/api/v1/*`) | **NOT A TEAM RAIL — authenticated engineering surface** | Write verbs are S2S- or dual-mode-authenticated (R-05/R-06 receipts). A non-engineering teammate holds no credential and no client. Exposing one would itself be a §5(b) credentials decision, i.e. CR-2's own reasoning one surface over |
| **R-14** | **CloudWatch Logs Insights / dashboards** | **NOT A TEAM RAIL — engineer-operated query surface** | It is the *source* NF-2/S4 is adjudicating (shape `:160-204`), not a delivery channel. Requires console access and query authorship |
| **R-15** | **A `.ledge/` markdown artifact relayed by the operator** | **REAL — this is what actually carried brief #1 — but it is OPERATOR-DEPENDENT, not autonomous** | `REPORT-asr-team-brief-2026-08-12.md` exists and is `status: draft` (`:3`); whether it was ever delivered, and by what channel, is **UV-P-1** and remains OPEN (`RULING…gate-b-modal:126` item 6). This rail **cannot discharge rung 2** — a human relays each publication by construction |
| **R-16** | **A BI tool / sheet / dashboard the team already uses** | **UNKNOWN — UV-P-4, OPERATOR-OWNED, OPEN** | Not probeable from this seat: it is a fact about surfaces **outside this repo**. Carried per §8, **not guessed** |
| **R-17** ✦ | **Asana task description UPDATE-IN-PLACE** (`PUT /api/v1/tasks/{gid}`, `notes`) — *critic's MR-1* | **RESERVED (CR-1)** — ⚠ **BUILT** — ✦ **ADDED REVISION 2 (C-6)** | Route `src/autom8_asana/api/routes/tasks.py:244` `@router.put("/{gid}", summary="Update a task", …)` with `x-fleet-side-effects: [{"type": "asana_api", "target": task}]`; payload field `api/models.py:292-295` `notes: str \| None = Field(default=None, description="Task description", …)`; mounted `main.py:461`. **Shape**: one standing readout task whose description is overwritten each cycle — idempotent by construction, no Slack block ceiling, no new work item in anyone's My Tasks. ⚠ **Its "softer broadcast" property is `[INFERRED — WEAK]`, not receipted** — the same route's docstring warns *"**CAUTION**: Setting `completed=true` may trigger Asana Rules automations (notifications, section moves, workflow transitions)"* (`tasks.py:272-273`); that caution is scoped to the `completed` limb, and **the repo carries no receipt either way for a `notes`-only update**. **UV-P-S3-5.** RESERVED regardless: §4.2 ground 1 is categorical |
| **R-18** ✦ | **Asana project description UPDATE-IN-PLACE** (`PUT /api/v1/projects/{gid}`, `notes`) — *critic's MR-2* | **RESERVED (CR-1)** — ⚠ **BUILT** — ✦ **ADDED REVISION 2 (C-6)** | Route `src/autom8_asana/api/routes/projects.py:262` `@router.put("/{gid}", summary="Update a project", …)`, `x-fleet-side-effects` target `project`; payload field `api/models.py:506-509` `notes: str \| None = Field(…, description="Project description", …)`; mounted `main.py:465`. The project description renders on the project Overview — for a team working a board daily, the highest-visibility non-task surface in the product. Same update-in-place shape as R-17 and the **same** unreceipted notification premise (**UV-P-S3-5**) |
| **R-19** ✦ | **PULL-SHAPED delivery: writing values into custom fields the team's existing board views already surface** — *critic's MR-3, a rail CLASS* | **RESERVED (CR-1)** — ⚠ **BUILT (two mechanisms)** — **and NOT SCOREABLE by §2 until UV-P-4 closes** — ✦ **ADDED REVISION 2 (C-6)** | Mechanisms both built and both S2S-gated: `entity_write.py:184` `@router.patch("/{entity_type}/{gid}")` (the R-06 row) and `intake_custom_fields.py:46` `@router.post(…)` on `s2s_router(prefix="/v1/tasks", …, include_in_schema=False)` (`:43`) → **`POST /v1/tasks/{task_gid}/custom-fields`**, `x-fleet-side-effects` target `task_custom_fields` (`:51`) — a **same-class sibling of R-06 that revision 1 never named**. **This is not a message**: the readout is "delivered" by the board changing under existing sorts and filters, with no new object and no notification. It is the class §2 could not express before §2.1. **Its test-3-pull receipt — that the team already consults such a view — is precisely UV-P-4, which is OPEN and OPERATOR-OWNED.** RESERVED under CR-1's custom-field limb; **proposed by nobody, here or anywhere** |

### §3.1 Falsification note — REVISION 2: THREE of three write classes are built

Per shape `:1515` ("surfaced, never papered"), and per the S3 mission's own
instruction to verify rather than inherit.

**✦ CORRECTED REVISION 2 under C-1/C-2.** Revision 1 said *two of three* Asana
write classes are built. **That was wrong. It is three of three.**

- **The frame's SVR-5 checked only `create_comment`**, and revision 1 caught
  that. Revision 1 then re-ran the same under-scoped probe one row away and
  reached the same species of false conclusion — see §3.1.1.
- **All three CR-1-enumerated write classes are BUILT and reachable at the HTTP
  API**: comment-CREATE at `POST /v1/receipts` (R-04), task-CREATE at
  `POST /api/v1/tasks` (R-05), custom-field / entity-field write at
  `PATCH /api/v1/entity/{type}/{gid}` (R-06) — with a fourth, unnamed
  same-class sibling at `POST /v1/tasks/{task_gid}/custom-fields`
  (`intake_custom_fields.py:46`, now R-19).
- **Consequence for CR-1: none to its outcome; more to its load-bearing than
  revision 1 claimed.** CR-1 listed "unbuilt" as an *independent* ground for
  comment-CREATE (shape `:375-378`). **That ground is now removed** — not by a
  ruling, but by a fact revision 1 got wrong. The remaining grounds are gate (a),
  gate (b), predicate integrity, and the `asana-mcp-v1:209` fence, and **all of
  them hold for all three classes**. The ruling survives intact and is now
  **carried entirely by the governance grounds**, with no buildness ground left
  underneath any limb of it.
- **Why this matters, restated at its true strength:** for **all three** classes
  — and for all **26** declared Asana-write endpoints (§4.2) — **the fence is
  the only thing standing between this initiative and an Asana write.** A later
  seat reading "Asana writes are unbuilt" would conclude the fence is redundant.
  It is not. It is the whole mechanism. **R-04 was the last row in this
  inventory carrying the word UNBUILT and that word is now gone from it.**

#### §3.1.1 The error class, named — a TRUE receipt supporting a FALSE claim

This is the sprint's real lesson and it is worth more than the correction.

Revision 1's probe was `grep -rn "create_comment" src/autom8_asana/api/ mcp/`
→ exit 1. **The critic reproduced that grep exactly and confirms it is
accurate.** The receipt was true. The claim built on it — *"No HTTP route, no
MCP tool"* — was false. The route exists; it reaches the verb through
`services/receipts_service.py`, which the grep's directory scope excluded.

> **Standing caution for every later seat on this initiative:**
> **A grep scoped to a directory tests where a TOKEN APPEARS, not where a
> CAPABILITY IS REACHABLE.** Absence of a symbol under `api/` is evidence about
> `api/`. It is *not* evidence that no route reaches the behaviour, because a
> route reaches behaviour by *calling* — through `services/`, through a client,
> through an SDK. To falsify reachability you must walk **mount → router →
> decorator → handler → service → client**, or read the declared side-effect
> marker (`x-fleet-side-effects`), which is the codebase's own machine-readable
> answer to exactly this question and would have caught it in one grep
> (§4.2).

This is **structurally the identical class** revision 1 had just caught in the
inherited SVR-5 ("checked only `create_comment`") — an under-scoped symbol probe
generalised into a claim about a whole class — **committed again, one row away,
in the same artifact, by the seat that had just named the pattern.** Naming a
failure mode does not immunise against it. Recorded here as a standing caution
rather than as an apology, because the next seat's exposure is the same and its
correction is mechanical.

### §3.2 The inventory in one line

> **One rail is AVAILABLE: Slack `#account-health` (R-08), now at rung
> `VERIFIED-LIVE`.** Two are NOT AVAILABLE (R-01 unresolvable, R-02 gated OFF).
> Five are NOT TEAM RAILS (R-03, R-10, R-11, R-13, R-14). **Eight** are RESERVED
> to the operator (R-04, R-05, R-06, R-07, R-12, **R-17, R-18, R-19**). One is
> real but operator-dependent and cannot discharge rung 2 (R-15). One is UNKNOWN
> and carried (R-16 / UV-P-4). **One rail class (R-19) is now expressible by §2
> but not scoreable by it, pending UV-P-4 (§2.1).** **One** rail requires a build
> before it could be evaluated (R-09, a new channel) — ✦ **corrected: R-04 no
> longer belongs in that set.**

---

## §4 CR-1, restated — and its reach over what it did not enumerate

### §4.1 The restatement (verbatim from shape `:415-426`, unmodified)

> **All three write classes into the live Asana board are OPERATOR-RESERVED.**
> […] **Therefore this initiative is READ-ONLY with respect to the Asana board.**
> "Deliver the insight as an Asana comment / task / custom field" is **out of
> scope at shape altitude.** Changing that requires a **new operator ruling**
> (§10 OS-6), not a shape decision.

**This artifact proposes no Asana-native rail.** R-04, R-05, R-06 and R-07 are
recorded as RESERVED, never as available. Any later proposal of one **HALTS that
sprint** and routes to **OS-6** as a ruling request (K-SW-4, shape `:1439`).

### §4.2 The classes CR-1 did not enumerate — the MEASURED surface

**✦ REWRITTEN REVISION 2 under C-5.** Revision 1 illustrated the unenumerated
classes with *"external attachments, adding a follower, project status updates"*
— a list that points **outward** to mostly-unbuilt verbs while the large **built**
write surface sits inside the same route tree. That understated the fence's reach
by an order of magnitude. The illustrative list is replaced with the codebase's
own machine-readable census.

**The probe** (re-run from this seat this dispatch, SVR-S3-17):
`grep -rn '"type": "asana_api"' src/autom8_asana/api/routes/` → **26 matches
across 8 modules.** This marker is the codebase's own declaration that an
endpoint writes to Asana; it is the right instrument for this question and it is
what a directory-scoped symbol grep should have been (§3.1.1).

| module | n | note |
|---|---|---|
| `tasks.py` | **10** | create, update (**R-17**), delete, duplicate, tags ±, section move, assignee, projects ± |
| `projects.py` | **5** | create, update (**R-18**), delete, members ± |
| `sections.py` | **5** | create, update, delete, add-task, reorder |
| `intake_create.py` | **2** | targets `business_task`, `process_task` |
| `entity_write.py` | **1** | `:184` PATCH — **the R-06 row** |
| `intake_custom_fields.py` | **1** | `:46` POST, target `task_custom_fields` — **same-class sibling of R-06, unnamed in revision 1; now R-19** |
| `receipts.py` | **1** | `:85` POST, target `business_task_comment` — **the R-04 row, §3.1** |
| `workflows.py` | **1** | `:250` POST invoke, target `task` |
| **total** | **26** | all mounted at `main.py:456-492` |

Beyond the census, verbs with **no route** in this repo: **external attachments**
(R-07, `attachments.py:340` client-layer only) and **project status updates**
(`grep status_update src/` returns only *model* fields at
`models/project.py:89-91`, `models/goal.py:148`, `models/portfolio.py:78`, i.e.
read-side — **re-confirmed by the critic**).

These are **NOT open doors**, on three independent grounds:

1. **The consolidated clause is categorical, not enumerative** — *"READ-ONLY
   with respect to the Asana board"* (shape `:423`). A write class absent from
   the enumeration is still a write.
2. **The general principle generalises** — every Asana write decomposes into a
   reversible **record** and an irretractable **broadcast** (shape `:350-359`).
   An attachment, a follower add, and a status update all fire notifications.
   Gate (a) binds on the broadcast in each case.
3. **The `asana-mcp-v1:209` fence is itself categorical** — *"No write verb
   beyond `add_tag` / `mark_complete` / push-save — any addition is
   operator-reserved."* Every class above is "beyond".

> **Recorded so the enumeration is never mistaken for the boundary.** The
> boundary is `READ-ONLY`. The door for **any** Asana write class, enumerated or
> not, is **OS-6** — an operator ruling, never a sprint's decision.
>
> ✦ **And now with the size of what it holds:** the boundary stands in front of
> **26 built, mounted, declared Asana-write endpoints** — not two, and not the
> handful of unbuilt verbs revision 1's illustrative list pointed at. Ground 1's
> categorical form is what makes this survivable: **no enumeration this artifact
> could write would have been complete, which is precisely why CR-1 is not an
> enumeration.**

### §4.2.1 Ground 2 repaired — where record/broadcast comes apart

**✦ ADDED REVISION 2 under C-6.** Ground 2 above asserts that *every* Asana
write decomposes into a reversible **record** and an irretractable **broadcast**
(shape `:350-359`), and that gate (a) binds on the broadcast in each case. The
critic found the one place that decomposition genuinely comes apart, and it is
the class revision 1 never named: **update-in-place** (R-17, R-18).

- **A create** (task, comment) produces a record **and** a new object that fans
  out — a work item into someone's My Tasks, a comment into a follower's inbox.
  Both limbs fire together.
- **An update-in-place** (`notes` on an existing task or project) produces the
  record limb in full, while its broadcast limb is **at minimum different in
  kind**: no new object comes into existence, and the surface's audience is
  whoever was already attached to it.
- **A pull-shaped write** (R-19: a custom-field value under an existing board
  view) is the limit case: record limb in full, broadcast limb plausibly **zero**
  — nothing is sent to anyone; the board simply reads differently.

**How much softer, this artifact does not know and will not assert.** That is a
fact about Asana's notification semantics, not about this repo, and the one
in-repo receipt on the R-17 route warns in the *opposite* direction for a
neighbouring field (`tasks.py:272-273`, `completed=true` may trigger Rules
automations). Carried as **UV-P-S3-5**, `[INFERRED — WEAK]`.

**What follows regardless — and this is the part that binds:**

1. **Ground 2 is now a spectrum, not a binary**, and a decision that turns on
   "how loud is the broadcast" can no longer be read off the decomposition
   alone. Any future OS-6 request must state *which* limb it is asking about.
2. **No verdict moves.** Ground 1 (categorical `READ-ONLY`) and ground 3 (the
   categorical `asana-mcp-v1:209` fence) each independently catch R-17, R-18 and
   R-19 without needing ground 2 at all. **Ground 2 becoming softer at one class
   costs the fence nothing, because the fence was never resting on it alone.**
   That over-determination is a design property of CR-1, and it is why this
   finding is a refinement rather than a breach.
3. **The operator deciding OS-6 deserves to know the fenced set contains options
   with a softer broadcast profile than "create a task."** Revision 1 presented
   the fenced set as uniformly broadcast-shaped. It is not.

### §4.3 ✦ The gate on those 26 endpoints is AUTHENTICATION, not AUTHORIZATION

**ADDED REVISION 2 under C-5.** Revision 1 described R-05's auth as
*"`AsanaClientDualMode`"* and R-06's as *"gated `Depends(require_service_claims)`
(S2S-only)"*. **Both statements are true and both understate.** The critic walked
the chain revision 1 did not, and its finding is sharper than anything revision 1
produced. I re-walked every hop from this seat before adopting it.

**What is NOT the finding** — and this matters, because the obvious suspicion is
the wrong one:

> **PAT mode is not an exposure.** `dependencies.py:140-149` returns
> `AuthContext(mode=auth_mode, asana_pat=token)` — the caller's own token, passed
> through unchanged. The only checks are structural
> (`_extract_bearer_token`, `dependencies.py:92-105`: header present,
> `Bearer ` prefix, non-empty, `len(token) >= 10`). The service validates
> nothing and Asana enforces. **A PAT-mode caller gets exactly the privileges it
> already had; the route is a proxy.** The critic tried to make this material and
> failed. Recorded so a later seat does not re-litigate it.

**What IS the finding**, in four receipted steps:

1. **The router decorator is not the gate.** `tasks.py:64` builds its router via
   `pat_router(...)`, and that factory is documented as metadata-only:
   `api/routes/_security.py:10-13` — *"The `auto_error=False` setting ensures
   SecureRouters only inject OpenAPI metadata without performing runtime auth
   checks -- runtime auth is handled by the existing auth dependencies."*
2. **A fleet JWT lends the caller the bot PAT.** `auth/dual_mode.py:55-58`
   branches on a **dot count** (2 dots → JWT). On the JWT limb the service
   substitutes a service-held credential: `auth/bot_pat.py:56-58` — *"It's the
   single credential that autom8_asana uses to call the Asana API **on behalf of
   all S2S callers**."* Both write paths then use it verbatim:
   `entity_write.py:271` and `receipts.py:163`, each
   `async with AsanaClient(token=auth_context.asana_pat)`. **A JWT caller needs
   no Asana credential at all — it borrows the bot's board privileges.**
3. **`require_service_claims` performs no authorization.** `internal.py:83-161`
   rejects PATs (`SERVICE_TOKEN_REQUIRED`, `:114-118`), validates signature /
   expiry / issuer plus a fleet audience (`jwt_validator.py:83`,
   `audience="https://api.autom8y.io"`), and returns
   `ServiceClaims(sub, service_name, scope, permissions)` (`:155-160`). **It
   checks no permission, no scope, and no per-service allowlist.**
4. **The routes add none.** In `entity_write.py`, `claims` is referenced at
   exactly `:231` and `:362` — **both logging** (`"caller_service":
   claims.service_name`). ✦ **I extend the critic's audit to the R-04 route it
   did not check, and it is the same**: `receipts.py:135` and `:219`, both
   `"caller_service": claims.service_name`, both logging. **Two of the three
   write classes are confirmed authorization-free by direct file audit.**

**And the contrast that makes this a finding rather than a fleet limitation** —
the codebase *has* fine-grained authorization and uses it one file away:

> `api/routes/admin.py:456` — `if SUPER_ADMIN_PERMISSION not in claims.permissions:`
> under the comment *"Super-admin gate (Bedrock W4C-P3 / SEC-DT-10): only
> ServiceAccounts provisioned with the canonical `admin:access` permission may
> purge the fleet-wide cache. All other authenticated S2S callers are rejected
> with 403"* (`:452-455`).

`ServiceClaims.permissions` exists for precisely this (`internal.py:39-43`).

> **Plain statement.** **A cache-refresh is permission-gated. An Asana board
> write is not.** R-04 and R-06 are reachable by *any* holder of a valid,
> unexpired fleet service JWT bearing audience `https://api.autom8y.io` — not
> "the entity-writer service," any fleet service account — and the route then
> executes the write with the bot PAT's board privileges. **The gate is fleet
> membership, not authorization.**

**Two mitigations I checked and will not suppress**: both routers carry
`include_in_schema=False` (`entity_write.py:54`, `receipts.py:82`), so they are
absent from the published OpenAPI document — **that is discoverability, not
access control**; the routers are mounted (`main.py:487`, `:491`) and route
normally. And **network reachability is unestablished** — `terraform/services/asana/`
in this repo contains only alarm definitions (**UV-P-C-2**).

**The open half, carried unclosed and deliberately unprobed**: whether an agent
seat in this fleet can *obtain* such a JWT is a fact about credential
distribution, not about this repo's code. **Neither the critic nor I probed it,
because probing it means handling live credentials.** **UV-P-C-1**, routed to the
**security** rite (§10, O-H).

**Why this belongs in a rails artifact at all.** It is the reason §3.1 exists,
at its true strength: **CR-1 is a PROCESS fence standing exactly where a
TECHNICAL one does not.** A later seat that reads "S2S-only" as "a named peer
service, therefore effectively closed" would conclude the fence is belt-and-braces.
It is not. Remove CR-1 and the remaining barrier to an Asana board write is
membership in the fleet — which this initiative's own services have. **The fence
is not redundant with the auth layer; it is doing work the auth layer does not
do.**

---

## §5 The `#account-health` design question — how a readout stays distinguishable

**The channel is NOT dark.** It carries a post on every abort tick — 6×/day at
`cron(0 */4 * * ? *)`. The design problem is therefore *co-tenancy*, not
silence.

### §5.1 What already occupies the channel (probed, verbatim)

| occupant | header | body glyph | context footer | fallback `text` |
|---|---|---|---|---|
| **readiness abort** (`orchestrator.py:1330-1359`) | `"Account Status Reconciliation -- Data Quality Abort"` | `:warning:` + `*Reconciliation aborted.*` | `"account-status-recon \| readiness gate"` | `f"Account status reconciliation aborted: {readiness.message}"` (`:226`) |
| **all-sources-failed** (`:160-168`) | (same family) | — | — | (distinct, `:151-168`) |
| **full report** (`report.py:264-269`) | `ReportConfig(title="Account Status Reconciliation", service_name="account-status-recon")` | severity glyphs; `:scissors:` for cap | SDK footer | — |

**The collision is exact**: both live occupants render a header beginning
`"Account Status Reconciliation"`. A third message that also opens that way is
indistinguishable at a glance, which is the failure F-5 names (shape `:1426`).

### §5.2 The answer — and it is INHERITED, not invented

The codebase already solved this exact class of problem and wrote down the rule.
`report.py:70-76` (AMENDMENT-001 D-6, W-2), verbatim:

> *"GLYPH … `:scissors:`, NOT `:warning:`. `:warning:` is
> `_severity_emoji(Severity.HIGH)` and already appears in this same summary block
> as ':warning: HIGH: N'. **One glyph carrying two meanings inside one block is a
> legibility defect**; `:scissors:` is unambiguous and reads as truncation."*

**The rule: one token, one meaning, channel-wide.** Applied to a readout, that
yields four requirements — all zero-infrastructure, all satisfiable at authoring
time, no new rail and no operator gate:

| id | requirement | why it is forced |
|---|---|---|
| **D-1** | The readout's **header block MUST NOT begin with `"Account Status Reconciliation"`** | Both live occupants do. Header is the first and largest visual token |
| **D-2** | The readout's **glyph MUST be unused in this channel** — not `:warning:` (already `Severity.HIGH`), not `:scissors:` (already cap-truncation), not the SDK severity glyphs | Direct application of the D-6 rule above. A readout that reuses `:warning:` reads as an alert |
| **D-3** | The **context footer MUST name a distinct producer** — not `"account-status-recon \| readiness gate"` | The footer is the channel's existing provenance line; reusing it attributes the readout to the aborting service |
| **D-4** | The **fallback `text` MUST be distinct** and must not open with `"Account status reconciliation…"` | `text` is the mobile/notification line — the *only* thing many readers see. `_safe_slack_post` takes it as a positional arg (`orchestrator.py:1178-1187`), so it is a free design variable |

**D-1..D-4 are jointly sufficient** for glance-level distinguishability at every
surface Slack renders (channel body, notification, mobile preview, search
result). They cost nothing and require nothing from the operator.

### §5.3 Mechanisms considered and REJECTED (enumerated, per shape `:1509`)

| mechanism | disposition | reason |
|---|---|---|
| **Threading the readout under a parent message** (`thread_ts`) | **REJECTED** | The SDK supports it — `autom8y_slack` 0.3.0 `client.py:258-265` (`thread_ts: str \| None = None`) — but `_safe_slack_post` never passes it (`orchestrator.py:1248`: `send_blocks(channel=channel, blocks=blocks, text=text)`). Beyond the build: a readout is **not a reply to an abort**. Threading would subordinate it to the alert stream and hide it from channel skim |
| **A distinct bot display name / app identity** | **REJECTED as unverifiable from this seat** | Same `SLACK_BOT_TOKEN` secret (`main.tf:120-122`). Whether a second app identity exists is a Slack-workspace fact → **UV-P-S3-2** |
| **Retargeting `SLACK_CHANNEL` to a new channel** | **REJECTED** | One value, three call sites (`orchestrator.py:162, :225, :503`). It moves the aborts too — solving co-tenancy by evicting the incumbent |
| **Suppressing abort alerts while the readout runs** | **REJECTED, firmly** | The aborts are the pause's honest signal (P-4 observability-truthful-first). Quieting a truthful alert to make room for a report inverts the priority |
| **A new producer with its own channel** | **NOT REJECTED — deferred to build time** | See §5.4. It does not change today's rail inventory |

### §5.4 The one thing that widens the design space later

The "one channel setting, three call sites" constraint binds **the ASR service**,
not the universe. A **new producer** (which Mission A's board-behaviour readout
would be — it is not verdict-class and does not belong in ASR) would carry its
**own** channel setting and could target its own channel without touching ASR.

Two things follow, and both must be said:

- **It does not make R-09 available today.** It is a build, and the bot must be
  invited to the target channel — an operational act outside this seat
  (UV-P-S3-2).
- **It does not escape §7's reading (b).** *Every* Slack channel has a mutable
  member set. Under a uniformly-applied modal, a new channel is gate-(b)-crossing
  on identical grounds. **There is no Slack channel that escapes reading (b)**
  — which is precisely why §7 is a fork about *autonomy*, not about *which
  channel*.

---

## §6 The 50-block ceiling — inherited constraint and its consequence for length

### §6.1 The constraint, with receipts

| fact | anchor |
|---|---|
| Slack's Block Kit hard limit is **50 blocks per message** | `report.py:4` — *"Reports grouped by severity (FR-19) with 50-block limit (FR-21)"* |
| The truncation site | `report.py:261` — *"FR-21: 50-block limit with truncation."* |
| The SDK's budget constants | `autom8y_reconciliation` 2.3.0 `report.py:21-22` — `DEFAULT_MAX_BLOCKS = 50`, `DEFAULT_RESERVED_BLOCKS = 10` |
| The budget arithmetic | same, `:160` — `available_blocks = max_blocks - reserved_blocks - len(blocks)` |
| **Slack truncates silently** | `report.py:77-82` verbatim — *"Slack's 50-block ceiling can truncate this report's finding sections **with no marker of any kind**. The counts in this summary are complete by construction; the rendered sections may not be."* |

### §6.2 The consequences for readout length — five, and the fifth is a defect

1. **The budget is per message, not per channel.** Sharing `#account-health`
   with the aborts costs the readout **zero** blocks. Co-tenancy (§5) and the
   ceiling (§6) are independent problems; conflating them would over-constrain
   the design. ✦ **REVISION 2: now live-confirmed.** The tick census shows the
   incumbent occupying `block_count: 3` per message, 7/7 ticks. The incumbent
   costs the readout zero blocks, measured rather than reasoned.
   ⚠ **And that is the ONLY thing `block_count: 3` establishes.** It is **not**
   a measurement of framing overhead against the 50-block ceiling. The 3 blocks
   are the abort's *entire* message (`orchestrator.py:1330` `_build_readiness_abort_alert`
   → header + section + context), and the abort path **bypasses the report
   builder outright**:
   `services/account-status-recon/.know/feat/slack-report-delivery.md:40` —
   *"Abort-path alerts … are hand-built 3-block arrays in `orchestrator.py` and
   **bypass `report.py` entirely**."* It therefore touches neither
   `DEFAULT_MAX_BLOCKS` nor `DEFAULT_RESERVED_BLOCKS`, which live in the SDK
   builder the abort never calls. **Item 3's refusal to name an item ceiling
   stands unrelaxed by this datum.**
   ✦ **One genuine refinement it does surface**: §6 presents the ceiling as a
   property of the channel's traffic, but **the incumbent's messages do not pass
   through the capped builder at all.** SA-1 will be the first payload in this
   channel that does. Worth a line in SA-1's brief.
2. **The readout must be BUDGETED, never truncated.** Because truncation is
   silent, an overflow does not *look* like an error — it looks like a shorter
   report. A recurring readout that silently drops its tail is exactly the
   "confidently wrong" failure K-SW-5 exists to prevent (shape `:1440`).
3. **The usable body budget is `50 − reserved − framing`.** On the SDK's own
   defaults that is **40 blocks** before the readout's own header/summary/divider
   framing is subtracted. **This artifact deliberately does not name a maximum
   item count**: it depends on blocks-per-item, which is the generator's design
   choice. **The requirement is that SA-1 declare its budget explicitly** —
   framing blocks, blocks-per-item, and the resulting item ceiling — as a stated
   number, not an emergent one.
4. **Overflow must degrade to complete-by-construction summary + a drill
   pointer**, following the incumbent's own precedent: counts complete, sections
   possibly not, with an explicit `:scissors:` marker. Truncating without the
   marker is the defect the incumbent already fixed; re-introducing it is a
   regression against a solved problem in the same channel.
5. ⚠ **Today, that drill-out terminates in a 404.** The incumbent's pointer
   renders a **bare** `latest.json` at `report.py:81`, `:167`, `:193`, while the
   key is built as `f"{prefix}/{_LATEST_KEY}"` (`verdict_store.py:28, :43, :45`).
   I re-derived this myself; it is NF-1, owned by **S5**.
   ✦ **REVISION 2: CONFIRMED by the rite-disjoint critic, which re-derived it
   independently at `origin/main` and reached the identical three lines and the
   identical write-path key** (critique §4 F-6). It also **tested the opposite
   case** — whether the defect is secretly this sprint's to absorb — and
   concluded it is not: it touches no rail verdict (R-08's availability does not
   depend on the pointer resolving, and R-12 is RESERVED under CR-2 regardless of
   whether its URL is well-formed). **The routing below is endorsed unchanged.**
   I re-resolved all five line anchors at today's `origin/main` (`0c2fc6a5`)
   this dispatch; all five still resolve (SVR-S3-14).
   **Consequence binding on SA-1**: until S5 lands, a readout **may not rely on
   drill-out for completeness**. It must be complete *within* the ceiling, or
   carry a pointer this initiative itself makes resolvable. Recorded as a
   cross-sprint dependency, **not** absorbed — S5 owns the fix.

---

## §7 The §OPEN scope question — BOTH readings, NEITHER assumed

**Status: UNDECIDED IN BOTH DIRECTIONS.** The operator ratified
`RULING-operator-gate-b-modal-2026-08-12.md` (the shape's modal governs gate (b))
and **explicitly excluded** the scope question from that ratification
(`:106-115`, item 1). Under the standing discipline — *"Nothing I don't
explicitly rule on may be recorded as decided"* — this section presents the
decision surface and picks nothing. It is routed to **PT-02**.

**The question**: the modal keys on *"the recipient set is mutable and not under
our control."* Slack `#account-health` has that property — a workspace admin can
add a guest exactly as an Asana admin can add a guest follower. Does the modal
scope to Asana writes, or apply uniformly?

### §7.1 Reading (a) — modal scoped to Asana writes; Slack distinguished

**The claim**: gate (b) fires on board writes on mutable-follower grounds; the
Slack rail is distinguished as an opted-in, internally-controlled channel already
carrying automated posts 6×/day. **Delivery stays autonomous.**

| in favour | against |
|---|---|
| `CHARTER…:55` closes with *"Everything else — INCLUDING reversible decisions that set patterns others will copy — runs autonomously"* — a clause that exists to refuse the "it might matter later" species of argument (the adversary's second ground, `RULING…:49-52`) | It is a **distinction without a stated principle**. Nothing in the modal's own text ("recipient set is mutable and not under our control") is false of a Slack channel. Reading (a) must supply a discriminator the modal does not contain |
| The channel is **opted-in**: a member joins; nobody is fanned-out to by default. Asana's follower notification pushes to an inbox and an e-mail without the recipient acting | ⚠ **Its load-bearing premise is UNVERIFIED from this seat.** "Membership internally controlled" is a Slack-workspace fact I cannot probe (**UV-P-S3-1**). Reading (a) may be right and still rest on an unchecked premise |
| — | ✦ ⚠ **REVISION 2 (C-3): in-repo evidence bearing on that premise, which revision 1 read past.** The deployed producer's own source calls this channel **customer-facing**: `services/account-status-recon/src/account_status_recon/orchestrator.py:1226-1227` (autom8y @ `origin/main`) — *"the wire-call to `send_blocks` is suppressed so an un-ratified shadow baseline cannot post to the **customer-facing channel**."* The only channel `_safe_slack_post` ever targets is `settings.slack_channel` = `#account-health`. **The ambiguity is genuine and this artifact does not resolve it**: in ASR's own vocabulary "customer" may mean the internal business stakeholder — the same feature record calls the feature *"the **only user-facing surface** of the service"* and says *"The business stakeholders who act on anomalies are not engineers"* (`.know/feat/slack-report-delivery.md:30,32`), on which reading "customer-facing" means *the live audience channel*, not *client-reachable*. **Recorded, not adjudicated.** It is a signal on **DEFER-WATCH-2's exact predicate** and it belongs beside UV-P-S3-1. See §7.2 for the same datum in reading (b)'s column, and §9 |
| The channel **already carries 6 autonomous posts/day** and has done so through a production history. Reading (b) would make that pre-existing behaviour retroactively gate-crossing (see §7.3) | The *precedent* of existing autonomous posts is not itself a charter argument. "We already do it" is not "the gate does not fire" |
| Practically: it is the only reading under which this initiative has an autonomous delivery rail at all | That consequence is a cost, not an argument. It must not be smuggled in as a reason |

### §7.2 Reading (b) — modal applied uniformly

**The claim**: gate (b) fires wherever the recipient set is mutable, including
`#account-health`. **Consequence: the only working delivery rail becomes
operator-gated, and every readout needs an operator release per publication.**

| in favour | against |
|---|---|
| **Consistency.** It is the modal applied to its own terms. Reading (a) requires a discriminator that has not yet been stated; reading (b) requires none | It **proves a great deal** (the adversary's OVER-EXTENDED verdict, `RULING…:47`). Under it, essentially any channel with a member list is gate-(b) crossing, which is close to every channel that exists |
| Gate (b) is *"regardless of reversibility"*, so "we can delete the message" is unavailable by construction | ⚠ It reaches **backwards** onto behaviour already in production — see §7.3. A reading that retroactively re-classifies a running system is a heavier ruling than it looks |
| It is the conservative reading, and the charter's sensitive list is deliberately conservative | ⚠ It may make a named success rung structurally unreachable — see §7.4 |
| ✦ **REVISION 2 (C-3): the same `orchestrator.py:1226-1227` datum, in this reading's favour.** The deployed producer's own source calls the target *"the **customer-facing channel**"*. If that phrase means what it literally says, `#account-health` is not merely a channel with a mutable member list — it is a channel the service's own authors classify as facing customers, which is charter §5(b)'s trigger read straight off the code. **The ambiguity stated in §7.1 applies identically here** (ASR may mean the internal business stakeholder), and this artifact resolves it in neither direction. It is filed in both columns because a datum on DEFER-WATCH-2's predicate that appears in only one reading's adverse column is itself a tilt | ⚠ The phrase is a **code comment**, not a probe of the member list. It is evidence about how the service's authors *describe* the channel, not about who is *in* it. It cannot close UV-P-S3-1, and reading (b) does not need it — (b)'s argument is the modal applied to its own terms |
| ✦ **REVISION 2 (C-4): the channel is observed broadcasting RIGHT NOW.** 7/7 ticks posting live during the pause (§7.3). **A surface that is actively broadcasting is a *stronger* candidate for gate-(b) scrutiny than a dormant one**, not a weaker one — the modal keys on live reach, and live reach is now measured rather than inferred | ⚠ Symmetrically, the same observation is the factual base of §7.3's retroactivity cost, which is filed **against** this reading. **The census cuts both ways and neither direction is privileged** |

### §7.3 The consequence neither reading has yet been costed against — **retroactivity**

Under reading (b), the modal's logic does not distinguish *new* autonomous
delivery from *existing* autonomous delivery. The ASR service **already** posts
to `#account-health` autonomously, 6×/day, unattended, today
(`main.tf:108`, `orchestrator.py:223`). If mutable membership makes a Slack post
gate-(b) crossing, that property is **already true of the incumbent**.

> ✦ **REVISION 2 (C-7): this predicate is no longer inferred from cron plus
> code. It is OBSERVED.** `EVIDENCE-tick-terminal-census-2026-08-12.md`:
> **7 ticks, 7 posts, `ok: true`, over 2026-08-11T20:00Z→2026-08-12T20:36Z —
> during the pause.** Every tick emits `event: slack_post` **and**
> `event: report_posted` naming `#account-health`.
>
> **Why `report_posted` means *delivered* and not *attempted*** — I re-derived
> this rather than inheriting it (SVR-S3-15): it sits **inside the `try`, after
> the wire call** (`orchestrator.py:1248` `await slack_client.send_blocks(...)` →
> `:1251` `log.info("report_posted", ...)`), with failures diverting to
> `slack_post_failed` (`:1268`) and `raise ReportError` (`:1296`); `dry_run`
> **returns at `:1246`, before the `try`**, having logged
> `slack_post_suppressed_dry_run` instead; and the SDK raises on Slack's
> HTTP-200-with-`ok:false` (`sdks/python/autom8y-slack/.../client.py:187`
> `if not data.get("ok", False):` → `SlackChannelNotFoundError` `:192`,
> `SlackRateLimitError` `:200`, `SlackAPIError` `:206`; `send_blocks` `:258`
> routes through `_request` `:135`).
>
> ✦ **Bonus discharge nobody claimed**: because `dry_run` returns *before*
> `report_posted` can fire, **the census independently proves `dry_run=False` in
> the deployed configuration** — upgrading revision 1's config-default-plus-
> absent-tfvar *inference* (R-08 receipt, SVR-S3-8) to a live measurement.

**This changes the evidential status of §7.3, and it must not be allowed to
change the tilt.** Retroactivity stops being a hypothetical cost of reading (b)
and becomes a measured one. §7.3 is filed in reading (b)'s **against** column, so
strengthening its factual base strengthens the case against (b) — which the
critic identified as the section's existing lean. **The census is therefore
entered as a FACT that cuts both ways (§7.2 rows, and §7.6 in full), not as
reinforcement of one column.** Revision 1 could not have written the pro-(b)
limb; the datum did not exist.

Two sub-readings, and **this artifact picks neither**:

- **(b-i) Prospective only** — the gate governs *decisions this initiative is
  making*, not behaviour already running under prior decisions. Reading (b) then
  costs one operator release per *new* readout and leaves the aborts alone.
- **(b-ii) Categorical** — the gate is a property of the surface, not of the
  decision's timestamp. Then the incumbent's abort alerts are also
  gate-(b)-crossing, and the operator is being asked a much larger question than
  "may this initiative publish."

**This is a genuine, previously-unnamed decision surface.** It is surfaced here
per shape `:1515` and belongs in the PT-02 briefing beside the primary question.

### §7.4 The consequence for the telos, stated two-sidedly

Rung 2 of the realization predicate is *"two consecutive deliveries on the
readout's own cadence, generation receipts showing no human assembling them"*
(frame `:524-525`).

- **Narrow read**: an operator *release* is not *assembling*. The generator still
  runs unattended; a human presses publish. Rung 2 survives, with an asterisk.
- **Broad read**: a per-publication operator gate puts a human in the delivery
  loop by construction, and rung 2 as written becomes unreachable — the
  initiative would need either an amended predicate or an honest declaration
  that it is operator-triggered rather than recurring (which frame `:464-466`
  already names as a legitimate outcome).

**Not decided here.** Flagged because it means reading (b) is not merely a
friction cost — under the broad read it changes what success can even mean.

> ✦ **REVISION 2 (C-4): the lean in this paragraph is corrected, and the
> reciprocal cost is supplied.** Revision 1 closed §7.4 with *"The operator
> should see that before ruling"* — a sentence attached to a cost of reading (b)
> with **no equivalent attached to any cost of reading (a)**. The critic graded
> that MILD TILT by asymmetric novelty, and it is right: both of revision 1's
> novel contributions (§7.3 retroactivity, §7.4 rung-2) land in (b)'s against
> column, and only one of them carried an imperative to the operator. The
> sentence is withdrawn as an imperative and restated below as one half of a pair.
>
> **The reciprocal cost of reading (a), stated at the same weight:** reading (a)
> **buys rung 2 by asserting a discriminator the modal does not contain**, on a
> premise this seat could not verify (**UV-P-S3-1**) and against which there is
> now an in-repo counter-signal (`orchestrator.py:1226-1227`, §7.1/§7.2). If that
> premise is false — if `#account-health` membership is *not* internally
> controlled — then reading (a) does not merely cost something, it **delivers
> autonomously into a surface the charter's §5(b) would have gated**, and does so
> with no operator in the loop to catch it. **Reading (a)'s failure mode is
> silent; reading (b)'s failure mode is friction.** That asymmetry in *kind* is
> the thing the operator should see, and it belongs beside §7.4's rung-2 cost,
> not beneath it.
>
> **Neither is an argument. Both are consequences. The operator should see the
> pair.**

### §7.5 What is true under BOTH readings

So nothing waits on the ruling that need not:

1. **The rail inventory (§3) is unchanged.** Slack `#account-health` is the only
   available rail either way; the readings differ on whether *using* it is
   autonomous, not on whether it *exists*.
2. **The distinguishability design (§5) is unchanged.** D-1..D-4 apply
   identically to an autonomous post and an operator-released one.
3. **The 50-block ceiling (§6) is unchanged.** It is a Slack property.
4. **CR-1 is unchanged** — over-determined under both readings
   (`RULING…:64-67`).
5. **A new Slack channel escapes neither reading** (§5.4).

> **S3 is therefore complete under either ruling**, and PT-02 inherits a decision
> surface rather than a blocked sprint.

### §7.6 ✦ Staged for PT-02 — the tick census, two-sidedly (C-4)

**ADDED REVISION 2.** C-4's owner is the **PT-02 author**, not this seat. This
section stages the material so C-4 is discharged by *inheritance* rather than by
re-derivation, and so the two-sidedness cannot be lost in transcription.

**The fact, stated neutrally and without inference:**

> Over 2026-08-11T20:00Z → 2026-08-12T20:36Z, the ASR Lambda invoked 7 times on
> its 4-hourly cron. Each invocation emitted `event: slack_post` and
> `event: report_posted` naming channel `#account-health`, `block_count: 3`,
> `abort_reason: readiness_gate_abort`. `report_posted` fires only after
> `send_blocks` returns without raising, and the SDK raises on `ok: false`.
> **Therefore: the channel received 7 successful automated posts in ~24h,
> including throughout the initiative's pause.** Source:
> `.sos/wip/EVIDENCE-tick-terminal-census-2026-08-12.md`, queryId
> `bf15fa66-2ea9-4622-ac30-b82fcb8e4dbc`, read-only, zero mutations.

**How it bears on the ruling — both limbs, equal weight, neither privileged:**

| cuts AGAINST reading (b) | cuts FOR reading (b) |
|---|---|
| A uniform modal now demonstrably re-classifies **observed live traffic**, not hypothetical traffic. §7.3's retroactivity cost is measured, not projected: 7 real posts in the window under examination | The same observation shows the surface is **actively broadcasting right now**, which is precisely the condition the modal keys on. A live, currently-firing autonomous channel is a **stronger** candidate for gate-(b) scrutiny than a dormant one |
| Sub-reading (b-ii) categorical would classify those 7 posts as already gate-(b)-crossing, making the operator's question much larger than *"may this initiative publish"* | Reading (a) would have to distinguish a channel that is *demonstrably* pushing content 6×/day from one that merely *could*. "Opted-in and quiet" is a weaker premise than revision 1 had; "opted-in and broadcasting" is what is actually true |

**What it does NOT establish, and must not be stretched to:**

- **Not** framing-overhead arithmetic. `block_count: 3` is the abort's entire
  hand-built message, bypassing `report.py` and the SDK budget machinery
  (§6.2 item 1). It measures nothing about the 50-block ceiling.
- **Not** that a readout-shaped payload posts successfully. That is a different
  payload class on the exact dimension §6 constrains — **UV-P-C-3**.
- **Not** anything about *who reads* `#account-health`. The census proves
  delivery to a channel, not membership of it. **UV-P-S3-1 remains OPEN**, and
  the `orchestrator.py:1226-1227` counter-signal (§7.1/§7.2) remains unresolved.

**Instruction to the PT-02 author**: carry both columns. A briefing that inherits
only the left column has re-introduced the tilt this section exists to remove.

---

## §8 UV-P register — carried under the Gate-C DEFER-tag pattern

Per `telos-integrity-ref` §3 Gate-C option (c) and SVR §1 RULE-2, each unclosed
item is carried explicitly into the outbound artifact, never dropped.

**[UV-P-4 — the one this sprint's exit criteria name, OPERATOR-OWNED, OPEN]**

> `[UV-P: what non-engineering data surfaces the offers/account team already has (BI tool, sheet, dashboard) that a readout could land in | METHOD: operator statement or a fleet-topology probe beyond this repo | REASON: the referent is outside this repo's read surface by construction. Confirmed still OPEN at RULING-operator-gate-b-modal-2026-08-12.md:126 (item 6, OS-1/OS-2). Guessing it is the exact failure SVR-1/3/4/5 caught four times in the frame and twice more here. Owner: OPERATOR (OS-2). Soft-blocks the EXTERNAL half of this inventory ONLY; the in-repo half (§3 R-01..R-15) is complete without it.]`
> **`[UNATTESTED — DEFER-POST-HANDOFF]`** — carried into PT-01 per shape `:1262`
> (OS-2 → S3 is a **SOFT** edge; making it hard would idle a sprint on an
> operator statement).

**New UV-Ps opened by this dispatch:**

- **UV-P-S3-1** — `[UV-P: whether #account-health's membership is in fact internally controlled, and whether any guest/external account is currently a member | METHOD: Slack workspace admin read (conversations.members + member profile check) | REASON: not probeable from this seat; no Slack API call was made or permitted. This is the LOAD-BEARING premise of §7 reading (a) — reading (a) may be correct and still rest on an unverified fact.]`
- **UV-P-S3-2** — `[UV-P: whether the ASR Slack bot identity can post to any channel other than #account-health, i.e. whether it is a member of a candidate new channel | METHOD: Slack workspace check + one no-op post to a scratch channel | REASON: bot channel membership is a workspace fact, not a code fact. Binds R-09 and §5.4.]`
- **UV-P-S3-3** — `[UV-P: whether the SNS topic autom8y-platform-alerts actually has live Slack + e-mail subscribers | METHOD: aws sns list-subscriptions-by-topic | REASON: the claim is an in-repo terraform comment (observability_alarms.tf:672), not a probe. Non-blocking — R-11 is rejected on category grounds regardless.]`
- **UV-P-S3-4** — ✦ **DISCHARGED 2026-08-12 (C-7)**, per SVR §1 RULE-1
  (consumed-within-initiative: a subsequent artifact in the same initiative
  attached a non-vacuous receipt for the same claim). Original text: *`[UV-P:
  whether abort alerts are landing in #account-health right now | METHOD: one
  channel read, or CloudWatch slack_post_attempt / report_posted event counts
  over 24h | REASON: every §3 R-08 receipt is a claim about CODE and TERRAFORM,
  not about DATA…]`*. **Discharge**:
  `.sos/wip/EVIDENCE-tick-terminal-census-2026-08-12.md` executed **precisely the
  named method** (`report_posted` event counts) over **precisely the named
  window** (24.6h) and answers **precisely the named question** — 7/7 ticks,
  `#account-health`, `ok: true`. The rite-disjoint critic tested the inference
  three ways before accepting it and I re-derived it independently (SVR-S3-15).
  **R-08 rung → `VERIFIED-LIVE`.** ✦ **Second, unclaimed discharge in the same
  evidence**: `dry_run=False` in the deployed configuration, now a live
  measurement rather than a config-default inference (§7.3, §12).

**New UV-Ps opened by REVISION 2:**

- **UV-P-S3-5** — `[UV-P: whether an Asana notes-only update (PUT /api/v1/tasks/{gid} or PUT /api/v1/projects/{gid}) is materially quieter in notification terms than task-CREATE — i.e. how far the record/broadcast decomposition actually comes apart at update-in-place | METHOD: Asana API notification-semantics documentation for story generation on field updates, plus one observed update against a scratch task with a follower | REASON: this is a fact about Asana's product behaviour, not about this repo, and no in-repo receipt establishes it. The nearest in-repo evidence points the OTHER way for a neighbouring field: tasks.py:272-273 warns that completed=true "may trigger Asana Rules automations (notifications, section moves, workflow transitions)". Carried because §4.2.1's ground-2 refinement rests on it. NON-BLOCKING: R-17/R-18/R-19 are RESERVED under §4.2 grounds 1 and 3 regardless of how this resolves — the refinement changes what an OS-6 request must state, not what the fence holds.]`
- **UV-P-C-1** — inherited from the critic, **carried forward UNCLOSED**. `[UV-P: whether an agent seat in this fleet can obtain a valid service JWT (audience https://api.autom8y.io) by following existing documented patterns, and therefore reach POST /v1/receipts, PATCH /api/v1/entity/{type}/{gid} or POST /v1/tasks/{task_gid}/custom-fields without an operator | METHOD: credential-distribution audit across the fleet's service-account issuance path (autom8y-auth), plus a review of agent-seat runtime env injection | REASON: this is a fact about credential distribution, not about this repo's code. Probing it means handling live credentials, which neither the critic nor this seat will do. **This is the open half of the §4.3 security question**: §4.3 establishes the code-side gate is fleet-membership-only; whether fleet membership is reachable from an agent seat is UNESTABLISHED. Route: security rite (O-H).]`
- **UV-P-C-2** — inherited from the critic, **carried forward UNCLOSED**. `[UV-P: the network reachability of the autom8y-asana API — whether the ALB/listener is internal-only or internet-facing, and what SG/WAF sits in front | METHOD: read terraform/services/asana/{alb,ecs,service}.tf in the autom8y monorepo at origin/main, or aws elbv2 describe-load-balancers | REASON: terraform/services/asana/ in THIS repo contains only observability alarm definitions; the service's network infra is defined elsewhere. Bounds the blast radius of §4.3 but does not change the code-side finding. Route: security rite (O-H).]`
- **UV-P-C-3** — opened by the critic at its §5.2, **adopted**. `[UV-P: whether a readout-class payload (SDK-built, multi-block, approaching the 50-block ceiling) posts successfully to #account-health | METHOD: first live readout post, observed via the same report_posted / block_count telemetry | REASON: the tick census proves the transport for a hand-built 3-block abort that bypasses report.py and the SDK budget machinery. The payload class differs from the class §6 constrains. NON-BLOCKING: it cannot be closed before a readout exists, and closing it is SA-1's natural first receipt.]`

**Inherited and still open, not re-derived**: UV-P-1 (was brief #1 delivered),
UV-P-2 (has the team asked for anything), UV-P-3 (bucket live state — the
operator's probe already fired, F-1/F-2).

---

## §9 Dispositions this sprint discharges or informs

| item | source | disposition |
|---|---|---|
| **F-5** — *"the readout can be delivered at all"* | shape `:1426` | **DOES NOT FIRE.** Slack `#account-health` is live (R-08) **and** it can carry a readout distinguishably (§5.2, D-1..D-4). The initiative **has** a delivery channel. ⚠ Its *autonomy* is the open question (§7), which is a different failure than F-5 names |
| **DEFER-WATCH-2** — any rail whose surface a client could reach → HALT + ESCALATE | shape `:1400` | **NOT TRIGGERED by any rail this artifact names as available.** Every client-reachable candidate (R-04..R-07, R-12, **R-17..R-19**) is recorded RESERVED, never proposed. ⚠ **But §7 reading (b) is precisely the claim that R-08 is client-reachable** — so this watch is what routes the §7 question to the operator rather than letting a seat resolve it. ✦ **REVISION 2 (C-3): a signal on this watch's exact predicate is now on the record and unresolved.** The deployed producer's own source calls `#account-health` *"the **customer-facing channel**"* (`orchestrator.py:1226-1227`). **The phrase is genuinely ambiguous** — ASR may mean the internal business stakeholder (`.know/feat/slack-report-delivery.md:30,32`) — and **this artifact resolves it in neither direction.** It does not flip the disposition, because the watch keys on a rail *proposal* and this artifact proposes none; it does mean the operator's two-sided briefing must carry it (§7.1, §7.2). **Remains STANDING** |
| **DEFER-S-5** — rung-3 evidence-capture mechanism (revisit trigger: *S3 exit*) | shape `:1391` | **TRIGGER FIRED; disposition = the Slack branch.** With R-08 the named rail, rung-3 capture is a **threaded or in-channel reply citing a figure**. Capture mechanism: the reply is durable in Slack history and quotable by permalink. **NOT designed here** (rung-3 mechanism is not in S3's exit criteria) — routed to **SA-3/SB-3**, which shape `:1559` already seats against the telos ladder. Recorded as *informed*, not *closed* |
| **K-SW-4** — any Asana-native write proposal HALTS | shape `:1439` | **Not invoked.** No such proposal made. §4.2 extends the fence to the unenumerated classes so a later seat cannot invoke a loophole |
| **NF-1 drill-pointer defect** | shape §2.2, S5 | **NOT absorbed.** Re-derived independently (§6.2 item 5) and recorded as a **constraint on SA-1's overflow design** until S5 lands. S5 keeps ownership |
| **FP-9 / DEFER-S-1** — the initiative's name promises a rail CR-1 reserves | shape `:1387` | ✦ **CORRECTED REVISION 2 (C-2). Confirmed, and sharpened further than revision 1 could see**: **all three** Asana write classes are **built** (§3.1) — not two — across **26 declared write endpoints** (§4.2), each reachable behind an **authentication-only** gate (§4.3). The name therefore promises something that **fully exists, is reachable today, and is held back by governance alone**. Revision 1's "two of three" understated this and is struck. Revisit trigger remains **GATE-FORK (OS-3)** — not this sprint's call |
| ✦ **C-5 security observation** — an Asana board write is reachable on fleet membership alone while a cache-refresh is permission-gated | critique §2.4 / this artifact §4.3 | **ADOPTED and ROUTED, not absorbed.** §4.3 records the finding with receipts and extends the critic's audit to the R-04 route (`receipts.py:135,:219` — logging only, same as `entity_write.py:231,:362`). **This is not a rails decision and this seat does not own it**: routed to the **security** rite as a cross-rite observation, with **UV-P-C-1** (can an agent seat obtain such a JWT?) and **UV-P-C-2** (network reachability) carried **UNCLOSED** and **deliberately unprobed** — probing either means handling live credentials. **O-H** |

---

## §10 What belongs to the OPERATOR

Nothing below is an agent decision. Listed so PT-01/PT-02 inherit a clean set.

| # | item | why it is the operator's | routing |
|---|---|---|---|
| **O-A** | **The §OPEN scope question** — modal scoped to Asana writes (delivery stays autonomous) vs applied uniformly (every publication operator-gated) | Explicitly excluded from today's ratification (`RULING…:113-115`). Presented two-sided at §7; **assumed in neither direction** | **PT-02** |
| **O-B** | **The retroactivity sub-question (§7.3)** — under a uniform modal, are the ASR abort alerts *already* gate-(b) crossing? (b-i) prospective vs (b-ii) categorical | **NEW this dispatch.** Nobody has costed reading (b) against the running system | **PT-02**, beside O-A |
| **O-C** | **The rung-2 consequence (§7.4)** — whether an operator release per publication leaves rung 2 reachable (narrow) or not (broad) | Amending a telos rung is operator-only; the telos is still `status: PROPOSED` (`RULING…:121-122`) | **PT-02** → telos |
| **O-D** | **UV-P-4 (OS-2)** — what non-engineering surfaces the team already has | Outside this repo's read surface. **Carried, not guessed** | **OS-2** |
| **O-E** | **UV-P-S3-1** — is `#account-health` membership actually internally controlled? | Slack workspace fact; no Slack call is permitted from this seat. **Load-bearing for reading (a)** | **PT-02** with O-A |
| **O-F** | **Any Asana-native rail, ever** — including the classes CR-1 did not enumerate (§4.2: **26 built write endpoints**, plus the update-in-place and pull-shaped classes at R-17/R-18/R-19) | CR-1 + K-SW-4: a new operator ruling, never a shape or sprint decision. ✦ **REVISION 2**: any OS-6 request must now state **which limb** of the record/broadcast decomposition it is asking about (§4.2.1) | **OS-6** |
| **O-G** | **R-12** — making the verdict record reachable by a non-engineer | CR-2, charter §5(b) security/credentials | **OS-7** |
| **O-H** ✦ | **The §4.3 authorization finding** — an Asana board write is reachable on **fleet membership alone** (`require_service_claims` is authentication-only) while a cache-refresh is permission-gated (`admin.py:456`). Plus **UV-P-C-1** (can an agent seat obtain such a JWT?) and **UV-P-C-2** (network reachability) | **ADDED REVISION 2 under C-5.** Not a rails decision and not an architecture decision — it is a security-posture finding surfaced incidentally by a rail inventory. Both open UV-Ps require handling live credentials or infrastructure this seat is read-only against; **neither was probed, by the critic or by me** | **security rite** (cross-rite observation), operator to route |

---

## §11 SVR ledger — probes I ran in THIS dispatch

Per `structural-verification-receipt` §2.3 (co-emission) and §2.4 (three
mechanical predicates). None of these is inherited.

**SVR-S3-1 (bash-probe — the iris rail does not resolve).**
```yaml
verification_method: bash-probe
source: 'ls .claude/commands/iris.md; ls .claude/agents/iris.md; ari rite pantheon | tail -n +2 | wc -l; ari rite pantheon | grep -ci iris'
command_output_verbatim: '".claude/commands/iris.md": No such file or directory (os error 2)  /  ".claude/agents/iris.md": No such file or directory (os error 2)  /  24  /  0'
exit_code: '2, 2, 0, 1'
claim: "no iris seat is dispatchable from this channel by either primitive — command file or agent file — and the 24-row pantheon contains no matching row, so any design naming iris as a delivery rail names something that cannot be invoked here"
```

**SVR-S3-2 (file-read — the MCP write surface is gated OFF and the launcher never arms it).**
```yaml
verification_method: file-read
source: "mcp/asana_mcp/assembly.py"
line_range: "L53-L54"
marker_token: "ASANA_MCP_ENABLE_WRITE_SURFACE (default OFF) — attaches nothing while off."
claim: "the composite write tool attaches zero surface under the default environment, so no Asana write can traverse MCP without an environment change nobody has made"
```
Corroborated: `mcp/serve_stdio.py:26` — *"…(default OFF); this launcher never sets it."*; `:60` reads the flag with a `""` default.

**SVR-S3-3 (file-read — MCP is an agent transport under a promotion fence).**
```yaml
verification_method: file-read
source: "mcp/README.md"
line_range: "L3-L4"
marker_token: "REFERENCE / THROWAWAY POSTURE. This is a proof-of-concept, NOT production"
claim: "the sidecar's own canonical document disclaims production status and forbids promotion pending a charter probe, so naming it a team delivery channel would breach a standing fence in addition to failing the non-engineering-reader test"
```

**SVR-S3-4 (bash-probe) — ✦ RETRACTED REVISION 2. The receipt is TRUE; the claim it carried is FALSE.**

The probe reproduces exactly (I re-ran it this dispatch; the critic re-ran it
independently; three runs, identical result). **The claim built on it was
false** — see §3.1.1. Retained verbatim, struck-through in substance, because
a retracted receipt teaches more than a deleted one.

```yaml
verification_method: bash-probe
source: 'grep -rn "create_comment" src/autom8_asana/api/ mcp/'
command_output_verbatim: "(no output)"
exit_code: 1
claim_RETRACTED: "the comment-creation verb is confined to the SDK client layer; neither the HTTP surface nor the MCP surface exposes it, so delivering an insight as an Asana comment is unbuilt work rather than a gated feature"
retraction_reason: >-
  The probe tests where the TOKEN `create_comment` appears under two
  directories. It does not test where the CAPABILITY is reachable. The route
  POST /v1/receipts reaches the verb by CALLING through services/, which the
  probe's directory scope excludes. Superseded by SVR-S3-13.
claim_CORRECTED: "the literal token `create_comment` does not appear under src/autom8_asana/api/ or mcp/ — which is a fact about those two directories and NOT evidence that comment-CREATE is unexposed"
```

**SVR-S3-5 (file-read — Asana task-CREATE IS exposed at the HTTP API).**
```yaml
verification_method: file-read
source: "src/autom8_asana/api/routes/tasks.py"
line_range: "L181-L183"
marker_token: '@router.post(\n    "",\n    summary="Create a task",'
claim: "unlike comment-CREATE, task creation is a built and reachable route, so CR-1's reservation of this class rests entirely on the charter gates and the mcp-v1 fence rather than on the class being unbuilt"
```

**SVR-S3-6 (file-read — entity/custom-field write IS exposed, S2S-gated).**
```yaml
verification_method: file-read
source: "src/autom8_asana/api/routes/entity_write.py"
line_range: "L184-L185"
marker_token: '@router.patch(\n    "/{entity_type}/{gid}",'
claim: "the entity field-write route exists behind service-claims auth, so the custom-field write class is likewise built and reachable and its reservation is a governance fence rather than an absence"
```

**SVR-S3-7 (file-read — the write-verb fence is categorical).**
```yaml
verification_method: file-read
source: ".sos/wip/frames/asana-mcp-v1.md"
line_range: "L209-L210"
marker_token: "No write verb beyond add_tag / mark_complete / push-save — any addition is"
claim: "the ratified fence reserves additions by class rather than by enumeration, so write classes CR-1 did not name individually are nonetheless operator-reserved"
```

**SVR-S3-8 (bash-probe — the Slack rail is armed, scheduled, and not suppressed).**
```yaml
verification_method: bash-probe
source: 'git show origin/main:terraform/services/account-status-recon/main.tf | grep -n "schedule_expression\|SLACK_CHANNEL"; git show origin/main:services/account-status-recon/src/account_status_recon/config.py | grep -n -A6 dry_run'
command_output_verbatim: '108:  schedule_expression = "cron(0 */4 * * ? *)"  /  135:    SLACK_CHANNEL                        = var.slack_channel  /  210:    dry_run: bool = Field(  211-        default=False,'
exit_code: 0
claim: "the reconciliation lambda fires six times a day with the channel wired from a terraform variable and shadow-mode off by default, and production.tfvars sets no override, so Slack egress is armed in the deployed configuration"
```

**SVR-S3-9 (file-read — the co-tenancy collision is exact).**
```yaml
verification_method: file-read
source: "services/account-status-recon/src/account_status_recon/orchestrator.py (autom8y @ origin/main 0e60e0f5)"
line_range: "L1338-L1341"
marker_token: '"text": "Account Status Reconciliation -- Data Quality Abort",'
claim: "the incumbent abort message opens with the same title stem the full report's ReportConfig uses, so a third message reusing that stem would be indistinguishable at glance level and the readout must differentiate on header, glyph, footer and fallback text"
```

**SVR-S3-10 (file-read — the block budget and the silent-truncation property).**
```yaml
verification_method: file-read
source: "services/account-status-recon/src/account_status_recon/report.py (autom8y @ origin/main 0e60e0f5)"
line_range: "L77-L79"
marker_token: "Slack's 50-block ceiling can truncate this report's finding sections with no marker of any kind"
claim: "overflow past the ceiling is invisible to the reader rather than error-signalled, so a recurring readout must budget its blocks up front instead of relying on truncation behaviour"
```
Corroborated in the SDK: `autom8y_reconciliation` 2.3.0 `report.py:21-22`
(`DEFAULT_MAX_BLOCKS = 50`, `DEFAULT_RESERVED_BLOCKS = 10`) and `:160`
(`available_blocks = max_blocks - reserved_blocks - len(blocks)`).

**SVR-S3-11 (bash-probe — the O-11 read-surface hazard is LIVE in this working tree).**
```yaml
verification_method: bash-probe
source: 'cd …/autom8y && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git rev-parse origin/main'
command_output_verbatim: 'fix/wss-wildcard-scope-bypass-closure  /  cd24d61f07fcb670472a60c55a95f1c57a29f786  /  0e60e0f530eea0f6bbee955b509dc0ce038b9d5c'
exit_code: 0
claim: "the autom8y checkout sits on an unrelated feature branch whose tip differs from the published main, so every monorepo fact in this artifact was read through git show origin/main rather than from the working tree, per the standing read-surface discipline"
```

**SVR-S3-12 (file-read — the NF-1 pointer defect, independently re-derived).**
```yaml
verification_method: file-read
source: "services/account-status-recon/src/account_status_recon/verdict_store.py (autom8y @ origin/main 0e60e0f5)"
line_range: "L42-L45"
marker_token: 'def latest_pointer_key(prefix: str) -> str:\n    """Key of the latest-pointer manifest."""\n    return f"{prefix}/{_LATEST_KEY}"'
claim: "the pointer key is prefix-qualified at the write path while the Slack renderer emits the bare filename at three sites, so the overflow drill-out path this artifact would otherwise rely on resolves to nothing until the S5 fix lands"
```
✦ **REVISION 2**: the pinned SHA `0e60e0f5` in SVR-S3-9/10/12 is restated as
*"read at `origin/main` on 2026-08-12"*. Main has advanced twice since revision 1
(`0e60e0f5` → `7bbb418e` → `0c2fc6a5`); every cited anchor still resolves
(SVR-S3-14), but a pinned SHA in a same-day artifact is a re-verification hazard,
not a receipt-strengthener.

---

### §11.1 ✦ REVISION 2 probes

**SVR-S3-13 (bash-probe — comment-CREATE IS built, mounted and reachable; supersedes SVR-S3-4's claim).**
```yaml
verification_method: bash-probe
source: 'grep -n "async with AsanaClient\|await service.thread_receipt\|@router.post\|^router = \|require_service_claims\|claims" src/autom8_asana/api/routes/receipts.py; grep -n "create_comment_async" src/autom8_asana/services/receipts_service.py'
command_output_verbatim: '82:router = s2s_router(prefix="/v1", tags=["receipts"], include_in_schema=False)  /  85:@router.post(  /  103:    claims: Annotated[ServiceClaims, Depends(require_service_claims)],  /  135:            "caller_service": claims.service_name,  /  163:        async with AsanaClient(token=auth_context.asana_pat) as client:  /  169:            result = await service.thread_receipt(  /  219:            "caller_service": claims.service_name,  /  [receipts_service.py] 346:        story = await self._client.stories.create_comment_async(task=business_gid, text=text)'
exit_code: 0
claim: "the S2S-mounted receipts route terminates in the Asana comment-creation verb by calling through the service layer, so the Asana write class revision 1 recorded as unbuilt is in fact built and reachable, and the fence rather than the absence of code is what holds it"
```

**SVR-S3-14 (bash-probe — the monorepo read surface drifted twice and every citation still resolves).**
```yaml
verification_method: bash-probe
source: 'cd …/autom8y && git rev-parse --abbrev-ref HEAD && git rev-parse HEAD && git rev-parse origin/main && git merge-base --is-ancestor HEAD origin/main'
command_output_verbatim: 'fix/wss-wildcard-scope-bypass-closure  /  29724c2b204db680c43256420b712502a9b3a93a  /  0c2fc6a5df49919717cede66ad550b93f19d742e  /  NOT-AN-ANCESTOR'
exit_code: 1
claim: "the monorepo checkout still sits on a branch that is not an ancestor of the published main, and main itself advanced twice within one day, so every monorepo anchor in this artifact was re-resolved through git show origin/main in this dispatch rather than trusted from the prior revision"
```

**SVR-S3-15 (file-read — `report_posted` is a delivery event, not an attempt event).**
```yaml
verification_method: file-read
source: "services/account-status-recon/src/account_status_recon/orchestrator.py (autom8y, read at origin/main on 2026-08-12)"
line_range: "L1246-L1251"
marker_token: "return\n    try:\n        await slack_client.send_blocks(channel=channel, blocks=blocks, text=text)"
claim: "the dry-run limb exits before the wire call and the success log sits inside the try after send_blocks returns, so the census event proves an accepted post rather than an egress attempt, and it simultaneously proves the deployed configuration is not in dry-run"
```
Corroborated: failure diverts to `slack_post_failed` (`:1268`) and
`raise ReportError` (`:1296`); the SDK raises on HTTP-200-with-`ok:false`
(`sdks/python/autom8y-slack/src/autom8y_slack/client.py:187`
`if not data.get("ok", False):`).

**SVR-S3-16 (bash-probe — R-01 and R-02 re-probed under revision 2; both reproduce).**
```yaml
verification_method: bash-probe
source: 'ls .claude/commands/iris.md; ls .claude/commands/ | grep -i iris; sed -n "53,54p" mcp/asana_mcp/assembly.py'
command_output_verbatim: '".claude/commands/iris.md": No such file or directory (os error 2)  /  iris-attestation.md  /  # EXPOSURE-GATED (W-5 / GATE-BW): register() self-gates on  /  # ASANA_MCP_ENABLE_WRITE_SURFACE (default OFF) — attaches nothing while off.'
exit_code: 2
claim: "the two NOT-AVAILABLE verdicts rest on conditions that are still true at this revision, so the corrections applied elsewhere in this artifact do not silently rehabilitate a rail that was rejected on unrelated grounds"
```

**SVR-S3-17 (bash-probe — the declared Asana-write surface, measured).**
```yaml
verification_method: bash-probe
source: "grep -rn '\"type\": \"asana_api\"' src/autom8_asana/api/routes/ | awk -F: '{print $1}' | sort | uniq -c | sort -rn"
command_output_verbatim: '10 tasks.py  /  5 sections.py  /  5 projects.py  /  2 intake_create.py  /  1 workflows.py  /  1 receipts.py  /  1 intake_custom_fields.py  /  1 entity_write.py  /  [total] 26'
exit_code: 0
claim: "the codebase's own machine-readable side-effect marker declares twenty-six Asana-write endpoints across eight route modules, so the fence CR-1 states categorically stands in front of a surface an order of magnitude larger than revision 1's illustrative enumeration suggested"
```

**SVR-S3-18 (file-read — the S2S gate authenticates but does not authorize).**
```yaml
verification_method: file-read
source: "src/autom8_asana/api/routes/admin.py"
line_range: "L454-L456"
marker_token: "if SUPER_ADMIN_PERMISSION not in claims.permissions:"
claim: "fine-grained permission checking exists in this codebase and is applied to a cache-purge route, while the Asana board-write routes reference their claims object only in log statements, so the difference is a choice made per-route rather than a capability the fleet lacks"
```
Corroborated: `internal.py:155-160` returns `permissions` unchecked;
`entity_write.py:231,:362` and `receipts.py:135,:219` are the complete set of
`claims` references on the two write routes, all four logging.

**SVR-S3-19 (file-read — the update-in-place route carries a notification caution, cutting against the "softer broadcast" inference).**
```yaml
verification_method: file-read
source: "src/autom8_asana/api/routes/tasks.py"
line_range: "L272-L273"
marker_token: "**CAUTION**: Setting completed=true may trigger Asana Rules automations"
claim: "the same route that carries the notes field warns that a neighbouring field's update can trigger downstream automations, so the claim that update-in-place is a materially quieter broadcast than task-creation is not supported in-repo and is carried as an unverified premise rather than a receipt"
```

---

## §12 Evidence grade and honest rungs

**Grade: MODERATE.** Self-attestation ceiling per `self-ref-evidence-grade-rule`
and shape `:1512`. ✦ **REVISION 2**: the rite-disjoint external critic named for
this sprint — `structure-evaluator` (arch) — **has now run**, verdict
**PASS-WITH-CONDITIONS**. **That does not lift the ceiling, and I decline to
claim it does.** Rite-disjoint critique raises confidence in what the artifact
says; it does not convert file-read evidence into runtime evidence, and the
critic capped itself at MODERATE on the same grounds. **No claim here is STRONG
except one, and it is not mine** — see below.

**Honest rungs:**

| claim class | rung | why not higher |
|---|---|---|
| Rail existence / absence (R-01..R-07, R-13, R-14, **R-17..R-19**) | **VERIFIED-IN-REPO** ✦ *and now rite-disjointly corroborated on the rows the critic re-probed* | Direct file and command probes at the read surface of record. Highest available without a runtime. ⚠ **R-04's revision-1 rung was VERIFIED-IN-REPO and it was WRONG** — the probe was sound and its scope was not (§3.1.1). A rung records probe quality, not correctness |
| Slack rail (R-08) | ✦ **VERIFIED-LIVE** *(was `VERIFIED-IN-CODE-AND-TERRAFORM`)* | **The one rung that moved this revision.** 7/7 ticks observed posting to `#account-health` with `ok: true` over 24.6h. **UV-P-S3-4 DISCHARGED.** ⚠ Scope: proven for the **abort payload class**; a readout-class payload is **UV-P-C-3** |
| Slack egress not suppressed (`dry_run=False`) | ✦ **VERIFIED-LIVE** *(was inference from config default + absent tfvar)* | Second, unclaimed discharge in the same census: `dry_run` returns before `report_posted` can fire, so the event's existence proves the flag's value |
| §4.2 write-surface size (26 endpoints) | **VERIFIED-IN-REPO** | Measured off the codebase's own declaration marker, not enumerated by hand. Revision 1's illustrative list is struck |
| §4.3 authorization finding | **VERIFIED-IN-REPO (code-side only)** | Call chains, decorators and mount points are deterministic and were walked end-to-end. ⚠ **The operationally decisive half is NOT established**: whether an agent seat can obtain a fleet JWT (**UV-P-C-1**) and whether the API is network-reachable (**UV-P-C-2**). Both were **deliberately not probed** — probing means live credentials. A reachability claim that cannot see the network layer or the credential path is capped, and I decline to call it more than this |
| Distinguishability design (§5) | **DESIGNED, UNTESTED** | D-1..D-4 are derived from the codebase's own D-6 rule and are sound on their face; no message has been rendered or posted |
| 50-block ceiling (§6) | **VERIFIED** | Named in code, in the SDK constants, and in the arithmetic. ✦ Refined: the incumbent's messages never traverse the capped builder, so SA-1 will be the first payload in this channel that does |
| §4.2.1 record/broadcast at update-in-place | ✦ **INFERRED — WEAK** | Deliberately **not** rungged higher. The "softer broadcast" property is a fact about Asana's notification semantics, not this repo, and the nearest in-repo receipt (`tasks.py:272-273`) points the other way for a neighbouring field. **UV-P-S3-5** |
| §7 two-sided presentation | **PRESENTED, UNDECIDED** | By construction. Deciding it here would be the failure this section exists to prevent. ✦ Revision 2 corrects the MILD TILT the critic graded (§7.4) and files the `orchestrator.py:1226-1227` signal in **both** columns (§7.1, §7.2) |
| The tick census itself (§7.3, §7.6) | **STRONG — and it is NOT mine** | Produced rite-disjointly by the main thread, attacked by the arch critic on three independent inference paths, and re-derived by me at the code level (SVR-S3-15). I graded it by trying to break it, not by producing it. **The one STRONG strand in this record, and the artifact does not get to claim it as self-attestation** |
| UV-P-4 | **OPEN — OPERATOR** | Carried under the Gate-C DEFER-tag. **Not guessed.** ✦ Revision 2 finds it load-bearing in a **second** place: it hard-blocks scoring of the pull-shaped rail class (§2.1, R-19) |
| UV-P-C-1 / UV-P-C-2 | **OPEN — carried UNCLOSED, deliberately unprobed** | Inherited from the critic and **not** discharged here. Probing either requires handling live credentials or infrastructure this seat is read-only against. **O-H → security rite** |

**Anti-falsifier acknowledged** (shape `:1444-1451`): this artifact naming a
rail is **not** a readout delivered, and a readout delivered is **not** a readout
read. Nothing here advances any predicate rung. ✦ **Revision 2 adds a second
anti-falsifier**: surviving a rite-disjoint critique is not the same as being
correct. Three of the critic's eight attacks landed, and the sharpest of them
(§3.1.1) landed on a claim revision 1 had marked **VERIFIED-IN-REPO** with a
receipt that reproduced exactly, three times. **A true receipt is not a true
claim.** That is the sprint's transferable lesson and it outweighs any of its
findings.

**Live-world discipline, revision 2**: zero writes of any class. No Asana call,
no Slack post, no Lambda invoke, no AWS mutation, no terraform action, no git
mutation. Every probe in §11.1 is a file read, a grep, or a read-only git
plumbing command. Under CR-1 the three write classes are operator-reserved, and
verifying a rail by exercising it is the one failure this sprint cannot absorb.

**Next**: ✦ critique **RUN**, conditions **DISPOSITIONED** above with no silent
drops (C-1/C-2/C-3/C-5/C-6/C-7 discharged here; **C-4 routed to the PT-02 author
with its material staged verbatim at §7.6**) → **PT-01** fan-in, carrying
**O-A..O-H** to **PT-02**, and **O-H** onward to the **security** rite.
