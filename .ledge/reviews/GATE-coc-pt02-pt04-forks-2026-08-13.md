---
type: review
artifact_type: GATE
artifact_id: GATE-coc-pt02-pt04-forks-2026-08-13
initiative: chain-of-custody-closure
date: 2026-08-13
author: pythia (ecosystem navigator — routing/adjudication seat)
checkpoints: [PT-02, PT-04]
forks_presented: [F-1, F-7, F-8, RE-2-severity-determinant]
forks_resolved: NONE
status: draft
lifecycle_state: AUTHORED-UNMERGED (F-A terminal state this wave; Q-4 HALT; main thread owns git)
binds: NOTHING
self_assessment_ceiling: MODERATE (F-C — single seat, self-ref)
grounds_on:
  - .ledge/decisions/SLATE-re1-warm-path-options-2026-08-13.md
  - .ledge/reviews/CRITIQUE-re1-slate-2026-08-13.md
  - .ledge/reviews/RECON-gitleaks-enforcement-locus-2026-08-13.md
  - .ledge/reviews/CRITIQUE-cc6-gitleaks-recon-2026-08-13.md
  - .ledge/reviews/CRITIQUE-cc3-blast-radius-2026-08-13.md
  - .ledge/decisions/DESIGN-re2-two-layer-authz-2026-08-13.md
  - .ledge/reviews/CRITIQUE-re2-design-2026-08-13.md
  - .ledge/decisions/RULING-operator-coc-defaults-ratification-2026-08-13.md
  - .sos/wip/frames/chain-of-custody-closure.md (§9, §10)
  - .sos/wip/frames/chain-of-custody-closure.shape.md (CC-7, E1)
---

# GATE — PT-02 / PT-04 operator decision surface

> **What this is.** Three decision surfaces, options enumerated before any is
> recommended. **F-1 is HALTING and is presented UNRESOLVED.** F-7/F-8 carry
> ratified defaults and are presented as CONFIRM-WITH-NEW-EVIDENCE. The RE-2
> severity determinant is a third, cheap surface that surfaced during Phase 1.
>
> **What this is NOT.** A ruling. Nothing here resolves F-1, F-4, F-7, F-8, the
> RE-2 remediation, or GATE-FORK. Every one stays the operator's. This seat
> holds no authority over any of them and asserts none.

---

## §0 — Standing at a glance

| surface | checkpoint | ratified default | disposition here |
|---|---|---|---|
| **F-1** — RE-1 ownership + scope | PT-02 | **NONE** (Q-3 HALT, `RULING…:54-57`) | **PRESENTED, UNRESOLVED.** CC-5 stays SHUT |
| **F-7** — gitleaks baseline | PT-04 | enforce-with-baseline (Q-6, `RULING…:36-39`) | **CONFIRM** — default now evidence-backed, with a scope extension |
| **F-8** — fix locus | PT-04 | prefer in-repo (Q-8, `RULING…:42-44`) | **CONFIRM-WITH-NARROWING** — viable, no halt, but two-action not one |
| **RE-2 severity** | surfaced | none (not previously a named fork) | **FRAMED** — one cross-repo yes/no moves High↔Critical |

**Every Phase-1 negative STANDS.** NR-4 (RE-1) stands under live re-derivation;
NR-5 (gitleaks) stands; the RE-2 authz gap is verified real. Nothing below rests
on an unverified premise, and where a residual is open it is named as such.

---

# PART A — PT-02 · F-1 (RE-1 ownership + scope) · HARD, HALTING

## A.1 — The receipted floor (what is no longer in question)

The warm path never reaches offers. This is not inferred from a single seat:

- **0 of 325 runs** reach offer, re-derived **own-hands against live production
  CloudWatch Logs today**, not inherited from the PROBE
  (`CRITIQUE-re1-slate-2026-08-13.md:229-233`).
- The structural mechanism is derived from code control flow, not merely
  observed: `total_tasks` (`story_warmer.py:85`) increments **before** the chunk
  loop and therefore crosses offer's boundary every run, while `success`
  (`:136`) increments only **inside** the loop, past the timeout check (`:114`).
  One counter crosses 10,616; the other freezes at ~7,455
  (`CRITIQUE-re1-slate…:180-201`).
