/**
 * acceptance.mjs — THE objective live-browser offline instrument (TDD §5, PKG-002).
 *
 * This is the load-bearing receipt. The static-analysis N3 GO was FALSIFIED by a
 * rite-disjoint critic precisely because static offset-checks were structurally
 * BLIND to the `$&`/`</script>` premature-close bug — only LIVE EXECUTION caught
 * it (N3-spike.md:379). So realization is proven ONLY by a live headless-browser
 * offline render, never by a green build log or a static scan.
 *
 * For each emitted deck it loads file://…?addr=<valid-email>&client=<name> under
 * Playwright with the browser context set OFFLINE (network physically denied) and
 * asserts AC-G1..G9:
 *
 *   AC-G1  ZERO external (non file:/data:/blob:) requests in hard-offline
 *   AC-G2  window.React=18.3.1, window.ReactDOM defined, body rendered (not source)
 *   AC-G3  all slides built — via the deck's OWN live DOM model ([data-deck-slide])
 *   AC-G4  CopyField click → clipboard readback matches the field value
 *   AC-G5  ?addr (valid contenteapp.com email) + ?client reflected in the DOM
 *   AC-G6  ZERO page errors
 *   AC-G7  golden sha256 determinism — build twice, hashes MATCH
 *   AC-G8  measured weight < 10 MB ideal / < 25 MB hard (measured, not projected)
 *   AC-G9  deliberately-broken fixture fires RED against the REAL build (EXIT 1,
 *          named error, NO output) — missing screenshot AND mutated namespace
 *
 * Exit non-zero if ANY assertion fails (the gate). This harness is run
 * rite-disjointly by qa-adversary; the build author does NOT grade STRONG here.
 */

import { execFileSync } from 'node:child_process';
import {
  readFileSync, writeFileSync, mkdirSync, rmSync, existsSync, cpSync, readdirSync,
  mkdtempSync, chmodSync,
} from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';

import { installRoutingCliShim } from './lib/routing-cli-shim.mjs';
import { gatedAddressForGuid } from '../lib/resolve-routing-address.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..', '..');
const INLINE = join(PROJECT_ROOT, 'build', 'inline.mjs');
const EXPORT_DIR = join(PROJECT_ROOT, 'export');
// Throwaway scratch dir for AC-G9 fixture residue. MUST NOT be the tracked
// `fixtures/` dir — `rmSync(FIXTURES)` below would delete the committed
// fixtures/README.md (the AC-G9 contract doc) on every run, dirtying the tree.
// `.fixtures-tmp/` is gitignored (see project/.gitignore) so it never stages.
const FIXTURES = join(__dirname, '.fixtures-tmp');

// MC-1 (S2) TIGHTENED the deck's okAddr regex from host-permissive
// /^[^\s@]+@[^\s@]*contenteapp\.com$/i to exact-host + canonical-UUIDv4:
//   /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}@appointments\.contenteapp\.com$/
// (mirror of the autom8y-core format_routing_address output). The old
// VALID_ADDR ('bookings.acmeclinic@contenteapp.com') NO LONGER personalizes —
// it is not a UUIDv4@appointments local-part (UV-P-2). VALID_ADDR moves to the
// canonical gated address in lockstep with MC-1.
//
// KNOWN_GUID is the #719 gate's own docstring example
// (feat/sdk-routing-address-formatter:.../helpers/routing.py). EXPECTED_ADDR is
// its deterministic gated output. We do NOT hardcode-derive EXPECTED_ADDR by
// string concat at use sites — it IS the gate's pure output for KNOWN_GUID.
const KNOWN_GUID = 'b167331c-536f-4996-9b2d-2f696f35f556';
const EXPECTED_ADDR = 'b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com';
const VALID_ADDR = EXPECTED_ADDR;
const CLIENT = 'AcmeClinic';

// A deliberately NON-canonical GUID (AC-G5'' fail-closed fixture). The gate
// RAISES on this; the producer must refuse to freeze it (ADDR-NON-CANONICAL).
const KNOWN_BAD_GUID = 'not-a-uuid';

// The two per-deck fallback placeholders. Neither is a canonical address (by
// design — a fallback is the NOT-personalized branch and must never masquerade
// as personalized). Used to assert ABSENCE in the personalized render.
const FALLBACK_EMAIL = 'xxxx-xxxx@appointments.contenteapp.com';
const FALLBACK_GHL = 'appointments+clinic@contenteapp.com';

const DECKS = [
  { deck: 'templates/ghl-calendar-setup', title: 'GHL Calendar Setup — Contente', out: 'GhlCalendarSetup.html', slides: 23 },
  { deck: 'templates/email-forwarding-setup', title: 'Email Forwarding Setup — Contente', out: 'EmailForwardingSetup.html', slides: 15 },
];

let failures = 0;
const log = (s) => console.log(s);
const pass = (id, msg) => log(`  [${id}] PASS — ${msg}`);
const fail = (id, msg) => { log(`  [${id}] FAIL — ${msg}`); failures++; };

function buildDeck(d, extraArgs = []) {
  return execFileSync(
    'node',
    [INLINE, '--deck', d.deck, '--title', d.title, '--out', d.out, ...extraArgs],
    { cwd: PROJECT_ROOT, encoding: 'utf8' }
  );
}

function sha256File(p) {
  return createHash('sha256').update(readFileSync(p)).digest('hex');
}

/**
 * AC-G7 — golden determinism: build the deck twice, hashes MUST match.
 */
function checkDeterminism(d) {
  buildDeck(d);
  const h1 = sha256File(join(EXPORT_DIR, d.out));
  buildDeck(d);
  const h2 = sha256File(join(EXPORT_DIR, d.out));
  if (h1 === h2) pass('AC-G7', `${d.out} deterministic sha256 ${h1.slice(0, 16)}… (2 runs match)`);
  else fail('AC-G7', `${d.out} NON-deterministic: ${h1} != ${h2}`);
  return h1;
}

/**
 * AC-G1..G6,G8 — the live offline render against one emitted deck.
 */
