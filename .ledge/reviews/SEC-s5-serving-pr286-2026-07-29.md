---
id: SEC-s5-serving-pr286
slug: substrate-v2-s5-serving
type: review
status: complete
reviewer: security-reviewer (security rite, co-seated into 10x-dev)
date: 2026-07-29
pr: 286
verdict: Approve            # APPROVE-WITH-ADVISORIES — schema enum {Approve|Request-Changes|Reject}
blocking_findings: []       # SI-5 recede binding: Approve carries NO blocking_findings (none found)
prod_touch: NONE
evidence_grade: STRONG (disclosure-surface enumeration — direct code inspection + read passing tests)
                MODERATE (forward-looking advisories A1/A2 — future-wiring / probabilistic behavior)
---

# Security Co-Review — substrate-v2 S5 serving (PR #286)

**Scope:** DP-3 cross-service ONE-WAY door + the `RefusePayload` EXTERNAL-DISCLOSURE
surface reaching MCP / delegated-fleet (LLM-facing) consumers.
**Files:** `src/autom8_asana/substrate/serve.py`, `.../serve_adapters.py`,
`mcp/asana_mcp/errors.py` (+ `tests/unit/substrate/*`, `mcp/.../tools/_common.py`).
**Verdict: APPROVE-WITH-ADVISORIES.** No Critical/High/Medium finding; no blocking
finding; no formal-gate escalation. Three LOW forward-looking advisories (all S8-cutover
obligations; the seam is DARK — no consumer repointed). Two clean rulings.

---

## FOCUS 1 — Disclosure surface (every field crossing the wire) — CLEAN

Refusal 424 body (`serve_adapters._refusal_envelope`, serve_adapters.py:175-203):

