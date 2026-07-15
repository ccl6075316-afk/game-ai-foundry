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
  if (item.action === "install_guide") return "安装说明";
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
  const visible = showAll ? components : components.filter((c) => !c.available);

  const handleAction = async (item: ToolchainComponent) => {
    if (item.available || installing) return;
    if (item.action === "auto" || item.action === "pip") {
      onInstall(item.id);
      return;
    }
    if (item.install_cmd) {
      try {
        await navigator.clipboard.writeText(item.install_cmd);
      } catch {
        /* ignore */
      }
    }
    if (item.download_url) onOpenExternal(item.download_url);
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
              {item.install_cmd && !item.available && (
                <code className="toolchain-item__path mono">{item.install_cmd}</code>
              )}
              {item.path && <p className="toolchain-item__path mono">{item.path}</p>}
            </div>
            <div className="toolchain-item__actions">
              <button
                type="button"
                className={`btn btn--sm ${item.available ? "btn--ghost" : "btn--secondary"}`}
                disabled={!canAct && !item.available}
                onClick={() => void handleAction(item)}
              >
                {actionLabel(item, busy)}
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
