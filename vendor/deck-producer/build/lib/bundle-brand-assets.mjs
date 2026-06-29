/**
 * C-brand — bundle-brand-assets (Path-C-REUSABLE; PKG-006, TDD §C-brand).
 *
 * Factored SEPARATELY from the dc-runtime-specific half so a future Path C
 * Svelte satellite inherits this brand half cheaply (T4-d). Responsibilities:
 *   - flatten the token sheets in globalCssPaths order, swapping the Google
 *     @import (in tokens/fonts.css) for the vendored base64 @font-face CSS;
 *   - DE-DUP guard: styles.css re-@imports the same 6 token sheets, so we
 *     flatten the 6 directly and DROP styles.css's @import block (NEW-1);
 *   - base64-embed images in BOTH HTML-attribute and JS-string contexts;
 *   - inject the OFL notice.
 */

import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, basename } from 'node:path';
import {
  safeReplace,
  escapeStyleContent,
  BuildError,
} from './safe-html.mjs';

const GOOGLE_FONTS_IMPORT_RE = /@import\s+url\(\s*["']?https?:\/\/fonts\.googleapis\.com[^)]*\)\s*;?/gi;
const ANY_IMPORT_RE = /@import\s+url\([^)]*\)\s*;?/gi;

/**
 * Flatten the manifest's globalCssPaths into one inline stylesheet.
 *
 * Spec (NEW-1 de-dup): flatten the 6 token sheets directly; for tokens/fonts.css
 * drop its Google @import and splice the vendored base64 @font-face CSS in its
 * place; for styles.css (the aggregator that re-@imports the same 6 sheets) drop
 * ALL its @import lines so the token sheets are inlined exactly ONCE.
 *
 * @param {string[]} globalCssPaths   manifest order, e.g. ["tokens/fonts.css", ..., "styles.css"]
 * @param {string}   projectRoot      absolute project/ root
 * @param {string}   vendoredFontsCss base64 @font-face CSS (from build/vendor/fonts/fonts.base64.css)
 * @returns {string} the flattened CSS
 */
export function flattenCss(globalCssPaths, projectRoot, vendoredFontsCss) {
  let out = '/* ── Contente DS token sheets (flattened, de-duped) ── */\n';
  out += '\n/* === vendored base64 @font-face (Google @import stripped) === */\n';
  out += vendoredFontsCss + '\n';

  for (const rel of globalCssPaths) {
    const abs = join(projectRoot, rel);
    if (!existsSync(abs)) {
      throw new BuildError('CSS-SHEET-MISSING', `globalCssPaths sheet not found: ${abs}`);
    }
    let content = readFileSync(abs, 'utf8');
    const name = basename(rel);

    if (name === 'fonts.css') {
      // Drop the Google @import; the vendored @font-face is already spliced above.
      content = content.replace(GOOGLE_FONTS_IMPORT_RE, '/* Google Fonts @import stripped → vendored base64 @font-face above */');
      // Any residual @import is also stripped (defensive).
      content = content.replace(ANY_IMPORT_RE, '/* @import stripped by inliner */');
    } else if (name === 'styles.css') {
      // styles.css is a pure @import aggregator of the same 6 sheets — drop ALL
      // its @import lines so the token sheets are inlined exactly once (NEW-1).
      content = content.replace(ANY_IMPORT_RE, '/* @import stripped (aggregated sheets already inlined) */');
    } else {
      // Token sheets: strip any stray @import (none today) for safety.
      content = content.replace(ANY_IMPORT_RE, '/* @import stripped by inliner */');
    }
    out += `\n/* === ${name} === */\n${content}\n`;
  }
  return out;
}

/**
 * Enumerate the deck's assets in sorted order and classify logo (PNG) vs
 * screenshot (committed optimized JPEG). The build consumes the COMMITTED
 * optimized bytes (ADR D5: recompress-once-in-prep, host-independent determinism).
 *
 * @param {string} assetsDir absolute path to the deck assets/ dir
 * @returns {Array<{name:string, abs:string, mime:string}>}
 */
export function enumerateAssets(assetsDir) {
  if (!existsSync(assetsDir)) {
    throw new BuildError('ASSETS-MISSING', `assets/ not found: ${assetsDir}`);
  }
  const files = readdirSync(assetsDir)
    .filter((f) => /\.(png|jpe?g)$/i.test(f))
    .sort(); // explicit sort for determinism
  return files.map((name) => ({
    name,
    abs: join(assetsDir, name),
    mime: /\.png$/i.test(name) ? 'image/png' : 'image/jpeg',
  }));
}

/**
 * Build the deck's image → data-URI map from committed optimized bytes.
 * The deck references each asset BOTH as `assets/<name>` (a logo <img src> and a
 * JS-string in the data block). We must base64 the bytes that ACTUALLY exist:
 * the optimized JPEG may be committed as `image5.jpg` while the deck still
 * references `assets/image5.png`. We therefore key the map by the ORIGINAL deck
 * reference (the .png name the deck uses), resolving to whichever optimized byte
 * file is committed.
 *
 * @param {string} assetsDir absolute deck assets dir
 * @param {string} entryHtml the deck .dc.html (to discover referenced names)
 * @returns {{map: Record<string,{dataUri:string, bytes:number}>, totalBytes:number}}
 */
export function buildImageMap(assetsDir, entryHtml) {
  // Discover every assets/<name> reference in the deck (attr + JS-string).
  const refs = new Set();
  const refRe = /assets\/([A-Za-z0-9._-]+\.(?:png|jpe?g))/gi;
  let m;
  while ((m = refRe.exec(entryHtml)) !== null) refs.add(m[1]);

  if (refs.size === 0) {
    throw new BuildError('NO-ASSET-REFS', `no assets/ references found in deck — expected logos + screenshots`);
  }

  const map = {};
  let totalBytes = 0;
  for (const ref of [...refs].sort()) {
    // Resolve the committed optimized byte file: prefer a same-stem .jpg
    // (screenshot recompressed in prep), else the literal ref (logo PNG).
    const stem = ref.replace(/\.(png|jpe?g)$/i, '');
    const candidates = [
      join(assetsDir, `${stem}.jpg`),
      join(assetsDir, `${stem}.jpeg`),
      join(assetsDir, ref),
    ];
    const hit = candidates.find((p) => existsSync(p));
    if (!hit) {
      throw new BuildError('MISSING-ASSET', `deck references assets/${ref} but no committed byte file found (tried ${candidates.map((c) => basename(c)).join(', ')})`);
    }
    const mime = /\.png$/i.test(hit) ? 'image/png' : 'image/jpeg';
    const bytes = readFileSync(hit);
    totalBytes += bytes.length;
    map[ref] = { dataUri: `data:${mime};base64,${bytes.toString('base64')}`, bytes: bytes.length };
  }
  return { map, totalBytes };
}

/**
 * Substitute every assets/<name> reference (HTML attr + JS string, both quote
 * styles) with its data URI, using safeReplace (split/join — data URIs may
 * contain characters that are replacement-specials).
 */
export function inlineImages(html, imageMap) {
  let out = html;
  for (const [ref, { dataUri }] of Object.entries(imageMap)) {
    out = safeReplace(out, `src="assets/${ref}"`, `src="${dataUri}"`);
    out = safeReplace(out, `src='assets/${ref}'`, `src='${dataUri}'`);
    out = safeReplace(out, `"assets/${ref}"`, `"${dataUri}"`);
    out = safeReplace(out, `'assets/${ref}'`, `'${dataUri}'`);
  }
  return out;
}

/**
 * Wrap flattened CSS in a <style> block (style terminators escaped).
 */
export function cssStyleBlock(flatCss) {
  return `<style>\n${escapeStyleContent(flatCss)}\n</style>`;
}
