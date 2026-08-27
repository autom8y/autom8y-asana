---
type: spec
artifact_subtype: tdd
status: proposed
date: 2026-07-07
initiative: client-onboarding-delivery
slug: floodgates-batch-seam
rung: authored (design altitude only — no production code)
scope: system-TDD (per-office batch orchestrator around the operator CF gate)
station: architect (design station)
telos: trust-first — make the whole ACTIVE set a repeatable one-command-per-office motion
routed_by: .ledge/reviews/CASE-pr205-v3-template-2026-07-07.md (§ "Hosting seam … floodgates build … Separate initiative")
reuses:
  - producer.freeze_walkthrough_deck (producer.py:128-278) — SOLE deck freezer
  - host_bundle.stage_deck_bundle (host_bundle.py:83-152) — audience-gate + stage + write-back parity
  - host_bundle.verify_bundle_parity (host_bundle.py:155-180) — served/frozen sha compare
  - link_on_play.post_link_on_play (link_on_play.py:203-265)
  - template_comment.post_template_comment (template_comment.py:288-376) — task-bound guid (C-1 closed)
  - contact_synthesis.post_contact_card (contact_synthesis.py:465-547)
  - autom8y_core.helpers.routing.format_routing_address (routing.py:75-110)
  - section_resolution.resolve_section_gids (section_resolution.py:19-64)
  - deck_manifests.assert_customer_deck / load_title (deck_manifests.py:78-124)
grounded_against: origin/main @ e95a9de6 (posters merged) + rep-template-v3 worktree c1025940 (template_comment merging)
---

# System-TDD — Foundation-First Floodgates Batch Seam

## 0. Grandeur anchor

> Make the whole ACTIVE set a repeatable **one-command-per-office** motion so the
> Nova operator can send in waves. The CF `wrangler pages deploy` is a RESERVED
> operator lever (surfaced, never auto-fired). The client SEND stays the
> operator's Nova/Intercom action. Proven by an **idempotent/resumable**
> orchestrator, not a one-off script.

This is the "floodgates build" that `CASE-pr205-v3-template-2026-07-07.md`
explicitly routed to 10x-dev as a **separate initiative** ("Build hosting seam +
batch runner separately; this PR gates on that work, not the reverse", CASE §
Cross-Rite Routing L-row). The v3 template-comment PR closed the pre-batch
blocker (C-1 cross-tenant post); this spec designs the machine that consumes it.

---

## 1. Ground truth — the REAL per-office pipeline (file:line grounded)

Verified by direct read. **Correction to the N0 brief:** the brief says the slug
is minted "at freeze/host time (`host_bundle.py:64`)". It is **not**.
`host_bundle.py:63-67` only *documents* `secrets.token_hex(16)` and defines
`_SLUG_RE`; `stage_deck_bundle` **takes a pre-minted `--slug`** (`host_bundle.py:88,
100-103, 125-129`). **No module in the repo mints the slug** — a full-repo grep
for `token_hex(16)` outside onboarding returns only `observability/correlation.py:28`
(`token_hex(2)`). Sand Lake's slug `207688021de88a6d7231e1d08ea77a85`
(`rep-onboarding-deck-email-template-v3-2026-07-07.md:208`) was minted **ad-hoc by
the operator**. **Owning the slug mint is therefore net-new work the orchestrator
must carry** (see §4 SLUG-1).

### 1.1 Produce / freeze — what freezing ONE office actually requires

The **sole freezer** is `producer.freeze_walkthrough_deck` (producer.py:128-278),
which shells `node build/inline.mjs` (producer.py:201-212, entrypoint
`producer.py:35`). Its inputs:

