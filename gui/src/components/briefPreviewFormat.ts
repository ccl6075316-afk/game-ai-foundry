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

export type DocsShardKind = "scene" | "system" | "asset";

export type DocsView =
  | { mode: "overview" }
  | { mode: "shard"; kind: DocsShardKind; id: string };

export type CatalogRow = {
  kind: DocsShardKind;
  id: string;
  title: string;
  summary?: string;
  /** Repo-relative path when present on catalog ref. */
  path?: string;
};

/** Human label for catalog rows: use title when present; id is machine mapping only. */
export function catalogDisplayTitle(row: { id: string; title?: string }): string {
  const id = String(row.id || "").trim();
  const title = String(row.title || "").trim();
  if (title) return title;
  return id || "（未命名）";
}

const SHARD_KIND_LABEL: Record<DocsShardKind, string> = {
  scene: "场景",
  system: "系统",
  asset: "资产",
};

export function formatDocsViewLabel(
  view: DocsView,
  title?: string | null,
): string {
  if (view.mode === "overview") return "总览";
  const kind = SHARD_KIND_LABEL[view.kind] || view.kind;
  const display = catalogDisplayTitle({ id: view.id, title: title || "" });
  return `${kind} · ${display}`;
}

export function formatFocusLabel(
  focus: HostChatStatus["focus"] | null | undefined,
  title?: string | null,
): string {
  if (!focus || typeof focus !== "object") return "未钉住";
  const kind = String(focus.kind || "").trim();
  if (!kind) return "未钉住";
  const id = String(focus.id || "").trim();
  if (kind === "project") return "项目门面";
  if (kind === "visual_target") {
    const sceneLabel = catalogDisplayTitle({ id: id === "global" ? "" : id, title: title || "" });
    return id && id !== "global"
      ? `北极星 · 场景 ${sceneLabel || id}`
      : "北极星 · 全局";
  }
  const kindLabel =
    kind === "scene" || kind === "system" || kind === "asset"
      ? SHARD_KIND_LABEL[kind]
      : kind;
  if (!id) return kindLabel;
  return `${kindLabel} · ${catalogDisplayTitle({ id, title: title || "" })}`;
}

/** Map session.focus → docs preview target (null = leave view alone). */
export function docsViewFromFocus(
  focus: HostChatStatus["focus"] | null | undefined,
): DocsView | null {
  if (!focus || typeof focus !== "object") return null;
  const kind = String(focus.kind || "").trim();
  const id = String(focus.id || "").trim();
  if (kind === "project") return { mode: "overview" };
  if (kind === "scene" || kind === "system" || kind === "asset") {
    if (!id) return null;
    return { mode: "shard", kind, id };
  }
  if (kind === "visual_target" && id && id !== "global") {
    return { mode: "shard", kind: "scene", id };
  }
  return null;
}

export function focusKey(
  focus: HostChatStatus["focus"] | null | undefined,
): string | null {
  if (!focus || typeof focus !== "object") return null;
  const kind = String(focus.kind || "").trim();
  if (!kind) return null;
  const id = String(focus.id || "").trim();
  return `${kind}:${id}`;
}

export function shardRelPath(
  projectRootRel: string,
  kind: DocsShardKind,
  id: string,
  catalogPath?: string | null,
): string {
  const explicit = String(catalogPath || "").trim().replace(/\\/g, "/");
  if (explicit) {
    if (explicit.startsWith("external:") || explicit.startsWith("projects/")) {
      return explicit;
    }
    const root = projectRootRel.replace(/\\/g, "/").replace(/\/+$/, "");
    return `${root}/${explicit.replace(/^\//, "")}`;
  }
  const root = projectRootRel.replace(/\\/g, "/").replace(/\/+$/, "");
  const safeId = id.replace(/\\/g, "/").replace(/\.\./g, "");
  if (kind === "scene") return `${root}/scenes/${safeId}.json`;
  if (kind === "system") return `${root}/systems/${safeId}.json`;
  return `${root}/assets/${safeId}.spec.json`;
}

export function catalogRowsFromDraft(draft: HostChatDraftBrief | null): CatalogRow[] {
  if (!draft) return [];
  const rows: CatalogRow[] = [];
  const p = (draft.project || {}) as Record<string, unknown>;
  for (const item of asRecordList(p.scenes)) {
    const id = String(item.id || "").trim();
    if (!id) continue;
    const path = String(item.path || "").trim() || undefined;
    rows.push({
      kind: "scene",
      id,
      title: String(item.title || id).trim() || id,
      summary: String(item.summary || "").trim() || undefined,
      path,
    });
  }
  for (const item of asRecordList(p.systems)) {
    const id = String(item.id || "").trim();
    if (!id) continue;
    const path = String(item.path || "").trim() || undefined;
    rows.push({
      kind: "system",
      id,
      title: String(item.title || id).trim() || id,
      summary: String(item.summary || "").trim() || undefined,
      path,
    });
  }
  for (const a of draft.assets || []) {
    const id = String((a as { name?: string; id?: string }).id || a?.name || "").trim();
    if (!id) continue;
    const title = String(a?.name || id).trim() || id;
    const summary = String(a?.description || "").trim() || undefined;
    const path = String((a as { path?: string }).path || "").trim() || undefined;
    rows.push({ kind: "asset", id, title, summary, path });
  }
  return rows;
}

