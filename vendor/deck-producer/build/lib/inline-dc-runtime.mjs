/**
 * C-runtime — inline-dc-runtime (deck-specific; Path-C-orphaned; TDD §C-runtime).
 *
 * The D1 blueprint verbatim:
 *   1. Inline React + ReactDOM UMD as <script> AHEAD of support.js (the
 *      `if (w.React && w.ReactDOM) return` guard then short-circuits the unpkg fetch).
 *   2. Rewrite `<x-import from="./deck-stage.js">` → data:text/javascript;base64,…
 *      (byte-relocation, NO transpiler).
 *   3. Inline support.js + _ds_bundle.js (from build/vendor/runtime/, NOT live
 *      exporter output — ADR D2).
 *   4. Replace <script src="./support.js"> and <script src="./ds-base.js"> with
 *      the inline script + CSS blocks.
 *   5. NEVER pre-render — ?addr/?client stay live.
 * All injection via C-guards (safeReplace + escapeScriptContent).
 */

import { readFileSync } from 'node:fs';
import {
  safeReplace,
  escapeScriptContent,
  BuildError,
} from './safe-html.mjs';

// Markers used by the A-order assertion (must be stable, searchable strings).
export const REACT_MARKER = '/* React 18.3.1 UMD — vendored (contente deck inliner) */';
export const SUPPORT_GUARD_MARKER = 'if (w.React && w.ReactDOM) return';

/**
 * Inline the dc-runtime stack into the deck HTML.
 *
 * @param {string} html        the deck .dc.html source (after image inlining)
 * @param {object} v           vendored byte paths
 * @param {string} v.reactJs    build/vendor/react.umd.js
 * @param {string} v.reactDomJs build/vendor/react-dom.umd.js
 * @param {string} deckStageJs  the deck's deck-stage.js (relocated to data: URI)
 * @param {string} supportJs    the deck's support.js
 * @param {string} dsBundleJs   project _ds_bundle.js
 * @param {string} cssBlock     the <style>…</style> block from C-brand
 * @param {string} oflNotice    the OFL HTML-comment notice (C-ofl)
 * @returns {string} HTML with the runtime inlined
 */
export function inlineDcRuntime({
  html,
  reactJsPath,
  reactDomJsPath,
  deckStageJsPath,
  supportJsPath,
  dsBundleJsPath,
  cssBlock,
  oflNotice,
}) {
  // ── React + ReactDOM UMD (escape </script in every inlined JS block) ──
  const reactJs = escapeScriptContent(readFileSync(reactJsPath, 'utf8'));
  const reactDomJs = escapeScriptContent(readFileSync(reactDomJsPath, 'utf8'));
  const supportJs = escapeScriptContent(readFileSync(supportJsPath, 'utf8'));
  const dsBundleRaw = readFileSync(dsBundleJsPath, 'utf8');
  const dsBundleJs = escapeScriptContent(dsBundleRaw);

  // ── deck-stage.js → data: URI (byte-relocation, NO transpiler) ──
  const deckStageB64 = readFileSync(deckStageJsPath).toString('base64');
  const deckStageDataUri = `data:text/javascript;base64,${deckStageB64}`;

  let out = html;

  // 1) Rewrite the x-import from="./deck-stage.js" → data: URI (both quote styles).
  const beforeXImport = out;
  out = safeReplace(out, `from="./deck-stage.js"`, `from="${deckStageDataUri}"`);
  out = safeReplace(out, `from='./deck-stage.js'`, `from='${deckStageDataUri}'`);
  if (out === beforeXImport) {
    throw new BuildError('XIMPORT-NOT-FOUND', `x-import from="./deck-stage.js" not found in deck — cannot relocate deck-stage.js`);
  }

  // 2) Replace <script src="./support.js"></script> with the inline script stack.
  //    React + ReactDOM are placed AHEAD of support.js so the guard short-circuits.
  const inlineScriptBlock =
    `${oflNotice}\n` +
    `<!-- contente deck inliner: React+ReactDOM UMD vendored — unpkg fetch dead, guard fires immediately -->\n` +
    `<script>${REACT_MARKER}\n${reactJs}\n</script>\n` +
    `<script>/* ReactDOM 18.3.1 UMD — vendored (contente deck inliner) */\n${reactDomJs}\n</script>\n` +
    `<!-- contente deck inliner: _ds_bundle.js inlined — no external fetch -->\n` +
    `<script>/* Contente DS bundle — inlined */\n${dsBundleJs}\n</script>\n` +
    `<!-- contente deck inliner: support.js inlined — REACT_URL/REACT_DOM_URL guards short-circuit -->\n` +
    `<script>/* support.js — inlined */\n${supportJs}\n</script>`;

  const beforeSupport = out;
  out = safeReplace(out, '<script src="./support.js"></script>', inlineScriptBlock);
  if (out === beforeSupport) {
    throw new BuildError('SUPPORT-TAG-NOT-FOUND', `<script src="./support.js"></script> not found in deck head`);
  }

  // 3) Replace <script src="./ds-base.js"></script> with the inline CSS block.
  //    ds-base.js dynamically links the 6+1 sheets + _ds_bundle.js; we replace it
  //    with the flattened inline CSS (the bundle is already inlined above).
  const inlineCssBlock =
    `<!-- contente deck inliner: DS token sheets + vendored fonts inlined (ds-base.js replaced) -->\n` +
    `${cssBlock}\n` +
    `<script>/* ds-base.js replaced by inliner — CSS inlined above, bundle inlined above */</script>`;

  const beforeBase = out;
  out = safeReplace(out, '<script src="./ds-base.js"></script>', inlineCssBlock);
  if (out === beforeBase) {
    throw new BuildError('DSBASE-TAG-NOT-FOUND', `<script src="./ds-base.js"></script> not found in deck`);
  }

  return out;
}

