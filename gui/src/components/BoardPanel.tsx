import type { PipelineStatus, PipelineTask } from "../vite-env.d";
import type { HostChatDraftBrief } from "../chat/types";
import { TaskList } from "./TaskList";

interface Props {
  manifest: string;
  status: PipelineStatus | null;
  tasks: PipelineTask[];
  logs: string[];
  onRefresh: () => void;
  onRun: () => void;
  busy: boolean;
  draftBrief?: HostChatDraftBrief | null;
}

export function BoardPanel({
  manifest,
  status,
  tasks,
  logs,
  onRefresh,
  onRun,
  busy,
  draftBrief = null,
}: Props) {
  const counts = status?.counts || {};

  return (
    <aside className="side-panel board-panel">
      <div className="side-panel__head board-head">
        <h2>看板 {tasks.length > 0 ? "✓" : ""}</h2>
        <p className="hint">
          {tasks.length > 0
            ? `任务清单已加载（${tasks.length} 项）— 主操作在对话上方按钮`
            : "尚无任务 — 先点「① 生成流水线」"}
        </p>
      </div>

      <div className={`board-meta mono ${tasks.length > 0 ? "board-meta--ready" : ""}`}>
        {manifest || "（未选择 manifest）"}
      </div>

      <div className="stats compact">
        <div className={`stat ${tasks.length > 0 ? "ok" : ""} ${status?.done ? "ok" : ""}`}>
          <span className="stat-label">清单</span>
          <span>{tasks.length > 0 ? "已生成" : "未生成"}</span>
        </div>
        <div className={`stat ${status?.done ? "ok" : ""}`}>
          <span className="stat-label">跑完</span>
          <span>{status?.done ? "是" : "否"}</span>
        </div>
        {Object.entries(counts).map(([k, v]) => (
          <div key={k} className="stat">
            <span className="stat-label">{k}</span>
            <span>{v}</span>
          </div>
        ))}
      </div>

      <div className="board-actions">
        <button type="button" className="btn btn--secondary" onClick={onRefresh} disabled={busy}>
          刷新
        </button>
        <button type="button" className="btn btn--primary" onClick={onRun} disabled={busy}>
          运行
        </button>
      </div>

      <TaskList tasks={tasks} compact briefAssets={draftBrief?.assets} />

      {logs.length > 0 && (
        <div className="board-logs">
          <h3>最近日志</h3>
          <pre>{logs.slice(-30).join("\n")}</pre>
        </div>
      )}
    </aside>
  );
}
