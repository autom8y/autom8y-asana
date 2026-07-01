---
type: decision
artifact_kind: adr
initiative: gfr
title: "ADR — GFR SEAM1 Ride Options (enumeration; decision deferred to PT-01)"
status: draft
version: v2
created: 2026-06-25
revised: 2026-06-25
author: architect (10x-dev)
rite: 10x-dev
source_hash: f4f924d2684386093ef656ecde5e98613cdffce8
decision: "Option E ADOPTED — PROPOSED, pending rite-disjoint review critic at PT-01"
decision_owner: PT-01 (Pythia-navigation fork + rite-disjoint review critic confirms/overrides)
supersedes: none
relates_to:
  - .ledge/specs/gfr-tdd.md
  - .ledge/decisions/ADR-seam1-entity-identity-key.md
  - .ledge/decisions/ADR-G2RECV-body-parameterized-entity-resolvability.md
external_critic:
  rite: review
  artifact: .ledge/reviews/gfr-seam1-critic-verdict.md
  status: PROPOSED — UNRATIFIED (the author cannot certify their own ride; PT-01 rite-disjoint review critic is the ratifier)
  mandate: "Confirm or override the PROPOSED Option E. LOAD-BEARING CHARGE: is there ANY path that serves a legacy-fallback row WITHOUT the gid-identity re-assertion firing? The legacy project-only partition is multi-tenant; Option E's entire cross-tenant safety rests on the re-assertion firing on EVERY fallback-served row. Enumerate the read-gates (storage.py:1010,1195,1291,1372) and confirm each one that can serve a fallback row routes through the re-assertion. The author cannot certify their own ride from inside their vantage. Option E closes Vector A (routing) only; Vector B is certified separately. NOTE the re-assertion is a ROUTING guard (served row gid == anchored gid); it is NOT about the inbound DISPLAY-collision (TDD §11.6, R-10), which is a separate LOW-severity email-booking-intake concern out of this ride's scope."
vector_b_certification:
  owner: "detection-rite / ProjectTypeRegistry maintainer (tier1.py:38/117, registry.py; ADR-0101, ADR-0109)"
  artifact: .ledge/reviews/gfr-vectorB-discriminator-cert.md
  note: "gid->project_gid->entity_TYPE (NOT gid->tenant); project_gid shared across tenants. Ride claims NO cross-tenant safety on Vector B alone."
---

# ADR — GFR SEAM1 Ride Options

> **STATUS: DRAFT — Option E ADOPTED, marked PROPOSED.** This ADR ENUMERATES the
> full slate of SEAM1 ride strategies with tradeoffs and, per the v2 TDD
> directive, ADOPTS **Option E (dual-read + on-fallback gid-identity
> re-assertion)** as the proposed ride. The adoption is **PROPOSED**, NOT
> ratified: the rite-DISJOINT review critic at PT-01 confirms or overrides it
> per `option-enumeration-discipline` and `critic-substitution-rule`. The author
> cannot certify their own cross-tenant key shape from inside their vantage —
> the critic's job is precisely to surface any collision Option E's author cannot
> see. **Option E closes Vector A (wrong-row within a project) ONLY**; it does
> NOT close Vector B (gid->project_gid->entity_type discriminator), which is a
> separate certification (TDD §11.5).

## v2 changelog

- The v1 ADR enumerated A–D and DEFERRED the whole decision. v2 ADDS **Option E**
  and ADOPTS it (PROPOSED). Option E is the v1 NO-GO fix at the ride layer: plain
  dual-read (Option B) carried a MEDIUM cross-tenant risk because the legacy
  project-only fallback could surface the wrong tenant's row. Option E re-asserts
  the served row's gid against the parent-chain-anchored gid on the fallback
  path, dropping that risk to LOW.
- Adoption is gated: PROPOSED pending the PT-01 rite-disjoint critic.
- Explicit scope note added: Option E closes Vector A only (not Vector B).

## v2 round-2 changelog (post QA re-review GO-WITH-FIXES)

- **Option E remains PROPOSED, UNRATIFIED.** The QA re-review correctly flagged
  that Option E is the author's own ride and cannot be self-certified: its
  cross-tenant safety rests ENTIRELY on the gid re-assertion firing on EVERY
  fallback-served row, and the legacy project-only fallback partition is
  multi-tenant. The PT-01 critic's load-bearing charge (any path serving a
  fallback row WITHOUT the re-assertion firing) is sharpened in the
  `external_critic.mandate` to require enumerating each read-gate
  (`storage.py:1010,1195,1291,1372`).
