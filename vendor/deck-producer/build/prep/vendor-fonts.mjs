/**
 * P-fonts — vendor the REAL latin webfont faces (ADR D2 / D4).
 *
 * BUILD-TIME-NETWORK, run ONCE, OUTPUT COMMITTED. Resolves the same Google Fonts
 * CSS the brand fonts.css @import requests (now owned by
 * @autom8y/contente-tokens — src/css/fonts.css), and for each declared
 * (family, weight, style) tuple extracts the LATIN subset @font-face block:
 *
 *   Spectral          400, 500, 600, 700, 800, 400-italic
 *   Plus Jakarta Sans 400, 500, 600, 700, 800
 *   JetBrains Mono    400, 500, 700
 *
 * D4 (faux-bold fix) — IMPORTANT PRAGMATIC FINDING (deviation from "14 distinct
 * woff2 files", documented in the implementation notes):
 *   Google serves Plus Jakarta Sans and JetBrains Mono as VARIABLE FONTS — ONE
 *   woff2 covers the whole weight axis (probed: the latin woff2 for PJS 400/500/
 *   600/700/800 are byte-identical; JBM 400/500/700 are byte-identical). Spectral
 *   is served as STATIC per-weight files (distinct woff2 per weight).
 *   A variable-font woff2 with a wght axis renders TRUE weights via the
 *   `font-weight` selector — this is NOT the export's faux-bold (the export
 *   reused ONE usWeightClass=400 STATIC face and let the browser synthesize bold).
 *   So premise-4 is FIXED either way; the cleanest, smallest, true-weight encoding
 *   is: dedup the variable-font woff2 by bytes and emit ONE @font-face per unique
 *   file with a `font-weight: <min> <max>` RANGE (the VF path D4 deferred only for
 *   "sourcing cost" — but Google already serves the VF, so there is no extra
 *   sourcing). Static families (Spectral) keep one @font-face per weight.
 *
 * This avoids embedding the same ~135 KiB VF five times (PJS) / three times (JBM)
 * while delivering real weights. The committed raw woff2 are deduped to the unique
 * set; fonts.base64.css references each unique file once.
 *
 * Determinism: faces are emitted in a fixed order; base64 of fixed bytes is
 * deterministic; the build consumes the committed fonts.base64.css, so the golden
 * hash is host-independent (ADR D5 rationale, applied to fonts).
 */

