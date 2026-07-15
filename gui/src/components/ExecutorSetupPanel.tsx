import type { ExecutorId, ExecutorSetupInfo, ExecutorSetupReport } from "../settings/executorsSetup";
import { EXECUTOR_ORDER } from "../settings/executorsSetup";

interface Props {
  report: ExecutorSetupReport | null;
  busyKey: string | null;
  log: string[];
  onRefresh: () => void;
  onRunStep: (executorId: ExecutorId, stepId: string) => void;
  onOpenSettings?: () => void;
}

function stepButtonLabel(stepId: string, done: boolean, busy: boolean): string {
  if (busy) return "执行中…";
  if (done) return "已完成";
  if (stepId === "login") return "浏览器登录";
  if (stepId === "configure_api") return "同步 API";
  if (stepId === "open_download") return "打开下载页";
  if (stepId === "verify_cli") return "检测 CLI";
  if (stepId.startsWith("install")) return "安装";
  return "执行";
}

function ExecutorCard({
  info,
  busyKey,
  onRunStep,
  onOpenSettings,
}: {
  info: ExecutorSetupInfo;
  busyKey: string | null;
  onRunStep: (executorId: ExecutorId, stepId: string) => void;
  onOpenSettings?: () => void;
}) {
  return (
    <li className={`executor-card ${info.ready ? "ready" : ""}`}>
      <div className="executor-card__head">
        <span className={`toolchain-dot ${info.ready ? "ok" : "no"}`} />
        <div>
          <strong>{info.label}</strong>
          <p className="executor-card__desc">{info.description}</p>
          {info.path && <p className="toolchain-item__path mono">{info.path}</p>}
        </div>
        <span className={`executor-card__badge ${info.ready ? "ok" : "pending"}`}>
          {info.ready ? "就绪" : "未完成"}
        </span>
      </div>

      <ol className="executor-steps">
        {info.steps.map((step) => {
          const key = `${info.id}:${step.id}`;
          const busy = busyKey === key;
          return (
            <li key={step.id} className={`executor-step ${step.done ? "done" : ""}`}>
              <div className="executor-step__main">
                <span className="executor-step__mark">{step.done ? "✓" : step.optional ? "○" : "·"}</span>
                <div>
                  <span className="executor-step__label">{step.label}</span>
                  {step.hint && <p className="executor-step__hint">{step.hint}</p>}
                </div>
              </div>
              {!step.done || step.optional ? (
                <button
                  type="button"
                  className="btn btn--sm btn--secondary"
                  disabled={busy || (step.done && !step.optional)}
                  onClick={() => onRunStep(info.id, step.id)}
                >
                  {stepButtonLabel(step.id, step.done && !step.optional, busy)}
                </button>
              ) : null}
            </li>
          );
        })}
      </ol>

      {info.id === "hermes" && !info.ready && (
        <p className="hint executor-card__foot">
          同步 API 需要先在
          {onOpenSettings ? (
            <button type="button" className="link-btn" onClick={onOpenSettings}>
              设置页
            </button>
          ) : (
            "设置页"
          )}
          配置 OpenRouter Key。
        </p>
      )}
    </li>
  );
}

export function ExecutorSetupPanel({
  report,
  busyKey,
  log,
  onRefresh,
  onRunStep,
  onOpenSettings,
}: Props) {
  const executors = report
    ? EXECUTOR_ORDER.map((id) => report.executors[id]).filter(Boolean)
    : [];

  return (
    <section className="env-panel__section executor-setup">
      <div className="executor-setup__head">
        <h3>执行器</h3>
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRefresh}>
          刷新状态
        </button>
      </div>
      <p className="hint">点击各步骤按钮完成安装；Codex 会触发浏览器登录，Hermes 可自动同步 OpenRouter API。</p>

      {!report ? (
        <p className="hint">尚未加载执行器状态。</p>
      ) : (
        <ul className="executor-list">
          {executors.map((info) => (
            <ExecutorCard
              key={info.id}
              info={info}
              busyKey={busyKey}
              onRunStep={onRunStep}
              onOpenSettings={onOpenSettings}
            />
          ))}
        </ul>
      )}

      {log.length > 0 && (
        <pre className="toolchain-log executor-log">{log.join("\n")}</pre>
      )}
    </section>
  );
}
