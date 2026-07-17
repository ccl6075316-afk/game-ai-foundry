export type AgentExecutor = "hermes" | "cursor" | "codex";

export interface ExecutorOption {
  id: AgentExecutor;
  label: string;
  description: string;
}

/** 项目经理 orchestrator */
export const HOST_EXECUTORS: ExecutorOption[] = [
  {
    id: "cursor",
    label: "Cursor 对话",
    description: "在 Cursor 里聊天带队（当前开发方式，GUI 也走这条）",
  },
  {
    id: "hermes",
    label: "Hermes 助手",
    description: "独立 AI 助手会话（需本机安装 Hermes，并安装本项目技能包）",
  },
  {
    id: "codex",
    label: "Codex 命令行",
    description: "用 OpenAI Codex 命令行处理任务（需安装 Codex CLI）",
  },
];

/** 程序员 godot-developer */
export const CODE_EXECUTORS: ExecutorOption[] = [
  {
    id: "codex",
    label: "Codex 命令行",
    description: "自动读开发说明，生成 / 修改 Godot C# 代码",
  },
  {
    id: "cursor",
    label: "Cursor 对话",
    description: "在 Cursor 里直接改 games/ 下的代码和场景",
  },
  {
    id: "hermes",
    label: "Hermes 助手",
    description: "由 Hermes 会话驱动程序员角色完成开发",
  },
];

export const DEFAULT_AGENT_SKILLS = {
  orchestrator: "game-factory-orchestrator",
  "godot-developer": "game-factory-godot-developer",
} as const;

export function parseExecutor(value: unknown, fallback: AgentExecutor): AgentExecutor {
  const v = String(value || fallback);
  if (v === "hermes" || v === "cursor" || v === "codex") return v;
  return fallback;
}

export function executorAvailable(
  executors: Record<string, { available?: boolean }> | undefined,
  id: AgentExecutor,
): boolean {
  return Boolean(executors?.[id]?.available);
}

/** Codex / Cursor / Hermes 走本机登录，不用 Provider 页的 API Key */
export function executorUsesLogin(id: AgentExecutor): boolean {
  return id === "codex" || id === "cursor" || id === "hermes";
}

export const EXECUTOR_LOGIN_HINTS: Record<AgentExecutor, string> = {
  codex: "在环境面板安装 Codex CLI 并浏览器登录。GUI 聊天走 `codex exec`，不开桌面 App。",
  cursor: "安装 Cursor Agent shell 命令（`agent` / `cursor-agent`）。GUI 走 Agent CLI，不是打开 IDE 窗口回信。",
  hermes: "在环境面板安装 Hermes CLI、Skills，并同步 API。GUI 走 `hermes chat -q`。",
};