async function checkLiveOffline(d) {
  const outPath = join(EXPORT_DIR, d.out);
  const bytes = readFileSync(outPath).length;

  // AC-G8 — measured weight.
  const mb = bytes / 1024 / 1024;
  if (bytes <= 25 * 1024 * 1024) {
    pass('AC-G8', `${d.out} ${mb.toFixed(2)} MB (<25 MB hard${bytes <= 10 * 1024 * 1024 ? ', <10 MB ideal' : ', >10 MB ideal'})`);
  } else {
    fail('AC-G8', `${d.out} ${mb.toFixed(2)} MB exceeds 25 MB hard gate`);
  }

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'] });
  await context.setOffline(true); // HARD OFFLINE — non file:/data:/blob: requests fail

  const externalRequests = [];
  context.on('request', (req) => {
    const url = req.url();
    if (!url.startsWith('file:') && !url.startsWith('data:') && !url.startsWith('blob:')) {
      externalRequests.push(`${req.method()} ${url}`);
    }
  });

  const pageErrors = [];
  const page = await context.newPage();
  page.on('pageerror', (e) => pageErrors.push(e.message));

  const fileUrl = `file://${outPath}?addr=${encodeURIComponent(VALID_ADDR)}&client=${encodeURIComponent(CLIENT)}`;
  try {
    await page.goto(fileUrl, { waitUntil: 'load', timeout: 30000 });
  } catch (e) {
    // networkidle/load may settle oddly offline; proceed to assertions regardless.
    log(`    [nav note] ${e.message.split('\n')[0]}`);
  }
  await page.waitForTimeout(2500); // let React mount + deck-stage collect slides

  // AC-G1 — zero external requests.
  if (externalRequests.length === 0) pass('AC-G1', `${d.out}: 0 external requests (hard-offline)`);
  else fail('AC-G1', `${d.out}: ${externalRequests.length} external requests: ${externalRequests.slice(0, 5).join(' | ')}`);

  // AC-G2 — React mounted with rendered content.
  const reactState = await page.evaluate(() => ({
    react: typeof window.React !== 'undefined',
    reactDom: typeof window.ReactDOM !== 'undefined',
    version: window.React ? window.React.version : null,
    bodyHtmlLen: document.body ? document.body.innerHTML.length : 0,
  }));
  if (reactState.react && reactState.reactDom && reactState.version === '18.3.1' && reactState.bodyHtmlLen > 10000) {
    pass('AC-G2', `${d.out}: React ${reactState.version} mounted, body ${reactState.bodyHtmlLen} chars rendered`);
  } else {
    fail('AC-G2', `${d.out}: React=${reactState.react} ReactDOM=${reactState.reactDom} ver=${reactState.version} bodyLen=${reactState.bodyHtmlLen}`);
  }

  // AC-G3 — all slides built via the deck's OWN live DOM model.
  // deck-stage._collectSlides() stamps data-deck-slide="N" on each rendered slide
  // (probed: deck-stage.js:1117). This is the deck's model, not a [class*=slide]
  // selector (the spike's selector returned 0 — N3-spike.md:474).
  const slideCount = await page.evaluate(() => document.querySelectorAll('[data-deck-slide]').length);
  if (slideCount === d.slides) pass('AC-G3', `${d.out}: ${slideCount}/${d.slides} slides built (data-deck-slide DOM model)`);
  else fail('AC-G3', `${d.out}: ${slideCount} slides built, expected ${d.slides}`);

  // AC-G4 — CopyField clipboard readback. Find a Copy button, read its sibling
  // value span, click, read clipboard back.
  const copyResult = await page.evaluate(async () => {
    const btns = [...document.querySelectorAll('button')].filter((b) => /^\s*Copy\s*$/i.test(b.textContent || ''));
    if (btns.length === 0) return { ok: false, reason: 'no Copy button found' };
    const btn = btns[0];
    // The value span is the flex:1 sibling within the same field row.
    const row = btn.parentElement;
    const valueSpan = row ? row.querySelector('span') : null;
    const expected = valueSpan ? (valueSpan.textContent || '').trim() : '';
    btn.click();
    await new Promise((r) => setTimeout(r, 300));
    let readback = '';
    try { readback = await navigator.clipboard.readText(); } catch (e) { readback = `__readText_threw:${e.message}`; }
    return { ok: expected.length > 0 && readback === expected, expected, readback, count: btns.length };
  });
  if (copyResult.ok) pass('AC-G4', `${d.out}: CopyField copied "${copyResult.expected}" → clipboard readback matches (${copyResult.count} fields)`);
  else fail('AC-G4', `${d.out}: clipboard mismatch — expected "${copyResult.expected}", got "${copyResult.readback}" (${copyResult.reason || ''})`);

  // AC-G5 — personalization reflected in the DOM.
  // NOTE: the deck is a single-slide viewer, so body.innerText returns ONLY the
  // currently-VISIBLE slide's text — the personalized routing-address slide and
  // the "Prepared for" cover are usually NOT the active slide. We must inspect
  // the FULL rendered DOM (textContent / innerHTML), not visible innerText — this
  // is the spike's AC-G5 blind spot, fixed.
  //
  // The unique test addr only enters the DOM if the deck's okAddr regex
  // (/^[^\s@]+@[^\s@]*contenteapp\.com$/i) PASSED and routingAddress = rawAddr;
  // otherwise the deck renders its fallback address (probed distinct from
  // VALID_ADDR for both decks). So "unique addr present in DOM" UNIQUELY proves
  // the okAddr personalization path fired — the one path the spike's non-email
  // TEST-ADDR-123 never exercised. We also assert the fallback is ABSENT.
  // We scan the RENDERED DOM text only — explicitly EXCLUDING <script> source
  // (the `routingAddress = okAddr ? rawAddr : '<fallback>'` ternary embeds the
  // fallback literal in the inlined x-dc data <script>, so innerHTML always
  // contains it regardless of which branch executed). The RENDERED text (React
  // output in CopyField spans / cover headings) reflects only what actually ran.
  const FALLBACKS = ['appointments+clinic@contenteapp.com', 'xxxx-xxxx@appointments.contenteapp.com'];
  const personalization = await page.evaluate(({ addr, client, fallbacks }) => {
    // Collect rendered text from every element, skipping <script>/<style>.
    let rendered = '';
    const walk = (node) => {
      for (const child of node.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) { rendered += child.nodeValue || ''; continue; }
        if (child.nodeType !== Node.ELEMENT_NODE) continue;
        const tag = child.tagName;
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEMPLATE') continue;
        walk(child);
      }
    };
    if (document.body) walk(document.body);
    const fullHtml = document.body ? (document.body.innerHTML || '') : '';
    return {
      clientInDom: rendered.includes(client),
      addrInDom: rendered.includes(addr),
      fallbackPresent: fallbacks.some((f) => rendered.includes(f)),
      preparedForRendered: fullHtml.includes(`Prepared for ${client}`),
    };
  }, { addr: VALID_ADDR, client: CLIENT, fallbacks: FALLBACKS });
  if (personalization.clientInDom && personalization.addrInDom && !personalization.fallbackPresent) {
    pass('AC-G5', `${d.out}: ?client="${CLIENT}" reflected${personalization.preparedForRendered ? ' ("Prepared for ' + CLIENT + '" rendered)' : ''}; ?addr="${VALID_ADDR}" rendered (okAddr regex passed, fallback absent)`);
  } else {
    fail('AC-G5', `${d.out}: clientInDom=${personalization.clientInDom} addrInDom=${personalization.addrInDom} fallbackPresent=${personalization.fallbackPresent} preparedFor=${personalization.preparedForRendered}`);
  }

  // AC-G6 — zero page errors.
  if (pageErrors.length === 0) pass('AC-G6', `${d.out}: 0 page errors`);
  else fail('AC-G6', `${d.out}: ${pageErrors.length} page errors: ${pageErrors.slice(0, 3).join(' | ')}`);

  await browser.close();
}

/**
 * AC-G9 — the deliberately-broken fixture MUST fire RED against the REAL build.
 * We copy the GHL deck into fixtures/, mutate the @ds-bundle namespace in the
 * deck source AND remove a screenshot, then point the REAL inliner at it and
 * assert it EXITs non-zero with a named error and writes NO output file.
 */
