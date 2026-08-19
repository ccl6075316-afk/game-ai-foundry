/** Ephemeral pipeline snapshot for PM agent turns (goal mode — not persisted as user message). */

import { redactOpsSecrets } from "./itOpsContext";

type DiagnoseItem = {
  task_id?: string;
  kind?: string;
  summary?: string;
  pm_fit?: string;
  pm_tip?: string;
};

export function buildPmGuiOpsContext(opts: {
  manifestRel?: string | null;
  pipelineLogs?: string[];
  diagnose?: {
    pm_advice_short?: string;
    pm_advice?: string;
    fix_commands?: string[];
    auto_fix_without_agent?: boolean;
    needs_hermes?: DiagnoseItem[];
    items?: DiagnoseItem[];
  } | null;
}): string {
  const lines: string[] = [];
  const manifest = String(opts.manifestRel || "").trim();
  if (manifest) {
    lines.push(`当前流水线 manifest: ${manifest}`);
  }

  const diag = opts.diagnose;
  if (diag) {
    const advice = String(diag.pm_advice_short || diag.pm_advice || "").trim();
    if (advice) {
      lines.push(`diagnose 摘要: ${advice}`);
    }
    const items = (diag.needs_hermes?.length ? diag.needs_hermes : diag.items) || [];
    if (items.length) {
      lines.push("failed 任务分诊:");
      for (const n of items.slice(0, 8)) {
        const tip = n.pm_tip || n.summary || "";
        lines.push(
          `- ${n.task_id || "?"} kind=${n.kind || "?"} pm_fit=${n.pm_fit || "?"}` +
            (tip ? ` — ${tip.slice(0, 240)}` : ""),
        );
      }
    }
    const fixes = diag.fix_commands || [];
    if (fixes.length) {
      lines.push("宿主将自动串跑的 fix_commands:");
      for (const cmd of fixes.slice(0, 6)) {
        lines.push(`- ${cmd}`);
      }
    }
  }

  const logTail = (opts.pipelineLogs || []).slice(-40);
  if (logTail.length) {
    lines.push("最近流水线终端日志:");
    for (const line of logTail) {
      lines.push(redactOpsSecrets(String(line)).slice(0, 600));
    }
  }

  lines.push(
    "目标模式: 先执行白名单修复命令（config set / reset / run），禁止只复述 errno；" +
      "在 dispatch.cli_hints 给出可执行命令，宿主会自动串跑。",
  );

  return lines.join("\n").slice(0, 12_000);
}
