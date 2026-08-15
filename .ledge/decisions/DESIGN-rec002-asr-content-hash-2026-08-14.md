---
type: decision
status: proposed
---

# DESIGN — REC-002(b): arm the swap detector at the ASR production delivery path

| | |
|---|---|
| **Status** | READY-FOR-BUILD (design authority: architect, 10x-dev @ autom8y-asana) |
| **Wave** | `coc-arm-the-instrument`, PHASE A-1 (session-20260814-210158-d6cdff92) |
| **Charge** | REC-002 conjunct **(b) ONLY** — additive observability. Conjunct (a) is operator-reserved. |
| **Builder** | principal-engineer. Write path: `services/account-status-recon/**` (autom8y monorepo). |
| **Substrate of record** | autom8y `origin/main` **5f554d60** (2026-08-14T18:35:31+02:00); autom8y-asana **f6de435f** (local `main` == `origin/main`) |
| **Evidence cap** | **MODERATE** — self-referential authorship (the seat designing the instrument's arming also authors its proof design) per `self-ref-evidence-grade-rule`. STRONG requires the rite-disjoint attester's own re-derivation. |
| **Companion** | `ADR-asr-content-hash-canonicalization-2026-08-14.md` (canonicalization option (iv) + (iv)→(iii) trip-wire) |

> **Read discipline for this document.** Every autom8y-side anchor below was read via
> `git -C /Users/tomtenuta/Code/a8/a8/repos/autom8y show origin/main:<path>`. The local
> autom8y checkout is **281 files divergent** from `origin/main` and was never used as a
> read surface. Line numbers are `origin/main` line numbers.

---

## §0 — Grant interpretation (F1) and the fence this design does not cross

This design implements **REC-002 conjunct (b)** — emitting `content_hash` +
`report_generated` on the ASR production delivery path — under the operator's explicit
Phase-3 / REC-002 charge.

**Conjunct (a) — wiring the EX-5 readout (`render()`) into ASR's egress — is
OPERATOR-RESERVED and is NOT designed, NOT specified, and NOT built here.** It is
surfaced as a named boundary (§6) and as exit-predicate E4, never silently absorbed.
This is the charter's own instruction: *"never silently widen mandate (scope changes are
surfaced as findings, not absorbed)"* — `CHARTER-decision-space-of-record-2026-07-30.md:57`
(Operative Core §7, verbatim-fenced region L48–65).

Two further charter checks, run explicitly rather than assumed:

- **Core §5 gate (a), irreversibility** — NOT tripped. The change is one new module, one
  new log event, one new field on an existing log event. Revert = revert the PR. No
  migration, no schema change, no IAM, no infrastructure.
- **Core §5 gate (b), customer-visible / security / spend** — NOT tripped. §3.4 establishes
  structurally that **the bytes handed to `send_blocks` are byte-identical to today**. No
  block, no fallback text, no channel, no ordering changes. Nothing a customer sees moves.
  No credential surface is touched. No spend.

Therefore the work runs autonomously under Core §5, **licensed by Core §6** (independent
verification before it is real) — discharged by the qa-adversary leg and the two-sided
proof design in §7. Autonomy is void where that verification does not happen.

---

## §1 — Verified premises (A-1 own-hands re-probe)

Each row was re-read by this seat at design time, not inherited.

| # | Claim | Anchor (origin/main) | Label |
|---|---|---|---|
| P-1 | ASR assembles the report at `build_slack_report(...)` | `orchestrator.py:472` | SVR-1 |
| P-2 | `report_posted` emits `{channel, block_count, abort_reason, invocation_id}` — **no `content_hash`** | `orchestrator.py:1250-1256` | SVR-2 |
| P-3 | `content_hash` appears **nowhere** in the ASR service | `git grep -c content_hash -- services/account-status-recon/**` → zero hits | SVR-3 |
| P-4 | **THREE** `_safe_slack_post` call sites, **three distinct block builders** | `orchestrator.py:160`, `:223`, `:501`; builders at `:149`, `:212`, `:472` | SVR-4 |
| P-5 | `send_blocks` does not mutate or truncate `blocks`/`text` | `autom8y-slack/client.py:290-294`, `_request` at `:135` posts `json=payload` | SVR-5 |
| P-6 | The 50-block truncation happens **inside** `build_slack_report` (before any hash point) | `report.py:260-261` (FR-21) | SVR-6 |
| P-7 | structlog renders the positional message under the key `event` (JSONRenderer, no EventRenamer) | `autom8y-log/backends/structlog_backend.py:136-139` | SVR-7 |
| P-8 | `content_hash` is **not** in the redaction set | `autom8y-log/processors.py:139-157` | SVR-8 |
| P-9 | ASR default log level is INFO | `config.py:206` | SVR-9 |
| P-10 | `invocation_id` == Lambda `aws_request_id` (unique per invocation) | `handler.py:47` | SVR-10 |
| P-11 | Merge to monorepo main auto-deploys to production, no environment gate | `service-deploy-dispatch.yml:26-28` (push), `:162` (`ENV="production"`), `:255` (`deploy-lambda`) | SVR-11 |
| P-12 | `image_tag` pin at `production.tfvars:30` is a live rollback hazard | `production.tfvars:20-30` | SVR-12 |

**P-4 is the premise that reshapes the build.** The dispatch brief anchored the build at
`:472` alone. Direct read shows `_safe_slack_post` serves **three** paths, two of which
assemble entirely different payloads (`_build_all_failed_alert` at `:1302`,
`_build_readiness_abort_alert` at `:1330`). A design that stamps only the `:472` path
would leave the two abort paths emitting `report_posted` **without** `content_hash` — and
E1 says *every* `report_posted`. §3.5 and §8 place the emissions accordingly.

---

## §2 — (a) IMPEDANCE RULING: what `report_generated` means for ASR

### §2.1 The two payload families are different products