function checkBrokenFixtureRed() {
  rmSync(FIXTURES, { recursive: true, force: true });
  mkdirSync(FIXTURES, { recursive: true });

  // Build a minimal fixture project: copy the GHL deck folder + project manifest
  // into a fixture deck under templates/_broken-fixture, then mutate it.
  const srcDeck = join(PROJECT_ROOT, 'templates', 'ghl-calendar-setup');
  const fxDeck = join(PROJECT_ROOT, 'templates', '_broken-fixture');
  rmSync(fxDeck, { recursive: true, force: true });
  cpSync(srcDeck, fxDeck, { recursive: true });

  const dcPath = join(fxDeck, readdirSync(fxDeck).find((f) => f.endsWith('.dc.html')));
  let dc = readFileSync(dcPath, 'utf8');

  // (1) Mutate the @ds-bundle namespace in the deck's consumer tags so it no
  //     longer agrees with the manifest → C-resolve NS-DRIFT-CONSUMER fires.
  dc = dc.split('ContenteDesignSystem_9ed584').join('ContenteDesignSystem_DEADBEEF');
  writeFileSync(dcPath, dc, 'utf8');

  // (2) Remove a screenshot the deck references → MISSING-ASSET fires.
  const fxAssets = join(fxDeck, 'assets');
  for (const f of readdirSync(fxAssets)) {
    if (/^image\d+\.(png|jpe?g)$/i.test(f)) { rmSync(join(fxAssets, f)); break; }
  }

  const fxOut = '_BrokenFixture.html';
  const fxOutPath = join(EXPORT_DIR, fxOut);
  rmSync(fxOutPath, { force: true });

  let exitCode = 0;
  let stderr = '';
  try {
    execFileSync('node', [INLINE, '--deck', 'templates/_broken-fixture', '--title', 'BROKEN', '--out', fxOut],
      { cwd: PROJECT_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    exitCode = e.status ?? 1;
    stderr = (e.stderr || '') + (e.stdout || '');
  }

  const wroteOutput = existsSync(fxOutPath);
  const named = /BUILD FAILED|RESOLVE-FAILED|NS-DRIFT|MISSING-ASSET|NAMESPACE/i.test(stderr);

  if (exitCode !== 0 && !wroteOutput && named) {
    pass('AC-G9', `broken fixture fired RED (exit ${exitCode}, named error, NO output written)`);
  } else {
    fail('AC-G9', `broken fixture did NOT fire correctly — exit=${exitCode} wroteOutput=${wroteOutput} named=${named}\n    stderr: ${stderr.slice(0, 400)}`);
  }

  // Clean up the fixture deck so it never lands in the committed tree.
  rmSync(fxDeck, { recursive: true, force: true });
  rmSync(fxOutPath, { force: true });
  rmSync(FIXTURES, { recursive: true, force: true });
}

/**
 * Open a built deck OFFLINE under Playwright and probe its OWN personalization
 * state from the rendered DOM (NOT from <script> source — the ternary embeds the
 * fallback literal in the inlined x-dc data <script>, so source always contains
 * it). Returns the address presence, fallback presence, and the deck's
 * personalized/not-personalized sc-if BRANCH state (the deck's own model).
 *
 * @param {string} outPath  absolute path to the built deck
 * @param {string} query    query string to open with (e.g. '' for the frozen
 *                           path with NO human ?addr; or '?addr=...' for live)
 * @returns {Promise<{addrInDom:boolean, fallbackPresent:boolean,
 *   personalizedBranch:boolean, notPersonalizedBranch:boolean,
 *   externalRequests:number, pageErrors:number}>}
 */
async function probePersonalization(outPath, query, addr, fallbacks) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ permissions: ['clipboard-read', 'clipboard-write'] });
  await context.setOffline(true); // HARD OFFLINE

  const externalRequests = [];
  context.on('request', (req) => {
    const url = req.url();
    if (!url.startsWith('file:') && !url.startsWith('data:') && !url.startsWith('blob:')) {
      externalRequests.push(`${req.method()} ${url}`);
    }
  });
  const pageErrors = [];
  const page = await context.newPage();
  page.on('pageerror', (e) => pageErrors.push(e.message));

  try {
    await page.goto(`file://${outPath}${query}`, { waitUntil: 'load', timeout: 30000 });
  } catch (e) {
    log(`    [nav note] ${e.message.split('\n')[0]}`);
  }
  await page.waitForTimeout(2500);

  const state = await page.evaluate(({ a, fbs }) => {
    let rendered = '';
    const walk = (node) => {
      for (const child of node.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) { rendered += child.nodeValue || ''; continue; }
        if (child.nodeType !== Node.ELEMENT_NODE) continue;
        const tag = child.tagName;
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEMPLATE') continue;
        walk(child);
      }
    };
    if (document.body) walk(document.body);
    // Deck-own personalization branch signals (the sc-if branch CONTENT):
    //  personalized  -> "This address is unique to you" / "This is your address"
    //  not-personalized -> "the one shown is only an example" / "We'll send you"
    const personalizedBranch =
      rendered.includes('This address is unique to you') ||
      rendered.includes('This is your address') ||
      rendered.includes('This is YOUR appointments address');
    const notPersonalizedBranch =
      rendered.includes('only an example') ||
      rendered.includes("We'll send you");
    return {
      addrInDom: a ? rendered.includes(a) : false,
      fallbackPresent: fbs.some((f) => rendered.includes(f)),
      personalizedBranch,
      notPersonalizedBranch,
    };
  }, { a: addr, fbs: fallbacks });

  await browser.close();
  return {
    ...state,
    externalRequests: externalRequests.length,
    pageErrors: pageErrors.length,
  };
}

/**
 * AC-G5' — render-then-freeze personalized proof (the S2 proven-of-component).
 * Build the deck via `--addr <EXPECTED_ADDR> --client`, open it OFFLINE with NO
 * ?addr query, and assert: EXPECTED_ADDR in rendered DOM, BOTH fallbacks ABSENT,
 * personalized branch rendered, not-personalized branch ABSENT, 0 external
 * requests. Proves the frozen-input path renders personalized===true with zero
 * human seam, fully offline.
 */
async function checkPersonalizedFreeze(d) {
  const out = `_personalized_${d.out}`;
  const outPath = join(EXPORT_DIR, out);
  rmSync(outPath, { force: true });
  buildDeck({ ...d, out }, ['--addr', EXPECTED_ADDR, '--client', CLIENT]);

  const fallbacks = [FALLBACK_EMAIL, FALLBACK_GHL];
  const s = await probePersonalization(outPath, '', EXPECTED_ADDR, fallbacks);

  const ok =
    s.addrInDom && !s.fallbackPresent &&
    s.personalizedBranch && !s.notPersonalizedBranch &&
    s.externalRequests === 0 && s.pageErrors === 0;
  if (ok) {
    pass("AC-G5'", `${d.out}: frozen gated ${EXPECTED_ADDR} renders personalized===true (NO ?addr query, fallbacks absent, ${s.externalRequests} external reqs)`);
  } else {
    fail("AC-G5'", `${d.out}: addrInDom=${s.addrInDom} fallbackPresent=${s.fallbackPresent} personalizedBranch=${s.personalizedBranch} notPersonalizedBranch=${s.notPersonalizedBranch} extReqs=${s.externalRequests} pageErrors=${s.pageErrors}`);
  }
  rmSync(outPath, { force: true });
}

/**
 * AC-CLIENT-BREAK (FINDING B) — a `--client` value carrying a `</script`-family
 * sequence MUST NOT break the <head> freeze seed. We build the deck with
 * `--client 'Acme--></script foo'` and a canonical --addr, then open it OFFLINE
 * with NO ?addr query and assert: the freeze still fires (EXPECTED_ADDR rendered,
 * personalized branch, fallbacks absent), ZERO page errors (the head freeze-script
 * did NOT die with `Invalid or unexpected token`), and ZERO external requests.
 * Before the fix, the un-escaped `</script ` prematurely closed the freeze script,
 * the seed never ran, and the deck rendered the un-personalized placeholder.
 */
