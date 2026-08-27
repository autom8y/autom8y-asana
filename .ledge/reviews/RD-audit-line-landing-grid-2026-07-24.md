---
type: review
artifact: RD-audit-line-landing-grid
initiative: fleet-delegation-phase2
sprint: RD (the re-derivation option grid — the spine, R24's order)
rite: arch
lead: structure-evaluator
supporting: [topology-cartographer (surface census), arch-adversary (internal two-sided kill-proof)]
external_critic: security (security-reviewer, threat-modeler) — rite-disjoint, at CP-1/CP-2
landing_mode: SURFACE — staged into the PK-2 R4 packet; MERGES NOTHING, FLIPS NOTHING
status: SURFACED — working-tree only; staged for operator post-ruling disposition; NOT committed (R29 gate un-pre-empted)
date: 2026-07-24
source_anchor: "autom8y-asana origin/main = dfdb84a38e71496e3b3a577935aa72039f37b5df (dfdb84a3); local main FROZEN pre-epic — committed truth read via `git show origin/main:<path>` ONLY"
governing: "R28 admissible-readings (RULINGS-operator-interview-fleet-constitution-2026-07-24.md @origin/main :124-148); R25 effect-not-repo; R29 identity gate; frame §4-RD; shape §2-RD"
disposition: STAGED — grid REPORTS; operator RULES; RD pre-decides NO conclusion (frame boundary)
self_grade: "MODERATE (self-ref ceiling per self-ref-evidence-grade-rule; external corroboration arrives at CP-1/CP-2 via the security rite-disjoint critic)"
handoff: HANDOFF-rd-grid-to-pk-packet → PK-2
---

# RD — The Re-Derivation Option Grid: "the audit line names that human"

> **What this is.** An adversarial, exhaustive enumeration of EVERY admissible
> landing of the R28 predicate leg *"the audit line names that human (not the
> service)"* — each candidate proven **LANDABLE (with a code receipt)** or
> **KILLED (with a cause of death)**. Killed options STAY in the grid.
> Exhaustiveness is the deliverable; a truncated slate is a frame violation
> (option-enumeration-discipline). This grid **flips nothing**: any landing it
> marks admissible is R29-gated INTO the packet (PK-2), never into main. The
> grid reports the *search space*; the operator rules the *choice*.

## 0. Executive read (said first)

Eighteen candidates are gridded across R28's two admitted readings — **(a)
in-the-business-record**, **(b) durable structured logs** — plus reading **(c)**
(candidates neither the inaugural wave nor the frame named), plus the two
mandated DEAD classes (the MCP-write throwaway; the three constitution-pre-killed
options).

- **13 LANDABLE** (surface is an admissible home for "&lt;human&gt; via &lt;agent&gt;",
  at varying strength; every one conditioned on the SHARED PRECONDITION §2.3).
- **5 KILLED / DEAD** (1 native-attribution kill; 1 MCP-write throwaway; 3
  constitution-pre-killed AS-THE-BAR).

The single most consequential archaeological finding: **the real live audit
path is a FAMILY of per-route structured logs the census missed** — the
flagged `workflow_invoke_api` (`workflows.py:322`) is not a one-off. A
deterministic reconciliation — {routes emitting a `caller_service` structured
log} ∩ {routes declaring an `asana_api` write side-effect} — partitions to
**exactly FIVE** audit-log-family members: `workflows` (C1), `entity_write`
(C2), `intake_create` (C3), `intake_custom_fields` (C5), `receipts` (C6). Every
one records `caller_service` (the service) with **zero** human field. That
family is the strongest reading-(b)-shaped landing because the surface *already
fires on every write* — naming the human there is a field addition to a live
audit line, not a new mechanism. The SAME reconciliation surfaces the inverse
seam: `projects`, `sections`, and route-level `tasks` declare `asana_api` writes
but emit **no** structured audit log — live reading-(a) write surfaces that are
currently un-audited (§3 census-seam note). Re-baselined 16 → 18 at CP-2 on the
security-reviewer's deterministic census gap (C5 + C6 added; DELTA scope).

