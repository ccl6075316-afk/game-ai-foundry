import type {
  HostChatDraftBrief,
  HostChatStatus,
  MakeabilityIntentGap,
  MakeabilityReview,
} from "../chat/types";

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

/** Short read-only chips for board (declared fields only; no resolve). */
export function assetStyleChips(asset: Record<string, unknown>): string[] {
  const chips: string[] = [];
  if (
    asset.content_class !== undefined &&
    asset.content_class !== null &&
    String(asset.content_class).trim() !== ""
  ) {
    chips.push(`类:${String(asset.content_class)}`);
  }
  if (asset.style_group !== undefined && asset.style_group !== null && asset.style_group !== "") {
    chips.push(`组:${String(asset.style_group)}`);
  }
  if (
    asset.style_anchor_kind !== undefined &&
    asset.style_anchor_kind !== null &&
    asset.style_anchor_kind !== ""
  ) {
    chips.push(`锚类型:${String(asset.style_anchor_kind)}`);
  }
  if (asset.style_anchor !== undefined && asset.style_anchor !== null && asset.style_anchor !== "") {
    chips.push(`锚:${String(asset.style_anchor)}`);
  }
  if (
    asset.identity_anchor !== undefined &&
    asset.identity_anchor !== null &&
    asset.identity_anchor !== ""
  ) {
    chips.push(`身份:${String(asset.identity_anchor)}`);
  }
  if (Object.prototype.hasOwnProperty.call(asset, "use_style_img2img")) {
    chips.push(`img2img:${formatUseStyleImg2img(asset.use_style_img2img)}`);
  }
  return chips;
}

