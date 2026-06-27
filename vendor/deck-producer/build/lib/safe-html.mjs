/**
 * C-guards — the regression cures + build-time assertions (ADR D3, TDD §C-guards).
 *
 * These are ported VERBATIM from the validated reference (inline.mjs:60-76,
 * 297-378). Every assertion fails the build non-zero. Their authority is the
 * live-browser instrument (static checks were proven structurally blind to the
 * `$&` premature-close bug once — N3-spike.md:379); these are the cheap fast-fail
 * in front of the slow objective gate, kept as defense in depth.
 */

/**
 * BuildError — a named, non-zero-exit build failure. The CLI catches this and
 * exits 1 WITHOUT writing an output file (fail-loud, no silent emit).
 */
export class BuildError extends Error {
  constructor(code, message) {
    super(`${code} — ${message}`);
    this.name = 'BuildError';
    this.code = code;
  }
}

/**
 * Escape script terminators inside JS content destined for a <script> block.
 *   </script  →  <\/script   (deck-stage.js JSDoc contains a literal </script>)
 *   <!--      →  \x3c!--      (HTML comment start inside a script can confuse parsers)
 * We do NOT escape --> because a standalone --> inside a script body is benign in
 * modern parsers. (inline.mjs:60-65)
 */
export function escapeScriptContent(src) {
  return src
    .replace(/<\/script/gi, '<\\/script')
    .replace(/<!--/g, '\\x3c!--');
}

/**
 * Escape style terminators inside CSS content destined for a <style> block.
 *   </style → <\/style   (belt-and-suspenders; benign but guarded).
 */
export function escapeStyleContent(src) {
  return src.replace(/<\/style/gi, '<\\/style');
}

/**
 * Safe string replacement: replaces `needle` (a literal string) with `payload`
 * using split/join so NONE of payload's characters are ever treated as
 * String.prototype.replace replacement-specials ($&, $1, $`, $', $$).
 * This is THE cure for the react.production.min.js `replace(da,"$&/")` footgun.
 * (inline.mjs:73-76)
 */
export function safeReplace(html, needle, payload) {
  return html.split(needle).join(payload);
}

/**
 * Build a STRUCTURAL copy of the HTML: replace every <script ...>...</script>
 * CONTENT with empty, keeping only the open/close tags. This strips inline JS
 * (which may contain string literals like "<script>" in minified react-dom)
 * from any tag-balance count. (inline.mjs:297)
 */
function structuralCopy(html) {
  // \s* before > makes the close-tag match whitespace-tolerant: </script > is valid HTML.
  // Without \s* the regex fails to strip </script > leaving JS content un-stripped
  // and miscounting tag balance (CodeQL js/bad-tag-filter #236).
  return html.replace(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi, '<script$1></script>');
}

/**
 * A-balance — balanced <script>/</script> on the STRUCTURAL copy.
 * Throws BuildError on imbalance. (inline.mjs:297-313)
 */
export function assertScriptBalance(html) {
  const structural = structuralCopy(html);
  const opens = (structural.match(/<script\b/gi) || []).length;
  // \s* keeps close-tag counter consistent with structuralCopy's whitespace-tolerant regex
  // so opens/closes stay balanced under </script > variants (CodeQL js/bad-tag-filter #236).
  const closes = (structural.match(/<\/script\s*>/gi) || []).length;
  if (opens !== closes) {
    const rawCloses = (html.match(/<\/script\s*>/gi) || []).length;
    const escCloses = (html.match(/<\\\/script>/gi) || []).length;
    throw new BuildError(
      'SCRIPT-IMBALANCE',
      `unbalanced <script> tags (structural): ${opens} opens vs ${closes} closes. ` +
      `This indicates a </script premature close. ` +
      `Full html: </script>=${rawCloses}, escaped <\\/script>=${escCloses}. ` +
      `escapeScriptContent() must catch every occurrence.`
    );
  }
  return { opens, closes };
}

