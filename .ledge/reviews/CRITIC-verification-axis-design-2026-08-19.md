---
type: review
status: accepted
title: "CRITIC — certification of the SPR-V0 design lock (verification-axis realization)"
initiative: asr-verification-axis-landing
sprint: SPR-VC
rite: dre
agent: change-warden
dispatch_cwd: /Users/tomtenuta/Code/a8/a8/repos/autom8y
created: 2026-08-19
verdict: CERTIFIED-WITH-FLAGS
evidence_grade: MODERATE
grade_ceiling_reason: >-
  ADVISORY §C.5 binding on this initiative: STRONG is unavailable at all.
  This seat is rite-disjoint from the producing lineage (dre ≠ 10x-dev) but
  shares a session root and consumes a prior artifact of its own authorship
  (the 08-18 CRITIC) — the repeat-critic residual is disclosed at §0.3 and
  is NOT curable by further work from this seat.
pins:
  autom8y_origin_main: 08e5080a          # RE-PINNED; both artifacts pinned 3a066a5a
  autom8y_asana_origin_main: e3aab8d4    # unchanged
  probed_at_utc: "2026-08-19T15:19Z – 15:34Z"
targets:
  - autom8y-asana/.ledge/specs/TDD-verification-axis-realization-2026-08-19.md
  - autom8y-asana/.ledge/specs/SPEC-verification-axis-acceptance-2026-08-19.md
production_change: NONE
---

# CRITIC — SPR-V0 Design Lock Certification

> **Verdict: CERTIFIED-WITH-FLAGS.** The design's load-bearing rulings survive
> independent re-derivation. Eleven items require a ruled resolution before build
> dispatch; two of them (X-5, X-7) defeat MUST-grade acceptance predicates and are
> BINDING. The schedule is refused as unsound.

---

## §0 Disjointness Attestation (GATE-2)

### §0.1 The producing lineage this verdict is disjoint from

| | |
|---|---|
| **Producing lineage** | `10x-dev` rite — `architect` (TDD) + `requirements-analyst` (SPEC), both dispatched into `autom8y-asana` at SPR-V0 |
| **This seat** | `dre` rite, `change-warden`, dispatched from the monorepo root `/Users/tomtenuta/Code/a8/a8/repos/autom8y` with read-scope into `autom8y-asana` |
| **Rite-disjointness** | **HOLDS.** `dre` ∉ the `10x-dev` agent roster. This is not a role-switch: it is a different rite, a different cwd, a different dispatch. |
| **critic-never-author** | **HOLDS.** This seat authored zero bytes of either artifact and will author zero bytes of the fix. The only file written is this one. |
| **Dispatcher-critic degeneracy** | Not present. This seat was not dispatched *by* either authoring agent. |

Per `critic-substitution-rule` §5 pre-gate check: A(auditor)=dre/change-warden,
B(target)=10x-dev SPR-V0 artifacts, C(critic)=dre/change-warden. A≠B holds;
A=C is the intended single-critic configuration for this gate (the shape's SPR-VC
seats one disjoint critic), not a MARG INV-1 violation.

### §0.2 What was NOT inherited

Every anchor cited below was re-read by this seat at `origin/main` with its own
hands. The two artifacts' receipts were treated as **context, never evidence**.
The live manifest probe at §1.4 is this seat's own fetch at its own instant — it
is deliberately a *different* warm cycle from the TDD's, so it functions as an
independent replication rather than a re-reading of the same number.

### §0.3 Repeat-critic residual — DISCLOSED, not cured

**This seat certified this front's DIAG on 2026-08-18**
(`.ledge/reviews/CRITIC-wsa-watermark-cure-2026-08-18.md`). **Both artifacts under
review consume that CRITIC as binding input** — the TDD at §0.2 (C-1, C-3, C-7,
C-8, C-9), the SPEC at §53 (C-1..C-9, "C-8 in particular").

The residual is concrete and structural:

- **C-8** (the four-clause test) is *this seat's own finding*, and it is now the
  frame against which this seat is grading. §10 of the TDD and §3 of the SPEC are
  both organized around it. Grading an artifact for conformance to one's own prior
  ruling is a self-confirmation channel, not an independent test.
- **C-3** (pool-level only) constrains what evidence either seat was permitted to
  produce — and therefore constrains what this seat can now demand.
- **C-9** (`NEW LAUNCH REVIEW`, 84-day-stale content watermark) is re-adjudicated
  at §1.3 below against the verification axis rather than inherited.

**Mitigation applied:** every ruling in §1–§4 is re-derived from code, from the
frozen CONTRACT, or from live production data — **not** from the 08-18 CRITIC.
Where a finding coincides with C-8, it is marked as such so a reader can discount it.

**Mitigation NOT available:** this residual cannot be closed by more work from this
seat. It is a standing argument that **SPR-Z1 must be dispatched to a critic
disjoint from BOTH `10x-dev` AND this `dre` seat.** Recorded as ESC-1.

### §0.4 Substrate-of-record scars honored

- **origin/main only.** The `autom8y` working tree is on
  `fix/wss-wildcard-scope-bypass-closure` @ `7ddbd46c`; `origin/main` is
  `08e5080a`. The `autom8y-asana` working tree is `8e1b3964`, **two commits behind**
  its own `origin/main` `e3aab8d4`. **The stale-tree scar is live in both checkouts
  of this session root.** Zero claims below were read from a working tree.
- **Both artifacts' pins are already stale.** Both pinned `autom8y` at `3a066a5a`;
  main is `08e5080a`. See §4.2 — conclusions survive, discipline does not.

---

## §1 QUESTION 1 — THE GRAIN FIGHT

### §1.1 Ruling: **the TDD's refusal of `billable_sections()` is CORRECT** — and it is correct on *two* frozen clauses, not one

The TDD grounds its refusal in §1.4 CO-SOURCING. That is sufficient, but it
under-states its own case. Read verbatim at
`.ledge/decisions/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md:317-319`:

> **VERIFICATION GRAIN (binding).** `verified_at` is the `min` over the
> **complete classification-scoped section-name set** for the request — every
> section the producer's classifier assigns to the **requested classification(s)**

**The frozen GRAIN clause itself already says "for the request" and "the requested
classification(s)."** It does not say "billable." A producer hardcoding
`billable_sections()` on a `classification="active"` request folds over the
requested set **plus five sections nobody asked for** — violating the GRAIN clause
directly, and violating §1.4 CO-SOURCING (`:505-508`) a second way because those
five sections' bytes are not in that response.

The DIAG (§5 rank-1, `:433`), the shape (SPR-V0 exit criterion 3, `:153`) and the
SPEC (R-V1-3, `:250`) all prescribe `billable_sections()`. **All three are wrong
against the frozen text, and the TDD is right.** It is right-answer/wrong-mechanism:
`billable_sections()` returns the correct *number* for this caller only because
ASR's two calls happen to union to exactly billable — verified by direct read of
`activity.py`, where `billable_sections()` is literally
`sections_for(ACTIVE, ACTIVATING)`.

Re-derived anchors, my own hands @ `autom8y-asana` `origin/main` `e3aab8d4`:

