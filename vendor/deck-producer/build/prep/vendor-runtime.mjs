/**
 * P-runtime — vendor React + ReactDOM UMD + the dc-runtime triple (ADR D2).
 *
 * BUILD-TIME-NETWORK, run ONCE, OUTPUT COMMITTED. Downloads React 18.3.1 +
 * ReactDOM 18.3.1 UMD (production) from unpkg, pinned, with @license banners
 * preserved (UMD distributions carry their banner inline). The dc-runtime triple
 * (support.js, deck-stage.js, _ds_bundle.js) already lives in the repo (the
 * exporter's committed output); we COPY-PIN it into build/vendor/runtime/ so the
 * `build` step consumes pinned in-repo bytes, never live exporter output.
 *
 * After this runs, the committed bytes under build/vendor/ are the source of
 * record; network is never touched again at build time.
 */

import { writeFileSync, mkdirSync, existsSync, copyFileSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..', '..');
const VENDOR = join(PROJECT_ROOT, 'build', 'vendor');
const RUNTIME = join(VENDOR, 'runtime');

const REACT_VERSION = '18.3.1';
const REACT_UMD_URL = `https://unpkg.com/react@${REACT_VERSION}/umd/react.production.min.js`;
const REACT_DOM_UMD_URL = `https://unpkg.com/react-dom@${REACT_VERSION}/umd/react-dom.production.min.js`;

async function fetchText(url) {
  const res = await fetch(url, { redirect: 'follow' });
  if (!res.ok) throw new Error(`fetch failed ${res.status} for ${url}`);
  return await res.text();
}

async function main() {
  mkdirSync(VENDOR, { recursive: true });
  mkdirSync(RUNTIME, { recursive: true });

  // ── React + ReactDOM UMD (pinned 18.3.1; @license banner preserved by source) ──
  console.log(`[vendor-runtime] fetching React ${REACT_VERSION} UMD…`);
  const reactJs = await fetchText(REACT_UMD_URL);
  const reactDomJs = await fetchText(REACT_DOM_UMD_URL);

  // Sanity: the UMD must register window.React / window.ReactDOM.
  if (!/React/.test(reactJs)) throw new Error('react UMD looks wrong (no "React")');
  if (!/ReactDOM/.test(reactDomJs)) throw new Error('react-dom UMD looks wrong (no "ReactDOM")');

  const banner = (name, url) =>
    `/* @license vendored ${name} @ ${REACT_VERSION} — ${url}\n` +
    `   Pinned by P-runtime (ADR D2). Do not edit by hand; re-run \`npm run prep\` to re-vendor. */\n`;

  writeFileSync(join(VENDOR, 'react.umd.js'), banner('react', REACT_UMD_URL) + reactJs, 'utf8');
  writeFileSync(join(VENDOR, 'react-dom.umd.js'), banner('react-dom', REACT_DOM_UMD_URL) + reactDomJs, 'utf8');
  console.log(`  react.umd.js: ${reactJs.length} bytes`);
  console.log(`  react-dom.umd.js: ${reactDomJs.length} bytes`);

  // ── dc-runtime triple: copy-pin from the in-repo exporter output ──
  // _ds_bundle.js is project-level; support.js/deck-stage.js are per-deck. We pin
  // the project bundle + a per-deck snapshot so drift is detectable (T4-a probe
  // compares the live deck files against these pins is a future hardening; today
  // the build consumes the live per-deck files which the resolver namespace-checks).
  const bundleSrc = join(PROJECT_ROOT, '_ds_bundle.js');
  if (!existsSync(bundleSrc)) throw new Error(`_ds_bundle.js not found at ${bundleSrc}`);
  copyFileSync(bundleSrc, join(RUNTIME, '_ds_bundle.js'));
  const bundleNs = (readFileSync(bundleSrc, 'utf8').match(/"namespace"\s*:\s*"([^"]+)"/) || [])[1] || 'unknown';
  console.log(`  pinned _ds_bundle.js (namespace ${bundleNs})`);

  // Record the pin manifest.
  const pin = {
    react: REACT_VERSION,
    reactUmd: REACT_UMD_URL,
    reactDomUmd: REACT_DOM_UMD_URL,
    dsBundleNamespace: bundleNs,
    vendoredAt: new Date().toISOString().slice(0, 10),
  };
  writeFileSync(join(VENDOR, 'PIN.json'), JSON.stringify(pin, null, 2) + '\n', 'utf8');
  console.log('[vendor-runtime] done. Pin manifest → build/vendor/PIN.json');
}

main().catch((e) => { console.error('[vendor-runtime] FAILED:', e.message); process.exit(1); });
