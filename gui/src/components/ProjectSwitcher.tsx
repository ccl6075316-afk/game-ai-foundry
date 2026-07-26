import { useEffect, useRef, useState } from "react";
import { slugFromBriefRel } from "../chat/projectPaths";

export type ProjectBriefItem = {
  path: string;
  label: string;
  status?: "ready" | "draft";
};

interface Props {
  activeBriefRel: string | null;
  onSelect: (briefRel: string) => void;
  /** Start a fresh planner draft unbound from the current project. */
  onNewProject?: () => void;
  /** Compact chip for topbar vs fuller control for docs panel */
  variant?: "chip" | "panel";
}

export function ProjectSwitcher({
  activeBriefRel,
  onSelect,
  onNewProject,
  variant = "chip",
}: Props) {
  const [open, setOpen] = useState(false);
  const [briefs, setBriefs] = useState<ProjectBriefItem[]>([]);
  const [loading, setLoading] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const slug = activeBriefRel ? slugFromBriefRel(activeBriefRel) : null;

  const loadBriefs = async () => {
    if (!window.gameFactory?.listBriefs) {
      setBriefs([]);
      return;
    }
    setLoading(true);
    try {
      const items = await window.gameFactory.listBriefs();
      setBriefs(
        (items || []).map((b) => ({
          path: String(b.path || "").replace(/\\/g, "/"),
          label: b.label || slugFromBriefRel(String(b.path || "")),
          status: b.status === "draft" ? "draft" : "ready",
        })),
      );
    } catch {
      setBriefs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!open) return;
    void loadBriefs();
  }, [open]);

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
          {loading && <div className="project-switcher__empty">加载中…</div>}
          {!loading && briefs.length === 0 && (
            <div className="project-switcher__empty">暂无工程。点上方「新建项目」创建目录。</div>
          )}
          {!loading &&
            briefs.map((b) => {
              const s = slugFromBriefRel(b.path);
              const active = activeBriefRel?.replace(/\\/g, "/") === b.path;
              const draft = b.status === "draft";
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
                    {s}
                    {draft ? " · 草稿" : ""}
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
