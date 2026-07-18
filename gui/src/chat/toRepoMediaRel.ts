/** Convert CLI absolute/relative media paths to repo-relative for Electron preview. */

export function toRepoMediaRel(absOrRel: string): string {
  const norm = String(absOrRel || "").trim().replace(/\\/g, "/");
  if (!norm) return "";

  const projectsIdx = norm.indexOf("projects/");
  if (projectsIdx >= 0) return norm.slice(projectsIdx);

  // Prefer not to strip projects/ prefix — only fall back for legacy flat layout
  const outputIdx = norm.indexOf("output/");
  if (outputIdx >= 0) return norm.slice(outputIdx);

  const plansIdx = norm.indexOf("plans/");
  if (plansIdx >= 0) return norm.slice(plansIdx);

  const gamesIdx = norm.indexOf("games/");
  if (gamesIdx >= 0) return norm.slice(gamesIdx);

  return norm.replace(/^\.\.\//, "");
}
