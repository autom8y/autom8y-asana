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
# Leg 1 — valid addr: frozen deck emitted, exit 0, frozen addr present in file
# Leg 2 — broken addr: ADDR-NON-CANONICAL in stderr, exit nonzero, NO file

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
# ---------------------------------------------------------------------------
echo ""
echo "--- Leg 1: valid --addr -> frozen deck must be emitted ---"
docker run --rm \
  --entrypoint node \
  -v "$SMOKE_TMP:/app/vendor/deck-producer/export" \
  "$IMAGE" \
  /app/vendor/deck-producer/build/inline.mjs \
    --deck templates/ghl-calendar-setup \
    --title "GHL Calendar Setup — Contente" \
    --out GhlCalendarSetup.html \
    --addr "$ADDR"

FROZEN_FILE="$SMOKE_TMP/GhlCalendarSetup.html"
if [ ! -f "$FROZEN_FILE" ]; then
  echo "FAIL: Leg 1 — frozen file not emitted" >&2; exit 1
fi
if ! grep -q "$ADDR" "$FROZEN_FILE"; then
  echo "FAIL: Leg 1 — frozen address not found in output file" >&2; exit 1
fi
echo "PASS: Leg 1 — frozen deck emitted with address frozen in place"
ls -lh "$FROZEN_FILE"

# ---------------------------------------------------------------------------
# Leg 2 — broken --addr
# Uses a temp file to capture stderr without losing exit code in subshell.
# ---------------------------------------------------------------------------
echo ""
echo "--- Leg 2: broken --addr -> ADDR-NON-CANONICAL, exit nonzero, no file ---"
rm -f "$FROZEN_FILE"
LEG2_STDERR_FILE="$SMOKE_TMP/.leg2_stderr"
set +e
docker run --rm \
  --entrypoint node \
  -v "$SMOKE_TMP:/app/vendor/deck-producer/export" \
  "$IMAGE" \
  /app/vendor/deck-producer/build/inline.mjs \
    --deck templates/ghl-calendar-setup \
    --title "GHL Calendar Setup — Contente" \
    --out GhlCalendarSetup.html \
    --addr "not-a-valid-address" >"$LEG2_STDERR_FILE" 2>&1
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
if [ -f "$FROZEN_FILE" ]; then
  echo "FAIL: Leg 2 — file written despite broken addr (must be NO FILE)" >&2; exit 1
fi
echo "PASS: Leg 2 — ADDR-NON-CANONICAL confirmed, exit $LEG2_EXIT, no file"

echo ""
echo "=== smoke-freeze PASSED (both legs) ==="
