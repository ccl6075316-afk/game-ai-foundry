import { useState } from "react";
import type { ToolchainComponent } from "../settings/toolchain";

interface Props {
  components: ToolchainComponent[];
  installing: string | null;
  installLog: string[];
  onInstall: (id: string) => void;
  onOpenExternal: (url: string) => void;
  onOpenSettings?: () => void;
  showAll?: boolean;
}

function actionLabel(item: ToolchainComponent, installing: boolean): string {
  if (installing) return "安装中…";
  if (item.available) return "已就绪";
  if (item.action === "auto" || item.action === "pip") return "下载安装";
  if (item.id === "godot") return "前往下载";
  return "打开下载页";
}

export function EnvComponentList({
  components,
  installing,
  installLog,
  onInstall,
  onOpenExternal,
  onOpenSettings,
  showAll = true,
}: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const visible = showAll ? components : components.filter((c) => !c.available);

  const handleAction = (item: ToolchainComponent) => {
    if (item.available || installing) return;
    if (item.action === "auto" || item.action === "pip") {
      onInstall(item.id);
      return;
    }
    if (item.download_url) onOpenExternal(item.download_url);
    if (item.id === "godot") onOpenSettings?.();
  };

  return (
    <ul className="toolchain-list env-component-list">
      {visible.map((item) => {
        const busy = installing === item.id;
        const canAct = !item.available && !installing;
        return (
          <li
            key={item.id}
            className={`toolchain-item ${item.required ? "required" : "optional"} ${item.available ? "ready" : ""}`}
          >
            <div className="toolchain-item__main">
              <div className="toolchain-item__title">
                <span className={`toolchain-dot ${item.available ? "ok" : "no"}`} />
                <strong>{item.label}</strong>
                <span className="toolchain-badge">{item.required ? "必需" : "可选"}</span>
              </div>
              <p className="toolchain-item__desc">{item.description}</p>
              {item.path && <p className="toolchain-item__path mono">{item.path}</p>}
              {item.id === "godot" && !item.available && (
                <p className="toolchain-item__hint">解压后在「设置 → 本机工具」指定可执行文件。</p>
              )}
            </div>
            <div className="toolchain-item__actions">
              <button
                type="button"
                className={`btn btn--sm ${item.available ? "btn--ghost" : "btn--secondary"}`}
                disabled={!canAct && !item.available}
                onClick={() => handleAction(item)}
              >
                {actionLabel(item, busy)}
              </button>
              {(item.action === "auto" || item.action === "pip") && installLog.length > 0 && (
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
              <pre className="toolchain-log">{installLog.slice(-16).join("\n")}</pre>
            )}
          </li>
        );
      })}
    </ul>
  );
}
