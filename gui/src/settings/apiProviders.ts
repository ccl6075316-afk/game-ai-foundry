export type ApiProviderId =
  | "openrouter"
  | "deepseek"
  | "kimi"
  | "glm"
  | "openai"
  | "gemini"
  | "custom";

/** Any provider_accounts key (builtin preset id or user slug). */
export type ProviderId = string;

export const BUILTIN_PROVIDER_IDS = [
  "openrouter",
  "deepseek",
  "kimi",
  "glm",
  "openai",
  "gemini",
] as const;

export type BuiltinProviderId = (typeof BUILTIN_PROVIDER_IDS)[number];

export interface ApiProviderPreset {
  id: string;
  label: string;
  description: string;
  apiBase: string;
  imageModelDefault: string;
  promptModelDefault: string;
  keyPlaceholder: string;
}

export interface ApiProviderHint {
  label?: string;
  apiBase?: string;
  textModel?: string;
  imageModel?: string;
}

export const API_PROVIDERS: ApiProviderPreset[] = [
  {
    id: "openrouter",
    label: "OpenRouter",
    description: "一个平台用多家模型，适合快速切换",
    apiBase: "https://openrouter.ai/api/v1",
    imageModelDefault: "google/gemini-3.1-flash-image",
    promptModelDefault: "deepseek/deepseek-v4-flash",
    keyPlaceholder: "sk-or-…",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    description: "DeepSeek 官方 API（OpenAI 兼容）",
    apiBase: "https://api.deepseek.com/v1",
    imageModelDefault: "",
    promptModelDefault: "deepseek-v4-flash",
    keyPlaceholder: "sk-…",
  },
  {
    id: "kimi",
    label: "Kimi / 月之暗面",
    description: "Moonshot 官方 API；海外可用 api.moonshot.ai/v1",
    apiBase: "https://api.moonshot.cn/v1",
    imageModelDefault: "",
    promptModelDefault: "kimi-k2.5",
    keyPlaceholder: "sk-…",
  },
  {
    id: "glm",
    label: "智谱 GLM",
    description: "智谱 AI 官方 API（OpenAI 兼容）",
    apiBase: "https://open.bigmodel.cn/api/paas/v4",
    imageModelDefault: "",
    promptModelDefault: "glm-4-flash",
    keyPlaceholder: "…",
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

export function isBuiltinProviderId(id: string): id is BuiltinProviderId {
  return (BUILTIN_PROVIDER_IDS as readonly string[]).includes(id);
}

export function listBuiltinProviders(): ApiProviderPreset[] {
  return API_PROVIDERS.filter((p) => isBuiltinProviderId(p.id));
}

export function getApiProvider(id: string, hint?: ApiProviderHint): ApiProviderPreset {
  const builtin = API_PROVIDERS.find((p) => p.id === id);
  if (builtin) return builtin;
  if (hint) {
    return {
      id,
      label: hint.label?.trim() || id,
      description: "用户自建 OpenAI 兼容账号",
      apiBase: hint.apiBase?.trim() || "",
      imageModelDefault: hint.imageModel?.trim() || "",
      promptModelDefault: hint.textModel?.trim() || "",
      keyPlaceholder: "API Key",
    };
  }
  return API_PROVIDERS[0]!;
}

export function isApiProviderId(id: string): id is ApiProviderId {
  return API_PROVIDERS.some((p) => p.id === id);
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
  if (normalized.includes("deepseek.com")) return "deepseek";
  if (normalized.includes("moonshot.cn") || normalized.includes("moonshot.ai")) return "kimi";
  if (normalized.includes("bigmodel.cn")) return "glm";
  for (const preset of API_PROVIDERS) {
    if (preset.id === "custom") continue;
    if (normalized === normalizeBase(preset.apiBase)) return preset.id as ApiProviderId;
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

export function resolveApiBase(provider: string, customBase: string): string {
  if (provider === "custom" || !isBuiltinProviderId(provider)) {
    return customBase.trim();
  }
  return getApiProvider(provider).apiBase;
}

export function resolveVideoBase(provider: VideoProviderId, customBase: string): string {
  if (provider === "custom") return customBase.trim();
  return getVideoProvider(provider).apiBase;
}
