import type { CSSProperties } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { HostChatDraftBrief, HostChatDraftDocument, HostChatStatus } from "../chat/types";
import {
  isExternalBriefRel,
  parseExternalBriefId,
  planTargetsFromBrief,
  planTargetsFromExternalEntry,
  slugFromBriefRel,
  type PlanTargets,
} from "../chat/projectPaths";
import { ProjectSwitcher } from "./ProjectSwitcher";
import {
  briefMakeabilityGateHint,
  catalogDisplayTitle,
  catalogRowsFromDraft,
  docsViewFromFocus,
  focusKey,
  formatBriefCatalogOverview,
  formatMakeabilityProductionSummary,
  formatShardDocument,
  inlineShardFromDraft,
  shardEntryHasBody,
  shardRelPath,
  tryFormatBriefJsonText,
  type DocsShardKind,
  type DocsView,
} from "./briefPreviewFormat";
import type { ExternalProjectEntry } from "../vite-env";

export type DocListItem = {
  id: string;
  label: string;
  source: "session" | "disk";
  kind: "brief" | "markdown" | "json";
  hint?: string;
  path?: string;
};

interface Props {
  draftBrief: HostChatDraftBrief | null;
  draftDocument: HostChatDraftDocument | null;
  status: HostChatStatus | null;
  activeBriefRel: string | null;
  /** Registry entries for external:<id>/brief.json path display. */
  externalEntryById?: Record<string, ExternalProjectEntry>;
  activeProjectLabel?: string | null;
  readyToExport: boolean;
  onExportBrief?: () => void;
  /** Write ui-wireframe.md from draft project.ui_panels. */
  onUiWireframe?: () => void;
  onAutofix?: () => void;
  onMakeability?: () => void;
  onEnrich?: () => void;
  onTopicBrainstorm?: () => void;
  onRefresh?: () => void;
  onSelectProject?: (briefRel: string) => void;
  /** Create+bind a new project from the docs panel switcher. */
  onNewProject?: () => void;
  busy?: boolean;
  /** Bump after export so disk list reloads. */
  diskRefreshKey?: number;
  /** Prefer selecting this repo-relative path after refresh (e.g. brief.json). */
  focusDiskRel?: string | null;
  /** Clear sticky focus after user picks another doc (or after focus applied). */
  onFocusDiskRelConsumed?: () => void;
  /** Optional width override from chat-layout resize handle. */
  style?: CSSProperties;
}

function targetsForBrief(
  briefRel: string,
  externalEntryById?: Record<string, ExternalProjectEntry>,
): PlanTargets {
  if (isExternalBriefRel(briefRel)) {
    const id = parseExternalBriefId(briefRel);
    const entry = id && externalEntryById ? externalEntryById[id] : undefined;
    if (entry) return planTargetsFromExternalEntry(entry);
  }
  return planTargetsFromBrief(briefRel);
}

function parseSessionShardKey(
  value: string,
): { kind: DocsShardKind; id: string } | null {
  const m = value.match(/^session-brief:(scene|system|asset):(.+)$/);
  if (!m) return null;
  return { kind: m[1] as DocsShardKind, id: m[2] };
}

