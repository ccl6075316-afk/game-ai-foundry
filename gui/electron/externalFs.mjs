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
 * Project root key for binding / VT matching.
 * `projects/<slug>/…` → `projects/<slug>`
 * `external:<id>/…` → `external:<id>`
 * @param {string | null | undefined} rel
 * @returns {string | null}
 */
export function projectRootKeyFromBriefRel(rel) {
  const raw = String(rel || "")
    .replace(/\\/g, "/")
    .replace(/^\/+/, "");
  if (!raw) return null;
  const ext = raw.match(/^(external:[^/]+)/i);
  if (ext?.[1]) return ext[1];
  const proj = raw.match(/^(projects\/[^/]+)/i);
  if (proj?.[1]) return proj[1];
  return null;
}

/**
 * True when path is under rootAbs (or equals it).
 * @param {string} absPath
 * @param {string} rootAbs
 */
export function pathUnderRoot(absPath, rootAbs) {
  const full = path.resolve(absPath);
  const root = path.resolve(rootAbs);
  return full === root || full.startsWith(root + path.sep);
}

/**
 * Match a visual-target manifest's brief_path to the active brief.
 * Never match on basename alone (all briefs are often named brief.json).
 *
 * @param {{ briefAbs: string, briefRel: string, manBriefPath: string, repoRoot: string }} args
 * @returns {boolean}
 */
export function manifestBelongsToBrief({
  briefAbs,
  briefRel,
  manBriefPath,
  repoRoot,
}) {
  const man = String(manBriefPath || "").replace(/\\/g, "/").trim();
  if (!man) return false;
  const briefResolved = path.resolve(briefAbs);
  let manAbs;
  try {
    manAbs = path.isAbsolute(man)
      ? path.resolve(man)
      : path.resolve(repoRoot, man);
  } catch {
    return false;
  }
  if (manAbs === briefResolved) return true;

  const briefRoot = projectRootKeyFromBriefRel(briefRel);
  // Manifest may store repo-relative or absolute; derive root from man string too.
  let manRelHint = man;
  try {
    const rel = path.relative(path.resolve(repoRoot), manAbs);
    if (rel && !rel.startsWith("..") && !path.isAbsolute(rel)) {
      manRelHint = rel.replace(/\\/g, "/");
    }
  } catch {
    /* keep man */
  }
  const manRoot = projectRootKeyFromBriefRel(manRelHint);
  if (briefRoot && manRoot) {
    return briefRoot.toLowerCase() === manRoot.toLowerCase();
  }
  return false;
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
