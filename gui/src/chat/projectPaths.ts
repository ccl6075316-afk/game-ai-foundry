/** Derive pipeline / output / Godot paths from a brief file path.

 * Isolated (new): projects/<slug>/brief.json → all artifacts under projects/<slug>/
 * Legacy flat: resources/*-brief.json → pipeline/, output/, games/, plans/
 */

export interface PlanTargets {
  briefRel: string;
  manifestRel: string;
  outputDirRel: string;
  godotProjectRel: string;
  plansDirRel: string;
  progressRel: string;
  productionRel: string;
  projectRootRel: string | null;
  slug: string;
  isolated: boolean;
}

/** Registry entry — mirrors cli/external_projects.py schema. */
export interface ExternalProjectEntry {
  id: string;
  display_name: string;
  root_abs: string;
  godot_rel: string;
  brief_rel: string;
  added_at?: string;
}

const EXTERNAL_BRIEF_KEY_RE = /^external:[^/]+\/brief\.json$/i;

export function isExternalBriefRel(rel: string): boolean {
  return EXTERNAL_BRIEF_KEY_RE.test(norm(rel));
}

/** Extract ext_… id from virtual brief key; null if not external brief. */
export function parseExternalBriefId(rel: string): string | null {
  const n = norm(rel);
  if (!isExternalBriefRel(n)) return null;
  return n.split(":", 2)[1]?.split("/", 1)[0] ?? null;
}

export function externalBriefRel(id: string): string {
  return `external:${id}/brief.json`;
}

function externalRootRel(id: string): string {
  return `external:${id}`;
}

