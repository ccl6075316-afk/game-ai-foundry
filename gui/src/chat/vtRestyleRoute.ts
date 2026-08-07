/** Route helpers for multi-scene visual-target restyle / regenerate. */

import {
  extractSceneIdFromChoice,
  sanitizeVtChoiceTitle,
} from "./vtChoiceParse";

export type VtRestyleFocus = {
  /** True while user is revising after「都不满意」 until pick or explicit scope change. */
  active: boolean;
  /** null = global default north-star */
  sceneId: string | null;
  sceneTitle?: string;
  /** Set after a successful pick so follow-up chat stays on that scene. */
  candidateId?: string;
  kind?: "restyle" | "pick";
  /** Restyle: user has typed feedback; only then show / allow regenerate. */
  feedbackDone?: boolean;
};

/** Primary chip label — dissatisfaction ≠ style change. */
export function formatVtRestyleChoice(
  sceneId: string | null,
  sceneTitle?: string,
): string {
  if (!sceneId) return "都不满意，重做 · 全局";
  const title = sanitizeVtChoiceTitle(sceneTitle || sceneId) || sceneId;
  return `都不满意，重做（场景：${title}｜${sceneId}）`;
}

/** Shown only after the user wrote restyle feedback. */
export function formatVtRegenAfterFeedbackChoice(
  sceneId: string | null,
  sceneTitle?: string,
): string {
  if (!sceneId) return "我写好了 · 重新生成全局北极星";
  const title = sanitizeVtChoiceTitle(sceneTitle || sceneId) || sceneId;
  return `我写好了 · 重新生成（场景：${title}｜${sceneId}）`;
}

export function parseVtRegenAfterFeedbackChoice(
  trimmed: string,
): { hit: true; sceneId: string | null } | { hit: false } {
  const t = trimmed.trim();
  if (t === "我写好了 · 重新生成全局北极星" || t === "我写好了，重新生成全局北极星") {
    return { hit: true, sceneId: null };
  }
  if (!/^我写好了\s*[·•，,]\s*重新生成/.test(t)) return { hit: false };
  if (/全局/.test(t) && !/[｜|]/.test(t) && !/（[a-zA-Z]/.test(t)) {
    return { hit: true, sceneId: null };
  }
  const sceneId = extractSceneIdFromChoice(t);
  if (!sceneId) return { hit: false };
  return { hit: true, sceneId };
}

/**
 * Parse restyle chip / short aliases (incl. legacy「换风格」labels).
 * `sceneId: undefined` means “use pending generate scope”.
 */
export function parseVtRestyleChoice(
  trimmed: string,
): { hit: true; sceneId: string | null | undefined } | { hit: false } {
  const t = trimmed.trim();
  if (
    t === "都不满意，重做" ||
    t === "都不满意，换风格" ||
    t === "都不满意" ||
    t === "换风格" ||
    t === "重新定风格"
  ) {
    return { hit: true, sceneId: undefined };
  }
  if (/^都不满意，(?:重做|换风格)\s*[·•]\s*全局$/.test(t)) {
    return { hit: true, sceneId: null };
  }
  if (!/^都不满意，(?:重做|换风格)/.test(t)) return { hit: false };
  if (/全局/.test(t) && !/[｜|]/.test(t)) {
    return { hit: true, sceneId: null };
  }
  const sceneId = extractSceneIdFromChoice(t);
  // Chip matched but nested-title broke id extract — still consume so planner
  // does not treat it as free chat (fall back to pending scope in App).
  return { hit: true, sceneId: sceneId ?? undefined };
}

const RESTYLE_NO_SPECULATIVE_PATCH =
  `重要：用户点「都不满意」只表示候选图不行，不等于要换画风。` +
  `在听清具体不满点之前，禁止改 project.art_direction，禁止擅自换风格/配色/像素风。` +
  `只根据用户原话落实：构图/内容/钓点/UI 布局等问题 → upsert_scene 的 summary/notes；` +
  `仅当用户明确说「换风格 / 换画风 / 改 art_direction / 太像素 / 太写实」等时才可改 art_direction。` +
  `若原话含糊，先问一句澄清，本轮 brief_patches 留空。`;

/** Prefixed user turn so host-chat knows which north-star is being revised. */
export function wrapVtRestyleUserMessage(
  focus: VtRestyleFocus,
  userMessage: string,
): string {
  const body = userMessage.trim();
  if (!focus.active || !body) return userMessage;
  if (focus.kind === "pick") {
    if (focus.sceneId) {
      const title = (focus.sceneTitle || focus.sceneId).trim();
      const cand = focus.candidateId ? `候选 ${focus.candidateId}` : "已选定候选";
      return (
        `【刚选定北极星 · 场景 ${title}（${focus.sceneId}）· ${cand}】` +
        `后续反馈默认针对该场景的北极星；不要当成别的屏或全局。` +
        `若用户要改这张图，用 upsert_scene 更新该场景 summary/notes。` +
        `不要擅自改画风。\n\n` +
        `用户原话：${body}`
      );
    }
    return (
      `【刚选定北极星 · 全局 · ${focus.candidateId ? `候选 ${focus.candidateId}` : "已选定"}】` +
      `后续反馈默认针对全局 visual target。不要擅自换风格。\n\n用户原话：${body}`
    );
  }
  if (focus.sceneId) {
    const title = (focus.sceneTitle || focus.sceneId).trim();
    return (
      `【北极星重做 · 仅场景 ${title}（${focus.sceneId}）】` +
      RESTYLE_NO_SPECULATIVE_PATCH +
      `默认用 upsert_scene 更新该场景 summary/notes（英文）。\n\n` +
      `用户原话：${body}`
    );
  }
  return (
    `【北极星重做 · 全局默认北极星】` +
    RESTYLE_NO_SPECULATIVE_PATCH +
    `\n\n用户原话：${body}`
  );
}
