/** Detect planner intent to start a brand-new game (not continue the current draft). */

export type NewProjectIntent = {
  /** Remaining text after the trigger, used as host-chat seed. */
  seed?: string;
  /** Optional ASCII project folder name, e.g. fishing-jam. */
  slugHint?: string;
};

const EXACT = /^(?:新建|新项目|新工程|新游戏|重新策划)$/u;

const PATTERNS: RegExp[] = [
  /^(?:(?:请)?(?:帮我)?)?(?:新建|开启|开一?个)(?:一个)?(?:新的?)?(?:项目|工程|游戏|brief)\s*[，,。！!：:]*\s*(.*)$/iu,
  /^(?:新开(?:一个)?(?:项目|工程|游戏))\s*[，,。！!：:]*\s*(.*)$/iu,
  /^(?:重新(?:开始)?策划|重开项目|换个(?:新)?游戏|换一个游戏)\s*[，,。！!：:]*\s*(.*)$/iu,
  /^(?:new\s+project|start\s+(?:a\s+)?new\s+(?:game|project))\s*[，,。！!：:]*\s*(.*)$/iu,
];

function splitSlugAndSeed(rest: string): { seed?: string; slugHint?: string } {
  const t = rest.trim();
  if (!t) return {};
  const m = t.match(/^([a-z][a-z0-9-]{0,62})(?:\s+|$)(.*)$/i);
  if (m && /^[a-z0-9-]+$/i.test(m[1])) {
    const slugHint = m[1].toLowerCase();
    const seed = (m[2] || "").trim();
    return seed ? { slugHint, seed } : { slugHint };
  }
  return { seed: t };
}

export function parseNewProjectIntent(text: string): NewProjectIntent | null {
  const t = text.trim();
  if (!t || /^\/brief\b/i.test(t)) return null;
  if (EXACT.test(t)) return {};
  for (const re of PATTERNS) {
    const m = t.match(re);
    if (m) {
      return splitSlugAndSeed(m[1] || "");
    }
  }
  return null;
}
