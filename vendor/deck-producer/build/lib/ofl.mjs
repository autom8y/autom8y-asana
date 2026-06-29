/**
 * C-ofl — SIL OFL-1.1 compliance (ADR D6 / HANDOFF C1).
 *
 * Two mandatory artifacts before any client-distribution emit:
 *   1. A human-readable OFL-1.1 notice injected into EVERY emitted deck.
 *   2. A LICENSE-fonts.txt present in the package (validated here; the build
 *      refuses to emit if it is absent).
 * (inline.mjs:271-284 emitted only the HTML comment; this closes C1.)
 */

import { existsSync } from 'node:fs';
import { BuildError } from './safe-html.mjs';

/**
 * The human-readable OFL notice injected into every deck (an HTML comment in
 * <head>, so it travels with the redistributed fonts but does not render).
 */
export const OFL_NOTICE = `<!--
  ============================================================================
  EMBEDDED WEBFONT LICENSE NOTICE — SIL Open Font License, Version 1.1
  ============================================================================
  This file embeds the following open-source fonts as base64 @font-face data,
  redistributed under the SIL Open Font License, Version 1.1
  (https://openfontlicense.org/open-font-license-official-text/):

    • Plus Jakarta Sans — Copyright 2020 The Plus Jakarta Sans Project Authors
    • Spectral          — Copyright 2017 The Spectral Project Authors
    • JetBrains Mono    — Copyright 2020 The JetBrains Mono Project Authors

  The full license text ships alongside this deck as LICENSE-fonts.txt.
  ============================================================================
-->`;

/**
 * Pre-emit gate: assert LICENSE-fonts.txt exists in the package. Fails the build
 * non-zero (no silent emit) if absent.
 */
export function assertLicenseFilePresent(licensePath) {
  if (!existsSync(licensePath)) {
    throw new BuildError(
      'OFL-LICENSE-MISSING',
      `LICENSE-fonts.txt not found at ${licensePath}. ` +
      `The OFL requires the license to travel with the redistributed fonts (ADR D6 / C1).`
    );
  }
}