async function checkClientScriptBreakFreeze(d) {
  const out = `_clientbreak_${d.out}`;
  const outPath = join(EXPORT_DIR, out);
  rmSync(outPath, { force: true });
  const HOSTILE_CLIENT = 'Acme--></script foo';
  // Build MUST succeed (the producer escapes the client literal; no LOUD failure).
  buildDeck({ ...d, out }, ['--addr', EXPECTED_ADDR, '--client', HOSTILE_CLIENT]);

  // Finding-B closure is proven AUTHORITATIVELY, not by a static HTML-tag regex (which
  // js/bad-tag-filter rightly flags as under-matching the `</script ...>` variants):
  //   1. the build SUCCEEDED — the producer escapes the client literal (escapeScriptContent)
  //      and asserts script-balance at build time (assertScriptBalance); and
  //   2. the LIVE browser renders with ZERO page errors below — a hostile `</script `-family
  //      seed would throw a parse error (pageErrors > 0) or drop personalization.
  // Those two guarantees are strictly stronger than a regex balance heuristic.
  const fallbacks = [FALLBACK_EMAIL, FALLBACK_GHL];
  const s = await probePersonalization(outPath, '', EXPECTED_ADDR, fallbacks);

  const ok =
    s.addrInDom && !s.fallbackPresent &&
    s.personalizedBranch && !s.notPersonalizedBranch &&
    s.externalRequests === 0 && s.pageErrors === 0;
  if (ok) {
    pass('AC-CLIENT-BREAK', `${d.out}: hostile --client "${HOSTILE_CLIENT}" does NOT break the freeze seed `
      + `(build succeeded + literal escaped; ${EXPECTED_ADDR} frozen+rendered, personalized===true, `
      + `${s.pageErrors} page errors, ${s.externalRequests} external reqs)`);
  } else {
    fail('AC-CLIENT-BREAK', `${d.out}: hostile --client broke the seed — `
      + `addrInDom=${s.addrInDom} fallbackPresent=${s.fallbackPresent} personalizedBranch=${s.personalizedBranch} `
      + `notPersonalizedBranch=${s.notPersonalizedBranch} extReqs=${s.externalRequests} pageErrors=${s.pageErrors}`);
  }
  rmSync(outPath, { force: true });
}

/**
 * Open a built deck OFFLINE and return its full RENDERED text (every TEXT node,
 * skipping <script>/<style>/<template>) plus error/request counters. The FAULT-13
 * legs assert on rendered CONTENT (the customer-visible plane), so they need the
 * raw text, not the boolean summary probePersonalization returns.
 */
async function probeRenderedText(outPath, query = '') {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  await context.setOffline(true); // HARD OFFLINE

  const externalRequests = [];
  context.on('request', (req) => {
    const url = req.url();
    if (!url.startsWith('file:') && !url.startsWith('data:') && !url.startsWith('blob:')) {
      externalRequests.push(`${req.method()} ${url}`);
    }
  });
  const pageErrors = [];
  const page = await context.newPage();
  page.on('pageerror', (e) => pageErrors.push(e.message));

  try {
    await page.goto(`file://${outPath}${query}`, { waitUntil: 'load', timeout: 30000 });
  } catch (e) {
    log(`    [nav note] ${e.message.split('\n')[0]}`);
  }
  await page.waitForTimeout(2500);

  const rendered = await page.evaluate(() => {
    let text = '';
    const walk = (node) => {
      for (const child of node.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) { text += child.nodeValue || ''; continue; }
        if (child.nodeType !== Node.ELEMENT_NODE) continue;
        const tag = child.tagName;
        if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEMPLATE') continue;
        walk(child);
      }
    };
    if (document.body) walk(document.body);
    return text;
  });

  await browser.close();
  return { rendered, externalRequests: externalRequests.length, pageErrors: pageErrors.length };
}

// The exact FAULT-13 live leak string: 65 UTF-16 code units — one past the old
// .slice(0, 64) cap, which rendered the cover as "…Vitality Medicine of New Yor"
// (silent mid-word amputation, no ellipsis) on the live attached deck.
const FAULT13_LIVE_CLIENT = 'PLAY: Custom Calendar Integration — Vitality Medicine of New York';

/**
 * AC-G5-LEN (FAULT-13b) — boundary-length triple 63/64/65 chars plus the literal
 * 65-char live leak string. Every fixture MUST survive the freeze->render seam
 * WHOLE: the rendered DOM must contain the exact --client value (wrap, never
 * silently truncate). RED on the pre-fix template: the 65-char fixtures lose
 * their final char to .slice(0, 64).
 */
async function checkClientLengthBoundaries(d) {
  const fixtures = [
    ['63ch', 'A'.repeat(59) + ' Cli'],           // 63 — below the old cap
    ['64ch', 'A'.repeat(59) + ' Clin'],          // 64 — exactly the old cap
    ['65ch', 'A'.repeat(59) + ' Clini'],         // 65 — one past the old cap
    ['live-65ch', FAULT13_LIVE_CLIENT],          // the exact live leak string
  ];
  for (const [tag, client] of fixtures) {
    const out = `_len_${tag}_${d.out}`;
    const outPath = join(EXPORT_DIR, out);
    rmSync(outPath, { force: true });
    buildDeck({ ...d, out }, ['--addr', EXPECTED_ADDR, '--client', client]);
    const s = await probeRenderedText(outPath);
    const whole = s.rendered.includes(client);
    if (whole && s.pageErrors === 0) {
      pass('AC-G5-LEN', `${d.out} [${tag}]: ${client.length}-unit --client rendered WHOLE (no silent cut)`);
    } else {
      fail('AC-G5-LEN', `${d.out} [${tag}]: ${client.length}-unit --client "${client}" NOT rendered whole `
        + `(wholeInDom=${whole} pageErrors=${s.pageErrors}) — the cover silently truncates the customer-facing name`);
    }
    rmSync(outPath, { force: true });
  }
}

/**
 * AC-G5-LEN-CLAMP (teeth, two-sided) — a >140-grapheme --client MUST render with
 * an HONEST visible cut: the first 139 graphemes followed by a trailing ellipsis,
 * never the full run and never a silent cut. Proves the clamp BITES exactly on
 * the over-length defect variant (the no-defect variants are AC-G5-LEN above).
 */
async function checkClientClampTeeth(d) {
  const client = 'X'.repeat(150); // > 140 graphemes
  const clamped = 'X'.repeat(139) + '…';
  const out = `_clamp_${d.out}`;
  const outPath = join(EXPORT_DIR, out);
  rmSync(outPath, { force: true });
  buildDeck({ ...d, out }, ['--addr', EXPECTED_ADDR, '--client', client]);
  const s = await probeRenderedText(outPath);
  const honestCut = s.rendered.includes(clamped);
  const fullRunAbsent = !s.rendered.includes('X'.repeat(140));
  if (honestCut && fullRunAbsent && s.pageErrors === 0) {
    pass('AC-G5-LEN-CLAMP', `${d.out}: 150-grapheme --client clamped to 139+'…' (visible cut, full run absent)`);
  } else {
    fail('AC-G5-LEN-CLAMP', `${d.out}: over-length --client not honestly clamped `
      + `(honestCut=${honestCut} fullRunAbsent=${fullRunAbsent} pageErrors=${s.pageErrors})`);
  }
  rmSync(outPath, { force: true });
}

/**
 * AC-G5-UNI (FAULT-13b unicode axis) — an emoji + combining-accent fixture
 * straddling the old index-64 cut MUST render whole with NO U+FFFD replacement
 * character. RED on the pre-fix template: .slice(0, 64) operates on UTF-16 code
 * units and splits the emoji's surrogate pair at the boundary, rendering a lone
 * surrogate as U+FFFD on the customer cover.
 */
async function checkClientUnicode(d) {
  // 63 code units, then an astral emoji (U+1F3E5 — its surrogate PAIR occupies
  // indices 63-64, so the old cut lands INSIDE it), then an explicit combining
  // acute (e + U+0301, NOT precomposed).
  const client = 'A'.repeat(63) + '🏥 Cline\u0301 Clinic';
  const out = `_uni_${d.out}`;
  const outPath = join(EXPORT_DIR, out);
  rmSync(outPath, { force: true });
  buildDeck({ ...d, out }, ['--addr', EXPECTED_ADDR, '--client', client]);
  const s = await probeRenderedText(outPath);
  const noReplacementChar = !s.rendered.includes('�');
  const whole = s.rendered.includes(client);
  if (noReplacementChar && whole && s.pageErrors === 0) {
    pass('AC-G5-UNI', `${d.out}: emoji/combining fixture straddling index 64 rendered whole, no U+FFFD`);
  } else {
    fail('AC-G5-UNI', `${d.out}: unicode boundary broken `
      + `(noReplacementChar=${noReplacementChar} wholeInDom=${whole} pageErrors=${s.pageErrors}) — `
      + `a lone surrogate / lost accent reached the customer cover`);
  }
  rmSync(outPath, { force: true });
}