/** Thin catalog for human docs panel (no scene/system notes dump). */
export function formatBriefCatalogOverview(
  draft: HostChatDraftBrief | null,
  status: HostChatStatus | null,
): string {
  if (!draft) return "";
  const p = draft.project || {};
  const title = String(status?.title || p.title || "未命名项目");
  const lines: string[] = [
    `# ${title}`,
    "",
    "_Brief 总览（薄目录）。下方点选场景 / 系统 / 资产打开分册；点选不会改对话焦点。_",
    "",
  ];
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
  lines.push(...formatUiPanelsSection(p as Record<string, unknown>));
  return lines.join("\n");
}

export function formatShardDocument(
  kind: DocsShardKind,
  id: string,
  raw: unknown,
): string {
  const kindLabel = SHARD_KIND_LABEL[kind];
  let title = "";
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    title = String(obj.title || obj.name || "").trim();
  }
  const display = catalogDisplayTitle({ id, title });
  const lines: string[] = [`# ${kindLabel} · ${display}`, "", `**id：** \`${id}\``, ""];
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    if (title && title !== display) lines.push(`**标题：** ${title}`, "");
    const summary = String(obj.summary || "").trim();
    if (summary) lines.push("## 摘要", "", summary, "");
    const notes = String(obj.notes || "").trim();
    if (notes) lines.push("## 备注 / 正文", "", notes, "");
    const desc = String(obj.description || "").trim();
    if (desc && kind === "asset") lines.push("## 描述", "", desc, "");
  }
  lines.push("## 原始 JSON", "", "```json", JSON.stringify(raw, null, 2), "```", "");
  return lines.join("\n");
}

/** Keep previous focus unless payload explicitly sets focus (incl. null). */
export function mergeStatusFocus(
  prev: HostChatStatus["focus"] | null | undefined,
  incoming: HostChatStatus["focus"] | undefined,
): HostChatStatus["focus"] | null {
  if (incoming !== undefined) return incoming;
  return prev ?? null;
}

/** Resolve inline scene/system/asset body from session draft (legacy or unsaved). */
export function inlineShardFromDraft(
  draft: HostChatDraftBrief | null,
  kind: DocsShardKind,
  id: string,
): Record<string, unknown> | null {
  const want = String(id || "").trim();
  if (!draft || !want) return null;
  if (kind === "asset") {
    for (const a of draft.assets || []) {
      if (!a || typeof a !== "object") continue;
      const row = a as Record<string, unknown>;
      const aid = String(row.id || row.name || "").trim();
      if (aid === want) return row;
    }
    return null;
  }
  const p = (draft.project || {}) as Record<string, unknown>;
  const list = asRecordList(kind === "scene" ? p.scenes : p.systems);
  for (const item of list) {
    if (String(item.id || "").trim() === want) return item;
  }
  return null;
}

/** True when entry looks like body (not bare catalog ref). */
export function shardEntryHasBody(entry: Record<string, unknown> | null | undefined): boolean {
  if (!entry) return false;
  for (const key of ["notes", "summary", "description", "tuning", "ui_panel_ids"]) {
    const v = entry[key];
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v) && v.length === 0) continue;
    return true;
  }
  return false;
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

/** Export allowed when structural contract passes (JSON / asset pipeline). Makeability is advisory. */
export function briefMakeabilityExportReady(status: HostChatStatus | null): boolean {
  if (!status) return false;
  if ((status.gaps?.length ?? 0) > 0) return false;
  if (status.contract_complete === false) return false;
  if (status.ready_to_export) return true;
  // Backend may omit ready when only makeability was stale; structural OK is enough.
  return Boolean(status.contract_complete) && (status.gaps?.length ?? 0) === 0;
}

export function briefMakeabilityGateHint(status: HostChatStatus | null): string {
  if ((status?.gaps?.length ?? 0) > 0) {
    return "校验未通过，请先点「自动修」或补齐会挡生图/解析的字段";
  }
  if (status?.contract_complete === false) return "草稿尚未通过结构校验";
  if (!status?.ready_to_export && !(status?.contract_complete && !(status.gaps?.length))) {
    return "校验已过，刷新状态后可导出";
  }
  if (!status?.has_review) return "可保存；建议稍后点「制作审查」补产品逻辑（不挡导出）";
  if (!status.makeability_fingerprint_match) {
    return "可保存；草稿已改，制作审查已过期（可选再审，不挡导出）";
  }
  if ((status.intent_count ?? 0) > 0) {
    return `可保存；还有 ${status.intent_count} 条意图缺口（可选继续拍板，不挡导出）`;
  }
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
