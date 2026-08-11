import { useState, type FormEvent, type KeyboardEvent } from "react";
import {
  BriefWorkstationBar,
  type BriefWorkstationAction,
  type FocusOption,
} from "./BriefWorkstationBar";

interface Props {
  disabled?: boolean;
  busy?: boolean;
  /** Main-LLM dialog suggestions only — never host tools / Critic gaps. */
  choices?: string[];
  /** Hide dialog suggestion chips (e.g. while Critic gap card needs answers). */
  hideDialogChoices?: boolean;
  readyToExport?: boolean;
  showAutofix?: boolean;
  showMakeability?: boolean;
  showEnrich?: boolean;
  showUiWireframe?: boolean;
  showTopicBrainstorm?: boolean;
  exportGateHint?: string;
  placeholder?: string;
  onSend: (text: string) => void;
  onStop?: () => void;
  onChoice?: (text: string) => void;
  onWorkstation?: (action: BriefWorkstationAction) => void;
  focusValue?: string;
  focusOptions?: FocusOption[];
  onFocusChange?: (value: string) => void;
}

export function ChatInput({
  disabled = false,
  busy = false,
  choices = [],
  hideDialogChoices = false,
  readyToExport,
  showAutofix,
  showMakeability,
  showEnrich,
  showUiWireframe,
  showTopicBrainstorm,
  exportGateHint,
  placeholder = "描述想法…",
  onSend,
  onStop,
  onChoice,
  onWorkstation,
  focusValue,
  focusOptions,
  onFocusChange,
}: Props) {
  const [text, setText] = useState("");
  const locked = disabled || busy;
  const dialogChoices = hideDialogChoices ? [] : choices;

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
      {dialogChoices.length > 0 && (
        <div className="composer__chips composer__chips--dialog" aria-label="对话建议">
          {dialogChoices.map((c) => (
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
      {onWorkstation && (
        <BriefWorkstationBar
          disabled={locked}
          showMakeability={showMakeability}
          showEnrich={showEnrich}
          showTopic={showTopicBrainstorm}
          showUi={showUiWireframe}
          showAutofix={showAutofix}
          showExport={true}
          exportEnabled={Boolean(readyToExport)}
          exportHint={exportGateHint}
          onAction={onWorkstation}
          focusValue={focusValue}
          focusOptions={focusOptions}
          onFocusChange={onFocusChange}
        />
      )}
    </div>
  );
}
