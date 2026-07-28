import {
  VIDEO_PROVIDERS,
  detectApiProvider,
  detectVideoProvider,
  getApiProvider,
  getVideoProvider,
  isApiProviderId,
  isBuiltinProviderId,
  listBuiltinProviders,
  resolveApiBase,
  resolveVideoBase,
  type VideoProviderId,
} from "./apiProviders";
import { keyConfigured } from "./sections";

export { isBuiltinProviderId, listBuiltinProviders };

const PROVIDER_SLUG_RE = /^[a-z][a-z0-9_-]{1,31}$/;

export function isValidProviderSlug(id: string): boolean {
  return PROVIDER_SLUG_RE.test(id);
}

export function isUserProviderId(id: string): boolean {
  return id === "custom" || !isBuiltinProviderId(id);
}

export interface ProviderAccount {
  apiKey: string;
  apiBase: string;
  textModel: string;
  imageModel: string;
  kind?: "builtin" | "user";
  label?: string;
}

export interface VideoAccount {
  apiKey: string;
  apiBase: string;
}

export type ProviderAccountsMap = Record<string, ProviderAccount>;
export type VideoAccountsMap = Partial<Record<VideoProviderId, VideoAccount>>;

function isVideoProviderId(id: string): id is VideoProviderId {
  return VIDEO_PROVIDERS.some((p) => p.id === id);
}

function isLoadableProviderId(id: string): boolean {
  return isApiProviderId(id) || isValidProviderSlug(id);
}

function inferAccountKind(id: string, raw: Record<string, unknown>): "builtin" | "user" {
  if (raw.kind === "user" || raw.kind === "builtin") return raw.kind;
  if (id === "custom") return "user";
  if (isBuiltinProviderId(id)) return "builtin";
  return "user";
}

function readAccount(raw: Record<string, unknown>, id: string): ProviderAccount | undefined {
  const label = raw.label != null ? String(raw.label).trim() : undefined;
  const preset = getApiProvider(id, {
    label,
    apiBase: raw.api_base != null ? String(raw.api_base) : undefined,
    textModel: raw.text_model != null ? String(raw.text_model) : undefined,
    imageModel: raw.image_model != null ? String(raw.image_model) : undefined,
  });
  const kind = inferAccountKind(id, raw);
  const apiKey = String(raw.api_key || "");
  const apiBase = String(raw.api_base || preset.apiBase);
  const textModel = String(raw.text_model || raw.model || "");
  const imageModel = String(raw.image_model || "");

  if (!keyConfigured(apiKey) && !textModel && !imageModel) {
    if (id === "custom") {
      // keep legacy custom slot
    } else if (isBuiltinProviderId(id)) {
      return undefined;
    } else if (!apiBase.trim()) {
      return undefined;
    }
  }

  return {
    apiKey,
    apiBase,
    textModel: textModel || preset.promptModelDefault,
    imageModel: imageModel || preset.imageModelDefault,
    kind,
    ...(label ? { label } : kind === "user" && !isApiProviderId(id) ? { label: id } : {}),
  };
}

export function listUserAccounts(
  map: ProviderAccountsMap,
): Array<{ id: string; account: ProviderAccount }> {
  return Object.entries(map)
    .filter(([id, account]) => account != null && isUserProviderId(id))
    .map(([id, account]) => ({ id, account: account! }));
}

export function getProviderAccount(map: ProviderAccountsMap, id: string): ProviderAccount {
  const saved = map[id];
  const preset = getApiProvider(id, saved);
  return {
    apiKey: saved?.apiKey ?? "",
    apiBase: saved?.apiBase ?? preset.apiBase,
    textModel: saved?.textModel ?? preset.promptModelDefault,
    imageModel: saved?.imageModel ?? preset.imageModelDefault,
    kind: saved?.kind ?? (isBuiltinProviderId(id) ? "builtin" : "user"),
    label: saved?.label,
  };
}

export function updateProviderAccount(
  map: ProviderAccountsMap,
  id: string,
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

export function isProviderConfigured(map: ProviderAccountsMap, id: string): boolean {
  return keyConfigured(getProviderAccount(map, id).apiKey);
}

export function isVideoConfigured(map: VideoAccountsMap, id: VideoProviderId): boolean {
  return keyConfigured(getVideoAccount(map, id).apiKey);
}

function mergeLegacyAccount(
  map: ProviderAccountsMap,
  id: string,
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

function resolveActiveProviderId(
  field: unknown,
  base: string,
  accounts: ProviderAccountsMap,
  fallback: string,
): string {
  if (typeof field === "string" && field in accounts) return field;
  if (typeof field === "string" && isLoadableProviderId(field)) return field;
  return detectApiProvider(base) || fallback;
}

export function loadProviderAccountsFromConfig(data: Record<string, unknown>): {
  providerAccounts: ProviderAccountsMap;
  activeTextProvider: string;
  activeImageProvider: string;
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
    if (!isLoadableProviderId(id)) continue;
    const acc = readAccount(raw, id);
    if (acc) providerAccounts[id] = acc;
  }

  const hostBase = String(host.api_base || image.api_base || "");
  const hostProvider = resolveActiveProviderId(host.provider, hostBase, providerAccounts, "openrouter");

  providerAccounts = mergeLegacyAccount(providerAccounts, hostProvider, host, "text");

  const imageBase = String(image.api_base || "");
  const imageProvider = resolveActiveProviderId(
    image.provider,
    imageBase || hostBase,
    providerAccounts,
    hostProvider,
  );

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

function isUserAccountEntry(id: string, acc: ProviderAccount): boolean {
  return acc.kind === "user" || isUserProviderId(id);
}

export function serializeProviderAccounts(map: ProviderAccountsMap): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [id, acc] of Object.entries(map)) {
    if (!acc) continue;
    const preset = getApiProvider(id, acc);
    const userEntry = isUserAccountEntry(id, acc);

    if (!userEntry && !keyConfigured(acc.apiKey) && id !== "custom") continue;
    if (userEntry && !keyConfigured(acc.apiKey) && !acc.textModel && !acc.imageModel && !acc.apiBase.trim()) {
      continue;
    }

    const entry: Record<string, unknown> = {};
    if (userEntry) {
      entry.kind = "user";
      if (acc.label?.trim()) entry.label = acc.label.trim();
      if (acc.apiBase.trim()) entry.api_base = acc.apiBase.trim();
    } else if (acc.kind === "builtin") {
      entry.kind = "builtin";
    }
    if (acc.apiKey) entry.api_key = acc.apiKey;
    if (!userEntry && id === "custom" && acc.apiBase.trim()) {
      entry.api_base = acc.apiBase.trim();
    }
    if (acc.textModel && acc.textModel !== preset.promptModelDefault) {
      entry.text_model = acc.textModel;
    }
    if (acc.imageModel && acc.imageModel !== preset.imageModelDefault) {
      entry.image_model = normalizeImageModelId(acc.imageModel);
    }
    if (Object.keys(entry).length > 0) out[id] = entry;
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
  activeTextProvider: string;
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
  activeTextProvider: string;
  activeImageProvider: string;
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