| | ASR account-findings payload | EX-5 item-1a readout |
|---|---|---|
| Assembler | `ReconciliationReportBuilder` via `build_slack_report` (`orchestrator.py:472`, `report.py:251-269`) | `render()` (`src/autom8_asana/readout/generation.py`) |
| Content | three-way reconciliation findings grouped by severity | offer-rows say-able readout |
| Live? | **YES** — 6 ticks/day, `cron(0 */4 * * ? *)`, 58 `report_posted` / 30d | **NO** — zero production callers |
| Egress | `slack_client.send_blocks` → `#account-health` | none |

### §2.2 The join is generator-agnostic — this is what makes (b) coherent without (a)

`_classify` (`join.py:71-128`) never reads `generator`, `generator_version`, or
`source_query_id`. It reads exactly four things: presence of delivery, presence of
generation, `human_in_loop`, `assembled_by`, then the two hashes and the two block counts.
A `report_generated` is therefore **valid for the join iff it satisfies the
`GenerationReceipt` field contract keyed on `invocation_id`** — regardless of which
machine assembled the payload.

This is not a convenient reading; it is the join's founding design. `schema.py:29-42`
names the autom8y ASR service as *the* delivery half the instrument was built against, and
`schema.py:44-56` states the founding negative precisely: *no generation-provenance receipt
exists, joinable to the live `report_posted` delivery receipt on `invocation_id`*. ASR is
the intended discharge site for the generation half. Arming it is REC-002(b) executed at
the place the instrument was aimed.

### §2.3 The generation event ASR emits

ASR's payloads are machine-assembled with no human in the loop **on all three paths** —
the claim `assembled_by=machine, human_in_loop=false` is *true at each assembly site*, not
a convenience. The emitted contract:

```
event             = "report_generated"
invocation_id     = <aws_request_id>                     # join key; HARD-REQUIRED
assembled_by      = "machine"                            # -> Assembler.MACHINE
human_in_loop     = False                                # real JSON boolean, NOT a string
generator         = "<module>.<assembly function>"       # per-path self-identification
generator_version = <importlib.metadata version, fallback "unknown">
source_query_id   = "<stable input-set label>"           # see §2.4
content_hash      = "sha256:<64 hex>"                    # canonical_payload_hash(blocks, text)
block_count       = len(blocks)
generated_at      = <ISO-8601 UTC>
```

### §2.4 Field-contract verification against the join (the E2-critical check)

Verified field-by-field against `GenerationReceipt.from_event` (`schema.py:259-277`).
**A mis-named field does not fail loudly — it defaults, and the default is hostile:**

| Emitted key | `from_event` line | Behaviour if MIS-NAMED / ABSENT | Consequence |
|---|---|---|---|
| `invocation_id` | `:269` `str(evt["invocation_id"])` | **KeyError — raises** | join crashes. HARD-REQUIRED. |
| `assembled_by` | `:262` default `"unknown"` | → `Assembler.UNKNOWN` → clause 3 (`join.py:86`) | `NOT_OBSERVABLE / assembled_by_human` |
| `human_in_loop` | `:270` default `True` | → clause `if generation.human_in_loop` (`join.py:84`) | `NOT_OBSERVABLE / human_in_loop` |
| `content_hash` | `:274` default `""` | falsy → clause 4a **skipped**, falls to 4b | 4a silently UNATTESTED — instrument reads armed but is not |
| `block_count` | `:275` via `_as_int` | → `0` → falsy → clause 4b skipped | both swap clauses dark |
| `generator` / `generator_version` / `source_query_id` / `generated_at` | `:271-276` | default `""` | **no verdict impact** — provenance metadata only |

**Correction to an inherited premise.** The dispatch brief states that a mismatched field
name *"silently keeps the join in the generation-absent branch."* Direct read shows that is
false. `GENERATION_PROVENANCE_ABSENT` (`join.py:79-83`) is reachable **only** when no
generation event is keyed to that `invocation_id` — i.e. when the **event name** is wrong
(`query.py:56-59` splits on `evt.get("event")`), or when the emit never fired. A wrong
**field** name lands in clause 3 or leaves clause 4a dark. Both sink E2; they sink it by
different routes and are diagnosed differently. The builder must treat the field names as
a frozen wire contract, copied from `schema.py:269-276`, not paraphrased.

**Log-level coupling.** `report_generated` MUST be emitted at `log.info` — the same level
as `report_posted` (`orchestrator.py:1250`). Emitting the generation half at `debug` would
make it vanish under any raised `LOG_LEVEL` while the delivery half survived, stranding
every tick in `generation_provenance_absent` with no signal that anything is wrong.
Identical level = identical survivability = the two halves live or die together.

---

## §3 — (b) HASH REFERENT: exactly what bytes, hashed exactly where

### §3.1 The referent

The bytes hashed are the canonical JSON form of `{"blocks": <blocks list>, "text": <fallback text>}`
— the payload **as delivered**. This is faithful to the wire: `send_blocks` constructs
`{"channel", "text", "blocks"}` (`client.py:290-294`) and `_request` posts it as `json=payload`
(`client.py:135`, `:159` region). Excluding `channel` is correct — the channel is delivery
routing, not payload content, and the asana-side canonicalization already fixed this shape
for the same reason (`payload_hash.py:19-21`: hashing blocks alone would leave the fallback
`text` unbound and a text-only swap invisible).

### §3.2 The mutation-window trace (the false-positive-storm question)

The design must place the two hash points so an **honest** delivery hashes EQUAL — otherwise
every live tick reads as a swap and the wave produces a false-positive storm. Traced at
`origin/main`, end to end:

| Step | Anchor | Does `blocks` or `text` change? |
|---|---|---|
| Assembly (report path) | `orchestrator.py:472-477` | `blocks` bound. **50-block truncation already applied inside** (`report.py:261`, FR-21) |
| Fallback text built | `orchestrator.py:481-489` | `fallback_text` bound |
| `slack_post_attempt` | `orchestrator.py:494-499` | reads `len(blocks)` only — **no mutation** |
| Call into helper | `orchestrator.py:501-510` | passed **by reference**, positionally |
| `slack_post_entered` | `orchestrator.py:1216-1223` | reads `len(blocks)`, `text[:100]` — read-only slice |
| dry_run branch | `orchestrator.py:1229-1246` | **returns** before the wire; no delivery occurs |
| Wire call | `orchestrator.py:1248` | `send_blocks(channel=…, blocks=blocks, text=text)` |
| SDK | `client.py:290-294` | builds a **new** dict *referencing* `blocks` — **no mutation, no truncation** |

