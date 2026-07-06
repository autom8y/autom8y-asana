"""Permanent two-sided RENDER assert for the vendored deck producer (R1 guard).

The worst failure the telos names is a SILENT WRONG OUTCOME: a frozen deck
that renders BROKEN for the client, felt only after the send. Fault R1
(CDS 255c7c2): the dc-runtime's text-level ``parseDcText`` extractor
(``/<x-dc.../``.exec first-match + ``lastIndexOf("</x-dc>")`` + slice) plus an
UNCONDITIONAL ``fetch(location.href)`` re-hydration re-parsed the whole served
page and clobbered the good render with runtime JS AS VISIBLE CONTENT. The
producer inlines ``templates/<deck>/support.js`` verbatim at freeze
(``build/lib/inline-dc-runtime.mjs`` ``readFileSync``), so a stale re-vendor
silently re-ships the corruption -- exactly the drift this file exists to bite.

Three legs, all against a deck frozen by the REPO-VENDORED producer at test
time (never a checked-in artifact, so a producer regression cannot hide):

* **static discriminator** (needs node+producer only): the frozen bytes must
  carry the fixed DOM extractor and NONE of the corruptor's signature strings,
  plus the N-1 (``__dcMerge`` capture-then-strip) and fault-13 (wrap CSS +
  grapheme clamp) markers -- the four-fix co-presence the merge must preserve.
* **GREEN render** (needs the pre-installed Chromium headless shell; NEVER
  downloads): served over localhost HTTP (the corruption vector needs a
  succeeding ``fetch(location.href)`` -- it is INERT on ``file://``), the deck
  must render real content ("Prepared for <client>", ``<deck-stage``) with no
  runtime-JS-as-text corruption marker visible.
* **RED render / positive control (teeth):** the SAME assert must FLAG a
  deliberately-broken INPUT -- the frozen bytes with the fixed extractor
  surgically swapped back to the exact stale corruptor (the historical
  origin/main bytes). Discriminating-canary doctrine: the defect is injected
  into a throwaway FIXTURE, never into production code. If the surgery seams
  vanish (support.js refactored), the test FAILS LOUDLY instead of passing
  vacuously (broken-fixture trip).
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import http.server
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

from autom8_asana.automation.workflows.onboarding_walkthrough import deck_manifests
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    freeze_walkthrough_deck,
)

# --- Conventions (mirrors test_onboarding_walkthrough.py) ---

# Spike-proven canonical gated address (test GUID) -- same constant as the
# anchor suite. NEVER a live client address.
SPIKE_ADDRESS = "b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com"
CLIENT_NAME = "Restore Neuro Rehab"
DECK_TEMPLATE = "email-forwarding-setup"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _vendored_producer_dir() -> Path:
    """The REPO-VENDORED producer -- the freezer under guard (not the CDS dir)."""
    return _repo_root() / "vendor" / "deck-producer"


def _producer_available() -> bool:
    pdir = _vendored_producer_dir()
    return (
        shutil.which("node") is not None
        and (pdir / "build" / "inline.mjs").exists()
        and (pdir / "node_modules").exists()
    )


def _headless_shell() -> Path | None:
    """Locate a PRE-INSTALLED Chromium headless shell. Never downloads.

    Resolution order: ``CHROME_HEADLESS_SHELL_BIN`` env override, then the
    Playwright browser caches (``PLAYWRIGHT_BROWSERS_PATH`` or the platform
    default), newest build wins.
    """
    override = os.environ.get("CHROME_HEADLESS_SHELL_BIN")
    if override:
        p = Path(override)
        return p if p.is_file() else None
    if sys.platform == "darwin":
        default_cache = Path.home() / "Library" / "Caches" / "ms-playwright"
    else:
        default_cache = Path.home() / ".cache" / "ms-playwright"
    cache = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", default_cache))
    if not cache.is_dir():
        return None
    candidates = sorted(
        cache.glob("chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"),
        key=lambda p: p.parts,
    )
    for candidate in reversed(candidates):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


requires_producer = pytest.mark.skipif(
    not _producer_available(),
    reason="vendored Node producer not available (need node + vendor/deck-producer/node_modules)",
)
requires_browser = pytest.mark.skipif(
    _headless_shell() is None,
    reason="no pre-installed Chromium headless shell (ms-playwright cache); never downloaded",
)

# --- The corruptor surgery seams (exact bytes, both sides) ---
#
# FIXED = the CDS 255c7c2 code the producer inlines today (must be present in
# the frozen artifact). STALE = the exact pre-fix corruptor from the stale
# vendored support.js (autom8y-asana pre-re-vendor). The RED fixture is
# frozen-GREEN with FIXED -> STALE swapped; if a seam stops matching, the test
# fails loudly (fixture-broken trip) rather than passing vacuously.

_FIXED_EXTRACTOR_SEAM = """  function parseDcText(src) {
    const doc = new DOMParser().parseFromString(src, "text/html");
    const dc = doc.querySelector("x-dc");
    if (!dc) return null;
    const scriptEl = doc.querySelector("script[data-dc-script]");
    const { props, preview } = parseDataProps(
      scriptEl?.getAttribute("data-props") ?? null
    );
    return {
      template: dc.innerHTML,"""

_STALE_EXTRACTOR_SEAM = """  function parseDcText(src) {
    const openMatch = /<x-dc(?:\\s[^>]*)?>/.exec(src);
    if (!openMatch) return null;
    const close = src.lastIndexOf("</x-dc>");
    if (close === -1 || close < openMatch.index) return null;
    const template = src.slice(openMatch.index + openMatch[0].length, close);
    const doc = new DOMParser().parseFromString(src, "text/html");
    const scriptEl = doc.querySelector("script[data-dc-script]");
    const { props, preview } = parseDataProps(
      scriptEl?.getAttribute("data-props") ?? null
    );
    return {
      template,"""

_FIXED_FETCH_SEAM = """    // R1(b): parseDcDocument already selected the real <x-dc> template from the
    // live document by DOM query. The location.href re-fetch is a redundant
    // re-hydration path that re-parses the whole page — the vector that lets a
    // text-level extractor mis-select. Only re-fetch when the in-document parse
    // produced no template.
    if (!parsed.template) {
      fetch(location.href).then((res) => res.ok ? res.text() : "").then((t) => {
        const raw = t ? parseDcText(t) : null;
        if (raw?.template) runtime.updateHtml(rootName, raw.template);
      }).catch(() => {
      });
    }"""

_STALE_FETCH_SEAM = """    fetch(location.href).then((res) => res.ok ? res.text() : "").then((t) => {
      const raw = t ? parseDcText(t) : null;
      if (raw?.template) runtime.updateHtml(rootName, raw.template);
    }).catch(() => {
    });"""

#: Corruptor signature strings that must NEVER appear in a healthy frozen deck.
_CORRUPTOR_SIGNATURES = (
    'src.lastIndexOf("</x-dc>")',
    "const openMatch =",
)

#: dc-runtime source fragments that, when VISIBLE in the rendered body (outside
#: <script>/<style>), prove the R1 runtime-JS-as-content corruption fired.
_RENDERED_CORRUPTION_MARKERS = (
    "[dc-runtime]",
    "function updateHtml",
    "parsed.template",
    "compileTemplate(",
)


# --- Freeze / render helpers ---


@pytest.fixture(scope="module")
def frozen_deck() -> bytes:
    """Freeze the customer deck ONCE via the repo-vendored producer (real node)."""
    if not _producer_available():  # pragma: no cover - mirrored by skip markers
        pytest.skip("vendored Node producer not available")
    pdir = _vendored_producer_dir()
    out_filename = f"render-assert-{uuid.uuid4().hex}.html"
    frozen = asyncio.run(
        freeze_walkthrough_deck(
            producer_dir=pdir,
            deck_template=DECK_TEMPLATE,
            gated_address=SPIKE_ADDRESS,
            client_name=CLIENT_NAME,
            title=deck_manifests.load_title(DECK_TEMPLATE),
            out_filename=out_filename,
        )
    )
    # FR-8-style hygiene: the export file is a test byproduct; remove it.
    with contextlib.suppress(OSError):
        (pdir / "export" / out_filename).unlink()
    return frozen


@contextlib.contextmanager
def _serve(directory: Path) -> Iterator[str]:
    """Serve ``directory`` on an ephemeral localhost port (corruption needs HTTP)."""
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(directory),
    )

    class _QuietServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    with _QuietServer(("127.0.0.1", 0), handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


def _render_dom(url: str) -> str:
    """Dump the post-JS DOM of ``url`` via the pre-installed headless shell."""
    shell = _headless_shell()
    assert shell is not None, "requires_browser must gate callers"
    proc = subprocess.run(
        [
            str(shell),
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=8000",
            "--timeout=15000",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        timeout=45,
        check=False,
    )
    dom = proc.stdout.decode("utf-8", "replace")
    assert proc.returncode == 0 and dom.strip(), (
        f"headless render failed (exit={proc.returncode}): "
        f"{proc.stderr.decode('utf-8', 'replace')[:500]}"
    )
    return dom


def _visible_body(dom: str) -> str:
    """The rendered <body> markup with <script>/<style> payloads stripped.

    What remains is (a superset of) what the CLIENT sees. dc-runtime source
    text appearing here means the deck rendered runtime JS as content -- R1.
    """
    body = dom[dom.find("<body") :]
    body = re.sub(r"<script\b.*?</script>", "", body, flags=re.S | re.I)
    return re.sub(r"<style\b.*?</style>", "", body, flags=re.S | re.I)


def _corrupt(frozen: bytes) -> bytes:
    """Swap the fixed extractor back to the exact stale corruptor (RED fixture)."""
    text = frozen.decode("utf-8")
    n_extract = text.count(_FIXED_EXTRACTOR_SEAM)
    n_fetch = text.count(_FIXED_FETCH_SEAM)
    if n_extract < 1 or n_fetch < 1:
        pytest.fail(
            "R1 canary fixture seams not found in the frozen artifact "
            f"(extractor={n_extract}, fetch={n_fetch}). support.js drifted -- "
            "update _FIXED_*_SEAM/_STALE_*_SEAM so the positive control keeps teeth."
        )
    corrupted = text.replace(_FIXED_EXTRACTOR_SEAM, _STALE_EXTRACTOR_SEAM).replace(
        _FIXED_FETCH_SEAM, _STALE_FETCH_SEAM
    )
    assert corrupted != text
    return corrupted.encode("utf-8")


# --- Leg 1: static discriminator (no browser needed) ---


@requires_producer
class TestFrozenArtifactStaticDiscriminator:
    def test_fixed_extractor_present_and_corruptor_absent(self, frozen_deck: bytes) -> None:
        text = frozen_deck.decode("utf-8")
        # R1: the DOM-query extractor is inlined; the text-level corruptor is not.
        assert 'doc.querySelector("x-dc")' in text
        assert "r.htmlSeq" in text  # R1(c) stale-update generation guard
        for signature in _CORRUPTOR_SIGNATURES:
            assert signature not in text, f"stale corruptor re-vendored: {signature!r}"

    def test_merge_copresence_n1_and_fault13(self, frozen_deck: bytes) -> None:
        text = frozen_deck.decode("utf-8")
        # N-1: capture-then-strip of the identity params off the URL.
        assert "__dcMerge" in text
        assert "searchParams.delete('addr')" in text
        # fault-13: wrap CSS + grapheme-safe clamp on "Prepared for".
        assert "text-wrap:balance" in text
        assert "graphemes.slice(0, 139)" in text
        # The producer-injected gated address is baked in (freeze re-validates too).
        assert SPIKE_ADDRESS in text


# --- Legs 2+3: the two-sided headless RENDER assert ---


@requires_producer
@requires_browser
class TestWalkthroughRenderAssert:
    def test_green_frozen_deck_renders_content_not_runtime_js(
        self, frozen_deck: bytes, tmp_path: Path
    ) -> None:
        (tmp_path / "deck.html").write_bytes(frozen_deck)
        with _serve(tmp_path) as base:
            vis = _visible_body(_render_dom(f"{base}/deck.html"))
        # Personalization rendered for the client (fault-13 surface).
        assert f'Prepared for <span class="sc-interp">{CLIENT_NAME}</span>' in vis
        # Real deck content mounted.
        assert "<deck-stage" in vis
        # And NO runtime source leaked into the visible body (R1).
        for marker in _RENDERED_CORRUPTION_MARKERS:
            assert marker not in vis, (
                f"R1 REGRESSION: dc-runtime source {marker!r} is VISIBLE in the "
                "rendered deck body -- the producer froze a corrupting runtime"
            )

    def test_red_stale_corruptor_is_flagged(self, frozen_deck: bytes, tmp_path: Path) -> None:
        """Positive control: the assert has TEETH against the historical defect."""
        (tmp_path / "deck.html").write_bytes(_corrupt(frozen_deck))
        with _serve(tmp_path) as base:
            vis = _visible_body(_render_dom(f"{base}/deck.html"))
        flagged = [m for m in _RENDERED_CORRUPTION_MARKERS if m in vis]
        assert flagged, (
            "the RED fixture (exact stale text-extractor corruptor) rendered "
            "clean -- the render assert lost its teeth"
        )
