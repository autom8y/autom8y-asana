/**
 * inline.mjs — the producer CLI (TDD §CLI).
 *
 * RUNTIME-OFFLINE-ONLY: reads ONLY committed bytes (the `prep` step vendored
 * React UMD + the 14 woff2 faces + the optimized JPEGs into the repo). This step
 * NEVER touches the network. It orchestrates:
 *
 *   C-resolve  → manifest-driven, validated deck input contract (namespace agree)
 *   C-brand    → image map (committed optimized bytes) + CSS flatten (de-dup) +
 *                vendored base64 @font-face (Google @import stripped)
 *   C-runtime  → React+ReactDOM UMD inlined AHEAD of support.js, deck-stage.js →
 *                data: URI, support.js/_ds_bundle.js inlined, ds-base.js → CSS
 *   C-guards   → balance / no-src / no-rel / order / namespace assertions
 *   C-ofl      → OFL notice in the deck + LICENSE-fonts.txt present gate
 *
 * Emits the bundled single-file <ClientName>.html (the client artifact) to
 * project/export/ and preserves the editable .dc.html source in place (dual
 * deliverable). Exit non-zero on ANY guard/missing-asset failure, writing NO
 * output file (fail-loud; ADR D1/D3; inline.mjs:81,198 cured).
 *
 * Usage:
 *   node build/inline.mjs --deck templates/ghl-calendar-setup --title "GHL Calendar Setup" --out GhlCalendarSetup.html
 *   node build/inline.mjs --all
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

import { resolveDeck } from './lib/resolve-deck.mjs';
import {
  flattenCss, buildImageMap, inlineImages, cssStyleBlock,
} from './lib/bundle-brand-assets.mjs';
import {
  inlineDcRuntime, injectTitle, injectFrozenAddress, CANONICAL_ADDR_RE,
  REACT_MARKER, SUPPORT_GUARD_MARKER,
} from './lib/inline-dc-runtime.mjs';
import {
  assertScriptBalance, assertNoScriptSrc, assertNoRelativeRefs,
  assertReactBeforeGuard, assertBundleNamespace, BuildError,
} from './lib/safe-html.mjs';
import { OFL_NOTICE, assertLicenseFilePresent } from './lib/ofl.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..');
const VENDOR = join(PROJECT_ROOT, 'build', 'vendor');
const EXPORT_DIR = join(PROJECT_ROOT, 'export');
const LICENSE_PATH = join(PROJECT_ROOT, 'LICENSE-fonts.txt');

// The deck roster for --all (folder, title, out).
const DECKS = [
  {
    deck: 'templates/ghl-calendar-setup',
    title: 'GHL Calendar Setup — Contente',
    out: 'GhlCalendarSetup.html',
    slides: 23,
  },
  {
    deck: 'templates/email-forwarding-setup',
    title: 'Email Forwarding Setup — Contente',
    out: 'EmailForwardingSetup.html',
    slides: 15,
  },
];

function parseArgs(argv) {
  const args = { all: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--all') args.all = true;
    else if (a === '--deck') args.deck = argv[++i];
    else if (a === '--title') args.title = argv[++i];
    else if (a === '--out') args.out = argv[++i];
    else if (a === '--addr') args.addr = argv[++i];
    else if (a === '--client') args.client = argv[++i];
  }
  return args;
}

function assertVendored() {
  const reactJs = join(VENDOR, 'react.umd.js');
  const reactDomJs = join(VENDOR, 'react-dom.umd.js');
  const fontsCss = join(VENDOR, 'fonts', 'fonts.base64.css');
  const missing = [];
  if (!existsSync(reactJs)) missing.push('build/vendor/react.umd.js');
  if (!existsSync(reactDomJs)) missing.push('build/vendor/react-dom.umd.js');
  if (!existsSync(fontsCss)) missing.push('build/vendor/fonts/fonts.base64.css');
  if (missing.length > 0) {
    throw new BuildError(
      'VENDOR-MISSING',
      `vendored bytes absent:\n  ${missing.join('\n  ')}\nRun \`npm run prep\` first (build-time network, committed once).`
    );
  }
  return { reactJs, reactDomJs, fontsCss };
}

/**
 * Build one deck → bundled single-file HTML string + receipts. Throws BuildError
 * (caught by the CLI) on any failure; the caller writes NO file on throw.
 */
