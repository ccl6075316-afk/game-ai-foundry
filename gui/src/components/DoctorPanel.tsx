import type { DoctorReport } from "../vite-env.d";

interface Props {
  report: DoctorReport;
  onRefresh: () => void;
}

export function DoctorPanel({ report, onRefresh }: Props) {
  const caps = report.capabilities || {};

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>环境探测</h2>
        <button type="button" className="secondary" onClick={onRefresh}>
          重新扫描
        </button>
      </div>
      <p className="hint">
        Hermes / Codex / Cursor 不随仓库分发 — 此处显示本机探测结果（同 <code>gamefactory doctor</code>）。
      </p>

      <div className="cap-grid">
        {Object.entries(caps).map(([key, ok]) => (
          <div key={key} className={`cap-item ${ok ? "ok" : "no"}`}>
            <span className="cap-dot" />
            <span>{key}</span>
          </div>
        ))}
      </div>

      <h3>执行器</h3>
      <table className="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>状态</th>
            <th>路径 / 说明</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(report.executors || {}).map(([name, info]) => (
            <tr key={name}>
              <td>{name}</td>
              <td>{info.available ? "可用" : "缺失"}</td>
              <td className="mono">
                {info.cli || info.reason || (info.hints || []).join(" ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Agent 路由</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Role</th>
            <th>配置</th>
            <th>可用</th>
            <th>建议</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(report.agents || {}).map(([role, a]) => (
            <tr key={role} className={a.action_required ? "warn-row" : ""}>
              <td>{role}</td>
              <td>{a.configured_executor || a.executor}</td>
              <td>{a.executor_available ? "是" : "否"}</td>
              <td>{a.suggested_executor || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>配置</h3>
      <ul className="config-list">
        <li>
          文件: <code>{report.config.path}</code> ({report.config.exists ? "存在" : "缺失"})
        </li>
        <li>OpenRouter: {report.config.openrouter_key}</li>
        <li>Seedance: {report.config.seedance_key}</li>
        <li>Godot path: {report.config.godot_engine_path}</li>
      </ul>
    </section>
  );
}