- The refuter that could have inverted everything — *"is the zero an unemitted
  metric?"* — was swept hardest and **did not fire**
  (`SLATE…:91-96`; `CRITIQUE-re1-slate…:170-287`).
- The Tier-1/Tier-2 population arithmetic reproduces from live logs
  independently: `14,808 − 10,616 = 4,192` (offers) and
  `59,278 − 10,616 = 48,662` (full starved set)
  (`CRITIQUE-re1-slate…:236-242`).

**The receipted zero is real.** F-1 is therefore a decision about *what to do
about a known condition*, not a decision under uncertainty about the condition.

## A.2 — The four questions this gate was asked to answer FOR the operator

### Q1. Is the slate EXHAUSTIVE before recommendatory? — **YES**

Eight options are enumerated in §3 (`SLATE…:125-171`) before §7 declines to
recommend (`SLATE…:260-289`). All probe-named shapes are present, **plus**
routed-out as a first-class option:

| # | option | one-line mechanism |
|---|---|---|
| **O-A** | offers-only dedicated warm | targeted second pass on the offers project GID (`SLATE…:131`) |
| **O-B** | rotate iteration start offset | entities take turns leading the cascade (`:137`) |
| **O-C** | dedicated invocation | story warming gets its own Lambda budget (`:142`) |
| **O-D** | consumer-demand ordering | warm what gets read (`:147`) |
| **O-E** | **routed-out with a named owner** | F-1 assigns the fleet redesign elsewhere (`:152`) |
| **O-F** | round-robin interleave | every entity gets partial budget every run (`:158`) |
| **O-G** | raise budget / concurrency | widen `Semaphore(3)` / timeout (`:163`) |
| **O-H** | disclosure-only (the null) | never warm; make option (g) read *honestly empty* (`:168`) |

**O-E is genuinely first-class, confirmed by the rite-disjoint critic**, not a
disguised failure: it is the only row priced at true zero cost in this lane, and
the critic read the PROBE's own §3.3 text directly rather than through the
slate's paraphrase to confirm the fleet-wide framing is the PROBE's, not the
slate author's (`CRITIQUE-re1-slate…:293-303`). The critic also read every option
section looking for smuggled steering and **found no ranked preference and no
"recommended" language** (`:328-335`).

**Two options are honestly self-deprecating rather than padded** — worth the
operator's eye because they are the ones most likely to look attractive and fail:
- **O-G** is listed for completeness but the shortfall is *ordering*-structural,
  not *budget*-structural: reaching offer's end needs roughly a **2× throughput
  doubling** (7,460 → ≥14,808) inside a 15-min ceiling, while raising concurrency
  raises 429 pressure on the documented storm surface (`SLATE…:163-166`).
- **O-D** needs a demand signal **that does not exist**: the endpoint has zero
  traffic today, so "demand for offers" is presently unmeasurable — a
  chicken-and-egg the slate names against its own option (`SLATE…:149-150`).

### Q2. Are the two scope tiers priced SEPARATELY? — **YES, and the arithmetic was independently re-derived**

| | **Tier 1 — OFFERS-ONLY** | **Tier 2 — FULL STARVED SET** |
|---|---|---|
| population | **4,192 tasks** (1 entity) | **~48,662 tasks** (12 entity types) |
| dedicated warm time | **~6–8 min/pass** | **~65–90 min/pass** |
| fits one Lambda invocation? | **Yes** | **No** — exceeds by ~4–6×; needs multi-invocation / fan-out |
| blast radius | one project GID | twelve entity types, each with its own consumers |
| is this repo's to decide? | plausibly (bounded, in-`src/`) | **this is the fleet-warmer redesign the fences forbid building here** |

Source: `SLATE…:107-115`. Both tiers' arithmetic reproduced from the critic's own
live log queries (`CRITIQUE-re1-slate…:305-313`).

**The load-bearing separation:** *mechanism* (which lever) and *scope* (which
tier) are **orthogonal**. Every warming option can be scoped to Tier 1 **or**
Tier 2. The slate carries an explicit warning against conflation — *"Do not let a
cheap Tier-1 price smuggle in a Tier-2 commitment"* (`SLATE…:120-121`) — and the
critic verified no smuggling occurred.

