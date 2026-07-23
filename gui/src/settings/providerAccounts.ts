import {
  API_PROVIDERS,
  VIDEO_PROVIDERS,
  detectApiProvider,
  detectVideoProvider,
  getApiProvider,
  getVideoProvider,
  resolveApiBase,
  resolveVideoBase,
  type ApiProviderId,
  type VideoProviderId,
} from "./apiProviders";
import { keyConfigured } from "./sections";

export interface ProviderAccount {
  apiKey: string;
  apiBase: string;
  textModel: string;
  imageModel: string;
}

export interface VideoAccount {
  apiKey: string;
  apiBase: string;
}

export type ProviderAccountsMap = Partial<Record<ApiProviderId, ProviderAccount>>;
export type VideoAccountsMap = Partial<Record<VideoProviderId, VideoAccount>>;

function isApiProviderId(id: string): id is ApiProviderId {
  return API_PROVIDERS.some((p) => p.id === id);
}

function isVideoProviderId(id: string): id is VideoProviderId {
  return VIDEO_PROVIDERS.some((p) => p.id === id);
}

function readAccount(raw: Record<string, unknown> | undefined, id: ApiProviderId): ProviderAccount | undefined {
  if (!raw) return undefined;
  const preset = getApiProvider(id);
  const apiKey = String(raw.api_key || "");
  const apiBase = String(raw.api_base || preset.apiBase);
  const textModel = String(raw.text_model || raw.model || "");
  const imageModel = String(raw.image_model || "");
  if (!keyConfigured(apiKey) && !textModel && !imageModel && id !== "custom") {
    return undefined;
  }
  return {
    apiKey,
    apiBase,
    textModel: textModel || preset.promptModelDefault,
    imageModel: imageModel || preset.imageModelDefault,
  };
}

export function getProviderAccount(
  map: ProviderAccountsMap,
  id: ApiProviderId,
): ProviderAccount {
  const preset = getApiProvider(id);
  const saved = map[id];
  return {
    apiKey: saved?.apiKey ?? "",
    apiBase: saved?.apiBase ?? preset.apiBase,
    textModel: saved?.textModel ?? preset.promptModelDefault,
    imageModel: saved?.imageModel ?? preset.imageModelDefault,
  };
}

export function updateProviderAccount(
  map: ProviderAccountsMap,
  id: ApiProviderId,
  patch: Partial<ProviderAccount>,
): ProviderAccountsMap {
  const current = getProviderAccount(map, id);
  return { ...map, [id]: { ...current, ...patch } };
}

export function getVideoAccount(map: VideoAccountsMap, id: VideoProviderId): VideoAccount {
  const preset = getVideoProvider(id);
  const saved = map[id];
  return {
    apiKey: saved?.apiKey ?? "",
    apiBase: saved?.apiBase ?? preset.apiBase,
  };
}

export function updateVideoAccount(
  map: VideoAccountsMap,
  id: VideoProviderId,
  patch: Partial<VideoAccount>,
): VideoAccountsMap {
  const current = getVideoAccount(map, id);
  return { ...map, [id]: { ...current, ...patch } };
}

export function isProviderConfigured(map: ProviderAccountsMap, id: ApiProviderId): boolean {
  return keyConfigured(getProviderAccount(map, id).apiKey);
}

export function isVideoConfigured(map: VideoAccountsMap, id: VideoProviderId): boolean {
  return keyConfigured(getVideoAccount(map, id).apiKey);
}

function mergeLegacyAccount(
  map: ProviderAccountsMap,
  id: ApiProviderId,
  legacy: Record<string, unknown>,
  role: "text" | "image",
): ProviderAccountsMap {
  const key = String(legacy.api_key || "");
  if (!keyConfigured(key)) return map;
  const existing = getProviderAccount(map, id);
  const patch: Partial<ProviderAccount> = { apiKey: key };
  if (legacy.api_base) patch.apiBase = String(legacy.api_base);
  if (role === "text" && legacy.model) patch.textModel = String(legacy.model);
  if (role === "image" && legacy.model) patch.imageModel = String(legacy.model);
  return updateProviderAccount(map, id, { ...existing, ...patch });
}

