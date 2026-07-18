import type { ToolchainReport } from "../settings/toolchain";
import { autoInstallable } from "../settings/toolchain";
import { EnvComponentList } from "./EnvComponentList";
import type { EnvIssue } from "../settings/envHealth";

interface Props {
  report: ToolchainReport;
  extraIssues?: EnvIssue[];
  installing: string | null;
  installLog: string[];
  onDismiss: () => void;
  onInstall: (id: string) => void;
  onInstallAll: () => void;
  onOpenExternal: (url: string) => void;
  onOpenSettings: () => void;
}

export function ToolchainModal({
  report,
  extraIssues = [],
  installing,
  installLog,
  onDismiss,
  onInstall,
  onInstallAll,
  onOpenExternal,
  onOpenSettings,
}: Props) {
  const missing = report.components.filter((c) => !c.available);
  const autoItems = autoInstallable(report);
  const apiIssues = extraIssues.filter((i) => i.severity === "error");

  if (!missing.length && !apiIssues.length) return null;

  return (
    <div className="toolchain-overlay" role="dialog" aria-modal="true" aria-labelledby="toolchain-title">
      <div className="toolchain-modal">
        <header className="toolchain-modal__head">
          <h2 id="toolchain-title">环境检查未通过</h2>
          <p className="toolchain-modal__lead">
            发给别人用时请先看清下列错误。修完后点「重新检测」。可把本页文字复制给支持。
          </p>
        </header>

        {apiIssues.length > 0 && (
          <ul className="toolchain-modal__issues">
            {apiIssues.map((issue) => (
              <li key={issue.id}>
                <strong>{issue.title}</strong>
                <div className="toolchain-modal__issue-detail">{issue.detail}</div>
                <div className="toolchain-modal__issue-fix">→ {issue.fixHint}</div>
              </li>
            ))}
          </ul>
        )}

        {missing.length > 0 && (
          <EnvComponentList
            components={report.components}
            installing={installing}
            installLog={installLog}
            onInstall={onInstall}
            onOpenExternal={onOpenExternal}
            onOpenSettings={onOpenSettings}
            showAll={false}
          />
        )}

        <footer className="toolchain-modal__foot">
          {autoItems.length > 0 && (
            <button
              type="button"
              className="btn btn--primary"
              disabled={Boolean(installing)}
              onClick={onInstallAll}
            >
              {installing ? "正在安装…" : `自动安装可选项（${autoItems.length}）`}
            </button>
          )}
          <button type="button" className="btn btn--ghost" onClick={onOpenSettings}>
            打开设置
          </button>
          <button type="button" className="btn btn--ghost" onClick={onDismiss}>
            稍后
          </button>
        </footer>
      </div>
    </div>
  );
}