export function DocsPreviewPanel({
  draftBrief,
  draftDocument,
  status,
  activeBriefRel,
  externalEntryById,
  activeProjectLabel,
  readyToExport,
  onExportBrief,
  onUiWireframe,
  onAutofix,
  onMakeability,
  onEnrich,
  onTopicBrainstorm,
  onRefresh,
  onSelectProject,
  onNewProject,
  busy,
  diskRefreshKey = 0,
  focusDiskRel = null,
  onFocusDiskRelConsumed,
  style,
}: Props) {
  const projectSlug = activeProjectLabel
    || (activeBriefRel ? slugFromBriefRel(activeBriefRel) : null);
  const [selectedId, setSelectedId] = useState("session-brief");
  const [diskBody, setDiskBody] = useState("");
  const [diskError, setDiskError] = useState("");
  const [diskLoading, setDiskLoading] = useState(false);
  const [diskDocs, setDiskDocs] = useState<DocListItem[]>([]);
  const [diskListTick, setDiskListTick] = useState(0);
  const [docsView, setDocsView] = useState<DocsView>({ mode: "overview" });
  const [shardBody, setShardBody] = useState("");
  const [shardError, setShardError] = useState("");
  const [shardLoading, setShardLoading] = useState(false);
  /** Last focusDiskRel we already jumped to — avoid sticky re-select on every click. */
  const appliedFocusRelRef = useRef<string | null>(null);
  const lastFollowedFocusRef = useRef<string | null>(null);

  const projectRootRel = useMemo(() => {
    if (!activeBriefRel) return null;
    try {
      return targetsForBrief(activeBriefRel, externalEntryById).projectRootRel;
    } catch {
      return null;
    }
  }, [activeBriefRel, externalEntryById]);

  const catalogRows = useMemo(() => catalogRowsFromDraft(draftBrief), [draftBrief]);

  const sessionDocs = useMemo(() => {
    const items: DocListItem[] = [
      {
        id: "session-brief",
        label: "Brief 工作草稿",
        source: "session",
        kind: "brief",
        hint: readyToExport
          ? "可导出"
          : draftBrief
            ? (status?.gaps?.length ?? 0) > 0
              ? `${status!.gaps!.length} 条结构问题`
              : "草稿中"
            : "尚未成形",
      },
    ];
    if (draftDocument?.body || draftDocument?.title) {
      items.push({
        id: "session-doc",
        label: draftDocument.title || "设计文档草稿",
        source: "session",
        kind: "markdown",
        hint: "会话内",
      });
    }
    return items;
  }, [draftBrief, draftDocument, readyToExport, status?.gaps]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (!window.gameFactory?.listProjectDocs) {
        console.warn("[docs] listProjectDocs API missing");
        setDiskDocs([]);
        return;
      }
      try {
        const items = await window.gameFactory.listProjectDocs(activeBriefRel || undefined);
        if (cancelled) return;
        if (import.meta.env.DEV) {
          console.info("[docs] listProjectDocs", {
            activeBriefRel,
            count: (items || []).length,
            paths: (items || []).map((d) => d.path),
          });
        }
        setDiskDocs(
          (items || []).map((d) => {
            const full = d.path;
            let hint = full;
            if (activeBriefRel) {
              try {
                const root = targetsForBrief(activeBriefRel, externalEntryById).projectRootRel;
                if (root && full.startsWith(`${root}/`)) {
                  hint = full.slice(root.length + 1);
                }
              } catch {
                /* keep full */
              }
            }
            return {
              id: `disk:${d.path}`,
              label: d.label,
              source: "disk" as const,
              kind: d.kind,
              path: d.path,
              hint,
            };
          }),
        );
      } catch (err) {
        console.warn("[docs] listProjectDocs failed", err);
        if (!cancelled) setDiskDocs([]);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [activeBriefRel, draftBrief, readyToExport, diskListTick, externalEntryById]);

  useEffect(() => {
    if (diskRefreshKey > 0) {
      setDiskListTick((n) => n + 1);
    }
  }, [diskRefreshKey]);

  const allDocs = useMemo(() => [...sessionDocs, ...diskDocs], [sessionDocs, diskDocs]);

  // One-shot jump when parent asks to focus a disk path (e.g. after export).
  useEffect(() => {
    if (!focusDiskRel) {
      appliedFocusRelRef.current = null;
      return;
    }
    if (appliedFocusRelRef.current === focusDiskRel) return;
    const want = `disk:${focusDiskRel.replace(/\\/g, "/")}`;
    if (!allDocs.some((d) => d.id === want)) return;
    setSelectedId(want);
    appliedFocusRelRef.current = focusDiskRel;
    onFocusDiskRelConsumed?.();
  }, [allDocs, focusDiskRel, onFocusDiskRelConsumed]);

  useEffect(() => {
    if (!allDocs.some((d) => d.id === selectedId)) {
      setSelectedId(allDocs[0]?.id || "session-brief");
    }
  }, [allDocs, selectedId]);

  // External pin → jump docs select to that shard (preview only).
  useEffect(() => {
    const key = focusKey(status?.focus);
    if (!key) {
      lastFollowedFocusRef.current = null;
      return;
    }
    if (lastFollowedFocusRef.current === key) return;
    const next = docsViewFromFocus(status?.focus);
    if (!next) {
      // Consume unmappable focus so a later remappable focus with the same prior
      // key (e.g. scene → visual_target global → scene) can follow again.
      lastFollowedFocusRef.current = key;
      return;
    }
    lastFollowedFocusRef.current = key;
    setSelectedId("session-brief");
    setDocsView(next);
  }, [status?.focus]);

  const selectDoc = (id: string) => {
    setSelectedId(id);
    if (id === "session-brief") {
      setDocsView({ mode: "overview" });
    }
    if (focusDiskRel) onFocusDiskRelConsumed?.();
  };

  const applyDocSelect = (value: string) => {
    const shard = parseSessionShardKey(value);
    if (value === "session-brief") {
      selectDoc("session-brief");
      setDocsView({ mode: "overview" });
      return;
    }
    if (shard) {
      setSelectedId("session-brief");
      setDocsView({ mode: "shard", kind: shard.kind, id: shard.id });
      if (focusDiskRel) onFocusDiskRelConsumed?.();
      return;
    }
    selectDoc(value);
  };

  const docSelectValue = useMemo(() => {
    if (selectedId === "session-brief") {
      if (docsView.mode === "shard") {
        return `session-brief:${docsView.kind}:${docsView.id}`;
      }
      return "session-brief";
    }
    return selectedId;
  }, [selectedId, docsView]);

  const selected = allDocs.find((d) => d.id === selectedId) || allDocs[0];

  useEffect(() => {
    let cancelled = false;
    const loadDisk = async () => {
      if (!selected || selected.source !== "disk" || !selected.path) {
        setDiskBody("");
        setDiskError("");
        return;
      }
      if (!window.gameFactory?.readRepoText) {
        setDiskError("当前 GUI 不支持读仓库文件，请重启应用。");
        return;
      }
      setDiskLoading(true);
      setDiskError("");
      try {
        const res = await window.gameFactory.readRepoText(selected.path);
        if (cancelled) return;
        if (!res.ok) {
          setDiskBody("");
          setDiskError(res.error || "读取失败");
        } else {
          setDiskBody(res.text || "");
        }
      } catch (e) {
        if (!cancelled) {
          setDiskBody("");
          setDiskError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (!cancelled) setDiskLoading(false);
      }
    };
    void loadDisk();
    return () => {
      cancelled = true;
    };
  }, [selected?.id, selected?.path, selected?.source]);

  useEffect(() => {
    let cancelled = false;
    const loadShard = async () => {
      if (selected?.id !== "session-brief" || docsView.mode !== "shard") {
        setShardBody("");
        setShardError("");
        setShardLoading(false);
        return;
      }
      const applyInlineFallback = (diskError?: string) => {
        const inline = inlineShardFromDraft(draftBrief, docsView.kind, docsView.id);
        if (inline && shardEntryHasBody(inline)) {
          const note = diskError
            ? `_磁盘分册不可用（${diskError}），以下为会话草稿内嵌正文。_\n\n`
            : `_未找到磁盘分册，以下为会话草稿内嵌正文。_\n\n`;
          setShardError("");
          setShardBody(note + formatShardDocument(docsView.kind, docsView.id, inline));
          return true;
        }
        if (inline) {
          setShardError("");
          setShardBody(
            formatShardDocument(docsView.kind, docsView.id, inline) +
              "\n\n_（仅目录条目；磁盘分册尚未落盘或无可读正文。）_",
          );
          return true;
        }
        return false;
      };

      if (!projectRootRel) {
        if (applyInlineFallback("无项目根目录")) return;
        setShardBody("");
        setShardError("当前工程没有可解析的项目根目录，无法读分册。");
        return;
      }
      if (!window.gameFactory?.readRepoText) {
        if (applyInlineFallback("GUI 不支持读盘")) return;
        setShardError("当前 GUI 不支持读仓库文件，请重启应用。");
        return;
      }
      const rel = shardRelPath(
        projectRootRel,
        docsView.kind,
        docsView.id,
        catalogRows.find((r) => r.kind === docsView.kind && r.id === docsView.id)?.path,
      );
      setShardLoading(true);
      setShardError("");
      try {
        const res = await window.gameFactory.readRepoText(rel);
        if (cancelled) return;
        if (!res.ok) {
          if (applyInlineFallback(res.error || `读分册失败：${rel}`)) return;
          setShardBody("");
          setShardError(res.error || `读分册失败：${rel}`);
          return;
        }
        const text = res.text || "";
        try {
          const parsed = JSON.parse(text) as unknown;
          setShardBody(formatShardDocument(docsView.kind, docsView.id, parsed));
        } catch {
          setShardBody(text);
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : String(e);
          if (applyInlineFallback(msg)) return;
          setShardBody("");
          setShardError(msg);
        }
      } finally {
        if (!cancelled) setShardLoading(false);
      }
    };
    void loadShard();
    return () => {
      cancelled = true;
    };
  }, [selected?.id, docsView, projectRootRel, catalogRows, draftBrief]);

  const sessionBody = useMemo(() => {
    if (!selected || selected.source !== "session") return "";
    if (selected.id === "session-doc") {
      const title = draftDocument?.title || "设计文档";
      const body = draftDocument?.body || "（正文为空）";
      return body.startsWith("#") ? body : `# ${title}\n\n${body}`;
    }
    if (docsView.mode === "shard") {
      if (shardLoading) return "读取分册中…";
      if (shardError) return shardError;
      return shardBody || "（分册为空）";
    }
    return formatBriefCatalogOverview(draftBrief, status);
  }, [
    selected,
    draftBrief,
    draftDocument,
    status,
    docsView,
    shardLoading,
    shardError,
    shardBody,
  ]);

  const previewBody = useMemo(() => {
    if (selected?.source === "disk") {
      if (diskLoading) return "读取中…";
      if (diskError) return diskError;
      if (selected.kind === "brief" || /\.json$/i.test(selected.path || "")) {
        const formatted = tryFormatBriefJsonText(diskBody, null);
        if (formatted) return formatted;
      }
      return diskBody;
    }
    return sessionBody;
  }, [selected?.source, selected?.kind, diskLoading, diskError, diskBody, sessionBody]);

  const productionMakeabilityLine = useMemo(() => {
    if (selected?.source !== "disk" || !diskBody || diskLoading || diskError) return null;
    const pathNorm = (selected.path || "").replace(/\\/g, "/");
    if (!pathNorm.endsWith("production.json")) return null;
    try {
      const parsed = JSON.parse(diskBody) as Record<string, unknown>;
      const doc =
        parsed.production_doc && typeof parsed.production_doc === "object"
          ? (parsed.production_doc as Record<string, unknown>)
          : parsed;
      return formatMakeabilityProductionSummary(doc);
    } catch {
      return null;
    }
  }, [selected?.source, selected?.path, diskBody, diskLoading, diskError]);

  const exportGateHint = briefMakeabilityGateHint(status);
  const emptyHint =
    selected?.id === "session-brief" && !draftBrief
      ? "和策划聊聊玩法后，这里会实时出现 Brief 全文预览。"
      : selected?.id === "session-doc" && !draftDocument?.body
        ? "说「整理成设计说明」后，这里会显示 Markdown 文档。"
        : "";

  const showBriefChrome = selected?.id === "session-brief";
  const previewError =
    (selected?.source === "disk" && Boolean(diskError)) ||
    (showBriefChrome && docsView.mode === "shard" && Boolean(shardError));

  return (
    <aside className="side-panel docs-preview-panel" style={style}>
      <div className="side-panel__head">
        <h2>{projectSlug ? `文档 · ${projectSlug}` : "文档"}</h2>
        {onSelectProject ? (
          <ProjectSwitcher
            variant="panel"
            activeBriefRel={activeBriefRel}
            onSelect={onSelectProject}
            onNewProject={onNewProject}
          />
        ) : null}
        <label className="docs-doc-select">
          <select
            className="docs-doc-select__control"
            value={
              allDocs.some((d) => d.id === selectedId) || docSelectValue.startsWith("session-brief:")
                ? docSelectValue
                : allDocs[0]?.id || "session-brief"
            }
            onChange={(e) => applyDocSelect(e.target.value)}
            aria-label="选择文档"
          >
            <optgroup label="会话">
              {sessionDocs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.label}
                  {doc.id === "session-brief" ? " · 总览" : ""}
                </option>
              ))}
              {draftBrief
                ? catalogRows
                    .filter((r) => r.kind === "scene")
                    .map((row) => (
                      <option key={`scene:${row.id}`} value={`session-brief:scene:${row.id}`}>
                        场景 · {catalogDisplayTitle(row)}
                      </option>
                    ))
                : null}
              {draftBrief
                ? catalogRows
                    .filter((r) => r.kind === "system")
                    .map((row) => (
                      <option key={`system:${row.id}`} value={`session-brief:system:${row.id}`}>
                        系统 · {catalogDisplayTitle(row)}
                      </option>
                    ))
                : null}
              {draftBrief
                ? catalogRows
                    .filter((r) => r.kind === "asset")
                    .map((row) => (
                      <option key={`asset:${row.id}`} value={`session-brief:asset:${row.id}`}>
                        资产 · {catalogDisplayTitle(row)}
                      </option>
                    ))
                : null}
            </optgroup>
            {diskDocs.length ? (
              <optgroup label="磁盘">
                {diskDocs.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.label}
                  </option>
                ))}
              </optgroup>
            ) : null}
          </select>
        </label>
      </div>

      {productionMakeabilityLine ? (
        <p className="hint docs-preview-makeability">{productionMakeabilityLine}</p>
      ) : null}

      <div className="docs-preview-body">
        {emptyHint && !previewBody ? (
          <p className="brief-draft-empty">{emptyHint}</p>
        ) : (
          <pre
            className={`docs-preview-content mono ${previewError ? "docs-preview-content--error" : ""}`}
          >
            {previewBody || "（空）"}
          </pre>
        )}
      </div>

      {status?.gaps && status.gaps.length > 0 && selected?.id === "session-brief" && (
        <div className="brief-draft-gaps">
          <h3>还缺（{status.gaps.length}）</h3>
          <ul>
            {status.gaps.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
          {onAutofix && (
            <button
              type="button"
              className="btn btn--primary brief-draft-autofix"
              onClick={onAutofix}
              disabled={busy}
              title="把上述校验错误交给策划 LLM，自动改草稿直到通过或达轮次上限"
            >
              自动修到可导出
            </button>
          )}
        </div>
      )}

      <div className="board-actions">
        <button
          type="button"
          className="btn btn--secondary"
          onClick={() => {
            setDiskListTick((n) => n + 1);
            onRefresh?.();
          }}
          disabled={busy}
        >
          刷新
        </button>
        {onAutofix && selected?.id === "session-brief" && (status?.gaps?.length || 0) > 0 && (
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onAutofix}
            disabled={busy}
            title="自动读取右侧 gaps 并循环修复"
          >
            自动修
          </button>
        )}
        {onMakeability && selected?.id === "session-brief" && draftBrief && (
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onMakeability}
            disabled={busy}
            title="独立子 LLM 审查 draft brief 的制作完备性"
          >
            制作审查
          </button>
        )}
        {onEnrich && selected?.id === "session-brief" && draftBrief && (
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onEnrich}
            disabled={busy}
            title="开放式加厚玩家可见细节"
          >
            补全细节
          </button>
        )}
        {onTopicBrainstorm && selected?.id === "session-brief" && draftBrief && (
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onTopicBrainstorm}
            disabled={busy}
            title="针对议题多视角头脑风暴"
          >
            议题头脑风暴
          </button>
        )}
        {onUiWireframe && selected?.id === "session-brief" && draftBrief && activeBriefRel && (
          <button
            type="button"
            className="btn btn--secondary"
            onClick={onUiWireframe}
            disabled={busy}
            title="根据草稿中的 UI 面板列表生成字符线稿 ui-wireframe.md"
          >
            生成 UI 示意
          </button>
        )}
        {onExportBrief && selected?.id === "session-brief" && (
          <button
            type="button"
            className="btn btn--primary"
            onClick={onExportBrief}
            disabled={busy || !readyToExport}
            title={exportGateHint}
          >
            导出 Brief
          </button>
        )}
      </div>

      {activeBriefRel ? (
        <p className="docs-preview-footer hint">
          当前工程：{projectSlug}
          <br />
          {activeBriefRel}
          {(() => {
            try {
              const t = targetsForBrief(activeBriefRel, externalEntryById);
              return (
                <>
                  <br />
                  {t.productionRel} · {t.progressRel} · {t.manifestRel}
                </>
              );
            } catch {
              return null;
            }
          })()}
        </p>
      ) : (
        <p className="docs-preview-footer hint">未选择工程 — 文档列表不会混入其它游戏。</p>
      )}
    </aside>
  );
}
