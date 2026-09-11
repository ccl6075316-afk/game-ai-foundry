import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const DEFAULT_RUNTIME = path.join(REPO_ROOT, "gui", "runtime", "pi");
const ENTRY_REL = path.join(
  "node_modules",
  "@earendil-works",
  "pi-coding-agent",
  "dist",
  "cli.js"
);
const RPC_ENTRY_REL = path.join(
  "node_modules",
  "@earendil-works",
  "pi-coding-agent",
  "dist",
  "rpc-entry.js"
);

/**
 * @param {string} root
 * @returns {boolean}
 */
function hasPiCli(root) {
  return existsSync(path.join(root, ENTRY_REL));
}

/**
 * Dev: gui/runtime/pi; override via GAMEFACTORY_PI_ROOT.
 * @returns {string | null}
 */
export function resolvePiRuntimeRoot() {
  const env = (process.env.GAMEFACTORY_PI_ROOT || "").trim();
  if (env && hasPiCli(env)) {
    return path.resolve(env);
  }
  if (hasPiCli(DEFAULT_RUNTIME)) {
    return DEFAULT_RUNTIME;
  }
  return null;
}

/**
 * @param {string | null | undefined} [root]
 * @returns {Record<string, unknown> | null}
 */
export function loadEmbedManifest(root) {
  const base = root || resolvePiRuntimeRoot();
  if (!base) {
    return null;
  }
  const manifestPath = path.join(base, "embed-manifest.json");
  if (!existsSync(manifestPath)) {
    return null;
  }
  try {
    const data = JSON.parse(readFileSync(manifestPath, "utf8"));
    return data && typeof data === "object" ? data : null;
  } catch {
    return null;
  }
}

/**
 * @param {string | null | undefined} [root]
 * @returns {string | null}
 */
export function resolvePiCliJs(root) {
  const base = root || resolvePiRuntimeRoot();
  if (!base) {
    return null;
  }
  const manifest = loadEmbedManifest(base);
  const entryRel = typeof manifest?.entry === "string" ? manifest.entry : ENTRY_REL;
  const cliPath = path.join(base, entryRel);
  return existsSync(cliPath) ? cliPath : null;
}

/**
 * @param {string | null | undefined} [root]
 * @returns {string | null}
 */
export function resolvePiRpcEntry(root) {
  const base = root || resolvePiRuntimeRoot();
  if (!base) {
    return null;
  }
  const rpcPath = path.join(base, RPC_ENTRY_REL);
  return existsSync(rpcPath) ? rpcPath : null;
}

/**
 * @param {object} [opts]
 * @param {"rpc-entry"|"cli-rpc"} [opts.mode]
 * @param {string | null | undefined} [opts.root]
 * @param {string[]} [opts.extraArgs]
 * @returns {{ entry: string, args: string[], cwd: string } | null}
 */
export function resolvePiRpcSpawnLaunch(opts = {}) {
  const root = opts.root || resolvePiRuntimeRoot();
  if (!root) {
    return null;
  }
  const mode = opts.mode || "rpc-entry";
  const extraArgs = opts.extraArgs || [];
  if (mode === "rpc-entry") {
    const entry = resolvePiRpcEntry(root);
    if (!entry) {
      return null;
    }
    return { entry, args: [...extraArgs], cwd: root };
  }
  const entry = resolvePiCliJs(root);
  if (!entry) {
    return null;
  }
  return { entry, args: ["--mode", "rpc", ...extraArgs], cwd: root };
}

export { DEFAULT_RUNTIME, ENTRY_REL, REPO_ROOT, RPC_ENTRY_REL };