**The load-bearing decomposition (R28's own):** this grid evaluates the
**audit-LANDING** leg (WHERE the line can durably live). It does NOT evaluate the
**species-CONSUMPTION** leg (HOW the satellite comes to *know* the human) — that
is SP's sprint and is R4-reserved. Every LANDABLE verdict therefore means *"this
surface is an admissible, durable home for the audit line **once SP delivers the
human into context**"* — never *"this works today."* Today no surface names a
human (§2.3 receipt).

## 1. Method & governing terms

### 1.1 R28, verbatim (the bar this grid enumerates against)

> **Selected (verbatim labels):** "In-the-business-record" AND "Structured log
> lines." NOT selected (a ruling): "Fleet-owned durable store" and
> "External-auditor grade" — EXCLUDED as the bar; they may appear in options
> analysis only as optional hardening, never as a REALIZED requirement.
> **Binding terms:** The audit line may land (a) written INTO the business record
> itself — an Asana story/comment/field naming "&lt;human&gt; via &lt;agent&gt;", where the
> work lives, visible to reps — and/or (b) as durable structured log lines naming
> the human, with retention. No new audit database is required by the bar.
> **Consequences:** … The audit-landing leg comes home to this repo, which
> writes stories and structured logs today. The auth-service audit-table path is
> dead as the bar.
> — `RULINGS-operator-interview-fleet-constitution-2026-07-24.md` @origin/main dfdb84a3, R28 :130-148

### 1.2 The three-check false-positive gate (applied to every KILL)

Per the anti-pattern register, a candidate is KILLED only after a **two-sided**
kill-proof (discriminating-canary-doctrine): I state the condition **X** under
which the candidate would PASS, then show **X is structurally false** with a
code receipt. A kill without a stated pass-condition is an assertion, not a
proof. Symmetrically, a LANDABLE verdict carries the receipt proving the surface
exists and can carry free-text/human naming.

### 1.3 Disposition vocabulary

| Token | Meaning |
|---|---|
| **LANDABLE** | The surface is an admissible, durable home for "&lt;human&gt; via &lt;agent&gt;" per R28, conditioned only on the shared §2.3 precondition (an SP/retention matter, not a defect of this surface). Strength annotated: `full` / `partial` / `weak`. |
| **KILLED** | The surface cannot be a bar-satisfying home for a reason **intrinsic to the surface** (two-sided proof in the cause column). |
| **DEAD-AS-BAR** | Excluded by R28 as *the bar*; may appear as **optional hardening** layered under a LANDABLE candidate, never as a REALIZED requirement. |

LANDABLE is **not a recommendation.** It marks admissibility of the *surface*;
the operator rules *which* surface(s) the packet adopts.

## 2. Cross-cutting preconditions (shared by all LIVE candidates — stated once, not repeated per row)

### 2.1 PRE-SP (species consumption) — the human must be *in context* to be named
`AuthContext` is a **3-slot** carrier — `("mode", "asana_pat", "caller_service")`
— and holds no human, business, or actor identity.

```
receipt (file-read @ origin/main dfdb84a3):
  src/autom8_asana/api/dependencies.py:58
  __slots__ = ("mode", "asana_pat", "caller_service")
```
Every reading-(a) write and every reading-(b)/(c) log can only *name* an
identity that is present in the request context. The delegating human enters
context ONLY when SP's species-consumption leg lands (SDK actor-claim modeling +
validator widening) — which is **R4-reserved** (constitution :146-148). This is
the R28 landing-vs-consumption split, not a defect of any surface below.

### 2.2 PRE-D1 (event-triggered actions) — no human token on the event path
The D1 seam ADR (`#266 → 2c91a724`) requires the grammar honor `sub=human /
act=agent` for **both** request- and event-triggered actions. On the
event-triggered path (Asana webhook → automation), there is **no
human-bearing token at all** — the trigger is a platform event. Naming the human
on that path depends wholly on SP's D1 event-triggered mapping and is strictly
weaker than the request path. Flagged per-row where it bites (C4).

### 2.3 Today, NO surface names a human — receipt
A repo-wide scan of every route log for a human principal returns **zero** hits:

```
receipt (bash-probe @ origin/main dfdb84a3):
  git grep -nE 'acting_agent|delegating_user|user_id|human|actor|"sub"|on_behalf' -- 'src/autom8_asana/api/routes/**'
  → 0 audit-field matches (all hits are default_factory / SecureRouter noise)
```
This is the measurement the whole leg exists to change; it is the baseline, not
a candidate.

