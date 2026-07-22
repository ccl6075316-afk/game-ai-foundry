import type { HostChatDraftBrief, HostChatStatus } from "../chat/types";

const ART_TOKEN_KNOWN_KEYS = ["line", "palette", "forbid", "silhouette"] as const;

function formatArtTokenValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (value !== null && typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function artTokenKeys(tokens: Record<string, unknown>): string[] {
  const known = new Set<string>(ART_TOKEN_KNOWN_KEYS);
  const ordered: string[] = [...ART_TOKEN_KNOWN_KEYS];
  for (const key of Object.keys(tokens)) {
    if (!known.has(key)) {
      ordered.push(key);
    }
  }
  return ordered.filter((key) => {
    const value = tokens[key];
    return value !== undefined && value !== null && value !== "";
  });
}

function formatArtTokensSection(project: Record<string, unknown>): string[] {
  const raw = project.art_tokens;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return [];
  const tokens = raw as Record<string, unknown>;
  const keys = artTokenKeys(tokens);
  if (!keys.length) return [];
  const lines: string[] = ["## 风格硬锁 (art_tokens)", ""];
  for (const key of keys) {
    lines.push(`- **${key}：** ${formatArtTokenValue(tokens[key])}`);
  }
  lines.push("");
  return lines;
}

function formatUseStyleImg2img(value: unknown): string {
  if (value === false) return "关";
  if (value === true) return "开";
  return String(value);
}

function formatAssetStyleLines(asset: Record<string, unknown>): string[] {
  const lines: string[] = [];
  if (asset.style_group !== undefined && asset.style_group !== null && asset.style_group !== "") {
    lines.push(`  - **风格组 (style_group)：** ${String(asset.style_group)}`);
  }
  if (
    asset.style_anchor_kind !== undefined &&
    asset.style_anchor_kind !== null &&
    asset.style_anchor_kind !== ""
  ) {
    lines.push(`  - **锚类型 (style_anchor_kind)：** ${String(asset.style_anchor_kind)}`);
  }
  if (asset.style_anchor !== undefined && asset.style_anchor !== null && asset.style_anchor !== "") {
    lines.push(`  - **风格锚 (style_anchor)：** ${String(asset.style_anchor)}`);
  }
  if (
    asset.identity_anchor !== undefined &&
    asset.identity_anchor !== null &&
    asset.identity_anchor !== ""
  ) {
    lines.push(`  - **身份锚 (identity_anchor)：** ${String(asset.identity_anchor)}`);
  }
  if (Object.prototype.hasOwnProperty.call(asset, "use_style_img2img")) {
    lines.push(
      `  - **风格 img2img (use_style_img2img)：** ${formatUseStyleImg2img(asset.use_style_img2img)}`,
    );
  }
  return lines;
}

export function isBriefShaped(value: unknown): value is HostChatDraftBrief {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const obj = value as Record<string, unknown>;
  return "project" in obj || "assets" in obj;
}

export function formatBriefDocument(
  draft: HostChatDraftBrief | null,
  status: HostChatStatus | null,
): string {
  if (!draft) return "";
  const p = draft.project || {};
  const title = String(status?.title || p.title || "未命名项目");
  const lines: string[] = [`# ${title}`, ""];
  const genre = status?.genre || p.genre;
  if (genre) lines.push(`**类型：** ${genre}`, "");
  const desc = p.description;
  if (desc) lines.push("## 简介", "", String(desc), "");
  const loop = status?.gameplay_loop || p.gameplay_loop;
  if (loop) lines.push("## 玩法循环", "", String(loop), "");
  const art = p.art_direction;
  if (art) lines.push("## 美术方向", "", String(art), "");
  lines.push(...formatArtTokensSection(p as Record<string, unknown>));
  const goal = p.session_goal;
  if (goal) lines.push("## 本局目标", "", String(goal), "");
  const controls = p.controls;
  if (controls && typeof controls === "object") {
    lines.push("## 操作", "");
    for (const [k, v] of Object.entries(controls as Record<string, unknown>)) {
      const keys = Array.isArray(v) ? v.join(", ") : String(v);
      lines.push(`- **${k}：** ${keys}`);
    }
    lines.push("");
  }
  const camera = p.camera;
  if (camera && typeof camera === "object") {
    lines.push("## 摄像机", "", "```json", JSON.stringify(camera, null, 2), "```", "");
  }
  const viewport = p.viewport;
  if (viewport && typeof viewport === "object") {
    lines.push("## 视口", "", "```json", JSON.stringify(viewport, null, 2), "```", "");
  }
  const assets = draft.assets || [];
  if (assets.length) {
    lines.push("## 资产", "");
    for (const a of assets) {
      if (!a?.name) continue;
      const meta = [a.type, a.usage].filter(Boolean).join(" · ");
      lines.push(`- **${a.name}**${meta ? `（${meta}）` : ""}`);
      if (a.description) lines.push(`  - ${a.description}`);
      lines.push(...formatAssetStyleLines(a as Record<string, unknown>));
    }
    lines.push("");
  }
  lines.push("## 原始 JSON", "", "```json", JSON.stringify(draft, null, 2), "```", "");
  return lines.join("\n");
}

export function tryFormatBriefJsonText(
  text: string,
  status: HostChatStatus | null = null,
): string | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    const parsed: unknown = JSON.parse(trimmed);
    if (!isBriefShaped(parsed)) return null;
    return formatBriefDocument(parsed, status);
  } catch {
    return null;
  }
}