```
query/engine.py:124   classification_sections = self._resolve_classification(request.classification, entity_type)
query/engine.py:438-490  _resolve_classification -> frozenset[str] | None, lower-cased (:449), via classifier.sections_for(activity) (:480)
models/business/activity.py  billable_sections() -> self.sections_for(AccountActivity.ACTIVE, AccountActivity.ACTIVATING)
metrics/freshness.py:785     active_names = classifier.active_sections()          [G-1 CONFIRMED]
metrics/freshness.py:809     candidate = info.written_at                          [G-2 CONFIRMED]
metrics/freshness.py:102-110 unavailable() -> max_age_seconds=0, available=False  [G-3 CONFIRMED]
```

### §1.2 Does request-resolved grain re-open a hole? **NO** — and I tested the direction neither seat tested

The dispatch's hazard: *a pool the requests never cover going permanently
unverified — the C-9 / NEW LAUNCH REVIEW class.*

**The TDD's §1.2 receipt folds manifest → classifier.** That direction proves
"every manifest section in scope carries a stamp." It **cannot** detect the
failure that actually matters: **a classifier-assigned section ABSENT from the
manifest.** Under the TDD's own §5.3 emission rule, an absent in-scope section is
`missing` → `verified_at: null` → AXIS-NULL → **REFUSE on every tick**. If even one
of the 27 billable names were missing from the manifest, **the cure would be dead
on arrival — a permanent 7201.0 sentinel** — and nothing in either artifact would
have caught it.

**I ran the reverse fold.** Own hands, live production S3, `2026-08-19T15:33:29Z`:

| Grain | Classifier names | Present in manifest | **ABSENT from manifest** | Present w/o stamp | `min(last_verified_at)` | age |
|---|---|---|---|---|---|---|
| ACTIVE (request-resolved) | 22 | 22 | **0** | 0 | 2026-08-19T15:24:34.853393Z | 561.8 s |
| ACTIVATING (request-resolved) | 5 | 5 | **0** | 0 | 2026-08-19T15:24:34.853393Z | 561.8 s |
| BILLABLE (union) | 27 | 27 | **0** | 0 | 2026-08-19T15:24:34.853393Z | 561.8 s |
| ALL-34 (manifest) | 34 | 34 | — | 0 | 2026-08-19T15:24:34.853393Z | 561.8 s |

`schema_version=1.6.0`, `total_sections=34`, `completed_sections=34`,
**null-name entries = 0**, distinct names = 34.

**Sections in the manifest but in NO requested classification (7):**
`account error`, `awaiting rep update`, `complete`, `inactive`,
`performance concerns`, `plays`, `sales process`.

Cross-checked against `activity.py`: all seven are `inactive` or `ignored`.
**None is billable.** The request-resolved grain strands no billable pool.

**The hole does not open, for three independently checkable reasons:**

1. **Coverage is identical.** `billable_sections()` ≡ `sections_for(ACTIVE, ACTIVATING)`
   ≡ the union of ASR's two request-resolved sets. Same 27 names, by construction.
   The TDD's refusal changes the *mechanism*, not the *denominator*.
2. **The reverse-direction check passes live.** 0/27 absent, 0/27 unstamped.
3. **The 7 excluded sections are excluded under BOTH grains** and are excluded
   from the served bytes too — which is what CO-SOURCING requires.

### §1.3 C-9 re-adjudicated against the verification axis — **it does not transfer**

