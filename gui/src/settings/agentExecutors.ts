import { API_PROVIDERS, type ApiProviderId } from "./apiProviders";

export type AgentExecutorId = "pi" | "hermes" | "codex" | "cursor";

export const AGENT_EXECUTOR_IDS: AgentExecutorId[] = ["pi", "hermes", "codex", "cursor"];

export interface AgentExecutorPreset {
  provider?: ApiProviderId;
  model?: string;
  use_third_party?: boolean;
}

export type AgentExecutorsMap = Record<AgentExecutorId, AgentExecutorPreset>;

export interface ExecutorHireDefaults {
  provider: ApiProviderId;
  model: string;
  use_third_party: boolean;
}

function isApiProviderId(id: string): id is ApiProviderId {
  return API_PROVIDERS.some((p) => p.id === id);
}

function coerceProvider(value: unknown, fallback: ApiProviderId): ApiProviderId {
  const id = String(value || fallback);
  return isApiProviderId(id) ? id : fallback;
}

function inferPiPreset(agents: Record<string, unknown>): AgentExecutorPreset {
  const brief = (agents.brief || {}) as Record<string, unknown>;
  const it = (agents.it || {}) as Record<string, unknown>;
  const block =
    _normalizeStr(brief.provider) != null ||
    _normalizeStr(brief.model) != null ||
    brief.model === null
      ? brief
      : it;
  return {
    provider: coerceProvider(block.provider, "openrouter"),
    model: block.model != null ? String(block.model) : "",
    use_third_party: false,
  };
}

function inferHermesPreset(agents: Record<string, unknown>): AgentExecutorPreset {
  const orchestrator = (agents.orchestrator || {}) as Record<string, unknown>;
  const provider = agents.hermes_provider ?? orchestrator.provider;
  return {
    provider: coerceProvider(provider, "openrouter"),
    model: orchestrator.model != null ? String(orchestrator.model) : "",
    use_third_party: false,
  };
}

function inferCodexPreset(agents: Record<string, unknown>): AgentExecutorPreset {
  const roleBlock = (agents["godot-developer"] || {}) as Record<string, unknown>;
  return {
    provider: coerceProvider(roleBlock.provider, "openrouter"),
    model: roleBlock.model != null ? String(roleBlock.model) : "",
    use_third_party: Boolean(roleBlock.use_third_party ?? false),
  };
}

function inferCursorPreset(): AgentExecutorPreset {
  return {};
}

function inferAllFromLegacy(agents: Record<string, unknown>): AgentExecutorsMap {
  return {
    pi: inferPiPreset(agents),
    hermes: inferHermesPreset(agents),
    codex: inferCodexPreset(agents),
    cursor: inferCursorPreset(),
  };
}

function _normalizeStr(value: unknown): string | undefined {
  if (value == null) return undefined;
  const text = String(value).trim();
  return text || undefined;
}

function parseExecutorPreset(
  raw: unknown,
  fallback: AgentExecutorPreset,
  executorId: AgentExecutorId,
): AgentExecutorPreset {
  if (!raw || typeof raw !== "object") return { ...fallback };
  const rec = raw as Record<string, unknown>;
  const preset: AgentExecutorPreset = {
    provider:
      rec.provider != null
        ? coerceProvider(rec.provider, fallback.provider ?? "openrouter")
        : fallback.provider,
    model: rec.model != null ? String(rec.model) : fallback.model,
  };
  if (executorId === "codex") {
    preset.use_third_party =
      rec.use_third_party != null
        ? Boolean(rec.use_third_party)
        : Boolean(fallback.use_third_party ?? false);
  }
  return preset;
}

export function loadAgentExecutorsFromConfig(data: Record<string, unknown>): AgentExecutorsMap {
  const agents = (data.agents || {}) as Record<string, unknown>;
  const inferred = inferAllFromLegacy(agents);
  const raw = agents.executors;
  if (!raw || typeof raw !== "object") return inferred;

  const out = { ...inferred };
  for (const id of AGENT_EXECUTOR_IDS) {
    out[id] = parseExecutorPreset(
      (raw as Record<string, unknown>)[id],
      inferred[id],
      id,
    );
  }
  return out;
}

export function getExecutorPreset(
  map: AgentExecutorsMap,
  executorId: AgentExecutorId,
): AgentExecutorPreset {
  return map[executorId] ?? {};
}

export function defaultsFromExecutorPreset(
  map: AgentExecutorsMap,
  executorId: AgentExecutorId,
): ExecutorHireDefaults {
  const preset = getExecutorPreset(map, executorId);
  return {
    provider: coerceProvider(preset.provider, "openrouter"),
    model: preset.model != null ? String(preset.model) : "",
    use_third_party: executorId === "codex" ? Boolean(preset.use_third_party ?? false) : false,
  };
}

export function serializeAgentExecutors(
  map: AgentExecutorsMap,
): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {};
  for (const id of AGENT_EXECUTOR_IDS) {
    const rec = map[id];
    if (!rec) {
      out[id] = {};
      continue;
    }
    const entry: Record<string, unknown> = {};
    if (rec.provider) entry.provider = rec.provider;
    const model = rec.model != null ? String(rec.model).trim() : "";
    if (model) entry.model = model;
    else if (rec.model != null) entry.model = null;
    if (id === "codex") {
      entry.use_third_party = Boolean(rec.use_third_party ?? false);
    }
    out[id] = entry;
  }
  return out;
}
