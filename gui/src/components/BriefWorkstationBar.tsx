/** Compact host-tool strip below the composer (not chat chips). */

export type BriefWorkstationAction =
  | "makeability"
  | "enrich"
  | "topic"
  | "ui"
  | "autofix"
  | "export";

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
  ...flags
}: Props) {
  const visible = TOOLS.filter((t) => Boolean(flags[t.showKey]));
  if (!visible.length) return null;

  return (
    <div className="brief-workstation" role="toolbar" aria-label="策划固定功能">
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
