---
type: review
status: accepted
---

# OB-GUIDE byte-exact attestation — North Star Family Chiropractic pilot (N=1)

> forwarding-cutover-first-value · sprint-3 OB-GUIDE · principal-engineer (N3) · 2026-06-29
>
> **Honest rung:** `byte-exact-verified (qa GO, MODERATE) + staged — NOT attached, NOT live, NOT first-value-realized; LIVE attach + every Tier-B lever operator-terminal; PT-02 HALT stands`

Land predicate (a) of first-value: produce North Star Family Chiropractic's personalized
walkthrough deck carrying the **BYTE-EXACT** routing address
`d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com` (the FULL uuidv4 —
never the 8-char shorthand `d167d635@…`), byte-verify it, and STAGE the attach to Asana
task `1210776074464695`. Proven by a TWO-SIDED byte-diff through the REAL Node producer +
an INDEPENDENT oracle — never by "the producer ran".

## Anchors

| Anchor | Value | Verification |
|--------|-------|--------------|
| autom8y-asana worktree | `feat/fcfv-sprint3-ob-guide-attestation` off `6551aee0fe7d6d546917b511fc8daf4f0b4afb3c` | `git rev-parse HEAD` == `6551aee0…` (confirmed at setup) |
| autom8y-core (source anchor) | `autom8y f1f54612` → `autom8y-core==4.9.0` | f1f54612 per architect TDD; 4.9.0 directly verified (G-3) |
| autom8y-core (installed) | `4.9.0` | `importlib.metadata.version('autom8y-core')` → `4.9.0` |
| vendored producer | `vendor/deck-producer` (git-tracked, runtime-only node_modules = 190 files) | `git ls-files` |

## §0 — Build-env precondition gate (ORDERED, fail-closed) — ALL PASS

The gate fired honestly: G-1 caught an expired token and G-5 caught the wrong node — both
robustly resolved (re-mint / node22 on PATH), not papered over.

| Gate | Check | Result | Receipt |
|------|-------|--------|---------|
| **G-1** | CodeArtifact auth BEFORE any uv op | **PASS** (after re-mint) | Harness token was **EXPIRED** (`exp=1782331638`, −116.9h). Re-minted via `aws codeartifact get-authorization-token --domain autom8y --domain-owner 696318035277 --region us-east-1` → fresh token (`exp=1782795692`, valid 12.0h, sha256 prefix `eab65a636eaa7d05`); `UV_INDEX_AUTOM8Y_USERNAME=aws`. AWS identity `arn:aws:iam::696318035277:user/tom.tenuta`. |
| **G-2** | `uv sync --frozen` resolves core 4.9.0 from CodeArtifact (package env) | **PASS** | `uv sync --frozen` completed; `.venv` created at worktree root; `autom8y-core` installed `4.9.0`. |
| **G-3** | Import-shadow catch (3-fold) | **PASS** | `uv run --frozen --no-sync python -c "…version('autom8y-core')…format_routing_address('d167d635-…')"` → stdout `4.9.0` then `d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com`, exit 0. No stale 4.6.0 shadow (despite the autom8y-asana main checkout being on `chore/bump-core-4.6.0`). |
| **G-4** | `autom8y-routing-address` CLI | **PASS** | `uv run --frozen --no-sync autom8y-routing-address d167d635-1468-4ad5-9f88-8d44c8a4d1a9` → `d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com`, exit 0. |
| **G-5** | `node --version` ≥ v22 | **PASS** (after re-path) | mise default shim was **v20.10.0**; node 22.23.1 installed at `/Users/tomtenuta/.local/share/mise/installs/node/22/bin/node` → prepended to PATH → `node --version` = `v22.23.1`. Producer `package.json` requires `node >=22`. |
| **G-6** | Vendored producer present + complete | **PASS** | `build/inline.mjs` (9.5k), `node_modules/`, `build/vendor/react.umd.js` (11k), `build/vendor/fonts/fonts.base64.css` (199k) all present. |