- **Re-assertion is a ROUTING guard, not a DISPLAY guard.** Round-2 clarifies
  (per TDD §11.6 / R-10) that Option E's gid re-assertion defends tenant ROUTING
  (served-row gid == anchored gid). The inbound `:141` phone-fallback
  DISPLAY-collision is a separate, LOW-severity `email-booking-intake` concern
  OUT of this ride's scope — the critic should not conflate them.
- No change to the option slate or the adoption rationale; the collision is not
  reopened.

## Context

GFR reads field values across the in-flight **entity-partitioned storage
migration** (SEAM1). The migration changes the cache key shape to
`dataframes/{project_gid}/{entity_type}/…` (entity-partitioned), but is NOT yet
complete: legacy (project-only) partitions still exist behind a dual-read
switch.

SVR-confirmed substrate at f4f924d2:

- `dataframes/storage.py:352` — `legacy_fallback_enabled: bool = True`
  (the SEAM1 dual-read switch, "Decision 2B").
- read-gates at `storage.py:1010,1195,1291,1372` — each guards a legacy fallback
  when the entity-partitioned read returns `None`.
- `ADR-seam1-entity-identity-key.md:103-104` — code must **SUPPORT** the
  migration (build-on-miss, dual-read), **NOT EXECUTE** it. The entity-partitioned
  key shape is **MANDATORY**.
- Frame LATITUDE — the ride is a "genuine fork for Pythia-navigation", explicitly
  NOT hardened into a constraint; the adversarial /qa pass pressure-tests
  whatever choice is made.

```yaml
structural_verification_receipt:
  claim: "SEAM1 dual-read is live at HEAD via legacy_fallback_enabled defaulting True, with four read-gates that fall back to legacy when the entity-partitioned read misses"
  verification_method: bash-probe
  verification_anchor:
    source: "grep -n 'legacy_fallback_enabled' src/autom8_asana/dataframes/storage.py"
    command_output_verbatim: "352:        legacy_fallback_enabled: bool = True,\n1010:            if not self._legacy_fallback_enabled:\n1195:            if data is None and self._legacy_fallback_enabled:\n1291:            if data is None and self._legacy_fallback_enabled:\n1372:            if data is None and self._legacy_fallback_enabled:"
    exit_code: 0
    claim: "the dual-read switch and its four read-gates are present at HEAD; the GFR ride must consume this seam, not re-implement partition fallback"
```

**The decision space is genuinely plural** (this is NOT a singular design forced
by constraint): the migration's incompleteness means GFR can legitimately read
the new shape, the legacy shape, or both — and can choose whether to migrate
forward on miss. The cross-tenant risk dimension is what makes the choice
load-bearing: a wrong key shape could read another tenant's partition.

## The Decision (Option E ADOPTED — PROPOSED, confirmed/overridden at PT-01)

**Adopted (proposed): Option E — dual-read + on-fallback gid-identity
re-assertion.** Rationale below (after the full slate). The decision is PROPOSED,
not ratified: PT-01's rite-disjoint review critic confirms or overrides. The
other options remain documented as the genuine slate the critic evaluates Option
E against.

## Options Considered (FULL SLATE)

Each option is a genuinely different read strategy across the SEAM1 seam — not a
single-dimension ranking. Cross-tenant risk, cold-frame cost, and migration
safety are scored low/medium/high.

### Option A — build-on-miss

**How:** Read the entity-partitioned key
(`dataframes/{project_gid}/{entity_type}/…`). On a partition miss, BUILD the
entity-partitioned frame (via the existing warm/build machinery), then read it.
Never read the legacy shape.

- **Pros:** strictly entity-partitioned reads (lowest cross-tenant risk — only
  ever touches the correct `{project_gid}/{entity_type}` partition); migrates the
  store forward as a side effect; no dependence on `legacy_fallback_enabled`
  (clean once the migration completes).
- **Cons:** highest cold-frame cost (a miss triggers a full 0.5–120s build
  inline before the first value); build-on-the-read-path tension with
  ADR-G2RECV's "never builds on the request path" for offer-domain (must NOT
  build offer-domain frames on miss — only the migration-eligible entity frames).
- **cross_tenant_risk:** low
- **coldframe_cost:** high
- **migration_safety:** medium (forward-migrates but couples reads to builds)

