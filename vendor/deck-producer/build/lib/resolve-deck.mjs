/**
 * C-resolve — deck folder → resolved, validated input set (TDD §C-resolve).
 *
 * Replaces the spike's hardcoded DECK_ROOT/DS_ROOT (inline.mjs:42-45) with a
 * manifest-driven contract. Resolves globalCssPaths relative to the project
 * root (NOT hardcoded), identifies the deck entry .dc.html from the manifest,
 * validates the @ds-bundle namespace AGREES across the 3 hardcoded sites
 * (T4-a probe: E5 manifest header, E6 window assignment, E7 consumer tags),
 * and COLLECTS ALL ERRORS before halting (not throw-on-first — inline.mjs:81
 * production gap, HANDOFF §2.1).
 */

import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, basename, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BuildError } from './safe-html.mjs';

/**
 * Resolve the @autom8y/contente-tokens package's canonical CSS directory and
 * remap a manifest globalCssPaths list onto package-relative basenames.
 *
 * The brand CSS is owned by the package (the single source of truth); the deck
 * build consumes the PACKAGE bytes, not in-tree copies. The package ships the 7
 * sheets flat under src/css/ — so we resolve that dir via the package's `cssDir`
 * export and rewrite each manifest rel (e.g. "tokens/colors.css", "styles.css")
 * to its BASENAME ("colors.css", "styles.css"). flattenCss() then resolves
 * join(cssRoot, basename) onto package bytes WITHOUT any change to its signature
 * or its de-dup branching (which keys on basename(rel) — unchanged by this).
 *
 * Byte-invariant: the package sheets are byte-identical to the retired in-tree
 * sheets (sha256 parity proven at build rung), so same bytes in -> same golden
 * hash out. import.meta.resolve is used so resolution honours the file: dep /
 * node_modules link without hardcoding a path.
 *
 * @param {string[]} globalCssPaths manifest order rels
 * @returns {{cssRoot: string, cssRels: string[]}}
 */
function resolvePackageCss(globalCssPaths) {
  let cssDir;
  try {
    // index.mjs exports `cssDir`; resolving the barrel and walking to src/css is
    // robust to the package's internal layout via the exports map.
    const barrelUrl = import.meta.resolve('@autom8y/contente-tokens');
    const barrelPath = fileURLToPath(barrelUrl);
    cssDir = join(dirname(barrelPath), 'src', 'css');
  } catch (e) {
    throw new BuildError(
      'TOKENS-PKG-MISSING',
      `@autom8y/contente-tokens not resolvable — is the file: dependency installed? (${e.message})`
    );
  }
  if (!existsSync(cssDir)) {
    throw new BuildError('TOKENS-CSS-MISSING', `@autom8y/contente-tokens CSS dir not found: ${cssDir}`);
  }
  const cssRels = globalCssPaths.map((rel) => basename(rel));
  for (const r of cssRels) {
    if (!existsSync(join(cssDir, r))) {
      throw new BuildError('TOKENS-SHEET-MISSING', `package sheet not found: ${join(cssDir, r)}`);
    }
  }
  return { cssRoot: cssDir, cssRels };
}

/**
 * Resolve and validate a deck against the project manifest.
 *
 * @param {object} opts
 * @param {string} opts.deckDir       relative deck folder, e.g. "templates/ghl-calendar-setup"
 * @param {string} opts.projectRoot   absolute path to the project/ root
 * @param {string} opts.outputTitle   <title> for the emitted deck
 * @param {string} opts.outputFilename client-clean output filename, e.g. "GhlCalendarSetup.html"
 * @returns {object} resolved input contract
 */