> **This is what makes F-1 the operator's fork rather than a technical
> selection.** A ~6–8 min bounded in-repo job and a ~65–90 min twelve-consumer
> fleet redesign are the same *sentence* ("warm the offers") at two different
> blast radii.

### Q3. Is DF-4 priced (AL-5 producer-deploy interaction)? — **YES, 9/9 rows, no option silently exempted**

**The rule:** any WS-C fix is a **producer deploy** that moves/re-arms the AL-5
sample window, which opens **~2026-08-15T12:45Z**, *regardless of when the merge
fence lifts* (`SLATE…:199-206`). The mechanism is confirmed at
`cache_warmer.py:1159-1166` — story warming piggybacks the **same Lambda
invocation and same `context`** as the frame warmer, so any change to how that
shared budget is spent is a freshness-producer change for the frame path too
(`CRITIQUE-re1-slate…:315-326`).

**Which options do NOT re-arm AL-5** (the cheap-DF-4 set):

| option | freshness-producer deploy? | AL-5 disturbance |
|---|---|---|
| **O-E** routed-out | **No deploy in this lane** | **zero** |
| **O-H** disclosure-only | No (read-payload change) | **zero** — deployable any time |
| **§4 receipt shape** | No (instrumentation only) | **zero** — deployable any time |
| O-A / O-C / O-D | Yes | one clean boundary if landed before window open |
| **O-B / O-F** | Yes, **intermittently** | **fuzzy boundary** — highest O-7a bookkeeping cost; no single before/after cut |
| **O-G** | Yes | boundary **plus a confound** — 429 storm could itself spike frame staleness, contaminating AL-5 in the opposite direction |

Source: `SLATE…:218-230`.

> **⏱ A TIMING INPUT THAT DECAYS.** Today is 2026-08-13; the AL-5 window opens
> **~2026-08-15T12:45Z** — roughly **two days**. Any warming option landed before
> that instant buys **one clean regime**; landed after, **O-7a segmentation
> becomes mandatory**, and for the intermittent options (O-B/O-F) it is expensive
> and fuzzy. This does not pressure the ruling — O-E, O-H, and the receipt shape
> all cost zero here — but the *cheap-clean-regime* branch of the option space is
> the part with an expiry.
>
> The window-open timestamp itself is carried **UV-P** by the slate (not
> re-verified own-hands this sprint) and the critic confirmed that UV-P label is
> correctly applied (`SLATE…:204-206`; `CRITIQUE-re1-slate…:322-326`).

**R-9 trap, carried verbatim:** *do not misread a post-deploy AL-5 green as
staleness cured* — it may be the warm fix or the deploy, not the regime
(`SLATE…:214-216`).

### Q4. The cross-fork note — **STATED, NOT RULED**

**RE-1 sits on GATE-FORK's option-(g) critical path** (*warm → measure →
decide*), per `chain-of-custody-closure.md:470` (DF-5). **Therefore F-1's ruling
is also a GATE-FORK-timing input.**

**GATE-FORK is NOT ruled here and is not this envelope's** — it remains deferred
and honestly waitable on UV-P-2's answer (the pulse-check was sent 2026-08-13;
the answer is pending) (`chain-of-custody-closure.md:483`;
`RULING…:105-106`). This gate states the coupling and stops.

## A.3 — The decision axes, in order (verbatim structure from `SLATE…:264-281`)

1. **Is option (g)'s retrospective half actually NEEDED for Mission A?**
   - **No** → **O-H** (disclosure-only) or **O-E** (route it out). Both
     first-class; both ~zero DF-4 cost.
   - **Yes** → continue.
2. **Tier 1 (offers-only) or Tier 2 (full starved set)?** — the blast-radius
   fork. Tier 2 is the fleet redesign this lane is fenced from building → **O-E
   with a named owner** is the structurally-honest disposition for Tier 2.
3. **If Tier 1: which lever?** — steady-state guarantee (**O-C**, most infra) ·
   intermittent-cheap (**O-B/O-F**, redistribution) · targeted pass (**O-A**, new
   API budget + 429 risk) · demand-reorder (**O-D**, needs a signal that does not
   exist) · **O-G** low-confidence.
4. **Deploy timing vs AL-5** — the §4 receipt ships clean any time; land any
   warming fix **before ~2026-08-15T12:45Z** or pay O-7a segmentation.

