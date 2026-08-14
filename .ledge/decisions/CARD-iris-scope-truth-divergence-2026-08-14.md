---
type: decision
status: proposed
id: CARD-iris-scope-truth-divergence-2026-08-14
wave: chain-of-custody-closure (adjacent finding, NOT self-assigned)
opened_by: operator (Phase-2 sitting R-7, 2026-08-14)
owner: operator (execution routable to a security-seated wave)
self_assessment_cap: MODERATE
---

# CARD — iris governance-integrity: divergent scope truth

**What** (from the SEC-002 chain trace, `24a52c52` dossier): the logical
identity `iris` ≡ `autom8y-hermes` carries TWO divergent scope truths —
the SA registry path (read-only 5-scope set, exempt/bypass tuple) and an
OAuth-client terraform grant of `asana:read` that is **INERT at runtime**
(iris mints on the SA path, never the OAuth path), while the shipped hermes
docstring **advertises a scope set the runtime token does not carry**.
CF-1's "second uncounted population" inverted on trace: it is a
population-of-one, a **governance-truth defect** (what the system SAYS about
its own authority diverges from what is TRUE), not an access-control
differential.

**Why a card**: no live privilege differential exists today — but divergent
authority-truth is exactly the substrate silent authorization drift grows in
(cf. RE-2's filterless exemption path, boot-time tuple re-emitter). The
finding must not rot as a dossier footnote.

**The act (security-seated wave or operator directly)**:
1. Re-derive the divergence live (registry entry, OAuth-client terraform,
   the hermes docstring, an actual minted-token claim set — four surfaces,
   one truth expected).
2. Rule the canonical truth: either the OAuth `asana:read` grant is retired
   (population-of-one collapses to one path, docstring corrected), or the
   grant is real and the SA-path scope set widens FORMALLY through the
   registry with an exemption-block amendment — never informally.
3. Correct the advertising surface (docstring) to the ruled truth; receipts
   per surface.

**Guards**: read-only until ruled; any scope widening is operator-sovereign
and registry-governed (never issuance-time); interacts with the ratified
(f)+(a) RE-2 remediation — sequence this card behind or alongside it, not
against it.
