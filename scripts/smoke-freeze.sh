#!/usr/bin/env bash
# scripts/smoke-freeze.sh — in-container freeze smoke (CON-2)
#
# Proves node build/inline.mjs executes inside a built image containing the
# Node>=22 binary and the vendored deck-producer (A2-vendor bundle, N2 §3).
#
# N4 discovery: _ds_manifest.json and _ds_bundle.js (root-level) are required
# by resolve-deck.mjs in addition to the N2 minimum footprint; both are
# included in vendor/deck-producer/. --deck path must be RELATIVE to projectRoot
# (templates/ghl-calendar-setup, not an absolute path).
#
# Both legs MUST pass; script exits nonzero if either fails.
#
# Usage (local):
#   scripts/smoke-freeze.sh <docker-image>
#
# Leg 1 — valid addr: frozen deck emitted in-container AS appuser, no mount,
#          exit 0, frozen addr present in the in-container file.
# Leg 2 — broken addr: ADDR-NON-CANONICAL in stderr, exit nonzero, NO file.
#
# Prod-representative: runs as appuser with NO writable mount over export/.
# The assertion that the file was written is performed INSIDE the container.
# A writable host mount would mask the CLASS-1a EACCES failure mode (G-THEATER).

set -euo pipefail

IMAGE="${1:?Usage: smoke-freeze.sh <docker-image>}"
# Proper UUIDv4: third segment must start with 4, fourth with 8/9/a/b
ADDR="32df0345-50c6-4539-9c91-10174b1d1161@appointments.contenteapp.com"
SMOKE_TMP="$(mktemp -d)"

cleanup() { rm -rf "$SMOKE_TMP" 2>/dev/null || true; }
trap cleanup EXIT

echo "=== CON-2 freeze smoke: $IMAGE ==="

# ---------------------------------------------------------------------------
# Leg 1 — valid --addr
# Run AS appuser, NO writable mount. Assertion performed inside the container.
# ---------------------------------------------------------------------------
echo ""
echo "--- Leg 1: valid --addr -> frozen deck must be emitted (in-container, as appuser) ---"
docker run --rm \
  --user appuser \
  --entrypoint sh \
  "$IMAGE" -c '
    node /app/vendor/deck-producer/build/inline.mjs \
      --deck templates/ghl-calendar-setup \
      --title "GHL Calendar Setup — Contente" \
      --out GhlCalendarSetup.html \
      --addr "'"$ADDR"'" \
    && test -f /app/vendor/deck-producer/export/GhlCalendarSetup.html \
    && grep -q "'"$ADDR"'" /app/vendor/deck-producer/export/GhlCalendarSetup.html'
echo "PASS: Leg 1 — frozen deck emitted with address frozen in place (in-container, as appuser)"

# ---------------------------------------------------------------------------
# Leg 2 — broken --addr
# Run AS appuser, NO writable mount. Assert: exit nonzero + ADDR-NON-CANONICAL
# in output + NO file written. Output captured to host scratch (not mounted).
# ---------------------------------------------------------------------------
echo ""
echo "--- Leg 2: broken --addr -> ADDR-NON-CANONICAL, exit nonzero, no file (in-container, as appuser) ---"
LEG2_STDERR_FILE="$SMOKE_TMP/.leg2_output"
set +e
docker run --rm \
  --user appuser \
  --entrypoint sh \
  "$IMAGE" -c '
    node /app/vendor/deck-producer/build/inline.mjs \
      --deck templates/ghl-calendar-setup \
      --title "GHL Calendar Setup — Contente" \
      --out GhlCalendarSetup.html \
      --addr "not-a-valid-address"; rc=$?
    if [ -f /app/vendor/deck-producer/export/GhlCalendarSetup.html ]; then
      echo "FAIL: file written despite broken addr" >&2; exit 99; fi
    exit $rc' >"$LEG2_STDERR_FILE" 2>&1
LEG2_EXIT=$?
set -e
cat "$LEG2_STDERR_FILE"
echo "exit: $LEG2_EXIT"
if [ "$LEG2_EXIT" -eq 0 ]; then
  echo "FAIL: Leg 2 — expected nonzero exit on broken addr, got 0" >&2; exit 1
fi
if ! grep -q "ADDR-NON-CANONICAL" "$LEG2_STDERR_FILE"; then
  echo "FAIL: Leg 2 — ADDR-NON-CANONICAL not found in output" >&2; exit 1
fi
echo "PASS: Leg 2 — ADDR-NON-CANONICAL confirmed, exit $LEG2_EXIT, no file"

echo ""
echo "=== smoke-freeze PASSED (both legs) ==="