function formatAssetStyleLines(asset: Record<string, unknown>): string[] {
  const lines: string[] = [];
  if (
    asset.content_class !== undefined &&
    asset.content_class !== null &&
    String(asset.content_class).trim() !== ""
  ) {
    lines.push(`  - **内容类 (content_class)：** ${String(asset.content_class)}`);
  }
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

function asRecordList(raw: unknown): Record<string, unknown>[] {
  if (!Array.isArray(raw)) return [];
  return raw.filter((item): item is Record<string, unknown> => !!item && typeof item === "object");
}

function formatIdTitleList(
  heading: string,
  raw: unknown,
  options?: { extra?: (item: Record<string, unknown>) => string[] },
): string[] {
  const items = asRecordList(raw);
  if (!items.length) return [];
  const lines: string[] = [`## ${heading}`, ""];
  for (const item of items) {
    const id = String(item.id || "").trim();
    const title = String(item.title || "").trim();
    if (!id && !title) continue;
    const head = title ? `**${title}**` : "**（无标题）**";
    const idBit = id ? ` (\`${id}\`)` : "";
    lines.push(`- ${head}${idBit}`);
    const summary = String(item.summary || "").trim();
    if (summary) lines.push(`  - ${summary}`);
    if (options?.extra) {
      for (const line of options.extra(item)) lines.push(line);
    }
    const notes = String(item.notes || "").trim();
    if (notes) lines.push(`  - 备注：${notes}`);
  }
  lines.push("");
  return lines;
}

function formatScenesSection(project: Record<string, unknown>): string[] {
  return formatIdTitleList("场景（有进出的屏）", project.scenes, {
    extra: (item) => {
      const panelIds = Array.isArray(item.ui_panel_ids)
        ? item.ui_panel_ids.map(String).filter((s) => s.trim())
        : [];
      return panelIds.length ? [`  - UI 面板：${panelIds.map((id) => `\`${id}\``).join("、")}`] : [];
    },
  });
}

function formatSystemsSection(project: Record<string, unknown>): string[] {
  return formatIdTitleList("逻辑系统（跨场景）", project.systems);
}

function formatUiPanelsSection(project: Record<string, unknown>): string[] {
  return formatIdTitleList("UI 面板", project.ui_panels, {
    extra: (item) => {
      const bits: string[] = [];
      const kind = String(item.kind || "").trim();
      if (kind) bits.push(`  - 类型：${kind}`);
      const anchor = String(item.anchor || "").trim();
      if (anchor) bits.push(`  - 位置：${anchor}`);
      const slots = Array.isArray(item.slots)
        ? item.slots.map(String).filter((s) => s.trim())
        : [];
      if (slots.length) bits.push(`  - 内容块：${slots.join("、")}`);
      return bits;
    },
  });
}

function formatIdListField(label: string, raw: unknown): string | null {
  if (!Array.isArray(raw)) return null;
  const ids = raw.map(String).filter((s) => s.trim());
  if (!ids.length) return null;
  return `  - **${label}：** ${ids.map((id) => `\`${id}\``).join("、")}`;
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
  const view = p.view;
  if (view !== undefined && view !== null && String(view).trim() !== "") {
    lines.push(`**视角 (view)：** ${String(view)}`, "");
  }
  const desc = p.description;
  if (desc) lines.push("## 简介", "", String(desc), "");
  const loop = status?.gameplay_loop || p.gameplay_loop;
  if (loop) lines.push("## 玩法循环", "", String(loop), "");
  const art = p.art_direction;
  if (art) lines.push("## 美术方向", "", String(art), "");
  lines.push(...formatArtTokensSection(p as Record<string, unknown>));
  const goal = p.session_goal;
  if (goal) lines.push("## 本局目标", "", String(goal), "");
  lines.push(...formatScenesSection(p as Record<string, unknown>));
  lines.push(...formatSystemsSection(p as Record<string, unknown>));
  lines.push(...formatUiPanelsSection(p as Record<string, unknown>));
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
      const sceneLine = formatIdListField(
        "归属场景 (scene_ids)",
        (a as Record<string, unknown>).scene_ids,
      );
      if (sceneLine) lines.push(sceneLine);
      const systemLine = formatIdListField(
        "归属系统 (system_ids)",
        (a as Record<string, unknown>).system_ids,
      );
      if (systemLine) lines.push(systemLine);
    }
    lines.push("");
  }
  lines.push("## 原始 JSON", "", "```json", JSON.stringify(draft, null, 2), "```", "");
  return lines.join("\n");
}

/** Export allowed only when backend ready + fresh makeability review with no intent gaps. */
export function briefMakeabilityExportReady(status: HostChatStatus | null): boolean {
  if (!status?.ready_to_export) return false;
  if (!status.has_review) return false;
  if (!status.makeability_fingerprint_match) return false;
  if ((status.intent_count ?? 0) > 0) return false;
  return true;
}

export function briefMakeabilityGateHint(status: HostChatStatus | null): string {
  if (!status?.has_review) return "请先点「制作审查」";
  if (!status.makeability_fingerprint_match) return "草稿已改，请重新「制作审查」";
  if ((status.intent_count ?? 0) > 0) {
    return `还有 ${status.intent_count} 条意图缺口未关，请点选项或回复后再审查`;
  }
  if (status.gaps?.length) return "校验未通过，请先点「自动修」或补齐字段";
  if (!status.contract_complete && !status.ready_to_export) return "草稿尚未通过校验";
  if (!status.ready_to_export) return "校验已过，刷新状态或再点一次「制作审查」后可导出";
  return "导出到 projects/<slug>/";
}

export function flattenIntentChoices(intentGaps: MakeabilityIntentGap[] | undefined): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const gap of intentGaps || []) {
    for (const raw of gap.choices || []) {
      const choice = String(raw).trim();
      if (choice && !seen.has(choice)) {
        seen.add(choice);
        out.push(choice);
      }
    }
  }
  return out;
}

export function formatMakeabilityReviewDetails(review: MakeabilityReview | null | undefined): string {
  if (!review) return "";
  const lines: string[] = [];
  const intentGaps = review.intent_gaps || [];
  const detailGaps = review.detail_gaps || [];
  if (intentGaps.length) {
    lines.push("**意图缺口**（须在本对话内拍板）：");
    for (const gap of intentGaps) {
      const id = gap.id ? `\`${gap.id}\` · ` : "";
      lines.push(`- ${id}${gap.question || "（未描述）"}`);
      if (gap.why_blocking) lines.push(`  - ${gap.why_blocking}`);
    }
    lines.push("");
  }
  if (detailGaps.length) {
    lines.push("**施工细节**（导出后进 production，PM 可补暂定值）：");
    for (const gap of detailGaps) {
      const id = gap.id ? `\`${gap.id}\` · ` : "";
      lines.push(`- ${id}${gap.topic || "（未描述）"}`);
    }
  }
  return lines.join("\n");
}

export function formatMakeabilityProductionSummary(
  productionDoc: Record<string, unknown> | null | undefined,
): string | null {
  const makeability = productionDoc?.makeability;
  if (!makeability || typeof makeability !== "object" || Array.isArray(makeability)) return null;
  const row = makeability as Record<string, unknown>;
  const status = String(row.status || "unknown");
  const items = row.detail_items;
  const count = Array.isArray(items) ? items.length : 0;
  return `制作完备性：${status} · ${count} 条施工细节`;
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
