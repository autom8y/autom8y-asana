/**
 * resolve-routing-address — the gated injection glue (TDD §3.4, §4.1).
 *
 * G-PROPAGATE (HARD): this module is a PURE RELAY. It NEVER constructs a routing
 * address in JS. The authority — guid -> "{guid}@appointments.contenteapp.com" —
 * is `autom8y_core.helpers.routing.format_routing_address` (Python, in autom8y).
 * This glue invokes that gate through the STABLE CLI contract and relays ONLY what
 * the gate printed. Zero formatter logic lives here. (TDD §3 constraint.)
 *
 * The CLI contract (TDD §3.3):
 *   Command:  autom8y-routing-address <guid>
 *   Success:  prints "{guid}@appointments.contenteapp.com\n" to stdout; exit 0
 *   Failure:  diagnostic to stderr; NOTHING to stdout; exit non-zero (the gate
 *             RAISES ValueError on bad/empty/injection input)
 *
 * Fail-closed taxonomy (every non-success collapses to `null`, NEVER a throw):
 *   - CLI missing on PATH (e.g. #719 not merged / SDK not installed) -> null
 *   - CLI non-zero exit (bad GUID -> gate RAISE)                     -> null
 *   - CLI success but empty/whitespace stdout                        -> null
 *   - CLI success but stdout is NOT a single canonical address       -> null
 *     (multi-line, extra content, wrong host, injection, a different
 *      address than the gate's own format — a buggy/compromised CLI)
 *   - CLI success with a single canonical-address line               -> that address
 *
 * A `null` return means the caller injects NO ?addr — the producer emits the
 * un-personalized placeholder template. A bad GUID — OR a buggy/compromised CLI —
 * can therefore NEVER yield a wrong address; the worst case is the (correct)
 * fallback placeholder. The relay's "NEVER a wrong address" guarantee holds in
 * ISOLATION: it does not trust the CLI's stdout blindly (TDD §3.4 fail-closed).
 */

import { execFileSync } from 'node:child_process';

/**
 * The default stable CLI console-script name (autom8y-core [project.scripts]
 * entrypoint). The production path resolves this from PATH.
 */
export const ROUTING_ADDRESS_CLI = 'autom8y-routing-address';

/**
 * Canonical routing-address acceptance pattern (G-PROPAGATE): exact-host +
 * canonical lowercase UUIDv4 local-part — the EXACT shape the autom8y-core gate
 * (format_routing_address) emits. This is an ACCEPTANCE MIRROR, NOT a formatter:
 * the relay derives NOTHING from it; it only refuses to relay any stdout that is
 * not byte-for-byte what the gate's own output looks like. Anchored start-to-end
 * (^…$) so trailing/leading content, extra lines, or injected payloads cannot
 * pass. Mirror of inline-dc-runtime CANONICAL_ADDR_RE and the deck's okAddr.
 */
export const CANONICAL_ADDR_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}@appointments\.contenteapp\.com$/;

/**
 * Resolve the CLI command to invoke. Read at CALL time (not module-load time) so
 * the acceptance shim's AUTOM8Y_ROUTING_ADDRESS_CLI override — pointing at a
 * contract-faithful real-Python executable on a temp path — takes effect even
 * when set after this module is imported. The override is a TEST seam only.
 */
function resolveCli() {
  return process.env.AUTOM8Y_ROUTING_ADDRESS_CLI || ROUTING_ADDRESS_CLI;
}

/**
 * Relay a business GUID through the #719 gate CLI and return the gated routing
 * address, or `null` on ANY non-success (fail-closed).
 *
 * This function constructs nothing. It marshals one argv in and returns the
 * gate's stdout out — or null. It is a pure relay (deterministic over the CLI's
 * own purity) with no network, no data-service, no formatting.
 *
 * @param {string} guid an existing business GUID (canonical lowercase UUID v4).
 *   NOT a rep-key — rep-key -> GUID resolution is S4's (live) scope, out of S2.
 * @returns {string | null} the gated address `"{guid}@appointments.contenteapp.com"`,
 *   or `null` (fail-closed) if the CLI is absent, exits non-zero, or prints nothing.
 */
export function gatedAddressForGuid(guid) {
  if (typeof guid !== 'string' || guid.length === 0) {
    // Defensive: a non-string / empty GUID never reaches the gate. Fail closed.
    return null;
  }

  let stdout;
  try {
    stdout = execFileSync(resolveCli(), [guid], {
      encoding: 'utf8',
      // Inherit nothing on stdin; capture stdout; swallow stderr (diagnostic only).
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (e) {
    // ENOENT (CLI missing on PATH) OR non-zero exit (gate RAISE on bad GUID).
    // Both are fail-closed: return null, the caller injects no address. We do
    // NOT rethrow — the template path is valid without a gated address.
    return null;
  }

  // ── Re-validate the CLI's stdout BEFORE returning (fail-closed in isolation) ──
  // The relay must be safe even if the CLI is buggy or compromised. We do NOT
  // trust stdout blindly: an adversarial shim (exit 0) could print a DIFFERENT
  // address, multiple lines, garbage, or a script-injection payload such as
  // `x</script><img onerror=…>@appointments.contenteapp.com`. We accept ONLY a
  // single line that is EXACTLY a canonical {uuidv4}@appointments.contenteapp.com
  // address (the gate's own output shape). Anything else -> null (no ?addr; the
  // producer emits the placeholder). This derives NOTHING (G-PROPAGATE) — it is a
  // pure accept/reject of the gate's stdout against the canonical mirror.
  const raw = stdout || '';
  // Reject multi-line output outright: a canonical relay emits ONE line. We trim
  // only the single trailing newline the gate writes (TDD §3.3), then assert the
  // remainder contains no embedded newline (no second line / no CR/LF injection).
  const trimmed = raw.trim();
  if (trimmed.length === 0) return null;
  if (/[\r\n]/.test(trimmed)) {
    // Multi-line stdout (extra content after the address line) — fail closed.
    return null;
  }
  if (!CANONICAL_ADDR_RE.test(trimmed)) {
    // Wrong host, non-canonical local-part, injection payload — fail closed.
    // NEVER relay a malformed / wrong-host / injected address.
    return null;
  }
  // Bind the relayed address to the INPUT guid. The gate is deterministic:
  // format_routing_address(guid) === `${guid}@appointments.contenteapp.com`, so
  // the local-part of a faithful stdout IS the input guid. A buggy/compromised
  // CLI that exits 0 but prints a canonical address for a DIFFERENT guid is
  // therefore detectable WITHOUT reconstructing the formatter (G-PROPAGATE): we
  // assert the gate echoed the guid we handed it. This derives nothing — it is a
  // pure equality check of stdout's local-part against the caller's own input.
  // (The gate emits canonical lowercase; the local-part class above is lowercase,
  // so we compare against the lowercased input guid.)
  const localPart = trimmed.slice(0, trimmed.indexOf('@'));
  if (localPart !== guid.toLowerCase()) {
    // The gate returned an address for a DIFFERENT guid than requested — a buggy
    // or compromised CLI. Fail closed: the relay must NEVER hand back an address
    // that does not correspond to the guid the caller asked about.
    return null;
  }
  return trimmed;
}