C-9 (this seat's own 08-18 finding) was: `NEW LAUNCH REVIEW` carries rows=3 with a
**content** watermark 84 days stale, masked only because the pool combination is
`max()`.

Re-derived against the *verification* axis:

- `NEW LAUNCH REVIEW` is in the classifier's `activating` group — **in scope under
  BOTH grains.** Not stranded.
- Its `last_verified_at` is fresh (my probe: all 27 billable sections stamp at the
  same instant). C-9's staleness is a **content-mutation** property; verification
  advances on probe, not on mutation. **C-9 has no purchase on this axis.**
- **The `max()` direction inverts favourably.** On the content axis, `max(watermark)`
  within a pool selects the *freshest* and masks the stale member — that is the C-9
  defect. On the verification axis, ASR's `max(ages)` selects the *oldest* verified
  instant — **conservative**. The same operator that hid C-9 protects here.

**A genuine residual hole exists, and it is orthogonal to the grain fight.** The
classifier is a **static hardcode** (`activity.py`, `OFFER_CLASSIFIER` /
`from_groups`, 36 literal names). A section that exists in Asana but is absent from
that hardcode classifies to `None`, is filtered out of the served rows, and is
outside the denominator — **identically under `billable_sections()` and under the
request-resolved set.** It is a property of the hardcode, not of the grain ruling.
**Carded as FLAG-6**, routed to SPR-R1 alongside R-2/C-9 as a manifest-integrity item.

### §1.4 What `max(ages)` DOES and does NOT reconstitute

**DOES reconstitute:**

- **The billable-union minimum.** `max(age_A, age_G) = now − min(v_A, v_G)`
  = `now − min(last_verified_at | ACTIVE ∪ ACTIVATING)`, with co-sourcing intact
  on each producer leg and the union assembled at the consumer, which is where
  ASR actually gates (it gates on the concatenation of both response bodies).
- **Fail-safe behaviour across manifest generations.** The two legs are two
  separate HTTP requests, each with its own manifest read, so they may see two
  different manifest generations. `max` **always selects the staler leg** —
  a cross-generation read is conservative in the safe direction. Neither artifact
  names this property; it holds, and it is worth having on the record.
- **Refusal propagation** — via §7.2's REFUSE-before-DORMANT ordering, not via
  `max` itself. `max` is never applied to a null.

**Does NOT reconstitute:**

- **(a) Exact identity.** The TDD §4.2 writes "`[identical, by construction]`".
  It is identical **only if `now_A = now_G`**. ASR issues the two requests
  sequentially (`fetcher.py`, `active_result` then `activating_result`), each
  producer stamping its own `now`. The true relation is
  `max(now_A − v_A, now_G − v_G)`, which equals `now − min(v_A,v_G)` **up to the
  inter-request skew**. Immaterial against a 3600 s bar; **material to any test
  asserting exact equality**, which will flake. → **FLAG-1**, resolution at X-1c.
- **(b) Single-snapshot semantics.** The combined number describes no single
  manifest generation. Safe (per above) but it is an approximation, not a fold.
- **(c) Partial coverage.** `max` cannot express "one pool derivable, one not."
  That is correctly handled by the disposition switch, not by the arithmetic —
  and it means **the disposition switch, not `max`, is the load-bearing safety
  mechanism.** A builder who implements `max` and forgets the ordering rule ships
  a cure that swallows refusals. → build obligation, X-1d.
- **(d) Same-response co-location.** The combined axis is derived across **two
  producer traces**. This does not break the frame's conjunct-3 (which concerns
  ASR's *own* emitted trace), but it does mean the TDD's OPT-6 refusal ground
  — *"a metric stream is not derivable from the response it gated"* — applies with
  less force than §3.2 claims, since the ruled design already crosses two
  responses. **The OPT-6 refusal still stands** on the metric-pipeline-lag and
  §1.4-inversion grounds. Calibration note only.

### §1.5 The check that CANNOT be run in production, re-confirmed independently

My probe returned **`distinct stamp instants across all 34 sections = 1`** —
at `15:24:34.853393Z`. The TDD's probe returned the same property at
`14:46:32.232624Z`, **a different warm cycle ~38 minutes earlier**.

**Two independent warm cycles, both single-instant.** This is not a coincidence of
one read: `progressive.py:494` takes one `now` for the whole pass and applies it at
`:573`, so it is a **structural property**. Consequences, both binding:

1. **TRAP-3 is confirmed and strengthened.** `billable`, `active`, `activating`
   and `all-34` all yield the identical number in production, today and on the
   next cycle. **A wrong grain is numerically invisible and will stay invisible
   until a partial warm failure.**
2. **SPEC R-V1-3's method is void.** A live pool-level assertion **cannot
   discriminate the grain** — not "is hard to", *cannot*. The only discriminating
   check is the divergent-stamp fixture (TDD §5.6 item 6). → ruled at X-1b.

---

## §2 QUESTION 2 — FORK-1 / OPT-7 SOUNDNESS

### §2.1 Anchors re-verified (own hands, `autom8y-asana` `origin/main` `e3aab8d4`)

| Claim | Verified |
|---|---|
| `execute_rows` step 12.5 reads the manifest unconditionally | **YES** — `engine.py:248-256`, `honest_contract_complete = await self._derive_honest_contract_complete(...)` |
| The read is at `:588` inside that method | **YES** — `manifest = await section_persistence.get_manifest_async(...)`; result used for one boolean `is_honest_complete(manifest)` and discarded |
| `load_json` is an uncached S3 GET | **YES** — `storage.py`, `load_json` → `return await self._get_object(key)` |
| `EntityQueryService` is per-request | **YES** — `query.py:468`, inside `async def query_rows` (`:334`, `@router.post` `:321`) |
| **No module-level singleton exists anywhere** | **YES** — exhaustive `git grep` over `src/**/*.py` @ `origin/main`: 4 construction sites (`query.py:468`, `query.py:609`, `fleet_query.py:162`, `onboarding_walkthrough.py:79`), **all per-invocation** |
| No early return yields a response before 12.5 | **YES** — the only `raise`/`return` in `execute_rows` `:112-255` is `UnknownFieldError`, which yields no response |
| The manifest read is **not** behind the dataframe cache | **YES** — step 4 loads the df; step 12.5 reads the manifest afterward, on **every** successful rows response including a warm-cache hit. *This is the property that makes OPT-7 work and neither artifact states it explicitly.* |
| `execute_aggregate` does not read the manifest | **YES** — `engine.py:305+` calls only `_get_freshness_meta`, never `_derive_honest_contract_complete` |
| `RowsMeta` / `AggregateMeta` both `extra="forbid"` | **YES** — `query/models.py:390` and `:228`. TRAP-4 is real. |

### §2.2 Both request shapes: **no divergence**

ASR issues `query_rows_async("offer", classification="active"|"activating", limit=1000)`
twice (`fetcher.py`). **Both are `POST /{entity_type}/rows` → `query.py:468` →
`execute_rows`.** Identical code path; only the `classification` value differs,
which changes only `classification_sections`. OPT-7 holds identically under both.
The aggregate path is not in ASR's path and correctly declares AXIS-ABSENT.

### §2.3 **HOLE FOUND — "zero added S3 GETs" is TRUE on the happy path and FALSE on all three sad paths**

`get_manifest_async` (`section_persistence.py:433-478`) populates the memo on
**exactly one** line, inside the success branch:

```python
        if raw_bytes is None:
            return None                      # <- NO memo write
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
            manifest = SectionManifest.model_validate(data)
            self._manifest_cache[cache_key] = manifest       # <- the ONLY memo write
            return manifest
        except Exception as e:
            logger.error("manifest_parse_failed", ...)
            return None                      # <- NO memo write
```

**Negative results are never cached.** Three paths leave `_manifest_cache` empty:

1. `raw_bytes is None` — the manifest object is absent from S3 (both the v2 key
   **and** the SEAM-1 legacy fallback key miss);
2. parse failure → `manifest_parse_failed` → `return None`;
3. `load_json` raises → propagates to `_derive_honest_contract_complete`'s broad
   catch → `honest_contract_derivation_failed` → `return False`.

On every one of these, `_derive_verification_axis`'s `get_manifest_async` call
**repeats the entire read sequence** — and because of the SEAM-1 dual-read
fallback, that sequence is **up to two `load_json` calls**, not one. So a
manifest-absent request goes from **2 GETs today to 4 GETs** under the design.

**This falsifies an explicit design claim.** TDD §5.5, verbatim:

> If the honest-contract read failed, the verification read fails the same way and
> emits AXIS-NULL. Consistent, and **no second network attempt**.

There **is** a second network attempt, on every failure path.

**Severity: FLAG, not BLOCK.** It is bounded (one extra round of ≤2 GETs per
request), it fires only in states where the system is already degraded, and the
disposition stays fail-safe (AXIS-NULL → REFUSE). But it is a latency amplifier in
exactly the condition where amplification hurts, and it is a *stated* property the
build would otherwise inherit as proven.

**Ruled cure (X-2a, BINDING).** `_derive_verification_axis` **must not re-call**
`get_manifest_async`. `_derive_honest_contract_complete` fetches the manifest once
and the object (or a small result tuple) is threaded to both derivations **within
the single request**. This is *not* a hoisted handle and does **not** create
TRAP-1 or TRAP-2 — the object's lifetime is still exactly one request. It is
strictly better than the memo-reliance design: it removes the negative-caching
dependency entirely and makes "zero added S3 GETs" true unconditionally rather
than conditionally.

**Rejected alternative:** negative-caching inside `section_persistence`. It changes
shared behaviour (a manifest appearing mid-request would become invisible) for a
larger blast radius. Do not take this arm.

### §2.4 Is the 0 s-staleness claim honest? **YES, correctly scoped**

The claim is about the **read path**, and on the read path it is exact: the
manifest is fetched fresh from S3 within the request, is not behind the dataframe
cache, and is read on every successful rows response. The axis's *value* is set by
the warm cadence, and the TDD says so.

Two calibrations, neither a defect:

- The TDD calls the cadence "hourly." I observed stamps at `14:46:32Z` (TDD) and
  `15:24:34Z` (mine) — **~38 minutes apart**. The cadence is sub-hourly at present.
  Ages: 1132.4 s → 561.8 s, both far under the 3600 s bar. The GREEN arm is not
  marginal.
- The 0 s figure is *added* horizon, not total. Stated correctly in §3.3 item 3.

### §2.5 TRAP-1's premise holds today, and the guard is correctly demanded

No singleton exists (§2.1). `_manifest_cache` has no TTL and no read-path
invalidation — I confirmed the only eviction is inside `delete_manifest_async`.
The TDD's demanded test (assert a fresh `SectionPersistence` per `query_rows`) is
the right guard and must survive the X-2a refactor: **threading the manifest does
not remove the need for the lifetime assertion**, because a hoisted service would
still break the 0 s horizon.

---

## §3 QUESTION 3 — FORK-3 / PINS

### §3.1 The three pins: **CONFIRMED verbatim, my own hands** @ `autom8y` `origin/main` `08e5080a`

```
services/account-status-recon/pyproject.toml:35    "autom8y-core>=4.6.0,<5.0.0",
services/account-status-recon/pyproject.toml:79    "autom8y-core[testing]>=4.6.0,<5.0.0",
pyproject.toml:21                                   "autom8y-core>=3.2.0",
pyproject.toml:71                                   autom8y-core = { workspace = true }
```

`:26` **is comment prose** — it falls inside the R-6 HONEST QUIET TOLERANCE
rationale block (`:24-34`), which reads in part *"The offers content axis needs
4.14.0 … but is deliberately NOT floored here."* **A limb sent to `:26` edits a
comment and reports success.** D-2 / S-CORR-1 / S-CORR-2 / AD-3 all CONFIRMED.
Both seats found this independently; I found it a third time.

SDK baseline confirmed: `sdks/python/autom8y-core/pyproject.toml:7` = `version = "4.15.0"`.

### §3.2 The Dockerfile claim: **conclusion CORRECT, receipt ONE LINK SHORT**

The TDD's §8.1 verdict — the image resolves `autom8y-core` from CodeArtifact and
**the root pin cannot influence the image** — is right. But its SVR receipt
(`§14`, third block) cites **only Dockerfile lines**. That does not close the
chain, because:

> `COPY --link pyproject.toml ./` resolves against the **build context**, not
> against the Dockerfile's own directory.

If the build context were the monorepo root, that same line would copy the **root**
`pyproject.toml` and the entire FORK-3 ruling would invert. **The TDD never cites
the build invocation.** Its receipt asserts a conclusion its marker tokens cannot
support — an AP-1/AP-4 shape (under-specified anchor) inside an otherwise
disciplined register.

**I closed the chain myself:**

```
services.yaml:613   context: services/account-status-recon
services.yaml:614   dockerfile: services/account-status-recon/Dockerfile
.github/workflows/service-deploy-dispatch.yml:246   context: ${{ matrix.context }}
.github/workflows/service-build.yml:231,:250        context: ${{ inputs.context }}
```

@ `autom8y` `origin/main` `08e5080a`. **The build context IS the service
directory.** The conclusion survives independent re-derivation. Dockerfile facts
re-read directly: `COPY --link pyproject.toml ./`; `uv pip compile pyproject.toml`
(×2 branches); `--index-url "$EXTRA_INDEX_URL" --extra-index-url https://pypi.org/simple/`;
`uv pip install --system --no-deps .`; **no `uv sync`, no `uv.lock`, no
parent-directory copy.** → **FLAG-2**: the SVR is re-graded from CONFIRMED-by-receipt
to CONFIRMED-by-independent-re-derivation; the receipt itself must be amended to
carry the `services.yaml:613` link before it is cited downstream.

### §3.3 Is PT-02's clean-env index-resolution gate SUFFICIENT? **NECESSARY, NOT SUFFICIENT**

The TDD §8.3 argument is right as far as it goes: dev/CI resolve the workspace
editable (`pyproject.toml:71`), the image resolves CodeArtifact against `:35`, and
the two never disagree in CI's favour. So a green CI can never witness image
resolution. PT-02's gate — *resolution from the index, workspace excluded* — is the
correct necessary condition, and SPEC AR-05 / R-V2-3 state it well.

**It is not sufficient, for two mechanical reasons neither artifact names:**

1. **The uv cache mount.** All three `RUN` steps in the Dockerfile carry
   `--mount=type=cache,target=/root/.cache/uv`. `uv pip compile` resolves against
   a **cached index snapshot**. A floor moved from `>=4.6.0` to `>=4.16.x` will
   force a new resolution, but a floor moved *within* an already-cached range, or
   a same-version re-publish, can resolve stale. Combined with the asana
   build-cache-skips-new-files scar (TDD §8.5), "resolvable from the index" and
   "present in the image" are two different facts.
2. **`--generate-hashes` + `--require-hashes`.** The image installs a compiled,
   hash-pinned requirement set produced *inside* the build. PT-02 proves the index
   can serve the wheel; it does not prove this build's compile step selected it.

**Ruled additions (X-3, BINDING):**

- **(a)** The V3 build busts the uv resolver cache (`--refresh`, or a cache-key
  bump) so `uv pip compile` re-resolves against a live index.
- **(b)** The gate chain closes **only** at the live post-deploy observation —
  SPEC R-V1-1 (live serve-path field) and R-V3-3 (live tick). PT-02 is recorded
  as *necessary-not-sufficient* in the receipts table, so no one substitutes it
  for the live leg.

With (a) and (b), the false-green the TDD names is genuinely closed. Without them,
PT-02 green + CI green + publish green is still compatible with a dark image —
which is the predecessor's exact scar.

---

## §4 QUESTION 4 — SCHEDULE HONESTY

### §4.1 Ruling: **NOT honest. The tripwire is arithmetically unsound, and the named lever addresses the wrong segment.**

The TDD §12 states: deadline **2026-08-28**; tripwire **PT-04 fires by
2026-08-25T~12:00Z**; walk = design lock → V1∥V2 ~2 d → publish+resolve+V3+deploy
~1 d → **48 h window (irreducible)** → SPR-V4 ~1 d → SPR-Z1 ~1 d.

**Take the TDD's own tripwire and its own durations and add them:**

```
boundary pinned          2026-08-25T12:00Z   (the stated tripwire)
+ 48 h irreducible window 2026-08-27T12:00Z
+ SPR-V4 receipts ~1 d    2026-08-28T12:00Z
+ SPR-Z1 attestation ~1 d 2026-08-29T12:00Z   <-- ~1.5 days PAST the 2026-08-28 deadline
```

**The tail the TDD itself budgets is 4 days (48 h + 1 d + 1 d). Its tripwire leaves
2.5 days.** The plan does not close even when its own tripwire is met on time.
Firing PT-04 at 08-25T12:00Z would certify an already-missed deadline as on-track.

**The honest tripwire is ≈ 2026-08-24T00:00Z**
(→ 48 h → 08-26 → V4 → 08-27 → Z1 → 08-28), and even that carries **zero** slack.

**Two further compressions the walk does not price:**

- **The 48 h window is a floor, not an expectation.** 12 ticks at
  `cron(0 */4 * * ? *)` = 48 h **only if the boundary lands on a tick**. From an
  arbitrary deploy instant you wait to the next tick, then 11 more: **up to 52 h**,
  plus the SPEC's own +300 s dispatch tolerance. Add ~4 h to the tail.
- **SPR-Z1 is not a one-day task as specified.** SPEC §4.8 requires three
  non-substitutable legs each re-derived by the attester with its **own fresh
  construction**, plus a direct read of the `#account-health` channel, plus an
  ECR-digest boundary pin by the attester's own hands. Budgeting 1 day for that
  is the compression the TDD elsewhere forbids.

### §4.2 The lever is aimed at the wrong segment

The TDD's one named lever is *split V3 into V3a (inert, parallel) + V3b (pins,
after PT-02)*, at the price of one additional production act. That removes V3 from
the **front** serialized segment. **The deficit is entirely in the TAIL**
(48 h + V4 + Z1). Parallelising the front buys ~1 day against a ~1.5-day tail
deficit while **adding a production act** into a lane whose realized failure rate
today is non-trivial (§4.3). **Net: it makes the risk worse and the arithmetic no
better.** Do not take this lever as the remedy for the date.

