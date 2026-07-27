import { useEffect, useRef, useState } from "react";
import {
  externalBriefRel,
  isExternalBriefRel,
  parseExternalBriefId,
  slugFromBriefRel,
} from "../chat/projectPaths";

export type ProjectBriefItem = {
  path: string;
  label: string;
  status?: "ready" | "draft";
  external?: boolean;
};

interface Props {
  activeBriefRel: string | null;
  /** Display name for active project (e.g. external display_name). */
  activeProjectLabel?: string | null;
  onSelect: (briefRel: string) => void;
  /** Start a fresh planner draft unbound from the current project. */
  onNewProject?: () => void;
  /** Compact chip for topbar vs fuller control for docs panel */
  variant?: "chip" | "panel";
}

export function ProjectSwitcher({
  activeBriefRel,
  activeProjectLabel,
  onSelect,
  onNewProject,
  variant = "chip",
}: Props) {
  const [open, setOpen] = useState(false);
  const [briefs, setBriefs] = useState<ProjectBriefItem[]>([]);
  const [loading, setLoading] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const activeNorm = activeBriefRel?.replace(/\\/g, "/") ?? null;
  const activeItem = activeNorm ? briefs.find((b) => b.path === activeNorm) : undefined;
  const slug =
    activeProjectLabel ||
    activeItem?.label ||
    (activeBriefRel ? slugFromBriefRel(activeBriefRel) : null);

  const loadBriefs = async () => {
    if (!window.gameFactory?.listBriefs) {
      setBriefs([]);
      return;
    }
    setLoading(true);
    try {
      const [builtIn, externalRes] = await Promise.all([
        window.gameFactory.listBriefs(),
        window.gameFactory.externalProjectsList?.() ?? Promise.resolve({ ok: true, projects: [], count: 0 }),
      ]);
      const builtInPaths = new Set(
        (builtIn || []).map((b) => String(b.path || "").replace(/\\/g, "/")),
      );
      const merged: ProjectBriefItem[] = (builtIn || []).map((b) => ({
        path: String(b.path || "").replace(/\\/g, "/"),
        label: b.label || slugFromBriefRel(String(b.path || "")),
        status: b.status === "draft" ? "draft" : "ready",
      }));
      for (const entry of externalRes.projects || []) {
        const id = String(entry.id || "").trim();
        if (!id) continue;
        const path = externalBriefRel(id);
        if (builtInPaths.has(path)) continue;
        merged.push({
          path,
          label: entry.display_name || id,
          status: "draft",
          external: true,
        });
      }
      setBriefs(merged);
    } catch {
      setBriefs([]);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenExternal = async () => {
    if (!window.gameFactory?.externalProjectOpen) return;
    setLoading(true);
    try {
      const res = await window.gameFactory.externalProjectOpen();
      if (res.canceled) return;
      if (!res.ok || !res.briefRel) return;
      await loadBriefs();
      onSelect(res.briefRel);
      setOpen(false);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveExternal = async (e: React.MouseEvent, extId: string) => {
    e.stopPropagation();
    if (!window.gameFactory?.externalProjectRemove) return;
    setLoading(true);
    try {
      await window.gameFactory.externalProjectRemove(extId);
      await loadBriefs();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!open) return;
    void loadBriefs();
  }, [open]);

  useEffect(() => {
    if (!activeBriefRel || !isExternalBriefRel(activeBriefRel) || activeProjectLabel) return;
    void loadBriefs();
  }, [activeBriefRel, activeProjectLabel]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const label = slug ? `工程 · ${slug}` : "未选择工程";

  return (
    <div
      className={`project-switcher project-switcher--${variant}`}
      ref={rootRef}
    >
      <button
        type="button"
        className={`project-switcher__btn ${slug ? "" : "project-switcher__btn--empty"}`}
        title={activeBriefRel || "选择或导出 Brief 以绑定当前工程"}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="project-switcher__dot" aria-hidden />
        <span className="project-switcher__label">{label}</span>
        <span className="project-switcher__caret" aria-hidden>
          ▾
        </span>
      </button>
      {open && (
        <div className="project-switcher__menu" role="listbox">
          {onNewProject && (
            <button
              type="button"
              className="project-switcher__item project-switcher__item--new"
              onClick={() => {
                onNewProject();
                setOpen(false);
              }}
            >
              <span className="project-switcher__item-slug">＋ 新建项目</span>
              <span className="project-switcher__item-path">
                先创建 projects/&lt;目录名&gt;/ 并绑定，文档只显示本工程
              </span>
            </button>
          )}
          <button
            type="button"
            className="project-switcher__item project-switcher__item--new"
            onClick={() => void handleOpenExternal()}
          >
            <span className="project-switcher__item-slug">打开外置工程…</span>
            <span className="project-switcher__item-path">
              选择已有 Godot 工程目录（产物写在外置根）
            </span>
          </button>
          {loading && <div className="project-switcher__empty">加载中…</div>}
          {!loading && briefs.length === 0 && (
            <div className="project-switcher__empty">暂无工程。点上方「新建项目」或「打开外置工程…」。</div>
          )}
          {!loading &&
            briefs.map((b) => {
              const rowSlug = b.external ? b.label : slugFromBriefRel(b.path);
              const active = activeNorm === b.path;
              const draft = b.status === "draft";
              const extId = b.external ? parseExternalBriefId(b.path) : null;
              return (
                <button
                  key={b.path}
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={`project-switcher__item ${active ? "project-switcher__item--active" : ""}`}
                  onClick={() => {
                    onSelect(b.path);
                    setOpen(false);
                  }}
                >
                  <span className="project-switcher__item-slug">
                    {rowSlug}
                    {b.external && (
                      <span className="project-switcher__badge" title="外置工程">
                        外置
                      </span>
                    )}
                    {draft ? " · 草稿" : ""}
                    {extId && (
                      <span
                        role="button"
                        tabIndex={0}
                        className="project-switcher__remove"
                        title="从列表移除外置工程（不删除磁盘）"
                        onClick={(e) => void handleRemoveExternal(e, extId)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            e.stopPropagation();
                            void handleRemoveExternal(e as unknown as React.MouseEvent, extId);
                          }
                        }}
                      >
                        移除
                      </span>
                    )}
                  </span>
                  <span className="project-switcher__item-path">{b.label || b.path}</span>
                </button>
              );
            })}
        </div>
      )}
    </div>
  );
}