## A.4 — The hazard that survives EVERY option except a real warm

Carry this regardless of the ruling: the first authenticated call to
`GET /api/v1/offers/section-timelines` returns a payload **~100% imputed and
visually indistinguishable from a fully-observed one** — it reads as *"these
offers have not moved"* when it means *"we have never observed these offers."*
And because ~4,192 misses ≫ 50, that call takes the no-op branch and **writes
nothing**, so it does not improve the next call
(`SLATE…:283-289`; mechanism at `section_timeline_service.py:505/:532`).

Disclosure is necessary under every option **except** a real warm.

## A.5 — Disposition

> ## ⛔ F-1 IS PRESENTED AND NOT RESOLVED.
>
> **F-1 has no default that resolves it** (Q-3 HALT STANDS — *"RE-1 ownership +
> locus is operator-only and unresolved"*, `RULING…:54-57`).
>
> **CC-5 does not open until the operator rules ownership AND scope** — both, not
> either. A ruling naming a lever without naming a tier does not open CC-5; a
> ruling naming a tier without naming an owner does not either.
>
> **Any seat treating the slate as a decision is over-reading** (`RULING…:56-57`).
> This gate makes the fork *priced*, not *decided*.

**Repairs pending (non-material, no disposition changes):** three citation
anchors in the slate need repair — `story_warmer.py:159` should be `:157`, and
the cache-fill-on-read sub-citation's `:34`/`:30` should be the def-site and
`:97-98`/`:100`. Every substantive claim they support was independently
re-derived through a different route (`CRITIQUE-re1-slate…:58-65, :85-111,
:374-379`).

**Nulls carried, unresolved by either seat:** (1) whether an offer GID could also
be a member of an earlier-warmed entity's DataFrame — no mechanism producing it
was found by either party; (2) whether future `warm_priority` ties could
reintroduce a hash-order hazard — none exist today, all 16 registry priorities
distinct (`CRITIQUE-re1-slate…:339-357`).

---

# PART B — PT-04 · F-7 / F-8 (gitleaks baseline + fix-locus)

**This is a CONFIRM-with-new-evidence, not a blind fork.** Both carry ratified
defaults. Both defaults survive the new evidence — one is *strengthened*, one is
*narrowed*.

## B.1 — F-7 (baseline) — the default is now EVIDENCE-BACKED

**Ratified default:** enforce-with-baseline (Q-6 RATIFIED-CONDITIONAL — *"the
baseline fork may dissolve on CC-6's answer; if it fires, the default is
enforce-with-baseline"*, `RULING…:36-39`).

**F-7 did NOT dissolve. It fires, and the default is the right one.** CC-6
answered UV-P-CoC-4 **YES** — an enforcing run **would** trip on the historical
cred-t21 leak. Four factors compound and **none of the suppressors are present**
(`RECON…:116-164`; re-swept own-hands at `CRITIQUE-cc6…:181-221`):

1. **Full-history scan** — `fetch-depth: 0` on checkout.
2. **`detect` walks full `git log -p`** — no `--log-opts` range restriction is
   passed, verified against the gitleaks v8.24.3 README.
3. **cred-t21 is in main-branch history** — absent-at-HEAD is irrelevant to a
   history-mode scan.
4. **The local rule already exists and fires; nothing suppresses it** — this
   repo's `.gitleaks.toml` carries a purpose-built `asana-native-pat` rule
   (`:52-56`) and `[allowlist].paths` exempts only `\.claude/.*\.md$`
   (**markdown-only**), which does **not** match the `.json` path that carried the
   leak. The critic went one hop further and **tested the regex against synthetic
   tokens of the documented shape** (CR-5-safe, never the real value): the `1/`
   and `2/` native-PAT forms **MATCH** (`CRITIQUE-cc6…:196-221`).

### The correction the operator most needs to see

> **"Rotate-then-enforce" is incomplete as a two-step sequence. It is really
> "rotate + baseline-then-enforce" — and the BASELINE is the step that actually
> unblocks CI, not the rotation.**
> (`RECON…:166`; survives attack at `CRITIQUE-cc6…:223-229`.)

gitleaks pattern-matches **git history**, not token liveness. A
rotated-but-still-present-in-history string still matches the rule and still
trips the scan. **Rotation (F-2) closes live-credential risk; it does not green
the gate.** The two are orthogonal, and F-7 does not wait on F-2.

### Scope extension the critic added — **the baseline is wider than cred-t21**

Two precision notes that **extend, not refute**, the corollary
(`CRITIQUE-cc6…:231-239`):

- **The baseline is FINGERPRINT-keyed, not commit-keyed.** `.gitleaksignore`
  keys on `commit:file:rule:line`, not a bare commit SHA. The artifact must carry
  the **findings' fingerprints**, not the three commit hashes.
- **It must cover EVERY historical finding that trips — not only cred-t21's three
  commits.** If any other historical secret exists in this repo's history (the
  memory index references residual leaked-PAT / `#927` items), it too must be
  baselined **or the gate stays red**. Scope the baseline to the **full tripping
  set**.

**F-7 options:**

| # | option | status |
|---|---|---|
| **(i)** | **enforce-with-baseline** — baseline the full historical tripping set (fingerprint-keyed); gate bites on NEW instances | **RATIFIED DEFAULT · now evidence-backed** |
| **(ii)** | rotate-then-enforce | **evidence says INCOMPLETE as stated** — rotation does not green the gate; this collapses into (i) plus a rotation that F-2 reserves anyway |
| **(iii)** | do not enforce | not proposed by any seat; leaves predicate (iii) unmet and the wave's premise open |

**Bounded residual, named not dismissed (CR-5):** the regex was validated against
the **documented** PAT shape, not the real token. It assumes lowercase hex, gid
≥6 digits, hex ≥32 chars. If the leaked token deviated (uppercase hex, shorter
fields) the rule would silently not fire. **This residual cannot be closed
without reading the credential, which CR-5 forbids**
(`CRITIQUE-cc6…:212-221`). Practical effect: it could make the gate trip *less*
than expected, never more — it does not weaken the case for a baseline.

## B.2 — F-8 (fix locus) — default viable, **no halt**, but NARROWED

**Ratified default:** prefer in-repo (Q-8 — *"WS-D prefers the in-repo locus; if
CC-6 finds the gate can only bite cross-repo, that surfaces as an operator fork
at PT-04 — never built unilaterally"*, `RULING…:42-44`).

> ## ✅ **F-8 DOES NOT FIRE.** The in-repo locus (c) is viable; the gate is not cross-repo-only.
> Both CC-6 and its rite-disjoint critic concur (`RECON…:197`;
> `CRITIQUE-cc6…:264`).

**The single bypass, located own-eyes and re-fetched byte-identical by two
seats:** one `|| true` at the "Run gitleaks" step of `security-gitleaks.yml` in
`autom8y/autom8y-workflows` @ `f5601acb…` (`RECON…:39-57, :88`;
`CRITIQUE-cc6…:38-55`). Every local control surface this repo owns —
permissions, concurrency, required-check registration, input plumbing, trigger
coverage — is **already correctly configured** (`RECON…:201-214`).

### The two live loci

| | **(a) upstream `autom8y-workflows` edit** | **(c) local enforcing job + registration** |
|---|---|---|
| **change** | remove `\|\| true` from the reusable workflow's run step | add a local job that runs gitleaks without the swallow |
| **actions required** | **ONE** — same reusable job, same registered check name, **bites automatically** | **TWO** — the job **plus** a branch-protection contexts edit |
| **authority** | **cross-repo; not solo-viable from this envelope** — PR + review + merge in a repo this session cannot write to | **fully local** for the job; the registration is a **repo-admin act** |
| **blast radius** | **org-wide** — fixes the class for every consumer; but any other consuming repo with its own unaddressed historical leak goes **instantly CI-red** on adoption. Consumer count **not enumerated** (out of envelope) | none outside this repo |
| **cost** | none in-repo | duplicates the install+run sequence the org centralizes (SCAR-PC-002/004-shaped divergence) |
| **verdict** | **durable / org-correct**, slowest, highest authority | **fastest to ship**, needs the second action or it does not bite |

Sources: `RECON…:172-192`; `CRITIQUE-cc6…:247-264`.
**(b)** — re-point to an enforcing variant — **is not independently available**:
no enforcing variant exists upstream today, so it collapses into (a)
(`RECON…:176-181`). **(d)** — branch-protection registration — is **not a
separate locus**; see the narrowing below.

### ⚠ THE NARROWING — AR-1, a material correction to the F-8 input

CC-6 concluded *"fixing (a) or (c) alone is sufficient … the remediation surface
is narrower than 'gate config + branch protection both need fixing'"*
(`RECON…:187-192`). **The critic proved this TRUE for (a) and FALSE for (c)**
(`CRITIQUE-cc6…:99-149`).

**Mechanism, verified empirically against live check-runs — not theorised:** the
composite check name `gitleaks / Secrets Scan` arises **only** from
reusable-workflow nesting (`{calling job name} / {called workflow's job name}`).
A plain local job reports under a **simple** name. This dichotomy is observable
in this repo's own live check-run list: every plain job carries a simple name
(`dispatch`, `Fleet Schema Governance`, `Lint noqa Drift Guard (RUF100)`), while
**only** reusable-called jobs carry the `X / Y` composite
(`CRITIQUE-cc6…:104-112`).

Branch protection requires the literal string `"gitleaks / Secrets Scan"`
(strict, `enforce_admins: true`) — and the live reported name matches it
byte-for-byte today (`CRITIQUE-cc6…:80-94`). **A new local job will not report
under that name.** Two failure modes follow:

| mode | what happens | result |
|---|---|---|
| **(c) alongside** the delegated job | old delegated job keeps reporting **green** (`\|\| true` unchanged); new enforcing job reports **red** under an **unregistered** name | **red job does not block the merge → silent non-biting gate** — the exact class this wave exists to close |
| **(c) in place of** the delegated job | required context `gitleaks / Secrets Scan` **never reports** → GitHub holds it **PENDING** | **merges block indefinitely** on a check that can never go green |

The only escape without a branch-protection edit is hand-crafting the local job's
`name:` as the literal `"gitleaks / Secrets Scan"` — **a fragile spoof the critic
neither identified as sound nor endorsed** (`CRITIQUE-cc6…:129-132`).

### Two consequences the operator should see before CC-7 opens

**1. (c) collides with CC-7's declared PR boundary.** CC-7 is scoped to **ONE
PR** in `autom8y-asana` `.github/workflows/`
(`chain-of-custody-closure.shape.md:519`), while its exit criterion 1 requires
*"the red path reaches the surface that actually blocks a merge (NR-6(d))"*
(`…shape.md:530-532`). **Under locus (c) those two cannot both be satisfied by a
workflow-file PR** — the biting half is a branch-protection settings change, not
a file in `.github/workflows/`. Under locus (a) there is no collision (same
registered name, bites automatically) but the PR is cross-repo. **This is a real
scope question, not a footnote.**

**2. Ordering hazard if (c) is chosen — register AFTER the job lands, never
before.** Registering the new context while the enforcing workflow is still held
un-merged (Q-4 / CC-1 hold all merges) creates a required check that **cannot
report** — which, the moment the fence lifts, blocks every merge on a permanently
pending check (AR-1 mode 2). The sequence must be *land the job, then register
the context*, never the reverse.

## B.3 — Does CC-7 proceed on the confirmed defaults? — **FRAMED, operator decides**

Under the shape's own gate logic, the defaults **do** open CC-7: F-7 fired (not
dissolved) and enforce-with-baseline governs; F-8 did not fire
(`…shape.md:745-747`). **But AR-1 changed CC-7's shape after that logic was
written.** Three postures:

| # | posture | what it means | cost |
|---|---|---|---|
| **(1)** | **Proceed on defaults, in-repo (c)** | CC-7 opens now; janitor builds the job + baseline; the **branch-protection registration is surfaced as a second, operator-reserved act** and CC-7's PR boundary is explicitly widened or split | fastest; requires the operator to accept a **two-action** CC-7 and an amended PR boundary |
| **(2)** | **Rule the locus first, then open CC-7** | operator picks (a) or (c) before the build starts; CC-7 opens with an unambiguous boundary | one operator act's delay; removes the boundary collision entirely |
| **(3)** | **Proceed on (a) — upstream** | durable/org-correct, bites with no registration | **not solo-viable from this envelope**; needs cross-repo authority + an unenumerated org-wide blast-radius check first |

**This gate does not choose among them.** Note only: **postures (1) and (2)
differ mainly in *when* the operator spends the same ruling** — (1) spends it at
CC-7's exit, (2) at CC-7's entry. Posture (3) is a different authority envelope
altogether and would need the consumer-count enumeration that `RECON…:236`
explicitly leaves out of scope.

**Untouched throughout:** F-2 (cred-t21 rotation) remains **operator-only,
runbook ready, currently disabled** (Q-5 DEFER, `RULING…:34-35`). Nothing in F-7
or F-8 performs, schedules, or prepares it — and per B.1, nothing in them
*depends* on it.

---

# PART C — THE RE-2 SEVERITY DETERMINANT (third surface, cheap)

## C.1 — What is verified, and what is not

**VERIFIED — the authz gap is real (High).** The Asana S2S write routes perform
**zero write-class authorization**. `require_service_claims` validates token-type
and fleet audience, captures `scope`/`caller_service` **for logging only**, and
returns claims with no `has_scope` / `has_permission` / service allowlist. The
sibling `admin.py` route **does** gate on `claims.permissions` — proving the
omission on the write routes is a **genuine gap, not an intended design**. There
is no fleet `asana:write` scope to check even if one were added. This is a real
CWE-862 Missing-Authorization defect (`CRITIQUE-cc3…:171-178`).

**NARROWED — from Critical to High, on one untraced control.** The S2S write
routes sit behind `JWTAuthMiddleware` with `require_business_scope=True`
(`main.py:445`). Its precedence (`middleware.py:246-300`) is:

1. `bypass_scope_enforcement is True` → **allow**
2. truthy `business_id` → **allow**
3. else → **reject 400 AUTH-TEB-004**

And the claims defaults (`claims.py:134,175`) are `bypass_scope_enforcement =
False`, `business_id = None`. **This is a real gate, not a no-op** — the original
Critical framing asserted past it without tracing it
(`CRITIQUE-cc3…:123-136, :180-188`).

## C.2 — The determinant

> ### One cross-repo yes/no:
> ### **Are the AI-agent seats `ace` / `iris` provisioned as exempt-SAs carrying `bypass_scope_enforcement=True`?**

| answer | what it implies |
|---|---|
| **NO** (or business-scoped) | the business-scope middleware **bounds** the finding. **F-001 stays High**: a real missing-write-class-authorization defect on an internet-reachable S2S mutation surface, exploitable by any holder of a fleet credential that clears the middleware — but **bounded to a business scope**, not unbounded cross-tenant write |
| **YES** | the gate **no longer bounds** the finding → **F-001 re-escalates toward Critical** (`CRITIQUE-cc3…:207-212`) |

**Why no seat resolved it:** it is **credential-adjacent (CR-5)** and
**cross-repo**. CR-5 forbids every non-security seat from handling credential
material, and CC-3 correctly did **not** mint a token to find out
(`CRITIQUE-cc3…:196-197`). The critic recorded it as *"the single
operator-actionable question that resolves the High/Critical fork"* and *"the
load-bearing UNKNOWN"* (`:211-212, :256-259`).

## C.3 — What resolves it, and who can

**What resolves it:** inspection of the `autom8y-auth` **SA config and/or the
issuance path** — whether `ace`/`iris` carry the exempt-SA grant
(`bypass_scope_enforcement=True`), which is **not the default**
(`CRITIQUE-cc3…:132-133, :208-210`). This is a **static config/code read**, not a
token mint.

**Who can — two routes, both already available:**

| route | basis | note |
|---|---|---|
| **Security rite, in-session** | UV-P-C-1's METHOD names it explicitly: *"credential-distribution audit across autom8y-auth issuance + agent-seat runtime env review (**security rite, SEC-002**)"* (`chain-of-custody-closure.md:593`). And the RE-2 design names the same owner for exactly this act: *"**Escalation — severity re-grade**: re-grading SEC-001 High→Critical on SEC-002's return — **security rite**"* (`DESIGN-re2…:§6`) | **The security borrow is already co-seated** — Q-2 RATIFIED WS-B locus **in-session** (`inv-20260813-41bc318aeb4c`, `RULING…:29-33`). No new seating act is needed |
| **Operator directly** | the operator holds the authority CR-5 reserves | fastest if the answer is already known to the operator |

**A cost note, offered as framing not as a finding:** the SA registry
`services/auth/service-accounts.yaml` **has already been read own-hands** by the
RE-2 design critic at `origin/main` (it derived `query:read` / `read:pii` from it,
`CRITIQUE-re2-design…:161-168`). So **if** the exempt-SA grant is
registry-declared, the read surface is demonstrably reachable and the determinant
is cheap. **If** it is set at issuance time instead, it needs the issuance-path
trace that SEC-002 owns. The critic wrote the locus as *"SA config **/**
issuance path"* — i.e. either — so **which of the two it is has not been
established here**, and this gate does not establish it.

## C.4 — Adjacent widening the operator should see at the same time

Two findings that **enlarge the population** the determinant applies to — neither
resolves it, both change its scope:

- **A second, uncounted identity population.** The `iris` SA in
  `service-accounts.yaml` carries **no** asana scope, but the OAuth-client
  terraform (`module oauth_clients_hermes`) grants the **same logical identity**
  `asana:read`. The design's blast-radius analysis examined **only** the
  SA-registry path — **OAuth-client identities are a second population also
  carrying asana scope**, widening the reachable surface beyond the design's 18
  (`CRITIQUE-re2-design…:170-178`). **`iris` is therefore precisely the seat where
  the two substrates disagree** — which makes it the more interesting half of the
  `ace`/`iris` question, not the less.
- **A silent species reclassification.** The SDK selects claims species by
  structural shape, and the SERVICE species is an **unguarded catch-all `else`**
  with no `token_type` allowlist — so an `agent_access` token is **not rejected,
  it is silently reclassified as `ServiceClaims`** (`CRITIQUE-re2-design…:183-206`,
  SVR at `client.py:L476-489`). The `require_access_token_type` assertion exists
  **only** in the USER branch.

## C.5 — Disposition

> **This gate assigns no severity beyond the verified High.** F-001 stands as a
> High CWE-862 defect. The re-escalation trigger is named, not fired. **Nothing
> here rules the RE-2 remediation** — the design's `(e) now, (f) next`
> recommendation (`DESIGN-re2…:510-524`) remains an unratified recommendation, and
> the execution locus / landing decision stays operator-reserved (F-3's
> remediation half, `DESIGN-re2…:§6` Governance row).

---

# §D — What this gate did NOT do

Recorded explicitly so no later seat reads a resolution into this artifact.

| item | status |
|---|---|
| **F-1** (RE-1 ownership + scope) | **NOT RULED — halting.** Presented priced. CC-5 stays SHUT |
| **F-4** (fence lift) | **NOT RULED.** Nothing merges; PR-UP-MERGE-HELD stands |
| **F-7** (baseline) | **NOT RULED** — default confirmed *as evidence-backed*; confirming is the operator's act |
| **F-8** (locus) | **NOT RULED** — narrowing surfaced; the choice between (a) and (c) is the operator's |
| **F-2** (rotation) | **NOT TOUCHED** — operator-only, runbook ready, disabled |
| **RE-2 remediation** | **NOT RULED** — no option selected; no severity assigned beyond verified High |
| **GATE-FORK** | **NOT RULED** — coupling stated (DF-5) and nothing more |
| **CC-7 opening** | **NOT DECIDED** — three postures framed; the operator chooses |

## §E — Verification scope

Read-only throughout. All eight grounding artifacts read in full or at the cited
ranges; every claim carries a `file:line` anchor to a Phase-1 artifact rather than
a re-derivation by this seat. **No** independent re-derivation of any Phase-1
negative was attempted (they stand on their own rite-disjoint receipts, and
re-deriving them is not this seat's charge). **No** AWS call, **no** Asana call,
**no** credential material read (CR-5 — the exempt-SA question is **framed, not
probed**), **no** cross-repo probe, **no** git verb (main thread owns git; this
seat authored a file only, via the Bash scribe channel — this agent holds no
Write/Edit tool). CR-1/CR-2 untouched. This artifact rests **AUTHORED-UNMERGED**
(F-A). Self-assessment ceiling **MODERATE** (F-C — single seat, self-referential;
the substance of every negative rests on the rite-disjoint critics cited, not on
this seat).
