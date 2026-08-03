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
 * Normalize repo-relative path. Rejects any `..` segment (including mid-path).
 * Returns "" for empty/invalid input — callers must treat empty as reject.
 * @param {string | null | undefined} relPath
 * @returns {string}
 */
export function normalizeRepoRel(relPath) {
  const raw = String(relPath || "")
    .replace(/\\/g, "/")
    .replace(/^\/+/, "");
  if (!raw) return "";
  const parts = raw.split("/").filter((p) => p && p !== ".");
  if (parts.some((p) => p === "..")) return "";
  return parts.join("/");
}

/**
 * CLI cwd is cli/ — external paths use absolute; repo paths use ../rel.
 * @param {string} rel
 * @param {{ resolvedExternal: ReturnType<typeof resolveExternalAbs>, repoRoot: string }} ctx
 * @returns {string}
 */
export function cliArgForResolved(rel, { resolvedExternal, repoRoot }) {
  if (resolvedExternal) return resolvedExternal.full;
  const norm = normalizeRepoRel(rel);
  if (!norm) {
    throw new Error(`invalid repo-relative path: ${rel}`);
  }
  const root = path.resolve(repoRoot);
  const full = path.resolve(root, norm);
  if (full !== root && !full.startsWith(root + path.sep)) {
    throw new Error(`path outside repo: ${rel}`);
  }
  return path.join("..", norm);
}

/**
 * Absolute filesystem path for mkdir/read/write.
 * @param {string} rel
 * @param {{ resolvedExternal: ReturnType<typeof resolveExternalAbs>, repoRoot: string }} ctx
 * @returns {string}
 */
export function absForResolved(rel, { resolvedExternal, repoRoot }) {
  if (resolvedExternal) return resolvedExternal.full;
  const norm = normalizeRepoRel(rel);
  if (!norm) {
    throw new Error(`invalid repo-relative path: ${rel}`);
  }
  const root = path.resolve(repoRoot);
  const full = path.resolve(root, norm);
  if (full !== root && !full.startsWith(root + path.sep)) {
    throw new Error(`path outside repo: ${rel}`);
  }
  return full;
}