function norm(rel: string): string {
  return rel.replace(/\\/g, "/").replace(/^\.?\//, "");
}

/** projects/<slug>/... → slug; else stem without -brief */
export function slugFromBriefRel(briefRel: string): string {
  const n = norm(briefRel);
  const m = n.match(/^projects\/([^/]+)\//i);
  if (m?.[1]) return m[1];
  const base = n.split("/").pop() || "game";
  const stem = base.replace(/\.json$/i, "");
  const slug = stem.replace(/-brief$/i, "").trim();
  return slug || "game";
}

export function projectRootFromBriefRel(briefRel: string): string | null {
  const n = norm(briefRel);
  const m = n.match(/^(projects\/[^/]+)\//i);
  return m?.[1] ?? null;
}

/** True when both paths belong to the same isolated projects/<slug>/ tree. */
export function sameProjectRoot(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false;
  const ra = projectRootFromBriefRel(a);
  const rb = projectRootFromBriefRel(b);
  if (ra && rb) return ra.toLowerCase() === rb.toLowerCase();
  return norm(a).toLowerCase() === norm(b).toLowerCase();
}

export function isIsolatedBriefRel(briefRel: string): boolean {
  return projectRootFromBriefRel(briefRel) != null || isExternalBriefRel(briefRel);
}

/** Plan targets for a registered external project (virtual external:… keys). */
export function planTargetsFromExternalEntry(entry: ExternalProjectEntry): PlanTargets {
  const id = String(entry.id || "").trim();
  const root = externalRootRel(id);
  const godotRel = String(entry.godot_rel || ".").replace(/\\/g, "/");
  const slug =
    sanitizeProjectSlug(entry.display_name || "") ||
    id.replace(/^ext_/, "") ||
    "external";
  const godotProjectRel = godotRel === "." ? root : `${root}/${godotRel}`;
  return {
    briefRel: externalBriefRel(id),
    slug,
    isolated: true,
    projectRootRel: root,
    manifestRel: `${root}/pipeline/manifest.json`,
    outputDirRel: `${root}/output`,
    godotProjectRel,
    plansDirRel: `${root}/plans`,
    progressRel: `${root}/progress.json`,
    productionRel: `${root}/production.json`,
  };
}

export function planTargetsFromBrief(briefRel: string): PlanTargets {
  const brief = norm(briefRel);
  if (isExternalBriefRel(brief)) {
    throw new Error(
      "planTargetsFromBrief 不支持 external: 虚拟键；请使用 planTargetsFromExternalEntry 并传入 registry entry。",
    );
  }
  const root = projectRootFromBriefRel(brief);
  const slug = slugFromBriefRel(brief);
  if (root) {
    return {
      briefRel: brief,
      slug,
      isolated: true,
      projectRootRel: root,
      manifestRel: `${root}/pipeline/manifest.json`,
      outputDirRel: `${root}/output`,
      godotProjectRel: `${root}/game`,
      plansDirRel: `${root}/plans`,
      progressRel: `${root}/progress.json`,
      productionRel: `${root}/production.json`,
    };
  }
  const base = brief.split("/").pop() || "game.json";
  const stem = base.replace(/\.json$/i, "");
  return {
    briefRel: brief,
    slug,
    isolated: false,
    projectRootRel: null,
    manifestRel: `pipeline/${slug}.json`,
    outputDirRel: `output/${stem}`,
    godotProjectRel: `games/${stem}`,
    plansDirRel: "plans",
    progressRel: `plans/progress_${slug}.json`,
    productionRel: `plans/production_${slug}.json`,
  };
}

export function productionPathFromBrief(briefRel: string): string {
  return planTargetsFromBrief(briefRel).productionRel;
}

export function progressPathFromBrief(briefRel: string): string {
  return planTargetsFromBrief(briefRel).progressRel;
}

/** Export path for a new game — always isolated. */
export function briefExportRel(slug: string): string {
  const s = sanitizeProjectSlug(slug) || "my-game";
  return `projects/${s}/brief.json`;
}

/** ASCII project folder name under projects/. Empty if unusable. */
export function sanitizeProjectSlug(raw: string): string {
  const t = (raw || "").trim().toLowerCase();
  if (!t) return "";
  if (/[\u4e00-\u9fff]/.test(t) && !/[a-z0-9]/.test(t)) {
    return "";
  }
  return t
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 64);
}

/** `/delta <change-id> | <intent>` or `/delta <change-id> <intent…>` */
export function parseDeltaCommand(text: string): { changeId: string; intent: string } | null {
  const raw = text.trim();
  if (!raw.toLowerCase().startsWith("/delta")) return null;
  const rest = raw.slice("/delta".length).trim();
  if (!rest) return null;
  if (rest.includes("|")) {
    const [id, ...intentParts] = rest.split("|");
    const changeId = id.trim();
    const intent = intentParts.join("|").trim();
    if (!changeId || !intent) return null;
    return { changeId, intent };
  }
  const m = rest.match(/^([^\s]+)\s+(.+)$/);
  if (!m) return null;
  return { changeId: m[1], intent: m[2].trim() };
}

export function parsePlanSubcommand(text: string): string | null | undefined {
  const parts = text.trim().split(/\s+/);
  if (parts[0]?.toLowerCase() !== "/plan") return undefined;
  const briefArg = parts.slice(1).join(" ").trim();
  if (!briefArg) return null;
  return briefArg.replace(/\\/g, "/");
}

const ACTIVE_BRIEF_KEY = "gamefactory.activeBrief";
/** Last real selection — survives `__none__` so cold start can restore after 新建项目取消. */
const LAST_BRIEF_KEY = "gamefactory.lastBrief";
/** Explicit “no project” — must not fall back to listBriefs()[0]. */
const ACTIVE_BRIEF_NONE = "__none__";

/** Preference for which brief the topbar binds to. */
export type ActiveBriefPreference =
  | { kind: "unset" }
  | { kind: "none" }
  | { kind: "brief"; rel: string };

export function readActiveBriefPreference(): ActiveBriefPreference {
  try {
    const v = localStorage.getItem(ACTIVE_BRIEF_KEY);
    if (v === null) return { kind: "unset" };
    const n = v.replace(/\\/g, "/").trim();
    if (!n || n === ACTIVE_BRIEF_NONE) return { kind: "none" };
    return { kind: "brief", rel: n };
  } catch {
    return { kind: "unset" };
  }
}

export function loadActiveBriefRel(): string | null {
  const pref = readActiveBriefPreference();
  return pref.kind === "brief" ? pref.rel : null;
}

/**
 * Cold-start / first paint: restore last project even if preference is ``__none__``
 * (set by 新建项目 / legacy 新对话). Do **not** use for plan/export path resolution.
 */
export function loadActiveBriefRelForStartup(): string | null {
  return loadActiveBriefRel() || loadLastBriefRel();
}

/** Last explicitly selected project (not cleared by 「新建项目」unbind). */
export function loadLastBriefRel(): string | null {
  try {
    const v = localStorage.getItem(LAST_BRIEF_KEY);
    if (v === null) return null;
    const n = v.replace(/\\/g, "/").trim();
    if (!n || n === ACTIVE_BRIEF_NONE) return null;
    return n;
  } catch {
    return null;
  }
}

export function saveActiveBriefRel(briefRel: string): void {
  try {
    const n = briefRel.replace(/\\/g, "/");
    localStorage.setItem(ACTIVE_BRIEF_KEY, n);
    localStorage.setItem(LAST_BRIEF_KEY, n);
  } catch {
    /* ignore */
  }
}

/**
 * Drop the topbar project binding (新建项目 before bind).
 * Keeps ``lastBrief`` so app restart can restore if the user never finished creating.
 */
export function clearActiveBriefRel(): void {
  try {
    localStorage.setItem(ACTIVE_BRIEF_KEY, ACTIVE_BRIEF_NONE);
  } catch {
    /* ignore */
  }
}