/**
 * AC-TITLE-DEFAULT (FAULT-13/S5) — freeze with the WORKFLOW's historical arg
 * vector (--deck/--addr/--client/--out, NO --title) and assert the frozen
 * <title> carries NO internal 'templates/' path fragment. RED pre-fix: the
 * producer defaulted title to args.deck, shipping
 * <title>templates/email-forwarding-setup</title> in every customer artifact's
 * browser tab. (The smoke/acceptance surfaces always passed --title, which is
 * exactly what MASKED this live defect.)
 */
function checkTitleDefault(d) {
  const out = `_titledefault_${d.out}`;
  const outPath = join(EXPORT_DIR, out);
  rmSync(outPath, { force: true });
  execFileSync(
    'node',
    [INLINE, '--deck', d.deck, '--addr', EXPECTED_ADDR, '--client', CLIENT, '--out', out],
    { cwd: PROJECT_ROOT, encoding: 'utf8' }
  );
  const html = readFileSync(outPath, 'utf8');
  const m = html.match(/<title>([^<]*)<\/title>/);
  const title = m ? m[1] : '';
  if (m && title.length > 0 && !title.includes('templates/')) {
    pass('AC-TITLE-DEFAULT', `${d.out}: no---title freeze emits customer-safe <title>${title}</title>`);
  } else {
    fail('AC-TITLE-DEFAULT', `${d.out}: no---title freeze emitted <title>${title}</title> — `
      + `an internal template path in the customer artifact's browser tab`);
  }
  rmSync(outPath, { force: true });
}

/**
 * AC-G5'' — fail-closed proof. Building with a deliberately BAD --addr (the gate
 * would RAISE on KNOWN_BAD_GUID; we pass the would-be address directly) MUST exit
 * non-zero with ADDR-NON-CANONICAL and write NO output (the AC-G9 fail-loud
 * pattern). Proves a bad GUID yields no address, never a wrong one.
 */
