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
  codex: "在环境面板点击「安装」与「浏览器登录」即可完成 Codex 配置，无需填 API Key。",
  cursor: "在环境面板打开 Cursor 下载页并检测 CLI；IDE 内登录订阅账号即可。",
  hermes: "在环境面板分步安装 Hermes、Skills，并一键同步 OpenRouter API。",
};
