/** 同事实例（工种 × 多人）— 见 docs/HOST-CHAT-PRODUCT.md */

import type { ChatAgentRole } from "./roles";
import { CHAT_AGENT_LABELS } from "./roles";

export type ExecutorKind = "hermes" | "cursor" | "codex" | "pi" | null;

export interface ColleagueInstance {
  id: string;
  roleKind: ChatAgentRole;
  displayName: string;
  /** ②③ Agent 执行器；① 策划为 null；IT 默认 pi */
  executor: ExecutorKind;
  createdAt: number;
}

export const DEFAULT_INSTANCE_NAMES: Record<ChatAgentRole, string> = {
  brief: "策划 · 默认",
  product_host: "项目经理 · 主线",
  programmer: "程序员 · 玩法",
  it: "IT · 运维",
};

function newInstanceId(roleKind: ChatAgentRole): string {
  return `${roleKind}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

export function createColleague(
  roleKind: ChatAgentRole,
  displayName?: string,
  executor: ExecutorKind = null,
): ColleagueInstance {
  return {
    id: newInstanceId(roleKind),
    roleKind,
    displayName: displayName?.trim() || DEFAULT_INSTANCE_NAMES[roleKind],
    executor: roleKind === "brief" ? null : roleKind === "it" ? "pi" : executor,
    createdAt: Date.now(),
  };
}

export function createDefaultRoster(): ColleagueInstance[] {
  return [
    createColleague("brief", DEFAULT_INSTANCE_NAMES.brief),
    createColleague("product_host", DEFAULT_INSTANCE_NAMES.product_host),
    createColleague("programmer", DEFAULT_INSTANCE_NAMES.programmer),
    createColleague("it", DEFAULT_INSTANCE_NAMES.it, "pi"),
  ];
}

export function nextHireName(roster: ColleagueInstance[], roleKind: ChatAgentRole): string {
  const n = roster.filter((c) => c.roleKind === roleKind).length + 1;
  const base = CHAT_AGENT_LABELS[roleKind];
  if (roleKind === "brief") return `${base} · ${n}`;
  if (roleKind === "product_host") return `项目经理 · ${n}`;
  if (roleKind === "it") return `IT · ${n}`;
  return `程序员 · ${n}`;
}

export function findColleague(roster: ColleagueInstance[], id: string): ColleagueInstance | undefined {
  return roster.find((c) => c.id === id);
}
