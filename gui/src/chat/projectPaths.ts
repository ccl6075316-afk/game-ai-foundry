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

export function isIsolatedBriefRel(briefRel: string): boolean {
  return projectRootFromBriefRel(briefRel) != null;
}

export function planTargetsFromBrief(briefRel: string): PlanTargets {
  const brief = norm(briefRel);
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
  const s = (slug || "my-game").replace(/[/\\]/g, "-").trim() || "my-game";
  return `projects/${s}/brief.json`;
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

export function loadActiveBriefRel(): string | null {
  try {
    return localStorage.getItem(ACTIVE_BRIEF_KEY);
  } catch {
    return null;
  }
}

export function saveActiveBriefRel(briefRel: string): void {
  try {
    localStorage.setItem(ACTIVE_BRIEF_KEY, briefRel.replace(/\\/g, "/"));
  } catch {
    /* ignore */
  }
}