export function resolveDeck({ deckDir, projectRoot, outputTitle, outputFilename }) {
  const errors = [];
  const collect = (cond, code, msg) => { if (!cond) errors.push(`[${code}] ${msg}`); };

  const manifestPath = join(projectRoot, '_ds_manifest.json');
  collect(existsSync(manifestPath), 'MANIFEST-MISSING', `_ds_manifest.json not found at ${manifestPath}`);

  let manifest = null;
  if (existsSync(manifestPath)) {
    try {
      manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
    } catch (e) {
      collect(false, 'MANIFEST-PARSE', `_ds_manifest.json is not valid JSON: ${e.message}`);
    }
  }

  // E5 — namespace from the manifest header.
  const nsManifest = manifest && manifest.namespace;
  collect(!!nsManifest, 'MANIFEST-NAMESPACE', 'manifest.namespace missing');

  // globalCssPaths resolved relative to project root.
  const globalCssPaths = (manifest && Array.isArray(manifest.globalCssPaths)) ? manifest.globalCssPaths : [];
  collect(globalCssPaths.length > 0, 'CSS-PATHS', 'manifest.globalCssPaths missing or empty');

  const absDeckDir = join(projectRoot, deckDir);
  collect(existsSync(absDeckDir), 'DECK-DIR-MISSING', `deck folder not found: ${absDeckDir}`);

  // Identify the deck entry .dc.html from the manifest templates[].entryPath,
  // falling back to a single *.dc.html in the deck folder.
  let entryPath = null;
  if (manifest && Array.isArray(manifest.templates)) {
    const t = manifest.templates.find((x) => x.folder === deckDir);
    if (t && t.entryPath) entryPath = join(projectRoot, t.entryPath);
  }
  if (!entryPath && existsSync(absDeckDir)) {
    const dc = readdirSync(absDeckDir).filter((f) => f.endsWith('.dc.html'));
    if (dc.length === 1) entryPath = join(absDeckDir, dc[0]);
    else collect(false, 'ENTRY-AMBIGUOUS', `expected exactly one *.dc.html in ${absDeckDir}, found ${dc.length}`);
  }
  collect(!!entryPath && existsSync(entryPath), 'ENTRY-MISSING', `deck entry .dc.html not found (manifest entryPath / single *.dc.html)`);

  // Sidecars + bundle.
  const supportJs = join(absDeckDir, 'support.js');
  const deckStageJs = join(absDeckDir, 'deck-stage.js');
  const dsBaseJs = join(absDeckDir, 'ds-base.js');
  const dsBundleJs = join(projectRoot, '_ds_bundle.js');
  const assetsDir = join(absDeckDir, 'assets');
  collect(existsSync(supportJs), 'SUPPORT-MISSING', `support.js not found: ${supportJs}`);
  collect(existsSync(deckStageJs), 'DECKSTAGE-MISSING', `deck-stage.js not found: ${deckStageJs}`);
  collect(existsSync(dsBundleJs), 'BUNDLE-MISSING', `_ds_bundle.js not found: ${dsBundleJs}`);
  collect(existsSync(assetsDir), 'ASSETS-MISSING', `assets/ not found: ${assetsDir}`);

  // RK-1 — assert zero .jsx/.tsx runtime x-imports (today: 0). HALT if found.
  let entryHtml = '';
  if (entryPath && existsSync(entryPath)) {
    entryHtml = readFileSync(entryPath, 'utf8');
    const jsxImports = entryHtml.match(/from\s*=\s*["'][^"']+\.(?:jsx|tsx)["']/gi) || [];
    collect(jsxImports.length === 0, 'JSX-XIMPORT', `runtime .jsx/.tsx x-imports found (Babel phone-home risk RK-1): ${jsxImports.slice(0, 3).join(', ')}`);
  }

  // T4-a — namespace agreement across the 3 hardcoded sites.
  // E6 window assignment + E7 manifest @ds-bundle header live in _ds_bundle.js;
  // E7 consumer tags live in the .dc.html.
  if (nsManifest) {
    if (existsSync(dsBundleJs)) {
      const bundle = readFileSync(dsBundleJs, 'utf8');
      // @ds-bundle JSON header comment (line 1) carries "namespace":"...".
      collect(
        new RegExp(`"namespace"\\s*:\\s*"${escapeRe(nsManifest)}"`).test(bundle),
        'NS-DRIFT-HEADER',
        `@ds-bundle header namespace disagrees with manifest.namespace "${nsManifest}"`
      );
      // window assignment: window.<namespace> = ...
      collect(
        new RegExp(`window\\.${escapeRe(nsManifest)}\\b`).test(bundle) ||
        new RegExp(`window\\[["']${escapeRe(nsManifest)}["']\\]`).test(bundle),
        'NS-DRIFT-WINDOW',
        `_ds_bundle.js window assignment for "${nsManifest}" not found (E6 drift)`
      );
    }
    // consumer tags in the deck.
    collect(
      entryHtml.includes(`component-from-global-scope="${nsManifest}.`) ||
      entryHtml.includes(`component-from-global-scope='${nsManifest}.`),
      'NS-DRIFT-CONSUMER',
      `deck has no component-from-global-scope="${nsManifest}.*" consumer tags (E7 drift)`
    );
  }

  if (errors.length > 0) {
    throw new BuildError('RESOLVE-FAILED', `deck "${deckDir}" failed validation:\n  ${errors.join('\n  ')}`);
  }

  // Source the brand CSS from the owned @autom8y/contente-tokens package (the
  // single source of truth), not in-tree copies. cssRoot + cssRels feed
  // flattenCss with package bytes; flattenCss itself is unchanged.
  const { cssRoot, cssRels } = resolvePackageCss(globalCssPaths);

  return {
    deckDir,
    absDeckDir,
    projectRoot,
    namespace: nsManifest,
    globalCssPaths,
    cssRoot,
    cssRels,
    entryPath,
    entryHtml,
    supportJs,
    deckStageJs,
    dsBaseJs,
    dsBundleJs,
    assetsDir,
    outputTitle,
    outputFilename,
    deckName: basename(entryPath || '', '.dc.html'),
  };
}

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