| Input | Source (proven) | file:line |
|---|---|---|
| `producer_dir` | vendored Node tree `vendor/deck-producer/` (has `build/inline.mjs`, `templates/`, `node_modules/`, `export/`) | producer.py:150-153; NODE_BUNDLING.md:11-21 |
| `deck_template` | `"email-forwarding-setup"` — the universal customer deck | constants.py:130 |
| `gated_address` | `format_routing_address(office_guid)` → `{guid}@appointments.contenteapp.com`; raises `ValueError` on bad guid | routing.py:75-110 |
| `client_name` | customer-plane display name (fault-13: **NOT** the Asana task name) | workflow.py:646; producer.py:160-169 |
| `title` | manifest-owned → `"Gmail Forwarding Setup"` | deck_manifests.py:78-109; `deck_manifests/email-forwarding-setup.json` |
| `out_filename` | any relative name (producer writes `export/<out>`) | producer.py:174-175 |

The producer refuses a non-canonical `--addr` fail-loud (`ADDR-NON-CANONICAL`,
inline.mjs:122-129; sentinel `producer.py:32`), and `freeze_walkthrough_deck`
re-validates the gated address is present in the frozen bytes
(producer.py:275-276). Node ≥22 + the vendored tree are **proven offline**
(NODE_BUNDLING.md:3-9; `scripts/smoke-freeze.sh` is the in-container GREEN/RED
smoke). **How Sand Lake was frozen:** by running this producer (the reference
invocation is `smoke-freeze.sh:44-51`), NOT via `OnboardingWalkthroughWorkflow`.

**The ACTIVE-enumerating `OnboardingWalkthroughWorkflow` (workflow.py:217) is a
different, heavier path and is NOT what freezes for the floodgates.** It:
- enumerates ACTIVE via `resolve_section_gids` over `CALENDAR_INTEGRATIONS_PROJECT_GID`
  (workflow.py:349-441; constants.py:76,85);
- resolves the row via the **autom8y-core SDK** `get_business_by_phone_async`
  (workflow.py:13-18; lambda_handlers/onboarding_walkthrough.py:60-85), needing
  `AUTOM8Y_DATA_URL` + S2S creds;
- runs a **W1 GFR by-GUID identity guard** needing a wired `query_engine`
  (workflow.py:656-803); unwired ⇒ every task fail-closes `anchor_unresolved`
  (workflow.py:664-674) and the sweep is LOUD-INERT at preflight (workflow.py:306-317);
- is **opt-in DISABLED** unless `AUTOM8_WALKTHROUGH_ENABLED=true` (workflow.py:280-294;
  constants.py:51) and **DEPLOYED-DARK** (lambda_handlers/onboarding_walkthrough.py:22-27);
- **produces an Asana ATTACHMENT** (upload-then-delete, workflow.py:21-23) — it
  does **not** host on Cloudflare, mint a slug, or post the 3 comments.

**Design consequence (load-bearing):** the floodgates orchestrator does **not**
use `OnboardingWalkthroughWorkflow`. It composes the *primitives*
(`freeze_walkthrough_deck` + `host_bundle` + 3 posters) directly, **pure-Asana**,
run **operator-side/local** — sidestepping the whole query_engine + SDK-resolver +
DEPLOYED-DARK Lambda residual (CON-2, NODE_BUNDLING.md:57-67). See §7.

### 1.2 Slug + host-stage

`host_bundle.stage_deck_bundle` (host_bundle.py:83-152): deny-first order —
audience gate `assert_customer_deck(deck_template)` (host_bundle.py:114-115) →
slug shape `_SLUG_RE` (host_bundle.py:125-129) → writes
`<deploy_root>/<slug>/index.html` verbatim + a `_headers` file
(host_bundle.py:135-139) → immediate write-back parity (host_bundle.py:142-143).
Nothing else is written into the deploy root (host_bundle.py:32-33) — any stray
file would be PUBLISHED by `wrangler pages deploy`. That deploy root is exactly
what `wrangler pages deploy <deploy_root>` consumes. **`wrangler` is nowhere in
this repo** (grep: no scripts, no module) — the deploy is fully manual (memory
scars: CF auth `direnv exec ~/life`; no `wrangler pages domain` verb at 4.107).

