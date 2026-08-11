/** Compact host-tool strip below the composer (not chat chips). */

export type BriefWorkstationAction =
  | "makeability"
  | "enrich"
  | "topic"
  | "ui"
  | "autofix"
  | "export";

export type FocusOption = {
  value: string; // "" | "project" | "scene:id" | "system:id" | "asset:id"
  label: string;
  group?: string;
};

interface Props {
  disabled?: boolean;
  showMakeability?: boolean;
  showEnrich?: boolean;
  showTopic?: boolean;
  showUi?: boolean;
  showAutofix?: boolean;
  showExport?: boolean;
  /** When false, 存 stays visible but disabled (title shows why). */
  exportEnabled?: boolean;
  exportHint?: string;
  onAction: (action: BriefWorkstationAction) => void;
  /** Conversation focus dropdown (session.focus). */
  focusValue?: string;
  focusOptions?: FocusOption[];
  onFocusChange?: (value: string) => void;
}

const TOOLS: Array<{
  id: BriefWorkstationAction;
  label: string;
  title: string;
  showKey: "showMakeability" | "showEnrich" | "showTopic" | "showUi" | "showAutofix" | "showExport";
  primary?: boolean;
}> = [
  {
    id: "makeability",
    label: "审",
    title: "制作审查 · 独立 Critic 子 Agent",
    showKey: "showMakeability",
  },
  {
    id: "enrich",
    label: "补",
    title: "补全细节 · 宿主固定功能",
    showKey: "showEnrich",
  },
  {
    id: "topic",
    label: "议",
    title: "议题头脑风暴 · 宿主固定功能",
    showKey: "showTopic",
  },
  {
    id: "ui",
    label: "UI",
    title: "生成 UI 示意 · 宿主固定功能",
    showKey: "showUi",
  },
  {
    id: "autofix",
    label: "修",
    title: "自动修 brief · 宿主固定功能",
    showKey: "showAutofix",
  },
  {
    id: "export",
    label: "存",
    title: "保存 Brief · 宿主固定功能",
    showKey: "showExport",
    primary: true,
  },
];

export function BriefWorkstationBar({
  disabled = false,
  exportEnabled = true,
  exportHint,
  onAction,
  focusValue = "",
  focusOptions,
  onFocusChange,
  ...flags
}: Props) {
  const visible = TOOLS.filter((t) => Boolean(flags[t.showKey]));
  const showFocus = Boolean(onFocusChange);

  if (!visible.length && !showFocus) return null;

  const groups = new Map<string, FocusOption[]>();
  const ungrouped: FocusOption[] = [];
  for (const opt of focusOptions || []) {
    if (opt.group) {
      const list = groups.get(opt.group) || [];
      list.push(opt);
      groups.set(opt.group, list);
    } else {
      ungrouped.push(opt);
    }
  }

  return (
    <div className="brief-workstation" role="toolbar" aria-label="策划固定功能">
      {showFocus ? (
        <label className="brief-workstation__focus">
          <span className="brief-workstation__focus-label">焦点</span>
          <select
            className="brief-workstation__focus-select"
            disabled={disabled}
            value={focusValue}
            title="对话焦点：决定本轮改哪一册"
            aria-label="对话焦点"
            onChange={(e) => onFocusChange?.(e.target.value)}
          >
            <option value="">未钉住</option>
            {ungrouped.map((opt) => (
              <option key={opt.value || "empty"} value={opt.value}>
                {opt.label}
              </option>
            ))}
            {[...groups.entries()].map(([group, opts]) => (
              <optgroup key={group} label={group}>
                {opts.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
      ) : null}
      {visible.map((t) => {
        const exportBlocked = t.id === "export" && !exportEnabled;
        const btnDisabled = disabled || exportBlocked;
        const title =
          t.id === "export"
            ? exportHint || t.title
            : t.title;
        return (
          <button
            key={t.id}
            type="button"
            className={
              "brief-workstation__btn" +
              (t.primary ? " brief-workstation__btn--primary" : "")
            }
            disabled={btnDisabled}
            title={title}
            aria-label={title}
            onClick={() => onAction(t.id)}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
