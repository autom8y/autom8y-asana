"""D10(b) rendered-deck check: render the staged deck in a real browser and assert it.

Governing record: RATIFICATION-onboarding-deck-workflow-decision-space-2026-11-07 D10(b)
("an automated rendered-deck check built into the recipe shows only the clinic's own
address, with no placeholder or unfilled fields"); design FORK-S2 (pythia, 2026-11-07).

Why RENDER, not only the frozen bytes: the static tenant-binding oracle
(:mod:`tenant_binding`) reads the frozen bytes. It cannot see an address that the
page's own script assembles at runtime, and it cannot see the R1 corruption (the stale
dc-runtime re-parses the served page and paints its own JS source as visible content).
Both are visible only after a browser runs the page over HTTP. This module is that
check, shared by the produce step and the deploy gate.

Fail-closed everywhere. There is no skip path in this module: no browser is
:class:`BrowserUnavailable` (stop and ask the operator), an override that is not an
executable is :class:`BrowserOverrideInvalid` (never a silent fall-through), and a
failed, empty or timed-out render is :class:`RenderCheckRefused`. This module never
downloads a browser. Skips exist only as pytest markers in the test suite.

Layout served: ``<deploy_root>`` is served on 127.0.0.1 and ``/<slug>/`` is rendered,
the same path shape as the live capability URL, with the ``_headers`` block of
:data:`host_bundle.HEADERS_FILE_CONTENT` sent on every response (``no-store``, so a
re-fetch of ``location.href`` is a 200 as on the live host, never a 304).

CLI (the deploy gate; no Asana reads)::

    python -m autom8_asana.automation.workflows.onboarding_walkthrough.render_check \\
        --deploy-base <abs deploy root> --state-dir <abs floodgates state dir>

Exit 0 only when every staged deck passed; 1 on any refusal (including zero decks
checked); 2 when no usable browser exists (stop and ask the operator).
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import functools
import hashlib
import html
import http.server
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NoReturn

from autom8y_log import get_logger

from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    Phase,
    StateStore,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.host_bundle import (
    HEADERS_FILE_CONTENT,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.tenant_binding import (
    CANONICAL_ROUTING_ADDR_RE,
    _mask_addr,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

logger = get_logger(__name__)

__all__ = [
    "BROWSER_OVERRIDE_ENV",
    "KEYCHAIN_FLAGS",
    "PLACEHOLDER_TOKENS",
    "RENDERED_CORRUPTION_MARKERS",
    "Browser",
    "BrowserOverrideInvalid",
    "BrowserUnavailable",
    "RenderCheckRefused",
    "RenderGateRefused",
    "RenderReceipt",
    "assert_rendered_deck",
    "browser_version",
    "check_staged_deck",
    "find_browser",
    "main",
    "render_argv",
    "render_dom",
    "render_gate",
    "require_browser",
    "serve_directory",
    "visible_body",
]

#: Explicit browser override. Set but not an executable file -> BrowserOverrideInvalid.
BROWSER_OVERRIDE_ENV = "CHROME_HEADLESS_SHELL_BIN"

#: Flags on EVERY browser invocation (render and --version probe). macOS: a fresh
#: --user-data-dir otherwise makes Chrome ask the login keychain for "Chrome Safe
#: Storage", which raises a "keychain cannot be found" dialog for the operator.
KEYCHAIN_FLAGS: tuple[str, ...] = ("--use-mock-keychain", "--password-store=basic")

#: The subprocess ceiling for one render (the browser's own --timeout is 15 s).
RENDER_TIMEOUT_S = 45

#: dc-runtime source fragments that, when VISIBLE in the rendered body (outside
#: <script>/<style>), prove the R1 runtime-JS-as-content corruption fired.
RENDERED_CORRUPTION_MARKERS: tuple[str, ...] = (
    "[dc-runtime]",
    "function updateHtml",
    "parsed.template",
    "compileTemplate(",
)

#: Unfilled-field tokens that must never be visible in a client's rendered deck. The
#: template's own ``{{ ... }}`` placeholders are consumed by the runtime, so any that
#: survive into the visible body are unfilled fields (FORK-S2 probe: zero on GREEN).
PLACEHOLDER_TOKENS: tuple[str, ...] = (
    "xxxx",
    "{{",
    "}}",
    "{guid}",
    "{addr}",
    "<clinic>",
    "&lt;clinic&gt;",
)

_EMPTY_INTERP = '<span class="sc-interp"></span>'
_DECK_STAGE = "<deck-stage"

#: The macOS system Applications folder (absolute, so discovery never depends on HOME).
MACOS_SYSTEM_APPLICATIONS = Path("/Applications")
#: Installed Chromium-family browsers, macOS (under /Applications, then ~/Applications).
_MACOS_APP_BINARIES: tuple[str, ...] = (
    "Google Chrome.app/Contents/MacOS/Google Chrome",
    "Chromium.app/Contents/MacOS/Chromium",
)
#: Installed Chromium-family browsers, Linux (resolved with shutil.which).
_LINUX_BROWSER_NAMES: tuple[str, ...] = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)
_PLAYWRIGHT_SHELL_GLOB = "chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"
_PLAYWRIGHT_REVISION_RE = re.compile(r"chromium_headless_shell-(\d+)$")


class RenderCheckRefused(RuntimeError):
    """Fail-closed refusal of the D10(b) rendered-deck check.

    ``reason`` is a stable machine code (one per failure, in the style of
    ``DeployRootRefused``); the message masks every routing address.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(f"[{reason}] {message}")
        self.reason = reason