function buildDeck({ deck, title, out, addr, client }) {
  // ── C-ofl pre-emit gate: LICENSE-fonts.txt must be present ──
  assertLicenseFilePresent(LICENSE_PATH);

  // ── render-then-freeze pre-validation (ADR Amendment A1, TDD §4.2) ──
  // If --addr is supplied it MUST be a gated, MC-1-canonical address. We refuse
  // to freeze a non-canonical address — fail-loud, no output written. This is the
  // producer-side parity of the deck's MC-1 okAddr check. The producer NEVER
  // constructs an address (G-PROPAGATE) — it only freezes one the caller passed,
  // and only if it is exactly what the gate would emit.
  if (addr !== undefined && !CANONICAL_ADDR_RE.test(addr)) {
    throw new BuildError(
      'ADDR-NON-CANONICAL',
      `--addr "${addr}" is not a canonical {uuidv4}@appointments.contenteapp.com ` +
      `routing address; refusing to freeze a non-gated address. The address must ` +
      `come from the autom8y-core gate (format_routing_address); the producer never ` +
      `derives one.`
    );
  }

  // ── C-resolve ──
  const r = resolveDeck({
    deckDir: deck,
    projectRoot: PROJECT_ROOT,
    outputTitle: title,
    outputFilename: out,
  });

  const { reactJs, reactDomJs, fontsCss } = assertVendored();
  const vendoredFontsCss = readFileSync(fontsCss, 'utf8');

  let html = r.entryHtml;

  // ── C-brand: images (committed optimized bytes) ──
  const { map: imageMap, totalBytes: imageBytes } = buildImageMap(r.assetsDir, r.entryHtml);
  html = inlineImages(html, imageMap);

  // ── C-brand: CSS flatten (de-dup) + vendored base64 @font-face ──
  // Source the brand sheets from the owned @autom8y/contente-tokens package
  // (cssRoot/cssRels resolved in C-resolve) — NOT the in-tree tokens/. flattenCss
  // is unchanged: it resolves join(cssRoot, basename) onto byte-identical package
  // bytes, so the golden hash holds.
  const flatCss = flattenCss(r.cssRels, r.cssRoot, vendoredFontsCss);
  const cssBlock = cssStyleBlock(flatCss);

  // ── C-runtime: inline React UMD ahead, deck-stage → data:, support/bundle inline ──
  html = inlineDcRuntime({
    html,
    reactJsPath: reactJs,
    reactDomJsPath: reactDomJs,
    deckStageJsPath: r.deckStageJs,
    supportJsPath: r.supportJs,
    dsBundleJsPath: r.dsBundleJs,
    cssBlock,
    oflNotice: OFL_NOTICE,
  });

  // ── client-clean <title> ──
  html = injectTitle(html, title);

  // ── render-then-freeze: seed the gated ?addr (and optional client) ──
  // Only when --addr is supplied (and already validated canonical above). When
  // absent, the deck is unchanged — it renders the placeholder until a human
  // supplies ?addr live (D1 preserved). The frozen instance renders
  // personalized === true with NO human seam.
  if (addr !== undefined) {
    html = injectFrozenAddress(html, addr, client);
  }

  // ── C-guards (each fails the build non-zero) ──
  assertScriptBalance(html);
  assertNoScriptSrc(html);
  assertNoRelativeRefs(html);
  assertReactBeforeGuard(html, REACT_MARKER, SUPPORT_GUARD_MARKER);
  assertBundleNamespace(html, r.namespace);

  const bytes = Buffer.byteLength(html, 'utf8');
  const sha256 = createHash('sha256').update(html, 'utf8').digest('hex');

  return {
    html,
    receipts: {
      deck,
      out,
      namespace: r.namespace,
      imageRefs: Object.keys(imageMap).length,
      imageBytes,
      bytes,
      mb: (bytes / 1024 / 1024).toFixed(2),
      sha256,
    },
  };
}

function emit(html, out) {
  mkdirSync(EXPORT_DIR, { recursive: true });
  const outPath = join(EXPORT_DIR, out);
  writeFileSync(outPath, html, 'utf8');
  return outPath;
}

function reportReceipts(rec, outPath) {
  const idealGate = rec.bytes <= 10 * 1024 * 1024;
  const hardGate = rec.bytes <= 25 * 1024 * 1024;
  console.log(`\n[inline] ${rec.deck} → ${outPath}`);
  console.log(`  namespace:   ${rec.namespace}`);
  console.log(`  images:      ${rec.imageRefs} refs, ${(rec.imageBytes / 1024 / 1024).toFixed(2)} MB committed bytes`);
  console.log(`  output size: ${rec.bytes} bytes (${rec.mb} MB)`);
  console.log(`  sha256:      ${rec.sha256}`);
  console.log(`  <10MB ideal: ${idealGate ? 'PASS' : 'OVER (warn)'}`);
  console.log(`  <25MB hard:  ${hardGate ? 'PASS' : 'FAIL'}`);
  if (!hardGate) throw new BuildError('WEIGHT-HARD-GATE', `${rec.mb} MB exceeds 25 MB hard gate`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  // --addr/--client apply to single-deck render-then-freeze only. --all is the
  // template/placeholder roster path (no per-clinic freeze).
  const targets = args.all
    ? DECKS
    : [{
        deck: args.deck,
        // FAULT-13/S5: the default <title> must be CUSTOMER-SAFE. Defaulting to
        // args.deck shipped the internal path (<title>templates/email-forwarding-
        // setup</title>) in every live customer artifact's browser tab. The deck
        // FOLDER NAME (basename) is the safe floor; callers pass --title (the
        // manifest-owned customer-facing title) for the real document title.
        title: args.title || basename(args.deck || ''),
        out: args.out || 'deck.html',
        addr: args.addr,
        client: args.client,
      }];

  if (!args.all && !args.deck) {
    console.error('[inline] usage: --deck <folder> --title "<title>" --out <ClientName>.html   (or --all)');
    process.exit(2);
  }

  for (const t of targets) {
    const { html, receipts } = buildDeck(t);
    const outPath = emit(html, t.out);
    reportReceipts(receipts, outPath);
  }
  console.log('\n[inline] DONE — bundled deck(s) emitted to export/. Editable .dc.html sources preserved in place.');
}

main().catch((e) => {
  if (e instanceof BuildError) {
    console.error(`\n[inline] BUILD FAILED — ${e.message}`);
  } else {
    console.error(`\n[inline] UNEXPECTED FAILURE — ${e.stack || e.message}`);
  }
  process.exit(1);
});
