import { useEffect, useState } from "react";
import type { BriefItem, PipelineStatus } from "../vite-env.d";
import { planTargetsFromBrief } from "../chat/projectPaths";

interface Props {
  briefs: BriefItem[];
  manifests: BriefItem[];
  selectedManifest: string;
  activeBrief: string | null;
  status: PipelineStatus | null;
  busy: boolean;
  onSelectManifest: (path: string) => void;
  onSelectBrief: (path: string) => void;
  onPlan: (opts: {
    briefRel: string;
    manifestRel: string;
    outputDirRel: string;
    godotProjectRel: string;
  }) => void;
  onRun: () => void;
  onOpenGodot: () => void;
}

export function PipelinePanel({
  briefs,
  manifests,
  selectedManifest,
  activeBrief,
  status,
  busy,
  onSelectManifest,
  onSelectBrief,
  onPlan,
  onRun,
  onOpenGodot,
}: Props) {
  const [briefRel, setBriefRel] = useState(activeBrief || briefs[0]?.path || "");

  useEffect(() => {
    if (activeBrief) setBriefRel(activeBrief);
    else if (!briefRel && briefs[0]?.path) setBriefRel(briefs[0].path);
  }, [activeBrief, briefs, briefRel]);

  const counts = status?.counts || {};
  const done = status?.done;
  const targets = briefRel ? planTargetsFromBrief(briefRel) : null;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Pipeline</h2>
        <div className="actions">
          <button
            type="button"
            className="secondary"
            disabled={busy || !targets}
            onClick={() => targets && onPlan(targets)}
          >
            Plan
          </button>
          <button type="button" className="primary" disabled={busy || !selectedManifest} onClick={onRun}>
            {busy ? "运行中…" : "Run"}
          </button>
          <button type="button" className="secondary" disabled={!selectedManifest} onClick={onOpenGodot}>
            打开 Godot
          </button>
        </div>
      </div>

      <div className="form-row">
        <label>
          Brief
          <select
            value={briefRel}
            onChange={(e) => {
              setBriefRel(e.target.value);
              onSelectBrief(e.target.value);
            }}
          >
            {briefs.length === 0 && <option value="">（暂无 brief — 先用 /brief 导出）</option>}
            {briefs.map((b) => (
              <option key={b.path} value={b.path}>
                {b.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Manifest
          <select
            value={selectedManifest}
            onChange={(e) => onSelectManifest(e.target.value)}
          >
            {manifests.length === 0 && (
              <option value="">（暂无 manifest — 先 Plan）</option>
            )}
            {manifests.map((m) => (
              <option key={m.path} value={m.path}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {targets && (
        <p className="hint mono">
          输出 {targets.outputDirRel} · Godot {targets.godotProjectRel}
        </p>
      )}

      <div className="stats">
        <div className={`stat ${done ? "ok" : ""}`}>
          <span className="stat-label">状态</span>
          <span>{done ? "完成" : "进行中"}</span>
        </div>
        <div className="stat">
          <span className="stat-label">任务</span>
          <span>{status?.total ?? "—"}</span>
        </div>
        {Object.entries(counts).map(([k, v]) => (
          <div key={k} className="stat">
            <span className="stat-label">{k}</span>
            <span>{v}</span>
          </div>
        ))}
      </div>

      <p className="hint">
        工作流：Brief 策划 → Plan → Run。测试用 brief 留在本地，不会随 release 打包。
      </p>
    </section>
  );
}