/**
 * A-no-src — zero surviving `<script src=` in the structural output.
 * (inline.mjs:323-331)
 */
export function assertNoScriptSrc(html) {
  const structural = structuralCopy(html);
  const remaining = structural.match(/<script[^>]+\bsrc\s*=/gi) || [];
  if (remaining.length > 0) {
    throw new BuildError(
      'SCRIPT-SRC-SURVIVED',
      `${remaining.length} <script src= still present in output: ${remaining.slice(0, 5).join(' | ')}`
    );
  }
  return remaining.length;
}

/**
 * A-no-rel — zero surviving relative `from="./"` / `src="./*.js|css"` /
 * `href="./*.js|css"` and zero surviving external CDN refs in HTML (scripts
 * stripped so dead minified-JS string literals don't false-positive).
 * (inline.mjs:335-360)
 */
export function assertNoRelativeRefs(html) {
  // Strip <script>...</script> so dead string literals inside minified JS are excluded.
  // \s* before > matches </script > (whitespace before close >) — consistent with
  // structuralCopy fix (CodeQL js/bad-tag-filter #235).
  const scan = html.replace(/<script\b[^>]*>[\s\S]*?<\/script\s*>/gi, '<script>/*stripped*/</script>');
  const patterns = [
    { re: /from\s*=\s*["']\.\/[^"']+\.(?:js|mjs)["']/i, label: 'relative x-import from="./*.js"' },
    { re: /src\s*=\s*["']\.\/[^"']+\.(?:js|css)["']/i, label: 'relative .js/.css src attribute' },
    { re: /href\s*=\s*["']\.\/[^"']+\.(?:js|css)["']/i, label: 'relative .js/.css href attribute' },
    { re: /https?:\/\/unpkg\.com/i, label: 'unpkg.com in HTML' },
    { re: /https?:\/\/fonts\.googleapis\.com/i, label: 'fonts.googleapis.com in HTML' },
    { re: /https?:\/\/fonts\.gstatic\.com/i, label: 'fonts.gstatic.com in HTML' },
    { re: /@import\s+url\(\s*["']?https?:\/\//i, label: '@import url(https://...) in CSS' },
  ];
  const found = [];
  for (const { re, label } of patterns) {
    const m = scan.match(re);
    if (m) found.push(`${label}: ${m[0]}`);
  }
  if (found.length > 0) {
    throw new BuildError('EXTERNAL-REF-SURVIVED', `surviving external/relative refs:\n  ${found.join('\n  ')}`);
  }
  return 0;
}

/**
 * A-order — the inlined React UMD block index must precede the support.js guard
 * index, or the guard will NOT short-circuit the unpkg fetch. (inline.mjs:370-378)
 */
export function assertReactBeforeGuard(html, reactMarker, guardMarker) {
  const reactIdx = html.indexOf(reactMarker);
  const guardIdx = html.indexOf(guardMarker);
  if (reactIdx === -1) {
    throw new BuildError('REACT-NOT-INLINED', `React UMD marker not found in output: "${reactMarker}"`);
  }
  if (guardIdx !== -1 && guardIdx < reactIdx) {
    throw new BuildError(
      'REACT-ORDER',
      'React guard appears BEFORE the inlined React block — the unpkg fetch will NOT be short-circuited.'
    );
  }
  return { reactIdx, guardIdx };
}

/**
 * A-bundle — the @ds-bundle namespace must be present in the output (the deck's
 * components resolve against window.<namespace>). (inline.mjs:97-104, 136-141)
 */
export function assertBundleNamespace(html, namespace) {
  if (!html.includes(namespace)) {
    throw new BuildError(
      'NAMESPACE-MISSING',
      `@ds-bundle namespace "${namespace}" absent from emitted deck. ` +
      `If you mutated the namespace (broken fixture), this is the expected RED signal.`
    );
  }
}
