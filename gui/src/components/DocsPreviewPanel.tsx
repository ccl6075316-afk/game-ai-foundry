import { useEffect, useMemo, useState } from "react";
import type { HostChatDraftBrief, HostChatDraftDocument, HostChatStatus } from "../chat/types";
import {
  planTargetsFromBrief,
  productionPathFromBrief,
  progressPathFromBrief,
  slugFromBriefRel,
} from "../chat/projectPaths";
import { ProjectSwitcher } from "./ProjectSwitcher";
import { formatBriefDocument, tryFormatBriefJsonText } from "./briefPreviewFormat";

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
  readyToExport: boolean;
  onExportBrief?: () => void;
  onAutofix?: () => void;
  onRefresh?: () => void;
  onSelectProject?: (briefRel: string) => void;
  busy?: boolean;
}

export function DocsPreviewPanel({
  draftBrief,
  draftDocument,
  status,
  activeBriefRel,
  readyToExport,
  onExportBrief,
  onAutofix,
  onRefresh,
  onSelectProject,
  busy,
}: Props) {
  const projectSlug = activeBriefRel ? slugFromBriefRel(activeBriefRel) : null;
  const [selectedId, setSelectedId] = useState("session-brief");
  const [diskBody, setDiskBody] = useState("");
  const [diskError, setDiskError] = useState("");
  const [diskLoading, setDiskLoading] = useState(false);
  const [diskDocs, setDiskDocs] = useState<DocListItem[]>([]);
  const [diskListTick, setDiskListTick] = useState(0);

  const sessionDocs = useMemo(() => {
    const items: DocListItem[] = [
      {
        id: "session-brief",
        label: "Brief 工作草稿",
        source: "session",
        kind: "brief",
        hint: readyToExport ? "可导出" : draftBrief ? "草稿中" : "尚未成形",
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
  }, [draftBrief, draftDocument, readyToExport]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (!window.gameFactory?.listProjectDocs) {
        setDiskDocs([]);
        return;
      }
      try {
        const items = await window.gameFactory.listProjectDocs(activeBriefRel || undefined);
        if (cancelled) return;
        setDiskDocs(
          (items || []).map((d) => {
            const full = d.path;
            let hint = full;
            if (activeBriefRel) {
              try {
                const root = planTargetsFromBrief(activeBriefRel).projectRootRel;
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
      } catch {
        if (!cancelled) setDiskDocs([]);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [activeBriefRel, draftBrief, readyToExport, diskListTick]);

  const allDocs = useMemo(() => [...sessionDocs, ...diskDocs], [sessionDocs, diskDocs]);

  useEffect(() => {
    if (!allDocs.some((d) => d.id === selectedId)) {
      setSelectedId(allDocs[0]?.id || "session-brief");
    }
  }, [allDocs, selectedId]);

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

  const sessionBody = useMemo(() => {
    if (!selected || selected.source !== "session") return "";
    if (selected.id === "session-doc") {
      const title = draftDocument?.title || "设计文档";
      const body = draftDocument?.body || "（正文为空）";
      return body.startsWith("#") ? body : `# ${title}\n\n${body}`;
    }
    return formatBriefDocument(draftBrief, status);
  }, [selected, draftBrief, draftDocument, status]);

  const previewBody = useMemo(() => {
    if (selected?.source === "disk") {
      if (diskLoading) return "读取中…";
      if (diskError) return diskError;
      if (selected.kind === "brief") {
        const formatted = tryFormatBriefJsonText(diskBody, null);
        if (formatted) return formatted;
      }
      return diskBody;
    }
    return sessionBody;
  }, [selected?.source, selected?.kind, diskLoading, diskError, diskBody, sessionBody]);
  const emptyHint =
    selected?.id === "session-brief" && !draftBrief
      ? "和策划聊聊玩法后，这里会实时出现 Brief 全文预览。"
      : selected?.id === "session-doc" && !draftDocument?.body
        ? "说「整理成设计说明」后，这里会显示 Markdown 文档。"
        : "";

  return (
    <aside className="side-panel docs-preview-panel">
      <div className="side-panel__head">
        <h2>{projectSlug ? `文档 · ${projectSlug}` : "文档"}</h2>
        <p className="hint">
          {projectSlug
            ? "仅显示当前工程落盘文件；上方可切换工程。"
            : "尚未绑定工程。导出 Brief 或从列表选择后，这里只显示该工程文档。"}
        </p>
        {onSelectProject ? (
          <ProjectSwitcher
            variant="panel"
            activeBriefRel={activeBriefRel}
            onSelect={onSelectProject}
          />
        ) : null}
      </div>

      <div className="docs-preview-list">
        {allDocs.map((doc) => (
          <button
            key={doc.id}
            type="button"
            className={`docs-preview-item ${selected?.id === doc.id ? "docs-preview-item--active" : ""}`}
            onClick={() => setSelectedId(doc.id)}
          >
            <span className="docs-preview-item__label">{doc.label}</span>
            {doc.hint ? <span className="docs-preview-item__hint">{doc.hint}</span> : null}
          </button>
        ))}
        {activeBriefRel && diskDocs.length === 0 ? (
          <p className="docs-preview-empty hint">当前工程还没有落盘文件（先导出 Brief）。</p>
        ) : null}
      </div>

      <div className="docs-preview-body">
        {emptyHint && !previewBody ? (
          <p className="brief-draft-empty">{emptyHint}</p>
        ) : (
          <pre className={`docs-preview-content mono ${diskError ? "docs-preview-content--error" : ""}`}>
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
        {onExportBrief && selected?.id === "session-brief" && (
          <button
            type="button"
            className="btn btn--primary"
            onClick={onExportBrief}
            disabled={busy || !readyToExport}
            title={readyToExport ? "导出到 projects/<slug>/" : "校验通过后可导出，或先点「自动修」"}
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
              const t = planTargetsFromBrief(activeBriefRel);
              return (
                <>
                  <br />
                  {productionPathFromBrief(activeBriefRel)} · {progressPathFromBrief(activeBriefRel)} ·{" "}
                  {t.manifestRel}
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