### §4.3 Today's realized friction — measured, not asserted

Own reads at `2026-08-19T15:19–15:34Z`:

| Signal | Measurement |
|---|---|
| `autom8y` `origin/main` commits **today** | **9**, from `13:45:13Z` (`c66c7381`) to `15:04:52Z` (`08e5080a`) — **one every ~9 minutes over 80 minutes** |
| Shape pin vs design pin | `d9b9c92c` (`14:01:45Z`) → `3a066a5a` (`14:52:00Z`); main moved **3 more times** in that 50-minute gap |
| Both artifacts' pins vs current main | Both pinned `3a066a5a`; main is `08e5080a`. **Already stale at PT-01, before build.** |
| `#1643` merge | Required a **conflict-merge with `#1647`** — RECEIPTS ledger records it as *"two independent same-day catches of drift firing #11"* |
| `#1643` prerequisite | A **manual STEP-0 dual-writer fence** on an uncommitted laptop-local tfstate (`terraform.tfstate.pre-fence-backup-20260819T135853Z`), operator-executed |
| PT-06b leg 2 status | **IN FLIGHT** at read time — asana apply dispatched, plan verification before approval |
| SPR-D1 / SPR-D2 | Both **BUILT, NOT REALIZED** |

The dispatch framed this as "two firings in 90 minutes." **The measured rate is
nine main-movements in eighty minutes**, and two of the three sequential production
acts the V-lane requires traverse the same apply lane that is *currently mid-flight*
with an operator gate on it.

