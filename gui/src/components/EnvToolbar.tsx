import type { DoctorReport } from "../vite-env.d";
import type { ToolchainReport } from "../settings/toolchain";
import { autoInstallable } from "../settings/toolchain";

interface Props {
  toolchain: ToolchainReport | null;
  doctor: DoctorReport | null;
  scanning: boolean;
  installing: boolean;
  onScan: () => void;
  onInstallAll: () => void;
  onOpenEnv: () => void;
  onOpenGuide: () => void;
}

const CHIP_LABELS: Record<string, string> = {
  ffmpeg: "FFmpeg",
  godot: "Godot",
  dotnet: ".NET",
  rembg: "rembg",
};

export function EnvToolbar({
  toolchain,
  doctor,
  scanning,
  installing,
  onScan,
  onInstallAll,
  onOpenEnv,
  onOpenGuide,
}: Props) {
  const chips = toolchain?.components ?? [];
  const missingRequired = toolchain?.missing_required.length ?? 0;
  const autoCount = toolchain ? autoInstallable(toolchain).length : 0;
  const apiOk = doctor?.capabilities?.image_api;
  const configOk = doctor?.config?.exists;

  return (
    <div className="env-toolbar" role="toolbar" aria-label="环境工具栏">
      <div className="env-toolbar__chips">
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
        <button
          type="button"
          className={`env-chip ${apiOk ? "ok" : "warn"}`}
          title="OpenRouter / 图像 API Key"
          onClick={onOpenEnv}
        >
          <span className="env-chip__dot" />
          API
        </button>
        <button
          type="button"
          className={`env-chip ${configOk ? "ok" : "warn"}`}
          title={doctor?.config.path}
          onClick={onOpenEnv}
        >
          <span className="env-chip__dot" />
          配置
        </button>
      </div>

      <div className="env-toolbar__actions">
        {missingRequired > 0 && (
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
