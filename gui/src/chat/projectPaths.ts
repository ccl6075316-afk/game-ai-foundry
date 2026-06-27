/** Derive pipeline / output / Godot paths from a brief file path. */

export interface PlanTargets {
  briefRel: string;
  manifestRel: string;
  outputDirRel: string;
  godotProjectRel: string;
  slug: string;
}

export function slugFromBriefRel(briefRel: string): string {
  const base = briefRel.split(/[/\\]/).pop() || "game";
  const stem = base.replace(/\.json$/i, "");
  const slug = stem.replace(/-brief$/i, "").trim();
  return slug || "game";
}

export function planTargetsFromBrief(briefRel: string): PlanTargets {
  const slug = slugFromBriefRel(briefRel);
  return {
    briefRel,
    slug,
    manifestRel: `pipeline/${slug}.json`,
    outputDirRel: `output/${slug}`,
    godotProjectRel: `games/${slug}`,
  };
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