### 2.4 PRE-RETENTION (readings b/c) — "durable … with retention"
R28(b) requires *"durable structured log lines … with retention."* The asana
service logs to a CloudWatch log group, but **no `aws_cloudwatch_log_group` with
`retention_in_days` is declared in this repo** — the group is an external
variable input:

```
receipt (bash-probe @ origin/main dfdb84a3):
  terraform/services/asana/observability_alarms.tf:324  variable "asana_service_log_group" { … }
  :336  log_group_name = var.asana_service_log_group   # metric filters attached; NO retention_in_days resource in-repo
```
Consequence: every reading-(b)/(c) candidate is durable-sink-present but its
**retention *duration* is an out-of-repo config** the packet must name (§6
Unknown U-1). "With retention" is *achievable* (CloudWatch groups carry a
retention policy) but not *confirmed in-repo* — a precondition, not a kill.

## 3. THE GRID

Legend: strength `full`/`partial`/`weak`; conf = confidence (High = code-anchor +
structural corroboration; Med = partial / out-of-repo dependency).

### Reading (a) — In-the-business-record (Asana story / comment / field / attachment)

| # | Candidate | Disposition | Receipt @ origin/main dfdb84a3 | Cause-of-death (two-sided) / Landing note | Conf |
|---|---|---|---|---|---|
| **A1** | **Story/comment "&lt;human&gt; via &lt;agent&gt;"** on the acted-on object | **LANDABLE** `full` | `clients/stories.py:249/262/275/288/301` `create_comment[_async]`; story `update:158` / `delete:197` are "comment only" (docstrings :167/:198) | Comment body is **free text**, durable in the Asana record, **visible to reps** — R28(a)'s canonical example verbatim. Lands iff §2.1 delivers the human. Highest-fidelity reading-(a) home. | High |
| **A2** | **Task description / notes grammar** (append "&lt;human&gt; via &lt;agent&gt;" to `notes`) | **LANDABLE** `full` | `clients/tasks.py:436/470-471` create `notes`; `update:528`; PUT `/tasks/{gid}` full-state (composite_write header, `tasks.py:246-301`) | `notes` is free-text task description; durable, rep-visible. Nuance: a PUT full-state overwrite can clobber a prior line — append-grammar must be additive (Asana `notes` is last-write-wins), an implementation constraint, not a kill. Lands iff §2.1. | High |
| **A3** | **Custom-field write** naming the human | **LANDABLE** `partial` | `clients/custom_fields.py:218` create; `:320` update; `:398` enum-option; `:613` add_to_project | PASSES IF a dedicated text/enum field ("acting human") is provisioned on the object type. It is a **typed** surface, not free text → requires field provisioning + project linkage; naming grammar is constrained to the field type. Admissible but heavier than A1/A2; better as a *structured* complement. Lands iff §2.1 + field provisioned. | High |
| **A4** | **Attachment / artifact record** naming the human | **LANDABLE** `weak` | `clients/attachments.py` (24 defs): `upload:204`, `upload_from_path:300`, `create_external:388`, `delete:104` | PASSES IF the human-naming lives in the artifact/URL and that counts as "the audit line." The human name sits in **file content/metadata**, not a first-class record field → awkward as the *primary* audit line; fine as **optional hardening** (e.g., a provenance attachment). Not a kill; a low-fidelity home. Lands iff §2.1. | High |
| **A5** | **Rely on Asana's NATIVE actor attribution** (created_by / system stories "X added…") | **KILLED** | write credential = **shared bot PAT**: `api/routes/workflows.py:359` `AsanaClient(token=auth_context.asana_pat)`; `dependencies.py:58` slot `asana_pat` = `get_bot_pat()` (`:239`) | PASSES IF Asana attributes the mutation to the invoking human. It does **not**: every write executes under the **single shared bot PAT**, so Asana's own `created_by` / system stories name the **bot/service account**, never the delegating human — by construction. The naive "let Asana track it" option is dead independent of SP. | High |

### Reading (b) — Durable structured logs (the frame-named surfaces)

