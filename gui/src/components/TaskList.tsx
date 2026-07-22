import type { HostChatDraftBrief } from "../chat/types";
import type { PipelineTask } from "../vite-env.d";
import { assetStyleChips } from "./briefPreviewFormat";

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
  /** Brief assets for read-only style chips (declared fields only). */
  briefAssets?: HostChatDraftBrief["assets"];
}

function lookupAsset(
  assets: HostChatDraftBrief["assets"] | undefined,
  name: string,
): Record<string, unknown> | null {
  if (!assets?.length || !name) return null;
  const hit = assets.find(
    (a) => a && (String(a.name || "") === name || String(a.id || "") === name),
  );
  return hit ? (hit as Record<string, unknown>) : null;
}

function groupTasksByAsset(tasks: PipelineTask[]): { asset: string; tasks: PipelineTask[] }[] {
  const sorted = tasks.slice().sort((a, b) => a.layer - b.layer || a.id.localeCompare(b.id));
  const order: string[] = [];
  const map = new Map<string, PipelineTask[]>();
  for (const t of sorted) {
    const key = t.asset || "(unknown)";
    if (!map.has(key)) {
      map.set(key, []);
      order.push(key);
    }
    map.get(key)!.push(t);
  }
  return order.map((asset) => ({ asset, tasks: map.get(asset)! }));
}

export function TaskList({ tasks, compact = false, briefAssets }: Props) {
  if (!tasks.length) {
    return (
      <section className={`panel muted ${compact ? "compact" : ""}`}>
        <p>无任务 — 切到「项目经理」同事，点「生成流水线」。</p>
      </section>
    );
  }

  const groups = groupTasksByAsset(tasks);

  return (
    <section className={`panel ${compact ? "compact board-tasks" : ""}`}>
      {!compact && <h2>任务 DAG</h2>}
      {compact && <h3>任务</h3>}
      {groups.map(({ asset, tasks: groupTasks }) => {
        const styleAsset = lookupAsset(briefAssets, asset);
        const chips = styleAsset ? assetStyleChips(styleAsset) : [];
        return (
          <div key={asset} className="task-asset-group">
            <div className="task-asset-head">
              <span className="task-asset-name mono">{asset}</span>
              {chips.length > 0 && (
                <span className="task-style-chips">
                  {chips.map((c) => (
                    <span key={c} className="pill style-chip">
                      {c}
                    </span>
                  ))}
                </span>
              )}
            </div>
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
                {groupTasks.map((t) => (
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
          </div>
        );
      })}
    </section>
  );
}