### 1.3 Byte-parity verify

`host_bundle.verify_bundle_parity(deploy_root, slug, expected_sha256)`
(host_bundle.py:155-180): the served-file SHA-256 must equal the frozen SHA-256 or
`BundleParityError`. `stage` runs it against the *staged* bytes pre-deploy; the
same predicate must be run against **`curl`-fetched served bytes** post-deploy
(host_bundle.py:158-162 says exactly this). Sand Lake's parity was proven this way
(cc9d171c byte-parity through the CF proxy — memory
`dc-render-remediation-first-client-send`). **Scar to carry:** hash-parity ≠
renders-correctly, and PV the LIVE deployed slug, not the local manifest.

### 1.4 The 3 posters — exact invocation contract

All three are single-`--task-gid` CLIs, default **dry-run**, `--execute` is the
sole mutating path, and each is **marker-idempotent** on the PLAY:

| Poster | Needs | Idempotency marker | Identity resolution | file:line |
|---|---|---|---|---|
| `link_on_play` | `--task-gid`, `--deck-url` | `[autom8y:link-on-play deck=<slug>]` | slug ← `deck_slug_from_url` (host-pinned `decks.cntently.com`) | link_on_play.py:56,97-118,203-265 |
| `template_comment` (v3) | `--task-gid`, `--deck-url`, `[--office-guid]`, `--clinic` | `[autom8y:rep-template deck=<slug>]` | guid **ALWAYS** resolved FROM the task (phone→Business→Company ID); explicit `--office-guid` only VERIFIES (`TaskOfficeMismatch`) | template_comment.py:84,232-261,288-376 |
| `contact_synthesis` | `play_gid`, `--deck-slug` | `[autom8y:contact-card deck=<slug>]` | office phone → Businesses-project Business → ranked contacts | contact_synthesis.py:76,374-414,465-547 |

**The #205 fix (load-bearing for the batch):** `post_template_comment` binds guid
to the TASK (template_comment.py:319-327) — the batch **must never** pass a
precomputed `(office_guid, task)` pairing, because CASE C-1 proved a scrambled
`task_gid` list posts every routing address to the wrong task while every guard
returns PASS (CASE-pr205 §C-1, §H-1). The orchestrator iterates **PLAY tasks** and
lets each poster resolve identity FROM the task — the slug is the only cross-poster
datum threaded in.

---

## 2. Orchestrator architecture

### 2.1 Ruling: single-office runner + thin batch loop (NOT a unified monolith)

**Chosen.** A `run_office(play_gid, phase, execute)` runner that is fully testable
in isolation (mirrors the existing single-`--task-gid` poster CLIs and the CASE
per-entity-isolation demand), plus a thin `run_batch(...)` that enumerates ACTIVE
and calls the runner per office, aggregating state.

**Rejected — unified monolith orchestrator:** the cross-tenant scar (CASE C-1)
makes a per-office **task-bound** runner strictly safer than a loop that holds
parallel arrays; and a single-office runner is the unit the operator can point at
one misbehaving office during a wave without re-running the fleet.

### 2.2 Module home + CLI

New subpackage `src/autom8_asana/automation/workflows/onboarding_walkthrough/floodgates/`:

| Module | Responsibility |
|---|---|
| `office_runner.py` | The two-phase single-office runner (`run_office`). Composes freeze → mint → stage (Phase-1); verify-served → post×3 → done (Phase-2). |
| `batch.py` | Enumerate ACTIVE (`resolve_section_gids`, §1.1) → loop `run_office`; the CLI entrypoint. |
| `state.py` | The per-office state manifest: model + atomic read/write, keyed by PLAY gid (§3). |

Plus **one small addition to the EXISTING `host_bundle.py`**: a `mint_slug()`
(`secrets.token_hex(16)`, validated by the already-present `_SLUG_RE`) — closes the
SLUG-1 gap in its natural home rather than a new module.

CLI shape (design sketch, not code):