| # | Candidate | Disposition | Receipt @ origin/main dfdb84a3 | Cause-of-death (two-sided) / Landing note | Conf |
|---|---|---|---|---|---|
| **B1** | **Wire the DORMANT `S2SAuditLogger`** with human fields | **LANDABLE** `partial` | `auth/audit.py:99` class; entry fields `:51-59` (event/timestamp/request_id/auth_mode/**caller_service**/endpoint/method/status/duration) — **no human field**; singleton `:259`; **zero live callers** (`git grep` → only `auth/__init__.py:26-28` exports) | PASSES IF (i) a human field is added to `S2SAuditEntry`, (ii) live call sites are wired into route handlers, (iii) §2.1 populates it, (iv) §2.4 retention named. Purpose-built audit surface, but **presently inert** — three build steps + two preconditions. Landable, not free. | High |
| **B2** | **Extend the inline auth log** (`auth_mode_jwt`) with a human field | **LANDABLE** `partial` | `api/dependencies.py:253-260` `logger.info("auth_mode_jwt", … caller_service=claims.service_name, scope=claims.scope)`; failure branch `:228` `s2s_jwt_validation_failed` logs **no principal** | PASSES IF a human field is threaded here. But this fires **once per authentication**, not per business action → it records *who authenticated*, not *who acted on which object*. Coarser grain than A1/C1; admissible as a coarse ledger. Lands iff §2.1 + §2.4. | High |
| **B3** | **MCP-layer log at the tool boundary** (10 tool modules) | **LANDABLE** `weak` | `mcp/asana_mcp/tools/` (10 modules @ dfdb84a3); sidecar self-labeled **"REFERENCE / THROWAWAY POSTURE"** (`workflows.py:26,63`) | PASSES IF the sidecar log is in the production audit path with retention. The sidecar is **reference/throwaway** posture and sits *outside* the production service; its logs are the weakest "durable with retention" claim (§2.4 applies to the *service* group, not necessarily the sidecar). Admissible only as optional hardening. Lands iff §2.1 + a *named* sidecar retention posture. | Med |

### Reading (c) — Discovered surfaces (neither the inaugural wave nor the frame named)

| # | Candidate | Disposition | Receipt @ origin/main dfdb84a3 | Cause-of-death (two-sided) / Landing note | Conf |
|---|---|---|---|---|---|
| **C1** | **`workflow_invoke_api` — the LIVE audit log** (the census-missed real audit path) | **LANDABLE** `full` | `api/routes/workflows.py:320-329` — comment `# Audit log (full invocation context)`, `logger.info("workflow_invoke_api", … caller_service=auth_context.caller_service, auth_mode=…)`; completion twin `:400` `workflow_invoke_completed` | PASSES with the **least new mechanism** of any reading-(b) candidate: the audit log **already fires on every invoke**, is already structured, is already self-labeled "Audit log" — naming the human is a **field addition to a live line**, not a new surface. Records the service today; add `acting_agent`/`delegating_user`. Lands iff §2.1 + §2.4. **This is the strongest structured-log home.** | High |
| **C2** | **`entity_write` field-write audit log** (sibling on a WRITE route) | **LANDABLE** `full` | `api/routes/entity_write.py:225` + `:353` `logger.info(… caller_service=claims.service_name)` around `write_entity_fields` (`:195`), Asana write `:271` | Same shape as C1, sited **at the mutation point** of the entity-field write route — arguably the most apt per-action home (the log sits exactly where the record changes). Service-only today; add the human. Proves C1 is a **pattern, not a one-off**. Lands iff §2.1 + §2.4. | High |
| **C3** | **`intake_create` audit log** (sibling on a WRITE route) | **LANDABLE** `full` | `api/routes/intake_create.py:108` `intake_create_business_request` + `:176` `…_complete`, both `extra={… caller_service=claims.service_name}` | Third live instance of the per-route audit-log family, on business-hierarchy creation. Service-only today. Corroborates the family verdict; same disposition as C1/C2. Lands iff §2.1 + §2.4. | High |
| **C5** | **`intake_custom_fields` audit log** (4th family member; CP-2 census gap) | **LANDABLE** `full` | `api/routes/intake_custom_fields.py` POST `/{task_gid}/custom-fields` side-effect `asana_api/task_custom_fields:51`; twins `intake_custom_fields_request:90` + `_complete:149`, both `caller_service=claims.service_name`, zero human; mounted `api/main.py:488` | Distinct from C2/C3 — different path/verb/target (`task_custom_fields`)/event-names → **not subsumable**. Same shape/disposition as C1-C3: service-only today, add the human. Lands iff §2.1 + §2.4. Added at CP-2 (security-reviewer). | High |
| **C6** | **`receipts`/`forwarding_receipt` audit log** (5th family member; CP-2) — ALSO the live in-production embodiment of **A1** | **LANDABLE** `full` | `api/routes/receipts.py` POST `/receipts` side-effect `asana_api/business_task_comment:90`; twins `forwarding_receipt_request:130` + `_complete:210` (`caller_service:135/:219`), zero human; **`result.story_gid` recorded :215**; mounted `api/main.py:490` | **Doubly material:** `forwarding_receipt_complete` records `story_gid` → this route **already writes a story onto the Business task in production**, so it is the single most concrete LIVE instance of **A1** (grid otherwise presents A1 only as an abstract client capability at `clients/stories.py`). Service-only log today; add the human on both the log and the story body. Lands iff §2.1 + §2.4. Added at CP-2. | High |
| **C4** | **Event-triggered dispatch log** (webhook path) | **LANDABLE** `weak` | `api/routes/webhooks.py:173` `logger.info("webhook_…")` in `WebhookDispatcher.dispatch`; V2 extension point (`:6`) | PASSES IF the human is nameable on the **event-triggered** path. Per §2.2 there is **no human-bearing token** on a webhook trigger → naming depends wholly on SP's D1 event-triggered mapping (`#266`). Strictly weaker than the request path; admissible only as the event-path complement. Lands iff §2.1 **and** §2.2 D1 mapping. | Med |

