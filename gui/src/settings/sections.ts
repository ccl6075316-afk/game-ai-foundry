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
  note: "下载 Godot 4 .NET / Mono 便携版（zip 解压即用），无需安装；解压后在下方指定可执行文件路径。",
};

export const HOST_SECTION: SettingsSectionMeta = {
  step: "带队",
  title: "项目经理",
  roleId: "orchestrator",
  purpose: "选择外部派活工具（Hermes / Codex / Cursor）；均为本机登录，不用 Provider Key",
  note: "GUI /brief 对话仍走 Provider 页的生文账号，与此处执行器无关",
};

export const CODE_SECTION: SettingsSectionMeta = {
  step: "开发",
  title: "程序员",
  roleId: "godot-developer",
  purpose: "选择写 Godot C# 的工具（Codex / Cursor / Hermes）；本机登录，不用 Provider Key",
  note: "Codex：codex login；Cursor：IDE 订阅；Hermes：自有配置",
};

export const PIPELINE_STEPS = [
  { label: "项目经理", desc: "统筹" },
  { label: "需求", desc: "想做什么" },
  { label: "文案", desc: "写描述" },
  { label: "原画", desc: "出图" },
  { label: "动画", desc: "出片" },
  { label: "程序", desc: "写玩法" },
];

export type SettingsTab = "providers" | "roles" | "local";

export const TEXT_PROVIDER_SECTION: SettingsSectionMeta = {
  step: "①",
  title: "生文",
  roleId: "llm-api",
  purpose: "策划对话、文案（/brief、prompt-crafter）；走 OpenRouter 等 chat/completions",
  note: "路由靠 model 字段：OpenRouter 用 厂商/模型名；官方 API 用 deepseek-chat、kimi-k2.5、glm-4-flash 等",
};

export const IMAGE_PROVIDER_SECTION: SettingsSectionMeta = {
  step: "②",
  title: "生图",
  roleId: "image-api",
  purpose: "原画出图（image-generator）；同一平台通常与生文共用账号，仅 model 不同",
  note: "OpenRouter 生图示例：google/gemini-3.1-flash-image；请求同样发到 chat/completions，并带 modalities",
};

export const VIDEO_PROVIDER_SECTION: SettingsSectionMeta = {
  step: "③",
  title: "生视频",
  roleId: "video-api",
  purpose: "图生视频（Seedance / 火山方舟 ARK）；独立 API，与 OpenRouter 不是一家",
};

/** @deprecated 使用 TEXT_PROVIDER_SECTION + IMAGE_PROVIDER_SECTION */
export const PROVIDER_SECTION = TEXT_PROVIDER_SECTION;

export const ROLES_SECTION = {
  step: "②",
  title: "角色与执行器",
  roleId: "agents",
  purpose: "按花名册中的每个同事实例配置执行器、Provider 与模型；未单独保存的实例继承工种默认",
  note: "策划 / IT 固定内置 Pi；Cursor 仅本机登录，第三方不可用。Key 仍在 Provider 页填写。",
};

export const INSTANCE_SECTION: SettingsSectionMeta = {
  step: "实例",
  title: "同事实例",
  roleId: "agents.instances",
  purpose: "选择一名同事，为其单独指定 Provider、模型与（Codex）第三方开关",
};

export function keyConfigured(value: string): boolean {
  const v = value.trim();
  return Boolean(v) && !v.toUpperCase().includes("YOUR_");
}

export type { ApiProviderId, VideoProviderId };
