import type { ApiProviderId, VideoProviderId } from "./apiProviders";

export interface SettingsSectionMeta {
  step: string;
  title: string;
  /** 括号里展示的技术角色名 */
  roleId: string;
  purpose: string;
  note?: string;
}

export const PROMPT_SECTION: SettingsSectionMeta = {
  step: "①",
  title: "文案策划",
  roleId: "prompt-crafter",
  purpose: "把游戏需求改写成 AI 能看懂的英文描述",
  note: "未单独填账号时，自动使用项目经理的在线账号",
};

export const IMAGE_SECTION: SettingsSectionMeta = {
  step: "②",
  title: "原画师",
  roleId: "image-generator",
  purpose: "根据描述生成角色、场景、图标等图片",
};

export const VIDEO_SECTION: SettingsSectionMeta = {
  step: "③",
  title: "动画师",
  roleId: "video-generator",
  purpose: "生成角色动作视频，并拆成游戏用的序列帧",
};

export const GODOT_SECTION: SettingsSectionMeta = {
  step: "工具",
  title: "Godot 引擎",
  roleId: "godot-assembler",
  purpose: "本机 Godot 程序，用于打开工程、导入素材、检查项目",
};

export const HOST_SECTION: SettingsSectionMeta = {
  step: "带队",
  title: "项目经理",
  roleId: "orchestrator",
  purpose: "统筹游戏想法，协调文案、美术、动画、程序；其在线账号供文案/程序在未单独配置时共用",
  note: "下方选「谁来对话」；在线账号是文案与程序的默认回退",
};

export const CODE_SECTION: SettingsSectionMeta = {
  step: "开发",
  title: "程序员",
  roleId: "godot-developer",
  purpose: "在 Godot 工程里写玩法、操作和界面逻辑（C#）",
  note: "未单独填账号时，自动使用项目经理的在线账号；素材导入完成后才轮到这一步",
};

export const PIPELINE_STEPS = [
  { label: "项目经理", desc: "统筹" },
  { label: "需求", desc: "想做什么" },
  { label: "文案", desc: "写描述" },
  { label: "原画", desc: "出图" },
  { label: "动画", desc: "出片" },
  { label: "程序", desc: "写玩法" },
];

export type SettingsTab = "ai" | "local";

export function keyConfigured(value: string): boolean {
  const v = value.trim();
  return Boolean(v) && !v.toUpperCase().includes("YOUR_");
}

export type { ApiProviderId, VideoProviderId };
