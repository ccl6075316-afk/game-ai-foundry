/** Shared parsers for VT choice chips (pick / restyle / regen / generate). */

/** Strip nested fullwidth parens from titles so chips stay parseable. */
export function sanitizeVtChoiceTitle(title: string): string {
  return String(title || "")
    .replace(/[（(][^）)]*[）)]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Extract scene id from a choice suffix.
 * Prefer `｜id` / `|id`, then trailing `（ascii_id）`.
 */
export function extractSceneIdFromChoice(text: string): string | null {
  const t = String(text || "").trim();
  const pipe = t.match(/[｜|]([a-zA-Z][a-zA-Z0-9_-]*)\s*）?\s*$/);
  if (pipe) return pipe[1];
  const paren = t.match(/（([a-zA-Z][a-zA-Z0-9_-]*)）\s*$/);
  if (paren) return paren[1];
  return null;
}

export function parseVtPickChoice(
  trimmed: string,
): { hit: true; candidateId: string; sceneId: string | null } | { hit: false } {
  const t = trimmed.trim();
  const m = t.match(/^选用北极星\s*([a-dA-D])(.*)$/i);
  if (!m) return { hit: false };
  const candidateId = m[1].toLowerCase();
  const rest = m[2] || "";
  if (!rest.trim()) return { hit: true, candidateId, sceneId: null };
  const sceneId = extractSceneIdFromChoice(rest);
  // Rest present but no parseable id (broken nested title) — still treat as pick
  // so it never falls through to the planner LLM.
  return { hit: true, candidateId, sceneId };
}

export function formatVtPickChoice(
  candidateId: string,
  sceneId: string | null,
  sceneTitle?: string,
): string {
  const id = String(candidateId || "").trim().toLowerCase();
  if (!sceneId) return `选用北极星 ${id}`;
  const title = sanitizeVtChoiceTitle(sceneTitle || sceneId) || sceneId;
  return `选用北极星 ${id}（场景：${title}｜${sceneId}）`;
}
