export type VtGlobalMark = {
  ready?: boolean;
  selected_id?: string | null;
  has_selected_image?: boolean;
  preview_path?: string | null;
};

/** Per-scene / global visual-target (北极星) readiness for GUI labels. */
export type VtSceneMark = {
  id: string;
  title: string;
  ready?: boolean;
  selected_id?: string | null;
  has_selected_image?: boolean;
  visual_reference?: string;
  preview_path?: string | null;
};

/** True when brief is bound or selected.png exists under the VT folder. */
export function vtIsMarked(row: {
  ready?: boolean;
  has_selected_image?: boolean;
}): boolean {
  return Boolean(row.ready || row.has_selected_image);
}

/** Short badge like ✓b / ✓ / ○ */
export function vtMarkBadge(row: {
  ready?: boolean;
  selected_id?: string | null;
  has_selected_image?: boolean;
}): string {
  if (!vtIsMarked(row)) return "○";
  const id = String(row.selected_id || "").trim().toLowerCase();
  return id ? `✓${id}` : "✓";
}

/**
 * Choice chip for scope picker. Keeps `（sceneId）` as the last paren group so
 * App.tsx regex can still extract the id.
 */
export function formatVtSceneChoiceLabel(scene: VtSceneMark): string {
  const rawTitle = (scene.title || scene.id || "").trim() || scene.id;
  const title = rawTitle.replace(/[（(][^）)]*[）)]/g, "").replace(/\s+/g, " ").trim() || scene.id;
  const badge = vtMarkBadge(scene);
  return `生成北极星 · ${badge} ${title}（${scene.id}）`;
}

export function formatVtGlobalChoiceLabel(globalMark: VtGlobalMark): string {
  const badge = vtMarkBadge(globalMark);
  return `生成北极星 · ${badge} 全局`;
}

/** Markdown board for the scope prompt. */
export function formatVtProgressBoard(
  globalMark: VtGlobalMark,
  scenes: VtSceneMark[],
): string {
  const lines: string[] = ["### 北极星进度", ""];
  const gBadge = vtMarkBadge(globalMark);
  const gBind = globalMark.ready
    ? "已绑定 brief"
    : globalMark.has_selected_image
      ? "磁盘有图，brief 未绑定"
      : "未选";
  lines.push(`- 全局：${gBadge} · ${gBind}`);
  for (const s of scenes) {
    const title = (s.title || s.id).trim();
    const badge = vtMarkBadge(s);
    const bind = s.ready
      ? "已绑定 brief"
      : s.has_selected_image
        ? "磁盘有图，brief 未绑定"
        : "未选";
    lines.push(`- **${title}**（\`${s.id}\`）：${badge} · ${bind}`);
  }
  const marked = scenes.filter((s) => vtIsMarked(s)).length;
  lines.push("");
  lines.push(
    `场景进度：**${marked}/${scenes.length}** 已有北极星` +
      (vtIsMarked(globalMark) ? "；全局已有" : "；全局未选") +
      "。点下方按钮生成或重选。",
  );
  return lines.join("\n");
}

export function formatVtStickyHint(
  globalMark: VtGlobalMark,
  scenes: VtSceneMark[],
): string {
  if (!scenes.length) {
    return vtIsMarked(globalMark)
      ? `✓ 全局北极星${globalMark.selected_id ? ` · 选 ${globalMark.selected_id}` : ""}`
      : "Brief 已保存 · 建议先生成并选用北极星图";
  }
  const marked = scenes.filter((s) => vtIsMarked(s)).length;
  const g = vtIsMarked(globalMark)
    ? `全局${vtMarkBadge(globalMark)}`
    : "全局○";
  return `北极星 ${marked}/${scenes.length} 场景 · ${g}`;
}