## Step 1 — MINT (G-PROPAGATE; never hand-typed)

```
expected = format_routing_address("d167d635-1468-4ad5-9f88-8d44c8a4d1a9")
         = "d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com"
assert expected == "d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com"  # holds
```

Minted via `format_routing_address(guid)` DIRECTLY (not `resolve_routing_address_by_phone_async`
— no phone→guid re-resolution; the CRR-1 guid is held).

## Step 2 — RENDER (frozen-file receipt)

Rendered through the **PYTHON invoker** `freeze_walkthrough_deck(...)` (retains the
producer.py:141-142 output re-validation — NOT a raw `node inline.mjs` shell), deck
template `email-forwarding-setup` (FORK-DECK(a), the provider-agnostic forwarding deck),
client `North Star Family Chiropractic`.

| Field | Value |
|-------|-------|
| FROZEN_PATH | `/Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-fcfv-s3/vendor/deck-producer/export/walkthrough_1210776074464695_20260629170500.html` |
| FROZEN_SHA256 | `cc1702124d3af095288da75c37596cf7760f6b302c442485cf47665ba74f2644` |
| FROZEN_BYTES | `1047203` |
| PRESENCE(expected) | `True` (`expected.encode() in frozen`) |
| HARVESTED | `{'d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com'}` (exactly one) |
| PLACEHOLDER_RAW_PRESENT | `True` — the `xxxx-xxxx@appointments.contenteapp.com` placeholder IS in raw bytes (deck:342); the shape-based harvester correctly ignores it (`x` ∉ hex). This is why the oracle must NOT assert `b'xxxx-xxxx@…' not in frozen`. |

(The frozen file lives under the now-gitignored `export/` and is ephemeral; the sha256 is
the durable receipt. The operator re-renders at attach time per the staged parameters below.)

## Step 3 — Byte-diff oracle + two-sided proof (THE TEETH)

Durable test-support + tests added at
`tests/unit/automation/workflows/test_onboarding_walkthrough.py`:

- `harvest_appointment_addresses(frozen) -> set[str]` — version/variant-**AGNOSTIC** harvester
  `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}@appointments\.contenteapp\.com`,
  **strictly WEAKER** than the producer's `CANONICAL_ADDR_RE`
  (`inline-dc-runtime.mjs:115-116` — `^…-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-…$`, anchored + v4
  version nibble + variant nibble). Provably a superset of CANONICAL_ADDR_RE's acceptance
  set ⇒ NOT a reimplementation; excludes by shape both the `xxxx-xxxx` placeholder and the
  okAddr-regex source literal.
- `assert_byte_exact_tenant_address(frozen, expected)` — (1) presence + (2) exclusivity
  (`harvested == {expected}`); `expected` minted INDEPENDENTLY (never the fed `--addr`).

### Full suite result (NOT a `-k` subset)

`uv run --frozen --no-sync pytest tests/unit/automation/workflows/test_onboarding_walkthrough.py`
→ **33 passed, 1 skipped in 1.53s** (the skip is the `@integration` live-resolve test gated
on `AUTOM8Y_DATA_URL` — a reserved lever, untouched). The 14 new attestation tests + the
existing producer-real tests (run against the vendored producer) all GREEN.

### Two-sided RED/GREEN matrix (node-ids)

