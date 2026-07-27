import path from "node:path";

/** @typedef {{ id: string, root_abs: string, display_name?: string, godot_rel?: string, brief_rel?: string }} ExternalEntry */

/**
 * Parse virtual key `external:<id>/…` into components.
 * @param {string | null | undefined} rel
 * @returns {{ raw: string, extId: string, sub: string } | null}
 */
export function parseExternalVirtual(rel) {
  if (!rel || typeof rel !== "string") return null;
  const raw = rel.replace(/\\/g, "/").replace(/^\/+/, "");
  if (!raw.toLowerCase().startsWith("external:")) return null;
  const rest = raw.slice("external:".length);
  const slash = rest.indexOf("/");
  const extId = slash >= 0 ? rest.slice(0, slash) : rest;
  const sub = slash >= 0 ? rest.slice(slash + 1) : "";
  if (!extId || sub.includes("..")) return null;
  return { raw, extId, sub };
}

/**
 * @param {string | null | undefined} rel
 * @returns {boolean}
 */
export function isExternalVirtualRel(rel) {
  return parseExternalVirtual(rel) != null;
}

/**
 * Resolve virtual external key to absolute path under registered root_abs.
 * @param {string} rel
 * @param {(extId: string) => ExternalEntry | null | undefined} getEntryById
 * @returns {{ full: string, rel: string, entry: ExternalEntry, rootAbs: string } | null}
 */
export function resolveExternalAbs(rel, getEntryById) {
  const parsed = parseExternalVirtual(rel);
  if (!parsed) return null;
  const entry = getEntryById(parsed.extId);
  if (!entry?.root_abs) return null;
  const rootAbs = path.resolve(String(entry.root_abs));
  const full = parsed.sub ? path.resolve(rootAbs, parsed.sub) : rootAbs;
  if (full !== rootAbs && !full.startsWith(rootAbs + path.sep)) return null;
  return { full, rel: parsed.raw, entry, rootAbs };
}

/**
 * Normalize repo-relative path (strip ../ and ./).
 * @param {string | null | undefined} relPath
 * @returns {string}
 */
export function normalizeRepoRel(relPath) {
  return String(relPath || "")
    .replace(/\\/g, "/")
    .replace(/^\.\.\//, "")
    .replace(/^\.\//, "");
}

/**
 * CLI cwd is cli/ — external paths use absolute; repo paths use ../rel.
 * @param {string} rel
 * @param {{ resolvedExternal: ReturnType<typeof resolveExternalAbs>, repoRoot: string }} ctx
 * @returns {string}
 */
export function cliArgForResolved(rel, { resolvedExternal, repoRoot }) {
  if (resolvedExternal) return resolvedExternal.full;
  return path.join("..", normalizeRepoRel(rel));
}

/**
 * Absolute filesystem path for mkdir/read/write.
 * @param {string} rel
 * @param {{ resolvedExternal: ReturnType<typeof resolveExternalAbs>, repoRoot: string }} ctx
 * @returns {string}
 */
export function absForResolved(rel, { resolvedExternal, repoRoot }) {
  if (resolvedExternal) return resolvedExternal.full;
  return path.join(repoRoot, normalizeRepoRel(rel));
}