**Result: the window between assembly and wire contains ZERO mutation.** An honest delivery
hashes EQUAL by construction, not by hope. No false-positive storm.

Two consequences worth stating plainly:

- **Truncation is not a hazard here.** FR-21's 50-block cap runs *inside* `build_slack_report`,
  so the truncated form is what gets hashed at the generation point. A cap applied *after*
  the generation hash would have been a false-positive generator; it is not.
- **Slack server-side truncation is outside the custody chain.** `report.py:69` records that
  *"ASR never attempts to PREDICT what the SDK will truncate."* Whatever Slack does to the
  payload after receipt is invisible to **both** hash points equally, so it cannot cause
  disagreement. Out of scope, by construction rather than by neglect.

### §3.3 Where each hash is computed — and why NOT one shared value

**RULING: two hash points, both calling the ONE function. The delivery-side hash is
RE-COMPUTED, never threaded through from the generation side.**

- **Generation hash** — computed at each **assembly** site, on the freshly-assembled
  `(blocks, fallback_text)`: `orchestrator.py:472` (report), `:149` (all-sources-failed),
  `:212` (readiness abort).
- **Delivery hash** — **re-computed inside `_safe_slack_post`** from the `blocks`/`text`
  *parameters as handed to the wire*, immediately before the `try:` at `orchestrator.py:1247`.

The rejected alternative is the one that looks simplest: compute once and pass the value
into both emits. **It must not be done.** Threading one value into both sides makes the
join's clause 4a evaluate `h == h` — a tautology that can never fail. The join would then
report `OBSERVABLE` with 4a apparently *satisfied* while comparing a value to itself: an
instrument that reads **armed** while detecting nothing.

That is strictly worse than today's state. Today clause 4a is honestly `UNATTESTED` and the
gap is pinned by a test (`join.py:39-44`; `test_swap_detector_closure.py:199-209`). A
tautological pass would convert a *known* gap into a *false attestation* — precisely the
outcome the charter hard-floors: **NEVER CONFIDENTLY WRONG**
(`CHARTER-decision-space-of-record-2026-07-30.md:52`, Operative Core §2). Re-computation at
the delivery point is what gives the comparison any referent at all.

**REC-001 compliance.** The invariant is *no second **independent** canonicalization of the
same logical payload within a comparison pair* (`payload_hash.py:16-18`, as clarified by the
adopted pythia ruling). Both ASR hash points call **one** function; the pair is internally
consistent by construction. Two invocations of the same canonicalization are not two
canonicalizations.

### §3.4 What the live signal honestly is — and is not

With a zero-mutation window, an honest tick **always** agrees. So the live clause-4a check is
a **standing invariant assertion**, not an anomaly detector. Stated without inflation:

- **What it buys.** (i) It closes the join's UNATTESTED 4a branch, so an occurrence can reach
  `OBSERVABLE` with payload identity actually **hash-verified** rather than resting on
  `block_count` alone. (ii) It is **regression surveillance**: the day a decoration, a
  post-assembly banner, a retry rewrite, or a second truncation is inserted between assembly
  and egress, the detector bites — and that insertion is exactly the plausible future change.
- **What it does NOT buy.** A hand-paste — the founding-wound shape named at
  `test_swap_detector_closure.py:66-70` — does not traverse this code path at all. It would
  surface as `generation_provenance_absent`, caught by clause 2, not by the hash. Arming 4a
  does not make ASR's egress resistant to an out-of-band post.
- **Discriminating power over clause 4b** is a count-preserving content change occurring
  *within the traced window*. Real, and narrow today by exactly the amount §3.2 measured.

Claiming more than this would be the "armed instrument" theater the wave exists to end.

### §3.5 Placement consequence for the three paths

Because `report_posted` is emitted from **one** site (`orchestrator.py:1251`) serving all
three call paths, placing the delivery hash inside `_safe_slack_post` satisfies **E1 for all
three paths by construction** — no per-call-site work, no drift surface.

`report_generated` is emitted at **all three** assembly sites. Rationale:

1. **Truth**: all three payloads are machine-assembled, no human in the loop.
2. **E2 starvation risk**: abort ticks are a large share of live deliveries — `orchestrator.py:234-238`
   records the 07-31→08-03 window as *6 runs/day, all readiness=fail*. If only the report path
   carried a generation receipt, E2 (≥1 live ATTESTED traversal) would depend on catching a
   `report_success` tick and could starve through an entire readiness-fail streak.
3. **Half-dark instrument**: leaving abort ticks permanently in `generation_provenance_absent`
   would leave the join dark on the majority path while the paper claimed it was armed.

Exactly one `_safe_slack_post` call executes per invocation (each abort path `return`s —
`orchestrator.py:179`, `:240`+), so at most one `report_posted` and one `report_generated` per
`invocation_id`. This preserves the join's last-write-wins keying (`join.py:146-155`) and its
stated assumption *"report_posted fires once per invocation"* (`join.py:149`).

---

## §4 — (c) JOIN SHAPE: is the ATTESTED branch actually reachable?