```
python -m ...onboarding_walkthrough.floodgates.batch \
    --phase produce            # Phase-1 for all not-yet-produced ACTIVE offices
    [--office <play_gid>]      # scope to ONE office (the isolation door)
    [--state <path>]           # manifest location (default: repo-local .sos/floodgates/)

python -m ...floodgates.batch --phase resume [--office <play_gid>] --execute
    # Phase-2: after the operator confirms the deck(s) live on CF
```

Default is dry-run everywhere (`--execute` gates every Asana write, inheriting the
poster contract). `--phase produce` NEVER touches Asana (reads + freeze + stage +
manifest only); `--phase resume` is where the `--execute` posts happen.

---

## 3. State + idempotency / resumability

### 3.1 Where per-office state lives — a state manifest keyed by PLAY gid

The PLAY comment-markers are the posters' idempotency source, but they are
**insufficient as the orchestrator's state of record** because the slug exists
between freeze and the first post with **no durable home** (it lives only in the
deploy-root dir + process memory until a comment is posted). A crash there orphans
the slug. Therefore a durable **state manifest** is the resumability keystone.

`state.py` model (design sketch — one record per office):

```
OfficeState:
  play_gid: str                 # the key
  office_guid_masked: str        # first-8 only (never full guid at rest — mirror _mask_guid)
  clinic: str                    # customer-safe display name (see §7 DEP-2)
  slug: str                      # minted ONCE, pinned here (SLUG-1)
  deck_url: str                  # https://decks.cntently.com/<slug>/
  frozen_sha256: str             # the arm-2 oracle recorded at freeze
  phase: enum{ pending, produced, deploy_confirmed, posted, done }
  posts: { link: story_gid|null, template: story_gid|null, card: outcome }
  updated_at: iso8601
```

Written **atomically** (temp-file + rename) after each state transition, so a
crash leaves the manifest at the last committed phase.

### 3.2 Idempotency layering

- **Freeze/stage (net-new idempotency):** keyed by the manifest's recorded slug
  per `play_gid`. **If a slug exists for the office, REUSE it — never re-mint**
  (re-minting orphans the deployed deck). Re-freeze is allowed and deterministic
  for a fixed `(guid, name, title, template)`; the recorded `frozen_sha256` lets a
  re-run detect drift.
- **Posters (already marker-idempotent):** re-running `--execute` is a no-op when
  the slug-scoped marker exists (link_on_play.py:230-245; template_comment.py:344-357;
  contact_synthesis.py:482-495). The manifest slug is threaded into all three via
  `deck_url` / `--deck-slug` so the three markers are slug-consistent.
- **Skip-completed:** `run_batch` skips offices at `phase=done`; per office it
  resumes at the recorded phase.

### 3.3 Recovery if it dies mid-batch

Because the manifest is per-office and committed after each transition, and the CF
deploy is a natural HALT (§4), recovery is: re-run `--phase produce` (skips
produced offices, resumes any half-produced) → operator deploys → re-run
`--phase resume --execute` (skips posted offices). No global lock; per-office
isolation means one office's failure never blocks the wave.

---

## 4. The two-phase operator-gated flow (the halt/resume seam)

This seam is what makes it foundation, not a script. `run_office` is a **state
machine**, not a straight line.

### Phase 1 — `produce` (fully automatable; NO Asana writes, NO client contact)

Per PLAY gid:
1. **Preflight** — reuse `link_on_play._preflight` semantics (link_on_play.py:151-200):
   PLAY name convention + ACTIVE-section membership by CANONICAL resolved gid, or
   refuse. (Positive selection — the same C-1 defense.)
2. **Resolve office guid pure-Asana** — reuse `template_comment._resolve_office_guid`
   (template_comment.py:232-261): phone → Businesses-project Business → Company ID.
