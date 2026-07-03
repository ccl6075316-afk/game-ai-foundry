import { useMemo, useState } from "react";
import type { ToolchainComponent, ToolchainReport } from "../settings/toolchain";
import { autoInstallable } from "../settings/toolchain";

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

function actionLabel(item: ToolchainComponent): string {
  if (item.action === "auto" || item.action === "pip") return "下载安装";
  if (item.id === "godot") return "前往下载";
  return "打开下载页";
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
  const missing = useMemo(
    () => report.components.filter((c) => !c.available),
    [report.components],
  );
  const autoItems = useMemo(() => autoInstallable(report), [report]);
  const [expanded, setExpanded] = useState<string | null>(null);

  if (!missing.length) return null;

  const handlePrimary = (item: ToolchainComponent) => {
    if (item.action === "auto" || item.action === "pip") {
      onInstall(item.id);
      return;
    }
    if (item.download_url) onOpenExternal(item.download_url);
    if (item.id === "godot") onOpenSettings();
  };

  return (
    <div className="toolchain-overlay" role="dialog" aria-modal="true" aria-labelledby="toolchain-title">
      <div className="toolchain-modal">
        <header className="toolchain-modal__head">
          <h2 id="toolchain-title">首次运行 · 环境检查</h2>
          <p className="toolchain-modal__lead">
            类似 VS Code 扩展提示：检测到本机缺少运行管线所需的工具。Godot 为便携 zip，需手动下载后在设置中指定路径；其余可自动安装。
          </p>
        </header>

        <ul className="toolchain-list">
          {missing.map((item) => (
            <li key={item.id} className={`toolchain-item ${item.required ? "required" : "optional"}`}>
              <div className="toolchain-item__main">
                <div className="toolchain-item__title">
                  <span className={`toolchain-dot ${item.available ? "ok" : "no"}`} />
                  <strong>{item.label}</strong>
                  <span className="toolchain-badge">{item.required ? "必需" : "可选"}</span>
                </div>
                <p className="toolchain-item__desc">{item.description}</p>
                {item.id === "godot" && (
                  <p className="toolchain-item__hint">
                    下载解压后，在「设置 → 本机工具」中浏览选择 Godot 可执行文件。
                  </p>
                )}
              </div>
              <div className="toolchain-item__actions">
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  disabled={Boolean(installing)}
                  onClick={() => handlePrimary(item)}
                >
                  {installing === item.id ? "安装中…" : actionLabel(item)}
                </button>
                {(item.action === "auto" || item.action === "pip") && (
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                  >
                    日志
                  </button>
                )}
              </div>
              {expanded === item.id && installLog.length > 0 && (
                <pre className="toolchain-log">{installLog.slice(-12).join("\n")}</pre>
              )}
            </li>
          ))}
        </ul>

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