| Requirement | Verified | Anchor |
|---|---|---|
| Same log group | YES — both events emit through `log = get_logger(__name__)` in the same Lambda → `/aws/lambda/autom8y-account-status-recon` | `orchestrator.py:62` |
| Event key is `event` | YES — JSONRenderer, no EventRenamer → structlog's positional message lands under `event` | `structlog_backend.py:136-139` |
| Event names exact | `report_posted` / `report_generated`, matching the split at `query.py:56-59` and the constants `DELIVERY_EVENT` / `GENERATION_EVENT` | `schema.py:169`, `:173` |
| Insights queries already select the fields | Delivery query selects `content_hash`; generation query selects all nine generation fields | `schema.py:376-388` |
| No redaction of `content_hash` | Not in `DEFAULT_SENSITIVE_FIELDS` | `processors.py:139-157` |
| Level survivability | Both at `log.info`; service default INFO | `orchestrator.py:1250`; `config.py:206` |
| Join key uniqueness | `invocation_id` = `aws_request_id` | `handler.py:47` |

**Live precedent that the mechanism works:** `report_posted` is emitted by exactly this
mechanism and the 30-day census returned **58 rows** with `invocation_id` present on all 58.
The generation half uses an identical emit shape through the identical logger.

**Reachability of `OBSERVABLE`** — walking `_classify` (`join.py:71-128`) with the designed
emissions: delivery present ✓ (`:77`) → generation present ✓ (`:79`) → `human_in_loop` False ✓
(`:84`) → `assembled_by is MACHINE` ✓ (`:86`) → clause 4a both hashes present and **equal** ✓
(`:100-108`) → clause 4b both counts present and equal ✓ (`:119-127`) → **`RungEObservability.OBSERVABLE`,
reason `None`** (`:128`). The ATTESTED branch is reachable.

### §4.1 HAZARD H-1 — the ingestion coercion that silently sinks E2

**`GenerationReceipt.from_event` does `human_in_loop=bool(evt.get("human_in_loop", True))`
(`schema.py:270`). CloudWatch Logs Insights returns every discovered field value as a
STRING. `bool("false")` is `True`.**

So if E2 evidence is gathered by piping a Logs Insights *field projection* into `run_query`,
every honest tick evaluates `human_in_loop → True`, trips `join.py:84`, and returns
`NOT_OBSERVABLE / human_in_loop` — **while the ASR emission is perfectly correct**. The wave
would fail E2 and the failure would point at the wrong half of the system.

This asymmetry is specific to one field. `block_count` is string-tolerant via `_as_int`
(`schema.py:349-360`); `content_hash` via `str()`; `assembled_by` via the `Assembler(...)`
lookup on a string. Only `human_in_loop` coerces hostilely.

**Disposition (two parts, both required):**

1. **E2 procedure is constrained** (§7.1): ingest **raw JSON log records** — e.g.
   `aws logs filter-log-events` → parse each `@message` as JSON → JSONL →
   `python -m autom8_asana.observability.rung_receipts.query` — so the real JSON boolean
   survives. Do **not** feed a Logs Insights `{field, value}` projection into `run_query`.
2. **Named instrument-side residual**, NOT this wave's builder's work. The durable fix is a
   tolerant `_as_bool` in `schema.py` (mirroring `_as_int`). That file is in autom8y-asana and
   outside the builder's `services/account-status-recon/**` path fence (§9). Carried as
   RESIDUAL-1 (§10).

The emission side needs no hedge: ASR emits a real JSON boolean `False`, which is exactly
what the contract (`schema.py:459` `"human_in_loop": {"type": "boolean"}`) requires. The
defect is on ingestion, and it is recorded rather than papered over.

---

## §5 — (d) FAILURE MODE: fail-open, and the sharp edge in the obvious placement

