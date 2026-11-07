"""Two-sided tests for the D10(b) rendered-deck check (``render_check``).

Design of record: FORK-S2 (pythia, 2026-11-07), "Two-sided tests".

* **Always-run legs** (no browser; these carry CI): the pure assertion on synthetic
  visible bodies (GREEN passes, every failure has its own reason code), the browser
  resolver order on temporary fake executables, the render argv, the render refusals
  driven by fake browsers, the localhost server headers, the deploy gate on a fake
  state dir, and the CLI exit codes.
* **Browser legs** (``requires_producer`` + ``requires_browser``): a real freeze staged
  into a temporary deploy root passes; three deliberately broken INPUTS refuse with
  their exact reason codes (a deck frozen with a foreign address, a foreign address
  assembled by the page's own script at runtime, the stale R1 corruptor).
  Discriminating-canary doctrine: every RED breaks the input, never the surface.

Synthetic identities only (this is a public repo): the spike GUID is "own", and
``FOREIGN_GUID`` is a made-up v4.
"""

from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import hashlib
import stat
import sys
import urllib.request
import uuid
from pathlib import Path

import pytest

from autom8_asana.automation.workflows.onboarding_walkthrough import (
    deck_manifests,
    host_bundle,
    render_check,
    tenant_binding,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.floodgates.state import (
    OfficeState,
    Phase,
    StateStore,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.producer import (
    freeze_walkthrough_deck,
)
from autom8_asana.automation.workflows.onboarding_walkthrough.render_check import (
    PLACEHOLDER_TOKENS,
    RENDERED_CORRUPTION_MARKERS,
    Browser,
    BrowserOverrideInvalid,
    BrowserUnavailable,
    RenderCheckRefused,
    RenderGateRefused,
    RenderReceipt,
    assert_rendered_deck,
    check_staged_deck,
    find_browser,
    render_argv,
    render_dom,
    render_gate,
    require_browser,
    serve_directory,
)
from tests.unit.automation.workflows.test_walkthrough_render_assert import (
    CLIENT_NAME,
    DECK_TEMPLATE,
    SPIKE_ADDRESS,
    _corrupt,
    _producer_available,
    _vendored_producer_dir,
    requires_browser,
    requires_producer,
)

SPIKE_GUID = SPIKE_ADDRESS.partition("@")[0]
OWN_SHA = hashlib.sha256(SPIKE_GUID.encode()).hexdigest()
FOREIGN_GUID = "0f0f0f0f-1111-4222-8333-444444444444"
FOREIGN_ADDRESS = f"{FOREIGN_GUID}@appointments.contenteapp.com"
FOREIGN_SHA = hashlib.sha256(FOREIGN_GUID.encode()).hexdigest()
SLUG = "0123456789abcdef0123456789abcdef"
SLUG_2 = "fedcba9876543210fedcba9876543210"


def _green_body(address: str = SPIKE_ADDRESS, clinic_markup: str = CLIENT_NAME) -> str:
    return (
        "<body><deck-stage>"
        f'<p>Prepared for <span class="sc-interp">{clinic_markup}</span></p>'
        f'<p>Forward to <a href="mailto:{address}">{address}</a></p>'
        "</deck-stage></body>"
    )


def _refusal(visible: str, *, sha: str = OWN_SHA, clinic: str = CLIENT_NAME) -> RenderCheckRefused:
    with pytest.raises(RenderCheckRefused) as info:
        assert_rendered_deck(visible, office_guid_sha256=sha, clinic=clinic)
    return info.value


# --- The pure assertion (always runs) ---


class TestAssertRenderedDeck:
    def test_green_passes(self) -> None:
        assert_rendered_deck(_green_body(), office_guid_sha256=OWN_SHA, clinic=CLIENT_NAME)

    def test_green_with_uppercase_own_address_passes(self) -> None:
        # The harvest is case-insensitive and lowercased: a case-variant of OWN is OWN.
        body = _green_body(address=f"{SPIKE_GUID.upper()}@appointments.contenteapp.com")
        assert_rendered_deck(body, office_guid_sha256=OWN_SHA, clinic=CLIENT_NAME)

    def test_clinic_with_ampersand_and_apostrophe_matches_dom_serialization(self) -> None:
        clinic = "Smith & Jones' Rehab"
        # The DOM serializer escapes & < > in text nodes but not quotes.
        body = _green_body(clinic_markup="Smith &amp; Jones' Rehab")
        assert_rendered_deck(body, office_guid_sha256=OWN_SHA, clinic=clinic)

    @pytest.mark.parametrize(
        ("visible", "reason"),
        [
            pytest.param(
                _green_body(address=FOREIGN_ADDRESS), "routing_address_foreign", id="foreign"
            ),
            pytest.param(
                _green_body() + f"<p>{FOREIGN_ADDRESS}</p>",
                "routing_address_multiple",
                id="two-addresses",
            ),
            pytest.param(
                _green_body() + f"<p>{FOREIGN_ADDRESS.upper()}</p>",
                "routing_address_multiple",
                id="two-addresses-uppercase-foreign",
            ),
            pytest.param(
                _green_body().replace(SPIKE_ADDRESS, "your clinic's address"),
                "routing_address_missing",
                id="zero-addresses",
            ),
            pytest.param(
                _green_body() + '<span class="sc-interp"></span>', "empty_interp", id="empty-interp"
            ),
            pytest.param(
                _green_body().replace("<deck-stage>", "<div>").replace("</deck-stage>", "</div>"),
                "deck_stage_missing",
                id="deck-stage-missing",
            ),
        ],
    )
    def test_each_failure_has_its_reason(self, visible: str, reason: str) -> None:
        assert _refusal(visible).reason == reason

    def test_wrong_clinic_refuses(self) -> None:
        assert _refusal(_green_body(), clinic="Another Synthetic Clinic").reason == "clinic_missing"

    def test_wrong_digest_refuses_as_foreign(self) -> None:
        # The SAME body is GREEN against its own digest (above) and RED against another.
        assert _refusal(_green_body(), sha=FOREIGN_SHA).reason == "routing_address_foreign"

    @pytest.mark.parametrize("token", PLACEHOLDER_TOKENS)
    def test_each_placeholder_token_refuses(self, token: str) -> None:
        assert _refusal(_green_body() + f"<p>{token}</p>").reason == "placeholder_token"

    @pytest.mark.parametrize("marker", RENDERED_CORRUPTION_MARKERS)
    def test_each_corruption_marker_refuses(self, marker: str) -> None:
        assert _refusal(_green_body() + f"<pre>{marker}</pre>").reason == "corruption_marker"

    @pytest.mark.parametrize(
        "visible",
        [
            _green_body(address=FOREIGN_ADDRESS),
            _green_body() + f"<p>{FOREIGN_ADDRESS}</p>",
        ],
        ids=["foreign", "two-addresses"],
    )
    def test_messages_mask_every_address(self, visible: str) -> None:
        message = str(_refusal(visible))
        assert FOREIGN_ADDRESS not in message
        assert SPIKE_ADDRESS not in message
        assert FOREIGN_GUID[:8] in message  # the masked breadcrumb is present


# --- Browser resolution (always runs, on fake executables) ---


def _fake_executable(path: Path, script: str = "echo 'Fake Chromium 1.0'") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


@pytest.fixture
def isolated_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Point every discovery source at empty temp dirs (nothing is found by default)."""
    home = tmp_path / "home"
    home.mkdir()
    sys_apps = tmp_path / "sys-applications"
    sys_apps.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    cache = tmp_path / "pw-cache"
    monkeypatch.delenv(render_check.BROWSER_OVERRIDE_ENV, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(cache))
    monkeypatch.setattr(render_check, "MACOS_SYSTEM_APPLICATIONS", sys_apps)
    return {"home": home, "sys_apps": sys_apps, "bin": bin_dir, "cache": cache, "tmp": tmp_path}


def _plant_cache(cache: Path, revision: int) -> Path:
    return _fake_executable(
        cache
        / f"chromium_headless_shell-{revision}"
        / "chrome-headless-shell-test"
        / "chrome-headless-shell"
    )


def _plant_installed(dirs: dict[str, Path]) -> Path:
    if sys.platform == "darwin":
        return _fake_executable(
            dirs["sys_apps"] / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome"
        )
    return _fake_executable(dirs["bin"] / "google-chrome")


class TestFindBrowser:
    def test_override_beats_cache_and_installed(
        self, isolated_discovery: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _plant_cache(isolated_discovery["cache"], 1200)
        _plant_installed(isolated_discovery)
        override = _fake_executable(
            isolated_discovery["tmp"] / "override" / "chrome-headless-shell"
        )
        monkeypatch.setenv(render_check.BROWSER_OVERRIDE_ENV, str(override))
        assert find_browser() == Browser(path=override, kind="shell")

    def test_cache_beats_installed_newest_revision_first(
        self, isolated_discovery: dict[str, Path]
    ) -> None:
        _plant_cache(isolated_discovery["cache"], 999)
        newest = _plant_cache(isolated_discovery["cache"], 1200)  # numeric, not lexicographic
        _plant_installed(isolated_discovery)
        assert find_browser() == Browser(path=newest, kind="shell")

    def test_installed_found_when_nothing_else(self, isolated_discovery: dict[str, Path]) -> None:
        installed = _plant_installed(isolated_discovery)
        assert find_browser() == Browser(path=installed, kind="chrome")

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS ~/Applications branch")
    def test_user_applications_found_after_system(
        self, isolated_discovery: dict[str, Path]
    ) -> None:
        user = _fake_executable(
            isolated_discovery["home"]
            / "Applications"
            / "Chromium.app"
            / "Contents"
            / "MacOS"
            / "Chromium"
        )
        assert find_browser() == Browser(path=user, kind="chrome")

    @pytest.mark.parametrize("kind", ["missing", "not-executable", "directory", "empty"])
    def test_invalid_override_raises_never_falls_through(
        self, kind: str, isolated_discovery: dict[str, Path], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Planted control: a usable cache AND installed browser exist, yet a bad override refuses."""
        _plant_cache(isolated_discovery["cache"], 1200)
        _plant_installed(isolated_discovery)
        target = isolated_discovery["tmp"] / "bad-override"
        if kind == "not-executable":
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o644)
        elif kind == "directory":
            target.mkdir()
        value = "" if kind == "empty" else str(target)
        monkeypatch.setenv(render_check.BROWSER_OVERRIDE_ENV, value)
        with pytest.raises(BrowserOverrideInvalid) as info:
            find_browser()
        assert info.value.reason == "browser_override_invalid"
        # It is also a BrowserUnavailable, so the CLI maps it to "stop and ask" (exit 2).
        assert isinstance(info.value, BrowserUnavailable)

    def test_nothing_found_returns_none(self, isolated_discovery: dict[str, Path]) -> None:
        assert find_browser() is None

    def test_refuses_not_skips(self, isolated_discovery: dict[str, Path]) -> None:
        """With no browser anywhere, the runtime path REFUSES; it never skips or downloads."""
        with pytest.raises(BrowserUnavailable) as info:
            require_browser()
        message = str(info.value)
        assert info.value.reason == "browser_unavailable"
        assert render_check.BROWSER_OVERRIDE_ENV in message
        assert str(isolated_discovery["cache"]) in message
        assert "Stop and ask the operator" in message
        if sys.platform == "darwin":
            assert str(isolated_discovery["sys_apps"] / "Google Chrome.app") in message
            assert str(isolated_discovery["home"] / "Applications") in message
        else:
            assert "google-chrome" in message

    def test_check_staged_deck_refuses_without_browser(
        self, isolated_discovery: dict[str, Path], tmp_path: Path
    ) -> None:
        with pytest.raises(BrowserUnavailable):
            check_staged_deck(tmp_path, SLUG, office_guid_sha256=OWN_SHA, clinic=CLIENT_NAME)


# --- argv and render refusals (always run) ---


class TestRenderArgv:
    @pytest.mark.parametrize(
        ("kind", "flag"), [("shell", "--headless"), ("chrome", "--headless=new")]
    )
    def test_headless_flag_per_kind_and_fresh_profile(
        self, kind: str, flag: str, tmp_path: Path
    ) -> None:
        browser = Browser(path=Path("/opt/browser/bin"), kind=kind)  # type: ignore[arg-type]
        argv = render_argv("http://127.0.0.1:1/x/", browser, tmp_path / "profile")
        assert argv[0] == "/opt/browser/bin"
        assert argv[-1] == "http://127.0.0.1:1/x/"
        assert [a for a in argv if a.startswith("--headless")] == [flag]
        assert f"--user-data-dir={tmp_path / 'profile'}" in argv
        for required in (
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=8000",
            "--timeout=15000",
            "--dump-dom",
        ):
            assert required in argv

    @pytest.mark.parametrize("kind", ["shell", "chrome"])
    def test_keychain_flags_always_present(self, kind: str, tmp_path: Path) -> None:
        """macOS: no "Chrome Safe Storage" keychain request on any launch, either kind."""
        browser = Browser(path=Path("/opt/browser/bin"), kind=kind)  # type: ignore[arg-type]
        argv = render_argv("http://127.0.0.1:1/x/", browser, tmp_path / "profile")
        assert "--use-mock-keychain" in argv
        assert "--password-store=basic" in argv
        assert render_check.KEYCHAIN_FLAGS == ("--use-mock-keychain", "--password-store=basic")

    def test_version_probe_carries_keychain_flags(self, tmp_path: Path) -> None:
        log = tmp_path / "version-argv.log"
        fake = _fake_executable(
            tmp_path / "chrome-v", f'echo "$@" > "{log}"\necho "Fake Chromium 9.9"'
        )
        assert (
            render_check.browser_version(Browser(path=fake, kind="chrome")) == "Fake Chromium 9.9"
        )
        args = log.read_text(encoding="utf-8").split()
        assert args == ["--use-mock-keychain", "--password-store=basic", "--version"]

    def test_render_dom_invocation_carries_keychain_flags(self, tmp_path: Path) -> None:
        log = tmp_path / "render-argv.log"
        fake = _fake_executable(
            tmp_path / "chrome-r", f'echo "$@" > "{log}"\necho "<html><body>ok</body></html>"'
        )
        render_dom("http://127.0.0.1:1/a/", Browser(path=fake, kind="shell"))
        args = log.read_text(encoding="utf-8").split()
        assert "--use-mock-keychain" in args and "--password-store=basic" in args

    def test_render_dom_uses_a_fresh_profile_each_time(self, tmp_path: Path) -> None:
        log = tmp_path / "argv.log"
        fake = _fake_executable(
            tmp_path / "chrome",
            f'echo "$@" >> "{log}"\necho "<html><body>ok</body></html>"',
        )
        browser = Browser(path=fake, kind="chrome")
        assert "ok" in render_dom("http://127.0.0.1:1/a/", browser)
        assert "ok" in render_dom("http://127.0.0.1:1/b/", browser)
        profiles = [
            next(a for a in line.split() if a.startswith("--user-data-dir="))
            for line in log.read_text(encoding="utf-8").splitlines()
        ]
        assert len(profiles) == 2 and profiles[0] != profiles[1]
        for profile in profiles:
            assert not Path(profile.partition("=")[2]).exists()  # removed after the render

    @pytest.mark.parametrize(
        ("script", "reason"),
        [
            ('echo "<html><body>partial</body></html>"; exit 3', "render_failed"),
            ("exit 0", "render_empty"),
        ],
        ids=["non-zero-exit", "empty-dom"],
    )
    def test_render_refusals(self, script: str, reason: str, tmp_path: Path) -> None:
        browser = Browser(path=_fake_executable(tmp_path / "chrome", script), kind="chrome")
        with pytest.raises(RenderCheckRefused) as info:
            render_dom("http://127.0.0.1:1/", browser)
        assert info.value.reason == reason

    def test_render_timeout_refuses(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(render_check, "RENDER_TIMEOUT_S", 1)
        browser = Browser(path=_fake_executable(tmp_path / "chrome", "exec sleep 5"), kind="chrome")
        with pytest.raises(RenderCheckRefused) as info:
            render_dom("http://127.0.0.1:1/", browser)
        assert info.value.reason == "render_timeout"


class TestServeDirectory:
    def test_sends_host_headers_and_serves_slug_index(self, tmp_path: Path) -> None:
        (tmp_path / SLUG).mkdir()
        (tmp_path / SLUG / "index.html").write_bytes(b"<html><body>deck</body></html>")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with serve_directory(tmp_path) as base:
            assert base.startswith("http://127.0.0.1:")
            with opener.open(f"{base}/{SLUG}/", timeout=10) as resp:
                assert resp.status == 200
                assert resp.headers["Cache-Control"] == "no-store"
                assert resp.headers["X-Robots-Tag"] == "noindex, nofollow"
                assert resp.headers["Referrer-Policy"] == "no-referrer"
                assert resp.headers["X-Content-Type-Options"] == "nosniff"
                assert resp.read() == b"<html><body>deck</body></html>"


# --- The deploy gate (always runs; check_staged_deck faked) ---


def _office(
    play_gid: str, slug: str, frozen_sha256: str, phase: Phase, *, sha: str = OWN_SHA
) -> OfficeState:
    return OfficeState(
        play_gid=play_gid,
        office_guid_masked=f"{SPIKE_GUID[:8]}…",
        office_guid_sha256=sha,
        clinic=CLIENT_NAME,
        slug=slug,
        deck_url=f"https://decks.example.invalid/{slug}/",
        frozen_sha256=frozen_sha256,
        phase=phase,
        posts={"link": None, "template": None, "card": None},
        updated_at="2026-11-07T00:00:00+00:00",
    )


def _stage(root: Path, slug: str, data: bytes) -> str:
    (root / slug).mkdir(parents=True, exist_ok=True)
    (root / slug / "index.html").write_bytes(data)
    return hashlib.sha256(data).hexdigest()


@dataclasses.dataclass
class GateCtx:
    deploy: Path
    state_dir: Path
    calls: list[dict[str, object]]
    failing: set[str]

    @property
    def store(self) -> StateStore:
        return StateStore(self.state_dir)


@pytest.fixture
def gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GateCtx:
    ctx = GateCtx(deploy=tmp_path / "public", state_dir=tmp_path / "state", calls=[], failing=set())
    ctx.deploy.mkdir()
    fake_browser = Browser(path=Path("/fake/chrome"), kind="chrome")

    def fake_check(deploy_root: Path, slug: str, **kwargs: object) -> RenderReceipt:
        ctx.calls.append({"deploy_root": deploy_root, "slug": slug, **kwargs})
        if slug in ctx.failing:
            raise RenderCheckRefused("routing_address_foreign", "synthetic refusal")
        return RenderReceipt(
            slug, "/fake/chrome", "chrome", "Fake 1", "2026-11-07T00:00:00+00:00", "pass"
        )

    monkeypatch.setattr(render_check, "check_staged_deck", fake_check)
    monkeypatch.setattr(render_check, "require_browser", lambda: fake_browser)
    monkeypatch.setattr(render_check, "browser_version", lambda browser: "Fake 1")
    return ctx


class TestRenderGate:
    def test_produced_and_deploy_confirmed_decks_are_checked(self, gate: GateCtx) -> None:
        d = gate.deploy
        gate.store.save(_office("1001", SLUG, _stage(d, SLUG, b"deck-1"), Phase.PRODUCED))
        gate.store.save(
            _office("1002", SLUG_2, _stage(d, SLUG_2, b"deck-2"), Phase.DEPLOY_CONFIRMED)
        )
        receipts = render_gate(d, gate.state_dir)
        assert [r.slug for r in receipts] == [SLUG, SLUG_2]
        assert [c["slug"] for c in gate.calls] == [SLUG, SLUG_2]
        assert all(c["deploy_root"] == d for c in gate.calls)
        assert all(
            c["office_guid_sha256"] == OWN_SHA and c["clinic"] == CLIENT_NAME for c in gate.calls
        )

    def test_other_phases_and_unstaged_decks_are_not_checked(self, gate: GateCtx) -> None:
        d = gate.deploy
        gate.store.save(_office("1001", SLUG, _stage(d, SLUG, b"deck-1"), Phase.PRODUCED))
        gate.store.save(_office("1002", SLUG_2, _stage(d, SLUG_2, b"deck-2"), Phase.DONE))
        gate.store.save(_office("1003", "ab" * 16, "0" * 64, Phase.PRODUCED))  # not staged here
        gate.store.save(_office("1004", "cd" * 16, "0" * 64, Phase.PENDING))
        receipts = render_gate(d, gate.state_dir)
        assert [r.slug for r in receipts] == [SLUG]

    def test_drifted_staged_sha_refuses_without_rendering(self, gate: GateCtx) -> None:
        d = gate.deploy
        frozen_sha = _stage(d, SLUG, b"frozen deck")
        (d / SLUG / "index.html").write_bytes(b"edited after freeze")
        gate.store.save(_office("1001", SLUG, frozen_sha, Phase.PRODUCED))
        with pytest.raises(RenderGateRefused) as info:
            render_gate(d, gate.state_dir)
        assert info.value.reason == "deck_refused"
        assert [r.outcome for r in info.value.receipts] == ["refused:staged_sha_drift"]
        assert gate.calls == []

    def test_one_refusal_refuses_the_gate_but_every_deck_is_checked(self, gate: GateCtx) -> None:
        d = gate.deploy
        gate.store.save(_office("1001", SLUG, _stage(d, SLUG, b"deck-1"), Phase.PRODUCED))
        gate.store.save(_office("1002", SLUG_2, _stage(d, SLUG_2, b"deck-2"), Phase.PRODUCED))
        gate.failing.add(SLUG)
        with pytest.raises(RenderGateRefused) as info:
            render_gate(d, gate.state_dir)
        assert [r.outcome for r in info.value.receipts] == [
            "refused:routing_address_foreign",
            "pass",
        ]
        assert info.value.receipts[0].browser_version == "Fake 1"

    def test_zero_decks_checked_refuses(self, gate: GateCtx) -> None:
        with pytest.raises(RenderGateRefused) as info:
            render_gate(gate.deploy, gate.state_dir)
        assert info.value.reason == "zero_decks_checked"

    def test_browser_unavailable_propagates(
        self, gate: GateCtx, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        d = gate.deploy
        gate.store.save(_office("1001", SLUG, _stage(d, SLUG, b"deck-1"), Phase.PRODUCED))

        def no_browser() -> Browser:
            raise BrowserUnavailable("browser_unavailable", "synthetic")

        monkeypatch.setattr(render_check, "require_browser", no_browser)
        with pytest.raises(BrowserUnavailable):
            render_gate(d, gate.state_dir)


# --- CLI exit codes (always run) ---


class TestMain:
    def _receipt(self) -> RenderReceipt:
        return RenderReceipt(
            SLUG, "/fake/chrome", "chrome", "Fake 1", "2026-11-07T00:00:00+00:00", "pass"
        )

    def test_exit_0_when_every_deck_passed(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        seen: list[tuple[Path, Path]] = []

        def fake_gate(deploy_base: Path, state_dir: Path) -> list[RenderReceipt]:
            seen.append((deploy_base, state_dir))
            return [self._receipt()]

        monkeypatch.setattr(render_check, "render_gate", fake_gate)
        monkeypatch.chdir(tmp_path)
        assert render_check.main(["--deploy-base", "public", "--state-dir", "state"]) == 0
        assert seen == [((tmp_path / "public").resolve(), (tmp_path / "state").resolve())]
        out = capsys.readouterr().out
        assert f"slug={SLUG} browser=chrome version='Fake 1'" in out
        assert "outcome=pass" in out
        assert "RENDER-GATE PASS decks=1" in out

    def test_exit_1_on_refusal(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        refused = RenderReceipt(
            SLUG, "/fake/chrome", "chrome", "Fake 1", "t", "refused:corruption_marker"
        )

        def fake_gate(deploy_base: Path, state_dir: Path) -> list[RenderReceipt]:
            raise RenderGateRefused("deck_refused", "synthetic", [refused])

        monkeypatch.setattr(render_check, "render_gate", fake_gate)
        assert render_check.main(["--deploy-base", "/x", "--state-dir", "/y"]) == 1
        captured = capsys.readouterr()
        assert "outcome=refused:corruption_marker" in captured.out
        assert "REFUSED" in captured.err

    def test_exit_1_on_zero_decks_unfaked(self, tmp_path: Path) -> None:
        (tmp_path / "public").mkdir()
        argv = ["--deploy-base", str(tmp_path / "public"), "--state-dir", str(tmp_path / "state")]
        assert render_check.main(argv) == 1

    def test_exit_2_on_browser_unavailable(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def fake_gate(deploy_base: Path, state_dir: Path) -> list[RenderReceipt]:
            raise BrowserUnavailable("browser_unavailable", "synthetic")

        monkeypatch.setattr(render_check, "render_gate", fake_gate)
        assert render_check.main(["--deploy-base", "/x", "--state-dir", "/y"]) == 2
        assert "Stop and ask the operator" in capsys.readouterr().err


# --- Browser legs: real freeze, real render (requires_producer + requires_browser) ---


def _freeze(gated_address: str) -> bytes:
    if not _producer_available():  # pragma: no cover - mirrored by skip markers
        pytest.skip("vendored Node producer not available")
    pdir = _vendored_producer_dir()
    out_filename = f"render-check-{uuid.uuid4().hex}.html"
    frozen = asyncio.run(
        freeze_walkthrough_deck(
            producer_dir=pdir,
            deck_template=DECK_TEMPLATE,
            gated_address=gated_address,
            client_name=CLIENT_NAME,
            title=deck_manifests.load_title(DECK_TEMPLATE),
            out_filename=out_filename,
        )
    )
    with contextlib.suppress(OSError):
        (pdir / "export" / out_filename).unlink()
    return frozen


@pytest.fixture(scope="module")
def own_frozen() -> bytes:
    return _freeze(SPIKE_ADDRESS)


@pytest.fixture(scope="module")
def foreign_frozen() -> bytes:
    return _freeze(FOREIGN_ADDRESS)


def _stage_real(tmp_path: Path, frozen: bytes) -> Path:
    """Stage through the real host_bundle staging (writes _headers + <slug>/index.html)."""
    artifact = tmp_path / "artifact.html"
    artifact.write_bytes(frozen)
    deploy_root = tmp_path / "public"
    host_bundle.stage_deck_bundle(
        deck_template=DECK_TEMPLATE, frozen_artifact=artifact, slug=SLUG, deploy_root=deploy_root
    )
    return deploy_root


def _runtime_assembled_foreign(frozen: bytes) -> bytes:
    """Inject a script that writes a foreign address, joined from two halves, into the body.

    No canonical address exists in the bytes for the injected one (the halves are each
    too short), so the static tenant-binding oracle cannot see it.
    """
    head, tail = FOREIGN_ADDRESS[:24], FOREIGN_ADDRESS[24:]
    script = (
        "<script>setTimeout(function(){var p=document.createElement('p');"
        f"p.textContent='{head}'+'{tail}';document.body.appendChild(p);}},0);</script>"
    ).encode()
    idx = frozen.rfind(b"</body>")
    assert idx != -1, "frozen deck has no </body>; update the runtime-assembly fixture"
    return frozen[:idx] + script + frozen[idx:]


@requires_producer
@requires_browser
class TestStagedDeckRenderCheck:
    def test_green_real_freeze_passes_with_receipt(self, own_frozen: bytes, tmp_path: Path) -> None:
        deploy_root = _stage_real(tmp_path, own_frozen)
        receipt = check_staged_deck(
            deploy_root, SLUG, office_guid_sha256=OWN_SHA, clinic=CLIENT_NAME
        )
        browser = find_browser()
        assert browser is not None
        assert receipt.outcome == "pass"
        assert receipt.slug == SLUG
        assert receipt.browser_path == str(browser.path)
        assert receipt.browser_kind == browser.kind
        assert receipt.browser_version and not receipt.browser_version.startswith("unknown")

    def test_red_deck_frozen_with_foreign_address(
        self, foreign_frozen: bytes, tmp_path: Path
    ) -> None:
        deploy_root = _stage_real(tmp_path, foreign_frozen)
        with pytest.raises(RenderCheckRefused) as info:
            check_staged_deck(deploy_root, SLUG, office_guid_sha256=OWN_SHA, clinic=CLIENT_NAME)
        assert info.value.reason == "routing_address_foreign"
        assert FOREIGN_ADDRESS not in str(info.value)
        # Two-sided: the same deck is GREEN for the office it was actually frozen for.
        check_staged_deck(deploy_root, SLUG, office_guid_sha256=FOREIGN_SHA, clinic=CLIENT_NAME)

    def test_red_runtime_assembled_foreign_address(self, own_frozen: bytes, tmp_path: Path) -> None:
        tampered = _runtime_assembled_foreign(own_frozen)
        # The static oracle on the bytes passes: it cannot see a runtime-assembled address.
        tenant_binding.assert_exclusive_tenant_binding(frozen=tampered, gated_address=SPIKE_ADDRESS)
        deploy_root = _stage_real(tmp_path, tampered)
        with pytest.raises(RenderCheckRefused) as info:
            check_staged_deck(deploy_root, SLUG, office_guid_sha256=OWN_SHA, clinic=CLIENT_NAME)
        assert info.value.reason == "routing_address_multiple"
        assert FOREIGN_ADDRESS not in str(info.value)

    def test_red_stale_corruptor(self, own_frozen: bytes, tmp_path: Path) -> None:
        deploy_root = _stage_real(tmp_path, _corrupt(own_frozen))
        with pytest.raises(RenderCheckRefused) as info:
            check_staged_deck(deploy_root, SLUG, office_guid_sha256=OWN_SHA, clinic=CLIENT_NAME)
        assert info.value.reason == "corruption_marker"

    def test_gate_cli_end_to_end_logs_a_receipt(
        self, own_frozen: bytes, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        deploy_root = _stage_real(tmp_path, own_frozen)
        state_dir = tmp_path / "state"
        StateStore(state_dir).save(
            _office("1001", SLUG, hashlib.sha256(own_frozen).hexdigest(), Phase.PRODUCED)
        )
        code = render_check.main(["--deploy-base", str(deploy_root), "--state-dir", str(state_dir)])
        out = capsys.readouterr().out
        assert code == 0, out
        assert f"RENDER-CHECK slug={SLUG}" in out and "outcome=pass" in out
        browser = find_browser()
        assert browser is not None and f"browser={browser.kind}" in out