> **Census-seam note — reading-(a) write surfaces that carry NO audit log (CP-2 reconciliation, non-blocking).**
> The §0 reconciliation's INVERSE set — `asana_api` write routes that emit no `caller_service`
> structured log — names three live surfaces audited today only at the client layer, never at the
> route layer: **`api/routes/projects.py`** (`asana_api/project`, writes :221/:270/:333/:462/:508),
> **`api/routes/sections.py`** (`asana_api/section|task`, :97/:146/:196/:246/:298), and route-level
> **`api/routes/tasks.py`** (`asana_api/task`, 10 write ops :191…:786). These are live
> reading-(a)/(A2/A3) write surfaces: any audit-line landing that relies on a structured log
> (readings b/c) does **not** cover them today — they would need the C-family log pattern extended
> onto them, or an in-record (reading-a) line. Named for completeness; **not a distinct numbered
> candidate** (same mechanisms as A1/A2/A3 + the C-family), so the count stays 18.
> Reconciliation receipt (bash-probe @ origin/main dfdb84a3): `git grep -l caller_service --
> src/autom8_asana/api/routes/**` ∩ `git grep -n asana_api -- src/autom8_asana/api/routes/**`
> → audit-log family = {workflows, entity_write, intake_create, intake_custom_fields, receipts}
> (5); write-but-no-log = {projects, sections, tasks} (3); read routes logging `caller_service`
> (side-effects `[]`: admin, exports, fleet_query, intake_resolve, matching, query, resolver,
> resolver_schema, internal) are NOT family members.

### KILLED — the MCP write-throwaway (mandated grid entry)

| # | Candidate | Disposition | Receipt @ origin/main dfdb84a3 | Cause-of-death (two-sided) | Conf |
|---|---|---|---|---|---|
| **K-MCP** | **Armed MCP composite write** (`composite_write.py` + `confirm_gate.py`) as the audit-naming surface | **KILLED** | `composite_write.py:1-6` "**THROWAWAY / REFERENCE-POSTURE PROTOTYPE. NOT production code.**"; exposure gate `:98/:102/:458` `if not write_surface_enabled(ctx): return` (`ASANA_MCP_ENABLE_WRITE_SURFACE`, **default OFF**); backing write via `ctx.http` = **S2S-JWT → shared bot PAT**; `mcp/asana_mcp/tools/workflows.py:26-27,63` "**This ships SURFACE, NOT audit-names-the-human**" | PASSES IF (i) it were production, (ii) exposed by default, and (iii) the write named the human. **All three false:** self-labeled throwaway/reference; gated OFF by default; and even armed the write executes under the **shared bot PAT** (`confirm_gate` gates *whether* to fire, it authors no audit line) → the tool's own docstring declares "NOT audit-names-the-human." Three independent kills; any one suffices. | High |

