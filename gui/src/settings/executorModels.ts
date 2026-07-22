/**
 * Native Codex/Cursor model UI helpers.
 * Option lists come from CLI (`setup executor models`); tier prefs only apply
 * when that id appears in the live list — never invent fake options.
 */

export type ModelTier = { high: string; mid: string; low: string };

export type ExecutorModelCatalog = {
  tiers: ModelTier;
  options: Array<{ id: string; label: string }>;
  /** Live discovery hint when models empty */
  hint?: string | null;
  source?: string | null;
};

/** Preference order for tiers — used only if id ∈ live options. */
export const CODEX_TIER_PREFS: ModelTier = {
  high: "gpt-5.5",
  mid: "gpt-5.3",
  low: "gpt-5.3-codex",
};

export const CURSOR_TIER_PREFS: ModelTier = {
  high: "opus-4.5",
  mid: "auto",
  low: "composer-2",
};

export function tierPrefsForExecutor(executor: "codex" | "cursor"): ModelTier {
  return executor === "codex" ? CODEX_TIER_PREFS : CURSOR_TIER_PREFS;
}

/** @deprecated Use live CLI list via gameFactory.executorModels */
export function catalogForNativeExecutor(
  executor: "codex" | "cursor",
): ExecutorModelCatalog {
  const prefs = tierPrefsForExecutor(executor);
  return { tiers: prefs, options: [], hint: "请刷新以从本机 CLI 加载模型列表" };
}

export function catalogFromLiveModels(
  executor: "codex" | "cursor",
  models: Array<{ id: string; label?: string }>,
  meta?: { hint?: string | null; source?: string | null },
): ExecutorModelCatalog {
  const prefs = tierPrefsForExecutor(executor);
  const options = models
    .map((m) => ({
      id: String(m.id || "").trim(),
      label: String(m.label || m.id || "").trim() || String(m.id || "").trim(),
    }))
    .filter((m) => m.id);
  const ids = new Set(options.map((o) => o.id));
  const pick = (preferred: string, fallbackIndex: number): string => {
    if (preferred && ids.has(preferred)) return preferred;
    if (options.length === 0) return preferred;
    const idx = Math.min(Math.max(fallbackIndex, 0), options.length - 1);
    return options[idx]!.id;
  };
  return {
    tiers: {
      high: pick(prefs.high, 0),
      mid: pick(prefs.mid, Math.min(1, Math.max(0, options.length - 1))),
      low: pick(prefs.low, Math.max(0, options.length - 1)),
    },
    options,
    hint: meta?.hint ?? null,
    source: meta?.source ?? null,
  };
}

export function modelForTier(
  catalog: ExecutorModelCatalog,
  tier: "high" | "mid" | "low",
): string {
  return catalog.tiers[tier];
}

export function tierForModel(
  catalog: ExecutorModelCatalog,
  model: string,
): "high" | "mid" | "low" | "custom" {
  const id = String(model || "").trim();
  if (!id) return "mid";
  if (id === catalog.tiers.high) return "high";
  if (id === catalog.tiers.mid) return "mid";
  if (id === catalog.tiers.low) return "low";
  return "custom";
}

export function resolveNativeModel(
  catalog: ExecutorModelCatalog,
  savedModel: string,
): string {
  const id = String(savedModel || "").trim();
  if (id) return id;
  if (catalog.options.length === 0) return "";
  return catalog.tiers.mid || catalog.options[0]!.id;
}

export function tierAvailable(
  catalog: ExecutorModelCatalog,
  tier: "high" | "mid" | "low",
): boolean {
  const id = catalog.tiers[tier];
  return Boolean(id && catalog.options.some((o) => o.id === id));
}