| field | type / value | leaks topology? |
|---|---|---|
| `substrate_refused` | `True` (refusal marker, NOT a data field) | no |
| `reason` | enum {stale,corrupt,missing,divergent} | no |
| `code` | `SUBSTRATE_REFUSED_{REASON}` (enum-derived) | no |
| `plane` | logical `v2/{entity_type}` (`_plane_label`, serve.py:201-209) | **no** — never an S3 key/bucket/version/path |
| `absolute_age_seconds` | map `{plane → float}` (the caller's OWN artifact age) | no |
| `divergence_magnitude` | `0.0` on the live path | no |
| `per_section_delta` | `{}` on the live path (see A1) | no |
| `sunset_breach` | `{surface(=plane), sunset_after(iso), observed_at(iso)}` when present | no — `SunsetBreach` carries the logical plane label + two instants only (serve.py:40-59) |
| header `Retry-After` | int (see A2) | no |

422 unservable body (`_unservable_entity`, serve_adapters.py:285-298): `substrate_refused`,
`code=SUBSTRATE_UNSERVABLE_ENTITY_TYPE`, `entity_type=<caller's own echoed input>`.

**Verified no physical key/path interpolates into any detail/message:** `_plane_label`
returns `f"v2/{aid.entity_type.value}"` — a logical label; the physical key builder is
the SEPARATE `artifact_key` = `dataframes-v2/{gid}/{entity}` (identity.py:68-75), which
never touches the refusal body. Ages are numeric; magnitude/delta are numeric/empty.
`project_gid` is deliberately omitted from the plane label (serve.py:206-208). The
un-digestable-frame path logs `exc_info=True` to **logs only** (serve.py:432-436) and
returns `RefuseReason.CORRUPT` + age-only payload to the wire — no stack trace / exception
repr crosses. Asserted by construction AND by `test_cp345_refusal_body_carries_no_topology`
(greps the whole serialized body for `dataframes-v2`) + `test_refusal_payloads_carry_no_topology`.

## FOCUS 2 — Enumeration oracle — RULED SAFE (contingent on FOCUS 5)

Distinguishability for a caller supplying `(project_gid, entity_type)`:
- non-servable / unknown / malformed entity_type → **422**, `reader.reads == []` (refused at
  the boundary, never reaches serving — `test_cp345_query_adapter_unknown_entity_is_a_422_client_error`);
- malformed project_gid (non-digit; `_PROJECT_GID_PATTERN.fullmatch`, identity.py:30/62) → **422**;
- valid + never-built/reaped → **424 MISSING** (empty plane, empty age — `missing_payload`, serve.py:154-163);
- valid + stale → **424 STALE** (populated plane + age);
- valid + provable → **200**.

**Ruling — NOT an enumeration oracle for unknown projects/entities:**
(a) the servable entity_type **set** is public product-schema (registry-derived warmable
entities, C6; identical for every tenant — not customer data), and non-servable is refused
*pre-serving* at 422 with the reader untouched, so the 424 surface cannot probe entity-type
existence; (b) reaching MISSING/STALE/200 requires a well-formed digit project_gid — the
gid space is not brute-forceable and, by design, upstream auth gates project addressability.
The residual disclosure (MISSING vs STALE vs 200 are mutually distinguishable by status +
body + timing — MISSING short-circuits at `store.read_current` *before* the frame read,
serve.py:413-416) reveals per-artifact **build/freshness state** for a project the caller
can already address — legitimate visibility for an authorized caller. **This safety is
CONTINGENT on the FOCUS-5 upstream auth boundary** (advisory A3). Timing adds nothing beyond
what the `reason` field already discloses.

## FOCUS 3 — Injection (per_section_delta → LLM) — LOW / latent (advisory A1)

`per_section_delta` KEYS are Asana section names (user-controlled upstream). Current risk is
**double-gated to zero**: (1) every live-path payload constructor sets `per_section_delta={}`
(serve.py:154-198 + the inline PointerCorrupt payload:423) — the populated-delta DIVERGENT case
is "unconstructable through the single-source v2 read path" (serve.py:170-176); (2) the MCP
`map_http_error` path does NOT extract `per_section_delta` into the LLM-facing `to_tool_payload`
(errors.py:48-58, 145-215) — only `code`/nested-`message` reach the model, and the flat substrate
body has no nested `error` envelope. See A1 for the latent path.

## FOCUS 4 — DoS / amplification — RULED (no refusal amplification; A2 for retry-storm)

**No cheap-to-trigger expensive path.** MISSING / pointer-CORRUPT short-circuit *before* the
frame read (cheaper than a serve). STALE / undigestable-CORRUPT / PROVABLE all pay the SAME
read-current + `digest_of_frame` cost (serve.py:413-457) — a refusal is never *more* expensive
than a success, so an attacker cannot amplify by forcing refusals. The digest-every-read (C2, no
result-cache above the gate; `test_serve_no_result_cache.py`) is the inherent cost of the freshness
guarantee, borne equally by 200 and 424, mitigated by upstream rate-limiting (the 429 `rate_limit`
class exists, errors.py:175-183). Retry-After storm → advisory A2.

## FOCUS 5 — Auth boundary — RULED CLEAN (CP-6 does not widen access)

The serving seam is auth-delegated-upstream BY DESIGN. `SubstratePersistenceReader` (CP-6,
serve_adapters.py:304-321) is a thin pass-through to the SAME gated reader, takes a TYPED
`ArtifactId` (no `entity_type: str|None` plane-blind surface — the v1 DEFECT:38 hole is
unconstructable), and imports neither `store.read_current` nor `load_dataframe` (structurally
asserted by `test_serve_adapters_never_call_read_current` + `test_serve_adapters_do_not_import_the_store`).
It is a server-internal storage wrapper, NOT a new external wire surface, and grants no access
beyond CP-3/4/5. It does not widen access. The only obligation is the shared S8 auth-wiring one (A3a).

## FOCUS 6 — mcp/errors.py 424 branch — CONFIRMED classification-only

`git diff main` on errors.py adds exactly ONE branch (errors.py:193-215): status 424 →
`McpToolError(kind="data-integrity-refusal", retryable=False, honors Retry-After)`. No I/O,
no state, no new capability; ADDITIVE + INERT (dead until v2 flips). `_common.py` `get_json`/
`post_json` RAISE `map_http_error` on non-200, so the rich 424 body never reaches
`shape_execution_result` — only the mapped error (curated message + `_upstream_suffix`) reaches
the LLM. For the flat substrate body `_upstream_suffix` extracts only `code` (enum-derived) —
no message/details/section-names flow. Confirmed.

---

## Advisories (all LOW, forward-looking; the seam is DARK)

- **A1 — per_section_delta injection latent surface.** Surface: `_refusal_envelope`
  serializes `per_section_delta` verbatim (serve_adapters.py:192); keys are user-controlled
  Asana section names. Risk: NONE today (empty on live path + not extracted by the MCP mapper);
  IF the two-copy DIVERGENT path is wired live populating raw section names AND a consumer renders
  the RAW 424 body into LLM context, prompt-injection-shaped keys reach the model unbounded.
  Fix: before wiring the DIVERGENT path, add key sanitization + length/count bounds at
  `_refusal_envelope` (one choke-point covers all CPs). Track as an S8 gate.

- **A2 — Retry-After has no jitter → synchronized-retry-storm.** Surface: fixed
  `Retry-After: {retry_after_seconds}` (serve_adapters.py:226), echoed MCP-side. Risk: a plane
  going stale refuses many clients at once → lockstep retry herd on the rebuild path when it is
  already behind. LOW (dark seam; refusal body cheap to serve; herd hits idempotent rebuild not
  serve; the 424 non-hot-retry classification already blunts tight loops). Fix: apply jitter to
  Retry-After at the S8 wiring site, or codify a consumer-side jitter obligation in DP-3.

- **A3 — enumeration-safety is contingent on the upstream auth boundary; docstring rationale
  imprecise.** (a) The S8 cutover MUST place every wire-exposed CP (3/4/5) behind the same auth
  the v1 surfaces required, so an unauthorized caller cannot use the MISSING/STALE/200 trichotomy
  as a per-project freshness oracle. (b) Comment precision: the serve.py:161 rationale
  "Missing-vs-unknown are the SAME shape" is loose — MISSING(424) and unknown(422) are different
  statuses/shapes, and MISSING(empty payload) is distinguishable from STALE(populated payload);
  the accurate safety argument is "public type-set (422 pre-serving) + auth-gated gid." Code is
  correct; the stated rationale should be tightened. No code change required.

## Signoff conditions (S8-cutover, carried forward — none block THIS PR)
1. Sanitize/bound `per_section_delta` keys before the DIVERGENT path is wired live (A1).
2. Jitter Retry-After (or codify consumer jitter obligation) before/at cutover (A2).
3. Wire every external CP behind the upstream auth context v1 required (A3a / FOCUS 5).

## Attestation table (all Read/inspected this review)

| Artifact | Absolute path |
|---|---|
| serve core | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s5/src/autom8_asana/substrate/serve.py |
| serve adapters | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s5/src/autom8_asana/substrate/serve_adapters.py |
| mcp errors | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s5/mcp/asana_mcp/errors.py |
| mcp _common (non-200 raise) | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s5/mcp/asana_mcp/tools/_common.py |
| identity (ArtifactId guard) | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s5/src/autom8_asana/substrate/identity.py |
| serve tests | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s5/tests/unit/substrate/test_serve.py |
| adapters tests | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana-wt-w2-s5/tests/unit/substrate/test_serve_adapters.py |
| DP-3 contract | /Users/tomtenuta/Code/a8/a8/repos/autom8y-asana/.ledge/decisions/DP-3-consumer-contracts.md |

Evidence grade: FOCUS 1-6 rulings STRONG (direct code inspection corroborated by read passing
tests). Advisories A1/A2 MODERATE (forward-looking / future-wiring). Single-reviewer verdict.
