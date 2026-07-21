/**
 * Smoke-test executor model catalog helpers (mirrors gui/src/settings/executorModels.ts).
 * Run: node gui/scripts/test-executor-models.mjs
 */

/** Keep in sync with executorModels.ts catalogs. */
const CODEX_MODEL_CATALOG = {
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

const CURSOR_MODEL_CATALOG = {
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

function catalogForNativeExecutor(executor) {
  return executor === "codex" ? CODEX_MODEL_CATALOG : CURSOR_MODEL_CATALOG;
}

function modelForTier(catalog, tier) {
  return catalog.tiers[tier];
}

function tierForModel(catalog, model) {
  const id = String(model || "").trim();
  if (!id) return "mid";
  if (id === catalog.tiers.high) return "high";
  if (id === catalog.tiers.mid) return "mid";
  if (id === catalog.tiers.low) return "low";
  return "custom";
}

function resolveNativeModel(catalog, savedModel) {
  const id = String(savedModel || "").trim();
  return id || catalog.tiers.mid;
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

// catalogForNativeExecutor
assert(
  catalogForNativeExecutor("codex") === CODEX_MODEL_CATALOG,
  "codex catalog",
);
assert(
  catalogForNativeExecutor("cursor") === CURSOR_MODEL_CATALOG,
  "cursor catalog",
);

// modelForTier (Codex)
assert(modelForTier(CODEX_MODEL_CATALOG, "high") === "gpt-5.5", "codex high tier");
assert(modelForTier(CODEX_MODEL_CATALOG, "mid") === "gpt-5.3", "codex mid tier");
assert(modelForTier(CODEX_MODEL_CATALOG, "low") === "gpt-5.3-codex", "codex low tier");

// modelForTier (Cursor)
assert(modelForTier(CURSOR_MODEL_CATALOG, "high") === "opus-4.5", "cursor high tier");
assert(modelForTier(CURSOR_MODEL_CATALOG, "mid") === "auto", "cursor mid tier");
assert(modelForTier(CURSOR_MODEL_CATALOG, "low") === "composer-2", "cursor low tier");

// tierForModel (Codex)
assert(tierForModel(CODEX_MODEL_CATALOG, "gpt-5.5") === "high", "codex tier high");
assert(tierForModel(CODEX_MODEL_CATALOG, "gpt-5.3") === "mid", "codex tier mid");
assert(tierForModel(CODEX_MODEL_CATALOG, "gpt-5.3-codex") === "low", "codex tier low");
assert(tierForModel(CODEX_MODEL_CATALOG, "o3") === "custom", "codex tier custom");
assert(tierForModel(CODEX_MODEL_CATALOG, "") === "mid", "codex empty -> mid");
assert(tierForModel(CODEX_MODEL_CATALOG, "  ") === "mid", "codex whitespace -> mid");

// tierForModel (Cursor)
assert(tierForModel(CURSOR_MODEL_CATALOG, "opus-4.5") === "high", "cursor tier high");
assert(tierForModel(CURSOR_MODEL_CATALOG, "auto") === "mid", "cursor tier mid");
assert(tierForModel(CURSOR_MODEL_CATALOG, "composer-2") === "low", "cursor tier low");
assert(tierForModel(CURSOR_MODEL_CATALOG, "grok-4.5") === "custom", "cursor tier custom");

// resolveNativeModel
assert(
  resolveNativeModel(CODEX_MODEL_CATALOG, "gpt-5.5") === "gpt-5.5",
  "resolve saved model",
);
assert(
  resolveNativeModel(CODEX_MODEL_CATALOG, "") === "gpt-5.3",
  "resolve empty -> mid",
);
assert(
  resolveNativeModel(CURSOR_MODEL_CATALOG, "  ") === "auto",
  "resolve whitespace -> mid",
);

console.log("ok: executorModels");