3. **Compose gated address** — `format_routing_address(guid)` (routing.py:75).
4. **Resolve `clinic` / `client_name`** — see §7 DEP-2 (the one genuine open input).
5. **Freeze** — `freeze_walkthrough_deck(...)` (producer.py:128) → `frozen_bytes`;
   record `frozen_sha256`.
6. **Mint slug** — `host_bundle.mint_slug()` **iff** the manifest has none for this
   office (SLUG-1 / §3.2).
7. **Host-stage** — `stage_deck_bundle(deck_template, frozen_artifact, slug,
   deploy_root)` (host_bundle.py:83) → audience gate + `<slug>/index.html` +
   `_headers` + write-back parity.
8. **Record** slug + `deck_url` + `frozen_sha256`; set `phase=produced`.

Then the orchestrator **SURFACES the exact command and HALTS**:

```
[HALT — operator lever] Deck staged for <clinic> at deploy_root <path>.
  Reserved CF deploy (run in the CF-authed env — direnv exec ~/life):
    wrangler pages deploy <deploy_root> --project-name <decks-project> --branch <...>
  Then confirm live and re-run:  --phase resume --office <play_gid> --execute
```

`produce` never posts, never sends. It stops at `phase=produced`.

### Phase 2 — `resume` (after operator confirms the deck is live)

