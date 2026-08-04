/** Convert CLI absolute/relative media paths to repo-relative for Electron preview. */

/**
 * Index of the in-repo ``projects/<slug>/…`` segment.
 *
 * Must not use the first ``projects/`` — clones under ``~/projects/<repo>`` would
 * slice to ``projects/<repo>/projects/<slug>/…`` and preview resolves to nowhere
 * (UI: 图片加载失败 / 找不到文件).
 */
function projectsSegmentIndex(norm: string): number {
  const re =
    /projects\/[^/]+\/(?:output|plans|pipeline|games|brief)(?:\/|$)/gi;
  let last = -1;
  let match: RegExpExecArray | null;
  while ((match = re.exec(norm)) !== null) {
    last = match.index;
  }
  if (last >= 0) return last;
  return norm.lastIndexOf("projects/");
}

export function toRepoMediaRel(absOrRel: string): string {
  const norm = String(absOrRel || "").trim().replace(/\\/g, "/");
  if (!norm) return "";

  const projectsIdx = projectsSegmentIndex(norm);
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