**Verdict: plan-shaped hope.** The design is sound; the calendar is not. The honest
act is to **move the date now, at design lock — not at the tripwire.** Moving it at
the tripwire converts a schedule decision into a receipts decision under pressure,
which is the predecessor's failure mode. → **ESC-2**, operator ruling required
**before** build dispatch. This is *not* a design blocker and does not gate X-1..X-11.

**Pin discipline (X-9, BINDING).** Every build leg re-fetches and re-pins at branch
time and records the branch-point SHA in its PR body. A pin from 15:00Z today is
already stale. Neither artifact's pin may be inherited.

---

## §5 Four-clause sweep — what the test fails to bind that a builder could exploit

Applying the four-clause test (clause (i) quantity-change, (ii) RED-on-halted-warmer,
(iii) GREEN-arm-on-real-data, (iv) construct-validity) **against the artifacts
themselves**, hunting for gaps a builder could satisfy in letter while defeating in
substance. Clause (ii) and (iv) originate in this seat's own C-8 — discount
accordingly (§0.3).

### §5.1 Clause (ii) — **the specified canary tests the WRONG RED**. BINDING.

TDD §10 proposes, as the clause-(ii) construction:

> a **manifest fixture whose in-scope set contains one section with
> `last_verified_at=None` and a fresh `written_at`** … emits
> `verified_at: null, verification_backfill_used: true` → ASR REFUSES → 7201.0.

That is a good two-sided proof — **of the G-2 backfill refusal**. It is *not* the
halted-warmer tooth. A genuinely halted warmer produces **stamps that are present
but OLD**: no probe ran, so `min(last_verified_at)` does not advance, so the age
climbs past 3600 s and the gate FAILs. The proposed fixture never exercises that
path — it exercises *stamp absent*, which routes through AXIS-NULL, an entirely
different mechanism.

**A builder can file the TDD's fixture, satisfy SPEC R-V4-ii's letter, and never
have tested the RED that the whole cure rests on.**

**RULING — TWO canaries, both two-sided, both required:**

| # | Construction | Expected | Two-sided arm | Discharges |
|---|---|---|---|---|
| **CAN-A** | manifest fixture, **all** in-scope sections stamped at `now − 7200 s` | axis derives; `verification_age_seconds ≈ 7200` > 3600 → **FAIL** | same fixture at `now − 600 s` → **PASS** | **clause (ii)** — the halted-warmer tooth |
| **CAN-B** | one in-scope section `last_verified_at=None` + fresh `written_at` | `verified_at: null`, `verification_backfill_used: true` → **REFUSE** (7201.0) | same fixture with the stamp present → **PASS** | the G-2 backfill refusal (SPEC R-V1-5 / FG-V1-3 / AD-6) |

Only **CAN-A** discharges clause (ii). SPEC R-V1-4 and R-V4-ii are amended to
require both, named separately. Both are broken **INPUTS** — no production code is
edited, so G-THEATER is not approached.

### §5.2 Clause (i) — **the "before" trace is unobtainable after the deploy**. BINDING.

Both artifacts bind clause (i) to a disposition-level before/after (TDD §10;
SPEC R-V4-i). **Neither requires the pre-boundary trace to be captured BEFORE the
V3 merge.** Once V3 deploys, the "before" state exists only in retained CloudWatch
logs; any retention lapse, log-group change, or query-window error makes clause (i)
undischargeable — and the pressure at that point is to substitute a reconstruction,
which the k1-ib1 scar (*prove against the REAL emitter*) forbids.

**RULING (X-8, BINDING):** SPR-V3 does not merge until the pre-boundary trace
artifact — 32-hex `trace_id`, UTC timestamp, verbatim disposition fields — is
captured and stored as a file. Cheap, and it is the only moment it is capturable.

### §5.3 Clause (iii) — the GREEN arm is well-bound, but its **discrimination**
depends on X-5

SPEC R-V4-iii is strong: denominator 12, boundary-anchored, `+300 s` tolerance,
`reason="no_staleness_metadata"` passes excluded (AD-5). Clause (iii)'s
*achievability* is independently established — the TDD measured 1132.4 s and I
measured **561.8 s on a separate cycle**, both against a 3600 s bar.

**But its discrimination is defeated by X-5.** "Every offers evaluation PASSes **on
`verification_age`**" is not separable from "PASSed on the DORMANT build clock"
unless a positive verification event exists to join on. See §5.5.

### §5.4 Clause (iv) — correctly demanded, same X-5 dependency

SPEC FG-V4-2 is exactly right that an *argued* clause (iv) is the reductio. The
observed state exists — the TDD's §1.2 read and my §1.4 read are both instances of
*quiet business + healthy warmer + GREEN quantity*. Naming it **by `trace_id`**
requires the positive event of X-5.

### §5.5 **X-5 — OQ-3 IS UNANSWERED, AND IT BREAKS THE SPEC'S CENTRAL DISCRIMINATOR.** BINDING.

The SPEC flags OQ-3 as *"**the one open dependency** between the design lock and
this spec"*: what is the literal verification-disposition **event name**? The TDD
answers OQ-1 (§7.4), OQ-2 (§5.3) and OQ-4 (§16.3). **It never answers OQ-3.**

Worse — §7.1's design mirrors the existing switch, and I read that switch at
`origin/main`:

```
readiness.py   GATE arm    -> offer_staleness = decision.content_age_seconds
                              (logs ONLY offer_freshness_axis_clamped, and only when clamped)
               REFUSE arm  -> log.error("offer_freshness_axis_refused", ...)
               DORMANT arm -> log.info("offer_freshness_axis_dormant", ...)
```

**The healthy GATE arm emits NOTHING.** The TDD's §7.1 reproduces that shape
exactly: `offer_verification_axis_refused` (REFUSE), `offer_verification_axis_dormant`
(DORMANT), `offer_verification_axis_clamped` (skew) — **and no positive event on
GATE.**

Consequence, mechanical:

| SPEC predicate | Requires | Under the TDD as written |
|---|---|---|
| **AR-07 (MUST)** | verification event **PRESENT** and `offers_content_axis_unavailable` **ABSENT** | PRESENT conjunct **unsatisfiable** |
| R-V3-3 | "verification disposition event is **PRESENT** with a numeric value" | unsatisfiable |
| R-B2-2 | "verification disposition event **PRESENT** on that trace" | unsatisfiable |
| FG-V3-1 discriminating check | "**the presence of the positive event is the discriminator**" | no discriminator |
| R-V4-iii / R-V4-iv | join a GREEN tick to a `trace_id` | no join key |