class BrowserUnavailable(RenderCheckRefused):
    """No usable browser: stop and ask the operator. Never skip, never download."""


class BrowserOverrideInvalid(BrowserUnavailable):
    """``CHROME_HEADLESS_SHELL_BIN`` is set but is not an executable file (no fall-through)."""


def _refuse(
    reason: str, message: str, *, cls: type[RenderCheckRefused] = RenderCheckRefused
) -> NoReturn:
    # Reason code only: the detail can carry the clinic name (clinic_missing), which stays
    # out of the structured log (D12; the operator reads it from the raised message).
    logger.error("render_check_refused", reason=reason)
    raise cls(reason, message)


# --- Browser resolution (FORK-S2 (a)) ---


@dataclasses.dataclass(frozen=True)
class Browser:
    """A resolved Chromium-family binary and the headless mode it needs."""

    path: Path
    kind: Literal["shell", "chrome"]

    @classmethod
    def at(cls, path: Path) -> Browser:
        """Classify by binary name: ``headless-shell`` -> shell, else full chrome."""
        return cls(path=path, kind="shell" if "headless-shell" in path.name else "chrome")


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _playwright_cache_dir() -> Path:
    if sys.platform == "darwin":
        default = Path.home() / "Library" / "Caches" / "ms-playwright"
    else:
        default = Path.home() / ".cache" / "ms-playwright"
    return Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or default)


def _playwright_candidates() -> list[Path]:
    """Playwright headless-shell builds, newest revision first."""
    cache = _playwright_cache_dir()
    if not cache.is_dir():
        return []

    def revision(path: Path) -> tuple[int, tuple[str, ...]]:
        for part in path.parts:
            match = _PLAYWRIGHT_REVISION_RE.match(part)
            if match:
                return int(match.group(1)), path.parts
        return -1, path.parts

    return sorted(cache.glob(_PLAYWRIGHT_SHELL_GLOB), key=revision, reverse=True)


def _macos_app_roots() -> tuple[Path, ...]:
    # Absolute system root first (found even under an empty HOME), then the user's.
    return (MACOS_SYSTEM_APPLICATIONS, Path.home() / "Applications")


def _installed_candidates() -> list[Path]:
    if sys.platform == "darwin":
        return [root / rel for root in _macos_app_roots() for rel in _MACOS_APP_BINARIES]
    found: list[Path] = []
    for name in _LINUX_BROWSER_NAMES:
        hit = shutil.which(name)
        if hit:
            found.append(Path(hit))
    return found