### Option B — dual-read

**How:** Read the entity-partitioned key first; on miss, fall back to the legacy
(project-only) partition by CONSUMING `legacy_fallback_enabled` and the existing
read-gates (`storage.py:1195,1291,1372`). Serve whichever has the value.

- **Pros:** lowest cold-frame cost (legacy partition is already warm — no build
  on the read path); highest migration safety (reads succeed throughout the
  migration regardless of which shape a given frame is in); zero new partition
  logic — pure reuse of the live dual-read seam.
- **Cons:** **medium cross-tenant risk** — the legacy fallback reads a
  project-only key, and if entity-type disambiguation is weak at the legacy
  layer, a fallback could surface a row from the wrong entity within the project;
  the cross-tenant guard must be airtight ON the fallback path specifically;
  inherits the legacy shape's lifetime (GFR can't retire `legacy_fallback_enabled`).
- **cross_tenant_risk:** medium
- **coldframe_cost:** low
- **migration_safety:** high

### Option C — hybrid (dual-read serve + async build-on-miss)

**How:** Dual-read for the SERVE (Option B's read path, low latency), AND
asynchronously trigger an entity-partitioned build-on-miss (Option A's
forward-migration) so subsequent reads hit the entity-partitioned shape. The
serve never waits on the build.

- **Pros:** low cold-frame cost on the serve (legacy fallback answers
  immediately) AND forward-migrates the store over time; the async build reuses
  singleflight/coalesce (no new rebuild engine); cross-tenant risk stays low for
  the entity-partitioned reads while the legacy fallback shrinks over time.
- **Cons:** most moving parts (two paths + async coordination); the async build
  must respect ADR-G2RECV cache-only for offer-domain (only migrate
  migration-eligible entities, never build offer-domain on miss); the cross-tenant
  guard still applies to the legacy fallback during the serve.
- **cross_tenant_risk:** low
- **coldframe_cost:** medium
- **migration_safety:** high

### Option D — partition-pinned (strict)

**How:** Resolve ONLY against the entity-partitioned key. A legacy miss is an
unresolved field (trips all-or-nothing). Never read the legacy shape; never build
on miss.

- **Pros:** lowest cross-tenant risk AND lowest cold-frame cost (no build, no
  fallback — a fast strict read); simplest possible ride (one path); composes
  cleanly with the central guard's entity_type key-shape check.
- **Cons:** **lowest migration safety** — during the in-flight migration, frames
  still in the legacy shape return `empty-frame` -> `UnresolvedError`, so GFR
  would fail on legitimately-existing data that simply hasn't migrated yet;
  effectively requires the migration to be COMPLETE before GFR is reliable,
  contradicting "SUPPORT the migration, not execute it".
- **cross_tenant_risk:** low
- **coldframe_cost:** low
- **migration_safety:** low

### Option E — dual-read + on-fallback gid-identity re-assertion (ADOPTED — PROPOSED)

**How:** Read the entity-partitioned key first (Option B's primary read path).
On a partition miss, fall back to the legacy (project-only) partition by
CONSUMING `legacy_fallback_enabled` and the existing read-gates
(`storage.py:1195,1291,1372`) — BUT before serving the legacy-fallback row,
RE-ASSERT its gid against the identity the caller is resolving: the served row's
gid MUST equal the parent-chain-anchored `business_gid` (for an identity field)
or the requested entity gid (for a local/in-frame field). If the gids do not
match, REJECT the fallback row (treat as miss) rather than serve it.

- **Pros:** lowest cold-frame cost (legacy partition already warm — no build on
  the read path, like Option B); highest migration safety (reads succeed
  throughout the migration); AND **closes the medium-cross-tenant-risk cell that
  plain dual-read carries** — the legacy project-only partition is multi-tenant,
  but the gid-exact re-assertion makes it impossible to serve the wrong tenant's
  row on the fallback (the row's gid would not match the anchored gid). Composes
  directly with INVARIANT GFR-IDENTITY-1 and the central guard's gid-exact read
  (TDD §5.3, §6.1). Zero new partition logic beyond the re-assertion check.
- **Cons:** the re-assertion adds a cheap gid-equality check on the fallback path
  (negligible cost); inherits the legacy shape's lifetime (cannot retire
  `legacy_fallback_enabled` — that is the migration owner's call); the
  re-assertion's correctness DEPENDS on the parent-chain anchor being right,
  which rests on the identity path (TDD §4-5), not on this ride alone.
- **cross_tenant_risk:** low (gid re-assertion neutralizes the legacy-fallback
  collision that made Option B medium)
- **coldframe_cost:** low
- **migration_safety:** high
- **scope note:** **closes Vector A ONLY.** Vector B
  (gid->project_gid->entity_type discriminator) is NOT addressed by any ride and
  is certified separately (TDD §11.5). The ride MUST NOT claim cross-tenant
  safety on its own.

## Why Option E (adoption rationale — PROPOSED)

The realization predicate makes cross-tenant correctness the dominant axis (R-1,
critical). Among the options:
- **B (plain dual-read)** has the best cold-frame/migration profile but a MEDIUM
  cross-tenant risk on its legacy fallback — the exact class of defect that made
  v1 NO-GO.
- **A / C (build-on-miss / hybrid)** lower the risk but at cold-frame cost and/or
  the most moving parts, and risk colliding with ADR-G2RECV cache-only for
  offer-domain.
- **D (partition-pinned)** is safe and cheap but has the LOWEST migration safety
  — it fails on legitimately-existing un-migrated data, contradicting "SUPPORT
  the migration, not execute it."
- **E** retains B's cold-frame/migration profile AND drops the cross-tenant risk
  to LOW by re-asserting gid-identity on the fallback. It is the only option that
  is simultaneously low-cross-tenant-risk, low-cold-frame-cost, and
  high-migration-safety. That is why it is adopted (PROPOSED). The PT-01 critic's
  specific charge: pressure-test whether the gid re-assertion is truly airtight
  on the legacy project-only partition — is there any path where a fallback row
  is served WITHOUT the re-assertion firing?

## Decision Criteria for PT-01

The realization predicate makes **cross-tenant correctness the dominant axis**
(R-1, critical). Cold-frame cost is second (north-star speed). Migration safety
mediates whether GFR is reliable DURING the migration vs only after it. The
rite-disjoint review critic must specifically pressure-test the chosen ride's
legacy-fallback path (if any) for cross-tenant key-collision — the medium-risk
cell in Option B/C is the load-bearing question.

## Consequences (shared across all options; E-specific noted)

- All five options use the MANDATORY entity-partitioned key shape for the primary
  read; they differ only in miss-handling.
- None EXECUTE the migration (`ADR-SEAM1:103-104`); A, C, and E forward-migrate
  or tolerate legacy frames as a side effect of reads, which is "support", not a
  bulk migration run. (E reads legacy on miss but does not build.)
- The central guard's entity_type key-shape + cache-only + identity-purity checks
  (TDD §6.1) apply regardless of ride; the ride choice changes the miss path, not
  the guard. **Option E adds one check on the miss path:** gid-equality
  re-assertion of the fallback row against the parent-chain-anchored gid.
- **Option E closes Vector A only.** Vector B
  (gid->project_gid->entity_type discriminator, `tier1.py:38/117`) maps
  gid->entity-TYPE not gid->tenant (project_gid is shared across tenants) and is
  certified SEPARATELY (`.ledge/reviews/gfr-vectorB-discriminator-cert.md`, TDD
  §11.5). No ride — E included — may claim cross-tenant safety on Vector B alone.
- qa-adversary hardens the ride with the dedup-loser cross-tenant fixture (TDD
  §12.2): seed a phone collision where the WRONG tenant is the legacy-fallback
  dedup-winner, assert E's gid re-assertion rejects it.

## Reversibility

The ride is a **two-way door** at the read layer (it changes how `engine.py`
constructs the read, not a schema or a public contract) — swapping rides later
is a localized change in `resolution/gfr/`. It becomes a one-way door only if a
ride retires `legacy_fallback_enabled` (Option A post-migration); that retirement
is the migration owner's call, NOT GFR's, and stays out of scope.

---

*DRAFT (v2). Enumerated by the 10x-dev architect at sprint-0, f4f924d2, per
`option-enumeration-discipline`. v2 ADDS Option E and ADOPTS it (PROPOSED);
confirmation/override is PT-01's with a rite-disjoint review critic. Option E
closes Vector A only; Vector B is certified separately. Self-grade [STRUCTURAL |
MODERATE] — the option slate is author-complete to the best of the architect's
vantage; the critic's job is precisely to surface any option (or any
re-assertion gap in E) this vantage cannot see.*