Every one collapses to an **absence-only** predicate — which the SPEC's **own
LAW R-3** declares *vacuously true*. **The born-mute failure mode is reproduced
inside the cure itself**, and it is invisible precisely because the healthy path is
the silent one.

**RULING (BINDING, V3):** emit a positive event on the GATE arm. Name fixed here so
it is not re-litigated across two repos:

```
log.info(
    "offer_verification_axis_gated",
    verification_age_seconds=<float>,
    verified_at=<iso8601>,
    verification_backfill_used=<bool>,
    constituents=<per-pool identity>,
)
```

One line, inside a leg already being built. Without it, one MUST-grade requirement
and the discriminator for **two of the four clauses** are unsatisfiable.

### §5.6 **X-6 — the `axes_present` literal tokens are never fixed.** BINDING.

TDD §5.2/§5.3 say *"the three verification names"* and never write them. The
consumer side is unforgiving — verified at `origin/main`:

- `QueryMeta.axes_present: list[str] = Field(default_factory=list)` exists, with
  `_normalize_axes_present` (`mode="before"`) that returns `[]` **whole** for any
  non-list value **or any list containing a non-string element** — deliberately
  *"normalized whole rather than filtered"*.
- `declares_axis(axis: str)` tests membership **by wire field name** (its own
  docstring example is `"content_watermark"`).

So if V1 emits `["verification"]` and V3 asks `declares_axis("verification_age_seconds")`,
the answer is `False` → **DORMANT** → the cure is **silently inert and
indistinguishable from AXIS-ABSENT**. No alarm, no refusal, a passing gate on the
build clock. CONTRACT §1.2 clause 6 makes spelling load-bearing for exactly this.

**RULING:** the three literals are exactly

```
["verified_at", "verification_age_seconds", "verification_backfill_used"]
```

pinned here; asserted by a test in **V1** (emitter) **and** in **V2** (parser); never
a single collapsed axis token. **And the assignment is a UNION, not a replacement** —
TDD §5.3 writes `axes_present = [the three verification names]`; the moment a
content-axis CAP-SIG is added, an assignment silently un-declares it. Write it as a
union from the start.

**Verified non-hazard:** `axes_present` currently has **zero occurrences anywhere in
`autom8y-asana/src/**/*.py`** at `origin/main` (exhaustive `git grep`). It is
genuinely net-new on the producer side, so V1 cannot clobber an existing roster.

---

## §6 The builders' contradiction-resolution list

The two artifacts were authored concurrently and blind. Eleven divergences, **each
with exactly one ruled resolution.** Where the TDD and SPEC conflict, the ruling
names the winner and the reason; a builder follows this table, not either artifact
alone.