### DEAD-AS-BAR — pre-killed by the constitution (mandated; R28 exclusions)

| # | Candidate | Disposition | Constitution receipt | Optional-hardening note (permitted) | Conf |
|---|---|---|---|---|---|
| **D-1** | **Fleet-owned durable store AS THE BAR** | **DEAD-AS-BAR** | R28 :130-133 "NOT selected … EXCLUDED as the bar; … only as optional hardening, never as a REALIZED requirement" | MAY appear as optional hardening (e.g., ship the C1-family structured logs onward to a durable store) — **never** as a REALIZED requirement of the leg. | High |
| **D-2** | **External-auditor grade AS THE BAR** | **DEAD-AS-BAR** | R28 :130-133 (same exclusion clause) | MAY appear as optional hardening (an external attester over the logs) — **never** REALIZED-required. | High |
| **D-3** | **Auth-service audit-table path AS THE BAR** | **DEAD-AS-BAR** | R28 :146-147 "The auth-service audit-table path is **dead as the bar**"; supersession register (frame §3 :238-241) | The auth-server already models BOTH species — `services/auth/…/models/audit_log.py:45 acting_agent_id` / `:46 delegating_user_id` (LANE-2 vetted; carried UV-P, cross-repo) — so this path is **optional-hardening-ready** but DEAD as the bar. It is *complementary*, not the leg. | High |

## 4. Live-vs-killed accounting (exhaustiveness receipt)

| Bucket | Count | Members |
|---|---|---|
| **LANDABLE** (admissible surface, §2.3-conditioned) | **13** | A1, A2, A3, A4, B1, B2, B3, C1, C2, C3, C4, C5, C6 |
| — of which `full` strength | 7 | A1, A2, C1, C2, C3, C5, C6 |
| — of which `partial` | 3 | A3, B1, B2 |
| — of which `weak` | 3 | A4, B3, C4 |
| **KILLED** (intrinsic cause) | **2** | A5 (native attribution = bot PAT), K-MCP (throwaway/gated/bot-PAT) |
| **DEAD-AS-BAR** (R28 exclusion) | **3** | D-1, D-2, D-3 |
| **TOTAL gridded** | **18** | — |

**Minimum-viable-slate check (option-enumeration-discipline §5):** ≥3
structurally-distinct mechanisms — YES (in-record write / structured log /
native-attribution / MCP-tool-write / auth-table are categorically distinct);
a no-new-mechanism option — YES (C1: the audit line already fires; naming the
human is a field addition); an externally-prompted option — YES (the C1-family
was surfaced by potnia+pythia; C2/C3/C4 + the A5 kill were discovered by this
sprint's archaeology, and C5/C6 by the CP-2 security-reviewer's reconciliation —
the discipline biting twice, exactly as intended); a delegation option — YES (D-3 auth-table, present
DEAD-as-bar / optional-hardening). Slate is complete, not terminated-by-convention.

## 5. ATAM trade-off surface (for the operator's ruling — not a recommendation)

Per the boundary case in the calibration anchors, coupling/placement must be
evaluated against the quality attribute it serves. The grid does not choose; it
names the trade-offs so PK-2 can present them:

- **Visibility-to-reps ↔ machine-queryability.** Reading (a) (A1/A2) is
  rep-visible where the work lives but not machine-indexed; reading (c) (C1/C2/C3)
  is machine-queryable/structured but invisible to reps. R28 admits **and/or** —
  the two are complementary, not exclusive; the packet may propose both legs.
- **Least-new-mechanism ↔ purpose-built.** C1 (extend a live audit line) is the
  lowest-effort/highest-leverage home; B1 (`S2SAuditLogger`) is purpose-built but
  presently inert (3 build steps). The trade is effort vs. semantic fit.
- **Per-action grain ↔ per-auth grain.** A1/C1/C2 record *who acted on which
  object*; B2 records *who authenticated*. The bar says "the audit line names
  that human" — per-action grain is the stronger construct-validity match.
- **Durability posture (§2.4).** Reading (a) inherits Asana's own durability
  (the record persists); reading (b)/(c) inherits the CloudWatch group's
  retention, which is **out-of-repo** (U-1). A belt-and-suspenders reading —
  (a) for rep-visible durability **and** (c) for structured retention — hedges
  both.