def _locations_tried() -> list[str]:
    tried = [f"env {BROWSER_OVERRIDE_ENV} (unset)"]
    tried.append(f"Playwright cache {_playwright_cache_dir() / _PLAYWRIGHT_SHELL_GLOB}")
    if sys.platform == "darwin":
        tried.extend(str(root / rel) for root in _macos_app_roots() for rel in _MACOS_APP_BINARIES)
    else:
        tried.extend(f"PATH lookup {name}" for name in _LINUX_BROWSER_NAMES)
    return tried


def find_browser() -> Browser | None:
    """Resolve a PRE-INSTALLED Chromium-family browser. Never downloads.

    Order: ``CHROME_HEADLESS_SHELL_BIN`` (set but not an executable file raises
    :class:`BrowserOverrideInvalid`; it never falls through), then the Playwright cache
    (``PLAYWRIGHT_BROWSERS_PATH`` or the platform default, newest build first), then
    installed browsers (macOS app bundles under /Applications then ~/Applications; Linux
    ``shutil.which``). Returns ``None`` when nothing is found -- callers that must render
    use :func:`require_browser`, which refuses instead.
    """
    override = os.environ.get(BROWSER_OVERRIDE_ENV)
    if override is not None:  # set, even to "", is an explicit choice: never fall through
        path = Path(override)
        if not _is_executable_file(path):
            _refuse(
                "browser_override_invalid",
                f"{BROWSER_OVERRIDE_ENV}={override!r} is not an executable file; fix or unset "
                "it (an explicit override never falls through to discovery)",
                cls=BrowserOverrideInvalid,
            )
        return Browser.at(path)
    for candidate in [*_playwright_candidates(), *_installed_candidates()]:
        if _is_executable_file(candidate):
            return Browser.at(candidate)
    return None


def require_browser() -> Browser:
    """:func:`find_browser`, or raise :class:`BrowserUnavailable` naming every location tried."""
    browser = find_browser()
    if browser is None:
        _refuse(
            "browser_unavailable",
            "no pre-installed Chromium-family browser found; tried: "
            + "; ".join(_locations_tried())
            + f". Stop and ask the operator (set {BROWSER_OVERRIDE_ENV} to an installed "
            "browser). This check never skips and never downloads.",
            cls=BrowserUnavailable,
        )
    return browser