/**
 * The MC-1 canonical-address acceptance regex (producer-side parity with the
 * deck's `okAddr` check, EmailForwardingSetup.dc.html / GhlCalendarSetup.dc.html).
 * Exact-host + canonical lowercase UUIDv4 local-part. This is an ACCEPTANCE check,
 * NOT a formatter (G-PROPAGATE): the producer refuses to freeze anything the deck
 * itself would reject as un-personalized.
 */
export const CANONICAL_ADDR_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}@appointments\.contenteapp\.com$/;

/**
 * Render-then-freeze (ADR Amendment A1): inject a tiny <head> script that, when
 * the opened URL lacks an `addr` query param, SEEDS the frozen gated address (and
 * optional client name) into `location.search` via history.replaceState — BEFORE
 * the deck runtime's renderVals() reads location.search. This freezes an INPUT,
 * not the SPA (D1's live runtime is preserved): an explicit human `?addr` still
 * wins (the freeze only fires when `addr` is absent).
 *
 * The frozen `addr` MUST be a gated, MC-1-canonical address. Callers validate it
 * with CANONICAL_ADDR_RE BEFORE calling this (fail-loud ADDR-NON-CANONICAL upstream)
 * — this function assumes a validated address and only relocates bytes.
 *
 * @param {string} html  the deck HTML (post runtime-inline)
 * @param {string} addr  the gated, MC-1-canonical routing address to freeze
 * @param {string|undefined} client  optional client name to freeze alongside
 * @returns {string} HTML with the freeze script injected after <head>
 */
export function injectFrozenAddress(html, addr, client) {
  // ── JS-string-literal construction for the in-<script> freeze seed ──
  // The frozen `addr` is already MC-1-validated (no <>{}), so JSON.stringify alone
  // yields a safe literal. The `client` literal is NOT pre-validated to be free of
  // a `</script`-family sequence: JSON.stringify does NOT escape `/` or `<`, so
  // `JSON.stringify("</script>")` === `"\"</script>\""` — a verbatim `</script>`
  // that PREMATURELY CLOSES this <head> freeze script. assertScriptBalance only
  // catches the exact `</script>`; a `</script ` (space/slash, e.g. the client name
  // `Acme--></script foo`) slips past balance AND breaks the seed at runtime
  // (`Invalid or unexpected token`), so ?addr is never seeded and the clinic gets
  // the un-personalized placeholder. We therefore run escapeScriptContent over the
  // JSON literals (`</script`→`<\/script`, `<!--`→`\x3c!--`) so NO `</script`-family
  // sequence can survive inside the script context. JSON.stringify already escaped
  // the quotes/backslashes that bound the string, so the `<\/script` the escaper
  // emits stays inside the literal — a benign, correctly-decoded JS string.
  const addrLit = escapeScriptContent(JSON.stringify(addr));
  const clientLit = escapeScriptContent(JSON.stringify(typeof client === 'string' ? client : ''));
  // The freeze runs synchronously in <head>, ahead of the deck runtime scripts
  // injected at the support.js seam in <body>. It is a no-op when `addr` is
  // already present (explicit ?addr wins) and when history.replaceState is
  // unavailable (defensive; the deck then renders its placeholder).
  // NOTE: escapeScriptContent is applied ONLY to the two string LITERALS above —
  // NOT to this whole block. The block is a COMPLETE HTML snippet (an HTML comment
  // + a real <script>…</script>) injected verbatim into <head>; its OWN closing
  // `</script>` MUST stay literal or the head is corrupted. By escaping only the
  // interpolated literals we neutralize a `</script`-family sequence carried IN the
  // client/addr value while leaving this snippet's structural `</script>` intact.
  const freezeScript =
    `<!-- contente deck inliner: render-then-freeze (ADR Amendment A1) — seed gated ?addr when absent -->\n` +
    `<script>/* frozen routing-address seed — explicit ?addr still wins */\n` +
    `(function(){try{` +
    `var sp=new URLSearchParams(location.search);` +
    `if(sp.get('addr'))return;` + // explicit ?addr wins — do not overwrite
    `sp.set('addr',${addrLit});` +
    `var c=${clientLit};if(c&&!sp.get('client'))sp.set('client',c);` +
    `if(history&&history.replaceState){` +
    `history.replaceState(null,'',location.pathname+'?'+sp.toString()+location.hash);` +
    `}}catch(e){/* fail-closed: deck renders placeholder */}})();` +
    `\n</script>`;
  if (/<head\b[^>]*>/i.test(html)) {
    return html.replace(/(<head\b[^>]*>)/i, `$1\n${freezeScript}`);
  }
  // No <head> (defensive): prepend before <body> or at document start.
  return safeReplace(html, '<body', `${freezeScript}\n<body`);
}

/**
 * Inject a <title> into <head> (client-clean title). Idempotent: replaces an
 * existing <title> or inserts one after <head>.
 */
export function injectTitle(html, title) {
  const safeTitle = title.replace(/[<>]/g, '');
  if (/<title>[\s\S]*?<\/title>/i.test(html)) {
    return html.replace(/<title>[\s\S]*?<\/title>/i, `<title>${safeTitle}</title>`);
  }
  return safeReplace(html, '<head>', `<head>\n<title>${safeTitle}</title>`);
}
