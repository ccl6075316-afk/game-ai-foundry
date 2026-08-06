import { useCallback, useEffect, useState } from "react";
import type { DoctorReport } from "../vite-env.d";
import type { ToolchainReport } from "../settings/toolchain";
import type { ExecutorSetupReport } from "../settings/executorsSetup";
import { autoInstallable } from "../settings/toolchain";
import { EnvComponentList } from "./EnvComponentList";
import { ExecutorSetupPanel } from "./ExecutorSetupPanel";
import type { ExecutorId } from "../settings/executorsSetup";

interface Props {
  toolchain: ToolchainReport | null;
  executorSetup: ExecutorSetupReport | null;
  doctor: DoctorReport | null;
  scanning: boolean;
  installing: string | null;
  executorBusy: string | null;
  installLog: string[];
  onRefresh: () => void;
  onInstall: (id: string) => void;
  onInstallAll: () => void;
  onExecutorStep: (executorId: ExecutorId, stepId: string) => void;
  onOpenExternal: (url: string) => void;
  onOpenSettings: () => void;
  /** Full-page settings tab: no side-panel shell */
  embedded?: boolean;
}

export function EnvPanel({
  toolchain,
  executorSetup,
  doctor,
  scanning,
  installing,
  executorBusy,
  installLog,
  onRefresh,
  onInstall,
  onInstallAll,
  onExecutorStep,
  onOpenExternal,
  onOpenSettings,
  embedded = false,
}: Props) {
  const autoCount = toolchain ? autoInstallable(toolchain).length : 0;
  const Shell = embedded ? "div" : "aside";
  const shellClass = embedded ? "env-panel env-panel--embedded" : "side-panel env-panel";

  const [downloadMirror, setDownloadMirror] = useState(false);
  const [mirrorSaving, setMirrorSaving] = useState(false);
  const [mirrorError, setMirrorError] = useState<string | null>(null);

  const loadMirrorPref = useCallback(async () => {
    if (!window.gameFactory?.getConfig) return;
    try {
      const info = await window.gameFactory.getConfig();
      const tc = info.data?.toolchain;
      const on =
        tc && typeof tc === "object" && !Array.isArray(tc)
          ? Boolean((tc as { download_mirror?: unknown }).download_mirror)
          : false;
      setDownloadMirror(on);
      setMirrorError(null);
    } catch (err) {
      setMirrorError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    void loadMirrorPref();
  }, [loadMirrorPref]);

  const onToggleMirror = async (next: boolean) => {
    if (!window.gameFactory?.saveConfig) return;
    setMirrorSaving(true);
    setMirrorError(null);
    setDownloadMirror(next);
    try {
      const res = await window.gameFactory.saveConfig({
        toolchain: { download_mirror: next },
      });
      if (!res?.ok) {
        setDownloadMirror(!next);
        setMirrorError(res?.error || "保存失败");
        return;
      }
    } catch (err) {
      setDownloadMirror(!next);
      setMirrorError(err instanceof Error ? err.message : String(err));
    } finally {
      setMirrorSaving(false);
    }
  };

  return (
    <Shell className={shellClass}>
      {!embedded && (
        <header className="side-panel__head">
          <h2>环境准备</h2>
          <p className="side-panel__sub">检测本机工具、API 配置与执行器可用性</p>
        </header>
      )}

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
        <h3>下载镜像</h3>
        <p className="hint">
          默认直连 GitHub。国内网络装 FFmpeg / Godot / Codex 过慢时可开启（经 ghproxy.net
          等反代；社区服务，不稳定时可关掉）。
        </p>
        <label className="field field--checkbox">
          <input
            type="checkbox"
            checked={downloadMirror}
            disabled={mirrorSaving || !window.gameFactory?.saveConfig}
            onChange={(e) => void onToggleMirror(e.target.checked)}
          />
          <span>使用 GitHub 下载镜像</span>
        </label>
        {mirrorError && <p className="hint">{mirrorError}</p>}
      </section>

      <section className="env-panel__section">
        <h3>本机工具</h3>
        <p className="hint">FFmpeg / Godot / .NET 为必需项，缺失时启动会自动安装；rembg 已随内嵌 Python 自带。</p>
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

      <ExecutorSetupPanel
        report={executorSetup}
        busyKey={executorBusy}
        log={installLog}
        onRefresh={onRefresh}
        onRunStep={onExecutorStep}
        onOpenSettings={onOpenSettings}
      />

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
          <p className="hint">详细安装步骤见上方「执行器」卡片。</p>
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
    </Shell>
  );
}
