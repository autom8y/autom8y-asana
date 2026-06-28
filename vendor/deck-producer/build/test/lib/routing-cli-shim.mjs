/**
 * routing-cli-shim — a contract-faithful, REAL-PYTHON test double for the
 * `autom8y-routing-address` console-script (TDD §3.3, §6 stub-CLI note).
 *
 * HONESTY POSTURE (preferred per dispatch): this shim does NOT reimplement the
 * gate. It invokes the REAL `format_routing_address` Python function from the
 * #719 branch source (`feat/sdk-routing-address-formatter`) — extracted verbatim
 * from git into a temp file — via `python3`. So the offline proof exercises the
 * actual gate logic (canonical-UUIDv4 accept / ValueError-RAISE reject), not a
 * mirror of it. The ONLY thing S4 must validate live is that the real installed
 * console-script (autom8y-core [project.scripts]) is wired onto PATH after #719
 * merges — the gate LOGIC is the same code this shim runs.
 *
 * The shim's argv/stdout/exit contract is byte-faithful to TDD §3.3:
 *   autom8y-routing-address <guid>
 *     success: prints "{guid}@appointments.contenteapp.com\n" to stdout; exit 0
 *     failure: diagnostic to stderr; NOTHING to stdout; exit 1 (gate RAISE)
 *
 * If the #719 branch source is NOT reachable (autom8y repo absent / branch gone),
 * `installRoutingCliShim` throws — the harness then SKIPS the CLI-relay checks and
 * says so explicitly, rather than silently substituting a weaker double. The
 * MC-1 and render-then-freeze proofs do NOT depend on the CLI (they pass --addr
 * directly), so they still run.
 */

import { execFileSync } from 'node:child_process';
import {
  mkdtempSync, writeFileSync, chmodSync, rmSync, existsSync,
} from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

// Where the #719 gate source lives (branch-pinned; NOT on autom8y main as of
// 2026-06-24 — UV-P-1). We read it via `git show` so we never depend on a
// working-tree checkout of the branch.
const AUTOM8Y_REPO = '/Users/tomtenuta/Code/a8/repos/autom8y';
const GATE_BRANCH = 'feat/sdk-routing-address-formatter';
const GATE_PATH = 'sdks/python/autom8y-core/src/autom8y_core/helpers/routing.py';

/**
 * Extract the real #719 gate source from git into `dir/routing.py`.
 * @throws if the autom8y repo or the branch:path is unreachable.
 * @returns {string} absolute path to the extracted gate source.
 */
function extractRealGate(dir) {
  if (!existsSync(AUTOM8Y_REPO)) {
    throw new Error(`autom8y repo not found at ${AUTOM8Y_REPO}; cannot source the real #719 gate`);
  }
  let src;
  try {
    src = execFileSync('git', ['-C', AUTOM8Y_REPO, 'show', `${GATE_BRANCH}:${GATE_PATH}`], {
      encoding: 'utf8',
    });
  } catch (e) {
    throw new Error(`could not git-show ${GATE_BRANCH}:${GATE_PATH} (#719 gate): ${e.message.split('\n')[0]}`);
  }
  if (!src.includes('def format_routing_address')) {
    throw new Error('#719 gate source did not contain format_routing_address — refusing to proceed');
  }
  const gateFile = join(dir, 'routing.py');
  writeFileSync(gateFile, src, 'utf8');
  return gateFile;
}

/**
 * Install a real-Python `autom8y-routing-address` shim on a fresh temp dir and
 * return { binDir, gateFile, cleanup }. Prepend `binDir` to PATH (or point
 * AUTOM8Y_ROUTING_ADDRESS_CLI at the script) to exercise gatedAddressForGuid.
 *
 * The shim is a python3 script with a shebang; it imports the extracted real
 * gate by file path and calls format_routing_address(argv[1]). On ValueError it
 * writes the diagnostic to stderr, prints nothing to stdout, and exits 1.
 *
 * @returns {{ binDir: string, cliPath: string, gateFile: string, cleanup: () => void }}
 */
export function installRoutingCliShim() {
  const dir = mkdtempSync(join(tmpdir(), 'autom8y-routing-cli-'));
  const gateFile = extractRealGate(dir);

  // The shim runs the REAL gate. importlib loads the extracted routing.py by
  // path; no autom8y package install needed (the gate only imports stdlib uuid).
  const shim =
    `#!/usr/bin/env python3\n` +
    `import sys, importlib.util\n` +
    `_spec = importlib.util.spec_from_file_location("autom8y_routing_gate", ${JSON.stringify(gateFile)})\n` +
    `_m = importlib.util.module_from_spec(_spec)\n` +
    `_spec.loader.exec_module(_m)\n` +
    `def main():\n` +
    `    if len(sys.argv) != 2:\n` +
    `        sys.stderr.write("usage: autom8y-routing-address <guid>\\n")\n` +
    `        sys.exit(2)\n` +
    `    try:\n` +
    `        addr = _m.format_routing_address(sys.argv[1])\n` +
    `    except ValueError as e:\n` +
    `        # gate RAISED — diagnostic to stderr, NOTHING to stdout, exit 1.\n` +
    `        sys.stderr.write(str(e) + "\\n")\n` +
    `        sys.exit(1)\n` +
    `    sys.stdout.write(addr + "\\n")\n` +
    `    sys.exit(0)\n` +
    `if __name__ == "__main__":\n` +
    `    main()\n`;

  const cliPath = join(dir, 'autom8y-routing-address');
  writeFileSync(cliPath, shim, 'utf8');
  chmodSync(cliPath, 0o755);

  return {
    binDir: dir,
    cliPath,
    gateFile,
    cleanup: () => rmSync(dir, { recursive: true, force: true }),
  };
}