| AC | Arm | pytest node-id | Result |
|----|-----|----------------|--------|
| AC-1 | GREEN | `TestObGuideByteExactAttestation::test_ac1_green_oracle_passes_on_grandeur_render` | PASS — presence + exclusivity on the real d167d635 render |
| AC-1 | RED | `TestObGuideByteExactAttestation::test_ac1_red_no_addr_harvests_empty` | PASS — no `--addr` render → `harvest(...) == ∅` (placeholder invisible) |
| AC-2 | RED | `TestObGuideByteExactAttestation::test_ac2_red_prefix_shorthand_raises` | PASS — 8-char prefix `d167d635@…` → `ProducerFreezeError` (ADDR-NON-CANONICAL) |
| AC-2 | GREEN | `TestObGuideByteExactAttestation::test_ac2_green_full_uuid_accepted` | PASS — full uuidv4 accepted + frozen |
| **AC-3** | **GREEN** | `TestObGuideByteExactAttestation::test_ac3_green_byte_equal_independent_mint` | **PASS — feed `format_routing_address(d167d635-…)`, oracle vs INDEPENDENT `format_routing_address(d167d635-…)` → byte-equal** |
| **AC-3** | **RED** | `TestObGuideByteExactAttestation::test_ac3_red_wrong_but_canonical_caught` | **PASS — feed `format_routing_address(b167331c-536f-4996-9b2d-2f696f35f556)` (a DIFFERENT valid v4 the producer ACCEPTS), oracle vs d167d635 mint → RAISES. Teeth are producer-independent.** |
| AC-4 | RED | `TestObGuideMint::test_ac4_red_phone_or_name_raises_valueerror[7639994340]` | PASS — phone → `ValueError` |
| AC-4 | RED | `TestObGuideMint::test_ac4_red_phone_or_name_raises_valueerror[+17156902466]` | PASS — E.164 → `ValueError` |
| AC-4 | RED | `TestObGuideMint::test_ac4_red_phone_or_name_raises_valueerror[North Star Medical Clinic]` | PASS — name → `ValueError` |
| AC-4 | GREEN | `TestObGuideMint::test_ac4_green_guid_mints_grandeur_address` | PASS — the guid mints the grandeur address |
| AC-5 | GREEN | `TestOptInKillSwitch::test_unset_flag_disables` (+ `test_explicit_enable_proceeds`) | PASS (EXISTING — cited, nothing added; `AUTOM8_WALKTHROUGH_ENABLED` NEVER set by this work) |
| AC-6 | static | `TestObGuideOracleHygiene::test_ac6_oracle_source_has_no_live_attach_no_phone_or_name_resolution` | PASS — oracle source has no `upload_async` / `resolve_routing_address_by_phone` / `resolve_routing_address_by_name` / `nameparser` |
| AC-6+ | shape | `TestObGuideOracleHygiene::test_harvester_ignores_placeholder_and_shorthand_catches_canonical` | PASS — placeholder + 8-char shorthand invisible; canonical caught once |
| AC-6+ | shape | `TestObGuideOracleHygiene::test_harvester_strictly_weaker_than_canonical_addr_re` | PASS — harvester accepts a non-v4 UUID-shape CANONICAL_ADDR_RE rejects (proves strictly-weaker) |
| AC-7 | integrity | `TestObGuideByteExactAttestation::test_ac7_integrity_receipt_sha256_and_byte_diff_pass` | PASS — sha256 (64-hex) + byte-diff PASS on the real render |

**Why the RED arms have genuine teeth (discriminating-canary-doctrine §2.3):** the AC-3 RED
breaks the **INPUT** (feeds `b167331c-…`, a valid v4 the producer happily injects — the
wrong render is the SAME 1047203 bytes as the grandeur deck, since only the 36-char address
differs), and the SAME oracle that PASSES on d167d635 RAISES on b167331c. The surface is
never broken (no G-THEATER). A green producer run alone is rejected as theater.

## TIER-2 — headless personalized-render (AC-7) — RUN-GREEN

Provisioned cleanly OUT-OF-TREE (`npm install playwright@latest` into `/tmp/pw-tier2`,
imported by absolute path; the curated git-tracked `vendor/deck-producer/node_modules` was
NOT polluted). The cached chromium (build 1228, version 149.0.7827.55) matched playwright
1.61.1. Opened the FROZEN grandeur deck OFFLINE with NO `?addr` query (the frozen seed
activates). Receipt:

```json
{ "addrInDom": true, "fallbackPresent": false, "personalizedBranch": true,
  "notPersonalizedBranch": false, "externalRequests": 0, "pageErrors": 0 }
```

