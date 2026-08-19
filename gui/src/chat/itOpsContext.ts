/** Ephemeral ops snapshot for IT agent turns (not persisted as user message). */

import type { ChatSessionStore } from "./sessions";

const SECRET_VALUE_RE = /\b(sk-[a-zA-Z0-9_-]{12,}|sk-or-[a-zA-Z0-9_-]{12,})\b/g;

export function redactOpsSecrets(text: string): string {
  return String(text || "").replace(SECRET_VALUE_RE, "***");
}

export function buildItGuiOpsContext(opts: {
  store: ChatSessionStore;
  manifestRel?: string | null;
  pipelineLogs?: string[];
}): string {
  const lines: string[] = [];
  const manifest = String(opts.manifestRel || "").trim();
  if (manifest) {
    lines.push(`当前看板 manifest: ${manifest}`);
  }

  const pm = opts.store.roster.find((c) => c.roleKind === "product_host");
  if (pm) {
    const sid = opts.store.activeByInstance[pm.id];
    const sess = opts.store.sessions.find((s) => s.id === sid && s.instanceId === pm.id);
    if (sess?.messages?.length) {
      lines.push(`项目经理（${pm.displayName}）GUI 会话尾部：`);
      for (const m of sess.messages.slice(-10)) {
        const text = redactOpsSecrets(String(m.content || "").trim());
        if (!text) continue;
        lines.push(`${m.role}: ${text.slice(0, 900)}`);
      }
    }
  }

  const logTail = (opts.pipelineLogs || []).slice(-35);
  if (logTail.length) {
    lines.push("最近流水线终端日志：");
    for (const line of logTail) {
      lines.push(redactOpsSecrets(String(line)).slice(0, 600));
    }
  }

  return lines.join("\n").slice(0, 12_000);
}