| # | Contradiction | **RULED RESOLUTION** | Binding on |
|---|---|---|---|
| **X-1a** | SPEC R-V1-3 requires grain "via `billable_sections()`"; TDD §4 refuses it | **TDD WINS.** Grain = the request's resolved classification set (`engine.py:124`). `billable_sections()` NOT called; `active_sections()` NOT called on the serve path. Grounded in **two** frozen clauses: §1.2 GRAIN ("the requested classification(s)") **and** §1.4 CO-SOURCING. R-V1-3 is amended to the TDD §16.2 text. The DIAG §5 rank-1, shape exit-3 and SPEC R-V1-3 are all **corrected**. | V1 |
| **X-1b** | SPEC R-V1-3 asserts grain by **live pool-level observation** | **METHOD VOID — replaced.** Independently reproduced on two warm cycles: `distinct stamp instants = 1`. A live assertion **cannot** discriminate the grain. The discriminating check is the **divergent-stamp fixture** (TDD §5.6 item 6). Live observation is retained as a presence check only. | V1, V4 |
| **X-1c** | TDD §4.2 asserts ASR's `max(ages)` is "[identical, by construction]" to the billable fold | **AMENDED to "identical up to the inter-request skew."** The identity holds only if `now_A = now_G`; ASR's two calls are sequential. Immaterial vs 3600 s; **no test may assert exact equality.** | V3 |
| **X-1d** | Neither artifact states that the disposition switch, not `max`, carries the safety | **RULED:** `combine_offer_verification` evaluates **REFUSE before DORMANT** (mirroring `readiness.py`'s existing ordering); `max` is applied only when **all** constituents GATE. A test asserts a REFUSE is not swallowed by a sibling's DORMANT. | V3 |
| **X-2a** | TDD §5.5 claims "no second network attempt" on a failed manifest read | **FALSIFIED — design amended.** `get_manifest_async` never memoizes negatives (§2.3). `_derive_verification_axis` **must not re-call** it; thread the once-fetched manifest within the request. Not a hoisted handle; TRAP-1/TRAP-2 unaffected. Do **not** negative-cache in `section_persistence`. | V1 |
| **X-2b** | "Zero added S3 GETs" stated unconditionally | **RE-SCOPED:** true on the happy path; under X-2a it becomes true unconditionally. Until X-2a lands, the honest statement is "zero on the success path; up to 2 additional GETs on manifest-absent/parse-fail/raise." | V1 |
| **X-3** | SPEC §4.2 exit claim + R-V2-1 place the new field on `ResponseFreshness` / `asana_freshness.py`; TDD §6.1 refuses | **TDD WINS.** New module `helpers/asana_verification.py`; `ResponseFreshness` and `derive_response_freshness` **unmodified**. Grounded in three concrete coupling sites, incl. R-5's live 1000-row `T-GUARD` cliff (both ASR queries use `limit=1000`). R-V2-1/R-V2-2 re-anchored to the new module; the NON-ALIASING grep receipt runs over **both** modules and shows **zero cross-imports**. | V2 |
| **X-4** | SPEC R-V1-3's WHERE says "the call site **replacing** the `:785` hardcode" | **TDD WINS — `:785` is PRESERVED.** `compute_verification_age` keeps its ADR-006 CLI behaviour unchanged (§2.3 equivalence obligation: existing metrics tests pass **unmodified**). The new path is `_fold_oldest_verified` + `compute_serve_verification`. A builder who "replaces `:785`" breaks a ruled behaviour. R-V1-3's WHERE re-anchored. | V1 |
| **X-5** | SPEC OQ-3 (the event name) declared *"the one open dependency"*; **TDD does not answer it**, and §7.1 emits nothing on GATE | **BINDING BUILD OBLIGATION.** Emit `offer_verification_axis_gated` at INFO on the GATE arm with `verification_age_seconds`, `verified_at`, `verification_backfill_used`, `constituents`. Without it AR-07 (MUST), R-V3-3, R-B2-2, R-V4-iii and R-V4-iv are all vacuous under LAW R-3. | V3 |
| **X-6** | `axes_present` literal tokens never fixed; SDK `declares_axis` matches wire field names | **PINNED:** `["verified_at","verification_age_seconds","verification_backfill_used"]`, asserted by tests in **both** V1 and V2, written as a **UNION** not an assignment. A token mismatch is silently inert and reads as AXIS-ABSENT. | V1, V2 |
| **X-7** | TDD §10's clause-(ii) canary proves the **backfill refusal**, not the halted-warmer RED | **TWO canaries required** (§5.1): **CAN-A** stale-but-present stamps → age > 3600 → FAIL [discharges clause (ii)]; **CAN-B** absent stamp + fresh `written_at` → AXIS-NULL → REFUSE [discharges R-V1-5 / AD-6]. Both two-sided, both broken **INPUTS**. Only CAN-A discharges clause (ii). | V1, V4 |
| **X-8** | Neither artifact requires capturing the clause-(i) "before" trace **before** the deploy | **BINDING:** SPR-V3 does not merge until the pre-boundary trace (32-hex `trace_id` + UTC + verbatim disposition fields) is captured to a file. Unobtainable afterward. | V3 |
| **X-9** | Both artifacts pin `autom8y` at `3a066a5a`; main is `08e5080a`, moved 9× today | **BINDING:** every leg re-fetches and re-pins at branch time and records the SHA in its PR body. Conclusions survive (all pin-relevant anchors re-verified at `08e5080a`); the discipline does not transfer. | all |
| **X-10** | Both seats' diffs missed `#1644`: `+379` lines `terraform/services/account-status-recon/deadman_escalation.tf` + `production.tfvars`, merged **today** `14:06:56Z` | **RULED:** the SPEC's diff was scoped to `services/account-status-recon/`, which **excludes** `terraform/services/account-status-recon/`. SPEC R-I1-3's before/after baseline must anchor its "before" window **after `#1644`/`#1643` are APPLIED** (merge ≠ apply; PT-06b leg 2 was IN FLIGHT at this read), or the baseline is contaminated. The SPEC's §8.2 UV-P on this ("may not have landed") is **DISCHARGED: it landed.** | I1 |
| **X-11** | Shape names the exit artifact `.ledge/decisions/DESIGN-*.md`; it is at `.ledge/specs/TDD-*.md` | **ACCEPTED.** The TDD path is the SPR-V0 exit artifact of record. No `DESIGN-*.md` exists or will be authored. PT-01, SPR-VC and SPR-Z1 read the TDD path. Cosmetic. | PT-01 |

### §6.1 Divergences that are NOT contradictions (recorded so they are not re-opened)

- **AD-4 / OQ-1** (does R-6 tolerance extend to the verification axis?) — **ANSWERED**
  by TDD §7.4: it does not; the discriminator is `axes_present`. Consistent with
  CONTRACT §1.2. Closed.
- **AD-6 / AR-14** — TDD §16.3 takes arm 1 (`allow_written_at_backfill=False`). The
  `SPR-R1 → PT-04` edge is **not** created. Correct, and load-bearing given §4.
- **AD-7 / OQ-2** (empty join: refuse or degrade?) — **ANSWERED**: AXIS-NULL → REFUSE
  (§5.3). The docstring's "degrade to the mutation axis" is CLI-only. Closed.
- **AR-22 / OPT-6** — both refuse. Consistent (see §1.4(d) for the calibration).

---

## §7 Flags carried forward

| ID | Flag | Disposition |
|---|---|---|
| **FLAG-1** | `max(ages)` identity is skew-approximate | X-1c |
| **FLAG-2** | TDD §14 SVR #3 (Dockerfile) asserts a conclusion its markers cannot support; the build-context link is missing | Amend the receipt to cite `services.yaml:613` before any downstream citation. Conclusion CONFIRMED by this seat's independent re-derivation. |
| **FLAG-3** | TDD §3.1 presents OPT-7 as a gap-option the slate missed | The **DIAG §5 rank-1 already names it**: *"plumbed onto the serve path via the manifest read the engine already performs for `honest_contract_complete`"*. Attribution nit; the option-enumeration work itself is sound and the 7-option slate is genuine. Grade-honesty note only. |
| **FLAG-4** | The name-based join makes a null-name manifest entry silently `missing` → REFUSE | Fail-safe direction, and **0 null names live** (my probe). A re-seed that nulls names would produce total gate refusal. Card to SPR-R1. |
| **FLAG-5** | uv cache mount + `--require-hashes` mean PT-02 is necessary-not-sufficient | X-3(a)/(b) |
| **FLAG-6** | The classifier is a **static hardcode**; a live Asana section absent from it is outside the denominator under **both** grains | Orthogonal to the grain ruling. Route to SPR-R1 with R-2/C-9 as a manifest-integrity item. |
| **FLAG-7** | Warm cadence measured at **~38 min**, not "hourly" as the TDD states | Immaterial to the ruling; correct the prose so no receipt is written against a wrong cadence premise. |

## §8 Escalations

| ID | Escalation |
|---|---|
| **ESC-1** | **SPR-Z1 must be dispatched to a critic disjoint from BOTH `10x-dev` AND this `dre` seat.** This seat authored the 08-18 CRITIC whose C-8 is the four-clause frame both artifacts are built on and this certification grades against (§0.3). That residual is not curable by further work from this seat. |
| **ESC-2** | **Operator ruling required on the date, BEFORE build dispatch.** The 2026-08-28 walk does not close even when its own tripwire is met (§4.1). Move the date, or descope SPR-Z1's re-derivation depth by explicit ruling — never by silent compression at the tripwire. |

---

## §9 Four-clause adjudication against the DESIGNED quantity (shape SPR-VC exit criterion)

| Clause | Adjudication | Receipt that discharges it, and where |
|---|---|---|
| **(i) changes the QUANTITY** | **SATISFIED IN DESIGN.** `offer_staleness` moves from `now − min(max(last_modified \| pool))` to `now − min(last_verified_at \| requested classification set)` — different input, different write path, different tooth. Independently evidenced: on 2026-08-19 the content axis read 52 566.7 s while verification read 1 132.4 s (TDD) and 561.8 s (mine). | SPR-V4 R-V4-i, **conditional on X-8** (capture the "before" trace pre-merge). |
| **(ii) RED on a genuinely-halted warmer** | **SATISFIED IN MECHANISM, NOT IN THE SPECIFIED RECEIPT.** The withhold gates are structural and re-read at `origin/main`: `progressive.py:515-516` (`PROBE_FAILED` → `continue`), `:517-520` (unapplied delta → `continue`), `:561-572` (hash-only-clean → heal, do not stamp), `:573` (stamp past all three). `min` cannot advance without a live probe. **But the specified canary tests the wrong RED (§5.1).** | SPR-V4 R-V4-ii, **rewritten per X-7: CAN-A discharges this clause, CAN-B does not.** |
| **(iii) GREEN arm on REAL data** | **SATISFIED — independently replicated.** Not argued: measured twice, on two different warm cycles, before a line of code exists. TDD @ 15:05Z: 1 132.4 s. **This seat @ 15:33Z: 561.8 s** (`min = 2026-08-19T15:24:34.853393Z`), 0.16× the 3600 s bar, 27/27 billable sections stamped, 0 absent, 0 unstamped. | SPR-V4 R-V4-iii (12-tick window). **Its discrimination is conditional on X-5.** |
| **(iv) construct validity** | **SATISFIED — the state is OBSERVED, not argued.** *Warm loop healthy + business quiet + quantity GREEN* is exactly the live state both probes read: stamps advanced at 14:46:32Z and again at 15:24:34Z while the content axis sat at 52 566.7 s because nobody had edited the quieter pool since 2026-08-12. That is the state the old axis could never produce. | SPR-V4 R-V4-iv, named by `trace_id` — **conditional on X-5** supplying the join key. |

**Two of four clauses have their discrimination gated on X-5.** That is why X-5 is
binding rather than advisory.

---

## §10 VERDICT

# **CERTIFIED-WITH-FLAGS**

**The design lock is certified for build dispatch, subject to the eleven ruled
resolutions in §6 — of which X-2a, X-5, X-6, X-7, X-8 and X-9 are BINDING — and to
the operator ruling ESC-2 on the date.**

**Why not REFUSED.** Every load-bearing ruling survives independent re-derivation
by this seat's own hands: the grain ruling is correct and correct on *two* frozen
clauses rather than the one it cites; FORK-1/OPT-7 rests on a real, verified,
already-paid manifest read that is not behind the dataframe cache; FORK-3's
CodeArtifact conclusion is right (though its receipt was one link short, closed at
§3.2); the three pins are exactly as stated and `:26` is exactly the comment trap
described; R-1 is genuinely reconciled with no fourth derivation; the backfill
refusal is contract-correct; and the monotonicity finding on `mark_section_failed`
is a real defect correctly ruled non-blocking. **The TDD found four divergences from
its own inputs and was right about all four**, including correcting the DIAG, the
shape and its own sibling spec on the grain. Every gap I found is named precisely,
is cheap, and is closable inside legs already scheduled.

**Why not clean CERTIFIED.** Four defects reach substance, not polish:

1. **X-5** — OQ-3, the SPEC's self-declared *"one open dependency"*, is unanswered,
   and the design as written emits **nothing on the healthy path**. One MUST-grade
   requirement (AR-07) and the discriminator for **two of four clauses** are
   unsatisfiable. **The born-mute failure mode is reproduced inside the cure.**
2. **X-7** — the specified clause-(ii) canary tests the backfill refusal, not the
   halted-warmer RED. A builder could satisfy the letter and never test the tooth
   the cure rests on.
3. **X-2a** — an explicit design claim ("no second network attempt") is falsified
   by direct read; negatives are never memoized, so every sad path doubles the
   serve-path manifest reads.
4. **§4** — the schedule is arithmetically unsound. The walk misses 2026-08-28 by
   ~1.5 days **even when its own tripwire is met on time**, and the one named lever
   parallelises the front while the deficit is entirely in the tail.

**The founding premise was re-litigated, not inherited.** The premise — *that the
business-activity proxy is construct-invalid and a probe-anchored verification axis
is the axis of record* — was tested by asking whether the "waste" being removed was
load-bearing safety. It is not: the content axis is **retained** as disclosure and
as the anomaly input (CONTRACT §1.2), `combine_offer_axis` is unmodified,
`readiness.py:334-344` whole-source dormancy is untouched, and the DORMANT arm is
byte-identical to today. **Nothing is removed; a second, orthogonal axis is added
alongside, and the pre-existing behaviour is the fallback.** The premise survives.

**Evidence grade: `[STRUCTURAL | MODERATE]`.** STRONG is unavailable to this
initiative at all (ADVISORY §C.5). This seat is rite-disjoint from `10x-dev` but
carries the disclosed repeat-critic residual of §0.3. **Ambiguity rounded toward
the weaker grade throughout.**

---

## §11 Own-hands receipts

```bash
# substrate of record + drift measurement                       @ 2026-08-19T15:19:31Z
git rev-parse origin/main                     # autom8y-asana -> e3aab8d4 (tree 8e1b3964, BEHIND)
git rev-parse origin/main                     # autom8y       -> 08e5080a (tree 7ddbd46c, BEHIND)
git log origin/main --since=2026-08-19T00:00:00Z --format='%h %cI %s'   # 9 commits, 13:45Z..15:04Z

# GRAIN — the frozen text, read verbatim
sed -n '300,400p' .ledge/decisions/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md
#   :317-319 VERIFICATION GRAIN "... for the request ... the requested classification(s)"
#   :505-508 CO-SOURCING "describes the bytes in that same response"

# GRAIN — the code, at origin/main
git show origin/main:src/autom8_asana/query/engine.py            | sed -n '110,135p;438,495p'
git show origin/main:src/autom8_asana/models/business/activity.py| sed -n '60,230p'
git show origin/main:src/autom8_asana/metrics/freshness.py       | grep -n 'active_sections()|written_at|def compute_verification_age'
#   :735 def / :785 active_sections()  [G-1] / :809 written_at  [G-2] / :102-110 unavailable()  [G-3]

# OPT-7 — the negative-caching hole
git show origin/main:src/autom8_asana/dataframes/section_persistence.py | sed -n '425,500p'
#   _manifest_cache[cache_key] = manifest  written ONLY in the success branch
git show origin/main:src/autom8_asana/query/engine.py | sed -n '240,305p;544,615p'
git show origin/main:src/autom8_asana/api/routes/query.py | sed -n '315,345p;460,475p'
git grep -n 'EntityQueryService(' origin/main -- 'src/**/*.py'   # 4 sites, all per-invocation
git grep -n 'axes_present'        origin/main -- 'src/**/*.py'   # ZERO hits -> genuinely net-new

# FORK-3 — the link the TDD's receipt was missing
git show origin/main:services.yaml | sed -n '600,625p'   # :613 context: services/account-status-recon
git show origin/main:.github/workflows/service-deploy-dispatch.yml | sed -n '240,251p'
git show origin/main:.github/workflows/service-build.yml | grep -n 'context:'
git show origin/main:services/account-status-recon/Dockerfile | sed -n '50,105p'
git show origin/main:services/account-status-recon/pyproject.toml | grep -n autom8y-core  # :35 :79
git show origin/main:pyproject.toml | grep -n autom8y-core                                 # :21 :71

# X-5 — the GATE arm emits nothing (the finding)
git show origin/main:services/account-status-recon/src/account_status_recon/readiness.py | sed -n '485,560p'

# X-6 — the consumer side of CAP-SIG
git show origin/main:sdks/python/autom8y-core/src/autom8y_core/models/asana_service.py | sed -n '373,445p'

# X-10 — the diff both seats' path-scope excluded
git show --stat --format='' 927571fd   # terraform/services/account-status-recon/deadman_escalation.tf +379

# LIVE PROBE — own fetch, own fold, own instant       @ 2026-08-19T15:33:29Z
aws s3 cp s3://autom8-s3/dataframes/1143843662099250/offer/manifest.json - 
#   schema_version 1.6.0 | 34/34 complete | 0 null names
#   ACTIVE      22/22 present, 0 ABSENT, 0 unstamped
#   ACTIVATING   5/5  present, 0 ABSENT, 0 unstamped
#   BILLABLE    27/27 present, 0 ABSENT, 0 unstamped
#   min(last_verified_at) = 2026-08-19T15:24:34.853393Z -> age 561.8 s  (0.16x the 3600 s bar)
#   distinct stamp instants across all 34 = 1           -> TRAP-3 reproduced on a 2nd warm cycle
#   out-of-scope sections (7): account error, awaiting rep update, complete, inactive,
#                              performance concerns, plays, sales process  -> NONE billable
```

**Nothing above was inherited.** The TDD's and SPEC's receipts were read as context
and re-derived independently; the live probe is this seat's own fetch at its own
instant, deliberately on a different warm cycle so that it replicates rather than
re-reads.