**Invariant: a hashing or emission failure must NEVER suppress, alter, or fail the Slack
delivery.** House precedent — `.know/conventions.md:41`: *`services/receipts_service.py`
carries a deliberate `noqa: BLE001` blind-except boundary ("a receipt must never fail on the
stage write")*. Same principle at a different seam: **a receipt must never fail the delivery.**

### §5.1 The guard shape

```
def _safe_content_hash(blocks, text) -> str | None:
    """Total function. Never raises. None on any failure."""
    try:
        return canonical_payload_hash(blocks, text)
    except Exception as exc:                      # noqa: BLE001 — receipts never fail the write
        log.warning(
            "content_hash_failed",
            error_type=type(exc).__name__,        # TYPE ONLY — never str(exc), never the payload
            invocation_id=invocation_id,
        )
        return None
```

`canonical_payload_hash` calls `json.dumps` with no `default=`, so any non-serialisable
object reaching the blocks (a `datetime`, a model instance) raises `TypeError`. That is a
real, reachable failure — not a theoretical one — because block assembly is a rich code path.

`error_type` only: never `str(exc)` and never `exc_info`, because a serialisation error
message can echo the rejected payload fragment. This mirrors the existing discipline at
`orchestrator.py:1138-1151`, which records the exception **type** only for exactly this reason.

### §5.2 Placement — the sharp edge

**The delivery-side hash MUST be computed BEFORE the `try:` at `orchestrator.py:1247`** (and
after the `dry_run` early-return at `:1229-1246`).

If it were computed *inside* the try block, a hashing exception would be caught by
`except Exception as exc:` at `:1265` and mis-reported as **`slack_post_failed`** on a
delivery that actually **succeeded**, then escalated to a raised **`ReportError`**
(`:1289`+). An observability feature would have manufactured a false delivery failure and
killed the run. That is the single most damaging way to get this wrong, and the placement
rule exists to make it unreachable.

Because `_safe_content_hash` is total, computing it before the try is safe; nothing can
propagate.

### §5.3 Degradation semantics — omit the key, never emit `null`

**When the hash is unavailable, OMIT the `content_hash` key entirely. Do not emit
`"content_hash": null`.**

Emitting an explicit null is a false-positive generator: over a Logs Insights ingestion path
a null field can surface as the **string** `"null"`, which `_opt_str` (`schema.py:344-346`)
passes through as a truthy `"null"` string, which then compares unequal to the generation
hash and yields a spurious `CONTENT_HASH_MISMATCH`. Omission instead reproduces exactly the
live hashless shape the schema was built to tolerate and which is already pinned by
`test_swap_detector_closure.py:251-262`.

Degradation ladder, per half:

| Failure | Behaviour | Join reads |
|---|---|---|
| Delivery hash fails | key omitted from `report_posted`; delivery proceeds unchanged | clause 4a UNATTESTED, falls to 4b — **today's honest state** |
| Generation hash fails | **`report_generated` is not emitted at all**; report still builds and posts | `generation_provenance_absent` — the honest pre-wave state |
| Generation emit fails | wrapped, logged, swallowed; report still builds and posts | `generation_provenance_absent` |

A generation receipt whose entire purpose is to carry the hash should not be emitted without
one; emitting a hashless generation receipt would leave clause 4a dark while the receipt's
presence implied provenance was attested. Skipping is the honest degradation.

### §5.4 dry_run

Under `dry_run` the wire call is suppressed and `_safe_slack_post` returns at
`orchestrator.py:1246` — no `report_posted`, so no delivery occurrence. `report_generated`
still fires (generation genuinely happened). This is harmless and correct: the join is
**delivery-anchored** (`join_occurrences` iterates deliveries, `join.py:158`), so an
unmatched generation receipt never enters the output. A dry_run tick cannot pollute the join.

---

## §6 — (e) RENDER() BOUNDARY

**`render()` gains no production caller in this wave.** Its only callers remain tests
(`tests/unit/test_swap_detector_closure.py:54`). Wiring the EX-5 readout into ASR's egress is
REC-002 conjunct **(a)** — operator-reserved (§0).

Stated as a bound, so it cannot be mis-read:

- ASR's `report_generated` attests **ASR's own account-findings payload**
  (`ReconciliationReportBuilder`, `report.py:264-269`). It does **not** attest, deliver, or
  substitute for the item-1a offer readout.
- The **instrument** becomes armed. The **item-1a readout remains undelivered.** These are
  independent facts and the second is not improved by the first.
- **Telos-scope question surfaced, not resolved:** whether an ASR account-findings delivery
  counts toward the *asana-native-insight-delivery* telos's RUNG E limb (a) is an
  attester/operator question. This design establishes only the **mechanical** reachability of
  the join's `OBSERVABLE` branch (§4). It does not rule on telos semantics, and the builder
  must not claim limb (a) is satisfied.

**E4 known-gaps record** (both survive this wave, both named):

| Gap | Status after this wave | Pointer |
|---|---|---|
| `render()` has zero production callers | **SURVIVES** | REC-002(a), operator-reserved |
| Cross-repo byte-parity of the two canonicalizations | **DEFERRED, untested** | REC-004 (ADR trip-wire) |

---

## §7 — (f) TWO-SIDED PROOF DESIGN

**E3 binding: the tamper side is INPUT/FIXTURE-ONLY. No defect is ever injected into
production code.** Per the discriminating-canary doctrine, the RED is a deliberately-broken
*input* that the live surface correctly rejects — never a broken surface.

### §7.1 Honest side — live post-deploy observation

**Procedure.** After the CD deploy lands (P-11) and at least one scheduled tick has run
(`cron(0 */4 * * ? *)`, ≤4h):

1. Capture the paired events for one `invocation_id` from
   `/aws/lambda/autom8y-account-status-recon`.
2. **Ingest as raw JSON**, per H-1 (§4.1): `aws logs filter-log-events` → parse each
   `@message` as JSON → one JSON object per line → pipe to
   `python -m autom8_asana.observability.rung_receipts.query` (`query.py:74-84`).
3. Assert the occurrence receipt is `rung_e_limb_a_attestation == "observable"` with
   `rung_e_not_observable_reason == null`, and that both `content_hash` values are present
   and equal.

**Independent recomputation — UV-P.** Recomputing the hash from logged data is **not
feasible**: the logs deliberately never carry the payload. `slack_post_entered` carries
`text_preview=text[:100]` (`orchestrator.py:1220`) and `block_count` only. This is correct
design (payloads are not logged) and it is an honest ceiling on the live leg, not an
oversight.

> `[UV-P: an attester independently recomputes the live content_hash from logged data | METHOD: deferred-indefinitely-by-design | REASON: the ASR log surface deliberately carries no payload — only block_count and text[:100] (orchestrator.py:1220) — so the input bytes are not recoverable from CloudWatch. The live leg's honest ceiling is presence + well-formedness + equality + block-count agreement.]`

What **is** independently checkable from the live capture, and is therefore what the live leg
claims: both hashes present, both matching `^sha256:[0-9a-f]{64}$`, **equal to each other**,
`block_count` agreeing across the pair, `assembled_by == "machine"`, `human_in_loop == false`,
and the join returning `observable`.

### §7.2 Tamper side — fixture-only, ASR repo

Location: `services/account-status-recon/tests/test_orchestrator_observability.py` (extend).
Precedent for the mechanism: that file already imports `from structlog.testing import capture_logs`
(`:31`) and already drives `_safe_slack_post` directly (`:34`).

| Test | Shape | Proves |
|---|---|---|
| T-1 honest | drive `_safe_slack_post` with a fixture `(blocks, text)`; assert `report_posted` carries `content_hash == canonical_payload_hash(blocks, text)` | E1 delivery half; **RED at 5f554d60** (field does not exist — P-3) |
| T-2 discrimination | mutate ONE text leaf in the fixture blocks; assert the hash differs | the function discriminates on content, not shape |
| T-3 text-binding | same blocks, changed fallback text; assert the hash differs | `text` is bound, not free (mirrors `test_swap_detector_closure.py:225-230`) |
| T-4 generation contract | assert `report_generated` carries all nine fields with the **exact** key names from `schema.py:269-276`, `assembled_by == "machine"`, `human_in_loop is False` (a real bool) | §2.4 wire contract; guards the silent-default class |
| T-5 all three paths | assert `report_posted` carries `content_hash` on **each** of the three call paths (`:160`, `:223`, `:501`) | E1's *every* |
| T-6 fail-open | monkeypatch the hash helper to raise; assert `send_blocks` **still awaited**, `report_posted` **still emitted**, `content_hash` key **absent** (not null), **no `ReportError`** | §5 fail-open + §5.3 omission |
| T-7 dry_run | under `dry_run`, assert no `report_posted` and no wire call | §5.4; no regression of the existing dry_run canary |

### §7.3 Tamper side — instrument repo (OPTIONAL leg, separate grant)

Location: `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/tests/unit/test_swap_detector_closure.py`.

**This is a different repository and lies outside the builder's `services/account-status-recon/**`
path fence (§9). It requires its own dispatch and its own grant. It must not be folded silently
into the ASR PR.**

Value if granted: the existing teeth (`:114-137`) are proved on the **item-1a `render()` shape**.
An ASR-shaped fixture would prove the join bites on the **ASR receipt shape** specifically:

- **T-8** synthetic `report_generated` carrying the ASR field set
  (`generator="account_status_recon.report.build_slack_report"`) joined to a `report_posted`
  whose `content_hash` is the hash of a *mutated* payload → assert `CONTENT_HASH_MISMATCH`.
- **T-9** single-variable causation on the ASR shape, mirroring `:154-178`: the two input
  events differ in **exactly one field** (`content_hash`) and the verdict flips.

**If the grant is not extended, E3 is still satisfied**: the ASR-side T-1…T-7 prove the
emission, and the *existing* instrument tests (`:115-129`) already prove the join bites on a
hash mismatch. T-8/T-9 strengthen coverage; they are not load-bearing for E3.

### §7.4 Honest-negative guard — the fixture must be blind at the pre-arm ref

Per the discriminating-canary doctrine this is **mode 2: a genuine gap**, not an injected
defect. `content_hash` genuinely does not exist anywhere in the ASR service at `origin/main`
5f554d60 (P-3, `git grep -c` → zero hits).

- **RED-before**: T-1, T-4, T-5 **must fail** when run against 5f554d60 — the field and the
  event do not exist. This is the honest-negative: the tests are blind at the pre-arm ref
  because there is nothing to see.
- **GREEN-after**: they pass on the armed tree.
- **Two-sidedness**: T-2/T-3 prove the hash *discriminates* (a no-op or constant-returning
  hash would fail them), so a GREEN cannot be bought with a degenerate implementation.
- **Residual stays pinned**: `test_swap_detector_closure.py:199-209`
  (`test_swap_on_a_hashless_delivery_is_still_undetected`) **must continue to pass**. It pins
  the honest limitation that a hashless delivery cannot be swap-checked. This wave arms the
  ASR emitter; it does not repeal that residual for any other hashless emitter, and the test
  must not be edited to look armed.

---

## §8 — Build specification

### §8.1 New module

`services/account-status-recon/src/account_status_recon/payload_hash.py`

Named to **mirror** the asana-side module (`src/autom8_asana/observability/payload_hash.py`)
so the (iv)→(iii) migration in the companion ADR is a mechanical import swap — same module
name, same symbol name, same signature, same canonical form, same `sha256:` prefix.

```
canonical_payload_hash(blocks: Sequence[Mapping[str, object]], text: str) -> str
    canonical = json.dumps({"blocks": list(blocks), "text": text},
                           sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
```

Semantically mirrors `payload_hash.py:38-55` exactly: same key set, same `sort_keys=True`,
same `separators=(",", ":")`, same `list(blocks)` normalisation, same digest and prefix.
Its docstring must state that it is a deliberate mirror, name the ADR, and state that
**cross-repo byte-parity is NOT tested and NOT claimed** in this wave.

Also in this module (or an adjacent `provenance.py` — builder's discretion, single module
preferred):

- `_safe_content_hash(blocks, text, *, invocation_id) -> str | None` — the total guard (§5.1).
- `emit_report_generated(*, blocks, text, invocation_id, generator, source_query_id) -> None`
  — computes the hash and emits the nine-field event (§2.3); **never raises**; **skips the
  emit entirely** if the hash is unavailable (§5.3).

### §8.2 Edits to `orchestrator.py`

| Site | Edit |
|---|---|
| `:149` after `blocks = _build_all_failed_alert(...)` | `emit_report_generated(blocks=blocks, text=<the literal at :164>, invocation_id=…, generator="account_status_recon.orchestrator._build_all_failed_alert", source_query_id="asr:abort:all-sources-failed")` |
| `:212` after `blocks = _build_readiness_abort_alert(...)` | same, with the `:227` f-string as `text`, `generator="…_build_readiness_abort_alert"`, `source_query_id="asr:abort:readiness-gate"` |
| after `:489` (once `fallback_text` exists) | same, `generator="account_status_recon.report.build_slack_report"`, `source_query_id="asr:three-way:billing+campaign+contract"` |
| before `:1247` (`try:`), after the dry_run return | `content_hash = _safe_content_hash(blocks, text, invocation_id=invocation_id)` |
| `:1250-1256` `report_posted` | add `content_hash` **only when truthy** — build the kwarg conditionally, never emit an explicit null (§5.3) |

**The generation emit must sit AFTER the `text` value exists** at each site — the hash binds
`{blocks, text}` together, so an emit placed before `fallback_text` is constructed (`:481-489`)
would hash a different referent than the delivery side and manufacture a permanent mismatch.
On the two abort paths the text is the literal/f-string passed as the fourth positional
argument at `:164` and `:227`; the builder must bind it to a local **before** both the emit
and the `_safe_slack_post` call so exactly one value is used in both places.

**`source_query_id` is a labelling choice, not a discovered identifier.** ASR has no query id;
the values above honestly name *which input set* produced the payload. `_classify` never reads
the field (§2.2), so nothing depends on it. It must not be dressed up as a real query handle.

**`generator_version`**: `importlib.metadata.version("account-status-recon")` with a
`try/except → "unknown"` fallback. Honest note: this resolves to the static `"0.1.0"`
(`pyproject.toml:14`) and is therefore a **weak build discriminator** — no image tag or git SHA
is injected into the Lambda environment. Wiring build identity would require a terraform change
(operator-gated) and is **out of scope**. Carried as RESIDUAL-2 (§10).

### §8.3 Explicitly NOT changed

No change to the assembled blocks or fallback text. No change to `send_blocks` or the SDK. No
change to `report.py`. No new metric, alarm, IAM, or environment variable. No terraform. No
change to any file in autom8y-asana under the ASR PR. No change to `rung_receipts/**` — the
instrument's schema and join stay frozen; this wave feeds them, it does not alter them.

---

## §9 — Single-writer, deploy, rollback

**Single writer.** Builder = **principal-engineer**. Write path for the autom8y monorepo PR:
**`services/account-status-recon/**` ONLY**. The instrument-side test extension (§7.3) is a
**different repository** and is explicitly **outside this fence** — it requires a separate
dispatch and grant. A cross-repo edit folded into the ASR PR is a fence breach, not a
convenience.

**Deploy.** Merge to autom8y `main` **auto-deploys to production**: `service-deploy-dispatch.yml`
fires on `push` (`:26-28`); the non-`workflow_dispatch` branch sets `ENV="production"` (`:162`);
`deploy-lambda` runs (`:255`). **No environment gate.** The code is live on merge. No terraform
apply is needed or wanted — this change introduces no infrastructure.

**HAZARD H-2 — `image_tag` pin rollback.** `terraform/services/account-status-recon/environments/production.tfvars:30`
pins `image_tag = "c21cab9"`. The comment block at `:20-29` records that this pin previously sat
stale for **19 days** and that *"any dispatched apply or local `just tf-apply` would have silently
ROLLED BACK the ASR lambda"* past a merged cure — and that *"the refresh is manual and nothing
enforces it."*

Consequence for this wave: after CD deploys the armed image, **any** apply in that directory
would roll the Lambda back to `c21cab9` and **silently un-arm the instrument**, with the paper
still claiming REALIZED. Therefore:

1. Run **no** targeted apply in `terraform/services/account-status-recon/` during this wave.
2. If any apply is unavoidable, refresh the pin to the deployed tag **first**.
3. The §7.1 live observation must be timestamped **after** the CD deploy, and **re-taken** if
   any apply intervenes.

**Rollback.** Revert the PR. The next CD deploy restores the prior image. The join returns to
`generation_provenance_absent` / clause-4a-UNATTESTED — the honest pre-wave state, which the
instrument already models and tests (`join.py:39-44`).

---

## §10 — Residuals and hazards register

| ID | Item | Owner | Disposition |
|---|---|---|---|
| **H-1** | `human_in_loop=bool(evt.get(...))` coerces the string `"false"` to `True` (`schema.py:270`) — a Logs-Insights-projection ingestion silently sinks E2 | instrument owner (autom8y-asana) | E2 procedure constrained to raw-JSON ingestion (§7.1); tolerant `_as_bool` fix is **out of this wave's path fence** |
| **H-2** | `image_tag` pin can silently roll back the armed Lambda (`production.tfvars:20-30`) | platform / release | No apply during the wave; refresh pin before any apply (§9) |
| **RESIDUAL-1** | Clause 4a stays UNATTESTED for **every other** hashless emitter; `test_swap_detector_closure.py:199-209` must keep passing | instrument owner | Pinned by test; **must not** be edited to look armed |
| **RESIDUAL-2** | `generator_version` is a weak discriminator (static `"0.1.0"`); no build identity in the Lambda env | ASR service owner | Requires operator-gated terraform; deferred |
| **RESIDUAL-3** | Clause-3 over-claim: `UNKNOWN` assembler reports as `assembled_by_human` (`join.py:86-97`, `schema.py:133-143`) | instrument owner | Pre-existing, documented, frozen wire token; **untouched** by this wave |
| **E4-a** | `render()` has zero production callers | operator | REC-002(a), operator-reserved |
| **E4-b** | Cross-repo byte-parity of the two canonicalizations is untested and unclaimed | ADR owner-of-record | REC-004 trip-wire (companion ADR) |

---

## §11 — Exit-predicate mapping

| Predicate | How this design serves it | Verified by |
|---|---|---|
| **E1** — every `report_posted` carries `content_hash` from the same function that stamps `report_generated` | Delivery hash computed inside `_safe_slack_post`, the **single** `report_posted` emit site serving all three call paths (§3.5). Both sides call the **one** `canonical_payload_hash` (§8.1) | T-1, T-5 |
| **E2** — ≥1 real live delivery traverses the join's ATTESTED branch | Field contract verified against `from_event` (§2.4); `OBSERVABLE` walked clause-by-clause (§4); generation emitted on all three paths so an abort streak cannot starve it (§3.5); ingestion path constrained against H-1 (§4.1) | §7.1 live capture |
| **E3** — two-sided teeth, tampering INPUT/FIXTURE-ONLY | No production defect anywhere. Tamper = mutated fixture input (§7.2 T-2/T-3, §7.3 T-8/T-9). Honest-negative = tests blind at 5f554d60 because the field genuinely does not exist (§7.4) | T-1…T-7 |
| **E4** — known-gaps record | `render()` zero production callers **named as surviving** (§6); cross-repo byte-parity deferred to REC-004 (§6, ADR) | §10 register |

**Handoff readiness.** The builder can implement without further architectural questions:
module and symbol names (§8.1), exact edit sites with line anchors (§8.2), the exact nine-field
wire contract copied from `schema.py:269-276` (§2.3), the guard shape (§5.1), the placement
rule and its rationale (§5.2), the omission rule (§5.3), and the test roster (§7.2).

---

## §12 — Structural-verification receipts

Evidence cap for this document: **MODERATE** (`self-ref-evidence-grade-rule`).

**SVR-2 — the delivery emit's current field set (P-2)**

```yaml
claim: "the live ASR report_posted emitter names four fields and no content_hash, so the join's clause 4a input is absent on every production delivery today"
verification_method: file-read
verification_anchor:
  source: "services/account-status-recon/src/account_status_recon/orchestrator.py @ autom8y origin/main 5f554d60"
  line_range: "L1250-L1256"
  marker_token: "log.info( \"report_posted\", channel=channel, block_count=len(blocks), abort_reason=abort_reason, invocation_id=invocation_id, )"
  claim: "the emit's keyword set is exactly channel/block_count/abort_reason/invocation_id — the delivery half of the swap-check has no field to populate"
```

**SVR-4 — three call sites, three block builders (P-4, the premise that reshaped the build)**

```yaml
claim: "_safe_slack_post is reached from three call sites assembling three different payloads, so stamping only the :472 report path would leave two abort paths emitting report_posted without a content_hash and would fail E1's 'every'"
verification_method: bash-probe
verification_anchor:
  source: "git show origin/main:services/account-status-recon/src/account_status_recon/orchestrator.py | grep -n 'blocks = build_slack_report\\|blocks = _build_all_failed_alert\\|blocks = _build_readiness_abort_alert'"
  command_output_verbatim: "149:                blocks = _build_all_failed_alert(result.degraded_sources)\n212:                blocks = _build_readiness_abort_alert(readiness)\n472:            blocks = build_slack_report("
  exit_code: 0
  claim: "three distinct assembly sites feed one shared egress helper; the generation half must therefore be emitted per-assembly-site while the delivery half is emitted once at the shared helper"
```

**SVR-5 — the SDK does not mutate the payload (P-5, the false-positive-storm question)**

```yaml
claim: "the Slack SDK constructs a fresh request dict referencing the caller's blocks and neither mutates nor truncates them, so the bytes hashed at the delivery point are the bytes sent"
verification_method: file-read
verification_anchor:
  source: "sdks/python/autom8y-slack/src/autom8y_slack/client.py @ autom8y origin/main 5f554d60"
  line_range: "L290-L294"
  marker_token: "payload: dict[str, Any] = { \"channel\": channel, \"text\": text, \"blocks\": blocks, }"
  claim: "blocks is bound by reference into a new dict with no copy, filter, or cap applied — the delivered artifact is the caller's object graph unchanged"
```

**SVR-7 — structlog renders the message under the `event` key (P-7, join reachability)**

```yaml
claim: "the ASR logger's JSON renderer places the positional log message under the key 'event', which is the key the join splits on, so log.info(\"report_generated\", ...) is discoverable by the generation query without any renaming shim"
verification_method: file-read
verification_anchor:
  source: "sdks/python/autom8y-log/src/autom8y_log/backends/structlog_backend.py @ autom8y origin/main 5f554d60"
  line_range: "L136-L139"
  marker_token: "if format_to_use == \"json\": processors.append(structlog.processors.JSONRenderer()) else: processors.append(structlog.dev.ConsoleRenderer(colors=use_colors))"
  claim: "JSONRenderer terminates the chain with no EventRenamer inserted anywhere before it, so structlog's default event-key naming is what reaches CloudWatch"
```

**SVR-13 — the fail-open house precedent (§5)**

```yaml
claim: "this repository already carries an explicit convention that a receipt-writing path must never fail the operation it observes, which is the precedent the content-hash guard shape inherits"
verification_method: file-read
verification_anchor:
  source: "/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.know/conventions.md"
  line_range: "L41"
  marker_token: "carries a deliberate `noqa: BLE001` blind-except boundary (\"a receipt must never fail on the stage write\")"
  claim: "the convention establishes a sanctioned blind-except boundary specifically where observability wraps a write, which is structurally the same seam as a content hash wrapping a Slack delivery"
```

**SVR-12 — the image_tag rollback hazard (H-2)**

```yaml
claim: "the ASR production image pin is manually maintained with no enforcement, so an apply after this wave's CD deploy would silently revert the armed Lambda"
verification_method: file-read
verification_anchor:
  source: "terraform/services/account-status-recon/environments/production.tfvars @ autom8y origin/main 5f554d60"
  line_range: "L27-L30"
  marker_token: "The invariant above was already written here and was simply not honored -- the refresh is manual and nothing enforces it."
  claim: "the pin's own comment records a prior 19-day silent rollback of this exact Lambda, establishing the hazard as observed rather than hypothetical"
```

### UV-P labels carried by this design

> `[UV-P: an attester independently recomputes the live content_hash from logged data | METHOD: deferred-indefinitely-by-design | REASON: the ASR log surface deliberately carries no payload (orchestrator.py:1220 logs only text[:100] and block_count), so the input bytes are unrecoverable from CloudWatch — §7.1 states the live leg's honest ceiling instead]`

> `[UV-P: the designed report_generated emission traverses the join's OBSERVABLE branch on a real production tick | METHOD: deferred-to-post-deploy-observation | REASON: the emitter does not exist at 5f554d60 (P-3, git grep zero hits); §4 establishes mechanical reachability by walking _classify clause-by-clause, which is a code-read claim and not a live-traversal claim. §7.1 is the discharge site.]`

> `[UV-P: CloudWatch Logs Insights returns discovered JSON boolean fields as strings, making bool("false") coerce to True at schema.py:270 | METHOD: deferred-to-E2-execution | REASON: asserted from the Logs Insights result-shape contract, not probed live in this session; the E2 procedure (§7.1) is constrained to raw-JSON ingestion so the wave does not depend on this claim's resolution either way]`

---

## §13 — Acid test

*Will this look obviously right in 18 months?*

The decision that will be re-examined is **§3.3: recompute the delivery hash rather than
thread one value into both emits.** The threading version is shorter and passes every test
that does not specifically look for tautology. If a future reader finds `h == h` in clause 4a
and asks "what were they thinking?", the answer must be legible: threading was rejected
because it converts an honestly-UNATTESTED gap into a **false attestation**, and the whole
point of this wave is that an instrument reading *armed* while detecting nothing is worse
than one that reads *unarmed*. That rationale is recorded here and in the companion ADR so it
survives the code.

The second is **§3.4's honest scoping**: this arms a standing invariant assertion with
regression-surveillance value, not a live hand-paste detector. Overclaiming that would have
been the easy paper win and the durable lie.