export function loadProviderAccountsFromConfig(data: Record<string, unknown>): {
  providerAccounts: ProviderAccountsMap;
  activeTextProvider: ApiProviderId;
  activeImageProvider: ApiProviderId;
  imageUseTextProvider: boolean;
  videoAccounts: VideoAccountsMap;
  activeVideoProvider: VideoProviderId;
} {
  const host = (data.host || {}) as Record<string, unknown>;
  const image = (data.image || {}) as Record<string, unknown>;
  const video = (data.video || {}) as Record<string, unknown>;
  const rawAccounts = (data.provider_accounts || {}) as Record<string, Record<string, unknown>>;
  const rawVideoAccounts = (data.video_accounts || {}) as Record<string, Record<string, unknown>>;

  let providerAccounts: ProviderAccountsMap = {};
  for (const [id, raw] of Object.entries(rawAccounts)) {
    if (!isApiProviderId(id)) continue;
    const acc = readAccount(raw, id);
    if (acc) providerAccounts[id] = acc;
  }

  const hostProviderFromField = host.provider;
  const hostBase = String(host.api_base || image.api_base || "");
  const hostProvider =
    (typeof hostProviderFromField === "string" && isApiProviderId(hostProviderFromField)
      ? hostProviderFromField
      : detectApiProvider(hostBase)) || "openrouter";

  providerAccounts = mergeLegacyAccount(providerAccounts, hostProvider, host, "text");

  const imageProviderFromField = image.provider;
  const imageBase = String(image.api_base || "");
  const imageProvider =
    (typeof imageProviderFromField === "string" && isApiProviderId(imageProviderFromField)
      ? imageProviderFromField
      : detectApiProvider(imageBase || hostBase)) || hostProvider;

  providerAccounts = mergeLegacyAccount(providerAccounts, imageProvider, image, "image");

  const hostKey = getProviderAccount(providerAccounts, hostProvider).apiKey;
  const imageKey = getProviderAccount(providerAccounts, imageProvider).apiKey;
  const explicitUseText = image.use_text_provider;
  let imageUseTextProvider: boolean;
  if (typeof explicitUseText === "boolean") {
    imageUseTextProvider = explicitUseText;
  } else {
    imageUseTextProvider =
      !keyConfigured(imageKey) ||
      (imageKey === hostKey &&
        resolveApiBase(imageProvider, getProviderAccount(providerAccounts, imageProvider).apiBase) ===
          resolveApiBase(hostProvider, getProviderAccount(providerAccounts, hostProvider).apiBase));
  }

  let videoAccounts: VideoAccountsMap = {};
  for (const [id, raw] of Object.entries(rawVideoAccounts)) {
    if (!isVideoProviderId(id)) continue;
    const key = String(raw.api_key || "");
    if (!keyConfigured(key) && id !== "custom") continue;
    videoAccounts[id] = {
      apiKey: key,
      apiBase: String(raw.api_base || getVideoProvider(id).apiBase),
    };
  }

  const videoProviderFromField = video.provider;
  const videoBase = String(video.api_base || "");
  const activeVideoProvider =
    (typeof videoProviderFromField === "string" && isVideoProviderId(videoProviderFromField)
      ? videoProviderFromField
      : detectVideoProvider(videoBase)) || "seedance";

  if (keyConfigured(String(video.api_key || ""))) {
    videoAccounts = updateVideoAccount(videoAccounts, activeVideoProvider, {
      apiKey: String(video.api_key || ""),
      apiBase: videoBase || getVideoProvider(activeVideoProvider).apiBase,
    });
  }

  return {
    providerAccounts,
    activeTextProvider: hostProvider,
    activeImageProvider: imageUseTextProvider ? hostProvider : imageProvider,
    imageUseTextProvider,
    videoAccounts,
    activeVideoProvider,
  };
}

export function serializeProviderAccounts(map: ProviderAccountsMap): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const preset of API_PROVIDERS) {
    const acc = map[preset.id];
    if (!acc) continue;
    if (!keyConfigured(acc.apiKey) && preset.id !== "custom") continue;
    const entry: Record<string, unknown> = {};
    if (acc.apiKey) entry.api_key = acc.apiKey;
    if (preset.id === "custom" && acc.apiBase) entry.api_base = acc.apiBase;
    if (acc.textModel && acc.textModel !== preset.promptModelDefault) entry.text_model = acc.textModel;
    if (acc.imageModel && acc.imageModel !== preset.imageModelDefault) {
      entry.image_model = normalizeImageModelId(acc.imageModel);
    }
    if (Object.keys(entry).length > 0) out[preset.id] = entry;
  }
  return out;
}

export function serializeVideoAccounts(map: VideoAccountsMap): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const preset of VIDEO_PROVIDERS) {
    const acc = map[preset.id];
    if (!acc || !keyConfigured(acc.apiKey)) continue;
    const entry: Record<string, unknown> = { api_key: acc.apiKey };
    if (preset.id === "custom" && acc.apiBase) entry.api_base = acc.apiBase;
    out[preset.id] = entry;
  }
  return out;
}

export function resolveActiveTextSettings(form: {
  providerAccounts: ProviderAccountsMap;
  activeTextProvider: ApiProviderId;
}) {
  const acc = getProviderAccount(form.providerAccounts, form.activeTextProvider);
  return {
    provider: form.activeTextProvider,
    api_key: acc.apiKey.trim() || null,
    api_base: resolveApiBase(form.activeTextProvider, acc.apiBase),
    model: acc.textModel,
  };
}

export function normalizeImageModelId(model: string): string {
  return String(model || "")
    .trim()
    .replace(/^images\//i, "");
}

export function resolveActiveImageSettings(form: {
  providerAccounts: ProviderAccountsMap;
  activeTextProvider: ApiProviderId;
  activeImageProvider: ApiProviderId;
  imageUseTextProvider: boolean;
}) {
  const providerId = form.imageUseTextProvider ? form.activeTextProvider : form.activeImageProvider;
  const acc = getProviderAccount(form.providerAccounts, providerId);
  return {
    provider: providerId,
    use_text_provider: form.imageUseTextProvider,
    api_key: acc.apiKey.trim() || null,
    api_base: resolveApiBase(providerId, acc.apiBase),
    model: normalizeImageModelId(acc.imageModel),
  };
}

export function resolveActiveVideoSettings(form: {
  videoAccounts: VideoAccountsMap;
  activeVideoProvider: VideoProviderId;
}) {
  const acc = getVideoAccount(form.videoAccounts, form.activeVideoProvider);
  return {
    provider: form.activeVideoProvider,
    api_key: acc.apiKey.trim() || null,
    api_base: resolveVideoBase(form.activeVideoProvider, acc.apiBase),
  };
}
