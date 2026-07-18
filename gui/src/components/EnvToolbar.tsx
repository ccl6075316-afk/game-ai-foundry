import type { DoctorReport } from "../vite-env.d";
import type { ToolchainReport } from "../settings/toolchain";
import type { ExecutorSetupReport } from "../settings/executorsSetup";
import { EXECUTOR_ORDER } from "../settings/executorsSetup";
import { autoInstallable } from "../settings/toolchain";

interface Props {
  toolchain: ToolchainReport | null;
  executorSetup: ExecutorSetupReport | null;
  doctor: DoctorReport | null;
  scanning: boolean;
  installing: boolean;
  /** false = blocking env issues */
  healthOk?: boolean | null;
  scanError?: string | null;
  onScan: () => void;
  onInstallAll: () => void;
  onOpenEnv: () => void;
  onOpenGuide: () => void;
}

const CHIP_LABELS: Record<string, string> = {
  ffmpeg: "FFmpeg",
  godot: "Godot",
  dotnet: ".NET",
  hermes: "Hermes",
  codex: "Codex",
  cursor: "Cursor",
};

export function EnvToolbar({
  toolchain,
  executorSetup,
  doctor,
  scanning,
  installing,
  healthOk,
  scanError,
  onScan,
  onInstallAll,
  onOpenEnv,
  onOpenGuide,
}: Props) {
  const chips = toolchain?.components ?? [];
  const executorChips = EXECUTOR_ORDER.map((id) => executorSetup?.executors[id]).filter(Boolean);
  const missingRequired = toolchain?.missing_required.length ?? 0;
  const autoCount = toolchain ? autoInstallable(toolchain).length : 0;
  const apiOk = doctor?.capabilities?.image_api;
  const configOk = doctor?.config?.exists;
  const detectFailed = healthOk === false || Boolean(scanError) || (!doctor && !scanning && !toolchain);

  return (
    <div className="env-toolbar" role="toolbar" aria-label="环境工具栏">
      <div className="env-toolbar__chips">
        <button
          type="button"
          className={`env-chip ${detectFailed ? "warn" : healthOk ? "ok" : "muted"}`}
          title={scanError || (detectFailed ? "环境检测未通过，点开查看" : "环境正常")}
          onClick={onOpenEnv}
        >
          <span className="env-chip__dot" />
          {detectFailed ? "检测异常" : scanning ? "检测中" : "检测OK"}
        </button>
        {chips.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`env-chip ${item.available ? "ok" : item.required ? "warn" : "muted"}`}
            title={item.path || item.description}
            onClick={onOpenEnv}
          >
            <span className="env-chip__dot" />
            {CHIP_LABELS[item.id] || item.label}
          </button>
        ))}
        {executorChips.map((item) => (
          <button
            key={item!.id}
            type="button"
            className={`env-chip ${item!.ready ? "ok" : "muted"}`}
            title={item!.path || item!.description}
            onClick={onOpenEnv}
          >
            <span className="env-chip__dot" />
            {CHIP_LABELS[item!.id] || item!.label}
          </button>
        ))}
        <button
          type="button"
          className={`env-chip ${apiOk ? "ok" : "warn"}`}
          title={apiOk ? "图像 API 已配置" : "图像 API Key 未配置 — 生图/北极星会失败"}
          onClick={onOpenEnv}
        >
          <span className="env-chip__dot" />
          API
        </button>
        <button
          type="button"
          className={`env-chip ${configOk ? "ok" : "warn"}`}
          title={doctor?.config.path || "配置文件"}
          onClick={onOpenEnv}
        >
          <span className="env-chip__dot" />
          配置
        </button>
      </div>

      <div className="env-toolbar__actions">
        {detectFailed && (
          <span className="env-toolbar__hint env-toolbar__hint--err">
            {scanError ? "检测失败" : `有 ${missingRequired || "?"} 项需处理`}
          </span>
        )}
        {!detectFailed && missingRequired > 0 && (
          <span className="env-toolbar__hint">缺 {missingRequired} 项必需组件</span>
        )}
        <button type="button" className="btn btn--ghost btn--sm" disabled={scanning} onClick={onScan}>
          {scanning ? "检测中…" : "重新检测"}
        </button>
        {autoCount > 0 && (
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            disabled={installing || scanning}
            onClick={onInstallAll}
          >
            {installing ? "安装中…" : `安装缺失（${autoCount}）`}
          </button>
        )}
        <button type="button" className="btn btn--ghost btn--sm" onClick={onOpenEnv}>
          环境详情
        </button>
        <button type="button" className="btn btn--ghost btn--sm" onClick={onOpenGuide}>
          命令指南
        </button>
      </div>
    </div>
  );
}