function checkFailClosed(d) {
  const out = `_failclosed_${d.out}`;
  const outPath = join(EXPORT_DIR, out);
  rmSync(outPath, { force: true });

  // A non-canonical would-be address (KNOWN_BAD_GUID local-part). The gate RAISES
  // on this guid; the producer must likewise refuse to freeze the address.
  const badAddr = `${KNOWN_BAD_GUID}@appointments.contenteapp.com`;
  let exitCode = 0;
  let stderr = '';
  try {
    execFileSync('node', [INLINE, '--deck', d.deck, '--title', 'BAD', '--out', out, '--addr', badAddr],
      { cwd: PROJECT_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    exitCode = e.status ?? 1;
    stderr = (e.stderr || '') + (e.stdout || '');
  }
  const wroteOutput = existsSync(outPath);
  const named = /ADDR-NON-CANONICAL/.test(stderr);
  if (exitCode !== 0 && !wroteOutput && named) {
    pass("AC-G5''", `${d.out}: bad --addr "${badAddr}" fired RED (exit ${exitCode}, ADDR-NON-CANONICAL, NO output)`);
  } else {
    fail("AC-G5''", `${d.out}: bad --addr did NOT fail-close — exit=${exitCode} wroteOutput=${wroteOutput} named=${named}\n    stderr: ${stderr.slice(0, 300)}`);
  }
  rmSync(outPath, { force: true });
}

/**
 * MC-1 deliberately-broken RED fixture (G-THEATER — the load-bearing security
 * proof). We demonstrate the NEGATIVE actually fires:
 *
 *   (1) With the OLD host-permissive regex restored into a fixture deck, the
 *       injection/spoof addresses `victim-guid@evil.contenteapp.com` and
 *       `a<svg/onload=1>@x.contenteapp.com` render personalized===true (RED —
 *       the validator is exploitable). If this does NOT fire personalized, the
 *       test is theater (the fixture isn't actually using the weak regex).
 *   (2) With the TIGHTENED MC-1 regex, the SAME spoof addresses render
 *       personalized===false (fall to placeholder — contained), and ONLY a
 *       canonical {uuidv4}@appointments.contenteapp.com is personalized===true.
 *
 * We probe at the regex level against BOTH the restored-weak and the live-MC-1
 * deck sources extracted from the built exports — proving the export carries the
 * tightened check AND that the weak check would have admitted the spoofs.
 */
function checkMc1RedFixture() {
  // The two regexes, sourced as live JS (NOT reimplemented in the assertion).
  // OLD (host-permissive) — restored verbatim from the pre-MC-1 source.
  const OLD_RE = /^[^\s@]+@[^\s@]*contenteapp\.com$/i;
  // NEW (MC-1) — extracted live from the rebuilt export so we assert against the
  // ACTUAL shipped validator, not a hand-copied literal.
  const emailExport = readFileSync(join(EXPORT_DIR, 'EmailForwardingSetup.html'), 'utf8');
  const m = emailExport.match(/const okAddr = (\/\^\[0-9a-f\][^\n;]*\/)\.test\(cleanAddr\)/);
  if (!m) {
    // FAIL LOUD — a regression/refactor that renames okAddr, restructures the
    // validator, or drops the canonical regex MUST turn this RED, never silently
    // pass as "export may be stale". The validator pattern is the load-bearing
    // security surface; failure to locate it is a BLOCKING acceptance failure.
    fail('MC-1-RED', 'FAIL-LOUD: could not locate the MC-1 okAddr validator pattern in the rebuilt export. '
      + 'The validator was renamed, restructured, or removed — this is a regression on the load-bearing '
      + 'security surface, NOT a stale export. The host-axis negative fixtures below CANNOT be evaluated '
      + 'without the live validator; refusing to pass green-by-blind-spot.');
    return;
  }
  // Reconstruct the live regex object from the export's literal source.
  // eslint-disable-next-line no-eval -- sourcing the SHIPPED regex literal, not user input
  const NEW_RE = (0, eval)(m[1]);

  // FAIL LOUD if the extracted literal is not actually a tightened, host-pinned
  // validator. A host-widening refactor (e.g. @[a-z.]*contenteapp\.com) is the
  // exact D3 cross-tenant mutation MC-1 exists to close — the host-axis NEGATIVES
  // below catch admission, but we ALSO assert the regex source pins the literal
  // host so a structural drift is caught at the source level, not only behaviorally.
  const extractedSrc = m[1];
  if (!extractedSrc.includes('@appointments\\.contenteapp\\.com$')) {
    fail('MC-1-RED', `FAIL-LOUD: extracted MC-1 validator does NOT pin the exact host literal `
      + `\`@appointments\\.contenteapp\\.com$\` — it reads ${extractedSrc}. This is a host-widening `
      + `regression (the D3 cross-tenant-misroute RED-root). Refusing to pass.`);
    return;
  }

  // The deck applies a <>{} strip BEFORE the regex (cleanAddr). Mirror that here
  // so the spoof is evaluated exactly as the deck evaluates it.
  const clean = (s) => s.replace(/[<>{}]/g, '');

  const SPOOFS = [
    'victim-guid@evil.contenteapp.com',     // wrong host (subdomain spoof)
    'a<svg/onload=1>@x.contenteapp.com',     // injection-bearing local-part
  ];
  const CANONICAL = EXPECTED_ADDR;

  // ── HOST-AXIS NEGATIVES (FINDING D) — the D3 cross-tenant-misroute RED-root ──
  // The two SPOOFS above BOTH carry non-UUID local-parts, so the local-part
  // character class rejects them REGARDLESS of host — they prove nothing about
  // the HOST axis. A host-widening mutation (@[a-z.]*contenteapp\.com, canonical
  // UUID local-part kept) ADMITS {canonical-uuid}@evil.contenteapp.com while the
  // SPOOFS above stay rejected, so the suite would stay GREEN by blind spot.
  //
  // These fixtures use the CANONICAL KNOWN_GUID local-part on WRONG hosts. Each
  // MUST be rejected by the live MC-1 regex (personalized===false). They give the
  // host axis teeth: any host-widening makes at least one of them ADMIT, firing
  // MC-1-HOST RED. The local-part is held canonical so the ONLY discriminator is
  // the host — isolating the exact axis the existing SPOOFS were blind to.
  const HOST_AXIS_NEGATIVES = [
    [`${KNOWN_GUID}@evil.contenteapp.com`, 'foreign-tenant host (cross-tenant misroute)'],
    [`${KNOWN_GUID}@appointments.attacker.contenteapp.com`, 'attacker subdomain under contenteapp.com'],
    [`${KNOWN_GUID}@appointments.contenteapp.com.evil.com`, 'suffix spoof (contenteapp.com is not the registrable host)'],
    [`${KNOWN_GUID}@xcontenteapp.com`, 'no-dot label spoof (xcontenteapp != .contenteapp)'],
    [`${KNOWN_GUID}@appointments.contenteapp.co`, 'TLD truncation (.co not .com)'],
  ];
  // Sanity: every host-axis negative carries the CANONICAL local-part — so the
  // ONLY reason it can be rejected is the host. If the local-part itself differed
  // these would be theater (rejected on local-part, like the old SPOOFS).
  const allCanonicalLocalPart = HOST_AXIS_NEGATIVES.every(([a]) => a.startsWith(`${KNOWN_GUID}@`));
  const hostNegativeOffenders = HOST_AXIS_NEGATIVES
    .filter(([a]) => NEW_RE.test(clean(a)))
    .map(([a, why]) => `${a} (${why})`);
  const hostAxisAllRejected = hostNegativeOffenders.length === 0;
  // Prove the OLD permissive regex would have ADMITTED at least the foreign-tenant
  // host negative (it does — [^\s@]*contenteapp\.com matches evil.contenteapp.com),
  // so the host axis is genuinely a tightening MC-1 introduced, not a vacuous set.
  const oldAdmitsForeignTenant = OLD_RE.test(clean(`${KNOWN_GUID}@evil.contenteapp.com`));

  if (allCanonicalLocalPart && hostAxisAllRejected && oldAdmitsForeignTenant) {
    pass('MC-1-HOST', `host-axis negatives REJECTED by live MC-1 regex (canonical UUID local-part on ${HOST_AXIS_NEGATIVES.length} wrong hosts: `
      + `evil.contenteapp.com, appointments.attacker.contenteapp.com, *.com.evil.com, xcontenteapp.com, .contenteapp.co — all personalized===false). `
      + `OLD permissive regex ADMITTED {uuid}@evil.contenteapp.com (the D3 cross-tenant misroute MC-1 closes).`);
  } else {
    fail('MC-1-HOST', `HOST-AXIS RED — canonical-UUID-on-wrong-host ADMITTED by live MC-1 regex (cross-tenant misroute): `
      + `${hostNegativeOffenders.join(' | ') || '(none admitted)'}; allCanonicalLocalPart=${allCanonicalLocalPart} oldAdmitsForeignTenant=${oldAdmitsForeignTenant}`);
  }

  // (1) RED: old permissive regex ADMITS both spoofs (personalized===true). The
  //     negative MUST fire — if the weak regex rejected them, this proof is hollow.
  const oldAdmitsSpoofs = SPOOFS.every((s) => OLD_RE.test(clean(s)));
  // (2) GREEN: MC-1 regex REJECTS both spoofs (personalized===false) and ADMITS
  //     only the canonical address.
  const newRejectsSpoofs = SPOOFS.every((s) => !NEW_RE.test(clean(s)));
  const newAdmitsCanonical = NEW_RE.test(clean(CANONICAL));
  // Also prove the old regex would have ADMITTED the canonical too (so the
  // tightening is strictly narrowing, not a different axis).
  const oldAdmitsCanonical = OLD_RE.test(clean(CANONICAL));

  if (oldAdmitsSpoofs && newRejectsSpoofs && newAdmitsCanonical && oldAdmitsCanonical) {
    pass('MC-1-RED', `broken-fixture RED fires: OLD regex ADMITS spoofs [${SPOOFS.join(', ')}] (personalized===true), MC-1 regex REJECTS them (personalized===false) and admits ONLY canonical ${CANONICAL}`);
  } else {
    fail('MC-1-RED', `MC-1 proof incomplete — oldAdmitsSpoofs=${oldAdmitsSpoofs} newRejectsSpoofs=${newRejectsSpoofs} newAdmitsCanonical=${newAdmitsCanonical} oldAdmitsCanonical=${oldAdmitsCanonical}`);
  }

  // (3) LIVE-DOM corroboration of (1): build a fixture deck whose validator is
  //     reverted to the OLD permissive regex, freeze a SPOOF address into it, and
  //     assert the deck renders personalized===true (the exploit, demonstrated in
  //     a real browser). Then the SAME spoof against the real (MC-1) deck renders
  //     personalized===false. This is the in-anger RED, not just a regex assertion.
  return checkMc1RedLiveDom();
}

/**
 * Live-DOM half of the MC-1 RED proof. Builds a fixture deck with the OLD
 * permissive validator restored, freezes a spoof, and asserts personalized===true
 * (RED). Then asserts the real MC-1 deck refuses to even freeze the spoof
 * (ADDR-NON-CANONICAL) — fail-closed at the producer. Returns a Promise.
 */
async function checkMc1RedLiveDom() {
  const srcDeck = join(PROJECT_ROOT, 'templates', 'email-forwarding-setup');
  const fxDeck = join(PROJECT_ROOT, 'templates', '_mc1-red-fixture');
  rmSync(fxDeck, { recursive: true, force: true });
  cpSync(srcDeck, fxDeck, { recursive: true });

  const dcPath = join(fxDeck, readdirSync(fxDeck).find((f) => f.endsWith('.dc.html')));
  let dc = readFileSync(dcPath, 'utf8');

  // Revert the validator to the OLD host-permissive regex AND drop the <>{} strip
  // (restore the exact pre-MC-1 vulnerable seam). routingAddress falls back to
  // rawAddr (the pre-MC-1 source).
  dc = dc.replace(
    /const cleanAddr = rawAddr\.replace\(\/\[<>\{\}\]\/g, ''\);[\s\S]*?const okAddr = \/\^\[0-9a-f\][^\n]*\.test\(cleanAddr\);\n {4}const routingAddress = okAddr \? cleanAddr :/,
    "const okAddr = /^[^\\s@]+@[^\\s@]*contenteapp\\.com$/i.test(rawAddr);\n    const routingAddress = okAddr ? rawAddr :"
  );
  writeFileSync(dcPath, dc, 'utf8');

  // Register the fixture deck in the manifest path so resolveDeck can find it.
  // Easiest: the fixture sits under templates/ with a single *.dc.html, which
  // resolveDeck handles via its single-*.dc.html fallback (resolve-deck.mjs).
  const fxOut = '_Mc1RedFixture.html';
  const fxOutPath = join(EXPORT_DIR, fxOut);
  rmSync(fxOutPath, { force: true });

  // A subdomain-spoof address that the OLD regex ADMITS. We must build the fixture
  // WITHOUT the producer's --addr canonical gate (which would refuse the spoof),
  // so we open it with a live ?addr query instead (the OLD deck personalizes it).
  const SPOOF = 'victim-guid@evil.contenteapp.com';

  let built = true;
  try {
    execFileSync('node', [INLINE, '--deck', 'templates/_mc1-red-fixture', '--title', 'MC1-RED', '--out', fxOut],
      { cwd: PROJECT_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    built = false;
    log(`    [MC-1-RED-DOM] fixture build failed: ${((e.stderr || '') + (e.stdout || '')).slice(0, 200)}`);
  }

  if (built && existsSync(fxOutPath)) {
    // Open the OLD-regex deck with the spoof as a LIVE ?addr query and assert it
    // personalizes the spoof (RED — the vulnerability, demonstrated live).
    const sRed = await probePersonalization(
      fxOutPath, `?addr=${encodeURIComponent(SPOOF)}&client=${encodeURIComponent(CLIENT)}`,
      SPOOF, [FALLBACK_EMAIL, FALLBACK_GHL],
    );
    if (sRed.addrInDom && sRed.personalizedBranch && !sRed.notPersonalizedBranch) {
      pass('MC-1-RED-DOM', `OLD-regex fixture ADMITS spoof "${SPOOF}" — renders personalized===true in a live browser (the vulnerability MC-1 closes)`);
    } else {
      fail('MC-1-RED-DOM', `OLD-regex fixture did NOT personalize the spoof — RED did not fire: addrInDom=${sRed.addrInDom} personalizedBranch=${sRed.personalizedBranch} notPersonalizedBranch=${sRed.notPersonalizedBranch}`);
    }
  } else {
    fail('MC-1-RED-DOM', 'could not build the OLD-regex fixture deck to demonstrate the RED');
  }

  // Contained: the REAL (MC-1) deck refuses to freeze the spoof at the producer
  // (ADDR-NON-CANONICAL), AND would render personalized===false if the spoof were
  // supplied live. Prove the producer-side containment.
  let exitCode = 0; let stderr = '';
  try {
    execFileSync('node', [INLINE, '--deck', 'templates/email-forwarding-setup', '--title', 'X', '--out', '_should_not_exist.html', '--addr', SPOOF],
      { cwd: PROJECT_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    exitCode = e.status ?? 1; stderr = (e.stderr || '') + (e.stdout || '');
  }
  const containedAtProducer = exitCode !== 0 && /ADDR-NON-CANONICAL/.test(stderr) && !existsSync(join(EXPORT_DIR, '_should_not_exist.html'));
  if (containedAtProducer) {
    pass('MC-1-CONTAIN', `real MC-1 deck refuses to freeze spoof "${SPOOF}" at the producer (ADDR-NON-CANONICAL, no output) — contained`);
  } else {
    fail('MC-1-CONTAIN', `real MC-1 deck did NOT contain the spoof: exit=${exitCode} named=${/ADDR-NON-CANONICAL/.test(stderr)}`);
  }

  // Teardown — fixture deck/output never land in the committed tree.
  rmSync(fxDeck, { recursive: true, force: true });
  rmSync(fxOutPath, { force: true });
  rmSync(join(EXPORT_DIR, '_should_not_exist.html'), { force: true });
}

/**
 * CLI-relay proof (the gatedAddressForGuid fail-closed contract). Installs a
 * REAL-PYTHON shim of `autom8y-routing-address` (sourced from the #719 branch
 * gate — UV-P-1) and asserts: a known canonical GUID relays the gate's address;
 * every bad/empty/uppercase/injection GUID relays null (fail-closed); a missing
 * CLI relays null. This proves the Node glue CALLS the gate and NEVER constructs
 * an address.
 *
 * If the #719 branch source is unreachable, the relay checks are SKIPPED with an
 * explicit notice (rather than silently substituting a weaker double). The MC-1
 * and freeze proofs do not depend on the CLI.
 */
function checkCliRelay() {
  let shim;
  try {
    shim = installRoutingCliShim();
  } catch (e) {
    log(`  [CLI-RELAY] SKIPPED — #719 real-Python gate unreachable: ${e.message}`);
    log('  [CLI-RELAY] (MC-1 + render-then-freeze proofs do NOT depend on the CLI; they ran above.)');
    return;
  }
  const prevEnv = process.env.AUTOM8Y_ROUTING_ADDRESS_CLI;
  try {
    process.env.AUTOM8Y_ROUTING_ADDRESS_CLI = shim.cliPath;

    const good = gatedAddressForGuid(KNOWN_GUID);
    if (good === EXPECTED_ADDR) {
      pass('AC-CLI-OK', `gatedAddressForGuid("${KNOWN_GUID}") -> "${good}" via the REAL #719 gate (Python format_routing_address)`);
    } else {
      fail('AC-CLI-OK', `gatedAddressForGuid("${KNOWN_GUID}") -> "${good}", expected "${EXPECTED_ADDR}"`);
    }

    // Fail-closed: each MUST relay null (gate RAISES -> non-zero exit -> null).
    const badCases = [
      ['empty', ''],
      ['bad', 'not-a-uuid'],
      ['uppercase', 'B167331C-536F-4996-9B2D-2F696F35F556'],
      ['injection', 'a<svg/onload=1>'],
      ['victim', 'victim-guid'],
      ['non-v4', 'b167331c-536f-1996-9b2d-2f696f35f556'],
    ];
    const offenders = [];
    for (const [name, g] of badCases) {
      const r = gatedAddressForGuid(g);
      if (r !== null) offenders.push(`${name}->${JSON.stringify(r)}`);
    }
    if (offenders.length === 0) {
      pass('AC-CLI-CLOSED', `all ${badCases.length} bad GUIDs relay null (fail-closed): ${badCases.map(([n]) => n).join(', ')}`);
    } else {
      fail('AC-CLI-CLOSED', `bad GUID(s) did NOT fail-close: ${offenders.join(' | ')}`);
    }

    // Missing CLI on PATH -> null (e.g. #719 not yet merged / SDK not installed).
    process.env.AUTOM8Y_ROUTING_ADDRESS_CLI = 'autom8y-routing-address-DOES-NOT-EXIST';
    const missing = gatedAddressForGuid(KNOWN_GUID);
    if (missing === null) {
      pass('AC-CLI-MISSING', 'missing CLI on PATH relays null (fail-closed; placeholder, never a crash or wrong addr)');
    } else {
      fail('AC-CLI-MISSING', `missing CLI did NOT relay null: ${JSON.stringify(missing)}`);
    }
  } finally {
    if (prevEnv === undefined) delete process.env.AUTOM8Y_ROUTING_ADDRESS_CLI;
    else process.env.AUTOM8Y_ROUTING_ADDRESS_CLI = prevEnv;
    shim.cleanup();
  }
}

/**
 * CLI-relay re-validation proof (FINDING C — the relay must be safe in ISOLATION,
 * even if the CLI is buggy or compromised). We install ADVERSARIAL shims that all
 * exit 0 but print pathological stdout — a DIFFERENT address, multi-line output,
 * garbage, and a script-injection payload — and assert gatedAddressForGuid relays
 * `null` for EVERY one. Then a faithful canonical shim (exit 0, single canonical
 * line) MUST relay through. This proves the relay re-validates stdout against the
 * canonical mirror BEFORE returning, never trusting the CLI blindly.
 *
 * These shims are Node scripts (no Python dependency) so this check ALWAYS runs,
 * even when the real #719 gate is unreachable (it exercises the Node relay logic,
 * not the gate). Cross-platform: invoked via `node <shim>` through the
 * AUTOM8Y_ROUTING_ADDRESS_CLI override resolved at call time.
 */
function checkCliRelayRevalidation() {
  const dir = mkdtempSync(join(tmpdir(), 'autom8y-adversarial-shim-'));
  const prevEnv = process.env.AUTOM8Y_ROUTING_ADDRESS_CLI;

  // Write a shim that, regardless of argv, exits 0 and prints `payload` verbatim
  // to stdout. We wrap it so AUTOM8Y_ROUTING_ADDRESS_CLI points at a single
  // executable token: a tiny `node <script>` launcher is not directly an env
  // string, so we instead emit a self-contained executable shell shim that runs
  // node on an embedded script. Simpler + portable: write a Node script and a
  // POSIX launcher that execs `node` on it.
  function makeShim(name, payloadExpr) {
    const scriptPath = join(dir, `${name}.mjs`);
    // payloadExpr is a JS expression evaluated in the shim to produce the stdout
    // bytes. exit 0 always (the adversarial posture: "successful" exit, bad body).
    writeFileSync(scriptPath,
      `process.stdout.write(${payloadExpr});\nprocess.exit(0);\n`, 'utf8');
    const launcher = join(dir, name);
    writeFileSync(launcher, `#!/bin/sh\nexec node ${JSON.stringify(scriptPath)} "$@"\n`, 'utf8');
    chmodSync(launcher, 0o755);
    return launcher;
  }

  const ADV = [
    // name, shim-stdout payload expression, human description
    ['different-addr',
      JSON.stringify('11111111-2222-4333-8444-555555555555@appointments.contenteapp.com\n'),
      'a DIFFERENT (well-formed) canonical address than the gate would emit for this GUID'],
    ['different-host',
      JSON.stringify('b167331c-536f-4996-9b2d-2f696f35f556@evil.contenteapp.com\n'),
      'canonical UUID local-part but a FOREIGN host (cross-tenant misroute)'],
    ['multi-line',
      JSON.stringify('b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com\nEXTRA LINE\n'),
      'the canonical address PLUS a trailing extra line'],
    ['garbage',
      JSON.stringify('not an address at all\n'),
      'free-form garbage'],
    ['injection',
      JSON.stringify('x</script><img onerror=alert(1)>@appointments.contenteapp.com\n'),
      'a script-injection payload masquerading as an address'],
    ['empty',
      JSON.stringify('\n'),
      'whitespace-only stdout'],
    ['leading-space',
      JSON.stringify('   b167331c-536f-4996-9b2d-2f696f35f556@appointments.contenteapp.com   \n'),
      'canonical address with surrounding whitespace (trims clean → must relay)'],
  ];

  try {
    const offenders = [];
    for (const [name, payloadExpr, why] of ADV) {
      if (name === 'leading-space') continue; // positive trim case handled below
      process.env.AUTOM8Y_ROUTING_ADDRESS_CLI = makeShim(name, payloadExpr);
      const r = gatedAddressForGuid(KNOWN_GUID);
      if (r !== null) offenders.push(`${name} (${why}) -> ${JSON.stringify(r)}`);
    }
    if (offenders.length === 0) {
      pass('AC-CLI-REVALIDATE', `every adversarial exit-0 shim relays null (re-validated, never trusted blindly): `
        + `different-addr, different-host, multi-line, garbage, injection, empty`);
    } else {
      fail('AC-CLI-REVALIDATE', `buggy/compromised CLI stdout relayed a WRONG/UNVALIDATED address (NOT fail-closed): ${offenders.join(' | ')}`);
    }

    // Positive control A — a faithful canonical shim (exit 0, single canonical
    // line) MUST relay through. Proves re-validation does not over-reject.
    process.env.AUTOM8Y_ROUTING_ADDRESS_CLI = makeShim('canonical',
      JSON.stringify(`${EXPECTED_ADDR}\n`));
    const okCanonical = gatedAddressForGuid(KNOWN_GUID);
    // Positive control B — canonical address with surrounding whitespace trims
    // clean and MUST relay (the relay trims a single trailing newline + outer ws).
    process.env.AUTOM8Y_ROUTING_ADDRESS_CLI = makeShim('leading-space',
      ADV.find(([n]) => n === 'leading-space')[1]);
    const okTrimmed = gatedAddressForGuid(KNOWN_GUID);
    if (okCanonical === EXPECTED_ADDR && okTrimmed === EXPECTED_ADDR) {
      pass('AC-CLI-REVALIDATE-OK', `a faithful canonical shim relays "${okCanonical}" through (re-validation does not over-reject; whitespace-padded canonical also relays)`);
    } else {
      fail('AC-CLI-REVALIDATE-OK', `canonical shim did NOT relay through: canonical=${JSON.stringify(okCanonical)} trimmed=${JSON.stringify(okTrimmed)} (expected both "${EXPECTED_ADDR}")`);
    }
  } finally {
    if (prevEnv === undefined) delete process.env.AUTOM8Y_ROUTING_ADDRESS_CLI;
    else process.env.AUTOM8Y_ROUTING_ADDRESS_CLI = prevEnv;
    rmSync(dir, { recursive: true, force: true });
  }
}

async function main() {
  log('=== Contente deck inliner — ACCEPTANCE (live offline instrument) ===\n');

  // MC-1 RED-root proof FIRST (the load-bearing security proof — G-THEATER).
  log('--- MC-1: deliberately-broken RED fixture (the security proof — RED must fire) ---');
  await checkMc1RedFixture();
  log('');

  // CLI relay fail-closed contract (real-Python #719 gate shim).
  log('--- CLI relay: gatedAddressForGuid fail-closed (REAL #719 gate shim) ---');
  checkCliRelay();
  log('');

  // CLI relay re-validation (FINDING C — relay safe in ISOLATION vs a buggy/
  // compromised CLI; adversarial exit-0 shims must ALL relay null).
  log('--- CLI relay re-validation: adversarial exit-0 shims must relay null (FINDING C) ---');
  checkCliRelayRevalidation();
  log('');

  // AC-G9 first (it builds + tears down a fixture deck; isolate it from the real builds).
  log('--- AC-G9: deliberately-broken fixture (RED against the REAL build) ---');
  checkBrokenFixtureRed();
  log('');

  for (const d of DECKS) {
    log(`--- ${d.deck} ---`);
    checkDeterminism(d);             // AC-G7 (also leaves a fresh build in export/)
    await checkLiveOffline(d);       // AC-G1..G6, G8 (live ?addr personalization)
    await checkPersonalizedFreeze(d); // AC-G5' (render-then-freeze, NO ?addr, offline)
    await checkClientScriptBreakFreeze(d); // AC-CLIENT-BREAK (FINDING B: hostile --client)
    await checkClientLengthBoundaries(d);  // AC-G5-LEN (FAULT-13b: 63/64/65 + live leak string)
    await checkClientClampTeeth(d);        // AC-G5-LEN-CLAMP (>140 graphemes -> honest '…' cut)
    await checkClientUnicode(d);           // AC-G5-UNI (surrogate/combining straddle, no U+FFFD)
    checkTitleDefault(d);            // AC-TITLE-DEFAULT (no --title -> customer-safe <title>)
    checkFailClosed(d);              // AC-G5'' (bad --addr -> ADDR-NON-CANONICAL, no output)
    log('');
  }

  log('=== SUMMARY ===');
  if (failures === 0) {
    log("ALL ACCEPTANCE ASSERTIONS PASS (AC-G1..G9, AC-G5', AC-G5'', AC-CLIENT-BREAK, AC-G5-LEN, AC-G5-LEN-CLAMP, AC-G5-UNI, AC-TITLE-DEFAULT, MC-1-RED, MC-1-HOST, CLI-relay, CLI-revalidate).");
    process.exit(0);
  } else {
    log(`${failures} ACCEPTANCE ASSERTION(S) FAILED.`);
    process.exit(1);
  }
}

main().catch((e) => { console.error('[acceptance] HARNESS ERROR:', e.stack || e.message); process.exit(1); });
