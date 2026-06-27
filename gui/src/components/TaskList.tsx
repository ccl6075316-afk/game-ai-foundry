import type { PipelineTask } from "../vite-env.d";

const STATUS_CLASS: Record<string, string> = {
  done: "status-done",
  pending: "status-pending",
  running: "status-running",
  failed: "status-failed",
  skipped: "status-skipped",
};

interface Props {
  tasks: PipelineTask[];
  compact?: boolean;
}

export function TaskList({ tasks, compact = false }: Props) {
  if (!tasks.length) {
    return (
      <section className={`panel muted ${compact ? "compact" : ""}`}>
        <p>无任务 — 对话里发送 /plan 生成 manifest。</p>
      </section>
    );
  }

  return (
    <section className={`panel ${compact ? "compact board-tasks" : ""}`}>
      {!compact && <h2>任务 DAG</h2>}
      {compact && <h3>任务</h3>}
      <table className="table tasks">
        <thead>
          <tr>
            <th>Layer</th>
            <th>ID</th>
            <th>Role</th>
            <th>Step</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {tasks
            .slice()
            .sort((a, b) => a.layer - b.layer || a.id.localeCompare(b.id))
            .map((t) => (
              <tr key={t.id}>
                <td>{t.layer}</td>
                <td className="mono">{t.id}</td>
                <td>{t.role}</td>
                <td>{t.step}</td>
                <td>
                  <span className={`pill ${STATUS_CLASS[t.status] || ""}`}>{t.status}</span>
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </section>
  );
}
