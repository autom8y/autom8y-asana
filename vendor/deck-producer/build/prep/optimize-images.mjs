/**
 * P-images — sharp JPEG q83 recompress screenshots → COMMIT (ADR D5).
 *
 * BUILD-TIME (sharp/libvips), run ONCE, OUTPUT COMMITTED. For each deck's
 * assets/, recompress the large screenshot PNGs to JPEG q83 (mozjpeg) and COMMIT
 * the optimized .jpg alongside, retaining the original PNG under assets/_raw/ for
 * reproducibility. Logos (small, transparency) stay PNG.
 *
 * The `build` step then base64-embeds the COMMITTED optimized bytes — so the
 * golden hash (AC-G7) is a property of committed inputs, NOT the host's
 * sharp/libvips/mozjpeg version (ADR D5: recompress-once-and-commit, not
 * recompress-in-build).
 *
 * Idempotence: a screenshot is recompressed from its assets/_raw/<name>.png
 * source. On first run the original assets/<name>.png is MOVED to _raw/ and the
 * optimized <name>.jpg is written; on re-run the _raw/ source is reused (the
 * committed .jpg is overwritten with identical bytes — sharp q83 mozjpeg is
 * deterministic for fixed input). Re-runs do NOT recompress a previously-emitted
 * JPEG (that would be lossy-on-lossy).
 *
 * Classification: an asset is a LOGO (stays PNG) if its name matches the logo
 * pattern OR its raw bytes are < the logo size threshold; everything else is a
 * screenshot → JPEG. This is name+size based so it generalizes across decks
 * (the GHL deck uses image*.png; the email deck uses em_*.png).
 */

import {
  readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync, renameSync, statSync,
} from 'node:fs';
import { join, dirname, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..', '..');

const DECKS = [
  join(PROJECT_ROOT, 'templates', 'ghl-calendar-setup'),
  join(PROJECT_ROOT, 'templates', 'email-forwarding-setup'),
];

const JPEG_QUALITY = 83;
const LOGO_NAME_RE = /logo/i;
const LOGO_SIZE_THRESHOLD = 64 * 1024; // <64 KiB raw + named like a logo → keep PNG

function isLogo(name, bytes) {
  return LOGO_NAME_RE.test(name) && bytes.length < LOGO_SIZE_THRESHOLD;
}

async function optimizeDeck(sharp, assetsDir) {
  if (!existsSync(assetsDir)) {
    console.log(`[optimize-images] (skip) no assets/ at ${assetsDir}`);
    return;
  }
  const rawDir = join(assetsDir, '_raw');
  mkdirSync(rawDir, { recursive: true });

  // Enumerate source PNGs in the assets dir (NOT already-optimized jpgs).
  const pngs = readdirSync(assetsDir)
    .filter((f) => extname(f).toLowerCase() === '.png')
    .sort();

  let optimized = 0;
  let logos = 0;
  for (const name of pngs) {
    const src = join(assetsDir, name);
    const bytes = readFileSync(src);

    if (isLogo(name, bytes)) {
      logos++;
      continue; // logos stay PNG, in place
    }

    // Screenshot → JPEG. Use _raw/<name>.png as the recompression source so
    // re-runs never recompress a JPEG (lossy-on-lossy). On first run, move the
    // original PNG into _raw/.
    const stem = basename(name, '.png');
    const rawPath = join(rawDir, name);
    if (!existsSync(rawPath)) {
      renameSync(src, rawPath); // move original PNG → _raw/ (idempotent source)
    }
    const rawBytes = readFileSync(rawPath);
    const jpg = await sharp(rawBytes).jpeg({ quality: JPEG_QUALITY, mozjpeg: true }).toBuffer();
    writeFileSync(join(assetsDir, `${stem}.jpg`), jpg);
    optimized++;
    console.log(
      `  ${name}: ${(rawBytes.length / 1024).toFixed(0)} KiB PNG → ${(jpg.length / 1024).toFixed(0)} KiB JPEG`
    );
  }
  console.log(
    `[optimize-images] ${basename(assetsDir)}: ${optimized} screenshots → JPEG q${JPEG_QUALITY}, ${logos} logos kept PNG`
  );
}

async function main() {
  const { default: sharp } = await import('sharp');
  for (const deck of DECKS) {
    await optimizeDeck(sharp, join(deck, 'assets'));
  }
  console.log('[optimize-images] done. Optimized JPEGs committed to each deck assets/ (originals in assets/_raw/).');
}

main().catch((e) => { console.error('[optimize-images] FAILED:', e.message); process.exit(1); });
