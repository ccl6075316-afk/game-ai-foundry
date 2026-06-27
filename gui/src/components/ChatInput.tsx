import { useState, type FormEvent, type KeyboardEvent } from "react";

interface Props {
  disabled: boolean;
  choices?: string[];
  readyToExport?: boolean;
  onSend: (text: string) => void;
  onChoice?: (text: string) => void;
  onExportBrief?: () => void;
}

export function ChatInput({
  disabled,
  choices = [],
  readyToExport,
  onSend,
  onChoice,
  onExportBrief,
}: Props) {
  const [text, setText] = useState("");

  const submit = () => {
    const v = text.trim();
    if (!v || disabled) return;
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
    submit();
  };

  const pickChoice = (choice: string) => {
    if (disabled) return;
    onChoice?.(choice);
  };

  return (
    <div className="composer">
      {(choices.length > 0 || readyToExport) && (
        <div className="composer__chips">
          {choices.map((c) => (
            <button
              key={c}
              type="button"
              className="composer__chip"
              disabled={disabled}
              onClick={() => pickChoice(c)}
            >
              {c}
            </button>
          ))}
          {readyToExport && (
            <button
              type="button"
              className="composer__chip composer__chip--primary"
              disabled={disabled}
              onClick={() => onExportBrief?.()}
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
          placeholder="描述游戏想法，或输入 /brief /doctor /plan …"
          rows={1}
          disabled={disabled}
        />
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
      </form>
      <p className="composer__hint">Enter 发送 · `/run --run-prompts` 含文案生成 · `/brief save 名称` 导出</p>
    </div>
  );
}