Per office at `phase=produced` (or `deploy_confirmed`):
1. **Served byte-parity** — `curl` the live `deck_url` → SHA-256 → compare to the
   manifest `frozen_sha256` using the `verify_bundle_parity` predicate
   (host_bundle.py:155-180). Mismatch ⇒ LOUD refuse (do NOT post a link to a deck
   that isn't byte-identical). On pass: `phase=deploy_confirmed`.
   *(DEFER-WATCH: headless-render proof is a per-office STRONG lift, §7 DEP-4.)*
2. **Post link** — `post_link_on_play(--execute)` (link_on_play.py:203).
3. **Post template-v3** — `post_template_comment(--execute)`, guid resolved FROM
   the task (template_comment.py:288) — NO precomputed pairing.
4. **Post card** — `post_contact_card(--execute)` with `--deck-slug` = manifest slug
   (contact_synthesis.py:465).
5. **Mark done** — `phase=done`; record the three story gids.

The **client SEND is NOT here** — it is the operator's Nova/Intercom action,
surfaced by the template-v3 comment the poster staged onto the PLAY.

---

## 5. Reserved-lever boundary table

| # | Step | Orchestrator | file:line |
|---|---|---|---|
| 1 | Enumerate ACTIVE PLAYs | **DOES** | section_resolution.py:19; constants.py:76,85 |
| 2 | PLAY preflight (name + ACTIVE membership) | **DOES** | link_on_play.py:151-200 |
| 3 | Resolve office guid (pure-Asana) | **DOES** | template_comment.py:232-261 |
| 4 | Compose gated address | **DOES** | routing.py:75 |
| 5 | Resolve customer `clinic` name | **DOES** (source per §7 DEP-2) | workflow.py:646 |
| 6 | Freeze deck (Node producer) | **DOES** | producer.py:128 |
| 7 | Mint capability slug | **DOES** (net-new `mint_slug`) | host_bundle.py:63-67 |
| 8 | Host-stage (deploy-root, audience gate, write-back parity) | **DOES** | host_bundle.py:83-152 |
| 9 | **`wrangler pages deploy` (CF)** | **SURFACES + HALTS** — operator FIRES | (no repo artifact — manual) |
| 10 | Served byte-parity (post-deploy `curl`) | **DOES** | host_bundle.py:155-180 |
| 11 | Post link / template-v3 / card comments (`--execute`) | **DOES** (stages PLAY comments, NOT client sends) | link_on_play.py:249; template_comment.py:361; contact_synthesis.py:535 |
| 12 | **Client SEND (Nova/Intercom)** | **NEVER** — operator's action | (surfaced via the staged v3 comment) |
| 13 | Mark office done | **DOES** | state.py (net-new) |

Two reserved levers, both irreducibly operator: **#9 CF deploy** and **#12 client
SEND**. Everything else the machine owns.

---

## 6. G-PROVE citation index (every machinery claim)

| Claim | file:line |
|---|---|
| Slug NOT minted in-repo; `stage` takes pre-minted `--slug` | host_bundle.py:63-67, 88, 100-103, 125-129 |
| `stage_deck_bundle` audience-gate → write `<slug>/index.html` + `_headers` → parity | host_bundle.py:114-143 |
| `verify_bundle_parity` served==frozen sha | host_bundle.py:155-180 |
| `freeze_walkthrough_deck` inputs + shells node producer + re-validates addr | producer.py:128-212, 275-276 |
| Producer vendored + proven offline | NODE_BUNDLING.md:3-21; vendor/deck-producer/build/inline.mjs:77-130; scripts/smoke-freeze.sh |
| Universal customer deck + manifest title | constants.py:130; deck_manifests.py:78-124; email-forwarding-setup.json |
| Workflow enumerates ACTIVE / attaches (not hosts) / opt-in-DARK / needs query_engine+SDK | workflow.py:21-23, 217, 280-317, 349-441, 646, 656-803; lambda_handlers/onboarding_walkthrough.py:22-104 |
| Pure-Asana guid resolve + task-bound (C-1 closed) | template_comment.py:232-261, 319-327 |
| Posters marker-idempotent + host-pinned | link_on_play.py:56,97-118,230-245; contact_synthesis.py:76,482-495 |
| `format_routing_address` guid→addr, raises on bad | routing.py:75-110 |
| CASE routes floodgates as separate build; batch NO-GO until C-1 closed | CASE-pr205-v3-template-2026-07-07.md:18, 61-108 |
| Sand Lake slug/URL/PLAY gid | rep-onboarding-deck-email-template-v3-2026-07-07.md:208-212 |

**UV-P (verify live at run, not asserted here):** the 8 ACTIVE offices, ACTIVE
section gid `1209442954085037`, and that 7/8 remain unhosted are N0-recon inputs —
the enumeration MECHANISM is grounded (§1.1); the live count is re-verified by
`--phase produce` itself.

---

## 7. The hardest dependency, honestly

**Headline: the Node producer substrate is NOT a blocking sub-project for a
LOCAL/operator-run MVP — it is already vendored and offline-proven.** The blocking
narrative in the N0 brief applies to the *Lambda/ECS deploy* of the producer
(CON-2), which the MVP deliberately does not need.

| Dep | Status | Verdict |
|---|---|---|
| **DEP-1 Node producer** | Vendored `vendor/deck-producer/` w/ `node_modules`; Node ≥22 offline-proven (NODE_BUNDLING.md:3-9; smoke-freeze.sh) | **NOT blocking.** Orchestrator runs `freeze_walkthrough_deck` locally in the repo env. The Lambda-deploy residual (CON-2) is a DIFFERENT, out-of-scope problem. |
| **DEP-2 `client_name` provenance** | fault-13 blessed **only** `BusinessRecord.business_name` (SDK), NOT the Asana task name (workflow.py:646) | **The one genuine open input.** Pure-Asana has no fault-13-blessed name source. **MVP: operator-confirmed `clinic` per office** (7 offices, one-time), gated through `personalization_gate.assert_customer_personalization` (the same gate the workflow uses). **Full: SDK `get_business_by_phone_async` name** as an opt-in when `AUTOM8Y_DATA_URL` creds are present locally — reuses the blessed source without the query_engine/Lambda weight. |
| **DEP-3 CF `wrangler` deploy** | No repo artifact; manual; no domain verb at 4.107; auth `direnv exec ~/life` | **Not a gap — the reserved lever by design.** Surfaced, never automated. |
| **DEP-4 served render proof** | Byte-parity is mechanical (host_bundle.py:155); "hash-parity ≠ renders-correctly" (memory) | **MVP gate = served byte-parity.** Headless-render proof is a per-office STRONG lift → **DEFER-WATCH** (Phase-2 hardening). |
| **DEP-5 slug mint** | No module mints it (§1) | **Net-new, trivial** — `host_bundle.mint_slug()` (`secrets.token_hex(16)` + `_SLUG_RE`). |

### 7.1 Anti-goal (scope wall)

Full **scheduled Lambda** automation of the whole motion is an **anti-goal**: the
CF deploy (#9) and client SEND (#12) are reserved operator levers, so an
end-to-end unattended pipeline is neither wanted nor safe. The
`OnboardingWalkthroughWorkflow` Lambda residual (query_engine + SDK + CON-2 +
DEPLOYED-DARK) is therefore explicitly **out of scope** for floodgates.

---

## 8. Phased build plan

### MVP — **1 sprint** — "first non-Sand-Lake office, end to end"

Build `floodgates/` (`office_runner`, `batch`, `state`) + `host_bundle.mint_slug`.
Pure-Asana identity; `clinic` operator-confirmed + personalization-gated (DEP-2
MVP). Two-phase `produce` / `resume --execute` around the surfaced `wrangler` HALT.
Served byte-parity gate in Phase-2. Single-office `--office` isolation. Atomic
per-office manifest.
- **Done-bar:** `--office <one live non-Sand-Lake PLAY>` runs `produce` (stages +
  surfaces the deploy) → operator deploys → `resume --execute` posts all three
  comments idempotently, byte-parity-gated. Re-run is a no-op.
- **Why 1 sprint:** every primitive already exists and is proven — producer
  (vendored + smoke), `host_bundle` (merged), 3 posters (merged / merging), pure-
  Asana guid bridge (8/8 proven), `format_routing_address` (proven). Net-new is
  glue + state + `mint_slug`.

### S2 — hardening (**+1 sprint**) — "wave-ready across all 7"

SDK `client_name` opt-in (DEP-2 full); headless-render verify per office +
DEFER-WATCH closure (DEP-4); `--phase produce` over the full ACTIVE set with a
combined deploy-root option; batch summary report (green/red per office);
`_business_gid_by_phone` returns-None + ambiguity refusals surfaced per office.

### S3 (optional / likely never) — scheduled automation

Explicitly gated by the §7.1 anti-goal. Only revisit if the reserved-lever
doctrine changes.

---

## 9. Open questions for the operator

1. **DEP-2:** confirm MVP `clinic` = operator-confirmed-per-office (gated), or
   require the SDK-name source (needs local `AUTOM8Y_DATA_URL` creds)?
2. **Deploy-root granularity:** one deploy-root per office (simplest HALT/resume,
   one `wrangler` per office) vs one combined deploy-root for a wave (one
   `wrangler`, N slugs)? MVP proposes **per-office** (cleanest isolation); S2 adds
   the combined option.
3. **State manifest home:** repo-local `.sos/floodgates/<batch>.json` (ephemeral,
   git-ignored) vs a durable committed ledger. MVP proposes repo-local ephemeral.

---

## 10. Design summary

The floodgates orchestrator is a **per-office two-phase state machine** that
composes already-proven primitives **pure-Asana, operator-run**, NOT the
DEPLOYED-DARK `OnboardingWalkthroughWorkflow`. Phase-1 (`produce`) resolves guid →
address → freezes → **mints the slug (net-new)** → host-stages → records state, then
**surfaces the `wrangler` command and HALTS**. The operator fires the reserved CF
lever. Phase-2 (`resume --execute`) verifies served byte-parity, then posts the
three marker-idempotent PLAY comments and marks the office done. The client SEND
stays the operator's. A durable per-office manifest (keyed by PLAY gid, atomic
writes) makes it resumable; slug-reuse + comment-markers make it idempotent. The
hardest real dependency is not the Node substrate (vendored + proven) but the
fault-13 `client_name` provenance — solved for the MVP by operator-confirmation +
the existing personalization gate.