**TIER-2 PASS:** the `d167d635-…` grandeur address RENDERS `personalized===true` in the
browser DOM (not merely present in bytes), both fallbacks absent, fully offline. This is a
guid-SPECIFIC strengthening of the vendored `AC-G5'` (`acceptance.mjs:388`, which proves
render-personalization guid-agnostically on `KNOWN_GUID=b167331c`).

## Lint / lock receipts

| Check | Result |
|-------|--------|
| `ruff check .` | `All checks passed!` |
| `ruff format --check .` | `1175 files already formatted` |
| `uv.lock` | UNCHANGED (`git status` empty); `grep -c pypi.org uv.lock` = `0` |
| `pyproject.toml` | UNCHANGED |

## STAGED operator attach parameters (SURFACED, NOT EXECUTED — PT-02 HALT)

No Asana token was read; `/Users/tomtenuta/Code/autom8/.env` was never read or staged. The
LIVE attach is operator-terminal.

```
PARENT_TASK_GID : 1210776074464695
ATTACH_FILE     : /Users/tomtenuta/Code/a8/repos/autom8y-asana-wt-fcfv-s3/vendor/deck-producer/export/walkthrough_1210776074464695_20260629170500.html
                  (sha256 cc1702124d3af095288da75c37596cf7760f6b302c442485cf47665ba74f2644, 1047203 bytes;
                   re-render deterministically via the throwaway runner if the ephemeral export/ is cleared)
ATTACH_NAME     : walkthrough_1210776074464695_20260629170500.html   (matches ATTACHMENT_GLOB walkthrough_*.html)
CONTENT_TYPE    : text/html
TENANT_BINDING  : guid d167d635-1468-4ad5-9f88-8d44c8a4d1a9  (PREFERRED, zero re-resolution;
                  phone +17156902466 via Businesses task 1210665001963343 is the only fallback; NEVER name)
```

## G-PROPAGATE statement

- The frozen address is **byte-identical** to `format_routing_address("d167d635-1468-4ad5-9f88-8d44c8a4d1a9")`
  = `{NSF_GUID}@{APPOINTMENTS_DOMAIN}` = `d167d635-1468-4ad5-9f88-8d44c8a4d1a9@appointments.contenteapp.com`.
- The EBI `F-TP-1` fail-closed allowlist holds the SAME guid `d167d635-1468-4ad5-9f88-8d44c8a4d1a9`.
- **Reimplemented NONE** of the three frozen primitives: `format_routing_address` (autom8y-core gate,
  called directly), `CANONICAL_ADDR_RE` (producer-side validator), `injectFrozenAddress` (producer
  freeze). The oracle's harvester is a provably-WEAKER independent extractor, not a re-derivation.
- **N=1, positively selected:** the address is DERIVED from the confirmed guid via the gate — never
  reverse-matched from a render or name-guessed (G-DENOM).

## Honest rung (VERBATIM)

> `byte-exact-verified (qa GO, MODERATE) + staged — NOT attached, NOT live, NOT first-value-realized; LIVE attach + every Tier-B lever operator-terminal; PT-02 HALT stands`

## Commit scope

One atomic commit on `feat/fcfv-sprint3-ob-guide-attestation` — exactly three paths:
this attestation `.md`, the test additions (oracle + AC-1..AC-7), and the one `.gitignore`
line. NOT pushed / NOT PR'd / NOT merged (operator-terminal). The frozen deck, `.venv`, and
caches are gitignored and never staged.

---

## ⚠️ FAULT-13 ANNOTATION (2026-07-02/03)

The TIER-2 headless personalized-render attested the ADDRESS personalization only, with a
clean literal client fixture ("North Star Family Chiropractic") that never exercised the
task-name binding — the fixture masked seam S1 (fault 13). Boundary-length + provenance
legs now exist: AC-G5-LEN / AC-G5-LEN-CLAMP / AC-G5-UNI / AC-TITLE-DEFAULT (asana #196)
+ the field-level personalization gate with mutation-proven tests (#197).
