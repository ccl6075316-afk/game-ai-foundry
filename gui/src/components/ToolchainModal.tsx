import type { ToolchainReport } from "../settings/toolchain";
import { autoInstallable } from "../settings/toolchain";
import { EnvComponentList } from "./EnvComponentList";

interface Props {
  report: ToolchainReport;
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

  if (!missing.length) return null;

  return (
    <div className="toolchain-overlay" role="dialog" aria-modal="true" aria-labelledby="toolchain-title">
      <div className="toolchain-modal">
        <header className="toolchain-modal__head">
          <h2 id="toolchain-title">首次运行 · 环境检查</h2>
          <p className="toolchain-modal__lead">
            检测到本机缺少运行管线所需的工具。之后可在顶部工具栏「环境详情」随时复查与安装。
          </p>
        </header>

        <EnvComponentList
          components={report.components}
          installing={installing}
          installLog={installLog}
          onInstall={onInstall}
          onOpenExternal={onOpenExternal}
          onOpenSettings={onOpenSettings}
          showAll={false}
        />

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