## 6. Unknowns (structural decisions requiring human/context — surfaced, not assumed)

### Unknown U-1: audit-log-group retention duration
- **Question**: What `retention_in_days` is set on `var.asana_service_log_group`, and does it meet the audit-retention need R28(b) implies?
- **Why it matters**: Every reading-(b)/(c) LANDABLE verdict's "durable … with retention" clause depends on it; if the group is set to never-expire or a short window, the packet must name the retention decision as part of the landing.
- **Evidence**: `terraform/services/asana/observability_alarms.tf:324/336` consumes the group as a variable; no `aws_cloudwatch_log_group{retention_in_days}` resource is declared in-repo.
- **Suggested source**: the shared platform/ECS terraform module that provisions the group (outside `terraform/services/asana/`); the operator / SRE.

### Unknown U-2: per-action vs per-request human grain expectation
- **Question**: Does the bar want the human named on **every business-record mutation** (A1/C1/C2 grain) or once per invocation is sufficient (B2/C1 grain)?
- **Why it matters**: Decides whether A3/A4 (per-object structured field) and the full C1-family are required, or a single coarse ledger line suffices.
- **Evidence**: R28 text says "the audit line names that human" (singular) but reading (a)'s example is object-sited ("where the work lives, visible to reps"), implying per-object.
- **Suggested source**: operator, at the R4 packet ruling.

### Unknown U-3: event-triggered human provenance (C4 / PRE-D1)
- **Question**: On the webhook/event-triggered path, whose human identity (if any) does the D1 seam expect the audit line to name?
- **Why it matters**: C4 landability and the D1 constraint (`#266`) hinge on it; an event with no originating human may name only the automation.
- **Evidence**: `webhooks.py:6` V2 extension point; §2.2; D1 ADR `#266 → 2c91a724`.
- **Suggested source**: SP sprint (species-leg contract) + operator; this is the SP/D1 boundary, referred, not decided here.

## 7. Cross-rite observations (for the remediation/packet author — not decided here)

- **→ SP (security):** every LANDABLE verdict is gated on §2.1 species
  consumption. RD and SP are co-critical; the packet must present them as one
  coherent whole (the audit line lands *because* the species is consumed).
- **→ security-review (cross-rite):** the K-MCP kill and the shared-bot-PAT
  attribution (A5) touch credential-scope semantics; noted as an observation for
  the PK author to convert into a structured referral if warranted (not a
  security audit performed here).
- **→ FL / provenance:** the five-member C1/C2/C3/C5/C6 audit-log family (plus the
  three write-but-no-log surfaces `projects`/`sections`/`tasks`) is undocumented as
  "the audit path" — the feature catalog (FL-3) and any audit ADR should name it.

## 8. Confidence & self-grade

- **High confidence** on all existence/disposition claims: each row carries a
  direct `file:line` receipt at origin/main dfdb84a3, corroborated by both the
  topology census (surfaces exist) and semantic reading (what they record).
- **Medium** on B3/C4 (out-of-production-path / event-path dependency) and on the
  retention clause (U-1, out-of-repo).
- **Self-grade: MODERATE** (self-ref ceiling per self-ref-evidence-grade-rule).
  External corroboration arrives rite-disjoint at CP-1/CP-2 via the security
  critic (security-reviewer, threat-modeler) and at CP-4 via the eunomia
  verification-auditor ADVISORY. This grid is a search-space + disposition
  artifact staged into PK-2; it is not a realization claim, and it grades what
  it is.

**Boundary reaffirmed:** this grid FLIPS NOTHING. No species, validator,
claims-model, or audit-semantics change is merged, deployed, or flipped by this
artifact (R29). Any landing marked LANDABLE is R29-gated INTO the packet (PK-2),
never into main. The grid REPORTS; the operator RULES; RD pre-decides no
conclusion.

---
*RD sprint · fleet-delegation-phase2 · arch/structure-evaluator (lead) with
topology-cartographer + arch-adversary · SURFACE landing mode · staged for
HANDOFF-rd-grid-to-pk-packet → PK-2. Source: origin/main dfdb84a3, committed
truth via `git show origin/main:` only. No git add / commit / branch / push /
merge — staged for operator post-ruling disposition, never pre-empting the R29
gate.*
