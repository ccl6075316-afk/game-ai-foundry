import type { DoctorReport } from "../vite-env.d";
import type { ToolchainReport } from "../settings/toolchain";
import { autoInstallable } from "../settings/toolchain";
import { EnvComponentList } from "./EnvComponentList";

type Tab = "tools" | "doctor";

interface Props {
  toolchain: ToolchainReport | null;
  doctor: DoctorReport | null;
  scanning: boolean;
  installing: string | null;
  installLog: string[];
  onRefresh: () => void;
  onInstall: (id: string) => void;
  onInstallAll: () => void;
  onOpenExternal: (url: string) => void;
  onOpenSettings: () => void;
}

export function EnvPanel({
  toolchain,
  doctor,
  scanning,
  installing,
  installLog,
  onRefresh,
  onInstall,
  onInstallAll,
  onOpenExternal,
  onOpenSettings,
}: Props) {
  const autoCount = toolchain ? autoInstallable(toolchain).length : 0;

  return (
    <aside className="side-panel env-panel">
      <header className="side-panel__head">
        <h2>环境准备</h2>
        <p className="side-panel__sub">检测本机工具、API 配置与执行器可用性</p>
      </header>

      <div className="env-panel__actions">
        <button type="button" className="btn btn--secondary" disabled={scanning} onClick={onRefresh}>
          {scanning ? "扫描中…" : "重新检测"}
        </button>
        {autoCount > 0 && (
          <button
            type="button"
            className="btn btn--primary"
            disabled={Boolean(installing) || scanning}
            onClick={onInstallAll}
          >
            {installing ? "安装中…" : `一键安装可自动项（${autoCount}）`}
          </button>
        )}
      </div>

      <section className="env-panel__section">
        <h3>本机工具</h3>
        <p className="hint">Godot 为便携 zip 手动下载；FFmpeg / rembg 可点击安装。</p>
        {toolchain ? (
          <EnvComponentList
            components={toolchain.components}
            installing={installing}
            installLog={installLog}
            onInstall={onInstall}
            onOpenExternal={onOpenExternal}
            onOpenSettings={onOpenSettings}
            showAll
          />
        ) : (
          <p className="hint">尚未扫描，请点击「重新检测」。</p>
        )}
      </section>

      {doctor && (
        <section className="env-panel__section">
          <h3>能力探测</h3>
          <div className="cap-grid">
            {Object.entries(doctor.capabilities || {}).map(([key, ok]) => (
              <div key={key} className={`cap-item ${ok ? "ok" : "no"}`}>
                <span className="cap-dot" />
                <span>{key}</span>
              </div>
            ))}
          </div>

          <h3>配置</h3>
          <ul className="config-list">
            <li>
              文件: <code>{doctor.config.path}</code> ({doctor.config.exists ? "存在" : "缺失"})
            </li>
            <li>OpenRouter: {doctor.config.openrouter_key}</li>
            <li>Seedance: {doctor.config.seedance_key}</li>
            <li>Godot path: {doctor.config.godot_engine_path}</li>
          </ul>

          <h3>执行器</h3>
          <table className="table">
            <thead>
              <tr>
                <th>名称</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(doctor.executors || {}).map(([name, info]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>{info.available ? "可用" : "缺失"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </aside>
  );
}