import { writeFileSync, mkdirSync, readFileSync, existsSync, readdirSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..', '..');
const FONTS_DIR = join(PROJECT_ROOT, 'build', 'vendor', 'fonts');

// The exact CSS the brand fonts.css @import requests (kept in sync with the
// owned @autom8y/contente-tokens src/css/fonts.css @import — if that @import
// changes, re-derive this URL).
const GOOGLE_CSS_URL =
  'https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400' +
  '&family=Plus+Jakarta+Sans:wght@400;500;600;700;800' +
  '&family=JetBrains+Mono:wght@400;500;700&display=swap';

// A modern desktop UA so Google serves woff2 (not the older ttf fallback).
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

// The 14 faces we expect (the assertion target — D4). Order is the emit order.
const EXPECTED_FACES = [
  { family: 'JetBrains Mono', style: 'normal', weight: 400 },
  { family: 'JetBrains Mono', style: 'normal', weight: 500 },
  { family: 'JetBrains Mono', style: 'normal', weight: 700 },
  { family: 'Plus Jakarta Sans', style: 'normal', weight: 400 },
  { family: 'Plus Jakarta Sans', style: 'normal', weight: 500 },
  { family: 'Plus Jakarta Sans', style: 'normal', weight: 600 },
  { family: 'Plus Jakarta Sans', style: 'normal', weight: 700 },
  { family: 'Plus Jakarta Sans', style: 'normal', weight: 800 },
  { family: 'Spectral', style: 'normal', weight: 400 },
  { family: 'Spectral', style: 'normal', weight: 500 },
  { family: 'Spectral', style: 'normal', weight: 600 },
  { family: 'Spectral', style: 'normal', weight: 700 },
  { family: 'Spectral', style: 'normal', weight: 800 },
  { family: 'Spectral', style: 'italic', weight: 400 },
];

async function fetchText(url) {
  const res = await fetch(url, { redirect: 'follow', headers: { 'User-Agent': UA } });
  if (!res.ok) throw new Error(`fetch failed ${res.status} for ${url}`);
  return await res.text();
}

async function fetchBytes(url) {
  const res = await fetch(url, { redirect: 'follow', headers: { 'User-Agent': UA } });
  if (!res.ok) throw new Error(`fetch failed ${res.status} for ${url}`);
  return Buffer.from(await res.arrayBuffer());
}

/**
 * Parse the Google CSS into per-subset @font-face descriptors. Each descriptor:
 *   { subset, family, style, weight, url }
 */
function parseFontFaces(css) {
  const faces = [];
  // Split on the /* subset */ comment so we know which subset each block is.
  const blockRe = /\/\*\s*([a-z-]+)\s*\*\/\s*@font-face\s*\{([\s\S]*?)\}/gi;
  let m;
  while ((m = blockRe.exec(css)) !== null) {
    const subset = m[1];
    const body = m[2];
    const family = (body.match(/font-family:\s*['"]([^'"]+)['"]/i) || [])[1];
    const style = (body.match(/font-style:\s*([a-z]+)/i) || [])[1];
    const weight = parseInt((body.match(/font-weight:\s*(\d+)/i) || [])[1], 10);
    const url = (body.match(/src:\s*url\(([^)]+)\)/i) || [])[1];
    if (family && style && weight && url) {
      faces.push({ subset, family, style, weight, url: url.replace(/['"]/g, '') });
    }
  }
  return faces;
}

function faceKey(f) {
  return `${f.family}|${f.style}|${f.weight}`;
}

function safeStem(f) {
  const fam = f.family.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return `${fam}-${f.weight}-${f.style}`;
}

async function main() {
  mkdirSync(FONTS_DIR, { recursive: true });

  // Clean any stale woff2 from a prior run so the committed set is exactly the
  // unique faces this run produces (deterministic, no orphan duplicates).
  for (const f of readdirSync(FONTS_DIR)) {
    if (f.endsWith('.woff2')) rmSync(join(FONTS_DIR, f));
  }

  console.log('[vendor-fonts] fetching Google Fonts CSS (latin subset target)…');
  const css = await fetchText(GOOGLE_CSS_URL);
  const allFaces = parseFontFaces(css);

  // Select the LATIN subset face for each (family, style, weight) tuple.
  const latin = allFaces.filter((f) => f.subset === 'latin');
  const latinByKey = new Map(latin.map((f) => [faceKey(f), f]));

  // Validate we found exactly the 14 expected faces (D4 assertion).
  const missing = [];
  for (const want of EXPECTED_FACES) {
    if (!latinByKey.has(faceKey(want))) {
      missing.push(`${want.family} ${want.weight} ${want.style}`);
    }
  }
  if (missing.length > 0) {
    throw new Error(
      `[vendor-fonts] FAILED — Google CSS did not yield the expected latin faces:\n  ` +
      missing.join('\n  ') +
      `\nFound ${latin.length} latin faces. Re-check the @import URL / UA.`
    );
  }

  // Download each expected face's woff2 (in fixed order for determinism).
  // Dedup by content hash so variable-font families (PJS, JBM) commit ONE woff2.
  const downloaded = []; // { want, bytes, sha }
  const byHash = new Map(); // sha → { bytes, stem }
  for (const want of EXPECTED_FACES) {
    const face = latinByKey.get(faceKey(want));
    console.log(`[vendor-fonts] ${want.family} ${want.weight} ${want.style} ← …${face.url.slice(-32)}`);
    const bytes = await fetchBytes(face.url);
    // woff2 magic number: 'wOF2'.
    if (bytes.length < 4 || bytes.toString('ascii', 0, 4) !== 'wOF2') {
      throw new Error(`[vendor-fonts] ${want.family} ${want.weight}: not a woff2 (magic mismatch)`);
    }
    const sha = createHash('sha256').update(bytes).digest('hex');
    downloaded.push({ want, bytes, sha });
    if (!byHash.has(sha)) {
      // Name the committed file by the FIRST tuple that produced it.
      byHash.set(sha, { bytes, stem: safeStem(want) });
    }
  }

  // Group expected tuples by their unique woff2 (sha). For each group: if it spans
  // multiple weights of the SAME family+style → a variable font → emit ONE
  // @font-face with a font-weight RANGE; otherwise emit a static per-weight face.
  const groups = new Map(); // sha → [tuples]
  for (const d of downloaded) {
    if (!groups.has(d.sha)) groups.set(d.sha, []);
    groups.get(d.sha).push(d.want);
  }

  // Commit each UNIQUE woff2 once (raw, for audit/reproducibility).
  let uniqueBytes = 0;
  for (const [sha, { bytes, stem }] of byHash) {
    writeFileSync(join(FONTS_DIR, `${stem}.woff2`), bytes);
    uniqueBytes += bytes.length;
  }

  // Emit the base64 @font-face CSS. Deterministic order: by stem.
  let outCss =
    '/* ============================================================================\n' +
    '   Contente — VENDORED webfonts (SIL OFL-1.1; see LICENSE-fonts.txt)\n' +
    '   REAL latin faces, base64-embedded. Generated by build/prep/vendor-fonts.mjs\n' +
    '   (ADR D2/D4) — do NOT edit by hand; re-run `npm run prep` to re-vendor.\n' +
    '   Premise-4 (faux-bold) FIXED: Spectral ships static per-weight faces; Plus\n' +
    '   Jakarta Sans + JetBrains Mono ship as variable fonts (Google serves one\n' +
    '   woff2 per family covering the wght axis) with a font-weight RANGE — both\n' +
    '   render TRUE weights, not a 400 reused across declared weights.\n' +
    '   ============================================================================ */\n';

  const emitOrder = [...byHash.keys()].sort((a, b) => byHash.get(a).stem.localeCompare(byHash.get(b).stem));
  const faceManifest = [];
  for (const sha of emitOrder) {
    const tuples = groups.get(sha);
    const b64 = byHash.get(sha).bytes.toString('base64');
    // All tuples sharing a woff2 must share family + style (asserted).
    const fam = tuples[0].family;
    const sty = tuples[0].style;
    if (!tuples.every((t) => t.family === fam && t.style === sty)) {
      throw new Error(`[vendor-fonts] a shared woff2 spans multiple families/styles: ${JSON.stringify(tuples)}`);
    }
    const weights = tuples.map((t) => t.weight).sort((a, b) => a - b);
    const weightDecl = weights.length > 1 ? `${weights[0]} ${weights[weights.length - 1]}` : `${weights[0]}`;
    outCss +=
      `\n@font-face {\n` +
      `  font-family: '${fam}';\n` +
      `  font-style: ${sty};\n` +
      `  font-weight: ${weightDecl};\n` +
      `  font-display: swap;\n` +
      `  src: url(data:font/woff2;base64,${b64}) format('woff2');\n` +
      `}\n`;
    faceManifest.push({ family: fam, style: sty, weights, variable: weights.length > 1 });
  }

  writeFileSync(join(FONTS_DIR, 'fonts.base64.css'), outCss, 'utf8');

  // Record a pin manifest for audit (NOT consumed by the build → no hash impact).
  const pin = {
    source: GOOGLE_CSS_URL,
    declaredTuples: EXPECTED_FACES.length,
    uniqueWoff2: byHash.size,
    uniqueWoff2Bytes: uniqueBytes,
    faces: faceManifest,
    vendoredAt: new Date().toISOString().slice(0, 10),
  };
  writeFileSync(join(FONTS_DIR, 'FONTS-PIN.json'), JSON.stringify(pin, null, 2) + '\n', 'utf8');

  console.log(
    `[vendor-fonts] done. ${EXPECTED_FACES.length} declared tuples → ${byHash.size} unique woff2 ` +
    `(${(uniqueBytes / 1024).toFixed(1)} KiB), ${emitOrder.length} @font-face rules → fonts.base64.css`
  );
}

main().catch((e) => { console.error('[vendor-fonts] FAILED:', e.message); process.exit(1); });
