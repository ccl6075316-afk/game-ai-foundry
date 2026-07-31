import { useState, type FormEvent, type KeyboardEvent } from "react";

interface Props {
  disabled?: boolean;
  busy?: boolean;
  choices?: string[];
  readyToExport?: boolean;
  showAutofix?: boolean;
  showMakeability?: boolean;
  exportGateHint?: string;
  placeholder?: string;
  hint?: string;
  onSend: (text: string) => void;
  onStop?: () => void;
  onChoice?: (text: string) => void;
  onExportBrief?: () => void;
  onAutofix?: () => void;
  onMakeability?: () => void;
  onEnrich?: () => void;
  onUiWireframe?: () => void;
  onTopicBrainstorm?: () => void;
}

export function ChatInput({
  disabled = false,
  busy = false,
  choices = [],
  readyToExport,
  showAutofix,
  showMakeability,
  exportGateHint,
  placeholder = "描述想法，或点下方快捷按钮…",
  hint = "Enter 发送 · 左侧切换同事 · 快捷按钮推进流水线",
  onSend,
  onStop,
  onChoice,
  onExportBrief,
  onAutofix,
  onMakeability,
  onEnrich,
  onUiWireframe,
  onTopicBrainstorm,
}: Props) {
  const [text, setText] = useState("");
  const locked = disabled || busy;

  const submit = () => {
    const v = text.trim();
    if (!v || locked) return;
    onSend(v);
    setText("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (busy) {
      onStop?.();
      return;
    }
    submit();
  };

  const pickChoice = (choice: string) => {
    if (locked) return;
    onChoice?.(choice);
  };

  return (
    <div className="composer">
      {(choices.length > 0 || readyToExport || showAutofix || showMakeability || onEnrich || onUiWireframe || onTopicBrainstorm) && (
        <div className="composer__chips">
          {choices.map((c) => (
            <button
              key={c}
              type="button"
              className="composer__chip"
              disabled={locked}
              onClick={() => pickChoice(c)}
            >
              {c}
            </button>
          ))}
          {showMakeability && (
            <button
              type="button"
              className="composer__chip"
              disabled={locked}
              onClick={() => onMakeability?.()}
              title="独立子 LLM 审查 draft brief 的制作完备性"
            >
              制作审查
            </button>
          )}
          {onEnrich && (
            <button
              type="button"
              className="composer__chip"
              disabled={locked}
              onClick={() => onEnrich()}
              title="开放式加厚玩家可见细节（可带要求二次补全）"
            >
              补全细节
            </button>
          )}
          {onUiWireframe && (
            <button
              type="button"
              className="composer__chip"
              disabled={locked}
              onClick={() => onUiWireframe()}
              title="从草稿 ui_panels 生成字符线稿 ui-wireframe.md"
            >
              生成 UI 示意
            </button>
          )}
          {onTopicBrainstorm && (
            <button
              type="button"
              className="composer__chip"
              disabled={locked}
              onClick={() => onTopicBrainstorm()}
              title="针对某一议题多视角头脑风暴，先拣再写回"
            >
              议题头脑风暴
            </button>
          )}
          {showAutofix && (
            <button
              type="button"
              className="composer__chip"
              disabled={locked}
              onClick={() => onAutofix?.()}
              title="自动读取校验错误并循环修复草稿"
            >
              自动修 brief
            </button>
          )}
          {readyToExport && (
            <button
              type="button"
              className="composer__chip composer__chip--primary"
              disabled={locked}
              onClick={() => onExportBrief?.()}
              title={exportGateHint || "导出到 projects/<slug>/"}
            >
              保存 Brief
            </button>
          )}
        </div>
      )}
      <form className="composer__box" onSubmit={onSubmit}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={busy ? "生成中…可点右侧停止" : placeholder}
          rows={1}
          disabled={locked}
        />
        {busy ? (
          <button
            type="button"
            className="composer__send composer__send--stop"
            onClick={() => onStop?.()}
            aria-label="停止"
            title="停止当前对话"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            type="submit"
            className="composer__send"
            disabled={disabled || !text.trim()}
            aria-label="发送"
          >
            <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
              <path
                d="M12 19V5M12 5l-5 5M12 5l5 5"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}
      </form>
      <p className="composer__hint">{busy ? "生成中 · 点停止可中断本轮对话" : hint}</p>
    </div>
  );
}
