import { useEffect, useId, useState } from "react";
import { sanitizeProjectSlug } from "../chat/projectPaths";

interface Props {
  open: boolean;
  defaultSlug?: string;
  onCancel: () => void;
  /** Bind project folder; keep current planner chat. */
  onBind: (slug: string) => void;
  /** Bind and start a fresh planner chat (wipes current draft thread). */
  onBindAndReset: (slug: string) => void;
}

export function NewProjectModal({
  open,
  defaultSlug,
  onCancel,
  onBind,
  onBindAndReset,
}: Props) {
  const titleId = useId();
  const inputId = useId();
  const [value, setValue] = useState(defaultSlug || "fishing-2d");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setValue(defaultSlug || `game-${Date.now().toString(36)}`);
    setError(null);
  }, [open, defaultSlug]);

  if (!open) return null;

  const resolved = (): string | null => {
    const slug = sanitizeProjectSlug(value);
    if (!slug) {
      setError("请用英文小写和短横线，例如 fishing-2d");
      return null;
    }
    return slug;
  };

  return (
    <div className="toolchain-overlay" role="presentation" onMouseDown={onCancel}>
      <div
        className="toolchain-modal new-project-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="toolchain-modal__head">
          <h2 id={titleId}>工程目录</h2>
          <p className="toolchain-modal__lead">
            Electron 不支持系统弹窗，请在这里填写目录名。会使用{" "}
            <code>projects/目录名/</code>；文档栏只显示该工程。
          </p>
        </div>
        <label className="new-project-modal__label" htmlFor={inputId}>
          工程目录名（英文）
        </label>
        <input
          id={inputId}
          className="new-project-modal__input"
          autoFocus
          spellCheck={false}
          placeholder="fishing-2d"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              const slug = resolved();
              if (slug) onBind(slug);
            }
            if (e.key === "Escape") onCancel();
          }}
        />
        {error ? <p className="new-project-modal__error">{error}</p> : null}
        <p className="hint new-project-modal__hint">
          路径预览：projects/{sanitizeProjectSlug(value) || "…"}/
        </p>
        <div className="toolchain-modal__foot">
          <button type="button" className="btn btn--ghost" onClick={onCancel}>
            取消
          </button>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => {
              const slug = resolved();
              if (slug) onBindAndReset(slug);
            }}
            title="绑定目录并清空当前策划对话"
          >
            绑定并新开对话
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => {
              const slug = resolved();
              if (slug) onBind(slug);
            }}
            title="只绑定工程，保留当前策划对话（续写钓鱼草稿用这个）"
          >
            绑定工程
          </button>
        </div>
      </div>
    </div>
  );
}
