export type ApiProviderId = "openrouter" | "openai" | "gemini" | "custom";

export interface ApiProviderPreset {
  id: ApiProviderId;
  label: string;
  description: string;
  apiBase: string;
  imageModelDefault: string;
  promptModelDefault: string;
  keyPlaceholder: string;
}

export const API_PROVIDERS: ApiProviderPreset[] = [
  {
    id: "openrouter",
    label: "OpenRouter",
    description: "一个平台用多家模型，适合快速切换",
    apiBase: "https://openrouter.ai/api/v1",
    imageModelDefault: "google/gemini-3.1-flash-image",
    promptModelDefault: "deepseek/deepseek-chat",
    keyPlaceholder: "sk-or-…",
  },
  {
    id: "openai",
    label: "OpenAI",
    description: "OpenAI 官方 GPT / 出图",
    apiBase: "https://api.openai.com/v1",
    imageModelDefault: "gpt-4o",
    promptModelDefault: "gpt-4o-mini",
    keyPlaceholder: "sk-…",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    description: "Google Gemini 官方接口",
    apiBase: "https://generativelanguage.googleapis.com/v1beta/openai/",
    imageModelDefault: "gemini-2.0-flash-preview-image-generation",
    promptModelDefault: "gemini-2.0-flash",
    keyPlaceholder: "AIza…",
  },
  {
    id: "custom",
    label: "自定义",
    description: "其他兼容 OpenAI 格式的平台",
    apiBase: "",
    imageModelDefault: "",
    promptModelDefault: "",
    keyPlaceholder: "API Key",
  },
];

export type VideoProviderId = "seedance" | "custom";

export interface VideoProviderPreset {
  id: VideoProviderId;
  label: string;
  apiBase: string;
  keyPlaceholder: string;
}

export const VIDEO_PROVIDERS: VideoProviderPreset[] = [
  {
    id: "seedance",
    label: "Seedance / 火山方舟",
    apiBase: "https://ark.cn-beijing.volces.com/api/v3",
    keyPlaceholder: "ARK API Key",
  },
  {
    id: "custom",
    label: "自定义",
    apiBase: "",
    keyPlaceholder: "API Key",
  },
];

export function getApiProvider(id: ApiProviderId): ApiProviderPreset {
  return API_PROVIDERS.find((p) => p.id === id) ?? API_PROVIDERS[0]!;
}

export function getVideoProvider(id: VideoProviderId): VideoProviderPreset {
  return VIDEO_PROVIDERS.find((p) => p.id === id) ?? VIDEO_PROVIDERS[0]!;
}

function normalizeBase(url: string): string {
  return url.trim().toLowerCase().replace(/\/+$/, "");
}

export function detectApiProvider(apiBase: string | undefined): ApiProviderId {
  const normalized = normalizeBase(apiBase || "");
  if (!normalized) return "openrouter";
  for (const preset of API_PROVIDERS) {
    if (preset.id === "custom") continue;
    if (normalized === normalizeBase(preset.apiBase)) return preset.id;
  }
  return "custom";
}

export function detectVideoProvider(apiBase: string | undefined): VideoProviderId {
  const normalized = normalizeBase(apiBase || "");
  if (!normalized) return "seedance";
  for (const preset of VIDEO_PROVIDERS) {
    if (preset.id === "custom") continue;
    if (normalized === normalizeBase(preset.apiBase)) return preset.id;
  }
  return "custom";
}

export function resolveApiBase(provider: ApiProviderId, customBase: string): string {
  if (provider === "custom") return customBase.trim();
  return getApiProvider(provider).apiBase;
}

export function resolveVideoBase(provider: VideoProviderId, customBase: string): string {
  if (provider === "custom") return customBase.trim();
  return getVideoProvider(provider).apiBase;
}