@functools.cache
def _version_of(path: str) -> str:
    try:
        proc = subprocess.run(
            [path, *KEYCHAIN_FLAGS, "--version"], capture_output=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unknown ({type(exc).__name__})"
    text = proc.stdout.decode("utf-8", "replace").strip()
    return text if proc.returncode == 0 and text else f"unknown (exit={proc.returncode})"


def browser_version(browser: Browser) -> str:
    """The browser's ``--version`` string (run once per binary), for the run receipt."""
    return _version_of(str(browser.path))


# --- Serve and render (FORK-S2 (b)) ---


def _parse_headers_block(content: str) -> list[tuple[str, str]]:
    """The ``Name: value`` pairs of the ``/*`` rule block of a Pages ``_headers`` file."""
    pairs: list[tuple[str, str]] = []
    in_block = False
    for line in content.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            in_block = line.strip() == "/*"
            continue
        if in_block:
            name, sep, value = line.strip().partition(":")
            if sep:
                pairs.append((name.strip(), value.strip()))
    return pairs


#: Headers the localhost server sends on every response, mirroring the live host.
SERVED_HEADERS: tuple[tuple[str, str], ...] = tuple(_parse_headers_block(HEADERS_FILE_CONTENT))
if not any(
    name.lower() == "cache-control" and "no-store" in value for name, value in SERVED_HEADERS
):
    raise RuntimeError(  # pragma: no cover - import-time contract with host_bundle
        "HEADERS_FILE_CONTENT lost Cache-Control: no-store; the localhost render would "
        "diverge from the live host (304 re-fetch)"
    )


class _HostHeadersHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        for name, value in SERVED_HEADERS:
            self.send_header(name, value)
        super().end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


class _LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@contextlib.contextmanager
def serve_directory(root: Path) -> Iterator[str]:
    """Serve ``root`` on an ephemeral 127.0.0.1 port with the deck host's headers.

    HTTP, not ``file://``: the R1 vector (a succeeding ``fetch(location.href)``) is inert
    on ``file://``, which would make the render a vacuous GREEN.
    """
    handler = functools.partial(_HostHeadersHandler, directory=str(root))
    with _LoopbackServer(("127.0.0.1", 0), handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


def render_argv(url: str, browser: Browser, user_data_dir: Path) -> list[str]:
    """The exact argv for one render: fresh profile, no keychain, headless flag per kind."""
    headless = "--headless" if browser.kind == "shell" else "--headless=new"
    return [
        str(browser.path),
        headless,
        f"--user-data-dir={user_data_dir}",
        *KEYCHAIN_FLAGS,
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=8000",
        "--timeout=15000",
        "--dump-dom",
        url,
    ]


def render_dom(url: str, browser: Browser) -> str:
    """Dump the post-JS DOM of ``url``. Refuses on non-zero exit, empty DOM or timeout.

    Every render gets a fresh temporary ``--user-data-dir`` (never the operator's
    profile, never a running Chrome). Partial output is never returned.
    """
    with tempfile.TemporaryDirectory(
        prefix="render-check-profile-", ignore_cleanup_errors=True
    ) as profile:
        argv = render_argv(url, browser, Path(profile))
        try:
            proc = subprocess.run(argv, capture_output=True, timeout=RENDER_TIMEOUT_S, check=False)
        except subprocess.TimeoutExpired:
            _refuse(
                "render_timeout", f"render of {url} exceeded {RENDER_TIMEOUT_S}s ({browser.path})"
            )
        except OSError as exc:
            _refuse("render_launch_failed", f"could not launch {browser.path}: {exc}")
    dom = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace")[-500:]
        _refuse("render_failed", f"render of {url} exited {proc.returncode}: {stderr}")
    if not dom.strip():
        _refuse("render_empty", f"render of {url} produced an empty DOM")
    return dom


def visible_body(dom: str) -> str:
    """The rendered ``<body>`` markup with ``<script>``/``<style>`` payloads stripped.

    What remains is (a superset of) what the client sees. dc-runtime source text here
    means the deck rendered runtime JS as content (R1).
    """
    body = dom[dom.find("<body") :]
    body = re.sub(r"<script\b.*?</script[^>]*>", "", body, flags=re.S | re.I)
    return re.sub(r"<style\b.*?</style[^>]*>", "", body, flags=re.S | re.I)


# --- Assertions (FORK-S2 (d)) ---


def _local_sha256(address: str) -> str:
    return hashlib.sha256(address.partition("@")[0].encode()).hexdigest()


def assert_rendered_deck(visible: str, *, office_guid_sha256: str, clinic: str) -> None:
    """Assert a rendered deck's visible body is this clinic's, complete and uncorrupted.

    Pure. ``office_guid_sha256`` is the state manifest's digest (state never stores the
    full guid). Each failure raises :class:`RenderCheckRefused` with its own reason:

    * ``corruption_marker`` -- dc-runtime source is visible (R1);
    * ``routing_address_missing`` / ``routing_address_multiple`` -- the harvest (lowercased)
      is not exactly one address;
    * ``routing_address_foreign`` -- the one address's local part does not hash to
      ``office_guid_sha256``;
    * ``placeholder_token`` / ``empty_interp`` -- an unfilled field is visible;
    * ``clinic_missing`` -- ``Prepared for <span class="sc-interp">{clinic}</span>`` absent;
    * ``deck_stage_missing`` -- the deck never mounted.

    Messages mask addresses (first 8 hex + domain); a full address is never printed.
    """
    corruption = [m for m in RENDERED_CORRUPTION_MARKERS if m in visible]
    if corruption:
        _refuse(
            "corruption_marker", f"dc-runtime source visible in the rendered body: {corruption!r}"
        )

    addresses = sorted({a.lower() for a in CANONICAL_ROUTING_ADDR_RE.findall(visible)})
    if not addresses:
        _refuse("routing_address_missing", "rendered body shows no routing address")
    if len(addresses) > 1:
        _refuse(
            "routing_address_multiple",
            f"rendered body shows {len(addresses)} distinct routing addresses "
            f"{[_mask_addr(a) for a in addresses]} (expected exactly the clinic's own)",
        )
    if _local_sha256(addresses[0]) != office_guid_sha256.lower():
        _refuse(
            "routing_address_foreign",
            f"rendered routing address {_mask_addr(addresses[0])} is not this office's own "
            "(sha256 of its local part != office_guid_sha256)",
        )

    placeholders = [t for t in PLACEHOLDER_TOKENS if t in visible]
    if placeholders:
        _refuse("placeholder_token", f"unfilled placeholder(s) visible: {placeholders!r}")
    if _EMPTY_INTERP in visible:
        _refuse("empty_interp", f"empty interpolation visible: {_EMPTY_INTERP!r}")

    # quote=False: the DOM serializer escapes only & < > in text nodes, so an apostrophe
    # in a clinic name must not be compared as &#x27;.
    prepared = f'Prepared for <span class="sc-interp">{html.escape(clinic, quote=False)}</span>'
    if prepared not in visible:
        _refuse("clinic_missing", f"rendered body lacks {prepared!r}")
    if _DECK_STAGE not in visible:
        _refuse("deck_stage_missing", f"rendered body lacks {_DECK_STAGE!r} (deck did not mount)")


# --- Composition (produce + deploy gate) ---


@dataclasses.dataclass(frozen=True)
class RenderReceipt:
    """One rendered-deck check outcome, for the run log."""

    slug: str
    browser_path: str
    browser_kind: str
    browser_version: str
    checked_at: str  # iso8601 UTC
    outcome: str  # "pass", or "refused:<reason>"

    def line(self) -> str:
        return (
            f"RENDER-CHECK slug={self.slug} browser={self.browser_kind} "
            f"version={self.browser_version!r} path={self.browser_path!r} outcome={self.outcome}"
        )


def check_staged_deck(
    deploy_root: Path,
    slug: str,
    *,
    office_guid_sha256: str,
    clinic: str,
    browser: Browser | None = None,
) -> RenderReceipt:
    """Render ``<deploy_root>/<slug>/`` over localhost HTTP and assert it (D10(b)).

    ``browser`` defaults to :func:`require_browser`; pass one to reuse a resolution.

    Raises:
        BrowserUnavailable: no usable browser (stop and ask the operator).
        RenderCheckRefused: the render failed or the rendered deck failed an assertion.
    """
    browser = browser if browser is not None else require_browser()
    version = browser_version(browser)
    with serve_directory(deploy_root) as base:
        dom = render_dom(f"{base}/{slug}/", browser)
    assert_rendered_deck(visible_body(dom), office_guid_sha256=office_guid_sha256, clinic=clinic)
    receipt = RenderReceipt(
        slug=slug,
        browser_path=str(browser.path),
        browser_kind=browser.kind,
        browser_version=version,
        checked_at=datetime.now(UTC).isoformat(),
        outcome="pass",
    )
    logger.info("render_check_passed", **dataclasses.asdict(receipt))
    return receipt


class RenderGateRefused(RenderCheckRefused):
    """The deploy gate refused: carries every per-deck receipt checked before refusing."""

    def __init__(self, reason: str, message: str, receipts: Sequence[RenderReceipt]) -> None:
        super().__init__(reason, message)
        self.receipts = list(receipts)


def render_gate(deploy_base: Path, state_dir: Path) -> list[RenderReceipt]:
    """The deploy gate: every staged PRODUCED / DEPLOY_CONFIRMED deck must pass. No Asana.

    For each office in the state dir at PRODUCED or DEPLOY_CONFIRMED whose
    ``<deploy_base>/<slug>/index.html`` exists: its sha256 must equal the recorded
    ``frozen_sha256`` (else ``staged_sha_drift``), then :func:`check_staged_deck` runs with
    the state's digest and clinic. Every deck is checked (one refusal does not hide the
    rest); any refusal raises :class:`RenderGateRefused`, as does checking zero decks
    (nothing to deploy is not a pass). :class:`BrowserUnavailable` propagates at once.
    """
    gated = {Phase.PRODUCED, Phase.DEPLOY_CONFIRMED}
    receipts: list[RenderReceipt] = []
    refused: list[str] = []
    browser: Browser | None = None
    for state in StateStore(state_dir).all_offices():
        if state.phase not in gated:
            continue
        served = deploy_base / state.slug / "index.html"
        if not served.is_file():
            continue
        try:
            actual = hashlib.sha256(served.read_bytes()).hexdigest()
            if actual != state.frozen_sha256:
                _refuse(
                    "staged_sha_drift",
                    f"/{state.slug}/index.html sha256={actual} != frozen_sha256="
                    f"{state.frozen_sha256} (staged bytes are not the frozen deck)",
                )
            if browser is None:
                browser = require_browser()
            receipts.append(
                check_staged_deck(
                    deploy_base,
                    state.slug,
                    office_guid_sha256=state.office_guid_sha256,
                    clinic=state.clinic,
                    browser=browser,
                )
            )
        except BrowserUnavailable:
            raise
        except RenderCheckRefused as exc:
            refused.append(f"{state.slug}: {exc}")
            receipts.append(
                RenderReceipt(
                    slug=state.slug,
                    browser_path=str(browser.path) if browser else "",
                    browser_kind=browser.kind if browser else "",
                    browser_version=browser_version(browser) if browser else "",
                    checked_at=datetime.now(UTC).isoformat(),
                    outcome=f"refused:{exc.reason}",
                )
            )
    if refused:
        message = f"{len(refused)} of {len(receipts)} staged deck(s) refused: " + " | ".join(
            refused
        )
        logger.error(
            "render_gate_refused", reason="deck_refused", refused=len(refused), total=len(receipts)
        )
        raise RenderGateRefused("deck_refused", message, receipts)
    if not receipts:
        message = (
            f"zero staged decks checked (no PRODUCED/DEPLOY_CONFIRMED state in {state_dir} "
            f"has <slug>/index.html under {deploy_base}); nothing to deploy is not a pass"
        )
        logger.error("render_gate_refused", reason="zero_decks_checked", detail=message)
        raise RenderGateRefused("zero_decks_checked", message, receipts)
    return receipts


def main(argv: Sequence[str] | None = None) -> int:
    """CLI for the deploy gate. Exit 0 all passed / 1 refused / 2 no browser."""
    parser = argparse.ArgumentParser(
        prog="render_check",
        description="D10(b) rendered-deck deploy gate (fails closed, never skips).",
    )
    parser.add_argument("--deploy-base", required=True, type=Path, help="deck-host deploy root")
    parser.add_argument("--state-dir", required=True, type=Path, help="floodgates state dir")
    args = parser.parse_args(argv)
    deploy_base: Path = args.deploy_base.expanduser().resolve()
    state_dir: Path = args.state_dir.expanduser().resolve()
    try:
        receipts = render_gate(deploy_base, state_dir)
    except BrowserUnavailable as exc:
        sys.stderr.write(f"BROWSER-UNAVAILABLE: {exc}\nStop and ask the operator.\n")
        return 2
    except RenderGateRefused as exc:
        for receipt in exc.receipts:
            sys.stdout.write(receipt.line() + "\n")
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 1
    except RenderCheckRefused as exc:  # pragma: no cover - render_gate wraps per-deck refusals
        sys.stderr.write(f"REFUSED: {exc}\n")
        return 1
    for receipt in receipts:
        sys.stdout.write(receipt.line() + "\n")
    sys.stdout.write(f"RENDER-GATE PASS decks={len(receipts)}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
