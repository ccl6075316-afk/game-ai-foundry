/** Static catalogs — update by hand when upstream renames models. */

export type ModelTier = { high: string; mid: string; low: string };

export type ExecutorModelCatalog = {
  tiers: ModelTier;
  options: Array<{ id: string; label: string }>;
};

export const CODEX_MODEL_CATALOG: ExecutorModelCatalog = {
  tiers: {
    high: "gpt-5.5",
    mid: "gpt-5.3",
    low: "gpt-5.3-codex",
  },
  options: [
    { id: "gpt-5.5", label: "GPT-5.5" },
    { id: "gpt-5.3", label: "GPT-5.3" },
    { id: "gpt-5.3-codex", label: "GPT-5.3 Codex" },
    { id: "gpt-5.4-mini", label: "GPT-5.4 mini" },
    { id: "o3", label: "o3" },
  ],
};

export const CURSOR_MODEL_CATALOG: ExecutorModelCatalog = {
  tiers: {
    high: "opus-4.5",
    mid: "auto",
    low: "composer-2",
  },
  options: [
    { id: "auto", label: "Auto" },
    { id: "opus-4.5", label: "Opus 4.5" },
    { id: "grok-4.5", label: "Grok 4.5" },
    { id: "composer-2", label: "Composer 2" },
    { id: "sonnet-4.5", label: "Sonnet 4.5" },
  ],
};

export function catalogForNativeExecutor(
  executor: "codex" | "cursor",
): ExecutorModelCatalog {
  return executor === "codex" ? CODEX_MODEL_CATALOG : CURSOR_MODEL_CATALOG;
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
  return id || catalog.tiers.mid;
}
